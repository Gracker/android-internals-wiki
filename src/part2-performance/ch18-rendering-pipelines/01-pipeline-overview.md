---
title: "渲染管线分类、选型与分析方法"
chapter: "18.1"
section: "18.1"
status: finalized
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified_against: "AOSP android-17.0.0_r1 Choreographer / ViewRootImpl / HWUI / BLASTBufferQueue / SurfaceFlinger FrontEnd / HWComposer + Perfetto android-17.0.0_r1"
confidence: high
tags: ["rendering-pipeline", "BLAST", "SurfaceFlinger", "HWUI", "SurfaceView", "TextureView", "Vulkan", "OpenGL ES", "HardwareBufferRenderer"]
related_chapters: ["2.5", "2.6", "2.13", "2.16", "13.9", "13.14", "13.19", "14.21", "15.1", "18.2", "18.3", "18.4", "18.5", "18.6", "18.7", "18.8", "18.9", "18.10"]
consolidated_from:
  - "src/part2-performance/ch18-rendering-pipelines/20-pipeline-analysis-methodology.md"
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md"
    role: "App 出图类型公共基线、12 个显示锚点与版本演进"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java"
    role: "帧调度与五类 callback 顺序"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java"
    role: "Traversal、batched input 与 HWUI 交接"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
    role: "BufferItem 到 SurfaceControl transaction 的转换"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.h"
    role: "BufferTX pending-buffer counter 语义"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp"
    role: "transaction readiness 与 latch-unsignaled 条件"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp"
    role: "validate、presentOrValidate、present 与 fence"
  - type: perfetto
    path: "https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/prelude/after_eof/events.sql"
    role: "actual_frame_timeline_slice schema"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java"
    role: "Android 17 producer throttling 的查询、控制与诊断边界"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6"
    role: "dma-buf、dma-fence、sync_file 与 DRM/KMS 的统一 kernel 锚点"
last_verified: "2026-07-31"
task9_state: "reviewed"
task2b_state: "fixed"
task6_state: "reviewed"
pipeline_stage: "ready-to-publish"
---

# 18.1 渲染管线分类、选型与分析方法

## 为什么需要理解渲染管线

Perfetto 里出现一帧超时，定位工作不应从“最长的 trace slice（追踪时间区间）”开始，而应先回答三个问题：

1. 谁在生产本帧 buffer（图像缓冲区）？
2. buffer 写入哪个 `Surface`，是否形成独立 layer（合成图层）？
3. 本帧在哪里合成，又在哪个时间边界完成 present（帧呈现）？

Producer 指生成并提交 buffer 的组件。标准 App Window 通常由 HWUI 的 RenderThread 生产 buffer；HWUI 是 Android 的硬件加速 UI 渲染器。SurfaceView、Camera、Video、WebView、Flutter、游戏和 React Native 则可能把生产工作交给引擎线程、解码器或硬件模块。BufferQueue 在 Producer 与读取 buffer 的 Consumer 之间传递数据，SurfaceFlinger（SF）组织各个 layer，HWC（Hardware Composer，硬件合成器）选择硬件合成路径，FrameTimeline 则记录预期帧与实际帧的时间。不同出图类型的线程、layer 数量、合成位置与 FrameTimeline 覆盖程度并不相同。

`queueBuffer` 表示 Producer 把 buffer 交回队列，`latch` 表示 SurfaceFlinger 在本轮采纳该 buffer，`present fence` 是显示管线完成本轮 present 后给出的同步信号。看到其中一个事件，只能证明显示路径走到了对应位置，不能替代其他阶段的证据。本节先明确公共主线，后续章节再解释各出图类型从哪里分开。

本文以 Android 17 / API 37 的 `android-17.0.0_r1` 为实现基线。涉及 dma-buf（跨设备共享 buffer 的内核机制）、sync_file（把同步 fence 暴露为文件描述符的接口）、DRM/KMS（内核显示与模式设置子系统）或调度器实现时，统一核对 `android17-6.18-2026-06_r6`；Framework 结论不依靠某个单独的 kernel 函数推导。

## 用四个坐标识别出图类型

