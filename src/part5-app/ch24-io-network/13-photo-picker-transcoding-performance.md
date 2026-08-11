---
title: "Photo Picker、媒体转码与缓存治理"
chapter: "24.13"
status: ready-for-review
drafted_date: "2026-05-22"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "Android Developers docs 2026-05, AOSP MediaProvider main, source.android.com 2026-04"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/photo-picker"
  - type: official
    path: "https://developer.android.com/training/data-storage/shared/photo-picker/embedded"
  - type: official
    path: "https://developer.android.com/media/platform/transcoding"
  - type: official
    path: "https://developer.android.com/social-and-messaging/guides/media-thumbnails"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/media/media-transcoding"
  - type: aosp-doc
    path: "https://source.android.com/docs/core/media/media-provider"
  - type: aosp
    path: "packages/providers/MediaProvider/apex/framework/java/android/provider/MediaStore.java"
  - type: aosp
    path: "packages/providers/MediaProvider/src/com/android/providers/media/TranscodeHelperImpl.java"
  - type: aosp
    path: "packages/providers/MediaProvider/src/com/android/providers/media/photopicker/PhotoPickerActivity.java"
  - type: book-structure
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: book-structure
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [photo-picker, mediaprovider, transcoding, storage, io-performance]
related_chapters: ["12.1", "20.10", "22.6", "22.35", "24.12", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "官方文档/每日信息/素材驱动/AOSP结构"
---

# 24.13 Photo Picker、媒体转码与缓存治理

## Photo Picker 负责选择授权，后续处理仍在应用侧

Photo Picker 把“用户允许应用读取哪些图片或视频”交给系统界面。临时选择媒体的应用无需申请整个媒体库的读取权限，也不用维护一套相册索引和权限页面。

选择完成后，应用仍需处理：

- 返回 `Uri` 的授权时长和持久化。
- 本地媒体与云媒体不同的打开延迟。
- HEVC、HDR 和业务目标格式之间的转换。
- 大图采样、视频读取、上传与取消。
- 应用私有临时文件和失败任务的清理。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，重点是选择完成后的应用路径。`MediaStore` 索引、FUSE、缩略图和兼容媒体转码原理见 24.12 节；图片解码与 Bitmap 缓存见 22.6、22.35 节；文件 I/O 与网络上传见 24.1、24.6 节。

## Photo Picker 的性能边界

标准 Photo Picker 的返回值是只读 picker `Uri`。它可以查询
`MediaStore.PickerMediaColumns` 中有限的元数据，也可以按读取模式打开；调用方不能
把它当作可写文件路径。云媒体提供方返回的内容还可能在打开时通过网络获取。

常见选择入口的差异如下：

| 路径 | 适合场景 | 授权与内容边界 |
| --- | --- | --- |
| Photo Picker | 头像、聊天附件、发帖、反馈等用户主动选择 | 只授权所选媒体，可包含云媒体；AndroidX 可自动选择平台、系统回退或 SAF |
| SAF / `ACTION_OPEN_DOCUMENT` | 任意文档和需要通用文件浏览的流程 | URI authority 来自文档提供方；多选上限和媒体界面由 DocumentsUI 与提供方决定 |
| 厂商相册 Intent | 已有厂商专用协议的产品 | 返回格式和授权行为需要逐设备验证，不适合作为通用默认路径 |
| 应用自建媒体页 | 相册管理、备份和长期媒体库同步 | 由应用负责权限、分页、缩略图、云端同步和索引一致性 |

使用 AndroidX Activity 1.7.0 或更高版本的 `PickVisualMedia` /
`PickMultipleVisualMedia`，可以让库选择设备支持的 Photo Picker；不可用时，库会
回退到 `ACTION_OPEN_DOCUMENT`。单选接入可以保持很小：

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

这段代码只记录选择结果。回调发生时，视频还未必已在本地准备完成；
`onMediaSelected()` 应把 `Uri` 交给后台准备流程，不能在主线程立即读取视频。

### 把一次选择分成五个阶段

性能数据应按以下顺序记录：

```text
启动选择器
  → 用户确认选择
  → 应用收到 URI
  → 描述符打开
  → 首字节可读
  → 业务数据准备完成
```

这段阶段图用于确定等待发生的位置。标准 Picker 运行在系统 Activity 中，普通应用
无法在生产环境准确观测“系统网格首张缩略图出现”的时间；点击到回调还包含用户
浏览和选择的时间。Picker 启动与首张缩略图应通过 UiAutomator、Macrobenchmark
和 Perfetto 在实验室测量，不能从线上会话时长反推。

`Uri` 回调到描述符返回的时间可能包含云媒体下载或转码。描述符返回后还要单独测
首字节，因为返回对象可能由管道提供内容。只有业务上传体、编辑输入或本地副本
可用时，才算完成媒体准备。

### API 36 及以上优先使用 `MediaStore.open*`

Android 16 / API 36 起，`MediaStore.openFileDescriptor()`、
`openAssetFileDescriptor()` 和 `openTypedAssetFileDescriptor()` 专门处理
`ACTION_PICK_IMAGES` 返回的 MediaStore URI。Android 17 源码明确建议优先使用
这些入口。AndroidX 回退到 SAF 时，URI authority 不再是 `media`，仍需使用
`ContentResolver`。

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

调用方拥有返回的描述符，使用后必须关闭。用户撤销任务、页面退出或新选择替代旧
选择时调用 `signal.cancel()`。云端失败、权限撤销、Provider 崩溃和媒体被删除都
应作为可恢复的读取失败处理。

Picker URI 可查询 `SIZE`、`DISPLAY_NAME`、`MIME_TYPE`、`DURATION_MILLIS`、
`WIDTH`、`HEIGHT`、`ORIENTATION` 等只读列。`SIZE` 和路径信息只能作为提示；
云媒体可能依赖网络，应用也不应根据 `DATA` 拼装文件路径。

### 临时授权与持久授权

默认授权持续到设备重启或应用停止。后台上传、WorkManager 恢复、草稿跨进程重启
等场景应在收到 URI 后调用：

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

这段代码延长读取授权，不会把远端媒体下载到本地。Android 平台允许每个应用同时
保留最多 5000 个媒体授权；继续新增时会移除最早的授权。草稿删除、任务结束和账号
退出时应调用 `releasePersistableUriPermission()`，并在后台任务开始前重新验证
读取能力。

### Android 17 把业务限制前移到 Picker

`android-17.0.0_r1` 的 `MediaStore.getPickImagesMaxLimit()` 返回 100。应用的
多选数量不能超过平台上限；设备回退到 `ACTION_OPEN_DOCUMENT` 时，系统会忽略
AndroidX 传入的最大数量，因此回调后仍需执行数量校验。

API 37 的 `PhotoPickerSelectionParams` 还能按 MIME、单项大小、批次总大小、
分辨率和视频时长限制可选内容。超出限制的媒体会在 Picker 中禁用，减少选择完成
后才拒绝文件的情况。业务阈值必须来自服务端协议、磁盘预算或产品规则。

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

这段代码使用 API 37 能力；同一 API 也通过 Android 14 的 U SDK Extension 22
提供。旧版本需要在选择后校验。Picker 的元数据限制可以减少无效选择，却不能保证
云端内容已经下载，也不能代替打开、读取和上传阶段的错误处理。

## 嵌入式 Photo Picker 的接入成本

嵌入式 Photo Picker 把系统媒体网格放在应用页面中的 `SurfaceView`，通过
`setChildSurfacePackage()` 承载系统提供的界面。宿主 Activity 保持 resumed，
可以连续接收选择与取消选择事件；媒体内容的授权边界与标准 Picker 相同。

该能力要求 Android 14 及以上且 U SDK Extension 至少为 15。平台类从 API 36
公开，同时可通过扩展回传到 Android 14。Jetpack `androidx.photopicker` 仍标记
`ExperimentalPhotoPickerApi`，升级依赖时应复核回调和生命周期行为。不满足条件
或会话打开失败时，使用标准 Photo Picker。

嵌入式路径需要单独处理四类成本：

- 宿主首帧：输入区、附件条和 Picker 容器属于应用绘制。
- 会话建立：Jetpack 需要连接系统服务、创建 Surface 并取得系统 SurfacePackage。
- 媒体网格：索引、缩略图和云媒体仍由系统 Picker 加载。
- 连续选择：每次授权和撤销都可能更新附件列表、校验规则和准备队列。

因此，`Activity.onCreate()` 到首帧只覆盖宿主页面。会话打开、Picker 内容可见和
首次选择回调应分别测量。系统没有向应用提供稳定的“首张缩略图已绘制”业务回调，
这一项仍需借助界面自动化和 Perfetto。

### 连续选择需要双向维护状态

Jetpack 提供 `onUriPermissionGranted` 和 `onUriPermissionRevoked`，应用据此
更新附件列表。应用主动调用 `deselectUri()` / `deselectUris()` 时，Picker 不会
再通过 revoked 回调重复通知；应用必须同时删除自己的选中状态。忽略这一点会造成
附件条与系统网格的选择不一致。

选择事件只应安排后台准备任务。缩略图预览、元数据查询、云媒体打开和上传准备都
不应在回调的主线程中完成。用户取消选择后，依次取消该 URI 的打开信号、解码任务
和尚未开始的上传任务。

折叠屏、多窗口、横竖屏和输入法显示会改变宿主与 `SurfaceView` 尺寸。应用应保存
选择 URI 和页面模式，把窗口尺寸更新交给现有会话；不要因为普通布局变化反复销毁
并创建嵌入式 Picker。退出页面时关闭会话并释放监听，防止 Surface 和回调继续持有
Activity。

## 视频转码的时间与存储成本

Photo Picker 的 HDR→SDR 与 MediaProvider 的兼容媒体转码使用相近的媒体能力
描述，却属于两个入口：

| 入口 | 启用方式 | 返回行为 | Android 17 边界 |
| --- | --- | --- | --- |
| Photo Picker HDR→SDR | 启动 Picker 时通过 AndroidX `MediaCapabilities` 声明支持的 HDR 类型 | 发生转换时，Picker 返回转码结果 URI | Android 13 及以上；视频最长 1 分钟；结果缓存会在设备空闲维护时清理 |
| MediaProvider 兼容转码 | 打开媒体时传入 `ApplicationMediaCapabilities`，或使用资源声明 | 支持源格式时返回原内容；不支持时可能返回 AVC/SDR 或缓存结果 | Android 12 及以上；设备、格式、来源、片长和系统资源都影响是否转换 |

两条路径默认都不会因为应用“可能不支持”就无条件转换。应用必须准确声明能力，
并在接收端检查最终媒体能否处理。旧 Pixel 3 的固定耗时不能作为 Android 17 的
性能预算；片长、分辨率、源格式、编解码器、存储、温度和并发负载都会改变等待。

### Photo Picker HDR→SDR

AndroidX Activity 的
`PickVisualMediaRequest.Builder.setMediaCapabilitiesForTranscoding()` 接收
`MediaCapabilities`。列出的 HDR 类型表示应用支持；未列出的类型视为不支持。
传入 `null` 会关闭该请求的转码。

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

这段代码需要包含该 API 的 AndroidX Activity 版本，官方要求
1.11.0-alpha01 或任意包含此 API 的后续 alpha、beta、RC、稳定版。Picker
执行转换时会返回转换后的 URI；调用方不能通过解析 URI 路径判断是否命中缓存。

转码会创建新文件并占用处理时间，且只处理不超过 1 分钟的视频。超过限制、设备
能力不足或平台未执行转换时，应用可能拿到原内容。上传协议只接受 SDR 时，读取后
仍需验证轨道色彩信息，并为不支持的结果提供应用侧转换或拒绝流程。

### MediaProvider 兼容转码

Android 17 延续 Android 12 引入的兼容转码。AOSP 文档规定的标准来源是 OEM
原生相机写入主外部卷 `DCIM/Camera/` 的本机视频；二级存储以及通过邮件、SD 卡等
外部来源导入的媒体不在标准支持范围内。厂商只能通过资源覆盖增加 `DCIM/` 下的
路径。

标准转换包含 HEVC 8-bit→AVC，以及设备具备色调映射插件时的 HDR10+ 10-bit→
AVC SDR。MediaStore、直接路径、SAF、使用 MediaStore URI 的系统分享和 MTP/PTP
都可能进入转码。取出 SD 卡以及 Nearby Share、蓝牙等设备间传输路径会绕过它。

平台还限制连续转码会话和累计运行时间；AOSP 文档给出的限制是连续 10 个会话、
累计 3 分钟，两项都超出后返回原描述符。设备缺少 HDR 插件时也会返回原描述符。
因此，多选上传不能假定所有不支持的媒体都会被系统转换。

兼容转码只适合离机上传、导出和分享。本机播放直接使用设备解码器；网格预览使用
缩略图 API。资源级 `media_capabilities.xml` 会影响应用的多条读取路径，容易让
本机播放或缩略图发生计划外转换。按打开调用传入
`ApplicationMediaCapabilities` 更适合能力不同的业务路径，具体代码见 24.12。

## MediaProvider 与缓存清理链路

媒体选择后可能出现三类缓存，所有权和清理责任不同：

| 层次 | 内容 | 清理者 | 应用能否依赖 |
| --- | --- | --- | --- |
| MediaProvider 兼容转码缓存 | FUSE 读取时生成的 AVC/SDR 文件 | MediaProvider 与系统存储管理 | 不能依赖路径、存活时间或命中 |
| Photo Picker HDR 转码缓存 | Picker 返回的兼容视频 | Picker 的设备空闲维护 | 只能依赖仍有效的 URI 授权，不能依赖缓存文件持续存在 |
| 应用私有临时数据 | 上传副本、压缩结果、编辑中间文件、业务缩略图 | 应用 | 必须有持久记录、容量预算和删除策略 |

Android 17 的 `TranscodeHelperImpl.java` 把兼容转码文件放在
`/storage/emulated/<user>/.transforms/transcode/`，以 MediaStore 行 ID 生成内部
文件名，并实现 `freeCache()` 与单项删除。这个路径属于实现细节，应用无权据此
定位或清理文件，也不能把一次命中延迟推断成未来仍会命中。

同一版本的 `PhotoPickerTranscodeHelper.java` 把 Picker HDR 转码结果放在
`/storage/emulated/<user>/.picker_transcoded/`，按媒体提供方 authority 与媒体 ID
生成缓存名，并提供按容量、全量和单项清理入口。两种目录都归 MediaProvider 模块
管理，却服务于不同的请求路径；应用只能通过有效 URI 读取，不能直接访问这些目录。

系统设备空闲维护不会处理应用的 `cacheDir`、草稿数据库和失败上传。应用应给每个
私有临时文件记录：

- 业务归属，例如草稿、消息或编辑任务 ID。
- 原始 picker URI 与持久授权状态。
- 文件用途与是否可重新生成。
- 创建时间、最近访问时间和任务状态。
- 预期大小、已写大小与校验结果。

发送完成、用户撤销选择、草稿删除和账号退出都应触发对应清理。失败任务是否保留
副本、保留多久，由重试承诺和存储预算决定，不能统一套用一个时间值。

### 什么时候复制到应用私有目录

服务端接受源格式、上传库支持顺序流且任务不需要随机访问时，可直接从 picker URI
上传，避免额外副本。以下情况更适合复制一次：

- 需要断点续传或多次重试，而源 URI 可能依赖网络。
- 图片编辑、视频分析或编码器需要 seek。
- 任务要跨进程重启，且不能接受系统缓存清理后重新下载或重新转码。
- 需要在上传前生成稳定摘要并核对完整内容。

复制过程使用 `.partial` 临时文件，写完并校验后再切换为 ready；进程中止时，启动
清理只删除没有活跃任务引用的 partial 文件。`cacheDir` 仍可能在存储压力下被系统
删除。业务承诺必须跨重启保留的内容，应放在应用管理的私有目录，并由数据库状态
控制删除。

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

这段状态图把 URI 授权、系统打开、应用副本和上传分开。每次状态变化与文件重命名
完成后再提交数据库事务，恢复逻辑便能判断继续任务还是删除孤立文件。

## 大图、多选和云端媒体的 I/O 与内存压力

多选要形成一个有容量限制的任务队列，不能把单选代码按 URI 数量同时启动。选择
数量、源文件总字节、解码后的 Bitmap、转换后的临时文件和上传并发属于不同预算。

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

这段代码只用于 authority 为 `media` 的 picker URI，并及时关闭 Cursor。
`MIME_TYPE`、`SIZE` 和 `DURATION_MILLIS` 从 API 33 / R Extension 2 可用；
`WIDTH`、`HEIGHT` 从 API 34 / R Extension 5 可用，所以投影先做能力判断。
AndroidX 回退到 SAF 时，使用 `ContentResolver.getType()` 与
`OpenableColumns.SIZE` / `DISPLAY_NAME`，不要请求 Picker 专用列。即使列已定义，
值也可能为空；`SIZE` 更不能代替流式读取时的实际字节计数。元数据适合做排队和
界面提示，安全校验仍需在读完整个内容后完成。

### 图片路径

网格预览使用 `ContentResolver.loadThumbnail()` 或支持 `content://` 的图片库，
传入控件所需像素尺寸。上传服务接受 HEIC、AVIF、JPEG 或 PNG 源文件时，直接流式
上传，避免生成 Bitmap。

只有裁剪、缩放、去除元数据或转换格式时才解码。解码器应设置目标尺寸或采样，
再依据 Bitmap 字节数限制并发。图片文件的压缩字节数无法预测解码内存，宽高、
像素格式、色彩空间和中间 Bitmap 都会影响峰值。

### 视频路径

视频预览使用缩略图或播放器，不为网格提取多个指定时间帧。上传不需要转封装或
转码时直接顺序读取；需要格式转换时，把转换任务放入独立队列，并把输入读取、
编码输出与临时文件空间同时计入预算。

### 云媒体路径

系统 Picker 会尝试预加载已选云媒体。Android 17 的
`PhotoPickerActivity.java` 会在离线且云端媒体未缓存时提示错误，并从选择中移除
不可用项。即便 Picker 返回 URI，应用打开时仍可能遇到网络变化、云账号变化或
缓存清理。

界面至少区分：

- 已选择：应用收到 URI。
- 正在准备：查询、云端获取、打开或转换尚未完成。
- 可发送：业务已经取得可读流或验证完成的本地副本。
- 失败：可以重试、重新选择或移除。

URI 打开和顺序复制属于 I/O；图片缩放、编码和哈希属于 CPU；上传由网络调度器
管理。三个队列分别限流，选择数量增加时不线性增加线程。用户撤销某项时，取消该
项尚未完成的打开、解码、转换和上传请求。

## 可观测性与回归防护

线上数据和实验室数据要分开设计。标准 Picker 的系统网格绘制对调用应用不可见，
生产埋点不能声称测到了 Picker 首帧或首张缩略图。应用可观测的阶段如下：

| 指标 | 起点与终点 | 说明 |
| --- | --- | --- |
| `picker_session_ms` | 启动请求→收到结果 | 包含用户浏览时间，只用于路径完成率和异常长会话，不是启动性能 |
| `selection_to_open_ms` | 收到 URI→描述符返回 | 包含授权检查、Provider、云端获取或转码等待 |
| `open_to_first_byte_ms` | 描述符返回→首字节读取 | 区分描述符建立与内容供应 |
| `prepare_queue_ms` | 任务入队→开始处理 | 判断 I/O 或 CPU 队列拥塞 |
| `prepare_work_ms` | 开始处理→业务可用 | 复制、解码、压缩、转码或摘要计算 |
| `upload_ms` | 网络请求开始→完成 | 与本地准备分开 |
| `temp_bytes` | 任务状态变化时采样 | 观察 partial、ready 和失败副本占用 |

事件公共字段包括 Picker 路径、Android 版本、SDK Extension、是否嵌入式、是否
SAF 回退、媒体类型、数量、声明的能力类别、持久授权结果和取消阶段。不要记录原始
URI、文件名、相册名或云账号。

应用无法仅从 URI 可靠判断系统是否执行过兼容转码。实验室可结合：

```bash
adb shell dumpsys media.transcoding
adb shell dumpsys activity provider \
  com.android.providers.media.module/com.android.providers.media.MediaProvider
```

第一条命令查看当前和历史媒体转码会话；第二条查看 AOSP Android 17
MediaProvider 的卷、转码辅助器和访问状态。OEM 或 Google MediaProvider 的组件名
可能不同，应先用 `adb shell dumpsys activity providers | grep -i media` 定位。

Perfetto 采集应用、MediaProvider 和媒体服务的调度、Binder、CPU 频率、文件系统、
块设备 I/O、内存与网络，并在应用代码中标记 URI 打开、首字节、复制、解码、编码
和上传区间。标准 Picker 的启动和网格内容使用 Macrobenchmark / UiAutomator
驱动；嵌入式路径还要记录宿主首帧、会话打开与 Surface 尺寸变化。

### 回归覆盖

设备和能力组合至少包括：

- Android 13 平台 Picker。
- Android 14 及以上、U Extension 15 的嵌入式 Picker。
- Android 17 的 `PhotoPickerSelectionParams` 和 `MediaStore.open*`。
- Android 11/12 的模块化 Picker。
- Google Play services backport，以及明确走 `ACTION_OPEN_DOCUMENT` 的设备。

媒体组合包括本地与云端、云端离线、JPEG/HEIC/AVIF、HEVC、各业务支持的 HDR
类型、1 分钟边界两侧的视频、单选与业务允许的最大多选。生命周期用例包括设备
重启、进程终止、持久授权、授权释放、选择后立即撤销、准备中取消、存储空间不足
和 Provider 读取失败。

验收使用目标设备的 P50/P95/P99、峰值内存、临时文件峰值和取消后残留任务
数，不复制其他设备的耗时阈值。

## Photo Picker 与 Android 版本适配表

| 能力 | 平台边界 | 接入与回退 |
| --- | --- | --- |
| 标准 Photo Picker | Android 13 / API 33 原生；符合条件的 Android 11 及以上设备通过模块更新获得 | AndroidX Activity 1.7.0 及以上；使用 `isPhotoPickerAvailable(context)` 做能力探测 |
| Google Play services backport | Android 4.4–10，以及支持 Google Play services 的 Android Go 11/12 | 清单声明模块依赖后可安装；不可用时由 AndroidX 回退 SAF |
| SAF 回退 | Android 4.4 / API 19 及以上 | `ACTION_OPEN_DOCUMENT` 会忽略多选最大数量；按文档 URI 处理，不能调用 MediaStore 专用打开入口 |
| Photo Picker HDR→SDR | Android 13 及以上 | AndroidX Activity 需要包含 `setMediaCapabilitiesForTranscoding()`；只为业务不支持的 HDR 类型请求转换 |
| 嵌入式 Photo Picker | Android 14 及以上且 U Extension 15；平台 API 36 | Jetpack API 仍为实验性；会话失败或能力不足时使用标准 Picker |
| `MediaStore.open*` Picker helper | API 36，同时在 R Extension 15 提供 | authority 为 `media` 时优先；SAF URI 继续使用 `ContentResolver` |
| 选择属性约束 | API 37，同时在 U Extension 22 提供 | `PhotoPickerSelectionParams` 可限制 MIME、大小、总批次、分辨率和时长 |
| 多选数量 | `android-17.0.0_r1` 上限为 100 | 运行时读取 `getPickImagesMaxLimit()`；业务上限不得超过平台值 |
| 兼容媒体转码 | Android 12 及以上 | 受设备、来源、格式、片长和会话限制；调用方必须能处理原内容回退 |

Android 11/12 的模块更新与 Android 4.4–10 的 Google Play services backport
不是同一分发路径。是否安装成功、厂商是否提供系统回退 Picker、AndroidX 是否走
SAF，都应通过能力探测和实际启动结果记录，不能只看 `SDK_INT`。

## 与隐私权限、应用锁和 OEM 相册能力的关系

Photo Picker 适合“用户明确选择少量媒体”的流程，可以减少
`READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` 整库权限申请。相册管理、备份、文件管理
和云图库同步仍需依据功能选择 `MediaStore`、部分媒体访问、SAF 或特殊合规权限，
不能用 Picker 模拟全库同步。

系统认证、厂商私密相册、工作资料、云媒体账号和离线状态都可能改变可见内容或让
读取失败。应用只应依赖公开回调与 URI 授权：

- 标准 Picker 返回空结果时按用户未完成选择处理，不推测具体隐私原因。
- URI 打开失败时保留异常类别和当前能力路径，不记录媒体身份。
- 嵌入式会话报错时关闭会话并使用标准 Picker，不在同一页面无限重连。
- SAF 回退 URI 按其 authority 和可持久化授权处理。

OEM 差异通过 `isPhotoPickerAvailable(context)`、SDK Extension、实际 Intent
解析结果和错误分类观测。只有官方兼容方案不能覆盖且有长期验证要求时，才增加
厂商专用分支。

## 与 24.12 MediaStore / MediaProvider 的交叉引用

24.12 已说明 `MediaStore` 查询、`MediaProvider` 索引、FUSE、缩略图、
version/generation 和兼容媒体转码。这里补充选择器启动、Picker URI 生命周期、
云媒体读取、HDR 请求、私有临时文件和多选队列。

媒体选择慢可按阶段定位：

1. 系统 Picker 在实验室打开慢：检查平台、模块、嵌入式/标准路径与
   MediaProvider 状态。
2. 回调后描述符打开慢：检查授权、云媒体、兼容转码和取消信号。
3. 描述符已返回而首字节慢：检查管道供应、云端获取与磁盘 I/O。
4. 内容可读而准备慢：检查应用复制、解码、编码、摘要和队列等待。
5. 准备完成而发送慢：进入网络上传与服务端处理范围。

`dumpsys media.transcoding` 查看媒体转码会话；Android 17 AOSP MediaProvider
使用完整组件名
`com.android.providers.media.module/com.android.providers.media.MediaProvider`
观察。命令、Provider version/generation 与批量媒体操作详见 24.12。

## 实战检查清单

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
- 云媒体失败、选择撤销和页面退出能否取消所有下游任务。
- 大图、多选和视频转换是否分别限制 I/O、CPU、临时空间和网络并发。
- 线上指标是否避开原始 URI、文件名、相册名和账号信息。
- 标准 Picker 首帧与首张缩略图是否通过实验室自动化测量。

## 参考资料

- [Android Developers：Photo Picker](https://developer.android.com/training/data-storage/shared/photo-picker)
- [Android Developers：嵌入式 Photo Picker](https://developer.android.com/training/data-storage/shared/photo-picker/embedded)
- [Android Developers：兼容媒体转码](https://developer.android.com/media/platform/transcoding)
- [Android Developers：媒体缩略图](https://developer.android.com/social-and-messaging/guides/media-thumbnails)
- [Android API：`MediaStore`](https://developer.android.com/reference/android/provider/MediaStore)
- [Android API：`PickerMediaColumns`](https://developer.android.com/reference/android/provider/MediaStore.PickerMediaColumns)
- [Android API：`PhotoPickerSelectionParams`](https://developer.android.com/reference/android/widget/photopicker/PhotoPickerSelectionParams)
- [AOSP 文档：兼容媒体转码](https://source.android.com/docs/core/media/media-transcoding)
- [AOSP 文档：MediaProvider 模块](https://source.android.com/docs/core/media/media-provider)
- [Android 17 源码：`MediaStore.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/apex/framework/java/android/provider/MediaStore.java)
- [Android 17 源码：`TranscodeHelperImpl.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/TranscodeHelperImpl.java)
- [Android 17 源码：`PhotoPickerTranscodeHelper.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/PhotoPickerTranscodeHelper.java)
- [Android 17 源码：`PhotoPickerActivity.java`](https://android.googlesource.com/platform/packages/providers/MediaProvider/+/refs/tags/android-17.0.0_r1/src/com/android/providers/media/photopicker/PhotoPickerActivity.java)
