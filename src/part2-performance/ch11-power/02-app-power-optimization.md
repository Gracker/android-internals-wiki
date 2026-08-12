---
title: "App 耗电优化"
chapter: "11.2"
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
section: "11.2"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1, android17-6.18-2026-06_r6, Android Developers Android 16 JobScheduler quota / Android 17 background audio / exact alarm / foreground service / WorkManager docs"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/power"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/alarms"
  - type: official
    path: "https://developer.android.com/training/location"
  - type: official
    path: "https://developer.android.com/training/location/geofencing"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/schedule-exact-alarms"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/fgs-types-required"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/timeout"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-all#job-quota-opt"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/bg-audio"
  - type: official
    path: "https://firebase.google.com/docs/cloud-messaging/android/message-priority"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/AlarmManager.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/audio/AudioService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/audio/HardeningEnforcer.java"
  - type: kernel
    path: "include/linux/pm_wakeup.h"
  - type: kernel
    path: "drivers/base/power/wakeup.c"
  - type: blog
    path: "Obsidian Cubox - 借助 Android Studio 中的功耗性能分析器进行 A-B 测试"
  - type: blog
    path: "Obsidian Cubox - 谈功耗是什么"
  - type: blog
    path: "Obsidian Cubox - SoC 低功耗问题定位及优化的 10 个思路"
  - type: blog
    path: "Obsidian Cubox - BatteryHistorian Android 手机耗电分析神器"
  - type: blog
    path: "Obsidian Cubox - 抖音功耗优化实践"
tags: ['wakelock', 'jobscheduler', 'workmanager', 'doze', 'location', 'alarm', 'power', 'fgs', 'foreground-service', 'fcm', 'alarmmanager', 'geofencing', 'battery-historian', 'camera']
related_chapters: ["11.1", "11.3", "5.6", "5.4", "5.10", "11.5"]
task2b_state: fixed
task9_state: reviewed
---


# 11.2 App 耗电优化

## 从系统行为理解 App 耗电

App 不能直接决定电池消耗多少。它提交工作、请求硬件资源、保持设备唤醒，系统再通过调度器、HAL 和驱动完成这些请求。优化时需要检查四件事：

- **设备被唤醒多久**：WakeLock、Alarm、Job、FGS 是否延长了 CPU 活跃时间。
- **哪些硬件保持工作**：GNSS、蜂窝网络、Camera、麦克风、编解码器有没有超出业务生命周期。
- **单位工作量有多大**：采样频率、分辨率、上传字节数、重试次数是否符合用户功能。
- **工作能否延后或合并**：可延迟任务交给系统批处理，用户正在等待的任务保留及时性。

电流值不能脱离设备、网络、屏幕、温度和测量窗口单独比较。同一段代码在两款手机上可能走不同的 modem、GNSS、codec 或调度策略。工程判断应基于目标设备的时间线和能量数据，避免引用某款设备的一次测试作为通用结论。

### 先选合适的执行机制

| 业务性质 | 建议入口 | 必须接受的系统边界 |
| --- | --- | --- |
| 用户正在界面里等待 | 协程、线程池或进程内异步任务 | 页面退出时取消无用工作，耗时工作不能阻塞主线程 |
| 可延迟、要求进程重启后继续 | WorkManager；平台组件可直接用 JobScheduler | 受约束、配额、standby bucket 和 Doze 影响，执行时间不精确 |
| 用户要求在某个时刻收到提醒 | AlarmManager | 优先不精确闹钟；精确闹钟有权限和使用场景限制 |
| 用户知情的持续任务 | 对应类型的前台服务 | 需要持续通知、启动豁免、类型权限，部分类型有时长限制 |
| 服务端有新事件才处理 | FCM 或业务推送通道 | 优先级必须符合用户可见性，离线与厂商环境要有降级方案 |

这个选择决定系统还有多少合并和延后空间。把普通同步放进精确闹钟或长期 FGS，会主动绕开大量省电机会。

## WakeLock：只保护不可中断的短窗口

`PARTIAL_WAKE_LOCK` 保持 CPU 运行，屏幕仍可关闭。旧的 `SCREEN_DIM_WAKE_LOCK`、`SCREEN_BRIGHT_WAKE_LOCK` 和 `FULL_WAKE_LOCK` 已废弃；Activity 需要防止屏幕熄灭时，应使用 `FLAG_KEEP_SCREEN_ON` 或 `View.setKeepScreenOn()`，这样界面不可见后系统能恢复正常屏幕策略。

