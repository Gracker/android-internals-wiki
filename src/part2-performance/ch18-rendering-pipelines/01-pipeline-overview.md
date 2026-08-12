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

Perfetto 里出现一帧超时，定位工作不应从“最长的 slice”开始，而应先回答三个问题：

1. 谁在生产本帧 buffer？
2. buffer 进入哪个 `Surface`，是否形成独立 layer？
3. 本帧在哪里合成，又在哪个时间边界完成 present？

标准 App Window 的 Producer 通常是应用进程里的 HWUI RenderThread；SurfaceView、Camera、Video、WebView、Flutter、游戏和 React Native 可能把生产工作交给引擎线程、解码器或硬件模块。它们都可能经过 BufferQueue、SurfaceFlinger 和 HWC，但线程、layer 数量、合成位置与 FrameTimeline 覆盖程度并不相同。

`queueBuffer`、`latch` 和 `present fence` 分别属于提交、采纳和显示反馈阶段。看到其中一个事件，只能证明显示路径走到了对应位置，不能替代其他阶段的证据。这里先固定公共主线，后续章节再解释各出图类型从哪里分叉。

当前实现锚点是 Android 17 / API 37 的 `android-17.0.0_r1`。涉及 dma-buf、sync_file、DRM/KMS 或调度器实现时，内核锚点统一为 `android17-6.18-2026-06_r6`；framework 结论不依靠某个 kernel 函数推导。

## 用四个坐标识别出图类型

`SurfaceView`、`TextureView`、WebView、Flutter 和 Compose 是 API 或框架名称。名称本身不足以确定 trace 中的图形路径。同一个 Flutter 页面可能使用 `SurfaceView` 或 `TextureView` 作为宿主，Platform View 还会改变 layer 拓扑；同一个播放器也可能在普通 buffer queue、SurfaceView 独立 layer 与 tunneled/sideband 路径之间切换。

每次分析先固定四个坐标：

| 坐标 | 要确认的对象 | Trace 或源码证据 |
|---|---|---|
| Producer | HWUI RenderThread、GL/Vulkan thread、Chromium、Flutter raster thread、Camera HAL、MediaCodec、游戏引擎或其他模块 | 线程 slice、GPU submission、decoder/camera 事件 |
| 输出目标 | App Window、独立 `Surface`、`SurfaceTexture`、swapchain、离屏 `HardwareBuffer` 或 sideband stream | BufferQueue、ANativeWindow、SurfaceControl、layer dump |
| layer 拓扑 | 内容进入宿主窗口，还是形成一个或多个独立 child layer | layer parent、relative layer、Z-order、`BufferTX` |
| 合成与 present | 宿主 HWUI 采样、SurfaceFlinger CLIENT composition、HWC DEVICE composition 或专用媒体路径 | RenderEngine、composition type、HWC、present fence |

线程名只说明某段代码在哪条线程执行。确认渲染类型还要把线程、swapchain/BufferQueue、SurfaceControl 和目标 layer 连到同一条路径。看到 `GLThread` 不足以证明页面一定存在独立 layer；看到 `SurfaceView` 对象也不足以证明本帧拿到了 overlay。

## 版本与架构对照表

Android 9 到 Android 17 的图形栈不能只用“Legacy”与“BLAST”二分。对 trace 更有帮助的写法，是标出哪个版本可以使用哪些对象和观测方法。

