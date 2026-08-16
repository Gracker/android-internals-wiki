---



status: "finalized"
title: 后台执行限制与优化
chapter: '5.7'
section: '5.7'
applicable_versions: Android 6.0 (API 23) - Android 17 (API 37)
last_verified: "2026-06-21"
last_verified_against: "Android Developers Android 17 bg-audio docs + JobScheduler/IBinder API reference + source.android cached apps freezer docs"
confidence: high
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/07-cpu-evolution.md"
  - "src/part1-fundamentals/ch05-cpu-power/17-fgs-type-declaration-background-performance.md"
  - "src/part1-fundamentals/ch05-cpu-power/21-adaptive-battery-app-standby-coordination.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.23-android17-background-audio-hardening-leaudio-power-source.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.34-android17-task-scheduler-optimization.md"
sources:
- type: official
  path: https://developer.android.com/training/monitoring-device-state/doze-standby
- type: official
  path: https://developer.android.com/topic/performance/appstandby
- type: official
  path: https://developer.android.com/topic/performance/power/power-details#app-stdby-bucket
- type: official
  path: https://developer.android.com/about/versions/oreo/background
- type: official
  path: https://developer.android.com/about/versions/14/changes/fgs-types-required
- type: official
  path: https://developer.android.com/about/versions/15/behavior-changes-15#fgs-hardening
- type: official
  path: https://developer.android.com/about/versions/15/changes/foreground-service-types
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/data-transfer-options
- type: official
  path: https://developer.android.com/develop/background-work/services/alarms/schedule
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- type: official
  path: https://developer.android.com/reference/android/app/Service
- type: official
  path: https://developer.android.com/reference/android/app/job/JobScheduler
- type: aosp
  path: frameworks/base/core/java/android/app/usage/UsageStatsManager.java
- type: aosp
  path: frameworks/base/core/java/android/app/Service.java
- type: aosp
  path: frameworks/base/services/usage/java/com/android/server/usage/AppStandbyController.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/DeviceIdleController.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java
- type: aosp
  path: frameworks/base/core/java/android/os/IBinder.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
tags:
- 后台限制
- Doze
- App Standby
- 前台服务
- WorkManager
- JobScheduler
- AlarmManager
- 省电
- 后台启动
- BAL
related_chapters:
- '5.6'
- '5.8'
- '11.2'
- '8.4'
pipeline_stage: ready-to-publish
task6_state: reviewed
task2b_state: fixed
task9_state: reviewed
---


# 5.7 后台执行限制与优化

## 为什么要了解后台执行限制

Perfetto 中若显示灭屏后某个进程仍持续占用 CPU，或 Battery Historian 中反复出现后台闹钟（`alarm`）、调度任务（`job`）和网络（`network`）活动，需要判断是应用工作没有停止，还是系统规则已经限制了执行机会。

Android 的后台限制持续演进。Android 6.0 引入休眠模式（Doze）和应用待机（App Standby），Android 8.0 开始限制后台服务（Service），Android 9 把 App Standby 细分为多个待机桶（App Standby Buckets），Android 12 加入 Restricted 桶并限制从后台启动前台服务（Foreground Service，FGS）。Android 14 和 15 又为 FGS 类型、权限和超时规定了更明确的运行时规则。JobScheduler 在 API 34 公开单个等待原因（pending reason），用于说明任务为何尚未执行；API 36 增加多原因与历史视图，API 37 再增加按原因统计的累计等待时长。

了解这套机制有两个直接用途：后台任务未按预期执行时，可以区分系统延后与应用缺陷；确有后台需求时，可以按任务含义选择 API，避免用前台服务、精确闹钟或轮询制造持续负载。

CPU 调度（5.1）、EAS（5.2）、大小核（5.3）、DVFS（5.4）、Thermal（5.5）和 Android 功耗管理框架（5.6）说明硬件如何分配资源；本节关注 Android framework（系统框架）何时允许应用在后台继续使用这些资源。

## Android 后台限制如何逐步细化

### Android 6.0 之前：还没有 Doze 这类设备空闲总控

在 Android 6.0（Marshmallow）之前，平台还没有 Doze 这类统一的设备空闲状态机。进程优先级、Service 生命周期、Alarm 批处理和厂商省电策略已经存在，但应用更容易借助唤醒锁（WakeLock）、Service、Alarm 和轮询在灭屏后继续运行。这不等于当时“后台完全没有限制”，只是 framework 尚未通过 Doze 和 App Standby 系统性地推迟设备空闲期工作。

### Android 6.0-7.1：Doze、App Standby 与 Light Doze

Android 6.0 同时引入了 **Doze** 和 **App Standby**。Doze 根据设备整体状态工作：设备满足灭屏、静止、未充电等条件后，大量后台活动会被推迟到系统定期开放的维护窗口（maintenance window）。App Standby 根据单个应用的使用情况工作，长时间未被用户打开或交互的应用会受到更严格的后台限制。

Android 7.0（API 24）又加入 **Light Doze**（浅层休眠）。设备灭屏后便可能进入这一较温和的空闲（idle）流程，不必等到“长时间静止”才开始限制活动。它的限制程度低于 Deep Doze（深层休眠），但已经会推迟一部分后台工作。

### Android 8.0：后台 Service 被系统限制

Android 8.0（API 26，Oreo）明显改变了后台执行模型。这组限制默认作用于目标 API 为 26 及以上，即 `targetSdkVersion >= 26` 的应用。应用转入后台后，已有后台 Service 通常还有数分钟宽限期；宽限期结束后会被停止，从后台创建 Service 也会受限。通知携带的 `PendingIntent`（可由系统稍后代应用执行的操作凭据）、Firebase Cloud Messaging（FCM）的高优先级消息等入口，还可能让应用暂时进入允许名单（temporary allowlist）。因此，调用 `startService()` 是否失败，要结合进程状态、目标 SDK 版本与豁免条件判断。

