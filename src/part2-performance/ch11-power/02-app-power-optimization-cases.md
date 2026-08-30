---
title: App 耗电优化与案例
chapter: '11.2'
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
section: '11.2'
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-08-30'
last_verified_against: AOSP android-17.0.0_r1, android17-6.18-2026-06_r6, Android Developers Android 16 JobScheduler quota / Android 17 background audio / exact alarm / foreground service / WorkManager docs
confidence: medium-high
last_idle_audit_at: '2026-08-30T22:50:37+08:00'
last_idle_audit_run_id: 20260830-224346-idle-audit-4d6023fa
sources:
- type: official
  path: https://developer.android.com/topic/performance/power
- type: official
  path: https://developer.android.com/training/monitoring-device-state/doze-standby
- type: official
  path: https://developer.android.com/topic/performance/vitals/excessive-wakelock
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent
- type: official
  path: https://developer.android.com/develop/background-work/services/alarms
- type: official
  path: https://developer.android.com/training/location
- type: official
  path: https://developer.android.com/training/location/geofencing
- type: official
  path: https://developer.android.com/about/versions/14/changes/schedule-exact-alarms
- type: official
  path: https://developer.android.com/about/versions/14/changes/fgs-types-required
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/timeout
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-all#job-quota-opt
- type: official
  path: https://developer.android.com/about/versions/17/changes/bg-audio
- type: official
  path: https://firebase.google.com/docs/cloud-messaging/android/message-priority
- type: aosp
  path: frameworks/base/core/java/android/os/PowerManager.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActiveServices.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/audio/AudioService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/audio/HardeningEnforcer.java
- type: kernel
  path: include/linux/pm_wakeup.h
- type: kernel
  path: drivers/base/power/wakeup.c
- type: blog
  path: Obsidian Cubox - 借助 Android Studio 中的功耗性能分析器进行 A-B 测试
- type: blog
  path: Obsidian Cubox - 谈功耗是什么
- type: blog
  path: Obsidian Cubox - SoC 低功耗问题定位及优化的 10 个思路
- type: blog
  path: Obsidian Cubox - BatteryHistorian Android 手机耗电分析神器
- type: blog
  path: Obsidian Cubox - 抖音功耗优化实践
- type: deepresearch
  path: AOSP android-17.0.0_r1 source paths listed in source_repos; Android Developers Android 17 features, JobScheduler API, foreground-service timeout, Doze/App Standby, and background-location documentation; Android common kernel android17-6.18-2026-06_r6; DeepResearch/2026-06-17-battery-saver-location-power-policy-aosp-deep-dive.md; DeepResearch/2026-06-20-job-scheduler-throttling-mechanism.md; DeepResearch/2026-06-18-jobscheduler-source-verification.md; DeepResearch/2026-06-18-radio-power-state-machine-source-analysis.md; DeepResearch/2026-06-18-adaptive-battery-app-standby-coordination.md
tags:
- wakelock
- jobscheduler
- workmanager
- doze
- location
- alarm
- power
- fgs
- foreground-service
- fcm
- alarmmanager
- geofencing
- battery-historian
- camera
- '[power, battery, energy]'
related_chapters:
- '11.1'
- '5.2'
- '5.5'
- '11.3'
task2b_state: fixed
task9_state: reviewed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch11-power/02-app-power-optimization.md
- src/part2-performance/ch11-power/04-case-studies.md
---

# App 耗电优化与案例

应用耗电治理从场景、时间窗口和组件活动开始，继续检查 WakeLock、Alarm、网络、定位、动画和后台任务。修复结果需要在相同设备状态和业务负载下复测。

## 组件活动、唤醒与后台工作

### 从系统行为理解 App 耗电

App 不能直接决定电池消耗多少。它提交工作、请求硬件资源、保持设备唤醒，系统再通过调度器、HAL（硬件抽象层）和驱动完成这些请求。优化时需要检查四件事：

- **设备被唤醒多久**：WakeLock、Alarm、Job、FGS（Foreground Service，前台服务）是否延长了 CPU 活跃时间。
- **哪些硬件保持工作**：GNSS（全球导航卫星系统）、蜂窝网络、Camera、麦克风、编解码器有没有超出业务生命周期。
- **单位工作量有多大**：采样频率、分辨率、上传字节数、重试次数是否符合用户功能。
- **工作能否延后或合并**：可延迟任务交给系统批处理，用户正在等待的任务保留及时性。

电流值不能脱离设备、网络、屏幕、温度和测量窗口单独比较。同一段代码在两款手机上可能使用不同的 modem（蜂窝基带）、GNSS、codec（编解码器）或调度策略。工程判断应基于目标设备的时间线和能量数据，避免引用某款设备的一次测试作为通用结论。

#### 先选合适的执行机制

| 业务性质 | 建议入口 | 必须接受的系统边界 |
| --- | --- | --- |
| 用户正在界面里等待 | 协程、线程池或进程内异步任务 | 页面退出时取消无用工作，耗时工作不能阻塞主线程 |
| 可延迟、要求进程重启后继续 | WorkManager；平台组件可直接用 JobScheduler | 受约束、配额、standby bucket（应用待机分组）和 Doze（设备空闲省电模式）影响，执行时间不精确 |
| 用户要求在某个时刻收到提醒 | AlarmManager | 优先不精确闹钟；精确闹钟有权限和使用场景限制 |
| 用户知情的持续任务 | 对应类型的前台服务 | 需要持续通知、启动豁免、类型权限，部分类型有时长限制 |
| 服务端有新事件才处理 | FCM（Firebase Cloud Messaging）或业务推送通道 | 优先级必须符合用户可见性，离线与厂商环境要有降级方案 |

这个选择决定系统还有多少合并和延后空间。把普通同步放进精确闹钟或长期 FGS，会主动绕开大量省电机会。

### WakeLock：只保护不可中断的短窗口

`PARTIAL_WAKE_LOCK` 是只保持 CPU 运行的 WakeLock，屏幕仍可关闭。旧的 `SCREEN_DIM_WAKE_LOCK`、`SCREEN_BRIGHT_WAKE_LOCK` 和 `FULL_WAKE_LOCK` 已废弃；Activity 需要防止屏幕熄灭时，应使用 `FLAG_KEEP_SCREEN_ON` 或 `View.setKeepScreenOn()`，这样界面不可见后系统能恢复正常屏幕策略。

WorkManager、JobScheduler、媒体、位置和下载等高层 API 已经在各自的执行窗口内管理唤醒条件。业务只有在“CPU 休眠会让当前短操作无法安全完成”时才应直接持锁；锁应有单一所有者、稳定且不含隐私的 tag、由业务截止时间推导的超时，并在 `finally` 中释放。超时只是故障保护，不能代替正常释放。

客户端对象显示 held（已持有），不等于这把锁在当前电源策略下仍有效；App tag、PowerManagerService 的 suspend blocker（系统休眠阻止项）、SystemSuspend 和内核 `wakeup_source`（唤醒源）也无法一一对应。源码调用链、安全示例、Doze/LPS（Low Power Standby，低功耗待机）边界、Android Vitals 口径与逐层排障方法统一见 [11.3 WakeLock 机制与功耗分析](03-wakelock.md)。

### WorkManager 与 JobScheduler：把延迟空间交给系统

WorkManager 适合需要可靠完成、允许延迟，并且希望进程重启后继续的工作。JobScheduler 是平台原生调度器，系统组件、不引入 Jetpack 的项目或需要平台能力的代码可以直接使用。WorkManager 在不同版本与 `minSdk` 下选择的内部调度器可能变化，业务不应依赖它使用哪一个后端。

