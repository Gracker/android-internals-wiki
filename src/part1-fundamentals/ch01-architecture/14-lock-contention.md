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
created_date: '2026-04-06'
drafted_date: '2026-04-06'
reviewed_date: '2026-07-25'
reviewed_by: Codex
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
deepseek_cn_review_state: done
created_by: "task2a-knowledge-gap"
gap_source: "研究素材+AOSP结构+每日信息+读者需求"
gap_score: "17/20"
drafted_by: "openclaw-task2a"
task9_reviewed_date: "2026-07-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-14T17:26:54+08:00"
last_task9_audit: "2026-07-02"
last_task9_audit_log: "logs/deep-review/2026-07-02-12-audit.md"
task6_review_notes_round4: "2026-07-03 Task6 revisiting-review round4 (post-Task9 autofix): pass-light-edit. L1 scan: 0 banned words, 0 high-freq violations. L2: structure intact, outline 8/8 anchors + 3/3 extensions covered. No new L3/L4 issues. task9_result=auto-fixed (not pass-tech-review), cannot auto-promote."
task6_review_notes_round2: "2026-07-02 Task6 revisiting-review round2 (post-Task9 autofix): pass-light-edit. Task9 idle audit auto-fixed Android 17 source re-anchoring (OomAdjuster package path, DeliQueue metrics). L1 scan: 0 banned words, 0 high-freq violations. L2: structure intact, outline 8/8 anchors covered, 4 extensions covered. No new L3/L4 issues. task9_result=auto-fixed (not pass-tech-review), cannot auto-promote."
last_task9_autofix_at: "2026-07-02"
last_task2b_at: "2026-05-27T16:50:00+08:00"
task2b_notes: "2026-05-27 Task2B：清理文末 AIW 源码调研原始块，将 AMS mGlobalLock/mProcLock 双锁与 PI-futex 边界合并入正文。"
last_task6_audit: "2026-06-08"
last_task6_at: "2026-07-14T13:14:05+08:00"
last_task6_review_log: "logs/review/2026-06-25-21-review.md"
review_type: "task6-writing-quality-review"
task6_l1_l2_fixes: 9
task6_l3_l4_issues: 0
task6_review_notes: "2026-07-14 Task6 revisiting-final: pass-light-edit. L1 小修 1 处（正文列表项 mProcLock 缺 backticks）。无新增 L3/L4 回炉项。Task9 pass-tech-review，queue 无 pending，自动晋升 finalized。 | 2026-06-25 21:17 Task6 复审：修复 LRU 性能数据小节重复（删除文末 1204 字符重复块）、性能数据中英文间距、大纲禁用词「深入分析」、补 [待验证] 标注；Task9 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_review_log: logs/deep-review/2026-07-14-17-deep-review.md
task9_review_notes: "2026-07-03 04:37 Task9 deep-review：AOSP android-17.0.0_r1 / kernel common android17-6.18 源码锚点复核通过；无 P0/P1；1 条 LRU 性能数据待补实测，写入 suggestions；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-02 12:46 Task9 idle audit AUTO-FIX：重锚 ART/bionic/Binder/AMS/DeliQueue 源码到 Android 17，修正 OomAdjuster Android 17 包路径与 DeliQueue 官方指标口径；回到 Task6 复审。 | 2026-05-27 15:22 Task9 deep-review：技术复审无新增 P0/P1；既有 queue pending 为 Task6/Task2B 文末源码调研原始块清理，不自动晋升。 | 2026-07-14 Task9 deep-review: pass-tech-review. P0=0/P1=0/P2=0, queue 无 pending, 自动晋升 finalized."
last_deepseek_cn_review_at: 2026-07-15
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 1
finalized_by: "openclaw-task6-auto-promote"
finalized_date: "2026-07-14"
---

# 1.14 锁竞争与同步性能分析

线程显示为等待（Waiting）或休眠（Sleeping），只能证明它没有在 CPU 上执行，不能直接证明发生了锁竞争。它可能在等 Java monitor、native mutex、条件变量、Binder 回复、I/O、定时器，也可能只是 Looper 正常睡在 `epoll_wait()`。

诊断锁问题时，先回答四个问题，不要从猜测“哪种锁更快”开始：

1. **谁在等**：主线程、RenderThread、Binder worker，还是普通后台线程？
2. **等什么**：Java monitor、native 同步原语、Binder 回复，还是正常事件等待？
3. **谁能让它继续**：实际持锁者或服务端线程是谁？
4. **owner 为什么没有及时推进**：正在运行、排队等 CPU、阻塞在另一把锁，还是做了 I/O？

