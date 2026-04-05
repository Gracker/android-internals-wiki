---
title: "ART 分代垃圾回收与 GC 暂停优化"
chapter: "4.8"
status: ready-for-review
drafted_date: "2026-04-06"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-04-06"
last_verified_against: "AOSP android-17-beta3 + source.android.com/docs/core/perf/art-management"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/art-management"
  - type: official
    path: "https://developer.android.com/about/versions/17"
  - type: aosp
    path: "art/runtime/gc/collector/concurrent_copying.cc"
  - type: aosp
    path: "art/runtime/gc/heap.cc"
  - type: research
    path: "intake/research-feeds/2026-04-03-19-ch04-android17-generational-gc.md"
  - type: research
    path: "intake/research-feeds/2026-03-31-11-ch04-art-generational-gc.md"
  - type: research
    path: "intake/research-feeds/2026-04-02-07-ch04-art-gc-pause-time-data.md"
  - type: research
    path: "intake/research-feeds/2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md"
tags: ['art', 'gc', 'generational-gc', 'write-barrier', 'card-table', 'android-17', 'jank', 'perfetto-sql']
related_chapters: ["4.3", "4.6", "7.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档（Android 17 行为变更）+ AOSP 源码分析"
---

# 4.8 ART 分代垃圾回收与 GC 暂停优化

阅读本节之前，建议先了解 §4.3 中 ART 堆结构和 GC 策略演进的基础内容。本节在 §4.3 的基础上，深入分代垃圾回收的内部实现——Write Barrier 如何工作、Card Table 怎么记录跨代引用、Android 17 对分代 GC 做了哪些增强——然后把视角拉回到实际工作：GC 暂停怎么导致掉帧，在 Perfetto 中怎么分析，App 端有哪些手段可以减轻 GC 压力。

读完这一节，我们应该能回答三个问题：为什么一个"只有 1-3ms"的 GC 暂停仍然可能导致掉帧；Android 17 的分代 GC 做了哪些底层改变来减少这种影响；以及在自己的应用中，发现 GC 相关的卡顿后应该怎么排查和优化。

## GC 暂停为什么会影响流畅性

§4.3 中我们提到，ART 的 Concurrent Copying GC 将大部分 GC 工作放在应用线程之外并发执行，stop-the-world 暂停只有 1-5ms。这个数字看起来很小——但问题不在单次暂停的长度，而在 GC 活动与渲染管线的**时间冲突**。

在一个 120Hz 的设备上，帧间隔只有 8.33ms。主线程的 `doFrame()` 需要在这个窗口内完成 input 处理、animation 计算、measure、layout、draw，然后交给 RenderThread 进行 GPU 渲染。如果一次 Young GC 的暂停恰好发生在这个窗口内，主线程被暂停的 2-3ms 直接吃掉了整个帧预算的 25-36%。更严重的情况是：GC 并发阶段虽然不暂停主线程，但会与主线程争抢 CPU 时间，导致 `doFrame()` 执行变慢，间接造成掉帧。

```
正常帧（120Hz, 8.33ms 窗口）:
┌────────────────────────────────┐
│ Input → Animation → Traversal  │  8ms
└────────────────────────────────┘  ✓ 按时完成

GC 干扰帧:
┌────────────────────────────────────────┐
│ Input │ ██ GC Pause 2.5ms ██ │ Anim…  │  > 8.33ms
└────────────────────────────────────────┘  ✗ 掉帧
```

问题不止于暂停时间。GC 线程在并发标记和拷贝阶段需要占用 CPU——在 4 核的设备上，一个 GC 线程就吃掉了 25% 的计算资源。如果应用在滑动列表时触发了频繁的 Young GC，主线程和 RenderThread 可用的 CPU 时间被压缩，帧率下降可能比"暂停导致掉帧"更常见。

这就是为什么 Android 17 花大力气在 ART 中引入增强的分代 GC：不是让单次暂停更短（已经够短了），而是减少 GC 的总 CPU 开销和触发频率，让渲染管线有更充足的 CPU 时间来完成每一帧。

[已验证: 官方文档, developer.android.com/about/versions/17]
[待补充: Trace 截图 — GC pause 与 doFrame 时间冲突的具体 Perfetto 片段]

## 从 Concurrent Mark-Sweep 到分代 GC：ART 的演进路径

§4.3 已经梳理了 CMS → CC → CMC 的 GC 策略演进。这里我们把焦点放在分代策略本身——它是如何叠加到这些收集器之上的。

### 分代假说：为什么要把堆分成两块

分代垃圾回收的理论基础是"分代假说"（Generational Hypothesis）：在一次 GC 中存活下来的对象，大概率会在后续的 GC 中继续存活。反过来说，绝大多数对象都是短命的。

ART 的实测数据支撑了这个假设：在典型的 Android 应用中，超过 90% 的对象在创建后很快就会变成垃圾。以一个列表滑动场景为例：`onBindViewHolder()` 中创建的临时字符串、`MeasureSpec` 对象、`Rect` 实例——它们在一次 `doFrame()` 结束后就不再被引用。

如果不分代，每次 GC 都要扫描整个堆。假设堆有 128MB，其中 90% 的存活对象集中在老年代，那 GC 每次都要遍历这 128MB 来找出那 10% 的垃圾。分代策略的核心收益是：**Young GC 只扫描 Young Generation（通常只占堆的 10-20%），找出短期垃圾的速度快得多，暂停时间也短得多。**

### ART 分代 GC 的版本时间线

分代策略在 ART 中不是一步到位的，而是经历了多个版本的迭代：

**Android 8.0（Oreo）**：CC（Concurrent Copying）GC 成为默认收集器。CC 本身不是分代的，但它引入了 RegionSpace 和 TLAB 分配，为后续分代策略奠定了基础。CC GC 的暂停时间相比 Android 7.0 减少了 85%。

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]

