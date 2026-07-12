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
task6_state: revisiting
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
last_deepseek_cn_review_at: 2026-06-07
last_task9_autofix_at: "2026-07-12"
last_task9_audit: "2026-06-06"
pipeline_stage: task6_pending
---

# 触摸响应的性能分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 触摸响应延迟的组成：硬件采样 → 内核处理 → InputDispatcher → App 处理 → 渲染上屏
- 🔹 触摸采样率（120Hz/240Hz/480Hz）对流畅感的影响
- 🔹 输入事件 Batching 机制与 Choreographer 的配合
- 🔹 触摸场景的性能分析方法：从 Perfetto 定位延迟瓶颈
- 🔹 常见触摸卡顿原因：主线程阻塞、过深的 View 层级、事件冲突

### 扩展（可选深入）

- 🔸 Motion Prediction / Pencil Kit 的低延迟技术
- 🔸 厂商触控优化方案概述（高刷屏、低延迟触控芯片）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要关注触摸响应

在 Perfetto 中打开一段用户滑动列表的 Trace，会看到这样的画面：InputReader 线程每隔几毫秒读取一个触摸坐标，InputDispatcher 线程把这些坐标派发给应用，应用主线程被唤醒，处理事件、执行 invalidate()、等 VSync、绘制一帧。等这一帧显示出来时，用户的手指已经移动到了下一个位置，但屏幕上显示的还是上一帧的内容。

这就是触摸响应延迟。用户的手指已经离开了某个位置，但系统还没来得及把画面更新到屏幕上。在 60Hz 屏幕上，最坏情况下一帧从"触摸发生"到"画面更新"可能经历一个完整的 VSync 周期（16.6ms）的延迟；在 120Hz 屏幕上这个数字降到了约 8.3ms。但如果在 Perfetto 中仔细看，从触摸硬件采样到画面最终上屏，实际的总延迟往往在 30-80ms 之间。本节按时间顺序分解这段延迟。

理解触摸响应延迟的组成，是优化所有"跟手性"问题的前提。不管是滑动流畅度优化、启动速度优化还是 ANR 分析，Input 事件传递路径上的每一个环节都可能成为瓶颈。

### HCI 感知阈值研究

HCI 领域对触摸延迟的感知研究提供了几个方向性参考。用户对拖拽类操作的端到端延迟感知阈值在 10-25ms 量级，但具体数值依赖实验条件——任务类型（拖拽、点击、绘图）、显示设备刷新率、输入设备类型和统计口径不同，结论差异很大。当前可以确认的方向是：直接操作场景（拖拽、绘图）对延迟的敏感度明显高于离散点击；120Hz 高刷配合低延迟采样的感知优于 60Hz，但收益受端到端延迟制约。

需要注意：这些结论来自实验室条件，和 Android 端到端 touch-to-display 延迟（本节后文表格给出 15-75ms）是不同口径，不要把实验室阈值直接当作产品 SLA 使用。

## 触摸响应延迟的组成

一个触摸事件从手指触碰屏幕到画面更新显示，要经过一条相当长的路径。按时间顺序分解后，每一阶段发生了什么、耗时在哪里会更清楚。

### 1. 硬件采样（触摸屏 → 驱动）

触摸屏控制器以固定的采样率扫描触摸面板。当手指接触屏幕时，触控 IC 会在下一个采样周期检测到坐标变化，把原始数据通过 I2C 或 SPI 总线传给 SoC。这个过程的时间取决于触摸采样率：

- **120Hz 采样率**：每 8.3ms 扫描一次，意味着最坏情况下手指触摸后需要等 8.3ms 才被检测到
- **240Hz 采样率**：每 4.16ms 扫描一次
- **480Hz 采样率**：每 2.08ms 扫描一次，一些游戏手机甚至达到 720Hz 或 960Hz

采样率越高，第一个触摸事件被捕获的延迟越低，后续的 MOVE 事件也越密集。但采样率不是越高越好。如果系统的渲染帧率只有 60fps（16.6ms 一帧），那么在一个 VSync 周期内产生过多的 MOVE 事件反而会造成浪费，因为中间的事件最终会被 Batch 合并。高爷在实战分析中明确指出：在 60fps 渲染下，120Hz 的触摸采样率已经足够；只有当渲染帧率提升到 90fps 或 120fps 时，240Hz 甚至更高的触摸采样率才有实际意义。

### 2. 内核处理（驱动 → EventHub）

触摸屏驱动将原始触控数据转换为 Linux input 事件格式（`input_event` 结构体），写入 `/dev/input/eventX` 设备节点。Android 的 EventHub 利用 Linux 的 inotify + epoll 机制监听这些设备节点，当有新事件时通过 `getEvents()` 接口读取出来。

这一步的延迟通常很小（微秒级别），因为内核的中断处理和 EventHub 的 epoll 机制都是高效的。但在极端情况下，比如系统 I/O 负载极高，或者触控驱动与 SoC 之间的总线带宽被其他外设占用，这里可能引入额外的毫秒级延迟。

#### 16KB 页面大小的潜在影响

Android 15+ AOSP 支持配置 16KB 页面大小的设备。更大的页面尺寸提升了 TLB 命中率、减少了缺页异常处理开销，在 app 启动、系统启动、摄像头延迟等宏观指标上有可量化的改善（参见 Android 官方 16KB page size 文档）。