#### 约束表达的是业务条件

下面的 Kotlin 示例把大文件上传限制在充电且网络不计费的环境，并让失败任务指数退避。等待时长是产品选择的常量，方便测试和统一调整。

```kotlin
private const val UPLOAD_RETRY_DELAY_SECONDS = 30L

val uploadConstraints = Constraints.Builder()
    .setRequiresCharging(true)
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .build()

val upload = OneTimeWorkRequestBuilder<UploadWorker>()
    .setConstraints(uploadConstraints)
    .setBackoffCriteria(
        BackoffPolicy.EXPONENTIAL,
        UPLOAD_RETRY_DELAY_SECONDS,
        TimeUnit.SECONDS
    )
    .build()

WorkManager.getInstance(context).enqueueUniqueWork(
    "pending-media-upload",
    ExistingWorkPolicy.KEEP,
    upload
)
```

`UNMETERED` 表示 `ConnectivityManager` 报告当前网络不计费，不等同于 Wi‑Fi。某些 Wi‑Fi 可能被标记为计费，某些蜂窝套餐或设备环境也可能被标记为不计费。若业务只需要联网，应使用 `CONNECTED`；增加多余约束会推迟任务，并可能让积压工作在条件满足时集中执行。

#### 周期、加急与唯一工作

- `PeriodicWorkRequest` 的最小重复间隔为 15 分钟。这是请求下限，系统可以因为约束、Doze、配额或 standby bucket 延后某一轮，也不承诺固定相位。
- flex window（弹性窗口）允许系统在周期尾部选择执行时间，适合对时刻不敏感的刷新。
- Expedited work（加急工作）面向用户刚触发、需要尽快开始的短工作，受 expedited quota（加急配额）和 `OutOfQuotaPolicy` 约束。
- 唯一工作可以避免相同任务被重复入队。能合并的上报、清理、索引操作应在业务层合并输入。
- `Result.retry()` 只用于可恢复错误。鉴权失败、参数错误等永久失败继续重试，只会重复唤醒设备和服务器。

`PerformanceHintManager.Session.setPreferPowerEfficiency(true)` 是 Android 15+ 对正在运行线程的能效提示，属于 ADPF（Android Dynamic Performance Framework）能力。它不参与 WorkManager 排队，也不保证绑定到某类 CPU。设备是否采用提示取决于系统和 Power HAL，适合计算密集型代码在实机上做 A/B 验证后使用。

#### Android 16 的 Job runtime quota

Android 16（API 36）调整了 regular 与 expedited job 的运行时配额：

- 在 App 处于 top state（最前台状态）时启动、界面消失后继续运行的 job，要遵守 job runtime quota（运行时长配额）。
- 与 FGS 并发执行的 job，也要遵守 job runtime quota。
- WorkManager、JobScheduler 和 DownloadManager 调度的相关工作都受影响。

这里没有“Job 与 FGS 共用一个预算”的规则。FGS 的类型时长和 JobScheduler 的 runtime quota 属于两套限制。用户发起的大文件传输可评估 user-initiated data transfer job（用户发起的数据传输任务）；它有专门的资格条件和配额语义，不能当成通用后台通道。

定位延迟与停止原因时，WorkManager 通过 `WorkInfo.getStopReason()` 提供原因，直接使用 JobScheduler 时则读取 `JobParameters.getStopReason()`。Android 16 还提供 `JobScheduler.getPendingJobReasonsHistory()`，用于查看任务没有运行的历史原因。

#### Doze 不会消失

Doze 会延后普通网络访问、Job 和 Alarm，并在 maintenance window（维护窗口）批量执行。FGS 不能让同进程里的 Job 免除配额，也不提供设备级 Doze 豁免。应用若依赖“前台服务开着，所以网络和 Job 一直畅通”，在熄屏静置测试中很容易暴露问题。

### 位置服务：请求目标，不指定传感器

Fused Location Provider（融合位置提供方）的 priority 表达精度与功耗偏好，公开契约没有规定固定传感器组合或固定精度：

| Priority | 契约含义 | 合适的业务 |
| --- | --- | --- |
| `PRIORITY_HIGH_ACCURACY` | 偏向高精度，可能增加功耗 | 用户可见导航、运动轨迹、一次高精度确认 |
| `PRIORITY_BALANCED_POWER_ACCURACY` | 在精度与功耗之间平衡 | 城市天气、附近内容、非连续位置感知 |
| `PRIORITY_LOW_POWER` | 偏向低功耗，允许降低精度 | 对误差容忍度较高的低频场景 |
| `PRIORITY_PASSIVE` | 只接收其他客户端产生的位置，不为本请求额外计算 | 辅助更新、维护缓存时效性 |

高精度请求不保证 GNSS 一定启用，平衡模式也不保证只用 Wi‑Fi 和基站。系统设置、权限、设备能力、环境和其他客户端都会改变结果。App 应依据返回位置的 `accuracy`、时间戳和业务容差决定是否可用。

#### 间隔、批量与生命周期

下面的请求用于允许批量交付的轨迹场景。几个时长是产品根据交互延迟和会话上限定义的常量，不是平台推荐值。

```kotlin
private val TRACK_SAMPLE_INTERVAL = 30.seconds
private val TRACK_BATCH_DELAY = 2.minutes
private val TRACK_SESSION_LIMIT = 45.minutes

val request = LocationRequest.Builder(
    Priority.PRIORITY_HIGH_ACCURACY,
    TRACK_SAMPLE_INTERVAL.inWholeMilliseconds
).apply {
    setMinUpdateIntervalMillis(TRACK_SAMPLE_INTERVAL.inWholeMilliseconds)
    setMaxUpdateDelayMillis(TRACK_BATCH_DELAY.inWholeMilliseconds)
    setDurationMillis(TRACK_SESSION_LIMIT.inWholeMilliseconds)
}.build()
```

请求间隔是期望值，系统可能更快或更慢地交付；`setMaxUpdateDelayMillis()` 允许提供方批量交付，也不保证设备一定缓存到该时刻。对实时导航，过长的批量延迟会影响交互；对后台日志轨迹，批量能减少 App 被唤醒的次数。会话结束、权限撤销、页面离开和服务停止时，都要调用 `removeLocationUpdates()`。

还可以按需求设置最小位移、最大更新次数、请求时长以及“等待更准确的首个位置”。这些条件来自产品容差，不宜复制一组固定数字到所有场景。

#### Geofencing 的边界

Geofencing（地理围栏）适合“进入或离开区域时通知”这类事件驱动需求。App 不需要用短周期定位轮询维持判断，Play services 与位置栈可以合并多个客户端的请求。Android 8.0+ 在后台交付地理围栏事件时，响应可能放宽到几分钟量级；它不适合秒级轨迹或严格到达时间。

硬件是否参与围栏判断属于设备实现。公开 App 契约没有保证 `GnssCapabilities`、`dumpsys location` 中的某个字段能稳定表示 Play services Geofencing 的完整执行路径，因此不能把“存在 GNSS geofencing 能力”直接写成“当前业务已由硬件独立处理”。

后台定位还要满足权限与 FGS 条件。位置权限只有 while-in-use（仅使用期间允许）时，App 退到后台后不能继续假设完整定位能力；需要持续用户可见的定位时，应核对后台启动豁免、`location` FGS type（服务类型）、对应清单权限和运行时位置权限。

### 网络请求：减少唤醒、传输与失败重试

网络功耗由传输字节、连接建立、无线状态切换、信号质量、协议和设备实现共同决定。蜂窝与 Wi‑Fi 谁更省电没有跨设备结论，优化应围绕业务可控制的行为。

