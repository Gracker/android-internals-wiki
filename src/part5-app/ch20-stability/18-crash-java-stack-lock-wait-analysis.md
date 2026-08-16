---
title: "Crash 状态下 Java 线程堆栈获取与锁等待分析"
chapter: "20.18"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [crash, java-stack, ThreadList, StackVisitor, MonitorInfo, lock-wait, ART]
related_chapters: ["20.2", "20.3", "20.15", "20.16", "26.23"]
sources:
  - type: aosp
    path: "art/runtime/thread_list.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/stack.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/monitor.cc (android-17.0.0_r1)"
  - type: aosp
    path: "libcore/ojluni/src/main/java/java/lang/Thread.java (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/native/dalvik_system_VMStack.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/signal_catcher.cc (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java (android-17.0.0_r1)"
  - type: aosp
    path: "system/core/debuggerd (android-8.0.0_r1)"
  - type: aosp
    path: "external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/monitor_contention.sql (android-17.0.0_r1)"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - pthread_create 回溯：原来 Native 也有 try catch！.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 分析与监控原理.md"
---

# Crash 状态下 Java 线程堆栈获取与锁等待分析

Crash 时获取全部 Java 栈，需要先区分四类现场：Java 未捕获异常、Native 致命信号、系统 ANR，以及进程退出后的证据读取。它们的运行时状态、权限和安全边界各不相同。若统一塞进 signal handler（信号处理函数），一次可诊断的故障可能演变成死锁、二次崩溃或残缺报告。

本文的平台与 ART（Android Runtime，执行 Java/Kotlin 字节码并管理对象、线程和垃圾回收的运行时）源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。涉及 futex 与线程调度时，内核锚点为 `android17-6.18-2026-06_r6`。futex 是 Linux 的快速用户态互斥机制：无竞争时主要在用户态完成，发生竞争后才进入内核等待。Java monitor（`synchronized` 和 `Object.wait()` 使用的对象锁结构）的 owner、held lock 和栈帧仍由 ART 解释，无法从一条内核睡眠状态直接反推。

## 1. 先按现场选择取证路径

OOM 指 `OutOfMemoryError`，即 Java 堆或相关内存资源无法满足分配请求。ANR 是 Application Not Responding，表示系统判定应用在规定时间内没有响应。`SIGQUIT` 是 Android/ART 用来请求诊断转储的信号，SignalCatcher 是 ART 中专门等待并处理这类信号的线程。Perfetto trace 是按时间记录系统与应用事件的诊断轨迹。

breadcrumb 是故障前预先保存的少量关键事件记录；`siginfo_t` 保存信号编号、故障地址等信号信息，`ucontext_t` 保存信号发生时的寄存器上下文；tombstone 是 Android debuggerd 生成的 Native 崩溃诊断文件；minidump 是由应用或外部采集器生成的紧凑二进制转储。JNI 是 Java 与 C/C++ 代码互相调用的接口。`ApplicationExitInfo` 则是 API 30 引入的历史进程退出记录。

fatal handler 指致命故障发生后、进程终止前执行的回调。Java 与 Native 的回调环境不同，不能共享一套安全假设。`sigaction()` 是注册 Unix 信号处理动作的系统接口；应用自行接管 `SIGQUIT` 会与 ART 的诊断机制冲突，也不属于 Android SDK 承诺兼容的用法。

| 现场 | 进程状态 | 应用可优先保存的证据 | 不应依赖的动作 |
| --- | --- | --- | --- |
| Java 未捕获异常 | ART 通常还能运行，但可能正处于 OOM、栈溢出或锁异常 | 已抛出的 `Throwable`、崩溃线程、预存 breadcrumb；资源允许时补少量目标线程 | 无限制遍历全部线程、同步网络、等待业务锁 |
| 系统 ANR / 调试 SIGQUIT | 进程仍存在，由 ART 的 SignalCatcher 执行诊断流程 | 系统 ANR trace、重复的主线程预采样、Perfetto trace | 把自定义 `sigaction(SIGQUIT)` 当成稳定公开接口 |
| Native 致命信号 | Java 堆、线程栈或运行时锁都可能不一致 | `siginfo_t`、`ucontext_t`、debuggerd tombstone 或外部 minidump | JNI、Java API、私有 ART 遍历、普通分配和锁 |
| 进程已经退出 | 进程内 Java 状态已经不存在 | `ApplicationExitInfo`、tombstone/ANR trace、进程退出前写好的记录 | 重启后再查询旧进程的 Java 对象或 monitor |