需要延续用户可感知的工作时，可以先调用 `startForegroundService()`，再在系统规定的时限内调用 `startForeground()` 显示通知。可延迟的工作更适合 JobScheduler 或 WorkManager。同一轮变更还限制了目标 API 为 26 及以上的应用在 manifest（应用清单文件）中注册多数隐式广播；显式广播、只面向本应用的广播、签名权限广播、豁免广播与运行时注册仍有各自的适用条件。

### Android 9-10：Buckets 与 BAL

Android 9（API 28）把 App Standby 进一步细化为 **App Standby Buckets**，由“常用/不常用”的粗略区分，变成 Active、Working Set、Frequent、Rare 四个主要等级。Android 12 以后又加入 Restricted 桶。

Android 10（API 29）开始限制 **后台启动 Activity（Background Activity Launch，BAL）**。从后台启动 Activity 需要满足用户可见性或系统豁免等条件，锁屏后直接弹出页面的许多路径会被系统阻止。

### Android 12-17：Restricted bucket、FGS 类型和调试接口

Android 12（API 31）进一步加严后台限制：

- 加入 **Restricted bucket**，对高耗电或长时间不使用的应用施加更严格的 job、alarm 和 network 配额
- 后台启动前台服务时，如果不满足豁免条件，会抛 `ForegroundServiceStartNotAllowedException`
- 精确闹钟（exact alarm）进入特殊应用权限（special app access）体系，`targetSdkVersion >= 31` 的应用需要先确认是否获准使用

Android 13（API 33）继续调整 Restricted bucket 与后台资源策略。分桶条件和阈值属于系统实现，厂商也能采用自己的非 Active 分桶标准，应用不能把某个天数当作稳定规则。Doze 允许名单（allowlist）等豁免还会改变待机桶限制是否生效。

Android 14（API 34）要求 FGS **显式声明类型**，系统会严格校验类型、专属权限和运行时前提。Android 15（API 35）又加入 `mediaProcessing` 类型，并为 `dataSync` / `mediaProcessing` 设置 6 小时预算和 `Service.onTimeout(...)` 超时回调。

Android 16（API 36）加入 `getPendingJobReasons()` 与 `getPendingJobReasonsHistory()`，并把 Active bucket、由前台顶层应用启动的任务（top-started job）和与 FGS 并行执行的 Job 纳入运行时配额。Android 17（API 37）增加 `getPendingJobReasonStats()`，用于按原因汇总累计等待时长；后台音频也新增生命周期与“使用期间”资格（While-In-Use，WIU）约束。

## Doze 与 App Standby 机制的内部工作

Doze 和 App Standby 经常一起出现，但作用对象不同。Doze 看设备整体状态，App Standby 看单个应用的活跃度。排查后台任务时，需要同时核对这两个维度。

### Deep Doze：把后台工作压缩到维护窗口

Deep Doze 在设备灭屏、静止、未充电一段时间后触发。进入这一状态后，系统会推迟大多数后台活动，只在维护窗口内集中提供一小段执行时间。

Doze 期间，常见限制包括：

- 常规网络访问暂停，通常到维护窗口才会恢复
- 普通 `AlarmManager` 闹钟会推迟到维护窗口
- `JobScheduler`、`SyncAdapter` 等延迟型后台任务会被后移
- Wi-Fi 扫描等周期性动作会被减少或延后

`setAndAllowWhileIdle()` / `setExactAndAllowWhileIdle()` 仍能在 Doze 中触发，但这类空闲期间闹钟（while-idle alarm）也有单独的频率上限，不能作为不受限制的后台入口。

### Light Doze：先限流，再进入更深 idle

Android 7.0 引入 Light Doze。设备灭屏后就可能先进入这一层。它比 Deep Doze 温和，但已经会推迟一部分 job、同步（sync）和网络活动。很多“刚锁屏就不再立即回调”的现象发生在 Light Doze 阶段，不必等到 Deep Doze。

### App Standby Buckets：桶常量在 UsageStatsManager，分桶逻辑在 AppStandbyController

App Standby Bucket 的常量定义在 `UsageStatsManager`，桶位管理由 `AppStandbyController` 负责；Doze / device idle 则由 `DeviceIdleController` 负责。在 `android-17.0.0_r1` 中，后两个服务都位于 JobScheduler APEX。APEX 是 Android 用来独立更新部分系统组件的模块格式。

```java
// frameworks/base/core/java/android/app/usage/UsageStatsManager.java
public static final int STANDBY_BUCKET_ACTIVE = 10;
public static final int STANDBY_BUCKET_WORKING_SET = 20;
public static final int STANDBY_BUCKET_FREQUENT = 30;
public static final int STANDBY_BUCKET_RARE = 40;
public static final int STANDBY_BUCKET_RESTRICTED = 45;
public static final int STANDBY_BUCKET_NEVER = 50; // @hide
```

这些常量对应待机等级。应用开发者通常会接触五个公开桶：Active、Working Set、Frequent、Rare、Restricted。`NEVER` 是内部桶，表示安装后一次也未启动的应用。

当前官方 `power-details` 页面给出的资源上限如下。表中数值是应用状态（App state）与设备状态（device state）没有进一步改变限制时的基线：

| Bucket | Regular jobs | Expedited jobs | Alarms | Network |
|------|------|------|------|------|
| Active | 60 分钟滚动窗口内最多 20 分钟 | 24 小时滚动窗口内最多 30 分钟 | 无额外执行上限 | 不限 |
| Working Set | 4 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 15 分钟 | 每小时最多 10 次 | 不限 |
| Frequent | 12 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 10 分钟 | 每小时最多 2 次 | 不限 |
| Rare | 24 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 10 分钟 | 每小时最多 1 次 | 禁用 |
| Restricted | 每天 1 次，最多 10 分钟 | 24 小时滚动窗口内最多 5 分钟 | 每天 1 次，只能是 exact 或 inexact alarm 之一 | 禁用 |

