---
title: "触摸延迟、预测与低延迟渲染"
chapter: "3.2"
section: "3.2"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-12"
last_verified_against: "AOSP android-17.0.0_r1 InputFlinger/InputTransport/ViewRootImpl/Choreographer/MotionPredictor/MotionEvent/InputEventAssigner sources; external/perfetto android.input inputevent config and android.input stdlib docs; source.android.com Input/Winscope adb trace docs; AndroidX Input/Graphics low-latency docs | 2026-08-12 rework cleared stale-source-verification finding AIW-FRESH-bfb7868d39d57e84"
confidence: medium-high
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
    path: "source.android.com/docs/core/graphics/winscope/capture/adb"
  - type: official
    path: "developer.android.com/reference/android/view/MotionEvent"
  - type: official
    path: "developer.android.com/reference/android/view/MotionPredictor"
  - type: official
    path: "developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features"
  - type: official
    path: "developer.android.com/jetpack/androidx/releases/input"
  - type: official
    path: "developer.android.com/jetpack/androidx/releases/graphics"
  - type: official
    path: "perfetto.dev/docs/analysis/stdlib-docs#android-input"
  - type: research
    path: "DeepResearch/2026-05-11-hci-perception-input-latency-analysis.md"
  - type: research
    path: "intake/research-feeds/2026-04-05-15-motionprediction-low-latency-graphics.md"
tags: [touch, input-latency, HCI, InputReader, InputDispatcher, sampling-rate, batching, resampling, MotionPredictor, front-buffer, Choreographer, responsiveness]
related_chapters: ["3.1", "2.3", "2.4", "2.5", "2.18", "2.19", "7.9", "8.1", "13.8", "15.3"]
task2b_state: fixed
task6_state: pending-review
task9_state: pending-review
last_rework_at: "2026-08-12T09:45:30+08:00"
last_rework_run_id: "20260812-093533-rework-855a7839"
pipeline_stage: ready-for-review
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch03-input/04-input-latency-prediction.md"
  - "src/part1-fundamentals/ch03-input/09-input-latency-budget-perception.md"
---

# 3.2 触摸延迟、预测与低延迟渲染

## 为什么需要关注触摸响应

在列表滑动的 Perfetto 系统跟踪中，可以沿时间轴看到 `InputReader`、`InputDispatcher`、应用主线程、`RenderThread`、SurfaceFlinger 和显示帧。触摸样本进入系统后，应用还要消费事件、更新界面状态、提交缓冲区，再由 SurfaceFlinger 合成并送显；其中任何一段延后，都会增加可见响应时间。

从物理动作到显示内容变化的时间通常称为触摸到显示延迟（touch-to-display latency）。如果终点是面板像素实际发光变化，则称为触摸到光子延迟（touch-to-photon latency）。刷新周期只是其中一个时间尺度：60 Hz 每周期约 16.67 ms，120 Hz 每周期约 8.33 ms。事件落在 VSYNC 周期的哪个相位、应用是否赶上当前帧、缓冲区是否按期合成，都会改变结果。因此，一个刷新周期不能直接代表端到端延迟，也不应脱离设备、操作和统计分位数给出通用的“典型毫秒数”。

触摸响应主要分为两类：

- **离散响应**：按下按钮后，下一帧何时显示按下状态或业务结果。
- **连续跟手**：手指或笔持续移动时，屏幕轨迹与当前位置相差多少时间和空间。

连续跟手会反复暴露位置差，通常比一次点击更容易显出延迟。工程测试应在目标设备上分别统计点击响应和连续手势，至少报告刷新率、触控模式、冷机与热机状态、P50、P90、P99 以及丢帧情况。缺少这些条件的单一数字不适合作为产品服务水平目标（SLA）。

## 先统一测量口径

“输入延迟”常指四种不同区间，不声明起止点就无法比较：

| 口径 | 起点 | 终点 | 不包含的主要部分 |
|---|---|---|---|
| 硬件到读取（hardware-to-read） | 触控控制器或内核事件 | `EventHub` 或 `InputReader` 读到事件 | 应用处理、渲染和显示 |
| 分发到确认（dispatch-to-ACK） | `InputDispatcher` 发布事件 | 系统框架收到 `FINISHED` | 完成确认后的渲染、合成与面板输出 |
| 读取到呈现（read-to-present） | `InputReader.readTime` | 关联帧的呈现时间 | 触控 IC 扫描前段与面板光学响应 |
| 触摸到光子（touch-to-photon） | 物理接触 | 目标像素实际变化 | 原则上覆盖整条链，通常需要外部仪器 |

可执行的阶段预算应记录证据来源，而不是把几个经验数相加：

| 阶段 | 常用时间点 | 责任边界 |
|---|---|---|
| 采样与驱动 | 外部接触、evdev `eventTime`、`readTime` | 触控 IC、固件、总线与内核 |
| 读取与分发 | `readTime`、发布时间、接收时间 | `InputReader`、`InputDispatcher`、目标进程调度 |
| 应用处理 | 接收时间、完成时间、`deliverInputEvent` | View、Compose、IME、主线程和异步 `InputStage` |
| 生产与合成 | 帧开始、完成与呈现时间 | `Choreographer`、`RenderThread`、GPU、BufferQueue、SurfaceFlinger |
| 面板输出 | 从系统呈现到光学变化 | HWC、显示时序和面板响应 |

CPU 与 GPU 可能并行，多个样本也可能合并到同一帧；FrameTimeline 的呈现时刻还可能早于面板上某个像素完成响应。因此，预算表用于划分调查责任，不能把各段经验值直接相加成一个看似精确的总数。

### 人机交互阈值不能脱离具体任务

直接操控的感知线索与离散点击差异很大。UIST 2012 的连续拖动实验中，参与者在该装置和 1 ms 参照延迟下的差别阈限（JND，即刚好能察觉差异的最小变化）约为 2.38–11.36 ms；CHI 2013 的落点反馈实验则得到更宽的 20–100 ms 范围。这些数字只说明任务类型会改变人的感知敏感度，不是 Android 17 设备的通用验收线。

