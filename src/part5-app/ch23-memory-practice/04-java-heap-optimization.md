---
title: "Java Heap 优化策略"
chapter: "23.4"
section: "23.4"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers ComponentCallbacks2 + Clippings/Android 性能优化"
confidence: medium
drafted_date: "2026-05-14"
reviewed_date: "2026-05-14"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
polish_count: 1
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: official
    path: "https://developer.android.com/reference/android/content/ComponentCallbacks2"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java"
  - type: official
    path: "https://developer.android.com/studio/profile/capture-heap-dump"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-allocations"
  - type: aosp
    path: "art/runtime/gc/heap.h"
  - type: aosp
    path: "art/runtime/gc/heap-inl.h"
  - type: aosp
    path: "art/runtime/gc/heap.cc"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]"
tags: [java-heap, object-pool, gc-friendly, collection-optimization]
related_chapters: ["23.1", "23.5", "4.3", "4.8"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task6_review_notes: "2026-05-14 task6 review: 修正否定纠正式表达、缓存预算和 GC 友好段落；四层质检通过，无新增 L3/L4 回炉项，等待 Task9 review。"
last_task6_review_log: "logs/review/2026-05-14-01-review.md"
last_task6_at: "2026-05-14T01:14:00+08:00"
last_task6_audit: 2026-07-15
task9_result: auto-fixed
task9_reviewed_date: 2026-05-14
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-08T05:20:00+08:00"
last_task9_audit: 2026-06-08
last_task9_autofix_at: 2026-06-08
last_task9_review_log: logs/deep-review/2026-06-08-05-audit.md
task9_review_notes: "2026-06-08 Task9 idle audit：AUTO-FIX，补充 API 34+/35+ onTrimMemory 等级边界，回到 Task6 复审。"
task2b_result: fixed
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-18
task2b_state: fixed
last_task2b_verifier_at: "2026-06-14T11:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-14-11-task2b-verifier.md"
consolidated_from:
  - "src/part5-app/ch23-memory-practice/23.26-art-heap-distribution-oom-trigger-path.md"
---

# Java Heap 优化策略

> **版本基线**
>
> 平台行为与源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。涉及旧版本的内容只说明 API 或行为变化，不高于 Android 17。

## 为什么要了解 Java Heap 优化策略

Java Heap 优化处理的是应用侧对象分配、对象生命周期和缓存预算之间的关系。内存泄漏章节处理“该释放的对象没有释放”，Bitmap 章节处理“像素内存太大”，这一节转到应用侧常见的堆压力：对象本身仍有业务价值，但分配时机、集合规模、缓存策略或临时对象频率让堆压力升高。

Android 会为每个应用进程设置 Java Heap 上限，无法在上限内完成分配时会抛出 `OutOfMemoryError`。Android Studio Profiler 可以观察堆曲线、对象数量和 GC 事件。工程判断不能只看一次 `Runtime.maxMemory()`：还要比较同一场景的分配速度、峰值、退出后的存活对象和 GC 行为。堆曲线回落说明对象有机会被回收，不代表对应页面已经满足性能目标；曲线不立即回落也可能来自 ART 的目标堆大小，而非泄漏。

ART 堆空间、分配器和 GC 细节详见 4.3 节；分代 GC 与暂停分析详见 4.8 节；内存泄漏治理详见 23.1 节；内存抖动与 GC 治理详见 23.5 节。应用侧动作包括少分配、晚分配、按预算缓存，并在生命周期边界清理。

## Java Heap 空间组成与分配策略

应用代码创建的对象不会都进入同一种 ART space。普通对象使用哪条分配路径，取决于当前 collector 和 allocator 配置，可能涉及 Region Space、Bump Pointer Space 或其他连续空间；应用不能把它简化为固定的“Main Space”。对于达到内部阈值的特定对象，ART 还会尝试 Large Object Space。

Android 17 的 `Heap::ShouldAllocLargeObject()` 同时检查两个条件：分配字节数达到 `large_object_threshold_`，并且对象类型是 primitive array 或 `String`。满足条件时，分配器会尝试 `AllocLargeObject()`；如果 Large Object Space 分配失败，源码还会清除本次 OOM 并尝试普通空间。这个阈值是 ART 内部配置，不是应用 API，也不应在业务代码中复制一个固定数值。

体积较大的 `ByteArray`、`IntArray` 或字符串构造结果，除了增加存活字节数，还可能进入不同的分配与回收路径。优化动作仍应从数据形态入手：能否分块读取、缩短生命周期或避免复制，而不是依据 Large Object Space 名称写特殊业务分支。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap-inl.h::Heap::ShouldAllocLargeObject()`, `art/runtime/gc/heap-inl.h::Heap::AllocObjectWithAllocator()`]

堆上限不等于进程物理内存占用。`Heap::GetMaxMemory()` 对应 `Runtime.maxMemory()`；Android 应用以 `growth_limit_` 为限制，`largeHeap` 应用会把它扩展到 heap capacity。`GetFreeMemoryUntilOOME()` 用 `growth_limit_` 与当前已分配字节数估算 OOM 前的余量。PSS 还包含 Java Heap 之外的映射和按比例计入的共享页，必须与逻辑堆值分开分析。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap.h::GetMaxMemory()`, `GetFreeMemoryUntilOOME()`]

