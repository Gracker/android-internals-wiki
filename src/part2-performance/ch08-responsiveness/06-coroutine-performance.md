---
status: "finalized"
title: Kotlin Coroutine、Flow 与线程调度实践
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
last_task6_audit: "2026-07-09T10:20:48.680322"
---



# 8.6 Kotlin Coroutine、Flow 与线程调度实践

协程能把等待从线程中移开，也能把过多的小任务塞进同一条调度路径。判断性能时要区分四件事：协程是否挂起、continuation 是否需要 dispatch、目标线程何时得到 CPU、业务代码运行多久。把这四段都叫作“协程切换”会掩盖瓶颈。

以下说明按 kotlinx.coroutines 1.11.0 的公开 API 与 Android 17 / API 37 核对。平台源码锚点为 android-17.0.0_r1；涉及线程调度时，内核锚点为 android17-6.18-2026-06_r6。协程库版本可以独立升级，不能用 Android API 级别推断 Dispatcher 的内部实现。

## 一张图式化的性能模型

一次挂起调用可能经历以下阶段：

1. 当前协程运行到挂起点，保存 continuation 状态。
2. I/O、计时器、锁或其他协程完成条件。
3. continuation 交给 Dispatcher。
4. Dispatcher 内联恢复，或把 Runnable 放入目标队列。
5. 目标线程从队列取出任务。
6. Linux 调度器让该线程进入 Running。
7. 协程继续执行。

第 1、3、4 步主要属于协程运行时；第 5 步属于线程池或 Android Looper；第 6 步属于内核调度。Perfetto 中的 Runnable 等待位于第 5、6 步附近，业务方法的 CPU 时间位于第 7 步。只统计 suspend 函数的墙钟时间，无法判断是哪一层慢。

## Dispatcher 选择：选执行约束，不按“前台/后台”命名

### 四个标准 Dispatcher

| Dispatcher | 执行模型 | 适合的工作 | 容易写错的地方 |
|---|---|---|---|
| `Dispatchers.Main` | Android 主 Looper 对应的单线程 Dispatcher | UI 状态读取与更新、很短的主线程工作 | suspend 函数仍可能阻塞；队列拥塞不会消失 |
| `Dispatchers.Default` | 共享后台调度器，面向 CPU task，worker 有本地队列和 work stealing | 排序、解析、压缩、纯计算 | 阻塞 I/O 会占住计算并行度 |
| `Dispatchers.IO` | 面向阻塞 I/O 的弹性视图，与 Default 共享线程和资源 | 阻塞文件、阻塞 socket、旧数据库或 SDK API | suspend 网络 API 往往已有自己的调度；IO 不是“任何后台代码” |
| `Dispatchers.Unconfined` | 调用帧内启动，挂起后在恢复方所在线程继续 | 少数框架、测试和高级控制场景 | 没有线程约束，嵌套执行顺序也不应依赖 |

#### Main：Handler、Looper 与队列延迟

Android 端的 Main Dispatcher 由 kotlinx-coroutines-android 提供。1.11.0 的 `AndroidDispatcherFactory` 使用主 Looper 创建 async Handler，`HandlerContext.dispatch()` 再调用 `handler.post(block)`。async message 可以越过 MessageQueue 的同步屏障；它仍要等待主线程当前回调和排在前面的其他可执行消息。协程路径还带有 Job、continuation、取消检查和上下文元素，不能简化成一次普通方法调用。

`Dispatchers.Main.immediate` 在当前 Looper 已匹配时可以跳过一次重新投递；从其他线程进入时仍会 dispatch。它会改变执行顺序并引入同步重入的可能，所以选择它时要同时审查状态更新顺序，不能只按“少一次 post”判断。

Android 17 的 MessageQueue 已改为无全局队列锁的实现，减少一类入队与队列管理竞争。主线程依然一次只执行一个回调，前面的长消息、其他 async message、帧回调和 Binder 返回仍会形成队列延迟。

#### Default：CPU 并行度与阻塞补偿

