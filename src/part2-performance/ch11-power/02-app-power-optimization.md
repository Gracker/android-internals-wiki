---
title: "App 耗电优化"
chapter: "11.2"
status: finalized
section: "11.2"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
rework_count: 5
rework_date: "2026-05-08"
rework_by: "task2b-rework"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-06-29"
last_verified_against: "AOSP android-17.0.0_r1, Android Developers Android 16 JobScheduler quota / Android 17 background audio / exact alarm / foreground service / WorkManager docs"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/power"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/wakelock"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent"
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
    path: "frameworks/base/services/core/java/com/android/server/audio/AudioService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/audio/HardeningEnforcer.java"
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
task2b_result: fixed
task2b_state: fixed
task6_state: revisiting
task9_state: reviewed
pipeline_stage: task6_pending
last_task2b_lite_at: "2026-06-06"
last_task2b_at: "2026-05-04T01:40:00+08:00"
task6_result: "pass-light-edit"
task9_result: auto-fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-06"
repaired_date: "2026-04-26"
repaired_by: "openclaw-task2b"
review_round: 5
task9_reviewed_date: "2026-06-06"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-06T19:20:00+08:00"
last_task9_autofix_at: "2026-06-29"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-27
last_task6_audit: "2026-06-27"
last_task9_audit: "2026-06-29"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-06
review_notes: "2026-05-08 10:28 task9 deep-review: pass-tech-review；无 P0/P1，Task6 已通过且 queue 无 pending 条目，自动晋升 finalized / ready-to-publish。；2026-06-06 17:20 task9 idle-audit: needs-rework；P1 Android 16 JobScheduler quota 与 Android 17 background audio hardening 版本差异回炉。；2026-06-06 19:20 task9 deep-review: pass-tech-review；复核 Android 16 JobScheduler quota 与 Android 17 background audio hardening 已补齐；无 P0/P1，Task6 已通过且 queue 无 pending 条目，自动晋升 finalized / ready-to-publish。；2026-06-29 12:29 task9 idle-audit: auto-fixed；AOSP 源码锚点升级到 android-17.0.0_r1，修正 Android 17 Audio 覆盖说明，回到 Task6 复审。"
---

# App 耗电优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 WakeLock 最佳实践：类型选择、超时设置、及时释放
- 🔹 后台任务省电策略：JobScheduler / WorkManager 的正确使用
- 🔹 位置服务功耗优化：精度选择、更新频率、Geofencing
- 🔹 网络请求功耗优化：批量请求、减少轮询、Push 替代 Pull
- 🔹 Alarm 使用规范：避免精确重复闹钟、使用 setAndAllowWhileIdle 的限制

### 扩展（可选深入）

- 🔸 前台服务的功耗考量与 Android 14+ 对 FGS 的限制
- 🔸 Camera/Audio 等硬件资源的功耗优化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要关注 App 耗电

§11.1 已经分析了 Android 的功耗模型——CPU 频率、屏幕亮度、网络模块、GPS，每一个硬件器件都有各自的功耗曲线，而 App 对这些器件的使用方式直接决定了用户手机能撑多久。

但问题在于，很多开发者对"耗电"没有直观感受。耗电不像卡顿那样有明确的 FPS 指标，也不像 ANR 那样有系统弹窗。用户只是觉得"今天手机掉电特别快"，然后打开设置→电池，看到一个 App 吃了 30% 的电量，直接卸载。

对系统开发者来说，理解 App 耗电的原因更关键——要判断某个 App 为什么在目标设备上特别费电，是 WakeLock 没释放、后台频繁拉起，还是网络轮询间隔太短。这些分析能力直接影响用户对设备续航的体感评价。

本章从五个耗电入口切入：WakeLock、后台任务调度、位置服务、网络请求和闹钟，覆盖 App 端耗电的主要来源，每个入口都会给出"在 Battery Historian / Perfetto 中怎么看到它"的分析方法。

## WakeLock 最佳实践

WakeLock 是 Android 提供的一种让 CPU 或屏幕保持唤醒的机制。设计初衷很合理——音乐播放需要 CPU 保持工作，导航需要屏幕常亮——但用不好的话，WakeLock 就是耗电的第一大来源。

[已验证: 官方文档, developer.android.com/reference/android/os/PowerManager.WakeLock]

### WakeLock 的类型与选择

Android 的 `PowerManager` 提供了几种不同级别的 WakeLock，每种控制的硬件范围不同。

**PARTIAL_WAKE_LOCK** 是最常见的类型。它只保持 CPU 运行，允许屏幕和键盘关闭。绝大多数后台工作只需要这种 WakeLock——比如在屏幕关闭后继续下载文件、处理数据。但正因为屏幕关闭了用户感知不到，如果忘记释放，设备就会在口袋里默默耗电。

