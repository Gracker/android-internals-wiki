---
title: "第 3 章：输入系统"
chapter: "3.0"
section: "3.0"
status: "ready-for-review"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1; kernel android17-6.18-2026-06_r6; consolidated ch03 structure 3.1-3.6"
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
pipeline_stage: "ready-for-review"
task6_state: "pending-verification"
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
last_consolidated_at: '2026-08-24'
consolidation_note: 第二轮逐篇审阅后收敛为 6 篇，合并同一责任链中的总览、机制、版本增量、观测与案例，并统一连续编号。
---

# 第 3 章：输入系统

“点了没反应”“滑动不跟手”“返回动画晚一拍”可能发生在输入采集、目标选择、应用消费、渲染或显示中的任一阶段。帧率正常也不能证明输入事件及时到达应用。分析这类问题时，需要把输入事件与产生视觉反馈的那一帧放到同一条时间线上。

源码锚点如下：

- 系统平台：Android 17（API 37），源码标签为 `android-17.0.0_r1`；
- 内核：`android17-6.18-2026-06_r6`；
- Android 10—17 的演进用于解释输入分类、系统手势、Predictive Back（预测性返回）、Rust 过滤器和动态刷新率；当前对象与调用名以 Android 17 的固定源码标签为准。

## 1. 从输入设备到应用窗口

Android 17 的主要分发路径如下；`evdev` 是 Linux 内核向用户空间暴露输入事件的设备接口，后续对象均位于 Android 系统或应用侧：

`evdev → EventHub → InputReader → InputListener 各处理阶段 → InputDispatcher → InputChannel 与 InputTransport → InputEventReceiver → ViewRootImpl`

其中每一段回答的问题不同：

| 区间 | Android 17 对象 | 主要职责 | 常用证据 |
|---|---|---|---|
| 内核 → 原生读取端 | evdev、`EventHub`、`InputReader`、输入设备映射器 | 发现设备、读取原始事件、转换协议并生成 Android 输入事件 | 内核输入跟踪、事件时间、读取时间、读取端跟踪 |
| 原生监听链 | `UnwantedInteractionBlocker`、`InputFilter`、`PointerChoreographer`、`InputProcessor` | 处理手掌与触控笔冲突、辅助功能按键过滤、指针显示状态和动作分类 | InputFlinger 跟踪、功能开关、分类结果 |
| 目标选择与投递 | `InputDispatcher`、`InputChannel`、`InputPublisher` | 选择焦点窗口或触摸窗口，管理连接队列、投递、超时与丢弃 | InputDispatcher 跟踪、`dumpsys`、ANR 或丢弃原因 |
| 应用接收 | `InputConsumer`、`InputEventReceiver`、`ViewRootImpl` | 读取消息、依次经过输入处理阶段，处理批量输入并发送完成信号 | 应用主线程、输入执行片段、回调 |
| 视觉反馈 | `Choreographer`、HWUI、SurfaceFlinger、HWC | 更新状态、提交缓冲区、锁存图层并呈现到显示设备 | FrameTimeline、缓冲区、图层、栅栏与呈现时间 |

