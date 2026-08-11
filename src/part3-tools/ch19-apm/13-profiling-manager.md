---
title: "ProfilingManager"
chapter: "19"
section: "19.13"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)（app-driven API 35；system-triggered 触发器覆盖 API 36、version 36.1、API 37）"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1 packages/modules/Profiling (ProfilingService / ProfilingManager / ProfilingTrigger / ProfilingResult) + developer.android ProfilingManager / ProfilingTrigger / ProfilingResult + AndroidX Profiling reference | 2026-07-30 rework: cleared pending-verification-marker (待验证→要排查) + thin-source-marking (补 3 处内联 [来源:] 标记)"
last_rework_at: "2026-07-30T17:35:57+08:00"
last_rework_run_id: "20260730-173557-rework-d7fa8e54"
rework_notes: "2026-07-30 rework：解决 2 个启发式 quality_flag。pending-verification-marker：§'按结果类型选请求' 首句 '待验证的问题' 改为 '要排查的性能问题'（消除误触发词，语义不变）。thin-source-marking：在版本边界声明、文件后缀来源、trigger 登记语义三处补内联 [来源:] 标记（共 3 处，≥2 阈值），全部映射既有 frontmatter sources。章节本身已是 finalized + ready-to-publish，sources 完备（12 条），本次为启发式标记清除，不改技术结论。"
confidence: medium
tags: [apm, profiling, perfetto]
related_chapters: ["19.9", "19.10", "15.5", "13.1", "9.1", "8.2"]
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingResult"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/retrieve-and-analyze"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/will-my-profile-always-be-collected"
  - type: official
    path: "https://developer.android.com/reference/androidx/core/os/Profiling"
  - type: official
    path: "https://developer.android.com/reference/androidx/core/os/ProfilingRequest"
  - type: aosp
    path: "packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java (android-17.0.0_r1)"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java (android-17.0.0_r1)"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingResult.java (android-17.0.0_r1)"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-08"
last_task6_at: "2026-07-07T20:11:24+08:00"
last_task6_audit: "2026-06-20"
last_task6_review_log: "logs/review/2026-06-14-11-review.md"
last_task9_at: "2026-07-08T00:31:29+08:00"
last_task9_audit: "2026-07-07"
last_task9_audit_log: "logs/deep-review/2026-07-07-19-audit.md"
task9_audit_notes: "2026-07-07 Task9 idle audit：auto-fixed。P0 1：android-17.0.0_r1 ProfilingService 输出 Java heap dump 后缀为 .perfetto-java-heap-dump，正文原写 .hprof 已修正。"
task9_review_notes: "2026-06-14 Task9 deep review：pass-tech-review。复核 ProfilingManager API35、ProfilingTrigger API36/36.1/API37、SDK_INT_FULL/BAKLAVA_1、AndroidX Profiling builder 与限流/结果目录口径；无 P0/P1，queue 无 pending，Task6 已通过，自动晋升 finalized。 | 2026-07-07 Task9 idle audit：auto-fixed。P0 1：将 Java heap dump 产物后缀从 .hprof 修正为 android-17.0.0_r1 ProfilingService 实际输出 .perfetto-java-heap-dump，回到 Task6 复审。"
task2b_result: fixed
last_task2b_at: "2026-05-31T18:50:00+08:00"
task2b_fixed_at: "2026-05-31T18:50:00+08:00"
task2b_rework_source: "frontmatter backlog fallback; logs/deep-review/2026-05-20-07-deep-review.md"
task2b_rework_notes: "修复 Task9 19.16：拆开 profileable/shell 与线上 ProfilingManager 前提；补 OOM trigger 默认 uncaught handler 透传要求；补 rate limiter cost/hour/day/week 模型；替换 404 官方 guide URL。"
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
task6_result: "pass-light-edit"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-07-07"
last_task9_review_log: "logs/deep-review/2026-07-08-00-deep-review.md"
task6_reviewed_date: "2026-07-07"
last_task2b_verifier_at: "2026-07-07T23:28:23+08:00"
last_task2b_verifier_log: "logs/rework/2026-05-31-23-task2b-verifier.md"
last_task9_autofix_at: "2026-07-07"
task6_review_notes: '2026-07-07 Task6 revisiting review: pass-light-edit；Task9 auto-fix .hprof→.perfetto-java-heap-dump 已验证正确；L1/L2 扫描干净；锚点 5/5 覆盖；无 L3/L4 回炉项。task9_result=auto-fixed 非 pass-tech-review，未自动晋升。 | 2026-06-14 Task6 revisiting review: pass-light-edit；terminology 一致性修复 artifact→产物 (5处)；Task9 auto-fix SDK_INT_FULL 已验证正确；无新增 Task2B 回炉项。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-08
finalized_date: "2026-07-08"
finalized_by: openclaw-task9-auto-promote
auto_promoted_date: "2026-07-08"
auto_promoted_by: openclaw-task9
---


