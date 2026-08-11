---


status: finalized
title: JobScheduler/WorkManager 调度与后台任务性能
chapter: '5.8'
section: '5.8'
drafted_date: '2026-04-06'
polish_count: 1
polish_date: '2026-04-09'
polish_by: task2b-polish
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-04-27'
reviewed_date: 2026-06-07
reviewed_by: openclaw-task6
last_verified_against: AOSP android-16.0.0_r1, developer.android.com reference, perfetto.dev
  stdlib docs, Android Vitals docs
confidence: medium
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/05.26-android17-jobscheduler-service-cpu-quota.md"
  - "src/part1-fundamentals/ch05-cpu-power/23-android17-jobscheduler-system-throttling.md"
sources:
- type: official
  path: https://developer.android.com/reference/android/app/job/JobScheduler
- type: official
  path: https://developer.android.com/reference/android/app/job/JobInfo.Builder
- type: official
  path: https://developer.android.com/reference/android/app/usage/UsageStatsManager
- type: official
  path: https://developer.android.com/topic/libraries/architecture/workmanager/how-to/define-work
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/features#job-debugging
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobStore.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobInfo.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
tags:
- jobscheduler
- workmanager
- background-scheduling
- power
- doze
- battery
- wakelock
- app-standby
- quota
related_chapters:
- '5.6'
- '5.7'
- '1.5'
- '11.2'
- '15.5'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: "fixed"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-06-04'
last_task9_at: "2026-06-04T18:15:00+08:00"
task9_review_notes: "2026-06-04 Task9 18: auto-fixed。P0 1:PENDING_JOB_REASON_DEVICE_STATE 版本线由 API 37 修正为 API 34 常量/API 37 stats 方法;P2 1:TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE 产物口径从 Method Trace/Heapprofd 改为 running system trace snapshot/call stack sample 边界。回到 Task6 复审。"
last_task2b_at: '2026-06-04T12:57:00+08:00'
repaired_date: '2026-04-27'
repaired_by: openclaw-task2b
rework_type: review回炉修复(Task9 问题单)
task6_result: pass-light-edit
last_task6_at: 2026-06-07T17:05:00+08:00
last_task6_review_log: "logs/review/2026-05-17-11-review.md"
task6_review_notes: "2026-06-07 17:05 Task6 revisiting #2: pass-light-edit. 禁用词0/高频词0/物理动词0. 否定-纠正2处均为功能性技术对比. 无B类大问题. task9_result=auto-fixed, queue无pending, 自动晋升finalized."
last_task9_review_log: "logs/deep-review/2026-06-04-18-deep-review.md"
p0: 1
p1: 0
p2: 1
last_task9_autofix_at: "2026-06-04"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-07
---


# 5.8 JobScheduler/WorkManager 调度与后台任务性能

## 为什么后台任务需要系统调度

后台同步、日志上传、缓存整理和资源预取都有一个共同特点：它们通常可以晚一点执行。若每个应用都用精确闹钟唤醒设备，再自行持有 WakeLock，系统很难把多个应用的工作安排到同一个活跃窗口。单次任务也许只运行几十毫秒，大量碎片化唤醒却会缩短 CPU 在深度空闲状态中的停留时间。

JobScheduler 的做法是让应用声明“做什么、需要哪些条件、允许多晚”，由系统结合设备状态和所有应用的请求选择执行时机。WorkManager 在此基础上增加任务持久化、依赖关系、重试和兼容处理。两者都适合可延期的后台工作，但它们没有提供精确定时或无限运行的资格。

需要回答三个问题：

1. 一个 job 从 `schedule()` 到 `JobService` 的路径是什么；
2. 任务迟迟不运行时，怎样区分约束、配额、设备状态和应用自身问题；
3. WorkManager、Expedited Job、UIDT、Foreground Service 和精确闹钟分别适合什么场景。

Doze、App Standby 与后台执行限制的策略背景见 5.6 和 5.7 节。平台源码以 `android-17.0.0_r1` 为基准。

## JobScheduler 的调度模型

### 声明执行条件，而非预订一个时刻

AlarmManager 面向时间点或时间窗口；JobScheduler 面向一项带条件的工作。以下写法表达“联网且电量不低后再同步”，并没有承诺某个固定时刻开始：

```kotlin
val job = JobInfo.Builder(
    SYNC_JOB_ID,
    ComponentName(context, SyncJobService::class.java)
)
    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
    .setRequiresBatteryNotLow(true)
    .build()

val result = context.getSystemService(JobScheduler::class.java).schedule(job)
```

