---
title: "第 2 章：渲染系统"
chapter: "2.0"
section: "2.0"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1; kernel android17-6.18-2026-06_r6; consolidated ch02 structure 2.1-2.34"
confidence: high
tags: [rendering, SurfaceFlinger, BufferQueue, BLAST, sync-fence, FrameTimeline, ARR]
pipeline_stage: ready-to-publish
last_consolidated_at: "2026-08-11"
consolidation_note: "完整审阅原 42 篇正文后收敛为 34 篇：合并 GPU 工具链、桌面模式、FrameTimeline、BufferQueue/GraphicBuffer、DMA-BUF/16KB 与 Choreographer stuffing 重复稿，并统一为 2.1-2.34 连续编号。"
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

Android 的掉帧、首帧延迟、SurfaceView 错位、视频抖动和刷新率切换，可能发生在不同责任区间。应用主线程、HWUI RenderThread、GPU、BufferQueue、SurfaceFlinger、Composer HAL 与显示后段各有独立的时钟、队列和完成信号。定位时要先确定内容走哪条出图路径，再判断延迟发生在哪个时间边界。

本章统一锚定 Android 17 / API 37 / `android-17.0.0_r1`；内核公共语义锚定 `android17-6.18-2026-06_r6`。GPU、HWC、overlay、带宽、面板和驱动策略包含厂商实现，AOSP 只能证明公共接口与 framework 行为。

## 公共主线

标准硬件加速 App Window 的公共主线是：

`VSync 调度 → Choreographer → ViewRootImpl/HWUI → RenderThread/GPU → BLAST → SurfaceFlinger → HWC → Display`

这条主线提供观察坐标，不代表所有内容都由 HWUI 生产。SurfaceView、TextureView、Camera、视频、Flutter、OpenGL ES、Vulkan 与游戏引擎会改变 Producer、Surface 数量、layer 拓扑或合成位置。遇到这些类型，应配合[第 18 章：渲染链路全景](../../part2-performance/ch18-rendering-pipelines/README.md)分型。

分析一帧时要分开四组时间点：

1. App VSync 到 `Choreographer#doFrame()`：应用何时获得回调并开始工作；
2. `syncAndDrawFrame()`、GPU submit 与 `queueBuffer()`：Producer 何时提交内容；
3. SurfaceFlinger transaction、snapshot 与 latch：系统何时采纳新 buffer；
4. HWC validate/present 与 present fence：display present 何时越过 Android 可观察边界。

`queueBuffer()` 返回不等于上屏，present fence 也不包含 panel 扫描和像素响应时间。

## 内容索引

### 帧生产与系统合成（2.1—2.6）

- [2.1 Android 渲染架构全景](01-rendering-overview.md)
- [2.2 帧率与刷新率](02-framerate.md)
- [2.3 VSync 机制](03-vsync.md)
- [2.4 Choreographer 与渲染流水线](04-choreographer.md)
- [2.5 MainThread 与 RenderThread 协作](05-main-render-thread.md)
- [2.6 SurfaceFlinger 与合成](06-surfaceflinger.md)

这六篇建立标准 App Window 的时间和责任边界。初次阅读按编号顺序；排障时从异常帧反向追到最早偏离点。

### 绘制、GPU 与图形接口（2.7—2.11）

- [2.7 Hardware Layer](07-hardware-layer.md)
- [2.8 过度绘制](08-overdraw.md)
- [2.9 渲染机制的版本演进](09-rendering-evolution.md)
- [2.10 GPU 渲染、调试与性能分析](10-gpu-rendering.md)
- [2.11 Flutter 渲染管线与性能](11-flutter-rendering.md)

GPU 结论应同时检查 CPU submission、GPU stage、producer fence、composition type、频率/计数器与热状态。空 GPU 轨道只说明证据缺失，不能证明 GPU 空闲。

### Window、Buffer 与同步（2.12—2.16）

- [2.12 Window Manager Service 与窗口管理](12-window-manager.md)
- [2.13 图形缓冲区管理（BufferQueue）](13-buffer-queue.md)
- [2.14 图形 API 演进与选择策略](14-graphics-api-evolution.md)
- [2.15 DMA-BUF、Gralloc 与跨进程图形内存共享](15-dmabuf-gralloc.md)
- [2.16 Sync Fence 框架与帧同步机制](16-sync-fence.md)

slot 状态、GraphicBuffer 引用、dma-buf backing storage 与 fence 是四类对象。“三缓冲”“内存池”“零拷贝”都必须落到具体 Producer/Consumer、对象身份和完成方向。

### 帧节奏与显示策略（2.17—2.23）

- [2.17 Frame Pacing Library 与帧节奏控制](17-frame-pacing.md)
- [2.18 Adaptive Refresh Rate 与动态帧率控制](18-adaptive-refresh-rate.md)
- [2.19 刷新率切换与帧率适配性能](19-refresh-rate-switching.md)
- [2.20 多窗口与桌面模式渲染性能](20-multiwindow-desktop-rendering.md)
- [2.21 文字渲染性能](21-text-rendering-performance.md)
- [2.22 SurfaceFlinger FrontEnd 与 RequestedLayerState](22-surfaceflinger-frontend-requestedlayerstate.md)
- [2.23 SurfaceFlinger VSync Scheduler 与 DisplayFrameRate 策略](23-vsync-scheduler-displayframerate.md)

