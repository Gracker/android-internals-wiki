---
title: "图片加载与显示优化"
chapter: "22.6"
section: "22.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1; Glide 5.0.9; Coil 3.5.0; Android Developers docs"
confidence: high
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapFactory.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/ImageDecoder.java @ android-17.0.0_r1"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/reduce-image-sizes"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapFactory.Options"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapRegionDecoder"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/ImageDecoder"
  - type: library-doc
    path: "https://bumptech.github.io/glide/doc/caching.html"
  - type: library-doc
    path: "https://bumptech.github.io/glide/doc/resourcereuse.html"
  - type: library-doc
    path: "https://coil-kt.github.io/coil/"
  - type: library-doc
    path: "https://coil-kt.github.io/coil/image_loaders/"
  - type: library-release
    path: "https://github.com/bumptech/glide/releases/tag/v5.0.9"
  - type: library-release
    path: "https://github.com/coil-kt/coil/releases/tag/3.5.0"
tags: [image-loading, glide, coil, bitmap-decode, image-cache]
related_chapters: ["22.1", "22.26", "23.2"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
---

# 图片加载与显示优化

图片从 URL 变成屏幕像素，要经过获取压缩数据、查找各级缓存、解码、变换、持有像素、更新 UI、HWUI（Android 硬件加速 UI 渲染系统）采样，再提交窗口缓冲区直至上屏（present）。任何一段都可能成为首图慢、列表掉帧或内存峰值的来源。

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，Linux 内核观察基线固定为 `android17-6.18-2026-06_r6`。软件 Bitmap 解码完成后，宿主 View 仍要更新 DisplayList（记录待执行绘制命令的显示列表），专用渲染线程 RenderThread 再通过 HWUI 采样 Bitmap，并提交应用窗口缓冲区。硬件 Bitmap 的像素存储位于图形内存，适合只在硬件加速 Canvas 上显示；它仍占用图形资源，也不代表图片已经按期上屏。显示阶段可结合 [Android View 标准渲染路径](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md) 阅读。

## Glide 与 Coil：按版本和约束选型

截至 2026-08-14，第三方库相关行为以 Glide `5.0.9` 与 Coil `3.5.0` 为准。两者独立于 Android 平台发布；升级库后要重新核对默认解码器、缓存键、网络组件和 Compose API。

| 维度 | Glide 5.0.9 | Coil 3.5.0 | 评审问题 |
| --- | --- | --- | --- |
| Android View | 提供 `RequestManager`、`ViewTarget`、资源引用计数和 `BitmapPool` | `ImageView.load()` 与 `ImageRequest` 可直接使用 | 现有模块使用哪套生命周期、扩展组件和监控 |
| Compose | Compose 集成是单独的 beta 版依赖模块 | `AsyncImage`、`rememberAsyncImagePainter`、`SubcomposeAsyncImage` 是主文档 API | 能否接受 beta API；是否需要跨平台 |
| 内存资源 | 正在使用的资源（active resources）、内存缓存和资源复用池 | 单例 `ImageLoader` 的内存缓存 | 同屏尺寸、硬件位图策略、变换产生的中间资源 |
| 磁盘 | 原始数据与变换后资源可按策略缓存 | `ImageLoader` 自有磁盘缓存 | 缓存的是原始响应还是输出结果；失效标识是什么 |
| 网络 | 默认可用 HttpURLConnection，也可接入其他网络栈 | 核心依赖模块默认不含网络支持，需要 OkHttp、Ktor 或自定义 `NetworkClient` 组件 | 连接池是否共享；HTTP 缓存语义是否满足服务端协议 |

框架名称不能替代请求配置。相同 URL 在不同目标尺寸、变换、色彩配置、硬件位图策略和生命周期下，内存峰值与首帧时间都可能不同。选型应使用同一批资源、相同目标尺寸、相同缓存未命中或命中状态和相同设备做对比。

### Glide 的使用边界

Glide 5.0.9 的 `Engine` 先查正在使用的资源和内存缓存；未命中后复用同一缓存键对应的 `EngineJob`（进行中的加载任务），否则启动新的 `DecodeJob`（解码任务）。原始数据和变换后资源的磁盘缓存策略由请求决定。加载到 `ImageView` 时，新的 `into(imageView)` 会替换该 View 上的旧请求；RecyclerView 回收后若暂时不绑定新图，应调用 `clear(imageView)`，同时清掉占位图之外的旧内容。

`Glide.with(fragment)`、`Glide.with(activity)` 或 `Glide.with(view)` 可以获得与界面关联的 `RequestManager`。传入 Application Context（应用级 Context）会得到应用级 `RequestManager`，不具备页面停止时的自动暂停语义。Glide 返回的 Bitmap 可能受引用计数和 `BitmapPool` 管理；请求清理后继续持有 Bitmap，或在 Transformation（变换实现）中手动调用 `recycle()` 回收原始 Bitmap，都可能造成内容复用错误或崩溃。

### Coil 的使用边界

Coil 3.5.0 建议全应用共享一个 `ImageLoader`。每个实例都持有自己的内存缓存、磁盘缓存和网络资源；按页面创建实例会拆散命中率并增加常驻对象。需要不同认证或隔离域时，可以显式设计少量 `ImageLoader`，并记录它们的缓存目录和生命周期。

Compose 中，`AsyncImage` 会结合可组合项的布局约束（constraints）与 `ContentScale` 推导请求尺寸。直接调用 `rememberAsyncImagePainter(model)` 不会自动感知显示尺寸，默认请求原始尺寸；应提供 `SizeResolver`。`SubcomposeAsyncImage` 为状态插槽（slot）使用子组合（subcomposition），官方文档明确提示它不适合性能敏感的 `LazyList` 高频路径。

Coil 3 的网络行为要单独配置：

- `coil-compose` 或 `coil` 本身不提供 URL 网络获取，需要引入一个 `coil-network-*` 依赖模块；
- 3.5.0 可使用 `coil-network-okhttp`、`coil-network-ktor2` 或 `coil-network-ktor3`；
- 默认 `NetworkFetcher` 会把响应写入 Coil 磁盘缓存，但不遵循 HTTP `Cache-Control`；
- 需要遵循响应缓存头时，引入 `coil-network-cache-control` 并配置 `CacheControlCacheStrategy`；相关 `CacheStrategy` API 在该版本仍标记为 `ExperimentalCoilApi`。

这些行为与 OkHttp 自身的 HTTP 缓存不是同一层。评审缓存命中时，要记录命中的具体层和 Coil 网络组件配置。

### 混用两套框架的成本

迁移期允许 Glide 与 Coil 并存。一个页面同时请求同一批图片时，两套内存缓存、磁盘缓存、解码任务和网络连接可能重复。迁移方案应按功能模块或页面切分，并采集两套 data source（数据来源）指标；不要在同一个 RecyclerView 中按列表项随机选择图片框架。

## 解码尺寸、像素内存与硬件位图

压缩文件大小不能代表解码后内存。4000 × 3000 的 ARGB_8888 Bitmap 仅按像素计算为：

`4000 × 3000 × 4 = 48,000,000 bytes ≈ 45.8 MiB`

显示目标为 1000 × 750 时，同配置像素约 2.86 MiB，两者像素数量相差 16 倍。行跨度（row stride，即相邻两行像素起始位置之间的字节数）、色彩配置、复用空间、辅助解码缓冲区和图形驱动资源还会增加运行时占用。

Android 8.0 / API 26 起，软件 Bitmap 的像素数据位于原生堆（native heap）。Android 17 的 `Bitmap` 通过 `NativeAllocationRegistry` 登记原生内存分配，`getAllocationByteCount()` 返回当前底层分配空间的字节数；复用过的 Bitmap 可能出现这个值大于当前 `getByteCount()`。`Bitmap.Config.HARDWARE` 的像素存放在图形内存且始终不可变：`getPixel()`、`getPixels()` 与 `copyPixelsToBuffer()` 等直接访问会抛出异常，软件 Canvas 也不能绘制它。显式复制成软件 Bitmap 等路径可能触发 GPU 回读（readback，即把图形内存读回 CPU 可访问内存），需要单独测量。

### BitmapFactory：先读边界尺寸，再按 2 的幂采样

下面的函数只负责文件解码，调用方必须把它放到解码线程池。它会先读取文件头得到边界尺寸，并选择不会把两个维度都采样到目标值以下的最大 2 的幂。

```kotlin
@WorkerThread
fun decodeSampledFile(
    path: String,
    requestedWidth: Int,
    requestedHeight: Int,
): Bitmap {
    require(requestedWidth > 0 && requestedHeight > 0)

    val bounds = BitmapFactory.Options().apply {
        inJustDecodeBounds = true
    }
    BitmapFactory.decodeFile(path, bounds)
    require(bounds.outWidth > 0 && bounds.outHeight > 0) {
        "Unsupported or corrupt image: $path"
    }

    var sampleSize = 1
    while (sampleSize <= Int.MAX_VALUE / 2) {
        val nextSampleSize = sampleSize * 2
        if (bounds.outWidth / nextSampleSize < requestedWidth ||
            bounds.outHeight / nextSampleSize < requestedHeight
        ) {
            break
        }
        sampleSize = nextSampleSize
    }

    val options = BitmapFactory.Options().apply {
        inSampleSize = sampleSize
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return requireNotNull(BitmapFactory.decodeFile(path, options))
}
```

Android 17 的 `BitmapFactory.Options` 仍说明：`inSampleSize <= 1` 按 1 处理，非 2 的幂会向下取到最近的 2 的幂。采样得到的是解码近似尺寸，ImageView 或图片库还可能执行精确缩放与裁剪。服务端能提供接近目标的资源时，应先减少下载尺寸，再让客户端做末端适配。

`inBitmap` 能复用可变 Bitmap 的已分配空间。API 19 起，只要新结果所需字节不超过旧 Bitmap 的 `getAllocationByteCount()`，复用限制比早期版本宽；配置、可变性、色彩空间和仍在展示的引用仍要正确。普通业务应交给经过测试的框架资源池，手写池需要处理并发占用、拒绝复用和异常回退。

### ImageDecoder：默认结果通常是硬件 Bitmap

`ImageDecoder` 从 API 28 提供。`decodeBitmap()` 是同步调用；使用头信息回调（header callback）不会自动把解码移出主线程。下面的函数接收专用协程调度器（dispatcher），并按目标边界等比缩小。只有调用方需要像素访问或软件 Canvas 时才强制使用软件内存。

```kotlin
@RequiresApi(Build.VERSION_CODES.P)
suspend fun decodeSized(
    source: ImageDecoder.Source,
    requestedWidth: Int,
    requestedHeight: Int,
    decodeDispatcher: CoroutineDispatcher,
    requireSoftwarePixels: Boolean,
): Bitmap = withContext(decodeDispatcher) {
    require(requestedWidth > 0 && requestedHeight > 0)

    ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
        val sourceWidth = info.size.width
        val sourceHeight = info.size.height
        val scale = minOf(
            requestedWidth.toFloat() / sourceWidth,
            requestedHeight.toFloat() / sourceHeight,
            1f,
        )
        decoder.setTargetSize(
            maxOf(1, (sourceWidth * scale).roundToInt()),
            maxOf(1, (sourceHeight * scale).roundToInt()),
        )
        if (requireSoftwarePixels) {
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
        }
    }
}
```

Android 17 的 `ALLOCATOR_DEFAULT` 通常产生 `Bitmap.Config.HARDWARE`，小图或与硬件分配不兼容的选项可能回到软件分配。设置 `setMutableRequired(true)`、需要读写像素、绘制到软件 Canvas 或执行只支持软件 Bitmap 的算法时，应请求软件结果。只在硬件 Canvas 展示时可以保留默认策略，并让 Glide / Coil 按变换与设备能力决定。

### 从解码完成到图片可见

图片库回调成功只说明结果已经交给显示目标（target）。软件 Bitmap 第一次被硬件 Canvas 使用时，RenderThread / GPU 可能还要准备纹理；硬件 Bitmap 省去一部分软件像素到图形资源的转换，但仍有图形内存分配、同步和采样成本。首图慢应区分：

| 现象 | 观察点 | 可能位置 |
| --- | --- | --- |
| 解码时间片（decode span）很长 | 图片库事件、工作线程的 Running（正在运行）/ Runnable（已就绪、等待 CPU）状态、I/O | 文件读取、编解码器、缩放、变换 |
| UI 回调或 View 树遍历很长 | UI 线程、ImageView / Compose 失效请求、布局 | 设置 Drawable 改变尺寸、主线程变换、过量重组 |
| UI 按时，RenderThread 首次绘制变长 | `DrawFrame`、纹理与图形内存、GPU 工作区间 | 软件 Bitmap 上传、图形分配、复杂裁剪或混合 |
| 应用帧已提交，上屏仍晚 | FrameTimeline、BLAST（应用窗口缓冲区交接）、SurfaceFlinger（系统合成服务）、HWC（硬件合成器） | 缓冲区积压、合成或显示阶段 |

这四类现象要用同一张图片、同一次请求和同一个 FrameTimeline（关联应用、系统合成与显示阶段的帧时间线）帧关联，单看图片库“加载成功”事件无法判断图片何时可见。

`getAllocationByteCount()` 适合记录单个 Bitmap 的分配空间，不能覆盖临时编解码缓冲区、硬件图形资源和缓存中的其他对象。内存分析还要看原生堆、图形资源与 dma-buf（设备间共享缓冲区）、PSS（按比例归属进程的物理内存）、GC（垃圾回收）、缺页（page fault）、内存回收（reclaim）与进程 OOM（内存不足）状态。Linux 6.18 内核基线下可补看 PSI memory（内存压力停顿）、`kswapd` 后台回收、direct reclaim（当前线程同步回收）、zram 压缩交换和 GPU 驱动等待，避免把内存回收停顿写成解码器算法问题。

## 大图与 BitmapRegionDecoder

长图、地图和超高分辨率海报需要分块（tile）模型。应用按缩放层级计算可见源坐标，只解码当前视口和有限预取区；离开视口的分块进入有上限的缓存。一次解码完整图片再裁切，仍会占用完整图片的像素内存。

典型状态包括：

1. 原图宽高、方向与坐标系；
2. 当前缩放比例、视口（viewport）和分块网格（tile grid）；
3. 正在执行、已取消、已缓存和正在显示的分块；
4. 每个缩放层级对应的 `inSampleSize`；
5. 内存预算和预取距离。

下面的示例负责把请求矩形限制在原图内，并在后台解码一个分块。示例有意不设置 `inBitmap`，资源复用由分块缓存或统一的 Bitmap 复用池处理。

```kotlin
@WorkerThread
fun decodeTile(
    decoder: BitmapRegionDecoder,
    requestedRect: Rect,
    sampleSize: Int,
): Bitmap {
    val imageBounds = Rect(0, 0, decoder.width, decoder.height)
    val boundedRect = Rect()
    require(boundedRect.setIntersect(requestedRect, imageBounds)) {
        "Tile is outside the source image"
    }

    val options = BitmapFactory.Options().apply {
        inSampleSize = sampleSize.coerceAtLeast(1)
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return requireNotNull(decoder.decodeRegion(boundedRect, options))
}
```

Android 17 的 `BitmapRegionDecoder` 用内部锁保护原生解码器，同一个实例一次只能执行一个 `decodeRegion()`。给同一解码器配置很多工作线程不会得到并行解码，只会增加等待和过期任务。预取队列应支持取消、优先当前视口，并限制尚未消费的结果数量。

`BitmapRegionDecoder` 的平台格式边界有明确演进：

| 平台 | 源码列出的区域解码格式 |
| --- | --- |
| Android 10—11 | JPEG、PNG |
| Android 12—16 | JPEG、PNG、WebP、HEIF |
| Android 17 | JPEG、PNG、WebP、HEIF、AVIF |

这是 Android 框架当前公开的格式边界，设备编解码器、具体文件编码特征和损坏输入仍要实测。服务端向 Android 10/11 下发需要平移缩放的超大图时，应准备 JPEG / PNG 分块或客户端支持的替代解码器；Android 17 才能按平台 `BitmapRegionDecoder` 的声明使用 AVIF 区域解码。

带 `isShareable` 的 `newInstance()` 重载已经弃用，该参数在对应历史版本早已被忽略。一个解码器不再使用且没有并发请求时，可以调用 `recycle()` 释放原生对象；调用后所有读取与解码都会失败。

`ImageDecoder.setCrop()` 发生在解码和缩放输出流程中，Android 17 源码明确说明它不用于替代 `BitmapRegionDecoder.decodeRegion()`。单次裁掉边缘可以使用裁剪（crop）；可缩放长图仍需分块、请求调度和缓存。

## 内存、磁盘与网络缓存

缓存层回答的问题不同，指标也要分开。

| 层级 | 常见内容 | 命中省掉的工作 | 主要风险 |
| --- | --- | --- | --- |
| 正在使用或显示的资源 | 正在被显示目标使用的 Drawable / Bitmap | 重复引用与解码 | 清理后仍持有被资源池接管的对象 |
| 内存缓存 | 已解码并可能已变换的结果 | 磁盘读取、解码、变换 | 原生堆或图形内存峰值，尺寸变体互相挤占 |
| Bitmap / 资源复用池 | 可安全复用的已分配空间或数组 | 频繁分配与释放 | 把仍在显示或不可变的对象放入池 |
| 变换结果磁盘缓存 | 已缩放或变换的输出 | 网络、解码和部分变换 | 尺寸或变换版本遗漏导致错误命中 |
| 原始数据磁盘缓存 | 原始压缩数据 | 网络 | 同一 URL 内容变化、认证隔离和过期策略 |
| HTTP 缓存 / CDN | HTTP 响应或内容分发网络（CDN）的边缘资源 | 服务端传输 | `Cache-Control`、`ETag`、`Vary` 或客户端实现不一致 |

这些层节省的工作不同，命中率不能合并成一个“缓存命中”数字。先确认慢请求缺失的是哪一层，再决定调整容量、缓存键还是服务端响应头。

### 缓存键必须描述内容身份

图片框架会把尺寸、Transformation、Options 和结果类型等请求信息纳入相应缓存键，但“这个 URL 的内容版本”仍由业务和服务端提供。优先使用内容哈希或版本化 URL。URL 不变而内容会更新时，Glide 可使用 `signature`；Coil 可以使用请求数据版本或经过审查的自定义缓存键。不同用户、鉴权请求头、租户或隐私域共享缓存前，要确认缓存键和缓存目录不会串数据。

业务层再增加一份 URL → Bitmap 的强引用缓存，往往造成双份持有、错误失效和绕过内存裁剪策略。确有跨框架共享需求时，更适合共享原始文件或统一网络 / 磁盘层，并明确所有权。

### 缓存容量由峰值场景决定

- 信息流要同时计算可见列表项、预取列表项、交叉淡入淡出（crossfade）期间的新旧 Drawable 和请求并发；扩大内存缓存无法消除同一时刻的解码峰值。
- 相册与聊天应让缩略图、预览图、原图使用不同内容标识和目标尺寸，避免原图挤掉高复用缩略图。
- 多进程各有独立堆和 `ImageLoader`。只有展示图片的进程才应初始化完整图片栈。
- 收到系统内存压力回调时，先让框架按策略裁剪缓存；页面还要释放 RecyclerView adapter（适配器）、Compose 状态、预取结果和自建强引用。
- 清空整个缓存会把后续访问变成冷加载。它属于诊断或明确的账户 / 隐私清理操作，不是常规掉帧修复。

### 网络缓存要验证客户端实现

服务端应提供版本化 URL，或正确的 `ETag`、`Last-Modified`、`Cache-Control` 与 `Vary`。客户端是否使用这些响应头取决于网络组件：

- Glide 的原始数据磁盘缓存与底层 HTTP 缓存是两层；接入 OkHttp 后也要确认是否配置了 `Cache`；
- Coil 3 默认磁盘缓存行为不会自动遵循 `Cache-Control`；
- 使用带签名 URL 时，短期 token（临时凭证）进入 URL 可能降低缓存命中，应由安全与后端共同设计稳定内容标识；
- 失败响应、重定向和认证差异也要进入缓存测试。

命中率统计应分成正在使用的资源、内存、变换结果磁盘、原始数据磁盘、HTTP 与网络六类。只记录 `from cache` 无法判断下一步该调整哪一层。

## AVIF、WebP、JPEG 与 PNG

Android 官方文档说明平台从 Android 12 / API 31 支持 AVIF；Android 10—11 需要 WebP、JPEG、PNG 或库自带解码器作为兼容路径。格式选择要同时比较传输、解码、像素质量、透明度、色彩空间、区域解码和服务端协商。

| 格式 | 适合内容 | Android 10—17 边界 | 评审重点 |
| --- | --- | --- | --- |
| JPEG | 照片、无透明度内容 | 全范围可用 | 有损质量、EXIF（拍摄元数据）方向、渐进编码与服务端尺寸 |
| PNG | UI 资源、无损和透明内容 | 全范围可用 | 照片体积、色板优化、透明像素 |
| WebP | 有损照片、无损或透明图片 | Android 10—17 均可解码 | 编码模式、质量、动画需求、区域解码的平台差异 |
| AVIF | 服务端可协商的高压缩静态图；图像序列需另验具体解码器 | 平台解码从 API 31 开始；平台区域解码声明到 Android 17 才包含 AVIF | 低端机解码时间、色彩 / HDR（高动态范围）、兼容回退、图片库解码器 |

文件更小会减少传输和磁盘字节，但不保证解码或首个可见帧更短。同一组代表性图片要在目标设备上比较：

- CDN 输出字节、TTFB（首字节到达时间）与完整下载时间；
- 冷 / 热原始数据缓存下的解码与变换时间；
- 输出 Bitmap 尺寸、配置、分配空间和图形内存；
- UI 回调、RenderThread 首次采样与 FrameTimeline；
- 视觉质量、透明度、色彩空间、HDR 和 EXIF 方向；
- Android 10、Android 11 与 Android 12—17 的兼容回退。

## 诊断与上线检查

| 问题 | 至少记录的证据 |
| --- | --- |
| 首图慢 | 请求排队、DNS / 连接 / 下载、data source（数据来源）、解码、变换、显示目标回调、首个可见帧 |
| 列表掉帧 | 列表项目标尺寸、请求并发与取消、UI 树遍历、RenderThread、纹理或图形内存分配 |
| 内存峰值 | 同屏与预取数量、Bitmap 配置与分配空间、内存缓存、原生堆、图形 / dma-buf 内存、内存回收 |
| 图片错位 | 显示目标复用、请求缓存键、取消时机、稳定的列表项标识、占位图状态 |
| 缓存失效 | 内容版本、各层缓存键、响应头、Coil `CacheStrategy` 或 Glide `DiskCacheStrategy` |
| 大图卡顿 | 视口与分块队列、同一解码器串行等待、过期任务、分块缓存与缩放层级 |

上线前逐项确认：

- View 或可组合项的目标尺寸在发起请求前可解析，未约束尺寸不会退回原图。
- 解码、变换和磁盘 I/O 不运行在 UI 线程。
- RecyclerView 回收、Fragment `onDestroyView()`、Compose 列表项离屏和页面停止时，请求与结果引用按框架契约释放。
- 预取数量、请求并发、交叉淡入淡出和缓存容量经过低内存设备测试。
- 软件与硬件 Bitmap 的选择符合像素访问、Canvas 类型、变换和图形内存限制。
- 自定义 Transformation 不调用 `recycle()` 回收框架仍拥有的输入资源。
- Coil 3 的网络依赖模块与 `Cache-Control` 策略已经显式记录。
- Android 10 / 11 收到 AVIF 时有服务端兼容回退或经过验证的库解码器。
- 平台区域解码 AVIF 只按 Android 17 能力启用。
- 监控能区分获取、各级缓存、解码、UI 提交、RenderThread 与上屏。

图片优化的验收结果应写成可复现数据：输入资源、目标像素、缓存状态、库版本、设备、刷新率、各阶段耗时和峰值内存。这样才能判断收益来自减少下载、减少解码、降低内存分配，还是缩短了图片进入显示路径后的等待。

## 参考资料

- [AOSP Android 17 `Bitmap.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java)
- [AOSP Android 17 `BitmapFactory.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/BitmapFactory.java)
- [AOSP Android 17 `BitmapRegionDecoder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)
- [AOSP Android 17 `ImageDecoder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/ImageDecoder.java)
- [AOSP Android 10 `BitmapRegionDecoder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-10.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)
- [AOSP Android 11 `BitmapRegionDecoder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-11.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)
- [AOSP Android 12 `BitmapRegionDecoder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-12.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)
- [AOSP Android 16 `BitmapRegionDecoder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)
- [Android `BitmapFactory.Options`](https://developer.android.com/reference/android/graphics/BitmapFactory.Options)
- [Android `BitmapRegionDecoder`](https://developer.android.com/reference/android/graphics/BitmapRegionDecoder)
- [Android `ImageDecoder`](https://developer.android.com/reference/android/graphics/ImageDecoder)
- [Android Bitmap 内存管理](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Android 图片格式与传输尺寸](https://developer.android.com/develop/ui/views/graphics/reduce-image-sizes)
- [Glide 5.0.9 release](https://github.com/bumptech/glide/releases/tag/v5.0.9)
- [Glide 5.0.9 `Engine.java`](https://github.com/bumptech/glide/blob/v5.0.9/library/src/main/java/com/bumptech/glide/load/engine/Engine.java)
- [Glide 5.0.7 release](https://github.com/bumptech/glide/releases/tag/v5.0.7)
- [Glide 5.0.7 `Engine.java`](https://github.com/bumptech/glide/blob/v5.0.7/library/src/main/java/com/bumptech/glide/load/engine/Engine.java)
- [Glide cache 文档](https://bumptech.github.io/glide/doc/caching.html)
- [Glide resource reuse 文档](https://bumptech.github.io/glide/doc/resourcereuse.html)
- [Glide Compose integration 状态](https://bumptech.github.io/glide/int/compose.html)
- [Coil 3.5.0 changelog](https://coil-kt.github.io/coil/changelog/)
- [Coil 3.5.0 release](https://github.com/coil-kt/coil/releases/tag/3.5.0)
- [Coil 3.5.0 `CacheStrategy.kt`](https://github.com/coil-kt/coil/blob/3.5.0/coil-network-core/src/commonMain/kotlin/coil3/network/CacheStrategy.kt)
- [Coil 3.5.0 `CacheControlCacheStrategy.kt`](https://github.com/coil-kt/coil/blob/3.5.0/coil-network-cache-control/src/commonMain/kotlin/coil3/network/cachecontrol/CacheControlCacheStrategy.kt)
- [Coil Compose 文档](https://coil-kt.github.io/coil/compose/)
- [Coil ImageLoader 文档](https://coil-kt.github.io/coil/image_loaders/)
- [Coil network 文档](https://coil-kt.github.io/coil/network/)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 17 kernel common `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
