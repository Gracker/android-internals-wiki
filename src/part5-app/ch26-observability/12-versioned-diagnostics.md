---
title: "Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger"
chapter: "26.12"
section: "26.12"
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [observability, online-diagnostics, application-exit-info, profiling-manager]
confidence: "medium"
sources:
- type: aosp
  path: packages/modules/Profiling/framework/java/android/os/ProfilingResult.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingResult.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingResult
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/will-my-profile-always-be-collected
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/reference/android/os/Build.VERSION
- type: official
  path: https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL
- type: aosp
  path: packages/modules/Profiling
last_verified: "2026-06-28"
last_verified_against: "refs/tags/android-17.0.0_r1 (frameworks/base, packages/modules/Profiling, frameworks/proto_logging均已确认存在)"
drafted_date: "2026-05-17"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-06-28"
reviewed_by: "openclaw-task6"
related_chapters: ["26.2", "26.5", "14.11", "13.2", "15.5", "20.3", "19.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材/官方文档/章节深挖"
gap_score: "18"
task6_state: reviewed
last_task6_at: "2026-06-28T22:10:00+08:00"
task9_state: reviewed
task6_result: "pass-light-edit"
task2a_result: "draft-ready-for-review"
last_task2a_at: "2026-05-17T06:04:00+08:00"
task9_result: pass-tech-review
task9_reviewed_date: "2026-06-28"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-28T22:28:19+08:00"
last_task9_autofix_at: "2026-06-28"
task2b_result: fixed-lite
task2b_state: fixed
last_task2b_lite_at: "2026-06-28"
last_task2b_at: "2026-06-24T14:53:26+08:00"
repaired_date: "2026-06-24"
repaired_by: "openclaw-task2b"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-28
last_task9_audit: "2026-06-28"
last_task9_review_log: "logs/deep-review/2026-06-28-22-deep-review.md"
---

# 26.12 Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger

同一个故障发生在 Android 10 和 Android 17 上，可取得的系统证据并不相同。诊断系统需要先判断设备版本和能力，再决定采集入口。版本号只能说明 API 的上限，不能保证系统一定生成了某份附件。

平台源码锚点采用 `android-17.0.0_r1`。涉及旧版本时保留其公开 API 边界；涉及 Android 17 新行为时，以正式开发者文档和该标签下的源码为准。

## 三条诊断路径分别回答什么

Android 10 到 Android 17 的公开诊断能力可以分成三条路径。

| 路径 | 要回答的问题 | 起始版本 | 公开入口 | 典型结果 |
|---|---|---:|---|---|
| 退出追溯 | 进程为何退出 | Android 11 / API 30 | `ActivityManager#getHistoricalProcessExitReasons()` | reason、status、退出时间、最近一次 PSS/RSS、可选 trace |
| 应用请求采集 | App 已知问题正在复现，能否请求一次 profile | Android 15 / API 35 | `ProfilingManager#requestProfiling()`，或 AndroidX Profiling | system trace、Java heap dump、heap profile、stack sampling |
| 系统事件触发采集 | 系统识别到特定事件时，能否保存事件前后的 profile | Android 16 / API 36 | `addProfilingTriggers()`、全局结果监听器 | 后台 trace 快照、Java heap dump、stack sample 等 |

退出追溯记录的是进程终点。它适合确认 ANR、native crash、用户操作或系统资源处置，但通常缺少故障发生前的完整运行时序。应用请求采集针对可控复现窗口。系统事件触发采集依赖系统后台采样和限流，适合捕获难以预测的事件。

一次问题可以关联多条路径。例如，ANR 发生时系统可能生成触发式 system trace；进程随后被杀，下次启动又能读到 `ApplicationExitInfo`。两者应作为独立来源归档，再通过时间、进程和事件语义建立关联，不能因为时间相近就覆盖其中一份。

## 版本能力表

| 系统版本 | 可用的主要能力 | 仍需保留的降级手段 |
|---|---|---|
| Android 10 / API 29 | App 自有日志、Crash SDK；开发或用户协助场景下使用 Perfetto、bug report | 业务状态快照、请求 ID、会话 ID、复现步骤 |
| Android 11 / API 30 | 增加 `ApplicationExitInfo`；ANR 记录可能带 trace | Crash SDK、卡顿监控、人工 Perfetto |
| Android 12-14 / API 31-34 | native crash 记录可带 tombstone protobuf；API 33/34 又增加部分 reason | 同上，并持续处理 trace 缺失 |
| Android 15 / API 35 | 增加 `ProfilingManager#requestProfiling()` | 低版本采集方案仍需保留 |
| Android 16 / API 36 | 增加 `APP_FULLY_DRAWN`、`ANR` 两类系统 trigger | 系统后台 trace 没运行或限流时仍会没有产物 |
| Android 16 minor release / API 36.1 | 增加主动请求后台 trace 快照及三类用户终止 trigger | 运行时按完整 SDK 版本检查 |
| Android 17 / API 37 | 增加 cold start、OOM、anomaly、CPU kill、app compat trigger；部分设备启用 MemoryLimiter | 设备覆盖、系统限流和无产物路径都要监控 |

API 36.1 是 Android 16 的 minor SDK release。它不是 `SdkExtensions.getExtensionVersion()` 所表示的 Mainline SDK Extension。调用 36.1 新 API 前，应检查 `Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1`；只看 `SDK_INT >= 36` 无法区分 36.0 和 36.1。Android 17 的 `SDK_INT_FULL` 高于该值，因此也满足条件。

## Android 10-14：退出记录之前和之后

Android 10 没有 `ApplicationExitInfo`。线上进程退出只能依赖 App 在进程存活时写下的证据、Crash SDK，以及用户允许或测试设备上的 bug report、Perfetto。低内存杀进程通常没有 Java 异常回调，所以业务阶段、前后台状态、关键资源计数应在运行时定期写入小型状态记录，不能等到退出时再补。

Android 11 引入 `ActivityManager#getHistoricalProcessExitReasons(packageName, pid, maxNum)`。系统按时间从近到远返回历史退出记录。它是系统保存的事后记录，不等同于 Crash SDK 的崩溃样本，也不承诺每次退出都有 trace。

Android 12 / API 31 扩展了 native crash 附件：`REASON_CRASH_NATIVE` 的 `getTraceInputStream()` 可以返回 tombstone protobuf。Android 13 / API 33 增加 `REASON_FREEZER`；Android 14 / API 34 增加 `REASON_PACKAGE_STATE_CHANGE` 和 `REASON_PACKAGE_UPDATED`。读取记录时按运行系统的 API 能力解释 reason，不要让旧客户端引用尚未存在的常量。

## ApplicationExitInfo 能证明什么

`ApplicationExitInfo` 的稳定核心是系统记录的退出事实：

- `getTimestamp()` 是进程死亡的 wall-clock 时间，单位为毫秒。
- `getPid()`、`getProcessName()`、`getPackageUid()`、`getRealUid()` 用来识别进程身份；隔离进程的 package UID 和 real UID 可能不同。
- `getReason()` 给出公开的退出原因大类，`getStatus()` 保存退出码或 signal 等补充值。
- `getPss()` 和 `getRss()` 是系统最近一次采样值，单位为 kB。它们不是死亡瞬间的内存快照；系统来不及采样时可能为 0。
- `getProcessStateSummary()` 是 App 先前通过 `ActivityManager#setProcessStateSummary()` 写入的有限状态数据，可能为 `null`。
- `getDescription()` 面向人工阅读，通常不应作为稳定协议解析。Android 17 MemoryLimiter 的官方标记是一个有文档保证的例外，后文单独说明。

公开 SDK 没有 `getSubReason()`。AOSP 内部确有更细的 sub-reason，statsd 也可使用内部字段，但普通应用不能把它写进依赖公开 API 的数据模型。旧资料中出现的 `REASON_APPLICATION_SPECIFIC_ERROR` 也不在 `android-17.0.0_r1` 的公开 reason 列表中，因此不在这里使用。

### 安全读取退出记录

下面的示例只读取公开字段，并把最大记录数交给产品配置。代码不会假设 PSS/RSS 非零，也不会把 description 当成通用枚举。

```kotlin
data class ExitEvidence(
    val packageUid: Int,
    val realUid: Int,
    val pid: Int,
    val processName: String,
    val timestampMs: Long,
    val reason: Int,
    val status: Int,
    val pssKb: Long?,
    val rssKb: Long?,
    val description: String?,
)

fun readRecentExits(
    context: Context,
    maxRecords: Int,
): List<ExitEvidence> {
    require(maxRecords > 0)
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return emptyList()

    val activityManager = context.getSystemService(ActivityManager::class.java)
    return activityManager.getHistoricalProcessExitReasons(
        context.packageName,
        0,
        maxRecords,
    ).map { info ->
        ExitEvidence(
            packageUid = info.packageUid,
            realUid = info.realUid,
            pid = info.pid,
            processName = info.processName,
            timestampMs = info.timestamp,
            reason = info.reason,
            status = info.status,
            pssKb = info.pss.takeIf { it > 0L },
            rssKb = info.rss.takeIf { it > 0L },
            description = info.description,
        )
    }
}
```

这段映射把 0 内存样本转成缺失值，避免服务端把“尚未采样”解释成“占用为零”。归档端还应补充包名、应用版本、设备型号、系统 build、API level、读取时间和客户端生成的 `caseId`。

### traceInputStream 的类型和空值

`getTraceInputStream()` 从 API 30 起存在，但它的内容随 reason 和系统版本变化：

| 条件 | 可能返回的内容 | 处理要求 |
|---|---|---|
| 与 ANR 关联的记录，API 30+ | 系统在进程死亡前保存的 ANR trace | 通常对应 `REASON_ANR`；已恢复的 ANR 也可能把 trace 附在后来因其他原因退出的记录上 |
| `REASON_CRASH_NATIVE`，API 31+ | 符合 AOSP tombstone schema 的 protobuf | 保存原始字节并使用对应 protobuf schema 解析 |
| 其他 reason，或附件已丢失 | `null` | 正常降级，不能判成采集代码故障 |

trace 保存在独立的全局循环缓冲中，新事件可能覆盖旧附件，其中也包括其他应用产生的 native crash。因此，即使 reason 满足条件，返回值仍可能为 `null`。ANR trace 和 tombstone protobuf 不是同一种格式，文件扩展名、解析器和服务端内容类型都要分开。

Native crash 的系统 tombstone 与 Crashpad/Breakpad minidump 也不等价。SDK minidump 由自有崩溃处理流程写入，系统 tombstone 由平台生成。两份证据可以用 signal、进程、线程、时间和 build ID 交叉校验；任一份缺失都不应删除另一份。

### 低内存原因需要能力探测

并非所有设备都支持上报 `REASON_LOW_MEMORY`。在不支持该能力的设备上，内存压力导致的 kill 可能表现为 `REASON_SIGNALED`，且 `status` 为 `SIGKILL`。应用应调用 `ActivityManager.isLowMemoryKillReportSupported()` 记录设备能力。

即便设备不支持 low-memory kill report，也不能把每个 `SIGKILL` 都归因为低内存。`SIGKILL` 只说明终止信号；用户操作、系统策略和其他管理动作也可能产生相似结果。可靠归因还需要系统能力标记、前后台状态、内存趋势和同一时间段的设备压力证据。

### Android 17 MemoryLimiter

Android 17 在一部分设备上实施基于设备总内存的应用内存限制。该行为位于“影响所有应用”的变更列表中，不受 `targetSdkVersion` 限制。官方文档没有给出可供应用依赖的固定 RAM 门槛，因此线上逻辑不应按设备是否为 6GB 或某个具体机型预判。

受 MemoryLimiter 影响的进程退出有明确的公开识别方式：

- `ApplicationExitInfo#getReason()` 返回 `REASON_OTHER`。
- `getDescription()` 包含精确字符串 `"MemoryLimiter:AnonSwap"`，后面还可能有其他信息。
- 注册 `TRIGGER_TYPE_ANOMALY` 后，系统可以在命中内存限制时提供 Java heap dump，但仍受设备覆盖、后台采样和限流约束。

这里可以对精确标记做包含判断，因为 Android 17 行为变更文档给出了该协议。不要把它缩写为匹配 `"MemoryLimiter"`，也不要把所有 `REASON_OTHER` 都归到内存限制。MemoryLimiter kill 与 Java `OutOfMemoryError` 是不同事件：前者走 anomaly trigger，后者才对应 `TRIGGER_TYPE_OOM`。

## Android 15：应用请求 profiling

Android 15 / API 35 引入公开的 `ProfilingManager`。实现位于 Mainline Profiling 模块 `packages/modules/Profiling`，Android 17 的直接 API 签名为：

`requestProfiling(int profilingType, Bundle parameters, String tag, CancellationSignal cancellationSignal, Executor executor, Consumer<ProfilingResult> listener)`

应用也可以使用 AndroidX Profiling 提供的 request builder，减少参数 Bundle 与平台版本差异带来的维护成本。平台支持四种请求类型：

| profiling type | 适用问题 | 主要成本或限制 |
|---|---|---|
| Java heap dump | Java 堆泄漏、堆占用构成 | 可能暂停应用；文件可能含对象字段和业务数据 |
| heap profile | 分配热点和一段时间内的堆增长 | 采样结果有偏差；窗口要覆盖问题发生阶段 |
| stack sampling | CPU 热点的低频观察 | 短函数和瞬态热点可能未被采到 |
| system trace | 启动、卡顿、调度、Binder 与系统交互 | 缓冲区和时长影响文件大小与覆盖范围 |

请求是异步的，也不是必定执行。系统和进程级 rate limiter、已有任务、执行或后处理错误、磁盘不足、非法参数都可能使请求失败；系统也可能延后开始。应用要归档 `ProfilingResult#getErrorCode()` 和可选的 `getErrorMessage()`，并把“请求已发出”和“结果已生成”作为两个状态。

结果回调有两个入口：

- 请求专用的 `Executor` 与 `Consumer<ProfilingResult>`，用于当前 `requestProfiling()`。
- `registerForAllProfilingResults()` 注册的全局监听器，接收应用请求结果，也接收系统 trigger 结果。

如果请求没有提供专用 listener/executor，且进程也没有全局监听器，调用方收不到结果通知。系统触发的结果没有请求现场的 callback，只能经全局监听器交付；应用在下次启动后重新注册时，也可能收到此前生成的结果。

成功文件的位置必须读取 `ProfilingResult#getResultFilePath()`。目录结构和文件命名属于实现细节，不能在上传器里拼 `/data/user/0/<package>/files/profiling/...`。`ProfilingResult` 可直接读取 error code、error message、结果路径、tag 和 trigger type；它没有 `getProfilingType()`。主动请求时，应用要把请求类型和自有 request ID 一起保存。系统触发时，应根据 trigger type、tag 和收到的文件类型归档，不要虚构 profiling type 字段。

## Android 16-17：系统事件触发 profiling

trigger 注册表达的是“应用对某类系统事件感兴趣”。它不保证系统持续录制，也不保证每次事件都有附件。系统通常以采样方式运行后台 trace；事件发生时若有可用历史缓冲、应用已注册且限流允许，才会保存结果。

### API 36

| trigger | 触发条件 | 系统结果 | 解释边界 |
|---|---|---|---|
| `TRIGGER_TYPE_APP_FULLY_DRAWN` | 冷启动后调用 `Activity.reportFullyDrawn()` | 正在运行的 system trace 快照 | 依赖应用正确调用 `reportFullyDrawn()` |
| `TRIGGER_TYPE_ANR` | 系统已识别 ANR，准备执行后续处置前 | 正在运行的 system trace 快照 | 触发不表示进程一定因 ANR 被杀 |

这两类结果都依赖系统当时存在可保存的后台 trace。ANR 的 `ApplicationExitInfo` trace 与这里的 Perfetto system trace 是两份不同证据，不能使用同一个解析器。

### API 36.1

| trigger | 触发条件 | 系统结果 |
|---|---|---|
| `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` | 先注册该 trigger，再调用 `requestRunningSystemTrace(tag)` | 正在运行的 system trace 快照 |
| `TRIGGER_TYPE_KILL_FORCE_STOP` | 用户在应用信息页点“强行停止” | 正在运行的 system trace 快照 |
| `TRIGGER_TYPE_KILL_RECENTS` | 用户从最近任务界面移除应用并导致终止 | 正在运行的 system trace 快照 |
| `TRIGGER_TYPE_KILL_TASK_MANAGER` | 用户在 Task Manager 中停止应用 | 正在运行的 system trace 快照 |

这些常量和方法在 API 36.1 才加入。接入代码要以 `SDK_INT_FULL` 对比 `VERSION_CODES_FULL.BAKLAVA_1`，并让 Android Lint 检查 minor SDK API。`SDK_INT == 36` 不能证明设备已经具备 36.1。

### API 37

| trigger | 触发条件 | 文档规定的结果与注意事项 |
|---|---|---|
| `TRIGGER_TYPE_OOM` | App 抛出 Java `OutOfMemoryError` | Java heap dump；自定义 `UncaughtExceptionHandler` 必须继续调用默认 handler |
| `TRIGGER_TYPE_ANOMALY` | 系统检测到资源异常 | 产物按异常类型变化，`ProfilingResult#getTag()` 提供附加分类 |
| `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | App 因过量 CPU 使用被杀，退出 reason 为 `REASON_EXCESSIVE_RESOURCE_USAGE` | AOSP/API reference 写明返回后台 system trace 快照 |
| `TRIGGER_TYPE_COLD_START` | `ApplicationStartInfo` 判断为 cold start | 新启动的 system trace 与 stack sampling profile |
| `TRIGGER_TYPE_APP_COMPAT` | 系统发现未来版本将不再支持的异常行为 | 产物随兼容性问题变化，tag 提供附加信息 |

`TRIGGER_TYPE_OOM` 依赖默认未捕获异常处理路径。自定义 handler 如果不继续调用原默认 handler，系统无法使用这个 trigger；应用仍可在合适时机主动请求 Java heap dump，但要评估进程当时是否还有足够资源完成请求。

`TRIGGER_TYPE_ANOMALY` 的产物不能预设为一种格式。Android 17 文档列出的场景包括：命中 OS memory limit 时返回 heap dump，过量 Binder 调用时返回 stack sample。多个 package 共享同一 UID 并同时注册某些异常 trigger 时，系统可能不提供附件。结果处理器应先看 trigger type、tag 和文件，再选择解析器。

`TRIGGER_TYPE_COLD_START` 会尽早启动一份新的 system trace 和 stack sampling profile，持续到应用调用 `reportFullyDrawn()`；未调用时，公开 API 文档给出的默认停止时间为 5 秒。它使用 discard buffer，缓冲区满后丢弃新事件，以保留启动初期的内容。采集启动仍可能有延迟，因此产物不保证覆盖进程创建后的每个事件。

`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 存在官方文档差异：`android-17.0.0_r1` 源码注释和 API reference 写的是后台 system trace 快照，Android 17 features 页面写的是 call-stack sample。接入端应保存系统返回的原始产物及文件类型，不要按 trigger 名写死解析器；这里以版本化源码和 API reference 作为接口语义锚点，同时保留该差异记录，等待官方文档一致。

## 证据归档：系统事实与应用推断分开

推荐把退出记录、profiling 结果、Crash SDK 样本和业务状态保存为不同记录类型。`caseId` 负责关联，不能用它抹去来源差异。

### 退出记录字段

| 字段 | 说明 |
|---|---|
| `source` | 固定为 `application_exit_info` |
| `packageName`、`processName` | 包和进程身份 |
| `packageUid`、`realUid`、`pid` | 系统身份；注意隔离进程和 PID 复用 |
| `timestampMs` | 系统记录的进程死亡时间 |
| `reason`、`status` | 公开 reason 与退出状态 |
| `pssKb`、`rssKb` | 最近一次样本；0 应按缺失处理 |
| `descriptionRaw` | 限制访问的原始描述，只对有文档保证的标记做机器判断 |
| `traceKind`、`traceHash` | `anr_trace`、`native_tombstone_proto` 或 `none` |
| `appVersion`、`device`、`osBuild`、`apiLevel` | 解释版本差异所需环境 |

退出记录的持久去重指纹可以由 `packageName + processName + packageUid + realUid + pid + timestampMs + reason + status` 生成。PID 会复用，不能单独做主键。读取窗口可能重复返回相同历史记录，因此应先按完整系统字段去重，再与客户端 case 做候选关联。

### profiling 结果字段

| 字段 | 说明 |
|---|---|
| `source` | `profiling_request` 或 `profiling_trigger` |
| `requestId` | 主动请求时由 App 生成；系统 trigger 可为空 |
| `requestedProfilingType` | 只在主动请求时由 App 自己记录 |
| `triggerType` | 从 `ProfilingResult#getTriggerType()` 读取；主动请求通常为 `TRIGGER_TYPE_NONE` |
| `tag` | 原样保存，同时限制长度和敏感信息 |
| `errorCode`、`errorMessage` | 结果状态 |
| `resultFilePathLocal` | 本地处理使用；不要直接作为服务端长期标识 |
| `artifactMime`、`artifactHash`、`artifactSize` | 按收到的文件计算 |
| `caseId`、`sessionId` | 应用侧关联字段 |

主动请求的去重指纹应包含 request ID、requested profiling type、tag 和文件 hash。系统 trigger 结果可使用 trigger type、tag、结果时间和文件 hash。没有文件时，也要保存 error code 或“系统未产出”的状态，避免重复请求掩盖系统限流。

### 常见事件的关联规则

| 事件 | 建议关联方式 | 不应采用的方式 |
|---|---|---|
| Java crash | Crash SDK 样本与 `REASON_CRASH` 按进程、时间、异常摘要做候选匹配 | 只看 PID |
| Native crash | minidump 与 `REASON_CRASH_NATIVE`、tombstone 按进程、signal、时间、build ID 匹配 | 把 tombstone 和 minidump 互相覆盖 |
| ANR | `REASON_ANR`、ANR trace、triggered system trace 按事件时间和进程关联 | 假定 trigger 发生后进程必然被杀 |
| Java OOM | `TRIGGER_TYPE_OOM` heap dump 与 Java crash/退出记录关联 | 把 MemoryLimiter kill 当成 OOM |
| MemoryLimiter | `REASON_OTHER` 加精确 description 标记，并关联 anomaly heap dump | 匹配所有 `REASON_OTHER` |
| 用户终止 | `REASON_USER_REQUESTED` 或 36.1 用户终止 trigger 单独分类 | 计入 crash 率 |

时间接近只能生成候选关系。服务端应保留原记录，给关联关系附上算法版本和置信度，便于后续修正。

## 排障决策表

| 问题 | Android 10 | Android 11-14 | Android 15 | Android 16 | Android 17 |
|---|---|---|---|---|---|
| 慢启动 | 自有启动指标；实验设备 Perfetto | 同左，加退出记录排除异常终止 | 主动请求 system trace | 可注册 `APP_FULLY_DRAWN` | 优先评估 `COLD_START` trace + stack sampling |
| ANR | 卡顿监控、bug report、人工 Perfetto | `REASON_ANR` + 可选 ANR trace | 可主动请求 system trace 复现 | 增加 `ANR` trigger 快照 | 同 Android 16 |
| Native crash | Crashpad/Breakpad minidump | API 31+ 再取可选 tombstone protobuf | 同左 | 同左 | 同左 |
| Java OOM | Crash SDK 与内存趋势 | 同左，加退出记录 | 可控场景主动请求 heap dump/profile | 同左 | 增加 `OOM` trigger heap dump |
| 被系统杀 | 自有前后台和资源记录 | reason、status、最近 PSS/RSS；探测 LMK reporting | 同左 | 可增加部分 trigger | CPU kill、anomaly 和 MemoryLimiter 证据 |

高版本能力是补充证据，不应导致低版本日志、指标和 Crash SDK 被删除。某个 trigger 在 API 上可用，也不表示每台设备、每次事件都能产生结果。

## 隐私、限流与采集成本

profiling 文件可能包含比普通日志更敏感的内容：

- Java heap dump 可能保存对象字段、缓存、请求参数和页面状态。
- system trace 可能出现方法名、线程名、调度时序、Binder 交互及部分系统上下文。
- stack sampling 和 heap profile 会暴露代码结构、调用栈或分配路径。
- ANR trace、tombstone 与 minidump 可能包含路径、寄存器、映射和构建信息。

采集设计至少要包含用户授权或适用的合规依据、数据最小化、传输与静态加密、访问审计、保留期限、删除机制和远程关闭能力。tag、caseId 和文件名中不要放用户输入、账号、URL、token 或其他敏感值。

采集预算应来自设备实验和线上观测。system trace 按时长与缓冲大小评估，stack sampling 按采样频率评估，heap dump 按停顿、峰值内存和文件大小评估。配置应区分 case、版本、设备和采集类型；系统 rate limiter 之外，应用仍需自己的并发控制与预算。命中限流或跳过采集时，上报轻量状态和原因，不要立即循环重试。

## 与 26.5 证据包模板的关系

26.5 负责问题受理、复现步骤、远程日志、灰度处置和问题单流程。版本化的“系统诊断附件”包括：

- `ApplicationExitInfo` 退出记录及可选 ANR/native 附件；
- 应用请求产生的 system trace、heap dump、heap profile 或 stack sampling；
- trigger 产生的文件、tag、trigger type 和错误状态；
- 每份文件的来源、hash、大小、采集时间、系统版本、权限和保留期限。

问题单展示时应保留来源标签。值班人员需要知道某个结论来自系统退出记录、App 自有日志还是 profiling 文件，才能判断证据强度。

## 源码与官方文档锚点

- [ApplicationExitInfo.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [ActivityManager.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [ProfilingManager.java（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [ProfilingResult.java（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingResult.java)
- [ProfilingTrigger.java（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [ApplicationExitInfo API reference](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [ProfilingManager API reference](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingResult API reference](https://developer.android.com/reference/android/os/ProfilingResult)
- [ProfilingTrigger API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Profiling limitations](https://developer.android.com/topic/performance/tracing/profiling-manager/will-my-profile-always-be-collected)
- [Android 17：影响所有应用的行为变更](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android 17：功能与 API](https://developer.android.com/about/versions/17/features)
- [Build.VERSION API reference](https://developer.android.com/reference/android/os/Build.VERSION)
- [Build.VERSION_CODES_FULL API reference](https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL)
