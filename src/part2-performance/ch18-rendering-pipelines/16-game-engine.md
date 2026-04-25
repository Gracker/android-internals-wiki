---
title: "游戏引擎渲染链路"
chapter: "18.16"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
tags: ["Unity", "Unreal", "Game-Engine", "Swappy", "Frame-Pacing", "Vulkan", "GLES", "渲染链路"]
related_chapters: ["2.5", "8.9", "18.6", "18.8", "18.9"]
created_by: "rendering-pipelines-merge"
created_date: "2026-04-09"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-04-25"
task6_result: pass-light-edit
task2b_result: fixed
task9_reviewed_date: '2026-04-22'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-04-22T20:50:00+08:00'
---

<!-- outline-start -->

**锚点（必须覆盖）：**
- 游戏引擎的 Game Loop 模型（与 App 事件驱动的区别）
- 多线程架构：Logic Thread / Render Thread / Worker Threads
- Unity 和 Unreal 的典型线程模型与 Trace 特征
- Swappy Frame Pacing 的原理与作用
- 游戏引擎几乎总是使用 SurfaceView + BLAST

**扩展（可选深入）：**
- DrawCall 合批（Batching）与 GPU 性能
- Game Mode / State API 对渲染链路的影响
- 常见游戏性能问题的诊断思路

<!-- outline-end -->

## 为什么游戏引擎的渲染链路不同于普通 App

普通 App 的渲染是事件驱动的——用户操作触发 `invalidate()`，Choreographer 在 VSync 时回调 `doFrame()`，UI 线程执行 Measure/Layout/Draw。但游戏引擎不是这样工作的：它有一个**自主运行的 Game Loop**，不管有没有用户输入，都会按照固定节奏持续更新和渲染。

游戏引擎渲染链路面临一个普通 App 不存在的问题：**如何让游戏逻辑帧率与屏幕刷新率同步**。跑 40fps 的游戏在 60Hz 屏幕上如果不做帧节奏控制，会导致部分帧显示 16ms、部分显示 33ms，视觉抖动非常明显。[已验证: Android Game SDK 文档]

## Game Loop 模型

游戏引擎通常采用双线程或三线程架构：

```mermaid
sequenceDiagram
    participant Logic as Game Logic Thread
    participant Render as Render Thread
    participant Driver as GPU Driver
    participant BBQ as BLAST Adapter
    participant SF as SurfaceFlinger

    Note over Logic: Frame N Pipeline
    
    Logic->>Logic: 1. Input / AI / Physics
    Logic->>Logic: 2. Update Transforms
    Logic->>Logic: 3. Culling (剔除不可见物体)
    Logic->>Render: CommandBuffer (DrawList)
    
    Render->>Render: 4. Batching (合批)
    Render->>Render: 5. Set Pass / Shader
    Render->>Driver: 6. DrawCall (x100~1000)
    Render->>BBQ: vkQueuePresent / eglSwap
    
    BBQ->>SF: Transaction(Buffer)
    SF->>SF: Latch & Composite
```

关键阶段：

1. **Logic Thread**：运行 C#/Lua/C++ 脚本，处理物理模拟、AI、输入、动画。产物是 DrawCall List（渲染指令列表）。
2. **Render Thread**：接收 DrawList，执行 Batching（合批减少 DrawCall），设置 Shader/Texture，提交 GPU 指令。
3. **GPU**：执行渲染指令，将结果写入 Back Buffer。
4. **Present**：通过 `eglSwapBuffers`（GLES）或 `vkQueuePresentKHR`（Vulkan）提交给 SurfaceFlinger。

## Unity 与 Unreal 的线程模型

### Unity

| 线程 | 职责 | Trace 标签 |
|:---|:---|:---|
| **UnityMain / Main** | C# 脚本，Update/LateUpdate，物理模拟 | `PlayerLoop`, `Physics.FixedUpdate` |
| **UnityGfx / Gfx** | 渲染命令提交，Batching，GPU 调度 | `Gfx.WaitForPresent`, `RenderThread` |
| **UnityJobWorker** | 多线程任务，Burst 编译任务 | `JobSystem`, `ParallelFor` |

