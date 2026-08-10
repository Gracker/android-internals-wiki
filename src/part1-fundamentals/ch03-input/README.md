---
title: "第 3 章:输入系统"
chapter: "3.0"
section: "3.0"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-20"
last_verified_against: "AOSP android-17.0.0_r1; ch03 finalized subchapters 3.1/3.3/3.4/3.5/3.8/3.10/3.11; Android Developers Predictive Back / MotionPredictor / ARR docs"
confidence: "high"
tags:
  - input
  - inputflinger
  - touch
  - input-latency
  - predictive-back
  - arr
related_chapters:
  - "3.1"
  - "3.2"
  - "3.3"
  - "3.4"
  - "3.5"
  - "3.6"
  - "3.7"
  - "3.8"
  - "3.9"
  - "3.10"
  - "3.11"
pipeline_stage: "finalized"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-09T10:55:26+08:00"
task6_result: pass-light-edit
task9_result: pass-tech-review
last_task9_at: "2026-07-20T15:05:34+08:00"
task9_reviewed_by: hermes-aiw-review-finalize-apply
task9_reviewed_date: "2026-07-20"
last_task6_at: "2026-07-20T15:05:34+08:00"
last_task6_review_log: "logs/review/2026-05-09-04-review.md"
task2b_rework_notes: "2026-06-09 Task2B main:补全缺失子章节 3.7-3.11 列表与阅读建议;修复 last_verified_against 源码版本锚点;合并重复延伸阅读;修复 InputClassifier 后括号无空格;响应 deep-review 2026-05-10-03 P1 反压/背压/优先级/异步回调覆盖缺口。送 Task6 复审。"
task6_review_notes: "2026-05-09 Task6 04:05:Task2B 修复后写作复审;修正验证锚点路径格式,L1/L2 通过;无新增 L3/L4 回炉项,送 Task9 复审。"
last_review_finalize_at: "2026-07-20T15:05:34+08:00"
last_review_finalize_run_id: "20260720-150534-9a0187cb"
review_finalize_notes: "2026-07-20 Hermes AIW review/finalize: 按 android-17.0.0_r1 与已 finalized 的 ch03 子章节复核总览;收窄 InputFlinger Rust、Predictive Back、DeliQueue 和 MotionPredictor 表述后晋升 finalized。"
reviewed_by: hermes-aiw-review-finalize-apply
reviewed_date: "2026-07-20"
---

# 第 3 章：输入系统

“点了没反应”“滑动不跟手”“返回动画晚一拍”可能发生在输入采集、目标选择、应用消费、渲染或显示中的任一区间。帧率正常也不能证明输入及时到达应用。分析这类问题，要把输入事件与产生视觉反馈的那一帧对齐。

源码锚点如下：

- platform：Android 17 / API 37 / `android-17.0.0_r1`；
- kernel：`android17-6.18-2026-06_r6`；
- Android 10—17 的演进用于解释分类、系统手势、Predictive Back、Rust filter 和动态刷新率；当前对象与调用名以 Android 17 固定 tag 为准。

## 1. 从 input device 到应用窗口

Android 17 的主分发路径可以写成：

`evdev → EventHub → InputReader → InputListener stages → InputDispatcher → InputChannel/InputTransport → InputEventReceiver → ViewRootImpl`

其中每一段回答的问题不同：

| 区间 | Android 17 对象 | 主要职责 | 常用证据 |
|---|---|---|---|
| Kernel → native reader | evdev、`EventHub`、`InputReader`、reader mapper | 设备发现、raw event 读取、协议映射与 Android event 生成 | kernel/input trace、event time、read time、reader trace |
| Native listener chain | `UnwantedInteractionBlocker`、`InputFilter`、`PointerChoreographer`、`InputProcessor` | 手掌/触控笔冲突、辅助功能按键过滤、指针显示状态、motion classification | InputFlinger trace、feature flag、classification |
| 目标选择与投递 | `InputDispatcher`、`InputChannel`、`InputPublisher` | 焦点/touched window 选择、connection queue、dispatch、timeout 与 drop | dispatcher trace、dumpsys、ANR/drop reason |
| 应用接收 | `InputConsumer`、`InputEventReceiver`、`ViewRootImpl` | 读取消息、输入 stage、batched input 与 finish signal | 应用 main thread、input slice、callback |
| 视觉反馈 | `Choreographer`、HWUI、SurfaceFlinger、HWC | 状态更新、buffer 提交、latch 与 present | FrameTimeline、buffer/layer/fence、present |

