---
title: ProfilingManager 系统触发式性能追踪
chapter: '8.10'
section: '8.10'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
last_verified: '2026-06-25'
last_verified_against: AOSP android-17.0.0_r1 (ProfilingTrigger.java, ProfilingManager.java,
  ProfilingService.java) + Task9 2026-06-25 deep-review items
confidence: medium
tags:
- responsiveness
- latency
- launch
related_chapters:
- '16.8'
- '26.12'
version_breakdown: 'API 35 (Android 15): ProfilingManager 手动请求能力; API 36 (Android
  16): addProfilingTriggers 系统触发式 profiling, APP_FULLY_DRAWN=1/ANR=2; extension 36.1:
  APP_REQUEST_RUNNING_TRACE=3/KILL_FORCE_STOP=4/KILL_RECENTS=5/KILL_TASK_MANAGER=6;
  API 37 (Android 17): OOM=7/ANOMALY=8/KILL_EXCESSIVE_CPU_USAGE=9/COLD_START=10/APP_COMPAT=11'
created_by: task2a-knowledge-gap
created_date: '2026-04-10'
deepseek_cn_review_state: done
gap_source: 研究素材
last_deepseek_cn_review_at: '2026-06-25'
last_task2b_lite_at: '2026-06-25'
last_task6_at: '2026-06-25T04:05:00+08:00'
last_task6_audit: '2026-06-25'
last_task6_review_log: logs/review/2026-06-24-09-review.md
last_task9_at: '2026-06-23T13:20:00+08:00'
last_task9_audit: '2026-06-24'
last_task9_autofix_at: '2026-06-23'
last_task9_review_log: logs/deep-review/2026-06-23-13-deep-review.md
path: https://developer.android.com/reference/android/os/ProfilingManager
reviewed_by: openclaw-task6
reviewed_date: '2026-06-25'
task6_result: pass-light-edit
task6_review_notes: '2026-06-25 Task6 revisiting复审(Task2B fix后回归): 禁用词扫描零命中(Task2B已修复)。否定-纠正结构1处在限额内。L1/L2通过,无B类大问题。task9_result=pass-tech-review,queue无pending,自动晋升finalized。'
task9_result: pass-tech-review
task9_review_date: '2026-06-25'
task9_review_notes: '2026-06-25 Task9 deep-review: 无 P0/P1 问题，P2 建议改进 3 处，已写入 suggestions.md。'
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-06-25'
task9_reviewer: openclaw-task9
task9_state: reviewed
tech_score: 3/5
verifier_pass: '2026-06-23T11:26:00+08:00'
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
pipeline_stage: ready-to-publish
last_task2b_at: '2026-06-25T00:53:48+08:00'
repaired_date: '2026-06-25'
repaired_by: openclaw-task2b
task2b_notes: '2026-06-25 Task2B main: AOSP source path corrected to frameworks/base;
  constant values annotated with AOSP tag; ANOMALY-ApplicationExitInfo linkage structured.
  2026-06-25 Task2B Lite: added version_breakdown to frontmatter for API 35/36/37
  boundary clarity; added related_chapters cross-reference to 16.8 (ApplicationExitInfo)
  and 26.12 (versioned diagnostics).'
---

# ProfilingManager 系统触发式性能追踪

冷启动慢、偶发 ANR 和一次性 OOM 常有同一个取证难点：工程师开始抓 trace 时，异常已经过去。`ProfilingManager` 允许应用预先注册系统事件。设备在满足触发条件并且还有采集配额时保存 profile，再把结果路径交给应用。

这项能力不承诺每次触发都有文件。后台 trace 只会按系统策略间歇运行，采集还受应用级、系统级和 trigger 自定义限流影响。应用需要同时处理成功结果、错误结果以及长时间没有结果的情况。

本文以 Android 17 / API 37 的 `android-17.0.0_r1` 为平台源码锚点。Android 17 增加了冷启动、Java OOM、异常行为、过量 CPU kill 和兼容性问题等 trigger；不同 trigger 可能返回 system trace、stack sampling、Java heap dump 或带 metadata 的容器。文件类型没有辨认清楚，后续工具选择就会错位。

<!-- outline-start -->
## 要点

### 🔹 ProfilingManager 的角色与源码位置
- `ProfilingManager` 本体在 Android 15 提供手动请求能力,system-triggered profiling 从 Android 16 才开始可用
- 公开 API 位于 `packages/modules/Profiling/framework/android/os/`
- 服务端实现位于 `packages/modules/Profiling/service/java/com/android/os/profiling/`

