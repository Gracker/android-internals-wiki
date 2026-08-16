---
title: "Android 17 Binder 异步事务与排队机制"
chapter: "1.29"
section: "1.29"
status: finalized
applicable_versions: "Android 17 (API 37)"
tags: [binder, ipc, 异步机制, 批处理]
related_chapters: ["1.4", "1.13"]
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: "reviewed"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; kernel/common android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "platform/frameworks/native/libs/binder/IPCThreadState.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/native/libs/binder/ProcessState.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/native/libs/binder/include/binder/IBinder.h (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/core/java/android/os/Binder.java (android-17.0.0_r1)"
  - type: kernel
    path: "kernel/common/drivers/android/binder.c (android17-6.18-2026-06_r6)"
  - type: kernel
    path: "kernel/common/drivers/android/binder_alloc.c (android17-6.18-2026-06_r6)"
  - type: official-docs
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#android-binder"
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/01.30-android17-binder-transaction-queue-optimization.md"
---

# 1.29 Android 17 Binder 异步事务与排队机制

Binder 的 `oneway`（单向）调用经常被概括成“异步、不会阻塞”。这句话只覆盖了调用方不等待业务回复这一层。调用方仍要把事务提交给驱动，驱动仍要为目标进程分配缓冲区，目标 Binder 线程仍要执行服务端代码；缓冲区耗尽、目标死亡或冻结等状态也可能在提交阶段反馈给调用方。

分析 Android 17 Binder 异步机制时，最好把一次调用拆成两个完成点：

1. **提交完成**：驱动已经接收事务，调用方收到 `BR_TRANSACTION_COMPLETE`，或收到冻结、死亡、缓冲区不足等结果。
2. **执行完成**：目标 Binder 线程已经运行服务端方法，相关状态变更也已完成。

同步调用用 `BR_REPLY` 把两个完成点关联起来。`oneway` 调用只观察第一个完成点，服务端执行成功、抛异常或何时完成，都不会通过原事务返回。

## 1. 从 `FLAG_ONEWAY` 到 `IPCThreadState::transact()`

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

### 1.1 `mCallRestriction` 的准确边界

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

### 1.2 服务端异常不会返回给 `oneway` 调用方

Java Binder 服务端执行 `onTransact()` 时，如果 `oneway` 方法抛出 `RemoteException` 或 `RuntimeException`，`Binder.execTransactInternal()` 会记录异常并调用 `onUnhandledException()`，但不会把异常写入回复 Parcel。同步事务才会执行 `reply.writeException(e)`。

调用方在提交成功后，无法通过原 `oneway` 调用知道服务端是否失败。需要确认业务结果时，应设计独立回调、状态查询或事件确认，并明确超时、进程死亡和重复回调的处理方式。

## 2. 驱动如何排队 `oneway` 事务

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

### 2.1 顺序保证到哪里为止

Binder 驱动维护的是同一 node 上的 `oneway` 串行执行。以下情况不能据此推导全局顺序：

- 两个不同 Binder 对象，即使属于同一进程，也可能由不同线程并行处理。
- 同一个业务动作拆到多个 Binder 接口后，接口之间没有统一的 `oneway` 顺序。
- 服务端收到调用后把工作继续投递到其他线程，后续顺序由服务端队列决定。
- 进程冻结、死亡、缓冲区不足或厂商扩展钩子（hook）都可能改变可见时序。

如果协议要求 A 必须先于 B 生效，最好让 A、B 经过同一个串行执行点，或者给消息增加序列号和状态校验，不能只依赖“它们都是 `oneway`”。

### 2.2 调用方优先级不会随 `oneway` 继承

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

## 3. 事务缓冲区与异步配额

### 3.1 约 1 MB 来自用户态请求，4 MB 是内核上限

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

### 3.2 异步配额不是独立内存池

映射建立后，驱动初始化：

```c
alloc->free_async_space = alloc->buffer_size / 2;
```