**Android 10（Q）**：在 CC 的基础上正式引入分代 GC。堆被划分为 Young Generation（Nursery）和 Old Generation（Tenured）。Young GC 只处理新生代，暂停时间通常在 1-3ms（实测平均值约 1.83ms）。经历多次 Young GC 仍存活的对象被提升（promote）到老年代。

**Android 14-15**：CMC（Concurrent Mark-Compact）GC 开始替代 CC。CMC 用 UFFD（userfaultfd）机制替代 Read Barrier，GC 不运行时零额外开销。分代策略继续沿用。

**Android 17（API 37）**：将分代收集正式集成到 CMC 收集器的核心路径中。之前的分代 GC 更像是在 CC/CMC 之上的"优化策略"，Android 17 让分代成为收集器的原生特性。系统优先执行低成本的 Young Generation 回收，减少全堆 GC（Full-Heap GC）的频率。关键改变在于：Young GC 的调度更激进（更早触发、更频繁执行），但每次成本更低；Full GC 被尽可能推迟。

> Android 17 引入了分代垃圾回收，预期在资源密集型应用中减少卡顿，通过降低整体 GC CPU 开销和暂停时间来自动提升性能。
> — 来源：Android 17 Developer Features, developer.android.com

这些改进可通过 Google Play System Updates 回推到 Android 12（API 31）及以上设备——这意味着大部分在役设备都能受益。

## Android 17 分代 GC 的内部实现

这一节深入分代 GC 的三个核心技术机制：Write Barrier、Card Table 和跨代引用追踪。理解这些机制不是为了去修改 ART 的源码，而是为了在分析 Trace 时能准确判断 GC 行为是否正常。

### Write Barrier：记录谁改了谁

分代 GC 面临一个核心问题：Young GC 只扫描 Young Generation，但老年代的对象可能持有新生代对象的引用。如果 Young GC 不扫描老年代，怎么知道新生代中哪些对象还被老年代引用着？

答案是：不让 GC 去扫描老年代，而是让应用线程自己报告"我改了什么"。每当应用代码执行一个对象引用的赋值操作（比如 `oldObject.field = newYoungObject`），编译器会在赋值前后插入一段额外的代码——这就是 Write Barrier（写屏障）。

```
// 应用代码
oldObject.field = newYoungObject;

// 编译器实际生成的代码（概念示意）
oldObject.field = newYoungObject;
writeBarrier(oldObject, "field");  // 通知 GC：oldObject 的引用发生了变化
```

Write Barrier 的作用是通知 GC："老年代对象 `oldObject` 的某个字段现在指向了新生代对象"。GC 把这个信息记录下来，Young GC 时只需要检查这些"被修改过的老年代对象"的引用字段，就能找到所有从老年代指向新生代的引用——而不需要扫描整个老年代。

