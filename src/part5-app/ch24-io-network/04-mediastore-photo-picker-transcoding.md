---
title: MediaStore、Photo Picker 与媒体转码
chapter: '24.4'
section: '24.4'
status: finalized
pipeline_stage: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37); queryDeletedFiles API 37.1 / S Extension 23
last_verified: '2026-08-15'
last_verified_against: Android and AOSP docs current through 2026-08-15; Android 17 / API 37 docs and android-17.0.0_r1 MediaProvider source; AndroidX Activity 1.11.0 Photo Picker docs; current Google Play All files access policy
confidence: high
tags:
- MediaStore
- MediaProvider
- scoped-storage
- media-transcoding
- thumbnails
- io-performance
- photo-picker
- mediaprovider
- transcoding
- storage
related_chapters:
- '6.1'
- '6.3'
- '22.9'
- '24.1'
- '24.3'
- '25.10'
- '20.5'
- '26.9'
sources:
- type: official
  path: https://developer.android.com/training/data-storage/shared/media
- type: official
  path: https://developer.android.com/social-and-messaging/guides/media-thumbnails
- type: official
  path: https://developer.android.com/media/platform/transcoding
- type: official
  path: https://developer.android.com/training/data-storage/shared/photo-picker
- type: official
  path: https://developer.android.com/reference/android/provider/MediaStore
- type: official
  path: https://developer.android.com/reference/android/content/ContentResolver
- type: official
  path: https://developer.android.com/reference/android/media/ApplicationMediaCapabilities
- type: official
  path: https://developer.android.com/reference/androidx/activity/result/contract/ActivityResultContracts.PickVisualMedia.MediaCapabilities
- type: policy
  path: https://support.google.com/googleplay/android-developer/answer/10467955
- type: aosp-doc
  path: https://source.android.com/docs/core/media/media-provider
- type: aosp-doc
  path: https://source.android.com/docs/core/media/media-transcoding
- type: aosp-doc
  path: https://source.android.com/docs/core/storage/scoped
- type: aosp
  path: packages/providers/MediaProvider/apex/framework/java/android/provider/MediaStore.java
- type: aosp
  path: packages/providers/MediaProvider/src/com/android/providers/media/MediaProvider.java
- type: aosp
  path: packages/providers/MediaProvider/jni/FuseDaemon.cpp
- type: book-structure
  path: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md
- type: book-structure
  path: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md
- type: book-structure
  path: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md
- type: book-structure
  path: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md
- type: book-structure
  path: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md
- type: official
  path: https://developer.android.com/training/data-storage/shared/photo-picker/embedded
- type: official
  path: https://developer.android.com/reference/android/provider/MediaStore.PickerMediaColumns
- type: official
  path: https://developer.android.com/reference/android/widget/photopicker/PhotoPickerSelectionParams
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/activity
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/photopicker
- type: aosp
  path: packages/providers/MediaProvider/src/com/android/providers/media/TranscodeHelperImpl.java
- type: aosp
  path: packages/providers/MediaProvider/src/com/android/providers/media/PhotoPickerTranscodeHelper.java
- type: aosp
  path: packages/providers/MediaProvider/src/com/android/providers/media/photopicker/PhotoPickerActivity.java
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch24-io-network/11-mediastore-mediaprovider-performance.md
- src/part5-app/ch24-io-network/12-photo-picker-transcoding-performance.md
---

# MediaStore、Photo Picker 与媒体转码

MediaStore 和 MediaProvider 管理共享媒体索引、权限与文件访问，Photo Picker 提供受控选择入口，系统转码可能在交付 URI 内容时改变格式和延迟。缓存必须跟随 URI 授权和媒体版本。

## MediaStore 索引、查询、写入与 Provider 路径

### 媒体库的耗时从哪里来

`MediaStore` 是应用访问共享媒体的公开 API，`MediaProvider` 是负责实现查询、权限检查和文件访问的系统模块。Android 17 上，一次查询可能从 `ContentResolver` 进入 Binder 跨进程调用，再经过 `MediaProvider`、SQLite 索引和权限过滤。打开查询结果时，还可能进入 FUSE、缩略图生成或兼容媒体转码。FUSE 是 Filesystem in Userspace，即在用户空间处理部分文件系统请求的机制。

列表查询返回得快，首屏仍可能卡在后续工作。`Cursor` 是承载查询结果的游标对象，遍历时可能继续读取数据；`Bitmap` 是解码后的像素数据，分配量会直接影响内存。文件打开和图片解码也要分别计时。

相册、即时通信、备份和文件管理应用面对的媒体项可能达到数万甚至更多。常见问题包括：

- 在主线程查询，或者一次读取整个媒体库。
- 列表绑定时打开原文件并解码。
- 用文件系统遍历重复完成 `MediaProvider` 已经维护的索引工作。
- 把 `ContentObserver` 回调当作完整、按顺序到达的变更日志。
- 把 `generation`（由 `MediaProvider` 递增的变更序号）查询误当成包含删除记录的完整同步协议。
- 未声明媒体能力，导致分享或上传路径发生未计划的转码。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为核对基准。Scoped Storage（分区存储）按文件归属和授权范围限制应用访问，相关演进见 6.1、6.3 节；图片加载与缓存见 22.9、24.3 节；普通文件 I/O 的线程管理见 24.1 节。

### MediaStore 访问模型与性能边界

`MediaStore` 约定了共享媒体的索引和访问方式。列表、筛选和同步通过索引查询完成；读取媒体内容时再打开单个 `Uri`。`Uri` 是形如 `content://...` 的内容标识符，不等同于本地文件路径。文件路径仍可服务于已经合法取得路径的旧库或原生库，但不应作为枚举整个媒体库的入口。

| 访问方式 | 适合场景 | 主要收益 | 必须处理的边界 |
| --- | --- | --- | --- |
| `ContentResolver.query()` | 列表、筛选、搜索、同步 | 复用 `MediaProvider` 索引，只传回所需列 | 权限决定可见行；`Cursor` 仍需在工作线程读取并及时关闭 |
| `openFileDescriptor()` / `openInputStream()` | 上传、编辑、分享、播放单项媒体 | 以 `content://` 为稳定访问入口 | 打开操作可能包含权限检查、重定向或转码，不能在列表绑定阶段批量执行 |
| `ContentResolver.loadThumbnail()` | Android 10 及以上的网格和列表预览 | `MediaProvider` 可利用已有缩略图，并按目标尺寸返回 `Bitmap` | 调用仍可能涉及 Binder、磁盘和解码，需要工作线程与取消信号 |
| 直接路径 / `File` / `fopen()` | 已获授权的现有媒体、旧库或原生库 | 减少第三方库迁移成本 | 路径可能失效；随机读写可能受 FUSE 影响；不能用 `DATA` 创建或移动媒体 |
| Photo Picker | 用户主动选择图片或视频 | 系统选择器只授予所选项目，无需申请整个媒体库的读取权限，并支持云媒体提供方 | 返回项未必有本地路径；后台全库同步不适用 |