其他类型的 WakeLock 控制屏幕行为(SCREEN_BRIGHT_WAKE_LOCK、SCREEN_DIM_WAKE_LOCK、FULL_WAKE_LOCK)，这些在 API 17 之后已经被标记为 deprecated，不应该继续使用。如果需要保持屏幕常亮，应该使用 `FLAG_KEEP_SCREEN_ON` 这个 Window flag 或者 `View.setKeepScreenOn(true)`，它们的功耗更可控——当 Activity 不可见时屏幕会自动关闭。

```java
// frameworks/base/core/java/android/os/PowerManager.java
// @ AOSP android-17.0.0_r1
// 获取 PARTIAL_WAKE_LOCK 的标准方式
PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
WakeLock wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MyApp:MyTag");
```

这里第二个参数是 WakeLock 的 tag，它必须是一个有意义的、硬编码的字符串。这个 tag 会出现在 Battery Historian 和 bugreport 中，是分析耗电问题的重要线索。不要使用动态生成的字符串或包含 PII 的信息。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/PowerManager.java]

### 获取与释放的正确姿势

WakeLock 的原则只有一条：**一定要释放**。不管代码走了哪个分支，不管有没有异常，WakeLock 必须被释放。

```java
wakeLock.acquire(60 * 1000L); // 带超时:最多持有 1 分钟
try {
    // 执行需要 CPU 保持唤醒的工作
    doBackgroundWork();
} finally {
    if (wakeLock.isHeld()) {
        wakeLock.release();
    }
}
```

这里有两个关键细节。第一，`acquire(long timeout)` 的超时参数是安全网——即使代码逻辑出了问题忘记调用 release，系统也会在超时后自动释放。建议所有 WakeLock 都设置超时，超时长度略大于预期工作时间即可。第二，`finally` 块中调用 `release()` 之前先检查 `isHeld()`，因为超时释放后再调用 release 会抛出 `RuntimeException`。

### Android Vitals 对 WakeLock 的监控

Android Vitals 会把 excessive partial wake locks 单独统计出来。局部判定条件是：一个 App 在 24 小时窗口内，后台或前台服务期间持有的非豁免 partial wake lock 累计达到 2 小时。平台侧再看 28 天滚动窗口，如果这类问题出现在超过 5% 的 app sessions 中，Play 可能在该指标脱离 beta 后影响可见性。音频、位置和 JobScheduler 的部分场景属于文档列出的豁免项。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/wakelock]

在 Battery Historian 中，WakeLock 持有期会以条形图显示在 `Partial Wakelock` 行。Perfetto 在打开 power data source 时可能包含 `power/wakelock` 轨道，但标准 user build 不保证这条轨道一定存在。排查时先从 bugreport、Battery Historian 和 `dumpsys batterystats --history` 入手，确认问题后再决定是否需要补抓 Perfetto。

## 后台任务省电策略：WorkManager 与 JobScheduler

Android 的后台任务调度经历了多轮演进，从最初的 Service + AlarmManager，到 JobScheduler（API 21），再到 Jetpack 的 WorkManager。演进始终围绕一个目标：省电。

### 为什么不推荐自己管理后台任务

手动管理后台任务的问题在于，App 看不到系统当前的省电策略。App 用 AlarmManager 设了一个 5 分钟的定时器，系统很难把它和其他 App 的定时任务统一安排，结果是设备隔几分钟就被唤醒一次。单看一个 App，代价不大；多个 App 叠加后，设备就很难稳定进入休眠。

Doze 模式就是拿来处理这种叠加效应的。设备静止、屏幕关闭一段时间后，系统会把非豁免的后台活动延后到维护窗口集中执行。App 自己设的闹钟、注册的 JobScheduler 任务和后台网络请求，都会一起受这个调度策略约束。

### WorkManager：后台任务的首选方案

WorkManager 是 Google 推荐的后台任务调度 API，它封装了 JobScheduler（API 23+）和 AlarmManager + BroadcastReceiver（旧版本）的差异，提供统一的接口。

WorkManager 的省电优势在于**约束条件（Constraints）**和**任务合并**。

```kotlin
// 使用约束条件:仅在充电 + WiFi 时执行
val constraints = Constraints.Builder()
    .setRequiresCharging(true)
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .build()

val uploadWork = OneTimeWorkRequestBuilder<UploadWorker>()
    .setConstraints(constraints)
    .build()

WorkManager.getInstance(context).enqueue(uploadWork)
```

这段代码定义了一个上传任务，但不会立即执行。系统会等待设备在充电且连接 WiFi 时再调度执行。对用户来说，这种延迟通常无感；对电池来说，收益也很直接，因为任务会尽量落在更适合的网络和供电条件下。

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/workmanager]

WorkManager 的几个关键省电配置：

**最小间隔 15 分钟**。周期性任务（PeriodicWorkRequest）的最小间隔是 15 分钟。这个值对应系统 JobScheduler 的最小调度窗口，不是随意定的下限。不要试图绕过这个限制。

