---
title: 内存监控与线上治理
chapter: '23.7'
section: '23.7'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: Android 17 / API 37 / AOSP android-17.0.0_r1；Debug、ActivityManager、ApplicationExitInfo、ProfilingManager、Android Vitals LMK 与 Memory Advice 官方文档
last_review_finalize_at: '2026-08-15T08:12:21+08:00'
last_review_finalize_run_id: 20260815-081221-gracker-writing-review
confidence: high
sources:
- type: official
  path: https://developer.android.com/reference/android/os/Debug
- type: official
  path: https://developer.android.com/reference/android/os/Debug.MemoryInfo
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo
- type: official
  path: https://developer.android.com/reference/android/content/ComponentCallbacks2
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int[])
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://developer.android.com/studio/profile/chart-glossary/process-memory
- type: official
  path: https://developer.android.com/topic/performance/memory
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: official
  path: https://developer.android.com/studio/profile/capture-heap-dump
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits
- type: official
  path: https://developer.android.com/topic/performance/vitals/lmk
- type: official
  path: https://developer.android.com/games/sdk/memory-advice/overview
- type: official
  path: https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/cb0cf2c186b9a70a15057bdf8d998eab38f74fa1/include/memory_advice/memory_advice.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Debug.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/cb0cf2c186b9a70a15057bdf8d998eab38f74fa1/games-memory-advice/core/memory_advice_impl.cpp
- type: clipping
  path: 货拉拉司机 Android 端内存治理实践（本地归档 Cubox）
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]'
tags:
- memory-monitoring
- pss
- rss
- heap-dump
- oom-alert
related_chapters:
- '23.2'
- '23.3'
- '23.1'
- '23.5'
- '20.5'
- '26.1'
- '10.1'
- '17.3'
pipeline_stage: finalized
last_draft_polish_at: '2026-08-15T08:12:21+08:00'
last_draft_polish_run_id: 20260815-081221-gracker-writing
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
consolidated_from:
- src/part5-app/ch23-memory-practice/08-memory-case-studies.md
- src/part5-app/ch23-memory-practice/10-memory-advice-api.md
---

# 内存监控与线上治理

线上内存治理需要区分泄漏、峰值、持续增长和系统回收风险，并把每个信号关联到版本、场景和设备分层。采集方案既要统一 PSS、RSS、Java 与 Native 口径，也要控制快照成本和隐私边界。

> **版本基线**
>
> 平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点；读取 `/proc` 指标时，内核侧以 `android17-6.18-2026-06_r6` 为基线。历史版本只用于说明 API 与行为边界，最高版本为 Android 17。

## 线上监控要回答什么

本地 Memory Profiler（Android Studio 内存分析器）适合解释一次可复现的问题；生产环境监控面对的是分散在版本、设备、进程和业务场景中的样本。它至少要回答四个问题：

- 哪一类内存在增长：Java Heap（ART 管理的 Java/Kotlin 对象堆）、native allocator（C/C++ 内存分配器）、图形、文件映射、线程栈，还是多个进程的合计。
- 增长是短时峰值、可回落缓存，还是跨页面、跨会话持续积累。
- 变化是否集中在某个版本、设备档位、ABI（应用二进制接口，规定指令集、调用约定和二进制布局）、进程或用户路径。
- 需要保留轻量指标、退出记录、Java heap dump（Java 堆转储），还是 native heap profile（按采样记录原生内存分配调用栈的剖析产物）。

只上报一个“内存占用”指标，无法区分这些问题。PSS、RSS、Java Heap 和 Native Heap（原生堆）的统计对象不同，任何一项都不能单独代表应用的全部内存。多进程应用还要带进程名；把所有进程混成一个分布，会掩盖主进程回归或独立任务进程的峰值。

Java 泄漏引用链见 [23.2 内存泄漏检测与治理](02-memory-leak-governance.md)，原生分配诊断见 [23.3 Native 与虚拟内存管理优化](03-native-virtual-memory-optimization.md)，Java Heap 预算见 [23.1 Java Heap、GC 与 Compose 内存分配](01-java-heap-gc-compose-allocation.md)，OOM（`OutOfMemoryError`，无法满足分配时抛出的内存不足异常）分类见 [20.5 OOM、进程资源治理与 WebView Renderer 恢复](../ch20-stability/05-oom-webview-renderer-recovery.md)。本文聚焦生产环境中的指标、判断、降级和证据采集。

