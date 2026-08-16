---
title: "MediaStore 与 MediaProvider 性能治理"
chapter: "24.11"
section: "24.11"
status: finalized
pipeline_stage: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37); queryDeletedFiles API 37.1 / S Extension 23"
last_verified: "2026-08-15"
last_verified_against: "Android and AOSP docs current through 2026-08-15; Android 17 / API 37 docs and android-17.0.0_r1 MediaProvider source; AndroidX Activity 1.11.0 Photo Picker docs; current Google Play All files access policy"
confidence: high
tags: [MediaStore, MediaProvider, scoped-storage, media-transcoding, thumbnails, io-performance]
related_chapters: ["6.1", "6.4", "22.6", "24.1", "24.6"]
sources:
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/media"
  - type: official
    path: "https://developer.android.com/social-and-messaging/guides/media-thumbnails"
  - type: official
    path: "https://developer.android.com/media/platform/transcoding"
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/photo-picker"
  - type: official
    path: "https://developer.android.com/reference/android/provider/MediaStore"
  - type: official
    path: "https://developer.android.com/reference/android/content/ContentResolver"
  - type: official
    path: "https://developer.android.com/reference/android/media/ApplicationMediaCapabilities"
  - type: official
    path: "https://developer.android.com/reference/androidx/activity/result/contract/ActivityResultContracts.PickVisualMedia.MediaCapabilities"
  - type: policy
    path: "https://support.google.com/googleplay/android-developer/answer/10467955"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/media/media-provider"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/media/media-transcoding"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/storage/scoped"
  - type: aosp
    path: "packages/providers/MediaProvider/apex/framework/java/android/provider/MediaStore.java"
  - type: aosp
    path: "packages/providers/MediaProvider/src/com/android/providers/media/MediaProvider.java"
  - type: aosp
    path: "packages/providers/MediaProvider/jni/FuseDaemon.cpp"
  - type: book-structure
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
---

# MediaStore 与 MediaProvider 性能治理

## 媒体库的耗时从哪里来

`MediaStore` 是应用访问共享媒体的公开 API，`MediaProvider` 是负责实现查询、权限检查和文件访问的系统模块。Android 17 上，一次查询可能从 `ContentResolver` 进入 Binder 跨进程调用，再经过 `MediaProvider`、SQLite 索引和权限过滤。打开查询结果时，还可能进入 FUSE、缩略图生成或兼容媒体转码。FUSE 是 Filesystem in Userspace，即在用户空间处理部分文件系统请求的机制。

列表查询返回得快，首屏仍可能卡在后续工作。`Cursor` 是承载查询结果的游标对象，遍历时可能继续读取数据；`Bitmap` 是解码后的像素数据，分配量会直接影响内存。文件打开和图片解码也要分别计时。

相册、即时通信、备份和文件管理应用面对的媒体项可能达到数万甚至更多。常见问题包括：

- 在主线程查询，或者一次读取整个媒体库。
- 列表绑定时打开原文件并解码。
- 用文件系统遍历重复完成 `MediaProvider` 已经维护的索引工作。
- 把 `ContentObserver` 回调当作完整、按顺序到达的变更日志。
- 把 `generation`（由 `MediaProvider` 递增的变更序号）查询误当成包含删除记录的完整同步协议。
- 未声明媒体能力，导致分享或上传路径发生未计划的转码。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为核对基准。Scoped Storage（分区存储）按文件归属和授权范围限制应用访问，相关演进见 6.1、6.4 节；图片加载与缓存见 22.6、24.6 节；普通文件 I/O 的线程管理见 24.1 节。

## MediaStore 访问模型与性能边界

`MediaStore` 约定了共享媒体的索引和访问方式。列表、筛选和同步通过索引查询完成；读取媒体内容时再打开单个 `Uri`。`Uri` 是形如 `content://...` 的内容标识符，不等同于本地文件路径。文件路径仍可服务于已经合法取得路径的旧库或原生库，但不应作为枚举整个媒体库的入口。

| 访问方式 | 适合场景 | 主要收益 | 必须处理的边界 |
| --- | --- | --- | --- |
| `ContentResolver.query()` | 列表、筛选、搜索、同步 | 复用 `MediaProvider` 索引，只传回所需列 | 权限决定可见行；`Cursor` 仍需在工作线程读取并及时关闭 |
| `openFileDescriptor()` / `openInputStream()` | 上传、编辑、分享、播放单项媒体 | 以 `content://` 为稳定访问入口 | 打开操作可能包含权限检查、重定向或转码，不能在列表绑定阶段批量执行 |
| `ContentResolver.loadThumbnail()` | Android 10 及以上的网格和列表预览 | `MediaProvider` 可利用已有缩略图，并按目标尺寸返回 `Bitmap` | 调用仍可能涉及 Binder、磁盘和解码，需要工作线程与取消信号 |
| 直接路径 / `File` / `fopen()` | 已获授权的现有媒体、旧库或原生库 | 减少第三方库迁移成本 | 路径可能失效；随机读写可能受 FUSE 影响；不能用 `DATA` 创建或移动媒体 |
| Photo Picker | 用户主动选择图片或视频 | 系统选择器只授予所选项目，无需申请整个媒体库的读取权限，并支持云媒体提供方 | 返回项未必有本地路径；后台全库同步不适用 |

