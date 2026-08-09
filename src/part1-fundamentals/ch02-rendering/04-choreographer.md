---
title: Choreographer 与渲染流水线
chapter: '2.4'
section: '2.4'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 Choreographer.java + DisplayEventReceiver.java + ViewRootImpl.java + FrameMetrics.java
confidence: high
sources:
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer
- type: aosp
  path: platform/frameworks/base/core/java/android/view/Choreographer.java
- type: aosp
  path: platform/frameworks/base/core/java/android/view/DisplayEventReceiver.java
- type: aosp
  path: platform/frameworks/base/core/java/android/view/ViewRootImpl.java
- type: aosp
  path: platform/frameworks/base/graphics/java/android/graphics/HardwareRenderer.java
- type: aosp
  path: platform/frameworks/base/libs/hwui/renderthread/CanvasContext.cpp
- type: aosp
  path: platform/frameworks/base/core/java/android/view/FrameMetrics.java
- type: aosp
  path: platform/frameworks/base/core/java/android/view/Window.java
- type: aosp
  path: platform/frameworks/native/services/surfaceflinger/Scheduler/EventThread.cpp
- type: aosp
  path: platform/frameworks/native/libs/gui/DisplayEventReceiver.cpp
- type: aosp
  path: platform/frameworks/native/libs/gui/BLASTBufferQueue.cpp
- type: kernel
  path: kernel/common/kernel/sched/core.c
  ref: android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/kernel/sched/fair.c
  ref: android17-6.18-2026-06_r6
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer.FrameData
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer.FrameTimeline
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://developer.android.com/develop/ui/compose/phases
- type: research
  path: Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: research
  path: Writer/rendering_pipelines/S02_aosp_standard_type.md
tags:
- choreographer
- doframe
- 渲染流水线
- VSync
- 帧调度
- 性能优化
- FrameMetrics
- FrameCallback
- 同步屏障
related_chapters:
- '2.3'
- '2.5'
- '2.6'
- '2.9'
- '3.1'
- '8.2'
drafted_date: '2026-03-30'
reviewed_date: '2026-04-21'
reviewed_by: openclaw-task6
review2_date: '2026-04-02'
review2_by: openclaw-task6
rework_date: '2026-04-02'
rework_by: openclaw-task2b
review3_date: '2026-04-03'
review3_by: openclaw-task6
review4_date: '2026-04-04'
review4_by: openclaw-task6
review5_date: '2026-04-10'
review5_by: openclaw-task6
review6_date: '2026-04-11'
review6_by: openclaw-task6
rework_reason: Task6 review 回炉修复:doFrame伪代码修正+总结重写+Compose节重写+补充3个Type A标准节+厂商优化标注
rework5_date: '2026-04-10'
rework5_by: openclaw-task2b
rework6_date: '2026-04-10'
rework6_by: openclaw-task2b
rework6_reason: 'Task9 Deep Tech Review: Compose pausable composition 补充 FrameData
  deadline 来源和 1.7 前对比; Frame Timeline 补充颜色编码规则和 Track 命名'
rework7_date: '2026-04-11'
rework7_by: openclaw-task2b
rework7_reason: 'Task9 Deep Tech Review: doFrame源码摘录、FrameMetrics API、FrameCallback续订、Perfetto
  SQL、版本时间线修正'
rework8_date: '2026-06-26'
rework8_by: openclaw-task2b
rework8_reason: 'Task9 Deep Tech Review: 移除 7.1-7.5 节未验证 Android 17 源码内容,替换为标注版变更笔记;修正回调类型术语(四种→五种)'
polish_count: '1'
polish_date: '2026-04-04'
polish_by: task2b-polish
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
review7_date: '2026-04-19'
review7_by: openclaw-task6
review8_date: '2026-06-26'
review8_by: openclaw-task6
task9_result: pass-tech-review
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task9_at: '2026-06-26T07:20:00+08:00'
task9_reviewed_date: '2026-06-26'
task9_reviewed_by: openclaw-task9
last_task6_at: '2026-06-26T07:07:00+08:00'
last_task6_audit: '2026-06-26'
last_task6_audit_result: pass-clean
last_task6_audit_log: logs/review/2026-06-10-10-audit.md
last_task9_audit: '2026-06-26'
last_task9_audit_at: '2026-06-26T07:20:00+08:00'
last_task9_audit_log: logs/deep-review/2026-06-26-07-choreographer-deep-review.md
last_task9_review_log: logs/deep-review/2026-05-23-03-deep-review.md
task9_review_notes: '2026-05-23 Task9 deep review: pass-tech-review。无 P0/P1；P2：回调类型"四种/五类"内部表述需统一，已写入
  suggestions.md。满足 task6_result=pass-light-edit 且 queue 无 pending，自动晋升 finalized。
  | 2026-06-26 Task9 deep review: pass-tech-review。无 P0/P1，2项 P2 建议已写入 suggestions.md，满足晋升条件。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: '2026-06-26'
last_task2b_lite_at: '2026-06-26'
task2b_verified_at: '2026-06-26T07:27:19+08:00'
task2b_verify_result: 'promoted-to-finalized: task6 pass-light-edit + task9 pass-tech-review
  + queue clear'
---

# Choreographer 与渲染流水线

## Choreographer 管理“何时开始一帧”

Choreographer 是绑定到某个 `Looper` 的帧回调调度器。它把需要和显示节奏配合的工作分组，在一次应用 VSync 到来后按固定阶段执行。