`SurfaceView`、`TextureView`、WebView、Flutter 和 Compose 是 API 或框架名称。名称本身不足以确定 trace 中的图形路径。同一个 Flutter 页面可能使用 `SurfaceView` 或 `TextureView` 作为宿主，Platform View（嵌入 Flutter 的原生平台视图）还会改变 layer 拓扑；同一个播放器也可能在普通 BufferQueue、SurfaceView 独立 layer 与 tunneled/sideband（绕开普通 buffer 队列的专用媒体路径）之间切换。

每次分析先固定四个坐标：

| 坐标 | 要确认的对象 | Trace 或源码证据 |
|---|---|---|
| Producer | HWUI RenderThread、GL/Vulkan thread、Chromium、Flutter raster thread（光栅化线程）、Camera HAL（相机硬件抽象层）、MediaCodec、游戏引擎或其他模块 | 线程 slice、GPU submission（命令提交）、decoder/camera 事件 |
| 输出目标 | App Window、独立 `Surface`、`SurfaceTexture`、swapchain（轮换使用的一组可显示 buffer）、离屏 `HardwareBuffer` 或 sideband stream | BufferQueue、ANativeWindow（NDK 窗口接口）、SurfaceControl、layer dump |
| layer 拓扑 | 内容进入宿主窗口，还是形成一个或多个独立 child layer | layer parent、relative layer、Z-order（前后叠放顺序）、`BufferTX` |
| 合成与 present | 宿主 HWUI 采样、SurfaceFlinger CLIENT composition（用 GPU 合成）、HWC DEVICE composition（由显示硬件合成）或专用媒体路径 | RenderEngine（SurfaceFlinger 的 GPU 合成引擎）、composition type、HWC、present fence |

线程名只说明某段代码在哪条线程执行。确认渲染类型还要用对象标识把线程、swapchain/BufferQueue、SurfaceControl 和目标 layer 对到同一条路径。看到 `GLThread` 不足以证明页面一定存在独立 layer；看到 `SurfaceView` 对象也不足以证明本帧被 HWC 作为 overlay（独立硬件图层）处理。

## 版本与架构对照表

Android 9 到 Android 17 的图形栈不能只用“Legacy”与“BLAST”二分。对 trace 更有帮助的写法，是标出哪个版本可以使用哪些对象和观测方法。

这里的 BLAST 指协调窗口 buffer 更新与 `SurfaceControl.Transaction` 提交的机制，Legacy 则是对更早 BufferQueue/layer 路径的概括称呼。

| 平台 | 公共显示主线 | Trace 判读要点 |
|---|---|---|
| Android 9 / API 28 | App Window 常见传统 BufferQueue producer/consumer 路径 | 不应期待 BLAST 或 FrameTimeline；以 `Choreographer`、HWUI、`queueBuffer`、SF/HWC slice 为主 |
| Android 10 / API 29 | `SurfaceControl.Transaction` 能力扩展，App Window 仍处于迁移前后混合期 | 不要只凭系统版本断定采用 BLAST，要以进程内对象和 trace 为证 |
| Android 11 / API 30 | BLAST 进入平台主线，窗口 buffer 与 layer transaction 的组织方式开始改变 | 旧资料中的 `BufferStateLayer` 只适合对应旧源码 tag，不能拿来解释 Android 17 的 FrontEnd（layer 状态处理阶段） |
| Android 12 / API 31 | BLAST 与 FrameTimeline 构成现代 trace 基线 | 标准 App Window 可用 SurfaceFrame/DisplayFrame token（跨阶段关联一帧的标识）对齐；独立 Surface 仍需 layer、BufferQueue 与 fence 证据 |
| Android 13 / API 33 | `AutoSingleLayer` 下的 latch-unsignaled 策略成为重要边界 | acquire fence 尚未 signal（发出完成信号）时，transaction 也不再必定无法 latch；硬件读取仍要遵守同步约束 |
| Android 14 / API 34 | 公共 Choreographer→HWUI→BLAST→SF→HWC 骨架延续；SurfaceView 增加 alpha 与 lifecycle 能力 | 标准窗口仍按公共主线读，独立 Surface 的透明度与生命周期要单独核对 |
| Android 15 / API 35 | Window/SurfaceView 源码与 API 面开始提供 desired HDR headroom（SDR 白场以上的 HDR 亮度余量），r1 中仍带 feature flag 边界 | headroom 只是请求；还要核对目标设备的 feature flag（功能开关）、bit depth（色深）、面板与显示策略 |
| Android 16 / API 36 | SurfaceView 源码增加整数 `compositionOrder`，r1 API 签名带 `@FlaggedApi`；公共主线延续 | 多 Surface 页面要记录 parent、relative layer、flag 状态与 Z-order |
| Android 17 / API 37 | 锚定 FrontEnd `RequestedLayerState` / `LayerSnapshot`、预测 present time、现行 BLAST/HWC 路径；SurfaceView blur region 与 `compositionOrder` 仍带 flag 边界 | 源码按 `android-17.0.0_r1` 的对象名解释；旧 `DispSync`、固定 phase offset（相位偏移）和逐个旧 Layer latch 模型不能直接套用 |

