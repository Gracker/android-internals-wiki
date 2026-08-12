---
title: "Kotlin 协程泄漏诊断与结构化并发性能监控"
chapter: "20.21"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [coroutine, leak, structured-concurrency, performance, monitoring]
related_chapters: ["20.12", "20.19", "8.6"]
task6_state: reviewed
task9_state: deep-reviewed
pipeline_stage: reviewed
last_draft_polish_at: "2026-08-06T11:35:47+08:00"
last_draft_polish_run_id: "20260806-113520-draft-polish-933adf6b"
last_deep_review_at: "2026-08-06T12:38:04+08:00"
last_deep_review_run_id: "20260806-123528-deep-review-933adf6b"
last_verified: "2026-08-06"
last_verified_against: "android-17.0.0_r1 / Android 17 (API 37); kotlinx.coroutines 1.11.0 source/API docs and AndroidX Lifecycle public documentation links spot-checked; no Android 18/API38+ claims"
confidence: medium-high
sources:
- type: official
  path: kotlinx.coroutines 1.11.0 source and official API docs
- type: reference
  path: 'Android Developers: lifecycle-aware coroutines, StateFlow/SharedFlow, Compose side-effects, tracing, background task scheduling'
- type: aosp
  path: AOSP android-17.0.0_r1 / Android 17 API 37 platform boundary
---