Default 面向持续占用 CPU 的任务。当前 JVM 调度器使用共享 worker、本地队列、全局队列和 work stealing；CPU task 的有效并行度接近可用处理器数量，并保留最低并行度。内部实现可以随 kotlinx.coroutines 版本改变，业务代码不要依赖 worker 数字、队列顺序或线程名。

CPU 任务数量超过并行度时，排队属于预期行为。把阻塞调用放进 Default 会占住 worker；调度器虽然能为标记为 blocking 的任务做补偿，但任意业务代码不会自动获得正确的 blocking 标记。调用方应把阻塞边界放到 IO 或专用受限 Dispatcher。

#### IO：默认限制与弹性视图

`Dispatchers.IO` 默认允许并行执行的阻塞任务数为 64 与处理器数量中的较大值，可由 `kotlinx.coroutines.io.parallelism` 调整。这个数限制默认 IO 视图的并行阻塞任务，不等于进程里最多只能存在这么多协程或线程。

`Dispatchers.IO.limitedParallelism(n)` 具有弹性：这些视图不受默认 IO 并行度上限约束，但会共享底层线程与资源。若同时创建 100、60 两个视图，峰值阻塞并行度可能叠加。它适合表达两个外部系统各自的并发预算，也要求团队计算总并发量。

Default 与 IO 共享线程。当前协程已经在 Default worker 上时，切到 IO 可能继续使用同一线程；官方把这项行为描述为 best effort，代码不能依赖线程不变。

#### Unconfined：线程不受约束，结构仍可存在

Unconfined 在调用者的当前调用帧开始执行，第一次挂起后的恢复线程由挂起函数决定。嵌套的 Unconfined 协程使用内部事件循环避免栈溢出，执行顺序没有可依赖的保证。

线程约束和 Job 父子关系是两个维度。Unconfined 不会自动切断结构化并发，但它会让线程亲和性难以推理。需要“当前调用帧执行到首次挂起”且后续仍回到指定 Dispatcher 时，可评估 `CoroutineStart.UNDISPATCHED`；普通 UI 与数据层代码优先使用有明确执行约束的 Dispatcher。

### 让 suspend API 对主线程安全

下面的代码用于把阻塞读取与 CPU 解码的责任留在 Repository 内部，并让 Dispatcher 可替换。

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

调用者可以从 Main 调用 `load()`，不会把文件读取或解码留在主线程。示例假设缩略图文件大小受控；任意大文件要改为流式读取。注入 Dispatcher 还允许测试替换为 TestDispatcher。若阻塞 API 支持 `Thread.interrupt()`，可以评估 `runInterruptible(ioDispatcher)`；普通 `withContext(IO)` 的取消不会强制中断所有 Java 或 native 阻塞调用。

### limitedParallelism 解决并发预算，不保证线程亲和

`Dispatchers.Default.limitedParallelism(2)` 表示同一时刻最多有两个任务在该视图执行。并行度为 1 时，任务按顺序执行并具有 happens-before 保证，但它们仍可能落到不同 worker。依赖 ThreadLocal、固定 TID、JNI 线程附着或 Looper 的组件需要专用线程。

## 协程切换与线程切换：用事件数量和分位量化

### 三种事件不能互换

- **挂起/恢复**：continuation 状态变化，可能不换 Dispatcher。
- **dispatch**：Dispatcher 决定内联执行或排队。
- **内核上下文切换**：CPU 从一个线程切到另一个线程，可由 `sched_switch` 观察。

一个协程恢复可能内联完成，也可能先排队再触发多次调度。一个 Linux 线程切换也可能与协程无关，例如 GC、Binder、RenderThread 或其他进程抢占。“协程几十到几百纳秒、线程 1–10 微秒”的固定范围缺少硬件、ART、协程版本、CPU 频率和队列状态，不能作为 Android 项目结论。

### dispatch 结构可以精确计数

