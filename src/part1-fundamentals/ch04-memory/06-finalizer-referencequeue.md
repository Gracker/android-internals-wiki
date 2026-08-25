---
title: ART FinalizerDaemon、Cleaner 与 ReferenceQueue
chapter: '4.6'
section: '4.6'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-06-09'
last_verified_against: AOSP android-16.0.0_r1 libcore + Android Developers API reference (Cleaner/CloseGuard/SystemCleaner) + Oracle Java SE 8 ReferenceQueue API
confidence: medium
sources:
- type: research
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-09-art-finalizerdaemon-referencequeue-concurrency.md
- type: aosp
  path: platform/libcore/android-16.0.0_r1/ojluni/src/main/java/java/lang/ref/ReferenceQueue.java
- type: aosp
  path: platform/libcore/android-16.0.0_r1/libart/src/main/java/java/lang/Daemons.java
- type: official
  path: https://developer.android.com/reference/android/util/CloseGuard
- type: official
  path: https://developer.android.com/reference/android/os/StrictMode
- type: official
  path: https://docs.oracle.com/javase/8/docs/api/java/lang/ref/ReferenceQueue.html
tags:
- art
- gc
- memory
- finalizer
- referencequeue
- performance
related_chapters:
- '4.2'
- '4.4'
- '23.2'
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
---

# ART FinalizerDaemon、Cleaner 与 ReferenceQueue

看到 `FinalizerDaemon` 忙、文件描述符（FD）数量上涨或 CloseGuard 告警时，先把几个相邻概念分开：

- GC 判断对象的可达性，并把需要后续处理的 `Reference` 交给引用处理机制。
- `ReferenceQueueDaemon` 把 GC 提供的待处理（pending）引用转移到目标 `ReferenceQueue`。
- `FinalizerDaemon` 串行执行 `finalize()`，也负责 Android 共享 `SystemCleaner` 的清理动作。
- 应用代码负责在明确的生命周期边界释放文件描述符、套接字、游标、图形缓冲区和原生资源句柄。

前三项属于运行时机制，最末项才是资源所有权。运行时可以延后清理，也可能在进程结束前来不及执行；因此不能用 GC 是否发生来证明资源已经释放。

源码以 AOSP `android-17.0.0_r1` 的 `platform/libcore` 为锚点。`ReferenceQueue.java`、`FinalizerReference.java` 和 `Daemons.java` 共同定义了 Android 17 的引用入队、对象终结和超时监控行为。

## 1. 一张表分清四个角色

| 角色 | 输入 | 主要动作 | 不提供的保证 |
|---|---|---|---|
| GC 的引用处理 | 对象图和各类 `Reference` | 判定引用状态，生成待入队引用 | 不关闭应用资源 |
| `ReferenceQueueDaemon` | `ReferenceQueue.unenqueued` | 把待处理引用批量放入各自队列；处理旧式 `sun.misc.Cleaner` | 不消费应用自己的 `ReferenceQueue` |
| `FinalizerDaemon` | `FinalizerReference.queue` | 调用 `finalize()`；执行 `SystemCleaner` 的 `Cleanable` | 不保证资源何时释放 |
| 资源所有者 | 明确的业务生命周期 | 调用 `close()`、`release()` 或原生释放函数 | 不应等待对象不可达后才开始释放 |

`ReferenceQueue` 是引用对象的容器。应用创建弱引用 `WeakReference`、虚引用 `PhantomReference` 和对应队列后，还需要自己消费队列；ART 只负责把符合条件的引用放进去。虚引用通常用于在对象已不能恢复访问后接收清理通知，但通知到达时间仍由 GC 和调度决定。

`FinalizerDaemon` 是进程内的单线程守护线程。这里的 finalizer 指对象的 `finalize()` 终结方法；某个终结方法或系统 Cleaner 动作耗时过长，会推迟同一队列后面的所有工作。

## 2. Android 17 的对象终结路径

### 2.1 可终结对象先注册 `FinalizerReference`

Android 17 的隐藏类 `java.lang.ref.FinalizerReference` 为每个需要执行 `finalize()` 的对象维护一个引用节点。运行时调用 `FinalizerReference.add()` 后，节点进入由 `LIST_LOCK` 保护的双向链表。