这四个答案拼起来，才是一条可修复的等待链。

## 1. 先把几类“等”分开

Android 跟踪记录中容易混淆的是下面五类路径。

| 类型 | 常见入口 | 主要实现 | 首要证据 |
| --- | --- | --- | --- |
| Java monitor | `synchronized`、`Object.wait()` | ART Monitor / LockWord | `android_monitor_contention`、owner/waiter 方法 |
| Java 并发包 | `ReentrantLock`、`Condition`、`LockSupport.park()` | AQS、park/unpark、native 等待 | Java 调用栈、线程状态、相关业务埋点 |
| Native 锁 | `pthread_mutex`、`std::mutex`、condition variable | bionic + futex | native 栈、`blocked_function`、锁埋点 |
| Binder IPC | 同步 AIDL、服务端线程池 | libbinder + binder driver | binder transaction/reply、client/server 线程状态 |
| Looper 等待 | `MessageQueue.next()` | Java 队列 + native Looper + epoll | 是否有到期消息、`nativePollOnce()`、MessageQueue contention |

它们都可能在内核线程状态里表现为睡眠，但优化方式完全不同。

- Java 监视器要找持有同一对象 monitor 的线程。
- `ReentrantLock` 不属于 ART monitor，不能指望 `android_monitor_contention` 自动给出 owner。
- native `futex_wait` 只说明某个 futex 慢路径在等待，无法据此确认它对应互斥锁或启用了优先级继承。
- 同步 Binder 调用的 client 等的是服务端回复；服务端内部可能又卡在 Java 或原生锁上。
- 空闲 Looper 睡在原生轮询中属于正常行为，无需消除。

## 2. ART Monitor：`synchronized` 在 Android 17 中怎样工作

Java 字节码用 `monitorenter` 和 `monitorexit` 表达 `synchronized`。ART 在对象头的 32 位 LockWord 中记录轻量状态，必要时再关联完整的 `Monitor` 对象。

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

这些枚举说明 LockWord 还要容纳对象标识哈希和转发状态。观察到 `synchronized` 时，不能把对象头恒定解释成一组 owner/递归计数字段。

### 2.1 无竞争路径：thin lock

对象未加锁时，ART 可以把当前线程的监视器线程 ID 和递归计数编码进 LockWord。线程通过原子更新获得轻量锁（thin lock）；同一线程重入时增加计数。

thin lock 的优势是不用为每个曾被 `synchronized` 的对象都分配完整 Monitor。无竞争时，路径短、没有线程休眠，也没有内核调度切换。

“无竞争的 `synchronized` 很便宜”不等于“任何 `synchronized` 都只做一次 CAS”。对象可能已经膨胀为 fat monitor，可能带有 identity hash code，也可能发生递归和运行时状态变化。性能结论要落到实际对象和竞争形态。

### 2.2 竞争、`wait()` 和 identity hash：monitor inflation

`art/runtime/monitor.cc` 的源码注释列出需要完整 Monitor 的三类典型情况：

- 出现真实竞争。
- 在对象上调用 `wait()`。
- 一个需要加锁的对象同时带有 identity hash code。

竞争线程面对被其他线程持有的 thin lock 时，ART 会协调 owner 并尝试把锁膨胀为重量级监视器（fat monitor）。重量级监视器记录完整的 owner、waiter、条件等待和诊断信息。

`Object.wait()` 的语义也不能简化成“睡一会”：

1. 调用线程必须已经持有该对象 monitor。
2. `wait()` 把线程放入等待集合，并释放 monitor。
3. `notify()` / `notifyAll()`、中断或超时使它具备继续条件。
4. `wait()` 返回前还必须重新获得同一个 monitor。

因此，被唤醒不等于马上执行。线程可能从“等通知”转成“等重新拿锁”。

### 2.3 `kLongWaitMs` 是日志阈值，不是统一的 Perfetto 阈值

Android 17 源码定义：

```cpp
static constexpr uint64_t kDebugThresholdFudgeFactor =
        kIsDebugBuild ? 10 : 1;
static constexpr uint64_t kLongWaitMs =
        100 * kDebugThresholdFudgeFactor;
```

也就是发布构建为 100ms，debug 构建为 1000ms。这个常量服务于 ART 的长竞争告警逻辑，日志是否出现还受采样、owner 方法是否可解析等条件影响。

它不能用来推导以下结论：

