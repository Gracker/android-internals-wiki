---
title: "Android 17 游戏引擎渲染链路"
chapter: "18.16"
section: "18.16"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: ["Unity", "Unreal", "Game-Engine", "Swappy", "Frame-Pacing", "Vulkan", "GLES", "渲染链路"]
related_chapters: ["2.4", "2.5", "5.9", "18.6", "18.8", "18.9", "18.15", "18.18", "18.20", "18.21"]
consolidated_from:
  - "src/part2-performance/ch08-responsiveness/09-game-performance.md"
created_by: "rendering-pipelines-merge"
created_date: "2026-04-09"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-31"
task6_result: pass-light-edit
task2b_result: fixed-lite
task9_reviewed_date: '2026-04-22'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-04-22T20:50:00+08:00'
last_task2b_lite_at: "2026-05-31"
repaired_date: "2026-04-26"
repaired_by: openclaw-task2b
last_task9_audit: "2026-06-11"
last_task6_audit: "2026-06-13"
last_task6_at: "2026-05-31T08:08:00+08:00"
last_task6_reviewed_by: openclaw-task6
last_task9_audit_log: "logs/deep-review/2026-06-11-10-audit.md"
last_task9_autofix_at: "2026-06-11"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-26
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1 (SurfaceView.java, Surface.java, PerformanceHintManager.java, GameManager.java, GameState.java, TextureView.java, HardwareRenderer.java, TextureLayer.java, DeferredLayerUpdater.cpp, DrawFrameTask.cpp, swapchain.cpp, Surface.cpp, SurfaceFlinger.cpp, HWComposer.cpp, Display.cpp, Output.cpp, OutputLayer.cpp, AidlComposerHal.cpp, Mode.aidl) / AGDK Frame Pacing, Frame Rate, ADPF, Game Mode, Game State, OpenXR 1.1 docs / kernel android17-6.18-2026-06_r6 (dma-buf.c, dma-fence.c, dma-fence.h, sync_file.c)"
confidence: medium
last_idle_audit_at: "2026-07-27T22:35:52+08:00"
last_idle_audit_run_id: "20260727-223552-idle-audit-6c95044a"
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S13_game_type.md"
    role: "游戏线程、pacing、ADPF、SurfaceFlinger、Perfetto 与版本边界"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_architecture/source.md"
    role: "Native 游戏、小游戏、云游戏、AR 与 XR 生产者分类"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_native_engine_pipeline/source.md"
    role: "Android 17 Vulkan WSI、BufferQueue 与显示尾链"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_android_display_pipeline/source.md"
    role: "CompositionEngine、Composer HAL、present fence 与 release fence"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_mini_game_pipeline/source.md"
    role: "小游戏独立 Surface 与 TextureView 宿主回接分支"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_cloud_game_pipeline/source.md"
    role: "云游戏输入上行、视频下行与本地输出承载"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_ar_pipeline/source.md"
    role: "Camera、IMU、VIO、pose 与显示时间戳边界"
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S13_game_xr_pipeline/source.md"
    role: "OpenXR frame loop、runtime swapchain 与 compositor 边界"
  - type: official
    path: "https://developer.android.com/games/agdk/game-activity"
    role: "GameActivity 的 SurfaceView 承载与 C/C++ 生命周期"
  - type: official
    path: "https://developer.android.com/reference/games/game-activity/struct/game-activity-callbacks"
    role: "ANativeWindow 创建、变更与销毁回调契约"
  - type: official
    path: "https://developer.android.com/games/sdk/frame-pacing"
    role: "Swappy、queue-stuffing、presentation timestamp 与 pipeline mode"
  - type: official
    path: "https://developer.android.com/games/sdk/reference/frame-pacing/group/swappy-vk"
    role: "Swappy Vulkan 初始化、swap interval 与 queuePresent API"
  - type: official
    path: "https://developer.android.com/games/develop/vulkan/frame-pacing-extensions"
    role: "Android 17 VK_EXT_present_timing 与前置能力"
  - type: official
    path: "https://developer.android.com/games/develop/vulkan/native-engine-support"
    role: "Vulkan swapchain、显式同步与阻塞行为边界"
  - type: official
    path: "https://developer.android.com/reference/android/view/Surface"
    role: "Frame Rate compatibility 与 API 37 producer throttling"
  - type: official
    path: "https://developer.android.com/media/optimize/performance/frame-rate"
    role: "游戏 DEFAULT、视频 FIXED_SOURCE 与刷新率 vote"
  - type: official
    path: "https://developer.android.com/games/optimize/display-refresh-rate-change"
    role: "Android 15 以后游戏显式请求高刷新率"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf"
    role: "ADPF 持续性能与自适应质量控制"
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager.Session"
    role: "Hint Session 线程、target、actual work 与能效偏好"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api"
    role: "Game Mode 查询、用户选择与 intervention 边界"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api"
    role: "Game State 与 isLoading 开发者接口"
  - type: official
    path: "https://source.android.com/docs/core/perf/boost"
    role: "Android 13 GAME_LOADING 与 Android 14 GAME Power HAL mode"
  - type: official
    path: "https://docs.unity3d.com/Manual/profiler-markers.html"
    role: "Unity PlayerLoop、render 与 present marker 语义"
  - type: official
    path: "https://dev.epicgames.com/documentation/en-us/unreal-engine/threaded-rendering-in-unreal-engine"
    role: "Unreal Game/Rendering Thread 与跨帧关系"
  - type: official
    path: "https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-insights-in-unreal-engine"
    role: "Unreal Insights task、timing 与 trace 证据"
  - type: official
    path: "https://registry.khronos.org/OpenXR/specs/1.1-khr/html/xrspec.html"
    role: "OpenXR frame synchronization、swapchain image 与 composition layer"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceView.java"
    role: "SurfaceView 的 BLASTBufferQueue、SurfaceControl 与窗口同步"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Surface.java"
    role: "Frame Rate API 与 API 37 producer throttling"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java"
    role: "Hint Session、WorkDuration 与 power efficiency"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameManager.java"
    role: "Game Mode 与 Game State 平台入口"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameState.java"
    role: "loading 与 gameplay mode 数据结构"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/TextureView.java"
    role: "小游戏 TextureView frame available、update 与 invalidation"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java"
    role: "TextureLayer pending update 进入 RenderThread"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/TextureLayer.java"
    role: "updateSurfaceTexture 与 pushLayerUpdate"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/DeferredLayerUpdater.cpp"
    role: "SurfaceTexture 最新 AHardwareBuffer 获取与 fence"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp"
    role: "syncFrameState 应用 TextureLayer pending update"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp"
    role: "dequeue/AcquireImageANDROID、QueueSignalReleaseImageANDROID、queueBuffer 与 present timing"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp"
    role: "ANativeWindow dequeue、queue、frame rate 与 producer throttling"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp"
    role: "Layer snapshot、latch、composition 与 present 主路径"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp"
    role: "HWC validate、client target、present 与 release fence"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Display.cpp"
    role: "chooseCompositionStrategy 与 presentFrame fence 收集"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp"
    role: "RenderEngine client composition 与 client target 生产"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/OutputLayer.cpp"
    role: "游戏 Layer buffer、geometry 与 composition type 写入 HWC"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/AidlComposerHal.cpp"
    role: "Composer3 setLayerBuffer、validate 与 present 命令"
  - type: aosp
    path: "https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/aidl/android/hardware/power/Mode.aidl"
    role: "Power HAL GAME 与 GAME_LOADING mode"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c"
    role: "GPU、DPU 与 codec 跨设备共享 buffer"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c"
    role: "fence signal、callback 与 wait"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/dma-fence.h"
    role: "dma-fence 公共同步接口与语义"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c"
    role: "dma-fence 的 sync_file fd 接口"
