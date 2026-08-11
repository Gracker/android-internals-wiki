---
title: "Android 线程模型与调度器选型实战"
chapter: "8.19"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['thread-model', 'coroutine-dispatcher', 'executor-service', 'handler-thread', 'thread-pool']
related_chapters: ['8.06', '8.17', '21.16']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1; kotlinx.coroutines 1.9.x; developer.android.com"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/kotlin/coroutines/coroutines-adv"
  - type: aosp
    path: "frameworks/base/core/java/android/os/HandlerThread.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerformanceHintManager.java"
  - type: blog
    path: "kotlinx.coroutines源码 Dispatchers.kt / CoroutineScheduler.kt"
gap_source: "素材驱动"
---

# 8.19 Android 线程模型与调度器选型实战

协程不会消除线程。协程在 suspend 时保存 continuation，恢复时由 `CoroutineDispatcher` 决定在哪个线程执行；进入内核调度后，Linux 只认识线程、调度策略、nice、cgroup、uclamp 和 CPU affinity。

选型时不要从“协程、Executor、HandlerThread 谁更快”开始。先确认任务会不会阻塞线程、能否并行、是否需要 Looper、生命周期由谁持有，以及下游资源能承受多少并发。平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，协程库按 `kotlinx.coroutines` 1.11.0 校验，kernel 按 `android17-6.18-2026-06_r6` 校验。

## 1. 一张选型表

| 任务特征 | 推荐起点 | 主要约束 |
|---|---|---|
| 更新 View、处理主线程限定 API | `Dispatchers.Main` / `.immediate` | 单线程；不能放长计算或阻塞 I/O |
| 可分片 CPU 计算 | `Dispatchers.Default` | 并行度受 CPU permit 限制；要保留 UI 和系统余量 |
| 文件、阻塞 socket、旧数据库驱动 | `Dispatchers.IO` | 阻塞并发要受连接池、FD、内存约束 |
| 同一数据源最多 N 个调用 | `limitedParallelism(N)` | 限制同时执行数，不限制待执行任务数量 |
| 必须复用第三方 `ExecutorService` | `asCoroutineDispatcher()` | owner 负责 shutdown/close 和拒绝策略 |
| API 明确要求 Looper/Handler | `HandlerThread` 或已有 Looper | 单线程、单 MessageQueue、必须退出 |
| 同一时刻只执行一个 continuation 片段 | 合适 dispatcher 的 `limitedParallelism(1)` | suspend 后其他协程可以进入，不等于整个操作互斥 |
| 包含 suspend 的完整状态操作要互斥 | `Mutex` 或 actor/Channel | 明确公平性、失败、取消和消息容量 |
| native/第三方 API 要求稳定 TID | 明确 owner 的单线程 Executor 或 HandlerThread | suspend 后仍可能执行其他任务；确认线程死亡恢复 |
| 跨重启的延迟后台工作 | WorkManager / JobScheduler | 这不是进程内 dispatcher 问题 |

“挂起 I/O”与“阻塞 I/O”要分开。Room、Retrofit/OkHttp 或其他库可能已在内部 executor 上工作，suspend API 也可能通过回调恢复，不需要外层再包一层 `Dispatchers.IO`。只有调用会占住当前线程等待时，IO dispatcher 才是在隔离阻塞。

## 2. `Dispatchers.Default`、`IO` 与 `Main`

### 2.1 Default 与 IO 共用 scheduler

1.11.0 的 JVM 实现由 `DefaultScheduler` 持有 `CoroutineScheduler`。它有 worker 本地队列、global CPU queue、global blocking queue 和 work stealing。CPU task 必须取得 CPU permit，permit 数默认为可用处理器数且至少为 2；blocking task 会释放 CPU permit，scheduler 可补充 worker，避免阻塞任务耗尽 CPU task 的执行名额。

这不表示 Default 和 IO 各自拥有固定大小的 `ThreadPoolExecutor`：

- `CoroutineScheduler` 是独立实现，不继承 `ThreadPoolExecutor`；
- `Dispatchers.Default` 提交 non-blocking task；
- `Dispatchers.IO` 经 `UnlimitedIoScheduler` 提交 blocking task；
- 两者共享 worker 和资源；
- 从 Default 进入 IO 时，库会尽量复用当前 worker，不承诺发生物理线程切换。

### 2.2 IO 的 64 是默认并行度

`Dispatchers.IO` 的默认 parallelism 是 `max(64, availableProcessors)`，可由 `kotlinx.coroutines.io.parallelism` 系统属性配置。它限制同时执行的 IO task，不等于进程最多只能存在这些协程线程。

