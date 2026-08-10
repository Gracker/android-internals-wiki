---
title: "Android 渲染架构全景"
chapter: "2.1"
section: "2.1"
applicable_versions: "Android 3.0 (API 11) - Android 17 (API 37)"  # 版本演进从 3.0 开始,核心内容覆盖 API 11-37
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1: View/ViewRootImpl/Choreographer/ThreadedRenderer/HardwareRenderer/BaseRecordingCanvas, HWUI RenderNode/DrawFrameTask/CanvasContext/Properties/Skia pipelines, BufferQueue/BLASTBufferQueue, SurfaceFlinger FrontEnd/Scheduler/HWComposer/HWC2/ComposerHal/RenderEngine; kernel android17-6.18-2026-06_r6 boundary; Writer rendering_pipelines S01/S02"
confidence: high
drafted_date: "2026-03-30"
polish_count: 2
polish_date: "2026-04-09"
polish_by: "task2b-polish"
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/graphics/overview"
  - type: official
    path: "https://source.android.com/docs/core/graphics/unsignaled-buffer-latch"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: blog
    path: "https://www.yuque.com/docs/share/0a92fc0e-185c-4f03-a088-458bb9f3913f"
  - type: blog
    path: "https://mp.weixin.qq.com/s?__biz=MzkxMDc4NTc0OQ==&mid=2247483817&idx=1&sn=f280eb86b50d803c89113ff2c7bb105b"
  - type: research
    path: "AOSP 源码分析 frameworks/base/core/java/android/view"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ThreadedRenderer.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/HardwareRenderer.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BaseRecordingCanvas.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/RenderNode.h"
  - type: aosp
    path: "frameworks/base/libs/hwui/RenderNode.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/CanvasContext.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/Properties.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaPipeline.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueCore.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueProducer.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueConsumer.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BLASTBufferQueue.cpp"
  - type: aosp
    path: "frameworks/native@android-11.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Layer.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrontEnd/"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DisplayHardware/ComposerHal.h"
  - type: aosp
    path: "frameworks/native/libs/renderengine/"
  - type: research
    path: "Writer/rendering_pipelines/S01_rendering_types_overview.md"
  - type: research
    path: "Writer/rendering_pipelines/S02_aosp_standard_type.md"
tags: ['rendering', 'hwui', 'skia', 'surfaceflinger', 'gpu', 'triple-buffering', 'rendering-pipeline', 'bufferqueue', 'vsync', 'displaylist', 'rendernode']
related_chapters: ["2.2", "2.3", "2.4", "2.5", "2.6", "2.10"]
review_round: 7
task9_result: "auto-fixed"
task9_reviewed_date: "2026-07-11"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-11T19:30:22+08:00"
task2b_fixed_by: openclaw-task2b
review_notes_4: "2026-04-25 task6 re-review (round 4): pass-light-edit after task2b fix. L1: no banned words. L2: opening/structure/flow all good. 1 minor wording fix (手工→手动). No B-class issues."
review_notes_5: "2026-04-25 task6 re-review (round 5): pass-light-edit. L1: 禁用短语修复 1 处；AI句式 3→1 in 03-metrics. 01-rendering-overview and 05-leakcanary clean. No B-class issues across all 3 chapters."
task9_review_notes: "2026-07-11 Task9 idle audit auto-fix: P0 源码锚点 3 类已修复（BufferItemConsumer 签名、BaseRecordingCanvas 路径/代码、RenderEngine 路径）；无 queue pending，回到 Task6 复审。"
last_task9_review_log: "logs/deep-review/2026-07-11-19-audit.md"

