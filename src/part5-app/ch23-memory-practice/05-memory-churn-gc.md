---
title: "内存抖动与 GC 治理"
chapter: "23.5"
section: "23.5"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1；Android 16 QPR2 分代 CMC、Android Studio 分配记录、Perfetto ART allocation profiling 与 ComponentCallbacks2 官方文档"
last_review_finalize_at: "2026-08-15T07:40:39+08:00"
last_review_finalize_run_id: "20260815-074039-gracker-writing-review"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/studio/profile/memory-profiler"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-allocations"
  - type: official
    path: "https://source.android.com/docs/core/runtime/gc-debug"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/about/versions/16/qpr2/release-notes"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/reference/android/content/ComponentCallbacks2"
  - type: aosp
    path: "https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/libart/src/main/java/java/lang/Daemons.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/task_processor.cc"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
tags: [memory-churn, gc, allocation, autoboxing]
related_chapters: ["23.4", "10.6", "4.3", "7.2"]
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T07:40:39+08:00"
last_draft_polish_run_id: "20260815-074039-gracker-writing"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
  - "src/part5-app/ch23-memory-practice/23.6-heaptask-concurrent-gc-suppression.md"
---

# 内存抖动与 GC 治理

> **版本基线**
>
> 平台实现统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。历史版本只用于说明 collector 和工具能力的演进，最高版本为 Android 17。

## 内存抖动需要解决什么

内存抖动指短时间内反复分配对象，对象很快失去引用，又持续增加回收工作的现象。泄漏会让不再需要的对象长期保持可达，抖动对象通常能被回收，两种问题也可能同时出现。[23.4 Java Heap 优化策略](./04-java-heap-optimization.md)解释堆预算与缓存控制，[10.6 内存抖动与频繁 GC](../../part2-performance/ch10-memory-perf/06-memory-churn.md)和 [4.3 ART 虚拟机内存管理](../../part1-fundamentals/ch04-memory/03-art-memory.md)给出运行时与工具原理，[7.2 卡顿原因体系](../../part2-performance/ch07-smoothness/02-jank-causes.md)说明慢帧的其他来源。本文聚焦应用侧如何降低启动、首帧、滑动和动画期间的分配峰值。

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

## 内存抖动的成因与表现

内存抖动同时受分配大小、分配频率和对象存活时间影响。大量小对象会迅速增加累计分配字节数，大对象则可能直接形成峰值；只按对象大小排序会漏掉高频调用栈。