IO 的 `limitedParallelism()` 具有弹性。下面两个 view 共享 scheduler，却不受 IO 默认 64 的总量限制。

```kotlin
val sqliteDispatcher = Dispatchers.IO.limitedParallelism(4, "sqlite")
val legacyHttpDispatcher = Dispatchers.IO.limitedParallelism(16, "legacy-http")
```

峰值 blocking parallelism 可能接近 IO 默认额度与各个弹性 view 额度之和。每新增一个 view 都要核对数据库连接数、HTTP dispatcher 限制、文件描述符、响应体内存和服务端限流。

`limitedParallelism(N)` 只保证同一 view 最多有 N 个 task 同时执行。大量生产者仍能把任务排在 dispatcher 前面；需要提交侧背压时，应再使用有界 `Channel`、`Semaphore` 或业务队列。

### 2.3 Main 与 `Main.immediate`

Android 的 `Dispatchers.Main` 由 `HandlerContext` 基于 main Looper 的 async Handler 实现。普通 Main dispatch 会 `handler.post(block)`；`Main.immediate` 在当前线程已经是该 Handler 的 Looper 时，可在当前调用栈继续执行。

`.immediate` 减少一次投递，也改变执行顺序和重入边界。代码若依赖“稍后执行”，仍应显式 post 或使用普通 Main。不能把 `.immediate` 当作通用微优化。

下面的函数只把 UI 更新限制在主线程，数据准备应在调用前完成。

```kotlin
suspend fun showUser(model: UserUiModel) {
    withContext(Dispatchers.Main.immediate) {
        userName.text = model.name
        avatar.setImageDrawable(model.avatar)
    }
}
```

从主线程调用时，这段代码可能同步执行；从其他线程恢复时，它仍会投递到 main Handler。可重入风险要由调用者和状态模型负责。

### 2.4 Default 与 IO 的典型用法

阻塞文件读取和 CPU 解析应按阶段切换。

```kotlin
suspend fun loadIndex(path: Path): SearchIndex {
    val bytes = withContext(Dispatchers.IO) {
        Files.readAllBytes(path)
    }
    return withContext(Dispatchers.Default) {
        parseAndBuildIndex(bytes)
    }
}
```

两个阶段顺序相关，因此没有必要用两个 `async`。若文件 API 已提供异步回调或 suspend 适配器，应检查实现线程，再决定是否保留 IO 切换。

## 3. 并行度按资源选，不按公式照抄

### 3.1 CPU workload

CPU task 的起点可以参考可用处理器数，但 Android 设备存在异构 CPU、热降频、前台渲染、音频和系统服务竞争。`availableProcessors()` 不能告诉应用当前有几个大核，也不能保证这些 CPU 都供应用独占。

建议：

- 大任务按可取消的 chunk 切分；
- 以端到端时延、CPU time、能耗和温度比较 parallelism；
- 前台交互任务给主线程、RenderThread 和系统工作留余量；
- 用 `Dispatchers.Default.limitedParallelism(N)` 限制某一批高成本计算；
- 避免多个库各自创建“CPU 核心数”大小的独立池。

下面的 dispatcher 把图片解码的同时执行数限制为 2，线程仍来自 Default scheduler。

```kotlin
private val imageDecodeDispatcher =
    Dispatchers.Default.limitedParallelism(2, "image-decode")

suspend fun decode(bytes: ByteArray): Bitmap =
    withContext(imageDecodeDispatcher) {
        decodeBitmap(bytes)
    }
```

`2` 只是该应用的实验起点。低端机、不同图片大小和并发滚动场景都要重新测量。

### 3.2 Blocking I/O workload

阻塞并发的上限通常来自下游资源：

- 数据库连接池大小；
- HTTP client 的全局与 per-host 限制；
- 服务端 QPS/并发限制；
- 文件描述符和 socket 数；
- 每个请求的 buffer、response 和解析内存；
- 超时、重试造成的瞬时放大。

`Ncpu × (1 + wait/compute)` 可以帮助理解等待比例，却很难覆盖移动设备上的网络抖动、热状态和共享资源，不能直接作为生产线程数。

### 3.3 串行 workload

串行状态机要区分“代码片段不并行”和“整个操作互斥”：