#### 合并可延迟请求

- 日志、埋点、已缓存媒体和索引数据可以积累到大小、时限或网络条件满足后批量上传。
- 用户点击发送、支付确认等交互请求不能为了批量而延后。
- 复用 HTTP 连接，开启协议支持的压缩，使用增量接口、ETag（资源版本标识）或版本游标减少重复字节。
- 失败按错误类型处理：网络瞬断可退避，服务端限流遵守 `Retry-After`（服务端建议的重试时间），客户端参数错误应停止重试。
- 大文件支持断点续传和幂等提交（重复提交不会产生额外副作用），避免一次失败重传全部内容。

批量的收益来自减少 App 唤醒与连接建立次数。若批量让每次传输大到容易超时或触发内存压力，需要缩小批次，并在目标网络环境重新测量。

#### 推送替代固定轮询

业务只有在服务端状态变化时才需要唤醒客户端，可以使用 FCM 或同类推送。FCM normal priority（普通优先级）适合普通同步，在 Doze 中可能延迟；high priority（高优先级）只用于时间敏感、用户可见的内容，并应在收到后及时展示通知。长期发送 high priority 却没有用户可见结果，FCM 可能降低后续消息优先级或代理通知。

推送不能替代数据一致性设计。消息可能重复、延迟或丢失，客户端仍需用版本号或游标拉取缺失数据；低频兜底同步可交给 WorkManager。

### AlarmManager：精确性有明确成本

AlarmManager 用于进程生命周期之外的时间事件。普通同步、清理和重试更适合 WorkManager。若用户接受时间窗口，使用 `set()`、`setWindow()`、`setAndAllowWhileIdle()` 或不精确重复闹钟，让系统有机会合并唤醒。

#### 精确闹钟权限与例外

Android 12（API 31）引入 “Alarms & reminders” special app access（特殊应用访问权限）。Android 13+ 可根据受限使用场景选择 `SCHEDULE_EXACT_ALARM` 或 `USE_EXACT_ALARM`：

| 能力 | 授权方式 | 适用边界 |
| --- | --- | --- |
| `SCHEDULE_EXACT_ALARM` | 用户授予，也可被用户或系统撤销 | 使用面较宽；调用前检查 `canScheduleExactAlarms()` |
| `USE_EXACT_ALARM` | 安装时自动授予，用户不可撤销 | 只允许闹钟、计时器、日历等受限核心场景，并受 Google Play 政策约束 |

Android 14 对 target 33+ 的多数新安装应用不再预授予 `SCHEDULE_EXACT_ALARM`；备份恢复到 Android 14 设备时也按拒绝处理。已有授权随系统升级通常会保留。

`AlarmManager.OnAlarmListener` 形式的 `setExact()` 不要求 `SCHEDULE_EXACT_ALARM`。它是进程内监听器：进程退出后不能指望系统重新创建 App 来交付回调。需要跨进程生命周期可靠触发时，通常使用 `PendingIntent`（可由系统代应用执行的预封装操作），并遵守精确闹钟权限规则。这个例外不能用于构造后台保活。

#### Doze 与 allow-while-idle

- `setAlarmClock()` 面向用户可见闹钟，系统会为交付离开低功耗模式。
- `setExactAndAllowWhileIdle()` 能穿过 Doze，但受到严格频率限制。
- `setAndAllowWhileIdle()` 允许在空闲状态交付不精确闹钟。
- 普通 Alarm 在 Doze 中可能延后到 maintenance window（维护窗口）。

AlarmManager API 文档给出的正常条件下节流量级约为每个 App 九分钟一次，系统也可以拉长间隔。这个数值是防滥用边界，不是建议轮询周期。闹钟回调里只安排短操作；需要联网或持久执行时，把后续工作交给 JobScheduler 或 WorkManager。

### 前台服务：持续可见不等于无限运行

FGS 用持续通知表达用户知情的长任务，并提高进程重要性。它不免除 Doze、Job quota（任务配额）、网络限制或硬件资源管理。Android 14（target 34+）要求服务类型、类型权限和运行时前置条件同时成立：

- 未声明 `android:foregroundServiceType` 可能触发 `MissingForegroundServiceTypeException`。
- 缺少 `FOREGROUND_SERVICE_*` 权限，或 location、camera、microphone 等 while-in-use 条件不满足，可能触发 `SecurityException`。
- App 已在后台且不满足 FGS 启动豁免时，可能触发 `ForegroundServiceStartNotAllowedException`。

日志判读要区分声明、权限与启动资格，三个异常指向的修复位置不同。

#### Android 14 与 Android 15 的超时

| 类型 | 平台限制 | 超时回调 | 未及时停止 |
| --- | --- | --- | --- |
| `shortService` | Android 14+，约三分钟 | `Service.onTimeout(int)` | 系统触发 ANR；系统不会代替服务自动完成 `stopSelf()` |
| `dataSync` | target 35+，后台状态下每 24 小时累计六小时 | `Service.onTimeout(int, int)` | 几秒内不停止会抛内部远程服务异常并终止进程 |
| `mediaProcessing` | target 35+，后台状态下每 24 小时累计六小时 | `Service.onTimeout(int, int)` | 与 `dataSync` 相同 |

六小时按类型分别计时，同一 App 的多个同类型服务共享该类型额度。用户把 App 带到前台会重置计时器。额度耗尽后继续启动同类型服务会收到 `ForegroundServiceStartNotAllowedException`。

`android-17.0.0_r1` 的 `ActiveServices.getTimeLimitedFgsType()` 把 `dataSync` 与 `mediaProcessing` 纳入此路径；宽限期结束后，`onFgsCrashTimeout()` 通过 `ForegroundServiceDidNotStopInTimeException` 终止宿主进程。`shortService` 使用独立的 ANR timer（超时计时器），两条超时路径不能混为同一种故障。

超时回调只应保存进度、释放资源并停止服务。数据同步可评估 WorkManager、user-initiated data transfer job 或 DownloadManager，选择时仍要接受对应 API 的调度和配额规则。

#### Android 17 后台音频

Android 17（API 37）把后台播放、音频焦点请求和音量修改纳入音频 hardening（限制强化）：

- 所有运行在 Android 17 上的 App，无论 targetSdk，都要有可见 Activity，或正在运行一个类型不是 `shortService` 的 FGS，才能进行这些后台音频交互。
- target 37 的 App 在后台还要求该 FGS 具有 while-in-use（WIU，仅使用期间允许）能力。通常由用户操作或 App 可见状态下启动的 FGS 获得。
- App 具有精确闹钟权限并操作 `USAGE_ALARM` 音频流时，WIU 要求可豁免；前一条“可见 Activity 或非 shortService FGS”仍然存在。

不满足条件时，播放和音量 API 可能静默失败，音频焦点请求返回 `AUDIOFOCUS_REQUEST_FAILED`。使用 `adb dumpsys audio` 或 logcat 搜索 `AudioHardening`：`level: partial` 表示没有运行 FGS，`level: full` 表示 FGS 缺少 WIU 能力。系统实现可对照 `AudioService.java` 与 `HardeningEnforcer.java`。

媒体播放服务仍需声明 `mediaPlayback` 类型及对应权限。播放永久结束、收到不可恢复的焦点丢失或用户明确停止后，应关闭播放器、media session 和 FGS。

### Camera 与 Audio 资源生命周期

#### Camera

Camera 的开销受 sensor mode（传感器工作模式）、分辨率、帧率、HDR、稳定算法、ISP（图像信号处理器）和编码路径影响。优化重点是让配置满足业务下限，并把资源生命周期限制在功能可见期间：