生产代码要检查 `schedule()` 的返回值。`RESULT_SUCCESS` 只表示系统接受了任务，并不表示任务已经启动；参数无效、达到调度限制或 Expedited Job 没有可用配额时，都可能得到 `RESULT_FAILURE` 或在构建阶段抛出异常。

AlarmManager 仍有适用场景，例如闹钟、日历提醒等面向用户的精确时间事件。它的精确闹钟访问权限、Doze 行为和不同重载的生命周期边界见 5.7 节。普通同步和维护任务优先交给 JobScheduler 或 WorkManager，让系统获得批处理空间。

### Android 17 源码中的核心组件

Android 17 的 JobScheduler 实现位于 `frameworks/base/apex/jobscheduler/`。应用侧 API 和系统服务分开存放：

- `framework/java/android/app/job/`：`JobInfo`、`JobScheduler`、`JobService` 等公开 API；
- `service/java/com/android/server/job/`：`JobSchedulerService`、`JobStore`、`JobConcurrencyManager`、`JobServiceContext`；
- `service/java/com/android/server/job/controllers/`：网络、电量、空闲、存储、时间、配额等状态控制器。

一次普通调度的主路径可以概括为：

```text
App: JobScheduler.schedule(JobInfo)
  -> system_server: JobSchedulerService.scheduleAsPackage(...)
  -> startTrackingJobLocked(...)
  -> 各 StateController 跟踪并更新约束状态
  -> maybeQueueReadyJobsForExecutionLocked(...)
     或 queueReadyJobsForExecutionLocked(...)
  -> mPendingJobQueue
  -> maybeRunPendingJobsLocked()
  -> JobConcurrencyManager.assignJobsToContextsLocked()
  -> JobServiceContext.executeRunnableJob(...)
  -> bind JobService
  -> JobService.onStartJob(JobParameters)
```

这条路径揭示了一个常见误判：job 已经出现在 `dumpsys jobscheduler` 中，只能证明 `JobSchedulerService` 正在跟踪它。它还要通过 Controller 的约束判断、配额与并发选择，随后才会进入某个 `JobServiceContext`。

几个核心组件各自负责的范围如下：

| 组件 | Android 17 中的职责 |
|---|---|
| `JobSchedulerService` | 接收、校验、跟踪和排队 job，协调状态变化与执行 |
| `StateController` 子类 | 维护一类约束或策略状态，并通知服务重新评估相关 job |
| `JobStore` | 保存已登记 job；持久化 job 写入 `/data/system/job/jobs.xml` |
| `JobConcurrencyManager` | 根据并发容量、work type 和优先级给 job 分配执行上下文 |
| `JobServiceContext` | 绑定应用的 `JobService`，管理回调、超时、停止原因和 WakeLock |

Android 17 的 Controller 包括 `ConnectivityController`、`BatteryController`、`IdleController`、`StorageController`、`TimeController`、`ContentObserverController`、`QuotaController`、`BackgroundJobsController`、`DeviceIdleJobsController`、`PrefetchController`、`FlexibilityController` 等。Controller 之间并非简单的串行过滤器；每个 `JobStatus` 保存当前约束满足情况，状态变化后由服务重新选择可运行任务。

### JobStore、重启与持久化边界

调用 `setPersisted(true)` 的 job 会由 `JobStore` 写入 `/data/system/job/jobs.xml`，设备重启后可以恢复。使用该能力需要 `RECEIVE_BOOT_COMPLETED` 权限。未持久化的 job 不会因为系统重启自动回来。

持久化只覆盖 JobScheduler 登记信息。应用数据仍需自行保证事务完整性和幂等性；卸载应用、清除数据或取消 job 会改变这份状态。`JobInfo` 中的临时对象也受限制，例如 persisted job 不能依赖无法持久化的 `ClipData`。

AlarmManager 的 alarm 默认不会跨重启保留，应用通常在收到 `BOOT_COMPLETED` 后重新登记。两种 API 的差异在于调度记录能否由系统恢复，并不表示某个应用组件在重启后“消失”。

### JobService 生命周期与系统 WakeLock

`JobService.onStartJob()` 和 `onStopJob()` 在应用主线程回调。耗时工作不能直接堵在回调中。异步任务的正确骨架如下：

