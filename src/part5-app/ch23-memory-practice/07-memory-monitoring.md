---

title: "内存监控与线上治理"
chapter: "23.7"
section: "23.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers Debug/ActivityManager/ComponentCallbacks2 + Clippings/Android 性能优化"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/Debug.MemoryInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager.MemoryInfo"
  - type: official
    path: "https://developer.android.com/reference/android/content/ComponentCallbacks2"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int[])"
  - type: official
    path: "https://developer.android.com/studio/profile/chart-glossary/process-memory"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Debug.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-16.0.0_r1"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]"
tags: [memory-monitoring, pss, rss, heap-dump, oom-alert]
related_chapters: ["23.1", "20.5", "26.3", "10.1", "19.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
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
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_audit: "2026-06-08"
auto_finalized_by: openclaw-task6
auto_finalized_date: "2026-05-14"
last_task9_audit: "2026-06-08"
last_task9_autofix_at: "2026-06-08"
task9_review_notes: "2026-05-14 Task9 04: pass-tech-review。P0/P1 0；P2 1：Debug.getRss() API 35+ 边界，后续已由 Task6 标注并自动晋升 finalized。 | 2026-06-08 Task9 idle audit: auto-fixed。P0 0 / P1 1 / P2 1；补充 Android 14/API 34 起 TRIM_MEMORY_RUNNING_* 等旧低内存等级不再投递、API 35 废弃的版本边界；Android 17/API 37 ProfilingTrigger OOM/anomaly 属于本节未来扩展 P2，未写入正文。"
task6_state: reviewed
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_audit: "2026-06-08"
---

# 内存监控与线上治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存指标采集：PSS / RSS / Java Heap / Native Heap
- 🔹 内存水位线与告警策略
- 🔹 OOM 预警与主动回收
- 🔹 内存快照（Heap Dump）线上采集方案

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解内存监控与线上治理

内存优化做到线上阶段，问题已经从“哪里多占了内存”变成“什么时候该报警、该保留什么现场、该把哪类样本交给谁处理”。本地 Profiler 适合看清单机现象，线上监控要回答的是趋势、阈值、版本回归和 OOM 前兆。

这里的边界是监控与治理策略。Java 泄漏引用链详见 23.1 节，OOM 分类详见 20.5 节，内存分析工具详见 10.1 节，KOOM 这类专项工具详见 19.3 节。原理部分不重复展开，重点放在可持续采集、告警和现场保存。

参考书把 Android App 内存拆成 Java Heap、Native Heap、图形/文件映射、线程栈、多进程共享页等多个来源，这个拆法适合作为线上指标体系的结构参考。线上面板不能只放一个“内存占用”，否则 Java 泄漏、Native 泄漏、图片缓存、线程栈增长、mmap 增长都会混在同一条曲线上。[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]

## 内存指标采集：PSS / RSS / Java Heap / Native Heap

线上采集要把“系统怎么计量”和“业务怎么判断”分开。PSS 更适合看进程对系统内存压力的分摊，RSS 更适合看进程当前驻留物理内存，Java Heap 与 Native Heap 用来定位增长来源。

| 指标 | 采集入口 | 线上用途 | 边界 |
|---|---|---|---|
| PSS | `ActivityManager.getProcessMemoryInfo(intArrayOf(pid))` 或 `Debug.getMemoryInfo()` | 观察进程对系统内存的分摊压力，适合做版本基线和 OOM 前兆指标 | Android Q 起 `getProcessMemoryInfo()` 采样频率被系统限制，过快调用会拿到上一次结果；PSS 读取成本高，不适合秒级轮询 |
| RSS | Android Studio Process Memory 口径、`/proc/self/status` 的 `VmRSS`、API 35+ 的 `Debug.getRss()` | 观察进程驻留物理内存，适合发现 native 分配、mmap、线程栈和图形资源抬升 | RSS 包含共享页，不能直接等同于“应用独占内存”；公开 API 可用性随版本变化，线上兼容采集应优先读本进程 `/proc` |
| Java Heap | `Runtime.totalMemory() - Runtime.freeMemory()`、`Runtime.maxMemory()`、`Debug.MemoryInfo.dalvikPss` | 判断 Java 对象分配与 `maxMemory()` 的距离，适合 Java OOM 预警和泄漏趋势 | `dalvikPss` 是内存页口径，`Runtime` 是 Java 堆对象口径，两者不能混算 |
| Native Heap | `Debug.getNativeHeapAllocatedSize()`、`Debug.MemoryInfo.nativePss` | 观察 C/C++、Bitmap native backing、第三方 SDK、播放器、图形相关分配 | native 增长不等于泄漏，缓存、解码 buffer、mmap 和线程栈都要分开归因 |
| 系统水位 | `ActivityManager.getMemoryInfo(ActivityManager.MemoryInfo)` | 判断设备是否进入低内存状态，结合 `availMem`、`threshold`、`lowMemory` 做全局背景信号 | 这是设备维度信号，不是单个 App 的 OOM 阈值 |

[已验证: 官方文档, developer.android.com/reference/android/os/Debug.MemoryInfo] `Debug.MemoryInfo` 按 dalvik、native、other 拆分内存映射，公开字段包含 `dalvikPss`、`nativePss`、`otherPss`、private dirty 等，单位为 kB。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Debug.java] `Debug.getMemoryInfo(MemoryInfo)` 直接读取当前进程可见的底层内存信息；源码注释说明它可能拿不到某些受保护分配，例如 graphics，若要覆盖进程分配信息，应使用 `ActivityManager.getProcessMemoryInfo(int[])`。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/ActivityManager.java] `getProcessMemoryInfo(int[])` 通过系统服务返回每个 pid 对应的 `Debug.MemoryInfo`；源码注释写明 Android Q 起该 API 采样频率受到限制，调用过快会返回上一次数据。