**谨慎使用 Expedited Work**。`setExpedited()` 会争取更快启动，但它仍受 quota 和 `OutOfQuotaPolicy` 约束。它适合用户刚触发、需要尽快开始且执行时间较短的任务；如果只是常规同步或周期性工作，继续用普通 WorkRequest。更细的配额和 fallback 语义可对照 §5.10。

**合理安排任务顺序**。多个有依赖关系的任务可以用 WorkManager 的 `then()` 接在一起，系统更容易把它们放进同一批执行窗口，减少额外唤醒。

**能效提示 ADPF setPreferPowerEfficiency（Android 15+）**。WorkManager 本身没有能效标记 API。能效提示应走 ADPF 的 `PerformanceHintManager.Session.setPreferPowerEfficiency(boolean)`(Android 15 / API 35+)。当任务不紧急时传入 `true`，向系统声明这组线程可偏向能效；系统/OEM 策略可据此调整频率、核心放置或功耗策略——但不保证一定绑到低功耗核心，具体行为取决于设备实现和 Power HAL。这套机制面向的是正在执行的计算密集型任务(如后台数据同步、日志处理)，而不是 WorkManager 的调度决策。WorkManager 仍按约束(constraints)、配额(quota)、standby bucket、expedited / UIDT 等机制调度。

### JobScheduler 的定位

如果项目没有使用 Jetpack，或者需要直接与系统服务交互，JobScheduler 仍然是有效的选择。它的核心机制与 WorkManager 底层相同：通过 `JobInfo.Builder` 设置约束条件，系统在合适的时机调度执行。

WorkManager 和 JobScheduler 的选择不需要纠结：新项目用 WorkManager，已有项目迁移到 WorkManager。不需要两者混用。

Android 16 起，前台服务期间启动的 JobScheduler / WorkManager / DownloadManager job 会受运行时配额限制，排查细节见下文「Android 16 的 JobScheduler 配额优化」。

### 在 Battery Historian 中的表现

后台任务调度的效率可以通过 Battery Historian 的 "JobScheduler" 行观察。如果看到某个 App 的 Job 条频繁出现且间隔很短(比如每几分钟一次)，说明任务调度过于激进。正常情况下，后台任务的调度间隔应该与设置的约束条件匹配——只有在满足约束时才执行。

[待补充: Battery Historian 截图展示 JobScheduler 和 WorkManager 的正常/异常调度模式]

## 位置服务功耗优化

位置服务是 Android 中较高功耗的硬件子系统之一。持续 GNSS 定位通常比只用 WiFi 和基站的粗定位更耗电，但具体电流与 SoC、GNSS 芯片、屏幕状态和采样窗口强相关，不能把某个机型的数值当成通用结论。

[已验证: 官方文档, developer.android.com/training/location]

### Fused Location Provider 与精度选择

Google Play Services 提供的 Fused Location Provider（FLP）是现代 Android 定位的推荐方案。它会智能地融合 GPS、WiFi、基站、传感器数据，在满足精度需求的前提下选择功耗最低的定位源。

FLP 提供四种精度级别，对应不同的功耗：

**PRIORITY_BALANCED_POWER_ACCURACY** 是大多数 App 应该使用的默认选择。它通常不启用 GPS，依靠 WiFi 和基站信息提供街区级（约 100 米）精度，功耗通常低于 GPS。社交类 App 的"附近的人"、天气 App 的城市定位、本地搜索，这些场景用这个精度就够了。

**PRIORITY_HIGH_ACCURACY** 会启用全部定位源包括 GPS，功耗最高。只有在导航、跑步追踪等需要精确位置的场景才使用，而且应该只在 App 处于前台时启用。

**PRIORITY_LOW_POWER** 仅使用基站，精度为城市级（约 10 公里），功耗最低。

**PRIORITY_PASSIVE** 完全不主动请求定位，只被动接收其他 App 触发的位置更新。功耗几乎为零。

[已验证: 官方文档, developer.android.com/training/location/receive-location-updates]

```kotlin
// 精度与功耗的平衡:只在需要时请求高精度
val locationRequest = LocationRequest.Builder(
    Priority.PRIORITY_BALANCED_POWER_ACCURACY,
    60_000L  // 更新间隔 60 秒
).apply {
    setMaxUpdateDelayMillis(300_000L)  // 批量交付:最长延迟 5 分钟
    setDurationMillis(TimeUnit.HOURS.toMillis(1))  // 自动超时 1 小时
}.build()
```

这段代码有两个省电要点。第一，`setMaxUpdateDelayMillis()` 启用了批量交付模式：FLP 内部按 60 秒间隔计算位置，积累最多 5 分钟后一次性交付一批位置更新。App 唤醒次数从每分钟一次降到每 5 分钟一次——以延迟换功耗。