WorkManager、JobScheduler、媒体、位置和下载等高层 API 已经在各自的执行窗口内管理唤醒条件。业务只有在“CPU 休眠会让当前短操作无法安全完成”时才应直接持锁；锁应有单一所有者、稳定且不含隐私的 tag、由业务截止时间推导的超时，并在 `finally` 中释放。超时只是故障保护，不能代替正常释放。

客户端对象显示 held，不等于这把锁在当前电源策略下仍有效；App tag、PowerManagerService 的 suspend blocker、SystemSuspend 和内核 `wakeup_source` 也不是可以一一对应的对象。源码调用链、安全示例、Doze/LPS 边界、Android Vitals 口径与逐层排障方法统一见 [11.5 WakeLock 机制与功耗分析](05-wakelock.md)。

## WorkManager 与 JobScheduler：把延迟空间交给系统

WorkManager 适合需要可靠完成、允许延迟、并且希望跨进程重启继续的工作。JobScheduler 是平台原生调度器，系统组件、不引入 Jetpack 的项目或需要平台能力的代码可以直接使用。WorkManager 在不同版本与 `minSdk` 下选择的内部调度器可能变化，业务不应依赖它使用哪一个后端。

### 约束表达的是业务条件

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

`UNMETERED` 表示 `ConnectivityManager` 报告当前网络不计费，不等同于 Wi‑Fi。某些 Wi‑Fi 可能被标记为计费，某些蜂窝套餐或设备环境也可能被标记为不计费。若业务只需要联网，应使用 `CONNECTED`；多加约束会推迟任务，并可能让积压工作在条件满足时集中执行。

### 周期、加急与唯一工作

- `PeriodicWorkRequest` 的最小重复间隔为 15 分钟。这是请求下限，系统可以因为约束、Doze、配额或 standby bucket 延后某一轮，也不承诺固定相位。
- flex window 允许系统在周期尾部选择执行时间，适合对时刻不敏感的刷新。
- Expedited work 面向用户刚触发、需要尽快开始的短工作，受 expedited quota 和 `OutOfQuotaPolicy` 约束。
- 唯一工作可以避免相同任务被重复入队。能合并的上报、清理、索引操作应在业务层合并输入。
- `Result.retry()` 只用于可恢复错误。鉴权失败、参数错误等永久失败继续重试，只会重复唤醒设备和服务器。

`PerformanceHintManager.Session.setPreferPowerEfficiency(true)` 是 Android 15+ 对正在运行线程的能效提示。它不参与 WorkManager 排队，也不保证绑定到某类 CPU。设备是否采用提示取决于系统和 Power HAL，适合计算密集型代码在实机上做 A/B 验证后使用。

### Android 16 的 Job runtime quota

Android 16（API 36）调整了 regular 与 expedited job 的运行时配额：

- 在 App 处于 top state 时启动、界面消失后继续运行的 job，要遵守 job runtime quota。
- 与 FGS 并发执行的 job，也要遵守 job runtime quota。
- WorkManager、JobScheduler 和 DownloadManager 调度的相关工作都受影响。

这里没有“Job 与 FGS 共用一个预算”的规则。FGS 的类型时长和 JobScheduler 的 runtime quota 属于两套限制。用户发起的大文件传输可评估 user-initiated data transfer job；它有专门的资格条件和配额语义，不能当成通用后台通道。

定位延迟与停止原因时，WorkManager 记录 `WorkInfo.getStopReason()`，直接使用 JobScheduler 时读取 `JobParameters.getStopReason()`。Android 16 还提供 `JobScheduler.getPendingJobReasonsHistory()`，用于查看任务没有运行的历史原因。

### Doze 不会消失

Doze 会延后普通网络访问、Job 和 Alarm，并在维护窗口批量执行。FGS 不能让同进程里的 Job 免除配额，也不提供设备级 Doze 豁免。应用若依赖“前台服务开着，所以网络和 Job 一直畅通”，在熄屏静置测试中很容易暴露问题。

## 位置服务：请求目标，不指定传感器

Fused Location Provider 的 priority 表达精度与功耗偏好，公开契约没有规定固定传感器组合或固定精度：

| Priority | 契约含义 | 合适的业务 |
| --- | --- | --- |
| `PRIORITY_HIGH_ACCURACY` | 偏向高精度，可能增加功耗 | 用户可见导航、运动轨迹、一次高精度确认 |
| `PRIORITY_BALANCED_POWER_ACCURACY` | 在精度与功耗之间平衡 | 城市天气、附近内容、非连续位置感知 |
| `PRIORITY_LOW_POWER` | 偏向低功耗，允许降低精度 | 对误差容忍度较高的低频场景 |
| `PRIORITY_PASSIVE` | 只接收其他客户端产生的位置，不为本请求额外计算 | 辅助更新、缓存新鲜度维护 |