关键字段可以简化为：

```java
// platform/libcore, android-17.0.0_r1
// luni/src/main/java/java/lang/ref/FinalizerReference.java
public static final ReferenceQueue<Object> queue = new ReferenceQueue<>();

private static final Object LIST_LOCK = new Object();
private static FinalizerReference<?> head;

private T zombie;
```

这里有两套独立结构：

- `head` 指向的链表覆盖堆中所有可终结对象，对象此时可能仍然可达。
- `queue` 只存放已经具备执行终结条件的 `FinalizerReference`。

`FinalizerReference.get()` 返回 `zombie`，而非普通的 `Reference.referent`。`zombie` 是源码字段名，表示等待终结方法处理期间用于保留对象的引用，并不表示资源已经释放。GC 判定对象需要终结时，会把对象从 `referent` 移到 `zombie`，使它在 `finalize()` 执行前仍保持可访问。

### 2.2 GC 先交给 `ReferenceQueueDaemon`

GC 产生的待处理引用通过静态字段 `ReferenceQueue.unenqueued` 交给 Java 层。`ReferenceQueueDaemon` 在 `ReferenceQueue.class` 上等待；拿到一批引用后，先把全局字段置空，再调用：

```java
ReferenceQueue.enqueuePending(list, progressCounter);
```

这一段只负责把引用从待处理链表转移到目标队列。对于 `FinalizerReference`，目标队列就是 `FinalizerReference.queue`。

Android 17 还在这个循环里观察全堆 GC 计数。当没有待处理引用且发现全堆 GC 次数增加时，它会调用 `VMRuntime.onPostCleanup()`。这属于运行时的 GC 后处理，不能据此推断某个业务资源已经关闭。

### 2.3 `FinalizerDaemon` 串行执行

`FinalizerDaemon` 先用非阻塞的 `poll()` 处理已有元素；队列为空后，关闭看门狗（watchdog）的活动标记并在 `remove()` 上阻塞等待。取到元素后，`processReference()` 区分两类对象：

```java
private void processReference(Object ref) {
    if (ref instanceof FinalizerReference finalizingReference) {
        finalizingObject = finalizingReference.get();
        try {
            doFinalize(finalizingReference);
        } finally {
            Reference.reachabilityFence(finalizingObject);
        }
    } else if (ref instanceof Cleaner.Cleanable cleanableReference) {
        finalizingObject = cleanableReference;
        doClean(cleanableReference);
    } else {
        throw new AssertionError("Unknown class was placed into queue: " + ref);
    }
}
```

这段代码有三个重要细节：

1. 普通终结方法和 `SystemCleaner` 共用同一个 `FinalizerDaemon`。
2. `reachabilityFence(finalizingObject)` 强制让对象保持可达直到终结处理结束，避免后续 `PhantomReference` 过早入队。
3. 该线程只有一个；队首的慢任务会推迟后续任务。

`doFinalize()` 的顺序是：

1. 从全部终结引用的链表中移除当前节点。
2. 从 `zombie` 取出对象。
3. 清空引用节点。
4. 调用 `object.finalize()`。
5. 清掉守护线程持有的 `finalizingObject`。

Android 会记录 `finalize()` 抛出的异常。常规情况下，这类异常不会沿业务调用栈传播；如果异常日志记录过程本身也长时间卡住，看门狗还有专门的超时处理。

Java 允许终结方法把对象重新放回可达对象图，这种行为称为对象复活。终结机制并不会因此成为可靠的复用协议；对象复活会显著增加生命周期推理难度，工程代码应禁止这种做法。

## 3. `ReferenceQueue` 的同步边界

### 3.1 每个队列一把实例锁，队内保持先进先出

Android 17 的 `ReferenceQueue` 用 `head`、`tail` 和私有 `lock` 实现先进先出（FIFO）：

```java
private Reference<? extends T> head;
private Reference<? extends T> tail;
private final Object lock = new Object();

public Reference<? extends T> poll() {
    synchronized (lock) {
        return reallyPollLocked();
    }
}
```