- `limitedParallelism(1)`：同一时刻最多执行一个位于两次 suspension 之间的代码片段，并在片段之间建立 happens-before；一个协程 suspend 后，其他协程可以进入；
- `Mutex` 或 actor/Channel：适合把包含 suspension 的完整状态操作纳入互斥或消息顺序；
- 单线程 Executor/HandlerThread：适合线程亲和、ThreadLocal、Looper 或第三方 API 的固定线程要求。

`limitedParallelism(1)` 不承诺整个 coroutine run-to-completion，也不应当作 Mutex；它还不保证每次执行都落在同一物理线程。要求 TID 稳定的 native context、EGL context 或 ADPF session 不能只靠这个 view。

## 4. 自定义 Executor 的所有权

### 4.1 `asCoroutineDispatcher()` 做了什么

`ExecutorService.asCoroutineDispatcher()` 返回 `ExecutorCoroutineDispatcher`，dispatch 路径调用 `executor.execute()`。若底层是 `ScheduledExecutorService`，`delay` 和 timeout 可使用它的 schedule；普通 Executor 的时间管理会使用协程库的内部计时设施，恢复任务仍回到该 Executor。

提交被 `RejectedExecutionException` 拒绝时，1.11.0 实现会取消受影响的 Job，并把任务交给 `Dispatchers.IO` 运行清理代码。这个 fallback 不能把拒绝伪装成成功；调用方仍要处理取消，队列容量与拒绝策略仍属于 owner 的设计。

### 4.2 一个有明确 owner 的线程池

下面的类拥有 Executor 和 dispatcher，并在 worker 入口设置 Android nice。不要在 ThreadFactory 的创建线程上直接调用 `Process.setThreadPriority()`，那会改到创建者线程。

```kotlin
class LegacyDbPool : Closeable {
    private val threadId = AtomicInteger()

    private val executor = Executors.newFixedThreadPool(2) { task ->
        Thread(
            {
                Process.setThreadPriority(
                    Process.THREAD_PRIORITY_BACKGROUND
                )
                task.run()
            },
            "legacy-db-${threadId.incrementAndGet()}",
        )
    }

    val dispatcher: ExecutorCoroutineDispatcher =
        executor.asCoroutineDispatcher()

    override fun close() {
        dispatcher.close()
    }
}
```

`dispatcher.close()` 会对底层 `ExecutorService` 调用 shutdown。Owner 还要定义：何时停止接单、等待多久、未完成任务是否持久化，以及进程退出前是否允许直接丢弃。

固定线程数不等于有界队列。`Executors.newFixedThreadPool()` 使用无界 `LinkedBlockingQueue`；生产速度长期高于消费速度时，任务对象仍会持续占内存。需要有界策略时，应显式构造 `ThreadPoolExecutor` 并设计 rejection 对业务的含义。

### 4.3 何时值得自建

常见理由包括：

- 第三方库只接受 Executor，且需要与它共享并发额度；
- native/runtime 要求稳定线程或固定 ThreadLocal；
- 需要有界队列、业务拒绝策略或专门隔离故障；
- 线程命名和生命周期有独立运维要求；
- ADPF workload 需要一组长期稳定 TID。

只为了“在 Perfetto 里名字好看”就创建新池，通常得不偿失。`limitedParallelism(N, "name")`、应用 trace 和 `CoroutineName` 已能解决一部分可观测性需求。

## 5. HandlerThread 只服务 Looper 约束

Android 17 的 `HandlerThread.java` 文档已经写明：仅在必须使用 Handler API 且需要一个新的 Looper thread 时使用；新版 API 同时支持 Executor 时，优先传入 Executor。

HandlerThread 的运行结构是 `Thread → Looper.prepare() → MessageQueue → Looper.loop()`。它带来这些约束：

- 一个 HandlerThread 对应一个常驻线程；
- MessageQueue 通过单锁保护入队和出队；
- 消息按 `when` 排序，延迟消息多时插入成本与位置有关；
- 长 callback 会阻塞后续全部消息；
- 多个生产者同时 post 会竞争同一队列锁；
- 退出要调用 `quit()` 或 `quitSafely()`。

下面的 owner 适合只能接收 Handler 的旧 API。

```kotlin
class CameraCallbackThread : Closeable {
    private val thread = HandlerThread(
        "camera-callback",
        Process.THREAD_PRIORITY_DISPLAY,
    ).apply { start() }

    val handler = Handler(thread.looper)

    override fun close() {
        thread.quitSafely()
    }
}
```

`quitSafely()` 会处理已经到期的消息，再退出 Looper；未来延迟消息不会全部执行。测试或服务 teardown 若要求确定线程已结束，应在非 HandlerThread 自身的线程上再 `join()`，并设置超时。

