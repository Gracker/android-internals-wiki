---
title: "Java Heap 优化策略"
chapter: "23.4"
section: "23.4"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers ComponentCallbacks2 + Clippings/Android 性能优化"
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
---

# Java Heap 优化策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Java Heap 空间组成与分配策略
- 🔹 大对象与集合优化
- 🔹 对象池与缓存策略
- 🔹 GC 友好的编码实践

### 扩展（可选深入）

- 🔸 ART GC 调优参数

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Java Heap 优化策略

Java Heap 优化处理的是应用侧对象分配、对象生命周期和缓存预算之间的关系。内存泄漏章节处理“该释放的对象没有释放”，Bitmap 章节处理“像素内存太大”，这一节转到应用侧常见的堆压力：对象本身仍有业务价值，但分配时机、集合规模、缓存策略或临时对象频率让堆压力升高。

Android Developers 的内存文档给了两个判断口径：Android 会给每个应用进程设置堆上限，应用超过堆容量继续分配会触发 `OutOfMemoryError`；Memory Profiler 可以观察内存曲线、Java 对象数量和 GC 事件。工程上不要只看一次 `maxMemory()`，还要看场景里的增长速度、峰值、回落能力和 GC 频率。

ART 堆空间、分配器和 GC 细节详见 4.3 节；分代 GC 与暂停分析详见 4.8 节；内存泄漏治理详见 23.1 节；内存抖动与 GC 治理详见 23.5 节。本节把这些机制转成应用侧可执行动作：少分配、晚分配、按预算缓存、在生命周期边界清理。


## Java Heap 空间组成与分配策略


应用代码里 `new` 出来的对象不会均匀落在一整块抽象堆里。ART 会按对象性质和回收器配置把对象放到不同空间中，应用侧最需要关心的是 Main Space 和 Large Object Space：普通对象通常进入 Main Space，满足大对象条件的基本类型数组或 `String` 会走 Large Object Space。

AOSP `Heap::ShouldAllocLargeObject()` 的判断包含两个条件：分配字节数达到 `large_object_threshold_`，并且对象类型是 primitive array 或 `String`。这会影响优化动作的优先级。体积较大的 `ByteArray`、`IntArray` 或字符串拼接结果，除了占用更多字节，还可能走另一条分配路径，回收与碎片风险也会不同。

堆上限不等于进程物理内存占用。AOSP `Heap::GetMaxMemory()` 对应 `Runtime.maxMemory()`，注释里写明 Android 应用从 growth limit 起步，large app 会扩展这个限制；`GetFreeMemoryUntilOOME()` 用 `growth_limit_ - GetBytesAllocated()` 估算距离 OOM 的空间。Android Developers 也强调，堆的逻辑大小和 PSS 这样的物理内存口径不同，排查时要分开看。

应用侧判断堆压力时，可以用三组数：

- `Runtime.maxMemory()`：当前进程 Java Heap 的上限，用来决定缓存总预算，不能拿一台高端机的结果套到低端机。
- `Runtime.totalMemory() - Runtime.freeMemory()`：虚拟机已经分配且正在使用的近似值，适合做轻量趋势监控。
- Memory Profiler / heap dump / allocation recording：用于定位“谁在分配”和“谁没有释放”，不要把线上每分钟轮询做成重型分析。