`poll()` 立即返回；`remove(timeout)` 在同一把锁上调用 `wait()`，入队方完成修改后调用 `notifyAll()`。`wait()` 会释放锁，因此阻塞消费者不会持续占住入队锁。

由此得到的并发边界是：

- 不同 `ReferenceQueue` 有不同实例锁。
- 同一个队列的头尾修改串行进行。
- 队列锁只保护引用节点，不保护引用关联的业务资源。
- 入队成功只说明引用可以被消费者看到，不说明清理动作已经完成。

### 3.2 `enqueuePending()` 按相邻同队列引用批处理

GC 交来的待处理链表可能包含多个目标队列。Android 17 会把连续指向同一个队列的引用放在一次加锁区间内处理：

```java
final int MAX_ITERS = 100;
int i = 0;
synchronized (queue.lock) {
    do {
        Reference<?> next = list.pendingNext;
        list.pendingNext = list;
        queue.enqueueLocked(list);
        list = next;
    } while (list != start
            && list.queue == queue
            && ++i < MAX_ITERS);
    queue.lock.notifyAll();
}
progressCounter.incrementAndGet();
```

`MAX_ITERS = 100` 限制一个批次的规模，也让 `ReferenceQueueDaemon.progressCounter` 能够定期更新，供看门狗判断线程是否仍在推进。

需要准确理解这个计数器：

- 普通引用按“同队列批次”递增，不是每处理一个引用都递增。
- 旧式 `sun.misc.Cleaner` 每处理一个就递增。
- `FinalizerDaemon` 有自己的 `progressCounter`，两者互不共用。
- 该数值是运行时内部的活性信号，不是公开的队列长度或性能指标。

### 3.3 Android 17 没有接入 `ConcurrentMessageQueue`

在 `android-17.0.0_r1` 的 `ReferenceQueue.java`、引用类目录和 `Daemons.java` 中，`ReferenceQueue` 仍采用上述 FIFO、实例锁和批处理实现，没有 `ConcurrentMessageQueue` 接入点。

消息队列的并发改动不能外推到 Java 引用队列。分析引用处理性能时，应以 `ReferenceQueue.enqueuePending()`、队列锁持有区间和两个守护线程的实际状态为依据。

## 4. 看门狗监控的精确含义

`FinalizerWatchdogDaemon` 同时观察：

- `FinalizerDaemon` 是否长时间没有推进；
- `ReferenceQueueDaemon` 是否长时间没有推进。

超时时间来自 `VMRuntime.getFinalizerTimeoutMs()`，不应在应用文档里写成固定秒数。厂商配置、运行环境和后续平台版本都可能影响具体值。

看门狗把一个超时窗口分成 5 次唤醒。每次醒来都会比较活动标记和进度计数器，这能降低进程被冻结或线程没有获得 CPU 调度时的误判概率。

两种超时的判定力度不同：

| 监控对象 | 可疑状态 | 上报策略 |
|---|---|---|
| `FinalizerDaemon` | 一个终结方法或 `SystemCleaner` 动作跨过完整超时窗口仍无进展 | 当次即可构造 `TimeoutException` |
| `ReferenceQueueDaemon` | 一个旧 Cleaner 或同队列批处理长期没有可见进展 | 容忍计数为 5；同一段未完成处理期间第 6 次被判定超时才构造异常 |

一批待处理引用完成转移后，`ReferenceQueueDaemon` 会重置其超时观察计数。这个容忍机制是因为该线程不会在每处理一个引用后都更新进度。

确认超时且调试器未连接时，看门狗会先给本进程发送 `SIGQUIT`，留出时间记录原生线程栈，再把超时异常交给未捕获异常处理机制。由 Zygote 派生的应用进程通常会由 `RuntimeInit` 的处理器生成崩溃报告并终止。调试器连接期间，源码明确跳过这次致命超时处理。

“看到 FinalizerDaemon 很忙”和“看门狗判定进程必须终止”之间，还有进度、超时窗口、调试器状态等条件。诊断报告要保留这些条件。

## 5. Android 17 的三种 Cleaner 路径

Cleaner 这个名字覆盖了三套执行模型。混写它们会直接导致线程归因错误。

### 5.1 平台旧实现：`sun.misc.Cleaner`

