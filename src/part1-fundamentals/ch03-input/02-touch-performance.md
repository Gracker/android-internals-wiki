---
title: "触摸响应的性能分析"
chapter: "3.2"
section: "3.2"
status: ready-for-review
drafted_date: "2026-03-30"
drafted_by: "openclaw-task2"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-03-31"
reviewed_date: "2026-04-03"
reviewed_by: "openclaw-task6"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
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
tags: [touch, input, latency, InputReader, InputDispatcher, sampling-rate, batching, Choreographer, responsiveness]
related_chapters: ["3.1", "2.3", "2.4", "2.5", "8.1"]
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

在 Perfetto 中打开一段用户滑动列表的 Trace，我们会看到这样的画面：InputReader 线程每隔几毫秒就读取一个触摸坐标，InputDispatcher 线程把这些坐标派发给应用，应用的主线程被唤醒，处理事件、执行 invalidate()、等 VSync、绘制一帧——然后用户的手指已经移动到了下一个位置，但屏幕上显示的还是上一帧的内容。

这就是触摸响应延迟。用户的手指已经离开了某个位置，但系统还没来得及把画面更新到屏幕上。在 60Hz 屏幕上，最坏情况下一帧从"触摸发生"到"画面更新"可能经历一个完整的 VSync 周期（16.6ms）的延迟；在 120Hz 屏幕上这个数字降到了约 8.3ms，但如果我们在 Perfetto 中仔细看，从触摸硬件采样到画面最终上屏，实际的总延迟往往在 30-80ms 之间——这中间发生了什么，就是本节要讲清楚的内容。

理解触摸响应延迟的组成，是优化所有"跟手性"问题的前提。不管我们在做滑动流畅度优化、启动速度优化还是 ANR 分析，Input 事件传递路径上的每一个环节都可能成为瓶颈。

[来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md] [来源: obsidian/Personal-Knowlodge/source/android-systrace-Responsiveness-in-action-1.md]

## 触摸响应延迟的组成

一个触摸事件从手指触碰屏幕到画面更新显示，要经过一条相当长的路径。我们用时间顺序来拆解，看看每一阶段发生了什么、耗时在哪里。

### 1. 硬件采样（触摸屏 → 驱动）

触摸屏控制器以固定的采样率扫描触摸面板。当手指接触屏幕时，触控 IC 会在下一个采样周期检测到坐标变化，把原始数据通过 I2C 或 SPI 总线传给 SoC。这个过程的时间取决于触摸采样率：

- **120Hz 采样率**：每 8.3ms 扫描一次，意味着最坏情况下手指触摸后需要等 8.3ms 才被检测到
- **240Hz 采样率**：每 4.16ms 扫描一次
- **480Hz 采样率**：每 2.08ms 扫描一次，一些游戏手机甚至达到 720Hz 或 960Hz

采样率越高，第一个触摸事件被捕获的延迟越低，后续的 MOVE 事件也越密集。但采样率不是越高越好——如果系统的渲染帧率只有 60fps（16.6ms 一帧），那么在一个 VSync 周期内产生过多的 MOVE 事件反而会造成浪费，因为中间的事件最终会被 Batch 合并。高爷在实战分析中明确指出：在 60fps 渲染下，120Hz 的触摸采样率已经足够；只有当渲染帧率提升到 90fps 或 120fps 时，240Hz 甚至更高的触摸采样率才有实际意义。

