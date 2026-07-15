---
title: "Android 17 前台服务类型执行模型与后台启动性能边界"
chapter: "25.26"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['foreground-service', 'fgs-type', 'background-launch', 'power', 'android17']
related_chapters: ['25.13', '25.25', '8.14']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构 + 官方文档 + research-gaps"
gap_score: "17/20"
---

# 25.26 Android 17 前台服务类型执行模型与后台启动性能边界

<!-- outline-start -->
## 要点

### 🔹 FGS 类型强制声明与匹配校验机制
Android 14 引入的 FGS 类型（dataSync, location, camera, microphone, health, mediaPlayback, mediaProjection, phoneCall, shortService, specialUse, systemExempted, connectedDevice）在 Android 17 的演进与执行约束。

### 🔹 Android 17 FGS 临时允许列表（FgsTempAllowList）与超时机制
FgsTempAllowList 实现原理、 grant 时间窗口、与 OomAdjuster 优先级提升的联动关系。

### 🔹 后台 Activity 启动（BAL）限制与 FGS 启动链路
BackgroundActivityLauncher 检查链路、FGS BAL 豁免条件、Android 17 收紧的 BAL 策略。

### 🔹 FGS Defer 执行模型与 JobScheduler 配额联动
Android 17 中 FGS 与 JobScheduler quota 系统的协调机制、超时降级策略。

### 🔹 厂商差异化 FGS 限制策略
小米/华为/OPPO/vivo 等厂商在 AOSP 基础上对 FGS 的额外限制层（ Kill 时机、白名单差异、配额叠加）。

### 🔹 FGS 性能指标与可观测性
FGS 启动延迟、执行时长分布、被系统 Kill 的原因分布与诊断方法。

## 扩展

### 🔸 FGS 与 WorkManager 的选择决策树
什么场景该用 FGS、什么场景该用 WorkManager，性能/功耗 tradeoff 分析。

### 🔸 Android 17 FGS 与 Predictive Back 的交互
前台服务运行时 Predictive Back 手势的性能影响。

<!-- outline-end -->

> 本节内容待加工。