status: "finalized"
reviewed_by: "openclaw-task6"
reviewed_date: 2026-07-11
task6_result: pass-light-edit
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
task2b_state: "fixed"
last_task6_at: "2026-07-11T20:10:00+08:00"
last_task6_review_log: "logs/review/2026-07-11-20-review.md"
task2b_result: "fixed"
task6_review_notes: "2026-06-20 12:07 Task6 revisiting-review：Task9 idle audit auto-fix（P0: Android 16 Vulkan CDD 版本断言错误，3 处正文修正）写作质量复审通过；L1 禁用词/高频词/结构性元叙述 0 命中；L2 开头/节奏/结构/读者视角全部通过；outline 锚点全覆盖；无新增 L3/L4 回炉项；task9_result=auto-fixed → pass-tech-review，queue.json 无 pending，自动晋升 finalized。"
task6_review_notes_2: "2026-07-11 20:10 Task6 revisiting-review (round 7)：Task9 idle audit auto-fix（P0: BufferItemConsumer acquireBuffer 签名、BaseRecordingCanvas 录制入口/路径、RenderEngine 源码路径，3 类源码锚点已修正到 android-17.0.0_r1）写作质量复审通过。L1：禁用词/高频词/结构性元叙述 0 命中；中英文间距修复 1 处（一个wrap_content→一个 wrap_content）。L2：开头（Perfetto Trace 场景引入）/节奏（长短句交替自然）/结构（7 阶段管线主线清晰）/读者视角（Trace 观察点贯穿全文）全部通过。outline 锚点 5/5 全覆盖，扩展 3/3 全覆盖。L3/L4 无新增回炉项。task9_result=auto-fixed（P0 已修复）→视为 pass-tech-review，queue.json 中 section 2.1 无 pending 条目，自动晋升 finalized。"
last_task6_audit: "2026-07-11"
last_task9_audit: "2026-07-11"
last_task9_audit_at: "2026-07-11T19:30:22+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-11-19-audit.md"
last_task9_audit_result: "auto-fixed-p0-source-anchors"
task9_audit_notes: "2026-07-11 Task9 idle audit auto-fix: 按 android-17.0.0_r1 修正 BufferItemConsumer acquireBuffer 签名、BaseRecordingCanvas 录制入口、RenderEngine 源码路径，并把 SurfaceFlinger/HWUI/BufferQueue 验证锚点更新到 Android 17；回到 Task6 复审。"
p0: 3
p1: 0
p2: 0
updated_by: "openclaw-task9"
updated_date: "2026-07-11"
task2b_fixed_at: "2026-06-01T04:50:00+08:00"
task2b_fix_notes: "2026-05-31 Task2B main: 修复 Task9 2026-05-26 P1 版本差异；拆开 Android 3.0 早期 HWUI/DisplayList 与 Android 5.0 RenderNode/RenderThread 分工。"
last_task2b_at: "2026-06-01T04:50:00+08:00"
task2b_notes: "2026-06-01 Task2B main: 修复 Task9 P95：BufferQueue acquireBuffer 伪代码改为真实签名引用，补充三缓冲显示延迟副作用，复核 Android 3.0 DisplayList 与 Android 5.0 RenderNode/RenderThread 版本边界。"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_new_rework: false
review_type: "task6-writing-quality-review"
last_task9_autofix_at: "2026-07-11"
last_task2b_verifier_at: "2026-06-01T07:30:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-01-07-task2b-verifier.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-11
---

# Android 渲染架构全景

一次触摸已经改变了 View 的状态，下一帧却没有按时出现在屏幕上。问题可能出在主线程遍历、RenderThread、GPU、应用侧 BufferQueue、SurfaceFlinger，甚至显示合成阶段。只看一段 `draw` 耗时，很难判断阻塞发生在哪里。

分析这类问题需要先回答两个问题：

1. 谁在生产图形缓冲区，缓冲区交给了哪一个 Surface？
2. 当前观察到的事件位于“生成内容”“提交缓冲区”“系统合成”还是“显示呈现”阶段？

现行架构以 Android 17 / API 37 / `android-17.0.0_r1` 为源码基线，从普通应用窗口出发，说明 View、HWUI、BufferQueue、BLAST、SurfaceFlinger、Hardware Composer（HWC）和显示设备之间的关系。历史部分保留 Android 3.0 到 Android 17 的演进边界。内核对象只用于解释同步与共享缓冲区，基线为 `android17-6.18-2026-06_r6`。

## 1. 输出拓扑分类

“Android 渲染”包含多种数据路径。它们都可能出现在同一个窗口中，却不一定共享同一个生产者或同一条 BufferQueue。

| 内容类型 | 主要生产者 | 提交目标 | 常见特征 |
| --- | --- | --- | --- |
| 普通 View / Compose UI | 应用进程中的 HWUI | 宿主 App Window 的 Surface | 主线程生成 UI 状态和绘制记录，RenderThread 驱动 Skia 绘制 |
| `TextureView` 内容 | 相机、解码器、OpenGL 等生产者 | `SurfaceTexture`，再作为 View 树纹理参与 HWUI 绘制 | 外部内容最终进入宿主窗口缓冲区 |
| `SurfaceView` 内容 | 相机、解码器、游戏引擎等生产者 | 独立 Surface / Layer | 内容有独立缓冲区队列，SurfaceFlinger 与宿主窗口一起合成 |
| 视频解码 | Codec / vendor 组件 | Surface 对应的 BufferQueue | 生产节拍、色彩格式和保护内容约束与普通 UI 不同 |
| 游戏或自建引擎 | EGL / Vulkan 应用代码 | NativeWindow / Surface | 应用自行组织渲染循环与 GPU 工作 |
| WebView / Flutter 等框架 | 框架自身加上 HWUI 或独立 Surface | 取决于具体实现和模式 | 不能仅凭控件名称推断缓冲区拓扑 |

“标准应用窗口路径”指普通 View 或 Compose 内容经过宿主 App Window 的 HWUI Surface 输出。它不包括 `SurfaceView` 的独立内容生产路径，也不能概括所有 Flutter、WebView、Camera 或视频场景。

若 Perfetto 中出现多条 BufferQueue 或多个 SurfaceFlinger Layer，应按生产者和 Surface 归属拆分，再分析每条路径的时序。

## 2. 标准应用窗口的一帧经过哪些阶段

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

各阶段并非全部按单线程串行执行。主线程、RenderThread、GPU、SurfaceFlinger 和显示硬件可以重叠处理不同帧。分析时必须保留帧号、VSync 周期和栅栏（fence）依赖，不能只把各段耗时相加。