选路依据是现场边界，而非某个函数在平时能否调用。正常运行期可用的 API 未必适合未捕获异常回调；Java fatal handler 中偶尔成功的代码，也不能移入 Native signal handler。

## 2. `Thread.getAllStackTraces()` 的 Android 17 语义

### 2.1 它逐线程取栈，不做全局 `SuspendAll`

Android 17 的 [`Thread.getAllStackTraces()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java) 先取得活动线程数组，再循环调用每个线程的 `getStackTrace()`。下面的等价伪代码只保留影响快照一致性的部分：

```java
AllThreadsRecord record = getAllThreadsInternal();
Map<Thread, StackTraceElement[]> result = new HashMap<>();
for (int i = 0; i < record.count; i++) {
    Thread thread = record.threads[i];
    result.put(thread, thread.getStackTrace());
}
```

这段流程会分配线程数组、`HashMap`、各线程的栈数组和 `StackTraceElement` 对象。`getAllThreadsInternal()` 先用 `ThreadGroup.activeCount()` 估算数组大小，再调用 `enumerate()`；若线程正在并发创建，枚举结果不承诺覆盖每条活动线程。线程列表与各条栈的采样时刻也不相同，遍历期间线程仍可运行、创建或退出。公开 API 文档将每条栈定义为快照，并注明它们可能在不同时间取得。

下面两种理解均不符合 Android 17 的实现：

- “`getAllStackTraces()` 会先触发一次全局 GC 暂停，再原子地抓取全进程。”
- “这张 Map 表示同一个时刻的完整线程与锁状态。”

它适合正常运行期诊断、受控 watchdog（看门狗，用于定时检查目标线程是否响应的监控组件）或测试工具，无法单独证明一组严格同时发生的死锁关系。

### 2.2 当前线程与其他线程走不同路径

`Thread.getStackTrace()` 会进入 Android 私有的 `VMStack.getThreadStackTrace()`。Android 17 的 [`dalvik_system_VMStack.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/dalvik_system_VMStack.cc) 在 `GetThreadStack()` 中区分两种情况：

1. 目标就是调用线程：直接调用 `Thread::CreateInternalStackTrace()`。
2. 目标是另一条 Java 线程：调用线程先离开 Runnable 状态，再用 `ThreadList::SuspendThreadByPeer()` 挂起目标线程；栈对象生成后恢复目标线程。

Runnable 是 ART 中可执行托管代码并持有 mutator lock 共享访问权的线程状态。mutator lock 是 ART 用来协调 Java 堆访问、垃圾回收与线程挂起的运行时锁。调用线程先离开这个状态，才能等待并检查另一条线程。跨线程取栈会逐个挂起目标线程，不会一次挂起全部线程。目标线程若迟迟到不了 suspend point（允许 ART 安全暂停线程的检查点），取栈延迟会增加；目标已经退出时，结果可以为空。

`CreateInternalStackTrace()` 通过 `StackVisitor` 遍历 managed stack（由 ART 管理的 Java/Kotlin 调用栈），并在 Java 堆上构造内部 trace 和后续的 `StackTraceElement[]`。这条路径要求 ART 的线程协调、对象访问与内存分配仍能工作。它不满足 async-signal-safe 要求；该术语指函数可在异步信号打断任意指令时安全调用。OOM 现场也不能依赖它完成最小数据写入。

### 2.3 `Throwable` 栈记录异常发生点

未捕获异常到达 handler 时，传入的 `Throwable` 通常已经保存了对象创建时或上次调用 `fillInStackTrace()` 时的栈。它是 Java Crash 的主证据，采样时刻可能早于 handler 执行时刻：

- 异常对象可以先创建、稍后抛出；
- 代码可以重写 `fillInStackTrace()` 或再次调用它；
- cause（异常原因链）与 suppressed exception（被抑制异常）各自保存栈；
- R8 代码压缩与混淆、日志截断和服务端长度限制会影响可见结果。