第二，`setDurationMillis()` 设置了自动超时。即使忘记移除位置请求，1 小时后 FLP 会自动停止更新，防止因代码缺陷导致无限定位。

### Geofencing 的省电优势

Geofencing（地理围栏）仍然是位置场景里相对省电的入口，因为 App 不必自己保活轮询。设备进入或离开指定区域时，系统再通过 PendingIntent 或 BroadcastReceiver 通知 App。从 Android 8.0（API 26）开始，后台 geofence 事件的响应频率会放宽到 every couple of minutes，这是系统用延迟换电量的明确策略。

```kotlin
// Geofencing:系统级省电
val geofence = Geofence.Builder()
    .setRequestId("store-001")
    .setCircularRegion(latitude, longitude, 200f)  // 200 米半径
    .setExpirationDuration(TimeUnit.HOURS.toMillis(2))  // 2 小时后自动失效
    .setTransitionTypes(Geofence.GEOFENCE_TRANSITION_ENTER)
    .build()
```

Geofencing 省电的关键，在于围栏判断由 FLP、Play services 和系统位置栈统一调度，而不是 App 每隔几秒自己请求一次定位。

**GNSS 硬件围栏卸载**。支持硬件围栏的 GNSS 芯片可以把 Geofencing 判定卸载到硬件执行，CPU 不需要保持唤醒即可维持围栏检测。设备进入 Doze 或 CPU 深度休眠后，GNSS 芯片仍然能独立判断进出围栏事件，再通过中断唤醒系统通知 App。硬件卸载是否可用取决于设备能力：通过 `GnssCapabilities.hasGeofencing()`（API 34+）或 `dumpsys location` 查看 Geofence 的实现路径（software / hardware）。如果设备只支持软件模式，Geofencing 的功耗优势仍然存在但幅度更小。

Geofencing 适合低频、事件驱动的位置需求；如果业务要秒级连续轨迹，就该回到显式定位请求，并单独评估功耗。

[已验证: 官方文档, developer.android.com/training/location/geofencing]

### 在 Perfetto 中的表现

位置相关问题先从 bugreport、`dumpsys location` 和 Battery Historian 入手。标准 user build 不一定有公开的 `Location Manager` 或 `GPS` 轨道——部分设备会提供厂商特定的 location data source，部分不会。排查时先确认谁在请求定位、请求是否已进入后台，再决定是否补抓 Perfetto。

[待补充: `dumpsys location`、Battery Historian 与 vendor trace 的对照图]

## 网络请求功耗优化

网络模块是仅次于屏幕和 CPU 的第三大功耗来源。移动数据（Cellular）的功耗远高于 WiFi，而网络模块从休眠到活跃的状态切换本身就消耗能量——即使只传几个字节，射频模块也需要几百毫秒的启动时间。

### 批量请求与减少轮询

优化网络请求功耗，就是减少射频模块的唤醒次数。

假设一个 App 每 5 秒向服务器轮询一次数据，每次传输 100 字节。从数据量看，一小时只有 72KB，微不足道。但从射频模块的角度看，每小时 720 次唤醒——每次唤醒射频模块都要从休眠状态切换到活跃状态，这个过程消耗的能量可能比传输 100 字节本身还多。

解决方案是**批量请求**：将多次小请求合并为一次大请求。如果业务允许，将轮询间隔从 5 秒延长到 30 秒或更长；更好的做法是使用 Push 模式替代 Pull 模式。

### Push 替代 Pull

Firebase Cloud Messaging（FCM）是 Android 推荐的消息推送方案。它的省电优势在于，多个 App 可以复用同一条 TCP 长连接，系统不必为每个 App 各养一条常驻连接。相反，如果每个 App 都自己维护长连接轮询，随着 App 数量增加，常驻网络连接也会跟着变多。

FCM 分为两种优先级：

**高优先级消息**(high priority)会争取立即送达，适合需要马上展示用户可见通知的场景。但如果 FCM 在 7 天行为窗口里发现这些消息没有带来 user-facing notifications，后续消息可能被降级为 normal priority，也可能改由 Google Play services 代理展示通知。高优先级不是通用保活通道，它只适合需要打到用户面前的事件。

**普通优先级消息**(normal priority)会在设备下次活跃时才送达，不会额外唤醒设备。用于数据同步、内容更新等不需要立即处理的场景。

[已验证: 官方文档, firebase.google.com/docs/cloud-messaging/android/message-priority]

### 网络约束与 WorkManager 配合

对于大文件上传、数据同步等可延迟的网络操作，通过 WorkManager 设置网络约束是最佳实践：

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)  // 仅 WiFi
    .build()

val syncWork = OneTimeWorkRequestBuilder<SyncWorker>()
    .setConstraints(constraints)
    .setBackoffCriteria(  // 失败后退避
        BackoffPolicy.EXPONENTIAL,
        30, TimeUnit.SECONDS
    )
    .build()
