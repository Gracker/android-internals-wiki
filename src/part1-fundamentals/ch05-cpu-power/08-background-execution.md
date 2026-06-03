---


status: "ready-for-review"
title: 后台执行限制与优化
chapter: '5.8'
section: '5.8'
applicable_versions: Android 6.0 (API 23) - Android 17 (API 37)
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
last_verified: '2026-06-04'
last_verified_against: AOSP android-16.0.0_r1 + Android Developers Android 17 docs + JobScheduler API reference
confidence: high
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
- '5.7'
- '11.2'
- '8.4'
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
task6_reviewed_date: 2026-05-18
task6_reviewed_by: openclaw-task6
task9_reviewed_date: "2026-06-04"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-04T06:48:42+08:00"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: 2026-06-04T02:57:11+08:00
task9_state: reviewed
task9_result: auto-fixed
last_task9_review_log: "logs/deep-review/2026-06-04-06-deep-review.md"
queue_entry: task9-20260518-5.8-freezer-gc-version-boundary
task9_review_notes: "2026-06-04 task9 deep-review: auto-fixed。修正 Android 16 Binder freezer 源码行号，补 Android 17 JobScheduler reason stats 版本边界。"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-04"
last_task6_at: "2026-06-04T04:12:07+08:00"
last_task6_review_log: "logs/review/2026-05-18-02-review.md"
last_task9_autofix_at: "2026-06-04"
---



# 5.8 后台执行限制与优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 后台限制的演进：Doze、App Standby、后台服务限制与 FGS 类型化
- 🔹 Doze 与 App Standby Buckets 的工作方式，以及在 Perfetto / dumpsys 中怎么观察
- 🔹 前台服务的定位、类型声明和超时约束
- 🔹 WorkManager、JobScheduler、AlarmManager 的适用边界
- 🔹 后台执行对前台性能的影响：CPU、内存与热节流
- 🔹 与 CPU 调度、DVFS、Thermal、响应速度章节的关系
- 🔹 版本演进与常见误区

### 扩展（可选深入）

- 🔸 Standby Bucket、Job 配额与网络策略的内部实现
- 🔸 Android 16 的后台任务调试接口与版本边界

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或官方文档中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解后台执行限制

当我们在 Perfetto 里看到灭屏后某个进程还在持续跑 CPU，或者在 Battery Historian 里看到后台 alarm、job、network 活动一直冒出来，排查往往会卡在同一个问题上：这是应用代码没收住，还是系统已经开始限流了。

Android 的后台限制是一套逐步收紧的制度。Android 6.0 引入 Doze 和 App Standby，Android 8.0 开始限制后台 service，Android 9 把 App Standby 细化成 Buckets，Android 12 加入 Restricted bucket 并限制后台启动 FGS，Android 14 和 15 又把 FGS 类型、权限和超时写成了更明确的运行时规则，Android 16 补上了 JobScheduler 的待执行原因观测接口。

理解这套机制，主要是为了解决两类问题。第一，后台任务没按预期执行时，先判断它是被系统延后了，还是代码本身有 bug。第二，真有后台需求时，选对 API，别拿前台服务、精确闹钟或者轮询把系统拖热。

本章前面讨论了 CPU 调度（5.1）、EAS（5.2）、大小核（5.3）、DVFS（5.4）、Thermal（5.5）和 Android 功耗管理框架（5.6）。那些章节回答的是硬件怎么分配资源，这一节回答的是框架什么时候允许 App 在后台继续消耗这些资源。

## Android 后台限制的演进：从“能跑就行”到“按规则跑”

### Android 6.0 之前：后台几乎没有总闸门

在 Android 6.0（Marshmallow）之前，App 在后台几乎没有统一的系统级约束。一个 App 只要拿到 `WAKE_LOCK`，再配一个长期存活的 service，就能在灭屏后继续占着 CPU、拉网络、做同步。那时很多厂商做“自启动管理”“后台白名单”，是在给 AOSP 补一层额外管控。

### Android 6.0-7.1：Doze、App Standby 与 Light Doze

Android 6.0 同时引入了 **Doze** 和 **App Standby**。Doze 盯的是设备状态，满足灭屏、静止、未充电等条件后，把大量后台活动推迟到维护窗口；App Standby 盯的是单个 App 的使用情况，长时间没被用户碰过的 App 会受到更严的后台限制。

Android 7.0（API 24）又加了 **Light Doze**。设备只要灭屏，就会先进入更温和的 idle 流程，不必等到“长时间静止”才开始限流。它没有 Deep Doze 那么狠，但已经会推迟一部分后台工作。

### Android 8.0：后台 service 被系统限制

Android 8.0（API 26，Oreo）是后台执行模型的分水岭。后台 App 再直接调 `startService()`，系统会抛 `IllegalStateException`。如果必须在后台拉起持续工作，就要改成 `startForegroundService()`，并在很短时间内调用 `startForeground()` 把通知挂出来。

