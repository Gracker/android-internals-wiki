---
title: "Hardware Bitmap 与 RenderNode 缓存策略"
chapter: "22.17"
status: ready-for-review
drafted_date: "2026-05-26"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-26"
last_verified_against: "AOSP master; Android Developers Bitmap/RenderNode/HardwareRenderer/Profile GPU Rendering/Compose image optimization"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BaseCanvas.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/hwui/Bitmap.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/HardwareBitmapUploader.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/Bitmap"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RenderNode"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/HardwareRenderer"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/images/optimization"
  - type: official
    path: "https://developer.android.com/topic/performance/rendering/profile-gpu"
  - type: research
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-hardware-bitmap-rendernode-surfaceflinger-composition.md"
  - type: clipping-structure
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: clipping-structure
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [rendering, bitmap, rendernode, hwui, surfaceflinger]
related_chapters: ["2.5", "2.13", "2.15", "22.6", "22.35", "23.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "素材驱动/AOSP结构/官方文档"
---

# 22.17 Hardware Bitmap 与 RenderNode 缓存策略

Hardware Bitmap 适合解码完成后主要交给硬件加速 Canvas 显示的图片，例如首屏头图、信息流封面和静态贴图。它的像素存放在 graphics memory，并保持不可变；代价是不能直接执行 CPU 像素读写，也不能画进软件 Canvas。[`Bitmap.Config.HARDWARE` API](https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE)

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，kernel 图形内存与 fence 观察固定为 `android17-6.18-2026-06_r6`。Hardware Bitmap 从 API 26 引入，版本沿革只用于解释兼容行为。图片加载、Bitmap 内存与公共显示管线分别见 [22.6 图片加载](06-image-loading.md)、[23.2 Bitmap 内存优化](../ch23-memory-practice/02-bitmap-optimization.md) 和 [18.2 Android View 标准管线](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)。

使用 Hardware Bitmap 的工程目标需要写准：

- 把软件像素转换为 GPU 可采样资源的主要工作前移到解码/分配阶段；
- 避免 HWUI 对软件 Bitmap 执行显式 `prepareToDraw` 纹理准备分支；
- 让只读图片直接作为 Skia 图像资源进入硬件渲染；
- 以不可变、不可直接 CPU 访问和 graphics allocation 换取上述路径。

它不等于“图片不占 RAM”或“首帧没有 GPU 工作”。Android 设备常使用 CPU/GPU 共享物理内存，graphics memory 仍会增加进程与系统压力。Android 8.0 起，普通软件 Bitmap 的像素也位于 native heap，因此 Hardware Bitmap 的收益不能概括为“把像素移出 Java heap”。[Android Bitmap memory evolution](https://developer.android.com/topic/performance/graphics/manage-memory)

Android 17 的 [`Bitmap.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java) 给出以下限制：

- Hardware Bitmap 始终不可变，`createBitmap(width, height, Config.HARDWARE)` 会因该 API 要创建 mutable 结果而抛出异常；
- `getPixel()`、`getPixels()`、`copyPixelsToBuffer()` 与 `copyPixelsFromBuffer()` 拒绝 Hardware Bitmap；
- 某些以 Hardware Bitmap 为源的复制、裁剪、几何变换或 Parcel 操作可能触发慢速 readback/copy，不能视作零成本；
- `wrapHardwareBuffer()` 要求 `USAGE_GPU_SAMPLED_IMAGE`，并拒绝 protected buffer；Bitmap 会持有底层 buffer 引用。

圆角、颜色滤镜或模糊不能一律归为“不支持”。由硬件 Canvas、shader、`RenderEffect` 或 Compose 绘制阶段完成的效果可以继续采样 Hardware Bitmap；需要 CPU 读取或修改像素的 transformation 才应请求软件 Bitmap。

## 从解码结果到 RenderNode

Android 17 的创建路径包含一次明确的像素传输：

1. [`Bitmap.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/hwui/Bitmap.cpp) 的 `Bitmap::allocateHardwareBitmap()` 进入 `HardwareBitmapUploader::allocateHardwareBitmap()`。
2. [`HardwareBitmapUploader.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp) 根据 Skia color type 选择 AHardwareBuffer 格式；不受当前后端支持的格式还会先转换成兼容格式。
3. AHardwareBuffer usage 固定包含 `CPU_READ_NEVER`、`CPU_WRITE_NEVER` 与 `GPU_SAMPLED_IMAGE`。
4. GL 后端通过 EGLImage 与 `glTexSubImage2D()` 写入，创建 fence、flush 并等待；Vulkan 后端使用 `TextureFromAHardwareBufferWithData()` 后提交并等待 CPU。
5. `Bitmap::createFrom()` 持有 AHardwareBuffer，并通过 `SkImages::DeferredFromAHardwareBuffer()` 建立 Skia `SkImage`。

这条链路说明成本发生了位置变化。源像素仍要解码、必要时转换格式，再写进 AHardwareBuffer；创建函数也会等待上传路径完成。GL 源码注释还说明，驱动可能把向硬件缓冲区的底层传输延后到首次绘制。工程结论应写成“主要上传工作前移，HWUI 软件 Bitmap 的显式准备分支被跳过”，不能写成“上传成本消失”。

进入 View 或 Compose 后，Hardware Bitmap 仍由宿主 RenderNode/display list 引用，并由 RenderThread/HWUI 采样。普通图片 composable 没有因此创建一条特殊的系统显示管线。主线程与 RenderThread 的职责见 [2.5 MainThread 与 RenderThread](../../part1-fundamentals/ch02-rendering/05-main-render-thread.md)。

### RenderNode 保存命令，不等于保存整块栅格结果

[RenderNode](https://developer.android.com/reference/android/graphics/RenderNode) 包含 display list 和作用于 display list 的属性。内容没有变化时，translation、scale、alpha 等属性可更新而无需重新录制绘制命令；图片对象或绘制内容改变后，相关节点仍要重新录制。

[RecordingCanvas](https://developer.android.com/reference/android/graphics/RecordingCanvas) 会保留所绘制的 Paint 与 Bitmap 引用，避免 display list 执行前 backing memory 被释放。这带来一个容易忽略的缓存边界：页面已经从业务缓存移除 Bitmap，不代表仍持有该 display list 的 RenderNode 会立即释放它。自建 RenderNode 不再使用时，可按生命周期调用 `discardDisplayList()`；View 系统内部节点应交给框架管理，业务代码避免长期持有脱离页面的 View/RenderNode。

RenderNode 自身也不等于离屏 texture。只有框架因效果或性能判断创建 compositing layer，或代码显式请求 layer，才会增加中间渲染目标与 graphics memory。`computeApproximateMemoryUsage()` 明确不包含 child RenderNode 和 Bitmap，不能用它估算页面总图片内存。[HardwareRenderer](https://developer.android.com/reference/android/graphics/HardwareRenderer)

## 省掉的是 RenderThread upload

Android 17 的 [`SkiaGpuPipeline::prepareToDraw()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp) 只有在 GPU context 存在且 `!bitmap->isHardware()` 时才执行：

- `Bitmap#prepareToDraw WxH` trace；
- `PinAsTexture()` / `UnpinTexture()`；
- `flushAndSubmit()`。

Hardware Bitmap 不进入这段显式准备路径。`prepareToDraw()` 的语义是提前建立绘制缓存，不保证纹理在调用返回时已经完成所有 GPU/驱动工作。[Compose bitmap optimization](https://developer.android.com/develop/ui/compose/graphics/images/optimization)

Perfetto 取证需要同时覆盖“创建前移成本”和“首次显示成本”：

| 阶段 | 观察点 | 解释边界 |
|---|---|---|
| 获取与解码 | 图片库事件、decoder worker、I/O、目标尺寸 | 压缩数据读取、codec 与缩放，不属于 HWUI upload |
| Hardware Bitmap 分配 | `HardwareBitmapUploader`、upload thread、调用线程等待、graphics allocation | 主要像素传输是否已经计入解码完成前 |
| 软件 Bitmap 预热 | `Bitmap#prepareToDraw WxH`、RenderThread/GPU submit | 只有显式调用相应准备路径时才应期待该 slice |
| 首次展示 | `DrawFrame`、GPU completion、App SurfaceFrame | 检查驱动延后工作、shader、混合和内存回收 |
| 系统显示 | SF DisplayFrame、目标 layer latch/present | 图片资源类型不能证明窗口已按期显示 |

对照实验要固定图片字节、解码尺寸、色彩空间、图片库版本、缓存冷热、页面状态、设备温度和刷新率。比较这些组别更有解释力：

1. 软件 Bitmap 冷解码后直接显示；
2. 软件 Bitmap 冷解码后，在非关键帧前调用 `prepareToDraw()`；
3. Hardware Bitmap 冷解码后显示；
4. 三组各自的内存缓存命中路径。

若 Hardware Bitmap 组的首帧缩短，但解码完成时间变长，说明成本被前移；端到端用户等待是否改善仍要看请求开始到目标帧 present 的总时长。第二次展示没有上传 slice，通常只能证明资源已被缓存。

## 不会变成 SurfaceFlinger 独立 layer

AHardwareBuffer 是可被图形系统使用的缓冲区抽象，不等于 BufferQueue 中一帧待显示的 window buffer。Hardware Bitmap 在这里作为 Skia 可采样图像资源，由 HWUI 画进宿主 App Window；它不会因为 backing 是 AHardwareBuffer 就得到独立 SurfaceFlinger layer。

几类常被混淆的对象有不同拓扑：

| 对象 | producer / consumer 关系 | SurfaceFlinger 可见形态 |
|---|---|---|
| View/Compose 中的 Hardware Bitmap | HWUI 采样图片并产出 App Window buffer | 图片本身不可见，只看到宿主窗口 layer |
| `SurfaceView` | 内容 producer 写入独立 Surface/BufferQueue | 通常有独立 layer，可单独 latch、合成与 present |
| `TextureView` | 外部 producer 写入 SurfaceTexture，宿主 HWUI 再采样 | 外部 queue 存在，但显示结果通常并入 App Window |
| `ImageReader` | 应用或系统组件消费图像 buffer | 它本身是 consumer，不自动生成可见 SF layer |
| `MediaCodec` | codec 向调用方提供的 Surface 输出 | layer 拓扑取决于目标 Surface，例如 SurfaceView 或 SurfaceTexture |

因此，layer 数、HWC composition type 或 BufferQueue producer 发生变化时，应检查 Surface 类型、相机/视频/地图组件与窗口结构。`Bitmap.Config.HARDWARE` 只改变宿主绘制资源。BufferQueue、DMA-BUF 与 Gralloc 见 [2.13 BufferQueue](../../part1-fundamentals/ch02-rendering/13-buffer-queue.md) 和 [2.15 DMA-BUF 与 Gralloc](../../part1-fundamentals/ch02-rendering/15-dmabuf-gralloc.md)；混合输出拓扑见 [18.4 View 混合渲染](../../part2-performance/ch18-rendering-pipelines/04-android-view-mixed.md)。

## 资源代价与低内存边界

Hardware Bitmap 的 allocation 可能出现在 Graphics、GL、memtrack、dmabuf 或设备特定分类中；映射与共享关系还会影响 PSS。`getAllocationByteCount()` 可用作单个 Bitmap backing allocation 的近似值，不能覆盖 decoder 临时内存、驱动缓存、RenderNode 引用和页面其他图形资源。

资源评估至少记录：

| 口径 | 用途 | 局限 |
|---|---|---|
| 图片解码尺寸、config、`allocationByteCount` | 解释单张图的像素规模 | 不含全部驱动与中间资源 |
| `dumpsys meminfo` Native / Graphics / GL / total PSS | 比较页面前后和多轮回落 | 分类受驱动、memtrack 和共享归属影响 |
| dmabuf / GPU memory 工具 | 检查图形缓冲区与设备侧压力 | 量产设备权限和驱动支持不同 |
| `/proc/<pid>/fd` 或应用自有资源计数 | 发现句柄/FD 持续增长 | AHardwareBuffer 与 FD 没有跨设备固定的一对一关系 |
| 图片库 memory cache 与 active resource | 解释对象为何仍被持有 | 还要检查 View、Drawable 与 display list 引用 |

AHardwareBuffer 句柄底层可能携带文件描述符，数量和共享方式由 gralloc/驱动实现决定。不能按“每张 Hardware Bitmap 固定占一个 FD”估算；FD 与 Graphics 同时持续上涨时，才需要沿图片缓存、HardwareBuffer owner 和页面生命周期继续追踪。

缓存容量应按解码像素、设备内存档位、graphics 峰值、可见页面数量和回落时间共同设定。收到 `onTrimMemory()` 后是否缩减缓存，要遵守图片库的生命周期接口；业务代码不要手动 recycle 仍由图片库或 display list 持有的 Bitmap。

低 RAM 设备也不应一律关闭 Hardware Bitmap。控制变量测试如果显示软件 Bitmap 的 native heap、首次纹理准备和 GC/回收成本更高，关闭后可能更差。稳妥策略是限制大图并发、按显示尺寸解码、降低预取距离，并为需要 CPU 像素的请求单独选择软件 allocation。

## 应用层实践清单

图片请求应按最终用途选择 allocation：

| 用途 | 建议 |
|---|---|
| 只在硬件加速 ImageView / Compose 中显示 | 允许图片库或 `ImageDecoder.ALLOCATOR_DEFAULT` 选择 Hardware Bitmap；默认 allocator 对小图或不兼容选项仍可能返回软件结果 |
| 需要 `getPixel()`、Palette、二维码识别、CPU 滤镜或编辑 | 请求软件 Bitmap，避免显示后再 readback |
| 需要画入软件 Canvas、生成离屏分享图 | 请求软件 Bitmap |
| 圆角、裁剪、颜色滤镜由硬件绘制完成 | 可保留 Hardware Bitmap，验证是否产生额外 layer 或昂贵 GPU pass |
| 需要 `inBitmap` 复用 | 使用 mutable 软件 Bitmap；Hardware Bitmap 不能进入该复用模型 |
| 自定义跨进程或 HardwareBuffer 协议 | 明确 usage、同步、所有权与 color space，不能只传一个 Bitmap 引用 |

`ImageDecoder.ALLOCATOR_DEFAULT` 通常返回 Hardware Bitmap，小图或与硬件 allocation 不兼容的设置可能返回软件 Bitmap；`ALLOCATOR_HARDWARE` 与 mutable 或 alpha-mask 等不兼容设置组合时会失败。[ImageDecoder allocator](https://developer.android.com/reference/android/graphics/ImageDecoder)

Glide 与 Coil 的默认 hardware 策略会随版本、变换和设备能力变化。页面代码应声明“是否需要 CPU pixels”，让图片库根据单次请求选择；不要在拿到结果后假设 config。完成升级后，用同一图片集复核返回 config、缓存键、transformation、首图耗时与内存峰值。

Compose 自管 `ImageBitmap` 时可以提前调用 `prepareToDraw()`；多数图片库已经包含相应优化，重复预热只会增加工作。`remember` 保留对象，`drawWithCache` 缓存绘制期对象，`graphicsLayer` 可能引入离屏层；三者都不会把软件 Bitmap 自动转换成 Hardware Bitmap。

灰度指标建议包含：

- 请求开始到目标帧 present 的 P50/P90/P95；
- decode、HardwareBitmapUploader、`Bitmap#prepareToDraw`、DrawFrame 与 GPU completion；
- Native、Graphics/GL、total PSS、dmabuf/GPU memory 和 FD 趋势；
- 图片缓存命中、淘汰、页面退出回落与多轮基线漂移；
- 软件 Canvas 异常、readback slow call、OOM、低内存终止和视觉差异。

出现回归时按页面用途关闭 Hardware Bitmap，避免回滚与问题无关的图片请求。解码尺寸、缓存和并发策略要保留，因为 allocation 类型不能修复超尺寸图片。

## 小结

Hardware Bitmap 把像素放进 GPU 可采样的图形缓冲区，并在创建阶段完成主要传输。Android 17 的 HWUI 会跳过软件 Bitmap 的 `prepareToDraw` 分支，但驱动仍可能把部分工作延到首次使用。它继续经过 RenderNode、RenderThread、App Window、SurfaceFlinger 和 present，也继续占用物理内存。

评审时检查四件事：请求是否需要 CPU pixels，创建成本是否只是从目标帧前移到用户等待区间，RenderNode/display list 是否延长资源生命周期，Graphics/dmabuf/FD 是否在页面退出后回落。四项都有数据，Hardware Bitmap 才能成为稳定策略。

## Android 17 源码索引

- [`Bitmap.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java) 与 [`BaseCanvas.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BaseCanvas.java)：不可变性、CPU 像素访问、HardwareBuffer usage 与软件 Canvas 限制。
- [`Bitmap.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/hwui/Bitmap.cpp)：Hardware backing、allocation size、`DeferredFromAHardwareBuffer()` 与资源释放。
- [`HardwareBitmapUploader.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/HardwareBitmapUploader.cpp)：格式转换、AHardwareBuffer 分配、GL/Vulkan 上传和同步等待。
- [`SkiaGpuPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp)：软件 Bitmap 的 `prepareToDraw()` 分支。
- [`RenderNode.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java) 与 [`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)：display list、属性与输出 Surface。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp) 与 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：App Window buffer 与 present 证据。
- [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c) 与 [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)：kernel 侧共享缓冲区与同步机制边界。