高精度请求不保证 GNSS 一定启用，平衡模式也不保证只用 Wi‑Fi 和基站。系统设置、权限、设备能力、环境和其他客户端都会改变结果。App 应依据返回位置的 `accuracy`、时间戳和业务容差决定是否可用。

### 间隔、批量与生命周期

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

请求间隔是期望值，系统可能更快或更慢地交付；`setMaxUpdateDelayMillis()` 允许提供方批量交付，也不保证设备一定缓存到该时刻。对实时导航，过长批量延迟会破坏交互；对后台日志轨迹，批量能减少 App 被唤醒的次数。会话结束、权限撤销、页面离开和服务停止时，都要调用 `removeLocationUpdates()`。

还可以按需求设置最小位移、最大更新次数、请求时长以及“等待更准确的首个位置”。这些条件来自产品容差，不宜复制一组固定数字到所有场景。

### Geofencing 的边界

Geofencing 适合“进入或离开区域时通知”这类事件驱动需求。App 不需要用短周期定位轮询维持判断，Play services 与位置栈可以合并多个客户端的请求。Android 8.0+ 在后台交付地理围栏事件时，响应可能放宽到几分钟量级；它不适合秒级轨迹或严格到达时间。

硬件是否参与围栏判断属于设备实现。公开 App 契约没有保证 `GnssCapabilities`、`dumpsys location` 中的某个字段能稳定表示 Play services Geofencing 的完整执行路径，因此不能把“存在 GNSS geofencing 能力”直接写成“当前业务已卸载到硬件”。

后台定位还要满足权限与 FGS 条件。位置权限只有 while-in-use 时，App 退到后台后不能继续假设完整定位能力；需要持续用户可见的定位时，应核对后台启动豁免、`location` FGS type、对应清单权限和运行时位置权限。

## 网络请求：减少唤醒、传输与失败重试

网络功耗由传输字节、连接建立、无线状态切换、信号质量、协议和设备实现共同决定。蜂窝与 Wi‑Fi 谁更省电没有跨设备结论，优化应围绕业务可控制的行为。

### 合并可延迟请求

- 日志、埋点、已缓存媒体和索引数据可以积累到大小、时限或网络条件满足后批量上传。
- 用户点击发送、支付确认等交互请求不能为了批量而延后。
- 复用 HTTP 连接，开启协议支持的压缩，使用增量接口、ETag 或版本游标减少重复字节。
- 失败按错误类型处理：网络瞬断可退避，服务端限流遵守 `Retry-After`，客户端参数错误应停止重试。
- 大文件支持断点续传和幂等提交，避免一次失败重传全部内容。

批量的收益来自减少 App 唤醒与连接建立次数。若批量让每次传输大到容易超时或触发内存压力，需要缩小批次，并在目标网络环境重新测量。

### 推送替代固定轮询

业务只有在服务端状态变化时才需要唤醒客户端，可以使用 FCM 或同类推送。FCM normal priority 适合普通同步，在 Doze 中可能延迟；high priority 只用于时间敏感、用户可见的内容，并应在收到后及时展示通知。长期发送 high priority 却没有用户可见结果，FCM 可能降低后续消息优先级或代理通知。

推送不能替代数据一致性设计。消息可能重复、延迟或丢失，客户端仍需用版本号或游标拉取缺失数据；低频兜底同步可交给 WorkManager。

## AlarmManager：精确性有明确成本

AlarmManager 用于进程生命周期之外的时间事件。普通同步、清理和重试更适合 WorkManager。若用户接受时间窗口，使用 `set()`、`setWindow()`、`setAndAllowWhileIdle()` 或不精确重复闹钟，让系统有机会合并唤醒。

### 精确闹钟权限与例外

Android 12（API 31）引入 “Alarms & reminders” special app access。Android 13+ 可根据受限使用场景选择 `SCHEDULE_EXACT_ALARM` 或 `USE_EXACT_ALARM`：

| 能力 | 授权方式 | 适用边界 |
| --- | --- | --- |
| `SCHEDULE_EXACT_ALARM` | 用户授予，也可被用户或系统撤销 | 使用面较宽；调用前检查 `canScheduleExactAlarms()` |
| `USE_EXACT_ALARM` | 安装时自动授予，用户不可撤销 | 只允许闹钟、计时器、日历等受限核心场景，并受 Google Play 政策约束 |

