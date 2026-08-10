---


title: "触摸响应的性能分析"
chapter: "3.2"
section: "3.2"
status: finalized
drafted_date: "2026-03-30"
drafted_by: "openclaw-task2"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
polish_count: 2
polish_date: "2026-05-08"
polish_by: "task2b-rework"
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Systrace-Input.md"
  - type: blog
    path: "Personal-Knowlodge/source/android-systrace-Responsiveness-in-action-1.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_从input响应性能差的issue演示perfetto_trace用法.md"
  - type: official
    path: "source.android.com/docs/core/interaction/input"
  - type: official
    path: "developer.android.com/reference/android/view/MotionEvent"
  - type: official
    path: "developer.android.com/reference/android/view/MotionPredictor"
  - type: official
    path: "developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features"
  - type: official
    path: "developer.android.com/jetpack/androidx/releases/input"
tags: [touch, input, latency, InputReader, InputDispatcher, sampling-rate, batching, Choreographer, responsiveness]
related_chapters: ["3.1", "2.3", "2.4", "2.5", "8.1"]
task2b_rework_date: "2026-05-08"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-12"
last_task9_at: "2026-07-12T12:28:57+08:00"
task9_result: auto-fixed

reviewed_date: "2026-07-12"
reviewed_by: openclaw-task6
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-07-12"
task2b_lite_note: "版本锚点从 android-16.0.0_r1 更新到 android-17.0.0_r1（6 处正文 + frontmatter）；依据同目录 §3.9、§3.13 已验证 android-17.0.0_r1 路径一致性"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-07-12T12:15:00+08:00"
last_task6_audit: "2026-07-12"
last_task6_review_log: "logs/review/2026-05-08-15-review.md"
review_notes: "2026-05-08 10:28 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 0；InputReader.loopOnce 源码片段与 InputDispatcher 队列观测口径需修正。 | 2026-05-08 Task6 14:05：复审 Task2B 修复后的文稿，完成 frontmatter 去重、代码围栏语言标注与 L1/L2 小修；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-05-08 Task6 15:05：自动晋升 finalized。条件满足：task6_result=pass-light-edit、task9_result=pass-tech-review、queue 无 pending 条目；本轮未做重复正文 review。"
last_task9_review_log: "logs/deep-review/2026-07-12-12-deep-review.md"
task9_review_notes: "2026-05-08 Task9 14:32：needs-rework。P0 1 / P1 0 / P2 1；正文写 WaitQueue 条目要等 `doDispatchCycleFinishedLockedInterruptible` 收到 ACK 后移走；android-16.0.0_r1 的实际路径是 `handleReceiveCallback()` 读取 Finished signal，`finishDispatchCycleLocked()` post command，随后 `doDispatchCycleFinishedCommand()` 从 `connection->waitQueue` erase 对应 `seq`。Task2B 随后修正 ACK 回路方法名，queue 项已 completed，task9_result 更新为 pass-tech-review。 | 2026-06-06 Task9 15:45 闲时抽检：auto-fixed。P0 版本/源码锚点 1 组；16KB page size 起点从 Android 16+ 修正为 Android 15+ AOSP 支持，并把 Resampler.cpp 锚点从 AOSP mainline 改为 android-16.0.0_r1；本轮未使用 Android 18/API 38+ 或 main/master 资料作为正文结论。 | 2026-07-12 Task9 12:28：auto-fixed。P0 1 / P1 0 / P2 0 / P3 1；移除 16KB 页面段落中的 “socketpair mmap” 错误机制（android-17.0.0_r1 `InputChannel::sendMessage()` / `receiveMessage()` 为 Unix socket `send` / `recv`），并把 InputReader Perfetto 观察点从固定 Slice 修正为 inputevent tracing / 线程活动观察。本轮未使用 Android 18/API 38+ 或 main/master 资料作为正文结论。"
finalized_date: "2026-07-12"
finalized_by: openclaw-task6-auto-promote
task6_review_notes: "2026-07-12 Task6 revisiting 复审：pass-light-edit。L1 禁用词/高频词/否定-纠正/元叙述 grep 全部零命中；L2 结构/节奏/读者视角通过；task9 idle audit auto-fixed（P2 版本锚点）等效通过；无新增 L3/L4 回炉项。自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
last_task9_autofix_at: "2026-07-12"
last_task9_audit: "2026-06-06"
pipeline_stage: ready-to-publish
---

# 触摸响应的性能分析

## 为什么需要关注触摸响应

在滑动列表的 Perfetto trace，可以沿时间轴看到 InputReader、InputDispatcher、应用主线程、RenderThread、SurfaceFlinger 和显示帧。触摸样本进入系统后，应用还要消费事件、更新界面状态、提交 buffer，再由 SurfaceFlinger 合成并送显；其中任何一段延后，都会增加可见响应时间。

这段从物理动作到光子变化的时间通常称为 touch-to-display latency。刷新周期只是其中一个时间尺度：60Hz 每周期约 16.67ms，120Hz 每周期约 8.33ms。事件落在 VSync 周期的哪个相位、应用是否赶上当前帧、buffer 是否按期合成，都会改变结果。因此，一个刷新周期不能直接代表端到端延迟，也不应脱离设备、操作和统计分位数给出通用的“典型毫秒数”。

触摸响应主要分为两类：

- **离散响应**：按下按钮后，下一帧何时显示 pressed state 或业务结果。
- **连续跟手**：手指或笔持续移动时，屏幕轨迹与当前位置相差多少时间和空间。

连续跟手会反复暴露位置差，通常比一次点击更容易显出延迟。工程测试应在目标设备上分别统计点击响应和连续手势，至少报告刷新率、触控模式、冷/热状态、P50/P90/P99 以及丢帧情况。缺少这些条件的单一数字不适合作为产品 SLA。

