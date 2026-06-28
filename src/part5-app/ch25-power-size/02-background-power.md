---
title: "后台功耗治理"
chapter: "25.2"
section: "25.2"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers power / background work docs + Clippings structure references"
confidence: medium-high
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: official
    path: "https://developer.android.com/topic/performance/appstandby"
  - type: official
    path: "https://developer.android.com/topic/performance/power/power-details"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/optimize-battery"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/service-types"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/timeout"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/fgs-types-required"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start"
  - type: official
    path: "https://developer.android.com/about/versions/oreo/background-location-limits"
  - type: official
    path: "https://developer.android.com/develop/sensors-and-location/location/battery/scenarios"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/usage/UsageStatsManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/ServiceInfo.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [background-power, doze, app-standby, bucket, workmanager, jobscheduler, foreground-service, location-power]
related_chapters: ["25.1", "25.3", "25.4", "25.5", "25.13", "5.8", "11.2"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_at: "2026-05-15T07:22:00+08:00"
last_task2b_lite_at: "2026-06-28"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_reviewed_date: "2026-05-14"
last_task6_at: "2026-05-14T15:12:00+08:00"
last_task6_audit: "2026-06-28"
last_task6_review_log: logs/review/2026-05-14-15-review.md
task6_review_notes: "L1/L2 轻量修复 4 处；写作质量通过，无 Task6 回炉项，送 Task9 技术复审。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-28"
last_task9_at: "2026-06-28T11:50:29+08:00"
task2b_verified_at: "2026-06-26T07:27:19+08:00"
task2b_verify_result: "stale-state-fixed: task6_state revisiting→reviewed (already finalized)"
last_task9_review_log: logs/deep-review/2026-06-28-11-deep-review.md
task9_review_notes: "2026-06-28 Task9：auto-fixed。P0 2 / P1 1 / P2 1 均为局部修复；修正 UsageStatsManager bucket 常量、Android 16 Job 配额口径、FGS timeout 版本边界，并补 §25.13 交叉引用；回到 Task6 复审。"
last_task9_autofix_at: "2026-06-28"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-25
---

# 后台功耗治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 后台执行限制演进（Doze / App Standby / Bucket）
- 🔹 后台任务最佳实践
- 🔹 前台服务的正确使用与 Android 14+ 限制
- 🔹 后台定位与传感器管控

### 扩展（可选深入）

- 🔸 后台任务回归守门

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解后台功耗治理

本节讲 App 侧怎么把后台耗电收住，不重复 Doze、App Standby、Job 配额的系统实现。后台执行限制的版本演进和 AOSP 入口见 §5.8；App 耗电模型、WakeLock、Alarm、定位和 FCM 的横向策略见 §11.2；功耗诊断流程见 §25.1；FGS 超时与 Android 16 Job 配额细节见 §25.13。

后台功耗治理的任务很具体：把后台工作改成可延后、可合并、可取消、可观测。系统限制会延后 CPU、网络、Job、Alarm 和定位访问，但系统不会替业务判断“这次同步是否还需要做”“这段定位是否还能降频”“这个前台服务是否应该停掉”。这些判断仍要放回 App 架构里处理。

功耗治理和 CPU / 任务调度的工程原则其实是相通的：按用户可见度分层、把可延后的工作交给系统调度、把后台 CPU / 网络 / 定位采样压到最低——这和"按任务类型分线程池、预加载放到闲时、避免核心线程被 IO 和锁拖住"是同一套思路在不同方向上的应用。

## Android 后台执行限制演进（Doze / App Standby / Bucket）

Android 后台限制可以按“设备状态、App 使用状态、任务 API”三层理解。设备进入 Doze 后，系统延后后台 CPU 和网络活动，把普通 Job、同步适配器、常规 Alarm 推迟到 maintenance window；App 长时间未被用户使用后，App Standby 会限制后台网络；Android 9 引入 App Standby Buckets 后，限制还会跟随用户使用频率变化。 [已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby] [已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java]

| 版本节点 | 后台规则变化 | App 侧治理动作 |
|----------|--------------|----------------|
| Android 6.0 | Doze 和 App Standby 开始延后后台 CPU、网络、Job 和普通 Alarm | 可延后任务迁到 `JobScheduler` / WorkManager；即时消息优先用高优先级 FCM，不用轮询 |
| Android 8.0 | 后台 service 和后台定位频率被限制 | 长时间后台 service 改成调度任务；定位改成地理围栏、被动定位或批量位置 |
| Android 9 | App Standby Buckets 按使用频率限制资源 | 在测试里记录 bucket；不要把 rare / restricted 下的延迟误判成代码失败 |
| Android 12 | 后台启动前台服务受限，`ForegroundServiceStartNotAllowedException` 成为运行时风险 | 前台服务启动必须来自用户可见动作或官方豁免场景 |
| Android 14 | 前台服务类型和对应权限成为硬性约束 | Manifest 声明 `foregroundServiceType`，补对应 `FOREGROUND_SERVICE_*` 权限 |
| Android 16 | Job 执行配额与 App 状态关系更细；与前台服务并发执行的 Job 也会受运行时配额约束 | 把前台服务并发 Job 纳入功耗预算和超时监控，记录 `WorkInfo.getStopReason()` / `JobParameters.getStopReason()` 与 `JobScheduler#getPendingJobReasonsHistory()` |

Android Developers 的 power resource limits 文档把限制分成两种：一种是设备低功耗状态下延后执行，例如 Doze 期间普通 Job 和非精确 Alarm 延后；另一种是根据 standby bucket 限制唤醒频率和可运行时长，例如 rare bucket 下 Job 运行预算更少。WorkManager 在 App 不可见时通过 JobScheduler 执行，也会受到这些限制。 [已验证: 官方文档, developer.android.com/topic/performance/power/power-details]

AOSP 的入口能对应到这三层：`DeviceIdleController` 维护 idle / maintenance 状态，`AppStandbyController` 维护 bucket，`QuotaController` 根据 bucket 和 Job 状态计算剩余执行时间，`UsageStatsManager` 暴露 `STANDBY_BUCKET_ACTIVE`、`STANDBY_BUCKET_WORKING_SET`、`STANDBY_BUCKET_FREQUENT`、`STANDBY_BUCKET_RARE`、`STANDBY_BUCKET_RESTRICTED` 等常量。 [已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java] [已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java] [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/usage/UsageStatsManager.java]

到 App 实战层，判断顺序不要从“怎么绕过限制”开始，而是先问四个问题：

- 这件事是否由用户刚刚触发：用户点击通知、打开页面、发起上传，系统更容易给资源；定时轮询和静默同步会被当成普通后台工作。
- 这件事是否能延后：能延后的工作交给 WorkManager / JobScheduler，并声明网络、充电、空闲等约束。
- 这件事是否必须持续运行：只有播放、导航、通话、录音、健身记录这类用户感知强的场景才适合前台服务。
- 这件事是否能被取消或合并：用户退出场景后取消任务；多业务同步合并成一个周期；同一 UID 下避免重复拉起网络和定位。

## 后台任务最佳实践

后台任务要按用户可见度分层，而不是按业务模块分层。用户正在等待结果的工作走即时路径；用户不等结果但结果要可靠落盘的工作走 WorkManager；周期性同步和清理走带约束的延后任务；只为“保持活跃”的轮询应删除。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/optimize-battery]

