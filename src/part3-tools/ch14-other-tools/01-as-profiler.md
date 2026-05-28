---

title: "Android Studio Profiler"
chapter: "14.1"
section: "14.1"
status: ready-for-review
polish_count: 1
drafted_date: "2026-04-03"
reviewed_date: "2026-05-19"
reviewed_by: "openclaw-task6"
polish_date: "2026-04-08"
polish_by: "task2b-polish"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "official documentation + AOSP android-16"
confidence: high
sources:
  - type: blog
    path: "Obsidian Cubox: Android Studio 中 CPU Profiler 系统性能分析工具的使用 - 掘金"
  - type: blog
    path: "Obsidian Cubox: Can you trust time measurements in Profiler - ProAndroidDev"
  - type: official
    path: "developer.android.com/studio/profile"
  - type: blog
    path: "androidperformance.com (高爷博客)"
tags:
  - android
  - profiling
  - research
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task9_state: "pending"
task2b_state: "fixed"
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-05-28"
task6_result: "pass-light-edit"
related_chapters: ["5.4", "13.3", "13.5", "13.7", "14.2", "14.11"]
task9_result: needs-rework
task9_reviewed_date: "2026-05-19"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-19T12:20:00+08:00"
last_task6_at: "2026-05-19T12:07:00+08:00"
task6_review_notes: "2026-05-19 12:07 Task6 复审：pass-light-edit。L1/L2 小修 4 处，清理结构性元叙述与复述型过渡；Task9 仍 pending/needs-rework，未自动晋升。"
task9_review_notes: "2026-05-19 12:20 Task9 复审：needs-rework。P0 0 / P1 4 / P2 0；Network Inspector 入口/timeline、profileable Java Method Trace、Power Profiler ODPM app 归因、APP_FULLY_DRAWN 语义仍需回炉。2026-05-28 Task2B Lite 已做局部修复，回流 Task6。"
last_task6_review_log: "logs/review/2026-05-19-12-review.md"
last_task9_review_log: "logs/deep-review/2026-05-19-12-deep-review.md"
---


# Android Studio Profiler

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android Studio Profiler 概述：CPU、Memory、Network、Energy Profiler
- 🔹 CPU Profiler：System Trace vs Method Trace vs Callstack Sample
- 🔹 Memory Profiler：实时内存分配图、Heap Dump、Allocation Tracking
- 🔹 各 Profiler 模式的性能开销与适用场景
- 🔹 Profiler 与 Perfetto 的互补关系

### 扩展（可选深入）

- 🔸 Power Profiler（Android Studio Hedgehog+）
- 🔸 使用 Profiler API 在代码中触发 profiling

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要了解 Android Studio Profiler

遇到 App 滑动卡顿、启动慢、内存泄漏、耗电快这类性能问题时，第一件事是确认问题位置。在不知道问题位置的情况下，所有优化方案都是盲猜。Android Studio Profiler 提供了从"不知道"走到"知道"的第一个入口。

这个工具把 Google 已有的多个性能分析工具（Perfetto、Simpleperf、JVMTI 等）集成到 Android Studio 的 IDE 中，提供统一的界面和交互方式。它的优势在于：能在 IDE 里直接看到 CPU、内存、网络、功耗的实时数据，并在同一个窗口中点击跳转到源码，分析效率比在命令行和网页工具之间来回切换高得多。

但 Profiler 有它的局限性——它主要关注单个 App 的视角，看不到系统全局的状态。当需要理解 App 和系统服务之间的交互、多个进程之间的竞争、或者整个渲染管线的调度情况，Perfetto 的全局视野是不可替代的。所以 Profiler 和 Perfetto 不是互相替代的关系，而是互补的：Profiler 适合快速定位 App 侧的瓶颈，Perfetto 适合深入分析系统侧的上下文。

[已验证: 官方文档, developer.android.com/studio/profile]

## Profiler 的整体结构

打开 Android Studio，点击底部的 Profiler 标签页（或者 View → Tool Windows → Profiler），就能看到 Profiler 的主界面。在 Android Studio Koala（2024.1）及之后的版本中，Profiler 采用了任务导向的新界面：首页列出了几个常见的分析任务，点击即可开始，相比旧版本启动速度提升了约 60%。[已验证: 官方文档, developer.android.com/studio/releases]

