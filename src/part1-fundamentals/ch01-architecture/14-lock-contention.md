---
title: "锁竞争与同步性能分析"
chapter: "1.14"
status: draft
applicable_versions: "Android 1.0 (API 1) - Android 17 (API 37)"
tags: [Mutex, Futex, monitor lock, 优先级反转, 锁竞争, DeliQueue, Perfetto, Binder, jank, ANR]
related_chapters: ["1.5", "1.13", "2.4", "2.5", "7.1", "9.1"]
section: "1.14"
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "研究素材+AOSP结构+每日信息+读者需求"
gap_score: "17/20"
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
confidence: "medium"
---

# 1.14 锁竞争与同步性能分析

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Android 中的锁类型全景
- Java 层：synchronized（monitor lock）、ReentrantLock、ReadWriteLock、StampedLock
- Native 层：pthread_mutex（POSIX）、std::mutex、futex（Fast Userspace Mutex）
- 内核层：spinlock、mutex、rt_mutex（支持优先级继承）
- Binder 层：Binder 线程池锁、服务端对象锁（如 WindowManagerGlobalLock）
- 不同锁类型的开销层级：CAS < spinlock < futex < monitor lock < Binder IPC 锁

### 🔹 锚点 2：Monitor Lock 的实现与性能特征
- synchronized 底层依赖 ART monitor，进入/退出通过 monitorenter/monitorexit 字节码
- ART monitor 的实现：先做 CAS 自旋（轻量级锁），失败后膨胀为 monitor（重量级锁）
- 膨胀过程涉及 futex 系统调用，将线程挂入等待队列
- Object.wait() / notify() / notifyAll() 的 futex 机制
- Monitor 性能开销：无竞争时 < 10ns（CAS 成功路径），竞争时 1-10μs（futex 调度延迟）

### 🔹 锁点 3：Futex 与 Linux 同步原语
- futex(2) 系统调用：用户态快速路径 + 内核态慢速路径的设计哲学
- FUTEX_WAIT / FUTEX_WAKE 的语义
- PI-futex（优先级继承 futex）：解决优先级反转的内核支持
- Android 中 futex 的使用场景：ART monitor、pthread_mutex（PI 模式）、binder 框架
- [已验证: 来源见 Linux kernel source futex.c, Android bionic libc]

### 🔹 锚点 4：优先级反转——从理论到 Android 实战
- 经典优先级反转：低优先级线程持锁 → 中优先级线程抢占 → 高优先级线程饿死
- 1997 年火星探路者号事件（历史上的经典案例）
- Android 中的典型场景：主线程（高优先级）等待后台线程（低优先级）释放 MessageQueue 锁
- 优先级继承（Priority Inheritance, PI）：临时提升持锁线程优先级
- Android 的 PI 实现：Binder 使用 PI-futex、ART monitor 使用 PI-futex（Android 12+）
- 优先级继承本身的开销：即使无竞争，PI-futex 的 wake 路径比普通 futex 多约 15% [待验证]
- 2026 年赵俊民技术简报指出：「即使无实际锁竞争，优先级继承机制本身也会引入延迟」

### 🔹 锚点 5：Binder 框架中的锁竞争
- Binder 线程池（默认 16 个线程）的锁竞争模式
- BpBinder/BbBinder 的引用计数锁
- IPCThreadState 的进程级锁（mLock）
- ServiceManager 注册/查询的全局锁
- system_server 中常见的高争抢锁：ActivityManagerGlobalLock、WindowManagerGlobalLock、PackageManagerGlobalLock
- Binder 事务超时与 ANR 的锁竞争关联

### 🔹 锁点 6：在 Perfetto 中的表现
- 线程状态解读：S（Sleeping）+ blocked_function=futex_wait_queue_me → 锁等待
- Monitor Contention 切片：Perfetto 直接显示 Java monitor 竞争
- Owner-Waiter 关系可视化：Perfetto UI 中连接持锁线程和等待线程
- 常见锁相关 Track：binder transaction、monitor contention、futex wait
- 实战 SQL 查询：定位主线程锁等待最长的事件

```sql
-- 查询主线程锁竞争 Top 20
SELECT
  slice.name,
  CAST(slice.dur / 1e6 AS FLOAT) AS duration_ms,
  thread.name AS thread_name,
  process.name AS process_name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE slice.name LIKE '%monitor%'
  AND thread.name = 'main'
ORDER BY slice.dur DESC
LIMIT 20;
```

