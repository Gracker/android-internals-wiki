---



status: "finalized"
title: 后台执行限制与优化
chapter: '5.7'
section: '5.7'
applicable_versions: Android 6.0 (API 23) - Android 17 (API 37)
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
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
task6_reviewed_date: 2026-05-18
task6_reviewed_by: openclaw-task6
task9_reviewed_date: "2026-06-21"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-21T19:26:37+08:00"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: 2026-06-04T02:57:11+08:00
task9_state: reviewed
task9_result: auto-fixed
last_task9_review_log: "logs/deep-review/2026-06-21-19-audit.md"
queue_entry: task9-20260518-5.8-freezer-gc-version-boundary
task9_review_notes: "2026-06-04 task9 deep-review: auto-fixed。修正 Android 16 Binder freezer 源码行号，补 Android 17 JobScheduler reason stats 版本边界。 | 2026-06-05 Task9 深度复审：pass-tech-review。P0 0 / P1 0 / P2 0；Doze/App Standby、FGS 超时、Android 17 后台音频硬化、JobScheduler pending reason stats 与 Binder freezer 版本边界复核通过，满足自动晋升 finalized 条件。 | 2026-06-21 Task9 闲时抽检：auto-fixed。修正 Android 17 background audio hardening 的 WIU / exact alarm + USAGE_ALARM 边界；把 cached apps freezer 约 10 秒冻结窗口从 Android 16 修正为 Android 14+；回到 Task6 复审。"
last_task6_at: "2026-06-21T20:07:00+08:00"
last_task6_review_log: "logs/review/2026-06-21-20-review.md"
task6_review_notes: "2026-06-21 20:07 Task6 revisiting-review (post-Task9-auto-fix): pass-light-edit。Task9 修正 Android 17 background audio WIU/USAGE_ALARM 边界及 freezer 冻结窗口版本(Android 14+)。L1/L2 复扫通过，无新增小修，无新增回炉项。自动晋升 finalized。"
last_task9_autofix_at: "2026-06-21"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
last_task9_audit: "2026-06-21"
last_task2b_verify_at: "2026-06-21T19:30:09+08:00"
task2b_verifier_notes: "状态修正：Task9 auto-fix 后 status 应为 ready-for-review，原 finalized 已回退。"
task6_result: pass-light-edit
reviewed_date: 2026-06-21
---


# 5.7 后台执行限制与优化

## 为什么要了解后台执行限制

Perfetto 中若显示灭屏后某个进程仍持续占用 CPU，或 Battery Historian 中反复出现后台 alarm、job、network 活动，需要区分应用工作没有停止和系统已经开始限流两种情况。

Android 的后台限制持续演进。Android 6.0 引入 Doze 和 App Standby，Android 8.0 开始限制后台 service，Android 9 把 App Standby 细化成 Buckets，Android 12 加入 Restricted bucket 并限制后台启动 FGS，Android 14 和 15 又把 FGS 类型、权限和超时写成了更明确的运行时规则。JobScheduler 的单个 pending reason 在 API 34 已公开，API 36 增加多原因与历史视图，API 37 再增加按原因统计的累计等待时长。

这套机制用于解决两类问题：后台任务未按预期执行时，区分系统延后与应用缺陷；存在后台需求时，根据业务语义选择 API，避免用前台服务、精确闹钟或轮询制造持续负载。

CPU 调度（5.1）、EAS（5.2）、大小核（5.3）、DVFS（5.4）、Thermal（5.5）和 Android 功耗管理框架（5.6）说明硬件如何分配资源；这里说明 framework 何时允许 App 在后台继续消耗这些资源。

## Android 后台限制如何逐步细化

### Android 6.0 之前：还没有 Doze 这类设备空闲总控

在 Android 6.0（Marshmallow）之前，平台还没有 Doze 这类统一的设备空闲状态机。进程优先级、Service 生命周期、Alarm 批处理和厂商省电策略已经存在，但应用更容易借助 WakeLock、Service、Alarm 和轮询在灭屏后继续运行。这里不能概括成“后台完全没有限制”，差别在于 framework 尚未用 Doze 和 App Standby 系统性地推迟设备空闲期工作。

### Android 6.0-7.1：Doze、App Standby 与 Light Doze

Android 6.0 同时引入了 **Doze** 和 **App Standby**。Doze 盯的是设备状态，满足灭屏、静止、未充电等条件后，把大量后台活动推迟到维护窗口；App Standby 盯的是单个 App 的使用情况，长时间没被用户碰过的 App 会受到更严的后台限制。

Android 7.0（API 24）又加了 **Light Doze**。设备只要灭屏，就会先进入更温和的 idle 流程，不必等到“长时间静止”才开始限流。它没有 Deep Doze 那么狠，但已经会推迟一部分后台工作。

### Android 8.0：后台 service 被系统限制