一段可用的采集代码要做两件事：按低频周期采 PSS / native 页口径，按更高频周期采 Java Heap 对象口径。下面是采集骨架，重点看单位换算和采样频率分离。

```kotlin
import android.app.ActivityManager
import android.content.Context
import android.os.Debug
import android.os.Process

// 示意代码：调用方需要放到后台线程，并加采样率、远程开关和异常保护。
data class MemorySample(
    val timestampMs: Long,
    val pssKb: Int,
    val javaHeapUsedKb: Long,
    val javaHeapMaxKb: Long,
    val nativeHeapAllocatedKb: Long,
    val dalvikPssKb: Int,
    val nativePssKb: Int,
    val otherPssKb: Int
)

fun collectMemorySample(context: Context): MemorySample {
    val am = context.getSystemService(ActivityManager::class.java)
    val info = am.getProcessMemoryInfo(intArrayOf(Process.myPid())).first()
    val runtime = Runtime.getRuntime()

    return MemorySample(
        timestampMs = System.currentTimeMillis(),
        pssKb = info.totalPss,
        javaHeapUsedKb = (runtime.totalMemory() - runtime.freeMemory()) / 1024,
        javaHeapMaxKb = runtime.maxMemory() / 1024,
        nativeHeapAllocatedKb = Debug.getNativeHeapAllocatedSize() / 1024,
        dalvikPssKb = info.dalvikPss,
        nativePssKb = info.nativePss,
        otherPssKb = info.otherPss
    )
}
```

这段代码只能作为基础探针。线上版本还要补进程名、前后台状态、页面、机型、Android 版本、App 版本、采样原因和采样间隔；没有这些维度，单点数值很难转成治理动作。

[自动发现] RSS 曲线要单独入库。Android Studio 2026 年文档把 Process Memory（RSS）拆成 Total、Allocated、File Mappings、Shared，用来解释物理驻留内存来自匿名私有分配、文件映射还是共享内存。线上不一定能拿到 Studio 的完整拆分，但至少要区分 `VmRSS`、PSS 和 Java Heap，避免把 RSS 抬升误判成 Java 泄漏。[已验证: 官方文档, developer.android.com/studio/profile/chart-glossary/process-memory]

## 内存水位线与告警策略

