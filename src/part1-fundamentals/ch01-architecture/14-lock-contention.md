---
title: 锁竞争与同步性能分析
chapter: '1.14'
section: '1.14'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Perfetto official documentation
confidence: high
sources:
  - type: aosp
    path: "art/runtime/monitor.cc @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/lock_word.h @ android-17.0.0_r1"
  - type: aosp
    path: "bionic/libc/bionic/pthread_mutex.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java @ android-17.0.0_r1"
  - type: kernel
    path: "kernel/common/drivers/android/binder.c @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/Documentation/locking/rt-mutex.rst @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/Documentation/locking/pi-futex.rst @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/common/kernel/futex/pi.c @ android17-6.18-2026-06_r6"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#androidbinder"
  - type: official
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
tags:
  - android
  - lock-contention
  - monitor
  - mutex
  - futex
  - priority-inversion
  - binder
  - perfetto
related_chapters:
  - '1.4'
  - '1.5'
  - '1.13'
  - '2.4'
  - '2.5'
  - '7.1'
  - '9.1'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
---

# 1.14 锁竞争与同步性能分析

线程显示为等待（Waiting）或休眠（Sleeping），只能证明它当时没有在 CPU 上执行，不能直接证明发生了锁竞争。它可能在等待 Java 监视器锁、原生互斥锁（native mutex）、条件变量、Binder 回复、I/O 或定时器，也可能只是 Looper 正常阻塞在 `epoll_wait()`，等待新事件。

诊断锁问题时，先回答四个问题，不要从猜测“哪种锁更快”开始：

1. **谁在等**：主线程、RenderThread、Binder 工作线程，还是普通后台线程？
2. **等什么**：Java 监视器锁、原生同步原语、Binder 回复，还是正常事件？
3. **谁能让它继续**：实际持锁线程或服务端线程是谁？
4. **这个线程为什么没有及时推进**：正在运行、排队等待 CPU、阻塞在另一把锁，还是执行 I/O？

这四个答案拼起来，才是一条可修复的等待链。

## 1. 先把几类“等”分开

Android 性能轨迹中，下面五类等待最容易混淆。

| 类型 | 常见入口 | 主要实现 | 首要证据 |
| --- | --- | --- | --- |
| Java 监视器锁 | `synchronized`、`Object.wait()` | ART Monitor / LockWord | `android_monitor_contention`、等待者与持锁者的方法 |
| Java 并发包 | `ReentrantLock`、`Condition`、`LockSupport.park()` | 抽象队列同步器（AQS）、线程挂起/唤醒、原生等待 | Java 调用栈、线程状态、相关业务埋点 |
| 原生锁 | `pthread_mutex`、`std::mutex`、条件变量 | bionic + futex | 原生调用栈、`blocked_function`、锁埋点 |
| Binder IPC | 同步 AIDL、服务端线程池 | libbinder + Binder 驱动 | Binder 事务/回复、调用端/服务端线程状态 |
| Looper 等待 | `MessageQueue.next()` | Java 队列 + 原生 Looper + epoll | 是否有到期消息、`nativePollOnce()`、MessageQueue 锁竞争 |

它们都可能在内核线程状态里表现为睡眠，但优化方式完全不同。

- Java 监视器锁要找到持有同一对象锁的线程。
- `ReentrantLock` 不属于 ART Monitor，不能指望 `android_monitor_contention` 自动给出持锁者。
- 原生 `futex_wait` 只说明线程进入了 futex 的内核等待路径，无法据此确认它对应互斥锁或启用了优先级继承。
- 同步 Binder 调用的调用端等待服务端回复；服务端内部可能又阻塞在 Java 或原生锁上。
- 空闲 Looper 睡在原生轮询中属于正常行为，无需消除。

## 2. ART Monitor：`synchronized` 在 Android 17 中怎样工作

Java 字节码使用 `monitorenter` 和 `monitorexit` 表达 `synchronized`。ART 在对象头的 32 位 LockWord（锁状态字）中记录轻量锁状态，必要时再关联完整的 `Monitor` 对象。

`art/runtime/lock_word.h` 在 `android-17.0.0_r1` 中定义了这些状态：