- “小于 100ms 的锁竞争不会进 Perfetto。”
- “没有长等待日志就没有锁问题。”
- “100ms 是 Android 所有锁的统一严重阈值。”

一帧在 60Hz 下只有约 16.7ms，几毫秒的主线程锁等待已经可能造成掉帧，远不到 ART 长等待日志的量级。

## 3. Futex：用户态快路径与内核慢路径

futex 是用户态原子状态与内核等待队列协作的机制；它本身不是某一种具体的 C++ 锁。

普通 mutex 的典型思路是：

```text
尝试用户态原子加锁
  ├─ 成功：直接进入临界区
  └─ 失败：标记存在竞争，通过 futex 进入内核等待

解锁
  ├─ 没有 waiter：用户态完成
  └─ 存在 waiter：通过 futex 唤醒等待线程
```

`bionic/libc/bionic/pthread_mutex.cpp` 的非 PI 互斥锁路径会在竞争时调用 `__futex_wait_ex()`，释放竞争锁时调用 `__futex_wake_ex()`。无竞争时不需要每次都陷入内核。

这也是为什么 `blocked_function` 里看到 `futex_*` 仍然不能直接下结论：

- 它可能来自 `pthread_mutex`。
- 可能来自 condition variable。
- 可能来自 ART 或其他运行时内部同步。
- 可能是 Java 并发包最终触发的 park。
- 只能证明线程在某个 futex 等待点睡眠，不能单凭函数名恢复锁对象和 owner。

要定位原生锁，通常还需要原生调用栈、业务锁埋点、同进程线程状态，或在可复现环境中增加针对该锁的 trace。

## 4. 优先级反转与 PI-futex

优先级反转的经典链条是：

```text
低优先级线程 L：持有锁
中优先级线程 M：持续占用 CPU
高优先级线程 H：等待 L 的锁

结果：H 的进度被 M 间接拖慢
```

即使 L 的临界区只有 1ms，如果 L 长时间拿不到 CPU，这把锁对 H 的墙上时间影响也可能远大于 1ms。

### 4.1 PI 的作用

ACK `android17-6.18-2026-06_r6` 的 rt-mutex 文档描述了优先级继承：

- 高优先级 waiter 阻塞在 rt-mutex 上时，低优先级 owner 临时继承更高优先级。
- owner 释放锁后撤销这次提升。
- owner 又阻塞在另一把 rt-mutex 时，提升可以沿依赖链传播。
- waiter 按优先级组织；同优先级使用 FIFO 顺序。

PI 缩短的是“高优先级线程被低优先级 owner 挡住，而 owner 又抢不到 CPU”的窗口。它不能缩短 owner 自己在临界区里做的 I/O、长计算或同步 Binder 调用。

### 4.2 Android 17 bionic 怎样选择 PI mutex

bionic 支持：

```c
pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
pthread_mutex_init(&mutex, &attr);
```

只有 mutex 属性显式选择 `PTHREAD_PRIO_INHERIT`，bionic 才走 `__futex_pi_lock_ex()` / `__futex_pi_unlock()`，由内核 PI-futex 和 rt-mutex 处理 owner 提升。普通 mutex 仍走普通 futex 路径。

所以：

- “Android 内核支持 PI-futex”是能力描述。
- “这把锁启用了 PI”必须检查它的初始化属性。
- “某线程在 `futex_wait`”不能证明它走的是 PI。

PI 也不是修复糟糕锁设计的替代品。临界区过大、锁顺序混乱、持锁做 I/O，仍应先从设计上消除。

## 5. Binder 等待与 Java 锁等待是两条不同路径

同步 Binder 调用跨越 client、驱动和 server：

```text
客户端线程
  └─ binder transaction
      └─ Binder 驱动选择/唤醒 server thread
          └─ Server Binder thread Binder 线程执行服务代码
              └─ binder reply
                  └─ Client 继续执行
```

client 在等回复时没有持有“Binder Java monitor”。驱动使用自己的锁和 wait queue 管理事务、线程与工作项；server 的业务代码则可能再遇到 Java 监视器或 native mutex。

一次同步 Binder 延迟可以拆成：

```text
总墙上时间
= client 入驱动与排队
+ server thread 获得运行机会
+ server 业务执行
+ server 内部锁 / I/O / 嵌套 Binder 等待
+ reply 返回与 client 再次被调度
```

只看 client 睡在 Binder 相关内核函数上，无法判断哪一项占主导。

### 5.1 Binder 有自己的优先级传播

`drivers/android/binder.c` 在当前 ACK tag 中包含：