## 触摸响应延迟的组成

从手指触碰屏幕到画面更新，触摸事件要经过多个阶段。按时间顺序拆分，才能确定耗时所在的边界。

### 1. 硬件采样（触摸屏 → 驱动）

触控控制器扫描面板并把报告送到 SoC。扫描、滤波、去抖、总线上报和驱动中断都属于设备实现，AOSP 不规定它们必须采用哪种总线或固定采样率。若设备以近似固定频率上报，采样周期可用 `1 / samplingRate` 粗略估算：

- **120Hz**：约 8.33ms 一个采样周期
- **240Hz**：约 4.17ms 一个采样周期
- **480Hz**：约 2.08ms 一个采样周期

周期只给出相位等待的上界模型，不能覆盖控制器内部滤波和上报策略。更高的采样率通常能减小首次检测等待，并为轨迹重建提供更密的 MOVE 样本；即使这些样本被批量放进同一个 `MotionEvent`，应用仍可读取历史样本，系统也可用于重采样。高于显示帧率的采样并非自动浪费，但能否改善画面取决于应用是否消费历史点、是否走 unbuffered path，以及渲染和显示是否及时。

### 2. 内核处理（驱动 → EventHub）

触摸驱动向 Linux input core 上报事件，evdev 再通过 `/dev/input/eventX` 暴露 `input_event` 流。Android 的 EventHub 用 inotify 发现设备节点增删，用 epoll 等待已打开 fd 的数据；`getEvents()` 被唤醒后批量读取事件。

Android 17 的 `EventHub::getEvents()` 为每个 `RawEvent` 保留两个重要时间：

- `when`：经 `processEventTimestamp()` 处理后的内核事件时间。
- `readTime`：EventHub 从设备节点读取该事件时记录的 `SYSTEM_TIME_MONOTONIC` 时间。

`readTime - when` 可用于判断事件从驱动/evdev 到 EventHub 读取之间是否停留过久。这个差值应从目标设备的 Trace 或日志取得；源码没有承诺它必然小于 1ms。

### 3. InputReader 读取和加工

InputReader 是运行在 `system_server` 进程中的 Native 线程。它从 EventHub 读取原始 `input_event`，完成设备映射、坐标转换、多点触控组装、工具类型识别等处理，生成 `NotifyArgs`。这些参数随后进入 Android 17 的 input listener chain，经过误触处理、pointer choreography、可选分类/过滤等阶段，再送到 InputDispatcher。

核心循环在 `InputReader.loopOnce()` 中：

```cpp
// frameworks/native/services/inputflinger/reader/InputReader.cpp (android-17.0.0_r1)
// 结构化伪代码：保留锁边界，省略配置刷新和设备变更
void InputReader::loopOnce() {
    std::vector<RawEvent> events = mEventHub->getEvents(timeoutMillis);
    std::list<NotifyArgs> notifyArgs;
    {
        std::scoped_lock lock(mLock);
        if (!events.empty()) {
            mPendingArgs += processEventsLocked(events.data(), events.size());
        }
        std::swap(notifyArgs, mPendingArgs);
    }
    for (const NotifyArgs& args : notifyArgs) {
        mNextListener.notify(args);
    }
}
```

这段代码展示三个边界：`getEvents()` 返回 `std::vector<RawEvent>`；映射与状态更新在 InputReader 锁内完成；对下一监听器的通知发生在锁外。`loopOnce()` 一次可能读到一批 evdev 事件，但“批量读取 RawEvent”与应用侧“把多个 MOVE 坐标合成一个 MotionEvent”分属不同层级，排查时要分开处理。

### 4. InputDispatcher 派发

InputDispatcher 也是 `system_server` 中的 Native 线程。监听器链把 `NotifyArgs` 交给 dispatcher 后，事件入队并唤醒它的 Looper。它根据焦点、窗口信息、touch state、手势监视和安全策略选择一个或多个目标窗口；Activity 只是窗口背后的上层组件，不能代替窗口路由规则。

事件在 InputDispatcher 中经过三个关键队列：

1. **InboundQueue（"iq"）**：InputReader 交付的事件先进入这里。InputDispatcher 从队列头取出事件开始处理。
2. **OutboundQueue（"oq"）**：每个目标 `Connection` 都有一个 OutboundQueue。事件被包装成 `DispatchEntry` 后放入此队列，等待发布到 InputChannel。
3. **WaitQueue（"wq"）**：发布成功后，条目从 OutboundQueue 移到 WaitQueue，等待应用侧返回 `FINISHED`。Android 17 的回收路径由 `handleReceiveCallback()` 接收响应，随后经 `finishDispatchCycleLocked()` 和 `doDispatchCycleFinishedCommand()` 按 `seq` 删除 WaitQueue 条目。

`FINISHED` 表示应用结束这枚输入事件的分发责任，不表示对应画面已经 present。若事件触发了异步 InputStage，或应用主线程迟迟没有走到 `finishInputEvent()`，WaitQueue 会保持非空；渲染可以在 ACK 之后继续执行。因此，输入 ACK 延迟和 touch-to-display 延迟需要分开测量。

在 Perfetto 中，这三个队列以计数器轨道出现（由 `ATRACE_INT` 写入 `iq` / `oq:<channel>` / `wq:<channel>`，并非 slice）。`iq` 描述尚未处理的入站事件，`oq` 描述尚未发布的连接事件，`wq` 描述已发布但尚未 finish 的事件。

这些判断都要结合持续时间：队列在事件发布与 ACK 之间短暂变为 1 是正常状态，连续增长或长时间不归零才提示背压。`wq` 增长也不能单凭计数器断言“主线程阻塞”，还要查看应用主线程、异步 InputStage 和 socket 回写时序。

