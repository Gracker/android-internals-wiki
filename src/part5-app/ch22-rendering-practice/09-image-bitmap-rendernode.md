---
title: 图片加载、Bitmap 解码与 RenderNode
chapter: '22.9'
section: '22.9'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1; Glide 5.0.9; Coil 3.5.0; Android Developers docs
confidence: medium-high
sources:
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 资源文件的体积优化实战.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Bitmap.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/BitmapFactory.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/ImageDecoder.java @ android-17.0.0_r1
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://developer.android.com/develop/ui/views/graphics/reduce-image-sizes
- type: official
  path: https://developer.android.com/reference/android/graphics/BitmapFactory.Options
- type: official
  path: https://developer.android.com/reference/android/graphics/BitmapRegionDecoder
- type: official
  path: https://developer.android.com/reference/android/graphics/ImageDecoder
- type: library-doc
  path: https://bumptech.github.io/glide/doc/caching.html
- type: library-doc
  path: https://bumptech.github.io/glide/doc/resourcereuse.html
- type: library-doc
  path: https://coil-kt.github.io/coil/
- type: library-doc
  path: https://coil-kt.github.io/coil/image_loaders/
- type: library-release
  path: https://github.com/bumptech/glide/releases/tag/v5.0.9
- type: library-release
  path: https://github.com/coil-kt/coil/releases/tag/3.5.0
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/ImageDecoder.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/BitmapFactory.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Bitmap.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Gainmap.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java
- type: aosp
  path: frameworks/base/libs/hwui/jni/ImageDecoder.cpp
tags:
- image-loading
- glide
- coil
- bitmap-decode
- image-cache
- bitmap
- image-decoder
- decode-pipeline
- hardware-bitmap
- image-format
- mmap
- inbitmap
related_chapters:
- '22.1'
- '23.4'
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch07-smoothness/10-image-bitmap-performance.md
- src/part5-app/ch22-rendering-practice/17-hardware-bitmap-rendernode.md
- src/part5-app/ch22-rendering-practice/06-image-loading.md
- src/part5-app/ch22-rendering-practice/26-bitmap-decode-imagedecoder.md
---

# 图片加载、Bitmap 解码与 RenderNode

图片从 URL 变成屏幕像素，要经过获取压缩数据、查找各级缓存、解码、变换、持有像素、更新 UI、HWUI（Android 硬件加速 UI 渲染系统）采样，再提交窗口缓冲区直至上屏（present）。任何一段都可能成为首图慢、列表掉帧或内存峰值的来源。

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，Linux 内核观察基线固定为 `android17-6.18-2026-06_r6`。软件 Bitmap 解码完成后，宿主 View 仍要更新 DisplayList（记录待执行绘制命令的显示列表），专用渲染线程 RenderThread 再通过 HWUI 采样 Bitmap，并提交应用窗口缓冲区。硬件 Bitmap 的像素存储位于图形内存，适合只在硬件加速 Canvas 上显示；它仍占用图形资源，也不代表图片已经按期上屏。显示阶段可结合 [Android View 标准渲染路径](../../part2-performance/ch13-rendering-pipelines/01-android-view-pipeline-analysis.md) 阅读。

图片显示跨越网络或磁盘读取、解码、缩放、Bitmap 存储、纹理上传和最终绘制。Hardware Bitmap 与 RenderNode 可以减少部分复制或录制成本，但受可变性、内存和生命周期限制。

## 请求、缓存、尺寸与显示生命周期

### Glide 与 Coil：按版本和约束选型

截至 2026-08-14，第三方库相关行为以 Glide `5.0.9` 与 Coil `3.5.0` 为准。两者独立于 Android 平台发布；升级库后要重新核对默认解码器、缓存键、网络组件和 Compose API。

| 维度 | Glide 5.0.9 | Coil 3.5.0 | 评审问题 |
| --- | --- | --- | --- |
| Android View | 提供 `RequestManager`、`ViewTarget`、资源引用计数和 `BitmapPool` | `ImageView.load()` 与 `ImageRequest` 可直接使用 | 现有模块使用哪套生命周期、扩展组件和监控 |
| Compose | Compose 集成是单独的 beta 版依赖模块 | `AsyncImage`、`rememberAsyncImagePainter`、`SubcomposeAsyncImage` 是主文档 API | 能否接受 beta API；是否需要跨平台 |
| 内存资源 | 正在使用的资源（active resources）、内存缓存和资源复用池 | 单例 `ImageLoader` 的内存缓存 | 同屏尺寸、硬件位图策略、变换产生的中间资源 |
| 磁盘 | 原始数据与变换后资源可按策略缓存 | `ImageLoader` 自有磁盘缓存 | 缓存的是原始响应还是输出结果；失效标识是什么 |
| 网络 | 默认可用 HttpURLConnection，也可接入其他网络栈 | 核心依赖模块默认不含网络支持，需要 OkHttp、Ktor 或自定义 `NetworkClient` 组件 | 连接池是否共享；HTTP 缓存语义是否满足服务端协议 |

框架名称不能替代请求配置。相同 URL 在不同目标尺寸、变换、色彩配置、硬件位图策略和生命周期下，内存峰值与首帧时间都可能不同。选型应使用同一批资源、相同目标尺寸、相同缓存未命中或命中状态和相同设备做对比。

#### Glide 的使用边界

Glide 5.0.9 的 `Engine` 先查正在使用的资源和内存缓存；未命中后复用同一缓存键对应的 `EngineJob`（进行中的加载任务），否则启动新的 `DecodeJob`（解码任务）。原始数据和变换后资源的磁盘缓存策略由请求决定。加载到 `ImageView` 时，新的 `into(imageView)` 会替换该 View 上的旧请求；RecyclerView 回收后若暂时不绑定新图，应调用 `clear(imageView)`，同时清掉占位图之外的旧内容。

`Glide.with(fragment)`、`Glide.with(activity)` 或 `Glide.with(view)` 可以获得与界面关联的 `RequestManager`。传入 Application Context（应用级 Context）会得到应用级 `RequestManager`，不具备页面停止时的自动暂停语义。Glide 返回的 Bitmap 可能受引用计数和 `BitmapPool` 管理；请求清理后继续持有 Bitmap，或在 Transformation（变换实现）中手动调用 `recycle()` 回收原始 Bitmap，都可能造成内容复用错误或崩溃。

#### Coil 的使用边界

Coil 3.5.0 建议全应用共享一个 `ImageLoader`。每个实例都持有自己的内存缓存、磁盘缓存和网络资源；按页面创建实例会拆散命中率并增加常驻对象。需要不同认证或隔离域时，可以显式设计少量 `ImageLoader`，并记录它们的缓存目录和生命周期。

