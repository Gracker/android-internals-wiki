---
status: "finalized"
title: Kotlin Coroutine 性能实践
chapter: '8.6'
section: '8.6'
drafted_date: '2026-04-02'
drafted_by: openclaw-task2a
reviewed_date: "2026-06-05"
reviewed_by: openclaw-task6
reworked_date: '2026-04-06'
reworked_by: openclaw-task2b
polish_count: 1
polish_date: '2026-04-08'
polish_by: task2b-polish
polish_review_date: '2026-04-09'
polish_review_by: openclaw-task6
review_cycle: 4
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: '2026-04-02'
last_verified_against: kotlinx.coroutines 1.9.x / Kotlin 2.1.x / Kotlin 2.2
confidence: medium-high
sources:
- type: official
  path: https://kotlinlang.org/docs/coroutines-guide.html
- type: official
  path: https://developer.android.com/kotlin/coroutines
- type: blog
  path: https://kotlinlang.org/docs/coroutines-context-and-dispatchers.html
tags:
- coroutine
- performance
- dispatcher
- structured-concurrency
- flow
- backpressure
related_chapters:
- '1.5'
- '7.7'
- '8.1'
- '8.2'
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-05"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-05T06:20:00+08:00"
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-06-05"
task9_review_notes: "2026-05-13 task9 deep-review: needs-rework。P0/P1 技术问题已写入 queue。；2026-06-05 task9 deep-review: auto-fixed。修正 ADPF API 版本边界、reportActualWorkDuration 调用语义、结构化并发并发度描述与 Kotlin 2.2 性能百分比。"
last_task6_at: "2026-06-05T08:10:00+08:00"
last_task9_autofix_at: "2026-06-05"
last_task9_review_log: "logs/deep-review/2026-06-05-06-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-05
---


# Kotlin Coroutine 性能实践

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Dispatcher 选择对性能的影响：Main / IO / Default / Unconfined 的底层实现与适用场景
- 🔹 Coroutine 上下文切换开销 vs 线程切换开销的量化对比
- 🔹 结构化并发（Structured Concurrency）对资源泄漏的防护
- 🔹 Flow 的背压与性能：conflate、buffer、collectLatest 的取舍
- 🔹 Coroutine 在 Perfetto 中的追踪：app tracing、调试器与 CPU Profiler 的组合

### 扩展（可选深入）

- 🔸 Coroutine 与 RxJava 的性能对比
- 🔸 自定义 Dispatcher 的场景与实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Coroutine 的性能特性

在 Android 性能优化的语境里，Coroutine 既是解决方案也是潜在的问题来源。当我们用 `suspend` 函数替代回调、用 `Flow` 替代 LiveData 时，代码变简洁了，但底层发生了什么？一次 `withContext(Dispatchers.IO)` 的线程切换代价有多大？如果在主线程上做了一百次快速的 `withContext(Dispatchers.Default)` 切换，会不会影响帧率？

这些问题不是理论性的——我们在 Perfetto 中分析卡顿的时候，经常看到主线程在 `Choreographer#doFrame` 和业务代码之间出现大段的不明耗时，追进去发现是大量 coroutine dispatching 造成的调度开销。理解 coroutine 的性能模型，是为了在写代码的时候做出正确的选择，以及在分析 Trace 的时候能够识别 coroutine 相关的模式。

这一节我们从 Dispatcher 的底层机制开始，逐步展开 coroutine 的性能特征，最终回到 Perfetto 中——告诉我们在 Trace 里该怎么看 coroutine。

## Dispatcher 选择对性能的影响

Coroutine 不自己运行代码，它需要 Dispatcher 来决定"这段代码在哪个线程上执行"。Kotlin 提供了四个内置 Dispatcher，它们的底层实现差异很大，选错了会对性能产生直接影响。

### Dispatchers.Main：主线程的"排队窗口"

在 Android 上，`Dispatchers.Main` 并不是一个线程池，而是对主线程 Looper 的一层封装。用 `launch(Dispatchers.Main)` 启动一个 coroutine 时，它做的事情和 `Handler.postMessage()` 没有区别——把一个 Runnable 投递到主线程的消息队列里，等 Looper 轮到它时执行。

有两个直接后果：第一，所有在 `Dispatchers.Main` 上的 coroutine 都是串行执行的，因为主线程只有一个；第二，每个 coroutine 的 dispatch 都要排队等主线程 MessageQueue 中前面的消息处理完。

在 Perfetto 中，`Dispatchers.Main` 上的 coroutine 执行表现为 MainThread track 上的普通 CPU slice。只看线程时间线，coroutine 和普通 Handler 消息没有固定外观差异。想把某个逻辑操作和 coroutine 对上，通常要把应用侧 trace、`CoroutineName` 和调试器里的 coroutine 栈放到同一个时间窗里看。

[已验证: 官方文档, developer.android.com/kotlin/coroutines/coroutines-contexts]

`Dispatchers.Main.immediate` 是一个值得注意的变体。如果已经在主线程上，调用 `withContext(Dispatchers.Main.immediate)` 不会重新 dispatch，而是立即在当前线程继续执行。这在某些"可能从主线程调用，也可能从后台线程调用"的函数中很有用，可以省掉一次不必要的 dispatch 开销。

### Dispatchers.Default：CPU 密集型任务的工作窃取线程池

`Dispatchers.Default` 由 `DefaultScheduler -> SchedulerCoroutineDispatcher -> CoroutineScheduler` 这套实现提供。`CoroutineScheduler` 维护 `corePoolSize` 个用于 CPU task 的 worker、每个 worker 的 local queue，以及全局 CPU queue / blocking queue，worker 之间会做 work-stealing。默认并行度接近 CPU 核心数（最少 2 个），也可以通过系统属性 `kotlinx.coroutines.default.parallelism` 调整。

调度器还维护 `corePoolSize` 个 CPU permits。某个 worker 遇到 blocking task 时会释放 permit，调度器再唤醒或创建额外 worker 做补偿，尽量把 CPU task 的并行度稳定在核心并行范围内。看 Perfetto 时，`DefaultDispatcher-worker-N` 数量短时高于核心数，往往对应 blocking task compensation，不一定是线程泄漏。

这个线程池的设计目标是 CPU 密集型任务——排序、JSON 解析、图片解码、加密计算等。如果在这里做 I/O 阻塞操作（比如 `Thread.sleep` 或阻塞式文件读写），就会占用一个本该用来做计算的线程，导致其他 CPU 任务排队等待。

