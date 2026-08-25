---
title: Binder 线程池、异步事务与 Freezer
chapter: '1.12'
section: '1.12'
status: finalized
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: '2026-08-19'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android 17 API 37 official documentation
confidence: high
sources:
- type: official
  path: https://source.android.com/docs/core/perf/cached-apps-freezer
- type: official
  path: https://source.android.com/docs/core/architecture/ipc/binder-freezer
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://developer.android.com/reference/android/os/IBinder
- type: official
  path: https://developer.android.com/reference/android/os/RemoteCallbackList
- type: official
  path: https://docs.kernel.org/admin-guide/cgroup-v2.html
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/IBinder.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/RemoteCallbackList.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ApplicationExitInfo.java @ android-17.0.0_r1
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/android/binder.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/cgroup/freezer.c
- type: aosp
  path: platform/frameworks/native/libs/binder/IPCThreadState.cpp (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/native/libs/binder/ProcessState.cpp (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/native/libs/binder/include/binder/IBinder.h (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/core/java/android/os/Binder.java (android-17.0.0_r1)
- type: kernel
  path: kernel/common/drivers/android/binder.c (android17-6.18-2026-06_r6)
- type: kernel
  path: kernel/common/drivers/android/binder_alloc.c (android17-6.18-2026-06_r6)
- type: official-docs
  path: https://perfetto.dev/docs/analysis/stdlib-docs#android-binder
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp
- type: aosp
  path: frameworks/native/libs/binder/IPCThreadState.cpp
- type: aosp
  path: drivers/android/binder.c (kernel android17-6.18-2026-06_r6)
- type: official
  path: source.android.com/docs/core/architecture/ipc/binder-threading
- type: official
  path: source.android.com/docs/core/architecture/ipc/binder-freezer
- type: official
  path: developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
- type: blog
  path: DeepResearch/2026-06-24-android-17-binder-ipc-latency-analysis-and-optimization.md
- type: blog
  path: DeepResearch/2026-06-26-android17-binder-perf-monitor-recording-aidl-trace.md
- type: blog
  path: DeepResearch/2026-06-27-android17-binder-async-frozen-batch-pipeline.md
tags:
- android
- binder
- cached-app
- freezer
- cgroup-v2
- oom-adjuster
- performance
- ipc
- 异步机制
- 批处理
- thread-pool
- starvation
- ANR
- IPC
- system_server
related_chapters:
- '1.1'
- '1.3'
- '5.3'
- '26.6'
- '1.9'
- '1.6'
- '9.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/01.30-android17-binder-transaction-queue-optimization.md
- src/part1-fundamentals/ch01-architecture/1.48-android17-binder-priority-inheritance.md
- src/part1-fundamentals/ch01-architecture/1.54-binder-thread-pool-implementation/1.54-binder-thread-pool-implementation.md
- src/part1-fundamentals/ch01-architecture/18-binder-freezer-cached-process.md
- src/part1-fundamentals/ch01-architecture/29-binder-async-transaction-queue.md
- src/part1-fundamentals/ch01-architecture/38-binder-thread-pool-starvation-performance.md
---

# Binder 线程池、异步事务与 Freezer

Binder 线程池饥饿是指一个进程暂时没有可用的 Binder 服务线程。调用方仍能把事务交给驱动，但事务可能在目标进程的待办队列中等待；同步调用方要一直等到服务端处理并回复。这个问题常与锁竞争、磁盘 I/O、嵌套 IPC 和异步 `oneway` 事务积压一起出现，单看线程数量容易误判。

以下用户空间行为以 `android-17.0.0_r1` 的 libbinder、framework 和 Perfetto 为准，内核行为以 `android17-6.18-2026-06_r6` 的 Binder 驱动为准。分开标注两处版本，是因为 libbinder 与内核驱动共同决定线程池行为，却来自不同源码仓库。

Binder 延迟由服务端线程供给、事务排队方式和目标进程状态共同决定。线程池饥饿会阻塞同步调用，异步队列会积累 oneway 事务，Freezer 则改变缓存进程何时能够消费这些事务。

## Binder 线程池、嵌套调用与饥饿

### 1. “默认 15 个线程”的准确含义

#### 1.1 `ProcessState` 初始化了什么

原生 Binder 首次创建 `ProcessState` 时会打开 Binder 设备，并为接收事务映射一段只读虚拟地址空间；驱动会把接收到的事务数据放进这段映射。Android 17 的两个相关常量是：

```cpp
#define BINDER_VM_SIZE ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
#define DEFAULT_MAX_BINDER_THREADS 15
```

`BINDER_VM_SIZE` 是 1 MiB 减去两个页，不宜简写成精确的 1 MiB。`DEFAULT_MAX_BINDER_THREADS=15` 也不等于“进程总共有 15 个 Binder 线程”。

`ProcessState.h` 对线程数的定义很明确：

- `setThreadPoolMaxThreadCount(n)` 配置内核最多按需请求的线程数；
- `startThreadPool()` 另外主动创建 1 个线程；
- 显式调用 `joinThreadPool()` 的线程另行计算。

在常见的 `startThreadPool()` 配置下，默认上界可理解为“1 个主动启动线程 + 最多 15 个内核请求线程”。如果程序显式让其他线程 `joinThreadPool()`，总数还能增加。线程池上限应结合启动方式解释，不能机械写成固定的“15+1”平台规则。

#### 1.2 Java App 主线程不默认加入 Binder 池

`frameworks/base/cmds/app_process/app_main.cpp` 在 app process 或 Zygote 子进程初始化时调用 `ProcessState::startThreadPool()`。这个调用会创建专门的 Binder 线程。

应用主线程继续运行处理界面消息的 `Looper`，不会因为 Activity 启动而调用 `IPCThreadState::joinThreadPool()`。主线程发起同步 Binder 调用时会等待回复，也可能在嵌套回调链中执行 Binder 工作，但这与“主线程长期注册为线程池工作线程”属于不同机制。

#### 1.3 `BC_ENTER_LOOPER` 与 `BC_REGISTER_LOOPER`

| 命令 | 来源 | 内核记账 |
|---|---|---|
| `BC_ENTER_LOOPER` | `joinThreadPool(true)` 或 polling setup | 标记为主动进入 Binder 读取循环的 looper |
| `BC_REGISTER_LOOPER` | 收到 `BR_SPAWN_LOOPER` 后创建的线程 | 消耗一次内核请求，并增加 `requested_threads_started` |

`startThreadPool()` 创建的首个 `PoolThread` 以 `main-pool-thread` 身份进入 `joinThreadPool(true)`。这里的 “main” 指 Binder 线程池内部角色，并非 Java UI 主线程。polling setup 则是由调用方自行轮询 Binder 文件描述符的接入方式。

#### 1.4 驱动何时请求新线程

在 `android17-6.18-2026-06_r6` 的 `binder_thread_read()` 尾部，驱动满足以下核心条件时返回“请用户空间再创建一个工作线程”的 `BR_SPAWN_LOOPER`：

- 当前没有尚未兑现的线程请求；
- `waiting_threads` 为空，即当前没有已在驱动中等待工作的线程；
- 已由内核启动的线程数低于 `max_threads`；
- 当前线程已经是合法 Binder looper。

libbinder 的 `IPCThreadState::getAndExecuteCommand()` 收到命令后调用 `ProcessState::spawnPooledThread(false)`，新线程再用 `BC_REGISTER_LOOPER` 向驱动注册。线程是按需增加的；进程不会在启动时一次性创建到上限。

源码锚点：

- `frameworks/native/libs/binder/ProcessState.cpp`
- `frameworks/native/libs/binder/include/binder/ProcessState.h`
- `frameworks/native/libs/binder/IPCThreadState.cpp`
- `frameworks/base/cmds/app_process/app_main.cpp`
- `drivers/android/binder.c`

### 2. 饥饿时各层发生了什么

#### 2.1 服务端队列与同步调用方

驱动收到事务后会优先从目标进程的 `waiting_threads` 选择可用线程。没有可用线程时，普通的进程级工作进入目标进程的待办链表 `proc->todo`。同步调用方阻塞在 libbinder 的 `waitForResponse()`，直到收到回复或错误。

调用方被阻塞的线程可能是 UI 主线程、业务线程，也可能是正在处理另一笔事务的 Binder worker（工作线程）。只有第三种情况会占用调用方进程的 Binder 服务能力。把每个同步客户端线程都计为“占用一个 Binder 池线程”会高估线程池消耗。

#### 2.2 100 ms 饥饿日志是用户空间的近似判断

Android 17 的 `IPCThreadState::getAndExecuteCommand()` 在执行一个驱动返回命令前增加 `mExecutingThreadsCount`。计数达到 `mMaxThreads` 时记录开始时间；计数回落后，如果持续超过 100 ms，输出：

```text
binder thread pool (15 threads) starved for 234 ms
```

这条日志是启发式信号：libbinder 只根据计数和持续时间作近似判断，说明它观察到“执行命令的线程数长时间达到配置阈值”。它很有价值，但不能单独证明：

- 每个线程都在执行应用的 `onTransact()`；
- 驱动队列里一定存在待处理事务；
- 延迟一定由 CPU 忙导致。

Binder 引用计数维护命令、嵌套调用、锁等待和调度延迟都可能计入这段时间，需要结合性能 trace 判断。可用下面的命令只查看 libbinder 的错误级别日志：

```bash
adb logcat -v threadtime -s libbinder.IPCThreadState:E
```

这条过滤命令可以找到饥饿提示，但不能替代线程和事务时间线分析。

`IPCThreadState::blockUntilThreadAvailable()` 确实存在，并会等待 `mExecutingThreadsCount < mMaxThreads`。但 Android 17 的标准 `transact()` 路径不会自动调用它；在 frameworks/native 中也没有把它接入每次出站事务。不能把该函数描述成“线程池一满，进程内所有新 Binder 调用都会先在此等待”。

#### 2.3 线程状态要看组合，不能只数 `Running`

典型状态及含义如下：

| 线程状态 | 可能含义 |
|---|---|
| `S`，阻塞点在 `binder_thread_read` | 空闲等待新事务，通常正常 |
| `S`，阻塞在 futex/Java monitor | 等锁、条件变量或同步结果 |
| `D` | 不可中断 I/O 等待，需继续找块设备或文件系统原因 |
| `R` 且正在 CPU 上运行 | 正在执行；还要检查运行的代码 |
| `R` 但长时间未上 CPU | runnable（已可运行但还未获 CPU）调度延迟，常见于系统负载高 |

“所有 Binder 线程显示 Running”只是一张瞬时快照。判定线程池饥饿需要同时看到：可用 worker 缺失、服务端工作持续未完成，以及调用方延迟或待办队列同时上升。

### 3. 三种高发模式

#### 3.1 慢接口实现：锁、I/O 和数据库

AIDL Stub 会在当前 Binder worker 上分发接口方法，不会自动切到业务线程池。服务实现中的锁等待、文件访问、数据库查询、网络代理调用和同步硬件操作都会延长 worker 占用时间。

常见问题包括：

- 持有服务内部锁时调用另一个 Binder 服务；
- 多个接口争用同一把全局锁；
- 在 Binder worker 上执行无超时的磁盘或设备 I/O；
- ContentProvider 查询缺少索引，或等待长事务释放数据库锁；
- 错误路径记录大对象、同步写文件或等待遥测上报。

增加 Binder 线程只能提高同时进入慢路径的请求数。共享锁、连接池或设备队列容量不变时，更多 worker 可能带来更长的排队和更大的内存压力。

#### 3.2 嵌套同步调用与重入

假设进程 A 的线程调用进程 B，而 B 的 Binder worker 又同步调用进程 C：

```text
A caller waits for B
  B binder worker waits for C
    C binder worker handles request
```

A 的调用线程（caller）不一定属于 Binder 池；B 的 worker 则在等待期间持续占用 B 的服务线程。多个并发请求重复这条链路时，B 更容易耗尽可用 worker。

Binder 还支持嵌套回调复用原调用链线程。若 C 回调 A，驱动可能把回调送回 A 正在等待的原线程。这里的“重入”是指线程尚未从前一次调用返回，就再次进入相关服务代码。它可以避免某些单线程死锁，却会让“同步 IPC 像普通本地调用一样不会重入”的假设失效。

设计服务锁时应遵守一条硬规则：持锁期间避免跨进程 Binder 调用。即使线程池只有一个 worker，嵌套调用也可能在同一线程重入并修改当前数据结构。

官方模型见 [AOSP Binder threading](https://source.android.com/docs/core/architecture/ipc/binder-threading)。

#### 3.3 oneway 积压

`oneway` 只保证调用方不等待服务端 reply。服务端仍要占用 Binder worker 执行方法。

驱动会串行处理发往同一个 Binder node（驱动中代表一个 Binder 对象的节点）的异步事务：一个事务正在处理时，后续事务进入该 node 的 `async_todo` 待办队列。不同 node 的异步事务可以并行。因此，一条高频 `oneway` 接口可能形成很长的单 node 队列，也可能与其他接口一起消耗整个进程的 worker。

Android 17 的 libbinder 默认请求开启 `BINDER_ENABLE_ONEWAY_SPAM_DETECTION`。异步 buffer 使用量达到驱动阈值时，相关 buffer 会被标记为可疑（suspect）；发送进程收到 `BR_ONEWAY_SPAM_SUSPECT`，libbinder 随后输出调用栈。`android17-6.18-2026-06_r6` 还会通过 Binder Generic Netlink 报告这类事件；Netlink 是内核向用户空间传递结构化消息的机制。

需要区分三层结果：

1. suspect：事务仍可能成功，只产生诊断信号；
2. 同 node 排队：事务已进入目标队列，尚未执行；
3. async 空间不足：分配失败，发送方得到失败结果。

`oneway` API 仍需限制调用频率、合并可覆盖的状态更新，并设置业务队列上界。把同步接口改成 `oneway` 只会改变等待发生的位置，不会自动减少服务端工作。

### 4. system_server 的边界

#### 4.1 AOSP Android 17 配置为 31

`SystemServer.java` 定义：

```java
private static final int sMaxBinderThreads = 31;
```

启动时通过 `BinderInternal.setMaxThreads(31)` 调到 `ProcessState::setThreadPoolMaxThreadCount()`。这 31 仍是内核按需启动的上限；app process 启动阶段的 `startThreadPool()` 另有 1 个主动线程。没有其他线程显式 join 时，总体上界通常可到 32。

system_server 主线程随后创建 Java `Looper`，不会因为 `setMaxThreads(31)` 自动加入 Binder 池。厂商分支也可能调整常量或加入额外线程，设备上的实际数量应以源码和运行时为准。

#### 4.2 跨服务影响

system_server 同时承载 AMS、WMS、PMS 等服务。某一组慢调用占满 Binder worker 后，其他互不相关的客户端也可能等待空闲线程。常见后果包括：

- App 主线程等待 system_server 的同步回复，输入和绘制无法继续；
- system_server 自身 worker 形成嵌套调用链，扩大多个服务之间的锁依赖；
- 服务启动、广播、Provider 获取等 framework 状态机无法按时推进；
- Watchdog 观察的关键线程或 Monitor 检查项（通常用于确认关键锁能否及时取得）也可能因同一把锁受阻。

不存在一条通用的 “Binder WATCHDOG” 规则专门按 Binder 调用延迟报警。Watchdog、ANR controller、Binder 饥饿日志和 Perfetto 分别观察不同对象，应分别核对。

### 5. Binder Freeze 对线程池的影响

cached 进程是系统暂时不需要其前台工作的缓存进程；被冻结后，其中的 Binder worker 也不能获得 CPU 调度。`android17-6.18-2026-06_r6` 的 `binder_proc_transaction()` 对两类事务分别处理：

- 同步事务：拒绝投递，返回 `BR_FROZEN_REPLY`；
- oneway：成功排入待处理队列，发送方收到 `BR_TRANSACTION_PENDING_FROZEN`。

libbinder 对前者返回 `FROZEN_OBJECT` 或兼容的 `FAILED_TRANSACTION`，对后者记录 “Sending oneway calls to frozen process”。内核还可用 Binder Generic Netlink 上报 frozen pending。

`oneway` 事务在冻结期持续到达时会占用异步事务 buffer。解冻后这些事务恢复处理，也可能形成短时积压。Android framework 会结合缓存应用冻结器（cached-app freezer）策略控制进程状态；发送调用已经返回，并不代表冻结进程中的目标方法已经执行。

`BINDER_GET_FROZEN_INFO` 返回的是目标进程在冻结期间是否收到过同步/异步事务的标志，不是“冻结前已处理完成的事务计数”。

源码锚点：

- `drivers/android/binder.c::binder_proc_transaction`
- `include/uapi/linux/android/binder.h`
- `frameworks/native/libs/binder/IPCThreadState.cpp::waitForResponse`
- [AOSP Binder freezer](https://source.android.com/docs/core/architecture/ipc/binder-freezer)

### 6. 线程选择与优先级继承

`binder_select_thread_ilocked()` 从 `waiting_threads` 链表头取出一个等待线程；而 Android 17 的等待路径用 `list_add()` 把新等待者插到链表头。因此当前实现更接近“最近进入等待队列的 worker 先被唤醒”，不能把它解释成先进先出（FIFO）调度。这个事实也不代表事务执行时“所有 worker 优先级完全相同”。

选中线程后，驱动调用 `binder_transaction_priority()`。它会综合事务携带的优先级、Binder node 允许的最低优先级与 `inherit_rt` 配置，临时调整服务线程的调度属性；事务结束后再恢复此前保存的优先级。实时调度策略是否能够继承，还受 node 配置和驱动限制。

同步事务会从调用线程携带可以继承的调度信息；普通 `oneway` 不继承调用方优先级，而是使用 Binder node 的最低优先级策略。`FLAT_BINDER_FLAG_INHERIT_RT` 只决定 node 是否允许继承实时调度策略，不等于给所有事务强制提升优先级。calling UID/PID 等身份字段也不携带 CPU 调度优先级，身份传播与调度继承是两套机制。

驱动在事务开始前保存 worker 的原优先级，完成后恢复。Android 17 的 `SET`、`PENDING`、`ABORT` 状态用于处理“设置事务优先级”和“恢复原优先级”之间的竞态，也就是两个动作并发交错时的结果不确定问题。若恢复请求与正在进行的设置交错，恢复动作会延后或取消，以免旧事务覆盖新事务刚设置的优先级。它约束的是同一 worker 上的事务切换，不是跨进程的全局优先级仲裁。

需要分开理解：

- 选择哪一个空闲 worker：当前实现由 `list_add()` 与链表头选择共同决定，更接近后进先出；
- 工作线程以什么优先级执行：由 Binder 优先级继承和 node 策略决定；
- 线程何时拿到 CPU：由内核调度器、cpuset（允许线程运行的 CPU 集合）、uclamp（调度利用率上下限）等共同决定。

Android 17 的行为描述仅适用于当前实现。Binder 优先级继承早已存在，没有跨版本提交证据时不应宣称本版新增了这项能力。

### 7. 与 ANR 的关系

线程池饥饿本身不会直接生成 App ANR。它会延长同步 IPC 或 framework 状态机的耗时，最终由对应的 ANR 超时机制判定。

| 场景 | AOSP/Pixel 默认边界 | Binder 可能扮演的角色 |
|---|---|---|
| 输入分发 | 通常 5 秒 | UI 主线程等待同步 reply，不能处理输入 |
| 前台 Service 执行 | 通常 20 秒 | 主线程在 service 回调前后被慢 IPC 阻塞 |
| 后台 Service 执行 | 通常 200 秒 | 同上，但默认窗口更长 |
| Broadcast | Android 13 及以下：前台优先级约 10 秒、后台优先级约 60 秒；Android 14+：前台约 10–20 秒、后台约 60–120 秒，是否 CPU-starved 会影响窗口 | 广播线程或主线程等待 IPC，system_server 也可能无法及时调度 |

这些是 AOSP/Pixel 默认值，OEM 可修改。`startForegroundService()` 后 5 秒内调用 `startForeground()` 属于另一类超时，不能与前台 Service 的 20 秒执行窗口混写。

官方说明见 [Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)。

ANR 现场应先回答两个问题：

1. App 主线程是否卡在同步 Binder 调用？
2. reply 对应的服务端线程在做什么？

只看到主线程栈顶是 `BinderProxy.transactNative` 还不足以定位原因。服务端可能正在运行、等待锁或 I/O、已经 runnable 却未获调度，也可能尚未从进程队列取出事务。

### 8. Android 17 上的诊断路径

#### 8.1 快速查看线程

下面的命令只读目标进程各线程的名称和调度状态：

```bash
adb shell 'pid=$(pidof -s com.example.app); \
for task in /proc/$pid/task/*; do \
  tid=${task##*/}; name=$(cat "$task/comm"); \
  case "$name" in binder:*|Binder:*) \
    state=$(awk "{print \\$3}" "$task/stat"); \
    echo "$tid $state $name";; \
  esac; \
done'
```

线程数量接近理论上界不能证明饥饿，因为 libbinder 启动过的池线程通常会留到进程退出。还要检查这些线程在目标时间窗内是否都有未完成工作。

ANR 文件位置随版本和构建而变，不应固定写成 `/data/anr/traces.txt`。优先使用 bugreport、`adb shell dumpsys activity lastanr`、Play/Crashlytics 报告以及同时间段 Perfetto。

#### 8.2 `binder_calls_stats` 能回答什么

可先用下面的命令查看 framework 收集的 Binder 调用统计：

```bash
adb shell dumpsys binder_calls_stats
```

Android 17 的输出按 UID、接口和方法提供 `cpu_time_micros`、`max_cpu_time_micros`、`latency_time_micros`、`max_latency_time_micros`、调用次数、异常数和 Parcel 大小等数据。详细记录通常采用抽样，输出会标明 sampling interval，也就是每隔多少次调用采集一条详细记录。

这些数据适合寻找高频方法或服务端执行耗时较高的方法。它并非 Binder 驱动队列监视器，单靠这份统计无法精确分离：

- 驱动中等待空闲 worker 的时间；
- 服务端获得 CPU 前的 runnable 调度延迟；
- 接口实现内部等待锁或下游 Binder 的时间。

`BBinder::startRecordingTransactions()` 与 `RecordedTransaction` 是独立的事务录制能力，并非 `binder_calls_stats` 的“更细统计模式”。它可以记录请求和回复 Parcel，可能包含敏感信息，也会引入存储开销，只适合在受控环境中调试。

#### 8.3 用 Perfetto 关联 client、server 和调度

采集 Binder driver、sched、AIDL 与锁竞争相关数据后，Android 17 Perfetto stdlib 可这样查询同步事务：

```sql
INCLUDE PERFETTO MODULE android.binder;
INCLUDE PERFETTO MODULE android.binder_breakdown;

SELECT
  client_process,
  client_thread,
  server_process,
  server_thread,
  aidl_name,
  client_dur / 1e6 AS client_ms,
  server_dur / 1e6 AS server_ms
FROM android_binder_txns
WHERE is_sync = 1
  AND server_process = 'system_server'
ORDER BY client_dur DESC
LIMIT 50;
```

`client_dur` 是同步调用方看到的实际经过时间（wall duration），`server_dur` 是服务端对应 Binder reply slice 的实际经过时间。两者之差可能包含驱动排队、调度、传输及其他边界开销，不能直接命名为“排队时间”。

若 `aidl_name` 为空，可能是 AIDL trace 未启用、接口没有生成相应的 trace 名称，或这笔事务缺少可关联的时间片。`BBinder::execTransact()` 的 `ATRACE_TAG_AIDL` 能产生接口/方法 slice，但没有版本历史证据时，不能把这项能力标为 Android 17 首次引入。

随后检查：

- 服务端线程的 `thread_state` 区间；
- `android_binder_server_breakdown` 对服务端实际经过时间的分类；
- monitor contention（Java 对象锁竞争）与 Binder 回复的关联；
- 同一时间窗内所有 Binder worker 是否持续无空闲；
- 调用端与服务端的 CPU、cpuset 和 runnable latency（线程可运行后等待 CPU 的时长）。

源码锚点：`external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql`。

### 9. 修复与容量调整

#### 9.1 修复慢路径

优先按以下顺序处理：

1. 缩短持锁范围，禁止持锁跨进程调用；
2. 给 I/O、设备调用和下游 IPC 设置明确超时；
3. 把无需同步返回的工作改成有上界的异步协议；
4. 对状态更新做合并，对事件流做限频；
5. 把高延迟方法与高频方法分离，避免共用同一业务队列或全局锁；
6. 验证异常路径、日志和遥测不会同步阻塞 Binder worker。

同步 AIDL 若必须立即返回结果，不能简单“扔进 Executor 后马上返回”。可以保留同步语义并缩短执行时间，也可以重新设计 callback/`oneway` 协议；后一种方案还要定义超时、取消、顺序和背压，也就是下游处理不及时的时候如何限制上游继续提交。

#### 9.2 何时调整线程上限

原生服务可以在 `startThreadPool()` 前调用：

```cpp
ProcessState::self()->setThreadPoolMaxThreadCount(newMax);
```

libbinder 不允许在线程池启动后降低上限。Java App 也没有面向普通 SDK 应用、可任意调整平台 Binder 池的公开 API。

只有在以下条件同时成立时，增加线程才可能有效：

- 多个互相独立的请求可以安全并行；
- 共享锁、数据库连接、设备队列仍有余量；
- trace 证明等待空闲 Binder worker 占主要延迟；
- 增加线程后的内存、调度和尾延迟经过目标设备验证。

如果所有 worker 都在等同一把锁，增加线程只会增加等待者。若服务内部已有专用线程池，Binder 上限还要与该线程池和下游容量一起设计。

#### 9.3 UI 框架与线程池策略无关

Flutter Platform Channel 或 Compose 协程（coroutine）可能在 UI 线程发起系统服务调用，慢同步 IPC 会造成界面卡顿；这属于调用方线程选择问题，不能由此推出“所有 Binder 调用都应切到 `Dispatchers.IO`”。

部分 framework API 要求在主线程调用，许多短 Binder 调用也适合留在主线程。应根据 API 契约和实测延迟决定线程：允许后台调用且可能阻塞的工作可移出 UI 线程；需要主线程状态的 API 则保持线程约束，并从服务端缩短延迟。

### 10. 版本边界与核查清单

以下版本边界涵盖 Android 12—17 的 freeze、oneway spam 和诊断演进，当前结论以 Android 17 为上限：

- 用户空间：`android-17.0.0_r1`
- kernel：`android17-6.18-2026-06_r6`
- Perfetto stdlib：`android-17.0.0_r1`

复核产品分支时至少检查：

- `ProcessState.cpp` 的默认线程数、VM size 与 spam detection 默认值；
- `app_main.cpp` 和服务 main 函数如何启动线程池；
- `SystemServer.java` 的 `sMaxBinderThreads`；
- `binder.c` 的 spawn、async serialization、freeze、priority 与 Netlink 路径；
- `IPCThreadState.cpp` 的饥饿时间与线程计数记录，以及相关返回码；
- Perfetto `android.binder` 模块当前字段；
- 设备实际 ANR 超时与厂商修改。

Binder 线程池问题的判断链条应从一次具体慢调用出发：调用方等了多久、服务端何时开始、工作线程其间在运行还是等待、同一时间还有多少可用线程。只看线程数、单条饥饿日志或一张线程快照，都不足以确定原因。


## 异步事务队列与反压

线程池决定服务端能同时处理多少工作，oneway 队列决定调用者不等待时压力积累在哪里。异步不等于没有排队。

Binder 的 `oneway`（单向）调用经常被概括成“异步、不会阻塞”。这句话只覆盖了调用方不等待业务回复这一层。调用方仍要把事务提交给驱动，驱动仍要为目标进程分配缓冲区，目标 Binder 线程仍要执行服务端代码；缓冲区耗尽、目标死亡或冻结等状态也可能在提交阶段反馈给调用方。

分析 Android 17 Binder 异步机制时，最好把一次调用拆成两个完成点：

1. **提交完成**：驱动已经接收事务，调用方收到 `BR_TRANSACTION_COMPLETE`，或收到冻结、死亡、缓冲区不足等结果。
2. **执行完成**：目标 Binder 线程已经运行服务端方法，相关状态变更也已完成。

同步调用用 `BR_REPLY` 把两个完成点关联起来。`oneway` 调用只观察第一个完成点，服务端执行成功、抛异常或何时完成，都不会通过原事务返回。

### 1. 从 `FLAG_ONEWAY` 到 `IPCThreadState::transact()`

原生 Binder 的 `IBinder::FLAG_ONEWAY` 与内核 UAPI（用户态和内核态共享的接口定义）中的 `TF_ONE_WAY` 都使用最低位 `0x01`。AIDL 中声明为 `oneway` 的接口或方法，会在代理端发起带该标志的事务。

Android 17 的 `IPCThreadState::transact()` 先把 `BC_TRANSACTION` 写入当前线程的输出缓冲区，再按标志选择等待方式。下面的代码用于观察分支，不代表一次事务只会触发一次 `ioctl`（用户态向 Binder 驱动收发命令的系统调用）：

```cpp
err = writeTransactionData(BC_TRANSACTION, flags, handle, code, data, nullptr);

if ((flags & TF_ONE_WAY) == 0) {
    if (reply) {
        err = waitForResponse(reply);
    } else {
        Parcel fakeReply;
        err = waitForResponse(&fakeReply);
    }
} else {
    err = waitForResponse(nullptr, nullptr);
}
```

同步路径需要等到 `BR_REPLY` 或错误。`oneway` 路径把两个输出参数都设为 `nullptr`，`waitForResponse()` 收到 `BR_TRANSACTION_COMPLETE` 后即可结束。

`BR_TRANSACTION_COMPLETE` 不能理解为“远端方法执行完毕”。它表示当前事务已经完成驱动侧的提交步骤。目标进程可能尚未被调度，事务也可能还在 `proc->todo` 或 `node->async_todo` 中等待。

#### 1.1 `mCallRestriction` 的准确边界

`ProcessState::setCallRestriction()` 设置进程的默认调用限制：

| 值 | 遇到同步 Binder 调用时的行为 |
|---|---|
| `NONE` | 允许调用 |
| `ERROR_IF_NOT_ONEWAY` | 记录错误和调用栈，调用继续 |
| `FATAL_IF_NOT_ONEWAY` | 终止进程 |

这个默认值必须在创建 Binder 线程状态之前设置。`ProcessState::setCallRestriction()` 会检查当前线程是否已经存在 `IPCThreadState`；每个新的 `IPCThreadState` 在构造时复制 `ProcessState::mCallRestriction`。

因此它包含两层状态：

- `ProcessState` 保存新线程采用的进程默认值。
- 每个 `IPCThreadState` 保存自己的副本，必要时可由当前线程临时改写并恢复。

修改进程默认值不会追溯更新已经创建的线程副本。它也与应用冻结机制（freezer）无关：freezer 在 Binder 驱动的 `binder_proc` 上工作，不会修改 libbinder 的调用限制。

#### 1.2 服务端异常不会返回给 `oneway` 调用方

Java Binder 服务端执行 `onTransact()` 时，如果 `oneway` 方法抛出 `RemoteException` 或 `RuntimeException`，`Binder.execTransactInternal()` 会记录异常并调用 `onUnhandledException()`，但不会把异常写入回复 Parcel。同步事务才会执行 `reply.writeException(e)`。

调用方在提交成功后，无法通过原 `oneway` 调用知道服务端是否失败。需要确认业务结果时，应设计独立回调、状态查询或事件确认，并明确超时、进程死亡和重复回调的处理方式。

### 2. 驱动如何排队 `oneway` 事务

驱动收到 `BC_TRANSACTION` 后，会解析 Binder 对象、在目标进程的 `binder_alloc` 中分配缓冲区、从调用方地址空间复制 Parcel 数据，然后把事务放入目标执行队列。

对 `oneway` 事务，`binder_proc_transaction()` 还要维护同一 Binder node 的串行语义。node 是驱动中代表目标 Binder 对象的节点；这里的顺序只覆盖发往同一 node 的异步事务。

```c
if (oneway) {
    if (node->has_async_transaction)
        pending_async = true;
    else
        node->has_async_transaction = true;
}

if (thread) {
    binder_enqueue_thread_work_ilocked(thread, &t->work);
} else if (!pending_async) {
    binder_enqueue_work_ilocked(&t->work, &proc->todo);
} else {
    binder_enqueue_work_ilocked(&t->work, &node->async_todo);
}
```

三种目标各有不同作用：

| 队列 | 进入条件 | 含义 |
|---|---|---|
| `thread->todo` | 驱动已经选中等待线程 | 事务直接交给该 Binder 线程 |
| `proc->todo` | 没有指定线程，且该 node 没有未完成的 `oneway` | 进入目标进程的公共工作队列 |
| `node->async_todo` | 同一 node 已有未完成的 `oneway` | 后续事务在该 node 上串行等待 |

目标进程用完第一个异步事务 buffer 并发送 `BC_FREE_BUFFER` 后，驱动才从该 node 的 `async_todo` 取出下一项，转入 `proc->todo` 并唤醒目标进程。

#### 2.1 顺序保证到哪里为止

Binder 驱动维护的是同一 node 上的 `oneway` 串行执行。以下情况不能据此推导全局顺序：

- 两个不同 Binder 对象，即使属于同一进程，也可能由不同线程并行处理。
- 同一个业务动作拆到多个 Binder 接口后，接口之间没有统一的 `oneway` 顺序。
- 服务端收到调用后把工作继续投递到其他线程，后续顺序由服务端队列决定。
- 进程冻结、死亡、缓冲区不足或厂商扩展钩子（hook）都可能改变可见时序。

如果协议要求 A 必须先于 B 生效，最好让 A、B 经过同一个串行执行点，或者给消息增加序列号和状态校验，不能只依赖“它们都是 `oneway`”。

#### 2.2 调用方优先级不会随 `oneway` 继承

Android 17 驱动为同步事务记录调用线程的受支持调度策略和优先级；`oneway` 事务使用目标进程的默认优先级：

```c
if (!(t->flags & TF_ONE_WAY) && binder_supported_policy(current->policy)) {
    t->priority.sched_policy = current->policy;
    t->priority.prio = current->prio;
} else {
    t->priority = target_proc->default_priority;
}
```

因此，`oneway` 不继承调用方的实时或普通线程优先级。目标 Binder node 自身配置的 `min_priority` 仍会参与 `binder_transaction_priority()`，只是其输入不再来自 `oneway` 调用方。

`FLAT_BINDER_FLAG_INHERIT_RT` 仅允许同步事务继承实时策略。驱动 UAPI 支持为 node 编码 `SCHED_NORMAL`、`SCHED_FIFO`、`SCHED_RR` 和 `SCHED_BATCH`，但应用不能因为某条调用重要就随意启用实时调度；权限、CPU 占用和优先级反转风险都要在目标设备上验证。

### 3. 事务缓冲区与异步配额

这里仅保留解释 `oneway` 反压所需的缓冲区与异步预算语义；映射区、分配器、RPC 上限和错误观测的完整细节见 [1.17 Binder 事务缓冲区与可观测性](17-binder-buffer-observability.md)。

#### 3.1 约 1 MB 来自用户态请求，4 MB 是内核上限

Android 17 的 `ProcessState.cpp` 仍按下面的大小建立 Binder 内存映射（mmap）：

```cpp
#define BINDER_VM_SIZE ((1 * 1024 * 1024) - sysconf(_SC_PAGE_SIZE) * 2)
```

`android17-6.18-2026-06_r6` 的 `binder_alloc_mmap_handler()` 则把内核可接受的映射大小限制为不超过 4 MB：

```c
alloc->buffer_size = min_t(unsigned long,
        vma->vm_end - vma->vm_start, SZ_4M);
```

二者共同决定实际大小。AOSP libbinder 只请求约 1 MB，所以标准路径仍得到约 1 MB 的接收缓冲区；`SZ_4M` 表示内核允许更大的用户态请求，不表示 Android 17 默认分配了 4 MB。

Binder mmap 是接收方读取事务数据的窗口。调用方不会直接写入目标进程的 mmap：驱动先在目标 `binder_alloc` 中分配 buffer，再通过 `binder_alloc_copy_user_to_buffer()` 等路径复制调用方 Parcel 数据。

#### 3.2 异步配额不是独立内存池

映射建立后，驱动初始化：

```c
alloc->free_async_space = alloc->buffer_size / 2;
```

同步和异步事务使用同一块映射。`oneway` 分配除了受总空闲空间约束，还要通过 `free_async_space` 检查；同步事务不受这项异步配额限制，但仍受总空间和碎片影响。

所以“每个进程可发送一笔接近 1 MB 的事务”不是安全结论。可用空间属于目标进程，并被并发事务、对象偏移表和其他 Binder 工作共同消耗。Java 层会根据事务失败时的上下文推测并报告 `TransactionTooLargeException`，这不是驱动返回的精确字节上限，不能据此反推出固定的单笔限制。

适合 Binder 的数据通常应当小而有界。大图、文件和连续媒体数据更适合文件描述符、共享内存或专门的数据通道；拆成多笔事务时还要处理部分成功和版本一致性。

#### 3.3 `oneway` spam 检测只用于压力诊断

这里的 spam 指同一发送进程大量占用目标异步空间的可疑行为。Android 17 驱动只有在异步剩余空间低于总 buffer 的 10% 时，才扫描当前发送进程在目标 `binder_alloc` 上的占用。如果该 PID 已有超过 50 个异步 buffer，或占用大小超过总 buffer 的四分之一，当前 buffer 会被标记为 `oneway_spam_suspect`。

调用方随后收到 `BR_ONEWAY_SPAM_SUSPECT`。libbinder 记录错误和调用栈，再按 `BR_TRANSACTION_COMPLETE` 的语义结束本次提交。

这个机制不按固定时间窗统计调用频率，也不会自动限流。触发时该事务已经获得 buffer；警告用于定位哪个发送进程正在加剧目标的异步空间压力。治理措施仍要由上层完成，例如合并可覆盖的状态更新、限制采样频率、为事件队列设置容量和丢弃策略。

### 4. 目标进程冻结时的同步与 `oneway` 分流

在 `android17-6.18-2026-06_r6` 中，`binder_proc_transaction()` 对冻结目标采用两种处理：

| 调用类型 | 驱动动作 | 调用方结果 |
|---|---|---|
| 同步 | 拒绝入队 | `BR_FROZEN_REPLY`，libbinder 返回 `FROZEN_OBJECT` 或 `FAILED_TRANSACTION` |
| `oneway` | 保留事务并排队 | `BR_TRANSACTION_PENDING_FROZEN`，libbinder 记录警告后以成功提交结束 |

`FROZEN_OBJECT` 是否单独暴露由 `enable_frozen_object_error` 特性控制；未启用时映射为 `FAILED_TRANSACTION`。无论映射成哪个用户态错误，同步事务都没有进入目标队列，解冻后不会自动重放。

`oneway` 事务已经入队，目标解冻后可以继续处理。调用方收到的 `BR_TRANSACTION_PENDING_FROZEN` 是一次即时诊断回执；对应的 `BINDER_WORK_TRANSACTION_PENDING` 在驱动返回该命令时就被释放。目标解冻后不会再补发一个 `BR_TRANSACTION_COMPLETE`。

驱动还会把冻结期间是否收到过同步或异步事务记录在 `sync_recv`、`async_recv` 中。这两个字段采用按位或累积，在查询或解冻流程中提供状态信息，解冻与进程释放时清零。

#### 4.1 `TF_UPDATE_TXN` 只替换特定的冻结队列项

`TF_UPDATE_TXN` 适合“旧状态可被新状态覆盖”的 `oneway` 更新，但它不是通用去重，也不是缓冲区溢出后的回收策略。Android 17 驱动只有在以下条件同时满足时才查找旧事务：

1. 新旧事务都带 `TF_ONE_WAY | TF_UPDATE_TXN`。
2. 目标进程处于冻结状态。
3. 同一 node 已有未完成的 `oneway`，新事务将进入 `node->async_todo`。
4. 旧事务与新事务的目标进程、事务码、完整 `flags`、发送 PID、目标 node 指针和 `cookie` 字段都匹配。

命中后，驱动先从 `node->async_todo` 移除旧事务，释放锁，再释放旧 buffer 和事务对象，最终保留新事务。把 buffer 释放移到锁外可以减少临界区工作，但查找旧事务仍是对目标队列的线性扫描。

使用这项标志的前提是消息具有覆盖语义。日志、增量计数、队列操作等不可丢事件不适合被新事务替换。

### 5. `BINDER_WRITE_READ` 如何批量收发命令

`IPCThreadState` 为每个线程维护 `mOut` 和 `mIn`。BC 表示用户态写给驱动的命令，BR 表示驱动返回给用户态的命令。`talkWithDriver()` 把待发送的 BC 命令与用于接收 BR 命令的空间放进同一个 `binder_write_read`：

```cpp
bwr.write_size = mOut.dataSize();
bwr.write_buffer = reinterpret_cast<uintptr_t>(mOut.data());
bwr.read_size = mIn.dataCapacity();
bwr.read_buffer = reinterpret_cast<uintptr_t>(mIn.data());

ioctl(mProcess->mDriverFD, BINDER_WRITE_READ, &bwr);
```

单次 `ioctl` 可以写入多条 `BC_TRANSACTION`、引用计数或 buffer 释放命令，也可以读取多条 `BR_*` 命令。它减少的是用户态与驱动之间的往返次数，不会把多笔业务事务合成一笔原子事务。

`mIn`、`mOut` 初始容量都是 256 字节，但 Parcel 可以增长。一次调用能处理多少命令取决于命令类型、当前缓冲区内容、目标执行时机和驱动返回量，没有固定的“每批 N 条”。同步调用还要继续等 `BR_REPLY`，可能经历多轮 `talkWithDriver()`。

#### 5.1 `flushCommands()` 与 `flushIfNeeded()`

`flushCommands()` 调用 `talkWithDriver(false)`，只写不读。第一次写入可能触发 `processPostWriteDerefs()`，并在 `mOut` 中产生新的 `BC_RELEASE` 或 `BC_DECREFS`；若仍有数据，函数会再写一次。

`flushIfNeeded()` 只在当前线程不属于 Binder 命令循环（looper）、没有正在服务 Binder 事务且未处于递归刷新时强制发送。普通线程可能很久不再进入驱动，积压在其 `mOut` 中的 `BC_FREE_BUFFER` 等命令会长期占用对端资源，因此需要在这些条件下强制发送。

批处理是 libbinder 的常规传输行为，不是调用者可以为某个 AIDL 方法打开的“批量模式”。业务层若要合并多条消息，仍需单独设计批量接口、上限和部分失败语义。

### 6. `oneway` 缩短调用方等待，不减少目标线程池工作

Android 17 libbinder 默认把 `BINDER_SET_MAX_THREADS` 设为 15。这个值是内核最多可请求用户态按需额外创建的 Binder 线程数；这类线程在源码中称为 lazy Binder 线程。它不等于进程内 Binder 线程总数：

- `startThreadPool()` 会主动创建一个主线程池线程。
- 内核在没有可用线程且符合条件时返回 `BR_SPAWN_LOOPER`，用户态再创建额外线程。
- 进程还可以主动调用 `joinThreadPool()`，或让其他线程以轮询模式（polling）参与 Binder 事件处理。
- 线程池启动后，libbinder 禁止缩小已设置的最大 lazy 线程数。

`oneway` 调用方在提交完成后可以继续工作，目标进程仍要占用 Binder 线程执行服务端方法。若服务端在 `oneway` 方法中做磁盘 I/O、长计算或等待其他锁，事务会在 node 队列和目标线程池中累积；此时客户端“很快返回”会掩盖服务端拥塞。

平台或服务端代码应尽快把重任务移交给设有容量上限的工作队列。工作队列还需要优先级、过期和合并策略，否则压力只是从 Binder 线程池转移到另一个队列。

### 7. 优先级继承与嵌套事务

同步 Binder 需要调用方等待结果，驱动因而记录调用线程的优先级，并在目标线程处理事务时，应用经过 node 最低优先级与 `inherit_rt` 约束后的值。回复完成后，驱动恢复目标线程原优先级。

Android 17 的 `binder_transaction_priority()` 用 `set_priority_called` 防止同一事务重复设置优先级。嵌套事务还通过 `BINDER_PRIO_PENDING`、`BINDER_PRIO_SET`、`BINDER_PRIO_ABORT` 协调“正在恢复旧优先级”与“新事务又需要提升优先级”的竞态。

这些状态用于保证恢复顺序，不能直接换算成固定的系统调用节省量或延迟收益。分析实时或音频服务的 Binder 优先级问题时，应同时查看 `binder_transaction`、`binder_set_priority`、`sched_switch` 和目标线程的调度策略。

### 8. 业务确认、超时与进程死亡

#### 8.1 回调是另一笔事务

`oneway` 加回调可以表达异步结果，但回调是独立的 Binder 调用，拥有自己的缓冲区、线程池和死亡条件。设计时至少要处理：

- 请求已经提交，但服务端尚未执行。
- 服务端执行时抛异常，没有发送回调。
- 回调发送前任一进程死亡。
- 超时后回调才到达，形成迟到结果。
- 重试产生重复请求或重复回调。

用 `CountDownLatch`、`ConditionVariable` 或协程等待回调时必须设置超时，并且不要在目标 Binder 线程池中等待一个还需要同一线程池处理的回调。没有超时的等待可能永久挂起，但这不是 `oneway` 自动产生的“必死锁”；是否形成死锁取决于等待依赖图和可用执行线程。

#### 8.2 死亡通知不是 `oneway` 业务事务

`linkToDeath()` 通过 `BC_REQUEST_DEATH_NOTIFICATION` 注册内核事件。目标 node 释放时，`binder_node_release()` 把 `BINDER_WORK_DEAD_BINDER` 放入每个观察者进程的 `proc->todo`，再唤醒可用 Binder 线程。用户态收到 `BR_DEAD_BINDER` 后用 `BC_DEAD_BINDER_DONE` 确认。

死亡通知（death notification）不占用普通事务 buffer，也不经过 `node->async_todo`。观察者进程若在确认前退出，驱动会在释放流程中清理 `delivered_death` 等未完成工作。它只通知对象所属进程已经死亡，不提供某笔 `oneway` 业务调用的执行结果。

### 9. Perfetto：分别看客户端提交与服务端执行

采集 Binder 驱动事件并启用相应的 AIDL / atrace 分类后，可以使用 Perfetto 标准库 `android.binder`。`android_binder_txns` 已经关联客户端、服务端和同步类型。

下面的查询用于找出目标时间范围内执行时间较长的 `oneway` 服务端方法：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_process,
  client_thread,
  server_process,
  server_thread,
  aidl_name,
  client_dur / 1e6 AS client_submit_ms,
  server_dur / 1e6 AS server_exec_ms
FROM android_binder_txns
WHERE is_sync = 0
ORDER BY server_dur DESC
LIMIT 50;
```

对 `oneway` 而言，`client_dur` 主要覆盖客户端提交过程，`server_dur` 覆盖服务端处理时间片（slice）。二者不构成同步调用那样的等待关系；服务端可以在客户端返回后才开始执行。

按进程汇总后，可以定位发送大量异步事务的进程和执行最慢的接收方：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_process,
  server_process,
  COUNT(*) AS txn_count,
  SUM(server_dur) / 1e6 AS total_server_ms,
  MAX(server_dur) / 1e6 AS max_server_ms
FROM android_binder_txns
WHERE is_sync = 0
GROUP BY client_process, server_process
ORDER BY total_server_ms DESC;
```

#### 9.1 不同问题需要不同证据

| 要回答的问题 | 主要证据 |
|---|---|
| 谁在发送或处理 `oneway` | `android_binder_txns.is_sync = 0`、AIDL 名称、客户端与服务端线程 |
| 服务端为何慢 | 服务端 Binder 时间片、线程状态、锁竞争、CPU 调度、I/O |
| 异步 buffer 是否紧张 | `BR_ONEWAY_SPAM_SUSPECT` 日志、Binder debugfs / binderfs 状态、驱动分配事件 |
| 目标是否被冻结 | freezer / cgroup 状态、Binder 冻结日志、驱动事件；只凭调用失败不够 |
| 一次 `ioctl` 带了多少命令 | 系统调用级轨迹或受控实验；`android_binder_txns` 本身不能还原 BC / BR 批次 |

普通 Perfetto Binder 时间片不一定直接显示 `BR_TRANSACTION_PENDING_FROZEN` 的命令名。把目标进程被冻结、`oneway` 事务提交、客户端警告三项对齐，才能确认该分支；不能只凭一条很短的客户端时间片推断。

### 10. 选择 `oneway` 时的检查表

#### 10.1 适合 `oneway` 的条件

- 调用方不需要立即返回值，也不需要知道服务端是否执行成功。
- 消息允许排队，且目标暂时变慢时，已经明确如何限流、合并或丢弃。
- 协议能处理迟到、重复、进程死亡和版本差异。
- 单条数据小而有界，不依赖大 Parcel 搬运批量内容。
- 顺序要求能落在同一 Binder node 或服务端明确的串行队列上。

#### 10.2 常见误区

| 误区 | Android 17 中的事实 |
|---|---|
| `oneway` 完全不阻塞 | 调用方仍要提交事务，可能受驱动、调度和 buffer 分配影响 |
| 返回成功表示服务端完成 | 只表示提交阶段没有返回错误；服务端结果未知 |
| `oneway` 不占 Binder 线程 | 只缩短调用方等待，服务端仍由 Binder 线程执行 |
| 异步事务有独立的 512 KB 内存池 | 同步与异步事务共用同一映射，异步事务另受半池配额限制 |
| Android 17 默认 Binder 池是 4 MB | AOSP libbinder 仍请求约 1 MB，内核 4 MB 是映射上限 |
| `oneway` 自动保证跨接口顺序 | 串行保证围绕同一 Binder node，跨 node 需要协议约束 |
| `oneway_spam_suspect` 会拒绝事务 | 它是异步空间不足时的诊断信号，不会执行限流 |
| `TF_UPDATE_TXN` 可解决所有队列堆积 | 只替换冻结目标上特定 node 队列中的等价更新事务 |

### 11. Android 17 版本边界

相关分析以平台源码 `android-17.0.0_r1` 和 Android 通用内核（common kernel）标签 `android17-6.18-2026-06_r6` 为准。`TF_ONE_WAY`、oneway spam、freezer、优先级状态机等机制来自多个历史版本，Android 17 延续并组合了这些能力。描述 Android 17 时应避免把沿用机制写成该版本首发特性。

不同设备还可能存在以下差异：

- `enable_frozen_object_error` 等 aconfig 功能开关的启用状态。
- 厂商对 Binder 扩展钩子（vendor hooks）、线程池上限和服务端工作队列的调整。
- 用户态是否仍使用 AOSP `BINDER_VM_SIZE`，以及内核是否采用同一 Android 通用内核标签。
- 系统轨迹配置是否采集 Binder 驱动、AIDL 名称、调度和 freezer 数据。

遇到设备差异时，应同时确认平台构建版本（build）、内核标签、厂商补丁、功能开关值和系统轨迹配置，不能只按 API 级别推断底层行为。


## 缓存进程冻结期间的 Binder 行为

目标进程被冻结后，事务队列还要处理投递、积压、唤醒和失败语义。Freezer 的收益与风险取决于这些事务是否允许延迟。

Android 会把退到后台、当前没有重要工作的进程标为缓存进程（cached process），并暂时保留在内存中，以减少下次打开时的冷启动成本。但进程存活不代表它仍应执行工作：如果缓存进程继续运行轮询线程、定时器或回调，它仍会消耗 CPU，甚至唤醒设备。

缓存应用冻结器（Cached Apps Freezer）在“继续运行”和“杀掉回收”之间增加了一种状态：

```text
进程仍存在、地址空间仍存在
            +
进程中的线程暂时不能获得 CPU
```

冻结后，进程和地址空间仍在，但其中的线程暂停执行。它节省的是缓存进程的 CPU 与唤醒成本。内存压力到来时，低内存终止守护进程 `lmkd` 仍可杀掉它；进程重新进入前台或接到生命周期工作时，系统也可以先解冻再继续执行。

Binder 路径需要单独处理。被冻结的线程无法处理进程间通信：同步调用不能无限等待，`oneway` 异步事务也不能无限堆积。以下结合 Android 17 框架与 Android 通用内核（Android Common Kernel，ACK）6.18 源码说明这条链路。

### 1. 先区分冻结器、Doze 和 LMK

| 机制 | 主要对象 | 直接动作 | 进程内存 | 恢复方式 |
| --- | --- | --- | --- | --- |
| Cached Apps Freezer | 已进入缓存状态的应用进程 | 暂停线程执行 | 通常仍保留 | 系统解冻后继续执行 |
| Doze / App Standby | 设备或应用的后台活动 | 延后或限制 Job、Alarm、网络等能力 | 不要求进程冻结 | 满足窗口、配额或状态条件 |
| 后台启动 / 前台服务（FGS）限制 | 组件启动与长期后台执行 | 拒绝、限时或约束组件行为 | 不直接决定是否保留 | 依组件和用户可见状态变化 |
| `lmkd` | 内存压力下的低优先级进程 | 杀进程并回收内存 | 释放 | 下次需要时重新启动 |

因此，下列推断都不成立：

- “进程被冻结，所以按比例分摊的物理内存（PSS）已经释放。”
- “应用处于 Doze，所以进程一定没有 CPU 时间。”
- “进程处于缓存状态，所以它一定已经被冻结。”
- “进程已被冻结但仍在内存，所以不会被杀。”

是否启用 Cached Apps Freezer 还受设备配置影响。AOSP 提供 `activity_manager_native_boot/use_freezer` 和开发者选项，但量产设备是否启用、控制组（cgroup）如何布局、厂商是否增加自己的后台策略，都需要在实机上确认。

### 2. Android 17 的决策链：先把进程重要性转换成 CPU 执行资格

`oom_adj` 是进程在内存压力下的终止优先级分值，通常数值越低，进程越重要；进程状态（proc state）则描述它当前处于前台、服务、缓存等哪一类状态。理解当前实现时，不能只背一句“`oom_adj >= CACHED_APP_MIN_ADJ` 就冻结”。Android 17 会把这些状态转换为 CPU 执行资格（capability），再决定能否冻结：

```text
Activity / Service / Broadcast / binding 等状态
                     │
                     ▼
OomAdjuster 计算 proc state、oom_adj 与 capability
                     │
                     ├─ PROCESS_CAPABILITY_CPU_TIME
                     └─ PROCESS_CAPABILITY_IMPLICIT_CPU_TIME
                                      │
                                      ▼
getFreezePolicy()
  ├─ 持有任一 CPU_TIME capability → 不冻结
  └─ 两者都没有                  → 可冻结
                                      │
                                      ▼
ActivityManagerService
  ├─ freezeAppAsyncLSP()
  └─ unfreezeAppLSP()
                                      │
                                      ▼
CachedAppOptimizer 执行 Binder freeze 与 cgroup freeze
```

流程图中的两个 `CPU_TIME` 标志都表示进程仍应获得 CPU 时间：一个来自当前明确工作，另一个保留旧 `oom_adj` 阈值所表达的兼容行为。

#### 2.1 显式 CPU_TIME：当前确实有工作要执行

`android-17.0.0_r1` 的 `psc/OomAdjuster.java` 会为下列典型状态授予 `PROCESS_CAPABILITY_CPU_TIME`：

- UID 位于电源管理允许名单。
- 进程处于顶部（top）状态，或持有用户可感知的前台 Activity。
- 正在启动或停止 Service。
- 承载前台服务。
- 正在接收广播。
- 正在运行 instrumentation 测试。
- CPU 执行资格通过重要客户端的绑定关系传递而来。

这比“缓存 / 非缓存”二分更能表达真实意图：一个进程当前是否仍有必须执行的工作。

#### 2.2 隐式 CPU_TIME：保留 oom_adj 阈值的兼容行为

Android 17 并没有丢掉 oom_adj。`getImplicitCpuCapability()` 在下面任一条件成立时授予 `PROCESS_CAPABILITY_IMPLICIT_CPU_TIME`：

```java
adj < mFreezerCutoffAdj
        ||
maxAdj < mFreezerCutoffAdj
```

默认阈值来自 `ActivityManagerConstants.DEFAULT_FREEZER_CUTOFF_ADJ`：

```java
Flags.prototypeAggressiveFreezing()
        ? HOME_APP_ADJ
        : CACHED_APP_MIN_ADJ
```

设备还可通过 `activity_manager/freezer_cutoff_adj` 修改它。由此形成三条边界：

- 常规配置仍以缓存进程边界为基准。
- 激进冻结（aggressive freezing）实验可把资格范围提前到 `HOME_APP_ADJ`。
- 即使当前 adj 较低，`maxAdj` 约束也可能让进程继续获得隐式 CPU 时间。

排查“为什么没有冻结”时，要同时查看 adj、CPU 执行资格、功能开关和可在线调整系统参数的 DeviceConfig，不能只看 `curAdj`。

#### 2.3 旧实现里的两个判断已经不能代表 Android 17

较早版本的分析常引用：

```text
ProcessCachedOptimizerRecord.shouldNotFreeze()
ProcessCachedOptimizerRecord.isFreezeExempt()
```

Android 17 当前主路径的 `getFreezePolicy()` 不再靠这两个状态决定资格；`ActivityManagerService` 的兼容轨迹甚至把对应占位值固定为 `false`。描述 Android 17 时，应使用 `CPU_TIME` / `IMPLICIT_CPU_TIME` 模型。

这不表示所有豁免都消失了。官方文档仍列出两类实现级保护：

- 缓存进程持有文件锁并阻塞非缓存进程时，系统会避免继续冻结锁持有者。
- `BIND_WAIVE_PRIORITY` 连接可能让服务进程进入缓存状态，但在相关客户端全部进入缓存状态前仍保持可运行。

它们是冻结执行链上的保护条件，不应重新包装成旧版 `shouldNotFreeze()` 结论。

### 3. 进入缓存状态后为什么还要等 10 秒

Android 17 的默认值来自：

```xml
<integer name="config_defaultFreezerDebounceTimeout">10000</integer>
```

`CachedAppOptimizer` 允许用 `activity_manager_native_boot/freeze_debounce_timeout` 覆盖这个资源值。默认等待 10 秒有两个目的：

1. 避免 Activity 刚退后台、Service 刚结束时立刻冻结，打断仍在收尾的状态切换。
2. 避免短时间内反复冻结和解冻，增加调度、Binder 与日志开销。

这段等待也叫防抖（debounce），用于让短暂状态变化稳定下来。实现并非简单地“发一个 10 秒后的消息”。它会维护 `earliestFreezableTime`：临时解冻可能继续推迟最早可冻结时间；立即冻结请求也要与这个时间以及待处理状态协调。

因此，看到进程进入缓存状态后仍运行几秒，并不能直接说明冻结器失效。要先确认：

- 当前 CPU 执行资格是否允许冻结。
- `earliestFreezableTime` 是否还没到。
- 是否有尚未完成的 Binder 事务导致重试。
- 是否刚发生生命周期事件或文件锁保护。

### 4. 冻结时，Binder 必须先于 cgroup

Android 17 的 `CachedAppOptimizer.freezeProcess()` 顺序很明确：

```text
1. freezeBinder(pid, true, timeout)
   ├─ 阻止新的同步事务进入
   └─ 等待 outstanding transaction 排空

2. setProcessFrozen(pid, uid, true)
   └─ 把进程置入 freezer cgroup

3. 标记 ProcessCachedOptimizerRecord.frozen = true
   └─ 写 AM_FREEZE、statsd 与 trace

4. getBinderFreezeInfo(pid)
   └─ 冻结后再次检查竞态窗口中的 pending transaction
```

竞态窗口指第一次检查结束到线程真正冻结之间，状态仍可能发生变化的短暂时间。流程先阻止新的同步 Binder 事务并等待旧事务结束，再通过 cgroup 暂停线程。两个动作不能交换：如果先停掉线程，却让 Binder 驱动继续接受同步事务，调用端就可能等待一个永远不会执行的服务端。

ACK `android17-6.18-2026-06_r6` 的 `BINDER_FREEZE` 路径也说明了这一点：

1. 先设置目标 `binder_proc.is_frozen = true`，阻止新的同步事务。
2. 若传入超时时间，等待 `outstanding_txns` 归零。
3. 再检查仍在等待回复的事务调用栈。
4. 若检查失败，清除 `is_frozen`，并把失败交给 Android 框架处理。

`CachedAppOptimizer` 遇到尚未完成的事务，或冻结后新出现的待处理事务，不会把本次操作记录为冻结成功。它会解冻、调整重试时间并重新安排冻结；反复出现时还会识别 Binder 事务洪泛，避免应用靠持续发送事务永久逃过冻结。

### 5. cgroup v2 freezer：请求冻结不等于已经冻结

控制组（cgroup）是 Linux 按进程组管理 CPU、内存等资源的机制。ACK 6.18 使用 cgroup v2 的冻结功能，用户空间通过 `cgroup.freeze` 请求冻结或解冻。下面两条命令展示写入值的含义：

```bash
echo 1 > cgroup.freeze   # 请求冻结本 cgroup 及其后代
echo 0 > cgroup.freeze   # 请求解冻
```

写入只发出请求，内核还需要区分两个状态：

| 状态 | 含义 |
| --- | --- |
| `CGRP_FREEZE` | 用户空间已经请求冻结 |
| `CGRP_FROZEN` | 本 cgroup 的任务以及需要计入的后代已经达到冻结条件 |

因此，写完 `1` 以后，应观察 `cgroup.events`：

```text
frozen 1
```

只有这个状态变为 `1`，才表示冻结转换完成。某个任务还没运行到可安全暂停的位置时，`CGRP_FREEZE` 可以已经置位，而 `CGRP_FROZEN` 尚未成立。

#### 5.1 内核状态机

`android17-6.18-2026-06_r6/kernel/cgroup/freezer.c` 的关键路径是：

```text
cgroup_freeze(cgrp, true)
  └─ cgroup_do_freeze()
       ├─ set_bit(CGRP_FREEZE)
       ├─ 遍历 task
       │    └─ cgroup_freeze_task()
       │         ├─ JOBCTL_TRAP_FREEZE
       │         └─ signal_wake_up()
       └─ cgroup_update_frozen()
```

任务进入冻结点后，`cgroup_enter_frozen()` 会：

- 设置 `current->frozen = true`。
- 增加 cgroup 中已冻结任务的计数。
- 重新计算 `CGRP_FROZEN`。

解冻时则清除 `JOBCTL_TRAP_FREEZE`、唤醒任务，并在 `cgroup_leave_frozen()` 中更新计数。

#### 5.2 性能含义

冻结不是忙等：任务不会占着 CPU 循环检查“能不能解冻”。因此，Java 线程、C/C++ 工作线程、Handler 和协程都不会继续执行。

冻结也不是回收：

- 虚拟地址空间仍在。
- Java 堆和 C/C++ 堆仍在。
- 文件描述符和 Binder 引用仍在。
- 驻留物理内存（RSS）和按比例分摊的物理内存（PSS）不会因为 `cgroup.freeze=1` 自动归零。

Android 14 以后，Android 框架可能在冻结前后触发垃圾回收（GC）、内存压缩、匿名页换入 ZRAM 等辅助动作。ZRAM 是用压缩内存充当交换空间的机制。这些动作可能降低物理内存压力，但要与“冻结器本身暂停 CPU”分开描述。

### 6. Binder Freezer 的两条事务路径

#### 6.1 同步事务：驱动拒绝，系统终止被冻结的接收进程

目标 `binder_proc.is_frozen` 为 `true` 时，ACK r6 的 `binder_proc_transaction()` 对同步事务执行：

```text
proc->sync_recv = true
return BR_FROZEN_REPLY
```

平台对外的行为是：

- 同步事务不会排到冻结进程等待解冻。
- 调用端随后收到 `RemoteException`，已注册的 Binder 远端死亡监听也会被触发。
- 系统终止被冻结的接收进程，退出原因记录为冻结器。

Android 17 的 `CachedAppOptimizer` 同时保留两条发现路径：

- Binder 监控收到 `BR_FROZEN_REPLY` 报告后，直接按“冻结期间收到同步事务”处理目标 PID。
- 若即时报告能力未启用，解冻前的 `getBinderFreezeInfo()` 仍能发现 `SYNC_RECEIVED_WHILE_FROZEN` 并杀进程。

这项处理用于保护调用线程，与惩罚“服务端太慢”无关。最常见的应用错误是：

1. 客户端已经调用 `unbindService()`。
2. 服务端因失去重要绑定关系，退到缓存状态并被冻结。
3. 客户端仍保存旧的 `IBinder` 代理，继续发同步调用。

修复时要让 Binder 引用的生命周期与绑定关系一致：解绑后立即丢弃代理，不要把它当作永久可用的本地对象。

#### 6.2 oneway 事务：允许入队，但队列并非无限

`oneway` 事务命中冻结目标时，Binder 驱动会：

```text
proc->async_recv = true
transaction 入 async queue
return BR_TRANSACTION_PENDING_FROZEN
```

目标解冻后才会消费这些事务。这个设计避免了同步等待，却带来两个问题：

- 事务继续占用目标进程的 Binder 缓冲区；空间耗尽时，系统会以 `SUBREASON_FREEZER_BINDER_ASYNC_FULL` 终止目标。
- 事件可能已经过期；解冻后一次性处理大量旧回调，还可能造成 CPU 使用突增和业务状态倒退。

“改成 `oneway`”只解决了等待方式，没有解决事件模型。更合适的策略通常是：

| 事件语义 | 冻结期间策略 |
| --- | --- |
| 瞬时采样、下一次可重新获取 | 丢弃 |
| 当前状态，以最新值为准 | 只保留最新一条 |
| 每条都是不可丢的业务记录 | 有上限地排队，并设计补偿、去重和持久化 |

如果“不可丢”意味着无限排队，这个协议仍然没有完成设计。

### 7. API 36+：使用系统提供的冻结回调队列

#### 7.1 观察远端 Binder 的冻结状态

`IBinder.addFrozenStateChangeCallback()` 从 API 36 起成为公开 API。下面的示例注册回调，把远端是否冻结保存到 `remoteFrozen`：

```java
IBinder.FrozenStateChangeCallback callback = (who, state) -> {
    boolean frozen =
            state == IBinder.FrozenStateChangeCallback.STATE_FROZEN;
    remoteFrozen.set(frozen);
};

try {
    remoteBinder.addFrozenStateChangeCallback(executor, callback);
} catch (UnsupportedOperationException e) {
    // Kernel binder driver 不支持 frozen notification。
} catch (RemoteException e) {
    // 远端可能已死亡，按正常 Binder death 路径处理。
}
```

若注册成功，系统会通过给定的 `executor` 执行回调；异常分支分别处理内核不支持和远端已经死亡。

使用时要记住三个边界：

1. 只会观察远端 Binder；本地 Binder 与当前进程一起冻结或解冻。
2. 状态变化可能合并，只保证拿到最新状态，不能用回调次数统计冻结次数。
3. 内核不支持时会抛出 `UnsupportedOperationException`，必须有降级策略。

不再需要时可调用 `removeFrozenStateChangeCallback()`。所有 Binder 代理引用都释放后，注册也会自动移除，但显式解除通常更容易明确组件生命周期。

#### 7.2 用 RemoteCallbackList 表达事件策略

API 36 的 `RemoteCallbackList` 支持三种“被调用方冻结时”的策略。下面的示例选择只保留最新回调：

```java
RemoteCallbackList<IMyCallback> callbacks =
        new RemoteCallbackList.Builder<IMyCallback>(
                RemoteCallbackList.FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT)
                .build();

callbacks.broadcast(callback -> {
    try {
        callback.onStateChanged(latestState);
    } catch (RemoteException ignored) {
        // RemoteCallbackList 会处理死亡的远端接口。
    }
});
```

当远端冻结时，旧状态会被新状态替换；解冻后只发送最后一次 `onStateChanged()`。

可选策略与适用场景：

| 策略 | 行为 | 适合 |
| --- | --- | --- |
| `FROZEN_CALLEE_POLICY_DROP` | 远端冻结时丢弃 | 高频瞬时事件 |
| `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT` | 只保留最新回调 | 音量、亮度、连接状态等状态同步 |
| `FROZEN_CALLEE_POLICY_ENQUEUE_ALL` | 按顺序排队 | 少量且每条都有意义的事件 |

`ENQUEUE_ALL` 也有队列上限。Android 17 默认最多 1000 条；达到上限后会丢掉最旧回调，构建器可用 `setMaxQueueSize()` 显式设置容量。选择这个策略时，仍要写出容量、溢出和恢复方案。

未设置策略的旧构造方式保留兼容行为：照常调用冻结的远端。SDK 36 及以上版本不推荐这种用法。

### 8. Freezer 对应用代码的几个隐蔽影响

#### 8.1 固定频率任务可能在解冻后追赶

冻结期间，`Timer.scheduleAtFixedRate()` 或 `ScheduledThreadPoolExecutor.scheduleAtFixedRate()` 不会执行。解冻后，错过的固定频率任务可能快速连续运行。

如果业务需要“每次完成后再间隔一段时间”，应使用 `scheduleWithFixedDelay()`；如果任务允许由系统安排执行时机，优先考虑 WorkManager。不要在解冻后补跑几十次已经失去意义的轮询。

#### 8.2 GC 与内存回收回调也无法执行

线程全部暂停意味着进程不能主动执行垃圾回收，也不能处理 `onTrimMemory()` 等内存回收提示回调。Android 14 起，Android 框架会调整通知和冻结前准备：

- 可见 Activity 退后台时尽早收到 `TRIM_MEMORY_UI_HIDDEN`。
- 进程进入缓存状态后，运行时可能先执行 GC。
- 其他内存回收提示级别不保证能在冻结进程中执行。

应用不能依赖“等 `onTrimMemory()` 再释放关键资源”来保证冻结前收尾。

#### 8.3 不同广播采用不同的解冻方式

Android 14 起，为减少无意义的解冻：

- 通过代码动态注册的广播可在缓存期间排队，解冻后再投递。
- 在清单中声明的广播会先解冻进程，再投递。

因此，在系统轨迹中看到广播延迟时，不应先归因于 BroadcastQueue 卡死；还要检查目标是否处于缓存或冻结状态，以及接收器采用哪种注册方式。

#### 8.4 TCP 套接字不能当作保活承诺

官方冻结器文档说明：当一个应用的所有进程都被冻结时，系统会终止该应用的活动 TCP 套接字，避免保活包（keepalive）唤醒基带。需要长期可靠传递的业务应使用 Firebase Cloud Messaging（FCM）、JobScheduler、WorkManager 或符合其语义的系统设施，不能依赖缓存进程维持套接字连接。

### 9. 退出归因：区分公开原因与内部子原因

`ApplicationExitInfo` 从 API 30 开始提供，`REASON_FREEZER` 从 API 33 起加入公开 SDK。下面的代码在应用下次启动时查询最近 20 条退出记录，并筛选冻结器导致的退出：

```java
ActivityManager am = context.getSystemService(ActivityManager.class);
List<ApplicationExitInfo> exits =
        am.getHistoricalProcessExitReasons(null, 0, 20);

for (ApplicationExitInfo info : exits) {
    if (Build.VERSION.SDK_INT >= 33
            && info.getReason() == ApplicationExitInfo.REASON_FREEZER) {
        Log.w(TAG, "Previous process was killed by freezer: "
                + info.getDescription());
    }
}
```

命中时，日志会记录系统提供的退出描述。Android 17 源码中的内部子原因包括：

| 子原因 | 含义 |
| --- | --- |
| `SUBREASON_FREEZER_BINDER_TRANSACTION` | 冻结期间收到同步 Binder 事务 |
| `SUBREASON_FREEZER_BINDER_IOCTL` | 冻结、解冻 Binder 或查询状态失败 |
| `SUBREASON_FREEZER_BINDER_ASYNC_FULL` | 冻结期间异步 Binder 缓冲区接近耗尽 |

这些子原因与 `getSubReason()` 都是隐藏 API，普通应用不能把它们当成公开诊断接口。平台或设备厂商调试可从 `dumpsys`、`system_server` 日志与源码获得更细的信息；应用侧应以公开原因、描述、自己的业务状态和时间线为准。

API 30～32 没有公开 `REASON_FREEZER` 常量。不要硬编码数值 `14` 跨版本猜测；这会混淆“当时平台是否记录这种原因”与“当前 SDK 中的常量值”。

### 10. 用四层证据诊断，避免根据缓存状态直接下结论

#### 10.1 配置与 Android 框架状态

下面三条命令依次查看冻结器开关、CachedAppOptimizer 配置，以及进程重要性与冻结资格：

```bash
# 当前设备是否请求启用 cached apps freezer
adb shell device_config get activity_manager_native_boot use_freezer

# Android 17 的 CachedAppOptimizer 配置与统计
adb shell dumpsys activity cao

# 进程状态、adj、capability 与 LRU 信息
adb shell dumpsys activity processes
```

重点记录：

- `use_freezer`
- `freeze_debounce_timeout`
- `freezer_cutoff_adj`
- 进程状态与 `oom_adj`
- `CPU_TIME` 与 `IMPLICIT_CPU_TIME` 执行资格
- 待冻结状态与实际冻结状态

#### 10.2 shell 控制实验

Android 17 的 ActivityManager shell 提供以下查询、冻结和解冻命令：

```bash
adb shell cmd activity isfrozen <PROCESS_OR_PID>
adb shell cmd activity freeze <PROCESS_OR_PID>
adb shell cmd activity unfreeze <PROCESS_OR_PID>
```

`--sticky` 会让强制状态保持到进程死亡，或下一次方向相反的 shell 操作为止，只应用于隔离的测试进程。实验结束必须解冻，不能拿线上关键进程做同步 Binder 探测。

#### 10.3 cgroup 与事件日志

下面的命令用于定位进程所属的 cgroup、查找冻结状态文件、读取冻结事件和历史退出原因：

```bash
# 先找 PID 属于哪个 cgroup
adb shell cat /proc/<PID>/cgroup

# 设备路径可能不同；user build 也可能限制读取
adb shell find /sys/fs/cgroup \
  \( -name cgroup.freeze -o -name cgroup.events \)

# framework 冻结与解冻事件
adb logcat -b events -v threadtime | grep -E 'am_freeze|am_unfreeze'

# 历史退出原因
adb shell dumpsys activity exit-info <PACKAGE>
```

只看到 `cgroup.freeze=1` 还不够；还要确认对应 `cgroup.events` 的 `frozen=1`，并核对该 cgroup 确实包含目标 PID。

#### 10.4 Perfetto 时间线

Android 17 的 `CachedAppOptimizer` 会在 ActivityManager 系统轨迹中写入一条名为 `Freezer` 的轨道：

```text
Freeze <process>:<pid> -1
Unfreeze <process>:<pid> <reason>
Reschedule freeze <process>:<pid> timeout=<...>, reason=<...>
```

分析顺序：

1. 用 `am_freeze` 或 `Freezer` 瞬时事件定位冻结窗口。
2. 检查目标线程在该窗口内是否还有运行中的轨迹区段。
3. 若出现 `Reschedule freeze`，核对尚未完成或新出现的待处理 Binder 事务。
4. 若进程消失，核对 `exit-info`、Binder 调用端和 `am_kill`。
5. 若解冻后 CPU 使用突增，检查积压的 `oneway` 事务、广播和固定频率任务。

Perfetto 没有采集 ActivityManager 或线程调度数据时，“没看到事件”不能证明冻结器没有运行。

### 11. 一个可复现的 Binder Freezer 实验

准备两个独立进程：

- 进程 A 提供一个同步方法和一个 `oneway` 方法。
- 进程 B 绑定 A，拿到 Binder 代理。

实验分三轮。

#### 第一轮：正常绑定

保持绑定关系并调用同步方法。A 的重要性会被 B 的绑定提升，通常不应进入缓存进程冻结状态。应先证明基础 IPC 正常，再分析冻结行为。

#### 第二轮：解绑后误用旧代理

1. B 调用 `unbindService()`，但故意保留旧代理。
2. 等 A 进入缓存状态，或在测试环境中使用 `cmd activity freeze`。
3. B 再发同步调用。

预期验证点包括：

- Binder 驱动返回冻结回复。
- B 收到 `RemoteException` 或 Binder 远端死亡通知。
- A 的退出记录为 `REASON_FREEZER`。

#### 第三轮：oneway 积压

向冻结的 A 发送有限数量、带序号的 `oneway` 事件，然后解冻：

- 确认事件是否在解冻后按同一 Binder 对象内的 `oneway` 顺序到达。
- 观察事件是否已经过期。
- 观察解冻后的 CPU 使用是否突增。

不要用无限循环耗尽 Binder 缓冲区作为默认验证手段。需要验证溢出时，应在隔离设备上设置明确上限，并保存系统轨迹、事件日志和退出信息。

### 12. 复核清单

1. 确认设备的 `use_freezer`、内核支持和 cgroup v2 布局。
2. 同时记录进程状态、`oom_adj`、`CPU_TIME` 执行资格与冻结阈值。
3. 区分等待冻结、已经请求冻结和 `cgroup.events frozen=1`。
4. 检查 Binder 冻结是否先于 cgroup 冻结。
5. 同步调用命中冻结目标时，找到调用端、旧代理生命周期和退出原因。
6. 为 `oneway` 回调写清丢弃、只留最新、全量排队策略及容量上限。
7. API 36 及以上版本优先使用 `IBinder` 冻结回调或 `RemoteCallbackList` 策略。
8. 检查固定频率任务、广播与 `oneway` 是否在解冻后造成 CPU 使用突增。
9. 不把冻结本身写成内存回收；单独验证 GC、内存压缩、ZRAM 和 LMK。
10. 用 Perfetto、事件日志、cgroup 和退出信息四条时间线交叉证明结论。
11. 区分公开的 `REASON_FREEZER` 与隐藏的内部子原因。
12. 当前源码统一引用 `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6`。


## 版本与实现边界

| 版本 | 已确认变化 | 工程含义 |
| --- | --- | --- |
| Android 11（API 30） | AOSP 支持 Cached Apps Freezer；`ApplicationExitInfo` 公开 | 设备是否启用仍取决于内核与配置 |
| Android 13（API 33） | 公开 `ApplicationExitInfo.REASON_FREEZER` | 应用可把冻结器终止与 LMK、ANR 分开统计 |
| Android 14（API 34） | 进入缓存状态后默认等待 10 秒再冻结；生命周期事件立即解冻；动态注册广播可排队；冻结前后配合 GC、压缩等操作 | 冻结器从单个开关扩展为更完整的缓存进程策略 |
| Android 16（API 36） | 公开 `IBinder` 冻结状态回调；`RemoteCallbackList` 增加远端冻结策略 | 回调服务可以按“丢弃、只留最新、全部排队”表达积压处理方式 |
| Android 17（API 37） | 当前 `OomAdjuster` 以显式、隐式 `CPU_TIME` 执行资格统一决定能否冻结；Binder 监控与冻结重试继续完善 | 框架源码以 `android-17.0.0_r1` 为准，内核源码以 `android17-6.18-2026-06_r6` 为准 |

版本演进可以保留，但描述当前行为时，不能继续用 Android 15/16 的旧文件路径代替 Android 17。特别是 `shouldNotFreeze()`、冻结阈值和 Binder 错误上报，已经出现足以影响结论的结构变化。


## 常见误区

### “缓存进程一定被冻结”

不成立。设备可能没有启用冻结器，进程可能仍持有 CPU 执行资格，也可能处于防抖等待、Binder 重试或实现级保护中。

### “被冻结就等于释放内存”

不成立。冻结器的直接作用是停止 CPU 执行；进程仍占用地址空间和物理内存。GC、内存压缩、ZRAM 回写与 LMK 是另外的动作。

### “同步调用只会等到对方解冻”

不成立。Android 会拒绝发往冻结远端的同步 Binder 事务，并终止被冻结的接收进程，避免调用线程无限等待。

### “oneway 对冻结进程绝对安全”

不成立。它会积压并占用 Binder 缓冲区，解冻后还可能集中处理过期事件；缓冲区压力过高时，目标进程会被终止。

### “观察冻结回调就能统计冻结次数”

不成立。状态事件允许合并，API 只承诺最新状态。

### “厂商的‘冻结’都等于 AOSP Cached Apps Freezer”

不成立。必须用 ActivityManager 事件、cgroup 状态、Binder 冻结退出原因和厂商实现证据进行区分。


## 参考资料

- [Android 17 `IPCThreadState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/IPCThreadState.cpp)
- [Android 17 `ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [Android 17 `IPCThreadState.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/include/binder/IPCThreadState.h)
- [Android 17 `ProcessState.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/include/binder/ProcessState.h)
- [Android 17 `IBinder.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/include/binder/IBinder.h)
- [Android 17 Java `Binder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Binder.java)
- [Android 17 kernel `binder.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [Android 17 kernel `binder_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c)
- [Android 17 kernel Binder UAPI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/android/binder.h)
- [Perfetto SQL 标准库：`android.binder`](https://perfetto.dev/docs/analysis/stdlib-docs#android-binder)

- [AOSP：Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [AOSP：Handle cached and frozen apps](https://source.android.com/docs/core/architecture/ipc/binder-freezer)
- [Android API：ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android API diff：API 33 新增 REASON_FREEZER](https://developer.android.com/sdk/api_diff/33/changes/android.app.ApplicationExitInfo)
- [Android API：IBinder](https://developer.android.com/reference/android/os/IBinder)
- [Android API：RemoteCallbackList](https://developer.android.com/reference/android/os/RemoteCallbackList)
- [Linux Kernel：Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [AOSP：OomAdjuster.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/psc/OomAdjuster.java)
- [AOSP：ActivityManagerConstants.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java)
- [AOSP：ActivityManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP：CachedAppOptimizer.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP：config_defaultFreezerDebounceTimeout（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)
- [AOSP：IBinder.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/IBinder.java)
- [AOSP：RemoteCallbackList.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/RemoteCallbackList.java)
- [AOSP：ApplicationExitInfo.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [ACK：Binder driver（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [ACK：Binder UAPI（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/android/binder.h)
- [ACK：cgroup freezer（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/cgroup/freezer.c)