`sun.misc.Cleaner` 是平台内部实现，不属于应用可依赖的稳定 SDK。它继承 `PhantomReference`，使用一个只用于识别这条处理路径的占位队列。

`ReferenceQueue.enqueuePending()` 识别到这个占位队列后，不把引用放进普通队列，而是在 `ReferenceQueueDaemon` 上直接调用 `clean()`：

```text
GC pending list
  -> ReferenceQueueDaemon
     -> ReferenceQueue.enqueuePending()
        -> sun.misc.Cleaner.clean()
           -> thunk.run()
```

图中的 `thunk.run()` 是旧 Cleaner 包装的实际清理动作。因此，这类慢动作会卡住全进程的 `ReferenceQueueDaemon`，连带推迟其他引用入队。应用不应通过反射或隐藏 API 依赖这套实现。

### 5.2 公开 `java.lang.ref.Cleaner.create()`

`java.lang.ref.Cleaner` 从 API 33 起成为 Android 公共 API。每次调用 `Cleaner.create()` 都会创建一个由 `CleanerImpl` 管理的守护线程，默认名称形如 `Cleaner-0`：

```text
Cleaner.create()
  -> CleanerImpl.start()
     -> 独立 daemon 线程
        -> queue.remove(60 s)
           -> Cleanable.clean()
```

该线程会捕获并忽略清理动作抛出的 `Throwable`。一个动作阻塞时，会推迟注册在同一个 Cleaner 上的其他动作，但不会直接占住 `ReferenceQueueDaemon` 或 `FinalizerDaemon`。

独立 Cleaner 提供线程隔离，也会增加线程和栈空间成本。库不宜各自无条件创建 Cleaner；是否共享要依据清理动作的耗时、阻塞风险和故障隔离需求决定。

### 5.3 `android.system.SystemCleaner`

`SystemCleaner.cleaner()` 同样从 API 33 起公开。它返回进程共享的 Cleaner，内部通过隐藏入口 `Cleaner.createSystemCleaner()` 把队列设置为 `FinalizerReference.queue`：

```text
SystemCleaner.cleaner()
  -> shared Cleaner
     -> FinalizerReference.queue
        -> FinalizerDaemon.processReference()
           -> Cleanable.clean()
```

官方契约要求这类动作快速结束，并避免显式 I/O、IPC 和网络访问，原因如下：

- 全进程共享，同一个动作会挡住后续共享清理动作；
- 它与普通终结方法共用 `FinalizerDaemon`，还受终结器看门狗监控。

`SystemCleaner` 不会忽略共享守护线程上未捕获的清理异常，异常通常会导致进程崩溃并暴露问题。这与 `Cleaner.create()` 的独立线程行为不同。

### 5.4 三者对比

| 类型 | Android 17 执行线程 | 慢动作的主要影响 | 异常边界 |
|---|---|---|---|
| `sun.misc.Cleaner` | `ReferenceQueueDaemon` | 阻塞全进程的待处理引用转移 | 内部实现，不提供应用兼容承诺 |
| `Cleaner.create()` | 每个 Cleaner 自己的守护线程 | 阻塞同一 Cleaner 的后续动作 | 后台线程忽略清理动作异常 |
| `SystemCleaner.cleaner()` | `FinalizerDaemon` | 阻塞共享 Cleaner 和普通终结方法 | 未捕获异常通常导致进程崩溃 |

三种机制都只保证清理动作至多执行一次，不保证 GC 触发时间，也不保证动作一定会在进程退出前执行。

## 6. 正确的资源所有权设计

### 6.1 主路径必须显式关闭

资源包装类应满足四个条件：

1. 所有者明确，创建者知道由谁关闭；
2. `close()` 幂等；
3. 正常、异常和取消路径都会关闭；
4. 兜底清理只处理遗漏，不负责日常释放流量。

Java 用 `try-with-resources`，Kotlin 用 `use`：

```kotlin
fun decode(path: String): Result {
    ParcelFileDescriptor.open(
        File(path),
        ParcelFileDescriptor.MODE_READ_ONLY
    ).use { descriptor ->
        return decodeFromFd(descriptor.fileDescriptor)
    }
}
```

