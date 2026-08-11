---
title: "渲染系统总纲"
chapter: "2.0"
section: "2.0"
status: finalized
drafted_date: "2026-04-23"
drafted_by: "openclaw-task2b"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-23"
last_verified_against: "ch02-rendering 目录结构、AOSP android-16.0.0_r1 渲染流程说明、external review 资产"
confidence: medium
tags: [rendering, SurfaceFlinger, BufferQueue, BLAST, sync-fence, FrameTimeline, ARR]
pipeline_stage: ready-to-publish
last_task2b_at: "2026-05-09T22:40:00+08:00"
task6_state: reviewed
reviewed_date: "2026-05-13"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
task9_result: pass-tech-review
last_task9_at: "2026-05-14T11:34:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-14"
---

# 第 2 章：渲染系统

Android 的掉帧、首帧延迟、SurfaceView 错位、视频抖动和刷新率切换，可能发生在不同责任区间。应用主线程、HWUI RenderThread、GPU、BufferQueue、SurfaceFlinger、Composer HAL 与显示后段各有独立的时钟、队列和完成信号。定位时要先确定当前内容走哪条出图路径，再判断延迟发生在哪个时间边界。

复核锚点如下：

- platform：Android 17 / API 37 / `android-17.0.0_r1`；
- kernel：`android17-6.18-2026-06_r6`；
- Android 12—17 的版本变化用于解释现代 trace，版本首引保留对应 tag 或 API 文档；
- GPU、HWC、overlay、带宽与面板策略包含厂商实现，AOSP 只能证明公共接口和 framework 行为。

## 公共主线

标准硬件加速 App Window 的公共主线可以写成：

`VSync 调度 → Choreographer → ViewRootImpl/HWUI → RenderThread/GPU → BLAST → SurfaceFlinger → HWC → Display`

这条表达式提供观察坐标，不代表所有内容都由 HWUI 生产。SurfaceView、TextureView、Camera、视频、WebView、Flutter、OpenGL ES、Vulkan 与游戏引擎会改变 Producer、Surface 数量、layer 拓扑或合成位置。遇到这些类型，应配合[第 18 章：渲染链路全景](../../part2-performance/ch18-rendering-pipelines/README.md)分型。

分析一帧时，下面四组时间点要分开：

1. `vsync-app` 到应用 `Choreographer#doFrame()`：应用何时获得帧回调，主线程何时开始工作；
2. `syncAndDrawFrame()`、GPU submit 与 `queueBuffer`：HWUI 或其他 Producer 何时提交内容；
3. SurfaceFlinger transaction、snapshot 与 latch：系统何时采纳该 layer 的新 buffer；
4. HWC validate/present 与 present fence：本轮 display present 何时越过系统显示边界。

`queueBuffer` 返回只证明 Producer 已把 buffer 交回队列。GPU 写入可能仍由 acquire fence 约束，SurfaceFlinger 也可能尚未 latch。present fence 更靠近显示出口，但不包含 panel 扫描和像素响应时间。

## 内容索引

### 1. 起帧、应用渲染与系统合成

- [2.1 Android 渲染架构全景](01-rendering-overview.md)：把应用生产、BLAST、SurfaceFlinger、HWC 和 display 放到一条时序线上。
- [2.2 帧率与刷新率](02-framerate.md)：区分内容帧率、VSync 周期、display mode 与 jank 统计口径。
- [2.3 VSync 机制](03-vsync.md)：理解 Android 17 的预测 present time、work duration、ready duration 与 EventThread 分发，避免套用固定 phase offset 模型。
- [2.4 Choreographer 与渲染流水线](04-choreographer.md)：跟读 `INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT`。
- [2.5 MainThread 与 RenderThread 协作](05-main-render-thread.md)：区分 UI 状态准备、RenderNode 同步、GPU 提交和等待。
- [2.6 SurfaceFlinger 与合成](06-surfaceflinger.md)：理解 FrontEnd、CompositionEngine、RenderEngine、HWC 与 present。

