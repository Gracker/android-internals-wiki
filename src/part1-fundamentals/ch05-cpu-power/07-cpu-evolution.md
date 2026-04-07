---
title: "CPU 相关的版本演进"
chapter: "5.7"
status: ready-for-review
applicable_versions: "Android 5.0 - 16"
last_verified: "2026-04-01"
last_verified_against: "Android 15 developer docs, AOSP source code"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/about/versions/marshmallow/android-6.0-changes"
  - type: official
    path: "developer.android.com/about/versions/pie/power"
  - type: official
    path: "developer.android.com/about/versions/12/behavior-changes-12"
  - type: official
    path: "source.android.com/docs/core/power"
  - type: blog
    path: "ARM documentation - Energy Aware Scheduling"
tags: ['doze', 'JobScheduler', 'adaptive-battery', 'wakelock', 'app-standby-buckets', 'eas', 'background-restrictions', 'gki', 'power-management', 'version-evolution']
related_chapters: ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "11.5"]
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2"
reviewed_date: "2026-04-04"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
---

# CPU 相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 5.0+ 引入 JobScheduler 优化后台功耗
- 🔹 Android 6.0 Doze 模式引入
- 🔹 Android 9.0 Adaptive Battery + App Standby Buckets
- 🔹 Android 10 EAS 成为默认调度策略
- 🔹 Android 12+ 对精确闹钟、前台服务、后台启动的持续限制

### 扩展（可选深入）

- 🔸 GKI 对内核调度模块定制化的影响
- 🔸 Android 16 功耗与调度相关的新变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 CPU 相关的版本演进

做过 Android 性能优化的工程师，很可能遇到过这种情况：App 在 Android 10 上跑得很好，到了 Android 12 突然后台任务不执行了；或者用 AlarmManager 设了一个精确闹钟，结果在 Android 13 上根本不响。这不是 Bug，是 Google 在每个版本中逐步收紧后台行为限制的结果。

从 Android 5.0 到 Android 16，Google 围绕 CPU 和功耗管理做了一系列层层递进的改动。这些改动覆盖了三个层面：

1. **内核调度层面**：从传统 CFS 到 EAS（Energy Aware Scheduling），再到 GKI 对调度定制化的约束
2. **系统策略层面**：Doze 模式、App Standby Buckets、Adaptive Battery——系统越来越"聪明"地决定哪些 App 可以用 CPU，哪些必须等着
3. **应用约束层面**：JobScheduler 引入 → 后台服务限制 → 精确闹钟管控 → 前台服务类型化——App 能做的事情越来越受限

理解这条演进线，我们就能回答：为什么我的后台任务在某个版本突然不工作了？为什么同样的代码在不同设备上表现不一样？做功耗优化时，应该关注哪些系统机制的变化？

我们按时间线逐个版本看下来。

## Android 5.0：JobScheduler——后台任务批处理的开端

在 Android 5.0 之前，开发者要做后台工作，主要有两个选择：用 `AlarmManager` 定时唤醒，或者直接起一个 `Service` 在后台跑。这两种方式有个共同的问题：每个 App 各自为政，系统无法协调。结果就是十个 App 可能在同一时刻被闹钟唤醒，CPU 从深度休眠中醒来，一起抢 CPU 时间片，忙完之后各自又进入空闲，CPU 再次休眠。这种"集体醒来又集体睡觉"的模式，对电池的消耗远大于把这些任务合并处理。

Android 5.0 引入了 `JobScheduler`（API 21），它的核心思路是让系统来决定后台任务什么时候跑。开发者只需要告诉系统："我有个任务，需要在充电时、网络连接时执行"，系统就会在合适的时机把多个 App 的任务打包在一起执行。

```java
// 示例：通过 JobScheduler 注册一个后台任务
ComponentName service = new ComponentName(context, MyJobService.class);
JobInfo job = new JobInfo.Builder(JOB_ID, service)
    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED) // 需要 Wi-Fi
    .setRequiresCharging(true)  // 需要充电
    .setPeriodic(24 * 60 * 60 * 1000L) // 每天执行一次
    .build();
```

JobScheduler 并没有强制禁止旧的后台工作方式，它只是一个"更好的选择"。但在后续的版本中，Google 逐步封堵了旧的路径，让 JobScheduler（以及后来基于它的 WorkManager）成为后台工作的唯一正规途径。