```

这里 `UNMETERED` 指定只在 WiFi 下执行，比 `CONNECTED`(任何网络)更省电。同时 `setBackoffCriteria()` 设置了指数退避。如果网络请求失败，任务不会立即重试，而是按指数增长的间隔重试，避免在网络不稳定时反复唤醒射频模块。

[已验证: 官方文档, developer.android.com/reference/androidx/work/NetworkType]

## Alarm 使用规范

AlarmManager 是 Android 最早的定时机制，也是被滥用最多的 API 之一。在 WorkManager 和 JobScheduler 已经成熟的今天，AlarmManager 的合理使用场景已经非常有限。

### 精确闹钟与功耗

Android 的闹钟分为两种：精确闹钟(exact alarm)和不精确闹钟(inexact alarm)。

精确闹钟(`setExact()`、`setExactAndAllowWhileIdle()`、`setAlarmClock()`)会在接近指定时间触发，系统能做的合并空间很小。如果 10 个 App 各设了一个精确闹钟，设备就可能被唤醒 10 次。

不精确闹钟(`set()`、`setWindow()`、`setAndAllowWhileIdle()`)由系统在更宽的时间窗口里调度，可以与其他闹钟合并执行，功耗更低。

[已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager]

### Android 12 引入精确闹钟 special app access，Android 14 调整默认授权策略

`SCHEDULE_EXACT_ALARM` 不是 Android 14 才出现的限制。Android 12（API 31）已经把它作为精确闹钟的 special app access 引入。所有精确闹钟 API——包括 `setExact()`、`setExactAndAllowWhileIdle()` 和 `setAlarmClock()`——都属于 exact alarm 能力，受 `SCHEDULE_EXACT_ALARM` special app access 约束。调用前应通过 `AlarmManager.canScheduleExactAlarms()` 检查授权状态；没有授权时，用 `Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM` 引导用户进入系统设置页。

`setAlarmClock()` 与 `setExact*()` 的差异在于 Doze 行为：`setAlarmClock()` 在 Doze 模式下会正常触发(系统会在闹钟时间前退出 Doze)，而不是"不需要权限"。它同样受 exact alarm 权限/ 豁免资格约束。闹钟和日历类应用可以声明 `USE_EXACT_ALARM` 来获得豁免。

Android 14（API 34）的变化在默认授权策略。对 targetSdk 33+ 的多数新安装应用，`SCHEDULE_EXACT_ALARM` 不再预授予，备份恢复到 Android 14 设备时也按 denied 处理。系统升级前已经拿到这项 special app access 的存量应用，升级后通常会保留授权。闹钟和日历这类以精确提醒为主功能的应用，可以按官方分类声明 `USE_EXACT_ALARM`。

落实到业务上：如果只是定时同步、重试、批量上报，优先用 WorkManager 或不精确闹钟；只有提醒、闹钟、倒计时这类用户明确期待准点触发的场景，才值得继续用 exact alarm。

[已验证: 官方文档, developer.android.com/about/versions/14/changes/schedule-exact-alarms]

### setAndAllowWhileIdle 的使用限制

`setAndAllowWhileIdle()` 和 `setExactAndAllowWhileIdle()` 能在 Doze 中触发，但它们不是仅有的例外，`setAlarmClock()` 也会正常触发，系统会在闹钟到点前退出 Doze。实际排查时，按下面三类区分：

- `setAlarmClock()`：面向用户可见闹钟，正常触发。
- allow-while-idle alarms：可以穿过 Doze，但受频率限制，文档给出的节流口径大约是每个 App 每 9 分钟一次。
- 普通 `set()`、`setWindow()`、`setExact()`：Doze 期间会被推迟到 maintenance window。

这几类能力的设计目标都是让必要事件发生，不给 App 提供高频保活通道。

### 在 Battery Historian 中的表现

AlarmManager 的使用情况在 Battery Historian 的 "Alarm" 行中显示。如果看到某个 App 频繁触发闹钟(特别是精确闹钟)，说明需要迁移到 WorkManager 或使用不精确闹钟。

[待补充: Battery Historian 截图展示精确闹钟与不精确闹钟的调度差异]

## 前台服务的功耗考量与 Android 14+ 的限制

前面讨论的后台任务调度和 Alarm 优化，核心思路都是"尽量让系统决定什么时候执行"。但有些场景 App 需要持续在后台运行，比如音乐播放、导航、位置追踪。前台服务会通过持续通知告诉用户"这个 App 还在工作"，同时提高进程优先级，降低因后台限制被回收的概率。它解决的是 app-level background limits 问题，本身不提供 device-level Doze 豁免。设备进入 Doze 后，网络、Job、普通 Alarm 等限制仍然存在，wake lock 也会被忽略。

Android 14（API 34）对 FGS 的治理经历了重大变革，系统从"信任开发者声明"转向"强制类型分类 + 运行时权限验证"。

### FGS 类型与权限

Android 14 要求前台服务同时满足三层约束：Manifest 里的 `android:foregroundServiceType`、对应的 `FOREGROUND_SERVICE_*` 清单权限，以及运行时前置条件。

- **缺少 service type**：targetSdk 34+ 的服务如果没有声明 `foregroundServiceType`，调用 `startForeground()` 时会抛 `MissingForegroundServiceTypeException`。
- **类型权限或运行时权限不满足**：如果缺少对应的 `FOREGROUND_SERVICE_*` 权限，或者 location / camera / microphone 这类 while-in-use 权限在当前状态下不可用，系统更常抛 `SecurityException`。
- **后台启动条件不满足**：如果问题出在 background start exemption 不成立，例如应用已经退到后台又不满足豁免条件，常见结果是 `ForegroundServiceStartNotAllowedException`。

排查 FGS 失败时，要把这三类入口分开看。把"类型和权限不匹配"一概归到 `MissingForegroundServiceTypeException`，会把日志判读带偏。

新增的 FGS 类型中，有两个值得特别关注：

**shortService**：专为短时间(约 3 分钟)的关键工作设计。如果超时未完成，系统会停止服务。这个类型适合一次性文件加密、紧急数据保存等场景——它有明确的功耗上限，不会无限持有。

**dataSync**：`dataSync` 仍是有效的 foreground service type，但官方已经给出替代方向，例如 WorkManager、user-initiated data transfer jobs 和 DownloadManager。对于系统开发者来说，长时间运行的 `dataSync` FGS 仍然应该被视为优先优化对象，只是不能把它写成"已经 deprecated"。

[已验证: 官方文档, developer.android.com/about/versions/14/changes/fgs-types-required]

### Android 15 的进一步限制

Android 15（API 35）对 `dataSync` 和新增的 `mediaProcessing` 类型引入了 6 小时 / 24 小时的后台预算。这个 budget 按 service type 统计，同一 App 的多个 `dataSync` 实例共享同一个窗口；用户把 App 带回前台后，对应计时器才会重置。

到点后，系统会回调 `Service.onTimeout(int, int)`(注意：这是双参数版本，区别于 `shortService` 的单参数 `onTimeout(int)`)；服务有几秒钟调用 `stopSelf()` 自行结束。若没有及时停止，`ActiveServices.onFgsCrashTimeout()` 会抛出 `ForegroundServiceDidNotStopInTimeException`，进程直接 crash（不是 ANR）。把这条路径和 `shortService` 的 ANR 路径分开看：

- **shortService**(Android 14 引入)：约 3 分钟超时，回调 `onTimeout(int)`，未停止 → ANR。
- **dataSync / mediaProcessing**(Android 15 引入)：6h / 24h budget 耗尽，回调 `onTimeout(int, int)`，未停止 → crash(`ForegroundServiceDidNotStopInTimeException`)。
- **Android 14 及以下**：没有 `onTimeout(int, int)` 回调，不适用此 timeout 机制。

`onTimeout()` 触发后，系统已经把这个 App 的对应 service type 预算标记为耗尽。此时再尝试启动同类型的 FGS 会抛 `ForegroundServiceStartNotAllowedException`，这不是软限制，是系统层面的最终判决——和 `shortService` 超时后的 ANR 一样，都是强制终止路径。剩余收尾只做资源释放、进度持久化和替代任务调度；大文件上传或下载优先迁到 WorkManager、user-initiated data transfer job 或 DownloadManager。服务如果需要下一轮工作，等用户重新把 App 带到前台(这会重置对应 service type 的计时器)，再由正常入口启动。

[已验证: 官方文档, developer.android.com/develop/background-work/services/fgs/timeout]

### Android 16 的 JobScheduler 配额优化

Android 16 起，前台服务期间并发运行的 JobScheduler、WorkManager 和 DownloadManager job 会遵守各自的运行时配额。从 top state 启动后继续运行的 job 也会计入配额。这意味着把 WorkManager 或 DownloadManager 当成 FGS 的"免费"替代路径不再成立——它们和 FGS 共享后台预算。

排查时关注 `WorkInfo.getStopReason()` 或 `JobParameters.getStopReason()`，结合 standby bucket 判断 job 是否因配额耗尽被系统终止。用户触发的大文件传输优先使用 user-initiated data transfer job，这类 job 有独立的配额窗口，不受 FGS 并发配额约束。

### FGS 的功耗分析方法

分析 App 的功耗时，先分清楚问题落在哪个对象上。WakeLock、定位、FGS 和 Camera 的证据入口各不相同，标准 user build 也不保证每类都有稳定的 Perfetto 轨道。

| 问题类型 | 推荐抓取方式 | 主要观察面(轨道/表) | 适用版本 / 前提 |
| --- | --- | --- | --- |
| WakeLock 长持有 | bugreport → Battery Historian,必要时补抓 Perfetto power data source | Battery Historian `Partial Wakelock`、`dumpsys batterystats --history`、Perfetto `power/wakelock` | Android 6+;Perfetto 轨道依赖 trace config 和设备支持 |
| 定位请求过密 | bugreport + `dumpsys location`,有厂商 / userdebug 数据源时再补 Perfetto | `dumpsys location` active requests、Battery Historian 的位置 / 网络活动、vendor-specific location/GNSS 轨道 | Android 8+ 背景限制更明显;标准 user build 不保证公开 `GPS` 轨道 |
| FGS 跑太久 | bugreport + Perfetto + `dumpsys activity services` | `dumpsys activity services`、Perfetto app/service slices、Battery Historian 前后台状态 | Android 14+ 重点看 service type;Android 15+ 额外看 timeout |
| Camera 后台未释放 | bugreport + `dumpsys media.camera`,设备支持时补抓 camera / vendor trace | `dumpsys media.camera` 活跃 client、Battery Historian Camera 使用、camera/cameraserver/vendor 轨道 | Camera HAL 轨道依赖厂商实现,user build 常常没有公共轨道 |

判断 FGS 是否真的需要时，要把服务存活时间放到和 CPU、network、Binder 活动同一时间轴上看。如果服务长时间存在，但对应线程几乎不工作，问题通常不在 FGS API 本身，而在业务把它当成常驻后台容器。

如果 Perfetto 里刚好能看到 `power/wakelock`、location、camera 这些轨道，它们适合拿来和 CPU、Binder、network 活动看先后关系。看不到也不代表问题不存在，先回到 bugreport、Battery Historian 和 `dumpsys`，通常更稳。

## Camera/Audio 等硬件资源的功耗优化

除了 CPU、网络、GPS 这些常见入口，Camera 和 Audio 也经常把功耗问题藏在业务路径里。视频通话、扫码、直播、持续录音这类场景里，持续耗电的是 sensor、ISP、codec 和 display 这一整条流程，不只是 App 自己的代码。

### Camera

Camera 往往是高功耗器件，实际开销和分辨率、帧率、HDR、EIS/OIS、编码路径、ISP pipeline 都强相关，不能把某个机型的电流值直接外推到所有设备。优化时先看三个动作：缩短打开时长、降低不必要的预览负载、离开场景后立刻释放资源。

**降低预览负载**。如果业务只需要扫码或拍照预览，没有必要长期维持最高分辨率和最高帧率。Camera2 可以通过 `CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE` 配合 `setRepeatingRequest()` 控制目标预览帧率，但实际收益要按设备实测，因为 sensor mode 和 ISP 策略并不统一。

**及时释放 Camera 资源**。Camera2 的关闭链应以 `CameraCaptureSession.close()` 和 `CameraDevice.close()` 为核心，同时回收不再使用的 Surface。`CameraManager` 负责枚举和打开设备，不提供 `closeCamera()` 这类 API。若 App 退到后台后 `dumpsys media.camera` 里仍能看到活跃 client，就应该先排查资源泄漏。

[已验证: 官方文档, developer.android.com/reference/android/hardware/camera2/CameraDevice]

### Audio

Audio 的功耗优化主要关注两个方面：

**避免使用不必要的高采样率**。多数普通媒体播放和语音业务用 44.1kHz 或 48kHz 就够了。96kHz 更常见于专业采集、低延迟监听或外接音频接口场景，是否值得开启要看 codec、输出路径和设备是否真的支持高采样率直通。若最终仍在 AudioFlinger / HAL 里被重采样，处理开销会上去，听感收益不一定能保留下来。

**后台音频要分开看 FGS 启动限制和类型声明**。后台音频如果需要长时间播放，应使用前台服务向用户展示持续通知。Android 12 的变化是限制后台直接启动 FGS：App 退到后台后，只有满足豁免条件才能启动前台服务。Android 14（targetSdk 34+）才强制要求在 manifest 中声明 `foregroundServiceType="mediaPlayback"`，并声明 `FOREGROUND_SERVICE_MEDIA_PLAYBACK` 权限。不要把 Android 12 的启动限制写成 Android 14 的类型强制。

**Android 17 / API 37 的 background audio hardening。** Android 17 对后台音频播放进一步收紧：后台音频交互（播放、焦点变更、音量调节）需要可见 Activity 或非 `shortService` 的 FGS；targetSdk 37 后还要求具备 while-in-use 能力，或在 exact alarm 权限 + `USAGE_ALARM` 场景下操作。本节 Audio 部分覆盖到 Android 17（API 37）。排查 Android 17 设备上后台音频失败时，需同时检查 `AudioHardening` 日志和 FGS 类型声明。

## 与其他章节的关系

App 耗电优化不是孤立的话题，它与全书的多个章节形成上下游关系。

从系统层面看，§11.1 分析了各硬件模块的功耗参数，是判断"优化哪个模块收益最大"的依据。§5.4 DVFS 机制在 CPU 层面动态调节频率和电压，App 减少不必要的 CPU 使用时间，就是在配合 DVFS 让设备更快进入低频低功耗状态。§5.6 Doze 和 App Standby 是系统对后台行为的全局管控，理解了这些机制的设计意图，才能写出不会与系统优化"打架"的 App。

从关联问题看，§9.2 ANR 分析中经常遇到一个矛盾：一些 App 为了避免主线程阻塞导致 ANR，把本该在主线程的工作推到后台 Service 中持续执行，结果 ANR 是少了，功耗却上去了。§5.10 对 JobScheduler 和 WorkManager 的底层调度机制做了更深入的分析，可以帮助理解 WorkManager 的约束条件在 JobScheduler 层面是怎么实现的。§11.5 对 WakeLock 的系统级机制(PowerManagerService 的 wakelocks 管理)有更详细的源码分析。

## 常见问题与误区

### 误区一："WakeLock 只要不一直持有就没事"

实际情况是，频繁地获取和释放 WakeLock（比如每秒 acquire/release 一次）同样会造成功耗问题。每次 acquire 都会通知 PowerManagerService 更新系统的 wakefulness 状态，涉及 Binder 调用和锁竞争。如果需要频繁的短时间唤醒，应该用一次较长时间的 acquire 覆盖整个工作周期，而不是反复 acquire/release。

### 误区二："WorkManager 的约束条件设得越多越好"

约束条件过多会导致任务长期无法执行，积累后可能在工作条件满足时集中爆发，造成瞬时高功耗。合理的做法是根据业务需求设置核心约束——比如大文件上传需要 WiFi 和充电，但普通数据同步只需要 WiFi 即可。

### 误区三："GPS 没开就不会耗电"

即使 App 请求了 PRIORITY_HIGH_ACCURACY，而用户在系统设置中关闭了 GPS，FLP 仍然会尝试通过 WiFi 和基站提供定位，但精度会低于预期。App 不应该因为精度达不到要求就持续请求高精度——这会导致 WiFi 和基站扫描频率升高。应该根据实际场景选择合适的精度级别。

### 误区四："前台服务有通知就不会被系统杀"

Android 14 的 FGS Task Manager 让用户可以直接看到并停止前台服务。Android 15 又给 `dataSync` 和 `mediaProcessing` 加了 6 小时 / 24 小时 budget，到点后系统回调 `Service.onTimeout(int, int)`。如果服务没有及时 `stopSelf()`，进程会被 `ForegroundServiceDidNotStopInTimeException` crash 掉(不是 ANR——ANR 是 `shortService` 的超时路径)；单靠通知栏常驻并不能换来无限时运行。

### 误区五："用了 WorkManager 就不用关心功耗了"

WorkManager 比手动调度更省电，但它不是银弹。如果 App 注册了大量 PeriodicWorkRequest 且间隔很短(比如多个 15 分钟间隔的周期任务)，系统仍然需要频繁唤醒。最佳实践是将多个周期性任务合并为一个，或者利用任务的输出作为下一个任务的触发条件，减少总调度次数。

## 参考资料

- [Android 官方:优化电池寿命](https://developer.android.com/topic/performance/power)
- [Android 官方:Doze 和 App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Android 官方:Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/wakelock)
- [Android 官方:后台执行指南](https://developer.android.com/guide/background)
- [Android 官方:WorkManager 指南](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Android 官方:位置服务功耗优化](https://developer.android.com/training/location)
- [Android 官方:Foreground service types are required](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 官方:Foreground service timeout behavior](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android 官方:Android 16 JobScheduler quota optimizations](https://developer.android.com/about/versions/16/behavior-changes-all#job-quota-opt)
- [Android 官方:Android 17 background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Android 官方:CameraDevice API](https://developer.android.com/reference/android/hardware/camera2/CameraDevice)
- [AOSP PowerManager.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/os/PowerManager.java)
- [AOSP PowerManagerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java)
- [AOSP AudioService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/audio/AudioService.java)
- [AOSP HardeningEnforcer.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/audio/HardeningEnforcer.java)
- [Android 官方:位置服务 Geofencing](https://developer.android.com/training/location/geofencing)
- [Firebase 官方:Set and manage Android message priority](https://firebase.google.com/docs/cloud-messaging/android/message-priority)
- [Android 官方:Battery Historian 使用指南](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [来源： Obsidian Cubox - 借助 Android Studio 中的功耗性能分析器进行 A-B 测试]
- [来源： Obsidian Cubox - 谈功耗是什么]
- [来源： Obsidian Cubox - SoC 低功耗问题定位及优化的 10 个思路]
- [来源： Obsidian Cubox - BatteryHistorian Android 手机耗电分析神器]
- [来源： Obsidian Cubox - 抖音功耗优化实践]