这张表描述的是观察边界，不表示每个版本都重做了一套渲染管线。BLAST 改变了 buffer 与窗口状态进入 SurfaceFlinger 的组织方式，但 Producer/Consumer 分工和 acquire/release fence 仍然存在。

## 典型模式对比

先按 Producer、输出目标、layer 拓扑与合成位置区分主干模式：

| 模式 | 主要 Producer | Surface/layer 形态 | 主要合成位置 | 容易误判的点 | 章节 |
|---|---|---|---|---|---|
| 标准 Android View | MainThread 准备状态，HWUI RenderThread/GPU 产出 | 宿主 App Window | SF 选择 DEVICE 或 CLIENT | MainThread `draw()` 结束不等于 buffer 已提交 | [18.2](02-android-view-standard.md) |
| Software / 离屏 | `lockCanvas()` 线程、CPU raster（CPU 光栅化）或离屏 GPU | 可见 Surface 或离屏 buffer | 可见目标进入 SF/HWC；离屏目标由下游消费 | “软件绘制”不等于没有 BufferQueue；离屏完成 fence 也不是 present fence | [18.3](03-android-view-software.md)、[18.17](17-hardware-buffer-renderer.md) |
| 混合渲染 | 宿主 HWUI + 一个或多个独立 Producer | App Window 与 child layer 并存 | SF/HWC 合成多个 layer | 不能用宿主窗口一条 FrameTimeline 代表所有独立 Surface | [18.4](04-android-view-mixed.md) |
| 多窗口 | 每个 Window 各有 ViewRoot/Surface；线程可能同进程共享，也可能跨进程 | 多个 Window layer | 每个 display 分别组织输出 | “多窗口必定同一主线程串行”只适用于部分同进程场景 | [18.5](05-android-view-multi-window.md) |
| SurfaceView | 解码器、Camera、GL/Vulkan 或其他 Producer | 独立 child Surface/layer | 常由 SF/HWC 与宿主拼层 | 独立 layer 有利于 overlay，但不保证低延迟或 DEVICE composition | [18.6](06-surfaceview.md) |
| TextureView | 外部 Producer 写入 `SurfaceTexture` | 内容作为纹理进入宿主 View 树 | 宿主 HWUI 再采样到 App Window | 成本是额外采样/宿主合成，不宜笼统写成固定 CPU 拷贝 | [18.7](07-textureview.md) |
| OpenGL ES | GL thread / engine thread | EGL window surface（EGL 的可显示窗口目标）对应 BufferQueue | SF/HWC | `eglSwapBuffers()` 返回不代表 GPU 写完或已经 present | [18.8](08-opengl-es.md) |
| Vulkan | engine/render thread | `VkSwapchainKHR` 对接 ANativeWindow | SF/HWC | 显式 API 可以降低部分 driver 开销，但 CPU 成本取决于引擎、同步和驱动 | [18.9](09-vulkan-native.md) |
| WebView | Chromium renderer/compositor、Viz（Chromium 的显示合成服务）与宿主进程协作 | Chromium surface 与宿主窗口组合，具体拓扑依实现而定 | Chromium 合成后进入 Android 显示链 | 只看 App MainThread 会漏掉 renderer/GPU 进程 | [18.13](13-webview-rendering.md) |
| Flutter | UI/raster/platform thread 与 Impeller/Skia 渲染后端 | 宿主可用 SurfaceView 或 TextureView；Platform View 再增加分支 | 宿主 layer 与 Platform View 共同进入 SF/HWC | 框架名不能确定宿主 render mode（渲染承载方式） | [18.12](12-flutter-rendering.md) |
| Camera | Camera HAL、ISP（图像信号处理器）与应用/系统消费者 | 预览 Surface、ImageReader、编码器等多消费者 | 预览常通过独立 layer 参与合成 | request/result 完成不等于预览已 present | [18.14](14-camera-pipeline.md) |
| Video / HWC | MediaCodec、解码器、播放器 | SurfaceView buffer queue 或 tunneled/sideband 路径 | HWC overlay、专用媒体路径或 CLIENT fallback | 解码完成、releaseOutputBuffer 与上屏时间不是同一边界 | [18.15](15-video-overlay-hwc.md)、[18.21](21-media-codec2-tunneled-media3-abr.md) |
| 游戏引擎 | game/render thread、GL/Vulkan queue | ANativeWindow swapchain，可能叠加独立 UI/video layer | SF/HWC | 平均 FPS 会掩盖 frame pacing（帧输出节奏）、queue depth（排队帧数）与 present 抖动 | [18.16](16-game-engine.md) |
| Compose | Compose runtime 与 UI thread 生成状态，HWUI RenderThread/GPU 产出 | 默认仍是宿主 App Window | SF/HWC | recomposition（重组）、layout、draw 与 GPU 提交属于不同阶段 | [18.23](23-compose-rendering-pipeline.md) |
| React Native | JS、Fabric（新架构 UI 渲染系统）、HWUI；第三方原生组件可另建 Surface | 标准 View 树或 SurfaceView/TextureView 分支 | 取决于宿主与原生组件拓扑 | JS thread 只是 Producer 路径的一段，不能代表 present | 这里只给分型基线 |