Android 8.0（API 26，Oreo）是后台执行模型的分水岭。这组限制默认作用于 target API 26 及以上的应用。应用转入后台后，已有后台 Service 通常还有数分钟宽限期；宽限期结束后会被停止，后台创建 Service 也会受限。通知 `PendingIntent`、高优先级 FCM 等入口还可能让应用进入临时允许名单。因而，调用 `startService()` 是否失败要结合进程状态、target SDK 与豁免条件判断。

需要延续用户可感知工作时，可以先调用 `startForegroundService()`，再及时调用 `startForeground()` 显示通知。可延迟工作更适合 JobScheduler 或 WorkManager。同一轮变更还限制了 target API 26 及以上应用在 manifest 中注册多数隐式广播；显式广播、只面向本应用的广播、签名权限广播、豁免广播与运行时注册仍有各自入口。

### Android 9-10：Buckets 与 BAL

Android 9（API 28）把 App Standby 进一步细化为 **App Standby Buckets**，从按“常用/不常用”粗分，变成 Active、Working Set、Frequent、Rare 四档主桶。Android 12 以后又补上 Restricted 桶。

Android 10（API 29）开始限制 **Background Activity Launch（BAL）**。后台启动 Activity 需要满足用户可见性或系统豁免等条件，锁屏后直接弹出页面的许多路径会被系统阻止。

### Android 12-17：Restricted bucket、FGS 类型和调试接口

Android 12（API 31）进一步收紧后台限制：

- 加入 **Restricted bucket**，给高耗电或长时间不使用的 App 更重的 job、alarm、network 限流
- 后台启动前台服务时，如果不满足豁免条件，会抛 `ForegroundServiceStartNotAllowedException`
- exact alarm 进入 special app access 体系，targetSdk 31+ 需要先处理权限门禁

Android 13（API 33）继续调整 Restricted bucket 与后台资源策略。分桶条件和阈值属于系统实现，厂商也能采用自己的非 Active 分桶标准，应用不能把某个天数写成稳定契约。Doze allowlist 等豁免还会改变待机桶限制是否生效。

Android 14（API 34）要求 FGS **显式声明类型**。类型、专属权限和运行时前提开始做强校验。Android 15（API 35）又补了 `mediaProcessing` 类型，并给 `dataSync` / `mediaProcessing` 加上 6 小时预算和 `Service.onTimeout(...)` 超时回调。

Android 16（API 36）加入 `getPendingJobReasons()` 与 `getPendingJobReasonsHistory()`，并把 Active bucket、top-started job 和与 FGS 并行执行的 Job 纳入运行时配额。Android 17（API 37）增加 `getPendingJobReasonStats()`，用于按原因汇总累计等待时长；后台音频也新增生命周期与 WIU 约束。

## Doze 与 App Standby 机制的内部工作

Doze 和 App Standby 经常一起出现，但它们盯的对象不同。Doze 看设备整体状态，App Standby 看单个应用的活跃度。排查后台任务时，这两个维度要一起看。

### Deep Doze：把后台工作压缩到维护窗口

Deep Doze 在设备灭屏、静止、未充电一段时间后触发。进入这一状态后，系统会把大多数后台活动延后，只在维护窗口里集中放行一小段时间。

Doze 期间，常见限制包括：

- 常规网络访问暂停，维护窗口内才会放行
- 普通 `AlarmManager` 闹钟会推迟到维护窗口
- `JobScheduler`、`SyncAdapter` 等延迟型后台任务会被后移
- Wi-Fi 扫描等周期性动作会被压缩

`setAndAllowWhileIdle()` / `setExactAndAllowWhileIdle()` 仍然能在 Doze 中触发，但这类 while-idle alarm 也有单独的频率上限，不能作为无限制的后台入口。

### Light Doze：先限流，再进入更深 idle

Android 7.0 引入 Light Doze。设备只要灭屏，就可能先进入这一层。它比 Deep Doze 温和，但已经会把一部分 job、sync 和网络活动后移。很多“刚锁屏就不再秒回调”的现象，实际发生在 Light Doze 阶段，不必等到 Deep Doze。

### App Standby Buckets：桶常量在 UsageStatsManager，分桶逻辑在 AppStandbyController

App Standby Bucket 的常量定义在 `UsageStatsManager`，桶位管理由 `AppStandbyController` 负责；Doze / device idle 则由 `DeviceIdleController` 负责。在 `android-17.0.0_r1` 中，后两个服务都位于 JobScheduler APEX。

```java
// frameworks/base/core/java/android/app/usage/UsageStatsManager.java
public static final int STANDBY_BUCKET_ACTIVE = 10;
public static final int STANDBY_BUCKET_WORKING_SET = 20;
public static final int STANDBY_BUCKET_FREQUENT = 30;
public static final int STANDBY_BUCKET_RARE = 40;
public static final int STANDBY_BUCKET_RESTRICTED = 45;
public static final int STANDBY_BUCKET_NEVER = 50; // @hide
```

