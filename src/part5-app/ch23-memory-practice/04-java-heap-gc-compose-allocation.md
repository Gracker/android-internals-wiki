---
title: Java Heap、GC 与 Compose 内存分配
chapter: '23.4'
section: '23.4'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: Android 17 / API 37 / AOSP android-17.0.0_r1；ART Heap、ComponentCallbacks2、ProfilingTrigger 与 Android 内存管理官方文档
last_review_finalize_at: '2026-08-15T07:29:18+08:00'
last_review_finalize_run_id: 20260815-072918-gracker-writing-review
confidence: high
sources:
- type: official
  path: https://developer.android.com/topic/performance/memory
- type: official
  path: https://developer.android.com/topic/performance/memory-overview
- type: official
  path: https://developer.android.com/topic/performance/memory-management
- type: official
  path: https://developer.android.com/reference/android/content/ComponentCallbacks2
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java
- type: official
  path: https://developer.android.com/studio/profile/capture-heap-dump
- type: official
  path: https://developer.android.com/studio/profile/record-java-kotlin-allocations
- type: aosp
  path: https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/util/LruCache.java
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]'
- type: official
  path: https://developer.android.com/topic/performance/vitals/render
- type: official
  path: https://developer.android.com/studio/profile/memory-profiler
- type: official
  path: https://source.android.com/docs/core/runtime/gc-debug
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://developer.android.com/about/versions/16/qpr2/release-notes
- type: official
  path: https://developer.android.com/about/versions/17/release-notes
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/libart/src/main/java/java/lang/Daemons.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/task_processor.cc
- type: research
  path: DeepResearch/2026-06-19-jetpack-compose-memory-churn-source-analysis.md
- type: official
  path: https://developer.android.com/jetpack/compose/performance
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/compose-runtime
- type: official
  path: https://developer.android.com/develop/ui/compose/performance/bestpractices
- type: official
  path: https://developer.android.com/develop/ui/compose/performance/stability/strongskipping
- type: official
  path: https://developer.android.com/develop/ui/compose/performance/stability/diagnose
- type: official
  path: https://developer.android.com/develop/ui/compose/lists
- type: official
  path: https://developer.android.com/develop/ui/compose/tooling/tracing
- type: official
  path: https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views
- type: official
  path: https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动？.md]'
tags:
- java-heap
- object-pool
- gc-friendly
- collection-optimization
- memory-churn
- gc
- allocation
- autoboxing
- compose
- memory
- slottable
- recomposition
related_chapters:
- '23.1'
- '23.2'
- '23.5'
- '23.6'
- '4.2'
- '4.6'
- '10.2'
- '7.1'
- '22.3'
pipeline_stage: finalized
last_draft_polish_at: '2026-08-15T07:29:18+08:00'
last_draft_polish_run_id: 20260815-072918-gracker-writing
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
- src/part5-app/ch23-memory-practice/23.26-art-heap-distribution-oom-trigger-path.md
- src/part5-app/ch23-memory-practice/23.6-heaptask-concurrent-gc-suppression.md
- src/part5-app/ch23-memory-practice/12-compose-memory-allocation-gc.md
- src/part5-app/ch23-memory-practice/04-java-heap-optimization.md
- src/part5-app/ch23-memory-practice/05-memory-churn-gc.md
- src/part5-app/ch23-memory-practice/08-compose-memory-allocation-gc.md
last_consolidated_at: '2026-08-24'
---

# Java Heap、GC 与 Compose 内存分配

> **版本基线**
>
> 平台行为与源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。涉及旧版本的内容只说明 API 或行为变化，不高于 Android 17。

Java Heap 优化先控制对象生命周期和存活集，再处理高频分配造成的 GC 抖动。Compose 会在重组、布局和绘制阶段创建临时对象，需要结合状态稳定性和分配调用栈定位。

## 对象生命周期、存活集与缓存边界

### Java 堆优化解决什么问题

Java 堆优化处理应用侧对象分配、对象生命周期和缓存预算之间的关系。[23.1 内存泄漏检测与治理](01-memory-leak-governance.md)处理“该释放的对象没有释放”，[23.2 Bitmap 与图片内存优化](02-bitmap-optimization.md)处理像素内存；本文关注另一类堆压力：对象仍有业务价值，但分配时机、集合规模、缓存策略或临时对象频率让占用或回收成本升高。

Android 会为每个应用进程设置 Java 堆上限，无法在限制内完成分配时会抛出 `OutOfMemoryError`。Android Studio 的 Memory Profiler（内存分析器）可以观察堆曲线、对象数量和 GC 事件。工程判断不能只看一次 `Runtime.maxMemory()`：还要比较同一场景的分配速度、峰值、退出后的存活对象和 GC 行为。堆曲线回落只说明对象具备被回收的条件，不代表页面已经满足性能目标；曲线没有立即回落，也可能是 ART 保留可复用堆空间，而不是对象仍被引用。

[4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md)解释堆空间、分配器和 GC；[4.6 ART FinalizerDaemon、Cleaner 与 ReferenceQueue](../../part1-fundamentals/ch04-memory/06-finalizer-referencequeue.md)解释延迟清理与引用队列；[23.4 Java Heap、GC 与 Compose 内存分配](04-java-heap-gc-compose-allocation.md)讨论高频分配和暂停证据。应用侧的基本动作是减少或推迟分配、按预算缓存，并在生命周期边界释放不再需要的引用。

文中术语含义如下：

| 术语 | 本文含义 |
| --- | --- |
| Java Heap / Native / PSS | Java Heap 是 ART 管理的对象堆；Native 是 C/C++ 分配、映射等原生内存；PSS 按共享者数量分摊物理页。三者口径不同。 |
| ART / GC / collector / mutator | ART 是 Android Runtime；GC 是垃圾回收；collector（收集器）是具体回收算法；mutator（应用线程）会读写对象图，并可能在 GC 的部分阶段暂停。 |
| space / allocator | space（堆空间）是 ART 管理对象的逻辑区域；allocator（分配器）决定如何从相应区域取得内存。 |
| Region Space / Bump Pointer Space / Large Object Space | 这些是 ART 堆空间的源码名称：Region Space 按区域管理对象，Bump Pointer Space 通过移动分配指针取得连续空间，Large Object Space（LOS，大对象空间）处理满足内部条件的大对象。 |
| growth limit / capacity / target footprint | growth limit 是当前 Java 堆增长限制；capacity 是可扩展的最大容量；target footprint 是 ART 根据回收结果调节的目标堆大小，不是硬上限。 |
| OOM / OOME | OOM 表示无法满足内存请求的状态；OOME 是 Java 异常 `OutOfMemoryError` 的简称。 |
| heap dump / allocation recording | heap dump（堆转储）记录某一时刻的对象和引用；allocation recording（分配记录）记录一段时间内的分配次数、大小与调用栈。 |
| shallow size / retained size | shallow size 是对象自身占用；retained size 还包括只通过该对象保持可达、移除这条引用后可一并回收的对象。 |
| LRU / trim | LRU 是“最近最少使用”淘汰顺序；trim 表示根据进程状态或系统提示主动缩减可重建资源。 |
| FD / VMA | FD 是文件描述符；VMA 是进程的一段虚拟内存区域。FD、VMA 或地址空间耗尽也可能表现为分配失败。 |
| profiling trigger / artifact / handler | profiling trigger 是满足条件后由系统启动诊断采集的触发器；artifact 是返回的堆转储、跟踪等诊断产物；handler 是接收或处理异常、结果的回调。 |

源码、错误日志和工具界面使用的英文名称会保留，通用概念同时给出中文含义，便于把文章与实际诊断数据对应起来。

### Java 堆空间组成与分配策略

应用代码创建的对象不会全部进入同一种 ART 堆空间。普通对象走哪条分配路径，取决于当前收集器和分配器配置，可能涉及 Region Space、Bump Pointer Space 或其他连续空间；应用不能把它简化为固定的“Main Space”。特定对象达到内部阈值后，ART 还会尝试从 Large Object Space 分配。

Android 17 的 `Heap::ShouldAllocLargeObject()` 同时检查两个条件：分配字节数达到 `large_object_threshold_`，并且对象类型是基本类型数组或 `String`。满足条件时，分配器会尝试 `AllocLargeObject()`；如果 Large Object Space 分配失败，源码会清除本次 OOM 异常，再尝试主空间或非移动空间。这个阈值是 ART 内部配置，不是应用 API，业务代码不应复制一个固定数值作为分支条件。

体积较大的 `ByteArray`、`IntArray` 或字符串构造结果，除了增加存活字节数，还可能进入不同的分配与回收路径。优化动作仍应从数据形态入手：能否分块读取、缩短生命周期或避免复制，而不是依据 Large Object Space 名称写特殊业务分支。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap-inl.h::Heap::ShouldAllocLargeObject()`, `art/runtime/gc/heap-inl.h::Heap::AllocObjectWithAllocator()`]

堆上限不等于进程物理内存占用。`Heap::GetMaxMemory()` 对应 `Runtime.maxMemory()`；普通 Android 应用受 `growth_limit_` 限制，声明 `largeHeap` 后会把限制扩展到堆的 `capacity_`。`GetFreeMemoryUntilOOME()` 用 `growth_limit_` 与当前已分配字节数估算 OOM 前的余量。PSS 还包含 Java 堆之外的映射和按比例计入的共享页，必须与逻辑堆值分开分析。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap.h::GetMaxMemory()`, `GetFreeMemoryUntilOOME()`]

应用侧判断堆压力时，可以用三组数：