它负责：

- 合并同一待处理帧的重复调度请求；
- 按需向 `DisplayEventReceiver` 申请下一次 VSync；
- 保存五类回调队列；
- 提供稳定的帧时间、候选 FrameTimeline、截止时间和 VSync ID；
- 在 `doFrame()` 中按阶段执行已经到期的回调；
- 检测迟到、帧时间倒退和缓冲积压恢复条件。

它不负责：

- 直接读取触摸设备；
- 独自完成 View 的 measure、layout、draw；
- 在 RenderThread 上执行 GPU 绘制；
- 决定 SurfaceFlinger 采用哪块缓冲；
- 判断面板像素何时完成光学响应。

标准 View 窗口的一帧可以概括为：

```text
状态变化 / 输入 / 动画
  → ViewRootImpl 或其他组件注册帧回调
  → Choreographer 申请一次应用 VSync
  → FrameDisplayEventReceiver 投递异步消息
  → Choreographer.doFrame()
  → INPUT → ANIMATION → INSETS_ANIMATION → TRAVERSAL → COMMIT
  → ViewRootImpl / HWUI / RenderThread 生产缓冲
  → SurfaceFlinger / HWC 完成合成与显示提交
```

这条路径说明 Choreographer 位于应用生产阶段的起点。`doFrame()` 结束只表示这次 Looper 回调已经完成，不能证明 GPU、缓冲、SurfaceFlinger 或显示后段已经完成。

---

## 一、Choreographer 与线程、Looper 的关系

### 1.1 每个实例绑定一个 Looper

`Choreographer.getInstance()` 使用 `ThreadLocal` 保存实例。当前线程必须已经有 `Looper`，否则会抛出 `IllegalStateException`。实例创建后，`FrameHandler` 和 `FrameDisplayEventReceiver` 都绑定到这个 Looper。

主线程是最常见的使用位置，但“Choreographer 只存在于主线程”不准确。带 Looper 的其他线程也能取得自己的实例。普通应用 UI 的 `ViewRootImpl`、动画和窗口绘制仍主要由主线程实例驱动。

### 1.2 VSync 到达与回调执行之间还有 MessageQueue

系统侧 `EventThread("app")` 把 VSync 事件发送到应用的 `DisplayEventReceiver`。`FrameDisplayEventReceiver.onVsync()` 不会直接执行全部帧回调，而是创建一条异步 `Message`，按 VSync 时间戳投到绑定的 Handler。

Android 17 源码注释给出了消息顺序：

- 时间戳早于本次 VSync 的消息可以先执行；
- 没有更早消息时，VSync 消息可以立即处理；
- 若已有待处理 VSync，源码会记录诊断信息，但仍更新待处理数据；
- VSync 时间戳若落在 `System.nanoTime()` 未来，会被修正为当前时间。

因此，系统侧出现 `VSYNC-app` 不等于目标线程已经进入 `doFrame()`。两者之间可能存在 Looper 排队、同步代码执行和 CPU 调度等待。

---

## 二、一帧是怎样被安排出来的

### 2.1 状态变化先注册工作

一帧通常由这些事件触发：

- View 调用 `invalidate()` 或 `requestLayout()`；
- 输入需要在显示节奏上批量消费；
- 属性动画、滚动或其他帧动画仍在运行；
- Window、Insets、可见性或几何状态变化；
- 应用主动注册 `FrameCallback` 或 `VsyncCallback`。

这些调用先把工作放进 Choreographer 的某个 `CallbackQueue`。队列按 `dueTime` 排序。回调已经到期时，Choreographer 安排一帧；延迟回调尚未到期时，先投递 `MSG_DO_SCHEDULE_CALLBACK`，到期后再判断是否需要安排一帧。

### 2.2 `mFrameScheduled` 合并重复请求

`scheduleFrameLocked()` 只在 `mFrameScheduled == false` 时继续：

```java
if (!mFrameScheduled) {
    mFrameScheduled = true;
    if (isRunningOnLooperThreadLocked()) {
        scheduleVsyncLocked();
    } else {
        Message msg = mHandler.obtainMessage(MSG_DO_SCHEDULE_VSYNC);
        msg.setAsynchronous(true);
        mHandler.sendMessageAtFrontOfQueue(msg);
    }
}
```

这段代码用于说明合并机制。多个组件在同一待处理帧内注册工作，只会共享一次 VSync 申请。从其他线程安排帧时，Choreographer 先把异步消息放到所属 Looper 的队首，再由正确线程调用 `DisplayEventReceiver.scheduleVsync()`。

`mFrameScheduled` 只合并“一次帧分发请求”，不会合并不同回调队列中的业务内容。每个到期回调仍会在对应阶段执行。

### 2.3 `scheduleVsync()` 请求单次脉冲

`DisplayEventReceiver.scheduleVsync()` 调用原生方法 `nativeScheduleVsync()`。原生连接最终向 SurfaceFlinger EventThread 发出 `requestNextVsync()`，请求类型是单次 VSync。

如果动画还要继续，动画回调必须再次安排下一帧；如果 View 状态在本帧处理后又需要更新，`ViewRootImpl` 或相应组件也会再次注册工作。Choreographer 不会因为注册过一次回调就永久订阅每个显示周期。

---

## 三、ViewRootImpl、同步屏障与 Traversal