[18.10 SurfaceControl API](10-surface-control-api.md) 与 [18.11 ANGLE](11-angle-gles-vulkan.md) 分别解释 layer 控制和 GLES→Vulkan 翻译。[18.5 多窗口/PiP/Freeform](05-android-view-multi-window.md)、[18.18 VRR](18-variable-refresh-rate.md)、[18.20 XR](20-android-xr-spatial-ui-rendering.md) 继续分析 window/display 分支。本节后半给出所有路径共用的证据收集步骤。

### 快速识别当前管线

一段 trace 可以先做四项检查：

1. 找到目标 Window、Surface 和 layer，确认是一层还是多层。
2. 找到 Producer：MainThread/RenderThread、GL/Vulkan thread、解码器、Camera、Chromium、Flutter raster thread 或其他引擎线程。
3. 确认提交点：`queueBuffer`、BLAST buffer transaction、SurfaceControl transaction（图层状态更新）或硬件模块输出。
4. 确认合成与显示：latch、composition type（合成类型）、RenderEngine、HWC、FrameTimeline 和 present feedback（显示结果反馈）。

线程名只能提供线索。比如出现 GL thread 并不能单独证明它写入独立 Surface；还要把它的 swapchain、BufferQueue 与目标 layer 对上。

## 阅读路径

App 滑动卡顿从 [18.2 标准 Android View](02-android-view-standard.md) 开始；有视频、地图或相机预览时，再读 [18.4 混合渲染](04-android-view-mixed.md)、[18.6 SurfaceView](06-surfaceview.md) 和 [18.7 TextureView](07-textureview.md)。

音视频开发者可以按 [18.15 Video/HWC](15-video-overlay-hwc.md) → [18.21 MediaCodec2](21-media-codec2-tunneled-media3-abr.md) → [18.18 VRR](18-variable-refresh-rate.md) 阅读。播放器卡顿不能只查刷新率，还要对齐解码输出、buffer timestamp（内容时间戳）、acquire fence、latch 和 present。

游戏与自研引擎可以按 [18.8 OpenGL ES](08-opengl-es.md) / [18.9 Vulkan](09-vulkan-native.md) → [18.16 Game](16-game-engine.md) → 本节的分析方法阅读。要同时观察 game/render thread、GPU queue、swapchain 深度、FrameTimeline、Game Mode 与温控。

Framework 工程师可先读前面的公共主线，再看 [18.10 SurfaceControl](10-surface-control-api.md)、[18.18 VRR](18-variable-refresh-rate.md) 和 [18.24 HWUI Vulkan 多队列](24-android17-hwui-vulkan-multi-queue.md)。遇到 vendor（设备或芯片厂商）显示问题时，还要补充 Composer HAL、display driver（显示驱动）和面板证据。

## 公共主线：十二个检查点

