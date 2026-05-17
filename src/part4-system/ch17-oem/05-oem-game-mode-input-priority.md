---
title: "OEM 游戏模式输入优先级与触控调度"
chapter: "17.5"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [oem, game-mode, input, touch-latency, refresh-rate, perfetto]
related_chapters: ["3.5", "3.9", "8.9", "17.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材/AOSP结构/官方文档"
gap_score: 17
material_count: 3
source_refs:
  - "DeepResearch/2026-05-12-oem-game-mode-input-priority-research.md"
  - "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/app/GameManagerService.java"
  - "https://cs.android.com/android/platform/superproject/+/master:frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api"
---

# 17.5 OEM 游戏模式输入优先级与触控调度

<!-- outline-start -->
## 要点

### 🔹 AOSP GameMode 的能力边界
厘清 GameManagerService、GameService API、PowerManager HAL GAME 档位分别控制什么，避免把功耗/帧率策略写成系统级输入优先级。

### 🔹 焦点窗口与 InputDispatcher 分发路径
从 WindowManagerService 焦点更新、InputDispatcher 目标窗口选择和无响应窗口降级解释 AOSP 标准输入分发的优先级来源。

### 🔹 帧率优先级如何影响触摸到显示延迟
说明 Window.refreshRateSelectionPriority、preferredDisplayModeId、SurfaceFlinger 刷新率选择只改变渲染时序，不直接改变输入事件排队顺序。

### 🔹 游戏 View 如何保证触摸序列完整
梳理 requestDisallowInterceptTouchEvent(true)、FLAG_DISALLOW_INTERCEPT、GameActivity 触摸事件处理与父容器拦截边界。

### 🔹 OEM 专有输入优化的验证路径
列出厂商可能修改的 InputDispatcher.cpp、WindowManagerService、触控驱动、Power HAL 和游戏工具服务入口，并给出可验证证据类型。

### 🔹 Perfetto 实机验证口径
设计 input、view、sched、freq、SurfaceFlinger、FrameTimeline 组合采集方式，用队列延迟、触摸到显示延迟和频率档位变化区分不同优化来源。

## 扩展

### 🔸 GameService 与厂商游戏工具服务
跟踪 GameSession、GameServiceProvider 与厂商游戏空间的职责边界。

### 🔸 多窗口、折叠屏与外设输入
补充桌面模式、自由窗口、手柄/键鼠输入下焦点与优先级的变化。

<!-- outline-end -->

> 本节内容待加工。
