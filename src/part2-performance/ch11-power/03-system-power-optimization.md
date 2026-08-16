---
title: 系统级功耗优化
chapter: '11.3'
status: finalized
section: '11.3'
applicable_versions: Android 6.0 (API 23) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1, android17-6.18-2026-06_r6, Android Developers Doze / App Standby / Battery Saver / background limits / Android 17 JobScheduler and AlarmManager docs
confidence: medium-high
sources:
- type: official
  path: https://developer.android.com/training/monitoring-device-state/doze-standby
- type: official
  path: https://developer.android.com/topic/performance/appstandby
- type: official
  path: https://developer.android.com/topic/performance/power/power-details
- type: official
  path: https://developer.android.com/topic/performance/power/test-power
- type: official
  path: https://developer.android.com/guide/components/activities/secure-bal
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/background
- type: official
  path: https://source.android.com/docs/core/power/mgmt
- type: official
  path: https://source.android.com/docs/core/power/platform_mgmt
- type: official
  path: https://source.android.com/docs/core/power/trackers
- type: official
  path: https://source.android.com/docs/core/power/routine-battery-saver
- type: official
  path: https://developer.android.com/reference/android/os/PowerManager
- type: official
  path: https://developer.android.com/reference/android/app/job/JobScheduler
- type: official
  path: https://developer.android.com/reference/android/app/AlarmManager
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java
- type: aosp
  path: frameworks/base/services/usage/java/com/android/server/usage/UsageStatsService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/LowPowerStandbyController.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverController.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverPolicy.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityOptions.java
- type: aosp
  path: frameworks/base/core/java/android/os/PowerManager.java
- type: kernel
  path: kernel/power/suspend.c
- type: kernel
  path: kernel/sched/idle.c
- type: kernel
  path: drivers/base/power/wakeup.c
- type: community
  path: https://dontkillmyapp.com/
- type: official
  path: https://developer.android.com/topic/performance/app-hibernation
- type: official
  path: https://developer.android.com/about/versions/15/features#app-archiving
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller#requestArchive(java.lang.String,android.content.IntentSender)
- type: official
  path: https://developer.android.com/about/versions/oreo/background
- type: official
  path: https://developer.android.com/topic/performance/power
- type: official
  path: https://developer.android.com/about/versions
tags:
- doze
- standby
- battery-saver
- background-restriction
- oem-power
- adaptive-battery
- foreground-service
related_chapters:
- '5.6'
- '11.1'
- '11.2'
- '1.3'
- '4.4'
task6_state: reviewed
pipeline_stage: ready-to-publish
task9_state: reviewed
task2b_state: fixed
---


# 11.3 系统级功耗优化

## 系统为什么要限制后台工作

单个 App 只知道自己的任务是否紧急，系统还要综合考虑电量、充电状态、屏幕、移动状态、温度、内存压力、网络和其他 App。Android 因此把后台资源分配分为多组可叠加的策略：

| 决策维度 | 主要机制 | 影响对象 |
| --- | --- | --- |
| 设备是否空闲 | Doze、Light Doze、Low Power Standby | 网络、WakeLock、Job、Alarm、Sync |
| 用户多久使用一次 App | App Standby Buckets、Restricted bucket | Job 时长、Alarm 频率、后台网络 |
| 用户是否主动限制 App | Battery settings、background restriction | Job、Alarm、网络与后台执行 |
| 全局是否节电 | Battery Saver、OEM low-power policy | 位置、后台任务、显示、性能与厂商功能 |
| App 当前是否可见 | 进程重要性、FGS、BAL、while-in-use 权限 | 资源配额、界面拉起、位置与敏感资源 |
| ROM 的附加策略 | OEM 冻结、自启动和应用启动管理 | 进程调度、广播、推送与后台存活 |

下文沿用 Android 文档中的常用名称：FGS 是 Foreground Service（前台服务），BAL 是 Background Activity Launch（后台 Activity 启动），quota 表示系统分配的资源配额，OEM 指设备厂商，ROM 指设备搭载的系统。它们分别约束不同环节，不能用其中一个机制的状态推断其他机制。

