---


status: finalized
title: JobScheduler/WorkManager 调度与后台任务性能
chapter: '5.8'
section: '5.8'
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-08-11'
last_verified_against: AOSP android-17.0.0_r1, AOSP android-13.0.0_r1 / android-14.0.0_r1 historical TARE implementation and removal commit 4a98dd235a70, developer.android.com reference, perfetto.dev stdlib docs, Android Vitals docs
confidence: medium
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/05.26-android17-jobscheduler-service-cpu-quota.md"
  - "src/part1-fundamentals/ch05-cpu-power/23-android17-jobscheduler-system-throttling.md"
  - "src/part2-performance/ch11-power/08-tare-economic-model.md"
last_consolidated_at: "2026-08-11"
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
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/4a98dd235a708115db41e722776eff3ef9ed09fe
- type: aosp-historical
  path: android-14.0.0_r1/apex/jobscheduler/service/java/com/android/server/tare/InternalResourceService.java
- type: aosp-historical
  path: android-14.0.0_r1/apex/jobscheduler/service/java/com/android/server/tare/Analyst.java
- type: aosp-historical
  path: android-14.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/controllers/TareController.java
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
---


# 5.8 JobScheduler/WorkManager 调度与后台任务性能

## 为什么后台任务需要系统调度

后台同步、日志上传、缓存整理和资源预取都有一个共同特点：它们通常可以延后执行。若每个应用都用精确闹钟唤醒设备，再自行持有唤醒锁（WakeLock）阻止 CPU 休眠，系统就很难把多个应用的工作安排到同一个活跃窗口。单次任务也许只运行几十毫秒，大量零散唤醒仍会缩短 CPU 在深度空闲状态中的停留时间。

JobScheduler 让应用声明“做什么、需要哪些条件、最晚可以延后多久”，再由系统结合设备状态和所有应用的请求选择执行时机。WorkManager 在此基础上增加任务持久化、依赖关系、重试和版本兼容处理。两者都适合可延期的后台工作，但都不保证精确定时，也不允许任务无限运行。

需要回答三个问题：

1. 一个调度任务（job）从 `schedule()` 到 `JobService` 会经过哪些组件；
2. 任务迟迟不运行时，怎样区分约束、配额、设备状态和应用自身问题；
3. WorkManager、加急任务（Expedited Job）、用户发起的数据传输任务（User-Initiated Data Transfer，UIDT）、前台服务（Foreground Service）和精确闹钟分别适合什么场景。

设备休眠（Doze）、应用待机（App Standby）与后台执行限制的策略背景见 5.6 和 5.7 节。本文引用的平台源码以 `android-17.0.0_r1` 为基准。

## JobScheduler 的调度模型

### 声明执行条件，而非预订一个时刻

AlarmManager 面向时间点或时间窗口；JobScheduler 面向带条件的工作。下面的代码声明“联网且电量不低后再同步”，没有承诺在某个固定时刻开始：

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

这段代码只负责构建并提交任务。生产代码还要检查 `schedule()` 的返回值：`RESULT_SUCCESS` 只表示系统接受了任务，不表示任务已经启动；参数无效、达到调度限制或 Expedited Job 没有可用配额时，都可能返回 `RESULT_FAILURE`，也可能在构建阶段抛出异常。

AlarmManager 仍适用于闹钟、日历提醒等面向用户的精确时间事件。其精确闹钟访问权限、Doze 行为和不同重载的生命周期边界见 5.7 节。普通同步和维护任务应优先交给 JobScheduler 或 WorkManager，为系统保留合并任务和唤醒的空间。

### Android 17 源码中的核心组件

Android 17 的 JobScheduler 实现位于 `frameworks/base/apex/jobscheduler/`。应用侧 API 与系统服务分别存放在以下目录：

- `framework/java/android/app/job/`：`JobInfo`、`JobScheduler`、`JobService` 等公开 API；
- `service/java/com/android/server/job/`：`JobSchedulerService`、`JobStore`、`JobConcurrencyManager`、`JobServiceContext`；
- `service/java/com/android/server/job/controllers/`：网络、电量、空闲、存储、时间、配额等状态控制器。

下面的调用路径展示普通 job 从应用提交到 `JobService.onStartJob()` 回调的过程。其中 `system_server` 是承载 Android 核心系统服务的进程：

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