访问方式由用户授权范围和当前操作共同决定。索引查询用于缩小集合，打开文件和解码只针对当前需要的项目；表中任何方式都不会绕过权限检查。

#### 先确定应用能看到哪些媒体

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

#### 只查询所需列，并让分页可取消

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

#### 用 `IS_PENDING` 发布完整媒体

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

### MediaProvider 索引、扫描与元数据更新

`MediaProvider` 是 Mainline 可更新模块，可以随 Google Play 系统更新独立于整机系统升级。它维护共享存储中的图片、视频、音频和下载项索引，并在查询、打开文件和扫描时执行可见性检查、位置元数据移除等规则。查询结果反映 `MediaProvider` 已建立的索引，不是对目录进行一次实时遍历。

应用自己通过 `MediaStore.insert()` 创建媒体时，应保留返回的 `Uri`。外部程序直接写入共享目录后，索引更新可能晚于文件出现；读取端要容忍文件存在但索引尚未更新，以及索引行存在但文件打开失败的短暂状态。

#### `version` 判断是否重建，`generation` 定位增量

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

#### `ContentObserver` 只负责唤醒重新查询

Android 11 及以上的 `ContentObserver.onChange()` 可以接收一组 `Uri`，以及表示插入、更新或删除的通知标记。这些详细标记由内容提供方选择是否发送，只能作为提示；`MediaProvider` 也可以只对集合根 `Uri` 发送通知。进程未运行时，系统不会为应用保存完整通知序列，回调的合并、顺序和详细程度都不足以构成持久同步协议。

推荐处理方式是：

- 前台收到通知后，取消已经过时的列表查询，并刷新受影响窗口。
- 后台同步把通知转换成“安排一轮 `generation` 检查”，不直接根据回调参数修改永久记录。
- 高频通知可在短时间内合并成一次刷新；等待时长依据应用测量、交互要求和设备负载确定，不写固定毫秒值。
- 进程重新启动时从持久化的 `version` / `generation` 检查点恢复，不依赖上一次 `ContentObserver` 回调。

### Scoped Storage、FUSE 与批量操作

Android 11 及以上允许应用通过直接路径和原生 `fopen()` 访问其有权读取的共享媒体。`MediaProvider` 的 FUSE 守护进程负责在用户空间处理相关文件请求，仍可执行访问检查、位置元数据移除和兼容转码。

Android Open Source Project（AOSP）文档记录了一组调优 Pixel 2 的对照测试：通过文件路径和 `MediaStore` 顺序读取时性能接近，FUSE 顺序写入稍慢，随机读写耗时最高约为 `MediaStore` 路径的两倍。这个结果描述特定设备和测试方式，不是 Android 17 的性能保证。应用需要在目标机型上按顺序读写、随机读写等实际模式分别测量。

路径访问还受这些约束：

- `DATA` 可用于打开当前已存在且有权访问的媒体，但路径可能因移动、卸载卷或权限变化失效。
- 创建和更新位置应使用 `DISPLAY_NAME` 与 `RELATIVE_PATH`，不能写 `DATA`。
- Photo Picker 或云媒体提供方返回的 `Uri` 不保证对应本地路径。
- 递归扫描目录、逐个读取长度和 EXIF，再查询 `MediaStore`，会重复索引工作并产生大量小 I/O。

列表和同步先查询轻量元数据。只有上传、编辑、播放或详情展示需要文件内容时，才打开相应 `Uri`。

#### 批量用户请求有 2000 项输入上限

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

### 缩略图、预览图与解码成本

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

### 兼容媒体转码只用于明确的格式边界

Android 12 引入兼容媒体转码。设备可以保存 HEVC（H.265 视频编码）或 HDR 媒体；读取方明确声明不支持源格式时，`MediaProvider` 与媒体转码服务可以返回兼容版本，例如把 HDR 视频转为 SDR。首次转码需要完成解码、重新编码和文件 I/O，后续读取才可能复用系统缓存。等待时间取决于片长、分辨率、格式、硬件编解码能力、温度和系统负载，不能拿一台旧设备的单次耗时作为 Android 17 的固定预算。

平台文档建议本机播放和缩略图生成不要触发兼容转码：

- 设备本机播放。播放器通常可以直接使用设备解码能力。
- 生成缩略图。缩略图接口可直接从源媒体产生预览。

兼容转码适合把媒体发送到设备之外的场景，例如服务端不接受 HEVC，或者接收方协议只支持 SDR。上传、导出和分享流程应显示等待与取消状态，并分别测量打开文件描述符的等待时间和后续读取耗时。

#### 按调用路径声明媒体能力

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

#### Photo Picker 的 HDR → SDR 转换需要显式开启

Photo Picker 可以返回设备本地或云媒体提供方的 `Uri`。HDR 视频默认不会自动转成 SDR。Android 13 及以上可以通过 AndroidX Photo Picker 请求中的 `MediaCapabilities` 显式选择兼容转码；它是 AndroidX 选择器请求类型，不是平台的 `ApplicationMediaCapabilities`。当前接口要求 AndroidX Activity 1.11.0 及以上，并且只支持最长一分钟的视频。发生转换时，应用拿到可读取的结果 `Uri`。

应用需要据业务路径选择：

- 播放、编辑和上传均支持 HDR：声明支持相应 HDR 类型，保留源质量。
- 上传协议只接收 SDR：在选择请求中声明不支持的 HDR 类型，并在提交上传前处理等待。
- 只显示缩略图：直接请求缩略图，不为预览请求整段视频转码。

需要在应用进程重启后继续处理 Photo Picker 结果时，及时调用 `takePersistableUriPermission()` 保存读取授权，并为授权失效准备重新选择流程。不能把返回的 `Uri` 转换成本地路径；云媒体和系统维护的转码结果都不保证存在可长期依赖的文件路径。

### 用指标、Perfetto 和 `dumpsys` 分段定位

单个“查询耗时”无法区分 Binder 等待、`MediaProvider` 执行、`Cursor` 读取和应用对象构造。应用应给每个阶段单独计时，并用 `Trace.beginSection()` 或 AndroidX Tracing 添加跟踪区间。Perfetto 是 Android 的系统跟踪工具，可以把应用区间与进程调度、Binder、文件 I/O 等事件放到同一时间线上分析。

记录这些字段时，媒体身份使用散列值或内部编号，避免把完整 `Uri` 和文件名写入日志：

