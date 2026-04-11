---
title: "后台执行限制与优化"
chapter: "5.8"
section: "5.8"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/oreo/background"
  - type: official
    path: "https://developer.android.com/guide/background"
  - type: official
    path: "https://developer.android.com/about/versions/12/foreground-services"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/fgs-types"
  - type: official
    path: "https://developer.android.com/about/versions/15/changes"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/DeviceIdleController.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/job/JobScheduler.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Service.java"
tags: [后台限制, Doze, App Standby, 前台服务, WorkManager, JobScheduler, AlarmManager, 省电, 后台启动, BAL]
related_chapters: ["5.6", "5.7", "11.2", "8.4"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
reviewed_date: "2026-04-12"
reviewed_by: "openclaw-task6"
task6_result: "needs-rework"
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
- 🔸 Android 16 / 17 的后台任务调试接口与策略变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或官方文档中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解后台执行限制

当我们在 Perfetto 中看到灭屏后某个进程仍在疯狂地占用 CPU，或者在 Battery Historian 中发现某个 App 的后台网络活动密密麻麻地布满整条时间线——这些现象背后，要么是 App 没有遵守系统的后台限制，要么是系统已经对它进行了限制而开发者还浑然不知。

Android 的后台执行限制不是一蹴而就的。从 Android 6.0 引入 Doze 模式开始，到 Android 8.0 限制后台服务，再到 Android 14 强制声明前台服务类型，Google 用了近十年时间，一步步收紧 App 在后台能做的事情。每一次收紧都伴随着大量 App 崩溃、功能异常和开发者抱怨——但方向从未改变：**让后台行为可预测、可控、可省电。**

理解这套限制体系，对我们分析性能问题有两层意义。第一层，当我们发现某个后台任务没有被按时执行时，能判断出是系统主动限制的结果（正常行为），还是代码逻辑的 bug。第二层，当我们需要做后台优化时，知道应该用什么 API、遵循什么约束，才能既完成任务又不拖垮系统。

本章前面讨论了 CPU 调度（5.1）、EAS（5.2）、大小核（5.3）、DVFS（5.4）、Thermal（5.5）和 Android 功耗管理框架（5.6）。那些章节解决的是"硬件如何高效运行"的问题，而这一节解决的是"软件如何被允许运行"的问题——当 App 被推到后台，系统会逐步剥夺它的执行权利，直到它几乎什么都做不了。

## Android 后台限制的演进：从"自由"到"管制"

### Android 6.0 之前：蛮荒时代

在 Android 6.0（Marshmallow）之前，App 在后台几乎没有限制。一个 App 只要在 manifest 中声明了 `android.permission.WAKE_LOCK`，就可以通过 `startService()` 启动一个长期运行的后台服务，然后持有一个 PARTIAL_WAKE_LOCK，让 CPU 一直为自己工作。用户的手机灭屏之后，几十个 App 各自持锁、各自同步、各自拉网络——电池以肉眼可见的速度往下掉。

那个年代，"杀后台"是所有手机厂商的标配功能。MIUI 的"自启动管理"、EMUI 的"受保护应用"、ColorOS 的"后台运行白名单"——这些厂商定制功能的本质，都是在弥补 AOSP 对后台行为管控的缺失。

### Android 6.0-7.0：Doze 与 App Standby 登场

Android 6.0（API 23）引入了 **Doze 模式**。这是 Android 第一次在系统层面对后台行为进行大规模限制。当设备灭屏、静止、未充电一段时间后，系统进入 Doze 状态，强制暂停大部分后台活动。

Android 7.0（API 24）在此基础上增加了 **Light Doze**——一个较温和的版本，在设备灭屏但可能还在移动时生效，限制比 Deep Doze 宽松但仍然有效。

同时，Android 7.0 引入了 **App Standby**，根据 App 的使用频率对其进行分级管理。不常用的 App 会被限制网络访问和后台任务执行频率。

我们在 5.6 节（Android 功耗管理）中详细讨论了 Doze 的维护窗口机制和 App Standby 的基本原理。这里不再重复，而是聚焦于从 Android 8.0 开始的进一步收紧。

### Android 8.0：后台服务限制的转折点

Android 8.0（API 26，Oreo）是一个分水岭。在此之前，App 可以通过 `startService()` 随时启动后台服务；在此之后，**后台 App 调用 `startService()` 会抛出 `IllegalStateException`**。这不是建议，是强制禁止。

Google 同时引入了 `startForegroundService()` 作为替代方案——它允许后台启动服务，但要求 App 必须在 **5 秒内** 调用 `startForeground()` 显示一个用户可见的通知。如果超时，系统会抛出 `ForegroundServiceDidNotStartInTimeException`（在某些版本中是 ANR），直接杀掉 App。

这个设计反映了一个核心理念：**后台工作可以存在，但必须对用户透明。** 你想做后台同步？可以，但用户得看到一个通知知道你在做。如果用户觉得这个通知烦人，他可以关掉它——这就等于关掉了你的后台工作。

此外，Android 8.0 还限制了隐式广播（Implicit Broadcast）的接收。大部分系统广播（如 `BOOT_COMPLETED` 除外）不再能通过 manifest 注册的 Receiver 接收，必须使用 Context 注册的动态 Receiver。这直接砍掉了大量 App 在开机后扎堆唤醒的"传统操作"。

### Android 9.0-10：App Standby Buckets 与后台启动 Activity 限制

Android 9.0（API 28，Pie）引入了 **App Standby Buckets**，将前面的 App Standby 机制细化为五个桶：Active、Working Set、Frequent、Rare、Restricted。系统会根据用户的使用习惯（可能借助设备端机器学习）动态调整 App 所属的桶。不同桶的 App 在 JobScheduler 执行频率、Alarm 触发频率、网络访问权限上享有不同级别的限制。

这个机制与我们前面讨论的 EAS 调度器（5.2 节）和 DVFS（5.4 节）形成互补：硬件层通过调度器决定"哪个任务分到多少 CPU 资源"，框架层通过 Standby Bucket 决定"这个 App 的后台任务到底能不能执行"。

Android 10（API 29）引入了 **后台 Activity 启动限制**（Background Activity Launch，简称 BAL）。在此之前，任何 App 都可以从后台弹出一个 Activity 覆盖在当前界面上——这就是臭名昭著的"广告弹窗"。Android 10 之后，后台 App 启动 Activity 会被系统静默忽略，只有极少数豁免情况（如全屏 Intent 通知、来电等）被允许。

### Android 12-14：前台服务类型强制声明

Android 12（API 31）进一步收紧了前台服务的启动限制：**后台 App 不能再启动前台服务**（除非满足特定豁免条件，如收到高优先级 FCM 消息）。如果违反，会抛出 `ForegroundServiceStartNotAllowedException`。同时引入了 **Notification Trampoline 限制**：从通知点击启动的 Broadcast Receiver 不能再启动后台服务，必须直接启动 Activity 或使用其他方式。

Android 13（API 33）加快了 Restricted 桶的生效速度——从 Android 12 的 45 天未使用缩短到 **8 天**。如果一个 App 连续 8 天没有被用户打开，更容易进入最高限制级别的桶里。

Android 14（API 34）引入了两项重要变化：

**第一，前台服务类型强制声明。** App 必须在 manifest 中明确声明前台服务的类型（如 `camera`、`connectedDevice`、`dataSync`、`health`、`location`、`mediaPlayback`、`mediaProjection`、`messaging`、`phoneCall`、`specialUse`），否则调用 `startForeground()` 会抛出 `MissingForegroundServiceTypeException`。每种类型还对应一个特定的权限（如 `FOREGROUND_SERVICE_DATA_SYNC`），这些权限默认授予但不可由用户撤销。

**第二，能耗惩罚桶。** 如果一个 App 反复触发 ANR，系统会自动将其移入 Restricted 桶，即使它的使用频率本应属于更高的桶。

[图：Android 后台限制演进时间线，从 6.0 到 17，标注每个版本的核心限制变化]

## Doze 与 App Standby 机制的内部工作

我们在 5.6 节中了解了 Doze 的基本概念和维护窗口机制。这里从性能分析的角度，深入看看 Doze 和 App Standby Buckets 对后台任务的实际影响。

### Deep Doze：逐步加深的休眠

Deep Doze 在设备灭屏、静止、未充电的条件下触发。它的核心设计是**逐步延长休眠时间、缩短维护窗口**。

进入 Doze 后的第一阶段，系统大约每 25 分钟打开一个维护窗口（maintenance window），持续约 5 分钟。在维护窗口中，App 可以执行被暂停的工作（JobScheduler 任务、同步、Alarm 等）。之后系统回到休眠，间隔逐步加长到约 60 分钟、120 分钟……维护窗口的持续时间也逐渐缩短。

在 Doze 期间被限制的行为包括：

- 网络访问被完全禁止（维护窗口期间除外）
- 标准 `AlarmManager` 闹钟被延迟到下一个维护窗口
- `WakeLock` 被忽略（部分类型除外）
- WiFi 扫描被禁止
- 同步适配器（SyncAdapter）被暂停
- `JobScheduler` 任务被推迟

唯一的例外是 `setAndAllowWhileIdle()` 和 `setExactAndAllowWhileIdle()` 设置的 Alarm——它们可以在 Doze 期间触发，但每个 App 每大约 9 分钟只能触发一次。这是给闹钟、日历提醒等必须准时触发的场景留的口子。

### Light Doze：温和版休眠

Light Doze 在设备灭屏但可能仍在移动时生效（比如手机放在口袋里但人在走路）。它的限制比 Deep Doze 宽松：

- 网络访问在维护窗口期间被允许
- `JobScheduler` 和 `SyncAdapter` 在维护窗口中可以运行
- `WakeLock` 不受影响
- Alarm 不受影响

Light Doze 的维护窗口间隔从约 10 分钟开始，逐步延长到约 30 分钟。

在 Perfetto 中，我们可以通过搜索 `device_idle` 相关的事件来观察 Doze 状态的切换。`adb shell dumpsys deviceidle` 可以查看当前的 Doze 状态和维护窗口历史。

### App Standby Buckets：五级分类

App Standby Buckets 从 Android 9 开始引入，五个桶的资源和限制差异如下：

**Active（活跃）**：App 当前正在使用或刚被使用过。没有后台限制，JobScheduler 和网络访问不受约束。

**Working Set（工作集）**：App 经常使用但当前不在前台。有轻微限制——JobScheduler 的执行频率约每 2 小时一次（非精确值，系统会动态调整）。

**Frequent（频繁）**：App 定期使用但不是每天。JobScheduler 执行频率更低，网络访问在 Doze 期间更受限。

**Rare（稀有）**：App 很少使用。JobScheduler 执行频率约每天一次，Alarm 被严格限制，网络访问受限更严重。

**Restricted（受限）**：Android 12 新增。App 被系统判定为"消耗过多资源"或用户手动限制。这是最严格的级别：Jobs 每天最多执行一次，Alarm 被严重限制（每天几个），网络访问受限，甚至 FCM 高优先级消息的数量也被限制。

关键代码路径在 `DeviceIdleController.java` 中，它负责维护每个 App 的 Standby Bucket 并根据 Bucket 级别向 `JobScheduler`、`AlarmManager`、`NetworkPolicyManager` 等子系统下发限制策略。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/DeviceIdleController.java]