访问方式由用户授权范围和当前操作共同决定。索引查询用于缩小集合，打开文件和解码只针对当前需要的项目；表中任何方式都不会绕过权限检查。

### 先确定应用能看到哪些媒体

Android 13 及以上把读取权限分为 `READ_MEDIA_IMAGES`、`READ_MEDIA_VIDEO` 和 `READ_MEDIA_AUDIO`。Android 14 及以上还提供 `READ_MEDIA_VISUAL_USER_SELECTED`，用于表示应用只能访问用户选中的图片和视频。应用自己写入的媒体在 Android 10 及以上不需要读取权限即可再次访问。Photo Picker 返回逐项 `Uri` 授权，其可见集合与整个媒体库的读取权限不同。

所以，“查询结果里没有某条记录”至少可能表示三种情况：文件被删除、存储卷被卸载、当前授权不可见。备份应用不能仅凭查询缺失就删除云端副本。它需要同时记录权限范围、存储卷状态和同步检查点。

`MediaStore.VOLUME_EXTERNAL` 是汇总多个外部卷的合成视图，适合跨卷展示，但它只读。卷是一个独立的存储区域，例如内部共享存储或 SD 卡。插入操作与 `generation` 同步都应使用具体卷名：

```kotlin
val volumes: Set<String> = MediaStore.getExternalVolumeNames(context)

for (volume in volumes) {
    val images = MediaStore.Images.Media.getContentUri(volume)
    // 对每个具体卷分别查询、记录 version 和 generation。
}
```

这段代码用于发现当前已挂载的外部媒体卷。卷名可能随可移动存储的插拔而变化，不能把 `VOLUME_EXTERNAL` 传给 `getVersion(context, volume)` 或 `getGeneration(context, volume)`；两者都要求具体卷名。

### 只查询所需列，并让分页可取消

`projection` 是查询要求返回的列集合，只应包含当前阶段需要的数据。媒体网格通常先取 `_ID`、时间、MIME 类型、宽高、视频时长和 `generation`；MIME 类型用 `image/jpeg` 这类值标识内容格式。详情页再读取 EXIF 拍摄信息或打开文件。查询返回 `Cursor` 后，把列表需要的字段复制到小型数据对象中，再关闭 `Cursor`，避免界面长期占用 `MediaProvider` 查询资源。

大图库不宜用不断增长的 `OFFSET` 翻页；`OFFSET` 表示先跳过多少行。较早页面发生插入或删除后，按行数跳过可能造成重复或遗漏，`MediaProvider` 仍可能扫描这些行。应用可以保存上一页末尾的“排序值 + `_ID`”，下一页从该位置继续查询。代码按 `DATE_ADDED` 和 `_ID` 倒序读取图片；`_ID` 用于区分同一秒加入的多条记录：

```kotlin
data class PageAnchor(
    val dateAddedSeconds: Long,
    val id: Long,
)

fun queryImagePage(
    resolver: ContentResolver,
    volume: String,
    anchor: PageAnchor?,
    limit: Int,
    signal: CancellationSignal,
): Cursor? {
    require(limit > 0)

    val queryArgs = Bundle().apply {
        putString(
            ContentResolver.QUERY_ARG_SQL_SORT_ORDER,
            "${MediaStore.Images.Media.DATE_ADDED} DESC, " +
                "${MediaStore.Images.Media._ID} DESC",
        )
        putInt(ContentResolver.QUERY_ARG_LIMIT, limit)

        if (anchor != null) {
            putString(
                ContentResolver.QUERY_ARG_SQL_SELECTION,
                "(${MediaStore.Images.Media.DATE_ADDED} < ?) OR " +
                    "(${MediaStore.Images.Media.DATE_ADDED} = ? AND " +
                    "${MediaStore.Images.Media._ID} < ?)",
            )
            putStringArray(
                ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS,
                arrayOf(
                    anchor.dateAddedSeconds.toString(),
                    anchor.dateAddedSeconds.toString(),
                    anchor.id.toString(),
                ),
            )
        }
    }

    return resolver.query(
        MediaStore.Images.Media.getContentUri(volume),
        arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DATE_ADDED,
            MediaStore.Images.Media.MIME_TYPE,
            MediaStore.Images.Media.WIDTH,
            MediaStore.Images.Media.HEIGHT,
            MediaStore.Images.Media.GENERATION_MODIFIED,
        ),
        queryArgs,
        signal,
    )
}
```

这是一种应用侧分页方案，不保证 `_ID` 永久稳定。媒体库 `version`（整体版本标识）变化后，应废弃旧页位置并重新查询。界面销毁、筛选条件变化或新查询取代旧查询时，调用 `signal.cancel()`；`MediaProvider` 会在支持取消的位置尽快终止工作。

