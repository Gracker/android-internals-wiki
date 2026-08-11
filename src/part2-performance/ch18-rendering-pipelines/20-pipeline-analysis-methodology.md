---
title: "Android 17 渲染管线分析方法"
chapter: "18.20"
section: "18.20"
section_title: "Android 17 渲染管线分析方法"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: ["方法论", "渲染管线", "Perfetto", "dumpsys", "诊断", "BufferQueue", "性能分析"]
reviewed_date: "2026-07-03"
reviewed_by: "openclaw-task6"
related_chapters: ["18.1", "2.6", "13.5", "15.1", "18.13", "18.14", "18.15"]
created_by: "rendering-pipelines-merge"
created_date: "2026-04-09"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
task6_result: "pass-light-edit"
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-03T08:38:28+08:00"
task2b_result: "fixed"
repaired_date: "2026-04-24"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-05-21T07:17:00+08:00"
last_task6_audit: "2026-07-03"
last_task9_audit: 2026-07-03
last_task9_audit_at: 2026-07-03T02:24:40+08:00
last_task9_audit_log: logs/deep-review/2026-07-03-02-audit.md
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-04
last_task9_autofix_at: 2026-07-03
updated_by: "openclaw-task9"
updated_date: "2026-07-03"
p0: 0
p1: 0
p2: 0
task9_review_notes: "2026-07-03 Task9 idle-audit AUTO-FIX: P1 版本差异 1 处；18.20 快速判断清单的 Flutter 观察点从旧 UI/Raster/Platform 口径修正为 Flutter 3.32 stable+ Main(UI+Platform)/Raster/IO，3.31- 或定制 Embedder 才看 UI/Platform 分离；详见 logs/deep-review/2026-07-03-02-audit.md。 | 2026-07-03 Task9 deep review: pass-tech-review；无 P0/P1/P2；task6 已通过且 queue.json 无 pending，自动晋升 finalized；详见 logs/deep-review/2026-07-03-08-deep-review.md。"
last_task2b_verifier_at: "2026-07-03T07:32:03+08:00"
last_task6_at: "2026-07-03T08:10:00+08:00"
last_task9_review_log: "logs/deep-review/2026-07-03-08-deep-review.md"
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
last_verified: "2026-07-31"
last_verified_against: "android-17.0.0_r1 (DrawFrameTask, CanvasContext, WebViewFunctor, Surface, BLASTBufferQueue, BufferQueueProducer, SurfaceFlinger FrontEnd, CompositionEngine, HWComposer, FrameTimeline) / Android Graphics 与 Perfetto 官方文档 / android17-6.18-2026-06_r6 (dma-fence, sync_file, DRM vblank, scheduler)"
confidence: high
last_idle_audit_at: "2026-07-26T22:35:34+08:00"
last_idle_audit_run_id: "20260726-223534-idle-audit-c8b734d5"
last_idle_audit_log: "logs/audit/2026-07-26-20260726-223534-idle-audit-c8b734d5-idle-audit.md"
idle_audit_result: "pass-frontmatter-source-marking"
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md"
    role: "渲染类型、标准窗口十二锚点与证据链基线"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S01_baseline_12_anchor_pipeline/source.md"
    role: "App 起帧、Buffer 提交、SF latch、HWC present 与 fence 的十二锚点"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S05_mixed_rendering_architecture/source.md"
    role: "混合页面的单宿主 Buffer 与多 Surface/Layer 边界"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S09_webview_functor_drawfn_pipeline/source.md"
    role: "WebView 默认硬件路径中的 functor、DrawFn、宿主 RenderThread 与 Chromium 边界"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S12_video_hwc_overlay_decision_pipeline/source.md"
    role: "HWC composition strategy、client target 与 present/release fence 路径"
  - type: official
    path: "https://source.android.com/docs/core/graphics/architecture"
    role: "Android 图形架构与 SurfaceFlinger/HWC 分工"
  - type: official
    path: "https://source.android.com/docs/core/graphics/arch-bq-gralloc"
    role: "BufferQueue、gralloc、Producer/Consumer 与 Buffer slot 模型"
  - type: official
    path: "https://source.android.com/docs/core/graphics/sync"
    role: "acquire、release、present fence 的同步模型"
  - type: official
    path: "https://source.android.com/docs/core/graphics/unsignaled-buffer-latch"
    role: "Android 13+ 受限场景下的 unsignaled buffer latching"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
    role: "Android 12+ FrameTimeline、surface/display token 与 SurfaceView 限制"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
    role: "Trace Processor 查询模型"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
    role: "android.frames.timeline 标准库表与字段"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp"
    role: "UI 线程与 RenderThread 同步、draw frame 调度"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp"
    role: "HWUI frame 生命周期、swap 与 FrameTimeline 上报"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h"
    role: "HWUI WebView functor 接口及 DrawFn 调用边界"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Surface.java"
    role: "API 37 producer throttling 公开语义与自然回压边界"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
    role: "应用进程内取得 BufferItem 并通过 SurfaceControl transaction 提交 Buffer"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp"
    role: "dequeue/queue、slot 状态与 producer throttling 实现"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/LayerLifecycleManager.cpp"
    role: "Android 17 SurfaceFlinger 前端 layer 生命周期与 transaction 应用"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/LayerSnapshotBuilder.cpp"
    role: "Layer 层级、可见性与合成输入 snapshot 构建"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp"
    role: "composition strategy 选择、可选 client composition 与输出流程"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Display.cpp"
    role: "HWC strategy 应用、client target 与 display present"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp"
    role: "validate/present、present fence 与各 Layer release fence"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp"
    role: "SurfaceFlinger 的 surface/display frame token 与 jank 上报"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c"
    role: "内核异步执行完成点、signal 与 wait 基础设施"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c"
    role: "dma_fence 通过 sync_file 文件描述符跨用户空间边界传递"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c"
    role: "DRM CRTC vblank 计数、时间戳与中断生命周期"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c"
    role: "线程 runnable、调度与阻塞状态的内核边界"