```kotlin
class SyncJobService : JobService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var running: Job? = null
    @Volatile private var stoppedBySystem = false

    override fun onStartJob(params: JobParameters): Boolean {
        stoppedBySystem = false
        running = scope.launch {
            val needsRetry = try {
                syncOnce()
                false
            } catch (_: CancellationException) {
                return@launch
            } catch (_: Exception) {
                true
            }
            if (!stoppedBySystem) {
                jobFinished(params, needsRetry)
            }
        }
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean {
        stoppedBySystem = true
        running?.cancel()
        return true
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
```

返回 `true` 表示工作离开回调后仍在进行，完成时必须调用 `jobFinished()`。`onStopJob()` 到来后，应用应尽快停止正在做的工作，并且不要再为这次执行调用 `jobFinished()`；返回值表示系统是否应按退避策略再次调度。示例用 `stoppedBySystem` 区分正常完成与系统停止，业务代码还应记录停止原因并处理并发竞态。

Android 17 的 `JobServiceContext.executeRunnableJob()` 创建并获取 `PARTIAL_WAKE_LOCK`，清理执行上下文时释放。因此，JobService 通常不需要再为同一段执行自行持锁。漏掉 `jobFinished()` 会让系统一直把任务视为运行中，直到完成、停止或超时清理，造成不必要的运行时间和功耗；它不会让 WakeLock 永久保留。

### 约束、时间窗口与 deadline

常用 `JobInfo.Builder` 条件如下：

| 条件 | API | 诊断时要注意的边界 |
|---|---|---|
| 网络 | `setRequiredNetworkType()` / `setRequiredNetwork()` | “有网络”不等于服务端可达；计费、漫游和能力也可能不符合 |
| 充电 | `setRequiresCharging()` | 仅在工作只适合充电时设置 |
| 设备空闲 | `setRequiresDeviceIdle()` | 这是显式 job 条件，不能直接等同于 Doze 的全部状态 |
| 电量不低 | `setRequiresBatteryNotLow()` | 阈值由系统决定 |
| 存储不低 | `setRequiresStorageNotLow()` | 适合会明显增加存储占用的工作 |
| 最早时间 | `setMinimumLatency()` | 表示最早可以开始，不是定时器 |
| 截止窗口 | `setOverrideDeadline()` | 到期后可放宽功能约束，仍可能受 Doze、配额、系统健康等限制 |
| 内容变化 | `addTriggerContentUri()` | 适合对 ContentProvider 变化做去抖后的处理 |
| 周期 | `setPeriodic()` | 周期运行有最小间隔，也会被批处理和跳过 |

`setOverrideDeadline()` 只适用于非周期 job。Android 5.0 曾以到期执行为目标；从 Android 6.0 起，公开文档已经不再给出按 deadline 执行的保证。到达 deadline 后，网络、充电等功能约束可以被视为满足，Doze、后台限制、配额和系统负载仍可能推迟任务。需要精确用户提醒时，应回到 AlarmManager 的对应场景。

条件越多，候选窗口通常越少。把“充电、非计费网络、设备空闲、电量不低”全部加上，看起来很节能，也可能让一项业务数据数天无法上传。每个约束都应回答一个具体问题：缺少它时，工作会失败，还是仅仅成本稍高？后者适合由业务做降级或分批，而不是一律阻塞调度。

### 优先级、Standby Bucket 与配额

JobScheduler 没有按 `schedule()` 调用顺序逐个运行。候选任务会同时受约束、优先级、应用状态、Standby Bucket、配额、系统负载和并发容量影响。

`JobInfo.Builder.setPriority()` 在 API 33 公开。优先级用于比较调用应用自己的 job；Android 14 起，文档进一步把排序范围描述为同一个 job namespace。它不是跨应用抢占 CPU 的全局优先级。重试 job 的有效优先级还可能逐步降低，因此把所有任务都设成 `PRIORITY_HIGH` 不会获得稳定的低延迟。

App Standby Buckets 的版本边界需要分开看：

- Android 9（API 28）引入 `ACTIVE`、`WORKING_SET`、`FREQUENT`、`RARE` 四档；
- `STANDBY_BUCKET_RESTRICTED` 常量在 API 30 加入，Android 11 默认并未启用该档；
- 档位越靠后，后台 job、alarm 和网络活动通常受到更严格限制；
- Bucket 是系统策略输入，不是应用可以可靠控制的开关。用户活跃使用可能改善状态，但应用不应依赖某次交互“领取”固定额度。

`QuotaController` 维护的是一组随版本演进的策略和执行历史，不能用一个固定的“每天 N 分钟”公式描述。设备厂商、系统版本、应用状态和 bucket 都会影响结果。Android 16 又扩大了运行时配额的适用范围：应用在前台时启动、随后进入后台的 job，以及与 Foreground Service 并行的 job，也不能再假设始终不计入后台 job 运行额度。