[已验证: 官方文档, developer.android.com/reference/android/app/job/JobScheduler]

## Android 6.0：Doze 模式——设备静止时的深度管控

Android 6.0 引入了 Doze 模式，这是 Android 功耗管理的第一个里程碑。它的触发条件很明确：设备拔掉电源、屏幕关闭、保持静止（通过加速度传感器判断）、没有持有长时间 WakeLock。当这些条件同时满足一段时间后，设备进入 Doze 状态。

在 Doze 状态下，系统做的事情核心做法是：**尽可能让 CPU 保持休眠**。具体来说：

- 网络访问被完全禁止
- WakeLock 被忽略
- 标准的 `AlarmManager` 闹钟被推迟（只有 `setAndAllowWhileIdle()` 和 `setExactAndAllowWhileIdle()` 例外）
- Wi-Fi 扫描停止
- SyncAdapter 同步被暂停

但系统并不是一直把 App "冻住"。Doze 采用了一种"维护窗口"机制：设备进入 Doze 后，会周期性地打开一个短暂的窗口，让挂起的任务集中执行。这个窗口的间隔会越来越长——第一次可能在进入 Doze 后的一小时出现，之后逐渐拉长到两小时、四小时……这意味着设备静止时间越长，后台活动越少，省电效果越明显。

[图：Doze 模式周期示意图——展示 Doze 进入→维护窗口→深度休眠的周期]

从 Perfetto 分析的角度，Doze 带来了几个值得关注的现象：如果在 Perfetto 中看到某个时间段内 App 的 CPU 活动完全消失（连 Binder 调用都没有），而设备满足静止条件，很可能就是 Doze 在起作用。通过 `adb shell dumpsys deviceidle` 可以查看 Doze 状态。