### 3.1 `scheduleTraversals()` 做了三件关键事情

Android 17 的 `ViewRootImpl.scheduleTraversals()` 在尚未安排 traversal 时：

```java
mTraversalScheduled = true;
postTraversalBarrier();
mChoreographer.postVsyncCallback(
        Choreographer.CALLBACK_TRAVERSAL, mTraversalCallback);
notifyRendererOfFramePending();
```

这段结构展示三个不同责任：

1. `mTraversalScheduled` 合并重复的布局/绘制请求；
2. `ViewRootImpl` 向主线程 MessageQueue 放置同步屏障；
3. traversal 以 `CALLBACK_TRAVERSAL` 类型的 `VsyncCallback` 注册到 Choreographer。

Android 17 的 `TraversalCallback.onVsync(FrameData)` 读取 `frameData.getFrameTimeNanos()`，然后进入 `doTraversal()` 和 `performTraversals()`。

### 3.2 同步屏障属于 ViewRootImpl 的调度策略

同步屏障会阻止屏障之后的普通同步消息继续执行，异步消息仍可穿过。Choreographer 的 VSync 调度消息和 `FrameDisplayEventReceiver` 消息会标记为异步，因此 traversal 能在屏障存在时获得执行机会。

常见表述“Choreographer 放置同步屏障”会把责任写错。放置和移除遍历屏障的是 `ViewRootImpl`；Choreographer 提供异步帧消息和回调分发。

`doTraversal()` 开始时会清除 `mTraversalScheduled` 并移除屏障，再进入 `performTraversals()`。屏障忘记移除会阻塞普通消息，因此这部分代码对异常返回和取消路径很谨慎。

---

## 四、五类回调的顺序与边界

`doFrame()` 的固定顺序是：

```text
CALLBACK_INPUT
  → CALLBACK_ANIMATION
  → CALLBACK_INSETS_ANIMATION
  → CALLBACK_TRAVERSAL
  → CALLBACK_COMMIT
```

五类回调各自解决不同问题：

| 阶段 | Android 17 跟踪子切片 | 主要工作 | 容易误解的地方 |
|------|--------------------------|----------|----------------|
| INPUT | `input` | 帧同步的批量输入消费、重采样等 | 普通输入事件也可以在其他时机处理 |
| ANIMATION | `animation` | 属性动画、`FrameCallback`、公开 `VsyncCallback` 等 | 回调只推进状态，不保证一定产生新缓冲 |
| INSETS_ANIMATION | `insets_animation` | 汇总系统栏、IME 等 Insets 动画更新 | 它位于 Animation 之后、Traversal 之前 |
| TRAVERSAL | `traversal` | ViewRoot 遍历、测量/布局/绘制、HWUI 交接 | 三项工作是否都执行取决于本帧状态 |
| COMMIT | `commit` | 绘制后收尾与提交后回调 | 该阶段观察到的帧时间可能因前面迟到而调整 |

### 4.1 INPUT 不等于全部输入处理

普通输入经 `InputChannel` 到达应用后，可以由主线程异步处理。`ViewRootImpl.scheduleConsumeBatchedInput()` 注册 `CALLBACK_INPUT`，用于把一批运动事件按本帧时间消费或重采样。

列表拖动时，手指仍在移动，INPUT 阶段常有批量运动事件处理；松手进入惯性滚动后，新输入减少，位移主要由 ANIMATION 阶段的滚动物理模型推进。INPUT 变短并不表示帧调度失效。

### 4.2 ANIMATION 包含两个公开入口

`postFrameCallback()` 把 `FrameCallback` 放进 `CALLBACK_ANIMATION`。公开的 `postVsyncCallback(VsyncCallback)` 也默认放进 ANIMATION；Android 17 另有隐藏重载，可指定回调类型。

这两个公开回调都是一次性的，执行后自动移除。连续动画或采样器需要在回调内再次注册。

### 4.3 INSETS_ANIMATION 为什么单独存在

Input 和普通 animation 都可能修改 Insets。Choreographer 在二者之后集中分发 `INSETS_ANIMATION`，把多个 ongoing inset animation 的更新汇总后再交给 View 系统。这样 Traversal 读取到的是本帧已经合并的 Insets 状态。

### 4.4 TRAVERSAL 不总是完整重走整棵树

`performTraversals()` 根据布局请求、窗口变化、脏区状态和绘制状态决定本帧是否执行测量、布局、绘制。硬件加速路径的绘制主要更新 RenderNode/DisplayList 并进入 `syncAndDrawFrame()`；像素绘制和 GPU 提交由后续 HWUI/RenderThread 完成。

看到 `traversal` 较长，要继续展开内部切片，区分：

- 大范围 measure/layout；
- DisplayList 重录；
- UI 线程业务回调；
- `syncAndDrawFrame()` 等待 RenderThread；
- 锁、Binder 或缓冲相关等待。

### 4.5 COMMIT 的帧时间可能更新

Choreographer 的注释明确指出：Traversal 若很重并跨过多个帧，COMMIT 阶段报告的帧时间可以更新，以更接近这批 UI 状态开始生效的帧。监控代码若混用不同阶段的帧时间，可能把这种调整误判为时钟异常。

---

## 五、`doFrame()` 的完整执行流程

### 5.1 从 VSync 事件到五阶段回调

下面的流程图把 Android 17 的关键分支放在一条线上：