需要在 Handler 上运行协程时可使用 `handler.asCoroutineDispatcher()`。Handler 已退出导致 post 失败时，Job 会取消，并由 IO dispatcher 执行清理路径；这仍是生命周期错误，应修复 owner 的关闭时序。

不需要 Looper 的严格串行任务优先使用单线程 Executor、actor/Channel 或 `limitedParallelism(1)`，选择取决于线程亲和与队列需求。

## 6. 线程优先级、task profile 与内核调度

### 6.1 `Process.setThreadPriority` 和 `Thread.setPriority`

两套 API 的语义不同：

| API | 数值范围 | 保存位置与继承 |
|---|---|---|
| `Process.setThreadPriority()` | Linux nice：-20 到 19 | 直接设置当前/指定 TID；不更新 Java cached priority；Java 子线程不继承该调用 |
| `Thread.setPriority()` | Java priority：1 到 10 | 更新 Java Thread 的 priority 语义，新建 Java 子线程可继承 |

`Process.setThreadPriority(tid, nice)` 可能因 TID、权限或目标 nice 不允许而抛异常。普通应用不要把主线程设为 -19，也不要假设提优先级能绕过系统策略。低优先级后台 worker 使用 `THREAD_PRIORITY_BACKGROUND` 更常见。

Android 文档还提示：对另一个线程调用 `Process.setThreadPriority()` 设置非负 nice 时，runtime 在少数情况下可能按 Java cached priority 重置它。需要 Java 继承语义时使用 `Thread.setPriority()`，需要精确 Android nice 常量时在目标线程入口调用 `Process.setThreadPriority()`。

### 6.2 nice 只是调度输入之一

Android 17 通过 libprocessgroup 的 task profiles 配置 cpu/cpuset controller、uclamp 和其他资源属性。`task_profiles.json` 定义了 `HighPerformance`、`MaxPerformance`、background cpuset、`UClampMin`、`UClampMax` 等动作；OEM 可以用覆盖文件修改配置。

因此：

- nice 较高优先级不能保证运行在大核；
- background/top-app 组变化会改变可用 CPU 与调度权重；
- uclamp 会影响调度器看到的利用率约束；
- 进程状态、热限制和系统负载仍会改变结果；
- 不应把某台设备的 `/dev/cgroup/...` 路径硬编码进应用逻辑。

这些设置通常由 framework 和系统 task profile 管理。普通应用应通过正确生命周期、线程优先级常量、ADPF 和系统调度 API表达意图。

## 7. 结构化并发管理任务，不管理物理线程

### 7.1 取消是协作式的

父 Job 取消会向子 Job 传播。挂起函数在可取消 suspend 点检查状态；CPU 循环要主动检查，阻塞式第三方调用是否响应取消取决于适配器能否关闭资源或中断等待。

下面的计算按 chunk 检查取消，避免每个元素都产生检查成本。

```kotlin
suspend fun hashAll(chunks: List<ByteArray>): List<Hash> =
    withContext(Dispatchers.Default) {
        buildList(chunks.size) {
            for (chunk in chunks) {
                ensureActive()
                add(hash(chunk))
            }
        }
    }
```

`ensureActive()` 的间隔要由单个 chunk 最坏执行时长决定。若一个 chunk 本身可运行几百毫秒，还要在 chunk 内继续分段。

捕获 `CancellationException` 时应重新抛出，除非代码正在执行明确的清理。阻塞 I/O 需要在 `invokeOnCancellation`、`finally` 或库提供的 cancellation hook 中关闭 socket、stream、cursor 等资源。

### 7.2 Scope 不会自动关闭 Executor

结构化并发负责 Job 的父子关系、等待和异常传播，不拥有外部 Executor、HandlerThread、socket 或 native handle。Scope 结束后：

- 标准 Dispatchers 继续为进程内其他协程服务；
- 自定义 `ExecutorCoroutineDispatcher` 仍要由 owner close；
- HandlerThread 仍要 quit；
- callback API 仍要 unregister；
- 必须跨进程重启完成的任务要交给持久化 scheduler。

`supervisorScope` 只改变兄弟失败传播，不会让资源自动释放，也不会让失败任务继续符合业务一致性。

## 8. Android 17 r6 的 EEVDF 边界

Linux 从 6.6 开始把 fair scheduler 的选取逐步切换到 EEVDF。Android 17 的 r6 kernel 在 `kernel/sched/fair.c` 中使用 `pick_eevdf()`：