- `binder_select_thread_ilocked()`：为进程工作选择等待线程。
- `binder_wakeup_thread_ilocked()`：唤醒具体线程或通知进程需要线程。
- `binder_transaction_priority()`：根据事务与 Binder 节点限制处理 server thread 的优先级。

这是 Binder 事务调度的一部分，不等同于 `PTHREAD_PRIO_INHERIT`，也不会自动提升“server thread 正在等待的某个 Java monitor owner”。如果 Binder 工作线程进入服务代码后又卡在应用锁上，仍要沿 Java 或 native owner 链继续追。

### 5.2 默认 15 不代表进程里固定只有 15 条 Binder 线程

Android 17 的 `ProcessState.cpp` 定义：

```cpp
#define DEFAULT_MAX_BINDER_THREADS 15
```

初始化 Binder 驱动时，libbinder 通过 `BINDER_SET_MAX_THREADS` 把这个默认最大值设为 15。与此同时，`startThreadPool()` 会调用 `spawnPooledThread(true)` 主动启动一条 main pooled thread。

因此应该这样读：

- 15 是 libbinder 传给驱动的默认“可请求启动线程”上限。
- 主动启动的 main pooled thread单独计入总量计算。
- 业务线程也可以进入 Binder 调用上下文。
- 服务可以在启动线程池前通过 API 配置不同上限。

把这些机制压缩成“Binder 线程池固定 15 条”或“固定 16 条”都会误导跟踪分析。线程数只是容量的一部分；一个 worker 持大锁或做慢 I/O，仍可能让其他事务排队。

## 6. system_server：Binder 慢经常只是表象

App 主线程调用 AMS、WMS 或 PMS 后长时间等待回复，常见根因位于服务端，而非 Binder 驱动本身：

- Binder 工作线程等 system_server 的全局对象锁。
- owner 持锁执行长计算或磁盘 I/O。
- owner 在持锁状态发起另一个同步 Binder 调用。
- 多把系统锁形成长等待链。
- Binder 工作线程接近饱和，新事务迟迟没有线程处理。

分析顺序应是：从 client transaction 跟到 server reply，再看服务端线程的状态；如果它在等锁，继续找 owner，不能停在“Binder 调用耗时”这个表面结论。

### 6.1 Android 17 AMS 的 `mGlobalLock` 与 `mProcLock`

`ActivityManagerService.java` 当前源码明确给出：

```java
final ActivityManagerGlobalLock mGlobalLock = ActivityManagerService.this;

private static final boolean ENABLE_PROC_LOCK = true;

final ActivityManagerGlobalLock mProcLock = ENABLE_PROC_LOCK
        ? new ActivityManagerProcLock() : mGlobalLock;
```

源码注释规定锁顺序：`mProcLock` 位于 `mGlobalLock` 之下，不应在只持有 `mProcLock` 时反向获取 `mGlobalLock`。

`@CompositeRWLock({"mService", "mProcLock"})` 表达的是静态锁契约，不会在运行时创建读写锁对象：相关状态读取可由两把锁中的任意一把保护，写入通常要求同时持有两把锁。方法后缀也帮助审阅调用约束：

- `LOSP`：通常表示持有列出的任一锁。
- `LSP`：通常表示同时持有 service/global 与 proc lock。

例如 Android 17 的 `OomAdjuster`：

```java
@GuardedBy("mServiceLock")
void updateOomAdjLocked(@OomAdjReason int oomAdjReason) {
    synchronized (mProcLock) {
        updateOomAdjLSP(oomAdjReason);
    }
}
```

这里调用者已经受 `mServiceLock` 保护，再进入 `mProcLock`，符合全局锁到进程锁的顺序。`ProcessList.mLruProcesses` 也标注为 composite lock 保护。

这些源码能证明锁域和顺序，不能单独证明某个固定性能提升比例。锁持有时间必须来自具体设备与 trace；没有可定位的一手基准时，不应写“从 25ms 降到 8ms”或“吞吐提升 3 倍”。

## 7. MessageQueue：Android 17 的一个针对性去锁案例

旧 MessageQueue 用同一个 `synchronized (this)` 保护有序链表，生产者入队、Looper 取消息和移除操作会在这把 monitor 上竞争。

对运行在 Android 17 且 `targetSdkVersion >= 37` 的应用，DeliQueue 默认启用。它把生产者提交改为 Treiber 栈上的 CAS，由 Looper 独占两个最小堆完成同步/异步消息排序。核心消息路径不再依赖旧的单一全局 monitor，但 IdleHandler 和文件描述符记录仍有各自的小锁。

