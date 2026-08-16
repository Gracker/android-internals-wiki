---
title: "Java Heap 优化策略"
chapter: "23.4"
section: "23.4"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1；ART Heap、ComponentCallbacks2、ProfilingTrigger 与 Android 内存管理官方文档"
last_review_finalize_at: "2026-08-15T07:29:18+08:00"
last_review_finalize_run_id: "20260815-072918-gracker-writing-review"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: official
    path: "https://developer.android.com/reference/android/content/ComponentCallbacks2"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-allocations"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/util/LruCache.java"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]"
tags: [java-heap, object-pool, gc-friendly, collection-optimization]
related_chapters: ["23.1", "23.2", "23.5", "23.6", "23.7", "4.3", "4.8"]
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T07:29:18+08:00"
last_draft_polish_run_id: "20260815-072918-gracker-writing"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
consolidated_from:
  - "src/part5-app/ch23-memory-practice/23.26-art-heap-distribution-oom-trigger-path.md"
---

# Java Heap 优化策略

> **版本基线**
>
> 平台行为与源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。涉及旧版本的内容只说明 API 或行为变化，不高于 Android 17。

## Java 堆优化解决什么问题

Java 堆优化处理应用侧对象分配、对象生命周期和缓存预算之间的关系。[23.1 内存泄漏检测与治理](./01-memory-leak-governance.md)处理“该释放的对象没有释放”，[23.2 Bitmap 与图片内存优化](./02-bitmap-optimization.md)处理像素内存；本文关注另一类堆压力：对象仍有业务价值，但分配时机、集合规模、缓存策略或临时对象频率让占用或回收成本升高。

Android 会为每个应用进程设置 Java 堆上限，无法在限制内完成分配时会抛出 `OutOfMemoryError`。Android Studio 的 Memory Profiler（内存分析器）可以观察堆曲线、对象数量和 GC 事件。工程判断不能只看一次 `Runtime.maxMemory()`：还要比较同一场景的分配速度、峰值、退出后的存活对象和 GC 行为。堆曲线回落只说明对象具备被回收的条件，不代表页面已经满足性能目标；曲线没有立即回落，也可能是 ART 保留可复用堆空间，而不是对象仍被引用。

[4.3 ART 虚拟机内存管理](../../part1-fundamentals/ch04-memory/03-art-memory.md)解释堆空间、分配器和 GC；[4.8 ART FinalizerDaemon、Cleaner 与 ReferenceQueue](../../part1-fundamentals/ch04-memory/08-finalizer-referencequeue.md)解释延迟清理与引用队列；[23.5 内存抖动与 GC 治理](./05-memory-churn-gc.md)讨论高频分配和暂停证据。应用侧的基本动作是减少或推迟分配、按预算缓存，并在生命周期边界释放不再需要的引用。

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

## Java 堆空间组成与分配策略

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

## ART 分配失败与 OOM 触发路径

普通对象的快速分配失败后，`Heap::AllocateInternalWithGc()` 不会立即抛出 OOME。Android 17 会先等待正在运行的 GC；等待期间完成过回收时重试分配；随后按 `next_gc_type_` 执行阻塞式 GC，也就是由分配线程发起并等待完成的回收。仍未取得足够空间时，ART 会执行覆盖整个堆的回收，并清除 SoftReference（内存不足时允许 GC 清除的软引用）。部分分配器在配置启用且达到时间间隔后，还会尝试 homogeneous space compaction（同构空间压缩），即在两个同类堆空间之间复制对象以整理碎片。以上尝试都失败后才抛出 OOME。

这里不存在设备无关的“Young GC（年轻代回收）→ Full GC（全堆回收）”固定两步顺序。`next_gc_type_` 取决于收集器、代际状态、上次 GC 和目标堆大小。分配线程也可能主要耗时在等待另一线程执行 GC，因此 Perfetto 中看到的业务停顿可能长于单次 GC 暂停。

### 读懂 OOME 文本

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

### 先区分四种“内存不足”