同一轮变更里，隐式广播也被大幅收紧。很多靠 manifest 常驻 receiver 拉起后台逻辑的旧做法，从这一代开始就走不通了。

### Android 9-10：Buckets 与 BAL

Android 9（API 28）把 App Standby 进一步细化为 **App Standby Buckets**，从按“常用/不常用”粗分，变成 Active、Working Set、Frequent、Rare 四档主桶。Android 12 以后又补上 Restricted 桶。

Android 10（API 29）开始限制 **Background Activity Launch（BAL）**。后台弹 Activity 不再是想弹就弹，很多“锁屏后突然跳广告页”的路径从系统层就被卡掉了。

### Android 12-16：Restricted bucket、FGS 类型和调试接口

Android 12（API 31）把后台限制又拧紧了一圈：

- 加入 **Restricted bucket**，给高耗电或长时间不使用的 App 更重的 job、alarm、network 限流
- 后台启动前台服务时，如果不满足豁免条件，会抛 `ForegroundServiceStartNotAllowedException`
- exact alarm 进入 special app access 体系，targetSdk 31+ 需要先处理权限门禁

Android 13（API 33）把“长期未交互后更容易进入 Restricted bucket”的阈值，从 Android 12 / 12L 的 45 天收紧到 8 天。官方 App Standby 文档同时说明，满足 exemption 的应用不走这条自动降桶路径。

Android 14（API 34）要求 FGS **显式声明类型**。类型、专属权限和运行时前提开始做强校验。Android 15（API 35）又补了 `mediaProcessing` 类型，并给 `dataSync` / `mediaProcessing` 加上 6 小时预算和 `Service.onTimeout(...)` 超时回调。

Android 16（API 36）没有推翻这套模型，但把 JobScheduler 的可观测性补得更像样了，开发者可以直接看 pending reason 和 pending reason history，不必只靠 `dumpsys jobscheduler` 猜原因。

[图：Android 后台限制演进时间线，从 6.0 到 16，标注 Doze、App Standby Buckets、Restricted bucket、FGS 类型与 JobScheduler 调试接口]

## Doze 与 App Standby 机制的内部工作

Doze 和 App Standby 经常一起出现，但它们盯的对象不同。Doze 看设备整体状态，App Standby 看单个应用的活跃度。排查后台任务时，这两个维度要一起看。

### Deep Doze：把后台工作压缩到维护窗口

Deep Doze 在设备灭屏、静止、未充电一段时间后触发。进入这一状态后，系统会把大多数后台活动延后，只在维护窗口里集中放行一小段时间。

Doze 期间，常见限制包括：

- 常规网络访问暂停，维护窗口内才会放行
- 普通 `AlarmManager` 闹钟会推迟到维护窗口
- `JobScheduler`、`SyncAdapter` 等延迟型后台任务会被后移
- Wi-Fi 扫描等周期性动作会被压缩

`setAndAllowWhileIdle()` / `setExactAndAllowWhileIdle()` 仍然能在 Doze 中触发，但这类 while-idle alarm 也有单独的频率上限，不能当成无限制的后门。

### Light Doze：先限流，再进入更深 idle

Android 7.0 引入 Light Doze。设备只要灭屏，就可能先进入这一层。它比 Deep Doze 温和，但已经会把一部分 job、sync 和网络活动后移。很多“刚锁屏就不再秒回调”的现象，实际发生在 Light Doze 阶段，不必等到 Deep Doze。

### App Standby Buckets：桶常量在 UsageStatsManager，分桶逻辑在 AppStandbyController

App Standby Bucket 的常量定义在 UsageStatsManager，不是 DeviceIdleController。在 android-16.0.0_r1 中，App 的桶位管理由 AppStandbyController 负责，Doze / device idle 才由 DeviceIdleController 负责。

```java
// frameworks/base/core/java/android/app/usage/UsageStatsManager.java
public static final int STANDBY_BUCKET_ACTIVE = 10;
public static final int STANDBY_BUCKET_WORKING_SET = 20;
public static final int STANDBY_BUCKET_FREQUENT = 30;
public static final int STANDBY_BUCKET_RARE = 40;
public static final int STANDBY_BUCKET_RESTRICTED = 45;
public static final int STANDBY_BUCKET_NEVER = 50; // @hide
```

对应用开发者，常用的是五个公开桶：Active、Working Set、Frequent、Rare、Restricted。`NEVER` 是内部桶，表示安装后从未真正使用过的应用。

当前官方 `power-details` 页面给出的资源上限如下，表里是“App state 与 device state 没有进一步放宽或收紧”时的基线值：

| Bucket | Regular jobs | Expedited jobs | Alarms | Network |
|------|------|------|------|------|
| Active | 60 分钟滚动窗口内最多 20 分钟 | 24 小时滚动窗口内最多 30 分钟 | 无额外执行上限 | 不限 |
| Working Set | 4 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 15 分钟 | 每小时最多 10 次 | 不限 |
| Frequent | 12 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 10 分钟 | 每小时最多 2 次 | 不限 |
| Rare | 24 小时滚动窗口内最多 10 分钟 | 24 小时滚动窗口内最多 10 分钟 | 每小时最多 1 次 | 禁用 |
| Restricted | 每天 1 次，最多 10 分钟 | 24 小时滚动窗口内最多 5 分钟 | 每天 1 次，只能是 exact 或 inexact alarm 之一 | 禁用 |

