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

## 三条演进时间线

CPU 与功耗问题经常被写成一条简单的版本链：Android 版本升级，内核调度器随之更换，应用后台限制继续增加。这个说法会把不同层次的变化混在一起，需要分别追踪三条时间线：

1. **应用 API 与兼容性规则**：`JobScheduler`、精确闹钟、前台服务和后台 Activity 启动限制。它们通常还受 `targetSdkVersion`、权限、豁免条件影响。
2. **系统资源策略**：Doze、App Standby Buckets、Battery Saver、任务配额。它们由 framework 服务执行，也可能带有 DeviceConfig 和厂商配置。
3. **内核与设备实现**：EAS、UClamp、CPUFreq、GKI、vendor module、`sched_ext`。同一个 Android 版本可以运行多条受支持的内核分支，不同设备也可以采用不同的调度和功耗参数。

平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为基准，内核以 `android17-6.18-2026-06_r6` 为基准。历史段落使用机制首次公开时的版本，不把后续版本新增的行为倒推到旧系统。

> **关联章节**：EAS 的调度路径见 §5.2，Android 功耗控制面见 §5.6，后台任务选型见 §5.8。这里说明变化发生的层次和版本起点，具体实现由对应专题展开。

## Android 5.0：JobScheduler 把可延迟工作交给系统编排

Android 5.0（API 21）加入 `JobScheduler`。应用描述任务所需的网络、充电、空闲等约束，由系统选择执行时机。系统因此有机会合并多个应用的唤醒和网络活动，减少设备频繁退出低功耗状态。

下面的任务只声明“满足非计费网络并且正在充电时执行”。它没有承诺提交后立刻运行：

```java
ComponentName service = new ComponentName(context, SyncJobService.class);
JobInfo job = new JobInfo.Builder(JOB_ID, service)
        .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED)
        .setRequiresCharging(true)
        .build();

JobScheduler scheduler = context.getSystemService(JobScheduler.class);
int result = scheduler.schedule(job);
```

`schedule()` 返回成功，表示系统接受了任务；任务仍可能因为显式约束、待机桶、Doze、配额或系统优化而等待。这个语义贯穿后续版本。

`JobScheduler` 也没有取代所有后台机制。到 Android 17，应用仍需按语义选择：

- 可推迟且要保证最终执行的工作，优先考虑 WorkManager；其后台调度通常会使用 `JobScheduler`。
- 直接使用平台任务约束、命名空间或 user-initiated job 时，可以使用 `JobScheduler`。
- 用户可感知且正在进行的工作，可能需要前台服务。
- 用户要求在准确时刻发生的提醒，才考虑精确闹钟。
- 与界面生命周期绑定的短任务，不应为了“后台化”而提交成系统任务。

> **版本边界**：Android 5.0 引入 `JobScheduler`；后续版本仍保留多种后台执行入口，并未只剩 JobScheduler/WorkManager。

## Android 6.0—7.0：Doze 与 App Standby 控制设备空闲期

### Android 6.0：Deep Doze

Android 6.0（API 23）加入 Doze 和 App Standby。设备未充电、屏幕关闭并保持静止一段时间后，可以进入深度空闲。此时系统会延后普通网络活动、Job、Sync 和普通 Alarm，并忽略应用持有的普通 WakeLock；系统会间歇进入维护窗口，集中处理积压工作。

维护窗口的开始时间与间隔是系统策略，不属于公开 API 契约。文章和业务代码都不应依赖“一小时、两小时、四小时”这类固定序列。设备配置、版本和厂商实现都可能改变节奏。

`setAndAllowWhileIdle()` 与 `setExactAndAllowWhileIdle()` 可以在低功耗空闲期间触发，但平台会限制调用频率。它们只适合用户明确要求的时效性场景，也不等于给应用开放持续运行或持续联网能力。

排查入口如下：

```shell
adb shell dumpsys deviceidle
adb shell dumpsys jobscheduler
adb shell dumpsys alarm
```

`dumpsys deviceidle` 用于确认状态机；不能只看到一段 CPU 空白就判断设备进入 Doze。屏幕关闭、应用无工作、系统挂起、采样缺口都可能产生相似图形。

