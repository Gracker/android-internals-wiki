---
title: "内存抖动与 GC 治理"
chapter: "23.5"
section: "23.5"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers Android 17 release notes + Android Developers + Perfetto docs + Clippings/Android 性能优化"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/studio/profile/memory-profiler"
  - type: official
    path: "https://source.android.com/docs/core/runtime/gc-debug"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
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
related_chapters: ["23.4", "10.6", "4.8", "7.2"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_date: "2026-05-14"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-14"
task6_review_notes: "2026-05-14 task6 review: 四层质检通过，未发现 L1/L2 正文问题；无新增 L3/L4 回炉项，送 Task9 技术复审。"
last_task6_review_log: "logs/review/2026-05-14-02-review.md"
last_task6_at: "2026-05-14T02:13:00+08:00"
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-30"
last_task9_at: "2026-06-30T15:36:54+08:00"
task9_review_notes: "2026-06-30 task9 idle audit auto-fix: Android 17 基线复核发现 ShouldConcurrentGCForJava() 已加入 time-based GC triggering 分支；已更新源码锚点和版本说明，回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-30
last_task6_audit: "2026-07-17"
last_task9_audit: "2026-06-30"
last_task9_autofix_at: "2026-06-30"
---

# 内存抖动与 GC 治理

> **版本基线**
>
> 平台实现统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。历史版本只用于说明 collector 和工具能力的演进，最高版本为 Android 17。

## 为什么要了解内存抖动与 GC 治理

内存抖动说的是短时间大量分配、很快失效、又反复触发回收的问题。前文已经讲过 Java Heap 预算与缓存控制（23.4 节），以及 ART GC 的机制和 Perfetto 识别方法（10.6 节、4.8 节）。这一节把视角切到应用实战：怎么把分配峰值从启动、首帧、滑动、动画这些敏感窗口里移走。

ART 的并发 collector 缩短了许多暂停，但分配、标记、复制或压缩仍要消耗 CPU 和内存带宽，部分阶段仍需暂停 mutator。应用分配速度超过回收与堆扩展能力时，分配线程还可能等待 GC 完成。因而，卡顿归因不能简化成“看到 GC 就是 GC 卡住主线程”，也不能假设并发 GC 没有应用侧成本。

Hook `libart.so` 或阻塞 `HeapTaskDaemon` 会破坏 ART 的回收时序，并依赖非公开 ABI。应用治理应从 trace 和 allocation call stack 找到分配热点，缩短无用中间态的生命周期，控制单次处理范围，再验证 GC 与慢帧是否同步改善。

## 内存抖动的成因与表现

内存抖动同时受分配大小、分配频率和对象存活时间影响。大量小对象可以快速推进已分配字节数，大对象则可能直接形成峰值；只按对象大小排序会漏掉高频调用栈。

Android 17 的 `Heap::AllocObjectWithAllocator()` 在分配记账后调用 `ShouldConcurrentGCForJava(new_num_bytes_allocated)`。启用 time-based GC triggering 且 `time_based_gc_threshold_` 非零时，该函数结合 GC 后新增字节数与时间进度，返回立即请求 GC 或安排阈值复查；`concurrent_start_bytes_` 保留为接近堆限制时的保护条件。未启用这条路径时，判断回到已分配字节数与 `concurrent_start_bytes_` 的比较。任务排队发生在对象可以安全暴露后，由 `RequestConcurrentGCAndSaveObject()` 请求 `ConcurrentGCTask`。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap-inl.h::Heap::AllocObjectWithAllocator()`, `Heap::ShouldConcurrentGCForJava()`, `art/runtime/gc/heap.cc::Heap::RequestConcurrentGC()`]

从应用层来看，内存抖动通常表现为四种现象：

- **堆曲线呈锯齿状**：内存快速上升，又被 GC 拉回，周期很短。单次峰值可能不高，但回收频率高。
- **Logcat 或 trace 里 GC 密集**：`HeapTaskDaemon` 活跃，Perfetto / Systrace 能看到多个 GC 片段紧贴在交互窗口附近。
- **帧耗时波动**：Frame Timeline 里的慢帧可能间隔出现，并集中在滑动、动画或连续输入期间。
- **分配慢路径或等待**：线程在分配时等待 GC 完成，或进入需要扩展/回收的慢路径。业务函数自身的 CPU 时间可能不高，但 wall time 会被等待拉长。

Android 8 起，ART 的默认计划是 Concurrent Copying；官方 GC 文档说明 Android 10 及以上的 CC 默认使用分代模式。Android 17 又为 Concurrent Mark-Compact 增加分代 GC 能力。collector 与 generational 开关仍取决于运行时配置，不能从系统版本推断每个进程都采用同一组合；Android 17 的 `PostForkChildAction()` 会在日志中输出当前进程使用的 generational/non-generational collector，可与 trace 一起确认。

## 频繁 GC 对帧率的影响

GC 对帧率的影响来自两块：短暂停应用线程，以及后台 GC 线程和渲染线程抢 CPU。AOSP `Daemons.java` 中 `HeapTaskDaemon` 会调用 `VMRuntime.getRuntime().runHeapTasks()`；`TaskProcessor::RunAllTasks()` 从队列取 `HeapTask` 并执行。Android Developers 的慢渲染文档也提到，新版本 Android 上 GC 通常运行在名为 `HeapTaskDaemon` 的后台线程上，大量分配会让更多 CPU 资源花在 GC 上。

每帧预算由屏幕刷新率决定，不能固定写成某个毫秒数。滑动时主线程、RenderThread、图片解码线程和后台任务共同使用 CPU；GC 工作与帧生产重叠时，可能增加调度等待、内存带宽压力或短暂停顿。是否影响用户可见帧必须由 Frame Timeline 与线程轨道证明。

排查时不要只盯单次 GC 耗时。相同的 GC 工作落在空闲窗口与关键帧窗口，用户影响不同。把三类轨道放到同一张 trace 里比较：

- **Frame Timeline**：确认 missed frame、slow frame 和 present 结果，判断是否影响用户可见帧。
- **主线程 / RenderThread**：确认帧生产阶段是否被分配、锁、Binder 或调度延迟干扰。
- **HeapTaskDaemon / GC 事件**：确认 GC 是否和帧尖峰重叠，不能只根据内存曲线猜。

时间重叠只能建立相关性，还要检查主线程和 RenderThread 的状态。`Running` 表示线程正在 CPU 上执行，应查看对应 slice 或调用栈；`Runnable` 表示线程已就绪却没有获得 CPU，才更支持调度延迟或 CPU 竞争；`Sleeping`、`Blocked` 等状态要继续追踪唤醒者、锁、Binder 或其他等待原因。GC 与慢帧相邻但不重叠，也不能据此判定因果。

### Android 17 的 post-fork GC 不一定来自页面抖动

Android 17 的 `Heap::PostForkChildAction()` 在 `initial_heap_size_ < growth_limit_` 时安排 target footprint 调整，并为新 fork 的应用进程排入 `TriggerPostForkCCGcTask`。该任务只有在计划时间到达、且从 fork 后尚未发生其他 GC 时，才请求一次后台 GC；如果期间已经有 GC，它就是 no-op。调度时间还带有按 UID 确定、在不同进程间变化的偏移。从这段实现可以推断，该偏移用于降低多个进程在同一时刻发起这类 GC 的概率。

因此，启动后看到一次后台 GC 时，要同时查看 GC cause、进程启动时间和前后的分配轨道。不能仅凭“启动附近出现 GC”就归因到某个页面的临时对象。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/gc/heap.cc::Heap::PostForkChildAction()`, `TriggerPostForkCCGcTask`]