| 调用形态 | 协程层面的 dispatch | 强制线程迁移 |
|---|---:|---:|
| 同一 Dispatcher 的 `withContext` | 通常 0 | 0 |
| 已在主线程调用 `Main.immediate` | 0 | 0 |
| worker 调用 `withContext(Main)` | 进入 Main 一次，返回原 Dispatcher 一次 | 至少需要两个执行线程参与 |
| Default 调用 `withContext(IO)` | 语义上进入和返回两个边界 | 可能为 0；共享线程只提供 best effort |
| `yield()` | 至少让当前 continuation 重新参与调度 | 可能仍由同一线程恢复 |
| I/O 回调恢复 continuation | 一次恢复调度 | 取决于目标 Dispatcher 和线程状态 |

“至少需要两个线程参与”不等于恰好发生两次 `sched_switch`。等待期间可能发生抢占、GC 和其他任务，内核事件数量可以更多。

### 在目标设备上测四个数

量化时使用 release/profileable 构建、固定设备温度与电源状态，并分别记录：

| 指标 | 回答的问题 |
|---|---|
| wall time P50/P95/P99 | 从逻辑开始到结果可用，用户等了多久？ |
| thread running time | 业务和运行时用了多少 CPU？ |
| Runnable time | 线程已就绪却等了多久？ |
| scheduled slices / operation | 每次操作被切成多少段 CPU 执行？ |

对照组应保留相同业务工作，只去掉 Dispatcher 边界。测试空 block 得到的是框架、循环和计时器噪声；测试过重的 block 又会掩盖调度成本。推荐至少准备“空对照、短任务、真实任务”三档，并报告分位，不只报平均值。

120 Hz 一帧约 8.33 ms。若某设备测得一次往返 dispatch 的 P95 为 0.20 ms，同一帧串行执行 10 次，调度墙钟预算就可能接近 2 ms。这里的 0.20 ms 是计算示例，项目结论必须换成自己的测量值。

## 结构化并发：控制寿命、失败和取消

### Job 树的规则

`coroutineScope` 与普通父 Job 遵循这些规则：

- 父 Job 取消时，子 Job 会被取消。
- 父 Job 进入 completing 状态后，会等待子 Job 结束。
- 普通子协程以非 CancellationException 失败时，会取消父 Job；父的其他子任务随后也会取消。
- `supervisorScope` 或 `SupervisorJob` 隔离子任务失败，兄弟任务不会自动连带取消。
- 取消是协作式的。挂起函数通常检查取消；长 CPU 循环和不响应中断的阻塞 API需要主动配合。

Android 的 `viewModelScope` 与生命周期 scope 使用 SupervisorJob 风格的根作用域，因此一个顶层 `launch` 失败不会自动取消所有兄弟任务。进入普通 `coroutineScope` 后，作用域内部仍按普通失败传播处理。写异常策略时要区分这两层。

### 生命周期取消要覆盖“不可见”状态