Android 14 对 target 33+ 的多数新安装应用不再预授予 `SCHEDULE_EXACT_ALARM`；备份恢复到 Android 14 设备时也按拒绝处理。已有授权随系统升级通常会保留。

`AlarmManager.OnAlarmListener` 形式的 `setExact()` 不要求 `SCHEDULE_EXACT_ALARM`。它是进程内监听器：进程退出后不能指望系统重新创建 App 来交付回调。需要跨进程生命周期可靠触发时，通常使用 `PendingIntent`，并遵守精确闹钟权限规则。这个例外不能用于构造后台保活。

### Doze 与 allow-while-idle

- `setAlarmClock()` 面向用户可见闹钟，系统会为交付离开低功耗模式。
- `setExactAndAllowWhileIdle()` 能穿过 Doze，但受到严格频率限制。
- `setAndAllowWhileIdle()` 允许在空闲状态交付不精确闹钟。
- 普通 Alarm 在 Doze 中可能延后到 maintenance window。

AlarmManager API 文档给出的正常条件下节流量级约为每个 App 九分钟一次，系统也可以拉长间隔。这个数值是防滥用边界，不是建议轮询周期。闹钟回调里只安排短操作；需要联网或持久执行时，把后续工作交给 JobScheduler 或 WorkManager。

## 前台服务：持续可见不等于无限运行

FGS 用持续通知表达用户知情的长任务，并提高进程重要性。它不免除 Doze、Job quota、网络限制或硬件资源管理。Android 14（target 34+）要求服务类型、类型权限和运行时前置条件同时成立：

- 未声明 `android:foregroundServiceType` 可能触发 `MissingForegroundServiceTypeException`。
- 缺少 `FOREGROUND_SERVICE_*` 权限，或 location、camera、microphone 等 while-in-use 条件不满足，可能触发 `SecurityException`。
- App 已在后台且不满足 FGS 启动豁免时，可能触发 `ForegroundServiceStartNotAllowedException`。

日志判读要区分声明、权限与启动资格，三个异常指向的修复位置不同。

### Android 14 与 Android 15 的超时

| 类型 | 平台限制 | 超时回调 | 未及时停止 |
| --- | --- | --- | --- |
| `shortService` | Android 14+，约三分钟 | `Service.onTimeout(int)` | 系统触发 ANR；系统不会代替服务自动完成 `stopSelf()` |
| `dataSync` | target 35+，后台状态下每 24 小时累计六小时 | `Service.onTimeout(int, int)` | 几秒内不停止会抛内部远程服务异常并终止进程 |
| `mediaProcessing` | target 35+，后台状态下每 24 小时累计六小时 | `Service.onTimeout(int, int)` | 与 `dataSync` 相同 |

六小时按类型分别计时，同一 App 的多个同类型服务共享该类型额度。用户把 App 带到前台会重置计时器。额度耗尽后继续启动同类型服务会收到 `ForegroundServiceStartNotAllowedException`。

`android-17.0.0_r1` 的 `ActiveServices.getTimeLimitedFgsType()` 把 `dataSync` 与 `mediaProcessing` 纳入此路径；宽限期结束后，`onFgsCrashTimeout()` 通过 `ForegroundServiceDidNotStopInTimeException` 终止宿主进程。`shortService` 使用独立的 ANR timer，两条超时路径不能混为同一种故障。

超时回调只应保存进度、释放资源并停止服务。数据同步可评估 WorkManager、user-initiated data transfer job 或 DownloadManager，选择时仍要接受对应 API 的调度和配额规则。

### Android 17 后台音频

Android 17（API 37）把后台播放、音频焦点请求和音量修改纳入音频 hardening：

- 所有运行在 Android 17 上的 App，无论 targetSdk，都要有可见 Activity，或正在运行一个类型不是 `shortService` 的 FGS，才能进行这些后台音频交互。
- target 37 的 App 在后台还要求该 FGS 具有 while-in-use（WIU）能力。通常由用户操作或 App 可见状态下启动的 FGS 获得。
- App 具有精确闹钟权限并操作 `USAGE_ALARM` 音频流时，WIU 要求可豁免；前一条“可见 Activity 或非 shortService FGS”仍然存在。

不满足条件时，播放和音量 API 可能静默失败，音频焦点请求返回 `AUDIOFOCUS_REQUEST_FAILED`。使用 `adb dumpsys audio` 或 logcat 搜索 `AudioHardening`：`level: partial` 表示没有运行 FGS，`level: full` 表示 FGS 缺少 WIU 能力。系统实现可对照 `AudioService.java` 与 `HardeningEnforcer.java`。