这六篇构成标准 App Window 的基线。初次阅读建议按编号顺序完成；排障时可按异常时间点跳到对应对象。

### 2. 绘制成本、GPU 与图形 API

- [2.7 Hardware Layer](07-hardware-layer.md)：分析离屏缓存、纹理占用、更新成本和动画适用边界。
- [2.8 过度绘制](08-overdraw.md)：检查无效像素填充、透明混合和工具统计边界。
- [2.9 渲染机制的版本演进](09-rendering-evolution.md)：按具体对象梳理 View、HWUI、BLAST、FrameTimeline 与现代显示策略。
- [2.10 GPU 渲染深入](10-gpu-rendering.md)：区分 CPU 录制/提交、GPU 执行、内存带宽、频率和热状态。
- [2.14 图形 API 演进与选择](14-graphics-api-evolution.md)：对照 OpenGL ES、Vulkan、ANGLE 与应用选择条件。
- [2.21 文字渲染性能](21-text-rendering-performance.md)：覆盖文本测量、布局、字形缓存、fallback 与 GPU 绘制。
- [2.24 图形内存、DMA-BUF、Gralloc 与 16KB 边界](24-graphic-memory-dmabuf-gralloc-16kb-boundary.md)：区分页面大小、buffer stride、映射和 allocator 约束。
- [2.31 HDR 显示管线与色彩管理](31-hdr-color-management-pipeline-performance.md)：跟踪 dataspace、HDR metadata、headroom、tone mapping 与 HWC/RenderEngine 分工。

GPU 时间变长时，应同时查看 shader/纹理/带宽、DVFS、thermal、buffer 等待和 composition type。单个 GPU 利用率百分比不足以确认瓶颈。

### 3. Buffer、共享内存与同步

- [2.13 BufferQueue](13-buffer-queue.md)：Producer/Consumer、slot、dequeue、queue、acquire、release 与 backpressure。
- [2.15 DMA-BUF 与 Gralloc](15-dmabuf-gralloc.md)：GraphicBuffer 如何跨进程共享，以及 dma-buf 能证明的边界。
- [2.16 Sync Fence](16-sync-fence.md)：区分 acquire fence、release fence 和 present fence 的方向与粒度。
- [2.32 GraphicBuffer 内存池与 slot 复用](32-graphic-buffer-memory-pool.md)：理解 BufferQueue slot、GraphicBuffer 重分配和“复用”的精确含义。

这组章节使用 `android17-6.18-2026-06_r6` 固定 dma-buf、dma-fence 与 sync_file 的公共语义。Android 设备可能使用厂商 GPU/display 驱动；plane 分配、带宽投票和 scanout 仍需设备源码或 trace。

### 4. Window、layer、transaction 与 display

- [2.12 Window Manager Service](12-window-manager.md)：窗口层级、可见性、relayout、动画与 SurfaceControl 的职责边界。
- [2.20 多窗口与桌面模式](20-multiwindow-desktop-rendering.md)：同进程/跨进程窗口、共享资源、几何同步和整屏合成。
- [2.22 SurfaceFlinger FrontEnd](22-surfaceflinger-frontend-requestedlayerstate.md)：跟读 `RequestedLayerState`、`LayerLifecycleManager` 与 `LayerSnapshotBuilder`。
- [2.27 SurfaceFlinger Transaction Queue](27-sf-transaction-queue-lockless.md)：理解无锁入口、按 token 分桶、barrier 与 readiness 过滤。
- [2.29 TaskSnapshot 与 Overview](29-tasksnapshot-recents-rendering.md)：区分 snapshot 捕获、缓存、缩略图和启动窗口。
- [2.30 DisplayManagerService](30-displaymanager-service-lifecycle.md)：DisplayDevice、LogicalDisplay、拓扑、功耗状态和 SurfaceFlinger 交接。

WMS 管理窗口与 Task 状态，SurfaceControl transaction 管理 layer 状态，BLAST 提交窗口内容。三者可能按 frame number 或同步组协作，trace 中仍应分别识别。