### Android 7.0：Light Doze 与广播限制起步

Android 7.0（API 24）增加较轻的空闲阶段。设备未充电且屏幕关闭时，即使仍在移动，也可以先限制部分后台活动；满足静止条件后再进入更深的空闲阶段。

同一版本还限制了若干高频隐式广播。例如，面向 Android 7.0 的应用不能再依赖 manifest 中的 `CONNECTIVITY_ACTION` 接收器获取所有连接变化；`ACTION_NEW_PICTURE` 与 `ACTION_NEW_VIDEO` 也不再按旧方式广播。这不是“系统删除了所有隐式广播”。运行时注册、显式广播以及后续文档列出的豁免广播仍有各自语义。

> **版本边界**：Android 6.0 引入 Doze；Android 7.0 扩大了设备移动时的空闲管理范围。维护窗口没有固定公开时刻表。

## Android 8.0：后台服务与 manifest 广播受到 target SDK 约束

Android 8.0（API 26）的 Background Execution Limits 主要影响以 API 26 或更高版本为目标的应用。

当应用进入后台后，系统会给已有后台服务保留一段宽限期；宽限期结束后，服务会停止，应用也不能继续任意创建后台服务。处理高优先级消息、通知 `PendingIntent` 等用户可感知事件时，应用还可能进入临时允许名单。因而，“只要在后台调用 `startService()` 就必然立即抛异常”过于绝对，必须结合进程状态、调用入口与豁免条件判断。

需要继续执行用户可感知工作时，应用可以调用 `startForegroundService()`，随后及时把服务提升为前台服务并显示通知。可延迟工作更适合 Job 或 WorkManager。

同一版本对 manifest 声明的隐式广播接收器增加了限制：

- 面向 API 26 及以上的应用，通常不能在 manifest 中注册面向所有应用的隐式广播；
- 显式广播、只发给本应用的广播、签名权限保护的广播和官方豁免项仍可使用；
- 运行时通过 `registerReceiver()` 注册的接收器不等同于 manifest 静态接收器。

这里的关键变量是设备 API、`targetSdkVersion`、广播种类和接收器注册方式，缺少其中任何一个都无法解释行为差异。

## Android 9：App Standby Buckets 与 Adaptive Battery

Android 9（API 28）引入 App Standby Buckets。系统根据应用近期和历史使用情况，把应用分到不同优先级组，并据此约束 Job、Alarm 与网络等资源。

Android 9 的常用分组是 Active、Working Set、Frequent、Rare；`STANDBY_BUCKET_NEVER` 表示应用已安装但一次也未启动。`STANDBY_BUCKET_RESTRICTED` 在 Android 12（API 31）才加入，不能出现在 Android 9 的初始分组表里。

Adaptive Battery 可以借助系统预测决定应用未来可能被使用的时间，再影响待机桶选择。AOSP 也支持按近期使用情况作非预测式判断。具体分类标准属于系统与设备实现，应用不应假设某个固定机器学习模型、固定预测小时数或固定厂商阈值。

应用可以读取自己的待机桶，调试环境也可以通过 shell 查看指定包：

```shell
adb shell am get-standby-bucket com.example.app
adb shell dumpsys usagestats
```

待机桶是任务延后的一个输入。即使处于 Active，任务自身的网络、充电等约束仍需满足；即使进入 Rare，也不代表进程立刻被杀或所有前台功能失效。

> **版本边界**：Android 9 引入 App Standby Buckets。Adaptive Battery 会参与资源优先级判断，但分类算法与阈值不是应用可依赖的稳定接口。

## Android 10—11：EAS 普及、task profile 与 GKI

### Android 10 时期的 EAS：常见工程路线，不是版本开关

Android 10 前后，异构多核手机采用 EAS（Energy Aware Scheduling）组织任务放置已成为常见路线。这里的“主流”描述的是移动 SoC 和设备内核的工程趋势，不表示 Android 10 API 或兼容性要求强制所有设备启用 EAS。

