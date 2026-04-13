---
title: "App 耗电优化"
chapter: "11.2"
status: ready-for-review
section: "11.2"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-13"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/power"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: official
    path: "https://developer.android.com/guide/background"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: blog
    path: "Obsidian Cubox - 借助 Android Studio 中的功耗性能分析器进行 A-B 测试"
  - type: blog
    path: "Obsidian Cubox - SoC 低功耗问题定位及优化的 10 个思路"
  - type: blog
    path: "Obsidian Cubox - 抖音功耗优化实践"
  - type: blog
    path: "Obsidian Cubox - BatteryHistorian Android 手机耗电分析神器"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager.WakeLock"
  - type: official
    path: "https://firebase.google.com/docs/cloud-messaging"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/fgs-types"
  - type: official
    path: "https://developer.android.com/about/versions/15/changes"
tags: ['wakelock', 'jobscheduler', 'workmanager', 'doze', 'location', 'alarm', 'power', 'fgs', 'foreground-service', 'fcm', 'alarmmanager', 'geofencing', 'battery-historian', 'camera']
related_chapters: ["11.1", "11.3", "5.6", "5.4", "5.10", "11.5"]
task9_result: needs-rework
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: needs-rework
task9_state: reviewed
task2b_state: pending
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

上一章我们拆解了 Android 的功耗模型——CPU 频率、屏幕亮度、网络模块、GPS，每一个硬件器件都有各自的功耗曲线，而 App 对这些器件的使用方式直接决定了用户手机能撑多久。

但问题在于，很多开发者对"耗电"没有直观感受。耗电不像卡顿那样有明确的 FPS 指标，也不像 ANR 那样有系统弹窗。用户只是觉得"今天手机掉电特别快"，然后打开设置→电池，看到一个 App 吃了 30% 的电量，直接卸载。

对系统开发者来说，理解 App 耗电的原因更为关键——我们需要知道为什么某个 App 在我们的设备上特别费电，是 WakeLock 没释放、后台频繁拉起、还是网络轮询间隔太短。这些分析能力直接影响用户对设备续航的体感评价。

本章从五个最常见的耗电入口切入：WakeLock、后台任务调度、位置服务、网络请求和闹钟，覆盖 App 端耗电的主要来源，每个入口都会给出"在 Battery Historian / Perfetto 中怎么看到它"的分析方法。

## WakeLock 最佳实践

WakeLock 是 Android 提供的一种让 CPU 或屏幕保持唤醒的机制。它的本意是好的——音乐播放需要 CPU 保持工作，导航需要屏幕保持常亮——但如果使用不当，WakeLock 会成为头号耗电杀手。

[已验证: 官方文档, developer.android.com/reference/android/os/PowerManager.WakeLock]

### WakeLock 的类型与选择

Android 的 `PowerManager` 提供了几种不同级别的 WakeLock，每种控制的硬件范围不同。

**PARTIAL_WAKE_LOCK** 是最常见的类型。它只保持 CPU 运行，允许屏幕和键盘关闭。绝大多数后台工作只需要这种 WakeLock——比如在屏幕关闭后继续下载文件、处理数据。但正因为屏幕关闭了用户感知不到，如果忘记释放，设备就会在口袋里默默耗电。

其他类型的 WakeLock 控制屏幕行为（SCREEN_BRIGHT_WAKE_LOCK、SCREEN_DIM_WAKE_LOCK、FULL_WAKE_LOCK），这些在 API 17 之后已经被标记为 deprecated，不应该继续使用。如果需要保持屏幕常亮，应该使用 `FLAG_KEEP_SCREEN_ON` 这个 Window flag 或者 `View.setKeepScreenOn(true)`，它们的功耗更可控——当 Activity 不可见时屏幕会自动关闭。

```java
// frameworks/base/core/java/android/os/PowerManager.java
// @ AOSP android-16.0.0_r1
// 获取 PARTIAL_WAKE_LOCK 的标准方式
PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
WakeLock wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MyApp:MyTag");
```

这里第二个参数是 WakeLock 的 tag，它必须是一个有意义的、硬编码的字符串。这个 tag 会出现在 Battery Historian 和 bugreport 中，是我们分析耗电问题的重要线索。不要使用动态生成的字符串或包含 PII 的信息。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PowerManager.java]

### 获取与释放的正确姿势

WakeLock 最关键的原则只有一条：**一定要释放**。不管代码走了哪个分支，不管有没有异常，WakeLock 必须被释放。

