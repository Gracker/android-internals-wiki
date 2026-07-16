---



title: CPU 相关的版本演进
chapter: '5.7'
section: '5.7'
status: finalized
reviewed_at: '2026-05-16T12:20:36+08:00'
last_task6_at: '2026-06-04T07:05:00+08:00'
last_task6_audit: "2026-07-17T04:09:00+08:00"
review_round: 2
task6_review_notes: '2026-06-04 task6 revisiting-review: pass-light-edit。L1/L2 全部通过(禁用词0/AI套话0/高频词全0/元叙述0)。无B类大问题。自动晋升 finalized(task9 auto-fixed + queue 无 pending + 本次无B类大问题)。'
applicable_versions: Android 5.0 - Android 17
last_verified: '2026-06-04'
last_verified_against: developer.android.com Android 17 behavior/features + source.android.com + AOSP android-17.0.0_r1
  + android15-6.6.98_r00 + Arm MTE docs
confidence: medium
sources:
- type: official
  path: developer.android.com/about/versions/marshmallow/android-6.0-changes
- type: official
  path: developer.android.com/about/versions/pie/power
- type: official
  path: developer.android.com/about/versions/12/behavior-changes-12
- type: official
  path: developer.android.com/develop/background-work/services/alarms
- type: official
  path: developer.android.com/about/versions/15/behavior-changes-all
- type: official
  path: source.android.com/docs/core/power
- type: official
  path: source.android.com/docs/core/perf/cgroups
- type: blog
  path: ARM documentation - Energy Aware Scheduling
- type: aosp
  path: platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java
- type: aosp
  path: platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java
- type: aosp
  path: platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java
- type: aosp
  path: platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: platform/system/core/+/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json
- type: aosp
  path: platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java
- type: official
  path: developer.android.com/ndk/guides/arm-mte
- type: official
  path: source.android.com/docs/security/test/memory-safety/arm-mte
- type: aosp
  path: kernel/common/+/refs/tags/android15-6.6.98_r00/include/trace/hooks/sched.h
tags:
- android
- power
- cpu-scheduling
- doze
- eas
- job-scheduler
- gki
polish_count: 1
drafted_date: '2026-04-01'
related_chapters:
- 5.2 EAS 能量感知调度
- 5.6 Android 功耗管理
- 5.8 后台执行限制与优化
repaired_date: '2026-04-30'
repaired_by: openclaw-task2b
rework_type: review回炉修复(Task9/External 问题单)
reviewed_date: 2026-06-04
reviewed_by: openclaw-task6
task6_reviewed_date: "2026-06-04"
task6_result: pass-light-edit
task6_state: reviewed
last_task2b_at: '2026-04-30T10:46:19+08:00'
review_notes: '2026-05-12 task9 deep-review: needs-rework。P1 2 / P2 1，精确闹钟版本与 sched_ext 版本锚点需回炉。'
task9_result: auto-fixed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
task9_reviewed_date: "2026-06-04"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-04T06:48:42+08:00"
task9_review_notes: "2026-06-04 task9 deep-review: auto-fixed。补 Android 17 JobScheduler reason stats（Map<Integer, Duration>），修正 Android 17 证据来源边界。"
last_task2b_lite_at: "2026-06-04"
last_task9_autofix_at: "2026-06-04"
last_task9_review_log: "logs/deep-review/2026-06-04-06-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-04
verifier_last_checked: "2026-07-15T23:27:58+08:00"
verifier_result: "state-consistency-fixed: task6_state/task9_state/pipeline_stage aligned with finalized"
---


# CPU 相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 Android 5.0+ 引入 JobScheduler 优化后台功耗
- 🔹 Android 6.0 Doze 模式引入
- 🔹 Android 9.0 Adaptive Battery + App Standby Buckets
- 🔹 Android 10 时期 EAS 成为主流调度路线
- 🔹 Android 12+ 对精确闹钟、前台服务、后台启动的持续限制

### 扩展(可选深入)

- 🔸 GKI 对内核调度模块定制化的影响
- 🔸 Android 16 功耗与调度相关的新变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 CPU 相关的版本演进

做过 Android 性能优化的工程师，很可能遇到过这种情况：App 在 Android 10 上跑得很好，到了 Android 12 突然后台任务不执行了；或者用 AlarmManager 设了一个精确闹钟，结果在 Android 13 上没有触发。这些行为的变化来自 Google 在不同版本里逐步加严后台行为限制。

从 Android 5.0 到 Android 16,Google 围绕 CPU 和功耗管理做了一系列层层递进的改动。这些改动覆盖了三个层面:

1. **内核调度层面**：从传统 CFS 到 EAS（Energy Aware Scheduling），再到 GKI 对调度定制化的约束
2. **系统策略层面**：Doze 模式、App Standby Buckets、Adaptive Battery——系统越来越“聪明”地决定哪些 App 可以用 CPU，哪些必须等着
3. **应用约束层面**：JobScheduler 引入 → 后台服务限制 → 精确闹钟管控 → 前台服务类型化——App 能做的事情越来越受限