handler 再调用 `thread.getStackTrace()` 得到的是较晚的采样，栈顶很可能已经进入 handler。分析时应保留原始 `Throwable`，不要用 handler 时刻的新栈覆盖它。

## 3. ART SIGQUIT 线程转储与应用 Crash Handler 的边界

### 3.1 SignalCatcher 在普通线程上下文中处理 SIGQUIT

ART 会让相关线程屏蔽 `SIGQUIT`，再由专门的 SignalCatcher 线程通过 `sigwait()` 同步等待这个信号。`sigwait()` 在普通线程控制流里返回信号编号，不会把处理逻辑插入某条业务线程正在执行的指令中。Android 17 的 [`SignalCatcher::HandleSigQuit()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/signal_catcher.cc) 调用 `Runtime::DumpForSigQuit()`，后者再进入 `ThreadList::DumpForSigQuit()` 等诊断模块。

这个流程不会给每条 Java 线程各发送一次 `SIGQUIT`，也不会在任意业务线程的异步 signal handler 中直接遍历 Java 堆。SignalCatcher 已附着到 ART，可以按运行时规则使用锁、C++ 输出流和诊断对象；普通应用的 Native fatal handler 没有这些前提。

Android 17 的 [`ThreadList::Dump()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread_list.cc) 创建 `DumpCheckpoint`，通过 `RunCheckpoint()` 请求各线程执行 dump checkpoint，再等待并按诊断价值排序输出。checkpoint 是 ART 发给线程的协作式诊断请求：运行中的线程到达安全位置后执行；已经挂起的线程可由请求方代为检查。native unwind 指沿保存的寄存器和栈内存回溯 C/C++ 调用帧，也在这条诊断路径中发生。

由此得到三个诊断边界：

- 各线程的 dump 仍不是同一 CPU 指令时刻的原子快照；
- checkpoint、栈遍历、native unwind 和输出都可能耗时，故障或进程退出也可能让 trace 缺帧；
- 这条系统路径可以服务 ANR 和调试，不能被简化成普通 SDK 可复制的 `ThreadList::ForEach()` 调用。

### 3.2 ART dump 可以附加 Java monitor 关系