Compose 中，`AsyncImage` 会结合可组合项的布局约束（constraints）与 `ContentScale` 推导请求尺寸。直接调用 `rememberAsyncImagePainter(model)` 不会自动感知显示尺寸，默认请求原始尺寸；应提供 `SizeResolver`。`SubcomposeAsyncImage` 为状态插槽（slot）使用子组合（subcomposition），官方文档明确提示它不适合性能敏感的 `LazyList` 高频路径。

Coil 3 的网络行为要单独配置：

- `coil-compose` 或 `coil` 本身不提供 URL 网络获取，需要引入一个 `coil-network-*` 依赖模块；
- 3.5.0 可使用 `coil-network-okhttp`、`coil-network-ktor2` 或 `coil-network-ktor3`；
- 默认 `NetworkFetcher` 会把响应写入 Coil 磁盘缓存，但不遵循 HTTP `Cache-Control`；
- 需要遵循响应缓存头时，引入 `coil-network-cache-control` 并配置 `CacheControlCacheStrategy`；相关 `CacheStrategy` API 在该版本仍标记为 `ExperimentalCoilApi`。

这些行为与 OkHttp 自身的 HTTP 缓存不是同一层。评审缓存命中时，要记录命中的具体层和 Coil 网络组件配置。

#### 混用两套框架的成本

迁移期允许 Glide 与 Coil 并存。一个页面同时请求同一批图片时，两套内存缓存、磁盘缓存、解码任务和网络连接可能重复。迁移方案应按功能模块或页面切分，并采集两套 data source（数据来源）指标；不要在同一个 RecyclerView 中按列表项随机选择图片框架。

### 解码尺寸、像素内存与硬件位图

压缩文件大小不能代表解码后内存。4000 × 3000 的 ARGB_8888 Bitmap 仅按像素计算为：

`4000 × 3000 × 4 = 48,000,000 bytes ≈ 45.8 MiB`

显示目标为 1000 × 750 时，同配置像素约 2.86 MiB，两者像素数量相差 16 倍。行跨度（row stride，即相邻两行像素起始位置之间的字节数）、色彩配置、复用空间、辅助解码缓冲区和图形驱动资源还会增加运行时占用。

Android 8.0 / API 26 起，软件 Bitmap 的像素数据位于原生堆（native heap）。Android 17 的 `Bitmap` 通过 `NativeAllocationRegistry` 登记原生内存分配，`getAllocationByteCount()` 返回当前底层分配空间的字节数；复用过的 Bitmap 可能出现这个值大于当前 `getByteCount()`。`Bitmap.Config.HARDWARE` 的像素存放在图形内存且始终不可变：`getPixel()`、`getPixels()` 与 `copyPixelsToBuffer()` 等直接访问会抛出异常，软件 Canvas 也不能绘制它。显式复制成软件 Bitmap 等路径可能触发 GPU 回读（readback，即把图形内存读回 CPU 可访问内存），需要单独测量。

#### BitmapFactory：先读边界尺寸，再按 2 的幂采样

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

#### ImageDecoder：默认结果通常是硬件 Bitmap

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

#### 从解码完成到图片可见

图片库回调成功只说明结果已经交给显示目标（target）。软件 Bitmap 第一次被硬件 Canvas 使用时，RenderThread / GPU 可能还要准备纹理；硬件 Bitmap 省去一部分软件像素到图形资源的转换，但仍有图形内存分配、同步和采样成本。首图慢应区分：

| 现象 | 观察点 | 可能位置 |
| --- | --- | --- |
| 解码时间片（decode span）很长 | 图片库事件、工作线程的 Running（正在运行）/ Runnable（已就绪、等待 CPU）状态、I/O | 文件读取、编解码器、缩放、变换 |
| UI 回调或 View 树遍历很长 | UI 线程、ImageView / Compose 失效请求、布局 | 设置 Drawable 改变尺寸、主线程变换、过量重组 |
| UI 按时，RenderThread 首次绘制变长 | `DrawFrame`、纹理与图形内存、GPU 工作区间 | 软件 Bitmap 上传、图形分配、复杂裁剪或混合 |
| 应用帧已提交，上屏仍晚 | FrameTimeline、BLAST（应用窗口缓冲区交接）、SurfaceFlinger（系统合成服务）、HWC（硬件合成器） | 缓冲区积压、合成或显示阶段 |

这四类现象要按帧关联到同一张图片、同一次请求和同一个 FrameTimeline（关联应用、系统合成与显示阶段的帧时间线），单看图片库“加载成功”事件无法判断图片何时可见。

`getAllocationByteCount()` 适合记录单个 Bitmap 的分配空间，不能覆盖临时编解码缓冲区、硬件图形资源和缓存中的其他对象。内存分析还要看原生堆、图形资源与 dma-buf（设备间共享缓冲区）、PSS（按比例归属进程的物理内存）、GC（垃圾回收）、缺页（page fault）、内存回收（reclaim）与进程 OOM（内存不足）状态。Linux 6.18 内核基线下可补看 PSI memory（内存压力停顿）、`kswapd` 后台回收、direct reclaim（当前线程同步回收）、zram 压缩交换和 GPU 驱动等待，避免把内存回收停顿写成解码器算法问题。

### 大图与 BitmapRegionDecoder

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

### 内存、磁盘与网络缓存

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

#### 缓存键必须描述内容身份

图片框架会把尺寸、Transformation、Options 和结果类型等请求信息纳入相应缓存键，但“这个 URL 的内容版本”仍由业务和服务端提供。优先使用内容哈希或版本化 URL。URL 不变而内容会更新时，Glide 可使用 `signature`；Coil 可以使用请求数据版本或经过审查的自定义缓存键。不同用户、鉴权请求头、租户或隐私域共享缓存前，要确认缓存键和缓存目录不会串数据。

业务层再增加一份 URL → Bitmap 的强引用缓存，往往造成双份持有、错误失效和绕过内存裁剪策略。确有跨框架共享需求时，更适合共享原始文件或统一网络 / 磁盘层，并明确所有权。

#### 缓存容量由峰值场景决定

- 信息流要同时计算可见列表项、预取列表项、交叉淡入淡出（crossfade）期间的新旧 Drawable 和请求并发；扩大内存缓存无法消除同一时刻的解码峰值。
- 相册与聊天应让缩略图、预览图、原图使用不同内容标识和目标尺寸，避免原图挤掉高复用缩略图。
- 多进程各有独立堆和 `ImageLoader`。只有展示图片的进程才应初始化完整图片栈。
- 收到系统内存压力回调时，先让框架按策略裁剪缓存；页面还要释放 RecyclerView adapter（适配器）、Compose 状态、预取结果和自建强引用。
- 清空整个缓存会把后续访问变成冷加载。它属于诊断或明确的账户 / 隐私清理操作，不是常规掉帧修复。

#### 网络缓存要验证客户端实现