---

## 为什么需要渲染路径分析方法论

用户只说“App 卡了”时，Perfetto 往往会同时出现主线程、RenderThread、SurfaceFlinger、GPU、HWC 和显示设备等轨道。每条轨道都可能很忙，但“忙”只是一条观察事实，不能单独证明它造成了用户看到的卡顿。开始读耗时之前，应先确认目标帧属于哪个进程、哪个窗口或 Layer、哪个 BufferQueue，以及哪一轮 display present。

同一块可见内容可能走完全不同的显示路径：

- 普通 View/Compose 内容由宿主窗口的 HWUI RenderThread 生产；
- `SurfaceView` 通常拥有独立 Surface 和独立 Layer，视频解码器、Camera HAL 或游戏引擎可以直接成为 Producer；
- `TextureView` 的上游内容先进入 `SurfaceTexture`，再由宿主 RenderThread 采样进窗口 Buffer；
- WebView 可能把网页内容通过 functor 并入宿主窗口，也可能出现独立子 Surface；
- `HardwareBufferRenderer` 把 `RenderNode` 渲染到调用方提供的 `HardwareBuffer`，它不会自动把结果送到屏幕。

因此，诊断应按固定顺序推进：

1. 识别当前内容的 Surface/Layer 身份与渲染路径；
2. 画出 Producer、队列 Consumer、SurfaceFlinger Layer 和三类 fence；
3. 用 Perfetto、Winscope 与 dumpsys 把同一帧的证据对齐；
4. 只在证据足够时，把问题归到生产、队列回压、系统合成或显示输出。

当前平台锚点是 Android 17 / API 37 的 `android-17.0.0_r1`。Android 9—16 只用于解释 trace 能力和对象模型的变化。涉及 dma-buf、`sync_file`、DRM/KMS 或内核调度时，kernel 锚点统一为 `android17-6.18-2026-06_r6`。

### 用十二个锚点复原标准窗口的一帧

Android 17 标准窗口可以按以下对象和事件复原：`VSYNC-app` → Choreographer 的 Input、Animation、InsetsAnimation、Traversal、Commit 回调 → `ViewRootImpl`/HWUI 的 `syncAndDrawFrame` → RenderThread `DrawFrameTask` → `dequeueBuffer` → App GPU 写 Buffer → `queueBuffer` → 应用进程内 BLAST 取得 `BufferItem` 并生成 `setBuffer()` transaction → SurfaceFlinger FrontEnd 应用 transaction、更新 Layer snapshot → latch/选择合成策略 → 可选的 RenderEngine client composition → HWC present → present/release fence。

这条链用于标记检查点，不表示所有动作都同步串行执行。App GPU、SurfaceFlinger、RenderEngine、HWC 与显示设备会并行工作；同一段 trace 里还会交错上一帧的 release 与下一帧的 dequeue。诊断时必须用 Surface、Layer、token、frame number 和 fence 确认对象，不能只按时间邻近关系配对。

### 版本边界

| 版本 | 分析时应采用的边界 |
| --- | --- |
| Android 9—10 | 没有当前的 FrameTimeline 主表；按该版本的 `doFrame`、BufferQueue、SurfaceFlinger 与 fence 轨迹复原 |
| Android 11 | 标准窗口开始迁移到 BLAST；旧设备和厂商分支仍要按对应 tag 与现场对象确认 |
| Android 12 | FrameTimeline 可用于连接 App SurfaceFrame 与 SF DisplayFrame，但独立 Surface 的覆盖仍有限 |
| Android 13—16 | 受限场景允许 unsignaled buffer latching；latch 时间不能代替 acquire fence signal 时间 |
| Android 17 / API 37 | 以 SurfaceFlinger FrontEnd snapshot 模型分析 Layer；`Surface` 增加 producer throttling 的查询与控制接口，便于辨认 queue/present 边界的 CPU 回压 |

### 先区分事实、关联与结论

一次可靠的复盘至少要记录三层信息：

| 层次 | 示例 | 能否直接定根因 |
| --- | --- | --- |
| 观察事实 | `dequeueBuffer` 持续 8 ms；目标 Layer 本轮为 `CLIENT` | 不能 |
| 时间关联 | `dequeueBuffer` 与上一帧 release fence 晚 signal 同窗 | 仍需确认对象身份 |
| 因果结论 | 目标 BufferQueue 无可复用 slot，原因是上一轮 HWC 延迟归还该 Layer 的 Buffer | 可以，但必须有队列、fence 和 Layer 证据 |

只有按这三层记录，才能避免把时间关联误写成因果结论。`queueBuffer` 已返回不代表 GPU 写入完成，latch 已发生不代表 acquire fence 已经 signal，HWC 的 `present()` 已返回也不代表面板像素已经完成光学响应。