对输入分发路径的影响，目前公开资料没有给出独立的 benchmark 数据。android-17.0.0_r1 的 `InputChannel` 仍是 Unix socket `send` / `recv` 路径，不存在“socketpair mmap”这一环节；16KB 页面对输入分发的潜在收益只能宽泛理解为降低内存管理抖动，具体到 InputDispatcher → App 这条路径的收益幅度需要实测验证。如果要做 16KB 相关的触摸延迟分析，建议直接在两种页面大小的设备上对比 Perfetto trace，而不是引用未标明条件的精确百分比。

16KB 页面大小的详细分析见 §4.7。

### 3. InputReader 读取和加工

InputReader 是运行在 `system_server` 进程中的 Native 线程。它从 EventHub 读取原始的 `input_event`，经过一系列加工处理（坐标转换、多点触控合并、工具类型识别、虚拟按键判断等），转换为 Android 层面的 `NotifyArgs` 对象，然后逐个交给下一层监听器（InputDispatcher）。

核心循环在 `InputReader.loopOnce()` 中：

```cpp
// frameworks/native/services/inputflinger/reader/InputReader.cpp (android-17.0.0_r1)
// 简化伪代码，省略锁细节和边界处理
void InputReader::loopOnce() {
    // 从 EventHub 获取原始事件
    std::vector<RawEvent> events = mEventHub->getEvents(timeoutMillis);
    if (!events.empty()) {
        // 加工：RawEvent -> NotifyArgs，累积到 mPendingArgs
        mPendingArgs += processEventsLocked(events);
    }
    // 锁外：将 NotifyArgs 逐个通知给 mNextListener (即 InputDispatcher)
    std::vector<NotifyArgs> notifyArgs;
    std::swap(notifyArgs, mPendingArgs);
    for (const NotifyArgs& args : notifyArgs) {
        mNextListener.notify(args);
    }
}
```

android-17.0.0_r1 的 `loopOnce()` 已经不再使用旧版 `QueuedListener.flush()` 路径，改为 `processEventsLocked()` 返回 `NotifyArgs` 列表并累积到 `mPendingArgs`，锁外通过 `std::swap` 取出后逐个调用 `mNextListener.notify(args)` 交给 InputDispatcher。`getEvents()` 也改为返回 `std::vector<RawEvent>`，不再使用固定大小的 `mEventBuffer` 数组。一次 `loopOnce` 调用会读取并处理一批事件（一次 MOVE 操作可能产生几十个采样点），所以 InputReader 的处理效率通常不会成为瓶颈。

### 4. InputDispatcher 派发

InputDispatcher 也是 `system_server` 中的 Native 线程，被 InputReader 唤醒后开始工作。它的核心职责是找到目标窗口（哪个 App 的哪个 Activity 应该接收这个事件），然后把事件派发过去。

事件在 InputDispatcher 中经过三个关键队列：

1. **InboundQueue（"iq"）**：InputReader 交付的事件先进入这里。InputDispatcher 从队列头取出事件开始处理。
2. **OutboundQueue（"oq"）**：每个目标窗口（Connection）都有一个 OutboundQueue。事件被包装成 `DispatchEntry` 后放入对应窗口的 OutboundQueue，等待通过 socketpair 发送。
3. **WaitQueue（"wq"）**：事件通过 socket 发送给 App 后，会先从 OutboundQueue 挪到 WaitQueue，等待 App 侧把 `Finished` 信号写回 InputChannel。条目从 WaitQueue 移走，要等 `InputDispatcher` 在 `handleReceiveCallback()` → `finishDispatchCycleLocked()` → `doDispatchCycleFinishedCommand()` 里收到这个 ACK，而不是某个 View 回调刚 return 的瞬间。

这条 ACK 回路要单独看。主线程已经跑完 `onTouchEvent()`，但如果 Looper 回切、线程调度或 socket 回写又慢了一拍，WaitQueue 仍然会继续堆积。Input ANR 计时看的就是这条“已分发但未完成 ACK”的路径。

在 Perfetto 中，这三个队列以 **counter 计数器轨道**的形式出现在 `system_server` 进程的 InputDispatcher 线程中（由 `ATRACE_INT` 写入的 `iq` / `oq:*` / `wq:*` 计数器，不是 Slice）。它们是分析触摸延迟的核心入口点。如果 InboundQueue 堆积，说明 InputDispatcher 处理不过来；如果 OutboundQueue 堆积，说明目标窗口的 socket 通道拥塞；如果 WaitQueue 堆积，说明 App 端处理太慢，主线程很可能被阻塞了。

对手写笔、掌压误触和边缘触控更激进的设备，还要把 classification 一起纳入判断。系统在 dispatch 前后都可能附带分类结果；落到应用观察面时，常见信号是 `MotionEvent.CLASSIFICATION_AMBIGUOUS_GESTURE`、被放大的 touch slop / long-press timeout，以及 Android 13+ 上用 `ACTION_CANCEL` / `FLAG_CANCELED` 撤回误触输入。遇到“第一笔慢半拍”或“首个 MOVE 没生效”的问题时，别只盯 WaitQueue，也要把 classification 和 cancel 路径一起看。