同一个 Job 可能同时等待充电约束、Doze 维护窗口、standby quota（待机配额）和 OEM 调度条件。定位“为什么没运行”时，需要逐项核对证据，不能只看 WorkManager 状态。

## Doze：按设备状态集中后台活动

Android 6.0（API 23）引入 Doze（设备空闲省电模式）。设备长时间未使用时，系统暂停普通后台网络，忽略 App WakeLock，并延后 Job、Sync 与普通 Alarm；设备会周期性进入维护窗口，批量处理积压工作。

### Light Doze 与 Deep Doze

Android 7.0（API 24）加入限制较轻的 Light Doze。Light Doze 与 Deep Doze 是两条独立的状态机，触发条件和限制强度不同：

| 模式 | 进入条件 | 主要目的 |
| --- | --- | --- |
| Light Doze（轻度 Doze） | 屏幕关闭、未充电；不要求设备静止 | 较早限制后台网络和调度，移动中的设备也能节电 |
| Deep Doze（深度 Doze） | 屏幕关闭、未充电、持续静止；完整实现依赖 significant motion detector（显著运动检测器） | 延长 suspend（系统挂起）驻留时间，限制更严格 |

设备移动、点亮屏幕或接入充电器会让 Deep Doze 退出。Light Doze 与 Deep Doze 在 `DeviceIdleController` 中有各自状态，`dumpsys deviceidle` 输出的 `mLightState`、`mState` 也要分开读。

### 维护窗口不是定时器

维护窗口会短暂恢复网络，并分发积压的 Sync、Job 和 Alarm。设备持续空闲时，维护窗口之间的休眠间隔会逐步增长。具体时长由平台版本、资源 overlay（资源覆盖配置）、DeviceConfig（系统动态配置）与设备实现决定，App 不能把某款手机的窗口间隔当作调度 SLA（服务时限承诺）。

窗口到来只表示限制暂时放宽，仍不保证某个任务马上执行。Job 还要满足自身约束、standby bucket（待机分组）、quota 和并发调度条件。

### Doze 中哪些能力会被限制

- 普通网络访问暂停。
- App 持有的 WakeLock 被忽略。
- `set()`、`setWindow()`、`setExact()` 等普通 Alarm 延后到维护窗口。
- JobScheduler、WorkManager 和 SyncAdapter 延后。
- 后台 Wi‑Fi 扫描停止。
- FGS 可以提高进程重要性，但不能获得设备级 Doze 豁免。

高优先级 FCM 只适合时间敏感、会产生用户可见通知的消息。系统会给接收方短暂使用网络和 partial WakeLock（只保持 CPU 运行的唤醒锁）的机会，处理完成后设备继续空闲。普通数据刷新使用 normal priority（普通优先级），并接受维护窗口延迟。

`setAndAllowWhileIdle()`、`setExactAndAllowWhileIdle()` 和 `setAlarmClock()` 能在空闲期间交付。前两者受每个 App 约九分钟一次的频率边界，系统还可以延长间隔。它们适合用户感知的关键事件，不能用于高频轮询。

### Android 17 的 listener 型 allow-while-idle Alarm

API 37 新增 `setExactAndAllowWhileIdle(int, long, String, Executor, OnAlarmListener)`。这是 listener（监听器）形式的 allow-while-idle Alarm，可在设备空闲时交付。回调直接在指定 `Executor` 上执行，仍有组件存活的 App 因而无需为等待精确回调而持续持有 WakeLock。

`OnAlarmListener` 形式的 Alarm 依赖调用进程继续有组件运行。进程没有 Activity、Service 或 ContentProvider 时，系统可以取消它。需要在进程退出后仍能收到事件，应使用 `PendingIntent` 形式并遵守精确闹钟权限。新 API 没有改变 allow-while-idle 只能低频使用的原则。

### Doze 豁免是部分豁免

用户可以在系统设置中把 App 加入电池优化豁免列表。豁免 App 在 Doze 中可以访问网络并持有 `PARTIAL_WAKE_LOCK`，普通 Alarm 等限制仍可能存在。App 可用 `PowerManager.isIgnoringBatteryOptimizations()` 检查状态。

`ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` 只适用于官方列出的少数核心场景，Google Play 也限制直接请求豁免。一般应用应打开电池优化设置页，由用户决定；不要在首次启动时把“无限制”当作必选权限。

### 从 Framework 到 kernel suspend

`DeviceIdleController` 决定何时限制 App 资源，`PowerManagerService` 与 SystemSuspend 协调系统休眠。内核 `android17-6.18-2026-06_r6` 的 `kernel/power/suspend.c` 执行 suspend 主流程，`drivers/base/power/wakeup.c` 管理 wakeup source（唤醒源），`kernel/sched/idle.c` 处理 CPU idle（CPU 空闲状态）。

Doze 状态不能证明设备已经进入 suspend。驱动 wakeup source、内核 timer（定时器）、IRQ（中断请求）或 `system_server` 中的工作仍可能阻止休眠。Framework 层的状态只能证明策略已进入 idle（空闲）阶段；还要结合 `power/suspend_resume`、wakeup source 与 CPU idle 证据确认硬件状态。

### 强制进入 Doze 的测试方法

下面的命令用于专用测试设备，主动驱动 DeviceIdle 状态并保存快照。

```bash
adb shell dumpsys battery unplug
adb shell dumpsys deviceidle force-idle
adb shell dumpsys deviceidle
adb shell dumpsys jobscheduler com.example.app
adb shell dumpsys alarm

# 测试结束后恢复设备状态
adb shell dumpsys deviceidle unforce
adb shell dumpsys battery reset
```

`force-idle` 会绕过正常等待时间，适合验证功能恢复和任务延迟，不适合测量自然进入 Doze 的时延。性能与续航测试还要覆盖屏幕关闭、设备静止的自然路径。

## App Standby Buckets：按使用关系分配配额

App Standby（应用待机）不要求整台设备空闲。Android 9（API 28）开始，系统根据使用模式把 App 动态放入不同的 standby bucket：Active（活跃）、Working set（常用）、Frequent（频繁使用）、Rare（很少使用）或 Restricted（受限）；安装后从未运行的 App 还有 `Never` 状态。

### 当前官方指导额度

下表是 Android 官方在 2026 年提供的近似资源边界。这些数字不承诺任务一定执行；设备状态、进程可见性、充电、用户限制、bucket 变化和未来系统更新都可能改变结果。

| Bucket（待机分组） | Regular jobs（普通任务） | Expedited jobs（加急任务） | Alarms（闹钟） | 后台网络 |
| --- | --- | --- | --- | --- |
| Active | Android 16+：滚动 60 分钟内最多约 20 分钟 | 滚动 24 小时内最多约 30 分钟 | 无 bucket 频率限制 | 不限制 |
| Working set | 滚动 4 小时内最多约 10 分钟 | 滚动 24 小时内最多约 15 分钟 | 每小时最多约 10 次 | 不限制 |
| Frequent | 滚动 12 小时内最多约 10 分钟 | 滚动 24 小时内最多约 10 分钟 | 每小时最多约 2 次 | 不限制 |
| Rare | 滚动 24 小时内最多约 10 分钟 | 滚动 24 小时内最多约 10 分钟 | 每小时最多约 1 次 | 禁用 |
| Restricted | 每天一次、批量会话最多约 10 分钟 | 滚动 24 小时内最多约 5 分钟 | 每天一次 exact 或 inexact alarm（精确或非精确闹钟） | 禁用 |

充电时多数 bucket 限制会放宽，Restricted 仍有专门规则。可见或前台进程通常不受 bucket 执行限制；运行 FGS 的进程仍要遵守 bucket 对 Job 和 Alarm 的限制。Android 16 之前，Active bucket 与 FGS 并发 Job 的 runtime quota（运行时长配额）更宽松，迁移测试要注意版本差异。

`QuotaController` 负责 JobScheduler 的配额判断，`AppStandbyController` 评估 bucket，`JobSchedulerService` 汇总约束并分发任务。表里的数字来自当前默认策略说明，不应硬编码进业务重试逻辑。