### 2.1 一帧至少跨越三个调度域

| 调度域 | 代表线程或组件 | 主要职责 |
| --- | --- | --- |
| 应用 UI | `main` / `ViewRootImpl` / `Choreographer` | 处理输入、动画、布局和绘制记录 |
| 应用渲染 | `RenderThread` + GPU 队列 | 同步 RenderNode、执行 Skia 管线、产生窗口缓冲区 |
| 系统显示 | SurfaceFlinger / HWC / 显示设备 | 选择缓冲区、确定合成策略并呈现 |

“应用主线程已经画完”通常只说明 UI 侧工作到达某个提交边界。它不说明 GPU 已完成，也不说明 SurfaceFlinger 已经 latch，更不说明像素已经开始被面板扫描。

## 3. 主线程：从状态变化到 Traversal

### 3.1 `scheduleTraversals()` 合并同一轮请求

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

### 3.2 Choreographer 的回调顺序

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

### 3.3 `performTraversals()` 不等于每帧完整执行三大流程

`ViewRootImpl.performTraversals()` 是窗口级遍历的核心入口。根据布局请求、尺寸、可见性、Surface 状态和脏区域，它可能执行：

- 测量（measure）：计算 View 所需尺寸；
- 布局（layout）：确定 View 在父容器中的位置；
- 绘制（draw）：录制或更新需要重绘的内容。

三者都有条件判断。Perfetto 出现 `performTraversals` slice 时，不能直接断言该帧完整测量、布局和绘制了整棵 View 树。

#### Measure：父子双方参与尺寸协商

父 View 通过 `MeasureSpec` 把尺寸约束传给子 View：

| 模式 | 含义 |
| --- | --- |
| `EXACTLY` | 尺寸已确定，子 View 应使用该尺寸 |
| `AT_MOST` | 子 View 可以选择不超过上限的尺寸 |
| `UNSPECIFIED` | 父容器没有给出这一方向的上限 |

自定义 View 需要依据内容、建议最小尺寸、padding 和 `MeasureSpec` 调用 `setMeasuredDimension()`。测量次数增加可能来自嵌套权重、父容器的多轮协商、窗口尺寸变化或布局请求传播，不能仅凭一次 `AT_MOST` 判断根因。

#### Layout：确定位置，不自动裁剪内容

Layout 通过 `layout(l, t, r, b)` 和 `onLayout()` 确定子 View 的边界。子 View 的位置和尺寸由父容器决定，但内容是否被裁剪属于绘制阶段行为，还会受 `clipChildren`、`clipToPadding`、outline、显式 clip 和变换影响。

因此，“子 View 位于父 View 边界内”和“超出父边界的像素不会显示”是两个不同判断。

#### Draw：生成绘制记录

硬件加速窗口中，`View.draw()` 及其相关分发逻辑通过 `RecordingCanvas` 记录绘制命令。它们描述“画什么”和状态变换，通常不在主线程当场把最终像素光栅化到显示缓冲区。

常见绘制顺序如下：

1. 绘制背景；
2. 保存或处理滚动、裁剪等状态；
3. 调用 `onDraw()` 绘制自身内容；
4. `dispatchDraw()` 绘制子 View；
5. 绘制前景、滚动条等装饰。

具体分支受 View 标志、缓存、动画和硬件加速状态影响，不应把这份顺序当成所有 View 都固定执行的调用清单。

### 3.4 `invalidate()` 与 `requestLayout()` 的边界

| API | 主要表达 | 可能触发的工作 |
| --- | --- | --- |
| `invalidate()` | 某个区域的显示内容失效 | 标记脏区域，调度绘制；不主动表达尺寸变化 |
| `requestLayout()` | 当前 View 的测量结果或位置可能失效 | 向父级传播布局请求，并调度 traversal |

两者最终都可能通过 `ViewRootImpl` 汇入下一轮 traversal。`requestLayout()` 的传播和框架优化会影响实际遍历范围，所以“每次调用必然完整重测整棵树”也不准确。

排查主线程问题时，建议同时看：

- 调用频率：是否在循环或动画中反复请求布局；
- View 树规模：深度、宽度以及复杂容器；
- 自定义 `onMeasure()`、`onLayout()`、`onDraw()` 的耗时；
- 是否发生窗口 relayout、Insets 或配置变化；
- traversal 相对 VSync 的开始时间和结束时间。

## 4. HWUI：从绘制命令到 RenderThread

### 4.1 RenderNode 保存可复用的绘制记录

硬件加速的 View 树会用 `RenderNode` 表示可独立更新和复用的渲染节点。主线程把 Canvas 操作录制为 DisplayList，后续帧若某个节点内容没有失效，HWUI 可以复用已有记录。

这并不意味着未失效节点完全没有成本。属性同步、树遍历、裁剪、合批、资源生命周期和最终 GPU 工作仍可能涉及该节点。DisplayList 主要减少重复执行 Java 绘制代码和重复生成绘制命令的成本。

Android 17 的原生 `RenderNode` 同时维护当前状态与暂存（staging）状态。与 DisplayList 同步有关的字段和方法包括：

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