这条路径说明，job 出现在 `dumpsys jobscheduler` 中，只能证明 `JobSchedulerService` 正在跟踪它。任务还要经过状态控制器（Controller）的约束判断、配额检查与并发选择，之后才会进入某个 `JobServiceContext` 并绑定应用服务。

几个核心组件各自负责的范围如下：

| 组件 | Android 17 中的职责 |
|---|---|
| `JobSchedulerService` | 接收、校验、跟踪和排队 job，协调状态变化与执行 |
| `StateController` 子类 | 维护一类约束或策略状态，并通知服务重新评估相关 job |
| `JobStore` | 保存已登记 job；持久化 job 写入 `/data/system/job/jobs.xml` |
| `JobConcurrencyManager` | 根据并发容量、工作类型（work type）和优先级给 job 分配执行上下文 |
| `JobServiceContext` | 绑定应用的 `JobService`，管理回调、超时、停止原因和 WakeLock |

Android 17 的 Controller 包括 `ConnectivityController`、`BatteryController`、`IdleController`、`StorageController`、`TimeController`、`ContentObserverController`、`QuotaController`、`BackgroundJobsController`、`DeviceIdleJobsController`、`PrefetchController`、`FlexibilityController` 等。它们并非依次执行的一组过滤器。每个 `JobStatus` 都保存当前约束是否满足；状态发生变化后，服务会重新选择可运行任务。

### JobStore、重启与持久化边界

调用 `setPersisted(true)` 的 job 会由 `JobStore` 写入 `/data/system/job/jobs.xml`，设备重启后可以恢复。使用该能力需要 `RECEIVE_BOOT_COMPLETED` 权限。未持久化的 job 不会在系统重启后自动恢复。

持久化只覆盖 JobScheduler 的登记信息。应用仍需自行保证业务数据的事务完整性和幂等性；幂等性是指同一操作重复执行时，不会产生重复记录或其他额外副作用。卸载应用、清除数据或取消 job 都会改变这份状态。`JobInfo` 中的临时对象也受限制，例如持久化 job 不能依赖无法写入持久存储的 `ClipData`。

AlarmManager 的 alarm 默认不会跨重启保留，应用通常在收到设备启动完成广播 `BOOT_COMPLETED` 后重新登记。两种 API 的差异在于调度记录能否由系统恢复，与某个应用组件在重启后是否存在无关。

### JobService 生命周期与系统 WakeLock

`JobService.onStartJob()` 和 `onStopJob()` 都在应用主线程回调，因此不能直接在回调中执行耗时工作。下面的示例把同步任务交给 I/O 协程，并处理正常完成与系统停止两种情况：

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

`onStartJob()` 返回 `true` 表示工作在该回调结束后仍会继续，完成时必须调用 `jobFinished()`。收到 `onStopJob()` 后，应用应尽快停止当前工作，并且不再为这次执行调用 `jobFinished()`；`onStopJob()` 的返回值表示系统是否应按退避策略再次调度。示例用 `stoppedBySystem` 区分正常完成与系统停止，实际业务代码还应记录停止原因，并处理两个回调可能交错发生的并发竞态。

Android 17 的 `JobServiceContext.executeRunnableJob()` 会创建并持有 `PARTIAL_WAKE_LOCK`，在清理执行上下文时释放。这类部分唤醒锁允许屏幕关闭后 CPU 继续运行。因此，JobService 通常无须为同一段执行再次自行持锁。遗漏 `jobFinished()` 会让系统持续把任务视为运行中，直到任务完成、被停止或因超时而清理，造成不必要的运行时间和功耗；但这不会让 WakeLock 永久保留。

### 约束、时间窗口与 deadline

常用 `JobInfo.Builder` 条件如下：

