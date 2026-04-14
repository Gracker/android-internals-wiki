---
title: "渲染机制的版本演进"
chapter: "2.9"
section: "2.9"
status: ready-for-review
drafted_date: 2026-03-30
drafted_by: "openclaw-task2a"
reviewed_date: 2026-04-15
reviewed_by: openclaw-task6
applicable_versions: "Android 3.0 (API 11) ~ Android 16 (API 36)"
last_verified: "2026-03-30"
last_verified_against: "developer.android.com + source.android.com"
confidence: medium
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
sources:
  - type: official
    path: "developer.android.com/about/versions"
  - type: official
    path: "developer.android.com/about/versions/16/features"
  - type: official
    path: "source.android.com"
  - type: research
    path: "intake/research-feeds/2026-03-30-ch02-gpu-optimization.md"
  - type: research
    path: "intake/research-feeds/2026-03-30-15-arr-vsync-android15-16.md"
  - type: research
    path: "intake/research-feeds/2026-03-30-ch02-skia-surfaceflinger.md"
tags: ['frametimeline', 'vulkan', 'rendering-evolution', 'blastBufferQueue', 'hwui', 'skia', 'choreographer', 'FrameMetrics']
related_chapters: ["2.1", "2.3", "2.6", "2.10", "3.1", "8.2"]
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: pending
task2b_state: idle
---

# 渲染机制的版本演进

当我们打开 Perfetto 抓一份 Trace，看到 `RenderThread` 在主线程旁边有条不紊地执行 GPU 命令，看到 `VSYNC-app` 和 `VSYNC-sf` 的信号整齐排列——这套"主线程构建 DisplayList → RenderThread 执行 GPU 命令 → SurfaceFlinger 合成上屏"的流水线，并非一蹴而就。它经历了十多个 Android 大版本的持续重构。

理解这段演进历史，对于性能分析来说不是"课外阅读"，而是刚需：我们在 Perfetto 中看到的每一个 Track 名称、每一项 API 行为，都带着版本烙印。当我们面对一份来自 Android 12 设备的 Trace 时，如果不知道 `BLASTBufferQueue` 已经取代了旧的 `BufferQueue`，就可能对着一个不存在的概念去排查问题。

下面的梳理从硬件加速的引入开始，到 Vulkan 统一渲染堆栈为止，覆盖了我们在 Perfetto 中会遇到的每一个关键版本的渲染变化。

## 硬件加速的诞生（Android 3.0）与默认开启（Android 4.0）

### 问题的起点

Android 2.x 时代，所有 UI 绘制都依赖 CPU 完成。`Canvas` 的 `drawXXX` 操作最终走到 Skia 的软件光栅化路径，主线程承担了从 Measure/Layout/Draw 到像素生成的全部工作。这套方案在低分辨率设备上勉强够用，但随着屏幕分辨率提升和 UI 复杂度增加，CPU 很快成为瓶颈。

### Android 3.0 Honeycomb：HWUI 登场

Android 3.0（API 11，2011 年）引入了基于 OpenGL ES 2.0 的硬件加速渲染管线 **HWUI**。这是 Android 首次将 GPU 引入 UI 渲染管线，从此 CPU 不再是唯一的渲染路径。

HWUI 带来了三个核心概念：

1. **DisplayList（后更名为 RenderNode）**：将 `View` 的绘制操作录制为一份命令列表，而非直接执行。当一个 `View` 只有位置变化（平移、旋转、缩放）时，无需重新录制所有 draw 命令，只需修改变换矩阵即可。这在 Perfetto 中体现为：同一个 `View` 的连续帧，主线程 `draw` 阶段的耗时会明显减少——因为只需修改矩阵参数，跳过了整个命令录制过程。

2. **硬件层（Hardware Layer）**：将复杂的 `View` 内容缓存为 GPU 纹理，后续帧只需做纹理合成，不再重复光栅化。适合频繁做动画但内容不变的 `View`。

3. **GPU 加速的 Canvas**：`Canvas` 的绘制操作不再走 Skia 软件路径，而是通过 OpenGL ES 驱动 GPU 完成。常见操作如 `drawRect`、`drawBitmap`、`clipPath` 等被编译为 GL 命令。

