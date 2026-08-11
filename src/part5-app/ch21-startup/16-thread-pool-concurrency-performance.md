---
title: "线程池与并发调度性能实战"
chapter: "21.16"
status: ready-for-review
drafted_date: "2026-07-01"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/reference/java/util/concurrent/ThreadPoolExecutor"
  - type: aosp
    path: "libcore/ojluni/src/main/java/java/util/concurrent/ThreadPoolExecutor.java"
  - type: aosp
    path: "art/runtime/thread.cc (FixStackSize, CreateNativeThread)"
  - type: blog
    path: "https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/"
tags: [thread-pool, concurrency, cpu-scheduling, startup, coroutines]
related_chapters: ["1.5", "5.1", "8.6", "20.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "素材驱动/参考书"
---

# 21.16 线程池与并发调度性能实战

启动优化经常把“移到后台线程”和“缩短启动”写成同一件事。任务离开主线程后，仍会竞争 CPU、存储、Binder、内存带宽和锁；主线程若等待它的结果，排队时间也会进入启动关键路径。线程数增加只能扩大并发机会，无法消除依赖和资源上限。

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核锚点是 `android17-6.18-2026-06_r6`。每个调度结论都要回答任务契约、执行器、并行度和等待位置，并由队列指标与 Perfetto 支撑。

线程、锁与协程的基础机制分别见 [§1.5 线程模型](../../part1-fundamentals/ch01-architecture/05-threading-model.md) 和 [§8.6 协程性能](../../part2-performance/ch08-responsiveness/06-coroutine-performance.md)。以下只讨论启动场景中的任务编排和资源竞争。

## 1. 并发优化先看启动关键路径

启动任务可以画成一张有向无环图。节点是工作，边表示依赖；从进程创建走到首帧或 fully drawn 的最长依赖路径，就是当前指标下的关键路径。

一项后台任务对启动时间的贡献可以拆成四段：

`完成时间 = 提交时刻 + 队列等待 + 获得 CPU 后的执行 + 依赖或资源等待`

只统计任务函数自身的运行时间，会漏掉线程池排队、处于 Runnable 却没获得 CPU、锁竞争、同步 Binder 和主线程等待。并发调优必须把这几段分开。

启动任务按契约分类，比按代码所在模块分类更可靠：

| 任务类型 | 例子 | 主要约束 | 常见执行位置 |
|---|---|---|---|
| 首帧必需、主线程亲和 | View 创建、资源主题应用、窗口操作 | Android UI 线程规则 | 主线程，缩短同步工作 |
| 首帧必需、CPU 计算 | 小规模配置解析、状态归并 | CPU 容量、热状态、依赖顺序 | 有界计算调度器 |
| 首帧必需、阻塞调用 | 磁盘读取、同步数据库、同步 Binder | 外部服务与设备延迟 | 有界阻塞调度器，并评估能否取消依赖 |
| 首帧后可做 | 缓存预热、非当前页 SDK、统计准备 | 生命周期、功耗、与首帧竞争 | 首帧后由应用作用域调度 |
| 需要跨进程存活 | 可重试上传、持久同步 | 系统配额、约束、重试语义 | WorkManager |
| 回调式异步 API | OkHttp enqueue、异步数据库或系统回调 | API 自有线程与并发限制 | 保留原调度器，用挂起桥接等待结果 |

“I/O 任务不消耗 CPU”不成立。网络和文件路径仍可能做协议处理、内存复制、校验、解压、反序列化、加密和 Binder 调用。分类依据应是阻塞行为与资源占用，而非函数名中有没有 `read` 或 `load`。

并行化只对互相独立、且并行后没有把共享资源压满的任务有效。A、B 可以同时执行，但 C 等待 A 和 B 时，C 的开始时间仍由较慢分支决定；若 A、B 同时争用存储或 CPU，它们各自还可能变慢。

## 2. `ThreadPoolExecutor` 的队列决定扩容时机

### 2.1 `execute()` 的三段决策

Android 17 的 `ThreadPoolExecutor` 来自 libcore OpenJDK 实现。下面的伪代码用于呈现 `execute()` 的决策顺序，省略了运行状态重检和并发控制细节。

```text
if workerCount < corePoolSize:
    tryAddCoreWorker(task)
else if workQueue.offer(task):
    recheckPoolState()
else if workerCount < maximumPoolSize:
    tryAddNonCoreWorker(task)
else:
    reject(task)
```

这段顺序解释了一个常见现象：核心线程都忙时，执行器先调用 `workQueue.offer()`；只有入队失败，才尝试创建非核心线程。使用无界 `LinkedBlockingQueue` 时，运行中的执行器几乎不会因为积压而走到 `maximumPoolSize`，所以调大 `maximumPoolSize` 往往没有效果。

### 2.2 队列是延迟和过载策略

| 队列 | 行为 | 适用边界 | 主要风险 |
|---|---|---|---|
| 无界队列 | 核心线程忙后持续排队 | 生产速率受控、任务必须保留、已有外部背压 | 延迟与内存占用缺少上界，`maximumPoolSize` 很少参与 |
| 有界队列 | 队列满后扩到最大线程数，再拒绝 | 需要给排队和内存设上限 | 容量过小会频繁拒绝，过大又会隐藏过载 |
| `SynchronousQueue` | 提交者必须把任务直接交给空闲或新线程 | 极短突发、线程上限和拒绝语义清楚 | 阻塞任务容易迅速打满线程上限 |
| 优先级队列 | 由业务优先级选择任务 | 任务可稳定排序且能处理饥饿 | 默认通常无界，旧任务可能长期等不到执行 |

队列容量不应来自“64 看起来够用”这样的经验值。可从压测中记录到达速率、服务时间和允许排队时长，再按突发流量预留余量。Little 定律 `L = λW` 可以估算稳定区间的平均在途任务数，其中 `λ` 是每秒到达任务数，`W` 是任务从进入系统到离开的平均秒数；它不能替代突发测试，也不能给启动阶段直接生成一个通用常量。

### 2.3 拒绝策略属于正确性设计

执行器饱和时，拒绝策略决定数据是否丢失、调用线程是否被阻塞，以及错误能否被发现：

- `AbortPolicy` 抛出 `RejectedExecutionException`，适合不能静默丢失且调用方能够降级或重试的任务。
- `CallerRunsPolicy` 在提交线程执行任务，能够减慢生产者；若提交者是主线程，它会把后台工作搬回启动关键路径。
- `DiscardPolicy` 和 `DiscardOldestPolicy` 只适合允许丢弃、合并或由新状态覆盖旧状态的任务，还要记录丢弃原因。
- 自定义策略必须定义关闭期间与过载期间的差异，避免把 executor 已关闭误判成瞬时拥塞。

拒绝次数不能统一设成“只要大于零就报警”。主动丢弃的遥测任务和必须执行的配置加载，对拒绝的容忍度完全不同。监控规则要绑定任务契约。

### 2.4 同池等待会造成饥饿

一个容易漏掉的故障是：池中的每个工作线程都提交子任务到同一个有界池，然后同步等待子任务。所有 worker 被父任务占住后，子任务只能在队列里等待，系统可能永久停住。

修复方向包括取消同步等待、使用结构化并发让父任务挂起、把依赖关系交给调度器，或为有明确隔离需求的资源使用独立执行器。单纯扩大池只能推迟故障出现，无法修正循环等待关系。

## 3. 并行度由任务和设备共同决定

### 3.1 CPU 密集任务

`Runtime.getRuntime().availableProcessors()` 只能提供当前运行时可见的处理器数量。它没有表达大小核能力差异、当前 cpuset、前后台状态、系统负载、温度限制和其他进程竞争。

CPU 密集池可以从“接近可用处理器数量”的候选区间开始做实验，但不能把核数直接固化成所有设备的答案。启动阶段还要给主线程、RenderThread、Binder 和 GC 留出运行机会。较可靠的流程是：

1. 用低端、中端和高端代表设备固定 release APK、数据集与启动模式；
2. 分别测试几个小范围并行度；
3. 同时比较 TTID/TTFD、任务队列等待、Runnable 时间、温升与功耗；
4. 选择尾延迟稳定、且不会压缩 UI 调度空间的最小并行度。

任务粒度也会改变结果。几十微秒的小任务若每次都入队，调度、对象分配和同步成本可能超过计算本身；过大的任务又会长时间占用 worker。应从 trace 中确认任务切分后有没有减少关键路径，而非只看 CPU 利用率。

### 3.2 阻塞任务

阻塞线程在等待磁盘、socket、Binder 或锁时不占用 CPU 执行，但仍占据一个 Java/内核线程、栈地址空间和调度数据结构。阻塞池可以比 CPU 计算池容纳更多并发任务，具体上限仍受连接池、数据库并发、文件系统、服务端配额和进程内存约束。

如果底层 API 已提供异步回调，不必再包一层阻塞 executor。额外线程只是在等待原 API 的结果，还会让取消、超时和 trace 关联变得更复杂。OkHttp、Room、图片加载库等组件通常也有自己的执行器；应用接入前应先盘点它们的线程和并发配置。

### 3.3 隔离用于控制干扰

计算与阻塞任务可以分开调度，因为两者对并行度和过载的需求不同。但“每类任务一个线程池”会制造大量长期存活线程，也不能让 CPU、存储和内存带宽变成私有资源。

有以下证据时，再引入独立执行器：

- 某类长阻塞任务反复让低延迟任务排队；
- 某个串行资源要求严格顺序，例如单文件写入；
- 第三方 SDK 无法遵守应用的取消和优先级规则；
- 安全边界要求任务不能和普通业务共用执行上下文。

其余场景可以复用少量受管理的执行器，再用有界队列、`limitedParallelism`、`Semaphore` 或业务级合并控制单类任务的并发。

## 4. Android 17 上的优先级和 CPU 选择

### 4.1 `Process` 优先级对应 Linux nice

Android 的 `android.os.Process` 常量与 Java 的 `Thread.MIN_PRIORITY` 到 `MAX_PRIORITY` 不是同一套数值。Android 17 源码中：

- `THREAD_PRIORITY_DEFAULT = 0`；
- `THREAD_PRIORITY_BACKGROUND = 10`，正数代表较低的调度权重；
- `THREAD_PRIORITY_FOREGROUND = -2`；
- display、video、audio 等负值常量服务于特定系统场景，普通应用不应借它们抢占 UI 或媒体线程。

新线程会继承创建线程的优先级和调度分组。工作线程应在自己的入口处设置 Android nice 值，避免从创建者继承一个不符合任务用途的状态。下面的 `ThreadFactory` 用于给受管理的 worker 统一命名并设置优先级。

```kotlin
import android.os.Process
import java.util.concurrent.ThreadFactory
import java.util.concurrent.atomic.AtomicInteger

class AndroidThreadFactory(
    private val namePrefix: String,
    private val androidNice: Int
) : ThreadFactory {
    private val sequence = AtomicInteger()

    override fun newThread(task: Runnable): Thread {
        val threadName = "$namePrefix-${sequence.incrementAndGet()}"
        return Thread(
            {
                Process.setThreadPriority(androidNice)
                task.run()
            },
            threadName
        )
    }
}
```

`Process.setThreadPriority()` 由 worker 自己执行，因此设置的是当前工作线程。后台预取可以使用 `THREAD_PRIORITY_BACKGROUND`；首屏依赖任务是否适合默认优先级，要靠与主线程和 RenderThread 的竞争结果判断。应用不应把普通 worker 提升到 display 或 audio 优先级。

### 4.2 内核调度不只看 nice

在 `android17-6.18-2026-06_r6` 中，普通线程进入 fair 调度类，`fair.c` 通过 EEVDF 路径选择可运行实体。nice 会改变调度权重，但不会承诺某个线程在指定毫秒内获得 CPU。

Android 还用 cgroup 与 task profile 管理进程和线程所属的调度组。CPU 选择会受 cpuset、利用率钳制（uclamp）、CPU 容量、当前负载、能耗模型和热限制影响，设备厂商也可以调整配置。应用层的一个 nice 数值无法覆盖这些条件。

因此，优先级适合表达“这类工作相对更能等待”，不适合表达截止时间。首帧依赖仍要缩短工作量、取消非必需依赖，并在代表设备上检查尾延迟。

### 4.3 不把业务线程固定到大核

通过 JNI 调用 `sched_setaffinity()` 把工作线程绑到所谓大核，会绕过调度器对负载、能耗、温度和前后台状态的动态判断。不同 SoC 的 CPU 拓扑与在线状态也不一致；后台后仍保留错误亲和性，还可能增加功耗或让线程无核可用。

CPU 亲和性可以用于实验室归因，例如判断某段计算是否受核容量影响。生产应用不应把硬绑核作为通用启动优化。若 trace 显示关键线程长期在不合适的 CPU 上等待，应同时检查任务优先级、进程状态、Runnable 竞争、设备温度与厂商调度配置。

## 5. 每个线程都有内存和生命周期成本

### 5.1 ART 不采用“每线程固定 1 MB”的模型

Android 17 的 `art/runtime/thread.cc` 在 `Thread::CreateNativeThread()` 中调用 `FixStackSize()`。这段源码会：

1. 在调用者传入零时使用运行时默认栈大小；
2. 为兼容依赖较大 native stack 的旧应用再增加 1 MB；
3. 加入栈溢出保护区；
4. 满足 `PTHREAD_STACK_MIN`，并向系统页大小取整。

所以，不能用 `new Thread(..., stackSize)` 的参数推导线程最终栈映射大小。栈地址空间的保留量、已提交页和 RSS 还要分开看；一个较大的虚拟地址区间不代表同样大小的物理内存已常驻。

不要通过 PLT hook 统一改写 `pthread_attr_setstacksize()`。Java、JNI、解释器和 sanitizer 构建的栈需求不同，过小的栈会把偶发深调用变成难复现的崩溃。线程数量过多时，先减少无所有者线程、重复线程池和空闲 worker，再评估少数明确的 native 线程是否需要调整。

### 5.2 所有者负责关闭和取消

每个自建执行器都要有所有者、创建时机和关闭时机。常驻进程级执行器可以由 application scope 管理；页面级任务应随 `ViewModel` 或 Lifecycle 取消；测试和动态功能卸载还要显式 `shutdown()`，避免 class loader、Activity 或大对象被任务闭包长期引用。

线程“泄漏”常见的表现包括：

- 周期任务使用固定频率调度，页面销毁后仍继续提交；
- executor 没有关闭，核心线程长期等待队列；
- 阻塞调用忽略 interrupt，取消请求无法结束；
- 任务闭包持有 Activity、View 或大缓存；
- 第三方 SDK 多次初始化，每次创建一组线程。

`Thread.getAllStackTraces()` 会遍历并抓取大量 Java 栈，生产环境高频调用会制造额外开销，而且无法完整覆盖 native-only 线程。它适合受控诊断。日常盘点可以结合 Perfetto、bugreport、`/proc/self/task` 和库配置完成。

## 6. 协程仍运行在线程调度器上

### 6.1 `Dispatchers.Default` 与 `Dispatchers.IO`

在 JVM/Android 目标上，`Dispatchers.Default` 面向 CPU 计算，`Dispatchers.IO` 面向阻塞 I/O。协程挂起可以释放承载线程，普通阻塞调用仍会占住 worker。

`Dispatchers.IO` 的默认阻塞并行度是 64 与处理器数量两者中的较大值，也可以由 `kotlinx.coroutines.io.parallelism` 调整。这是 kotlinx.coroutines 的默认实现边界，不是应用应该追求的线程数。`IO` 与 `Default` 共享线程和调度资源；从 `Default` 切到 `IO` 时，实现还可能在同一个 worker 上继续执行。

`Dispatchers.IO.limitedParallelism(n)` 的视图具有弹性，各个视图的并行度总和不受 `Dispatchers.IO` 默认 64 限制。为多个 SDK 分别创建很大的 view，峰值时仍可能出现大量阻塞 worker。

### 6.2 `limitedParallelism` 控制执行片段

`limitedParallelism(n)` 返回底层 dispatcher 的一个视图，没有私有线程集合，也不保证稳定线程身份。它限制同时执行的协程片段数量；协程挂起后，其他协程可以进入同一个 view。

这使它适合约束 CPU 工作或实现“挂起点之间串行执行”。如果要限制数据库连接、socket 请求或解码器实例等资源的在途数量，应使用 `Semaphore`；需要保护共享可变状态时使用 `Mutex`。这些资源约束不能由 dispatcher 名称推断。

### 6.3 用结构化并发表达依赖

下面的通用函数用于并行读取两个互不依赖的启动输入。父协程取消时，两个子任务都会收到取消；函数返回前也不会留下脱离所有者的工作。

```kotlin
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope

suspend fun <A, B> loadStartupInputs(
    dispatcher: CoroutineDispatcher,
    loadA: suspend () -> A,
    loadB: suspend () -> B
): Pair<A, B> = coroutineScope {
    val a = async(dispatcher) { loadA() }
    val b = async(dispatcher) { loadB() }
    a.await() to b.await()
}
```

这段代码只表达依赖和取消关系，不承诺两个任务一定在不同线程上运行。若 `loadA` 或 `loadB` 调用不可中断的阻塞 API，协程取消也无法立刻释放底层线程，仍需为该 API 配置超时或使用可取消接口。

`GlobalScope` 不适合启动任务。它把任务寿命与调用页面、启动会话和测试分离，错误与取消也难以回收到所有者。应用级工作应注入明确的 `CoroutineScope`，页面工作使用 `viewModelScope` 或合适的 Lifecycle scope。

## 7. App Startup 和 WorkManager 解决不同问题

### 7.1 App Startup 负责发现和依赖顺序

Jetpack App Startup 用一个 `InitializationProvider` 发现 initializer，并按 `dependencies()` 先初始化依赖。自动初始化发生在 provider 启动路径，`AppInitializer` 同步调用 initializer 的 `create()`；它不会把依赖图自动并行，也不会自动把工作移出主线程。

因此，合并多个 provider 能减少组件发现成本，却不代表 initializer 中的阻塞工作已经离开启动关键路径。非首帧必需组件应移除自动初始化元数据，在明确的业务时机手动初始化；首帧必需组件则要让 `create()` 保持短小，并把后续可异步部分交给有所有者的调度器。Provider 约束详见 [§21.3 ContentProvider 启动优化](./03-contentprovider-optimization.md)。

### 7.2 WorkManager 用于需要持久执行的工作

WorkManager 面向应用离开可见状态后仍需执行、需要约束或重试的任务。它受 JobScheduler、系统配额、进程状态和设备条件管理，不能用来保证某个启动任务立刻完成。

`Worker`、`CoroutineWorker` 和 WorkManager 内部任务也不是一个固定“最多 16 个线程”的池。自定义 `Configuration` 可以设置 worker executor 和 task executor；`CoroutineWorker.doWork()` 默认使用 `Dispatchers.Default`。WorkManager 2.10.0 起还可以用 `setWorkerCoroutineContext()` 配置 worker 协程上下文，方法内部使用 `withContext()` 也能针对阻塞调用切换 dispatcher。

若应用只想让 WorkManager 自身不占用启动路径，可以关闭默认 initializer，再按官方的按需初始化方式配置。这个动作只移动 WorkManager 初始化时机，不会让已入队的持久任务变成应用内启动任务。

## 8. 线程治理从“谁创建、谁负责”开始

### 8.1 建立执行资源清单

线程治理表至少记录这些字段：

| 字段 | 用途 |
|---|---|
| owner | 谁创建、谁关闭、异常交给谁 |
| task contract | CPU、阻塞、串行、持久或主线程亲和 |
| pool/dispatcher | 具体执行资源及共享关系 |
| concurrency limit | 限制来源：CPU、连接池、数据库或业务顺序 |
| queue/rejection | 队列上限、过载时丢弃或降级方式 |
| priority | Android nice 值及依据 |
| observability | 线程名前缀、trace 名、指标标签 |

盘点时应覆盖直接 `Thread`、`Executors`、`HandlerThread`、Rx scheduler、自建 coroutine dispatcher、JNI `pthread_create`，以及 SDK 内部执行器。线程名应稳定、低基数并包含 owner，例如 `image-decode-2`，这样 Perfetto、ANR trace 和 tombstone 才能对应到组件。

字节码插桩可以用于发现匿名线程、补命名或记录创建堆栈。不要把所有 `Executors.new*` 调用静默重定向到一个全局池：原池的顺序、拒绝、线程局部变量和关闭语义可能不同，强行替换会引入饥饿或死锁。

### 8.2 指标覆盖排队、执行和取消

线程池至少观测：

- 提交量、完成量、取消量和拒绝量；
- 队列长度，以及任务排队时间的分位数；
- 执行时间与端到端时间的分位数；
- `activeCount`、`poolSize`、`largestPoolSize` 和完成任务数；
- 新建线程次数、线程退出次数与存活时长；
- 任务异常类型，以及 executor shutdown 后的提交；
- 启动窗口内 worker 的 Running、Runnable、Sleeping 和 blocked 分布。

固定的“线程数大于 200”或“队列超过 80%”无法跨应用复用。阈值应来自进程基线、设备档位、任务 SLO 和队列语义；一次版本变化若同时推高线程数、RSS、Runnable 时间与 TTID 尾延迟，才形成较强的回归证据。

## 9. 用 Perfetto 区分排队和 CPU 竞争

启动并发问题适合按以下顺序分析：

1. 在 Android App Startups 轨道选择 TTID 或 TTFD 区间，固定分析窗口；
2. 查看主线程是否 Running、Runnable、Sleeping，或在锁/Binder 上阻塞；
3. 找到启动 worker，区分“线程池队列中尚无对应 slice”和“线程已经 Runnable 但没获得 CPU”；
4. 对齐 RenderThread、Binder、GC、磁盘与 CPU frequency，判断后台任务是否挤压首帧；
5. 用低基数业务 trace 标记任务提交、开始和结束，计算 queue wait、run time 与 end-to-end；
6. 在相同 APK、设备状态和数据集下改变一个并行度参数，比较多轮分布。

线程总 CPU 时间下降，不一定让启动更快；任务可能只是等待得更久。CPU 利用率升高也不等于优化成功；如果 TTID 尾延迟、功耗或首帧掉帧变差，新增并发没有服务当前目标。

线上持续采样应控制成本。任务计数、直方图和低频线程数量比周期性抓取所有 Java 栈更适合常驻；完整栈、Perfetto 和 `/proc` 明细留给诊断构建、触发式采样或用户授权的问题复现。

## 10. Android 17 的两个版本边界

### 10.1 `AsyncTask` 只做遗留迁移

`AsyncTask` 自 API 30 起废弃。Android 17 源码中的默认 executor 仍是 `SERIAL_EXECUTOR`；显式 `THREAD_POOL_EXECUTOR` 使用 `corePoolSize = 1`、`maximumPoolSize = 20`、`SynchronousQueue`，拒绝后再交给 5 线程、无界队列的 backup executor。`doInBackground()` 入口还会把当前线程设为 `THREAD_PRIORITY_BACKGROUND`。

这些数字属于 framework 遗留实现，不能当成应用线程池模板。维护旧代码时应确认 `execute()` 与 `executeOnExecutor()` 的顺序差异，随后迁移到有生命周期和取消语义的协程，或迁移到任务契约明确的 executor。

### 10.2 虚拟线程尚不能作为 Android 17 基线

`android-17.0.0_r1` 的 libcore 已引入 OpenJDK 21 风格的 `Thread.Builder`、`ofVirtual()` 和 `startVirtualThread()` 源码，并包含 Android 自己的 `VirtualThreadContext` 路径。不过，`api/current.txt` 把这些入口标成 `@FlaggedApi(com.android.libcore.virtual_thread_api_v1)`，运行实现还检查 ART 的 `virtual_thread_impl_v1` flag。

同一时期的 Android 公共参考文档没有列出 `ofVirtual()` 与 `startVirtualThread()`，`Thread.isVirtual()` 的文档仍写明 Android 尚未实现虚拟线程并返回 `false`。源码、flag 和公开契约没有形成可供普通应用依赖的一致边界，因此 Android 17 应用不应把虚拟线程用于生产启动路径，也不应通过反射探测内部实现。

即使后续版本提供稳定虚拟线程，它们主要降低大量阻塞任务占用平台线程的成本，不会提高 CPU 密集任务的可用算力。资源并发、超时、取消和启动关键路径仍要单独设计。

## 11. 检查清单

- 是否先画出 TTID/TTFD 的任务依赖图，再决定哪些节点可以并行？
- 是否同时记录 queue wait、run time、依赖等待和端到端时间？
- 是否理解无界队列会让 `maximumPoolSize` 很少参与扩容？
- 是否为每类任务定义队列上限、拒绝语义、取消和所有者？
- 是否避免把 `availableProcessors()`、64 个 I/O worker 或固定队列容量当成通用答案？
- 是否检查 OkHttp、Room、图片库和 SDK 已有执行器，避免重复套池？
- 是否使用 `Process.THREAD_PRIORITY_BACKGROUND = 10`，并避免给普通 worker 设置 display/audio 优先级？
- 是否让内核根据 cpuset、uclamp、容量、能耗和热状态选择 CPU，而非在生产环境硬绑大核？
- 是否区分线程栈虚拟地址保留与 RSS，并避免统一缩小 pthread 栈？
- 是否理解 `Dispatchers.IO` 与 `Default` 共享资源，且 `IO.limitedParallelism` view 具有弹性？
- 是否用 `Semaphore` 或 `Mutex` 表达资源约束，而非把 `limitedParallelism(1)` 当作通用锁？
- 是否让 App Startup initializer 保持同步路径短小，并只把持久任务交给 WorkManager？
- 是否把 `AsyncTask` 和 flag 控制的虚拟线程视为版本边界，而非新代码模板？
- 是否用 release-like 构建和 Perfetto 验证并发变化对 TTID/TTFD 尾延迟、帧和功耗的影响？

## 参考资料

- [AOSP Android 17 `ThreadPoolExecutor`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/util/concurrent/ThreadPoolExecutor.java)
- [AOSP Android 17 `Process`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java)
- [AOSP Android 17 ART `Thread::FixStackSize`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)
- [AOSP Android 17 `AsyncTask`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/AsyncTask.java)
- [AOSP Android 17 `Thread`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)
- [AOSP Android 17 libcore public API surface](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt)
- [Android 17 kernel `fair.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [Android cgroup and task profile](https://source.android.com/docs/core/perf/cgroups)
- [Android process and thread overview](https://developer.android.com/guide/components/processes-and-threads)
- [Android threading performance](https://developer.android.com/topic/performance/threads)
- [Kotlin `Dispatchers.IO`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)
- [Kotlin `limitedParallelism`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-dispatcher/limited-parallelism.html)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [WorkManager persistent work](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [WorkManager `CoroutineWorker` threading](https://developer.android.com/develop/background-work/background-tasks/persistent/threading/coroutineworker)
- [WorkManager `Configuration.Builder`](https://developer.android.com/reference/androidx/work/Configuration.Builder)
- [Android system tracing overview](https://developer.android.com/topic/performance/tracing)
- [Android startup analysis and optimization](https://developer.android.com/topic/performance/appstartup/analysis-optimization)
- [§21.2 启动任务编排](./02-startup-framework.md)
- [§21.3 ContentProvider 启动优化](./03-contentprovider-optimization.md)
- [§21.8 启动性能监控](./08-startup-monitoring.md)