- 查询：卷、集合、查询类型、返回列数、分页方式、单页上限、返回行数、`query()` 耗时、`Cursor` 遍历耗时、取消结果。
- 缩略图：目标像素、媒体类型、内存/磁盘缓存命中、调用耗时、取消数、`Bitmap` 分配字节。
- 文件打开：打开 API、读取目的、描述符等待、首字节、总读取量与总耗时。
- 转码：能力声明类别、源格式、接收端要求、描述符等待、读取耗时、取消与失败原因。
- 同步：卷、`version` 是否变化、起止 `generation`、变更行数、`_ID` 集合差异、`ContentObserver` 唤醒次数。

Perfetto 采集至少包含应用进程和 `com.android.providers.media.module` 进程的调度、CPU 频率、Binder、文件系统、块设备 I/O 与内存信息；块设备 I/O 表示发送到存储设备的读写请求。应用自己的跟踪区间用于区分 `query()`、`Cursor` 读取、缩略图、文件打开和转码。只有明确启用或插入 SQLite 跟踪后，界面中才会出现可用于归因的数据库事件；不能只凭一条名称类似 `database` 的轨道判断耗时来源。

#### Android 17 的 `MediaProvider` 诊断命令

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

### 大图库首屏加载与分页同步策略

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

### 拥有 `MANAGE_EXTERNAL_STORAGE` 权限的应用仍要限制扫描

`MANAGE_EXTERNAL_STORAGE` 是“所有文件访问”特殊权限。Google Play 当前只允许它服务于需要广泛文件访问的核心功能，例如文件管理、备份与恢复、防病毒、文档管理、设备内文件搜索、文件加密和设备迁移。开发者需要在 Play Console 提交权限声明并通过审核。只访问媒体，或让用户手动选择单个文件，不属于允许申请该权限的理由；这些场景应使用 `MediaStore` 或 Storage Access Framework。Storage Access Framework 是由系统文件选择器和文档提供方组成的授权框架。

这项权限不会让目录遍历或随机 I/O 自动变快，也不会取消 FUSE 的所有工作。可见范围扩大后，待扫描条目更多，启动时全盘遍历会增加 I/O、电量、温度和隐私成本。

具备全文件访问的应用仍应分类处理：

- 图片、视频和音频：优先查询 `MediaStore` 索引，按需打开内容。
- 文档和普通文件：根据功能使用 Storage Access Framework 或文件系统。
- 全盘扫描：保存目录与文件检查点，响应卷挂载变化，并按电量、温度和前后台条件限流。
- 媒体变更：避免为每个文件主动触发重复扫描，也不要与系统媒体扫描同时进行大批元数据回写。