主线程更新 staging 数据，RenderThread 在同步阶段把需要的变化推入渲染侧状态。这个双阶段模型能减少主线程直接操作渲染线程当前状态所需的竞争。

### 4.2 `RecordingCanvas` 负责录制

Java 层 `RecordingCanvas` 的绘制 API 最终进入 `BaseRecordingCanvas` 等实现。以绘制 RenderNode 为例，Android 17 的 native 入口由框架内部桥接完成。阅读源码时要区分：

- Java Canvas API；
- JNI/native 方法；
- Skia/HWUI DisplayList 操作；
- RenderThread 上的执行。

看到 `drawRect()`、`drawBitmap()` 或 `drawRenderNode()` 返回，只能说明相应调用已经完成。对于硬件加速 Canvas，最终 GPU 执行通常尚未完成。

### 4.3 `syncAndDrawFrame()` 是 UI 到 RenderThread 的提交边界

`ThreadedRenderer` 通过 `HardwareRenderer` 把帧信息提交给 native 渲染代理，核心入口名为 `syncAndDrawFrame()`。它连接两类工作：

1. UI 线程准备帧信息和 RenderNode 变化；
2. RenderThread 同步状态并安排绘制。

`frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp` 中的 `DrawFrameTask::run()` 会执行帧状态同步，并按条件决定何时解除 UI 线程等待；随后由 `CanvasContext` 执行绘制和缓冲区交换。

`syncAndDrawFrame()` 的返回值或切片结束，不能当作 GPU 完成、BufferQueue 消费完成或屏幕呈现完成的证据。

### 4.4 RenderThread 和 GPU 允许并行

RenderThread 负责准备并提交 GPU 命令。GPU 在独立队列中执行这些命令，因此可能出现：

```text
主线程准备 Frame N+1
RenderThread 提交 Frame N
GPU 执行 Frame N-1
SurfaceFlinger 合成更早的一帧
```

这种重叠是图形管线维持吞吐量的基础。“某条 GPU 轨道超过一个刷新周期，当前帧就一定掉帧”不是充分判断。需要结合依赖栅栏、队列深度和 FrameTimeline，确认该 GPU 工作是否阻塞目标帧的截止时间（deadline）。

### 4.5 SkiaGL、SkiaVulkan 与渲染后端

Android 17 的 HWUI 包含 Skia OpenGL 与 Skia Vulkan 管线：

- `SkiaOpenGLPipeline`
- `SkiaVulkanPipeline`

`Properties::peekRenderPipelineType()` 会结合构建时的 `use_vulkan()` 结果和 `debug.hwui.renderer` 属性选择 `skiavk` 或 `skiagl`。这是一项设备、构建配置和调试属性共同参与的选择，不能概括成“Android 17 所有设备都默认使用 Vulkan”。

Vulkan 与 OpenGL ES 的 CPU 开销、驱动行为、着色器编译、内存压力和功耗表现依赖具体设备及负载。后端名称本身不能证明某一帧更快。

## 5. BufferQueue：共享缓冲区，而非整帧像素拷贝

### 5.1 Producer 与 Consumer

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

`queueBuffer()` 成功只说明生产者把缓冲区置为可消费状态。它没有证明 SurfaceFlinger 已经锁存，更没有证明显示设备已经呈现。

### 5.2 槽位状态

BufferQueue 中常见的槽位状态为：

| 状态 | 含义 |
| --- | --- |
| `FREE` | 当前可供生产者选择 |
| `DEQUEUED` | 已由生产者取得，正在写入或准备 |
| `QUEUED` | 已提交，等待消费者获取 |
| `ACQUIRED` | 已由消费者获取，尚未释放 |

生产者无法无限制地 `dequeueBuffer()`。最大已 dequeue 数、最大已 acquire 数、异步模式、消费者是否会阻塞以及当前可用槽位共同决定它是否需要等待。

Android 17 的 `BufferQueueCore` 初始配置中可看到最大 acquired 和 dequeued 数的默认值，但实际最大缓冲区数量由运行时条件计算。它不是全系统固定的三个缓冲区。

### 5.3 “三缓冲”要按队列状态理解

双缓冲或三缓冲常被用来描述生产、消费和显示可以同时占用多个缓冲区，但 Android 的 BufferQueue 深度具有动态性：

- Surface 尺寸、格式或使用属性（usage）改变会触发重新分配；
- 最小未释放数量与 consumer 配置有关；
- async / shared buffer 等模式会改变规则；
- dequeue/acquire 上限会限制可并行持有的缓冲区；
- fence 未完成时，槽位即使逻辑上可流转也可能还不能安全复用。

多一个可用缓冲区有时能减少生产者因暂时无槽位而停顿，但队列持续堆积也可能增加输入到显示的延迟。不能把“三缓冲”写成必然降低卡顿，或必然增加一整帧延迟。

### 5.4 背压比“丢弃所有多余帧”更准确

应用生产速度超过消费者处理速度时，常见结果包括：