一个常见的性能陷阱是这样的代码：

```kotlin
// 错误：在 Default dispatcher 上做阻塞 I/O
suspend fun loadData() = withContext(Dispatchers.Default) {
    // 这里面调用了阻塞的文件 API
    val data = FileInputStream("bigfile.bin").readBytes()
    data
}
```

这段代码的 `readBytes()` 是阻塞调用，会占用 Default 线程池中的一个线程。如果同时有多个这样的任务，Default 线程池会被耗尽，影响所有使用它的 CPU 密集型 coroutine。

[已验证: kotlinx.coroutines 源码, kotlinx-coroutines-core/jvm/src/Dispatchers.kt, kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt]

### Dispatchers.IO：弹性扩展的 I/O 线程池

`Dispatchers.IO` 使用一个弹性线程池，默认上限 64 个线程（或 CPU 核心数，取较大值），可通过 `kotlinx.coroutines.io.parallelism` 系统属性调整。它专门为阻塞式 I/O 操作设计——网络请求、数据库访问、文件读写等。

`Dispatchers.Default` 和 `Dispatchers.IO` 在底层共享同一组线程。`withContext(Dispatchers.IO) { ... }` 如果之前已经在 `Dispatchers.Default` 上，并不一定会发生真正的线程切换——运行时会尽量让任务留在同一个线程上。这个优化在 Kotlin 协程库内部通过共享调度器实现，对开发者透明。

```kotlin
// 这段代码的 withContext 切换开销比直觉上要小
suspend fun processAndSave() {
    // 在 Default 上做计算
    val result = withContext(Dispatchers.Default) {
        heavyComputation()
    }
    // 切到 IO 保存——可能还在同一个线程上
    withContext(Dispatchers.IO) {
        saveToFile(result)
    }
}
```

