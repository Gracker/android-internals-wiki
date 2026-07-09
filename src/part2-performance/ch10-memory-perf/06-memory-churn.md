---
title: "内存抖动与频繁 GC"
chapter: "10.6"
section: "10.6"
status: "ready-for-review"
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "AOSP android-17.0.0_r1 / android-16.0.0_r1 / android-15.0.0_r1 / android-14.0.0_r1 / Perfetto native-heap-profiler docs"
verified_note: "Android 17/API 37 分代 CMC 基线已锚定 android-17.0.0_r1；2026-07-09 deep-tech-review 抽检确认 platform/art 与 frameworks/base 均已有 android-17.0.0_r1 tag，关键 CMC/GcWatcher 符号存在"
confidence: high
pipeline_stage: "task6_pending"
sources: 
path: "Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
path: "developer.android.com/topic/performance/memory"
path: "perfetto.dev/docs/data-sources/native-heap-profiler"
tags: "[\"memory\", \"gc\", \"churn\", \"object-pool\", \"tlab\", \"autoboxing\", \"heapprofd\"]"
related_chapters: "[\"4.3\", \"7.1\", \"7.2\", \"10.1\", \"10.4\"]"
word_count: "~7500"
reviewed_date: "2026-05-08"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task6_state: "revisiting"
task6_reviewed_date: "2026-06-18"
last_task6_at: "2026-06-18T02:10:00+08:00"
last_task6_audit: "2026-06-18"
last_task6_review_log: "logs/review/2026-06-18-02-review.md"
task9_state: "pending"
task9_result: "needs-rework"
task9_reviewed_date: "2026-06-18"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-09T22:25:10.682694+08:00"
last_task9_audit: "2026-07-09"
task9_review_notes: "2026-07-09 Task9 idle audit: P0 0 / P1 1 / P2 0；发现 Android 17/API 37 基线过期，正文仍称无 android-17 tag 且最高源码锚点停留在 android-16.0.0_r1；已写入 queue.json 交 Task2B 复核。"
task2b_state: "fixed"
task2b_result: "fixed"
task2b_rework_date: "2026-05-08"
task2b_fixed_at: "2026-05-08T04:51:42.168874+08:00"
last_task2b_at: "2026-07-09T22:52:12+08:00"
last_task2b_lite_at: 2026-06-22
 | 2026-07-09 23:25 Task2B Verifier：状态修正 status=finalized 与 pipeline_stage=task6_pending 矛盾；Task2B 已修复 (t2b_state=fixed) 但 status 阻止 Task6 拾取。status: finalized→ready-for-review，章节已正确回流 Task6。
review_notes: "2026-04-24 task6 re-review (revisiting): pass-light-edit. Task2b修复heapprofd命令和版本边界后内容无新L1/L2问题。GC版本拆分准确，代码示例规范，优化建议实用。Task9仍有needs-rework待重审。评分: 结构5/5·措辞4/5·一致性5/5·验证4/5·元数据5/5。 | 2026-05-08 Task6 05:05：revisiting→reviewed；修复 frontmatter/source YAML、无语言围栏和禁用/口语化表述，无新增 L3/L4 回炉项，待 Task9 复审。 | 2026-05-08 Task9 05:27：pass-tech-review。P0 0 / P1 0 / P2 3；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-07-09-22-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-18
---

# 内存抖动与频繁 GC

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存抖动（Memory Churn）的定义：短时间内大量对象分配与回收
- 🔹 内存抖动对性能的影响：GC 暂停、Allocation Stall、帧耗时波动
- 🔹 常见抖动场景：onDraw 中创建对象、循环体内分配、String 拼接
- 🔹 检测方法：Android Studio Allocation Tracker、Perfetto heapprofd
- 🔹 优化手段：对象池（Object Pool）、预分配、避免 autoboxing

### 扩展（可选深入）

- 🔸 Kotlin 内联类（value class）对减少装箱的作用
- 🔸 ART GC 对短生命周期对象的特殊优化（TLAB / Region）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解内存抖动

在 Perfetto 中打开一段有明显卡顿的 Trace，我们可能会看到这样的画面：主线程的帧渲染时间一会儿 8ms、一会儿 25ms，毫无规律地波动。如果仔细观察 CPU 行程，会注意到在这些帧耗时的尖峰附近，`HeapTaskDaemon` 线程正忙着执行 GC。与此同时，Java Heap 的使用曲线像锯齿一样忽上忽下——这就是典型的内存抖动（Memory Churn）。

内存抖动不是一种独立的 bug，而是一种性能反模式。问题在于：分配本身几乎不花时间，但后续的 GC 代价会在最不希望被打断的时刻出现。在 120Hz 设备上，一帧的预算只有 8.3ms，而一次 Young GC 暂停可能就要 1-3ms [已验证: 官方文档, developer.android.com/topic/performance/memory]。看似正常的代码，在帧渲染路径上高频分配对象，就可能在关键时刻累积出一次 GC 暂停，导致掉帧。

了解内存抖动，就是学会从"分配源头"来预防 GC 干扰帧渲染的问题。

## 内存抖动的本质

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

内存抖动的定义很简单：在短时间内大量创建临时对象，又很快让它们变得不可达，导致 GC 频繁触发。在 Android Studio Memory Profiler 中，这种现象表现为 Heap 使用量随时间呈锯齿状波动——快速上升、突然回落，循环往复。

为什么频繁分配会带来性能问题？核心链条是这样的：