### 🔹 trigger → artifact → stop condition → result delivery
- `APP_FULLY_DRAWN`、`ANR`、`COLD_START`、`OOM`、`KILL_EXCESSIVE_CPU_USAGE` 返回的工件并不相同
- 结果统一通过 `registerForAllProfilingResults()` 的全局 listener 取回
- `ProfilingResult#getResultFilePath()` 是结果文件入口,`getTriggerType()` 用来区分触发器

### 🔹 Android 16、36.1、17 的版本分层
- API 36:`APP_FULLY_DRAWN=1`、`ANR=2`
- extension 36.1:`APP_REQUEST_RUNNING_TRACE=3`、`KILL_FORCE_STOP=4`、`KILL_RECENTS=5`、`KILL_TASK_MANAGER=6`,运行时还要做 Extension SDK gating
- API 37:`OOM=7`、`ANOMALY=8`、`KILL_EXCESSIVE_CPU_USAGE=9`、`COLD_START=10`、`APP_COMPAT=11`

### 🔹 冷启动、ANR、OOM 的使用方式
- 冷启动要分清 `APP_FULLY_DRAWN` 和 `COLD_START`
- ANR 结果是 running system trace snapshot
- OOM 结果是 Java heap dump,不是 LMK / lmkd 现场

### 🔹 工具中的观测入口
- `.perfetto-trace` 结果走 Perfetto UI
- Java heap dump 结果按 heap dump 工具链分析
- 每类结果都要先看 artifact,再决定分析工具

### 🔹 常见误区
- 不要把 `APP_FULLY_DRAWN` 写成 `COLD_START`
- 不要把 OOM 写成 LMK
- 不要把系统触发结果写成 request-scoped listener 可接收
<!-- outline-end -->

## 核心机制

### API 与 Mainline 模块的边界

Android 15 / API 35 引入 `ProfilingManager`，当时公开的是 `requestProfiling()` 等应用主动请求能力。Android 16 / API 36 增加 `addProfilingTriggers()`、`clearProfilingTriggers()` 和按类型移除 trigger 的接口，系统触发式采集由此进入公开 SDK。

这些类不在 `frameworks/base/core/java/android/os/`。Android 17 tag 中的准确位置如下：

- SDK 类：`packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`
- trigger 与结果模型：同目录下的 `ProfilingTrigger.java`、`ProfilingResult.java`
- 系统服务：`packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`
- Perfetto 配置：服务目录下的 `Configs.java`

Profiling 模块以 Mainline 组件交付，公开 API 仍属于 `android.os`。分析公开契约时看 SDK 类注释；解释 Android 17 的文件格式、redaction 或限流实现时，再看 `ProfilingService` 和 `Configs`。服务实现可以随模块更新，不能把每个内部字段都当作应用契约。

### running snapshot 与新采集会看到不同时间窗

多数 trigger 依赖系统事先运行的后台 system trace。系统按策略随机启动这类 trace，使用环形缓冲区保留触发前的一段历史。事件发生时，服务克隆正在运行的 session，执行 redaction，再把文件复制到应用私有目录。后台 trace 没有运行、配额不足或后处理失败时，注册过 trigger 也可能拿不到成功文件。

`TRIGGER_TYPE_COLD_START` 走另一条路径。系统在确认冷启动后尽早创建新的 profile，使用 discard buffer 保留开头数据；缓冲区满时丢弃后来的事件。它关注进程启动早期，running snapshot 关注触发前最近一段历史，两者的 buffer 策略不能互换解释。

应用只通过 `registerForAllProfilingResults(Executor, Consumer<ProfilingResult>)` 接收 system-triggered 结果。某次 `requestProfiling()` 携带的 request-scoped listener 收不到这些结果。采集完成时应用若不在运行，系统可以在应用下次启动并重新注册全局 listener 后补发通知。

### Android 17 trigger 对照表

下表的常量、触发条件和产物以 `android-17.0.0_r1` 的 `ProfilingTrigger.java` 为准：