对应用开发者，常用的是五个公开桶：Active、Working Set、Frequent、Rare、Restricted。`NEVER` 是内部桶，表示安装后一次也未启动的应用。

当前官方 `power-details` 页面给出的资源上限如下，表里是 App state 与 device state 没有进一步调整限制时的基线值：

| Bucket | Regular jobs | Expedited jobs | Alarms | Network |
|------|------|------|------|------|
| Active | 60 分钟滚动窗口内最多 20 分钟 | 24 小时滚动窗口内最多 30 分钟 | 无额外执行上限 | 不限 |
| Working Set | 4 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 15 分钟 | 每小时最多 10 次 | 不限 |
| Frequent | 12 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 10 分钟 | 每小时最多 2 次 | 不限 |
| Rare | 24 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 10 分钟 | 每小时最多 1 次 | 禁用 |
| Restricted | 每天 1 次，最多 10 分钟 | 24 小时滚动窗口内最多 5 分钟 | 每天 1 次，只能是 exact 或 inexact alarm 之一 | 禁用 |

这些上限只适用于设备在电池供电、应用没有额外豁免时的基线。官方 App Standby 文档明确写到，Standby bucket 的限制只在 on battery 时生效；`power-details` 页面也给出了 charging、screen on、screen off + doze active 三种 device state 下的差异，其中 charging 基本不按桶限流，screen off + doze active 时 regular alarm、job 和 network 还会再叠加 Doze 的维护窗口约束。

开发者侧最常用的查询入口仍然是 `UsageStatsManager.getAppStandbyBucket()`。测试时可以用 `adb shell am get-standby-bucket <package>` 读取当前桶位，用 `adb shell am set-standby-bucket <package> <bucket>` 强制切桶。

### Bucket 是资源控制器的共同输入，不是单独的执行器

`AppStandbyController` 维护 bucket 与变更 reason，预测组件、用户交互和系统规则都可能更新它。随后 JobScheduler 的 `QuotaController`、AlarmManager、NetworkPolicyManagerService，以及 Battery Saver 相关的 `AppStateTrackerImpl` 各自消费应用状态。它们没有合并成一个“Adaptive Battery 调度器”：同一 bucket 对 job、alarm、network 的影响不同，还会叠加 charging、Doze、用户后台限制与豁免。

预测得到的 bucket 也有时效性。Android 17 AOSP 中，预测超过约 12 小时没有刷新后会失效并重新由系统规则评估；该超时不是“12 小时后应用必进 Rare”的产品契约。排查状态跳变时，应记录 bucket、reason、预测时间、设备状态以及各消费者自己的 dumpsys，而不是只看设置页中的 Adaptive Battery 开关。

### 观测方法：先看 dumpsys，再看 Battery Historian / Perfetto

排查后台任务时，不能假设 Trace 中一定存在 `device_idle` track。能否直接看到 Doze 状态切换，取决于 trace config、系统版本和厂商裁剪。

观测顺序如下：

- `adb shell dumpsys deviceidle`，确认当前是否进入 light / deep doze，以及 allowlist 状态
- `adb shell dumpsys usagestats appstandby` 或 `adb shell am get-standby-bucket <package>`，确认 bucket
- `adb shell dumpsys jobscheduler <package>`，确认 job 的 pending reason、quota 和实际约束
- bugreport / Battery Historian，观察灭屏后 alarm、job、network、wakelock 的时间分布
- Perfetto，在 trace config 已包含 framework / power / batterystats 相关数据源时，再去看 screen-off 期间的 CPU、wakeup、alarm/job slice 和网络活动

Perfetto 更适合回答“后台工作有没有把前台拖慢、有没有在灭屏后持续跑 CPU”，`dumpsys` 和 Battery Historian 更适合回答“系统为什么没让它现在执行”。

Battery Historian 已不再积极维护，适合读取已有 bugreport 的系统事件关联；新的性能采集和可重复实验应优先使用 Perfetto、Android Studio Power Profiler 与明确的 `dumpsys` 快照。

现成的等价证据可以直接用 `bugreport` 与 `dumpsys` 组合取得，不必等 Trace 里刚好有现成的 `device_idle` 轨道。

第一组证据看 Doze 状态切换。设备灭屏、静止、未充电后，`dumpsys deviceidle` 会从 active 进入 idle / idle maintenance。对应的 Battery Historian 时间线里，`screen` 熄灭后 `cpu_running` 会从连续活跃收缩成稀疏脉冲，`job`、`alarm`、`network` 条带集中出现在短暂窗口里；这和官方 Doze 文档描述的 maintenance window 行为一致。14.8《Battery Historian 与功耗分析工具》已经把 `cpu_running`、`wake_lock`、`job`、`alarm` 这些行的读法拆开讲过，可以直接拿来做对照。