这些上限适用于设备由电池供电、应用没有额外豁免的基线情况。官方 App Standby 文档说明，Standby bucket 的限制只在电池供电（on battery）时生效；`power-details` 页面也列出了充电（charging）、亮屏（screen on）、灭屏且 Doze 生效（screen off + doze active）三种设备状态的差异。充电时基本不按桶限制，灭屏且 Doze 生效时，常规 alarm、job 和 network 还会叠加维护窗口约束。

开发者侧最常用的查询入口仍是 `UsageStatsManager.getAppStandbyBucket()`。测试时可以用 Android 调试桥（ADB）命令 `adb shell am get-standby-bucket <package>` 读取当前桶位，用 `adb shell am set-standby-bucket <package> <bucket>` 强制切换桶位。

### Bucket 是资源控制器的共同输入，不是单独的执行器

`AppStandbyController` 维护 bucket 及其变更原因（reason），预测组件、用户交互和系统规则都可能更新它。随后，JobScheduler 的 `QuotaController`、AlarmManager、`NetworkPolicyManagerService`，以及与省电模式（Battery Saver）相关的 `AppStateTrackerImpl`，分别使用这份应用状态。它们并没有合并成一个“自适应电池（Adaptive Battery）调度器”：同一 bucket 对 job、alarm、network 的影响不同，还会叠加充电状态、Doze、用户设置的后台限制与豁免。

预测得到的 bucket 也有时效性。在 Android 17 的 Android 开源项目（Android Open Source Project，AOSP）中，预测超过约 12 小时没有刷新便会失效，随后由系统规则重新评估。该超时不表示“12 小时后应用必定进入 Rare”。排查状态变化时，应记录 bucket、reason、预测时间、设备状态，以及各相关系统服务的 `dumpsys` 输出，不能只看设置页中的 Adaptive Battery 开关。

### 观测方法：先看 `dumpsys`，再看 Battery Historian / Perfetto

`dumpsys` 是读取 Android 系统服务当前状态的诊断命令。排查后台任务时，不能假设每份 trace（性能跟踪记录）中都存在 `device_idle` 轨道；能否直接看到 Doze 状态切换，取决于 trace config（采集配置）、系统版本和厂商裁剪。

观测顺序如下：

- `adb shell dumpsys deviceidle`，确认当前是否进入 light / deep doze，以及 allowlist 状态
- `adb shell dumpsys usagestats appstandby` 或 `adb shell am get-standby-bucket <package>`，确认 bucket
- `adb shell dumpsys jobscheduler <package>`，确认 job 的 pending reason、quota 和实际约束
- 系统诊断报告（bugreport）/ Battery Historian，观察灭屏后 alarm、job、network、wakelock 的时间分布
- Perfetto：在 trace config 已包含 framework、power、batterystats 相关数据源时，再查看灭屏（screen-off）期间的 CPU 活动、唤醒（wakeup）、alarm/job 时间片（slice）和网络活动

Perfetto 更适合回答“后台工作是否拖慢前台、是否在灭屏后持续占用 CPU”；`dumpsys` 和 Battery Historian 更适合回答“系统为何没有立即执行任务”。

Battery Historian 已不再积极维护，适合读取已有 bugreport 中系统事件之间的时间关联；新的性能采集和可重复实验应优先使用 Perfetto、Android Studio Power Profiler 与明确的 `dumpsys` 快照。

使用 `bugreport` 与 `dumpsys` 也能取得等价证据，不必等 trace 中恰好出现 `device_idle` 轨道。

第一组证据用于观察 Doze 状态切换。设备灭屏、静止、未充电后，`dumpsys deviceidle` 显示的状态会从 `active` 进入 `idle` / `idle maintenance`。在对应的 Battery Historian 时间线上，`screen` 熄灭后，`cpu_running` 会从连续活跃变为稀疏脉冲，`job`、`alarm`、`network` 条带集中出现在短暂窗口内；这与官方 Doze 文档描述的 maintenance window 行为一致。14.8《Battery Historian 与功耗分析工具》已经分别说明 `cpu_running`、`wake_lock`、`job`、`alarm` 这些行的含义，可以直接对照阅读。

第二组证据用于观察后台任务被延后。把目标包切到 `Rare` 或 `Restricted` 桶后，先用 `dumpsys jobscheduler <package>` 查看 pending reason、配额（quota）和约束，再看 Battery Historian 的 `job` 行，或 Perfetto 中短时间密集出现的 CPU / network 活动（burst）。正常情况下，任务不会消失，执行时间会被移到配额允许或 Doze 维护窗口到来之后。11.4《功耗分析案例集》中的 AlarmManager 滥用案例显示每 60 秒出现一次 `alarm` 唤醒条带，JobScheduler 生命周期错误案例则显示持续 30 分钟的 `WakeLock` 条带。两组样本的问题类型不同，但都能作为可复核的对照，用于区分系统主动延后与任务异常持续运行。

如果 trace config 已启用 power、batterystats 和调度数据源，Perfetto 中可能会出现更少的可运行时间片（runnable slice，即线程已具备运行条件但仍在等待 CPU 的区间），并在维护窗口附近出现短促的 network / alarm burst。CPU 频率是否下降取决于同期系统负载，不能单独用来证明 Doze 已生效。缺少这些数据源时，不应根据空白轨道推断结论，应回到 `dumpsys` 与 bugreport。

## 前台服务：用户可感知工作的运行契约

当应用需要在后台持续执行用户可感知的工作时，前台服务（Foreground Service，FGS）仍是直接选择。系统要求这类工作始终对用户可见，并且会严格校验启动 FGS 的用途和条件。