| 平台 | 公共显示主线 | Trace 判读要点 |
|---|---|---|
| Android 9 / API 28 | App Window 常见传统 BufferQueue producer/consumer 路径 | 不应期待 BLAST 或 FrameTimeline；以 `Choreographer`、HWUI、`queueBuffer`、SF/HWC slice 为主 |
| Android 10 / API 29 | `SurfaceControl.Transaction` 能力扩展，App Window 仍处于迁移前后混合期 | 不要只凭系统版本断定采用 BLAST，要以进程内对象和 trace 为证 |
| Android 11 / API 30 | BLAST 进入平台主线，窗口 buffer 与 layer transaction 的组织方式开始改变 | 旧资料中的 `BufferStateLayer` 只适合对应旧 tag，不能拿来解释 Android 17 的 FrontEnd |
| Android 12 / API 31 | BLAST 与 FrameTimeline 构成现代 trace 基线 | 标准 App Window 可用 SurfaceFrame/DisplayFrame token 对齐；独立 Surface 仍需 layer、BufferQueue 与 fence 证据 |
| Android 13 / API 33 | `AutoSingleLayer` 下的 latch-unsignaled 策略成为重要边界 | acquire fence 未 signal 不再等于 transaction 必定无法 latch；硬件读取仍要遵守同步约束 |
| Android 14 / API 34 | 公共 Choreographer→HWUI→BLAST→SF→HWC 骨架延续；SurfaceView 增加 alpha 与 lifecycle 能力 | 标准窗口仍按公共主线读，独立 Surface 的透明度与生命周期要单独核对 |
| Android 15 / API 35 | Window/SurfaceView 源码与 API 面开始提供 desired HDR headroom，r1 中仍带 feature flag 边界 | headroom 是请求；目标设备 flag、bit depth、面板与显示策略仍要核对 |
| Android 16 / API 36 | SurfaceView 源码增加整数 `compositionOrder`，r1 API 签名带 `@FlaggedApi`；公共主线延续 | 多 Surface 页面要记录 parent、relative layer、flag 状态与 Z-order |
| Android 17 / API 37 | 锚定 FrontEnd `RequestedLayerState` / `LayerSnapshot`、预测 present time、现行 BLAST/HWC 路径；SurfaceView blur region 与 `compositionOrder` 仍带 flag 边界 | 源码按 `android-17.0.0_r1` 的对象名解释；旧 `DispSync`、固定 phase offset 和逐个旧 Layer latch 模型不能直接套用 |

这张表描述的是观察边界，不表示每个版本都重做了一套渲染管线。BLAST 改变 buffer 与窗口状态进入 SurfaceFlinger 的组织方式，没有取消 Producer/Consumer 分工，也没有取消 acquire/release fence。

## 典型模式对比

先按 Producer、输出目标、layer 拓扑与合成位置区分主干模式：

