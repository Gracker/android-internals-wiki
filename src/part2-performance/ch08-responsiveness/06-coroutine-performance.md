---
status: "finalized"
title: Kotlin Coroutine、Flow 与线程调度实践
chapter: '8.6'
section: '8.6'
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-08-09'
last_verified_against: kotlinx.coroutines 1.11.0 / Android 17 android-17.0.0_r1 / kernel android17-6.18-2026-06_r6
confidence: medium-high
consolidated_from:
  - "src/part2-performance/ch08-responsiveness/17-kotlin-flow-backpressure-performance.md"
  - "src/part2-performance/ch08-responsiveness/19-thread-model-dispatcher-selection.md"
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
task9_state: reviewed
task2b_state: fixed
---



# 8.6 Kotlin Coroutine、Flow 与线程调度实践

协程可以在等待期间释放线程，也可能把大量细小任务集中到同一条调度路径。分析性能时，需要区分四件事：协程何时挂起、保存后续执行状态的 continuation 是否需要 dispatch（提交给调度器）、目标线程何时获得 CPU，以及业务代码实际运行了多久。如果把这四个阶段都称为“协程切换”，就无法判断延迟发生在哪里。

以下说明按照 kotlinx.coroutines 1.11.0 的公开 API 和 Android 17 / API 37 核对。平台源码基线为 `android-17.0.0_r1`，涉及线程调度时使用内核基线 `android17-6.18-2026-06_r6`。协程库可以独立于系统升级，不能根据 Android API 级别推断 Dispatcher 的内部实现。

## 一张图式化的性能模型

一次挂起和恢复可能经历以下阶段：

1. 当前协程运行到挂起点，将后续要继续执行的位置和局部状态保存到 continuation。
2. I/O、计时器、锁或其他协程完成条件。
3. continuation 交给 Dispatcher。
4. Dispatcher 直接在当前调用栈内恢复，或将 `Runnable` 放入目标队列。
5. 目标线程从队列取出任务。
6. Linux 调度器为目标线程分配 CPU，使它进入 Running 状态。
7. 协程继续执行。

第 1、3、4 步主要发生在协程运行时；第 5 步属于线程池或 Android Looper；第 6 步属于内核调度。Perfetto 中的 Runnable 表示线程已经具备运行条件，却尚未获得 CPU；continuation 仍停留在 Dispatcher 队列中的等待则不会直接显示成该线程的 Runnable。业务方法的 CPU 时间位于第 7 步。只统计 suspend 函数从开始到结束的墙钟时间，无法判断具体哪一层较慢。

## Dispatcher 选择：选执行约束，不按“前台/后台”命名

### 四个标准 Dispatcher

| Dispatcher | 执行模型 | 适合的工作 | 容易写错的地方 |
|---|---|---|---|
| `Dispatchers.Main` | Android 主 Looper 对应的单线程 Dispatcher | UI 状态读取与更新、很短的主线程工作 | suspend 函数仍可能阻塞；队列拥塞不会消失 |
| `Dispatchers.Default` | 共享后台调度器，面向 CPU task；worker 有本地队列，并可通过 work stealing 从其他队列取任务 | 排序、解析、压缩、纯计算 | 阻塞 I/O 会占住计算并行度 |
| `Dispatchers.IO` | 面向阻塞 I/O 的弹性视图，与 Default 共享线程和资源 | 阻塞文件、阻塞 socket、旧数据库或 SDK API | suspend 网络 API 往往已经自行调度；IO 不适合所有后台代码 |
| `Dispatchers.Unconfined` | 调用帧内启动，挂起后在恢复方所在线程继续 | 少数框架、测试和高级控制场景 | 没有线程约束，嵌套执行顺序也不应依赖 |

#### Main：Handler、Looper 与队列延迟

Android 上的 Main Dispatcher 由 kotlinx-coroutines-android 提供。1.11.0 的 `AndroidDispatcherFactory` 使用主 Looper 创建 async Handler，`HandlerContext.dispatch()` 再调用 `handler.post(block)`。async message 可以越过 MessageQueue 的同步屏障，但仍要等待主线程当前回调和排在前面的其他可执行消息。协程路径还要处理 Job、continuation、取消检查和上下文元素，因此开销不等同于一次普通方法调用。

`Dispatchers.Main.immediate` 在当前线程已经是目标 Looper 时，可以跳过一次重新投递；从其他线程进入时仍会 dispatch。直接执行会改变事件先后顺序，也可能发生同步重入，也就是尚未退出当前调用就再次进入同一段状态逻辑。因此，不能只因为“少一次 post”就选择它。

