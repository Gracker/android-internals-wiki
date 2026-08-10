---

title: "内存监控与线上治理"
chapter: "23.7"
section: "23.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers Debug/ActivityManager/ComponentCallbacks2 + Clippings/Android 性能优化"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
- type: official
  path: https://developer.android.com/reference/android/os/Debug.MemoryInfo
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo
- type: official
  path: https://developer.android.com/reference/android/content/ComponentCallbacks2
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int[])
- type: official
  path: https://developer.android.com/studio/profile/chart-glossary/process-memory
- type: official
  path: https://developer.android.com/topic/performance/memory
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture
- type: official
  path: https://developer.android.com/studio/profile/capture-heap-dump
- type: aosp
  path: frameworks/base/core/java/android/os/Debug.java @ android-16.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityManager.java @ android-16.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/ComponentCallbacks2.java @ android-16.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-16.0.0_r1
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]'
tags: [memory-monitoring, pss, rss, heap-dump, oom-alert]
related_chapters: ["23.1", "20.5", "26.3", "10.1", "19.3"]
pipeline_stage: ready-to-publish
task9_state: reviewed
task2b_state: fixed
task9_result: auto-fixed
last_task9_at: "2026-06-08T10:32:00+08:00"
task9_reviewed_date: "2026-06-08"
task9_reviewed_by: "openclaw-task9"
last_task9_review_log: "logs/deep-review/2026-06-08-10-audit.md"
reviewed_date: "2026-05-14"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-14"
task6_reviewed_by: "openclaw-task6"
task6_review_notes: "2026-05-14 task6 review: L1/L2 轻修 3 处（第二人称收束、API 35+ 边界标注、结尾措辞）；四层质检通过，无新增 L3/L4 回炉项。Task9 已 pass-tech-review 且 queue 无 pending，自动晋升 finalized。"
auto_finalized_by: openclaw-task6
auto_finalized_date: "2026-05-14"
last_task9_audit: "2026-06-08"
last_task9_autofix_at: "2026-06-08"
task9_review_notes: "2026-05-14 Task9 04: pass-tech-review。P0/P1 0；P2 1：Debug.getRss() API 35+ 边界，后续已由 Task6 标注并自动晋升 finalized。 | 2026-06-08 Task9 idle audit: auto-fixed。P0 0 / P1 1 / P2 1；补充 Android 14/API 34 起 TRIM_MEMORY_RUNNING_* 等旧低内存等级不再投递、API 35 废弃的版本边界；Android 17/API 37 ProfilingTrigger OOM/anomaly 属于本节未来扩展 P2，未写入正文。"
task6_state: reviewed
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_audit: "2026-06-08"
deepseek_cn_review_state: needs-structure-rework
last_deepseek_cn_review_at: 2026-06-12
---

# 内存监控与线上治理

> **版本基线**
>
> 平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点；读取 `/proc` 指标时，内核侧以 `android17-6.18-2026-06_r6` 为基线。历史版本只用于说明 API 与行为边界，最高版本为 Android 17。

## 线上监控要回答什么

本地 Memory Profiler 适合解释一次复现，线上系统面对的是分散在版本、设备、进程和业务场景中的样本。它至少要回答四个问题：

- 哪一类内存在增长：Java Heap、native allocator、图形、文件映射、线程栈，还是多个进程的合计。
- 增长是短时峰值、可回落缓存，还是跨页面、跨会话持续积累。
- 变化是否集中在某个版本、设备档位、ABI、进程或用户路径。
- 需要保留轻量指标、退出记录、Java heap dump，还是 native heap profile。

只上报一个“内存占用”无法区分这些问题。PSS、RSS、Java Heap 和 Native Heap 的统计对象不同，任何一项都不能单独代表应用的全部内存。多进程应用还要带进程名；把所有进程混成一个分布，会掩盖主进程回归或独立任务进程的峰值。