Profiler 的核心分析模块对应不同类别的性能问题。Android Studio 2020.3.1+ 中，旧版 Network Profiler 已迁移到 App Inspection > Network Inspector，不再作为 Profiler 同级模块共享同一条 timeline：

CPU Profiler 解决"App 慢在哪里"的问题。它提供了三种 CPU 分析模式——System Trace、Java Method Trace 和 Callstack Sample——分别对应不同的精度和开销级别，适用于不同的分析场景。三种模式的取舍会直接影响数据可信度。

Memory Profiler 解决"App 的内存怎么了"的问题。它可以实时展示 Java 堆和 Native 堆的内存变化曲线，支持 Heap Dump（堆快照）分析对象引用关系，还支持 Allocation Tracking 追踪对象的分配来源。当怀疑有内存泄漏或者内存抖动时，Memory Profiler 是最直接的切入点。

Network Inspector（Android Studio 2020.3.1+ 从 Profiler 内的 Network Profiler 迁移到 App Inspection > Network Inspector）展示 App 的网络活动——请求的时间、大小、响应状态。虽然它的深度不如专业的网络抓包工具（如 Charles、mitmproxy），但对于快速确认"是不是网络请求太慢导致了卡顿"这类问题非常方便。旧版本 Android Studio（2020.3.1 之前）的 Network Profiler 仍在 Profiler 面板中显示。

Energy Profiler（在 Android Studio Hedgehog 之后升级为 Power Profiler）展示 App 的功耗来源。它分别展示 CPU、网络、GPS 等子系统的电量消耗，帮助定位高耗电的行为。

CPU、Memory 与 Power 视图适合按同一操作窗口做交叉排查；网络请求在新版本 Android Studio 中要切到 Network Inspector 对照时间范围。

## CPU Profiler：三种分析模式的深度对比

CPU Profiler 是日常性能分析中使用频率最高的模块。它提供三种分析模式，选模式前要先区分精度和开销——选错模式，要么数据不准确，要么 App 直接卡死。

### System Trace（系统追踪）

System Trace 是 CPU Profiler 中开销最低的模式。它的底层就是 Perfetto（在 Android 10 之前是 Systrace），通过 atrace 机制采集系统预埋的 TracePoint 以及通过 `android.os.Trace` 自定义的标记。

每个 TracePoint 的开销大约 5μs，对于一般的分析方法来说完全可以忽略。抓取 System Trace 时，App 的运行表现和正常使用几乎没有差别——这是它最大的优势。因为开销低，所以数据可信度高，适合分析 UI 卡顿、帧渲染耗时、线程调度等需要"接近真实环境"的场景。

System Trace 的局限是：它只能看到系统预埋的和手动标记的 TracePoint，无法看到每个 Java 方法的调用耗时。如果卡顿的原因在某个具体方法内部（比如一个耗时的排序算法），System Trace 只能定位到大概范围，需要更精细的工具来进一步分析。

在 Profiler 中选择 "System Trace Recording" 即可开始抓取。抓取完成后，数据可以导出为 `.perfetto-trace` 文件，在 Perfetto UI（ui.perfetto.dev）中打开做更深入的分析——因此，Profiler 的 System Trace 和命令行抓取的 Perfetto Trace 是完全兼容的。

[已验证: 官方文档, developer.android.com/studio/profile/cpu-profiler]

### Java Method Trace（方法追踪）

Java Method Trace 是最"精确"但也最"重"的模式。它通过在虚拟机层面插桩（instrumentation），记录每一个 Java/Kotlin 方法的进入和退出时间戳。理论上，它能揭示每一个方法的精确执行时间。

但精确的代价是巨大的运行时开销。插桩会在每个方法的入口和出口添加额外的记录逻辑，这不仅拖慢了方法本身的执行速度，还改变了 CPU 缓存的行为和 JIT 的优化决策。一个在正常执行时只需 5ms 的方法，在 Method Trace 模式下可能显示为 50ms 甚至 130ms——10 倍以上的膨胀是很常见的。

Method Trace 给出的时间数据不能直接当真。它更适合用来理解"方法的调用顺序和层级关系"，而不是"方法到底执行了多久"。当需要确认"某段代码到底调用了哪些子方法、调用链有多深"时，Method Trace 的全量记录能力是其他模式无法替代的。

