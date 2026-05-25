---
title: Android View 标准管线（BLAST 深入）
chapter: '18.2'
section: '18.2'
status: "ready-for-review"
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: '2026-05-05'
last_verified_against: AOSP ViewRootImpl/HWUI/BLASTBufferQueue + Compose 官方 Phases
  of a frame + 2026-04-29 external review
confidence: medium
sources:
- type: aosp
  path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
- type: aosp
  path: "frameworks/base/libs/hwui/"
- type: aosp
  path: "frameworks/native/libs/gui/BLASTBufferQueue.cpp"
- type: official
  path: "https://developer.android.com/develop/ui/compose/phases"
- type: research
  path: "DeepResearch/2026-05-15-android-view-blast-art-gc.md"
tags:
- BLAST
- RenderThread
- HWUI
- DisplayList
- FrameTimeline
- Triple-Buffering
- Non-blocking-Sync
- Compose
related_chapters:
- '2.1'
- '2.5'
- '2.6'
- '2.7'
- '18.1'
created_by: rendering-pipelines-merge
created_date: '2026-04-09'
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task9_state: "pending"
task2b_state: "fixed"
task2b_result: "fixed"
last_task2b_at: "2026-05-26T03:19:12+08:00"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-24"
task6_result: needs-rework
task6_reviewed_date: "2026-05-24"
last_task6_at: "2026-05-24T21:11:52+08:00"
task9_result: needs-rework
task9_reviewed_date: "2026-05-24"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-24T20:34:56+08:00"
task9_review_notes: "2026-05-15 task9 deep-review: needs-rework。P0 3 / P1 2 / P2 0。HWUI Sync、BLAST 回调、ART Generational CMC 源码口径需回炉。 | 2026-05-24 Task9 deep-review: needs-rework。P0 2 / P1 1 / P2 1；ART GC 把 ConcurrentCopying 写成 CMS、DeliQueue 源码路径仍指旧 MessageQueue、Trace 阈值用固定 16ms/8ms，需 Task2B 回炉。"
task6_review_notes: "2026-05-24 task6 revisiting review: needs-rework。小修1处（清理 Compose 段结构性元叙述），风险标注3处（固定帧预算、DeliQueue 源码路径、GC 术语混写）；L3/L4 1项：源码调研补充仍保留素材归档与编辑痕迹，已合并到 queue.json 18.2 P95 pending 项。"
last_task6_review_log: "logs/review/2026-05-24-21-review.md"
last_task9_review_log: "logs/deep-review/2026-05-24-20-deep-review.md"
---


# Android View 标准管线（BLAST 深入）

<!-- outline-start -->