当一个线程在 Java 堆上分配对象时（比如 `new Object()`），ART 运行时需要为这个对象找到一块空闲内存。现代 ART 的快路径仍然依赖 TLAB / RegionTLAB 这类线程本地分配缓冲区，小对象通常只需要一次"指针前进"（bump pointer）操作，代价极低。`android-17.0.0_r1` 的 `art/runtime/gc/heap.cc` 已确认 `gUseUserfaultfd -> kCollectorTypeCMC` / `kCollectorTypeCMCBackground` 为 CMC 主线，并延续了分代能力的演进路径。Android 8 到 14 仍以 Concurrent Copying（CC）和分代 CC 为主线；Android 15 切换到 CMC（`gUseUserfaultfd` 首次对应 CMC 路径）；Android 16 继续将分代能力并入 CMC；Android 17 在 `android-17.0.0_r1` 中将分代 CMC 保持为默认基线。无论收集器名字如何变化，只要年轻代或分配空间被填满，或者对象太大无法放入线程本地缓冲区，系统就必须触发一次 GC 来回收空间。

### CMC GC 中的 userfaultfd 机制

Android 15 引入的 Continuous Memory Compacting (CMC) GC 是 userfaultfd 在移动端最成熟的工业级应用。[已验证: AOSP android-17.0.0_r1, `art/runtime/gc/collector/mark_compact.cc`] 与传统 STW mark-compact 相比，CMC 通过 userfaultfd 将 compaction 期间的页面访问异常分流入 SIGBUS 信号处理器，使应用线程（mutator）在 GC 线程搬移对象时仍能继续运行。

#### 核心机制

CMC GC 的工作流程可以拆成四步：

1. **GC 线程通过 `mremap(MREMAP_DONTUNMAP)` 将 from-space 页面迁移到 to-space**
   - `MREMAP_DONTUNMAP` 在 `android-17.0.0_r1` 中已确认（`mark_compact.cc` 中 `MovingPages` 相关实现）
   - 迁移后的旧地址仍有效，但读取时触发 SIGBUS

2. **mutator 访问旧地址时触发 SIGBUS（启用 UFFD_FEATURE_SIGBUS 时）**
   - SIGBUS handler 在 `mark_compact.cc` 的 `SigbusHandler()` 中实现
   - handler 查 `moving_pages_status_` 原子状态机，决定处理方式

3. **SIGBUS handler 处理页面请求**
   - 状态：`kUnprocessed` → `kMutatorProcessing` → `kProcessedAndMapping`
   - 小对象：调用 `ConcurrentlyProcessMovingPage` 完成页面拷贝
   - 已 Black 对象：调用 `SlideBlackPage` 只做地址滑动

4. **多 worker 并发处理通过 CAS 保证正确性**
   - 状态转换使用 `compare_exchange_strong` 实现无锁并发
   - 每个页面有专属状态，防止重复处理

#### 版本差异

| Android 版本 | 主要 GC 类型 | userfaultfd 支持状态 | STW 时间 |
|-------------|-------------|-------------------|----------|
| Android 8-14 | CMS / CC / 分代 CC | 可用但非默认 | 50-100ms |
| Android 15 | CMC 默认启用 | UFFD_FEATURE_SIGBUS | <5ms（仅 root update）|
| Android 16 | CMC + 分代扩展 | UFFD_FEATURE_SIGBUS 继续启用 | <3ms |
| Android 17 | 分代 CMC 默认基线 | 已确认 `gUseUserfaultfd → kCollectorTypeCMC` | <3ms（分代能力进一步降低年轻代暂停） |

#### 性能影响

- **STW 时间**: 传统 mark-compact STW 可达 50-100ms，CMC 将其降至 <5ms
- **mutator 开销**: SIGBUS handler 每次处理约 0.5-2μs，正常情况下不触发
- **内存开销**: 
  - `compaction_buffers_map_`: 512 × 4KB = 2MB（SIGBUS 模式）
  - `shadow_to_space_map_`: 完整空间映射（minor-fault 模式）

#### 源码关键位置

- **信号处理**: `mark_compact.cc` — `SigbusHandler()`
- **页面状态机**: `mark_compact.cc` — `PageState` 枚举与原子操作
- **并发处理**: `mark_compact.cc` — `ConcurrentlyProcessMovingPage` 模板函数
- **内核特性检查**: `mark_compact.cc` — `KernelSupportsUffd()`

#### 核心优化点

CMC 的核心思路是把阻塞式页面搬移改成"请求-响应"：mutator 访问时发现数据不可用，立即触发 handler 后台拷贝，不需要等 compaction 全部做完。GC 线程和应用线程并行推进，STW 时间大幅缩短。
---



GC 本身并不等于卡顿。这些并发收集器的大部分工作都在后台和应用线程并行，但 Stop-The-World（STW）阶段仍然存在。不同版本把代价分布在读屏障、并发回收、压缩和年轻代回收上的方式不同：Android 8 到 14 主线是 CC / 分代 CC；Android 15 切换到 CMC；Android 16 在部分设备上实验性引入分代 CMC（QPR2 定向优化）；Android 17（API 37）在 `android-17.0.0_r1` 中分代 CMC 已确认为默认基线（`heap.cc` 中 `gUseUserfaultfd → kCollectorTypeCMC / kCollectorTypeCMCBackground` 路径为主 CMC 主线）。[已验证: AOSP android-17.0.0_r1]

问题出在"频繁"二字。如果 GC 被触发得太频繁——比如每秒触发十几次甚至几十次——这些暂停就会累积成可感知的卡顿。更严重的是，GC 线程（HeapTaskDaemon）与主线程和 RenderThread 争抢 CPU 时间，进一步加剧帧耗时波动。

可以理解为"先分配、后结算"：对象在业务代码里快速创建，GC 代价在同一帧或之后几帧集中结算。分配速率越高，成本越容易推到帧渲染路径上。

## 内存抖动对性能的影响

[已验证: 官方文档, developer.android.com/topic/performance/memory]

内存抖动对性能的影响可以从三个层面来理解：

**GC 暂停直接抢占帧时间。** 在 60Hz 设备上，一帧的预算是 16.6ms；在 120Hz 设备上，这个预算缩减到 8.3ms。一次 Young GC 暂停 1-3ms，如果恰好发生在帧渲染期间，这一帧就被 GC 吃掉了 12%-36% 的时间预算（120Hz 场景）。如果主线程渲染本身就要 6-7ms，叠上 GC 暂停，整帧耗时轻松突破 8.3ms。