水位线不要写成固定百分比。不同设备的 `memoryClass`、前后台行为、64 位比例、图片规格、页面复杂度和厂商 LMK 策略都不一样，固定“80% 报警”会在低端机上过晚，在高端机上过早。

更稳的水位线由三层组成：

| 层级 | 判断对象 | 触发方式 | 处理动作 |
|---|---|---|---|
| 版本基线 | P50 / P90 / P99 的 PSS、RSS、Java Heap 使用率 | 每个版本、机型档位、进程类型分别建基线 | 发现版本回归，拦截灰度扩大 |
| 设备水位 | `ActivityManager.MemoryInfo.availMem`、`threshold`、`lowMemory` | 系统进入低内存区间，或 `availMem` 接近 `threshold` | 降低缓存、停止预加载、延后非必要任务 |
| 进程水位 | Java Heap 使用率、PSS / RSS 连续增长、Native Heap 增长 | 连续 N 次采样超过阈值，且 GC / trim 后仍未回落 | 采集快照、打标页面、触发专项诊断 |

[已验证: 官方文档, developer.android.com/reference/android/app/ActivityManager.MemoryInfo] `ActivityManager.MemoryInfo` 提供 `availMem`、`totalMem`、`threshold` 和 `lowMemory`。其中 `threshold` 是系统认为可用内存偏低并开始杀后台服务或非必要进程的 `availMem` 门槛，`lowMemory` 表示系统当前是否处于低内存状态。

告警规则要看“持续增长”和“回落能力”。一次 PSS 高点可能来自大图解码、页面切换、短视频缓冲或文件 mmap；连续多个采样窗口高位不回落，才更接近泄漏或缓存失控。

一套常用的内存告警口径可以这样落表：

| 事件 | 条件 | 样本字段 |
|---|---|---|
| `memory_baseline_regression` | 同机型档位 P90 PSS 比上一稳定版本上升超过阈值，并持续两个灰度批次 | version、device_tier、process、pss_p90、rss_p90、sample_count |
| `java_heap_pressure` | Java Heap 使用率连续超过阈值，且手动释放业务缓存后仍未回落 | heap_used、heap_max、page_stack、gc_count、cache_size |
| `native_growth` | Native Heap 或 RSS 连续增长，但 Java Heap 稳定 | native_heap、rss、thread_count、fd_count、top_page |
| `system_low_memory` | `lowMemory=true` 或 `availMem` 接近 `threshold` | avail_mem、threshold、foreground、trim_level、device_tier |
| `snapshot_triggered` | 满足快照条件并成功保留现场 | snapshot_type、file_size、duration、result、reason |

这类事件要能转成治理动作：版本回归给发布门禁，单设备高水位给快照采集，低内存信号给端侧降级。把所有情况都打成一个 “OOM warning” 会让排查入口失效。

## OOM 预警与主动回收

OOM 预警不是等 `OutOfMemoryError` 抛出来。线上更有价值的窗口在 OOM 之前：Java Heap 接近上限、PSS / RSS 长时间不回落、系统低内存信号增强、页面刚经历大图/视频/列表密集加载。

可执行的预警策略按信号强弱分级：

| 等级 | 信号 | 端侧动作 | 上报动作 |
|---|---|---|---|
| L1 观察 | Java Heap 或 PSS 高于该设备档位 P90 | 记录页面和业务状态，不打扰用户 | 普通采样上报 |
| L2 降级 | 连续采样高位；Android 13 及以下可结合 `TRIM_MEMORY_RUNNING_LOW`，Android 14+ 主要看 `MemoryInfo.lowMemory` / `availMem` 接近 `threshold` | 清理可重建缓存、暂停预取、降低图片内存缓存、停止后台批处理 | 上报内存压力事件 |
| L3 保留现场 | 清理后仍未回落，或接近 Java Heap 上限 | 在采样命中、前台安全、磁盘充足时触发 heap dump / 专项工具 | 上报快照摘要与触发原因 |
| L4 保护 | 低端机、前台高交互、短时间已 dump、剩余磁盘不足 | 放弃 dump，只保留轻量指标 | 上报放弃原因，避免重复触发 |