- `Runtime.maxMemory()`：当前进程 Java 堆上限，是制定缓存预算的输入之一，不能直接乘固定比例得出所有设备通用的预算。
- `Runtime.totalMemory() - Runtime.freeMemory()`：ART 当前已使用 Java 堆的近似值，适合在同一构建、同一设备上观察趋势。
- heap dump（堆转储）/ allocation recording（分配记录）：前者观察快照时仍然存活的对象与引用链，后者观察目标窗口内的分配次数、大小和调用栈。采集本身有成本，应放在可控诊断流程中。

下面的工具函数把堆使用量转换为轻量信号。阈值由调用方传入，要求来自目标设备与业务场景的测量；代码不提供一个看似通用的默认比例。

```kotlin
object JavaHeapPressure {
    data class Snapshot(
        val maxBytes: Long,
        val usedBytes: Long,
        val usedRatio: Double
    )

    fun snapshot(): Snapshot {
        val runtime = Runtime.getRuntime()
        val maxBytes = runtime.maxMemory()
        val usedBytes = runtime.totalMemory() - runtime.freeMemory()
        return Snapshot(
            maxBytes = maxBytes,
            usedBytes = usedBytes,
            usedRatio = usedBytes.toDouble() / maxBytes.coerceAtLeast(1L)
        )
    }

    fun shouldTrimCache(threshold: Double): Boolean {
        require(threshold in 0.0..1.0)
        return snapshot().usedRatio >= threshold
    }
}
```

这段代码只能提供趋势信号。它不知道对象是否可回收，也不包含 Native（原生内存）、Graphics（图形内存）等进程分区；单次超过阈值不能证明泄漏。生产监控若采用该信号，还要限制采样频率、合并连续事件，并同时记录场景与缓存命中变化。

### ART 分配失败与 OOM 触发路径

普通对象的快速分配失败后，`Heap::AllocateInternalWithGc()` 不会立即抛出 OOME。Android 17 会先等待正在运行的 GC；等待期间完成过回收时重试分配；随后按 `next_gc_type_` 执行阻塞式 GC，也就是由分配线程发起并等待完成的回收。仍未取得足够空间时，ART 会执行覆盖整个堆的回收，并清除 SoftReference（内存不足时允许 GC 清除的软引用）。部分分配器在配置启用且达到时间间隔后，还会尝试 homogeneous space compaction（同构空间压缩），即在两个同类堆空间之间复制对象以整理碎片。以上尝试都失败后才抛出 OOME。

这里不存在设备无关的“Young GC（年轻代回收）→ Full GC（全堆回收）”固定两步顺序。`next_gc_type_` 取决于收集器、代际状态、上次 GC 和目标堆大小。分配线程也可能主要耗时在等待另一线程执行 GC，因此 Perfetto 中看到的业务停顿可能长于单次 GC 暂停。

#### 读懂 OOME 文本

Android 17 的典型错误会列出本次请求大小、堆空闲字节数、距离 OOM 的余量、目标堆大小和增长限制：

```text
Failed to allocate a 48 byte allocation with 3610680 free bytes and
3526KB until OOM, target footprint 536870912, growth limit 536870912;
giving up on allocation because <1% of heap free after GC.
```

- `free bytes` 是 ART 统计的堆空闲总量，不保证目标分配器有合适的连续块；
- `until OOM` 是距离 `growth limit` 的估算增长空间；
- `target footprint` 是当前调节目标，会随 GC 和分配变化，不是硬上限；
- `growth limit` 是普通应用 Java 堆的增长限制；
- `<1% ... after GC` 表示完成本次分配后无法保留运行时要求的最小空闲比例。

小对象也可能在堆接近限制时失败；大数组失败还要检查输入尺寸、乘法溢出和连续空间。ART 构造 OOME 时若再次分配失败，会使用启动阶段预分配的异常对象，因此生产日志不一定每次都有完整错误文本。OOM 异常处理器中也不要再创建大集合或同步抓取完整堆转储。

#### 先区分四种“内存不足”

| 现场 | 主要证据 | 排查方向 |
| --- | --- | --- |
| Java 堆 OOM | `Failed to allocate`、对象存活集、`growth limit` | 泄漏、业务仍需保留的对象、短时间频繁分配和回收、单次大对象 |
| 原生分配失败 | `malloc` / `mmap` 错误、原生调用栈、PSS/VMA | 分配器、匿名映射、Graphics、请求大小 |
| 线程创建失败 | `pthread_create (... stack) failed`、线程数、`errno` 错误码 | 每线程栈、VMA、原生内存、系统任务数限制 |
| FD / 地址空间耗尽 | `EMFILE` / `ENOMEM`、FD/VMA 数量、最大连续空闲区 | 资源关闭、32 位地址空间、线程与映射数量 |

原生分配失败只有部分 Android 框架层或 JNI（Java 原生接口）入口会转换为 Java OOME；FD 用尽通常直接返回 `EMFILE`。不能把所有带 `OutOfMemoryError` 或 `ENOMEM` 的现场都归入 ART 对象泄漏。

#### 不修改 ART 内部计数来“扩堆”

`largeHeap` 只扩展 Java 堆的 `growth limit`，不增加设备物理内存，也不处理原生内存、Graphics、线程栈或无界缓存。修改 `num_bytes_allocated_`、`large_object_threshold_`，伪造已释放字节数，拦截分配器以绕过 GC，或解除 ART 堆空间映射，会破坏分配计数、对象存活位图、card table（记录跨区域引用的卡表）、对象所属空间和 GC 根集合之间的一致性，不能用于生产环境。Android 17 的 LOS 也没有为应用提供固定保留 512 MiB 空间的接口。

### 大对象与集合优化

大对象优化先从减少一次性装入开始。服务端返回几 MB JSON、一次性读取完整文件、把长日志拼成一个 `String`、把列表全量转换成界面状态模型，都会让 Java 堆压力集中在一个短窗口内。GC 能回收不可达对象，但它不能替业务决定哪些数据不该一次性加载。

处理大对象时按这个顺序排查：

- **输入是否可以分页或流式处理**：列表接口、文件读取、日志解析优先改为分页、分块或流式处理，不把完整数据一次性放进内存。
- **中间态是否可以消除**：JSON 字符串、DTO（数据传输对象）、领域模型、UI 模型发生多层复制时，检查是否能在边界处直接转换，少保留一份大集合。
- **字符串构造是否有上限**：日志、埋点、调试面板不要无限拼接；给字符串构建器设置长度上限，超过后截断或写入文件。
- **数组容量是否按需增长**：已知数量时可以传入合理的初始容量；未知数量时不应凭空预留大数组。只有剖析表明扩容复制或长期空余容量形成主要成本时，才值得更换容器或重建紧凑副本。

集合优化不能停在“换一个集合类”。`ArrayList`、`HashMap`、`SparseArray`、`ArrayMap` 的选择依据是元素数量、键类型、访问模式、写入频率和生命周期。整数键可以避免 `HashMap<Int, ...>` 把 `Int` 包装成对象的装箱成本，但是否使用 `SparseArray` 仍要结合 CPU 与内存测量。不要写一个固定的元素数量分界线，因为设备、访问模式和实现版本都会改变结果。

下面的示例适用于数据能够以 Kotlin `Sequence`（惰性序列）提供、且只需要前 `limit` 个结果的场景。它避免由 `filter()` 和 `map()` 各自产生一份完整中间列表。

```kotlin
data class RawItem(val id: Long, val title: String, val score: Int)
data class UiItem(val id: Long, val title: String)

fun buildVisibleItems(
    source: Sequence<RawItem>,
    minScore: Int,
    limit: Int
): List<UiItem> {
    return source
        .filter { it.score >= minScore }
        .take(limit)
        .map { UiItem(id = it.id, title = it.title) }
        .toList()
}
```

收益主要来自 `take(limit)` 限制结果数量，以及惰性操作避免完整中间集合。`Sequence` 自身也会创建操作包装对象并增加迭代调用；如果源数据已经完整驻留，或集合很小，它未必更省时。应使用分配记录与基准测试，同时比较分配字节数、对象数和 CPU 时间。

### 对象池与缓存策略

对象池和缓存都在用空间换时间，目标并不相同。对象池减少重复分配，缓存减少重复计算或重复 I/O（输入输出）。两者都要有上限、失效条件和生命周期归属，否则原本的优化会变成常驻内存。

缓存预算不能只按“最大堆的固定比例”决定。要同时测量对象大小、峰值并发、重建成本、命中收益和设备内存档位：首屏与高频路径可以保留有界缓存，低频内容更适合缩小容量或在离开场景时移除。弱引用的回收时机由 GC 决定，不能替代容量和淘汰策略。

`onTrimMemory()` 需要区分进程状态提示与内存压力提示。`TRIM_MEMORY_UI_HIDDEN` 表示界面已不可见，`TRIM_MEMORY_BACKGROUND` 表示进程进入后台 LRU 队列，它们适合触发与相应状态相关的缓存收缩。从 API 34 开始，`TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE` 和 `TRIM_MEMORY_COMPLETE` 不再投递给应用，`onLowMemory()` 也不再调用；这些常量和方法从 API 35 起标记为弃用。因此，Android 17 应用不能等待旧的前台运行级别回调或 `onLowMemory()` 来处理内存压力。

下面的 `LruCache` 示例缓存原始字节内容，使 `sizeOf()` 至少能精确计算值的字节数；收到界面隐藏或进入后台的提示后，再按业务策略把当前缓存收缩到目标字节数。`trimToSize()` 不会永久修改构造时传入的最大容量，后续写入仍可能让缓存重新增长。