```cpp
enum LockState {
  kUnlocked,
  kThinLocked,
  kFatLocked,
  kHashCode,
  kForwardingAddress,
};
```

这些枚举说明 LockWord 还要容纳对象身份哈希值和垃圾回收所用的转发地址。分析 `synchronized` 时，不能把对象头始终解释成持锁线程 ID 和重入计数。

### 2.1 无竞争路径：轻量锁

对象未加锁时，ART 可以把当前线程用于 Monitor 的线程 ID 和重入计数编码进 LockWord。线程通过原子更新取得轻量锁（thin lock）；同一线程再次进入同一把锁时，只增加重入计数。

轻量锁的优势是，不必为每个使用过 `synchronized` 的对象都分配完整 Monitor。没有竞争时，这条路径很短，不会让线程休眠，也不会触发内核调度切换。

“无竞争的 `synchronized` 开销较小”，不表示任何 `synchronized` 都只执行一次比较并交换（CAS）。对象可能已经膨胀为重量级 Monitor，可能带有身份哈希值（identity hash code），也可能发生重入和其他运行时状态变化。性能结论要结合实际对象和竞争形态。

### 2.2 竞争、`wait()` 与身份哈希：Monitor 膨胀

`art/runtime/monitor.cc` 的源码注释列出需要完整 Monitor 的三类典型情况：

- 出现真实竞争。
- 在对象上调用 `wait()`。
- 一个需要加锁的对象同时带有身份哈希值。

竞争线程遇到已被其他线程持有的轻量锁时，ART 会与持锁线程协调，并尝试把锁膨胀为重量级 Monitor。重量级 Monitor 会记录完整的持锁者、等待者、条件等待和诊断信息。

`Object.wait()` 的语义也不能简化成“睡一会”：

1. 调用线程必须已经持有该对象的监视器锁。
2. `wait()` 把线程放入等待集合，并释放监视器锁。
3. `notify()` / `notifyAll()`、中断或超时使它具备继续条件。
4. `wait()` 返回前还必须重新取得同一个监视器锁。

因此，被唤醒不等于马上执行。线程可能从“等通知”转成“等重新拿锁”。

### 2.3 `kLongWaitMs` 是日志阈值，不是统一的 Perfetto 阈值

Android 17 源码定义：

```cpp
static constexpr uint64_t kDebugThresholdFudgeFactor =
        kIsDebugBuild ? 10 : 1;
static constexpr uint64_t kLongWaitMs =
        100 * kDebugThresholdFudgeFactor;
```

也就是发布（release）构建为 100ms，调试（debug）构建为 1000ms。这个常量服务于 ART 的长时间竞争告警；是否记录日志，还会受采样和持锁者方法能否解析等条件影响。

它不能用来推导以下结论：

- “小于 100ms 的锁竞争不会进 Perfetto。”
- “没有长等待日志就没有锁问题。”
- “100ms 是 Android 所有锁的统一严重阈值。”

一帧在 60Hz 下只有约 16.7ms，几毫秒的主线程锁等待已经可能造成掉帧，远不到 ART 长等待日志的量级。

## 3. Futex：用户态快路径与内核慢路径

futex（fast userspace mutex）是让用户态原子状态与内核等待队列协作的基础机制，本身并不是某一种具体的 C++ 锁。没有竞争时通常只操作用户态内存；需要让线程休眠或唤醒时，才进入内核。

普通互斥锁（mutex）的典型流程如下：

```text
尝试用户态原子加锁
  ├─ 成功：直接进入临界区
  └─ 失败：标记存在竞争，通过 futex 进入内核等待

解锁
  ├─ 没有 waiter：用户态完成
  └─ 存在 waiter：通过 futex 唤醒等待线程
```

`bionic/libc/bionic/pthread_mutex.cpp` 中未启用优先级继承（PI）的互斥锁，在发生竞争时调用 `__futex_wait_ex()`，释放有等待者的锁时调用 `__futex_wake_ex()`。没有竞争时，不需要每次都进入内核。

这也是为什么 `blocked_function` 里看到 `futex_*` 仍然不能直接下结论：