---

# 18.16 Android 17 游戏引擎渲染链路

## 游戏渲染要从输入追到显示

普通 Android View 页面通常由事件触发：输入、动画或数据变化引起 `invalidate()`，`Choreographer` 在 VSync 节点驱动 ViewRootImpl 和 HWUI。游戏也要处理 Activity 生命周期、窗口和输入事件，但画面生产通常由引擎自己的 game loop 持续推进。

这一区别改变了性能分析的起点。普通页面常从 UI Thread 的 `doFrame()` 往后看；游戏要从“哪一次输入被哪一轮 simulation 读取”开始，继续跟踪 Render / RHI、GPU、swapchain、BufferQueue、SurfaceFlinger 和显示 present。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`，内核锚点为 `android17-6.18-2026-06_r6`。Unity、Unreal、Cocos、自研引擎、Swappy 和 GPU driver 各有独立版本，采集数据时要把引擎版本、graphics API、渲染后端、frame pacing 配置、Game Mode 和设备 build fingerprint 一起记录。

## Game Loop 与事件驱动 UI 有什么不同

下面的伪代码只用于解释职责和节奏，不代表某个引擎的固定实现：

```text
while (running) {
    pollLifecycleAndInput();

    accumulator += elapsedTime();
    while (accumulator >= fixedStep) {
        simulatePhysicsAndGameplay(fixedStep);
        accumulator -= fixedStep;
    }

    buildRenderSnapshot(accumulator / fixedStep);
    recordAndSubmitGpuCommands();
    presentWithFramePacing();
}
```

很多引擎用固定步长更新物理，用可变步长或插值生成渲染快照。输入也可能在 game thread 开头、VSync 附近或更靠近提交时采样。只知道“游戏 60 FPS”无法推出 simulation 每秒运行 60 次，更无法推出触控到显示只有一帧延迟。

| 对比维度 | 普通 View 页面 | 游戏引擎 |
| --- | --- | --- |
| 主要驱动力 | View 失效、输入、动画、数据变化 | 自有 game loop 持续执行 |
| 逻辑更新 | UI Thread 上的回调与状态更新 | Game / Logic thread 的 simulation、脚本、物理、动画 |
| 渲染准备 | HWUI 在 UI Thread / RenderThread 协作 | Render / RHI thread、task workers、引擎 render graph |
| 提交接口 | HWUI 通过 Skia / RenderThread 输出 | GLES `eglSwapBuffers()` 或 Vulkan `vkQueuePresentKHR()` |
| 节奏控制 | Choreographer 与系统帧调度 | Swappy、自研 pacer、引擎 limiter、Frame Rate API |
| 核心延迟 | 输入到 App FrameTimeline | 输入采样到对应游戏帧 present 的完整链路 |

游戏仍然生活在 Android 窗口系统里。自有 game loop 不会绕开 SurfaceFlinger，也不能用阻塞的 swap/present 代替完整的线程和 GPU 同步设计。

## 一帧的完整路径

下面的图用于把 CPU、GPU 和显示端放进同一条时间线：

```mermaid
flowchart TD
    Input["InputReader / InputDispatcher<br/>touch event"]
    Game["Game / Logic thread<br/>script + physics + animation"]
    Workers["Worker threads<br/>jobs + streaming + animation"]
    Render["Render thread<br/>culling + render graph + draw preparation"]
    RHI["RHI / graphics thread<br/>command recording + submit"]
    Pacer["Swappy or engine pacer<br/>target time + in-flight control"]
    API["GLES / Vulkan driver<br/>GPU queue submit"]
    GPU["GPU execution<br/>producer completion fence"]
    Swap["eglSwapBuffers / vkQueuePresentKHR"]
    BQ["ANativeWindow / BufferQueue<br/>buffer + fence"]
    SF["SurfaceFlinger<br/>snapshot + latch"]
    Compose["HWC / RenderEngine<br/>composition"]
    Driver["Composer HAL / display driver"]
    Present["display present"]

    Input --> Game
    Workers --> Game
    Game --> Render --> RHI --> Pacer --> API
    API --> GPU
    API --> Swap --> BQ
    GPU --> BQ
    BQ --> SF --> Compose --> Driver --> Present
    Present -. timing feedback .-> Pacer
    Compose -. layer release fence .-> BQ