对手写笔、掌压误触和边缘触控问题，还要检查 `MotionEvent` 的 classification 与 cancel 路径。分类可能影响 touch slop、长按判断或误触撤回；遇到首笔不生效时，应确认应用是否收到 `ACTION_CANCEL` / `FLAG_CANCELED`，不能只看 WaitQueue。

### 5. 跨进程传输（socketpair）

InputDispatcher 通过 `InputChannel` 将事件发送给目标进程。Android 17 的通道由 `socketpair(AF_UNIX, SOCK_SEQPACKET, ...)` 建立并设为 non-blocking；`InputChannel::sendMessage()` / `receiveMessage()` 负责消息收发。应用的 `NativeInputEventReceiver` 把 fd 注册到主线程 Looper，fd 可读后消费消息。

这里需要区分“socket 写入耗时”与“接收线程何时获得 CPU”。即使消息已经写入内核缓冲区，应用主线程处于 Running、Runnable、Blocked 或 Sleep 的不同状态，也会让消费时间产生很大差异。Binder 压力只有在引发 CPU 竞争或应用同步等待时才构成相关证据，不能把 Binder 和 InputChannel 当成同一条数据通道。

### 6. App 端处理（View 树遍历）

`NativeInputEventReceiver` 把事件转成 Java `InputEvent` 后，`WindowInputEventReceiver` 将其加入 `ViewRootImpl` 的 pending queue。Android 17 用 `aq:pending:<window>` counter 记录队列长度，并以 `deliverInputEvent` 同步/异步 Trace 标记整段处理。触摸这类 pointer event 通常从 post-IME 链进入 `EarlyPostImeInputStage`、`NativePostImeInputStage` 和 `ViewPostImeInputStage`，再由 View 树处理。

View 的触摸分发沿命中的目标分支和已建立的 `TouchTarget` 关系进行，并非每个 MOVE 都遍历整棵 View 树。事件可能只更新滚动偏移或状态，也可能触发 `invalidate()`、`requestLayout()` 或动画。前者通常只要求重绘，后者可能让下一次 traversal 执行 measure/layout/draw。

### 7. 渲染上屏

触摸引起的状态改变要进入某一帧，随后经过应用 traversal、RenderThread/GPU、BufferQueue、SurfaceFlinger 和显示输出。任何一段错过当前帧 deadline，都可能让可见反馈顺延一个或多个刷新周期。不能预设渲染一定是最长阶段：主线程调度、输入处理、GPU 和合成都要用同一份 Trace 逐段排除。

### 延迟全景图

用源码中能够对应的时间点建立测量表，比套用一组“典型耗时”更可靠：

| 边界 | Android 17 证据 | 能回答的问题 |
|------|-----------------|--------------|
| 设备事件 → EventHub 读取 | `RawEvent.when`、`RawEvent.readTime` | 驱动/evdev 到读取是否滞留 |
| InputDispatcher 入队/发布 | `android.input.inputevent`、`iq`/`oq:*` | 系统侧是否积压、目标窗口是谁 |
| 发布 → 应用消费/完成 | delivery、consume、finish 时序，`wq:*` | 调度与应用输入处理是否拖延 |
| 应用输入 → 目标帧 | `deliverInputEvent`、`aq:pending:*`、Choreographer、input event ID | 哪枚事件驱动了哪一帧 |
| 目标帧 → present | FrameTimeline、RenderThread、GPU、SurfaceFlinger | 画面为何晚一个或多个刷新周期 |

Android 17 的 `InputEventAssigner` 有一项限制：连续手势中，一帧只归因到一枚输入 event ID。首帧优先关联未处理的 DOWN，后续帧通常关联该帧之前的最新事件；中间的 MOVE 可能没有独立的 frame attribution。因此，做端到端关联时要保留 event ID 与 history，不能假设每个采样点都有一帧与之对应。

## 触摸采样率与跟手性

### 采样率 ≠ 刷新率

这两个概念容易混淆，但表示相互独立的频率：

- **触摸采样率**：触摸屏硬件每秒检测手指位置的次数。120Hz 表示每秒检测 120 次。
- **屏幕刷新率**：屏幕每秒更新画面的次数。120Hz 表示每秒刷新 120 次。

采样率影响坐标的时间密度，刷新率限定显示更新机会。两者独立运行且相位未必对齐：240Hz 触控与 120Hz 显示组合，理想情况下每个显示周期约有两个触控样本；120Hz 触控与 60Hz 显示约有两个。前者拥有更短的采样周期和显示周期，但事件能否进入最近一帧仍取决于到达时刻与整条处理路径，不能直接用频率比推出端到端延迟。

### 采样率和渲染帧率的匹配

高采样率的价值，要放到“应用如何消费样本、每秒能显示多少帧”两个前提下看。

- **60fps + 120Hz 触控**：按理想固定频率估算，一个显示周期约有两个样本。它们可以合并到一枚 `MotionEvent` 中，较早的点通过 history 暴露。
- **60fps + 240Hz 触控**：一个显示周期约有四个样本。列表仍只能每帧呈现一次位置，但笔迹拟合、速度估计和 prediction 可以使用更密的数据。
- **120fps + 240Hz 触控**：一个显示周期约有两个样本；更短的显示周期也缩短了错过一帧后的等待。
- **unbuffered dispatch / front-buffer**：前者缩短 MOVE 进入应用的等待，后者缩短局部笔迹的渲染路径。两者解决的是不同阶段，且都需要设备与应用实现配合。

上面的样本数只是频率比值，不代表每个周期都严格收到相同数量。触控控制器可能动态调整报告率，显示也可能运行在 VRR 模式。验证设备规格时，应根据驱动事件时间或结构化 input trace 统计相邻样本间隔。