- 扫码或普通取景无需默认选择最大输出尺寸。
- `CONTROL_AE_TARGET_FPS_RANGE` 是请求范围，设备会结合 AE（自动曝光）与硬件能力选择帧率，不构成恒定帧率保证。
- 页面离开或任务结束时，停止 repeating request，关闭 `CameraCaptureSession`、`CameraDevice`，并释放不再使用的 Surface。
- App 退到后台后若 `dumpsys media.camera` 仍显示活跃 client，应检查会话和错误分支。

#### Audio

采样率、声道数、格式、缓冲区、编解码器、offload（交给专用音频硬件处理）能力和输出路由共同决定音频开销。44.1 kHz、48 kHz 或 96 kHz 没有脱离内容与设备的统一优劣关系。应使用内容和设备支持的原生配置，避免无收益的重采样；长时间播放要检查硬件 offload 是否生效，短提示音则要避免维持不必要的常驻播放对象。

录音、播放、焦点和 media session 都要跟随用户会话结束。音频线程不工作时还持有 WakeLock，或播放停止后仍保留 FGS，是常见的额外待机成本。

### 证据驱动的排查流程

#### 建立可复现窗口

记录机型、系统 build（构建版本）、App 版本、网络、屏幕亮度、温度、电池电量区间和操作脚本。对照组只改变一个变量；重复多轮后比较时间线与分布。测试期间的 USB 供电、调试器和屏幕常亮都可能改变结果。

下面的命令用于一次短测试前清理 Batterystats，并在测试后收集各系统服务状态。

```bash
adb shell dumpsys batterystats --reset
# 执行固定测试脚本
adb shell dumpsys batterystats > batterystats.txt
adb shell dumpsys jobscheduler > jobscheduler.txt
adb shell dumpsys alarm > alarm.txt
adb shell dumpsys location > location.txt
adb shell dumpsys activity services > services.txt
adb shell dumpsys media.camera > camera.txt
adb shell dumpsys audio > audio.txt
```

重置 Batterystats 会影响设备上的累计统计，只应在专用测试设备与明确测试窗口中执行。文件内容需结合 bugreport、Battery Historian 或 Perfetto 时间线分析，单个 `dumpsys` 快照无法说明整段耗电过程。

#### 按时间线归因

| 现象 | 证据入口 | 继续核对 |
| --- | --- | --- |
| 熄屏后仍无法 suspend（系统休眠） | Battery Historian、batterystats history、Perfetto suspend | WakeLock UID/tag、wakeup source、Alarm 与 Job 是否重叠 |
| Job 被推迟或中止 | WorkInfo/JobParameters stop reason、jobscheduler | standby bucket、约束、Android 16 runtime quota |
| 位置持续活跃 | `dumpsys location`、Battery Historian | 请求 UID、priority、间隔、后台权限和移除时机 |
| 周期性唤醒 | Alarm、JobScheduler 时间线 | exact/allow-while-idle、重复 PendingIntent、失败重试 |
| FGS 长时间存在 | `dumpsys activity services`、Perfetto CPU/network | service type、业务进度、timeout、硬件资源 |
| 后台音频静默 | `dumpsys audio`、`AudioHardening` 日志 | Activity 可见性、FGS、WIU、targetSdk、usage |
| Camera 退出后仍活跃 | `dumpsys media.camera`、cameraserver trace | session、device、Surface 的关闭路径 |

Perfetto 轨道依赖 trace config（采集配置）、系统 build 和厂商实现。标准 user build 看不到 location、camera 或 wakelock 专用轨道时，应回到 bugreport 与系统服务状态，不能把“没有轨道”等同于“没有耗电”。

### 复核清单

- WakeLock 是否有稳定 tag、业务上限和覆盖成功/失败/取消的释放路径？
- 可延迟任务是否使用 WorkManager 或 JobScheduler，并只添加必要约束？
- 是否把 `UNMETERED` 错当成 Wi‑Fi，或把周期最小间隔错当成准时保证？
- Android 16 上是否记录 Job/Work 的 stop reason 和 pending reason history？
- 位置 priority 是否按业务容差选择，退出会话后是否移除更新？
- Geofencing 是否被当成分钟级事件入口，而非秒级轨迹服务？
- 网络是否合并可延迟上传、复用连接、区分可重试与永久错误？
- high-priority FCM 是否对应时间敏感且用户可见的结果？
- 精确闹钟是否属于用户明确感知的准点功能，权限撤销后能否降级？
- 是否理解 `OnAlarmListener` 例外只适合进程存活期间？
- FGS type、权限、启动资格和 timeout（超时）是否分别处理？
- Android 17 后台音频是否满足非 shortService FGS、WIU 与 usage 规则？
- Camera、Audio、Surface、media session 是否在业务结束时关闭？
- 功耗结论是否来自目标设备、固定脚本和多轮对照？

### 与其他章节的关系

§11.1 解释系统如何把 CPU、屏幕、网络、GNSS 与其他组件能量归因到 UID；这里讨论 App 怎样减少这些组件的活跃时间。§5.3 说明 Doze、App Standby 与 JobScheduler/WorkManager，§11.3 追踪 WakeLock 在 PowerManagerService 与 suspend 路径中的实现。遇到“任务被推迟”或“设备不休眠”时，应沿这些章节的系统路径继续定位。

### 案例：能量归因、修复与复测

通用检查项用于缩小范围，案例应保留功耗基线、异常组件、修改变量和复测窗口。

功耗问题很少由一行代码单独造成。常见过程是：应用发起工作，系统为它安排 CPU、网络、定位或存储资源，硬件进入高功耗状态，工作结束后资源又未及时释放。以下六个案例说明怎样从业务现象找到系统证据，再选择合适的 Android API 修复问题。

这里不给出通用的“节电百分比”。芯片、基带、信号、屏幕、温度、账号数据和 OEM（设备厂商）策略都会改变结果。缺少 bugreport（系统诊断包）、trace（性能跟踪）、测试脚本与环境记录的数字，无法支撑工程决策。

#### 案例分析的共同步骤

每个案例都按同一组问题检查：

1. **功能契约是什么**：用户能接受多大延迟？工作是否由用户发起？错过一次是否可恢复？
2. **谁发起了资源请求**：记录 UID（Linux 用户标识，Android 通常用它区分应用及资源归属）、线程、Job ID、WakeLock tag（唤醒锁标签）、定位请求、网络调用和时间戳。
3. **系统为何准许或推迟**：检查 Doze（设备空闲省电模式）、App Standby bucket（应用待机分组）、Battery Saver（省电模式）、后台限制、热状态和 Job quota（任务配额）。
4. **硬件是否被激活**：CPU 运行不代表蜂窝基带正在发射，收到定位回调也不能说明 GNSS（全球导航卫星系统）只被当前 UID 使用。证据必须区分应用、系统服务和硬件层级。
5. **修复是否破坏业务**：同时比较成功率、端到端延迟、重试量和能耗指标。

推荐保留以下测试信息：

| 类别 | 至少记录的内容 |
|---|---|
| 构建 | 设备型号、Android build（系统构建版本）、应用版本、target SDK（目标 API 级别） |
| 环境 | Wi-Fi/蜂窝、信号、温度区间、屏幕状态、充电状态 |
| 负载 | 账号数据量、请求数量、文件大小、测试时长 |
| 功能 | 成功率、延迟分布、丢失与重复次数 |
| 系统 | bugreport、Perfetto、`dumpsys batterystats`、相关服务的 dumpsys（状态快照） |
| 统计 | 样本数、预热规则、中位数与离散程度 |