`use` 把关闭动作绑定到词法作用域。`decodeFromFd()` 正常返回或抛出异常时，`ParcelFileDescriptor.close()` 都会执行。

### 6.2 Cleaner 清理动作不能捕获所有者

Cleaner 只会在所有者进入虚可达（phantom reachable）状态后自动执行。虚可达表示 GC 已确认对象不能再通过普通、软或弱引用访问，但相应虚引用还可以收到入队通知。如果清理动作直接或间接引用所有者，所有者会一直保持强可达，自动清理也就永远没有机会开始。

以下 Java 示例适用于 API 33 及以上。它使用静态嵌套状态对象，并用 `AtomicLong.getAndSet(0)` 让原生资源句柄最多释放一次：

```java
final class NativeSession implements AutoCloseable {
    private static final Cleaner CLEANER = SystemCleaner.cleaner();

    private static final class State implements Runnable {
        private final AtomicLong handle;

        State(long handle) {
            this.handle = new AtomicLong(handle);
        }

        @Override
        public void run() {
            long value = handle.getAndSet(0L);
            if (value != 0L) {
                nativeRelease(value);
            }
        }
    }

    private final State state;
    private final Cleaner.Cleanable cleanable;

    NativeSession(long handle) {
        state = new State(handle);
        cleanable = CLEANER.register(this, state);
    }

    @Override
    public void close() {
        cleanable.clean();
    }

    private static native void nativeRelease(long handle);
}
```

这里的 `State` 不持有 `NativeSession`。显式调用 `close()` 时，`cleanable.clean()` 在调用线程执行释放；遗忘关闭时，SystemCleaner 才提供延迟兜底。

如果 `nativeRelease()` 可能等待 Binder、磁盘、网络或不可控锁，这个清理动作就不适合 `SystemCleaner`。应把耗时释放设计成可显式等待或受控调度的业务操作，Cleaner 中只保留快速、有限、不会阻塞的最后一道防线。

低于 API 33 的设备不能直接假设存在公共 `java.lang.ref.Cleaner`。项目可以在兼容层选择其他实现，但 `AutoCloseable` 的调用契约应保持一致。不要把隐藏的 `sun.misc.Cleaner` 当作兼容方案；API 脱糖（desugaring）会把部分新版 Java API 改写或补充到旧系统，若没有验证构建配置和运行时语义，也不能断言它与 Android 17 原生 Cleaner 完全等价。

### 6.3 CloseGuard 负责定位遗漏

公共 `android.util.CloseGuard` 从 API 30 起可用。典型使用顺序是：

1. 获取资源后 `open("close")`，记录获取位置；
2. 显式关闭后调用 `close()`；
3. 兜底检查阶段调用 `warnIfOpen()`。

CloseGuard 的输出用于回答“资源在哪里获取却没有关闭”。它不释放资源，也不保证告警何时出现。只记录一条告警而不修复所有者生命周期，文件描述符和原生内存仍会继续增长。

### 6.4 StrictMode 负责尽早暴露问题

调试包和自动化测试可开启：

```kotlin
StrictMode.setVmPolicy(
    StrictMode.VmPolicy.Builder()
        .detectLeakedClosableObjects()
        .penaltyLog()
        .build()
)
```

`detectLeakedClosableObjects()` 从 API 11 起提供，用来发现 `Closeable` 在没有显式关闭的情况下走到终结处理。设置虚拟机策略（VM policy）会替换当前进程策略，项目应在统一的调试初始化入口合并其他检测项，避免多个模块互相覆盖。

StrictMode 适合在开发和持续集成（CI）阶段尽早暴露错误。生产环境是否启用、采用日志还是更强的处罚策略（penalty），需要结合噪声、性能和隐私要求评估。

## 7. 队列堆积为何表现为内存或卡顿

### 7.1 可终结对象仍占用资源

对象进入终结处理后，`FinalizerReference.zombie` 会在 `finalize()` 开始前保留它。Java 包装对象可能很小，但它代表的资源可能很大：

- 一个文件或套接字的文件描述符；
- SQLite 游标与 `CursorWindow`；
- 原生堆中的解码缓冲区；
- GraphicBuffer、ImageReader image 或 Surface；
- JNI 全局引用和它间接保活的对象图。