## 内存指标采集：先统一统计定义

### PSS、RSS、Java Heap 与 Native Heap

| 指标 | Android 入口 | 适合回答 | 不能据此断言 |
| --- | --- | --- | --- |
| PSS（Proportional Set Size，按比例分摊集） | `ActivityManager.getProcessMemoryInfo()`、`Debug.getPss()`、`Debug.MemoryInfo.totalPss` | 进程私有页加共享页按比例分摊后的系统内存占用 | 某个 Java 对象或原生调用栈造成了增长 |
| RSS（Resident Set Size，驻留集大小） | API 35+ 的 `Debug.getRss()`；旧版本可读本进程 `/proc/self/status` 的 `VmRSS` | 当前驻留在物理内存中的页总量及其变化 | RSS 全部由应用独占；共享页会被每个进程完整计入 |
| Java Heap | `Runtime.totalMemory() - Runtime.freeMemory()`、`Runtime.maxMemory()` | ART 堆已用空间的近似值与当前上限 | 已用值全是可达对象；尚未经过 GC（垃圾回收）的不可达对象也可能在其中 |
| native allocator | `Debug.getNativeHeapAllocatedSize()` | 当前进程原生内存分配器已分配的字节数 | 所有原生内存、图形内存、`mmap` 映射和线程栈都包含在该值中 |
| 分类 PSS | `Debug.MemoryInfo.dalvikPss`、`nativePss`、`otherPss` 及汇总字段 | PSS 按映射类别的组成 | `nativePss` 等于 `malloc` 的活跃分配；两者统计路径不同 |
| 设备内存状态 | `ActivityManager.getMemoryInfo()` | `availMem`、`threshold`、`lowMemory` 所描述的全设备背景 | 当前进程离 Java OOM 还有多少字节 |

这张表用于确定每项数据能回答什么。判断全局趋势可用 PSS 或 RSS；定位 Java 或原生分配，要再结合各自的堆指标与诊断产物。

`Debug.MemoryInfo` 的 PSS 字段以 kB 表示；`Runtime` 和 `Debug.getNativeHeapAllocatedSize()` 返回字节，入库前必须保留单位。`Debug.getMemoryInfo()` 直接读取当前进程，但 Android 17 源码注释说明它可能无法取得 graphics（图形）等受保护分配；需要更完整的进程分类时，应使用 `ActivityManager.getProcessMemoryInfo()`。

Android 10（API 29）起，普通应用通过 `getProcessMemoryInfo()` 只能取得调用方 UID（应用在系统中的用户标识）下的进程信息，其他 PID（进程编号）的条目为零；平台还会限制采样频率，调用过密可能收到上一次结果。采样请求时间不等于底层数据的更新时间，监控系统不能用高频调用制造虚假的高分辨率曲线。

