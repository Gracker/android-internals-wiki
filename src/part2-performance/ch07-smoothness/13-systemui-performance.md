---
title: "SystemUI 性能分析"
chapter: "7.13"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [systemui, jank, launcher, statusbar, navigationbar, notification-shade, perfetto]
related_chapters: ["2.4", "2.5", "7.1", "7.3", "13.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "AOSP结构+读者需求+素材驱动"
gap_score: 18
---

# 7.13 SystemUI 性能分析

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么 SystemUI 性能值得关注
- SystemUI 是用户最常感知的「系统窗口」：StatusBar、NavigationBar、Notification Shade、Recent Apps、Launcher
- SystemUI jank 对用户感知的影响比普通 App 更大——因为它永远在屏幕上
- OEM 在 SystemUI 优化上投入的工程量通常超过任何单个 App
- SystemUI 进程（com.android.systemui）与 system_server 进程的关系

### 🔹 锚点 2：SystemUI 架构与渲染路径
- SystemUI 的多 Surface 架构：StatusBar、NavigationBar、Shade 各自拥有独立 Surface
- Shade 展开动画的渲染路径：从拖拽到全屏展开的帧预算分配
- Launcher 与 SystemUI 的交互：App 启动动画期间的状态同步
- Recents（最近任务）的 Surface 管理与动画性能
- SystemUI 与 SurfaceFlinger 的 Layer 层级关系（z-order）

### 🔹 锚点 3：StatusBar 与 NavigationBar 的性能陷阱
- 通知图标的 measure/layout 开销：频繁更新的 Notification Icon API
- NavigationBar 按钮的触摸响应延迟：Input 事件从 App → system_server → SystemUI 的额外跳转
- StatusBar 布局过深导致的 inflate 开销
- 系统图标（Signal、Battery、Clock）的更新频率与绑定开销
- Android 17 手势导航对 NavigationBar 渲染的影响

### 🔹 锚点 4：Notification Shade 展开性能
- Shade 展开/收起动画的关键路径：从 Input 事件到 SurfaceControl 事务
- 通知列表的 RecyclerView 性能：RemoteViews inflate 开销
- 通知内容更新导致的 Shade 重绘频率
- Heads-up Notification（HUN）对主线程的阻塞风险
- 大视图通知（BigPicture、InboxStyle）的渲染性能

### 🔹 键点 5：Launcher 性能分析
- Workspace 页面滑动性能：CellLayout 的 measure/layout 瀑布
- App 启动动画的帧同步：Launcher → SurfaceFlinger → App 的三方协作
- AllApps 列表的大数据集 RecyclerView 性能
- 快捷方式和小部件（Widget）的加载性能
- Launcher 进程与 SystemUI 进程在启动动画期间的 CPU 竞争

### 🔹 锚点 6：在 Perfetto 中分析 SystemUI 性能
- SystemUI 进程的 Track 识别：com.android.systemui 的 UI/Main/RenderThread
- 关键 Trace 点：StatusBar.updateNotificationIcons、ShadeController、NotificationStackScrollLayout
- Launcher3 的 tracepoint：DragLayer、Workspace、AppTransition
- 使用 SurfaceFlinger Layers Track 分析 SystemUI 的 Layer 合成开销
- 常见 SystemUI jank 模式在 Trace 中的特征

### 🔹 锚点 7：SystemUI 优化策略
- 异步布局：将 inflate 和 measure 移到后台线程
- 图标缓存与预加载：减少通知图标更新的渲染开销
- SurfaceControl 事务批处理：减少跨进程 IPC 次数
- 视图层级扁平化：减少 StatusBar/NavigationBar 的嵌套层级
- 通知限流：对高频通知更新的合并策略

## 扩展

### 🔸 扩展点 1：OEM 厂商的 SystemUI 定制与性能回归
- 厂商定制对 SystemUI 布局层级的影响
- 第三方 SystemUI 替换方案的架构差异
- A/B 测试 SystemUI 布局变更对性能的影响

### 🔸 扩展点 2：多用户/多显示场景下的 SystemUI 性能
- 多用户切换时 SystemUI 的状态重建开销
- 外接显示器/桌面模式下 SystemUI 的双屏渲染
- 折叠屏设备 SystemUI 的布局切换性能

### 🔸 扩展点 3：Android 17 Predictive Back 对 SystemUI 的影响
- Predictive Back 动画在 SystemUI 中的实现
- 后退手势与 NavigationBar 的协作性能
- 边到边（Edge-to-Edge）渲染对 StatusBar 的影响

<!-- outline-end -->

> 本节内容待加工。