```java
wakeLock.acquire(60 * 1000L); // 带超时：最多持有 1 分钟
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

Google Play 已开始把 WakeLock 滥用纳入应用质量评估。[待验证: 2026 年 3 月是否为正式生效时间，需与最新 Android Vitals 文档交叉确认] 文档当前给出的口径是，如果一个 App 在 24 小时内后台持有的 PARTIAL_WAKE_LOCK 累计超过 2 小时，并且这种情况影响了超过 5% 的用户，App 在 Play Store 中的可见性会降低。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/wakelock]

在 Battery Historian 中，WakeLock 持有期会以条形图显示在 "Partial Wakelock" 行中。如果我们看到某个 App 的 WakeLock 条横跨了很长时间且没有间断，基本上就是释放逻辑有问题。在 Perfetto 中，WakeLock 的持有可以通过 `power/wakelock` track 观察。

## 后台任务省电策略：WorkManager 与 JobScheduler

Android 的后台任务调度经历了多轮演进，从最初的 Service + AlarmManager，到 JobScheduler（API 21），再到 Jetpack 的 WorkManager。演进的核心驱动力始终是省电。

### 为什么不推荐自己管理后台任务

手动管理后台任务的短板，在于它看不到系统当前的省电策略。App 用 AlarmManager 设了一个 5 分钟的定时器，系统很难把它和其他 App 的定时任务统一安排，结果是设备隔几分钟就被唤醒一次。单看一个 App，代价不大；多个 App 叠加后，设备就很难稳定进入休眠。

Doze 模式就是拿来处理这种叠加效应的。设备静止、屏幕关闭一段时间后，系统会把非豁免的后台活动延后到维护窗口集中执行。App 自己设的闹钟、注册的 JobScheduler 任务和后台网络请求，都会一起受这个调度策略约束。

### WorkManager：后台任务的首选方案

WorkManager 是 Google 推荐的后台任务调度 API，它封装了 JobScheduler（API 23+）和 AlarmManager + BroadcastReceiver（旧版本）的差异，提供统一的接口。

WorkManager 的省电优势在于**约束条件（Constraints）**和**任务合并**。

```kotlin
// 使用约束条件：仅在充电 + WiFi 时执行
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

**最小间隔 15 分钟**。周期性任务（PeriodicWorkRequest）的最小间隔是 15 分钟，这不是随便设的，而是系统 JobScheduler 的最小调度窗口。不要试图绕过这个限制。

**避免使用 Expedited Work**。`setExpedited()` 会让任务绕过部分系统优化立即执行，只有处理用户可见的高优先级 FCM 消息等场景才应该使用。滥用 Expedited Work 的功耗影响等同于手动 WakeLock。

**合理安排任务顺序**。多个有依赖关系的任务可以用 WorkManager 的 `then()` 接在一起，系统更容易把它们放进同一批执行窗口，减少额外唤醒。

### JobScheduler 的定位

如果项目没有使用 Jetpack，或者需要直接与系统服务交互，JobScheduler 仍然是有效的选择。它的核心机制与 WorkManager 底层相同：通过 `JobInfo.Builder` 设置约束条件，系统在合适的时机调度执行。

WorkManager 和 JobScheduler 的选择不需要纠结：新项目用 WorkManager，已有项目迁移到 WorkManager。不需要两者混用。

### 在 Battery Historian 中的表现

后台任务调度的效率可以通过 Battery Historian 的 "JobScheduler" 行观察。如果看到某个 App 的 Job 条频繁出现且间隔很短（比如每几分钟一次），说明任务调度过于激进。正常情况下，后台任务的调度间隔应该与设置的约束条件匹配——只有在满足约束时才执行。

[待补充: Battery Historian 截图展示 JobScheduler 和 WorkManager 的正常/异常调度模式]

## 位置服务功耗优化

位置服务是 Android 中功耗最高的硬件子系统之一。GPS 模块启动后持续搜索卫星信号，功耗可达 50-100mA；即使只用网络定位（WiFi + 基站），频繁的扫描也会拉高功耗。

[已验证: 官方文档, developer.android.com/training/location]

### Fused Location Provider 与精度选择

Google Play Services 提供的 Fused Location Provider（FLP）是现代 Android 定位的推荐方案。它会智能地融合 GPS、WiFi、基站、传感器数据，在满足精度需求的前提下选择功耗最低的定位源。