- `dequeueBuffer()` 等待可用槽位；
- 应用被 VSync 节奏约束，无法持续无界生产；
- 队列中的缓冲区在特定模式下按规则被替换或跳过；
- SurfaceFlinger 选择满足 latch 条件的缓冲区；
- Choreographer 检测缓冲区堆积（buffer stuffing）并调整恢复节奏。

不同 Surface 类型、显示模式（present mode）和 BufferQueue 配置会改变行为。没有这些条件时，不应笼统写成“多画的帧都会被丢掉”。

## 6. BLAST：把窗口缓冲区与 SurfaceControl 事务对齐

### 6.1 标准 App Window 中的 BLASTBufferQueue

在现代 Android 的普通应用窗口路径中，应用进程内的 `BLASTBufferQueue` 承担应用侧 BufferQueue consumer 角色，并把取得的缓冲区包装进 `SurfaceComposerClient::Transaction`。它通过 `setBuffer()` 把栅栏、帧号和 release callback 等信息提交给 SurfaceFlinger。

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
- BLAST 获取缓冲区后，还要经过事务应用、Layer 状态更新、锁存（latch）、合成与显示提交（present），不能把 BLAST 事件当成显示完成点。

### 6.2 `BufferTX - <layerName>` 的含义

SurfaceFlinger 的 Layer 追踪中可看到形如 `BufferTX - <layerName>` 的计数器。Android 17 的命名锚点位于 `frameworks/native/services/surfaceflinger/Layer.h`。

它表达 SurfaceFlinger 侧待处理的 buffer transaction 数量，可用于观察事务积压。它不是普通应用 BufferQueue 的槽位状态计数，也不直接等于已经排队等待扫描输出的显示帧数。

分析时应把下面几类指标分开：

| 指标 | 所在边界 |
| --- | --- |
| dequeue / queue / acquire / release | 某条 BufferQueue 的槽位生命周期 |
| `BufferTX - layerName` | SurfaceFlinger Layer 的缓冲区事务积压 |
| FrameTimeline expected/ actual | 帧预计呈现与实际呈现结果 |
| HWC validate/ present | 显示合成与提交阶段 |

## 7. Fence：说明“什么时候可以安全使用”

图形管线通过 fence 表达跨 CPU、GPU、合成器和显示设备的异步完成关系。名称相近的 fence 所处方向不同。

| Fence | 谁等待 | 表达的条件 |
| --- | --- | --- |
| 获取栅栏（acquire fence） | 消费者 | 生产者对该缓冲区的写入何时完成，消费者何时可以安全读取 |
| 释放栅栏（release fence） | 后续复用该缓冲区的一方 | 当前消费者何时不再使用该缓冲区，何时可以安全重写 |
| 显示栅栏（present fence） | SurfaceFlinger / 显示时序追踪 | 当前显示提交何时在显示管线的呈现边界完成 |

在应用到 SurfaceFlinger 的队列中，应用是 producer，BLAST/系统侧消费逻辑接收带有 acquire fence 的缓冲区。到了 HWC 和显示设备边界，SurfaceFlinger 又要处理客户端目标（client target）、各 Layer 和 display present 相关的栅栏。

### 7.1 Present fence 的边界

Present fence 是 Android 显示栈的呈现完成时序锚点，但它不等同于面板像素的光学响应完成。面板扫描方式、像素响应时间、显示后处理和外部显示设备都可能位于 Android 软件可观测边界之外。

对于“输入到用户看到变化的总延迟”，应用 trace、FrameTimeline 和 present fence 只能覆盖其中一部分，还需结合触摸采样、显示扫描和面板特性。

### 7.2 等待 fence 不一定是 GPU 算力不足

一次栅栏等待只能说明依赖尚未满足。上游原因可能是：

- GPU 工作排队或执行时间长；
- producer 提交过晚；
- 前一消费者仍持有缓冲区；
- HWC 或显示设备尚未释放资源；
- 跨进程事务与目标 VSync 错位。

需要沿 fence 的生产者方向追踪，才能确定责任阶段。

## 8. SurfaceFlinger：接收事务、选择内容并组织合成

SurfaceFlinger 管理系统可见 Layer 的状态，接收来自 WindowManager、应用和系统组件的 SurfaceControl 事务。Android 17 的实现已经把 Layer 前端状态、快照生成、调度、合成规划和显示设备交互拆成多个模块，不能用单一“收到 VSync 后遍历所有 Layer 并画到屏幕”的函数调用描述它。

一轮显示处理涉及的核心概念包括：

1. 接收并应用 SurfaceControl 事务；
2. 更新 Layer 前端状态与可见性；
3. 为当前组合生成可用于合成决策的快照；
4. 判断缓冲区是否满足 latch 条件；
5. 结合损伤区域（damage）、几何、色彩、保护内容等信息准备合成；
6. 调用 HWC validate/ present；
7. 对需要客户端合成的部分调用 RenderEngine；
8. 传播 present 与 release 同步信息。

具体执行路径受 Scheduler、显示设备、Layer 状态、预测结果和 HWC 返回值影响。分析跟踪数据时，应围绕当前帧的事务、Layer、FrameTimeline 与 HWC 事件建立对应关系。