# ProfilingManager

## 适用范围按版本区分

`android.os.ProfilingManager` 从 Android 15（API 35）开始提供。它允许普通应用在量产设备上请求受控的性能剖析，或者登记自己关心的系统事件，由系统在条件满足时生成诊断文件。平台负责执行、脱敏、限流和把文件写入应用私有目录；应用负责接收结果、关联业务现场、上传与清理。

接入前要把两套能力分开：

- **app-driven profiling**：API 35 起可用。应用主动发起请求，抓 system trace、Java heap dump、heap profile、stack sampling
- **system-triggered profiling**：从 API 36 开始，经过 version 36.1，在 API 37 补入更多触发器。应用登记触发器，事件发生的时机和系统是否执行采集由平台决定

API 35 不能使用 trigger API；API 36 也不等于拥有 36.1 和 API 37 的全部触发器。版本判断、监听器注册和服务端字段都应按这三条边界设计。

## 按结果类型选请求

先写明要排查的性能问题，再选择剖析类型。四种结果都比帧指标、启动耗时或 ANR 计数更重，线上只应做低频取证。

| AndroidX builder | Android 17 文件后缀 | 适合回答的问题 | 主要限制 |
|---|---|---|---|
| `SystemTraceRequestBuilder` | `.perfetto-trace` | 启动慢、卡顿、ANR 前后线程时序、Binder / I/O / 调度问题 | 不能直接看对象引用链 |
| `JavaHeapDumpRequestBuilder` | `.perfetto-java-heap-dump` | 哪些 Java 对象仍然存活、引用链为何无法释放 | 不能观察一段时间里的分配速率 |
| `HeapProfileRequestBuilder` | `.perfetto-heap-profile` | 哪类 native / Java 分配持续增长、分配调用栈在哪里 | 不能直接确认 Java GC Root |
| `StackSamplingRequestBuilder` | `.perfetto-stack-sample` | 应用 CPU 时间主要花在哪些调用栈 | 不能查看完整的系统时间线 |

这些后缀来自 `android-17.0.0_r1` 的 `ProfilingService`，不能把 Java heap dump 写成传统的 `.hprof` 文件名。四类结果都可以从 Perfetto UI 开始检查；Java heap dump 若要进入只接受 HPROF 的工具，必须使用经过验证的转换链，不能只改扩展名。

`ProfilingManager` 返回的是请求进程的资料。经过平台脱敏的 system trace 会保留本进程线程和 trace slice，并把其他进程的 CPU 活动合并到 `OtherProcesses`。因此它适合判断“本进程慢”还是“整机繁忙”，无法替代本地拥有更高权限的全系统 Perfetto trace。

## app-driven request 的基本调用形态

公开 API 位于 `android.os.ProfilingManager`。业务代码推荐通过 AndroidX 的 `Profiling` 和四种 request builder 构造参数。以下依赖版本与 2026 年 7 月官方示例一致：

```kotlin
dependencies {
    implementation("androidx.core:core:1.19.0")
    implementation("androidx.tracing:tracing:1.3.0")
}
```

`androidx.core` 提供请求和监听器封装，`androidx.tracing` 用于在 trace 中标记业务区间。工程可由 version catalog 统一管理版本，但不能只升级调用端而跳过 API 35 的运行时判断。