主动回收只处理“业务可控资源”。图片内存缓存、页面级大对象、预加载队列、临时 byte buffer、播放器预缓冲、WebView 预热实例，都可以按优先级释放；不应该尝试频繁调用 `System.gc()` 作为常规治理手段。GC 只能处理不可达对象，不能释放仍被缓存或单例持有的对象，频繁触发还会带来停顿。

参考书把 Java Heap 优化拆成减少缓存、按需加载、优化数据结构和释放无效对象，这个顺序适合线上回收策略：先删业务缓存，再降低后续分配，再进入专项分析。[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]

一段端侧判断逻辑要保守，只在连续窗口里触发。下面代码只展示规则形状，不代表阈值可以照搬。

```kotlin
// 示意代码：阈值应按设备档位、进程类型、版本基线动态下发。
private const val WARN_RATIO = 0.75
private const val DANGER_RATIO = 0.88
private const val MIN_CONSECUTIVE_WINDOWS = 3

fun classifyJavaHeapPressure(samples: List<MemorySample>): String {
    val recent = samples.takeLast(MIN_CONSECUTIVE_WINDOWS)
    if (recent.size < MIN_CONSECUTIVE_WINDOWS) return "normal"

    val ratios = recent.map { it.javaHeapUsedKb.toDouble() / it.javaHeapMaxKb }
    val allDanger = ratios.all { it >= DANGER_RATIO }
    val allWarn = ratios.all { it >= WARN_RATIO }

    return when {
        allDanger -> "snapshot_candidate"
        allWarn -> "degrade_cache"
        else -> "normal"
    }
}
```

这段逻辑的判断点在“连续窗口”。一次峰值只记录，连续高位才降级或保留现场。实际工程还要叠加前后台、页面类型、用户交互状态、磁盘容量和远程开关。

[自动发现] `onTrimMemory()` 适合做进程状态和可回收资源信号，不适合单独作为 OOM 预警。Android 14/API 34 起，系统不再向 App 投递 `TRIM_MEMORY_RUNNING_LOW`、`TRIM_MEMORY_RUNNING_CRITICAL`、`TRIM_MEMORY_RUNNING_MODERATE`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 等旧低内存等级；这些常量在 API 35 被废弃。线上策略应把 `TRIM_MEMORY_UI_HIDDEN` / `TRIM_MEMORY_BACKGROUND` 作为缓存收缩时机，把设备级低内存判断交给 `ActivityManager.MemoryInfo` 与自身 PSS / RSS / Java Heap 曲线。详见 20.5 节对 OOM 分类与系统回收路径的讨论。[已验证: 官方文档, developer.android.com/reference/android/content/ComponentCallbacks2; AOSP android-16.0.0_r1, frameworks/base/core/java/android/content/ComponentCallbacks2.java]

## 内存快照（Heap Dump）线上采集方案

线上 heap dump 的目标是保留“足够定位问题”的证据，不是把用户设备变成分析机。直接在主进程里 dump 完整 Hprof 会触发 GC、写大文件并占用 I/O；如果触发时机选错，诊断动作本身会放大卡顿、ANR 或 OOM 风险。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Debug.java] `Debug.dumpHprofData(String)` 调用 `VMDebug.dumpHprofData(fileName)`，源码注释写明它会把 hprof 数据写入指定文件，且可能触发 GC，并可能抛出 `UnsupportedOperationException` 或 `IOException`。

[已验证: 官方文档, developer.android.com/studio/profile/capture-heap-dump] Android Studio 文档建议用 heap dump 查看某个时刻仍占用内存的对象，尤其适合长时间用户会话后识别仍不应存活的对象；文档也说明 Android 的 GC 会短暂停住代码，分配速度超过回收速度会造成跳帧或可见卡顿。

线上方案通常分成四层：