1. runnable entity 要满足 eligibility，也就是其 lag 表明仍应获得服务；
2. 在 eligible entity 中选择 virtual deadline 更早者。

nice 通过 task weight 影响虚拟时间推进和 deadline 计算。EEVDF 仍属于 fair scheduling 路径；“所有短任务都比长任务优先”会忽略 eligibility、weight、slice、唤醒抢占、cgroup、uclamp 和 CPU 拓扑。

协程库在用户态把 continuation 放入 worker queue；r6 kernel 再从 runnable 线程中选取。下面两层指标要分开：

| 层 | 代表等待 | 主要观测 |
|---|---|---|
| 协程 scheduler | continuation 已提交但尚未由 worker 运行 | 应用提交/开始时间、coroutine trace、worker queue 压力 |
| kernel scheduler | worker 已 runnable 但没有得到 CPU | Perfetto `sched`、`thread_state`、CPU 频率、cgroup/uclamp |

增加协程并发可能让更多 worker runnable，也可能只增加用户态排队。只有将任务提交时间、实际开始时间和 sched 状态放在同一 trace，才能区分两层。

## 9. PerformanceHintManager 与协程

### 9.1 API 版本

Android 17 / API 37 保留的公开 ADPF session 能力如下：

| API | 引入 API | 用途 |
|---|---:|---|
| `createHintSession(tids, target)` | 31 | 为一组相关线程创建 session |
| `updateTargetWorkDuration(long)` | 31 | 更新每个周期的目标 wall duration |
| `reportActualWorkDuration(long)` | 31 | 上报上一周期的实际 wall duration |
| `setThreads(int[])` | 34 | 替换 session 的线程集合 |
| `WorkDuration` 与结构化上报 | 35 | 上报周期起点、total、CPU、GPU duration |
| `setPreferPowerEfficiency(boolean)` | 35 | 表示 workload 可偏向能效调度 |

所有时间使用 `SystemClock.uptimeNanos()`。Session 方法会修改内部状态，调用方要自行同步。`createHintSession()` 可能返回 null，`setThreads()` 还要求 session 在前台且 TID 属于本应用。

### 9.2 适合 ADPF 的 workload

ADPF 面向有目标周期、持续重复、线程组稳定的 workload，例如游戏帧、音视频处理或持续图像管线。一次普通 `launch(Dispatchers.Default)` 可能在多次 resume 间迁移 worker；为每个短协程创建 session、每次 resume 调 `setThreads()` 会增加复杂度，也违背长期稳定线程的设计建议。

需要 ADPF 时，常见做法是：

- 使用已有稳定 render/engine threads；
- 或让一组明确 owner 的长期 Executor threads 承载周期工作；
- 每周期测量一次完整 wall duration；
- target 随产品帧预算或周期变化更新；
- session 与 worker 一起关闭。

下面的简化 owner 展示稳定单线程 session。构造和关闭会等待 worker，必须在非 UI、非 worker 线程执行。

```kotlin
class PeriodicHintWorker(
    manager: PerformanceHintManager,
    targetNanos: Long,
) : Closeable {
    private val executor = Executors.newSingleThreadExecutor()

    private fun uptimeNanosCompat(): Long =
        if (Build.VERSION.SDK_INT >= 35) {
            SystemClock.uptimeNanos()
        } else {
            System.nanoTime()
        }

    private val session: PerformanceHintManager.Session? =
        executor.submit<PerformanceHintManager.Session?> {
            manager.createHintSession(
                intArrayOf(Process.myTid()),
                targetNanos,
            )
        }.get()

    fun executeCycle(block: () -> Unit) {
        executor.execute {
            val started = uptimeNanosCompat()
            try {
                block()
            } finally {
                val elapsed =
                    (uptimeNanosCompat() - started).coerceAtLeast(1L)
                session?.reportActualWorkDuration(elapsed)
            }
        }
    }

    override fun close() {
        session?.let { s ->
            executor.submit { s.close() }.get()
        }
        executor.shutdown()
    }
}
```

这段代码展示 TID、周期测量和生命周期的关系，不是通用线程池封装。API 35 增加了 `SystemClock.uptimeNanos()`；API 31–34 的简单 duration 上报可用 `System.nanoTime()` 的差值。结构化 `WorkDuration` 的时间戳应使用 API 35 的 uptime 时钟。未捕获异常会让 Executor 替换 worker，此时 session 里的旧 TID 已失效；生产实现要捕获任务边界异常或重建 session，并处理初始化失败、队列背压、shutdown timeout、前后台切换和设备不支持 ADPF 的路径。