**锚点（必须覆盖）：**
- [18.2.1 一帧的完整旅程](#一帧的完整旅程) — 从 VSync 到上屏的完整路径
- [18.2.2 BLAST Buffer 生命周期](#blast-buffer-生命周期) — Buffer 状态机与 Triple Buffering
- [18.2.3 渲染时序图](#渲染时序图blast-sequence) — BLAST 模式下的跨进程交互
- [18.2.4 Trace 视角](#trace-视角) — Perfetto 中的关键 Slice
- [18.2.5 FrameTimeline 与 Jank 检测](#frametimeline-与-jank-检测) — Android 12+ 的帧判定机制

**扩展（可选深入）：**
- SyncFrameState 的阻塞语义
- Fence 在 App-SF 间的流转
- Thread Roles 与职责边界
- Jetpack Compose 在这条管线上的位置

<!-- outline-end -->

这是一条绝大多数 Android App 每一帧都在走的渲染管线：UI Thread 构建 DisplayList → RenderThread 翻译为 GPU 指令 → BLAST 提交 Transaction → SurfaceFlinger 合成上屏。理解这些环节，是做渲染性能优化的基本功。

## 一帧的完整旅程

### 第一阶段：UI Thread — 生产蓝图

`VSync-App` 信号到达时，主线程被 `Choreographer` 唤醒，开始构建这一帧的绘制蓝图。这个过程是纯 CPU 操作，不产生任何像素：

1. **Input**：处理触摸/按键事件。用户点击了按钮，View 状态改变（如 `setPressed(true)`），触发 `invalidate()` 请求重绘。
2. **Animation**：`ValueAnimator` 在这里计算当前帧的动画值（如按钮缩放比例从 1.0 到 1.1 的中间值）。
3. **Measure**：自顶向下递归，父 View 询问子 View 需要多大空间，子 View 计算后汇报。这是一次完整的视图树遍历。
4. **Layout**：根据测量结果，确定每个 View 的精确位置 `(x, y, width, height)`。
5. **Draw（记录）**：调用 `View.onDraw(Canvas)`，但这个 Canvas 是 `RecordingCanvas`——它不画像素，只记录绘制命令（画圆、画文字、画图片），存入 `DisplayList`（也称为 `RenderNode`）。

**产物**：一组绘制指令列表（DisplayList）。这就是"蓝图"——它描述了"画什么"，但没有实际像素数据。

### 第二阶段：Sync — 移交蓝图

UI 线程完成 Draw 后，会把这一帧封装成 `DrawFrameTask` 交给 RenderThread，然后主线程进入等待。执行 `syncFrameState()` 的是 RenderThread，它在 `DrawFrameTask::run()` 中把 DisplayList、Bitmap 引用、Path 数据和 Layer 更新同步到渲染上下文。

**跨版本一致的机制**：`DrawFrameTask::postAndWait()` 从 Android 5.0 引入 RenderThread 起即存在，android-11 到 android-16 结构一致。UI 线程提交后同步等待 RenderThread 完成状态同步。具体流程：`DrawFrameTask::run()` 中先执行 `syncFrameState(info)`，把 DisplayList、Bitmap 引用和 Layer 更新同步到渲染上下文；同步完成后，如果满足条件（`canUnblockUiThread` 为 true），RenderThread 通过 `mSyncCond.signal()` 提前释放 UI 线程，UI 线程就能返回处理下一帧的 Input / Animation，不必等到 GPU 绘制完成。如果不满足提前释放条件（如帧结构复杂、需要保持 Draw-RT 原子性的场景），UI 线程会继续等待直到绘制结束。AVP 视频播放相关事务属于后一种场景，仍走完整同步阻塞路径。

[已验证: AOSP `frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp` — postAndWait() + canUnblockUiThread + mSyncCond.signal()，android-11/14/15/16 结构一致]

`syncFrameState` 变长时，常见原因是 Bitmap 过大、脏区域过多或 Layer 更新量突然上升。

### 第三阶段：RenderThread — GPU 绘制

RenderThread 拿到蓝图后，开始将它翻译为 GPU 能理解的指令：

1. **dequeueBuffer**：向 BLASTBufferQueue 申请一个空白的 GraphicBuffer。如果三个槽位都被占用（Triple Buffering 满载），这里会阻塞等待。在 Trace 中这是排查 Buffer 瓶颈的关键锚点。
2. **Flush Commands（GPU Draw）**：遍历 DisplayList，将"画圆、画图片"翻译为 OpenGL 或 Vulkan 指令（`glDrawArrays` / `vkCmdDraw`）。这些指令被写入 GPU Command Buffer，**CPU 并不等待 GPU 执行完毕**。
3. **queueBuffer**：绘制指令提交完成后，将这个 Buffer 归还给 BLASTBufferQueue，附带一个 `acquireFence`（表示 GPU 何时画完）。

### 第四阶段：BLAST 提交与 SurfaceFlinger 合成

这是 BLAST 模型的核心变化点：

1. **acquireNextBuffer**：BBQ 在 App 进程内作为消费者，从队列中取出刚画好的 Buffer。
2. **Build Transaction**：创建 `SurfaceControl.Transaction`，把 Buffer、acquireFence 和窗口几何信息放进同一次提交。Android 12+ 还会在这里通过 `setFrameTimelineInfo()` 带上这一帧的 VSyncId。
3. **apply Transaction**：通过 Binder 将 Transaction 发送给 SurfaceFlinger。这个调用通常是**异步的**，RenderThread 不等 SF 完成处理就返回。
4. **VSync-SF 到达**：SurfaceFlinger 被唤醒，等待 acquireFence signal，执行 `latchBuffer`，将所有 App 的 Layer 按 Z-Order 叠加，交给 HWC 硬件合成，最终上屏。

## BLAST Buffer 生命周期

理解 BLAST 的关键在于理解 Buffer 在槽位池中的状态流转。BBQ 内部维护一个 Buffer 槽位池（通常 3 个槽位，对应 Triple Buffering）。

### Buffer 状态机

```mermaid
stateDiagram-v2
    [*] --> FREE: 初始化
    FREE --> DEQUEUED: dequeueBuffer (RenderThread 拿走)
    DEQUEUED --> QUEUED: queueBuffer (RenderThread 归还)
    QUEUED --> ACQUIRED: acquireBuffer (BBQ 消费)
    ACQUIRED --> FREE: releaseBuffer (TransactionCompleted 回调触发)
```

每一个 Buffer 在任意时刻处于以下状态之一：

| 状态 | 含义 | 占有者 |
|:---|:---|:---|
| **FREE** | 空闲，可被分配 | 无 |
| **DEQUEUED** | 被 RenderThread 拿走准备写 | RenderThread |
| **QUEUED** | 写完放回队列，等待消费 | BLASTBufferQueue |
| **ACQUIRED** | Buffer 已被 BBQ 取走，并已关联到待提交或已提交的 Transaction | App 进程内的 BBQ |

### Triple Buffering 的意义

为什么要三个槽位？考虑一个最坏情况：

```
时间 →
Slot 0:  [App Draw F0]  [SF Display F0]
Slot 1:       [App Draw F1]  [SF Display F1]
Slot 2:            [App Draw F2]  [SF Display F2]
```

双缓冲时，如果 App 画 F1 比 SF 消费 F0 快，App 必须等 SF 释放 Slot 0——这就是 `dequeueBuffer` 阻塞的原因。Triple Buffering 引入第三个 Slot，让 App 可以立即拿到空闲 Slot 开始画 F2，而不必等 SF。

**代价**：多了一个 Slot 的显存占用（一张 1080p RGBA Buffer 约 8MB），以及多一帧的显示延迟。但换来的 GPU 利用率提升和卡顿减少，在大多数场景下是值得的。

### Buffer 计数逻辑（槽位视角）

| 操作 | 触发者 | 槽位变化 | 关联 Fence |
|:---|:---|:---|:---|
| **dequeueBuffer** | RenderThread | FREE → DEQUEUED | 返回 releaseFence（前消费者释放信号） |
| **queueBuffer** | RenderThread | DEQUEUED → QUEUED | 传入 acquireFence（GPU 画完信号） |
| **acquireBuffer** | BBQ 内部 | QUEUED → ACQUIRED | — |
| **releaseBuffer** | BBQ（由 SF 的 TransactionCompleted 回调触发） | ACQUIRED → FREE | releaseFence |

`releaseBuffer` 这一行背后有一条跨进程回调链。BLAST 模式下，Consumer 驻留在 App 进程的 BBQ，而不是 SurfaceFlinger。SF 在 Transaction 完成后通过 `TransactionCompletedListener` 把 `ReleaseCallbackId` 和 `releaseFence` 回传给 App，BBQ 再调用 `releaseBufferCallbackLocked()` 与 `BLASTBufferItemConsumer::releaseBuffer()` 归还槽位。排查 `dequeueBuffer` 长等待时，这条释放链要一起看。

## 渲染时序图（BLAST Sequence）

这张图展示了 BLAST 模式下，App、RenderThread、BBQ、SurfaceFlinger 和 HWC 之间的完整交互。注意 Buffer 的提交变成了 Transaction 的一部分——这是 BLAST 区别于 Legacy BufferQueue 的核心变化。

```mermaid
sequenceDiagram
    participant HW as Hardware VSync
    participant App as App UI Thread
    participant RT as RenderThread
    participant BBQ as BLASTBufferQueue
    participant SF as SurfaceFlinger
    participant HWC as HWC / Display

    Note over HW, App: 1. VSync-App（唤醒 App）
    HW->>App: VSync-App Signal
    
    rect rgb(240, 240, 250)
        Note over App, RT: 2. App 生产
        activate App
        App->>App: Input → Animation → Layout → Draw (Record)
        App->>RT: SyncFrameState（阻塞等待）
        deactivate App
        
        activate RT
        RT->>BBQ: dequeueBuffer() → releaseFence
        Note right of RT: 返回 releaseFence
        RT->>RT: Flush GL/Vulkan Commands
        RT->>BBQ: queueBuffer(acquireFence)
        deactivate RT
    end

    rect rgb(230, 250, 230)
        Note over BBQ, SF: 3. BLAST 提交
        BBQ->>BBQ: acquireNextBuffer
        BBQ->>SF: Transaction(Buffer, acquireFence, FrameTimelineInfo)
    end

    Note over HW, SF: 4. VSync-SF（合成）
    HW->>SF: VSync-SF Signal
    activate SF
    SF->>SF: Wait acquireFence
    SF->>SF: latchBuffer
    SF->>HWC: validate & present
    deactivate SF

    rect rgb(250, 230, 230)
        Note over HWC: 5. 上屏
        HWC->>HWC: Scanout
    end
    
    HWC-->>SF: presentFence
    SF-->>BBQ: TransactionCompleted(releaseFence)
    BBQ-->>RT: Buffer 可复用
```

### 关键时序特征

1. **App 与 SF 的解耦**：RenderThread 通过 `queueBuffer` 将 Buffer 提交给 BBQ 后，不等待 SF 处理。BBQ 在 App 进程内完成 `acquireNextBuffer` 并构造 Transaction，再通过异步 Binder 发给 SF。这使得 App 侧的帧生产不会被 SF 的合成节奏直接阻塞。
2. **Fence 同步**：CPU 不等 GPU。`acquireFence` 是 GPU 画完的信号，SF 在 `latchBuffer` 时等待这个 fence，而不是 CPU spin-wait。
3. **槽位循环**：Slot 0 画完进入 ACQUIRED 状态后，RenderThread 可以立即 dequeue Slot 1 开始画下一帧。
4. **释放回路**：Slot 回到 FREE，要等 SF 的 TransactionCompleted 回调把 `releaseFence` 带回 BBQ。`dequeueBuffer` 堵住时，问题也可能出在这条释放路径的后段。

## Trace 视角

在 Perfetto 中分析标准管线时，以下 Slice 和信号是关键锚点。注意：具体名称可能因 Android 版本和 OEM 而异，但功能语义是稳定的。

[已修正: Task9 2026-05-24 指出固定 16ms/8ms 阈值不适配高刷，表中正常耗时改为相对参考值。判断掉帧应基于当前 display frame interval 和 FrameTimeline expected present deadline，而非固定 16ms。]

### UI Thread 关键 Slice

| Slice | 含义 | 正常耗时 | 异常信号 |
|:---|:---|:---|:---|
| `Choreographer#doFrame` | 一帧的完整 UI 处理 | < frame_interval / 2（60Hz 约 8ms） | 超过当前 display frame interval → 必定掉帧 |
| `measure` / `layout` | 视图树的测量和布局 | < 2ms | 递归层级过深或布局复杂 |
| `draw` | DisplayList 记录 | < 4ms | onDraw 中有耗时操作 |
| `syncAndDrawFrame` / `DrawFrame` | 把任务投递给 RenderThread 后进入等待 | < 2ms | 这里变长时，继续看 RenderThread 的 `syncFrameState`、`dequeueBuffer` 和 GPU 提交 |

### RenderThread 关键 Slice

| Slice | 含义 | 正常耗时 | 异常信号 |
|:---|:---|:---|:---|
| `DrawFrame` | 一帧渲染任务的入口 | < frame_interval / 2（60Hz 约 8ms） | 内部若出现长 `syncFrameState` 或长 `dequeueBuffer`，说明瓶颈在状态同步或 Buffer 供给 |
| `syncFrameState` | 同步 RenderNode、Bitmap、Layer 状态 | < 2ms | Bitmap 过大、Layer 更新突增、脏区域扩大 |
| `dequeueBuffer` | 申请空闲 Buffer | < 1ms | 长等待 → Buffer 释放链或 SF 节奏跟不上 |
| `queueBuffer` | 提交画好的 Buffer | < 1ms | 异常少见 |

### SurfaceFlinger 关键 Slice

| Slice | 含义 | 异常信号 |
|:---|:---|:---|
| `setTransactionState` / `applyTransactionState` | 收到并应用 App 的 Transaction | 排队过多说明 Transaction 提交密度过高 |
| `commit` / `latchBuffer` | 锁定 Buffer 并推进本帧合成 | 等待 acquireFence 久 → GPU 还没画完 |

### 快速定位口诀

- **主线程长条 + RenderThread 短条** → UI 负担重（measure/layout/draw 慢）
- **主线程短条 + RenderThread 长条 + dequeueBuffer 长等待** → GPU 瓶颈或 Buffer 瓶颈
- **主线程短条 + RenderThread 短条 + FrameTimeline 标记 Jank** → SF 合成瓶颈或 HWC 问题

## FrameTimeline 与 Jank 检测

Android 12 引入了 FrameTimeline 机制，改变了 Jank 的判定方式。在此之前，性能分析依赖简单的"VSync 周期"判断——如果一帧耗时超过 16.6ms 就算掉帧。但这种方式无法区分"故意降频"和"用户感知的卡顿"。

### 核心机制

1. **VSyncId**：每个 VSync 信号携带唯一 ID。`Choreographer` 收到 `VSyncId`（比如 1001）后，在 `doFrame` 开始时根据这个 ID 计算预期上屏时间（`ExpectedPresentTime`）。
2. **Propagation**：RenderThread 把 `VSyncId` 交给 BBQ，BBQ 在组装 `SurfaceControl.Transaction` 时调用 `setFrameTimelineInfo()`，再把这份信息跟着 Transaction 跨进程发给 SurfaceFlinger。
3. **Matching**：SF 以这份 FrameTimelineInfo 为索引，对照 Expected Present Time 和实际 present 结果判断这一帧是否超时。

### Perfetto 中的表现

在 Perfetto 的 FrameTimeline Track 中：

- **Expected Timeline（绿条）**：表示"这帧应该在什么时间点上屏"
- **Actual Timeline（实心条）**：表示"这帧实际在什么时间点上屏"
- **Jank Tag**：Actual 超过 Expected 时自动标记。分为 `Jank`（轻微）和 `BigJank`（严重）

这种基于 VSyncId 的判定方式比传统的 "16.6ms 阈值" 精确得多。一个 30fps 渲染的页面，每两帧才有一个 VSync，FrameTimeline 能正确识别这不是掉帧——而简单的周期判定会把它标记为 Jank。

## 补充：Jetpack Compose 在这条管线上的位置

Jetpack Compose 是 Android 原生的声明式 UI 框架。从出图路径看，Compose 和 View 系统没有区别——最终都走这条 HWUI / BLAST / SurfaceFlinger 主路径。Compose 的独立维度只有一个：**MainThread 上的工作形态不同**。RenderThread 之后的部分完全共用，Compose 相关分析应集中在 MainThread 侧。

### Compose 一帧的三阶段

Compose 一帧在 MainThread 侧分三个阶段：

1. **Composition**：执行 `@Composable` 函数树，生成或更新代表界面结构的 layout node tree；Slot Table 记录 composition group、`remember` 状态和重组定位信息。这一阶段只决定"写什么"，不做布局和绘制。
2. **Layout**：用 Compose 自己的 measure policy 计算每个节点的尺寸和位置。Compose **默认**是一次 measure/layout 遍历（single-pass），但 intrinsic measurements / `SubcomposeLayout` / Lookahead 这些机制会带来额外 pass。
3. **Drawing**：把 layout node tree 对应的绘制指令录到 DisplayList（与 View 系统共用 HWUI 的 DisplayList / RenderNode）。

三阶段执行完后，Compose 把结果挂到 Host View（`ComposeView` / `AbstractComposeView`）上。这个 Host View 对外仍是普通 Android View，继续走 `ViewRootImpl` 的 `performTraversals()` / `performDraw()` 路径。RenderThread 之后的一切和 View 标准管线完全相同。

**运行时层演进**：Android 17 的 Generational CMC（分代并发标记压缩）对 Compose Composition 阶段的 GC 停顿有潜在优化空间。Composition 阶段会产生大量 `Snapshot` 状态快照对象，属于短生命周期分配。分代 GC 的 young generation 回收范围更小，理论上停顿时间比全堆回收更短。

注意：Slot Table 条目不是简单的每帧短生命周期临时对象——它们在重组间持续存在，生命周期与 Composition group 绑定。GC 策略对 Composition 阶段分配停顿的实际影响取决于 ART 运行时版本、堆大小和具体 Composable 复杂度，需要按场景实测确认。[待验证: 目前缺少 ART generational CMC 与 Compose Composition 阶段的一手 benchmark 数据（设备、模型、量化配置和 jank 指标），无法确认具体收益幅度]

[已验证: AOSP `frameworks/base/core/java/android/view/ViewRootImpl.java` + Compose 官方文档 "Phases of a frame"]

### 重组与跳过机制

Compose 性能分析最先要盯的是**重组**（recomposition）——状态变化时只重新执行相关的 Composable，不整树重跑。重组的作用域和跳过由 Compose 编译器插入的代码决定：

- **skippable**：参数都 stable 且没变化时，Composable 可以被跳过（不重新执行函数体）。
- **restartable**：Composable 自身可以作为重组的起点，状态变化时从这里开始重跑。
- **stable**：类型满足 Compose 的稳定性判定（primitive 类型、带 `@Stable` 或 `@Immutable` 注解的类、`MutableState` 的 value 等）。

非 stable 参数（普通 `List<T>`、未加注解的 data class、捕获了不稳定状态的 lambda）会导致 Composable 每次都重组，即使参数内容没变。trace 上看到 MainThread 反复跑 Composition 阶段的大块 slice，多半是 skippability 出了问题。具体哪个 Composable 跑多了，用 Compose Compiler 的 stability report 或 Layout Inspector 的重组计数定位。

### Compose 特有的 Perfetto Slice

启用 Compose tracing（`androidx.compose.runtime:runtime-tracing`；具体环境门槛以官方 Compose tooling 文档为准）后，MainThread 上能看到几类 Compose 特有 slice：

- **重组阶段相关 slice**（具体命名随 Compose 运行时版本，常见 `Recomposer` / `Composition` / `ComposerImpl.doCompose`）。
- **Composable 函数调用 slice**（开启 source information 后能看到具体 `@Composable` 名字和位置）。
- **Layout 阶段 slice**（Compose 自己的 measure policy 执行）。
- **Drawing 阶段 slice**（录入 DisplayList，与 View 的 `onDraw` 共享 HWUI 底层）。

未开启 Compose tracing 的 trace 里只能看到笼统的 `ComposeView#onMeasure` / `onLayout` / `onDraw`。排查 Compose 性能问题前先确认 tracing 是否启用，没启用的话数据价值有限。

### Compose 与 View 在 Trace 上的对比

| 维度 | View 系统 | Compose |
|:---|:---|:---|
| UI 构建方式 | XML + `findViewById` + `setText` 命令式 | `@Composable` 函数声明式 |
| 变更触发 | `invalidate()` / `requestLayout()` | 状态（`MutableState` / `StateFlow` 等）变化 |
| 布局遍历 | measure + layout 两阶段，嵌套容器可能触发多次 | 默认 single-pass，intrinsic / `SubcomposeLayout` / Lookahead 会带来额外 pass |
| MainThread slice | `measure` / `layout` / `draw` / `onDraw` | `Composition` / `Layout` / `Drawing` / Composable 函数 |
| 跨帧并行度 | UI Thread + RenderThread 两级流水 | 与 View 相同（Compose 不改变流水深度） |
| RenderThread 之后 | 标准 BLAST 主路径 | 完全相同 |
| 特有性能陷阱 | 深嵌套 ViewGroup 多次 measure、over-invalidation | 非 stable 参数触发的非必要重组、`remember` 用错 |

性能差异主要落在 MainThread 上的工作效率——Compose 看重组跳过做得好不好，View 看 measure / layout 做得轻不轻。RenderThread 之后两者完全一致；瓶颈类型相同，只是 MainThread 侧的分析入口不同。

### ComposeView 与 AndroidView 的互嵌

Compose 与 View 系统可以互相嵌入：

- **Compose 内嵌 View**：用 `AndroidView { ... }` 在 Composable 里放原生 View。被嵌入的 View 走自己的 measure / layout / draw，Compose 负责把它挂在正确的位置。
- **View 内嵌 Compose**：在 XML 里放 `ComposeView`，调 `setContent { ... }` 加 Composable 内容。`ComposeView` 对外是 `AbstractComposeView`（继承 `ViewGroup`），走标准 View 路径被 `ViewRootImpl` 管理。

混合场景在 trace 上能看到 MainThread 交替出现 Compose 阶段 slice 和 View 的 measure / layout / draw slice。分析时先按外层容器判断整体驱动模型：外层是 `ViewRootImpl` 管的 View tree，内层 Compose 阶段在外层 `Traversal` 中间插入；外层是 `ComposeView`，Compose 阶段在其 `onMeasure` / `onLayout` / `onDraw` 回调里完成。

---

> **交叉引用**：
> - BufferQueue 的内部机制（Producer/Consumer 双端、Buffer Slot 管理）详见 [2.13 图形缓冲区管理](../../part1-fundamentals/ch02-rendering/13-buffer-queue.md)
> - SurfaceFlinger 的合成策略（GPU 合成 vs HWC 合成）详见 [2.6 SurfaceFlinger 与合成](../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md)
> - Fence 同步原理详见 [2.16 Sync Fence 框架与帧同步机制](../../part1-fundamentals/ch02-rendering/16-sync-fence.md)
> - SurfaceControl 与 Transaction 的底层实现详见 [18.10 SurfaceControl API 深入](10-surface-control-api.md)

<!-- AIW-源码调研-2026-05-15 -->

<!-- AIW-源码调研-2026-05-16 -->
## 源码调研补充（2026-05-16）

**关联章节**：§18.2
**调研目标**：HWUI Sync、BLAST 回调机制源码验证；DeliQueue 版本边界确认

### MessageQueue.DeliQueue 源码验证

**文件**：`frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java`（AOSP main，targetSdk >= 37 默认实现）

[已修正: Task9 2026-05-24 指出 DeliQueue 源码锚点应指向 `ConcurrentMessageQueue/MessageQueue.java`，已修正。]

DeliQueue（Treiber Stack 实现）是 Android 17 (API 37) 为 targetSdk >= 37 应用引入的 MessageQueue 优化：

| 特性 | 说明 |
|:---|:---|
| **类型** | Treiber Stack（无锁栈） |
| **启用条件** | targetSdk >= 37（Android 17+） |
| **核心改进** | CAS 无锁入队/出队，减少同步开销 |
| **native 层** | `nativePollOnce()` 通过 epoll_wait 阻塞，不占用 CPU |

旧版 Message 使用单向链表，按 `when`（消息触发时间）排序插入。DeliQueue 用无锁栈替代链表，在高消息频率场景下减少锁竞争。

### BLASTBufferQueue TransactionCompleted 回调链

**文件**：
- Java：`frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java`
- Native：`frameworks/native/libs/gui/BLASTBufferQueue.cpp`

关键回调链：
```
SurfaceFlinger 合成完成
    ↓ TransactionCompletedListener（跨进程 Binder 回调）
BLASTBufferQueue.releaseBufferCallbackCallback
    ↓
BLASTBufferItemConsumer::releaseBuffer()
    ↓
ACQUIRED → FREE（槽位释放）
```

`dequeueBuffer` 长等待的排查方向：除看 RenderThread 侧，还要看 release 链后段是否顺畅（SF 回调是否及时到达）。

### View mAttachInfo / mWindowAttachCount 渲染生命周期

**文件**：`frameworks/base/core/java/android/view/View.java`

| 字段 | 作用 |
|:---|:---|
| `mAttachInfo` | View 附着信息，attach 时从 ViewRootImpl 传入；决定 View 能否参与当前帧 |
| `mWindowAttachCount` | 记录 attach/detach 次数，判断 View 是否在当前窗口树中 |

detached View 的 `invalidate()`/`requestLayout()` 会被忽略或延迟到下次 attach。

### canUnblockUiThread 机制确认

**文件**：`frameworks/base/libs/hwui/renderthread/DrawFrameTask.cpp`（postAndWait + canUnblockUiThread）

- 存在于 Android 14/15/16（android-14+ 保持一致）
- 满足 `canUnblockUiThread` 条件时，RenderThread 通过 `mSyncCond.signal()` 提前释放 UI 线程
- 不满足时（如 AVP 视频播放场景），UI 线程等待完整绘制完成

### ART Generational CMC 与 Compose（待验证）

**已知源码路径**：
- `art/runtime/gc/collector/mark_compact.cc`
- `art/runtime/gc/heap.cc`
- `build/flags/art-flags.aconfig`

Compose Composition 阶段产生的 `Snapshot`/`SlotTable` 对象生命周期与 Generational CMC 的交互缺乏一手 benchmark 数据，章节中 `对象分配开销降低 20%+` 暂无版本/设备/场景支撑，应标注为「待验证」或删除具体数字。

<!-- AIW-源码调研-2026-05-16 -->
## 附：源码调研补充 — ART Generational CC 与 BLAST BufferQueue 协同机制

*来源：AIW 每日源码调研 · 2026-05-15 · 关联 §18.2*

### BLASTBufferQueue 核心路径（Native 层）

**文件**: `frameworks/native/libs/gui/BLASTBufferQueue.cpp`

BLASTBufferQueue 持有 `IGraphicBufferProducer`，在 `relayout()` 触发时通过 JNI 创建底层 Surface。关键类继承关系：

```cpp
class BLASTBufferQueue : public ConsumerBase::FrameAvailableListener,
                         public BufferItemConsumer::BufferFreedListener {
    // onFrameAvailable(): producer queueBuffer() 后 BBQ 作为 consumer 收到的
    // BufferQueue 回调，表示有新 Buffer 可消费
    void onFrameAvailable(const BufferItem& item) override;
    void onFrameReplaced(const BufferItem& item) override;
    void onFrameDequeued(const uint64_t) override;
    void onFrameCancelled(const uint64_t) override;
    sp<IGraphicBufferProducer> getIGraphicBufferProducer() const { return mProducer; }
};
```

BBQ 在 `acquireNextBufferLocked()` 中消费新 Buffer 并构建 `SurfaceControl.Transaction`，通过 `Transaction.apply()` 提交给 SurfaceFlinger。`transactionCommittedCallback` 在 Transaction 提交后被回调，用于清理 synced frame state 和 flush shadow queue，不是驱动 Transaction 提交的入口。[已验证: AOSP `frameworks/native/libs/gui/BLASTBufferQueue.cpp` — acquireNextBufferLocked / processNextBufferLocked / transactionCommittedCallback]

Java 层绑定在 `frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java`，JNI 层在 `core/jni/android_graphics_BLASTBufferQueue.cpp`。

ViewRootImpl (`frameworks/base/core/java/android/view/ViewRootImpl.java`) 通过 `mBlastBufferQueue` 成员持有实例。`performTraversals()` → `relayout()` → `scheduleTraversals()` 调度链路中，`mChoreographer.postCallback(Choreographer.CALLBACK_TRAVERSAL, this, null)` 将 traversal 任务注入下一个 vsync 周期。

### ART Generational GC 源码级机制

**文件**: `art/runtime/gc/collector/mark_compact.cc`（Android 17 Concurrent Mark-Compact generational GC）；`art/runtime/gc/collector/concurrent_copying.cc`（历史 CC/Generational CC）

Android 17 引入的 CMC（Concurrent Mark-Compact）generational support 与历史 generational CC 是不同实现：

- **历史 Generational CC**（`-Xgc:generational_cc`，Android 10 引入，默认关闭）：基于 `ConcurrentCopying` collector，在 `concurrent_copying.cc` 中实现分代逻辑，young GC 只回收 young generation，全堆回收在 explicit/native alloc 等 GcCause 时触发。
- **Android 17 CMC generational**：基于 `MarkCompact` collector，源码在 `mark_compact.cc`，通过 ART aconfig flags（`art-flags.aconfig`）控制启用条件。具体 runtime 条件和 targetSdk 边界需待 AOSP 正式 tag 发布后确认。

CC Collector 通过 read-barrier 拦截堆引用读取，在应用线程运行期间并发复制对象。GC 的 stop-the-world 停顿时间取决于回收范围和堆大小——分代回收时 young generation 扫描范围更小，停顿通常更短，但具体收益取决于应用分配模式和堆配置。

[待验证: Android 17 CMC generational 的启用条件、Runtime::Init 中的 generational_cmc_supported 判断逻辑，需 AOSP 正式 tag 确认]

### 版本差异

| 版本 | GC 类型 | 分代支持 |
|------|---------|----------|
| Android 10 之前 | CMS / Semi-space | 无分代 |
| Android 10 | CC | 引入 `-Xgc:generational_cc`（默认关闭）|
| Android 11-16 | CC | 分代 CC 在部分设备逐步默认启用 |
| Android 17 | CMC (Concurrent Mark-Compact) | 引入基于 MarkCompact 的分代 GC，与历史 CC 分代为不同实现；启用条件和 targetSdk 边界待 AOSP 正式 tag 确认 |

### 性能影响机制

Compose Composition 阶段的 `Snapshot` 状态快照属于短生命周期分配，会被 young generation GC 回收。Slot Table 条目生命周期与 Composition group 绑定，不全是每帧临时对象。分代 GC 对 Compose 渲染性能的实际影响需要按场景实测。[待验证: 缺少一手 benchmark 数据]

源码参考：
- AOSP: `art/runtime/gc/collector/concurrent_copying.h` — CC Collector 定义
- source.android.com: "Debug ART garbage collection" — CC 并发机制说明
- developer.android.com: "Verifying app behavior on the Android runtime (ART)" — ART GC 概述

## 参考资料

### Android View 标准管线 — BLASTBufferQueue 与 ART 分代 GC 协同机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-15-android-view-blast-art-gc.md
- 类型：DeepResearch 调研结果
- 摘要：解析 BLASTBufferQueue 与 ViewRootImpl 的异步 buffer 提交流程，以及 ART Generational CC 分代 GC 对 View 渲染分配压力的影响。核心内容：整理 BLASTBufferQueue 的 buffer 回调路径和 ART 分代 GC 的停顿边界；Compose / View 渲染阶段的收益仍需实测。
- 注入时间：2026-05-15
- 价值：提供后续核对 BLASTBufferQueue 与 ART GC 关系的素材索引，待 Task2B 整合进正文

<!-- AIW-源码调研-2026-05-24 -->
## 附：Android ART GC 与 Compose 性能关联（源码级验证）

### GC 触发机制对 Compose 的影响

**关键源码路径**：`art/runtime/gc/heap.cc`

ART 在 allocation failure 时触发 `kGcCauseForAlloc` 同步 GC：

```cpp
// GC_FOR_ALLOC when young generation is full
if (last_gc_ < tried_type) {
  CollectGarbageInternal(tried_type, kGcCauseForAlloc, false, starting_gc_num + 1);
}
```

**对 Compose 的影响**：
- Compose recomposition 产生大量短期对象（lambda、state、node）
- 这些对象集中在 young generation，快速填满分配空间
- 当达到 `growth_limit_` / `alloc_limit_` 阈值时，触发同步 GC
- 同步 GC 导致分配线程 stop-the-world，如果发生在 VSYNC 窗口则造成掉帧

**Android 13+ 改进**：
[已修正: Task9 2026-05-24 指出 CC 与 CMS 不可混写，已修正。Android 8+ 默认 GC 为 Concurrent Copying（CC），Concurrent Mark Sweep（CMS）是另一个 GC plan。]

- 默认使用 Concurrent Copying（CC）大幅减少 stop-the-world pause
- `ChangeCollector()` 支持 young→old GC 类型切换
- `use_generational_gc_` 参数启用分代 GC 优化

### 性能优化建议

1. 减少 recomposition 频率（避免不必要状态变更）
2. 使用 `remember` + `derivedStateOf` 减少对象分配
3. 对高频重组场景使用 `remember` 缓存计算结果
