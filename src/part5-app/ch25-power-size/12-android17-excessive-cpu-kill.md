---
title: "Android 17 Excessive CPU Kill 与后台任务功耗治理"
chapter: "25.12"
section: "25.12"
status: finalized
drafted_date: "2026-05-20"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-08-05"
last_verified_against: "Android Developers ProfilingManager / ProfilingTrigger docs, AOSP android-17.0.0_r1 frameworks/base and packages/modules/Profiling, DeepResearch 2026-05-26/2026-06-03"
reviewed_date: "2026-08-05"
reviewed_by: "hermes-aiw-review-finalize-apply"
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-08-05T10:05:53+08:00"
last_review_finalize_run_id: "20260805-100553-af78308e"
confidence: high
tags: [android-17, profiling-trigger, jobscheduler, workmanager, power, background-task]
related_chapters: ["5.10", "25.2", "25.4", "26.12", "11.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "研究素材/官方文档/章节深挖"
gap_score: 18
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-19-android-jobscheduler-profilingtrigger-version-boundary.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-26-android17-excessive-cpu-kill-mechanism-boundary.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-03-android17-profilingmanager-excessive-cpu-version-boundary.md"
  - type: research
    path: "/Users/gracker/.openclaw/workspace/AutoResearchClaw/state/researched-gaps.json"
  - type: internal
    path: "src/part5-app/ch26-observability/12-versioned-diagnostics.md"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
---

# 25.12 Android 17 Excessive CPU Kill 与后台任务功耗治理

## 问题范围

Android 17 / API 37 新增 `ProfilingTrigger.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`。当系统以 `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 记录一次 excessive CPU 终止时，这个触发器可以让已注册的应用收到对应的性能分析结果。它提供事后证据，不负责决定任务应否执行。

这里有一条容易混淆的版本边界：Android 17 新增的是公开取证入口，系统终止高 CPU 缓存进程的机制并非 Android 17 才出现。`ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 从 API 30 已经公开。Android 17 把既有的终止路径接入 `ProfilingManager`，使应用有机会拿到终止前的系统跟踪快照。

源码锚点为 `android-17.0.0_r1` 的 `ActivityManagerService`、`ActivityManagerConstants`、`CachedAppOptimizer` 和 `packages/modules/Profiling`。JobScheduler 与 WorkManager 的调度规则分别见 5.10、25.4 节；这里说明进程为何被 excessive CPU 路径终止、如何收集证据，以及后台任务如何避免留下失控的 CPU 工作。

## Android 17 excessive CPU 触发器的能力边界

`ProfilingManager` 从 Android 15 / API 35 开始提供应用主动请求的性能分析。API 36 增加 `ProfilingTrigger` 与触发器注册接口，API 37 再增加 excessive CPU、冷启动、OOM 等触发类型。[`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`](https://developer.android.com/reference/android/os/ProfilingTrigger#TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE) 的常量值为 9，触发条件是应用以 `REASON_EXCESSIVE_RESOURCE_USAGE` 被终止。

应用需要提前注册触发器，并通过 `registerForAllProfilingResults()` 注册全局监听器。结果可能在应用下次启动并重新注册监听器后送达。`ProfilingResult` 的公开字段只有：

- `getTriggerType()`：结果来自哪个触发器；
- `getResultFilePath()`：成功时的文件路径；
- `getTag()`：调用方标签或系统附加信息；
- `getErrorCode()` 与 `getErrorMessage()`：失败原因。

`ProfilingResult` 没有 `getProfilingType()`、pid 或任务 ID。归档代码不能调用不存在的方法，也不能只凭文件名猜任务来源。

Android 17 功能概览把该产物描述为调用栈采样，但 API 参考文档与 `android-17.0.0_r1` 的 [`ProfilingTrigger.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java#117) 都写明会返回运行中系统跟踪的快照；同一版本的 [`ProfilingService.getProfilingTypeForTrigger()`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java#2225) 也把该触发器映射到 `PROFILING_TYPE_SYSTEM_TRACE`。这里采用 API 参考文档与源码一致的“系统跟踪快照”口径。

触发器结果是尽力而为的。系统后台跟踪并非持续运行，系统级与应用自定义频率限制也可能拒绝一次采集。应用被终止时没有收到回调，并不等于没有发生 excessive CPU 终止；结果错误或文件路径为空时也必须保留错误码。

## Android 17 源码中的终止条件

Android 17 的 [`ActivityManagerService.checkExcessivePowerUsage()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java#16057) 先刷新 CPU 统计，再遍历 LRU 进程。只有进程状态数值大于或等于 `PROCESS_STATE_HOME` 时，才进入这条 CPU 检查路径。换成应用工程语言，就是 Home 与缓存进程；前台进程、前台服务进程和正在以 service 状态执行的进程不在这一条件中。

系统为每个候选进程计算：

```text
cpuPercent = processCpuTimeDelta * 100 / checkWindowUptime
```

这条公式的用途是说明源码判定量：分子是进程内各线程累计消耗的 CPU 时间增量，分母是相邻检查之间的墙上时间。多线程并行时，累计 CPU 时间可以高于单核墙上时间，因此这个百分比不能直接等同于性能面板里的整机 CPU 占比。

`android-17.0.0_r1` 的 [`ActivityManagerConstants`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java#213) 给出以下默认配置：

| 配置项 | AOSP 默认值 | 使用位置 |
| --- | ---: | --- |
| `POWER_CHECK_INTERVAL` | 5 分钟 | CPU 统计检查窗口 |
| `POWER_CHECK_MAX_CPU_1` | 25% | 进程进入不重要状态后的第一个窗口 |
| `POWER_CHECK_MAX_CPU_2` | 25% | 第二个窗口；Home 进程不会使用更低的后两档 |
| `POWER_CHECK_MAX_CPU_3` | 10% | 第三个窗口 |
| `POWER_CHECK_MAX_CPU_4` | 2% | 更长时间处于缓存状态后 |

这些数字是 AOSP r1 的默认实现值，不是第三方应用可依赖的兼容性承诺。它们可以从 `Settings.Global.ACTIVITY_MANAGER_CONSTANTS` 覆盖，厂商系统也可能修改配置或相关路径。应用不应围绕某个阈值设计“刚好不被终止”的轮询。

达到当前阈值后，AMS 会再次确认进程仍处于 Home 或缓存状态，然后调用 `killLocked()`，记录：

- `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE`；
- 平台内部的 `SUBREASON_EXCESSIVE_CPU`；
- 包含 CPU 时间、检查窗口和阈值的内部终止描述；
- `EXCESSIVE_CPU_USAGE_REPORTED` 统计事件。

随后 AMS 调用 `sendKillExcessiveCpuProfilingTrigger()`。这里的顺序说明触发器用于保存终止前已经存在的后台跟踪，不会在进程死亡后重新采样它。

Android 17 r1 还有两条相邻路径需要留意：归属于应用的 phantom process 可能因同一 CPU 判定被终止；[`CachedAppOptimizer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java#2469) 在缓存进程反复因 Binder 事务无法冻结时，也使用 `REASON_EXCESSIVE_RESOURCE_USAGE`、内部 excessive CPU 子原因和同一性能分析触发器。因此，看到该触发器后仍要检查跟踪文件与退出描述，不能先入为主地认定业务代码一定是纯计算死循环。

## 与 JobScheduler 配额的关系

JobScheduler 配额控制 job 的执行资格与可用运行时间，输入包括待机分桶、约束、历史执行和系统状态。excessive CPU 路径检查的是 Home 或缓存进程在采样窗口里的进程 CPU 时间。两条路径没有直接调用关系。

| 维度 | JobScheduler / WorkManager 配额 | `KILL_EXCESSIVE_CPU_USAGE` 触发器 |
|------|----------------------------------|------------------------------------|
| 决策时机 | job 等待、启动、运行和停止阶段 | 进程处于 Home 或缓存状态后的周期检查 |
| 决策对象 | job / work 的调度资格和运行配额 | 应用进程或归属它的 phantom process |
| 应用可控项 | 约束、唯一任务、退避、任务粒度、停止响应 | 触发器注册、结果监听、证据归档与任务生命周期 |
| 典型证据 | JobDebugInfo、`dumpsys jobscheduler`、WorkInfo / JobParameters 停止原因 | `ApplicationExitInfo`、`ProfilingResult`、Perfetto 跟踪文件 |
| 容易混淆之处 | 配额耗尽不是进程 CPU 终止 | 收到跟踪文件不表示 JobScheduler 参与了终止 |

一个正在由 `SystemJobService` 执行的 Worker 通常具有 service 级进程状态，不能仅凭“后台任务 CPU 很高”断定它会进入上述缓存进程检查。Worker 与 excessive CPU 终止更常见的关联是：任务结束或被停止后，线程、原生任务、协程或子进程仍在运行，宿主进程随后降为缓存状态。定位时要先检查工作是否越过了 Worker 生命周期。

## 应用侧高 CPU 后台任务的常见成因

后台 CPU 问题常见于任务生命周期、幂等性和取消处理：

- 周期任务重复注册：相同业务建立了多条周期任务，约束满足时一起执行。
- 链式任务堆积：压缩、加密、上传和清理形成长链，失败策略又让前置工作重复计算。
- 重试策略没有分类：鉴权失败、服务端错误、网络不可用和本地数据损坏都返回 `Result.retry()`。
- 取消没有传入底层：Worker 已被停止，FFmpeg、压缩库、数据库重算或 JNI 线程仍继续运行。
- 线程与协程脱离作用域：使用全局作用域、独立线程池或未跟随 Worker 取消的回调，任务返回后仍占用 CPU。
- 热轮询：等待远端状态、文件或锁时使用短间隔循环，没有事件通知或有上限的退避。
- 全量处理缺少分片：日志、媒体、索引和离线模型更新一次处理全部数据，无法在约束变化时停止。
- 多进程边界遗漏：主进程认为任务已取消，独立工具进程或子进程没有收到终止信号。

系统看到的是进程 CPU 时间，无法理解这次计算的业务价值。任务框架必须记录任务名称、触发来源、开始与结束时间、停止原因、重试次数、用户可见状态和业务负责人。线程名、Perfetto 切片和任务标识也要使用同一套可检索命名。

## 注册 Android 17 触发器

下面的代码只负责注册 excessive CPU 触发器和过滤对应结果。调用方需要使用 `compileSdk 37`，并在 `SDK_INT >= 37` 的分支中调用；`minResultIntervalHours` 由应用的采集预算决定。

```kotlin
@RequiresApi(37)
fun registerExcessiveCpuProfiling(
    context: Context,
    executor: Executor,
    minResultIntervalHours: Int,
    onResult: (ProfilingResult) -> Unit,
) {
    require(minResultIntervalHours >= 0)

    val manager =
        context.getSystemService(ProfilingManager::class.java) ?: return

    manager.registerForAllProfilingResults(executor) { result ->
        if (
            result.triggerType ==
                ProfilingTrigger.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE
        ) {
            onResult(result)
        }
    }

    val trigger = ProfilingTrigger.Builder(
        ProfilingTrigger.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE,
    )
        .setRateLimitingPeriodHours(minResultIntervalHours)
        .build()

    manager.addProfilingTriggers(listOf(trigger))
}
```

监听器要先于触发器注册，并由应用级组件长期持有执行器与回调。收到结果后先判断 `errorCode`；只有 `ERROR_NONE` 且 `resultFilePath` 非空时才能读取文件。始终使用 `getResultFilePath()`，不要拼接系统目录。触发器注册和结果采集不需要普通应用声明 `MANAGE_PROFILING` 这类特权权限，公开 API 参考文档也没有这项权限要求。

## 线上证据采集与归因字段

一次事件要同时保存系统退出记录、性能分析结果和应用任务记录。`ApplicationExitInfo` 与 `ProfilingResult` 都没有公开的后台任务 ID，应用需要补足关联字段。

| 字段 | 来源 | 用途 |
|------|------|------|
| `eventId` | 应用归档层 | 关联退出记录、结果文件和任务日志 |
| `uid` / `pid` / `processName` | `ApplicationExitInfo` | 区分主进程、工具进程和 SDK 进程 |
| `exitReason` / `description` / `status` / `timestamp` | `ApplicationExitInfo` | 确认资源过量终止并保留系统描述 |
| `importance` / `processStateSummary` | `ApplicationExitInfo` | 还原进程重要性与应用写入的任务摘要 |
| `triggerType` / `tag` / `errorCode` / `errorMessage` | `ProfilingResult` | 判断结果来源和失败原因 |
| `resultFilePath` / `fileSha256` / `fileSize` | `ProfilingResult` + 归档层 | 定位、去重和校验性能分析文件 |
| `workId` / `workName` / `tags` / `jobId` | WorkManager / JobScheduler | 定位调度实体 |
| `retryCount` / `stopReason` / `chainDepth` | 任务框架 | 识别重试与任务链问题 |
| `taskStart` / `taskEnd` / `processCpuDelta` | 应用任务记录 | 判断 CPU 工作是否越过任务生命周期 |
| `standbyBucket` / `charging` / `thermalStatus` | 系统接口 | 解释调度与设备条件，不作为 CPU 终止阈值 |

`ApplicationExitInfo.getReason()` 公开到“资源使用过量”这一层，平台内部的 `SUBREASON_EXCESSIVE_CPU` 不是普通应用可读取的稳定 API。`getDescription()` 只适合保存和展示，官方文档明确说明其文本格式不保证跨版本或设备稳定，不能用字符串解析作为判定条件。

API 30 起，应用可以用 `ActivityManager.setProcessStateSummary()` 写入最多 128 字节的非敏感诊断摘要。对后台任务平台而言，可保存短任务类型、版本化状态码和重试次数。系统可能限制高频调用，因此只在活动任务发生关键状态变化时更新，不能按进度循环写入。

结果匹配也有边界：`ProfilingResult` 没有 pid，系统触发时按 uid 与包名进入性能分析服务。应用可以用触发类型、文件时间、最近的 `REASON_EXCESSIVE_RESOURCE_USAGE` 退出记录和 `processStateSummary` 做关联，但公开字段不足以保证所有多进程场景都能一一对应。归档层要保留“可能关联”，不要生成虚假的精确关系。

## 治理策略：约束、合并、退避和熔断

后台 CPU 治理要让任务的用户可见度、调度方式和资源预算一致：

- 约束：充电、低电量、空闲和网络约束只用于业务允许等待的任务。不能为了省电给用户正在等待的操作增加不必要约束。
- 唯一任务：同类同步或上传使用 `enqueueUniqueWork()` / `enqueueUniquePeriodicWork()`，业务键必须稳定。
- 退避分类：可恢复的服务端或网络错误使用退避；鉴权失效、输入损坏和永久业务错误直接失败，等待外部状态变化后再入队。
- 取消传播：`isStopped`、协程取消和底层库取消信号要传到压缩、媒体、数据库和原生代码；Worker 返回前确认自建线程已经结束。
- 分片与检查点：大任务按可重入边界分片，每片完成后持久化检查点，并再次检查停止信号和约束。
- 并发预算：CPU 密集任务使用有界并发，线程数来自负载验证，不能与 `Dispatchers.IO` 的阻塞任务混用。
- 故障隔离：任务连续失败或超过项目 CPU 预算时暂停该任务类型，通过配置关闭问题路径；预算值必须来自业务测试。
- 采集限额：使用 `setRateLimitingPeriodHours()` 设置触发器级冷却期，上传端还要按应用版本和设备控制文件数量与总大小。

下面的 WorkManager 片段展示一个可延后日志上传任务，其中包含唯一任务、约束和指数退避三项配置。

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .setRequiresBatteryNotLow(true)
    .build()

val request = OneTimeWorkRequestBuilder<LogUploadWorker>()
    .setConstraints(constraints)
    .setBackoffCriteria(
        BackoffPolicy.EXPONENTIAL,
        WorkRequest.MIN_BACKOFF_MILLIS,
        TimeUnit.MILLISECONDS,
    )
    .addTag("log_upload")
    .build()

WorkManager.getInstance(context).enqueueUniqueWork(
    "log_upload_${accountId}",
    ExistingWorkPolicy.KEEP,
    request,
)
```

`KEEP` 在已有未完成的同名工作时不会再建立一条工作链，适合按账号去重。需要新输入替换旧任务时，应在选择 `REPLACE` 前确认旧任务可以安全取消。`MIN_BACKOFF_MILLIS` 使用 WorkManager 公开的最小退避常量，避免示例凭空设置时间。约束与退避都不承诺立即执行，Worker 仍要实现幂等、停止检查和断点恢复。

## Android 11-17 的版本化降级路径

| 系统版本 | 可用能力 | 后台 CPU 异常处理方式 |
|----------|----------|----------------------|
| Android 10 及更早 | 应用任务日志、实验室 Perfetto、bugreport | 记录任务与线程生命周期，线上缺少标准退出历史 API |
| Android 11～14 | `ApplicationExitInfo`、`setProcessStateSummary()` | 下次启动读取退出原因、时间戳、进程名和应用摘要；CPU 热点仍依赖自建记录或实验室跟踪 |
| Android 15 | `ProfilingManager.requestProfiling()` | 应用主动请求系统跟踪、堆分析或栈采样；请求受频率限制且不保证执行 |
| Android 16 | `ProfilingTrigger`、`addProfilingTriggers()` | 注册 API 36 已公开的系统触发器，并通过全局监听器接收结果 |
| Android 17 | `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 把 excessive CPU 终止接入系统触发式性能分析，结合退出记录和任务摘要定位 |

API 37 是触发器常量的可用版本，不等于该终止机制只影响 `targetSdkVersion >= 37` 的应用。`android-17.0.0_r1` 的 AMS 检测、终止和发送触发器代码中没有这一 target SDK 条件。接入代码只需要做运行版本保护；产品仍应在 Android 17 上测试不同 target SDK 的应用行为。

## 与 26.12 线上诊断能力的关系

26.12 介绍 `ProfilingManager` 的通用 API、文件取回与隐私处理。诊断记录还要增加 `backgroundTask` 子对象，至少包含 `workId`、`jobId`、`workName`、`tags`、`retryCount`、`stopReason`、任务开始时间和业务负责人。性能分析文件可能包含敏感的执行路径信息，上传、保留和访问控制应沿用 26.12 的安全策略。

## 与 5.10 系统调度机制的关系

5.10 解释约束、待机分桶、配额、等待原因和 Expedited Job。排查顺序如下：

1. 任务没有启动：查 JobDebugInfo、等待原因、约束和配额。
2. 任务启动后被调度器停止：查 WorkInfo 或 `JobParameters.getStopReason()`，确认 Worker 是否及时停止底层工作。
3. 进程死亡：读取 `ApplicationExitInfo`。原因是 `REASON_EXCESSIVE_RESOURCE_USAGE` 时，再查 Android 17 触发器结果和 Perfetto 文件。
4. 任务已经结束，进程降为缓存后仍有 CPU：查未取消协程、独立线程、JNI、子进程与 Binder 循环。

这个顺序把调度等待、任务停止和进程终止分开，避免用同一套“后台限制”解释所有现象。

## 待验证阈值与厂商差异

源码已经确认 AOSP 默认阈值、目标进程状态、终止原因与性能分析服务调用，仍有以下设备侧变量：

- `ACTIVITY_MANAGER_CONSTANTS` 的实际值以及厂商是否修改默认配置；
- 厂商是否改变进程状态、phantom process 或冻结失败处理；
- 系统后台跟踪在事件发生时是否正在运行；
- 系统级与应用级频率限制是否允许保存结果；
- `ProfilingResult` 文件在不同构建上的实际覆盖时段与裁剪内容；
- WorkManager 在宿主进程被直接终止前能否持久化有用的停止信息。

验证时不要让生产 Worker 故意制造无限循环。使用可恢复的测试应用，在隔离设备上注册触发器，把进程置于可确认的 Home 或缓存状态，再运行有明确停止条件的 CPU 负载。同步采集 `dumpsys activity settings`、`dumpsys activity processes`、logcat、`ApplicationExitInfo` 和 `ProfilingResult`。测试结束后核对进程状态、实际配置、退出原因和文件内容，单台设备的结果只能说明该设备构建。

## 小结

Android 17 为既有的 excessive CPU 终止路径增加了公开取证触发器。AOSP r1 的主要判定对象是 Home 与缓存进程，依据进程 CPU 时间增量和可配置检查窗口终止进程；它不等同于 JobScheduler 配额，也不会自动指向某个 Worker。

应用侧要完成两件事：注册 API 37 触发器，并把结果文件与 `ApplicationExitInfo`、任务生命周期记录和 `processStateSummary` 关联；同时修复越过任务生命周期的线程、协程、原生工作与子进程。唯一任务、分类退避、取消传播、有界并发和可恢复分片，才是降低后台 CPU 风险的主要手段。

## 延伸阅读

- [Android 17 Features and APIs](https://developer.android.com/about/versions/17/features)
- [`ProfilingTrigger` API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [`ProfilingManager` API reference](https://developer.android.com/reference/android/os/ProfilingManager)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [`ApplicationExitInfo` API reference](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ActivityManager.setProcessStateSummary()`](https://developer.android.com/reference/android/app/ActivityManager#setProcessStateSummary(byte%5B%5D))
- [Android 17 `ActivityManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java#16057)
- [Android 17 `ActivityManagerConstants.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java#213)
- [Android 17 `CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java#2469)
- [Android 17 Profiling module](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/)