服务端应提供版本化 URL，或正确的 `ETag`、`Last-Modified`、`Cache-Control` 与 `Vary`。客户端是否使用这些响应头取决于网络组件：

- Glide 的原始数据磁盘缓存与底层 HTTP 缓存是两层；接入 OkHttp 后也要确认是否配置了 `Cache`；
- Coil 3 默认磁盘缓存行为不会自动遵循 `Cache-Control`；
- 使用带签名 URL 时，短期 token（临时凭证）进入 URL 可能降低缓存命中，应由安全与后端共同设计稳定内容标识；
- 失败响应、重定向和认证差异也要进入缓存测试。

命中率统计应分成正在使用的资源、内存、变换结果磁盘、原始数据磁盘、HTTP 与网络六类。只记录 `from cache` 无法判断下一步该调整哪一层。

### AVIF、WebP、JPEG 与 PNG

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

### 诊断与上线检查

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

## 解码、像素存储与绘制提交

加载框架控制请求和缓存，解码与绘制阶段决定像素格式、内存位置和 GPU 上传。目标尺寸应在两层保持一致。

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Java API：`ImageDecoder.java`、`BitmapFactory.java`、`Bitmap.java`
> - Native 实现：`frameworks/base/libs/hwui/jni/ImageDecoder.cpp`、`BitmapFactory.cpp`
>
> 这里的“Android 17 行为”以这些源码为准。编解码器实现、图形内存分配和内存统计还会受 SoC（片上系统）、厂商图形缓冲分配器 `gralloc` 与驱动影响，因此设备实测仍是性能结论的一部分。

讨论范围是压缩图片数据如何变成可绘制像素，以及这些像素如何进入 Android 17 的 HWUI（Android 硬件加速 UI 渲染器）路径。图片请求、缓存与框架选型已由前一节建立边界；本节继续深入 Hardware Bitmap 与 RenderNode 的绘制侧行为，Bitmap 内存治理见 [23.4 Bitmap 与图片内存优化](../ch23-memory-practice/04-bitmap-optimization.md)。

### 1. 一次解码包含哪些工作

一次静态图片解码至少包含以下工作：

1. 从文件描述符、流、字节数组或 `ByteBuffer` 读取压缩数据；
2. 识别格式并解析头信息，得到原始尺寸、MIME 类型、动画与色彩空间信息；
3. 根据目标尺寸、采样、裁剪、色彩空间和内存策略确定输出规格；
4. 编解码器把压缩数据还原成可写像素；
5. 按需要执行缩放、裁剪、色彩转换、增益图提取或 `PostProcessor`；
6. 把结果放入普通原生堆（native heap）、共享内存或 Hardware Bitmap；
7. UI 使用结果时，HWUI 记录绘制命令，其渲染线程 RenderThread 再把图片作为采样资源提交给 GPU。

这几步不会因为调用了一个 Java 方法而变成同一类成本。文件读取受页缓存和存储影响，像素解码主要消耗 CPU 与内存带宽，Hardware Bitmap 的创建还包含图形缓冲分配和上传。诊断时要区分阶段，不能只记录 `decodeBitmap()` 的总耗时就把它直接归因于格式。

压缩文件大小也不能代表解码后内存。普通 `ARGB_8888` 图片的像素存储通常接近 `rowBytes × height`，其中 `rowBytes` 是一行像素实际占用的字节数。行对齐、色彩格式、增益图和中间缓冲会让实际分配不同于简单的 `width × height × 4`。

### 2. ImageDecoder 与 BitmapFactory 的边界

`BitmapFactory` 和 `ImageDecoder` 都是同步 API。它们适合在工作线程调用，但不会自行创建后台任务。

`ImageDecoder.decodeBitmap()` 与 `decodeDrawable()` 标注了 `@WorkerThread`。`OnHeaderDecodedListener` 是头信息回调，不是异步通知：它在调用解码方法的同一线程执行，并且发生在方法返回之前。调用方可以在已经读到头信息、尚未开始完整像素解码时配置本次请求。

| 维度 | `BitmapFactory` | `ImageDecoder` |
| --- | --- | --- |
| 初始版本 | API 1 | API 28 |
| 调用语义 | 同步 | 同步 |
| 头信息决策 | `inJustDecodeBounds` 后再次调用解码 | 同一次调用中的 `OnHeaderDecodedListener` |
| 缩小输出 | `inSampleSize`，原生解码器最终按 2 的幂处理；资源密度还可能追加缩放 | `setTargetSampleSize()` 或 `setTargetSize()` |
| 像素复用 | `Options.inBitmap` | 没有把现有 Bitmap 设为目标的公开 API |
| 存储选择 | `inPreferredConfig` 等选项 | DEFAULT、SOFTWARE、SHARED_MEMORY、HARDWARE 四种 allocator（分配器） |
| 静态输出 | `Bitmap` | `Bitmap`、`BitmapDrawable` 或 `NinePatchDrawable` |
| 动画输出 | 不负责通用动画 Drawable | `decodeDrawable()` 可返回 `AnimatedImageDrawable` |
| 损坏输入 | 返回 `null`、抛异常或给出部分结果，取决于入口与错误 | `OnPartialImageListener` 决定是否接受可用的部分结果 |

`ImageDecoder.setCrop()` 只是从已经解码、缩放后的结果中裁剪输出。官方文档明确说明它不替代 `BitmapRegionDecoder.decodeRegion()`。超大图只显示局部时，应先判断格式和区域解码能力，不能把 `setCrop()` 当作降低完整解码成本的保证。

#### 2.1 正确使用 ImageDecoder

这段代码在调用方提供的后台调度器中解码一张只用于显示的静态图片，并在头信息回调中限制输出尺寸。

```kotlin
@RequiresApi(Build.VERSION_CODES.P)
suspend fun decodeForDisplay(
    resolver: ContentResolver,
    uri: Uri,
    targetWidth: Int,
    targetHeight: Int,
    decodeDispatcher: CoroutineDispatcher,
): Bitmap = withContext(decodeDispatcher) {
    require(targetWidth > 0 && targetHeight > 0)

    val source = ImageDecoder.createSource(resolver, uri)
    ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
        val sourceWidth = info.size.width
        val sourceHeight = info.size.height
        val scale = minOf(
            1f,
            targetWidth.toFloat() / sourceWidth,
            targetHeight.toFloat() / sourceHeight,
        )

        decoder.setTargetSize(
            (sourceWidth * scale).toInt().coerceAtLeast(1),
            (sourceHeight * scale).toInt().coerceAtLeast(1),
        )
        decoder.setAllocator(ImageDecoder.ALLOCATOR_DEFAULT)
    }
}
```

`withContext` 决定代码在哪个线程池执行，`ImageDecoder` 本身仍是同步调用。协程被取消时可以阻止排队任务开始或阻止结果交付，但已经进入原生编解码器的任务不一定会立即中断。列表快速滑动时，结果返回后还要核对请求身份。