| 模式 | 主要 Producer | Surface/layer 形态 | 主要合成位置 | 容易误判的点 | 章节 |
|---|---|---|---|---|---|
| 标准 Android View | MainThread 准备状态，HWUI RenderThread/GPU 产出 | 宿主 App Window | SF 选择 DEVICE 或 CLIENT | MainThread `draw()` 结束不等于 buffer 已提交 | [18.2](02-android-view-standard.md) |
| Software / 离屏 | `lockCanvas()` 线程、CPU raster 或离屏 GPU | 可见 Surface 或离屏 buffer | 可见目标进入 SF/HWC；离屏目标由下游消费 | “软件绘制”不等于没有 BufferQueue；离屏完成 fence 也不是 present fence | [18.3](03-android-view-software.md)、[18.17](17-hardware-buffer-renderer.md) |
| 混合渲染 | 宿主 HWUI + 一个或多个独立 Producer | App Window 与 child layer 并存 | SF/HWC 拼接多层 | 不能用宿主窗口一条 FrameTimeline 代表所有独立 Surface | [18.4](04-android-view-mixed.md) |
| 多窗口 | 每个 Window 各有 ViewRoot/Surface；线程可能同进程共享，也可能跨进程 | 多个 Window layer | 每个 display 分别组织输出 | “多窗口必定同一主线程串行”只适用于部分同进程场景 | [18.5](05-android-view-multi-window.md) |
| SurfaceView | 解码器、Camera、GL/Vulkan 或其他 Producer | 独立 child Surface/layer | 常由 SF/HWC 与宿主拼层 | 独立 layer 有利于 overlay，但不保证低延迟或 DEVICE composition | [18.6](06-surfaceview.md) |
| TextureView | 外部 Producer 写入 `SurfaceTexture` | 内容作为纹理进入宿主 View 树 | 宿主 HWUI 再采样到 App Window | 成本是额外采样/宿主合成，不宜笼统写成固定 CPU 拷贝 | [18.7](07-textureview.md) |
| OpenGL ES | GL thread / engine thread | EGL window surface 对应 BufferQueue | SF/HWC | `eglSwapBuffers()` 返回不代表 GPU 写完或已经 present | [18.8](08-opengl-es.md) |
| Vulkan | engine/render thread | `VkSwapchainKHR` 对接 ANativeWindow | SF/HWC | 显式 API 可以降低部分 driver 开销，但 CPU 成本取决于引擎、同步和驱动 | [18.9](09-vulkan-native.md) |
| WebView | Chromium renderer/compositor、Viz 与宿主进程协作 | Chromium surface 与宿主窗口组合，具体拓扑依实现而定 | Chromium 合成后进入 Android 显示链 | 只看 App MainThread 会漏掉 renderer/GPU 进程 | [18.13](13-webview-rendering.md) |
| Flutter | UI/raster/platform thread 与 Impeller/Skia backend | 宿主可用 SurfaceView 或 TextureView；Platform View 再增加分支 | 宿主 layer 与 Platform View 共同进入 SF/HWC | 框架名不能确定宿主 render mode | [18.12](12-flutter-rendering.md) |
| Camera | Camera HAL、ISP 与应用/系统消费者 | 预览 Surface、ImageReader、编码器等多消费者 | 预览常通过独立 layer 参与合成 | request/result 完成不等于预览已 present | [18.14](14-camera-pipeline.md) |
| Video / HWC | MediaCodec、解码器、播放器 | SurfaceView buffer queue 或 tunneled/sideband 路径 | HWC overlay、专用媒体路径或 CLIENT fallback | 解码完成、releaseOutputBuffer 与上屏时间不是同一边界 | [18.15](15-video-overlay-hwc.md)、[18.21](21-media-codec2-tunneled-media3-abr.md) |
| 游戏引擎 | game/render thread、GL/Vulkan queue | ANativeWindow swapchain，可能叠加独立 UI/video layer | SF/HWC | 平均 FPS 会掩盖 pacing、queue depth 与 present 抖动 | [18.16](16-game-engine.md) |
| Compose | Compose runtime 与 UI thread 生成状态，HWUI RenderThread/GPU 产出 | 默认仍是宿主 App Window | SF/HWC | recomposition、layout、draw 与 GPU 提交属于不同阶段 | [18.23](23-compose-rendering-pipeline.md) |
| React Native | JS、Fabric/UI、HWUI；第三方原生组件可另建 Surface | 标准 View 树或 SurfaceView/TextureView 分支 | 取决于宿主与原生组件拓扑 | JS thread 只是 Producer 链的一段，不能代表 present | 这里只给分型基线 |

[18.10 SurfaceControl API](10-surface-control-api.md) 与 [18.11 ANGLE](11-angle-gles-vulkan.md) 分别解释 layer 控制和 GLES→Vulkan 翻译。[18.5 多窗口/PiP/Freeform](05-android-view-multi-window.md)、[18.18 VRR](18-variable-refresh-rate.md)、[18.20 XR](20-android-xr-spatial-ui-rendering.md) 继续分析 window/display 分支。本节后半给出所有路径共用的取证步骤。

### 快速识别当前管线

一段 trace 可以先做四项检查：

1. 找到目标 Window、Surface 和 layer，确认是一层还是多层。
2. 找到 Producer：MainThread/RenderThread、GL/Vulkan thread、解码器、Camera、Chromium、Flutter raster thread 或其他引擎线程。
3. 确认提交点：`queueBuffer`、BLAST buffer transaction、SurfaceControl transaction 或硬件模块输出。
4. 确认合成与显示：latch、composition type、RenderEngine、HWC、FrameTimeline 和 present feedback。

线程名只能提供线索。比如出现 GL thread 并不能单独证明它写入独立 Surface；还要把它的 swapchain、BufferQueue 与目标 layer 对上。

## 阅读路径

App 滑动卡顿从 [18.2 标准 Android View](02-android-view-standard.md) 开始；有视频、地图或相机预览时，再读 [18.4 混合渲染](04-android-view-mixed.md)、[18.6 SurfaceView](06-surfaceview.md) 和 [18.7 TextureView](07-textureview.md)。

音视频开发者可以按 [18.15 Video/HWC](15-video-overlay-hwc.md) → [18.21 MediaCodec2](21-media-codec2-tunneled-media3-abr.md) → [18.18 VRR](18-variable-refresh-rate.md) 阅读。播放器卡顿不能只查刷新率，还要对齐解码输出、buffer timestamp、acquire fence、latch 和 present。