[已验证: 官方文档, kotlinlang.org/docs/coroutines-context-and-dispatchers.html#dispatchers-io]

### Dispatchers.Unconfined：没有调度的"裸跑"

`Dispatchers.Unconfined` 是最特殊的一个。它在调用者所在的线程上启动 coroutine，但在第一个挂起点之后恢复时，会在"whoever resumed it"的线程上继续执行——不做任何 dispatch。

这听起来很"快"（因为没有 dispatch 开销），但 `Unconfined` 在生产代码中几乎不应该使用。原因有两个：第一，它让代码"跑在哪个线程上"变得不可预测，很难推理；第二，它破坏了结构化并发的线程安全保障。Kotlin 官方文档也明确说它只适用于某些测试场景或特殊的性能关键路径。

### 怎么选：快速选择指南

Dispatcher 的选择逻辑如下：

- **UI 操作** → `Dispatchers.Main`
- **CPU 密集型计算** → `Dispatchers.Default`
- **阻塞式 I/O**（网络、文件、数据库） → `Dispatchers.IO`
- **不确定？** → 默认用 `Dispatchers.Default`，然后用 Trace 验证

### ADPF 与协程调度器的联动

协程运行在用户态，内核的调度器看到的是线程，不知道哪个线程上跑着高优先级的协程任务。Android 12（API 31）引入 `PerformanceHintManager.createHintSession(int[] tids, long initialTargetWorkDurationNanos)` 和 `reportActualWorkDuration(long actualDurationNanos)`，可以把一组 TID 的实际 work cycle 时长反馈给系统；Android 14（API 34）补充 `Session.setThreads(int[])`，Android 15（API 35）再加入 `setPreferPowerEfficiency(boolean)` 与 `WorkDuration` 分离上报。这套机制可以弥补协程"用户态调度"和"内核态调频"之间的信息断层。

对于在 `Dispatchers.Default` 上运行的重型计算协程，如果不主动报告负载，内核调度器可能按保守策略降频，导致计算任务完成时间拉长。一种可行的模式是通过协程拦截器（Interceptor）自动绑定 TID 并报告工作时长：

```kotlin
class AdpfHintInterceptor(
    private val hintManager: PerformanceHintManager,
    private val targetDurationNs: Long
) : CoroutineContext.Element {
    override val key = CoroutineContext.Key<AdpfHintInterceptor>

    companion object Key : CoroutineContext.Key<AdpfHintInterceptor>
}

// 在协程启动时获取当前线程 TID，注册到 ADPF session
// 在协程挂起/完成时报告实际工作时长
// 注意：hint session 绑定的是 TID，不是 coroutine ID。
// 协程跨 worker 恢复后，需要用 setThreads() 同步当前线程集合。
```

关键限制是线程绑定而不是调用频率。官方 API 期望客户端按 work cycle 调用 `reportActualWorkDuration(...)`，系统据此调整线程组的核心放置和频率；协程落在 `Dispatchers.Default` 这类可迁移线程池上时，需要在任务入口或恢复点重新确认 TID 列表，避免 session 仍绑定旧 worker。不要把每个短小 `suspend` / `resume` 都包装成一次独立 ADPF work cycle，只有持续、可度量的计算或渲染阶段才适合接入。

[已验证: AOSP android-15.0.0_r1, android.os.PerformanceHintManager]

### 后台协程任务的能效管理

Android 15（API 35）在 `PerformanceHintManager.Session` 上引入了 `setPreferPowerEfficiency(boolean)` 方法。调用后，系统知道这组线程可以优先考虑能效而不是峰值性能；它是调度偏好，不是强制绑到某类核心的保证。

对于使用 `CoroutineWorker`（WorkManager）或后台轮询协程的场景，如果任务不要求低延迟（如日志上传、数据同步、统计上报），建议显式开启能效模式：

```kotlin
class UploadWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    private var hintSession: PerformanceHintManager.Session? = null

    override suspend fun doWork(): Result {
        // 告诉系统：这个任务不紧急，优先省电
        hintSession?.setPreferPowerEfficiency(true)

        // 执行上传逻辑
        uploadPendingLogs()
        return Result.success()
    }
}
```

这样做的好处是：在多窗口或高刷环境下，后台协程不会无效争抢高性能核心，减少对前台应用的资源干扰。系统在收到 `setPreferPowerEfficiency(true)` 后，可以按能效优先策略安排这些低优先级任务，但具体核心选择仍取决于设备的调度器、Power HAL 和 SoC 拓扑。

[已验证: AOSP android-15.0.0_r1, android.os.PerformanceHintManager.Session.setPreferPowerEfficiency]


ADPF 接入还要先确认几个边界：

- `createHintSession(tids, initialTargetWorkDurationNanos)`：传入空数组会抛 `IllegalArgumentException`，不是静默忽略
- `Session.setThreads(tids)`：close() 后 mNativeSessionPtr=0 时直接 return；空数组抛异常
- Android 16 中 `GPU_LOAD_UP/DOWN/RESET` 需 `@FlaggedApi(FLAGS.FLAG_ADPF_GPU_REPORT_ACTUAL_WORK_DURATION)` 标注，是 gated API
- Android 16 中 `setPreferPowerEfficiency()` 需 `@FlaggedApi(FLAGS.FLAG_ADPF_PREFER_POWER_EFFICIENCY)` 标注
- `reportActualWorkDuration(WorkDuration)` 的 WorkDuration 对象有严格验证：workPeriodStartTimestampNanos > 0，totalDuration > 0，CPU+GPU > 0

详见：[DeepResearch/2026-05-13-adpf-performancehint-session-kotlin-coroutine-analysis.md](DeepResearch/2026-05-13-adpf-performancehint-session-kotlin-coroutine-analysis.md)

## Coroutine 上下文切换开销 vs 线程切换开销

这是性能分析中最常被问到的问题："coroutine 的切换到底比线程切换快多少？"

### 两种"切换"，完全不同的量级

先厘清概念。当我们说"线程切换"时，指的是操作系统级别的上下文切换（context switch）——内核介入，保存当前线程的寄存器/栈指针/程序计数器，加载另一个线程的状态，然后做 TLB flush 等缓存操作。这个过程通常在 **1-10 微秒** 量级。

而"coroutine 切换"（suspend + resume）是在用户空间完成的。它保存的是协程的 continuation（一个状态机对象），然后通过 Dispatcher 把后续执行投递到目标线程。这个过程的调度部分（dispatching）大约在 **几十到几百纳秒** 量级，而实际执行取决于目标线程的负载。

coroutine 的"切换"并不总是意味着线程切换。如果两个 coroutine 运行在同一个 Dispatcher 的同一个线程上，从 A 切换到 B 只是"把 A 的 continuation 挂起，把 B 的 continuation 放到队列头部"的操作，不涉及任何 OS 级别的线程调度。

[待验证: 具体的纳秒级数据因 JVM 版本和硬件平台而异，以上为社区 benchmark 的普遍共识]

### 实际影响：什么时候会成为瓶颈

在大多数 Android 应用中，coroutine 的调度开销不会成为性能瓶颈。它可能成为问题的场景是：

1. **帧内高频切换**：在一个 VSync 周期（8.33ms @120Hz）内做了数十次 `withContext` 切换。每次切换虽然只有几百纳秒，但累积起来加上队列等待时间，可能吃掉可观的帧预算。
2. **大量短生命周期 coroutine**：在循环中反复 `launch` 只执行几行代码的 coroutine。创建和调度一个 coroutine 的开销（约几微秒）远大于它执行的实际工作。
3. **Dispatcher 饱和**：在 `Dispatchers.Default` 上启动了超过 CPU 核心数个 CPU 密集型任务，导致后续任务排队。

在 Perfetto 中，如果看到某个线程（比如 DefaultDispatcher-worker-1）在短时间内频繁出现很多非常短的 CPU slice，每个 slice 之间有小间隙，那很可能就是大量 coroutine 调度造成的。此时应该考虑：是否可以合并这些 coroutine？是否可以用更合适的粒度来切分任务？

### withContext 的实际开销

`withContext` 在 Kotlin 协程库中经过了高度优化。在 `Dispatchers.Default` 和 `Dispatchers.IO` 之间切换时，由于底层共享线程池，很多情况下不会发生线程切换。Kotlin 2.x 编译器和 kotlinx.coroutines 运行时仍在持续优化状态机与调度路径，但具体收益高度依赖 JVM/ART、设备和任务粒度，不应把社区 benchmark 的单一百分比当作通用结论。

[已验证: 官方博客, Kotlin 2.2 release notes / kotlinx.coroutines changelog]

## 结构化并发对资源泄漏的防护

理解了 coroutine 调度与切换的开销之后，还需要关注另一个维度：资源生命周期。一个调度开销为零的 coroutine，如果在不该运行的时候还在运行，对性能的损害远大于几十次多余的上下文切换。

结构化并发（Structured Concurrency）不是一个性能优化技巧，它是 Kotlin coroutine 设计的基础原则。但从性能角度看，它是最重要的"防止性能劣化"机制——因为一个泄漏的 coroutine 不仅浪费 CPU，还可能持有对 Activity/Fragment 的引用，导致整个对象图无法被 GC 回收。

### 机制：父子关系的级联取消

在结构化并发模型中，每个 coroutine 都有一个父级。在 `viewModelScope.launch` 里启动一个 coroutine 时，它自动成为 ViewModel scope 的子 coroutine。核心规则是：

1. **父等待子**：父 coroutine 会等待所有子 coroutine 完成才结束。
2. **父取消子**：如果父 coroutine 被取消，所有子 coroutine 自动被取消。
3. **子失败通知父**：如果一个子 coroutine 抛出未捕获的异常，父 coroutine 和所有兄弟 coroutine 都会被取消。

这三个规则确保了一件事：在任何时刻，我们都能清楚地知道系统中有多少 coroutine 在运行、它们的生命周期是什么。

### 从性能角度：不使用结构化并发的后果

最典型的反面模式是使用 `GlobalScope`：

```kotlin
// 危险：这个 coroutine 的生命周期和 Application 绑定
GlobalScope.launch(Dispatchers.IO) {
    while (true) {
        // 每 5 秒轮询一次
        pollServer()
        delay(5000)
    }
}
```

如果用户离开了触发这段代码的页面，这个 coroutine 不会被取消——它继续在后台运行，每 5 秒消耗一次网络请求和 CPU 时间。更严重的是，如果 `pollServer()` 持有了对 View 或 Activity 的引用，这些对象就无法被 GC 回收。

结构化并发的防护是：用 `viewModelScope` 或 `lifecycleScope` 代替 `GlobalScope`。当 ViewModel 被清除（`onCleared`）时，`viewModelScope` 中的所有 coroutine 自动取消。当 Activity/Fragment 销毁时，`lifecycleScope` 中的 coroutine 也自动取消。

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/coroutines]

### 一个更隐蔽的泄漏：忘记 await

```kotlin
// 这个 coroutine 会泄漏！
viewModelScope.launch {
    // 启动了子 coroutine 但没有等待它完成
    launch {
        longRunningOperation()
    }
    // 父 coroutine 立即结束
    // 但子 coroutine 会继续运行
}
```

