---
title: "线程泄漏与匿名线程监控实战"
chapter: "20.19"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [thread, leak, monitoring, stability, ThreadGroup, pthread]
related_chapters: ["20.1", "20.5", "20.12", "20.18", "20.21"]
consolidated_from:
  - "src/part5-app/ch20-stability/09-stability-case-studies.md#案例一"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadGroup.java
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/build/flags/art-flags.aconfig
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Thread.cc
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_create.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_internal.h
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_exit.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_join.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_detach.cpp
- type: aosp
  path: https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_setname_np.cpp
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/fork.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst
- type: official
  path: https://developer.android.com/reference/java/lang/Thread
- type: official
  path: https://developer.android.com/reference/java/lang/ThreadGroup
- type: official
  path: https://developer.android.com/reference/java/util/concurrent/ThreadPoolExecutor
- type: official
  path: https://developer.android.com/reference/java/util/concurrent/ScheduledThreadPoolExecutor
- type: reference
  path: https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/new-single-thread-context.html
- type: reference
  path: https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-global-scope/
- type: reference
  path: https://github.com/square/okhttp/blob/parent-5.1.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt
- type: official
  path: https://developer.android.com/reference/androidx/work/Configuration
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/manage-work
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://perfetto.dev/docs/analysis/sql-tables
- type: aosp
  path: bionic/ART
last_draft_polish_at: "2026-07-31T19:35:24+08:00"
last_draft_polish_run_id: "20260731-193524-draft-polish-a7da59d3"
status: finalized
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-07-31T20:08:09+08:00"
last_review_finalize_run_id: "20260731-200809-b4d1007d"
---