不过 Android 3.0 主要是面向平板的过渡版本，硬件加速需要开发者手动开启。

> [已验证: L2 — developer.android.com/guide/topics/graphics/hardware-accel]

### Android 4.0 ICS：默认开启

Android 4.0 Ice Cream Sandwich（API 14，2011 年）将硬件加速设为 **所有 targetSdk ≥ 14 应用的默认行为**。开发者不再需要手动添加 `android:hardwareAccelerated="true"`，GPU 渲染成为 Android UI 的标准路径。

同时，Android 4.0 **强制要求** 所有搭载该版本的设备支持硬件加速的 2D 绘制，将 GPU 加速从"可选特性"升级为"平台基线"。

> [已验证: L2 — developer.android.com/about/versions/android-4.0-highlights]

## Project Butter 与 VSync/Choreographer（Android 4.1）

### 60 FPS 的承诺

Android 4.1 Jelly Bean（API 16，2012 年）的 **Project Butter** 是渲染流畅度的一次标志性升级。Google 承诺"vsync 时代的 60 FPS"，核心改动有三个：

**Choreographer** 是整个改动的枢纽。它接收来自 SurfaceFlinger 的 VSync 信号（在 Perfetto 中对应 `VSYNC-app`），在信号到来时触发 `doFrame()`，依次执行 `INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT` 回调。`TRAVERSAL` 阶段执行 `performTraversals()`，即 `measure → layout → draw`。

在 Perfetto 中，Choreographer 的调度可以通过 `Choreographer#doFrame` slice 观察。每个 `doFrame` 的开始时间应该紧贴 `VSYNC-app` 信号，如果出现明显延迟，说明主线程被阻塞。

**三重缓冲（Triple Buffering）**：当一帧超过 16.67ms（60Hz）时，双缓冲会导致下一个 VSync 周期也被阻塞（因为 CPU 要等 GPU 释放 Buffer）。三重缓冲引入第三个 Buffer，允许 CPU 在 GPU 仍在渲染上一帧时就开始准备当前帧，减少连续丢帧。

**VSync 信号分发模型**：SurfaceFlinger 从硬件 Composer（HWC）获取 VSync 周期信号后，通过 `DispSync` 模型生成两个偏移信号：
- `VSYNC-app`：分发给应用进程的 Choreographer，触发 UI 线程的 measure/layout/draw
- `VSYNC-sf`：分发给 SurfaceFlinger 自身，触发合成

两者的时间偏移（在 Perfetto 中可以观察 `VSYNC-app` 和 `VSYNC-sf` 的间距）决定了 App 渲染和 SF 合成之间的流水线配合。

[图：VSync 信号分发时序图，展示 HWC → DispSync → VSYNC-app/VSYNC-sf 的分发流程与 offset 关系]

[待高爷补充：Perfetto 中 VSYNC-app 和 VSYNC-sf 信号的 Track 截图，标注 offset 间距]

> [已验证: L2 — source.android.com/devices/graphics]



## RenderThread：主线程与 GPU 命令的分离（Android 5.0）

### 为什么需要 RenderThread

在 Android 4.x 中，虽然硬件加速已经默认开启，但 GPU 命令的提交仍然在主线程上执行。`draw` 阶段不仅要构建 DisplayList，还要将 GL 命令 flush 给 GPU。这里有一个关键的 API 行为差异：`eglSwapBuffers()` 本身是**非阻塞**的——它只是将待显示帧入队到 GPU 的命令队列，然后立即返回，主线程继续执行后续代码；真正会阻塞主线程的是 `glFinish()`——它强制等待 GPU 完成所有已提交的命令才会返回。在 Android 5.0 之前，`glFinish()` 是主线程卡顿的常见根因，而 Android 5.0 引入 RenderThread 之后，GL 命令的提交和等待都移到了独立线程，主线程得以解放。

### RenderThread 的工作方式

Android 5.0 Lollipop（API 21，2014 年）引入了 **RenderThread**——一个系统管理的专用渲染线程。

新的流程变成：