| 条件 | API | 诊断时要注意的边界 |
|---|---|---|
| 网络 | `setRequiredNetworkType()` / `setRequiredNetwork()` | “有网络”不表示服务端一定可达；计费、漫游和网络能力也可能不符合要求 |
| 充电 | `setRequiresCharging()` | 仅在工作只适合充电时设置 |
| 设备空闲 | `setRequiresDeviceIdle()` | 这是显式 job 条件，不能直接等同于 Doze 的全部状态 |
| 电量不低 | `setRequiresBatteryNotLow()` | 阈值由系统决定 |
| 存储不低 | `setRequiresStorageNotLow()` | 适合会明显增加存储占用的工作 |
| 最早时间 | `setMinimumLatency()` | 表示最早可以开始，不是定时器 |
| 截止窗口 | `setOverrideDeadline()` | 到期后可放宽功能约束，仍可能受 Doze、配额、系统健康等限制 |
| 内容变化 | `addTriggerContentUri()` | 适合等待 ContentProvider 变化稳定后再处理，即对连续变化进行去抖（debounce） |
| 周期 | `setPeriodic()` | 周期运行有最小间隔，也会被批处理和跳过 |

`setOverrideDeadline()` 只适用于非周期 job。Android 5.0 曾以到期执行为目标；从 Android 6.0 起，公开文档已不再保证任务会在截止时间（deadline）执行。到达 deadline 后，网络、充电等显式条件可以被视为满足，但 Doze、后台限制、配额和系统负载仍可能推迟任务。需要精确用户提醒时，应使用 AlarmManager 的相应能力。

条件越多，可执行窗口通常越少。把“充电、非计费网络、设备空闲、电量不低”全部加上，看似节能，也可能使一项业务数据数天无法上传。设置每个约束前都应回答一个问题：缺少它时，工作会失败，还是仅仅成本稍高？如果只是成本较高，更适合由业务进行降级或分批处理，不必一律阻止调度。

### 优先级、Standby Bucket 与配额

JobScheduler 不会按照 `schedule()` 的调用顺序逐个运行任务。候选任务同时受约束、优先级、应用状态、待机桶（Standby Bucket）、配额、系统负载和并发容量影响。

`JobInfo.Builder.setPriority()` 在 API 33 公开。优先级用于比较调用应用自己的 job；Android 14 起，文档进一步将排序范围限定为同一个 job 命名空间（namespace，用于隔离同一应用内不同任务组的标识范围）。它不是跨应用争抢 CPU 的全局优先级。重试 job 的有效优先级还可能逐步降低，因此把所有任务都设为 `PRIORITY_HIGH`，也不会获得稳定的低延迟。

App Standby Buckets 的版本边界需要分开看：

- Android 9（API 28）引入 `ACTIVE`、`WORKING_SET`、`FREQUENT`、`RARE` 四档；
- `STANDBY_BUCKET_RESTRICTED` 常量在 API 30 加入，Android 11 默认并未启用该档；
- 档位越靠后，后台 job、alarm 和网络活动通常受到更严格限制；
- Bucket 是系统策略的输入，应用无法把它当作可可靠控制的开关。用户活跃使用可能改善状态，但应用不应假定某次交互一定能获得固定额度。

`QuotaController` 根据一组随版本演进的策略和执行历史管理配额，不能用固定的“每天 N 分钟”公式概括。设备厂商、系统版本、应用状态和 bucket 都会影响结果。Android 16 又扩大了运行时配额的适用范围：应用在前台时启动、随后进入后台的 job，以及与 Foreground Service 并行的 job，都不能再假定始终不计入后台 job 运行额度。

这里的 quota 记录 job 执行会话经过的实际时长（elapsed time），不读取线程真正占用 CPU 的时间（CPU time）。`JobService` 内部阻塞于网络、等待 Binder 或主动休眠（sleep），仍可能占用执行窗口；反过来，多线程并行也不会把各线程的 CPU 时间简单相加为一项公开“CPU 配额”。如果资料使用“CPU 时间配额”一词，必须先核对它指系统执行时长、厂商私有策略，还是应用自己的 CPU 预算。

一次 job 能否开始，可以按五项检查定位：调度请求已被接受；显式与隐式约束已满足；配额与待机策略（quota / standby policy）允许执行；任务获得并发槽位并通过优先级选择；`JobServiceContext` 成功绑定并执行服务。任务开始后，还可能因超时、约束失效、热状态（thermal）、Doze 或其他系统停止原因而结束。`schedule()` 成功、`isReady()` 为真和 `onStartJob()` 已回调，是三个不同状态。

排查任务积压时，应同时查看显式约束和配额。如果网络、电量均已满足，而 `PENDING_JOB_REASON_QUOTA` 长时间存在，继续放宽网络条件不会解决问题。此时应减少触发频率、合并请求、缩短执行时间，或重新判断该任务是否属于用户发起的传输。