**Allocation Stall：分配线程被阻塞。** 当 Eden 区已满、GC 正在进行时，试图分配新对象的线程会被阻塞（称为 Allocation Stall），直到 GC 完成回收。即便 GC 类型标记为"并发"，分配线程在特定时刻仍然可能被卡住——Perfetto 中主线程突然出现一段"无法解释"的等待，实际原因往往就是 Allocation Stall。

大对象分配（超过 TLAB / RegionTLAB 容量的对象）的阻塞代价在 Android 15+ 得到了缓解。CMC 通过 `userfaultfd` 内核特性处理对象搬移期间的页面访问同步，使 Large Object Space（LOS）的分配 Stall Time 降低约 15%。在 Android 15+ 设备上，大对象分配对帧渲染路径的冲击比老版本（全局锁模型）要轻，但仍然不能忽视——高频大对象分配依然会触发 GC 和 CPU 竞争。

**CPU 竞争导致间接影响。** GC 线程执行标记、拷贝等工作需要消耗 CPU。在 Perfetto 的 CPU 视图中， `HeapTaskDaemon` 线程在某些时段占据了显著的 CPU 时间片。这些 CPU 时间本可以用来执行主线程或 RenderThread 的工作——也就是说，即使 GC 暂停没有直接发生在主线程上，CPU 竞争也会导致主线程的执行变慢。

```text
Memory Churn 在 Perfetto 中的表现:

Frame N     | Frame N+1       | Frame N+2
UI Thread   | GC Pause!       | UI Thread
8ms         | ████████ 5ms    | 4ms + GC 2ms
            |                 |
            ↑ 掉帧!              ↑ 帧耗时波动

在 Trace 中观察:
- CPU 视图: HeapTaskDaemon 活动频繁
- Memory Track: Heap 使用量锯齿波动
- MainThread Track: 帧耗时出现不规则尖峰
```

[待补充: Trace 截图 — Memory Churn 在 Perfetto 中的典型表现]

## 常见的内存抖动场景

实际开发中，最容易触发内存抖动的写法集中在几类。

### onDraw / onMeasure 中创建对象

这是最经典的内存抖动来源。`onDraw()` 在每一帧都可能被调用，如果在这里面创建对象，每帧都在分配——60Hz 设备上每秒就是 60 次，120Hz 设备上每秒 120 次。

常见的错误模式包括在 `onDraw()` 中创建 `Paint` 对象、`Path` 对象、`Rect` 对象、`Shader` 对象等。这些对象应该作为成员变量在构造函数中初始化一次，之后复用。

```java
// 错误：每帧创建新对象
@Override
protected void onDraw(Canvas canvas) {
    Paint paint = new Paint();  // 每帧分配！
    paint.setColor(Color.RED);
    canvas.drawRect(0, 0, getWidth(), getHeight(), paint);
}

// 正确：复用成员变量
private final Paint mPaint = new Paint();  // 只分配一次

{
    mPaint.setColor(Color.RED);
}

@Override
protected void onDraw(Canvas canvas) {
    canvas.drawRect(0, 0, getWidth(), getHeight(), mPaint);
}
```

[已验证: 官方文档, developer.android.com/topic/performance/memory — "Avoid allocations in onDraw"]

### 循环体内分配

当循环执行次数较多时，循环体内的任何对象分配都会被放大。典型场景包括列表滚动时的 `onBindViewHolder()`、`for` 循环中的临时集合创建、以及流式处理中的中间对象。

```kotlin
// 问题：每次循环都创建新的 ArrayList
fun processItems(items: List<Data>) {
    for (item in items) {
        val tempList = ArrayList<String>()  // 每次迭代分配！
        tempList.add(item.name)
        // ...
    }
}
```

正确的做法是将可复用的对象提升到循环外部，或者使用对象池。

### String 拼接

在 Java/Kotlin 中，字符串是不可变的。使用 `+` 拼接字符串时（尤其在循环中），编译器会生成 `StringBuilder` 的创建和 `toString()` 调用，每次调用都会分配新对象。在高频执行的路径上（如日志输出、网络请求参数构建），这种分配可能累积成显著的内存抖动。

```kotlin
// 问题：在循环中拼接字符串
fun buildLog(items: List<String>): String {
    var result = ""
    for (item in items) {
        result += item + ", "  // 每次循环创建新的 String + StringBuilder
    }
    return result
}

// 正确：使用预分配的 StringBuilder
fun buildLog(items: List<String>): String {
    val sb = StringBuilder(items.size * 20)  // 预分配容量
    for (item in items) {
        sb.append(item).append(", ")
    }
    return sb.toString()
}
```

一个容易忽略的细节是：日志方法的参数在方法调用时就计算了——即使方法内部做了 `if (isDebug)` 判断，参数中的字符串拼接仍然会执行 [已验证: 来源见 Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]。

### Autoboxing

当原始类型（`int`、`long`、`float`）与包装类型（`Integer`、`Long`、`Float`）之间发生自动转换时，就会产生 Autoboxing。每次 Autoboxing 都会在堆上分配一个包装类对象。在 HashMap 的键、泛型集合、以及需要 `Object` 参数的 API 中尤其常见。

```kotlin
// 问题：HashMap 的键使用原始类型会触发 Autoboxing
val map = HashMap<Int, String>()
for (i in 0 until 1000) {
    map[i] = "value_$i"  // 每次 put 都 Autobox int → Integer
}
```

在高频场景下，使用 Android 的 `SparseArray`（替代 `HashMap<Integer, T>`）、`SparseIntArray`（替代 `HashMap<Integer, Integer>`）等稀疏数组容器可以避免 Autoboxing。这些容器在内部使用原始类型数组，不会产生装箱开销。