## Step 1：识别渲染模式

分析开始时先回答“当前看到的是哪一个显示对象”。控件类名只能提供候选路径，Layer 树、线程、BufferQueue 和 frame token 才是现场证据。

### 快速判断清单

| 场景 | 典型路径 | 最直接的观察点 |
| --- | --- | --- |
| 普通 RecyclerView / Compose | 18.2 标准窗口路径 | App `Choreographer#doFrame`、RenderThread `DrawFrame`、宿主窗口 Layer |
| `SurfaceView` 视频 / Camera | 18.6、18.14、18.15 独立 Surface | 独立 Layer、上游 Producer、BufferQueue、HWC composition type |
| `TextureView` 视频 / Camera | 18.7 宿主纹理采样 | `SurfaceTexture` / `updateTexImage`、宿主 RenderThread、宿主窗口 Buffer |
| WebView | 18.13 WebView 路径 | functor、Chromium/Viz 线程、child Surface 或纹理采样，以现场为准 |
| 地图或原生 GLES/Vulkan | 18.8、18.9 Native Graphics | 引擎渲染线程、EGL/Vulkan submit、目标 `ANativeWindow` |
| Flutter | 18.12 Flutter 路径 | Flutter 3.32 stable+ 看 Main（UI+Platform）/ Raster / IO；旧版或定制 Embedder 再确认线程模型 |
| 游戏（Unity / Unreal） | 18.16 游戏路径 | 引擎主线程、Render/RHI 线程、GPU submit、独立 Surface |
| `HardwareBufferRenderer` | 18.17 离屏或自管 Buffer 路径 | draw request、调用方 `HardwareBuffer`、完成 fence、后续 `setBuffer()`（若送显） |
| PiP / Freeform | 18.18 多窗口路径 | WM Shell transition、WMS 窗口树、SurfaceFlinger Layer 树、Buffer transaction |
| 高刷 / VRR | 18.19 刷新率路径 | 内容帧率、应用 render rate、显示 refresh rate、FrameTimeline |

BLAST 是当前 Android 17 标准窗口与许多独立 Surface 路径的重要实现，但不要仅凭系统版本推断现场对象。Android 11 的标准窗口迁移与后续 SurfaceView 路径的演进属于不同的版本结论。诊断 Android 17 时，直接确认应用进程里的 `BLASTBufferQueue`、SurfaceControl transaction 和对应 Layer；复盘旧设备时再回到该版本源码。

### 建立对象身份卡

在 trace 截图或问题单中记录以下字段，后续才不会把同名窗口、旧 Layer 或另一个 display 的帧串在一起：

| 字段 | 用途 |
| --- | --- |
| package / PID / UID | 锁定 Producer 所在进程 |
| displayId 与刷新模式 | 区分内屏、外屏、虚拟显示和模式切换 |
| Window / Surface / Layer 名称与 layer id | 对齐 WMS、SurfaceFlinger、Winscope |
| Layer parent、relative layer、Z-order | 确认可见关系和独立 Surface |
| BufferQueue / BLAST 名称 | 对齐 `dequeueBuffer`、`queueBuffer`、`BufferTX` |
| surface frame token / display frame token | 对齐 App SurfaceFrame 与 SF DisplayFrame |
| 复现时间窗与输入动作 | 避免从整段 trace 猜测目标帧 |

### dumpsys 快速确认

下面的命令只用于建立对象清单和补充时间戳；它们不能替代 Perfetto 或 Winscope 的时序证据。

```bash
adb shell dumpsys SurfaceFlinger --list
adb shell dumpsys SurfaceFlinger > /data/local/tmp/sf.txt
adb pull /data/local/tmp/sf.txt .
adb shell dumpsys SurfaceFlinger --latency "<LayerName>"
```

`--latency` 是旧式的 Layer 时间戳接口，不同版本和厂商实现的可用性、列含义与历史长度可能不同。它既不能给出 composition type，也不能证明某个 Buffer 在 HWC、显示驱动或面板中的状态。Layer 层级、可见区域和 transaction 应优先用 Winscope；单帧 deadline、线程、GPU 与 fence 应回到 Perfetto。

## Step 2：确定 Producer / Consumer 路径

渲染路径确定后，把“谁写 Buffer、谁从队列取 Buffer、谁把 Layer 送入合成”分别写清。现代标准窗口的 BLAST Consumer 位于应用进程，它取得 `BufferItem` 后通过 `SurfaceComposerClient::Transaction::setBuffer()` 把 Buffer update 送到 SurfaceFlinger。把第一 Consumer 直接写成 SurfaceFlinger，会丢掉 BLAST transaction 这一段。