Android 17 的 `Debug.getRss()` 仍是当前进程 API。`android-17.0.0_r1` 的 JNI 实现读取 `StatusVmRSS()`，并在 memtrack（Android 图形内存统计接口）可用时加入 graphics、GL 和 other 三类未计入 `/proc` 映射的图形内存；直接读取 `/proc/self/status` 只能得到原始 `VmRSS`。这是该版本的实现细节，公开 API 注释只承诺返回 RSS。因此，API 35 前后的 RSS 来源需要单独标记，不能不加说明就拼进同一条比较基线。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/os/Debug.java`, `frameworks/base/core/jni/android_os_Debug.cpp`, `frameworks/base/core/java/android/app/ActivityManager.java`]

### 一个可审计的采样实现

这段实现采集当前进程的低频快照。调用方需要在非主线程执行，并由远程策略决定采样时机；代码没有假设固定周期或固定阈值。

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

`pssKb == null` 或 `rssKb == null` 表示本次未取得有效值，不能按零内存上报。`DEBUG_API_WITH_MEMTRACK` 只表示样本来自 `Debug.getRss()`：Android 17 r1 会尝试加入 memtrack 数据，但该枚举值不能证明本次 memtrack 查询成功。`elapsedRealtimeMs` 来自设备启动后的单调时钟，适合计算同一次开机期间的时间差，重启后会重新计时；跨设备、跨重启聚合时还要带服务端接收时间。

事件包还应包含应用版本、Android 版本、ABI、设备 RAM（物理内存）档位、前后台状态、页面类别、采样原因、采样策略版本和每个指标的来源。

### 采样频率由成本和问题决定

指标分为三类：

- 本进程计数：Java Heap 和 native allocator 读取较直接，可以在应用启动完成、页面退出或任务结束时采集。
- 映射统计：PSS 需要读取进程映射并可能经过系统服务，适合低频、场景结束或异常触发。
- 诊断产物：heap dump、heap profile 和 Perfetto system trace（记录系统调度、内存计数与业务事件时间关系的跟踪文件）开销与敏感度高，只能由严格条件触发。

采样任务自身也要测量执行时间、分配量、I/O 和上报量。若采样逻辑在启动、列表滚动或渲染关键路径执行，采集行为可能改变被观察对象。官方也不建议持续轮询 `ActivityManager.getMemoryInfo()`。每轮发布都要保留“未采到、被限流、权限不足、文件失败”等状态，不能只统计成功样本。

## 内存阈值与告警策略

### 不使用跨设备固定百分比

Java Heap 上限、设备 RAM、页面资源、ABI、WebView 版本和厂商内存策略都会改变正常分布。一个跨设备固定比例容易同时产生漏报与误报。线上阈值应来自同类样本：

- 版本：当前分批放量（灰度）版本对比上一稳定版本。
- 设备：按 RAM 档位、低内存设备（low-RAM）标记、ABI 和设备形态分组。
- 进程：主进程、独立任务进程、推送进程、WebView 宿主分别统计。
- 场景：冷启动稳定点、页面停留、任务峰值、页面退出后的回落、后台驻留分别统计。
- 状态：前台可见、前台服务、后台和缓存进程（cached）状态不能共用一条阈值。

比较基线至少要保留完整分布、样本数和缺失率。缺失率是应采样但没有得到有效数据的样本占比；只比较成功样本，可能把限流或采集失败造成的偏差误判成改善。均值会掩盖少数高值形成的长尾；P95、P99 等分位数分别表示 95%、99% 的样本不超过该值。样本不足、设备构成变化或场景定义变化时，分位数也不能直接用于发布判断。

### 一条告警需要趋势、恢复能力和上下文

| 观察 | 需要组合的信号 | 更可能的方向 |
| --- | --- | --- |
| Java Heap 接近上限 | 使用比例、分配/回收趋势、页面退出后的回落 | 无界缓存、对象泄漏、批量分配过大 |
| RSS/PSS 上涨而 Java Heap 平稳 | native allocator、Graphics、线程数、FD、`mmap` 场景 | 原生内存、图形、线程栈或文件映射 |
| native allocator 上涨 | `nativeAllocatorBytes` 与 `nativePss`、RSS 同向性 | malloc 路径增长；仍需 heap profile 或调用栈确认 |
| PSS 高但 RSS 变化不同 | 共享页比例、进程数量、WebView renderer（独立渲染进程） | 共享映射或进程结构变化 |
| `lowMemory=true` | `availMem`、`threshold`、进程状态、设备档位 | 设备整体压力，不等同于当前进程泄漏 |
| 资源释放后不回落 | 相同场景的多次采样、GC 与生命周期边界 | 持有关系、allocator 保留或映射未释放 |

FD 是 file descriptor（文件描述符），表示进程打开的文件、套接字或管道句柄；`mmap` 是把文件或匿名内存映射进进程地址空间的系统调用。表中的“更可能的方向”用于选择下一项证据，不能直接当作根因结论。例如 RSS 上涨且 Java Heap 平稳时，应再查看 native heap profile、图形内存、线程和映射；仅凭这组曲线还不能确认原生内存泄漏。

示例分类器只处理 Java Heap 连续高位。阈值和最少样本数必须由发布策略传入，不能把示例值写死在客户端。

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

分类结果只是候选信号。进入 `CAPTURE_CANDIDATE`（允许进一步评估是否采集诊断产物）前，还要检查前后台状态、用户交互、磁盘、电量、近期采集配额和隐私策略；执行资源收缩后要再采一次轻量指标，记录释放动作是否有效。

### 告警事件要能指导排查

建议按用途拆分事件，不要统一命名为“OOM warning（内存不足预警）”：

| 事件 | 判定重点 | 必要字段 |
| --- | --- | --- |
| `memory_baseline_regression` | 同一分组相对稳定版本的分布变化 | 基线版本、当前版本、分组键、分位数、样本数、缺失率 |
| `java_heap_pressure` | Java Heap 连续高位与回落失败 | `used/max`、GC 统计、页面类别、缓存规模、执行动作 |
| `native_or_mapping_growth` | RSS/PSS 上涨且 Java Heap 平稳 | native allocator、分类 PSS、线程、FD、任务类型 |
| `system_memory_pressure` | 设备低内存背景与应用状态 | `availMem`、`threshold`、`lowMemory`、进程重要性 |
| `profile_requested` | 满足证据采集条件 | 触发规则、配额、设备状态、请求类型 |
| `profile_result` | 系统返回成功或错误 | 结果类型、错误码、文件大小、策略版本 |
| `previous_memory_exit` | 重启后发现 LMK 或 Memory Limiter | 退出原因、描述标记、上次采样 PSS/RSS |

`used/max` 表示 Java Heap 已用字节数除以上限；分组键是用于区分版本、设备、进程和场景的字段组合。LMK 是 Low Memory Killer（低内存终止），Android 的 `lmkd` 守护进程会在全设备内存压力下选择低优先级进程终止。Memory Limiter 则是 Android 17 在部分设备上启用的单应用内存限制，两者需要分开统计。事件名决定后续处理流程：趋势回归进入版本比较，压力事件进入资源降级，退出事件进入重启后取证，`profile_requested` 和 `profile_result` 进入敏感文件治理。

事件里应保存页面类别或业务阶段，不要默认上传完整 URL、搜索词、对象字符串或用户标识。监控维度越细，越需要在客户端先转换成有限枚举并删除不必要字段。

## 内存压力预警、资源降级与退出归因

### 能安全释放的只有业务可控资源

预警阶段可以缩小图片缓存、停止预取、取消尚未开始的批处理、减少播放器预缓冲、关闭闲置 WebView、释放页面级对象并降低后续输入规格。流、游标、文件描述符、`ParcelFileDescriptor`、`SharedMemory` 映射和 native handle（原生资源句柄）都要由明确的所有者关闭；缺少所有权约定时，重复关闭和遗漏释放都可能发生。

不要把 `System.gc()` 当成常规回收接口。GC 只能处理不可达对象，无法释放仍被缓存、单例、JNI global reference（JNI 全局引用，会让原生代码长期持有 Java 对象）或活跃组件持有的数据；显式 GC 还可能增加停顿。也不要在全局捕获 `OutOfMemoryError` 后继续运行：OOM 发生时，错误处理路径本身可能无法分配对象，进程状态也可能不再满足业务依赖的状态约束。边界清楚的单次分配可以设计局部降级，例如图片解码失败后改用更小规格。

Android 17 上，`onTrimMemory()` 仍应聚焦 `TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND`，这两个等级表示界面隐藏或进程进入后台 LRU（按最近使用时间维护的进程列表）。从 Android 14（API 34）起，其余旧内存压力等级不再投递，并在 Android 15（API 35）废弃。设备压力使用 `ActivityManager.MemoryInfo` 观察；Android 17 应用内存限制的事前取证使用 `TRIGGER_TYPE_ANOMALY`，退出后再读 `ApplicationExitInfo`。

### 重启后核对退出原因

Android 11（API 30）起，`getHistoricalProcessExitReasons()` 可以读取调用方 UID 最近的退出记录。这段代码只挑出 LMK 和 `android-17.0.0_r1` 所定义的 Memory Limiter 记录。

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

`getPss()` 和 `getRss()` 是系统上一次采样值，可能为零，也不代表进程死亡前一刻的精确内存。`getDescription()` 的一般格式没有稳定保证；这里匹配的 `MemoryLimiter:AnonSwap` 是 Android 17 r1 行为文档明确给出的标记，不应扩展成对其他描述文本的解析。[23.5 大内存与多进程策略](05-large-heap-multiprocess.md) 继续说明 Memory Limiter 的设备范围和测试命令。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/app/ApplicationExitInfo.java`]