| 任务类型 | 推荐 API | 功耗治理点 | 不建议的做法 |
|----------|----------|------------|--------------|
| 用户点击后立即上传、导出、下载 | 用户发起的数据传输 / 合适类型的前台服务 / WorkManager expedited | 有通知、有取消入口、有超时；失败后降级为普通后台任务 | 静默启动无类型前台服务 |
| 可靠但可延后的同步 | WorkManager `OneTimeWorkRequest` | 设置网络、充电、电量不低等约束；同类任务用 unique work 合并 | 每个业务各起一个周期线程 |
| 周期性刷新 | WorkManager periodic work / JobScheduler | 周期拉长；后台只同步摘要，详情等用户进入页面再拉 | 固定 5 分钟轮询网络 |
| 缓存清理、日志压缩、索引构建 | WorkManager / JobScheduler idle + charging 约束 | 只在空闲、充电、非低电量时运行；任务可中断 | App 启动后立刻扫全量文件 |
| 即时消息 | FCM | 只有会展示通知的消息使用 high priority，payload 带足展示信息 | 收到推送后再发起多轮网络请求 |

下面的 WorkManager 片段展示一个“可延后但要可靠执行”的后台同步。读者重点看三处：约束、unique work、退避策略。

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .setRequiresBatteryNotLow(true)
    .build()

val request = OneTimeWorkRequestBuilder<InboxSyncWorker>()
    .setConstraints(constraints)
    // import java.util.concurrent.TimeUnit
    .setBackoffCriteria(
        BackoffPolicy.EXPONENTIAL,
        30,
        TimeUnit.MINUTES
    )
    .addTag("inbox-sync")
    .build()