理解这条演进线，我们就能回答：为什么我的后台任务在某个版本突然不工作了？为什么同样的代码在不同设备上表现不一样？做功耗优化时，应该关注哪些系统机制的变化？

这条时间线从 Android 5.0 的 JobScheduler 开始。

> **交叉引用**:本节聚焦版本间的变化脉络。EAS 的调度原理详见 §5.2,Android 整体功耗管理框架详见 §5.6,后台执行限制的实战分析详见 §5.8。

## Android 5.0：JobScheduler —— 后台任务批处理的开端

在 Android 5.0 之前,开发者要做后台工作,主要有两个选择:用 `AlarmManager` 定时唤醒,或者直接起一个 `Service` 在后台跑。这两种方式有个共同的问题:每个 App 各自为政,系统无法协调。结果就是十个 App 可能在同一时刻被闹钟唤醒,CPU 从深度休眠中醒来,一起抢 CPU 时间片,忙完之后各自又进入空闲,CPU 再次休眠。这种"集体醒来又集体睡觉"的模式,对电池的消耗远大于把这些任务合并处理。

Android 5.0 引入了 `JobScheduler`（API 21），它的核心思路是让系统来决定后台任务什么时候跑。开发者只需要告诉系统：“我有个任务，需要在充电时、网络连接时执行”，系统就会在合适的时机把多个 App 的任务打包在一起执行。

```java
// 示例:通过 JobScheduler 注册一个后台任务
ComponentName service = new ComponentName(context, MyJobService.class);
JobInfo job = new JobInfo.Builder(JOB_ID, service)
    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED) // 需要 Wi-Fi
    .setRequiresCharging(true)  // 需要充电
    .setPeriodic(24 * 60 * 60 * 1000L) // 每天执行一次
    .build();
```

JobScheduler 并没有强制禁止旧的后台工作方式,它只是一个"更好的选择"。但在后续的版本中,Google 逐步封堵了旧的路径,让 JobScheduler（以及后来基于它的 WorkManager）成为后台工作的唯一正规途径。

[已验证: 官方文档, developer.android.com/reference/android/app/job/JobScheduler]

## Android 6.0：Doze 模式 —— 设备静止时的深度管控

Android 6.0 引入了 Doze 模式,这是 Android 功耗管理的第一个里程碑。它的触发条件是设备拔掉电源、屏幕关闭、保持静止(通过加速度传感器判断)。当这些条件同时满足一段时间后,设备进入 Doze 状态。

在 Doze 状态下,系统的做法是:**尽可能让 CPU 保持休眠**。具体来说:

- 网络访问被完全禁止
- WakeLock 被忽略
- 标准的 `AlarmManager` 闹钟被推迟(只有 `setAndAllowWhileIdle()` 和 `setExactAndAllowWhileIdle()` 例外)
- Wi-Fi 扫描停止
- SyncAdapter 同步被暂停

但系统并不是一直把 App "冻住"。Doze 采用了一种"维护窗口"机制:设备进入 Doze 后,会周期性地打开一个短暂的窗口,让挂起的任务集中执行。这个窗口的间隔会越来越长--第一次可能在进入 Doze 后的一小时出现,之后逐渐拉长到两小时、四小时......设备静止时间越长,后台活动越少,省电效果也越明显。

[图:Doze 模式周期示意图--展示 Doze 进入→维护窗口→深度休眠的周期]

从 Perfetto 分析的角度,Doze 带来了几个值得关注的现象:如果在 Perfetto 中看到某个时间段内 App 的 CPU 活动完全消失(连 Binder 调用都没有),而设备满足静止条件,很可能就是 Doze 在起作用。通过 `adb shell dumpsys deviceidle` 可以查看 Doze 状态。