[已验证: 官方文档, source.android.com/docs/core/interaction/input] [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

### 2. 内核处理（驱动 → EventHub）

触摸屏驱动将原始触控数据转换为 Linux input 事件格式（`input_event` 结构体），写入 `/dev/input/eventX` 设备节点。Android 的 EventHub 利用 Linux 的 inotify + epoll 机制监听这些设备节点，当有新事件时通过 `getEvents()` 接口读取出来。

这一步的延迟通常很小（微秒级别），因为内核的中断处理和 EventHub 的 epoll 机制都是高效的。但在极端情况下——比如系统 I/O 负载极高、或者触控驱动与 SoC 之间的总线带宽被其他外设占用——这里可能引入额外的毫秒级延迟。

### 3. InputReader 读取和加工

InputReader 是运行在 `system_server` 进程中的 Native 线程。它从 EventHub 读取原始的 `input_event`，经过一系列加工处理（坐标转换、多点触控合并、工具类型识别、虚拟按键判断等），转换为 Android 层面的 `NotifyArgs` 对象，然后通过 `QueuedListener.flush()` 发送给 InputDispatcher。

核心循环在 `InputReader.loopOnce()` 中：

```cpp
// frameworks/native/services/inputflinger/reader/InputReader.cpp
void InputReader::loopOnce() {
    // 从 EventHub 获取原始事件
    size_t count = mEventHub->getEvents(timeoutMillis, mEventBuffer, EVENT_BUFFER_SIZE);
    if (count) {
        // 加工：RawEvent -> NotifyArgs
        processEventsLocked(mEventBuffer, count);
    }
    // 将加工后的事件发送给 InputDispatcher
    mQueuedListener->flush();
}
```

注意这里 `mEventBuffer` 的大小是 256。在正常操作中，一次 `loopOnce` 调用会读取并处理一批事件（一次 MOVE 操作可能产生几十个采样点），所以 InputReader 的处理效率通常不会成为瓶颈。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/reader/InputReader.cpp] [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

### 4. InputDispatcher 派发

InputDispatcher 也是 `system_server` 中的 Native 线程，被 InputReader 唤醒后开始工作。它的核心职责是找到目标窗口（哪个 App 的哪个 Activity 应该接收这个事件），然后把事件派发过去。

事件在 InputDispatcher 中经过三个关键队列：

1. **InboundQueue（"iq"）**：InputReader 交付的事件首先进入这里。InputDispatcher 从队列头取出事件开始处理。
2. **OutboundQueue（"oq"）**：每个目标窗口（Connection）都有一个 OutboundQueue。事件被包装成 `DispatchEntry` 后放入对应窗口的 OutboundQueue，等待通过 socketpair 发送。
3. **WaitQueue（"wq"）**：事件通过 socket 发送给 App 后，从 OutboundQueue 移到 WaitQueue。直到 App 处理完事件并回调 `finishInputEvent()`，才从 WaitQueue 中移除。

在 Perfetto 中，这三个队列以 Slice 的形式出现在 `system_server` 进程的 InputDispatcher 线程中。它们是分析触摸延迟的核心入口点——如果 InboundQueue 堆积，说明 InputDispatcher 处理不过来；如果 OutboundQueue 堆积，说明目标窗口的 socket 通道拥塞；如果 WaitQueue 堆积，说明 App 端处理太慢（可能是主线程被阻塞了）。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp] [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

### 5. 跨进程传输（socketpair）

InputDispatcher 通过 `InputChannel`（底层是 Unix socketpair）将事件发送给目标 App 进程。`InputChannel.sendMessage()` 将序列化后的 MotionEvent 写入 socket，App 端的 `Looper` 在 poll 到 socket 可读事件后，唤醒主线程处理。

这一步的延迟取决于系统的 IPC 负载和 CPU 调度状态。正常情况下 socketpair 的传输延迟在微秒级别，但如果系统繁忙（比如多个进程同时进行 Binder 调用、CPU 频率被限制），这里可能因为 CPU 调度延迟而引入额外的等待时间。

### 6. App 端处理（View 树遍历）

App 主线程被 Input 事件唤醒后，执行 `ViewRootImpl.deliverInputEvent()`。事件按照责任链模式经过多个 `InputStage` 处理（包括 ImeInputStage 处理输入法、ViewPostImeInputStage 处理 View 树分发等），最终到达 `DecorView`，开始从 View 树的根节点逐层分发。

如果这个事件导致了 UI 变化（比如点击按钮改变了 View 状态、MOVE 事件触发列表滑动），App 会调用 `View.invalidate()` 或 `ViewRootImpl.requestLayout()`，这会触发 Choreographer 申请下一个 VSync 信号，在 VSync 到来时执行 `doFrame()` 开始绘制。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/ViewRootImpl.java] [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

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

这也解释了为什么用户对"拖动跟手性"特别敏感——学术论文的研究结果表明，直接触摸拖动的可感知平均最小时延（Perceivable Average Minimum Time to Display, PAMTD）仅为 11ms，而点击的可接受时延约为 263ms。也就是说，拖动场景对延迟的容忍度远低于点击场景，优化拖动跟手性是触摸响应优化的重中之重。

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_响应时延的科学研究.md] [待补充: PAMTD 11ms 数据的学术论文出处]