刷新率提高不会修复 Producer 迟到、GPU 超时、buffer backpressure 或错误的媒体 PTS。内容帧率、render rate、VSync rate、peak refresh rate 与实际 present cadence 要分别记录。

### 窗口形态与显示管线（2.24—2.30）

- [2.24 Edge-to-Edge 渲染与 WindowInsets 处理性能](24-edge-to-edge-inset-rendering-performance.md)
- [2.25 SurfaceFlinger Transaction Queue：无锁入口、分桶与就绪过滤](25-sf-transaction-queue-lockless.md)
- [2.26 折叠屏显示切换、窗口连续性与渲染性能](26-foldable-display-pipeline-performance.md)
- [2.27 TaskSnapshot 捕获、Overview 缩略图与启动窗口](27-tasksnapshot-recents-rendering.md)
- [2.28 DisplayManagerService：Display 发现、拓扑、功耗与渲染交接](28-displaymanager-service-lifecycle.md)
- [2.29 HDR 显示管线与色彩管理性能](29-hdr-color-management-pipeline-performance.md)
- [2.30 Android 17 FrameTimeline、FrameTracer 与合成边界](30-android17-frametimeline-composition-boundary.md)

WMS 管理窗口和 Task，SurfaceControl transaction 管理 layer 状态，BLAST 提交窗口内容，DMS 管理 Display 拓扑与策略。FrameTimeline 用于分类，FrameTracer 用于追 buffer；两者的 token/frame number 不能直接互换。

### Compose、Camera 与模式选择（2.31—2.34）

- [2.31 Compose Pausable Composition 实战指南](31-compose-pausable-composition-guide.md)
- [2.32 Camera HAL3 Buffer 管理与 BufferQueue 协作](32-camera-hal3-buffer-management.md)
- [2.33 CameraX ZSL 与 HAL Reprocessing Request](33-camerax-zsl-hal-mapping.md)
- [2.34 Android 17 Display Mode 选择与 RefreshRateSelector 评分机制](34-display-mode-refresh-rate-selection.md)

Compose 版本、Android platform、CameraX 版本和 vendor Camera HAL 是独立版本轴。显示模式请求也是投票输入，不是应用对 HWC 的直接切换命令。

## 与第 18 章怎样配合

| 当前场景 | 第 2 章基础 | 第 18 章分型 |
|---|---|---|
| 普通 View / Compose | [2.1](01-rendering-overview.md) → [2.4](04-choreographer.md) → [2.5](05-main-render-thread.md) | [标准 View](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)、[Compose](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md) |
| SurfaceView / TextureView | [2.13](13-buffer-queue.md) → [2.16](16-sync-fence.md) → [2.6](06-surfaceflinger.md) | [SurfaceView](../../part2-performance/ch18-rendering-pipelines/06-surfaceview.md)、[TextureView](../../part2-performance/ch18-rendering-pipelines/07-textureview.md) |
| Flutter | [2.11](11-flutter-rendering.md) → [2.13](13-buffer-queue.md) | [Flutter](../../part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md) |
| Camera / 视频 | [2.13](13-buffer-queue.md) → [2.16](16-sync-fence.md) → [2.32](32-camera-hal3-buffer-management.md) | [Camera](../../part2-performance/ch18-rendering-pipelines/14-camera-pipeline.md)、[Video/HWC](../../part2-performance/ch18-rendering-pipelines/15-video-overlay-hwc.md) |
| OpenGL ES / Vulkan / 游戏 | [2.10](10-gpu-rendering.md) → [2.14](14-graphics-api-evolution.md) → [2.17](17-frame-pacing.md) | [OpenGL ES](../../part2-performance/ch18-rendering-pipelines/08-opengl-es.md)、[Vulkan](../../part2-performance/ch18-rendering-pipelines/09-vulkan-native.md)、[游戏](../../part2-performance/ch18-rendering-pipelines/16-game-engine.md) |
| 多窗口 / 折叠屏 / 桌面 | [2.12](12-window-manager.md) → [2.20](20-multiwindow-desktop-rendering.md) → [2.28](28-displaymanager-service-lifecycle.md) | [多窗口、PiP 与 Freeform](../../part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md) |

若路径尚未确定，先从[渲染管线分类、选型与分析方法](../../part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md)建立 Producer、Surface、layer 与合成位置映射。

## 按现象选择阅读顺序

- 主线程掉帧：`2.1 → 2.4 → 2.5 → 2.30`。
- `dequeueBuffer` 或 release 等待：`2.13 → 2.15 → 2.16 → 2.6`。
- GPU 时间偏高：`2.10 → 2.8 → 2.14 → 2.30`。
- `DEVICE` / `CLIENT` composition 切换：`2.6 → 2.22 → 2.29 → 2.30`。
- 60/90/120 Hz 或视频 cadence 异常：`2.2 → 2.17 → 2.18 → 2.19 → 2.23 → 2.34`。
- resize、折叠或桌面窗口错帧：`2.12 → 2.20 → 2.24 → 2.26 → 2.28`。
- Camera 预览或 ZSL 回压：`2.13 → 2.16 → 2.32 → 2.33`。

阅读任何一条路径时，都应记录平台/框架版本、Display、Window、Surface、layer、Producer、三类 fence 与 present 时间。缺少这些对象时，“应用慢”“GPU 慢”或“系统合成慢”都只是待验证假设。