### Expedited Job

Android 12（API 31）加入 `setExpedited(true)`。Expedited Job 适合重要、短小且需要尽快开始的工作，默认优先级为 `PRIORITY_MAX`，并使用限制更严格、会随时间恢复的专用配额。

Android 17 的 `JobInfo` 校验规则很明确：

- 只能设置网络、存储不低和持久化相关条件；
- 不能设置最小延迟、deadline、周期或 Content URI 触发；
- 不能同时标记为用户发起（user-initiated）；
- 优先级只能是 high 或 max。

直接使用 JobScheduler 时，如果调用时没有 Expedited 配额，`schedule()` 会立即返回 `RESULT_FAILURE`，job 不会进入系统队列。已经处于等待状态（pending）的 Expedited Job 后来缺少配额时，可以按普通 job 运行。应用应记录 `schedule()` 结果，并通过 `JobParameters.isExpeditedJob()` 判断本次执行是否仍具备 expedited 属性。

下面的代码通过 `setExpedited(OutOfQuotaPolicy)` 声明配额不足时的处理策略：

```kotlin
val request = OneTimeWorkRequestBuilder<SyncWorker>()
    .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
    .build()
```

在这段代码中，`RUN_AS_NON_EXPEDITED_WORK_REQUEST` 会在配额不足时将任务改为普通 work；另一选项 `DROP_WORK_REQUEST` 会取消该 work。选择前者时，业务必须接受延后；选择后者时，业务必须接受任务被丢弃。Expedited 仍可能因约束或系统负载而推迟，不能用于精确定时。

### User-Initiated Data Transfer

Android 14（API 34）加入 `setUserInitiated(true)`，简称 UIDT。它适用于由用户明确发起、需要显示进度的网络传输，例如上传一段刚选中的长视频。

在 Android 14 的公开约束下，UIDT job 需要：

- 声明 `RUN_USER_INITIATED_JOBS`；
- 在应用处于前台，或处于允许启动 Activity 的状态时调度；
- 指定网络约束；
- 运行期间通过 `JobService.setNotification()` 提供通知；
- 不设置延迟、deadline、周期、device-idle 或 Content URI 触发。

UIDT 不使用普通 job 配额，在约束满足且系统状态允许时会尽快开始。用户从系统提供的入口停止任务后，应用不能在没有提示的情况下重新提交同一项传输。自动同步、遥测上传等缺少明确用户动作的任务不属于 UIDT。

## WorkManager 的架构与性能边界

### “可靠执行”具体涵盖什么

WorkManager 适合可延期、异步，而且需要在应用进程或设备重启后继续安排的工作。它将 `WorkSpec`、依赖关系、输入输出、重试次数和状态写入 Room 数据库；初始化时恢复未完成记录，再交给可用的调度器（Scheduler）。Room 是 AndroidX 提供的 SQLite 数据库访问层。

这项可靠性有清楚的边界：

- 应用进程被系统常规回收后，系统调度和数据库记录仍可让工作继续；
- 设备重启后，WorkManager 会重建符合条件的底层调度；
- 应用被强行停止（force-stop）后，系统会取消该包的 alarm 和 job；WorkManager 要等应用再次启动并完成初始化，才会检测并重新安排任务；
- 卸载应用或清除数据会删除 WorkManager 数据库；
- 约束长期不满足、配额不足或设备策略持续限制时，执行可以长时间推迟。

因此，这里的“可靠”是指调度状态可以恢复，不表示任务会立即执行、在精确时刻执行或无条件完成。业务数据仍需支持幂等处理、断点续传和服务端去重。

### 当前稳定版中的调度器

Android 17 对应的内容以 WorkManager 2.11.2 为库版本基准，2.11 系列的 `minSdk` 是 23。其主要角色如下：

| 角色 | 职责 |
|---|---|
| `WorkDatabase` | 保存 `WorkSpec`、依赖、标签（tag）、进度与调度状态 |
| `Processor` | 启动并跟踪当前进程内的 Worker |
| `SystemJobScheduler` | 通过 JobScheduler 保留跨进程生命周期的调度记录 |
| `GreedyScheduler` | 进程存活时，立即尝试执行已经满足条件的 work |
| `SystemAlarmScheduler` | 旧版 WorkManager 在 API 14—22 的兼容路径 |

