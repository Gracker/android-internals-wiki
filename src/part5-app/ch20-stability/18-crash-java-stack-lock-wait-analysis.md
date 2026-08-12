---
title: "Crash 状态下 Java 线程堆栈获取与锁等待分析"
chapter: "20.18"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
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

“Crash 时取全部 Java 栈”不是一个单一问题。Java 未捕获异常、Native 致命信号、系统 ANR 和进程退出后的回捞，拥有不同的运行时状态、权限和安全边界。把它们放进同一个 signal handler 方案，往往会把一次可诊断故障变成死锁、二次崩溃或残缺报告。

平台与 ART 源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。涉及 futex 与线程调度的底层判断时，内核锚点为 `android17-6.18-2026-06_r6`；Java monitor 的 owner、held lock 和栈帧仍由 ART 解释，不能从一个内核睡眠状态直接反推。

## 先按现场选择取证路径

| 现场 | 进程状态 | 应用可优先保存的证据 | 不应依赖的动作 |
| --- | --- | --- | --- |
| Java 未捕获异常 | ART 通常还能运行，但可能正处于 OOM、栈溢出或锁异常 | 已抛出的 `Throwable`、崩溃线程、预存 breadcrumb；资源允许时补少量目标线程 | 无限制遍历全部线程、同步网络、等待业务锁 |
| 系统 ANR / 调试 SIGQUIT | 进程仍存在，由 ART 的 SignalCatcher 执行诊断流程 | 系统 ANR trace、重复的主线程预采样、Perfetto | 把自定义 `sigaction(SIGQUIT)` 当成稳定公开接口 |
| Native 致命信号 | Java 堆、线程栈或运行时锁都可能不一致 | `siginfo_t`、`ucontext_t`、debuggerd tombstone 或外部 minidump | JNI、Java API、私有 ART 遍历、普通分配和锁 |
| 进程已经退出 | 进程内 Java 状态已经不存在 | `ApplicationExitInfo`、tombstone/ANR trace、进程退出前写好的记录 | 重启后再查询旧进程的 Java 对象或 monitor |

这里的分界比“能不能调用某个函数”更重要。一个 API 在正常运行期可用，不代表它适合未捕获异常回调；Java fatal handler 中偶尔成功的代码，也不代表它能放进 Native signal handler。

## `Thread.getAllStackTraces()` 的 Android 17 语义

### 它逐线程抓取，不做一次全局 `SuspendAll`

Android 17 的 [`Thread.getAllStackTraces()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java) 先取得活动线程数组，再循环调用每个线程的 `getStackTrace()`。下面的等价伪代码只保留影响一致性的部分：

```java
AllThreadsRecord record = getAllThreadsInternal();
Map<Thread, StackTraceElement[]> result = new HashMap<>();
for (int i = 0; i < record.count; i++) {
    Thread thread = record.threads[i];
    result.put(thread, thread.getStackTrace());
}
```

这段流程会分配线程数组、`HashMap`、各线程的栈数组和 `StackTraceElement`。`getAllThreadsInternal()` 先用 `ThreadGroup.activeCount()` 估算数组大小，再调用 `enumerate()`；线程并发创建时，枚举结果本身也不承诺覆盖每条活动线程。线程列表与每条栈的采样时刻不同，遍历期间线程可以继续运行、创建或退出。公开 API 文档也明确说明，每条栈只是快照，并且可能在不同时间取得。

因此，下面两种说法都不成立：

- “`getAllStackTraces()` 会先触发一次全局 GC 暂停，再原子地抓取全进程。”
- “这张 Map 表示同一个时刻的完整线程与锁状态。”

它适合正常运行期的诊断、受控 watchdog 或测试工具，不适合负责严格一致的死锁证明。

### 当前线程与其他线程走不同路径

`Thread.getStackTrace()` 进入 Android 私有的 `VMStack.getThreadStackTrace()`，Android 17 的 [`dalvik_system_VMStack.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/dalvik_system_VMStack.cc) 在 `GetThreadStack()` 中区分两种情况：

