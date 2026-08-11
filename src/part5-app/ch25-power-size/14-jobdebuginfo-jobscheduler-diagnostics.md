---

title: "JobScheduler 调试：Pending Reasons 与 JobDebugInfo"
chapter: "25.14"
status: finalized
drafted_date: "2026-05-22"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "Android Developers JobScheduler reference / Android 17 features / WorkManager debug docs；AOSP android-16.0.0_r1 JobSchedulerService + JobStatus"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/features#job-debugging"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobScheduler"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/data-transfer-options"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/testing/persistent/debug"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/JobStatus.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/job/PendingJobReasonsInfo.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [jobscheduler, workmanager, background-work, power, diagnostics]
related_chapters: ["5.10", "14.12", "25.4", "25.13", "26.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "官方文档/每日信息/章节深挖"
task2a_result: draft-ready-for-review
last_task2a_at: "2026-05-22T05:19:00+08:00"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-05
task6_result: pass-light-edit
last_task6_at: "2026-06-05T13:11:00+08:00"
last_task6_audit: "2026-07-10"
task9_result: auto-fixed
task2b_state: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-05"
last_task9_at: "2026-06-05T11:24:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-05-11-deep-review.md"
task9_review_notes: "2026-06-05 Task9 auto-fix：移除 JobScheduler pending reason 示例中错误的 PACKAGE_USAGE_STATS 权限注解；官方 API reference 与 AOSP android-16.0.0_r1 均未要求该权限。回到 Task6 复审。"
last_task9_autofix_at: "2026-06-05"
last_task6_review_log: "logs/review/2026-06-05-13-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-05
---

# 25.14 JobScheduler 调试：Pending Reasons 与 JobDebugInfo

后台任务排障过去常从“Worker 为什么没有执行”开始，证据主要来自 WorkManager 日志、`dumpsys jobscheduler` 和业务状态机。Android 14—17 逐步把“为什么仍在等待”开放为结构化 API。同样是任务延迟，原因可能是显式约束不满足、运行额度用完、设备处于 Doze、应用被限制后台运行，也可能是 JobScheduler 正在等待更合适的执行窗口。

这里处理 JobScheduler 待执行原因的使用方式，不重复展开 JobScheduler 调度模型。Controller、JobStore、JobServiceContext 和配额机制详见 5.10；WorkManager 建模详见 25.4；Foreground Service 与 Android 16 Job 配额变化详见 25.13；线上证据归档详见 26.12。

Android 17 功能页把这一组能力统称为 “JobDebugInfo APIs”，SDK 中并没有名为 `JobDebugInfo` 的公开类。应用调用的入口仍在 `JobScheduler`，历史记录元素类型是 `PendingJobReasonsInfo`。

## 待执行原因解决的是等待归因

JobScheduler 的待执行原因不是任务执行日志。它回答的是：一个已经提交给系统的 Job，当前或历史上为什么还没有进入执行状态。它与 `JobParameters.getStopReason()` 互补：待执行原因解释运行前的等待，停止原因解释执行为何结束。

Android Developers 的 `JobScheduler` reference 给出四个入口：

| API | 起始版本 | 返回内容 | 适合回答的问题 |
| --- | ---: | --- | --- |
| `getPendingJobReason(jobId)` | API 34 | 单个待执行原因 | 快速判断一个 Job 是否存在、是否正在执行、是否有一个主要等待原因 |
| `getPendingJobReasons(jobId)` | API 36 | 当前可能导致等待的原因数组 | 当前有哪些约束或系统限制同时阻止执行 |
| `getPendingJobReasonsHistory(jobId)` | API 36 | 若干条带时间戳的 `PendingJobReasonsInfo` | 等待原因如何随网络、电量、Doze、配额等状态变化 |
| `getPendingJobReasonStats(jobId)` | API 37 | `Map<Integer, Duration>`，原因到累计等待时长 | 哪类原因占用了最多等待时间，适合汇总和趋势观察 |

`getPendingJobReason()` 只能返回一个原因。Job 同时等待充电、未计费网络和运行额度时，这个 API 会丢失其他并发原因；官方 API 参考也建议用 `getPendingJobReasons()` 获取所有可能原因。API 36 的 `getPendingJobReasonsHistory()` 提供有限长度的历史记录，时间戳只在约束变化时产生，没有固定采样间隔，设备重启后不会保留。API 37 的 `getPendingJobReasonStats()` 聚合每种原因的累计等待时长。多个原因可以同时计时，所以各项时长之和经常大于 Job 的实际等待时间；设备重启、Job 成功完成或取消都会清除统计。

这组查询不需要额外权限，但调用范围受调用方 UID 和当前 `JobScheduler` 命名空间限制。用 `forNamespace()` 调度的 Job，查询时也要使用同一命名空间实例。历史与统计查询要求 Job 仍存在；Job 在多次查询之间完成或被取消时会抛出 `IllegalArgumentException`，几次调用也不构成同一时刻的原子快照。

下面的代码用于按需采集一次待执行状态，并处理 Job 在查询期间结束所产生的竞态。示例假定项目以 API 37 编译；低版本调用由系统版本分支保护。

```kotlin
fun JobScheduler.capturePendingState(
    jobId: Int,
    taskType: String,
): JobPendingSnapshot? {
    if (Build.VERSION.SDK_INT < 34) return null

    return try {
        val currentReasons = if (Build.VERSION.SDK_INT >= 36) {
            getPendingJobReasons(jobId).toList()
        } else {
            listOf(getPendingJobReason(jobId))
        }

        val history = if (Build.VERSION.SDK_INT >= 36) {
            getPendingJobReasonsHistory(jobId).map { item ->
                PendingReasonHistory(
                    timestampMillis = item.timestampMillis,
                    reasons = item.pendingJobReasons.toList(),
                )
            }
        } else {
            emptyList()
        }

        val statsMillis = if (Build.VERSION.SDK_INT >= 37) {
            getPendingJobReasonStats(jobId).mapValues { (_, duration) ->
                duration.toMillis()
            }
        } else {
            emptyMap()
        }

        JobPendingSnapshot(
            capturedAtMillis = System.currentTimeMillis(),
            taskType = taskType,
            currentReasons = currentReasons,
            history = history,
            statsMillis = statsMillis,
        )
    } catch (_: IllegalArgumentException) {
        // Job 已完成或取消，调用方改查自己的完成记录。
        null
    }
}
```

这段采集适合用户反馈、内部测试或采样后的量产诊断，不应在主线程轮询。`taskType` 必须来自固定枚举；若业务仍需关联 Job ID，应在本地映射或稳定哈希后再上报。历史记录要限制条数，原因常量要转成低基数字段。任务参数、URL、文件名、网络 SSID 和业务标识不应进入日志。

## 原因常量对应的排障含义

`PENDING_JOB_REASON_*` 可以分成五类：显式约束、系统隐式状态、应用状态、用户动作和调度器策略。Android 17 的 `JobStatus.constraintsToPendingJobReasons()` 把未满足的内部约束位转换成公开原因。例如，网络约束对应 `PENDING_JOB_REASON_CONSTRAINT_CONNECTIVITY`，运行额度约束对应 `PENDING_JOB_REASON_QUOTA`；后台限制与设备状态分别对应 `PENDING_JOB_REASON_BACKGROUND_RESTRICTION` 和 `PENDING_JOB_REASON_DEVICE_STATE`。

| 原因 | 常见触发 | 排障动作 |
| --- | --- | --- |
| `CONSTRAINT_CONNECTIVITY` | `JobInfo` 要求网络，但当前网络不满足请求 | 对照网络类型、是否按流量计费和任务是否能降低网络要求；不要只看业务 HTTP 失败 |
| `CONSTRAINT_CHARGING` / `CONSTRAINT_BATTERY_NOT_LOW` | 显式要求充电或电量不低 | 检查约束是否过严；低优先级同步可保留，高价值用户任务应评估 UIDT 或前台入口 |
| `CONSTRAINT_DEVICE_IDLE` | 显式要求设备空闲 | 只适合维护类任务；普通上传若加 idle，线上会出现长时间等待 |
| `CONSTRAINT_MINIMUM_LATENCY` / `CONSTRAINT_DEADLINE` | 最小延迟未到，或 deadline 相关约束未满足 | 检查业务是否误把延迟窗口当成精确时间；精确提醒回到 AlarmManager |
| `CONSTRAINT_PREFETCH` / `JOB_SCHEDULER_OPTIMIZATION` | 预取任务或系统认为可以等待更合适窗口 | 检查 `setPrefetch()` 使用场景，预取不应承载用户当前等待的操作 |
| `QUOTA` | 应用待机分组或系统运行额度限制 | 对照 25.13 的 Android 16 规则，检查密集重试、FGS 并发 Job 和加急 Job 滥用 |
| `DEVICE_STATE` | Doze、Battery Saver、热状态、内存压力等设备状态 | 结合 `dumpsys deviceidle`、热状态、低内存和系统日志确认；不要归因到单个 Worker |
| `BACKGROUND_RESTRICTION` | 应用被用户或系统限制后台运行 | 记录应用限制状态，给用户可理解的恢复入口，避免后台密集重试 |
| `APP_STANDBY` | 当前应用待机分组阻止运行 | 结合 `UsageStatsManager.getAppStandbyBucket()` 和任务价值调整频率 |
| `APP` | JobService 组件不可用、应用状态阻止运行等 | 检查清单、组件启用状态、包更新和多进程服务状态 |
| `USER` | 用户强行停止（force stop）或 adb 命令等动作导致延后 | 不要自动恢复；等待用户重新打开或明确触发 |
| `EXECUTING` / `INVALID_JOB_ID` / `UNDEFINED` | 正在运行、Job 不存在、系统未给出明确原因 | 分别查看运行中记录、调度表，以及历史 API 与 `dumpsys` |

Android 17 的 `JobSchedulerService.getPendingJobReasonsLocked()` 还规定了查询顺序：Job 不存在时返回 `INVALID_JOB_ID`，正在运行时返回 `EXECUTING`；Job 未就绪或受到系统 restriction 限制时，读取 `JobStatus` 转换出的原因；Job 已就绪但用户未启动、应用正在备份、待执行队列拥塞或组件不可用时，再返回 `USER`、`APP`、`DEVICE_STATE` 等原因。

同一个原因不能直接对应一项修复。`DEVICE_STATE` 可能来自 Doze、省电模式、热限制、内存压力，也可能表示 Job 已经就绪但并发槽位不足；`APP_STANDBY` 只说明当前待机分组阻止执行。待执行原因给出排查方向，还要结合 `dumpsys jobscheduler`、WorkManager 状态、业务阶段日志和设备状态判断。

## WorkManager、dumpsys 与 API 的分工

WorkManager、`dumpsys jobscheduler` 和待执行原因 API 各自回答的问题不同。把三者混成一个排障入口，容易得出错误结论。

| 入口 | 观察范围 | 优点 | 边界 |
| --- | --- | --- | --- |
| WorkManager 详细日志 | App 内 WorkRequest、Worker、重试、约束跟踪器 | 能看到唯一工作、标签、退避和 Worker 状态 | 看不到 JobScheduler 的全部隐式限制，线上开详细日志成本高 |
| `REQUEST_DIAGNOSTICS` | WorkManager 2.4.0+ 调试构建中的已完成、运行中、已调度 Work | 适合本地和内部测试快速导出 Work 表 | 通过 Logcat 输出，不适合量产常开 |
| `adb shell dumpsys jobscheduler` | 系统 Job 现场，包括必要、已满足、未满足约束，历史和应用待机分组 | 信息最完整，能看到 system_server 的当前判断 | 需要 adb，属于本地现场工具 |
| JobScheduler 待执行原因 API | 调用 App 自己的 Job，输出结构化当前原因、历史和统计 | 适合内部测试和灰度归因 | 只覆盖该 App 在当前命名空间可查询的 Job；API 36/37 才有完整能力 |
| Background Task Inspector | IDE 调试视图 | 适合开发阶段理解 WorkManager 任务 | 不适合线上和自动化门禁 |

本地排障建议从 `dumpsys jobscheduler` 开始。官方 WorkManager 调试文档给出的输出里，Job 会列出 `Required constraints`、`Satisfied constraints`、`Unsatisfied constraints`、`Tracking`、`Standby bucket`、`Run time` 和 `Ready`。这些字段能还原 system_server 当时如何判断一个 Job。WorkManager 任务在 API 23+ 通常会表现为 `androidx.work.impl.background.systemjob.SystemJobService`，可用包名和 service 名过滤。

JobScheduler 的查询方法接收平台 Job ID，不接收 WorkRequest UUID。WorkManager 对 SystemJobService 的 Job ID 分配属于其内部实现，应用不应依赖这层映射；WorkManager 任务优先使用 WorkManager 状态、停止原因和诊断广播，`dumpsys jobscheduler` 用于交叉查看系统现场。

下面的命令用于查看系统现场、触发 Job 路径并改变应用待机分组。包名和 Job ID 都要替换为测试应用的值。

```bash
# 查看当前包名关联的 JobScheduler 现场
adb shell dumpsys jobscheduler | sed -n '/com.example.app/,/Job history/p'

# 强制运行指定 Job，验证 JobService / Worker 路径是否可执行
adb shell cmd jobscheduler run -f com.example.app 42

# 模拟 Job 超时，验证 onStopJob()、WorkInfo 停止原因和断点续传
adb shell cmd jobscheduler timeout com.example.app 42

# 切换应用待机分组，观察待执行原因是否转为配额或待机限制
adb shell am set-standby-bucket com.example.app restricted
adb shell am set-standby-bucket com.example.app active

# 触发 WorkManager 2.4.0+ 调试诊断输出
adb shell am broadcast \
  -a "androidx.work.diagnostics.REQUEST_DIAGNOSTICS" \
  -p "com.example.app"

# 测试结束后恢复应用待机分组
adb shell am set-standby-bucket com.example.app active
```

`jobscheduler run -f` 会忽略部分技术约束，只能证明执行代码可以被拉起，不能证明自然调度条件已经满足。`timeout` 只作用于正在执行的 Job。命令验证只覆盖本地现场；线上应保留任务类型、API 级别、应用待机分组、待执行原因集合、历史记录条数、累计时间较长的少量原因、停止原因、任务阶段和重试次数。

## Android 16/17 版本边界与降级路径

版本边界要按能力拆开，不要把 Android 17 的 JobDebugInfo 统一写成所有 Android 16+ 设备可用。

| 版本 | 可用能力 | 降级方式 |
| --- | --- | --- |
| API 33 及以下 | 无公开待执行原因 API；依赖 WorkManager 状态、业务日志、`dumpsys` 本地取证 | 上报任务阶段、约束配置、重试次数、网络和电量粗粒度状态 |
| API 34-35 | `getPendingJobReason()` 返回单个原因 | 只做快速提示，不用于统计并发约束；本地继续用 `dumpsys` |
| API 36 | `getPendingJobReasons()`、`getPendingJobReasonsHistory()` | 按需采集当前原因和有限历史，避免高频查询 |
| API 37 | `getPendingJobReasonStats()` | 聚合原因到累计时长，适合灰度报表；保留 API 36 历史作为抽样明细 |

在 Android 17 / API 37 最终 SDK 中，这四个方法已经按表中的 API 级别公开。以 API 37 编译时，可以直接用 `Build.VERSION.SDK_INT` 保护调用；不需要权限探测、SDK Extension 判断或反射。若项目的 `compileSdk` 较低，先升级编译 SDK，再接入对应方法，避免维护反射分支。

旧版本应保留四类应用阶段日志：入队、约束配置、开始执行、停止或完成。WorkManager 可读取 `WorkInfo` 状态和停止原因；直接使用 JobScheduler 的任务记录 `onStartJob()`、`onStopJob()`、`jobFinished()` 和受控的 Job ID 映射。服务端看到任务长时间未完成时，依次区分没有入队、已入队但未启动、启动后停止和业务阶段失败。

## 接入后台功耗治理

待执行原因适合放在后台任务治理流程里，不只用于单次崩溃排障。一个任务长时间等待未必是故障；低优先级日志上传等待未计费网络或充电，说明约束正在生效。需要处理的异常包括约束配置错误、系统配额被消耗过快和业务重试放大功耗。

| 现象 | 待执行原因信号 | 常见原因 | 治理动作 |
| --- | --- | --- | --- |
| 低优先级同步长期不执行 | `CONSTRAINT_CHARGING`、`CONSTRAINT_CONNECTIVITY` 长时间占比高 | 约束过严，用户很少满足充电 + 未计费网络 | 放宽约束或降低任务频率；把必要数据改为前台触发 |
| 用户触发上传延迟 | `QUOTA`、`APP_STANDBY`、`BACKGROUND_RESTRICTION` | 普通 Job 承载用户等待操作，或 App 已被限制后台 | Android 14+ 评估 UIDT；低版本给用户可见恢复入口 |
| FGS 与 WorkManager 并发后任务仍被延迟 | `QUOTA` 占比上升 | Android 16 起 FGS 并发 Job 仍受运行时长配额约束 | 参照 25.13 拆分长任务，不再用 FGS 规避 Job 配额 |
| 后台预取持续等待 | `CONSTRAINT_PREFETCH`、`JOB_SCHEDULER_OPTIMIZATION` | 预取任务被系统延后到更合适窗口 | 降低告警级别；只观察完成率和过期率 |
| 任务反复入队但不完成 | 历史中的原因切换频繁，停止原因也异常 | 网络抖动、重试策略过密、任务粒度过大 | 指数退避、分片、唯一任务去重，限制并发 |

发布门禁可以加入三条规则：同一任务类型在内部测试中以 `QUOTA` 或 `BACKGROUND_RESTRICTION` 为主要等待原因时，审查频率和重试策略；用户触发任务出现 `APP_STANDBY` 或 `QUOTA` 长时间等待时，评估 UIDT、Foreground Service 或前台恢复入口；低优先级任务因显式约束等待时，不按故障处理，只跟踪是否过期和是否影响用户路径。

## 线上可观测性边界

待执行原因适合做低基数指标，不适合上传完整现场。原因常量本身不含业务数据，但它容易和 Job ID、命名空间、网络状态、任务参数一起进入日志。设计字段时要同时满足定位和隐私要求。

建议保留这些字段：

- `task_type`：内部枚举，例如 `log_upload`、`receipt_upload`、`feed_prefetch`。
- `job_id_hash`：稳定哈希，不上传原始 Job ID 与业务 ID。
- `api_level`、`target_sdk`、`app_version`、`rom_bucket`：用于版本分组。
- `current_reasons`：`PENDING_JOB_REASON_*` 枚举集合。
- `stats_top_reasons`：Android 17+ 只保留少量累计时长最高的原因和时长桶。
- `history_count`：历史记录条数和最近一次时间戳桶，不上传完整时间线。
- `work_state`、`work_stop_reason`、`job_stop_reason`：与运行后停止原因放在同一条事件里。
- `retry_count`、`attempt_bucket`、`duration_bucket`：避免原始时长和高基数字段。

不建议上传这些字段：原始 Job ID、WorkRequest UUID、任务数据、URL、文件名、用户标识、网络 SSID、精确地理位置、完整 `dumpsys` 输出和完整历史明细。`dumpsys jobscheduler` 可能包含包名、UID、extras、网络请求和系统状态，只适合本地诊断或脱敏后的内部证据包。

采样频率也要受控。Android 17 的 `JobSchedulerService` 为当前原因查询设置了独立缓存，源码注释明确考虑了应用频繁查询对调度器的影响。App 不应在主线程轮询；可以在任务超过产品定义的等待阈值、内部手动诊断、灰度异常窗口或用户反馈时采集。

## 与 Android 17 Excessive CPU Kill 的衔接

Android 17 的版本化诊断能力把两条线接到一起：JobDebugInfo 解释任务为什么没开始，ProfilingTrigger / Excessive CPU 解释任务运行后是否耗尽 CPU 或被系统干预。二者都不应单独下结论。

后台任务问题可以按三个阶段检查：

1. 调度前：用待执行原因判断是否被约束、配额、设备状态或用户动作延后。
2. 运行中：用 WorkManager / JobScheduler 停止原因、运行时长、CPU 时间和网络字节数判断负载。
3. 系统干预后：用 26.12 的 ProfilingTrigger、ApplicationExitInfo 和版本化证据包确认是否有 excessive resource usage、ANR、OOM 或系统 kill。

如果某类任务同时出现 `QUOTA` 长时间等待、启动后 CPU 时间高、`onStopJob()` 频繁返回系统停止原因，应优先调整任务粒度和重试策略：分片、限频、断点续传、去重、延后低价值预取。只有用户明确等待的长传输，才考虑 UIDT 或 Foreground Service，并按 25.13 的配额边界设计恢复路径。

## JobDebugInfo 指标进入发布门禁

发布门禁用于发现新版本是否增加后台任务负载，不能证明单台设备上的任务会准时执行。单机调试数据不能当作线上 SLA，内部测试和灰度指标也要按设备状态与版本切分。

推荐门禁项如下：

| 门禁项 | 采集方式 | 触发后动作 |
| --- | --- | --- |
| 待执行原因分布 | API 37 用累计统计，API 36 用周期历史抽样 | 主要原因从显式约束变成 `QUOTA` / `BACKGROUND_RESTRICTION` 时，审查重试和频率 |
| 任务完成率 | WorkManager / 业务状态机 | 完成率下降且待执行原因指向系统限制时，检查任务是否误用普通后台 Job |
| 重试放大 | 重试次数、退避、入队次数 | 同一任务短时间重复入队，改唯一任务、退避和合并策略 |
| 用户任务等待 | 用户触发任务的等待时长桶 | 超过产品阈值时，改 UIDT、前台入口或可恢复通知 |
| 低优先级过期 | 任务业务截止时间与完成时间 | 约束等待导致过期时，调整约束或降低任务价值假设 |

这些门禁只做阻断前的证据提示。最终是否修改约束、迁移 UIDT、降低频率或拆分任务，还要结合业务价值、用户可见度和系统版本占比判断。

## 小结

JobScheduler 待执行原因让应用可以按公开原因检查约束、配额、设备状态和应用状态。Android 16 提供当前原因和历史变化，Android 17 增加按原因聚合的累计时长。工程上应把它用于内部测试、灰度和本地排障，并与 WorkManager 状态、`dumpsys jobscheduler`、停止原因和任务阶段日志一起分析。

不要把 JobDebugInfo 当成保活或准点执行工具。它给的是等待归因，不改变 JobScheduler 的调度策略。任务能否省电、能否按用户期望完成，仍取决于任务分类、约束设计、重试策略、分片恢复和版本降级路径。

## 参考资料

- [Android 17 features: JobDebugInfo APIs](https://developer.android.com/about/versions/17/features#job-debugging)
- [JobScheduler reference](https://developer.android.com/reference/android/app/job/JobScheduler)
- [PendingJobReasonsInfo reference](https://developer.android.com/reference/android/app/job/PendingJobReasonsInfo)
- [Debug WorkManager](https://developer.android.com/develop/background-work/background-tasks/testing/persistent/debug)
- [Data transfer background task options](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [`JobScheduler.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java)
- [`PendingJobReasonsInfo.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/job/PendingJobReasonsInfo.java)
- [`JobSchedulerService.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java)
- [`JobStatus.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/controllers/JobStatus.java)