# 线程泄漏与匿名线程监控实战

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`；涉及 task 创建、`/proc` 和资源限制时，内核锚点是 `android17-6.18-2026-06_r6`。Linux task 是内核调度的执行实体，应用线程会在 `/proc/self/task` 中各有一个目录。FD 是 file descriptor，即进程访问文件、socket、pipe 等内核对象时使用的整数句柄。

本文保留几个常用工程词：pool 是复用一组执行线程的线程池，worker 是其中执行任务的线程，owner 是负责创建、取消和关闭该资源的组件或生命周期对象；Java peer 是 ART 线程关联的 `java.lang.Thread` 对象；Java platform thread 是由操作系统线程承载的普通 Java 线程；raw pthread 是 C/C++ 代码直接通过 `pthread_create()` 创建、没有 Java peer 的线程。

## 1. 先定义“泄漏”的对象

“线程数很多”只是现象。线程处于 `WAITING` 也不等于泄漏：线程池空闲 worker、Binder 线程、GC 线程和等待消息的 `HandlerThread` 都可能长期休眠。本文把“泄漏”限定为资源超过约定生命周期后仍存活或仍被强引用，排查前要确认具体对象。

joinable pthread 在退出后保留回收信息，必须由另一个线程调用 `pthread_join()`；detached pthread 则在线程退出时自行回收。协程 `Job` 表示可取消、可等待完成的任务生命周期，`CoroutineScope` 管理一组子 `Job`，dispatcher 决定这些任务在哪些线程上运行。GC root 是垃圾回收器判定为天然存活的引用起点；heap dominator 是堆分析中的支配对象，移除它即可让其支配的对象失去这条存活路径。

| 问题 | 仍能在 `/proc/self/task` 看到吗 | 主要证据 | 典型修复 |
| --- | --- | --- | --- |
| 不再需要的 Java/Native 活线程 | 能 | task 数持续增长、名称、状态、栈和创建来源 | 结束任务，修正 owner 的取消与退出协议 |
| 重复创建或未关闭的线程池 | 只看到仍存活的 worker | pool size、队列、pool 实例来源、`shutdown` 状态 | 复用 pool，由 owner 关闭 |
| 协程/任务生命周期泄漏 | 不一定增加线程 | `Job` 树、scope owner、队列和 dispatcher | 使用结构化并发，取消 owner 对应 scope |
| 已退出但未 `join`/`detach` 的 joinable pthread | 不能 | `pthread_create`、入口返回、`pthread_exit`、`pthread_join`、`pthread_detach` 事件差额 | 创建时设 detached，或保证一次 join |
| 活线程造成 Java 对象滞留 | 能 | heap dominator、`ThreadLocal`、Runnable 或线程子类字段 | 清理引用并结束不再需要的线程 |
| 线程创建失败 | 新线程未出现 | `pthread_create` 返回值、ART OOM 文案、内存映射和进程限制 | 按失败层定位，不能只看 Java heap |

OOM 是 out of memory，表示某层内存或相关资源无法满足分配请求。`ThreadLocal` 是按线程保存值的线程局部存储。上表中的几类问题可以同时发生：某个 SDK 每次初始化都创建一个 pool，每个 worker 又持有 `ThreadLocal<Activity>`，每个任务还打开 socket。此时 Linux task、Java heap 和 FD 会一起增长，但不能据此推导“每条线程固定占一个 FD”。

OpenJDK 的 `Thread.exit()` 会调用 `clearReferences()`，清空 `target`、`threadLocals`、`inheritableThreadLocals`、`blocker` 和未捕获异常处理器等引用；Android 17 的行为不同。该标签的 `Thread.getThreadGroup()` 源码明确注明 ART 在线程退出时没有调用 `Thread.exit()`。ART 的 `Thread::Destroy()` 会分发未捕获异常、从 `ThreadGroup` 移除 Java peer、清除 Native peer，并唤醒等待 `join()` 的线程，但不会代替 Java `clearReferences()` 清空上述字段。

因此要区分两类对象链：仍存活的线程会作为 GC root 保留栈和线程局部引用；已经终止的 `Thread` 不再对应 Linux task，但业务静态集合、线程注册表或其他长生命周期对象若仍强引用它，`target`、`ThreadLocalMap` 或线程子类字段仍可能继续保留对象。终止线程本身不再被引用后，这些字段会随整个 `Thread` 对象一起回收。heap dominator 分析应确认具体强引用链，不能从线程状态直接推断。

## 2. “匿名线程”指来源不明

这里的“匿名线程”指名称只有通用序号、无法直接看出创建模块的线程，并非 Java 语法中的匿名类。Java 无参命名路径会产生 `Thread-N`，`Executors.defaultThreadFactory()` 常见名称是 `pool-N-thread-M`。这些名称能说明归因信息不足，却不能单独证明线程不该存活。排查时需要回答三个问题：

1. 哪个模块创建了它？
2. 它执行哪类任务，由谁取消或关闭？
3. 同一个 owner 在一次进程生命周期中允许创建多少个 pool 和 worker？

Linux task 名称还有长度边界。`comm` 是内核保存的 task 短名称。Android 17 bionic 的 `pthread_setname_np()` 把缓冲区长度上限定为 16 字节，名称达到 16 字节时返回 `ERANGE`，表示参数超出允许范围；内核 `TASK_COMM_LEN` 同样是 16，并包含末尾的 NUL（值为 0 的字符串结束字节）。Java 中较长的 `Thread.name` 与 `/proc/self/task/<tid>/comm` 因此可能不同。用于 Native 快照的模块标识应放在前 15 个 ASCII 字节内，完整来源另存到固定容量的注册表。

推荐的命名格式是短而稳定的 `模块-用途-序号`，例如 `img-dec-3`、`net-dns-2`。不要把账号、URL、订单号或其他用户数据放进线程名。改名无法补回历史创建栈，命名需要与创建入口记录一起实施。

## 3. 四个观测面不能互相替代

TID 是 Linux 分配给 task 的线程 ID。下面四个入口分别观察内核 task、ART Java 线程和组件自己的任务模型，口径不同：

| 观测入口 | 能回答什么 | 主要盲区 |
| --- | --- | --- |
| `/proc/self/status` 的 `Threads` | 当前进程有多少 Linux task | 没有来源和状态细节 |
| `/proc/self/task/<tid>` | 当前 task 的 Linux TID、短名称与调度状态 | 看不到已退出未 join 的 pthread 映射 |
| Java `Thread` 快照 | 有 Java peer 的线程、Java 状态和调用栈 | 纯 native pthread；快照不是同一时刻 |
| pool、coroutine 和 SDK 自身指标 | owner、worker、任务与队列关系 | 只能覆盖已经接入的组件 |

### 3.1 `ThreadGroup` 只能做近似诊断

Android 17 的 `ThreadGroup.activeCount()` 文档和实现都说明返回值是估计值。线程可能在计数和枚举之间启动或结束，`enumerate(Thread[])` 在数组过小时还会静默截断；默认只遍历指定 group 的子树。这个数不等于进程 Linux task 数，也不适合作为硬限流依据。

`ThreadGroup` 的若干生命周期 API 已废弃。新代码不应把 pool 所有权寄托在 `ThreadGroup.destroy()` 一类机制上，应由 `ExecutorService`、`CoroutineScope` 或组件 owner 显式管理生命周期。

### 3.2 `Thread.getAllStackTraces()` 不适合常态计数

Android 17 的实现先取得 Java 线程记录，再逐个调用 `getStackTrace()`，会创建 `Map` 和每条线程的栈数组。各条栈采样时间不同，线程还可能在过程中结束。可先用低成本计数发现持续增长，再调用它生成诊断快照；秒级轮询开销过高，也覆盖不到没有 Java peer 的 raw pthread。

Java Crash、ANR 和跨线程栈采集机制见 [20.18 Java Crash 堆栈与锁等待诊断](18-crash-java-stack-lock-wait-analysis.md)；进程级线程与 FD 常态监控见 [20.12 FD 资源监控与治理](12-fd-resource-monitoring.md)。

### 3.3 `/proc` 快照必须容忍线程并发退出

常态只读取 `/proc/self/status` 的 `Threads` 字段。需要查看构成时，再在后台、触发式地枚举 `/proc/self/task`。下面的示例限制返回数量，并把读取过程中已经退出的线程当作正常竞态。

```kotlin
data class NativeThreadRow(
    val tid: Int,
    val kernelName: String
)

data class NativeThreadSnapshot(
    val rows: List<NativeThreadRow>,
    val truncated: Boolean
)