### 8.1 Latch 不是无条件拿最新缓冲区

SurfaceFlinger 选择缓冲区时要考虑：

- acquire fence 是否满足；
- 缓冲区期望呈现时间；
- Layer 与事务状态；
- 当前调度和 latch 策略；
- 当前版本与场景是否允许有限处理未 signal fence 的栅栏。

Android 13 以后存在受约束的未发信号缓冲区锁存（unsignaled latch）优化，但它有严格条件，不能扩写成 SurfaceFlinger 会忽略所有 acquire fence。

### 8.2 SurfaceFlinger VSync 与应用 VSync

应用和 SurfaceFlinger 都受显示节拍驱动，但调度器可以给它们设置不同的相位和 deadline。调度目标是让应用先生产，SurfaceFlinger 再在合适的时间消费并提交显示。

高刷新率、可变刷新率和多显示设备让“固定 16.67 ms、应用与 SurfaceFlinger 同时唤醒”的模型失效。性能判断应读取当前显示模式以及 FrameTimeline 给出的 expected/ actual 时序。

## 9. HWC 与 RenderEngine：每帧决定如何合成

### 9.1 HWC validate

Hardware Composer HAL 连接 SurfaceFlinger 与设备显示合成能力。SurfaceFlinger 为 Layer 提供候选 composition type，HWC validate 后可以接受或要求调整。

合成决策可能受以下因素影响：

- Layer 数量和硬件平面（plane）数量；
- 像素格式、压缩格式与 buffer usage；
- 缩放、旋转、裁剪和其他变换；
- alpha、混合模式和遮挡关系；
- dataspace、HDR、色彩转换和显示能力；
- protected content 与安全显示路径；
- 设备厂商的 HWC 实现和当前资源占用；
- 多显示器、虚拟显示器及 client target 约束。

“Layer 太多或有透明混合才会转 GPU 合成”只覆盖少数可能性。

### 9.2 Device composition 与 Client composition

| 类型 | 主要执行者 | 说明 |
| --- | --- | --- |
| 设备合成（Device composition） | 显示控制器 / HWC 能力 | Layer 可由硬件平面等资源直接组合 |
| 客户端合成（Client composition） | SurfaceFlinger 的 RenderEngine | 先把相应 Layer 合成为 client target，再交给 HWC |

同一帧可以混合使用两者。某个 Layer 的合成类型（composition type）也可能随帧变化，因此必须查看该帧的 HWC/SurfaceFlinger 数据，不能按应用或控件类型永久归类。

### 9.3 RenderEngine 与应用 HWUI 是两个组件

两者都可能使用 Skia、OpenGL ES 或 Vulkan 相关图形能力，但职责不同：

- 应用 HWUI 把 View/Compose 绘制记录生成应用窗口缓冲区；
- SurfaceFlinger RenderEngine 在客户端合成、模糊、色彩处理等系统合成任务中生成输出。

应用 GPU slice 很短，不代表 SurfaceFlinger 的 client composition 也很短；反过来也一样。Perfetto 中需要按进程和上下文区分 GPU 工作来源。

### 9.4 色彩处理位于多个可能阶段

色彩空间转换、色调映射、显示颜色变换可能由 RenderEngine、HWC、显示处理单元或面板侧能力负责，位置取决于 Layer、输出显示和设备实现。它不总是显示前的收尾步骤，成本也不能一概忽略。

## 10. 从应用缓冲区到显示输出，不是同一组“三个 Buffer”

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

把它们统一称作“前台、后台、显示中三个缓冲区”会混淆应用 BufferQueue、HWC 客户端目标与扫描输出（scanout）。排查时应明确当前 buffer 的 owner、queue、slot、frame number 和栅栏。

## 11. 硬件加速与软件绘制

### 11.1 硬件加速窗口

硬件加速窗口中，View 绘制命令通常录制进 DisplayList，由 HWUI、RenderThread 和 GPU 生成 GraphicBuffer。优势来自命令复用、GPU 并行和图形管线，但性能仍受内容特征影响：

- 大量离屏层和过度绘制会增加像素工作；
- 复杂 path、阴影、模糊和滤镜可能引入额外 pass；
- 位图上传和纹理缓存失效会增加内存与传输成本；
- shader 编译或管线缓存未命中可能造成抖动；
- 大量 RenderNode 更新也会增加 CPU 同步成本。

### 11.2 `setLayerType()` 的准确含义

`View.setLayerType(View.LAYER_TYPE_SOFTWARE, ...)` 在硬件加速窗口里为该 View 使用软件生成的 layer 内容，再由硬件管线把它当作纹理参与合成。它不会把整个 Window 切换成软件渲染。

窗口级是否启用硬件加速由 manifest、Window flag 和系统条件决定。View 级 layer type 主要影响该 View 的缓存/绘制策略，两者不能混为一谈。

### 11.3 软件渲染没有统一的胜负结论

软件 Canvas 由 CPU 执行光栅化，某些小型、低频或特定操作可能成本可控；复杂动画、大面积更新和高分辨率内容通常更容易受 CPU 与内存带宽限制。硬件渲染也可能受驱动、GPU 队列和资源管理影响。