### 用 `IS_PENDING` 发布完整媒体

Android 10 及以上写共享媒体时，先插入 `IS_PENDING=1` 的记录，写完内容后再清除该标记。其他应用通常不会看到未完成的媒体，调用方也不需要等待媒体扫描重新发现自己刚写入的文件。

这段代码先隐藏未写完的记录，内容写入成功后再发布，保证其他应用看到记录时文件已经完整：

```kotlin
fun publishJpeg(
    resolver: ContentResolver,
    displayName: String,
    writeBody: (OutputStream) -> Unit,
): Uri {
    val collection = MediaStore.Images.Media.getContentUri(
        MediaStore.VOLUME_EXTERNAL_PRIMARY,
    )
    val values = ContentValues().apply {
        put(MediaStore.Images.Media.DISPLAY_NAME, displayName)
        put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
        put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/MyApp")
        put(MediaStore.Images.Media.IS_PENDING, 1)
    }

    val item = checkNotNull(resolver.insert(collection, values))
    try {
        resolver.openOutputStream(item, "w").use { output ->
            checkNotNull(output)
            writeBody(output)
        }
        check(
            resolver.update(
                item,
                ContentValues().apply {
                    put(MediaStore.Images.Media.IS_PENDING, 0)
                },
                null,
                null,
            ) == 1,
        )
        return item
    } catch (error: Exception) {
        resolver.delete(item, null, null)
        throw error
    }
}
```

这段代码应在负责阻塞 I/O 的后台调度器上执行。`IS_PENDING` 表示尚未发布；失败分支删除调用方刚创建的待发布记录，避免留下长期不可见的半成品。清理操作本身也可能失败，生产实现应记录待清理的 `Uri`，并避免让清理异常覆盖最初的写入异常。创建和移动媒体应使用 `DISPLAY_NAME`、`RELATIVE_PATH` 等列；`DATA` 是旧式绝对路径列，不能用于创建或移动媒体。

## MediaProvider 索引、扫描与元数据更新

`MediaProvider` 是 Mainline 可更新模块，可以随 Google Play 系统更新独立于整机系统升级。它维护共享存储中的图片、视频、音频和下载项索引，并在查询、打开文件和扫描时执行可见性检查、位置元数据移除等规则。查询结果反映 `MediaProvider` 已建立的索引，不是对目录进行一次实时遍历。

应用自己通过 `MediaStore.insert()` 创建媒体时，应保留返回的 `Uri`。外部程序直接写入共享目录后，索引更新可能晚于文件出现；读取端要容忍文件存在但索引尚未更新，以及索引行存在但文件打开失败的短暂状态。

### `version` 判断是否重建，`generation` 定位增量

Android 17 的 `MediaStore.java` 对两者给出了不同契约：

- `getVersion(context, volume)` 返回不能解析内部格式的版本字符串。媒体库发生重大变化时，它会改变。应用不必每次查询都调用；进程启动或开始一轮同步时检查即可。
- `getGeneration(context, volume)` 返回该卷当前的变更序号。只要 `version` 没变，`generation` 就单调递增，可以直接比较大小。
- 每行的 `GENERATION_ADDED` 表示记录加入索引时的 `generation`。
- 每行的 `GENERATION_MODIFIED` 表示该记录元数据最近变化时的 `generation`。
- `version` 改变后，旧 `generation` 失去比较意义，应用需要重新分页读取当前可见数据。

`generation` 比 `DATE_ADDED` 和 `DATE_MODIFIED` 更适合做增量判断，因为文件时间可被 `setLastModified()` 或系统时钟变化影响。`generation` 只描述 `MediaProvider` 索引变化，不能替代内容哈希；内容哈希是根据文件字节计算的指纹。元数据变化也不一定表示文件字节已经改变。

这段代码先取得本轮结束序号，再把增量查询限制在“上次检查点之后、本轮结束序号之前”的区间：

```kotlin
data class VolumeCheckpoint(
    val version: String,
    val generation: Long,
)

fun queryChangedImages(
    context: Context,
    volume: String,
    checkpoint: VolumeCheckpoint,
    signal: CancellationSignal,
): Pair<Long, Cursor?> {
    val versionBefore = MediaStore.getVersion(context, volume)
    require(versionBefore == checkpoint.version) {
        "MediaStore version changed; run a full synchronization"
    }

    val endGeneration = MediaStore.getGeneration(context, volume)
    val args = Bundle().apply {
        putString(
            ContentResolver.QUERY_ARG_SQL_SELECTION,
            "((${MediaStore.MediaColumns.GENERATION_ADDED} > ?) OR " +
                "(${MediaStore.MediaColumns.GENERATION_MODIFIED} > ?)) AND " +
                "${MediaStore.MediaColumns.GENERATION_MODIFIED} <= ?",
        )
        putStringArray(
            ContentResolver.QUERY_ARG_SQL_SELECTION_ARGS,
            arrayOf(
                checkpoint.generation.toString(),
                checkpoint.generation.toString(),
                endGeneration.toString(),
            ),
        )
    }

    val cursor = context.contentResolver.query(
        MediaStore.Images.Media.getContentUri(volume),
        arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.GENERATION_ADDED,
            MediaStore.Images.Media.GENERATION_MODIFIED,
            MediaStore.Images.Media.MIME_TYPE,
            MediaStore.Images.Media.SIZE,
        ),
        args,
        signal,
    )
    return endGeneration to cursor
}
```

