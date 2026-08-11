---
title: "MediaStore 与 MediaProvider 性能治理"
chapter: "24.11"
section: "24.11"
status: ready-for-review
drafted_date: "2026-05-21"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-21"
last_verified_against: "Android Developers docs 2026-03/2026-04, AOSP source.android.com 2026-04, packages/providers/MediaProvider main"
confidence: medium
tags: [MediaStore, MediaProvider, scoped-storage, media-transcoding, thumbnails, io-performance]
related_chapters: ["6.1", "6.4", "22.6", "24.1", "24.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "AOSP结构+官方文档+素材索引去重"
gap_score: "17/20"
sources:
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/media"
  - type: official
    path: "https://developer.android.com/social-and-messaging/guides/media-thumbnails"
  - type: official
    path: "https://developer.android.com/media/platform/transcoding"
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/photo-picker"
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

## 为什么媒体库会变成性能问题

Android 17 上，一次媒体查询可能经过 `ContentResolver`、Binder、`MediaProvider`、SQLite 索引和权限过滤；打开查询结果时，还可能进入 FUSE、缩略图生成或兼容媒体转码。列表查询快，不代表首屏一定快。Cursor 遍历、Bitmap 分配和文件打开同样会占用时间。

相册、即时通信、备份和文件管理应用面对的媒体项可能达到数万甚至更多。常见问题包括：

- 在主线程查询，或者一次读取整个媒体库。
- 列表绑定时打开原文件并解码。
- 用文件系统遍历重复完成 `MediaProvider` 已经维护的索引工作。
- 把 `ContentObserver` 回调当作完整、按顺序到达的变更日志。
- 把 generation 增量查询误当成包含删除记录的同步协议。
- 未声明媒体能力，导致分享或上传路径发生计划外转码。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。Scoped Storage 和 FUSE 的演进见 6.1、6.4 节；图片加载与缓存见 22.6、24.6 节；普通文件 I/O 的线程治理见 24.1 节。

## MediaStore 访问模型与性能边界

`MediaStore` 是共享媒体的索引与访问契约。列表、筛选和同步通过索引查询完成；读取媒体内容时再打开单个 `Uri`。文件路径仍可服务于合法持有路径的旧库或原生库，但它不应成为媒体枚举入口。

| 访问方式 | 适合场景 | 主要收益 | 必须处理的边界 |
| --- | --- | --- | --- |
| `ContentResolver.query()` | 列表、筛选、搜索、同步 | 复用 `MediaProvider` 索引，只传回所需列 | 权限决定可见行；Cursor 仍需在工作线程读取并及时关闭 |
| `openFileDescriptor()` / `openInputStream()` | 上传、编辑、分享、播放单项媒体 | 以 `content://` 为稳定访问入口 | 打开操作可能包含权限检查、重定向或转码，不能在列表绑定阶段批量执行 |
| `ContentResolver.loadThumbnail()` | Android 10 及以上的网格和列表预览 | Provider 可利用已有缩略图，并按目标尺寸返回 Bitmap | 调用仍可能涉及 Binder、磁盘和解码，需要工作线程与取消信号 |
| 直接路径 / `File` / `fopen()` | 已获授权的现有媒体、旧库或原生库 | 减少第三方库迁移成本 | 路径可能失效；随机读写可能受 FUSE 影响；不能用 `DATA` 创建或移动媒体 |
| Photo Picker | 用户主动选择图片或视频 | 无需申请整个媒体库的读取权限，并支持云媒体提供方 | 返回项未必有本地路径；后台全库同步不适用 |

### 先确定应用能看到哪些媒体

Android 13 及以上把读取权限分为 `READ_MEDIA_IMAGES`、`READ_MEDIA_VIDEO` 和 `READ_MEDIA_AUDIO`。Android 14 及以上还可能只授予用户选择的图片和视频。应用自己写入的媒体在 Android 10 及以上不需要读取权限即可再次访问。Photo Picker 返回的是逐项 `Uri` 授权，访问集合与全库权限没有等价关系。

所以，“查询结果里没有某条记录”至少可能表示三种情况：文件被删除、存储卷被卸载、当前授权不可见。备份应用不能仅凭查询缺失就删除云端副本。它需要同时记录权限范围、存储卷状态和同步检查点。

`MediaStore.VOLUME_EXTERNAL` 是汇总多个外部卷的合成视图，适合跨卷展示，但它只读。插入操作与 generation 同步都应使用具体卷名：

```kotlin
val volumes: Set<String> = MediaStore.getExternalVolumeNames(context)

for (volume in volumes) {
    val images = MediaStore.Images.Media.getContentUri(volume)
    // 对每个具体卷分别查询、记录 version 和 generation。
}
```

这段代码用于发现当前已挂载的外部媒体卷。卷名可能随可移动存储的插拔而变化，不能把 `VOLUME_EXTERNAL` 传给 `getVersion(context, volume)` 或 `getGeneration(context, volume)`；两者都要求具体卷名。

### projection、分页与取消

projection 只放当前阶段需要的列。媒体网格通常先取 `_ID`、时间、MIME、宽高、视频时长和 generation；详情页再读取 EXIF 或打开文件。Cursor 返回以后，复制列表所需的小对象并关闭 Cursor，避免把 Provider 连接生命周期延长到界面层。

大图库不宜用不断增长的 `OFFSET` 翻页。前面页发生插入或删除后，OFFSET 可能造成重复或遗漏，而且 Provider 仍可能扫描被跳过的行。应用可使用“排序值 + `_ID`”作为下一页锚点。下面的代码按 `DATE_ADDED` 和 `_ID` 倒序读取图片；`_ID` 用来处理同一秒内加入的多条记录：

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

这是一种应用侧分页方案，不是 `_ID` 永久稳定性的承诺。媒体库 version 变化后，应废弃旧页锚点并重新查询。界面销毁、筛选条件变化或新查询取代旧查询时，调用 `signal.cancel()`；Provider 会在支持取消的位置尽快终止工作。

### 用 `IS_PENDING` 发布完整媒体

Android 10 及以上写共享媒体时，先插入 `IS_PENDING=1` 的记录，写完内容后再清除该标记。其他应用通常不会看到未完成的媒体，调用方也不需要等待媒体扫描重新发现自己刚写入的文件。

下面的代码展示图片发布过程，目标是保证“索引可见”和“文件写完”处于一致顺序：

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

这段代码应在 I/O 调度器上执行。失败分支删除调用方刚创建的 pending 记录，避免留下长期不可见的半成品。创建和移动媒体应使用 `DISPLAY_NAME`、`RELATIVE_PATH` 等列，不要写 `DATA`。

## MediaProvider 索引、扫描与元数据更新

`MediaProvider` 是 Mainline 可更新模块。它维护共享存储中的图片、视频、音频和下载项索引，并在查询、打开文件和扫描时执行可见性、位置元数据擦除等规则。查询结果反映的是 Provider 索引，不是一次目录实时遍历。

应用自己通过 `MediaStore.insert()` 创建媒体时，应保留返回的 `Uri`。外部程序直接写入共享目录后，索引更新可能晚于文件出现；读取端要容忍文件存在但索引尚未更新，以及索引行存在但文件打开失败的短暂状态。

### version 与 generation 各自解决什么问题

Android 17 的 `MediaStore.java` 对两者给出了不同契约：

- `getVersion(context, volume)` 返回不透明字符串。媒体库发生重大变化时，它会改变。应用不能解析格式，也不必每次查询都调用；进程启动或开始一轮同步时检查即可。
- `getGeneration(context, volume)` 返回该卷当前 generation。只要 version 没变，generation 单调递增，可做算术比较。
- 每行的 `GENERATION_ADDED` 表示记录加入索引时的 generation。
- 每行的 `GENERATION_MODIFIED` 表示该记录元数据最近变化时的 generation。
- version 改变后，旧 generation 失去比较意义，需要执行全量同步。

generation 比 `DATE_ADDED` 和 `DATE_MODIFIED` 更可靠，因为文件时间可被 `setLastModified()` 或系统时钟变化影响。它仍然只描述 `MediaProvider` 索引变化，不能替代内容哈希；元数据变化也不一定表示文件字节发生改变。

下面的流程把一轮增量查询限制在明确的 generation 区间内：

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

调用方处理并持久化所有行后，还要再次读取 version。前后 version 相同，才把 `endGeneration` 写入检查点；查询期间发生且 generation 大于 `endGeneration` 的变化会留给下一轮。代码把 Cursor 交给调用方只是为了突出查询边界，业务实现必须用 `use` 关闭它。

`android-17.0.0_r1` 的公开 API 没有删除墓碑查询。已经删除的行不会出现在 `GENERATION_MODIFIED` 查询结果中。因此可靠同步需要两条路径：

1. generation 增量查询处理新增和修改。
2. 定期分页查询该卷当前可见的 `_ID`，与本地记录对账，补偿进程停止期间遗漏的删除。

对账前确认卷仍然挂载，且媒体读取权限没有收窄。权限变化造成的“不可见”不能记为用户删除。后续 37.1 SDK Extension 增加了 deleted-files 相关 API，但它不属于 `android-17.0.0_r1` 锚点。

### `ContentObserver` 只负责唤醒重新查询

Android 11 及以上的 `ContentObserver.onChange()` 可以接收一组 `Uri` 和插入、更新、删除标记。Provider 也可以只对集合根 `Uri` 发送通知。进程未运行时不会为应用保存完整通知序列，回调的合并、顺序和粒度也不足以构成持久同步协议。

推荐处理方式是：

- 前台收到通知后，取消已经过时的列表查询，并刷新受影响窗口。
- 后台同步把通知转换成“安排一轮 generation 检查”，不直接根据回调参数修改永久记录。
- 高频通知可合并，合并时长依据应用测量、交互要求和设备负载确定，不写固定毫秒值。
- 进程重新启动时从持久化的 version/generation 检查点恢复，不依赖上一次 Observer 回调。

## Scoped Storage、FUSE 与批量操作

Android 11 及以上允许应用通过直接路径和原生 `fopen()` 访问其有权读取的共享媒体。`MediaProvider` 的 FUSE 守护程序仍可在文件操作时执行访问检查、位置元数据擦除和兼容转码。

官方性能说明给出的边界很具体：顺序读取现有媒体时，直接路径与 `MediaStore` 访问性能相近；通过直接路径做随机读写时，耗时最多可能达到 `MediaStore` 路径的约两倍。这个数字是上限提示，不是所有设备的固定成本。应用需要在目标机型上按访问模式测量。

路径访问还受以下约束：

- `DATA` 可用于打开当前已存在且有权访问的媒体，但路径可能因移动、卸载卷或权限变化失效。
- 创建和更新位置应使用 `DISPLAY_NAME` 与 `RELATIVE_PATH`，不能写 `DATA`。
- Photo Picker 或云媒体提供方返回的 `Uri` 不保证对应本地路径。
- 递归扫描目录再逐个读取长度、EXIF，随后查询 `MediaStore`，会重复索引工作并产生大量小 I/O。

列表和同步先查询轻量元数据。只有上传、编辑、播放或详情展示需要文件内容时，才打开相应 `Uri`。

### 批量用户授权有 Android 17 的明确上限

Android 11 及以上提供以下请求：

- `createWriteRequest()`：请求一组媒体项的写权限。
- `createFavoriteRequest()`：修改收藏状态。
- `createTrashRequest()`：移入或移出回收站。
- `createDeleteRequest()`：立即删除。

每个 `Uri` 都必须由 `MediaStore` authority 托管，并指向带 `_ID` 的具体媒体项。系统结果返回前，请求的收藏、回收站或删除操作已经完成。`createWriteRequest()` 返回的写授权与 Activity 生命周期相关，不是可持久化、可授予前缀的权限。

Android 17 中，目标 SDK 为 Android 16 及以上的应用每次请求最多传入 2000 个 `Uri`，超出会抛出 `IllegalArgumentException`。2000 是 API 限制，不是推荐的产品批次。应用应根据确认界面的可理解程度、失败恢复和设备测量决定一次让用户处理多少项。

下面的代码在创建系统请求前校验 Android 17 的输入边界：

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

这段校验防止集合 `Uri` 和超限列表进入请求。用户取消时不能修改本地媒体状态；收到 `RESULT_OK` 后重新查询受影响项，不要假定所有旧缓存仍有效。

## 缩略图、预览图与解码成本

媒体网格需要的是接近控件物理像素尺寸的预览图。读取原图再缩放会增加文件读取、解码时间和 Bitmap 峰值。Android 10 及以上已有 `ContentResolver.loadThumbnail()`，Provider 可以复用已有缩略图，也可以根据目标尺寸生成结果。

| API | 适合场景 | 成本与限制 |
| --- | --- | --- |
| `ContentResolver.loadThumbnail()` | 已有 `content://` `Uri` 的图片或视频网格 | 可能发生 Binder、文件读取和解码；支持目标尺寸与 `CancellationSignal` |
| `ThumbnailUtils` | 合法持有 `File` 的旧路径代码 | 需要打开文件并生成缩略图；不适用于云媒体 `Uri` |
| `ImageDecoder` | 需要自定义采样、色彩处理或动画图像 | 可能读取原始资源；必须设置目标尺寸或采样 |
| `BitmapFactory` | 兼容静态图片旧代码 | 先读边界再采样，仍需控制流和 Bitmap 生命周期 |
| `MediaMetadataRetriever` | 视频指定时间帧、内嵌封面、详情页 | 解复用和解码可能较重，不适合网格中并发提取大量帧 |

下面这个包装函数只负责单次加载。列表层持有 `CancellationSignal`，条目离开预取窗口时取消：

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

`loadThumbnail()` 内部会调用 Provider 的类型化资源打开接口，并在必要时再次缩放。它返回 Bitmap，因此仍应在受限并发的工作线程执行。取消可能以 `IOException` 结束，调用方要把取消和读取失败分开统计。

查询、缩略图、上传和转码不宜共享无界执行器。缩略图同时消耗 Binder、磁盘、CPU 和图形内存；并发数应通过首屏时间、滚动丢帧、内存峰值和设备温度测量确定。固定套用 CPU 核数公式也可能在低内存设备上产生过多 Bitmap。

缩略图缓存键至少应包含：

- 媒体 `Uri`。
- `GENERATION_MODIFIED` 或应用能够验证的内容版本。
- 目标物理像素宽高。
- 裁剪、旋转、色彩和 HDR/SDR 处理参数。

同一 `Uri` 的小网格图和详情预览不能共用一个无尺寸缓存键。generation 改变时，只失效对应媒体的派生图；version 改变时，重新校验整个 MediaStore 缓存索引。

## 兼容媒体转码与 HDR → SDR 退化路径

Android 12 引入兼容媒体转码。设备可保存 HEVC 或 HDR 媒体；读取方不支持源格式时，`MediaProvider` 与媒体转码服务可以返回兼容版本。首次转码需要编解码和文件 I/O，后续读取才可能复用系统缓存。等待时间取决于片长、分辨率、格式、硬件编解码能力、温度和系统负载，不能用旧设备的单一耗时作为 Android 17 预算。

平台文档建议避免为以下本机用途触发兼容转码：

- 设备本机播放。播放器通常可以直接使用设备解码能力。
- 生成缩略图。缩略图接口可直接从源媒体产生预览。

兼容转码适合明确的离机边界，例如服务端不接受 HEVC，或者接收方协议只支持 SDR。上传、导出和分享流程应显示等待与取消状态，并分别测量“打开描述符等待”和“后续读取”耗时。

### 按调用路径声明媒体能力

`ApplicationMediaCapabilities` 用于描述当前代码路径支持的视频 MIME 和 HDR 类型。把它放入 `MediaStore.EXTRA_MEDIA_CAPABILITIES`，再通过 `openTypedAssetFileDescriptor()` 打开媒体，平台便能据此判断是否需要转换。

下面的示例表示当前上传路径可以处理 HEVC，但不能处理 HDR10：

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

调用级声明优先于应用资源中的通用声明，适合“本机播放器支持 HDR、上传服务只接受 SDR”这类不同路径。能力声明过宽可能把无法处理的源格式交给应用；声明过窄会增加转码。未声明的格式由平台决定，不应依赖某个版本的默认选择。

资源级声明会影响应用的多条媒体访问路径。仅在各路径能力一致时使用，否则缩略图或本机播放也可能受到不需要的转换影响。

### Photo Picker 的 HDR → SDR 是显式选择

Photo Picker 可以返回设备本地或云媒体提供方的 `Uri`。HDR 视频默认不会自动转成 SDR。Android 13 及以上可通过 AndroidX Photo Picker 请求中的媒体能力显式选择兼容转码；如果发生转换，应用拿到的是可读取的结果 `Uri`。

应用需要据业务路径选择：

- 播放、编辑和上传均支持 HDR：声明支持相应 HDR 类型，保留源质量。
- 上传协议只接收 SDR：为该选择请求声明不支持的 HDR 类型，并在提交上传前处理等待。
- 只显示缩略图：直接请求缩略图，不为预览请求整段视频转码。

需要跨重启继续处理 Picker 结果时，及时调用 `takePersistableUriPermission()`，并为授权失效准备重新选择流程。不要把返回 `Uri` 转换成本地路径；云媒体和系统维护的转码结果都不保证存在可长期依赖的路径。

## 线上排查与 Perfetto / dumpsys 观察点

单个“查询耗时”无法区分 Binder 等待、Provider 执行、Cursor 读取和应用对象构造。应用应给每个阶段单独计时，并用 `Trace.beginSection()` 或 AndroidX tracing 添加 Perfetto 可见区间。

建议记录以下字段，媒体身份使用散列或内部编号，避免把完整 `Uri` 和文件名写入日志：

- 查询：卷、集合、查询类型、projection 列数、分页方式、limit、返回行数、`query()` 耗时、Cursor 遍历耗时、取消结果。
- 缩略图：目标像素、媒体类型、内存/磁盘缓存命中、调用耗时、取消数、Bitmap 分配字节。
- 文件打开：打开 API、读取目的、描述符等待、首字节、总读取量与总耗时。
- 转码：能力声明类别、源格式、下游要求、描述符等待、读取耗时、取消与失败原因。
- 同步：卷、version 是否变化、起止 generation、变更行数、ID 对账差异、Observer 唤醒次数。

Perfetto 采集至少包含应用进程和 `com.android.providers.media.module` 进程的调度、CPU 频率、Binder、文件系统、块设备 I/O 与内存信息。应用自己的 trace 区间负责区分 query、Cursor 读取、缩略图、文件打开和转码。若没有明确启用或插入 SQLite 追踪，不要假定界面一定存在可直接归因的“database 轨道”。

### Android 17 的 Provider 诊断命令

`android-17.0.0_r1` 的清单把 `MediaProvider` 注册为包
`com.android.providers.media.module` 中、authority 为 `media` 的
`ContentProvider`。它不是名为 `media_provider` 的 ServiceManager 服务，
所以 `adb shell dumpsys media_provider` 不是该源码锚点下的可靠命令。

先列出匹配的 Provider 状态：

```bash
adb shell dumpsys activity providers \
  com.android.providers.media.module/.MediaProvider
```

这条命令用于确认设备上的包名、组件名、进程和发布状态。OEM 改名时，可先运行
`adb shell dumpsys activity providers | grep -i media` 查找设备组件。

再调用 Provider 自身的 `dump()`：

```bash
adb shell dumpsys activity provider \
  com.android.providers.media.module/.MediaProvider
```

Android 17 源码中的输出包含缩略图尺寸、已连接卷、用户缓存、转码辅助器、
Photo Picker 数据库与同步控制器、访问日志等状态。字段属于调试实现，不构成
应用 API；不同 Mainline MediaProvider 版本可能变化。

诊断顺序可以按现象缩小范围：

1. 仅 `query()` 阶段慢：查看调用线程、Binder 往返、Provider CPU 和磁盘等待。
2. Cursor 返回快而列表慢：查看 Cursor 遍历、对象分配、排序后的界面更新。
3. 网格慢：暂停缩略图后复测，再检查解码并发、Bitmap 内存与取消是否生效。
4. 打开视频慢：比较普通文件打开与带媒体能力的类型化打开，确认是否等待转码。
5. 扫描期间波动：检查卷挂载、Provider I/O、数据库写入和 Observer 唤醒密度。

## 大图库首屏加载与分页同步策略

大图库需要三条相互限流的流水：

1. 索引查询只生成当前页的轻量列表项。
2. 缩略图加载跟随可见窗口和经过测量的预取窗口。
3. generation 同步与删除对账在后台维护持久数据。

首屏查询完成后即可提交列表。EXIF、云端备份状态、内容哈希和视频指定帧按需读取。预取距离依据滑动速度、缩略图 P95、内存预算和取消率调整，不使用固定“滚动百分比”。

快速滑动时优先取消已经离开预取窗口的缩略图，保留当前可见项。新筛选条件到来时取消旧 Cursor 查询。界面中的稳定键可使用“卷名 + `_ID`”，但 MediaStore version 改变后必须重新建立映射。

后台同步建议采用以下状态机：

```text
检查卷是否挂载与权限范围
  → 比较 version
  → version 改变：全量分页同步
  → version 相同：按 generation 查询新增和修改
  → 持久化检查点
  → 按业务周期执行可见 ID 对账
```

这段状态机用于区分全量恢复、增量更新和删除补偿。每一步完成后再保存对应检查点，失败时从上一份完整检查点恢复。

`IS_PENDING=1` 的其他应用媒体默认不在普通查询结果中，回收站项目也默认被过滤。需要管理回收站的应用应显式使用对应查询参数，并把该状态与普通图库分开。上传任务在打开文件前再次查询记录并处理 `FileNotFoundException`、`SecurityException`，因为排队期间媒体可能被删除、移出可见范围或卸载。

性能验收应覆盖：

- 冷启动与热启动的首屏时间。
- 小库、大库和多个外部卷。
- 快速滚动后的无效缩略图完成数。
- 扫描、云同步或视频转码并行时的 P95/P99。
- 权限从完整访问切换为部分访问。
- SD 卡在同步中卸载与重新挂载。
- version 变化后的全量恢复，以及进程停止期间发生删除后的 ID 对账。

## MANAGE_EXTERNAL_STORAGE 类 App 的性能与合规边界

`MANAGE_EXTERNAL_STORAGE` 是特殊应用访问权限，面向文件管理、备份与恢复、防病毒、设备内文件搜索等需要广泛文件访问的主要功能。Google Play 会审核其用途；只有无法有效使用 MediaStore 或 Storage Access Framework 的合规场景才应申请。

这项权限不会让目录遍历或随机 I/O 自动变快，也不会取消 FUSE 的所有工作。可见范围扩大后，待扫描条目更多，启动时全盘遍历会增加 I/O、电量、温度和隐私成本。

具备全文件访问的应用仍应分类处理：

- 图片、视频和音频：优先查询 `MediaStore` 索引，按需打开内容。
- 文档和普通文件：根据功能使用 Storage Access Framework 或文件系统。
- 全盘扫描：保存目录与文件检查点，响应卷挂载变化，并按电量、温度和前后台条件限流。
- 媒体变更：避免为每个文件主动触发重复扫描，也不要与系统媒体扫描同时进行大批元数据回写。

发布前应以当前 Google Play 的 All files access 政策重新核对资格。平台权限可用不代表应用商店一定接受；性能设计也不能以审核一定通过为前提。

## 实战检查清单

- 查询是否按具体卷、必要列和稳定锚点分页，并带 `CancellationSignal`。
- 是否区分完整媒体权限、部分媒体权限、Picker 授权和应用自有媒体。
- version 改变时是否全量同步；version 未变时是否使用 generation。
- 是否承认 Android 17 r1 generation 不含删除墓碑，并安排 ID 对账。
- `ContentObserver` 是否只唤醒重新查询，没有充当持久事件日志。
- 是否避免在 RecyclerView 或 Compose 条目绑定期间同步打开文件、提取视频帧或解码原图。
- 缩略图缓存键是否包含内容版本、目标尺寸和变换参数。
- 批量请求是否使用具体 item `Uri`，并遵守 Android 17 的 2000 项上限。
- 媒体能力是否按播放、上传、导出等路径分别声明。
- 是否为类型化文件打开与转码等待提供取消、进度和分阶段指标。
- Perfetto 区间、Provider dump 和应用指标能否相互对应。
- 申请 `MANAGE_EXTERNAL_STORAGE` 前是否验证功能必要性与当前商店政策。

## 参考资料

- [Android Developers：访问共享存储中的媒体](https://developer.android.com/training/data-storage/shared/media)
- [Android Developers：媒体缩略图](https://developer.android.com/social-and-messaging/guides/media-thumbnails)
- [Android Developers：兼容媒体转码](https://developer.android.com/media/platform/transcoding)
- [Android Developers：Photo Picker](https://developer.android.com/training/data-storage/shared/photo-picker)
- [Android Developers：管理设备上的所有文件](https://developer.android.com/training/data-storage/manage-all-files)
- [Android API：`ContentObserver`](https://developer.android.com/reference/android/database/ContentObserver)
- [AOSP 文档：MediaProvider 模块](https://source.android.com/docs/core/media/media-provider)
- [AOSP 文档：兼容媒体转码](https://source.android.com/docs/core/media/media-transcoding)
- [AOSP 文档：Scoped Storage](https://source.android.com/docs/core/storage/scoped)
- [Android 17 源码：`MediaStore.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/apex/framework/java/android/provider/MediaStore.java)
- [Android 17 源码：`MediaProvider.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/MediaProvider.java)
- [Android 17 源码：`FuseDaemon.cpp`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/jni/FuseDaemon.cpp)
- [Android 17 源码：MediaProvider 清单](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/AndroidManifest.xml)