Android 17 的 `Heap::AllocObjectWithAllocator()` 在分配记账后调用 `ShouldConcurrentGCForJava(new_num_bytes_allocated)`。启用按时间触发 GC 的功能开关且 `time_based_gc_threshold_` 非零时，该函数结合上次 GC 后新增的字节数与经过时间，决定立即请求 GC，还是安排一次阈值复查；`concurrent_start_bytes_` 仍是接近堆限制时的兜底阈值。未启用这条路径时，判断只比较已分配字节数与 `concurrent_start_bytes_`。对象完成初始化并可交给应用代码后，`RequestConcurrentGCAndSaveObject()` 才把 `ConcurrentGCTask` 加入队列。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap-inl.h::Heap::AllocObjectWithAllocator()`, `Heap::ShouldConcurrentGCForJava()`, `art/runtime/gc/heap.cc::Heap::RequestConcurrentGC()`]

从应用层来看，内存抖动通常表现为四种现象：

- **堆曲线呈锯齿状**：内存快速上升，GC 后又下降，周期很短。单次峰值可能不高，但回收频率高。
- **Logcat 或系统跟踪里 GC 密集**：`HeapTaskDaemon` 活跃，Perfetto 或旧版 Systrace 能看到多个 GC 时间片集中在交互窗口附近。
- **帧耗时波动**：Frame Timeline 里的慢帧可能间隔出现，并集中在滑动、动画或连续输入期间。
- **分配慢路径或等待**：线程在分配时等待 GC 完成，或进入需要扩展、回收的慢路径。业务函数自身的 CPU 执行时间可能不高，但包含等待的经过时间会变长。

Android 8 起，ART 默认使用 Concurrent Copying；官方 GC 文档说明 Android 10 及以上的 CC 默认采用分代模式。Android 16 QPR2（第二次季度平台更新）对外发布分代 CMC，Android 17 源码继续保留相应的年轻代收集器和运行时开关。具体进程使用哪种收集器、是否启用分代，仍取决于运行时和设备配置；Android 17 的 `PostForkChildAction()` 会在日志中输出 `generational` 或 `non-generational` 以及收集器名称，可与系统跟踪一起确认。

## 频繁 GC 对帧率的影响

GC 对帧率的影响主要来自两类成本：部分阶段短暂停顿应用线程，以及后台 GC 线程与渲染线程竞争 CPU。AOSP `Daemons.java` 中的 `HeapTaskDaemon` 会调用 `VMRuntime.getRuntime().runHeapTasks()`；`TaskProcessor::RunAllTasks()` 从队列取出 `HeapTask` 并执行。Android Developers 的慢渲染文档也说明，新版 Android 的 GC 通常由名为 `HeapTaskDaemon` 的后台线程运行；大量分配会增加 GC 的 CPU 工作。

每帧预算由屏幕刷新率决定，不能固定写成某个毫秒数。滑动时主线程、RenderThread、图片解码线程和后台任务共同使用 CPU；GC 工作与帧生产重叠时，可能增加调度等待、内存带宽压力或短暂停顿。是否影响用户可见帧必须由 Frame Timeline 与线程轨道证明。

排查时不要只看单次 GC 耗时。相同的 GC 工作出现在空闲窗口与关键帧窗口，用户影响不同。应在同一份系统跟踪中比较三类轨道：

- **Frame Timeline**：确认 missed frame、slow frame 和 present 结果，判断是否影响用户可见帧。
- **主线程 / RenderThread**：确认帧生产阶段是否被分配、锁、Binder 或调度延迟干扰。
- **HeapTaskDaemon / GC 事件**：确认 GC 是否和帧尖峰重叠，不能只根据内存曲线猜。

时间重叠只能建立相关性，还要检查主线程和 RenderThread 的状态。`Running` 表示线程正在 CPU 上执行，应查看对应 slice 或调用栈；`Runnable` 表示线程已就绪却没有获得 CPU，才更支持调度延迟或 CPU 竞争；`Sleeping`、`Blocked` 等状态要继续追踪唤醒者、锁、Binder 或其他等待原因。GC 与慢帧相邻但不重叠，也不能据此判定因果。

### Android 17 在应用进程创建后安排的 GC

Android 17 的 `Heap::PostForkChildAction()` 在 `initial_heap_size_ < growth_limit_` 时安排目标堆大小调整，并为 Zygote 复制出的应用进程加入 `TriggerPostForkCCGcTask`。该任务只有在计划时间到达、且进程创建后尚未发生其他 GC 时，才请求一次后台 GC；期间已经发生 GC 时不再执行回收。调度时间包含一个以 UID 为种子的确定性偏移：同一 UID 得到相同偏移，不同 UID 通常不同。根据源码注释，这个偏移用于降低多个进程同时发起此类 GC 的概率。

因此，启动后看到一次后台 GC 时，要同时查看 GC cause（触发原因）、进程启动时间和前后的分配轨道。不能仅凭“启动附近出现 GC”就归因到某个页面的临时对象。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap.cc::Heap::PostForkChildAction()`, `TriggerPostForkCCGcTask`]

### HeapTaskDaemon 串行执行整条堆任务队列

`HeapTaskDaemon` 进入 `VMRuntime.runHeapTasks()` 后，由 ART 原生层的 `TaskProcessor::RunAllTasks()` 按 `target_run_time_`（计划运行时间）取任务。一次循环只执行一个 `HeapTask`：依次调用 `GetTask()`、`Run()` 和 `Finalize()`，再取下一项。`ConcurrentGCTask` 中的 Concurrent 表示收集器的部分阶段可与应用线程并发，不表示多个堆任务会在守护线程上并行执行。

这条队列还承载 HeapTrim（向系统归还可释放堆页）、收集器切换、按时间触发 GC 的阈值复查和部分启动维护。向它注入阻塞任务或暂停守护线程，会一起延迟这些工作。`TaskProcessor::Stop()` 只把处理器标记为停止；`GetTask()` 随后不再等待任务的计划时间，而是继续取出剩余任务，直到队列排空。错误干预可能让未到期任务集中执行。

### 并发 GC 请求如何判定和去重

Android 17 的 `ShouldConcurrentGCForJava()` 有字节阈值和“分配增量 × 经过时间”两类判断。它可能返回“不需要 GC”“请求 `ConcurrentGCTask`”或“安排 `TimeBasedGcThresholdCheckTask`”。`num_bytes_allocated_` 会把仍在使用的整块 TLAB 计入，因此是近似已分配字节数，不是逐对象精确值，也不是 PSS。

多个线程同时满足条件时，`RequestConcurrentGC()` 使用原子 compare-and-set（仅当旧值未变化时更新）增加 `max_gc_requested_`；只有更新成功的线程把任务加入队列。任务执行时还会检查目标序号，若其他路径已经完成更新的 GC，本次任务不会重复收集。去重依赖这个序号协议，而不是扫描队列里是否已有同名任务。

新对象在请求入队期间由 Handle 临时保护，因为 `TaskProcessor::AddTask()` 可能让线程挂起，移动式 GC 也可能在此时更新对象地址。Handle 只用于保证 ART 内部引用安全，应用代码不能取得或复用这套机制。

## 典型内存抖动场景