FGS 能否运行取决于五项检查：调用时应用是否具备从后台启动的资格，manifest 是否声明服务类型，类型专属权限是否齐全，camera / microphone / location 等仅限使用期间的权限（while-in-use permission）在调用时是否有效，以及服务是否在时限内调用 `startForeground()` 并持续满足通知与超时规则。异常出现在哪一项，决定排查 `ForegroundServiceStartNotAllowedException`、`SecurityException`、类型错误，还是前台升级超时（promotion timeout，即启动 Service 后未及时调用 `startForeground()`）。FGS 只改变服务生命周期和用户可见性，并不保证更高的 CPU 优先级或固定频率。

### 前台服务类型体系

目标 API 为 34 及以上的应用必须声明合适的 FGS 类型。manifest 未声明类型，或已声明类型但缺少专属权限或运行时前提时，`startForeground()` 可能失败。

| 类型 | API 34+ 专属权限 | 强校验版本 | 典型场景 |
|------|------|------|------|
| `camera` | `FOREGROUND_SERVICE_CAMERA` | Android 14 | 用户发起的相机操作、视频通话 |
| `connectedDevice` | `FOREGROUND_SERVICE_CONNECTED_DEVICE` | Android 14 | BLE、USB、外设连接 |
| `dataSync` | `FOREGROUND_SERVICE_DATA_SYNC` | Android 14 | 云同步、备份、上传下载 |
| `health` | `FOREGROUND_SERVICE_HEALTH` | Android 14 | 运动 / 健康数据采集 |
| `location` | `FOREGROUND_SERVICE_LOCATION` | Android 14 | 导航、持续定位 |
| `mediaPlayback` | `FOREGROUND_SERVICE_MEDIA_PLAYBACK` | Android 14 | 音视频播放 |
| `mediaProjection` | `FOREGROUND_SERVICE_MEDIA_PROJECTION` | Android 14 | 投屏、录屏 |
| `microphone` | `FOREGROUND_SERVICE_MICROPHONE` | Android 14 | 录音、语音通话 |
| `phoneCall` | `FOREGROUND_SERVICE_PHONE_CALL` | Android 14 | VoIP / 通话保持 |
| `remoteMessaging` | `FOREGROUND_SERVICE_REMOTE_MESSAGING` | Android 14 | 设备间消息连续性 |
| `shortService` | 无专属权限（仍需 `FOREGROUND_SERVICE`） | Android 14 | 约 3 分钟内必须完成的关键短任务 |
| `specialUse` | `FOREGROUND_SERVICE_SPECIAL_USE` | Android 14 | 无法归类到标准类型的特殊场景 |
| `systemExempted` | `FOREGROUND_SERVICE_SYSTEM_EXEMPTED` | Android 14 | 设备拥有者、紧急角色等系统级集成 |
| `mediaProcessing` | `FOREGROUND_SERVICE_MEDIA_PROCESSING` | Android 15 | 转码、导出、媒体加工 |

`camera`、`microphone`、`location` 等类型还会叠加 while-in-use 权限限制。即使应用满足“允许从后台启动 FGS”的豁免条件，只要相应的运行时权限仅在应用处于前台时有效，仍无法从后台启动这类 FGS。

下面以 `dataSync` 服务为例，展示 manifest 中至少需要声明的权限与服务类型：

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />

<service
    android:name=".SyncService"
    android:exported="false"
    android:foregroundServiceType="dataSync" />
```

这段声明只完成类型与权限登记。应用仍需满足 FGS 启动来源、通知、目标版本和相应类型的运行时条件。

### 超时机制：`shortService` 看单次时长，`dataSync` / `mediaProcessing` 看 24 小时预算

`shortService` 的规则来自 Android 14 的 FGS types 文档。它没有类型专属权限，但只能运行大约 3 分钟，计时从 `startForeground()` 开始。Android 14 文档明确要求实现 `Service.onTimeout()`：超时后，系统会留给应用几秒钟调用 `stopSelf()` / `stopForeground()`；如果服务仍未退出，应用会触发带 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` 的“应用无响应”（Application Not Responding，ANR）错误。官方同时说明，这个回调在 Android 13 及以下不存在，因此兼容旧版本时，应用仍需主动控制停止时机。

对于目标 API 为 35 及以上的应用，Android 15 为 `dataSync` 和 `mediaProcessing` 增加了累计时长预算。两种类型分别按 24 小时窗口统计，同一类型的所有 FGS 共用 6 小时额度；用户把应用带回前台后，计时器重置。预算用完后，再启动同类型 FGS 会直接失败；Android 15 行为变更页给出的报错示例是 `Time limit already exhausted for foreground service type dataSync`。

这一组超时回调以 Android Developers 的 `Service` API 参考文档和 Android 15 行为变更页为准。当前参考文档同时列出 `onTimeout(int startId)` 和 `onTimeout(int startId, int fgsType)` 两个重载：前者对应 `shortService`，后者对应 Android 15 新增的类型化超时。`dataSync` / `mediaProcessing` 收到 `Service.onTimeout(int, int)` 后，如果数秒内仍未调用 `stopSelf()`，Android 系统日志工具 Logcat 会记录 `RemoteServiceException`；`shortService` 超时后仍不退出则会触发 ANR。

### Android 17 的后台音频硬化

API 37 对后台音频操作施加了更严格的约束。在 Android 17 上运行的所有应用，只要从后台开始播放、请求音频焦点（audio focus，即协调多个应用音频输出优先级的机制）或调节音量，都需要有可见 Activity，或正在运行一个类型不是 `shortService` 的 FGS；如果 `targetSdkVersion` 为 37，该 FGS 还要具备 WIU 资格。由 `BOOT_COMPLETED`（设备启动完成广播）等后台触发器启动的 `mediaPlayback` FGS，如果没有由用户操作形成的 WIU 资格，调用 `AudioManager.requestAudioFocus()` 会返回 `AUDIOFOCUS_REQUEST_FAILED`，播放和音量 API 也可能在不抛异常的情况下失败。