## 输入事件 Batching 与 Choreographer 的配合

### 为什么需要 Batching

当触摸采样率高于渲染帧率时，一个 VSync 周期内可能到达多个 `ACTION_MOVE` 样本。若每个样本都立即唤醒应用并执行完整的 View 分发，会增加 Looper 和业务回调压力；即使多次失效请求合并到一帧，前面的 CPU 工作也可能重复。batching 用较少的应用交付次数保存这些样本。

Android 的输入批处理会合并交付，但不直接删除中间坐标。Android 17 的应用侧 `InputConsumer` 对可兼容的 `ACTION_MOVE` / `ACTION_HOVER_MOVE` 消息建立 batch；消费时，第一条样本初始化 `MotionEvent`，后续样本通过 `addSample()` 进入 history。当前坐标通过 `getX()` / `getY()` 读取，较早样本通过 `getHistorySize()` 和 `getHistorical*()` 读取。

下面的代码按时间顺序处理一枚 batched `MotionEvent`，适合画笔和轨迹记录；列表滚动通常只需使用当前坐标。

```java
final int historySize = event.getHistorySize();
for (int h = 0; h < historySize; h++) {
    float historicalX = event.getHistoricalX(0, h);
    float historicalY = event.getHistoricalY(0, h);
    // 处理 batched 历史样本
}
float latestX = event.getX();
float latestY = event.getY();
```

history 属于同一枚事件，因此 Perfetto 中通常只看到一次 Java `deliverInputEvent`，Native `dispatchInputEvent MotionEvent ... historySize=N` 会直接给出 history 数量。不要把一枚事件里的 N 个历史点误判为 N 次 View 分发。

### Batching 之外还有重采样

Batching 决定样本如何合并交付；重采样负责把轨迹时间与显示帧对齐。Android 17 的常规 ViewRoot 路径在应用进程 JNI 中持有 `InputConsumer`。当它以有效的 `frameTimeNanos` 消费 batch 且 `ro.input.resampling` 未被厂商关闭时，会以 `frameTimeNanos - 5ms` 为目标时间，在真实样本之间插值，或根据最近两个样本做受限外推。

`5ms` 是重采样目标相对 frame time 的相位偏移，用于为插值预留未来样本并限制错误外推；它不能单独计入 touch-to-display 耗时，写成“系统额外等待 5ms”。effective frame time、样本间隔、工具类型或 vendor flag 不满足条件时，重采样会跳过。

API 35+ 可用 `MotionEvent.PointerCoords.isResampled()` 判断指定坐标是否由重采样生成。这个方法属于 `PointerCoords`，调用方式如下：

```java
MotionEvent.PointerCoords coords = new MotionEvent.PointerCoords();
event.getPointerCoords(pointerIndex, coords);
boolean currentIsResampled = coords.isResampled();

for (int h = 0; h < event.getHistorySize(); h++) {
    event.getHistoricalPointerCoords(pointerIndex, h, coords);
    boolean historicalIsResampled = coords.isResampled();
}
```

重采样坐标会作为 batch 中的新样本加入，事件里至少保留一枚来自设备的真实样本。unbuffered dispatch 使用 `consumeBatchedInputEvents(-1)` 立即取走所有待处理样本，旧 `InputConsumer::consumeBatch()` 在 `frameTime < 0` 时直接返回，不执行重采样。

### Choreographer 中 Input 的优先级

在 android-17.0.0_r1 的 `Choreographer#doFrame()` 里，回调顺序是：

1. `CALLBACK_INPUT`
2. `CALLBACK_ANIMATION`
3. `CALLBACK_INSETS_ANIMATION`
4. `CALLBACK_TRAVERSAL`
5. `CALLBACK_COMMIT`

`CALLBACK_COMMIT` 运行在 traversal 之后，负责这一帧的 post-draw 工作和时间基准修正，不负责 measure/layout/draw。分析输入延迟时，主要检查前四段：输入处理排在最前面，后续动画和遍历都基于最新输入状态。

连续 `MOVE` 事件默认走 buffered path。`ViewRootImpl.WindowInputEventReceiver#onBatchedInputEventPending()` 会判断 `mUnbufferedInputDispatch` 和 `mUnbufferedInputSource`：当前序列请求了 unbuffered dispatch，直接调用 `consumeBatchedInputEvents(-1)`；否则调用 `scheduleConsumeBatchedInput()`，让事件贴近下一帧的输入阶段消费。

这条分叉决定 MOVE 是立即送达，还是贴近下一帧的 input callback 消费。普通滚动使用 buffered path，可以减少 Looper 唤醒和 View 分发次数；笔迹、绘图、签名可在确认命中目标后调用 `View.requestUnbufferedDispatch(event)`。它只影响当前手势序列，应用仍要逐个处理事件，CPU 调度和回调压力也会增加。

### Batching 与 WaitQueue 在 Perfetto 中的表现

批处理与 App 处理能力是两组不同的证据，在 Perfetto 中对应不同的 Track 和 Slice。

**InputDispatcher 侧 — 派发/ACK 背压**：

1. 找到 `system_server` 进程的 InputDispatcher 线程
2. 观察 `iq`、`oq:<channel>`、`wq:<channel>` 的 ATRACE_INT 计数器（队列长度，不是 Slice）
3. WaitQueue 反映已派发但等待 App finish/ACK 的事件数量。wq 堆积说明 App 端处理慢或 ACK 回写延迟，不等同于 batching 本身
4. 如果 WaitQueue 持续堆积且不下降，转到目标应用检查主线程、异步 InputStage 与回写；计数器本身还不能区分三者

**App 侧 — Batching 消费**：