| 路径类型 | Buffer Producer | 第一消费或接收点 | SurfaceFlinger 看到什么 |
| --- | --- | --- | --- |
| Android 17 标准窗口 | HWUI RenderThread / GPU | 应用进程内的 BLAST Consumer | 宿主窗口 Layer 的 buffer transaction |
| `SurfaceView` 独立 Surface | MediaCodec、Camera、游戏/GL 线程等 | 对应 Surface 的 Consumer；当前实现常由 BLAST 协调 transaction | 独立 child Layer，可单独参与 HWC |
| `TextureView` | MediaCodec、Camera、GL Producer | App 的 `SurfaceTexture` | 上游 Buffer 被宿主 RenderThread 采样后，只看到宿主窗口输出 |
| WebView functor | Chromium renderer/compositor/Viz 与宿主 HWUI 协作 | 宿主 RenderThread 参与合成 | 主要表现为宿主窗口 Layer；子 Surface 要另行识别 |
| `HardwareBufferRenderer` | HWUI RenderThread / GPU | 没有独立 BufferQueue Consumer；调用方等待完成 fence 并继续持有 `HardwareBuffer` | 默认看不到；调用方 `SurfaceControl.Transaction.setBuffer()` 后才形成送显输入 |
| Camera `ImageReader` 分析 | Camera HAL / ISP | `ImageReader` / 分析线程 | 通常不直接送屏，但长期持有 Image 会反压 Camera stream |
| Camera 录制 | Camera HAL / ISP | MediaCodec 输入 Surface | 编码队列；预览 Layer 是另一条 stream |

旧版标准窗口可能由 SurfaceFlinger 直接持有 BufferQueue Consumer，不能用 Android 17 的 BLAST 对象反推 Android 9/10。分析旧系统时，应使用对应 tag 的 `Surface`、BufferQueue 和 Layer 实现。

### 三类 fence 决定读写边界

Buffer 引用回答“访问哪块内存”，fence 回答“何时可读、何时可复用”。三类 fence 的方向和粒度不同：

| fence | 方向与粒度 | 回答的问题 |
| --- | --- | --- |
| acquire fence | Producer → Consumer，per-buffer | Producer 的 GPU、Camera、codec 或其他硬件何时写完，Consumer 何时可安全读取 |
| release fence | Consumer/SF → Producer，per-layer、per-frame | 上一轮使用的 Buffer 何时不再被 HWC/RenderEngine 使用，可以安全复用 |
| present fence | HWC → SurfaceFlinger，per-display、per-frame | 这一轮 display present 何时越过 Android 显示栈的时间边界 |

`queueBuffer` 返回时，GPU 仍可能在写入，完成时机由 acquire fence 约束。Android 13 之后，SurfaceFlinger 在 `AutoSingleLayer` 等受限条件下可以先 latch unsignaled Buffer；读取方依旧必须遵守 acquire fence。因此，“latch 已发生”和“Buffer 已可读”是两个判断。

present fence 描述一次 display present，release fence 描述某个 Layer 的 Buffer 何时可复用。混合页面上即使多个 Layer 共享同一个 present fence 时间边界，也不能据此断定其中某一个 Layer 延迟归还；需要继续核对该 Layer 的 release fence 与下一次 dequeue。

### 用队列状态解释等待

Producer 的典型周转顺序是 `dequeueBuffer → 写入 → queueBuffer`，Consumer 的典型顺序是 `acquireBuffer → 使用 → releaseBuffer`。分析等待时，应把动作落到具体队列：

- `dequeueBuffer` 长等：没有满足条件的可用 slot，继续查 Consumer 持有数量、release fence 和允许的 dequeued/acquired 数；
- `queueBuffer` 长等：可能涉及 callback 顺序、EGL production throttling 或 Consumer 节奏，不能直接写成“队列已满”；
- `updateTexImage` 长等：SurfaceTexture 获取/更新纹理的路径出现等待，需检查上游 Producer、acquire fence 和宿主 RenderThread；
- `BufferTX - <layerName>` 长期偏高：SF server 已收到多笔含 Buffer 的 transaction，但 latch 或 drop 没有及时消化；
- analysis 线程未及时关闭 `Image`：它可以反压 Camera 流，即使预览线程本身不忙。

不要把“增加 Buffer 数量”当作默认修复。更深的队列可能缓解短时抖动，也会增加内存占用和端到端延迟；Consumer 持有过久或 fence 过晚的问题仍然存在。

### Android 17 的 producer throttling 诊断边界

API 37 的 `Surface.isProducerThrottlingEnabled()` 可以确认 EGL/Vulkan Producer 是否启用了 queue/present 边界的 CPU 回压。默认启用时，`eglSwapBuffers()` 或 `vkQueuePresentKHR()` 可能等待前一帧 GPU 工作推进；这类等待应记录为 Producer 侧回压候选，不能直接归为 SurfaceFlinger CPU 或 BufferQueue slot 耗尽。

`Surface.setProducerThrottlingEnabled(false)` 只改变这处节流行为。它不改变 Surface 的帧率投票或 display refresh rate，也不会消除 Producer 过快时发生在 `dequeueBuffer`、首次 GLES 绘制或 `vkAcquireNextImageKHR()` 一侧的自然回压。异步模式下该设置不生效，节流保持启用。该接口适合验证等待来源；应用仍需建立正确的 Vulkan 同步，不能把 queue/present stall 当作隐含同步原语。

## Step 3：Perfetto 关键定位

### 采集前先确认数据源

一次可用于渲染归因的 trace，至少要覆盖：

- 目标 App、SurfaceFlinger、system_server 和相关媒体/Camera/引擎进程的线程调度；
- gfx、view、wm、binder、freq/idle 等常用 atrace 类别；
- FrameTimeline 与 SurfaceFlinger 数据源；
- GPU render stage/counter；HWC、DisplayHAL 或厂商显示轨迹若设备支持，也应开启；
- 需要分析 Layer transaction 时，配合 Winscope 的 WindowManager 与 SurfaceFlinger tracing。