若输出需要 `getPixel()`、`copyPixelsToBuffer()`、软件 `Canvas` 或后续原地修改，应显式选择 `ALLOCATOR_SOFTWARE`。如果只是在解码后画圆角，`ImageDecoder.setPostProcessor()` 可以先在内部软件像素上绘制，再生成不可变结果；它与“业务拿到结果后仍能修改像素”是两件事。

#### 2.2 BitmapFactory 的两阶段尺寸决策

文件来源必须使用 `BitmapFactory` 时，第一次调用只读取边界，第二次才分配像素：

```kotlin
fun decodeSampledFile(
    path: String,
    requestedWidth: Int,
    requestedHeight: Int,
): Bitmap? {
    require(requestedWidth > 0 && requestedHeight > 0)

    val bounds = BitmapFactory.Options().apply {
        inJustDecodeBounds = true
    }
    BitmapFactory.decodeFile(path, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

    var sampleSize = 1
    while (
        bounds.outWidth / (sampleSize * 2) >= requestedWidth &&
        bounds.outHeight / (sampleSize * 2) >= requestedHeight
    ) {
        sampleSize *= 2
    }

    val decodeOptions = BitmapFactory.Options().apply {
        inSampleSize = sampleSize
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return BitmapFactory.decodeFile(path, decodeOptions)
}
```

这里的 `inSampleSize` 只做粗粒度降采样。若 View 需要精确尺寸，后续仍可能发生缩放。对资源解码还要考虑 `inDensity` 与 `inTargetDensity`，不能只按文件原始宽高推断最终 Bitmap 尺寸。

### 3. Source 与文件 I/O：文件来源不等于 mmap

Android 17 的 `ImageDecoder.Source` 只是数据来源描述，创建 Source 通常不会完成像素解码。读取发生在 `decodeBitmap()` 或 `decodeDrawable()` 中。

`android-17.0.0_r1` 的具体路径如下：

- `File` 来源创建 `FileInputStream`。文件描述符可用时进入原生层的 `nCreate`；
- 原生层代码复制文件描述符，调用 `fdopen()`，再构造 `SkFILEStream`；
- `content://` 来源先尝试 `AssetFileDescriptor`，无法取得时回退到 `InputStream`；
- Java `InputStream` 在原生层由输入流适配器包装，并增加满足编解码器探测需求的前置缓冲；
- `ByteBuffer` 与 `byte[]` 使用各自的流适配器。

`mmap` 是把文件区间映射到进程虚拟地址空间的内存映射机制。源码没有承诺文件 Source 必然使用 `mmap`。`SkFILEStream`、C 标准 I/O、内核页缓存和具体编解码器可以减少重复物理读取，但这不等于零拷贝。即使应用自己建立 `MappedByteBuffer`，编解码器仍要读取压缩数据并写入新的像素存储。

是否采用映射应由访问模式决定：

- 多次随机访问同一个本地大文件时，映射可能减少应用层缓冲区管理；
- 顺序读取一次的图片可能从普通文件流和页缓存获得相近效果；
- `content://` 的真实来源可能是本地文件、Binder 代理、云端文档或动态生成数据；
- 加密缓存、压缩容器和不能随机改变读取位置的流会改变 I/O 路径。

测量文件 I/O 时，应区分冷缓存与热缓存，并把网络下载、解密、磁盘读取和像素解码分别计时。固定文件大小阈值无法跨设备判断内存映射是否更优。

### 4. Hardware Bitmap：图形存储不等于硬件编解码

`Bitmap.Config.HARDWARE` 表示结果的像素由图形缓冲持有，且应用不能通过普通 CPU 像素 API 读写。它没有承诺 JPEG、PNG、WebP、HEIF 或 AVIF 一定由专用硬件编解码器处理。

Android 17 的 `ImageDecoder_nDecodeBitmap()` 展示了静态图的关键顺序：

1. 根据目标尺寸、色彩空间和内存策略建立一个可写 `SkBitmap`，它是 Skia 内部的像素容器；
2. SOFTWARE、DEFAULT 与 HARDWARE 静态图路径先通过 `Bitmap::allocateHeapBitmap()` 分配普通像素；SHARED_MEMORY 使用 `allocateAshmemBitmap()`；
3. `decoder->decode()` 把像素写入这块 CPU 可写存储；
4. `PostProcessor` 如存在，会在该 Bitmap 的 `Canvas` 上执行；
5. 若最终结果应为 Hardware Bitmap，`Bitmap::allocateHardwareBitmap(bm)` 再创建图形缓冲并上传；
6. DEFAULT 的硬件分配失败时可以返回软件 Bitmap，HARDWARE 被显式要求时则报告失败。

因此 Hardware Bitmap 没有消除 CPU 解码和像素传输。它把图形缓冲准备放在解码结果构建阶段，避免普通软件 Bitmap 在首次绘制时再由 HWUI 建立纹理副本。成本发生时间和后续存储形态改变了，不能写成“图片由 GPU 直接解码”。

#### 4.1 四种 allocator（分配器）的含义

| allocator（分配器） | Android 17 公开语义 | 适合场景 | 主要约束 |
| --- | --- | --- | --- |
| `ALLOCATOR_DEFAULT` | 通常尝试 Hardware Bitmap，不兼容或分配失败时可回退软件结果 | 静态、只上屏图片 | 不能假设结果一定是 HARDWARE |
| `ALLOCATOR_SOFTWARE` | 普通软件像素存储 | CPU 读写、软件 Canvas、业务后处理 | 绘制时可能需要建立或更新 GPU 采样资源 |
| `ALLOCATOR_SHARED_MEMORY` | 共享内存像素 | 跨进程传递且确有共享需求 | 仍需计算像素内存与 IPC 生命周期 |
| `ALLOCATOR_HARDWARE` | 必须返回 `Config.HARDWARE` | 调用方能满足全部硬件限制的静态图 | 与可变输出、透明度蒙版（alpha mask）等选项冲突时抛异常 |

官方 API 文档说 DEFAULT “通常”产生 Hardware Bitmap，也保留小图走软件或不兼容时回退的权利。业务判断必须查看返回值的 `config`，不能把默认策略当作固定兼容性契约。

#### 4.2 可变性、后处理和动画

`setMutableRequired(true)` 只适用于 `decodeBitmap()`，并与 `ALLOCATOR_HARDWARE` 冲突。`decodeDrawable()` 请求可变结果会抛出 `IllegalStateException`。

`setPostProcessor()` 在解码和缩放后获得一个 `Canvas`，适合一次性绘制遮罩、圆角或颜色效果。Android 17 原生实现先完成这一步，再尝试生成 Hardware Bitmap；使用 PostProcessor 不会把最终结果限制为软件 Bitmap。如果业务要在返回后继续修改，仍需可变的软件结果。