1. 目标就是调用线程：直接调用 `Thread::CreateInternalStackTrace()`。
2. 目标是另一条 Java 线程：调用线程先离开 runnable 状态，再用 `ThreadList::SuspendThreadByPeer()` 挂起这一条目标线程；栈对象生成后恢复目标线程。

跨线程取栈是逐个挂起目标线程，不是一次挂起所有线程。目标线程若正在执行不可及时到达 suspend point 的代码，取栈延迟就会增加；目标已经退出时，结果可以为空。

`CreateInternalStackTrace()` 通过 `StackVisitor` 遍历 managed stack，并在 Java 堆上构造内部 trace 与后续的 `StackTraceElement[]`。这条路径要求 ART、mutator lock 和对象分配仍可工作。它不是 async-signal-safe 操作，也不是 OOM 下的保底写入原语。

### `Throwable` 栈与“此刻的线程栈”也不同

未捕获异常到达 handler 时，传入的 `Throwable` 通常已经保存了创建或上次 `fillInStackTrace()` 时的栈。它是 Java Crash 的主证据，但不一定等于 handler 执行时的栈：

- 异常对象可以先创建、稍后抛出；
- 代码可以重写 `fillInStackTrace()` 或再次调用它；
- cause 与 suppressed exception 各自有栈；
- R8、日志截断和服务端限制会影响可见结果。

handler 再调用 `thread.getStackTrace()` 得到的是更晚的采样，栈顶很可能已经进入 handler。分析时应保留原始 `Throwable`，不要用 handler 时刻的新栈覆盖它。

## ART 的 SIGQUIT 线程转储不是应用 Crash Handler

### SignalCatcher 在普通线程上下文中处理 SIGQUIT

ART 会让相关线程屏蔽 `SIGQUIT`，再由专门的 SignalCatcher 线程通过 `sigwait()` 同步接收。Android 17 的 [`SignalCatcher::HandleSigQuit()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/signal_catcher.cc) 调用 `Runtime::DumpForSigQuit()`，后者再进入 `ThreadList::DumpForSigQuit()` 等诊断模块。

这不是“给每条 Java 线程各发送一次 SIGQUIT”，也不是在任意业务线程的异步 signal handler 中直接遍历 Java 堆。SignalCatcher 是 ART 已知、已附着的线程，能使用运行时锁、C++ stream 和诊断对象；普通应用的 Native fatal handler 不具备这个前提。

Android 17 的 [`ThreadList::Dump()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread_list.cc) 创建 `DumpCheckpoint`，通过 `RunCheckpoint()` 请求各线程执行 dump checkpoint，再等待并按诊断价值排序输出。已经处于挂起状态的线程和运行中的线程由 ART 按各自状态处理。

这带来三个诊断边界：

- 各线程的 dump 仍不是同一 CPU 指令时刻的原子快照；
- checkpoint、栈遍历、native unwind 和输出都可能耗时，故障或进程退出也可能让 trace 缺帧；
- 这条系统路径可以服务 ANR 和调试，不能被简化成普通 SDK 可复制的 `ThreadList::ForEach()` 调用。

### ART dump 可以附加 Java monitor 关系