第二组证据看后台任务被延后。把目标包切到 `Rare` 或 `Restricted` 桶后，先用 `dumpsys jobscheduler <package>` 看 pending reason、quota 和约束，再看 Battery Historian 的 `job` 行或 Perfetto 里的 CPU / network burst。正常现象是任务没有消失，而是执行时间被挪到配额允许或 Doze 维护窗口到来之后。11.4《功耗分析案例集》里的 AlarmManager 滥用案例能看到每 60 秒一次的 `alarm` 唤醒条带，JobScheduler 生命周期错误案例能看到 30 分钟 `WakeLock` 条带；两组样本的问题类型不同，但都提供了可复核的对照，可用于区分系统主动延后与任务异常持续运行。

如果 trace config 已打开 power、batterystats 和调度数据源，Perfetto 里可能看到进程 runnable slice 变少，以及维护窗口附近出现短促的 network / alarm burst。CPU 频率是否下降取决于同期系统负载，不能作为 Doze 的单独证据。缺少这些数据源时，不要根据空白轨道猜结论，应回到 `dumpsys` 与 bugreport。

## 前台服务：用户可感知工作的运行契约

当 App 需要在后台持续做用户可感知的事情，前台服务（Foreground Service，FGS）仍然是最直接的手段。代价也很明确，系统要求它对用户可见，并且越来越严格地校验“你为什么要开这个 FGS”。

FGS 是否能运行要依次通过五道门：调用时应用是否有后台启动资格，manifest 是否声明服务类型，类型专属权限是否齐全，camera/microphone/location 等 while-in-use 条件是否在调用时成立，以及服务是否在时限内调用 `startForeground()` 并持续满足通知与超时规则。异常发生在哪一阶段，决定应查 `ForegroundServiceStartNotAllowedException`、`SecurityException`、类型错误还是 promotion timeout。FGS 只改变生命周期与用户可见性，不承诺更高 CPU 优先级或固定频率。

### 前台服务类型体系

面向 API 34 及以上的应用必须声明合适的 FGS 类型。manifest 没声明类型，或者声明了类型却没补齐专属权限 / 运行时前提，`startForeground()` 就可能失败。

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

`camera`、`microphone`、`location` 这类还会叠加 while-in-use 权限限制。即使应用碰巧满足“允许从后台启动 FGS”的豁免条件，只要对应运行时权限只在前台可用，后台也照样起不来。

manifest 声明至少要把类型和权限写完整：

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

