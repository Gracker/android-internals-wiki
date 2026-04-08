---
title: "Notification 性能与 ANR"
chapter: "9.6"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [notification, anr, notificationmanagerservice, remoteviews, performance]
related_chapters: ["9.2", "9.3", "1.4", "1.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "AOSP结构+读者需求+素材驱动"
gap_score: 16
---

# 9.6 Notification 性能与 ANR

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么 Notification 会引发 ANR
- NotificationManagerService（NMS）运行在 system_server，通过 Binder IPC 与 App 交互
- ANR 触发点：App 主线程在发送/更新通知时被 NMS 的同步回调阻塞
- 通知发布流程中的 Binder 调用链：App → NMS → SystemUI（RemoteViews inflate）
- ANR 的三种触发场景：发布通知、通知监听器回调、通知渠道更新

### 🔹 锚点 2：NotificationManagerService 内部机制
- NMS 的线程模型：在 system_server 的前台线程处理通知操作
- 通知发布流程：enqueueNotification → rank → filter → notify listeners → post to SystemUI
- 通知排名（ranking）的性能开销：对所有活跃通知的实时排序
- 通知限制策略：Android 12+ 的每 App 通知数量限制对性能的影响
- NMS 与 PermissionManager 的交互开销

### 🔹 锚点 3：RemoteViews 的性能开销
- RemoteViews 跨进程 inflate：App 构造 → Parcel 序列化 → SystemUI 反序列化 → inflate
- 布局嵌套对 inflate 时间的指数级影响
- 图片通知（BigPicture/Style with ImageView）的 Bitmap 传输开销
- RemoteViews 与系统资源加载：跨进程资源解析的性能陷阱
- 自定义通知布局的最佳实践：最大嵌套深度、避免的自定义 View

### 🔹 锚点 4：NotificationListenerService 与性能
- NLS 回调在主线程执行：onNotificationPosted/onNotificationRemoved 的执行时间预算
- 大量通知场景下 NLS 回调的频率与 CPU 开销
- NLS 排序（RankingMap）重建的触发频率
- 常见问题：NLS 实现中的 IO 操作、数据库查询导致 ANR

### 🔹 锚点 5：通知与 ANR 的典型模式
- 模式一：主线程同步等待 NMS 响应（低概率但存在）
- 模式二：NLS 回调阻塞主线程（最常见）
- 模式三：通知频道（Channel）创建/更新时的阻塞操作
- 模式四：高频通知更新导致 SystemUI 进程过载（间接 ANR）
- 模式五：Foreground Service 通知启动超时

### 🔹 键点 6：Android 17 通知性能变更
- 后台通知发送的严格限制（Background Service 限制联动）
- 通知权限（POST_NOTIFICATIONS）对通知管线的影响
- Notification.ProgressStyle 新 API 的性能特征
- Android 17 对通知监听器回调频率的限制

### 🔹 锚点 7：在 Perfetto 中诊断通知 ANR
- 识别 NMS 相关的 Binder 调用：在 Trace 中过滤 NotificationManager
- 分析 NLS 回调耗时：onNotificationPosted 的执行时间
- 通知发布链路的完整 Trace 路径
- 使用 dumpsys notification 输出辅助诊断

## 扩展

### 🔸 扩展点 1：通知批量操作优化
- 多通知发布的最佳实践：notifyAsUser 批量接口
- 通知组（Group/Summary）对渲染性能的影响
- 从 NMS 视角看通知限流策略

### 🔸 扩展点 2：推送服务（FCM/厂商推送）与通知性能
- 推送到达 → 通知展示的延迟链路
- 高推送频率场景下的通知队列管理
- 厂商推送 SDK 对通知性能的潜在影响

<!-- outline-end -->

> 本节内容待加工。