### Restricted bucket 的触发与例外

Android 12/12L 的无互动阈值为 45 天；Android 13+ 缩短为 8 天，关机时间不计入。Android 13+ 还可能因为 24 小时内广播或 binding（服务绑定）次数过多，把 App 放入 Restricted。设备厂商能调整非 Active App 的分类标准。

Companion Device（配套设备应用）、device/profile owner（设备或工作资料所有者）、persistent（常驻系统应用）、VPN、默认拨号、活动 widget（桌面小组件），以及具备部分官方列出权限或被用户设为“无限制”的 App，可能获得 Restricted 豁免。豁免条件应以运行设备和当前官方文档为准。

### Adaptive Battery 的可确认边界

Adaptive Battery（自适应电量管理）的公开契约只保证 bucket 会动态变化。设备可能预装使用机器学习预测近期使用情况的系统 App，也可以在没有该组件时按最近使用时间排序；厂商还能实现自己的分类标准。

AOSP 和公开文档没有规定统一的模型框架、网络结构、特征集合或训练方式。App 可以依赖 `UsageStatsManager.getAppStandbyBucket()` 的返回结果；预测器内部结构不属于公开契约。

### 检查 bucket、quota 与 pending reason

pending reason（待处理原因）指 Job 仍在等待的原因。下面的命令把测试 App 设为不同 bucket，并对照 UsageStats 与 JobScheduler。

```bash
adb shell dumpsys battery unplug
adb shell am set-standby-bucket com.example.app rare
adb shell am get-standby-bucket com.example.app
adb shell dumpsys usagestats appstandby
adb shell dumpsys jobscheduler com.example.app

# 测试结束后恢复电池模拟状态
adb shell dumpsys battery reset
```

手工分桶只覆盖 bucket 维度。测试报告还要记录屏幕、充电、Doze、Battery Saver、网络和 App 进程状态，否则无法解释同一 bucket 下的不同结果。

API 34 提供单个 pending reason，API 36 增加 `getPendingJobReasons()` 与 `getPendingJobReasonsHistory()`。API 37 的 `JobScheduler.getPendingJobReasonStats(jobId)` 返回 `PENDING_JOB_REASON_*` 到累计 `Duration`（持续时间）的映射；多个原因可同时存在，所以各项时长之和可能大于任务总等待时间。统计不会跨重启保留，任务成功或取消后也会清除。

诊断时应区分：

- `PENDING_JOB_REASON_APP_STANDBY`：bucket 阻止执行。
- `PENDING_JOB_REASON_QUOTA`：当前 Job quota 已用完。
- `PENDING_JOB_REASON_DEVICE_STATE`：Doze、Battery Saver、内存或温度等设备状态。
- `PENDING_JOB_REASON_JOB_SCHEDULER_OPTIMIZATION`：JobScheduler 选择更合适的时间。
- 显式 constraint reason（约束原因）：充电、网络、存储、minimum latency（最短等待时间）等业务约束未满足。

## 系统级后台限制

Doze 与 bucket 主要决定任务何时运行、可以运行多久。后台执行、后台界面和 while-in-use（仅使用期间授权）权限规则还会判断当前操作能否开始。

### Background Activity Launch

Android 10（API 29）开始限制 Background Activity Launch（后台 Activity 启动，BAL）。通知、full-screen intent（全屏通知意图）、系统角色和用户交互各有专门规则，FGS 通知本身不提供通用 BAL 豁免。

PendingIntent 与 IntentSender 的授权逐步改为 opt-in（显式选择启用）：

| 版本 | 变化 |
| --- | --- |
| target 34+ | PendingIntent 发送方不再默认授予自己的 BAL 能力；通过 `setPendingIntentBackgroundActivityStartMode()` 选择模式 |
| target 35+ | PendingIntent 创建方不再默认把自己的 BAL 能力交给接收方；通过 `setPendingIntentCreatorBackgroundActivityStartMode()` 授权 |
| API 36+ | 发送方优先使用 `MODE_BACKGROUND_ACTIVITY_START_ALLOW_IF_VISIBLE`；只有确有后台拉起需求时评估更宽模式 |
| target 37+ | `IntentSender.sendIntent()` 也要求发送方按 BAL 规则显式 opt-in |