| 层级 | 产物 | 适用场景 | 风险控制 |
|---|---|---|---|
| 轻量指标 | PSS / RSS / Java Heap / Native Heap、页面、前后台、trim level | 默认全量或高采样率 | 控制频率，批量上报 |
| 摘要快照 | top 对象类型、线程数、FD 数、缓存大小、页面历史 | L2 / L3 内存压力 | 不写大文件，适合更多设备 |
| Hprof 文件 | Java Heap dump | Java 泄漏疑似、灰度设备、低频采样 | 远程开关、磁盘配额、前台保护、超时、上传裁剪 |
| 专项工具产物 | KOOM / LeakCanary / native leak 报告 | 已确认某类内存问题集中爆发 | 只对命中版本和设备打开，保留放弃原因 |

Android 15 起，官方提供 app-driven profiling 能力。`ProfilingManager` 可以通过不同 builder 发起 profile 请求，其中 `JavaHeapDumpRequestBuilder` 用于 heap dump，`HeapProfileRequestBuilder` 用于 heap profile；官方文档同时说明系统内置 rate limiter，避免重复 profiling 请求影响设备性能。[已验证: 官方文档, developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture]

Android 10 到 14 的线上 heap dump 仍多依赖 `Debug.dumpHprofData()`、专项 SDK 或 fork dump 方案。fork dump、Hprof 裁剪、引用链摘要这类细节详见 19.3 节 KOOM；这里保留治理约束：

- **触发前检查**：前台高交互、低电量、低剩余内存、磁盘不足、短时间重复触发时放弃。
- **触发后限流**：同设备、同版本、同签名只保留有限样本；失败原因也要上报。
- **文件处理**：Hprof 不直接上传全量，优先裁剪、压缩、加密，只上传引用摘要或问题签名。
- **隐私处理**：对象字符串、图片、用户输入、网络返回体可能出现在 Hprof 中，上传前要做脱敏与白名单过滤。
- **分析归因**：快照必须带 App 版本、构建号、进程、页面、用户路径、设备档位、触发规则和采集耗时。

这一层的治理目标很明确：默认采指标，异常采摘要，少量设备采 dump。把 dump 当成常规监控，会把线上诊断成本转嫁给用户。

## 扩展：采集开销、隐私与发布门禁

[自动发现] 内存监控本身也要进性能预算。`getProcessMemoryInfo()` 会跨进程访问系统服务，PSS 读取来自底层内存映射统计，Android Q 之后平台已经对采样频率做限制；线上探针应使用分钟级或事件触发式采样，Java Heap 这类本进程轻量指标可以更高频。采集线程不能和主线程、渲染线程、启动路径抢资源。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java]

发布门禁不应该只看平均值。更合理的规则是：按设备档位看 P90 / P99，按进程类型看前台主进程、推送进程、WebView 进程，按场景看冷启动后、首页稳定后、长会话后。每个版本都要和上一个稳定版本比较，并保留样本数，样本不足时不能给出强结论。

隐私风险要前置处理。Hprof、对象摘要、页面路径、网络缓存、图片缓存都可能含有用户数据；线上系统默认只上传数值和签名，明文对象内容必须经过白名单和脱敏规则。没有隐私评审和远程关闭能力的 dump 方案，不应进入生产环境。

## 小结

内存监控的有效性取决于指标拆分和触发策略。PSS / RSS 看进程对系统和物理内存的压力，Java Heap / Native Heap 用于判断增长来源，`ActivityManager.MemoryInfo` 提供设备低内存背景信号。线上治理按“指标 → 水位线 → 降级 → 快照 → 专项分析”推进，少量高质量现场比大量单点数值更有用。

<!-- AIW-源码调研-2026-06-11 -->

## 🔬 源码调研发现 (2026-06-11)

### ProfilingManager.java API 验证
经源码级调研验证，Android 14/15 中 **ProfilingManager.java API 在实际AOSP源码中不存在**。章节23.7提到的该API可能属于以下情况之一：

- 该API仅存在于官方文档，未实际实现到AOSP框架层
- 实现后被移除或重命名为其他类名
- 仅在特定厂商分支或mainline模块中存在

**建议：** 如需使用内存跟踪功能，应使用已验证的以下替代方案：