Java 泄漏引用链见 23.1 节，Native 分配诊断见 23.3 节，Java Heap 预算见 23.4 节，OOM 分类见 20.5 节。这里聚焦生产环境中的指标、判断、降级和证据采集。

## 内存指标采集：先统一口径

### PSS、RSS、Java Heap 与 Native Heap

| 指标 | Android 入口 | 适合回答 | 不能据此断言 |
| --- | --- | --- | --- |
| PSS | `ActivityManager.getProcessMemoryInfo()`、`Debug.getPss()`、`Debug.MemoryInfo.totalPss` | 进程私有页加共享页按比例分摊后的系统内存占用 | 某个 Java 对象或 native 调用栈造成了增长 |
| RSS | API 35+ 的 `Debug.getRss()`；旧版本可读本进程 `/proc/self/status` 的 `VmRSS` | 当前驻留页总量及其变化 | RSS 全部由应用独占；共享页会被每个进程完整计入 |
| Java Heap | `Runtime.totalMemory() - Runtime.freeMemory()`、`Runtime.maxMemory()` | ART heap 已用空间的近似值与当前上限 | 已用值全是可达对象；尚未 GC 的不可达对象也可能在其中 |
| native allocator | `Debug.getNativeHeapAllocatedSize()` | 当前进程 native heap allocator 已分配的字节数 | 所有 Native、Graphics、mmap、线程栈都包含在该值中 |
| 分类页 | `Debug.MemoryInfo.dalvikPss`、`nativePss`、`otherPss` 及 summary stats | PSS 按映射类别的组成 | `nativePss` 等于 `malloc` 活跃分配；两者统计路径不同 |
| 设备水位 | `ActivityManager.getMemoryInfo()` | `availMem`、`threshold`、`lowMemory` 所描述的设备背景 | 当前进程离 Java OOM 还有多少字节 |

`Debug.MemoryInfo` 的 PSS 字段以 kB 表示；`Runtime` 和 `Debug.getNativeHeapAllocatedSize()` 返回字节，入库前必须保留单位。`Debug.getMemoryInfo()` 直接读取当前进程，但 Android 17 源码注释说明它可能无法取得 graphics 等受保护分配；需要更完整的进程分类时，应使用 `ActivityManager.getProcessMemoryInfo()`。

Android 10（API 29）起，普通应用通过 `getProcessMemoryInfo()` 只能取得调用方 UID 下的进程信息，其他 PID 的条目为零；平台还会限制采样频率，调用过密可能收到上一次结果。采样请求时间不等于底层数据的新鲜时间，监控系统不能用高频调用制造虚假的高分辨率曲线。

Android 17 的 `Debug.getRss()` 仍是当前进程 API。AOSP JNI 路径读取 `StatusVmRSS()`，并在 memtrack 可用时加入 graphics、GL 和 other；直接读取 `/proc/self/status` 只能得到原始 `VmRSS`。因此，API 35 前后的 RSS 来源需要单独标记，不能无说明地拼进同一条基线。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/os/Debug.java`, `frameworks/base/core/jni/android_os_Debug.cpp`, `frameworks/base/core/java/android/app/ActivityManager.java`]

### 一个可审计的采样骨架

下面的代码采集当前进程的低频快照。调用方需要在非主线程执行，并由远程策略决定采样时机；代码没有假设固定周期或固定阈值。

```kotlin
import android.app.ActivityManager
import android.app.Application
import android.content.Context
import android.os.Build
import android.os.Debug
import android.os.Process
import android.os.SystemClock
import java.io.File

enum class RssSource {
    DEBUG_API_WITH_MEMTRACK,
    PROC_STATUS
}

data class ProcessMemorySample(
    val elapsedRealtimeMs: Long,
    val pid: Int,
    val processName: String,
    val pssKb: Int?,
    val rssKb: Long?,
    val rssSource: RssSource,
    val javaHeapUsedBytes: Long,
    val javaHeapLimitBytes: Long,
    val nativeAllocatorBytes: Long,
    val systemAvailBytes: Long,
    val systemThresholdBytes: Long,
    val systemLowMemory: Boolean
)