产品指标应按照交互类型建立：点击关注首个可见反馈；拖动与书写同时关注时间滞后、空间偏差、步幅波动和预测误差；游戏还要分开统计本地判定、渲染帧和网络确认。同一脚本至少覆盖 P50、P90、P95、刷新率、温控和电源模式。

## 触摸响应延迟的组成

从手指触碰屏幕到画面更新，触摸事件要经过多个阶段。按时间顺序拆分，才能确定耗时所在的边界。

### 1. 硬件采样（触摸屏 → 驱动）

触控控制器扫描面板并把报告送到 SoC（片上系统）。扫描、滤波、去抖、总线上报和驱动中断都属于设备实现，AOSP 不规定它们必须采用哪种总线或固定采样率。若设备以近似固定频率上报，采样周期可用 `1 / samplingRate` 粗略估算：

- **120 Hz**：约 8.33 ms 一个采样周期
- **240 Hz**：约 4.17 ms 一个采样周期
- **480 Hz**：约 2.08 ms 一个采样周期

周期只给出相位等待的上界模型，不能覆盖控制器内部滤波和上报策略。更高的采样率通常能减小首次检测等待，并为轨迹重建提供更密集的 `MOVE` 样本；即使这些样本被批量放入同一个 `MotionEvent`，应用仍可以读取历史样本，系统也可以用它们进行重采样。高于显示帧率的采样并非自动浪费，但能否改善画面取决于应用是否消费历史点、是否使用无缓冲分发路径，以及渲染和显示是否及时。

### 2. 内核处理（驱动 → EventHub）

触摸驱动向 Linux input core 上报事件，evdev 再通过 `/dev/input/eventX` 暴露 `input_event` 流。Android 的 `EventHub` 使用 inotify 发现设备节点的增删，使用 epoll 等待已打开文件描述符中的数据；`getEvents()` 被唤醒后会批量读取事件。

Android 17 的 `EventHub::getEvents()` 为每个 `RawEvent` 保留两个重要时间：

- `when`：经 `processEventTimestamp()` 处理后的内核事件时间；
- `readTime`：`EventHub` 从设备节点读取事件时记录的 `SYSTEM_TIME_MONOTONIC` 时间。

`readTime - when` 可以用来判断事件从驱动与 evdev 到 `EventHub` 读取之间是否停留过久。这个差值应从目标设备的系统跟踪或日志中取得；源码没有承诺它必然小于 1 ms。

### 3. InputReader 读取和加工

`InputReader` 是运行在 `system_server` 进程中的原生线程。它从 `EventHub` 读取原始 `input_event`，完成设备映射、坐标转换、多点触控组装、工具类型识别等处理，生成 `NotifyArgs`。这些参数随后进入 Android 17 的输入监听链，经过误触处理、指针视觉状态管理、可选分类与过滤等阶段，再送到 `InputDispatcher`。

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

这段代码展示三个边界：`getEvents()` 返回 `std::vector<RawEvent>`；映射与状态更新在 `InputReader` 锁内完成；对下一个监听器的通知发生在锁外。`loopOnce()` 一次可能读到一批 evdev 事件，但“批量读取 `RawEvent`”与应用侧“把多个 `MOVE` 坐标合成一个 `MotionEvent`”分属不同层级，排查时要分开处理。

### 4. InputDispatcher 派发

`InputDispatcher` 也是 `system_server` 中的原生线程。监听链把 `NotifyArgs` 交给分发器后，事件进入队列并唤醒它的 Looper。它根据焦点、窗口信息、触摸状态、手势监视和安全策略选择一个或多个目标窗口；Activity 只是窗口背后的上层组件，不能代替窗口路由规则。

事件在 InputDispatcher 中经过三个关键队列：

1. **输入队列（InboundQueue，`iq`）**：`InputReader` 交付的事件先进入这里，`InputDispatcher` 从队首取出事件开始处理；
2. **输出队列（OutboundQueue，`oq`）**：每个目标 `Connection` 都有一条输出队列。事件被包装成 `DispatchEntry` 后进入此队列，等待发布到 `InputChannel`；
3. **等待队列（WaitQueue，`wq`）**：发布成功后，条目从输出队列移到等待队列，等待应用返回 `FINISHED`。Android 17 的回收路径由 `handleReceiveCallback()` 接收响应，再经 `finishDispatchCycleLocked()` 和 `doDispatchCycleFinishedCommand()` 按序列号删除等待队列条目。

`FINISHED` 表示应用结束了这枚输入事件的分发责任，不表示相应画面已经呈现。若事件触发了异步 `InputStage`，或应用主线程迟迟没有执行到 `finishInputEvent()`，等待队列会保持非空；渲染也可以在完成确认之后继续。因此，输入确认延迟与触摸到显示延迟需要分开测量。

在 Perfetto 中，这三个队列以计数器轨道出现，由 `ATRACE_INT` 写入 `iq`、`oq:<channel>`、`wq:<channel>`，并非执行片段。`iq` 描述尚未处理的输入事件，`oq` 描述尚未发布到通道的连接事件，`wq` 描述已发布但尚未完成的事件。

这些判断都要结合持续时间：队列在事件发布与完成确认之间短暂变为 1 属于正常状态，连续增长或长时间不归零才提示背压。`wq` 增长也不能单凭计数器断言主线程阻塞，还要查看应用主线程、异步 `InputStage` 和套接字回写时序。

对手写笔、手掌误触和边缘触控问题，还要检查 `MotionEvent` 的分类结果与取消路径。分类可能影响触摸位移阈值（touch slop）、长按判断或误触撤回；遇到首笔不生效时，应确认应用是否收到 `ACTION_CANCEL` 或 `FLAG_CANCELED`，不能只看等待队列。

### 5. 跨进程传输（socketpair）

`InputDispatcher` 通过 `InputChannel` 将事件发送给目标进程。Android 17 的通道由 `socketpair(AF_UNIX, SOCK_SEQPACKET, ...)` 建立并设为非阻塞；`InputChannel::sendMessage()` 和 `receiveMessage()` 负责消息收发。应用的 `NativeInputEventReceiver` 把文件描述符注册到主线程 Looper，文件描述符可读后再消费消息。