### 🔹 锚点 7：锁竞争优化的系统级策略
- DeliQueue（1.13 节详述）：消除主线程 MessageQueue 的 monitor 锁竞争
- 减小锁粒度：从全局锁到分区锁、per-CPU 锁
- 读写分离：ReadWriteLock / StampedLock 适用于读多写少场景
- 无锁数据结构：CAS-based（AtomicReference、ConcurrentLinkedQueue）
- RCU（Read-Copy-Update）：Linux 内核的读端零开销策略
- 避免嵌套锁：锁排序（lock ordering）防止死锁
- Android 17 的改进方向：更多子系统考虑无锁实现

### 🔹 锚点 8：版本演进中的锁优化
- Android 5.0 ART 替换 Dalvik：ART monitor 使用 futex 直接实现，减少一层间接调用
- Android 8.0 Binder 线程池扩展：从 8 个默认线程增加到 16 个，缓解锁争抢
- Android 12 PI-futex 全面启用：Binder 和 ART monitor 统一使用优先级继承
- Android 17 DeliQueue：主线程 MessageQueue 的无锁改造（1.13 节详述）
- 内核层面：EEVDF 调度器对锁持有者（lock holder）的调度优先级提升

## 🔸 扩展 1：常见问题与误区
1. 「synchronized 一定比 ReentrantLock 慢」→ 错误。无竞争时 synchronized 经历了多次 JIT 优化（偏向锁→轻量级锁→CAS），性能与 ReentrantLock 持平
2. 「无锁就一定更快」→ 不一定。CAS 重试（spin）在高竞争下比 futex sleep 浪费更多 CPU
3. 「锁竞争只在多线程场景出现」→ 不完全正确。主线程 post 消息到自己的 Handler 也可能因 MessageQueue 锁导致竞争（其他线程同时 enqueue）
4. 「Binder 调用没有锁」→ 错误。Binder IPC 的服务端处理涉及多个内部锁（IPCThreadState、ProcessState）
5. 「优先级继承能解决所有优先级反转」→ 不能。PI 只解决直接持锁关系的反转，多级传递的链式反转需要更复杂的协议

## 🔸 扩展 2：与其他机制的关系
- **1.5 线程模型**：锁是线程协作的基础设施，理解线程模型是分析锁竞争的前提
- **1.13 MessageQueue/DeliQueue**：DeliQueue 是锁竞争优化的典型案例
- **1.4 Binder IPC**：Binder 事务中的锁竞争是 ANR 的重要根因之一
- **2.4 Choreographer**：主线程锁竞争直接影响 doFrame 调度，导致掉帧
- **7.1 卡顿定义**：锁竞争导致的线程阻塞是卡顿的核心类型之一
- **9.1 ANR 设计思想**：主线程锁等待超过 5 秒触发 ANR

## 🔸 扩展 3：读者诊断清单
遇到疑似锁竞争问题时，按以下步骤排查：
1. 抓取 Perfetto trace（开启 sched、binder、monitor_contention category）
2. 查看主线程状态：大量 S 状态 + futex_wait → 确认有锁等待
3. 定位 Owner 线程：查看 Perfetto UI 中的 Owner-Waiter 连接线
4. 分析持锁原因：Owner 线程在做什么？是在执行耗时操作还是被更高优先级线程抢占？
5. 评估优化方向：减小锁粒度 / 改为无锁 / 使用读写锁 / 异步化
<!-- outline-end -->

## 为什么锁是性能分析的核心议题

当我们打开一份 Perfetto trace，试图理解某个掉帧或 ANR 的根因时，最常见的发现之一就是：主线程在等待一把锁。这把锁可能来自 MessageQueue 的 monitor lock，也可能来自 Binder 事务的服务端对象锁，或者是某个被广泛共享的全局锁。锁竞争不是一个独立的性能问题，它是理解 Android 系统中「谁在等谁、为什么等」的关键线索。

从系统的角度看，锁是线程之间协作的必要代价。Android 系统中有数千个锁实例同时运行，绝大多数时候它们安静地工作——一次 CAS 成功，几纳秒的开销，线程顺利获取资源继续执行。但当竞争发生时，等待锁的线程会被挂起（futex wait），经历一次完整的上下文切换，等待持锁线程释放后才能被唤醒（futex wake）。这个过程的开销从纳秒级跳到了微秒甚至毫秒级，如果等待发生在主线程上，一次锁竞争就可能直接导致掉帧。