不同 SoC 和 user/userdebug 构建暴露的 GPU、HWC slice 名称并不一致。看不到 `validateDisplay` 或 `presentDisplay` 只能说明 trace 没有该名称的事件，不能证明 HAL 没有执行相应调用。

### 必看的 Track

| Track | 关注内容 | 来源 |
| --- | --- | --- |
| App 主线程 | `Choreographer#doFrame*`、Input/Animation/Traversal/Commit | 生产起点与 UI CPU |
| RenderThread / 引擎线程 | `DrawFrame*`、树同步、dequeue/queue、EGL/Vulkan submit | CPU 命令构建与 Buffer 提交 |
| 上游 Producer | codec、Camera、Chromium、Flutter、游戏线程 | 非标准 HWUI 内容的生产节奏 |
| BufferQueue / BLAST | dequeue/queue、`BufferTX - <layerName>`、transaction | Producer/Consumer 节奏与 pending update |
| SurfaceFlinger | transaction flush、snapshot/latch、composition、RenderEngine | 系统侧 CPU/GPU 与合成策略 |
| FrameTimeline | expected/actual、surface/display token、jank type | App SurfaceFrame 与 SF DisplayFrame |
| GPU | App GPU、SF client composition、队列与频率 | CPU submit 之后的异步执行 |
| HWC / Display | validate/present、composition type、present timing | DEVICE/CLIENT 决策与显示后段 |

### 关键 Slice 速查

| 观察结果 | 它能说明什么 | 还不能说明什么 |
| --- | --- | --- |
| `Choreographer#doFrame*` 超过 expected window | 目标 App 的主线程帧工作晚 | 不能说明 GPU、SF 或 display 一定正常 |
| `DrawFrame*` 很长 | RenderThread 的 CPU 窗口或内部等待很长 | 不能把整段都算作 GPU 执行时间 |
| `dequeueBuffer` 长等 | Producer 一时拿不到可写 slot | 未确认 release fence 与 Consumer 前，不能写成 Buffer 数量不足 |
| `queueBuffer` 长等 | Producer 提交边界出现等待 | 不等价于 BufferQueue 满 |
| `updateTexImage` 长等 | 宿主采样 SurfaceTexture 时等待 | 需继续区分上游晚产出、acquire fence 或调用位置 |
| transaction 已到、BufferTX 积压 | SF server 已收到 Buffer update | 不能证明 Buffer 已 latch 或已 present |
| latch 已发生 | SF 已采纳该 Buffer 状态 | Android 13+ 受限场景可 latch unsignaled，不能据此证明写入完成 |
| SF actual 很长 | App 帧关联的系统显示区间偏长 | 不能把全部 duration 都归因于 SF 主线程 CPU |
| `CLIENT` composition 增多 | 更多 Layer 由 RenderEngine 生成 client target | 不能只凭一次结果断言某个 UI 属性是原因 |

Slice 名称会随版本、trace 配置和厂商实现变化。应先从 Track 与调用上下文确认语义，再使用名称筛选；不要把 `latchBuffer`、`validateDisplay` 等名字当作所有设备都必须出现的稳定 ABI。

### 按一帧复原证据

对一个明确的异常帧，建议按以下顺序复原：

1. 用 package/PID、Layer 和 surface frame token 锁定 App SurfaceFrame；
2. 找到对应 `Choreographer#doFrame*` 或引擎起帧点；
3. 追踪 RenderThread/引擎线程的 dequeue、GPU submit、queue；
4. 确认 BLAST/SurfaceControl transaction 到达 SF 的时刻和 `BufferTX` 变化；
5. 检查 transaction readiness、acquire fence、latch 或 drop；
6. 对齐 SF DisplayFrame、RenderEngine/HWC 工作与 present timing；
7. 回看上一帧 release fence，确认它是否反压了下一帧的 dequeue。

这条顺序能把相邻帧的相互影响纳入分析。很多 `dequeueBuffer` 等待来自上一轮 Buffer 归还过晚，只盯当前帧会漏掉起因。

FrameTimeline 中，App actual slice 的结束时间取 CPU post 与 GPU 完成的较晚者；SF actual slice 覆盖 SurfaceFlinger 主循环起点到显示更新，并包含 Composer/DisplayHAL 阶段。两者的 duration 口径不同，不能把 SF actual 的全部时间记到 SurfaceFlinger 主线程 CPU。

### SQL 诊断速查

下面的查询用于从 trace 中缩小候选时间窗。Slice 名称需要根据设备上的实际轨迹调整，查询结果也必须回到 UI 中核对调用上下文。第二段中的 5 ms 只是候选过滤值，应按本次场景的 expected window 与采集目的替换，不能用作通用 jank 阈值。