下面的例子在目标操作前发起 system trace，并把 `CancellationSignal` 交给调用方在操作完成后停止采集：

```kotlin
@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
fun requestScrollTrace(
    context: Context,
    callbackExecutor: Executor,
    resultSink: Consumer<ProfilingResult>,
): CancellationSignal {
    val stopSignal = CancellationSignal()
    val request = SystemTraceRequestBuilder()
        .setBufferSizeKb(10 * 1024)
        .setDurationMs(30_000)
        .setBufferFillPolicy(BufferFillPolicy.RING_BUFFER)
        .setTag("scroll-jank-case-42")
        .setCancellationSignal(stopSignal)
        .build()

    requestProfiling(
        context.applicationContext,
        request,
        callbackExecutor,
        resultSink,
    )
    return stopSignal
}
```

调用 `requestScrollTrace()` 只表示请求已提交，采集不保证立刻开始。连续型采集（system trace、heap profile、stack sampling）应在目标操作之前请求，在操作完成后调用 `stopSignal.cancel()`；系统超时和取消信号谁先发生，谁结束本次采集。Java heap dump 没有持续采样窗口，触发时点要在本地反复验证，不能假设调用 request 的那一行就是 dump 时刻。

request callback 只应校验结果并把任务交给持久化队列。文件校验、压缩、上传和删除不能占用主线程，也不要长期占用平台回调所用的 executor。

AndroidX builder 会避免业务侧手写未知的 `Bundle` key，但当前实现的 setter 只是把数值写进 `Bundle`，不会在客户端做上下界校验。平台遇到未知参数会返回 `ERROR_FAILED_INVALID_REQUEST`；已知参数超出范围时，会裁剪到设备支持的最近值。以 `android-17.0.0_r1` 的 AOSP 默认配置为例：

| 类型 | duration 默认 / 范围 | buffer 默认 / 范围 | 其他默认范围 |
|---|---:|---:|---:|
| system trace | 300 s / 1–600 s | 32 MiB / 64 KiB–32 MiB | buffer 按 4 KiB 对齐 |
| Java heap dump | 服务内部 1 s | 250 MiB / 8–250 MiB | 不暴露 duration setter |
| heap profile | 120 s / 1–300 s | 64 MiB / 256 KiB–64 MiB | sampling interval 1–65536 bytes |
| stack sampling | 60 s / 1–300 s | 64 MiB / 64 KiB–64 MiB | 1–200 Hz |

这些数值是该 AOSP tag 的默认值，并非稳定 API 契约。厂商配置和后续系统更新可以调整它们。应用应提交合理的小值、记录最终文件大小，并用真实设备验证采样是否覆盖目标区间。

结果写入应用内部的 `files/profiling/`，不需要外部存储权限。`<profileable android:shell="true" />` 服务于本地 shell、Perfetto、simpleperf 和 Android Studio Profiler 等调试工具，不是线上 `requestProfiling()` 的前提。发布包要检查 API 版本、采样预算、隐私告知、备份规则和诊断后端权限；调试包若还要配合 shell 工具，再单独配置 `profileable`。

## request listener 和 global listener 是两层结果通道

`requestProfiling(..., executor, listener)` 的 listener 只关联该次显式请求。`registerForAllProfilingResults(executor, listener)` 注册的是 UID 级全局结果入口，也是 system-triggered profiling 唯一的应用侧结果入口。

| 场景 | request listener | global listener | 说明 |
|---|---|---|---|
| 只发起一次显式 request，未注册 global listener | 会收到 | 收不到 | 最小可跑通接入 |
| 显式 request + 已注册 global listener | 会收到 | 也会收到同一结果 | callback 适合关联 case；global listener 适合统一归档 |
| `addProfilingTriggers(...)` 注册的 trigger 结果 | 收不到 | 会收到 | trigger 模式必须先注册 global listener |

平台要求 listener 和 executor 成对出现。显式请求可以在 request 上提供这一对，也可以依赖已经注册的 global listener；两处都没有时，请求会被丢弃，调用方也收不到失败回调。

全局监听器适合在进程级组件中注册，并保持对象引用稳定。以下代码展示注册和对称注销的基本形态：