| Trigger | 引入版本 | 值 | 触发条件 | 公开产物契约 |
|---|---:|---:|---|---|
| `APP_FULLY_DRAWN` | API 36 | `1` | 冷启动调用 `Activity.reportFullyDrawn()` 后 | running system trace snapshot |
| `ANR` | API 36 | `2` | 系统已经识别 ANR、尚未尝试终止应用时 | running system trace snapshot |
| `APP_REQUEST_RUNNING_TRACE` | 36.1 | `3` | 应用调用 `requestRunningSystemTrace()` | running system trace snapshot |
| `KILL_FORCE_STOP` | 36.1 | `4` | 用户在应用信息页点击“强行停止” | running system trace snapshot |
| `KILL_RECENTS` | 36.1 | `5` | 用户从最近任务中移除应用并触发相应 kill | running system trace snapshot |
| `KILL_TASK_MANAGER` | 36.1 | `6` | 用户在任务管理器停止应用 | running system trace snapshot |
| `OOM` | API 37 | `7` | 应用抛出 `OutOfMemoryError` | Java heap dump |
| `ANOMALY` | API 37 | `8` | 系统检测到应用异常行为 | 随异常类型变化，tag 提供分类 |
| `KILL_EXCESSIVE_CPU_USAGE` | API 37 | `9` | 系统因过量 CPU 使用终止应用，退出原因是 `REASON_EXCESSIVE_RESOURCE_USAGE` | running system trace snapshot |
| `COLD_START` | API 37 | `10` | `ApplicationStartInfo` 判定为 `START_TYPE_COLD` | 新启动的 system trace，同时采集 stack sampling |
| `APP_COMPAT` | API 37 | `11` | 系统发现未来 Android 版本将不再支持的应用行为 | 随兼容性问题变化，tag 提供分类 |

`TRIGGER_TYPE_NONE = 0` 只表示该 `ProfilingResult` 不是由 trigger 发起，不能传给 `ProfilingTrigger.Builder`。

### 生产接入要先处理错误结果

下面的 Kotlin 骨架面向 `compileSdk = 37`。它注册 API 36 的两个基础 trigger，并在 Android 17 上增加冷启动、OOM 和 anomaly；回调只做分类与任务入队，不在 executor 上同步上传大文件：

```kotlin
import android.content.Context
import android.os.Build
import android.os.ProfilingManager
import android.os.ProfilingResult
import android.os.ProfilingTrigger
import androidx.annotation.RequiresApi
import java.util.concurrent.Executor
import java.util.function.Consumer

@RequiresApi(36)
class TriggeredProfilingRegistration(
    context: Context,
    private val callbackExecutor: Executor,
    private val enqueueProfile: (
        triggerType: Int,
        tag: String?,
        resultFilePath: String
    ) -> Unit,
    private val reportError: (errorCode: Int, errorMessage: String?) -> Unit,
) {
    private val manager: ProfilingManager = requireNotNull(
        context.applicationContext.getSystemService(ProfilingManager::class.java)
    )

    private val resultListener = Consumer<ProfilingResult> { result ->
        val resultPath = result.resultFilePath
        if (result.errorCode == ProfilingResult.ERROR_NONE && resultPath != null) {
            enqueueProfile(result.triggerType, result.tag, resultPath)
        } else {
            reportError(result.errorCode, result.errorMessage)
        }
    }

    fun register() {
        val triggers = arrayListOf(
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN
            ).setRateLimitingPeriodHours(24).build(),
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_ANR
            ).setRateLimitingPeriodHours(24).build(),
        )

        if (Build.VERSION.SDK_INT >= 37) {
            triggers += ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_COLD_START
            ).setRateLimitingPeriodHours(24).build()
            triggers += ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_OOM
            ).setRateLimitingPeriodHours(24).build()
            triggers += ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_ANOMALY
            ).build()
        }

        manager.registerForAllProfilingResults(
            callbackExecutor,
            resultListener,
        )
        manager.addProfilingTriggers(triggers)
    }

    fun unregisterListener() {
        manager.unregisterForAllProfilingResults(resultListener)
    }
}
```

`getResultFilePath()` 在 `getErrorCode() != ERROR_NONE` 时按契约返回 `null`，所以不能先上传路径再检查错误码。全局 listener 与 executor 宜保持应用级生命周期；需要停止接收时，用同一个 `Consumer` 实例注销。`unregisterForAllProfilingResults()` 只移除 listener，已注册 trigger 要用 `clearProfilingTriggers()` 或 `removeProfilingTriggersByType()` 单独管理。

同一种 trigger 只能保留一个配置。再次注册会替换旧配置。`setRateLimitingPeriodHours(24)` 表示同类 trigger 的应用自定义最短间隔，系统仍可增加自己的限流或拒绝采集；设置为 `0` 只会取消这一层自定义间隔。

### 36.1 是 minor SDK release

