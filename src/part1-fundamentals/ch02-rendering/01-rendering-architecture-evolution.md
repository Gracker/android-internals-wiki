---
title: Android 渲染架构与版本演进
chapter: '2.1'
section: '2.1'
applicable_versions: Android 3.0 (API 11) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: 'AOSP android-17.0.0_r1: View/ViewRootImpl/Choreographer/ThreadedRenderer/HardwareRenderer/BaseRecordingCanvas, HWUI RenderNode/DrawFrameTask/CanvasContext/Properties/Skia pipelines, BufferQueue/BLASTBufferQueue, SurfaceFlinger FrontEnd/Scheduler/HWComposer/HWC2/ComposerHal/RenderEngine; kernel android17-6.18-2026-06_r6 boundary; Writer rendering_pipelines S01/S02'
confidence: medium
sources:
- type: official
  path: https://developer.android.com/guide/topics/graphics/overview
- type: official
  path: https://source.android.com/docs/core/graphics/unsignaled-buffer-latch
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: blog
  path: https://www.yuque.com/docs/share/0a92fc0e-185c-4f03-a088-458bb9f3913f
- type: blog
  path: https://mp.weixin.qq.com/s?__biz=MzkxMDc4NTc0OQ==&mid=2247483817&idx=1&sn=f280eb86b50d803c89113ff2c7bb105b
- type: research
  path: AOSP 源码分析 frameworks/base/core/java/android/view
- type: aosp
  path: frameworks/base/core/java/android/view/View.java
- type: aosp
  path: frameworks/base/core/java/android/view/ViewRootImpl.java
- type: aosp
  path: frameworks/base/core/java/android/view/Choreographer.java
- type: aosp
  path: frameworks/base/core/java/android/view/ThreadedRenderer.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/HardwareRenderer.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/BaseRecordingCanvas.java
- type: aosp
  path: frameworks/base/libs/hwui/RenderNode.h
- type: aosp
  path: frameworks/base/libs/hwui/RenderNode.cpp
- type: aosp
  path: frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp
- type: aosp
  path: frameworks/base/libs/hwui/renderthread/CanvasContext.cpp
- type: aosp
  path: frameworks/base/libs/hwui/Properties.cpp
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/SkiaPipeline.cpp
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueCore.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: frameworks/native/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: frameworks/native@android-11.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/Layer.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/FrontEnd/
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/
- type: aosp
  path: frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/DisplayHardware/ComposerHal.h
- type: aosp
  path: frameworks/native/libs/renderengine/
- type: research
  path: Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: research
  path: Writer/rendering_pipelines/S02_aosp_standard_type.md
- type: official
  path: developer.android.com/about/versions
- type: official
  path: developer.android.com/about/versions/16/features
- type: official
  path: developer.android.com/about/versions/17/summary
- type: official
  path: developer.android.com/develop/ui/views/graphics/hardware-accel
- type: official
  path: developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
- type: official
  path: developer.android.com/develop/ui/views/graphics/webgpu
- type: official
  path: developer.android.com/jetpack/androidx/releases/webgpu#1.0.0-alpha05
- type: official
  path: developer.android.com/reference/androidx/webgpu/GPUSurface
- type: official
  path: developer.android.com/reference/android/view/Choreographer.FrameTimeline
- type: official
  path: developer.android.com/reference/android/view/Display
- type: official
  path: developer.android.com/reference/android/view/FrameMetrics
- type: official
  path: developer.android.com/games/develop/vulkan/overview
- type: official
  path: developer.android.com/ndk/guides/graphics/android-vulkan-profile
- type: official
  path: perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: source.android.com
- type: official
  path: source.android.com/docs/compatibility/16/android-16-cdd
- type: official
  path: source.android.com/docs/core/graphics/implement-vulkan
- type: official
  path: github.com/KhronosGroup/Vulkan-Profiles/blob/1e7889df491ae9284ca096fcc1eb2bfcd1f367cb/profiles/VP_ANDROID_16_minimums.json