private fun readVmRssKb(): Long? = runCatching {
    File("/proc/self/status").useLines { lines ->
        lines.firstOrNull { it.startsWith("VmRSS:") }
            ?.substringAfter(':')
            ?.trim()
            ?.split(Regex("\\s+"))
            ?.firstOrNull()
            ?.toLongOrNull()
    }
}.getOrNull()

fun collectProcessMemorySample(context: Context): ProcessMemorySample {
    val am = context.getSystemService(ActivityManager::class.java)
    val processInfo = am.getProcessMemoryInfo(intArrayOf(Process.myPid()))
        .firstOrNull()
    val runtime = Runtime.getRuntime()
    val systemInfo = ActivityManager.MemoryInfo().also(am::getMemoryInfo)

    val debugRssKb = if (Build.VERSION.SDK_INT >= 35) {
        Debug.getRss().takeIf { it > 0L }
    } else {
        null
    }
    val rssKb = debugRssKb ?: readVmRssKb()

    return ProcessMemorySample(
        elapsedRealtimeMs = SystemClock.elapsedRealtime(),
        pid = Process.myPid(),
        processName = Application.getProcessName(),
        pssKb = processInfo?.totalPss?.takeIf { it > 0 },
        rssKb = rssKb,
        rssSource = if (debugRssKb != null) {
            RssSource.DEBUG_API_WITH_MEMTRACK
        } else {
            RssSource.PROC_STATUS
        },
        javaHeapUsedBytes = runtime.totalMemory() - runtime.freeMemory(),
        javaHeapLimitBytes = runtime.maxMemory(),
        nativeAllocatorBytes = Debug.getNativeHeapAllocatedSize(),
        systemAvailBytes = systemInfo.availMem,
        systemThresholdBytes = systemInfo.threshold,
        systemLowMemory = systemInfo.lowMemory
    )
}
```

`pssKb == null` 或 `rssKb == null` 表示本次未取得有效值，不能按零内存上报。`elapsedRealtimeMs` 适合计算当前进程内的时间差；跨进程、跨重启聚合时还要带服务端接收时间。事件包还应包含 App 版本、Android 版本、ABI、设备 RAM 档位、前后台状态、页面类别、采样原因、采样策略版本和每个指标的来源。

### 采样频率由成本和问题决定

指标分为三类：

- 本进程计数：Java Heap 和 native allocator 读取较直接，可以在关键业务边界采集。
- 映射统计：PSS 需要读取进程映射并可能经过系统服务，适合低频、场景结束或异常触发。
- 系统产物：heap dump、heap profile 和 Perfetto profile 开销与敏感度高，只能由严格条件触发。

采样任务自身也要测量执行时间、分配量、I/O 和上报量。若探针在启动、滚动或渲染关键路径执行，采集行为可能改变被观察对象。官方也不建议持续轮询 `ActivityManager.getMemoryInfo()`。每轮发布都要保留“未采到、被限流、权限不足、文件失败”等状态，不能只统计成功样本。

## 内存水位线与告警策略

### 不使用跨设备固定百分比

Java heap limit、设备 RAM、页面资源、ABI、WebView 版本和厂商内存策略都会改变正常分布。一个跨设备固定比例容易同时产生漏报与误报。线上阈值应来自同类样本：

- 版本：当前灰度版本对比上一稳定版本。
- 设备：按 RAM 档位、low-RAM 标记、ABI 和形态分组。
- 进程：主进程、独立任务进程、推送进程、WebView 宿主分别统计。
- 场景：冷启动稳定点、页面停留、任务峰值、页面退出后的回落、后台驻留分别统计。
- 状态：前台可见、前台服务、后台和 cached 状态不能共用一条阈值。

基线至少要保留分布、样本数和缺失率。均值会掩盖长尾；分位数能描述尾部，但样本不足、设备构成变化或场景口径变化时，分位数也不能直接用于发布判断。

### 一条告警需要趋势、恢复能力和上下文

| 观察 | 需要组合的信号 | 更可能的方向 |
| --- | --- | --- |
| Java Heap 接近上限 | 使用比例、分配/回收趋势、页面退出后的回落 | 无界缓存、对象泄漏、批量分配过大 |
| RSS/PSS 上涨而 Java Heap 平稳 | native allocator、Graphics、线程数、FD、mmap 场景 | Native、图形、线程栈或文件映射 |
| native allocator 上涨 | `nativeAllocatorBytes` 与 `nativePss`、RSS 同向性 | malloc 路径增长；仍需 heap profile 或调用栈确认 |
| PSS 高但 RSS 变化不同 | 共享页比例、进程数量、WebView renderer | 共享映射或进程结构变化 |
| `lowMemory=true` | `availMem`、`threshold`、进程状态、设备档位 | 设备整体压力，不等同于当前进程泄漏 |
| 资源释放后不回落 | 相同场景的多次采样、GC 与生命周期边界 | 持有关系、allocator 保留或映射未释放 |

下面的分类器只处理 Java Heap 连续高位。阈值和最少样本数必须由发布策略传入，不能把示例值写死在客户端。

```kotlin
data class HeapPressurePolicy(
    val warningFraction: Double,
    val captureFraction: Double,
    val minimumSamples: Int
) {
    init {
        require(warningFraction in 0.0..1.0)
        require(captureFraction in warningFraction..1.0)
        require(minimumSamples > 0)
    }
}