```kotlin
class BytePayloadCache(
    maxBytes: Int,
    private val uiHiddenBytes: Int,
    private val backgroundBytes: Int
) : LruCache<String, ByteArray>(maxBytes) {
    init {
        require(backgroundBytes in 0..uiHiddenBytes)
        require(uiHiddenBytes <= maxBytes)
    }

    override fun sizeOf(key: String, value: ByteArray): Int {
        return value.size
    }

    fun trimFor(level: Int) {
        when {
            level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> trimToSize(backgroundBytes)
            level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> trimToSize(uiHiddenBytes)
        }
    }
}
```

这里的计量仍未包含键字符串、`LruCache` 缓存条目和对象头（ART 为对象保存的类型、锁状态等元数据）开销，所以 `maxBytes` 只表示 `ByteArray` 内容的字节预算，不是整个缓存的 shallow size（对象自身占用）。字符串、图片引用和解析对象需要各自的计量口径。两个收缩预算由调用方根据业务测量传入，示例没有设置通用比例。兼容 API 33 及以下时可以处理旧的运行级别，但 Android 17 路径不应依赖这些不会到达的回调。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/content/ComponentCallbacks2.java`, `frameworks/base/core/java/android/util/LruCache.java`]

对象池只适合满足三个条件的对象：创建频繁、初始化成本高、可安全重置。普通 Kotlin `data class`（数据类）、生命周期复杂的对象、持有 `Context`、View 或回调的对象，不建议放进池。池化后的对象一旦忘记清除字段，可能引入泄漏和残留数据。

对象池还要与 ART 分代 GC 分开评估：ART 对短命小对象的分配路径通常开销较低，强行池化会把短命对象变成长命对象，增加老年代压力。只有分配热点造成了可观测的 GC 或 CPU 压力，池化才有继续评估的价值。分代和分配路径见 [4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md)，卡顿证据见 [23.4 Java Heap、GC 与 Compose 内存分配](04-java-heap-gc-compose-allocation.md)。

### 更适合 GC 的编码实践

更适合 GC 的代码会让分配符合场景节奏：启动、首帧、滑动、动画和输入响应期间减少短时间高峰；页面退出、切到后台或收到系统收缩提示时释放可重建资源；后台任务和低优先级计算不要与前台帧争抢资源。

可执行的检查项有这些：

- **启动阶段控制初始化范围**：只创建首屏和启动链依赖的对象。延迟初始化是否移到后台线程，要同时检查线程安全、I/O 和 CPU 竞争；“后台执行”不会消除分配成本。
- **滑动阶段少建临时对象**：`onBindViewHolder()`、`onDraw()`、触摸回调里避免格式化字符串、创建临时集合、重复构造匿名对象。高频回调里的分配要用分配记录验证。
- **批处理阶段控制峰值**：大量数据转换分批执行，每批结束释放中间态。协程或线程池只是调度工具，不会自动降低堆峰值。
- **生命周期边界清理长生命周期引用**：例如 Fragment 在 `onDestroyView()` 清理 ViewBinding，以及与 View 生命周期绑定的适配器和回调。不要机械地清除仍由下一状态使用的数据；引用归属应与生命周期一致。
- **监控对象数量和 GC 事件**：Memory Profiler 能显示 Java 对象数量与 GC 事件；生产环境的轻量监控只保留趋势指标，定位问题时再在可控环境采集堆转储和分配记录。

下面的写法把 `NumberFormat` 的构造移出重复绑定路径。它仍然会为展示结果创建 `String`；优化范围是避免反复创建格式器，不是让绑定过程零分配。

```kotlin
data class GoodsItem(
    val title: String,
    val priceFen: Long
)

class PriceFormatter(
    private val numberFormat: NumberFormat = NumberFormat.getCurrencyInstance(Locale.CHINA)
) {
    fun formatFen(fen: Long): String {
        return numberFormat.format(fen / 100.0)
    }
}

class GoodsRowBinder(
    private val titleView: TextView,
    private val priceView: TextView,
    private val formatter: PriceFormatter
) {
    fun bind(item: GoodsItem) {
        titleView.text = item.title
        priceView.text = formatter.formatFen(item.priceFen)
    }
}
```

`NumberFormat` 不是线程安全对象，`GoodsRowBinder` 和 `PriceFormatter` 应限制在 RecyclerView 所在的主线程使用。把所有临时对象都改成成员会延长生命周期，可能增加长命对象数量。判断改动是否有效，要同时比较绑定阶段的分配次数、GC 事件和帧耗时。

### ART GC 调优参数

`growth_limit_`、`target_footprint_`、`concurrent_start_bytes_`、`large_object_threshold_` 等变量解释了 ART 何时扩展堆、何时触发并发 GC、哪些对象走大对象路径，但它们不是面向普通应用公开的配置接口，不能作为常规调优手段。

`android:largeHeap="true"` 会让 ART 把应用的 `growth limit` 扩展到堆的 `capacity`，但容量仍由设备配置决定。它不会消除泄漏、无上限缓存或大对象峰值，也不保证某个固定的额外容量。只有图片编辑、大文档处理、地图或创作工具等经过测量后仍有合理大内存需求的业务，才值得单独评估；同时要观察进程 PSS、后台存活和低内存终止情况。

GC 抑制和 ART 接口拦截（Hook）依赖非公开实现，会受 ART 更新、线程协作和 GC 时序影响，不适合作为通用应用方案。应用侧应修正启动、滑动与批处理期间的分配热点，不要阻塞执行 GC 与堆维护任务的 `HeapTaskDaemon`，也不要修改 ART 内部状态。

评审时可以用下面的表格判断方案边界：

| 方案 | 适用场景 | 风险 |
| --- | --- | --- |
| 降低缓存预算 | 大多数应用 | 命中率下降，需要业务指标一起看 |
| 按 `onTrimMemory()` 状态释放 | UI 隐藏、进入后台 LRU | 释放过多会导致回到前台后重新加载 |
| 分页 / 流式处理 | 大列表、大文件、大响应 | 改造成本取决于接口和数据模型 |
| 对象池 | 高频、可重置、初始化贵的对象 | 脏字段、泄漏、老年代压力 |
| `largeHeap` | 明确需要大内存的少数场景 | 掩盖问题，增加系统内存压力 |
| ART 非公开接口拦截 / GC 抑制 | 专项实验或受控系统框架 | 版本兼容、稳定性和审核风险高 |

常规应用先调整缓存预算、数据加载方式和生命周期。`largeHeap` 需要用设备分档数据证明必要性；修改 ART 内部行为只适合具备系统控制权的受控实验。

### 排查路径：从堆曲线到代码改动

Java 堆优化可以按四步推进：

1. 用 Memory Profiler 录制目标场景，记录对象数量、堆曲线和 GC 事件。
2. 如果曲线持续上升且页面退出后不回落，转到 [23.1 内存泄漏检测与治理](01-memory-leak-governance.md)。
3. 如果曲线有尖峰但能回落，检查大对象、集合复制、缓存预算和批处理峰值。
4. 如果 GC 频率高且伴随卡顿，转到 [23.4 Java Heap、GC 与 Compose 内存分配](04-java-heap-gc-compose-allocation.md)，再根据分配证据减少热点。

Android 17 / API 37 为 `ProfilingTrigger` 增加 `TRIGGER_TYPE_OOM` 和 `TRIGGER_TYPE_ANOMALY`。OOM 触发器会在未捕获的 `OutOfMemoryError` 现场采集 Java 堆转储；应用下次启动并注册结果回调后，可以取得这份诊断结果。自定义 `Thread.UncaughtExceptionHandler` 必须继续调用默认异常处理器，系统才能观察到该事件。anomaly（系统异常行为）触发器覆盖内存用量超限等情况，但诊断产物由异常类型决定：超过 Android 17 内存限制时可返回堆转储，其他异常可能返回不同类型的跟踪或采样数据。触发式采集用于取得难以在本地复现的证据，不能替代堆预算和代码修正。生产监控见 [23.6 内存监控与线上治理](06-memory-monitoring.md)，Android 17 内存限制见 [23.5 大内存与多进程策略](05-large-heap-multiprocess.md)。

一次有效改动至少要回答三件事：分配对象数或字节数是否下降，峰值或稳定占用是否改善，CPU、I/O、网络请求与用户场景指标是否变差。只降低 Java 堆峰值却增加其他资源成本，不能视为完成优化。

## 高频分配、晋升与 GC 抖动

存活对象决定 Heap 基线，短命对象的创建速率决定回收频率。优化时要分别观察分配量、存活量和暂停。

> **版本基线**
>
> 平台实现统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。历史版本只用于说明 collector 和工具能力的演进，最高版本为 Android 17。

### 内存抖动需要解决什么

内存抖动指短时间内反复分配对象，对象很快失去引用，又持续增加回收工作的现象。泄漏会让不再需要的对象长期保持可达，抖动对象通常能被回收，两种问题也可能同时出现。[23.4 Java Heap、GC 与 Compose 内存分配](04-java-heap-gc-compose-allocation.md)解释堆预算与缓存控制，[10.3 内存抖动与频繁 GC](../../part2-performance/ch10-memory-perf/03-memory-churn.md)和 [4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md)给出运行时与工具原理，[7.1 卡顿定义、分类与原因体系](../../part2-performance/ch07-smoothness/01-jank-definition-causes.md)说明慢帧的其他来源。本文聚焦应用侧如何降低启动、首帧、滑动和动画期间的分配峰值。

ART 的并发收集器缩短了许多暂停，但分配、标记、复制或压缩仍要消耗 CPU 和内存带宽，部分阶段仍需暂停应用线程。应用分配速度超过回收与堆扩展能力时，分配线程还可能等待 GC 完成。GC 时间片与慢帧同时出现只能建立相关性；主线程暂停、分配等待或与 GC 线程竞争 CPU 才能解释具体影响。

拦截 `libart.so` 或阻塞 `HeapTaskDaemon` 会破坏 ART 的回收时序，并依赖非公开 ABI。应用侧应从系统跟踪和分配调用栈找到高频分配位置，缩短无用中间对象的生命周期，控制单次处理范围，再验证 GC 与慢帧是否同步改善。

文中术语含义如下：

| 术语 | 本文含义 |
| --- | --- |
| allocation churn / heap baseline | allocation churn 是内存抖动；heap baseline 是每轮 GC 后仍保留的堆基线，用于区分可回收波动和持续增长。 |
| ART / GC / collector / mutator | ART 是 Android Runtime；GC 是垃圾回收；collector（收集器）是具体回收算法；mutator 是执行应用代码并读写对象图的线程。 |
| CC / CMC / generational GC | CC 是 Concurrent Copying（并发复制）；CMC 是 Concurrent Mark-Compact（并发标记压缩）；generational GC（分代回收）优先处理较新的对象。 |
| allocation call stack / TLAB | allocation call stack 是对象创建时的分配调用栈；TLAB 是线程本地分配缓冲区，让线程从自己的小块空间快速分配对象。 |
| trace / track / slice / wall time | trace 是系统跟踪；track 是某类线程或事件的时间轨道；slice 是有起止时间的一段工作；wall time 是包含执行与等待在内的经过时间。 |
| Frame Timeline / missed / slow / present | Frame Timeline 是 Perfetto 的帧时间线；missed 表示没有按时呈现，slow 表示耗时偏长，present 表示帧的显示结果。 |
| Running / Runnable / Sleeping / Blocked | Running 表示正在 CPU 上执行；Runnable 表示已就绪但尚未获得 CPU；Sleeping 和 Blocked 表示睡眠或阻塞等待。 |
| PSS | Proportional Set Size，按共享者数量分摊共享页后的物理内存统计，不能用 Java 对象分配字节数直接换算。 |
| RenderThread / Binder | RenderThread 是 Android 界面渲染线程；Binder 是 Android 的进程间通信机制。两者都可能与 GC 同时消耗 CPU 或形成等待。 |
| GC cause | 日志与跟踪中的 GC 触发原因，例如后台请求、分配失败或原生分配压力；它不等同于收集器名称。 |
| Zygote / fork / post-fork / UID | Zygote 是应用进程模板；fork 是从模板复制新进程；post-fork 是复制后的初始化阶段；UID 是系统区分应用身份的用户编号。 |
| HeapTaskDaemon / HeapTask | HeapTaskDaemon 是 ART 串行执行堆维护任务的守护线程；HeapTask 是队列中的 GC、堆收缩或阈值检查任务。 |
| Handle | ART 的 Handle 是可由运行时更新的临时对象引用；移动式 GC 改变对象地址后，Handle 仍能指向新地址。 |
| heap dump / allocation profile / retention graph | heap dump（堆转储）给出某一时刻的存活对象；allocation profile（分配画像）记录一段时间内的创建调用栈；retention graph（保留关系图）描述对象为何仍可达。 |
| native hook / ABI / vtable | native hook 是拦截原生函数；ABI 是二进制调用约定；vtable 是 C++ 动态分派虚函数的表。三者都属于实现细节，不是应用 API。 |
| autoboxing / recomposition | autoboxing（自动装箱）把 `Int` 等基本值包装成对象；recomposition（重组）是 Compose 在状态变化后重新执行相关界面代码。 |

这些名称会出现在源码、日志和 Perfetto 界面中；保留原名有助于检索，中文释义用于明确它们在排查中的作用。

### 内存抖动的成因与表现

内存抖动同时受分配大小、分配频率和对象存活时间影响。大量小对象会迅速增加累计分配字节数，大对象则可能直接形成峰值；只按对象大小排序会漏掉高频调用栈。

Android 17 的 `Heap::AllocObjectWithAllocator()` 在分配记账后调用 `ShouldConcurrentGCForJava(new_num_bytes_allocated)`。启用按时间触发 GC 的功能开关且 `time_based_gc_threshold_` 非零时，该函数结合上次 GC 后新增的字节数与经过时间，决定立即请求 GC，还是安排一次阈值复查；`concurrent_start_bytes_` 仍是接近堆限制时的兜底阈值。未启用这条路径时，判断只比较已分配字节数与 `concurrent_start_bytes_`。对象完成初始化并可交给应用代码后，`RequestConcurrentGCAndSaveObject()` 才把 `ConcurrentGCTask` 加入队列。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap-inl.h::Heap::AllocObjectWithAllocator()`, `Heap::ShouldConcurrentGCForJava()`, `art/runtime/gc/heap.cc::Heap::RequestConcurrentGC()`]