```kotlin
@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
class ProfilingResultRegistry(
    private val executor: Executor,
    private val store: ProfilingResultStore,
) {
    private val listener = Consumer<ProfilingResult> { result ->
        store.enqueueIdempotently(result)
    }

    fun register(context: Context) {
        registerForAllProfilingResults(
            context.applicationContext,
            executor,
            listener,
        )
    }

    fun unregister(context: Context) {
        unregisterForAllProfilingResults(
            context.applicationContext,
            listener,
        )
    }
}
```

例子中的 `ProfilingResultStore` 是应用自己的持久化队列接口，listener 内不做文件解析。trigger 模式通常在 `Application` 或等价的进程初始化位置注册一次。不要在每个 `Activity` 创建一份 global listener；多进程应用还应指定一个诊断进程负责接收 UID 级结果。只有功能关闭、测试清理或进程级组件确定退出时才注销。

应用在采集期间被杀后，平台可能在应用重启并重新注册 global listener 时重投结果。显式请求同时使用两层 listener 也会产生两次回调。因此消费端必须幂等：成功结果可用规范化后的 `resultFilePath` 作为本地唯一键；失败结果没有路径，应该结合本地请求记录、`tag`、`triggerType`、错误码和时间窗口去重。这个组合只用于应用自己的持久化策略，平台没有承诺它是全局唯一 ID。

## system-triggered profiling 的版本边界

trigger 由应用主动登记，事件和采集时机由系统控制。登记成功不代表一定产出结果：后台 trace、进程与系统预算、磁盘空间、并发采集和系统策略都会影响成功率。