- 它可能来自 `pthread_mutex`；
- 可能来自条件变量；
- 可能来自 ART 或其他运行时内部同步；
- 可能是 Java 并发包最终触发的线程挂起（park）；
- 只能证明线程在某个 futex 等待点休眠，不能单凭函数名还原锁对象和持锁者。

要定位原生锁，通常还需要原生调用栈、业务锁埋点和同进程线程状态，或者在可复现环境中为该锁增加 Trace 区段。

## 4. 优先级反转与 PI-futex

优先级反转的经典链条是：

```text
低优先级线程 L：持有锁
中优先级线程 M：持续占用 CPU
高优先级线程 H：等待 L 的锁

结果：H 的进度被 M 间接拖慢
```

即使 L 的临界区只执行 1ms，如果 L 长时间得不到 CPU，H 实际经历的等待时间也可能远大于 1ms。

### 4.1 优先级继承的作用

ACK `android17-6.18-2026-06_r6` 的实时互斥锁（rt-mutex）文档描述了优先级继承（Priority Inheritance，PI）：

- 高优先级等待者阻塞在 rt-mutex 上时，低优先级持锁者临时继承更高优先级；
- 持锁者释放锁后撤销这次提升；
- 持锁者又阻塞在另一把 rt-mutex 上时，优先级提升可以沿依赖链传播；
- 等待者按优先级组织，同优先级使用先进先出（FIFO）顺序。

PI 缩短的是“高优先级线程被低优先级持锁者挡住，而持锁者又得不到 CPU”的时间。它无法缩短持锁者在临界区内执行的 I/O、长计算或同步 Binder 调用。

### 4.2 Android 17 bionic 怎样选择 PI 互斥锁

bionic 通过下面的属性显式启用优先级继承：

```c
pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
pthread_mutex_init(&mutex, &attr);
```

只有互斥锁属性显式选择 `PTHREAD_PRIO_INHERIT`，bionic 才会调用 `__futex_pi_lock_ex()` / `__futex_pi_unlock()`，由内核 PI-futex 和 rt-mutex 提升持锁者优先级。普通互斥锁仍走普通 futex 路径。

所以：

- “Android 内核支持 PI-futex”只说明具备这项能力；
- 判断“这把锁启用了 PI”，必须检查它的初始化属性；
- 某线程停在 `futex_wait`，不能证明该锁走的是 PI 路径。

PI 不能替代合理的锁设计。临界区过大、锁顺序混乱、持锁执行 I/O 等问题，仍应从设计上修复。

## 5. Binder 等待与 Java 锁等待是两条不同路径

同步 Binder 调用跨越调用端（client）、Binder 驱动和服务端（server）：

```text
Client thread
  └─ binder transaction
      └─ Binder driver 选择/唤醒 server thread
          └─ Server Binder thread 执行服务代码
              └─ binder reply
                  └─ Client 继续执行
```

调用端等待回复时，并没有持有一把所谓的“Binder Java 监视器锁”。驱动使用自己的锁和等待队列管理事务、线程与工作项；服务端业务代码则可能再次遇到 Java 监视器锁或原生互斥锁。

一次同步 Binder 延迟可以拆成：

```text
总墙上时间
= client 入驱动与排队
+ server thread 获得运行机会
+ server 业务执行
+ server 内部锁 / I/O / 嵌套 Binder 等待
+ reply 返回与 client 再次被调度
```

只看到调用端休眠在 Binder 相关内核函数上，无法判断哪一项耗时占主导。

### 5.1 Binder 有自己的优先级传播

`drivers/android/binder.c` 在当前 ACK tag 中包含：

- `binder_select_thread_ilocked()`：为进程中的工作选择等待线程；
- `binder_wakeup_thread_ilocked()`：唤醒具体线程，或通知进程需要增加线程；
- `binder_transaction_priority()`：根据事务和 Binder 节点（binder node）的限制，设置服务端处理线程的优先级。

这是 Binder 自身的事务调度机制，不等同于 `PTHREAD_PRIO_INHERIT`，也不会自动提升“服务端线程正在等待的某个 Java 监视器锁持有者”。如果 Binder 工作线程进入服务代码后又阻塞在业务锁上，仍要沿 Java 或原生锁的持有关系继续排查。