```

CPU 提交返回时，GPU 往往还在执行。生产者 fence signal 后，SurfaceFlinger 或 HWC 才能安全读取游戏 buffer；Layer release fence 控制旧 buffer 何时能回到生产者；present timing / present fence 描述显示端的后续阶段。把三个时间都写成“渲染完成”会掩盖瓶颈位置。

### 五段职责

1. **Input 与 Game / Logic**：读取输入，更新脚本、AI、物理、动画和世界状态。
2. **Render preparation**：做可见性裁剪、LOD、render graph、draw item 与资源依赖准备。
3. **RHI / graphics submission**：把引擎命令转换成 GLES/Vulkan 调用，录制并提交 GPU command buffer。
4. **GPU 与 swapchain**：GPU 写入可呈现 image，`eglSwapBuffers()` 或 `vkQueuePresentKHR()` 把该 image 交给 Android native window。
5. **Android display**：BufferQueue、SurfaceFlinger、HWC/RenderEngine、Composer HAL 和显示驱动完成 latch、合成与 present。

这些阶段可以跨帧流水执行。Game thread 在准备 N+1 帧时，Render thread 可能处理 N 帧，GPU 仍在执行 N-1 帧。吞吐量会提高，输入也可能多等一到两轮。分析时要同时记录“每秒完成多少帧”和“同一输入经历了多少个 in-flight frame”。

## 多线程架构：职责比线程名更可靠

引擎会按版本、graphics job、渲染后端和构建选项改变线程数量。先按职责识别，再用线程名辅助确认：

| 角色 | 常见工作 | 过载或阻塞时的表现 |
| --- | --- | --- |
| Game / Logic thread | input、script、physics、animation、world tick | GPU 队列出现空洞，Render thread 等新命令 |
| Render thread | culling、draw preparation、render graph | Game thread 可能在帧边界等 Render thread |
| RHI / graphics thread | API command、driver 调用、queue submit | CPU submit 晚，GPU 开工也晚 |
| Worker threads | jobs、animation、visibility、streaming | 主线程在 barrier / future 等 worker |
| GPU queue | vertex、fragment、compute、copy | producer fence 晚，swapchain image 回收慢 |
| SurfaceFlinger / display | latch、composition、present | buffer 已 ready，仍错过目标 present |

### Unity 的典型结构与证据边界

Unity 的 main thread 运行 `PlayerLoop`，脚本 `Update` / `FixedUpdate` / `LateUpdate` 等工作位于其下。启用多线程渲染后，render thread 处理图形命令；Job System worker 处理可并行任务。

Unity Profiler 中常用的 marker 包括：

- `PlayerLoop`：播放器主循环；
- `Gfx.ProcessCommands`：render thread 处理图形命令；
- `Gfx.WaitForCommands`：render thread 等 main thread 产生新命令；
- `Gfx.PresentFrame` / `Gfx.WaitForPresentOnGfxThread`：present、VSync、GPU 或队列等待相关区间；旧版本可能使用较短的 `Gfx.WaitForPresent` 名称；
- Job worker 上的任务与 idle 区间。

这些是 Unity Profiler marker，不能假定系统 Perfetto 默认会完整显示。Perfetto 至少能看到进程、Linux 线程、调度状态、futex、binder、图形和 GPU/SurfaceFlinger 信息；要把 Unity 内部阶段与系统帧准确对应，应同时采 Unity Profiler，或在关键阶段加 `ATrace` / Perfetto TrackEvent，并携带统一 frame id。

`Gfx.WaitForPresentOnGfxThread` 也不能单独证明 GPU bound。等待可能来自 VSync、frame pacer、swapchain back-pressure 或 GPU；要结合 GPU 完成时间和 BufferQueue 深度判断。

### Unreal 的典型结构与证据边界

Unreal 常见 Game Thread、Rendering Thread、可选 RHI Thread 与 Task Graph workers。Epic 的线程渲染文档明确说明 Rendering Thread 可能落后 Game Thread 一到两帧，Game Thread 会在帧边界限制这种领先距离。

Perfetto 中常能按 OS 线程名找到 Game、Render、RHI 和 worker 轨道，但名字会受引擎版本、平台封装和 Linux 线程名长度影响。`GameThread::Tick`、render pass、RHI command 等细节属于 Unreal 的引擎 trace 语义，完整证据通常来自 Unreal Insights 的 `.utrace`。推荐同时保留：

- Perfetto：系统调度、频率、GPU、BufferQueue、SurfaceFlinger 和 display；
- Unreal Insights：引擎 task、Game/Render/RHI dependency、asset loading 和自定义事件；
- 统一帧号：把同一 frame id 写入两边的自定义 marker。

### 线程等待怎样解读

等待本身没有好坏标签。Render thread 等 Game thread，可能说明逻辑慢；Game thread 等 Render thread，可能说明渲染准备积压；Swappy 或 acquire 上的短等待，可能是在主动限制 in-flight 深度。需要看等待对象、前驱 fence、目标帧率和下一段是否按预算启动。

## 游戏 Surface、SurfaceView 与 BLAST

大多数 Android 游戏把最终画面输出到独立 Surface。常见入口有：

- `GameActivity`：官方文档说明它渲染到 `SurfaceView`，并把 `ANativeWindow` 生命周期回调给 C/C++；
- Unity / Unreal 的 Android Player Activity：通常持有供引擎渲染的 Surface 或 native window，具体封装随版本变化；
- 自研 Native 游戏：从 `SurfaceView`、`NativeActivity` 或 `GameActivity` 获得 `ANativeWindow`。

这也是“游戏普遍使用 SurfaceView + BLAST”的准确含义：现代 Android 上常见的独立 `SurfaceView` 生产链会由 BLASTBufferQueue 与 SurfaceControl 事务管理。它不是所有引擎的 API 保证，也不表示引擎直接调用 BLAST。

### Android 17 的 SurfaceView 路径

`android-17.0.0_r1` 的 `SurfaceView.java` 直接持有 `BLASTBufferQueue`、`mBlastSurfaceControl` 和 `SurfaceControl.Transaction`。创建、resize、destination frame、crop、z-order 与窗口同步都在这套 SurfaceControl/BLAST 路径里处理。

稳态游戏帧仍由引擎通过 `ANativeWindow` 生产。以 Vulkan 为例，Android 17 的 `vulkan/libvulkan/swapchain.cpp` 会：

- 用 native window 查询 `NATIVE_WINDOW_MIN_UNDEQUEUED_BUFFERS` 等能力；
- 按 swapchain 配置设置 buffer format、dimensions、dataspace 和 transform；
- 在 acquire 路径调用 `dequeueBuffer()`；
- 在 present 路径把 GPU release fence 随 `queueBuffer()` 交给 BufferQueue。

acquire 的同步桥还要再看一层：`vkAcquireNextImageKHR()` 对应的实现从 `dequeueBuffer()` 取得 `ANativeWindowBuffer` 和 native fence fd，随后调用 driver 的 `AcquireImageANDROID()`，把该 fd 接到应用传入的 Vulkan semaphore / fence。应用只有在 acquire 同步对象满足后才能改写这块 image。

present 方向中，`vkQueuePresentKHR()` 或 `SwappyVk_queuePresent()` 最终进入 `PresentOneSwapchain()`。平台先调用 `QueueSignalReleaseImageANDROID()`，把 Vulkan wait semaphore 转换为 GPU 完成后的 sync fd，再将 buffer 和该 fd 交给 `ANativeWindow::queueBuffer()`。Vulkan swapchain image 与 Android BufferQueue buffer 因而有明确映射；present 调用进入这条路径时，该帧仍可能尚未被 SurfaceFlinger latch，更没有完成显示。

### 游戏 Layer 仍要经过 SurfaceFlinger

独立 Surface 绕开的是 App 的 HWUI RenderThread，不会绕开 SurfaceFlinger。SurfaceFlinger 仍为游戏建立 Layer snapshot，并与 HWC 协商 `CLIENT` / `DEVICE` composition。

即便游戏 Layer 被 HWC 判为 `DEVICE`，游戏场景本身已经由 GLES/Vulkan 在 GPU 中渲染完成。`DEVICE` 只减少显示合成阶段对该 Layer 的额外 GPU 采样，无法消除游戏渲染的 GPU 成本。

Android 17 的显示尾链可沿下面几组调用核对：

1. `Display::chooseCompositionStrategy()` 调用 `HWComposer::getDeviceCompositionChanges()`，由 Composer HAL 校验当前 Layer 栈并返回 composition type 或 display request 的变化。
2. `OutputLayer::writeStateToHWC()` 把游戏 Layer 的 buffer、acquire fence、几何和 composition type 写给 HWC。C++ 层入口名是 `HWC2::Layer::setBuffer()`，下层 Composer3 AIDL 命令名是 `AidlComposer::setLayerBuffer()`。
3. 存在 `CLIENT` composition 时，RenderEngine 先生成 client target，SurfaceFlinger 再通过 `HWComposer::setClientTarget()` 把它交给 HWC；`DEVICE` Layer 可由显示硬件直接读取各自 buffer。
4. `Display::presentFrame()` 调用 `presentAndGetReleaseFences()`，取得 display present fence 和各 Layer 的 release fence。

present 阶段返回的是尚可异步 signal 的 fence 对象。函数返回时间不能当作 vblank 已发生；Layer release fence 满足后，对应 producer slot 才可安全复用。present fence 与逐 Layer release fence 也不能混成一个“显示完成”时间。

### 生命周期和 resize

GameActivity 的 `onNativeWindowDestroyed` 文档要求：回调返回前，使用该 window 的其他渲染线程必须停止访问。旋转、分屏、折叠、自由窗口或 Surface 重建时，要按引擎规范停提交、等待必要的 GPU 使用结束、销毁或重建 EGLSurface/Vulkan swapchain，再使用新 window。

“旧 swapchain 继续画到已销毁 window”会表现为 `VK_ERROR_OUT_OF_DATE_KHR`、`VK_ERROR_SURFACE_LOST_KHR`、黑帧或 native crash。这个问题与 shader 或 Game thread 性能无关。

## Frame pacing：稳定间隔与低延迟要一起看

假设游戏在 60 Hz 屏幕上只能产出约 40 FPS。未经控制的提交会让某些帧停留一个刷新周期，另一些帧停留两个刷新周期，形成明显的 16.7 ms / 33.3 ms 交替。平均 FPS 可能接近目标，present-to-present 间隔仍很难看。

### Queue-stuffing 为什么会增加延迟

游戏持续按最快速度 present 时，display pipeline 的 buffer 会逐渐填满。队列没有空位后，render thread 在 acquire、swap 或 present 附近阻塞，看起来像系统自动帮游戏限速。此时输入可能已在更早的逻辑帧采样，玩家看到结果前还要等队列中的旧帧，输入延迟增加。

不能把“swap 调用阻塞”直接写成 GPU 慢。它可能由以下因素引起：

- Swappy 或引擎 pacer 主动等待目标时刻；
- swapchain image 仍被显示端使用；
- BufferQueue 已满；
- GPU producer fence 还未完成；
- resize / display mode change；
- Vulkan present mode 与 driver 行为。

### Swappy 做了什么

Swappy 是 AGDK Frame Pacing library：

- GLES 使用 `SwappyGL_swap()` 包装 `eglSwapBuffers()`；
- Vulkan 使用 `SwappyVk_queuePresent()`，它会代为调用 `vkQueuePresentKHR()`；
- 库利用 Choreographer、presentation timestamp 和 sync fence 控制 swap interval 与 pipeline mode；
- GLES 侧可使用 `EGL_ANDROID_presentation_time`，Vulkan 侧可使用 `VK_GOOGLE_display_timing` 等能力；
- 目标是避免帧过早 present 和 queue-stuffing，同时兼顾不同刷新率。

Swappy 中的 wait 可能是有意的 pacing。分析这段等待时，要检查目标 interval 是否正确、队列里有几帧、输入到 present 是否缩短。只把 wait slice 优化掉，常会把问题变回 queue-stuffing。

### Pipeline 与 non-pipeline

Pipeline mode 允许 CPU 和 GPU 跨 VSync 并行，吞吐更稳定，但可能多一轮 in-flight latency。Non-pipeline mode 适合 CPU+GPU 工作能落在一个 interval 内的轻负载场景，输入到显示延迟更低。Swappy 的 auto pipeline mode 会根据工作量调整，不能只用平均 FPS 评价模式选择。

### Choreographer 不是完整替代品

游戏可以用 Choreographer 对齐显示节拍，但回调偏移随设备而异，长帧也可能继续造成 buffer-stuffing。Swappy 在 Choreographer 之外还结合 presentation timestamp 与 fence。

Perfetto 中没有默认保证存在名为 `Swappy` 的 track。若要看到 `preWait`、`postWait`、`preSwapBuffers` 等内部边界，需要通过 Swappy tracer 回调写入 ATrace/TrackEvent。默认 trace 更适合观察 present 调用点、FrameTimeline、BufferQueue、GPU 和 SurfaceFlinger。

## Android 17 的 present timing 与 producer throttling

### `VK_EXT_present_timing`

Android 17 支持 `VK_EXT_present_timing`，自研 Vulkan pacer 可以请求 target present time，并查询 queue operations end、request dequeued、first pixel out / visible 等 present stage。它依赖 `VK_KHR_present_id2`，也要在创建 device 和 swapchain 前枚举 extension、feature 与相关 flag。

Android 17 平台的 `swapchain.cpp` 已解析 `VkPresentTimingsInfoEXT` 和 `VkPresentId2KHR`，并从 native window timestamp 填充 past presentation timing。支持 Android 17 不代表每个驱动组合都能跳过能力检查；扩展不可用时可退回 `VK_GOOGLE_display_timing` 或 Swappy。

### `Surface.setProducerThrottlingEnabled()`

API 37 新增 `Surface.setProducerThrottlingEnabled(boolean)`。默认开启时，Vulkan/EGL producer 在 queue buffer、而 consumer 仍处理上一帧的情况下会受到 CPU back-pressure，阻塞可能出现在 `eglSwapBuffers()` 或 Vulkan present 附近。

Android 17 的 API 文档建议 Vulkan 应用关闭这类隐式 throttling，并使用正确的显式同步。关闭后，生产速度超过 GPU 时，压力会自然移到 `vkAcquireNextImageKHR()` / dequeue 一侧。接入现成引擎时不要绕过引擎擅自改 Surface；应确认引擎版本已适配这项 API，且 semaphore、fence、in-flight frame 上限和 frame pacer 都有完整设计。

### 不要手工套用“二缓冲/三缓冲”结论

`BufferQueueDefs::NUM_BUFFER_SLOTS` 或 `mMaxBufferCount=64` 是 slot / 上限语义，不能推出当前稳定分配了 64 块，也不能推出应用默认只能使用两块。可 dequeue 数量、consumer 最少保留数量、async/shared mode、EGL swap behavior、Vulkan `minImageCount` 和设备实现共同决定在途 buffer。

普通应用也没有理由通过隐藏的 `Surface::setBufferCount()` 强改活动队列。Vulkan 应按 `VkSurfaceCapabilitiesKHR` 协商 swapchain image count，GLES 应交给 EGL/ANativeWindow 协议与引擎管理。低内存、resize 或模式切换时，如果需要减少 image count，应走引擎的 swapchain 重建流程，确保旧 image 和 fence 已退出使用。

## 三组系统调优 API 各管什么

Swappy、Frame Rate、ADPF 和 Game Mode 经常一起出现，职责并不相同：

| 机制 | 表达的内容 | 不负责什么 |
| --- | --- | --- |
| Swappy / engine pacer | 每帧何时提交、swap interval、in-flight 深度 | 不保证 CPU/GPU 资源，也不决定用户画质偏好 |
| Frame Rate API | Surface 希望显示系统采用什么刷新节奏 | 不是强制刷新率，也不安排每一帧的 CPU/GPU 工作 |
| Performance Hint Session | 一组周期性线程的 target / actual work duration | 不能锁核、锁频或绕过 thermal |
| Game Mode | 用户选择 PERFORMANCE / BATTERY / STANDARD 等目标 | 不规定各 OEM 必须使用同一套 intervention |
| Game State | 当前是否 loading、是否 gameplay 及业务标签 | 不等同于 Game Mode |

### ADPF Performance Hint Session

`PerformanceHintManager` 从 API 31 提供 Hint Session。正确使用要点如下：

- session 关联同一进程中一组长期存在、工作相关的线程；
- 创建时给出正数 target duration；
- 每个周期调用 `reportActualWorkDuration()`；
- 目标 FPS 或工作预算改变时调用 `updateTargetWorkDuration()`；
- API 34 可用 `setThreads()` 替换线程集合；
- API 35 可用 `WorkDuration` 报告 CPU/GPU 分量，并可用 `setPreferPowerEfficiency()` 表示这些线程可偏向能效调度；
- session 不受支持时，`createHintSession()` 可以返回 `null`。

这类 hint 帮助系统调整线程放置和 CPU 频率，不保证大核、固定频率或某个 GPU 档位。target、线程集合和 actual duration 写错时，系统得到的反馈也会失真。

持续性能还要结合 Thermal API。画质调节应分别评估 render scale、阴影、后处理、粒子、LOD 和目标 FPS，加入滞回与最短保持时间，避免热状态在阈值附近反复切换导致资源重建和 frame-time 尖峰。

### Frame Rate API

Android 11 / API 30 起，Java 可调用 `Surface.setFrameRate()`，Native 可调用 `ANativeWindow_setFrameRate()`；API 31 增加 change strategy。对游戏内容应使用 `FRAME_RATE_COMPATIBILITY_DEFAULT`，不要使用面向固定帧率视频的 `FIXED_SOURCE`，也不要使用明确不适合游戏的 `AT_LEAST`。

游戏专用的“Optimize refresh rates”页面示例传入 `FIXED_SOURCE`，但 `Surface` API 契约和通用 Frame rate 指南都明确限定：`FIXED_SOURCE` 只用于视频，游戏应传 `DEFAULT`。应以公开 API 契约和通用指南为准，不能照抄该示例。

Frame Rate API 只是投票。系统可能因 thermal、battery、其他可见 Surface 或 display mode 能力选择不同刷新率。Android 15 起，游戏默认刷新率策略更偏向 60 Hz；想要 90/120 Hz 的游戏应显式申请，并继续用 Swappy 或自研 pacer 控制提交节奏。

目标帧率改变时需要同时更新：

- display frame-rate vote；
- Swappy swap interval 或引擎 pacer；
- Performance Hint Session target duration；
- render scale / quality budget。

只更新其中一项，常会出现“屏幕 120 Hz、游戏仍按 60 FPS 提交”或“pacer 已降到 45 FPS，ADPF 还按 120 FPS 预算申请资源”的矛盾配置。

### Game Mode 与 Game State

`GameManager.getGameMode()` 从 API 31 提供 `STANDARD`、`PERFORMANCE`、`BATTERY` 和 `UNSUPPORTED`；API 34 增加 `CUSTOM`。官方要求游戏在每次 `onResume()` 重新查询，因为用户可能在暂停期间改变模式。

`PERFORMANCE` 也不是“所有质量选项拉满”。为了稳定高帧率，游戏可能需要适当降低重特效；`BATTERY` 可以降低帧率、刷新率或分辨率。OEM 还可能为未主动适配的游戏配置 Game Mode intervention。Android 13+ 的 FPS throttling intervention 只会限制帧率，不能把 60 FPS 提升到 120 FPS。

API 33 的 `GameManager.setGameState(GameState)` 用于报告 loading、`MODE_GAMEPLAY_INTERRUPTIBLE`、`MODE_GAMEPLAY_UNINTERRUPTIBLE`、`MODE_CONTENT` 等状态。`isLoading` 与 mode 是独立维度，加载也可能发生在后台。系统如何使用这些信号取决于 OEM 实现。

Power HAL mode 还要与面向用户的 Game Mode 分开。Android 13 的 `GameState.isLoading` 可经系统服务触发 `GAME_LOADING`，Android 14 起前台游戏可触发 `GAME`；Android 17 的 `Mode.aidl` 同时保留这两个枚举。它们只向 Power HAL 描述场景，具体 boost、持续时间、CPU/GPU 策略和 thermal 约束由 OEM 实现。

稳定出现 30、40、45、60 或 90 FPS 上限时，先查询 Game Mode、intervention 和 frame-rate vote，再检查引擎 limiter。不要看到固定上限就直接归因于 GPU。

### CPU/GPU headroom 进入低频控制回路

Android 16 / API 36 起，支持设备可通过 `SystemHealthManager.getCpuHeadroom()` 和 `getGpuHeadroom()` 返回 0～100 的余量估计；暂时不可计算时可能返回 `NaN`，不支持时可能抛出 `UnsupportedOperationException`。查询至少会经过同步 Binder，渲染关键线程不能直接等待。应用应读取平台给出的最小查询间隔，在独立执行器低频采样并缓存结果。

headroom 适合驱动画质控制器的趋势判断，不适合一次采样后立刻升降档。动态分辨率、阴影、后处理、simulation rate 和目标 FPS 要有滞回区间与最短保持时间；thermal headroom 仍单独采集，因为它描述热趋势，不等于当前 CPU/GPU 可用余量。

### 把用户模式、系统 intervention 与 OEM 面板拆开实验

同一场景至少保留四组变量：游戏自己的 Standard 基线、只切 Game Mode、只改 `game_overlay` intervention、最后再打开 OEM 游戏面板。每轮固定温度、亮度、刷新率、电源、场景和输入脚本，并记录游戏内部 target FPS / render scale、实际 present interval、频率、thermal 与 headroom。

`cmd game mode` 只改变用户模式；`device_config` 的 `game_overlay` 可能改变 downscale 或 FPS throttling，通常还需要重启进程。实验前保存原值，结束后恢复。若游戏已经声明自行处理某种模式，系统可能跳过相应 intervention；测试构建需要明确记录这项声明，避免把“未生效”误判成设备缺陷。

## Draw call、Batching 与 GPU 成本

每个 draw call 都会产生 CPU 侧命令准备、状态检查和 driver 成本，但“draw call 少”不自动代表 GPU 快：

- **Mesh batching**：把可合并几何放入较少的提交，减少 draw call，代价是更新、内存、culling 粒度可能变粗；
- **GPU instancing**：用一次或少量 draw 描述多个同网格/材质实例；
- **状态排序**：减少 pipeline、descriptor、texture 和 render target 切换；
- **Indirect / GPU-driven draw**：把部分可见性与提交工作移向 GPU；
- **缓存 render state**：减少 CPU 重建成本，不一定减少 draw call 数。

Unity SRP Batcher 的重点是降低兼容材质的 CPU 状态设置成本，不应简单写成“把 Mesh 合成一次 DrawCall”。Unreal Mesh Draw Commands 也包含缓存、排序和可能的 dynamic instancing，不能等同于传统静态合批。

“每帧超过 1000 draw call 就有问题”没有跨设备意义。要一起看：

- Render / RHI thread 花在 draw preparation 和 driver 的时间；
- pipeline / shader 是否在游戏过程中同步创建；
- GPU vertex、fragment、compute、texture、tile memory 和带宽；
- pass 数、阴影级联、透明 overdraw、分辨率和 MSAA；
- 降低 draw call 后 CPU、GPU 与画面质量是否得到预期变化。

CPU draw-call bound 常表现为 Render/RHI 晚、GPU 队列有空洞；fragment 或带宽 bound 常表现为 CPU 早早提交，GPU producer fence 仍然很晚。两者的优化方向不同。

## Perfetto：建立逐帧证据

### 采集前记录配置

至少记录这些变量：

- 引擎及版本、GLES/Vulkan、renderer / RHI、Swappy 或自研 pacer；
- SurfaceView / GameActivity / native window 结构；
- display refresh rate、游戏目标 FPS、frame-rate vote；
- Game Mode、intervention、充电状态、亮度和温度；
- render scale、HDR、画质档、最大 in-flight frame 数；
- 场景、相机路径、网络状态和输入脚本。

没有这些信息，同一台设备的两份 trace 也可能无法比较。

### 一次基础系统 trace

下面的命令用于采集图形、调度、频率、窗口和输入相关的基础数据：

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/game.perfetto-trace \
  -t 20s -b 256mb \
  gfx view sched freq idle am wm input binder_driver
adb pull /data/misc/perfetto-traces/game.perfetto-trace
```