应用侧判断堆压力时，可以用三组数：

- `Runtime.maxMemory()`：当前进程 Java Heap 上限，是制定缓存预算的输入之一，不能直接乘固定比例得出所有设备通用的预算。
- `Runtime.totalMemory() - Runtime.freeMemory()`：ART 当前已使用 Java Heap 的近似值，适合在同一构建、同一设备上观察趋势。
- heap dump / allocation recording：前者观察快照时仍然存活的对象与引用链，后者观察目标窗口内的分配次数、大小和调用栈。采集本身有成本，应放在可控诊断流程中。

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

这段代码只能做趋势信号。它不知道对象是否可回收，也不知道 Native、Graphics 等进程内存；单次超过阈值不能证明泄漏。线上若采用该信号，还要限制采样频率、合并连续事件，并同时记录场景与缓存命中变化。

## ART 分配失败与 OOM 触发路径

普通对象的快路径失败后，`Heap::AllocateInternalWithGc()` 不会立即抛出 OOME。Android 17 会先等待正在运行的 GC；若等待期间完成过回收则重试分配；随后按 `next_gc_type_` 执行 blocking GC，必要时使用覆盖范围更大的回收并清除 SoftReference。对支持的 allocator，运行时还可能在满足配置和时间间隔时尝试 homogeneous space compaction。仍无法满足请求，才进入 OOME。

这里没有设备无关的“Young GC → Full GC”固定两步顺序。`next_gc_type_` 取决于 collector、代际状态、上次 GC 和 heap 目标。分配线程也可能主要耗时在等待另一线程执行 GC，因此 Perfetto 中的业务停顿可能长于单次 pause。

### 读懂 OOME 文本

Android 17 的典型错误会包含本次 allocation size、free bytes、until OOM、target footprint 和 growth limit：

```text
Failed to allocate a 48 byte allocation with 3610680 free bytes and
3526KB until OOM, target footprint 536870912, growth limit 536870912;
giving up on allocation because <1% of heap free after GC.
```

- `free bytes` 是 ART 统计的 heap 空闲总量，不保证目标 allocator 有合适连续块；
- `until OOM` 是距离 growth limit 的估算增长空间；
- `target footprint` 是当前调节目标，会随 GC 和分配变化，不是硬上限；
- `growth limit` 才是普通应用 Java Heap 的增长限制；
- `<1% ... after GC` 表示完成本次分配后无法保留运行时要求的最小空闲比例。