Android 17 的 MessageQueue 已改为无全局队列锁的实现，减少了一类入队和队列管理竞争。主线程仍然一次只执行一个回调，前面的长消息、其他 async message、帧回调和 Binder 返回仍会造成队列延迟。

#### Default：CPU 并行度与阻塞补偿

Default 面向持续占用 CPU 的任务。当前 JVM 调度器使用共享 worker、本地队列、全局队列和 work stealing（空闲 worker 从其他队列窃取任务）；CPU task 的有效并行度接近可用处理器数量，并保留最低并行度。内部实现可能随 kotlinx.coroutines 版本变化，业务代码不能依赖具体 worker 数量、队列顺序或线程名。

CPU 任务数量超过并行度后，新增任务排队属于预期行为。把阻塞调用放入 Default 会一直占用 worker；调度器可以为被正确标记为 blocking 的内部任务增加补偿线程，但普通业务代码不会自动获得这个标记。调用方应将阻塞边界放到 IO 或专用的受限 Dispatcher。

#### IO：默认限制与弹性视图

`Dispatchers.IO` 默认允许并行执行的阻塞任务数，是 64 与处理器数量二者中的较大值，可以通过 `kotlinx.coroutines.io.parallelism` 调整。这个数限制默认 IO 视图中同时执行的阻塞任务，不表示进程最多只能存在这么多协程或线程。

`Dispatchers.IO.limitedParallelism(n)` 创建的是弹性视图：每个视图不受默认 IO 并行度上限约束，但仍共享底层线程和资源。如果同时创建并行度为 100 和 60 的两个视图，峰值阻塞并行度可能叠加。它适合表达两个外部系统各自的并发预算，但团队必须同时计算进程总并发量。

Default 与 IO 共享底层线程。当前协程已经位于 Default worker 时，切换到 IO 后可能仍使用同一线程；官方将这种复用描述为 best effort（尽力而为），业务代码不能依赖线程保持不变。

#### Unconfined：线程不受约束，结构仍可存在

Unconfined 会在调用者当前调用栈中开始执行，第一次挂起后的恢复线程则由挂起函数决定。嵌套的 Unconfined 协程使用内部事件循环避免栈溢出，但执行顺序没有稳定保证。

线程约束和 Job 父子关系是两个独立维度。Unconfined 不会自动切断结构化并发，但会让代码究竟在哪个线程运行变得难以推断。需要“在当前调用栈执行到首次挂起，后续仍回到指定 Dispatcher”时，可以评估 `CoroutineStart.UNDISPATCHED`；普通 UI 和数据层代码应优先使用线程约束明确的 Dispatcher。

### 让 suspend API 对主线程安全

下面的代码将阻塞文件读取和 CPU 解码的线程选择封装在 Repository 内部，同时允许测试替换 Dispatcher：

```kotlin
class ThumbnailRepository(
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val cpuDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    suspend fun load(file: File): Bitmap {
        val bytes = withContext(ioDispatcher) {
            file.readBytes() // 阻塞文件 I/O
        }
        return withContext(cpuDispatcher) {
            requireNotNull(
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            )
        }
    }
}
```

调用者可以从 Main 调用 `load()`，文件读取和解码仍会分别在指定 Dispatcher 上执行，这就是 main-safe：API 可以安全地从主线程调用。示例假设缩略图文件大小可控；任意大小的文件应改为流式读取。注入 Dispatcher 还允许测试替换为 TestDispatcher。如果阻塞 API 支持 `Thread.interrupt()`，可以评估 `runInterruptible(ioDispatcher)`；取消普通的 `withContext(IO)` 并不会强制中断所有 Java 或 native 阻塞调用。

### limitedParallelism 解决并发预算，不保证线程亲和

`Dispatchers.Default.limitedParallelism(2)` 表示同一时刻最多有两个任务在这个视图中执行。并行度为 1 时，任务按顺序执行，并具有 happens-before 保证，也就是前一个任务完成的内存写入对后一个任务可见；但两个任务仍可能落到不同 worker。依赖 ThreadLocal、固定 TID、JNI 线程附着或 Looper 的组件需要专用线程。

## 协程切换与线程切换：用事件数量和分位量化

### 三种事件不能互换