`shortService` 的规则来自 Android 14 的 FGS types 文档。它没有类型专属权限，但只能跑大约 3 分钟，超时从 `startForeground()` 开始计时。Android 14 文档明确要求实现 `Service.onTimeout()`：超时后系统会给应用几秒钟调用 `stopSelf()` / `stopForeground()`；如果服务还不退出，应用会收到带 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` 的 ANR。官方同时说明，这个回调在 Android 13 及以下不存在，所以兼容旧版本时不能把“等回调再停”当成前提。

对于 target API 35 及以上的应用，Android 15 给 `dataSync` 和 `mediaProcessing` 加了累计预算。两种类型分别按 24 小时窗口统计，同一类型所有 FGS 共用 6 小时额度，用户把应用带回前台后计时器重置。预算用完后，再启动同类型 FGS 会直接失败；Android 15 行为变更页给出的报错示例是 `Time limit already exhausted for foreground service type dataSync`。

这一组超时回调以 Android Developers 的 `Service` API reference 和 Android 15 behavior changes 页为准。当前 reference 同时列出 `onTimeout(int startId)` 和 `onTimeout(int startId, int fgsType)` 两个重载：前者对应 `shortService`，后者对应 Android 15 新增的类型化超时。`dataSync` / `mediaProcessing` 收到 `Service.onTimeout(int, int)` 后如果几秒内还不 `stopSelf()`，Logcat 会记录 `RemoteServiceException`；`shortService` 超时不退出则会走 ANR。

### Android 17 的后台音频硬化

API 37 对后台音频操作施加了更严格的约束。运行在 Android 17 的所有 App，只要在后台发起播放、请求音频焦点或改音量，都需要可见 Activity，或运行一个不是 `shortService` 类型的 FGS；如果 targetSdk 是 37，还要满足 FGS 具备 While-In-Use（WIU）能力。`BOOT_COMPLETED` 这类后台触发器拉起的 `mediaPlayback` FGS，如果没有用户触发形成的 WIU 能力，调用 `AudioManager.requestAudioFocus()` 会返回 `AUDIOFOCUS_REQUEST_FAILED`，播放和音量 API 可能静默失败。

例外要单独看：targetSdk 37 的应用如果已获得 exact alarm 权限，并且操作的是 `USAGE_ALARM` 音频流，官方文档明确豁免 WIU 要求。普通媒体播放、播客和直播类后台播放，仍应在用户发起播放时启动 `mediaPlayback` FGS，并在播放结束或永久失去音频焦点时停止 FGS。

## WorkManager vs JobScheduler vs AlarmManager：选型指南

这三个 API 都能用于后台任务，但职责边界差异很大。工具与业务语义不匹配时，任务延迟或受限只是后续表现。

### WorkManager：默认选择

WorkManager 适合“可以延迟，但希望最终能执行”的任务。它会按系统版本自动落到底层实现，在 API 23+ 上通常还是走 JobScheduler，所以 Doze、App Standby bucket 和 quota 依然会生效。

它的优势在于：

- 用 `Constraints` 表达网络、充电、空闲等条件
- 持久化到数据库，进程被杀后还能恢复
- 支持链式依赖和周期任务
- 默认帮你做批处理，减少碎片化唤醒

如果任务要尽快开始，又不该拉一个长期 FGS，WorkManager 2.7+ 的 `setExpedited()` 是更合适的入口。官方文档把 expedited work 定义成“重要、用户在意、几分钟内完成、希望立刻开始”的短任务。它仍然受 quota 控制，但比普通 work 更不容易被 Doze 或 Battery Saver 拖得太久。

long-running worker 也不是无限执行通道。WorkManager 即使为它启动 FGS，底层工作仍由 JobScheduler 调度；Android 16 起，这类工作可能耗尽应用的 Job runtime quota。用户主动发起的大数据上传或下载，应评估 user-initiated data transfer job。

### JobScheduler：系统原生调度层

JobScheduler 是系统原生调度 API。和 WorkManager 相比，它需要你自己处理更多细节，但也能直接用到一些 WorkManager 还没完全封装的能力，比如 `setPrefetch()`、`setUserInitiated(true)`，以及不同版本逐步加入的 pending reason 调试接口。

API 版本边界如下：

- API 34：`getPendingJobReason(int jobId)` 返回当前一个主因。存在多个原因时，它不会全部返回。
- API 36：`getPendingJobReasons(int jobId)` 返回当前可能原因的 `int[]`；`getPendingJobReasonsHistory(int jobId)` 返回有限的 `List<PendingJobReasonsInfo>` 历史视图。
- API 37：`getPendingJobReasonStats(int jobId)` 返回 `Map<Integer, Duration>`，按原因汇总任务生命周期内的累计等待时长。

history 适合观察约束变化顺序，stats 适合判断哪类约束累计影响最大。多个约束可以同时存在，所以 stats 中各项时长之和可能大于总等待时长；统计在重启后不保留，任务完成或取消时也会清除。

这些 API 可以在 `android-17.0.0_r1` 的 `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java` 复核。

对性能排查，`getPendingJobReasonsHistory()` 的价值在于把“最近一段时间为什么一直没跑”变成可读数据；`getPendingJobReasonStats()` 则适合看一段时间内是哪类约束反复压住 Job。

### AlarmManager：只留给需要精确时刻的事情

AlarmManager 的强项是精确时间点触发，代价是最难和系统的省电批处理和平共处。只要你开始频繁调 `setExact()` / `setExactAndAllowWhileIdle()`，就等于主动放弃系统帮你合并唤醒窗口的机会。

从 Android 12（targetSdk 31）开始，如果要用 exact alarm 的 PendingIntent 路径，应用必须先声明并处理 exact alarm special access。targetSdk 33+ 可以根据场景选择 `SCHEDULE_EXACT_ALARM` 或 `USE_EXACT_ALARM`。代码里要先用 `AlarmManager.canScheduleExactAlarms()` 做门禁；未获授权时继续调 exact API，会命中 `SecurityException`，系统不会替你偷偷改成非精确闹钟。

API 37 新增接收 `OnAlarmListener` 与 `Executor` 的 `setExactAndAllowWhileIdle()` 重载。它适合调用进程会持续存活的短期回调；组件结束或进程不再有活动组件时，系统可以取消 listener alarm。需要跨越进程生命周期交付时，仍应使用 `PendingIntent` 路径。这个重载也不会取消 allow-while-idle 的频率限制。

处理方式通常有三种：

- 引导用户去 `ACTION_REQUEST_SCHEDULE_EXACT_ALARM` 对应的设置页授权
- 退回 inexact alarm
- 如果任务本来就不要求秒级，直接改成 WorkManager / JobScheduler

### 例外与豁免：为什么“已经受限”的任务有时还是能跑

后台限制不是只有一条主路，系统留了几类明确的例外：

- **Expedited work / expedited jobs**：短、急、用户在意的任务可以请求更快执行，但受 quota 控制
- **User-initiated data transfer job（UIDT）**：Android 官方给“用户明确点了上传 / 下载”这种数据传输任务的专用入口，走 JobScheduler 的 `setUserInitiated(true)`，并要求进度通知
- **Temporary allowlist**：Android 8.0 文档明确写了，高优先级 FCM、SMS / MMS 广播、通知 `PendingIntent`、VPN 启动等场景，应用会被临时放进 allowlist 几分钟，这段时间可以启动 service 并继续跑后台逻辑
- **Android 12+ 的后台启动 FGS 豁免**：高优先级 FCM、用户可见交互、exact alarm 等场景仍可能允许起 FGS，但如果 FCM 最终被系统降级，`startForegroundService()` 依旧会因为 `ForegroundServiceStartNotAllowedException` 失败

因此，看到“受限状态下任务还是执行了”，先核对它是不是走了这些例外入口。

### 选型决策

可以按这条路径判断：

1. 必须在精确时刻触发，并且这是用户明确期待的提醒或闹钟，选 AlarmManager
2. 任务很短，用户刚刚触发，而且希望马上开始，先看 expedited WorkManager
3. 任务是用户亲手发起的长时间上传 / 下载，优先看 UIDT job
4. 任务可以延迟，但希望条件满足后最终执行，默认选 WorkManager
5. 需要 JobScheduler 的底层能力或细粒度调试接口，再直接用 JobScheduler
6. 任务需要持续运行且必须让用户清楚知道它在干什么，才用 FGS

以上是任务调度层面的限制。系统还会单独管理缓存进程：App 退到 cached 状态后，`CachedAppOptimizer` 决定何时暂停其执行。这条控制线与 Doze、Standby bucket 并行。

## CachedAppOptimizer 与 Binder：缓存进程冻结是另一条控制线

Doze、待机桶和 Job 配额决定后台工作何时获得执行机会；cached apps freezer 处理已经进入 cached 进程状态的进程能否继续占用 CPU。两者可能同时影响同一个应用，但触发条件和证据不同。

Android 11 起支持 cached apps freezer。Android 14 及以上的官方行为是：在支持并启用该功能的设备上，应用进程进入 cached 状态 10 秒后被冻结；收到 Intent、启动 JobService、恢复 Activity 等生命周期事件时，系统立即解冻。设备可以通过配置关闭 freezer，文件锁或特定绑定关系也可能让 cached 进程暂不冻结，所以“cached 已满 10 秒”仍不能单独证明进程处于 frozen。

冻结后，该进程的所有线程暂停，不能执行 CPU 工作、GC 或内存 trim 回调。Android 14 还配套处理了几件事：

- 进入 cached 后，系统可能先请求 runtime 做一次 GC，为后续冻结准备；
- 冻结后可能触发额外内存 compaction，例如把脏页写回 backing storage、把匿名页换出到 ZRAM；
- context-registered broadcast 可以排队到进程解冻后再交付，manifest receiver 的广播会把进程提升出 cached 状态；
- 如果某个应用的所有进程都被冻结，系统会终止该应用仍保持的 TCP socket，避免 keepalive 继续唤醒 modem。

这些动作都带有“可能”或设备支持条件。不能由一次 freeze 推导必然发生 GC、compaction、ZRAM 写入，也不能用 4 KB/16 KB 页大小推导固定的回收收益。

### framework 的两阶段冻结

Android 17 的 `CachedAppOptimizer` 先冻结 Binder 接口，再把进程迁入 frozen cgroup：

```text
Freezer.freezeBinder(pid, true, timeout = 0)
    ↓ 检查是否有未排空或新到达的事务