### 5. 帧节奏、刷新率与形态变化

- [2.17 Frame Pacing](17-frame-pacing.md)：分析 frame pacing、queue-stuffing、in-flight 深度和游戏提交节拍。
- [2.18 Adaptive Refresh Rate](18-adaptive-refresh-rate.md)：理解 ARR 能力、VSync period 变化与应用接口边界。
- [2.19 刷新率切换](19-refresh-rate-switching.md)：跟踪 frame-rate request、display mode 选择、切换时序和内容 cadence。
- [2.23 VSync Scheduler 与 DisplayFrameRate](23-vsync-scheduler-displayframerate.md)：深入 Android 17 Scheduler 的预测与刷新率决策对象。
- [2.25 Choreographer Buffer Stuffing Recovery](25-choreographer-buffer-stuffing-recovery.md)：解释 stuffing 检测、VSync 修正及其适用范围。
- [2.26 Edge-to-Edge 与 WindowInsets](26-edge-to-edge-inset-rendering-performance.md)：分析 Insets 动画、布局失效与内容边界。
- [2.28 折叠屏显示切换](28-foldable-display-pipeline-performance.md)：覆盖 display 切换、configuration、窗口连续性和渲染恢复。
- [2.29 Android 17 桌面模式窗口管理](2.29-Android-17-桌面模式窗口管理性能.md)：聚焦桌面窗口 resize、transition 与多窗口资源竞争。

刷新率提高不会修复 Producer 迟到、GPU 超时、buffer backpressure 或错误的媒体 PTS。显示节奏与内容生产节奏要在同一条时间线上对齐。

### 6. Compose、Flutter 与 Camera 专题

- [2.11 Flutter 渲染管线与性能](11-flutter-rendering.md)：区分 Flutter root render mode、Raster、external texture、PlatformView 与 Android 宿主路径。
- [2.28 Compose Pausable Composition 深度分析](2.28-Compose-Pausable-Composition-深度分析.md)：核对 pausable composition 的 runtime 状态机与版本边界。
- [2.29 Compose Pausable Composition 实战指南](2.29-compose-pausable-composition-guide.md)：把 API 使用、适用场景与诊断证据对应起来。
- [2.31 Camera HAL3 Buffer 管理](2.31-camera-hal3-buffer-management.md)：从 request/result、stream buffer、fence 和 consumer 回压理解 Camera 管线。
- [2.32 CameraX ZSL 与 HAL reprocessing](2.32-camerax-zsl-hal-mapping.md)：分清 CameraX ring buffer 与 HAL input reprocessing 的映射边界。

Compose 最终仍由 Android 宿主出图；Flutter 的 root render mode 和 PlatformView 策略可能改变 layer 拓扑；Camera 可以输出到 SurfaceView、TextureView、ImageReader 或编码器。框架名字只能提供线索，目标 Surface 与 layer 才能确定当前路径。

### 7. FrameTimeline 与 GPU 诊断工具

- [2.15 Android 17 GPU 图形调试工具链](2.15-android17-gpu-debug-tools.md)：工具选择、权限、数据覆盖范围与设备差异。
- [2.32 Android 17 FrameTimeline 数据结构](2.32-android-17-frametimeline-数据结构.md)：`SurfaceFrame`、`DisplayFrame`、token、expected/actual 与 jank classification。
- [2.51 Android 17 GPU Trace 数据源](2.51-android17-gpu-debug-performance-tools.md)：Perfetto GPU data source、Trace Processor 与证据关联。
- [2.52 Android 17 帧诊断](2.52-android17-gpu-debug-performance-tools.md)：对照 FrameTimeline、FrameTracer、TimeStats 与 JankTracker 的统计边界。

工具输出必须对应到同一帧、同一 Surface 和同一 display。FrameTimeline 的 App actual slice 主要适合标准窗口；SurfaceView、Camera、视频和自研引擎仍要补 layer、BufferQueue、fence、HWC 与 present 证据。