1. **主线程**执行 `measure → layout → draw`，在 `draw` 阶段将绘制操作录制到 `DisplayListCanvas`（后改为 `RecordingCanvas`），生成 `RenderNode` 树
2. 主线程将 `RenderNode` 树**同步**到 RenderThread
3. **RenderThread** 独立执行 GPU 命令：遍历 `RenderNode` 树，将 Skia draw 命令转为 GL/Vulkan 调用，提交给 GPU
4. RenderThread 完成后通过 `FrameMetrics` 或 `FrameTimeline` 通知帧完成

在 Perfetto 中，我们可以看到 `UI Thread` 和 `RenderThread` 两个独立的 Track。`UI Thread` 上的 `performTraversals` 结束后，`RenderThread` 上的 `DrawFrame` 才开始执行 GPU 工作。如果 `DrawFrame` 耗时长，但 `UI Thread` 已经空闲，说明 GPU 是瓶颈，而非主线程代码问题。

[图：Perfetto 中 UI Thread 与 RenderThread 的 Track 分离示意图，标注 performTraversals 和 DrawFrame 的时序关系]

[待高爷补充：Android 5.0+ 设备的 Perfetto Trace 截图，清晰展示 UI Thread 与 RenderThread Track 分离]

RenderThread 还带来一个额外好处：即使主线程正在处理耗时操作（如数据库读写），**属性动画（Property Animation）仍可由 RenderThread 独立驱动**。比如 `View.setTranslationX()` 只修改 `RenderNode` 的变换矩阵，不需要主线程重新 `draw`，RenderThread 直接在下一帧应用新变换并提交 GPU。Ripple 效果（水波纹）同理。

> [已验证: L2 — developer.android.com/about/versions/android-5.0-changes, AOSP frameworks/base/libs/hwui/renderthread]

## HWUI 后端演进：OpenGL ES → SkiaGL → SkiaVulkan

HWUI 的 GPU 后端经历了一条清晰的替换路径：

### OpenGL ES 直接后端（Android 3.0 ~ 7.x）

最初的 HWUI 直接使用 OpenGL ES 2.0 API 作为渲染后端。`GLES20Canvas`（后改名为 `DisplayListCanvas`）将 `Canvas` 的 draw 命令直接编译为 GL 调用。Skia 仍然存在，但只在特定场景（如路径光栅化）中被调用。

### SkiaGL 后端（Android 8.0 测试，9.0 默认）

Android Oreo（8.0）开始测试将 Skia 作为统一的渲染后端，通过 Skia 的 OpenGL ES 后端（`SkiaGL`，内部使用 `SKIA_GL_THREADED`）执行所有 2D 绘制。Android Pie（9.0）正式将 SkiaGL 设为默认路径。

这个改动简化了架构：HWUI 不再直接管理 OpenGL ES 上下文，而是将所有绘制命令交给 Skia，由 Skia 统一调度 GPU。好处是 Skia 团队可以独立优化渲染管线，无需 HWUI 逐版本调整 GL 调用。

### SkiaVulkan 后端（Android 10+ 可测试，2024+ 扩大部署）

Skia 同时实现了 Vulkan GPU 后端。从 Android Q（10.0）开始，开发者可以通过调试参数启用 `SkiaVulkan` 管线。到 2024 年，新芯片组开始默认使用 SkiaVulkan 后端。

Vulkan 后端相比 OpenGL ES 的具体改进：
- **CPU 开销降低约 30–50%** [待验证：需补充 benchmark 来源]：Vulkan 的命令缓冲区（Command Buffer）允许多线程并行构建和提交 GPU 命令，省去了 OpenGL ES 驱动层大量的隐式状态验证和同步开销
- **显式内存管理**：应用可以精确控制 GPU 内存的分配时机（通过 `VkAllocateMemory`）、绑定和释放，而非依赖 GL 驱动的隐式管理。内存生命周期与帧调度因此可以精确对齐，减少显存浪费
- **扩展图形特性集**：Vulkan 1.1+ 提供计算着色器（Compute Shader）、多通道渲染（Multi-pass Rendering）、异步计算队列等 OpenGL ES 3.x 不具备或受限的能力

> [已验证: L2 — developer.android.com/ndk/guides/graphics, skia.org, XDA-developers.com]

### Vulkan 兼容性要求