monitor owner 是当前持有对象 monitor 的线程，held lock 是线程在某个栈帧处被识别为仍持有的 monitor。Android 17 的 [`StackDumpVisitor`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 会把这些信息写在相应 Java frame 附近：

- `waiting to lock ... held by thread N`：线程处于 `BLOCKED` 或 monitor 竞争等待，ART 找到了目标 monitor 及 owner。
- `waiting on ...`：线程在 `Object.wait()` 一类等待中；它已经释放该对象 monitor，不能把该对象当前 owner 直接解释为唤醒责任方。
- `locked ...`：该 frame 被识别为持有某个 Java monitor。

下面是用于说明读取方式的简化示例，不是固定的 Android 17 输出格式：

```text
"main" ... tid=1 Blocked
  at com.example.Cache.read(Cache.kt:81)
  - waiting to lock <0x01234567> held by thread 23

"cache-writer" ... tid=23 TimedWaiting
  at com.example.Cache.refresh(Cache.kt:132)
  - locked <0x01234567>
  at java.lang.Object.wait(Native method)
  - waiting on <0x07654321>
```

这份样本支持“main 正在等待 thread 23 持有的第一个 monitor”。第二个 `waiting on` 表示 `cache-writer` 在等待通知或超时，无法据此判断第二个对象被某线程长期持有。`held by thread 23` 应与同一份 ART dump 头部的 Java `tid=23` 对应；`sysTid` 才是 Linux 内核线程 ID，两个编号不能混用。

### 3.3 `AnnotatedStackTraceElement` 属于隐藏的平台能力

ART 的 `Thread::CreateAnnotatedStackTrace()` 能构造带 `blockedOn`（当前阻塞对象）与 `heldLocks`（当前持有对象列表）的对象数组。frameworks/base 中的 [`WatchdogDiagnostics`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/WatchdogDiagnostics.java) 会通过隐藏的 `VMStack.getAnnotatedThreadStackTrace()` 使用这项能力。隐藏 API 指系统镜像内部可调用、普通应用 SDK 不承诺可用或兼容的接口。

这项能力有两个限制：

- 它是 `system_server` 等平台代码可用的内部接口。`system_server` 是承载 Android 大多数 Java 系统服务的核心进程，普通应用不具备相同权限与类路径。
- 实现会遍历 Java 栈、访问对象并分配数组，不是 Native fatal signal 下的安全替代方案。

公开的 `Thread.getStackTrace()` 只返回 `StackTraceElement[]`，不包含持锁对象、阻塞对象或 owner。普通应用不能假设存在稳定的 `thread.getLockedObjects()`。Java SE 提供 `ThreadMXBean.findDeadlockedThreads()` 等管理接口，但 Android 17 的[公共 API 清单](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt)中没有 `java.lang.management.ThreadMXBean`，应用代码不应把它当作 Android SDK 能力。

## 4. 不同故障现场怎样取 Java 栈

### 4.1 Java 未捕获异常：以已有 `Throwable` 为主

`Thread.UncaughtExceptionHandler` 是线程即将因未捕获异常退出时收到回调的接口，自定义 handler 通常就在抛出异常的线程上执行。此时 ART 多半还能执行 Java 代码，可用操作多于 Native signal handler；内存、栈空间和锁状态仍无法保证。

建议按下面的顺序限制采集范围：

1. 设置一次性 guard（原子进入标记），避免多线程同时崩溃时重复进入采集器。
2. 优先保存传入的 `Throwable`、崩溃线程标识和正常运行期已经准备好的 breadcrumb。
3. 只有在不是 `OutOfMemoryError`、`StackOverflowError`，并且写入预算允许时，补采主线程或少量白名单线程。
4. 限制 frame 数、cause 深度、suppressed 数量和总字节数。
5. 在 `finally` 中委托安装前保存的 default handler，让 Android 的上报与进程终止链继续执行。

时间预算只能阻止采集器继续处理下一条线程，无法中断一次已经进入 `getStackTrace()` 的跨线程挂起。若 fatal 回调必须在极短时间内返回，就不应在这里枚举全部线程。

OOM 路径需要把操作压到最少。`getAllStackTraces()` 会创建 `Map` 和大量对象，完整 JSON、压缩、数据库事务也会继续申请内存。可在正常运行期维护固定容量的记录，让 OOM handler 只写固定字段和已经存在的数据。自定义 handler 的委托结构见 [Java Crash 治理](02-java-crash-governance.md)。

应用不应通过“吞掉未捕获异常”来保留现场。Android 17 的 [`RuntimeInit.KillApplicationHandler`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 会先向 `ActivityManager` 报告 Crash，随后在 `finally` 中调用 `Process.killProcess()` 和 `System.exit(10)`。自定义 handler 若截断这条链，部分线程与业务状态会留在未定义的失败后状态。标准应用进程会退出，因此“崩溃线程留下了一把永远不释放的锁”不适用于默认终止流程；强行续命的进程也没有可依赖的一致性。

### 4.2 Native 致命信号：不要进入 ART 私有遍历

`SIGSEGV`、`SIGABRT`、`SIGBUS` 等同步致命信号发生时，故障可能位于 allocator（内存分配器）、GC、JNI、线程栈或 ART 自身。应用 signal handler 中不应执行以下工作：

- 调 JNI 或 Java 方法，包括 `Thread.getAllStackTraces()`；
- 通过偏移寻找 `Runtime::instance_`、`ThreadList`、`ManagedStack` 或 `ArtMethod`；
- 调 `SuspendAll()`、`SuspendThreadByPeer()`，或构造 ART handle scope（保护托管对象引用的内部作用域）；
- 使用 `malloc/new`、STL（C++ 标准库）容器扩容、普通 mutex（互斥锁）、数据库和网络；
- 用 `sigsetjmp/siglongjmp` 非局部跳转越过错误并继续运行应用。

`ArtMethod` 是 ART 的方法元数据结构，JIT frame 是即时编译代码的调用帧，read barrier 是 GC 读取对象引用时使用的校验或转发屏障，ART APEX 则是可独立更新的运行时系统模块。它们的布局与行为都属于私有实现。按设备版本维护偏移只会增加脆弱性，无法让已损坏的进程成为可信调试目标。采样 profiler 可以在受控挂起点完成 Java unwind（调用栈回溯），不代表同一逻辑能在任意 fatal signal 中安全执行。

Android 8 的 debuggerd handler 会先创建一个与故障进程共享地址空间的辅助线程；该线程再创建子进程，并按进程位数 `exec` [`/system/bin/crash_dump32` 或 `crash_dump64`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-8.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)。`exec` 会用指定程序替换子进程当前执行的程序映像。随后 `crash_dump` 连接 tombstoned（接收并保存系统 tombstone 的守护进程）并生成诊断数据。系统 tombstone 至少包含崩溃线程寄存器、maps（进程虚拟内存映射）和进程内各线程的 Native backtrace。能否识别托管代码帧取决于运行时与回溯器可获得的信息，采集端不应把它当作 ART SIGQUIT 的 Java monitor dump，也不能指望它给出 Java monitor owner。

普通应用应保留 debuggerd 的 signal 链。Android 12 / API 31 起，应用可在下次启动查询 `ApplicationExitInfo.REASON_CRASH_NATIVE`，并从 `getTraceInputStream()` 读取 tombstone protobuf；protobuf 是 Protocol Buffers 的二进制序列化格式，不能按普通文本解析。完整边界见 [Native 栈回溯与符号化](16-native-stack-unwinding-symbolication.md)，系统 signal/debuggerd 链路见 [Native Crash 治理](03-native-crash-governance.md)。

### 4.3 ANR：系统 trace 与事前采样互补

系统 ANR trace 更适合分析全线程 Java 状态和 monitor 关系。API 30 起，应用可在后续启动通过 `ActivityManager.getHistoricalProcessExitReasons()` 查询历史记录，并尝试从 `ApplicationExitInfo.getTraceInputStream()` 读取关联 trace。

使用这份数据时要保留以下条件：

- trace 位于独立的全局循环存储，可能被后续记录覆盖，所以流可以为 `null`；
- 进程发生 ANR 后若恢复、后来因别的原因退出，该退出记录仍可能带有早先 ANR trace；
- trace 抓取可能晚于阻塞点；`nativePollOnce()` 表示 Looper 正在等待事件，无法证明此前主线程一直空闲；
- 系统 trace 缺失时，单个 crash handler 或单次主线程栈不能补出完整 ANR 因果。

端侧 watchdog 可以在正常 Java 环境中定期或按触发条件采集主线程栈，并在持续卡顿期间保留少量连续样本。它能补充“阻塞从何时开始、栈是否变化”，却没有 system_server 掌握的输入分发、广播、Service 或 ContentProvider 超时上下文，只能标记为疑似卡顿或疑似 ANR。系统侧方法见 [ANR 分析](../../part2-performance/ch09-anr/03-anr-analysis.md)。

### 4.4 进程退出后：只合并进程外与预存证据

旧进程死亡后，新的应用进程不能再访问旧 ART 的线程、Java 对象或 monitor。重启后的工作是：

1. 查询 `ApplicationExitInfo`，按时间、进程名、PID（进程 ID）、reason 和 status 去重。
2. 区分 ANR 文本 trace 与 API 31+ Native tombstone protobuf，不能都按 UTF-8 解析。
3. 用进程启动时生成的 session ID（本次进程生命周期的唯一标识）关联 Crash 前 breadcrumb、资源水位和业务阶段。
4. 保存“系统证据”“端侧预判”“服务端推断”三种来源，不用一个字段混写。

没有拿到 trace 时，应记录缺失原因和采集版本。退出时间附近的一条普通日志只能作为旁证，不能补写成“完整线程现场”。

## 5. 锁等待分析：先确认等待类型

### 5.1 Java 线程状态不等于锁类型

`BLOCKED`、`WAITING` 和 `TIMED_WAITING` 是 Java 线程状态，只描述采样时的等待形态。AQS（AbstractQueuedSynchronizer，`ReentrantLock` 等并发工具使用的队列同步框架）、Binder 同步调用、Looper 事件循环和 Native 条件变量都可能让线程等待，却不归 ART Java monitor 的 owner 模型管理。`LockSupport.park()` 是 AQS 常用的线程暂停原语，直到收到唤醒许可、中断或发生伪唤醒才返回。

分析时需要把状态、栈帧和对应同步机制一起看：

| 表象 | 常见路径 | 能否直接从 ART monitor dump 找 owner | 分析重点 |
| --- | --- | --- | --- |
| `BLOCKED` + `waiting to lock` | `synchronized` 进入对象 monitor | 通常可以，dump 可给 `held by thread N` | owner 的栈、持锁栈帧、等待链 |
| `WAITING` + `Object.wait()` | monitor 的等待集合 | 不能把等待对象当成当前 owner；调用者已释放 monitor | 谁负责 `notify/notifyAll`、条件是否可能成立 |
| `WAITING/TIMED_WAITING` + `LockSupport.park()` | AQS、`ReentrantLock`、`Condition` | 不属于 ART monitor owner 模型 | AQS 队列、业务锁对象、重复样本或锁事件记录 |
| native `futex_wait*` | `pthread_mutex`、condvar（条件变量）或其他 futex 用户 | 不能 | Native 栈、锁事件记录、调度时间线 |
| `BinderProxy.transact*` | 同步 Binder IPC 等待回复 | 不能 | 客户端请求、服务端线程与后续等待 |
| `nativePollOnce()` / `epoll_wait()` | Looper 或事件循环等待事件 | 通常没有需要修复的 owner | 是否有到期消息、trace 是否抓晚 |

`ReentrantLock` 底层可能使用 park/futex，但它不属于对象 monitor；Native mutex 也不在 ART monitor 表中。内核的 `futex_wait` 只说明线程进入某个 futex 竞争等待，无法证明它对应哪一把上层锁，也不会自动给出 owner。

### 5.2 等待图只接受有 owner 的边

wait-for graph（等待关系图）以线程为节点，以“等待者正在等待 owner”作为有向边。从 ART dump 构图时，可以把 `waiting to lock ... held by thread N` 转换为 `waiter -> owner`。`locked ...` 用于核对 owner 当前持有的 monitor；`waiting on ...`、Binder、I/O 和普通 park 没有同类 owner 证据，不能凭猜测加入 monitor 图。

一个可用的判断流程是：

1. 在同一份 dump 内按 Java `tid` 关联 waiter 与 owner。
2. 核对 waiter 等待的对象标识与 owner 的 `locked` 对象是否一致。
3. 继续检查 owner 是否又 `waiting to lock` 另一把 monitor。
4. 出现循环等待时，用第二份样本或 Perfetto 再确认；各线程快照没有严格的同时性。
5. 没有循环等待时，继续判断是长持锁、owner 未获 CPU、owner 在 I/O/Binder，还是 trace 已经抓晚。

单次 dump 只能证明“采样附近观察到了等待关系”，不能给出锁已经持有多久。对象标识也只适合同一份现场内关联，不能跨进程或跨多次 GC 当作永久锁标识。

### 5.3 需要时长时，引入时间轴

堆栈回答“采样时在哪里”，trace 可以回答“持续多久、期间怎样变化”。Perfetto 是 Android 的系统级 trace 采集与分析工具；slice 是 trace 中带开始时间和持续时间的区间事件，data source 是配置中指定的数据生产来源。PerfettoSQL 是查询 Perfetto trace 的 SQL 方言。Android 17 上可按问题类型选择：

- Java monitor：采集包含 ART monitor-contention slice 的 Perfetto trace，导入 [`android.monitor_contention` PerfettoSQL 模块](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/monitor_contention.sql)，再查询 `android_monitor_contention` 表中的 waiter、owner、双方方法和等待时长。模块名是 SQL 导入入口，不是 trace 配置里的 data source 名。
- 线程调度：查看 `sched_switch`（内核线程切换事件）和线程状态，确认 owner 正在运行、等待 CPU，还是已经睡眠。
- Binder：关联 transaction 与 reply，沿同步 IPC 进入服务端线程。
- Native 锁：结合 Native 调用栈、futex wait 和应用或平台记录的锁事件。
- 主线程长任务：结合 Looper/atrace slice、帧时间线和多次主线程栈。

Perfetto 没记录到锁竞争事件，仍可能存在竞争；trace 配置、采样窗口、设备实现和数据裁剪都会影响可见性。系统化的锁诊断见 [锁竞争与同步性能分析](../../part1-fundamentals/ch01-architecture/14-lock-contention.md)。

## 6. 推荐的端侧采集分层

### 6.1 正常运行期

- 维护固定容量 breadcrumb、进程 session ID、页面或任务阶段，以及内存、线程数、文件描述符等资源水位。
- 对主线程卡顿使用有线程数、频率和总字节上限且可关闭的选定线程采样。
- 对关键业务锁记录等待开始、获得、释放和稳定的逻辑锁名；不要上传对象地址。
- 记录线程名时同时保留稳定角色，例如 main、render、binder-worker、业务 executor（线程池执行器）。
- 采集代码本身要有耗时、分配量、失败率和丢弃数监控。

### 6.2 Java fatal handler

- 原始 `Throwable` 是主栈，不再用 handler 栈覆盖。
- OOM/栈溢出走最小写入路径。
- 只在预算允许时补主线程或少量白名单线程。
- 不同步上传，不等待普通业务锁。
- 委托之前保存的 default handler。

### 6.3 Native fatal handler

- 使用预注册的 signal handler、备用信号栈、固定内存，以及预先打开的 IPC 通道和 FD（文件描述符）。
- 只保存 signal、fault address、寄存器上下文和预存注解，或通知外部 dumper（独立转储进程）。
- 继续交给 debuggerd/既有 handler，避免吞掉系统 tombstone。
- Java 全线程与 monitor 图留给 ANR/SIGQUIT、正常期采样或平台级工具。

### 6.4 下次启动

- 避开应用启动和首帧的关键时段，再读取历史退出记录。
- 给 trace 读取设置字节数与耗时上限，并校验类型、大小和完整性。
- 用 build ID、R8 mapping ID、版本和 ABI 做精确符号化。build ID 是 ELF（Android Native 可执行文件和共享库使用的二进制格式）中的构建标识，R8 mapping ID 对应一次混淆映射，ABI 表示处理器架构与二进制调用约定。
- 合并预存证据并上传，服务端按证据强度对相似故障分组。

## 7. 常见误判

| 误判 | 修正 |
| --- | --- |
| `getAllStackTraces()` 会全局暂停并生成原子快照 | Android 17 逐线程调用 `getStackTrace()`，每条栈采样时间不同 |
| `Thread.getStackTrace()` 只读内存，几乎没有成本 | 跨线程路径会挂起目标线程，并创建 Java 栈对象 |
| Native Crash 时直接调用 ART `ThreadList::ForEach()` 更完整 | 私有 ABI、运行时锁和对象分配在 fatal signal 下都不安全 |
| SIGQUIT 会逐个 signal 所有 Java 线程 | ART SignalCatcher 用 `sigwait()` 接收，再通过 checkpoint 组织线程 dump |
| 公开 `StackTraceElement[]` 能看到锁 owner | 普通公开栈没有 blocked/held object；详细注解来自 ART/platform 私有路径 |
| `WAITING` 就是等某线程持锁 | `Object.wait()` 已释放 monitor；park、Binder、I/O 也可表现为等待 |
| 一个 `futex_wait` frame 就能定位 Java 锁 | futex 是底层等待原语，还要用 native/Java 栈和事件关联语义 |
| 单次线程 dump 能证明死锁和等待时长 | 它只是一组时间接近的快照；循环等待与持续时间应由重复样本或 trace 确认 |
| Crash handler 返回后继续运行能保住用户数据 | 未捕获异常后的共享状态不可依赖，还会截断 Android 的报告与终止链 |
| `ApplicationExitInfo` 一定带完整 trace | trace 可能缺失或被全局循环存储覆盖，类型也随退出原因不同 |

## 8. Android 版本边界

| 版本 | 相关的公开或系统能力 |
| --- | --- |
| Android 8 / API 26 | Native crash 进入按需启动的 `crash_dump32/64` 架构；普通应用仍不能读取系统 tombstone 目录 |
| Android 11 / API 30 | `ApplicationExitInfo` 与历史退出查询公开，可在 trace 尚未被覆盖时读取 ANR 记录 |
| Android 12 / API 31 | `REASON_CRASH_NATIVE` 的 trace stream 可返回 tombstone protobuf |
| Android 17 / API 37 | 源码锚点；公开 `Thread` API 仍不给普通应用 monitor owner 或原子全线程快照 |

Android 17 的 Java monitor 解释不能直接套到内核。`android17-6.18-2026-06_r6` 的 scheduler/futex 证据用于说明线程为何睡眠或迟迟未运行；`synchronized` 对象、held lock 与 owner 的解释仍以 `android-17.0.0_r1` 的 ART dump 为准。

## 9. 验证清单

- [ ] Java Crash 样本保留原始 `Throwable`，没有被 handler 当前栈覆盖。
- [ ] 自定义 handler 委托原 default handler，多 SDK 安装顺序经过测试。
- [ ] OOM 与 `StackOverflowError` 不执行全线程 `Map`、压缩或数据库事务。
- [ ] 正常期线程采样限制线程数、frame 数、总字节和会话频率。
- [ ] Native handler 不调用 JNI、Java、私有 ART、allocator 或普通 mutex。
- [ ] Native crash 后能保留系统 tombstone，API 31+ 按 protobuf 读取。
- [ ] ANR trace 与端侧 watchdog 样本分别标明系统证据和疑似事件。
- [ ] `waiting to lock`、`waiting on`、park、Binder 和 futex 使用不同解释。
- [ ] wait-for graph 使用 Java `tid`，并通过重复样本或 Perfetto 确认循环等待。
- [ ] 无 trace、截断、读取失败和被覆盖都作为明确结果上报。

## 10. 源码与文档入口

- Android 17 [`java.lang.Thread`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)：核对逐线程 `getAllStackTraces()` 与公开栈语义。
- Android 17 [`dalvik_system_VMStack.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/dalvik_system_VMStack.cc)：核对当前线程直接取栈、其他线程 `SuspendThreadByPeer()` 路径。
- Android 17 [`thread_list.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread_list.cc) 与 [`signal_catcher.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/signal_catcher.cc)：核对 SIGQUIT、checkpoint 与线程 dump。
- Android 17 [`thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)、[`stack.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/stack.cc) 与 [`monitor.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc)：核对 StackVisitor、locked/waiting/blocked 输出和 monitor owner。
- Android 17 [`WatchdogDiagnostics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/WatchdogDiagnostics.java)：核对平台隐藏 annotated stack 的使用边界。
- Android 17 [`RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java) 与 [libcore 公共 API 清单](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt)：核对默认 Java Crash 终止链和 `ThreadMXBean` 的 SDK 边界。
- Android 8 [`debuggerd_handler.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-8.0.0_r1/debuggerd/handler/debuggerd_handler.cpp)、[`crash_dump.cpp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-8.0.0_r1/debuggerd/crash_dump.cpp) 与 [`Android.bp`](https://android.googlesource.com/platform/system/core/+/refs/tags/android-8.0.0_r1/debuggerd/Android.bp)：核对 `crash_dump32/64` 的生成和按需执行路径。
- [`Thread.getAllStackTraces()` API](<https://developer.android.com/reference/java/lang/Thread#getAllStackTraces()>)：核对非原子、多时刻快照的公开契约。
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)：核对 ANR trace、API 31+ Native tombstone stream 与可能为空的循环存储。
- [Android Native crash 与 tombstone](https://source.android.com/docs/core/tests/debug/native-crash)：核对 debuggerd 产物和全线程 backtrace。
- [查找 ANR 无响应线程](https://developer.android.com/topic/performance/anrs/find-unresponsive-thread)：核对 monitor、Binder、I/O 和抓取过晚等诊断分支。
- Android 17 [`monitor_contention.sql`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/monitor_contention.sql)：核对模块名、`android_monitor_contention` 表及 waiter/owner 字段。
- [Perfetto Android trace 分析示例](https://perfetto.dev/docs/analysis/common-queries#find-app-startups-blocked-on-monitor-contention)：核对 `android.monitor_contention` 模块及其 waiter/owner 解析字段。
- kernel `android17-6.18-2026-06_r6` 的 [ftrace 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/trace/ftrace.rst)：核对调度与内核 trace 能力，不把内核等待状态误写成 Java monitor owner。