这里的 quota 记录 job 执行会话的 elapsed time，而不是读取线程的 CPU time。JobService 内部阻塞网络、等待 Binder 或主动 sleep，仍可能占用一次执行窗口；反过来，多线程并行也不会按各线程 CPU 时间简单相加成一个公开“CPU 配额”。如果材料使用“CPU 时间配额”一词，必须先核对它指的是系统的执行时长、厂商私有策略，还是应用自己的 CPU 预算。

一次 job 能否开始可按五个关口定位：调度请求被接受、显式与隐式约束满足、quota/standby policy 放行、并发槽位与优先级选中、`JobServiceContext` 成功绑定执行。开始后还可能因超时、约束丢失、thermal、Doze 或系统停止原因结束。`schedule()` 成功、`isReady()` 为真和 `onStartJob()` 已回调是三个不同状态。

排查积压时，显式约束和配额要同时查看。网络、电量都满足而 `PENDING_JOB_REASON_QUOTA` 长时间存在，继续放宽网络条件没有帮助；此时应减少触发频率、合并请求、缩短执行时间，或者重新判断任务是否属于用户发起的传输。

### Expedited Job

Android 12（API 31）加入 `setExpedited(true)`。Expedited Job 面向重要、短小、需要尽快开始的工作，默认优先级为 `PRIORITY_MAX`，同时使用更严格且会补充的专用配额。

Android 17 的 `JobInfo` 校验规则很明确：

- 只能设置网络、存储不低和持久化相关条件；
- 不能设置最小延迟、deadline、周期或 Content URI 触发；
- 不能同时标为 user-initiated；
- 优先级只能是 high 或 max。

直接使用 JobScheduler 时，如果调用当下没有 Expedited 配额，`schedule()` 会立即返回 `RESULT_FAILURE`，job 不会进入系统队列。已经 pending 的 Expedited Job 在后来缺少配额时，可以按普通 job 运行。应用应记录 `schedule()` 结果，并在 `JobParameters.isExpeditedJob()` 上区分本次是否获得了 expedited 语义。

WorkManager 通过 `setExpedited(OutOfQuotaPolicy)` 表达降级策略：

```kotlin
val request = OneTimeWorkRequestBuilder<SyncWorker>()
    .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
    .build()
```

`RUN_AS_NON_EXPEDITED_WORK_REQUEST` 会在配额不足时改成普通 work；`DROP_WORK_REQUEST` 会取消该 work。选择前者时，业务必须接受延后；选择后者时，业务必须接受丢弃。Expedited 也可能因约束或系统负载推迟，不能用来实现精确定时。

### User-Initiated Data Transfer

Android 14（API 34）加入 `setUserInitiated(true)`，简称 UIDT。它服务于用户明确发起、需要显示进度的网络传输，例如上传一段刚选中的长视频。

在 Android 14 的公开约束下，UIDT job 需要：

- 声明 `RUN_USER_INITIATED_JOBS`；
- 在应用处于前台或允许启动 Activity 的状态下调度；
- 指定网络约束；
- 运行期间通过 `JobService.setNotification()` 提供通知；
- 不设置延迟、deadline、周期、device-idle 或 Content URI 触发。

UIDT 不使用普通 job 配额，条件和系统健康允许时会尽快开始。用户从系统提供的入口停止任务后，应用不能悄悄把同一项传输重新排回去。自动同步、遥测上传等没有明确用户动作的任务不属于 UIDT。

## WorkManager 的架构与性能边界

### “可靠执行”具体涵盖什么

WorkManager 适合可延期、异步、需要在应用进程重启或设备重启后继续安排的工作。它把 `WorkSpec`、依赖关系、输入输出、重试次数和状态写入 Room 数据库，初始化时恢复未完成记录，再交给可用 Scheduler。

这项可靠性有清楚的边界：

- 应用进程被普通回收后，系统调度和数据库记录仍可让工作继续；
- 设备重启后，WorkManager 会重建符合条件的底层调度；
- 应用被 force-stop 后，系统会取消该包的 alarm 和 job；WorkManager 要等应用再次启动并完成初始化，才会检测并重新安排；
- 卸载应用或清除数据会删除 WorkManager 数据库；
- 约束长期不满足、配额不足或设备策略持续限制时，执行可以长时间推迟。

因此，“可靠”指调度状态可恢复，不等于立即、精确时刻或无条件完成。对业务数据仍要做幂等、断点续传和服务端去重。

### 当前稳定版中的调度器