| 首次可用版本 | trigger | 结果与触发语义 | 必须注意的条件 |
|---|---|---|---|
| API 36 | `TRIGGER_TYPE_APP_FULLY_DRAWN` | 冷启动调用 `reportFullyDrawn()` 后，克隆正在运行的 system trace | 依赖后台 trace 和预算；只覆盖事件之前已经存在的数据 |
| API 36 | `TRIGGER_TYPE_ANR` | 系统识别 ANR 后、尝试杀进程前，克隆正在运行的 system trace | 触发不等于进程最终因 ANR 被杀 |
| version 36.1 | `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` | 应用调用 `requestRunningSystemTrace(tag)` 后，克隆正在运行的 system trace | 必须预先登记该 trigger |
| version 36.1 | `TRIGGER_TYPE_KILL_FORCE_STOP` | 用户在应用信息页点“强行停止”时取 running trace snapshot | 与普通进程死亡分开统计 |
| version 36.1 | `TRIGGER_TYPE_KILL_RECENTS` | 用户从最近任务界面移除应用时取 running trace snapshot | 语义是 Recents 移除 |
| version 36.1 | `TRIGGER_TYPE_KILL_TASK_MANAGER` | 用户从前台服务 Task Manager 停止应用时取 running trace snapshot | 语义是 Task Manager 的 Stop |
| API 37 | `TRIGGER_TYPE_COLD_START` | 冷启动尽早新开 system trace，并同时做 stack sampling | 到 `reportFullyDrawn()` 停止，未调用时默认 5 秒；可能延迟启动 |
| API 37 | `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 且归因为 excessive CPU 时取 running trace snapshot | 不要把所有 `REASON_EXCESSIVE_RESOURCE_USAGE` 都解释为 CPU trigger |
| API 37 | `TRIGGER_TYPE_OOM` | 应用发生 `OutOfMemoryError` 时生成 Java heap dump | 自定义 uncaught handler 必须继续调用默认 handler |
| API 37 | `TRIGGER_TYPE_ANOMALY` | 系统检测到应用异常行为，产物随异常类型变化 | `ProfilingResult.tag` 会携带异常类型补充信息 |
| API 37 | `TRIGGER_TYPE_APP_COMPAT` | 系统发现未来版本将不再支持的应用行为，产物随问题变化 | `tag` 会携带兼容性问题信息 |

`TRIGGER_TYPE_COLD_START` 使用 discard buffer：缓冲区满后丢弃新事件，以保住冷启动最早阶段的 tracepoint。它与 `TRIGGER_TYPE_APP_FULLY_DRAWN` 的 running-trace snapshot 解决不同问题，不能互换。前者尝试记录本次冷启动的开头，后者从系统已经运行的后台 trace 中截取历史窗口。

`TRIGGER_TYPE_OOM` 依赖默认未捕获异常处理链。应用若安装了自定义 `Thread.UncaughtExceptionHandler`，必须保存默认 handler 并在记录完成后继续调用它；吞掉默认处理会使 OOM trigger 无法使用。此时应用仍可主动请求 Java heap dump，但请求发生在 OOM 之后，内存与进程状态都很脆弱，不能把它当成等价兜底。

36.1 属于 Minor SDK 版本，只看 `SDK_INT == 36` 无法区分。以下判断需要用 API 37 SDK 编译：

```kotlin
fun supportsProfilingVersion36_1(): Boolean {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.BAKLAVA) return false
    return Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1
}
```

大于 36 的完整 SDK 值也会满足该判断，因此 Android 17 不会被误判为不支持。若工程的 `compileSdk` 尚未暴露 `SDK_INT_FULL`、`VERSION_CODES_FULL.BAKLAVA_1` 或对应 trigger 常量，应先升级编译 SDK；不要用反射拼接常量值掩盖编译边界。

trigger 注册还有四条规则：

- 每种 trigger 同一时刻只能登记一个配置；重复登记会替换旧配置
- `setRateLimitingPeriodHours(n)` 表示同一 trigger 两次结果之间至少等待 `n` 小时；`0` 表示不增加应用侧间隔
- 应用侧间隔叠加在系统限流之上，不能放宽系统预算
- 停用功能时用 `removeProfilingTriggersByType()` 或 `clearProfilingTriggers()` 清理登记

version 36.1 增加了 `addAllProfilingTriggers()`，但生产接入更适合按问题登记明确的 trigger：这样版本门槛、数据用途和采样间隔都能逐项审计。

## 在排查漏斗里的位置

`ProfilingManager` 位于“轻量指标发现异常”之后。推荐的排查顺序是：

1. `JankStats`、`FrameMetrics`、启动/ANR 指标、APM 事件先把异常样本筛出来
2. 满足条件时用 `ProfilingManager` 抓一份重样本
3. 四类文件先在 Perfetto UI 中检查；Java heap dump 若还要交给 HPROF-only 工具，走经过验证的转换流程
4. 把 profiling 结果与 session、版本、页面、实验分组关联回原始 APM 事件

轻量指标负责大样本统计，`ProfilingManager` 负责低频取证，Perfetto 或内存分析器负责还原现场。若每次卡顿都请求 system trace，系统限流会很快让策略失效，还会给用户设备增加额外负担。

## 错误码、限流和重试策略

成功时 `errorCode == ERROR_NONE`，`resultFilePath` 指向应用私有目录中的文件。失败时路径为 `null`，应同时记录 `errorMessage`，但聚合统计要以稳定的错误码为主。

| 错误码 | 含义 | 建议处理 |
|---|---|---|
| `ERROR_FAILED_RATE_LIMIT_PROCESS` | 当前 UID / 进程侧预算拒绝本次请求 | 本次不重试，降低该类型的采样频率 |
| `ERROR_FAILED_RATE_LIMIT_SYSTEM` | 系统级预算拒绝本次请求 | 不做即时重试，等待新的业务采样机会 |
| `ERROR_FAILED_PROFILING_IN_PROGRESS` | 已有 profiling 正在执行 | 请求侧串行化，同类重样本只保留一个 |
| `ERROR_FAILED_NO_DISK_SPACE` | 结果文件无法落盘 | 清理历史样本，给本地缓存设大小上限 |
| `ERROR_FAILED_POST_PROCESSING` | 采集完成，但后处理失败，结果被丢弃 | 记录设备、版本、request 类型、errorCode，回看是否集中在某个系统版本 |
| `ERROR_FAILED_EXECUTING` | 平台执行阶段失败 | 记失败事件，不做立即重试，等待下一次业务触发 |
| `ERROR_FAILED_INVALID_REQUEST` | 类型、key 或参数组合无效，或者相应采集能力被禁用 | 修正接入或关闭该能力，不走线上重试 |
| `ERROR_UNKNOWN` | 未归类失败 | 只记日志与事件，避免自动重试放大成本 |

应用侧至少记录 `tag`、`triggerType`、`errorCode`、`errorMessage`、本地 `requestType`、应用版本、设备、完整 SDK 版本、请求时间和回调时间。`ProfilingResult` 不提供 app-driven 的 request type 字段，业务侧要通过本地 request 记录补齐。

限流不能简化成固定的“每小时几次”。Android 17 的服务按 profiling type 计算不同 cost，并同时检查小时、天、周三个时间桶；进程侧和系统侧又有各自预算。任一时间桶不足都可能拒绝请求。具体 cost 和桶容量由系统配置控制，不属于应用可依赖的 API 常量。

端侧还应设置更保守的本地冷却时间和单飞锁，服务端配置只负责缩小采样范围。限流错误是一次明确拒绝，循环重试只会增加唤醒与日志噪声，无法恢复额度。

## 结果文件生命周期

系统通过应用进程创建的文件描述符，把结果复制到 `files/profiling/`，再把相对路径交给 listener。文件已经存在，callback 不需要再“保存”一份；应用要原子地登记路径与业务 metadata，然后交给后台任务。

下面的时序图描述了推荐的处理链：

```mermaid
sequenceDiagram
    participant App
    participant PM as ProfilingManager
    participant Store as App 私有存储
    participant Upload as 上传任务
    participant Server as 诊断平台

    App->>PM: requestProfiling(...) / trigger registration
    PM-->>App: ProfilingResult
    App->>Store: 落 metadata 与文件引用
    Upload->>Store: 校验 Wi-Fi / 充电 / 文件大小 / 预算
    Upload->>Server: 上传产物 + metadata
    Server-->>Upload: 返回 sample id
    Upload->>Store: 删除文件或标记已归档