媒体播放服务仍需声明 `mediaPlayback` 类型及对应权限。播放永久结束、收到不可恢复的焦点丢失或用户明确停止后，应关闭播放器、media session 和 FGS。

## Camera 与 Audio 资源生命周期

### Camera

Camera 的开销受 sensor mode、分辨率、帧率、HDR、稳定算法、ISP 和编码路径影响。优化重点是让配置满足业务下限，并把资源生命周期缩到可见功能窗口内：

- 扫码或普通取景无需默认选择最大输出尺寸。
- `CONTROL_AE_TARGET_FPS_RANGE` 是请求范围，设备会结合 AE 与硬件能力选择帧率，不构成恒定帧率保证。
- 页面离开或任务结束时，停止 repeating request，关闭 `CameraCaptureSession`、`CameraDevice`，并释放不再使用的 Surface。
- App 退到后台后若 `dumpsys media.camera` 仍显示活跃 client，应检查会话和错误分支。

### Audio

采样率、声道数、格式、缓冲区、编解码器、offload 能力和输出路由共同决定音频开销。44.1 kHz、48 kHz 或 96 kHz 没有脱离内容与设备的统一优劣关系。应使用内容和设备支持的原生配置，避免无收益的重采样；长时间播放要检查硬件 offload 是否生效，短提示音则要避免维持不必要的常驻播放对象。

录音、播放、焦点和 media session 都要跟随用户会话结束。音频线程不工作时还持有 WakeLock，或播放停止后仍保留 FGS，是常见的额外待机成本。

## 证据驱动的排查流程

### 建立可复现窗口

记录机型、系统 build、App 版本、网络、屏幕亮度、温度、电池电量区间和操作脚本。对照组只改变一个变量；重复多轮后比较时间线与分布。测试期间的 USB 供电、调试器和屏幕常亮都可能改变结果。

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

### 按时间线归因

| 现象 | 证据入口 | 继续核对 |
| --- | --- | --- |
| 熄屏后仍无法 suspend | Battery Historian、batterystats history、Perfetto suspend | WakeLock UID/tag、wakeup source、Alarm 与 Job 是否重叠 |
| Job 被推迟或中止 | WorkInfo/JobParameters stop reason、jobscheduler | standby bucket、约束、Android 16 runtime quota |
| 位置持续活跃 | `dumpsys location`、Battery Historian | 请求 UID、priority、间隔、后台权限和移除时机 |
| 周期性唤醒 | Alarm、JobScheduler 时间线 | exact/allow-while-idle、重复 PendingIntent、失败重试 |
| FGS 长时间存在 | `dumpsys activity services`、Perfetto CPU/network | service type、业务进度、timeout、硬件资源 |
| 后台音频静默 | `dumpsys audio`、`AudioHardening` 日志 | Activity 可见性、FGS、WIU、targetSdk、usage |
| Camera 退出后仍活跃 | `dumpsys media.camera`、cameraserver trace | session、device、Surface 的关闭路径 |

Perfetto 轨道依赖 trace config、系统 build 和厂商实现。标准 user build 看不到 location、camera 或 wakelock 专用轨道时，应回到 bugreport 与系统服务状态，不能把“没有轨道”等同于“没有耗电”。

## 版本边界

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

## 复核清单

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
- FGS type、权限、启动资格和 timeout 是否分别处理？
- Android 17 后台音频是否满足非 shortService FGS、WIU 与 usage 规则？
- Camera、Audio、Surface、media session 是否在业务结束时关闭？
- 功耗结论是否来自目标设备、固定脚本和多轮对照？

## 与其他章节的关系

§11.1 解释系统如何把 CPU、屏幕、网络、GNSS 与其他组件能量归因到 UID；这里讨论 App 怎样减少这些组件的活跃时间。§5.6 说明 Doze 与 App Standby，§5.10 深入 JobScheduler/WorkManager，§11.5 追踪 WakeLock 在 PowerManagerService 与 suspend 路径中的实现。遇到“任务被推迟”或“设备不休眠”时，应沿这些章节的系统路径继续定位。

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
- [AOSP：AlarmManager.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/app/AlarmManager.java)
- [AOSP：AlarmManagerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java)
- [AOSP：ActiveServices.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/am/ActiveServices.java)
- [AOSP：AudioService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/audio/AudioService.java)
- [AOSP：HardeningEnforcer.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/audio/HardeningEnforcer.java)
- [Android 17 Kernel：pm_wakeup.h](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/include/linux/pm_wakeup.h)
- [Android 17 Kernel：wakeup.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c)