```mermaid
flowchart TD
    A["FrameDisplayEventReceiver.onVsync()"] --> B["投递异步 Handler 消息"]
    B --> C["run() → Choreographer.doFrame()"]
    C --> D["更新缓冲积压状态"]
    D --> E{"需要主动延迟一帧？"}
    E -- "是" --> F["scheduleVsyncLocked() 后返回"]
    E -- "否" --> G["FrameData.update() 选择首选时间线"]
    G --> H{"mFrameScheduled？"}
    H -- "否" --> I["返回：本次没有工作"]
    H -- "是" --> J["计算抖动 / 必要时重同步帧时间"]
    J --> K{"帧时间倒退或 FPS 除数导致跳帧？"}
    K -- "是" --> L["申请下一次 VSync 后返回"]
    K -- "否" --> M["写入 FrameInfo，清除 mFrameScheduled"]
    M --> N["INPUT → ANIMATION → INSETS_ANIMATION"]
    N --> O["TRAVERSAL → COMMIT"]
```

收到 VSync 事件后，`doFrame()` 仍可能因为没有待处理工作、正在恢复缓冲积压、帧时间异常或 FPS 除数限制而不执行五阶段回调。

### 5.2 FrameData 先选择首选时间线

`doFrame()` 先用传入的 `VsyncEventData` 更新 `mFrameData`。一次 VSync 事件最多可携带多条候选时间线，每条包含：

- `vsyncId`；
- `expectedPresentationTime`；
- 截止时间 `deadline`。

平台同时标记 `preferredFrameTimelineIndex`。如果主线程已经迟到，`FrameData.update()` 会在现有候选中寻找仍有效的截止时间；现有候选都过期时，还可能通过 `DisplayEventReceiver.getLatestVsyncEventData()` 向 SurfaceFlinger 查询新数据。该 Binder 查询只在需要新时间线时发生，源码也注明它可能较慢。

### 5.3 抖动如何影响帧时间

`jitterNanos = System.nanoTime() - frameTimeNanos` 表示 `doFrame()` 开始时相对原始 VSync 时间的迟到量。迟到至少一个 `frameInterval` 时，Choreographer 会：

1. 计算跨过了多少个间隔；
2. 把用于动画的帧时间对齐到最近一个有效边界；
3. 必要时切换首选时间线；
4. 超过日志阈值时打印 `Skipped N frames`。

`debug.choreographer.skipwarning` 的默认阈值是 30。它只控制日志警告，不能当作系统判定卡顿的唯一门槛。没有 `Skipped N frames` 日志，仍可能错过截止时间；出现日志也只能说明主线程回调严重迟到，不能单靠它确认显示端结果。

### 5.4 写入 FrameInfo 后才分发回调

通过迟到和时间单调性检查后，Choreographer 将下列数据写进 `FrameInfo`：

- 预定 VSync 时间；
- 当前用于动画/绘制的帧时间；
- 首选时间线的 `vsyncId`；
- 截止时间；
- `doFrame()` 实际开始时间；
- 当前 `frameInterval`。

随后清除 `mFrameScheduled`，按顺序运行五类回调。新的状态变化可以在当前回调执行期间再次安排下一帧。

### 5.5 `doFrame()` 结束仍处在应用生产阶段

Traversal 可能把本帧状态交给 RenderThread，但以下工作可以继续发生：

- RenderThread 准备 RenderNode 树；
- GPU 命令提交和执行；
- `dequeueBuffer()`/`queueBuffer()`；
- 获取栅栏发出信号；
- SurfaceFlinger 事务、锁存和合成；
- HWC 显示提交与显示后段。

因此，“`doFrame()` 用时小于刷新周期”不能证明这一帧按时显示。需要用 FrameMetrics、FrameTimeline、RenderThread 和显示侧证据继续判断。

---

## 六、帧时间：`frameTimeNanos`、截止时间与预计呈现

### 6.1 `frameTimeNanos` 是稳定时间基准

`FrameCallback.doFrame(long frameTimeNanos)` 接收的是系统为本帧选定的帧时间，时间基准与 `System.nanoTime()` 一致。它可以早于回调开始执行的当前时间。同一次帧分发中的所有回调共享这个稳定时间，有利于动画保持一致。

动画应根据帧时间计算进度，不要用“每次回调固定增加 16.6 ms”。刷新率可变、应用渲染帧率可低于显示 VSync 频率，主线程也可能迟到或跳过候选时间线。

### 6.2 截止时间回答“何时必须准备好”

`FrameTimeline.getDeadlineNanos()` 表示该候选帧必须就绪的时刻。它比“当前屏幕刷新周期是多少”更适合判断应用是否命中预算，因为应用唤醒偏移、SF 预算、刷新率和候选时间线都会影响截止时间。

### 6.3 预计呈现时间回答“系统预计何时呈现”

`FrameTimeline.getExpectedPresentationTimeNanos()` 表示平台预计该时间线何时呈现。这个值属于预测时间，不代表显示栅栏或实际显示结果。比较预计与实际呈现时间，才能判断这一帧是否按计划显示。

### 6.4 VSync ID 是跨层关联键

`FrameTimeline.getVsyncId()` 用于把 HWUI 生产的帧与 SurfaceFlinger 保存的时间线数据关联起来。Android 17 的跟踪切片名为 `Choreographer#doFrame <vsyncId>`，RenderThread 和 SurfaceFlinger 的相应切片也会带令牌。