1. 切换到 App 进程的主线程 Track
2. 查找 Native `dispatchInputEvent MotionEvent ... historySize=N`，确认应用收到的 `MotionEvent` 是否包含 history
3. 查找 `deliverInputEvent src=... eventTimeNano=... id=...` 与异步 `deliverInputEvent`，确认 Java 输入处理起止
4. 观察 `aq:pending:<window>`，判断事件是否在 `ViewRootImpl` pending queue 中等待
5. 将事件 ID 与 FrameTimeline/应用帧关联，确认输入更新落入哪一帧以及何时 present

两条证据链要分别解读：InputDispatcher 的 `wq:*` 用于判断派发/ACK 背压；`historySize` 和 `MotionEvent` history 才是 batching 的直接证据。Choreographer 的 input callback 通常显示为 `input` 阶段，具体 UI 名称会随 Perfetto 版本和采集配置变化。

## 触摸场景的性能分析方法

### 从 Input 事件路径定位瓶颈

先确定问题属于“事件晚到”“应用晚处理”还是“画面晚出现”，再沿事件 ID 和帧 ID 追踪。可按下面的顺序排查：

1. **确认设备事件时间**：比较 evdev/event time 与 EventHub read time，排除触控固件、驱动和读取延迟。
2. **检查 InputDispatcher**：观察结构化 input event、`iq`、目标连接的 `oq:*` / `wq:*`，确认窗口选择、发布和 ACK。
3. **检查应用主线程**：从 socket 可读/Native dispatch 到 `deliverInputEvent`，区分 Running、Runnable、Sleep 和锁等待。
4. **检查 batching**：读取 `historySize`，确认是否在 `CALLBACK_INPUT` 消费，以及业务是否遗漏历史样本。
5. **检查目标帧**：用 input event ID、应用 FrameTimeline 和 SurfaceFlinger FrameTimeline 关联到 present。
6. **最终归因资源瓶颈**：根据 scheduler、CPU frequency、GPU 和内存轨道解释等待，避免从一个函数名直接猜根因。

### 采集结构化 Input Trace

Android 17 的 InputFlinger 注册了 `android.input.inputevent` Perfetto data source。它只允许在 debuggable（userdebug/eng）构建上采集，可记录 dispatcher input event 和 window dispatch；配置支持完整或脱敏级别，并可按安全窗口、IME 状态和目标包规则过滤。完整记录可能包含敏感坐标，只应在本地测试设备使用，现场采集必须使用严格规则。

下面的最小配置用于本地测试机短时抓取完整 input event；同时启用 `linux.ftrace` 才能看到调度、频率和 ATRACE 轨迹。

```textproto
buffers: {
  size_kb: 32768
  fill_policy: RING_BUFFER
}
data_sources: {
  config {
    name: "android.input.inputevent"
    android_input_event_config {
      mode: TRACE_MODE_TRACE_ALL
    }
  }
}
```

`TRACE_MODE_TRACE_ALL` 不适合现场或用户数据采集。正式配置应改用 rules，并验证输出是否已脱敏。

### 案例：Input Boost 未生效导致响应慢

下面的设备案例说明如何从函数 slice 转向调度证据。trace 中的 `processInputEventForCompatibility` slice 持续约 4ms，但对应的 AOSP 逻辑不足以解释这段墙钟时间。展开线程状态后可见：

- 线程在 slice 内并非始终 Running，中间存在被抢占和 Runnable 等待。
- 第二次触摸没有复现该设备第一次触摸时的频率变化，主线程以较低频率执行。
- 同时唤醒的硬件服务 timer 线程占用了 CPU，应用主线程延后获得运行机会。

这里的结论只适用于当时的设备实现：OEM input/touch boost 未按预期触发，加上线程竞争，放大了墙钟耗时。AOSP 不保证所有设备都有同名 CPU boost，也不规定输入后必须在几毫秒内升到某个频点。排查时应把 slice 拆成 Running 时间与非 Running 时间，再用频率、调度和厂商策略解释差值。

### Perfetto 中的关键 track 和 slice

分析触摸响应时，可检查以下 track、counter 和 slice：

**system_server 进程：**
- **InputReader 线程**：结合 `android.input.inputevent` 的 evdev/input event 时间和线程调度，统计相邻采样间隔；线程 wakeup 间隔不等于硬件固定采样率。
- **InputDispatcher 线程**：观察 `iq`、`oq:<channel>`、`wq:<channel>` 的长度与持续时间。
  - `iq` 连续增长：dispatcher 消费速度落后于输入或其他入站事件。
  - `oq` 长时间不降：消息尚未成功发布，需要查看连接状态和 socket 可写性。
  - `wq` 长时间不降：已发布事件尚未收到 finish，需要转到目标应用继续分析。

**App 进程：**
- **主线程 Track**：
  - Native `dispatchInputEvent MotionEvent ... historySize=N`
  - `aq:pending:<window>` 与 `deliverInputEvent`
  - Choreographer 的 `input`、`animation`、`insets_animation`、`traversal`、`commit`
- **FrameTimeline**：确认应用帧是否 miss deadline，以及 SurfaceFlinger 帧何时 present。
- **CPU/Scheduler Track**：确认主线程和 RenderThread 的 Running/Runnable/Blocked 区间，再看 CPU frequency。

### 用 dumpsys input 辅助排查

`adb shell dumpsys input` 命令可以获取 Input 系统的实时状态，包括：

- EventHub/InputReader 的设备、mapper 和配置状态。
- focused application/window、当前 touch state 与 pointer capture。
- `RecentQueue`：最多 10 枚最近 dispatch 或 drop 的事件及其 `age`。
- `PendingEvent`、`InboundQueue`。
- 每个连接的 status、responsive、OutboundQueue 和 WaitQueue；非空条目会附带 age 等描述。