EAS 是否参与调度，要同时满足内核配置、异构容量拓扑、Energy Model 和调度路径等条件。最终效果还受以下因素影响：

- PELT 对任务利用率的估算；
- UClamp 给任务或 cgroup 设置的利用率上下界；
- cpuset/cgroup 对可运行 CPU 的约束；
- `schedutil` 或其他 CPUFreq governor 的频率决策；
- thermal、Power HAL、ADPF 与厂商策略施加的限制或提示。

所以，“系统版本从 CFS 升级成 EAS”不是准确表述。EAS 处理的是 fair class 中的能量感知放置，仍建立在 Linux 调度框架之上；RT、Deadline、调度域配置和厂商策略也不会因此消失。

### Android 10—12：task profile 统一资源配置入口

Android 10 及以后使用 cgroup abstraction layer 与 task profile 描述资源约束。Android 11 及以后可通过 `SetTaskProfiles`、`SetProcessProfiles` 把配置应用到线程或进程；Android 12 的 init `task_profiles` 命令取代相关场景中的 `writepid`。

Android 17 的默认定义位于：

```text
system/core/libprocessgroup/profiles/cgroups.json
system/core/libprocessgroup/profiles/task_profiles.json
```

设备还可以提供 API level 或 vendor 覆盖文件。因此，看到相同的 profile 名称时，也要检查设备上的最终合并结果。task profile 是 framework/native 层调用 cgroup 与调度控制项的声明式入口，不是三方应用可直接依赖的公开性能 API。

### Android 11 起：GKI 改变内核定制边界

GKI 把通用核心内核与硬件相关 vendor module 分开，并为支持周期内的 vendor module 提供稳定 KMI。产品相关代码不能继续随意塞入 ACK 核心；需要通过上游能力、模块、导出 KMI 或经过审核的 vendor hook 连接。

GKI 并没有让所有设备使用相同的调度参数，也没有清除厂商扩展。设备仍可通过 vendor module、task profile、Power/Thermal HAL、设备配置和允许的 hook 实现产品策略。变化集中在接口边界、可维护性和兼容性约束。

## Android 12—14：精确闹钟、前台服务与后台启动限制继续增加

### Android 12：精确闹钟特殊访问与后台 FGS 启动限制

面向 Android 12（API 31）及以上的应用，使用基于 `PendingIntent` 的精确闹钟通常需要声明 `SCHEDULE_EXACT_ALARM` 并获得“闹钟和提醒”特殊访问。调用前应检查 `canScheduleExactAlarms()`；被用户撤销后，相关精确闹钟也会被移除。

同样从 target API 31 开始，后台应用通常不能直接启动前台服务，只有用户可见转换、高优先级消息、部分系统广播等文档列出的例外。违反规则会收到 `ForegroundServiceStartNotAllowedException`。

Android 12 还公开了 `PerformanceHintManager`。应用可为一组相关线程创建 hint session，报告目标工作时长与实际工作时长。它向系统提供工作负载信息，设备是否调整核选择或频率仍由系统实现决定。

### Android 13：两种精确闹钟权限语义

Android 13（API 33）加入 `USE_EXACT_ALARM`。它面向以精确时刻为核心功能的有限应用类别，安装时授予且受应用商店政策约束；普通可选功能继续使用由用户控制的 `SCHEDULE_EXACT_ALARM`。两者不能因为名字相近就互换。

### Android 14：默认拒绝与 FGS 类型校验

Android 14 设备上，多数新安装、面向 API 33 及以上且声明 `SCHEDULE_EXACT_ALARM` 的应用不再获得预授权。日历和闹钟等符合条件的应用有单独规则。

面向 API 34 及以上的应用还必须为前台服务声明合适的类型及对应权限。系统在 `startForeground()` 时检查类型和前置条件；涉及 camera、microphone、location 等 while-in-use 权限时，后台启动限制更严格。

> **版本边界**：Android 12 以后持续限制精确闹钟、后台启动前台服务和后台 Activity 启动；这些规则按设备版本、target SDK、权限和豁免条件分段生效，不能压缩成“后台一律禁止”。