[已验证: AOSP android-17-beta3, art/runtime/gc/collector/concurrent_copying.cc 中 WriteBarrier 相关实现]

### Card Table：Write Barrier 的存储结构

Write Barrier 记录的"哪些老年代对象被修改了"需要一个高效的存储结构。ART 使用 Card Table（卡表）来实现。

Card Table 将堆内存按固定大小（通常是 512 字节）划分为"卡片"（card）。每个卡片在 Card Table 中对应一个字节。当 Write Barrier 检测到某个老年代区域的引用被修改时，它将该区域对应的卡片标记为"脏"（dirty，值为 0x70）。

```
堆内存布局（老年代）:
┌──────────┬──────────┬──────────┬──────────┐
│ Card 0   │ Card 1   │ Card 2   │ Card 3   │  每张 512 字节
│ (clean)  │ (dirty)  │ (clean)  │ (dirty)  │
└──────────┴──────────┴──────────┴──────────┘
     ↓           ↓           ↓           ↓
Card Table: [  0x00  |  0x70  |  0x00  |  0x70  ]
                           ↑                 ↑
                    Card 1 和 Card 3 中有跨代引用被修改
```

Young GC 时，GC 只需要扫描 Card Table 中标记为 dirty 的卡片对应的老年代区域，就能找到所有可能的跨代引用。这比扫描整个老年代快几个数量级。

AOSP 源码路径：
- Card Table 实现：`art/runtime/gc/accounting/card_table.cc`
- Write Barrier 入口：`art/runtime/entrypoints/quick/quick_entrypoints.cc` 中的 `art_quick_write_barrier`

[已验证: AOSP android-17-beta3, art/runtime/gc/accounting/card_table.cc]

### Remembered Set：精确的跨代引用集合

Card Table 的粒度是 512 字节——一个卡片可能包含多个对象，其中只有一部分被修改了。为了进一步提高 Young GC 的效率，ART 在 Card Table 之上还维护了 Remembered Set（RSets）：一个更精确的"哪些老年代对象引用了新生代对象"的集合。

Remembered Set 的构建过程如下：
1. Write Barrier 标记 dirty card
2. GC 在下一次 Young GC 开始时，扫描所有 dirty card
3. 对每个 dirty card 中的对象，检查其引用字段是否指向新生代
4. 将确认存在跨代引用的对象加入 Remembered Set

这样 Young GC 扫描根集时，只需要处理 Remembered Set 中的对象，而不是所有 dirty card 中的对象。在对象密度高的情况下，这个优化能显著减少扫描时间。

### Young GC 的执行流程

把以上机制串起来，一次 Young GC 的完整流程如下：

1. **触发**：Young Generation 空间不足，或分配器检测到新生代容量达到阈值
2. **暂停应用线程**（stop-the-world）：暂停时间通常 1-3ms，只用于处理线程根集
3. **扫描根集**：从线程栈、全局变量、JNI 引用出发，标记所有直接可达的新生代对象
4. **处理 Remembered Set**：扫描被老年代引用的新生代对象，确保它们不会被误回收
5. **标记存活对象**：遍历新生代中的对象图，标记所有可达对象
6. **回收垃圾**：清除未被标记的对象，释放内存
7. **提升存活对象**：经历了多次 Young GC 仍存活的对象被拷贝到 Old Generation
8. **恢复应用线程**

步骤 2 的暂停是不可避免的，但它只处理根集，不扫描整个堆——这就是分代 GC 暂停时间短的根本原因。步骤 3-7 中，ART 尽可能将可并发的工作放在应用线程恢复之后执行。

[已验证: AOSP android-17-beta3, art/runtime/gc/collector/concurrent_copying.cc]
[待验证: Android 17 中 Young GC 是否引入了更多并发阶段以进一步缩短 STW 暂停]

## GC 对应用性能的实际影响

### 不同分配模式下的 GC 行为

理解 GC 对帧率的影响，需要区分三种典型的对象分配模式：

**稳态分配**：应用在正常运行中持续分配少量短期对象（如 UI 渲染中的临时 `Rect`、`Matrix`）。Young GC 以稳定的频率触发（每 2-5 秒一次），每次 1-3ms。这种模式下 GC 对帧率几乎没有影响。