同步和异步事务使用同一块映射。`oneway` 分配除了受总空闲空间约束，还要通过 `free_async_space` 检查；同步事务不受这项异步配额限制，但仍受总空间和碎片影响。

所以“每个进程可发送一笔接近 1 MB 的事务”不是安全结论。可用空间属于目标进程，并被并发事务、对象偏移表和其他 Binder 工作共同消耗。Java 层会根据事务失败时的上下文推测并报告 `TransactionTooLargeException`，这不是驱动返回的精确字节上限，不能据此反推出固定的单笔限制。

适合 Binder 的数据通常应当小而有界。大图、文件和连续媒体数据更适合文件描述符、共享内存或专门的数据通道；拆成多笔事务时还要处理部分成功和版本一致性。

### 3.3 `oneway` spam 检测只用于压力诊断

这里的 spam 指同一发送进程大量占用目标异步空间的可疑行为。Android 17 驱动只有在异步剩余空间低于总 buffer 的 10% 时，才扫描当前发送进程在目标 `binder_alloc` 上的占用。如果该 PID 已有超过 50 个异步 buffer，或占用大小超过总 buffer 的四分之一，当前 buffer 会被标记为 `oneway_spam_suspect`。

调用方随后收到 `BR_ONEWAY_SPAM_SUSPECT`。libbinder 记录错误和调用栈，再按 `BR_TRANSACTION_COMPLETE` 的语义结束本次提交。

这个机制不按固定时间窗统计调用频率，也不会自动限流。触发时该事务已经获得 buffer；警告用于定位哪个发送进程正在加剧目标的异步空间压力。治理措施仍要由上层完成，例如合并可覆盖的状态更新、限制采样频率、为事件队列设置容量和丢弃策略。

## 4. 目标进程冻结时的同步与 `oneway` 分流

在 `android17-6.18-2026-06_r6` 中，`binder_proc_transaction()` 对冻结目标采用两种处理：

| 调用类型 | 驱动动作 | 调用方结果 |
|---|---|---|
| 同步 | 拒绝入队 | `BR_FROZEN_REPLY`，libbinder 返回 `FROZEN_OBJECT` 或 `FAILED_TRANSACTION` |
| `oneway` | 保留事务并排队 | `BR_TRANSACTION_PENDING_FROZEN`，libbinder 记录警告后以成功提交结束 |

`FROZEN_OBJECT` 是否单独暴露由 `enable_frozen_object_error` 特性控制；未启用时映射为 `FAILED_TRANSACTION`。无论映射成哪个用户态错误，同步事务都没有进入目标队列，解冻后不会自动重放。

`oneway` 事务已经入队，目标解冻后可以继续处理。调用方收到的 `BR_TRANSACTION_PENDING_FROZEN` 是一次即时诊断回执；对应的 `BINDER_WORK_TRANSACTION_PENDING` 在驱动返回该命令时就被释放。目标解冻后不会再补发一个 `BR_TRANSACTION_COMPLETE`。

驱动还会把冻结期间是否收到过同步或异步事务记录在 `sync_recv`、`async_recv` 中。这两个字段采用按位或累积，在查询或解冻流程中提供状态信息，解冻与进程释放时清零。

### 4.1 `TF_UPDATE_TXN` 只替换特定的冻结队列项

`TF_UPDATE_TXN` 适合“旧状态可被新状态覆盖”的 `oneway` 更新，但它不是通用去重，也不是缓冲区溢出后的回收策略。Android 17 驱动只有在以下条件同时满足时才查找旧事务：

1. 新旧事务都带 `TF_ONE_WAY | TF_UPDATE_TXN`。
2. 目标进程处于冻结状态。
3. 同一 node 已有未完成的 `oneway`，新事务将进入 `node->async_todo`。
4. 旧事务与新事务的目标进程、事务码、完整 `flags`、发送 PID、目标 node 指针和 `cookie` 字段都匹配。