有一项例外需要单独判断：`targetSdkVersion` 为 37 的应用如果已获得 exact alarm 权限，并且操作的是闹钟用途音频流 `USAGE_ALARM`，官方文档明确豁免 WIU 要求。普通媒体、播客和直播的后台播放，仍应在用户发起播放时启动 `mediaPlayback` FGS，并在播放结束或永久失去音频焦点时停止 FGS。

## WorkManager vs JobScheduler vs AlarmManager：选型指南

这三个 API 都能用于后台任务，但用途差异很大。如果所选 API 与任务需求不匹配，常见结果就是任务延迟或受限。

### WorkManager：默认选择

WorkManager 适合“可以延迟，但希望最终执行”的任务。它会根据系统版本选择实际调度实现，在 API 23 及以上通常使用 JobScheduler，因此 Doze、App Standby bucket 和 quota 仍会生效。

它的优势在于：

- 用 `Constraints` 表达网络、充电、空闲等条件
- 将任务信息持久化到数据库，进程被终止后仍能恢复
- 支持链式依赖和周期任务
- 默认进行批处理，减少零散唤醒

如果任务需要尽快开始，又不适合启动长期 FGS，可以考虑 WorkManager 2.7+ 的 `setExpedited()`。官方文档将加急工作（expedited work）定义为重要、用户在意、可在几分钟内完成且希望立即开始的短任务。它仍受 quota 控制，但与普通 work 相比，较少因 Doze 或 Battery Saver 而长时间延后。

长时运行 Worker（long-running worker）也不能无限执行。即使 WorkManager 为它启动 FGS，任务仍由 JobScheduler 调度；Android 16 起，这类工作可能耗尽应用的 Job 运行时配额（runtime quota）。对于用户主动发起的大数据上传或下载，应评估用户发起的数据传输任务（user-initiated data transfer job）。

### JobScheduler：系统原生调度层

JobScheduler 是 Android 系统原生的调度 API。与 WorkManager 相比，开发者需要自行处理更多细节，但也能直接使用 WorkManager 尚未完整封装的能力，例如 `setPrefetch()`、`setUserInitiated(true)`，以及不同版本逐步加入的 pending reason 调试接口。

API 版本边界如下：

- API 34：`getPendingJobReason(int jobId)` 返回当前一个主因。存在多个原因时，它不会全部返回。
- API 36：`getPendingJobReasons(int jobId)` 返回当前可能原因的 `int[]`；`getPendingJobReasonsHistory(int jobId)` 返回有限的 `List<PendingJobReasonsInfo>` 历史视图。
- API 37：`getPendingJobReasonStats(int jobId)` 返回 `Map<Integer, Duration>`，按原因汇总任务生命周期内的累计等待时长。

历史记录（history）适合观察约束变化顺序，统计数据（stats）适合判断哪类约束的累计影响最大。多个约束可以同时存在，因此 stats 中各项时长之和可能大于总等待时长；这些统计在设备重启后不会保留，任务完成或取消时也会清除。

这些 API 可以在 `android-17.0.0_r1` 的 `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java` 复核。

在性能排查中，`getPendingJobReasonsHistory()` 可以呈现任务最近一段时间未执行的原因变化；`getPendingJobReasonStats()` 则适合判断哪类约束反复阻止 Job 执行。

### AlarmManager：只留给需要精确时刻的事情

AlarmManager 适合需要在精确时间点触发的任务，但这类调用难以参与系统的省电批处理。频繁调用 `setExact()` / `setExactAndAllowWhileIdle()`，会减少系统合并唤醒窗口的机会。

从 Android 12（`targetSdkVersion >= 31`）开始，如果要通过 `PendingIntent` 使用 exact alarm，应用必须先声明并处理 exact alarm special access。`targetSdkVersion >= 33` 时，可以根据场景选择 `SCHEDULE_EXACT_ALARM` 或 `USE_EXACT_ALARM`。代码需要先调用 `AlarmManager.canScheduleExactAlarms()` 检查授权；未获授权时继续调用 exact API 会抛出 `SecurityException`，系统不会自动改为非精确闹钟。

API 37 新增接收 `OnAlarmListener` 与 `Executor` 的 `setExactAndAllowWhileIdle()` 重载。它适合调用进程能够持续存活的短期回调；组件结束或进程不再包含活动组件时，系统可以取消通过监听器注册的闹钟（listener alarm）。如果闹钟需要跨进程生命周期交付，仍应使用 `PendingIntent`。这个重载也不会取消 allow-while-idle 的频率限制。

处理方式通常有三种：

- 引导用户去 `ACTION_REQUEST_SCHEDULE_EXACT_ALARM` 对应的设置页授权
- 改用非精确闹钟（inexact alarm）
- 如果任务本来就不要求秒级，直接改成 WorkManager / JobScheduler

### 例外与豁免：为什么“已经受限”的任务有时还是能跑

多套后台规则会同时生效，系统也为下列场景保留了明确的例外：

- **加急工作 / 加急任务（expedited work / expedited jobs）**：短、急、用户在意的任务可以请求更快执行，但仍受 quota 控制
- **用户发起的数据传输任务（User-initiated data transfer job，UIDT）**：Android 为“用户明确点击上传或下载”这类数据传输提供专用入口，通过 JobScheduler 的 `setUserInitiated(true)` 声明，并要求显示进度通知
- **临时允许名单（temporary allowlist）**：Android 8.0 文档说明，高优先级 FCM、SMS / MMS 广播、通知 `PendingIntent`、VPN 启动等场景会让应用临时进入 allowlist 数分钟；在此期间，应用可以启动 Service 并继续执行后台逻辑
- **Android 12 及以上的后台启动 FGS 豁免**：高优先级 FCM、用户可见交互、exact alarm 等场景仍可能允许启动 FGS；如果 FCM 最终被系统降级，`startForegroundService()` 依旧会因 `ForegroundServiceStartNotAllowedException` 而失败

因此，看到“受限状态下任务仍然执行”，应先核对它是否满足上述例外条件。

### 选型决策

可以按这条路径判断：