实际使用中，建议将 Method Trace 的录制时间控制在 5 秒以内。超过 5 秒，一方面数据量会非常庞大导致 Profiler 界面卡顿，另一方面长时间的开销累积会使数据的失真更加严重。

Paulina Sadowska 在对比测试中发现，同一个 `onBindViewHolder` 方法，在 Sample 模式下报告约 10ms，在 Trace 模式下报告约 130ms，而用 Systrace（System Trace）测量只有约 5.5ms。这个差距直观地说明了 Method Trace 的开销影响。[引用: proandroiddev.com/can-you-trust-time-measurements-in-profiler]

### Callstack Sample（调用栈采样）

Callstack Sample 是在精度和开销之间取得平衡的模式。它不是记录每一个方法的调用，而是以固定的时间间隔（通常几毫秒）对线程的调用栈进行"快照"，统计每个方法出现在调用栈上的频率。

因为不需要插桩，Callstack Sample 的开销比 Method Trace 低得多，App 的运行表现更加接近真实。但采样的本质决定了它有一个固有的局限：执行时间短于采样间隔的方法很可能被完全遗漏。如果有一个方法只执行了 1ms，而采样间隔是 10ms，那么这个方法有 90% 的概率不会出现在结果中。

Callstack Sample 最适合找"CPU 热点"——那些长时间占用 CPU 的方法。对于一个耗时 200ms 的排序方法，无论采样间隔怎么设，它都会被反复命中。但对于一个快速但被频繁调用的小方法（比如 `String.charAt()`），它可能完全不出现在采样结果中，即使它被调用了一万次、累计耗时可能很可观。

在 Android Studio Meercat (2024.3) 及后续版本中，Google 持续改进采样引擎的准确性，降低 debug profiling 时的误报率，使 Callstack Sample 在 debug 构建中的数据更加可靠。[待验证: 具体版本对应的采样引擎改进细节]

### 三种模式的选择决策

把这三种模式放在一个决策框架中，选择逻辑是这样的：

面对一个性能问题、还不知道问题位置时，第一步永远用 System Trace。它的开销最低、数据最可信，能快速回答：卡顿发生在主线程的哪个阶段？是 input 处理慢、动画计算慢、还是 measure/layout/draw 慢？是线程调度的问题（线程被挂起或者跑在了小核上），还是本身的执行就慢？

System Trace 定位到大致范围后，如果需要进一步看某个方法内部的调用关系和层级，第二步用 Callstack Sample。它能在可接受的开销下定位：那个耗时很长的 draw 阶段，到底是哪个方法在吃 CPU？

只有当需要确认某个方法的具体调用链（比如"这个方法内部到底调了哪些子方法"），才使用 Method Trace。而且必须记住：Method Trace 报告的时间数据因为开销太大不能直接参考，它的主要价值是调用关系的全量记录。

| 模式 | 底层工具 | 开销 | 精度 | 适用场景 |
|------|---------|------|------|---------|
| System Trace | Perfetto/atrace | ~5μs/事件 | 事件级 | UI 卡顿、线程调度、渲染管线 |
| Callstack Sample | Simpleperf | 中等 | 统计级 | CPU 热点定位 |
| Java Method Trace | ART 插桩 | 很高 | 方法级 | 调用链全量分析 |

[已验证: 官方文档, developer.android.com/studio/profile/cpu-profiler]

## Memory Profiler：从实时曲线到堆快照

Memory Profiler 是排查内存问题的主力工具。它的界面顶部是一条实时内存曲线，展示 Java 堆、Native 堆、Graphics、Stack、Code 等各类内存的变化趋势。当反复操作一个功能，看到这条曲线只涨不降、像楼梯一样一步一步往上走时，基本就可以判断存在内存泄漏。

### 实时内存曲线

实时曲线是内存状态的"第一眼"概览。曲线上每个突然的跳升对应着一次大的内存分配，每个突然的下降对应着一次 GC。如果 GC 之后内存并没有回到之前的水平，那说明有对象无法被回收——这就是内存泄漏的典型信号。