enum class HeapPressure {
    NORMAL,
    REDUCE_REBUILDABLE_RESOURCES,
    CAPTURE_CANDIDATE
}

fun classifyHeapPressure(
    samples: List<ProcessMemorySample>,
    policy: HeapPressurePolicy
): HeapPressure {
    val recent = samples.takeLast(policy.minimumSamples)
    if (recent.size < policy.minimumSamples) return HeapPressure.NORMAL
    if (recent.any { it.javaHeapLimitBytes <= 0L }) return HeapPressure.NORMAL

    val fractions = recent.map {
        it.javaHeapUsedBytes.toDouble() / it.javaHeapLimitBytes
    }
    return when {
        fractions.all { it >= policy.captureFraction } ->
            HeapPressure.CAPTURE_CANDIDATE
        fractions.all { it >= policy.warningFraction } ->
            HeapPressure.REDUCE_REBUILDABLE_RESOURCES
        else -> HeapPressure.NORMAL
    }
}
```

这个结果只是一个候选信号。进入 `CAPTURE_CANDIDATE` 前还要检查前后台状态、用户交互、磁盘、电量、近期采集配额和隐私策略；进入资源收缩后要再采一次轻量指标，记录释放动作是否有效。

### 告警事件要能指导排查

建议把事件分开，而非统一命名为“OOM warning”：

| 事件 | 判定重点 | 必要字段 |
| --- | --- | --- |
| `memory_baseline_regression` | 同一分组相对稳定版本的分布变化 | 基线版本、当前版本、分组键、分位数、样本数、缺失率 |
| `java_heap_pressure` | Java Heap 连续高位与回落失败 | used/max、GC 统计、页面类别、缓存规模、执行动作 |
| `native_or_mapping_growth` | RSS/PSS 上涨且 Java Heap 平稳 | native allocator、分类 PSS、线程、FD、任务类型 |
| `system_memory_pressure` | 设备低内存背景与应用状态 | availMem、threshold、lowMemory、进程重要性 |
| `profile_requested` | 满足证据采集条件 | 触发规则、配额、设备状态、请求类型 |
| `profile_result` | 系统返回成功或错误 | result type、错误码、文件大小、策略版本 |
| `previous_memory_exit` | 重启后发现 LMK 或 Memory Limiter | exit reason、description marker、上次采样 PSS/RSS |

事件里应保存页面类别或业务阶段，不要默认上传完整 URL、搜索词、对象字符串或用户标识。监控维度越细，越需要在客户端先做枚举化和最小化。

## OOM 预警与主动回收

### 能安全释放的只有业务可控资源

预警阶段可以缩小图片缓存、停止预取、取消尚未开始的批处理、减少播放器预缓冲、关闭闲置 WebView、释放页面级对象并降低后续输入规格。流、游标、文件描述符、`ParcelFileDescriptor`、`SharedMemory` 映射和 native handle 要按所有权关闭。

不要把 `System.gc()` 当成常规回收接口。GC 只能处理不可达对象，无法释放仍被缓存、单例、JNI global reference 或活跃组件持有的数据；显式 GC 还可能增加停顿。也不要在全局捕获 `OutOfMemoryError` 后继续运行：OOM 发生时，错误处理路径本身可能无法分配对象，进程状态也可能不再满足业务不变量。只有边界清楚的单次分配可以设计局部降级，例如图片解码失败后改用更小规格。

Android 17 上，`onTrimMemory()` 仍应聚焦 `TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND`，用于表示 UI 隐藏或进程进入后台 LRU。从 Android 14（API 34）起，其余旧内存压力等级不再投递，并在 Android 15（API 35）废弃。设备压力使用 `ActivityManager.MemoryInfo` 观察；Android 17 App Memory Limits 的预先取证使用 `TRIGGER_TYPE_ANOMALY`，退出后再读 `ApplicationExitInfo`。

### 重启后核对退出原因

Android 11（API 30）起，`getHistoricalProcessExitReasons()` 可以读取调用方 UID 最近的退出记录。下面的代码只挑出 LMK 和 `android-17.0.0_r1` 所定义的 Memory Limiter 记录。

```kotlin
import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import android.os.Build