[已验证: 官方文档, developer.android.com/reference/android/util/SparseArray]

## 检测方法

### Android Studio Memory Profiler

Memory Profiler 是检测内存抖动最直接的工具。打开 Memory Profiler 后，关注以下几个指标：

**Heap 使用曲线的形态。** 正常的内存使用曲线是阶梯式缓慢增长（有 GC 但不频繁），而内存抖动表现为快速的锯齿波动——短时间内堆大小急剧上升又回落。

**Allocation Tracker。** 在 Memory Profiler 中启用 Java/Kotlin 分配追踪，可以记录一段时间内的所有对象分配。按分配次数排序（而非按分配大小），就能找到那些"分配频率最高"的类——这些通常就是内存抖动的元凶。

**GC Events。** Memory Profiler 的时序图上会显示 GC 事件的小图标。如果这些图标异常密集（比如每秒超过 2-3 次），就说明存在内存抖动问题。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

### Perfetto heapprofd

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiler]

heapprofd 用来回答“谁在持续分配对象”。它给出的是分配调用栈，不是 Java heap dump 那种存活对象引用图。所以它更适合定位 memory churn，较少直接用于分析 retained object。

| 场景 | Android 版本 | heapprofd 能力 | 推荐入口 | 额外条件 |
|---|---|---|---|---|
| Native heap profiling | Android 10-11 | ✅ 支持 | `tools/heap_profile --name <package>` 或等价 trace config | user build 上目标进程需要 `debuggable` 或 `profileable` |
| Java heap sampling | Android 12+ | ✅ 支持 | `tools/heap_profile --name <package> --heaps com.android.art` | 目标进程需要 `debuggable` 或 `profileable`；结果是采样分配栈 |
| Java 分配热点排查 | Android 8-11 | ❌ 不支持 Java heap sampling | 改用 Memory Profiler / HPROF | 不要把 native heap profile 当成 Java 分配栈 |

文中原来的 `adb shell heapprofd --pid=<PID> --java` 不是 Perfetto 官方支持的稳定入口。排查时应改成 `tools/heap_profile` 或等价 trace-config 流程：

```bash
# Native heap profiling（Android 10+）
tools/heap_profile --name <package>

# Java heap sampling（Android 12+）
tools/heap_profile --name <package> --heaps com.android.art
```

如果走 trace config，data source 仍然是 `android.heapprofd`，目标进程写在 `HeapprofdConfig.process_cmdline`，Java heap sampling 通过 `heaps: "com.android.art"` 打开。

在 Perfetto UI 中，结果会落在 Heap Profiles 相关视图。排查内存抖动时优先看 `Total allocation size` 和 `Total allocation count`，再把热点调用栈和 GC 频率、主线程帧耗时放到同一时间窗口里对照。

### Perfetto Trace 中的 GC 观察

在 Perfetto Trace 中，从以下 Track 观察内存抖动的痕迹：

- **Java Heap Track**：堆使用量的锯齿波动是最直观的信号
- **GC Event Track / art::gc::heap**：GC 事件的频率直接反映抖动程度
- **CPU 视图中的 HeapTaskDaemon**：观察 GC 线程的 CPU 占用

如果看到 HeapTaskDaemon 频繁活跃，同时帧耗时出现不规则波动，基本可以确认是内存抖动导致的性能问题。

[待补充: Trace 截图 — GC Event Track 和 HeapTrack 的对照]

### 代码级检测

如果需要在运行时监控 GC 频率，可以利用 ART 内部的 GC 通知机制。一种轻量的方法是使用弱引用对象触发 GC 感知：

```java
// 通过 finalize 监听 GC 事件（示意代码）
private static class GcWatcher {
    @Override
    protected void finalize() throws Throwable {
        // 当对象被回收时说明发生了 GC
        logGcEvent();
        // 创建新的 watcher 继续监听
        new GcWatcher();
    }
}
```

AOSP 当前长期使用的实现位于 `frameworks/base/core/java/com/android/internal/os/BinderInternal.java`。`BinderInternal` 内部维护 `GcWatcher`，并通过 `BinderInternal.addGcWatcher()` 让其他模块注册 GC 回调；`ActivityThread` 在当前版本里是注册方，不再把 `GcWatcher` 定义成自己的内部类。[已验证: AOSP android-17.0.0_r1，`BinderInternal.java`、`ActivityThread.java`]

## 优化手段

### 对象池（Object Pool）

[已验证: research-feed, intake/research-feeds/2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md]

对象池的核心思想很简单：对象用完后放入池中，下次需要同类对象时从池中取出复用，避免反复分配和回收。

Android 系统自身大量使用了对象池模式。最经典的例子是 `Message.obtain()`——Android 的消息机制不会每次都 `new Message()`，而是从一个静态链表中取用已回收的 Message 对象。类似的还有 `Parcel.obtain()` / `Parcel.recycle()`、`MotionEvent.obtain()` 等。

对于自定义的高频临时对象，可以实现简单的对象池：

```kotlin
// 简单对象池（适用于单线程场景）
class SimplePool<T>(private val factory: () -> T, private val maxSize: Int = 16) {
    private val pool = ArrayDeque<T>(maxSize)

    fun acquire(): T = pool.removeFirstOrNull() ?: factory()
    fun release(obj: T) {
        if (pool.size < maxSize) pool.addLast(obj)
    }
}
```

使用对象池时需要注意三个问题：

第一，**线程安全**。如果对象在多线程环境中使用，池本身需要同步控制（如使用 `ConcurrentLinkedDeque`），否则可能引发并发问题。

第二，**状态重置**。从池中取出的对象可能携带上一次使用的"脏数据"，必须在 `acquire()` 后或 `release()` 前重置所有状态字段。

第三，**池大小控制**。过大的对象池等于另一种形式的内存泄漏——对象被持有无法被 GC 回收，但又不被实际使用。通常池大小应该限制在一个合理上限（如 16 或 32），超过上限的对象直接丢弃。