这些上限只适用于设备在电池供电、应用没有额外豁免时的基线。官方 App Standby 文档明确写到，Standby bucket 的限制只在 on battery 时生效；`power-details` 页面也给出了 charging、screen on、screen off + doze active 三种 device state 下的差异，其中 charging 基本不按桶限流，screen off + doze active 时 regular alarm、job 和 network 还会再叠加 Doze 的维护窗口约束。

开发者侧最常用的查询入口仍然是 `UsageStatsManager.getAppStandbyBucket()`。测试时可以用 `adb shell am get-standby-bucket <package>` 读取当前桶位，用 `adb shell am set-standby-bucket <package> <bucket>` 强制切桶。

### 观测方法：先看 dumpsys，再看 Battery Historian / Perfetto

排查后台任务时，别先假设 Trace 里一定有现成的 `device_idle` track。是否能直接看到 Doze 状态切换，取决于 trace config、系统版本和厂商裁剪。

建议把观测顺序固定下来：

- `adb shell dumpsys deviceidle`，确认当前是否进入 light / deep doze，以及 allowlist 状态
- `adb shell dumpsys usagestats appstandby` 或 `adb shell am get-standby-bucket <package>`，确认 bucket
- `adb shell dumpsys jobscheduler <package>`，确认 job 的 pending reason、quota 和实际约束
- Battery Historian，观察灭屏后 alarm、job、network、wakelock 的时间分布
- Perfetto，在 trace config 已包含 framework / power / batterystats 相关数据源时，再去看 screen-off 期间的 CPU、wakeup、alarm/job slice 和网络活动

Perfetto 更适合回答“后台工作有没有把前台拖慢、有没有在灭屏后持续跑 CPU”，`dumpsys` 和 Battery Historian 更适合回答“系统为什么没让它现在执行”。

现成的等价证据可以直接从 `bugreport` + `dumpsys` 组合里拿到，不必等 Trace 里刚好有现成的 `device_idle` 轨道。

第一组证据看 Doze 状态切换。设备灭屏、静止、未充电后，`dumpsys deviceidle` 会从 active 进入 idle / idle maintenance。对应的 Battery Historian 时间线里，`screen` 熄灭后 `cpu_running` 会从连续活跃收缩成稀疏脉冲，`job`、`alarm`、`network` 条带集中出现在短暂窗口里；这和官方 Doze 文档描述的 maintenance window 行为一致。14.11《Battery Historian 与功耗分析工具》已经把 `cpu_running`、`wake_lock`、`job`、`alarm` 这些行的读法拆开讲过，可以直接拿来做对照。

第二组证据看后台任务被延后。把目标包切到 `Rare` 或 `Restricted` 桶后，先用 `dumpsys jobscheduler <package>` 看 pending reason、quota 和约束，再看 Battery Historian 的 `job` 行或 Perfetto 里的 CPU / network burst。正常现象是任务没有消失，而是执行时间被挪到配额允许或 Doze 维护窗口到来之后。11.4《功耗分析案例集》里的 AlarmManager 滥用案例能看到每 60 秒一次的 `alarm` 唤醒条带，JobScheduler 生命周期错误案例能看到 30 分钟 `WakeLock` 条带；两组样本虽然问题类型不同，但都给了我们一个可复核的对照基线，方便把“系统主动延后”和“任务自己跑飞”区分开来。

如果 trace config 已打开 power、batterystats 和调度数据源，Perfetto 里通常还能看到同一时间段的 CPU frequency 下降、进程 runnable slice 稀疏化，以及维护窗口内短促的 network / alarm burst。没有这些数据源时，不要硬从空白轨道猜结论，回到 `dumpsys` + Battery Historian 更稳。

[图：Doze 等价证据对照图。左侧是 `dumpsys deviceidle` 的 idle / idle maintenance 状态切换，右侧是 Battery Historian 中 `cpu_running`、`job`、`alarm` 条带只在短窗口出现。]

[图：后台任务延后对照图。上方是 `dumpsys jobscheduler <package>` 的 pending reason / quota 信息，下方是 Battery Historian 或 Perfetto 中任务实际开始执行的延后时间点。]

## 前台服务：后台工作的“合法通行证”

当 App 需要在后台持续做用户可感知的事情，前台服务（Foreground Service，FGS）仍然是最直接的手段。代价也很明确，系统要求它对用户可见，并且越来越严格地校验“你为什么要开这个 FGS”。

### 前台服务类型体系

Android 14 起，FGS 类型是运行时约束。manifest 没声明类型，或者声明了类型却没补齐专属权限 / 运行时前提，startForeground() 就可能失败。