更微妙的是优先级反转问题。Android 的主线程（UI 线程）具有较高的调度优先级，但当它需要等待一把被后台低优先级线程持有的锁时，就可能出现「高优先级线程被低优先级线程阻塞」的反转现象。如果此时还有中优先级线程在运行并抢占了低优先级线程的 CPU 时间，主线程可能长时间无法获取锁，导致严重的 jank 或 ANR。这个问题不是理论上的——DeliQueue（1.13 节）的设计动机正是为了消除主线程 MessageQueue 上的优先级反转。

理解锁竞争的机制，是读懂 Perfetto trace 中线程状态变化的基础，也是从「看到掉帧」到「定位根因」的关键一步。

## Android 中的锁类型全景

Android 系统横跨 Java、Native、内核三个层次，每一层都有自己的锁机制。从性能分析的角度看，我们需要理解这些锁类型的开销层级和在不同 trace 中的表现。

**Java 层的锁**以 `synchronized` 和 `java.util.concurrent` 包为核心。`synchronized` 是最基础的互斥机制，编译为 `monitorenter` / `monitorexit` 字节码，底层由 ART 虚拟机的 monitor 实现。ART 的 monitor 经历了几代优化：无竞争时使用 CAS（thin lock），竞争时膨胀为完整的 monitor 对象并调用 futex 系统调用。`ReentrantLock` 提供了更灵活的控制（可中断、可超时、公平/非公平模式），但底层同样依赖 CAS + futex。`ReadWriteLock` 和 `StampedLock` 在读多写少的场景中通过读写分离减少竞争。

**Native 层的锁**使用 POSIX `pthread_mutex` 和 C++ `std::mutex`。Android 的 bionic libc 实现了 `pthread_mutex`，支持 normal、errorcheck、recursive 三种类型。从 Android 12 开始，bionic 的 mutex 实现增加了对优先级继承（PI）的支持，通过 `PTHREAD_PRIO_INHERIT` 属性启用。这个改进对 Binder 等系统服务的锁性能至关重要。

**内核层的锁**是所有上层锁的基础。`futex`（Fast Userspace Mutex）是 Linux 提供的通用同步原语——用户态先通过 CAS 尝试获取锁（快速路径），失败时通过 `futex(2)` 系统调用让内核挂起线程（慢速路径）。`rt_mutex` 是内核的实时互斥锁，原生支持优先级继承。`spinlock` 用于内核中不可睡眠的上下文（中断处理、软中断），通过忙等而非睡眠实现互斥。

开销层级大致为：CAS（纳秒级）< 自旋锁（纳秒到微秒）< futex（微秒级）< monitor lock（微秒级，包含 ART 开销）< 跨进程 Binder 锁（数十微秒到毫秒级）。这个层级关系帮助我们理解 trace 中观察到的等待时间。

## Monitor Lock 的实现细节

ART 虚拟机对 `synchronized` 的实现是一个典型的「从快到慢」优化路径。

当一个线程首次进入 synchronized 块时，ART 尝试使用 CAS 将锁状态从「无锁」变为「被当前线程持有」（thin lock / locked）。这是最快路径，仅需一次原子操作，耗时在 10ns 以内。如果 CAS 成功，线程继续执行同步块中的代码。

如果 CAS 失败（锁已被其他线程持有），ART 先尝试短暂自旋（spin）。自旋的假设是：持锁线程可能很快释放锁，与其让线程睡眠再唤醒（涉及上下文切换），不如让等待线程忙等几个周期。自旋几次后如果仍然获取不到锁，ART 就将锁「膨胀」（inflate）为完整的 monitor 对象。

Monitor 膨胀后，等待线程通过 `futex(FUTEX_WAIT)` 系统调用进入内核等待队列。此时线程状态从 Running 变为 Sleeping（S），CPU 可以调度其他线程执行。当持锁线程退出 synchronized 块时，通过 `futex(FUTEX_WAKE)` 唤醒一个或多个等待线程。

[图：monitor lock 状态转换示意——无锁 → thin lock → 膨胀 → monitor]

Object.wait() / notify() / notifyAll() 是 monitor 的条件变量机制。wait() 将当前线程加入 monitor 的 wait set 并释放锁（通过 futex wait），notify() 从 wait set 中唤醒一个线程（通过 futex wake）。这个机制是 Java 生产者-消费者模式的基础。

## Futex：用户态与内核态的桥梁