搞清楚了延迟的组成，一个自然的问题就是：在硬件层面，采样率对这 15-75ms 的总延迟有多大影响？是不是采样率越高就越好？

## 触摸采样率与跟手性

### 采样率 ≠ 刷新率

这是两个容易混淆的概念，但它们完全不同：

- **触摸采样率（Touch Sampling Rate）**：触摸屏硬件每秒检测手指位置的次数。120Hz 表示每秒检测 120 次。
- **屏幕刷新率（Display Refresh Rate）**：屏幕每秒更新画面的次数。120Hz 表示每秒刷新 120 次。

采样率决定了"手指位置数据"有多密集，刷新率决定了"画面更新"有多快。两者独立工作，但共同影响跟手性体验。一台 240Hz 触摸采样 + 120Hz 屏幕刷新的手机，可以在 8.3ms 内获取手指位置并在下一个 VSync 画出画面；而一台 120Hz 触摸采样 + 60Hz 屏幕刷新的手机，需要 16.6ms 才能更新画面，且手指位置数据的精度更低。

### 采样率和渲染帧率的匹配

高爷在 Input 专题文章中做了清晰的分析：

> 在屏幕刷新率和系统 FPS 都是 60 的时候，盲目提高触摸屏的采样率是没有太大的效果的。这期间如果有两个或者三个 Input 事件，那么必然有一个或者两个要被抛弃掉，只拿最新的那个。

具体来说：

- **60fps 渲染 + 120Hz 采样**：一个 VSync 周期（16.6ms）内产生约 2 个 MOVE 事件。系统会取最新的一个用于绘制，丢弃另一个。这是合理的搭配。
- **60fps 渲染 + 240Hz 采样**：一个 VSync 周期内产生约 4 个 MOVE 事件，其中 3 个被丢弃。额外的采样没有带来视觉上的改善。
- **120fps 渲染 + 240Hz 采样**：一个 VSync 周期（8.3ms）内产生约 2 个 MOVE 事件，与 60fps + 120Hz 的比例一致。这时 240Hz 采样才真正发挥了价值。

结论是：**触摸采样率应该至少是渲染帧率的 2 倍**，更高的采样率在大多数场景下意义不大。不过，更高的采样率对预测算法（Motion Prediction）有间接帮助——数据点越密集，预测越准确。