enum class MemoryExitKind {
    LOW_MEMORY_KILL,
    ANDROID_17_MEMORY_LIMITER
}

data class MemoryExitRecord(
    val kind: MemoryExitKind,
    val timestampMs: Long,
    val processName: String,
    val lastSampledPssKb: Long?,
    val lastSampledRssKb: Long?
)

fun readRecentMemoryExits(
    context: Context,
    maxRecords: Int
): List<MemoryExitRecord> {
    require(maxRecords > 0)
    if (Build.VERSION.SDK_INT < 30) return emptyList()

    val am = context.getSystemService(ActivityManager::class.java)
    return am.getHistoricalProcessExitReasons(
        context.packageName,
        0,
        maxRecords
    ).mapNotNull { exit ->
        val kind = when {
            exit.reason == ApplicationExitInfo.REASON_LOW_MEMORY ->
                MemoryExitKind.LOW_MEMORY_KILL
            Build.VERSION.SDK_INT >= 37 &&
                exit.reason == ApplicationExitInfo.REASON_OTHER &&
                exit.description?.contains("MemoryLimiter:AnonSwap") == true ->
                MemoryExitKind.ANDROID_17_MEMORY_LIMITER
            else -> null
        } ?: return@mapNotNull null

        MemoryExitRecord(
            kind = kind,
            timestampMs = exit.timestamp,
            processName = exit.processName,
            lastSampledPssKb = exit.pss.takeIf { it > 0L },
            lastSampledRssKb = exit.rss.takeIf { it > 0L }
        )
    }
}
```

`getPss()` 和 `getRss()` 是系统上一次采样值，可能为零，也不是进程死亡前一刻的精确内存。`getDescription()` 的一般格式没有稳定保证；这里匹配的 `MemoryLimiter:AnonSwap` 是 Android 17 r1 行为文档明确给出的标记，不应扩展成对其他 description 文本的解析。23.9 节会继续说明 Memory Limiter 的设备范围和测试命令。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/app/ApplicationExitInfo.java`]

## 内存快照线上采集

### 先按问题选择产物