Google 公布的内部 beta trace 中，App 主线程花在锁竞争上的时间下降 15%。这个数字只描述其样本中的 MessageQueue 改造效果，不能外推到 AMS、Binder、native mutex 或业务锁。

DeliQueue 展示了一种有边界的无锁设计：

- 多生产者共享的提交路径无锁。
- 排序复杂度留给单一 Looper owner。
- 取消时先标记墓碑，物理清理由 Looper 完成。
- 同步屏障、异步消息和 native poll 的语义继续保留。

它不适合作为“把所有锁换成 CAS”的通用模板。无锁结构仍会产生 CAS 重试、共享缓存行抖动、内存分配和延迟清理成本。

## 8. Perfetto：先找证据，再解释原因

### 8.1 Java monitor

当前 Perfetto 标准库模块名是 `android.monitor_contention`，查询表名是 `android_monitor_contention`：

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

这张表能给出 Java 监视器的 waiter、owner、双方方法、源码位置、是否主线程、锁名和时长。`android_monitor_contention_chain` 还能表达竞争的父子关系；配套 thread-state 表可以继续检查持锁者在持锁期间处于运行（Running）、可运行（Runnable），还是又阻塞在其他内核函数。

注意两个边界：

- 表中没有记录，不等于设备上绝对没有竞争；trace 配置、运行时采样和可解析信息都会影响数据完整性。
- 这张表针对 ART Java monitor，不覆盖所有 `ReentrantLock` 和 native mutex。

### 8.2 Native futex 等待

没有专门锁埋点时，可以先从 `thread_state.blocked_function` 找 futex 慢路径：

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

这一步只负责找候选。随后要结合原生栈或源码确认它对应 mutex、condvar 还是其他等待，并找 owner。不能根据 `futex_wait` 一个字符串直接断定发生了 Java 锁竞争。

### 8.3 Binder 客户端与 server

Perfetto 的 `android.binder` 模块可以把事务和回复关联到 client/server：

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

再用 `android_sync_binder_thread_state_by_txn` 或 `android_sync_binder_blocked_functions_by_txn` 分解 client 与 server 两端的线程状态。若 server reply 区间叠加 Java monitor contention，就继续查 `android_monitor_contention` 给出的 owner。

“client 时间长、server 时间短”可能意味着排队、调度或回复返回延迟；“server 时间长”也不能直接等同于 CPU 计算，server 可能大部分时间在锁、I/O 或嵌套 Binder 上。

## 9. 三个常见现场怎样推理

### 现场一：主线程出现 `monitor contention with ...`

1. 在 `android_monitor_contention` 找 waiter 方法、owner 线程和 owner 方法。
2. 看 owner 在等待区间内的 `thread_state`。
3. owner 如果 Runnable 但长时间未运行，检查 CPU 压力与优先级反转。
4. owner 如果睡在另一把锁或 Binder 上，继续沿依赖链追。
5. 回源码确认临界区，检查能否移出 I/O、IPC 或长计算。

### 现场二：主线程睡在同步 Binder 调用

1. 用 `android_binder_txns` 找 server 进程、线程和方法。
2. 比较 client 与 server 区间，确认时间花在哪一端。
3. 服务端工作线程若等监视器，用竞争表找持锁者。
4. server worker 若在原生 native futex，结合原生栈找具体锁。
5. 多个事务都排队时，检查 worker 饱和和某个长事务是否占住线程。

### 现场三：线程停在 `futex_wait`

1. 先确认 Java 调用栈是否来自 ART monitor、AQS/park，还是 JNI/native 代码。
2. 检查是否有对应的 `android_monitor_contention` 事件。
3. 没有 Java 监视器证据时，按原生锁或条件等待调查。
4. 找初始化代码，确认是否为 PI mutex；不能根据函数名猜测。
5. 如果这是正常 condvar 等待，再查“为什么条件迟迟没有产生”，无需优化 futex 本身。

## 10. 锁优化的工程顺序

### 10.1 先缩短临界区

最常见的有效改动是把不保护共享不变量的工作移出锁：

- 日志格式化和大对象构建。
- 磁盘、网络和数据库 I/O。
- 同步 Binder 调用。
- 可在锁内复制输入、锁外计算、锁内提交结果的长计算。
- 不需要共享状态保护的回调。

把代码移出锁前要重新审视不变量。盲目缩小范围可能制造 check-then-act race，性能改善不能以破坏正确性为代价。

### 10.2 再减少共享状态