这里需要区分套接字写入耗时与接收线程何时获得 CPU。即使消息已经写入内核缓冲区，应用主线程处于 Running、Runnable、Blocked 或 Sleeping 状态，也会让消费时间产生很大差异。Binder 压力只有在引发 CPU 竞争或应用同步等待时才构成相关证据，不能把 Binder 和 `InputChannel` 当成同一条数据通道。

### 6. 应用端处理（View 树）

`NativeInputEventReceiver` 把事件转换成 Java `InputEvent` 后，`WindowInputEventReceiver` 会将其加入 `ViewRootImpl` 的待处理队列。Android 17 用 `aq:pending:<window>` 计数器记录队列长度，并用同步和异步 `deliverInputEvent` 区段标记整段处理。触摸这类指针事件通常从 IME 后处理链进入 `EarlyPostImeInputStage`、`NativePostImeInputStage` 和 `ViewPostImeInputStage`，再由 View 树处理。

View 的触摸分发沿命中的目标分支和已经建立的 `TouchTarget` 关系进行，并非每个 `MOVE` 都遍历整棵 View 树。事件可能只更新滚动偏移或状态，也可能触发 `invalidate()`、`requestLayout()` 或动画。前者通常只要求重绘，后者可能让下一次遍历执行测量、布局与绘制。

### 7. 渲染上屏

触摸引起的状态改变要进入某一帧，随后经过应用遍历、`RenderThread`、GPU、BufferQueue、SurfaceFlinger 和显示输出。任何一段错过当前帧的截止时间，都可能让可见反馈顺延一个或多个刷新周期。不能预设渲染一定是最长阶段：主线程调度、输入处理、GPU 和合成都要用同一份系统跟踪逐段排除。

### 延迟全景图

用源码中能够对应的时间点建立测量表，比套用一组“典型耗时”更可靠：

| 边界 | Android 17 证据 | 能回答的问题 |
|------|-----------------|--------------|
| 设备事件 → `EventHub` 读取 | `RawEvent.when`、`RawEvent.readTime` | 驱动与 evdev 到读取之间是否滞留 |
| `InputDispatcher` 入队与发布 | `android.input.inputevent`、`iq`、`oq:*` | 系统侧是否积压、目标窗口是谁 |
| 发布 → 应用消费与完成 | 发布、消费、完成时序，`wq:*` | 调度与应用输入处理是否拖延 |
| 应用输入 → 目标帧 | `deliverInputEvent`、`aq:pending:*`、`Choreographer`、输入事件 ID | 哪枚事件驱动了哪一帧 |
| 目标帧 → 呈现 | FrameTimeline、RenderThread、GPU、SurfaceFlinger | 画面为何晚一个或多个刷新周期 |

Android 17 的 `InputEventAssigner` 有一项限制：在连续手势中，一帧只关联一枚输入事件 ID。首帧优先关联尚未处理的 `DOWN`，后续帧通常关联该帧之前的最新事件；中间的 `MOVE` 可能没有独立的帧归因。因此，做端到端关联时要保留事件 ID 和历史样本，不能假设每个采样点都有一帧与之对应。

## 触摸采样率与跟手性

### 采样率不等于刷新率

这两个概念容易混淆，但表示彼此独立的频率：

- **触摸采样率**：触摸屏硬件每秒检测手指位置的次数。120 Hz 表示每秒检测 120 次；
- **屏幕刷新率**：屏幕每秒更新画面的次数。120 Hz 表示每秒刷新 120 次。

采样率影响坐标的时间密度，刷新率限定显示更新机会。两者独立运行，相位也未必对齐：240 Hz 触控与 120 Hz 显示组合，理想情况下每个显示周期约有两个触控样本；120 Hz 触控与 60 Hz 显示组合也约有两个。前一种组合的采样周期和显示周期都更短，但事件能否进入最近一帧，仍取决于到达时刻与整条处理路径，不能直接根据频率比推算端到端延迟。

### 采样率和渲染帧率的匹配

高采样率的价值，要放到“应用如何消费样本、每秒能显示多少帧”两个前提下看。

- **60 fps + 120 Hz 触控**：按理想固定频率估算，一个显示周期约有两个样本。它们可以合并到一个 `MotionEvent` 中，较早的点通过历史样本接口读取；
- **60 fps + 240 Hz 触控**：一个显示周期约有四个样本。列表仍然只能每帧呈现一次位置，但笔迹拟合、速度估计和轨迹预测可以使用更密集的数据；
- **120 fps + 240 Hz 触控**：一个显示周期约有两个样本；更短的显示周期也会缩短错过一帧后的等待；
- **无缓冲分发与前缓冲渲染**：前者缩短 `MOVE` 进入应用前的等待，后者缩短局部笔迹从绘制到可见的路径。两者作用于不同阶段，都需要设备与应用实现配合。

上面的样本数只是频率比值，不代表每个周期都会严格收到相同数量的样本。触控控制器可能动态调整报告率，显示器也可能运行在 VRR（可变刷新率）模式。验证设备规格时，应根据驱动事件时间或结构化输入跟踪统计相邻样本间隔。

## 输入事件批处理与 Choreographer 的配合

### 为什么需要批处理

当触摸采样率高于渲染帧率时，一个 VSYNC 周期内可能到达多个 `ACTION_MOVE` 样本。若每个样本都立即唤醒应用并执行完整的 View 分发，会增加 Looper 和业务回调压力；即使多次重绘请求最终合并到一帧，前面的 CPU 工作也可能重复。批处理（batching）用较少的应用交付次数携带这些样本。

Android 的输入批处理会合并交付，但不会直接删除中间坐标。Android 17 的应用侧 `InputConsumer` 会把相互兼容的 `ACTION_MOVE` 或 `ACTION_HOVER_MOVE` 消息组成一批；消费时，第一条样本初始化 `MotionEvent`，后续样本通过 `addSample()` 加入历史记录。当前坐标通过 `getX()` 和 `getY()` 读取，较早样本则通过 `getHistorySize()` 和 `getHistorical*()` 读取。

