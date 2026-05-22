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
related_chapters: ["7.10", "12.1", "20.10", "22.6", "24.12", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "官方文档/每日信息/素材驱动/AOSP结构"
---

# 24.13 Photo Picker、媒体转码与缓存治理

<!-- outline-start -->
## 要点

### 🔹 Photo Picker 的性能边界
说明 Photo Picker 与传统 SAF / `ACTION_PICK` / 应用自建相册页的差异，重点放在启动延迟、权限面、媒体 URI 生命周期和跨版本兼容策略。

### 🔹 嵌入式 Photo Picker 的接入成本
梳理嵌入式 Photo Picker 在页面切换、窗口嵌入、回退行为和冷启动路径上的成本，区分系统能力与应用 UI 编排成本。

### 🔹 视频转码的时间与存储成本
覆盖官方文档提到的 transcoding 处理时间、新文件占用、1 分钟视频长度限制、缓存文件回收策略，并给出线上指标设计。

### 🔹 MediaProvider 与缓存清理链路
从 MediaProvider、idle maintenance 和应用本地缓存三个层次分析媒体选择后的文件治理边界，避免把系统缓存和业务缓存混为一谈。

### 🔹 大图/多选场景的 I/O 与内存压力
补齐多选图片、HEIC/AVIF、缩略图预取、大图解码和上传前压缩对主线程、I/O 线程、Bitmap 内存的影响。

### 🔹 可观测性与回归防护
设计 Photo Picker 打开耗时、首张缩略图时间、选择完成到业务可用时间、转码耗时、失败率和缓存占用的指标。

## 扩展

### 🔸 Photo Picker 与 Android 版本适配表
补充 Android 13 原生、Android 11/12 模块化 backport、Google Play services / OEM 差异的接入边界。

### 🔸 与隐私权限、应用锁和 OEM 相册能力的关系
只记录影响媒体选择性能和失败率的边界，不展开隐私功能本身。

### 🔸 与 24.12 MediaStore / MediaProvider 的交叉引用
加工时只引用 24.12 的 MediaProvider 原理，不重复写媒体库扫描机制。

<!-- outline-end -->

## Photo Picker 解决的是选择入口，不替应用吞掉后续成本

Photo Picker 把“让用户选几张图或视频”这件事交给系统 UI，App 不再为了临时选择去申请整库读取权限，也不用自建相册页、分页查询、缩略图缓存和权限弹窗。它能减少权限面和相册维护成本，但不会替 App 完成上传、解码、压缩、失败重试和业务缓存治理。

这节只讨论 App 接入层的性能边界。`MediaStore`、`MediaProvider`、FUSE、缩略图和兼容媒体转码的系统路径详见 24.12 节；图片加载和 `Bitmap` 缓存详见 7.10、22.6 节；普通文件 I/O 与网络上传详见 24.1、24.6 节。

[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md] [结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md] [结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md] [结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

## Photo Picker 的性能边界

Photo Picker 返回的是用户授权的媒体 `Uri`，不是一批可长期任意访问的文件路径。Android Developers 文档把它定位成安全的内置选择界面：用户只授予被选中图片或视频的访问权，App 不获得整库读取能力。AOSP `MediaStore.java` 也把 `ACTION_PICK_IMAGES` 返回的内容称为 picker URI，并说明这些 URI 暴露的是只读的 `PickerMediaColumns` 视图。[已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker] [已验证: AOSP main, packages/providers/MediaProvider/apex/framework/java/android/provider/MediaStore.java]

选择入口的成本可以分成四类：

| 路径 | 适合场景 | 性能收益 | 边界 |
| --- | --- | --- | --- |
| Photo Picker | 聊天、头像、发帖、反馈上传这类用户主动选择 | 不申请整库权限；系统处理跨版本 UI 与云端媒体入口 | 打开系统 UI 仍有冷启动、模块加载、媒体索引和缩略图加载成本 |
| SAF / `ACTION_OPEN_DOCUMENT` | 选择任意文件、需要持久授权的文档流 | Android 4.4+ 设备覆盖面广 | 文件浏览入口更通用，媒体体验和缩略图质量取决于 DocumentsUI / provider |
| `ACTION_PICK` / OEM 相册 | 兼容旧接入或厂商相册定制入口 | 能复用部分厂商体验 | 行为差异大，返回 URI、权限时长和失败码难以统一 |
| 自建相册页 | 相册、备份、云图库、重度编辑器 | UI 与业务状态可完全控制 | 要自己承担权限、分页、缩略图、缓存、转码、弱网云照片等成本 |

默认授权时长也要纳入方案设计。官方文档说明，系统通常授予 App 访问所选媒体，直到设备重启或 App 停止；长时间后台上传这类场景，应调用 `takePersistableUriPermission()` 延长访问权。这里的“长时间”不只是几分钟网络上传，也包括用户选完视频后切到别的 App、进程被系统回收、WorkManager 稍后恢复任务的情况。[已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker]

打开 picker URI 时优先使用 `MediaStore.openFileDescriptor()`、`MediaStore.openAssetFileDescriptor()` 或 `MediaStore.openTypedAssetFileDescriptor()`。AOSP `MediaStore.java` 在这些 API 的注释里写明，它们比直接使用 `ContentResolver` open API 更适合打开 `ACTION_PICK_IMAGES` 返回的媒体 URI，目标是保证系统稳定性。工程上要把“打开 URI”放到 I/O 线程，并带 `CancellationSignal`；列表预览、上传取消、页面退出时要取消正在排队的读取。[已验证: AOSP main, packages/providers/MediaProvider/apex/framework/java/android/provider/MediaStore.java]

## 嵌入式 Photo Picker 的接入成本

嵌入式 Photo Picker 把选择器放进 App 页面内部，官方文档说明它通过 `SurfaceView` 承载 picker UI，并通过 `setChildSurfacePackage` 维持与标准 Photo Picker 相同的安全和隐私边界。用户可以在 App 仍处于 resumed 状态时连续选择、取消选择图片和视频，App 则实时接收选中 URI。[已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker/embedded]

这类体验减少了 Activity 跳转，但新增了页面内编排成本：

- 页面首帧：宿主页面要创建输入框、预览区、选择器容器和业务状态；picker 自身还要连接系统服务、初始化 Surface 和加载媒体网格。首帧指标应拆成“宿主首帧”和“picker 首批缩略图出现”，不要只看 Activity `onCreate()` 到首帧。
- 连续选择：每次选择/取消都会触发宿主 UI 更新。聊天、发帖、工单上传这类页面通常还会同步刷新底部预览条、上传队列和按钮状态，Diff 计算、图片预解码和状态同步不要放在主线程长任务里。
- 回退行为：用户关闭键盘、收起 picker、退出页面是三条不同路径。回退栈处理错误会让 picker 反复销毁重建，表现成“第二次打开更慢”或“选中状态丢失”。
- 尺寸变化：折叠屏、多窗口、横竖屏切换会改变 `SurfaceView` 尺寸。宿主页面应把选择器高度、输入框高度、预览条高度纳入同一套布局状态，避免每次媒体选择都触发布局抖动。

嵌入式版本的设备条件更窄：官方文档写明它支持 Android 14（API 34）且 SDK Extensions 15+ 的设备；不满足条件时回退到标准 Photo Picker 或 Google Play services backport。接入层要把“是否可用”作为运行时能力，不要只按系统版本判断。[已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker/embedded]

## 视频转码的时间与存储成本

Android 12 引入兼容媒体转码，系统可以把设备相机生成的 HEVC / HDR 视频转换成旧 App 更容易处理的 AVC / SDR。Android Developers 文档给出的例子是：Pixel 3 上 1 分钟 HEVC 视频转成 AVC 大约需要 20 秒。这个数字不能直接当线上 SLA，但足以说明转码是重 CPU / 编解码器 / 存储操作，不应夹在用户点击“发送”和网络请求开始之间静默执行。[已验证: 官方文档, developer.android.com/media/platform/transcoding]

Photo Picker 的 HDR 转 SDR 转码也不是默认开启。App 通过 AndroidX Activity 的 `PickVisualMediaRequest.Builder.setMediaCapabilitiesForTranscoding()` 声明自己支持哪些 HDR 类型；未声明支持的 HDR 类型才可能被 picker 转成 SDR。官方文档同时给出三条边界：转码会耗时并创建新文件；为平衡体验和存储，视频长度限制为 1 分钟；缓存的转码文件会在 idle maintenance 期间周期清理。[已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker]

AOSP 文档对兼容媒体转码的限制更具体：它面向原生相机在主外部存储 `DCIM/Camera/` 下生成的本机媒体，不支持二级存储上的媒体，也不支持邮件、SD 卡等外部来源带入的内容；通过 `MediaStore`、直接文件路径、SAF 和系统分享入口访问时可能触发转码，弹出 SD 卡、Nearby Share、蓝牙传输等路径会绕过转码。[已验证: AOSP 文档, source.android.com/docs/core/media/media-transcoding]

线上指标不要只打一个“上传耗时”。至少拆成这几段：

| 指标 | 起点 | 终点 | 诊断含义 |
| --- | --- | --- | --- |
| `picker_open_latency_ms` | 点击选择按钮 | picker UI 可交互 | 系统 UI 冷启动、模块加载、窗口切换 |
| `picker_first_thumbnail_ms` | picker 打开 | 首批缩略图出现 | 媒体索引、缩略图读取、云照片状态 |
| `selection_to_fd_ms` | 用户完成选择 | App 拿到可读 fd | URI 权限、provider 响应、转码等待 |
| `transcode_wait_ms` | 打开媒体触发转码 | fd 返回或失败 | 兼容转码和 HDR → SDR 成本 |
| `local_prepare_ms` | fd 可读 | 业务上传体准备好 | 解码、压缩、临时文件写入、摘要计算 |
| `cache_bytes_after_send` | 发送完成 | 采样点 | App 本地临时文件与缩略图缓存是否回收 |

如果产品允许，转码等待超过阈值时给用户明确状态，例如“正在处理视频格式”。如果业务服务端已经支持 HEVC / HDR，App 应声明相应能力，减少不必要的转码。官方文档也明确提醒，不要为了本机播放或生成缩略图触发转码；这些场景应直接处理原始媒体或走缩略图 API。[已验证: 官方文档, developer.android.com/media/platform/transcoding]

## MediaProvider 与缓存清理链路

媒体选择后的缓存分三层，排查时要分开看：

- 系统转码缓存：AOSP `TranscodeHelperImpl.java` 把转码目录放在 `/storage/emulated/<user>/transcode`，通过 `getTranscodePath(rowId)` 为媒体行生成缓存路径，并提供 `freeCache(bytes)`、`deleteCachedTranscodeFile(rowId)` 这类清理入口。App 不能假设系统缓存会在业务完成后马上消失。[已验证: AOSP main, packages/providers/MediaProvider/src/com/android/providers/media/TranscodeHelperImpl.java]
- MediaProvider 索引与缩略图：MediaProvider 负责索引共享存储中的图片、视频和音频元数据，并通过 `MediaStore` 暴露给 App。扫描、索引、缩略图和转码细节详见 24.12 节，不在这里重复展开。[已验证: AOSP 文档, source.android.com/docs/core/media/media-provider]
- App 本地缓存：聊天草稿、上传队列、图片编辑临时文件、压缩后文件和业务缩略图都属于 App 自己的责任。系统 idle maintenance 只处理系统缓存，不会替 App 清理 `cacheDir`、数据库记录和上传失败的临时文件。

稳定的治理方式是给每个业务临时文件写入 owner、原始 picker URI、用途、创建时间、上传状态和过期时间。发送成功后立即删除可重建文件；发送失败但可重试的文件设置短 TTL；用户撤销选择、删除草稿、账号退出时按 owner 批量清理。只靠 `cacheDir` 大小阈值兜底，会在大量视频失败重试后把磁盘占用问题延后到下一次冷启动。

## 大图、多选和云端媒体的 I/O 与内存压力

多选不是把单选流程循环 N 次。系统限制 `ACTION_PICK_IMAGES` 的最大多选数量，AOSP `MediaStore.java` 里 `PICK_IMAGES_MAX_LIMIT` 当前是 100，公开 API `getPickImagesMaxLimit()` 返回这个上限。App 仍应根据业务服务端、页面内预览能力和弱网失败率设置更小的业务上限，例如头像选择只允许 1 张，聊天批量发送按会话类型限制 9、20 或更少。[已验证: AOSP main, packages/providers/MediaProvider/apex/framework/java/android/provider/MediaStore.java]

大图处理要避免两类问题。第一类是主线程 I/O：在 `onActivityResult`、Compose state 更新或 RecyclerView 绑定阶段同步打开 `Uri`，会把 provider 响应、磁盘读取、转码等待和解码堆到主线程。第二类是 Bitmap 峰值：HEIC、AVIF、超大 JPEG 和带 EXIF 旋转的图片，原图解码后可能远大于上传目标尺寸。缩略图使用 `ContentResolver.loadThumbnail()`（Android 10+）或图片加载库，上传前压缩使用独立 I/O / CPU 线程池，并限制并发数。[已验证: 官方文档, developer.android.com/social-and-messaging/guides/media-thumbnails]

云端媒体还会带来“看得见但本地不可立即读取”的状态。AOSP `PhotoPickerActivity.java` 里有对 unavailable cloud-only media 的处理逻辑：离线时用户选择未缓存云端媒体，会展示错误并移除不可用项。App 层也要把“用户选中 URI”和“业务已拿到可读内容”分成两个状态；只在 UI 上显示已选择，不代表可以马上开始上传。[已验证: AOSP main, packages/providers/MediaProvider/src/com/android/providers/media/photopicker/PhotoPickerActivity.java]

多选上传的线程池可以按三类任务分开：URI 打开和顺序读属于 I/O；缩放、编码、哈希属于 CPU；网络上传属于网络队列。线程池数量不要跟选择数量线性增长。参考性能优化资料里的线程池和 Bitmap 治理思路，媒体发送页更适合小并发、可取消、可背压的队列：当前屏预览优先，离屏预处理降级，用户取消后立即停止未开始任务。[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md] [结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

## 可观测性与回归防护

Photo Picker 接入后的故障常被误判成“用户没选图”或“上传慢”。埋点要覆盖入口、系统 UI、URI 打开、转码、业务处理和缓存回收：

| 维度 | 建议字段 | 用途 |
| --- | --- | --- |
| 设备能力 | Android 版本、SDK Extension、是否嵌入式 picker、是否 Google Play services backport | 区分原生、嵌入式、backport 和 SAF 回退 |
| 媒体信息 | MIME、大小、宽高、时长、是否多选、是否 HDR / HEVC（能识别时） | 判断转码、解码、压缩和上传成本 |
| URI 读取 | open fd 耗时、失败码、取消原因、是否持久授权 | 定位 provider、权限、生命周期问题 |
| 转码 | 是否声明 `MediaCapabilities`、转码等待、成功 / 失败 / 取消 | 判断兼容媒体转码是否进入主路径 |
| 内存与 I/O | 单次解码峰值、压缩队列等待、临时文件大小、cacheDir 占用 | 防止多选图片压垮内存和磁盘 |
| 用户路径 | picker 打开取消率、选择后取消率、发送失败重试率 | 识别 UI 回退和弱网体验问题 |

回归测试要覆盖四组样本：低端 Android 13 设备、Android 14 + SDK Extension 15+ 设备、带 Google Play services backport 的旧设备、厂商相册或 SAF 回退设备。媒体样本至少包含普通 JPEG、HEIC、AVIF、4K HEVC、HDR10 / HDR10+ 视频、超过 1 分钟视频、云端未缓存媒体和 50+ 多选图片。

Perfetto 侧重点是 App 自己的 I/O、解码和上传队列，不要期待 trace 里只有一个“Photo Picker 慢”的标签。可观察的线索包括主线程长任务、Binder 等待、磁盘读写峰值、图片解码 CPU、网络上传并发和 App 自己的 trace section。系统级 MediaProvider 观察入口详见 24.12 节，线上异常归因和指标体系详见 26.16 节。

## Photo Picker 与 Android 版本适配表

| 能力 | 版本边界 | 接入建议 |
| --- | --- | --- |
| 标准 Photo Picker | Android 13（API 33）原生；旧设备可通过 AndroidX Activity 与 Google Play services backport 覆盖更多版本 | 使用 AndroidX Activity 1.7.0+，运行时调用 `isPhotoPickerAvailable()` 判断可用性 |
| SAF 回退 | Android 4.4（API 19）+ | picker 不可用时由库回退到 `ACTION_OPEN_DOCUMENT`，业务侧要兼容持久授权和文件 provider 差异 |
| HDR 转 SDR Photo Picker 转码 | Android 13+，AndroidX Activity 1.11.0-alpha01 或后续版本提供相关 API | 只在服务端或业务不支持 HDR 时声明不支持；支持的 HDR 类型要显式声明 |
| 嵌入式 Photo Picker | Android 14（API 34）+ SDK Extensions 15+ | 把嵌入式当增强路径，标准 picker 当稳定回退路径 |
| 兼容媒体转码 | Android 12+ 平台能力，设备和媒体来源受限 | 通过 `MediaCapabilities` 控制触发范围，避免本机播放和缩略图路径触发转码 |

[已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker] [已验证: 官方文档, developer.android.com/training/data-storage/shared/photo-picker/embedded] [已验证: 官方文档, developer.android.com/media/platform/transcoding]

## 与隐私权限、应用锁和 OEM 相册能力的关系

Photo Picker 的主线是“用户选择哪些媒体，App 才能访问哪些媒体”。这能减少 `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` 这类整库权限的申请，也降低用户拒绝权限导致的失败率。它不是相册权限体系的全部替代品：相册、备份、文件管理、云图库同步这类长期整库管理场景，仍要按业务类型评估 `MediaStore`、系统选择器、SAF 或合规权限路径。

Android 17 原生应用锁、OEM 相册加密、私密相册和云相册离线状态会影响 picker 结果和失败率，但不宜在性能章节展开隐私策略。工程侧只记录会影响性能和稳定性的边界：是否出现空列表、是否无法读取已选 URI、是否提示云端未缓存、是否在应用锁验证后重新创建 picker、是否回退到厂商相册或 DocumentsUI。

OEM 差异最好用能力探测和失败码统计处理，不要为某个厂商写死逻辑。线上看板按系统版本、SDK Extension、Google Play services 版本、设备品牌和 picker 类型切分后，才能判断是系统模块问题、云端照片问题、业务压缩队列问题，还是用户在权限 / 应用锁环节放弃。

## 与 24.12 MediaStore / MediaProvider 的交叉引用

24.12 已覆盖 `MediaStore` 查询、`MediaProvider` 索引、FUSE、缩略图、兼容媒体转码和 `dumpsys media_provider` 观察入口。本节只补 App 接入层：选择器打开、URI 生命周期、转码等待、临时文件、上传准备、多选背压和回归防护。

遇到媒体访问慢时，排查顺序可以按这条路径走：picker UI 打开慢先看设备能力和嵌入式 / 标准路径；用户选择后业务拿不到文件先看 URI 权限和 open fd；open fd 卡住再看转码与 MediaProvider；fd 已返回但上传慢，看 App 的解码、压缩、临时文件和网络队列。这样能避免把所有问题都推给系统相册，也能避免在 App 层重复实现 24.12 已经交给平台处理的能力。