```sql
-- 1. 找目标进程内最耗时的 doFrame
SELECT
  p.name AS process_name,
  s.ts,
  s.dur,
  s.name
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t USING (utid)
JOIN process p USING (upid)
WHERE s.name GLOB 'Choreographer#doFrame*'
  AND p.name = 'com.example.app'
ORDER BY s.dur DESC
LIMIT 10;

-- 2. 用可替换的候选阈值筛选 Buffer 提交/获取
WITH params(min_candidate_ns) AS (VALUES (5000000))
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  s.name,
  s.ts,
  s.dur
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t USING (utid)
JOIN process p USING (upid)
JOIN params
WHERE p.name = 'com.example.app'
  AND (
    s.name GLOB '*dequeueBuffer*'
    OR s.name GLOB '*queueBuffer*'
  )
  AND s.dur > params.min_candidate_ns
ORDER BY s.dur DESC;

-- 3. Android 12+：按进程与 surface token 对齐 expected/actual
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  p.name AS process_name,
  a.layer_name,
  a.surface_frame_token,
  a.display_frame_token,
  e.ts AS expected_ts,
  e.dur AS expected_dur,
  a.ts AS actual_ts,
  a.dur AS actual_dur,
  a.jank_type,
  a.present_type,
  a.on_time_finish
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

Android 12+ 可以从 FrameTimeline 切入，但 `actual_frame_timeline_slice` 同时包含 App SurfaceFrame 与 SurfaceFlinger DisplayFrame：SF 行的 `surface_frame_token` 为 `0`，同一个非零 token 也可能因多个 Surface/Layer 出现多行。示例先按目标进程排除 SF 行，再使用 `layer_name` 与 surface token 连接 expected/actual；统计任务还应按分析目的处理一对多关系，不能只按 token 粗略去重。

官方 FrameTimeline 当前不支持 `SurfaceView`。Camera、Video、游戏等独立 Surface 也可能缺少与宿主窗口同等完整的 App 时间线，此时要回到 Producer、BufferQueue、Layer、fence 和 present 证据。Android 9—11 没有当前 FrameTimeline 主表，应使用对应版本可用的 `doFrame`、VSYNC、BufferQueue 与 SurfaceFlinger 轨迹复原时间窗。

## Step 4：常见瓶颈模式

### 瓶颈证据对照表

| 模式 | 主要证据 | 容易误判的点 | 修复方向 |
| --- | --- | --- | --- |
| 主线程 CPU 超预算 | App actual 晚；`doFrame` 内 Input/Animation/Traversal/Commit 占用明确 | 长 `doFrame` 不等于每次都 miss 当前动态 deadline | 缩短同步 IO、布局/绘制重算和帧内业务 |
| RenderThread CPU 重 | `DrawFrame` 的 CPU 子段长，GPU 尚未成为主导 | `DrawFrame` 墙钟时间可能包含等待 | 减少 DisplayList/资源准备、纹理上传和复杂效果 |
| App GPU 晚完成 | CPU submit 不晚，acquire fence/GPU render stage 晚 | `queueBuffer` 返回不能代表 GPU 完成 | 降低 shader、overdraw、离屏 pass、带宽与纹理压力 |
| Buffer 回压 | `dequeueBuffer` 等待，上一帧 release fence 或 Consumer 归还晚 | 盲目增加 Buffer 会提高延迟 | 找出持有者，缩短 Consumer 使用与归还时间 |
| Producer 供帧抖动 | codec/Camera/引擎 queue cadence 不稳，目标 Layer 没有及时更新 | SF 复用旧 Buffer 不代表 SF 自身卡住 | 修复上游调度、解码、Camera stream 或引擎 pacing |
| SF CPU/GPU 超预算 | SF actual/jank type、commit/composite、RenderEngine GPU 证据一致 | SF actual 包含 Composer/DisplayHAL 时间 | 区分 transaction、Layer 数量、client composition 与 GPU 完成 |
| HWC/overlay 路径变化 | composition type、client target、GPU 与功耗同时变化 | `SurfaceView` 只具备独立 Layer 条件，不保证 DEVICE | 依据 HWC 能力检查格式、blend、transform、dataspace、plane |
| 显示输出延迟 | App、latch、composition 按时，present/DisplayHAL 晚 | framework trace 不覆盖 panel 光学响应 | 查模式切换、HWC/driver、DRM/KMS 与厂商显示轨迹 |
| VRR/帧率口径错误 | 内容帧率、render rate、refresh rate 不一致 | 固定 16.6 ms 阈值不适合所有模式 | 用 expected/actual timeline 和实际刷新模式判断 |

Android 17 的合成决策可以沿源码中的 `chooseCompositionStrategy()` → `getDeviceCompositionChanges()` → `applyCompositionStrategy()` 追踪。出现 client composition 时，RenderEngine 生成 client target，再由 `setClientTarget()` 交给 HWC；输出阶段通过 `presentAndGetReleaseFences()` 取得 display present fence 和各 Layer 的 release fence。HWC 能否保留 `DEVICE` 还受 plane 数量、Buffer 格式、缩放/旋转、alpha/blend、受保护内容、HDR/dataspace 及厂商硬件限制影响。

### 帧率、延迟、功耗要分开

三个指标彼此影响，但不能互相替代：

- **帧率/吞吐**：单位时间产生和显示多少帧，关注 cadence、deadline miss 与稳定性；
- **端到端延迟**：从输入或内容 ready 到对应 present 的时间，队列更深时帧率可能稳定，延迟仍会上升；
- **功耗**：CPU/GPU 频率、内存带宽、重复采样、client composition、overlay 和刷新率共同决定。

例如，将视频从可用的 device composition 路径变成 TextureView 宿主采样，画面可能仍保持 60 fps，但 App GPU、SF client composition 或内存带宽成本可能上升。反过来，增加队列深度可能减少短时卡顿，却让触控或 Camera 预览更“跟手慢”。优化前应写清本次优先级，不能只看平均 FPS。

### 跨路径互相影响

页面里同时存在 WebView、SurfaceView、宿主 UI 与动画时，可从共享资源判断干扰位置：

- 内容并入同一个宿主窗口：共享主线程、RenderThread、App GPU 和宿主 BufferQueue 预算；
- 多个独立 Layer：共享 SurfaceFlinger 帧预算、HWC plane、显示带宽与 present；
- Camera/Video/游戏 Producer：可能共享 GPU、内存带宽、codec/ISP 或调度资源；
- 任一可见内容提交帧率意图，都可能影响 display mode 选择与其他内容的显示节奏。

看到两条路径同窗变慢时，应先找它们共享的资源，再判断谁是负载来源、谁只是受害者。

## 两个复盘案例

### 案例 1：浮层动画期间视频层从 DEVICE 变为 CLIENT

假设现场是：视频详情页静止播放时功耗正常，浮层动画出现后 GPU 和内存带宽同时上升，视频 Layer 的 composition type 也从 `DEVICE` 变为 `CLIENT`。`SurfaceView` 让视频具备独立 Layer 条件，但 HWC 是否选择 `DEVICE` 由设备能力和本帧 Layer 属性共同决定。alpha 只是待验证候选，不能预先写成根因。

复盘步骤如下：

1. 用 Layer 树确认视频是独立 Layer，并记录动画前后的 crop、transform、alpha、dataspace、Z-order；
2. 确认 Producer 是 MediaCodec，视频 Buffer 没有先被 App 采样进宿主窗口；
3. 对齐两段 trace 中的 composition type、RenderEngine/client target、GPU 负载和 present；
4. 一次只移除一个候选属性，再重复相同播放片段；
5. 只有当受控实验稳定复现“属性变化 → composition type 变化 → RenderEngine/GPU 与功耗变化”时，才能把该属性写成这台设备上的回退触发条件。

Alpha、圆角、blur、缩放、旋转、格式、dataspace、受保护内容和 overlay plane 数量都可能影响 HWC 决策，不同设备支持范围不同。删掉某个效果后恢复 `DEVICE` 只能证明该设备、该场景下存在关联，不能推广为 Android 17 的统一规则。

### 案例 2：WebView 滚动卡顿，宿主窗口帧出现超时

假设现场是：页面滚动时宿主窗口 miss deadline，主线程的 RecyclerView 工作不重，RenderThread 的 WebView functor 相关区间却持续变长。标准硬件 WebView 默认通过 functor/DrawFn 进入宿主 HWUI DisplayList；宿主 RenderThread 执行到该节点时，会进入 Chromium `AwDrawFnImpl::DrawGL()` 或 `DrawVk()`。SurfaceFlinger 主要看到宿主窗口 Layer，而不是一条单独的网页 Layer；视频等内容仍可能使用独立 Surface。

复盘步骤如下：

1. 从 Layer 树确认网页内容并入宿主窗口，还是另有 child Surface；不能只因页面里有 WebView 就预设 functor 路径；
2. 若内容并入宿主窗口，按 surface token 对齐宿主 `doFrame`、`DrawFrame`、`WebViewFunctor::draw*`、`DrawFn_Draw*`、`AwDrawFnImpl::*`、App GPU 和 queue；
3. 记录 WebView provider 版本，同窗查看 Chromium renderer/compositor/Viz 的线程与 Running、Runnable、Sleeping、阻塞状态；线程名和合并方式会随 provider 版本变化；
4. 区分宿主 RenderThread 在等待网页内容、执行 functor CPU 工作，还是提交后的 GPU 工作过晚；
5. 用固定 WebView provider、固定页面和固定输入脚本做前后对比，再评估 DOM/Canvas 复杂度、资源上传或 provider 回归。

宿主窗口 FrameTimeline 不提供独立的网页 frame id。若需要把 Chromium 内容帧精确对应到宿主帧，还要采集 Chromium 内部 frame id；若现场存在独立子 Surface，则要单独追踪该 Layer 的 Buffer transaction、fence、SF/HWC 与 present。第 18.13 节给出 WebView 各分支的源码边界。

## 常用 dumpsys 命令速查

下面的命令用于建立快照。长时间序列、Layer transaction 和帧级归因仍需 Perfetto/Winscope。

```bash
adb shell dumpsys SurfaceFlinger --list
adb shell dumpsys SurfaceFlinger --latency "<LayerName>"
adb shell dumpsys SurfaceFlinger > /data/local/tmp/sf.txt
adb pull /data/local/tmp/sf.txt .
adb shell dumpsys gfxinfo <package> framestats
```

- `SurfaceFlinger --list`：确认 Layer 名称，给 Perfetto 和 Winscope 找目标。
- 完整 `SurfaceFlinger` dump：补充 Buffer、transform、parent-child 等当前状态；具体字段随版本和厂商变化。
- `--latency`：查看该接口可提供的历史时间戳，不替代 composition 或 fence 判定。
- `gfxinfo framestats`：只覆盖 App 侧 UI 帧预算，不能替代 SurfaceFlinger / HWC 证据。

## 渲染路径选型决策树

选型应从“内容由谁生产、是否需要独立 Layer、是否要被宿主采样、Buffer 归谁所有”出发。下面的树用于缩小候选方案，不构成 HWC 或性能保证。

```text
内容是否属于普通 Android UI？
├── 是：View / Compose → HWUI → 宿主窗口
└── 否：上游是否可以直接向 Surface 生产 Buffer？
    ├── 是：是否需要独立 Layer、受保护内容或避免宿主二次采样？
    │   ├── 是：SurfaceView / Surface / ANativeWindow
    │   └── 否：是否必须跟随宿主做任意纹理效果？
    │       ├── 是：TextureView（接受宿主采样与合成成本）
    │       └── 否：独立 Surface 仍是候选，实测 HWC 与交互行为
    └── 否：是否要把 RenderNode 输出到调用方自管 HardwareBuffer？
        ├── 是：HardwareBufferRenderer
        │       └── 若需送显，再由调用方通过 SurfaceControl 等提交
        └── 否：继续确认框架自己的宿主/子 Surface 路径