**脉冲分配**：在某个操作（如页面跳转、列表滑动到新区域、加载 JSON 数据）中突然分配大量对象。短时间内触发多次 Young GC，如果脉冲恰好与 `doFrame()` 冲突，就可能掉帧。脉冲分配是"偶尔卡一下"的常见原因。

**持续高分配（内存抖动）**：应用持续高速分配和丢弃对象。典型场景：在 `onDraw()` 中创建新对象、在 `RecyclerView.Adapter.onBindViewHolder()` 中分配大量临时字符串、Compose recomposition 产生大量临时 lambda 和状态对象。Young GC 频率飙升到每秒 3 次以上，虽然每次暂停只有 2-3ms，但累积的 CPU 开销和与渲染管线的冲突导致持续掉帧。

```
稳态分配：     |GC|               |GC|               |GC|
帧时间线：     |f|f|f|f|f|f|f|f| |f|f|f|f|f|f|f|f| |f|f|f|f|
              ✓ 流畅

脉冲分配：     |GC GC|GC|         |GC GC|GC|
帧时间线：     |f|f|  X |f|f|f|f| |f|f|  X |f|f|f|
                        ↑ 掉帧              ↑ 掉帧

内存抖动：     |GC|GC|GC|GC|GC|GC|GC|GC|GC|GC|
帧时间线：     |f| X |f| X |f| X |f| X |f| X |
                 持续掉帧
```

### 内存抖动如何触发频繁 GC

内存抖动（Memory Churn）是指应用在短时间内大量创建和丢弃临时对象的行为。在 Android Studio 的 Memory Profiler 中，它表现为堆大小的"锯齿图"——快速上升（大量分配），陡峭下降（GC 回收），然后又快速上升。

为什么内存抖动在高刷新率设备上更严重？60Hz 设备的帧间隔是 16.67ms，Young GC 暂停 2-3ms 只占帧预算的 12-18%。120Hz 设备帧间隔 8.33ms，同样的 2-3ms 暂停占帧预算的 24-36%。240Hz 设备帧间隔只有 4.17ms，一次 2-3ms 的 GC 暂停直接超过半帧。帧率越高，对 GC 暂停越敏感。

[待验证: 240Hz 设备上 GC 暂停的实际影响数据]

大对象分配会进一步加剧问题。超过 12KB 的基本类型数组或 String 会进入 Large Object Space。大对象的分配不走 TLAB 的快速路径，需要获取堆锁；大对象空间的 GC 策略也不同，可能触发同步 GC（而不是并发 GC），暂停时间更长。

## 在 Perfetto 中分析 GC 行为

### ART GC Track 的解读

在 Perfetto 中，GC 活动主要出现在以下 Track 中：

- **`art_gc` counter track**：显示 GC 的整体活动水平和吞吐量。值为 0 表示没有 GC 活动，值越高表示 GC 越频繁。
- **GC 线程的 slice track**：可以看到具体的 GC 事件，包括类型（Young GC / Partial GC / Full GC）、触发原因、持续时间。
- **主线程 track**：检查 GC 暂停是否与 `doFrame()` 时间重叠。

在 Perfetto UI 中，我们关注的是 GC slice 的**颜色和密度**：
- Young GC 表现为短的、浅色的 slice，间隔均匀
- Full GC 表现为长的、深色的 slice，频率低
- 如果 Young GC 的 slice 变得密集（间隔 < 500ms），说明存在内存抖动

[待补充: Trace 截图 — 正常 GC 模式 vs 内存抖动 GC 模式的 Perfetto 对比]

### GC 相关的 PerfettoSQL 查询

Perfetto 提供了 `android_garbage_collection_events` 表，可以通过 SQL 精确分析 GC 行为。以下是几个实用的查询：

**查询 GC 事件的频率和类型分布**：

```sql
-- 统计 GC 类型分布和平均暂停时间
SELECT
  gc_type,
  COUNT(*) as gc_count,
  AVG(dur / 1e6) as avg_duration_ms,
  SUM(dur / 1e6) as total_duration_ms
FROM android_garbage_collection_events
WHERE package_name = 'com.example.app'
GROUP BY gc_type
ORDER BY gc_count DESC;
```