`age` 是执行 dumpsys 时的瞬时年龄，不存在通用的“正常必须小于 16ms”阈值。WaitQueue 的 ANR deadline 在事件发布时按连接设置：默认基值为 5000ms，再乘 `HwTimeoutMultiplier()`；窗口或应用可以覆盖 dispatching timeout。判断风险时，应查看该连接的 timeout、responsive 状态和连续多次采样趋势。

## 常见触摸卡顿原因

### 1. 主线程阻塞

主线程阻塞是常见的触摸卡顿原因。当 App 主线程执行磁盘 I/O、数据库查询、复杂计算或等待 Binder 调用返回时，排队等待处理的 Input 事件也会被延后。

在 Perfetto 中的表现：
- 主线程长时间处于 **Running** 状态但没有处理输入
- 主线程长时间 **Runnable** 却得不到 CPU，或阻塞在 Binder、futex、I/O
- WaitQueue（wq）持续堆积
- 最早的 WaitQueue 条目越过该连接的 dispatching timeout 后，InputDispatcher 判定连接 unresponsive

常见场景：
- `onCreate()`/`onResume()` 中做了太多初始化工作
- 主线程访问数据库或 SharedPreferences
- 主线程同步等待网络、Binder 或文件 I/O
- 主线程持锁等待（synchronized 块、ReentrantLock）

### 2. 过深的 View 层级

触摸分发从根 View 进入 `dispatchPointerEvent()`，随后沿命中的子树和当前 `TouchTarget` 路径执行 `dispatchTouchEvent()`。每一层 `ViewGroup` 都可能运行 interception、坐标变换和 listener，但 MOVE 不会无条件扫描整棵树。层级深度会增加固定调用成本，复杂的自定义命中测试、listener 和手势识别通常更值得优先检查。

batching 后的一枚 `MotionEvent` 只做一次 View 分发；只有应用主动遍历 history，或使用 unbuffered dispatch 收到更多事件时，才会按更多样本执行自身的轨迹逻辑。不要用“采样点数量 × 整棵 View 树深度”估算开销。

优化思路：
- 用 Trace 或方法级采样确认 `dispatchTouchEvent()`、gesture detector 和业务 listener 的耗时。
- 删除没有布局或语义价值的 wrapper；是否改用 ConstraintLayout 要以 measure/layout 数据为依据。
- 避免在 MOVE 回调中分配大量临时对象、同步 I/O、复杂路径运算或重复 `requestLayout()`。
- 自定义容器只在手势归属明确后拦截，并正确发送/处理 `ACTION_CANCEL`。

### 3. 事件分发冲突

嵌套滚动、ViewPager 与横向列表、自定义手势识别器可能对方向和 touch slop 作出不同判断。View 分发并非跨进程的多轮协商：父 View 在当前 `dispatchTouchEvent()` 中调用 `onInterceptTouchEvent()`；若中途接管手势，原 child target 会收到 `ACTION_CANCEL`。

这类问题常表现为首段位移未被业务采用、父子控件反复切换状态，或 CANCEL 后仍继续绘制，看起来像“慢半拍”。排查时应记录 action、pointer ID、intercept 决策和 CANCEL，不要仅凭耗时归类为系统触摸延迟。对 RecyclerView/NestedScrolling 体系，优先使用已有 nested scrolling 协议，减少重复的手势归属逻辑。

### 4. CPU 频率和调度问题

触摸事件到来时，如果 CPU 频率过低或 App 主线程被调度出去，即使代码本身没有问题，输入处理耗时也会增加。

不少设备实现了 Input Boost、Touch Boost 或类似策略，在输入到来后短时间调整 CPU/GPU 性能状态或线程放置。这些名称、触发条件和持续时间属于 SoC/厂商实现，不属于 Android 17 framework 的统一契约。

验证时应比较同一设备上的正常样本与异常样本：输入之后是否出现预期的频率/调度变化，主线程的 Runnable 延迟是否同步变长，thermal 或 power policy 是否正在限频。没有升频只是一条现象；设备也可能用 uclamp、task placement 或其他机制达到相同目标。

### 5. GPU 渲染瓶颈

如果 Input 处理和 View 树分发都很快，但渲染管线跟不上，例如 GPU 执行 DisplayList 过久、SurfaceFlinger 合成延迟、buffer 状态异常，画面更新仍会延迟。用户会感到“手指动了但画面跟不上”。

这种情况在 Perfetto 中表现为：
- 应用 FrameTimeline 标记 missed deadline，且主线程 input/traversal 已按时结束。
- RenderThread `DrawFrame`、GPU queue/completion 或 fence wait 延伸到 deadline 之后。
- `dequeueBuffer` 长时间等待可用 Buffer；具体原因还要结合 BufferQueue 和消费者状态。
- SurfaceFlinger FrameTimeline 显示合成帧 deadline miss，或目标 layer 的 buffer 没有赶上 latch。

`GPU Completion` 不表示用户看到画面的时间，显示侧边界应使用 present time。判断“慢了两帧”也要按当时的实际刷新周期计算，不能固定写成 32ms。

### 6. 系统低内存

内存压力会间接放大输入和渲染延迟，例如 Java GC pause、major fault、回收/压缩线程占用 CPU，以及文件页重新读取。是否由内存压力导致，要以同一时间窗口内的 GC、fault、reclaim、I/O 和调度证据为准。

在 Perfetto 中表现为：
- 主线程或 RenderThread 的 Runnable 延迟增加
- GC pause 与输入处理或 traversal 重叠
- `kswapd`/reclaim 活跃、major fault 或 I/O wait 与异常帧重叠