`BatteryStats` 和 Battery Historian 适合按 UID 归因，也就是把活动关联到具体应用，并对齐事件时间；设备支持的电源轨（芯片或模块的供电通道）或外接功耗仪更适合测量总能量。两类证据回答的问题不同，不能互相代替。

#### 案例一：用前台服务轮询消息

##### 故障代码

下面的示例展示一种常见错误：为了让进程长期存活（常称“保活”），每五秒在前台服务中查询一次服务端。

```java
public final class MessagePollingService extends Service {
    private volatile boolean stopped;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(1, buildNotification());
        new Thread(() -> {
            while (!stopped) {
                checkNewMessages();
                SystemClock.sleep(5_000);
            }
        }, "message-poll").start();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        stopped = true;
    }
}
```

这段代码把“消息送达”实现成应用侧定时查询。没有新消息时，它仍会产生定时器唤醒、网络握手和维持进程的成本；`START_STICKY` 还可能在进程被终止后恢复服务。通知只说明服务对用户可见，不会降低这类轮询的开销。

##### 按业务时效选择机制

| 业务要求 | 合适机制 | 说明 |
|---|---|---|
| 用户可见的实时消息 | 共享推送通道；高优先级只用于会立即展示通知的消息 | 避免每个应用维护独立的定时探测连接（心跳） |
| 后台内容刷新 | 普通优先级推送触发一次同步，另加低频恢复同步 | Doze 中允许延后 |
| 可延迟上传或同步 | WorkManager / JobScheduler | 声明网络、电量、充电等约束 |
| 用户正在感知的连续任务 | 与用途匹配的前台服务类型 | 导航、播放等工作结束后立即停服务 |

下面的 WorkManager 示例用于一次可恢复同步。多次触发会复用同名工作，避免在调度器中排出一串等价任务。

```java
public final class MessageSync {
    private static final String UNIQUE_WORK = "message-recovery-sync";

    public static void enqueue(Context context) {
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();

        OneTimeWorkRequest request =
                new OneTimeWorkRequest.Builder(MessageSyncWorker.class)
                        .setConstraints(constraints)
                        .setBackoffCriteria(
                                BackoffPolicy.EXPONENTIAL,
                                30,
                                TimeUnit.SECONDS)
                        .build();

        WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK,
                ExistingWorkPolicy.KEEP,
                request);
    }
}
```

`KEEP` 只消除同一时刻的重复待执行工作。Worker 仍需使用服务端游标或幂等键处理漏消息、重试和重复投递。周期任务的 15 分钟是最小周期边界，不是准点承诺，也不适合实时收消息。

##### Android 17 下的调度边界

`JobScheduler` 在 Android 16 起位于 `frameworks/base/apex/jobscheduler/`。应用无需为正在执行的 Job 再持有 CPU WakeLock，系统会在 Job 从开始到结束的执行期内代持。下面几条边界比内部可调常量更适合作为应用契约：

- Android 12 起，每个应用最多保有 150 个已调度 Job，expedited job（加急任务）也计入。
- Android 11 起，高频调用 `schedule()`、`enqueue()` 等调度入口会被节流。
- App Standby bucket、后台限制、Doze、Battery Saver、热状态、约束和 quota 都可能让 Job 等待。
- Android 16 的 `getPendingJobReasons()` 能返回同时存在的 pending reason（等待原因）。
- Android 17 的 `getPendingJobReasonStats()` 会按原因累计等待时长；统计在重启后不保留，Job 成功完成或取消后也会清除。

下面的 API 37 代码用于在问题仍存在时读取等待时间。

```java
if (Build.VERSION.SDK_INT >= 37) {
    JobScheduler scheduler = context.getSystemService(JobScheduler.class);
    Map<Integer, Duration> stats =
            scheduler.getPendingJobReasonStats(MESSAGE_SYNC_JOB_ID);
    stats.forEach((reason, duration) ->
            Log.i("JobDebug", "reason=" + reason + ", wait=" + duration));
}
```

多个约束可同时阻止 Job，因而各项时长之和可能大于按现实时间计算的总等待时长。采集代码应在 Job 完成或取消前运行，并把 Job ID 与业务请求 ID 一起记录。

##### 前台服务超时不是调度方案

| 类型 | Android 14—17 的边界 |
|---|---|
| `shortService` | 约三分钟；超时回调后仍不停止会进入 ANR 流程 |
| `dataSync` | target SDK 35+ 时，应用位于后台的累计运行额度通常为每 24 小时 6 小时 |
| `mediaProcessing` | target SDK 35+ 时，单独统计每 24 小时 6 小时 |

`dataSync` 与 `mediaProcessing` 按类型分别计时；同一类型下的多个服务共享运行额度。应用回到前台会重置可用时间。收到 `Service.onTimeout(int, int)` 后必须在数秒内 `stopSelf()`，否则进程会因服务未及时停止而异常终止。Android 17 延续这组行为。

这些超时限制用于约束前台服务滥用，不会把轮询自动变成可靠同步。可恢复的数据传输应保存进度，交给调度 API；用户可见且不可中断的工作才进入对应的前台服务。

##### 验证

修复前后比较：

- 单位时间内进程唤醒次数、CPU running（CPU 保持运行）时间和网络请求次数；
- Job 的 pending reason、stop reason（停止原因）、重试次数和端到端消息延迟；
- 前台服务运行时长以及 `onTimeout()`、ANR（应用无响应）、crash（崩溃）日志；
- Wi-Fi 与蜂窝两组测试，避免把基带变化误算成代码收益。

#### 案例二：后台持续请求高精度定位

##### 故障代码

下面的请求在组件存活期间持续向 GPS provider（位置提供方）请求更新，期望间隔为一秒，最小位移门槛为零。

```java
public final class LocationTracker implements LocationListener {
    private final LocationManager locationManager;

    public LocationTracker(Context context) {
        locationManager = context.getSystemService(LocationManager.class);
    }

    public void start() {
        locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                1_000,
                0,
                this);
    }
}
```

问题有两部分：请求参数没有依据产品场景确定，生命周期中也没有与注册对应的 `removeUpdates()`。系统可能因后台限制而降低回调频率，但应用仍应主动修正请求并及时注销。

##### 把定位需求写成产品参数

定位策略至少要区分三类场景：

| 场景 | 请求方式 | 退出条件 |
|---|---|---|
| 页面展示一次附近位置 | `getCurrentLocation()` 或缓存位置 | 得到结果、超时、页面离开 |
| 用户主动导航 | 连续高精度请求；按运动状态和 UI 需求设间隔、最小距离 | 导航停止、权限撤销、FGS（Foreground Service，前台服务）结束 |
| 后台地理围栏 | Geofencing（地理围栏）等系统能力 | 围栏移除、业务失效 |

下面的示例用于“页面需要一次新鲜位置”。取消信号跟随页面生命周期，避免页面退出后继续等待。

```java
public final class CurrentLocationRequest {
    private final LocationManager locationManager;
    private CancellationSignal cancellationSignal;

    public CurrentLocationRequest(Context context) {
        locationManager = context.getSystemService(LocationManager.class);
    }

    public void request(
            Executor executor,
            Consumer<Location> consumer) {
        cancellationSignal = new CancellationSignal();
        locationManager.getCurrentLocation(
                LocationManager.FUSED_PROVIDER,
                cancellationSignal,
                executor,
                consumer);
    }

    public void cancel() {
        if (cancellationSignal != null) {
            cancellationSignal.cancel();
            cancellationSignal = null;
        }
    }
}
```