`lifecycleScope` 在 Lifecycle 销毁时取消。页面进入 STOPPED 后仍可能长期存在，仅依赖 DESTROYED 会让不可见页面继续收集热流。下面的代码用于让两个流只在视图至少处于 STARTED 时并行收集。

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        launch { viewModel.uiState.collect(::renderState) }
        launch { viewModel.effects.collect(::handleEffect) }
    }
}
```

`repeatOnLifecycle` 在 STOPPED 时取消内部子协程，回到 STARTED 时重新创建。两个 `collect` 都是挂起终端操作，所以要放进各自的子协程。Fragment 应使用 `viewLifecycleOwner`，避免 View 销毁后仍更新旧视图。

### 结构化并发不能限制任务数量

在同一个 scope 中启动一万个子协程仍可能造成队列、内存和取消开销。生命周期正确只表示这些任务有共同的所有者，不表示并发度合理。并发上限应由 `limitedParallelism`、`Semaphore.withPermit`、Channel 或业务队列表达。

`async` 后忘记 `await` 不会让结构内的子协程脱离父 Job；父仍会等待它。但结果会被忽略，异常语义也更难阅读。没有结果需求时使用 `launch`，需要并行结果时显式 `await` 或 `awaitAll`。

### 常见的脱离结构路径

- `GlobalScope` 没有业务生命周期所有者，属于 delicate API。它不会保证进程常驻，也不会随页面退出取消。
- 手动创建 `CoroutineScope(Job() + dispatcher)` 后未在 owner 结束时调用 `cancel()`。
- 给 `withContext` 传入新的 Job，切断它与调用者 Job 的关系。当前官方 API 明确不支持这种模式。
- 用 `suspendCoroutine` 包装回调却不注销监听；可取消回调应使用 `suspendCancellableCoroutine` 并在取消处理器中注销。
- CPU 循环没有 `ensureActive()`、`yield()` 或可控分块，收到取消后仍占用 worker。
- 在 `NonCancellable` 中启动长期子任务。NonCancellable 只适合有界清理。

## Flow 背压：选择是否允许丢值、并发和取消

### 默认 Flow 是顺序执行

普通冷 Flow 的上游、中间操作和 collector 默认在同一协程顺序执行。collector 没处理完当前值时，上游的 `emit()` 不能继续完成，这就是基于挂起的背压。它保留所有值，但吞吐量受最慢阶段限制。

`buffer`、`conflate`、`channelFlow`、`flatMapMerge` 等操作会引入并发或通道。Flow 是冷还是热也要分开：StateFlow 和 SharedFlow 不会因为 collector 出现才创建数据源。

### 三个操作符的语义表

| 方案 | 是否丢值 | 是否增加并发 | 慢消费者时的行为 | 适用数据 |
|---|---|---|---|---|
| 默认 `collect` | 否 | 否 | 上游挂起 | 顺序事件、事务、审计记录 |
| `buffer(n)` + 默认 SUSPEND | 否 | 是，上游在独立协程 | 容量满后上游挂起 | 可流水处理且每项都要保留 |
| `conflate()` | 是，只保留较新值 | 是 | emitter 不因慢 collector 挂起 | 可跳过中间状态的 UI 快照 |
| `collectLatest` | 取消旧 action | action 可反复重启 | 新值到来时取消前一个 action | 搜索、预览、最新选择驱动的工作 |

`conflate()` 等价于容量 0 且溢出策略为 `DROP_OLDEST` 的 buffer 语义。StateFlow 已有基于 `Any.equals` 的状态合并，对它再调用 `conflate()` 没有效果。StateFlow 写值会遍历活跃订阅者，官方实现说明更新成本为 O(N)，订阅者数量很多时应纳入测量。

`buffer()` 默认容量是 `Channel.BUFFERED`，不是固定写死在业务语义里的数字。相邻的 `channelFlow`、`flowOn`、`buffer` 与 `produceIn` 会融合，最终容量与溢出策略要按操作符顺序推导。使用 `Channel.UNLIMITED` 会把持续速率差转成无上限内存增长。

### 按数据语义选择

下面的代码用于对比必须保留的事件、可跳过的状态与可取消的搜索三种路径。

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

事件缓冲满后会挂起上游，不会丢事件；UI 快照允许跳过中间值；新查询会取消旧的 collector action。示例假定该函数从 Main scope 调用，`persist()` 与 `repository.search()` 自己满足 main-safe 契约。`buffer()` 会增加协程和通道，不会自动选择后台 Dispatcher。第三条路径只有在搜索支持协作取消时才会及时生效；不可中断的阻塞 SDK 即使包在 IO 中，也可能拖到调用返回后才结束。

### flowOn 只改变上游

`flowOn(dispatcher)` 改变它前面那段上游的执行上下文，不改变下游 collector。跨 Dispatcher 时通常会加入通道和额外协程，所以它既影响执行位置，也影响缓冲与取消边界。数据层已经提供 main-safe suspend API 时，不要在每一层重复堆叠 `flowOn(IO)`。

### UI 收集还要考虑生命周期

StateFlow 或 SharedFlow 是热流，页面停止显示后上游可能继续运行。是否停止上游由 `stateIn/shareIn` 的 SharingStarted 策略和外部 scope 决定；`repeatOnLifecycle` 只控制当前 UI collector。排查后台耗电时要同时看共享上游的 owner、停止超时和订阅数量。

### StateFlow、SharedFlow 与 flatten 的资源语义

`StateFlow` 是只有一个当前值的状态容器，按 `Any.equals` 合并相同值；更新会遍历活跃订阅者，成本随订阅者数量增长。`SharedFlow` 是广播流，`replay`、`extraBufferCapacity` 和 `onBufferOverflow` 共同决定慢订阅者如何影响 emitter。两者都不会自动拥有上游生命周期，`shareIn` / `stateIn` 的 scope 与 `SharingStarted` 才决定上游何时启动、停止和保留最后状态。

`flatMapConcat` 顺序处理内层流，`flatMapMerge(concurrency)` 允许多条内层流并发，`flatMapLatest` 在新值到来时取消旧内层流。并发上限必须服从数据库连接、HTTP client、文件描述符和内存预算；取消只有在内层操作协作取消时才会及时生效。操作符链本身不会为每一级都创建 Job，但 `buffer`、`flowOn`、`channelFlow` 和并发 flatten 会引入协程或 Channel 边界。

## 在 Perfetto、调试器和 CPU Profiler 中定位协程

### 三类工具回答不同问题

| 工具 | 擅长回答 | 不能单独证明 |
|---|---|---|
| Perfetto / System Trace | 线程何时 Running、Runnable、Sleep；帧、Binder、频率和自定义 trace 的时间关系 | 某段 worker CPU 一定属于哪个 CoroutineName |
| Coroutine Debugger | Job 层级、状态、Dispatcher、挂起栈和创建栈 | release 构建中的真实耗时 |
| CPU Profiler 采样 | 哪些 Java/Kotlin/native 栈消耗 CPU | 等待队列、跨线程墙钟路径和完整因果链 |

调试器暂停和 debug 构建会扰动线程时序。性能结论应来自 profileable/release 构建；调试器用于解释 Job 状态，不能用暂停后的时间线做延迟基准。

`CoroutineName` 有助于调试器和日志阅读，但不会自动在 Perfetto 中生成同名 slice。需要稳定映射时，应给业务操作添加 trace。

### 跨 suspend 边界使用 async trace

同步 `beginSection/endSection` 必须在同一线程正确嵌套，不适合包住可能换线程的 suspend block。下面的辅助函数用于用唯一 cookie 记录跨线程、跨挂起的逻辑操作。

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

这里的 `Trace` 可使用 `androidx.tracing.Trace`。async section 表示业务墙钟区间，不会把等待时间伪装成某一线程的 CPU 时间。对不会挂起的短函数再使用同步 section，Perfetto 才能同时显示“整条操作等了多久”和“各线程执行了多久”。

AndroidX Tracing 2.0 当前仍是 beta，它新增了协程上下文传播和进程内 Perfetto packet；生产采用前要评估依赖版本、初始化开销与文件策略。稳定方案仍可使用 AndroidX Tracing 1.x 的同步/异步事件配合系统 trace。

### 用 sched 表量化 worker 运行片段

下面的 PerfettoSQL 用于统计协程 worker 在选定 trace 中获得 CPU 的次数与运行时间。

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

每一行 `sched` 记录该线程的一段 Running 时间，`scheduled_slices` 不是 coroutine resume 次数。将查询限制到业务 async slice 的时间窗，再配合方法采样和 Job 信息，才能判断碎片是否来自协程、GC、库代码或其他任务。

### 识别常见 trace 形态

- worker 长时间 Running：可能是大 CPU block；用采样栈找方法，并检查取消点。
- worker 长时间处于不可中断睡眠或 I/O：检查阻塞 API、存储与内核路径。
- worker 大量短 Running slice：可能是细粒度任务，也可能是 profiler 或其他运行时活动；加入业务 trace 后再归因。
- Main 上 async 操作很长而 Running 很短：多半在等队列、I/O、锁或其他线程，不能把全部墙钟时间算成主线程 CPU。
- Default 任务长期 Runnable：CPU 已饱和或线程优先级/系统负载影响调度；继续查看各核心、频率和竞争进程。

Android Studio 的 Java/Kotlin 方法 instrumentation 会引入额外开销，高频短协程尤其容易被放大。确认方法热点时优先使用采样；需要精确调用次数时再用 instrumentation，并明确它不代表生产延迟。

### kotlinx-coroutines-debug 的边界

`kotlinx-coroutines-debug` 的动态 agent 与 DebugProbes 主要面向标准 JVM。Android 设备上的协程调试由 Android Studio/IDE 集成和打包在 coroutines-core 中的调试元数据支持，不应把 JVM Instrument agent 当成设备侧 Perfetto 方案。调试设施会增加观测成本，也不应在生产长期启用。

## Coroutine 与 RxJava：比较相同语义

“协程一定更快”与“RxJava 操作符一定更成熟所以更快”都缺少工作负载前提。两者需要在相同的数据语义下比较：

| 维度 | Flow / Coroutine | RxJava |
|---|---|---|
| 单值异步 | suspend 函数、Job 取消 | Single/Maybe、Disposable |
| 默认流控制 | 冷 Flow 顺序执行，emit 挂起 | Observable 无背压；Flowable 使用 request 协议 |
| 并发边界 | buffer、flowOn、channelFlow 等 | subscribeOn、observeOn、各类 Scheduler |
| 生命周期 | Job 树与 scope | Disposable/CompositeDisposable |
| 融合优化 | 相邻 Flow 通道操作会融合 | 部分操作符支持 queue fusion |

基准必须统一热流/冷流、缓冲容量、丢值策略、错误处理、调度边界和消费者工作量。只比较“启动一百万个空任务”无法代表网络、数据库或 UI 路径。已有 RxJava 项目也不应仅凭微基准整体迁移；先测高频链路和维护成本。

## 自定义 Dispatcher：优先复用线程，再考虑专用线程

### 并发上限优先使用视图

下面的代码用于给图片解码和旧 SDK 各自设置并发预算，不创建新线程池。

```kotlin
private val imageDecodeDispatcher =
    Dispatchers.Default.limitedParallelism(2)