因此，Java 堆变化不大，而原生堆或图形内存持续上涨，是合理且常见的组合。浅层大小（shallow size）只统计对象本身直接占用的 Java 堆空间；只按这个值排序会漏掉对象间接持有的原生和图形资源。

### 7.2 单线程清理形成排队等待

`FinalizerDaemon` 串行处理普通终结方法和 SystemCleaner。假设每个动作只耗时 20 ms，前面堆积 500 个对象时，队尾对象也可能等待很久。这里不能用固定公式预测线上延迟，因为 GC 触发、线程调度和清理耗时都在变化；但只要生成速度长期高于消费速度，积压就会扩大。

慢清理一般不会直接运行在主线程，却仍可能造成：

- 与主线程争抢 CPU；
- 持有主线程需要的原生或 Java 锁；
- 发起 Binder、文件系统操作，增加系统服务压力；
- 推迟文件描述符和图形缓冲区归还，最终触发资源耗尽；
- 被看门狗判定为超时，导致进程崩溃。

## 8. 诊断顺序：先证明增长，再定位执行点

### 8.1 建立可重复的资源曲线

先定义一轮固定操作，例如进入页面、打开资源、完成任务、退出页面。每轮结束后记录同一组指标：

```bash
adb shell pidof com.example.app
adb shell dumpsys meminfo com.example.app
# 假设上一条 pidof 返回 12345
adb shell ls /proc/12345/fd
```

`/proc/<pid>/fd` 在量产设备上可能受权限和 SELinux 限制；无权限时应使用可调试构建、受控测试设备或应用自己的诊断计数。不能把“命令被拒绝”写成“文件描述符没有增长”。

比对时关注趋势：

- 每轮净增，且离开页面后不回落；
- 只在 GC 后部分回落；
- Java 堆回落，原生堆或图形内存不回落；
- 文件描述符达到某一水平后出现 `EMFILE`（进程打开文件数达到上限）、打开文件失败或套接字异常。

一次采样只能给出快照。稳定复现、多个时间点和同一测试基线的对照更有判断力。

### 8.2 收集日志和线程栈

重点日志包括：

- `A resource was acquired ... but never released` 一类 CloseGuard 告警；
- StrictMode 的可关闭资源泄漏违规；
- `Uncaught exception thrown by finalizer`；
- `FinalizerDaemon` 或 `ReferenceQueueDaemon` 超时；
- 文件描述符、ashmem、gralloc、SQLite 或相机模块的资源失败。

在有权限的可调试环境中，可用下面的命令获取 Java 与原生线程栈：

```bash
# 假设目标 PID 是 12345
adb shell debuggerd -b 12345
```

判断线程栈时，先看具体执行点：

| 线程 | 常见栈位置 | 能支持的结论 |
|---|---|---|
| `ReferenceQueueDaemon` | `enqueuePending()` 普通分支 | 正在转移待处理引用 |
| `ReferenceQueueDaemon` | 某个 `sun.misc.Cleaner.clean()` | 平台旧 Cleaner 动作可能阻塞引用队列守护线程 |
| `FinalizerDaemon` | 某类 `finalize()` | 该类终结代码正在执行 |
| `FinalizerDaemon` | `Cleaner.Cleanable.clean()` | `SystemCleaner` 清理动作正在执行 |
| `Cleaner-N` | `CleanerImpl.run()` 或业务清理动作 | 某个独立 Cleaner 正在处理 |

只看到线程处于可运行（RUNNABLE）状态，不能证明它连续消耗了整个时间窗口；需要多次栈快照或调度性能轨迹确认。

### 8.3 Perfetto 和 simpleperf 各回答什么

Perfetto 可用来观察：

- 守护线程何时获得 CPU、运行了多久；
- 守护线程的运行区间是否与主线程掉帧重叠；
- 是否伴随 Binder、文件系统或调度等待；
- GC、堆变化和应用生命周期事件的时间关系。

Perfetto 默认没有公开的 `FinalizerReference.queue` 深度计数器。线程轨道繁忙只能说明守护线程活跃，不能单独证明队列里有多少对象。