当输入是动画且调用 `decodeDrawable()` 时，Android 17 返回 `AnimatedImageDrawable`。allocator 对动画 Drawable 会被忽略，数据源还可能在返回后继续被动画对象读取。由 `byte[]` 或 `ByteBuffer` 创建动画 Source 时，不得在动画仍使用数据时修改底层内容。

#### 4.3 Hardware Bitmap 在显示管线中的位置

Hardware Bitmap 是应用绘制命令使用的资源，不会因为自身存在就成为 SurfaceFlinger 图层（layer）。标准窗口仍按这条路径显示：

`UI Thread 记录 DisplayList` → `RenderThread/HWUI` → `Skia GPU` → `App Window buffer` → `BLAST` → `SurfaceFlinger` → `HWC`

其中 `DisplayList` 是录制后的绘制命令列表，BLAST 负责衔接应用窗口缓冲队列与 SurfaceFlinger。普通软件 Bitmap 可能在 RenderThread 侧产生上传；Hardware Bitmap 已具备 GPU 可采样的图形存储。二者最终都由宿主窗口提交，除非应用另行把 `HardwareBuffer` 交给独立 `SurfaceControl`。

### 5. PNG、JPEG、WebP、HEIF 与 AVIF：格式没有固定性能排名

文件更小只代表下载、磁盘和缓存成本可能下降，不代表像素解码更快。格式复杂度、图片内容、位深、透明通道、动画、增益图、目标尺寸、编解码器实现和 SoC 都会改变结果。

| 格式 | 稳定特征 | 评测时容易遗漏的变量 |
| --- | --- | --- |
| JPEG | 常用于有损照片，无 alpha | 渐进式编码（progressive）、色度采样、EXIF 方向元数据、目标色彩空间 |
| PNG | 无损，支持 alpha | 滤波类型、位深、透明通道、图片内容可压缩性 |
| WebP | 支持有损、无损、alpha 与动画 | 静态和动画路径不同，编码参数差异很大 |
| HEIF | 容器可承载 HEVC 图像及附加信息 | 设备编解码器、位深、增益图、厂商实现 |
| AVIF | 基于 AV1 图像编码，支持较丰富的色彩能力 | 编码配置、位深、设备实现、目标尺寸 |

Android 17 的 `BitmapRegionDecoder.java` 明确列出 JPEG、PNG、WebP、HEIF 和 AVIF。这个列表表示当前平台区域解码器接受这些格式，不表示旧 API 版本都具备相同能力，也不表示所有输入特性都能等价处理。版本兼容必须在应用最低 API 和目标设备上验证。

#### 5.1 Ultra HDR 与 Gainmap

Android 14 起，Ultra HDR 图片可以在 SDR 基础图之外携带增益图（gainmap）。增益图记录从 SDR 基础图恢复 HDR 亮度所需的增益信息。Android 17 的 `BitmapFactory.cpp` 会从编解码器取得增益图，解码为独立 Bitmap 并附着到基础 Bitmap；Hardware Bitmap 路径还会为增益图创建对应的硬件像素存储。`Gainmap.java` 保存增益图内容 Bitmap 与显示参数。

Android 17 的 `ImageDecoder.cpp` 在设置 `PostProcessor` 时跳过自动增益图提取，因为平台无法推断任意 Canvas 处理应怎样等价作用于增益图。Ultra HDR 输入若还要做解码期后处理，应同时验证 `hasGainmap()` 和显示效果，不能只检查最终 Bitmap 是否为 `Config.HARDWARE`。

计算这类图片的驻留内存与解码峰值时，要纳入基础 Bitmap、增益图 Bitmap 和解码、缩放期间的临时缓冲；生成硬件结果时，软件像素与硬件像素存储还可能短暂共存。`Bitmap.getAllocationByteCount()` 只描述当前 Bitmap 的底层像素存储，不能代表附着的增益图和全部图形分配，因此不存在可跨设备套用的固定倍数。实测时应同时记录两层 Bitmap 的尺寸、配置、行跨度（stride），以及进程 Graphics、Native Heap 和比例分摊内存（PSS）的变化。

`bitmap.setGainmap(null)` 只解除基础 Bitmap 对增益图的关联；其他 Java 或原生层引用结束后，对应资源才具备释放条件。移除增益图还会改变 HDR 效果、显示能力适配和色彩一致性，不应作为低端机的无条件节省内存开关。

选择线上格式时，应对同一视觉内容记录：

- 编码字节数与下载时间；
- 头信息解析和完整解码耗时；
- 输出 `width`、`height`、`config`、色彩空间与 `allocationByteCount`；
- 解码期间的 CPU 时间、峰值内存和能耗；
- 首次绘制是否出现软件 Bitmap 上传；
- 失败率，以及服务端回退格式是否生效。

一台旗舰设备的单次结果不足以推导全量策略。设备分组应来自实际 SoC、系统版本、内存等级和业务样本，格式性能则由各组实测给出。

### 6. 解码线程调度：限制并发的依据是 CPU 与内存

专用线程、线程池和协程解决的是任务组织问题，不能改变编解码器的计算量。

| 模型 | 特点 | 适用条件 |
| --- | --- | --- |
| 单个专用线程 | 顺序明确，内存峰值容易控制 | 请求稀疏，或单次解码占用较大 |
| 有界线程池 | 可以提高吞吐，也会增加 CPU 竞争和同时存活的中间像素 | 列表、多路图片请求，且已通过设备实测确定并发上限 |
| 协程 + 有界调度器（dispatcher） | 生命周期与请求取消更易表达 | Kotlin 项目；底层仍需要受控的执行器或并行度 |

`Dispatchers.IO` 的名字不表示任务是轻量 I/O。图片解码在读完数据后会长时间占用 CPU，和数据库、网络或文件任务共用一个宽线程池时可能互相影响。自定义图片管线应给解码建立可观测的有界执行资源，并根据以下信号调节：

- 主线程与 RenderThread 已可运行但仍在等待 CPU 的调度延迟；
- 单次解码 CPU 时间和墙钟时间；
- 同时解码时的原生堆、共享内存或图形内存峰值；
- 视口请求命中率与被取消任务比例；
- 不同设备组的吞吐和卡顿变化。

并发数不应仅按 CPU 核数计算。两张大尺寸、广色域图片可能先受内存带宽和分配峰值限制；多张小缩略图则可能受调度与请求管理成本限制。

#### 6.1 取消的真实边界

图片请求至少有三种取消时机：

1. 尚在队列中：直接移除，不进入编解码器；
2. 正在读取自定义数据源：关闭来源或让读取逻辑响应取消；
3. 已进入 `BitmapFactory` 或 `ImageDecoder` 原生层解码：公开 API 没有可靠的逐请求强制中断协议。