## 典型内存抖动场景

调用频率比代码表面的复杂度更值得优先检查。一次分配在点击按钮时没有问题，放到 `onDraw()`、`onBindViewHolder()`、`onTouchEvent()`、Compose recomposition 或动画回调里，就会被帧率放大。

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

这段写法没有消除初始化和尺寸变化时的分配，只把 `Paint` 与 `RectF` 的创建移出高频绘制路径。优化后要用 Java/Kotlin allocation recording 或 Perfetto ART allocation profiling 检查 `onDraw()` 时间窗内的分配调用栈。

### 字符串拼接和格式化

字符串抖动常出现在日志、埋点、列表绑定和调试面板里。`String.format()`、复杂模板、循环里的 `+` 拼接、把大 JSON 拼成日志字符串，都会产生临时对象。影响取决于拼接频率、字符串长度和调用窗口。

下面这段代码用于列表绑定场景，把格式化器复用起来，并把展示字符串生成限制在绑定边界。重点看 `NumberFormat` 没有在每次 `onBindViewHolder()` 里创建。

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

`NumberFormat` 不是线程安全对象，这个 formatter 应限制在 RecyclerView 所在的主线程。`formatFen()` 仍会创建结果 `String`；复用只省去重复构造格式器的成本。若价格、币种与 Locale 未变化，可以让不可变 UI state 保存已格式化结果，并在任一输入变化时重新计算。不要把所有展示文案放进全局缓存，否则失效逻辑和常驻内存可能抵消收益。