下面的代码按时间顺序处理一个包含历史样本的 `MotionEvent`，适合画笔和轨迹记录；列表滚动通常只需使用当前坐标。

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

这些历史点属于同一个事件，因此 Perfetto 中通常只会看到一次 Java `deliverInputEvent`；原生区段 `dispatchInputEvent MotionEvent ... historySize=N` 会直接给出历史样本数量。不要把一个事件中的 N 个历史点误判为 N 次 View 分发。

### 批处理之外还有重采样

批处理决定样本怎样合并交付；重采样负责让轨迹时间更接近显示帧时序。Android 17 的常规 `ViewRootImpl` 路径在应用进程 JNI 中持有 `InputConsumer`。当它使用有效的 `frameTimeNanos` 消费一批事件，而且厂商没有关闭 `ro.input.resampling` 时，会以 `frameTimeNanos - 5 ms` 为目标时间，在真实样本之间插值，或者根据最近两个样本做受限外推。

这 5 ms 是重采样目标相对于帧时间的相位偏移，用于给插值预留后续样本并限制错误外推；它不能单独计入触摸到显示耗时，更不能写成“系统额外等待 5 ms”。有效帧时间、样本间隔、工具类型或厂商开关不满足条件时，重采样会跳过。

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

重采样坐标会作为这一批中的新样本加入，事件里至少保留一个来自设备的真实样本。无缓冲分发使用 `consumeBatchedInputEvents(-1)` 立即取走所有待处理样本；旧的 `InputConsumer::consumeBatch()` 在 `frameTime < 0` 时直接返回，不执行重采样。

### Choreographer 中输入回调的优先级

在 android-17.0.0_r1 的 `Choreographer#doFrame()` 里，回调顺序是：

1. `CALLBACK_INPUT`
2. `CALLBACK_ANIMATION`
3. `CALLBACK_INSETS_ANIMATION`
4. `CALLBACK_TRAVERSAL`
5. `CALLBACK_COMMIT`

`CALLBACK_COMMIT` 运行在遍历之后，负责这一帧的绘制后工作和时间基准修正，不负责测量、布局或绘制。分析输入延迟时，主要检查前四段：输入处理排在最前面，后续动画和遍历都基于最新输入状态。

连续 `MOVE` 事件默认使用缓冲路径。`ViewRootImpl.WindowInputEventReceiver#onBatchedInputEventPending()` 会检查 `mUnbufferedInputDispatch` 和 `mUnbufferedInputSource`：当前序列请求无缓冲分发时，直接调用 `consumeBatchedInputEvents(-1)`；否则调用 `scheduleConsumeBatchedInput()`，让事件在接近下一帧输入阶段时被消费。

这条分支决定 `MOVE` 是立即送达，还是接近下一帧时由输入回调消费。普通滚动使用缓冲路径，可以减少 Looper 唤醒和 View 分发次数；笔迹、绘图、签名场景可以在确认命中目标后调用 `View.requestUnbufferedDispatch(event)`。它只影响当前手势序列，应用仍要逐个处理交付的事件，CPU 调度和回调压力也会增加。

### 批处理与等待队列在 Perfetto 中的表现

批处理与应用处理能力是两组不同的证据，在 Perfetto 中对应不同的轨道与执行片段。

**InputDispatcher 侧——分发与完成确认的背压**：

1. 找到 `system_server` 进程中的 `InputDispatcher` 线程；
2. 观察 `iq`、`oq:<channel>`、`wq:<channel>` 的 `ATRACE_INT` 计数器；它们记录队列长度，不是执行片段；
3. `WaitQueue` 反映已经分发但仍在等待应用完成确认的事件数量。`wq` 堆积说明应用端处理缓慢或确认回写延迟，不等同于批处理本身；
4. 如果等待队列持续堆积且不下降，转到目标应用检查主线程、异步 `InputStage` 与回写；计数器本身还不能区分这三种原因。

**应用侧——批量事件消费**：

1. 切换到应用进程的主线程轨道；
2. 查找原生区段 `dispatchInputEvent MotionEvent ... historySize=N`，确认应用收到的 `MotionEvent` 是否包含历史样本；
3. 查找 `deliverInputEvent src=... eventTimeNano=... id=...` 与异步 `deliverInputEvent`，确认 Java 输入处理的起止时间；
4. 观察 `aq:pending:<window>`，判断事件是否在 `ViewRootImpl` 待处理队列中等待；
5. 将事件 ID 与 FrameTimeline 和应用帧关联，确认输入更新进入哪一帧，以及该帧何时呈现。

两条证据链要分别解读：`InputDispatcher` 的 `wq:*` 用于判断分发与完成确认的背压；`historySize` 和 `MotionEvent` 历史样本才是批处理的直接证据。`Choreographer` 的输入回调通常显示为 `input` 阶段，具体界面名称会随 Perfetto 版本和采集配置变化。

## 触摸场景的性能分析方法

### 从 Input 事件路径定位瓶颈

先确定问题属于“事件晚到”“应用晚处理”还是“画面晚出现”，再沿事件 ID 和帧 ID 追踪。可按下面的顺序排查：

1. **确认设备事件时间**：比较 evdev 事件时间与 `EventHub` 读取时间，排除触控固件、驱动和读取延迟；
2. **检查 InputDispatcher**：观察结构化输入事件、`iq`、目标连接的 `oq:*` 与 `wq:*`，确认窗口选择、发布和完成确认；
3. **检查应用主线程**：从套接字可读或原生分发到 `deliverInputEvent`，区分 Running、Runnable、Sleeping 和锁等待；
4. **检查批处理**：读取 `historySize`，确认事件是否在 `CALLBACK_INPUT` 中消费，以及业务是否遗漏历史样本；
5. **检查目标帧**：用输入事件 ID、应用 FrameTimeline 和 SurfaceFlinger FrameTimeline 关联到呈现时间；
6. **归因资源瓶颈**：根据调度器、CPU 频率、GPU 和内存轨道解释等待，避免根据一个函数名直接猜测原因。

### 采集结构化 Input Trace

