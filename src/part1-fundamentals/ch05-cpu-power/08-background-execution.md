---
title: "后台执行限制与优化"
chapter: "5.8"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 36)"
tags: [后台限制, Doze, App Standby, 前台服务, WorkManager, JobScheduler, 省电, 后台启动]
related_chapters: ["5.6", "5.7", "11.2", "8.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+研究素材"
gap_score: "14/20"
---

# 5.8 后台执行限制与优化

<!-- outline-start -->
## 要点

### 🔹 Android 后台限制演进史
Android 8.0 后台服务限制 → 9.0 电源管理 → 12 前台服务限制 → 16/17 精确的后台启动管控

### 🔹 Doze 与 App Standby 机制
Deep Doze / Light Doze 维护窗口期、App Standby Buckets（Active/Working Set/Frequent/Rare/Restricted）

### 🔹 前台服务与通知
前台服务类型（camera/connectedDevice/health/location/mediaPlayback/messaging/phoneCall/specialUse）与 Android 14 声明要求

### 🔹 WorkManager vs JobScheduler vs AlarmManager
三种后台调度方案的选型指南与性能影响

### 🔹 后台执行对性能的影响
不合理的后台工作如何拖慢前台：CPU 争抢、内存压力、热节流

## 扩展

### 🔸 Android 16/17 最新后台限制
DataSync 前台服务超时、mediaProcessing 超时、后台启动 Activity 新限制

### 🔸 系统级后台优化策略
OEM 厂商如何通过vendor配置进一步限制后台行为
<!-- outline-end -->

> 本节内容待加工。缺口评分：14/20。素材丰富度：3 篇。直接关联功耗优化（§5.6/§11.2）和响应速度（§8.4）。