FLP 提供四种精度级别，对应不同的功耗：

**PRIORITY_BALANCED_POWER_ACCURACY** 是大多数 App 应该使用的默认选择。它通常不启用 GPS，依靠 WiFi 和基站信息提供街区级（约 100 米）精度，功耗显著低于 GPS。社交类 App 的"附近的人"、天气 App 的城市定位、本地搜索，这些场景用这个精度就够了。

**PRIORITY_HIGH_ACCURACY** 会启用全部定位源包括 GPS，功耗最高。只有在导航、跑步追踪等确实需要精确位置的场景才使用，而且应该只在 App 处于前台时启用。

**PRIORITY_LOW_POWER** 仅使用基站，精度为城市级（约 10 公里），功耗最低。

**PRIORITY_PASSIVE** 完全不主动请求定位，只被动接收其他 App 触发的位置更新。功耗几乎为零。

[已验证: 官方文档, developer.android.com/training/location/receive-location-updates]

```kotlin
// 精度与功耗的平衡：只在需要时请求高精度
val locationRequest = LocationRequest.Builder(
    Priority.PRIORITY_BALANCED_POWER_ACCURACY,
    60_000L  // 更新间隔 60 秒
).apply {
    setMaxUpdateDelayMillis(300_000L)  // 批量交付：最长延迟 5 分钟
    setDurationMillis(TimeUnit.HOURS.toMillis(1))  // 自动超时 1 小时
}.build()
```

这段代码有两个省电要点。第一，`setMaxUpdateDelayMillis()` 启用了批量交付模式：FLP 内部按 60 秒间隔计算位置，但不是每次都唤醒 App，而是积累最多 5 分钟后一次性交付一批位置更新。这用延迟换取了功耗——App 唤醒次数从每分钟一次降低到每 5 分钟一次。

第二，`setDurationMillis()` 设置了自动超时。即使忘记移除位置请求，1 小时后 FLP 会自动停止更新，防止因代码缺陷导致无限定位。

### Geofencing 的省电优势

Geofencing（地理围栏）是位置服务中最省电的模式之一。它不要求 App 持续运行，而是在设备进入或离开指定区域时由系统通知 App。从 Android 8.0（API 26）开始，Geofencing 的响应性从数十秒放宽到约两分钟，功耗降低了约 10 倍。

```kotlin
// Geofencing：系统级省电
val geofence = Geofence.Builder()
    .setRequestId("store-001")
    .setCircularRegion(latitude, longitude, 200f)  // 200 米半径
    .setExpirationDuration(TimeUnit.HOURS.toMillis(2))  // 2 小时后自动失效
    .setTransitionTypes(Geofence.GEOFENCE_TRANSITION_ENTER)
    .build()
```

Geofencing 省电的原理在于，系统在硬件层面管理围栏检测，不需要持续唤醒 App。只有当设备确实进入围栏范围时，系统才会通过 PendingIntent 唤醒 App。这种"只在事件发生时才工作"的模式，比"每隔 N 秒检查一次位置"省电几个数量级。

[已验证: 官方文档, developer.android.com/training/location/geofencing]

### 在 Perfetto 中的表现

位置服务的功耗问题可以在 Perfetto 中通过以下 track 观察：

- **Location Manager** track：显示位置请求的注册和注销。如果看到一个 App 持续有位置请求而没有对应的注销操作，很可能是生命周期管理有问题。
- **GPS** track：GPS 芯片的活动状态。持续活跃的 GPS track 意味着高功耗。
- **Network** track：如果 App 使用网络定位，频繁的网络扫描也会反映在网络 track 中。

[待补充: Perfetto 截图展示正常和异常的位置服务使用模式]

## 网络请求功耗优化

网络模块是仅次于屏幕和 CPU 的第三大功耗来源。移动数据（Cellular）的功耗远高于 WiFi，而网络模块从休眠到活跃的状态切换本身就消耗能量——即使只传几个字节，射频模块也需要几百毫秒的启动时间。

### 批量请求与减少轮询

网络请求功耗优化的核心原则是**减少射频模块的唤醒次数**。

假设一个 App 每 5 秒向服务器轮询一次数据，每次传输 100 字节。从数据量看，一小时只有 72KB，微不足道。但从射频模块的角度看，每小时 720 次唤醒——每次唤醒射频模块都要从休眠状态切换到活跃状态，这个过程消耗的能量可能比传输 100 字节本身还多。

