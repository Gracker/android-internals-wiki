---
title: "Android 17 Tare 经济模型与电池统计源码闭环"
chapter: "11.8"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [tare, battery, power, economy-model, batterystats, power-profile]
related_chapters: ["11.1", "11.5", "5.8", "25.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "素材驱动"
confidence: high
---

# 11.8 Android 17 Tare 经济模型与电池统计源码闭环

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Tare（Token-based Resource Economy）架构全景
- Tare 的设计目标：为系统资源（电池、网络、存储 I/O）建立经济模型，用"收入-支出"代替硬性限制
- 核心组件：Ledger（账本）、RewardPolicy（奖励策略）、SpendPolicy（消费策略）
- Tare 与传统 Doze/App Standby 的关系：互补而非替代
- AOSP 源码位置：frameworks/base/services/core/java/com/android/server/tare/

### 🔹 锚点 2：BatteryStatsService 与电量归因
- BatteryStatsService 的数据采集路径：kernel wakelock → BatteryStatsImpl → BatteryStatsService
- 模块化电量统计：CPU、网络、GPS、传感器、Wi-Fi/蓝牙扫描各有独立统计器
- PowerProfile 的角色：将硬件活动时间转换为 mAh 估算值
- 应用级电量归因的精度边界：共享硬件（如 GPU、modem）的归因误差

### 🔹 锚点 3：Tare 经济模型如何影响后台任务调度
- Tare 的"账户"概念：每个应用有一个 Ledger，记录"余额"
- 余额的来源：用户交互（打开应用）→ 获得奖励；空闲时段 → 余额衰减
- 余额的消费：执行后台任务、发送推送、下载文件 → 扣除相应 token
- 与 JobScheduler 的集成：JobScheduler 在 Tare 中查询余额后决定是否执行任务

### 🔹 锚点 4：Perfetto 中观察 Tare 行为
- Tare 相关的 atrace tag：tare、battery_stats
- 如何通过 Perfetto SQL 查询应用的 Tare 余额变化
- BatteryStats dumpsys 的关键字段解读
- Tare 决策日志与 JobScheduler 调度日志的关联分析

### 🔹 锚点 5：Android 17 中 Tare 的行为变更
- Android 17 对 Tare 的调整：余额公式变化、新增消耗品类（如 AI 推理任务）
- 与 Android 17 Excessive CPU Kill 的协同：Tare 扣费 + 系统直接终止
- Tare 对 FGS（前台服务）的影响
- 开发者可观察的 Tare API：无法直接查询余额，但可通过 JobScheduler 回调感知

## 扩展

### 🔸 扩展点 1：Tare 调试与优化实战
- dumpsys tare 输出解读
- 如何判断应用被 Tare 限流
- 减少 Tare 消耗的编码实践

### 🔸 扩展点 2：Tare 与 OEM 定制的关系
- OEM 如何定制 RewardPolicy 和 SpendPolicy
- 不同厂商 Tare 策略差异对应用行为的实际影响

<!-- outline-end -->

> 本节内容待加工。