## 与第 18 章怎样配合

第 2 章按系统组件组织，第 18 章按出图类型组织。推荐的使用方式如下：

| 当前场景 | 第 2 章基础 | 第 18 章分型 |
|---|---|---|
| 普通 View / Compose 页面 | [2.1](01-rendering-overview.md) → [2.4](04-choreographer.md) → [2.5](05-main-render-thread.md) | [标准 View](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)、[Compose](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md) |
| SurfaceView / TextureView | [2.13](13-buffer-queue.md) → [2.16](16-sync-fence.md) → [2.6](06-surfaceflinger.md) | [SurfaceView](../../part2-performance/ch18-rendering-pipelines/06-surfaceview.md)、[TextureView](../../part2-performance/ch18-rendering-pipelines/07-textureview.md) |
| WebView / Flutter | [2.5](05-main-render-thread.md) → [2.13](13-buffer-queue.md) | [WebView](../../part2-performance/ch18-rendering-pipelines/13-webview-rendering.md)、[Flutter](../../part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md) |
| Camera / 视频 | [2.13](13-buffer-queue.md) → [2.16](16-sync-fence.md) → [2.19](19-refresh-rate-switching.md) | [Camera](../../part2-performance/ch18-rendering-pipelines/14-camera-pipeline.md)、[Video/HWC](../../part2-performance/ch18-rendering-pipelines/15-video-overlay-hwc.md) |
| OpenGL ES / Vulkan / 游戏 | [2.14](14-graphics-api-evolution.md) → [2.17](17-frame-pacing.md) | [OpenGL ES](../../part2-performance/ch18-rendering-pipelines/08-opengl-es.md)、[Vulkan](../../part2-performance/ch18-rendering-pipelines/09-vulkan-native.md)、[游戏](../../part2-performance/ch18-rendering-pipelines/16-game-engine.md) |
| 多窗口 / 折叠屏 / 桌面模式 | [2.12](12-window-manager.md) → [2.20](20-multiwindow-desktop-rendering.md) → [2.30](30-displaymanager-service-lifecycle.md) | [多窗口、PiP 与 Freeform](../../part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md) |

若路径尚未确定，可从[渲染管线分类、选型与分析方法](../../part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md)建立 Producer、Surface、layer 与合成位置的映射，并复原异常帧。

## 按现象选择阅读顺序

- 主线程掉帧：`2.1 → 2.4 → 2.5 → 2.52`。
- `dequeueBuffer` 或 release 等待：`2.13 → 2.16 → 2.32 GraphicBuffer → 2.6`。
- GPU 时间偏高：`2.10 → 2.8 → 2.14 → 2.51`。
- `DEVICE` 与 `CLIENT` composition 切换：`2.6 → 2.22 → 2.31 HDR → 18.15`。
- 60/90/120 Hz 切换或视频 cadence 异常：`2.2 → 2.17 → 2.18 → 2.19 → 2.23`。
- resize、折叠或桌面窗口错帧：`2.12 → 2.20 → 2.26 → 2.28 折叠屏 → 2.29 桌面模式`。
- Camera 预览或 ZSL 回压：`2.13 → 2.16 → 2.31 Camera HAL3 → 2.32 CameraX`。

阅读任何一条路径时，都应记录平台/框架版本、Display、Window、Surface、layer、Producer、三类 fence 与 present 时间。缺少这些对象时，“应用慢”“GPU 慢”或“系统合成慢”都只是待验证假设。

## 固定源码入口

- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Android 17 HWUI RenderThread](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/)
- [Android 17 `BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [Android 17 SurfaceFlinger FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrontEnd/)
- [Android 17 `SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [Android 17 `HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)
- [kernel `android17-6.18-2026-06_r6` dma-buf](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)
- [kernel `android17-6.18-2026-06_r6` sync_file](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)

这些入口用于核对公共调用关系。任何设备级性能结论仍需结合该设备的 Composer HAL、GPU/display 驱动、刷新率、温度和 Perfetto 轨迹。