授权链还必须包含一个原本就有后台启动资格的参与者。设置 mode（授权模式）不会额外产生启动资格。可见 App 绑定服务并希望被绑定方拉起 Activity 时，Android 14+ 还要核对 `BIND_ALLOW_ACTIVITY_STARTS`。

### 后台位置

- Android 8.0+：后台 App 通常每小时只能收到少量位置更新，此限制与 targetSdk 无关。
- Android 10+：持续后台定位需要 `ACCESS_BACKGROUND_LOCATION`，仅有 `coarse`/`fine`（粗略/精确位置）权限只覆盖 while-in-use。
- Android 11+：从可见界面启动的 `location` FGS 属于 foreground location（前台定位），界面退到后台后仍可继续；App 已在后台才启动 FGS 时，没有 `ACCESS_BACKGROUND_LOCATION` 就不能获得位置。
- Android 14、target 34+：创建 `location` FGS 时立即校验类型权限与 while-in-use 条件。App 已在后台且不满足例外时，可能抛 `SecurityException` 或 FGS 启动异常。

地理围栏和 batched location（批量定位）可以减少 App 主动轮询，但不会绕过权限和系统交付边界。

### 后台 Service 与 FGS

Android 8.0+ 对后台 Service 的创建和存活施加限制。可延迟任务交给 JobScheduler 或 WorkManager；用户知情的持续任务使用匹配类型的 FGS，并接受后台启动限制、类型权限和时长规则。

FGS 不能提升 bucket 等级、绕过 Doze、跳过 Job quota 或获得 while-in-use 权限。Android 16 起，与 FGS 并发的 Job 明确受 runtime quota 约束。

## Hibernation 与 Archiving

Hibernation（应用休眠）与 Archiving（应用归档）都会让长期未用的 App 停止后台活动，但两者对存储占用和恢复流程的影响不同：

| 机制 | 平台起点 | 系统动作 | 恢复时要处理 |
| --- | --- | --- | --- |
| App hibernation | Android 11 权限自动重置；Android 12 扩展完整休眠 | 重置运行时权限、停止后台 Job/Alarm/Push、清理 cache（缓存） | 用户重新交互后退出休眠；权限不会自动恢复，旧 Job/Alarm 也不会自动重新调度 |
| App archiving | Android 15 提供 OS 级 archive/unarchive（归档/恢复） | 安装器移除 APK 与 cache，保留用户数据；Launcher（桌面启动器）可展示归档状态 | 用户点击后由负责的 installer（安装器）恢复包，再按安装/恢复路径初始化 |

Android 15 提供 `PackageInstaller.requestArchive()`，调用者需要 `REQUEST_DELETE_PACKAGES`。是否自动选择长期未用 App、由哪个商店恢复、图标如何显示，取决于安装器和设备体验。不能把 Google Play 的 auto-archive（自动归档）策略写成所有 Android 15 设备的统一行为。

Hibernation 恢复后，App 应检查权限并重建必要任务。WorkManager 能帮助恢复一部分持久工作，业务仍要验证依赖的 Alarm、通知和服务是否重新注册。

## Battery Saver 与 Low Power Standby

### Battery Saver 是全局策略输入

Battery Saver 是系统级省电模式。`PowerManagerService` 发布 low-power（低功耗）状态，`BatterySaverController` 与 `BatterySaverPolicy` 计算各服务的策略。设备可以调整具体限制，所以 App 应读取公开状态并降低自身工作量：

- `PowerManager.isPowerSaveMode()` 判断 Battery Saver 是否开启。
- `ACTION_POWER_SAVE_MODE_CHANGED` 监听状态变化。
- `getLocationPowerSaveMode()` 返回当前定位节电策略，可能是屏幕关闭后停用 GNSS、停用全部 provider（位置提供方）、只给前台 App、降低请求频率或不改变。