从应用层来看，内存抖动通常表现为四种现象：

- **堆曲线呈锯齿状**：内存快速上升，GC 后又下降，周期很短。单次峰值可能不高，但回收频率高。
- **Logcat 或系统跟踪里 GC 密集**：`HeapTaskDaemon` 活跃，Perfetto 或旧版 Systrace 能看到多个 GC 时间片集中在交互窗口附近。
- **帧耗时波动**：Frame Timeline 里的慢帧可能间隔出现，并集中在滑动、动画或连续输入期间。
- **分配慢路径或等待**：线程在分配时等待 GC 完成，或进入需要扩展、回收的慢路径。业务函数自身的 CPU 执行时间可能不高，但包含等待的经过时间会变长。

Android 8 起，ART 默认使用 Concurrent Copying；官方 GC 文档说明 Android 10 及以上的 CC 默认采用分代模式。Android 16 QPR2（第二次季度平台更新）对外发布分代 CMC，Android 17 源码继续保留相应的年轻代收集器和运行时开关。具体进程使用哪种收集器、是否启用分代，仍取决于运行时和设备配置；Android 17 的 `PostForkChildAction()` 会在日志中输出 `generational` 或 `non-generational` 以及收集器名称，可与系统跟踪一起确认。

### 频繁 GC 对帧率的影响

GC 对帧率的影响主要来自两类成本：部分阶段短暂停顿应用线程，以及后台 GC 线程与渲染线程竞争 CPU。AOSP `Daemons.java` 中的 `HeapTaskDaemon` 会调用 `VMRuntime.getRuntime().runHeapTasks()`；`TaskProcessor::RunAllTasks()` 从队列取出 `HeapTask` 并执行。Android Developers 的慢渲染文档也说明，新版 Android 的 GC 通常由名为 `HeapTaskDaemon` 的后台线程运行；大量分配会增加 GC 的 CPU 工作。

每帧预算由屏幕刷新率决定，不能固定写成某个毫秒数。滑动时主线程、RenderThread、图片解码线程和后台任务共同使用 CPU；GC 工作与帧生产重叠时，可能增加调度等待、内存带宽压力或短暂停顿。是否影响用户可见帧必须由 Frame Timeline 与线程轨道证明。

排查时不要只看单次 GC 耗时。相同的 GC 工作出现在空闲窗口与关键帧窗口，用户影响不同。应在同一份系统跟踪中比较三类轨道：

- **Frame Timeline**：确认 missed frame、slow frame 和 present 结果，判断是否影响用户可见帧。
- **主线程 / RenderThread**：确认帧生产阶段是否被分配、锁、Binder 或调度延迟干扰。
- **HeapTaskDaemon / GC 事件**：确认 GC 是否和帧尖峰重叠，不能只根据内存曲线猜。

时间重叠只能建立相关性，还要检查主线程和 RenderThread 的状态。`Running` 表示线程正在 CPU 上执行，应查看对应 slice 或调用栈；`Runnable` 表示线程已就绪却没有获得 CPU，才更支持调度延迟或 CPU 竞争；`Sleeping`、`Blocked` 等状态要继续追踪唤醒者、锁、Binder 或其他等待原因。GC 与慢帧相邻但不重叠，也不能据此判定因果。

#### Android 17 在应用进程创建后安排的 GC

Android 17 的 `Heap::PostForkChildAction()` 在 `initial_heap_size_ < growth_limit_` 时安排目标堆大小调整，并为 Zygote 复制出的应用进程加入 `TriggerPostForkCCGcTask`。该任务只有在计划时间到达、且进程创建后尚未发生其他 GC 时，才请求一次后台 GC；期间已经发生 GC 时不再执行回收。调度时间包含一个以 UID 为种子的确定性偏移：同一 UID 得到相同偏移，不同 UID 通常不同。根据源码注释，这个偏移用于降低多个进程同时发起此类 GC 的概率。

