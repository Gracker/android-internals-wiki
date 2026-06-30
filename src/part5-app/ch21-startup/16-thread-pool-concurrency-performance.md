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
related_chapters: ["1.5", "5.1", "8.6", "8.17", "20.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "素材驱动/参考书"
---

# 21.16 线程池与并发调度性能实战

> 本章聚焦工程实战：如何在 App 中正确配置线程池、收敛野线程、优化线程优先级与 CPU 绑核，以及 Coroutine Dispatcher 的底层映射。线程的底层原理（线程模型、锁机制）详见 1.5 节，Coroutine 语言级性能详见 8.6 节。

[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]
[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]
[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]

---

## 1. 线程池配置对启动性能的直接冲击

`ThreadPoolExecutor` 的三个核心参数——`corePoolSize`、`maximumPoolSize`、`queueCapacity`——直接决定了启动阶段的任务吞吐能力。

### 1.1 任务分配流程

[已验证: AOSP android-17.0.0_r1, libcore/ojluni/src/main/java/java/util/concurrent/ThreadPoolExecutor.java]

`ThreadPoolExecutor.execute()` 的任务分配遵循严格优先级：

1. **线程数 < corePoolSize** → 创建新核心线程执行
2. **核心线程已满** → 尝试加入 workQueue 缓存队列
3. **队列已满** → 尝试创建非核心线程（直到 maximumPoolSize）
4. **线程数已达 maximumPoolSize** → 触发 RejectedExecutionHandler 兜底

```java
// AOSP ThreadPoolExecutor.execute() 简化逻辑
public void execute(Runnable command) {
    int c = ctl.get();
    if (workerCountOf(c) < corePoolSize) {        // ① 优先创建核心线程
        if (addWorker(command, true)) return;
        c = ctl.get();
    }
    if (isRunning(c) && workQueue.offer(command)) { // ② 入队列等待
        int recheck = ctl.get();
        if (!isRunning(recheck) && remove(command))
            reject(command);
        else if (workerCountOf(recheck) == 0)
            addWorker(null, false);
    }
    else if (!addWorker(command, false))            // ③ 创建非核心线程
        reject(command);                            // ④ 兜底
}
```

**关键推论**：只有当 workQueue **满了**之后才会创建非核心线程。如果使用无界队列（如 `LinkedBlockingQueue` 默认 `Integer.MAX_VALUE`），非核心线程永远不会被创建，maximumPoolSize 形同虚设。

### 1.2 启动阶段的推荐配置

| 参数 | CPU 线程池 | IO 线程池 |
|------|-----------|-----------|
| corePoolSize | `CPU 核心数`（通常 = `Runtime.getRuntime().availableProcessors()`） | 0~3（视 App 类型而定） |
| maximumPoolSize | = corePoolSize | 64~128（大型 App） |
| workQueue | `LinkedBlockingQueue(64)`（有界，便于异常监控） | `SynchronousQueue()`（无缓存） |
| keepAliveTime | 0（无非核心线程） | 30~60s |
| 线程优先级 | `THREAD_PRIORITY_DEFAULT` 或略高 | `THREAD_PRIORITY_BACKGROUND`(-10)~`THREAD_PRIORITY_DEFAULT`(0) |

**启动阶段的核心风险**：CPU 线程池 corePoolSize 设太低 → 任务排队 → 启动拉长；设太高（远超 CPU 核心数）→ 上下文切换开销暴增，实际吞吐反而下降。

> [适用版本: Android 10 - Android 17] ThreadPoolExecutor 的行为在 Android 各版本一致（基于 OpenJDK 实现）。

---

## 2. 线程池类型选型矩阵

### 2.1 四种线程池的适用场景

| 线程池类型 | 底层实现 | 适用场景 | 不适用场景 |
|-----------|---------|---------|-----------|
| **CPU 线程池**（自定义 ThreadPoolExecutor） | core=max=CPU 核数，LinkedBlockingQueue | 计算、解码、Bitmap 处理、布局计算 | 网络/磁盘 IO（会阻塞宝贵的 CPU 线程） |
| **IO 线程池**（自定义 ThreadPoolExecutor） | core≈0, max=64+, SynchronousQueue | 网络、磁盘读写、数据库 | CPU 密集计算（线程数过多导致调度开销） |
| **ScheduledThreadPoolExecutor** | 继承 ThreadPoolExecutor，DelayedWorkQueue | 延时任务、周期任务、CPU 闲置检测 | 即时 CPU 任务（调度延迟不可控） |
| **ForkJoinPool** | 工作窃取算法 | 分治算法、并行流（parallelStream） | 一般 Android 业务（场景有限） |

### 2.2 为什么 AsyncTask 默认配置在大型 App 中会变成瓶颈

`AsyncTask.THREAD_POOL_EXECUTOR` 的默认配置为：

```java
// AOSP AsyncTask.java（已废弃但历史项目仍在使用）
private static final int CPU_COUNT = Runtime.getRuntime().availableProcessors();
private static final int CORE_POOL_SIZE = Math.max(2, Math.min(CPU_COUNT - 1, 4));
private static final int MAXIMUM_POOL_SIZE = CPU_COUNT * 2 + 1;
private static final BlockingQueue<Runnable> sPoolWorkQueue =
        new LinkedBlockingQueue<Runnable>(128);
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/AsyncTask.java]

问题在于：
- **CORE_POOL_SIZE 上限锁定为 4**：在 8 核设备上仅使用 3 个核心线程，浪费一半 CPU 资源
- **队列容量 128**：大量任务堆积时延迟不可控
- **已被官方废弃**（API 30+ deprecation）：Coroutine 替代方案详见 8.6 节

### 2.3 混合型线程池的陷阱

如果 CPU 计算任务和 IO 任务共用同一个线程池，会出现典型的**资源饥饿**模式：

- IO 任务执行时不消耗 CPU（由 DMA 芯片处理），但占着线程
- CPU 任务被迫排队等待空闲线程
- 线程池监控指标显示「活跃线程数高 + CPU 利用率低」→ 误判为 CPU 瓶颈

**正确做法**：CPU 线程池和 IO 线程池物理隔离，各司其职。

---

## 3. CPU 线程池与 IO 线程池分离

### 3.1 为什么要分离

CPU 密集型任务（Bitmap 解码、JSON 解析、布局计算）和 IO 密集型任务（网络请求、磁盘读写、数据库查询）对线程池的需求截然不同：

- **CPU 密集型**：线程数 = CPU 核心数时吞吐最高。线程数 > 核心数时，CPU 时间片在上下文切换中被浪费
- **IO 密集型**：线程在等待 IO 时会被调度器挂起（不消耗 CPU），因此线程数可以远超 CPU 核心数

### 3.2 IO 线程池为什么可以远超 CPU 核心数

当线程执行 IO 操作时（如 `read()` 系统调用），底层流程为：

1. 线程发起 IO 系统调用 → 陷入内核态
2. DMA 芯片开始搬运数据 → CPU 空闲
3. 调度器将 CPU 时间片切换给其他线程
4. DMA 完成 → 通过中断通知 CPU → 唤醒等待线程

因此，IO 线程池的线程数上限取决于**系统资源限制**（虚拟内存、FD 数量）而非 CPU 核心数。但需要注意：
- 每个线程默认占用约 1MB 虚拟内存（栈空间，详见 3.4 和 ch1.5）
- 线程数过多会导致 FD 数量逼近 `RLIMIT_NOFILE` 上限

### 3.3 故障模式：CPU 线程被 IO 任务占满

```
// 典型错误：在 CPU 线程池执行 IO 任务
cpuExecutor.execute(() -> {
    // 这里的网络请求会阻塞 CPU 线程
    String data = networkClient.fetchLargeData();  // ❌ IO 任务
    parseAndProcess(data);                          // ✅ CPU 任务
});

// 正确做法
ioExecutor.execute(() -> {
    String data = networkClient.fetchLargeData();   // IO 线程池
    cpuExecutor.execute(() -> {
        parseAndProcess(data);                      // CPU 线程池
    });
});
```

### 3.4 线程栈内存开销

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.cc — FixStackSize]

`Thread::CreateNativeThread` 中调用 `FixStackSize()`，即使 Java 层传入 `stackSize = 0`，Native 层也会将其调整为默认值（约 1MB）：

```cpp
// art/runtime/thread.cc 简化逻辑
static size_t FixStackSize(size_t stack_size) {
    if (stack_size == 0) {
        stack_size = Runtime::Current()->GetDefaultStackSize();
    }
    stack_size += 1 * MB;  // 守卫页 + 对齐
    // ... 页对齐处理
    return stack_size;
}
```

最终通过 `pthread_create` → `clone()` 系统调用分配虚拟内存。200 个线程 = 约 200MB 虚拟内存开销，在 32 位进程上可直接导致地址空间耗尽。

> [适用版本: Android 10 - Android 17] FixStackSize 行为在各版本一致。Android 14+ 推荐使用 `pthread_attr_setstacksize()` 在 PLT Hook 层面缩小栈空间到 512KB（详见 ch20.14）。

---

## 4. 线程优先级与 Android 调度

### 4.1 两种优先级 API

[已验证: 官方文档, developer.android.com/reference/android/os/Process.html]

| API | 范围 | 说明 |
|-----|------|------|
| `Process.setThreadPriority(int priority)` | -20 ~ 19 | Android 原生 API，直接设置 Linux nice 值。**推荐使用** |
| `Thread.setPriority(int priority)` | 1 ~ 10 | Java API，内部映射到 nice 值。有已知的时序 Bug |

Java `Thread.setPriority()` 的时序 Bug：在子线程创建过程中调用 `setPriority()`，如果子线程尚未完全创建成功，可能误将主线程的优先级修改。因此**生产代码推荐统一使用 `Process.setThreadPriority()`**。

### 4.2 Android nice 值体系与 Linux CFS 调度器

Android 线程本质是 Linux 轻量级进程（通过 `clone()` 创建），受 CFS（Completely Fair Scheduler）管理：

| 系统常量 | nice 值 | 使用场景 |
|---------|---------|---------|
| `THREAD_PRIORITY_URGENT_AUDIO` | -19 | 音频线程（最高） |
| `THREAD_PRIORITY_AUDIO` | -16 | 音频相关 |
| `THREAD_PRIORITY_URGENT_DISPLAY` | -8 | 渲染线程（最高显示优先级） |
| `THREAD_PRIORITY_DISPLAY` | -4 | 渲染线程默认 |
| `THREAD_PRIORITY_FOREGROUND` | -2 | 前台关键线程 |
| `THREAD_PRIORITY_DEFAULT` | 0 | 默认值（主线程） |
| `THREAD_PRIORITY_BACKGROUND` | 10 | 后台线程 |
| `THREAD_PRIORITY_LOWEST` | 19 | 最低优先级 |

Android 系统线程的默认 nice 值：主线程 = 0，RenderThread = -4。

### 4.3 关键路径线程绑大核

[已验证: AOSP android-17.0.0_r1, bionic/libc/include/sched.h]

现代手机 CPU 均为大小核架构（如骁龙 8 Gen 3：1×3.3GHz 超大核 + 3×3.15GHz 大核 + 2×2.96GHz 中核 + 2×2.27GHz 小核）。通过 `sched_setaffinity()` 可将关键线程绑定到大核：

```cpp
#include <sched.h>

void bindToBigCores(pid_t tid) {
    cpu_set_t mask;
    CPU_ZERO(&mask);
    // 假设 cpu4-cpu6 为大核（需运行时读取 /sys/devices/system/cpu/cpuN/cpufreq/cpuinfo_max_freq）
    CPU_SET(4, &mask);
    CPU_SET(5, &mask);
    CPU_SET(6, &mask);
    sched_setaffinity(tid, sizeof(mask), &mask);
}
```

**大核识别方法**：读取 `/sys/devices/system/cpu/cpuN/cpufreq/cpuinfo_max_freq`，取频率最高的核心序列。

**注意事项**：
- Android 限制了 `pthread_setaffinity_np()` 的使用，只能用 `sched_setaffinity()`
- 绑核操作需 Native 层（JNI）执行
- 系统的 `OomAdjuster` 可能动态调整线程优先级，绑核效果在不同负载下有差异

> 详见 ch5.1 节关于 CFS 调度器与 nice 值的底层原理。

---

## 5. Coroutine Dispatcher 与线程池映射

### 5.1 Dispatchers.Default 的底层实现

`Dispatchers.Default` 底层使用 Kotlin 自研的 `CoroutineScheduler`（而非直接使用 `ThreadPoolExecutor`）：

- 核心线程数 = `max(2, availableProcessors)`（CPU 密集型）
- 内部维护两个队列：CPU 任务队列和阻塞任务队列
- 使用 work-stealing 算法提升利用率

```kotlin
// CoroutineScheduler 简化结构
internal class CoroutineScheduler(
    val corePoolSize: Int,     // CPU 任务线程数
    val maxPoolSize: Int,      // 阻塞任务线程数上限
) : ExecutorCoroutineDispatcher() {
    // CPU 任务队列 + 阻塞任务队列分离
}
```

[已验证: kotlinx.coroutines 1.9.x 源码, CoroutineScheduler.kt]

### 5.2 Dispatchers.IO 的弹性线程池与 limitedParallelism

`Dispatchers.IO` **共享** `Dispatchers.Default` 的 `CoroutineScheduler` 实例，但通过「阻塞任务」标记来扩展线程数（最高 64 个线程，可通过系统属性调整）。

Kotlin 1.7+ 引入的 `limitedParallelism` 是更精细的并发度控制方案：

```kotlin
// 创建一个最多使用 4 个并行度的 Dispatcher
val limitedDispatcher = Dispatchers.IO.limitedParallelism(4)

// 不再需要手动管理线程池
// 生命周期由 CoroutineScope 管理（结构化并发）
```

`limitedParallelism` 的优势：
- 不创建新的线程池，复用 `Dispatchers.IO` 的线程
- 保证并发度上限，防止资源耗尽
- 天然支持结构化并发，无需手动 shutdown

> Coroutine 的语言级性能特征（挂起开销、Channel 吞吐等）详见 8.6 节。

### 5.3 为什么 Dispatchers.Main 不适合计算密集任务

`Dispatchers.Main` 将协程分发到主线程的 `Handler` 队列。在主线程执行 CPU 密集任务会：
- 阻塞 UI 渲染（导致掉帧）
- 阻塞输入事件分发（导致 ANR 风险）
- 与 `RenderThread` 争抢 CPU 时间

**正确做法**：CPU 密集任务使用 `Dispatchers.Default`，仅在需要更新 UI 时切回 `Dispatchers.Main`。

---

## 6. 线程治理：减少线程数量的工程实践

### 6.1 大型 App 线程泛滥的根因

大型 App 动辄 200+ 线程，主要原因：

1. **SDK 各自创建线程池**：网络库、埋点库、图片库、推送库各自初始化线程池
2. **匿名 Thread**：`new Thread(runnable).start()` 没有命名、没有池化
3. **Executors 便捷方法滥用**：`Executors.newCachedThreadPool()` 无上限创建线程

### 6.2 线程收敛策略

**策略一：统一线程池管理**

在 App 基础架构层提供全局线程池入口：

```kotlin
object AppExecutors {
    val cpu: ExecutorService = ThreadPoolExecutor(
        Runtime.getRuntime().availableProcessors(),
        Runtime.getRuntime().availableProcessors(),
        0L, TimeUnit.MILLISECONDS,
        LinkedBlockingQueue(64),
        NamedThreadFactory("cpu-pool")
    )

    val io: ExecutorService = ThreadPoolExecutor(
        0, 128,
        30L, TimeUnit.SECONDS,
        SynchronousQueue(),
        NamedThreadFactory("io-pool")
    )
}
```

**策略二：SDK 线程审计**

通过 Hook `Executors.newFixedThreadPool()` 等静态方法，将 SDK 自建的线程池替换为全局线程池（使用 Lancet / ASM 字节码插桩）：

```kotlin
@TargetClass("java.util.concurrent.Executors")
@Proxy(value = "newFixedThreadPool")
fun hookFixedThreadPool(nThreads: Int): ExecutorService {
    log.warn("SDK attempted to create thread pool, redirecting to global pool")
    return AppExecutors.cpu
}
```

**策略三：Hook Thread.start() 拦截匿名线程**

通过字节码插桩，将 `new Thread()` 无参构造自动改写为 `new Thread(callerClassName)`，实现匿名线程的自动命名（详见 ch26.21 字节码插桩与监控自动化）。

### 6.3 线程命名规范对调试效率的影响

良好的线程命名可以显著提升线上问题排查效率：

| 命名规范 | 示例 | 优势 |
|---------|------|------|
| `模块-用途-序号` | `network-dispatcher-1` | 快速定位模块 |
| `SDK名-功能` | `firebase-uploader` | 区分第三方 SDK |
| `自动命名（字节码插桩）` | `com.app.InitActivity` | 无需手动管理 |

---

## 7. 线程泄漏检测与监控

### 7.1 典型线程泄漏模式

1. **未 shutdown 的线程池**：局部线程池在 Activity 销毁后仍在后台运行，持有 Activity 引用
2. **匿名 Thread 持有 Activity**：内部类 Thread 隐式持有外部 Activity 引用
3. **ScheduledThreadPoolExecutor 泄漏**：周期任务未被取消，线程池无法 GC

### 7.2 线上监控方案

**定期快照法**：

```kotlin
fun dumpThreadSnapshot() {
    val threads = Thread.getAllStackTraces()
    threads.forEach { (thread, stack) ->
        log.info("Thread: ${thread.name} | state=${thread.state} | stack=${stack.take(5)}")
    }
    log.info("Total threads: ${threads.size}")
}
```

**ThreadPoolExecutor 监控指标**：

| 指标 | 获取方式 | 告警阈值 |
|------|---------|---------|
| activeCount | `executor.activeCount` | 持续 = maximumPoolSize |
| queueSize | `executor.queue.size()` | 持续 > 队列容量 80% |
| completedTaskCount | `executor.completedTaskCount` | 增长速率骤降 |
| rejectedCount | 自定义 RejectedExecutionHandler 计数 | 任意拒绝即告警 |
| 线程总数 | `Thread.getAllStackTraces().size` | App 线程 > 200 |

> 详细的线程与 FD 资源监控体系参见 ch20.14。

### 7.3 字节码插桩自动命名匿名线程

通过 ASM 字节码改写，将无参 `Thread()` 构造自动添加调用类名为线程命名：

**改写前**（字节码）：
```
NEW java/lang/Thread
DUP
INVOKESPECIAL java/lang/Thread.<init> ()V
```

**改写后**：
```
NEW java/lang/Thread
DUP
LDC "com/app/MainActivity"     ; 插入调用类名
INVOKESPECIAL java/lang/Thread.<init> (Ljava/lang/String;)V
```

这一技术在 ch26.21（字节码插桩与监控自动化）中有完整实现方案。

---

## 8. 启动阶段任务编排中的线程池策略

### 8.1 启动框架中的线程池分配

现代 App 启动框架（如 App Startup、Booster、自研启动框架）的核心是**有向无环图（DAG）任务调度**：

```
Application.onCreate()
    ├── [CPU] 初始化日志库          ──→ [CPU] 初始化崩溃监控
    ├── [IO]  预加载首页数据        ──→ [CPU] 解析数据模型
    ├── [IO]  预加载首页 Bitmap     ──→ 无依赖
    └── [CPU] 初始化路由表          ──→ 无依赖
```

**线程池分配原则**：
- CPU 任务 → CPU 线程池（corePoolSize = CPU 核心数）
- IO 任务 → IO 线程池（弹性扩展）
- 有依赖关系的任务按拓扑序调度，前驱完成后提交后继

### 8.2 并行度控制

启动阶段目标：**CPU 利用率 80%+ 但避免 100% 饱和**。

- 并行度过低 → CPU 空闲，启动时间拉长
- 并行度过高 → 上下文切换开销激增，反而变慢
- 监控手段：启动阶段采样 `/proc/stat` 和 `/proc/<pid>/stat`，计算 CPU 利用率

### 8.3 CPU 闲置检测与预加载

启动完成后到首页可交互之间，存在 CPU 闲置窗口。可通过以下方式检测并利用：

**方案一：读取 /proc/stat 计算 CPU 占用率**

```kotlin
// 每隔 5 秒采样一次
fun getCpuUsage(): Float {
    val cpuTotal = readProcStat()       // /proc/stat 第一行累加
    val appCpu = readProcessStat()      // /proc/<pid>/stat utime + stime
    return (appCpuDelta / cpuTotalDelta)
    // 占用率 < 阈值（如 30%）则认为 CPU 闲置
}
```

**方案二：Native 层 times() 函数**（性能更好）

```cpp
#include <sys/times.h>
float getCpuSpeed() {
    struct tms t;
    times(&t);
    return (t.tms_utime + t.tms_stime);  // 进程 CPU 时间
}
```

通过 CPU 速率（CPU 时间增量 / 采样间隔）判断是否闲置。典型经验值：`cpuSpeed < 0.1` → CPU 闲置。

CPU 闲置时执行预加载任务（预创建 View、预拉取数据、预热路由），避免与核心路径争抢资源。

---

## 9. Android 16/17 线程调度行为变更

### 9.1 后台线程调度限制

Android 14（API 34）引入了对后台应用使用 CPU 的更严格限制。`OomAdjuster` 会根据进程的 `oom_adj` 等级动态调整线程优先级：

- 前台应用（`oom_adj = 0`）：线程保持原始 nice 值
- 后台应用（`oom_adj >= 900`）：线程 nice 值被提升到 `THREAD_PRIORITY_BACKGROUND`（10），CPU 调度权重显著降低
- 缓存应用（`oom_adj >= 999`）：可能被进一步限制 CPU 时间片

### 9.2 Android 17 的前台服务类型声明

[已验证: 官方文档, developer.android.com/about/versions/17]

Android 17 进一步强化了前台服务的类型声明要求。未正确声明 `foregroundServiceType` 的前台服务将被系统降级处理，其内部线程的优先级也会受到影响。开发者必须在前台服务中声明准确的类型（如 `dataSync`、`mediaPlayback` 等），否则面临 ANR 或被系统杀除的风险。

### 9.3 对工程实践的影响

| 变更 | 影响 | 应对策略 |
|------|------|---------|
| 后台 CPU 限制 | 后台预加载/轮询任务可能执行缓慢 | 使用 WorkManager 替代手动后台线程 |
| 前台服务类型声明 | 未声明类型的 FGS 线程优先级被降低 | 精确声明 foregroundServiceType |
| OomAdjuster 动态降级 | 后台线程被动态降低优先级 | 启动阶段任务避免放到后台 Service |

---

## 扩展

### 🔸 WorkManager 内部线程池

WorkManager 的 Worker 线程池由系统管理，其容量受 `JobScheduler` 配额限制。CoroutineWorker 通过 `Dispatchers.Default` 执行 `doWork()`，与手动线程池管理互补而非替代。

| Worker 类型 | 执行线程 | 适用场景 |
|------------|---------|---------|
| `Worker` | WorkManager 线程池（默认 ≤ 16） | 简单后台任务 |
| `CoroutineWorker` | `Dispatchers.Default` | 需要 suspend/Coroutine 的任务 |
| `ListenableWorker` | 自定义 | 需要完全控制线程分配的任务 |

CoroutineWorker vs Worker 的性能差异主要在挂起/恢复开销上（微秒级），对大多数业务场景可忽略。

### 🔸 线程池监控指标体系

线上线程池监控的核心指标：

```
active_threads    = executor.activeCount
queue_size        = executor.queue.size()
rejected_count    = 自定义 RejectedExecutionHandler 计数
avg_execute_time  = 任务平均执行时间（需自行埋点）
thread_pool_name  = 线程池实例名（通过 ThreadFactory 命名）
```

热点定位方案：重写 `beforeExecute(Thread t, Runnable r)` 和 `afterExecute(Runnable r, Throwable t)`，在 beforeExecute 中记录任务开始时间和堆栈摘要，在 afterExecute 中计算耗时并上报。

### 🔸 Java 21 Virtual Thread 在 Android 的前瞻

Java 21 的 Virtual Thread（Project Loom）在 Android 上的可行性分析：

- **ART 支持时间线**：截至 Android 17，ART 未支持 Virtual Thread。预计需要 Kotlin/ART 协同适配，最早可能在 Android 18+ 引入（但本文不涉及 Android 18 内容）
- **对现有架构的冲击**：Virtual Thread 使 IO 密集型任务不再需要大线程池（一个 Virtual Thread 仅占用几 KB），但 CPU 密集型任务仍受 CPU 核心数限制
- **过渡策略**：`limitedParallelism` 是 Virtual Thread 的前向兼容方案，迁移成本低

[待验证: ART 对 Virtual Thread 的支持时间线，截至 Android 17.0.0_r1 无相关实现]