调用频率比代码表面的复杂度更值得优先检查。一次分配在点击按钮时没有问题，放到 `onDraw()`、`onBindViewHolder()`、`onTouchEvent()`、Compose 重组或动画回调里，就会随帧数重复执行。

### onDraw / onMeasure 中分配对象

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

### 字符串拼接和格式化

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

### 自动装箱和临时集合

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

## 内存抖动检测与治理

检测内存抖动按“现象确认 → 分配归因 → 代码修复 → 回归防护”推进。堆转储适合分析某一时刻仍然存活的对象；抖动更需要时间序列上的分配记录：哪条调用栈在什么时段分配、每秒分配多少、是否与慢帧或启动阶段重叠。

### 现象确认：先把 GC 和帧放到同一张图里

用 Perfetto 或 Android Studio Profiler 记录一次目标场景：启动、打开页面、快速滑动、动画播放或连续输入。观察三组信号：

- **帧信号**：Frame Timeline 是否出现 missed frame（未按时呈现）或 slow frame（耗时偏长），慢帧是否集中在交互窗口。
- **GC 信号**：Logcat、Profiler 或系统跟踪里的 GC 是否密集，`HeapTaskDaemon` 是否在同一窗口活跃。
- **分配信号**：Java/Kotlin 分配记录或 ART 分配画像是否显示对象数量快速上升。

Android Studio 的 Java/Kotlin 分配记录要求 debuggable（可调试）构建。Full 模式记录每次分配，高分配应用可能出现明显的分析器开销；必要时改用定期抽样的 Sampled 模式，并把采集模式写进对比记录。Perfetto 从 Android 12 起支持 ART allocation profiling，在 `HeapprofdConfig` 中配置 `heaps: "com.android.art"` 后采集分配调用栈样本。它记录对象创建时的调用栈与累计分配，不记录对象何时被删除或回收，因而不能替代展示对象保留关系的堆转储。在量产 user 系统上，目标应用还必须声明 `debuggable` 或 `profileable`（允许系统分析）。

### 分配归因：按调用频率排序，不按代码体量排序

找到分配栈后，按调用频率、单次字节数和存活时间共同分层：每帧调用、每个列表项调用、每次页面打开调用、后台批处理调用。高频小对象可能比低频大对象产生更多累计分配，但优先级必须由目标时间窗内的总字节、次数和慢帧重叠关系决定。

常用修复动作有四类：

- **移出高频回调**：把可安全复用的 `Paint`、`Path`、`RectF`、格式化器或缓冲区移到与使用者相同的生命周期，并在尺寸或配置变化时更新。持有 View、Context 或大数组的对象不能无条件提升为全局成员。
- **合并中间态**：数据转换时减少 DTO（数据传输对象）、领域模型、界面模型之间的多份临时集合；能够流式处理时，不要先生成完整集合。
- **换基本类型容器**：高频 `Int` / `Long` 键场景使用 `SparseArray`、`SparseIntArray`、`LongSparseArray` 或专用数组结构。
- **分批处理**：把大列表差异计算、日志解析、埋点聚合分块执行，将分配峰值分散到多个调度片段。

### 代码修复：减少高频路径分配，不追求零分配

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

### 回归防护：给高频路径设分配预算

列表绑定、绘制和埋点代码重构后，分配热点可能重新出现。分配预算应来自同一设备、同一构建和确定脚本的基线分布，再按允许的性能变差范围设置门槛，不要复制其他项目的固定数值。

- **启动**：记录首屏前总分配字节、GC 次数和 `HeapTaskDaemon` 活跃区间。
- **滑动**：固定列表数据、设备条件和输入脚本，比较单位时间分配字节、慢帧与 GC 的时间关系。
- **绘制**：让自定义 View、图表或动画运行到数据稳定，记录目标方法时间窗内的分配次数与调用栈。
- **生产环境**：只采集已有的有界趋势指标和场景标签，不在用户设备上持续运行 Full 分配记录。异常版本回到实验设备复现；需要现场证据时使用受系统控制的分析能力。

把非关键工作延后只能改变时间分布，不能减少总分配。首屏后预取或 fling（惯性滑动）结束后刷新统计，仍可能与下一次输入、图片解码或后台任务竞争 CPU；要根据任务优先级设置取消条件，并在系统跟踪中确认延后后的窗口没有产生新的慢帧。

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

- [Android Developers：Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Android Developers：Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [Android 16 QPR2：Release notes](https://developer.android.com/about/versions/16/qpr2/release-notes)
- [Android Developers：Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [Android Developers：`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [AOSP：Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [Perfetto：ART Allocation Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `android-17.0.0_r1`, `Daemons.java`](https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/libart/src/main/java/java/lang/Daemons.java)
- [AOSP `android-17.0.0_r1`, `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP `android-17.0.0_r1`, `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `android-17.0.0_r1`, `task_processor.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/task_processor.cc)