### 5. 跨进程传输（socketpair）

InputDispatcher 通过 `InputChannel`（底层是 Unix socketpair）将事件发送给目标 App 进程。`InputChannel.sendMessage()` 将序列化后的 MotionEvent 写入 socket，App 端的 `Looper` 在 poll 到 socket 可读事件后，唤醒主线程处理。

这一步的延迟取决于系统的 IPC 负载和 CPU 调度状态。正常情况下 socketpair 的传输延迟在微秒级别，但如果系统繁忙（比如多个进程同时进行 Binder 调用、CPU 频率被限制），这里可能因为 CPU 调度延迟而引入额外的等待时间。

### 6. App 端处理（View 树遍历）

App 主线程被 Input 事件唤醒后，执行 `ViewRootImpl.deliverInputEvent()`。事件按照责任链模式经过多个 `InputStage` 处理（包括 ImeInputStage 处理输入法、ViewPostImeInputStage 处理 View 树分发等），最终到达 `DecorView`，开始从 View 树的根节点逐层分发。

如果这个事件导致了 UI 变化（比如点击按钮改变了 View 状态、MOVE 事件触发列表滑动），App 会调用 `View.invalidate()` 或 `ViewRootImpl.requestLayout()`，这会触发 Choreographer 申请下一个 VSync 信号，在 VSync 到来时执行 `doFrame()` 开始绘制。

### 7. 渲染上屏

从 `doFrame()` 开始，经过 measure → layout → draw（构建 DisplayList）→ syncFrameState → GPU 执行 → SurfaceFlinger 合成 → 显示输出，最终画面出现在屏幕上。这条渲染管线的详细分析在 2.4 和 2.5 节已经讲过，这里只强调一点：**从 Input 事件的视角看，渲染上屏是延迟路径上耗时最长、也最不确定的一环**。如果 GPU 繁忙、SurfaceFlinger 合成耗时、或者 Surface 的 Buffer 被占满（dequeueBuffer 等待），渲染延迟可能从正常的 8-16ms 飙升到 30-50ms 以上。

### 延迟全景图

综合来看，一次触摸响应的总延迟由以下部分组成：

| 阶段 | 典型耗时 | 变化因素 |
|------|---------|---------|
| 硬件采样 | 2-8ms | 采样率（120/240/480Hz） |
| 内核处理 + EventHub | <1ms | 驱动效率、I/O 负载 |
| InputReader 加工 | <1ms | 事件批量大小 |
| InputDispatcher 派发 | 1-3ms | 队列状态、目标窗口数量 |
| 跨进程传输 | <1ms | CPU 调度、系统负载 |
| App 处理（View 树分发） | 1-10ms | View 层级深度、事件处理逻辑 |
| 渲染上屏 | 8-50ms | GPU 负载、Buffer 状态、帧率 |
| **总计** | **~15-75ms** | 诸多因素 |

这也解释了为什么用户对拖动跟手性比点击更敏感：直接操作场景对时延的容忍度明显低于离散点击，拖动时延一旦跨过一两个刷新周期，手指位置和画面位置就更容易出现可感知的脱节。部分文献中引用的精确延迟阈值（如 PAMTD 11ms）目前还缺少可回溯的原始论文与实验条件，这里先不写成定值结论。

搞清楚了延迟的组成，一个自然的问题就是：在硬件层面，采样率对这 15-75ms 的总延迟有多大影响？是不是采样率越高就越好？

## 触摸采样率与跟手性

### 采样率 ≠ 刷新率

这是两个容易混淆的概念，但它们完全不同：

- **触摸采样率（Touch Sampling Rate）**：触摸屏硬件每秒检测手指位置的次数。120Hz 表示每秒检测 120 次。
- **屏幕刷新率（Display Refresh Rate）**：屏幕每秒更新画面的次数。120Hz 表示每秒刷新 120 次。

采样率决定了"手指位置数据"有多密集，刷新率决定了"画面更新"有多快。两者独立工作，但共同影响跟手性体验。一台 240Hz 触摸采样 + 120Hz 屏幕刷新的手机，可以在 8.3ms 内获取手指位置并在下一个 VSync 画出画面；而一台 120Hz 触摸采样 + 60Hz 屏幕刷新的手机，需要 16.6ms 才能更新画面，且手指位置数据的精度更低。

### 采样率和渲染帧率的匹配

高采样率的价值，要放到"每一帧最终能显示多少新信息"这个前提下看。

- **60fps 渲染 + 120Hz 采样**：一个 16.6ms 帧周期内通常会收集到约 2 个 MOVE 样本。系统常把它们批到同一个 `MotionEvent` 中，应用在这一帧里通常显示最新位置，前一个样本仍可通过 `getHistorySize()`、`getHistoricalX()`、`getHistoricalY()` 读取。
- **60fps 渲染 + 240Hz 采样**：一个帧周期内可能收集到约 4 个样本。普通列表滑动和点击反馈仍然只会在下一帧呈现一次画面，因此可见收益有限；但对笔迹平滑、轨迹重建和预测算法，更多样本仍有价值。
- **120fps 渲染 + 240Hz 采样**：一个 8.3ms 帧周期内大约 2 个样本，采样密度和显示频率更匹配，高刷屏的跟手感会更稳定。
- **高采样率 + unbuffered dispatch / front-buffer**：如果 App 主动关闭 batching，或者采用 front-buffer 这类低延迟路径，高采样率才更容易转化为更密的可见反馈。

