---
title: "InputMethodManager 与软键盘性能"
chapter: "3.11"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [input, ime, keyboard, animation, latency, rendering]
related_chapters: ["3.1", "3.4", "3.9", "2.4", "7.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "AOSP结构+官方文档"
---

# 3.11 InputMethodManager 与软键盘性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：InputMethodManagerService 架构与性能关键路径
- IMMS 的 Binder 调用链路：app → IMMS → IME 进程
- `showSoftInput()` / `hideSoftInput()` 的 IPC 延迟构成
- IME 进程启动（冷启动 vs 热启动）对输入延迟的影响
- Android 14+ IME 的 isolated process 模式与性能边界

### 🔹 锚点 2：软键盘弹出/收起动画性能
- ImeInsetsSourceConsumer 与 WindowInsets 动画管线
-InsetsController#applyImeVisibility 的动画时序
- Insets Animation 与 Choreographer 的协作：VSync 对齐
- 软键盘弹出帧预算：从 showSoftInput 到第一帧可见的端到端耗时
- `WindowInsetsAnimation.Callback` 在应用侧的回调时序

### 🔹 锚点 3：软键盘对应用布局的性能影响
- 键盘弹出触发的 relayout / measure / layout 开销
- `android:windowSoftInputMode` 各模式对布局的影响差异
- adjustResize 的 full redraw 与 adjustPan 的局部移动性能对比
- Compose 中 `WindowInsets.ime` 的 recomposition 开销

### 🔹 锚点 4：IME 切换与多输入法性能
- InputMethodSubtype 切换的延迟构成
- 多输入法安装时 IMMS 的选择决策开销
- SpellChecker 与 AutoFill 的叠加延迟
- Android 14+ inline suggestions rendering 管线

### 🔹 锚点 5：软键盘性能的观测方法
- `adb shell dumpsys input_method` 关键指标解读
- Perfetto 中 IME 相关 slice 和 track
- `WindowInsetsAnimation` 回调计时
- SoftInput show latency 的端到端测量

### 🔹 锚点 6：Android 版本演进中的 IME 性能变化
- Android 11: ImeInsetsSourceConsumer 引入 insets animation
- Android 12: Insets Animation LAUNCH_ANGLE
- Android 14: IME isolated process
- Android 15: predictive back 与 IME 的交互
- Android 16/17: IME 与 Edge-to-Edge 的适配性能

## 扩展

### 🔸 扩展点 1：硬件键盘与多输入设备的性能路径
- 外接键盘的事件路径差异（不走 IMMS show/hide）
- ChromeOS / 桌面模式下 IME 的性能差异

### 🔸 扩展点 2：自定义 IME 的性能优化建议
- IME 应用侧的渲染优化
- CandidateView 的滑动性能
- IME Service 生命周期与内存占用

<!-- outline-end -->

> 本节内容待加工。
