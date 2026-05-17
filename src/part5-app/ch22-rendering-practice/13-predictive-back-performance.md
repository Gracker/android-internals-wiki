---
title: "Predictive Back 动画与页面切换性能"
chapter: "22.13"
section: "22.13"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37); AndroidX Activity 1.8.0+; AndroidX Fragment 1.7.0+; AndroidX NavigationEvent 1.0+"
tags: [predictive-back, rendering, animation, fragment, compose]
related_chapters: ["3.3", "7.4", "18.2", "22.3", "22.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "官方文档/AndroidX 版本演进/AOSP 结构"
sources:
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/support-animations"
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/support-animations-views"
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture"
  - type: official
    path: "https://developer.android.com/guide/fragments/animate"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/navigationevent"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/activity"
  - type: blog
    path: "https://android-developers.googleblog.com/2024/05/a-developers-roadmap-to-predictive-back.html"
---

# 22.13 Predictive Back 动画与页面切换性能

<!-- outline-start -->
## 要点

### 🔹 平台 Back 分发与 AndroidX 兼容层
从 `OnBackInvokedCallback`、`OnBackInvokedDispatcher`、`OnBackPressedDispatcher` 和 AndroidX Activity 的桥接关系建立版本边界，说明 Android 13+ predictive back 与旧回退处理的差异。

### 🔹 手势进度如何进入动画系统
整理 predictive back 事件中的 progress、edge、cancel、complete 四类信号，区分 View property animation、Fragment transition、Activity transition 和 Compose `NavigationEvent` 的接入方式。

### 🔹 Fragment / Navigation 页面切换性能边界
结合 Fragment 1.7+、Transition 1.5+ 和 Navigation 版本演进，说明返回手势期间哪些工作应限制在动画属性更新，哪些 View inflate、数据加载和事务提交要避开手势进行中阶段。

### 🔹 Compose NavigationEvent 与重组成本
分析 `NavigationEventHandler`、`rememberNavigationEventState`、`NavigationEventTransitionState.InProgress` 的使用边界，重点检查手势进度驱动状态更新时的重组范围、布局成本和取消回滚逻辑。

### 🔹 Perfetto 观察点与问题定位
列出输入事件、主线程消息、Choreographer、FrameTimeline、RenderThread 和 GPU completion 的观察点，用于区分输入分发延迟、动画每帧计算过重、布局重算和合成阶段阻塞。

### 🔹 工程治理清单
给出接入 predictive back 的最小改造路径：版本开关、回调注册顺序、动画对象复用、手势取消复位、页面释放时机、WebView / Fragment / Compose 混合栈的兜底策略。

## 扩展

### 🔸 WebView predictive back
梳理 WebView 自身历史返回与 Activity 返回手势之间的优先级，避免页面内回退和系统返回动画互相抢占。

### 🔸 跨 Activity 转场
补充自定义 cross-activity predictive back 动画的版本要求、性能风险和低版本降级方案。

### 🔸 大屏与多窗口场景
分析 predictive back 在多窗口、桌面模式和 foldable 上的边缘手势、动画幅度和窗口尺寸变化问题。

<!-- outline-end -->

> 本节内容待加工。