所以，触摸采样率不是单独看的指标。普通手指滑动场景下，采样率高于渲染帧率后收益会迅速下降；手写笔、绘图和预测渲染场景，则更容易吃到更高采样率的红利。

## 输入事件 Batching 与 Choreographer 的配合

### 为什么需要 Batching

当触摸采样率高于渲染帧率时，一个 VSync 周期内会到达多个 `ACTION_MOVE` 样本。系统如果对每个样本都单独跑一次 measure/layout/draw，CPU 和 GPU 会做大量重复工作，而屏幕最终仍然只会在这一帧显示一个结果。

Android 的 Input batching 做的是"合并交付"，不是把中间采样直接删掉。多个 MOVE 样本可以被打包进同一个 batched `MotionEvent`，当前坐标通过 `getX()` / `getY()` 读取，历史采样通过 `getHistorySize()`、`getHistoricalX()`、`getHistoricalY()` 读取。渲染结果通常按帧呈现最新状态，但如果应用需要更平滑的轨迹，也可以显式消费这些历史样本。

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

### Batching 之外还有重采样

Batching 解决的是“一帧里来了太多点，怎么一起交给应用”；让轨迹贴着帧时间走的还有重采样。系统把 batched input 贴到 `CALLBACK_INPUT` 附近之后，Native 层 `InputConsumer` 会按照目标 frame time，在最近几个真实采样点之间做插值，补出一个更接近这一帧显示时刻的坐标。这样 120Hz 采样配 60Hz 显示仍然有价值：系统交给应用的当前坐标更接近这一帧该显示的位置，避免直接拿最新一个真实采样点造成时序偏差。

对应用来说，重采样生成的坐标可通过 `MotionEvent.PointerCoords.isResampled()`（Android 15 / API 35+）识别——`getX()` / `getY()` 读到的是当前样本坐标，是否为重采样点要看对应 PointerCoords 的 `isResampled` 字段。API 35 以下没有公开接口查询重采样状态，只能通过 Trace / 源码判断。历史样本还在，但当前坐标更贴近帧时序，指尖轨迹也更稳。也因为这个原因，`requestUnbufferedDispatch()` 只能在笔迹、绘图、签名这类场景慎用；一旦关闭 batching 和系统重采样，MOVE 事件虽然更早送达，轨迹也更容易抖。

在 Perfetto 里常见的现象是：一个 VSync 周期内先积累多个 MOVE 采样，App 在输入阶段一次性消费，然后这一帧的布局和绘制以最新状态为准。

### Choreographer 中 Input 的优先级

在 android-17.0.0_r1 的 `Choreographer#doFrame()` 里，回调顺序是：

1. `CALLBACK_INPUT`
2. `CALLBACK_ANIMATION`
3. `CALLBACK_INSETS_ANIMATION`
4. `CALLBACK_TRAVERSAL`
5. `CALLBACK_COMMIT`

`CALLBACK_COMMIT` 运行在 traversal 之后，负责这一帧的 post-draw 工作和时间基准修正，不承担 measure/layout/draw。本节分析输入延迟时，重点还是前四段，其中输入处理排在最前面，后续动画和遍历都基于最新输入状态。

连续 `MOVE` 事件默认走 buffered path。`ViewRootImpl.WindowInputEventReceiver#onBatchedInputEventPending()` 会先判断 `mUnbufferedInputDispatch` 和 `mUnbufferedInputSource`：如果当前序列请求了 unbuffered dispatch，就直接 `consumeBatchedInputEvents(-1)`；否则才 `scheduleConsumeBatchedInput()`，让事件贴着下一帧的输入阶段消费。

这条分叉决定了 MOVE 事件是立即送达还是贴着下一帧消费。普通滚动场景通常愿意用 batching 换吞吐；手写笔、绘图、签名这类低延迟场景，则经常在 `ACTION_DOWN` 后调用 `View.requestUnbufferedDispatch()`，把后续 MOVE 事件尽快送到应用，而不是统一等下一个 VSync。

### Batching 与 WaitQueue 在 Perfetto 中的表现

观察 Batching 和 App 处理能力是两个不同的视角，在 Perfetto 中对应不同的 Track 和 Slice。

**InputDispatcher 侧 — 派发/ACK 背压**：

1. 找到 `system_server` 进程的 InputDispatcher 线程
2. 观察 InboundQueue（iq）、OutboundQueue（oq）、WaitQueue（wq）的 ATRACE_INT 计数器（队列长度，不是 Slice）
3. WaitQueue 反映的是已派发但等待 App finish/ACK 的事件数量。wq 堆积说明 App 端处理慢或 ACK 回写延迟，不等同于 batching 本身
4. 如果 WaitQueue 持续堆积且不下降，说明 App 主线程跟不上事件到来速度，可能正在卡顿

**App 侧 — Batching 消费**：