`SystemJobScheduler` 和 `GreedyScheduler` 可以同时存在：前者向系统登记任务，后者在进程已存活且条件满足时减少等待。它们不是启动时只能选择其一的互斥分支。

在 Android 8.0—17 范围内，WorkManager 2.11 使用 `SystemJobScheduler`；`SystemAlarmScheduler` 只用于解释旧版库和 API 22 及以下设备的历史 trace。WorkManager 2.11 已不支持这些低版本设备。系统中的 JobScheduler 记录由 WorkManager 管理，WorkManager 还会自行持久化依赖与重试状态；应用不应依赖其内部 job ID，也不应自行修改相应的系统 job。

WorkManager 2.10 起为系统 job 增加了更易读的跟踪标签（trace tag），因此较新版本的 `dumpsys jobscheduler` 输出更容易关联到具体 Worker。

### One-time、Periodic 与任务链

`OneTimeWorkRequest` 适合一次性可靠工作。需要防止应用每次启动都重复入队时，可以用 `enqueueUniqueWork()` 表达业务唯一性，并明确选择替换、保留或追加策略。

`PeriodicWorkRequest` 的最小重复间隔（repeat interval）是 15 分钟。弹性间隔（flex interval）表示每个周期内允许执行的窗口。例如，周期为 30 分钟、flex 为 15 分钟时，候选窗口位于该周期的后 15 分钟。约束、系统优化和配额仍会推迟执行，某个周期也可能被跳过；系统不会补执行每一个错过的时间点。

周期工作（Periodic Work）的性能风险主要来自业务频率：

- 周期接近下限且每次只上传少量数据，容易产生零散的数据库操作、网络请求和设备唤醒；
- 条件反复变化会触发多轮约束评估；
- Worker 自己没有幂等保护时，重试和进程重启可能放大服务端请求。

应优先在业务层累计一批数据，并设置足够宽的网络和时间窗口。不要为了“每 15 分钟检查一次有没有事情”创建没有实际工作的 Worker；可以由事件驱动的任务，应在数据变化时入队。

任务链会持久化节点之间的依赖关系。一个节点完成后，WorkManager 更新数据库，解除后继节点的依赖，再将符合条件的 `WorkSpec` 交给 Scheduler。短链的管理成本通常可以接受；如果十几个节点各自只执行几行内存计算，数据库状态迁移、跨调度阶段和数据序列化的成本可能超过计算本身。需要独立重试、独立约束或独立观测的步骤适合分开；只在同一进程内连续转换数据的步骤，更适合放在一个 Worker 或普通协程中。

### Long-running Worker 与 Android 16 配额

WorkManager 的长时运行 Worker（long-running worker）会借助 Foreground Service 和通知运行。它提供较长的执行窗口，但任务仍由 WorkManager 的 JobScheduler 路径承载。

Android 16 起，long-running worker 会消耗应用的 JobScheduler 运行时配额。若应用频繁执行长任务，配额耗尽会影响其他普通 work。官方建议按场景重新选型：

- 用户发起的大文件网络传输：优先考虑 UIDT；
- 用户持续可见、类型符合且需要长时间运行的非纯传输工作：评估直接 Foreground Service；
- 可分片、可延期的维护任务：拆成可恢复的普通 WorkRequest。

将 Worker 提升到前台不会获得无限运行额度。Foreground Service 本身还受启动限制、服务类型（service type）、权限和分类型时长规则约束，详见 5.7 节。

## 后台任务选型

选择 API 时，先判断工作是否必须跨进程生命周期保留，再判断它是否由用户刚刚明确发起，以及允许延后的时间和预计持续时长。

| 场景 | 推荐入口 | 需要接受的限制 |
|---|---|---|
| 页面存活期间的短异步计算 | 协程（coroutine）/ 线程执行器（executor） | 进程退出即可取消；不要借持久调度器延长生命周期 |
| 可延期、需重试、需跨重启 | WorkManager one-time | 受约束、bucket、配额和系统负载影响 |
| 周期维护或汇总 | WorkManager periodic | 最短 15 分钟；不精确，周期可能跳过 |
| 用户刚触发的重要短任务 | Expedited Work / Expedited Job | 专用配额有限；仍可能延迟；要定义配额不足策略 |
| 用户发起的大文件上传或下载 | UIDT Job | Android 14+；网络传输限定；需权限、前台调度条件和通知 |
| 用户持续可见的长工作 | Foreground Service | 受后台启动、service type、权限和时长规则限制 |
| 闹钟、日历提醒等精确用户事件 | AlarmManager exact alarm | 需满足精确闹钟访问和版本政策；不用于普通轮询 |