调用方处理并持久化所有行后，还要再次读取 `version`。前后 `version` 相同，才能把 `endGeneration` 写入检查点；检查点是已经完整处理到哪个位置的持久记录。查询期间发生且 `generation` 大于 `endGeneration` 的变化会留给下一轮。代码把 `Cursor` 交给调用方是为了突出查询区间，业务实现必须用 `use` 关闭它。

`android-17.0.0_r1` 的公开 API 没有删除记录查询。原始媒体行删除后，`GENERATION_MODIFIED` 查询不会返回一个替代它的删除标记；这种保留“某项已删除”信息的记录常称为删除墓碑。因此，以基础 API 为基准的可靠同步需要两条路径：

1. `generation` 增量查询处理新增和修改。
2. 定期分页查询该卷当前可见的 `_ID`，与本地记录逐项比较，补偿进程停止期间遗漏的删除。

比较前要确认卷仍然挂载，且媒体读取权限没有收窄。权限变化造成的“不可见”不能记为用户删除。

当前 API 37.1 / S 扩展 23 已增加 `MediaStore.queryDeletedFiles()`；这里的 S 指 Android 12 的 SDK 扩展线。SDK 扩展版本让 Mainline 模块在基础 Android API 级别不变时增加公开 API。该方法返回外部卷的删除记录，包括原 `_ID`、媒体类型、删除 `generation` 和卷名；内部卷的删除不会返回，外部卷移除后，其删除记录也不再保留。应用应在运行时检查 SDK 扩展版本：支持时用新增/修改查询配合删除查询，不支持时继续比较当前 `_ID` 集合。即使支持该 API，卷移除和权限收窄仍要单独处理。

### `ContentObserver` 只负责唤醒重新查询

Android 11 及以上的 `ContentObserver.onChange()` 可以接收一组 `Uri`，以及表示插入、更新或删除的通知标记。这些详细标记由内容提供方选择是否发送，只能作为提示；`MediaProvider` 也可以只对集合根 `Uri` 发送通知。进程未运行时，系统不会为应用保存完整通知序列，回调的合并、顺序和详细程度都不足以构成持久同步协议。

推荐处理方式是：

- 前台收到通知后，取消已经过时的列表查询，并刷新受影响窗口。
- 后台同步把通知转换成“安排一轮 `generation` 检查”，不直接根据回调参数修改永久记录。
- 高频通知可在短时间内合并成一次刷新；等待时长依据应用测量、交互要求和设备负载确定，不写固定毫秒值。
- 进程重新启动时从持久化的 `version` / `generation` 检查点恢复，不依赖上一次 `ContentObserver` 回调。

## Scoped Storage、FUSE 与批量操作

Android 11 及以上允许应用通过直接路径和原生 `fopen()` 访问其有权读取的共享媒体。`MediaProvider` 的 FUSE 守护进程负责在用户空间处理相关文件请求，仍可执行访问检查、位置元数据移除和兼容转码。

Android Open Source Project（AOSP）文档记录了一组调优 Pixel 2 的对照测试：通过文件路径和 `MediaStore` 顺序读取时性能接近，FUSE 顺序写入稍慢，随机读写耗时最高约为 `MediaStore` 路径的两倍。这个结果描述特定设备和测试方式，不是 Android 17 的性能保证。应用需要在目标机型上按顺序读写、随机读写等实际模式分别测量。

路径访问还受这些约束：

- `DATA` 可用于打开当前已存在且有权访问的媒体，但路径可能因移动、卸载卷或权限变化失效。
- 创建和更新位置应使用 `DISPLAY_NAME` 与 `RELATIVE_PATH`，不能写 `DATA`。
- Photo Picker 或云媒体提供方返回的 `Uri` 不保证对应本地路径。
- 递归扫描目录、逐个读取长度和 EXIF，再查询 `MediaStore`，会重复索引工作并产生大量小 I/O。

列表和同步先查询轻量元数据。只有上传、编辑、播放或详情展示需要文件内容时，才打开相应 `Uri`。

### 批量用户请求有 2000 项输入上限

Android 11 及以上提供四种系统确认请求：

- `createWriteRequest()`：请求一组媒体项的写权限。
- `createFavoriteRequest()`：修改收藏状态。
- `createTrashRequest()`：移入或移出回收站。
- `createDeleteRequest()`：立即删除。