# Kotlin 协程泄漏诊断与结构化并发性能监控

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`。协程与 Lifecycle 属于独立发布的库，不能把 Android 版本当成库版本；涉及库实现时以 `kotlinx.coroutines 1.11.0` 的公开源码/API 与 AndroidX Lifecycle 公共文档为验证边界。涉及 Linux task 调度时以内核 `android17-6.18-2026-06_r6` 为边界；协程本身没有可由内核直接识别的 task 类型。

Android 17 不认识“协程”这个调度单位。平台看到的是 `Handler` 消息、Java 线程和 Linux task。协程的 `Job` 树、挂起状态、Flow 订阅与取消传播都由 Kotlin/Jetpack 库管理。排查时需要把两层证据对齐，不能从某个 `DefaultDispatcher-worker` 线程长期存在推导出某个协程泄漏。

## 1. 什么才算协程泄漏

“协程泄漏”限定为以下情况之一：

- `Job` 在 owner 结束后仍为 active，继续执行或等待；
- 挂起 continuation 捕获 Activity、Fragment View、回调或大对象，使其超过预期生命周期；
- Flow、Channel 或 callback bridge 的生产者没有退出，底层 listener、socket、sensor 等资源继续注册；
- 重复创建的长期任务没有替换或取消，造成 active job、缓冲数据或业务请求持续累积；
- 自建 dispatcher/executor 的 owner 已结束，但 scope 和线程池没有关闭。

“Job 已经 completed，但监控表还保存着它”属于监控器自身的对象滞留。“线程池仍有空闲 worker”属于线程资源治理。两者都要修，但不能和活跃协程混为一类。

协程挂起时不占用一个专属线程，却仍保留 continuation、`CoroutineContext` 和被 lambda 捕获的对象。它恢复时也可能换到另一个 worker。因此，线程数和协程数没有一一对应关系。线程层的归因与阈值见 [20.19 线程泄漏与匿名线程监控](./19-thread-leak-anonymous-thread-monitoring.md)。

### 1.1 判断泄漏要同时满足“超期”和“仍被持有”

长期运行不等于泄漏。进程级事件总线、WebSocket 接收循环和应用级缓存刷新可以合法地存活到进程结束。反过来，一个早已挂起且 CPU 为零的 collector，仍可能持有 Fragment View。

每类任务需要预先定义：

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| owner | `fragment-view:detail`、`viewmodel:player`、`process:sync` | 决定取消时机 |
| operation | `collect-ui-state`、`load-page`、`listen-socket` | 聚合同类任务 |
| expected lifetime | view、ViewModel、service、process、request | 判断是否超出边界 |
| deadline | 5 秒、30 秒、无限但需 heartbeat | 判断异常时长 |
| cardinality | 每 owner 1 个、最多 4 个并发 | 发现重复创建 |
| cancellation contract | owner end、new request、timeout、manual | 指定谁负责取消 |

只有当 owner 已结束或任务超过契约，且对应 `Job`/资源仍活跃，才具备泄漏证据。

## 2. `Job` 树决定生命周期，不是变量名决定生命周期

结构化并发的核心关系是：

- parent 等待 children 完成后才完成；
- parent 被取消时，取消向 children 传播；
- 普通 child 以非 `CancellationException` 失败时，会使普通 parent 失败并取消 siblings；
- `SupervisorJob` 隔离 child failure，某个 child 失败不会自动取消 siblings；
- 即使使用 `SupervisorJob`，parent 自身被取消时仍会取消所有 children。

`SupervisorJob` 只改变失败传播，不能替代 owner 取消。把一个全新的 `SupervisorJob()` 直接传给 `launch`，还会把新协程从原 scope 的 `Job` 关系中拆开。`kotlinx.coroutines 1.11.0` 已对“向 builder 传入 `Job`”增加迁移提示；需要局部监督时使用 `supervisorScope`，需要长期 root 时在 owner 创建 scope。

取消是协作式的。`delay`、多数 channel/Flow 操作和 cancellable suspend API 会检查取消；不含挂起点的 CPU 循环、吞掉 `CancellationException` 的捕获逻辑，以及不可中断的阻塞 I/O，可能在 `cancel()` 后继续运行。

### 2.1 手动 scope 必须有 owner 和关闭入口

`CoroutineScope(Dispatchers.IO)` 工厂会在 context 没有 `Job` 时补一个 `Job`，所以它不是“没有 Job”。问题在于新 root 与 Activity、View 或服务没有自动关系，调用方若忘记取消，它会存活到任务自然结束或进程退出。

下面的代码用于没有现成 Lifecycle owner 的长期组件，明确创建和关闭 root scope：

```kotlin
class FeatureScope(
    private val ownerId: String,
    dispatcher: CoroutineDispatcher
) : CoroutineScope, AutoCloseable {
    private val rootJob = SupervisorJob()

    init {
        require(ownerId.matches(Regex("[a-z0-9._-]{1,48}")))
    }

    override val coroutineContext: CoroutineContext =
        rootJob + dispatcher + CoroutineName("owner:$ownerId")

    override fun close() {
        rootJob.cancel(
            CancellationException("owner closed: $ownerId")
        )
    }
}
```

`close()` 必须由组件确定的结束回调调用。`ownerId` 应是短的枚举型标识，不能带账号、搜索词或 URL。一次请求内部需要并发子任务时，使用 `coroutineScope { ... }` 或 `supervisorScope { ... }`，不要为每个请求再造一个 root。

`GlobalScope` 是带 `DelicateCoroutinesApi` 标记的进程级独立 scope，启动的任务没有业务 parent。只有任务明确允许存活到进程结束、不会捕获短生命周期 owner，并且有自己的失败与资源清理协议时，才有理由采用这种寿命。工程中更易审阅的做法是注入命名的 application scope。

`MainScope()` 每次调用都会创建一个新的 `SupervisorJob + Dispatchers.Main`。它适合没有 Lifecycle 的 UI owner，但 owner 必须保存该实例并在结束时调用 `cancel()`；在不同方法里反复调用 `MainScope().launch`，调用方无法再找到此前的 root。

### 2.2 Android owner 的推荐 scope

| owner | 推荐 scope | 自动取消点 | 常见误用 |
| --- | --- | --- | --- |
| Fragment View | `viewLifecycleOwner.lifecycleScope` | View lifecycle `DESTROYED` | 用 Fragment 的 `lifecycleScope` 捕获已销毁的 View |
| Activity/Fragment | `lifecycleScope` | 对应 Lifecycle `DESTROYED` | 以为进入 `STOPPED` 就会取消 |
| ViewModel | `viewModelScope` | `ViewModel.clear()` | 期望配置变更或页面暂时不可见时取消 |
| Composable effect | `LaunchedEffect` | 离开 Composition 或 key 变化 | 在 composition body 直接 `launch` |
| Composable event | `rememberCoroutineScope()` | 调用点离开 Composition | 把 scope 保存到全局对象 |
| process 级组件 | 注入的 application scope | 进程级 owner 主动关闭 | 捕获 Activity/View |
| 可靠后台任务 | WorkManager/合适的系统调度 API | 由 scheduler 管理 | 用 process scope 假装任务可跨进程存活 |

`lifecycleScope` 在 `DESTROYED` 时取消，不会因为 `STOPPED` 自动取消。只应在界面可见时运行的 Flow，需要 `repeatOnLifecycle`。

AndroidX Lifecycle 2.8 的重要变化是 `viewModelScope` 可作为 `ViewModel` 构造参数注入，便于替换 dispatcher、`SupervisorJob` 或测试 scope。它没有改变 `lifecycleScope` 的销毁取消契约。到 Lifecycle 2.11.0，Compose 又增加了更细的 scoped `ViewModelStore` 能力；这些都是库演进，不是 Android 17 平台行为。

## 3. Flow 与 Channel：collector 和 producer 是两条生命周期

### 3.1 冷流、热流的泄漏边界不同

冷 `Flow` 每次 `collect` 都启动一条新的上游执行。取消 collector 通常会沿挂起调用取消该次上游。若在同一个页面重复启动 collector，每次都会重复网络、数据库或 callback 注册。

`StateFlow`/`SharedFlow` 是热流。取消某个 collector 只结束该订阅者，不会取消其他订阅者，也不会自动结束生产者。由 `shareIn`/`stateIn` 创建的 sharing coroutine 由传入的 scope 管理：

- `SharingStarted.Eagerly` 立即启动；
- `Lazily` 在首个订阅者出现后启动，之后即使没有订阅者也继续；
- `WhileSubscribed(...)` 可在订阅者归零后停止上游；
- 取消 sharing scope 才是无条件结束 sharing coroutine 的控制点。

`collectLatest` 只会在新值到达时取消上一轮 action。它不会把 collector 绑定到 Lifecycle。`launchIn(scope)` 的生命周期就是传入 scope；`collectIn` 不是 `kotlinx.coroutines` 或 AndroidX Lifecycle 的标准公开 API，项目若有同名扩展，必须单独审阅它的 scope 语义。

### 3.2 View 层使用 `repeatOnLifecycle`

下面的代码用于 Fragment View 在可见期间并行收集两个 Flow：

```kotlin
override fun onViewCreated(
    view: View,
    savedInstanceState: Bundle?
) {
    viewLifecycleOwner.lifecycleScope.launch {
        viewLifecycleOwner.repeatOnLifecycle(
            Lifecycle.State.STARTED
        ) {
            launch {
                viewModel.uiState.collectLatest(::render)
            }
            launch {
                viewModel.events.collect(::showEvent)
            }
        }
    }
}
```

进入 `STARTED` 时，`repeatOnLifecycle` 为 block 创建新的 child scope；跌到 `STOPPED` 时取消这一轮 children，再次可见时重新启动。外层 job 在 View `DESTROYED` 时取消。多个 Flow 需要并行收集，所以分别放进 child `launch`；连续写两个 `collect` 会被第一个长期挂起。

Compose 中优先使用 `collectAsStateWithLifecycle()` 把 UI 状态收集绑定到 Lifecycle。一次性事件仍要明确消费和重放策略，不能靠把 `replay` 调大掩盖丢事件或重复消费。

### 3.3 callback bridge 要在取消时注销

`callbackFlow` 的资源边界由 `awaitClose` 表达。下面的代码用于把可注册/注销的 listener 转成冷 Flow：

```kotlin
fun SensorClient.events(): Flow<SensorEvent> = callbackFlow {
    val listener = object : SensorListener {
        override fun onEvent(event: SensorEvent) {
            trySend(event)
        }
    }

    register(listener)
    awaitClose {
        unregister(listener)
    }
}
```

collector 取消、上游失败或 channel 关闭时，`awaitClose` 的清理 block 都应解除注册。`trySend` 失败要按业务决定丢弃、计数或释放 element 自带的资源。若 element 持有需要 `close()` 的句柄，可使用带 `onUndeliveredElement` 的 Channel 设计资源回收，避免取消和缓冲竞态造成句柄滞留。

`produce`/`produceIn` 返回 `ReceiveChannel`。若 consumer 提前退出且 owner scope 仍活跃，应取消 channel；owner scope 被取消时，producer 会随结构化关系退出。单看“channel 是否 close”不能判定泄漏，关键仍是 producer job、consumer job 和底层资源是否终止。

`flatMapMerge` 的并发 child 会随下游取消而取消，但并发度会影响同时活跃的上游数量和缓冲规模。把 `concurrency`、buffer capacity 与 owner 生命周期一起监控，才容易区分合法并发与任务积压。

## 4. Dispatcher 管线程，scope 管任务

### 4.1 三个常用 dispatcher 的 Android 实现

| Dispatcher | 1.11.0 实现要点 | 适用任务 | 主要风险 |
| --- | --- | --- | --- |
| `Main` | Android `HandlerContext`，向主 Looper 的异步 Handler 投递 | UI 状态与短小主线程操作 | 阻塞、长计算、消息队列积压 |
| `Default` | `CoroutineScheduler` 共享 worker，CPU 并行度接近核心数且至少 2 | CPU 密集计算 | 阻塞 I/O 占住 CPU permit |
| `IO` | 与 Default 共享线程资源的弹性 view，默认并行限制为 `max(64, cores)` | 阻塞 I/O | 大量阻塞任务与 elastic views 扩大并行线程 |

`Dispatchers.Main.immediate` 在已经位于目标 Looper 时可以直接执行，避免一次 `Handler.post`；它也会带来同步重入语义，不能只为减少一次调度就全量替换。

`Dispatchers.IO.limitedParallelism(n)` 创建的是 dispatcher view，不需要 `close()`。IO 的 view 具有弹性，各 view 的 parallelism 之和不受 IO 默认并行值约束。它限制同时执行的 task 数，不保证固定使用某几条线程，也不限制挂起协程的数量。

Default 与 IO 共享调度器线程，`withContext(Dispatchers.IO)` 从 Default 进入时不保证发生一次 OS 线程切换。dispatcher 切换的工程成本还包括队列等待、任务粒度和上下文 element，不能只用“协程切换比线程切换快”的固定数字评估。更完整的调度与背压分析见 [8.6 Kotlin Coroutine 性能实践](../../part2-performance/ch08-responsiveness/06-coroutine-performance.md)。

### 4.2 限并行不等于限业务并发

`limitedParallelism(1)` 只保证同一时刻最多一段代码在线程上执行。一个协程挂起后，另一个协程可以进入，因此它不是跨挂起点的互斥锁。

下面的代码分别限制 CPU 图片处理的并行执行，以及跨挂起网络请求的业务并发：

```kotlin
private val imageDispatcher =
    Dispatchers.Default.limitedParallelism(
        parallelism = 2,
        name = "image-decode"
    )