- type: aosp
  path: frameworks/base/core/java/android/view/Choreographer.java (android-5.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/view/Choreographer.java (android-6.0.0_r1)
- type: aosp
  path: frameworks/base/libs/hwui/Properties.cpp (android-8.0.0_r1)
- type: aosp
  path: frameworks/base/libs/hwui/Properties.cpp (android-9.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/view/Choreographer.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/view/Display.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/view/FrameRateVelocityPoint.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/view/FrameMetrics.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/RuntimeColorFilter.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/RuntimeXfermode.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/animation/RenderNodeAnimator.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/libs/gui/BLASTBufferQueue.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp (android-17.0.0_r1)
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h (android-17.0.0_r1)
- type: aosp
  path: external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto (android-17.0.0_r1)
- type: kernel
  path: kernel/common/drivers/dma-buf/dma-buf.c (android17-6.18-2026-06_r6)
- type: kernel
  path: kernel/common/drivers/dma-buf/dma-fence.c (android17-6.18-2026-06_r6)
- type: kernel
  path: kernel/common/drivers/dma-buf/sync_file.c (android17-6.18-2026-06_r6)
- type: writer
  path: Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: writer
  path: Writer/rendering_pipelines/S02_aosp_standard_type.md
- type: writer
  path: Writer/rendering_pipelines/S03_surfaceview_type.md
- type: writer
  path: Writer/rendering_pipelines/S04_textureview_type.md
- type: writer
  path: Writer/rendering_pipelines/S05_mixed_rendering_type.md
- type: writer
  path: Writer/rendering_pipelines/S06_multi_window_type.md
- type: writer
  path: Writer/rendering_pipelines/S07_software_offscreen_type.md
- type: writer
  path: Writer/rendering_pipelines/S08_native_graphics_type.md
- type: writer
  path: Writer/rendering_pipelines/S09_webview_type.md
- type: writer
  path: Writer/rendering_pipelines/S10_flutter_type.md
- type: writer
  path: Writer/rendering_pipelines/S11_camera_type.md
- type: writer
  path: Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
- type: writer
  path: Writer/rendering_pipelines/S13_game_type.md
- type: writer
  path: Writer/rendering_pipelines/S14_react_native_type.md
- type: writer
  path: Writer/rendering_pipelines/images/DIAGRAM_MANIFEST.md
tags:
- rendering
- hwui
- skia
- surfaceflinger
- gpu
- triple-buffering
- rendering-pipeline
- bufferqueue
- vsync
- displaylist
- rendernode
related_chapters:
- '2.2'
- '2.3'
- '2.4'
- '2.9'
- '2.7'
status: finalized
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch02-rendering/01-rendering-overview.md
- src/part1-fundamentals/ch02-rendering/09-rendering-evolution.md
---

# Android 渲染架构与版本演进

一次触摸已经改变了 View 的状态，下一帧却没有按时出现在屏幕上。问题可能出在主线程遍历、RenderThread、GPU、应用侧 BufferQueue、SurfaceFlinger，甚至显示合成阶段。只看一段 `draw` 耗时，很难判断阻塞发生在哪里。

分析这类问题需要先回答两个问题：

1. 谁在生产图形缓冲区，缓冲区交给了哪一个 Surface？
2. 当前观察到的事件位于“生成内容”“提交缓冲区”“系统合成”还是“显示呈现”阶段？

现行架构以 Android 17 / API 37 / `android-17.0.0_r1` 为源码基线，从普通应用窗口出发，说明 View、HWUI、BufferQueue、BLAST、SurfaceFlinger、Hardware Composer（HWC）和显示设备之间的关系。历史部分保留 Android 3.0 到 Android 17 的演进边界。内核对象只用于解释同步与共享缓冲区，基线为 `android17-6.18-2026-06_r6`。

先明确几个会贯穿全文的对象：buffer 是保存一帧图形内容的缓冲区，Surface 是 Producer（生产者）提交 buffer 的目标接口，BufferQueue 负责在 Producer 与 Consumer（消费者）之间流转 buffer，Layer 则是 SurfaceFlinger 组织合成内容的单位。latch 指 SurfaceFlinger 选中并取得某个可用 buffer，fence 是表示异步读写何时完成的同步信号。BLAST（Buffer Layer Async Surface Transactions）用于协调窗口 buffer 与 SurfaceControl transaction 的提交。

一帧从应用获得 VSync 开始，经过 UI 线程、RenderThread、GPU、BufferQueue 和 SurfaceFlinger，最后由 HWC 提交显示。版本变化主要改变调度、缓冲区和合成接口，分析时仍要回到 Producer、Consumer、layer 与 fence。

## 帧生产、缓冲与系统合成

### 1. 输出拓扑分类

这里的输出拓扑，指一类内容由哪个 Producer 生成、经过哪个 Surface 和 BufferQueue，并最终成为哪个 Layer。“Android 渲染”包含多种数据路径，它们都可能出现在同一个窗口中，却不一定共享同一个 Producer 或同一条 BufferQueue。

| 内容类型 | 主要生产者 | 提交目标 | 常见特征 |
| --- | --- | --- | --- |
| 普通 View / Compose UI | 应用进程中的 HWUI | 宿主 App Window 的 Surface | 主线程生成 UI 状态和绘制记录，RenderThread 驱动 Skia 绘制 |
| `TextureView` 内容 | 相机、解码器、OpenGL 等生产者 | `SurfaceTexture`，再作为 View 树纹理参与 HWUI 绘制 | 外部内容最终进入宿主窗口缓冲区 |
| `SurfaceView` 内容 | 相机、解码器、游戏引擎等生产者 | 独立 Surface / Layer | 内容有独立缓冲区队列，SurfaceFlinger 与宿主窗口一起合成 |
| 视频解码 | Codec / vendor 组件 | Surface 对应的 BufferQueue | 生产节拍、色彩格式和保护内容约束与普通 UI 不同 |
| 游戏或自建引擎 | EGL / Vulkan 应用代码 | NativeWindow / Surface | 应用自行组织渲染循环与 GPU 工作 |
| WebView / Flutter 等框架 | 框架自身加上 HWUI 或独立 Surface | 取决于具体实现和模式 | 不能仅凭控件名称推断缓冲区拓扑 |

“标准应用窗口路径”指普通 View 或 Compose 内容经过承载 View 树的 App Window，再从该窗口的 HWUI Surface 输出。它不包括 `SurfaceView` 的独立内容生产路径，也不能概括所有 Flutter、WebView、Camera 或视频场景。

若 Perfetto 中出现多条 BufferQueue 或多个 SurfaceFlinger Layer，应按生产者和 Surface 归属拆分，再分析每条路径的时序。

### 2. 标准应用窗口的一帧经过哪些阶段

普通应用窗口的一帧可以概括为下面这条路径：

```text
状态变化 / invalidate / requestLayout
    ↓
ViewRootImpl.scheduleTraversals()
    ↓
Choreographer：INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT
    ↓
ViewRootImpl.performTraversals()
    ↓
按需要执行 measure / layout / draw
    ↓
View 绘制操作录制到 RenderNode / DisplayList
    ↓
ThreadedRenderer → HardwareRenderer.syncAndDrawFrame()
    ↓
RenderThread：同步状态、Skia 绘制、提交 GPU 工作
    ↓
dequeueBuffer → draw → queueBuffer
    ↓
BLASTBufferQueue 将缓冲区放入 SurfaceControl Transaction
    ↓
SurfaceFlinger 接收事务、生成前端快照、latch 可用缓冲区
    ↓
HWC validate：设备合成或客户端合成
    ↓
必要时由 RenderEngine 生成 client target
    ↓
HWC present → present fence → release fence
```

其中，client target 是 SurfaceFlinger 执行客户端合成时生成的中间输出缓冲区。present fence 表示这次显示提交何时越过 Android 可观察的 present 边界，release fence 则表示相关 buffer 何时可以安全复用。

各阶段并非全部按单线程串行执行。主线程、RenderThread、GPU、SurfaceFlinger 和显示硬件可以重叠处理不同帧。分析时必须保留帧号、VSync 周期和 fence 依赖，不能只把各段耗时相加。

#### 一帧至少跨越三个调度域

| 调度域 | 代表线程或组件 | 主要职责 |
| --- | --- | --- |
| 应用 UI | `main` / `ViewRootImpl` / `Choreographer` | 处理输入、动画、布局和绘制记录 |
| 应用渲染 | `RenderThread` + GPU 队列 | 同步 RenderNode、执行 Skia 管线、产生窗口缓冲区 |
| 系统显示 | SurfaceFlinger / HWC / 显示设备 | 选择缓冲区、确定合成策略并呈现 |

“应用主线程已经画完”通常只说明 UI 侧工作到达某个提交边界。它不说明 GPU 已完成，也不说明 SurfaceFlinger 已经 latch，更不说明像素已经开始被面板扫描。

### 3. 主线程：从状态变化到 Traversal

Traversal 是 `ViewRootImpl` 发起的一轮窗口级遍历，按当前状态决定是否执行 measure、layout 和 draw；它不等同于每帧都完整遍历并重绘整棵 View 树。

#### 3.1 `scheduleTraversals()` 合并同一轮请求

View 状态改变后，框架通常不会马上递归遍历整棵树。`ViewRootImpl.scheduleTraversals()` 通过 `mTraversalScheduled` 避免重复调度，并把遍历回调（traversal callback）交给 `Choreographer`：

```java
void scheduleTraversals() {
    checkThreadCompat();
    if (!mTraversalScheduled) {
        mTraversalScheduled = true;
        postTraversalBarrier();
        mChoreographer.postVsyncCallback(
                Choreographer.CALLBACK_TRAVERSAL, mTraversalCallback);
        notifyRendererOfFramePending();
        pokeDrawLockIfNeeded();
    }
}
```

代码路径位于 `frameworks/base/core/java/android/view/ViewRootImpl.java`。同一消息循环内多次 `invalidate()` 或 `requestLayout()` 可以汇入一次待执行的 traversal，但这不保证后续工作量很小：被标记的区域、布局请求的传播范围和窗口状态仍会决定该帧要做多少工作。

#### 3.2 Choreographer 的回调顺序

Android 17 的 `Choreographer` 定义了以下回调类型：

```text
CALLBACK_INPUT
CALLBACK_ANIMATION
CALLBACK_INSETS_ANIMATION
CALLBACK_TRAVERSAL
CALLBACK_COMMIT
```

在一次 `doFrame()` 中，它们按上述顺序执行。这个顺序解释了几个常见现象：

- 输入回调可以先改变状态，动画随后更新属性，traversal 再读取这些结果。
- 主线程在 INPUT 或 ANIMATION 阶段耗时过长，会挤压同一帧留给 TRAVERSAL 的时间。
- COMMIT 位于 traversal 之后，但到达 COMMIT 仍不代表缓冲区已经显示。

#### 3.3 `performTraversals()` 不等于每帧完整执行三大流程

`ViewRootImpl.performTraversals()` 是窗口级遍历的核心入口。根据布局请求、尺寸、可见性、Surface 状态和脏区域，它可能执行：

- 测量（measure）：计算 View 所需尺寸；
- 布局（layout）：确定 View 在父容器中的位置；
- 绘制（draw）：录制或更新需要重绘的内容。

三者都有条件判断。Perfetto 出现 `performTraversals` slice（带起止时间的事件区间）时，不能直接断言该帧完整测量、布局和绘制了整棵 View 树。

##### Measure：父子双方参与尺寸协商

父 View 通过 `MeasureSpec` 把尺寸约束传给子 View：

| 模式 | 含义 |
| --- | --- |
| `EXACTLY` | 尺寸已确定，子 View 应使用该尺寸 |
| `AT_MOST` | 子 View 可以选择不超过上限的尺寸 |
| `UNSPECIFIED` | 父容器没有给出这一方向的上限 |

自定义 View 需要依据内容、建议最小尺寸、padding 和 `MeasureSpec` 调用 `setMeasuredDimension()`。测量次数增加可能来自嵌套权重、父容器的多轮协商、窗口尺寸变化或布局请求传播，不能仅凭一次 `AT_MOST` 判断根因。

##### Layout：确定位置，不自动裁剪内容

Layout 通过 `layout(l, t, r, b)` 和 `onLayout()` 确定子 View 的边界。子 View 的位置和尺寸由父容器决定，但内容是否被裁剪属于绘制阶段行为，还会受 `clipChildren`、`clipToPadding`、outline、显式 clip 和变换影响。

因此，“子 View 位于父 View 边界内”和“超出父边界的像素不会显示”是两个不同判断。

##### Draw：生成绘制记录

硬件加速窗口中，`View.draw()` 及其相关分发逻辑通过 `RecordingCanvas` 记录绘制命令。它们描述“画什么”和状态变换，通常不在主线程当场把最终像素光栅化到显示缓冲区。

常见绘制顺序如下：

1. 绘制背景；
2. 保存或处理滚动、裁剪等状态；
3. 调用 `onDraw()` 绘制自身内容；
4. `dispatchDraw()` 绘制子 View；
5. 绘制前景、滚动条等装饰。

具体分支受 View 标志、缓存、动画和硬件加速状态影响，不应把这份顺序当成所有 View 都固定执行的调用清单。

#### 3.4 `invalidate()` 与 `requestLayout()` 的边界

| API | 主要表达 | 可能触发的工作 |
| --- | --- | --- |
| `invalidate()` | 某个区域的显示内容失效 | 标记脏区域，调度绘制；不主动表达尺寸变化 |
| `requestLayout()` | 当前 View 的测量结果或位置可能失效 | 向父级传播布局请求，并调度 traversal |

两者最终都可能通过 `ViewRootImpl` 汇入下一轮 traversal。`requestLayout()` 的传播和框架优化会影响实际遍历范围，所以“每次调用必然完整重测整棵树”也不准确。

排查主线程问题时，建议同时看：

- 调用频率：是否在循环或动画中反复请求布局；
- View 树规模：深度、宽度以及复杂容器；
- 自定义 `onMeasure()`、`onLayout()`、`onDraw()` 的耗时；
- 是否发生窗口 relayout（重新协商尺寸和 Surface）、Insets（系统栏等占用区域）或配置变化；
- traversal 相对 VSync 的开始时间和结束时间。

### 4. HWUI：从绘制命令到 RenderThread

#### 4.1 RenderNode 保存可复用的绘制记录

硬件加速的 View 树会用 `RenderNode` 表示可独立更新和复用的渲染节点。主线程把 Canvas 操作录制为 DisplayList（可回放的绘制命令列表），后续帧若某个节点内容没有失效，HWUI 可以复用已有记录。

这并不意味着未失效节点完全没有成本。属性同步、树遍历、裁剪、合批（合并可一起提交的绘制操作）、资源生命周期和最终 GPU 工作仍可能涉及该节点。DisplayList 主要减少重复执行 Java 绘制代码和重复生成绘制命令的成本。

Android 17 的 native `RenderNode` 同时维护当前状态与暂存状态（staging state）。与 DisplayList 同步有关的字段和方法包括：

```cpp
bool mNeedsDisplayListSync;
DisplayList mDisplayList;
DisplayList mStagingDisplayList;

void syncDisplayList(TreeObserver& observer, TreeInfo* info);
void pushStagingDisplayListChanges(TreeObserver& observer, TreeInfo& info);
```

这些声明与实现位于：

- `frameworks/base/libs/hwui/RenderNode.h`
- `frameworks/base/libs/hwui/RenderNode.cpp`

主线程更新 staging 数据，RenderThread 在同步阶段把需要的变化推入渲染侧状态。这个双阶段模型能减少两个线程同时修改当前渲染状态所造成的锁竞争。

#### 4.2 `RecordingCanvas` 负责录制

Java 层 `RecordingCanvas` 的绘制 API 最终进入 `BaseRecordingCanvas` 等实现。以绘制 RenderNode 为例，Android 17 的 native 入口由框架内部桥接完成。阅读源码时要区分：

- Java Canvas API；
- JNI/native 方法；
- Skia/HWUI DisplayList 操作；
- RenderThread 上的执行。

看到 `drawRect()`、`drawBitmap()` 或 `drawRenderNode()` 返回，只能说明相应调用已经完成。对于硬件加速 Canvas，最终 GPU 执行通常尚未完成。

#### 4.3 `syncAndDrawFrame()` 是 UI 到 RenderThread 的提交边界

`ThreadedRenderer` 通过 `HardwareRenderer` 把帧信息提交给 native 渲染代理，核心入口名为 `syncAndDrawFrame()`。它连接两类工作：

1. UI 线程准备帧信息和 RenderNode 变化；
2. RenderThread 同步状态并安排绘制。

`frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp` 中的 `DrawFrameTask::run()` 会执行帧状态同步，并按条件决定何时解除 UI 线程等待；随后由 `CanvasContext` 执行绘制和缓冲区交换。

`syncAndDrawFrame()` 的返回值或 slice 结束，不能当作 GPU 完成、BufferQueue 消费完成或屏幕呈现完成的证据。

#### 4.4 RenderThread 和 GPU 允许并行

RenderThread 负责准备并提交 GPU 命令。GPU 在独立队列中执行这些命令，因此可能出现：

```text
主线程准备 Frame N+1
RenderThread 提交 Frame N
GPU 执行 Frame N-1
SurfaceFlinger 合成更早的一帧
```

这种重叠是图形管线维持吞吐量的基础。“某条 GPU track（Perfetto 中记录 GPU 工作的时间轨道）超过一个刷新周期，当前帧就一定掉帧”不是充分判断。需要结合依赖 fence、队列深度和 FrameTimeline，确认该 GPU 工作是否阻塞目标帧的截止时间（deadline）。

#### 4.5 SkiaGL、SkiaVulkan 与渲染后端

Skia 是 Android 使用的二维图形引擎；渲染后端决定它通过哪套图形 API 把命令交给 GPU。Android 17 的 HWUI 包含 Skia OpenGL 与 Skia Vulkan 管线：

- `SkiaOpenGLPipeline`
- `SkiaVulkanPipeline`

`Properties::peekRenderPipelineType()` 会结合构建时的 `use_vulkan()` 结果和 `debug.hwui.renderer` 属性选择 `skiavk` 或 `skiagl`。这是一项设备、构建配置和调试属性共同参与的选择，不能概括成“Android 17 所有设备都默认使用 Vulkan”。

Vulkan 与 OpenGL ES 的 CPU 开销、驱动行为、着色器编译、内存压力和功耗表现依赖具体设备及负载。后端名称本身不能证明某一帧更快。

### 5. BufferQueue：共享缓冲区，而非整帧像素拷贝

#### 5.1 Producer 与 Consumer

一条 BufferQueue 连接一个图形缓冲区生产者和一个消费者：

```text
Producer                         Consumer
dequeueBuffer()
    ↓
等待 acquire/release 条件
    ↓
写入或渲染 GraphicBuffer
    ↓
queueBuffer(fence)
                                acquireBuffer()
                                    ↓
                                等待 fence 后使用缓冲区
                                    ↓
                                releaseBuffer(releaseFence)
```

`queueBuffer()` 主要提交缓冲区槽位、元数据和同步信息。GraphicBuffer 背后的内存通过句柄共享，正常路径不需要在 `queueBuffer()` 时复制整张图片。

`queueBuffer()` 成功只说明生产者把缓冲区置为可消费状态。它没有证明 SurfaceFlinger 已经 latch，更没有证明显示设备已经呈现。

#### 5.2 槽位状态

BufferQueue 中常见的槽位状态为：

| 状态 | 含义 |
| --- | --- |
| `FREE` | 当前可供生产者选择 |
| `DEQUEUED` | 已由生产者取得，正在写入或准备 |
| `QUEUED` | 已提交，等待消费者获取 |
| `ACQUIRED` | 已由消费者获取，尚未释放 |

生产者无法无限制地 `dequeueBuffer()`。最大已 dequeue 数、最大已 acquire 数、异步模式、消费者是否会阻塞以及当前可用槽位共同决定它是否需要等待。

Android 17 的 `BufferQueueCore` 初始配置中可看到最大 acquired 和 dequeued 数的默认值，但实际最大缓冲区数量由运行时条件计算。它不是全系统固定的三个缓冲区。

#### 5.3 “三缓冲”要按队列状态理解

双缓冲或三缓冲常被用来描述生产、消费和显示可以同时占用多个缓冲区，但 Android 的 BufferQueue 深度具有动态性：

- Surface 尺寸、格式或使用属性（usage，即缓冲区可用于 CPU、GPU、相机等哪些场景）改变会触发重新分配；
- 最小未释放数量与 consumer 配置有关；
- async（异步入队）/ shared buffer（共享同一缓冲区）等模式会改变规则；
- dequeue/acquire 上限会限制可并行持有的缓冲区；
- fence 未完成时，槽位即使逻辑上可流转也可能还不能安全复用。

多一个可用缓冲区有时能减少生产者因暂时无槽位而停顿，但队列持续堆积也可能增加输入到显示的延迟。不能把“三缓冲”写成必然降低卡顿，或必然增加一整帧延迟。

#### 5.4 背压比“丢弃所有多余帧”更准确

背压（backpressure）表示 Consumer 的处理或释放速度反过来限制 Producer；它通常体现为 Producer 等待可用槽位，而不是队列可以无限增长。

应用生产速度超过消费者处理速度时，常见结果包括：

- `dequeueBuffer()` 等待可用槽位；
- 应用被 VSync 节奏约束，无法持续无界生产；
- 队列中的缓冲区在特定模式下按规则被替换或跳过；
- SurfaceFlinger 选择满足 latch 条件的缓冲区；
- Choreographer 检测 buffer stuffing（缓冲区持续积压，旧帧尚未及时消化）并调整恢复节奏。

不同 Surface 类型、present mode（缓冲区如何排队与呈现的模式）和 BufferQueue 配置会改变行为。没有这些条件时，不应笼统写成“多画的帧都会被丢掉”。

### 6. BLAST：把窗口缓冲区与 SurfaceControl 事务对齐

#### 6.1 标准 App Window 中的 BLASTBufferQueue

在现代 Android 的普通应用窗口路径中，应用进程内的 `BLASTBufferQueue` 承担应用侧 BufferQueue Consumer 角色，并把取得的缓冲区包装进 `SurfaceComposerClient::Transaction`。它通过 `setBuffer()` 把 fence、帧号和 release callback（用于交还 buffer 并传递 release 信息的回调）等信息提交给 SurfaceFlinger。

这条路径可以简化为：

```text
HWUI Producer
    │ queueBuffer
    ▼
应用进程内 BLASTBufferQueue
    │ acquire buffer
    │ Transaction.setBuffer(...)
    ▼
SurfaceFlinger 中对应 Layer 的待处理事务
```

这里容易出现两个误解：

- BLAST 不意味着 SurfaceFlinger 通过 Binder 接收整帧像素副本；事务传递的是缓冲区句柄、同步对象和元数据。
- BLAST acquire 到缓冲区后，还要经过事务应用、Layer 状态更新、latch、合成与 present，不能把 BLAST 事件当成显示完成点。

#### 6.2 `BufferTX - <layerName>` 的含义

SurfaceFlinger 的 Layer 追踪中可看到形如 `BufferTX - <layerName>` 的计数器。Android 17 的命名锚点位于 `frameworks/native/services/surfaceflinger/Layer.h`。

它表达 SurfaceFlinger 侧待处理的 buffer transaction 数量，可用于观察事务积压。它不是普通应用 BufferQueue 的槽位状态计数，也不直接等于已经排队等待扫描输出的显示帧数。

分析时应把下面几类指标分开：

| 指标 | 所在边界 |
| --- | --- |
| dequeue / queue / acquire / release | 某条 BufferQueue 的槽位生命周期 |
| `BufferTX - layerName` | SurfaceFlinger Layer 的缓冲区事务积压 |
| FrameTimeline expected / actual | 系统预期呈现时间与实际呈现结果 |
| HWC validate/ present | 显示合成与提交阶段 |

### 7. Fence：说明“什么时候可以安全使用”

图形管线通过 fence 表达跨 CPU、GPU、合成器和显示设备的异步完成关系。名称相近的 fence 所处方向不同。

| Fence | 谁等待 | 表达的条件 |
| --- | --- | --- |
| acquire fence | Consumer | Producer 对该缓冲区的写入何时完成，Consumer 何时可以安全读取 |
| release fence | 后续复用该缓冲区的一方 | 当前 Consumer 何时不再使用该缓冲区，何时可以安全重写 |
| present fence | SurfaceFlinger / 显示时序追踪 | 当前显示提交何时在显示管线的 present 边界完成 |

在应用到 SurfaceFlinger 的队列中，应用是 producer，BLAST/系统侧消费逻辑接收带有 acquire fence 的缓冲区。到了 HWC 和显示设备边界，SurfaceFlinger 又要处理客户端目标（client target）、各 Layer 和 display present 相关的 fence。

#### 7.1 Present fence 的边界

Present fence 是 Android 显示栈的呈现完成时序锚点，但它不等同于面板像素的光学响应完成。面板扫描方式、像素响应时间、显示后处理和外部显示设备都可能位于 Android 软件可观测边界之外。

对于“输入到用户看到变化的总延迟”，应用 trace、FrameTimeline 和 present fence 只能覆盖其中一部分，还需结合触摸采样、显示扫描和面板特性。

#### 7.2 等待 fence 不一定是 GPU 算力不足

一次 fence wait 只能说明依赖尚未满足。上游原因可能是：

- GPU 工作排队或执行时间长；
- producer 提交过晚；
- 前一消费者仍持有缓冲区；
- HWC 或显示设备尚未释放资源；
- 跨进程事务与目标 VSync 错位。

需要沿 fence 的生产者方向追踪，才能确定责任阶段。

### 8. SurfaceFlinger：接收事务、选择内容并组织合成

SurfaceFlinger 管理系统可见 Layer 的状态，接收来自 WindowManager、应用和系统组件的 SurfaceControl transaction（对 Layer 属性或 buffer 的一组原子更新）。Android 17 的实现已经把 Layer 前端状态、快照生成、调度、合成规划和显示设备交互分到多个模块，不能用单一“收到 VSync 后遍历所有 Layer 并画到屏幕”的函数调用描述它。

一轮显示处理涉及的核心概念包括：

1. 接收并应用 SurfaceControl 事务；
2. 更新 Layer 前端状态与可见性；
3. 为当前组合生成快照，也就是供本轮合成决策使用的不可变状态视图；
4. 判断缓冲区是否满足 latch 条件；
5. 结合损伤区域（damage，本帧相对上一帧发生变化的区域）、几何、色彩、protected content（要求安全显示路径的受保护内容）等信息准备合成；
6. 调用 HWC validate/ present；
7. 对需要客户端合成的部分调用 RenderEngine；
8. 传播 present 与 release 同步信息。

具体执行路径受 Scheduler、显示设备、Layer 状态、预测结果和 HWC 返回值影响。分析 trace 时，应围绕当前帧的事务、Layer、FrameTimeline 与 HWC 事件建立对应关系。

#### 8.1 Latch 不是无条件拿最新缓冲区

SurfaceFlinger 选择缓冲区时要考虑：

- acquire fence 是否满足；
- 缓冲区期望呈现时间；
- Layer 与事务状态；
- 当前调度和 latch 策略；
- 当前版本与场景是否允许在严格条件下处理尚未 signal（完成）的 fence。

Android 13 以后存在受约束的 unsignaled buffer latch 优化，即在特定条件下允许选择 fence 尚未完成的 buffer；它有严格条件，不能扩写成 SurfaceFlinger 会忽略所有 acquire fence。

#### 8.2 SurfaceFlinger VSync 与应用 VSync

应用和 SurfaceFlinger 都受显示节拍驱动，但调度器可以给它们设置不同的唤醒相位与 deadline（本周期必须完成的截止时间）。调度目标是让应用先生产，SurfaceFlinger 再在合适的时间消费并提交显示。

高刷新率、可变刷新率和多显示设备让“固定 16.67 ms、应用与 SurfaceFlinger 同时唤醒”的模型失效。性能判断应读取当前显示模式，以及 FrameTimeline 给出的 expected（预期）/ actual（实际）时序。

### 9. HWC 与 RenderEngine：每帧决定如何合成

#### 9.1 HWC validate

Hardware Composer HAL 连接 SurfaceFlinger 与设备显示合成能力。SurfaceFlinger 为 Layer 提供候选 composition type（合成方式），HWC 在 validate 阶段可以接受或要求调整。

合成决策可能受以下因素影响：

- Layer 数量和硬件 plane 数量；plane 是显示控制器可以独立缩放、叠加并输出的一路硬件图层；
- 像素格式、压缩格式与 buffer usage（缓冲区用途标志）；
- 缩放、旋转、裁剪和其他变换；
- alpha、混合模式和遮挡关系；
- dataspace（色彩空间与传递特性等颜色描述）、HDR、色彩转换和显示能力；
- protected content 与安全显示路径；
- 设备厂商的 HWC 实现和当前资源占用；
- 多显示器、虚拟显示器及 client target 约束。

“Layer 太多或有透明混合才会转 GPU 合成”只覆盖少数可能性。

#### 9.2 Device composition 与 Client composition

| 类型 | 主要执行者 | 说明 |
| --- | --- | --- |
| 设备合成（Device composition） | 显示控制器 / HWC 能力 | Layer 可由硬件 plane 等资源直接组合 |
| 客户端合成（Client composition） | SurfaceFlinger 的 RenderEngine | 先把相应 Layer 合成为 client target（供 HWC 使用的中间输出），再交给 HWC |

同一帧可以混合使用两者。某个 Layer 的合成类型（composition type）也可能随帧变化，因此必须查看该帧的 HWC/SurfaceFlinger 数据，不能按应用或控件类型永久归类。

#### 9.3 RenderEngine 与应用 HWUI 是两个组件

两者都可能使用 Skia、OpenGL ES 或 Vulkan 相关图形能力，但职责不同：

- 应用 HWUI 把 View/Compose 绘制记录生成应用窗口缓冲区；
- SurfaceFlinger RenderEngine 在客户端合成、模糊、色彩处理等系统合成任务中生成输出。

应用 GPU slice 很短，不代表 SurfaceFlinger 的 client composition 也很短；反过来也一样。Perfetto 中需要按进程和上下文区分 GPU 工作来源。

#### 9.4 色彩处理位于多个可能阶段

色彩空间转换、色调映射、显示颜色变换可能由 RenderEngine、HWC、显示处理单元或面板侧能力负责，位置取决于 Layer、输出显示和设备实现。它不总是显示前的收尾步骤，成本也不能一概忽略。

### 10. 从应用缓冲区到显示输出，不是同一组“三个 Buffer”

普通窗口的 App BufferQueue 保存应用生成的窗口缓冲区。SurfaceFlinger 若执行 client composition，还会生成 client target。显示控制器和面板扫描又可能有各自的内部缓冲与流水结构。

这些对象属于不同阶段：

```text
App Window GraphicBuffer
    ↓ 作为一个 Layer 的输入
SurfaceFlinger / HWC composition
    ↓ 可能产生 client target
Display present
    ↓
显示控制器扫描与面板响应
```

把它们统一称作“前台、后台、显示中三个缓冲区”会混淆应用 BufferQueue、HWC client target 与 scanout（显示控制器读取像素并送往面板的扫描输出）。排查时应明确当前 buffer 的 owner（持有者）、queue、slot、frame number 和 fence。

### 11. 硬件加速与软件绘制

#### 11.1 硬件加速窗口

硬件加速窗口中，View 绘制命令通常录制进 DisplayList，由 HWUI、RenderThread 和 GPU 生成 GraphicBuffer。优势来自命令复用、GPU 并行和图形管线，但性能仍受内容特征影响：

- 大量离屏层（先画到中间缓冲区再合成）和过度绘制会增加像素工作；
- 复杂 path、阴影、模糊和滤镜可能引入额外 rendering pass（一次独立的渲染处理）；
- 位图上传和纹理缓存失效会增加内存与传输成本；
- shader（着色器）编译或图形管线缓存未命中可能造成耗时抖动；
- 大量 RenderNode 更新也会增加 CPU 同步成本。

#### 11.2 `setLayerType()` 的准确含义

`View.setLayerType(View.LAYER_TYPE_SOFTWARE, ...)` 在硬件加速窗口里为该 View 使用软件生成的 layer 内容，再由硬件管线把它当作纹理参与合成。它不会把整个 Window 切换成软件渲染。

窗口级是否启用硬件加速由 manifest、Window flag 和系统条件决定。View 级 layer type 主要影响该 View 的缓存/绘制策略，两者不能混为一谈。

#### 11.3 软件渲染没有统一的胜负结论

软件 Canvas 由 CPU 执行光栅化，某些小型、低频或特定操作可能成本可控；复杂动画、大面积更新和高分辨率内容通常更容易受 CPU 与内存带宽限制。硬件渲染也可能受驱动、GPU 队列和资源管理影响。

选择渲染方式应基于目标设备、内容和 trace，而不是用“GPU 核心更多”或固定倍数推导速度与功耗。

### 12. 用 Perfetto 建立证据链

把某个阶段的结束当成整帧完成，很容易误判渲染问题。排查可以从用户感知的异常帧反向追踪。

#### 12.1 第一步：锁定目标帧

先查看：

- FrameTimeline 的预期时间线（expected timeline，即系统计划的呈现时间）；
- 实际时间线（actual timeline）和 jank classification（该帧晚到的原因分类）；
- 对应的 application frame（应用生产侧记录）与 SurfaceFlinger frame（系统合成侧记录）；
- 当前刷新率、VSync 周期和 deadline。

帧率只适合描述一段时间的吞吐量。定位单帧应以时间线和 deadline 为主。

#### 12.2 第二步：检查应用主线程

关注：

- Choreographer `doFrame` 是否启动过晚；
- INPUT、ANIMATION、TRAVERSAL 哪一段占用时间；
- `performTraversals` 内是否发生 measure、layout、draw；
- Binder、锁、I/O、GC 或调度延迟是否阻塞主线程；
- `requestLayout()` 或 `invalidate()` 是否异常频繁。

如果主线程很早完成，还要继续检查 RenderThread 与后续阶段。

#### 12.3 第三步：检查 RenderThread 和 GPU

关注：

- `DrawFrame` / `syncAndDrawFrame` 的同步等待；
- dequeue 是否等待可用缓冲区；
- Skia 绘制与 `swapBuffers`；
- GPU queue、GPU completion（完成时间）与相关 fence；
- 资源上传、shader/pipeline 编译和缓存抖动。

RenderThread 的 CPU slice 长度不等于 GPU 实际执行时长（GPU duration）。二者可能重叠，也可能通过 fence 形成依赖。

#### 12.4 第四步：检查 BufferQueue 与 BLAST

沿目标 Surface 查看：

- dequeue、queue、acquire、release 的时间；
- slot 和 frame number 是否对应；
- acquire fence 何时 signal（变为完成状态）；
- `BufferTX - layerName` 是否积压；
- BLAST transaction 何时进入 SurfaceFlinger；
- 队列深度是否带来背压或延迟。

如果一个进程包含多条 Surface，要先确认 Layer 名称与生产者，避免把 SurfaceView、视频或宿主窗口混在一起。

#### 12.5 第五步：检查 SurfaceFlinger 与 HWC

关注：

- 事务应用与 Layer 快照；
- 目标缓冲区是否按期 latch；
- SurfaceFlinger 是否错过自己的 deadline；
- HWC validate 返回的 composition type；
- 是否发生 RenderEngine client composition；
- present fence 和 release fence 的时间；
- 多显示器、刷新率切换或显示模式变化。

不要给 SurfaceFlinger 套用固定“只剩几毫秒”的预算。实际预算取决于当前显示模式、调度相位、预测和 FrameTimeline。

#### 12.6 常见错误推断

| 观察 | 不能直接推出 | 还需要的证据 |
| --- | --- | --- |
| `performTraversals` 出现 | 完整 measure/layout/draw 都已执行 | 内部 slice、布局标志、脏区域 |
| `syncAndDrawFrame` 返回 | GPU 或显示已完成 | GPU fence、`queueBuffer`、FrameTimeline |
| `queueBuffer` 成功 | 画面已经显示 | BLAST/SF latch、HWC present |
| GPU Track 超过一个周期 | 该工作必然导致当前帧掉帧 | GPU 依赖、frame id、deadline |
| `BufferTX` 增加 | App BufferQueue 一定塞满 | 对应 Layer 事务与 BQ slot 状态 |
| HWC 使用 CLIENT | 一定是 Layer 太多 | 每层 composition reason 与设备能力 |
| present fence signal | 面板像素完成响应 | 面板扫描和硬件测量数据 |

### 13. 一个可复用的排查例子

假设列表滑动时出现一次明显停顿，可以按下面的顺序检查：

1. 在 FrameTimeline 中锁定实际晚到的帧，不要只找最长 slice。
2. 查看应用 `doFrame` 是否晚启动；若晚启动，继续看 Runnable、Binder、锁、GC 和调度。
3. 若 `doFrame` 按时启动，检查 INPUT、ANIMATION、TRAVERSAL 的耗时与条件分支。
4. 若 UI 侧按时提交，检查 RenderThread 是否在同步、dequeue、绘制或 swap 阶段等待。
5. 若应用已按时 `queueBuffer`，按 Surface 和 frame number 追踪 BLAST transaction。
6. 检查 SurfaceFlinger 是否及时 latch，以及 acquire fence 是否满足。
7. 检查 HWC composition type、RenderEngine 工作和 present 时序。
8. 最终把根因归到“生产晚、GPU 完成晚、队列背压、系统合成晚或显示呈现晚”中的具体一项。

这种顺序可以避免看到主线程的一次长调用，就提前结束对后续异步阶段的检查。

### 14. 版本演进与 Android 17 边界

#### Android 3.0 / API 11

Android 开始为更多 View 引入硬件加速与 DisplayList 记录。早期实现与现代 RenderNode、RenderThread 架构不同，不能用 Android 17 的类关系直接解释 Android 3.x 行为。

#### Android 4.1 / API 16

Project Butter 是 Android 针对界面流畅度的一组平台改进，它强化了 VSync 驱动的 Choreographer 协调、三重缓冲相关能力和触摸响应优化。这里的“三重缓冲”仍应理解为管线并行策略，不能替代对具体 BufferQueue 配置的检查。

#### Android 5.0 / API 21

现代 HWUI 架构中的 RenderNode 与 RenderThread 分工逐步确立。主线程录制，RenderThread 同步并提交绘制，成为后续版本分析的基础。

#### Android 8.0 / API 26

Project Treble 把 Android framework 与 vendor 实现的接口边界进一步标准化，此后 HWC HAL 的系统/厂商边界更清晰。设备合成能力仍由具体硬件与 vendor 实现决定。

#### Android 10 / API 29

SurfaceControl 事务和渲染相关公开 API 继续扩展，系统合成与应用内容提交的关系更容易通过 trace 观察。

#### Android 11 / API 30

`android-11.0.0_r1` 源码中已经出现 `BLASTBufferQueue`，窗口路径随后逐步采用它来协调缓冲区与 SurfaceControl Transaction。源码中出现该组件不等于所有 Android 11 设备和所有 Surface 类型都采用同一条路径。

#### Android 12 / API 31

FrameTimeline 提供 expected/actual present 时间与 jank 分类，为跨应用和 SurfaceFlinger 的单帧分析提供稳定入口。

#### Android 13 到 Android 16

SurfaceFlinger Scheduler、Layer 前端、FrameTimeline、刷新率和合成策略持续演进。部分版本支持有条件的 unsignaled latch，但同步规则仍需按源码条件判断。

#### Android 17 / API 37

现行架构与源码路径以 `android-17.0.0_r1` 为准：

- ViewRootImpl 通过 Choreographer 调度 traversal；
- HWUI 通过 RenderNode、RenderThread 与 Skia 管线生成应用窗口缓冲区；
- 普通 App Window 使用 BLAST 参与缓冲区与 SurfaceControl Transaction 协调；
- SurfaceFlinger 使用前端状态/快照、Scheduler、HWC 与 RenderEngine 组织显示；
- HWUI 与 SurfaceFlinger 的具体后端选择受构建和设备配置影响；
- 性能结论以 FrameTimeline、fence、BufferQueue 和 HWC 的逐帧证据为准。

### 15. 源码阅读索引

#### 应用主线程与 HWUI Java 层

- `frameworks/base/core/java/android/view/View.java`
- `frameworks/base/core/java/android/view/ViewRootImpl.java`
- `frameworks/base/core/java/android/view/Choreographer.java`
- `frameworks/base/core/java/android/view/ThreadedRenderer.java`
- `frameworks/base/graphics/java/android/graphics/HardwareRenderer.java`
- `frameworks/base/graphics/java/android/graphics/BaseRecordingCanvas.java`

#### HWUI native 层

- `frameworks/base/libs/hwui/RenderNode.h`
- `frameworks/base/libs/hwui/RenderNode.cpp`
- `frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp`
- `frameworks/base/libs/hwui/renderthread/CanvasContext.cpp`
- `frameworks/base/libs/hwui/Properties.cpp`
- `frameworks/base/libs/hwui/pipeline/skia/SkiaPipeline.cpp`
- `frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp`
- `frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp`

#### BufferQueue 与 BLAST

- `frameworks/native/libs/gui/BufferQueueCore.cpp`
- `frameworks/native/libs/gui/BufferQueueProducer.cpp`
- `frameworks/native/libs/gui/BufferQueueConsumer.cpp`
- `frameworks/native/libs/gui/BLASTBufferQueue.cpp`

#### SurfaceFlinger、HWC 与 RenderEngine

- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
- `frameworks/native/services/surfaceflinger/Layer.h`
- `frameworks/native/services/surfaceflinger/FrontEnd/`
- `frameworks/native/services/surfaceflinger/Scheduler/`
- `frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp`
- `frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp`
- `frameworks/native/services/surfaceflinger/DisplayHardware/ComposerHal.h`
- `frameworks/native/libs/renderengine/`

### 标准应用窗口的七段边界

Android 渲染性能不能用“主线程画图，再由 GPU 显示”这一句话解释。标准应用窗口至少包含：

1. Choreographer 与 ViewRootImpl 驱动的 UI 遍历；
2. RenderNode DisplayList 的录制与同步；
3. RenderThread、Skia 和 GPU 生成 GraphicBuffer；
4. BufferQueue 与 BLAST 提交缓冲区和事务；
5. SurfaceFlinger 更新 Layer、latch 缓冲区并组织合成；
6. HWC、RenderEngine 和显示设备完成 present；
7. acquire、release、present fence 维护各阶段的安全依赖。

定位问题时，先确认输出拓扑，再按 frame id、Surface、BufferQueue slot、fence 和 FrameTimeline 逐段核对。这样才能区分应用生产晚、GPU 执行晚、队列背压、SurfaceFlinger 合成晚和显示呈现晚，避免用单个 slice 为整帧下结论。


## 版本演进改变了哪些责任边界

主路径稳定后，版本差异要落到具体接口和线程。Project Butter、RenderThread、Treble、BLAST 和 FrameTimeline 分别改变了帧调度、绘制和观测方式。

Android 渲染史不能只记成一串版本号。拿到 Perfetto 后，工程师需要回答三个问题：

1. 这一版由哪个线程记录 View 绘制命令，又由哪个线程准备和提交 GPU 工作？
2. App buffer 经过哪种队列与事务交给 SurfaceFlinger，页面里是否还有独立 Surface？
3. 当时有哪些 VSync、帧截止时间和 jank 数据可以使用？

这三条线的变化速度不同。Android 5.0 增加 RenderThread，没有改变每个页面都通过 SurfaceFlinger 显示这一事实；Android 11 引入 BLAST，也没有删除 BufferQueue；Android 12 增加 FrameTimeline，也没有让 Trace 中标红的卡顿帧自动带上唯一根因。

当前平台源码锚点是 Android 17 / API 37 的 `android-17.0.0_r1`，kernel 锚点是 `android17-6.18-2026-06_r6`。旧版本只用于说明演进，当前类名与行为以 Android 17 为准。

### 时间线速查

先约定表中的缩写：HWUI 是 Android 的 View 硬件加速渲染管线；NDK 是供 C/C++ 应用使用的 Native Development Kit；BLAST 把 buffer 更新与 Surface transaction 按帧组织；`FrameMetrics` 按 Window 报告一帧各阶段的时间，FrameTimeline 则关联应用帧、显示帧及其预期与实际时间；AGSL 是 Android Graphics Shading Language；ARR 是 Adaptive Refresh Rate（自适应刷新率）；ANGLE 是把 OpenGL ES 调用映射到其他图形 API 的兼容层；WebGPU 是独立发布的现代 GPU 接口。HAL 指 framework 与厂商硬件实现之间的接口，QPR 是 Android 的季度平台更新。launch device 指出厂时就搭载该 Android 版本的设备，不是后来通过 OTA 升级到该版本的设备。

| 版本 | 已验证的里程碑 | 分析 Trace 时的影响 |
| --- | --- | --- |
| Android 3.0 / API 11 | View 2D 硬件加速、显示列表模型、`View.setLayerType()` | 同一个 `Canvas` API 可能走软件或 HWUI 路径 |
| Android 4.0 / API 14 | 对 target API 14 及以上应用默认启用硬件加速 | 不能只按设备版本判断某个 Window 是否硬件加速 |
| Android 4.1 / API 16 | Project Butter 流畅性工程、Choreographer、VSync 驱动的 UI 节拍、三重缓冲策略 | 帧工作开始与显示节拍建立明确关系 |
| Android 5.0 / API 21 | HWUI RenderThread | UI 线程记录与同步、RenderThread 执行需要分开看 |
| Android 6.0 / API 23 | Choreographer 增加 COMMIT 回调阶段 | 现代回调顺序开始接近当前形态 |
| Android 7.0 / API 24 | Vulkan NDK API、`FrameMetrics` | 原生渲染多一种底层 API；App 可按 Window 取得帧阶段数据 |
| Android 8.x / API 26–27 | AOSP HWUI 可通过 `debug.hwui.renderer` 选择 SkiaGL/SkiaVulkan，未设置时仍使用旧 OpenGL renderer | 看到 Skia 后端类不等于该版本默认启用 |
| Android 9 / API 28 | AOSP 将 `debug.hwui.renderer` 的默认值改为 `skiagl` | 不要把旧 `OpenGLRenderer` 类名套到 Android 9 以后的 AOSP 默认主路径 |
| Android 11 / API 30 | 主窗口路径开始使用 BLASTBufferQueue | buffer 与 SurfaceControl transaction 的关系更紧 |
| Android 12 / API 31 | FrameTimeline；`FrameMetrics` 增加 GPU duration 与 deadline | 可关联 App SurfaceFrame 和 DisplayFrame，并区分 CPU/GPU/显示责任 |
| Android 13 / API 33 | `Choreographer.FrameData` / `FrameTimeline` 公共 API；AGSL `RuntimeShader` | App 可获取候选帧时间线；Canvas 增加运行时 shader |
| Android 15 / API 35 | ARR 在支持 Android 15 QPR1 与相应 HAL 的设备上可用；ANGLE 成为可选的 GLES-on-Vulkan（把 OpenGL ES 调用映射到 Vulkan）层 | VSync 间隔和内容提交帧率不能再假设固定；GLES 后端需看设备选择 |
| Android 16 / API 36 | `Display.hasArrSupport()`、`getSuggestedFrameRate()`；`RuntimeColorFilter` / `RuntimeXfermode`；Vulkan 1.4 launch-device 要求 | App 能查询 ARR；AGSL 可用于滤镜与混合；设备能力仍需运行时查询 |
| Android 17 / API 37 | Jetpack WebGPU；GLES `prefer_angle` manifest 请求；`Display.getFrameRateVelocityMapping()` | WebGPU 增加现代 GPU 接口但仍需独立依赖；ANGLE 仍是偏好请求；滚动帧率可结合速度映射 |

表中“引入”表示平台或 API 的版本边界，不保证所有升级到该版本的设备拥有相同 GPU、显示 HAL、驱动能力和默认后端。

### Android 3.0–4.0：View 硬件加速成为标准路径

#### Android 3.0：HWUI 与显示列表

Android 3.0 以前，普通 View 的 `Canvas` 主路径使用 Skia 软件光栅化。应用仍可以通过 OpenGL ES 等 API 自行使用 GPU，所以“Android 2.x 所有图形都由 CPU 绘制”并不准确。

API 11 开始，Android 2D View 管线支持硬件加速。硬件加速 Window 中，View 的绘制操作会记录到显示列表，也就是一组可由渲染管线重复执行的绘制指令；未失效的 View 可以复用已有记录，位置、缩放、旋转或 alpha 等属性也可以作为 RenderNode 状态处理。RenderNode 是 HWUI 保存绘制指令与合成属性的节点。

这里要区分两件事：

- `View.draw()` / `onDraw()` 的 Java 调用负责描述绘制；
- GPU 何时把这些命令光栅化为像素，取决于 HWUI 后续回放、buffer 和驱动调度。

“调用 `canvas.drawRect()` 就立即执行一条 GL 命令”不符合显示列表模型。

API 11 同时提供 `View.setLayerType()`。`LAYER_TYPE_HARDWARE` 可以把稳定内容放入硬件层，便于后续做合成属性动画；它会占用图形内存。内容失效后仍要重新绘制并更新 layer，尺寸或渲染上下文变化时还可能重新分配，因此不能长期给所有 View 强制开启。

#### Android 4.0：默认值与 target API 有关

硬件加速从 API 11 可用，从 target API 14 起默认启用；target API 是应用声明自己已适配的 Android API 级别。以下两种情况下都可能出现软件 Canvas：

- 应用或 Activity 显式关闭硬件加速；
- 硬件加速 View 被绘制到 Bitmap 等软件 Canvas。

自定义 View 判断当前绘制路径时，应看 `Canvas.isHardwareAccelerated()`。`View.isHardwareAccelerated()` 只表示 View 附着的 Window 是否硬件加速；软件 Canvas 则由 CPU 把绘制结果写入 Bitmap 等内存目标。

### Android 4.1：Project Butter 建立 VSync 驱动的帧节拍

Project Butter 是 Android 4.1 面向交互流畅度的一组系统改进，它把输入、动画和 View traversal（测量、布局、绘制等 View 树遍历工作）放到统一的帧节拍中。`Choreographer` 在 API 16 成为公共 API，早期 AOSP 的回调队列如下：

```text
INPUT → ANIMATION → TRAVERSAL
```

Android 6.0 加入 COMMIT（帧遍历后的提交回调阶段），后续又加入 INSETS_ANIMATION（系统栏和输入法等 Insets 的动画阶段）。Android 17 的顺序如下：

```text
INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT
```

这些队列运行在 Choreographer 所属的 Looper 线程；Looper 是从消息队列中持续取出并分发任务的线程循环。应用主 ViewRoot 通常在主线程上，但 native engine（以 C/C++ 为主的渲染引擎）、SurfaceFlinger 客户端或其他 Looper 也可以拥有不同用途的 Choreographer。

#### `VSYNC-app` 与 `VSYNC-sf` 是调度事件

Perfetto 里的 `VSYNC-app`、`VSYNC-sf` 或相关预测轨道描述调度节拍。它们不应被逐条解释成“应用直接收到一次硬件中断”。现代系统会根据硬件 VSync 样本、显示模式与工作时长，预测 App 和 SurfaceFlinger 的唤醒时间。

旧 AOSP 资料常出现 `DispSync`，Android 17 的主线使用 Scheduler 与 `VsyncPredictor` 等组件。内部预测器跨版本持续变化，Trace 分析应关注本帧的 expected/actual timeline（预期与实际时间线）、deadline（完成截止时间）和 present（向显示设备提交本帧），不要靠预测器类名判断问题。

#### 三重缓冲解决的是流水线容量

Project Butter 将三重缓冲作为流畅性策略之一。它允许 Producer（生成 buffer 的一方）、GPU 与 Consumer（读取 buffer 的一方）在更多情况下并行推进，减少“前一块 buffer 未释放，下一帧无处可画”的概率。

三重缓冲不表示所有 Surface 永远只有三个固定 slot（BufferQueue 管理 buffer 的槽位），也不保证卡顿后无额外延迟。现代 BufferQueue 的 slot 数、dequeue 上限（Producer 可同时取走的 buffer 数）、异步模式和使用者约束会共同决定可用容量。Producer 持续快于显示消费时，队列会积压，FrameTimeline 可能标记 buffer stuffing（Producer 提交过快导致 buffer 堆积），用户看到的输入延迟也会增加。

### Android 5.0–6.0：RenderThread 接管 HWUI 的渲染执行

Android 5.0 的 `libs/hwui/renderthread/RenderThread.cpp` 已包含独立 RenderThread。普通硬件加速 View 的主线变成：

1. UI 线程执行输入、动画、measure、layout，并更新失效 View 的显示列表；
2. `ThreadedRenderer` / `HardwareRenderer` 通过 native `RenderProxy`（Java 渲染器与 native RenderThread 之间的代理）把帧任务交给 RenderThread；
3. `DrawFrameTask::syncFrameState()` 把 RenderNode 树、Surface 与资源状态同步到 RenderThread；
4. RenderThread 准备 Skia/GPU 工作，并 dequeue/queue App Window buffer；
5. GPU completion fence（表示 GPU 何时完成该 buffer 写入的同步对象）随 buffer 交给下游，SurfaceFlinger 再处理 transaction、latch（选定本帧使用的 buffer）和合成。

主线程与 RenderThread 不是严格首尾相接的两段。同步阶段必须处理本帧状态；在条件满足时，UI 线程可以在 RenderThread 完成本帧 GPU 工作前继续运行。不同 Android 版本与场景的阻塞点也不相同。

Perfetto 中 `DrawFrame` 很长只能说明 RenderThread 这段跨度较长。它可能包含：

- RenderThread 的 CPU 工作；
- RenderNode 或资源同步；
- shader（GPU 着色程序）/pipeline（图形 API 的渲染状态与处理阶段组合）准备与纹理上传；
- `dequeueBuffer`、fence 或 buffer back-pressure（下游迟迟不释放 buffer，反过来阻塞 Producer）；
- GPU 命令提交与 GPU 完成等待。

需要 GPU slices（Trace 中记录 GPU 工作的时间片）、completion fence、`FrameMetrics.GPU_DURATION`、设备 counter（硬件性能计数器）或 Android GPU Inspector（AGI）才能进一步确认 GPU 工作量。

#### RenderThread 动画有明确范围

`RenderNodeAnimator` 和基于 `CanvasProperty`（可由渲染线程更新的绘制属性）的部分动画可以在 RenderThread 上推进。普通 `ValueAnimator`、大部分 `ObjectAnimator` 和业务状态更新仍由 UI 线程的 Choreographer 驱动。看到 RenderThread 存在，不代表主线程卡住时所有动画都能继续。

Android 5.0 的 Choreographer 源码仍有 INPUT、ANIMATION、TRAVERSAL 三类回调；Android 6.0 增加 COMMIT。这个差异会影响阅读早期源码，但不改变 RenderThread 由 HWUI 自己管理这一事实。

### Android 7.0–10：观测 API 与 GPU 后端扩展

#### Android 7.0：FrameMetrics

API 24 增加 `Window.addOnFrameMetricsAvailableListener()` 和 `FrameMetrics`。`FrameMetrics` 按 Window 报告 UI/HWUI 一帧在各阶段的时间里程碑：

| 指标 | 主要含义 |
| --- | --- |
| `UNKNOWN_DELAY_DURATION` | UI 线程未及时开始处理帧的等待 |
| `INPUT_HANDLING_DURATION` | 输入回调 |
| `ANIMATION_DURATION` | 动画回调 |
| `LAYOUT_MEASURE_DURATION` | measure/layout |
| `DRAW_DURATION` | 记录或更新显示列表 |
| `SYNC_DURATION` | 显示列表与 RenderThread 同步 |
| `COMMAND_ISSUE_DURATION` | 向 GPU 发出绘制命令 |
| `SWAP_BUFFERS_DURATION` | 把帧 buffer 交给显示子系统 |
| `TOTAL_DURATION` | 从 intended VSync（该帧原本对应的 VSync）到 frame completed（应用侧完成该帧）的跨度 |

这些阶段可能重叠或并行，`TOTAL_DURATION` 不能由其他 duration 直接相加得到。`COMMAND_ISSUE_DURATION` 长也不等于 GPU execution 长；前者观察 CPU 侧发命令阶段。

API 31 又增加：

- `GPU_DURATION`：该帧在 GPU 上完成所需时间；
- `DEADLINE`：系统分配给 App 生产该帧的时间预算。

API 36 增加 `FRAME_TIMELINE_VSYNC_ID`，可与 compositor（SurfaceFlinger 等显示合成组件）的帧时间线数据关联。Listener 回调还会给出自上次回调以来丢弃的报告数量；`FrameMetrics` 对象会被重复利用，需要跨线程保存时应先复制。

#### Android 7.0：Vulkan 进入 NDK

Vulkan 从 API 24 可供 native 应用使用。它减少驱动隐式管理，把 command buffer（批量记录并提交 GPU 命令的对象）、资源同步和内存管理交给应用显式控制。代价是同步、生命周期和跨设备能力判断更复杂。

Vulkan API 可用，不表示 View/HWUI 一定使用 Vulkan。应用自带的 Vulkan renderer、HWUI SkiaVulkan、ANGLE-on-Vulkan 是三条不同路径。

#### Android 8.x–9：HWUI 转向 Skia GPU 后端

早期 HWUI 自己维护大量 OpenGL renderer 逻辑。Android 8.0/8.1 的 `Properties.cpp` 已识别 `skiagl` 和 `skiavk`，但 `debug.hwui.renderer` 未设置时仍回退旧 OpenGL renderer；Android 9.0 的同一文件把属性默认值明确改为 `skiagl`。绘制 API 仍是 View/Canvas/RenderNode，底层由 HWUI 直接管理 GL 的路径逐步转向 Skia GPU backend（实际连接图形 API 与驱动的后端实现）。

Android 17 的 `libs/hwui/pipeline/skia/` 仍有 `SkiaOpenGLPipeline`、`SkiaVulkanPipeline` 和公共 `SkiaGpuPipeline`。设备可以按产品配置、驱动和调试设置选择后端，不能按 Android 版本断言所有设备都走同一个 backend。

Skia 项目中的 Graphite 是新一代 GPU 后端研发方向。`android-17.0.0_r1` 的 HWUI pipeline 目录没有 Graphite pipeline 或默认启用路径，因此不将它列为 Android 平台里程碑。

#### Vulkan 版本要求要看 launch-device 条件

官方 Vulkan 实现文档给出的主要版本阶段是：

- Android 7：Vulkan 1.0；
- Android 9：Vulkan 1.1；
- Android 13：Vulkan 1.3；
- Android 16：Vulkan 1.4。

对设备要求的严谨说法是：64 位、非 low-memory（没有被标记为低内存设备）且以相应版本 launch 的设备，需要支持该版本要求的 Vulkan feature set（规定功能与限制的一组能力要求）。OTA 升级后的旧硬件不会因系统版本号自动获得新 GPU 能力。应用仍应查询 `FEATURE_VULKAN_HARDWARE_VERSION`、extension（扩展能力）、profile（成组定义的一套 Vulkan 能力）与 dEQP level（图形兼容性测试覆盖级别）。

`VP_ANDROID_16_minimums`、Android Vulkan Baseline Profile 和 Compatibility Definition 解决的问题不同：前两者描述成组的 Vulkan 能力，CDD（Compatibility Definition Document，兼容性定义文档）规定设备兼容要求，应用的最低 Vulkan version/extension 则由自己的渲染器决定。这里的 Vulkan Baseline Profile 与用于优化应用启动的 ART Baseline Profile 不是同一个概念。

### Android 11：BLAST 改变 buffer 与 transaction 的配合

Android 11 的 AOSP 已包含 `BLASTBufferQueue.cpp`，主窗口路径也开始迁移到 BLAST。BLAST 的名称来自 Buffer Layer And Surface Transactions，它把窗口 buffer 与几何属性等更新放进同一帧的 Surface transaction。

它没有删除 BufferQueue。BLAST 内部仍使用 Producer/Consumer buffer queue，并把 buffer update 变成 `SurfaceControl::Transaction` 的一部分，便于把 buffer、frame number（Producer 分配的递增帧号）、crop（裁剪范围）、transform（旋转、缩放等几何变换）和窗口几何状态按帧关系提交给 SurfaceFlinger。

现代 App Window 的简化路径是：

```text
RenderThread
  → Surface / BufferQueue producer
  → BLASTBufferQueue consumer
  → Transaction::setBuffer() / apply()
  → SurfaceFlinger FrontEnd
```

这条路径说明 BLAST 位于 App Producer 与 SurfaceFlinger transaction 之间。`queueBuffer()` 只表示 Producer 提交了一块 buffer；SurfaceFlinger 还要收到 transaction、检查 acquire fence（保护 buffer 读取时机的同步对象）、选择并 latch buffer，随后完成本轮显示合成。

Android 12 以后 BLAST 覆盖更多窗口与 Surface 场景，但旧 BufferQueue 类型和非 BLAST 队列继续存在。Perfetto 中应按 Layer、connection（Producer 与 Consumer 的队列连接）、transaction 和 buffer id 识别对象，不要只搜索某个固定 slice（Trace 中的一段带起止时间事件）名称。

### Android 12–14：FrameTimeline 把 App 帧与显示帧关联起来

#### Android 12：SurfaceFrame 与 DisplayFrame

FrameTimeline 在系统侧维护 App `SurfaceFrame` 与 SurfaceFlinger `DisplayFrame` 的 expected/actual timing（预期与实际时间）：

- `SurfaceFrame` 观察应用向某个 Layer 提交的一帧是否按选定时间线完成；
- `DisplayFrame` 观察 SurfaceFlinger/HWC 组织的一次显示帧是否按时 present；
- VSyncId / token 是跨轨道关联 App 帧和显示帧的标识；
- jank type 是系统根据时间关系给出的卡顿分类，用于区分 App deadline、SurfaceFlinger CPU/GPU、Display HAL、prediction error 和 buffer stuffing 等方向。

`Actual Timeline` 迟到是诊断入口。Perfetto 文档说明 App 帧结束会考虑 buffer post（应用提交 buffer）和 GPU completion；SurfaceFlinger 侧还可能因 Layer readiness（Layer 内容尚未满足合成条件）、client composition（由 RenderEngine/GPU 先生成 client target）、HWC 或 present 迟到。

私有 `TimelineItem`、`SurfaceFrame` 和 token 保存策略会随版本调整。应用开发者应依赖 Perfetto schema（Trace 数据字段及其关系的定义）、公共 API 和目标版本源码，不应复制某个旧版本的私有结构体定义当作长期接口。

#### Android 13：App 可以读取候选帧时间线

API 33 增加：

- `Choreographer.postVsyncCallback()`；
- `Choreographer.FrameData`；
- `Choreographer.FrameTimeline`；
- `getDeadlineNanos()`、`getExpectedPresentationTimeNanos()` 和 `getVsyncId()`。

一份 `FrameData` 可以包含多个候选 timeline，并标出平台偏好的 timeline；不同候选项代表系统允许应用瞄准的不同呈现时刻。native 应用有对应的 AChoreographer frame callback data API，可以为 Surface transaction 选择 frame timeline。

这些 API 提供时间目标，不保证应用一定在 deadline 前完成，也不替代 buffer/fence/present 证据。

#### Android 13–16：AGSL 扩展 Canvas 效果

Android 13 的 `RuntimeShader` 让应用用 Android Graphics Shading Language（AGSL）编写运行时 shader，并作为 Canvas `Shader` 使用。Android 16 增加 `RuntimeColorFilter` 和 `RuntimeXfermode`，把 AGSL 扩展到颜色过滤和 source/destination（新绘制内容与目标中已有内容）混合。

AGSL 属于 Canvas/HWUI 效果接口。复杂 shader、离屏 layer、模糊或多个 render pass（围绕一个渲染目标组织的一组 GPU 绘制）的成本仍由实际内容与 GPU 决定，API 版本本身不提供性能保证。

### Android 15–16：ARR、ANGLE 与 Vulkan 1.4

#### ARR 改变了“固定 VSync 间隔”的假设

ARR 从 Android 15 开始提供，官方文档把可用条件写为支持相应 HAL 且运行 Android 15 QPR1 及以上。它可以让显示刷新节奏按内容 render rate（应用产生新内容的帧率）以离散的 VSync 步进变化，减少不必要的高刷新率驻留和 mode switch（在不同显示模式之间切换）。

Android 16 / API 36 增加 `Display.hasArrSupport()` 和 `getSuggestedFrameRate()`。应用还可以通过 View、Surface、ANativeWindow 的 frame-rate API 提交帧率偏好。系统会综合同一显示上的多个 View、Layer、系统 UI、触摸和功耗策略；API 调用成功只表示请求已被接收，不保证显示器立刻切到指定 Hz。

在 ARR 设备上看到 8.33 ms、16.67 ms 或更长 VSync 间隔变化时，应检查选定时间线、deadline、requested frame rate（应用请求的帧率）和 active display mode（当前生效的显示模式），再判断是否异常。

#### ANGLE 是可选 GLES-on-Vulkan 路径

Android 15 起，ANGLE 作为可选兼容层把 OpenGL ES（GLES）调用映射到 Vulkan。它能改善兼容性，并可能改变 CPU/GPU 工作分布，但性能结果取决于设备、驱动和负载。

GLES 应用、原生 Vulkan 应用和 HWUI 页面不能混为一个类型。ANGLE 的启用也不代表应用源码已经迁移到 Vulkan API。

#### Android 16 launch device 的 Vulkan 1.4

设备以 Android 16 及更高版本 launch，并满足 64 位、非 low-memory 等条件时，需要支持 Vulkan 1.4。GPU 驱动由 SoC 厂商或 IHV（独立硬件供应商）提供，framework 版本不能替代运行时 capability（设备实际能力）查询。

### Android 17：WebGPU、ANGLE 偏好与滚动帧率映射

#### WebGPU

Android 17 的发布说明把 WebGPU 列为图形新能力。公开接口来自独立发布的 Jetpack `androidx.webgpu:webgpu`，当前核验版本为 `1.0.0-alpha05`，不属于 `android.*` framework API；alpha 表示仍在早期预览阶段，接口可能变化。该库提供 Kotlin/Java 绑定，并以比 Vulkan 更高层的对象组织工作：adapter 表示可选 GPU 实现，device 是应用取得的逻辑 GPU 设备，queue 接收提交，command buffer 保存待执行命令，WGSL 是 WebGPU Shading Language。

WebGPU 不会让 View/Compose、WebView 或现有 GLES 应用自动换后端。分析使用 WebGPU 的应用时，应把它按独立 GPU API 和工作提交路径处理：离屏 compute（通用 GPU 计算）只跟踪 buffer、texture 与 queue；绘制到屏幕时，再沿 `GPUSurface` 的 current texture（当前可供渲染的一张交换链图像）、`present()`、目标 `ANativeWindow`、BufferQueue 和最终 SurfaceFlinger Layer 追踪。

#### `prefer_angle` 只表达偏好

Android 17 起，游戏可以在 manifest（应用清单文件）中请求优先使用 ANGLE 作为 GLES driver。下面配置的作用只是声明偏好：

```xml
<application android:appCategory="game">
    <meta-data
        android:name="com.android.graphics.driver.prefer_angle"
        android:value="true" />
</application>
```

平台无法使用 ANGLE 时会回到厂商 GLES driver。排查问题要记录实际 renderer/driver，不能只看 manifest。

#### API 37 的 frame-rate/velocity mapping

`Display.getFrameRateVelocityMapping()` 返回当前 Display 的滚动速度阈值与可行 frame rate 组成的只读、非空映射。例如一个点可以表达“速度超过 300 dp/s（每秒移动 300 个密度无关像素）时使用 120 fps”。官方契约主要面向 RecyclerView、ScrollView、AbsListView、NestedScrollView 等 fling（手指离开后继续惯性滚动）场景。设备从内屏切到外屏，或收到 `DisplayListener.onDisplayChanged()` 后，需要针对当前 Window 所在 Display 重新查询。

这些点是 display-specific（只适用于当前 Display）的策略输入，系统不会据此替 App 自动完成帧率切换。调用方仍要按速度选择映射点，并通过 View、Surface 或其他 frame-rate API 表达请求；列表也仍需在每个选定 deadline 前完成 UI、RenderThread、GPU 与 buffer 提交。

#### Android 17 的标准 HWUI 主线

回到当前版本，普通 View/Compose App Window 可按以下对象分析：

```text
Choreographer / UI Thread
  → View traversal + RenderNode display list
  → HardwareRenderer / RenderProxy
  → RenderThread / DrawFrameTask / CanvasContext
  → SkiaOpenGL or SkiaVulkan pipeline
  → App Window BLAST buffer transaction
  → SurfaceFlinger FrontEnd RequestedLayerState / LayerSnapshot
  → CompositionEngine / HWComposer / Composer3
  → display present
```

页面有 `SurfaceView`、`TextureView`、视频、Camera、WebView、Flutter、游戏或 React Native 时，要先确认 Producer、Consumer 与最终 Layer。`SurfaceView` 常有独立 child Surface；`TextureView` 会先被宿主 HWUI 采样进 App Window；框架名无法替代 Surface 拓扑。

这里的 child Surface 是挂在宿主窗口层级之下、拥有自己 buffer 提交路径的 Surface。主线末端的 CompositionEngine 为每个 Display 组织可见 Layer，HWComposer 再通过 Composer HAL 与显示硬件协商并 present。

### 怎样用版本信息读 Perfetto

#### 1. 记录设备与构建信息

记录：

- `Build.VERSION.SDK_INT`、build fingerprint（唯一描述系统构建版本的字符串）和 vendor image（厂商分区的软件镜像）；
- app target SDK、图形 API 与 renderer（实际使用的渲染器/驱动名称）；
- display mode、刷新率、ARR 支持；
- 页面里的 Window、SurfaceView、TextureView 和其他独立 Surface；
- Perfetto/Android Studio/AGI 版本与采集配置。

Track 是 Perfetto 中按线程、计数器或数据源组织的时间轴，slice 是其中带起止时间的事件；atrace 是 Android 代码写入这类 Trace 事件的传统插桩接口。Track 名和 atrace slice 属于实现细节，厂商也会增加或改名。找不到旧教程中的名字，不代表对应机制不存在。

#### 2. Android 5.0+ 分开 UI 与 RenderThread

UI 线程慢时看 input、animation、traversal、measure/layout 和 display-list record。RenderThread 慢时继续分辨 CPU、资源、buffer、fence、GPU submit 和 completion。不要用“哪个 slice 最长”直接给出 GPU/CPU 结论。

#### 3. Android 11+ 同时看 BLAST、BufferQueue 和 transaction

需要回答四个问题：

1. Producer 何时 queue 哪个 frame number；
2. BLAST 何时把 buffer 放入哪次 transaction；
3. SurfaceFlinger 何时认为 transaction ready 并 latch；
4. 对应 DisplayFrame 何时 present。

`BufferTX - <layerName>` 只表示 SurfaceFlinger server 侧 pending buffer transaction（尚待处理的 buffer transaction）数量发生变化，不表示屏幕已经显示。

#### 4. Android 12+ 用 FrameTimeline 锁定帧

选中目标 janky `SurfaceFrame`（被 FrameTimeline 判定为卡顿的应用帧）后，再跟到对应 `DisplayFrame`。App deadline missed、SF deadline missed 和 Display HAL 问题需要不同证据。多 Surface 页面不能只看宿主 App Window 的一条 timeline。

#### 5. Android 15+ 分开渲染帧率与显示刷新率

App 可能以 30 fps 更新，显示以 60/90/120 Hz 或 ARR 步进工作；多个 Layer 也可能按不同 cadence（内容更新与显示刷新的节奏关系）运行。帧是否准时应按选定的 timeline 和 deadline 判断，不能固定拿 16.67 ms 作为所有设备、所有帧的预算。

### API、平台实现与设备能力是三层约束

| 层次 | 例子 | 正确检查方式 |
| --- | --- | --- |
| 公共 API | `FrameMetrics`、`FrameTimeline`、WebGPU、`hasArrSupport()` | 看 API level、feature flag（可动态启停功能的开关）与官方契约 |
| AOSP 平台实现 | RenderThread、BLAST、SurfaceFlinger FrontEnd、Skia pipeline | 看目标 tag（源码版本标签）的源码和系统属性 |
| 设备能力 | GPU/Vulkan extension、ANGLE、HWC plane、ARR HAL、counter | 看运行时查询、dumpsys（系统服务状态快照）、driver 与目标设备 Trace |

“Android 17 支持某 API”只覆盖第一层；“AOSP 有某 pipeline”只覆盖第二层。具体手机是否启用、性能如何，仍由第三层决定。

### Kernel 与厂商边界

kernel 源码锚点是 `android17-6.18-2026-06_r6`。其中 `drivers/dma-buf/dma-buf.c` 管理可在设备和进程间共享的 buffer 对象，`dma-fence.c` 定义异步任务的完成依赖，`sync_file.c` 把 fence 封装成可跨进程传递和等待的文件描述符；通用 kernel 还提供线程调度、内存回收和频率框架等基础机制。

HWUI backend、Vulkan/GLES driver、GPU job（提交给 GPU 的一组工作）调度、图形内存分配、DPU（显示处理单元）/HWC plane 与 ARR HAL 含有大量厂商实现。一个 framework 版本里程碑不保证 vendor driver 同步采用相同策略。Kernel fence 只能说明异步依赖是否完成；要解释迟到原因，还需找到 fence owner（创建或负责把该 fence 标记为完成的组件）、提交者和对应硬件工作。

### 源码与官方资料

#### 历史版本锚点

- [Android 5.0 `RenderThread.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-5.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)：RenderThread 已进入 HWUI。
- [Android 5.0 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-5.0.0_r1/core/java/android/view/Choreographer.java)：INPUT、ANIMATION、TRAVERSAL。
- [Android 6.0 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-6.0.0_r1/core/java/android/view/Choreographer.java)：COMMIT 回调阶段。
- [Android 8.0 `Properties.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-8.0.0_r1/libs/hwui/Properties.cpp)、[Android 9.0 `Properties.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-9.0.0_r1/libs/hwui/Properties.cpp)：SkiaGL/SkiaVulkan 可选路径与 SkiaGL 默认值的版本分界。
- [Android 11 `BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-11.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：BLAST 初期实现。

#### Android 17 / `android-17.0.0_r1`

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)：当前回调顺序、FrameData 与 FrameTimeline。
- [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：当前指标、GPU duration、deadline 与 VSyncId。
- [`Display.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)、[`FrameRateVelocityPoint.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameRateVelocityPoint.java)：ARR 查询、建议帧率与速度映射的 API 37 实现。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：UI/RenderThread 同步、绘制和 buffer 提交。
- [`SkiaOpenGLPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp)、[`SkiaVulkanPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)：当前 HWUI GPU backend。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：buffer 与 transaction。
- [SurfaceFlinger `FrameTimeline.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.h)、[`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：SurfaceFrame、DisplayFrame 与 jank classification。
- [SurfaceFlinger FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrontEnd/)、[`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)：RequestedLayerState、LayerSnapshot、validate/present。

#### Kernel / `android17-6.18-2026-06_r6`

- [`dma-buf.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c)：共享 buffer 对象与设备 attachment/map（设备附着与地址映射）边界。
- [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)、[`sync_file.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：异步完成依赖与 `sync_file` fd（文件描述符）。

#### 官方文档

- [Hardware acceleration](https://developer.android.com/develop/ui/views/graphics/hardware-accel)
- [FrameMetrics](https://developer.android.com/reference/android/view/FrameMetrics)
- [FrameTimeline in Perfetto](https://perfetto.dev/docs/data-sources/frametimeline)
- [Choreographer.FrameTimeline](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline)
- [Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android 16 graphics features](https://developer.android.com/about/versions/16/features#graphics)
- [Implement Vulkan](https://source.android.com/docs/core/graphics/implement-vulkan)
- [Vulkan and ANGLE on Android](https://developer.android.com/games/develop/vulkan/overview)
- [Android 17 features and changes](https://developer.android.com/about/versions/17/summary)
- [WebGPU for Android](https://developer.android.com/develop/ui/views/graphics/webgpu)、[AndroidX WebGPU releases](https://developer.android.com/jetpack/androidx/releases/webgpu)、[`GPUSurface`](https://developer.android.com/reference/androidx/webgpu/GPUSurface)
- [Display API](https://developer.android.com/reference/android/view/Display)


## 常见误区

### “BLAST 已经替代 BufferQueue”

BLAST 使用并管理 BufferQueue，把 buffer update 纳入 Surface transaction。现代系统里两者同时存在。

### “RenderThread 的 DrawFrame 长就是 GPU 慢”

`DrawFrame` 跨度包含 RenderThread CPU、资源、buffer、fence 和 GPU 相关阶段。需要 GPU completion 或直接 GPU 证据。

### “Android 16/17 设备都用 SkiaVulkan 或 Graphite”

Android 17 AOSP 提供 SkiaOpenGL 与 SkiaVulkan pipeline，产品选择与设备配置有关；当前 tag 没有 HWUI Graphite pipeline。

### “Vulkan 1.4 要求适用于所有升级设备”

launch-device 条件、64 位与 low-memory 条件决定兼容要求。旧设备 OTA 后仍以硬件和驱动上报为准。

### “ARR 让 VSync 随意变化”

ARR 按设备支持情况、各 View/Surface 提交的帧率偏好和离散步进工作。间隔变化可以是正常策略，也可能是 mode switch 或调度问题，需要结合 display mode 与 FrameTimeline。

### “FrameMetrics 可以解释 SurfaceFlinger”

FrameMetrics 是 App Window 的渲染里程碑。SurfaceFlinger、HWC 和多 Layer 显示问题需要 Perfetto、layer state、composition type 与 present/fence 证据。
