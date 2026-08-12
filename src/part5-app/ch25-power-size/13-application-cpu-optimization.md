---
title: "应用层 CPU 优化实战指南"
chapter: "25.13"
section: "25.13"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [CPU优化, 应用实践, 线程池, 性能优化]
related_chapters: ["5.1", "5.9"]
last_verified: "2026-07-26"
last_verified_against: "AOSP android-17.0.0_r1 / android17-6.18"
confidence: medium-high
consolidated_from:
  - "src/part5-app/ch25-power-size/12-android17-excessive-cpu-kill.md"
  - "src/part5-app/ch25-power-size/15-scheduledexecutor-fixedrate-android16.md"
pipeline_stage: task6_ready_for_review
task6_state: ready-for-review
task9_state: ready-for-review
last_draft_polish_at: "2026-07-26T15:35:39+08:00"
last_draft_polish_run_id: "20260726-153539-draft-polish-19d43518"
last_review_finalize_at: "2026-07-26T16:08:37+08:00"
last_review_finalize_run_id: "20260726-160837-29efbe02"
last_rework_at: "2026-07-26T17:35:54+08:00"
last_rework_run_id: "20260726-173554-rework-19d43518"
sources:
  - type: aosp
    title: "ThreadPoolExecutor / Process / bionic times / procfs source verification"
    path: "DeepResearch/2026-07-02-android17-app-cpu-optimization-thread-priority-source-verification.md"
  - type: aosp
    title: "ThreadPoolExecutor 三层源码 + bionic times() 系统调用深挖"
    path: "DeepResearch/2026-07-02-android17-threadpoolexecutor-times-syscall-source-deepdive.md"
---

# 应用层 CPU 优化实战指南

> 平台源码上限为 `android-17.0.0_r1`，内核口径为 `android17-6.18-2026-06_r6`。普通应用示例只使用 public SDK/NDK；`/proc` 文件可能因设备策略而不可读，相关方案都必须允许采样失败。

## CPU 优化先回答三个问题

“CPU 高”只能描述现象，不能直接指出改法。开始修改线程池或调度参数前，需要回答：

1. 哪一段用户路径受影响：启动、首帧、滚动、输入、后台同步，还是持续计算？
2. 损失表现在哪个维度：延迟、CPU 时间、能耗、温升，还是后台执行额度？
3. 证据能否归因到具体任务、线程和调用栈？

常见指标的含义并不相同：

| 指标 | 回答的问题 | 容易误读的地方 |
| --- | --- | --- |
| 墙钟时间（wall time） | 用户等了多久 | 包含运行、排队、锁等待、I/O 和抢占 |
| 进程/线程 CPU 时间 | 代码在 CPU 上运行了多久 | 不包含大多数睡眠与阻塞等待 |
| Runnable 等待 | 线程能运行，但还未获得 CPU 的时间 | 可能来自并发过量、优先级或系统竞争 |
| Blocked/Sleeping 时间 | 线程在等锁、I/O、定时器或条件 | CPU 低也可能有很差的响应 |
| 能耗与温度 | 这段工作付出了多少设备成本 | 同样的 CPU 时间在不同频点和核上成本不同 |

应用层 CPU 优化通常落在四件事上：少做工作、减少同一时刻的并行工作、减少唤醒与切换、把非紧急工作交给合适的系统调度时机。线程池参数只是其中一个控制点。

## ThreadPoolExecutor：先理解队列，再谈线程数

### `execute()` 的三段决策

Android 17 的 `ThreadPoolExecutor` 来自 libcore 的 OpenJDK 实现。`execute()` 的主要决策顺序是：

1. 当前 worker 少于 `corePoolSize` 时，尝试创建核心 worker；
2. 否则尝试把任务放入 `workQueue`，入队后还会复查池状态；
3. 队列拒绝入队时，尝试创建非核心 worker；仍失败才调用拒绝策略。

这解释了一个常见疑问：使用容量很大的队列时，任务会长时间停在第 2 步，`maximumPoolSize` 很少参与调度。使用 `SynchronousQueue` 时没有存储槽位，提交方更容易触发创建非核心 worker。两种队列没有固定优劣，差别在于系统选择“排队”还是“增加并发”。