- Android 10（API 29）：64 位设备必须支持 Vulkan 1.1
- Android 13（API 33）：新设备必须支持 Vulkan 1.3

## BLASTBufferQueue：统一的 Buffer 管理（Android 12）

### 从 BufferQueue 到 BLASTBufferQueue

在 Android 11 及之前，App 进程与 SurfaceFlinger 之间的 Buffer 流转通过 `BufferQueue` 管理。`BufferQueue` 的设计存在一些问题：当多个 App 进程同时提交 Buffer 时，窗口几何变化（如旋转、resize）和 Buffer 内容的同步缺乏统一机制，可能导致 ANR（因为 View 事务已更新但 Buffer 回调未释放）。

Android 12（API 31，2021 年）引入了 **BLASTBufferQueue**（BLAST = Buffer Layer Async Synced Transfer），替代了 App 端的 `BufferQueue`。

### BLASTBufferQueue 的核心改进

1. **App 端自主提交**：App 不再需要等待 SurfaceFlinger 释放 Buffer 才能获取新的 Buffer，而是可以主动向 SurfaceFlinger "blasting"提交 Buffer，SurfaceFlinger 在下一个 `VSYNC-sf` 时机进行合成
2. **事务与 Buffer 绑定**：窗口几何变化（位置、大小、裁剪）与 Buffer 内容打包在一起提交，确保状态一致性
3. **多进程同步优化**：当多个 App 进程向同一个 SurfaceFlinger 提交内容时，`BLASTBufferQueue` 提供了更健壮的同步机制

在 Perfetto 中，这个变化主要体现在 Buffer 流转相关的事件和 Fence 时间线上。如果我们习惯了 Android 11 及之前的 `BufferQueue` Track，在 Android 12+ 上需要关注 `BLASTBufferQueue` 相关的 slice。

[图：Android 11 BufferQueue 与 Android 12 BLASTBufferQueue 的 Buffer 流转对比示意图]

[待高爷补充：可用文字流程图 + Perfetto 中 BufferQueue/BLASTBufferQueue 相关 slice 截图]

> [已验证: L2 — source.android.com/devices/graphics, AOSP frameworks/native/libs/gui/BLASTBufferQueue.cpp]

## Android 16：Vulkan 统一渲染堆栈

### Vulkan 成为官方图形 API

Android 16 带来一个实质性的转变：**Vulkan 正式成为 Android 的官方图形 API**。OpenGL ES 不再接受新特性开发，进入维护模式。

但 App 不需要改代码。Android 16 集成了 **ANGLE**（Almost Native Graphics Layer Engine）作为系统级驱动，将 OpenGL ES 调用翻译为 Vulkan 调用。结果：
- 使用 OpenGL ES 的 App 自动获得 ANGLE 翻译层带来的优化
- 游戏和图形密集型应用应直接使用 Vulkan API 以获得最佳性能
- 开发者可以使用 `Android Vulkan Profile 2025` 确保跨设备兼容性

### AGSL 图形着色能力增强

Android 16 扩展了 **AGSL**（Android Graphics Shading Language），新增 `RuntimeColorFilter` 和 `RuntimeXfermode`。开发者可以用类似 GLSL 的语法编写自定义图形效果（阈值、褐色调、色相饱和度等），直接应用于 `Canvas` 的绘制调用。

```java
// 示例：使用 AGSL RuntimeColorFilter
RuntimeShader shader = new RuntimeShader(
    "uniform half2 iResolution;\n" +
    "half4 main(float2 fragCoord) {\n" +
    "  return half4(1.0, 0.5, 0.0, 1.0);\n" +
    "}"
);
paint.setColorFilter(shader.createColorFilter());
canvas.drawRect(rect, paint);
```

### 自适应刷新率（ARR）

Android 15 引入、Android 16 进一步完善的 **自适应刷新率**（Adaptive Refresh Rate, ARR）是渲染管线的又一次重大变革。