Android 17 的 InputFlinger 注册了 `android.input.inputevent` Perfetto 数据源。它只允许在可调试的 userdebug 或 eng 构建上采集，可以记录分发器输入事件和窗口分发信息；配置支持完整或脱敏级别，也可以按安全窗口、IME 状态和目标包规则过滤。完整记录可能包含敏感坐标，只应在本地测试设备上使用，现场采集必须使用严格规则。

下面的最小配置用于在本地测试机上短时间抓取完整输入事件。若还要看到线程调度、CPU 频率和 ATRACE 轨迹，需要同时启用 `linux.ftrace`。

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

`TRACE_MODE_TRACE_ALL` 不适合现场或用户数据采集。正式配置应改用过滤规则，并验证输出已经脱敏。

### 案例：输入提频未生效导致响应变慢

下面的设备案例说明如何从函数执行片段转向调度证据。系统跟踪中的 `processInputEventForCompatibility` 区段持续约 4 ms，但相应的 AOSP 逻辑不足以解释整段墙钟时间。展开线程状态后可见：

- 线程在该区段内并非始终处于 Running 状态，中间存在被抢占和 Runnable 等待；
- 第二次触摸没有复现该设备第一次触摸时的频率变化，主线程以较低频率执行。
- 同时唤醒的硬件服务计时器线程占用了 CPU，应用主线程因此延后获得运行机会。

这里的结论只适用于当时的设备实现：厂商输入或触摸提频没有按预期触发，再叠加线程竞争，放大了墙钟耗时。AOSP 不保证所有设备都有同名的 CPU 提频机制，也不规定输入后必须在几毫秒内升到某个频点。排查时应把执行片段拆成 Running 时间和非 Running 时间，再用频率、调度与厂商策略解释差值。

### Perfetto 中的关键轨道与执行片段

分析触摸响应时，可以检查以下轨道、计数器和执行片段：

**`system_server` 进程：**
- **InputReader 线程**：结合 `android.input.inputevent` 中的 evdev 与输入事件时间和线程调度，统计相邻采样间隔；线程唤醒间隔不等于硬件固定采样率。
- **InputDispatcher 线程**：观察 `iq`、`oq:<channel>`、`wq:<channel>` 的长度与持续时间。
  - `iq` 连续增长：dispatcher 消费速度落后于输入或其他进入系统的事件；
  - `oq` 长时间不降：消息尚未成功发布，需要检查连接状态和套接字可写性；
  - `wq` 长时间不降：已发布事件尚未收到完成确认，需要转到目标应用继续分析。

**应用进程：**
- **主线程轨道**：
  - Native `dispatchInputEvent MotionEvent ... historySize=N`
  - `aq:pending:<window>` 与 `deliverInputEvent`
  - Choreographer 的 `input`、`animation`、`insets_animation`、`traversal`、`commit`
- **FrameTimeline**：确认应用帧是否错过截止时间，以及 SurfaceFlinger 帧何时呈现；
- **CPU 与调度器轨道**：确认主线程和 `RenderThread` 的 Running、Runnable、Blocked 区间，再检查 CPU 频率。

### 用 `android.input` 拆分“分发到确认”与“读取到呈现”

Perfetto 标准库的 `android_input_events` 会把套接字往返与关联帧分开：

- `dispatch_latency_dur = receive.ts - dispatch.ts`；
- `handling_latency_dur = finish.ts - receive.ts`；
- `ack_latency_dur = finish_ack.ts - finish.ts`；
- `total_latency_dur = finish_ack.ts - dispatch.ts`；
- `end_to_end_latency_dur = frame.present_time - frame.read_time`。

`total_latency_dur` 只计算到 `FINISHED` 完成确认，不表示画面已经显示。`end_to_end_latency_dur` 从 `InputReader` 读取时间开始计算，不包含触控 IC 前段和面板光学响应。标准库无法确定事件驱动的是哪一帧时，可能选择随后最近的一帧，并把 `is_speculative_frame` 设为 `true`；这类样本适合观察分布，不宜当作单个事件的确定因果证据。

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  process_name,
  event_action,
  total_latency_dur / 1e6 AS dispatch_to_ack_ms,
  end_to_end_latency_dur / 1e6 AS read_to_present_ms,
  is_speculative_frame