命中后，驱动先从 `node->async_todo` 移除旧事务，释放锁，再释放旧 buffer 和事务对象，最终保留新事务。把 buffer 释放移到锁外可以减少临界区工作，但查找旧事务仍是对目标队列的线性扫描。

使用这项标志的前提是消息具有覆盖语义。日志、增量计数、队列操作等不可丢事件不适合被新事务替换。

## 5. `BINDER_WRITE_READ` 如何批量收发命令

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

### 5.1 `flushCommands()` 与 `flushIfNeeded()`

`flushCommands()` 调用 `talkWithDriver(false)`，只写不读。第一次写入可能触发 `processPostWriteDerefs()`，并在 `mOut` 中产生新的 `BC_RELEASE` 或 `BC_DECREFS`；若仍有数据，函数会再写一次。

`flushIfNeeded()` 只在当前线程不属于 Binder 命令循环（looper）、没有正在服务 Binder 事务且未处于递归刷新时强制发送。普通线程可能很久不再进入驱动，积压在其 `mOut` 中的 `BC_FREE_BUFFER` 等命令会长期占用对端资源，因此需要在这些条件下强制发送。

批处理是 libbinder 的常规传输行为，不是调用者可以为某个 AIDL 方法打开的“批量模式”。业务层若要合并多条消息，仍需单独设计批量接口、上限和部分失败语义。

## 6. `oneway` 缩短调用方等待，不减少目标线程池工作

Android 17 libbinder 默认把 `BINDER_SET_MAX_THREADS` 设为 15。这个值是内核最多可请求用户态按需额外创建的 Binder 线程数；这类线程在源码中称为 lazy Binder 线程。它不等于进程内 Binder 线程总数：

- `startThreadPool()` 会主动创建一个主线程池线程。
- 内核在没有可用线程且符合条件时返回 `BR_SPAWN_LOOPER`，用户态再创建额外线程。
- 进程还可以主动调用 `joinThreadPool()`，或让其他线程以轮询模式（polling）参与 Binder 事件处理。
- 线程池启动后，libbinder 禁止缩小已设置的最大 lazy 线程数。

`oneway` 调用方在提交完成后可以继续工作，目标进程仍要占用 Binder 线程执行服务端方法。若服务端在 `oneway` 方法中做磁盘 I/O、长计算或等待其他锁，事务会在 node 队列和目标线程池中累积；此时客户端“很快返回”会掩盖服务端拥塞。

平台或服务端代码应尽快把重任务移交给设有容量上限的工作队列。工作队列还需要优先级、过期和合并策略，否则压力只是从 Binder 线程池转移到另一个队列。

## 7. 优先级继承与嵌套事务

同步 Binder 需要调用方等待结果，驱动因而记录调用线程的优先级，并在目标线程处理事务时，应用经过 node 最低优先级与 `inherit_rt` 约束后的值。回复完成后，驱动恢复目标线程原优先级。

Android 17 的 `binder_transaction_priority()` 用 `set_priority_called` 防止同一事务重复设置优先级。嵌套事务还通过 `BINDER_PRIO_PENDING`、`BINDER_PRIO_SET`、`BINDER_PRIO_ABORT` 协调“正在恢复旧优先级”与“新事务又需要提升优先级”的竞态。

这些状态用于保证恢复顺序，不能直接换算成固定的系统调用节省量或延迟收益。分析实时或音频服务的 Binder 优先级问题时，应同时查看 `binder_transaction`、`binder_set_priority`、`sched_switch` 和目标线程的调度策略。

## 8. 业务确认、超时与进程死亡

### 8.1 回调是另一笔事务

`oneway` 加回调可以表达异步结果，但回调是独立的 Binder 调用，拥有自己的缓冲区、线程池和死亡条件。设计时至少要处理：

- 请求已经提交，但服务端尚未执行。
- 服务端执行时抛异常，没有发送回调。
- 回调发送前任一进程死亡。
- 超时后回调才到达，形成迟到结果。
- 重试产生重复请求或重复回调。

