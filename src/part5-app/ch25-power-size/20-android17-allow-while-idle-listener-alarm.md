---
title: "Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理"
chapter: "25.20"
section: "25.20"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [power, alarmmanager, wakelock, android17, background-work]
related_chapters: ["11.5", "25.3", "25.14", "25.19"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/Android 17 API 变更/Clippings结构参考"
gap_score: 16
material_count: 5
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
  - type: official-blog
    path: "https://developer.android.com/blog/posts/the-third-beta-of-android-17"
  - type: official
    path: "https://developer.android.com/reference/android/app/AlarmManager#setExactAndAllowWhileIdle(int,long,java.lang.String,java.util.concurrent.Executor,android.app.AlarmManager.OnAlarmListener)"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/alarms"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/schedule-exact-alarms"
---

# 25.20 Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理

<!-- outline-start -->
## 要点

### 🔹 API 37 新增了什么
解释 `AlarmManager.setExactAndAllowWhileIdle(int, long, String, Executor, OnAlarmListener)` 与既有 `PendingIntent` 版本、`setExact()` Listener 版本的差异，明确它只适合进程仍在的短生命周期任务。

### 🔹 它解决的 WakeLock 问题
围绕长连接保活、短周期重试、消息同步和临时后台任务，说明 callback 型 allow-while-idle alarm 如何减少应用为了等待下一次任务而持有连续 WakeLock 的需求。

### 🔹 权限与生命周期边界
核对 `SCHEDULE_EXACT_ALARM`、`USE_EXACT_ALARM`、`OnAlarmListener` 豁免、进程被系统清理后的取消行为，以及 Android 14 之后 exact alarm 默认拒绝的迁移影响。

### 🔹 与 WorkManager、JobScheduler、Handler 延迟任务的选型
建立任务选型矩阵：可延迟周期任务走 WorkManager / JobScheduler，进程内短延迟走 Handler / coroutine delay，必须熄屏精确唤醒才考虑 allow-while-idle alarm。

### 🔹 电量归因与 tag 设计
整理 tag、Executor、任务类型、屏幕状态、前后台状态、WakeLock 持有时长和 Android Vitals 过度 WakeLock 指标之间的证据关联。

### 🔹 迁移与验证流程
给出从连续 WakeLock / 轮询线程迁移到 Listener Alarm 的实验设计：构造熄屏场景、记录触发延迟、检查 batterystats、确认漏触发和重复触发边界。

## 扩展

### 🔸 socket 保活与 FCM / push 的边界
对比主动维持 socket、FCM 高优先级消息、exact alarm 唤醒和后台网络限制的适用场景。

### 🔸 Android Vitals WakeLock 指标联动
把本节与 25.19 的 excessive partial wake lock 治理合并成后台唤醒门禁规则。

<!-- outline-end -->

> 本节内容待加工。