[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

### Android 7.0：Doze on the Go——Doze 模式的扩展

Android 7.0 对 Doze 做了一个重要改进：不再要求设备静止。只要设备拔掉电源、屏幕关闭，就会进入一种较轻的 Doze 状态（通常称为 "Light Doze" 或 "Doze on the Go"）。完整版 Doze（Level 2）仍然需要设备静止才能触发。

这个改动直接扩大了 Doze 的覆盖范围。当设备在用户口袋中移动时，系统也能进行一定程度的功耗优化了。

同时，Android 7.0 还启动了 "Project Svelte" 计划的一部分：移除了 `CONNECTIVITY_ACTION`、`ACTION_NEW_PICTURE`、`ACTION_NEW_VIDEO` 等隐式广播。之前每发一个这样的广播，系统中所有注册了接收器的 App 都会被唤醒——哪怕它什么都不需要做。移除这些广播，减少了不必要的 CPU 唤醒。

[已验证: 官方文档, developer.android.com/about/versions/nougat/android-7.0-changes]

### Android 8.0：后台执行限制——后台服务开始受限

Android 8.0 对后台行为的管控上了一个台阶。它引入了"后台执行限制"（Background Execution Limits），核心变化有两个：

第一，**后台 App 不能再随意创建后台服务**。如果一个 App 处于后台（没有可见的 Activity、没有前台服务），调用 `startService()` 会直接抛出 `IllegalStateException`。唯一的出路是使用 `startForegroundService()` 启动一个前台服务——但前台服务必须显示一个持续通知，用户能清楚地知道"有个 App 在后台跑"。

第二，**隐式广播接收器被大幅限制**。除了少数例外，App 无法再在 Manifest 中静态注册大部分隐式广播。这意味着像"网络变化"、"拍照完成"这类事件，不再能唤醒 App。需要在 App 正在运行时动态注册，或者使用 JobScheduler 来响应。

这两个变化让 JobScheduler 从"推荐使用"变成了"事实上的必选项"。如果要做后台工作，JobScheduler（以及后来基于它的 WorkManager）成了最可靠的途径。

[已验证: 官方文档, developer.android.com/about/versions/oreo/background]

## Android 9.0：Adaptive Battery 与 App Standby Buckets——ML 驱动的功耗管理

如果说 Android 6.0 的 Doze 是"一刀切"的静态管控，Android 9.0 引入的 Adaptive Battery 则是"因人而异"的动态策略。Google 与 DeepMind 合作，用一个设备端的机器学习模型来预测用户在未来几小时内会使用哪些 App。

基于这个预测，系统把每个 App 放入五个"待机桶"（App Standby Buckets）之一：

| 桶 | 含义 | 典型限制 |
|---|---|---|
| Active | 正在使用或刚使用 | 无限制 |
| Working Set | 经常使用但当前不在前台 | Jobs 和闹钟有少量限制 |
| Frequent | 定期使用但不是每天 | Jobs 和闹钟有较多限制，网络访问受限 |
| Rare | 很少使用 | Jobs 和闹钟严格限制，网络访问严重受限 |
| Restricted | 从未运行或被系统限制 | 几乎所有后台活动被禁止 |

关键在于：**桶的分配不是固定不变的**。系统会根据用户的使用习惯实时调整。一个上周天天用的 App，如果这周没碰过，会逐步从 Active 降级到 Rare。反过来，一个长期在 Rare 桶的 App，如果用户突然开始使用，会迅速升回 Active。

从性能分析的角度，通过 `adb shell am get-standby-bucket <package_name>` 可以查看某个 App 当前的桶分配。如果在 Perfetto 中发现某个 App 的 JobScheduler 任务长时间不执行，先检查它的 Standby Bucket——很可能被放到了 Rare 或 Restricted。

[已验证: 官方文档, developer.android.com/topic/performance/appstandby]

这个机制的实际影响：App 的后台行为频率不完全由开发者代码决定，而是由用户习惯和系统的 ML 模型共同决定。同一个 App，在重度用户的手机上和在偶尔打开的用户的手机上，后台任务的执行频率可能相差数倍。

## Android 10：EAS 成为默认调度策略

前面几个版本我们讲的都是系统层面对 App 后台行为的约束。Android 10 在更底层做了一件重要的事：**EAS（Energy Aware Scheduling）成为内核调度的默认策略**。

我们在 5.2 节详细讲了 EAS 的工作原理，这里重点说它从"可选"变成"默认"意味着什么。

EAS 的核心是在 CFS（Completely Fair Scheduler）的基础上加入能量模型。当调度器需要决定把一个任务放在大核还是小核上时，它不再只看哪个核心有空闲，而是计算"这个任务在大核上跑 2ms 和小核上跑 5ms，哪个更省电"。在大.LITTLE 架构的 SoC 上（也就是几乎所有现代手机芯片），这个决策每时每刻都在发生。

EAS 早在 2016 年就合入了 Android Common Kernel，但到 Android 10 才正式成为默认策略。原因是它需要硬件厂商提供准确的能量模型数据（EM，Energy Model），如果模型不准，调度器可能做出更差的决定——比如把所有任务都塞到小核上，导致性能下降。

EAS 成为默认的意义在于：

- **对 App 开发者**：App 的线程调度，从"哪个核心空闲去哪个"变成了"综合考虑性能和功耗的最优选择"。同样的代码在 Android 10 上可能比 Android 9 跑得慢一点点（因为系统优先省电），但整体功耗会下降。
- **对系统工程师**：在做性能分析时，不能只看 CPU 频率和利用率，还要结合 EAS 的调度决策来理解为什么任务被分配到了特定的核心。在 Perfetto 中，可以通过 CPU 调度 Track 观察任务的迁移模式。

[已验证: ARM 官方文档 - EAS, source.android.com/docs/core/power]

### Android 10 的其他功耗相关变化

Android 10 还做了两件值得注意的事：

第一，**限制了后台 App 启动 Activity 的能力**。如果一个 App 在后台，它不能直接弹出界面。取而代之的方式是发一个高优先级通知，让用户主动点击。这减少了后台 App 意外弹窗带来的 CPU 和 GPU 消耗。

第二，**引入了"使用中"（while-in-use）位置权限模型**。后台 App 获取位置信息变得更困难，需要用户显式授予 `ACCESS_BACKGROUND_LOCATION` 权限。这个变化间接减少了后台 App 的工作量。

[已验证: 官方文档, developer.android.com/about/versions/10/privacy/changes]

## Android 12+：对精确闹钟、前台服务、后台启动的持续限制

从 Android 12 开始，Google 对后台行为的管控进入了一个新的阶段——不再是大框架的改变，而是对每一个"后门"逐一封堵。这一阶段的特征是：权限管控精细化、前台服务类型化、后台网络访问受限。

### Android 12：精确闹钟需要权限

Android 12 引入了 `SCHEDULE_EXACT_ALARM` 权限。在此之前，任何 App 都可以通过 `AlarmManager.setExact()` 或 `setExactAndAllowWhileIdle()` 设置精确闹钟，这个闹钟会绕过 Doze 模式精确触发——换句话说，它可以在任何时间唤醒 CPU。

从 Android 12 开始，如果要使用精确闹钟 API（`setExact()`、`setExactAndAllowWhileIdle()`、`setAlarmClock()`），必须在 Manifest 中声明这个权限。不声明的话，调用会直接抛出 `SecurityException`。

对于闹钟类 App 和日历类 App，Google Play 提供了一个更宽松的替代权限 `USE_EXACT_ALARM`（Android 13 引入），这是一个普通权限，安装时自动授予。但 Google Play 会对声明了这个权限的 App 进行政策审查。

同时，Android 12 对后台启动前台服务也做了限制。如果 App 处于后台（有少数豁免场景），调用 `startForegroundService()` 会抛出 `ForegroundServiceStartNotAllowedException`。

[已验证: 官方文档, developer.android.com/about/versions/12/behavior-changes-12#exact-alarm-permission]

### Android 13：精确闹钟默认拒绝 + FGS Task Manager

Android 13 把精确闹钟的管控又推进了一步：对于 `targetSdkVersion >= 33` 的 App，`SCHEDULE_EXACT_ALARM` 权限**默认拒绝**。App 需要通过 `AlarmManager.canScheduleExactAlarms()` 检查权限状态，如果未授予，引导用户到系统设置页面手动开启。

此外，Android 13 引入了前台服务任务管理器（FGS Task Manager），用户可以在通知栏直接看到哪些 App 正在运行前台服务，并且可以手动停止。这让用户对后台活动有了前所未有的可见性和控制力。

[已验证: 官方文档, developer.android.com/about/versions/13/behavior-changes-13]

### Android 14：前台服务类型化 + 后台 Activity 启动需显式 opt-in

Android 14 要求前台服务必须声明**至少一个类型**（foreground service type），比如 `camera`、`location`、`mediaPlayback` 等。每种类型对应不同的权限要求和系统行为。这让系统可以更精准地管理不同类型的前台服务——比如一个声称在做媒体播放的前台服务，如果实际上没有在播放音频，系统可以检测到并终止它。

Android 14 还引入了后台 Activity 启动的显式 opt-in 机制：当 App 通过 `PendingIntent` 启动 Activity 时，必须显式声明 `PendingIntent.FLAG_MUTABLE` 或在发送方 opt-in 授予后台启动权限。这是为了防止 App 利用 PendingIntent 链绕过后台启动限制。

此外，`mlock()` 的上限从 64MB 降到了 64KB，这对某些使用内存锁定来优化性能的 App 是一个需要注意的变化。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14]

### Android 15：后台网络访问受限 + Doze 加速

Android 15 在两个方面做了重要改进：

**后台网络访问被限制**：如果一个 App 在 `Activity.onStop()` 之后不久发起网络请求（即 App 进入了缓存或后台状态），系统会返回 `UnknownHostException`。这意味着从 Android 15 开始，后台网络操作必须通过 `WorkManager` 或前台服务来执行。直接在后台线程中做网络请求变得不可靠了。

**Doze 激活速度提升 50%**：设备进入 Doze 模式的速度比 Android 14 快了一倍。根据 Google 的数据，这可以带来最多 3 小时的额外待机时间。这个变化不需要开发者做任何适配，但对后台任务的时间窗口有影响——App 可能比以前更早被 Doze "冻住"。

[已验证: 官方文档, developer.android.com/about/versions/15/behavior-changes-15]

### [自动发现: 来源 web search - Android developer docs] Android 16：JobScheduler 配额优化

Android 16 继续对 JobScheduler 进行精细化管控。核心变化是 Job 的执行时间配额（runtime quota）现在不仅取决于 App 的 Standby Bucket，还取决于：

- Job 是在 App 可见时启动并延续到后台，还是在 App 完全后台时启动
- Job 是否与前台服务并发执行
- App 当前的 Standby Bucket 的具体分数

具体来说：一个在前台启动、用户正在交互时发起的 Job，会获得更多的执行时间；而一个在后台静默启动的 Job，执行时间会更短。同时，Android 16 提供了更好的诊断工具，开发者可以通过 API 查询 Job 为什么没执行或被停止。

[待验证: Android 16 仍处于 beta 阶段，最终行为可能变化]

## GKI 对内核调度模块定制化的影响

[扩展素材]

GKI（Generic Kernel Image）从 Android 11 开始引入，到 Android 15 成为强制要求。它对 CPU 调度的影响是一个容易被忽视但很重要的变化。

在 GKI 之前，SoC 厂商（高通、联发科等）可以直接修改内核调度器代码来适配自己的硬件。比如联发科可以在 CFS 中加入针对天玑芯片大小核架构的特殊优化，高通可以为骁龙的调度策略写定制代码。这种做法的代价是内核碎片化——每家厂商的内核都是"自己的版本"，安全补丁和调度器改进很难统一推送。

GKI 的核心思路是：**内核是统一的标准版本，厂商的定制化通过可加载模块和 Vendor Hook 实现**。具体到调度方面：

1. **厂商不能直接修改 CFS/EAS 的核心代码**。GKI 内核是 Google 编译的统一二进制，厂商只能在此基础上加载模块。

2. **通过 Vendor Hook 注入定制逻辑**。GKI 2.0（内核 5.10+）引入了一系列 vendor hook，基于内核 tracepoint 实现。厂商可以通过这些 hook 在调度决策的关键节点注入自己的逻辑，比如：
   - `sched_exit()`：任务退出时的统计
   - `uclamp_eff_value`：修改 EAS 中 uclamp（utilization clamping）的有效值
   - `cpu_overutilized`：判断 CPU 是否"过载"
   - `balance_rt()`：实时任务的负载均衡

3. **eBPF 和 sched_ext 提供了新的扩展路径**。Linux 6.6+ 引入的 `sched_ext` 机制允许通过 eBPF 程序实现自定义调度策略。这意味着厂商可以在不修改内核代码的情况下，用 eBPF 写出"游戏模式"或"省电模式"的调度策略。

对性能分析的影响：在分析不同厂商设备的调度行为差异时需要注意这些差异不是来自内核版本的不同，而是来自 Vendor Hook 注入的定制逻辑。同样运行 Android 15 的骁龙和天玑设备，同一个 App 的任务可能被分配到不同的核心上。

[已验证: source.android.com/docs/core/architecture/kernel/gki]

## 版本演进全景时间线

把以上内容用一条时间线串起来，我们可以看到 Google 在 CPU/功耗管理上的策略是一脉相承的：**逐步限制 App 对 CPU 的自主使用权，让系统来做决策**。

| 版本 | 核心变化 | 约束层面 |
|------|---------|---------|
| 5.0 | JobScheduler 引入 | 应用层（推荐） |
| 6.0 | Doze 模式 | 系统策略层（静态） |
| 7.0 | Doze on the Go + 移除隐式广播 | 系统策略层 |
| 8.0 | 后台执行限制 | 应用层（强制） |
| 9.0 | Adaptive Battery + App Standby Buckets | 系统策略层（ML 驱动） |
| 10 | EAS 默认启用 + 后台 Activity 限制 | 内核层 + 应用层 |
| 11 | 后台位置权限收紧 | 应用层 |
| 12 | SCHEDULE_EXACT_ALARM + FGS 启动限制 | 应用层（权限化） |
| 13 | 精确闹钟默认拒绝 + FGS Task Manager | 应用层（用户可见） |
| 14 | FGS 类型化 + 后台 Activity opt-in | 应用层（类型化） |
| 15 | 后台网络受限 + Doze 加速 50% | 应用层 + 系统策略层 |
| 16 | JobScheduler 配额优化 | 系统策略层（精细化） |

可以看到三个趋势：

1. **约束越来越严格**：从推荐使用 JobScheduler（5.0），到限制后台服务（8.0），到限制精确闹钟（12-13），到限制后台网络（15）。每一步都在封堵"App 自己控制 CPU"的路径。
2. **策略越来越智能**：从静态的 Doze（6.0），到 ML 驱动的 Adaptive Battery（9.0），到动态 Standby Bucket 打分（15）。系统越来越擅长根据用户行为做决策。
3. **用户可见性越来越高**：前台服务通知（8.0）→ FGS Task Manager（13）→ 后台网络异常提示（15）。用户对"哪些 App 在用 CPU"的了解越来越清晰。

## 在 Perfetto 中的观察

当在 Perfetto 中分析 CPU 相关行为时，可以通过以下维度观察版本演进带来的差异：

1. **Doze 状态**：在设备空闲时段，检查 CPU 是否有长时间的无活动期（对应 Doze 深度休眠）。Android 15 的 Doze 加速意味着这个无活动期开始得更早。

2. **任务迁移模式**：对比不同 Android 版本上同一 App 的 CPU 调度 Track。在 EAS 启用前（Android 9 及更早），任务迁移更"随机"；EAS 启用后（Android 10+），可以看到更多"把轻量任务集中到小核"的规律性模式。

3. **JobScheduler 执行**：在 Android 12+ 上，Job 的执行间隔明显更不规律，特别是 Rare 桶的 App。可以通过 System Server 进程中的 JobScheduler track 观察任务的调度和执行情况。

4. **WakeLock 持有时间**：Doze 模式下 WakeLock 被忽略，所以在 Perfetto 中可能会看到 WakeLock 被 acquire 后很久才被 release，但这期间 CPU 并没有实际活动——因为 Doze 覆盖了 WakeLock 的效果。

[待补充：不同版本 Perfetto Trace 截图对比]

## 常见问题与误区

### "我的后台任务在 Android 12 上突然不工作了"
最大可能：使用了精确闹钟但没有声明 `SCHEDULE_EXACT_ALARM` 权限，或者 App 被放到了 Restricted 桶。检查 `adb shell am get-standby-bucket` 和 `adb shell dumpsys alarm`。

### "EAS 让我的 App 变慢了"
不完全是。EAS 可能会让某些场景下的单次执行时间变长（因为任务被放到了小核），但整体功耗下降。如果 App 对延迟敏感，可以通过设置线程的 uclamp 值来告诉调度器"这个线程需要高性能"，EAS 会尊重这个提示。

### "Doze 模式下我的推送收不到"
FCM（Firebase Cloud Messaging）高优先级消息可以绕过 Doze。如果推送走的是自有长连接，在 Doze 下确实会被延迟。建议将关键推送迁移到 FCM 高优先级通道。

### "不同厂商的设备，后台限制不一样"
确实如此。虽然 AOSP 定义了基础规则，但很多厂商（尤其是中国市场的厂商）会在 AOSP 基础上叠加自己的省电策略。这就是为什么同一个 App 在 Pixel 上表现正常，在某些国产设备上后台被杀。可以参考 [dontkillmyapp.com](https://dontkillmyapp.com/) 了解各厂商的差异。

## 参考资料

- [Android 6.0 Changes - Doze](https://developer.android.com/about/versions/marshmallow/android-6.0-changes) [已验证: 官方文档]
- [Android 9 Power Management](https://developer.android.com/about/versions/pie/power) [已验证: 官方文档]
- [Android 12 Behavior Changes - Exact Alarms](https://developer.android.com/about/versions/12/behavior-changes-12) [已验证: 官方文档]
- [Android 13 Behavior Changes](https://developer.android.com/about/versions/13/behavior-changes-13) [已验证: 官方文档]
- [Android 14 Behavior Changes - FGS Types](https://developer.android.com/about/versions/14/behavior-changes-14) [已验证: 官方文档]
- [Background Execution Limits (Android 8.0)](https://developer.android.com/about/versions/oreo/background) [已验证: 官方文档]
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby) [已验证: 官方文档]
- [Energy Aware Scheduling - ARM Documentation](https://developer.arm.com/documentation/den0024/latest) [已验证: ARM 官方文档]
- [GKI - Generic Kernel Image](https://source.android.com/docs/core/architecture/kernel/gki) [已验证: source.android.com]
- [sched_ext - LWN.net](https://lwn.net/Articles/922405/) [已验证: LWN]
- [Android 15 Behavior Changes](https://developer.android.com/about/versions/15/behavior-changes-15) [已验证: 官方文档]
- [JobScheduler Reference](https://developer.android.com/reference/android/app/job/JobScheduler) [已验证: 官方文档]
- AOSP 路径参考：
  - `frameworks/base/services/core/java/com/android/server/DeviceIdleController.java` — Doze 模式实现
  - `frameworks/base/services/core/java/com/android/server/usage/AppStandbyController.java` — App Standby Buckets 实现
  - `frameworks/base/services/core/java/com/android/server/job/JobSchedulerService.java` — JobScheduler 服务
  - `kernel/sched/fair.c` — CFS/EAS 调度器核心代码