GPU stage、counter 和 Vulkan API 细节依设备数据源和权限而异。Perfetto 数据不足时，用 AGI、GPU 厂商 profiler、Unity Profiler 或 Unreal Insights 补齐，不要用一个模糊的 `GPU completion` slice 推导所有 GPU 阶段。

### 连续三到五帧要标什么

| 节点 | 要找的证据 | 常见误读 |
| --- | --- | --- |
| Input | event time、dispatch、游戏采样点 | dispatch 到达等于本帧已经使用 |
| Game | tick start/end、physics、script、worker dependency | 主线程 Running 时间等于有效工作 |
| Render/RHI | draw preparation、command recording、submit | draw call 多就一定是瓶颈 |
| GPU | queue submit、job、producer fence | `vkQueueSubmit()` 返回等于 GPU 完成 |
| Swapchain | acquire、swap/present、queueBuffer、in-flight depth | 所有 wait 都是 GPU 慢 |
| SurfaceFlinger | latch、FrameTimeline、composition type | SF 沿用旧帧等于 SF 算慢 |
| Display | requested/actual present、present fence | fence 一定是精确首像素可见时刻 |

最有价值的是给同一输入和同一游戏帧分配稳定 ID，并把 ID 写入 Game、Render、submit 和 present marker。这样才能回答“这次触控对应哪一帧”，而不只是看到几条相似的周期曲线。