- **挂起 / 恢复**：continuation 状态发生变化，但不一定更换 Dispatcher。
- **dispatch**：Dispatcher 决定直接执行还是把任务放入队列。
- **内核上下文切换**：CPU 从一个线程切换到另一个线程，可以通过 `sched_switch` 观察。

一次协程恢复可能在当前调用栈内完成，也可能先排队，并在等待期间经历多次线程调度。一次 Linux 线程切换也可能与协程完全无关，例如由 GC、Binder、RenderThread 或其他进程抢占触发。“协程几十到几百纳秒、线程 1–10 微秒”这类固定范围缺少硬件、ART、协程版本、CPU 频率和队列状态等条件，不能直接用作 Android 项目结论。

### dispatch 结构可以精确计数

| 调用形态 | 协程层面的 dispatch | 强制线程迁移 |
|---|---:|---:|
| 同一 Dispatcher 的 `withContext` | 通常 0 | 0 |
| 已在主线程调用 `Main.immediate` | 0 | 0 |
| worker 调用 `withContext(Main)` | 进入 Main 一次，返回原 Dispatcher 一次 | 至少有两个执行线程参与 |
| Default 调用 `withContext(IO)` | 语义上进入和返回两个边界 | 可能为 0；共享线程只提供 best effort |
| `yield()` | 至少让当前 continuation 重新参与调度 | 可能仍由同一线程恢复 |
| I/O 回调恢复 continuation | 一次恢复调度 | 取决于目标 Dispatcher 和线程状态 |

“至少有两个线程参与”不表示恰好发生两次 `sched_switch`。等待期间还可能发生抢占、GC 和其他任务，内核记录的切换次数可以更多。

### 在目标设备上测四个数

量化时应使用 release / profileable 构建，固定设备温度和电源状态，并分别记录：

| 指标 | 回答的问题 |
|---|---|
| wall time P50 / P95 / P99 | 从逻辑开始到结果可用，用户等待了多久？ |
| thread running time | 业务和运行时用了多少 CPU？ |
| Runnable time | 线程已就绪却等了多久？ |
| scheduled slices / operation | 每次操作被分成多少段 Running 区间？ |

对照组应保留相同的业务工作，只移除 Dispatcher 边界。空 block 测到的主要是框架、循环和计时器噪声；block 过重又会掩盖调度成本。至少应准备“空对照、短任务、真实任务”三档，并报告分位数，不能只报告平均值。

120 Hz 屏幕的一帧约为 8.33 ms。如果某台设备测得一次往返 dispatch 的 P95 为 0.20 ms，同一帧串行执行 10 次，调度所占墙钟时间就可能接近 2 ms。这里的 0.20 ms 只用于演示计算方法，项目结论必须使用自己的测量值。

## 结构化并发：控制寿命、失败和取消

### Job 树的规则

`coroutineScope` 和普通父 Job 遵循以下规则：

- 父 Job 取消时，子 Job 会被取消。
- 父 Job 进入 completing（自身代码结束、等待子任务）状态后，会等待所有子 Job 结束。
- 普通子协程以非 CancellationException 失败时，会取消父 Job；父的其他子任务随后也会取消。
- `supervisorScope` 或 `SupervisorJob` 会隔离子任务失败，兄弟任务不会自动随之取消。
- 取消是协作式的。挂起函数通常会检查取消；长 CPU 循环和不响应中断的阻塞 API 需要主动配合。

Android 的 `viewModelScope` 和生命周期 scope 使用 `SupervisorJob` 风格的根作用域，因此一个顶层 `launch` 失败时，不会自动取消所有兄弟任务。进入普通 `coroutineScope` 后，内部仍按照普通父子 Job 规则传播失败。设计异常策略时要区分这两层。

### 生命周期取消要覆盖“不可见”状态