| 类型 | 专属权限 | 首个要求版本 | 典型场景 |
|------|------|------|------|
| `camera` | `FOREGROUND_SERVICE_CAMERA` | Android 14 | 后台拍摄、视频通话 |
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

### 超时机制：`shortService` 看单次时长，`dataSync` / `mediaProcessing` 看 24 小时预算

`shortService` 的规则来自 Android 14 的 FGS types 文档。它没有类型专属权限，但只能跑大约 3 分钟，超时从 `startForeground()` 开始计时。Android 14 文档明确要求实现 `Service.onTimeout()`：超时后系统会给应用几秒钟调用 `stopSelf()` / `stopForeground()`；如果服务还不退出，应用会收到带 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` 的 ANR。官方同时说明，这个回调在 Android 13 及以下不存在，所以兼容旧版本时不能把“等回调再停”当成前提。

Android 15 又给 `dataSync` 和 `mediaProcessing` 加了累计预算。两种类型分别按 24 小时窗口统计，同一类型所有 FGS 共用 6 小时额度，用户把应用带回前台后计时器重置。预算用完后，再启动同类型 FGS 会直接失败；Android 15 行为变更页给出的报错示例是 `Time limit already exhausted for foreground service type dataSync`。

这一组超时回调以 Android Developers 的 `Service` API reference 和 Android 15 behavior changes 页为准。当前 reference 同时列出 `onTimeout(int startId)` 和 `onTimeout(int startId, int fgsType)` 两个重载：前者对应 `shortService`，后者对应 Android 15 新增的类型化超时。`dataSync` / `mediaProcessing` 收到 `Service.onTimeout(int, int)` 后如果几秒内还不 `stopSelf()`，Logcat 会记录 `RemoteServiceException`；`shortService` 超时不退出则会走 ANR。

### Android 17 的后台音频硬化

API 37 对后台音频操作施加了更严格的约束。由后台触发器（如 BOOT_COMPLETED、CONNECTIVITY_ACTION）拉起的 FGS，即使声明了 mediaPlayback 类型，也无法获取音频焦点。AudioManager.requestAudioFocus() 在这类场景下返回 AUDIOFOCUS_REQUEST_FAILED，不会抛异常，但播放会静默失败。

这意味着"后台 FGS + 音频焦点 + 持续播放"这条保活路径从 API 37 起被系统层封堵。如果 App 需要在后台持续播放音频，必须保证前台交互状态（Activity 可见、或 FGS 由用户操作触发）成立。已经在播放的音频流，如果应用退到后台且失去了 While-In-Use 状态，系统会在一段宽限期后停止音频焦点。

## WorkManager vs JobScheduler vs AlarmManager：选型指南

当 App 需要做后台任务时，这三个 API 最常见，但职责边界差很多。选错工具，后面看到的大部分“系统为什么不让我跑”都只是后果。

### WorkManager：默认选择

WorkManager 适合“可以延迟，但希望最终能执行”的任务。它会按系统版本自动落到底层实现，在 API 23+ 上通常还是走 JobScheduler，所以 Doze、App Standby bucket 和 quota 依然会生效。

它的优势在于：

- 用 `Constraints` 表达网络、充电、空闲等条件
- 持久化到数据库，进程被杀后还能恢复
- 支持链式依赖和周期任务
- 默认帮你做批处理，减少碎片化唤醒

如果任务要尽快开始，又不该拉一个长期 FGS，WorkManager 2.7+ 的 `setExpedited()` 是更合适的入口。官方文档把 expedited work 定义成“重要、用户在意、几分钟内完成、希望立刻开始”的短任务。它仍然受 quota 控制，但比普通 work 更不容易被 Doze 或 Battery Saver 拖得太久。

### JobScheduler：系统原生调度层

JobScheduler 是系统原生调度 API。和 WorkManager 相比，它需要你自己处理更多细节，但也能直接用到一些 WorkManager 还没完全封装的能力，比如 `setPrefetch()`、`setUserInitiated(true)`，以及 Android 16 的 pending reason 调试接口。

这部分在 Android 16 的 public API 里，可以直接写成：

- `getPendingJobReason(int jobId)`，返回当前主因
- `getPendingJobReasons(int jobId)`，返回可能的原因集合 `int[]`
- `getPendingJobReasonsHistory(int jobId)`，返回 `List<PendingJobReasonsInfo>`，也就是“有限历史视图”，不是 `List<String>`

Android 17 又补了 `getPendingJobReasonStats()`，返回 `Map<Integer, Duration>`，按 reason 汇总 pending job 统计。这里要把两类数据分开：Android 16 的 history 看最近一段时间的原因变化，Android 17 的 stats 看按原因聚合后的累计时长。

Android 16 三个 pending reason API 可在 `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java` 复核；Android 17 的 `getPendingJobReasonStats()` 以官方 API reference 和 features 文档为准。

对性能排查，`getPendingJobReasonsHistory()` 的价值在于把“最近一段时间为什么一直没跑”变成可读数据；`getPendingJobReasonStats()` 则适合看一段时间内是哪类约束反复压住 Job。

### AlarmManager：只留给需要精确时刻的事情

AlarmManager 的强项是精确时间点触发，代价是最难和系统的省电批处理和平共处。只要你开始频繁调 `setExact()` / `setExactAndAllowWhileIdle()`，就等于主动放弃系统帮你合并唤醒窗口的机会。

从 Android 12（targetSdk 31）开始，如果要用 exact alarm 的 PendingIntent 路径，应用必须先声明并处理 exact alarm special access。targetSdk 33+ 可以根据场景选择 `SCHEDULE_EXACT_ALARM` 或 `USE_EXACT_ALARM`。代码里要先用 `AlarmManager.canScheduleExactAlarms()` 做门禁；未获授权时继续调 exact API，会命中 `SecurityException`，系统不会替你偷偷改成非精确闹钟。

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

- **AVF pVM 任务配额豁免**：[待验证] 通过 Android Virtualization Framework (AVF) 运行的受保护虚拟机（pVM）中的计算任务，可能不消耗宿主 App 的 JobScheduler 运行时配额。适用于需要隔离执行但又不想挤占宿主后台预算的 ML 推理、数据加工等场景。该豁免口径当前未在 Android Developers power-details、Android 17 changes 或 AOSP AVF 文档中核验到，补齐官方来源前不应作为选型决策依据。

因此，看到“受限状态下任务还是执行了”，先核对它是不是走了这些例外入口。

### 选型决策

可以按这条路径判断：

1. 必须在精确时刻触发，并且这是用户明确期待的提醒或闹钟，选 AlarmManager
2. 任务很短，用户刚刚触发，而且希望马上开始，先看 expedited WorkManager
3. 任务是用户亲手发起的长时间上传 / 下载，优先看 UIDT job
4. 任务可以延迟，但希望条件满足后最终执行，默认选 WorkManager
5. 需要 JobScheduler 的底层能力或细粒度调试接口，再直接用 JobScheduler
6. 任务需要持续运行且必须让用户清楚知道它在干什么，才用 FGS

## Android 16 的进程冻结流程：CachedAppOptimizer 与 Binder 协同

后台限制不只体现在 job、alarm 和 FGS 门禁上。应用退到 cached 之后，系统还会通过 CachedAppOptimizer 决定它何时进入 freezer。这套机制处理的是缓存进程何时暂停执行，Doze 和 Standby bucket 处理的是后台任务何时允许运行。

Android 16 在这里补了一层约 10 秒的 debounce。进程刚进入 cached 状态时，系统不会立刻冻结，而是先留出一个短窗口，避开用户来回切任务时的频繁 freeze / unfreeze。对体验的影响很直接：最近刚离开前台的应用，回切时更少撞上“刚被冻结又马上解冻”的额外开销。

Binder 侧也补了配套能力。`IBinder.FrozenStateChangeCallback` 允许系统服务感知远端进程已经 frozen 或恢复运行。对高频 callback 分发器，这个信号的作用是暂停发送非必要回调，或者改用丢弃策略，避免事务堆积在 frozen 进程前面。排查后台任务时，如果 Job、Alarm 和配额都正常，但进程长时间停在 cached + frozen 状态，就要把 CachedAppOptimizer 和 Binder 回调一起看。



### BINDER_FREEZE ioctl 与竞态处理

和排查 freezer 相关问题直接相关的细节主要有三类：

**BINDER_FREEZE ioctl 结构体**（`kernel/common/drivers/android/binder.c`）：
```c
struct binder_freeze_info {
    __u32 pid;        // 目标进程 group-leader PID
    __u32 enable;     // 1=冻结, 0=解冻
    __u32 timeout_ms; // 等待事务排空超时（ms），0=立即返回-EAGAIN
};
```

**BINDER_GET_FROZEN_INFO 查询结果**：
```c
struct binder_frozen_status_info {
    __u32 pid;
    __u32 sync_recv;   // bit 0 = 冻结后收到同步事务；bit 1 = race window 内新事务
    __u32 async_recv;  // 异步事务接收计数
};
```

**竞态修复**（commit `58a9e28781be68`）：
- 两步冻结之间检测到新同步事务 → 允许回滚 cgroup freeze
- 若响应在回滚前到达 → 按 oneway 事务处理，等解冻后处理

**FrozenStateChangeCallback 注册路径（API 36+）**：
```
IBinder.addFrozenStateChangeCallback(executor, callback)
  → BpBinder::addFrozenStateChangeCallback()  // libs/binder/BpBinder.cpp:566
    → IPCThreadState::addFrozenStateChangeCallback(handle, proxy)  // IPCThreadState.cpp:1015
      → mOut.writeInt32(BC_REQUEST_FREEZE_NOTIFICATION)  // 写入 kernel driver
        → 内核维护 frozen 状态，变更时通过 BR_FROZEN_NOTIFICATION 推送