### 自动装箱和临时集合

自动装箱会把基本类型包成对象，Kotlin / Java 的集合 API 很容易在泛型、lambda、nullable、`Map<Int, T>` 这些地方触发装箱。少量装箱不值得处理；滑动、采样、埋点聚合或图表绘制里每帧装箱，就会形成稳定分配源。

这段代码用于高频计数场景，用平台集合替代 `MutableMap<Int, Int>`，避免 key 和 value 在热路径上反复装箱。bucket 宽度由调用方按分析精度传入，示例不内置一个通用分界。

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

`snapshot()` 仍会创建普通 `Map` 并发生装箱，这是有意设置的边界：热路径只记录，低频读取时再转换为通用结构。调用方还要保证计数不会在无限生命周期内溢出，可按测试场景创建并丢弃 counter。

## 内存抖动检测与治理

检测内存抖动按“现象确认 → 分配归因 → 代码修复 → 回归防护”推进。只看 heap dump 容易偏向泄漏分析，抖动更需要 allocation over time：谁在什么时间段分配、每秒分配多少、是否和慢帧或启动阶段重叠。

### 现象确认：先把 GC 和帧放到同一张图里

用 Perfetto 或 Android Studio Profiler 抓一次目标场景：启动、打开页面、快速滑动、动画播放、输入连续触发。观察三组信号：

- **帧信号**：Frame Timeline 是否出现 missed / slow frame，慢帧是否集中在交互窗口。
- **GC 信号**：Logcat、Profiler 或 trace 里 GC 是否密集，`HeapTaskDaemon` 是否在同一窗口活跃。
- **分配信号**：Java/Kotlin allocation recording 或 heap profile 是否显示对象数量快速上升。

Android Studio 的 Java/Kotlin allocation recording 需要 debuggable 构建；Full 模式可能让高分配应用出现可见的 profiler 开销，必要时改用 Sampled，并把这个采样条件写进对比记录。Perfetto 从 Android 12 起支持 ART allocation profiling，在 `HeapprofdConfig` 中配置 `heaps: "com.android.art"` 后采集分配调用栈样本。它记录创建时的调用栈与累计分配，不记录对象何时被回收，不能替代 retention heap dump。

### 分配归因：按调用频率排序，不按代码体量排序

找到分配栈后，按调用频率、单次字节数和存活时间共同分层：每帧调用、每个 item 调用、每次页面打开调用、后台批处理调用。高频小对象可能比低频大对象产生更多累计分配，但优先级必须由目标时间窗内的总字节、次数和慢帧重叠关系决定。

常用修复动作有四类：