private val legacySdkDispatcher =
    Dispatchers.IO.limitedParallelism(4)
```

前者最多并行执行两个 CPU 解码任务，避免占满所有 Default 并行度；后者限制旧阻塞 SDK 的并发调用。IO 的弹性视图会与其他 IO 视图叠加，仍要检查进程总阻塞并发量。

### 线程亲和才创建专用 Executor

下面的代码用于必须固定到同一 Java 线程的 native 会话，并把线程释放绑定到 owner 的 `close()`。

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

专用 Dispatcher 持有原生线程，创建和销毁都有成本。它应由 Application 级服务、Repository 或其他明确 owner 复用，并在生命周期结束时关闭。不要在每次请求中创建 Executor，也不要用 Java 的 `Thread.MAX_PRIORITY` 代替 Android 线程优先级与负载测量。

### Executor、HandlerThread 与队列所有权

自定义 `ExecutorCoroutineDispatcher` 的 owner 还要定义 queue、rejection、停止接单、shutdown timeout 和未完成任务语义。`Executors.newFixedThreadPool()` 使用无界队列；线程数固定不代表提交侧有背压。需要有界策略时显式构造 `ThreadPoolExecutor`，并让 rejection 对应清楚的业务失败或降级。

`HandlerThread` 只在 API 明确要求 `Looper` / `Handler`、线程亲和或 MessageQueue 语义时使用。它是一个常驻线程和一条串行队列，长 callback 会阻塞所有后续消息；owner 结束时调用 `quitSafely()`，必要时在其他线程带超时 `join()`。普通串行状态操作优先比较 `limitedParallelism(1)`、Mutex、actor/Channel 和单线程 Executor：前者不保证固定 TID，也不保证一个含 suspension 的操作整体互斥。

`Channel` 的发送/接收以挂起等待，不占住物理线程；`BlockingQueue.put/take` 会阻塞调用线程。两者都能设计有界背压，也都需要明确关闭、取消和异常协议，不能把 BlockingQueue 概括成“没有背压”。

### 线程优先级与 ADPF 不能从协程名字推导

`Process.setThreadPriority()` 设置 Linux nice，`Thread.setPriority()` 维护 Java priority 语义；它们的数值范围、继承和 runtime 行为不同。Android 的 task profile、cpuset、uclamp、进程状态、thermal 和 OEM 策略仍会改变线程实际获得的 CPU。需要 Android nice 时在目标线程入口设置并测量，不要从创建者线程或 `CoroutineName` 推断内核优先级。

Linux 6.18 的 EEVDF 在 runnable fair entity 中按 eligibility 与 virtual deadline 选择任务。协程 continuation 尚在用户态 scheduler 队列，与 worker 已 Runnable 但没获得 CPU 是两层等待：前者用提交/开始埋点和 worker 压力判断，后者用 Perfetto `sched` / `thread_state`、频率、cgroup 与 uclamp 判断。

ADPF session 绑定长期存在的一组 TID，不绑定 coroutine ID。周期性渲染、音视频或稳定计算若确实需要 ADPF，应让明确 owner 的长期 worker 承载，按完整周期上报 wall duration，并在 worker 被替换时更新 TID；不要为每次 `launch`、suspend 或 resume 创建 session。

## Android 17 与内核 6.18 下的边界

- `Dispatchers.Main` 仍受单线程 Looper 约束。Android 17 的无全局锁 MessageQueue 降低队列竞争，没有消除长消息和帧预算。
- Default/IO 的队列与 work stealing 位于用户态；Linux 6.18 调度器只看到 worker 线程。协程优先级不会自动转成内核调度优先级。
- Perfetto 中 `Runnable` 表示线程可运行却未获得 CPU；它与协程在 Dispatcher 队列中尚未出队是不同状态。
- ADPF `PerformanceHintManager.Session` 绑定 TID，不绑定 coroutine ID。可迁移的 Default worker 不适合用一个静态 TID 列表长期代表某条协程。
- ADPF 适合持续、可度量的渲染或计算 work cycle。不要给每次 suspend/resume 发送 hint，也不要假设 hint 会固定到某类 CPU 核心。
- 发现系统调度或 Binder 等待时，平台源码按 android-17.0.0_r1 核对，内核行为按 android17-6.18-2026-06_r6 核对；历史版本 trace 不能直接代替当前基线。

## 排查清单

### 主线程

- suspend 函数内部是否仍有阻塞 I/O、锁或大计算？
- 是否连续嵌套多个 `withContext(Main/Default/IO)`？
- `Main.immediate` 是否改变了事件顺序或触发重入？
- UI collector 是否用 `repeatOnLifecycle` 跟随可见状态？

### worker

- Default 上是否存在阻塞调用？
- IO 与各 limitedParallelism 视图的总并发量是多少？
- CPU 循环是否定期检查取消？
- 任务粒度是否小到调度和对象分配占主要比例？
- 自定义 Executor 是否复用并正确关闭？

### Flow

- 中间值能否丢弃？
- buffer 满时应挂起、丢旧值还是丢新值？
- collectLatest 的 action 能否协作取消？
- flowOn 放在了哪段上游，是否无意增加通道边界？
- StateFlow/SharedFlow 的共享 scope 在页面不可见时是否仍工作？

### Trace

- 业务墙钟区间是否有 async trace？
- 同步 section 是否跨过 suspend 或线程迁移？
- 是否同时查看 Running、Runnable、Sleep 与 CPU 频率？
- 方法热点来自采样还是高开销 instrumentation？
- 调试器观察到的 Job 状态是否与 release trace 分开记录？

## 版本演进

- Kotlin 1.3 稳定了语言层协程支持，kotlinx.coroutines 继续独立演进。
- AndroidX Lifecycle 后续提供 `viewModelScope`、`lifecycleScope` 与 `repeatOnLifecycle`，把常见 Android owner 接入 Job 生命周期。
- kotlinx.coroutines 的 Default/IO 调度器、Flow 融合和调试支持持续变化；这里以 1.11.0 公开 API 为准，不承诺内部线程数量和队列实现长期不变。
- Android 12 / API 31 引入 `PerformanceHintManager`；Android 14 / API 34 公开 `Session.setThreads()`。它们是线程级性能提示接口，不是协程调度器。
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