- 用线程封闭或消息传递代替共享可变对象。
- 把一把全局锁拆成按对象、按分片或按子系统的锁。
- 读多写少时考虑不可变快照、copy-on-write 或读写分离。
- 高频计数器考虑分片，减少多个 CPU 写同一缓存行。

拆锁会引入锁顺序和跨域一致性问题。先写清哪些字段构成同一不变量，再决定能否拆。

### 10.3 明确锁顺序

跨多把锁时，项目应定义全局顺序，并在代码审查中阻止反向获取。Android 17 AMS 对 `mGlobalLock` → `mProcLock` 的注释就是这种契约。

超时只能限制等待，并不能修复潜在死锁；`tryLock()` 也不能自动保证状态机正确。

### 10.4 最终才比较锁类型或无锁结构

选择 `synchronized`、`ReentrantLock`、读写锁或无锁结构，应由需求决定：

- 是否需要可中断获取或超时。
- 是否需要多个 Condition。
- 是否允许公平策略带来的吞吐成本。
- 读写比例和临界区大小。
- 竞争线程数、优先级和 CPU 拓扑。
- 失败重试与内存回收是否可控。

微基准要覆盖真实竞争形态。只测单线程 acquire/release，无法预测主线程与多后台生产者同时竞争时的尾延迟。

### 10.5 Binder 线程数不是第一修复手段

增加 worker 可能缓解排队，也可能让更多线程同时争同一把全局锁，增加内存和调度压力。先找最长事务、持锁 I/O、嵌套同步 IPC 和锁依赖链，再判断容量是否不足。

## 11. 版本边界

| 版本 | 可确认的同步相关变化 | 阅读方式 |
| --- | --- | --- |
| Android 5.0（API 21） | 应用运行时切换到 ART，Java 监视器分析以 ART `monitor.cc` / `lock_word.h` 为准 | 不沿用 Dalvik 时代实现细节解释当前系统 |
| Android 9（API 28） | bionic 已具备 `PTHREAD_PRIO_INHERIT` mutex 属性接口 | 只说明可用；具体锁是否启用仍看初始化 |
| Android 17（API 37） | 当前 bionic PI 互斥锁走 PI-futex；当前 ACK 为 `android17-6.18-2026-06_r6`；DeliQueue 对目标版本为 37+ 的应用默认启用 | 平台、bionic 与内核源码按本知识库统一锚点核对 |

Binder 默认线程配置在历史上容易被误传。当前 Android 17 锚点下，`DEFAULT_MAX_BINDER_THREADS` 为 15，`startThreadPool()` 另行启动 main pooled thread；这个数值并非进程的固定线程总数。

## 12. 常见误区

### “Waiting / Sleeping 就是锁竞争”

不成立。Looper、条件变量、Binder、I/O 和定时器都会让线程睡眠。先找等待对象和唤醒条件。

### “`synchronized` 一定比 `ReentrantLock` 慢”

不成立。它们的功能、运行时路径和竞争行为不同。没有负载和 trace，单凭类型无法判断。

### “看到 `futex_wait` 就找 Java monitor owner”

不成立。先看 `android_monitor_contention` 和调用栈。futex 是底层等待机制，不是 Java 监视器的专属标签。

### “内核支持 PI，所以 Android 关键锁都有优先级继承”

不成立。bionic 互斥锁必须以 `PTHREAD_PRIO_INHERIT` 初始化；Binder 的事务优先级传播又是另一套机制。

### “Binder 调用慢就是驱动慢”

大多数时候证据还不够。server worker 可能卡在业务锁、I/O、CPU 调度或嵌套 IPC。先把 client 与 server 两端时间线连起来。

### “无锁一定更快”

不成立。CAS 重试、cache-line bouncing、GC 和算法复杂度都可能成为新成本。DeliQueue 的价值来自针对具体队列拓扑的重构，不能只归结为“无锁”两个字。

## 结论

锁竞争分析要还原完整的等待链。Java 监视器用 `android_monitor_contention` 找 waiter 与 owner；native mutex 从 futex 候选回到原生栈和初始化代码；Binder 用 transaction/reply 连起 client 与 server；MessageQueue 还要区分正常 native poll 与旧 monitor 竞争。

找到 owner 后继续问：它在 CPU 上运行吗，还是 Runnable 却没被调度？它是否阻塞在另一把锁、I/O 或 Binder 上？追到无法推进的节点后，缩短临界区、拆锁、调整线程模型、启用 PI 或采用无锁结构才有明确目标。

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