游戏与自研引擎可以按 [18.8 OpenGL ES](08-opengl-es.md) / [18.9 Vulkan](09-vulkan-native.md) → [18.16 Game](16-game-engine.md) → 本节的分析方法阅读。要同时观察 game/render thread、GPU queue、swapchain 深度、FrameTimeline、Game Mode 与温控。

Framework 工程师可先读前面的公共主线，再看 [18.10 SurfaceControl](10-surface-control-api.md)、[18.18 VRR](18-variable-refresh-rate.md) 和 [18.24 HWUI Vulkan 多队列](24-android17-hwui-vulkan-multi-queue.md)。遇到 vendor 显示问题时，还要补 Composer HAL、display driver 和面板证据。

## 公共主线：十二个检查点

标准 App Window 可以压缩为十二个检查点：

`vsync-app → doFrame → syncAndDrawFrame → dequeueBuffer → GPU submit → queueBuffer → BLAST transaction → SF snapshot/latch → HWC strategy → 可选 CLIENT composition → present → present feedback`

这是一张跨路径坐标表，不表示所有动作同步串行，也不要求特殊 Producer 具备完整的 HWUI slice。标准 View 的逐调用链解释由 [18.2](02-android-view-standard.md) 维护；这里仅保留比较不同 Producer 所需的公共边界。

| 检查点 | 先回答的问题 | 不能据此断言 |
| --- | --- | --- |
| `vsync-app` | 应用何时被计划唤醒 | 目标进程已经运行 |
| `doFrame` | 哪类 callback 或前序消息占用预算 | GPU 一定正常或异常 |
| `syncAndDrawFrame` | UI 状态何时交给 RenderThread | buffer 已提交或显示 |
| `dequeueBuffer` | Producer 是否拿到可写 slot | 等待一定由 buffer 数不足造成 |
| GPU submit | 命令何时进入 GPU queue | submit 返回即 GPU 完成 |
| `queueBuffer` | slot、元数据和 production fence 何时交回 | SF 已采纳像素 |
| BLAST / `BufferTX` | buffer update 是否到达 SF server | acquire fence 已满足 |
| snapshot / latch | 本轮采纳哪个 layer 状态和 buffer | Android 13+ 的 buffer 已可读 |
| HWC strategy | 本帧采用哪种 composition type | 结果由 API 名称固定决定 |
| CLIENT composition | RenderEngine 是否生成 client target | App shader 是回退根因 |
| present / release | HWC 何时收输出、何时归还 layer buffer | panel 已完成光学响应 |
| present feedback | display 到达 Android 可观测显示边界 | 单个 layer 的 release 时间 |

## 统一分析方法

### 先区分事实、关联与结论

| 层次 | 示例 | 是否足够定根因 |
| --- | --- | --- |
| 观察事实 | `dequeueBuffer` 持续 8 ms；目标 layer 为 CLIENT | 否 |
| 时间关联 | 等待与上一帧 release fence 晚 signal 同窗 | 还要核对对象 |
| 因果结论 | 同一队列无可复用 slot，因为 HWC 延迟归还上一轮 buffer | 是，但必须有队列、fence 和 layer 证据 |

“同一时间发生”不等于“前者导致后者”。对象身份不清时，长 slice 只能列为候选。

### Step 1：锁定对象与路径

先建立对象身份卡：

| 字段 | 用途 |
| --- | --- |
| package、UID、PID、关键 TID | 锁定 Producer 与线程 |
| displayId、mode、刷新率 | 区分内外屏、虚拟显示和模式切换 |
| Window、Surface、layer id | 对齐 WMS、SF、Perfetto 与 Winscope |
| parent、Z-order | 确认宿主内容和独立 child layer |
| BufferQueue / BLAST | 对齐 dequeue、queue 与 `BufferTX` |
| surface/display token | 对齐 App SurfaceFrame 与 SF DisplayFrame |
| 输入动作与时间窗 | 锁定用户看到的目标帧 |

控件或框架名只给候选；必须用 Producer、输出 `Surface`、layer 拓扑和合成结果验证。

### Step 2：画出 Producer、Consumer 与 fence