Android 17 对应的内容以 WorkManager 2.11.2 为库版本基准，2.11 系列的 `minSdk` 是 23。其主要角色如下：

| 角色 | 职责 |
|---|---|
| `WorkDatabase` | 保存 `WorkSpec`、依赖、tag、进度与调度状态 |
| `Processor` | 启动和跟踪当前进程内 Worker |
| `SystemJobScheduler` | 用 JobScheduler 保留跨进程生命周期的调度资格 |
| `GreedyScheduler` | 进程存活时，机会性执行已经满足条件的 work |
| `SystemAlarmScheduler` | 旧版 WorkManager 在 API 14—22 的兼容路径 |

`SystemJobScheduler` 和 `GreedyScheduler` 可以同时存在：前者给系统登记任务，后者在进程已存活且条件满足时减少等待。不能把它们理解成启动时三选一的互斥分支。

在 Android 8.0—17 范围内，WorkManager 2.11 使用 `SystemJobScheduler`；`SystemAlarmScheduler` 只用于解释旧版库和 API 22 及以下设备的历史 trace。WorkManager 2.11 已不支持这些低版本设备。底层 JobScheduler 记录由 WorkManager 管理，WorkManager 自己持久化依赖和重试状态；不要依赖其内部 job ID 或自行修改对应系统 job。

WorkManager 2.10 起为底层 job 增加了更易读的 trace tag，因此较新版本的 `dumpsys jobscheduler` 更容易关联到具体 Worker。

### One-time、Periodic 与任务链

`OneTimeWorkRequest` 适合一次性可靠工作。需要防止应用每次启动都重复入队时，用 `enqueueUniqueWork()` 表达业务唯一性，并为替换、保留或追加选择明确策略。

`PeriodicWorkRequest` 的最小 repeat interval 是 15 分钟。flex interval 表示每个周期内允许执行的窗口。例如 30 分钟周期、15 分钟 flex，候选窗口位于该周期的后 15 分钟。约束、系统优化和配额仍会使执行推迟，某个周期也可能被跳过；它不会补跑每一个错过的时间点。

Periodic Work 的性能风险主要来自业务频率：

- 周期接近下限且每次只上传少量数据，容易制造数据库、网络和唤醒碎片；
- 条件反复变化会触发多轮约束评估；
- Worker 自己没有幂等保护时，重试和进程重启可能放大服务端请求。

优先在业务层累计一批数据，并设置足够宽的网络和时间窗口。不要为了“每 15 分钟检查一次有没有事情”创建空转 Worker；可由事件驱动的工作应在数据变化时入队。

任务链会把依赖关系持久化。一个节点完成后，WorkManager 更新数据库，解除后继节点的依赖，再把符合条件的 `WorkSpec` 交给 Scheduler。短链的管理成本通常可接受；若十几个节点每个只做几行内存计算，数据库状态迁移、调度边界和序列化可能比计算本身更显眼。必须独立重试、独立约束或独立观测的步骤适合拆开；只在同一进程内连续变换数据的步骤更适合放进一个 Worker 或普通协程。

### Long-running Worker 与 Android 16 配额

WorkManager 的 long-running worker 会借助 Foreground Service 和通知运行。它提供了较长执行窗口，却仍由 WorkManager 的 JobScheduler 路径承载。

Android 16 起，long-running worker 会消耗应用的 JobScheduler 运行时配额。若应用频繁执行长任务，配额耗尽会影响其他普通 work。官方建议按场景重新选型：

- 用户发起的大文件网络传输：优先考虑 UIDT；
- 用户持续可见、类型符合且需要长时间运行的非纯传输工作：评估直接 Foreground Service；
- 可分片、可延期的维护任务：拆成可恢复的普通 WorkRequest。

把 Worker 提升到前台，不会获得无限运行额度。Foreground Service 自身还有启动限制、service type、权限和分类型时长规则，详见 5.7 节。

## 后台任务选型

先判断工作是否必须跨进程生命周期保留，再判断用户是否刚刚明确发起、时效要求和持续时间。

| 场景 | 推荐入口 | 需要接受的限制 |
|---|---|---|
| 页面存活期间的短异步计算 | coroutine / executor | 进程退出即可取消；不要借持久调度器延长生命周期 |
| 可延期、需重试、需跨重启 | WorkManager one-time | 受约束、bucket、配额和系统负载影响 |
| 周期维护或汇总 | WorkManager periodic | 最短 15 分钟；不精确，周期可能跳过 |
| 用户刚触发的重要短任务 | Expedited Work / Expedited Job | 专用配额有限；仍可能延迟；要定义配额不足策略 |
| 用户发起的大文件上传或下载 | UIDT Job | Android 14+；网络传输限定；需权限、前台调度条件和通知 |
| 用户持续可见的长工作 | Foreground Service | 受后台启动、service type、权限和时长规则限制 |
| 闹钟、日历提醒等精确用户事件 | AlarmManager exact alarm | 需满足精确闹钟访问和版本政策；不用于普通轮询 |