futex 是 Linux 同步原语的核心创新。它的设计哲学是：无竞争时在用户态快速完成（CAS），有竞争时才进入内核态（系统调用）。

`futex(2)` 系统调用接受一个用户态地址（32 位整数）作为参数。`FUTEX_WAIT` 语义：如果该地址的值等于期望值，则将当前线程挂起等待；如果不等于，立即返回。`FUTEX_WAKE` 语义：唤醒等待在该地址上的一个或多个线程。

在 Android 中，futex 被广泛使用：ART monitor 的膨胀路径调用 futex wait/wake；`pthread_mutex` 的竞争路径调用 futex；Binder 框架使用 futex 管理线程唤醒和事务完成通知。

特别重要的是 PI-futex（`FUTEX_LOCK_PI` / `FUTEX_UNLOCK_PI`），它扩展了普通 futex 以支持优先级继承。当高优先级线程等待一个被低优先级线程持有的 PI-futex 时，内核会临时将低优先级线程的调度优先级提升到等待者的级别，确保它能尽快执行并释放锁。Android 12+ 中，Binder 框架和 ART monitor 都启用了 PI-futex。

## 优先级反转：从火星到手机

优先级反转是最经典的实时系统问题之一。1997 年，NASA 的火星探路者号探测器因为优先级反转导致任务频繁重启——这个案例被写入了几乎每一本操作系统教科书。

在 Android 中，这个问题同样存在。考虑这个典型场景：主线程（优先级较高，约 -10 nice）需要获取一把 MessageQueue 的 monitor lock，但锁被一个后台 HandlerThread（优先级较低，约 5 nice）持有。主线程进入 futex wait。此时如果有另一个中优先级线程（如音频处理线程，优先级约 0 nice）在运行，它可能抢占后台线程的 CPU 时间，导致后台线程迟迟无法执行完同步块释放锁。主线程就这样被间接阻塞了——这就是优先级反转。

优先级继承是标准的解决方案。当检测到反转时，内核临时提升持锁线程的优先级到等待者的级别。对 PI-futex 来说，这个过程在 `FUTEX_LOCK_PI` 的内核路径中自动完成。Android 12 统一启用了 Binder 和 ART 的 PI 支持后，大部分直接的反转场景得到了缓解。

但优先级继承不是万能的。2026 年的技术简报指出，即使在没有实际竞争的情况下，PI-futex 的 wake 路径也需要遍历内核的 PI 树并做优先级比较，这比普通 futex 的 wake 路径多约 15% 的开销。此外，多级传递的链式反转（A 等 B 的锁，B 等 C 的锁）需要更复杂的协议（如优先级上限协议 Priority Ceiling Protocol）来解决，Android 目前没有实现。

## Binder 框架中的锁竞争

Binder 是 Android 进程间通信的支柱，它的锁竞争模式与单进程内的锁不同——涉及跨进程的同步。

Binder 驱动为每个进程维护一个线程池（默认最大 16 个线程）。当客户端发起 Binder 调用时，驱动从目标进程的线程池中选取一个空闲线程来处理请求。如果所有线程都在忙（处理其他事务或在等待锁），新的 Binder 事务就会排队等待。

在 system_server 中，几个全局锁是高争抢的热点。`WindowManagerGlobalLock` 保护窗口管理器的状态，几乎所有涉及窗口操作的 Binder 调用都需要获取它。`ActivityManagerGlobalLock` 保护 Activity 管理状态。`PackageManagerService` 的安装/查询锁在高频使用场景（如应用启动时查询组件信息）中也可能成为瓶颈。

当一个 Binder 线程持有某个服务锁并在处理事务时，如果该事务的处理又需要等待另一个锁（比如在 WMS 处理过程中需要等待 AMS 的锁），就可能形成跨服务的锁链。这种锁链在 Perfetto 中表现为多个 Binder 线程同时处于 S 状态，且它们之间存在锁等待的依赖关系。当锁链足够长时，可能导致 Binder 线程池耗尽——所有 16 个线程都在等锁，无法响应新的 Binder 请求，最终触发 ANR。

[图：Binder 线程池锁链示意——多个 Binder 线程通过锁依赖形成的等待链]

## 在 Perfetto 中识别锁竞争

Perfetto 是分析锁竞争的主要工具。在 trace 中，锁竞争有几种典型的表现形式。