Battery Saver 不会简单地把所有 App 改成 Rare bucket。Job、Alarm、位置、网络、显示与性能策略会分别根据 low-power 状态调整，OEM 还能加入刷新率、性能上限或传感器策略。某项功能是否改变，应在目标 build（系统构建版本）上读取状态并测量。

### Low Power Standby 的限制更直接

Android 13（API 33）公开 Low Power Standby（低功耗待机）状态。启用后，设备处于非交互状态且不在 maintenance window（维护窗口）时，App 的网络访问会被禁用，持有的 WakeLock 会被忽略；运行 FGS 的 App 也在范围内。系统角色、ongoing call（进行中的通话）、临时 allowlist（允许列表）或设备 policy（策略）可以获得例外。

App 可用 `isLowPowerStandbyEnabled()` 检查功能是否开启，并监听 `ACTION_LOW_POWER_STANDBY_ENABLED_CHANGED`。排查“FGS 明明活着却断网”时，要把 Low Power Standby 与 Doze、Data Saver 分开确认。

### Adaptive Battery 与 Routine Battery Saver

- Adaptive Battery（自适应电量管理）影响单个 App 的 bucket 分类，分类器可以使用预测或最近使用排序。
- Routine Battery Saver（按日常规律触发的省电模式）是 Android 10 的可选 OEM 集成。OEM 通过 `config_batterySaverScheduleProvider` 指定特权 provider（策略提供方），provider 用受 `POWER_SAVER` 保护的 API 提供启用提示。
- Adaptive Charging（自适应充电）属于电池健康与充电管理，设备实现可能根据日程、温度和电池状态控制充电。它不等于 App Standby 或 Battery Saver，也不能从 Android 版本推导每台设备的充电曲线。

三项功能可能同时存在，证据入口分别是 bucket、low-power 状态，以及充电与 battery health（电池健康）服务。

### Battery Saver 测试

下面的官方测试命令模拟设备断开电源，并打开 `low_power` 系统设置项；测试结束后恢复 BatteryService 状态。

```bash
adb shell dumpsys battery unplug
adb shell settings put global low_power 1
adb shell dumpsys power
adb shell dumpsys jobscheduler com.example.app

# 测试结束后恢复
adb shell dumpsys battery reset
```

性能基准要记录 Battery Saver、Low Power Standby、温度、充电和屏幕状态。CPU 频率下降或帧率变化属于设备结果，不能仅凭 `low_power=1` 预设固定幅度。

## OEM 功耗策略：按具体设备验证行为

AOSP 允许厂商调整 bucket 分类和低功耗策略。ROM 还可能提供自启动、关联启动、后台活动、睡眠待机、冻结和用户白名单等设置。这些名称、默认值和行为会随品牌、机型、地区与系统版本改变。

社区站点 Don't Kill My App 适合发现兼容性线索，不属于稳定的 API 契约。文档中出现“十分钟后冻结”“某品牌默认禁止全部自启动”或固定排行时，必须给出机型、build、地区、设置状态和复现证据；缺少这些条件就应删除数字。

### 区分几种容易混淆的现象

| 现象 | 进程与包状态 | 证据 |
| --- | --- | --- |
| Job 等待系统条件 | 进程可能不存在，包可正常启动 | Job pending reason、bucket、Doze、quota |
| OEM/内核冻结 | 进程可能仍在，但线程长时间不获调度 | vendor（厂商）日志、cgroup/freezer（控制组冻结）状态、sched trace（调度跟踪）；接口随设备变化 |
| 低内存回收 | 进程消失，系统有内存压力 | `ApplicationExitInfo`、lmkd/LMKD（低内存终止守护进程）日志、PSI（Pressure Stall Information，压力停顿信息）与内存 trace |
| force-stop（强制停止）/用户停止 | 包进入 stopped（已停止）状态，后台触发被阻断 | package/activity 状态、用户操作时间、重新点击图标后的恢复 |
| Hibernation | 长期未用，权限和后台任务被重置 | unused-app（未使用应用）设置、权限、Job/Alarm 与 push 状态 |
| Archiving | APK 被移除，用户数据保留 | Launcher/PackageInstaller 的 archive metadata（归档元数据）与 installer 状态 |