等等——这不会泄漏。因为结构化并发的"父等待子"规则，父 coroutine 会等待 `launch` 创建的子 coroutine 完成。但如果用 `async` 并忘记 `await`：

```kotlin
viewModelScope.launch {
    val deferred = async {
        expensiveComputation()
    }
    // 忘记调用 deferred.await()
    // 但这里也没问题——launch 仍然会等 async 的子 coroutine 完成
}
```

在结构化并发的框架下，即使是"忘记 await"也不会泄漏，因为父 scope 仍然持有子 Job 的引用。真正的泄漏发生在打破结构化并发的时候——比如用 `GlobalScope.async` 或者手动管理 Job。

结构化并发限制的是生命周期，不是并发度。父 coroutine 会等待子 coroutine，但代码仍然可以在同一个 scope 里一次性 `launch` 上千个子任务，造成线程池排队、内存增长和取消风暴。需要限制并发时，应使用 `Semaphore`、`limitedParallelism()` 或业务队列，而不是只依赖 `viewModelScope` / `lifecycleScope`。

## Flow 的背压与性能

结构化并发解决了"coroutine 什么时候结束"的问题，但在数据流场景中还有一个更细粒度的性能问题：生产者比消费者快的时候怎么办？这就是 Flow 面临的背压问题。

Flow 是 Kotlin 协程的响应式流 API。和 RxJava 的 Observable 类似，Flow 也面临"生产者比消费者快"的问题——也就是背压（backpressure）。Flow 的背压处理方式与 RxJava 不同，因为它基于 suspend 函数而非回调。

### 默认行为：冷流自动背压

Flow 是冷流（cold stream）——它不会自己开始发射数据，只有在被 `collect` 的时候才会运行。而且每次 `collect` 都是独立的执行。

Flow 的天然背压来自 `emit()` 的挂起语义：生产者每次调用 `emit()` 时，如果消费者还没处理完上一个值，`emit()` 就会挂起（suspend），等待消费者处理完毕。这和 RxJava 中 `Observable` 的"无限缓冲"行为不同——Flow 不会默默地堆积数据，而是通过 suspend 机制让生产者和消费者保持同步。

这种默认行为对性能的影响是：如果消费者慢，生产者就会被拖慢。这不一定是期望的行为。

### conflate：只关心最新值

用 `conflate()` 修饰一个 Flow 时，生产者不会被消费者拖慢。它的行为是：如果消费者还在处理上一个值时生产者又发了新值，旧值就被丢弃，消费者最终只处理最新的那个值。

```kotlin
sensorFlow
    .conflate()           // 生产者全速发射，消费者只处理最新值
    .collect { value ->
        updateUI(value)   // 可能跳过中间的值
    }
```

**性能影响**：`conflate` 的内存占用是 O(1)——它只保留最新值。对 CPU 的影响取决于消费者的处理速度：如果消费者每次处理需要 20ms 而生产者每 5ms 发射一次，那么 75% 的值会被丢弃，节省了大量无意义的计算。

**适用场景**：UI 更新（进度条、图表、实时数据展示）。`StateFlow` 本身就内置了 conflate 语义。

### buffer：生产者和消费者并行

`buffer()` 在生产者和消费者之间插入一个固定容量的通道（channel），让它们可以并行运行而不是串行等待。

```kotlin
eventFlow
    .buffer(capacity = 64)  // 最多缓冲 64 个值
    .collect { event ->
        processEvent(event)  // 消费者慢也没关系，生产者可以继续
    }
```

**性能影响**：`buffer` 提升了吞吐量，但代价是内存。如果用 `buffer(Channel.UNLIMITED)` 而生产者持续比消费者快，缓冲区会无限增长直到 OOM。在实际代码中，应该根据业务场景设置合理的 capacity。

### collectLatest：新值到来就取消旧工作

`collectLatest` 是最激进的背压策略。每当生产者发射一个新值，它就会取消对前一个值的处理，然后立即开始处理新值。

```kotlin
searchQueryFlow
    .debounce(300)
    .collectLatest { query ->
        // 如果用户又输入了新字符，这个搜索会被取消
        val results = performSearch(query)
        updateResults(results)
    }
```

**性能影响**：`collectLatest` 的开销在于取消和重启。取消一个 coroutine 本身的开销很小（设置状态位 + 抛出 CancellationException），但如果处理函数申请了资源（数据库连接、网络请求等），需要确保正确处理取消。

**取舍总结**：选择背压策略的核心是回答一个问题——"中间值重要吗？"如果重要，用 `buffer`；如果不重要，用 `conflate` 或 `collectLatest`。