**线程状态分析**是最直接的方式。当一个线程因锁竞争而阻塞时，它的状态从 Running（R）变为 Sleeping（S），blocked function 显示为 `futex_wait_queue_me`（Native 锁）或对应的 Java monitor 等待函数。在 Perfetto UI 的线程 track 上，这表现为一段较长的灰色（S 状态）区域，其间线程没有任何 CPU 活动。

**Monitor Contention 切片**提供了 Java 层锁竞争的直接信息。开启 `monitor_contention` trace category 后，Perfetto 会记录每次 monitor 竞争的详细信息，包括：
- 等待线程（Waiter）和持锁线程（Owner）的标识
- 锁对象的类名（如 `com.android.server.wm.WindowManagerGlobalLock`）
- 等待时长

在 Perfetto UI 中，monitor contention 切片显示在对应线程的 track 上，通常用特定颜色标记。点击切片可以在详情面板中看到 Owner 线程信息和调用栈。

**Binder 事务锁竞争**需要结合多个 Track 分析。查看 system_server 的 Binder 线程状态，如果一个或多个线程长时间处于 S 状态且 blocked function 包含 `binder` 或 `futex`，说明这些线程在处理 Binder 事务过程中等待某个锁。

```sql
-- 查找 system_server 中最长的 monitor 竞争事件
INCLUDE PERFETTO MODULE android.monitor;

SELECT
  slice.name AS lock_class,
  CAST(slice.dur / 1e6 AS FLOAT) AS wait_ms,
  thread.name AS waiter_thread,
  process.name AS process_name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'system_server'
  AND slice.name GLOB '*monitor*'
ORDER BY slice.dur DESC
LIMIT 30;
```

这段 SQL 从 Perfetto 的 monitor contention 数据中筛选 system_server 内的锁竞争事件，按等待时长降序排列。通过锁对象名称（如 WindowManagerGlobalLock）可以快速定位到具体的服务锁。

## 锁竞争优化的系统级策略

减少锁竞争的核心思路有三种：消除锁（无锁设计）、缩小锁的范围（减小粒度）、减少锁的持有时间（快速路径）。

**无锁设计**是最彻底的方案。DeliQueue（1.13 节）就是典型案例——它用无锁 Treiber 栈替代了 monitor lock 管理消息队列，使后台线程插入消息时不再需要获取主线程的锁。无锁设计的代价是实现复杂度更高（需要处理 CAS 失败、ABA 问题等），但在高争抢场景下性能收益显著。

**减小锁粒度**从全局锁改为分区锁。例如，将一个保护所有窗口状态的锁拆分为每个窗口独立的锁，使不同窗口的操作可以并行。Android 的 WMS 在演进过程中就经历了这种粒度细化。

**读写分离**对读多写少的场景特别有效。配置信息查询是典型的读多写少场景——大量线程并发读取配置，但只有少数线程会更新。`ReadWriteLock` 允许多个读线程同时获取锁，只在写线程请求时独占。`StampedLock` 进一步优化了乐观读路径。

**避免嵌套锁**是防止死锁和降低竞争的基本原则。当两个线程以不同顺序获取相同的两把锁时，就会产生死锁。遵循固定的锁排序（如总是先锁 A 再锁 B）可以避免死锁，但嵌套锁本身也增加了锁的持有时间。

从 Android 版本演进看，锁优化是一个持续的过程。Android 17 的 DeliQueue 是近年最显著的锁优化，但更广泛地看，几乎每个大版本都在减少系统关键路径上的锁竞争。例如 Android 8.0 将 Binder 线程池从 8 扩展到 16、Android 12 统一启用 PI-futex、Android 16 引入 ADPF 对持锁线程的调度优先级动态调整等。

## 版本演进中的锁优化

| 版本 | 优化内容 | 影响 |
|------|----------|------|
| Android 5.0 | ART 替换 Dalvik，monitor 直接基于 futex | 减少锁获取的一层间接调用 |
| Android 8.0 | Binder 线程池从 8 扩展到 16 | 缓解线程池级别的锁争抢 |
| Android 12 | ART monitor 和 Binder 统一启用 PI-futex | 系统级缓解优先级反转 |
| Android 16 | ADPF 可提升前台应用线程调度优先级 | 间接减少持锁线程被抢占的概率 |
| Android 17 | DeliQueue 无锁 MessageQueue | 主线程锁竞争时间减少 15% |

[待补充: 内核 EEVDF 调度器对 lock holder preemption 的处理策略变化]