Freezer.setProcessFrozen(pid, uid, true)
    ↓ BINDER_GET_FROZEN_INFO 再检查竞态
记录 frozen 状态，并执行冻结后的可选处理
```

顺序很重要。先阻止新的同步 Binder 事务，再暂停全部线程，可以降低调用方等待一个已经不能处理事务的进程所产生的死锁风险。两步并非原子操作，所以 framework 在 cgroup freeze 之后还会读取 Binder freezer 状态；发现冻结窗口中出现新的 pending transaction 时，会取消本次冻结或执行失败处理。

Android 17 的相关源码入口是：

- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`
- `frameworks/base/services/core/java/com/android/server/am/Freezer.java`
- `system/core/libprocessgroup/profiles/cgroups.json`
- `kernel/common/include/uapi/linux/android/binder.h`
- `kernel/common/drivers/android/binder.c`

### Binder 返回值的准确含义

在 `android17-6.18-2026-06_r6` 中，冻结相关 UAPI 包含 `BINDER_FREEZE`、`BINDER_GET_FROZEN_INFO` 以及三个容易混淆的 driver return：

| 返回项 | 接收方看到的含义 |
|---|---|
| `BR_FROZEN_REPLY` | 调用方发出的同步事务因目标进程 frozen 而被拒绝 |
| `BR_TRANSACTION_PENDING_FROZEN` | 调用方发出的异步事务已排队，等待目标解冻 |
| `BR_FROZEN_BINDER` | 已注册冻结通知的一方收到远端 Binder 宿主 frozen/unfrozen 状态变化 |

