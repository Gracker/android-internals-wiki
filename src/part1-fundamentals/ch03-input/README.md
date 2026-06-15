---
title: "第 3 章:输入系统"
chapter: "3.0"
section: "3.0"
status: "ready-for-review"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-09"
last_verified_against: "AOSP android-16.0.0_r4 frameworks/native/services/inputflinger、Android 15 ARR / Predictive Back 文档、ch03 子章节"
confidence: "medium"
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
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-09T10:55:26+08:00"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-05-09
task9_result: needs-rework
last_task9_at: "2026-04-28T14:33:59+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-04-28"
last_task6_at: "2026-05-09T04:05:00+08:00"
last_task6_review_log: "logs/review/2026-05-09-04-review.md"
task2b_rework_notes: "2026-06-09 Task2B main:补全缺失子章节 3.7-3.11 列表与阅读建议;修复 last_verified_against 源码版本锚点;合并重复延伸阅读;修复 InputClassifier 后括号无空格;响应 deep-review 2026-05-10-03 P1 反压/背压/优先级/异步回调覆盖缺口。送 Task6 复审。"
task6_review_notes: "2026-05-09 Task6 04:05:Task2B 修复后写作复审;修正验证锚点路径格式,L1/L2 通过;无新增 L3/L4 回炉项,送 Task9 复审。"
---

# 第 3 章:输入系统

输入系统经常在排查后期才被翻出来,但很多"点了没反应""滑动不跟手""帧率不低却还是觉得卡"的问题,往往都要回到这里。判断这类问题时,先看事件什么时候进入系统(EventHub → InputReader)、经过哪些分类和过滤环节(`InputClassifier` 自 Android 10 起作为触摸事件的必经路由点,负责多指/手掌/触控笔的分类和分流)、什么时候排到目标线程(InputDispatcher 按焦点窗口分发)、什么时候变成屏幕反馈,通常比只盯着渲染线程更有效。

核心分发路径在 AOSP 里的对应关系（按事件流经顺序）：

| 组件 | AOSP 路径 | 职责 |
|------|-----------|------|
| EventHub | `frameworks/native/services/inputflinger/reader/EventHub.cpp` | 从 `/dev/input/` 读取内核输入事件，是整个分发链的入口 |
| InputReader | `frameworks/native/services/inputflinger/reader/InputReader.cpp` | 解析原始事件、识别设备类型、执行触控预处理 |
| InputClassifier | `frameworks/native/services/inputflinger/classifier/InputClassifier.cpp` | Android 10+ 引入，负责多指/手掌/触控笔的分类和分流 |
| InputDispatcher | `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` | 按焦点窗口和输入策略投递到目标连接 |
| InputConsumer | `frameworks/native/libs/input/InputConsumer.cpp` | 应用端通过 `InputEventReceiver` 接收事件的 native 桥梁 |
| InputThread | `frameworks/native/services/inputflinger/common/InputThread.cpp` | 以 `ANDROID_PRIORITY_URGENT_DISPLAY` 启动 InputReader 和 InputDispatcher 线程 |

分析 Perfetto trace 时，这些类名会直接出现在 slice 和 thread name 里，按名字对照就能定位到具体阶段。

这一章也要按新版本重新看。分析输入问题时,版本差异直接决定从哪里下手:

- **Android 12 及更早**:InputFlinger 是纯 C++ 分发栈,`InputDispatcher` 直接按焦点窗口投递,`InputClassifier` 做基本的多指分类。
- **Android 13-14**:Predictive Back 引入返回手势预测,输入事件流和返回动画开始耦合;`InputClassifier` 的分类逻辑逐步加重。
- **Android 15+**:ARR(Adaptive Refresh Rate)进入输入分析视野--屏幕刷新节奏不再是固定 60/120Hz,而是随内容动态变化,触控采样到显示反馈的端到端延迟分析必须结合 ARR 的 VSync 调度策略。
- **Android 16/17**:AOSP 主线里的 InputFlinger 开始引入 Rust 组件替换部分 C++ 模块,`InputDispatcher` 的返回键 AOT 拦截模型(Target 36+)改变了传统 `onBackPressed` 流程;Native 级手势排除区域判定下沉至 `InputDispatcher` 循环。这些变化仍在推进中，分析前先确认目标设备的实际行为：