下面这段工具函数用于给缓存管理器提供堆压力信号，看 `usedRatio` 的计算和触发阈值即可。

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

    fun shouldTrimCache(threshold: Double = 0.75): Boolean {
        return snapshot().usedRatio >= threshold
    }
}
```

这段代码只能做轻量信号，不能替代 heap dump。线上使用时还要加采样、冷却时间和场景标签，避免在短时间内反复清缓存，把缓存命中率打低。

## 大对象与集合优化


大对象优化先从“减少一次性装入”开始。服务端返回几 MB JSON、一次性读完整文件、把长日志拼成一个 `String`、把列表全量映射成 ViewModel，都会把 Java Heap 压力集中到一个短窗口里。GC 能回收不可达对象，但它不能替业务决定哪些对象不该一次性加载。

处理大对象时按这个顺序排查：

- **输入是否可以分页或流式处理**：列表接口、文件读取、日志解析优先改成 page / chunk / stream，不把完整数据一次性放进内存。
- **中间态是否可以消除**：JSON 字符串、DTO、领域模型、UI 模型多层复制时，检查是否能在边界处直接转换，少保留一份大集合。
- **字符串构造是否有上限**：日志、埋点、调试面板不要无限拼接；给 builder 设置长度上限，超过后截断或落文件。
- **数组容量是否按需增长**：已知数量时预估容量，未知数量时避免频繁扩容后留下大数组；容量长期明显大于元素数时，重新创建小容器比继续持有更稳。

集合优化不要停在“换一个集合类”。`ArrayList`、`HashMap`、`SparseArray`、`ArrayMap` 各有适用区间，选择依据是元素数量、key 类型、访问频率和生命周期。几十个以内的 `Int` key 映射可以考虑 `SparseArray`，但高频查找的大集合仍要用基准测试确认 CPU 代价。内存少了但查找变慢，滑动和启动场景可能会把问题从堆转到 CPU。

下面这段代码展示列表页聚合数据的写法。它避免把完整响应、中间列表和 UI 列表同时长期持有。

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

这段代码的收益来自边界控制：`Sequence` 让过滤和映射按元素推进，`take(limit)` 给结果规模设上限。它不适合所有场景；如果数据源已经是一个完整 `List`，收益会变小。要用 allocation recording 看对象数和总字节数是否下降。

## 对象池与缓存策略


对象池和缓存都在用空间换时间，区别在于目标不同。对象池减少重复分配，缓存减少重复计算或重复 I/O。两者都要有上限、失效条件和生命周期归属，否则优化很快会变成常驻内存。

缓存预算不要按“最大堆的固定比例”拍脑袋。缓存预算应按业务价值分层：首屏和高频路径拿稳定预算，低频页面用小缓存或弱缓存，后台后响应 `onTrimMemory()` 释放 UI 相关对象。Android Developers 建议应用在内存紧张或生命周期变化时主动释放内存，`onTrimMemory()` 是应用侧接收系统压力信号的标准入口。

版本边界要分开看：从 API 34 开始，`TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 不再投递给 App；API 35 起这些常量在 SDK 中标记为 deprecated。`TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND` 仍可作为 UI 不可见、进入后台 LRU 后的释放入口。

下面这段 `LruCache` 代码保留两个策略：按字节计量，收到系统 trim 信号后主动降级。

```kotlin
class StringPayloadCache(
    maxBytes: Int
) : LruCache<String, String>(maxBytes) {
    override fun sizeOf(key: String, value: String): Int {
        return value.length * Char.SIZE_BYTES
    }

    fun trimFor(level: Int) {
        when {
            level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> trimToSize(maxSize() / 2)
            level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> trimToSize(maxSize() * 3 / 4)
        }
    }
}
```

`sizeOf()` 必须贴近对象真实占用，否则 `LruCache` 的上限会失真。字符串、字节数组、图片引用、解析结果不要共用同一套估算方式。收到 `TRIM_MEMORY_UI_HIDDEN` 时，只清 UI 相关缓存；收到 `TRIM_MEMORY_BACKGROUND` 后，再处理跨页面共享缓存。兼容 API 33 及以下时，可以单独处理 `TRIM_MEMORY_RUNNING_*` 前台压力等级；API 34+ 设备上不要把它们作为主要内存压力信号。

对象池只适合满足三个条件的对象：创建频繁、初始化成本高、可安全重置。普通 data class、生命周期复杂的对象、持有 `Context` / View / callback 的对象，不建议放进池。池化后的对象一旦忘记清字段，泄漏和脏数据会比原来的分配成本更贵。

对象池还要跟 ART 分代 GC 分开评估：短命小对象在现代 ART 上可能很便宜，强行池化会把短命对象变成长命对象，增加老年代压力。和 4.8 节里的分代 GC 逻辑对照看，池化的判断标准应该是“分配热点是否导致可观测 GC 或 CPU 压力”，不是“看到 new 就消灭”。

## GC 友好的编码实践


GC 友好的代码要让分配符合场景节奏：启动、首帧、滑动、动画、输入响应期间少制造短时间高峰；页面退出、后台切换、系统 trim 时能释放；后台任务和低优先级计算不要跟前台帧争资源。

可执行的检查项有这些：

