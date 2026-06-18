---
title: "App Widget 更新性能：RemoteViews IPC 与 Glance 渲染"
chapter: "22.24"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [appwidget, remoteviews, glance, ipc, widget-performance]
related_chapters: ["2.6", "7.13", "13.1", "22.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-19"
gap_source: "AOSP结构/官方文档"
---

# 22.24 App Widget 更新性能：RemoteViews IPC 与 Glance 渲染

<!-- outline-start -->
## 要点

### 🔹 RemoteViews 跨进程机制
- RemoteViews 的本质：序列化 View 树通过 Binder 传入 AppWidgetService
- AppWidgetService（system_server）作为中转，将 RemoteViews 分发给 AppWidgetHost（通常为 Launcher）
- 序列化/反序列化的 CPU 开销与 View 树复杂度的关系
- RemoteViews.Action 队列的执行模型：RemoteViewsAdapter 在 Host 侧重放操作

### 🔹 AppWidget 更新调度与限流
- AlarmManager 定时更新 vs WorkManager 按需更新的取舍
- Android 12+ 的系统更新限流策略（updatePeriodMillis 最小值 1800 秒）
- 快速更新序列对 system_server 和 Launcher 的 CPU/内存压力
- 高频更新导致的 ANR 风险（AppWidgetHost 频繁 rebind RemoteViewsService）

### 🔹 RemoteViewsService 与集合 Widget
- ListView/GridView Widget 的 RemoteViewsService.Connection 绑定生命周期
- RemoteViewsAdapter.getViewAt() 在 Launcher 进程中的执行成本
- 大数据集 Widget 的滚动卡顿机制：跨进程 getViewAt 调用的累积延迟
- ListView Widget 与 Compose Glance 的性能差异

### 🔹 Jetpack Glance 性能特征
- Glance 的架构：@Composable → RemoteViews 翻译层 → 标准 RemoteViews 流程
- Glance 与原生 Compose 的差异：不直接使用 Compose UI 运行时，最终产物仍是 RemoteViews
- Glance 的重组开销：状态变化触发 RemoteViews 重新生成
- Glance 与直接 RemoteViews 的性能对比：翻译层额外开销 vs 开发效率

### 🔹 Widget 位图与内存
- RemoteViews 中 ImageView/ImageButton 的位图传递：Bitmap Parcelable 跨进程传递
- 大尺寸 Widget 背景图的内存压力（Launcher 进程持有 Bitmap）
- 位图复用策略：同一 Widget 多尺寸（home screen grid cell）的位图管理
- widget background drawable 的 inflate 成本

### 🔹 Widget 功耗与后台调度
- Widget 更新唤醒设备的功耗链路：AlarmManager → AppWidgetProvider.onUpdate → 后台执行
- 息屏状态下的 Widget 更新：是否存在不必要的屏幕唤醒
- 多 Widget 应用的批量更新策略：合并 onUpdate 调用减少重复 bind
- 配合 WorkManager 的延迟更新与节流策略

## 扩展

### 🔸 RemoteViews.CallingIdentity 与权限边界
- Android 12+ 的 RemoteViews.CallingIdentity 机制
- 跨进程回调的权限验证开销

### 🔸 Widget 在多用户/工作配置下的性能
- WORK_PROFILE 用户下 Widget 的额外 IPC 路径
- 多用户场景的 AppWidgetService 调度差异

### 🔸 Dynamic Color 与 Widget 渲染
- Android 12+ 动态色彩对 Widget 的影响：颜色计算成本
- Glance 对 dynamicColor 的处理方式

<!-- outline-end -->

> 本节内容待加工。
