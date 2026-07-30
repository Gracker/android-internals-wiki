---
title: "TARE 退场：Android 17 后台任务预算与电量归因"
chapter: "11.8"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [tare, battery, power, app-standby, jobscheduler, quota, batterystats]
related_chapters: ["11.1", "11.5", "5.8", "25.12", "25.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
drafted_date: "2026-06-04"
drafted_by: "openclaw-task2a"
gap_source: "素材驱动"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-13.0.0_r1 / android-14.0.0_r1 历史实现；TARE 删除提交 4a98dd235a70；AOSP android-17.0.0_r1；Android 17 / API 37 SDK 与官方功耗文档 2026-07"
confidence: high
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/4a98dd235a708115db41e722776eff3ef9ed09fe"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/JobStatus.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/BackgroundJobsController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/FlexibilityController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/PendingJobReasonsInfo.java"
  - type: aosp-historical
    path: "android-14.0.0_r1/apex/jobscheduler/service/java/com/android/server/tare/InternalResourceService.java"
  - type: aosp-historical
    path: "android-14.0.0_r1/apex/jobscheduler/service/java/com/android/server/tare/Analyst.java"
  - type: aosp-historical
    path: "android-14.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/controllers/TareController.java"
  - type: aosp-historical
    path: "android-14.0.0_r1/apex/jobscheduler/framework/java/android/app/tare/EconomyManager.java"
  - type: official
    path: "https://developer.android.com/topic/performance/power/power-details"
  - type: official
    path: "https://developer.android.com/topic/performance/appstandby"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobScheduler"
  - type: research
    path: "DeepResearch/2026-05-31-android-17-battery-tare-economic-model.md"
  - type: research
    path: "DeepResearch/2026-05-23-android17-jobscheduler-excessive-cpu-powercheck.md"
---

# 11.8 TARE 退场：Android 17 后台任务预算与电量归因

Android 17 不包含 TARE（The Android Resource Economy）。在 `android-17.0.0_r1` 中找不到 `com.android.server.tare`、`TareController`、`android.app.tare.EconomyManager` 或 `resource_economy` 服务。JobScheduler 当前使用 App Standby、`QuotaController`、后台限制、Doze、显式约束和 flexibility policy 管理后台任务。

这个版本边界值得单独成章。网上仍有不少资料把 ARC 余额、`dumpsys tare` 和 `EconomyManager` 写成 Android 17 能力；按这些资料排查，只会寻找已经删除的服务。TARE 的设计仍有学习价值，但它只能放在 Android 13—14 的历史源码中阅读。

## 11.8.1 结论表：哪些说法已经失效

| 说法 | Android 17 核查结果 | 对应证据 |
|---|---|---|
| Android 17 用 TARE 控制 JobScheduler | 错误 | `android-17.0.0_r1` 无 `tare/` 与 `TareController` |
| BatteryUsageStats 的每 UID 耗电决定 ARC 余额 | 错误 | 历史 TARE 只用全局 screen-off discharge 辅助调节供给 |
| `TareEconomicManager` 是服务入口 | 类不存在 | 历史入口是 `InternalResourceService` |
| `AppBudgetManager` 提供毫秒预算 | 类与所列方法不存在 | 历史实现使用 `Agent`、`Ledger`、`EconomicPolicy` |
| API 34 公开 `EconomyManager` 预算接口 | 错误 | Android 14 源码中的类标记为 `@hide`、`@TestApi`，且没有预算 API |
| Android 17 可用 `dumpsys tare` 查询 ARC | 错误 | 对应 Binder 服务和 dump 入口已删除 |
| `JobDebugInfo` 提供 TARE 原因 | 类不存在 | API 37 使用 `getPendingJobReasonStats()` |
| Perfetto 有稳定的 `tare` / `battery_stats` atrace 类别 | 无此平台合同 | Android 17 应用公开接口与 JobScheduler dump 更可靠 |

这些错误不属于措辞差异。类名、服务、控制器和调度约束都已经变化，调试流程必须按 Android 17 重建。

## 11.8.2 TARE 在历史源码里是什么

已核对的 release tag 中，TARE 出现在 `android-13.0.0_r1` 与 `android-14.0.0_r1`；`android-12.0.0_r1` 尚无对应目录。Android 14 的实现默认关闭：

- `EconomyManager.DEFAULT_ENABLE_TARE_MODE` 为 `ENABLED_MODE_OFF`；
- `EconomyManager` 标记为 `@hide` 和 `@TestApi`；
- JobScheduler 与 AlarmManager 都保留了可切换到 TARE policy 的内部路径；
- TARE 可以运行在 on、off 或 shadow 模式。

因此，TARE 从未成为普通应用可依赖的 SDK 合同。它是一套平台内部实验设计，设备是否启用、采用哪组价格和奖励，都不能由三方应用假定。

### 历史组件

Android 14 的实现主要由下面几部分组成：

| 组件 | 历史职责 |
|---|---|
| `InternalResourceService` | 维护系统级状态、供给上限、包状态和内部服务 |
| `Agent` | 处理 action bill、余额变化、负担能力监听 |
| `Ledger` / `Scribe` | 保存 package 账本、交易记录和持久化状态 |
| `EconomicPolicy` | 定义 action 的 cost-to-produce、base price 与 reward |
| `TareController` | 把 JobScheduler 的 job 转成 action bill，维护 wealth constraint |
| `AlarmManagerEconomicPolicy` | 为不同类型的 alarm 定义历史价格 |
| `Analyst` | 统计 TARE 交易与整机后台电池变化，辅助调节供给 |

ARC 是内部记账单位，底层还能细分为 cake。Job 或 alarm 对应一组 action；系统根据 action 的生产成本、基础价格和状态修正计算费用。用户交互、通知交互、widget 交互等事件可以产生 reward。

### 历史设计没有使用“每 UID mAh 直接扣 ARC”

这条边界常被误写。Android 14 的 `Analyst` 通过 `IBatteryStats` 读取：

- screen-off realtime；
- screen-off discharge mAh；
- 电池电量变化。

`InternalResourceService` 把 screen-off discharge 当成后台耗电代理，用于估算后台续航并调节全局 consumption limit。源码中还留有“后续获取更准确后台耗电”的 TODO。

TARE 对具体应用的扣费来自调度 action 和 policy，不是从 `BatteryUsageStats` 读取某个 UID 的 mAh 后换算 ARC。BatteryStats 提供的是全局校准信号，作用与逐应用结算不同。

## 11.8.3 TARE 何时被删除

AOSP 提交 `4a98dd235a708115db41e722776eff3ef9ed09fe` 的标题为 `JobScheduler: remove TARE`，作者日期为 2024 年 3 月 22 日，提交日期为 3 月 29 日。该提交一次移除了：

- `EconomyManager` 与 `IEconomyManager`；
- `InternalResourceService` 和整个 `com.android.server.tare`；
- JobScheduler 的 `TareController` 与 `CONSTRAINT_TARE_WEALTH`；
- AlarmManager 的 TARE policy；
- `resource_economy` system service 注册；
- TARE 配置、测试和 dump 路径。

删除提交还恢复了 `QuotaController` 的持续生效。旧代码曾在启用 TARE policy 时关闭时间窗口配额；删除后，JobScheduler 不再在两套预算模型之间切换。

按 release tag 检查，边界如下：

| Release tag | TARE 服务端 | `TareController` | `EconomyManager` |
|---|---:|---:|---:|
| `android-12.0.0_r1` | 无 | 无 | 无 |
| `android-13.0.0_r1` | 有 | 有 | 有，隐藏 API |
| `android-14.0.0_r1` | 有，默认关闭 | 有 | 有，隐藏 / Test API |
| `android-15.0.0_r1` | 无 | 无 | 无 |
| `android-16.0.0_r1` | 无 | 无 | 无 |
| `android-17.0.0_r1` | 无 | 无 | 无 |

讲版本演进时可以保留 ARC、reward 和 action bill；讲 Android 15—17 调度行为时应结束 TARE 分支。

## 11.8.4 Android 17 的后台任务控制面

`JobSchedulerService` 在 Android 17 中注册的控制器包括 `PrefetchController`、`FlexibilityController`、`ConnectivityController`、`TimeController`、`IdleController`、`BatteryController`、`StorageController`、`BackgroundJobsController`、`ContentObserverController`、`DeviceIdleJobsController`、`QuotaController` 和 `ComponentController`。

对应用最常见的等待原因可以分成五组：

| 控制面 | Android 17 源码入口 | 回答的问题 |
|---|---|---|
| 应用显式约束 | Battery / Connectivity / Idle / Storage / Time controllers | 充电、网络、空闲、存储和时间条件是否满足 |
| Doze 与设备状态 | `DeviceIdleJobsController` | 设备空闲状态是否推迟普通 job |
| 应用后台资格 | `BackgroundJobsController` | 用户限制、AppOps、包 stopped 状态是否禁止后台运行 |
| 时间与次数配额 | `QuotaController` | 当前 standby bucket 的 regular / expedited quota 是否耗尽 |
| 机会调度 | `FlexibilityController` | JobScheduler 是否在等待更合适的充电、空闲或网络组合 |

`JobStatus` 的隐式约束包含 `CONSTRAINT_WITHIN_QUOTA`、`CONSTRAINT_BACKGROUND_NOT_RESTRICTED`、`CONSTRAINT_DEVICE_NOT_DOZING` 和 `CONSTRAINT_FLEXIBLE`。Android 17 已没有 `CONSTRAINT_TARE_WEALTH`。

### `QuotaController` 记录什么

`QuotaController` 以 user/package 和 App Standby Bucket 为维度维护：

- regular job 的执行时间；
- timing session；
- 窗口内 job 与 session 次数；
- expedited job（EJ）的独立执行时间；
- top-app、用户交互、临时 allowlist 等对 EJ quota 的影响；
- 配额重新可用的时刻。

它依靠调度与使用事件记账，没有读取 UID 的 mAh。`PENDING_JOB_REASON_QUOTA` 表示当前 quota 已消耗完，不能翻译成“ARC 余额不足”。

### Android 17 官方近似配额

官方文档将这些值标为近似指导值，设备状态、compat change、配置更新、充电状态和 OEM 策略都可能改变结果：

| Standby bucket | Regular job 指导值 | Expedited job 指导值 |
|---|---|---|
| Active | 最多约 20 分钟 / 滚动 60 分钟 | 最多约 30 分钟 / 滚动 24 小时 |
| Working set | 最多约 10 分钟 / 滚动 4 小时 | 最多约 15 分钟 / 滚动 24 小时 |
| Frequent | 最多约 10 分钟 / 滚动 12 小时 | 最多约 10 分钟 / 滚动 24 小时 |
| Rare | 最多约 10 分钟 / 滚动 24 小时 | 最多约 10 分钟 / 滚动 24 小时 |
| Restricted | 每天一个最长约 10 分钟的批次 | 最多约 5 分钟 / 滚动 24 小时 |

Android 16 起，Active bucket、前台服务期间和用户设为 unrestricted 的应用也进入新版 runtime quota 规则。Android 17 延续这套方向。WorkManager 在应用不可见时通常使用 JobScheduler，因此 Worker 也会受到这些资源限制。

表格不能当成准点执行保证。JobScheduler 还会评估设备状态、并发槽位、thermal、内存压力、显式约束和优化策略。

## 11.8.5 Flexibility policy 与 quota 的差别

`FlexibilityController` 会利用充电、battery-not-low、idle 和 connectivity 等机会条件安排可延迟工作。随着 job 生命周期推进，它会逐步放宽所需的灵活约束，防止任务一直等待理想设备状态。

两类等待在 API 中使用不同原因：

- quota 耗尽：`PENDING_JOB_REASON_QUOTA`；
- 等待 JobScheduler 选择更合适时机：`PENDING_JOB_REASON_JOB_SCHEDULER_OPTIMIZATION`。

前者需要等待配额恢复或应用状态变化；后者可能在机会条件出现、生命周期推进或调度资源释放后变化。只看到 `ENQUEUED` 或“尚未进入 `onStartJob()`”时，无法判断是哪一类。

## 11.8.6 BatteryStats 与 JobScheduler 的真实关系

Android 17 的 BatteryStats 负责记录 CPU、wakelock、网络、传感器、job 等活动，并通过 power calculators / power stats processors 生成组件与 UID 归因。硬件 consumed-energy 数据可用时，部分组件会使用测量值；缺失时使用 `PowerProfile` 和活动时间估算。详见 11.1、11.2 节。

JobScheduler 会把 job 的启动、停止和原因记入系统统计，BatteryStats 因而能观察后台任务活动。反方向的控制路径不同：当前 `QuotaController`、`BackgroundJobsController` 和 `FlexibilityController` 没有用 `BatteryUsageStats` 的 UID mAh 计算 job 余额。

可以把两边的职责写成：

```text
JobScheduler 控制器
  ├─ 输入：standby bucket、执行时间、约束、设备状态、用户限制
  └─ 输出：等待、开始、停止、停止原因

BatteryStats / BatteryUsageStats
  ├─ 输入：job 与其他组件的活动、硬件能量或 power profile
  └─ 输出：历史、组件和 UID 归因
```

这段图用于区分“调度决策”与“耗电归因”。两边会共享事件和设备状态，但 Android 17 没有历史 TARE 那种 ARC 经济账户。

`BatteryUsageStats`、`BatteryUsageStatsQuery` 在 `android-17.0.0_r1` 中仍标记为 `@hide`。普通应用不能使用原文中虚构的 `BatteryManager.getBatteryUsageStats(...)` 代码。应用侧诊断应使用公开 JobScheduler 原因 API、Android Studio Power Profiler、Battery Historian、Perfetto、Android vitals 和业务遥测。

## 11.8.7 用 API 37 定位 Job 为什么等待

Android 17 的公开接口已经能回答大部分应用侧问题：

| API | 引入版本 | 返回内容 |
|---|---:|---|
| `getPendingJobReason(jobId)` | API 34 | 一个等待原因 |
| `getPendingJobReasons(jobId)` | API 36 | 当前可能存在的全部原因 |
| `getPendingJobReasonsHistory(jobId)` | API 36 | 有长度上限的原因变化历史 |
| `getPendingJobReasonStats(jobId)` | API 37 | 每种原因累计持续时间 |

下面的 Kotlin 片段用于在 Android 17 上记录各等待原因的累计时间：

```kotlin
@RequiresApi(37)
fun logPendingReasonStats(
    jobScheduler: JobScheduler,
    jobId: Int,
) {
    jobScheduler.getPendingJobReasonStats(jobId)
        .forEach { (reason, duration) ->
            Log.d(
                "JobDiag",
                "jobId=$jobId reason=$reason pendingMs=${duration.toMillis()}",
            )
        }
}
```

同一时段可以同时存在多个原因，因此各项 duration 相加可能超过 job 的总等待时间。统计不会跨重启持久化，job 成功完成或取消后也会清除；应用应在发现延迟时采集，而不是等任务结束后追查。

`JobDebugInfo` 不是 API 37 类。若旧文、SDK 示例或代码审查意见出现这个名字，应改为 `PendingJobReasonsInfo` 和上表中的查询方法。

## 11.8.8 dumpsys 与 shell 调试

下面命令用于保存 standby bucket、job 粗粒度状态、完整 JobScheduler dump 和同期 BatteryStats：

```bash
adb shell am get-standby-bucket com.example.app
adb shell cmd jobscheduler get-job-state com.example.app 42
adb shell dumpsys jobscheduler > jobscheduler.txt
adb shell dumpsys batterystats --charged > batterystats.txt
```

`get-job-state` 只返回 pending、active、ready、waiting 等状态组合；控制器细节要从完整 dump 和公开 pending-reason API 补充。BatteryStats 文件用于对照任务是否运行及同期组件活动，不能用来读取 ARC。

`cmd jobscheduler run -f` 会绕过部分技术约束，适合验证 JobService 代码能否启动，不适合证明自然调度会按时发生。要测试约束已满足时的行为，可使用 `run -s`。测试命令改变了系统决策条件，报告中应注明。

在 Android 17 上不要把 `dumpsys tare`、`tare` atrace slice 或 ARC ledger 当成必备证据。AOSP 对应服务已经不存在。若某个 OEM build 仍暴露同名私有服务，需要按该厂商源码和版本单独分析。

## 11.8.9 工程策略

### 调度语义

- 只为可延迟、可重试的工作使用 JobScheduler / WorkManager；
- 用户正在等待的数据传输，评估 user-initiated data transfer job 或合适的前台机制；
- 不依赖某个精确执行时刻；
- 为网络、充电、idle 等约束提供业务理由，过多约束会缩短可运行窗口。

### 任务实现

- job 要幂等，进程被杀或 `onStopJob()` 后可以安全重试；
- 长队列应分批，并保存可恢复进度；
- 网络和服务端错误使用有上限的指数退避；
- 记录 enqueue、start、stop、complete 时间以及 `JobParameters.getStopReason()`；
- 避免短周期反复 schedule、cancel 或立即 retry。

### 线上观测

- 上报 standby bucket 时遵守隐私和采样限制；
- 分开统计“未获得运行机会”“运行后失败”“运行中被停止”；
- Android 17 上采集 `getPendingJobReasonStats()`，低版本按 API 能力降级；
- 按机型、系统版本、充电状态和用户电池设置分组；
- 不用“厂商 ARC 更少”解释 OEM 差异，应以公开原因、dump 和复现实验为证据。

## 11.8.10 版本迁移清单

- [ ] 删除 Android 15—17 使用 TARE 的架构图
- [ ] 删除 `TareEconomicManager`、`AppBudgetManager` 与虚构预算方法
- [ ] 删除普通应用调用 `EconomyManager` 的示例
- [ ] 删除“每 UID BatteryUsageStats 决定 ARC”的表述
- [ ] 将 `JobDebugInfo` 改为 pending-reason API
- [ ] 将 `dumpsys tare` 改为 `dumpsys jobscheduler`
- [ ] 把 `PENDING_JOB_REASON_QUOTA` 解释为 JobScheduler quota
- [ ] 保留 Android 13—14 的 ARC 设计时标注隐藏、默认关闭和历史版本
- [ ] Android 17 的数字以官方近似值和设备实测为准
- [ ] WorkManager 排障包含 JobScheduler 资源限制

## 小结

TARE 是 Android 13—14 AOSP 中一套默认关闭的内部经济模型，2024 年 3 月已从 JobScheduler、AlarmManager 和 system service 中删除。Android 15、16、17 都没有 ARC 账本，也没有供普通应用使用的 `EconomyManager` 预算接口。

Android 17 的后台任务预算来自 App Standby 与 `QuotaController`，再叠加后台限制、Doze、显式约束、flexibility policy 和系统资源状态。BatteryStats 继续记录与归因耗电，却不按 UID mAh 给 job 扣 ARC。排查 job 延迟时，应查看 pending-reason API、standby bucket、JobScheduler dump 和任务停止原因。

## 参考资料

- [AOSP 提交：JobScheduler: remove TARE](https://android.googlesource.com/platform/frameworks/base/+/4a98dd235a708115db41e722776eff3ef9ed09fe)
- [Android Developers：Power management resource limits](https://developer.android.com/topic/performance/power/power-details)
- [Android Developers：App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Android Developers：JobScheduler API](https://developer.android.com/reference/android/app/job/JobScheduler)
- AOSP `android-14.0.0_r1`：`InternalResourceService.java`、`Analyst.java`、`TareController.java`、`EconomyManager.java`
- AOSP `android-17.0.0_r1`：`JobSchedulerService.java`、`JobStatus.java`、`QuotaController.java`
- AOSP `android-17.0.0_r1`：`BackgroundJobsController.java`、`FlexibilityController.java`、`PendingJobReasonsInfo.java`