只凭 Perfetto 里“线程没有 runnable slice（处于可运行状态的时间段）”无法证明 OEM 冻结。线程可能正在 epoll（I/O 事件等待机制）中等待，Job 也可能尚未分发。判断冻结需要 ROM 侧状态或 vendor 日志支撑。

### 兼容性测试方法

- 为每个目标机型记录 `ro.build.fingerprint`（系统构建标识）、地区、系统更新版本和电池设置。
- 同一 App 包与账号分别测试屏幕关闭、重启、充电、低电量、网络切换和多日不互动。
- 保存 `dumpsys jobscheduler`、`deviceidle`、`alarm`、`activity processes`、bucket、AppOps（应用操作与权限状态）与设置页截图。
- 读取 `ApplicationExitInfo`，区分 low memory（低内存）、crash（崩溃）、ANR（应用无响应）、user requested（用户请求）和其他退出原因。
- 推送测试记录服务端发送时间、设备到达时间、通知展示与用户交互，不能只记录“收到/未收到”。
- 只有核心功能确受限制时才向用户解释设置入口；设置页面名称按设备动态展示，避免写成跨 ROM 固定路径。

删除系统包、禁用电源管理服务或要求所有用户打开“无限制”都不适合作为产品修复。前两项会改变系统安全与兼容性，后一项会增加用户电量成本。

## 统一诊断：按控制器收集证据

| 需要回答的问题 | Framework 入口 | 调试入口 |
| --- | --- | --- |
| 设备是否在 Light/Deep Doze | `DeviceIdleController` | `dumpsys deviceidle` |
| App 属于哪个 bucket | `AppStandbyController`、`UsageStatsService` | `am get-standby-bucket`、`dumpsys usagestats appstandby` |
| Job 为什么等待 | `JobSchedulerService`、controllers（各约束控制器） | `dumpsys jobscheduler`、pending reason APIs |
| Battery Saver 是否生效 | `PowerManagerService`、`BatterySaverController` | `dumpsys power`、`settings get global low_power` |
| Low Power Standby 是否限制网络/WakeLock | `LowPowerStandbyController` | `dumpsys power`、PowerManager API |
| 后台界面为何被拒绝 | ActivityTaskManager BAL controller、`ActivityOptions` | ActivityTaskManager 日志、调用链与 opt-in mode |
| 是否进入 kernel suspend | SystemSuspend、kernel PM（内核电源管理） | Perfetto/ftrace `power/suspend_resume`、wakeup sources、CPU idle |

Perfetto 配置至少考虑 `sched/*`、`power/suspend_resume`、`power/cpu_idle`、`power/cpu_frequency`，再按问题加入 Binder、network 和 Framework `power`/`am` category（类别）。轨道名称和可用数据受 build 与厂商影响，`dumpsys` 快照与 trace 必须对应同一测试窗口。

## 版本演进

| 版本 | 系统级功耗与后台行为变化 |
| --- | --- |
| Android 6.0 / API 23 | Doze、App Standby、battery optimization exemption |
| Android 7.0 / API 24 | Light Doze；屏幕关闭且移动时也能应用较轻限制 |
| Android 8.0 / API 26 | 后台 Service、后台位置与隐式广播限制 |
| Android 9 / API 28 | App Standby Buckets、Adaptive Battery；定位节电 mode API |
| Android 10 / API 29 | BAL 限制、`ACCESS_BACKGROUND_LOCATION`、可选 Routine Battery Saver |
| Android 11 / API 30 | 未使用 App 权限自动重置；后台位置改为通过系统设置授予 |
| Android 12 / API 31 | Restricted bucket、App hibernation 完整效果、精确闹钟 special access |
| Android 13 / API 33 | Restricted 无互动阈值改为 8 天；Low Power Standby 公开 API；高优先级 FCM quota 与 bucket 脱离 |
| Android 14 / API 34 | PendingIntent 发送方 BAL opt-in；FGS type 与权限校验；Job pending reason API |
| Android 15 / API 35 | PendingIntent 创建方 BAL opt-in；OS 级 App Archiving；部分 FGS type 时长限制 |
| Android 16 / API 36 | Active bucket、top-started 和 FGS 并发 Job 受 runtime quota；多原因与历史 pending API |
| Android 17 / API 37 | `getPendingJobReasonStats()`；listener 型 exact allow-while-idle Alarm；`IntentSender.sendIntent()` BAL opt-in |