一个常用判断顺序是：

1. 离开当前页面或进程后，任务是否仍有业务价值？如果没有，使用进程内并发工具。
2. 任务能否延后，并由系统选择执行时机？如果可以，使用普通 WorkManager。
3. 是否由用户刚刚明确发起，而且工作很短？评估 expedited。
4. 是否为用户发起的长网络传输？评估 UIDT。
5. 是否需要用户持续感知的长时间执行？检查 Foreground Service 的合规条件。
6. 是否要求在用户可感知的精确时刻执行？再评估 exact alarm。

## Android 17 的调试接口

### pending reason 的 API 34、36、37 边界

JobScheduler 分阶段增加了查询“任务为何仍在等待”的公开接口。这里的等待原因称为 pending reason：

| API | 版本 | 返回内容 |
|---|---:|---|
| `getPendingJobReason(jobId)` | API 34 | 一个当前主原因；新代码优先使用复数接口 |
| `getPendingJobReasons(jobId)` | API 36 | 当前所有已知挂起原因 |
| `getPendingJobReasonsHistory(jobId)` | API 36 | 有限的原因变化历史和时间戳 |
| `getPendingJobReasonStats(jobId)` | API 37 | 每个原因的累计 `Duration` |

下面的示例在 API 37 及以上读取各 pending reason 的累计时长，并取出配额等待时间：

```kotlin
if (Build.VERSION.SDK_INT >= 37) {
    val stats: Map<Int, Duration> =
        jobScheduler.getPendingJobReasonStats(jobId)
    val quotaWait = stats[
        JobScheduler.PENDING_JOB_REASON_QUOTA
    ] ?: Duration.ZERO
}
```

这段代码返回的各项时长不能直接相加为“总等待时间”。多个原因可以在同一时间段重叠，因此各项之和可能大于 job 从开始等待到查询时经过的墙钟时间（wall-clock time）。统计不会跨设备重启保留；job 成功完成或被取消后也会清除。查询无效的 pending job 还可能抛出异常，调试代码需要检查系统版本和任务状态。

`PENDING_JOB_REASON_DEVICE_STATE` 在 API 34 已存在，用来概括 Doze、省电模式、内存压力、热状态等系统条件。API 37 新增累计统计接口，但没有将该原因细分为一组固定的 thermal 或 battery-saver 子原因。

### ProfilingTrigger 的相关边界

Android 17 为 `ProfilingTrigger`（达到指定事件时启动性能采集的配置）增加了冷启动、内存不足（Out of Memory，OOM）和 CPU 使用过量终止（excessive CPU kill）等触发类型：

- `TRIGGER_TYPE_COLD_START`：可触发调用栈采样（call stack sample）与系统跟踪（system trace）；
- `TRIGGER_TYPE_OOM`：可触发 Java 堆转储（heap dump）；
- `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`：在异常 CPU 使用导致进程终止后提供调用栈采样。

冷启动触发器可用于判断 WorkManager 初始化或积压任务是否占用了应用启动的关键路径。excessive CPU kill 与 JobScheduler quota 是两套不同机制：前者用于诊断进程因异常 CPU 消耗而被终止的事件，后者决定 job 的调度与运行额度。没有公开依据时，不应给出固定的 CPU 阈值或检查周期，也不应将进程终止归因于 quota。

## 从系统到应用的观测面

### `dumpsys jobscheduler`

`dumpsys jobscheduler` 用于读取系统侧保存的 JobScheduler 状态。下面的命令只查看指定包名，以缩小输出范围：

```bash
adb shell dumpsys jobscheduler com.example.app
```

命令中的 `com.example.app` 需要替换为目标应用包名。不同 Android 版本和厂商的输出格式会变化，排查时重点查找：