一次定位也可能启用高成本 provider；这种 API 的价值是给请求设置明确终点。导航等连续场景仍应使用 `LocationRequest`，参数须由可接受延迟、路径误差和运动速度推导，并在停止导航时移除 listener（监听器）。

##### 系统端的检查链

Android 17 的 `LocationProviderManager` 会综合检查：

1. Manifest 声明、runtime permission（运行时权限）与 AppOps（应用操作权限状态）；
2. 用户是否启用位置、当前用户与 allowlist（允许列表）；
3. UID 前后台状态及后台定位资格；
4. Battery Saver 对 location service 的模式；
5. 后台请求的最小间隔与其他豁免条件。

未通过检查的 registration（已注册的定位请求）不会参与 provider request（提供方请求）的合并，当前 UID 的请求也就不会驱动底层 provider。设备上若还有导航、系统服务或其他应用请求定位，GNSS 或融合定位仍可能工作，所以“当前应用无回调”不能推导出整机定位功耗为零。

Battery Saver 的位置模式定义在 `PowerManager`，包括不改变、熄屏禁 GPS、熄屏禁全部位置、只允许前台请求、熄屏时降低请求频率等策略。`SystemLocationPowerSaveModeHelper` 接收 `PowerManagerInternal` 的状态，`LocationProviderManager` 再据此更新 registration。OEM 可以选择不同策略；应用不能假定某一模式永远是设备默认值。

后台位置限制从 Android 8.0 就已存在。AOSP 中能找到后台节流间隔的配置默认值，设备配置和 OEM 策略可以修改它；“后台大约每小时只有少量更新”才是应用应依赖的公开行为边界。Android 12 增加的是精确/大致位置等权限变化，不是后台节流的起点。

运行 `location` 类型 FGS 也不代表任何时刻都能启动定位。Android 12+ 的后台 FGS 启动限制和 Android 14+ 的 while-in-use（仅使用期间授权）权限检查仍然生效。导航应用应由用户可见操作启动，声明正确的前台服务类型，并在导航结束后释放请求。

##### Battery Saver 与 Thermal 是两条通道

Battery Saver 会把位置策略传给 location service（位置服务）。Thermal service（热管理服务）提供当前热状态和 headroom（距离热限制还有多少余量），平台不会把热状态自动换算为某个 location power-save mode。产品若允许在温度升高时降低更新频率，可以监听热状态后调整自身请求；不要用高频轮询热状态制造新的负载。

##### 验证

- `adb shell dumpsys location`：检查各 provider 的 request、registration、前后台与频率限制状态；
- bugreport 与 Battery Historian：对齐位置请求、WakeLock、屏幕、Doze 和 Battery Saver 时间线；
- Perfetto：检查 CPU 调度、Binder（进程间通信）与设备提供的定位 trace；
- 设备电源轨或外接仪表：判断 GNSS、CPU 和整机能量是否同步下降。

测试必须覆盖权限被撤销、仅大致位置、熄屏、后台、Battery Saver、导航 FGS 和其他应用同时定位等状态。

#### 案例三：零散网络请求反复激活蜂窝链路

##### 先划清 Android 与 modem 的边界

Android Radio HAL（无线硬件抽象层）的 `RadioState` 描述 modem（蜂窝基带）控制面处于 `OFF`、`UNAVAILABLE` 还是 `ON`。Android 17 的新实现使用稳定 AIDL（Android 接口定义语言）接口 `IRadioModem`；`RadioModemProxy` 仍保留旧的 HIDL（HAL 接口定义语言）分支以兼容旧设备。`setRadioPower()` 属于系统 telephony（电话与蜂窝网络）控制路径，普通应用不能用它做网络节能。

LTE/5G 的 RRC（Radio Resource Control，无线资源控制）连接态、DRX（Discontinuous Reception，非连续接收）周期、inactivity timer（空闲计时器）和发射功率，由 modem、网络制式、运营商参数及信号共同决定。公开 Android API 不提供一套跨设备可靠的 RRC 状态。把 3G 的 DCH/PCH（专用信道/寻呼信道）、LTE 的 RRC Connected/Idle 和 5G 状态放进同一张固定电流表，会产生错误结论。

应用层可以确认：大量间隔很短的请求会增加 DNS、连接建立、TLS、CPU 与网络活动；在蜂窝环境下，它们还可能延长 modem 活跃时间。请求结束后基带继续保持活跃的 tail time（尾时长）有多长、消耗多少能量，必须在目标设备和网络上测量。

##### 使用持久化 outbox 合并可延迟上传

outbox 是本地持久化的待发送队列。下面的示例在业务事件写入 outbox 后，只保留一个待执行的上传 Worker。

```java
public final class TelemetryUpload {
    private static final String UNIQUE_UPLOAD = "telemetry-outbox-upload";

    public static void notifyOutboxChanged(Context context) {
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();

        OneTimeWorkRequest upload =
                new OneTimeWorkRequest.Builder(OutboxUploadWorker.class)
                        .setConstraints(constraints)
                        .setBackoffCriteria(
                                BackoffPolicy.EXPONENTIAL,
                                30,
                                TimeUnit.SECONDS)
                        .build();

        WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_UPLOAD,
                ExistingWorkPolicy.KEEP,
                upload);
    }
}
```

Worker 在一次运行中循环读取大小受限的批次，收到服务端确认后再通过事务删除；达到本次执行额度且 outbox 尚未清空时返回 `Result.retry()`。数据库保存唯一可信的待发送记录，还要安排低频恢复同步，以处理“写入 outbox”与“调用 enqueue”无法纳入同一事务的问题，以及 `KEEP` 判断期间出现并发请求的竞争窗口。网络客户端应复用连接，并分别设置连接、读写与整次调用的超时。交互请求、支付确认和用户正在等待的发送操作不能为了批量而任意延后，它们需要单独的及时执行路径。

##### 诊断证据

| 问题 | 证据 |
|---|---|
| 请求是否过碎 | 客户端调用日志、服务端 access log（访问日志）、包大小与时间间隔 |
| 是否重复握手 | 网络库 event listener（事件监听器）、Perfetto socket/CPU 事件、抓包 |
| 哪个 UID 产生流量 | `NetworkStatsManager`、`TrafficStats`、bugreport |
| modem 是否长时间活跃 | 设备支持的 modem/ODPM（设备端功耗测量）电源轨、厂商 trace、外接仪表 |
| 是否由弱信号放大 | 相同业务在 Wi-Fi、强信号蜂窝、弱信号蜂窝下分组测试 |

`TrafficStats` 的字节数不能直接换算为毫安时。传输相同字节数时，Wi-Fi、5G 弱信号和漫游网络的能量消耗可能相差很大。

#### 案例四：组件泄漏伴随周期回调

##### 故障代码

下面的 Activity 注册网络回调后没有注销。匿名内部类会经由回调引用 Activity，页面销毁后仍可能收到事件。

```java
public final class NetworkScreen extends Activity {
    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    renderNetwork(network);
                }
            };

    @Override
    protected void onStart() {
        super.onStart();
        getSystemService(ConnectivityManager.class)
                .registerDefaultNetworkCallback(callback);
    }
}
```

泄漏的直接后果是对象无法随生命周期结束而回收。若回调还会刷新 UI、查询数据库或发起网络请求，已销毁的页面会继续触发 CPU、Binder 和 I/O 工作。较高的堆占用不能单独证明耗电，还要找到对象被保留后继续执行工作的证据链。

##### 对称释放

下面的修复让注册与注销处于同一生命周期区间。