### Memory Advice 只作为已接入项目的过渡信号

Memory Advice API 已结束 Beta 测试，官方文档在 2026 年 2 月将该库标记为 deprecated（已弃用）。新项目不应增加这项依赖；已接入的游戏或引擎可以在迁移期间把它保留为一项压力信号。

Memory Advice 以 Android Game Development Kit（AGDK）的独立 native 库形式提供，不由 Android framework 服务管理。公开 C API `MemoryAdvice_getAvailableMemory()` 返回“可安全分配字节数”的估算。Memory Advice 2.1.0 的 AOSP 实现用预测可用百分比乘以初始化时记录的设备总内存；这个值不等于 `/proc/meminfo` 的 `MemAvailable`，也不表示系统当前有同样多的空闲页。`OK`、`APPROACHING_LIMIT`、`CRITICAL` 是模型和规则给出的建议状态，不能预测下一次分配、`lmkd` 或 Android 17 Memory Limiter 的结果。

监视器（watcher）会创建该库自己的线程，按注册间隔检查状态；只有状态不为 `OK` 时才调用回调函数（callback）。回调函数应把压力请求交给线程安全的策略入口，纹理、网格（mesh）数据、音频、场景资源和 GPU 缓冲区仍要回到引擎规定的线程分批释放。注销与正在执行的回调可能交错，`user_data` 指向的调用方数据必须存活到所有回调结束。