解决方案是**批量请求**：将多次小请求合并为一次大请求。如果业务允许，将轮询间隔从 5 秒延长到 30 秒或更长；更好的做法是使用 Push 模式替代 Pull 模式。

### Push 替代 Pull

Firebase Cloud Messaging（FCM）是 Android 推荐的消息推送方案。它的省电优势在于，多个 App 可以复用同一条 TCP 长连接，系统不必为每个 App 各养一条常驻连接。相反，如果每个 App 都自己维护长连接轮询，随着 App 数量增加，常驻网络连接也会跟着变多。

FCM 分为两种优先级：

**高优先级消息**（high priority）会立即唤醒设备，适用于需要立即显示通知的场景。但 Google 对高优先级消息有配额限制——如果 App 频繁发送高优先级消息但用户没有与之交互，系统会将后续消息降级为普通优先级。这个机制是为了防止 App 借"通知"之名行"保活"之实。

**普通优先级消息**（normal priority）会在设备下次活跃时才送达，不会额外唤醒设备。用于数据同步、内容更新等不需要立即处理的场景。

[已验证: 官方文档, firebase.google.com/docs/cloud-messaging]

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

这里 `UNMETERED` 指定只在 WiFi 下执行，比 `CONNECTED`（任何网络）更省电。同时 `setBackoffCriteria()` 设置了指数退避。如果网络请求失败，任务不会立即重试，而是按指数增长的间隔重试，避免在网络不稳定时反复唤醒射频模块。

[已验证: 官方文档, developer.android.com/reference/androidx/work/NetworkType]

## Alarm 使用规范

AlarmManager 是 Android 最早的定时机制，也是被滥用最多的 API 之一。在 WorkManager 和 JobScheduler 已经成熟的今天，AlarmManager 的合理使用场景已经非常有限。

### 精确闹钟与功耗

Android 的闹钟分为两种：精确闹钟（exact alarm）和不精确闹钟（inexact alarm）。

精确闹钟（`setExact()`、`setExactAndAllowWhileIdle()`）会在指定时间精确触发，系统无法合并或延迟。如果 10 个 App 各设了一个精确闹钟，设备就可能被唤醒 10 次。

不精确闹钟（`set()`、`setWindow()`、`setAndAllowWhileIdle()`）由系统在合适的时间窗口内调度，可以与其他闹钟合并执行，功耗更低。

[已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager]

### Android 14 的 SCHEDULE_EXACT_ALARM 权限

从 Android 14 开始，非闹钟/日历类 App 默认不能使用精确闹钟。App 需要声明 `SCHEDULE_EXACT_ALARM` 权限，而且用户可以在设置中关闭这个权限。

这个变化背后的逻辑是：精确闹钟的功耗影响太大，应该由用户决定哪些 App 有权使用。如果 App 只是需要定时执行后台任务，应该用 WorkManager 而不是 AlarmManager。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14#schedule-exact-alarms]

### setAndAllowWhileIdle 的使用限制

`setAndAllowWhileIdle()` 和 `setExactAndAllowWhileIdle()` 是唯二能在 Doze 模式下触发的闹钟 API。但它们有限制：

每个 App 在 Doze 模式下，使用这些 API 触发的闹钟大约每 9 分钟只能触发一次。如果 App 设置了多个 AllowWhileIdle 闹钟，系统会合并执行。

这个限制告诉我们：**不要把 AllowWhileIdle 闹钟当作保活手段**。它的设计初衷是让闹钟类 App 在 Doze 下也能正常响铃，而不是让所有 App 都能在 Doze 下持续运行。

### 在 Battery Historian 中的表现

AlarmManager 的使用情况在 Battery Historian 的 "Alarm" 行中显示。如果看到某个 App 频繁触发闹钟（特别是精确闹钟），说明需要迁移到 WorkManager 或使用不精确闹钟。

[待补充: Battery Historian 截图展示精确闹钟与不精确闹钟的调度差异]

## 前台服务的功耗考量与 Android 14+ 的限制

前面讨论的后台任务调度和 Alarm 优化，核心思路都是"尽量让系统决定什么时候执行"。但有些场景 App 确实需要持续在后台运行——音乐播放、导航、位置追踪。前台服务就是为这些场景设计的，它通过通知栏告知用户"这个 App 正在后台工作"，换取系统不会因为后台限制而杀死它。问题在于，FGS 一旦启动就不受 Doze 限制，如果滥用，功耗影响比 WakeLock 更严重——WakeLock 至少还会在 Doze 中被延迟，FGS 则完全不受约束。