```java
public final class NetworkScreen extends Activity {
    private boolean registered;
    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    renderNetwork(network);
                }
            };

    @Override
    protected void onStart() {
        super.onStart();
        getSystemService(ConnectivityManager.class)
                .registerDefaultNetworkCallback(callback);
        registered = true;
    }

    @Override
    protected void onStop() {
        if (registered) {
            getSystemService(ConnectivityManager.class)
                    .unregisterNetworkCallback(callback);
            registered = false;
        }
        super.onStop();
    }
}
```

生产代码还要防止重复注册，并根据 UI 是否需要后台更新，选择 `onStart/onStop` 或更长的生命周期。协程、Rx stream（ReactiveX 数据流）、sensor listener（传感器监听器）、location listener（位置监听器）和 Handler callback（回调）都要明确由谁注册、由谁取消。

##### 证明它与功耗有关

证据应按顺序建立：

1. heap dump（堆转储）显示已销毁组件仍被某个 listener、线程或队列引用；
2. trace 或日志显示该对象仍收到回调；
3. 回调带来可量化的 CPU、binder、网络、定位或存储工作；
4. 修复后 retained object（仍被引用的对象）数量、回调量和对应资源使用时间同时下降。

GC（垃圾回收）次数增加可能带来 CPU 成本，内存压力也可能触发 reclaim（内存回收）、内存压缩或 swap（交换空间）；具体路径取决于设备内核与内存配置。`android17-6.18-2026-06_r6` 中页面回收的通用入口可从 `mm/vmscan.c` 追踪，但应用侧不能把 RSS（Resident Set Size，进程驻留内存）的变化直接换算成能耗。

Android 17 的 `ProfilingManager` 增加 anomaly trigger（异常触发器），可在系统检测到 Binder 调用过量或内存超限等异常时提供采样或 heap dump 线索。这个接口可以辅助取证，但不能取代复现脚本、对象引用链和功耗测量。

#### 案例五：用 WakeLock 和 Alarm 对抗 Doze

##### 错误思路

一种常见实现会在服务中长时间持有 WakeLock；检测到 `isDeviceIdleMode()` 后，再安排 `setExactAndAllowWhileIdle()` 继续唤醒设备。这样会减少系统合并后台工作的机会：

- Doze 会推迟普通 Job、sync、alarm 和网络访问，并忽略普通应用的 WakeLock；
- allow-while-idle Alarm（可在设备空闲时交付的闹钟）会唤醒设备，频率受系统限制，只应服务于用户可感知且有精确时刻要求的功能。

即时消息应优先使用共享推送通道。普通后台刷新交给 WorkManager/JobScheduler，接受维护窗口或 quota 带来的延迟。只有闹钟、日历提醒等用户明确要求准时发生的事件，才评估 exact Alarm（精确闹钟）资格。

##### Android 17 的 listener 型 idle Alarm

API 37 增加接收 `Executor` 与 `OnAlarmListener` 的 `setExactAndAllowWhileIdle()`。这种 listener（监听器）形式的 Alarm 依赖调用进程继续存活。下面的代码只适合当前组件仍存活时需要的精确回调。

```java
public final class VisibleSessionDeadline {
    private final AlarmManager alarmManager;
    private final Executor executor;
    private AlarmManager.OnAlarmListener listener;

    public VisibleSessionDeadline(Context context) {
        alarmManager = context.getSystemService(AlarmManager.class);
        executor = context.getMainExecutor();
    }

    public void schedule(long delayMillis, Runnable action) {
        if (Build.VERSION.SDK_INT < 37) {
            throw new UnsupportedOperationException("API 37 required");
        }
        cancel();
        listener = action::run;
        alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                SystemClock.elapsedRealtime() + delayMillis,
                "visible-session-deadline",
                executor,
                listener);
    }

    public void cancel() {
        if (listener != null) {
            alarmManager.cancel(listener);
            listener = null;
        }
    }
}
```

系统可在调用进程不再有 Activity、Service 或 ContentProvider 时取消 listener Alarm。组件结束时也应调用 `cancel(listener)`。需要在进程终止后仍可靠送达的用户提醒，应使用合适的 `PendingIntent` 方案，并遵守 exact Alarm 权限和政策。

##### Doze 与 Low Power Standby

Doze 关注设备长时间闲置时的 CPU、网络、Job、Alarm 和 WakeLock。Low Power Standby（低功耗待机）还会在非交互状态下限制网络与 WakeLock；设备支持、启用状态和豁免都可能不同。运行前台服务也不会自动获得这些网络与电源策略的豁免。

平台进入 suspend（系统挂起）时会检查 wakeup source（内核唤醒源）。Android 17 的内核锚点是 `kernel/power/suspend.c` 与 `drivers/base/power/wakeup.c`。应用在 BatteryStats 中看到的 WakeLock 归因和内核 wakeup source 处于不同层级，排查时要通过时间线建立关联。

下面的命令用于在测试设备上强制进入和退出 Doze。

```bash
adb shell dumpsys deviceidle force-idle
adb shell dumpsys deviceidle
adb shell dumpsys deviceidle unforce
```

测试期间应确认设备未充电，并在结束后执行 `unforce`。用例要检查推送送达、普通同步延迟、维护窗口恢复、网络失败后的幂等重试，以及用户唤醒设备后的状态一致性。

#### 案例六：多个模块各自注册后台任务

##### 问题

同步、日志、配置和清理模块若各自创建周期 Job，容易产生这些后果：

- 多个 Job 具有相同网络约束与相近时限，却分别启动进程和网络；
- 页面、广播和 push（推送）都重复调用 `schedule()`；
- 每个模块独立重试，服务恢复时形成请求峰值；
- Job 数量、调度入口频率和 App Standby quota 更快触及限制。

合并任务时不能只看时间接近。精确时限、网络类型、充电要求、失败语义或用户可见性不同的工作应保留独立调度。

##### 同约束工作使用一个 JobInfo

Android 14 起，`JobWorkItem`（Job 队列中的工作项）可以随 persisted Job（跨重启保留的任务）一起持久化。下面的示例让一组“需要联网且允许延迟”的工作共享内容稳定的 `JobInfo`。

```java
public final class DeferredWorkQueue {
    private static final int JOB_ID = 4100;

    public static int enqueue(
            Context context,
            String operation,
            long recordId) {
        ComponentName service =
                new ComponentName(context, DeferredJobService.class);

        JobInfo job = new JobInfo.Builder(JOB_ID, service)
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED)
                .setPersisted(true)
                .build();

        PersistableBundle extras = new PersistableBundle();
        extras.putString("operation", operation);
        extras.putLong("record_id", recordId);

        JobWorkItem item = new JobWorkItem.Builder()
                .setExtras(extras)
                .build();

        return context.getSystemService(JobScheduler.class)
                .enqueue(job, item);
    }
}
```

`NETWORK_TYPE_UNMETERED` 表示系统判定的非计量网络，不等同于 Wi-Fi。persisted Job 需要在 Manifest 中声明 `RECEIVE_BOOT_COMPLETED`，`DeferredJobService` 需要受 `BIND_JOB_SERVICE` 权限保护。服务应逐个调用 `dequeueWork()` 取出工作项，成功后调用 `completeWork()`，并在异步处理结束时调用 `jobFinished()`。业务记录需要自己的幂等键，以保证重复处理不会产生额外副作用；`JobWorkItem` 只负责排队，不能作为业务数据的唯一可信来源。

官方 API 建议同一队列持续使用相同的 `JobInfo`。反复改变 extras（附加参数）、ClipData（可携带 URI 等内容的数据容器）或约束，可能让系统认为任务描述发生变化，导致正在运行的 Job 被停止后重启。合并后仍受 150 个 Job 上限、调度入口频率限制、standby bucket、quota 和设备状态限制。