一个应用 VSync 可以携带多个候选时间线，最终帧也可能丢弃或换到后续目标。不要把“第几个 VSync 计数器”当成跨进程关联键。

---

## 七、FrameCallback：适合观察回调节奏，不等于显示帧率

### 7.1 连续采样必须主动续订

下面的 Kotlin 示例只测量 Choreographer 回调间隔，包含显式启停和去重：

```kotlin
class CallbackCadenceSampler(
    private val choreographer: Choreographer = Choreographer.getInstance(),
    private val onInterval: (Long) -> Unit,
) : Choreographer.FrameCallback {
    private var running = false
    private var lastFrameTimeNanos = 0L

    fun start() {
        if (running) return
        running = true
        lastFrameTimeNanos = 0L
        choreographer.postFrameCallback(this)
    }

    fun stop() {
        running = false
        choreographer.removeFrameCallback(this)
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running) return
        if (lastFrameTimeNanos != 0L) {
            onInterval(frameTimeNanos - lastFrameTimeNanos)
        }
        lastFrameTimeNanos = frameTimeNanos
        if (running) {
            choreographer.postFrameCallback(this)
        }
    }
}
```

这段代码应在 Choreographer 所属 Looper 线程启停。它能观察回调节奏、长间隔和节奏抖动，但不能回答缓冲是否提交、GPU 是否完成、SF 是否锁存或实际何时呈现。回调自身也会给主线程增加工作，采样逻辑应保持轻量。

### 7.2 不要用固定阈值数“掉帧”

常见实现把间隔除以 `16_666_667`，再把商减一当作掉帧数。这个算法在 90/120 Hz、动态刷新率、ARR、应用帧率覆盖和主动降帧场景都会误判。

如果只统计回调节奏，应同时记录当前帧间隔或显示/渲染帧率；如果目标是判断用户可见卡顿，应使用 FrameTimeline、FrameMetrics 或 JankStats 等呈现相关数据。

---

## 八、VsyncCallback 与多候选 FrameTimeline

### 8.1 API 33+ 的公开入口

`postVsyncCallback()` 从 API 33 提供 `FrameData`。下面的示例在回调有效期内复制基础值：

```kotlin
Choreographer.getInstance().postVsyncCallback { data ->
    val preferred = data.preferredFrameTimeline
    val vsyncId = preferred.vsyncId
    val deadlineNanos = preferred.deadlineNanos
    val expectedPresentNanos = preferred.expectedPresentationTimeNanos
    record(vsyncId, deadlineNanos, expectedPresentNanos)
}
```

`FrameData` 和其中的 `FrameTimeline` 只在 `onVsync()` 回调期间有效。源码在回调前后切换 `mInCallback`，离开回调再访问会抛出 `IllegalStateException`。需要异步保存时，只复制长整型等基础值，不要缓存对象引用。

### 8.2 多条时间线用来表达可选目标

`getFrameTimelines()` 返回按时间排序的候选项，`getPreferredFrameTimeline()` 返回平台当前推荐项。多候选设计允许系统在高刷新率、不同渲染节奏或主线程迟到时表达后续合法呈现目标。

应用通常遵循首选时间线。低延迟渲染器或系统组件若要选择其他时间线，需要同时理解缓冲提交与 SurfaceFlinger 的令牌约定；只改变业务动画时间不能改变系统实际采用的显示帧。

---

## 九、FrameMetrics：观察窗口帧的阶段耗时

### 9.1 FrameCallback 与 FrameMetrics 解决不同问题

| 工具 | 观察起点 | 能回答 | 不能单独回答 |
|------|----------|--------|--------------|
| `FrameCallback` | Choreographer 回调 | 回调间隔、主线程帧节奏 | GPU/呈现、具体阶段耗时 |
| `VsyncCallback` | 应用 VSync 分发 | 截止时间、预计呈现、VSync ID | 实际呈现、窗口各阶段耗时 |
| `FrameMetrics` | 硬件加速窗口已渲染帧 | 输入/动画/布局/绘制/同步/GPU/总耗时/截止时间 | 独立 Surface 内容、面板光学完成 |
| Perfetto FrameTimeline | 应用 SurfaceFrame 与 SF DisplayFrame | 预计/实际、卡顿类型、呈现类型、跨层令牌 | 未采集的厂商/面板细节 |

### 9.2 关键指标怎么读

`FrameMetrics` 从 API 24 开始提供窗口帧指标。常用字段包括：

- `INPUT_HANDLING_DURATION`；
- `ANIMATION_DURATION`；
- `LAYOUT_MEASURE_DURATION`；
- `DRAW_DURATION`；
- `SYNC_DURATION`；
- `COMMAND_ISSUE_DURATION`；
- `SWAP_BUFFERS_DURATION`；
- `TOTAL_DURATION`；
- `INTENDED_VSYNC_TIMESTAMP` 与 `VSYNC_TIMESTAMP`；
- API 31 的 `GPU_DURATION` 和 `DEADLINE`；
- API 36 的 `FRAME_TIMELINE_VSYNC_ID`。

`TOTAL_DURATION` 不一定等于各阶段相加，因为部分阶段可以并行。官方 API 契约指出，`TOTAL_DURATION < DEADLINE` 表示应用在分配的窗口帧预算内完成；这仍不能替代 SF/DisplayHAL 的实际呈现判断。

### 9.3 监听器中先复制再异步处理