所以列表复用时必须在完成回调处比较请求键、条目标识或代次编号（generation）。旧任务返回的 Bitmap 可以进入合适的缓存，但不能覆盖已绑定新数据的 View 或 Compose 状态。

### 7. inBitmap：BitmapFactory 能复用，ImageDecoder 不能

`BitmapFactory.Options.inBitmap` 允许符合条件的解码复用一块可变 Bitmap 存储。Android 17 原生实现会检查现有 `allocationByteCount`，并在有密度缩放或其他中间步骤时选择不同分配器。

约束应按公开 API 理解：

- Android 4.4 / API 19 起，候选 Bitmap 必须可变，且新结果的字节数不大于候选的 `allocationByteCount`；
- API 19 以前还有额外限制：输入需为 JPEG 或 PNG、尺寸相同、`inSampleSize == 1`；
- `Config.HARDWARE` 始终不可作为 `inBitmap`；
- 候选不能已回收；
- 解码方法可能因为候选不兼容而抛 `IllegalArgumentException`；
- 无论是否期待复用，都必须使用解码方法的返回值，不能直接假设返回的就是候选对象。

`ImageDecoder` 没有 `setTargetBitmap()`，也没有等价的公开复用入口。它可以选择目标尺寸和分配器，但不能把应用提供的 Bitmap 当成静态图解码目标。图片库若在某条路径切换到 ImageDecoder，也要重新评估原有 Bitmap 复用池在“解码目标复用”上的收益。

手工维护池还要证明对象已经不再显示、不会被另一个请求并发使用，并处理色彩格式与容量匹配。大多数应用应优先使用成熟图片库的缓存和复用策略；自定义池应记录命中、拒绝、错误与峰值内存，无需追求一个通用命中率阈值。

### 8. Android 17 的 Bitmap 内存模型

官方 Bitmap 内存文档给出的版本历史是：

| 平台区间 | 像素数据位置 |
| --- | --- |
| Android 2.3.3 / API 10 及以下 | 原生内存，与 Dalvik 堆中的 Bitmap 对象分离 |
| Android 3.0 / API 11 至 Android 7.1 / API 25 | 与 Bitmap 对象一起计入 Dalvik/ART 托管堆 |
| Android 8.0 / API 26 及以上 | 原生堆 |

Android 17 的普通 Bitmap Java 对象通过 `NativeAllocationRegistry` 关联原生分配。这个注册机制帮助运行时感知原生内存压力和释放动作，不表示像素转回 Java 托管堆，也不保证原生分配会在 Java 引用失效的瞬间释放。

#### 8.1 ashmem 与共享像素

`ashmem` 是 Android 的匿名共享内存机制。Android 17 的 ImageDecoder 在 `ALLOCATOR_SHARED_MEMORY` 路径调用 `Bitmap::allocateAshmemBitmap()`；`Bitmap.java` 还保留 `createAshmemBitmap()`、ashmem 检查和用于跨进程序列化的 Parcel 处理。

ashmem 在 Android 17 中仍有明确的共享像素用途。普通软件 Bitmap 默认使用原生堆；跨进程共享、Parcel 或指定共享内存分配器等场景才需要分析 ashmem。

共享内存不会降低解码后的像素总量。它改变了后端存储和跨进程共享方式，还会引入文件描述符、映射和对象生命周期问题。

#### 8.2 HardwareBuffer、dma-buf 与厂商实现

Hardware Bitmap 可以通过 `Bitmap.getHardwareBuffer()` 取得 `HardwareBuffer`。应用层拿到的是标准化的 AHardwareBuffer/HardwareBuffer 图形缓冲句柄；实际 `gralloc` 分配堆、压缩布局、IOMMU（I/O 内存管理单元）映射与统计归类由设备实现决定。

在 `android17-6.18-2026-06_r6` 内核基线下，图形缓冲跨设备或跨进程共享通常会使用 Linux 的共享缓冲机制 dma-buf，生产者和消费者同步会关联 dma-fence。这个机制不能反向证明“每个 Hardware Bitmap 都来自相同分配堆、采用相同物理布局”，也不能只凭一个文件描述符（FD）推断 GPU 已完成写入。

#### 8.3 怎样看内存统计

这组命令同时观察进程级 PSS 分类和图形缓冲信息，避免只凭某一个字段定性。

```bash
adb shell dumpsys meminfo your.package.name
adb shell dumpsys gfxinfo your.package.name
adb shell dumpsys SurfaceFlinger
```

`dumpsys meminfo` 中 Native Heap、Graphics、GL 和 Other 的归类依赖 Android 版本、图形内存统计接口 memtrack HAL 与厂商实现。PSS 表示按共享关系折算后的物理内存贡献，与某个 Java 对象的独占字节数含义不同。应用内的 `allocationByteCount`、进程 PSS、原生堆分析器 heapprofd 和图形缓冲统计应互相校验。

### 9. FrameMetrics 与 Perfetto：一个看帧，一个看解码

#### 9.1 FrameMetrics 不能直接测后台解码

Android 17 的 `FrameMetrics` 公开指标包括：

- `LAYOUT_MEASURE_DURATION`
- `DRAW_DURATION`
- `SYNC_DURATION`
- `COMMAND_ISSUE_DURATION`
- `SWAP_BUFFERS_DURATION`
- `TOTAL_DURATION`
- `GPU_DURATION`
- `DEADLINE`

这些指标描述窗口帧的 UI/HWUI/GPU 阶段。后台图片解码不计入这些时长字段，只会通过三种间接方式影响帧：

- 错误地在主线程解码，增加垂直同步信号（VSync）的响应延迟或某个 UI 阶段；
- 后台解码占用 CPU、内存带宽或触发内存回收，使 UI/RenderThread 调度变差；
- 软件 Bitmap 首次绘制需要准备 GPU 采样资源，影响 RenderThread 或 GPU。

所以 FrameMetrics 适合回答“用户看到的窗口帧是否受影响”，无法给出某一次后台图片解码的耗时。旧文案中的 `LAYOUT_DRAW_TIME`、`DRAW_TIME`、`SWAP_BUFFERS_TIME` 也不是 Android 17 的公开常量名。

#### 9.2 Perfetto 中的 Android 17 源码切片

`trace` 是系统跟踪中的带时间区间事件，Perfetto 会把这类区间显示为切片。`ImageDecoder.java` 在 Android 17 记录这些资源 trace：

- `ImageDecoder#decodeBitmap`
- `ImageDecoder#decodeDrawable`
- 内层描述 `ID#w=<sourceWidth>;h=<sourceHeight>;dw=<targetWidth>;dh=<targetHeight>;src=<source>`