### 5.2 默认 15 不代表进程里固定只有 15 条 Binder 线程

Android 17 的 `ProcessState.cpp` 定义：

```cpp
#define DEFAULT_MAX_BINDER_THREADS 15
```

初始化 Binder 驱动时，libbinder 通过 `BINDER_SET_MAX_THREADS` 把这个默认最大值设为 15。与此同时，`startThreadPool()` 会调用 `spawnPooledThread(true)`，主动启动一条主线程池线程（main pooled thread）。

因此应该这样读：

- 15 是 libbinder 传给驱动的默认“可按需请求启动的线程”上限；
- 主动启动的主线程池线程要单独计入线程总数；
- 业务线程也可以进入 Binder 调用上下文；
- 服务可以在启动线程池前通过 API 配置不同上限。

所以，把 Binder 线程池概括成“固定 15 条”或“固定 16 条”都会误导性能分析。线程数只是容量的一部分；一个工作线程长时间持锁或执行缓慢 I/O，仍可能让其他事务排队。

## 6. `system_server`：Binder 慢经常只是表象

应用主线程调用 AMS、WMS 或 PMS 后长时间等待回复，常见根因位于服务端，而非 Binder 驱动本身：

- Binder 工作线程等待 `system_server` 的全局对象锁；
- 持锁线程在锁内执行长计算或磁盘 I/O；
- 持锁线程在锁内发起另一个同步 Binder 调用；
- 多把系统锁形成长等待链；
- Binder 工作线程接近饱和，新事务迟迟没有线程处理。

分析时，应从调用端事务跟到服务端回复，再检查服务端线程的状态；如果它在等锁，就继续找持锁线程，不能停留在“Binder 调用耗时”这个表面结论。

### 6.1 Android 17 AMS 的 `mGlobalLock` 与 `mProcLock`

`ActivityManagerService.java` 当前源码明确给出：

```java
final ActivityManagerGlobalLock mGlobalLock = ActivityManagerService.this;

private static final boolean ENABLE_PROC_LOCK = true;

final ActivityManagerGlobalLock mProcLock = ENABLE_PROC_LOCK
        ? new ActivityManagerProcLock() : mGlobalLock;
```

源码注释规定了锁的获取顺序：先取得 `mGlobalLock`，再取得 `mProcLock`；不能在只持有 `mProcLock` 时反向获取 `mGlobalLock`，否则可能形成死锁。

`@CompositeRWLock({"mService", "mProcLock"})` 表达的是供静态分析和代码审查使用的组合锁契约，不会在运行时创建新的读写锁对象：相关状态的读取可由两把锁中的任意一把保护，写入通常要求同时持有两把锁。方法后缀也能提示调用者需要持有哪些锁：

- `LOSP`：通常表示持有列出的任意一把锁；
- `LSP`：通常表示同时持有服务全局锁和进程锁。

例如 Android 17 的 `OomAdjuster`：

```java
@GuardedBy("mServiceLock")
void updateOomAdjLocked(@OomAdjReason int oomAdjReason) {
    synchronized (mProcLock) {
        updateOomAdjLSP(oomAdjReason);
    }
}
```

这里调用者已经持有 `mServiceLock`，随后再进入 `mProcLock`，符合从全局锁到进程锁的顺序。`ProcessList.mLruProcesses` 也标注为由组合锁保护。

这些源码能证明哪些状态由哪些锁保护，以及锁的获取顺序，却不能单独证明某个固定的性能提升比例。锁持有时间必须来自具体设备的性能轨迹；没有可定位的一手基准时，不应写“从 25ms 降到 8ms”或“吞吐提升 3 倍”。

## 7. MessageQueue：Android 17 的一个针对性去锁案例

旧 MessageQueue 使用同一个 `synchronized (this)` 保护有序链表，生产者入队、Looper 取消息和移除操作都会竞争这把监视器锁。

对于运行在 Android 17 且 `targetSdkVersion >= 37` 的应用，DeliQueue 默认启用。它让生产者通过比较并交换（CAS）把消息提交到 Treiber 无锁栈，再由 Looper 独占两个最小堆，分别对同步和异步消息排序。核心消息路径不再依赖旧的单一全局监视器锁，但 IdleHandler 和文件描述符记录仍有各自的小锁。