- job ID、namespace、Service 与来源用户标识符（User Identifier，UID）；
- 要求的约束与已满足的约束（required / satisfied constraints）；
- standby bucket、quota 与系统偏好值 / 优先级（bias / priority）信息；
- pending、active、ready 状态；
- 最近一次停止原因、失败次数和退避信息；
- WorkManager 的 `SystemJobService`，以及较新版本附带的 Worker trace tag。

如果只搜索业务 `JobService`，可能遗漏 WorkManager。API 23 及以上的 WorkManager 系统侧 Service 通常是 `androidx.work.impl.background.systemjob.SystemJobService`。

WorkManager 2.4.0 及以上还提供诊断广播。下面的命令会让调试版本（debug build）把最近完成、正在运行和已经调度的 work 输出到 Android 日志工具 Logcat：

```bash
adb shell am broadcast \
  -a "androidx.work.diagnostics.REQUEST_DIAGNOSTICS" \
  -p "com.example.app"
```

这份输出适合核对通用唯一标识符（Universally Unique Identifier，UUID）、Worker 类名、状态、唯一工作名称（unique name）和 tag。它反映 WorkManager 数据库中的状态，仍需与 `dumpsys jobscheduler` 的系统状态相互核对。

### Background Task Inspector

Android Studio 中的工具名是 **Background Task Inspector**（后台任务检查器），入口位于 App Inspection。它要求 API 26 及以上设备；检查 WorkManager 还要求 WorkManager 2.5.0 及以上。该工具可以查看 Worker 状态、约束、输出和任务链，也可以取消选中的 work，或将其标记为失败、重新执行，适合开发阶段复现问题。

它观察的是 WorkManager 数据和应用进程，不能替代系统侧的 `dumpsys jobscheduler`。Inspector 显示 `ENQUEUED` 时，还要继续查看系统 job 是否受到配额、Doze 或系统状态限制。

### Perfetto：事件与状态分开看

Android 17 的 Perfetto SQL 标准库提供两种观察 JobScheduler 的方式，分别对应调度事件和状态区间。

`android.job_scheduler` 模块从 `system_server` 的 `ss` ATrace 类别解析调度事件。ATrace 是 Android 将 framework 事件写入系统 trace 的机制，这个模块适合回答“何时登记、何时执行”。下面的 SQL 查询目标包的调度事件：

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

查询结果按时间列出 job 的开始时间、持续时长、包名、job ID 和 Service 名称。

`android.job_scheduler_states` 模块从 `ScheduledJobStateChanged` statsd atom 生成状态区间。statsd atom 是 Android 统计服务记录的一类结构化系统事件；这里的事件包含约束、优先级、standby bucket、UIDT、启动延迟和停止原因等字段。trace 采集到该 atom 时，它更适合解释等待原因：

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

这段查询列出目标包各 job 的状态持续区间和部分约束字段。两张表来自不同数据源；trace 没有启用相应 ATrace 类别或 statsd atom 时，查询为空不表示系统没有运行 job。分析功耗时还应采集 CPU 调度、频率、网络和 `power` 相关数据，将 job 区间与 WakeLock、CPU 活动和短时间密集出现的网络请求相互对齐。

### Android Vitals 的 excessive partial wake locks

Android Vitals 当前将“24 小时内累计持有至少 2 小时的非豁免 partial WakeLock”视为一次不良会话（bad session）。统计包括应用在后台或运行 Foreground Service 时持有的相关锁；音频、位置和 JobScheduler UIDT 等场景可按规则豁免。

当 28 天窗口内超过 5% 的应用会话（session）出现该问题时，应用在 Google Play 中的可见性可能受影响，详情页也可能显示耗电警告。这个指标衡量 WakeLock 持有时长，不直接统计 job 次数。定位时，应结合 Play Console 中受影响的用户范围、Perfetto、`batterystats` 和任务日志。

系统在 `JobServiceContext` 中代为持有的锁，也说明任务时长需要受到控制。使用 JobScheduler 不会自动使业务代码节能；大循环、重复网络请求和遗漏结束信号仍会延长执行区间。

## 一套可复现的排查顺序

遇到“WorkManager 一直处于 `ENQUEUED`”或“`JobService` 没有回调”时，可以按下面的顺序缩小问题范围：