默认配置下，核心线程不会因 `keepAliveTime` 到期而退出；`keepAliveTime` 只约束超出核心数量的 worker。调用 `allowCoreThreadTimeOut(true)` 后，核心线程也可以超时退出。对应实现可在 Android 17 的 [`ThreadPoolExecutor.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/util/concurrent/ThreadPoolExecutor.java) 中核对。

### 没有跨应用通用的“核数公式”

`Runtime.availableProcessors()` 返回 JVM 当前可用的逻辑处理器数量。它不是性能核数量，也不是应用可长期占满的核数，更不能直接推出合适的 worker 数量。任务内部还可能调用并行库，设备也会受前台状态、温度、功耗策略和其他进程影响。

线程数需要从任务模型出发：

- 纯计算任务先用较小的受控并行度做基线，再观察吞吐、尾延迟、Runnable 等待、温度和前台流畅度；
- 阻塞任务的并发上限取决于下游容量、连接池、内存、文件描述符和超时策略，不能用一个很大的固定值代替分析；
- 混合任务应拆开计算阶段与阻塞阶段，让两者分别受限；
- 同一个执行器承载不同优先级、不同服务目标的任务，会让长任务阻塞短任务。

队列容量的单位是“任务个数”，并不代表内存大小或可接受等待时间。容量应同时受以下条件约束：

- 峰值到达速率与任务服务时间；
- 允许的排队时延；
- 每个排队任务持有的对象、Bitmap、Buffer 或请求上下文；
- 任务过期后是否还有业务价值；
- 饱和时可以合并、丢弃、降级还是改期。

因此，`workers = availableProcessors()`、`queue = processors × 4` 之类的表达最多只能当实验起点，不能写成工程规则。

### 一个可观测、可拒绝的计算执行器

下面的工厂刻意不替业务决定 worker 数和队列容量。调用方必须根据压测结果传入参数；线程优先级也由场景明确给出。

```kotlin
import android.os.Process
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ThreadFactory
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

data class CpuExecutorConfig(
    val workers: Int,
    val queueCapacity: Int,
    val threadPriority: Int,
)

fun newBoundedCpuExecutor(
    name: String,
    config: CpuExecutorConfig,
): ThreadPoolExecutor {
    require(config.workers > 0)
    require(config.queueCapacity > 0)

    val sequence = AtomicInteger()
    val factory = ThreadFactory { command ->
        Thread({
            Process.setThreadPriority(config.threadPriority)
            command.run()
        }, "$name-${sequence.incrementAndGet()}")
    }

    return ThreadPoolExecutor(
        config.workers,
        config.workers,
        0L,
        TimeUnit.MILLISECONDS,
        ArrayBlockingQueue(config.queueCapacity),
        factory,
        ThreadPoolExecutor.AbortPolicy(),
    )
}
```

固定大小的有界池让并发量和积压量都可控。`AbortPolicy` 会用 `RejectedExecutionException` 明确报告饱和，提交点据此选择合并同类请求、取消已经过期的工作、返回降级结果或交给持久化调度。

`CallerRunsPolicy` 会在提交任务的线程里直接调用 `Runnable.run()`。如果提交方恰好是主线程、Binder 线程或持有锁的回调线程，计算或阻塞工作就会转移到那里。只有能证明提交线程允许执行该任务时，才能把它当作反压手段。

线程工厂在新线程内部调用 `Process.setThreadPriority()`，因为该 API 默认修改调用线程。它设置的是 Linux nice 值相关的线程优先级，不负责选择大小核，也不改变 cpuset。

### 线程池至少记录哪些数据

只看 `activeCount` 不足以定位问题。建议为稳定的任务类型记录：

- 提交时间、开始时间和结束时间；
- 排队时长、墙钟执行时长、线程 CPU 时间；
- 已完成、取消、过期和拒绝次数；
- 采样时的活动 worker 数与队列深度；
- 分位数，而不是只有平均值；
- 对应的版本、设备档位、前后台状态和热状态。

任务类型应是低基数标识，例如 `image_decode`、`feed_diff`，不要把 URL、文件名或用户 ID 放进指标维度。对线程池调参时，一次只改一个主要变量，并同时检查吞吐、尾延迟、温升和 UI 帧表现。

## 进程 CPU 采样：把百分比说清楚

### Public SDK 的低成本窗口采样

`Process.getElapsedCpuTime()` 返回进程从启动以来消耗的 CPU 毫秒数，`SystemClock.elapsedRealtime()` 返回包含深度睡眠在内的单调墙钟毫秒数。两次采样的增量可以得到窗口内的“等效占用核数”。

```kotlin
import android.os.Process
import android.os.SystemClock

data class CpuSample(
    val processCpuMs: Long,
    val elapsedMs: Long,
    val availableProcessors: Int,
)

data class CpuWindow(
    val equivalentCores: Double,
    val logicalCapacityFractionHint: Double,
)

fun takeCpuSample(): CpuSample = CpuSample(
    processCpuMs = Process.getElapsedCpuTime(),
    elapsedMs = SystemClock.elapsedRealtime(),
    availableProcessors = Runtime.getRuntime().availableProcessors().coerceAtLeast(1),
)

fun calculateCpuWindow(
    before: CpuSample,
    after: CpuSample,
): CpuWindow? {
    val cpuDeltaMs = after.processCpuMs - before.processCpuMs
    val wallDeltaMs = after.elapsedMs - before.elapsedMs
    if (cpuDeltaMs < 0L || wallDeltaMs <= 0L) return null

    val equivalentCores = cpuDeltaMs.toDouble() / wallDeltaMs
    val capacity = minOf(before.availableProcessors, after.availableProcessors)

    return CpuWindow(
        equivalentCores = equivalentCores,
        logicalCapacityFractionHint = equivalentCores / capacity,
    )
}
```

`equivalentCores = 1.0` 表示采样窗口内累计使用了约一个核的 CPU 时间。多线程并行时它可以大于 `1.0`。除以逻辑处理器数量得到的值只能作为当前逻辑容量占比的粗略提示；它没有考虑各核性能差异、频率、温控和调度限制。

采样窗口太短会受毫秒精度影响，太长又会掩盖尖峰。窗口长度应由要观察的用户路径决定。监控代码不应内置一个适用于所有设备的“高 CPU 阈值”，告警线应来自场景基线、用户影响和设备分层。

### `/proc/stat` 不能直接回答“现在适合做重活吗”

Linux 6.18 的 `/proc/stat` 首行按 `USER_HZ` 输出累计时间，常见字段顺序为：

```text
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```

这里的 `guest` 已包含在 `user` 中，`guest_nice` 已包含在 `nice` 中。计算总时间时如果把十个字段全部相加，就会重复计算虚拟 CPU 时间。常见口径只累计 `user` 到 `steal` 的前八项，并明确忙碌时间是否排除 `iowait`。

内核文档还特别说明，`iowait` 很难可靠计算，在某些条件下甚至可能下降。它不表示某个特定 CPU 一直在等待 I/O，也不能作为应用预加载的安全信号。细节见 Android 17 内核锚点的 [`Documentation/filesystems/proc.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)。