## Motion Prediction：面向笔迹/绘图的感知降延迟

Motion Prediction 涉及三层概念，各自独立：

- **framework API**：`android.view.MotionPredictor`，API 34 加入。
- **AndroidX 库**：`androidx.input:input-motionprediction`，为不同系统版本提供封装。
- **低延迟输入**：`requestUnbufferedDispatch()` 让真实样本更早到达应用。
- **低延迟绘制**：front-buffer 等方案缩短笔迹提交到显示的路径。

这几层可以组合，但不能互相替代。Prediction 降低的是“已知轨迹落后于手”的感知差距；它不会修复主线程阻塞、丢帧或 SurfaceFlinger 合成延迟。

### Android 17 framework 实现边界

`android-17.0.0_r1` 的 `MotionPredictor` 是 Java 到 Native 的薄封装。设备资源 `config_enableMotionPrediction` 决定 Java API 是否启用，AOSP 基础值为 `false`，OEM 需要在确认模型适配设备后覆盖；Native 层还有可在运行时关闭的 `enable_motion_prediction` sysprop 检查。`isPredictionAvailable(deviceId, source)` 同时受这些开关约束，当前 Native 实现只接受 stylus source。API 存在不代表所有 Android 17 设备默认可用。

Native `TfLiteMotionPredictorModel` 优先加载 `/vendor/etc/motion_predictor_model.tflite`，否则使用 `/system/etc/motion_predictor_model.tflite`；同目录 XML 提供 prediction interval、noise floor 和 jerk threshold 等配置。输入张量包括相对轨迹的 `r`、`phi`、pressure、tilt、orientation，输出为 `r`、`phi`、pressure。Android 17 包含受 feature flag 控制的 jerk pruning；无论该 flag 是否启用，模型的 noise floor、输出长度和请求时间都可能让 `predict()` 返回 `null`，或让结果停在早于请求时间的位置。

源码没有为预测事件定义 `FLAG_PREDICTED`。应用要把真实笔迹和临时预测笔迹分层管理：下一批真实事件到达后，删除或修正未确认的预测段，再继续绘制。

### 调用与绘制约束

下面的 Java 骨架展示 framework API 的最小调用顺序。目标时间必须使用 uptime 时基的纳秒值，而且同一个实例在一次手势中只记录一个设备的事件流。

```java
MotionPredictor predictor = new MotionPredictor(context);

void onStylusEvent(MotionEvent event, long targetTimeNanos) {
    if (!predictor.isPredictionAvailable(event.getDeviceId(), event.getSource())) {
        drawRealSamples(event);
        return;
    }

    predictor.record(event);
    drawRealSamples(event);

    MotionEvent predicted = predictor.predict(targetTimeNanos);
    if (predicted != null) {
        drawTemporaryPrediction(predicted); // 同时消费 predicted 的 historical samples
        predicted.recycle();
    }
}
```

实际代码还要在 `ACTION_UP` / `ACTION_CANCEL` 清理临时预测层，并处理多 pointer、重采样点和模型不可用。普通按钮点击没有连续轨迹可预测；列表滑动也应先修复调度、主线程和帧 deadline 问题，再评估 prediction 是否适合产品交互。

## 厂商触控优化方案

这里只讨论可从系统行为验证的共性做法，不把某个厂商的营销规格写成通用结论。

### 高刷新率屏幕

更高的刷新率会缩短刷新周期：60Hz 约 16.67ms，120Hz 约 8.33ms，144Hz 约 6.94ms。应用和系统能按期生产帧时，它能缩短等待显示机会的时间。VRR 设备可能根据内容、触摸、功耗和 thermal 状态切换刷新率，因此分析必须读取 Trace 中该时段的实际 frame timeline，不能只采用设置页或规格表的最高值。

### 触控固件与控制器调校

很多设备会定制触控固件、滤波参数、采样率和上报节奏。规格表里常见 240Hz、480Hz、720Hz 甚至更高的触控采样率，但它只能说明“采样机会更多”，不能单独推出触摸到显示的时延。还要结合驱动处理、ViewRootImpl 的 batching 策略、应用是否消费历史样本，以及显示刷新周期。

### 调度与提频策略

厂商 ROM 常会在输入到来后短时间提高 CPU/GPU 频率，或提高 UI 相关线程的调度优先级。不同平台会给这类机制使用不同名称，但策略是否存在、持续多长、是否把线程放到大核，都必须以目标设备的 trace 和内核/ROM 实现为准，不能写成固定数值。排查时应直接查看 Perfetto 中的 CPU frequency、线程调度和 SurfaceFlinger/RenderThread 行为。

## 与其他章节的关系

触摸响应与输入分发、帧调度和渲染链路交叉关联：

- **3.1 Input 事件分发全流程**：输入事件从硬件到 App 的完整分发机制。
- **2.3 VSync 机制**：buffered MOVE 会贴近 Choreographer 的 input callback 消费，目标帧也由 VSync 驱动；unbuffered path 则不等待这一回调。理解 VSync 周期、deadline 和实际刷新率，才能解释事件赶上了当前帧还是顺延到下一帧。
- **2.4 Choreographer 与渲染流水线**：CALLBACK_INPUT 优先级、`doFrame()` 执行顺序与 Batching 实现见 2.4 节。
- **2.5 MainThread 与 RenderThread 协作**：View 输入分发和 traversal 位于 MainThread，部分硬件加速渲染工作交给 RenderThread/GPU。
- **8.1 响应速度原理**：输入延迟 → 处理延迟 → 输出延迟的通用模型与量化方法。

## 常见问题与误区

### 误区：触摸采样率越高越好