FROM android_input_events
WHERE end_to_end_latency_dur IS NOT NULL
ORDER BY read_to_present_ms DESC
LIMIT 50;
```

`android_motion_events`、`android_key_events` 和 `android_input_event_dispatch` 来自结构化 `android.input.inputevent` 数据源。后者用 `event_id`、`vsync_id` 和 `window_id` 表达投递关系，本身不包含分发开始、结束或完成确认耗时。

FrameTimeline 还可能出现“帧率稳定，但内容整体晚一帧”的高延迟状态。典型的 Buffer Stuffing（缓冲区持续排队）会让应用在旧缓冲区呈现之前持续提交新缓冲区；单帧工作虽然按时结束，可见内容仍然落后。此时要同时检查 `on_time_finish`、`present_type`、`jank_type`、SurfaceFlinger `DisplayFrame` 和实际呈现时间，不能根据“没有慢帧”推导“输入延迟正常”。

### 用 dumpsys input 辅助排查

`adb shell dumpsys input` 命令可以获取输入系统的实时状态，包括：

- `EventHub` 与 `InputReader` 的设备、映射器和配置状态；
- 焦点应用与窗口、当前触摸状态和指针捕获；
- `RecentQueue`：最多 10 个最近分发或丢弃的事件及其 `age`；
- `PendingEvent`、`InboundQueue`。
- 每个连接的状态、是否可响应、输出队列和等待队列；非空条目会附带事件年龄等描述。

`age` 是执行 `dumpsys` 时计算的瞬时年龄，不存在通用的“正常必须小于 16 ms”阈值。等待队列的 ANR 截止时间在事件发布时按连接设置：默认基值为 5000 ms，再乘 `HwTimeoutMultiplier()`；窗口或应用可以覆盖分发超时。判断风险时，应查看该连接的超时设置、是否可响应，以及连续多次采样的变化趋势。

## 常见触摸卡顿原因

### 1. 主线程阻塞

主线程阻塞是常见的触摸卡顿原因。当应用主线程执行磁盘 I/O、数据库查询、复杂计算或等待 Binder 调用返回时，排队等待处理的输入事件也会被延后。

在 Perfetto 中的表现：
- 主线程长时间处于 **Running** 状态但没有处理输入
- 主线程长时间 **Runnable** 却得不到 CPU，或阻塞在 Binder、futex、I/O
- WaitQueue（wq）持续堆积
- 最早的等待队列条目越过该连接的分发超时后，`InputDispatcher` 会把连接判定为无响应

常见场景：
- `onCreate()` 或 `onResume()` 中执行了过多初始化工作
- 主线程访问数据库或 SharedPreferences
- 主线程同步等待网络、Binder 或文件 I/O
- 主线程持锁等待（`synchronized` 块、`ReentrantLock`）

### 2. 过深的 View 层级

触摸分发从根 View 进入 `dispatchPointerEvent()`，随后沿命中的子树和当前 `TouchTarget` 路径执行 `dispatchTouchEvent()`。每一层 `ViewGroup` 都可能执行拦截判断、坐标变换和监听器，但 `MOVE` 不会无条件扫描整棵树。层级深度会增加固定调用成本，复杂的自定义命中测试、监听器和手势识别通常更值得优先检查。

批处理后的一个 `MotionEvent` 只进行一次 View 分发；只有应用主动遍历历史样本，或使用无缓冲分发收到更多事件时，才会按照更多样本执行自身的轨迹逻辑。不要用“采样点数量 × 整棵 View 树深度”估算开销。

优化思路：
- 用系统跟踪或方法级采样确认 `dispatchTouchEvent()`、手势检测器和业务监听器的耗时；
- 删除没有布局或语义价值的包装层；是否改用 `ConstraintLayout` 要以测量和布局数据为依据；
- 避免在 MOVE 回调中分配大量临时对象、同步 I/O、复杂路径运算或重复 `requestLayout()`。
- 自定义容器只在手势归属明确后拦截，并正确发送和处理 `ACTION_CANCEL`。

### 3. 事件分发冲突

嵌套滚动、`ViewPager` 与横向列表、自定义手势识别器可能对方向和触摸位移阈值作出不同判断。View 分发不是跨进程的多轮协商：父 View 在当前 `dispatchTouchEvent()` 中调用 `onInterceptTouchEvent()`；若中途接管手势，原子 View 目标会收到 `ACTION_CANCEL`。

这类问题常表现为首段位移未被业务采用、父子控件反复切换状态，或者收到 `CANCEL` 后仍继续绘制，看起来像“慢半拍”。排查时应记录动作类型、触点 ID、拦截决策和 `CANCEL`，不要仅凭耗时把问题归类为系统触摸延迟。对于 `RecyclerView` 和 `NestedScrolling` 体系，应优先使用现有的嵌套滚动协议，减少重复的手势归属逻辑。

### 4. CPU 频率和调度问题

触摸事件到来时，如果 CPU 频率较低或应用主线程被调度出去，即使代码本身没有问题，输入处理的墙钟时间也会增加。

不少设备实现了 Input Boost、Touch Boost 或类似的输入提频策略，在输入到来后短时间调整 CPU、GPU 性能状态或线程所在的 CPU。这些名称、触发条件和持续时间属于 SoC 与厂商实现，不属于 Android 17 系统框架的统一约定。

验证时应比较同一设备上的正常样本与异常样本：输入之后是否出现预期的频率或调度变化，主线程的 Runnable 延迟是否同步变长，温控或功耗策略是否正在限频。没有升频只是一条现象；设备也可能使用 uclamp 利用率限制、任务放置或其他机制达到相同目标。

### 5. GPU 渲染瓶颈

如果输入处理和 View 树分发都很快，但渲染管线跟不上，例如 GPU 执行 `DisplayList` 过久、SurfaceFlinger 合成延迟或缓冲区状态异常，画面更新仍会延迟。用户会感到“手指动了但画面跟不上”。

这种情况在 Perfetto 中表现为：
- 应用 FrameTimeline 标记错过截止时间，但主线程的输入处理与遍历已经按时结束；
- `RenderThread` 的 `DrawFrame`、GPU 队列与完成时间，或栅栏等待延伸到截止时间之后；
- `dequeueBuffer` 长时间等待可用缓冲区；具体原因还要结合 BufferQueue 和消费方状态；
- SurfaceFlinger FrameTimeline 显示合成帧错过截止时间，或者目标图层的缓冲区没有赶上锁存。

`GPU Completion` 不表示用户看到画面的时间，显示侧边界应使用呈现时间。判断“慢了两帧”也要按照当时的实际刷新周期计算，不能固定写成 32 ms。

### 6. 系统低内存

内存压力会间接放大输入和渲染延迟，例如 Java 垃圾回收停顿、重大缺页（major fault）、内存回收或压缩线程占用 CPU，以及重新读取文件页。是否由内存压力导致，要以同一时间窗口内的垃圾回收、缺页、内存回收、I/O 和调度证据为准。

在 Perfetto 中表现为：
- 主线程或 `RenderThread` 的 Runnable 延迟增加；
- 垃圾回收停顿与输入处理或遍历重叠；
- `kswapd` 或内存回收活跃、重大缺页或 I/O 等待与异常帧重叠。

## 轨迹预测：面向笔迹与绘图的感知降延迟

Motion Prediction（轨迹预测）涉及四层彼此独立的概念：

- **framework API**：`android.view.MotionPredictor`，API 34 加入。
- **AndroidX 库**：`androidx.input:input-motionprediction`，为不同系统版本提供封装。
- **低延迟输入**：`requestUnbufferedDispatch()` 让真实样本更早到达应用。
- **低延迟绘制**：前缓冲（front-buffer）等方案缩短笔迹从提交到显示的路径。

这几层可以组合，但不能互相替代。预测减少的是“已知真实轨迹落后于笔尖”的感知差距；它不会让真实事件更早到达，也无法修复主线程阻塞、丢帧或 SurfaceFlinger 合成延迟。

### Android 17 framework 实现边界

`android-17.0.0_r1` 的 `MotionPredictor` 是 Java 到原生层的轻量封装。设备资源 `config_enableMotionPrediction` 决定 Java API 是否启用，AOSP 基础值为 `false`，厂商需要在确认模型适配设备后覆盖；原生层还会检查可在运行时关闭功能的系统属性 `enable_motion_prediction`。`isPredictionAvailable(deviceId, source)` 同时受这些开关约束，当前原生实现只接受手写笔来源。API 存在不表示所有 Android 17 设备都默认可用。

原生 `TfLiteMotionPredictorModel` 优先加载 `/vendor/etc/motion_predictor_model.tflite`，否则使用 `/system/etc/motion_predictor_model.tflite`；同目录的 XML 提供预测间隔、噪声下限和急转阈值等配置。输入张量包括相对轨迹的半径 `r`、角度 `phi`、压力、倾斜和方向，输出为 `r`、`phi` 与压力。Android 17 还包含受功能开关控制的急转点裁剪；无论该开关是否启用，模型的噪声下限、输出长度和请求时间都可能让 `predict()` 返回 `null`，或使结果停在早于请求时间的位置。

源码没有为预测事件定义 `FLAG_PREDICTED`。应用需要分层管理真实笔迹与临时预测笔迹：下一批真实事件到达后，删除或修正尚未确认的预测段，再继续绘制。

### 调用与绘制约束

下面的 Java 骨架展示系统框架 API 的最小调用顺序。目标时间必须使用系统运行时间（uptime）时基的纳秒值，而且同一个实例在一次手势中只能记录一个设备的事件流。

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

实际代码还要在 `ACTION_UP` 或 `ACTION_CANCEL` 时清理临时预测层，并处理多个触点、重采样点和模型不可用等情况。普通按钮点击没有连续轨迹可预测；列表滑动也应先修复调度、主线程和帧截止时间问题，再评估轨迹预测是否适合该产品交互。

## 前缓冲与低延迟图形

传统多缓冲路径要等待应用渲染、缓冲区交换、SurfaceFlinger 合成和显示刷新。整屏 UI 需要这条稳定路径；对于手写场景中的局部增量笔迹，等待完整的多缓冲提交会让墨迹持续落后于笔尖。

Jetpack 低延迟图形组件会把短生命周期的增量内容放到专用前缓冲图层（front-buffered layer），以暂时出现画面撕裂（tearing）的风险换取更早可见：

- `GLFrontBufferedRenderer`：使用 OpenGL 管理笔迹增量层和持久多缓冲层；
- `CanvasFrontBufferedRenderer`：同时管理前缓冲图层与完整场景，调用 `commit()` 时重画并提交稳定内容；
- `LowLatencyCanvasView`：在 View 层级上方管理临时单缓冲覆盖层，提交后隐藏覆盖层，由普通 View 路径保留最终内容。

| 场景 | 前缓冲适用性 | 原因 |
|---|---|---|
| 签名、白板、手写笔迹 | 适合 | 增量区域小，预测段可在真实样本到达后修正 |
| 整屏列表滚动 | 不适合 | 更新范围大，容易出现撕裂和层次错位 |
| 普通按钮反馈 | 通常不适合 | 需要与 View 状态、无障碍和动画系统保持一致 |
| 画笔、游戏准星 | 取决于引擎 | 只有引擎能正确管理局部增量层才适用 |

手写优化可以形成一条从临时内容到持久内容的明确流程：读取真实样本及历史点，必要时用无缓冲分发缩短到达等待，用 `MotionPredictor` 只产生短时间窗口内的临时点，并在前缓冲层绘制；真实样本到达后修正预测段，抬笔或分段结束时通过 `commit()` 提交到多缓冲层，并清理临时内容。只增加预测而不修正，会在轨迹急转时出现回弹；只增加前缓冲却不限制更新区域，画面撕裂可能比延迟更显眼。

## 厂商触控优化方案

这里只讨论可从系统行为验证的共性做法，不把某个厂商的营销规格写成通用结论。

### 高刷新率屏幕

更高的刷新率会缩短刷新周期：60 Hz 约为 16.67 ms，120 Hz 约为 8.33 ms，144 Hz 约为 6.94 ms。当应用和系统能按期生成帧时，它可以缩短等待显示机会的时间。VRR 设备可能根据内容、触摸、功耗和温控状态切换刷新率，因此分析时必须读取系统跟踪中该时段的实际 FrameTimeline，不能只采用设置页或规格表中的最高值。

### 触控固件与控制器调校

很多设备会定制触控固件、滤波参数、采样率和上报节奏。规格表中常见 240 Hz、480 Hz、720 Hz 甚至更高的触控采样率，但它只能说明采样机会更多，不能单独推导出触摸到显示延迟。还要结合驱动处理、`ViewRootImpl` 的批处理策略、应用是否消费历史样本，以及实际显示刷新周期。

### 调度与提频策略

厂商系统常会在输入到来后短时间提高 CPU 或 GPU 频率，或者提高 UI 相关线程的调度优先级。不同平台会给这类机制使用不同名称，但策略是否存在、持续多长、是否把线程放到高性能核心，都必须以目标设备的系统跟踪、内核和系统实现为准，不能写成固定数值。排查时应直接查看 Perfetto 中的 CPU 频率、线程调度、SurfaceFlinger 与 `RenderThread` 行为。

### 交互提示与自适应刷新率的边界

Android 17 中，`InputDispatcher` 会把符合条件的按键、触摸动作和其他动作事件归类为用户活动，默认对同类型活动设置 100 ms 的最小通知间隔。PowerManager 的交互提频信号一方面进入 Power HAL，另一方面通知 SurfaceFlinger；Scheduler 随后把仍然有效的触摸计时器转换为全局触摸信号。虽然部分方法名中含有 touch，但上游交互提频并不只由触摸触发。

这个信号只是 `RefreshRateSelector` 的一个排名输入。图层的显式帧率投票、显示策略范围、候选模式、面板与 HAL 能力以及温控状态仍可能改变结果。应用还可以用 `Window.setFrameRateBoostOnTouchEnabled()` 表达是否允许触摸升频，并用 View 或 Window 帧率 API 提交偏好；这些设置都不保证当前帧一定使用最高刷新率。

验证时应同时观察 Power `userActivity`、SurfaceFlinger `TouchState`、`Touch Boost`、`Touch Boost [late]`、图层投票、当前渲染帧率、刷新率与 FrameTimeline。完整的 ARR 选择和显示时序见 2.18 与 2.19，这里只保留与输入延迟直接相关的交互边界。

## 与其他章节的关系

触摸响应与输入分发、帧调度和渲染链路交叉关联：

- **3.1 Input 事件分发：队列、反压与丢弃**：输入事件从硬件到应用的完整分发机制；
- **2.3 VSYNC 机制**：缓冲的 `MOVE` 会接近 `Choreographer` 输入回调时消费，目标帧也由 VSYNC 驱动；无缓冲路径则不等待这一回调。理解 VSYNC 周期、截止时间和实际刷新率，才能解释事件赶上了当前帧还是顺延到下一帧；
- **2.4 Choreographer 与渲染流水线**：`CALLBACK_INPUT` 优先级、`doFrame()` 执行顺序与批处理实现见 2.4 节；
- **2.5 MainThread 与 RenderThread 协作**：View 输入分发和遍历位于主线程，部分硬件加速渲染工作交给 `RenderThread` 与 GPU；
- **8.1 响应速度原理**：输入延迟 → 处理延迟 → 输出延迟的通用模型与量化方法。

## 常见问题与误区

### 误区：触摸采样率越高越好

更高采样率可以提供更多、时间上更接近当前时刻的真实坐标，但显示帧数仍受刷新率和渲染能力限制。普通滚动中，多出的 `MOVE` 样本常进入同一个 `MotionEvent`；应用只读取当前坐标时，可见收益会受限。手写笔、轨迹拟合、轨迹预测以及高刷新率、高帧率场景更可能利用历史样本。

### 误区：触摸卡顿一定是应用的问题

事件可以在触控固件、驱动、InputFlinger、应用、GPU、SurfaceFlinger 或显示阶段延后。只有事件到达应用后的处理器或遍历阶段明显超时，才能把责任范围缩小到应用侧。CPU 频率低或某个提频信号没有出现，也必须结合调度、温控和对照样本解释。

### 误区：输入 ANR 等于应用卡死

连接型输入 ANR 检查等待队列条目的 `timeoutTime`。Android 17 默认分发超时尚未乘系数时的基值为 5000 ms，运行时还会应用 `HwTimeoutMultiplier()`，窗口或应用可以覆盖此值。超时表示系统没有按期收到相应的完成确认；原因可能是主线程长任务、Runnable 饥饿、锁等待、Binder 或 I/O、异步 `InputStage` 或进程异常。完成确认也不表示画面已经呈现，因此 ANR 指标不能替代跟手性测量。

## 输入重采样（Motion Resampling）机制

### 源码级细节

`android-17.0.0_r1` 同时保留两套相关代码：

- `libs/input/InputConsumer.cpp`：当前 `android_view_InputEventReceiver.cpp` 的 `NativeInputEventReceiver` 直接构造并使用这套 `InputConsumer`，重采样逻辑仍在该文件内。
- `libs/input/InputConsumerNoResampling.cpp` 与 `libs/input/Resampler.cpp`：把批处理与传输和 `LegacyResampler`、`FilteredLegacyResampler` 分开，Android 17 源树已经编译并测试这些实现，但常规 `ViewRootImpl` JNI 代码尚未改用它。

分析 Android 17 应用行为时，应以第一条实际调用链为准；阅读第二套代码可以理解重构方向，不能把它描述成所有应用已经切换的生产路径。两套旧算法的常量和核心边界一致：

- 目标时间为 `sampleTime = frameTime - 5 ms`；
- 若一批事件中还有目标时间之后的未来样本，则在当前样本与未来样本之间线性插值；两点间隔至少为 2 ms；
- 没有未来样本时，使用最近两个点外推；两点间隔必须在 2 ms 到 20 ms 之间；
- 外推最远到 `currentTime + min(delta / 2, 8 ms)`；
- 支持 `FINGER`、`MOUSE`、`STYLUS`、`UNKNOWN` 工具类型，并要求触点 ID、工具类型和显示器等条件一致；
- 只对指针来源的 `ACTION_MOVE` 执行；厂商可以通过只读属性 `ro.input.resampling=0` 关闭。

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

重采样发生在目标应用进程中，不在 `InputReader` 或 `InputDispatcher` 中。它通过插值或受限外推，让 `MOVE` 坐标更接近帧时序，但急转弯、速度突变和稀疏样本仍可能产生偏差。评估时要同时比较真实样本、重采样标记与最终笔迹，不要只看坐标是否更接近帧时间。

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
- AndroidX 低延迟图形：[`CanvasFrontBufferedRenderer`](https://developer.android.com/reference/androidx/graphics/lowlatency/CanvasFrontBufferedRenderer)、[`LowLatencyCanvasView`](https://developer.android.com/reference/androidx/graphics/lowlatency/LowLatencyCanvasView)
- Perfetto：[`android.input` 标准库](https://perfetto.dev/docs/analysis/stdlib-docs#android-input)、[FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- HCI 原始研究：[Ng 等，UIST 2012](https://dl.acm.org/doi/10.1145/2380116.2380124)、[Jota 等，CHI 2013](https://www.tactuallabs.com/papers/howFastIsFastEnoughCHI13.pdf)、[Henze 等，MobileHCI 2016](https://nhenze.net/uploads/Software-Reduced-Touchscreen-Latency.pdf)
- [高爷 - Systrace 基础知识：Input 解读](https://www.androidperformance.com/2019/10/27/Android-Systrace-Input/)
- [高爷 - Systrace 响应速度实战 1](https://www.androidperformance.com/2022/03/20/android-systrace-Responsiveness-in-action-1/)