标准 App Window 可以压缩为十二个检查点：

`vsync-app → doFrame → syncAndDrawFrame → dequeueBuffer → GPU submit → queueBuffer → BLAST transaction → SF snapshot/latch → HWC strategy → 可选 CLIENT composition → present → present feedback`

这是一张跨路径坐标表，不表示所有动作会同步、依次执行，也不要求特殊 Producer 具备完整的 HWUI slice。标准 View 的逐调用链解释由 [18.2](02-android-view-standard.md) 维护；这里仅保留比较不同 Producer 所需的公共边界。

| 检查点 | 先回答的问题 | 不能据此断言 |
| --- | --- | --- |
| `vsync-app` | 应用何时被计划唤醒 | 目标进程已经运行 |
| `doFrame` | 哪类 callback（帧回调）或前序消息占用预算 | GPU 一定正常或异常 |
| `syncAndDrawFrame` | UI 状态何时交给 RenderThread | buffer 已提交或显示 |
| `dequeueBuffer` | Producer 是否拿到可写 slot（缓冲区槽位） | 等待一定由 buffer 数不足造成 |
| GPU submit | 命令何时进入 GPU queue | submit 返回即 GPU 完成 |
| `queueBuffer` | slot、元数据和 production fence（Producer 完成写入的同步信号）何时交回 | SF 已采纳像素 |
| BLAST / `BufferTX` | buffer update 是否到达 SurfaceFlinger 进程 | acquire fence 已满足 |
| snapshot / latch | 本轮采纳哪个 layer 状态和 buffer | Android 13+ 的 buffer 已可读 |
| HWC strategy | 本帧采用哪种 composition type | 结果由 API 名称固定决定 |
| CLIENT composition | RenderEngine 是否生成 client target（GPU 合成后的显示目标） | App shader（着色器）是回退根因 |
| present / release | HWC 何时接收输出、何时归还 layer buffer | panel（物理显示面板）已完成光学响应 |
| present feedback | display 到达 Android 可观测显示边界 | 单个 layer 的 release 时间 |

## 统一分析方法

### 先区分事实、关联与结论

| 层次 | 示例 | 是否足以确认根因 |
| --- | --- | --- |
| 观察事实 | `dequeueBuffer` 持续 8 ms；目标 layer 为 CLIENT | 否 |
| 时间关联 | 等待与上一帧 release fence 较晚发出 signal 的时段重合 | 还要核对对象 |
| 因果结论 | 同一队列无可复用 slot，因为 HWC 延迟归还上一轮 buffer | 是，但必须有队列、fence 和 layer 证据 |

“同一时间发生”不等于“前者导致后者”。对象身份不清时，长 slice 只能列为候选。

### Step 1：锁定对象与路径

先建立一张对象记录表：

| 字段 | 用途 |
| --- | --- |
| package、UID、PID、关键 TID | 用应用包名、UID（应用身份标识）、PID（进程 ID）和 TID（线程 ID）锁定 Producer 与线程 |
| displayId、mode、刷新率 | 区分内外屏、虚拟显示和显示模式切换 |
| Window、Surface、layer id | 对齐 WindowManagerService（WMS）、SurfaceFlinger（SF）、Perfetto 与 Winscope（窗口和图层检查工具） |
| parent、Z-order | 确认宿主内容和独立 child layer |
| BufferQueue / BLAST | 对齐 dequeue、queue 与 `BufferTX` |
| surface/display token | 对齐 App SurfaceFrame 与 SF DisplayFrame |
| 输入动作与时间窗 | 锁定用户看到的目标帧 |

控件或框架名只给候选；必须用 Producer、输出 `Surface`、layer 拓扑和合成结果验证。

### Step 2：记录 Producer、Consumer 与 fence 的关系

| 路径 | Producer | 第一接收点 | SF 主要对象 |
| --- | --- | --- | --- |
| 标准 View / Compose | HWUI RenderThread / GPU | 应用进程内 BLAST | 宿主窗口 transaction |
| SurfaceView | codec、Camera、GL/Vulkan 等 | 独立 Surface Consumer（接收 buffer 的组件） | 独立 child layer |
| TextureView | codec、Camera、GL | App 内 `SurfaceTexture` | HWUI 采样后的宿主窗口 |
| WebView | Chromium 与宿主 HWUI | functor（把 Chromium 绘制接入 HWUI 的桥接对象）或 child Surface | 以现场拓扑为准 |
| HardwareBufferRenderer | HWUI RenderThread / GPU | 调用方 `HardwareBuffer` | 调用方提交后才送显 |