下面的写法展示正确的对象生命周期：

```kotlin
window.addOnFrameMetricsAvailableListener(
    { _, metrics, droppedReports ->
        val snapshot = FrameMetrics(metrics)
        metricsWorker.execute {
            consume(snapshot, droppedReports)
        }
    },
    metricsHandler,
)
```

回调传入的 `FrameMetrics` 对象会复用，离开回调后不能继续持有原引用。监听器执行太慢还会丢报告，`droppedReports` 必须一并记录。回调线程只负责复制与入队，聚合、日志和上报放到其他线程。

### 9.4 适用范围

FrameMetrics 面向某个硬件加速窗口。`SurfaceView`、视频、相机、游戏引擎等可能有独立 Surface 和生产节奏；宿主窗口的 FrameMetrics 不能代表这些内容图层的每一帧。此类场景要结合对应生产者、图层和 FrameTimeline。

---

## 十、在 Perfetto 中定位 Choreographer 问题

### 10.1 先看哪些轨迹

Android 17 常见证据包括：

- 应用主线程：`Choreographer#doFrame <vsyncId>`；
- doFrame 子阶段：`input`、`animation`、`insets_animation`、`traversal`、`commit`；
- RenderThread：`DrawFrame` 及同一 token；
- 应用 FrameTimeline：Expected 与 Actual；
- SurfaceFlinger FrameTimeline：DisplayFrame Expected 与 Actual；
- `BufferTX - <layerName>`、缓冲/栅栏相关轨迹；
- `sched_wakeup`、`sched_switch`、运行中/可运行/休眠状态。

跟踪配置、平台版本和设备实现会影响轨迹是否出现。没有某条计数器轨迹时，先检查数据源，不要用名称猜测机制失效。

### 10.2 Expected 与 Actual 怎么读

Perfetto FrameTimeline 从 Android 12 开始可用：

- 应用 Expected 切片表示系统给应用生产目标帧的预算窗口，起点是 Choreographer 回调计划运行的时刻；
- 应用 Actual 切片从 `Choreographer#doFrame` 或 NDK VSync 回调实际开始，结束时间取 GPU 完成与缓冲提交中更晚者；
- SF Actual 切片覆盖 SF 工作以及其下方 Composer/DisplayHAL 到屏幕更新的显示栈区间；
- 应用 SurfaceFrame 与 SF DisplayFrame 可通过令牌和流向关联。

Expected 切片长度不保证等于一个固定显示周期。应用/SF 工作预算、刷新率和时间线选择都会影响它。

### 10.3 一条可复用的 SQL

下面的查询用于列出目标进程的应用 Actual FrameTimeline：

```sql
SELECT
  p.name AS process_name,
  a.ts,
  a.dur,
  a.surface_frame_token,
  a.display_frame_token,
  a.jank_type,
  a.on_time_finish,
  a.present_type,
  a.layer_name
FROM actual_frame_timeline_slice AS a
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
ORDER BY a.ts;
```

查询结果提供逐帧令牌、卡顿分类和图层。把包名换成目标进程后，再用 `surface_frame_token` 回到界面选择对应切片，查看流向哪一个 DisplayFrame。

### 10.4 常见现象的证据解释

| 现象 | 先检查 | 可能原因 |
|------|--------|----------|
| `VSYNC-app` 已出现，`doFrame` 晚 | Looper 早期消息、可运行态等待、长任务、锁、Binder、GC | 回调尚未得到执行机会 |
| `doFrame` 很长 | 五个子阶段和内部切片 | 输入/动画/遍历/RenderThread 同步成本 |
| `doFrame` 不长，应用 Actual 很长 | RenderThread、GPU、`queueBuffer` | 应用后半段仍未完成 |
| 应用按时完成，SF Actual 晚 | SF CPU/GPU、HWC、DisplayHAL | 系统显示侧错过目标 |
| 回调节奏平稳，FrameTimeline 高延迟 | Expected/Actual 整体偏移、缓冲积压 | 帧率平稳但输入到显示延迟增加 |
| 一次令牌对应多个应用 Actual 切片 | `layer_name`、`is_buffer` | 同一进程更新多个 Surface/图层 |

### 10.5 不要把所有 `doFrame` 长度和刷新周期硬比较

“60 Hz 超过 16.6 ms 就算卡顿”只适合做粗筛。现代设备可能运行 90/120 Hz、动态刷新率、ARR 或应用帧率覆盖；应用截止时间也不等于裸显示周期。

逐帧判断优先使用：

1. Expected 时间线的截止时间；
2. 应用 Actual 的 `on_time_finish`、`jank_type`；
3. SF Actual 的呈现结果；
4. 同一令牌的线程、GPU、缓冲和显示证据。

---

## 十一、缓冲积压恢复

### 11.1 它处理的是队列积压后的延迟

Android 17 的标准 HWUI/BLAST 路径会把等待缓冲释放的时长回传给 Choreographer：

```text
BBQBufferQueueProducer::waitForBufferRelease() 统计等待时长
  → BLASTBufferQueue → CanvasContext/HardwareRenderer 回调
  → ViewRootImpl 绑定 Choreographer.onWaitForBufferRelease()
  → 等待时长超过上一帧间隔的一半
  → 标记缓冲积压
```