WebView / Flutter / 游戏等框架
└── 不按框架名预设路径
    ├── 查实际宿主 View 与 child Surface
    ├── 查引擎/renderer 的 Producer 线程
    └── 查 BufferQueue、Layer、fence 与 HWC 结果
```

`SurfaceView` 的独立 Layer 有利于视频、Camera、游戏与受保护内容，但 `DEVICE` composition、低功耗和低延迟都要由实测证明。`TextureView` 提供宿主窗口内的纹理采样能力，代价通常包括一次额外采样和宿主 GPU 工作。`HardwareBufferRenderer` 是 `RenderNode → HardwareBuffer` 的异步渲染工具，不是 `TextureView` 或 `SurfaceView` 的直接替代品。

## 复核清单

完成一次渲染问题复盘前，逐项确认：

- [ ] 已锁定 package/PID、display、Window、Layer、BufferQueue 和复现时间窗；
- [ ] 已画出 Producer、第一 Consumer、SF Layer 与送显路径；
- [ ] 已区分 acquire、release、present fence；
- [ ] 已用 token 或明确时序把 App SurfaceFrame 与 SF DisplayFrame 对齐；
- [ ] 已区分 CPU wall time、GPU execution 与 fence wait；
- [ ] 已检查上一帧归还是否反压当前帧；
- [ ] 已区分 queue/present CPU throttling 与 dequeue/acquire 自然回压；
- [ ] 已说明 FrameTimeline、GPU/HWC 轨迹缺失时的证据边界；
- [ ] 已将 `DEVICE`/`CLIENT` 结果写成设备现场结论，而非平台保证；
- [ ] 已区分帧率、端到端延迟与功耗；
- [ ] 修复前后使用相同设备、场景、输入和采集配置。

## 章节交叉引用表

| 现场 | 先看章节 |
| --- | --- |
| RecyclerView 滑动卡顿 | 18.2 + 7.8 |
| SurfaceView 视频黑屏 / 闪烁 | 18.6 + 18.15 |
| TextureView 功耗高 | 18.7 |
| WebView 页面拖慢宿主窗口 | 18.13 + 22.7 |
| Camera 预览掉帧 | 18.14 + 14.9 |
| Flutter 嵌入原生 View 性能差 | 18.12 |
| 游戏帧率不稳 | 18.16 |
| PiP Resize 黑边 | 18.18 |
| VRR 设备误报掉帧 | 18.19 |
| Overlay 失效 | 18.15 |
| 离屏渲染性能差 | 18.17 |

## 与其他章节的关系

- **18.1 渲染分类与选择章节**：用于在开分析前选对路径。
- **13.5 Perfetto 专题解读**：用于补 SQL、时间窗和轨道操作细节。
- **15.1 性能优化的术、道、器**：用于把局部 trace 结论放回整体诊断流程。
- **18.13 / 18.14 / 18.15**：对应 WebView、Camera、Overlay 三类高频复盘现场。

## 参考资料

- Android Graphics Architecture: <https://source.android.com/docs/core/graphics/architecture>
- Android Graphics BufferQueue and Gralloc: <https://source.android.com/docs/core/graphics/arch-bq-gralloc>
- Android Synchronization Framework: <https://source.android.com/docs/core/graphics/sync>
- SurfaceFlinger and WindowManager: <https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager>
- Unsignaled Buffer Latching: <https://source.android.com/docs/core/graphics/unsignaled-buffer-latch>
- Perfetto Trace Processor: <https://perfetto.dev/docs/analysis/trace-processor>
- PerfettoSQL Standard Library: <https://perfetto.dev/docs/analysis/stdlib-docs>
- Perfetto FrameTimeline: <https://perfetto.dev/docs/data-sources/frametimeline>
- Android Developers, `SurfaceView`: <https://developer.android.com/reference/android/view/SurfaceView>
- Android Developers, [`Surface`](https://developer.android.com/reference/android/view/Surface)
- AOSP Android 17, [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp) 与 [`WebViewFunctor.h`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h)
- AOSP Android 17, [`Surface.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Surface.java)、[`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp) 与 [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- AOSP Android 17, [`LayerLifecycleManager.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/LayerLifecycleManager.cpp) 与 [`LayerSnapshotBuilder.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/LayerSnapshotBuilder.cpp)
- AOSP Android 17, CompositionEngine [`Output.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp)、[`Display.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Display.cpp) 与 [`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)
- Kernel common `android17-6.18-2026-06_r6`, [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)、[`drm_vblank.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c) 与 [`sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c)