Android 17 的 [`InputManager.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputManager.cpp) 明列当前 listener 顺序：

`InputReader → UnwantedInteractionBlocker → InputFilter → PointerChoreographer → InputProcessor → Metrics/InteractionReporter → InputDispatcher`

Metrics collector 和 interaction reporter 可按构建配置或服务条件省略。旧资料中的 `classifier/InputClassifier.cpp` 在 `android-17.0.0_r1` 不存在；motion classification 位于 `InputProcessor.cpp`，手掌拒绝位于 `UnwantedInteractionBlocker.cpp`。两者也不能合并成“所有输入都经过 AI 分类”。

## 2. 六个时间边界

端到端输入延迟至少要标出六个时刻：

1. 硬件或 kernel 产生 event；
2. EventHub/InputReader 读取并转换 event；
3. InputDispatcher 为 event 选择目标并发出消息；
4. 目标进程的 InputConsumer/InputEventReceiver 收到 event；
5. 应用处理 event 并提交带有视觉变化的 buffer；
6. SurfaceFlinger/HWC 完成本轮 display present。

`MotionEvent.getEventTime()` 接近设备事件时间，不等于应用接收时间。业务 callback 的结束也不等于画面已经显示。只测 event time 到 callback 的差值，得到的是输入到应用的延迟；端到端“触摸到显示”还要补应用渲染、buffer、SurfaceFlinger 与 present。

触摸 MOVE 可能批量传输，并在接近 VSync 时由 `ViewRootImpl` 消费。batching 可以减少唤醒和 IPC 压力，也会改变单个 sample 的消费时刻。重采样和预测产生的坐标还要区分原始 sample time、预测目标时间和呈现时间。

## 3. Android 17 的组件边界

### 3.1 Motion classification 与手掌拒绝

`InputProcessor` 可连接 input processor HAL，维护 motion event 队列并更新 classification。它只处理满足来源、配置与服务条件的事件。`UnwantedInteractionBlocker` 负责另一组问题，包括 palm rejection 和 stylus/touch 冲突。

评审分类论述时，应写明组件、输入来源、feature flag、HAL 是否存在及输出如何影响下游。仅凭系统版本不能推断目标设备启用了某个模型。

### 3.2 Rust InputFilter

Android 17 的 C++ `InputFilter` 通过 AIDL/FFI 使用 Rust 实现辅助功能过滤。当前公开源码可看到 bounce keys、slow keys 与 sticky keys 等配置；motion event 在 C++ wrapper 中继续传给下游 listener。

因此，Rust 的范围应限定到具体 filter 功能。`EventHub`、`InputReader` 与 `InputDispatcher` 仍是 C++ 主线。

### 3.3 InputDispatcher

InputDispatcher 管理 inbound event、目标窗口、connection、wait queue、finish signal、drop 与 timeout。出现输入 ANR 或事件积压时，应区分：

- 尚未找到焦点或 touched window；
- 目标 connection 尚未就绪；
- 事件已经发送，应用未按期 finish；
- policy、安全条件或 stale 判定要求丢弃；
- 系统线程没有及时获得 CPU。

把这些状态统称为“InputDispatcher 卡住”会丢失责任对象。

### 3.4 Predictive Back

Predictive Back 跨越输入策略、应用 callback、WindowManager transition、SystemUI animation 与 SurfaceControl。手势开始、back callback、动画 transaction 和 display present 是独立事件。

`OnBackInvokedDispatcher` 的 callback 优先级、系统动画目标与旧 `onBackPressed()` 兼容路径要按 target SDK、manifest opt-in 和平台版本核对。动画卡顿不能只查 InputDispatcher。

### 3.5 ARR 与输入延迟

Adaptive Refresh Rate 位于显示时序与刷新率策略侧，没有替换 InputReader/InputDispatcher。ARR 会改变相邻 VSync 的间隔，因此端到端测量不能固定假设 16.67 ms 或 8.33 ms。

高刷设备上的触控分析要同时记录 input sample cadence、应用帧调度、实际 VSync period、active mode 和 present。刷新率提高也无法修复焦点错误、应用主线程阻塞或 connection backpressure。

## 4. 内容索引

### 4.1 分发与端到端延迟

- [3.1 Input 事件分发全流程](01-input-dispatch.md)：从 kernel/evdev、EventHub、InputReader 到 InputDispatcher 和应用窗口。
- [3.2 触摸响应性能](02-touch-performance.md)：采样、batching、应用消费、帧调度与视觉反馈。
- [3.9 端到端输入延迟预算](09-input-latency-budget-perception.md)：建立可测量的阶段预算，并区分设备、系统、应用和显示成本。

### 4.2 手势、预测与返回

- [3.3 手势导航与系统交互](03-gesture-navigation.md)：系统手势截获、导航策略与应用窗口之间的边界。
- [3.4 输入延迟与预测输入](04-input-latency-prediction.md)：MotionPredictor、resampling、prediction horizon 与 trace 证据。
- [3.6 手势识别算法](06-gesture-recognition-performance.md)：GestureDetector、VelocityTracker、多点手势与算法成本。
- [3.12 Predictive Back](12-predictive-back-system-architecture.md)：back callback、WindowManager、SystemUI 动画和 SurfaceControl 的协作。

### 4.3 路由、安全、回压与丢弃

- [3.5 输入拦截与安全](05-input-interception-security.md)：焦点、窗口遮挡、monitor、filter、注入权限与安全策略。
- [3.7 InputDispatcher 回压](07-inputdispatcher-backpressure.md)：inbound/connection queue、finish signal、无响应窗口与 ANR。
- [3.10 stale event 判定](10-inputdispatcher-stale-event.md)：过期事件、drop reason、timeout 与版本边界。

### 4.4 Filter、IME 与桌面输入

- [3.8 InputFlinger Rust 与 ARR](08-inputflinger-rust-arr.md)：Rust filter 的实现范围，以及动态刷新率对测量口径的影响。
- [3.11 InputMethodManager](11-input-method-manager-performance.md)：IME client/session、焦点、show/hide、Insets 与键盘显示性能。
- [3.13 键盘、鼠标与指针输入](13-keyboard-mouse-pointer-input-performance.md)：桌面模式下的 hover、scroll、cursor、capture、focus 与多 display。
- [3.14 Input 系统参考文献](参考资料.md)：Android 17 与 kernel 固定 tag 的源码索引。

## 5. 按现象选择阅读路径

| 现象 | 阅读顺序 | 先确认的证据 |
|---|---|---|
| 点击无响应 | 3.1 → 3.5 → 3.7 → 3.10 | device event、target window、connection、drop/timeout |
| 滑动不跟手 | 3.2 → 3.4 → 3.9 | sample、batch、resample/prediction、应用帧、present |
| 输入 ANR | 3.1 → 3.7 → 3.10 | dispatch start、wait queue、finish signal、ANR reason |
| 返回动画晚或错位 | 3.3 → 3.12 → 第 2 章渲染 | back callback、transition、SurfaceControl transaction、present |
| IME 弹出慢 | 3.11 → 3.5 → 第 2 章 WindowInsets | IME target、session、show request、Insets animation、present |
| 高刷下触控节奏不稳 | 3.2 → 3.4 → 3.8 → 第 2 章 ARR | input cadence、VSync period、active mode、frame/present |
| 鼠标 hover 或键盘焦点异常 | 3.13 → 3.5 → 3.1 | device/source、display、focus、pointer capture、target |

渲染与显示阶段可对照[第 2 章 VSync](../ch02-rendering/03-vsync.md)、[Choreographer](../ch02-rendering/04-choreographer.md)、[Sync Fence](../ch02-rendering/16-sync-fence.md)和[Adaptive Refresh Rate](../ch02-rendering/18-adaptive-refresh-rate.md)。

## 6. Perfetto 与现场信息

采集输入问题时，至少保存：

- 设备、build fingerprint、Android/API、刷新率与 active display mode；
- input device id、source、display id、event type 与 event time；
- 目标 window、focus、touch region、InputChannel/connection；
- InputReader、InputDispatcher、应用 main thread 与 RenderThread 调度状态；
- FrameTimeline、目标 layer、buffer 提交、latch 与 present；
- 问题发生时的旋转、窗口模式、IME、系统手势和辅助功能配置。

Perfetto 中没有某个 slice，不能直接证明该阶段没有工作。InputFlinger trace category、应用 tracing、FrameTimeline 和厂商 input/display trace 的可用性取决于 build、数据源配置与权限。

## 7. 固定源码入口

- [`InputManager.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputManager.cpp)：Android 17 listener chain 与组件装配；
- [`EventHub.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/reader/EventHub.cpp)、[`InputReader.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/reader/InputReader.cpp)：设备读取与事件转换；
- [`UnwantedInteractionBlocker.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/UnwantedInteractionBlocker.cpp)、[`InputProcessor.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputProcessor.cpp)：手掌/触控笔冲突与 motion classification；
- [`InputFilter.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputFilter.cpp)、[`rust/`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/rust/)：C++ wrapper 与 Rust filter；
- [`InputDispatcher.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)、[`InputTransport.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputTransport.cpp)：目标选择、connection 与应用传输；
- [`InputEventReceiver.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/InputEventReceiver.java)、[`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：应用接收与 input stage；
- [`drivers/input/input.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/input/input.c)、[`input-event-codes.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/input-event-codes.h)：kernel input core 与 UAPI。

这些入口用于确认公共调用关系。触控固件、采样策略、手掌模型、scheduler tuning 和 display scanout 可能由设备厂商实现，设备级结论还要补对应源码或运行时证据。