[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

### Android 7.0：Doze on the Go —— Doze 模式的扩展

Android 7.0 对 Doze 做了一个重要改进:不再要求设备静止。只要设备拔掉电源、屏幕关闭,就会进入一种较轻的 Doze 状态(通常称为 "Light Doze" 或 "Doze on the Go")。完整版 Doze(Level 2)仍然需要设备静止才能触发。

这个改动直接扩大了 Doze 的覆盖范围。当设备在用户口袋中移动时,系统也能进行一定程度的功耗优化了。

同时,Android 7.0 还启动了 "Project Svelte" 计划的一部分:移除了 `CONNECTIVITY_ACTION`、`ACTION_NEW_PICTURE`、`ACTION_NEW_VIDEO` 等隐式广播。之前每发一个这样的广播,系统中所有注册了接收器的 App 都会被唤醒--哪怕它什么都不需要做。移除这些广播,减少了不必要的 CPU 唤醒。

[已验证: 官方文档, developer.android.com/about/versions/nougat/android-7.0-changes]

### Android 8.0：后台执行限制 —— 后台服务开始受限

Android 8.0 对后台行为的管控上了一个台阶。它引入了"后台执行限制"(Background Execution Limits),核心变化有两个:

第一,**后台 App 不能再随意创建后台服务**。如果一个 App 处于后台(没有可见的 Activity、没有前台服务),调用 `startService()` 会直接抛出 `IllegalStateException`。唯一的出路是使用 `startForegroundService()` 启动一个前台服务--但前台服务必须显示一个持续通知,用户能清楚地知道"有个 App 在后台跑"。

第二,**隐式广播接收器被大幅限制**。除了少数例外,App 无法再在 Manifest 中静态注册大部分隐式广播。像"网络变化"、"拍照完成"这类事件,不再能唤醒 App。需要在 App 正在运行时动态注册,或者使用 JobScheduler 来响应。

这两个变化让 JobScheduler 从"推荐使用"逐渐变成了"基本必选"。如果要做后台工作,JobScheduler（以及后来基于它的 WorkManager）成了更稳妥的途径。

[已验证: 官方文档, developer.android.com/about/versions/oreo/background]

## Android 9.0：Adaptive Battery 与 App Standby Buckets —— ML 驱动的功耗管理

如果说 Android 6.0 的 Doze 是"一刀切"的静态管控,Android 9.0 引入的 Adaptive Battery 则是"因人而异"的动态策略。Google 与 DeepMind 合作,用一个设备端的机器学习模型来预测用户在未来几小时内会使用哪些 App。

基于这个预测,系统会先把 App 放入一组有先后顺序的 priority buckets:Active、Working Set、Frequent、Rare、Restricted。它们决定 Job、Alarm 和网络访问会被推迟到什么程度。AOSP 在 `UsageStatsManager.java` 里还定义了一个 special bucket,`STANDBY_BUCKET_NEVER = 50`,表示"已安装但从未启动"。这个桶不参与日常的 priority 排序,但它解释了为什么新装后从未打开的 App 会比 Rare 还安静。

| 桶 | 含义 | 典型限制 |
|---|---|---|
| Active | 正在使用、刚使用,或者系统预测很快会被使用 | 基本不受限 |
| Working Set | 最近用过,未来几小时仍可能被用到 | Job 和 Alarm 会有轻度延后 |
| Frequent | 最近几天用过,但不是高频 App | Job、Alarm 延后更明显,部分后台网络会受限 |
| Rare | 多天未使用 | 只在较少的维护窗口中运行后台任务 |
| Restricted* | 长时间不活跃，或者资源消耗异常、行为异常 | 约束最重，Job、Alarm、网络访问都会进一步加严 |

\* `STANDBY_BUCKET_RESTRICTED = 45` 在 Android 9（API 28）中不存在，AOSP `android-9.0.0_r61` 的 `UsageStatsManager` 只定义到 `STANDBY_BUCKET_RARE = 40`。Restricted bucket 从 Android 12（API 31）起加入。表格按最新常量列出以展示完整演进，但 Android 9 设备上只有 Active / Working Set / Frequent / Rare 四个桶。

这里最容易写错的地方有两个。第一,Restricted 不是"从未运行",这个语义属于 Never bucket。第二,Restricted 的触发条件在不同 Android 版本里有调整,既看最近是否被使用,也看系统是否认定它存在异常耗电或异常行为,所以文档里更适合把它写成"更严格的后台限制状态",不要写成单一原因。

从性能分析的角度,通过 `adb shell am get-standby-bucket <package_name>` 可以查看某个 App 当前的桶分配。App 内也可以通过 API 查询自己的桶状态:

```java
UsageStatsManager usm = getSystemService(UsageStatsManager.class);
int bucket = usm.getAppStandbyBucket();
// ACTIVE = 10, WORKING_SET = 20, FREQUENT = 30, RARE = 40
// Android 12+ 新增 RESTRICTED = 45; @SystemApi STANDBY_BUCKET_NEVER = 50
```

如果在 Perfetto 中发现某个 App 的 JobScheduler 任务长时间不执行,先检查它的 Standby Bucket。Rare、Restricted,或者从未启动过的 Never,都可能解释为什么后台任务几乎没有运行机会。

[已验证: 官方文档 developer.android.com/topic/performance/appstandby;AOSP android-17.0.0_r1 frameworks/base/core/java/android/app/usage/UsageStatsManager.java]

这个机制的实际影响:App 的后台行为频率不完全由开发者代码决定,而是由用户习惯和系统的 ML 模型共同决定。同一个 App,在重度用户的手机上和在偶尔打开的用户的手机上,后台任务的执行频率可能相差数倍。

## Android 10:EAS 成为主流调度路线

前面几个版本讲的是系统如何约束 App 的后台活动。Android 10 这一阶段,调度器本身也在变。EAS 在 Android 10 时期成为 big.LITTLE 设备的主流路线,很多新设备把它作为默认选择,但前提是内核已经具备 Energy Model、相关 kernel config,厂商 bringup 也把参数校准完成。

我们在 §5.2 详细拆过 EAS 的工作方式,这里只看版本演进带来的变化。EAS 把能量模型接到 CFS 调度决策里。调度器在选择 CPU 时,不只看哪个核心空闲,还会估算不同 CPU 上的能耗和完成时间,然后在性能与功耗之间取一个更合适的点。

这也是为什么"Android 10 默认启用 EAS"这句话不能写得太满。没有 Energy Model,或者厂商没有把 capacity、frequency、util 这一套参数校准好,设备仍可能继续使用更传统的调度方案,或者只启用部分能力。做跨设备 Perfetto 对比时,如果一个 Android 10 设备明显偏向小核、另一个却没有这种特征,排查时先确认内核配置和厂商 bringup,再检查 App 代码。

对 App 开发者来说,同一段工作负载在不同设备上的落核位置可能不同。对系统工程师来说,CPU frequency、CPU idle state、task migration 和 uclamp 提示要一起看,单看利用率很容易误判。

[已验证: ARM EAS 文档;source.android.com/docs/core/power]

### Android 10 的其他功耗相关变化

Android 10 还做了两件和功耗直接相关的改动:

第一,**限制了后台 App 启动 Activity 的能力**。如果一个 App 在后台,它不能直接弹出界面。取而代之的方式是发一个高优先级通知,让用户主动点击。这减少了后台 App 意外弹窗带来的 CPU 和 GPU 消耗。

第二,**引入了"使用中"(while-in-use)位置权限模型**。后台 App 获取位置信息变得更困难,需要用户显式授予 `ACCESS_BACKGROUND_LOCATION` 权限。这个变化间接减少了后台 App 的工作量。

[已验证: 官方文档, developer.android.com/about/versions/10/privacy/changes]

以上是应用层约束的演进。在硬件层面，ARM 架构版本的迭代也给 Android App 带来了新的能力分化，主要体现在向量指令和内存标记两方面。

## [自动发现] ARMv8.5 / ARMv9:SVE2 与 MTE 对 App 的影响

ARMv9 进入手机后,Android App 主要受到两类硬件能力分化影响:向量指令和内存标记。

SVE2 面向 native 热点路径,典型受益场景是图像处理、音频 DSP、加解密、ML 前后处理这类循环密集代码。它不是 Java / Kotlin 层直接调用的 Android API;NDK 代码要做运行时能力检测,并保留 NEON 或标量 fallback。不同 SoC 是否暴露 SVE / SVE2 能力差异很大,不能按 Android 版本直接判断。

MTE (Memory Tagging Extension)由 Armv8.5-A 引入,Android 在支持硬件的设备上通过 `android:memtagMode` 控制 App 或进程的 native 内存标记检查。`sync` 模式更适合调试,能在 tag mismatch 附近给出精确崩溃;`async` / `asymm` 更偏低开销监控,但崩溃点可能滞后到后续 kernel entry。MTE 的目标是内存安全,不应被当成性能优化开关;开启前要在目标机型上用 Perfetto / simpleperf 复测 CPU、启动耗时和 native 崩溃率。

这条演进和调度策略不是同一层。Perfetto 能帮助观察 MTE 开启后的线程时序、崩溃前后 CPU 状态和启动耗时变化;tag mismatch 的直接证据仍然来自 tombstone / logcat / crash report。SVE2 的收益则要通过 native benchmark、simpleperf 热点和硬件能力检测一起确认。

[已验证: developer.android.com/ndk/guides/arm-mte;source.android.com/docs/security/test/memory-safety/arm-mte;Arm Architecture Reference Manual]

讲完调度器选核策略（EAS）和硬件能力（ARM 扩展），中间还缺一层：线程的性能意图怎么传给调度器。下面这个 [自动发现] 段落补的就是这条连接路径。

## [自动发现] Android 11-15:schedtune 退场,uclamp 与 task profiles 进入主线

如果只记住 EAS 和 GKI,中间会少掉最关键的一层,线程的性能意图怎么传到调度器。Android 10 之前,很多设备习惯用 schedtune 和一组厂商自定义 cgroup boost 做前台、后台、Top App 的差异化调度。到 Android 11 之后,AOSP 开始把这类策略收敛到 `libprocessgroup` 和 `task_profiles.json` 这一套统一接口里。

`task_profiles.json` 的作用很直接,框架给进程或线程打上 profile,`libprocessgroup` 再把这个 profile 展开成具体的 cgroup、cpuset、timer slack 和 uclamp 操作。到了 android-17.0.0_r1,文件里已经能直接看到 `UClampMin -> cpu.uclamp.min`、`UClampMax -> cpu.uclamp.max` 这样的映射。也就是说,线程"至少要拿到多高的算力""最多只能吃到多少 CPU",在这一层就已经被写成了调度器能直接消费的参数。

这段演进把 §5.2 和 §5.9 串了起来。§5.2 讲的是 EAS 怎么做 CPU 选择,§5.9 讲的是 ADPF / PerformanceHint 怎么让 App 报告自己的工作节奏。它们之间还隔着一层系统策略,hint session、task profile、uclamp、cpuset。PerformanceHintManager / ADPF 提供的是 work duration hint,本身不等于调度参数。系统或厂商策略需要把这些 hint 转成更低层的线程分组、uclamp 调整或 cpuset 选择,调度器才会看到差异。

对排查工作也有直接帮助。如果一个线程明明负载不高,却总被放在大核上,或者一直被压在小核,别只盯着 EAS 算法。先看它当前属于什么 task profile,再看对应 profile 有没有给 `cpu.uclamp.min`、`cpu.uclamp.max` 或 cpuset 施加限制。很多"调度器好像失灵了"的问题，通常不是 `fair.c` 算错，而是策略层先把范围框好了。

[已验证: source.android.com/docs/core/perf/cgroups;AOSP android-17.0.0_r1 platform/system/core/libprocessgroup/profiles/task_profiles.json]

## Android 12+:对精确闹钟、前台服务、后台启动的持续限制

从 Android 12 开始,Google 对后台行为的管控进入了一个新的阶段--不再是大框架的改变,而是对每一个"后门"逐一封堵。这一阶段的特征是:权限管控精细化、前台服务类型化、后台网络访问受限。

### Android 12：精确闹钟进入特殊访问控制

Android 12 把精确闹钟纳入 "Alarms & reminders" 特殊访问。走 `PendingIntent` 形态的 exact alarm,比如 `setExact()`、`setExactAndAllowWhileIdle()`、`setAlarmClock()`,通常需要声明 `SCHEDULE_EXACT_ALARM`,并在运行时确认 `canScheduleExactAlarms()` 为 `true`。缺少这项访问时,相关调用会失败。

一个容易漏掉的边界是，官方文档明确写到，如果 exact alarm 走 `OnAlarmListener` 形态，例如 `setExact()` 的 listener 变体，则不需要 `SCHEDULE_EXACT_ALARM`。排查权限问题时，要先区分调用形态，再看权限状态。

Android 13 起,闹钟类、日历类这类场景还可以声明 `USE_EXACT_ALARM`。它是普通权限,安装时授予,但受 Google Play 政策限制,只适用于少数类别,不能当成通用替代方案。

同时,Android 12 对后台启动前台服务也做了限制。如果 App 处于后台(有少数豁免场景),调用 `startForegroundService()` 会抛出 `ForegroundServiceStartNotAllowedException`。

[已验证: 官方文档, developer.android.com/develop/background-work/services/alarms;developer.android.com/about/versions/12/behavior-changes-12#exact-alarm-permission]

### Android 13：USE_EXACT_ALARM 权限 + FGS Task Manager

Android 13 新增了 `USE_EXACT_ALARM` 普通权限(安装时授予),面向闹钟、日历等特定类别应用，作为 `SCHEDULE_EXACT_ALARM` 的替代路径。但 Google Play 政策限制该权限的使用范围，不能当成通用方案。

Android 13 同时引入了前台服务任务管理器(FGS Task Manager),用户可以在通知栏直接看到哪些 App 正在运行前台服务,并且可以手动停止。这让用户对后台活动有了更高的可见性和控制力。

Android 14 起，精确闹钟权限默认更严格：`SCHEDULE_EXACT_ALARM` 权限对大多数新安装且 targetSdkVersion >= 33 的 App **默认拒绝**。App 需要通过 `AlarmManager.canScheduleExactAlarms()` 检查权限状态,如果未授予,引导用户到系统设置页面手动开启。此前在 Android 13 中,`SCHEDULE_EXACT_ALARM` 仍默认授予——Android 12 引入的是特殊访问控制(需声明),Android 14 才将默认授予改为默认拒绝。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14#schedule-exact-alarms;developer.android.com/develop/background-work/services/alarms]

### Android 14：前台服务类型化 + 后台 Activity 启动需显式 opt-in

Android 14 要求前台服务必须声明**至少一个类型**(foreground service type),比如 `camera`、`location`、`mediaPlayback` 等。每种类型对应不同的权限要求和系统行为,系统也能据此更细地管理服务。如果一个声称在做媒体播放的前台服务并没有在播放音频,系统就可能终止它。

Android 14 还引入了后台 Activity 启动的显式 opt-in 机制。在此之前的版本中,App 发送 `PendingIntent` 时会隐式地将自己的后台 Activity 启动权限传递给接收方--恶意 App 可以通过 PendingIntent 链绕过后台启动限制。

从 Android 14 开始,发送方必须通过 `ActivityOptions.setPendingIntentBackgroundActivityStartMode(MODE_BACKGROUND_ACTIVITY_START_ALLOWED)` 显式授权,接收方才能在后台启动 Activity。同样,通过 `bindService()` 绑定后台 App 的服务时,也需要添加 `Context.BIND_ALLOW_ACTIVITY_STARTS` 标志。[已验证: developer.android.com/about/versions/14/behavior-changes-14]

此外,`mlock()` 的上限从 64MB 降到了 64KB,这对某些使用内存锁定来优化性能的 App 是一个需要注意的变化。

[已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14]

### Android 15：后台网络请求跟随 valid process lifecycle，Doze 进入更快

Android 15 新增了后台网络访问限制。官方文档的边界写法是 `valid process lifecycle`:App 在有效进程生命周期之外发起网络请求时,会收到 `UnknownHostException` 或其他 socket 相关 `IOException`。文档没有给出 "`Activity.onStop()` 之后固定几秒必现" 这样的时间承诺,因此排查时应以生命周期边界为准,不要写死秒数。

对应的工程动作也要跟着改。用户离开界面后仍需继续的网络工作,适合交给 `WorkManager`;任务如果必须保持用户可见,则改走 Foreground Service。普通后台线程上的裸网络请求,在 Android 15 上已经不能当成稳定路径。

Android 15 还让设备更快进入 Doze。官方行为变更页强调了这个方向,但没有在该页面给出 "50% 更快""额外 3 小时待机" 这类统一测试口径。写版本演进时保留行为变化即可,不把这两个数字当成 behavior changes 文档里的硬指标。

[已验证: 官方文档, developer.android.com/about/versions/15/behavior-changes-all]

Android 15 把后台网络、Doze 加速这些基调和 GKI 基线定了下来，Android 16 没有再做大框架变更，转而对 JobScheduler 配额做精细化管控。

### [自动发现：来源 web search - Android developer docs] Android 16：JobScheduler 配额优化

Android 16 继续对 JobScheduler 进行精细化管控。核心变化是 Job 的执行时间配额(runtime quota)现在不仅取决于 App 的 Standby Bucket,还取决于:

- Job 是在 App 可见时启动并延续到后台,还是在 App 完全后台时启动
- Job 是否与前台服务并发执行
- App 当前的 Standby Bucket 的具体分数

具体来说:一个在前台启动、用户正在交互时发起的 Job,会获得更多的执行时间;而一个在后台静默启动的 Job,执行时间会更短。同时,Android 16 提供了更好的诊断工具,开发者可以通过 API 查询 Job 为什么没执行或被停止。

[已验证: developer.android.com/about/versions/16/behavior-changes-all;developer.android.com/reference/android/app/job/JobScheduler]

Android 17 延续了精细化管控的方向，下面列出已通过官方文档确认的功耗行为变更。

### [自动发现] Android 17：已确认的功耗行为变更

Android 17 (API 37) 在功耗管理方面的已确认变化(本轮按官方 behavior changes、features 与 API reference 复核):

- **App memory limits**:系统可按进程设置内存上限,超出即终止。这和之前的 `android:largeHeap` 不同,是一个强制硬限制。
- **Reduced Wakelocks for Idle Alarms**：新增 `OnAlarmListener` 版 `setExactAndAllowWhileIdle()`，允许 App 在 idle 状态下用 listener 回调替代持续 partial WakeLock，减少闹钟唤醒后的 CPU 活动窗口。
- **ProfilingManager KILL_EXCESSIVE_CPU_USAGE**：`ProfilingManager` 新增 `KILL_EXCESSIVE_CPU_USAGE` trigger，系统可在检测到 App 长时间高 CPU 占用时主动终止进程。这是一个可观测性入口，也给了系统更强的干预手段。
- **JobScheduler reason stats**：`JobScheduler.getPendingJobReasonStats()` 返回 `Map<Integer, Duration>`，把 `PENDING_JOB_REASON_*` 映射到累计 pending 时长，适合和 Android 16 的 pending reason / history API 一起看配额、约束和停止原因。

这些变化延续了前面版本的演进方向：逐步减少 App 对 CPU 的自主使用权，同时提供更好的可观测性。

[已验证: Android 17 behavior changes / features / JobScheduler API reference; source.android.com/docs/core/power]

## GKI 对内核调度模块定制化的影响

GKI(Generic Kernel Image)把 Android 通用内核和厂商定制拆开了。Android 11 引入 GKI 1.0,Android 12 起要求搭配 5.10+ 内核的新设备采用这套模型。它的目标不是让所有设备"长得一样",而是把可复用的通用内核和厂商自带模块分开,减少长期堆补丁造成的碎片化。Android 15 这一代常见的 GKI 基线已经来到 6.6,同时 16KB page size 兼容也开始影响 App 和 SoC 适配节奏。

这里有个经常被写反的点。GKI release boot image 带有 Google 用于认证/VTS 的 `boot_signature`,这不等于 OEM 量产 `boot.img` 由 Google 代签。量产设备的 Verified Boot 仍然看 OEM 自己的 AVB key。把 `boot_signature` 和 AVB 设备签名混成一件事,会把认证流程和设备量产流程讲乱。

GKI 对 CPU 调度的影响,主要体现在厂商还能在哪里放自己的策略。

1. **通用调度器代码更收敛了**。厂商不能再长期依赖直接改 CFS/EAS 主干代码的方式维护自家分支,新增策略更适合通过 vendor modules、vendor hooks,或者推动上游合入。

2. **Vendor Hook 仍然是厂商插策略的常用位置**。在 android15-6.6 的调度 hook 里,可以直接看到 `android_rvh_cpu_overutilized`、`android_rvh_sched_balance_rt`、`android_rvh_uclamp_eff_get` 这类入口。它们比文档式的伪名字更重要,因为你在设备差异分析里实际会碰到的就是这些符号。

3. **`sched_ext` 还不是 Android 15 GKI 6.6 的现成能力**。它在 upstream Linux 6.12 才合入,更适合写成后续可能进入 Android common kernel 的实验方向。今天在 Android 15 设备上谈调度定制,主角仍然是 vendor hooks、uclamp、cpuset 和 task profiles,不是 `sched_ext`。

GKI 讲的是厂商还能在哪插策略，下面这个 [自动发现] 方向则代表了调度器更根本的变化可能：运行时可插拔。

### [自动发现] sched_ext:BPF 可编程调度的演进蓝图

Linux 6.12 合入的 `sched_ext` 为调度器提供了一条 BPF 插件化路径。通过加载一个 eBPF 程序,可以在不修改内核调度器源码的前提下,替换或增强任务选核、负载均衡、时间片分配等核心决策。Linux 6.12 / Android common 6.12 分支包含 sched_ext 基础设施;Android 17 设备是否可用取决于具体 kernel tag 和 `CONFIG_SCHED_CLASS_EXT` 配置,AOSP 默认调度链尚未切换到 sched_ext。

sched_ext 的潜在价值在于:厂商或场景化优化方案可以通过 BPF 程序实现"游戏模式用激进绑核策略、阅读模式用节能策略"的动态切换,而不再需要维护厂商独占的调度器补丁。这和 vendor hooks 的区别是,vendor hooks 只能在调度器内部决策点插入回调,sched_ext 允许完全替换调度策略主体。

目前 sched_ext 仍然属于实验方向。生产环境中调度定制的主力还是 vendor hooks、uclamp 和 task profiles。但 sched_ext 的存在意味着 Android 调度架构正在从"静态编译策略"向"运行时可插拔策略"演进。[已验证: LWN sched_ext 文档; kernel/common 6.12 sched/ext 目录]

对性能分析的直接影响是,两个都跑 Android 15 的设备,调度差异未必来自不同 Linux 版本,更常见的是 vendor hook、task profile 和 uclamp 策略不同。Perfetto 里看到的落核差异、频点抬升速度、RT 线程平衡方式,往往就从这里分叉。

[已验证: GKI 官方说明;AOSP android15-6.6.98_r00 kernel/common/include/trace/hooks/sched.h;Android 15 16KB page size 官方文档]

## 版本演进全景时间线

把以上内容放到一条时间线上，Google 在 CPU 和功耗管理上的策略是一脉相承的：**逐步限制 App 对 CPU 的自主使用权，让系统来做决策**。

| 版本 | 核心变化 | 约束层面 |
|------|---------|---------|
| 5.0 | JobScheduler 引入 | 应用层(推荐) |
| 6.0 | Doze 模式 | 系统策略层(静态) |
| 7.0 | Doze on the Go + 移除隐式广播 | 系统策略层 |
| 8.0 | 后台执行限制 | 应用层(强制) |
| 9.0 | Adaptive Battery + App Standby Buckets | 系统策略层(ML 驱动) |
| 10 | EAS 成为主流路线（取决于 EM + kernel 支持）+ 后台 Activity 限制 | 内核层 + 应用层 |
| 11 | task profiles 开始统一 cgroup / 调度策略入口 | Framework ↔ kernel |
| 12 | Performance Hint API 引入 + 精确闹钟权限化 | API 层 + 应用层 |
| 13 | USE_EXACT_ALARM 权限 + FGS Task Manager | 应用层(用户可见) |
| 14 | 精确闹钟默认拒绝 + FGS 类型化 + 后台 Activity opt-in | 应用层（权限加严 + 类型化） |
| 15 | GKI 6.6 常见化 + 后台网络受限 + Doze 进入更快 | 内核层 + 应用层 + 系统策略层 |
| 16 | JobScheduler 配额优化 | 系统策略层（精细化） |
| 17 | App memory limits + idle alarm wakelock 降低 + ProfilingManager KILL_EXCESSIVE_CPU_USAGE + JobScheduler reason stats + sched_ext 实验方向 | 应用层（资源硬限制） + 系统策略层（可观测性） + 内核层（可插拔） |

这条演进线背后有三个趋势:

1. **约束越来越严格**:从推荐使用 JobScheduler（5.0）,到限制后台服务(8.0),到限制精确闹钟(12-14),到限制后台网络(15)。每一步都在封堵"App 自己控制 CPU"的路径。
2. **策略越来越智能**:从静态的 Doze(6.0),到 ML 驱动的 Adaptive Battery(9.0),再到按 Standby Bucket、前后台状态和 Job 配额做动态控制(16)。系统越来越擅长根据用户行为和设备状态做决策。
3. **用户可见性越来越高**:前台服务通知(8.0)→ FGS Task Manager(13)→ Play listing / Vitals 警告。Android 15 的后台网络限制属于平台约束,常见表现是 App 侧 `UnknownHostException` 或 socket `IOException`,不写成通用用户提示。

## 在 Perfetto 中的观察

当在 Perfetto 中分析 CPU 相关行为时,可以通过以下维度观察版本演进带来的差异:

1. **Doze 状态**:在设备空闲时段,检查 CPU 是否有长时间的无活动期(对应 Doze 深度休眠)。Android 15 的 Doze 加速意味着这个无活动期开始得更早。

2. **任务迁移模式**:对比不同 Android 版本上同一 App 的 CPU 调度 Track。在 EAS 启用前（Android 9 及更早），任务迁移更“随机”；EAS 启用后（Android 10+），会更常看到"把轻量任务集中到小核"的规律性模式。

3. **JobScheduler 执行**:在 Android 12+ 上,Job 的执行间隔明显更不规律,特别是 Rare 桶的 App。Perfetto 里要把两类数据分开:`android_job_scheduler_states` 来自 statsd atom,适合看 constraint、bucket 和 pending 状态;`android_job_scheduler_events` 来自 system_server 的 atrace `ss` 类别,适合看 schedule / execute 事件。

4. **Standby Bucket 变化**:在长时间 Trace 中,同一个 App 的 Job 执行频率通常会随时间推移而降低,这正是 Adaptive Battery 在起作用。bucket 与约束状态优先看 statsd 生成的 `android_job_scheduler_states`,执行时序再用 atrace 生成的 `android_job_scheduler_events` 互查。

5. **WakeLock 持有时间**:Doze 模式下 WakeLock 被忽略,所以在 Perfetto 中可能会看到 WakeLock 被 acquire 后很久才被 release,但这期间 CPU 并没有实际活动--因为 Doze 覆盖了 WakeLock 的效果。

[待补充:不同版本 Perfetto Trace 截图对比]

## 常见问题与误区

### "我的后台任务在 Android 12 上突然不工作了"
最大可能:使用了精确闹钟但没有声明 `SCHEDULE_EXACT_ALARM` 权限,或者 App 被放到了 Restricted 桶。检查 `adb shell am get-standby-bucket` 和 `adb shell dumpsys alarm`。

### "EAS 让我的 App 变慢了"
EAS 可能会让某些场景下的单次执行时间变长,因为任务被放到了小核,但整体功耗下降。App 侧没有公开 API 直接写 `cpu.uclamp.min` / `cpu.uclamp.max`。延迟敏感工作应优先使用 ADPF / `PerformanceHintManager` 创建 hint session,持续上报 target / actual work duration;系统组件或 OEM 策略再把 hint、task profile、cpuset 和 uclamp 连接到调度器。直接操作 uclamp 属于系统组件、root / 调试环境或厂商策略范围。

### "Doze 模式下我的推送收不到"
FCM（Firebase Cloud Messaging）高优先级消息可以绕过 Doze。如果推送走的是自有长连接，在 Doze 下通常会被延迟。建议将关键推送迁移到 FCM 高优先级通道。

### “不同厂商的设备，后台限制不一样”
会有差异。AOSP 定义了基础规则，但很多厂商（尤其是中国市场的厂商）会在 AOSP 基础上叠加自己的省电策略。这就是为什么同一个 App 在 Pixel 上表现正常,在某些国产设备上后台被杀。可以参考 [dontkillmyapp.com](https://dontkillmyapp.com/) 了解各厂商的差异。

## 参考资料

- [Android 6.0 Changes - Doze](https://developer.android.com/about/versions/marshmallow/android-6.0-changes) [已验证: 官方文档]
- [Android 9 Power Management](https://developer.android.com/about/versions/pie/power) [已验证: 官方文档]
- [Android 12 Behavior Changes - Exact Alarms](https://developer.android.com/about/versions/12/behavior-changes-12) [已验证: 官方文档]
- [Android 13 Behavior Changes](https://developer.android.com/about/versions/13/behavior-changes-13) [已验证: 官方文档]
- [Android 14 Behavior Changes - FGS Types](https://developer.android.com/about/versions/14/behavior-changes-14) [已验证: 官方文档]
- [Background Execution Limits (Android 8.0)](https://developer.android.com/about/versions/oreo/background) [已验证: 官方文档]
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby) [已验证: 官方文档]
- [Energy Aware Scheduling - ARM Documentation](https://developer.arm.com/documentation/den0024/latest) [已验证: ARM 官方文档]
- [GKI 官方文档](https://source.android.com/) [已验证: source.android.com 站点内容]
- [sched_ext - LWN.net](https://lwn.net/Articles/922405/) [已验证: LWN]
- [Android 15 Behavior Changes](https://developer.android.com/about/versions/15/behavior-changes-15) [已验证: 官方文档]
- [Android 17 Features](https://developer.android.com/about/versions/17/features) [已验证: 官方文档]
- [Android 17 Behavior Changes](https://developer.android.com/about/versions/17/behavior-changes-17) [已验证: 官方文档]
- [JobScheduler Reference](https://developer.android.com/reference/android/app/job/JobScheduler) [已验证: 官方文档]
- [PerformanceHintManager API Reference](https://developer.android.com/reference/android/os/PerformanceHintManager) [已验证: 官方文档]
- [Android cgroups and task profiles](https://source.android.com/docs/core/perf/cgroups) [已验证: source.android.com]
- [Arm Memory Tagging Extension on Android](https://developer.android.com/ndk/guides/arm-mte) [已验证: 官方文档]
- AOSP 路径参考(android-17.0.0_r1 / android15-6.6.98_r00):
  - `frameworks/base/core/java/android/app/usage/UsageStatsManager.java` - Standby bucket 常量定义(含 `STANDBY_BUCKET_NEVER = 50`)
  - `frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java` - Doze 模式实现
  - `frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java` - App Standby Buckets 实现
  - `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java` - JobScheduler 服务
  - `system/core/libprocessgroup/profiles/task_profiles.json` - task profile 与 uclamp 映射
  - `kernel/common/include/trace/hooks/sched.h` - Android common kernel vendor hooks
  - `kernel/sched/fair.c` - CFS/EAS 调度器核心代码