选择渲染方式应基于目标设备、内容和 trace，而不是用“GPU 核心更多”或固定倍数推导速度与功耗。

## 12. 用 Perfetto 建立证据链

把某个阶段的结束当成整帧完成，很容易误判渲染问题。排查可以从用户感知的异常帧反向追踪。

### 12.1 第一步：锁定目标帧

先查看：

- FrameTimeline 的预期时间线（expected timeline）；
- 实际时间线（actual timeline）和 jank classification；
- 对应的 application frame 与 SurfaceFlinger frame；
- 当前刷新率、VSync 周期和 deadline。

帧率只适合描述一段时间的吞吐量。定位单帧应以时间线和 deadline 为主。

### 12.2 第二步：检查应用主线程

关注：

- Choreographer `doFrame` 是否启动过晚；
- INPUT、ANIMATION、TRAVERSAL 哪一段占用时间；
- `performTraversals` 内是否发生 measure、layout、draw；
- Binder、锁、I/O、GC 或调度延迟是否阻塞主线程；
- `requestLayout()` 或 `invalidate()` 是否异常频繁。

如果主线程很早完成，还要继续检查 RenderThread 与后续阶段。

### 12.3 第三步：检查 RenderThread 和 GPU

关注：

- `DrawFrame` / `syncAndDrawFrame` 的同步等待；
- dequeue 是否等待可用缓冲区；
- Skia 绘制与 `swapBuffers`；
- GPU queue、GPU completion 与相关 fence；
- 资源上传、shader/pipeline 编译和缓存抖动。

RenderThread CPU slice 长度不等于 GPU duration。二者可能重叠，也可能通过 fence 形成依赖。

### 12.4 第四步：检查 BufferQueue 与 BLAST

沿目标 Surface 查看：

- dequeue、queue、acquire、release 的时间；
- slot 和 frame number 是否对应；
- acquire fence 何时 signal；
- `BufferTX - layerName` 是否积压；
- BLAST transaction 何时进入 SurfaceFlinger；
- 队列深度是否带来背压或延迟。

如果一个进程包含多条 Surface，要先确认 Layer 名称与生产者，避免把 SurfaceView、视频或宿主窗口混在一起。

### 12.5 第五步：检查 SurfaceFlinger 与 HWC

关注：

- 事务应用与 Layer 快照；
- 目标缓冲区是否按期 latch；
- SurfaceFlinger 是否错过自己的 deadline；
- HWC validate 返回的 composition type；
- 是否发生 RenderEngine client composition；
- present fence 和 release fence 的时间；
- 多显示器、刷新率切换或显示模式变化。

不要给 SurfaceFlinger 套用固定“只剩几毫秒”的预算。实际预算取决于当前显示模式、调度相位、预测和 FrameTimeline。

### 12.6 常见错误推断

| 观察 | 不能直接推出 | 还需要的证据 |
| --- | --- | --- |
| `performTraversals` 出现 | 完整 measure/layout/draw 都已执行 | 内部切片、布局标志、脏区域 |
| `syncAndDrawFrame` 返回 | GPU 或显示已完成 | GPU fence、`queueBuffer`、FrameTimeline |
| `queueBuffer` 成功 | 画面已经显示 | BLAST/SF latch、HWC present |
| GPU Track 超过一个周期 | 该工作必然导致当前帧掉帧 | GPU 依赖、frame id、deadline |
| `BufferTX` 增加 | App BufferQueue 一定塞满 | 对应 Layer 事务与 BQ slot 状态 |
| HWC 使用 CLIENT | 一定是 Layer 太多 | 每层 composition reason 与设备能力 |
| present fence signal | 面板像素完成响应 | 面板扫描和硬件测量数据 |

## 13. 一个可复用的排查例子

假设列表滑动时出现一次明显停顿，可以按下面的顺序检查：

1. 在 FrameTimeline 中锁定实际晚到的帧，不要只找最长切片。
2. 查看应用 `doFrame` 是否晚启动；若晚启动，继续看 Runnable、Binder、锁、GC 和调度。
3. 若 `doFrame` 按时启动，检查 INPUT、ANIMATION、TRAVERSAL 的耗时与条件分支。
4. 若 UI 侧按时提交，检查 RenderThread 是否在同步、dequeue、绘制或 swap 阶段等待。
5. 若应用已按时 `queueBuffer`，按 Surface 和 frame number 追踪 BLAST transaction。
6. 检查 SurfaceFlinger 是否及时 latch，以及 acquire fence 是否满足。
7. 检查 HWC composition type、RenderEngine 工作和 present 时序。
8. 最终把根因归到“生产晚、GPU 完成晚、队列背压、系统合成晚或显示呈现晚”中的具体一项。

这种顺序可以避免看到主线程的一次长调用，就提前结束对后续异步阶段的检查。

## 14. 版本演进与 Android 17 边界

### Android 3.0 / API 11