原生层的 `ImageDecoder_nDecodeBitmap()` 还记录 `Decoding <width>x<height> bitmap`。这些切片可以确认一次调用的总区间、目标尺寸和原生像素解码区间，但没有自动把格式探测、文件读取、颜色转换、上传全部分成独立公开阶段。

这段代码给业务自己的获取、解码和交付阶段增加同一个请求标识，便于与系统切片对齐。

```kotlin
inline fun <T> tracedImageStage(
    requestId: String,
    stage: String,
    block: () -> T,
): T {
    Trace.beginSection("Image:$stage:$requestId")
    return try {
        block()
    } finally {
        Trace.endSection()
    }
}
```

`beginSection()` 与 `endSection()` 必须在同一线程成对执行，切片名称还应控制长度并避免写入用户隐私。使用这层标记后，可以在 Perfetto 中把应用排队、系统解码和结果绑定关联到同一个请求。

一次可靠的线下分析应同时检查：

1. 应用自定义请求、获取、解码和交付切片；
2. `ImageDecoder#decodeBitmap` 或 `BitmapFactory` 调用所在的线程；
3. `sched` 调度事件中 UI Thread、RenderThread 与解码线程已可运行但仍在等待 CPU 的时长；
4. FrameTimeline 帧时间线中受影响的窗口帧；
5. RenderThread/GPU 是否在软件 Bitmap 首次出现时增加资源准备成本；
6. heapprofd、Java 托管堆与 `dumpsys meminfo` 中的分配峰值；
7. 冷缓存和热缓存是否混在同一组数据里。

不要编写依赖并不存在的 `Bitmap#allocate` 切片参数的 SQL。若平台源码没有记录所需字段，应由应用 trace counter（轨迹计数器）、请求日志或内存采样补齐。

### 10. 九宫格和瀑布流的调度策略

列表图片管线的目标，是让当前视口在内存可控的前提下及时得到正确尺寸的结果。

设计时依次确定：

1. **请求身份**：URL、目标尺寸、变换、色彩策略和业务版本共同决定缓存键（key）；
2. **目标尺寸**：布局尺寸确定后再请求，避免按原图解码后立即缩小；
3. **任务去重**：相同缓存键的并发请求共享获取和解码工作；
4. **优先级**：视口内高于预取，滚动方向上的近邻高于远端；
5. **取消与交付校验**：离开视口时取消排队任务，完成后核对条目身份；
6. **有界并发**：同时执行数由设备测量和图片尺寸决定；
7. **内存预算**：同时存活的解码中间结果、内存缓存和待上传 Bitmap 都要计入；
8. **预取验证**：记录预取命中和浪费，不能只看缓存命中率。

按 dp（密度无关像素）把图片固定分为“小、中、大”不能准确估计内存。解码目标最终是像素尺寸，还会受屏幕密度、输出配置、广色域和增益图影响。预算至少应使用预计 `rowBytes × height`，解码完成后再用实际 `allocationByteCount` 校准。

动态并发也不应只由上一帧是否超过某个毫秒值控制。刷新率、FrameTimeline 记录的帧截止时间（deadline）、CPU 压力和图片内存峰值需要共同判断；频繁改变并发本身还会造成队列抖动。可按设备组离线确定安全区间，线上只做缓慢、可回退的调整。

### 11. Glide、Coil 与 Picasso：先确认依赖版本的真实路径

图片库的默认解码器、Hardware Bitmap 条件、线程配置和缓存策略会随版本改变。不能用“Glide 永远走 ImageDecoder”“Coil 固定使用某个协程调度器”或“Picasso 已停止维护”这类未经当前版本源码确认的结论选型。

| 框架 | 官方资料可确认的能力 | 主要核查点 |
| --- | --- | --- |
| Glide 4 | 请求生命周期、内存/磁盘缓存、`BitmapPool`、可配置 Hardware Bitmap | 当前版本是否启用 ImageDecoder；该路径不能使用 `inBitmap` 作为解码目标 |
| Coil 3 | Interceptor、Mapper、Keyer、Fetcher、Decoder 组件链，内存/磁盘缓存 | 注册了哪个 Decoder、`allowHardware` 与变换是否要求软件像素 |
| Picasso | ImageView 复用处理、请求取消、变换与缓存 | 当前依赖版本和源码中采用的解码器、网络缓存实际由谁提供 |

选择时应优先检查项目已经使用的 UI 技术、现有缓存命中、定制格式、生命周期接入和可观测性。成熟框架能处理大量边界，但不能替应用决定服务端格式、设备分组和业务内存预算。

若性能问题只发生在少数请求，先从框架的请求监听器、事件监听或自定义解码器取得分阶段数据。直接绕开框架自建下载、缓存、解码和取消系统，往往会增加重复请求与生命周期错误。

### 12. Android 17 的 ImageDecoder 新增项

Android 17 / API 37 的公开 API 差异为 `ImageDecoder` 增加了四个默认头信息监听方法：

- `setDefaultThreadListener()` / `getDefaultThreadListener()`
- `setDefaultProcessListener()` / `getDefaultProcessListener()`

Android 17 源码中的调用顺序是：

1. 当前线程设置了线程级监听器时，先调用它，并跳过进程级监听器；
2. 当前线程没有线程级监听器时，调用进程级监听器；
3. 本次 `decodeBitmap()` 或 `decodeDrawable()` 显式传入的监听器始终随后执行。

线程级监听器存在 `ThreadLocal` 中，每个线程各自保存一份值；进程级监听器则由进程内所有线程共享。它们适合由基础设施统一附加保守默认值或观测逻辑，但有两个工程风险：

- 进程级设置会影响同进程内的图片库和其他模块；
- 显式监听器后执行，可以覆盖默认监听器设置的参数。

业务请求若只需要配置自己的尺寸、分配器或颜色空间，继续使用每次调用的显式监听器更清楚。使用默认监听器时，还要明确安装、覆盖和清理时机，避免测试或线程池复用带来隐藏状态。

`setTargetColorSpace()`、`setOnPartialImageListener()` 和四种分配器都早于 API 37，不能列为 Android 17 新增能力。Android 17 的公开变化应以 API 差异中的这四个监听方法为准。

### 13. RenderNode 与首次纹理准备

`RenderNode` 是 HWUI 中可跨帧复用的绘制节点，`DisplayList` 是它录制的绘制命令列表。Hardware Bitmap 进入 View 或 Compose 后，仍是宿主 RenderNode 的 DisplayList 所引用的图片资源。RenderNode 保存命令和属性，不等于缓存整块栅格结果；`translation`、`scale`、`alpha` 等属性可在内容不变时复用已录制命令，图片对象或绘制内容变化仍要重录。

`RecordingCanvas` 会保留所画 Bitmap 的引用，因此业务缓存移除对象，不代表仍存活的 View 或 RenderNode 已立即释放它；自建 RenderNode 结束生命周期时可调用 `discardDisplayList()`，框架 View 的内部节点交给框架管理。