ARR 将**显示刷新率与内容帧率解耦**：当内容以 30 FPS 渲染时，屏幕刷新率可以同步降低到 30Hz（而非维持 120Hz），降低功耗（在低帧率场景下，屏幕刷新率从 120Hz 降到 30Hz，GPU 和显示驱动的功耗可下降约 40–60% [待验证：需补充实测来源]，具体取决于面板和 SoC）；当用户开始滑动时，刷新率可以无缝提升到 120Hz，消除卡顿。

实现要求：
- 硬件：支持离散 VSync 步进的显示面板
- 系统：HWC HAL v3（`android.hardware.graphics.composer3`）
- API：`hasArrSupport()` 和 `getSuggestedFrameRate(int)` 帮助 App 集成

RecyclerView 1.4 已内置 ARR 支持，在 fling 和 smooth scroll 操作时自动请求合适的帧率。

在 Perfetto 中，ARR 的变化体现在 **`VSYNC-app` 信号不再固定间隔**。当 App 请求 30 FPS 时，`VSYNC-app` 的周期间隔会变为约 33.3ms 而非 8.33ms（120Hz）。这让 Perfetto 分析需要更仔细地识别帧率切换场景。

[图：ARR 开启前后 VSYNC-app 信号间隔对比，展示 120Hz→30Hz 切换时的 Trace 表现]

[待高爷补充：支持 ARR 的设备上 VSYNC-app 间隔动态变化的 Perfetto 截图]

> [已验证: L2 — developer.android.com/about/versions/16/features, developer.android.com/about/versions/15/features]

## Choreographer 与 FrameMetrics API 的演进

### Choreographer 的版本变化

从 Android 4.1 引入到 Android 16，Choreographer 的核心职责未变——在 VSync 信号到来时调度帧工作。但实现细节在持续优化：

- Android 4.1：引入 `Choreographer`，VSync 信号通过 `DisplayEventReceiver` 的 native 层接收
- Android 5.0：与 RenderThread 协作，`doFrame()` 的 `CALLBACK_COMMIT` 阶段将帧提交给 RenderThread
- Android 16：配合 ARR，Choreographer 需要适应动态的 VSync 周期，帧节奏库（Frame Pacing Library / Swappy）也相应更新

### FrameMetrics API：量化每一帧的"慢"在哪里

当我们分析卡顿时，最常面对的问题是"这帧为什么超了 16.67ms"。FrameMetrics 就是回答这个问题的工具——它把一帧的完整生命周期拆解为多个阶段，告诉我们时间究竟花在了哪里。

FrameMetrics 在 Android 7.0（API 24）引入，通过 `Window.addOnFrameMetricsAvailableListener()` 注册回调，系统会在每帧渲染完成后回调一次，附带该帧各阶段的精确耗时。开发者不需要在代码里手动打点，就能拿到完整的帧耗时分布。

FrameMetrics 将一帧的渲染拆解为以下阶段：

| 阶段 | 含义 |
|------|------|
| `INTENDED_VSYNC_TIMESTAMP` | 本帧期望的 VSync 时间 |
| `UNKNOWN_DELAY_DURATION` | 未知延迟 |
| `INPUT_HANDLING_DURATION` | Input 事件处理耗时 |
| `ANIMATION_DURATION` | 动画计算耗时 |
| `LAYOUT_MEASURE_DURATION` | measure + layout 耗时 |
| `DRAW_DURATION` | draw（录制 DisplayList）耗时 |
| `SYNC_DURATION` | 主线程与 RenderThread 同步耗时 |
| `COMMANDS_DURATION` | RenderThread 执行 GPU 命令耗时 |
| `SWAP_BUFFERS_DURATION` | 提交 Buffer 耗时 |
| `TOTAL_DURATION` | 总耗时 |

在实际分析中，我们通常关注两个层面：

第一是**单帧瓶颈定位**。如果 `LAYOUT_MEASURE_DURATION` 占比最高，说明 View 层级过深或 layout 逻辑过重；如果 `COMMANDS_DURATION` 高，说明 GPU 是瓶颈；如果 `SYNC_DURATION` 异常，可能是主线程和 RenderThread 之间的同步出了问题（常见于大量 RenderNode 变更的场景）。

