---
title: "AccessibilityManagerService 与无障碍服务性能影响"
chapter: "7.19"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [accessibility, jank, layout, a11y, performance, rendering]
related_chapters: ["7.2", "7.3", "2.5", "12.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "AOSP结构+章节深挖"
---

# 7.19 AccessibilityManagerService 与无障碍服务性能影响

<!-- outline-start -->
## 要点

### 🔹 锚点 1：AccessibilityManagerService 架构与性能模型
- AMS 中 Accessibility 管线的 Binder 调用链路
- AccessibilityInteractionClient 的跨进程查询模型
- AccessibilityEvent 分发路径：app → A11yMS → A11yService
- 事件类型过滤与批量分发对主线程的影响

### 🔹 锚点 2：无障碍服务对 View 渲染管线的额外开销
- AccessibilityNodeInfo 树构建的触发时机与开销
- `onInitializeAccessibilityNodeInfo()` / `onPerformActionForVirtualView()` 对 measure/layout 的叠加
- `sendAccessibilityEvent()` 的主线程阻塞点
- RecyclerView / Compose 中 accessibility delegate 的批量调用

### 🔹 锚点 3：常见无障碍服务的性能影响实测
- TalkBack 对列表滑动帧率的影响
- Select to Speak 对渲染管线的额外负担
- Switch Access 的轮询开销
- 第三方无障碍服务（抢红包/自动化工具）的高频事件订阅

### 🔹 锚点 4：应用侧的 Accessibility 性能优化策略
- `importantForAccessibility` 的精细控制减少 NodeInfo 构建
- `accessibilityTraversalAfter/before` 控制遍历顺序
- Compose 中 `semantics` 作用域的最小化
- 批量 UI 更新时合并 AccessibilityEvent
- `AccessibilityDelegate` 的懒加载

### 🔹 锚点 5：Accessibility 性能的观测方法
- Perfetto 中 AccessibilityEvent 的 slice 追踪
- `adb shell dumpsys accessibility` 关键指标
- `AccessibilityEvent.getType()` 频率统计
- 通过 `isAccessibilityEnabled()` 的运行时检测

### 🔹 锚点 6：Android 版本演进中的 Accessibility 性能变化
- Android 12: AccessibilityService flag 的性能优化选项
- Android 13: per-app accessibility event throttling
- Android 14: AccessibilityNodeInfo 的 parcelable 优化
- Android 15/16: Compose semantics 性能改进
- Android 17: AccessibilityService 生命周期与后台执行限制

## 扩展

### 🔸 扩展点 1：自动化测试框架（UiAutomation/Espresso）的 Accessibility 性能耦合
- Espresso 的 Accessibility Check 对测试性能的影响
- UiAutomation 与 A11yMS 的共享 binder 连接

### 🔸 扩展点 2：WebView 与 Accessibility 的性能交互
- WebView 的 AccessibilityNodeProvider 实现开销
- 混合栈应用中 WebView 内容变化触发的 A11y 洪水

<!-- outline-end -->

> 本节内容待加工。