fun snapshotNativeThreads(
    maxRows: Int = 256
): Result<NativeThreadSnapshot> = runCatching {
    require(maxRows in 1..1024)
    val taskDirs = File("/proc/self/task").listFiles()
        ?: throw IOException("cannot list /proc/self/task")

    val rows = taskDirs
        .asSequence()
        .mapNotNull { taskDir ->
            val tid = taskDir.name.toIntOrNull() ?: return@mapNotNull null
            val name = runCatching {
                File(taskDir, "comm").readText().trimEnd()
            }.getOrNull() ?: return@mapNotNull null
            NativeThreadRow(tid, name)
        }
        .take(maxRows)
        .toList()
    NativeThreadSnapshot(
        rows = rows,
        truncated = taskDirs.size > maxRows
    )
}
```

`listFiles()` 失败通过 `Result.failure` 表示，调用方应把它记录为“缺测”，不能上报成 0 条线程。遍历期间某个 TID 目录消失，表示该线程已经结束，属于正常竞态。`truncated` 为 `true` 时只能分析已采到的名称分布，不能把 `rows.size` 当成当前 task 总数。这个函数会产生文件 I/O 和对象分配，不要放在主线程、crash handler（崩溃回调）或高频定时器中。

Java `Thread.threadId()`（API 36 起）和旧的 `getId()` 都是 Java 生命周期 ID，不是 Linux TID。只有在线程内部调用 `Process.myTid()`，或在可靠的 Native 创建事件中取得 TID，才能与 Perfetto、tombstone 和 `/proc` 对齐。TID 在线程退出后会复用，跨时间关联还必须带进程启动标识和采样时间。

## 4. 从创建入口保存来源

能控制的 Java worker 应统一经过 `ThreadFactory`。下面的示例在线程开始执行后登记 Java ID 和 Linux TID，并在任务入口退出时删除记录。`ThreadRegistry` 是示例中的线程注册表，并非 Android API；实现时应限制容量，采用无锁或低竞争数据结构，并保证注册失败不影响业务线程。

```kotlin
class TrackedThreadFactory(
    private val sourceId: String,
    private val registry: ThreadRegistry,
    private val delegate: ThreadFactory = Executors.defaultThreadFactory()
) : ThreadFactory {
    private val sequence = AtomicInteger()

    init {
        require(sourceId.matches(Regex("[a-z0-9-]{1,7}")))
    }

    override fun newThread(task: Runnable): Thread {
        val ordinal = Integer.toUnsignedString(sequence.incrementAndGet(), 36)
            .padStart(7, '0')
        val name = "$sourceId-$ordinal"
        val wrapped = Runnable {
            val current = Thread.currentThread()
            val javaId = if (Build.VERSION.SDK_INT >= 36) {
                current.threadId()
            } else {
                @Suppress("DEPRECATION")
                current.id
            }
            val tid = Process.myTid()

            registry.tryOnStart(
                javaId = javaId,
                linuxTid = tid,
                sourceId = sourceId,
                javaName = current.name
            )
            try {
                task.run()
            } finally {
                registry.tryOnStop(javaId = javaId, linuxTid = tid)
            }
        }
        return delegate.newThread(wrapped).apply {
            this.name = name
        }
    }
}
```

这里用不超过 7 个 ASCII 字节的 `sourceId` 和固定 7 位 base-36（36 进制）序号，把 Java 名称控制在内核 `comm` 的 15 字节载荷内。注册表记录的是 worker 生命周期，不包含每个提交任务的生命周期。若一个 pool 长期复用 worker，还要单独包装任务，采集队列等待、执行时长、取消和异常。创建栈成本较高，可以在新 pool 出现、数量增长或诊断开关开启时采样；不应给每次任务提交都保存完整堆栈。

第三方 SDK 无法接入 factory 时，可按风险从低到高采用：

- 记录 SDK 版本、初始化次数和进程角色，与线程名前缀和数量变化对齐；
- 对可修改的依赖入口传入自有 executor（任务执行器）；
- 在内部或诊断构建中做有限范围的字节码插桩，即在编译产物中自动加入创建事件记录；
- 对必须诊断的 Native SDK，在受控版本中跟踪 pthread 生命周期。

不要用 `Thread.stop()`、`pthread_cancel()` 或反射强制终止未知线程。线程可能持有 Java monitor、malloc 锁、数据库事务或库内状态，强停会把“线程多”变成数据损坏或死锁。

## 5. Native pthread 的特殊盲区

### 5.1 Java `Thread` 与 raw pthread 的回收协议不同

Android 17 的 ART `Thread::CreateNativeThread()` 会把 pthread attribute 设成 `PTHREAD_CREATE_DETACHED`，再调用 `pthread_create()`。普通 Java `Thread` 因而由 detached pthread 承载，退出时不需要业务调用 `pthread_join()`。

raw `pthread_create()` 在未传 detached 属性时使用 joinable 语义。Android 17 bionic 的状态迁移如下：

| 事件 | bionic 状态 | 栈映射何时释放 |
| --- | --- | --- |
| 创建默认 pthread | `THREAD_NOT_JOINED` | 尚未释放 |
| 入口函数返回或调用 `pthread_exit()` | `THREAD_EXITED_NOT_JOINED` | 继续保留，等待 join |
| 调用 `pthread_join()` | `THREAD_JOINED` | join 路径移除并释放 |
| 创建时 detached，或存活时 `pthread_detach()` | `THREAD_DETACHED` | 线程退出时自行释放 |
| 已退出后再 `pthread_detach()` | 清理路径转到 join | 当次调用释放 |

`THREAD_EXITED_NOT_JOINED` 已经没有 Linux task，因此 `/proc/self/task`、`Threads`、Java 栈快照和 Perfetto 的存活线程表都看不到它。该 pthread 的主映射仍等待 `join` 或 `detach` 回收。若 Native RSS 或虚拟地址空间持续增长，但活线程数会回落，应检查这一类资源。

### 5.2 监控必须覆盖成对事件

对自有 C/C++ 代码，优先提供 RAII（对象析构时自动执行清理）或统一包装层，明确以下约束：

- 无需返回结果、创建方不再等待的 worker 在创建前设置 detached；
- 需要结果的 joinable worker 只能由一个 owner join；
- 创建失败时不能把未初始化的 `pthread_t` 写入注册表；
- 入口函数正常返回、异常适配层返回和显式 `pthread_exit()` 都要结算状态；
- registry 以创建序号作为事件 ID，不能长期只用可能复用的 `pthread_t` 或 TID；
- 进程退出前输出成功创建总数、创建失败数，以及 `running`、`exited-unjoined`、`joined-reclaimed`、`detached-reclaimed` 等互斥生命周期状态；不要把可重叠计数直接相减。

PLT（Procedure Linkage Table，过程链接表）hook 通过改写动态链接跳转表拦截函数，inline hook 则改写函数入口指令。它们可以观察三方库，但会受到 ABI（二进制接口）、加载顺序、静态链接、设备厂商改动和重入影响；重入指 hook 内部再次触发被 hook 函数。hook 中采完整 Native 栈、扩容容器或写文件还会引入新故障。此类方案应限定构建类型、进程、启用时长和事件上限，并用 `/proc/self/task` 核对；不能把它写成所有版本默认开启的稳定接口。

## 6. 每条线程的资源成本不是固定常数

“每条线程默认占用 1 MiB 栈空间”过于简化，也容易把虚拟地址预留误算成 RSS。虚拟地址空间是进程可寻址的范围；RSS（resident set size，常驻内存集）只统计当前驻留在物理内存中的页面，两者口径不同。

Android 17 bionic 对 raw pthread 的默认栈常量是 1 MiB 减去独立信号栈的可用部分。该 pthread 的主映射还包含 guard page（设置为不可访问、用于捕获越界的保护页）、static TLS（线程局部存储）、专用 libgen buffers 和另一侧保护页，并使用 `MAP_NORESERVE`，即创建映射时不要求内核预留等量交换空间。架构和内存安全能力还可能增加 alternate signal stack（处理信号时使用的备用栈）、shadow call stack（单独保存返回地址以检测破坏的影子调用栈）等线程私有区域。

Java `Thread` 还会经过 ART 的 `FixStackSize()`：传入 0 时先取运行时 `-Xss` 默认值，随后为 Dalvik/Android 兼容增加 1 MiB，再加入栈溢出保护与保留区并按页对齐。`Thread` 构造器的 `stackSize` 参数只是依赖虚拟机实现的提示；没有覆盖深递归、JNI 和低内存压力测试时，不应随意缩小。

监控至少区分三种量：

- 虚拟地址空间中的线程映射；
- 已提交并驻留的物理页面；
- task、TLS、信号栈和运行时附属结构。

估算不能只做“线程数 × 1 MiB”。应在目标 ABI、页大小、设备内存和相同业务负载上比较 `/proc/self/maps`（进程内存映射列表）、`smaps_rollup`（各映射内存统计的进程级汇总）、RSS 与 task 数的共同变化。

线程也不会天然持有一个 FD。`/proc/self/task/<tid>` 是 procfs（内核导出的进程信息伪文件系统）视图，不表示进程为每条线程常驻打开了文件描述符。线程和 FD 一起增长，通常说明同一模块同时创建 worker 与 socket、pipe、eventfd 或文件；仍需按 owner 和时间线证明关联。FD 的计数、限额与复用规则见 [FD 耗尽监控与故障排查](12-fd-resource-monitoring.md)。

## 7. 线程创建失败没有单一“上限”

在 `android17-6.18-2026-06_r6` 中，内核 `copy_process()` 会检查按 real user（内核记账使用的真实用户 ID）统计的 `RLIMIT_NPROC` 上限和系统 `max_threads`。超过数量限制时返回 `-EAGAIN`，表示当前资源条件不允许再次创建；task 结构、内核栈等分配失败还可能返回 `-ENOMEM`，表示内存不足。设备若启用 cgroup pids controller（按控制组限制 task 数的内核机制），还会受到额外策略约束。

在到达内核 `clone` 前，bionic 还需要建立线程映射并初始化 TLS；ART 创建 Java 线程前还会分配内部 `Thread`、JNI 环境和 Java peer 关联。因此，相同的“无法创建线程”可能来自：

- 用户/系统/cgroup 的 task 数限制；
- 虚拟地址空间不足或碎片；
- native 内存、页表、内核内存压力；
- 线程栈或 TLS 映射失败；
- ART 自身分配失败；
- 某个库请求了异常大的 stack size。

`/proc/self/limits` 的 Max processes 不是“本进程还可创建多少条线程”的精确余额。`RLIMIT_NPROC` 按 real user 计数，Android 的应用 UID、共享 UID 和进程角色会影响结果；其他限制也可能更早触发。诊断时要保存 bionic/ART 原始错误和 errno（C 库错误编号），以及进程角色、ABI、task 数、`VmSize`（虚拟地址空间总量）、RSS 和近期增长，不要只记录 Java heap 剩余空间。

Android 17 bionic 在线程映射中加入页对齐的专用 libgen buffers，并加强备用信号栈初始化失败的处理。这些是内存布局和错误处理变化，不能推导出“应用最多 500 条线程”之类的平台规则。

## 8. 线程池：看容量、任务和 owner

### 8.1 `activeCount < poolSize` 很正常

`ThreadPoolExecutor.getActiveCount()` 返回正在执行任务的 worker 估计数，`getPoolSize()` 返回当前 worker 数。空闲 worker 会等待队列，因此 `activeCount` 小于 `poolSize` 不能证明泄漏。建议同时记录：

- `corePoolSize`、`maximumPoolSize`、`poolSize`、`largestPoolSize`；
- `activeCount`、`completedTaskCount`、`taskCount`；
- 队列长度、最老任务等待时间与拒绝次数；
- pool 创建来源、实例数、`isShutdown`、`isTerminated`；
- 前后台状态和对应功能是否仍然存活。

固定线程池常用无界队列，worker 数稳定时仍可能发生任务或内存堆积。cached pool 会按需增加 worker，阻塞任务突发时线程数可能快速上升；空闲 worker 默认会在 keep-alive（空闲存活时间）到期后回收。两类线程池要用不同证据判断。

### 8.2 `ScheduledThreadPoolExecutor` 要看取消策略

周期任务会持续执行到取消。一次性延迟任务被取消后，默认仍可能留在 delay queue（按执行时间排序的延迟队列）中，直到原延迟到期；大量长延迟任务会造成对象滞留。业务允许时可启用 `setRemoveOnCancelPolicy(true)`，并由 owner 保存代表计划任务句柄的 `ScheduledFuture`，在生命周期结束时取消任务，再关闭专用 executor。

`ScheduledThreadPoolExecutor` 基于固定数量的 core worker（核心 worker）和无界 delay queue，调大 `maximumPoolSize` 通常没有作用。这里需要分开看“worker 没退出”和“取消任务仍在队列”，它们的修复点不同。

### 8.3 重复创建 pool 比某一条匿名线程更值得查

线程名前缀里的 pool 序号不断增长、旧 pool worker 长期存活，通常提示组件重复初始化或缺少关闭。注册表应记录 pool 实例来源和 owner 生命周期，不能只记录线程。进程级单例也不要求所有场景共用一个全进程 executor：隔离明确、能独立关闭的模块可以拥有专用 pool，但必须有并发预算和 owner。

## 9. 协程：任务泄漏与线程泄漏要分开

`Dispatchers.Default` 和 `Dispatchers.IO` 会复用调度器 worker；一万个挂起协程不等于一万条 Linux task。挂起协程会保存继续执行所需的状态，等待条件满足后再由 dispatcher 调度。`GlobalScope` 没有可由业务 owner 统一等待或取消的父 `Job`，容易让任务及其捕获对象超过页面或会话生命周期，但它不会自动为每个协程新建线程。

更接近线程资源泄漏的协程用法包括：

- 重复创建 `newSingleThreadContext()` 后没有 `close()`；
- 把新建 `ExecutorService` 转成 dispatcher 后没有关闭 dispatcher 或 executor；
- 每次进入页面都创建独立 dispatcher，并把它保存在长生命周期对象里；
- 阻塞任务占满共享 dispatcher，又通过错误补偿持续增加其他 pool。

若不要求专用物理线程，单路串行执行可优先考虑现有 dispatcher 的 `limitedParallelism(1)`。结构化并发要求子任务的生命周期嵌套在父 scope 内；页面、ViewModel、服务或会话应使用有 owner 的 scope。协程取消采用协作机制，取消 scope 后还要确认阻塞调用能否响应线程中断或自身的取消协议。

排查时同时画两条曲线：活跃 `Job`/队列数与 Linux task 数。只有 Job 增长，重点查 scope 和任务；两者都增长，再查自定义 dispatcher、executor 或 native 库。

## 10. 常见组件的判断边界

### 10.1 OkHttp

OkHttp 官方建议复用一个 `OkHttpClient`，通过已有 client 的 `newBuilder()` 派生出的客户端会共享连接池、线程池和基础配置。连接池保存可复用的网络连接，`Dispatcher` 管理同步与异步请求的排队和执行。多个独立构造的 client 可能各自持有这些资源，但仍需检查实际共享关系，不能只数 client 对象。

应记录 client 构造来源、`Dispatcher.runningCallsCount()`、`queuedCallsCount()`、请求取消和回调是否返回。不要为了降低快照中的线程数就关闭全局共享 client：关闭 dispatcher executor 后，后续请求会被拒绝；连接池中的空闲连接会按自身策略释放。

### 10.2 WorkManager

WorkManager 的重复 `WorkRequest` 更常见的是任务重复，不一定产生一条新 worker。unique work 用业务唯一名称约束同类工作，`WorkInfo` 记录任务状态、输出和停止原因。排查时还要检查约束与重试策略。自定义 `Configuration` 时，执行器应有容量边界，并区分运行 Worker 的 executor 与 WorkManager 内部协调任务使用的 task executor。

多进程应用必须按进程记录 PID（进程 ID）、进程名和角色。每个进程都有自己的 ART、Binder 和库初始化开销，把主进程与远程进程 task 数相加后套用单进程阈值会误报。若某个依赖在每个进程都自动初始化，应通过 AndroidX Startup、manifest 配置或进程判断缩小初始化范围。

## 11. 告警要看基线、增量和持续时间

`200 / 400 / 500` 可以是某个产品在特定设备分组上的经验值，不能写成 Android 平台通用阈值。主进程、WebView 进程、音视频进程和 isolated process（以隔离 UID 运行、权限受限的进程）基线不同；ABI、设备内存、页大小、目标版本和功能开关也会改变成本。

一条可解释的线程风险规则至少包含：

| 信号 | 含义 |
| --- | --- |
| 同进程角色、版本和设备分组的 P95/P99 | 用第 95/99 百分位判断当前值是否偏离同类样本 |
| 相对冷启动稳定点的增量 | 排除启动后原本就存在的平台与组件基线 |
| 一段时间内的增长斜率 | 用单位时间增量识别快速创建 |
| 页面退出、任务取消或进入后台后的回落 | 验证生命周期是否收敛 |
| 名称/sourceId 的增量贡献 | 指向 owner |
| pool 队列、RSS、VmSize、FD 与失败日志 | 判断资源后果 |

建议使用分层触发：

1. 常态只采 `Threads`、pool 摘要和历史高水位（进程生命周期内观测到的最大值）；
2. 增长持续多个窗口后，读取 `/proc/self/task` 名称分布；
3. 某来源异常时，短时开启创建事件或采样栈；
4. 接近故障或出现创建失败时，写入预留的有界摘要；
5. 下一次启动关联 `ApplicationExitInfo` 历史退出记录、ANR trace 或 tombstone。

崩溃 handler 中不要调用 `Thread.getAllStackTraces()`、遍历几百个 `/proc` 文件或启动上传线程。资源紧张阶段这些动作可能再次分配失败，甚至覆盖原始现场。

## 12. 用 Perfetto 还原生命周期

Perfetto 是 Android 的系统 trace 采集与分析工具。实验室或可控设备上，它能把“某时段线程数增加”细化成创建、改名、调度和退出事件。下面的配置片段通过 ftrace（Linux 内核事件跟踪机制）采集 task 生命周期与调度切换，同时轮询进程统计；实际 buffer（环形缓冲区）、时长与权限应按测试场景调整。

```textproto
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_process_exit"
      ftrace_events: "sched/sched_process_free"
      ftrace_events: "task/task_newtask"
      ftrace_events: "task/task_rename"
    }
  }
}
data_sources: {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
      proc_stats_poll_ms: 1000
    }
  }
}
```

`task_newtask` 用于补充线程开始时间，`sched_process_exit` 和 `sched_process_free` 分别记录 task 退出与最终释放，`task_rename` 能看到内核短名称变化；`sched_switch` 记录 CPU 在 task 间切换。Perfetto 的 `utid` 是一次 trace 内分配的唯一线程标识，分析时不要只用可能复用的操作系统 TID。

Perfetto 不能自动给出 Java 创建调用点，也看不到已经退出但未 join 的 pthread 用户空间映射。前一类来源要与 `ThreadFactory` 或受控采样关联，后一类资源要依赖 pthread 成对事件或内存映射证据。

## 13. 四类案例怎样判

### 13.1 `pthread_create` OOM 与页面线程泄漏

看到 `OutOfMemoryError: pthread_create (...) failed` 只能确认 ART 在线程创建路径抛出了 `OutOfMemoryError`，不能因 Java heap 尚有余量就排除资源耗尽。失败可能发生在 ART `Thread`/JNI 环境分配、bionic stack/TLS 映射或内核 `clone`；还要保留原始错误、线程数、`VmSize`/RSS、ABI、页大小、进程角色和近期增长。

一个可重复的调查过程是：

1. 按进程角色和设备内存/性能分组绘制 Linux task 数、Java 线程、pool 实例、队列、VmSize 与 RSS 时间线；
2. 在增长刚越过基线时采集 `/proc/self/task` 名称分布和有限 Java 栈，不等到创建已经失败；
3. 用统一 `ThreadFactory`、executor registry 或诊断构建中的 pthread 包装定位创建 owner；
4. 页面/组件退出后等待契约规定的宽限期，确认线程、pool 和任务是否回落；
5. 修复 owner 的取消、shutdown、join/detach 和重复初始化；提高阈值或缩小未知线程栈不能修复生命周期错误。

复现样例应运行在独立测试进程：重复进入页面，每次错误创建一组 `HandlerThread` 或 executor 且不退出，直到 task 数和虚拟地址映射呈阶梯增长。修复版保存 owner，在 `onDestroy` 或 `close` 中停止任务，调用 `quitSafely()` 或 `shutdown()`，并等待明确终止。验收应比较相同循环次数后的峰值、回落时间、任务完成率和内存；单凭“不再抛 OOM”不足以证明资源已经回收。

告警应同时使用基线、增长斜率和回落情况。固定的 400/500 不是 Android 平台上限；阈值要按主进程、WebView 或媒体进程、ABI、设备内存和实测栈成本校准。fatal 路径指致命故障后的最小采集回调，它只写入预生成且有容量上限的摘要，不能在资源即将耗尽时创建上传线程或抓取全部线程栈。

### 13.2 广告 SDK 出现大量短名称线程

不能从 `Thread-123` 直接推断“广告 SDK 泄漏并耗尽 FD”。可靠证据链是：

1. SDK 初始化或广告页面进入后，特定短名称或 `sourceId` 分布持续增加；
2. 页面退出和 SDK 关闭后，多个稳定窗口仍不回落；
3. Java/Native 栈或受控创建事件指向同一依赖版本；
4. pool 实例、任务队列或 pthread 状态能解释存活原因；
5. FD 若同步增长，还能按 socket/pipe/file 类型归到相同 owner。

修复可能是升级 SDK、禁止重复初始化、传入共享 executor、补充关闭协议或隔离到可控进程。强停未知线程不在可接受方案内。

### 13.3 `GlobalScope` 数量增长

若协程任务增长而 Linux task 稳定，这是 scope 或任务生命周期问题。应定位未完成的 Job、捕获对象和不可取消的调用，不要通过扩大 `Dispatchers.IO` 并发来掩盖。只有自建 dispatcher 或 pool 数量同步增长时，才同时归为线程资源问题。

### 13.4 WorkManager 多进程 task 数上升

先按 PID 分组，确认哪些进程加载了 WorkManager 和业务依赖，再检查是否重复 enqueue（入队）、是否使用 unique work、是否在远程进程重复初始化自定义 executor。多进程的固定基线开销与同一进程内持续增长不是一类信号。

## 14. Android 17 的虚拟线程边界

API 36 已公开 `Thread.isVirtual()` 查询方法，但这不代表普通应用已经稳定获得虚拟线程创建能力。`android-17.0.0_r1` 的 `isVirtual()` 实现会检查 `VirtualThreadContext` 或 `BaseVirtualThread`，与同一文件中“Android 总返回 false”的旧注释不一致，判断应以该标签实现和设备行为为准。Android 17 还包含 `Thread.ofVirtual()`、`startVirtualThread()`、`Executors.newVirtualThreadPerTaskExecutor()` 及对应 ART 实现；这些创建入口仍带 `FlaggedApi`（由平台功能开关控制的 API 标记），底层实现还受 `is_exported: false` 的 `virtual_thread_impl_v1` ART flag 控制。

因此，面向普通 Android 17 应用的设计不能假设 Project Loom（OpenJDK 的虚拟线程项目）已成为默认能力。生产监控仍要把 Java platform thread 和 Native pthread 映射到 Linux task；Kotlin coroutine 也不等于 Java virtual thread。若未来版本全面公开并启用虚拟线程，监控模型需要新增“虚拟线程数量”和“carrier platform thread 数量”两个维度。carrier thread 是某一时刻承载并执行虚拟线程的操作系统线程，届时不能沿用“一条 Java 线程对应一个 Linux task”的假设。

## 15. 验证方案

建议在独立测试进程中覆盖以下场景：

| 注入场景 | 预期结果 |
| --- | --- |
| 重复创建固定 pool 且不 shutdown | pool 实例、worker 和 Linux task 同步增长 |
| cached pool 提交一批短任务 | task 数短时上升，keep-alive 后回落 |
| 取消长延迟 scheduled task | 开启 remove-on-cancel 前后队列保留差异可见 |
| 创建 `newSingleThreadContext` 后不关闭 | dispatcher owner 与 task 数持续增加 |
| raw joinable pthread 立即返回且不 join | 活 task 回落，但 pthread 事件差额和映射压力增长 |
| raw detached pthread 立即返回 | task 和映射都能回收 |
| 仍存活线程持有 `ThreadLocal<Activity>` | heap dominator 指向活线程；线程终止并释放外部 `Thread` 强引用后，整条对象链可回收 |
| 已终止 `Thread` 仍被静态注册表保存 | `/proc` 已无 task，但 dominator 仍经该 `Thread` 指向 `target`、`ThreadLocalMap` 或子类字段 |
| 线程与 socket 同时泄漏 | 两种资源都能归到同一 owner，而非按数量猜测 |
| `/proc` 遍历时线程退出 | 快照容忍 TID 消失并标记缺测/跳过 |
| 接近资源压力时触发摘要 | 不抓全栈，不创建新线程，摘要仍有界 |

测试结束后必须退出测试进程，或由明确 owner 释放资源。不要在承载用户数据的线上进程中制造几百条线程、降低资源限制或留下 joinable pthread 来验证告警。

## 16. 检查清单

- [ ] 是否区分 Linux task、Java platform thread、pool worker、协程 Job 与 raw pthread？
- [ ] 是否用生命周期和 owner 证明泄漏，而非看到 `WAITING` 或匿名名称就下结论？
- [ ] 常态监控是否只采低成本计数，详细栈是否由增长触发？
- [ ] 是否把 Java ID、Linux TID、pthread 事件 ID 分开保存并处理复用？
- [ ] 是否区分仍存活的线程与被业务强引用的已终止 `Thread`，没有假定 ART 会调用 `Thread.exit()` 清字段？
- [ ] `ThreadGroup.activeCount()` 是否只作为估计，不用于硬限流？
- [ ] `/proc/self/task` 是否容忍并发退出，并与 Java 快照解释差额？
- [ ] 自有 pool 是否有稳定 sourceId、容量、队列、拒绝和关闭协议？
- [ ] 计划任务是否保存 `ScheduledFuture`、正确取消并处理队列保留？
- [ ] coroutine scope 和 dispatcher 是否都有明确 owner？
- [ ] native joinable pthread 是否保证一次 join，或创建时设为 detached？
- [ ] 是否避免把 Java `Thread` 的 ART 栈映射写成固定 1 MiB？
- [ ] 是否避免把线程数与 FD 数写成一一对应？
- [ ] 告警是否按进程角色、版本、设备分组、增量和持续时间校准？
- [ ] 创建失败是否同时保留 errno、task 数、`VmSize`/RSS 与进程限制？
- [ ] 线程名、调用栈和来源字段是否限长并去除用户信息？
- [ ] fatal 路径是否只消费预生成的有界摘要？

## 17. 源码与官方资料

- [AOSP `Thread.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)：默认命名、`getAllStackTraces()`、Android 未调用 `exit()` 的兼容注释和虚拟线程 API 边界。
- [AOSP libcore `current.txt`（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt)：虚拟线程相关入口的 `FlaggedApi` 标记。
- [AOSP `ThreadGroup.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadGroup.java)：`activeCount()` 与 `enumerate()` 的估计和竞态语义。
- [AOSP ART `thread.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)：`Thread::Destroy()`、`FixStackSize()`、detached pthread 属性和 Java 线程创建失败路径。
- [AOSP ART `art-flags.aconfig`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/build/flags/art-flags.aconfig)：`virtual_thread_impl_v1` 实现 flag 的声明与导出边界。
- [AOSP ART `java_lang_Thread.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Thread.cc)：Java `Thread` 到 ART 创建入口。
- [AOSP bionic `pthread_create.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_create.cpp)：线程映射、TLS、guard、`MAP_NORESERVE`、clone 和默认 join 状态。
- [AOSP bionic `pthread_internal.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_internal.h)：默认栈、备用信号栈和 guard 大小常量。
- [AOSP bionic `pthread_exit.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_exit.cpp)：detached 与 exited-not-joined 的映射回收差异。
- [AOSP bionic `pthread_join.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_join.cpp)：join 状态迁移和释放路径。
- [AOSP bionic `pthread_detach.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_detach.cpp)：线程存活与已经退出两种情况下的 detach 路径。
- [AOSP bionic `pthread_setname_np.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_setname_np.cpp)：16 字节 kernel comm 边界与 `prctl`/proc 写入路径。
- [Android Common Kernel `fork.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/fork.c)：`RLIMIT_NPROC`、`max_threads`、`EAGAIN` 与 task 分配失败路径。
- [Android Common Kernel `proc.rst`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)：`Threads`、task 目录和 proc 字段语义。
- [Android Developers：`Thread`](https://developer.android.com/reference/java/lang/Thread)：`threadId()`、`isVirtual()` 和平台 API 契约。
- [Android Developers：`ThreadGroup`](https://developer.android.com/reference/java/lang/ThreadGroup)：估计计数、枚举和废弃 API。
- [Android Developers：`ThreadPoolExecutor`](https://developer.android.com/reference/java/util/concurrent/ThreadPoolExecutor)：pool、active、queue 与生命周期指标。
- [Android Developers：`ScheduledThreadPoolExecutor`](https://developer.android.com/reference/java/util/concurrent/ScheduledThreadPoolExecutor)：取消任务保留和 remove-on-cancel 策略。
- [Kotlin Coroutines：`newSingleThreadContext`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/new-single-thread-context.html)：专用 native 线程资源与关闭要求。
- [Kotlin Coroutines：`GlobalScope`](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-global-scope/)：无 owner Job 的生命周期边界。
- [OkHttp 5.1.0：`OkHttpClient.kt`](https://github.com/square/okhttp/blob/parent-5.1.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)：客户端复用、共享资源和关闭行为。
- [Android Developers：WorkManager `Configuration`](https://developer.android.com/reference/androidx/work/Configuration)：worker executor 与 task executor 配置。
- [Android Developers：管理 WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/manage-work)：unique work、取消与工作状态。
- [Perfetto：CPU scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)：ftrace 调度和 task 生命周期事件。
- [Perfetto：SQL tables](https://perfetto.dev/docs/analysis/sql-tables)：thread 的 `start_ts`、`end_ts`、TID 与 `utid` 语义。

线程治理的目标是让每个 worker 都能回答“谁创建、为谁工作、何时退出”。进程计数负责发现趋势，组件指标负责说明任务压力，创建事件负责确认来源，heap/FD/内存映射负责判断后果。把这些证据按时间和 owner 对齐，才能区分正常峰值、生命周期错误与临近资源耗尽。