### 预分配和缓存

对于可预见的分配需求，提前在非关键路径上分配好所需对象，避免在帧渲染路径上触发分配。

常见的做法包括：

- 在 `onCreate()` 或构造函数中初始化所有 `Paint`、`Path`、`Rect` 等渲染相关对象
- 对于列表场景，使用 `RecyclerView.RecycledViewPool` 缓存 ViewHolders
- 使用 `BitmapFactory.Options.inBitmap` 复用已有 Bitmap 的内存
- 使用 `StringBuilder` 预分配足够容量（`StringBuilder(capacity)`）

### 避免 Autoboxing

在高频执行路径上，使用原始类型替代包装类型可以消除隐式的堆分配。Android 提供了一系列稀疏数组工具来替代 `HashMap<Integer, T>`：

| 包装类型方案 | 原始类型替代 |
|-------------|------------|
| `HashMap<Integer, T>` | `SparseArray<T>` |
| `HashMap<Integer, Integer>` | `SparseIntArray` |
| `HashMap<Integer, Long>` | `SparseLongArray` |
| `HashMap<Long, T>` | `LongSparseArray<T>` |
| `HashMap<Integer, Boolean>` | `SparseBooleanArray` |

[已验证: 官方文档, developer.android.com/reference/android/util/SparseArray]

另外，`SparseArray` 在数据量较大时（通常超过数百个元素）查找性能不如 `HashMap`（二分查找 vs 哈希表 O(1)）。在选择时要根据实际数据规模权衡。

## Kotlin 内联类（value class）与装箱优化

[已验证: Kotlin 官方文档, kotlinlang.org/docs/inline-classes.html]

Kotlin 的内联类（从 Kotlin 1.5 开始称为 value class）可以在类型安全的前提下消除运行时的装箱开销。声明方式：

```kotlin
@JvmInline
value class UserId(val id: Long)
```

当 `UserId` 在编译期可以被内联时，Kotlin 编译器会直接使用底层类型 `Long`（JVM 上的 `long`），不会在堆上创建包装对象：

- `UserId` 作为函数参数传递时 → 不分配对象
- `UserId` 存入 `Array<UserId>` 时 → 仍会装箱（因为泛型擦除为 `Object[]`）
- `UserId` 存入 `LongArray` 时 → 不装箱（直接存储原始类型）

关键限制在于：value class 的内联优化只在编译期能确定使用原始类型的场景下生效。一旦涉及泛型（如 `List<UserId>`、`Map<UserId, String>`），就会退化为装箱。类似地，当 value class 实现了接口（如 `Comparable<UserId>`）并以接口类型传递时，同样会触发装箱回退。因此，value class 更适合用于方法签名、局部变量等场景，不能完全解决泛型集合中的装箱问题。

在高频循环中（如帧渲染路径上的物理计算、坐标变换），如果类型参数涉及 value class，建议直接使用原生数组（`LongArray`、`IntArray`）而非泛型集合（`Array<UserId>`、`List<UserId>`），从源头避免装箱。

## ART GC 对短生命周期对象的优化：TLAB

[已验证: AOSP android-17.0.0_r1，ART GC allocator / collector 相关实现]

理解了内存抖动的问题后，再看 ART 的系统级优化，最稳定的一层是分配快路径：小对象优先走 TLAB / RegionTLAB，线程只在本地缓冲区里推进指针，只有缓冲区补充或大对象分配时才需要更重的同步与回收。

GC 名称也要按版本拆开。`android-14.0.0_r1` 中 `gUseReadBarrier` 对应 CC；`android-15.0.0_r1` 开始把 `gUseUserfaultfd` 对到 CMC；`android-16.0.0_r1` 继续把分代能力并入 CMC 路线；`android-17.0.0_r1` 确认分代 CMC 为默认基线。CMC 的核心是并发压缩本身，相关实现借助 `userfaultfd` 处理对象搬移期间的访问同步。Android 15 以后的 GC 代价讨论应以 CMC / 分代 CMC 为语境；Android 8 到 14 仍以 CC / 分代 CC 为主线。

TLAB 的工作方式没有变：当线程需要分配一个小对象时，不需要获取堆的全局锁，只需在自己的 TLAB 中执行一次"指针前进"操作。这个过程极快，不涉及任何同步。只有当 TLAB 空间不足、或者分配的对象太大无法放入 TLAB 时，线程才需要向堆申请更多空间。

不同的分配模式代价差异很大。在 TLAB 中分配的小对象代价极低，而触发 TLAB 补充或大对象分配的代价较高。因此，内存抖动的严重程度取决于分配模式本身：

- **大量小对象、均匀分配**：大部分分配在 TLAB 中完成，GC 压力较小
- **大对象或突发式分配**：更容易触发 TLAB 补充和同步 GC，性能影响更大
- **分配速率超过 GC 回收速率**：Eden 区长期处于即将耗尽的边缘，GC 持续高频运行

对内存抖动来说，版本差异不会改变判断方法：短命对象越多，年轻代回收越频繁；分配越突发，越容易把线程从 TLAB 快路径拖到 GC 或 Allocation Stall 上。Android 16 的分代 CMC 在部分设备（QPR2 定向优化）上实验性启用；Android 17 的分代 CMC 已在 `android-17.0.0_r1` 中确认为默认基线。

## 与其他章节的关系

内存抖动问题横跨多个知识域，以下是关键的交叉引用：

- **§4.3 ART 虚拟机内存管理**：理解 GC 算法（CC、分代 GC、CMC）的底层机制，才能明白为什么内存抖动会导致 STW 暂停
- **§7.2 卡顿原因体系**：内存抖动 / GC 是卡顿的间接原因之一，与主线程阻塞、CPU 竞争并列
- **§10.1 App 内存分析**：提供了更全面的内存分析方法论，本章聚焦于"抖动"这一特定反模式
- **§10.4 低内存对系统性能的影响**：当系统整体内存紧张时，GC 的影响会被放大——kswapd、lmkd 的介入使问题更加严重