## 10. Channel、BlockingQueue 与线程泄漏

### 10.1 Channel 与 BlockingQueue

| 维度 | `Channel` | `BlockingQueue` |
|---|---|---|
| 等待方式 | sender/receiver 挂起，不占住线程 | `put/take` 阻塞调用线程 |
| 容量 | rendezvous、有界、无界、conflated | 有界或无界，取决于实现 |
| 关闭 | `close` 并携带可选 cause | 没有统一 close，常用 sentinel/外部状态 |
| 取消 | 与协程 Job 配合 | Future/interruption/外部标志 |
| 适用 | 协程生产消费 | Java 线程、遗留库、明确阻塞线程模型 |

两者都能表达有界队列；不能写成“BlockingQueue 没有背压”。Java 标准库也没有通用 `Channel.asBlockingQueue()`，跨模型适配要显式定义阻塞、关闭、取消和异常语义。

### 10.2 泄漏与过量线程

诊断时关注：

- `/proc/self/task` 的线程数量和名称；
- Perfetto 中长时间空闲却常驻的线程；
- `dumpsys meminfo`、native heap 与 thread stack 区域；
- 未 shutdown 的 Executor、未 quit 的 HandlerThread；
- `GlobalScope`、静态 scope 和失去 owner 的 callback；
- 队列长度、active count、completed task count 与 rejection。

线程 stack 的 virtual reservation、resident pages 和 runtime 默认值会随设备与线程创建方式变化，不能用“每线程固定 1 MiB”估算 RSS。应在目标 ABI 和设备上读取 maps/meminfo，并同时考虑 ThreadLocal、队列和任务对象。

## 11. 检查清单

- 任务会阻塞线程，还是在 suspend 后释放线程？
- CPU、blocking I/O、主线程限定和 Looper 任务是否分开？
- `limitedParallelism` 限制的是执行并发，提交侧是否仍可能无限排队？
- IO 弹性 view 的额度之和是否超过连接池、FD、内存和服务端限制？
- 自定义 Executor 是否有明确 owner、queue、rejection 和 shutdown 策略？
- HandlerThread 是否由 API 的 Looper 要求驱动，是否调用 `quitSafely()`？
- Thread priority 是否在目标线程入口设置，权限与 task profile 是否考虑？
- CPU 循环多久检查一次取消，阻塞资源如何被关闭？
- 是否区分协程 scheduler 排队和 kernel runnable 等待？
- ADPF session 是否绑定长期稳定 TID，并按周期使用 uptime 时钟上报？
- 性能数字是否来自目标设备、release 构建、当前协程库和真实负载？

## 参考资料

- [kotlinx.coroutines 1.11.0 `Dispatchers.IO`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)
- [kotlinx.coroutines 1.11.0 `CoroutineDispatcher`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-dispatcher/)
- [kotlinx.coroutines 1.11.0 `CoroutineScheduler.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt)
- [kotlinx.coroutines 1.11.0 `Dispatcher.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/jvm/src/scheduling/Dispatcher.kt)
- [kotlinx.coroutines 1.11.0 `Executors.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/jvm/src/Executors.kt)
- [kotlinx.coroutines 1.11.0 `HandlerDispatcher.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/ui/kotlinx-coroutines-android/src/HandlerDispatcher.kt)
- [AOSP `HandlerThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/HandlerThread.java)
- [AOSP `MessageQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedMessageQueue/MessageQueue.java)
- [AOSP `PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [Android `PerformanceHintManager.Session`](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [Android `Process.setThreadPriority`](https://developer.android.com/reference/android/os/Process#setThreadPriority(int))
- [AOSP libprocessgroup task profiles](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json)
- [r6 kernel `sched/fair.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [r6 kernel EEVDF 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-eevdf.rst)
- [Android threading 指南](https://developer.android.com/topic/performance/threads)

## 交叉引用

- [**8.6 Kotlin Coroutine 性能实践**](06-coroutine-performance.md)：协程结构、异常与取消。
- [**8.17 Kotlin Flow 背压**](17-kotlin-flow-backpressure-performance.md)：流式并发和缓冲语义。
- [**5.1 Linux 进程调度基础**](../../part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md)：r6 fair/EEVDF 的虚拟时间与 deadline。
- [**5.8 JobScheduler/WorkManager**](../../part1-fundamentals/ch05-cpu-power/08-jobscheduler-workmanager-performance.md)：持久化后台任务。