`lifecycleScope` 会在 Lifecycle 销毁时取消，但页面进入 STOPPED 后仍可能长期存在；如果只等待 DESTROYED，不可见页面可能继续收集热流。下面的代码让两个 Flow 只在视图至少处于 STARTED 状态时并行收集：

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        launch { viewModel.uiState.collect(::renderState) }
        launch { viewModel.effects.collect(::handleEffect) }
    }
}
```

`repeatOnLifecycle` 会在 STOPPED 时取消内部子协程，回到 STARTED 时再重新创建。两个 `collect` 都是会持续挂起的终端操作，因此要放入各自的子协程。Fragment 应使用 `viewLifecycleOwner`，避免 View 已销毁后仍更新旧视图。

### 结构化并发不能限制任务数量

在同一个 scope 中启动一万个子协程，仍可能造成大量队列、内存和取消开销。生命周期正确只表示这些任务有共同所有者，不表示并发度合理。并发上限应通过 `limitedParallelism`、`Semaphore.withPermit`、Channel 或业务队列明确限制。

调用 `async` 后忘记 `await`，不会让结构内的子协程脱离父 Job，父任务仍会等待它结束；但返回结果会被忽略，异常处理也更难理解。没有返回值需求时应使用 `launch`，需要并行结果时则显式调用 `await` 或 `awaitAll`。

### 常见的脱离结构路径

- `GlobalScope` 没有业务生命周期所有者，属于 delicate API（需要谨慎使用的 API）。它不会保证进程常驻，也不会随页面退出而取消。
- 手动创建 `CoroutineScope(Job() + dispatcher)` 后未在 owner 结束时调用 `cancel()`。
- 向 `withContext` 传入新的 Job，会切断它与调用者 Job 的关系。当前官方 API 明确不支持这种模式。
- 使用 `suspendCoroutine` 包装回调却不注销监听；支持取消的回调应使用 `suspendCancellableCoroutine`，并在取消处理器中注销监听。
- CPU 循环没有 `ensureActive()`、`yield()` 或可控分块，收到取消后仍占用 worker。
- 在 `NonCancellable` 中启动长期子任务。`NonCancellable` 只适合时长明确且有限的清理工作。

## Flow 背压：选择是否允许丢值、并发和取消

### 默认 Flow 是顺序执行

普通冷 Flow 的上游、中间操作和 collector 默认在同一个协程中顺序执行。collector 没有处理完当前值时，上游的 `emit()` 无法继续完成，这就是基于挂起的背压：慢消费者通过挂起生产者来限制数据产生速度。它会保留所有值，但整体吞吐量由最慢阶段决定。

`buffer`、`conflate`、`channelFlow`、`flatMapMerge` 等操作会引入并发或 Channel 边界。还要区分冷流和热流：冷 Flow 通常在每次收集时开始执行，`StateFlow` 和 `SharedFlow` 这类热流则不会因为 collector 出现才创建数据源。

### 三个操作符的语义表

| 方案 | 是否丢值 | 是否增加并发 | 慢消费者时的行为 | 适用数据 |
|---|---|---|---|---|
| 默认 `collect` | 否 | 否 | 上游挂起 | 顺序事件、事务、审计记录 |
| `buffer(n)` + 默认 SUSPEND | 否 | 是，上游在独立协程中运行 | 容量满后上游挂起 | 可流水处理且每项都要保留 |
| `conflate()` | 是，只保留较新值 | 是 | emitter（发送方）不因慢 collector 挂起 | 可跳过中间状态的 UI 快照 |
| `collectLatest` | 取消旧 action | action 可反复重启 | 新值到来时取消前一个 action | 搜索、预览、最新选择驱动的工作 |

`conflate()` 等价于容量 0、溢出策略为 `DROP_OLDEST` 的 buffer 语义。StateFlow 已经根据 `Any.equals` 合并相同状态，再调用 `conflate()` 不会产生效果。StateFlow 写入新值时会遍历活跃订阅者，官方实现说明更新成本为 O(N)，即订阅者数量翻倍时遍历工作也近似翻倍；订阅者很多时应纳入测量。

`buffer()` 的默认容量是 `Channel.BUFFERED`，并非业务代码中写死的固定数字。相邻的 `channelFlow`、`flowOn`、`buffer` 和 `produceIn` 可能发生操作符融合，共享底层 Channel；最终容量和溢出策略要按照操作符顺序推导。使用 `Channel.UNLIMITED` 会把生产与消费之间长期存在的速率差转化为没有上限的内存增长。

### 按数据语义选择

下面的代码对比三种数据语义：必须全部保留的事件、允许跳过中间值的 UI 状态，以及新查询到来时可以取消的旧搜索：

```kotlin
suspend fun collectPipelines(
    events: Flow<Event>,
    uiSnapshots: Flow<UiState>,
    queries: Flow<String>,
) = coroutineScope {
    launch {
        events
            .buffer(capacity = 64)
            .collect { event -> persist(event) }
    }

    launch {
        uiSnapshots
            .conflate()
            .collect { state -> render(state) }
    }

    launch {
        queries
            .collectLatest { query ->
                render(repository.search(query))
            }
    }
}
```

事件缓冲区满后会让上游挂起，不会丢失事件；UI 快照允许跳过中间值；新查询则会取消旧的 collector action。示例假定函数从 Main scope 调用，`persist()` 和 `repository.search()` 自己满足 main-safe 契约。`buffer()` 会增加协程和 Channel，但不会自动选择后台 Dispatcher。第三条路径只有在搜索支持协作式取消时才能及时停止；不可中断的阻塞 SDK 即使放在 IO 中，也可能一直执行到调用返回。

### flowOn 只改变上游

`flowOn(dispatcher)` 只改变它前方上游操作符的执行上下文，不改变下游 collector。跨 Dispatcher 时通常会加入 Channel 和额外协程，因此它既影响执行位置，也影响缓冲和取消边界。数据层已经提供 main-safe suspend API 时，不要在每一层重复叠加 `flowOn(IO)`。

### UI 收集还要考虑生命周期

StateFlow 和 SharedFlow 是热流，页面停止显示后，共享上游仍可能继续运行。上游何时停止由 `stateIn / shareIn` 的 `SharingStarted` 策略和外部 scope 决定；`repeatOnLifecycle` 只控制当前 UI collector。排查后台耗电时，还要检查共享上游的 owner、停止超时和订阅数量。

### StateFlow、SharedFlow 与 flatten 的资源语义

`StateFlow` 是只保存一个当前值的状态容器，按照 `Any.equals` 合并相同值；更新时会遍历活跃订阅者，开销随订阅者数量增长。`SharedFlow` 是广播流，`replay`（为新订阅者重放的值数量）、`extraBufferCapacity` 和 `onBufferOverflow` 共同决定慢订阅者如何影响 emitter。两者都不会自动拥有上游生命周期，只有 `shareIn` / `stateIn` 使用的 scope 和 `SharingStarted` 才决定上游何时启动、停止，以及是否保留最后状态。

`flatMapConcat` 按顺序处理内层流，`flatMapMerge(concurrency)` 允许多条内层流并发，`flatMapLatest` 则在新值到来时取消旧内层流。并发上限必须符合数据库连接数、HTTP client、文件描述符和内存预算；只有内层操作支持协作取消时，取消才能及时生效。操作符链不会为每一级都创建 Job，但 `buffer`、`flowOn`、`channelFlow` 和并发 flatten（将内层流合并回外层）会引入协程或 Channel 边界。

## 在 Perfetto、调试器和 CPU Profiler 中定位协程

### 三类工具回答不同问题

| 工具 | 擅长回答 | 不能单独证明 |
|---|---|---|
| Perfetto / System Trace | 线程何时 Running、Runnable、Sleep；帧、Binder、频率和自定义 trace 之间的时间关系 | 某段 worker CPU 一定属于哪个 `CoroutineName` |
| Coroutine Debugger | Job 层级、状态、Dispatcher、挂起栈和创建栈 | release 构建中的真实耗时 |
| CPU Profiler 采样 | 哪些 Java / Kotlin / native 调用栈消耗 CPU | 等待队列、跨线程墙钟路径和完整因果关系 |

调试器暂停和 debug 构建都会扰动线程时序。性能结论应来自 profileable / release 构建；调试器只用于解释 Job 状态，不能把暂停后的时间线用作延迟基准。

`CoroutineName` 有助于阅读调试器和日志，但不会自动在 Perfetto 中生成同名 slice。需要把业务操作稳定地映射到 trace 时，应显式添加跟踪标记。

### 跨 suspend 边界使用 async trace

同步的 `beginSection / endSection` 必须在同一线程上正确嵌套，不适合包住可能切换线程的 suspend block。下面的辅助函数为每次操作分配唯一 cookie，用 async section 记录跨线程、跨挂起的完整逻辑区间：

```kotlin
private val nextTraceCookie = AtomicInteger(1)