一个常用判断顺序是：

1. 离开当前页面或进程后，任务还有没有业务价值？没有就用进程内并发工具。
2. 能否延后并由系统选择时机？可以就用普通 WorkManager。
3. 是否由用户刚刚明确发起且工作很短？评估 expedited。
4. 是否为用户发起的长网络传输？评估 UIDT。
5. 是否需要用户持续感知的长时间执行？检查 Foreground Service 的合规条件。
6. 是否要求用户可感知的精确时刻？再评估 exact alarm。

## Android 17 的调试接口

### pending reason 的 API 34、36、37 边界

JobScheduler 对“为什么还没运行”的公开观测分三步增加：

| API | 版本 | 返回内容 |
|---|---:|---|
| `getPendingJobReason(jobId)` | API 34 | 一个当前主原因；新代码优先使用复数接口 |
| `getPendingJobReasons(jobId)` | API 36 | 当前所有已知挂起原因 |
| `getPendingJobReasonsHistory(jobId)` | API 36 | 有限的原因变化历史和时间戳 |
| `getPendingJobReasonStats(jobId)` | API 37 | 每个原因的累计 `Duration` |

Android 17 的聚合统计可以这样读取：

```kotlin
if (Build.VERSION.SDK_INT >= 37) {
    val stats: Map<Int, Duration> =
        jobScheduler.getPendingJobReasonStats(jobId)
    val quotaWait = stats[
        JobScheduler.PENDING_JOB_REASON_QUOTA
    ] ?: Duration.ZERO
}
```

这里的时长不能直接相加成“总等待时间”。多个原因可以在同一时间段重叠，所以各项之和可能大于 job 的墙钟等待时长。统计不会跨设备重启保留；job 成功完成或被取消后也会清除。查询无效的 pending job 还可能抛出异常，调试代码要做好版本和状态检查。

`PENDING_JOB_REASON_DEVICE_STATE` 在 API 34 已存在，概括 Doze、省电模式、内存压力、热状态等系统条件。API 37 新增的是累计统计接口，并没有把它拆成一组固定的 thermal 或 battery-saver 子原因。

### ProfilingTrigger 的相关边界

Android 17 为 `ProfilingTrigger` 增加冷启动、OOM 和 excessive CPU kill 等触发类型：

- `TRIGGER_TYPE_COLD_START`：可触发 call stack sample 与 system trace；
- `TRIGGER_TYPE_OOM`：可触发 Java heap dump；
- `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`：在异常 CPU 使用导致进程终止后提供 call stack sample。

冷启动触发器可用于发现 WorkManager 初始化或积压任务是否占用了启动关键路径。excessive CPU kill 与 JobScheduler quota 是两套机制：前者针对进程异常 CPU 消耗后的诊断，后者决定 job 的调度与运行额度。没有公开依据时，不应写固定 CPU 阈值、检查周期，也不应把 kill 归因于 quota。

## 从系统到应用的观测面

### `dumpsys jobscheduler`

先用包名缩小输出：

```bash
adb shell dumpsys jobscheduler com.example.app
```

不同 Android 版本和厂商输出格式会变化，排查时重点寻找：

- job ID、namespace、service 与来源 UID；
- required / satisfied constraints；
- standby bucket、quota 与 bias/priority 信息；
- pending、active、ready 状态；
- 最近一次停止原因、失败次数和退避信息；
- WorkManager 的 `SystemJobService` 以及较新版本附带的 Worker trace tag。

若只搜业务 `JobService`，可能漏掉 WorkManager。API 23+ 的 WorkManager 底层 service 通常是 `androidx.work.impl.background.systemjob.SystemJobService`。

WorkManager 2.4.0 及以上还提供诊断广播。下面的命令会让 debug 构建把最近完成、正在运行和已经调度的 work 输出到 logcat：

```bash
adb shell am broadcast \
  -a "androidx.work.diagnostics.REQUEST_DIAGNOSTICS" \
  -p "com.example.app"
```