每个 `Uri` 都必须由 `MediaStore` 的 `authority` 托管，并指向带 `_ID` 的具体媒体项。`authority` 是内容提供方在 `content://` 内容标识符中的唯一名称，`MediaStore` 使用 `media`。收藏、回收站或删除请求在系统返回结果前已经执行完成；`createWriteRequest()` 的成功结果只代表用户授予写权限，应用随后还要执行写入。该写权限与发起请求的 `Activity`（界面组件）生命周期相关，不能持久保存，也不能扩展到同一路径前缀。

Android 17 中，`targetSdkVersion` 为 36（Android 16）及以上的应用，每次请求最多传入 2000 个 `Uri`，超出会抛出 `IllegalArgumentException`。2000 是 API 输入上限，并非建议一次让用户确认 2000 项。实际批次应由确认界面的可理解程度、失败恢复方式和设备测量决定。

这段代码在创建系统删除请求前校验 Android 17 的输入边界：

```kotlin
fun createDeleteRequestForItems(
    resolver: ContentResolver,
    itemUris: List<Uri>,
): PendingIntent {
    require(itemUris.isNotEmpty())
    require(itemUris.size <= 2_000) {
        "Android 17 allows at most 2000 item URIs per request"
    }
    require(itemUris.all { uri ->
        uri.authority == MediaStore.AUTHORITY &&
            ContentUris.parseId(uri) >= 0L
    })
    return MediaStore.createDeleteRequest(resolver, itemUris)
}
```

这段校验防止代表整张表的集合 `Uri` 和超限列表进入请求。代码在所有目标版本上都采用 2000 项上限，便于服务端或共享模块使用同一分批规则。用户取消时不能修改本地媒体状态；收到 `RESULT_OK` 后重新查询受影响项，不能假定旧缓存仍然有效。

## 缩略图、预览图与解码成本

媒体网格需要接近控件实际像素尺寸的预览图。读取原图再缩小，会增加文件读取量、解码时间和 `Bitmap` 内存峰值。Android 10 及以上已有 `ContentResolver.loadThumbnail()`；内容提供方可以复用已有缩略图，也可以根据目标尺寸生成结果。

| API | 适合场景 | 成本与限制 |
| --- | --- | --- |
| `ContentResolver.loadThumbnail()` | 已有 `content://` `Uri` 的图片或视频网格 | 可能发生 Binder、文件读取和解码；支持目标尺寸与 `CancellationSignal` |
| `ThumbnailUtils` | 合法持有 `File` 的旧路径代码 | 需要打开文件并生成缩略图；不适用于云媒体 `Uri` |
| `ImageDecoder` | 需要自定义采样、色彩处理或动画图像 | 可能读取原始资源；必须设置目标尺寸或采样 |
| `BitmapFactory` | 兼容静态图片旧代码 | 先读边界再采样，仍需控制流和 `Bitmap` 生命周期 |
| `MediaMetadataRetriever` | 视频指定时间帧、内嵌封面、详情页 | 分离音视频轨道（解复用）和解码的成本较高，不适合网格中并发提取大量帧 |

这个包装函数只负责加载一张缩略图。预取窗口是当前可见项附近、列表准备提前加载的项目范围；列表层持有 `CancellationSignal`，条目离开该范围时取消：

```kotlin
fun loadMediaThumbnail(
    resolver: ContentResolver,
    uri: Uri,
    widthPx: Int,
    heightPx: Int,
    signal: CancellationSignal,
): Bitmap {
    require(widthPx > 0 && heightPx > 0)
    return resolver.loadThumbnail(
        uri,
        Size(widthPx, heightPx),
        signal,
    )
}
```

`loadThumbnail()` 内部会让内容提供方按目标媒体类型打开资源，并在必要时再次缩放。它返回 `Bitmap`，因此仍应在限制并发数的工作线程执行。官方 API 约定，加载失败或 `CancellationSignal.cancel()` 都可能抛出 `IOException`；调用方应结合取消信号状态，把用户不再需要结果与实际读取失败分开统计。

查询、缩略图、上传和转码不宜共享一个可以无限增加任务的执行器。缩略图同时消耗 Binder、磁盘、CPU 和图形内存；并发数应通过首屏时间、滚动丢帧、内存峰值和设备温度测量确定。固定套用 CPU 核数公式也可能在低内存设备上同时产生过多 `Bitmap`。

缓存键是区分和查找缓存对象的标识。缩略图缓存键至少应包含：

- 媒体 `Uri`。
- `GENERATION_MODIFIED` 或应用能够验证的内容版本。
- 目标物理像素宽高。
- 裁剪、旋转、色彩和 HDR/SDR 处理参数；HDR 是高动态范围，SDR 是标准动态范围。

同一 `Uri` 的小网格图和详情预览不能共用一个无尺寸缓存键。`generation` 改变时，只让对应媒体的派生图缓存失效；`version` 改变时，重新校验整个 `MediaStore` 缓存索引。