### Unity 与 Unreal 的 trace 组合

| 引擎 | Perfetto 默认侧重 | 引擎工具侧重 | 推荐关联方式 |
| --- | --- | --- | --- |
| Unity | OS 线程、调度、GPU/显示、SurfaceFlinger | `PlayerLoop`、script、render marker、Job System | 自定义 frame id + Unity Profiler timestamp |
| Unreal | OS 线程、调度、GPU/显示、SurfaceFlinger | Game/Render/RHI task、asset loading、render events | 自定义 frame id + `.utrace` |

不要在 Perfetto 里没看到 `PlayerLoop` 就认定 Unity main thread 没工作，也不要把一个名为 `RenderThread` 的线程自动归为 Unreal。进程包名、线程周期、调用栈、引擎 marker 和 frame id 应共同成立。

## 常见瓶颈怎样区分

### CPU bound

表现通常是 Game、Render 或 RHI 超出预算，GPU 队列出现空洞。原因包括 script、physics、animation、draw preparation、同步 shader/pipeline creation、资源上传、JNI、锁和 worker barrier。

降低分辨率对纯 CPU draw-call bound 帮助有限；降低对象数、pass、状态切换或并行任务依赖更有针对性。

### GPU bound

CPU 提交较早，GPU 长时间占满，producer fence 晚。需要用 GPU stage/counter 区分 vertex、fragment、compute、texture、overdraw、tile memory、带宽、同步 bubble 和频率限制。