第二是**整体帧率趋势**。通过持续收集 FrameMetrics 数据，我们可以建立帧耗时的时间线，发现哪些场景出现规律性 Jank。Android 12 的 `FrameTimeline` Track 在 Perfetto 中直观地展示了这一点——每一帧都有"预期完成时间"和"实际完成时间"的对比，绿色表示准时，红色表示 Jank。FrameMetrics 的阶段数据与 FrameTimeline 的视觉表现结合起来，就能精确定位 Jank 的根因。

需要注意的是，FrameMetrics 只在 App 进程内可用（它是 per-window 的 API）。如果要分析系统级的帧率问题（如 SurfaceFlinger 合成延迟），需要结合 Perfetto Trace 中的 SurfaceFlinger Track 和 FrameTimeline 数据。

### Frame Pacing Library（Swappy）

Frame Pacing Library 是 Android Game Development Kit（AGDK）的一部分，专门为游戏场景设计。它通过精确控制 `swap` 时机来确保帧均匀分布：
- 自动检测设备的最佳帧率（如 60/90/120Hz）
- 为短帧补偿等待时间，避免显示重复帧
- 为长帧添加 `present timestamp`，确保在正确的 VSync 周期显示
- 在 ARR 设备上自动适配动态刷新率

Unreal Engine 已集成 Swappy。

> [已验证: L2 — developer.android.com/reference/android/view/FrameMetrics, developer.android.com/games/sdk/frame-pacing]

## 版本演进时间线总览

| 版本 | 年份 | 关键里程碑 | 对 Perfetto 分析的影响 |
|------|------|-----------|----------------------|
| 3.0 | 2011 | HWUI + OpenGL ES 2.0 硬件加速引入 | `RenderNode`（DisplayList）概念诞生 |
| 4.0 | 2011 | 硬件加速默认开启 | GPU 渲染成为基线 |
| 4.1 | 2012 | Project Butter：Choreographer + VSync + 三重缓冲 | `VSYNC-app` / `VSYNC-sf` Track 首次出现 |
| 5.0 | 2014 | RenderThread 引入 | `UI Thread` 与 `RenderThread` 分离为独立 Track |
| 7.0 | 2016 | FrameMetrics API | 可量化每帧各阶段耗时 |
| 8.0 | 2017 | SkiaGL 后端测试 | HWUI 渲染路径变更（OpenGL → SkiaGL） |
| 9.0 | 2018 | SkiaGL 正式默认 | `hwui` Task 线程行为变化 |
| 10 | 2019 | Vulkan 1.1 强制要求（64位） | SkiaVulkan 可测试 |
| 12 | 2021 | BLASTBufferQueue + FrameTimeline | Buffer 管理 Track 变化；可精确对比预期/实际帧时间 |
| 13 | 2022 | Vulkan 1.3 强制要求 + AGSL 引入 | 自定义图形着色器可用 |
| 15 | 2024 | ARR 自适应刷新率引入 | `VSYNC-app` 间隔不再固定 |
| 16 | 2025 | Vulkan 官方图形 API + ANGLE + ARR 增强 | 渲染堆栈统一；帧率动态切换更频繁 |

> [已验证: Android 16 于 2025 年 6 月 10 日正式发布（稳定版 BP2A.250605.031.A2），确认年份为 2025。验证来源: Wikipedia + androidcentral.com + androidauthority.com。验证时间: 2026-04-03]



## 常见问题与误区

### "硬件加速从 Android 4.0 才开始"——不准确

Android 3.0 就引入了 HWUI 硬件加速，4.0 只是将它设为默认开启。如果分析的是 targetSdk < 14 的老应用，它可能仍在走 CPU 软件渲染路径——在 Perfetto 中表现为 `draw` 阶段没有对应的 GPU 工作，主线程承担了全部光栅化。

### "RenderThread 是 App 自己创建的线程"——不是

RenderThread 是 `hwui` 库内部管理的系统线程，每个拥有硬件加速 Window 的进程都会自动创建一个。它不是 `Thread` 的子类，而是通过 native 代码（`renderthread::RenderThread.cpp`）实现的。在 Perfetto 中它的线程名通常是 `RenderThread`。

### "BLASTBufferQueue 在 Android 12 就完全替代了 BufferQueue"——部分替代