acquire fence 回答“buffer 何时可读”，release fence 回答“buffer 何时可复用”，present fence 回答“本轮 Display 何时到达显示边界”。`dequeueBuffer` 长时间等待时，应检查同一队列的可用 slot、Consumer 持有量和上一轮 release；`BufferTX` 积压时，应检查 transaction readiness（事务是否满足处理条件）、acquire，以及 buffer 最终被 latch 还是 drop（丢弃）。增加队列深度会同时增加内存和延迟，不能作为默认修复。

API 37 的 `Surface.isProducerThrottlingEnabled()` 可帮助识别 EGL/Vulkan queue/present 边界的 CPU backpressure（下游来不及消费时，Producer 被迫等待）。关闭它不会改变帧率投票（向显示系统提交的帧率偏好），也不会消除 dequeue 或 swapchain acquire 产生的正常等待。

### Step 3：对齐同一帧

采集 trace 时，要覆盖目标 App、SF、`system_server` 和上游 Producer 的线程调度，以及 gfx/view/wm 图形类别、FrameTimeline、BufferQueue/SF、GPU 与设备可提供的 HWC/Display 轨迹；layer 层级和 transaction 变化可配合 Winscope 检查。

| 轨道 | 重点 |
| --- | --- |
| App / RenderThread / 引擎 | `doFrame`、draw、dequeue/queue、GPU submit |
| codec / Camera / Chromium / Flutter | 非标准 Producer 的节奏 |
| BufferQueue / BLAST | queue 周转、transaction、`BufferTX` |
| SurfaceFlinger | transaction、snapshot/latch、RenderEngine |
| FrameTimeline | expected/actual（预期/实际时间）、surface/display token、jank type（卡顿类型） |
| GPU / HWC / Display | 异步执行、composition type 与 present |

按“锁定 token/layer → 帧开始 → CPU/GPU 生产 → transaction 到达 → acquire/latch → SF/HWC/present → 上一帧 release”的顺序复原路径。相邻帧会重叠，只看时间是否接近，无法正确配对对象。

下面的 Perfetto SQL 用于找出目标进程中带有 jank 标记的实际帧，并用 surface token 关联对应的预期帧：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT p.name AS process_name, a.layer_name,
       a.surface_frame_token, a.display_frame_token,
       e.ts AS expected_ts, e.dur AS expected_dur,
       a.ts AS actual_ts, a.dur AS actual_dur,
       a.jank_type, a.present_type, a.on_time_finish
FROM actual_frame_timeline_slice a
JOIN process p ON a.upid = p.upid
LEFT JOIN expected_frame_timeline_slice e
  ON a.upid = e.upid
 AND a.surface_frame_token = e.surface_frame_token
 AND a.layer_name = e.layer_name
WHERE p.name = 'com.example.app'
  AND a.surface_frame_token != 0
  AND a.layer_name IS NOT NULL
  AND COALESCE(a.jank_type, 'None') != 'None'
ORDER BY a.ts DESC
LIMIT 20;
```

同一 token 可能对应多行，统计前还要按 layer 处理一对多。独立 Surface 缺少完整 App FrameTimeline 时，回到 Producer、BufferQueue、layer、fence 和 present。

### Step 4：按证据模式归因

| 模式 | 主要证据 | 不能直接推断 |
| --- | --- | --- |
| 主线程 / RenderThread CPU 重 | expected/actual 与明确 CPU 子段一致 | 整段 wall time（实际经过时间）都是 GPU |
| App GPU 晚完成 | submit 不晚，GPU stage（执行阶段）或 acquire readiness（可读取条件）较晚 | `queueBuffer` 返回等于完成 |
| Buffer 队列阻塞 | dequeue 与同队列 release/Consumer 对上 | 只需增加 buffer |
| Producer 抖动 | codec/Camera/引擎 cadence（输出间隔）不稳 | SF 复用旧 buffer 就是 SF 卡顿 |
| SF CPU/GPU 超预算 | SF actual、CPU/GPU 与 jank type 相互印证 | SF actual 全属主线程 CPU |
| HWC 路径变化 | composition type、client target、GPU/功耗同变 | SurfaceView 必然获得 DEVICE |
| 显示后段延迟 | App、latch、composition 按时，present 晚 | framework trace 覆盖面板响应 |
| VRR 口径错误 | 内容帧率、render rate、refresh rate 不一致 | 固定 16.6 ms 适合所有模式 |

帧率、端到端延迟和功耗要分别记录。队列更深可能让吞吐稳定但交互更慢；CLIENT composition 可能保持帧率，却增加 GPU、带宽和功耗。

## 选型与复核

下面的决策树用于按输出对象和合成需求选择渲染入口：

```text
普通 Android UI？
├── 是：View / Compose → HWUI → 宿主窗口
└── 否：上游能否直接向 Surface 生产 buffer？
    ├── 是：需要独立 layer 或避免宿主二次采样？
    │   ├── 是：SurfaceView / Surface / ANativeWindow
    │   └── 否：需要宿主任意纹理效果？是 → TextureView
    └── 否：RenderNode 输出到自管 HardwareBuffer？是 → HardwareBufferRenderer
