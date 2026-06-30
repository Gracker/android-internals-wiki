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
pipeline_stage: task6_pending
task6_state: revisiting
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
last_deepseek_cn_review_at: 2026-06-02
last_task6_audit: "2026-06-06"
last_task9_audit: "2026-06-30"
last_task9_autofix_at: "2026-06-30"
---

# 内存抖动与 GC 治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存抖动的成因与表现
- 🔹 频繁 GC 对帧率的影响
- 🔹 典型内存抖动场景：onDraw 分配、字符串拼接、自动装箱
- 🔹 内存抖动检测与治理

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解内存抖动与 GC 治理

内存抖动说的是短时间大量分配、很快失效、又反复触发回收的问题。前面 23.4 节讲了 Java Heap 预算和缓存控制，10.6 节和 4.8 节展开了 ART GC 的机制和 Perfetto 识别方法。这一节换到应用实战视角：把分配峰值从启动、首帧、滑动、动画这些敏感窗口里移走。

Android Developers 的慢渲染文档把对象分配和 GC 列为卡顿原因，结论很明确：ART 之后 GC 的影响小了很多，但高频路径里的分配仍然会吃掉 CPU，也会让 GC 更频繁。Memory Profiler 文档也说明，Android 的 GC 会在某些时刻短暂停应用代码；如果应用分配速度快于回收速度，线程会等回收器释放出足够内存再继续分配。