- **启动阶段少建全局对象**：全局服务、单例缓存、配置表、路由表按使用时机延后创建。启动只保留首屏必需对象，其他模块通过懒加载或后台预热处理。
- **滑动阶段少建临时对象**：`onBindViewHolder()`、`onDraw()`、触摸回调里避免格式化字符串、创建临时集合、重复构造匿名对象。高频回调里的分配要用 allocation recording 验证。
- **批处理阶段控制峰值**：大量数据转换分批执行，每批结束释放中间态。协程或线程池只是调度工具，不会自动降低堆峰值。
- **生命周期边界清引用**：页面退出时清 listener、adapter、callback、缓存条目。泄漏治理详见 23.1 节，这里只强调它对堆回落曲线的影响。
- **监控对象数量和 GC 事件**：Memory Profiler 能显示 Java 对象数量与 GC 事件；线上轻量监控只保留趋势指标，定位问题再回到线下 heap dump 和 allocation recording。

下面这段写法用于高频绑定场景，目标是避免在每次绑定时创建格式化器和临时字符串模板对象。

```kotlin
class PriceFormatter(
    private val numberFormat: NumberFormat = NumberFormat.getCurrencyInstance(Locale.CHINA)
) {
    fun formatFen(fen: Long): String {
        return numberFormat.format(fen / 100.0)
    }
}

class GoodsAdapter(
    private val formatter: PriceFormatter
) : RecyclerView.Adapter<GoodsViewHolder>() {
    override fun onBindViewHolder(holder: GoodsViewHolder, position: Int) {
        val item = getItem(position)
        holder.titleView.text = item.title
        holder.priceView.text = formatter.formatFen(item.priceFen)
    }
}
```

这类改动要防止走到另一个极端。把所有对象都提到成员变量会增加生命周期，可能把短命对象变成长命对象。判断标准仍然是数据：绑定阶段 allocation count 是否下降，GC 事件是否减少，帧耗时是否更稳定。

## ART GC 调优参数


`growth_limit_`、`target_footprint_`、`concurrent_start_bytes_`、`large_object_threshold_` 等变量解释了 ART 何时扩堆、何时触发并发 GC、哪些对象走大对象路径，但它们不是面向普通应用暴露的配置接口，不要当作常规调优手段。

`android:largeHeap="true"` 也不能当默认方案。它会让部分设备给进程更大的堆上限，但不会消除泄漏、无上限缓存和大对象峰值；它还会让单进程占用更高，增加系统回收后台进程的压力。只有图片编辑、大文档处理、地图、创作工具这类明确需要大内存且已做过分层释放的业务，才值得单独评估。

参考书里提到的 GC 抑制和 ART Hook 属于高风险方案，不建议作为通用手段。更安全的做法是减少启动和滑动期间的分配热点，而不是阻塞 HeapTaskDaemon 或修改 ART 内部行为。

评审时可以用下面的表格判断方案边界：

| 方案 | 适用场景 | 风险 |
| --- | --- | --- |
| 降低缓存预算 | 大多数应用 | 命中率下降，需要业务指标一起看 |
| `onTrimMemory()` 分级释放 | 前后台切换、系统内存紧张 | 释放过猛会导致回到前台后重新加载 |
| 分页 / 流式处理 | 大列表、大文件、大响应 | 改造成本取决于接口和数据模型 |
| 对象池 | 高频、可重置、初始化贵的对象 | 脏字段、泄漏、老年代压力 |
| `largeHeap` | 明确需要大内存的少数场景 | 掩盖问题，增加系统内存压力 |
| ART Hook / GC 抑制 | 专项实验或厂内框架 | 版本兼容、稳定性和审核风险高 |

## 排查路径：从堆曲线到代码改动


Java Heap 优化可以按四步推进：

1. 用 Memory Profiler 录制目标场景，记录对象数量、堆曲线和 GC 事件。
2. 如果曲线持续上升且页面退出后不回落，转 23.1 节的泄漏排查。
3. 如果曲线有尖峰但能回落，检查大对象、集合复制、缓存预算和批处理峰值。
4. 如果 GC 频率高且伴随卡顿，转 23.5 节看内存抖动；再回到本节减少分配热点。

一次有效改动要同时给出三项证据：对象分配数下降、峰值或常驻占用下降、用户场景指标不变差。只降低 Java Heap 峰值但让 CPU、I/O 或网络请求增加，也可能把问题转移到其他章节。