`BBQBufferQueueProducer` 是 Android 17 标准应用窗口的 BLAST 生产者实现。它在没有空闲缓冲、`dequeueBuffer()` 必须等待释放时进入这条路径。`onWaitForBufferRelease()` 只负责设置状态，具体动作在后续 `doFrame()` 开始时由 `updateBufferStuffingState()` 决定。

### 11.2 恢复动作有 DELAY_FRAME 和 OFFSET

当系统判定需要恢复时：

- `DELAY_FRAME`：主动申请下一次 VSync 并结束本次 `doFrame()`，给队列消费留时间；
- `OFFSET`：恢复期间把动画时间线向前偏移一个帧间隔；
- `NONE`：无需动作或恢复已经结束。

相关 aconfig 标志可以控制同一段动画是否多次恢复，以及累计主动延迟是否受 100 ms 阈值限制。设备上的标志取值必须从配置或跟踪数据确认。

Perfetto 可搜索：

- `Buffer stuffing recovery`；
- `buffer stuffed`；
- `Negative offset`；
- `dequeueBuffer` 等待；
- FrameTimeline 的 `Buffer Stuffing` 卡顿类型。

看到主动延迟时，不能把这帧简单归因于主线程计算慢。还要检查积压是否下降、后续输入延迟是否恢复。

---

## 十二、Compose 与 Choreographer 的关系

### 12.1 Compose 有自己的阶段，但仍使用 Android 帧时钟

Compose 官方把 UI 更新分为：

1. 组合（Composition）：决定显示哪些 UI；
2. 布局（Layout）：测量与放置；
3. 绘制（Drawing）：绘制内容。

Compose 运行时使用帧时钟推进动画和需要按帧运行的状态，Android 宿主最终仍参与 ViewRoot/HWUI 的窗口生产路径。纯 Compose 窗口通常与 View 页面共享应用窗口、RenderThread、BLAST、SurfaceFlinger 和 HWC 后半段。

### 12.2 不要把 Compose 三阶段强行等同于 Choreographer 五阶段

Choreographer 的五类回调是 Android Looper 上的调度分类；Compose 的组合、布局、绘制是 UI 运行时的工作阶段。二者粒度不同。

一次 Compose 状态变化可能：

- 触发重组；
- 只触发重新布局；
- 只触发重绘；
- 因状态读取位置不同而跳过前面的阶段。

不能写成“Compose 的三阶段始终全部位于一个固定 Traversal 子切片”。跟踪数据中要同时看 `Choreographer#doFrame`、Compose 跟踪、宿主遍历和 RenderThread。

### 12.3 Platform 与 Jetpack 版本要分别记录

Android 17 / API 37 的平台标签不能确定应用使用的 Compose 运行时、编译器插件、Kotlin 或 BOM 版本。同一系统镜像可以运行多种 Compose 版本。

做性能对比时至少记录：

- Android 构建版本/标签与厂商构建版本；
- Compose Runtime/UI 与 BOM 版本；
- Kotlin 与 Compose 编译器插件；
- 调试、可分析或发布构建；
- 是否开启组合阶段跟踪；
- 刷新率、热状态和测试输入。

没有这些条件，Compose 切片的跨版本差异很难归因。

---

## 十三、常见误区

### 误区 1：一次 `invalidate()` 对应一次 VSync

`ViewRootImpl.mTraversalScheduled` 和 `Choreographer.mFrameScheduled` 都会合并重复请求。多次失效可以共享一次 traversal 和一次 VSync 申请。

### 误区 2：每个 VSync 都会执行 `doFrame()`

应用按需申请单次 VSync。没有待处理帧时不会持续执行；收到事件后也可能因无工作、缓冲恢复、帧时间检查或 FPS 除数限制提前返回。

### 误区 3：INPUT 阶段处理所有触摸事件

普通输入可以异步处理。Choreographer INPUT 重点包含批量运动事件的帧同步消费和重采样。

### 误区 4：`FrameCallback` 就是帧率监控的完整答案

它只能观察回调节奏。用户可见帧率和卡顿还涉及 RenderThread、GPU、缓冲、SF 与显示提交。

### 误区 5：`doFrame()` 超过显示周期就一定掉帧

截止时间、候选时间线和后半段执行共同决定结果。使用 FrameTimeline 的预计/实际结果和卡顿类型判断具体帧。

### 误区 6：同步屏障由 Choreographer 插入

标准窗口的遍历屏障由 `ViewRootImpl` 插入和移除；Choreographer 的异步消息能够穿过屏障。

### 误区 7：COMMIT 表示缓冲已显示

COMMIT 是应用回调阶段。缓冲生产、SF 合成、HWC 显示提交和面板显示仍在后面。

---

## 十四、版本演进

| 版本 | 与 Choreographer 相关的变化 | 分析影响 |
|------|------------------|----------|
| Android 4.1 / API 16 | Project Butter 引入 Choreographer | 应用输入、动画和遍历开始围绕 VSync 调度 |
| Android 7.0 / API 24 | FrameMetrics 公开 | 可按窗口帧观察阶段耗时 |
| Android 8.0 / API 26 | FrameMetrics 增加 intended/actual VSync 时间 | 可识别 UI 线程未及时响应 intended VSync |
| Android 10 / API 29 | Choreographer 已包含独立的 Insets 动画回调类别 | 五阶段顺序包含 `INSETS_ANIMATION` |
| Android 12 / API 31 | SurfaceFlinger/Perfetto FrameTimeline 可用；FrameMetrics 增加 GPU 时长/截止时间 | 应用与 SF 可以按令牌分析预计/实际结果；此时还没有 API 33 的公开 `Choreographer.FrameData` |
| Android 13 / API 33 | 公开 `VsyncCallback`、`FrameData`、`FrameTimeline` | 应用可读取候选时间线、截止时间和 VSync ID |
| Android 16 / API 36 | FrameMetrics 公开 `FRAME_TIMELINE_VSYNC_ID` | 线上窗口指标更容易与跟踪令牌关联 |
| Android 17 / API 37 | 源码基线；五类回调、多时间线、缓冲积压恢复均按 `android-17.0.0_r1` 核验 | 不把当前实现倒推成 Android 17 首次新增 |