因此，启动后看到一次后台 GC 时，要同时查看 GC cause（触发原因）、进程启动时间和前后的分配轨道。不能仅凭“启动附近出现 GC”就归因到某个页面的临时对象。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap.cc::Heap::PostForkChildAction()`, `TriggerPostForkCCGcTask`]

#### HeapTaskDaemon 串行执行整条堆任务队列

`HeapTaskDaemon` 进入 `VMRuntime.runHeapTasks()` 后，由 ART 原生层的 `TaskProcessor::RunAllTasks()` 按 `target_run_time_`（计划运行时间）取任务。一次循环只执行一个 `HeapTask`：依次调用 `GetTask()`、`Run()` 和 `Finalize()`，再取下一项。`ConcurrentGCTask` 中的 Concurrent 表示收集器的部分阶段可与应用线程并发，不表示多个堆任务会在守护线程上并行执行。

这条队列还承载 HeapTrim（向系统归还可释放堆页）、收集器切换、按时间触发 GC 的阈值复查和部分启动维护。向它注入阻塞任务或暂停守护线程，会一起延迟这些工作。`TaskProcessor::Stop()` 只把处理器标记为停止；`GetTask()` 随后不再等待任务的计划时间，而是继续取出剩余任务，直到队列排空。错误干预可能让未到期任务集中执行。

#### 并发 GC 请求如何判定和去重

Android 17 的 `ShouldConcurrentGCForJava()` 有字节阈值和“分配增量 × 经过时间”两类判断。它可能返回“不需要 GC”“请求 `ConcurrentGCTask`”或“安排 `TimeBasedGcThresholdCheckTask`”。`num_bytes_allocated_` 会把仍在使用的整块 TLAB 计入，因此是近似已分配字节数，不是逐对象精确值，也不是 PSS。

多个线程同时满足条件时，`RequestConcurrentGC()` 使用原子 compare-and-set（仅当旧值未变化时更新）增加 `max_gc_requested_`；只有更新成功的线程把任务加入队列。任务执行时还会检查目标序号，若其他路径已经完成更新的 GC，本次任务不会重复收集。去重依赖这个序号协议，而不是扫描队列里是否已有同名任务。

新对象在请求入队期间由 Handle 临时保护，因为 `TaskProcessor::AddTask()` 可能让线程挂起，移动式 GC 也可能在此时更新对象地址。Handle 只用于保证 ART 内部引用安全，应用代码不能取得或复用这套机制。

### 典型内存抖动场景

调用频率比代码表面的复杂度更值得优先检查。一次分配在点击按钮时没有问题，放到 `onDraw()`、`onBindViewHolder()`、`onTouchEvent()`、Compose 重组或动画回调里，就会随帧数重复执行。

#### onDraw / onMeasure 中分配对象

`onDraw()` 和 `onMeasure()` 处在渲染关键路径里，分配对象会同时增加 CPU 工作和 GC 压力。常见问题包括每帧创建 `Paint`、`Path`、`RectF`、`Shader`，每次测量创建临时数组，或者在绘制时格式化文案。

下面这段代码的用途是把绘制用对象移动到 View 生命周期内，只在尺寸变化时更新几何数据。重点看 `onDraw()` 里不再创建 `Paint` 和 `RectF`。

```kotlin
class GaugeView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {
    private val arcPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeWidth = 8f * resources.displayMetrics.density
    }
    private val arcBounds = RectF()

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        val padding = arcPaint.strokeWidth / 2f
        arcBounds.set(padding, padding, w - padding, h - padding)
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawArc(arcBounds, 180f, 220f, false, arcPaint)
    }
}
```

这段写法没有消除初始化和尺寸变化时的分配，只把 `Paint` 与 `RectF` 的创建移出高频绘制路径。优化后要用 Android Studio 的 Java/Kotlin 分配记录或 Perfetto ART 分配画像，检查 `onDraw()` 时间窗内的分配调用栈。

#### 字符串拼接和格式化

字符串抖动常出现在日志、埋点、列表绑定和调试面板里。`String.format()`、复杂模板、循环里的 `+` 拼接、把大 JSON 拼成日志字符串，都会产生临时对象。影响取决于拼接频率、字符串长度和调用窗口。

下面这段代码用于列表绑定场景，复用价格格式化器，并把展示字符串的生成限制在绑定边界。`NumberFormat` 不再在每次 `onBindViewHolder()` 调用时创建。

```kotlin
class PriceTextFormatter(
    private val numberFormat: NumberFormat = NumberFormat.getCurrencyInstance(Locale.CHINA)
) {
    fun formatFen(priceFen: Long): String {
        return numberFormat.format(priceFen / 100.0)
    }
}