private suspend inline fun <T> traceAsync(
    name: String,
    crossinline block: suspend () -> T,
): T {
    val cookie = nextTraceCookie.getAndIncrement()
    Trace.beginAsyncSection(name, cookie)
    return try {
        block()
    } finally {
        Trace.endAsyncSection(name, cookie)
    }
}
```

这里的 `Trace` 可以使用 `androidx.tracing.Trace`。async section 表示业务操作从开始到结束的墙钟区间，不会把其中的等待时间误画成某个线程的 CPU 时间。对于不会挂起的短函数，再使用同步 section；这样 Perfetto 才能同时显示整条操作经过了多久，以及各线程实际执行了多久。

AndroidX Tracing 2.0 当前仍处于 beta，新增了协程上下文传播和进程内 Perfetto packet。在线上采用前，需要评估依赖版本、初始化开销和文件策略。需要稳定版本时，仍可以使用 AndroidX Tracing 1.x 的同步 / 异步事件配合系统 trace。

### 用 sched 表量化 worker 运行片段

下面的 PerfettoSQL 统计选定 trace 中，每个协程 worker 获得了多少段 CPU 运行时间，以及累计运行了多久：

```sql
SELECT
  t.name,
  COUNT(*) AS scheduled_slices,
  ROUND(SUM(s.dur) / 1e6, 3) AS running_ms