## Android 15—16：从“能否启动”继续走向时长与配额管理

Android 15 针对部分前台服务类型增加运行时长限制，并限制从 `BOOT_COMPLETED` 启动若干类型的前台服务。工程上应按工作语义选择 API，不能用前台服务长期包裹普通同步任务来绕开后台限制。

Android 16（API 36）调整了 JobScheduler 执行配额：

- 任务在应用处于 top 状态时启动，随后应用转入后台，也会受运行时配额约束；
- 与前台服务并行执行的 Job 也会计入配额；
- Active 待机桶内启动的后台任务有较宽裕的配额，但不再等同于没有配额；
- WorkManager 的 long-running worker 底层仍使用 JobScheduler，因而也可能耗尽任务配额；
- 用户主动发起的数据传输应评估 user-initiated data transfer job，而不是默认套用 long-running worker。

Android 16 还提供 CPU/GPU headroom 查询能力，让应用评估近期可用的性能余量。headroom 是观测和自适应输入，不是锁频接口；渲染、游戏或计算负载应结合热状态和实际帧耗时调整工作量。

> **版本边界**：Android 16 扩大了 Job 配额覆盖范围，并增强性能余量观测能力，没有引入一套新的内核调度器。

## Android 17：诊断能力增强，内核锚点进入 6.18

Android 17 / API 37 与 CPU、功耗排查直接相关的公开变化主要集中在诊断和更窄的后台接口：

### JobScheduler 等待原因统计

`JobScheduler.getPendingJobReasonStats(int)` 返回 `Map<Integer, Duration>`，把任务生命周期内每种等待原因映射到累计时长。多种约束可能同时不满足，因此各时长之和可能大于任务总等待时间。统计在设备重启后不保留，任务成功完成或取消时也会清除。

它回答“任务为什么一直没运行”，不表示系统按 CPU 时间给单个线程分配 JobScheduler 配额。Android 17 对应实现仍位于 JobScheduler APEX：

```text
frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
frameworks/base/apex/jobscheduler/service/java/com/android/server/job/
```

前一个路径定义公开 API 语义，后一个目录包含服务端调度、约束控制器与配额处理。定位问题时要同时看调用契约和服务端状态。

### ProfilingManager 的系统触发器