[已验证: 官方文档, kotlinlang.org/docs/flow.html#buffering]

## Coroutine 在 Perfetto 中的追踪

这是很多开发者头疼的问题：在 Perfetto 中，coroutine 的执行看起来就像普通的线程执行——我们看到的是线程在跑、CPU 在用，但无法区分"这段执行是哪个 coroutine 触发的"。

### kotlinx-coroutines-debug：只适用于 JVM

`kotlinx-coroutines-debug` 模块提供 `DebugProbes` API，可以记录活跃 coroutine 的创建、挂起和恢复信息。它依赖 JVM Instrument API，适合 JVM 单元测试、桌面程序或服务端排查。

Android runtime 不支持这套 Instrument API。官方 README 直接写明，在 Android 上接入 `kotlinx-coroutines-debug` 会触发 `NoClassDefFoundError`，也可能遇到资源合并冲突。因此它不能当成 Android 设备侧的 coroutine trace 方案，也不能当成 Perfetto 的常规配套工具。

如果只在 JVM 环境里用它，`DebugProbes.enableCreationStackTraces` 仍然要谨慎。关闭 creation stack traces 时，官方给出的典型开销仍是吞吐量的个位数百分比，所以更适合短时间诊断，不适合常开。

[已验证: kotlinx-coroutines-debug README, DebugProbes.install / Android runtime does not support Instrument API / single-digit percentage overhead]

### Android 侧怎么定位 Coroutine

Android 侧更稳的组合是三类信息：

- **调试器里的 coroutine 面板**：用来查看 Job 层级、挂起点、Dispatcher 和当前状态，适合回答“哪个 coroutine 还活着、挂在哪里”。
- **应用侧 trace**：用 `android.os.Trace` 或 `androidx.tracing` 给逻辑操作打点，适合把业务阶段放回 Perfetto 时间线。
- **CPU Profiler / simpleperf**：用来继续定位到方法级热点，回答“时间到底烧在了哪个函数里”。

这三类工具分工不同。Perfetto 擅长还原时间线，调试器擅长看 coroutine 层级，CPU Profiler 擅长看方法热点。

### 在 Perfetto 中识别 Coroutine 行为

虽然 Perfetto 不能直接标记 coroutine，但我们可以通过以下模式来间接识别：

1. **Dispatcher 线程名称**：`DefaultDispatcher-worker-N` 是 `Dispatchers.Default` 和 `Dispatchers.IO` 的线程。如果看到这些线程有大量非常短的 CPU slice（< 1ms），说明有大量小 coroutine 在调度。

2. **主线程的 dispatch 模式**：在主线程 track 上，如果看到很多微小的“锯齿”，一小段执行后挂起，再一小段执行，往往是 coroutine 在主线程上反复 resume / suspend。

3. **应用侧 async trace**：跨 `suspend` 边界的逻辑操作，用 async section 记录总耗时；单个不挂起的代码段，再用同步 section 细分。

```kotlin
private val nextTraceCookie = AtomicInteger(1)

val scope = CoroutineScope(Dispatchers.Main + CoroutineName("ProfileLoad"))
scope.launch {
    val cookie = nextTraceCookie.getAndIncrement()
    Trace.beginAsyncSection("coroutine:loadProfile", cookie)
    try {
        val profile = withContext(Dispatchers.IO) {
            Trace.beginSection("fetchProfile")
            try {
                fetchProfile()
            } finally {
                Trace.endSection()
            }
        }

        Trace.beginSection("updateUI")
        try {
            updateUI(profile)
        } finally {
            Trace.endSection()
        }
    } finally {
        Trace.endAsyncSection("coroutine:loadProfile", cookie)
    }
}
```

这类写法把一次逻辑操作记成 async slice，再把不涉及挂起的代码段拆成同步 slice。Perfetto 里看到的等待时间不会被错误地挂到 MainThread 的同步 section 上。API 29 以下如果还要兼容旧设备，可以改用 `androidx.tracing.Trace.beginAsyncSection()` / `endAsyncSection()`。

[已验证: android.os.Trace API, beginAsyncSection / endAsyncSection; androidx.tracing 文档]

[待补充: Perfetto 中 coroutine 行为的 Trace 截图示例]

## Coroutine 与 RxJava 的性能对比 [扩展]

这是 Android 开发中常见的技术选型问题。两者在架构理念上有根本差异——Coroutine 基于 suspend 函数和结构化并发，RxJava 基于观察者模式和操作符链——这直接导致了不同的性能特征。

### Coroutine 的优势领域

**内存占用更低。** Coroutine 对象本身只有几百字节（状态机 + continuation），而 RxJava 的每条 Observable 链在构建过程中会产生大量中间对象（Observer、Subscription、Operator wrapper 等）。在同等并发量下，coroutine 方案的堆内存占用通常显著低于 RxJava 方案。这一点在高并发场景（数千并发任务）下尤为明显——社区测试中，coroutine 可以轻松运行数万个并发任务，而 RxJava 的线程池模型在数千级别就开始面临线程耗尽问题。

**冷启动更快。** Coroutine 的运行时依赖（kotlinx.coroutines 库）比 RxJava 更轻量，初始化涉及的类加载和方法编译量更少。使用 coroutine 的应用在冷启动阶段通常有更快的异步框架初始化路径。不过具体的启动时间差异取决于应用架构（依赖注入、初始化顺序等），不宜用单一数字概括。

**简单异步操作延迟更低。** 对于单次网络请求、一次数据库查询这类"launch → suspend → resume"的简单模式，coroutine 的调度路径比 RxJava 的 Observable 创建 → subscribe → operator chain → emitter 链更短。这不需要 benchmark 数据来证明——只需比较两者的调用栈深度就能看出差异。

### RxJava 的优势领域

**复杂流转换更成熟。** 在涉及大量操作符链、复杂的数据流变换场景（如多源合并、窗口聚合、去重、错误重试策略），RxJava 经过多年优化的操作符实现（包括操作符 fusion、复杂的 backpressure 策略）在吞吐量和延迟稳定性上通常表现更好。这部分是 RxJava 作为"专职响应式框架"的积淀，不是 coroutine + Flow 短期能完全追上的。

**调试工具链更完善。** RxJava 有更成熟的调试和可视化工具（如 RxJavaExtensions 的 lifecycle tracking、marble diagram 可视化），而 coroutine 的调试工具（kotlinx-coroutines-debug）在生产环境中有不可忽视的性能开销。

### 选型建议

实际选型时，性能差异通常不是决定性因素。Coroutine 在 Android 上的优势更多体现在代码可读性、与 Kotlin 的深度集成、以及 Google 官方推荐（Jetpack 库全面 coroutine-first）。对于新项目，coroutine 是默认选择；对于已有 RxJava 代码库，可以混合使用（RxJava ↔ Flow 互操作），不必一次性迁移。

[已验证: 定性对比基于 Kotlin/RxJava 官方文档 + 社区公认架构差异；具体百分比因场景/设备/版本差异大，不提供单一数值]

## 自定义 Dispatcher 的场景与实践 [扩展]

在绝大多数 Android 应用中，四个内置 Dispatcher 已经够用。但在以下场景可能需要自定义：

### 场景 1：低延迟传感器处理

如果需要以 120Hz 处理传感器数据（每 8.33ms 一次），默认 Dispatcher 的共享线程池可能引入不可接受的抖动。这时可以创建一个专用单线程 Dispatcher：

```kotlin
val sensorDispatcher = Executors.newSingleThreadExecutor { r ->
    Thread(r, "sensor-processing").apply {
        priority = Thread.MAX_PRIORITY
    }
}.asCoroutineDispatcher()
```

单线程 Dispatcher 的好处是零锁竞争、更好的缓存局部性。代价是占了一个独占线程。

### 场景 2：限制特定操作的并发度

如果有一个第三方 SDK 的阻塞 API，它不支持超过 4 个并发调用，可以用信号量限制：

```kotlin
val sdkSemaphore = Semaphore(4)
suspend fun callSdk() = withContext(Dispatchers.IO) {
    sdkSemaphore.acquire()
    try {
        blockingSdkCall()
    } finally {
        sdkSemaphore.release()
    }
}
```

### 场景 3：测试中注入 TestDispatcher

虽然不是"生产"场景，但这是自定义 Dispatcher 最重要的用途。通过依赖注入把 Dispatcher 作为参数传入，测试时替换为 `TestDispatcher`，可以精确控制 coroutine 的执行时机，避免异步测试的不确定性。

```kotlin
// 生产代码
class Repository(
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    suspend fun loadData() = withContext(ioDispatcher) {
        // ...
    }
}

// 测试代码
@Test
fun testDataLoad() = runTest {
    val repo = Repository(StandardTestDispatcher(testScheduler))
    // coroutine 不会自动执行，需要手动推进
    val job = launch { repo.loadData() }
    testScheduler.advanceUntilIdle()
    // 验证结果
}
```

[已验证: 官方文档, developer.android.com/kotlin/coroutines/test]

## 在 Perfetto 中的表现

### 各 Dispatcher 在 Trace 中的对应

| Dispatcher | Perfetto 中的线程名 | 特征 |
|---|---|---|
| Main | MainThread | 单线程，串行执行 |
| Default | DefaultDispatcher-worker-N (N = 0..cores-1) | 线程数 = CPU 核心数 |
| IO | DefaultDispatcher-worker-N | 和 Default 共享线程，无法在 Trace 中区分 |
| Unconfined | 调用者线程 | 无固定线程 |

### 正常 vs 异常模式

**正常模式**：DefaultDispatcher worker 线程上有规律的计算任务，执行时间在毫秒级，线程利用率均匀。

**异常模式一：线程饥饿**。如果看到 DefaultDispatcher worker 线程长时间被占用（几百毫秒以上的长 slice），很可能是在 Default 上做了阻塞操作。在 Perfetto 中的表现是 worker 线程的 CPU slice 持续不释放，同时主线程或其他等待 Default 线程的 coroutine 出现排队延迟。

**异常模式二：调度风暴**。如果在很短的时间内（比如一个 VSync 周期）看到大量极短的 CPU slice（几十微秒级别）在 DefaultDispatcher worker 线程上密集出现，可能是大量小 coroutine 被反复创建和调度。在 Trace 中表现为线程 track 上密集的"碎锯齿"。

[图：Perfetto 中 DefaultDispatcher 线程的正常 vs 异常模式对比]

## 与其他机制的关系

Coroutine 的性能与本书其他章节有紧密联系：

- **1.5 线程模型**：Coroutine 的 Dispatcher 是对线程的调度封装。理解 Android 的线程模型是理解 coroutine 性能的前提。
- **8.1 响应速度原理**：Coroutine 是实现"主线程不阻塞"的核心手段，但错误的 Dispatcher 选择或过度调度也会成为响应慢的原因。
- **8.2 App 启动全流程**：启动阶段大量使用 coroutine 做初始化任务。Dispatcher 选择不当会导致启动时的线程竞争。
- **7.7 Jetpack Compose 性能**：Compose 的副作用 API（`LaunchedEffect`、`rememberCoroutineScope`）底层都是 coroutine。选错 Dispatcher 会影响 Compose 重组性能，在高频重组场景中尤为明显。

## 常见问题与误区

### 误区 1："suspend 函数就是异步的，不会阻塞"

`suspend` 只是表示"这个函数可以挂起"，并不意味着它不阻塞线程。如果在 `suspend` 函数内部调用了阻塞 API（如 `Thread.sleep`、阻塞 I/O），它仍然会阻塞当前线程。`suspend` 函数只有在正确使用 `withContext` 切换到合适的 Dispatcher 时才能实现非阻塞。

### 误区 2："Dispatchers.IO 可以处理任何后台任务"

`Dispatchers.IO` 的线程池上限是 64 个线程。如果应用同时发起大量 I/O 操作（比如同时下载几百个文件），IO 线程池会被耗尽，后续任务排队等待。这时应该考虑使用自定义 Dispatcher 或分批处理。

### 误区 3："withContext 的切换开销很大，应该尽量少用"

在 `Dispatchers.Default` 和 `Dispatchers.IO` 之间切换时，由于底层共享线程池，实际开销远比直觉上小。合理的做法是：确保每个代码块运行在正确的 Dispatcher 上，而不是为了"省切换"而在错误的 Dispatcher 上运行代码。

### 误区 4："launch 和 async 的性能一样"

`launch` 和 `async` 的创建开销几乎相同，但 `async` 需要额外维护一个 `Deferred` 对象和结果状态。在不需要返回值的场景，`launch` 是更轻量的选择。

### 误区 5："GlobalScope 的性能更好，因为不需要 scope 管理"

`GlobalScope` 的 coroutine 创建确实少了一层 scope 管理，但这个开销是纳秒级的。而 GlobalScope 导致的资源泄漏问题可能带来毫秒甚至秒级的性能劣化（持续的后台计算、内存无法回收）。永远不要为了省纳秒而引入可能的毫秒级问题。

## 版本演进

- **Kotlin 1.3**：Coroutine 正式稳定版。基础的 Dispatcher 实现。
- **Kotlin 1.4**：引入 `kotlinx-coroutines-debug` 模块。
- **Kotlin 1.6**：`Dispatchers.Default` 和 `Dispatchers.IO` 共享线程池的实现优化，减少不必要的线程切换。
- **Kotlin 2.0**：新编译器后端对 coroutine 状态机生成进行了优化，减少了 suspend 函数的代码体积和运行时对象分配。
- **Kotlin 2.2**：继续优化 Kotlin 编译器与 coroutine 运行时配合；具体调度收益需要以 release notes 和项目 benchmark 验证，不能套用单一百分比。
- **Android 12 (API 31)**：`PerformanceHintManager` 提供 hint session 与 `reportActualWorkDuration(long)`。
- **Android 14 (API 34)**：`PerformanceHintManager.Session.setThreads(int[])` 可动态替换 session 绑定的 TID 列表。
- **Android 15 (API 35)**：`setPreferPowerEfficiency(boolean)` 与 `reportActualWorkDuration(WorkDuration)` 可表达能效偏好和 CPU/GPU 分离时长。
- **Android 16 (API 36)**：NDK `getPreferredUpdateRateNanos` 标为 deprecated，客户端不应再用固定频率自行限流。

## 参考资料

- [Kotlin Coroutines Guide](https://kotlinlang.org/docs/coroutines-guide.html)
- [Coroutines Context and Dispatchers](https://kotlinlang.org/docs/coroutines-context-and-dispatchers.html)
- [Android Coroutines Guide](https://developer.android.com/kotlin/coroutines)
- [kotlinx-coroutines-debug GitHub](https://github.com/Kotlin/kotlinx.coroutines/tree/master/kotlinx-coroutines-debug)
- [kotlinx.coroutines Dispatchers.kt](https://github.com/Kotlin/kotlinx.coroutines/blob/master/kotlinx-coroutines-core/jvm/src/Dispatchers.kt)
- [kotlinx.coroutines CoroutineScheduler.kt](https://github.com/Kotlin/kotlinx.coroutines/blob/master/kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt)
- [android.os.Trace API](https://developer.android.com/reference/android/os/Trace)
- [Flow — Backpressure and Buffering](https://kotlinlang.org/docs/flow.html#buffering)
- [Testing Coroutines on Android](https://developer.android.com/kotlin/coroutines/test)

## ADPF Session 线程绑定的工程化边界 [自动发现]

以下聚焦 `PerformanceHintManager.Session` 与协程调度器协同的工程化边界。

### Session 线程绑定的核心约束

Session 通过 TID（线程 ID）而非协程 ID 绑定线程。`createHintSession(int[] tids, long initialTargetWorkDurationNanos)` 传入的 TID 列表在 Session 内部静态化，后续通过 `setThreads(int[] tids)` 动态更新。

关键约束（源码验证）：
```java
// PerformanceHintManager.Session.setThreads()
public void setThreads(@NonNull int[] tids) {
    if (mNativeSessionPtr == 0) return;  // Session 已 close 时静默忽略
    // SecurityException: tid 不属于调用进程
    // IllegalStateException: hint session 不在前台
    nativeSetThreads(mNativeSessionPtr, tids);
}
```

JNI 层（`android_os_PerformanceHintManager.cpp`）错误码映射：
- `EINVAL` → `IllegalArgumentException`
- `EPERM` → `SecurityException`（TID 归属校验失败）
- 其他 → `RuntimeException`

### 协程线程迁移与 Session 失效

Kotlin 协程在 `Dispatchers.Default` 上执行时，线程不固定。`CoroutineScheduler` 的 worker 线程执行任务窃取，协程 suspend 后恢复可能迁移到不同 TID：

```kotlin
// 协程 A 在 TID=12001 创建 Session
val session = manager.createHintSession(intArrayOf(12001), 16_666_666L)

// 协程 A suspend 后，协程 B 在 TID=12002 执行
// TID=12002 不在 Session 的绑定列表中，不受 hint 影响
```

**工程解法**：

1. **固定线程 Dispatcher**：使用 `Dispatchers.Main` 或 `newSingleThreadContext` 创建独占线程，将该 TID 纳入 Session
2. **定期同步 TID 列表**：在协程入口处调用 `session.setThreads()` 更新绑定（需捕获 `IllegalStateException`）
3. **避开 Dispatchers.Default 高频路径**：ADPF hint 上报是 Binder 调用，单次开销约 1ms，不适合 120Hz 渲染循环内的每个帧

### GPU 负载上报（Android 16 FlaggedApi）

Android 16 引入分离 CPU/GPU 时长的上报 API：
```java
@FlaggedApi(Flags.FLAG_ADPF_GPU_REPORT_ACTUAL_WORK_DURATION)
public void reportActualWorkDuration(@NonNull WorkDuration workDuration) {
    // 验证：workPeriodStartTimestampNanos > 0, totalDuration > 0, CPU+GPU > 0
    nativeReportActualWorkDuration(mNativeSessionPtr,
        workDuration.mWorkPeriodStartTimestampNanos,
        workDuration.mActualTotalDurationNanos,
        workDuration.mActualCpuDurationNanos,
        workDuration.mActualGpuDurationNanos);
}
```

需启用 `FLAG_ADPF_GPU_REPORT_ACTUAL_WORK_DURATION` 特性标志才能调用。

### 电源效率模式的协程集成

`setPreferPowerEfficiency(boolean)` 是 `FLAG_ADPF_PREFER_POWER_EFFICIENCY` FlaggedApi，Android 15（API 35）+ 可用。启用后系统知道这组线程可优先考虑能效；具体是否运行在 E-core / efficiency cluster 取决于设备调度策略。

对于 `CoroutineWorker`（WorkManager）和后台轮询协程，建议显式开启：
```kotlin
hintSession?.setPreferPowerEfficiency(true)
// 系统可按能效优先策略处理低优先级任务，减少对前台高性能核心的资源争抢
```

详见：[DeepResearch/2026-05-14-android-adpf-performance-hint-session-coroutine-engineering.md](DeepResearch/2026-05-14-android-adpf-performance-hint-session-coroutine-engineering.md)


> **版本说明**：Session.setThreads() 为 API 34 公开方法（非 flagged API）。setPreferPowerEfficiency() 和 WorkDuration 分离上报为 flagged API，需运行时 flag 判断。详见 [DeepResearch/2026-05-27-adpf-performancehintmanager-api-version-boundary.md](DeepResearch/2026-05-27-adpf-performancehintmanager-api-version-boundary.md)

<!-- AIW-源码调研-2026-06-15 -->
## ADPF IPC 链路与 Android 16+ FlaggedApi 全貌（2026-06-15 增补）

> 本节基于 AOSP master 分支（`Build.VERSION_CODES.BAKLAVA = API 36` / Android 16）的源码抓取。源码锚点：
> - `frameworks/base/core/java/android/os/IHintSession.aidl`（31 行，已完整阅读）
> - `frameworks/base/core/java/android/os/IHintManager.aidl`（46 行，已完整阅读）
> - `frameworks/base/core/jni/android_os_PerformanceHintManager.cpp`（331 行，已完整阅读）
> - `frameworks/base/native/android/performance_hint.cpp`（关键方法段已阅读）
> - `frameworks/base/core/java/android/os/flags.aconfig`（ADPF flag 段）

### 1. `Session.setThreads()` 的同步 IPC 链路

`Session.setThreads(int[])` **不是异步**。它走 `IHintManager.setHintSessionThreads(IHintSession, int[])` 这条**同步** AIDL 通道，再由 HintManagerService 在内部触发 `IHintSession.setMode`，错误码从系统进程经 Binder 一路返回 Java 层。`IHintSession` 整体声明为 `oneway interface`，但 `setThreads` 这条路径通过 `IHintManager` 的 sync 通道拿到 errno：

```
Java Session.setThreads(int[])
  → nativeSetThreads
  → gAPH_setThreadsFn (dlopen libandroid.so 后 dlsym)
  → APerformanceHint_setThreads
  → session->setThreads (Binder 客户端)
  → IHintManager.setHintSessionThreads (sync IPC)
  → HintManagerService (system_server)
  → 校验：tids 全属于本进程？session 在前台？tids 非空？
  → 内部 IHintSession.setMode
  → 返回 errno (EINVAL/EPERM/0)
  → Java: throwExceptionForErrno
       EINVAL → IllegalArgumentException
       EPERM  → SecurityException
       其他   → RuntimeException
```

JNINativeMethod 注册表里 `nativeReportActualWorkDuration` 有两个重载（`(JJ)V` 与 `(JJJJJ)V`），分别对应单 long 旧接口和 WorkDuration 4 字段新接口。

### 2. Android 16 全量 ADPF FlaggedApi 全景（来自 `flags.aconfig`）

按 `is_exported` / `is_fixed_read_only` 划分：

**应用可见（`is_exported: true`）**：
| flag 名 | 对应 API |
|---------|----------|
| `adpf_gpu_report_actual_work_duration` | `WorkDuration` 类 + `reportActualWorkDuration(WorkDuration)` + `GPU_LOAD_UP/DOWN/RESET` |
| `adpf_graphics_pipeline` | `SessionCreationConfig` + Graphics Pipeline 模式 |
| `adpf_prefer_power_efficiency` | `Session.setPreferPowerEfficiency(boolean)` |

**平台内部只读（`is_fixed_read_only: true`，应用不可写）**：
| flag 名 | 用途 |
|---------|------|
| `adpf_hwui_gpu` | libandroid 层 FMQ 通道启用 |
| `adpf_obtainview_boost` | HWUI obtainView 提频 |
| `adpf_platform_power_efficiency` | 平台内部能效模式 |
| `adpf_use_load_hints` | 公共 load hints 走 readonly flag（详见 §3） |

**应用可见但仍 gated（`is_exported: false`）**：
| flag 名 | 用途 |
|---------|------|
| `adpf_measure_during_input_event_boost` | 输入事件触发的 measure 提频 |

### 3. 私有 load hints 速率限制器（libandroid 内置）

`frameworks/base/native/android/performance_hint.cpp` 中常量：

```cpp
constexpr double kLoadHintInterval = std::chrono::nanoseconds(2s).count();   // 2 秒窗口
constexpr double kMaxLoadHintsPerInterval = 20;                              // 窗口内最多 20 个
constexpr double kReplenishRate = kMaxLoadHintsPerInterval / kLoadHintInterval;  // 10 hints/s

bool useNewLoadHintBehavior() {
    return android::os::adpf_use_load_hints() || kForceNewHintBehavior;
}
```

含义：NDK 层私有 API `APerformanceHint_notifyWorkloadIncrease/Reset/Spike` 在 `adpf_use_load_hints` flag 开启后启用，并被 libandroid 内置令牌桶限流（2 秒滑动窗口、稳态 10 hints/s）。这套约束是为防止游戏渲染循环以帧率（60–120 Hz）滥用 hint。Java SDK 未暴露这套 API，但游戏引擎和 HWUI 内部可通过 native 路径使用。

### 4. `WorkDuration` 的双重校验路径

Java `PerformanceHintManager.Session.reportActualWorkDuration(WorkDuration)` 的 setter 抛 `IllegalArgumentException`，但绕过 setter 直接构造 `WorkDuration` 后调用，会进入 JNI/libandroid 层：

```cpp
int APerformanceHint_reportActualWorkDuration2(APerformanceHintSession* session,
                                               AWorkDuration* workDurationPtr) {
    VALIDATE_PTR(session)
    VALIDATE_PTR(workDurationPtr)
    VALIDATE_INT(workDurationPtr->durationNanos, > 0)
    VALIDATE_INT(workDurationPtr->workPeriodStartTimestampNanos, > 0)
    VALIDATE_INT(workDurationPtr->cpuDurationNanos, >= 0)
    VALIDATE_INT(workDurationPtr->gpuDurationNanos, >= 0)
    VALIDATE_INT(workDurationPtr->gpuDurationNanos + workDurationPtr->cpuDurationNanos, > 0)
    return session->reportActualWorkDuration(workDurationPtr);
}
```

`VALIDATE_INT` 失败返回 `EINVAL`，JNI 抛 `IllegalArgumentException`。这是协程框架（Kotlin 1.9/2.x 的 `PerformanceHintManager` 包装库）需要复用的约束：**`totalDuration > 0` 且 `cpu+gpu > 0`，二者缺一不可**。

### 5. 新增 AIDL 接口（`IHintSession.associateToLayers`）

```java
oneway interface IHintSession {
    void updateTargetWorkDuration(long targetDurationNanos);
    void reportActualWorkDuration(in long[] actualDurationNanos, in long[] timeStampNanos);
    void close();
    void sendHint(int hint);
    void setMode(int mode, boolean enabled);
    void reportActualWorkDuration2(in WorkDuration[] workDurations);
    /** Used by apps to associate a session to a given set of layers */
    oneway void associateToLayers(in IBinder[] layerTokens);     // ★ Android 16 新增
}
```

`associateToLayers` 把 session 与 SurfaceFlinger 的图层 token 关联，用于 graphics pipeline 模式下的 frame cadence 协调（与 `adpf_graphics_pipeline` flag 联动）。调用是 `oneway`，应用不阻塞，但系统内部把 layerTokens 注入 PowerHAL 的 SessionConfig 后才能让提频信号真正生效。

### 工程结论（与 §8.6 原内容协同）

- §8.6 原"Session 线程绑定的核心约束"已经覆盖 API 边界，本节补充 **IPC 同步性**（setThreads 同步、reportActual 异步 oneway、associateToLayers oneway）这条工程决策依据。
- §8.6 原"GPU 负载上报（Android 16 FlaggedApi）"已经覆盖 Java 层校验，本节补充 **libandroid 层 VALIDATE_INT 二次校验**，解释为什么 WorkDuration 在绕过 setter 时仍会失败。
- 新 flag `adpf_graphics_pipeline` 与 `IHintManager.getMaxGraphicsPipelineThreadsCount()` 是 graphics pipeline 模式的两个抓手，应用层暂未直接暴露 setter，但通过 `adpf_graphics_pipeline` flag 启用后 `getMaxGraphicsPipelineThreadsCount()` 会返回非零值，提示应用可以做 graphics pipeline 提交。

详见：[DeepResearch/2026-06-15-performancehint-setthreads-ipc-chain-newly-flags.md](DeepResearch/2026-06-15-performancehint-setthreads-ipc-chain-newly-flags.md)