FROM sched AS s
JOIN thread AS t USING (utid)
WHERE t.name GLOB 'DefaultDispatcher-worker-*'
GROUP BY t.name
ORDER BY running_ms DESC;
```

`sched` 的每一行记录线程的一段 Running 时间，因此 `scheduled_slices` 不是 coroutine resume 次数。需要把查询限制在业务 async slice 的时间窗口内，再结合方法采样和 Job 信息，才能判断这些短片段来自协程、GC、库代码还是其他任务。

### 识别常见 trace 形态

- worker 长时间 Running：可能在执行大型 CPU block；使用采样栈定位方法，并检查取消点。
- worker 长时间处于不可中断睡眠或 I/O：检查阻塞 API、存储与内核路径。
- worker 出现大量短 Running slice：可能是细粒度任务，也可能来自 profiler 或其他运行时活动；加入业务 trace 后再归因。
- Main 上的 async 操作很长，但 Running 时间很短：大部分时间可能在等待队列、I/O、锁或其他线程，不能把全部墙钟时间算成主线程 CPU。
- Default 任务长期 Runnable：CPU 已饱和或线程优先级/系统负载影响调度；继续查看各核心、频率和竞争进程。

Android Studio 的 Java / Kotlin 方法 instrumentation（插桩跟踪）会引入额外开销，高频短协程尤其容易被放大。确认方法热点时应优先使用采样；只有需要精确调用次数时再使用 instrumentation，并注明结果不代表生产环境延迟。

### kotlinx-coroutines-debug 的边界

`kotlinx-coroutines-debug` 的动态 agent 和 DebugProbes 主要面向标准 JVM。Android 设备上的协程调试依赖 Android Studio / IDE 集成，以及打包在 coroutines-core 中的调试元数据，不能把 JVM Instrument agent 当成设备侧 Perfetto 方案。调试设施本身会增加开销，也不应在线上长期启用。

## Coroutine 与 RxJava：比较相同语义

判断 Coroutine 和 RxJava 性能时，必须先统一工作负载与数据语义，不能预设其中一方一定更快：

| 维度 | Flow / Coroutine | RxJava |
|---|---|---|
| 单值异步 | suspend 函数、Job 取消 | Single/Maybe、Disposable |
| 默认流控制 | 冷 Flow 顺序执行，`emit` 挂起 | `Observable` 无背压；`Flowable` 使用 request 协议 |
| 并发边界 | buffer、flowOn、channelFlow 等 | subscribeOn、observeOn、各类 Scheduler |
| 生命周期 | Job 树与 scope | Disposable/CompositeDisposable |
| 融合优化 | 相邻 Flow 通道操作会融合 | 部分操作符支持 queue fusion |

基准必须统一热流 / 冷流、缓冲容量、丢值策略、错误处理、调度边界和消费者工作量。只比较“启动一百万个空任务”无法代表网络、数据库或 UI 路径。已有 RxJava 项目也不应仅凭微基准整体迁移，应先测量高频路径和维护成本。

## 自定义 Dispatcher：优先复用线程，再考虑专用线程

### 并发上限优先使用视图

下面的代码复用标准 Dispatcher，分别限制图片解码和旧 SDK 的并发量，不创建新的线程池：

```kotlin
private val imageDecodeDispatcher =
    Dispatchers.Default.limitedParallelism(2)

private val legacySdkDispatcher =
    Dispatchers.IO.limitedParallelism(4)
```

前者最多并行执行两个 CPU 解码任务，避免占满 Default 的全部并行度；后者限制旧阻塞 SDK 的并发调用。IO 弹性视图的并发量会与其他 IO 视图叠加，因此仍要检查整个进程中的阻塞任务总数。

### 线程亲和才创建专用 Executor

下面的代码为必须固定在同一个 Java 线程上的 native 会话创建专用 Dispatcher，并通过 owner 的 `close()` 释放线程：

```kotlin
class NativeSessionExecutor : Closeable {
    private val dispatcher =
        Executors.newSingleThreadExecutor { task ->
            Thread(task, "native-session")
        }.asCoroutineDispatcher()