simpleperf 适合在 CPU 异常时查找热点函数；具备符号和可展开调用栈时，采样结果会包含原生清理函数或锁竞争相关调用。它也不提供引用队列长度；阻塞型问题仅看 CPU 剖析，可能没有明显热点。

### 8.4 堆转储能做什么

堆转储适合：

- 比较资源包装对象的实例数；
- 查仍被业务对象、缓存或 JNI 引用保活的所有者；
- 观察 `FinalizerReference`、Cleaner 状态对象等相关对象数量；
- 对比操作前后的类直方图和保留关系。

堆转储不能直接证明“这些对象都不可达，只是在等待终结方法”。生成 HPROF 本身会触发暂停和运行时活动，工具对终结状态、原生资源所有权的呈现也有限。结论需要和线程栈、资源计数、日志及原生侧证据互相印证。

## 9. 原生资源排查模板

| 资源 | Java 包装对象 | 释放动作 | 首选证据 | 常见遗漏位置 |
|---|---|---|---|---|
| 文件描述符 / 套接字 | `ParcelFileDescriptor`、流、网络连接 | `close()` | 文件描述符计数、CloseGuard、异常日志 | 异常、取消、重试 |
| SQLite | `Cursor`、`CursorWindow`、语句对象 | `close()` | StrictMode、SQLite 日志、`meminfo` | 提前返回、分页切换 |
| ImageReader / Image | `Image`、读取器或会话包装对象 | `close()` | 相机日志、图形内存、BufferQueue 性能轨迹 | 回调异常、消费速度不足 |
| Surface / GraphicBuffer | Surface 类包装对象 | `release()` / `close()` | Perfetto、`dumpsys`、图形内存 | 页面销毁、重建 |
| Bitmap / 原生分配 | `Bitmap` 与缓存所有者 | 移除强引用、按 API 契约回收关联资源 | 堆、原生堆、图形内存 | 无界缓存、后台任务保活 |
| JNI 句柄 | 自定义所有者 | 对应的原生销毁或释放函数 | 原生日志、ASan/HWASan、堆分析 | Java 异常、重复所有者 |
| JNI 全局引用 | 原生模块 | `DeleteGlobalRef` | CheckJNI、自建计数、原生调试 | 模块卸载、失败分支 |

排查 JNI 包装对象时，建议把状态机明确写成：

```text
NEW -> OPEN -> CLOSING -> CLOSED
```

每个状态转换都要规定：

- 哪个线程执行；
- 原生资源句柄是否仍有效；
- 失败能否重试；
- 并发 `close()` 如何合并；
- 所有者被取消或销毁时由谁触发关闭。

资源池还要额外限定最大容量、空闲回收和进程前后台策略。复用可以减少创建成本，但没有上限的池本身就是资源泄漏。

## 10. 一个可执行的定位案例

假设页面反复打开相机预览后，图形内存和文件描述符数量同时上涨，日志偶尔出现 `Image` 未关闭。

建议按以下顺序处理：

1. 固定“进入预览—拍摄—退出”为一轮，记录每轮文件描述符、图形内存和 `ImageReader` 相关业务计数。
2. 在所有 `onImageAvailable` 分支检查 `Image.close()`，包括解码失败、队列取消和回调抛出异常。
3. 检查页面销毁时会话、读取器和 Surface 的关闭顺序，确认后台任务不会继续持有它们。
4. 多次抓取 `FinalizerDaemon` 线程栈。如果栈停在图像包装对象的终结代码，只能说明兜底清理正在追赶，修复点仍是显式生命周期。
5. 用 Perfetto 对齐相机回调、页面退出、守护线程运行和主线程掉帧，确认是否存在锁或 Binder 竞争。
6. 修复后重复同样轮数，要求资源曲线回到稳定区间，并让 StrictMode/CloseGuard 不再报告遗漏。

这个流程把“守护线程很忙”的表象还原成可验证的资源所有权问题。

## 11. Android 8 到 Android 17 的版本边界