### Unreal

| 线程 | 职责 | Trace 标签 |
|:---|:---|:---|
| **GameThread** | C++ 游戏逻辑 | `GameThread::Tick` |
| **RenderThread** | 渲染指令生成和提交 | `FRenderingThread` |
| **RHIThread** | 底层图形 API 调用（GLES/Vulkan） | `FRHICommandList::Execute` |

Unity 和 Unreal 都采用了**逻辑线程与渲染线程分离**的架构。逻辑线程产出 DrawList 后交给渲染线程，两者可以流水线化并行——逻辑线程在计算第 N+1 帧的同时，渲染线程在渲染第 N 帧。

## SurfaceView + BLAST

游戏引擎通常把画面输出到 `SurfaceView`，或 `GameActivity` 暴露的 `ANativeWindow`。共同点很稳定：游戏 Surface 独立于 App View 树，提交路径绕开 App RenderThread，SurfaceFlinger 直接消费游戏帧。

- **Android 5-10**：常见路径是 `eglSwapBuffers` / `vkQueuePresentKHR` → `BufferQueue` → `SurfaceFlinger` → `HWC`。窗口尺寸和位置变化仍按旧版 SurfaceView 机制处理，排查 resize 闪烁、几何不同步时要按 [18.6 SurfaceView 章节](06-surfaceview.md) 里的 pre-BLAST 路径去看。
- **Android 11+**：SurfaceView 更常和 `BLASTBufferQueue`、`SurfaceControl.Transaction` 一起出现。折叠、分屏、自由窗口、分辨率切换这类几何变化会经过事务同步，Buffer 与几何信息更容易在同一批次提交。对应细节见 [18.6 SurfaceView 章节](06-surfaceview.md) 的现代 SurfaceView 路径。

稳态渲染阶段，两条路径的判断方法一致：游戏线程负责生产帧，SurfaceFlinger 负责消费，App 主线程的 `doFrame()` 不是主提交流程里的提交点。

## Swappy Frame Pacing

**Swappy** 是 Google 官方的帧节奏库（属于 Android Game SDK），解决游戏引擎帧节奏控制的核心问题：

### 问题

游戏跑 40fps，屏幕 60Hz。如果不做控制：
- 帧 1：显示 16ms
- 帧 2：显示 33ms（等了一个 VSync）
- 帧 3：显示 16ms
- 视觉上严重抖动

### 解决方案

Frame Pacing library 在 present 路径里结合 Choreographer 节拍、presentation timestamp 和 sync fence 调整提交时机，目标是减少 queue stuffing，让每帧停留时间更接近目标刷新周期。[已验证: Android Game SDK Frame Pacing 文档说明使用 Choreographer、presentation timestamps、sync fences]

```mermaid
sequenceDiagram
    participant App as Game Engine
    participant Swappy as Frame Pacing
    participant GPU as GPU
    participant SF as SurfaceFlinger

    App->>Swappy: eglSwapBuffers() / SwappyVk_queuePresent()
    Swappy->>Swappy: 计算目标提交时刻
    Swappy->>GPU: 按目标时刻安排 present
    GPU->>SF: queueBuffer / vkQueuePresentKHR
    SF->>SF: FrameTimeline + 合成
```

### Vulkan 接入顺序

Vulkan 接入不能只写 `init` 和 `queuePresent` 两个调用，顺序要和设备创建过程保持一致：

1. 在创建 `VkDevice` 之前，先枚举设备扩展并调用 `SwappyVk_determineDeviceExtensions()`，把 Swappy 需要的扩展一并放进 `VkDeviceCreateInfo`。
2. 创建 `VkQueue` 后，调用 `SwappyVk_setQueueFamilyIndex(device, queue, queueFamilyIndex)`，把 present queue 对应的 queue family index 告诉 Swappy。
3. 创建 `VkSwapchainKHR` 后，调用 `SwappyVk_initAndGetRefreshCycleDuration(...)` 初始化 swapchain 级实例，再用 `SwappyVk_setSwapIntervalNS(device, swapchain, swap_ns)` 设置目标帧间隔。
4. 提交帧时，应用调用 `SwappyVk_queuePresent(queue, &presentInfo)`，由 Swappy 代为调用 `vkQueuePresentKHR()`，并在需要时向 `VkPresentInfoKHR::pNext` 插入额外结构或补充命令。
5. 销毁阶段按 swapchain / device 粒度调用 `SwappyVk_destroySwapchain()`、`SwappyVk_destroyDevice()` 释放资源。