Android 14（API 34）对 FGS 的治理经历了重大变革，系统从"信任开发者声明"转向"强制类型分类 + 运行时权限验证"。

### FGS 类型与权限

Android 14 要求所有前台服务必须声明一个具体类型（如 `location`、`camera`、`mediaPlayback`），并且在 Manifest 中声明对应的权限（如 `FOREGROUND_SERVICE_LOCATION`）。如果类型和权限不匹配，系统会抛出 `MissingForegroundServiceTypeException`。

新增的 FGS 类型中，有两个值得特别关注：

**shortService**：专为短时间（约 3 分钟）的关键工作设计。如果超时未完成，系统会停止服务。这个类型适合一次性文件加密、紧急数据保存等场景——它的功耗上限是明确的，不会无限持有。

**dataSync**：已标记为未来弃用（deprecated），Google 建议迁移到 WorkManager 或 DownloadManager。对于系统开发者来说，如果一个 App 声明了 dataSync 类型的 FGS 并长时间运行，在功耗分析中应该标记为可优化项。

[已验证: 官方文档, developer.android.com/about/versions/14/changes/fgs-types]

### Android 15 的进一步限制

Android 15（API 35）对 `dataSync` 和新增的 `mediaProcessing` 类型引入了 6 小时的时间上限。超过限制后服务会被系统降级为普通服务并停止。这个限制是跨实例共享的——同一 App 的所有 dataSync 类型的 FGS 共享一个 6 小时计时器。

对功耗分析来说，FGS 已经不再是"一旦启动就一直运行"的后台常驻方案。系统在强制它回到短时间工作的定位上。

[已验证: 官方文档, developer.android.com/about/versions/15/changes]

### FGS 的功耗分析方法

在分析 App 的 FGS 功耗时，我们关注两个层面。

第一，**FGS 是否真的需要**。很多 App 启动 FGS 只是为了避免后台执行限制，但实际工作用 WorkManager 就能完成。在 Perfetto 中，可以通过 `Svc` track 观察前台服务的生命周期。如果 FGS 长时间运行但没有对应的 CPU 活动，说明 FGS 可能只是为了保活。

第二，**FGS 是否在正确的场景启动**。Android 14+ 对 FGS 的启动时机有限制，比如不能从 `BOOT_COMPLETED` 广播中启动 `camera`、`mediaPlayback` 等类型的 FGS。

[待补充: Perfetto 截图展示 FGS 的 CPU 活动与持续时间]

## Camera/Audio 等硬件资源的功耗优化

除了 CPU、网络、GPS 这些"大头"，Camera 和 Audio 也是不少 App 的功耗盲区。视频通话类 App 的 Camera 传感器持续运行、音乐类 App 的 Audio 后台播放，都属于"用户能感知到但开发者很少主动优化"的功耗来源。它们的优化空间不如 WakeLock 或网络请求那么大，但在特定场景下（比如直播、视频会议），Camera 的功耗可以占到整机的 30% 以上。

### Camera

Camera 传感器启动后的功耗在 200-500mA 量级（取决于分辨率和帧率），是所有传感器中最高的之一。优化方向主要有：

**降低预览帧率**。如果 App 只需要拍照，不需要持续的 60fps 预览，将预览帧率降到 30fps 甚至 15fps 可以显著降低 Camera 的功耗。在 Camera2 API 中，可以通过 `setRepeatingRequest()` 配合 `CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE` 设置目标帧率范围。

**及时释放 Camera 资源**。这是最基本的但也是最常被忽视的。Camera 在不使用时必须调用 `cameraManager.closeCamera()` 完整释放。在 Perfetto 中，可以通过 Camera HAL 的 track 观察 Camera 的活跃时间——如果 App 退到后台后 Camera 仍然活跃，就是资源泄漏。

[待验证: Camera2 FPS 设置对功耗的量化影响]

### Audio

Audio 的功耗优化主要关注两个方面：

**避免使用不必要的高采样率**。44.1kHz 对于大多数应用已经足够，96kHz 虽然在专业音频场景有价值，但在普通 App 中只是浪费处理能力。

**后台播放需要 FGS**。从 Android 12 开始，后台播放音乐必须使用 `mediaPlayback` 类型的 FGS。这是合理的要求——后台音频确实需要持续运行，但系统需要通过通知告知用户。