Android 16 的 36.1 使用 full SDK version 表示。它不属于 `SdkExtensions.getExtensionVersion()` 管理的 B Extensions。只检查 `SDK_INT >= 36` 会在首个 Android 16 release 上误调用 36.1 API。

下面的代码展示 36.1 API 的运行时边界，并在请求 running trace 前注册对应 trigger：

```kotlin
if (
    Build.VERSION.SDK_INT >= 36 &&
    Build.VERSION.SDK_INT_FULL >= Build.VERSION_CODES_FULL.BAKLAVA_1
) {
    manager.addProfilingTriggers(
        listOf(
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE
            ).setRateLimitingPeriodHours(1).build()
        )
    )
    manager.requestRunningSystemTrace("checkout")
}
```

`requestRunningSystemTrace()` 只请求克隆当前后台 trace。没有运行中的 trace、未注册 `APP_REQUEST_RUNNING_TRACE` 或限流拒绝时，它不保证返回 profile。`addAllProfilingTriggers()` 同样从 36.1 可用；生产应用通常按诊断需求注册少量 trigger，避免收集无法消费的文件。

## 产物与分析路径

### `APP_FULLY_DRAWN` 与 `COLD_START` 的时间窗

`APP_FULLY_DRAWN` 在一次冷启动调用 `reportFullyDrawn()` 后克隆 running trace。它能覆盖多少启动历史，取决于后台 trace 当时是否运行以及环形缓冲区还保留了什么。

`COLD_START` 在系统判定 `ApplicationStartInfo.getStartType() == START_TYPE_COLD` 后尽早启动新采集。调用 `reportFullyDrawn()` 会停止采集；应用没有调用时，公开默认值是 5 秒。Android 17 服务端还为它设置 `KEY_COLLECT_STACK_SAMPLING = true` 和 discard fill policy，所以同一 profile 可同时检查调度时间线与采样调用栈，并优先保住启动早期事件。

这两种结果都不能代替应用自己的启动指标。trace 用来解释 TTID、TTFD 或业务 ready 指标为什么变慢，线上指标负责说明问题影响了多少用户。

### ANR 与过量 CPU kill

ANR trigger 在系统已经识别 ANR 后发生，返回触发前的 running trace snapshot。分析顺序可以从主线程 `thread_state` 开始，再追同步 Binder、锁 owner、I/O 和 CPU 饥饿。redaction 会移除其他应用信息，`system_server` 的完整上下文也可能不可见，不能期待它等同于本地抓取的全系统 trace。

`KILL_EXCESSIVE_CPU_USAGE` 在系统已经做出 kill 判断后触发。公开契约只给出 `ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 和 system trace snapshot，没有固定 CPU 百分比、持续时长或设备统一阈值。结果可能延迟交付，应用应把它与 `ActivityManager.getHistoricalProcessExitReasons()` 返回的退出记录一并保存，再按包、进程和相近时间做关联；不能假定列表第一项必然对应这份 profile。

### Java OOM、Memory Limiter 与 LMKD 是三条路径

`TRIGGER_TYPE_OOM` 针对应用抛出的 `OutOfMemoryError`，产物是 Perfetto Java heap dump。应用若安装了自定义 `Thread.UncaughtExceptionHandler`，必须继续调用默认 handler，否则 OOM trigger 无法工作。这个文件是 Perfetto profile，不应直接当作传统 `.hprof` 交给 MAT。

Android 17 Memory Limiter 使用 cgroup v2 的 `memory` controller 约束应用进程。超过设备配置的内存边界时，系统可以在执行约束动作前触发 `TRIGGER_TYPE_ANOMALY`。该场景与 Java 堆分配抛 OOM 不同，也和系统内存压力下的 LMKD 选杀路径不同。

Android 17 公开文档给出的两个 anomaly 示例是过量内存与 Binder spam：前者提供 heap dump，后者提供 stack sampling。`ProfilingResult.getTag()` 携带异常分类。`android-17.0.0_r1` 的 `ProfilingService` 对 Memory Limiter 路径使用 `memory_limit` tag，并在 `attachMetadataIfNeeded()` 中把 heap dump 与 `perfetto_metadata.json` 封装成 `-metadata.zip`。这是当前 tag 的实现细节，应用不应只凭 `.perfetto-java-heap-dump` 后缀分流 ANOMALY。

收到 anomaly 或 app-compat 结果时，建议按以下字段保存索引：

1. `getTriggerType()`：区分 anomaly 与 app-compat
2. `getTag()`：记录系统提供的具体分类
3. `getErrorCode()` 与 `getErrorMessage()`：保留失败原因
4. `getResultFilePath()`：成功后交给文件识别与上传任务
5. 应用版本、进程名、设备 build fingerprint 和本地接收时间

同一 UID 下有多个包注册 ANOMALY 时，公开 API 明确允许某些异常不返回 artifact。多进程应用也不能据此推导“每个进程都会得到一份文件”。

### 工具选择

| 产物 | 推荐入口 | 要回答的问题 |
|---|---|---|
| `.perfetto-trace` | Perfetto UI、`trace_processor_shell` | 主线程为何没有运行、Binder 或锁在等谁、启动阶段卡在哪一段 |
| system trace 中的 stack sampling | Perfetto UI flamegraph / SQL | CPU 时间集中在哪些调用栈 |
| `.perfetto-java-heap-dump` | Perfetto UI Heap Dump Explorer / PerfettoSQL | 哪些类型实例多、谁保留了大对象、GC root 路径是什么 |
| `-metadata.zip` | 支持 Perfetto metadata 的工具，必要时检查容器内 profile 与 JSON | anomaly 类型、标注区域与对应 heap/stack 证据 |

下面的查询用于在 Java heap dump 已被 Perfetto 正确解析后找出实例数较高的类型：

```sql
INCLUDE PERFETTO MODULE android.memory.heap_graph.heap_graph_class_aggregation;