private val requestGate = Semaphore(permits = 8)

suspend fun decode(bytes: ByteArray): Bitmap =
    withContext(imageDispatcher) {
        decodeBitmap(bytes)
    }

suspend fun fetch(request: Request): Response =
    requestGate.withPermit {
        withContext(Dispatchers.IO) {
            blockingClient.execute(request)
        }
    }
```

图片处理每次占用 CPU 时最多并行 2 个；`Semaphore` permit 则跨 `withContext` 和挂起点持有，把 in-flight 请求限制在 8 个。数据库连接池、服务端配额等资源应以 `Semaphore` 或资源池本身限流，不要从 dispatcher 线程数间接推断。

如果通过 `ExecutorService.asCoroutineDispatcher()` 创建独立 dispatcher，owner 结束时要关闭返回的 `ExecutorCoroutineDispatcher`。公共的 `Dispatchers.Default`、`IO`、`Main` 不能由业务关闭。

### 4.3 协程没有独立的 Linux 调度优先级

Android 内核调度的是线程。协程恢复到哪个 worker，就临时继承该 worker 的 nice、cgroup 和调度属性。在线程池协程中调用 `Process.setThreadPriority()` 会修改可复用 worker；后续无关任务也可能继承该值，协程换 worker 后又失去预期。

需要稳定线程属性的组件应使用有界的专用 executor，并在 ThreadFactory 中设置线程属性，再把它转成 dispatcher。相关线程必须由 owner 关闭并纳入 [20.19](./19-thread-leak-anonymous-thread-monitoring.md) 的 task/线程池监控。

## 5. Android 上不能依赖全局协程枚举

### 5.1 `kotlinx-coroutines-debug` 的 JVM agent 不支持 ART

`kotlinx-coroutines-debug` 的 `DebugProbes.install()` 依赖 ByteBuddy 和 Java Instrument API。1.11.0 的官方 README 明确说明 Android Runtime 不支持所需的 Instrument API，打包到 Android 项目还可能遇到资源合并问题。

在 `kotlinx.coroutines 1.11.0` 的公开 API 与源码中，也没有面向 Android 应用的稳定 `CoroutineTracing` 或 `correlate()` 接口。这些名称不能作为“1.7+ 已提供”的版本结论。

因此，以下对象不能作为 Android 线上监控基础：

- `DebugProbes.dumpCoroutinesInfo()`；
- 没有公开出处的 `DebugCoroutinesInfo`、`correlate()`；
- `CoroutineStackFrame`；
- `kotlinx.coroutines.internal.recoverStackTrace`；
- 替换 `DebugProbesKt.bin` 或探测 continuation 内部字段。

`CoroutineStackFrame` 属于 Kotlin continuation 调试协议，`recoverStackTrace` 在 coroutines 源码中是 internal 实现。它们的对象布局和调用时机没有应用级兼容承诺，R8、Kotlin 编译器或 coroutines 升级都可能改变行为。

Android Studio/Kotlin 插件的 Coroutine Debugger 适合 debuggable 构建：暂停进程后查看运行/挂起状态、creation stack 和 coroutine dump。它不是常驻线上数据源。

`-Dkotlinx.coroutines.debug` 会在 JVM 调试模式下把 coroutine ID/`CoroutineName` 附加到执行线程名，便于日志分析。它需要在运行时初始化前配置，也不会生成可供生产环境遍历的 `Job` 注册表，更不会让 Perfetto 自动理解父子 `Job`。

### 5.2 线上方案从受控创建入口登记

线上不追求拦截所有 continuation，而是给关键 root scope 和 operation 建立显式注册表。至少记录：

- 有界的 operation/owner ID；
- 创建、开始执行、完成的单调时钟；
- 完成原因：success、cancel、failure；
- dispatcher 类别；
- active 数、最长 age、P50/P95/P99 时长；
- owner end 到 job completion 的取消延迟；
- 同一 owner/operation 的峰值基数；
- 诊断灰度下采样的创建栈或调用点 ID。

下面的 helper 用公开 API 登记一个 operation，并用 `androidx.tracing` 1.3.0 的 suspend `traceAsync` 在 Perfetto 中标出逻辑时段：

```kotlin
private val nextTraceCookie = AtomicInteger()