动态分辨率主要缓解像素与带宽成本；如果瓶颈是 vertex、compute 或同步，降低 render scale 可能几乎没有改善。

### Queue / pacing bound

acquire、swap、present 或 Swappy wait 周期性变长。继续检查 pending buffer、release fence、目标 interval、pipeline mode 和 producer throttling。主动 pacing wait 可保持低队列深度，不能按 CPU idle 一概删除。

### Display bound

游戏 buffer 已 ready，SurfaceFlinger 仍错过 latch 或显示端 present 变晚。检查 desired present、FrameTimeline、HWC `CLIENT` composition、display mode change 和 Composer / driver fence。游戏 Layer 本身 GPU 很重时，额外的 RenderEngine client composition 还会与游戏争抢 GPU 和带宽。

### 稳态 thermal bound

首分钟正常，运行十分钟后 CPU/GPU 频率、内存带宽或可用功耗预算下降，frame time 持续恶化。测试要覆盖足够长的会话，并同时记录 thermal status / headroom、频率、亮度、充电和环境温度。

平均 FPS 会掩盖长帧簇。至少统计 frame-time 分布、P90/P99、1% low、present-to-present 间隔和输入到显示延迟。

## Android 12 到 Android 17 的关键演进

| 版本 | 与游戏渲染直接相关的变化 |
| --- | --- |
| Android 12 / API 31 | Game Mode 与 Performance Hint Manager 公布；三参数 `setFrameRate()` 可带 change strategy；FrameTimeline 成为系统分析基线 |
| Android 13 / API 33 | `GameState` / `setGameState()` 与 Power HAL `GAME_LOADING` 公布；FPS throttling intervention 可在平台侧限制游戏帧率 |
| Android 14 / API 34 | `GAME_MODE_CUSTOM`、Hint Session `setThreads()` 与 Power HAL `GAME`；SurfaceView alpha 能力扩展，但 z-order 语义仍需区分 |
| Android 15 / API 35 | `WorkDuration` 和 `setPreferPowerEfficiency()`；游戏需要显式请求高于默认策略的刷新率 |
| Android 16 / API 36 | 支持设备可提供更丰富的 ARR / headroom 能力，游戏仍需按设备检查并做反馈控制 |
| Android 17 / API 37 | `VK_EXT_present_timing` 与 `Surface.setProducerThrottlingEnabled()` 提供更细的 present 反馈和 producer back-pressure 控制 |