迁移时可保持四层结构：信号层汇总资源数量、PSS/RSS、生命周期与历史退出；策略层按设备和场景输出低、中、高等资源规格；执行层在指定线程降低规格或释放可重建资源；验证层比较峰值、回落、帧时间与 LMK/Memory Limiter。旧库移除后，资源模块仍可沿用同一套策略接口。

## 线上诊断产物采集

### 先按问题选择产物

| 产物 | 适用问题 | 主要限制 |
| --- | --- | --- |
| 轻量摘要 | 大范围设备的趋势、版本回归、采集前筛选 | 只能指出方向，不能提供对象引用链 |
| Java heap dump（Java 堆转储） | Java/Kotlin 对象数量、持有关系、泄漏 | 只覆盖 Java Heap；生成与处理会消耗内存、CPU、I/O |
| heap profile（堆分配剖析） | Java 或 native 分配热点与调用栈 | 采样结果需要结合场景解释，不等于存活对象图 |
| Perfetto system trace（系统跟踪） | GC、调度、内存计数与业务时序 | 不替代对象级 heap dump |
| `ApplicationExitInfo` | LMK、Memory Limiter 及其他退出后的证据 | 记录有限；PSS/RSS 是上次采样值 |

轻量摘要用于筛选，堆转储回答“谁持有对象”，堆分配剖析回答“谁在分配”，系统跟踪回答“何时发生以及与调度、GC 有何关系”。先按问题选择产物，可以减少无效采集和敏感数据暴露。

`Debug.dumpHprofData()` 可以把当前进程 Java Heap 写成 Hprof（记录 Java 堆对象与引用关系的快照文件）。Android 17 `Debug.java` 的注释指出该操作可能触发 GC，并可能抛出 `UnsupportedOperationException` 或 `IOException`。它适合本地、内部构建或受控诊断，不应在内存已经很紧张时由普通线上规则直接调用。

