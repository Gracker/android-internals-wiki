---
title: "Android 16 固定频率任务补偿执行与后台 CPU 峰值治理"
chapter: "25.15"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [power, background-task, scheduledexecutor, android16, cpu]
related_chapters: ["5.10", "25.2", "25.4", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "官方文档/每日信息/源码结构"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://developer.android.com/reference/java/util/concurrent/ScheduledExecutorService"
  - type: blog
    path: "https://android-developers.googleblog.com/2025/06/android-16-is-here.html"
---

# 25.15 Android 16 固定频率任务补偿执行与后台 CPU 峰值治理

<!-- outline-start -->
## 要点

### 🔹 行为变化边界
Android 16 面向 `targetSdk >= 36` 调整 `scheduleAtFixedRate()` 的补偿执行语义：应用回到有效生命周期后，最多立即补一次错过的周期任务。

### 🔹 旧补偿语义的性能风险
后台暂停、长任务阻塞或生命周期切换后，固定频率任务如果连续补跑，容易形成线程池排队、CPU 峰值、功耗抬升和 UI 恢复阶段争抢。

### 🔹 周期任务分类
区分监控采样、心跳上报、缓存刷新、实时处理四类周期任务，分别判断是否需要固定频率、是否允许跳过、是否应该迁移到 WorkManager 或 JobScheduler。

### 🔹 适配与降级策略
针对 API 36 前后建立统一封装：记录上次执行时间、限制补偿次数、按生命周期暂停、把恢复阶段的低优先级任务错峰执行。

### 🔹 观测方法
用 Perfetto 观察线程池 runnable 队列、CPU frequency、main thread 恢复阶段耗时；用 Batterystats / 电量采样对照后台恢复后的功耗峰值。

### 🔹 测试矩阵
覆盖 `targetSdk 35/36`、前后台切换、长任务阻塞、Doze / Battery Saver、不同线程池大小和周期参数，确认行为变化不会隐藏业务状态同步问题。

## 扩展

### 🔸 ScheduledThreadPoolExecutor 源码差异
补充 libcore / OpenJDK 中 `ScheduledThreadPoolExecutor` 的周期任务调度路径，对照 Android 16 行为变化的具体实现位置。

### 🔸 周期任务与后台调度 API 的边界
对比 `scheduleAtFixedRate()`、`Handler.postDelayed()`、WorkManager periodic work、JobScheduler periodic job、AlarmManager 的时效性和功耗代价。

### 🔸 SDK 与三方库迁移清单
整理广告、埋点、IM、APM SDK 中常见固定频率任务的风险模式，以及接入方能做的外层保护。

<!-- outline-end -->

> 本节内容待加工。