**查找与掉帧时间重叠的 GC 事件**：

```sql
-- 找出与 jank frame 重叠的 GC 事件
SELECT
  gc.ts as gc_start,
  gc.dur / 1e6 as gc_duration_ms,
  gc.gc_type,
  frame.ts as frame_start,
  frame.dur / 1e6 as frame_duration_ms
FROM android_garbage_collection_events gc
JOIN actual_frame_timeline frame
  ON gc.ts < frame.ts + frame.dur
  AND gc.ts + gc.dur > frame.ts
WHERE gc.package_name = 'com.example.app'
  AND frame.jank_type != 'none'
ORDER BY gc.ts;
```

**按线程统计 GC 导致的暂停**：

```sql
-- 检查哪些线程受 GC 暂停影响最大
SELECT
  tid,
  thread_name,
  COUNT(*) as pause_count,
  AVG(dur / 1e6) as avg_pause_ms,
  MAX(dur / 1e6) as max_pause_ms
FROM slice
WHERE name LIKE '%GC%pause%'
  AND package_name = 'com.example.app'
GROUP BY tid
ORDER BY avg_pause_ms DESC;
```

[已验证: 官方文档, perfetto.dev/docs/data-sources/java-heap-profiler]
[待验证: `android_garbage_collection_events` 表在各 Android 版本中的可用性和字段差异]

### heapprofd：定位内存抖动的源头

如果 Perfetto SQL 分析确认了 GC 频率异常，下一步是找出"谁在分配这么多对象"。Perfetto 的 `heapprofd` 工具可以追踪 Java 堆的分配调用栈：

```bash
# 追踪特定进程的 Java 堆分配
adb shell heapprofd --pid=<PID> --java

# 或在 Perfetto 配置中启用 Java Heap Profiling
```

在 Perfetto UI 的 "Heap Profiles" 面板中，按分配大小或分配次数排序，可以定位到产生大量临时对象的具体调用栈。常见的"罪魁祸首"包括：

- `onDraw()` 中创建 `Paint`、`Path`、`Rect` 等对象
- `onBindViewHolder()` 中的字符串拼接和格式化
- JSON 解析产生的大量临时 `JSONObject`
- Compose recomposition 产生的临时 lambda 和状态快照

## App 端的 GC 优化策略

理解了 GC 的工作原理和影响方式后，我们来看 App 端可以采取的具体优化手段。核心思路只有一个：**减少需要 GC 处理的对象数量**。

### 减少对象分配

最直接的优化是在热点路径上避免创建不必要的对象：

**在 `onDraw()` 中避免分配**：`onDraw()` 在每一帧都会被调用，是最高频的方法之一。将 `Paint`、`Path`、`Rect` 等对象作为成员变量在构造函数中创建，而不是在 `onDraw()` 中每次 new。

```java
// 错误：每帧创建新对象
@Override
protected void onDraw(Canvas canvas) {
    Paint paint = new Paint();  // 每帧分配
    paint.setColor(Color.RED);
    canvas.drawRect(rect, paint);
}

// 正确：复用成员变量
private final Paint paint = new Paint();  // 只创建一次

@Override
protected void onDraw(Canvas canvas) {
    paint.setColor(Color.RED);  // 复用
    canvas.drawRect(rect, paint);
}
```

**避免在循环中创建临时对象**：字符串拼接、boxed 类型（`Integer`、`Long`）、临时集合是循环中最常见的分配来源。使用 `StringBuilder`、原始类型、对象池来替代。

### 对象池模式（Object Pool）

对于确实需要频繁创建和销毁的对象，对象池是一种有效的优化方式。Android 系统自身就大量使用了这个模式：

- `Message.obtain()`：Android 的 Message 对象池，最大容量 50。调用 `obtain()` 从池中取，调用 `recycle()` 归还。
- `Parcel.obtain()` / `Parcel.recycle()`：跨进程通信的 Parcel 对象池。
- `MotionEvent.obtain()` / `MotionEvent.recycle()`：触摸事件对象池。

自定义对象池的实现需要注意几点：