`ActivityManager.setWatchHeapLimit()` 也不是生产监控接口。Android 17 源码和 API 注释明确要求应用为 debuggable（允许调试），或设备使用 userdebug/eng（带调试能力的系统构建）；它适合开发阶段验证 PSS 阈值与 heap dump 流程。

Android 15（API 35）起，`ProfilingManager` 支持应用主动请求 Java heap dump、heap profile、stack sampling（调用栈采样）和 system trace，并有系统限流。官方 Jetpack wrapper（封装接口）提供 `JavaHeapDumpRequestBuilder` 与 `HeapProfileRequestBuilder`；请求不保证执行，结果和错误都通过 `ProfilingResult` 返回。

### Android 17 的 OOM 与异常触发器

触发器（trigger）让系统在特定事件发生时决定是否采集诊断产物。Android 17（API 37）增加 `TRIGGER_TYPE_OOM` 和 `TRIGGER_TYPE_ANOMALY`：

- OOM 触发器在应用出现 `OutOfMemoryError` 时提供 Java heap dump。若应用安装了自定义 `UncaughtExceptionHandler`（未捕获异常处理器），应保存安装前的系统默认处理器，并在自定义处理结束后转交给它；未调用默认处理器时，该触发器无法工作。
- Anomaly（异常）触发器在系统识别异常资源行为时触发，产物类型取决于异常。Android 17 应用内存限制命中时，系统可以在执行限制前提供 Java heap dump；其他异常可通过 `ProfilingResult.getTag()` 进一步识别，部分异常可能没有文件产物。

这段注册函数同时监听两种内存触发器。它应在要监控的进程启动后注册一次，并保留返回的 listener（监听器）；不再需要接收结果时，用它调用 `unregisterForAllProfilingResults()`。

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

`unregisterForAllProfilingResults(listener)` 只停止向该监听器交付结果，不会删除已经注册的触发器。要停止监控，还要调用 `removeProfilingTriggersByType()` 删除指定类型，或调用 `clearProfilingTriggers()` 清空本应用的触发器。

系统触发器受随机设备采样与系统限流影响，不保证每次事件都有产物。触发器结果只能通过全局监听器接收；如果采集时进程已经退出，系统会在应用再次启动并注册监听器后尝试交付。多个软件包共用同一 UID 且都注册异常触发器时，某些异常可能无法生成产物。文件位置必须使用 `ProfilingResult.getResultFilePath()`，不能依赖内部目录结构。应用还可以用 `ProfilingTrigger.Builder.setRateLimitingPeriodHours()` 增加自己的冷却期，也就是两次触发之间的最短间隔；该限制会与系统限流同时生效，具体时长应由采样配额和隐私规则决定。

[源码锚点: AOSP `android-17.0.0_r1`, `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`, `ProfilingTrigger.java`]

### 产物治理比触发代码更重要

Java heap dump 可能包含对象字符串、用户输入、请求响应、缓存键、文件路径和业务标识。文件位于应用私有目录并不代表内容已经去除敏感信息。上线前需要完成：

- 采集资格：版本、进程、场景、设备状态、磁盘和配额均满足策略。
- 最小化：能用指标或摘要定位时不采完整 dump；原生内存问题不采 Java dump。
- 安全传输：文件在端侧、传输中和服务端均按敏感诊断数据保护。
- 访问控制：限制可查询人员、记录访问审计、设置保留期限并支持删除。
- 用户与合规：遵循产品隐私说明、用户选择、地区法规和商店政策。
- 资源控制：支持远程关闭；失败后逐步延长重试间隔；限制每台设备、每个版本的采集次数；限定允许上传的网络类型。
- 可分析性：保留构建符号、混淆映射、版本、进程、触发规则和场景标签。

收到文件路径后，不要在回调函数中直接压缩并通过网络上传。回调函数只登记结果与错误，后续任务再核对文件、策略和设备条件。分析完成后要能从问题特征回查对应版本与样本分组，但不需要把原始用户路径写进文件名。

## 把案例与预算写成可复用证据