发布前应按当前 Google Play 的 [All files access 政策](https://support.google.com/googleplay/android-developer/answer/10467955)重新核对资格。系统提供该权限，不代表应用一定符合商店政策；性能设计也不能以审核一定通过为前提。

### MediaStore 路径检查清单

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

### MediaStore 部分的参考与验证

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


## Photo Picker 选择授权、转码与缓存生命周期

媒体索引确定可访问对象后，Photo Picker 只授予选中内容。读取阶段仍可能触发转码，调用方要处理耗时、格式变化和授权失效。

### Photo Picker 负责选择授权，后续处理仍在应用侧

Photo Picker（系统照片选择器）把“用户允许应用读取哪些图片或视频”交给系统界面。只需临时选择媒体的应用不用申请整个媒体库的读取权限，也不用维护相册索引和权限页面。

选择完成后，应用仍需处理：

- 返回 `Uri` 的授权时长和持久化。`Uri` 是统一资源标识符，这里代表系统授予应用读取权的媒体入口，不等同于磁盘路径。
- 本地媒体与云媒体不同的打开延迟。
- HEVC、HDR 和业务目标格式之间的转换。
- 大图采样、视频读取、上传与取消。
- 应用私有临时文件和失败任务的清理。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为准，重点讨论选择完成后的应用处理流程。`MediaStore` 索引、FUSE（Filesystem in Userspace，用户态文件系统）、缩略图和兼容媒体转码原理见本文前半部分；图片解码与 Bitmap（Android 内存中的像素图）缓存见 22.9；文件 I/O（输入/输出）与网络上传见 24.1、24.3。

### Photo Picker 的性能边界

标准 Photo Picker 返回只读 picker `Uri`。应用可以查询 `MediaStore.PickerMediaColumns` 中有限的元数据，也可以按读取模式打开；不能把它当作可写文件路径。云媒体提供方返回的内容还可能在打开时通过网络获取。

SAF（Storage Access Framework，存储访问框架）是 Android 的通用文件选择与访问体系。URI 的 authority 是 `content://` 后标识内容提供方身份的部分，例如 MediaStore 常用 `media`；它决定应用该向哪个 `ContentProvider`（跨进程提供数据的 Android 组件）发起查询或打开请求。

常见选择入口的差异如下：

| 路径 | 适合场景 | 授权与内容边界 |
| --- | --- | --- |
| Photo Picker | 头像、聊天附件、发帖、反馈等用户主动选择 | 只授权所选媒体，可包含云媒体；AndroidX 可自动选择平台实现、系统回退实现或 SAF |
| SAF / `ACTION_OPEN_DOCUMENT` | 任意文档和需要通用文件浏览的流程 | URI authority 来自文档提供方；多选上限和媒体界面由 DocumentsUI 与提供方决定 |
| 厂商相册 Intent | 已有厂商专用协议的产品 | 返回格式和授权行为需要逐设备验证，不适合作为通用默认路径 |
| 应用自建媒体页 | 相册管理、备份和长期媒体库同步 | 由应用负责权限、分页、缩略图、云端同步和索引一致性 |

AndroidX Activity 是 Jetpack 中封装 Activity 与结果回调的兼容库。使用 1.7.0 或更高版本的 `PickVisualMedia` / `PickMultipleVisualMedia` 合约，库会选择设备支持的 Photo Picker；不可用时再回退到 SAF 的 `ACTION_OPEN_DOCUMENT`。单选接入只需注册一次结果合约：

```kotlin
private val pickVideo = registerForActivityResult(
    ActivityResultContracts.PickVisualMedia(),
) { uri ->
    if (uri != null) {
        viewModel.onMediaSelected(uri)
    }
}

fun chooseVideo() {
    pickVideo.launch(
        PickVisualMediaRequest(
            ActivityResultContracts.PickVisualMedia.VideoOnly,
        ),
    )
}
```

这段代码只记录选择结果。回调发生时，视频未必已经在本地准备完成；`onMediaSelected()` 应把 `Uri` 交给后台准备流程，不能在主线程立即读取视频。

#### 把一次选择分成五个阶段

性能数据应按以下顺序记录：

```text
启动选择器
  → 用户确认选择
  → 应用收到 URI
  → 描述符打开
  → 首字节可读
  → 业务数据准备完成
```

这段阶段图用于确定等待发生的位置。标准 Picker 运行在系统 Activity（承载一个界面的 Android 组件）中，普通应用无法在线上准确观测“系统网格首张缩略图出现”的时间；点击到回调还包含用户浏览和选择的时间。实验室可用 UiAutomator 驱动系统界面，用 Macrobenchmark 执行跨进程性能测试，再用 Perfetto 系统跟踪分析调度与 I/O。线上会话时长不能反推出 Picker 的启动或缩略图性能。

`Uri` 回调到文件描述符返回的时间可能包含云媒体下载或转码。文件描述符是进程访问已打开文件或数据流的句柄。描述符返回后还要单独测“首字节可读”的时间，因为系统可能先返回管道的一端，再异步供应内容。上传请求能够读取完整内容，或编辑流程取得可用输入与本地副本时，才算完成媒体准备。

#### API 36 及以上优先使用 `MediaStore.open*`

Android 16 / API 36 起，`MediaStore.openFileDescriptor()`、`openAssetFileDescriptor()` 和 `openTypedAssetFileDescriptor()` 可用于打开 `ACTION_PICK_IMAGES` 返回的 MediaStore URI；三者也通过 Android 11（R）SDK Extension 15 提供。官方 API 文档建议优先使用这些入口，以增强系统稳定性。AndroidX 回退到 SAF 时，URI authority 不再是 `media`，仍需使用 `ContentResolver`。

下面的函数按版本和 authority 选择读取入口，并把取消信号传给 Provider：

```kotlin
fun openSelectedMedia(
    resolver: ContentResolver,
    uri: Uri,
    signal: CancellationSignal,
): ParcelFileDescriptor? {
    return if (
        Build.VERSION.SDK_INT >= 36 &&
        uri.authority == MediaStore.AUTHORITY
    ) {
        MediaStore.openFileDescriptor(resolver, uri, "r", signal)
    } else {
        resolver.openFileDescriptor(uri, "r", signal)
    }
}
```

示例只在 `SDK_INT >= 36` 时进入新 API 分支，便于展示平台版本判断。若产品还要在 Android 11–15 上使用 R Extension 15 提供的同名 API，需要额外检查 R 扩展版本，并把调用隔离在受 `@RequiresExtension` 约束的函数中；只检查 `SDK_INT` 不够。调用方拥有返回的描述符，使用后必须关闭。用户取消任务、页面退出或新选择替代旧选择时调用 `signal.cancel()`。云端失败、权限取消、Provider 崩溃和媒体被删除都应作为可恢复的读取失败处理。

Picker URI 可查询 `SIZE`、`DISPLAY_NAME`、`MIME_TYPE`、`DURATION_MILLIS`、`WIDTH`、`HEIGHT`、`ORIENTATION` 等只读列。MIME type（媒体类型标识，例如 `video/mp4`）描述内容格式。`SIZE` 和路径信息只能作为提示；云媒体可能依赖网络，应用也不应根据 `DATA` 拼装文件路径。

#### 临时授权与持久授权

默认授权持续到设备重启或应用停止。后台上传、WorkManager（Jetpack 的可延迟后台任务调度器）恢复、草稿跨进程重启等场景应在收到 URI 后调用：

```kotlin
fun persistPickerGrant(
    resolver: ContentResolver,
    uri: Uri,
) {
    resolver.takePersistableUriPermission(
        uri,
        Intent.FLAG_GRANT_READ_URI_PERMISSION,
    )
}
```

这段代码延长读取授权，不会把远端媒体下载到本地。Android 平台允许每个应用同时保留最多 5000 个媒体授权；继续新增时会移除最早的授权。草稿删除、任务结束和账号退出时应调用 `releasePersistableUriPermission()`，并在后台任务开始前重新验证读取能力。

#### Android 17 可在 Picker 中执行选择限制

`android-17.0.0_r1` 的 `MediaStore.getPickImagesMaxLimit()` 返回 100。应用的多选数量不能超过平台上限；设备回退到 `ACTION_OPEN_DOCUMENT` 时，系统会忽略 AndroidX 传入的最大数量，因此回调后仍需执行数量校验。

API 37 的 `PhotoPickerSelectionParams` 还能按 MIME、单项大小、批次总大小、分辨率和视频时长限制可选内容。超出限制的媒体仍显示在网格中，但处于禁选状态；这能减少选择完成后才拒绝文件的情况。限制值必须来自服务端协议、设备可用空间上限或产品规则。

下面的 Android 17 函数按调用方传入的限制创建视频选择 Intent：

```kotlin
@RequiresApi(37)
fun createConstrainedVideoPicker(
    maxItemBytes: Long,
    maxDuration: Duration,
): Intent {
    require(maxItemBytes > 0)
    require(!maxDuration.isZero && !maxDuration.isNegative)

    val params = PhotoPickerSelectionParams.Builder()
        .setMimeTypes(listOf("video/*"))
        .setMaxMediaItemSizeInBytes(maxItemBytes)
        .setMaxVideoDuration(maxDuration)
        .build()

    return Intent(MediaStore.ACTION_PICK_IMAGES).apply {
        type = "video/*"
        putExtra(MediaStore.EXTRA_PICK_IMAGES_SELECTION_PARAMS, params)
    }
}
```

这段代码以 `@RequiresApi(37)` 表示平台版本分支；同一 API 也通过 Android 14（U）的 SDK Extension 22 提供。SDK Extension 是模块化系统组件的功能版本号，同一 Android 大版本可因系统组件更新获得新增 API，因此扩展路径要检查 U Extension 22，并把调用隔离在受 `@RequiresExtension` 约束的函数中。更早的版本需要在选择后校验。Picker 的元数据限制可以减少无效选择，却不能保证云端内容已经下载，也不能代替打开、读取和上传阶段的错误处理。

### 嵌入式 Photo Picker 的接入成本

嵌入式 Photo Picker 把系统媒体网格放在应用页面的 `SurfaceView` 中。`SurfaceView` 为独立图形表面预留显示区域，`setChildSurfacePackage()` 再把系统进程提供的 `SurfacePackage` 接入该区域。宿主 Activity 保持 Resumed（可交互的前台生命周期）状态，可以连续接收选择与取消选择事件；媒体内容的授权边界与标准 Picker 相同。

该能力要求 Android 14 及以上，且 U SDK Extension 至少为 15。平台类从 API 36 公开，也通过扩展提供给 Android 14。当前 Jetpack `androidx.photopicker` 版本为 1.0.0-alpha02，API 仍标记 `ExperimentalPhotoPickerApi`；Alpha 阶段允许接口变化，升级依赖时应复核回调和生命周期行为。不满足条件或会话打开失败时，使用标准 Photo Picker。

嵌入式路径需要单独处理四类成本：

- 宿主首帧：输入区、附件条和 Picker 容器属于应用绘制。
- 会话建立：Jetpack 需要连接系统服务、创建图形表面并取得系统 `SurfacePackage`。
- 媒体网格：索引、缩略图和云媒体仍由系统 Picker 加载。
- 连续选择：每次授权和撤销都可能更新附件列表、校验规则和准备队列。

`Activity.onCreate()` 到首帧只覆盖宿主页面，不能代表 Picker 已经可用。会话打开、Picker 内容可见和首次选择回调应分别测量。系统没有向应用提供稳定的“首张缩略图已绘制”业务回调，这一项仍需借助界面自动化和 Perfetto 测量。

#### 连续选择需要双向维护状态

Jetpack 提供 `onUriPermissionGranted` 和 `onUriPermissionRevoked`，分别通知用户选择和取消选择的 URI，应用据此更新附件列表。应用主动调用 `deselectUri()` / `deselectUris()` 时还应同步删除自己的选中状态；不能等待只为“用户取消选择”定义的 revoked 回调来维护客户端状态。否则，附件条与系统网格可能出现选择不一致。

选择事件只应安排后台准备任务。缩略图预览、元数据查询、云媒体打开和上传准备都不应在回调的主线程中完成。用户取消选择后，依次取消该 URI 的打开信号、解码任务和尚未开始的上传任务。

折叠屏、多窗口、横竖屏和输入法显示会改变宿主与 `SurfaceView` 尺寸。应用应保存选择 URI 和页面模式，把窗口尺寸更新交给现有会话；不要因为普通布局变化反复销毁并创建嵌入式 Picker。退出页面时关闭会话并释放监听，防止图形表面和回调继续持有 Activity。

### 视频转码的时间与存储成本

HDR（High Dynamic Range，高动态范围）可保留更大的亮度与色彩范围，SDR（Standard Dynamic Range，标准动态范围）兼容面通常更广。Photo Picker 的 HDR→SDR 与 MediaProvider 的兼容媒体转码都根据应用声明的媒体能力决定是否转换，但两者属于不同入口：

| 入口 | 启用方式 | 返回行为 | Android 17 边界 |
| --- | --- | --- | --- |
| Photo Picker HDR→SDR | 启动 Picker 时通过 AndroidX `MediaCapabilities` 声明支持的 HDR 类型 | 发生转换时，Picker 返回转码结果 URI | Android 13 及以上；只处理不超过 1 分钟的视频；结果缓存会在设备空闲维护时清理 |
| MediaProvider 兼容转码 | 打开媒体时传入 `ApplicationMediaCapabilities`，或使用资源声明 | 支持源格式时返回原内容；不支持时可能返回 AVC/SDR 或缓存结果 | Android 12 及以上；设备、格式、来源、片长和系统资源都影响是否转换 |

两条路径都不会只因应用“可能不支持”便无条件转换。应用必须准确声明能力，并在接收端检查最终媒体能否处理。旧 Pixel 3 的测量值不能直接作为 Android 17 的耗时目标；片长、分辨率、源格式、编解码器、存储、温度和并发负载都会改变等待时间。

#### Photo Picker HDR→SDR

AndroidX Activity 的 `PickVisualMediaRequest.Builder.setMediaCapabilitiesForTranscoding()` 接收 `MediaCapabilities`。列出的 HDR 类型表示应用支持；未列出的类型视为不支持。传入 `null` 会关闭该请求的转码。

下面的请求表示应用能处理 HLG10，其他 HDR 类型可由 Picker 按平台能力转换：

```kotlin
@RequiresApi(33)
fun chooseCompatibleVideo(
    launcher: ActivityResultLauncher<PickVisualMediaRequest>,
) {
    val capabilities = MediaCapabilities.Builder()
        .addSupportedHdrType(MediaCapabilities.HdrType.TYPE_HLG10)
        .build()

    launcher.launch(
        PickVisualMediaRequest.Builder()
            .setMediaType(
                ActivityResultContracts.PickVisualMedia.VideoOnly,
            )
            .setMediaCapabilitiesForTranscoding(capabilities)
            .build(),
    )
}
```

这段代码需要 AndroidX Activity 1.11.0 或更高版本。Picker 执行转换时会返回转换后的 URI；调用方不能通过解析 URI 路径判断是否命中缓存。

转码会创建新文件并占用处理时间，且只处理不超过 1 分钟的视频。超过限制、设备能力不足或平台未执行转换时，应用可能拿到原内容。上传协议只接受 SDR 时，读取后仍需验证视频轨道的色彩信息，并为不支持的结果提供应用侧转换或拒绝流程。

#### MediaProvider 兼容转码

Android 17 延续 Android 12 引入的兼容转码。AOSP 文档规定的标准来源是 OEM（设备制造商）原生相机写入主外部卷 `DCIM/Camera/` 的本机视频；二级存储以及通过邮件、SD 卡等外部来源导入的媒体不在标准支持范围内。厂商只能通过资源覆盖增加 `DCIM/` 中的路径。

标准转换包含 HEVC（H.265，高效率视频编码）8-bit→AVC（H.264，高级视频编码），以及设备具备色调映射插件时的 HDR10+ 10-bit→AVC SDR。色调映射会把 HDR 的亮度和颜色映射到 SDR 可表达的范围。MediaStore、直接路径、SAF、使用 MediaStore URI 的系统分享，以及 MTP/PTP（USB 媒体或相机传输协议）都可能进入转码。取出 SD 卡以及 Nearby Share、蓝牙等设备间传输路径会绕过它。

标准实现只处理不超过 1 分钟的视频。平台还限制连续转码会话和累计运行时间；AOSP 文档给出的限制是连续 10 个会话、累计 3 分钟，两项都超出后返回原描述符。设备缺少 HDR 插件时也会返回原描述符。多选上传不能假定所有不支持的媒体都会被系统转换。

兼容转码适合把媒体上传到设备外、导出或分享。本机播放直接使用设备解码器；网格预览使用缩略图 API。资源级 `media_capabilities.xml` 会影响应用的多条读取路径，可能让本机播放或缩略图发生非预期转换。播放、上传等功能支持的格式不同时，宜在每次打开媒体时传入对应的 `ApplicationMediaCapabilities`，具体代码见本文前半部分“按调用路径声明媒体能力”。

### MediaProvider 与缓存清理

媒体选择后可能出现三类缓存，所有权和清理责任不同：

| 层次 | 内容 | 清理者 | 应用能否依赖 |
| --- | --- | --- | --- |
| MediaProvider 兼容转码缓存 | FUSE 读取时生成的 AVC/SDR 文件 | MediaProvider 与系统存储管理 | 不能依赖路径、存活时间或命中 |
| Photo Picker HDR 转码缓存 | Picker 返回的兼容视频 | Picker 的设备空闲维护 | 只能依赖仍有效的 URI 授权，不能依赖缓存文件持续存在 |
| 应用私有临时数据 | 上传副本、压缩结果、编辑中间文件、业务缩略图 | 应用 | 必须有持久记录、容量上限和删除策略 |

在 Android 17 AOSP 实现中，`TranscodeHelperImpl.java` 把兼容转码文件放在 `/storage/emulated/<user>/.transforms/transcode/`，以 MediaStore 数据库行 ID 生成内部文件名，并实现 `freeCache()` 与单项删除。该路径不是公开 API 契约，只适合源码阅读和系统调试；应用无权据此定位或清理文件，也不能从一次缓存命中推断后续仍会命中。

同一版本的 `PhotoPickerTranscodeHelper.java` 把 Picker HDR 转码结果放在 `/storage/emulated/<user>/.picker_transcoded/`，按媒体提供方 authority 与媒体 ID 生成缓存名，并提供按容量、全量和单项清理入口。这里的 host 是被 Picker URI 包装的媒体提供方 authority。两种目录都由 MediaProvider 模块管理，但服务于不同的请求路径；应用只能通过有效 URI 读取，不能直接访问这些目录。

系统设备空闲维护不会处理应用的 `cacheDir`、草稿数据库和失败上传。应用应给每个私有临时文件记录：

- 所属草稿、消息或编辑任务的 ID。
- 原始 picker URI 与持久授权状态。
- 文件用途与是否可重新生成。
- 创建时间、最近访问时间和任务状态。
- 预期大小、已写大小与校验结果。

发送完成、用户取消选择、草稿删除和账号退出都应触发对应清理。失败任务是否保留副本、保留多久，应根据允许重试的时间和可用存储上限确定，不能统一套用一个时间值。

#### 什么时候复制到应用私有目录

服务端接受源格式、上传库支持顺序流，且任务不需要随机定位（seek）时，可直接从 picker URI 上传，避免额外副本。以下情况更适合复制一次：

- 需要断点续传或多次重试，而源 URI 可能依赖网络。
- 图片编辑、视频分析或编码器需要在文件中反复定位。
- 任务要跨进程重启，且不能接受系统缓存清理后重新下载或重新转码。
- 需要在上传前生成稳定摘要并核对完整内容。

复制过程使用 `.partial` 后缀标记“尚未写完”的临时文件，写完并校验后再切换为 ready（内容完整、可供业务使用）状态。进程中止后，清理程序只删除没有活跃任务引用的 partial 文件。`cacheDir` 仍可能在存储压力下被系统删除。必须保证跨重启保留的内容，应放在应用管理的私有目录，并由数据库状态控制删除。

一条可恢复的准备状态如下：

```text
selected
  → grant-persisted
  → opening
  → copying-or-transforming
  → ready
  → uploading
  → completed / retryable-failure / abandoned
```

状态名依次表示已选择、已持久授权、正在打开、正在复制或转换、内容就绪、正在上传，以及三种终态：完成、可重试失败和放弃。保留这些英文短名，便于直接用作数据库枚举和日志字段。数据库事务是一组要么全部生效、要么全部回滚的状态写入；每次状态变化与文件重命名完成后再提交事务，恢复逻辑便能判断应继续任务还是删除不再被记录引用的文件。

### 大图、多选和云端媒体的 I/O 与内存压力

多选要形成有容量限制的任务队列，不能按 URI 数量同时启动单选处理。选择数量、源文件总字节、解码后的 Bitmap、转换后的临时文件和上传并发属于不同预算，任一项都可能先触及设备上限。

收到 URI 后可先查询允许的 Picker 列，避免为列表预览打开原内容：

```kotlin
data class PickedMediaMeta(
    val mimeType: String?,
    val sizeBytes: Long?,
    val width: Int?,
    val height: Int?,
    val durationMs: Long?,
)

fun queryPickedMediaMeta(
    resolver: ContentResolver,
    uri: Uri,
): PickedMediaMeta? {
    require(uri.authority == MediaStore.AUTHORITY)

    val hasDimensionColumns = Build.VERSION.SDK_INT >= 34 ||
        (
            Build.VERSION.SDK_INT >= 30 &&
                SdkExtensions.getExtensionVersion(Build.VERSION_CODES.R) >= 5
        )
    val columns = mutableListOf(
        MediaStore.PickerMediaColumns.MIME_TYPE,
        MediaStore.PickerMediaColumns.SIZE,
        MediaStore.PickerMediaColumns.DURATION_MILLIS,
    )
    if (hasDimensionColumns) {
        columns += MediaStore.PickerMediaColumns.WIDTH
        columns += MediaStore.PickerMediaColumns.HEIGHT
    }

    return resolver.query(
        uri,
        columns.toTypedArray(),
        null,
        null,
        null,
    )?.use { cursor ->
        if (!cursor.moveToFirst()) return@use null

        fun longOrNull(column: String): Long? {
            val index = cursor.getColumnIndex(column)
            return if (index >= 0 && !cursor.isNull(index)) {
                cursor.getLong(index)
            } else {
                null
            }
        }

        PickedMediaMeta(
            mimeType = cursor.getColumnIndex(
                MediaStore.PickerMediaColumns.MIME_TYPE,
            ).takeIf { it >= 0 && !cursor.isNull(it) }
                ?.let(cursor::getString),
            sizeBytes = longOrNull(MediaStore.PickerMediaColumns.SIZE),
            width = if (hasDimensionColumns) {
                longOrNull(MediaStore.PickerMediaColumns.WIDTH)?.toInt()
            } else {
                null
            },
            height = if (hasDimensionColumns) {
                longOrNull(MediaStore.PickerMediaColumns.HEIGHT)?.toInt()
            } else {
                null
            },
            durationMs = longOrNull(
                MediaStore.PickerMediaColumns.DURATION_MILLIS,
            ),
        )
    }
}
```

这段代码只用于 authority 为 `media` 的 picker URI，并及时关闭 Cursor（查询结果游标）。`MIME_TYPE`、`SIZE` 和 `DURATION_MILLIS` 从 API 33 / R Extension 2 可用；`WIDTH`、`HEIGHT` 从 API 34 / R Extension 5 可用，所以查询投影先做能力判断。这里的“投影”是一次查询请求返回的列集合。

AndroidX 回退到 SAF 时，使用 `ContentResolver.getType()` 与 `OpenableColumns.SIZE` / `DISPLAY_NAME`，不要请求 Picker 专用列。即使列已定义，值也可能为空；`SIZE` 不能代替流式读取时的实际字节计数。元数据适合做排队和界面提示，安全校验仍需在读完整个内容后完成。

#### 图片路径

网格预览使用 `ContentResolver.loadThumbnail()` 或支持 `content://` 的图片库，并传入控件所需的像素尺寸。上传服务接受 HEIC、AVIF、JPEG 或 PNG 源文件时，直接流式上传，避免生成 Bitmap。

只有裁剪、缩放、去除元数据或转换格式时才解码。解码器应设置目标尺寸或采样，再依据 Bitmap 字节数限制并发。图片文件的压缩字节数无法预测解码内存，宽高、像素格式、色彩空间和中间 Bitmap 都会影响内存峰值。

#### 视频路径

视频预览使用缩略图或播放器，不为网格提取多个指定时间帧。上传不需要转封装或转码时直接顺序读取；需要格式转换时，把转换任务放入独立队列，并把输入读取、编码输出与临时文件空间同时计入预算。转封装只改变媒体容器，转码则重新解码和编码音视频轨道，两者的 CPU 成本不同。

#### 云媒体路径

系统 Picker 会尝试预加载已选云媒体。在 Android 17 AOSP 的 `PhotoPickerActivity.java` 实现中，设备离线且云端媒体未缓存时会提示错误，并从选择中移除不可用项。这是当前源码行为，不表示返回 URI 后内容会持续可用；应用打开时仍可能遇到网络变化、云账号变化或缓存清理。

界面至少区分：

- 已选择：应用收到 URI。
- 正在准备：查询、云端获取、打开或转换尚未完成。
- 可发送：业务已经取得可读流或验证完成的本地副本。
- 失败：可以重试、重新选择或移除。

URI 打开和顺序复制主要消耗 I/O；图片缩放、编码和哈希摘要计算主要消耗 CPU；上传由网络调度器管理。三个队列分别限流，选择数量增加时不按相同比例增加线程。用户取消某项时，取消该项尚未完成的打开、解码、转换和上传请求。

### 监控与回归测试

这里的监控是把一次媒体处理拆成可记录的时间段，以确定等待发生在哪一步。线上数据和实验室数据要分开设计。标准 Picker 的系统网格绘制对调用应用不可见，线上埋点不能声称测到了 Picker 首帧或首张缩略图。应用可记录的阶段如下：

| 指标 | 起点与终点 | 说明 |
| --- | --- | --- |
| `picker_session_ms` | 启动请求→收到结果 | 包含用户浏览时间，只用于选择流程完成率和异常长会话，不是启动性能 |
| `selection_to_open_ms` | 收到 URI→描述符返回 | 包含授权检查、Provider、云端获取或转码等待 |
| `open_to_first_byte_ms` | 描述符返回→首字节读取 | 区分描述符建立与内容供应 |
| `prepare_queue_ms` | 任务入队→开始处理 | 判断 I/O 或 CPU 队列拥塞 |
| `prepare_work_ms` | 开始处理→内容可上传或可编辑 | 复制、解码、压缩、转码或摘要计算 |
| `upload_ms` | 网络请求开始→完成 | 与本地准备分开 |
| `temp_bytes` | 任务状态变化时采样 | 观察 partial、ready 和失败副本占用 |

事件公共字段包括 Picker 路径、Android 版本、SDK Extension、是否嵌入式、是否 SAF 回退、媒体类型、数量、声明的能力类别、持久授权结果和取消阶段。不要记录原始 URI、文件名、相册名或云账号。

应用无法仅从 URI 可靠判断系统是否执行过兼容转码。实验室可结合：

```bash
adb shell dumpsys media.transcoding
adb shell dumpsys activity provider \
  com.android.providers.media.module/com.android.providers.media.MediaProvider
```

第一条命令查看当前和历史媒体转码会话；第二条查看 AOSP Android 17 MediaProvider 的存储卷、转码辅助器和访问状态。OEM 或 Google MediaProvider 的组件名可能不同，应先用 `adb shell dumpsys activity providers | grep -i media` 定位。

Perfetto 可采集应用、MediaProvider 和媒体服务的调度、Binder 跨进程调用、CPU 频率、文件系统、块设备 I/O、内存与网络，并在应用代码中标记 URI 打开、首字节、复制、解码、编码和上传区间。标准 Picker 的启动和网格内容使用 Macrobenchmark / UiAutomator 驱动；嵌入式路径还要记录宿主首帧、会话打开与图形表面尺寸变化。

#### 回归测试覆盖

设备和能力组合至少包括：

- Android 13 平台 Picker。
- Android 14 及以上、U Extension 15 的嵌入式 Picker。
- Android 17 的 `PhotoPickerSelectionParams` 和 `MediaStore.open*`。
- Android 11/12 的模块化 Picker。
- Google Play services backport，以及明确走 `ACTION_OPEN_DOCUMENT` 的设备。

媒体组合包括本地与云端、云端离线、JPEG/HEIC/AVIF、HEVC、各业务支持的 HDR 类型、1 分钟边界两侧的视频、单选与业务允许的最大多选。生命周期用例包括设备重启、进程终止、持久授权、授权释放、选择后立即取消、准备中取消、存储空间不足和 Provider 读取失败。

验收使用目标设备的 P50/P95/P99、峰值内存、临时文件峰值和取消后残留任务数。P50、P95、P99 分别表示 50%、95%、99% 的样本不超过该值，可同时观察典型体验与长尾等待；不应照搬其他设备的耗时阈值。

### Photo Picker 与 Android 版本适配表

| 能力 | 平台边界 | 接入与回退 |
| --- | --- | --- |
| 标准 Photo Picker | Android 13 / API 33 原生；符合条件的 Android 11 及以上设备通过模块更新获得 | AndroidX Activity 1.7.0 及以上；使用 `isPhotoPickerAvailable(context)` 做能力探测 |
| Google Play services backport | Android 4.4–10，以及支持 Google Play services 的 Android Go 11/12 | 清单声明模块依赖后可安装；不可用时由 AndroidX 回退 SAF |
| SAF 回退 | Android 4.4 / API 19 及以上 | `ACTION_OPEN_DOCUMENT` 会忽略多选最大数量；按文档 URI 处理，不能调用 MediaStore 专用打开入口 |
| Photo Picker HDR→SDR | Android 13 及以上 | AndroidX Activity 1.11.0 及以上；只为业务不支持的 HDR 类型请求转换 |
| 嵌入式 Photo Picker | Android 14 及以上且 U Extension 15；平台 API 36 | Jetpack PhotoPicker 1.0.0-alpha02 的 API 仍为实验性；会话失败或能力不足时使用标准 Picker |
| `MediaStore.open*` Picker helper | API 36，同时在 R Extension 15 提供 | authority 为 `media` 时优先；SAF URI 继续使用 `ContentResolver` |
| 选择属性约束 | API 37，同时在 U Extension 22 提供 | `PhotoPickerSelectionParams` 可限制 MIME、大小、总批次、分辨率和时长 |
| 多选数量 | `android-17.0.0_r1` 上限为 100 | 运行时读取 `getPickImagesMaxLimit()`；业务上限不得超过平台值 |
| 兼容媒体转码 | Android 12 及以上 | 受设备、来源、格式、片长和会话限制；调用方必须能处理原内容回退 |

Android 11/12 的模块更新与 Android 4.4–10 的 Google Play services backport 不是同一分发路径。backport 指把新系统能力移植到仍受支持的旧 Android 版本。是否安装成功、厂商是否提供系统回退 Picker、AndroidX 是否走 SAF，都应通过能力探测和实际启动结果记录，不能只看 `SDK_INT`。

### 与隐私权限、应用锁和 OEM 相册能力的关系

Photo Picker 适合“用户明确选择少量媒体”的流程，可以减少 `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` 整库权限申请。相册管理、备份、文件管理和云图库同步仍需依据功能选择 `MediaStore`、部分媒体访问、SAF 或特殊合规权限，不能用 Picker 模拟全库同步。

系统认证、厂商私密相册、工作资料、云媒体账号和离线状态都可能改变可见内容或让读取失败。应用只应依赖公开回调与 URI 授权：

- 标准 Picker 返回空结果时按用户未完成选择处理，不推测具体隐私原因。
- URI 打开失败时保留异常类别和当前能力路径，不记录媒体身份。
- 嵌入式会话报错时关闭会话并使用标准 Picker，不在同一页面无限重连。
- SAF 回退 URI 按其 authority 和可持久化授权处理。

OEM 差异通过 `isPhotoPickerAvailable(context)`、SDK Extension、实际 Intent 解析结果和错误分类观测。只有官方兼容方案不能覆盖且有长期验证要求时，才增加厂商专用分支。

### 与本节前文 MediaStore / MediaProvider 内容的关系

本节前文已说明 `MediaStore` 查询、`MediaProvider` 索引、FUSE、缩略图、version/generation（索引整体版本与逐项变更编号）和兼容媒体转码。这里补充选择器启动、Picker URI 生命周期、云媒体读取、HDR 请求、私有临时文件和多选队列。

媒体选择慢可按阶段定位：

1. 系统 Picker 在实验室打开慢：检查平台、模块、嵌入式/标准路径与 MediaProvider 状态。
2. 回调后描述符打开慢：检查授权、云媒体、兼容转码和取消信号。
3. 描述符已返回而首字节慢：检查管道供应、云端获取与磁盘 I/O。
4. 内容可读而准备慢：检查应用复制、解码、编码、摘要和队列等待。
5. 准备完成而发送慢：进入网络上传与服务端处理范围。

`dumpsys media.transcoding` 查看媒体转码会话；观察 Android 17 AOSP MediaProvider 时使用完整组件名 `com.android.providers.media.module/com.android.providers.media.MediaProvider`。命令、Provider version/generation 与批量媒体操作详见本文前半部分。

### Photo Picker 路径检查清单

- 是否使用 AndroidX Activity 合约，并记录平台、系统回退或 SAF 路径。
- 是否区分收到 URI、描述符返回、首字节和业务准备完成。
- API 36 及以上的 MediaStore picker URI 是否优先使用 `MediaStore.open*`。
- SAF URI 是否继续使用 `ContentResolver`，并容忍多选上限失效。
- 长时任务是否持久化读取授权，并在任务结束后释放无用授权。
- 是否监控 5000 个持久媒体授权上限及最早授权被移除的情况。
- Android 17 是否把已知的大小、批次、分辨率和时长限制传给 Picker。
- HDR 能力是否按业务路径声明，读取后是否验证最终格式。
- 是否避免为本机播放和缩略图请求兼容转码。
- 是否把系统转码缓存与应用私有临时文件分开管理。
- 云媒体失败、取消选择和页面退出能否取消所有后续任务。
- 大图、多选和视频转换是否分别限制 I/O、CPU、临时空间和网络并发。
- 线上指标是否避开原始 URI、文件名、相册名和账号信息。
- 标准 Picker 首帧与首张缩略图是否通过实验室自动化测量。

## 全文小结

MediaStore 用索引、卷、`version` 与 `generation` 管理共享媒体集合，适合轻量分页和增量同步；打开文件、生成缩略图与兼容转码则是后续独立成本。应用要把查询、游标读取、描述符打开、首字节、解码和转码分别计时，并在权限收窄、卷卸载和删除记录缺失时保留可恢复的同步路径。

Photo Picker 负责逐项选择授权，不负责把云媒体、格式转换和后台任务变成零成本。长时处理要持久化并回收 URI 授权，按业务路径准确声明 HDR/编码能力，以有容量上限的 I/O、CPU、临时存储和上传队列准备内容。系统转码缓存与应用私有副本的所有权必须分开，最终格式和可读性仍由调用方验证。


## Photo Picker 部分的参考资料

- [Android Developers：Photo Picker](https://developer.android.com/training/data-storage/shared/photo-picker)
- [Android Developers：嵌入式 Photo Picker](https://developer.android.com/training/data-storage/shared/photo-picker/embedded)
- [Android Developers：兼容媒体转码](https://developer.android.com/media/platform/transcoding)
- [Android Developers：媒体缩略图](https://developer.android.com/social-and-messaging/guides/media-thumbnails)
- [Android API：`MediaStore`](https://developer.android.com/reference/android/provider/MediaStore)
- [Android API：`PickerMediaColumns`](https://developer.android.com/reference/android/provider/MediaStore.PickerMediaColumns)
- [Android API：`PhotoPickerSelectionParams`](https://developer.android.com/reference/android/widget/photopicker/PhotoPickerSelectionParams)
- [AndroidX Activity 版本说明](https://developer.android.com/jetpack/androidx/releases/activity)
- [AndroidX PhotoPicker 版本说明](https://developer.android.com/jetpack/androidx/releases/photopicker)
- [AOSP 文档：兼容媒体转码](https://source.android.com/docs/core/media/media-transcoding)
- [AOSP 文档：MediaProvider 模块](https://source.android.com/docs/core/media/media-provider)
- [Android 17 源码：`MediaStore.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/apex/framework/java/android/provider/MediaStore.java)
- [Android 17 源码：`TranscodeHelperImpl.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/TranscodeHelperImpl.java)
- [Android 17 源码：`PhotoPickerTranscodeHelper.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/PhotoPickerTranscodeHelper.java)
- [Android 17 源码：`PhotoPickerActivity.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/photopicker/PhotoPickerActivity.java)
