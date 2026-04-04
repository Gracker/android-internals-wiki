---
title: "Window Manager Service 与窗口管理"
chapter: "2.12"
section: "2.12"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [WMS, WindowManagerService, Surface, Window, StartingWindow, Window动画, 多窗口, SurfaceControl]
related_chapters: ["2.1", "2.6", "3.1", "8.2", "8.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+读者需求"
---

# 2.12 Window Manager Service 与窗口管理

<!-- outline-start -->
## 要点

### 🔹 锚点 1：WMS 为什么影响性能
- WMS 是 Android 窗口系统的中枢：管理所有 Window 的创建、销毁、层级（Z-order）和大小
- 从用户点击 App 图标到看到第一帧内容，WMS 负责了 StartingWindow 的创建、主 Window 的 relayout、以及 Surface 的分配
- WMS 运行在 system_server 进程中，与 SurfaceFlinger、AMS、Input 系统紧密协作
- 性能关键路径：relayoutWindow() 是 WMS 最频繁也最重的操作之一，涉及 Surface 分配/销毁、Window 布局计算、SurfaceControl Transaction 提交

### 🔹 锚点 2：Window 与 Surface 的关系
- 每个 Window 背后都有一个 Surface（对应 SurfaceFlinger 中的一个 Layer）
- WMS 持有 SurfaceControl（控制层属性：位置、大小、透明度、Z-order），App 持有 Surface（用于绘制）
- Surface 创建流程：App → WMS.relayoutWindow() → SurfaceFlinger.createLayer() → 返回 Surface 给 App
- BufferQueue 的 producer 端在 App（通过 Surface），consumer 端在 SurfaceFlinger
- [待验证：SurfaceControl.Transaction 的 apply() 是同步还是异步调用 SurfaceFlinger]

### 🔹 锚点 3：StartingWindow 与启动性能
- 冷启动时 WMS 立即创建 StartingWindow（splash screen），给用户即时视觉反馈
- Android 12+ SplashScreen API 统一了 StartingWindow 的行为，替代了各家 OEM 的定制方案
- StartingWindow 的生命周期：创建 → 显示第一帧 → App 主 Window 就绪 → 移除 StartingWindow
- StartingWindow 移除时机直接影响启动体感：过早移除出现白屏闪烁，过晚移除延长启动感知时间
- [待补充：StartingWindow 在 Perfetto 中的 Trace 表现]

### 🔹 锚点 4：Window 动画与过渡性能
- App 启动/退出/切换的动画由 WMS 的 WindowAnimator 统一调度
- 动画类型：Activity 切换动画（open/close）、Task 过渡动画、多窗口分屏动画
- Android 14+ Predictive Back 动画：WMS 与 Input 系统协作，实现手势驱动的返回预览动画
- 动画性能瓶颈：动画期间 WMS 每帧都要计算 Window 的 transform（缩放、平移、透明度），通过 SurfaceControl.Transaction 提交给 SurfaceFlinger
- [待验证：WindowAnimator 是否运行在独立的动画线程，还是在 system_server 主线程]

### 🔹 锚点 5：relayoutWindow 的性能路径
- relayoutWindow() 是 WMS 中最核心也最重的 Binder 调用之一
- 触发场景：Window 大小变化、配置变更（旋转屏幕）、Visibility 变化、Surface 属性更新
- 内部流程：参数校验 → WindowState 更新 → SurfaceControl Transaction 构建 → Surface 大小调整 → 布局计算 → 通知 App
- 性能风险：频繁的 relayout（如动画期间每帧触发）可能导致 system_server 主线程阻塞
- [待补充：relayoutWindow 在 Perfetto 中的 Trace 切片]

### 🔹 锚点 6：多窗口、折叠屏与 Desktop Mode
- Android 的多窗口模式（Split-screen、Freeform、Picture-in-Picture）完全由 WMS 管理
- 折叠屏设备：WMS 需要处理屏幕尺寸变化导致的 Window relayout，可能触发 Activity 重建或配置变更
- Android 16 Desktop Windowing：外接显示器场景下 WMS 管理自由窗口的拖拽、缩放、层级
- Android 17 recreateOnConfigChanges：6 种配置变更不再强制重启 Activity，减少 WMS 触发的 relayout 开销
- 多窗口场景下 Surface 数量增加，SurfaceFlinger 合成压力上升，可能导致掉帧

### 🔹 锚点 7：在 Perfetto 中的表现
- WMS 相关的 Trace 事件主要出现在 system_server 进程中
- 关键 Slice：wm.relayout_window、wm.set_visibility、SurfaceControl.Transaction.apply
- StartingWindow 的创建和移除在 Trace 中表现为 WindowState 的 visibility 变化
- 多窗口切换时，可以通过 SurfaceFlinger 的 Layer 变化观察 WMS 的操作结果
- [待补充：具体的 Perfetto SQL 查询示例]

## 扩展

### 🔸 扩展点 1：WindowInsets 与布局性能
- WindowInsets 的分发链路：WMS → ViewRootImpl → View hierarchy
- 不正确的 Insets 处理导致额外的 requestLayout 和 measure/layout pass
- Android 15+ 边到边（Edge-to-edge）强制要求，Insets 管理更关键

### 🔸 扩展点 2：WMS 与 Input 系统的协作
- WMS 维护 Window 的 Z-order 和区域信息，InputDispatcher 据此进行 hit-test
- 窗口焦点（focus）切换的性能影响：焦点变更 → Input 通道切换 → 可能的事件丢失
- 与 §3.1 Input 事件分发全流程 的交叉引用

<!-- outline-end -->

> 本节内容待加工。