在 Android 8.0（API 26）之后，Memory Profiler 的数据精度大幅提升。这得益于 Android 8.0 引入的 JVMTI（JVM Tool Interface）机制，Profiler 通过 JVMTI 获取的内存数据比之前通过 DDMS 协议获取的数据更加准确和详细。[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

### Heap Dump（堆快照）

当实时曲线暗示有泄漏时，下一步就是抓 Heap Dump。点击 Memory Profiler 中的 "Capture Heap Dump" 按钮（或者选择 "Analyze Memory Usage" 任务），Profiler 会冻结当前时刻的 Java 堆，记录下所有存活对象的信息：类名、实例数量、Shallow Size（对象自身占用的内存）、Retained Size（对象及其引用链持有的总内存）。

Heap Dump 的分析有两个关键视角。第一个是按类名查看：找到实例数量异常多的类，比如 `MainActivity` 在堆中出现了 5 个实例——正常情况应该只有 1 个。第二个是按引用链查看：选中一个可疑对象，Profiler 会展示它的 GC Root 引用链，指明是哪条引用阻止了对象被回收——这是定位泄漏根因的关键信息。

Profiler 还提供了自动检测 Activity 和 Fragment 泄漏的功能。它会标记出那些已经调用了 `onDestroy()` 但仍然在堆中存活的 Activity/Fragment 实例，帮助快速定位最常见的一类泄漏。

抓取 Heap Dump 的瞬间会暂停应用（stop-the-world），所以不要在生产环境或性能测试期间使用。

### Allocation Tracking（分配追踪）

Allocation Tracking 关注另一个问题："谁在频繁分配"。当在 Perfetto 中看到 GC 事件特别密集，或者 Memory Profiler 的实时曲线上出现锯齿状的快速波动，说明有大量的短生命周期对象被频繁创建和销毁——这就是内存抖动（Memory Churn）。

点击 "Track Memory Consumption"（Java/Kotlin Allocations）任务，Profiler 会开始记录每个对象的分配事件：在哪个线程上、通过哪个调用栈、分配了多大的内存。这些信息会直接指向产生抖动的代码位置。

Allocation Tracking 有两种模式：Full 和 Sampled。Full 模式记录所有分配事件，数据完整但开销较大；Sampled 模式按间隔采样，开销更低但可能遗漏。对于内存抖动这种"大量重复分配"的场景，Sampled 模式通常就足够了——因为抖动的来源是高频重复的模式，采样不会错过它。

如果 App 包含 Native 代码（C/C++），还可以使用 Native Allocation Tracking 来追踪 `malloc()`/`new` 的分配情况。这在分析 Native 层的内存增长问题时非常有用。[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

## 各 Profiler 模式的性能开销与适用场景

理解每种分析模式的开销，是正确使用 Profiler 的核心前提。一个引入了 10 倍开销的工具，它给出的数据本身就是失真的——如果不知道这一点，就会在错误的方向上浪费时间。

CPU 的三种模式已经按 System Trace、Callstack Sample、Java Method Trace 分开说明。

Memory 方面也有开销边界。实时内存曲线的监控开销很低，可以长期开启。Heap Dump 会触发一次 stop-the-world 暂停，时间取决于堆的大小——对于几百 MB 的堆，暂停可能达到几百毫秒。Allocation Tracking 的 Full 模式在对象分配密集的场景下会有明显的性能影响，建议优先使用 Sampled 模式。

一个重要的实践建议是：使用 `profileable` 构建类型（而非 `debuggable`）来 profiling。从 Android 10（API 29）开始，Android 支持 `profileable` 标志，它允许 Profiler 进行基本的性能分析，同时避开 debug 构建中的额外检查和 hook，profiling 数据也更接近真实发布版本的表现。

两种构建类型的能力边界：

| 能力 | `profileable` | `debuggable` |
|------|:---:|:---:|
| System Trace / CPU Trace | ✅ | ✅ |
| Callstack Sample | ✅ | ✅ |
| Java Method Trace | [待验证: 依 Android Studio / 平台版本确认] | ✅ |
| Java/Kotlin Allocation Recording | ❌ | ✅ |
| Heap Dump | ❌ | ✅ |
| Native Allocation Tracking | ✅ | ✅ |

需要 Heap Dump 或 Java/Kotlin Allocation Recording 时，仍然要使用 `debuggable` 构建。

在 Android Studio 中，可以通过在 Manifest 中添加 `<profileable android:shell="true"/>` 来启用。推荐在 release 构建的基础上加上 `profileable` 标志来做性能分析，这样得到的数据最有参考价值。

[已验证: 官方文档, developer.android.com/topic/performance/tracing/on-device]

## Profiler 与 Perfetto 的互补关系

Perfetto（第 13 章）在全书工具篇中篇幅最大，但 Android Studio Profiler 与它并非替代关系——两者覆盖不同的分析场景。

Profiler 的优势在于"App 开发者的日常工具"。它集成在 IDE 中，不需要额外安装，不需要命令行操作，点击几下就能开始分析。它的时间轴和源码编辑器在同一个窗口中，发现一个耗时方法后可以直接跳转到对应的代码文件。对于 App 开发者来说，这种"在开发流程中随时可以用的工具"才是最高频使用的。

Perfetto 的优势在于"系统级全局视野"。它能同时展示多个进程、CPU 所有核心的调度情况、内核事件、SurfaceFlinger 的合成过程——这些是 Profiler 看不到的。当怀疑性能问题的根源不在 App 自身，而在系统调度、其他进程的干扰、或者 GPU 合成过程时，Perfetto 是唯一能给出答案的工具。

[图：Profiler 与 Perfetto 的定位对比——Profiler 关注单个 App 的 CPU/内存/网络/功耗，Perfetto 关注整个系统的全局状态]

Profiler 的 System Trace 模式底层就是 Perfetto。在 Profiler 中抓取的 System Trace 可以导出为 `.perfetto-trace` 文件，直接在 Perfetto UI 中打开。在 Profiler 中完成第一轮快速分析、定位大致问题范围后，导出 Trace 到 Perfetto UI 做系统级深入分析——这个工作流在实践中非常高效。

实操中更稳的顺序是：先用 Profiler 的 System Trace 做快速扫描，判断问题在 App 内部还是外部。内部问题（某个方法慢、内存持续增长）直接在 Profiler 中切换到 Callstack Sample 或 Memory Profiler 做精细分析；外部问题（CPU 被其他进程抢占、VSync 信号延迟、SurfaceFlinger 合成慢）导出 Trace 到 Perfetto UI 做系统级分析。

## Power Profiler（Android Studio Hedgehog+）

从 Android Studio Hedgehog（2023.1）开始，原来的 Energy Profiler 升级为 Power Profiler。两者的核心区别是：Energy Profiler 只能估算功耗（基于 CPU 使用率、网络活动等的模型推算），而 Power Profiler 能直接测量设备各子系统的实际功耗。

Power Profiler 的数据来源是设备上的 ODPM（On-Device Power Rails Monitor），它把设备级功耗按子系统分割成多条 Power Rail：CPU 大核、中核、小核、GPU、Display、Camera、Cellular、WLAN、GPS、UFS（存储）、Memory 等。它适合把 App 操作时间窗与设备功耗变化做相关分析，但 ODPM 不是 app-specific 归因数据，其他活跃进程也可能贡献噪声。

举个例子：如果在 Power Profiler 中看到 Cellular 的 Power Rail 在 App 启动后持续高消耗，就可以推断出启动期间的网络请求过于密集，可能需要延迟或者合并请求。

Power Profiler 的设备要求比较严格：目前只有 Pixel 6 及以后的 Pixel 设备、且系统为 Android 10（API 29）及以上才支持 ODPM 数据。其他设备只能使用传统的 Coulomb Counter 数据，粒度要粗得多。[已验证: 官方文档, developer.android.com/studio/profile/power-profiler]

## 使用 Profiler API 在代码中触发 profiling

在某些场景下，profiling 需要由特定条件自动触发。Android 15（API 35）引入了 `ProfilingManager` 的基础能力，Android 16（API 36）扩展了可用的触发器类型。

`ProfilingManager` 允许 App 注册系统级的 profiling 触发器。Android 16 API 36 中公开的触发器类型包括：

- `ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN`：cold start 中 `Activity.reportFullyDrawn()` 被调用后触发，系统提供 running system trace snapshot
- `ProfilingTrigger.TRIGGER_TYPE_ANR`：发生 ANR 时触发

注册使用 `addProfilingTriggers()` 方法提交触发器列表，结果通过 `registerForAllProfilingResults(Executor, Consumer)` 回调接收（需先注册回调再添加触发器）。注册示例：

```kotlin
val profilingManager = getSystemService(ProfilingManager::class.java)
val mainExecutor: Executor = Executors.newSingleThreadExecutor()

// 先注册结果回调，再注册触发器
profilingManager.registerForAllProfilingResults(mainExecutor) { result ->
    if (result.errorCode == ProfilingResult.ERROR_NONE) {
        // 通过 result.resultFilePath 获取 trace 文件路径
    }
}
profilingManager.addProfilingTriggers(
    listOf(
        // Builder 构造器直接接收触发器类型，不是 .setTriggerType()
        ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_APP_FULLY_DRAWN)
            .setRateLimitingPeriodHours(1)
            .build(),
        ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
            .setRateLimitingPeriodHours(1)
            .build()
    )
)
```

[已验证: Android 16 API 36, android.os.ProfilingManager — addProfilingTriggers / registerForAllProfilingResults]

这种系统触发的 profiling 方式对于捕获难以复现的问题特别有价值——很多 ANR 问题在手动测试中很难复现，但在线上用户的环境中时有发生。通过 ProfilingManager 注册触发器，可以在问题发生时自动收集数据，无需用户干预。

## 常见问题与误区

**"Method Trace 报告的方法耗时就是真实的耗时。"** 不是。Method Trace 的插桩开销非常大，对于短方法（< 10ms）可能导致耗时膨胀 10 倍以上。只有 System Trace 给出的时间数据接近真实情况。Method Trace 的价值在于看调用关系，不是看绝对时间。

**"Profileable 构建不能做性能分析。"** 不是。Google 官方推荐使用 profileable 构建来做性能分析。它比 debuggable 构建更接近真实发布版。限制是 profileable 构建不能做 Java/Kotlin Allocation Recording 和 Heap Dump；Java Method Trace 需按 Android Studio / 平台版本复核。System Trace、Callstack Sample 和 Native Allocation Tracking 都支持。需要这些高级内存分析能力时切换到 debuggable 构建。

**"Profiler 能分析系统性能问题。"** Profiler 的视角是 App-centric 的，它主要展示单个 App 的 CPU、内存、网络数据。要分析系统级的性能问题（如调度延迟、多进程竞争、SurfaceFlinger 合成慢），需要使用 Perfetto 的全局视图。

**"Memory Profiler 发现不了的问题就不是内存问题。"** Memory Profiler 能检测 Java 堆上的泄漏，但 Native 内存泄漏（通过 `malloc` 分配但未释放的内存）需要使用 Native Allocation Tracking 或者 `heapprofd`（Perfetto 的原生内存分析工具，见 §13.5）来排查。

**"CPU Profiler 的三种模式可以随便选。"** 选错模式会导致数据完全不可用。在需要"真实性能数据"的场景下用 Method Trace，或者在高频调用的方法上用 Callstack Sample 期望看到精确耗时，都会得到误导性的结果。

## 参考资料

- Android Studio Panda 1 正式版: [juejin.cn](https://juejin.cn/post/7605097326727266350) — 内置 JDK 管理和新的内存泄漏检测工具

- Android Studio Profiler 官方文档: [developer.android.com/studio/profile](https://developer.android.com/studio/profile)
- CPU Profiler 使用指南: [developer.android.com/studio/profile/cpu-profiler](https://developer.android.com/studio/profile/cpu-profiler)
- Memory Profiler 使用指南: [developer.android.com/studio/profile/memory-profiler](https://developer.android.com/studio/profile/memory-profiler)
- Power Profiler 介绍: [developer.android.com/studio/profile/power-profiler](https://developer.android.com/studio/profile/power-profiler)
- ProfilingManager (Android 16): [developer.android.com/reference/android/os/ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- 高爷博客 - CPU Profiler 系统性能分析工具的使用: [androidperformance.com](https://www.androidperformance.com/)
- Paulina Sadowska, "Can you trust time measurements in Profiler?": [proandroiddev.com](https://proandroiddev.com/can-you-trust-time-measurements-in-profiler-5b3566a55e0c)