| 机制 | Android 8-9 | Android 10-12 | Android 13-17 |
|---|---|---|---|
| `FinalizerDaemon` / `ReferenceQueueDaemon` | 平台运行时机制 | 平台运行时机制 | 平台运行时机制 |
| `sun.misc.Cleaner` | 平台内部实现，非稳定 SDK | 平台内部实现，非稳定 SDK | 平台内部仍存在，应用不应依赖 |
| `android.util.CloseGuard` | 公共类尚不可用 | API 30 起公开 | 公开 API |
| `java.lang.ref.Cleaner` | 公共类尚不可用 | 公共类尚不可用 | API 33 起公开 |
| `android.system.SystemCleaner` | 公共类尚不可用 | 公共类尚不可用 | API 33 起公开 |

Android 17 的源码复核结果是：

- `Daemons.DAEMONS` 仍由 `HeapTaskDaemon`、`ReferenceQueueDaemon`、`FinalizerDaemon`、`FinalizerWatchdogDaemon` 组成；
- `ReferenceQueue` 仍为带实例锁的先进先出队列，并在 `enqueuePending()` 中按同队列引用批处理；
- 普通终结方法与 `SystemCleaner` 仍由 `FinalizerDaemon` 串行执行；
- 独立的 `Cleaner.create()` 仍由 `CleanerImpl` 创建自己的守护线程；
- 没有证据支持把消息队列的并发实现变化写成 `ReferenceQueue` 的 Android 17 行为。

版本演进可以说明 API 何时公开，但资源设计原则没有变化：显式关闭是主路径，终结和 Cleaner 都是执行时间不确定的延迟兜底机制。

## 12. 复核清单

提交资源包装类前，逐项确认：

- [ ] 正常、异常、取消和超时路径都会调用 `close()` 或 `release()`。
- [ ] `close()` 可重复调用，不会重复释放同一资源（double free）。
- [ ] Cleaner 清理动作没有直接或间接引用所有者。
- [ ] SystemCleaner 清理动作不执行 I/O、IPC、网络或无界等待。
- [ ] 原生资源句柄的所有者、线程和状态转换已经写清。
- [ ] 调试构建启用了适合项目的 StrictMode 检测。
- [ ] CloseGuard 告警包含有用的资源获取位置。
- [ ] 压力测试比较资源趋势，不用单个绝对值替代结论。
- [ ] Perfetto、simpleperf 和堆转储的结论没有超出各自可观测范围。
- [ ] 没有通过隐藏 `sun.misc.Cleaner` 规避公共 API 版本限制。

## 13. 小结

Android 17 的 `ReferenceQueueDaemon` 负责待处理引用入队，`FinalizerDaemon` 负责普通终结方法和 SystemCleaner，两者由独立进度计数器接受看门狗监控。`ReferenceQueue` 仍是带实例锁的先进先出队列；按同队列批处理减少了加锁次数，却没有提供实时清理保证。

定位问题时，先证明文件描述符、原生堆或图形内存随操作持续增长，再用日志、线程栈、Perfetto、simpleperf 和堆转储确认资源所有者与清理执行点。最终修复应回到显式生命周期，不能依靠增加 GC、主动调用 `System.gc()` 或等待 FinalizerDaemon 追赶。

## 参考源码与文档

- AOSP `platform/libcore`，`android-17.0.0_r1`：
  - `ojluni/src/main/java/java/lang/ref/ReferenceQueue.java`
  - `luni/src/main/java/java/lang/ref/FinalizerReference.java`
  - `libart/src/main/java/java/lang/Daemons.java`
  - `ojluni/src/main/java/java/lang/ref/Cleaner.java`
  - `ojluni/src/main/java/jdk/internal/ref/CleanerImpl.java`
  - `ojluni/src/main/java/sun/misc/Cleaner.java`
  - `luni/src/main/java/android/system/SystemCleaner.java`
- Android Developers：`java.lang.ref.Cleaner`
  - <https://developer.android.com/reference/java/lang/ref/Cleaner>
- Android Developers：`android.system.SystemCleaner`
  - <https://developer.android.com/reference/android/system/SystemCleaner>
- Android Developers：`android.util.CloseGuard`
  - <https://developer.android.com/reference/android/util/CloseGuard>
- Android Developers：`StrictMode.VmPolicy.Builder.detectLeakedClosableObjects()`
  - <https://developer.android.com/reference/android/os/StrictMode.VmPolicy.Builder>