| 产物 | 适用问题 | 主要限制 |
| --- | --- | --- |
| 轻量摘要 | 全量趋势、版本回归、采集前筛选 | 只能指出方向，不能提供对象引用链 |
| Java heap dump | Java/Kotlin 对象数量、持有关系、泄漏 | 只覆盖 Java Heap；生成与处理会消耗内存、CPU、I/O |
| heap profile | Java 或 native 分配热点与调用栈 | 采样结果需要结合场景解释，不等于存活对象图 |
| Perfetto system trace | GC、调度、内存计数与业务时序 | 不替代对象级 heap dump |
| `ApplicationExitInfo` | LMK、Memory Limiter 及其他退出后的证据 | 记录有限；PSS/RSS 是上次采样值 |

`Debug.dumpHprofData()` 可以把当前进程 Java heap 写入指定文件。Android 17 `Debug.java` 的注释指出该操作可能触发 GC，并可能抛出 `UnsupportedOperationException` 或 `IOException`。它适合本地、内部构建或受控诊断，不应在内存已经很紧张时由普通线上规则直接调用。

`ActivityManager.setWatchHeapLimit()` 也不是生产监控接口。Android 17 源码和 API 注释明确要求调用进程为 debuggable，或设备为 userdebug/eng；它适合开发阶段验证 PSS 阈值与 heap dump 流程。

Android 15（API 35）起，`ProfilingManager` 支持 app-driven Java heap dump、heap profile、stack sampling 和 system trace，并有系统限流。官方 Jetpack wrapper 提供 `JavaHeapDumpRequestBuilder` 与 `HeapProfileRequestBuilder`；请求不保证执行，结果和错误都通过 `ProfilingResult` 返回。

### Android 17 的 OOM 与 anomaly trigger

Android 17（API 37）增加 `TRIGGER_TYPE_OOM` 和 `TRIGGER_TYPE_ANOMALY`：

- OOM trigger 在应用出现 `OutOfMemoryError` 时提供 Java heap dump。若应用安装了自定义 `UncaughtExceptionHandler`，应保存安装前的默认 handler，并在自定义处理结束后转交给它；未调用默认 handler 时，该 trigger 无法工作。
- Anomaly trigger 在系统识别异常资源行为时触发，产物类型取决于异常。Android 17 App Memory Limits 命中时，系统可以在执行限制前提供 Java heap dump。

下面的注册函数同时监听两种内存 trigger。它应在要监控的进程启动后注册一次，并保留返回的 listener，供不再需要时调用 `unregisterForAllProfilingResults()`。

```kotlin
import android.content.Context
import android.os.ProfilingManager
import android.os.ProfilingResult
import android.os.ProfilingTrigger
import androidx.annotation.RequiresApi
import java.util.concurrent.Executor
import java.util.function.Consumer

@RequiresApi(37)
fun registerMemoryProfilingTriggers(
    context: Context,
    callbackExecutor: Executor,
    onArtifact: (ProfilingResult) -> Unit,
    onError: (errorCode: Int, errorMessage: String?) -> Unit
): Consumer<ProfilingResult> {
    val manager = context.getSystemService(ProfilingManager::class.java)
    val listener = Consumer<ProfilingResult> { result ->
        if (result.errorCode == ProfilingResult.ERROR_NONE) {
            onArtifact(result)
        } else {
            onError(result.errorCode, result.errorMessage)
        }
    }

    manager.registerForAllProfilingResults(callbackExecutor, listener)
    manager.addProfilingTriggers(
        listOf(
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_OOM
            ).build(),
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_ANOMALY
            ).build()
        )
    )
    return listener
}
```

系统 trigger 受设备采样与系统限流影响，不保证每次事件都有产物。trigger 结果只能通过全局 listener 接收；如果采集时进程已经退出，系统会在应用再次启动并注册 listener 后尝试交付。文件位置必须使用 `ProfilingResult.getResultFilePath()`，不能依赖内部目录结构。应用还可以用 `ProfilingTrigger.Builder.setRateLimitingPeriodHours()` 添加自己的冷却时间，但策略值应由团队的采样配额和隐私规则决定。