| 现场 | 主要证据 | 排查方向 |
| --- | --- | --- |
| Java 堆 OOM | `Failed to allocate`、对象存活集、`growth limit` | 泄漏、业务仍需保留的对象、短时间频繁分配和回收、单次大对象 |
| 原生分配失败 | `malloc` / `mmap` 错误、原生调用栈、PSS/VMA | 分配器、匿名映射、Graphics、请求大小 |
| 线程创建失败 | `pthread_create (... stack) failed`、线程数、`errno` 错误码 | 每线程栈、VMA、原生内存、系统任务数限制 |
| FD / 地址空间耗尽 | `EMFILE` / `ENOMEM`、FD/VMA 数量、最大连续空闲区 | 资源关闭、32 位地址空间、线程与映射数量 |

原生分配失败只有部分 Android 框架层或 JNI（Java 原生接口）入口会转换为 Java OOME；FD 用尽通常直接返回 `EMFILE`。不能把所有带 `OutOfMemoryError` 或 `ENOMEM` 的现场都归入 ART 对象泄漏。

### 不修改 ART 内部计数来“扩堆”

`largeHeap` 只扩展 Java 堆的 `growth limit`，不增加设备物理内存，也不处理原生内存、Graphics、线程栈或无界缓存。修改 `num_bytes_allocated_`、`large_object_threshold_`，伪造已释放字节数，拦截分配器以绕过 GC，或解除 ART 堆空间映射，会破坏分配计数、对象存活位图、card table（记录跨区域引用的卡表）、对象所属空间和 GC 根集合之间的一致性，不能用于生产环境。Android 17 的 LOS 也没有为应用提供固定保留 512 MiB 空间的接口。

## 大对象与集合优化

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

## 对象池与缓存策略

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

对象池还要与 ART 分代 GC 分开评估：ART 对短命小对象的分配路径通常开销较低，强行池化会把短命对象变成长命对象，增加老年代压力。只有分配热点造成了可观测的 GC 或 CPU 压力，池化才有继续评估的价值。分代和分配路径见 [4.3 ART 虚拟机内存管理](../../part1-fundamentals/ch04-memory/03-art-memory.md)，卡顿证据见 [23.5 内存抖动与 GC 治理](./05-memory-churn-gc.md)。

## 更适合 GC 的编码实践

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

## ART GC 调优参数

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

## 排查路径：从堆曲线到代码改动

Java 堆优化可以按四步推进：

1. 用 Memory Profiler 录制目标场景，记录对象数量、堆曲线和 GC 事件。
2. 如果曲线持续上升且页面退出后不回落，转到 [23.1 内存泄漏检测与治理](./01-memory-leak-governance.md)。
3. 如果曲线有尖峰但能回落，检查大对象、集合复制、缓存预算和批处理峰值。
4. 如果 GC 频率高且伴随卡顿，转到 [23.5 内存抖动与 GC 治理](./05-memory-churn-gc.md)，再根据分配证据减少热点。

Android 17 / API 37 为 `ProfilingTrigger` 增加 `TRIGGER_TYPE_OOM` 和 `TRIGGER_TYPE_ANOMALY`。OOM 触发器会在未捕获的 `OutOfMemoryError` 现场采集 Java 堆转储；应用下次启动并注册结果回调后，可以取得这份诊断结果。自定义 `Thread.UncaughtExceptionHandler` 必须继续调用默认异常处理器，系统才能观察到该事件。anomaly（系统异常行为）触发器覆盖内存用量超限等情况，但诊断产物由异常类型决定：超过 Android 17 内存限制时可返回堆转储，其他异常可能返回不同类型的跟踪或采样数据。触发式采集用于取得难以在本地复现的证据，不能替代堆预算和代码修正。生产监控见 [23.7 内存监控与线上治理](./07-memory-monitoring.md)，Android 17 内存限制见 [23.6 大内存与多进程策略](./06-large-heap-multiprocess.md)。

一次有效改动至少要回答三件事：分配对象数或字节数是否下降，峰值或稳定占用是否改善，CPU、I/O、网络请求与用户场景指标是否变差。只降低 Java 堆峰值却增加其他资源成本，不能视为完成优化。

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