WorkManager.getInstance(context).enqueueUniqueWork(
    "inbox-sync",
    ExistingWorkPolicy.KEEP,
    request
)
```

这段代码把“网络不贵、设备电量不低、同一同步不重复排队”写进调度条件。它不会保证任务立刻执行；在 Doze、rare bucket、restricted bucket 或系统负载高时，执行时间仍由系统决定。治理时要记录 `WorkInfo.stopReason`、任务开始时间、结束时间和失败原因，不能只看业务日志里“没跑”。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/optimize-battery]

后台任务还有一个容易漏掉的成本：任务自身超时会影响系统对 App 的判断。Android Developers 明确建议追踪任务是否被停止及停止原因；Android 14 及以上，如果任务超时过多，系统可能把 App 放进 restricted standby bucket。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/optimize-battery]

工程上可以把后台任务接入统一表结构，至少记录以下字段：

| 字段 | 用途 |
|------|------|
| `task_name` | 区分业务任务，避免只看到 Worker 类名 |
| `trigger_source` | 标记来自用户动作、推送、周期任务、冷启动补偿还是重试 |
| `visible_to_user` | 判断是否允许走前台服务或 expedited work |
| `constraints` | 回放时知道任务为什么没到运行条件 |
| `standby_bucket` | 解释 Job / WorkManager 延迟和配额变化 |
| `stop_reason` | 区分超时、约束变化、取消、失败重试 |
| `network_bytes` / `cpu_time_ms` | 和 §25.1 的 BatteryStats / Perfetto 数据对齐 |

后台功耗治理最好和任务平台绑定，而不是靠各业务自觉。任务平台统一封装 WorkManager、前台服务、Alarm 和网络重试，才能统计“谁在后台唤醒设备”“谁在 restricted bucket 下仍然排队”“谁的重试把网络拉满”。这类治理属于应用架构问题，单点修一个 Worker 很难稳定。

## 前台服务的正确使用与 Android 14+ 限制

前台服务不是保活工具。Android 官方文档给出的定位是：用户期望立即执行或不中断的任务，并且必须通过持续通知让用户感知。Doze 文档也明确提醒，不要只为了避免 App 进入 idle 状态而启动前台服务。 [已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

Android 12 以后，targetSdk 31+ 的 App 从后台启动前台服务会被限制，只有用户可见状态切换、用户触发的精确 Alarm、地理围栏或 activity recognition 事件、部分启动广播和系统角色等豁免场景可以启动。涉及 camera、microphone、location、body sensor 等 while-in-use 权限的前台服务，即使命中部分豁免，也不能在后台直接创建。 [已验证: 官方文档, developer.android.com/develop/background-work/services/fgs/restrictions-bg-start]

Android 14 对前台服务再加一层类型约束。targetSdk 34+ 的 App 必须在 manifest 中为每个前台服务声明合适的 `android:foregroundServiceType`，并声明对应的 `FOREGROUND_SERVICE_*` 权限；调用 `startForeground()` 时缺类型会触发 `MissingForegroundServiceTypeException`，类型不匹配会触发对应运行时异常。AOSP `ServiceInfo` 中的 `FOREGROUND_SERVICE_TYPE_*` 常量也能看到这些类型和部分超时说明。 [已验证: 官方文档, developer.android.com/about/versions/14/changes/fgs-types-required] [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/content/pm/ServiceInfo.java]

这段 manifest 片段用于检查位置型前台服务的最小声明：服务类型、基础前台服务权限、类型权限、运行时位置权限必须同时满足。

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />

    <application>
        <service
            android:name=".TrackingForegroundService"
            android:exported="false"
            android:foregroundServiceType="location" />
    </application>
</manifest>
```

这段声明只能说明 App 有资格创建 location 类型前台服务，不代表任何后台时刻都能启动。targetSdk 31+ 仍要满足后台启动豁免；Android 11+ 如果从后台启动并访问位置，还需要 `ACCESS_BACKGROUND_LOCATION`；Android 14+ 的 while-in-use 权限检查会更早暴露问题。 [已验证: 官方文档, developer.android.com/about/versions/oreo/background-location-limits] [已验证: 官方文档, developer.android.com/develop/background-work/services/fgs/restrictions-bg-start]

前台服务治理可以按以下清单做 review：

- 服务命名和通知文案能让用户知道正在发生什么，例如“正在导航”“正在上传 3 个视频”，不要写“同步中”这种无法判断成本的文案。
- 启动入口来自用户动作或官方豁免场景，后台广播里不要直接兜底启动前台服务。
- 每个服务都有停止条件：任务完成、用户取消、超时、约束不满足、App 登出、权限撤销。
- `shortService` 有约 3 分钟上限；targetSdk 35+ 的 `dataSync` / `mediaProcessing` 在后台运行时按 24 小时窗口累计 6 小时，业务层要主动停止，不要等系统回调。
- 服务里再派生的 Worker / Job 仍要记入后台任务预算，Android 16 起不要把“前台服务正在跑”当成 Job 无配额的保证。

## 后台定位与传感器管控

后台定位是功耗治理里最容易引发用户体感的模块。Android 8.0 以后，后台 App 获取当前位置的频率被限制到每小时少数几次；Android 11 以后，从后台启动的前台服务要访问位置，必须拿到 `ACCESS_BACKGROUND_LOCATION`；Android 官方推荐把长时间区域触发需求改成 Geofencing API，把非实时需求改成批量位置或被动位置。 [已验证: 官方文档, developer.android.com/about/versions/oreo/background-location-limits]