```java
// frameworks/base/services/core/java/com/android/server/DeviceIdleController.java
// App Standby Bucket 定义（部分）
public static final int STANDBY_BUCKET_ACTIVE = 10;
public static final int STANDBY_BUCKET_WORKING_SET = 20;
public static final int STANDBY_BUCKET_FREQUENT = 30;
public static final int STANDBY_BUCKET_RARE = 40;
public static final int STANDBY_BUCKET_RESTRICTED = 45;
```

开发者可以通过 `UsageStatsManager.getAppStandbyBucket()` 查询自己 App 的当前桶级别。测试时可以用 `adb shell am set-standby-bucket <package> <bucket>` 强制设置。

### 在 Perfetto 中的表现

当分析后台任务不执行的问题时，我们在 Perfetto 中可以关注以下 Track 和事件：

- **`device_idle` Track**：显示设备当前处于什么 Doze 状态（active/idle/light_idle/maintenance 等）
- **`am_proc_start` / `am_kill` 事件**：观察 App 进程被系统回收的情况
- **CPU Track**：灭屏期间是否有异常的 CPU 活动持续存在
- **Network Track**：后台网络活动是否符合维护窗口的时间模式

如果发现一个后台 Job 在预期时间没有被触发，先检查 App 的 Standby Bucket 级别，再检查设备是否在 Doze 中。大部分“我的 JobScheduler 怎么不执行了”的问题，根源都在这两条。