[来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

## 输入事件 Batching 与 Choreographer 的配合

### 为什么需要 Batching

当触摸采样率高于渲染帧率时（这是常见情况），一个 VSync 周期内会产生多个 MOVE 事件。如果系统对每一个 MOVE 事件都触发一次完整的渲染流程，那 GPU 和 CPU 的工作量会翻倍，而用户最终只能看到每帧一个画面——中间的渲染工作全部浪费了。

Android 的解决方案是 **Input Batching**（输入事件批量处理）。Choreographer 的 `doFrame()` 方法在处理 `INPUT` 类型的 Callback 时，会一次性消费当前所有待处理的 Input 事件，只保留最后一个 MOVE 事件的位置信息用于绘制。

从 Perfetto 中可以看到这种现象：在 InputResponse 区域内，一个 VSync 周期中的多个 MOVE 事件被快速消费，只有最后到达 VSync 边界时才触发实际的绘制操作。

### Choreographer 中 Input 的优先级

Choreographer 的 `doFrame()` 按以下顺序处理四种 Callback：

1. **CALLBACK_INPUT**：处理输入事件
2. **CALLBACK_ANIMATION**：处理动画计算
3. **CALLBACK_INSETS_ANIMATION**：处理窗口 Insets 动画
4. **CALLBACK_TRAVERSAL**：执行 measure/layout/draw

Input 被安排在第一位，这意味着在一个 VSync 周期内，系统优先处理输入事件，然后计算动画，最后才执行布局和绘制。这个顺序是精心设计的——先处理输入，才能让后续的动画和绘制基于最新的输入状态来工作。

不过，`CALLBACK_INPUT` 并不是在每次有 Input 事件时都注册的。对于 DOWN 事件，系统可能会直接唤醒主线程处理而不等待 VSync（这也是为什么 DOWN 事件的响应通常比 MOVE 更快）。对于连续的 MOVE 事件，系统倾向于等 VSync 到来后批量处理。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java] [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

### Batching 在 Perfetto 中的表现

在 Perfetto 中观察 Batching 的方法：

1. 找到 `system_server` 进程的 InputDispatcher 线程
2. 观察 WaitQueue（"wq"）的 Slice：如果在一个 VSync 周期内 WaitQueue 中有多个 MOVE 事件等待，说明 App 还没来得及处理，InputDispatcher 一直在堆积事件
3. 切换到 App 进程的主线程 Track：在 `InputResponse` 区域内，如果看到 `deliverInputEvent` 快速连续执行多次，那就是在消费 Batch 中的事件
4. 最后看 `doFrame` 的执行：它发生在 Batch 消费之后，使用最新的事件位置来计算布局和绘制

如果 WaitQueue 持续堆积且不下降，那就是一个明确的信号：App 的主线程处理速度跟不上 Input 事件的到来速度，可能正在发生卡顿。

[来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

## 触摸场景的性能分析方法

### 方法论：从 Input 事件链路定位瓶颈

分析触摸响应问题，最有效的方法是沿着事件传递路径从源头到终点逐步排查。基本思路是：

1. **看 InputDispatcher 的队列状态**：InboundQueue、OutboundQueue、WaitQueue 是否有堆积？
2. **看 App 主线程的状态**：被 Input 唤醒后，是 Running 还是 Sleep/Runnable？
3. **看 doFrame 的执行**：Input 处理 → Animation → Traversal 各阶段的耗时
4. **看渲染管线**：RenderThread 和 GPU 执行是否超时

### 实战案例：Input Boost 未生效导致响应慢

一个来自实战分析的典型案例：在 Perfetto 中发现 `processInputEventForCompatibility` 函数耗时 4ms，但 AOSP 代码显示这基本是个空函数。进一步排查 CPU 状态发现两个问题：

**问题一：CPU 大核频率过低。** 在 Input 事件到来时，大核频率只有 600+MHz。正常情况下，系统应该在收到 Input 事件时做 Input Boost（提频优化），把 CPU 频率拉高来加速事件处理。在这个案例中，第一次触摸有提频，但间隔 2 秒后的第二次触摸没有触发提频，导致大核在低频状态下处理 Input 事件，执行变慢。

**问题二：App 主线程被其他线程抢占。** 某个硬件服务的 POSIX timer 线程被唤醒后抢占了 App 主线程所在的大核 CPU，因为当时只有这个核心是空闲的。App 主线程被调度出去后，Input 事件处理被迫暂停，等它重新被调度回来才能继续。

这个案例的启示是：**触摸响应慢的根因不一定在 Input 系统本身，可能是 CPU 调度策略和频率管理的问题。** 分析时要同步看 CPU 频率 Track 和线程调度状态，而不能只看 Input 相关的 Slice。

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_从input响应性能差的issue演示perfetto_trace用法.md]

### 在 Perfetto 中的关键 Track 和 Slice

分析触摸响应时，以下 Track 和 Slice 是必须关注的：

**system_server 进程：**
- **InputReader 线程**：观察事件读取频率是否正常（120Hz 应该每 8.3ms 一个 Slice）
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

```
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

[来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

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

[自动发现: 来源 obsidian/Personal-Knowlodge/source/2026-03-05_wechat_Android_针对app的view_input优化.md]

### 3. 事件分发冲突

当多个 View 同时对同一个触摸事件感兴趣时（比如外层 ScrollView 和内层 RecyclerView 的滑动冲突），事件分发可能需要多轮协商才能确定最终消费者。每一轮协商都增加了延迟。

典型场景：
- 嵌套 ScrollView 的滑动方向冲突
- ViewPager 内嵌横向滑动列表
- 自定义 GestureDetector 与系统默认手势的冲突

### 4. CPU 频率和调度问题

如前文实战案例所述，触摸事件到来时如果 CPU 频率过低或 App 主线程被调度出去，即使代码本身没有问题，也会导致 Input 处理耗时增加。

Android 系统有 **Input Boost** 机制：在检测到 Input 事件时，临时提升 CPU 频率（通常持续约 1 秒），以加速事件处理和后续的帧渲染。如果 Input Boost 没有正确触发（比如厂商定制 ROM 修改了调度策略），触摸响应就会明显变慢。

在 Perfetto 中可以通过 CPU Frequency Track 来验证：正常情况下，Input 事件到来后 CPU 频率应该在几毫秒内拉到高频；如果没有，说明 Boost 机制可能有问题。

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_从input响应性能差的issue演示perfetto_trace用法.md]

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

[来源: obsidian/Personal-Knowlodge/source/android-systrace-Responsiveness-in-action-1.md]

## Motion Prediction：降低感知延迟

[自动发现: 来源 developer.android.com/reference/androidx/input/motionprediction]

对于手写笔和绘图场景，Android 提供了 Motion Prediction 库（`androidx.input:input-motionprediction`）来降低感知延迟。它的原理是：基于已有的 MotionEvent 轨迹数据，使用卡尔曼滤波等算法预测用户接下来的手势路径，生成预测的 MotionEvent 并提前渲染。当真实的 MotionEvent 到达后，用真实数据替换预测数据。

这套方案不适用于普通的触摸交互（手指点击和滑动），因为预测不准确时会导致画面跳动——在拖动列表时预测错一个方向，用户会立即察觉。它主要针对连续的、可预测的运动轨迹，如手写笔绘图。从 Android 4.4（API 19）开始支持，Android 13+ 的 `WindowManager` 也提供了系统级别的预测渲染支持。

在实际工程中，如果 App 不涉及手写笔场景，这一节可以跳过。对于需要集成的项目，官方推荐使用 `Jetpack` 的 `androidx.input:input-motionprediction` 库，而非直接调用平台 API。

[已验证: 官方文档, developer.android.com/reference/androidx/input/motionprediction]

## 厂商触控优化方案

[自动发现: 来源 web research]

除了 AOSP 标准的 Input 系统实现，主流手机厂商在 HAL 层和内核层做了大量定制优化。这些方案直接影响实际的触摸响应体验，但在 Perfetto 中很难直接观察到：

### 高刷新率屏幕

从 Android 10 开始，越来越多的设备支持 90Hz、120Hz 甚至 144Hz 的屏幕刷新率。更高的刷新率意味着更短的 VSync 周期，从 16.6ms 降到 8.3ms 甚至更低，直接缩短了从"事件处理完成"到"画面上屏"的等待时间。Android 11 引入了自适应刷新率（Adaptive Refresh Rate），可以根据内容类型动态调整刷新率，在滑动时用高刷、静止时降到低刷以节省功耗。

### 低延迟触控芯片

一些旗舰设备使用专用的低延迟触控 IC，采样率可达 480Hz 甚至更高，并且优化了从采样到上报的路径延迟。这些芯片通常还支持压力感应和悬停检测。

### Input Boost 策略

厂商会定制 CPU 的 Input Boost 策略：在检测到触摸事件时，不仅提升 CPU 频率，还可能把 App 的主线程和 RenderThread 绑定到大核上执行，确保触摸响应的关键路径获得最高的 CPU 优先级。

[待验证：各厂商具体的 Input Boost 实现差异]

## 与其他章节的关系

触摸响应不是一个孤立的系统，它和多个章节的内容交叉关联：

- **3.1 Input 事件分发全流程**：本章聚焦于触摸事件的性能分析，3.1 章节则详细讲解了 Input 事件从硬件到 App 的完整分发机制，是理解本章内容的前置知识。
- **2.3 VSync 机制**：触摸事件的 Batching 和渲染时机都受 VSync 控制——理解 VSync 周期和 offset，才能理解为什么 MOVE 事件要"等一个 VSync"才被消费。本章的"延迟全景图"中渲染上屏的耗时，本质上就是等待 VSync + 渲染执行的时间。
- **2.4 Choreographer 与渲染流水线**：本章提到的 CALLBACK_INPUT 优先级和 doFrame() 的执行顺序，在 2.4 节有完整的机制讲解。如果想深入理解 Batching 的代码实现，建议先读 2.4。
- **2.5 MainThread 与 RenderThread 协作**：触摸事件在 MainThread 处理，渲染在 RenderThread 执行。GPU 渲染瓶颈的排查（本章"常见卡顿原因"第 5 点）需要理解这两个线程的 syncAndDrawFrame 流程，详见 2.5 节。
- **8.1 响应速度原理**：触摸响应是"响应速度"的一个子集，8.1 节从更宏观的角度讨论了"输入延迟 → 处理延迟 → 输出延迟"的通用模型，并给出了量化的优化目标。

## 常见问题与误区

### 误区：触摸采样率越高越好

不是。触摸采样率应该与屏幕刷新率和渲染帧率匹配。在 60fps 渲染下，120Hz 采样率已经足够。过高的采样率只会产生更多被丢弃的事件，白白消耗触控 IC 和 InputReader 的算力，还可能导致事件分布不均匀引起 UI 抖动。

### 误区：触摸卡顿一定是 App 的问题

不一定。触摸卡顿可能来自系统层面：CPU 调度策略不当（大核频率低、线程被抢占）、Input Boost 没有生效、SurfaceFlinger 合成延迟、系统低内存引发的连锁反应等。在 Perfetto 中同步观察 CPU 状态和系统进程的活动，才能准确定位瓶颈是在 App 侧还是系统侧。

### 误区：Input ANR 等于 App 卡死

Input ANR 的触发条件是：InputDispatcher 将事件派发给 App 后，5 秒内没有收到 `finishInputEvent()` 的回调。这确实说明 App 主线程卡住了，但"卡住"的原因可能是多样的：死锁、Binder 调用阻塞、磁盘 I/O 等待、甚至是因为 GC 暂停了主线程。需要结合 Perfetto 或 ANR Trace 来具体分析，而不是笼统地认为"App 写得差"。

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/inputflinger/reader/InputReader.cpp`
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
  - `frameworks/base/core/java/android/view/ViewRootImpl.java`
  - `frameworks/base/core/java/android/view/Choreographer.java`
- [已验证: 官方文档, source.android.com/docs/core/interaction/input]
- [已验证: 官方文档, developer.android.com/reference/android/view/MotionEvent]
- [已验证: 官方文档, developer.android.com/reference/androidx/input/motionprediction]
- [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]（高爷原创：Systrace 基础知识 - Input 解读）
- [来源: obsidian/Personal-Knowlodge/source/android-systrace-Responsiveness-in-action-1.md]（高爷原创：Systrace 响应速度实战 1）
- [来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_从input响应性能差的issue演示perfetto_trace用法.md]
- [来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_响应时延的科学研究.md]
- [引用: http://gityuan.com/2016/12/11/input-reader/]
- [引用: http://gityuan.com/2016/12/17/input-dispatcher/]