class GoodsViewHolder(
    itemView: View,
    private val formatter: PriceTextFormatter
) : RecyclerView.ViewHolder(itemView) {
    private val priceView: TextView = itemView.findViewById(R.id.price)

    fun bind(item: GoodsItem) {
        priceView.text = formatter.formatFen(item.priceFen)
    }
}
```

`NumberFormat` 不是线程安全对象，`PriceTextFormatter` 应限制在 RecyclerView 所在的主线程使用。`formatFen()` 仍会创建结果 `String`；复用只省去重复构造格式器的成本。价格、币种与地区设置都未变化时，可以让不可变界面状态保存已格式化结果，并在任一输入变化时重新计算。不要把所有展示文案放进全局缓存，否则失效逻辑和常驻内存可能抵消收益。

#### 自动装箱和临时集合

自动装箱会把基本类型包装成对象，Kotlin / Java 的集合 API 很容易在泛型、lambda（匿名函数）、可空类型、`Map<Int, T>` 等位置触发装箱。少量装箱不值得处理；滑动、采样、埋点聚合或图表绘制中每帧装箱，才会形成稳定的分配来源。

这段代码用于高频计数场景，用平台集合替代 `MutableMap<Int, Int>`，避免键和值在高频路径上反复装箱。分桶宽度由调用方按分析精度传入，示例不内置通用分界。

```kotlin
class FrameBucketCounter(
    private val bucketWidthMicros: Int
) {
    init {
        require(bucketWidthMicros > 0)
    }

    private val buckets = SparseIntArray()

    fun add(frameCostMicros: Int) {
        val bucket = frameCostMicros / bucketWidthMicros
        buckets.put(bucket, buckets.get(bucket, 0) + 1)
    }

    fun snapshot(): Map<Int, Int> {
        return buildMap(buckets.size()) {
            for (index in 0 until buckets.size()) {
                put(buckets.keyAt(index), buckets.valueAt(index))
            }
        }
    }
}
```

`snapshot()` 仍会创建普通 `Map` 并发生装箱。这一边界让高频路径只记录数据，低频读取时再转换为通用结构。调用方还要避免计数在无限生命周期内溢出，可以按测试场景创建并丢弃计数器。

### 内存抖动检测与治理

检测内存抖动按“现象确认 → 分配归因 → 代码修复 → 回归防护”推进。堆转储适合分析某一时刻仍然存活的对象；抖动更需要时间序列上的分配记录：哪条调用栈在什么时段分配、每秒分配多少、是否与慢帧或启动阶段重叠。

#### 现象确认：先把 GC 和帧放到同一张图里

用 Perfetto 或 Android Studio Profiler 记录一次目标场景：启动、打开页面、快速滑动、动画播放或连续输入。观察三组信号：

- **帧信号**：Frame Timeline 是否出现 missed frame（未按时呈现）或 slow frame（耗时偏长），慢帧是否集中在交互窗口。
- **GC 信号**：Logcat、Profiler 或系统跟踪里的 GC 是否密集，`HeapTaskDaemon` 是否在同一窗口活跃。
- **分配信号**：Java/Kotlin 分配记录或 ART 分配画像是否显示对象数量快速上升。

Android Studio 的 Java/Kotlin 分配记录要求 debuggable（可调试）构建。Full 模式记录每次分配，高分配应用可能出现明显的分析器开销；必要时改用定期抽样的 Sampled 模式，并把采集模式写进对比记录。Perfetto 从 Android 12 起支持 ART allocation profiling，在 `HeapprofdConfig` 中配置 `heaps: "com.android.art"` 后采集分配调用栈样本。它记录对象创建时的调用栈与累计分配，不记录对象何时被删除或回收，因而不能替代展示对象保留关系的堆转储。在量产 user 系统上，目标应用还必须声明 `debuggable` 或 `profileable`（允许系统分析）。

#### 分配归因：按调用频率排序，不按代码体量排序

找到分配栈后，按调用频率、单次字节数和存活时间共同分层：每帧调用、每个列表项调用、每次页面打开调用、后台批处理调用。高频小对象可能比低频大对象产生更多累计分配，但优先级必须由目标时间窗内的总字节、次数和慢帧重叠关系决定。

常用修复动作有四类：

- **移出高频回调**：把可安全复用的 `Paint`、`Path`、`RectF`、格式化器或缓冲区移到与使用者相同的生命周期，并在尺寸或配置变化时更新。持有 View、Context 或大数组的对象不能无条件提升为全局成员。
- **合并中间态**：数据转换时减少 DTO（数据传输对象）、领域模型、界面模型之间的多份临时集合；能够流式处理时，不要先生成完整集合。
- **换基本类型容器**：高频 `Int` / `Long` 键场景使用 `SparseArray`、`SparseIntArray`、`LongSparseArray` 或专用数组结构。
- **分批处理**：把大列表差异计算、日志解析、埋点聚合分块执行，将分配峰值分散到多个调度片段。

#### 代码修复：减少高频路径分配，不追求零分配

零分配不应成为通用目标。ART 对短命小对象提供了低开销分配路径，强行池化反而可能把短命对象变成长命对象，增加老年代压力；字段未完整重置时还会产生残留数据。对象池只适合创建频繁、初始化成本高、状态可完整清理的对象；普通数据对象和持有 View、Context 或回调的对象不要池化。

下面的函数把批处理切成多个可协作让出执行权的调度片段。它直接把原列表和左闭右开的 `[start, end)` 索引交给调用方，省去分块子列表；`chunkSize` 必须由测量决定。

```kotlin
suspend fun <T> processInChunks(
    source: List<T>,
    chunkSize: Int,
    processRange: suspend (source: List<T>, start: Int, endExclusive: Int) -> Unit
) {
    require(chunkSize > 0)

    var index = 0
    while (index < source.size) {
        val end = index + minOf(chunkSize, source.size - index)
        processRange(source, index, end)
        index = end
        yield()
    }
}
```

`yield()` 只提供协作式让出机会，不保证跨帧执行，也不会自动切换到后台线程。调用方要选择合适的协程调度器，并确认 `processRange` 不在主线程执行大量 CPU 计算。该函数不会减少最终结果集；如果调用方仍把所有结果保存在内存中，稳定占用不会下降。最终结果过大时，应改用分页、流式消费或外部存储。

#### 回归防护：给高频路径设分配预算

列表绑定、绘制和埋点代码重构后，分配热点可能重新出现。分配预算应来自同一设备、同一构建和确定脚本的基线分布，再按允许的性能变差范围设置门槛，不要复制其他项目的固定数值。

- **启动**：记录首屏前总分配字节、GC 次数和 `HeapTaskDaemon` 活跃区间。
- **滑动**：固定列表数据、设备条件和输入脚本，比较单位时间分配字节、慢帧与 GC 的时间关系。
- **绘制**：让自定义 View、图表或动画运行到数据稳定，记录目标方法时间窗内的分配次数与调用栈。
- **生产环境**：只采集已有的有界趋势指标和场景标签，不在用户设备上持续运行 Full 分配记录。异常版本回到实验设备复现；需要现场证据时使用受系统控制的分析能力。

把非关键工作延后只能改变时间分布，不能减少总分配。首屏后预取或 fling（惯性滑动）结束后刷新统计，仍可能与下一次输入、图片解码或后台任务竞争 CPU；要根据任务优先级设置取消条件，并在系统跟踪中确认延后后的窗口没有产生新的慢帧。

## Compose 重组、布局与分配热点

通用分配模型进入 Compose 后，要沿 composition、measure 和 draw 确认对象来源。remember 只能延长明确可复用对象的生命周期。

### 范围与版本

讨论范围是 Android 上的 Compose Runtime、应用 Java Heap（ART 管理的 Java/Kotlin 对象堆）与 ART GC（垃圾回收）。平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核基线为 `android17-6.18-2026-06_r6`。Compose 是独立发布的 Jetpack 库；本文使用 2026 年 8 月 12 日发布的稳定版 Compose Runtime 1.12.0，并以 AndroidX 提交 `963bf914f78b389bdddef0da7f36bee19d897274` 为源码锚点。

Compose Runtime 1.13.0-alpha01 已发布，但仍是预览版。版本比较会标出预览变化，正文结论以 1.12.0 稳定版为准。

Composition 是一棵可组合界面在运行时的实例，保存界面结构、状态订阅和 `remember` 值；重组（recomposition）是状态变化后重新执行受影响的可组合函数。处理 Compose 内存问题时，先区分两种症状：

- 存活对象持续增加：常见于 Composition 没有按宿主生命周期释放、协程或监听器存活过久、状态所有者范围过大、View 与 Compose 互相持有。
- 短命对象分配速率过高：常见于组合阶段反复排序、映射、格式化，频繁重建输入对象，或在高频状态变化中执行不必要的组合。

allocation 表示创建对象并占用 Java Heap 空间，短命对象被频繁创建又回收时也称为分配抖动（allocation churn）。一次重组不一定创建新对象，也不一定创建新的 `RecomposeScopeImpl`。定位时要分别观察重组次数、对象分配和 GC；泄漏治理可参阅 [23.1 内存泄漏检测与治理](01-memory-leak-governance.md)，分配抖动与 GC 可参阅 [23.4 内存抖动与 GC 治理](04-java-heap-gc-compose-allocation.md)，生产环境指标可参阅 [23.6 内存监控与线上治理](06-memory-monitoring.md)。

### Compose Runtime 会长期保存哪些数据

一份活跃 Composition 至少要保存组合结构、`remember` 的值、重组范围、状态观察关系和待应用的变更。理解这些内部结构的用途，才能区分正常持有、短期分配和生命周期泄漏。

#### Slot storage 有两种实现

slot storage 是 Compose Runtime 保存组合层级、节点位置和 `remember` 值的内部存储。1.12.0 同时包含 gap-buffer（在连续数组中保留可移动空隙）与 LinkTable（用链接结构减少内容移动时的数组复制）两种实现。历史稳定提交中的 [`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt) 和 [1.12.0 `Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt) 都显示，`CompositionImpl.createSlotStorage()` 根据 `ComposeRuntimeFlags.isLinkBufferComposerEnabled` 选择实现。

历史 [`ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt) 与 [1.12.0 `ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt) 都把该开关的默认值设为 `false`。AndroidX 的 [Compose Runtime 1.11 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)首次说明了 LinkTable 的目标；1.12.0 发布说明仍将它列为实验实现，并要求团队主动启用和验证。

因此：

- 未启用实验标志的 1.12.0 应按 gap-buffer 分析；
- 开启标志的应用要按 LinkTable 分析，并同时检查 R8（Android 代码压缩与优化工具）规则；
- heap dump（Java 堆转储）中的内部类名和引用形态可能不同；
- 不应给所有 Compose 版本套用固定的 SlotTable 字节数或扩容次数。

slot storage（槽位存储）持有 `remember` 值和组合结构。Composition 被宿主继续引用时，其中的值也会继续存活。heap dump 中的 dominator（支配对象，释放它才可能释放其支配的对象集合）用于寻找主要持有者。看到 SlotTable 或 LinkTable 出现在引用链中时，应继续检查 Activity、Fragment View、`ComposeView`、Navigation destination（导航目的地）、Recomposer（调度重组的运行时对象）或长期协程；内部表结构通常只是引用路径中的一环。

#### `RecomposeScopeImpl` 会复用

`RecomposeScopeImpl` 表示可独立失效并重新执行的组合范围。历史稳定版 [`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt) 与 [1.12.0 源码](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt) 都让 `trackedInstances` 与 `trackedDependencies` 初始为 `null`，读取普通状态或派生状态后才按需创建。`release()` 会清空 `owner`、追踪集合和用于重启该范围的 `block`。

重组时可以继续使用已有的重组范围；`updateScope()` 只替换重启用的代码块。Lambda 是否产生新对象，还受 Compose Compiler 生成代码与 Strong Skipping（强跳过模式）影响。

[Strong Skipping 官方说明](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)记录了两条规则：

- Kotlin 2.0.20 起默认启用 Strong Skipping；
- restartable composable（可由运行时重新执行的可组合函数）即使带不稳定参数也可以被跳过；可组合函数内部的 Lambda 会自动缓存（memoize），也就是根据捕获对象缓存并复用。

不稳定参数使用引用相等比较，稳定参数使用对象相等比较。调用方每次构造新 `List`、新 UI 数据模型或捕获值不同的新 Lambda，仍可能让比较失败。优化时应检查输入对象是否稳定复用、状态是否在合适的所有者中更新，以及运行时是否出现高频分配；源码中的 Lambda 表达式数量不能直接代表运行时分配量。

#### Snapshot 状态记录随写入演进

Snapshot 是 Compose 为状态读取和写入提供一致视图的机制；状态记录（`state record`）是同一状态对象在不同 Snapshot 中可见的数据版本。`MutableState` 与 `derivedStateOf` 都使用记录链。写入需要取得可写记录，读取会选择当前 Snapshot 可见的记录；切换 Snapshot 不会为所有状态统一新建记录。并发 Snapshot、写入频率与记录复用共同决定对象数量。

Compose Runtime 1.11.4 的 [`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt) 与 [1.12.0 `DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt) 都显示，`ResultRecord` 保存依赖集合、计算结果和用于判断有效性的哈希值。mutation policy（变更策略）判定新旧结果等价时，实现会更新当前记录的依赖信息；结果变化时才申请可写记录。每一帧或每次 Snapshot 应用都不能直接换算成一个新 `ResultRecord`。

### 哪些分配值得优先处理

#### 组合阶段的集合加工与格式化

composable body（可组合函数体）可能因状态变化多次执行。排序、`map`、字符串拼接、解析和对象适配如果直接放在函数体中，也会重复执行。这段代码把排序结果保存在 Composition 中，并给 Lazy list（按需组合可见列表项的容器）提供稳定身份。

```kotlin
@Composable
fun ContactList(
    contacts: List<Contact>,
    comparator: Comparator<Contact>,
    modifier: Modifier = Modifier,
) {
    val sortedContacts = remember(contacts, comparator) {
        contacts.sortedWith(comparator)
    }

    LazyColumn(modifier) {
        items(
            items = sortedContacts,
            key = { contact -> contact.id },
        ) { contact ->
            ContactRow(contact)
        }
    }
}
```

`remember` 在 key（决定缓存何时失效的输入）的比较结果不变时返回已保存值，key 变化后重新计算。计算量较大的数据加工可以移到 ViewModel 或数据层。`contacts` 若在原对象上修改内容，Compose 和 `remember` 都可能观察不到变化；可以把界面状态暴露为新的不可变列表实例，或使用 `SnapshotStateList` 这类能通知写入的状态集合。每次重组创建 `contacts.toList()` 作为 key 会额外分配一份列表，也不能修正原地修改的数据模型。

#### 原始类型状态 API

Compose Runtime 提供 `mutableIntStateOf`、`mutableLongStateOf`、`mutableFloatStateOf` 和 `mutableDoubleStateOf`。这些接口直接保存整数、长整数、浮点数等原始类型，减少通用泛型状态可能产生的装箱对象。示例让高频计数状态使用原始类型接口。

```kotlin
@Composable
fun FrameCounter() {
    var frameCount by remember { mutableIntStateOf(0) }

    Text(
        text = frameCount.toString(),
        modifier = Modifier.clickable { frameCount++ },
    )
}
```