    suspend fun <T> call(block: () -> T): T =
        withContext(dispatcher) { block() }

    override fun close() {
        dispatcher.close()
    }
}
```

专用 Dispatcher 会一直持有原生线程，创建和销毁都有开销。它应由 Application 级服务、Repository 或其他明确的 owner 复用，并在 owner 生命周期结束时关闭。不要为每次请求创建 Executor，也不要用 Java 的 `Thread.MAX_PRIORITY` 代替 Android 线程优先级配置和负载测量。

### Executor、HandlerThread 与队列所有权

自定义 `ExecutorCoroutineDispatcher` 的 owner 还要定义 queue、rejection（拒绝新任务时的策略）、停止接单、shutdown timeout 和未完成任务的处理方式。`Executors.newFixedThreadPool()` 使用无界队列，线程数固定不表示提交方会受到背压。需要限制队列容量时，应显式构造 `ThreadPoolExecutor`，并让 rejection 对应明确的业务失败或降级结果。

只有 API 明确要求 `Looper` / `Handler`、固定线程亲和性或 MessageQueue 语义时，才应使用 `HandlerThread`。它包含一个常驻线程和一条串行队列，长 callback 会阻塞所有后续消息；owner 结束时应调用 `quitSafely()`，必要时从其他线程使用带超时的 `join()` 等待退出。对于普通串行状态操作，可以优先比较 `limitedParallelism(1)`、Mutex、actor / Channel 和单线程 Executor。`limitedParallelism(1)` 不保证固定 TID，也不保证包含 suspension 的整个业务操作始终互斥。

`Channel` 的发送 / 接收通过挂起等待，不占用物理线程；`BlockingQueue.put / take` 则会阻塞调用线程。两者都可以实现有界背压，也都需要明确关闭、取消和异常协议，不能笼统地说 `BlockingQueue`“没有背压”。

### 线程优先级与 ADPF 不能从协程名字推导

`Process.setThreadPriority()` 设置 Linux nice 值，`Thread.setPriority()` 维护 Java priority 语义；二者的数值范围、继承关系和 runtime 行为不同。Android 的 task profile、cpuset（允许线程运行的 CPU 集合）、uclamp（调度利用率上下限）、进程状态、thermal 和 OEM 策略，仍会改变线程实际获得的 CPU。需要设置 Android nice 时，应在目标线程入口设置并测量，不能根据创建者线程或 `CoroutineName` 推断内核优先级。

Linux 6.18 的 EEVDF 调度器会在 runnable fair entity（可运行的普通调度实体）中，根据 eligibility（是否具备运行资格）和 virtual deadline（虚拟截止时间）选择任务。协程 continuation 仍在用户态 scheduler 队列中，和 worker 已经 Runnable 但尚未获得 CPU，是两种不同的等待：前者通过提交 / 开始标记和 worker 队列压力判断，后者通过 Perfetto `sched` / `thread_state`、频率、cgroup 和 uclamp 判断。

ADPF（Android Dynamic Performance Framework）session 绑定一组长期存在的 TID（线程 ID），不绑定 coroutine ID。周期性渲染、音视频或稳定计算确实需要 ADPF 时，应由 owner 明确的长期 worker 承担，按照完整工作周期上报 wall duration，并在 worker 被替换时更新 TID；不要为每次 `launch`、suspend 或 resume 创建 session。

## Android 17 与内核 6.18 下的边界

- `Dispatchers.Main` 仍受单线程 Looper 约束。Android 17 的无全局锁 MessageQueue 减少了队列竞争，但没有消除长消息或改变帧预算。
- Default / IO 的队列和 work stealing 位于用户态，Linux 6.18 调度器只能看到 worker 线程。协程优先级不会自动转换成内核调度优先级。
- Perfetto 中 `Runnable` 表示线程可运行却未获得 CPU；它与协程在 Dispatcher 队列中尚未出队是不同状态。
- ADPF `PerformanceHintManager.Session` 绑定 TID，不绑定 coroutine ID。Default worker 之间可以迁移任务，因此一个静态 TID 列表不适合长期代表某条协程。
- ADPF 适合持续、可度量的渲染或计算 work cycle（工作周期）。不要为每次 suspend / resume 发送 hint，也不要假设 hint 会让任务固定到某一类 CPU 核心。
- 发现系统调度或 Binder 等待时，平台源码按 android-17.0.0_r1 核对，内核行为按 android17-6.18-2026-06_r6 核对；历史版本 trace 不能直接代替当前基线。

## 排查清单

### 主线程

- suspend 函数内部是否仍有阻塞 I/O、锁或大量计算？
- 是否连续嵌套多个 `withContext(Main/Default/IO)`？
- `Main.immediate` 是否改变了事件顺序或触发重入？
- UI collector 是否用 `repeatOnLifecycle` 跟随可见状态？

### worker

- Default 上是否存在阻塞调用？
- IO 和各个 `limitedParallelism` 视图的总并发量是多少？
- CPU 循环是否定期检查取消？
- 任务粒度是否小到调度和对象分配占主要比例？
- 自定义 Executor 是否复用并正确关闭？

### Flow

- 中间值能否丢弃？
- buffer 满时应挂起、丢旧值还是丢新值？
- collectLatest 的 action 能否协作取消？
- `flowOn` 放在了哪段上游，是否无意中增加了 Channel 边界？
- StateFlow / SharedFlow 的共享 scope 在页面不可见时是否仍在工作？

### Trace

- 业务墙钟区间是否有 async trace？
- 同步 section 是否跨过 suspend 或线程迁移？
- 是否同时查看 Running、Runnable、Sleep 和 CPU 频率？
- 方法热点来自采样还是高开销 instrumentation？
- 调试器观察到的 Job 状态是否与 release trace 分开记录？

## 版本演进

- Kotlin 1.3 稳定了语言层协程支持，kotlinx.coroutines 继续独立演进。
- AndroidX Lifecycle 后续提供了 `viewModelScope`、`lifecycleScope` 和 `repeatOnLifecycle`，将常见 Android owner 接入 Job 生命周期。
- kotlinx.coroutines 的 Default / IO 调度器、Flow 融合和调试支持仍在持续变化；本文以 1.11.0 公开 API 为准，不假设内部线程数量和队列实现长期不变。
- Android 12 / API 31 引入 `PerformanceHintManager`，Android 14 / API 34 公开 `Session.setThreads()`。它们是线程级性能提示接口，不属于协程调度器。
- Android 17 / API 37 的 MessageQueue 改为无全局队列锁实现；Main Dispatcher 仍执行在 Android 主线程。

## 参考资料

- [kotlinx.coroutines 1.11.0 API 总览](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/)
- [kotlinx-coroutines-android 1.11.0 HandlerDispatcher 源码](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/ui/kotlinx-coroutines-android/src/HandlerDispatcher.kt)
- [kotlinx.coroutines 1.11.0 CoroutineScheduler 源码](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt)
- [CoroutineDispatcher 公开契约](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-dispatcher/)
- [Dispatchers.IO 的并行度、弹性与共享线程说明](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)
- [Dispatchers.Unconfined 的恢复线程与事件循环](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-unconfined.html)
- [Main.immediate 的内联执行条件](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-main-coroutine-dispatcher/immediate.html)
- [withContext 的 dispatch 与取消契约](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/with-context.html)
- [Android 协程最佳实践](https://developer.android.com/kotlin/coroutines/coroutines-best-practices)
- [Lifecycle-aware coroutine 与 repeatOnLifecycle](https://developer.android.com/topic/libraries/architecture/views/coroutines-views)
- [Flow 公开契约](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-flow/)
- [buffer 的容量、溢出与操作符融合](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/buffer.html)
- [conflate 的丢值语义](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/conflate.html)
- [collectLatest 的取消语义](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/collect-latest.html)
- [StateFlow 的融合与复杂度说明](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-state-flow/)
- [Android 自定义 trace 事件](https://developer.android.com/topic/performance/tracing/custom-events)
- [AndroidX Tracing 2.0 进程内追踪与协程上下文传播](https://developer.android.com/topic/performance/tracing/in-process-tracing)
- [Android Studio System Trace](https://developer.android.com/studio/profile/cpu-profiler)
- [Android Studio / IntelliJ Coroutine Debugger](https://www.jetbrains.com/help/idea/debug-kotlin-coroutines.html)
- [PerformanceHintManager.Session API](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [Android 17 无全局锁 MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [android-17.0.0_r1 Combined MessageQueue 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java)
- [android-17.0.0_r1 PerformanceHintManager 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