```c
// Vulkan 最小接入顺序
SwappyVk_determineDeviceExtensions(physicalDevice,
    availableExtensionCount,
    availableExtensions,
    &requiredExtensionCount,
    requiredExtensions);

// vkCreateDevice(... requiredExtensions ...)
SwappyVk_setQueueFamilyIndex(device, presentQueue, presentQueueFamilyIndex);
SwappyVk_initAndGetRefreshCycleDuration(env, activity,
    physicalDevice, device, swapchain, &refreshDuration);
SwappyVk_setSwapIntervalNS(device, swapchain, 16666666);  // 60fps
SwappyVk_queuePresent(presentQueue, &presentInfo);        // 不再直接调用 vkQueuePresentKHR()
```

### OpenGL ES 接入顺序

OpenGL ES 仍然围绕 `eglSwapBuffers()` 接入。判断这条路径时，看 `eglSwapBuffers()` 所在渲染线程、FrameTimeline，以及 SurfaceFlinger / GPU 轨道，不要把 Vulkan 的 `SwappyVk_*` 调用模式套到 GLES 路径上。

### 在 Perfetto 中看 Swappy

Swappy 没有一个默认必然出现的 `Swappy` Track。排查时把信号分成三类更稳妥：

| 观测层级 | 默认是否可见 | 该看什么 |
|:---|:---|:---|
| 默认可见 | 通常可见 | 引擎线程上的 present 调用点，`eglSwapBuffers()`、`vkQueuePresentKHR()` 或引擎自己的 present 包装，Android 12+ 的 FrameTimeline `Expected` / `Actual`，以及 SurfaceFlinger 与 GPU 轨道 |
| 自定义埋点 | 取决于应用 | 应用调用 `SwappyVk_injectTracer()` 或同类接口后，如果在 `preWait` / `postWait` / `preSwapBuffers` / `postSwapBuffers` 回调里主动写 `ATrace` / TrackEvent，Perfetto 才会出现对应 Slice |
| 额外 graphics tracing / AGI | 需单独开启 | GPU driver queue、Vulkan present timing、更细的图形栈事件 |

### 最小 trace case

| 场景 | 期望表现 | 先查哪里 |
|:---|:---|:---|
| 60Hz 面板，同一段场景，未接 Swappy | 默认只看 present 调用点和 FrameTimeline。负载上来时，`Actual Timeline` 常会出现 16.6ms / 33.3ms 混合，重复帧偏多 | CPU 帧时间、GPU 帧时间、是否出现 queue stuffing |
| 60Hz 面板，同一段场景，接入 Swappy，目标 60fps | `Expected` 与 `Actual` 更接近 16.6ms 节奏，重复帧减少。若应用埋了 tracer，`preWait` / `postWait` 会围绕帧提交点出现 | swap interval 设置、前一帧 release 时机、是否有长 GPU slice |
| 120Hz 面板，游戏锁 60fps，Swappy `swap_ns=16666666` | FrameTimeline 表现为每两次显示刷新消费一帧，`Actual` 仍接近 16.6ms，不会去追 8.3ms | swap interval 是否写错，display mode / ARR / VRR 投票是否把游戏推到 120fps |

`Choreographer#doFrame` 只能当辅助线索。Frame Pacing library 内部会用 Choreographer 做同步，但 trace 里是否出现 `doFrame()`，取决于引擎接入方式、线程模型和采集配置。只靠 `doFrame()` 判断是否接入 Swappy，很容易误判。

**常见 Trace 表现**：