SELECT *
FROM android_heap_graph_class_aggregation
WHERE obj_count >= 2
ORDER BY obj_count DESC
LIMIT 100;
```

实例数高只是一条线索。还要结合 total size、retained size、dominator 与到 GC root 的最短路径，确认它是合理缓存、批量业务数据还是泄漏。对 Memory Limiter anomaly，还要检查 native、graphics、swap 等 Java heap dump 覆盖不到的内存，因为 cgroup 约束面对的是进程内存，不只 Java heap。

## 本地验证

### 强制后台 trace 并保留临时文件

Android 16 及以上可指定一个测试包，让系统持续运行后台 trace，并让该包绕过系统 trigger rate limiter。`delete_temporary_results.disabled` 会保留 redacted 和适用场景下的 unredacted 结果；`rate_limiter.disabled` 便于同时测试应用主动请求。下面的命令用于一次本地验证：

```bash
adb shell device_config put profiling_testing \
  system_triggered_profiling.testing_package_name com.example.app
adb shell device_config put profiling_testing \
  delete_temporary_results.disabled true
adb shell device_config put profiling_testing \
  rate_limiter.disabled true

adb shell am force-stop com.example.app
adb shell am start -W \
  -n com.example.app/.MainActivity

adb logcat -d -s ProfilingService
```

应用需要在启动完成点调用 `Activity.reportFullyDrawn()`，上面的冷启动才能触发 `APP_FULLY_DRAWN`。测试包模式绕过系统限流，不会绕过 `ProfilingTrigger.Builder` 设置的应用自定义间隔；调试构建可临时用 `0` 重新注册。logcat 会给出保留文件的位置，业务代码仍应以 `ProfilingResult.getResultFilePath()` 为准。

测试结束后要恢复三个开关，避免后台 trace 持续耗电并占用磁盘：

```bash
adb shell device_config delete profiling_testing \
  system_triggered_profiling.testing_package_name
adb shell device_config put profiling_testing \
  delete_temporary_results.disabled false
adb shell device_config put profiling_testing \
  rate_limiter.disabled false