Android 开始为更多 View 引入硬件加速与 DisplayList 记录。早期实现与现代 RenderNode、RenderThread 架构不同，不能用 Android 17 的类关系直接解释 Android 3.x 行为。

### Android 4.1 / API 16

Project Butter 强化了 VSync 驱动的 Choreographer 协调、三重缓冲相关能力和触摸响应优化。这里的“三重缓冲”仍应理解为管线并行策略，不能替代对具体 BufferQueue 配置的检查。

### Android 5.0 / API 21

现代 HWUI 架构中的 RenderNode 与 RenderThread 分工逐步确立。主线程录制，RenderThread 同步并提交绘制，成为后续版本分析的基础。

### Android 8.0 / API 26

Treble 之后 HWC HAL 接口与系统/厂商边界更清晰。设备合成能力仍由具体硬件与 vendor 实现决定。

### Android 10 / API 29

SurfaceControl 事务和渲染相关公开 API 继续扩展，系统合成与应用内容提交的关系更容易通过 trace 观察。

### Android 11 / API 30

`android-11.0.0_r1` 源码中已经出现 `BLASTBufferQueue`，窗口路径随后逐步采用它来协调缓冲区与 SurfaceControl Transaction。源码中出现该组件不等于所有 Android 11 设备和所有 Surface 类型都采用同一条路径。

### Android 12 / API 31

FrameTimeline 提供 expected/actual present 时间与卡顿分类，为跨应用和 SurfaceFlinger 的单帧分析提供稳定入口。

### Android 13 到 Android 16

SurfaceFlinger Scheduler、Layer 前端、FrameTimeline、刷新率和合成策略持续演进。部分版本支持有条件的 unsignaled latch，但同步规则仍需按源码条件判断。

### Android 17 / API 37

现行架构与源码路径以 `android-17.0.0_r1` 为准：

- ViewRootImpl 通过 Choreographer 调度 traversal；
- HWUI 通过 RenderNode、RenderThread 与 Skia 管线生成应用窗口缓冲区；
- 普通 App Window 使用 BLAST 参与缓冲区与 SurfaceControl Transaction 协调；
- SurfaceFlinger 使用前端状态/快照、Scheduler、HWC 与 RenderEngine 组织显示；
- HWUI 与 SurfaceFlinger 的具体后端选择受构建和设备配置影响；
- 性能结论以 FrameTimeline、fence、BufferQueue 和 HWC 的逐帧证据为准。

## 15. 源码阅读索引

### 应用主线程与 HWUI Java 层

- `frameworks/base/core/java/android/view/View.java`
- `frameworks/base/core/java/android/view/ViewRootImpl.java`
- `frameworks/base/core/java/android/view/Choreographer.java`
- `frameworks/base/core/java/android/view/ThreadedRenderer.java`
- `frameworks/base/graphics/java/android/graphics/HardwareRenderer.java`
- `frameworks/base/graphics/java/android/graphics/BaseRecordingCanvas.java`

### HWUI native 层

- `frameworks/base/libs/hwui/RenderNode.h`
- `frameworks/base/libs/hwui/RenderNode.cpp`
- `frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp`
- `frameworks/base/libs/hwui/renderthread/CanvasContext.cpp`
- `frameworks/base/libs/hwui/Properties.cpp`
- `frameworks/base/libs/hwui/pipeline/skia/SkiaPipeline.cpp`
- `frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp`
- `frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp`

### BufferQueue 与 BLAST

- `frameworks/native/libs/gui/BufferQueueCore.cpp`
- `frameworks/native/libs/gui/BufferQueueProducer.cpp`
- `frameworks/native/libs/gui/BufferQueueConsumer.cpp`
- `frameworks/native/libs/gui/BLASTBufferQueue.cpp`

### SurfaceFlinger、HWC 与 RenderEngine

- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
- `frameworks/native/services/surfaceflinger/Layer.h`
- `frameworks/native/services/surfaceflinger/FrontEnd/`
- `frameworks/native/services/surfaceflinger/Scheduler/`
- `frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp`
- `frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp`
- `frameworks/native/services/surfaceflinger/DisplayHardware/ComposerHal.h`
- `frameworks/native/libs/renderengine/`

## 标准应用窗口的七段边界

Android 渲染性能不能用“主线程画图，再由 GPU 显示”这一句话解释。标准应用窗口至少包含：

1. Choreographer 与 ViewRootImpl 驱动的 UI 遍历；
2. RenderNode DisplayList 的录制与同步；
3. RenderThread、Skia 和 GPU 生成 GraphicBuffer；
4. BufferQueue 与 BLAST 提交缓冲区和事务；
5. SurfaceFlinger 更新 Layer、latch 缓冲区并组织合成；
6. HWC、RenderEngine 和显示设备完成 present；
7. acquire、release、present fence 维护各阶段的安全依赖。

定位问题时，先确认输出拓扑，再按 frame id、Surface、BufferQueue slot、fence 和 FrameTimeline 逐段核对。这样才能区分应用生产晚、GPU 执行晚、队列背压、SurfaceFlinger 合成晚和显示呈现晚，避免用单个 slice 为整帧下结论。