1. 切换到 App 进程的主线程 Track
2. 在 `InputResponse` 区域内，如果看到 `deliverInputEvent` 快速连续执行多次，那就是在消费 Batch 中的历史事件
3. `consumeBatchedInputEvents` 的调用时刻对应 Choreographer `CALLBACK_INPUT` 阶段，一个 VSync 内积攒的 MOVE 历史样本在这里一次性取出
4. 再看 `doFrame` 的执行：它发生在 Batch 消费之后，使用最新的事件位置来计算布局和绘制

两条证据链不要混在一起：InputDispatcher 的 wq 计数器判断的是派发/ACK 背压；App 侧的 `deliverInputEvent` 连续调用和 MotionEvent history 才是 batching 的直接证据。

## 触摸场景的性能分析方法

### 从 Input 事件路径定位瓶颈

分析触摸响应问题，最有效的方法是沿着事件传递路径从源头到终点逐步排查。基本思路是：

1. **看 InputDispatcher 的队列状态**：InboundQueue、OutboundQueue、WaitQueue 是否有堆积？
2. **看 App 主线程的状态**：被 Input 唤醒后，是 Running 还是 Sleep/Runnable？
3. **看 doFrame 的执行**：Input 处理 → Animation → Traversal 各阶段的耗时
4. **再看渲染管线**：RenderThread 和 GPU 执行是否超时

### 实战案例：Input Boost 未生效导致响应慢

一个来自实战分析的典型案例：在 Perfetto 中发现 `processInputEventForCompatibility` 函数耗时 4ms，但 AOSP 代码显示这基本是个空函数。进一步排查 CPU 状态发现两个问题：

**问题一：CPU 大核频率过低。** 在 Input 事件到来时，大核频率只有 600+MHz。正常情况下，系统应该在收到 Input 事件时做 Input Boost（提频优化），把 CPU 频率拉高来加速事件处理。在这个案例中，第一次触摸有提频，但间隔 2 秒后的第二次触摸没有触发提频，导致大核在低频状态下处理 Input 事件，执行变慢。

**问题二：App 主线程被其他线程抢占。** 某个硬件服务的 POSIX timer 线程被唤醒后抢占了 App 主线程所在的大核 CPU，因为当时只有这个核心是空闲的。App 主线程被调度出去后，Input 事件处理被迫暂停，等它重新被调度回来才能继续。

这个案例的启示是：**触摸响应慢的根因不一定在 Input 系统本身，可能是 CPU 调度策略和频率管理的问题。** 分析时要同步看 CPU 频率 Track 和线程调度状态，而不能只看 Input 相关的 Slice。

### 在 Perfetto 中的关键 Track 和 Slice

分析触摸响应时，以下 Track 和 Slice 是必须关注的：

**system_server 进程：**
- **InputReader 线程**：观察原始输入事件和线程活动频率是否接近设备采样率（120Hz 约每 8.3ms 一批输入事件；Android 17 的 InputReader 原始事件通过 inputevent tracing 记录，不应简单理解成固定 Slice）
- **InputDispatcher 线程**：观察 InboundQueue（iq）、OutboundQueue（oq）、WaitQueue（wq）的长度变化
  - `iq` 堆积 → InputReader 生产过快或 InputDispatcher 处理过慢
  - `oq` 堆积 → 目标窗口的 socket 通道拥塞
  - `wq` 堆积 → App 端处理慢，是触摸卡顿最常见的表现

**App 进程：**
- **主线程 Track**：
  - `deliverInputEvent` / `Input` Slice：Input 事件消费的耗时
  - `InputResponse` Slice：整段 Input 处理区域
  - `Choreographer#doFrame`：VSync 到来后的帧处理
- **CPU Track**：主线程被唤醒后的 CPU 频率和调度状态

### dumpsys input 辅助排查

`adb shell dumpsys input` 命令可以获取 Input 系统的实时状态，包括：

- **Device 信息**：触摸屏的分辨率、采样率、校准参数
- **InputDispatcher 状态**：当前焦点窗口、各窗口的 OutboundQueue 和 WaitQueue 长度
- **RecentQueue**：最近处理的 10 个事件及其 age（年龄），可以看出事件处理的延迟

当 WaitQueue 中事件的 `age` 超过几百毫秒时，说明 App 端处理严重滞后，离 ANR（5 秒超时）不远了。

一个典型的 `dumpsys input` 输出片段如下：

```text
Input Dispatcher State:
  FocusedWindow: Window{abc1234 com.example.app/com.example.MainActivity}
  InboundQueue: <empty>
  Connections:
    - Window{abc1234}: status=NORMAL, outboundQueue=<empty>, waitQueue=3
      WaitQueue:
        MotionEvent(action=MOVE, age=42ms)
        MotionEvent(action=MOVE, age=38ms)
        MotionEvent(action=MOVE, age=35ms)
```

`waitQueue=3` 且 age 在 35-42ms 之间，说明 App 正在消费事件但速度稍慢（正常情况下 age 应该 < 16ms）。如果 age 持续增长超过几百毫秒，就要警惕主线程阻塞。

## 常见触摸卡顿原因

### 1. 主线程阻塞

这是最常见的触摸卡顿原因。当 App 主线程在执行耗时操作时（如磁盘 I/O、数据库查询、复杂的计算逻辑、等待 Binder 调用返回），所有排队等待处理的 Input 事件都会被阻塞。