BLASTBufferQueue 替代的是 **App 端**与 SurfaceFlinger 之间的 Buffer 流转。SurfaceFlinger 内部以及系统服务之间的 Buffer 管理仍然使用 `BufferQueue`。在 Perfetto 中，两者的 Track 共存是正常的。

### "VSync 信号间隔永远固定"——ARR 打破了这个假设

在支持 ARR 的设备上（Android 15+），`VSYNC-app` 的间隔会随内容帧率动态调整。分析 Perfetto Trace 时，如果看到 `VSYNC-app` 间隔在 8.33ms 和 33.3ms 之间跳变，这不是异常，而是 ARR 在工作。需要结合 `FrameTimeline` Track 来判断帧是否准时完成，而非单纯看 VSync 间距。

### "FrameMetrics 能分析系统级问题"——不能

FrameMetrics 是 per-window、per-process 的 API，只能报告当前 App 进程内某一帧的各阶段耗时。如果要分析 SurfaceFlinger 合成延迟、HWC 行为等系统级问题，必须使用 Perfetto Trace。两者的定位完全不同：FrameMetrics 用于 App 端自省，Perfetto 用于全系统分析。

## 参考资料

### AOSP 源码路径
- `frameworks/base/libs/hwui/` — HWUI 渲染引擎（含 RenderThread、RenderNode）
- `frameworks/base/core/java/android/view/Choreographer.java` — Choreographer 实现
- `frameworks/base/core/java/android/view/FrameMetrics.java` — FrameMetrics API
- `frameworks/native/libs/gui/BLASTBufferQueue.cpp` — BLASTBufferQueue 实现
- `frameworks/native/services/surfaceflinger/` — SurfaceFlinger 合成逻辑

> [已验证: 上述源码路径经 web 搜索验证，在 android-16.0.0_r1 分支中存在。hwui 目录下可见 StatsUtils.cpp、AutoBackendTextureRelease.cpp、JankTracker.cpp 等文件；Choreographer.java、FrameMetrics.java、BLASTBufferQueue.cpp、SurfaceFlinger/ 均为 AOSP 稳定路径，跨版本未变。验证时间: 2026-04-03]

### 官方文档
- [Hardware Acceleration](https://developer.android.com/guide/topics/graphics/hardware-accel)
- [Android Versions](https://developer.android.com/about/versions)
- [Android 16 Features](https://developer.android.com/about/versions/16/features)
- [Graphics Architecture](https://source.android.com/devices/graphics)
- [Frame Pacing Library](https://developer.android.com/games/sdk/frame-pacing)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Vulkan on Android](https://developer.android.com/ndk/guides/graphics)

## 总结

回看这段从 Android 3.0 到 16 的渲染演进，可以看到一条清晰的线索：**把更多工作交给 GPU，把主线程解放出来**。

最初，CPU 包揽了从 Measure/Layout/Draw 到像素生成的全部工作。OpenGL ES 硬件加速把像素生成交给了 GPU；RenderThread 把 GPU 命令提交从主线程剥离出去；SkiaGL/SkiaVulkan 统一了 GPU 后端；BLASTBufferQueue 让 Buffer 提交变成异步操作。每一步都在减轻主线程的负担——这也是为什么在 Perfetto 中，现代 Android 的主线程 `performTraversals` 可以非常短：它只需要录制 RenderNode，GPU 工作全部在 `RenderThread` Track 上执行。

另一条线索是**渲染节奏从固定到自适应**。Project Butter 确立了 VSync 驱动 60 FPS 的模型，但固定刷新率在高帧率设备上浪费功耗。ARR 让刷新率跟随内容帧率动态调整，`VSYNC-app` 不再是均匀的节拍器。Perfetto 分析也需要相应调整：不能只看 VSync 间隔是否均匀，还要结合 `FrameTimeline` 判断帧是否在预期时间内完成。

理解这些版本差异，是分析 Perfetto Trace 的前提条件。`RenderThread` Track 从 Android 5.0 才存在；`BLASTBufferQueue` 从 Android 12 开始取代 `BufferQueue`；ARR 设备上的 `VSYNC-app` 间隔会动态变化——每一个 Track 都带着版本烙印，忽略了这一点，就可能对着正确的 Trace 得出错误的结论。