小对象也可能在堆贴近限制时失败；大数组失败还要检查输入尺寸、乘法溢出和连续空间。ART 构造 OOME 本身再次失败时会使用启动阶段预分配的异常对象，所以线上不应假设每次都有完整错误文本，也不要在 OOM handler 中再创建大集合或同步抓取完整 heap dump。

### 先区分四种“内存不足”

| 现场 | 主要证据 | 排查方向 |
| --- | --- | --- |
| Java Heap OOM | `Failed to allocate`、对象存活集、growth limit | 泄漏、合法存活集、分配抖动、单次大对象 |
| Native allocation 失败 | `malloc` / `mmap` 错误、native 栈、PSS/VMA | allocator、匿名映射、Graphics、请求大小 |
| Thread OOM | `pthread_create (... stack) failed`、线程数、errno | 每线程栈、VMA、native memory、task limit |
| FD / 地址空间耗尽 | `EMFILE` / `ENOMEM`、fd/VMA/最大连续空洞 | 资源关闭、32 位地址空间、线程与映射数量 |

Native 失败只有部分 Framework/JNI 入口会转换为 Java OOME；FD 用尽也通常直接返回 `EMFILE`。不要把所有带 `OutOfMemoryError` 或 `ENOMEM` 的现场都归入 ART 对象泄漏。

### 不修改 ART 内部计数来“扩堆”

`largeHeap` 只扩展 Java Heap growth limit，不增加设备 RAM，也不处理 native、Graphics、线程栈或无界缓存。修改 `num_bytes_allocated_`、`large_object_threshold_`、伪造 freed bytes、hook allocator 绕过 GC 或解除 ART Space mapping，会破坏 allocation counter、bitmap、card table、Space membership 与 GC root 的一致性，不能进入生产方案。Android 17 的 LOS 源码也不存在所谓固定 512 MiB `mSponge` 平台能力。

## 大对象与集合优化

大对象优化先从“减少一次性装入”开始。服务端返回几 MB JSON、一次性读完整文件、把长日志拼成一个 `String`、把列表全量映射成 ViewModel，都会把 Java Heap 压力集中到一个短窗口里。GC 能回收不可达对象，但它不能替业务决定哪些对象不该一次性加载。

处理大对象时按这个顺序排查：

- **输入是否可以分页或流式处理**：列表接口、文件读取、日志解析优先改成 page / chunk / stream，不把完整数据一次性放进内存。
- **中间态是否可以消除**：JSON 字符串、DTO、领域模型、UI 模型多层复制时，检查是否能在边界处直接转换，少保留一份大集合。
- **字符串构造是否有上限**：日志、埋点、调试面板不要无限拼接；给 builder 设置长度上限，超过后截断或落文件。
- **数组容量是否按需增长**：已知数量时可以传入合理的初始容量；未知数量时不应凭空预留大数组。只有剖析表明扩容复制或长期空余容量形成主要成本时，才值得更换容器或重建紧凑副本。

集合优化不能停在“换一个集合类”。`ArrayList`、`HashMap`、`SparseArray`、`ArrayMap` 的选择依据是元素数量、key 类型、访问模式、写入频率和生命周期。整数 key 可以避免 `HashMap<Int, ...>` 的装箱成本，但是否使用 `SparseArray` 仍要结合 CPU 与内存测量。不要写一个固定的元素数量分界线，因为设备、访问模式和实现版本都会改变结果。

下面的示例适用于数据能够以 `Sequence` 提供、且只需要前 `limit` 个结果的场景。它避免由 `filter()` 和 `map()` 各自产生一份完整中间列表。

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

收益主要来自 `take(limit)` 的结果上限，以及惰性操作避免完整中间集合。`Sequence` 自身也会创建操作包装对象并增加迭代调用；如果源数据已经完整驻留，或集合很小，它未必更省时。应使用 allocation recording 与基准测试同时比较分配字节数、对象数和 CPU 时间。

## 对象池与缓存策略

