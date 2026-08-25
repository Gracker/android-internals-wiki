---
title: "第 2 章：渲染系统"
chapter: "2.0"
section: "2.0"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1; kernel android17-6.18-2026-06_r6; consolidated ch02 structure 2.1-2.18"
confidence: high
tags: [rendering, SurfaceFlinger, BufferQueue, BLAST, sync-fence, FrameTimeline, ARR]
pipeline_stage: ready-to-publish
last_consolidated_at: '2026-08-24'
consolidation_note: 第三轮逐篇审阅后确认当前 18 篇，合并同一责任链中的总览、机制、版本增量、观测与案例；Compose Pausable Composition 留待第 22 章审阅时与应用实践专题统一取舍。
consolidated_from:
  - "src/part1-fundamentals/ch02-rendering/2.15-android17-gpu-debug-tools.md"
  - "src/part1-fundamentals/ch02-rendering/2.29-Android-17-桌面模式窗口管理性能.md"
  - "src/part1-fundamentals/ch02-rendering/2.32-android-17-frametimeline-数据结构.md"
  - "src/part1-fundamentals/ch02-rendering/2.51-android17-gpu-debug-performance-tools.md"
  - "src/part1-fundamentals/ch02-rendering/2.52-android17-gpu-debug-performance-tools.md"
  - "src/part1-fundamentals/ch02-rendering/24-graphic-memory-dmabuf-gralloc-16kb-boundary.md"
  - "src/part1-fundamentals/ch02-rendering/25-choreographer-buffer-stuffing-recovery.md"
  - "src/part1-fundamentals/ch02-rendering/32-graphic-buffer-memory-pool.md"
---

# 第 2 章：渲染系统

Android 的掉帧、首帧延迟、SurfaceView 错位、视频抖动和刷新率切换，可能发生在渲染链路的不同阶段。应用主线程、HWUI RenderThread、GPU、BufferQueue、SurfaceFlinger、Composer HAL、显示控制器与面板各有独立的时钟、队列和完成信号。定位时要先确定内容经过哪条帧生产与合成路径，再判断延迟发生在哪个时间边界。

本章以 Android 17 / API 37 / `android-17.0.0_r1` 为平台基准，以 `android17-6.18-2026-06_r6` 为内核公共语义基准。GPU、HWC、overlay、带宽、面板和驱动策略包含厂商实现，AOSP（Android Open Source Project）只能证明公共接口与 framework 层行为。

先约定几类贯穿全章的对象：HWUI 是 View 体系的硬件加速渲染器，RenderThread 负责组织并提交部分绘制工作；Producer（生产者）取得 GraphicBuffer、写入内容，再通过 BufferQueue 入队，Consumer（消费者）从队列取得缓冲区。SurfaceFlinger 以 layer（合成图层）为单位组织屏幕内容，HWC（Hardware Composer）通过 Composer HAL 选择硬件或 GPU 合成，overlay 指交给显示硬件直接合成的平面。BLAST 用于协调 buffer 与 SurfaceControl transaction 的提交；fence 是表示读写何时完成的同步信号。

## 公共主线

标准硬件加速 App Window 的公共主线是：

`VSync 调度 → Choreographer → ViewRootImpl/HWUI → RenderThread/GPU → BLAST → SurfaceFlinger → HWC → Display`

这条主线提供分析基准，不代表所有内容都由 HWUI 生产。SurfaceView、TextureView、Camera、视频、Flutter、OpenGL ES、Vulkan 与游戏引擎会改变 Producer、Surface 数量、layer 拓扑或合成位置。遇到这些类型，应配合 [第 18 章：渲染链路全景](../../part2-performance/ch18-rendering-pipelines/README.md)按实际路径分类。

分析一帧时要分开四组时间点：

1. App VSync 到 `Choreographer#doFrame()`：应用何时获得垂直同步回调并开始工作；
2. `syncAndDrawFrame()`、GPU submit（提交命令）与 `queueBuffer()`：Producer 何时提交内容；
3. SurfaceFlinger transaction、snapshot 与 latch：系统何时更新 layer 状态、形成待合成快照并取得可用 buffer；
4. HWC validate/present 与 present fence：HWC 何时确认合成方案并提交显示，以及 Android 何时收到显示完成信号。

`queueBuffer()` 返回只说明 buffer 已进入队列，不代表画面已经上屏；present fence 也不包含面板逐行扫描和像素响应时间。

## 内容索引

