---
title: "Adaptive Battery 与 App Standby Bucket 协同机制"
chapter: "5.21"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [adaptive-battery, app-standby-bucket, power-management, jobscheduler, quotacontroller]
related_chapters: ["5.8", "5.10", "5.17", "11.2", "25.2", "25.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-19"
gap_source: "DeepResearch 素材驱动 + AOSP 源码结构"
last_verified: "2026-06-19"
last_verified_against: "android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppIdleHistory.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/AppStateTrackerImpl.java"
  - type: research
    path: "DeepResearch/2026-06-18-adaptive-battery-app-standby-coordination.md"
---

# 5.21 Adaptive Battery 与 App Standby Bucket 协同机制

<!-- outline-start -->
## 要点

### 🔹 Adaptive Battery 的本质：写一次、读三方的中间层

Adaptive Battery 在 AOSP 中不是一个独立服务，而是一套写入接口 + 衰减契约。ML 预测把"哪一类后台任务该被压"翻译成具体桶索引（STANDBY_BUCKET_ACTIVE 到 STANDBY_BUCKET_RARE），再由三套独立的资源调度器读取并执行限制。

已有的 5.8 后台执行限制 与 25.2 后台功耗治理 讲了开发者侧"桶是什么、怎么查、怎么适配"。本节回答系统侧的问题：桶值从哪来、谁写入、何时过期、三方消费者如何读取。

### 🔹 桶值写入：REASON_MAIN_PREDICTED 与 12 小时保质期

`AppStandbyController.setAppStandbyBuckets()` 按 calling UID 分三类写入 reason：
- `REASON_MAIN_FORCED_BY_USER`（shell / Settings）：用户锁定，预测不可覆盖
- `REASON_MAIN_FORCED_BY_SYSTEM`（Core 系统）：系统锁定，预测不可覆盖
- `REASON_MAIN_PREDICTED`（其他调用方 = ML 预测透传）：可被超时或 usage 事件刷新

predicted 桶值的"保质期"是 `DEFAULT_PREDICTION_TIMEOUT = 12 * ONE_HOUR`（生产构建）。超过 12 小时没人刷新预测，桶值回退到 `getBucketForLocked()` 的纯时间阈值算法——这个路径完全不读 `lastPredictedBucket`，只看"距离上次使用过了多久"。

### 🔹 衰减契约：evaluateBucketsLocked 决策树

`AppStandbyController.evaluateBucketsLocked()` 在每次评估时判断：
- 如果旧 reason ∈ {DEFAULT, USAGE, TIMEOUT} 或 prediction 已超时（predictionLate）
  - 且 lastPredictedBucket 仍在 [ACTIVE, RARE] 区间 → 用预测值，reason 标 REASON_SUB_PREDICTED_RESTORED
  - 否则 → 回退到时间阈值，reason 标 REASON_MAIN_TIMEOUT
- 如果旧 reason 是 FORCED_BY_USER 或 FORCED_BY_SYSTEM → 预测不能覆盖，直接返回

这套设计保证了 ML 预测只是"建议"，用户/系统强制操作的优先级永远高于算法。

### 🔹 三方消费者：桶值如何变成资源限制

桶值稳定后，三个独立的系统组件同时读取：

**消费者 1：QuotaController（Job / EJ 配额）**
- 入口：`JobSchedulerService.standbyBucketForPackage()` → `QuotaController.isWithinQuotaLocked()`
- 按桶分配滚动窗口内的 Job 数量、EJ 时长、Session 数量
- FREQUENT 桶约 200 Job/12h，RARE 桶约 48 Job/24h，RESTRICTED 桶约 10 Job/24h

**消费者 2：AppStateTrackerImpl（EXEMPTED 集管理）**
- 入口：`AppStateTrackerImpl.StandbyTracker.onAppIdleStateChanged()`
- ACTIVE / EXEMPTED 桶的 App 被加入 `mExemptedBucketPackages`，享受 RIL 数据通道豁免、QuotaController 前台旁路等特权
- RESTRICTED 桶的 App 在某些路径会被额外限制

**消费者 3：PowerManagerService（节电模式联动）**
- `isPowerSaveMode()` 叠加桶值影响——低电量模式下非 ACTIVE 桶的 App 会被进一步压缩
- `mForceAllAppStandbyForSmallBattery`（Android 16+）在小电量设备上强制所有 App 进入 standby 管控

### 🔹 桶值不可逆覆盖规则

predicted reason 不能覆盖 FORCED reason。`AppStandbyController` 在 `reportEvent` 路径中检查：如果当前桶值是被用户或系统强制的（FORCED_BY_USER / FORCED_BY_SYSTEM），ML 预测直接 return，不修改桶值。这解释了为什么 `adb shell am set-standby-bucket` 设置的桶位在 12 小时内不会被 Adaptive Battery 推翻。

### 🔹 Android 9-17 版本演进

- Android 9 (API 28)：引入五桶模型（ACTIVE/WORKING_SET/FREQUENT/RARE/EXEMPTED）
- Android 12 (API 31)：新增 RESTRICTED 桶，收紧 EXEMPTED 条件
- Android 13 (API 33)：RESTRICTED 自动降级阈值从 45 天缩至 8 天
- Android 14 (API 34)：顶层 EJ reward 时间块从 30s 改为 5min
- Android 16 (API 36)：prediction timeout 可由 DeviceConfig 改写；小电量设备强制 standby
- Android 17 (API 37)：AppStandbyController 迁移到 apex/jobscheduler/service/，调用方分类逻辑稳定

### 🔹 开发者诊断路径

如何判断 Adaptive Battery 是否在影响你的 App：
- `adb shell am get-standby-bucket <package>`：查看当前桶值
- `adb shell dumpsys usagestats appstandby`：查看桶值历史和 reason
- `adb shell dumpsys usagestats` 输出中的 `adaptivebat=<provider_pkg>`：确认 OEM 是否启用了 ML provider
- `UsageStatsManager.getAppStandbyBucket()`：运行时查询
- `adb shell am set-standby-bucket <package> <bucket>`：强制设置（测试用），设置后 ML 不可覆盖

## 扩展

### 🔸 OEM 自定义 ML Provider

AOSP 主线不包含完整的 Usage Ranker ML 模型实现。OEM（如 Pixel）通过私有 provider 接口提供预测。`AppStandbyController.dump()` 中的 `adaptivebat=<provider_pkg>` 字段可用于确认设备是否启用了真实 ML provider。不同 OEM 的预测精度和频率可能有显著差异，这解释了为什么同一 App 在不同设备上的后台行为可能不同。

### 🔸 与 Doze 模式的叠加关系

App Standby Bucket 和 Doze 是两套独立的管控通道：
- Doze 基于 `DeviceIdleController`，管的是设备级 idle / maintenance 状态
- App Standby Bucket 基于 `AppStandbyController`，管的是应用级后台配额
- 两者叠加：Doze maintenance 期间仍按桶值限制 Job 执行频率
- 详见 5.8 后台执行限制与优化

### 🔸 QuotaController 配额计算细节

QuotaController 使用的不是简单的固定值，而是基于多个参数的动态计算：
- 滚动窗口大小（默认 12h 或 24h，取决于桶位）
- 充电状态下的豁免规则
- 顶层 App 启动后的 reward 时间块
- EJ（Expedited Job）的独立配额池
- rate limit（默认 20 Job/min）与桶位限制叠加

### 🔸 待验证与待深入

- ML 模型具体架构未在 AOSP 源码中确认，属于厂商私有实现
- `mAppStandbyScreenThresholds` / `mAppStandbyElapsedThresholds` 的具体数值依赖设备 `xml/usage_stats.xml` 配置
- QuotaController 的 rate limit 与桶位限制的叠加效应未在现有材料中量化建模

<!-- outline-end -->

> 本节内容待加工。