## 兼容媒体转码只用于明确的格式边界

Android 12 引入兼容媒体转码。设备可以保存 HEVC（H.265 视频编码）或 HDR 媒体；读取方明确声明不支持源格式时，`MediaProvider` 与媒体转码服务可以返回兼容版本，例如把 HDR 视频转为 SDR。首次转码需要完成解码、重新编码和文件 I/O，后续读取才可能复用系统缓存。等待时间取决于片长、分辨率、格式、硬件编解码能力、温度和系统负载，不能拿一台旧设备的单次耗时作为 Android 17 的固定预算。

平台文档建议本机播放和缩略图生成不要触发兼容转码：

- 设备本机播放。播放器通常可以直接使用设备解码能力。
- 生成缩略图。缩略图接口可直接从源媒体产生预览。

兼容转码适合把媒体发送到设备之外的场景，例如服务端不接受 HEVC，或者接收方协议只支持 SDR。上传、导出和分享流程应显示等待与取消状态，并分别测量打开文件描述符的等待时间和后续读取耗时。

### 按调用路径声明媒体能力

`ApplicationMediaCapabilities` 用于描述当前代码路径支持的视频 MIME 类型和 HDR 类型。把它放入 `MediaStore.EXTRA_MEDIA_CAPABILITIES`，再通过 `openTypedAssetFileDescriptor()` 打开媒体，平台便能据此判断是否需要转换。

这段示例表示当前上传路径可以处理 HEVC，但不能处理 HDR10：

```kotlin
val capabilities = ApplicationMediaCapabilities.Builder()
    .addSupportedVideoMimeType(MediaFormat.MIMETYPE_VIDEO_HEVC)
    .addUnsupportedHdrType(MediaFeature.HdrType.HDR10)
    .build()

val options = Bundle().apply {
    putParcelable(MediaStore.EXTRA_MEDIA_CAPABILITIES, capabilities)
}

contentResolver.openTypedAssetFileDescriptor(
    mediaUri,
    "video/*",
    options,
    cancellationSignal,
).use { descriptor ->
    val opened = checkNotNull(descriptor)
    // 从 opened.fileDescriptor 读取并上传兼容内容。
}
```

调用级声明优先于应用资源中的通用声明，适合“本机播放器支持 HDR、上传服务只接受 SDR”这类不同路径。能力声明过宽，应用可能收到自身无法处理的源格式；声明过窄则会增加转码。应用完全不声明媒体能力时，当前平台按“支持所有格式”处理，兼容转码默认关闭。依赖转换的路径必须显式声明不支持的格式。

资源级声明会影响应用的多条媒体访问路径。仅在各路径能力一致时使用，否则缩略图或本机播放也可能受到不需要的转换影响。

### Photo Picker 的 HDR → SDR 转换需要显式开启

Photo Picker 可以返回设备本地或云媒体提供方的 `Uri`。HDR 视频默认不会自动转成 SDR。Android 13 及以上可以通过 AndroidX Photo Picker 请求中的 `MediaCapabilities` 显式选择兼容转码；它是 AndroidX 选择器请求类型，不是平台的 `ApplicationMediaCapabilities`。当前接口要求 AndroidX Activity 1.11.0 及以上，并且只支持最长一分钟的视频。发生转换时，应用拿到可读取的结果 `Uri`。

应用需要据业务路径选择：

- 播放、编辑和上传均支持 HDR：声明支持相应 HDR 类型，保留源质量。
- 上传协议只接收 SDR：在选择请求中声明不支持的 HDR 类型，并在提交上传前处理等待。
- 只显示缩略图：直接请求缩略图，不为预览请求整段视频转码。

需要在应用进程重启后继续处理 Photo Picker 结果时，及时调用 `takePersistableUriPermission()` 保存读取授权，并为授权失效准备重新选择流程。不能把返回的 `Uri` 转换成本地路径；云媒体和系统维护的转码结果都不保证存在可长期依赖的文件路径。

## 用指标、Perfetto 和 `dumpsys` 分段定位

单个“查询耗时”无法区分 Binder 等待、`MediaProvider` 执行、`Cursor` 读取和应用对象构造。应用应给每个阶段单独计时，并用 `Trace.beginSection()` 或 AndroidX Tracing 添加跟踪区间。Perfetto 是 Android 的系统跟踪工具，可以把应用区间与进程调度、Binder、文件 I/O 等事件放到同一时间线上分析。

记录这些字段时，媒体身份使用散列值或内部编号，避免把完整 `Uri` 和文件名写入日志：

- 查询：卷、集合、查询类型、返回列数、分页方式、单页上限、返回行数、`query()` 耗时、`Cursor` 遍历耗时、取消结果。
- 缩略图：目标像素、媒体类型、内存/磁盘缓存命中、调用耗时、取消数、`Bitmap` 分配字节。
- 文件打开：打开 API、读取目的、描述符等待、首字节、总读取量与总耗时。
- 转码：能力声明类别、源格式、接收端要求、描述符等待、读取耗时、取消与失败原因。
- 同步：卷、`version` 是否变化、起止 `generation`、变更行数、`_ID` 集合差异、`ContentObserver` 唤醒次数。