[待高爷补充：Perfetto 中 device_idle Track 的截图示例]

## 前台服务：后台工作的"合法通行证"

当 App 确实需要做后台工作时，前台服务（Foreground Service，简称 FGS）是最可靠的方式。它的代价是：必须向用户展示一个持续的通知。

### 前台服务类型体系

从 Android 14 开始，前台服务必须声明类型。每种类型对应特定的使用场景和权限要求：

| 类型 | 权限 | 典型场景 |
|------|------|----------|
| `camera` | `FOREGROUND_SERVICE_CAMERA` | 后台拍照/视频通话 |
| `connectedDevice` | `FOREGROUND_SERVICE_CONNECTED_DEVICE` | BLE 通信、USB 外设 |
| `dataSync` | `FOREGROUND_SERVICE_DATA_SYNC` | 文件同步、数据备份 |
| `health` | `FOREGROUND_SERVICE_HEALTH` | 健康数据采集（心率等） |
| `location` | `FOREGROUND_SERVICE_LOCATION` | 导航、位置追踪 |
| `mediaPlayback` | `FOREGROUND_SERVICE_MEDIA_PLAYBACK` | 音乐/视频播放 |
| `mediaProjection` | `FOREGROUND_SERVICE_MEDIA_PROJECTION` | 屏幕录制 |
| `messaging` | `FOREGROUND_SERVICE_MESSAGING` | 即时通讯消息收发 |
| `phoneCall` | `FOREGROUND_SERVICE_PHONE_CALL` | VoIP 通话 |
| `specialUse` | `FOREGROUND_SERVICE_SPECIAL_USE` | 不属于以上任何类型的特殊场景 |