Android 17 扩充 trigger-based profiling，包括冷启动、OOM、系统异常和因异常 CPU 使用被终止等触发器。`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 可在对应终止事件发生时提供调用栈采样，用于定位异常计算路径。

该接口是诊断入口。“存在 excessive CPU trigger”不等于 Android 17 给所有应用公布了固定 CPU 百分比或固定终止时长；触发条件仍由系统控制。

### allow-while-idle 的 listener 重载

API 37 新增接收 `String tag`、`Executor` 与 `OnAlarmListener` 的 `setExactAndAllowWhileIdle()` 重载。它适合调用进程会持续存活的短期场景，可以减少为了等待定时回调而长期持有 WakeLock 的需求。

listener alarm 不提供进程存活保证。调用组件结束、进程进入无活动组件状态后，系统可以取消它；需要跨越组件和进程生命周期可靠交付时，仍应使用基于 `PendingIntent` 的 API。新重载也没有放宽 allow-while-idle 的频率限制。

### Android 17 的内核基线

本知识库统一核对 `android17-6.18-2026-06_r6`。AOSP 支持关系同时允许 Android 17 搭配若干较早的 GKI 分支，所以“系统是 Android 17”不能单独证明设备运行 6.18。

6.18 锚点中已经包含 `sched_ext` 核心代码、工具和自测。`schedutil` 的 `sugov_get_util()` 也能读取 `scx_cpuperf_target()`；当 SCX 接管全部任务时，频率路径按 BPF scheduler 给出的性能目标工作。以下结论需要分开：

1. 源码树具备 `sched_ext`，这是源码事实；
2. 内核配置允许该能力，这是构建事实；
3. 设备加载并启用了某个 BPF scheduler，这是运行时事实；
4. 产品把它用于日常 CPU 调度，这是产品策略。

只证明第一项，不能推导后三项。分析具体设备时应检查内核版本、配置、已加载调度器和 trace。

## 一张表看清主要变化

| 版本 | 应用/API 侧 | 系统策略侧 | 内核/设备侧的解读 |
|---|---|---|---|
| Android 5.0 / API 21 | `JobScheduler` | 可延迟任务由系统选择时机 | 与具体调度器无直接绑定 |
| Android 6.0 / API 23 | allow-while-idle alarm | Deep Doze、App Standby | 目标是延长系统空闲与挂起时间 |
| Android 7.0 / API 24 | 部分广播行为变化 | Light Doze | 不能概括为删除全部隐式广播 |
| Android 8.0 / API 26 | 后台服务、manifest 接收器受限 | 后台执行规则增强 | 多数规则与 target SDK、豁免有关 |
| Android 9 / API 28 | 待机桶查询 API | App Standby Buckets、Adaptive Battery | Restricted bucket 尚未加入 |
| Android 10 | 后台启动继续受限 | cgroup abstraction/task profile | EAS 在异构设备上常见，但不是版本保证 |
| Android 11 | 资源策略继续演进 | task profile API | GKI 开始改变厂商内核扩展边界 |
| Android 12 / API 31 | 精确闹钟特殊访问、ADPF、后台 FGS 限制 | Restricted bucket 等策略加入 | 上层提示最终仍由设备策略解释 |
| Android 13 / API 33 | `USE_EXACT_ALARM` | 权限用途进一步区分 | 不改变底层调度器 |
| Android 14 / API 34 | 新安装应用精确闹钟默认策略变化、FGS 类型必填 | while-in-use 检查增强 | 继续按设备与 target SDK 分析 |
| Android 15 / API 35 | 部分 FGS 类型新增时长/启动限制 | 长任务约束增强 | 不应把 FGS 当作无限后台执行通道 |
| Android 16 / API 36 | CPU/GPU headroom、Job 诊断增强 | Job runtime quota 覆盖扩大 | 不代表统一切换调度器 |
| Android 17 / API 37 | Job 等待原因统计、profiling triggers、listener idle alarm | 后台规则继续按场景细化 | 推荐锚点为 `android17-6.18-2026-06_r6`；设备也可用受支持的旧 GKI |

## 版本差异排查：先确认规则属于哪一层

遇到“升级系统后任务不跑”时，按下面顺序收集证据。

### 1. 建立版本与安装状态

下面的命令保存系统版本和包状态，避免把 target SDK、安装路径差异误判为 CPU 调度变化：

```shell
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.incremental
adb shell dumpsys package com.example.app
```

至少记录设备 API、build fingerprint、应用 `targetSdkVersion`、安装/恢复/系统升级路径。精确闹钟是否默认授权就与“新安装还是升级保留”有关。

### 2. 确认应用选用的执行 API

把任务归入 Job/WorkManager、Alarm、FGS、普通 Service 或 Activity 启动之一，再检查对应约束。不要用“后台任务”四个字覆盖所有机制。

### 3. 查看系统为什么延后

下面的命令分别读取 Job、Doze、Alarm、待机桶和精确闹钟权限状态：

```shell
adb shell dumpsys jobscheduler
adb shell dumpsys deviceidle
adb shell dumpsys alarm
adb shell am get-standby-bucket com.example.app
adb shell cmd appops get com.example.app SCHEDULE_EXACT_ALARM
```

Android 17 应用还可以在合适的调试入口查询 `getPendingJobReasonStats()`。先读系统给出的等待原因，再判断是网络、充电、idle、quota、待机桶还是调度优化。

### 4. 再下沉到 CPU 与内核

任务已经进入运行态但执行慢，才进入 CPU 侧分析：

- Perfetto 中查看线程 `sched_switch`、`sched_wakeup`、CPU frequency、CPU idle、thermal 与应用自定义 slice；
- 检查线程所在 cpuset/cgroup、UClamp 和 task profile；
- 核对 `/proc/version`、内核配置、Energy Model、CPUFreq governor；
- 厂商设备还要核对 Power HAL、Thermal HAL 与 vendor module/hook。

Doze、JobScheduler 和待机桶主要决定“何时允许工作”；EAS、UClamp、CPUFreq 与 thermal 主要影响“开始运行后在哪个核、以多高频率和多大预算执行”。两组问题要用不同证据回答。

## 常见误区

### “Android 10 已把 CFS 替换成 EAS”

EAS 是 fair 调度路径中的能量感知放置机制，是否生效取决于内核和设备条件。Android 版本号不能证明设备启用了 EAS。

### “进入 Doze 后网络永久断开”

Doze 会延后普通后台网络和任务，并提供维护窗口及有限豁免。它是状态机与批处理策略，不是永久断网开关。

### “WorkManager 的 long-running worker 不受 JobScheduler 配额影响”

Android 16 起，这类 worker 仍可能消耗 Job runtime quota。需要由用户发起的大数据传输应评估 user-initiated data transfer job。

### “前台服务可以绕过后台限制”

前台服务要求工作对用户可感知，并受启动来源、类型、权限、时长和 target SDK 等规则约束。通知只是前台服务契约的一部分。

### “GKI 禁止厂商修改任何调度行为”

GKI 限制产品代码进入核心内核的方式，并稳定 vendor module 使用的 KMI。vendor module、受控 hook、task profile 与 HAL 策略仍给设备实现保留了空间。

### “Android 17 有 sched_ext，所以所有设备都在运行 BPF 调度器”

源码存在、编译启用、运行时加载和产品采用是四件事。必须在目标设备上逐项取证。

## 小结

Android 5 到 Android 17 的主线可以概括为：

- 可延迟工作逐步由系统统一安排，应用需要描述约束和用户语义；
- 设备空闲、应用活跃度、权限、前台可见性和配额共同决定后台机会；
- EAS、task profile、GKI 与 `sched_ext` 改变系统工程实现，但不能从 API 版本直接推断设备调度配置；
- Android 17 增加了 Job 等待原因、系统触发 profiling 和 listener 型 idle alarm 等诊断或细分接口；
- 排查版本差异时，先确认设备版本、target SDK 和执行 API，再检查系统状态，最终进入调度、频率和热管理。

在这套分层方法中，版本号用于选择规则和源码分支，不能直接作为结论。

## 参考与源码锚点

- [Android 6.0 Doze 行为变化](https://developer.android.com/about/versions/marshmallow/android-6.0-changes)
- [Doze 与 App Standby 指南](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Android 8.0 Background Execution Limits](https://developer.android.com/about/versions/oreo/background)
- [Android 9 电源管理与 App Standby Buckets](https://developer.android.com/about/versions/pie/power)
- [App Standby Buckets 当前规则](https://developer.android.com/topic/performance/appstandby)
- [Android 12 行为变化](https://developer.android.com/about/versions/12/behavior-changes-12)
- [精确闹钟指南](https://developer.android.com/develop/background-work/services/alarms)
- [前台服务后台启动限制](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Android 16 JobScheduler 配额变化](https://developer.android.com/about/versions/16/behavior-changes-all)
- [Android 17 Features and APIs](https://developer.android.com/about/versions/17/features)
- [Android 17 `JobScheduler` API](https://developer.android.com/reference/android/app/job/JobScheduler)
- [cgroup abstraction 与 task profile](https://source.android.com/docs/core/perf/cgroups)
- [GKI 内核模块与 vendor module](https://source.android.com/docs/core/architecture/kernel/modules)
- [Android Common Kernel 支持关系](https://source.android.com/docs/core/architecture/kernel/android-common)
- [Android 17 6.18 发布锚点](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)
- AOSP `android-17.0.0_r1`：`frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java`
- AOSP `android-17.0.0_r1`：`frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java`
- AOSP `android-17.0.0_r1`：`system/core/libprocessgroup/profiles/task_profiles.json`
- ACK `android17-6.18-2026-06_r6`：`kernel/sched/ext.c`
- ACK `android17-6.18-2026-06_r6`：`kernel/sched/cpufreq_schedutil.c`
- ACK `android17-6.18-2026-06_r6`：`include/trace/hooks/sched.h`