定位策略按场景选择：

| 场景 | 推荐策略 | 功耗边界 |
|------|----------|----------|
| 地图、导航、运动记录，用户正在看结果 | foreground + 合理频率位置请求 | 通知常驻；用户停止场景后立即停 |
| 到店提醒、区域进入 / 离开 | Geofencing API | 设置合适的 loitering delay 和 notification responsiveness，不追求秒级 |
| 后台粗略画像、天气、城市级推荐 | 低功耗或被动位置 | 优先 `PRIORITY_NO_POWER`；不能满足时用 balanced / low power |
| 历史轨迹补点 | batched location | 接受批量回调延迟，避免持续高精度采样 |
| 只为刷新首页内容 | 不应后台定位 | 用户打开页面后再请求，或用上次位置缓存 |

下面的请求配置用于“后台粗略位置可选增强”这类场景。重点看优先级和间隔：它不要求 GNSS 持续工作，而是尽量复用系统或其他前台 App 已经计算好的位置。

```kotlin
val request = LocationRequest.Builder(
    Priority.PRIORITY_NO_POWER,
    30.minutes.inWholeMilliseconds
)
    .setMinUpdateIntervalMillis(10.minutes.inWholeMilliseconds)
    .setMaxUpdateDelayMillis(2.hours.inWholeMilliseconds)
    .build()

fusedLocationClient.requestLocationUpdates(
    request,
    pendingIntent
)
```

`PRIORITY_NO_POWER` 适合可接受机会主义结果的场景；如果业务要求持续高精度，应该把场景变成用户可见的前台任务，例如导航或运动记录，而不是在后台偷偷提高采样频率。Android Developers 的位置功耗指南也建议：长时间后台区域触发优先 geofencing，后台采样尽量使用 `PRIORITY_NO_POWER`，无法满足时再退到 balanced 或 low power，避免 sustained `PRIORITY_HIGH_ACCURACY`。 [已验证: 官方文档, developer.android.com/develop/sensors-and-location/location/battery/scenarios]

传感器治理要区分普通传感器和受 while-in-use 权限约束的身体传感器。Android 14+ 的 health 类型前台服务要求声明 `FOREGROUND_SERVICE_HEALTH`，并满足 `HIGH_SAMPLING_RATE_SENSORS` 或相应健康数据权限；Android 16 起，后台身体传感器读取还涉及 `READ_HEALTH_DATA_IN_BACKGROUND`。 [已验证: 官方文档, developer.android.com/develop/background-work/services/fgs/service-types]

工程治理里，定位和传感器统一按“采样预算”管：

- 每个业务声明采样目的、前后台状态、精度、最短间隔、最长持续时间。
- 页面不可见后降级采样；任务结束、权限撤销、账号退出时释放监听。
- 多业务复用一个位置源，避免首页、推荐、风控、埋点各自启动一套请求。
- 对 GPS / sensor / CPU / network 做同一时间窗口统计，异常时能回到 §25.1 的 BatteryStats 和 Perfetto 数据里定位。

## 后台任务回归守门

后台功耗问题不适合只靠线上报警。线下 review 能发现 API 用错，自动化测试能发现“某次改动后多跑了 30 分钟后台同步”。守门指标至少覆盖三类：后台唤醒次数、后台运行时长、后台资源消耗。

一套可执行的守门流程如下：

1. 选固定场景：冷启动后息屏 30 分钟、收到 5 条推送、弱网重试、退出登录、权限撤销。
2. 采集数据：`dumpsys batterystats --reset` 后跑场景，导出 bugreport，同时保留应用任务日志。
3. 对齐时间：按场景开始 / 结束时间框选 BatteryStats、Perfetto、任务平台日志。
4. 计算阈值：后台 Job 数、Worker 超时数、网络字节数、定位请求次数、前台服务持续时长。
5. 建守门：PR 或 nightly 中跑短场景，完整长场景放每日回归。

后台功耗治理的判断不要追求一个总分。总分很容易掩盖问题：某次版本 CPU 降了，但定位采样翻倍；网络少了，但前台服务持续时间变长。更稳的做法是按资源类型设预算，再把每一次唤醒和任务归到业务 owner。

## 小结

后台功耗治理的目标，是把后台工作放到合适的系统 API、用户可见度和采样预算里。Doze、App Standby、Bucket、前台服务类型和位置限制负责给系统设边界；App 侧要做的是任务分层、约束声明、停止条件、观测字段和回归守门。

读完本节后，再看 §25.3 的 WakeLock / Alarm 和 §25.4 的 WorkManager，就可以把 API 细节放回治理框架里判断：这次唤醒是否有用户价值、是否能延后、是否能合并、是否能被测试稳定复现。