用 `CountDownLatch`、`ConditionVariable` 或协程等待回调时必须设置超时，并且不要在目标 Binder 线程池中等待一个还需要同一线程池处理的回调。没有超时的等待可能永久挂起，但这不是 `oneway` 自动产生的“必死锁”；是否形成死锁取决于等待依赖图和可用执行线程。

### 8.2 死亡通知不是 `oneway` 业务事务

`linkToDeath()` 通过 `BC_REQUEST_DEATH_NOTIFICATION` 注册内核事件。目标 node 释放时，`binder_node_release()` 把 `BINDER_WORK_DEAD_BINDER` 放入每个观察者进程的 `proc->todo`，再唤醒可用 Binder 线程。用户态收到 `BR_DEAD_BINDER` 后用 `BC_DEAD_BINDER_DONE` 确认。

死亡通知（death notification）不占用普通事务 buffer，也不经过 `node->async_todo`。观察者进程若在确认前退出，驱动会在释放流程中清理 `delivered_death` 等未完成工作。它只通知对象所属进程已经死亡，不提供某笔 `oneway` 业务调用的执行结果。

## 9. Perfetto：分别看客户端提交与服务端执行

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

### 9.1 不同问题需要不同证据

| 要回答的问题 | 主要证据 |
|---|---|
| 谁在发送或处理 `oneway` | `android_binder_txns.is_sync = 0`、AIDL 名称、客户端与服务端线程 |
| 服务端为何慢 | 服务端 Binder 时间片、线程状态、锁竞争、CPU 调度、I/O |
| 异步 buffer 是否紧张 | `BR_ONEWAY_SPAM_SUSPECT` 日志、Binder debugfs / binderfs 状态、驱动分配事件 |
| 目标是否被冻结 | freezer / cgroup 状态、Binder 冻结日志、驱动事件；只凭调用失败不够 |
| 一次 `ioctl` 带了多少命令 | 系统调用级轨迹或受控实验；`android_binder_txns` 本身不能还原 BC / BR 批次 |

普通 Perfetto Binder 时间片不一定直接显示 `BR_TRANSACTION_PENDING_FROZEN` 的命令名。把目标进程被冻结、`oneway` 事务提交、客户端警告三项对齐，才能确认该分支；不能只凭一条很短的客户端时间片推断。

## 10. 选择 `oneway` 时的检查表

### 10.1 适合 `oneway` 的条件

- 调用方不需要立即返回值，也不需要知道服务端是否执行成功。
- 消息允许排队，且目标暂时变慢时，已经明确如何限流、合并或丢弃。
- 协议能处理迟到、重复、进程死亡和版本差异。
- 单条数据小而有界，不依赖大 Parcel 搬运批量内容。
- 顺序要求能落在同一 Binder node 或服务端明确的串行队列上。

### 10.2 常见误区

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

## 11. Android 17 版本边界

相关分析以平台源码 `android-17.0.0_r1` 和 Android 通用内核（common kernel）标签 `android17-6.18-2026-06_r6` 为准。`TF_ONE_WAY`、oneway spam、freezer、优先级状态机等机制来自多个历史版本，Android 17 延续并组合了这些能力。描述 Android 17 时应避免把沿用机制写成该版本首发特性。

不同设备还可能存在以下差异：

- `enable_frozen_object_error` 等 aconfig 功能开关的启用状态。
- 厂商对 Binder 扩展钩子（vendor hooks）、线程池上限和服务端工作队列的调整。
- 用户态是否仍使用 AOSP `BINDER_VM_SIZE`，以及内核是否采用同一 Android 通用内核标签。
- 系统轨迹配置是否采集 Binder 驱动、AIDL 名称、调度和 freezer 数据。

遇到设备差异时，应同时确认平台构建版本（build）、内核标签、厂商补丁、功能开关值和系统轨迹配置，不能只按 API 级别推断底层行为。

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