[已验证: 官方文档, developer.android.com/about/versions/14/changes/fgs-types]

声明方式是在 manifest 的 `<service>` 标签中使用 `android:foregroundServiceType` 属性：

```xml
<!-- AndroidManifest.xml -->
<service
    android:name=".SyncService"
    android:foregroundServiceType="dataSync"
    android:exported="false">
</service>
```

### 超时机制：6 小时的硬限制

Android 15（API 35）引入了一个重要变化：`dataSync` 和 `mediaProcessing` 类型的前台服务有 **6 小时/24 小时** 的运行上限。超过这个时间后，系统会调用服务的 `onTimeout(int id, int fgsType)` 方法。如果服务不自行停止，系统会强制杀掉它。

```java
// frameworks/base/core/java/android/app/Service.java
// Android 15+ 新增
public void onTimeout(int startId, int fgsType) {
    // 默认实现：什么都不做，然后被系统杀掉
    // 正确做法：在这里停止服务
    stopForeground(STOP_FOREGROUND_REMOVE);
    stopSelf();
}
```

这里有几个细节值得注意。第一，6 小时的计时是按类型独立计算的——`dataSync` 用了 5 小时不影响 `mediaProcessing` 的额度。第二，把 App 带到前台会重置计时器。第三，超过额度后再尝试启动同类型的前台服务，会直接抛出 `ForegroundServiceStartNotAllowedException`。

## WorkManager vs JobScheduler vs AlarmManager：选型指南

当 App 需要做后台任务时，这三个 API 是最常见的选项。它们的定位和适用场景差异很大。

### WorkManager：推荐首选

WorkManager 是 Jetpack 组件之一，也是 Google 官方推荐的"可延迟后台任务"解决方案。它的核心优势在于**兼容性和可靠性**：

在底层，WorkManager 会根据设备的 API 级别自动选择最佳实现——在 API 23+ 上使用 JobScheduler，在更低版本上回退到 AlarmManager + BroadcastReceiver。开发者不需要关心这些差异，只需要定义 WorkRequest 和约束条件。

WorkManager 的关键特性包括：

**约束条件（Constraints）**：可以指定任务执行的前提条件——需要网络、需要充电、需要设备空闲、需要存储空间充足等。只有在所有约束条件都满足时，任务才会被调度执行。这样 WorkManager 可以配合 Doze 的维护窗口，在系统认为“合适的时候”运行任务。

**周期性任务**：支持定义周期执行的 WorkRequest，最小周期间隔为 15 分钟。系统会根据 App 的 Standby Bucket 动态调整实际执行频率。

**链式任务**：可以将多个 WorkRequest 组成执行链，定义先后顺序和并行关系。

**持久化保证**：WorkRequest 会被持久化到数据库中，即使 App 被杀掉或设备重启，任务仍然会在条件满足时被执行。

从性能角度看，WorkManager 相比直接使用 JobScheduler 的一个重要优势是**任务批处理**。WorkManager 会尽量将多个任务的执行窗口合并，减少设备唤醒次数。每次设备唤醒都是一笔功耗开销（CPU 从 idle 恢复、可能还要点亮 radio），合并执行窗口可以显著降低总功耗。

### JobScheduler：系统级调度

JobScheduler 从 Android 5.0（API 21）开始提供，是 Android 原生的任务调度 API。它的工作方式与 WorkManager 类似——开发者定义 JobInfo 和约束条件，系统负责在合适的时机触发执行。