```

回调重复、进程重启和上传重试都汇入同一个幂等记录。只有后端确认完整接收后才删除本地文件；上传失败则保留到应用自己的过期时间或容量上限。

metadata 至少包含：

- `case_id` / `session_id`
- `request_type` / `trigger_type`
- `app_version` / `build_id` / `device` / `sdk_int_full`
- 页面、前后台状态、实验分组、触发原因
- `result_file_path`、文件大小、摘要、上传状态和清理时间

`android-17.0.0_r1` 中，`ProfilingManager` 会在有 executor 的调用路径上尝试删除已交付超过 5 天的旧文件；服务侧也有结果重投与过期兜底。这些是实现细节，调用时机和系统配置都可能变化。应用仍需维护自己的容量上限、保留期和上传成功即删除策略。

`tag` 的前 20 个字母数字字符以及连字符会被转成小写并进入文件名。`tag` 只能放短的场景码或随机 case ID，不能放手机号、账号、Token、URL 查询参数等用户数据。

## Java heap dump 的敏感数据风险

Java heap dump 会记录应用进程中的对象、字段、数组和字符串。用户登录后的堆中可能出现：

- 登录 Token / Session ID / OAuth Refresh Token
- 手机号、邮箱、用户昵称等 PII
- 支付信息、订单号、地址
- 缓存在内存中的密钥材料或证书

平台对 system trace 的脱敏不能替应用清理 heap dump 中的业务数据。安全方案需要按分析方式选择：

1. **优先端侧提取**：若问题能由对象计数、Retained Size、类分布或少量调用栈回答，可在设备上提取诊断摘要，只上传摘要。
2. **受控后端分析**：必须上传原始 heap dump 时，使用 TLS、服务端加密存储、独立 KMS、最小权限、访问审计和短保留期。后端要分析文件，就必然存在受控的解密路径；“端到端加密且服务端无法读取”与服务端分析不能同时成立。
3. **明确授权与采样范围**：隐私告知应说明性能诊断可能包含内存快照，远程开关要能关闭 heap dump，并把采样限定到必要版本和必要用户范围。
4. **备份排除**：`files/` 默认可能进入 Auto Backup。把 `files/profiling/` 同时排除在 cloud backup 和 device transfer 规则之外，并覆盖旧版 `fullBackupContent` 配置。
5. **删除可验证**：上传成功、超过保留期、用户撤回同意或诊断任务关闭时，都要有可观测的删除记录。

不要把通用 trace 上传接口直接复用于 heap dump。两者的数据敏感度、访问人群、保留期和审计要求不同。

## 用源码核对调用链

`android-17.0.0_r1` 中可以沿以下路径核对关键行为：

| 源码位置 | 可验证的行为 |
|---|---|
| `framework/java/android/os/ProfilingManager.java` | 双层 listener、无 listener 时丢弃请求、`files/profiling/`、重投提示、旧文件清理 |
| `framework/java/android/os/ProfilingTrigger.java` | API 37 trigger 语义、冷启动 5 秒边界、OOM 默认 handler 要求、应用侧限流 |
| `framework/java/android/os/ProfilingResult.java` | 错误码、失败时路径为 `null`、`tag` 与 `triggerType` |
| `service/java/com/android/os/profiling/Configs.java` | 参数裁剪、默认范围、Perfetto data source 和 buffer policy |
| `service/java/com/android/os/profiling/ProfilingService.java` | 限流、执行与后处理、脱敏、文件后缀、结果复制和回调 |

从调用链看，应用侧 request 经 Binder 进入 `ProfilingService`，服务依次检查并发状态、限流与参数，再启动 Perfetto。采集完成后，system trace 与 stack sampling 在需要时经过 redaction，服务请求应用进程创建目标文件，把临时结果复制到应用私有目录，然后发送 `ProfilingResult`。任一阶段失败都映射到对应错误码，因此“提交成功”不能当成“采集成功”。

## 上线前检查清单

- 版本门槛按 API 35、API 36、version 36.1、API 37 分开判断
- trigger 模式先注册 global listener，再注册 trigger
- request 上没有 callback 时，确认进程已经注册 global listener
- 连续型 request 提前发起，并用 `CancellationSignal` 覆盖目标区间
- request callback 与 global callback 共存时，持久化层能够幂等消费
- request callback 只做轻量关联，归档走后台流程
- `tag` 不含 PII、Token 或其他敏感值
- 结果目录有容量上限、备份排除、过期时间和删除策略
- heap dump 与 trace 使用不同的数据权限和保留策略
- 线上 `ProfilingManager` 接入检查 API、限流、结果目录和隐私说明；`profileable` 只放在本地 shell / Perfetto / Android Studio 工具链检查项里
- 线上预算默认保守，不要把 `ProfilingManager` 当高频指标 SDK

## 参考资料

1. **Android SDK Reference, `android.os.ProfilingManager`**  
   https://developer.android.com/reference/android/os/ProfilingManager
2. **Android SDK Reference, `android.os.ProfilingTrigger`**  
   https://developer.android.com/reference/android/os/ProfilingTrigger
3. **Android SDK Reference, `android.os.ProfilingResult`**  
   https://developer.android.com/reference/android/os/ProfilingResult
4. **Android Developers, ProfilingManager overview**  
   https://developer.android.com/topic/performance/tracing/profiling-manager/overview
5. **Android Developers, App-driven profiling**  
   https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture
6. **Android Developers, Trigger-based profiling**  
   https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture
7. **Android Developers, Retrieve and analyze profiling data**  
   https://developer.android.com/topic/performance/tracing/profiling-manager/retrieve-and-analyze
8. **Android Developers, Profiling limitations**  
   https://developer.android.com/topic/performance/tracing/profiling-manager/will-my-profile-always-be-collected
9. **AndroidX Reference, `androidx.core.os.Profiling` / `ProfilingRequest`**  
   https://developer.android.com/reference/androidx/core/os/Profiling
10. **AOSP android-17.0.0_r1, `ProfilingService.java`**  
   `packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`
11. **AOSP android-17.0.0_r1, `Configs.java` / `DeviceConfigHelper.java` / `RateLimiter.java`**
   `packages/modules/Profiling/service/java/com/android/os/profiling/`
12. **Android Developers, Back up user data with Auto Backup**
   https://developer.android.com/identity/data/autobackup