`BR_FROZEN_REPLY` 不是 `BINDER_FREEZE` ioctl 的“冻结成功确认”。同步事务到达 frozen 目标时，驱动把失败返回给调用方；异步事务可以留在目标队列中。`CachedAppOptimizer` 通过 `BINDER_GET_FROZEN_INFO` 发现进程在 frozen 期间收到同步事务后，可能按 framework 策略终止该 cached 进程。这个终止决定不应写成“Binder 驱动直接杀目标进程”。

`binder_frozen_status_info.sync_recv` 的 bit 0 表示进程被冻结后收到同步事务，bit 1 表示冻结步骤中出现新的 pending 同步事务；`async_recv` 记录冻结后是否收到异步事务。排查时要结合 framework 的 freeze/unfreeze 日志和调用方错误，不能只看一个 bit 猜完整时序。

### API 36 的冻结通知与回调队列策略

API 36 公开 `IBinder.addFrozenStateChangeCallback(Executor, FrozenStateChangeCallback)`。它只观察远端 Binder 宿主进程的 frozen/unfrozen 状态，不控制进程冻结。内核不支持冻结通知时会抛出 `UnsupportedOperationException`；监听者自己也被冻结或事件到达过快时，状态通知还可能合并，因此不能用回调次数统计 freeze 次数。

下面的回调用于暂停向 frozen 远端发送非必要事务：

```java
binder.addFrozenStateChangeCallback(executor, (who, state) -> {
    if (state == IBinder.FrozenStateChangeCallback.STATE_FROZEN) {
        pauseNonEssentialCallbacks(who);
    } else {
        resumeCallbacks(who);
    }
});
```

回调必须配合 `removeFrozenStateChangeCallback()` 管理注册生命周期。远端为本地 Binder 时不会出现独立的冻结状态，因为宿主和监听者处于同一进程。

API 36 的 `RemoteCallbackList.Builder` 进一步提供 frozen callee policy：

- `FROZEN_CALLEE_POLICY_DROP`：冻结期间不保留回调；
- `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT`：只保留最新状态，解冻后交付；
- `FROZEN_CALLEE_POLICY_ENQUEUE_ALL`：保留事件序列，并受最大队列长度约束；
- `FROZEN_CALLEE_POLICY_UNSET`：保持 API 35 及以前的立即调用行为，仅用于兼容，不推荐新代码采用。

状态同步通常选 `ENQUEUE_MOST_RECENT`，可重建的提示事件可以选 `DROP`；只有业务必须保留完整事件历史时才选 `ENQUEUE_ALL`，并设置有限队列。这样能避免 frozen 进程解冻后一次接收大量陈旧回调。

## 后台执行对前台性能的影响

性能分析里，很多时候只盯前台 App 的渲染和响应，却漏掉了后台行为带来的间接代价。不合理的后台工作，经常和前台卡顿、发热、续航变短一起出现。

### CPU 争抢

最直接的影响是 CPU 资源争抢。当前台 App 正在做 layout 或 draw 操作时，后台进程的网络请求、数据同步、图片解码等工作会同时竞争 CPU 时间。在大小核架构（5.3 节）下，后台任务如果长期占用前台关键线程需要的 CPU，还可能增加 RenderThread 的 runnable delay。

Perfetto 中看到后台线程与 RenderThread 同时活跃，只能说明存在并发负载。要证明抢占关系，还要对齐掉帧区间，检查 RenderThread 的 wakeup、runnable、Running 切换，以及同一 CPU 上的 `sched_switch` 前驱线程。后台线程刚好出现在同一核上，不足以单独归因。

### 内存压力

后台进程消耗的内存会增加系统整体内存压力。压力升高后，内核可能执行 direct reclaim、kswapd 回收和 swap I/O，lmkd 也可能按 PSI 与进程优先级选择牺牲进程。分析前台卡顿时，应对齐 `mm_vmscan`、PSI、I/O、lmkd 事件与应用分配/GC slice；不能只看到后台 PSS 较大就认定它造成某次 GC 停顿。

### 热节流

持续的后台计算、媒体处理与无线传输会增加整机功耗，进而缩小前台工作负载可用的 thermal headroom。达到设备热策略阈值后，thermal、Power HAL 或频率上限可能共同压低 CPU/GPU 能力。

排查时应同时观察后台负载开始时间、thermal status/温区、CPU/GPU 频率上限、冷却设备状态和帧耗时。频率下降也可能来自低利用率或省电策略；温度上升与掉帧同时发生仍需通过控制变量实验确认因果。

## 与其他机制的关系

**与 CPU 调度（5.1）的关系**：Standby bucket 主要控制的是 job、alarm、network 这类后台资源额度，不是直接给线程改一个固定的 CPU 优先级。它对调度的影响更多是间接的，后台任务被延后了，可运行线程自然变少，前台争抢压力也会下降。线程一旦真的进入 runnable，最终怎么分配 CPU，还要看进程状态、cgroup / uclamp、线程策略和具体子系统规则。

