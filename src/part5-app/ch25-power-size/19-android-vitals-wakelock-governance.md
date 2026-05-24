---
title: "Android Vitals 过度 WakeLock 指标与治理"
chapter: "25.19"
section: "25.19"
status: draft
applicable_versions: "Android 8 (API 26) - Android 16 (API 36); Android Vitals wake lock metric updated 2026-05"
tags: [power, wakelock, android-vitals, battery, play-console]
related_chapters: ["11.5", "25.2", "25.3", "25.13", "25.14", "26.3", "26.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/Clippings结构参考/已有队列缺口"
gap_score: 17
material_count: 5
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md]"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official-blog
    path: "https://developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/set"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
---

# 25.19 Android Vitals 过度 WakeLock 指标与治理

<!-- outline-start -->
## 要点

### 🔹 指标口径：Android Vitals 到底统计什么
围绕非豁免 partial wake lock、后台/前台服务、熄屏、24 小时累计时长、28 天会话占比建立口径表，区分单次持有时长、应用会话占比和 Play 质量阈值。

### 🔹 豁免边界：audio、location、JobScheduler 用户发起 API
解释 Android Vitals 对部分有用户收益场景的豁免规则，拆开音频播放、定位、用户发起数据传输、Foreground Service 与手动 `PowerManager.WakeLock` 的责任边界。

### 🔹 归因链路：从 wake lock 名称到代码调用点
覆盖 wake lock 命名规范、PII / 混淆导致的 `_UNKNOWN`、第三方 SDK 间接持锁、WorkSource 归因和 BatteryStats 侧记录，说明 Play Console 只能给出问题入口，不能替代端侧堆栈采集。

### 🔹 本地验证：dumpsys、Batterystats 与 Battery Historian
建立开发阶段验证流程：重置 batterystats、构造后台熄屏场景、采集 bugreport、读取 partial wakelock、核对充电状态和屏幕状态，避免把前台活跃耗电误判为 Vitals 风险。

### 🔹 治理策略：替代 API、超时释放和异常兜底
按「不要持锁」「缩短持锁」「可观测持锁」三层处理：优先使用系统托管 API，手动持锁必须设置 timeout，释放路径覆盖异常、取消、进程退出和生命周期切换。

### 🔹 线上监控：比 Vitals 多拿现场
参考 Clippings 中的耗电监控结构，补充端侧采集：申请堆栈、释放堆栈、持锁时长、前后台状态、充电状态、电量、任务类型、SDK 来源，用内部阈值提前发现 Vitals 风险。

### 🔹 版本与分发影响：2026 Play 质量信号
整理 2025/2026 Android Vitals wake lock 指标的分发影响、beta 状态、店铺警告风险，以及国内渠道缺少 Vitals 数据时如何用自建指标替代。

## 扩展

### 🔸 Stuck partial wake lock 与 excessive wake lock 的差异
补充长时间未释放和累计时长过高两类问题的诊断差异。

### 🔸 Alarm / Wi-Fi scan / background network 的联合耗电规则
把 WakeLock 与 Android Vitals 其他电量指标放在同一套后台耗电治理框架中处理。

### 🔸 厂商后台限制与 Play Vitals 阈值的冲突
讨论 OEM 省电策略、白名单、前台服务展示和 Play 质量阈值之间的差异。

<!-- outline-end -->

> 本节内容待加工。