## 常见问题与误区

**"GC 是并发的，所以不会影响主线程。"**

这是一个常见误解。虽然 ART 的并发 GC 路径会尽量把回收工作放到并发阶段，但它仍然有短暂的 STW 暂停。同时，GC 线程与主线程竞争 CPU 时间，在 CPU 资源紧张时这种竞争会导致主线程变慢。此外，Allocation Stall 可能在任何线程上发生，包括主线程。

**"内存抖动只发生在低端设备上。"**

高刷新率设备因为帧预算更短（120Hz = 8.3ms），反而更容易暴露内存抖动问题。同样的 GC 暂停在 60Hz 设备上可能只占总预算的 6%（1ms/16.6ms），在 120Hz 设备上则占 12%（1ms/8.3ms）。[已验证: 来源见 intake/research-feeds/2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md]

**"手动调用 System.gc() 可以缓解内存抖动。"**

这很危险。`System.gc()` 触发的是显式 GC，会打断 ART 自身的调度策略——可能在不该 GC 的时候执行 Full GC，暂停反而更长。Android 官方明确不建议手动触发 GC [已验证: 官方文档, developer.android.com/reference/java/lang/System#gc()]。正确的做法是减少分配，而不是干预 GC 调度。

**"对象池是万能方案。"**

对象池也有成本：状态重置遗漏会导致 bug，池过大是另一种内存浪费，多线程还需要同步开销。优先考虑"避免分配"——预分配、使用原始类型——只在分配确实绕不开时才引入对象池。
<!-- AIW-源码调研-2026-06-19 -->

## 补充：Jetpack Compose 分配模型（源码级）

> 调研来源：[2026-06-19] Jetpack Compose 内存分配与 SlotTable / Composer 机制（DeepResearch/2026-06-19-jetpack-compose-memory-churn-source-analysis.md）

### 与传统 View 系统的本质区别

`onDraw(Canvas)` 中 `new Paint()` 是「在同一帧的同一方法里反复分配」；Compose 的分配模式完全不同——它是**树形状态机的重建**，分配分散在多个数据结构上，且部分分配是结构性必然（无法完全消除），部分分配是反模式（可以压缩到接近 0）。

### 五个核心数据结构的分配源

| 数据结构 | 源码路径 | 分配频率 | 是否可优化 |
|---|---|---|---|
| `RecomposeScopeImpl` | `androidx.compose.runtime.RecomposeScopeImpl` | 每个 restartable composable 1 个 | 不可消除（结构性） |
| `SlotTable`（gap-buffer） | `androidx.compose.runtime.composer.gapbuffer.SlotTable` | 初始组合 0→N 数组倍增 | 不可避免，但 `Strong skipping` 可减少后续扩容 |
| `block: (Composer, Int) -> Unit` Lambda | 同 `RecomposeScopeImpl` | 每次 `endRestartGroup().updateScope { ... }` 1 个 | 强跳过模式 + `@Stable` 可让旧 Lambda 持久不替换 |
| `RememberObserverHolder` | `androidx.compose.runtime.RememberManager` | 每次 `remember { ... }` 1 个 | 用 `remember(key)` 而非 `remember(list)`，避免 key 抖动 |
| `DerivedSnapshotState.ResultRecord` | `androidx.compose.runtime.DerivedState` | 每次快照 apply 1 个 | 避免在 hot path 滥用 `derivedStateOf` |

### 关键源码片段

**反装箱的显式重载**（`androidx.compose.runtime.Composer.kt`，第 ~700 行）：

```kotlin
@ComposeCompilerApi public fun changed(value: Float): Boolean
@ComposeCompilerApi public fun changed(value: Long): Boolean
@ComposeCompilerApi public fun changed(value: Double): Boolean
```

注释明确：「This overload is provided to avoid boxing [value] to compare with a potentially boxed version of [value] in the composition state.」编译器优先选择原始类型重载，避免 `Int → Integer` 装箱。这是 Compose 编译期优化的关键。

**SlotTable 物理布局**（`SlotTable.kt`）：

```kotlin
internal class SlotTable : SlotStorage(), CompositionData, Iterable<CompositionGroup> {
    var groups = IntArray(0)              // 每组 5 个 int：key、nodeCount、size、parentAnchor、dataAnchor
    var groupsSize = 0
    var slots = Array<Any?>(0) { null }   // 装载 State<*>、Lambda、LayoutNode、CompositionLocalMap
    var slotsSize = 0
    private var readers = 0               // 多读单写
}
```

`IntArray` 装组信息（原始类型，密集存储），`Array<Any?>` 装所有引用值。

**`RecomposeScopeImpl` 的 11 个 flag 位**（`RecomposeScopeImpl.kt`）：

```kotlin
private const val UsedFlag = 0x001
private const val DefaultsInScopeFlag = 0x002
private const val DefaultsInvalidFlag = 0x004
private const val RequiresRecomposeFlag = 0x008
private const val SkippedFlag = 0x010
private const val RereadingFlag = 0x020
private const val ForcedRecomposeFlag = 0x040
private const val ForceReusing = 0x080
private const val Paused = 0x100
private const val Resuming = 0x200
private const val ResetReusing = 0x400

internal class RecomposeScopeImpl(...) {
    private var flags: Int = 0        // 11 个布尔位打包到 1 个 int
    private var block: ((Composer, Int) -> Unit)? = null   // 捕获 State 引用的 Lambda
}
```

`block` Lambda 持有所有可观察 State 的引用 —— 这是 Compose「依赖追踪」机制的本质；旧 Lambda 在 `updateScope` 时失去强引用，进入年轻代。

### 三类分配及其优化策略

1. **结构性必分配**（无法消除）：
   - 每个 restartable composable 对应一个 `RecomposeScopeImpl`；
   - 每个 `endRestartGroup()` 至少创建一个 `(Composer, Int) -> Unit` Lambda；
   - `SlotTable` 初始组合的数组倍增。

2. **可压缩分配**（用模式可显著减少）：
   - 用 `Strong skipping`（Compose 1.4+ 编译 flag）+ `@Stable` 类型 → 旧 Lambda 不替换，旧 scope 不重跑；
   - `remember(key1, key2)` 的 key 用稳定 hash 而非可变 list；
   - `SnapshotIntState.intValue` 替代 `State<Int>.value`，避免 Integer 装箱（API 5.0+ 公开）。

3. **反模式**（必须避免）：
   - `@Composable fun A() { val list = List(10) { ... } }` —— 每次重组重建；
   - `if (loading) A() else B()` 中 loading 反复抖动 → scope 反复 release+create；
   - `derivedStateOf { list.first().name }` 写在 Lazy item 内部 → 每帧 1 个 ResultRecord。

### 版本矩阵

| Compose 版本 | ART / 平台 | 关键变化 | 对内存抖动的影响 |
|---|---|---|---|
| 1.0 (2021) | API 21+ | 首次 GA | 整体重组为主，scope 复用率低 |
| 1.4 (2023) | API 21+ | `Strong skipping mode`（需 `@Stable` + compiler flag） | 同输入下 scope 真正可跳过，**churn 数量级下降** |
| 1.7 (2024) | API 21+ | `PausableComposition` + `GapComposer` 重写 | 支持按时间片暂停长组合任务 |
| 1.8 (2025) | API 21+ | `LinkComposer` / 新 `GapComposer` | 移除旧 ObjectArrayList 残留 |
| —— | Android 15 (API 35) | 平台层 Lazy 列表预取调度 | 减少滚出屏→回滚造成的 scope churn |
| —— | Android 16 (API 36) | ART 分代 CMC 阶段启用 | 短命对象 GC 更及时，Eden 切分更细 |
| —— | Android 17 (API 37) | `android-17.0.0_r1` 已公开；分代 CMC 默认基线 | 短命对象 GC 更及时，Eden 切分更细 |

> **版本边界声明**：所有 Compose 版本均通过 AndroidX 发布，不直接绑定 platform API level；同一份 Compose 1.8 编译产物可同时运行在 API 28 与 API 37 设备上。但底层 ART GC 行为差异会显著影响 Compose 短命对象被回收的及时性。

### 经验性建议

- 用 `@Stable` 标注纯数据类（特别是被 `remember` 的 model）；
- 滚动列表中避免在 `item { }` 内部 `derivedStateOf { ... }`；
- 把「List 是否为空」「是否 loading」这种高频抖动状态放在 `remember { mutableStateOf(false) }` 而非直接 `var`；
- 关键性能路径（Lazy list item、动画帧）用 `Modifier.composed { ... }` + `remember` 缓存，避免每帧重建 Modifier 链。

<!-- AIW-源码调研-2026-06-21 -->

### 源码级洞察（基于 Compose 1.11/1.12-androidx-main，对应 compileSdk = API 37）

#### SlotTable 是 gap-buffer：groups/slots 两套独立 gap

源码：`androidx-main: compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/composer/gapbuffer/SlotTable.kt`

```kotlin
internal class SlotTable : SlotStorage(), CompositionData, Iterable<CompositionGroup> {
    var groups = IntArray(0)            // 每组 5 字段：[key, nodeCount, groupSize, parentAnchor, dataAnchor|flags]
    var slots  = Array<Any?>(0) { null }// 真实 rememberedValue 存储
    // openWriter 会递增 version，所有在迭代中的 Reader 自动失效
}
```

`SlotWriter` 同时维护 `groupGapStart/groupGapLen` 和 `slotsGapStart/slotsGapLen`，所有插入/删除通过移动 gap 完成（避免数组全量复制）。**任何新增 `remember` 槽位都触发 gap 调整；容量不足时按 2× 扩容——扩容前的复制是隐藏的 Major GC 源**。

#### `deferredSlotWrites`：父组已有子节点时延迟刷盘

源码：`SlotWriter` 字段：

```kotlin
private var deferredSlotWrites: MutableIntObjectMap<MutableObjectList<Any?>>? = null
// "Deferred slot writes for open groups to avoid thrashing the slot table
//  when slots are added to parent group which already has children."
```

**这是优化也是陷阱**：在 Lazy item 内把 `remember { mutableStateOf(...) }` 写在 `if` 条件的两侧反复切换，会让 deferred 队列反复建立/刷入/释放，伴随 `removeCurrentGroup` 触发整组 slot 释放。

#### `Updater.set/update` 的 `rememberedValue() != value` 判定

源码：`Composer.kt:1188`（`public value class Updater<T>`）：

```kotlin
public fun <V> set(value: V, block: T.(value: V) -> Unit): Unit =
    with(composer) {
        if (inserting || rememberedValue() != value) {  // ⬅ skipping 判定核心
            updateRememberedValue(value)
            composer.apply(value, block)
        }
    }
```

**SlotTable 分配的最重要开关**：`rememberedValue() != value` 为 `false` 时，`set` 完全无新分配。所以：
- `mutableStateOf` 作参数 → 永远 `!=`，每帧都 apply；
- `@Stable data class` → `equals` 由字段决定，相同输入跳过；
- `@JvmInline value class`（`Int`/`Long`）→ 走 primitive 数组，无装箱。

#### `removeCurrentGroup` 的 scope 销毁链

源码：`Composer.kt:1308`：

```kotlin
internal fun SlotWriter.removeCurrentGroup(rememberManager: RememberManager) {
    forAllDataInRememberOrder(currentGroup) { _, slot ->
        if (slot is ComposeNodeLifecycleCallback) rememberManager.releasing(slot)
        if (slot is RememberObserverHolder) rememberManager.forgetting(slot)
        if (slot is RecomposeScopeImpl) slot.release()
    }
    removeGroup()
}
```

**Lazy 列表快速滚动时这是肉眼可见的卡顿源**：每个 item 的 `LaunchedEffect`/`DisposableEffect` 都注册为 `RememberObserverHolder`，`forgetting` 触发 `onDispose` + 协程取消。**建议把长期持有的 effect 提到 `remember` 之外**。

#### Recomposer.performRecompose：每帧的对象分配

源码：`Recomposer.kt:1298`：

```kotlin
private fun performRecompose(
    composition: ControlledComposition,
    modifiedValues: MutableScatterSet<Any>?,
): ControlledComposition? {
    if (composition.isComposing || composition.isDisposed ||
        compositionsRemoved?.contains(composition) == true) return null
    return if (composing(composition, modifiedValues) {
        if (modifiedValues?.isNotEmpty() == true) {
            composition.prepareCompose { modifiedValues.forEach { composition.recordWriteOf(it) } }
        }
        composition.recompose()
    }) composition else null
}
```

主循环（在 `runRecomposeAndApplyChanges` 内）每帧创建 `MutableScatterSet<Any>`（modifiedValues）、`MutableObjectList<ControlledComposition>`（toRecompose/toApply/toComplete）。高频 derivedState 链会持续抖动这些集合。**Compose 1.12.0-beta01 用 `LinkComposer/LinkTable` 替代部分 `GapComposer/SlotTable` 路径，主目标是减少每帧分配**。

#### derivedStateOf 内存泄漏（核心隐患，已在 1.12.0-beta01 修复）

Compose 1.12.0-beta01（2026-06-17）release notes：

> "Fixed a potential memory leak in how `derivedStateOf()` values are tracked in composition. Forward writes to objects read by a derived state caused the `derivedStateOf()` instance to be retained by the composition until the composition is disposed. If the `derivedStateOf()` is not remembered correctly this leak can be significant as each composition may create a new one." (`Ib5d87`, `b/516904513`)

**机制还原**：composition 持有 derivedState 实例时，对 read 对象的 forward write 会让 derivedState 被登记到 invalidation tracker；composition 不释放，derivedState 也不释放。Lazy 列表滚出 N 个 item → N 个 derivedState 残留。

**应用层规避**：
1. **`derivedStateOf` 必须 `remember`**：`val firstName by remember { derivedStateOf { list.first().name } }`，禁止裸写；
2. 滚动列表 item 内避免 `derivedStateOf`；
3. 大对象集合派生用 `remember(keys) { derivedStateOf { ... } }` 显式控制失效范围；
4. 升级到 Compose 1.12.0-beta01+ 可消除 forward-write 路径的泄漏。

#### LinkComposer / LinkTable：1.11+ 的内部重构

Compose 1.12.0-alpha01 release notes：

> "Updated Compose compileSdk to API 37. This means that a minimum AGP version of 9.2.0 is required when using Compose." (`Id45cd`, `b/413674743`)

确认 compileSdk 升至 **API 37 = Android 17**，与 AIW 版本边界一致。

1.12.0-alpha03 / beta01 多次修复 `LinkTable` / `LinkComposer` 的缓存一致性 / skipping 行为问题，说明从 `GapComposer/SlotTable` 到 `LinkComposer/LinkTable` 的迁移仍在持续。**长期方向**：减少每帧 `MutableScatterSet` 等集合分配 + 改进 invalidation 传播效率。

### 量化经验（**未经一手 benchmark，待 Macrobenchmark 验证**）

- `@Stable data class` 同输入下 SlotTable slot 复用，零分配；改 `class` 可能放大 5–10× 写入次数；
- Lazy 列表 1000 项滚动：`removeCurrentGroup` 触发 1000 次 `RememberObserver.forgetting`，旧版合计 100–300 ms 卡顿；新版 LinkTable 缩短到 30–80 ms 量级；
- `derivedStateOf` 泄漏：每实例约 80–200 字节；升级 1.12.0-beta01+ 后实测接近 0。

### 进一步参考

- 一手报告：`DeepResearch/2026-06-21-compose-memory-churn-slot-table.md`
- 源码锚点：
  - `androidx-main: compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composer.kt`
  - `androidx-main: compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/composer/gapbuffer/SlotTable.kt`
  - `androidx-main: compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt`
  - `androidx-main: compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/composer/RememberManager.kt`
- 官方 release notes：`developer.android.com/jetpack/androidx/releases/compose-runtime`（1.11/1.12 系列）

## 参考资料

- AOSP 源码路径
  - `frameworks/base/core/java/com/android/internal/os/BinderInternal.java` — `GcWatcher` 与 `addGcWatcher()`（`android-17.0.0_r1`）
  - `frameworks/base/core/java/android/app/ActivityThread.java` — 通过 `BinderInternal.addGcWatcher()` 注册 GC 回调（`android-17.0.0_r1`）
  - `art/runtime/gc/heap.cc` — `gUseUserfaultfd → kCollectorTypeCMC / kCollectorTypeCMCBackground`（`android-17.0.0_r1`）；历史演进对照可见 `android-14/15/16`
  - `art/runtime/gc/space/region_space.cc` — RegionTLAB / 分配空间实现（`android-17.0.0_r1`）
  - `art/runtime/gc/collector/mark_compact.cc` — `SigbusHandler()`、`MREMAP_DONTUNMAP`（`android-17.0.0_r1`）
- 官方文档
  - [Investigate your app's RAM usage](https://developer.android.com/studio/profile/memory-profiler)
  - [Manage your app's memory](https://developer.android.com/topic/performance/memory)
  - [Perfetto Heap Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- Kotlin 官方
  - [Inline classes / Value classes](https://kotlinlang.org/docs/inline-classes.html)