这一节不推荐把治理方向放在 Hook `libart.so` 或人为阻塞 `HeapTaskDaemon` 上。参考书里提到过 GC 抑制方案，这类方案适合理解 ART 内部任务调度，不适合作为通用应用优化手段。工程侧更稳的做法是把分配热点找出来，减少临时对象，控制批处理规模，并把重分配从用户能感知的帧窗口里挪开。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]
[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

## 内存抖动的成因与表现

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap-inl.h]
[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap.cc]
[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

内存抖动由“分配密度”触发，而不只由“对象大小”触发。一个页面每秒创建几万个小对象，即使单个对象只有几十字节，也会快速推高 `bytes_allocated`，让 ART 更早发起并发 GC。AOSP android-17.0.0_r1 中，`Heap::AllocObjectWithAllocator()` 在分配后会检查 `ShouldConcurrentGCForJava(new_num_bytes_allocated)`；如果启用 time-based GC triggering 且配置了 `time_based_gc_threshold_`，该函数会结合上次 GC 后的分配量和时间进度触发 `kNeedGc` 或调度阈值检查，`concurrent_start_bytes_` 则作为防止堆空间耗尽的兜底阈值。未启用该路径时，函数退回到 Java 已分配字节数和 `concurrent_start_bytes_` 的比较，并进入 `RequestConcurrentGCAndSaveObject()` 路径。

从应用层来看，内存抖动通常表现为四种现象：

- **堆曲线呈锯齿状**：内存快速上升，又被 GC 拉回，周期很短。单次峰值可能不高，但回收频率高。
- **Logcat 或 trace 里 GC 密集**：`HeapTaskDaemon` 活跃，Perfetto / Systrace 能看到多个 GC 片段紧贴在交互窗口附近。
- **帧耗时波动**：Frame Timeline 里不是每一帧都慢，而是滑动、动画或输入期间隔几帧出现尖峰。
- **Allocation Stall**：线程在分配时等 GC 或堆扩容，代码火焰图里业务函数不一定耗时长，但调用栈附近有分配和回收活动。

ART 从 Android 8 起默认使用 Concurrent Copying，Android 10 之后 Concurrent Copying 默认按分代模式运行；Android 17 release notes 又把 Concurrent Mark-Compact collector 的 generational GC 列为 Runtime/Performance 能力。source.android.com 的 ART GC 文档也写到，过量分配这种 mutator 行为仍会造成性能问题。应用侧不能把“现代 GC 更快”理解成“高频分配可以不管”。

## 频繁 GC 对帧率的影响

[已验证: AOSP android-17.0.0_r1, libcore/libart/src/main/java/java/lang/Daemons.java]
[已验证: AOSP android-17.0.0_r1, art/runtime/gc/task_processor.cc]
[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]
[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

GC 对帧率的影响来自两块：短暂停应用线程，以及后台 GC 线程和渲染线程抢 CPU。AOSP `Daemons.java` 中 `HeapTaskDaemon` 会调用 `VMRuntime.getRuntime().runHeapTasks()`；`TaskProcessor::RunAllTasks()` 从队列取 `HeapTask` 并执行。Android Developers 的慢渲染文档也提到，新版本 Android 上 GC 通常运行在名为 `HeapTaskDaemon` 的后台线程上，大量分配会让更多 CPU 资源花在 GC 上。

一帧只有十几毫秒，GC 不需要长时间停主线程也能影响体感。滑动时主线程、RenderThread、图片解码线程、后台数据线程本来就在争 CPU；如果 `HeapTaskDaemon` 在同一帧里密集运行，主线程拿到 CPU 的时机就可能被挤到后面，RenderThread 提交也会变晚。7.2 节讲的是卡顿归因树，这里只看应用动作：不要让可避免的分配跟帧生产抢同一个时间段。

排查时不要只盯单次 GC 耗时。一次 2 ms 的 GC 落在空闲期可能没有感知；连续多次 GC 落在 fling、动画或首帧窗口里，帧耗时会被抬高。更可靠的判断方式是把三类轨道放到同一张 trace 里对齐：

- **Frame Timeline**：确认 missed frame、slow frame 和 present 结果，判断是否影响用户可见帧。
- **主线程 / RenderThread**：确认帧生产阶段是否被分配、锁、Binder 或调度延迟干扰。
- **HeapTaskDaemon / GC 事件**：确认 GC 是否和帧尖峰重叠，不能只根据内存曲线猜。

这里的“对齐”是时间轴对齐，不是汇报口径。只要 GC 事件和慢帧时间重叠，还要继续看主线程状态：Running 表示 CPU 争用更可疑，Sleeping / Blocked 表示锁、Binder 或等待更可疑。

## 典型内存抖动场景

[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]
[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

内存抖动最常出现的位置不是“看起来最复杂”的业务代码，而是调用频率最高的回调。一次分配在点击按钮时没有问题，放到 `onDraw()`、`onBindViewHolder()`、`onTouchEvent()`、Compose recomposition 或动画回调里，就会被帧率放大。

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

这段写法没有把所有分配都消掉，`View` 初始化和尺寸变化仍可能分配对象。它只处理高频帧路径。优化后要用 allocation recording 或 Perfetto heap profile 验证 `onDraw()` 调用期间分配次数是否下降。

### 字符串拼接和格式化

字符串抖动常出现在日志、埋点、列表绑定和调试面板里。`String.format()`、复杂模板、循环里的 `+` 拼接、把大 JSON 拼成日志字符串，都会产生临时对象。问题不在字符串本身，而在拼接频率、字符串长度和调用窗口。

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

如果绑定频率很高，还可以把服务端已稳定的展示字段下沉到数据层，或者只在数据变化时更新文案。不要为了减少字符串分配把所有展示文案做成全局缓存；列表数据变化快，缓存命中率低时会变成常驻内存。

### 自动装箱和临时集合

自动装箱会把基本类型包成对象，Kotlin / Java 的集合 API 很容易在泛型、lambda、nullable、`Map<Int, T>` 这些地方触发装箱。少量装箱不值得处理；滑动、采样、埋点聚合或图表绘制里每帧装箱，就会形成稳定分配源。

这段代码用于高频计数场景，用平台集合替代 `MutableMap<Int, Int>`，避免 key 和 value 在热路径上反复装箱。重点看计数更新只处理 `Int`。

```kotlin
class FrameBucketCounter {
    private val buckets = SparseIntArray()

    fun add(frameCostMs: Int) {
        val bucket = frameCostMs / 4
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

`snapshot()` 仍会创建普通 `Map`，这是有意保留的边界：热路径只记录，低频读取时再转换成易用结构。治理内存抖动时要把“高频写”和“低频读”分开，不要让 API 好用性污染帧路径。

## 内存抖动检测与治理

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]
[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiler]
[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]
[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap.cc]

检测内存抖动按“现象确认 → 分配归因 → 代码修复 → 回归防护”推进。只看 heap dump 容易偏向泄漏分析，抖动更需要 allocation over time：谁在什么时间段分配、每秒分配多少、是否和慢帧或启动阶段重叠。

### 现象确认：先把 GC 和帧放到同一张图里

用 Perfetto 或 Android Studio Profiler 抓一次目标场景：启动、打开页面、快速滑动、动画播放、输入连续触发。观察三组信号：

- **帧信号**：Frame Timeline 是否出现 missed / slow frame，慢帧是否集中在交互窗口。
- **GC 信号**：Logcat、Profiler 或 trace 里 GC 是否密集，`HeapTaskDaemon` 是否在同一窗口活跃。
- **分配信号**：Java/Kotlin allocation recording 或 heap profile 是否显示对象数量快速上升。

Android Studio Memory Profiler 可以查看 heap dump、对象数量、GC 事件，也可以记录 Java/Kotlin allocations。Perfetto heapprofd 文档说明，Android 12+ 支持 Java allocation profiling，配置 `heaps: "com.android.art"` 后可以按时间采样 Java 分配调用栈。线下分析优先用这些工具，不要在线上长期开启重型分配采样。

### 分配归因：按调用频率排序，不按代码体量排序

找到分配栈后，先按调用频率分层：每帧调用、每个 item 调用、每次页面打开调用、后台批处理调用。每帧调用的 64 B 临时对象，优先级可能高于页面打开时的一次 64 KB 对象。内存抖动关注的是单位时间内的分配总量。

常用修复动作有四类：

- **移出高频回调**：把 `Paint`、`Path`、`RectF`、formatter、临时 buffer 移到成员字段或尺寸变化回调里。
- **合并中间态**：数据转换时减少 DTO → domain → UI 多份临时集合，能流式处理就不要全量 materialize。
- **换基本类型容器**：高频 `Int` / `Long` key 场景用 `SparseArray`、`SparseIntArray`、`LongSparseArray` 或专用数组结构。
- **分批处理**：大列表 diff、日志解析、埋点聚合按 chunk 推进，把分配峰值拆到多个调度片段里。

### 代码修复：减少热路径分配，不追求零分配

零分配不应该是通用目标。现代 ART 对短命小对象已经做了优化，强行对象池化反而可能把短命对象变成长命对象，给老年代增加压力，还容易因为忘记重置字段引入脏数据。对象池只适合创建频繁、初始化成本高、状态可完整清理的对象；普通数据对象和持有 View / Context / callback 的对象不要池化。

下面这段代码用于批处理场景，目标是把一次性分配峰值切成小批次。重点看每批结束后只保留必要结果，中间列表不会跨批次长期持有。

```kotlin
suspend fun <T, R> mapInChunks(
    source: List<T>,
    chunkSize: Int = 200,
    mapper: (T) -> R
): List<R> = coroutineScope {
    val result = ArrayList<R>(source.size)
    var index = 0
    while (index < source.size) {
        val end = minOf(index + chunkSize, source.size)
        for (i in index until end) {
            result += mapper(source[i])
        }
        index = end
        yield()
    }
    result
}
```

这段代码降低的是单个调度片段里的分配密度，不会减少最终结果集大小。若最终结果本身过大，仍要回到 23.4 节的大对象和集合优化策略：分页、流式处理、缓存预算和生命周期清理。

### 回归防护：给高频路径设分配预算

内存抖动很容易在重构后回来，尤其是列表绑定、绘制和埋点代码。建议把分配预算写进性能验收：

- **启动**：记录首屏前总分配字节、GC 次数和 `HeapTaskDaemon` 活跃区间。
- **滑动**：固定列表数据、固定设备和固定手势，记录每秒分配字节、慢帧数和 GC 次数。
- **绘制**：自定义 View / 图表 / 动画组件在 5-10 秒压力场景下记录 allocation count。
- **线上**：只采轻量指标，例如 Java Heap 使用率、GC 次数、页面和设备维度；发现异常后再回到线下采样。

[自动发现] 对于启动、首帧和滑动，应用侧可以把重分配延后到帧稳定后执行，例如首屏渲染后再预热低优先级缓存，或者 fling 结束后再刷新非关键统计。这个动作不改变 ART GC 机制，只改变分配时间分布。[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

## 常见误区

### “看到 GC 就要抑制 GC”

GC 是结果，不是根因。AOSP 里 `ConcurrentGCTask` 是 `ShouldConcurrentGCForJava()` 判定需要 GC 后加入任务队列的结果，应用侧盲目抑制 GC 只会把回收延后。除非做虚拟机研究或受控实验，业务应用不要通过 native hook 阻塞 `HeapTaskDaemon`。

### “对象池一定能减少卡顿”

对象池只减少重复创建，不能自动减少状态复杂度。池里的对象生命周期变长后，可能提高保留内存，也可能把短命对象推向更长生命周期。对象池上线前至少比较三组数据：分配次数、GC 次数、帧耗时。

### “一次 heap dump 就能定位抖动”

Heap dump 适合看某一刻还活着的对象，抖动里的临时对象可能已经被回收。要定位抖动，需要 allocation recording 或 Perfetto Java allocation profiling，看对象在时间轴上的生成速度和调用栈。

## 参考资料

### AOSP 源码

- `android-17.0.0_r1/libcore/libart/src/main/java/java/lang/Daemons.java`：`HeapTaskDaemon` 调用 `VMRuntime.getRuntime().runHeapTasks()`。
- `android-17.0.0_r1/art/runtime/gc/task_processor.cc`：`TaskProcessor::RunAllTasks()` 取出 `HeapTask` 并执行。
- `android-17.0.0_r1/art/runtime/gc/heap-inl.h`：`Heap::AllocObjectWithAllocator()` 分配后检查 `ShouldConcurrentGCForJava()`；Android 17 该函数包含 time-based GC triggering 分支。
- `android-17.0.0_r1/art/runtime/gc/heap.cc`：`RequestConcurrentGCAndSaveObject()`、`ConcurrentGCTask` 和 GC 请求路径。

### 官方文档

- Android Developers — Slow rendering：对象分配和 GC 对慢帧的影响。
- Android Studio — Memory Profiler：heap dump、Java/Kotlin allocation recording 和 GC 事件观察。
- Android Open Source Project — Debug ART garbage collection：ART GC 策略、GC 性能观察和 Perfetto / Systrace 建议。
- Perfetto docs — Heap profiler：Android 12+ Java allocation profiling 与 `com.android.art` heap 配置。

### 结构参考

- [结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]
- [结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]
- [结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
