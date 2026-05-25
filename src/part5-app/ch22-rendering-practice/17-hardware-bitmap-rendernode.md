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
related_chapters: ["2.5", "2.13", "2.15", "7.10", "22.6", "23.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "素材驱动/AOSP结构/官方文档"
---

# 22.17 Hardware Bitmap 与 RenderNode 缓存策略

<!-- outline-start -->
## 要点

### 🔹 Hardware Bitmap 解决的问题
说明 `Bitmap.Config.HARDWARE` 的适用前提：像素只用于屏幕绘制、无需 CPU 读写、希望减少 Java heap 占用与首帧 GPU texture upload 抖动。区分它与普通 `ARGB_8888` Bitmap、`Bitmap.prepareToDraw()`、图片库预加载策略的边界。

### 🔹 AHardwareBuffer、SkImage 与 HWUI 绘制路径
梳理 Hardware Bitmap 从 `HardwareBitmapUploader` 分配 `AHardwareBuffer`，到 `SkImages::DeferredFromAHardwareBuffer` 暴露给 Skia，再被 RenderNode display list 记录和 RenderThread 执行的路径。标注源码验证点，不照搬调研稿代码。

### 🔹 RenderThread 中被省掉的 upload 成本
解释普通 Bitmap 首次绘制可能在 RenderThread 出现 texture upload，而 Hardware Bitmap 主要省掉这一段同步成本。给出 Perfetto 观察口径：`Upload ... Texture`、`DrawFrame`、`syncFrameState`、RenderThread CPU slice 与帧耗时对照。

### 🔹 不能直接交给 SurfaceFlinger 合成
澄清常见误判：Hardware Bitmap 仍然是应用 Surface 内部的绘制资源，通常不会变成独立 layer 交给 SurfaceFlinger。只有 SurfaceView、TextureView、ImageReader、MediaCodec 等 Surface 生产者路径才会改变 BufferQueue 与合成边界。

### 🔹 内存、FD 与 Low RAM 风险
覆盖 Hardware Bitmap 的资源代价：GPU/graphics memory 占用、AHardwareBuffer/文件描述符压力、不可变和不可 CPU 读写约束、低内存设备上的降级策略，以及图片库中禁用或限制 Hardware Bitmap 的场景。

### 🔹 工程选型与回退策略
形成应用层实践清单：大图首屏、列表预取、圆角/滤镜/截图/共享元素转场、Compose `ImageBitmap.prepareToDraw()`、Glide/Coil 配置、线上灰度指标与回退开关。

## 扩展

### 🔸 与 22.6 图片加载章节的分工
这一节聚焦 Hardware Bitmap 与 RenderNode/HWUI 路径；解码缓存、采样率、磁盘缓存、图片格式选择详见 22.6 节。

### 🔸 与 23.2 Bitmap 内存治理的交叉
补充 graphics memory 与 Java heap 的统计差异，避免把 Hardware Bitmap 的 Java heap 下降误判为总内存下降。

### 🔸 与 2.13/2.15 图形缓冲章节的交叉
只引用 BufferQueue、DMA-BUF、Gralloc 的机制章节，不重复展开底层图形内存原理。

<!-- outline-end -->

Hardware Bitmap 适合处理“解码后只上屏”的图片：大图首屏、信息流封面、详情页头图、静态贴图。它把像素放到图形内存里，`Bitmap` Java 对象只保留引用，首帧绘制时不再把一块 CPU 像素同步上传到 GPU。`ARGB_8888` 普通位图的价值在于可读写、可裁剪、可滤镜、可参与截图和像素分析；Hardware Bitmap 的价值在于减少 Java heap 压力和 RenderThread 首次 texture upload 抖动。[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

这个边界决定了使用前提：图片已经完成尺寸压缩、颜色空间处理和业务侧变换，后续只需要绘制到硬件加速 Canvas。`Bitmap.java` 对 `Config.HARDWARE` 做了多处限制：硬件位图不可变，不能通过 `createBitmap(width, height, Config.HARDWARE)` 创建可变位图，`copyPixelsToBuffer()`、`copyPixelsFromBuffer()`、`getPixel()` 一类 CPU 像素访问会抛异常；`wrapHardwareBuffer()` 还要求底层 `HardwareBuffer` 带 `USAGE_GPU_SAMPLED_IMAGE`。[已验证: AOSP master, frameworks/base/graphics/java/android/graphics/Bitmap.java][已验证: 官方文档, developer.android.com/reference/android/graphics/Bitmap]

## 从解码结果到 RenderNode

HWUI 的创建路径比“把 Bitmap 变快”更具体。`Bitmap::allocateHardwareBitmap()` 会进入 `HardwareBitmapUploader::allocateHardwareBitmap()`；后者按源图格式选择 `AHardwareBuffer` 格式，并设置 `AHARDWAREBUFFER_USAGE_CPU_READ_NEVER | AHARDWAREBUFFER_USAGE_CPU_WRITE_NEVER | AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE`。随后 `Bitmap.cpp` 通过 `SkImages::DeferredFromAHardwareBuffer()` 创建 Skia 侧 `SkImage`，让 HWUI 后续绘制时以 GPU 可采样资源处理这张图。[已验证: AOSP master, frameworks/base/libs/hwui/hwui/Bitmap.cpp][已验证: AOSP master, frameworks/base/libs/hwui/HardwareBitmapUploader.cpp]

进入 View 或 Compose 绘制后，Hardware Bitmap 仍然走 RenderNode。主线程把 `drawBitmap()` 或图片 composable 的绘制命令记录进 display list；下一帧同步时，RenderThread 接收 RenderNode 树并执行 Skia 绘制。RenderNode 官方文档把它定义为硬件加速渲染层级中的 display list 与属性容器，`HardwareRenderer` 文档也说明渲染请求会把 RenderNode 内容同步到 RenderThread，再渲染到目标 `Surface`。[已验证: 官方文档, developer.android.com/reference/android/graphics/RenderNode][已验证: 官方文档, developer.android.com/reference/android/graphics/HardwareRenderer]

这里的缓存有两层，不要混在一起看：RenderNode 缓存的是绘制命令和属性，Hardware Bitmap 缓存的是像素资源所在位置。移动、透明度、缩放这类属性变更可以复用 RenderNode display list；图片内容变了，仍要重新提交新的位图资源。详见 2.5 节的 MainThread/RenderThread 分工。

## 省掉的是 RenderThread upload

普通 Bitmap 首次参与 GPU 绘制时，系统要先把 CPU 侧像素上传成 GPU texture。Android 官方 Profile GPU Rendering 文档把 bitmap 绘制前的 GPU 内存传输列为渲染成本来源；Compose 图片优化文档也建议在自管 `ImageBitmap` 时提前调用 `prepareToDraw()`，让纹理上传过程提前发生。[已验证: 官方文档, developer.android.com/topic/performance/rendering/profile-gpu][已验证: 官方文档, developer.android.com/develop/ui/compose/graphics/images/optimization]

AOSP 里的分支更直接：`SkiaGpuPipeline::prepareToDraw()` 只在 `context && !bitmap->isHardware()` 时执行 `Bitmap#prepareToDraw` trace、`PinAsTexture()`、`UnpinTexture()` 和 `flushAndSubmit()`。Hardware Bitmap 不进入这个上传分支。[已验证: AOSP master, frameworks/base/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp]

Perfetto 里可以按三步确认收益：

- **RenderThread slice**：对比同一图片首次展示前后的 `DrawFrame`、`syncFrameState` 与 `Bitmap#prepareToDraw WxH`。普通 Bitmap 更容易在首次展示窗口出现 texture upload 相关 slice。
- **帧耗时**：把 upload slice 放回目标帧的 `FrameTimeline`，确认它是否跨过帧预算。只看单个 upload 时间会漏掉同帧 layout、动画和 GPU 等待。
- **复现方式**：清掉内存缓存和图片库预热后跑首帧，再跑一次缓存命中场景。第二次没有 upload 不代表策略有效，可能只是 texture 已经在 GPU 侧缓存。

`Bitmap.prepareToDraw()` 和 Hardware Bitmap 的关系也要分清。前者是把普通位图的绘制缓存提前准备，适合仍需 CPU 像素访问的图片；后者直接把像素放到硬件资源里，换来不可变和不可 CPU 读写。图片库通常已经做了预绘制或硬件位图配置，业务层不要在同一张图上重复设计多套预热逻辑。

## 不会变成 SurfaceFlinger 独立 layer

Hardware Bitmap 只是应用窗口内部的一张绘制资源。它不会因为背后是 `AHardwareBuffer`，就跳过应用 RenderThread，变成 SurfaceFlinger 可以单独调度的 layer。应用仍要把 RenderNode 树绘制到自己的窗口 `Surface`；SurfaceFlinger 看到的是这个窗口产出的 buffer，而不是其中每一张图片。BufferQueue、DMA-BUF、Gralloc 的跨进程边界详见 2.13 和 2.15 节。

改变合成边界的是 Surface 生产者模型。`SurfaceView`、`TextureView`、`ImageReader`、`MediaCodec` 这类路径会引入独立或半独立的 buffer 提交流程，SurfaceFlinger/HWC 才有机会按 layer 维度处理。普通 View 或 Compose 里的 `Image` 使用 Hardware Bitmap，仍属于应用窗口内部绘制。

这也是排查中的常见分叉：如果 trace 里只看到应用 RenderThread 的 upload 消失，但 SurfaceFlinger layer 数没有变化，这是符合预期的；如果 layer 数、BufferQueue producer 或 HWC composition 类型变化，原因通常在 View 类型、视频/相机/外部 Surface 路径，不在 `Bitmap.Config.HARDWARE` 本身。[来源: OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-hardware-bitmap-rendernode-surfaceflinger-composition.md]

## 资源代价与低内存边界

Hardware Bitmap 会降低 Java heap 可见占用，但总内存没有消失，只是移动到 graphics memory / native graphics allocation 一侧。低内存设备上，如果只盯 Java heap，容易得出“图片内存下降”的错判；要同时看 PSS、graphics、dmabuf、GPU memory、FD 数量和图片库缓存命中率。Bitmap 内存计算、采样率和泄漏治理详见 23.2 节。[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

`AHardwareBuffer` 还会带来句柄和文件描述符压力。稳定性章节里的 FD 治理已经说明，FD 泄漏会表现为打开文件、socket、Binder 或图形资源失败；Hardware Bitmap 大量缓存时要把 FD 数量纳入线上指标。列表页尤其容易踩到这个边界：图片看起来没有占 Java heap，滑动过程中却在 graphics memory 和 FD 上堆积。

工程上可以用分级策略控制风险：

- **启用场景**：首屏大图、详情页静态图、图片只进入硬件加速绘制路径，且后续不需要取像素、裁剪、滤镜、马赛克、二维码识别或截图导出。
- **禁用场景**：低 RAM 设备、需要软件 Canvas、圆角/模糊/调色在 CPU 侧执行、共享元素转场依赖截图、业务会调用像素读写 API。
- **缓存策略**：硬件位图缓存按像素总量和张数双阈值控制，收到 `TRIM_MEMORY_UI_HIDDEN`、`TRIM_MEMORY_RUNNING_LOW` 时主动收缩。冷热端缓存分层可参考《Android 性能优化》的缓存命中率章节，但落到图片时要把 graphics memory 一并计入容量。[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

## 应用层实践清单

图片库配置要按业务动作拆。Glide/Coil 打开 Hardware Bitmap 后，默认路径可能更适合静态展示；一旦同一张图要进 `Canvas` 软件绘制、Palette 取色、截图分享、圆角 CPU transformation 或编辑器，就要按 request 关闭硬件位图。不要把开关设成全局常量后长期不看指标。

Compose 场景也按同一原则处理：自管 `ImageBitmap` 时可用 `prepareToDraw()` 提前准备 GPU 纹理；如果图片来自加载库，先确认库是否已经处理预热和硬件位图策略。Compose 的 `drawWithCache`、`graphicsLayer`、`remember` 解决的是绘制对象和层属性复用，不等同于把普通 Bitmap 自动变成 Hardware Bitmap。

上线时保留四组指标：首帧/首屏 P90、RenderThread upload slice 数量和耗时、graphics memory / FD 水位、低内存与崩溃回退率。灰度开关至少按机型内存档位、Android 版本、页面类型拆分；出现低内存、FD 抖动或软件 Canvas 异常时，可以只关闭高风险页面，不必回滚整套图片加载策略。

## 小结

Hardware Bitmap 的收益来自像素资源位置变化：省掉普通 Bitmap 首次绘制时常见的 RenderThread texture upload，同时减少 Java heap 可见压力。它没有绕过 RenderNode、RenderThread 或 SurfaceFlinger，也不能替代图片采样、缓存容量控制和低内存治理。用它时看三件事：这张图是否只上屏，trace 里 upload 是否影响目标帧，graphics memory 与 FD 是否还能压得住。