Android 17 的 HWUI 对非 Hardware Bitmap 可进入 `prepareToDraw()` / `PinAsTexture()` 的显式纹理准备分支；Hardware Bitmap 已在创建阶段完成主要图形缓冲上传，所以跳过这段路径。收益是移动工作发生的时间和存储形态，不是让上传消失：格式转换、AHardwareBuffer 分配、GL/Vulkan 提交和驱动延迟仍可能落在解码完成前或首次使用时。

对照实验应固定同一图片字节、目标尺寸、色彩空间、缓存冷热和页面，分别采集软件 Bitmap 直接显示、软件 Bitmap 提前 `prepareToDraw()`、Hardware Bitmap 显示，以及三组内存缓存命中。比较从请求开始到目标帧呈现（present）的总等待，并记录解码、上传或准备切片、`DrawFrame`、GPU 完成时刻和 Graphics、dma-buf、PSS。若 Hardware 组首绘更稳定但解码完成更晚，只能说明成本前移；端到端是否改善仍要看总等待。

Hardware Bitmap 不会变成 SurfaceFlinger 独立图层，`computeApproximateMemoryUsage()` 也不包含子 RenderNode 和 Bitmap。页面退出后的评审要同时检查图片库仍在使用的资源（active resource）、View、Drawable 和 DisplayList 引用、Graphics/GL/PSS、dma-buf、GPU 内存与 FD 趋势；不能按“每张图固定一个 FD”或 `width × height × 4` 估算完整代价。

### 14. 错误恢复与安全边界

`OnPartialImageListener` 在编解码器报告输入不完整或数据错误后收到 `DecodeException`。返回接受只表示调用方愿意使用当前可得到的结果，不表示平台提供渐进式网络图片流，也不表示损坏内容已经安全。

对不可信图片来源，应同时限制：

- 压缩数据来源、协议和下载字节数；
- 头信息中声明的尺寸、帧数和色彩信息；
- 目标解码尺寸与同时解码数量；
- 超时、取消和失败回退；
- 原生编解码器安全更新对应的系统版本。

Android 17 源码中存在受特性开关（feature flag）保护的解码分配限制实现，但它不属于 API 37 已确认的稳定公开契约。应用不能把尚未公开的接口当作生产保护，应在请求层做尺寸预检和内存预算。

### 15. 评审清单

遇到图片解码或首次绘制问题时，依次核查：

- 解码是否在工作线程，头信息监听器是否被误解成异步；
- 输出像素尺寸是否接近实际显示尺寸；
- 采样 API 是否写成 `setTargetSampleSize()`；`ImageDecoder` 没有 `setSampleSize()`；
- 业务是否写了不存在的 `ImageDecoder.setTargetBitmap()`；
- CPU 读写需求是否与分配器匹配；
- Hardware Bitmap 是否被误写成专用硬件编解码器；
- 文件 Source 是否被无证据地描述成固定内存映射；
- `setCrop()` 是否被误当成区域解码；
- `inBitmap` 候选是否可变、容量足够且不再显示；
- 动画 Drawable 是否仍依赖原始字节数组、`ByteBuffer` 或流；
- FrameMetrics 是否只用于帧影响，解码耗时是否另有 trace 记录；
- 格式性能是否来自同尺寸、同设备、冷热缓存分开的测量；
- 原生堆、共享内存和图形内存是否用多种观测互相校验。

### 解码与绘制小结

Bitmap 解码优化需要控制输出像素、明确存储需求，并把 I/O、编解码器、分配、上传和绘制分别测量。

`ImageDecoder` 提供同一次同步调用中的头信息配置、四种分配器、静态与动画 Drawable 支持；它不提供现有 Bitmap 复用，也不会自动把工作移到后台。`BitmapFactory` 仍是有效且持续维护的 API，尤其适合需要 `inBitmap` 的成熟管线。

Hardware Bitmap 解决的是最终图形存储与绘制准备问题，不等同于硬件解码。Android 17 的静态图源码显示，CPU 可写像素解码完成后才分配 Hardware Bitmap。这一顺序可以解释“解码变慢但首绘更稳定”或“软件 Bitmap 解码快但首次显示多一次资源准备”等现象。

## 全文小结

图片管线要以同一个请求身份串起获取、各级缓存、目标尺寸、解码、变换、结果交付和首个可见帧。Glide 或 Coil 的名称不能代替这些配置；缓存键、目标像素、并发、取消和显示生命周期必须一起验证。

Bitmap 侧则要区分压缩字节、CPU 可写像素、共享内存、图形缓冲和 RenderNode 引用。最终验收不是“图片库回调成功”，而是在发布构建中用相同资源、目标尺寸和缓存状态，同时证明解码、内存峰值、RenderThread/GPU 资源准备与 actual present 都在预算内。

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

- [`ImageDecoder.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/ImageDecoder.java)：同步调用、默认监听器、动画、trace 与参数校验。
- [`ImageDecoder.cpp`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/ImageDecoder.cpp)：Source 适配、像素解码、ashmem、PostProcessor 与 Hardware Bitmap 创建。
- [`BitmapFactory.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BitmapFactory.java) 与 [`BitmapFactory.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/BitmapFactory.cpp)：采样、复用、缩放和硬件上传。
- [`Bitmap.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java)：NativeAllocationRegistry、ashmem、HardwareBuffer 与 CPU 访问限制。
- [`Gainmap.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Gainmap.java)：增益图内容 Bitmap、显示参数与引用关系。
- [`BitmapRegionDecoder.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)：Android 17 区域解码支持格式。
- [`RenderNode.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)：DisplayList 生命周期与近似内存统计口径。
- [`FrameMetrics.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：窗口帧公开时长字段。
- [ImageDecoder API](https://developer.android.com/reference/android/graphics/ImageDecoder) 与 [API 36 → 37 diff](https://developer.android.com/sdk/api_diff/37/changes/android.graphics.ImageDecoder)：公开契约和 Android 17 新增监听器。
- [BitmapFactory.Options API](https://developer.android.com/reference/android/graphics/BitmapFactory.Options)：`inBitmap` 与 `inSampleSize` 约束。
- [Managing Bitmap Memory](https://developer.android.com/topic/performance/graphics/manage-memory)：像素存储位置的版本历史。
- [BitmapRegionDecoder API](https://developer.android.com/reference/android/graphics/BitmapRegionDecoder)：当前区域解码格式与入口。
- [Glide BitmapPool 配置](https://bumptech.github.io/glide/doc/configuration.html)、[Coil image pipeline](https://coil-kt.github.io/coil/image_pipeline/)、[Picasso 官方站点](https://square.github.io/picasso/)：图片库能力边界。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线及 dma-buf/dma-fence 语义来源。