对象池和缓存都在用空间换时间，区别在于目标不同。对象池减少重复分配，缓存减少重复计算或重复 I/O。两者都要有上限、失效条件和生命周期归属，否则优化很快会变成常驻内存。

缓存预算不能只按“最大堆的固定比例”决定。要同时测量对象大小、峰值并发、重建成本、命中收益和设备内存档位：首屏与高频路径可以保留有界缓存，低频内容更适合缩小容量或在离开场景时移除。弱引用的回收时机由 GC 决定，不能替代容量和淘汰策略。

`onTrimMemory()` 还需要区分进程状态提示与内存压力提示。`TRIM_MEMORY_UI_HIDDEN` 表示 UI 已不可见，`TRIM_MEMORY_BACKGROUND` 表示进程进入后台 LRU，它们适合触发与对应状态相关的缓存收缩。从 API 34 开始，`TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE` 和 `TRIM_MEMORY_COMPLETE` 不再投递给应用；这些常量从 API 35 起标记为 deprecated。因此，Android 17 应用不能等待旧的 running-level 回调来处理前台内存压力。

下面的 `LruCache` 示例缓存原始字节负载，使 `sizeOf()` 至少能精确计算 value 的字节数；收到 UI 隐藏或进入后台的提示后，再按业务策略降低容量。

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

