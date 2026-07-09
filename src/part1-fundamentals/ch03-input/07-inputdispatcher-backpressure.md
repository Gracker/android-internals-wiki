---

title: "InputDispatcher 反压与无响应窗口降级"
chapter: "3.7"
section: "3.7"
status: ready-for-review
drafted_date: "2026-05-16"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/docs/anr.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/tools/dumpsys"
  - type: obsidian
    path: "DeepResearch/2026-05-10-inputdispatcher-backpressure.md"
  - type: obsidian
    path: "intake/daily-info/2026-05-16.md"
tags: [input, inputdispatcher, anr, latency, backpressure]
related_chapters: ["3.1", "3.2", "3.5", "9.2", "9.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/源码结构"
task6_result: pass-light-edit
last_task6_audit: "2026-06-12"
last_task6_at: "2026-07-09T18:14:16+08:00"
task2b_result: fixed
last_task2b_at: "2026-06-12"
last_task2b_lite_at: "2026-06-12"
reviewed_date: "2026-06-19"
reviewed_by: "openclaw-task6"
last_task9_audit: "2026-07-09"
last_task9_audit_log: "logs/deep-review/2026-07-09-13-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
task6_reviewed_date: "2026-06-19"
auto_promoted: true
last_task2b_verifier_at: "2026-07-05T03:26:57+0800"
last_verified: "2026-07-09"
last_verified_against: "AOSP android-17.0.0_r1（主线复核, 2026-07-09）; AOSP android-16.0.0_r1（历史差异参照）"
task9_result: "auto-fixed"
task9_state: "reviewed"
task2b_state: "fixed"
task6_state: "revisiting"
pipeline_stage: "task6_pending"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-09"
last_task9_at: "2026-07-09T16:30:36+08:00"
last_task9_autofix_at: "2026-07-09"
last_task9_review_log: "logs/deep-review/2026-07-09-16-deep-review.md"
updated_by: "openclaw-task9"
updated_date: "2026-07-09"
p0: 1
p1: 0
p2: 0
task9_review_notes: "2026-05-16 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；满足 Task6 pass 且 queue 无 pending，自动晋升 finalized。 | 2026-05-24 Task9 闲时抽检：needs-rework。P0 0 / P1 1 / P2 0；applicable_versions 覆盖 Android 10-17，但正文按 Android 16 的 mAnrTracker/processAnrsLocked/shouldPruneInboundQueueLocked/canReceiveForegroundTouches 讲主线，未交代 Android 10-12 的实现差异和 Android 17 未验证边界。 | 2026-05-25 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；版本边界已收窄到 Android 13-16，Task6 pass 且 queue 无 pending，自动晋升 finalized。 | 2026-06-12 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；源码锚点复核 android-16.0.0_r1，版本边界保持 Android 13-16；Task6 未通过，未自动晋升。 | 2026-06-18 Task9 闲时抽检 auto-fix：P0 0 / P1 1 / P2 0；AOSP android-17.0.0_r1 已发布，修正“Android 17 tag 未发布”的过期版本边界，并标注 no focused window ANR 状态在 Android 17 改为 mNoFocusedWindowAnrState，回到 Task6 复审。 | 2026-06-19 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；源码与版本边界复核通过，Task6 已通过且 queue 无 pending，自动晋升 finalized / ready-to-publish；详见 logs/deep-review/2026-06-19-01-deep-review.md。 | 2026-06-22 16 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 0；复核 AOSP android-16.0.0_r1/17.0.0_r1 InputDispatcher.cpp；Android 17 no focused window ANR 状态差异已在版本边界中标注，正文未越过 API 37。 | 2026-07-09 13 Task9 闲时抽检 auto-fix：P0 0 / P1 1 / P2 0；Android 17 基准抽检发现正文仍以 android-16.0.0_r1 为主线，已重锚到 android-17.0.0_r1，并将 no focused window ANR 主线字段改为 mNoFocusedWindowAnrState；回 Task6 复审。 | 2026-07-09 16 Task9 deep-review AUTO-FIX：P0 1 / P1 0 / P2 0；修正 `canReceiveForegroundTouches()` 与 `connection->responsive` 的职责归因；回 Task6 复审。"
verifier_checked: 2026-07-09
---

# 3.7 InputDispatcher 反压与无响应窗口降级

> **版本边界说明**：本章主线以 AOSP android-17.0.0_r1 为准。涉及的关键机制不在同一版本引入——`mAnrTracker` 和 `shouldPruneInboundQueueLocked` 始于 Android 11，`processConnectionResponsiveLocked` 始于 Android 12，`canReceiveForegroundTouches` 始于 Android 13。Android 17 的相关锚点位于 `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`；no focused window ANR 主线状态为 `mNoFocusedWindowAnrState`，内部保存等待中的 application、event id、`timeoutDuration`、`timeoutEndTime` 和 pre-ANR 标记。Android 16 及更早版本使用 `mAwaitedFocusedApplication` / `mNoFocusedWindowTimeoutTime` 等字段；Android 10 的 InputDispatcher 仍在 `services/inputflinger/InputDispatcher.cpp`（未迁入 `dispatcher/` 子目录），ANR 等待走 `mInputTargetWaitCause` / `mInputTargetWaitTimeoutTime` / `onANRLocked()`。排查旧版本时先确认源码路径和 ANR 等待模型，不要把 Android 17 字段名直接套回旧源码。

<!-- outline-start -->
## 要点

### 🔹 输入通道的天然反压点
说明 `InputChannel` 写入、`WOULD_BLOCK` 与 `waitQueue` 之间的反压关系。

### 🔹 waitQueue、inboundQueue 与 ANR 计时边界
区分 `inboundQueue`、`outboundQueue`、`waitQueue` 的含义，并说明 Input ANR 从交付后等待回执开始计时。

### 🔹 目标窗口无响应后的连接隔离
说明连接进入 `responsive=false` 后如何被跳过、取消事件如何生成，以及恢复条件。

### 🔹 跨应用切换时的队列裁剪策略
说明 no focused window 等待期间，新触摸目标如何触发队列裁剪，避免旧应用拖住新目标。

### 🔹 Perfetto / dumpsys input 的观察入口
列出 `dumpsys input` 与 Perfetto counter 中可观察的字段、轨道和判读边界。

### 🔹 与应用主线程卡顿、Binder 阻塞的归因边界
说明 `waitQueue` 只能作为症状入口，根因仍需回到 App 主线程、Binder、调度和窗口状态。

## 扩展

### 🔸 游戏/高频触控场景下的反压放大
说明高频触控如何放大队列现象，并区分 AOSP 能确认的机制与厂商差异。

### 🔸 厂商输入调度策略与可验证边界
说明厂商定制结论需要哪些实机证据，避免把宣传或主观手感写成通用机制。

<!-- outline-end -->

## 为什么单独看 InputDispatcher 反压

第 3.1 节已经给出 Input 事件从硬件到 App 的完整路径，第 3.2 节讨论触摸响应延迟。本节聚焦 InputDispatcher 内部：事件已经进入 InputDispatcher，目标窗口却没有及时消费时，系统怎样限制积压、怎样判定 Input ANR，怎样避免一个无响应窗口拖住新的输入目标。

这类问题在 trace 里很容易误判。`WaitQueue` 变长只能说明事件已经发给目标连接、还没收到 App 侧 `Finished` 回执；它不能直接等同于 App 主线程 MessageQueue 变长，也不能证明 Binder 调用就是根因。分析时要把 InputDispatcher 的队列状态、App 主线程栈、Binder 线程、CPU 调度和窗口焦点变化放到同一个时间窗口里看。详见 9.3 节。

## 输入通道的天然反压点

InputDispatcher 到 App 的事件面走 `InputChannel`。窗口连接建立时，服务端和客户端各持有一端 channel；事件分发阶段，`InputDispatcher::publishMotionEvent()` / `publishKeyEvent()` 经 `InputPublisher` 写入目标连接。这里要区分清楚：事件本身的传输走 channel fd，不走 Binder；Binder 主要参与窗口和 channel 的建立、传递与策略回调。详见 1.17 节与 3.1 节。

AOSP android-17.0.0_r1 的 `InputDispatcher::startDispatchCycleLocked()` 在写入失败时会检查返回码。返回 `WOULD_BLOCK` 时，代码分两种情况处理：

- `waitQueue` 为空却写不进去，说明 channel 状态异常，系统会走 `abortBrokenDispatchCycleLocked()`，把连接标为 broken，并通知策略层清理。
- `waitQueue` 非空时，说明 App 侧还有已交付事件没有完成，channel 缓冲也被顶住。InputDispatcher 停止继续向该连接写入，等待 App 消费并回执。

这就是输入管道的反压点。它依赖底层 channel 的可写性，不靠 Framework 额外猜测 App 是否繁忙。只要 App 侧没有及时读事件或发送 `Finished`，新的事件就会停在 `outboundQueue` 或更上游的 `inboundQueue`，直到目标连接恢复、超时、窗口被移除，或策略层做取消处理。


## waitQueue、inboundQueue 与 ANR 计时边界

InputDispatcher 内部有三类队列需要区分：

| 队列 | 含义 | 典型观察结论 |
|------|------|--------------|
| `inboundQueue` | 已进入 InputDispatcher、等待路由和分发的事件 | Dispatcher 忙、策略等待、焦点窗口未就绪，或前序事件阻塞了分发 |
| `outboundQueue` | 已确定目标连接、等待写入该连接的事件 | 目标连接暂时不可写，或前序 waitQueue 未清空导致继续派发受限 |
| `waitQueue` | 已写给 App、等待 App 返回 `Finished` 的事件 | App 侧已收到事件但未及时 ACK，常见原因是主线程处理慢、卡死、未及时读 channel |

ANR 计时绑定在 `waitQueue` 条目上。事件写给目标连接后，`deliveryTime` 和 `timeoutTime` 会被记录，条目从 `outboundQueue` 移入 `waitQueue`，`mAnrTracker` 记录最近的超时时间。App 侧返回 `Finished` 后，`handleReceiveCallback()` 读取回执，`finishDispatchCycleLocked()` 投递命令，`doDispatchCycleFinishedCommand()` 按 `seq` 从 `connection->waitQueue` 移除对应条目，并同步从 `mAnrTracker` 删除。

这条边界决定了排查顺序：Input ANR 不是从事件进入 `inboundQueue` 的瞬间开始计时，也不是按 App 主线程 MessageQueue 的长度计时。只有事件已经交给目标连接、等待回执超过窗口或应用的 dispatch timeout，InputDispatcher 才会把该连接判为无响应。Android Developers 的 ANR 文档也把 Input dispatching timed out 描述为应用没有在约 5 秒内响应按键或触摸事件。具体超时时间在系统内可由 window/application 的 dispatching timeout 影响，不要把 5 秒写成所有设备、所有窗口都不可变的常量。


## 目标窗口无响应后的连接隔离

`processAnrsLocked()` 会检查 `mAnrTracker` 中最近的超时点。超时发生后，当前连接的 `responsive` 会被置为 `false`，tracker 中该连接的 token 会被移除，`onAnrLocked(connection)` 再做一次恢复检查：如果 `waitQueue` 已经空了，就不继续上报；如果仍有积压，系统基于最早进入 `waitQueue` 的条目生成 reason，调用 `processConnectionUnresponsiveLocked()` 通知策略层窗口无响应，并调用 `cancelEventsForAnrLocked()` 合成取消事件。

隔离不是把整个输入系统停掉。AOSP 中多处会跳过无响应连接：全局 monitor 如果 `responsive=false` 会被忽略；触摸命中窗口时，目标解析阶段会检查 `connection->responsive`，为 `false` 时拒绝向该窗口发送新的触摸。`canReceiveForegroundTouches()` 只决定目标是否带 `FOREGROUND` 标记，不负责响应性判断。这样做的目的很明确：已经卡住的窗口不再继续吞新输入，其他窗口和系统手势仍有机会前进。

连接恢复也有明确回路。App 之后返回 `Finished`，对应 `waitQueue` 条目被移除；`isConnectionResponsive()` 确认剩余条目没有过期后，`processConnectionResponsiveLocked()` 通知策略层窗口恢复。这里的恢复条件仍然基于 InputDispatcher 自己的 `waitQueue`，不是基于 App 业务状态。


## 跨应用切换时的队列裁剪策略

输入反压最影响体验的场景，是用户已经不想等当前 App，转而点击另一个 App 或系统区域。InputDispatcher 对这种情况有专门的裁剪逻辑。

在 no focused window 等待路径中，Android 17 通过 `mNoFocusedWindowAnrState` 记录等待中的应用、事件 id、超时时长和 `timeoutEndTime`。如果用户此时按下新的触摸点，`shouldPruneInboundQueueLocked()` 会命中测试触摸位置：目标窗口属于另一个 application token，或存在可响应的 spy window 时，InputDispatcher 将当前新事件标为 `mNextUnblockedEvent`。后续调度会把这个事件之前的部分 focus-dispatched 事件按 `DropReason::BLOCKED` 丢弃，直到队列推进到新的可放行事件。

这不是“丢掉所有触摸”。源码只在特定条件下剪掉阻塞在前面的旧事件：触发点是新的 pointer down，目标是另一个应用或可响应的 spy window，目的在于避免旧应用迟迟没有焦点窗口时继续拖住新目标。对于正在进行的 pointer gesture，系统还会保留必要的状态，不会粗暴切断所有后续事件。

这条策略解释了一个常见现象：Input ANR 发生或即将发生时，用户点别的应用、返回桌面、拉系统手势，有时仍然能继续响应。无响应窗口被隔离，新的输入目标绕开旧队列继续前进。


## Perfetto / dumpsys input 的观察入口

观察 InputDispatcher 反压，优先看两个入口。

`adb shell dumpsys input` 能直接看到 Input Dispatcher State。Android Developers 的 dumpsys 文档示例包含 `PendingEvent`、`InboundQueue`、各 connection 的 `OutboundQueue`、`WaitQueue`、`status`、`monitor`、`responsive` 等字段。现场排查时，至少记录三项：

- `FocusedWindow` / `FocusedApplications`：确认事件应该发给谁，是否处在 no focused window 等待。
- 目标 connection 的 `OutboundQueue` / `WaitQueue` 长度和 age：确认事件卡在写入前，还是写入后等 ACK。
- `Input Dispatcher State at time of last ANR`：确认 ANR reason 与当时的队列快照。

Perfetto 侧看 ATRACE counter。AOSP android-17.0.0_r1 里 `traceInboundQueueLengthLocked()` 写 `iq`，`traceOutboundQueueLength()` 写 `oq:<channel>`，`traceWaitQueueLength()` 写 `wq:<channel>`。这些是 counter，不是 slice。`wq` 持续上升说明 ACK 回路被压住；`oq` 上升更接近 channel 写入受限或 waitQueue 未释放；`iq` 上升可能是 dispatcher 前端积压、焦点等待或策略等待。

判读时不要把 `wq` 当成 MotionEvent batching 的直接证据。batching 和重采样主要在 App 侧 `InputConsumer` / `ViewRootImpl` 时序里观察，InputDispatcher 的 `wq` 只说明已交付事件没有完成回执。详见 3.2 节。


## 与应用主线程卡顿、Binder 阻塞的归因边界

InputDispatcher 的 waitQueue 是症状，不是根因。一个输入事件停在 `waitQueue`，只能说明目标进程没有按时返回 `Finished`。常见根因有三类：

1. App 主线程正在执行长任务，没有进入 `NativeInputEventReceiver` 的消费回路。
2. App 主线程被 Binder、锁、I/O、GC 或同步等待卡住，导致已收到的事件无法完成处理。
3. system_server 或目标进程调度异常，InputDispatcher 写入、App 读取、回执返回中的某段被 CPU 饥饿或内核等待拖慢。

建议按以下顺序定位：先用 `dumpsys input` 或 Perfetto counter 确认 `wq/oq/iq` 的卡点；再看同一时间窗口目标 App 主线程的 call stack 和 sched 状态；如果主线程在 Binder 等待，沿 Binder transaction 查对端线程；如果主线程看起来空闲但 `wq` 不退，检查 App 进程是否被调度、channel 是否 broken、窗口是否被移除、策略层是否延长了 timeout。

这段分析能避免两个常见误判：一是把所有 Input ANR 都归到 App 主线程，二是把所有主线程卡顿都写成 InputDispatcher 的问题。InputDispatcher 负责检测和隔离无响应连接，根因通常还要在 App、system_server、Binder 对端或内核调度里落点。

## 扩展场景

以下两个场景是 InputDispatcher 反压在实际问题中最常遇到的延伸话题——游戏高频触控和厂商定制行为。它们不在 AOSP 主线机制内，但排查时经常被问到。

### 游戏/高频触控场景下的反压放大

高频触控会放大队列现象。240Hz / 480Hz 报点下，单位时间进入系统的 MOVE 更多；如果 App 主线程一段时间不读 channel，`waitQueue` 的增长更快，`WOULD_BLOCK` 更容易出现。反过来，只要 App 侧能按帧批量消费，InputDispatcher 侧通常不会成为瓶颈——延迟更可能出现在 `InputConsumer` batching、`Choreographer`、渲染线程或 GPU 队列。

游戏场景还有一个分析边界：公开 Android API 没有提供“把某个 App 的 InputDispatcher 优先级提高”这样的能力。`View.requestUnbufferedDispatch()` 影响的是 App 侧 MotionEvent batching 行为，不等于提升触控 IC 报点率，也不等于绕过 InputDispatcher 的 `waitQueue` / ANR 机制。厂商 ROM 可能有游戏模式或触控调度定制，但没有公开源码或实机 trace 时，只能标为 OEM 差异，不能写成 AOSP 通用行为。


### 厂商输入调度策略与可验证边界

厂商定制最容易混进不可验证结论。本节能确认的 AOSP 边界是：InputDispatcher 使用 `responsive` 隔离无响应连接，用 `mAnrTracker` 管理超时，用 `iq/oq/wq` counter 暴露队列长度，用 `dumpsys input` 暴露连接状态。超出这些边界的说法，需要实机证据支撑。

可接受的证据包括：同一机型开关游戏模式前后的 Perfetto trace、`dumpsys input` 快照、线程优先级/调度策略记录、vendor kernel 或 framework patch。只有产品宣传、论坛描述或单次主观手感，不足以写成章节结论。

## 小结

InputDispatcher 反压由 channel 可写性、`outboundQueue`、`waitQueue`、`mAnrTracker`、`responsive` 标记和跨应用队列裁剪共同构成。排查时先确认一个边界：`waitQueue` 表示“已交付、未回执”，它是 Input ANR 的计时基础，也是继续追 App 主线程、Binder、CPU 调度和窗口状态的入口。

## References

- AOSP: `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`（android-17.0.0_r1，主线）
- AOSP: `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`（android-16.0.0_r1，历史差异参照）
- AOSP docs: `frameworks/native/services/inputflinger/docs/anr.md`
- Android Developers: [ANRs](https://developer.android.com/topic/performance/vitals/anr)
- Android Developers: [dumpsys](https://developer.android.com/tools/dumpsys)
- [DeepResearch: 2026-05-10-inputdispatcher-backpressure]