在 Perfetto 中的表现：
- 主线程长时间处于 **Running** 状态但不是在做 Input 处理
- WaitQueue（wq）持续堆积
- 如果阻塞超过 5 秒，触发 Input ANR

常见场景：
- `onCreate()`/`onResume()` 中做了太多初始化工作
- 主线程访问数据库或 SharedPreferences
- 主线程等待网络请求返回
- 主线程持锁等待（synchronized 块、ReentrantLock）

### 2. 过深的 View 层级

Input 事件在 App 端的分发过程是从 DecorView 开始，逐层遍历 View 树。每一层 `ViewGroup.dispatchTouchEvent()` 都要判断：是否拦截？分发给哪个子 View？子 View 是否消费了事件？如果 View 层级很深（比如嵌套了 10+ 层 ViewGroup），每分发一个事件就要执行大量判断逻辑。

更关键的是，在滑动场景中，一个 VSync 周期内可能需要处理多个 MOVE 事件。如果每个事件都要遍历一次深层 View 树，累积的耗时可能相当可观。

优化思路：
- 扁平化布局，减少不必要的 ViewGroup 嵌套
- 使用 ConstraintLayout 减少层级
- 对于复杂列表，在 `onInterceptTouchEvent()` 中尽早拦截，避免事件在子 View 中无效遍历

### 3. 事件分发冲突

当多个 View 同时对同一个触摸事件感兴趣时（比如外层 ScrollView 和内层 RecyclerView 的滑动冲突），事件分发可能需要多轮协商才能确定最终消费者。每一轮协商都增加了延迟。

典型场景：
- 嵌套 ScrollView 的滑动方向冲突
- ViewPager 内嵌横向滑动列表
- 自定义 GestureDetector 与系统默认手势的冲突

### 4. CPU 频率和调度问题

如前文实战案例所述，触摸事件到来时如果 CPU 频率过低或 App 主线程被调度出去，即使代码本身没有问题，也会导致 Input 处理耗时增加。

Android 系统有 **Input Boost** 这类输入提频机制：在检测到 Input 事件时，短时间提高 CPU 频率，以加速事件处理和后续的帧渲染。持续时长、是否同时拉高 GPU，或者是否调整线程放置，都要看具体 SoC 和厂商策略。如果这类提频没有正确触发，触摸响应就会明显变慢。

在 Perfetto 中可以通过 CPU Frequency Track 来验证：正常情况下，Input 事件到来后 CPU 频率应该在几毫秒内拉到高频；如果没有，说明 Boost 机制可能有问题。

### Android 16 MotionPredictor Native 实现

android-17.0.0_r1 源码中，Native 层的 MotionPredictor 实现包含 TFLite 模型路径。`TfLiteMotionPredictorModel` 从 `/system/etc/motion_predictor_model.tflite` 或 `/vendor/etc/motion_predictor_model.tflite` 加载模型，输入为极坐标序列（r / phi / pressure / tilt / orientation），输出为预测坐标。

当前源码能确认的实现细节：
- 模型加载路径：`TfLiteMotionPredictorModel`，支持 system 和 vendor 两个目录
- 输入特征：极坐标（r、phi）+ pressure + tilt + orientation
- API 可用性检查：`isPredictionAvailable(deviceId, source)` 目前只对 stylus source 返回 true
- Framework API：`android.view.MotionPredictor`（Added in API 34）

源码和公开文档中未确认的内容：TCN 架构、NPU 加速、30ms 固定预测窗口、对非 stylus 输入源的支持。这些在后续版本公开前不应写成已验证结论。

开发者使用方式：先构造 `new MotionPredictor(context)` 实例，调用实例方法 `isPredictionAvailable(deviceId, source)` 检查可用性，然后用 `record(MotionEvent)` 输入真实事件，`predict(long targetTimeNanos)` 获取预测事件。预测事件与真实事件在应用自己的渲染层做来源标记——当前 `MotionEvent` 中没有 `FLAG_PREDICTED` 字段。

### 5. GPU 渲染瓶颈

如果 Input 处理和 View 树分发都很快，但渲染管线跟不上（GPU 执行 DisplayList 耗时过长、SurfaceFlinger 合成延迟、Buffer 状态异常），画面更新就会延迟。用户感知到的是"手指动了但画面跟不上"。

这种情况在 Perfetto 中表现为：
- RenderThread 的 `DrawFrame` 耗时过长（正常 < 8ms，超过 VSync 周期即为异常）
- `dequeueBuffer` 或 `queueBuffer` 处于 Binder 等待状态（说明 SurfaceFlinger 繁忙或 Buffer 被占满）
- GPU Track 显示某帧渲染接近或超过 VSync 周期
- SurfaceFlinger 进程的合成耗时异常升高

一个快速的判断方法：在 Perfetto 中选择从 `deliverInputEvent` 开始到下一帧 `GPU Completion` 结束的时间区间，如果超过 32ms（两个 VSync 周期），说明渲染管线是瓶颈。

### 6. 系统低内存

低内存会引发一系列连锁反应，间接导致触摸响应变慢：频繁 GC 导致主线程停顿、kswapd0 线程占用 CPU 资源、磁盘 I/O 增加（因为缓存不足导致更多直接 I/O）。这些因素都会让 App 主线程在处理 Input 事件时遭遇更多竞争和等待。