Google 公布的内部测试轨迹中，应用主线程花在锁竞争上的时间下降 15%。这个数字只描述其样本中的 MessageQueue 改造效果，不能外推到 AMS、Binder、原生互斥锁或业务锁。

DeliQueue 展示了一种有边界的无锁设计：

- 多个生产者共享的提交路径无锁；
- 排序工作由作为唯一消费者的 Looper 完成；
- 取消消息时先做逻辑删除标记，实际结构清理由 Looper 完成；
- 同步屏障、异步消息和原生轮询的语义继续保留。

它不适合作为“把所有锁换成 CAS”的通用模板。无锁结构仍会产生 CAS 重试、多个 CPU 核反复争用同一缓存行、内存分配和延迟清理等成本。

## 8. Perfetto：先找证据，再解释原因

### 8.1 Java 监视器锁

当前 Perfetto 标准库（stdlib）的模块名是 `android.monitor_contention`，查询表名是 `android_monitor_contention`。下面的 SQL 列出 `system_server` 中耗时最长的 30 次 Java 监视器锁竞争：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  process_name,
  blocked_thread_name AS waiter,
  blocking_thread_name AS owner,
  short_blocked_method AS waiter_method,
  short_blocking_method AS owner_method,
  lock_name,
  dur / 1e6 AS wait_ms
FROM android_monitor_contention
WHERE process_name = 'system_server'
ORDER BY dur DESC
LIMIT 30;
```

查询结果能给出等待线程（waiter）、持锁线程（owner）、双方方法、源码位置、是否为主线程、锁名和等待时长。`android_monitor_contention_chain` 还能表达多段锁竞争之间的依赖关系；配套的线程状态表可以继续检查持锁者在锁内是正在运行（Running）、可运行但等待 CPU（Runnable），还是又阻塞在其他内核函数中。

注意两个边界：

- 表中没有记录，不等于设备上完全没有竞争；性能轨迹配置、运行时采样和符号解析都会影响数据完整性；
- 这张表针对 ART Java Monitor，不覆盖所有 `ReentrantLock` 和原生互斥锁。

### 8.2 原生 futex 等待

没有专门的锁埋点时，可以先从 `thread_state.blocked_function` 查找耗时较长的 futex 等待。下面的 SQL 列出最长的 50 个候选区间：

```sql
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  ts.ts,
  ts.dur / 1e6 AS blocked_ms,
  ts.state,
  ts.blocked_function
FROM thread_state ts
JOIN thread t ON t.utid = ts.utid
LEFT JOIN process p ON p.upid = t.upid
WHERE ts.blocked_function GLOB '*futex*'
ORDER BY ts.dur DESC
LIMIT 50;
```

这一步只负责找候选。随后还要结合原生调用栈或源码，确认它对应互斥锁、条件变量（condvar）还是其他等待，并寻找真正能使其继续的线程。不能只根据 `futex_wait` 这个函数名，就断定发生了 Java 锁竞争。

### 8.3 Binder 调用端与服务端

Perfetto 的 `android.binder` 模块可以把事务与回复关联到调用端和服务端。下面的 SQL 按调用端总耗时列出最长的 30 笔同步 Binder 事务：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_process,
  client_thread,
  server_process,
  server_thread,
  interface,
  method_name,
  is_sync,
  client_dur / 1e6 AS client_ms,
  server_dur / 1e6 AS server_ms
FROM android_binder_txns
WHERE is_sync
ORDER BY client_dur DESC
LIMIT 30;
```

找到慢事务后，可以再用 `android_sync_binder_thread_state_by_txn` 或 `android_sync_binder_blocked_functions_by_txn` 分解调用端与服务端的线程状态。若服务端处理区间叠加 Java 监视器锁竞争，就继续查询 `android_monitor_contention` 给出的持锁者。

“调用端时间长、服务端时间短”可能意味着事务排队、线程调度或回复返回延迟；“服务端时间长”也不等同于一直执行 CPU 计算，服务端可能大部分时间都在等待锁、I/O 或嵌套 Binder 调用。