Android 17 的 [`StackDumpVisitor`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 会把 monitor 信息写在相应 Java frame 附近：

- `waiting to lock ... held by thread N`：线程处于 `BLOCKED` 或锁膨胀等待，ART 找到了目标 monitor 及 owner。
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

这份样本支持“main 正在等待 thread 23 持有的第一个 monitor”。第二个 `waiting on` 表示 `cache-writer` 在等待通知或超时，它不等同于“第二个对象被某线程长期持有”。`held by thread 23` 应与同一份 ART dump 头部的 Java `tid=23` 对应，不能误配为 Linux `sysTid`。

### `AnnotatedStackTraceElement` 是隐藏的平台能力

ART 的 `Thread::CreateAnnotatedStackTrace()` 能构造带 `blockedOn` 与 `heldLocks` 的对象数组。frameworks/base 中的 [`WatchdogDiagnostics`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/WatchdogDiagnostics.java) 会通过隐藏的 `VMStack.getAnnotatedThreadStackTrace()` 使用这项能力。

这里有两个常被忽略的限制：

- 它是 `system_server` 等平台代码可用的内部接口，不是普通应用 SDK。
- 实现会遍历 Java 栈、访问对象并分配数组，不是 Native fatal signal 下的安全替代方案。

公开的 `Thread.getStackTrace()` 只返回 `StackTraceElement[]`，不包含持锁对象、阻塞对象或 owner。普通应用不能假设存在稳定的 `thread.getLockedObjects()`；Android 也没有面向应用公开 Java SE `ThreadMXBean.findDeadlockedThreads()` 这一套管理接口。

## 不同故障现场怎样取 Java 栈

### Java 未捕获异常：以已有 `Throwable` 为主

自定义 `Thread.UncaughtExceptionHandler` 运行在抛出未捕获异常的线程上。ART 通常仍能执行 Java 代码，所以它比 Native signal handler 有更多选择，但资源状态无法保证。

建议按下面的顺序收敛工作量：

1. 写入一次性 guard，避免多线程同时崩溃时重复进入采集器。
2. 优先保存传入的 `Throwable`、崩溃线程标识和正常运行期已经准备好的 breadcrumb。
3. 只有在不是 `OutOfMemoryError`、`StackOverflowError`，并且写入预算允许时，补采主线程或少量白名单线程。
4. 限制 frame 数、cause 深度、suppressed 数量和总字节数。
5. 在 `finally` 中委托安装前保存的 default handler，让 Android 的上报与进程终止链继续执行。

时间预算只能阻止继续采下一条线程，不能中断一次已经进入 `getStackTrace()` 的跨线程挂起。若业务要求 fatal 回调必须在很小时间内返回，就不要在这里枚举全部线程。

OOM 路径尤其要克制。`getAllStackTraces()` 本身会创建 Map 和大量对象，完整 JSON、压缩、数据库事务也会继续申请内存。更可靠的做法是正常运行期维护有界记录，OOM handler 只写固定字段和已经存在的数据。自定义 handler 的委托结构见 [Java Crash 治理](02-java-crash-governance.md)。

应用不应通过“吞掉未捕获异常”来保留现场。Android 的默认 `KillApplicationHandler` 会报告 crash 并终止进程；自定义 handler 若截断这条链，会让部分线程与业务状态继续处在未定义的失败后状态。此时讨论“崩溃线程留下了一把永远不释放的锁”也失去了正确前提：标准应用进程会退出，而强行续命的进程不再具备可依赖的一致性。

### Native 致命信号：不要进入 ART 私有遍历

`SIGSEGV`、`SIGABRT`、`SIGBUS` 等同步致命信号发生时，故障可能位于 allocator、GC、JNI、线程栈或 ART 自身。应用 signal handler 中不应执行以下工作：

- 调 JNI 或 Java 方法，包括 `Thread.getAllStackTraces()`；
- 通过偏移寻找 `Runtime::instance_`、`ThreadList`、`ManagedStack` 或 `ArtMethod`；
- 调 `SuspendAll()`、`SuspendThreadByPeer()` 或构造 ART handle scope；
- 使用 `malloc/new`、STL 扩容、普通 mutex、数据库和网络；
- 用 `sigsetjmp/siglongjmp` 跳过错误后继续运行应用。

`ArtMethod`、对象布局、JIT frame、read barrier 和 ART APEX 更新都属于私有实现。按设备版本维护偏移只能增加脆弱性，不能把损坏进程变成可信的远程调试目标。采样 profiler 在受控挂起点完成 Java unwind，也不等于它能在任意 fatal signal 上安全复用同一逻辑。

Android 8 起，系统按需启动 `crash_dump32/64`，由 debuggerd/tombstoned 生成诊断数据。系统 tombstone 能提供崩溃线程寄存器、maps，并为进程内各线程生成 native 或可识别的混合栈；它不等价于 ART SIGQUIT 的 Java monitor dump，也不能保证给出 Java monitor owner。

普通应用应保留 debuggerd 的 signal 链。Android 12 / API 31 起，应用可在下次启动查询 `ApplicationExitInfo.REASON_CRASH_NATIVE`，并从 `getTraceInputStream()` 读取 tombstone protobuf。完整的 Native 栈采集与符号化边界见 [Native 栈回溯与符号化](16-native-stack-unwinding-symbolication.md)，系统 signal/debuggerd 链路见 [Native Crash 治理](03-native-crash-governance.md)。

### ANR：系统 trace 与事前采样互补

系统 ANR trace 更适合分析全线程 Java 状态和 monitor 关系。API 30 起，应用可在后续启动通过 `ActivityManager.getHistoricalProcessExitReasons()` 查询历史记录，并尝试读取 `ApplicationExitInfo.getTraceInputStream()`。

使用这份数据时要保留以下条件：

- trace 位于独立的全局循环存储，可能被后续记录覆盖，所以流可以为 `null`；
- 进程发生 ANR 后若恢复、后来因别的原因退出，该退出记录仍可能带有早先 ANR trace；
- trace 抓取可能晚于阻塞点，看到 `nativePollOnce()` 不足以证明当时主线程一直空闲；
- 系统 trace 缺失时，单个 crash handler 或单次主线程栈不能补出完整 ANR 因果。

端侧 watchdog 可以在正常 Java 环境中定期或触发式采主线程栈，并在持续卡顿期间保留少量连续样本。它能够补充“阻塞从何时开始、栈是否变化”，但没有 system_server 掌握的输入分发、广播、service 或 provider 超时上下文，只能标记为疑似卡顿/疑似 ANR。系统 ANR 分析方法见 [ANR 分析](../../part2-performance/ch09-anr/03-anr-analysis.md)。

### 进程退出后：只合并进程外与预存证据

旧进程死亡后，新的应用进程不能再访问旧 ART 的线程、Java 对象或 monitor。重启后的工作是：

1. 查询 `ApplicationExitInfo` 并按时间、进程名、PID、reason 和 status 去重。
2. 区分 ANR 文本 trace 与 API 31+ Native tombstone protobuf，不能都按 UTF-8 解析。
3. 用进程启动时生成的 session ID 关联 crash 前 breadcrumb、资源水位和业务阶段。
4. 保存“系统证据”“端侧预判”“服务端推断”三种来源，不用一个字段混写。

没有拿到 trace 时应记录缺失原因和采集版本，而不是根据退出时间附近的一条普通日志补写成“完整线程现场”。

## 锁等待分析：先确认等待类型

### Java 线程状态不是锁类型

`BLOCKED`、`WAITING` 和 `TIMED_WAITING` 描述 Java 线程状态，不足以单独确定 owner：

| 表象 | 常见路径 | 能否直接从 ART monitor dump 找 owner | 分析重点 |
| --- | --- | --- | --- |
| `BLOCKED` + `waiting to lock` | `synchronized` / monitor enter | 通常可以，dump 可给 `held by thread N` | owner 的栈、持锁 frame、等待链 |
| `WAITING` + `Object.wait()` | monitor wait set | 不能把等待对象当成当前 owner；调用者已释放 monitor | 谁负责 `notify/notifyAll`、条件是否可能成立 |
| `WAITING/TIMED_WAITING` + `LockSupport.park()` | AQS、`ReentrantLock`、`Condition` | 不属于 ART monitor owner 模型 | AQS 队列、业务锁对象、重复样本或埋点 |
| native `futex_wait*` | `pthread_mutex`、condvar 或其他 futex 用户 | 不能 | native 栈、锁埋点、调度时间线 |
| `BinderProxy.transact*` | 同步 Binder 等回复 | 不能 | client/server transaction、服务端线程与后续等待 |
| `nativePollOnce()` / `epoll_wait()` | Looper 或事件循环空闲 | 通常没有需要修复的 owner | 是否有到期消息、trace 是否抓晚 |

`ReentrantLock` 最终可能使用 park/futex，但它不是对象 monitor；native mutex 也不在 ART monitor 表中。内核的 `futex_wait` 只说明线程睡在某个 futex 慢路径，不能证明是哪一把高级语言锁，更不能自动给出 owner。

### 等待图只接受有 owner 的边

从 ART dump 构造 wait-for graph 时，可以把线程作为节点，把 `waiting to lock ... held by thread N` 转换为 `waiter -> owner` 边。`locked ...` 用于核对 owner 当前持有的 monitor；`waiting on ...`、Binder、I/O 和普通 park 不应凭猜测加入 monitor owner 图。

一个可用的判断流程是：

1. 在同一份 dump 内按 Java `tid` 关联 waiter 与 owner。
2. 核对 waiter 等待的对象标识与 owner 的 `locked` 对象是否一致。
3. 继续检查 owner 是否又 `waiting to lock` 另一把 monitor。
4. 出现循环等待时，用第二份样本或 Perfetto 再确认，因为各线程快照没有严格的同时性。
5. 没有循环等待时，继续判断是长持锁、owner 未获 CPU、owner 在 I/O/Binder，还是 trace 已经抓晚。

单次 dump 能证明“采样附近观察到了等待关系”，不能给出锁已经持有多久。对象标识也只适合同一份现场内关联，不应跨进程或跨多次 GC 后当作永久 lock ID。

### 需要时长，就引入时间轴

堆栈回答“采样时在哪里”，trace 才能回答“持续多久、期间怎样变化”。Android 17 上可按问题类型选择：

- Java monitor：采集包含 ART monitor-contention slice 的 Perfetto trace，再用 PerfettoSQL `android.monitor_contention` 模块解析 waiter、owner、双方方法和等待时长。模块名称是查询入口，不是 trace 配置中的 data source 名。
- 线程调度：`sched_switch` / thread state，确认 owner 是 Running、Runnable 还是睡眠。
- Binder：关联 transaction 与 reply，继续进入服务端线程。
- native 锁：结合 native callstack、futex wait 和应用/平台锁事件。
- 主线程长任务：Looper/atrace slice、帧时间线和多次主线程栈。

Perfetto 没记录到 contention 也不能证明没有竞争；trace 配置、采样、设备实现和数据裁剪都会影响可见性。系统化的锁诊断见 [锁竞争与同步性能分析](../../part1-fundamentals/ch01-architecture/14-lock-contention.md)。

## 推荐的端侧采集分层

### 正常运行期

- 维护固定容量 breadcrumb、进程 session ID、页面/任务阶段和资源水位。
- 对主线程卡顿使用有界、低频、可关闭的选定线程采样。
- 对关键业务锁记录等待开始、获得、释放和稳定的逻辑 lock name；不要上传对象地址。
- 记录线程名时同时保留稳定角色，例如 main、render、binder-worker、业务 executor。
- 采集代码本身要有耗时、分配量、失败率和丢弃数监控。

### Java fatal handler

- 原始 `Throwable` 是主栈，不再用 handler 栈覆盖。
- OOM/栈溢出走最小写入路径。
- 只在预算允许时补主线程或少量白名单线程。
- 不同步上传，不等待普通业务锁。
- 委托之前保存的 default handler。

### Native fatal handler

- 使用预注册的 signal handler、备用栈、固定内存和预打开 IPC/FD。
- 只保存 signal、fault address、寄存器上下文和预存注解，或通知外部 dumper。
- 继续交给 debuggerd/既有 handler，避免吞掉系统 tombstone。
- Java 全线程与 monitor 图留给 ANR/SIGQUIT、正常期采样或平台级工具。

### 下次启动

- 延迟到非首帧关键路径读取历史退出记录。
- 有界读取 trace，校验类型、大小和完整性。
- 用 build ID、R8 mapping ID、版本和 ABI 做精确符号化。
- 合并预存证据并上传，服务端按证据强度聚类。

## 常见误判

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
| Crash handler 返回后继续跑能保住用户数据 | 未捕获异常后的共享状态不可依赖，还会截断 Android 的报告与终止链 |
| `ApplicationExitInfo` 一定带完整 trace | trace 可能缺失或被全局循环存储覆盖，类型也随退出原因不同 |

## Android 版本边界

| 版本 | 相关的公开或系统能力 |
| --- | --- |
| Android 8 / API 26 | Native crash 进入按需启动的 `crash_dump32/64` 架构；普通应用仍不能读取系统 tombstone 目录 |
| Android 11 / API 30 | `ApplicationExitInfo` 与历史退出查询公开，可在可用时回捞 ANR trace |
| Android 12 / API 31 | `REASON_CRASH_NATIVE` 的 trace stream 可返回 tombstone protobuf |
| Android 17 / API 37 | 源码锚点；公开 `Thread` API 仍不给普通应用 monitor owner 或原子全线程快照 |

Android 17 的 Java monitor 解释不能直接套到内核。`android17-6.18-2026-06_r6` 的 scheduler/futex 证据用于说明线程为什么睡眠或迟迟未运行；`synchronized` 对象、held lock 与 owner 的解释仍以 `android-17.0.0_r1` 的 ART dump 为准。

## 验证清单

- [ ] Java Crash 样本保留原始 `Throwable`，没有被 handler 当前栈覆盖。
- [ ] 自定义 handler 委托原 default handler，多 SDK 安装顺序经过测试。
- [ ] OOM 与 `StackOverflowError` 不执行全线程 Map、压缩或数据库事务。
- [ ] 正常期线程采样限制线程数、frame 数、总字节和会话频率。
- [ ] Native handler 不调用 JNI、Java、私有 ART、allocator 或普通 mutex。
- [ ] Native crash 后能保留系统 tombstone，API 31+ 按 protobuf 读取。
- [ ] ANR trace 与端侧 watchdog 样本分别标明系统证据和疑似事件。
- [ ] `waiting to lock`、`waiting on`、park、Binder 和 futex 使用不同解释。
- [ ] wait-for graph 使用 Java `tid`，并通过重复样本或 Perfetto 确认循环等待。
- [ ] 无 trace、截断、读取失败和被覆盖都作为明确结果上报。

## 源码与文档入口

- Android 17 [`java.lang.Thread`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)：核对逐线程 `getAllStackTraces()` 与公开栈语义。
- Android 17 [`dalvik_system_VMStack.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/dalvik_system_VMStack.cc)：核对当前线程直接取栈、其他线程 `SuspendThreadByPeer()` 路径。
- Android 17 [`thread_list.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread_list.cc) 与 [`signal_catcher.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/signal_catcher.cc)：核对 SIGQUIT、checkpoint 与线程 dump。
- Android 17 [`thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)、[`stack.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/stack.cc) 与 [`monitor.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc)：核对 StackVisitor、locked/waiting/blocked 输出和 monitor owner。
- Android 17 [`WatchdogDiagnostics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/WatchdogDiagnostics.java)：核对平台隐藏 annotated stack 的使用边界。
- [`Thread.getAllStackTraces()` API](<https://developer.android.com/reference/java/lang/Thread#getAllStackTraces()>)：核对非原子、多时刻快照的公开契约。
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)：核对 ANR trace、API 31+ Native tombstone stream 与可能为空的循环存储。
- [Android Native crash 与 tombstone](https://source.android.com/docs/core/tests/debug/native-crash)：核对 debuggerd 产物和全线程 backtrace。
- [查找 ANR 无响应线程](https://developer.android.com/topic/performance/anrs/find-unresponsive-thread)：核对 monitor、Binder、I/O 和抓取过晚等诊断分支。
- [Perfetto Android trace 分析示例](https://perfetto.dev/docs/analysis/common-queries#find-app-startups-blocked-on-monitor-contention)：核对 `android.monitor_contention` 模块及其 waiter/owner 解析字段。
- kernel `android17-6.18-2026-06_r6` 的 [ftrace 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/trace/ftrace.rst)：核对调度与内核 trace 能力，不把内核等待状态误写成 Java monitor owner。