这份输出适合核对 UUID、Worker 类名、状态、unique name 和 tag。它来自 WorkManager 数据库视角，仍需与 `dumpsys jobscheduler` 的系统状态互查。

### Background Task Inspector

Android Studio 当前名称是 **Background Task Inspector**，入口位于 App Inspection。它要求 API 26+ 设备；WorkManager 检查能力要求 WorkManager 2.5.0 及以上。工具可以查看 Worker 状态、约束、输出和任务链，也可以取消、失败或重试选中的 work，适合开发期复现。

它观察的是 WorkManager 数据和应用进程，不替代系统侧 `dumpsys jobscheduler`。Inspector 显示 `ENQUEUED` 时，还要继续查看底层 job 是否受配额、Doze 或系统状态限制。

### Perfetto：事件与状态分开看

Android 17 的 Perfetto SQL 标准库提供两条 JobScheduler 观测路径。

`android.job_scheduler` 模块从 system_server 的 `ss` ATrace 类别解析调度事件，适合回答“何时登记、何时执行”。查询示例：

```sql
INCLUDE PERFETTO MODULE android.job_scheduler;

SELECT
  ts,
  dur,
  package_name,
  job_id,
  job_service_name
FROM android_job_scheduler_events
WHERE package_name = 'com.example.app'
ORDER BY ts;
```

`android.job_scheduler_states` 模块从 `ScheduledJobStateChanged` statsd atom 生成状态区间，包含约束、优先级、standby bucket、UIDT、启动延迟和停止原因等字段。trace 中采到该 atom 时，它更适合解释等待原因：

```sql
INCLUDE PERFETTO MODULE android.job_scheduler_states;

SELECT
  ts,
  dur,
  package_name,
  job_id,
  standby_bucket,
  has_charging_constraint,
  has_connectivity_constraint,
  is_requested_expedited_job,
  is_running_as_expedited_job
FROM android_job_scheduler_states
WHERE package_name = 'com.example.app'
ORDER BY ts;
```

两张表来自不同数据源。trace 没有启用相应 ATrace 类别或 statsd atom 时，查询为空不代表系统没有运行 job。分析功耗还应采集 CPU 调度、频率、网络和 `power` 相关数据，把 job 区间与 WakeLock、CPU 活跃和网络突发对齐。

### Android Vitals 的 excessive partial wake locks

Android Vitals 当前以 24 小时内累计至少 2 小时的非豁免 partial WakeLock 作为 bad session 条件。统计包含应用在后台或运行 Foreground Service 时持有的相关锁。音频、位置和 JobScheduler UIDT 等场景可按规则豁免。

当 28 天窗口内超过 5% 的应用 session 出现该问题，Play 的可见性可能受影响，并可能在详情页显示耗电警告。这个指标衡量 WakeLock 时长，不直接统计 job 次数。定位时应把 Play Console 的影响面与 Perfetto、batterystats 和任务日志结合起来。

系统在 `JobServiceContext` 中代持的锁同样提醒我们控制任务长度。使用 JobScheduler 并不会自动让业务代码节能；大循环、重复网络请求和遗漏结束信号仍会拉长执行区间。

## 一套可复现的排查顺序

遇到“WorkManager 一直 ENQUEUED”或“JobService 没回调”时，按下面顺序缩小范围：

1. **确认应用是否成功提交。** 记录 `schedule()` 结果或 WorkManager UUID，检查是否被 unique-work 策略替换、保留或取消。
2. **确认底层登记。** 用 `dumpsys jobscheduler <package>` 找业务 JobService 或 WorkManager `SystemJobService`。
3. **检查显式约束。** 对照 required 和 satisfied，特别关注网络能力、充电、存储和时间窗口。
4. **检查隐式策略。** 查看 standby bucket、quota、Doze、省电、热状态和后台限制；API 36+ 同时读取 pending reasons。
5. **确认是否曾启动又被停止。** 查看 stop reason、重试次数、退避和 Worker 日志；`onStopJob()` 后仍继续运行属于应用缺陷。
6. **抓取时序证据。** 用 Perfetto 对齐 schedule、state、WakeLock、CPU 和网络；必要时再用 bugreport/batterystats 看长时间聚合。
7. **回到选型。** 如果任务要求与 API 语义冲突，例如用 periodic work 做整点提醒，修补约束不会解决设计问题。

建议给每次业务任务生成稳定的关联 ID，把 WorkRequest UUID、job ID、服务端请求 ID 和完成状态记录在同一条诊断链中。日志应能区分“尚未开始、开始后失败、系统停止、业务取消、服务端已成功”。

## Android 8.0 到 Android 17 的演进

