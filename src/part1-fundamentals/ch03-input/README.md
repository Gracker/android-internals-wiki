---
title: "第 3 章：输入系统"
chapter: "3.0"
section: "3.0"
status: "ready-for-review"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-23"
last_verified_against: "AOSP frameworks/native/services/inputflinger main 分支、Android 15 ARR / Predictive Back 文档、ch03 子章节"
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
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-04-23T17:25:41+08:00"
---

# 第 3 章：输入系统

输入系统经常在排查后期才被翻出来，但很多“点了没反应”“滑动不跟手”“帧率不低却还是觉得卡”的问题，往往都要回到这里。判断这类问题时，先看事件什么时候进入系统、什么时候排到目标线程、什么时候变成屏幕反馈，通常比只盯着渲染线程更有效。

这一章也要按新版本重新看。Android 15 之后，输入延迟分析已经要同时关注预测输入、Predictive Back 和 ARR 对显示刷新节奏的协同；AOSP 主线里的 InputFlinger 也开始引入 Rust 组件，输入服务不再只有传统的 C++ 分发栈。把这些变化放进同一张图里，后面分析响应速度、ANR 和高延迟交互时才不容易看偏。

## 本章内容

- `3.1` Input 事件分发全流程：从 EventHub / InputReader，经由 `InputClassifier` 等分类或过滤环节，再到 InputDispatcher 和应用窗口的投递路径。
- `3.2` 触摸响应的性能分析：看采样、批处理、主线程消费和 UI 反馈之间的时间差。
- `3.3` 手势导航与系统交互：重点放在系统手势截获、Predictive Back 回调模型和返回动画时序。
- `3.4` 输入延迟与预测输入技术：把 Motion 预测、低延迟渲染路径和 Android 15 ARR 的高刷协同放在一起看。
- `3.5` 输入事件拦截与安全机制：看焦点窗口、权限边界、遮挡与注入限制。
- `3.6` 手势识别算法与性能优化：看去抖、阈值、误触处理和复杂手势识别的代价。

## 阅读建议

- 如果你在查“点了没反应”“滑动不跟手”，先读 `3.1`、`3.2`、`3.4`，把输入进入系统、进入应用、变成视觉反馈的时间顺序串起来。
- 如果你在查系统手势冲突、返回手势掉帧或动画接不上的问题，继续读 `3.3` 和 `3.5`。Android 14/15 的 Predictive Back 已经把输入分发和返回动画预览绑得更紧。
- 如果你在查高刷设备上的触控延迟、采样节奏或功耗波动，重点看 `3.4`，再和 `2.18` 的 ARR 机制对照。输入采样和刷新周期是否同步，会直接影响“跟手感”。