## 复核清单

- 是否把 Doze 状态与 kernel suspend 证据分开？
- 是否同时检查 Light Doze、Deep Doze 和维护窗口？
- FGS 是否被错误地当成 Doze、Job quota 或 Low Power Standby 豁免？
- bucket 配额是否注明“近似指导值”，并记录充电与进程状态？
- Android 16+ 是否验证 top-started（从最前台状态启动）与 FGS 并发 Job 的 quota？
- Android 17 是否使用 pending reason stats 解释等待时间？
- Adaptive Battery 描述是否停留在公开契约，没有猜测模型结构？
- BAL 调用链是否按 sender、creator、IntentSender 与 targetSdk 分别检查？
- 后台位置是否同时满足权限、可见性、FGS type 和启动条件？
- Hibernation 与 Archiving 是否按权限、APK、数据和恢复语义区分？
- Battery Saver、Low Power Standby、Data Saver 与 Doze 是否分别取证？
- OEM 结论是否附机型、build、地区、设置和 trace/log？
- 测试结束后是否恢复 battery、deviceidle 与 AppOps 状态？

## 与其他章节的关系

§5.6 解释 cpuidle（CPU 空闲管理）、cpufreq（CPU 频率管理）、EAS（Energy Aware Scheduling，能量感知调度）与 suspend 的基础，§11.1 说明能量归因，§11.2 讨论 App 如何减少 WakeLock、Job、位置和网络开销。本节说明二者之间的关系：Framework 策略决定任务何时获得资源，内核与硬件决定设备能进入多深的低功耗状态。进程被回收时还要结合 §1.3，避免把 LMKD 与功耗限制混为一类。

## 参考资料

### 官方与 API 文档

- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details)
- [Test power-related issues](https://developer.android.com/topic/performance/power/test-power)
- [AOSP：Platform power management with Doze](https://source.android.com/docs/core/power/platform_mgmt)
- [AOSP：Power management](https://source.android.com/docs/core/power/mgmt)
- [AOSP：App background behavior trackers](https://source.android.com/docs/core/power/trackers)
- [AOSP：Routine Battery Saver](https://source.android.com/docs/core/power/routine-battery-saver)
- [PowerManager API](https://developer.android.com/reference/android/os/PowerManager)
- [JobScheduler API](https://developer.android.com/reference/android/app/job/JobScheduler)
- [AlarmManager API](https://developer.android.com/reference/android/app/AlarmManager)
- [Android 17 features and APIs](https://developer.android.com/about/versions/17/features)
- [Secure background activity launches](https://developer.android.com/guide/components/activities/secure-bal)
- [Background FGS start restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Background location](https://developer.android.com/develop/sensors-and-location/location/background)
- [Background execution limits](https://developer.android.com/about/versions/oreo/background)
- [App hibernation](https://developer.android.com/topic/performance/app-hibernation)
- [Android 15 App archiving](https://developer.android.com/about/versions/15/features#app-archiving)

### Android 17 源码锚点

- [DeviceIdleController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java)
- [AppStandbyController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java)
- [JobSchedulerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java)
- [QuotaController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java)
- [JobScheduler.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java)
- [PowerManagerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java)
- [LowPowerStandbyController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/LowPowerStandbyController.java)
- [BatterySaverController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverController.java)
- [BatterySaverPolicy.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverPolicy.java)
- [ActivityOptions.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/app/ActivityOptions.java)

### Android 17 Kernel 锚点

- [kernel/power/suspend.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/kernel/power/suspend.c)
- [kernel/sched/idle.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/kernel/sched/idle.c)
- [drivers/base/power/wakeup.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c)

### OEM 行为线索

- [Don't Kill My App](https://dontkillmyapp.com/)：社区维护的设备行为记录，只用于兼容性线索，结论需在目标 build 复测