一条完整的内存案例应记录：用户场景 → 可重复动作 → 按同一统计定义采集的前后快照 → 引用链或分配栈 → 资源所有权缺陷 → 最小修改 → 同场景复测 → 线上结果。只有快照相关性时，结论仍是待验证假设。

预算也不能只给应用一个 MB 数。每条记录至少包含平台与构建、设备档位、进程、场景与采样时点、Java Heap、native allocator、Graphics 与总 PSS、样本量与分位数、负责人、处置和回滚。`memoryClass` 是系统为当前应用提供的 Java Heap 近似上限，不是进程 PSS 预算。

货拉拉公开复盘可拆成三类不同记录，不能笼统合并成“图片模块增长”：

| 场景 | 主要证据 | 根因方向 | 验收重点 |
| --- | --- | --- | --- |
| 首页反复展示弹窗 | Java heap dump 引用链与布局对象累积 | Lifecycle observer（生命周期观察者）未注销，旧 Dialog/View 仍可达 | 对象不再随次数累积 |
| 相机帧录制与识别 | `byte[]` 高占比、频繁 GC | 高频创建、释放与复用不足 | 分配速率、峰值、GC、分批放量阶段的 OOM 率 |
| 图片发送与旋转 | 原生内存峰值与大 Bitmap | 第一次解码前没有尺寸约束 | 解码/变换峰值和退出回落 |

三个案例的曲线都可能表现为“内存上涨”，证据却分别指向生命周期持有、短命数组分配和图片解码峰值。案例库应保留这种“现象—证据—所有者”的对应关系，避免按模块名或单一曲线套用结论。

修复后保留受影响版本、复现输入、原始证据、被排除的假设、资源所有者、修改与回滚、实验环境中的修复前后数据、分批放量样本和防复发验收条件。没有支持原假设的实验结果也应记录，避免下一次面对相同曲线重新猜测。

## 发布验收条件与线上复盘

发布验收应同时检查分布和失败率：

- 主进程与各独立进程的 PSS/RSS 分布相较稳定版本是否整体上移。
- Java Heap 峰值、页面退出后的回落，以及内存随会话时长持续上升的速度是否改变。
- native allocator、Graphics、线程与 FD 是否出现同向增长。
- Android Vitals 的 user-perceived LMK rate（发生至少一次用户可感知 LMK 的日活用户占比）是否上升；官方当前把超过 1% 标为严重。
- 应用自行统计的 Java OOM 与 native crash（原生代码崩溃）是否变化。
- `ApplicationExitInfo` 中 LMK、Android 17 Memory Limiter 与其他退出是否集中在同一分组。
- `ProfilingManager` 请求成功率、限流率、无产物率和文件处理失败率是否符合预期。

扩大分批放量范围前，要核对样本数、设备构成和场景覆盖。发现回归时，先缩小到版本、进程、设备与场景，再决定需要 Java heap dump、heap profile 还是 Perfetto system trace。在没有证据表明 Java 对象增长时，不要因为“内存高”就批量采集 Hprof。

## 全文小结

线上内存治理从统计定义开始：PSS 表示共享页按比例分摊后的占用，RSS 表示驻留页总量，Java Heap 和 native allocator 只覆盖各自的分配范围，设备 `MemoryInfo` 提供全局背景。所有指标都要带单位、来源、进程、场景和策略版本。

告警要观察同类样本的趋势与回落能力，再选择释放可重建资源、记录退出原因或申请系统诊断产物。Android 17 的 OOM 与异常触发器为难复现问题提供了系统产物，但仍受限流与采样约束。heap dump 是高成本且敏感的诊断数据，采集、传输、访问和删除必须作为同一项工程能力设计。

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
- [Memory Advice overview（已弃用）](https://developer.android.com/games/sdk/memory-advice/overview)
- [AOSP Memory Advice 2.1.0 C API 头文件](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/cb0cf2c186b9a70a15057bdf8d998eab38f74fa1/include/memory_advice/memory_advice.h)
- [AOSP Memory Advice 2.1.0 `GetAvailableMemory()` 实现](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/cb0cf2c186b9a70a15057bdf8d998eab38f74fa1/games-memory-advice/core/memory_advice_impl.cpp)