### 实际可用的内存跟踪 API
#### 1. ProfilingServiceManager (Android 15)
- **源码位置：** frameworks/base/core/java/android/os/ProfilingServiceManager.java
- **版本要求：** Android 15 (API 35)，需@FlaggedApi权限
- **功能：** 提供profiling mainline module的系统服务访问接口
- **限制：** 仅在android-15.0.0_r1 tag中存在，未进入Android 17主干

#### 2. ProcessMemoryState 扩展 (Android 14/15)
- **源码位置：** frameworks/base/core/java/android/app/ProcessMemoryState.java
- **功能：** Parcelable数据结构，包含uid/pid/processName/oomScore/hostingComponentTypes
- **增强：** Android 14/15新增HostingComponentType枚举，精确标识进程托管状态

#### 3. GC后内存指标上报控制
- **源码位置：** frameworks/base/core/java/android/app/metrics.aconfig
- **Feature Flag：** report_postgc_memory_metrics (bug 331243037)
- **功能：** 控制垃圾回收后的内存指标数据上报


<!-- AIW-源码调研-2026-06-12 -->

## 🔬 源码调研发现 (2026-06-12)

### 主题：Android 14 高精度内存跟踪 API 与泄漏检测增强机制

> 本节对 AIW §23.7「内存监控与线上治理」进行 AOSP 源码级补充，源码锚点全部来自 `android-14-release` 标签。深度报告见 `DeepResearch/2026-06-12-android14-memory-tracking-apis-leak-detection.md`。

#### 1. `setWatchHeapLimit` + `ACTION_REPORT_HEAP_LIMIT`：PSS 阈值触发的"自动 dump"

这是 Android 14 上最被低估的"泄漏疑似现场保留"能力。`ActivityManager.java` @ android-14-release（L5270-5300）：

```java
public void setWatchHeapLimit(long pssSize) {
    try {
        getService().setDumpHeapDebugLimit(null, 0, pssSize, mContext.getPackageName());
    } catch (RemoteException e) { throw e.rethrowFromSystemServer(); }
}
public static final String ACTION_REPORT_HEAP_LIMIT = "android.app.action.REPORT_HEAP_LIMIT";
public void clearWatchHeapLimit() {
    try { getService().setDumpHeapDebugLimit(null, 0, 0, null); }
    catch (RemoteException e) { throw e.rethrowFromSystemServer(); }
}
```

调用链（`AppProfiler.java` @ android-14-release L879-1000）：
```
App.setWatchHeapLimit(pss) → AMS.setDumpHeapDebugLimit() → AppProfiler.setDumpHeapDebugLimit()
  写入 ProcessMap<Pair<Long,String>> mMemWatchProcesses
  PSS 采样线程命中阈值 → Debug.dumpHprofData() 写到
    content://com.android.shell.heapdump/<procName>_javaheap.bin
  → dumpHeapFinished() → handlePostDumpHeapNotification()
    → 广播 Intent(ACTION_HEAP_DUMP_FINISHED) → App 端 Activity
```

> ⚠️ **API 边界**：仅 `FLAG_DEBUGGABLE` 包或 `userdebug`/`eng` 构建生效，公开 release 包不能依赖它的稳定性。**灰度包/内测包线上取证**是该 API 的最佳使用场景。

#### 2. `ApplicationExitInfo` 在 Android 14 的归因增强

`ApplicationExitInfo.java` @ android-14-release 在主原因枚举上新增 3 档：

| 常量 | 值 | 含义 |
|---|---|---|
| `REASON_FREEZER` | 14 | App Freezer 杀进程（详见 §20.5 冻结） |
| `REASON_PACKAGE_STATE_CHANGE` | 15 | 包状态变更（替代旧 `REASON_USER_REQUESTED`） |
| `REASON_PACKAGE_UPDATED` | 16 | 包更新 |

子原因补到 28（`SUBREASON_SDK_SANDBOX_NOT_NEEDED=28`），**对内存归因最相关**的几个：