更高采样率提供更多、更近的真实坐标，但显示帧数仍受刷新率和渲染能力限制。普通滚动中，多出的 MOVE 样本常进入同一枚 `MotionEvent`；应用只读当前坐标时，可见收益会受限。手写笔、轨迹拟合、prediction 和高刷新率/高帧率场景更可能利用历史样本。

### 误区：触摸卡顿一定是 App 的问题

事件可以在触控固件、驱动、InputFlinger、应用、GPU、SurfaceFlinger 或显示阶段延后。只有事件到应用后的 handler/traversal 明显超时，才能把责任收敛到应用侧。CPU 频率低或某个 boost 没有出现，也必须结合调度、温控和对照样本解释。

### 误区：Input ANR 等于 App 卡死

连接型 Input ANR 检查 WaitQueue 条目的 `timeoutTime`。Android 17 默认 dispatching timeout 的未乘倍率基值为 5000ms，运行时还应用 `HwTimeoutMultiplier()`，窗口或应用可覆盖此值。超时表示系统没有按期收到对应 finish/ACK；原因可能是主线程长任务、Runnable 饥饿、锁等待、Binder/I/O、异步 InputStage 或进程异常。ACK 也不代表画面已 present，因此 ANR 指标不能替代跟手性测量。

## 输入重采样（Motion Resampling）机制

### 源码级细节

`android-17.0.0_r1` 同时保留两套相关代码：

- `libs/input/InputConsumer.cpp`：当前 `android_view_InputEventReceiver.cpp` 的 `NativeInputEventReceiver` 直接构造并使用这套 `InputConsumer`，重采样逻辑仍在该文件内。
- `libs/input/InputConsumerNoResampling.cpp` + `libs/input/Resampler.cpp`：把 batching/transport 与 `LegacyResampler`、`FilteredLegacyResampler` 拆开，Android 17 源树已经编译和测试这些实现，但常规 ViewRoot JNI 代码没有改用它。

分析 Android 17 应用行为时，应以第一条实际调用链为准；阅读第二套代码可以理解重构方向，不能把它描述成所有应用已经切换的生产路径。两套 legacy 算法的常量和核心边界一致：

- 目标时间 `sampleTime = frameTime - 5ms`。
- 若 batch 中还有目标时间之后的 future sample，则在 current/future 之间线性插值；两点间隔至少 2ms。
- 没有 future sample 时，用最近两个点外推；两点间隔必须在 2ms 到 20ms 之间。
- 外推最远到 `currentTime + min(delta / 2, 8ms)`。
- 支持 `FINGER`、`MOUSE`、`STYLUS`、`UNKNOWN` tool type，并要求 pointer ID、tool type 和 display 等条件一致。
- 只对 pointer source 的 `ACTION_MOVE` 执行；厂商可通过只读属性 `ro.input.resampling=0` 关闭。

Android 17 的实际系统与应用调用边界可概括为：

```text
evdev → EventHub → InputReader → TouchInputMapper → InputDispatcher
    → InputChannel/Unix SOCK_SEQPACKET
    → app NativeInputEventReceiver
    → InputConsumer.consume(..., frameTimeNanos)
    → InputConsumer::consumeBatch()
    → InputConsumer::resampleTouchState()
    → WindowInputEventReceiver → ViewRootImpl InputStage → View
```

重采样发生在目标应用进程，不在 InputReader 或 InputDispatcher 中。它通过插值/受限外推让 MOVE 坐标更接近帧时序，但急转弯、速度突变和稀疏样本仍可能产生偏差。评估时要同时比较真实样本、resampled 标记与最终笔迹，不要只看坐标是否更接近 frame time。

## 参考资料

- AOSP `android-17.0.0_r1`：
  - `frameworks/native/services/inputflinger/reader/EventHub.cpp`
  - `frameworks/native/services/inputflinger/reader/InputReader.cpp`
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
  - `frameworks/native/services/inputflinger/dispatcher/LatencyTracker.cpp`
  - `frameworks/native/services/inputflinger/trace/InputTracingPerfettoBackend.cpp`
  - `frameworks/native/libs/input/InputConsumer.cpp`
  - `frameworks/native/libs/input/InputConsumerNoResampling.cpp`
  - `frameworks/native/libs/input/Resampler.cpp`
  - `frameworks/native/libs/input/MotionPredictor.cpp`
  - `frameworks/native/libs/input/TfLiteMotionPredictor.cpp`
  - `frameworks/base/core/jni/android_view_InputEventReceiver.cpp`
  - `frameworks/base/core/jni/android_view_MotionPredictor.cpp`
  - `frameworks/base/core/java/android/view/ViewRootImpl.java`
  - `frameworks/base/core/java/android/view/Choreographer.java`
  - `frameworks/base/core/java/android/view/InputEventAssigner.java`
  - `frameworks/base/core/java/android/view/MotionEvent.java`
  - `frameworks/base/core/java/android/view/MotionPredictor.java`
  - `external/perfetto/protos/perfetto/config/android/android_input_event_config.proto`
- Android 官方文档：[Input 系统概述](https://source.android.com/docs/core/interaction/input)、[通过 adb 抓取 Input Trace](https://source.android.com/docs/core/graphics/winscope/capture/adb)、[MotionEvent](https://developer.android.com/reference/android/view/MotionEvent)、[MotionPredictor](https://developer.android.com/reference/android/view/MotionPredictor)、[Advanced Stylus](https://developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features)、[AndroidX Input](https://developer.android.com/jetpack/androidx/releases/input)
- [高爷 - Systrace 基础知识：Input 解读](https://www.androidperformance.com/2019/10/27/Android-Systrace-Input/)
- [高爷 - Systrace 响应速度实战 1](https://www.androidperformance.com/2022/03/20/android-systrace-Responsiveness-in-action-1/)