Perfetto 采集至少包含应用进程和 `com.android.providers.media.module` 进程的调度、CPU 频率、Binder、文件系统、块设备 I/O 与内存信息；块设备 I/O 表示发送到存储设备的读写请求。应用自己的跟踪区间用于区分 `query()`、`Cursor` 读取、缩略图、文件打开和转码。只有明确启用或插入 SQLite 跟踪后，界面中才会出现可用于归因的数据库事件；不能只凭一条名称类似 `database` 的轨道判断耗时来源。

### Android 17 的 `MediaProvider` 诊断命令

`android-17.0.0_r1` 的清单把 `MediaProvider` 注册为 `com.android.providers.media.module` 包中的 `ContentProvider`，`authority` 为 `media`。它没有注册成名为 `media_provider` 的 `ServiceManager` 服务；`ServiceManager` 是 Android 原生 Binder 服务的注册表。因此 `adb shell dumpsys media_provider` 不是该版本可依赖的命令。`dumpsys` 是读取 Android 系统服务和组件诊断状态的命令行工具。

先列出匹配的 `ContentProvider` 状态：

```bash
adb shell dumpsys activity providers \
  com.android.providers.media.module/.MediaProvider
```

这条命令用于确认设备上的包名、组件名、进程和发布状态。OEM（设备制造商）修改组件名时，可先运行 `adb shell dumpsys activity providers | grep -i media` 查找设备上的实际组件。

再调用 `MediaProvider` 自身的 `dump()`：

```bash
adb shell dumpsys activity provider \
  com.android.providers.media.module/.MediaProvider
```

Android 17 源码中的 `dump()` 输出包含缩略图尺寸、已连接卷、卷与用户缓存、转码辅助器、Photo Picker 数据库与同步控制器、访问日志等状态。这些字段属于调试实现，不构成应用 API；不同 Mainline `MediaProvider` 版本可能变化。

诊断顺序可以按现象缩小范围：

1. 仅 `query()` 阶段慢：查看调用线程、Binder 往返、`MediaProvider` CPU 和磁盘等待。
2. `Cursor` 很快返回但列表仍慢：查看 `Cursor` 遍历、对象分配和排序后的界面更新。
3. 网格慢：暂停缩略图后复测，再检查解码并发、`Bitmap` 内存与取消是否生效。
4. 打开视频慢：比较普通文件打开与带媒体能力的类型化打开，确认是否等待转码。
5. 扫描期间波动：检查卷挂载、`MediaProvider` I/O、数据库写入和 `ContentObserver` 唤醒密度。

## 大图库首屏加载与分页同步策略

大图库可以使用三条队列，并分别限制并发数和执行频率：

1. 索引查询只生成当前页的轻量列表项。
2. 缩略图加载跟随可见窗口和经过测量的预取窗口。
3. `generation` 同步与删除集合比较在后台维护持久数据。

首屏查询完成后即可提交列表。EXIF、云端备份状态、内容哈希和视频指定帧按需读取。预取距离依据滑动速度、缩略图耗时 P95、内存预算和取消率调整；P95 表示 95% 样本的耗时不超过这个值。不要使用固定“滚动百分比”。

快速滑动时优先取消已经离开预取窗口的缩略图，保留当前可见项。新筛选条件到来时取消旧 `Cursor` 查询。界面中的稳定键可使用“卷名 + `_ID`”，但 `MediaStore` 的 `version` 改变后必须重新建立映射。

后台同步可以采用这组状态转换；状态机表示任务在条件满足后从一个明确状态进入另一个状态：

```text
检查卷是否挂载与权限范围
  → 比较 version
  → version 改变：全量分页同步
  → version 相同：按 generation 查询新增和修改
  → 持久化检查点
  → 按业务周期执行可见 ID 对账
```

这段状态机区分全量恢复、增量更新和删除补偿。每一步完成后再保存对应检查点，失败时从上一份完整检查点恢复。支持 `queryDeletedFiles()` 的系统可以把删除查询放在 `generation` 增量阶段，但仍要保留卷和权限检查。

`IS_PENDING=1` 的其他应用媒体默认不在普通查询结果中，回收站项目也默认被过滤。需要管理回收站的应用应显式使用对应查询参数，并把该状态与普通图库分开。上传任务在打开文件前再次查询记录并处理 `FileNotFoundException`、`SecurityException`，因为排队期间媒体可能被删除、移出可见范围或卸载。

性能验收应覆盖：

- 冷启动与热启动的首屏时间。
- 小库、大库和多个外部卷。
- 快速滚动后的无效缩略图完成数。
- 扫描、云同步或视频转码并行时的 P95/P99；P99 表示 99% 样本的耗时不超过该值。
- 权限从完整访问切换为部分访问。
- SD 卡在同步中卸载与重新挂载。
- `version` 变化后的全量恢复，以及进程停止期间发生删除后的 `_ID` 集合比较。