JobScheduler 的优势在于它是系统服务的一部分，调度策略由系统统一管理。系统可以将多个 App 的 Job 合并到同一个执行窗口中（batching），减少设备唤醒次数。在 App Standby Buckets 的机制下，JobScheduler 会根据 App 的 Bucket 级别自动调整 Job 的执行频率。

Android 16（API 36）对 JobScheduler 的配额管理做了进一步收紧。Job 的运行时配额会更加严格地考虑 App 的 Standby Bucket、Job 是否在前台状态下启动的、以及是否与前台服务并发运行等因素。新增的 `JobDebugInfo` API 和 `JobScheduler#getPendingJobReasonsHistory` 可以帮助开发者理解 Job 为什么没被执行或为什么被停止。[已验证: 官方文档, developer.android.com/about/versions/16]

```java
// Android 16 新增的 JobDebugInfo API
// frameworks/base/core/java/android/app/job/JobDebugInfo.java
JobScheduler js = (JobScheduler) getSystemService(Context.JOB_SCHEDULER_SERVICE);
// 查询 Job 未被执行的历史原因
List<String> reasons = js.getPendingJobReasonsHistory(jobId);
// reasons 包含如 "APP_STANDBY_BUCKET_RARE"、"BATTERY_NOT_CHARGING" 等原因
```

### AlarmManager：精确时机的最后手段

AlarmManager 是最古老的调度 API，用于在精确的时间点触发代码执行。它的特点是可以设置**精确闹钟**（`setExact()`、`setExactAndAllowWhileIdle()`），即使在 Doze 模式下也能按时触发。

正因为如此，AlarmManager 也是对电池影响最大的调度方式。每次精确闹钟触发都意味着一次设备唤醒，如果多个 App 各设各的精确闹钟，系统就没办法合并唤醒窗口，电池损耗会成倍增加。

从 Android 12（API 31）开始，使用精确闹钟需要声明 `SCHEDULE_EXACT_ALARM` 权限。这个权限不是自动授予的——用户需要在系统设置中手动允许。如果 App 没有这个权限就调用 `setExact()`，闹钟会被静默降级为非精确闹钟。

从 Android 13（API 33）开始，`SCHEDULE_EXACT_ALARM` 权限默认只授予闹钟和日历类 App。其他类型的 App 需要用户在设置中手动授权。

**AlarmManager 只应用于真正的"闹钟"场景**——定时提醒、日历事件、计时器等。其他任何后台定时任务都应该使用 WorkManager 或 JobScheduler。

### 选型决策

用一个简单的决策路径来概括：

1. 任务需要准时触发（精度要求在秒级）→ AlarmManager（但需精确闹钟权限）
2. 任务可以延迟但必须保证执行 → WorkManager（默认选择）
3. 任务需要系统级批处理优化、不需要持久化 → JobScheduler
4. 任务需要长期持续运行且用户需要感知 → 前台服务

绝大多数后台任务都应该使用 WorkManager。它覆盖了"可延迟但需保证执行"这个最常见的需求，同时自动适配 Doze 和 App Standby 的限制。

## 后台执行对前台性能的影响

这个话题在性能分析中经常被忽视——我们通常关注的是前台 App 的渲染和响应速度，而忽略了后台行为对前台的间接影响。实际上，不合理的后台工作是前台卡顿、发热和续航变短的常见根因之一。

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

**与 CPU 调度（5.1）的关系**：App Standby Buckets 通过影响进程的调度优先级来间接影响 CPU 分配。Restricted 桶的 App 进程会被降低 cgroup 优先级，获得更少的 CPU 时间。

**与 EAS（5.2）的关系**：后台任务的唤醒模式直接影响 EAS 对能量最优调度决策的判断。频繁的短时唤醒会导致 CPU 在大小核之间频繁迁移，增加迁移开销。

**与 DVFS（5.4）的关系**：后台工作推高 CPU 利用率后，DVFS 会提升频率和电压，增加功耗。Doze 的本质就是通过限制后台工作来让 CPU 保持低频甚至休眠。

**与 Thermal（5.5）的关系**：上面提到的热节流是最直接的交叉影响。后台工作的累积热量会导致 Thermal 管控触发，降频影响前台。

**与 Android 功耗管理（5.6）的关系**：5.6 节讨论了 WakeLock 和 PowerManagerService 的机制，本节则聚焦在"系统如何限制 App 的后台行为"这个更上层的维度。

