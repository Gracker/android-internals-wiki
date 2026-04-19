---
title: "输入延迟与预测输入技术"
chapter: "3.4"
section: "3.4"
status: ready-for-review
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "AOSP android-16.0.0_r1 + developer.android.com + perfetto stdlib docs"
confidence: medium
sources:
  - type: official
    path: "source.android.com/docs/core/interaction/input"
  - type: official
    path: "developer.android.com/reference/androidx/input/motionprediction/MotionEventPredictor"
  - type: official
    path: "https://developer.android.com/reference/android/view/MotionPredictor"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#android_input_events"
  - type: blog
    path: "https://kernel.meizu.com/2023/10/27/Android-inputTuning-and-Optimizing/"
  - type: blog
    path: "intake/research-feeds/2026-04-05-15-input-pipeline-latency-breakdown.md"
  - type: blog
    path: "intake/research-feeds/2026-04-05-15-motionprediction-low-latency-graphics.md"
  - type: blog
    path: "intake/research-feeds/2026-04-05-15-perfetto-input-latency-sql.md"
tags: [input, latency, touch, prediction, motioneventpredictor, front-buffer, kalman-filter, perfetto, input-latency]
related_chapters: ["3.1", "3.2", "2.3", "2.4", "2.5", "8.1", "13.3", "13.5"]
pipeline_stage: task9_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task6_result: pass-light-edit
task9_result: needs-rework
task2b_result: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-19"
---

# 3.4 输入延迟与预测输入技术

<!-- outline-start -->
## 要点

### 🔹 锚点 1
输入延迟的端到端模型

### 🔹 锚点 2
触控事件在内核层的处理

### 🔹 锚点 3
InputDispatcher 的延迟优化

### 🔹 锚点 4
预测输入与触控预测（Touch Prediction）

### 🔹 锚点 5
输入延迟在 Perfetto 中的分析方法

### 🔹 锚点 6
降低输入延迟的优化策略

## 扩展

### 🔸 扩展点 1
手写笔（Stylus）的延迟特性

### 🔸 扩展点 2
Android 17 Predictive Back 的输入关联

<!-- outline-end -->

## 为什么要了解输入延迟

在 §3.1 中我们走过了 Input 事件从硬件到 App 的完整分发过程，在 §3.2 中我们分析了触摸响应的性能表现。但当我们真正面对一个用户投诉"滑动手势不跟手"或"点击按钮反应慢"的问题时，我们更关心的是更精确的量化：延迟到底发生在哪个环节？有多少毫秒？能不能消除？有没有办法让用户感知到的延迟比实际更小？

UX 研究表明，用户对输入响应延迟的感知阈值大约在 100ms——低于这个值，用户会觉得"即时响应"；高于 200ms，用户会明显感觉到迟滞。而在 Android 的标准渲染管线中，从手指触碰屏幕到像素点亮的端到端延迟，典型值在 2-3 个 VSync 周期（60Hz 屏幕上约 33-50ms，120Hz 屏幕上约 17-25ms）。这个数字看起来离 100ms 还有余量，但实际场景中叠加主线程卡顿、调度延迟、GPU 合成时间等因素，很容易突破感知阈值。

这就是本节要解决的问题：把输入延迟拆解成可量化、可追踪的阶段，然后用两种思路来改善——一种是**减少实际延迟**（优化管线各阶段耗时），另一种是**减少感知延迟**（用预测算法提前渲染用户可能看到的画面）。


## 输入延迟的端到端模型

### 六个阶段的延迟分解

一个触控事件从指尖到像素，需要经过六个阶段。每个阶段都引入自己的延迟，它们叠加起来构成端到端延迟：

[已验证: source.android.com/docs/core/interaction/input + AOSP Choreographer.java]

**阶段 1：硬件采样延迟**（触控 IC → 中断）
触控 IC（Touch Panel Controller）以固定的采样率扫描屏幕电容变化，通常为 120Hz 或 240Hz（高端设备可达 480Hz）。当检测到触控事件后，IC 通过 I2C 或 SPI 总线向 CPU 发出中断。采样率决定了硬件层面的最小延迟粒度：120Hz 采样率下，最坏情况需要等待 8.33ms 才能采集到一次触控。