```

**BR_TRANSACTION_PENDING_FROZEN**（Android 14+）：内核告知用户空间 oneway 事务正在等待目标解冻，用于避免 buffer 溢出导致的进程崩溃。

**关键源码索引**：
- `libs/binder/BpBinder.cpp` L566-L605 — addFrozenStateChangeCallback 转发
- `libs/binder/IPCThreadState.cpp` L1015-L1026 — BC_REQUEST_FREEZE_NOTIFICATION 发送
- `services/core/java/com/android/server/am/CachedAppOptimizer.java` L2037-L2055 — 冻结编排里先冻结 Binder 接口
- `services/core/java/com/android/server/am/Freezer.java` L44-L61 — freezeBinder() 抽象入口
### CachedAppOptimizer 的 GC 联动与内存压缩

从 Android 14 开始，CachedAppOptimizer 在冻结 cached 进程前可能请求应用运行时执行一次 GC，为后续的内存回收做准备。冻结后，系统还可能对进程执行额外的内存压缩（compaction）：包括将脏页回写到 backing storage、将匿名页压缩到 ZRAM。

这套机制不依赖 16KB 页——它在 4KB 页设备上同样生效。但 16KB 页设备的单次页面释放粒度更大（16KB vs 4KB），压缩后的内存回收效率会更高。排查时可以在 Perfetto 中观察系统压缩事件前后，目标进程的 GC slice 与 `malloc_stats` 下降是否同步出现。

**关键源码路径**：
- `services/core/java/com/android/server/am/CachedAppOptimizer.java` — freeze 流程与 GC 请求
- `system/core/lmkd/lmkd.cpp` — lmkd 压力触发的回收路径
- source.android.com — cached-apps-freezer 官方文档

## Binder Freezer Driver 协同机制：源码级补充

CachedAppOptimizer 与 Binder Driver 协同冻结时，关键实现细节集中在 Binder 冻结、cgroup freezer 和回调策略这几处。

### 两步冻结的原子性问题

CachedAppOptimizer 对单个进程执行冻结时，严格按以下顺序操作：

```
1. freezeBinder(pid)  // BINDER_FREEZE ioctl → 冻结 Binder 接口
2. setProcessFrozen(uid, pid, true)  // 写 cgroup.freeze → 冻结进程线程
```

这两步**不是原子操作**。commit `58a9e28781be68d9a91fe9b8975c5c4bbf4be481`（2021-09-07）修复了如下竞态：

> 步骤 1-2 之间如果有新的同步 Binder 事务到达目标进程的已冻结主线程，该线程会收到 response 后尝试处理，导致崩溃或无响应。

修复方案：在两步之间增加 pending transaction 检测，如有新事务则回滚主线程冻结状态。

**关键源码路径**：
- 冻结入口：`services/core/java/com/android/server/am/CachedAppOptimizer.java`
- Kernel 实现：`kernel/common/drivers/android/binder.c` — `BINDER_FREEZE` ioctl handler
- cgroup v2 freezer：`kernel/common/kernel/cgroup/freezer.c`
- libprocessgroup 抽象：`system/core/libprocessgroup/profiles/cgroups.json` — FreezerState 定义

### BINDER_FREEZE ioctl 的返回语义

| 返回值/返回码 | 含义 |
|-------------|------|
| -EAGAIN | 有未排空的 Binder 事务，需重试 |
| BR_FROZEN_REPLY | Binder 驱动向用户空间返回的冻结确认 |
| 同步事务发往 frozen 进程 | 内核直接杀死目标进程，防止调用线程死锁 |

### FrozenStateChangeCallback 的实际使用模式

`IBinder.addFrozenStateChangeCallback()`（API 36）让系统服务在远端进程冻结/解冻时收到通知。公开 API 签名要求传入 `Executor` 和 `FrozenStateChangeCallback`，回调参数是 `(IBinder who, @State int state)`，状态值为 `STATE_FROZEN` / `STATE_UNFROZEN`：

```java
// 公开 API (API 36+): 需要传入 Executor
binder.addFrozenStateChangeCallback(executor, (who, state) -> {
    if (state == IBinder.FrozenStateChangeCallback.STATE_FROZEN) {
        // 暂停向该进程发送非关键 callback
        // 或改用 FROZEN_CALLEE_POLICY_DROP
    } else {
        // STATE_UNFROZEN：恢复发送
    }
});
// 单参数 overload (callback only) 是 @hide / internal，不在公开 API 中
```

**源码路径**：`frameworks/base/core/java/android/os/IBinder.java`

### RemoteCallbackList 的 frozen 策略

`RemoteCallbackList` 提供三种内置策略处理发往 frozen 进程的回调：

- `FROZEN_CALLEE_POLICY_DROP`：静默丢弃，节省 buffer 避免溢出崩溃
- `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT`：只保留最新一条，解冻后送达
- `FROZEN_CALLEE_POLICY_ENQUEUE_ALL`：保留全部事件，解冻后依次送达。适用于必须保留完整事件历史的场景，但可能导致 buffer overflow 或 stale events，默认不推荐

大多数场景推荐 `DROP` 或 `ENQUEUE_MOST_RECENT`。

**源码路径**：`frameworks/base/core/java/android/os/RemoteCallbackList.java`


## 后台执行对前台性能的影响

性能分析里，很多时候只盯前台 App 的渲染和响应，却漏掉了后台行为带来的间接代价。不合理的后台工作，经常和前台卡顿、发热、续航变短一起出现。

### CPU 争抢

最直接的影响是 CPU 资源争抢。当前台 App 正在做 layout 或 draw 操作时，后台进程的网络请求、数据同步、图片解码等工作会同时竞争 CPU 时间。在大小核架构（5.3 节）下，如果后台任务被调度到大核上运行，会直接影响前台 App 获得的大核时间片。

在 Perfetto 中，这类问题表现为：在滑动或动画的 Trace 片段中，CPU Track 显示多个后台进程的线程在同一个大核上有活动，导致前台 App 的 RenderThread 被抢占，出现帧延迟。

[待高爷补充：Perfetto 中后台进程抢占 CPU 导致前台掉帧的 Trace 截图]

### 内存压力

后台进程消耗的内存会增加系统的整体内存压力。当内存紧张时，LMK（4.4 节）会开始杀进程，而 kswapd 后台回收会增加 I/O 负载。这些都会间接影响前台 App 的性能——GC 暂停变长、I/O 操作变慢、页面切换时因内存分配延迟导致卡顿。

### 热节流

这是最容易被忽略但影响最严重的。持续的后台工作（尤其是网络 + CPU 密集型任务）会推高 SoC 温度。当温度达到 Thermal 阈值（5.5 节），系统开始降频——此时前台 App 也被连累。这就是为什么有时候 App 用着用着突然变卡，去查 Trace 发现 CPU 频率被 Thermal 降到了最低档。

一个典型案例是：某个 App 在后台持续上传照片（CPU 做图片压缩 + Radio 做网络传输），导致 SoC 温度升高，前台正在玩的 60fps 游戏被 Thermal 降频到 30fps。在 Perfetto 中可以同时看到 CPU Frequency Track 的下降和 Thermal Zone 的温度上升。

## 与其他机制的关系

**与 CPU 调度（5.1）的关系**：Standby bucket 主要控制的是 job、alarm、network 这类后台资源额度，不是直接给线程改一个固定的 CPU 优先级。它对调度的影响更多是间接的，后台任务被延后了，可运行线程自然变少，前台争抢压力也会下降。线程一旦真的进入 runnable，最终怎么分配 CPU，还要看进程状态、cgroup / uclamp、线程策略和具体子系统规则。

**与 EAS（5.2）的关系**：后台任务越碎、唤醒越频繁，EAS 就越难把工作稳定压在合适的核上。大量短时唤醒会让大小核迁移变多，额外吃掉能量和调度开销。

**与 DVFS（5.4）的关系**：后台工作把利用率顶上去后，DVFS 会升频，功耗跟着走高。Doze 和 bucket 限流的价值之一，就是少让这类后台负载在灭屏后把频率拉起来。

**与 Thermal（5.5）的关系**：后台同步、转码、上传这类持续工作，最容易把 SoC 温度慢慢推高。温度一旦过阈值，Thermal 降频打到的是整个前台体验，不会只处罚后台线程。

**与 Android 功耗管理（5.6）的关系**：5.6 节偏底层，讲 WakeLock、PowerManagerService、device idle。这里更偏框架和 API 选择，讲的是应用层后台任务最终会被哪些规则拦下来。

**与响应速度（8.4）的关系**：BAL 从 Android 10 开始收紧，后续版本还在继续加限制。后台能不能拉起 Activity，取决于用户可见性、通知 / `PendingIntent` / `IntentSender` 路径和系统豁免条件，不能再按老版本经验硬推。

## 版本演进

| 版本 | 核心变化 | 性能分析影响 |
|------|----------|-------------|
| Android 6.0 (API 23) | 引入 Doze 和 App Standby | 灭屏后后台任务开始系统级延后 |
| Android 7.0 (API 24) | 引入 Light Doze | 刚灭屏就可能开始限流 |
| Android 8.0 (API 26) | 限制后台 `startService()`，收紧隐式广播 | 很多旧式后台常驻方案直接失效 |
| Android 9.0 (API 28) | 引入 App Standby Buckets | Job、alarm、network 开始按桶分级限流 |
| Android 10 (API 29) | BAL 收紧 | 后台弹 Activity 的路径明显变少 |
| Android 12 (API 31) | Restricted bucket、后台启动 FGS 限制、exact alarm special access | 后台任务调度和 FGS 启动都要先过门禁 |
| Android 13 (API 33) | Restricted bucket 的长期未交互阈值从 45 天降到 8 天 | 很久不用的 App 更快进入重限流状态 |
| Android 14 (API 34) | FGS 类型强制声明，新增 `remoteMessaging`、`shortService`、`systemExempted` 等类型；CachedAppOptimizer 引入冻结前 GC 请求 + 冻结后 compaction | FGS 类型、权限和运行时前提都要写完整 |
| Android 15 (API 35) | `mediaProcessing` 类型加入，`dataSync` / `mediaProcessing` 引入 6 小时预算 | 长时间同步和媒体加工要处理超时回调 |
| Android 16 (API 36) | `getPendingJobReasons()` / `getPendingJobReasonsHistory()` 进入 public API；CachedAppOptimizer 增加约 10 秒 freeze debounce，Binder 增加 `FrozenStateChangeCallback` | Job pending 原因更容易直接定位，cached 进程的 freeze / unfreeze 抖动也更容易解释 |
| Android 17 (API 37) | 后台音频操作必须具备 While-In-Use 能力；`getPendingJobReasonStats()` 增加 Job pending reason 统计 | 后台保活路径进一步收窄，Job 未执行原因更容易聚合分析 |

## 常见问题与误区

### 误区 1："WorkManager 保证任务在指定时间执行"

WorkManager 不保证精确时间。它定义的是"约束条件"，系统会在满足约束条件后的某个时刻执行任务，但这个时刻由系统决定。如果你需要"精确在 10:00 执行"，必须使用 AlarmManager。

### 误区 2："前台服务不会被系统杀掉"

前台服务的进程优先级很高，但不是不可杀。内存极度紧张时系统仍然可能杀掉前台服务进程。另外，从 Android 15 开始，`dataSync` 和 `mediaProcessing` 类型有 6 小时的超时限制。

### 误区 3："我的 JobScheduler 不执行一定是系统 bug"

大部分情况下，问题出在 bucket、quota、约束条件或者设备状态。先用 `adb shell am get-standby-bucket <package>` 看桶位，再用 `adb shell dumpsys jobscheduler <package>` 看具体约束；如果平台版本够新，还可以直接看 `getPendingJobReason()` 和 `getPendingJobReasonsHistory()`。

### 误区 4："Doze 只在晚上才生效"

Doze 的触发条件是灭屏 + 静止 + 未充电，与时间无关。白天如果手机放在桌上灭屏不动，一样会进入 Doze。

### 误区 5："后台限制只影响后台 App"

不完全是。后台工作对前台的影响上面已经详细讨论了——CPU 争抢、内存压力、热节流都会直接拖慢前台 App。优化后台行为本身就是前台性能优化的一部分。

## 参考资料

### AOSP 源码路径
- `frameworks/base/services/core/java/com/android/server/DeviceIdleController.java` — Doze / device idle 状态机
- `frameworks/base/core/java/android/app/usage/UsageStatsManager.java` — App Standby bucket 常量定义
- `frameworks/base/services/usage/java/com/android/server/usage/AppStandbyController.java` — App Standby bucket 管理逻辑
- `frameworks/base/services/core/java/com/android/server/job/JobSchedulerService.java` — JobScheduler 服务端实现
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java` — Job quota 与 bucket 约束控制
- `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java` — JobScheduler public API
- `frameworks/base/core/java/android/app/AlarmManager.java` — AlarmManager public API
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` — cached 进程 freeze 调度入口
- `frameworks/base/core/java/android/os/IBinder.java` — `FrozenStateChangeCallback` 定义
- `frameworks/base/core/java/android/app/Service.java` — Service 生命周期；FGS timeout 签名以 `Service` API reference 为准

### 官方文档
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details#app-stdby-bucket)
- [Background Execution Limits (Android 8.0)](https://developer.android.com/about/versions/oreo/background)
- [Foreground service types are required (Android 14)](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Android 15 behavior changes: foreground services](https://developer.android.com/about/versions/15/behavior-changes-15#fgs-hardening)
- [Android 15 foreground service types](https://developer.android.com/about/versions/15/changes/foreground-service-types)
- [Define work requests with WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Data transfer background task options](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [Schedule alarms](https://developer.android.com/develop/background-work/services/alarms/schedule)
- [Restrictions on starting a foreground service from the background](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Service API reference](https://developer.android.com/reference/android/app/Service)
- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [Android 17 Features](https://developer.android.com/about/versions/17/features)
- [Android 17 Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)

### 深入阅读
- [Battery Historian 使用指南](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [Perfetto Power Analysis](https://perfetto.dev/docs/quickstart/android-power)
- [Perfetto trace 配置与数据源说明](https://perfetto.dev/docs/concepts/config)

### Android 16 CachedAppOptimizer : Freezer 进程冻结机制源码级深度解析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android 16 CachedAppOptimizer : Freezer 进程冻结机制源码级深度解析.md
- 类型：源码级调研资料
- 摘要：这篇源码级调研聚焦 Android 16 Freezer 演进，覆盖 10 秒 debounce、新拆分的 Freezer 类、FrozenStateChangeCallback API，以及 cgroup v2 freezer 与 Binder freeze driver 的协同约束。
- 价值：直接补到 5.8 的系统实现层，避免后台限制章节只停留在策略说明。