版本表只声明有公开 API 或旧 tag 证据的起点。Android 17 当前存在的内部方法，不自动等于该版本新增。

---

## 十五、框架与内核的排查边界

Choreographer 位于用户态框架，不直接决定线程何时获得 CPU。`FrameDisplayEventReceiver` 已投递异步消息后，目标线程仍可能处于：

- 运行中（Running）：正在执行其他代码；
- 可运行（Runnable）：已经可运行，但在运行队列等待；
- 休眠/阻塞（Sleeping/Blocked）：等待锁、futex、Binder、缓冲或其他资源。

框架源码回答“回调何时被安排、按什么顺序执行”；内核调度轨迹回答“线程何时被唤醒、何时被调度上 CPU”。内核行为以 `android17-6.18-2026-06_r6` 为准，通用入口是 `kernel/sched/core.c` 和 `kernel/sched/fair.c`。

Perfetto 中看到从唤醒到运行的长间隔时，再检查优先级、CFS 调度、CPU 争用、cpuset/uclamp 和热状态。没有对应跟踪数据或设备配置，不能仅凭 `doFrame()` 起点晚就推断厂商调度策略。

---

## 十六、排查清单

遇到 Choreographer 相关卡顿时，按下面顺序核对：

- 本帧由什么状态变化或回调触发？
- `mFrameScheduled` 前是否已有待处理帧？
- `FrameDisplayEventReceiver.onVsync()` 到 `doFrame()` 之间等了多久？
- 目标线程在等待 Looper、CPU、锁、Binder 还是缓冲？
- 首选时间线的截止时间与预计呈现时间是多少？
- `doFrame()` 是否发生抖动重同步、帧时间倒退或主动延迟？
- INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT 哪一段变长？
- Traversal 内是测量/布局/绘制，还是 `syncAndDrawFrame()` 等待？
- 应用 Actual 是否按时结束？GPU 与缓冲提交谁更晚？
- SF DisplayFrame 是否按时呈现？
- 是否出现 `Buffer Stuffing`，恢复动作后积压是否下降？
- 当前刷新率、渲染帧率、Compose 版本和跟踪配置是否与对照组一致？

---

## Android 17 的 Choreographer 调度边界

1. Choreographer 是绑定 Looper 的帧回调调度器，负责安排应用帧起点，不负责后续显示完成。
2. 回调先进入五个队列，`mFrameScheduled` 合并同一待处理帧的 VSync 申请。
3. 标准 View traversal 的同步屏障由 `ViewRootImpl` 管理，异步 VSync 消息可以穿过屏障。
4. 五阶段顺序固定为 INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT；各阶段是否有工作取决于到期回调。
5. `doFrame()` 还会处理时间线选择、抖动、帧时间单调性、FPS 除数限制和缓冲积压恢复。
6. `frameTimeNanos` 是稳定动画时间，截止时间与预计呈现时间分别描述就绪约束和呈现目标。
7. `FrameCallback` 适合观察回调节奏；FrameMetrics 和 Perfetto FrameTimeline 提供更完整的窗口与呈现证据。
8. Compose 的 UI 阶段与 Choreographer 回调分类粒度不同，平台和 Jetpack 版本需要分别记录。

---

## 参考资料

- AOSP `android-17.0.0_r1`：`core/java/android/view/Choreographer.java`
- AOSP `android-17.0.0_r1`：`core/java/android/view/DisplayEventReceiver.java`
- AOSP `android-17.0.0_r1`：`core/java/android/view/ViewRootImpl.java`
- AOSP `android-17.0.0_r1`：`graphics/java/android/graphics/HardwareRenderer.java`
- AOSP `android-17.0.0_r1`：`libs/hwui/renderthread/CanvasContext.cpp`
- AOSP `android-17.0.0_r1`：`core/java/android/view/FrameMetrics.java`
- AOSP `android-17.0.0_r1`：`core/java/android/view/Window.java`
- AOSP `android-17.0.0_r1`：`frameworks/native/services/surfaceflinger/Scheduler/EventThread.cpp`
- AOSP `android-17.0.0_r1`：`frameworks/native/libs/gui/DisplayEventReceiver.cpp`
- AOSP `android-17.0.0_r1`：`frameworks/native/libs/gui/BLASTBufferQueue.cpp`
- Android common kernel `android17-6.18-2026-06_r6`：`kernel/sched/core.c`、`kernel/sched/fair.c`
- [Choreographer API](https://developer.android.com/reference/android/view/Choreographer)
- [Choreographer.FrameData API](https://developer.android.com/reference/android/view/Choreographer.FrameData)
- [Choreographer.FrameTimeline API](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Jetpack Compose phases](https://developer.android.com/develop/ui/compose/phases)