| 主题 | 子节 | Android 16/17 候选变化 | 验证锚点 |
|------|------|----------------------|----------|
| Predictive Back | 3.3 | AOT 编译期 back 动画预测,减少运行时回调开销 | `frameworks/base/libs/windowmanager/` / `BackAnimationController` |
| MotionPredictor | 3.4 | ML 驱动的触控预测模型,替代线性外推 | `frameworks/native/services/inputflinger/predictor/` / `MotionPredictor.cpp` |
| InputFlinger Rust | 3.1 / 3.5 | 输入事件分发路径中的 Rust 组件替换 | `frameworks/native/services/inputflinger/rust/` |
| DeliQueue | 3.1 | MessageQueue 延迟投递优化,减少输入事件到主线程的排队延迟 | `frameworks/base/core/java/android/os/MessageQueue.java` |
| InputMonitor | 3.5 | 隐藏系统 API,可编程监控输入事件流,权限边界需按 `android.permission.MONITOR_INPUT` 核验 | `frameworks/base/core/java/android/hardware/input/InputMonitor.java` |

把以上变化放进同一张图里,后面分析响应速度、ANR 和高延迟交互时才不容易看偏。

## 本章内容

- `3.1` Input 事件分发全流程:从 EventHub / InputReader,经由 `InputClassifier` (Android 10+ 的触摸事件必经路由点,负责多指/手掌/触控笔分类与分流),再到 InputDispatcher 和应用窗口的投递路径。Android 16+ 的 AOT 返回键拦截和 Native 手势排除判定也落在这一节。
- `3.2` 触摸响应的性能分析:看采样、批处理、主线程消费和 UI 反馈之间的时间差。
- `3.3` 手势导航与系统交互:重点放在系统手势截获、Predictive Back 回调模型和返回动画时序。
- `3.4` 输入延迟与预测输入技术:把 Motion 预测、低延迟渲染路径和 Android 15 ARR 的高刷协同放在一起看。
- `3.5` 输入事件拦截与安全机制:看焦点窗口、权限边界、遮挡与注入限制。
- `3.6` 手势识别算法与性能优化:看去抖、阈值、误触处理和复杂手势识别的代价。
- `3.7` InputDispatcher 反压机制:事件积压时如何降级无响应窗口、如何通过 Dispatch 超时触发 ANR,以及 backpressure 在实际 trace 中的表现。
- `3.8` InputFlinger Rust 迁移与 ARR 协同:Android 15+ InputFlinger 引入 Rust 替换部分 C++ 分发路径,ARR 动态刷新率下输入采样周期的自适应调整。
- `3.9` 端到端延迟预算与感知阈值:把输入延迟拆成各阶段,结合 HCI 感知阈值研究给每段分派预算;回答"多快才算快"。
- `3.10` InputDispatcher stale event 判定:高负载下旧事件如何被标记 stale 并丢弃,优先级窗口 (foreground/background) 对事件存活时间的影响。
- `3.11` InputMethodManager 与软键盘性能:输入法会话的建立开销、IME 进程调度对输入响应的影响,以及软键盘弹出/收起期间的输入事件排队行为。

## 阅读建议

- 如果你在查"点了没反应""滑动不跟手",先读 `3.1`、`3.2`、`3.4`,把输入进入系统、进入应用、变成视觉反馈的时间顺序串起来;遇到应用频繁 ANR 或事件积压,再补 `3.7` 和 `3.10`。
- 如果你在查系统手势冲突、返回手势掉帧或动画接不上的问题,继续读 `3.3` 和 `3.5`。Android 14/15 的 Predictive Back 已经把输入分发和返回动画预览绑得更紧。
- 如果你在查高刷设备上的触控延迟、采样节奏或功耗波动,重点看 `3.4` 和 `3.8`,再和 `2.18` 的 ARR 机制对照。输入采样和刷新周期是否同步,会直接影响"跟手感";需要量化"多快才算快"时看 `3.9` 的延迟预算模型。
- IME 相关的输入卡顿(键盘弹起慢、切换输入法时掉帧)看 `3.11`。

## 延伸阅读

### Android Input/Touch/Scroll 性能与延迟深度调研
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android Input:Touch:Scroll 性能与延迟深度调研 —— 服务 SmartPerfetto 分析 Skill.md
- 类型：DeepResearch 调研结果
- 摘要：Android 输入链路跨进程流水线完整解析，含 InputReader/InputDispatcher/socketpair 传输、Choreographer CALLBACK_INPUT 批量消费、触摸 Resampling 精确常量（AOSP Resampler.cpp）、MotionPredictor TFLite 模型架构、FrameTimeline jank_type 归因，附 Perfetto stdlib android.input SQL 范式。
- 注入时间：2026-06-01
- 价值：输入链路最完整的源码级分析，Resampling 常量和 MotionPredictor TFLite 架构细节在公开资料中罕见