## 与其他章节的关系

App 耗电优化不是孤立的话题，它与全书的多个章节形成上下游关系。

从系统层面看，§11.1 拆解了各硬件模块的功耗参数，是我们判断"优化哪个模块收益最大"的依据。§5.4 DVFS 机制在 CPU 层面动态调节频率和电压，App 减少不必要的 CPU 使用时间，就是在配合 DVFS 让设备更快进入低频低功耗状态。§5.6 Doze 和 App Standby 是系统对后台行为的全局管控，理解了这些机制的设计意图，才能写出不会与系统优化"打架"的 App。

从关联问题看，§9.2 ANR 分析中经常遇到一个矛盾：一些 App 为了避免主线程阻塞导致 ANR，把本该在主线程的工作推到后台 Service 中持续执行，结果 ANR 是少了，功耗却上去了。§5.10 对 JobScheduler 和 WorkManager 的底层调度机制做了更深入的分析，可以帮助理解 WorkManager 的约束条件在 JobScheduler 层面是怎么实现的。§11.5 对 WakeLock 的系统级机制（PowerManagerService 的 wakelocks 管理）有更详细的源码分析。

## 常见问题与误区

### 误区一："WakeLock 只要不一直持有就没事"

实际情况是，频繁地获取和释放 WakeLock（比如每秒 acquire/release 一次）同样会造成功耗问题。每次 acquire 都会通知 PowerManagerService 更新系统的 wakefulness 状态，涉及 Binder 调用和锁竞争。如果需要频繁的短时间唤醒，应该用一次较长时间的 acquire 覆盖整个工作周期，而不是反复 acquire/release。

### 误区二："WorkManager 的约束条件设得越多越好"

约束条件过多会导致任务长期无法执行，积累后可能在工作条件满足时集中爆发，造成瞬时高功耗。合理的做法是根据业务需求设置核心约束——比如大文件上传确实需要 WiFi 和充电，但普通数据同步只需要 WiFi 即可。

### 误区三："GPS 没开就不会耗电"

即使 App 请求了 PRIORITY_HIGH_ACCURACY，而用户在系统设置中关闭了 GPS，FLP 仍然会尝试通过 WiFi 和基站提供定位，但精度会低于预期。App 不应该因为精度达不到要求就持续请求高精度——这会导致 WiFi 和基站扫描频率升高。应该根据实际场景选择合适的精度级别。

### 误区四："前台服务有通知就不会被系统杀"

Android 14 的 FGS Task Manager 让用户可以直接看到并停止前台服务。如果用户发现某个 FGS 持续运行且耗电高，会主动停止它。而且 Android 15 对 dataSync 类型引入了 6 小时上限，系统会强制回收。依赖 FGS 保活的时代已经过去了。

### 误区五："用了 WorkManager 就不用关心功耗了"

WorkManager 确实比手动调度更省电，但它不是银弹。如果 App 注册了大量 PeriodicWorkRequest 且间隔很短（比如多个 15 分钟间隔的周期任务），系统仍然需要频繁唤醒。最佳实践是将多个周期性任务合并为一个，或者利用任务的输出作为下一个任务的触发条件，减少总调度次数。

## 参考资料

- [Android 官方：优化电池寿命](https://developer.android.com/topic/performance/power)
- [Android 官方：Doze 和 App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Android 官方：后台执行指南](https://developer.android.com/guide/background)
- [Android 官方：WorkManager 指南](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Android 官方：位置服务功耗优化](https://developer.android.com/training/location)
- [Android 官方：前台服务类型（Android 14）](https://developer.android.com/about/versions/14/changes/fgs-types)
- [AOSP PowerManager.java](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/java/android/os/PowerManager.java)
- [AOSP PowerManagerService.java](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java)
- [Android 官方：位置服务 Geofencing](https://developer.android.com/training/location/geofencing)
- [Android 官方：Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [Android 官方：Battery Historian 使用指南](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [来源: Obsidian Cubox - 借助 Android Studio 中的功耗性能分析器进行 A-B 测试]
- [来源: Obsidian Cubox - 谈功耗是什么]
- [来源: Obsidian Cubox - SoC 低功耗问题定位及优化的 10 个思路]
- [来源: Obsidian Cubox - BatteryHistorian Android 手机耗电分析神器]
- [来源: Obsidian Cubox - 抖音功耗优化实践]
