---
title: "Foreground Service 超时与 JobScheduler 配额治理"
chapter: "25.13"
status: draft
applicable_versions: "Android 15 (API 35) - Android 16 (API 36)"
tags: [foreground-service, jobscheduler, power, background-work, android-16]
related_chapters: ["5.8", "5.10", "11.2", "25.2", "25.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "官方文档/AOSP结构/热点变更"
---

# 25.13 Foreground Service 超时与 JobScheduler 配额治理

<!-- outline-start -->
## 要点

### 🔹 Android 15 后台服务超时规则
整理 `dataSync`、`mediaProcessing` 等 Foreground Service 类型的超时窗口、回调行为和系统处置方式，区分正常停止、超时降级和异常终止。

### 🔹 Android 16 JobScheduler 配额变化
说明 Android 16 中 Job 与 Foreground Service 并发执行时仍受运行时配额约束的行为变化，避免把前台服务当作绕过后台任务限制的通道。

### 🔹 任务类型选择表
按用户可见、是否可中断、是否需要网络、是否需要充电/空闲条件，给出 Foreground Service、WorkManager、JobScheduler、AlarmManager 的选择边界。

### 🔹 线上指标与告警设计
定义需要采集的指标：服务启动次数、运行时长、超时回调、Job 停止原因、后台耗电、用户前台恢复次数，用于定位后台任务是否进入配额瓶颈。

### 🔹 迁移与降级策略
给出长任务拆分、断点续传、约束条件重排、用户主动入口恢复、通知交互恢复等治理动作，减少系统超时对任务完成率的影响。

### 🔹 与功耗治理章节的分工
本节处理后台执行规则和任务调度选择；电量归因、WakeLock、Alarm 和 WorkManager 实战分别详见 25.1、25.3、25.4 节。

## 扩展

### 🔸 厂商后台限制叠加
记录不同 ROM 对前台服务通知、后台启动、耗电排行的额外限制，作为线上问题排查的版本维度。

### 🔸 调试命令与复现场景
补充 `adb shell cmd jobscheduler`、`dumpsys activity services`、`dumpsys deviceidle` 等排查入口，并整理可复现的测试用例。

<!-- outline-end -->

> 本节内容待加工。