[源码锚点: AOSP `android-17.0.0_r1`, `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`, `ProfilingTrigger.java`]

### 产物治理比触发代码更重要

Java heap dump 可能包含对象字符串、用户输入、请求响应、缓存键、文件路径和业务标识。它不能因为位于应用私有目录就被视为已脱敏。上线前需要完成：

- 采集资格：版本、进程、场景、设备状态、磁盘和配额均满足策略。
- 最小化：能用指标或摘要定位时不采完整 dump；Native 问题不采 Java dump。
- 安全传输：文件在端侧、传输中和服务端均按敏感诊断数据保护。
- 访问控制：限制可查询人员、记录访问审计、设置保留期限并支持删除。
- 用户与合规：遵循产品隐私说明、用户选择、地区法规和商店政策。
- 资源控制：远程关闭、失败退避、每设备与每版本配额、上传网络条件。
- 可分析性：保留构建符号、混淆映射、版本、进程、触发规则和场景标签。

收到文件路径后，不要在 callback 中直接做压缩和网络上传。callback 只登记结果与错误，后续任务再核对文件、策略和设备条件。分析完成后要能从问题签名回查对应版本与样本分组，但不需要把原始用户路径写进文件名。

## 发布门禁与线上复盘

发布门禁应同时看分布和失败率：

- 主进程与各独立进程的 PSS/RSS 分布是否相对稳定版本回归。
- Java Heap 峰值、页面退出后的回落和长会话斜率是否改变。
- Native allocator、Graphics、线程与 FD 是否出现同向增长。
- Android Vitals 的 user-perceived LMK、Java OOM 与 native crash 是否变化。
- `ApplicationExitInfo` 中 LMK、Android 17 Memory Limiter 与其他退出是否集中在同一分组。
- Profiling 请求成功率、限流率、无产物率和文件处理失败率是否符合预期。

灰度扩大前要核对样本数、设备构成和场景覆盖。发现回归时，先缩小到版本、进程、设备与场景，再决定需要 Java heap dump、heap profile 还是 Perfetto。没有证据表明 Java 对象增长时，不要因为“内存高”就批量采 Hprof。

## 小结

线上内存治理从口径开始：PSS 表示共享页按比例分摊后的占用，RSS 表示驻留页总量，Java Heap 和 native allocator 只覆盖各自的分配域，设备 `MemoryInfo` 提供全局背景。所有指标都要带单位、来源、进程、场景和策略版本。

告警要观察同类样本的趋势与回落能力，再选择释放可重建资源、记录退出原因或申请系统 profile。Android 17 的 OOM/anomaly trigger 为难复现问题提供了系统产物，但仍受限流与采样约束。heap dump 是高成本且敏感的诊断数据，采集、传输、访问和删除必须作为同一项工程能力设计。

## 参考资料

- [`Debug`：PSS、RSS、native heap 与 Hprof API](https://developer.android.com/reference/android/os/Debug)
- [`Debug.MemoryInfo`](https://developer.android.com/reference/android/os/Debug.MemoryInfo)
- [`ActivityManager.getProcessMemoryInfo()`](https://developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int%5B%5D))
- [`ActivityManager.MemoryInfo`](https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Process Memory chart glossary](https://developer.android.com/studio/profile/chart-glossary/process-memory)
- [Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager)
- [`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android 17：App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Android vitals：Low memory killer](https://developer.android.com/topic/performance/vitals/lmk)
- [AOSP `Debug.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Debug.java)
- [AOSP `android_os_Debug.cpp` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp)
- [AOSP `ActivityManager.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [AOSP `ApplicationExitInfo.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP `ComponentCallbacks2.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP Profiling `ProfilingManager.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [AOSP Profiling `ProfilingTrigger.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [Kernel `/proc/<pid>/status` @ `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c)
- [Kernel `smaps_rollup` @ `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/task_mmu.c)