| 路径 | Producer | 第一接收点 | SF 主要对象 |
| --- | --- | --- | --- |
| 标准 View / Compose | HWUI RenderThread / GPU | 应用进程内 BLAST | 宿主窗口 transaction |
| SurfaceView | codec、Camera、GL/Vulkan 等 | 独立 Surface Consumer | 独立 child layer |
| TextureView | codec、Camera、GL | App 内 `SurfaceTexture` | HWUI 采样后的宿主窗口 |
| WebView | Chromium 与宿主 HWUI | functor 或 child Surface | 以现场拓扑为准 |
| HardwareBufferRenderer | HWUI RenderThread / GPU | 调用方 `HardwareBuffer` | 调用方提交后才送显 |

acquire fence 回答“何时可读”，release fence 回答“何时可复用”，present fence 回答“本轮 Display 何时到达显示边界”。`dequeueBuffer` 长等时查同队列的可用 slot、Consumer 持有量和上一轮 release；`BufferTX` 积压时查 transaction readiness、acquire、latch/drop。增加队列深度会同时增加内存和延迟，不是默认修复。

API 37 的 `Surface.isProducerThrottlingEnabled()` 可帮助识别 EGL/Vulkan queue/present 边界的 CPU 回压。关闭它不会改变帧率投票，也不会消除 dequeue 或 swapchain acquire 的自然回压。

### Step 3：对齐同一帧

采集要覆盖目标 App、SF、system_server 和上游 Producer 的线程调度，以及 gfx/view/wm、FrameTimeline、BufferQueue/SF、GPU 与设备可用的 HWC/Display 轨迹；层级与 transaction 变化配合 Winscope。

| 轨道 | 重点 |
| --- | --- |
| App / RenderThread / 引擎 | `doFrame`、draw、dequeue/queue、GPU submit |
| codec / Camera / Chromium / Flutter | 非标准 Producer 的节奏 |
| BufferQueue / BLAST | queue 周转、transaction、`BufferTX` |
| SurfaceFlinger | transaction、snapshot/latch、RenderEngine |
| FrameTimeline | expected/actual、surface/display token、jank type |
| GPU / HWC / Display | 异步执行、composition type 与 present |

按“锁定 token/layer → 起帧 → CPU/GPU 生产 → transaction 到达 → acquire/latch → SF/HWC/present → 上一帧 release”复原。相邻帧会重叠，只按时间邻近不能配对对象。

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
| 主线程 / RenderThread CPU 重 | expected/actual 与明确 CPU 子段一致 | 整段墙钟时间都是 GPU |
| App GPU 晚完成 | submit 不晚，GPU stage/acquire readiness 晚 | `queueBuffer` 返回等于完成 |
| Buffer 回压 | dequeue 与同队列 release/Consumer 对上 | 只需增加 buffer |
| Producer 抖动 | codec/Camera/引擎 cadence 不稳 | SF 复用旧 buffer 就是 SF 卡顿 |
| SF CPU/GPU 超预算 | SF actual、CPU/GPU 与 jank type 相互印证 | SF actual 全属主线程 CPU |
| HWC 路径变化 | composition type、client target、GPU/功耗同变 | SurfaceView 必然获得 DEVICE |
| 显示后段延迟 | App、latch、composition 按时，present 晚 | framework trace 覆盖面板响应 |
| VRR 口径错误 | 内容帧率、render rate、refresh rate 不一致 | 固定 16.6 ms 适合所有模式 |

帧率、端到端延迟和功耗要分别记录。队列更深可能让吞吐稳定但交互更慢；CLIENT composition 可能保持帧率，却增加 GPU、带宽和功耗。

## 选型与复核

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
- [ ] Producer、第一 Consumer、SF layer 与送显路径已经画出；
- [ ] acquire、release、present fence 没有混用；
- [ ] token、frame number 或明确时序指向同一帧；
- [ ] CPU wall time、GPU execution 与 fence wait 已分开；
- [ ] 上一帧 release 是否反压当前帧已经检查；
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

`queueBuffer` 说明内容已提交，`BufferTX` 说明 SF server 侧有 pending buffer update，latch 说明本轮采纳，present fence 提供 display-present 时间反馈。四者按顺序对齐，才能区分起帧晚、生产晚、消费等待、composition 回退和显示后段延迟。