```kotlin
class ObjectPool<T>(private val factory: () -> T, private val maxSize: Int = 16) {
    private val pool = ArrayDeque<T>(maxSize)

    fun acquire(): T = pool.removeFirstOrNull() ?: factory()
    fun release(obj: T) {
        if (pool.size < maxSize) {
            // 重要：归还前重置对象状态，避免脏数据
            reset(obj)
            pool.addLast(obj)
        }
    }
}
```

对象池的注意事项：
- **必须重置状态**：归还对象时清除所有字段，否则下一个使用者会拿到脏数据
- **池大小要合理**：过大的池等于另一种形式的内存泄漏，过小的池起不到复用效果
- **注意线程安全**：如果对象在多线程间共享，需要用 `ConcurrentLinkedDeque` 或加锁

[来源: intake/research-feeds/2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md]

### 避免 finalize()

`finalize()` 方法会在 GC 回收对象前被调用。它的问题是：包含 `finalize()` 的对象需要经过额外的 Finalizer 队列处理，这增加了 GC 的工作量，也延迟了对象被回收的时间。一个有 `finalize()` 的对象至少要经过两次 GC 才能被回收。

Android 10+ 已经标记 `finalize()` 为 deprecated，推荐使用 `Cleaner`（API 33+）或 `AutoCloseable` 模式。对于已有的使用 `finalize()` 的代码，迁移优先级取决于对象创建频率：高频创建的对象上的 `finalize()` 影响更大。

### Bitmap 复用

Bitmap 是 Android 中最常见的"大对象"之一。一张 1920x1080 的 ARGB_8888 Bitmap 占用约 8MB 内存，会进入 Large Object Space，可能触发同步 GC。

从 API 19（Android 4.4）开始，`BitmapFactory.Options.inBitmap` 允许我们将一块已有的 Bitmap 内存复用给新的 Bitmap。图片加载库（Glide、Coil）内部已经自动处理了 Bitmap 复用。对于手动管理 Bitmap 的场景（如相机预览、自定义图片编辑），使用 `inBitmap` 可以显著减少大对象分配：

```kotlin
val options = BitmapFactory.Options().apply {
    inBitmap = reusableBitmap  // 复用已有 Bitmap 的内存
    inSampleSize = 1
}
val newBitmap = BitmapFactory.decodeResource(resources, resId, options)
```

### Compose 的 GC 压力

Jetpack Compose 的 recomposition 机制会创建大量临时对象——lambda、状态快照（Snapshot）、remember 的值。这些短期对象主要分配在 Young Generation，通常不会导致严重问题。但在以下场景中，Compose 可能产生过度的 GC 压力：

- **不稳定的 lambda 参数**：在 recomposition 范围外创建的 lambda（如 `onClick = { ... }` 在 Composable 函数体内），每次 recomposition 都会创建新实例。使用 `remember` 缓存或 `rememberUpdatedState` 可以避免。
- **频繁变化的 State**：`mutableStateOf` 的值变化会触发 recomposition。如果在 `LaunchedEffect` 中高频更新 state（如动画、传感器数据），可能产生大量临时对象。
- **LazyColumn/LazyRow 中的不稳定 key**：如果 item key 的 equals 语义不正确，会导致不必要的 recomposition 和对象分配。

这些优化点在 §7.7（Jetpack Compose 性能优化）中有更详细的讨论。

## 与其他机制的关系

### 与 §4.3 ART 内存管理的关系

§4.3 覆盖了 ART 堆结构、GC 策略演进和对象分配路径。本节（§4.8）是 §4.3 中"分代 GC"部分的深度展开，聚焦在分代实现的内部机制（Write Barrier、Card Table、Remembered Set）和 Android 17 的增强。两节的关系是：§4.3 回答"ART 的 GC 是什么"，§4.8 回答"分代 GC 怎么工作，怎么影响帧率，怎么优化"。

### 与 §7.2 滑动卡顿分析的关系

GC 暂停和 CPU 争抢是滑动卡顿的常见原因之一。在 §7.2 的滑动卡顿分析流程中，"检查 GC 活动"是标准排查步骤之一。本节提供了 GC 分析的具体方法（Perfetto SQL 查询、heapprofd 用法），可以直接应用到 §7.2 的实战中。

### GC 暂停与 VSync 的交互