## 9. 三个常见现场怎样推理

### 现场一：主线程出现 `monitor contention with ...`

1. 在 `android_monitor_contention` 中找到等待者方法、持锁线程和持锁者方法；
2. 查看持锁者在等待区间内的 `thread_state`；
3. 如果持锁者处于 Runnable 状态却长时间没有运行，检查 CPU 压力与优先级反转；
4. 如果持锁者又等待另一把锁或 Binder，继续沿依赖链排查；
5. 回源码确认临界区，检查能否移出 I/O、IPC 或长计算。

### 现场二：主线程睡在同步 Binder 调用

1. 用 `android_binder_txns` 找到服务端进程、线程和方法；
2. 比较调用端与服务端区间，确认时间主要花在哪一端；
3. 服务端工作线程若等待 Java Monitor，用竞争表找持锁者；
4. 服务端工作线程若停在原生 futex，结合原生调用栈找具体同步对象；
5. 多个事务都在排队时，检查工作线程是否饱和，以及某个长事务是否占用线程过久。

### 现场三：线程停在 `futex_wait`

1. 先确认 Java 调用栈来自 ART Monitor、AQS/线程挂起，还是 JNI/原生代码；
2. 检查是否有对应的 `android_monitor_contention` 事件；
3. 没有 Java Monitor 证据时，按原生锁或条件等待调查；
4. 找到锁的初始化代码，确认是否为 PI 互斥锁，不能根据函数名猜测；
5. 如果这是正常的条件变量等待，就继续查“为什么条件迟迟没有满足”，无需优化 futex 本身。

## 10. 锁优化的工程顺序

### 10.1 先缩短临界区

最常见的有效改动，是把不需要维持共享状态一致性的工作移出锁：

- 日志格式化和大对象构建；
- 磁盘、网络和数据库 I/O；
- 同步 Binder 调用；
- 可以先在锁内复制输入、锁外计算、再在锁内提交结果的长计算；
- 不需要共享状态保护的回调。

把代码移出锁前，要重新确认临界区保护的不变量，也就是共享状态始终必须满足的约束。盲目缩小范围可能产生“先检查、后操作”之间状态已被其他线程改变的竞态（check-then-act race），性能改善不能以破坏正确性为代价。

### 10.2 再减少共享状态

- 用线程封闭（只允许一个线程访问状态）或消息传递代替共享可变对象；
- 把一把全局锁拆成按对象、按分片（shard）或按子系统的锁；
- 读多写少时考虑不可变快照、写时复制（copy-on-write）或读写分离；
- 高频计数器考虑分片，减少多个 CPU 写入同一缓存行。

拆锁会引入锁顺序和跨锁一致性问题。应先写清哪些字段共同构成一个必须原子维护的不变量，再决定能否拆分。

### 10.3 明确锁顺序

跨多把锁时，项目应定义全局顺序，并在代码审查中阻止反向获取。Android 17 AMS 对 `mGlobalLock` → `mProcLock` 的注释就是这种契约。

超时只能限制单次等待时间，不能修复潜在死锁；`tryLock()` 获取失败后的状态恢复同样需要正确设计。

### 10.4 最终才比较锁类型或无锁结构

选择 `synchronized`、`ReentrantLock`、读写锁或无锁结构，应由需求决定：

- 是否需要可中断的锁获取或超时；
- 是否需要多个条件队列（`Condition`）；
- 是否允许公平锁按等待顺序分配锁所带来的吞吐成本；
- 读写比例和临界区大小；
- 竞争线程数、优先级和 CPU 核心布局；
- 失败重试与内存回收成本是否可控。

微基准要覆盖真实的竞争形态。只测试单线程获取/释放锁（acquire/release），无法预测主线程与多个后台生产者同时竞争时，高百分位请求的尾延迟。

### 10.5 增加 Binder 线程数不是首选修复手段

增加工作线程可能缓解排队，也可能让更多线程同时争用同一把全局锁，增加内存和调度压力。应先找最长事务、持锁 I/O、嵌套同步 IPC 和锁依赖链，再判断线程池容量是否不足。