Android 17 的 [`InputManager.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputManager.cpp) 明确列出当前监听链顺序：

`InputReader → UnwantedInteractionBlocker → InputFilter → PointerChoreographer → InputProcessor → Metrics 与 InteractionReporter → InputDispatcher`

指标收集器（Metrics collector）和交互报告器（interaction reporter）可能因构建配置或服务条件而省略。旧资料中的 `classifier/InputClassifier.cpp` 在 `android-17.0.0_r1` 中不存在；动作分类位于 `InputProcessor.cpp`，手掌误触拒绝位于 `UnwantedInteractionBlocker.cpp`。两者职责不同，不能合并概括为“所有输入都经过 AI 分类”。

## 2. 六个时间边界

端到端输入延迟至少要标出六个时刻：

1. 硬件或内核产生输入事件；
2. `EventHub` 和 `InputReader` 读取并转换事件；
3. `InputDispatcher` 为事件选择目标并发出消息；
4. 目标进程中的 `InputConsumer` 和 `InputEventReceiver` 收到事件；
5. 应用处理事件并提交包含视觉变化的缓冲区；
6. SurfaceFlinger 和 HWC 完成本轮显示呈现。

`MotionEvent.getEventTime()` 接近设备产生事件的时间，不等于应用收到事件的时间。业务回调结束也不代表画面已经显示。只测量事件时间到回调时间的差值，得到的是“输入到应用”延迟；端到端的“触摸到显示”延迟还要包含应用渲染、缓冲区提交、SurfaceFlinger 合成与显示呈现。

触摸 `MOVE` 事件可能批量传输，并在接近 VSYNC 时由 `ViewRootImpl` 消费。批处理（batching）可以减少线程唤醒和 IPC 压力，但也会改变单个采样点的消费时刻。分析重采样和预测坐标时，还要区分原始采样时间、预测目标时间和画面呈现时间。

## 3. Android 17 的组件边界

### 3.1 动作分类与手掌误触拒绝

`InputProcessor` 可以连接输入处理器 HAL，维护动作事件队列并更新分类结果。它只处理满足输入来源、配置和服务条件的事件。`UnwantedInteractionBlocker` 负责另一组问题，包括手掌误触拒绝，以及触控笔与手指触摸之间的冲突。

评审输入分类相关论述时，应写明具体组件、输入来源、功能开关、HAL 是否存在，以及输出怎样影响下游。仅凭系统版本，不能推断目标设备已经启用某个模型。

### 3.2 Rust `InputFilter`

Android 17 的 C++ `InputFilter` 通过 AIDL 和 FFI（外部函数接口）调用 Rust 实现的辅助功能过滤器。当前公开源码包含防重复按键（bounce keys）、慢速键（slow keys）和粘滞键（sticky keys）等配置；动作事件仍由 C++ 包装层继续传给下游监听器。

因此，Rust 的使用范围应限定到这些具体过滤功能。`EventHub`、`InputReader` 与 `InputDispatcher` 仍位于 C++ 主路径上。

### 3.3 InputDispatcher

`InputDispatcher` 管理进入系统的事件、目标窗口、连接、等待队列、完成信号、丢弃与超时。出现输入 ANR 或事件积压时，应区分以下情况：

- 尚未找到焦点窗口或触摸目标窗口；
- 目标连接尚未就绪；
- 事件已经发出，但应用没有按期返回完成信号；
- 策略、安全条件或过期（stale）判定要求丢弃事件；
- 系统线程没有及时获得 CPU。

若把这些状态统称为“`InputDispatcher` 卡住”，就无法判断真正负责的组件。

### 3.4 Predictive Back

Predictive Back 跨越输入策略、应用返回回调、WindowManager 转场、SystemUI 动画和 SurfaceControl。手势开始、返回回调、动画事务与显示呈现是彼此独立的事件。

`OnBackInvokedDispatcher` 的回调优先级、系统动画目标与旧 `onBackPressed()` 兼容路径，需要结合目标 SDK、manifest 中的显式启用配置和平台版本核对。动画卡顿不能只检查 `InputDispatcher`。

### 3.5 ARR 与输入延迟

Adaptive Refresh Rate（自适应刷新率，ARR）位于显示时序和刷新率策略侧，不会替换 `InputReader` 或 `InputDispatcher`。ARR 会改变相邻 VSYNC 之间的间隔，因此端到端测量不能固定假设每帧都是 16.67 ms 或 8.33 ms。

分析高刷新率设备上的触控问题时，要同时记录输入采样节奏、应用帧调度、实际 VSYNC 周期、活动显示模式和呈现时间。提高刷新率也无法修复焦点错误、应用主线程阻塞或连接背压；背压是指下游处理不及时，导致队列逐渐占满并反向阻塞上游。

## 4. 内容索引

- [3.1 Input 分发、拦截与安全边界](01-input-dispatch-interception-security.md)
- [3.2 触摸延迟、预测与低延迟渲染](02-touch-performance.md)
- [3.3 系统手势导航与 Predictive Back](03-gesture-navigation-predictive-back.md)
- [3.4 手势识别算法与性能优化](04-gesture-recognition-performance.md)
- [3.5 InputMethodManager 与软键盘性能](05-input-method-manager-performance.md)
- [3.6 键盘、鼠标与指针输入性能 — 桌面模式交互管线](06-keyboard-mouse-pointer-input-performance.md)

## 5. 按现象选择阅读路径

| 现象 | 阅读顺序 | 先确认的证据 |
|---|---|---|
| 点击无响应 | 3.1 | 设备事件、目标窗口、连接、丢弃或超时、拦截或注入策略 |
| 滑动不跟手 | 3.2 → 3.4 | 采样、批处理与重采样、识别与消费、应用帧、呈现时间 |
| 输入 ANR、事件过期或丢弃 | 3.1 | 输入、输出和等待队列，完成信号，ANR 或丢弃原因 |
| 返回动画晚或错位 | 3.3 → 第 2 章渲染 | 返回回调、转场、SurfaceControl 事务、呈现时间 |
| IME 弹出慢 | 3.5 → 3.1 → 第 2 章 WindowInsets | IME 目标、会话、显示请求、Insets 动画、呈现时间 |
| 高刷新率下触控节奏不稳 | 3.2 → 第 2 章 ARR | 输入节奏、交互升频、VSYNC 周期、活动模式、帧生成与呈现 |
| 鼠标悬停、键盘过滤或焦点异常 | 3.6 → 3.1 | 设备与来源、Rust 过滤器、显示器、焦点、指针捕获、目标窗口 |

渲染与显示阶段可对照 [第 2 章 VSync](../ch02-rendering/03-vsync-choreographer-sf-scheduling.md)、[Choreographer](../ch02-rendering/03-vsync-choreographer-sf-scheduling.md)、[Sync Fence](../ch02-rendering/08-bufferqueue-gralloc-sync-fence.md) 和 [Adaptive Refresh Rate](../ch02-rendering/02-framerate-refresh-display-mode.md)。

## 6. Perfetto 与现场信息

采集输入问题时，至少保存：

- 设备型号、构建指纹、Android API 级别、刷新率与活动显示模式；
- 输入设备 ID、来源、显示器 ID、事件类型与事件时间；
- 目标窗口、焦点、触摸区域、`InputChannel` 和连接；
- `InputReader`、`InputDispatcher`、应用主线程与 `RenderThread` 的调度状态；
- FrameTimeline、目标图层、缓冲区提交、锁存与呈现时间；
- 问题发生时的旋转、窗口模式、IME、系统手势和辅助功能配置。

Perfetto 中没有出现某个执行片段（slice），不能直接证明相应阶段没有工作。InputFlinger 跟踪类别、应用插桩、FrameTimeline 和厂商输入或显示跟踪是否可用，取决于系统构建、数据源配置与权限。

## 7. 固定源码入口

- [`InputManager.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputManager.cpp)：Android 17 监听链与组件装配；
- [`EventHub.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/reader/EventHub.cpp)、[`InputReader.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/reader/InputReader.cpp)：设备读取与事件转换；
- [`UnwantedInteractionBlocker.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/UnwantedInteractionBlocker.cpp)、[`InputProcessor.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputProcessor.cpp)：手掌与触控笔冲突、动作分类；
- [`InputFilter.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/InputFilter.cpp)、[`rust/`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/rust/)：C++ 包装层与 Rust 过滤器；
- [`InputDispatcher.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)、[`InputTransport.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputTransport.cpp)：目标选择、连接与应用传输；
- [`InputEventReceiver.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/InputEventReceiver.java)、[`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：应用接收与输入处理阶段；
- [`drivers/input/input.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/input/input.c)、[`input-event-codes.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/input-event-codes.h)：内核输入核心与用户空间 API（UAPI）。

这些入口用于确认公共调用关系。触控固件、采样策略、手掌识别模型、调度器调优和显示扫描输出可能由设备厂商实现，因此设备级结论还要补充相应源码或运行时证据。