版本升级不会改变引擎和 GPU driver 的具体线程模型。Android 17 分析仍要记录 Unity / Unreal 版本、Swappy 版本、Vulkan extension 和设备 driver。

## 小游戏、云游戏、AR 与 XR 的边界

这些场景只在本地 game loop 与显示段上复用本节方法，端到端责任边界不同：小游戏还要拆 JS/runtime、bridge 与宿主 `SurfaceView`/`TextureView`；云游戏要把云端排队、渲染、编码和网络遥测接到本地解码与 present；手机 AR 要统一 Camera、IMU/pose、render target 与 present 的时钟；头显 XR 由 OpenXR runtime/compositor 负责 predicted display、reprojection 与最终显示交接，不保证经过普通 App `queueBuffer()`。

不要在这里维护四套缩略教程。TextureView 的消费语义见 [18.7](07-textureview.md)，云游戏本地视频与 sideband 见 [18.21](21-media-codec2-tunneled-media3-abr.md)，XR runtime/compositor 见 [18.20](20-android-xr-spatial-ui-rendering.md)。进入对应专题前，先确认最终 buffer Producer、输出 carrier、时钟域和 present 责任方。

## 内核和驱动侧

Android 通用内核提供 dma-buf、dma-fence 和 sync_file，负责 buffer 共享与异步硬件依赖。GPU scheduler、devfreq、thermal、IOMMU fault、memory reclaim 和 display driver tracepoint 多由设备实现提供。

在 `android17-6.18-2026-06_r6` 中可从以下入口核对通用语义：

- `drivers/dma-buf/dma-buf.c`：buffer attachment 与跨设备共享；
- `drivers/dma-buf/dma-fence.c`、`include/linux/dma-fence.h`：GPU / HWC 等异步任务的 fence signal、callback、wait 与公共同步接口；
- `drivers/dma-buf/sync_file.c`：把 fence 封装成跨进程 fd。

vendor GPU job 长、GPU 频率低和 producer fence 晚要放在同一帧分析。仅凭 Render / RHI 线程睡眠无法判断 GPU scheduler 出了问题。

## 常见误判

### “FPS 高，输入延迟就低”

队列中可能有多帧，输入也可能很早采样。应对齐 input、frame id、in-flight depth 与 display present。

### “`vkQueueSubmit()` 返回，GPU 已完成”

提交是异步操作。要看 GPU job 和 producer fence。

### “`vkQueuePresentKHR()` 慢，说明 Vulkan driver 差”

present 附近可包含 Swappy 等待、BufferQueue back-pressure、GPU fence、resize 或 display mode change。需要沿依赖追踪。

### “Unity/Unreal 的 marker 在 Perfetto 里默认都有”