1. 必须在精确时刻触发，并且是用户明确期待的提醒或闹钟，选择 AlarmManager
2. 任务很短、由用户刚刚触发且需要马上开始，优先评估 expedited WorkManager
3. 任务是用户主动发起的长时间上传或下载，优先评估 UIDT job
4. 任务可以延迟，但希望条件满足后最终执行，默认选 WorkManager
5. 需要 JobScheduler 的系统级能力或更细的调试接口时，直接使用 JobScheduler
6. 任务需要持续运行，并且必须让用户清楚知道其内容时，使用 FGS

以上规则作用于任务调度。系统还会单独管理缓存进程：应用进入 cached（缓存）状态后，`CachedAppOptimizer` 决定何时暂停进程执行。缓存进程冻结与 Doze、Standby bucket 是并行生效的不同机制。

## CachedAppOptimizer 与 Binder：独立的缓存进程冻结机制

Doze、待机桶和 Job 配额决定后台工作何时获得执行机会；缓存应用冻结器（cached apps freezer）决定已处于 cached 状态的进程能否继续占用 CPU。两类机制可能同时影响同一应用，但触发条件和判断证据不同。

Android 11 起支持 cached apps freezer。Android 14 及以上的官方行为是：在支持并启用该功能的设备上，应用进程进入 cached 状态 10 秒后被冻结；收到 Intent、启动 `JobService`、恢复 Activity 等生命周期事件时，系统立即解冻。设备可以通过配置关闭 freezer，文件锁或特定绑定关系也可能使 cached 进程暂不冻结。因此，仅凭“进入 cached 状态已满 10 秒”仍不能证明进程处于 frozen（已冻结）状态。

冻结后，该进程的所有线程都会暂停，不能执行 CPU 工作、垃圾回收（Garbage Collection，GC）或内存裁剪（memory trim）回调。Android 14 还配套处理了以下情况：

- 进入 cached 状态后，系统可能先请求运行时（runtime）执行一次 GC，为后续冻结做准备；
- 冻结后可能触发额外的内存压缩整理（compaction），例如将已修改的文件页（脏页）写回后备存储（backing storage），或将匿名页换出到压缩交换区 ZRAM；
- 运行时注册的广播（context-registered broadcast）可以排队到进程解冻后再交付；清单接收器（manifest receiver）收到广播时，系统会将进程提升出 cached 状态；
- 如果某个应用的所有进程都被冻结，系统会终止该应用仍保持的 TCP socket（网络连接端点），避免保活包（keepalive）继续唤醒蜂窝通信模块（modem）。

这些动作都受设备支持情况或运行时条件影响。一次 freeze 不能证明 GC、compaction、ZRAM 写入必然发生，也不能根据 4 KB / 16 KB 页大小推算固定的内存回收收益。

### framework 的两阶段冻结

Android 17 的 `CachedAppOptimizer` 先冻结 Binder 接口，再把进程移入 frozen cgroup。Binder 是 Android 的进程间通信（Inter-Process Communication，IPC）机制；cgroup 是内核按组管理进程资源和状态的机制。下面的伪代码展示了调用顺序：

```text
Freezer.freezeBinder(pid, true, timeout = 0)
    ↓ 检查是否有未排空或新到达的事务
Freezer.setProcessFrozen(pid, uid, true)
    ↓ BINDER_GET_FROZEN_INFO 再检查竞态
记录 frozen 状态，并执行冻结后的可选处理
```

这段流程先阻止新的同步 Binder 事务，再暂停全部线程，从而降低调用方等待已无法处理事务的进程而发生死锁的风险。两步并非不可分割的原子操作，因此 framework 在 cgroup freeze 之后还会读取 Binder freezer 状态；如果冻结间隙内出现新的待处理事务（pending transaction），系统会取消本次冻结或执行失败处理。

Android 17 的相关源码入口是：

- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`
- `frameworks/base/services/core/java/com/android/server/am/Freezer.java`
- `system/core/libprocessgroup/profiles/cgroups.json`
- `kernel/common/include/uapi/linux/android/binder.h`
- `kernel/common/drivers/android/binder.c`

### Binder 返回值的准确含义

在 `android17-6.18-2026-06_r6` 中，冻结相关的用户态内核接口（Userspace API，UAPI）包含 `BINDER_FREEZE`、`BINDER_GET_FROZEN_INFO`，以及三个容易混淆的驱动返回项（driver return）：

| 返回项 | 接收方看到的含义 |
|---|---|
| `BR_FROZEN_REPLY` | 调用方发出的同步事务因目标进程处于 frozen 状态而被拒绝 |
| `BR_TRANSACTION_PENDING_FROZEN` | 调用方发出的异步事务已排队，等待目标解冻 |
| `BR_FROZEN_BINDER` | 已注册冻结通知的一方收到远端 Binder 宿主 frozen / unfrozen 状态变化 |

`BR_FROZEN_REPLY` 不是 `BINDER_FREEZE` ioctl（用户态向内核驱动发出的控制调用）的“冻结成功确认”。同步事务到达 frozen 目标时，驱动会向调用方返回失败；异步事务可以保留在目标队列中。`CachedAppOptimizer` 通过 `BINDER_GET_FROZEN_INFO` 发现进程在 frozen 期间收到同步事务后，可能根据 framework 策略终止该 cached 进程。作出终止决定的是 framework，不能描述成“Binder 驱动直接终止目标进程”。

`binder_frozen_status_info.sync_recv` 的位 0（bit 0）表示进程被冻结后收到同步事务，位 1（bit 1）表示冻结步骤中出现新的待处理同步事务；`async_recv` 记录冻结后是否收到异步事务。排查时要结合 framework 的 freeze / unfreeze 日志和调用方错误，不能根据单个位值推断完整时序。

### API 36 的冻结通知与回调队列策略

API 36 公开 `IBinder.addFrozenStateChangeCallback(Executor, FrozenStateChangeCallback)`。它只观察远端 Binder 宿主进程的 frozen / unfrozen 状态，不控制进程冻结。内核不支持冻结通知时会抛出 `UnsupportedOperationException`；如果监听者自身也被冻结，或事件到达过快，系统还可能合并状态通知，因此不能用回调次数统计实际冻结次数。

下面的示例在远端 Binder 宿主被冻结时暂停非必要事务，解冻后再恢复：

```java
binder.addFrozenStateChangeCallback(executor, (who, state) -> {
    if (state == IBinder.FrozenStateChangeCallback.STATE_FROZEN) {
        pauseNonEssentialCallbacks(who);
    } else {
        resumeCallbacks(who);
    }
});
```

这段代码只处理状态变化；注册方还必须配合 `removeFrozenStateChangeCallback()` 管理回调生命周期。远端为本地 Binder 时不会出现独立的冻结状态，因为宿主和监听者位于同一进程。

API 36 的 `RemoteCallbackList.Builder` 进一步提供被调用端冻结策略（frozen callee policy）：

- `FROZEN_CALLEE_POLICY_DROP`：冻结期间不保留回调；
- `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT`：只保留最新状态，解冻后交付；
- `FROZEN_CALLEE_POLICY_ENQUEUE_ALL`：保留事件序列，并受最大队列长度约束；
- `FROZEN_CALLEE_POLICY_UNSET`：保持 API 35 及以前的立即调用行为，仅用于兼容，不建议新代码采用。

状态同步通常选择 `ENQUEUE_MOST_RECENT`，可以重新生成的提示事件可以选择 `DROP`。只有业务必须保留完整事件历史时才选择 `ENQUEUE_ALL`，并设置队列长度上限，以免 frozen 进程解冻后一次收到大量已过期的回调。

## 后台执行对前台性能的影响

性能分析常会聚焦前台应用的渲染和响应，容易遗漏后台行为带来的间接影响。不合理的后台工作经常与前台卡顿、发热和续航缩短同时出现。

### CPU 争抢

最直接的影响是 CPU 资源争用。当前台应用正在执行布局（layout）或绘制（draw）操作时，后台进程的网络请求、数据同步、图片解码等工作会同时竞争 CPU 时间。在大小核架构（5.3 节）下，如果后台任务长期占用前台关键线程所需的 CPU，还可能增加 RenderThread（渲染线程）的可运行等待时间（runnable delay）。

Perfetto 中后台线程与 RenderThread 同时活跃，只能说明两者并发运行。若要证明 CPU 争用或抢占关系，还要对齐掉帧区间，检查 RenderThread 在唤醒（wakeup）、可运行（runnable）和运行中（Running）状态之间的切换，以及同一 CPU 上 `sched_switch` 事件记录的上一运行线程。后台线程恰好出现在同一 CPU 核上，不足以确定因果关系。

### 内存压力

后台进程占用内存会增加系统整体内存压力。压力升高后，内核可能让申请内存的线程直接回收页面（direct reclaim），让后台内核线程 `kswapd` 回收页面，或进行交换区读写（swap I/O）。低内存终止守护进程 `lmkd` 也可能根据压力停顿信息（Pressure Stall Information，PSI）和进程优先级选择要终止的进程。分析前台卡顿时，应对齐 `mm_vmscan`（内存回收事件）、PSI、I/O、`lmkd` 事件与应用的内存分配 / GC 时间片；不能只因后台进程的比例集大小（Proportional Set Size，PSS）较大，就认定它造成了某次 GC 停顿。

### 热节流

持续的后台计算、媒体处理与无线传输会增加整机功耗，进而减少前台工作负载可用的热余量（thermal headroom，即达到热限制前仍可使用的温度与功耗空间）。达到设备热策略阈值后，热管理模块（thermal）、电源硬件抽象层（Power HAL）或频率上限可能共同限制 CPU / GPU 性能。

排查时应同时观察后台负载开始时间、热状态（thermal status）/ 温区、CPU / GPU 频率上限、冷却设备状态和帧耗时。频率下降也可能源于低利用率或省电策略；即使温度上升与掉帧同时发生，仍需通过只改变一个条件的对照实验确认因果关系。

## 与其他机制的关系

**与 CPU 调度（5.1）的关系**：Standby bucket 主要控制 job、alarm、network 等后台资源额度，不会直接为线程设置固定的 CPU 优先级。它主要产生间接影响：后台任务被延后后，可运行线程减少，前台的 CPU 争用压力也会下降。线程进入 runnable 状态后，CPU 如何分配还取决于进程状态、控制组（cgroup）、利用率限制机制（uclamp）、线程策略和具体子系统规则。

**与 EAS（5.2）的关系**：零散的后台任务会产生更多唤醒和短暂 runnable 区间，可能增加 CPU 核选择、线程迁移和频率响应成本。是否发生迁移仍取决于 CPU 亲和性（affinity）、允许线程运行的 CPU 集合（cpuset）、利用率与设备能耗模型（Energy Model）。

**与 DVFS（5.4）的关系**：后台工作提高调度利用率后，CPUFreq 调频策略（governor）可能请求更高频率。Doze 和 bucket 限制会减少不必要的 runnable 负载，使系统更容易合并唤醒并延长空闲（idle）时间。

**与 Thermal（5.5）的关系**：后台同步、转码、上传等持续工作容易逐步升高片上系统（System on Chip，SoC）的温度。温度超过阈值后，Thermal 降频会影响整机性能和前台体验，不会只限制后台线程。

**与 Android 功耗管理（5.6）的关系**：5.6 节侧重 WakeLock、`PowerManagerService`、device idle 等系统机制；本节侧重 framework 规则和 API 选择，说明哪些条件会延后或拒绝应用层后台任务。

**与响应速度（8.4）的关系**：BAL 限制从 Android 10 开始加严，后续版本仍在增加约束。后台能否启动 Activity，取决于用户可见性、通知、`PendingIntent`、`IntentSender` 路径和系统豁免条件，不能直接套用旧版本经验。

## 版本演进

| 版本 | 核心变化 | 性能分析影响 |
|------|----------|-------------|
| Android 6.0 (API 23) | 引入 Doze 和 App Standby | 灭屏后后台任务开始系统级延后 |
| Android 7.0 (API 24) | 引入 Light Doze | 刚灭屏就可能开始限流 |
| Android 8.0 (API 26) | 对目标 API 为 26 及以上的应用限制后台 Service 与 manifest 隐式广播 | 需要结合宽限期、临时允许名单与广播种类判断 |
| Android 9.0 (API 28) | 引入 App Standby Buckets | Job、alarm、network 开始按桶分级限制 |
| Android 10 (API 29) | 增加 BAL 限制 | 后台弹 Activity 的路径明显变少 |
| Android 12 (API 31) | Restricted bucket、后台启动 FGS 限制、exact alarm special access | 后台任务调度和 FGS 启动都要先通过相应条件检查 |
| Android 13 (API 33) | Restricted bucket 与后台资源规则继续调整 | 分桶阈值不是应用可依赖的公开契约 |
| Android 14 (API 34) | FGS 类型强制声明，新增 `remoteMessaging`、`shortService`、`systemExempted` 等类型；cached app 进入 cached 约 10 秒后冻结，并引入冻结前 GC 请求 + 冻结后 compaction | FGS 类型、权限和运行时前提都要写完整 |
| Android 15 (API 35) | `mediaProcessing` 类型加入，`dataSync` / `mediaProcessing` 引入 6 小时预算 | 长时间同步和媒体加工要处理超时回调 |
| Android 16 (API 36) | 多原因 / history API、Job runtime quota 扩大适用范围；Binder 增加 frozen callback | 可定位多重 Job 约束，并按远端 frozen 状态处理回调 |
| Android 17 (API 37) | `getPendingJobReasonStats()`；后台音频要求可见 Activity 或非 short FGS，target 37 后台 FGS 还需 WIU 或满足 alarm 豁免 | Job 原因可聚合分析，后台音频要核对完整生命周期条件 |

## 常见问题与误区

### 误区 1："WorkManager 保证任务在指定时间执行"

WorkManager 不保证精确时间。它定义约束条件，系统在条件满足后的合适时机执行。只有闹钟、日历提醒等用户明确要求准确时刻的功能，才应在处理 exact alarm 权限后使用 AlarmManager；普通定时同步应接受非精确触发或改用 WorkManager / JobScheduler。

### 误区 2："前台服务不会被系统杀掉"

前台服务进程的优先级较高，但系统仍可终止它。内存极度紧张时，系统可能终止前台服务进程。另外，从 Android 15 开始，`dataSync` 和 `mediaProcessing` 类型有 6 小时的超时限制。

### 误区 3："我的 JobScheduler 不执行一定是系统 bug"

常见原因包括 bucket、quota、任务约束和设备状态。先用 `adb shell am get-standby-bucket <package>` 查看桶位，再用 `adb shell dumpsys jobscheduler <package>` 查看具体约束。API 34 可通过 `getPendingJobReason()` 查询单个原因，API 36 可查询多原因和 history，API 37 可查询累计 stats。

### 误区 4："Doze 只在晚上才生效"

Doze 的触发条件是灭屏 + 静止 + 未充电，与时间无关。白天如果手机放在桌上灭屏不动，一样会进入 Doze。

### 误区 5："后台限制只影响后台 App"

后台规则直接控制后台任务的执行机会，但后台工作造成的 CPU 争用、内存压力和热节流也会拖慢前台应用。减少无效后台工作同样有助于改善前台性能。

## 参考资料

### AOSP 源码路径
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java` — Doze / device idle 状态机
- `frameworks/base/core/java/android/app/usage/UsageStatsManager.java` — App Standby bucket 常量定义
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java` — App Standby bucket 管理逻辑
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java` — JobScheduler 服务端实现
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java` — Job quota 与 bucket 约束控制
- `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java` — JobScheduler public API
- `frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java` — AlarmManager public API
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` — cached 进程 freeze 调度入口
- `frameworks/base/services/core/java/com/android/server/am/Freezer.java` — cgroup / Binder freezer 抽象
- `frameworks/base/core/java/android/os/IBinder.java` — `FrozenStateChangeCallback` 定义
- `frameworks/base/core/java/android/os/RemoteCallbackList.java` — frozen callee policy
- `frameworks/base/core/java/android/app/Service.java` — Service 生命周期；FGS timeout 签名以 `Service` API reference 为准
- `kernel/common` `android17-6.18-2026-06_r6`：`include/uapi/linux/android/binder.h`、`drivers/android/binder.c`

### 官方文档
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details#app-stdby-bucket)
- [Background Execution Limits (Android 8.0)](https://developer.android.com/about/versions/oreo/background)
- [Foreground service types are required (Android 14)](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 15 behavior changes: foreground services](https://developer.android.com/about/versions/15/behavior-changes-15#fgs-hardening)
- [Android 15 foreground service types](https://developer.android.com/about/versions/15/changes/foreground-service-types)
- [Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android 16 JobScheduler quota changes](https://developer.android.com/about/versions/16/behavior-changes-all)
- [Define work requests with WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Data transfer background task options](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [Schedule alarms](https://developer.android.com/develop/background-work/services/alarms/schedule)
- [Restrictions on starting a foreground service from the background](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Service API reference](https://developer.android.com/reference/android/app/Service)
- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [Android 17 Features](https://developer.android.com/about/versions/17/features)
- [Android 17 Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)

### 深入阅读
- [Battery Historian 使用指南](https://developer.android.com/topic/performance/power/battery-historian)
- [Perfetto Power Analysis](https://perfetto.dev/docs/quickstart/android-power)
- [Perfetto trace 配置与数据源说明](https://perfetto.dev/docs/concepts/config)