##### App Standby 只解释“为何等”，不替应用做优先级

Adaptive Battery（自适应电量管理）或系统使用记录会影响 App Standby bucket，`QuotaController` 再按 bucket 与设备状态判断 Job 是否还有可用 quota。应用应根据业务时限选择普通、expedited（加急）或 user-initiated（用户发起）工作，不能靠频繁重新调度争取执行机会。

Android 17 可使用 `getPendingJobReasonStats()` 区分等待主要来自网络约束、App Standby、quota、设备状态还是调度优化。等待时间符合已声明的约束时，这是正常调度结果；若 SLA（服务时限承诺）不允许这段延迟，应重新选择 API 或调整业务契约。

##### 验证

比较合并前后的：

- 待调度 Job 数与每小时调度 API 调用数；
- 进程启动、Job session（任务执行批次）、网络连接和失败重试数量；
- 每类操作的最长等待、成功率和重复处理；
- `STOP_REASON_*`、pending reason stats 与当前 standby bucket；
- 单位业务量的 CPU time、网络字节和设备能量。

#### 跨案例判断表

| 现象 | 不能直接得出的结论 | 需要补的证据 |
|---|---|---|
| UID 网络字节下降 | 蜂窝功耗按同比例下降 | 信号、制式、modem rail（基带电源轨）、请求时间线 |
| 定位回调停止 | GNSS 已关闭 | 其他 registration、provider request、电源轨 |
| RSS 下降 | 电池续航提升 | GC/reclaim/CPU/I/O 与能量变化 |
| Job 长时间 pending | JobScheduler 出错 | pending reason、standby bucket、quota、设备状态 |
| FGS 仍在通知栏 | 网络和 WakeLock 可在 Doze 中自由使用 | Doze/LPS 状态、网络与 WakeLock trace |
| 唤醒次数下降 | 用户体验没有损失 | 成功率、延迟、丢失与恢复结果 |

#### 复核清单

- [ ] 后台工作是否有明确的延迟和可靠性契约？
- [ ] 用户不可见的工作是否误用了前台服务、WakeLock 或 exact alarm？
- [ ] 是否用唯一工作、稳定 Job ID 或服务端游标消除了重复调度？
- [ ] 定位请求是否由场景推导精度、间隔、距离和退出条件？
- [ ] 网络批量是否只作用于允许延迟的请求？
- [ ] listener、callback、线程、协程和 WakeLock 是否对称释放？
- [ ] 是否记录 pending reason、stop reason、standby bucket 和系统电源状态？
- [ ] 功耗数字是否附带设备、网络、温度、样本与原始产物？
- [ ] AOSP 引用是否来自 `android-17.0.0_r1`，内核引用是否来自 `android17-6.18-2026-06_r6`？

#### 案例涉及的版本边界

| 版本 | 与案例有关的变化 |
|---|---|
| Android 14 / API 34 | Job pending reason API；persisted Job 可携带持久化的 JobWorkItem；`shortService` 类型 |
| Android 15 / API 35 | target 35+ 的 `dataSync`、`mediaProcessing` FGS 进入 6 小时/24 小时限制；`Service.onTimeout(int, int)` |
| Android 16 / API 36 | `getPendingJobReasons()` 返回多个等待原因；后台调度 quota 对 WorkManager 使用更需关注 |
| Android 17 / API 37 | `getPendingJobReasonStats()`；listener 版本 `setExactAndAllowWhileIdle()`；平台源码锚点 `android-17.0.0_r1` |

### 全文版本与实现边界

| Android 版本 | 相关变化 |
| --- | --- |
| Android 5.0 / API 21 | JobScheduler 引入 |
| Android 6.0 / API 23 | Doze 与 App Standby 引入 |
| Android 8.0 / API 26 | 后台执行、后台位置与隐式广播限制趋严 |
| Android 12 / API 31 | 精确闹钟 special app access；后台启动 FGS 受限 |
| Android 13 / API 33 | `USE_EXACT_ALARM` 与通知权限等边界进入适配范围 |
| Android 14 / API 34 | target 34+ 强制 FGS type 与对应权限；`shortService` 时限；多数 target 33+ 新安装不预授予精确闹钟权限 |
| Android 15 / API 35 | target 35+ 的 `dataSync`、`mediaProcessing` FGS 后台累计时限；ADPF 能效偏好提示 |
| Android 16 / API 36 | top-started 与 FGS 并发 job 恢复受 runtime quota 约束；新增 pending job reasons history |
| Android 17 / API 37 | 后台音频 hardening；target 37 后台音频增加 WIU 能力要求 |

## 参考资料

- [Android 官方：优化电池使用](https://developer.android.com/topic/performance/power)
- [Android 官方：Doze 和 App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Android 官方：Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [Android 官方：Persistent work](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Android 官方：WorkManager 定义工作请求](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Android 官方：位置服务](https://developer.android.com/training/location)
- [Google Play services：Location priority](https://developers.google.com/android/reference/com/google/android/gms/location/Priority)
- [Android 官方：Geofencing](https://developer.android.com/training/location/geofencing)
- [Android 官方：Alarm 调度](https://developer.android.com/develop/background-work/services/alarms)
- [Android 官方：Android 14 精确闹钟变化](https://developer.android.com/about/versions/14/changes/schedule-exact-alarms)
- [Android 官方：Android 14 FGS type](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 官方：FGS timeout](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android 官方：Android 16 JobScheduler quota](https://developer.android.com/about/versions/16/behavior-changes-all#job-quota-opt)
- [Android 官方：Android 17 后台音频](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Firebase 官方：Android 消息优先级](https://firebase.google.com/docs/cloud-messaging/android/message-priority)
- [Android 官方：Battery Historian](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [AOSP：PowerManager.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/os/PowerManager.java)
- [AOSP：PowerManagerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java)
- [AOSP：JobScheduler.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java)
- [AOSP：JobSchedulerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java)
- [AOSP：AlarmManager.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java)
- [AOSP：AlarmManagerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java)
- [AOSP：ActiveServices.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/am/ActiveServices.java)
- [AOSP：AudioService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/audio/AudioService.java)
- [AOSP：HardeningEnforcer.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/audio/HardeningEnforcer.java)
- [Android 17 Kernel：pm_wakeup.h](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/include/linux/pm_wakeup.h)
- [Android 17 Kernel：wakeup.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c)

### Android 17 / API 37

- [Android 17 features and APIs](https://developer.android.com/about/versions/17/features)
- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [AlarmManager API reference](https://developer.android.com/reference/android/app/AlarmManager)

#### 后台执行与位置

- [Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Background location limits](https://developer.android.com/about/versions/oreo/background-location-limits)
- [Android 16 JobScheduler quota changes](https://developer.android.com/about/versions/16/behavior-changes-all#job-scheduler-quota)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details)

#### AOSP `android-17.0.0_r1`

- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java`
- `frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java`
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- `frameworks/base/services/core/java/com/android/server/location/injector/SystemLocationPowerSaveModeHelper.java`
- `frameworks/base/services/core/java/com/android/server/location/provider/LocationProviderManager.java`
- `frameworks/opt/telephony/src/java/com/android/internal/telephony/RadioModemProxy.java`
- `hardware/interfaces/radio/aidl/android/hardware/radio/modem/IRadioModem.aidl`

#### Android common kernel `android17-6.18-2026-06_r6`

- `kernel/power/suspend.c`
- `drivers/base/power/wakeup.c`
- `mm/vmscan.c`