**阶段 2：内核处理延迟**（中断 → /dev/input/eventX）
CPU 响应中断后，内核的 input 子系统将原始数据解码为标准 Linux input_event 结构体，写入 `/dev/input/eventX` 设备节点。这个阶段通常在 1ms 以内，但受中断处理优先级和内核调度影响。在某些 SoC 上，如果触控中断被分配到大核上的高优先级 IRQ 线程，延迟可以压到亚毫秒级。

**阶段 3：EventHub → InputReader 延迟**（读取原始事件）
Android 的 EventHub 通过 epoll 监听 `/dev/input/` 目录下的设备节点，InputReader 线程调用 EventHub.getEvents() 读取原始 input_event，将其转换为 Android 层的 MotionEvent/KeyEvent。InputReader 是一个 Native 循环线程，运行在 system_server 进程中。这个阶段的延迟取决于 InputReader 线程的调度及时性——在魅族内核团队的实测中，游戏场景下高报点率时，InputReader 经常因为调度不及时导致事件积压（参见本章扩展阅读）。

[来源: Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

**阶段 4：InputDispatcher 分发延迟**（事件路由 → socketpair 发送）
InputDispatcher 从 InputReader 获取事件后，执行窗口焦点判断、事件过滤（InputFilter）、策略拦截（Policy）等操作，然后通过 InputChannel（底层是 socketpair）将事件发送到目标 App 进程。这里选择 socketpair 而非 Binder 的原因是为了避免 Binder 线程池的竞争，同时可以追踪 ANR 超时（InputDispatcher 通过收不到 ACK 来判断超时，5 秒未响应即报 ANR）。分发延迟通常在 1-3ms，但如果 InputDispatcher 线程调度不及时（和 InputReader 一样的问题），延迟可能飙升到 10ms 以上。

[已验证: AOSP frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

**阶段 5：App 输入处理延迟**（InputChannel → ViewRootImpl → View 树）
事件到达 App 进程后，并不会天然等到下一个 VSync 才开始处理。`ViewRootImpl.WindowInputEventReceiver.onInputEvent()` 会先调用 `processRawInputEvent(event)`，随后主线程消息循环收到 `MSG_DISPATCH_INPUT_EVENT`，再通过 `enqueueInputEvent(event, receiver, 0, true)` 把事件放入本地待处理队列，交给 `doProcessInputEvents()` 和 `deliverInputEvent` 流程分发给 View 树。

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1
@Override
public void onInputEvent(InputEvent event) {
    processRawInputEvent(event);
}

...

case MSG_DISPATCH_INPUT_EVENT: {
    InputEvent event = (InputEvent) args.arg1;
    InputEventReceiver receiver = (InputEventReceiver) args.arg2;
    enqueueInputEvent(event, receiver, 0, true);
} break;
```

这里要分清两件事。第一，输入事件的逻辑处理可以在主线程拿到消息后立即开始。第二，用户是否已经看到反馈，还要看下一帧什么时候开始绘制。

批量 motion event 是另一条分支。`onBatchedInputEventPending()` 会根据是否开启 unbuffered dispatch，决定立刻消费还是挂到 `Choreographer.CALLBACK_INPUT`：

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1
@Override
public void onBatchedInputEventPending(int source) {
    final boolean unbuffered = mUnbufferedInputDispatch
            || (source & mUnbufferedInputSource) != SOURCE_CLASS_NONE;
    if (unbuffered) {
        consumeBatchedInputEvents(-1);
        return;
    }
    scheduleConsumeBatchedInput();
}

void scheduleConsumeBatchedInput() {
    mChoreographer.postCallback(Choreographer.CALLBACK_INPUT,
            mConsumedBatchedInputRunnable, null);
}
```

这就是为什么同样是触控事件，有些 trace 会看到事件刚到 App 就进入 `DeliverInputEvent`，有些则贴着下一帧的 `CALLBACK_INPUT` 统一消费。手写笔、绘图、部分低延迟交互会请求 unbuffered dispatch，换更短的等待时间。代价是失去 batching 和 resampling 带来的平滑收益。`View.requestUnbufferedDispatch(MotionEvent)` 的文档也明确写了，这个 API 不适合大多数应用，副作用包括 jittery scrolls 和无法利用 system resampling。

[已验证: AOSP android-16.0.0_r1, ViewRootImpl.java + View.java]

**阶段 6：视觉反馈等待下一帧并完成上屏**
事件逻辑处理完，不等于像素已经更新。多数 UI 反馈仍要等下一次 `Choreographer#doFrame()` 触发 `CALLBACK_INPUT → CALLBACK_ANIMATION → CALLBACK_TRAVERSAL → CALLBACK_COMMIT`，View 树才会完成 measure/layout/draw，随后通过 `queueBuffer()` 提交 GraphicBuffer，交给 SurfaceFlinger 在后续 VSYNC-sf 上屏。

```java
// frameworks/base/core/java/android/view/Choreographer.java
// @ AOSP android-16.0.0_r1
mFrameInfo.markInputHandlingStart();
doCallbacks(Choreographer.CALLBACK_INPUT, frameIntervalNanos);

mFrameInfo.markAnimationsStart();
doCallbacks(Choreographer.CALLBACK_ANIMATION, frameIntervalNanos);
doCallbacks(Choreographer.CALLBACK_INSETS_ANIMATION, frameIntervalNanos);

mFrameInfo.markPerformTraversalsStart();
doCallbacks(Choreographer.CALLBACK_TRAVERSAL, frameIntervalNanos);

doCallbacks(Choreographer.CALLBACK_COMMIT, frameIntervalNanos);
```

所以我们分析输入延迟时，至少要拆成两段。一段是“事件多久送到并被 App 处理”，另一段是“处理结果多久出现在下一帧并真正显示”。前者更多受 InputDispatcher、主线程消息队列和 batching 影响，后者更多受 VSync 对齐、渲染耗时和 SurfaceFlinger 合成影响。

[已验证: AOSP android-16.0.0_r1, Choreographer.java]

### 典型延迟量级

以 120Hz 屏幕（VSync 周期 8.33ms）为例，一个“理想路径”的触控响应延迟大约是：

| 阶段 | 典型延迟 |
|------|----------|
| 硬件采样 | 0 - 8.33ms |
| 内核处理 | 0.5 - 1ms |
| InputReader | 0.5 - 2ms |
| InputDispatcher | 0.5 - 3ms |
| VSync 等待 | 0 - 8.33ms |
| App 渲染 | 4 - 8ms |
| SurfaceFlinger 合成 | 4 - 8ms |
| **总计** | **约 10 - 38ms** |

最坏情况下约 38ms（约 3 个 VSync 周期），在 120Hz 屏幕上用户不太容易察觉。但如果主线程有额外的工作（如 RecyclerView 的复杂 item 布局），App 渲染阶段可能超过一个 VSync 周期，导致需要多等一帧，总延迟直接翻倍。

### VSync 同步引入的固有延迟

上面表格中的“VSync 等待”，指的是视觉反馈等待，而不是所有输入事件都在这一段才开始处理。未批量化的输入事件可以先进入 `ViewRootImpl` 的即时处理路径，但只要这个事件最终要驱动 View 更新，大多数 UI 反馈仍然得等下一次 `doFrame()` 才能真正显示出来。

这也是 §2.3 中 VSYNC offset 机制的价值所在。通过让 VSYNC-app 和 VSYNC-sf 之间保持可预测的时间差，App 的渲染和 SurfaceFlinger 的合成可以流水线化，减少“事件处理完成了，但像素还要再等一拍”的额外等待。

[交叉引用: §2.3 VSync 机制 中关于 DispSync 和 offset 的详细分析]


## 触控事件在内核层的处理

### 从触控 IC 到 /dev/input/eventX

触控 IC 的工作方式是周期性扫描屏幕的电容矩阵。当手指接触或移动时，对应位置的电容值发生变化，IC 识别出触控点的坐标、压力等信息，通过 I2C 或 SPI 总线向 CPU 发送中断。内核的中断处理函数（IRQ handler）读取 IC 的寄存器数据，构造 `input_event` 结构体，写入 `/dev/input/eventX` 设备文件。

在 Perfetto 中，如果启用了 `input` trace category，会记录从内核到 userspace 的输入事件时间戳。通过比较 `input_event` 的时间戳和 InputReader 收到事件的时间戳，可以量化内核层面的延迟。

### 固件（firmware）对延迟的影响

触控固件是很多性能分析中容易被忽略的环节。固件决定了触控 IC 的采样策略、报点频率、过滤算法等。魅族内核团队在优化实践中提到，降低 TP 固件的休眠延迟和提高采样率可以改善触控响应速度，但代价是功耗增加——这就是为什么很多 OEM 会根据场景动态调整报点率（游戏场景拉高，桌面场景降低）。

[来源: Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

[待验证: 触控固件报点率动态调整的具体阈值和策略]


## InputDispatcher 的延迟优化

### 分发策略与 ANR 超时

InputDispatcher 的核心工作是找到正确的目标窗口并将事件发送过去。它维护了三个关键队列，在 Perfetto 中以 counter track 的形式呈现：

- **iq（InboundQueue）**：InputReader 交付给 InputDispatcher 的待处理事件
- **oq（OutboundQueue）**：即将通过 socketpair 发送给特定窗口的事件
- **wq（WaitQueue）**：已发送但等待 App ACK 的事件

[已验证: AOSP frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp, traceInboundQueueLengthLocked/traceOutboundQueueLength/traceWaitQueueLength]

在 Perfetto 中追踪这三个队列的长度变化，是定位输入延迟瓶颈的经典方法。如果 iq 持续非零，说明 InputReader 到 InputDispatcher 的处理跟不上；如果 wq 堆积，说明 App 主线程来不及处理输入事件。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
// @ AOSP android-16.0.0_r1
void InputDispatcher::traceInboundQueueLengthLocked() {
    if (ATRACE_ENABLED()) {
        ATRACE_INT("iq", mInboundQueue.size());
    }
}
```

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### 线程调度对延迟的关键影响

魅族内核团队在游戏场景的优化中发现了一个典型问题：InputReader 和 InputDispatcher 线程由于调度策略不够积极，在 CPU 负载高时经常处于 Runnable 状态但迟迟拿不到 CPU 时间。在 Perfetto 中表现为这两个线程出现长时间的 Runnable 状态（等待调度），导致触控事件从底层报出后长时间没有被读取和分发。

修复方案是调整 InputReader 和 InputDispatcher 线程的调度策略，提高其优先级（如使用 SCHED_FIFO 或提高 nice 值）。修改后 Perfetto 显示这两个线程的调度延迟大幅缩短，应用侧的 DeliverInputEvent 不再出现断档。

[来源: Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

这个案例揭示了一个常见规律：**输入延迟问题有时不在“处理太慢”，而在调度没有跟上**。在分析输入延迟时，除了看事件处理耗时，还要看相关线程的调度状态，是 Running、Runnable 还是 Sleeping。

[待验证: Android 16/17 中 InputReader/InputDispatcher 的默认调度策略是否有改进]


## 预测输入与触控预测（Touch Prediction）

### 感知延迟 vs 实际延迟

上面讨论的所有优化都在减少**实际延迟**——让事件更快地从触控 IC 传递到屏幕。但还有另一种思路：减少**感知延迟**。如果在真实触控数据到达之前，系统能预测用户的下一个触控点在哪里，并提前渲染出来，用户就会觉得响应更快。

Android 提供了两条互补的路径：

1. **MotionEventPredictor**（Jetpack 库）：通过 Kalman Filter 算法预测未来触控点，降低感知延迟
2. **低延迟图形库**（Jetpack graphics-core）：通过前缓冲渲染（Front Buffer Rendering）绕过多缓冲交换，降低实际渲染延迟

### MotionEventPredictor 的工作原理

Jetpack 的 `androidx.input.motionprediction.MotionEventPredictor` 对外暴露的是三个核心 API：`newInstance(View)`、`record(MotionEvent)` 和 `predict()`。当前公开文档里没有 `predict(MotionEvent)` 这个重载，示例也不能把原始 `MotionEvent` 直接传进 `predict()`。

```java
MotionEventPredictor predictor = MotionEventPredictor.newInstance(view);

predictor.record(motionEvent);
MotionEvent predictedEvent = predictor.predict();
```

[已验证: developer.android.com/reference/androidx/input/motionprediction/MotionEventPredictor]

`record()` 负责把真实事件送进预测器，`predict()` 返回基于已有轨迹估算出来的预测事件。渲染层要把真实点和预测点分开处理。预测点只用于缩短感知延迟，真实点到达后仍然要回写最终笔迹。

Jetpack API 和 platform API 要分开讲。AndroidX 的 `MotionEventPredictor` 是库封装。framework 里的 `android.view.MotionPredictor` 文档写明 Added in API level 34，对应 Android 14。也就是说，如果我们讨论 framework 内建预测器，版本边界应该写 Android 14+；如果讨论 AndroidX 封装，就直接引用 AndroidX API，不要把它混成“Android 12+ 的系统级预测 API”。

`android.view.MotionPredictor` 的接口也不同。它使用 `record(MotionEvent)` 累积真实事件，用 `predict(long)` 按目标时间预测，并可通过 `isPredictionAvailable(int, int)` 检查设备和输入源是否支持。

[已验证: developer.android.com/reference/android/view/MotionPredictor]

Kalman Filter 适合这个场景，是因为一次预测只需要轻量的矩阵运算，能塞进每帧的输入处理预算里。它的局限也很明确。轨迹突然折返、急停或抬笔时，预测点会偏离真实路径，所以笔迹类应用通常只把它用在“笔尖前沿”的临时显示，不直接当最终结果。

### 前缓冲渲染（Front Buffer Rendering）

如果说 MotionEventPredictor 是在"猜"用户下一步会去哪里，那么前缓冲渲染就是在缩短"画出来"的时间。

传统的渲染管线使用三缓冲（或双缓冲）机制：App 渲染到 Buffer A，SurfaceFlinger 从 Buffer B 合成，Buffer C 作为空闲缓冲等待。这种模式保证了画面不撕裂，但代价是至少多了一个缓冲周期的延迟——App 画好的内容要等到下一轮 buffer swap 才能被 SurfaceFlinger 拿到。

前缓冲渲染绕过了这个交换过程，直接写入当前正在显示的前缓冲区。这就像在一张正在展示的幻灯片上直接画线，而不是换一张新的幻灯片。对于局部更新（如笔画绘制），效果极好；对于全屏重绘，则会造成画面撕裂。

Jetpack 低延迟图形库提供了三层 API：

[已验证: developer.android.com/develop/ui/views/graphics/low-latency-graphics]

- **GLFrontBufferedRenderer**：基于 OpenGL 的前缓冲 + 多缓冲双模式
- **CanvasFrontBufferedRenderer**：基于硬件加速 Canvas，回溯到 API 29
- **LowLatencyCanvasView**：最简方案，内部管理 SurfaceView

以 `CanvasFrontBufferedRenderer` 为例，当手写笔在屏幕上画线时：
1. 笔画的前端（用户正在画的部分）通过前缓冲立即显示，延迟极低
2. 手写笔抬起后，系统自动切回多缓冲模式，将完整笔画持久化到正常渲染管线
3. 背景内容始终通过多缓冲渲染，避免撕裂

[已验证: developer.android.com, graphics-core 1.0.4 library]

### 组合使用：最佳实践

Google 推荐在笔迹类应用中同时使用 MotionEventPredictor 和前缓冲渲染。两者解决不同层面的问题：

- **MotionEventPredictor** 降低感知延迟：在真实数据到达前渲染预测点
- **前缓冲渲染** 降低实际渲染延迟：绕过 buffer swap 直接写屏

组合后的效果是：预测点通过前缓冲渲染立即显示 → 真实数据到达后替换预测点 → 笔画通过多缓冲模式持久化。这是目前 Android 上手写/绘图类应用的最佳实践。


## 输入延迟在 Perfetto 中的分析方法

### Perfetto android.input 模块

Perfetto stdlib 的 `android_input_events` 表把输入事件拆成五段 latency。官方文档还特别说明，input delivery 是 socket based，每个事件从系统发出后都要等待 App ACK，因此 `dispatch_latency_dur`、`handling_latency_dur`、`ack_latency_dur`、`total_latency_dur` 四段都能独立量化。

[已验证: perfetto.dev/docs/analysis/stdlib-docs#android_input_events]

| 字段 | 含义 |
|------|------|
| `dispatch_latency_dur` | InputDispatcher 发送事件到 App 接收事件 |
| `handling_latency_dur` | App 接收事件到 App 处理完毕并发送 ACK |
| `ack_latency_dur` | App 发送 ACK 到 InputDispatcher 收到 ACK |
| `total_latency_dur` | dispatch 到 ACK 的完整往返时间 |
| `end_to_end_latency_dur` | InputReader 读取事件到帧真正 present 的端到端延迟 |

前四个维度覆盖了 InputDispatcher 和 App 之间的 socket 往返。`end_to_end_latency_dur` 再把视角往前拉到 InputReader，往后拉到帧上屏。官方文档已经写明，如果输入事件没有关联到 frame event，这个字段就是 `NULL`。

### end_to_end_latency_dur 为什么会是 NULL

这里不能只看 Perfetto 表结构，还要回到 AOSP。`ViewRootImpl` 在启用 input latency tracking 且 `ThreadedRenderer` 存在时，会创建 `InputMetricsListener` 和 `HardwareRendererObserver`。`onFrameMetricsAvailable()` 会读取 `FrameMetrics.Index.INPUT_EVENT_ID`、`DISPLAY_PRESENT_TIME` 和 `GPU_COMPLETED`，然后通过 `mInputEventReceiver.reportTimeline(inputEventId, gpuCompletedTime, presentTime)` 把输入事件和实际显示时间绑起来。

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1
final class InputMetricsListener
        implements HardwareRendererObserver.OnFrameMetricsAvailableListener {
    @Override
    public void onFrameMetricsAvailable(int dropCountSinceLastInvocation) {
        final int inputEventId = (int) data[FrameMetrics.Index.INPUT_EVENT_ID];
        if (inputEventId == INVALID_INPUT_EVENT_ID) {
            return;
        }
        final long presentTime = data[FrameMetrics.Index.DISPLAY_PRESENT_TIME];
        if (presentTime <= 0) {
            return;
        }
        final long gpuCompletedTime = data[FrameMetrics.Index.GPU_COMPLETED];
        mInputEventReceiver.reportTimeline(inputEventId, gpuCompletedTime, presentTime);
    }
}
```

这段代码告诉我们，`end_to_end_latency_dur` 至少依赖四个条件：

1. 这次输入事件拿到了有效的 `android_input_id` / `INPUT_EVENT_ID`
2. 这次输入最终关联到一帧真实渲染
3. `DISPLAY_PRESENT_TIME` 可用，也就是系统拿到了 frame present 时间
4. App 走的是带 `ThreadedRenderer` 的渲染路径，输入 metrics 能被上报

如果事件只触发了逻辑处理，没有形成可呈现的帧，或者 trace 没有采到 frame metrics，对应的 `end_to_end_latency_dur` 就会是 `NULL`。这不是 SQL 写错了，而是关联路径还没有闭合。

[已验证: AOSP android-16.0.0_r1, ViewRootImpl.java + perfetto stdlib docs]

### SQL 实战查询

通过 `INCLUDE PERFETTO MODULE android.input` 引入模块，结合 `thread` 和 `process` 表可以定位到具体线程和进程：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  CAST(input.ts / 1000000.0) AS timestamp_ms,
  input.thread_name AS receiving_thread,
  process.name AS receiving_process,
  CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_ms,
  CAST(input.handling_latency_dur / 1000000.0) AS handling_ms,
  CAST(input.ack_latency_dur / 1000000.0) AS ack_ms,
  CAST(input.total_latency_dur / 1000000.0) AS total_ms,
  CAST(input.end_to_end_latency_dur / 1000000.0) AS e2e_ms,
  input.android_input_id
FROM android_input_events AS input
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE input.total_latency_dur IS NOT NULL
ORDER BY input.total_latency_dur DESC
LIMIT 100;
```

[来源: perfetto.dev/docs/analysis/stdlib-docs#android_input_events]

这个查询按 `total_latency_dur` 降序排列，能先把最慢的事件抓出来。解读时建议把 `total_ms` 和 `e2e_ms` 分开看：

- `dispatch_ms` 高，说明 system_server 到 App 的投递慢，优先看 InputDispatcher 线程调度和目标进程唤醒
- `handling_ms` 高，说明 App 主线程或输入处理路径本身耗时长
- `ack_ms` 高，说明 App 已经处理完事件，但 ACK 回传晚，常见于主线程回切、调度延迟或进程负载高
- `e2e_ms` 为 `NULL`，先确认有没有 frame present 时间，不要直接把它当成 trace 异常

### 在 Perfetto UI 中怎么把证据对应起来

如果想把同一条输入事件从 InputReader 一直追到屏幕，最稳妥的做法是拿 `android_input_id` 做主线，再去对照以下轨道：

- `system_server` 中的 InputReader / InputDispatcher 线程调度状态
- App 主线程上的 `DeliverInputEvent` 或输入相关 slice
- `Choreographer#doFrame` 和 FrameTimeline
- 最终帧的 present 时间

这样我们就能把“事件进了 App”“App 开始画了”“帧真的上屏了”三件事拆开看，而不是把它们糊成一个大延迟数字。

[图：同一条 `android_input_id` 在 Perfetto 中的对照轨道，依次标出 InputReader、InputDispatcher、DeliverInputEvent、Choreographer#doFrame、FrameTimeline]

[待补充：真实 Trace 截图]


## 降低输入延迟的优化策略

### 系统层面

**1. 线程调度优化**

正如前面魅族团队的案例所示，InputReader 和 InputDispatcher 的调度优先级对输入延迟影响很大。在 CPU 负载高的场景（如游戏），如果这两个线程不能及时获得 CPU 时间，即使触控 IC 按时报点，系统也来不及处理。

优化方向：
- 提高 InputReader/InputDispatcher 线程的调度优先级
- 在性能关键场景将它们绑定到大核
- 使用 `sched_setaffinity` 避免线程在不同核心间迁移带来的 cache miss

[来源: Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

**2. 触控采样率与报点率**

提高触控 IC 的报点频率可以减少硬件采样延迟。从 120Hz 提升到 240Hz，最坏情况的采样延迟从 8.33ms 降到 4.17ms。但代价是功耗增加和驱动层的事件密度翻倍，需要在性能和功耗之间做场景化的权衡。

**3. OEM 显示管线调优**

部分厂商文章会讨论调整 VSYNC-app 和 VSYNC-sf 的 offset、buffer release 时机，或者本地显示管线的唤醒策略，以减少“刚好错过一个 VSync”后的额外等待。这类做法确实可能改善个别机型的触控到显示延迟，但公开 AOSP 主线资料并没有把“主动唤醒 SurfaceFlinger 立即处理”暴露成通用 API。

更稳妥的写法是，把它归类为 OEM 定制经验，而不是所有 Android 设备都默认具备的系统能力。如果后续要保留更强的结论，需要补出对应机型、版本和源码路径。

[来源: Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

### App 层面

**1. 减轻主线程的输入处理负担**

Choreographer 的回调顺序（INPUT → ANIMATION → TRAVERSAL）意味着 `CALLBACK_INPUT` 的处理时间直接影响后续 measure/layout/draw 的时间预算。如果 `View.onTouchEvent()` 中做了 IO 操作、数据库查询或复杂计算，会压缩渲染时间导致掉帧。

解决方案是将重逻辑从 `onTouchEvent()` 中移出，只保留状态更新和 `invalidate()` 调用，把耗时操作放到异步线程。

**2. 使用 MotionEventPredictor 和前缓冲渲染**

对于笔迹、绘图类应用，接入 MotionEventPredictor 和低延迟图形库是目前最有效的延迟优化手段。接入成本低（Jetpack 库），效果明显，尤其是配合手写笔使用时。

**3. batched input 与 unbuffered dispatch 的取舍**

大多数应用默认走 batched input，让系统把一批 motion event 放到 `CALLBACK_INPUT` 一起消费。这样能配合 resampling 降低抖动，并减少主线程被高频 move event 打满的概率。只有笔迹、绘图、部分低延迟交互，才值得调用 `View.requestUnbufferedDispatch(MotionEvent)`，让 `onBatchedInputEventPending()` 直接走 `consumeBatchedInputEvents(-1)` 的即时路径。

AOSP `View.java` 的文档也明确提醒，这个 API 不适合大多数应用，副作用包括 jittery scrolls 和失去 system resampling。这里真正的取舍，不是“同步/异步 InputChannel 模式”二选一，而是“是否为特定输入流关闭 batching，换更低的等待时间”。

[已验证: AOSP android-16.0.0_r1, View.java + ViewRootImpl.java]

### 游戏模式（Game Mode）的输入优化

Game Mode 和 Game Mode Interventions 更接近系统为游戏提供的性能、功耗和画质策略入口，例如调整目标帧率、backbuffer 大小或处理器资源使用。当前公开文档没有给出“GameManagerService 直接通知 InputDispatcher 优先处理输入事件”的官方调用关系。

这里更稳妥的结论是，Game Mode 可能通过整体调度预算间接改善输入到显示延迟，但它不是 InputDispatcher 专用 low-latency API，也不能替代 App 自己做好主线程和渲染路径优化。

[来源: developer.android.com/games/optimize/performance#adpf + Game Mode Interventions 文档]

## 与其他机制的关系

输入延迟不是孤立存在的，它和渲染管线中的多个环节紧密关联：

- **VSync 机制**（§2.3）：VSYNC offset 直接决定了 App 渲染和 SurfaceFlinger 合成的时间差，是减少端到端延迟的关键
- **Choreographer**（§2.4）：输入事件在 doFrame 中被优先处理，但处理时间会影响后续渲染阶段
- **BufferQueue**（§2.13）：前缓冲渲染绕过了 BufferQueue 的多缓冲交换机制
- **SurfaceFlinger**（§2.6）：合成阶段是端到端延迟的末端阶段
- **触摸响应分析**（§3.2）：§3.2 从触摸采样率和 Batching 的角度分析性能，本节聚焦延迟量化和预测补偿
- **ANR 机制**（§9.1）：InputDispatcher 的 5 秒超时是输入 ANR 的触发条件


## 常见问题与误区

**误区 1："提高屏幕刷新率就能解决输入延迟问题"**

提高刷新率确实缩短了 VSync 周期（120Hz 下 8.33ms vs 60Hz 下 16.6ms），减少了 VSync 等待时间和 SurfaceFlinger 合成周期。但如果瓶颈在 App 主线程的处理耗时（比如 onDraw 超过 8ms），更高的刷新率只会让掉帧更频繁，因为每帧的时间预算更紧张了。

**误区 2："触控预测会让画面更流畅"**

MotionEventPredictor 的预测是基于历史数据的数学外推，在快速方向变化（如画"V"字形）时可能预测错误，导致画面出现短暂的抖动。它的价值在于降低感知延迟，而不是提升流畅度。在滑动列表等场景中，预测的收益不如在笔迹类应用中明显。

**误区 3："前缓冲渲染适合所有场景"**

前缓冲渲染只适合局部更新（笔画绘制、光标移动）。如果用于全屏重绘（如游戏画面），会因为读写同一个 buffer 而导致画面撕裂。这也是为什么 Jetpack 的低延迟图形库设计为"前缓冲用于笔画，抬笔后切回多缓冲"的原因。

**误区 4："输入延迟高一定是 App 的锅"**

按上面的六阶段拆解，延迟可能发生在任何一个环节。在魅族团队的案例中，问题出在 InputReader/InputDispatcher 的线程调度，和 App 完全无关。分析输入延迟时，一定要看整个路径，而不是只盯着 App 主线程。


## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/inputflinger/reader/` — InputReader 实现
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — InputDispatcher 实现及 iq/oq/wq 追踪
  - `frameworks/base/core/java/android/view/Choreographer.java` — doFrame 回调顺序
  - `frameworks/base/core/java/android/view/ViewRootImpl.java` — enqueueInputEvent / deliverInputEvent
- 官方文档：
  - [source.android.com/docs/core/interaction/input](https://source.android.com/docs/core/interaction/input)
  - [developer.android.com/reference/androidx/input/motionprediction/MotionEventPredictor](https://developer.android.com/reference/androidx/input/motionprediction/MotionEventPredictor)
  - [developer.android.com/develop/ui/views/graphics/low-latency-graphics](https://developer.android.com/develop/ui/views/graphics/low-latency-graphics)
  - [perfetto.dev/docs/analysis/sql-tables/android-input](https://perfetto.dev/docs/analysis/sql-tables/android-input)
- 博客：
  - [魅族内核团队：Android Input 调试与优化](https://kernel.meizu.com/2023/10/27/Android-inputTuning-and-Optimizing/)
  - [性能优化必学基础：input流程与systrace结合剖析](https://mp.weixin.qq.com/s?biz=MzkzOTQ4NDUyNg==&mid=2247490978)