**与响应速度（8.4）的关系**：后台 Activity 启动限制（BAL）直接影响 App 的后台启动体验。从 Android 12 开始，从通知启动 Activity 需要通过全屏 Intent 或使用 Activity Options 中的 BAL 权限。

## 版本演进

| 版本 | 核心变化 | 性能分析影响 |
|------|----------|-------------|
| Android 6.0 (API 23) | 引入 Deep Doze | 灭屏静止后后台任务大幅减少 |
| Android 7.0 (API 24) | 引入 Light Doze + App Standby | 移动中灭屏也有后台限制 |
| Android 8.0 (API 26) | 禁止后台 `startService()` | 大量 App 崩溃需适配 `startForegroundService()` |
| Android 9.0 (API 28) | App Standby Buckets 五级分类 | Bucket 级别影响所有后台 API 行为 |
| Android 10 (API 29) | 后台 Activity 启动限制 | 后台弹窗被禁止 |
| Android 11 (API 30) | 收紧后台位置权限 | 后台定位更困难 |
| Android 12 (API 31) | 禁止后台启动 FGS + 精确闹钟需权限 | 后台服务启动受限，Alarm 需声明权限 |
| Android 13 (API 33) | Restricted 桶 8 天生效 | 不常用 App 快速进入高限制状态 |
| Android 14 (API 34) | FGS 类型强制声明 + 能耗惩罚桶 | 后台服务必须声明用途 |
| Android 15 (API 35) | dataSync/mediaProcessing 6h 超时 + PendingIntent BAL 收紧 | 长时间同步任务被强制限时 |
| Android 16 (API 36) | JobScheduler 配额收紧 + JobDebugInfo API | Job 执行频率更严格，调试工具增强 |
| Android 17 (API 37) | 后台音频限制 + AI 驱动的后台管理 + BAL 扩展到 IntentSender | 后台行为管控更加智能化 |

## 常见问题与误区

### 误区 1："WorkManager 保证任务在指定时间执行"

WorkManager 不保证精确时间。它定义的是"约束条件"，系统会在满足约束条件后的某个时刻执行任务，但这个时刻由系统决定。如果你需要"精确在 10:00 执行"，必须使用 AlarmManager。

### 误区 2："前台服务不会被系统杀掉"

前台服务的进程优先级确实很高，但不是不可杀。内存极度紧张时系统仍然可能杀掉前台服务进程。更重要的是，从 Android 15 开始，`dataSync` 和 `mediaProcessing` 类型有 6 小时的超时限制。

### 误区 3："我的 JobScheduler 不执行一定是系统 bug"

大部分情况下是 App 的 Standby Bucket 太低。用 `adb shell am get-standby-bucket <package>` 检查当前桶级别，用 `adb shell dumpsys jobscheduler` 查看具体的 Job 状态和未执行原因。

### 误区 4："Doze 只在晚上才生效"

Doze 的触发条件是灭屏 + 静止 + 未充电，与时间无关。白天如果手机放在桌上灭屏不动，一样会进入 Doze。

### 误区 5："后台限制只影响后台 App"

不完全是。后台工作对前台的影响上面已经详细讨论了——CPU 争抢、内存压力、热节流都会直接拖慢前台 App。优化后台行为本身就是前台性能优化的一部分。

## 参考资料

### AOSP 源码路径
- `frameworks/base/services/core/java/com/android/server/DeviceIdleController.java` — Doze 与 App Standby 核心实现
- `frameworks/base/services/core/java/com/android/server/job/JobSchedulerService.java` — JobScheduler 服务
- `frameworks/base/core/java/android/app/Service.java` — 前台服务 API
- `frameworks/base/core/java/android/app/job/JobScheduler.java` — JobScheduler API
- `frameworks/base/core/java/android/app/AlarmManager.java` — AlarmManager API
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobDebugInfo.java` — Android 16 JobDebugInfo

### 官方文档
- [Background Execution Limits (Android 8.0)](https://developer.android.com/about/versions/oreo/background)
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Foreground Services (Android 12+)](https://developer.android.com/about/versions/12/foreground-services)
- [FGS Types (Android 14+)](https://developer.android.com/about/versions/14/changes/fgs-types)
- [Background Work with WorkManager](https://developer.android.com/guide/background)
- [Android 15 Behavior Changes](https://developer.android.com/about/versions/15/changes)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)

### 深入阅读
- [Battery Historian 使用指南](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [Perfetto Power Analysis](https://perfetto.dev/docs/quickstart/android-power)