在 Perfetto 中表现为：
- 主线程频繁出现 Runnable 状态（等待 CPU 时间片）
- HeapTaskDaemon（GC 线程）频繁活跃
- 主线程出现 Uninterruptible Sleep - IO 状态

## Motion Prediction：面向笔迹/绘图的感知降延迟

Motion Prediction 涉及三层概念，各自独立：

- **framework API**：`android.view.MotionPredictor`，系统级 API，Added in API level 34
- **AndroidX 库**：`androidx.input:input-motionprediction`，兼容封装层
- **低延迟配套手段**：`requestUnbufferedDispatch()`、front-buffer / low-latency graphics，跟 MotionPrediction 属于不同维度

三层相关但非同一版本能力，使用时要逐层确认。

`android.view.MotionPredictor` 是系统 API。调用前要先用 `isPredictionAvailable(deviceId, source)` 判断当前设备和输入源是否支持，再把系统收到的真实 `MotionEvent` 依次送入 `record(MotionEvent)`，按目标时间调用 `predict(long)` 取回预测事件。文档还特别提醒，预测结果里也要考虑 historical samples。

AndroidX `input-motionprediction` 更像兼容层和封装层。AndroidX release notes 显示，`1.0.0-beta06` 开始"系统 prediction API 可用时优先使用系统 API"，`1.0.0-rc01` 又把默认 `minSdk` 从 API 21 调整到 API 23。旧版 stylus 文档把 motion prediction 作为 API 19+ 的低延迟书写方案来介绍，但落到具体项目时，仍要以选用的 AndroidX 版本和当前构建配置为准，不能把这类文档表述直接写成 framework API 的起始版本。

因此，本章把 Motion Prediction 限定在手写笔、绘图、签名这类连续轨迹场景。普通按钮点击和列表滑动通常不靠它解决延迟问题。对这类场景，更常见的主线仍是减少主线程阻塞、控制 batching 行为，以及缩短渲染上屏时间。

## 厂商触控优化方案

这一节只保留在系统行为里能验证的共性做法，不把某个厂商的 marketing 规格写成通用结论。

### 高刷新率屏幕

更高的刷新率会缩短 VSync 周期，60Hz 是 16.6ms，120Hz 是 8.3ms，144Hz 约 6.9ms。只要应用和系统能稳定跟上，高刷新率会直接缩短"事件处理完成后等待下一次显示刷新"的时间。Android 11 之后常见的自适应刷新率，会在滑动和动画时拉高刷新率，在静止场景再降下来，跟手性和功耗要一起看。

### 触控固件与控制器调校

很多设备会在触控固件、滤波参数、采样率和上报节奏上做定制。规格表里常见 240Hz、480Hz、720Hz 甚至更高的触控采样率，但它只能说明"采样机会更多"，不能单独推出最终触摸时延。真实体验还要叠加驱动处理、ViewRootImpl 的 batching 策略、应用是否消费历史样本，以及显示刷新过程的周期。

### 调度与提频策略

厂商 ROM 常会在输入到来后短时间提高 CPU / GPU 频率，或者提高 UI 相关线程的调度优先级。不同平台把它叫 Input Boost、Touch Boost 或别的名字，但策略是否存在、持续多长、是否把线程放到大核，都必须以目标设备的 Trace 和内核 / ROM 实现为准，不能写成固定数值。排查时直接看 Perfetto 里的 CPU frequency、线程调度和 SurfaceFlinger / RenderThread 行为，比看规格表更靠谱。

## 与其他章节的关系

触摸响应不是一个孤立的系统，它和多个章节的内容交叉关联：

- **3.1 Input 事件分发全流程**：本章聚焦于触摸事件的性能分析，3.1 章节则详细讲解了 Input 事件从硬件到 App 的完整分发机制，是理解本章内容的前置知识。
- **2.3 VSync 机制**：触摸事件的 Batching 和渲染时机都受 VSync 控制。理解 VSync 周期和 offset，才能理解为什么 MOVE 事件要"等一个 VSync"才被消费。本章"延迟全景图"里的渲染上屏耗时，就是等待 VSync 加上渲染执行时间。
- **2.4 Choreographer 与渲染流水线**：本章提到的 CALLBACK_INPUT 优先级和 doFrame() 的执行顺序，在 2.4 节有完整的机制讲解。如果想深入理解 Batching 的代码实现，建议先读 2.4。
- **2.5 MainThread 与 RenderThread 协作**：触摸事件在 MainThread 处理，渲染在 RenderThread 执行。GPU 渲染瓶颈的排查（本章"常见卡顿原因"第 5 点）需要理解这两个线程的 syncAndDrawFrame 流程，详见 2.5 节。
- **8.1 响应速度原理**：触摸响应是"响应速度"的一个子集，8.1 节从更宏观的角度讨论了"输入延迟 → 处理延迟 → 输出延迟"的通用模型，并给出了量化的优化目标。

## 常见问题与误区

### 误区：触摸采样率越高越好