- [2.1 Android 渲染架构与版本演进](01-rendering-architecture-evolution.md)
- [2.2 帧率、刷新率与显示模式选择](02-framerate-refresh-display-mode.md)
- [2.3 VSync、Choreographer 与 SurfaceFlinger 调度](03-vsync-choreographer-sf-scheduling.md)
- [2.4 MainThread、RenderThread 与 Hardware Layer](04-main-render-thread-hardware-layer.md)
- [2.5 SurfaceFlinger 合成、FrontEnd 与事务队列](05-surfaceflinger-frontend-transaction.md)
- [2.6 过度绘制](06-overdraw.md)
- [2.7 GPU 渲染与图形 API 选型](07-gpu-rendering-graphics-api.md)
- [2.8 BufferQueue、Gralloc 与 Sync Fence](08-bufferqueue-gralloc-sync-fence.md)
- [2.9 Frame Pacing Library 与帧节奏控制](09-frame-pacing.md)
- [2.10 多窗口与桌面模式渲染性能](10-multiwindow-desktop-rendering.md)
- [2.11 文字渲染性能](11-text-rendering-performance.md)
- [2.12 Android 17 Edge-to-Edge 渲染与 WindowInsets 处理性能](12-edge-to-edge-inset-rendering-performance.md)
- [2.13 折叠屏显示切换、窗口连续性与渲染性能](13-foldable-display-pipeline-performance.md)
- [2.14 TaskSnapshot 捕获、Overview 缩略图与启动窗口](14-tasksnapshot-recents-rendering.md)
- [2.15 DisplayManagerService：显示器发现、拓扑、功耗与渲染交接](15-displaymanager-service-lifecycle.md)
- [2.16 HDR 显示管线与色彩管理性能](16-hdr-color-management-pipeline-performance.md)
- [2.17 Android 17 FrameTimeline、FrameTracer 与合成边界](17-android17-frametimeline-composition-boundary.md)
- [2.18 Compose Pausable Composition 实战指南](18-compose-pausable-composition-guide.md)

## 与第 18 章怎样配合

| 当前场景 | 第 2 章基础 | 第 18 章路径分析 |
|---|---|---|
| 普通 View / Compose | [2.1 Android 渲染架构与版本演进](01-rendering-architecture-evolution.md) → [2.3](03-vsync-choreographer-sf-scheduling.md) → [2.4](04-main-render-thread-hardware-layer.md) | [标准 View](../../part2-performance/ch18-rendering-pipelines/01-android-view-pipeline-analysis.md)、[Compose](../../part2-performance/ch18-rendering-pipelines/08-compose-rendering-pipeline.md) |
| SurfaceView / TextureView | [2.8](08-bufferqueue-gralloc-sync-fence.md) → [2.5](05-surfaceflinger-frontend-transaction.md) | [SurfaceView](../../part2-performance/ch18-rendering-pipelines/03-surfaceview-textureview-pipelines.md)、[TextureView](../../part2-performance/ch18-rendering-pipelines/03-surfaceview-textureview-pipelines.md) |
| Flutter | [2.8](08-bufferqueue-gralloc-sync-fence.md) → [2.5](05-surfaceflinger-frontend-transaction.md) | [Flutter](../../part2-performance/ch18-rendering-pipelines/07-flutter-rendering-pipeline.md) |
| Camera / 视频 | [2.8](08-bufferqueue-gralloc-sync-fence.md) → [2.5](05-surfaceflinger-frontend-transaction.md) | [Camera](../../part2-performance/ch18-rendering-pipelines/10-camera-pipeline.md)、[Video/HWC](../../part2-performance/ch18-rendering-pipelines/11-video-overlay-media3-codec-pipeline.md) |
| OpenGL ES / Vulkan / 游戏 | [2.7](07-gpu-rendering-graphics-api.md) → [2.9](09-frame-pacing.md) | [OpenGL ES](../../part2-performance/ch18-rendering-pipelines/04-opengl-egl-angle.md)、[Vulkan](../../part2-performance/ch18-rendering-pipelines/05-vulkan-hwui-multi-queue.md)、[游戏](../../part2-performance/ch18-rendering-pipelines/12-game-engine.md) |
| 多窗口 / 折叠屏 / 桌面 | [1.16](../ch01-architecture/16-display-windowmanager-architecture.md) → [2.15](15-displaymanager-service-lifecycle.md) → [2.10](10-multiwindow-desktop-rendering.md) → [2.13](13-foldable-display-pipeline-performance.md) | 按窗口中的 View、Compose、SurfaceView 或其他 Producer 选择对应 18.x 路径 |

若路径尚未确定，先从 [渲染管线分类、选型与分析方法](../../part2-performance/ch18-rendering-pipelines/01-android-view-pipeline-analysis.md)建立 Producer、Surface、layer 与合成位置的对应关系。

## 按现象选择阅读顺序

- 主线程掉帧：`2.1 → 2.3 → 2.4 → 2.17`。
- `dequeueBuffer()` 长时间取不到可用缓冲区，或 release fence 迟迟未完成：`2.8 → 2.5`。
- GPU 时间偏高：`2.7 → 2.6 → 2.17`。
- `DEVICE` / `CLIENT` composition 切换：`2.5 → 2.16 → 2.17`。
- 60/90/120 Hz 或视频呈现节奏异常：`2.2 → 2.3 → 2.9`。
- resize、折叠或桌面窗口错帧：`1.16 → 2.10 → 2.12 → 2.13 → 2.15`。
- Camera 预览或 ZSL 回压：`2.8 → 18.10`。

阅读任何一条路径时，都应记录平台/框架版本、Display、Window、Surface、layer、Producer，以及 acquire fence（Consumer 何时可以开始读）、release fence（Producer 何时可以再次使用缓冲区）、present fence（本次合成何时越过 Android 可观察的显示边界）和 present 时间。缺少这些对象时，“应用慢”“GPU 慢”或“系统合成慢”都只是待验证假设。