读取 `/proc/self/stat` 时，进程名 `comm` 位于括号内且可能包含空格，不能直接对整行 `split(" ")` 后取固定下标。应先识别 `comm` 的结束括号，再解析其后的字段；`utime` 和 `stime` 是文档中的第 14、15 字段。相关访问也可能因设备策略、SELinux 或未来平台限制失败，采样器必须返回“无数据”，而不是让业务崩溃。

`/proc/stat` 是整机聚合数据。即使整机采样显示较多 idle，也不知道用户是否即将触摸屏幕、前台应用是否临近帧期限、设备是否处于热约束，或你的任务是否会引起缓存和内存压力。它适合诊断，不适合单独决定业务时机。

### `times()` 的 USER_HZ 语义

Android bionic 的 `times()` 进入 Linux `do_sys_times()`。在 `android17-6.18-2026-06_r6` 中，内核通过 `thread_group_cputime_adjusted()` 取得当前线程组的 user/system CPU 时间，再用 `nsec_to_clock_t()` 转成 clock tick；返回值来自 `jiffies_64_to_clock_t(get_jiffies_64())`。源码可在 [`kernel/sys.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sys.c) 中核对。

`tms_utime` 与 `tms_stime` 是当前进程线程组的累计 CPU tick。`tms_cutime` 与 `tms_cstime` 反映已纳入 `times()` 子进程统计语义的子进程时间，普通 Android 应用通常不需要它们。`times()` 的返回值是从系统定义起点累计的 elapsed tick，绝对值没有业务含义，应只比较短时间窗口内的差值。

下面的 NDK 示例保留单位换算，并拒绝无效样本：

```cpp
#include <sys/times.h>
#include <unistd.h>

#include <optional>

struct TimesSample {
    clock_t elapsed_ticks;
    clock_t process_ticks;
    long ticks_per_second;
};

std::optional<TimesSample> TakeTimesSample() {
    const long ticks_per_second = sysconf(_SC_CLK_TCK);
    if (ticks_per_second <= 0) return std::nullopt;

    tms value{};
    const clock_t elapsed = times(&value);
    if (elapsed == static_cast<clock_t>(-1)) return std::nullopt;

    return TimesSample{
        .elapsed_ticks = elapsed,
        .process_ticks = value.tms_utime + value.tms_stime,
        .ticks_per_second = ticks_per_second,
    };
}

std::optional<double> EquivalentCores(
        const TimesSample& before,
        const TimesSample& after) {
    if (before.ticks_per_second != after.ticks_per_second) return std::nullopt;

    const clock_t wall_ticks = after.elapsed_ticks - before.elapsed_ticks;
    const clock_t cpu_ticks = after.process_ticks - before.process_ticks;
    if (wall_ticks <= 0 || cpu_ticks < 0) return std::nullopt;

    return static_cast<double>(cpu_ticks) /
           static_cast<double>(wall_ticks);
}
```

`sysconf(_SC_CLK_TCK)` 返回用户空间 ABI 使用的 clock ticks per second，也就是这里需要的 USER_HZ 口径。它不应由内核 `CONFIG_HZ` 推算。`CONFIG_HZ` 影响内核定时 tick 配置，两者不是同一个接口契约。

`times()` 精度较粗，适合低频累计采样。需要更细的进程 CPU 时间时，NDK 可评估 `clock_gettime(CLOCK_PROCESS_CPUTIME_ID, ...)`；只在 Kotlin/Java 层做应用监控时，前面的 `Process.getElapsedCpuTime()` 更直接。

## 预加载：由收益与生命周期决定，不由“空闲百分比”决定

预加载会提前支付 CPU、I/O、内存和缓存成本。如果结果没有被使用，这些成本都成了浪费。设计前应明确：

- 预加载命中率与节省的用户等待时间；
- 结果的有效期、取消点和去重键；
- 单次与累计 CPU/I/O 预算；
- 结果占用的 Java heap、native heap、GPU 资源和文件缓存；
- 前后台切换、低内存、温度升高时如何停止；
- 未命中或被回收后是否比按需加载更差。

`MessageQueue.IdleHandler` 只表示当前 Looper 队列暂时没有到期消息。它不表示整机 CPU 空闲，也不保证距离下一次输入或 vsync 还有足够时间。IdleHandler 中只适合短小、可立即结束的操作；重计算仍应交给受控执行器，并能在页面状态改变时取消。

需要延后、可持久化、受网络或充电等条件约束的后台工作，应使用 WorkManager 或 JobScheduler 表达约束。系统会结合设备状态调度，但不承诺精确执行时刻。不要通过高频轮询 `/proc/stat` 自建“空闲探测器”，轮询本身也会增加唤醒。

评估预加载时，至少同时看命中率、废弃工作比例、CPU 时间、I/O、RSS/PSS、启动与帧性能回归。只有用户收益覆盖设备成本时，这项预加载才值得保留。

## 周期任务：避免固定频率补跑制造恢复尖峰

`scheduleAtFixedRate()` 按起点维持固定节拍；任务因冻结、CPU 挂起或长执行错过周期后，旧实现可能连续追赶。Android 16 对 target 36+ 默认启用 `STPE_SKIP_MULTIPLE_MISSED_PERIODIC_TASKS`，最多立即补一次；`android-17.0.0_r1` 已直接采用新的时间校正逻辑，不再保留该 target 分支。

平台变化只限制 `ScheduledThreadPoolExecutor` 自己的追赶，不会处理业务手写补发循环、多个独立定时器或三方 SDK 队列。周期任务应先按语义分类：

| 需求 | 更合适的机制 |
| --- | --- |
| 前台、要求相位、允许进程退出后丢失 | `scheduleAtFixedRate()`，生命周期结束时取消 |
| 只要求每次完成后间隔一段时间 | `scheduleWithFixedDelay()` |
| 可延期、需跨进程/重启、带约束 | WorkManager / JobScheduler |
| 用户可感知的精确时刻 | 合适的 AlarmManager 接口 |

固定频率任务的异常默认会抑制后续执行；取消后还应启用 remove-on-cancel 或明确清理队列。采集冻结→恢复→首帧完成的完整区间，检查后台 Runnable 是否与主线程、RenderThread 和网络重连同时争用 CPU。升级 target 时同时审计广告、埋点、APM、IM 等 SDK 内部定时器，不能只测试应用自有线程池。

## Android 17 excessive CPU 终止与取证

Android 17 新增 `ProfilingTrigger.TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`，它把既有的 excessive resource usage 终止路径接入触发式性能分析；触发器提供事后系统跟踪快照，不负责决定任务能否执行。`ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE` 从 API 30 已公开，不能把终止机制本身误写成 Android 17 新增。

AOSP r1 的主要检查对象是 Home 与缓存进程。系统按检查窗口计算进程累计 CPU 时间，阈值可由系统配置和 OEM 修改；多线程累计 CPU 时间可以超过单核墙钟时间，所以源码百分比不等同于性能面板的整机 CPU 占比。JobScheduler/WorkManager 配额决定任务资格与运行额度，excessive CPU 路径决定缓存进程是否因持续 CPU 被终止，两者没有直接调用关系。

后台任务常见关联不是“Worker 一运行就被杀”，而是 Worker 已结束或被停止后，协程、独立线程、JNI、子进程或 Binder 循环仍在工作；进程随后降为缓存状态。治理重点是唯一任务、分类退避、取消传播、有界并发、分片与检查点，而不是围绕某个 AOSP 默认阈值设计轮询。

API 37 应用可以预注册触发器和全局结果监听器。`ProfilingResult` 只有 trigger type、文件路径、tag 与错误信息，没有公开 pid 或 Work ID；归档层应把结果与最近的 `ApplicationExitInfo`、`processStateSummary`、任务开始/结束、停止原因和线程命名做“可能关联”，不能伪造精确映射。没有结果也不表示没有发生终止，后台跟踪和采集都受频率与可用性限制。

排查顺序固定为：未启动先查 pending reason；启动后被停止查 Work/Job stop reason；进程死亡查 `ApplicationExitInfo`；原因是 excessive resource usage 时再查 ProfilingResult 与 Perfetto；任务已经结束而 CPU 仍持续时，回到未取消线程、协程、JNI 与子进程。

## 锁竞争：低 CPU 也可能让用户等很久

### 不要假设固定的“自旋后休眠”流程

Java/Kotlin `synchronized` 在 ART 中由 monitor 实现，具体快路径、竞争处理和运行时策略会随实现与状态改变。应用代码不能依赖“先自旋固定次数，再进入内核休眠”这类固定流程。

等待锁的线程通常不会持续消耗一个核，但锁竞争会增加尾延迟、线程唤醒、上下文切换和优先级反转风险。相反，CAS 在竞争激烈时可能反复失败并消耗 CPU。`synchronized`、`ReentrantLock`、原子变量之间不存在脱离负载的固定胜者。

### 优化顺序

锁问题应按证据处理：

1. 用 Perfetto 或可控的应用 trace 找到等待时间长、调用频繁的临界区；
2. 缩短持锁范围，避免在锁内执行 I/O、Binder 调用、回调和重计算；
3. 检查是否可以用线程封闭、不可变快照或消息传递减少共享可变状态；
4. 只有在确认单锁竞争后，再评估分段锁或更复杂的数据结构；
5. 用相同负载比较修改前后的墙钟时间、CPU 时间、等待分布和内存成本。

把一把锁换成多把锁可能增加一致性维护难度；把锁换成 CAS 也可能把阻塞等待变成忙碌重试。优化结果要由 trace 和基准测试确认。

## 协程：控制并发，不隐藏成本

`Dispatchers.Default` 面向 CPU 计算，`Dispatchers.IO` 面向阻塞 I/O。两者在 JVM 上共享线程资源，切换 dispatcher 不必然创建一条新线程。`Dispatchers.IO.limitedParallelism(n)` 创建的视图具有弹性：这些视图不受 IO dispatcher 常规并行度上限的同一约束，但仍与它共享线程和资源。具体语义见 kotlinx.coroutines 的 [`Dispatchers.IO` 文档](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)。

下面的封装要求调用方根据计算预算和下游容量显式给出并行度：

```kotlin
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers

class WorkDispatchers(
    cpuParallelism: Int,
    blockingParallelism: Int,
) {
    init {
        require(cpuParallelism > 0)
        require(blockingParallelism > 0)
    }

    val cpu: CoroutineDispatcher =
        Dispatchers.Default.limitedParallelism(cpuParallelism)

    val blockingIo: CoroutineDispatcher =
        Dispatchers.IO.limitedParallelism(blockingParallelism)
}
```

`limitedParallelism()` 限制该视图同时执行的协程数量，不承诺对应固定数量的物理线程。阻塞并发上限应与数据库连接池、服务端限流、文件描述符和内存预算匹配。CPU 任务即使写成 `suspend` 函数，所需指令和 CPU 时间也不会减少；仍要分批、取消过期任务并控制并发。

不要在主线程用 `runBlocking` 等待后台结果。结构化并发的价值在于生命周期、取消和错误传播，它不能补偿不受控的工作量。

## Android 17 上应用能控制什么

### 优先级不等于选核

Android 17 的内核锚点是 `android17-6.18-2026-06_r6`。公平调度类采用 EEVDF 选择可运行实体，但系统还会结合调度组、cpuset、利用率钳制、功耗和温度策略决定线程在哪里、以什么资源水平运行。

普通应用调用 `Process.setThreadPriority()` 表达 nice 级别的相对优先级。它不提供以下能力：

- 指定线程必须运行在性能核或能效核；
- 把线程移入系统 cpuset；
- 直接设置 `uclamp`；
- 绕过后台、功耗或温控策略。

提高优先级也不会减少工作量，只会改变竞争时的相对机会。优先级设置不当还可能挤压 UI、RenderThread、Binder 或其他关键工作。

### ADPF 是持续负载的协作接口

API 31 起，`PerformanceHintManager` 允许应用为一组工作线程创建 hint session，报告目标工作时长和实际工作时长。它适合游戏、相机、音视频等有重复工作周期且能持续反馈实际耗时的负载。系统据此调整资源策略；应用不能把它当成核心绑定或固定频率接口。API 边界见 [`PerformanceHintManager`](https://developer.android.com/reference/android/os/PerformanceHintManager)。

如果工作没有明确周期、线程集合不稳定，或应用无法可靠报告实际时长，先减少工作与并发通常更有效。使用 ADPF 后仍要在多档设备、持续温升和前后台切换条件下测量。

## 一套可执行的检查流程

### 建立基线

选择一个可重复的用户场景，记录应用版本、构建类型、设备、刷新率、电量、温度起点和后台环境。性能测量应使用接近发布配置的构建；调试器、日志和未优化代码会改变调度与 CPU 成本。

### 用时间线归因

Perfetto 中同时观察：

- 主线程、RenderThread 和相关 worker 的 Running/Runnable/Sleeping 状态；
- 应用 trace section 对应的业务阶段；
- 频率、调度、帧时间与热状态；
- Binder、I/O、锁等待和 GC 是否占据关键路径。

“CPU 时间很高”时查看调用栈与任务来源；“墙钟时间高但 CPU 时间低”时优先检查排队、锁、I/O 和调度等待。只有定位到具体阶段，才知道应减少计算、降低并发、移除锁内工作还是改变后台时机。

### 修改后同时检查收益与副作用

每轮只改变少量因素，并回答：

- 用户路径的中位数和尾延迟是否改善；
- 进程 CPU 时间和整机能耗是否下降；
- Runnable 等待、上下文切换或锁等待是否转移到别处；
- 队列是否积压，任务是否被拒绝或过期；
- 连续运行后是否因温度产生反向回归；
- 低端设备、后台状态和网络异常下是否仍成立。

CPU 优化的完成标准应落在明确场景中：以更少设备成本达到同等或更好的用户结果，同时不把延迟、内存和可靠性问题转移到其他阶段。某个瞬时百分比变小不足以证明优化完成。

## 源码与文档索引

- Android 17 [`ThreadPoolExecutor.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/util/concurrent/ThreadPoolExecutor.java)
- Android 17 [`android.os.Process`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java)
- Android 17 6.18 内核 [`kernel/sys.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sys.c)
- Android 17 6.18 内核 [`proc.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)
- Linux 6.18 [`EEVDF 调度文档`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-eevdf.rst)
- Android Developers [`优化后台任务`](https://developer.android.com/topic/performance/background-optimization)
- Android Developers [`PerformanceHintManager`](https://developer.android.com/reference/android/os/PerformanceHintManager)
- Kotlin [`Dispatchers.IO`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-i-o.html)