interface CoroutineMonitor {
    fun onCreated(
        cookie: Int,
        owner: String,
        operation: String,
        scheduledAtNs: Long
    )

    fun onStarted(cookie: Int, startedAtNs: Long)

    fun onCompleted(
        cookie: Int,
        completedAtNs: Long,
        cause: Throwable?
    )
}

fun CoroutineScope.launchTracked(
    owner: String,
    operation: String,
    monitor: CoroutineMonitor,
    block: suspend CoroutineScope.() -> Unit
): Job {
    require(owner.matches(Regex("[a-z0-9._-]{1,32}")))
    require(operation.matches(Regex("[a-z0-9._-]{1,48}")))

    val cookie = nextTraceCookie.incrementAndGet()
    val scheduledAtNs = SystemClock.elapsedRealtimeNanos()
    monitor.onCreated(cookie, owner, operation, scheduledAtNs)

    return launch(CoroutineName("$owner/$operation")) {
        monitor.onStarted(
            cookie,
            SystemClock.elapsedRealtimeNanos()
        )
        traceAsync("co:$owner/$operation", cookie) {
            block()
        }
    }.also { job ->
        job.invokeOnCompletion { cause ->
            monitor.onCompleted(
                cookie,
                SystemClock.elapsedRealtimeNanos(),
                cause
            )
        }
    }
}
```

`onCreated` 到 `onStarted` 是调度等待，`onStarted` 到 `onCompleted` 是包含挂起时间的逻辑持续时间，不是 CPU time。`invokeOnCompletion` 也能覆盖尚未开始就被取消的 job。监控实现必须线程安全、无阻塞、不抛异常，并在 completion 后移除 active 记录；否则监控器会成为新的泄漏源。

创建栈通过 `Throwable().stackTrace` 采集成本较高，只应在低比例灰度或异常触发后启用。更稳的做法是在调用点传入编译期常量 ID，再用版本与 mapping 文件离线还原。

### 5.3 `ThreadContextElement` 不适合充当全量 hook

`ThreadContextElement.updateThreadContext()`/`restoreThreadContext()` 会在 coroutine resume 和 thread switch 周围执行，适合传播 MDC、trace token 等少量线程上下文。实现必须处理恢复顺序和并发，不应在其中 unwind、写文件或上传网络。

它也看不到没有携带该 element 的协程，不能提供全局创建/完成计数。用它传播已存在的 trace ID 可以，用它替代 operation 注册表会留下大量盲区。

## 6. Perfetto 中怎样读协程

Android 17 不会自动把 `CoroutineName` 变成 Perfetto slice。系统 trace 默认能看到：

- 主线程与 `DefaultDispatcher-worker-*` 的 sched 状态；
- 主 Looper 上的运行片段；
- CPU 频率、唤醒和线程迁移；
- 应用主动写入的同步/异步 trace event。

suspend block 可能跨线程恢复，所以同步 `trace {}` 不能包住可能挂起并换线程的完整操作；同步 section 要在同一线程成对结束。`androidx.tracing` 的 suspend `traceAsync` 使用 name+cookie 配对，适合表示跨挂起的逻辑时段。

异步 slice 的长度包含排队、delay、I/O 等待和 CPU 执行。判断性能问题时要将它和 sched/线程 slice 对齐：

- async slice 很长、CPU 很短：多半在等待 I/O、timer、lock 或 dispatcher；
- Main 上连续 CPU slice 很长：主线程工作过重；
- scheduled→started 很长：dispatcher、executor 或 Main queue 积压；
- 大量同名重叠 async slice：缺少去重、并发上限或旧请求取消；
- owner end 后 slice 仍持续：生命周期违约候选。

Android 17 对 target 37 应用启用新的无锁 `MessageQueue` 实现。`Dispatchers.Main` 在需要 dispatch 时仍通过 Android Handler 投递，`Job` 与 Lifecycle 语义不变。应用若反射 `MessageQueue` 私有字段会有兼容风险；不要把内部队列结构当成协程监控 hook。

Android Studio 的 Java/Kotlin method tracing 会做运行时插桩，官方建议把记录限制在约 5 秒内。它适合短窗口定位方法耗时，不能拿插桩后的耗时当生产基线。采样型 CPU profiler 与 Perfetto 更适合观察较长场景。

## 7. Compose 的 scope 边界

`LaunchedEffect(keys...)` 进入 Composition 时启动 coroutine；key 改变时取消旧任务并启动新任务；离开 Composition 时取消。`rememberCoroutineScope()` 返回绑定到调用点的 scope，适合点击、动画等事件回调，调用点离开 Composition 时取消。

下面的代码区分“由状态驱动的 effect”和“由用户事件启动的任务”：

```kotlin
@Composable
fun DetailScreen(
    itemId: String,
    viewModel: DetailViewModel,
    onLoadError: (Throwable) -> Unit
) {
    val currentOnLoadError by rememberUpdatedState(onLoadError)
    val eventScope = rememberCoroutineScope()

    LaunchedEffect(itemId) {
        runCatching {
            viewModel.ensureLoaded(itemId)
        }.onFailure { error ->
            if (error is CancellationException) throw error
            currentOnLoadError(error)
        }
    }

    Button(
        onClick = {
            eventScope.launch {
                viewModel.refresh(itemId)
            }
        }
    ) {
        Text("Refresh")
    }
}
```

`itemId` 变化会重启加载，`rememberUpdatedState` 更新 callback 而不因 callback 实例变化重启 effect。点击任务使用 composition-aware scope。代码显式重抛 `CancellationException`，避免 `runCatching` 把正常取消改写成失败处理。

高频变化或不稳定的 key 会制造反复取消/重启，表现为请求抖动和重复分配。它未必造成泄漏，却会造成性能与网络浪费。需要跨页面或跨 configuration change 的工作应提升到合适的 `ViewModel`/repository owner，不要把 Compose scope 存入单例。

## 8. 协程如何引发 ANR

`suspend` 只表示函数可以挂起，不保证它不会阻塞。以下行为仍会卡住主线程：

- 在 `Dispatchers.Main` 上执行长循环、解码、压缩或大量序列化；
- 在 suspend 函数中调用阻塞 I/O，却没有切换到合适 dispatcher；
- 在主线程调用 `runBlocking` 等待 child；
- 持有 monitor/lock 后挂起，或恢复后争用主线程所需的锁；
- 大量 Main resume 同时入队，形成消息队列积压；
- `NonCancellable` cleanup 无边界运行。

`delay` 会挂起并让出线程，`Thread.sleep` 会占住当前线程。`withTimeout` 通过取消 coroutine 实现；它不能自动中断不响应取消的阻塞调用。对支持线程中断的 Java 阻塞 API 可使用 `runInterruptible(Dispatchers.IO)`，对 socket、stream、codec 等资源还要提供 close/cancel 通路。

CPU 密集循环应放到 `Dispatchers.Default`，并在合适粒度调用 `ensureActive()` 或使用本身可取消的操作。检查过密会增加开销，检查过疏会拉长取消延迟，需要按一次迭代成本实测。

ANR trace 记录的是发生时各线程栈。协程可能在此刻挂起而没有连续业务栈，因此还要结合 operation 注册表、async trace 和 dispatcher 排队时长。不能只凭 `DefaultDispatcher-worker` 名称归因。

## 9. Android 17 的后台边界

Android 17 没有一项“挂起函数后台特权”。协程不会提高进程重要性，也不能保证任务在应用离开可见状态、进程被回收或设备重启后完成。

按任务契约选择载体：

- 仅在当前界面有意义：View/Composition scope；
- ViewModel 存活期间有意义：`viewModelScope`；
- 进程活着时可尽力完成：application scope，并接受进程退出；
- 需要跨退出或重启可靠执行：WorkManager、JobScheduler 或对应领域 API；
- 用户可感知、长时间且必须立即运行：满足类型与权限要求的前台服务或合适的系统专用 API。

WorkManager 可以在 `CoroutineWorker` 内使用协程，但可靠性来自 WorkManager 的调度与持久化，不来自 coroutine。后台限制测试要验证进程退出、约束变化、重试和幂等，不能只在前台等待一个 `delay()` 完成。

## 10. 告警算法与测试

### 10.1 常驻指标

按 owner/operation 聚合，不上传任意 coroutine 名：

- created、started、completed、cancelled、failed；
- active gauge 与峰值；
- scheduled→started 延迟；
- operation duration；
- owner end→completion 取消延迟；
- timeout 和重复 key 数；
- Flow subscriber 数、sharing scope 状态；
- dispatcher/executor queue、active worker 与拒绝数。

线程数只能作为旁证。active coroutine 上升但线程平稳，可能是挂起任务、Flow collector 或缓冲积压；线程上涨而 tracked coroutine 平稳，应查 executor、SDK 或 raw pthread。

### 10.2 泄漏候选判定

一次候选事件至少满足：

1. owner 已结束，或 operation 超过其 deadline；
2. job 仍 active，或底层 listener/channel/resource 仍注册；
3. 已等待按任务类型设定的取消宽限期；
4. 同一版本和场景能重复出现，或群体分位数明显回归；
5. 监控记录没有因采样、进程前后台或缺测产生误判。

不要把所有超过固定 30 秒的 coroutine 归为泄漏。WebSocket 可能预期长期存活，页面请求则可能 10 秒已经异常。阈值属于 operation 契约。

### 10.3 自动化验证

单元和集成测试应覆盖：

- owner close/destroy 后 root job 进入 completed；
- `repeatOnLifecycle` 在 STOP 时取消当轮 collector，在 START 时只恢复一组；
- key 变化后旧 `LaunchedEffect` 不再写 UI；
- callbackFlow 取消后 listener 被注销一次；
- `shareIn/stateIn` 的 `SharingStarted` 策略与产品预期一致；
- timeout 后底层阻塞资源也停止；
- failure 在普通 scope 与 supervisor scope 中按预期传播；
- 自建 executor/dispatcher 被关闭；
- monitor completion 会删除 active 记录。

`runTest`、`TestScope` 和 Lifecycle test utilities 可以控制虚拟时间与状态切换。Lifecycle 2.8 起可向 `ViewModel` 注入 test scope，减少替换 `Dispatchers.Main` 的隐式依赖。测试结束时还应检查 owned root 的 `children`，但 `Job.children` 只覆盖该 root 的结构树，不是进程全局枚举。

## 11. 评审清单

- 每个长期 scope 是否有清晰 owner 和取消入口？
- Fragment 是否把 View 相关任务放进 `viewLifecycleOwner.lifecycleScope`？
- UI Flow 是否通过 `repeatOnLifecycle` 或 `collectAsStateWithLifecycle` 管理可见性？
- `collectLatest` 是否被误当成 Lifecycle 取消？
- `shareIn/stateIn` 的 scope 和 `SharingStarted` 是否符合生产者寿命？
- `callbackFlow` 是否在 `awaitClose` 中解除注册？
- 是否有 `GlobalScope`、未关闭的 `MainScope()` 或临时 `CoroutineScope(...)`？
- 是否向 `launch/async` 直接传入新 `Job`，导致 parent 关系断开？
- `CancellationException` 是否被 `catch(Throwable)`/`runCatching` 吞掉？
- 阻塞 API 是否能在 cancel/timeout 时中断或关闭？
- `limitedParallelism` 是否被误当成跨挂起点的并发锁？
- IO elastic views 的并行上限之和是否经过压测？
- 自建 executor dispatcher 是否随 owner 关闭？
- 线上监控是否只使用公开 API，并避免 continuation 私有反射？
- Perfetto slice 是否区分逻辑持续时间、调度等待和 CPU time？
- Android 17 后台任务是否使用与可靠性契约匹配的系统 API？

## 12. 源码与官方资料

### 验证基线

- [kotlinx.coroutines 1.11.0 源码](https://github.com/Kotlin/kotlinx.coroutines/tree/1.11.0)
- [Android dispatcher `HandlerDispatcher.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/ui/kotlinx-coroutines-android/src/HandlerDispatcher.kt)
- [`CoroutineScope.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/CoroutineScope.kt)
- [`Supervisor.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/Supervisor.kt)
- [`kotlinx-coroutines-debug` Android 限制](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-debug/README.md#debugger-and-android)

### Kotlin 与 Android 指南

- [Kotlin：Coroutine basics 与 structured concurrency](https://kotlinlang.org/docs/coroutines-basics.html)
- [Kotlin：Cancellation and timeouts](https://kotlinlang.org/docs/cancellation-and-timeouts.html)
- [Kotlin：`Dispatchers.IO`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)
- [Kotlin：`limitedParallelism`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-dispatcher/limited-parallelism.html)
- [Kotlin：`shareIn`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/share-in.html)
- [Android：Lifecycle-aware coroutines](https://developer.android.com/topic/libraries/architecture/views/coroutines-views)
- [AndroidX Lifecycle release notes](https://developer.android.com/jetpack/androidx/releases/lifecycle)
- [Android：StateFlow 与 SharedFlow](https://developer.android.com/kotlin/flow/stateflow-and-sharedflow)
- [Compose：Side-effects](https://developer.android.com/develop/ui/compose/side-effects)
- [AndroidX Tracing `traceAsync`](https://developer.android.com/reference/kotlin/androidx/tracing/package-summary)
- [Android 17：MessageQueue behavior change](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Android：Background task scheduling](https://developer.android.com/develop/background-work/background-tasks/persistent)

协程治理的关键对象始终是 owner、`Job` 和资源释放协议。线程与 Perfetto 帮助解释“代码何时得到 CPU”，Lifecycle 和结构化并发解释“任务何时应该结束”，显式 operation 监控则把这两类证据关联起来。