- `SUBREASON_LARGE_CACHED=5`（`REASON_OTHER`）：cached 占用大被杀——典型内存压力
- `SUBREASON_MEMORY_PRESSURE=6`（`REASON_OTHER`）：idle 后仍处于低内存
- `SUBREASON_TRIM_EMPTY=4`（`REASON_OTHER`）：empty 进程被 trim
- `SUBREASON_FREEZER_BINDER_IOCTL=19` / `SUBREASON_FREEZER_BINDER_TRANSACTION=20`（`REASON_FREEZER`）：被冻结时 binder 失败——**泄漏分析时必须排除**

线上归因面板推荐用 `ActivityManager.getHistoricalProcessExitReasons(pkg, pid, maxNum)` 取代 `logcat | grep "Killing"` 自解析，关键字段：

```java
info.getReason();        // 主原因
info.getSubReason();     // @hide 反射/系统签名
info.getImportance();    // 退时重要性
info.getPss();           // 退时 PSS（kB）  ← Android 11+ 新增
info.getRss();           // 退时 RSS（kB）  ← Android 11+ 新增
info.getDescription();   // 文本描述
info.getIntent();        // 启动 Intent 备份
```

#### 3. Native 侧 API 34 新增 `M_PURGE_ALL`

`bionic/libc/include/malloc.h` @ android-14-release 在 API 34 新增：

```c
/* Available since API level 34. */
#define M_PURGE_ALL (-104)   // 比 M_PURGE 扫描面更广，耗时通常 2x
```

Scudo 专属（jemalloc 设备不生效），只能在**后台线程**调用，开销 50-200 ms。Heap Tagging 等级 `M_HEAP_TAGGING_LEVEL_*`（NONE/TBI/ASYNC/SYNC）保持 API 31 引入，API 34 未新增 level 常量。

#### 4. `Debug.MemoryInfo` 分桶精度

`Debug.java` @ android-14-release（L116-450）维持 9 类分桶（`dalvikPss/nativePss/otherPss + swappable/rss/privateDirty/...`）+ 9 个 `NUM_CATEGORIES` 的 otherStats 数组。**`getTotalPss()` 等派生字段单位是 kB**（不是 byte），线上与 PSS 基线对比时注意单位换算。

`getProcessMemoryInfo(int[])` 行为约束（API 30 维持到 14）：仅同 uid 可见；采样频率被系统节流，**线上应取 1-5 分钟级**而非秒级。

#### 5. 迁移路径建议

| 旧实践 | Android 14 推荐 | 理由 |
|---|---|---|
| `logcat` grep `Killing` 自解析 | `getHistoricalProcessExitReasons()` | 拿到结构化 REASON/SUBREASON + PSS/RSS |
| `TRIM_MEMORY_RUNNING_LOW` 单独做 OOM 预警 | `MemoryInfo.lowMemory` + 自有 PSS 曲线 | 旧等级在 API 35 废弃 |
| 公开 release 触发 `Debug.dumpHprofData()` | 灰度包 `setWatchHeapLimit` + 公开 release 走 LeakCanary/KOOM | 灰度包走系统 dump，release 走自管 |
| `Runtime.getRuntime().gc()` 做"主动回收" | 业务缓存清理 + `M_PURGE`/`M_PURGE_ALL` | GC 不能释放仍可达对象，频繁触发带来停顿 |

#### 6. API 等级与版本差异速查

| 能力 | 引入版本 | 14 状态 |
|---|---|---|
| `Debug.MemoryInfo` 9 类分桶 | API 1 | 维持 |
| `setWatchHeapLimit` | API 26 | 维持（仅 debug/eng） |
| `ApplicationExitInfo` PSS/RSS 字段 | API 30 | 维持 |
| `ApplicationExitInfo` 新 REASON 14/15/16 | API 34 | **新增** |
| `M_PURGE_ALL` | **API 34** | **新增** |
| `M_HEAP_TAGGING_LEVEL_*` | API 31 | 维持 |
| `RateLimitingCache` 包裹 `getMemoryInfo` | main 分支（API 36+） | **未在 14 默认开启** |

> 报告全文与代码引用见 `DeepResearch/2026-06-12-android14-memory-tracking-apis-leak-detection.md`。