1. **确认应用是否成功提交。** 记录 `schedule()` 结果或 WorkManager UUID，检查是否被 unique-work 策略替换、保留或取消。
2. **确认底层登记。** 用 `dumpsys jobscheduler <package>` 找业务 JobService 或 WorkManager `SystemJobService`。
3. **检查显式约束。** 对照 required 和 satisfied，特别关注网络能力、充电、存储和时间窗口。
4. **检查隐式策略。** 查看 standby bucket、quota、Doze、省电、热状态和后台限制；API 36 及以上同时读取 pending reasons。
5. **确认是否曾启动又被停止。** 查看 stop reason、重试次数、退避和 Worker 日志；`onStopJob()` 后仍继续运行属于应用缺陷。
6. **采集时序证据。** 用 Perfetto 对齐调度（schedule）、状态（state）、WakeLock、CPU 和网络活动；必要时再用系统诊断报告（bugreport）/ `batterystats` 查看长时间汇总。
7. **重新检查 API 选择。** 如果任务要求与 API 用途冲突，例如使用 periodic work 做整点提醒，调整约束也无法解决设计问题。

建议为每次业务任务生成稳定的关联 ID，并在同一组诊断记录中写入 WorkRequest UUID、job ID、服务端请求 ID 和完成状态。这样可以通过一个标识追踪跨组件的同一任务。日志还应区分“尚未开始、开始后失败、系统停止、业务取消、服务端已成功”。

## Android 8.0 到 Android 17 的演进

### TARE 是 Android 13—14 的历史分支

TARE（The Android Resource Economy，Android 资源经济系统）曾尝试通过应用资源信用（Android Resource Credits，ARC）账户，以及动作账单（action bill）、价格（price）和奖励（reward），协调 JobScheduler 与 AlarmManager 的后台资源。它出现在 Android 13—14 的 AOSP 源码中；Android 14 的 `EconomyManager` 仍标记为隐藏 API `@hide` / 测试 API `@TestApi`，默认模式为关闭，因此第三方应用从未获得可以依赖的公开配额规则。

历史实现也不是“按每个 UID 的毫安时（mAh）直接扣除 ARC”。`Analyst` 读取整机灭屏后经过的时间（screen-off realtime）、灭屏放电量（screen-off discharge）与电量变化，作为调节全局消耗上限（consumption limit）的校准信号；具体应用的账目来自调度动作（action）和策略（policy）。BatteryStats 的耗电归因与 TARE 的应用账本衡量对象不同，不能互相替代。

AOSP 提交 [`4a98dd235a708115db41e722776eff3ef9ed09fe`](https://android.googlesource.com/platform/frameworks/base/+/4a98dd235a708115db41e722776eff3ef9ed09fe) 于 2024 年 3 月删除了 `EconomyManager`、`InternalResourceService`、`TareController`、`CONSTRAINT_TARE_WEALTH`、`resource_economy` 服务和相关 dump 路径，并恢复 `QuotaController` 的持续生效。Android 15—17 均不包含 TARE；在这些版本中，`PENDING_JOB_REASON_QUOTA` 表示 JobScheduler 的时间或次数配额，不能解释为 ARC 余额不足，也不应再用 `dumpsys tare` 排查问题。原始设备制造商（Original Equipment Manufacturer，OEM）若保留同名私有实现，需要针对相应系统构建单独取证。

| 平台 | 相关变化 |
|---|---|
| Android 8.0 / API 26 | 后台 Service 限制生效；持久后台工作更依赖 JobScheduler 等受控入口 |
| Android 9 / API 28 | 引入四档 App Standby Buckets，job quota 与应用活跃程度结合 |
| Android 11 / API 30 | 增加 `STANDBY_BUCKET_RESTRICTED` 常量；该档在 Android 11 默认未启用 |
| Android 12 / API 31 | 公开 Expedited Job；限制从后台启动 Foreground Service |
| Android 13 / API 33 | 公开 `JobInfo.Builder.setPriority()`；AOSP 引入隐藏的 TARE 实验实现 |
| Android 14 / API 34 | 加入 UIDT、单个 pending reason 查询；priority 文档明确 namespace 范围；TARE 仍为隐藏、默认关闭的内部路径 |
| Android 15 / API 35 | AOSP 已删除 TARE，JobScheduler 继续使用 quota、后台资格、Doze、显式约束与设备状态 |
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