```

SurfaceView 提供独立 layer 条件，不保证 DEVICE、低功耗或低延迟；TextureView 通常增加一次宿主采样。WebView、Flutter 和游戏必须核查真实宿主、Producer、BufferQueue、layer 与 HWC。

复盘完成前确认：

- [ ] package/PID、display、Window、layer、BufferQueue 和时间窗已经锁定；
- [ ] Producer、第一 Consumer、SF layer 与送显路径已经记录；
- [ ] acquire、release、present fence 没有混用；
- [ ] token、frame number 或明确时序指向同一帧；
- [ ] CPU wall time（实际经过时间）、GPU execution（执行时间）与 fence wait（同步等待）已分开；
- [ ] 上一帧 release 是否让当前帧等待已经检查；
- [ ] FrameTimeline、GPU/HWC 缺失时的证据边界已说明；
- [ ] DEVICE/CLIENT 只作为设备现场结论；
- [ ] 帧率、端到端延迟、功耗分别验收；
- [ ] 修复前后设备、场景、输入和采集配置一致。

## Android 17 源码入口

下面的源码入口覆盖公共主线，全部固定到 `android-17.0.0_r1`：

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)：`scheduleFrameLocked()`、`doFrame()` 与五类 callback 顺序；
- [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：`scheduleTraversals()`、batched input、`performTraversals()`、`performDraw()`；
- [`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java) 与 [`ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)：Java HWUI 入口；
- [`RenderProxy.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/RenderProxy.cpp)、[`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：RenderThread 状态同步、绘制、dequeue/queue duration；
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：`onFrameAvailable()`、`acquireNextBufferLocked()`、`Transaction::setBuffer()`；
- [`SurfaceFlinger FrontEnd`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrontEnd/) 与 [`Layer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.cpp)：requested state、snapshot、`BufferTX`、latch 与 release callback；
- [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)：transaction readiness、latch-unsignaled、composite；
- [`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp) 与 [`HWC2.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWC2.cpp)：validate/presentOrValidate/present 和 fences；
- [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：SurfaceFrame、DisplayFrame 与 present feedback。
- [`events.sql`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/prelude/after_eof/events.sql)：`actual_frame_timeline_slice` 的列定义；查询字段应跟随采集端对应的 Perfetto schema。

内核侧按 [`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6) 核对 dma-buf、dma-fence/sync_file、DRM atomic 与 vblank。Vendor GPU、Composer、display driver 和面板时序要用目标设备源码与 trace 补证。

## 总结：用角色和边界读 trace

看到任何 App 出图问题，先确定 Producer、Surface/layer、合成位置和 present 边界，再进入线程耗时。标准窗口从 `vsync-app → doFrame → RenderThread → BLAST → SurfaceFlinger → HWC` 建立基线；特殊框架与硬件 Producer 只是在某些节点替换角色或增加分支。

`queueBuffer` 说明内容已提交，`BufferTX` 说明 SurfaceFlinger 侧仍有待处理的 buffer 更新，latch 说明本轮已经采纳，present fence 提供显示管线完成呈现的时间反馈。按顺序对齐这四类证据，才能区分帧开始晚、Producer 完成晚、Consumer 等待、退回 GPU 合成和显示后段延迟。