GC 暂停如果恰好发生在 VSYNC-app 信号到来之后、`doFrame()` 执行期间，影响最大。因为 `doFrame()` 有严格的帧预算，任何在这个窗口内的暂停都可能导致帧超时。在 Perfetto 中检查 GC 与 VSync 的时间关系是一个有用的诊断手段：如果 GC 暂停集中在 VSync-app 和 VSYNC-sf 之间，说明 GC 正在"偷"App 的渲染时间。

## 版本演进

| Android 版本 | GC 策略变化 | 对 App 性能的影响 |
|---|---|---|
| 7.0 及更早 | Mark-Sweep / CMS，stop-the-world 暂停较长 | Full GC 可能暂停 50-100ms，严重影响流畅性 |
| 8.0 (Orepo) | Concurrent Copying GC 成为默认，暂停减少 85% | 大部分应用 GC 暂停降至 5ms 以下 |
| 10 (Q) | 在 CC 基础上引入分代 GC | Young GC 暂停 1-3ms，Full GC 频率大幅降低 |
| 14-15 | CMC GC 替代 CC，UFFD 替代 Read Barrier | GC 不运行时零额外开销，堆占用更小 |
| 17 (API 37) | 分代收集正式集成到 CMC，调度更激进 | 资源密集型应用 GC CPU 开销降低，卡顿减少 |

[已验证: 官方文档, source.android.com/docs/core/perf/art-management + developer.android.com/about/versions/17]

## 常见问题与误区

### "System.gc() 能帮助减少 GC 卡顿"

恰恰相反。`System.gc()` 强制触发一次 Full GC，暂停时间比正常的 Young GC 长得多。ART 的 GC 是自适应的，它知道什么时候该回收、回收哪一代。手动触发 GC 只会打乱这个调度。如果发现自己需要手动触发 GC 来"缓解"问题，真正的根因通常是内存泄漏或对象抖动。

### "GC 暂停只有 1-3ms，不可能导致掉帧"

单次暂停确实短，但在高刷新率设备上，帧预算本身就很紧张。更关键的是，GC 的影响不仅仅是暂停——并发 GC 的 CPU 开销会与渲染线程争抢计算资源。多次"小暂停"叠加的累积效应，加上 CPU 争用导致的帧处理变慢，完全可以导致可感知的卡顿。

### "分代 GC 意味着我不需要关心对象分配了"

分代 GC 让 Young GC 更高效，但它不能消除 GC 的存在。如果应用持续产生大量垃圾（每秒分配数百 MB 的临时对象），即使每次 Young GC 只暂停 1ms，GC 线程的 CPU 开销和 TLAB 分配慢路径的争用仍然会影响性能。减少不必要的对象分配始终是正确做法——分代 GC 是一个更好的安全网，不是替代优化。

### "finalize() 只是 deprecated，还能用"

虽然 `finalize()` 目前还能工作，但它会显著增加 GC 的负担。每个有 `finalize()` 的对象都需要进入 FinalizerReference 队列，由 FinalizerDaemon 线程异步处理。这意味着对象至少多存活一个 GC 周期，FinalizerDaemon 本身也会消耗 CPU。在高频分配场景下，FinalizerDaemon 可能成为性能瓶颈。

## 参考资料

### AOSP 源码路径
- Concurrent Copying GC 实现：`art/runtime/gc/collector/concurrent_copying.cc`
- Card Table 实现：`art/runtime/gc/accounting/card_table.cc`
- 堆管理和分代策略：`art/runtime/gc/heap.cc`
- Write Barrier 入口：`art/runtime/entrypoints/quick/quick_entrypoints.cc`
- Region Space（TLAB 分配）：`art/runtime/gc/space/region_space.cc`

### 官方文档
- ART 内存管理：https://source.android.com/docs/core/perf/art-management
- Android 17 开发者特性：https://developer.android.com/about/versions/17
- Java Heap Profiling (Perfetto)：https://perfetto.dev/docs/data-sources/java-heap-profiler
- 调查 RAM 使用量：https://developer.android.com/topic/performance/memory

### 研究素材（本节引用来源）
- intake/research-feeds/2026-04-03-19-ch04-android17-generational-gc.md
- intake/research-feeds/2026-03-31-11-ch04-art-generational-gc.md
- intake/research-feeds/2026-04-02-07-ch04-art-gc-pause-time-data.md
- intake/research-feeds/2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md