## 11. 版本边界

| 版本 | 可确认的同步相关变化 | 阅读方式 |
| --- | --- | --- |
| Android 5.0（API 21） | 应用运行时切换到 ART，Java Monitor 分析以 ART `monitor.cc` / `lock_word.h` 为准 | 不沿用 Dalvik 时代实现细节解释当前系统 |
| Android 9（API 28） | bionic 已提供 `PTHREAD_PRIO_INHERIT` 互斥锁属性接口 | 只说明这项能力可用；具体锁是否启用仍要看初始化 |
| Android 17（API 37） | 当前 bionic 的 PI 互斥锁走 PI-futex；当前 ACK 为 `android17-6.18-2026-06_r6`；DeliQueue 对目标 SDK 37 及以上应用默认启用 | 平台、bionic 与内核源码按本知识库的统一锚点核对 |

Binder 默认线程配置在历史上容易被误传。在当前 Android 17 锚点下，`DEFAULT_MAX_BINDER_THREADS` 为 15，`startThreadPool()` 还会另行启动主线程池线程；这个数值并非进程的固定 Binder 线程总数。

## 12. 常见误区

### “Waiting / Sleeping 就是锁竞争”

不成立。Looper、条件变量、Binder、I/O 和定时器都会让线程睡眠。先找等待对象和唤醒条件。

### “`synchronized` 一定比 `ReentrantLock` 慢”

不成立。它们的功能、运行时路径和竞争行为不同。没有实际工作负载和性能轨迹，单凭锁类型无法判断。

### “看到 `futex_wait` 就找 Java Monitor 的持锁者”

不成立。应先看 `android_monitor_contention` 和调用栈。futex 是底层等待机制，不是 Java Monitor 的专属标志。

### “内核支持 PI，所以 Android 关键锁都有优先级继承”

不成立。bionic 互斥锁必须使用 `PTHREAD_PRIO_INHERIT` 初始化；Binder 的事务优先级传播又是另一套机制。

### “Binder 调用慢就是驱动慢”

只看到 Binder 调用耗时，通常证据还不够。服务端工作线程可能阻塞在业务锁、I/O、CPU 调度或嵌套 IPC 上。应先把调用端与服务端的时间线连起来。

### “无锁一定更快”

不成立。CAS 重试、多个 CPU 核反复争用同一缓存行、垃圾回收（GC）和算法复杂度都可能成为新成本。DeliQueue 的价值来自针对具体队列结构的重构，不能只归结为“无锁”两个字。

## 结论

锁竞争分析要还原完整的等待链。Java Monitor 使用 `android_monitor_contention` 查找等待者与持锁者；原生互斥锁要从 futex 候选回到原生调用栈和初始化代码；Binder 要用事务与回复连起调用端和服务端；MessageQueue 还要区分正常的原生轮询与旧版监视器锁竞争。

找到持锁者后还要继续判断：它正在 CPU 上运行，还是处于 Runnable 状态却没有被调度？它是否阻塞在另一把锁、I/O 或 Binder 上？找到整条等待链中无法推进的节点后，缩短临界区、拆锁、调整线程模型、启用 PI 或采用无锁结构才有明确目标。

## 参考资料

- [AOSP：ART monitor.cc（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc)
- [AOSP：ART lock_word.h（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/lock_word.h)
- [AOSP：bionic pthread_mutex.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_mutex.cpp)
- [AOSP：libbinder ProcessState.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [AOSP：ActivityManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP：ProcessList.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [AOSP：OomAdjuster.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/psc/OomAdjuster.java)
- [AOSP：CombinedDeliMessageQueue/MessageQueue.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java)
- [ACK：Binder driver（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [ACK：rt-mutex 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/locking/rt-mutex.rst)
- [ACK：PI-futex 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/locking/pi-futex.rst)
- [ACK：futex PI 实现（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/futex/pi.c)
- [Perfetto：`android.monitor_contention` stdlib](https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention)
- [Perfetto：`android.binder` stdlib](https://perfetto.dev/docs/analysis/stdlib-docs#androidbinder)
- [Android Developers Blog：Android 17 lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
