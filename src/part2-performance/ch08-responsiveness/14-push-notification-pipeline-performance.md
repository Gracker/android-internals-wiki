---
title: "推送通知管线性能：FCM 投递延迟与 NotificationManagerService 渲染"
chapter: "8.14"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["FCM", "通知", "Notification", "推送", "延迟"]
related_chapters: ["9.6", "8.2", "25.4", "11.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/章节深挖"
---

# 8.14 推送通知管线性能：FCM 投递延迟与 NotificationManagerService 渲染

<!-- outline-start -->
## 要点

### 🔹 锚点 1
FCM 消息从服务器到设备的投递链路，Play Services FCM 接收器的唤醒延迟，消息类型（data/notification）对投递路径的影响

### 🔹 锚点 2
NMS 的通知入队处理，通知 UI 布局渲染开销，RemoteViews 与通知模板的性能差异

### 🔹 锚点 3
NMS 的通知速率限制（rate limiting）机制，postTimeout 与 cancel 的性能影响，通知栏更新频率与主线程占用

### 🔹 锚点 4
NotificationChannel 重要性级别对系统调度的影响，heads-up 通知的渲染开销，通知分组（grouping）的批量优化

### 🔹 锚点 5
data message 触发的后台任务调度性能，FCM + WorkManager 的唤醒链路开销，高优先级 FCM 与 Doze 模式的交互

## 扩展

### 🔸 扩展点 1
FCM、个推、极光等推送 SDK 的设备唤醒策略差异，长连接保活功耗对比

### 🔸 扩展点 2
通知中的动画、图片、进度条对渲染性能的影响，通知样式模板的性能排序

<!-- outline-end -->

> 本节内容待加工。