## 拥有 `MANAGE_EXTERNAL_STORAGE` 权限的应用仍要限制扫描

`MANAGE_EXTERNAL_STORAGE` 是“所有文件访问”特殊权限。Google Play 当前只允许它服务于需要广泛文件访问的核心功能，例如文件管理、备份与恢复、防病毒、文档管理、设备内文件搜索、文件加密和设备迁移。开发者需要在 Play Console 提交权限声明并通过审核。只访问媒体，或让用户手动选择单个文件，不属于允许申请该权限的理由；这些场景应使用 `MediaStore` 或 Storage Access Framework。Storage Access Framework 是由系统文件选择器和文档提供方组成的授权框架。

这项权限不会让目录遍历或随机 I/O 自动变快，也不会取消 FUSE 的所有工作。可见范围扩大后，待扫描条目更多，启动时全盘遍历会增加 I/O、电量、温度和隐私成本。

具备全文件访问的应用仍应分类处理：

- 图片、视频和音频：优先查询 `MediaStore` 索引，按需打开内容。
- 文档和普通文件：根据功能使用 Storage Access Framework 或文件系统。
- 全盘扫描：保存目录与文件检查点，响应卷挂载变化，并按电量、温度和前后台条件限流。
- 媒体变更：避免为每个文件主动触发重复扫描，也不要与系统媒体扫描同时进行大批元数据回写。

发布前应按当前 Google Play 的 [All files access 政策](https://support.google.com/googleplay/android-developer/answer/10467955)重新核对资格。系统提供该权限，不代表应用一定符合商店政策；性能设计也不能以审核一定通过为前提。

## 工程检查清单

- 查询是否按具体卷、必要列和稳定的排序位置分页，并带 `CancellationSignal`。
- 是否区分完整媒体权限、部分媒体权限、Photo Picker 授权和应用自有媒体。
- `version` 改变时是否全量同步；`version` 未变时是否使用 `generation`。
- 是否处理 `android-17.0.0_r1` 的 `generation` 不含删除记录这一边界，并按扩展版本选择 `queryDeletedFiles()` 或 `_ID` 集合比较。
- `ContentObserver` 是否只唤醒重新查询，没有充当持久事件日志。
- 是否避免在 RecyclerView 或 Compose 条目绑定期间同步打开文件、提取视频帧或解码原图。
- 缩略图缓存键是否包含内容版本、目标尺寸和变换参数。
- 批量请求是否使用具体媒体项 `Uri`，并遵守 Android 17 的 2000 项上限。
- 媒体能力是否按播放、上传、导出等路径分别声明。
- 是否为类型化文件打开与转码等待提供取消、进度和分阶段指标。
- Perfetto 区间、`MediaProvider` 的 `dump()` 输出和应用指标能否相互对应。
- 申请 `MANAGE_EXTERNAL_STORAGE` 前是否验证功能必要性与当前商店政策。

## 参考与验证

- [Android Developers：访问共享存储中的媒体](https://developer.android.com/training/data-storage/shared/media)
- [Android Developers：媒体缩略图](https://developer.android.com/social-and-messaging/guides/media-thumbnails)
- [Android Developers：兼容媒体转码](https://developer.android.com/media/platform/transcoding)
- [Android Developers：Photo Picker](https://developer.android.com/training/data-storage/shared/photo-picker)
- [Android API：`MediaStore`](https://developer.android.com/reference/android/provider/MediaStore)
- [Android API：`ContentResolver`](https://developer.android.com/reference/android/content/ContentResolver)
- [Android API：`ApplicationMediaCapabilities`](https://developer.android.com/reference/android/media/ApplicationMediaCapabilities)
- [AndroidX API：Photo Picker `MediaCapabilities`](https://developer.android.com/reference/androidx/activity/result/contract/ActivityResultContracts.PickVisualMedia.MediaCapabilities)
- [Android Developers：管理设备上的所有文件](https://developer.android.com/training/data-storage/manage-all-files)
- [Google Play：All files access 权限政策](https://support.google.com/googleplay/android-developer/answer/10467955)
- [Android API：`ContentObserver`](https://developer.android.com/reference/android/database/ContentObserver)
- [AOSP 文档：MediaProvider 模块](https://source.android.com/docs/core/media/media-provider)
- [AOSP 文档：兼容媒体转码](https://source.android.com/docs/core/media/media-transcoding)
- [AOSP 文档：Scoped Storage](https://source.android.com/docs/core/storage/scoped)
- [Android 17 源码：`MediaStore.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/apex/framework/java/android/provider/MediaStore.java)
- [Android 17 源码：`MediaProvider.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/MediaProvider.java)
- [Android 17 源码：`FuseDaemon.cpp`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp)
- [Android 17 源码：MediaProvider 清单](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/AndroidManifest.xml)