- **移出高频回调**：把可安全复用的 `Paint`、`Path`、`RectF`、formatter 或 buffer 移到与使用者相同的生命周期，并在尺寸或配置变化时更新。持有 View、Context 或大数组的对象不能无条件提升为全局成员。
- **合并中间态**：数据转换时减少 DTO → domain → UI 多份临时集合，能流式处理就不要全量 materialize。
- **换基本类型容器**：高频 `Int` / `Long` key 场景用 `SparseArray`、`SparseIntArray`、`LongSparseArray` 或专用数组结构。
- **分批处理**：大列表 diff、日志解析、埋点聚合按 chunk 推进，把分配峰值拆到多个调度片段里。

### 代码修复：减少热路径分配，不追求零分配

零分配不应该是通用目标。现代 ART 对短命小对象已经做了优化，强行对象池化反而可能把短命对象变成长命对象，给老年代增加压力，还容易因为忘记重置字段引入脏数据。对象池只适合创建频繁、初始化成本高、状态可完整清理的对象；普通数据对象和持有 View / Context / callback 的对象不要池化。

下面的函数用于把批处理切成多个协作式调度片段。它直接把原列表和 `[start, end)` 索引交给调用方，省去 chunk 子列表；`chunkSize` 必须由测量决定。

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

`yield()` 只提供协作式让出机会，不保证跨帧执行，也不会自动切换到后台线程。调用方要选择合适的 dispatcher，并确认 `processRange` 不在主线程执行重 CPU 工作。该函数不会减少最终结果集；如果调用方仍把所有结果保存在内存中，稳定占用不会下降。最终结果过大时，应改用分页、流式消费或外部存储。

### 回归防护：给高频路径设分配预算

列表绑定、绘制和埋点代码重构后，分配热点可能重新出现。分配预算应来自同一设备、同一构建和确定脚本的基线分布，再按可接受回退范围设置门槛，不要复制其他项目的固定数值。

- **启动**：记录首屏前总分配字节、GC 次数和 `HeapTaskDaemon` 活跃区间。
- **滑动**：固定列表数据、设备条件和输入脚本，比较单位时间分配字节、慢帧与 GC 的时间关系。
- **绘制**：让自定义 View、图表或动画运行到数据稳定，记录目标方法时间窗内的 allocation count 与调用栈。
- **线上**：只采已有的有界趋势指标和场景标签，不在用户设备上持续运行 Full allocation recording。异常版本回到实验设备复现；需要现场证据时使用受控的系统 profiling 能力。

把非关键工作延后只能改变时间分布，不能减少总分配。首屏后预取或 fling 后刷新统计仍可能与下一次输入、图片解码或后台任务竞争 CPU；要根据任务优先级设置取消条件，并在 trace 中确认延后后的窗口没有产生新的慢帧。

## 常见误区

### “看到 GC 就要抑制 GC”

GC 请求反映了堆状态和分配行为。AOSP 里，`ShouldConcurrentGCForJava()` 判定需要回收后才会请求 `ConcurrentGCTask`；应用侧盲目抑制 GC 只会把回收延后。除非做虚拟机研究或受控实验，业务应用不要通过 native hook 阻塞 `HeapTaskDaemon`。

### “对象池一定能减少卡顿”

对象池只减少重复创建，不能自动减少状态复杂度。池里的对象生命周期变长后，可能提高保留内存，也可能把短命对象推向更长生命周期。上线前要同时比较分配、GC、稳定占用和帧表现，并验证对象能够完整重置。

### “一次 heap dump 就能定位抖动”

Heap dump 适合看某一刻还活着的对象，抖动里的临时对象可能已经被回收。要定位抖动，需要 allocation recording 或 Perfetto Java allocation profiling，看对象在时间轴上的生成速度和调用栈。

## 参考资料

- [Android Developers：Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Android Developers：Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [Android Developers：Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [AOSP：Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [Perfetto：ART Allocation Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `android-17.0.0_r1`, `Daemons.java`](https://android.googlesource.com/platform/libcore/+/android-17.0.0_r1/libart/src/main/java/java/lang/Daemons.java)
- [AOSP `android-17.0.0_r1`, `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP `android-17.0.0_r1`, `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `android-17.0.0_r1`, `task_processor.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/task_processor.cc)