**与 EAS（5.2）的关系**：碎片化后台任务会制造更多唤醒和短 runnable 区间，可能增加核选择、迁移和频率响应成本。是否发生迁移仍要看 CPU affinity、cpuset、利用率与设备 Energy Model。

**与 DVFS（5.4）的关系**：后台工作提高调度利用率后，CPUFreq governor 可能请求更高频率。Doze 和 bucket 限流减少了不必要的 runnable 负载，也给系统合并唤醒、延长 idle 时间创造条件。

**与 Thermal（5.5）的关系**：后台同步、转码、上传这类持续工作，最容易把 SoC 温度慢慢推高。温度一旦过阈值，Thermal 降频打到的是整个前台体验，不会只处罚后台线程。

**与 Android 功耗管理（5.6）的关系**：5.6 节偏底层，讲 WakeLock、PowerManagerService、device idle。这里更偏框架和 API 选择，讲的是应用层后台任务最终会被哪些规则拦下来。

**与响应速度（8.4）的关系**：BAL 的限制从 Android 10 开始变严，后续版本还在继续增加约束。后台能不能拉起 Activity，取决于用户可见性、通知 / `PendingIntent` / `IntentSender` 路径和系统豁免条件，不能再按老版本经验硬推。

## 版本演进

| 版本 | 核心变化 | 性能分析影响 |
|------|----------|-------------|
| Android 6.0 (API 23) | 引入 Doze 和 App Standby | 灭屏后后台任务开始系统级延后 |
| Android 7.0 (API 24) | 引入 Light Doze | 刚灭屏就可能开始限流 |
| Android 8.0 (API 26) | 对 target API 26+ 限制后台 Service 与 manifest 隐式广播 | 需要结合宽限期、临时允许名单与广播种类判断 |
| Android 9.0 (API 28) | 引入 App Standby Buckets | Job、alarm、network 开始按桶分级限流 |
| Android 10 (API 29) | 增加 BAL 限制 | 后台弹 Activity 的路径明显变少 |
| Android 12 (API 31) | Restricted bucket、后台启动 FGS 限制、exact alarm special access | 后台任务调度和 FGS 启动都要先过门禁 |
| Android 13 (API 33) | Restricted bucket 与后台资源规则继续调整 | 分桶阈值不是应用可依赖的公开契约 |
| Android 14 (API 34) | FGS 类型强制声明，新增 `remoteMessaging`、`shortService`、`systemExempted` 等类型；cached app 进入 cached 约 10 秒后冻结，并引入冻结前 GC 请求 + 冻结后 compaction | FGS 类型、权限和运行时前提都要写完整 |
| Android 15 (API 35) | `mediaProcessing` 类型加入，`dataSync` / `mediaProcessing` 引入 6 小时预算 | 长时间同步和媒体加工要处理超时回调 |
| Android 16 (API 36) | 多原因/history API、Job runtime quota 扩围；Binder 增加 frozen callback | 可定位多重 Job 约束，并按远端 frozen 状态处理回调 |
| Android 17 (API 37) | `getPendingJobReasonStats()`；后台音频要求可见 Activity 或非 short FGS，target 37 后台 FGS 还需 WIU 或满足 alarm 豁免 | Job 原因可聚合分析，后台音频要核对完整生命周期条件 |

## 常见问题与误区

### 误区 1："WorkManager 保证任务在指定时间执行"

WorkManager 不保证精确时间。它定义约束条件，系统在条件满足后的合适时机执行。只有闹钟、日历提醒等用户明确要求准确时刻的功能，才应在处理 exact alarm 权限后使用 AlarmManager；普通定时同步应接受非精确触发或改用 WorkManager / JobScheduler。

### 误区 2："前台服务不会被系统杀掉"

前台服务的进程优先级很高，但不是不可杀。内存极度紧张时系统仍然可能杀掉前台服务进程。另外，从 Android 15 开始，`dataSync` 和 `mediaProcessing` 类型有 6 小时的超时限制。

### 误区 3："我的 JobScheduler 不执行一定是系统 bug"

常见原因包括 bucket、quota、任务约束和设备状态。先用 `adb shell am get-standby-bucket <package>` 看桶位，再用 `adb shell dumpsys jobscheduler <package>` 看具体约束。API 34 可查单个 `getPendingJobReason()`，API 36 可查多原因和 history，API 37 可查累计 stats。

### 误区 4："Doze 只在晚上才生效"

Doze 的触发条件是灭屏 + 静止 + 未充电，与时间无关。白天如果手机放在桌上灭屏不动，一样会进入 Doze。

### 误区 5："后台限制只影响后台 App"

后台规则直接控制的是后台机会，但后台工作造成的 CPU 争抢、内存压力和热节流会拖慢前台 App。减少无效后台工作也属于前台性能优化的一部分。

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