不是。更高采样率不会自动变成更多可见帧。普通滚动场景里，多出来的 MOVE 样本通常会被 batching 到同一个 `MotionEvent`，或者在同一帧里一起消费；如果应用既不读取 historical samples，也没有走 unbuffered dispatch，视觉收益很快就会碰到上限。更高采样率更适合手写笔、绘图、预测渲染和高刷高帧场景。

### 误区：触摸卡顿一定是 App 的问题

不一定。触摸卡顿可能来自系统层面：CPU 调度策略不当（大核频率低、线程被抢占）、Input Boost 没有生效、SurfaceFlinger 合成延迟、系统低内存引发的连锁反应等。在 Perfetto 中同步观察 CPU 状态和系统进程的活动，才能准确定位瓶颈是在 App 侧还是系统侧。

### 误区：Input ANR 等于 App 卡死

Input ANR 的触发条件是：InputDispatcher 将事件派发给 App 后，5 秒内没有收到 `finishInputEvent()` 的回调。这说明 App 主线程卡住了，但"卡住"的原因可能是多样的：死锁、Binder 调用阻塞、磁盘 I/O 等待、甚至是因为 GC 暂停了主线程。需要结合 Perfetto 或 ANR Trace 来具体分析，而不是笼统地认为"App 写得差"。

## 输入重采样（Motion Resampling）机制

### 源码级细节

Android Native 层实现了 **LegacyResampler**（`frameworks/native/libs/input/Resampler.cpp`），负责将触摸屏硬件高频采样与屏幕刷新率解耦。核心实现逻辑：

**两种工作模式：**

1. **插值模式（Interpolation）**：收到未来帧后，在历史帧和未来帧之间线性插值
   - `alpha = (resampleTime - pastSample.eventTime) / delta`
   - `resampledCoord = lerp(pastCoord, futureCoord, alpha)`
   - `RESAMPLE_LATENCY{5ms}` 人为延迟给等待未来帧留出时间窗口
   - 适用条件：`delta ∈ [2ms, 20ms]`

2. **外推模式（Extrapolation）**：无未来帧可用时，根据历史速度预测
   - `farthestPrediction = presentSample.eventTime + min(delta/2, 8ms)`
   - 预测窗口上限 8ms，防止误差累积
   - 适用条件：`delta ∈ [2ms, 20ms]`

**关键约束：**
- 仅支持 FINGER / MOUSE / STYLUS / UNKNOWN 四种工具类型
- `isResampled=true` 标记可供 App 层查询该坐标是否为重采样点（API 35+；低版本无公开接口，需依赖 Trace / 源码判断）
- 开关：`ro.input.resampling` 系统属性（默认启用）

**调用链（基于 AOSP android-17.0.0_r1）：**

**系统侧：**
```text
evdev → EventHub → InputReader → TouchInputMapper → InputDispatcher
    → InputChannel（通过 Unix socket 将 MotionEvent 批量发送给 App）
```

**App 侧（重采样发生在这里）：**
```text
ViewRootImpl → Choreographer.doFrame()
    → NativeInputEventReceiver.consumeBatchedInputEvents(frameTimeNanos)
        → InputConsumer.consume(..., frameTime)
            → resampleTouchState() / Resampler
                → 插值或外推生成重采样坐标
    → MotionEvent 分发给 View 树
```

Resampler 位于 App 进程的 `InputConsumer` 内部（`frameworks/native/libs/input/InputConsumer.cpp`），不在系统侧的 InputReader/InputDispatcher 管线中。`Resampler.cpp` 定义在 `frameworks/native/libs/input/Resampler.cpp`。

**性能影响：**
- 正面：消除频率差带来的抖动，使触摸轨迹贴近 VSync 边界
- 负面：5ms 人为延迟，外推在速度突变时可能预测错误

源码：`frameworks/native/libs/input/Resampler.cpp`（android-17.0.0_r1）

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/inputflinger/reader/InputReader.cpp`
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
  - `frameworks/base/core/java/android/view/ViewRootImpl.java`
  - `frameworks/base/core/java/android/view/Choreographer.java`
- 官方文档：[Input 系统概述](https://source.android.com/docs/core/interaction/input)、[MotionEvent](https://developer.android.com/reference/android/view/MotionEvent)、[MotionPredictor](https://developer.android.com/reference/android/view/MotionPredictor)、[Advanced Stylus](https://developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features)、[AndroidX Input](https://developer.android.com/jetpack/androidx/releases/input)
- [高爷 - Systrace 基础知识：Input 解读](https://www.androidperformance.com/2019/10/27/Android-Systrace-Input/)
- [高爷 - Systrace 响应速度实战 1](https://www.androidperformance.com/2022/03/20/android-systrace-Responsiveness-in-action-1/)
- 高爷 - 从 Input 响应性能差的 issue 演示 Perfetto Trace 用法（见 Obsidian 素材）
- 响应时延的科学研究（见 Obsidian 素材，原始论文待补充）
- [已验证: 官方文档, source.android.com/docs/core/interaction/input]
- [已验证: 官方文档, developer.android.com/reference/android/view/MotionEvent]
- [已验证: 官方文档, developer.android.com/reference/android/view/MotionPredictor]
- [已验证: 官方文档, developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features]
- [已验证: 官方文档, developer.android.com/jetpack/androidx/releases/input]