历史稳定版 [`SnapshotIntState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt) 与 [1.12.0 源码](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt) 中，`SnapshotMutableIntStateImpl` 都用 `IntStateStateRecord` 保存 `Int`，`intValue` 直接读写原始类型，委托运算符也访问 `intValue`。这条路径可以避免通用 `MutableState<Int>` 的自动装箱；收益仍要用 allocation recording（对象分配记录）验证，少量低频状态无需逐个替换。

#### Lambda 与 Modifier

Strong Skipping 会缓存可组合函数内的 Lambda，但以下写法仍可能产生额外分配或失去跳过机会：

- 在调用可组合函数前反复构造新的界面模型或集合；
- 明确使用 `@DontMemoize`；
- 在非可组合函数的高频路径中创建捕获外部变量的 Lambda；
- 每次执行函数体都构造复杂 Modifier 链或中间集合；
- 参数对象的引用每次变化，使不稳定参数的 `===` 比较失败。

Compose Compiler 报告能说明函数能否重启、能否跳过，以及参数稳定性。它不提供运行时对象分配数量，需与 allocation recording 配合使用。

### `derivedStateOf` 与 `snapshotFlow`

#### `derivedStateOf` 减少无效重组

`derivedStateOf` 适合输入频繁变化、界面只关心较少结果变化的场景。例如滚动位置不断变化，而按钮只关心列表是否已经离开顶部。

这段代码把高频滚动状态转换成一个 Boolean，并用 `remember` 把派生状态对象保存在 Composition 中。

```kotlin
@Composable
fun ScrollToTopButton(listState: LazyListState) {
    val showButton by remember(listState) {
        derivedStateOf {
            listState.firstVisibleItemIndex > 0
        }
    }

    AnimatedVisibility(visible = showButton) {
        Button(onClick = { /* launch scroll */ }) {
            Text("返回顶部")
        }
    }
}
```

只要 `showButton` 的结果没有变化，读取它的可组合函数就不需要因每次滚动更新而重组。`derivedStateOf` 自身要维护依赖和缓存；普通字符串拼接、两个低频状态的简单组合，以及每次输入变化都会产生新输出的计算，直接计算通常更清楚。

Compose Runtime 1.12.0 稳定版已经包含一项潜在内存泄漏修复：未正确 `remember` 的 `derivedStateOf()` 在 forward write（同一轮组合先读取依赖状态，随后又写入该状态）场景中，可能被 Composition 持有到该 Composition 销毁。该问题影响 1.11.4，修复最早记录于 1.12.0-beta01，随后进入 1.12.0 稳定版。处理边界如下：

- 在可组合函数内创建 `derivedStateOf` 时使用 `remember`；
- 使用 1.11.4 或更早版本并怀疑该问题时，在 heap dump 中检查 `DerivedSnapshotState` 到 Composition 的引用链，并用 1.12.0 复测；
- 升级到 1.12.0 后仍要使用 `remember`，避免每次重组创建新的派生状态对象；
- 不用 `remember(list, index)` 代替对 `SnapshotStateList` 元素的观察，因为列表身份不变时缓存可能返回旧数据。

#### `snapshotFlow` 负责把 Snapshot 状态转成事件流

`snapshotFlow` 记录 `block` 中读取的 Snapshot 状态；相关状态的写入被应用后，它会重新执行 `block`，只有新结果与旧结果不相等时才向 Flow 发送。历史稳定版 [`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt) 与 [1.12.0 源码](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt) 都会注册 Snapshot apply observer（状态应用观察者）、维护订阅集合，并在 Flow 结束收集时取消本次订阅。

1.12.0 默认重载会创建内部 `SnapshotFlowManager`，并在 Flow 结束时释放；实验性重载允许同一线程上的多个 `snapshotFlow` 共用管理器，此时由调用方在不再使用时调用 `dispose()`，且不能让同一个管理器被不同线程并行收集。这段代码使用默认重载，把列表位置变化交给分析回调上报；任务会在 `LaunchedEffect` 离开 Composition 或 key 变化时取消。

```kotlin
@Composable
fun TrackListPosition(
    listState: LazyListState,
    reportIndex: (Int) -> Unit,
) {
    LaunchedEffect(listState) {
        snapshotFlow { listState.firstVisibleItemIndex }
            .collect { index -> reportIndex(index) }
    }
}
```

把 `snapshotFlow` 放在 `LaunchedEffect` 中不会自动造成泄漏。风险来自外部协程作用域比界面所有者存活更久、`LaunchedEffect` 的 key 选择错误、回调捕获 Activity/View，或重复启动未受管理的收集任务。heap dump 中只看到 Snapshot 类不足以确认泄漏，还要继续检查协程 Job（可取消任务）、Flow collector（Flow 收集者）和宿主生命周期。

### Lazy layout 的 key 维护列表项身份