| 现象 | 可能含义 |
|:---|:---|
| `Expected Timeline` 与 `Actual Timeline` 持续错位 | 帧提交晚于目标时刻，先检查 swap interval、CPU 帧时间和 GPU 帧时间 |
| 自定义 `preWait` / `postWait` Slice 很长 | 应用确实埋了 Swappy tracer，长等待多半指向 GPU 负载高或前一帧释放太晚 |
| 只有 `vkQueuePresentKHR` / `eglSwapBuffers`，没有单独 `Swappy` Track | 这很常见，不能据此判断 Swappy 未接入 |
| 需要看到 GPU queue 与 present timing 细节 | 额外打开 graphics tracing 或用 AGI 复查 |

[已验证: Android Game SDK Frame Pacing 文档, SwappyVk API Reference 中 `SwappyVk_determineDeviceExtensions` / `SwappyVk_setQueueFamilyIndex` / `SwappyVk_queuePresent` / `SwappyVk_injectTracer` / `SwappyVk_setSwapIntervalNS`, Perfetto FrameTimeline]

## DrawCall 合批（Batching）

DrawCall 是 GPU 渲染的基本单元。每次 `glDrawElements` 或 `vkCmdDraw` 都有 CPU 开销（状态切换、驱动验证）。游戏场景中可能有上千个物体，如果不做合批，DrawCall 数量会爆炸。

**Batching 策略**：将材质（Shader + Texture）相同的物体合并成一个大 Mesh，用一次 DrawCall 画完。Unity 的 SRP Batcher 和 Unreal 的 Mesh Draw Command 合并都是这个思路。

在 Perfetto 中，如果 RenderThread 的 `DrawCall` 数量过多（>1000/帧），可能需要优化 Batching 策略。

## 在 Perfetto 中识别游戏引擎链路

| Trace 特征 | 可能的引擎 |
|:---|:---|
| `PlayerLoop`, `Physics.FixedUpdate` | Unity |
| `GameThread::Tick`, `FRenderingThread` | Unreal |
| `Expected Timeline` / `Actual Timeline` 与游戏 Surface 同步波动 | 默认可见的帧节奏信号 |
| 自定义 `preWait` / `postWait` Slice | 已接入 Swappy tracer 且应用主动埋点 |
| `vkQueueSubmit` / `eglSwapBuffers` | Vulkan / GLES 后端 |
| 密集的 `DrawCall` Slice | 游戏引擎渲染 |

**常见性能问题诊断**：

| 现象 | 可能原因 | 查看 |
|:---|:---|:---|
| 逻辑帧率低 | 物理模拟/AI 太重 | Logic Thread Track |
| 渲染帧率低 | GPU 过载或 DrawCall 过多 | RenderThread + GPU Track |
| 帧率波动 | 未接入 Swappy，帧节奏不稳 | VSync 同步情况 |
| 帧延迟高 | 呈现模式不优或 BufferQueue 阻塞 | `dequeueBuffer` 耗时 |

## 与其他章节的关系

- **8.9 游戏性能与 Game Mode API**：游戏性能优化实战
- **18.8 OpenGL ES / 18.9 Vulkan**：底层图形 API 管线
- **2.17 Frame Pacing Library**：帧节奏控制原理

## 参考资料

- Android Game SDK：Frame Pacing 官方文档（Swappy 库介绍与集成指南）  
  https://developer.android.com/games/sdk/frame-pacing
- SwappyVk API Reference（`SwappyVk_setSwapIntervalNS` / `SwappyVk_initAndGetRefreshCycleDuration` / `SwappyTracer` 等）  
  https://developer.android.com/games/sdk/reference/frame-pacing/group/swappy-vk
- SurfaceView API Reference（Android N 起位置同步，Android 14 起 arbitrary alpha）：https://developer.android.com/reference/android/view/SurfaceView
- Unity 文档：Android Player Settings — Optimized Frame Pacing 选项说明  
  https://docs.unity3d.com/Manual/class-PlayerSettingsAndroid.html
- Unreal Engine 文档：Frame Pacing for Mobile Devices（Swappy 集成与 CVars 配置）  
  https://dev.epicgames.com/documentation/en-us/unreal-engine/frame-pacing-for-mobile-devices-in-unreal-engine