| 平台 | 相关变化 |
|---|---|
| Android 8.0 / API 26 | 后台 Service 限制生效；持久后台工作更依赖 JobScheduler 等受控入口 |
| Android 9 / API 28 | 引入四档 App Standby Buckets，job quota 与应用活跃程度结合 |
| Android 11 / API 30 | 增加 `STANDBY_BUCKET_RESTRICTED` 常量；该档在 Android 11 默认未启用 |
| Android 12 / API 31 | 公开 Expedited Job；限制从后台启动 Foreground Service |
| Android 13 / API 33 | 公开 `JobInfo.Builder.setPriority()` |
| Android 14 / API 34 | 加入 UIDT、单个 pending reason 查询；priority 文档明确 namespace 范围 |
| Android 16 / API 36 | 增加当前全部 pending reasons 与有限历史；运行时 quota 覆盖范围扩大 |
| Android 17 / API 37 | 增加 `getPendingJobReasonStats()`；ProfilingTrigger 增加冷启动、OOM、excessive CPU kill 触发类型 |

WorkManager 也在独立演进。当前稳定版 2.11.2 已将 `minSdk` 提升到 23，因此阅读旧资料时要同时确认平台版本和 WorkManager 版本。Android 8—17 设备上使用当前稳定版，不会走 API 14—22 的 `SystemAlarmScheduler` 兼容路径。

## 常见误区

### “WorkManager 会立刻执行”

WorkManager 保存并安排可靠工作。开始时间仍取决于约束、配额、设备状态和 Scheduler。要求用户立即看到进度时，应比较 expedited、UIDT 和 Foreground Service 的条件。

### “PeriodicWorkRequest 每个周期都准时运行”

15 分钟是最小 repeat interval，未提供精确周期承诺。flex、约束、Doze 和配额都可改变开始时间，某个周期也可能没有一次运行。

### “Expedited 可以绕过所有限制”

Expedited 使用专用配额，允许的约束种类也更少。直接 JobScheduler 调度可能在配额不足时失败；WorkManager 需要明确降级或丢弃策略。

### “Foreground Worker 不消耗 JobScheduler 配额”

Android 16 起，WorkManager long-running worker 仍会占用 JobScheduler 运行时配额。把普通 Worker 提升为前台不能修复频率过高或单次工作过重的问题。

### “force-stop 后 WorkManager 会自行唤醒应用”

force-stop 会取消该包的系统 job 和 alarm，并阻止后台入口恢复。用户再次启动应用、WorkManager 完成初始化后，未完成数据库记录才有机会重新调度。

### “给 job 加满约束最省电”

过多约束会缩小执行窗口并制造积压。任务在用户打开应用后集中恢复，可能带来明显 CPU 和网络峰值。只保留成功所需的硬条件，其余策略通过批量、限速和业务降级处理。

## 参考资料

### Android 17 AOSP

- `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobInfo.java`
- `frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobConcurrencyManager.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobStore.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/`
- `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/job_scheduler.sql`
- `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/job_scheduler_states.sql`

### AndroidX 源码

- [`ForceStopRunnable`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/work/work-runtime/src/main/java/androidx/work/impl/utils/ForceStopRunnable.java)
- [`WorkManagerImpl`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/work/work-runtime/src/main/java/androidx/work/impl/WorkManagerImpl.kt)
- [`Schedulers`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/work/work-runtime/src/main/java/androidx/work/impl/Schedulers.java)
- [`SystemJobScheduler`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/work/work-runtime/src/main/java/androidx/work/impl/background/systemjob/SystemJobScheduler.java)
- [`GreedyScheduler`](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/work/work-runtime/src/main/java/androidx/work/impl/background/greedy/GreedyScheduler.java)

### 官方文档

- [JobScheduler API reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [JobInfo.Builder API reference](https://developer.android.com/reference/android/app/job/JobInfo.Builder)
- [WorkManager overview](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Define work requests](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Long-running workers](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running)
- [WorkManager release notes](https://developer.android.com/jetpack/androidx/releases/work)
- [Debug WorkManager](https://developer.android.com/develop/background-work/background-tasks/testing/persistent/debug)
- [Background Task Inspector](https://developer.android.com/studio/inspect/task)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Android 16 behavior changes](https://developer.android.com/about/versions/16/behavior-changes-all)
- [Android 17 features and APIs](https://developer.android.com/about/versions/17/features)
- [Android Vitals: excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [Exact alarms](https://developer.android.com/develop/background-work/services/alarms)

### Perfetto

- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