这里的计量仍未包含 key、`LruCache` entry 和对象头开销，所以 `maxBytes` 是 value payload 预算，不是整个缓存的 shallow size。字符串、图片引用和解析对象需要各自的计量口径。两个降级预算由调用方根据业务测量传入，示例没有设置通用比例。兼容 API 33 及以下时可以处理旧的 running level，但 Android 17 路径不应依赖这些不会到达的回调。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/content/ComponentCallbacks2.java`, `frameworks/base/core/java/android/util/LruCache.java`]

对象池只适合满足三个条件的对象：创建频繁、初始化成本高、可安全重置。普通 data class、生命周期复杂的对象、持有 `Context` / View / callback 的对象，不建议放进池。池化后的对象一旦忘记清字段，泄漏和脏数据会比原来的分配成本更贵。

对象池还要跟 ART 分代 GC 分开评估：短命小对象在现代 ART 上可能很便宜，强行池化会把短命对象变成长命对象，增加老年代压力。和 4.8 节里的分代 GC 逻辑对照看，池化的判断标准应该是“分配热点是否导致可观测 GC 或 CPU 压力”，不是“看到 new 就消灭”。

## GC 友好的编码实践

GC 友好的代码要让分配符合场景节奏：启动、首帧、滑动、动画、输入响应期间少制造短时间高峰；页面退出、后台切换、系统 trim 时能释放；后台任务和低优先级计算不要跟前台帧争资源。

可执行的检查项有这些：

- **启动阶段控制初始化范围**：只创建首屏和启动链依赖的对象。延迟初始化是否移到后台线程，要同时检查线程安全、I/O 和 CPU 竞争；“后台执行”不会消除分配成本。
- **滑动阶段少建临时对象**：`onBindViewHolder()`、`onDraw()`、触摸回调里避免格式化字符串、创建临时集合、重复构造匿名对象。高频回调里的分配要用 allocation recording 验证。
- **批处理阶段控制峰值**：大量数据转换分批执行，每批结束释放中间态。协程或线程池只是调度工具，不会自动降低堆峰值。
- **生命周期边界清理长生命周期引用**：例如 Fragment 在 `onDestroyView()` 清理 ViewBinding 和与 View 生命周期绑定的 adapter/callback。不要机械地清除仍由下一状态使用的数据；引用归属应与生命周期一致。
- **监控对象数量和 GC 事件**：Memory Profiler 能显示 Java 对象数量与 GC 事件；线上轻量监控只保留趋势指标，定位问题再回到线下 heap dump 和 allocation recording。

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

`NumberFormat` 不是线程安全对象，这个 binder 和 formatter 应限制在 RecyclerView 所在的主线程。把所有临时对象都改成成员会延长生命周期，可能增加长命对象数量。判断改动是否有效，要同时比较绑定阶段的 allocation count、GC 事件和帧耗时。

## ART GC 调优参数

`growth_limit_`、`target_footprint_`、`concurrent_start_bytes_`、`large_object_threshold_` 等变量解释了 ART 何时扩堆、何时触发并发 GC、哪些对象走大对象路径，但它们不是面向普通应用暴露的配置接口，不要当作常规调优手段。

`android:largeHeap="true"` 会让 ART 把应用的 growth limit 扩展到 heap capacity，但 capacity 仍由设备配置决定。它不会消除泄漏、无上限缓存或大对象峰值，也不保证某个固定的额外容量。只有图片编辑、大文档处理、地图或创作工具等经过测量后仍有合理大内存需求的业务，才值得单独评估；同时要观察进程 PSS、后台存活和低内存终止情况。

GC 抑制和 ART Hook 依赖非公开实现，会受 ART 更新、线程协作和 GC 时序影响，不适合作为通用应用方案。应用侧应修正启动、滑动与批处理期间的分配热点，不要阻塞 HeapTaskDaemon 或修改 ART 内部状态。

评审时可以用下面的表格判断方案边界：

| 方案 | 适用场景 | 风险 |
| --- | --- | --- |
| 降低缓存预算 | 大多数应用 | 命中率下降，需要业务指标一起看 |
| `onTrimMemory()` 状态化释放 | UI 隐藏、进入后台 LRU | 释放过多会导致回到前台后重新加载 |
| 分页 / 流式处理 | 大列表、大文件、大响应 | 改造成本取决于接口和数据模型 |
| 对象池 | 高频、可重置、初始化贵的对象 | 脏字段、泄漏、老年代压力 |
| `largeHeap` | 明确需要大内存的少数场景 | 掩盖问题，增加系统内存压力 |
| ART Hook / GC 抑制 | 专项实验或厂内框架 | 版本兼容、稳定性和审核风险高 |

## 排查路径：从堆曲线到代码改动

Java Heap 优化可以按四步推进：

1. 用 Memory Profiler 录制目标场景，记录对象数量、堆曲线和 GC 事件。
2. 如果曲线持续上升且页面退出后不回落，转 23.1 节的泄漏排查。
3. 如果曲线有尖峰但能回落，检查大对象、集合复制、缓存预算和批处理峰值。
4. 如果 GC 频率高且伴随卡顿，转 23.5 节看内存抖动，再据此减少分配热点。

Android 17 / API 37 为 `ProfilingTrigger` 增加 `TRIGGER_TYPE_OOM` 和 `TRIGGER_TYPE_ANOMALY`。OOM 触发器为未捕获的 `OutOfMemoryError` 采集 Java heap dump；自定义 `Thread.UncaughtExceptionHandler` 必须继续调用默认 handler，系统才能观察到该事件。anomaly 触发器可报告包括过量内存在内的系统异常，返回的 artifact 类型由异常决定。这些能力用于取得难以在线下复现的证据，不替代堆预算和代码修正。具体的生产监控与 Android 17 内存限制分别见 23.7、23.6 节。

一次有效改动至少要回答三件事：分配对象数或字节数是否下降，峰值或稳定占用是否改善，CPU、I/O、网络请求与用户场景指标是否出现回退。只降低 Java Heap 峰值却增加其他资源成本，不能视为完成优化。

## 参考资料

- [Android Developers：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Android Developers：Overview of memory management](https://developer.android.com/topic/performance/memory-overview)
- [Android Developers：`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Android Developers：`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android Developers：Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [Android Developers：Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [AOSP `android-17.0.0_r1`, ART `heap.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.h)
- [AOSP `android-17.0.0_r1`, ART `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP `android-17.0.0_r1`, ART `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `android-17.0.0_r1`, `ComponentCallbacks2.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP `android-17.0.0_r1`, `LruCache.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/util/LruCache.java)