```

Android 15 使用旧的 `delete_unredacted_trace.disabled` 调试项，只保留适用场景下的 unredacted 文件；system-triggered API 尚未引入，所以这条历史边界只用于验证应用主动请求。

### redaction 的诊断边界

交付给应用的 profile 会经过隐私处理，只保留请求应用相关信息。依赖其他应用、完整 `system_server` 或全局进程关系的 PerfettoSQL 模块可能没有足够数据。查询返回空表时，要先确认 redaction 是否删除了所需轨道，再判断业务事件是否缺失。

本地保留的 unredacted 文件只用于受控设备排查。heap dump、stack sampling 和 trace 仍可能包含类名、业务 tag、线程名与用户数据，不应直接上传到通用日志系统。线上采集需要明确保留时长、访问权限、加密与删除策略。

## 版本演进

| 平台 | 公开能力 | 运行时判断 |
|---|---|---|
| Android 15 / API 35 | `ProfilingManager` 主动请求、全局结果 listener | `SDK_INT >= 35` |
| Android 16 / API 36 | `addProfilingTriggers()`、`APP_FULLY_DRAWN=1`、`ANR=2` | `SDK_INT >= 36` |
| Android 16 minor release 1 / 36.1 | `APP_REQUEST_RUNNING_TRACE=3`、三个用户终止类 trigger、`addAllProfilingTriggers()` | `SDK_INT_FULL >= VERSION_CODES_FULL.BAKLAVA_1` |
| Android 17 / API 37 | `OOM=7`、`ANOMALY=8`、`KILL_EXCESSIVE_CPU_USAGE=9`、`COLD_START=10`、`APP_COMPAT=11` | `SDK_INT >= 37` |

36.1 的判断使用 `SDK_INT_FULL`；SDK Extensions 适用于可通过 Mainline 向既有平台 SDK 增加的另一套 API 版本体系。两者名字接近，运行时接口不同。

## 源码锚点与内核边界

本文的平台结论锚定 `android-17.0.0_r1`。`ProfilingTrigger.java` 定义公开常量与 artifact 契约，`ProfilingManager.java` 定义 listener 和注册行为，`ProfilingService.java` 负责后台 trace、交付、redaction、trigger 限流与 Android 17 anomaly metadata。

Memory Limiter 涉及内核时，以 `android17-6.18-2026-06_r6` 为本知识库内核锚点。它要求设备具备 cgroup v2 与 `memory` controller；OEM 仍可决定是否启用及如何配置 `/vendor/etc/memory-limiter-config.xml`。ProfilingManager 是取证接口，不能改变内存限制或 LMKD 策略。

## 常见误区

### 把 `APP_FULLY_DRAWN` 当作完整冷启动录制

它克隆触发时正在运行的后台 trace，开头可能早于或晚于进程启动。需要从冷启动早期新建采集时，Android 17 提供 `COLD_START`。

### 用 `SdkExtensions` 判断 36.1

36.1 是 minor SDK release。应使用 `SDK_INT_FULL` 与 `VERSION_CODES_FULL.BAKLAVA_1`，并用 `SDK_INT >= 36` 保护对这些字段的访问。

### 成功前直接读取文件路径

失败结果的路径为 `null`。先检查 `ERROR_NONE`，再保存 trigger、tag 和路径；上传任务还要能处理文件已被清理、空间不足和重复交付。

### 把 Java heap dump 当作 MAT 可直接读取的 HPROF

ProfilingManager 通过 Perfetto 的 `android.java_hprof` data source 生成 profile。使用 Perfetto UI Heap Dump Explorer 或 PerfettoSQL；若某工具只接受标准 HPROF，需要经过该工具明确支持的转换流程。

### 为 ANR、CPU 或 anomaly 编造统一阈值

公开 API 没有承诺固定 CPU 百分比、ANR 预警时长或 anomaly 阈值。设备配置和 Mainline 更新都可能改变内部策略，应用侧只依赖 trigger 条件、结果字段与公开 artifact 契约。

## 参考资料

- [ProfilingManager API](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger API](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [ProfilingResult API](https://developer.android.com/reference/android/os/ProfilingResult)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Profiling limitations and rate limiting](https://developer.android.com/topic/performance/tracing/profiling-manager/will-my-profile-always-be-collected)
- [Debug commands for local profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/debug-mode)
- [Query ProfilingManager profiles](https://developer.android.com/topic/performance/tracing/profiling-manager/querying-profiles)
- [Build.VERSION.SDK_INT_FULL](https://developer.android.com/reference/android/os/Build.VERSION#SDK_INT_FULL)
- [Build.VERSION_CODES_FULL](https://developer.android.com/reference/android/os/Build.VERSION_CODES_FULL)
- [Android 17 Memory Limiter](https://source.android.com/docs/core/perf/memory-limiter)
- [Android 17 `ProfilingManager.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [Android 17 `ProfilingTrigger.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [Android 17 `ProfilingResult.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingResult.java)
- [Android 17 `ProfilingService.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java)
- [Android 17 `Configs.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java)
- [Android 17 `PerfettoMetadata.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/util/src/com/android/profiling/utils/PerfettoMetadata.java)

## 相关章节

- [应用启动分析](02-app-launch.md)
- [ANR 分析方法](../ch09-anr/03-anr-analysis.md)
- [LMKD 与内存压力](../../part1-fundamentals/ch04-memory/04-lmk.md)
- [Perfetto 查看与基础分析](../../part3-tools/ch13-perfetto/03-perfetto-view.md)
- [ApplicationExitInfo](../../part5-app/ch26-observability/09-application-exit-info.md)