引擎 profiler、Unreal Insights 与 Perfetto 是不同数据源。未显式导出时，Perfetto 可能只显示线程和系统事件。

### “Vulkan 一定比 GLES 快”

Vulkan 把更多调度和同步责任交给引擎。性能取决于 render graph、driver、pipeline、资源管理和 workload。

### “ADPF 可以锁大核或锁频”

Hint Session 提供 target / actual workload 信息，资源决策仍由系统和 thermal 策略完成。

### “Game Mode Performance 会自动提高 FPS”

OEM 策略、画质、thermal、frame-rate vote 与引擎上限都可能限制结果。Performance mode 也可能通过降低部分画质来换稳定帧率。

### “BufferQueue 有64个slot，所以游戏要手工改成三缓冲”

64 是 slot 上限语义。swapchain image count 应通过 EGL / Vulkan 和 native window 协议协商，不应调用隐藏接口硬改活动队列。

## 与其他章节的关系

- [2.4 Choreographer](../../part1-fundamentals/ch02-rendering/04-choreographer.md)：VSync、回调与帧调度。
- [5.9 ADPF 自适应性能框架](../../part1-fundamentals/ch05-cpu-power/09-adpf.md)：Hint Session、Game Mode / State、headroom 与 thermal 反馈。
- [18.6 SurfaceView](06-surfaceview.md)：独立 Surface、BLAST 与生命周期。
- [18.8 OpenGL ES](08-opengl-es.md)：EGL window surface 和 GLES 提交。
- [18.9 Vulkan](09-vulkan-native.md)：Android Vulkan swapchain 与显式同步。
- [18.15 视频叠加与 HWC](15-video-overlay-hwc.md)：云游戏视频 carrier、CLIENT / DEVICE 与 tunneled sideband。
- [18.18 可变刷新率](18-variable-refresh-rate.md)：frame-rate vote、ARR 和 display mode。
- [18.20 Android XR 空间 UI](20-android-xr-spatial-ui-rendering.md)：OpenXR runtime、compositor 与显示边界。
- [18.21 Media Codec2 与 Tunneled Playback](21-media-codec2-tunneled-media3-abr.md)：云游戏本地视频解码和 sideband 证据。

## Android 17 源码核对清单

### 平台

- [`SurfaceView.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceView.java)、[`Surface.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Surface.java)：BLAST / SurfaceControl、Frame Rate API 与 API 37 producer throttling。
- [`PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)、[`GameManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameManager.java)、[`GameState.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/GameState.java)：Hint Session、Game Mode 与 Game State。
- [`TextureView.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/TextureView.java)、[`TextureLayer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/TextureLayer.java)、[`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)：小游戏 TextureView 的 frame available、宿主 invalidation 与 pending layer update。
- [`DeferredLayerUpdater.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/DeferredLayerUpdater.cpp)、[`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)：RenderThread 获取最新 SurfaceTexture buffer。
- [`swapchain.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp)、[`Surface.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp)：Vulkan WSI 到 ANativeWindow / BufferQueue、present timing 与 producer throttling。
- [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)、[`Display.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Display.cpp)、[`Output.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/Output.cpp)：Layer snapshot、composition strategy、RenderEngine client target 与 present。
- [`OutputLayer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/CompositionEngine/src/OutputLayer.cpp)、[`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)、[`AidlComposerHal.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/AidlComposerHal.cpp)：Layer buffer、client target、Composer3 validate / present 与 fence。
- Power HAL [`Mode.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/aidl/android/hardware/power/Mode.aidl)：`GAME` 与 `GAME_LOADING`。

### 通用内核

- [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)
- [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
- [`dma-fence.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/dma-fence.h)
- [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)

### 官方文档

- [AGDK Frame Pacing / Swappy](https://developer.android.com/games/sdk/frame-pacing)
- [Swappy Vulkan API](https://developer.android.com/games/sdk/reference/frame-pacing/group/swappy-vk)
- [Vulkan frame pacing extensions](https://developer.android.com/games/develop/vulkan/frame-pacing-extensions)
- [Vulkan native engine support](https://developer.android.com/games/develop/vulkan/native-engine-support)
- [GameActivity](https://developer.android.com/games/agdk/game-activity)
- [Frame Rate API](https://developer.android.com/media/optimize/performance/frame-rate)
- [ADPF](https://developer.android.com/games/optimize/adpf)
- [PerformanceHintManager.Session](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [Game Mode API](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api)
- [Game State API](https://developer.android.com/games/optimize/adpf/gamemode/gamestate-api)
- [Performance boost for games](https://source.android.com/docs/core/perf/boost)
- [Optimize refresh rates](https://developer.android.com/games/optimize/display-refresh-rate-change)
- [Unity Profiler markers](https://docs.unity3d.com/Manual/profiler-markers.html)
- [Unreal threaded rendering](https://dev.epicgames.com/documentation/en-us/unreal-engine/threaded-rendering-in-unreal-engine)
- [Unreal Insights](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-insights-in-unreal-engine)
- [OpenXR 1.1 specification](https://registry.khronos.org/OpenXR/specs/1.1-khr/html/xrspec.html)

## 小结

- 游戏用自有 game loop 持续推进，性能分析要从输入采样追到对应帧 present。
- Game、Render、RHI、worker 和 GPU 可以跨帧并行；吞吐提高时也要约束 in-flight latency。
- Unity Profiler、Unreal Insights 和 Perfetto 各自覆盖不同层级，统一 frame id 比猜线程名可靠。
- 游戏常使用独立 SurfaceView / GameActivity 路径；Android 17 的现代 SurfaceView 由 BLAST 和 SurfaceControl 管理，游戏 buffer 仍经 SurfaceFlinger。
- Vulkan WSI 把 acquire fence 接入 `AcquireImageANDROID`，把 GPU release fence 随 `queueBuffer()` 送入 BufferQueue；display present fence 与 Layer release fence 需要分开判读。
- Swappy 控制提交节奏和队列深度，Frame Rate API 表达刷新率意图，ADPF 报告 workload，Game Mode 表达用户目标。
- 小游戏 TextureView、云游戏视频 carrier、手机 AR 与 OpenXR runtime 各有独立的 producer 和时间戳边界。
- Android 17 新增 present timing 与 producer throttling 控制，但显式同步、extension 检查和设备验证仍由引擎负责。
- BufferQueue slot 上限不能当作当前 buffer 数量，也不应据此建议应用强改二缓冲或三缓冲。