Lazy layout（按需组合可见内容的布局）默认按位置识别 item（列表项）。数据重排后，同一个业务对象的位置会变化，按位置保存的 `remember` 状态就无法跟随业务对象移动。[Lazy list 官方文档](https://developer.android.com/develop/ui/compose/lists)建议为每项提供稳定且唯一的 key，使状态在插入、删除和重排时仍与同一个业务对象关联。

key 的主要价值包括：

- 数据插入、删除和排序后保持列表项身份；
- 减少无关列表项的重组；
- 让 `rememberSaveable` 状态在符合条件时恢复。

key 不能让滚出屏幕的所有节点永久保留，也不能消除列表项内部的对象分配。用于 `rememberSaveable` 时，key 类型还要能由 `Bundle` 保存，例如原始类型、枚举或 `Parcelable`。业务稳定 ID 通常适合作为 key；位置只适用于内容和顺序都固定的列表。

### View 与 Compose 混合时的生命周期

#### `ComposeView` 应跟随正确的 LifecycleOwner

每个 `ComposeView` 都有自己的 Composition，并引用宿主 View。Fragment 的 View 销毁后，如果 Composition 仍由更长生命周期的对象持有，`remember` 值、副作用任务和界面树也会继续存活。

这段代码让 Fragment 中的 Composition 随 View lifecycle（从 `onCreateView()` 到 `onDestroyView()` 的界面生命周期）销毁。

```kotlin
override fun onCreateView(
    inflater: LayoutInflater,
    container: ViewGroup?,
    savedInstanceState: Bundle?,
): View {
    return ComposeView(requireContext()).apply {
        setViewCompositionStrategy(
            ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed
        )
        setContent {
            AppTheme {
                ScreenContent()
            }
        }
    }
}
```

[Compose in Views 官方文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)把 `DisposeOnViewTreeLifecycleDestroyed` 列为 Fragment View 的适用策略。普通 View 场景默认使用 `DisposeOnDetachedFromWindowOrReleasedFromPool`：View 脱离窗口时释放；若位于 `RecyclerView` 等复用容器中，则在容器脱离或该项被移出对象池时释放。释放策略要按宿主类型选择。

#### `AndroidView.factory` 不需要额外 `remember`

`AndroidView` 的 `factory` 用于创建 View；`update` 在创建后执行，并在其中读取的 Snapshot 状态变化时再次执行。把 View 另存进 `remember` 会让 Composition 与 `AndroidView` 同时保存它的引用，增加生命周期不一致的风险。

Lazy list 中需要复用 View 时，应使用带 `onReset` 的重载 API。示例在复用前清理上一条列表项留下的临时状态，并在该 View 不再复用时释放资源。

```kotlin
AndroidView(
    factory = { context -> PreviewView(context) },
    update = { view ->
        view.bind(model)
    },
    onReset = { view ->
        view.clearTransientState()
    },
    onRelease = { view ->
        view.release()
    },
)
```

[Views in Compose 官方文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)说明，`onReset` 必须非空才会启用 Lazy 容器中的 View 复用；`onRelease` 在 View 离开 Composition 且不再复用时调用。`update` 应具备幂等性，也就是用相同输入重复执行不会累积副作用；监听器若在每次 `update` 中注册，要先替换或移除旧监听器。

混合页面的 heap dump 应同时检查 View tree（传统 View 层级）与 Composition。常见 dominator 包括 Fragment view binding（生成的视图绑定对象）、adapter（列表适配器）、listener（监听器）、`AndroidView` 内的 WebView/播放器/地图、Navigation back stack（导航返回栈）和长生命周期 ViewModel。

### Android 17 中分配如何触发 ART GC

Compose Runtime 对象位于应用 Java Heap。Android 17 的 [`heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)显示，Java 对象分配会更新已分配字节数；使用并发垃圾回收器时，`ShouldConcurrentGCForJava()` 根据当前配置检查字节阈值，以及启用后的 time-based GC（同时考虑分配量和距上次 GC 时间的触发方式）。需要 GC 时，分配路径会在允许线程挂起后调用 `RequestConcurrentGCAndSaveObject()` 请求并发回收。

[`heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)中的 `ConcurrentGCTask` 由 task processor（ART 的后台任务调度器）调度。GC 名称中的 concurrent 表示部分工作可与应用线程并行执行；root 扫描（检查线程栈和全局引用等根对象）、checkpoint（让线程在安全位置配合运行时操作）、对象移动与系统调度仍可能让应用线程等待并影响帧时间。

Android 17 的 ART 源码支持 generational CC（分代并发复制）与 generational CMC（分代并发标记压缩）。分代表示优先回收新生代对象，并按条件执行完整回收。设备选择哪种模式，还取决于垃圾回收器、read barrier（读取引用时执行的屏障逻辑）或 `userfaultfd` 内核能力、`-Xgc` 选项、ART 功能标志和 DeviceConfig 属性。源码支持某种模式，不代表所有 Android 17 设备都默认启用；应以目标设备日志和 Perfetto 跟踪结果为准。

Compose 分配与卡顿之间需要建立证据链：

1. Frame Timeline（帧时间线）出现 missed frame（未按时完成的帧）或长帧；
2. Compose tracing 显示对应时间段执行了哪些可组合函数；
3. allocation recording 证明该时间段的分配速率或特定类型增加；
4. ART GC slice（跟踪中的一段 GC 事件）、线程状态和暂停区间与长帧重叠；
5. 修正分配后，同一设备与场景的长帧和 GC 数据同步改善。

GC 与长帧出现在相近时间只能说明相关性。重组中的业务计算、measure/layout（测量与布局）、图片解码和主线程 I/O 都可能同时发生；需要用分配证据和修改后的对照数据确认 GC 是否为主要原因。

### 诊断与回归流程

#### 用发布版配置测量性能

Debug（调试）构建、Layout Inspector、method tracing（方法调用跟踪）和 allocation recording 都会改变执行与分配行为。[Compose 稳定性诊断文档](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)要求编译器报告使用发布版构建。页面性能回归也应使用接近发布配置的可分析构建：编译优化、R8、Baseline Profile（预编译常用代码路径的配置）和依赖版本都要与发布版一致，同时通过 `profileable` 等方式允许工具采集。

这段 Gradle 配置用于输出 Compose Compiler 稳定性报告和模块指标。

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

报告中的 `restartable`、`skippable` 和参数稳定性用于筛选可疑的可组合函数。某个函数不可跳过但调用很少，可能没有用户可见成本；把不满足稳定性约定的类型强行标成 `@Stable`，可能让 Compose 跳过本应执行的更新。

#### 四类工具回答四个问题

| 工具 | 回答的问题 | 使用限制 |
| --- | --- | --- |
| Compose Compiler reports | 编译器如何判断函数与参数 | 没有运行时次数和对象分配数据 |
| Layout Inspector | 当前会话中哪些 composable 重组或被跳过 | 调试工具有观测成本 |
| Perfetto + Compose tracing | 重组、布局、绘制、线程与 GC 的时间关系 | 需要固定场景和接近发布配置的构建 |
| Allocation recording / heap dump | 哪些类型在分配、哪些对象被谁持有 | 分配记录成本高；heap dump 只反映采集时刻 |

[Composition tracing 文档](https://developer.android.com/develop/ui/compose/tooling/tracing)说明，Macrobenchmark（在应用外驱动完整场景的基准测试）可以产出带 Compose tracing 的系统跟踪。滚动、页面切换和启动应写成可重复的 Macrobenchmark；Memory Profiler 用于定位具体分配或持有关系，不能单独作为回归判断依据。四类工具提供的是不同证据，需要按同一时间段、设备和操作进行关联。

#### 先判断分配抖动，再判断泄漏

建议按以下顺序检查：

1. 用 `dumpsys meminfo` 和 Java Heap 曲线确认占用水平与增长形态；
2. 用 allocation recording 找出高频分配类型与调用栈；
3. 用 heap dump 查看离开页面后仍存活对象的 dominator；
4. 用 Perfetto 按时间对齐 Compose、帧与 GC 事件；
5. 修改一处后复跑相同操作，不同时改状态模型、列表与图片策略。

页面退出后仍存在一份 Composition 不一定异常，Navigation 可能按设计保留导航目的地状态。判断时要结合返回栈、宿主生命周期与产品预期。相同导航目的地的实例数量随进入次数持续增加，或旧 Fragment View 已销毁却仍支配 Composition，才指向生命周期泄漏。

### 版本与实现边界

| 版本 | 相关变化 |
| --- | --- |
| Kotlin 2.0.20+ | Strong Skipping 默认启用；不稳定参数按引用相等判断，可组合函数内的 Lambda 自动缓存 |
| Compose Runtime 1.11.4 及更早版本 | LinkTable 实现存在但默认关闭；尚未包含 `derivedStateOf` forward-write 保留问题修复 |
| Compose Runtime 1.12.0 | 当前稳定锚点；包含上述 `derivedStateOf` 修复；LinkTable 仍为实验实现且默认关闭 |
| Compose Runtime 1.13.0-alpha01 | 当前预览版；不作为本文稳定行为依据 |
| Android 17 / API 37 | ART 源码锚点为 `android-17.0.0_r1`；垃圾回收器与分代模式仍受运行时和设备配置影响 |

Compose Multiplatform 在不同目标上使用不同运行时与内存管理器。这里的 GC、heap dump 和 Android View 互操作结论只适用于 Android；Desktop/JVM、iOS 或 Wasm 的对象大小与 GC 行为需要按各自平台验证。

### 小结

Compose 内存问题要把“对象被长期持有”和“短命对象分配过快”分开。slot storage（槽位存储）、RecomposeScope 和 Snapshot 状态记录是正常运行时结构，类名本身不能证明泄漏。泄漏要沿 dominator 查找生命周期更长的持有者，分配抖动要用 allocation stack（对象分配调用栈）确认创建位置。

应用代码应优先处理组合阶段的重复计算、每次创建的新输入对象、生命周期过长的状态所有者、未管理的协程和 View 资源。`remember`、`derivedStateOf`、原始类型状态 API、Lazy 列表 key 与 Strong Skipping 各自解决不同问题。ART GC 的触发与垃圾回收器配置以 Android 17 源码和设备跟踪结果为准；固定堆大小、每帧分配量或 GC 次数不能作为跨设备的通用阈值。

## 常见误区

### “看到 GC 就要抑制 GC”

GC 请求反映堆状态和分配行为。AOSP 中，`ShouldConcurrentGCForJava()` 判定需要回收后才会请求 `ConcurrentGCTask`；应用侧盲目抑制 GC 只会把回收延后。除非进行虚拟机研究或受控实验，业务应用不要通过原生函数拦截来阻塞 `HeapTaskDaemon`。

修改 `ConcurrentGCTask::Run()` 的 vtable（虚函数表）依赖非公开 C++ ABI，也只能拦截一类后台请求；分配失败路径仍会等待或触发 GC。伪造 `num_bytes_allocated_` 不会增加分配器空间或物理内存，还会让 GC 起点、分配限制、系统跟踪和回收记账互相矛盾。向 `TaskProcessor` 注入阻塞任务还会影响整条堆维护队列。这些方案都不能进入第三方应用的生产构建。

`onTrimMemory()` 也不是 HeapTrim 或 GC 请求。Android 17 中，它经 `ActivityThread` 分发给 `ComponentCallbacks2`；应用释放缓存只是让对象变得可回收，运行时仍自行决定何时 GC。从 API 34 起，`TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 不再发送，`onLowMemory()` 也不再调用；应用可利用 `UI_HIDDEN` 和 `BACKGROUND` 释放对应状态下可重建的资源，但不要在回调中调用 `System.gc()`。

### “对象池一定能减少卡顿”

对象池只减少重复创建，不能自动降低状态管理复杂度。池中对象的生命周期变长后，可能增加保留内存，也可能让短命对象进入更老的代。用于生产环境前，要同时比较分配、GC、稳定占用和帧表现，并验证对象能够完整重置。

### “一次堆转储就能定位抖动”

堆转储适合查看某一时刻仍然存活的对象，抖动中的临时对象可能已经被回收。定位抖动需要 Android Studio 分配记录或 Perfetto ART 分配画像，用时间轴上的创建速度和调用栈找到高频来源。

## 参考资料

- [Android Developers：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Android Developers：Overview of memory management](https://developer.android.com/topic/performance/memory-overview)
- [Android Developers：`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Android Developers：`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android 17：Features and APIs](https://developer.android.com/about/versions/17/features)
- [Android Developers：Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [Android Developers：Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [AOSP `android-17.0.0_r1`, ART `heap.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.h)
- [AOSP `android-17.0.0_r1`, ART `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP `android-17.0.0_r1`, ART `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `android-17.0.0_r1`, `ComponentCallbacks2.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP `android-17.0.0_r1`, `LruCache.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/util/LruCache.java)

- [Android Developers：Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Android 16 QPR2：Release notes](https://developer.android.com/about/versions/16/qpr2/release-notes)
- [Android Developers：Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [AOSP：Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [Perfetto：ART Allocation Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `android-17.0.0_r1`, `Daemons.java`](https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/libart/src/main/java/java/lang/Daemons.java)
- [AOSP `android-17.0.0_r1`, `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP `android-17.0.0_r1`, `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `android-17.0.0_r1`, `task_processor.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/task_processor.cc)

- [Compose Runtime release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime)
- [Compose performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices)
- [Compose phases and performance](https://developer.android.com/develop/ui/compose/performance/phases)
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)
- [Diagnose Compose stability](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)
- [State and Jetpack Compose](https://developer.android.com/develop/ui/compose/state)
- [Lazy lists and grids](https://developer.android.com/develop/ui/compose/lists)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Using Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)
- [Using Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)
- [Compose Runtime 1.11.4：`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt)
- [Compose Runtime 1.11.4：`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt)
- [Compose Runtime 1.11.4：`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt)
- [Compose Runtime 1.11.4：`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt)
- [AOSP Android 17：ART `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP Android 17：ART `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [Android 17 Kernel：`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
- [Compose Runtime 1.12.0：`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt)
- [Compose Runtime 1.12.0：`ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt)
- [Compose Runtime 1.12.0：`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt)
- [Compose Runtime 1.12.0：`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt)
- [Compose Runtime 1.12.0：`SnapshotIntState.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt)
- [Compose Runtime 1.12.0：`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt)
