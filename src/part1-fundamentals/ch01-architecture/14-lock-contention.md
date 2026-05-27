---

title: "锁竞争与同步性能分析"
chapter: "1.14"
status: ready-for-review
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37); bionic PI mutex sections require Android 9+; DeliQueue applies to Android 17 targetSdk 37+"
tags: [Mutex, Futex, monitor lock, 优先级反转, 锁竞争, DeliQueue, Perfetto, Binder, jank, ANR]
related_chapters: ["1.4", "1.5", "1.13", "2.4", "2.5", "7.1", "9.1"]
section: "1.14"
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "研究素材+AOSP结构+每日信息+读者需求"
gap_score: "17/20"
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-05-27"
reviewed_by: "openclaw-task6"
last_verified: "2026-04-11"
last_verified_against: "AOSP android-16.0.0_r1 + bionic android-9.0.0_r1 + binder android-7.1.2_r39/android-8.0.0_r1 + Perfetto stdlib"
confidence: "medium"
sources:
  - type: aosp
    path: "platform/art/runtime/monitor.cc (android-16.0.0_r1)"
  - type: aosp
    path: "platform/art/runtime/lock_word.h (android-16.0.0_r1)"
  - type: aosp
    path: "platform/bionic/libc/bionic/pthread_mutex.cpp (android-9.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/native/libs/binder/ProcessState.cpp (android-7.1.2_r39)"
  - type: aosp
    path: "platform/frameworks/native/libs/binder/ProcessState.cpp (android-8.0.0_r1)"
  - type: aosp
    path: "kernel/common/drivers/android/binder.c (android-mainline)"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention"
  - type: official
    path: "https://source.android.com/docs/core/audio/latency/priority-inversion"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html"
  - type: note
    path: "intake/research-feeds/2026-04-06-15-perfetto-monitor-contention-art-lock-analysis.md"
  - type: note
    path: "intake/research-feeds/2026-04-06-15-art-thin-fat-lock-inflation-long-wait.md"
  - type: note
    path: "intake/research-feeds/2026-04-06-15-priority-inversion-futex-pi-android-lock-performance.md"
  - type: note
    path: "intake/research-feeds/2026-04-05-19-android17-deliqueue-lockfree-messagequeue.md"
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: needs-rework
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-27"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-27T15:22:00+08:00"
task2b_state: pending
task2b_result: fixed
last_task2b_at: "2026-05-27T14:50:00+08:00"
task2b_notes: "2026-05-27 Task2B fallback：修复 Task9 2026-05-18 抽检问题；收窄适用版本，修正 DeliQueue URL/targetSdk 37+ 条件，删除 PTHREAD_PRIO_PROTECT、android_pid_t/ANDROID_PID_MAX 与 SF/Input PI-futex 错误断言。"
last_task6_audit: "2026-05-17"
last_task6_at: "2026-05-27T15:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-27-15-review.md"
review_type: "task6-writing-quality-review"
task6_l1_l2_fixes: 14
task6_l3_l4_issues: 1
task6_review_notes: "2026-05-27 15:08 Task6：修复若干口语化/编辑痕迹表达；发现文末仍保留两段 AIW 源码调研原始块，需 Task2B 整合/清理后再审，已写入 queue.json。"
last_task9_review_log: "logs/deep-review/2026-05-27-15-deep-review.md"
task9_review_notes: "2026-05-27 15:22 Task9 deep-review：技术复审无新增 P0/P1；既有 queue pending 为 Task6/Task2B 文末源码调研原始块清理，不自动晋升。"
---

# 1.14 锁竞争与同步性能分析

<!-- outline-start -->
## 要点

### 🔹 锚点 1：先把四类等待分开
- Java monitor：`synchronized`、`wait()` / `notify()`，底层是 ART monitor
- Native mutex / condition variable：`pthread_mutex`、`std::mutex`、`ConditionVariable`
- Binder driver wait queue：跨进程调用的等待与唤醒，由 binder driver 管理，不等同于 Java 锁
- MessageQueue / DeliQueue：主线程消息投递路径的串行化问题，需要和前面三类区分
- 无竞争 CAS 很便宜，一旦进入睡眠路径，成本就会跳到上下文切换级

### 🔹 锚点 2：Monitor Lock 的实现与性能特征
- `synchronized` 对应 `monitorenter` / `monitorexit`，由 ART monitor 实现
- 对象头 lock word 支持 `Unlocked → Thin Locked → Fat Monitor` 状态转换
- 发生竞争或调用 `wait()` 时会从 thin lock 膨胀为 fat monitor
- `kLongWaitMs = 100ms` 的长等待日志可直接帮助定位严重竞争
- Perfetto 的 `android.monitor_contention` 模块可直接查询 owner / waiter 关系

### 🔹 锚点 3：Futex 与 Linux 同步原语
- futex 的核心思路是“用户态快速路径，内核态慢速路径”
- `FUTEX_WAIT` / `FUTEX_WAKE` 是 Java monitor 和 native mutex 睡眠路径的基础
- bionic 在 `android-9.0.0_r1` 已提供 `pthread_mutexattr_setprotocol(..., PTHREAD_PRIO_INHERIT)`
- 但“系统支持 PI mutex”不等于“具体锁路径已经启用 PI-futex”
- Binder 的等待与唤醒要单独看 binder driver 的 wait queue 和事务优先级逻辑

### 🔹 锚点 4：优先级反转要按子系统拆开看
- 经典模式：低优先级线程持锁，中优先级线程抢占，高优先级线程饿死
- Java monitor、native mutex、Binder 事务等待都可能出现优先级反转，但处理手段不同
- Linux 提供 PI-futex，这是一种可选机制，不是所有 Android 子系统都统一采用
- Android 官方音频文档明确提醒，实时路径不一定适合直接依赖 PI-futex
- Binder 更应该看 `binder_transaction_priority()` 这类驱动侧优先级传播逻辑

### 🔹 锚点 5：Binder 框架中的锁竞争
- `ProcessState.cpp` 在 `android-7.1.2_r39` 和 `android-8.0.0_r1` 都把 `DEFAULT_MAX_BINDER_THREADS` 定义为 15
- Binder 调用卡住时，调用方常常睡在 `binder_thread_read` 或 reply 等待上
- 瓶颈经常在服务端对象锁，如 `WindowManagerGlobalLock`、AMS/PMS 全局锁
- Binder 线程池耗尽会把“一个服务慢”放大成“整批调用都慢”

### 🔹 锚点 6：在 Perfetto 中怎么区分这几类问题
- Java monitor：看 `android.monitor_contention` 和 Thread / Lock contention track
- Native mutex：看 `thread_state.blocked_function` 里的 `futex_*`，再反推 owner 线程
- Binder wait queue：看 `binder_thread_read`、binder transaction/reply，以及目标进程 Binder worker 是否打满
- system_server 场景要同时看 Binder worker 和服务线程，不要只盯住调用方主线程
- SQL 要用真实模块名 `android.monitor_contention`

### 🔹 锚点 7：锁竞争优化的系统级策略
- 先缩短临界区，再考虑换锁，再考虑无锁
- 读多写少场景优先考虑读写分离，不要上来就全局大锁
- Binder 事务里不要把 I/O、跨服务调用、长计算塞在持锁区间
- DeliQueue 是“先消掉主线程生产者锁竞争，再保留单消费者排序”的代表案例
- 无锁不等于零成本，CAS 重试和 cache line bouncing 也会吃掉收益

### 🔹 锚点 8：版本演进中的锁优化
- Android 5.0：Java monitor 讨论应以 ART 的 monitor / lock word 实现为准
- Android 7.1.2 与 8.0：Binder worker 默认上限都是 15，8.0 不是“8→16”的分水岭
- Android 9：bionic 已具备 PI mutex 属性接口，是否启用取决于具体 mutex 配置
- Android 17：DeliQueue 把 MessageQueue 生产者路径改为无锁，Google 公布主线程 lock contention time 下降 15%

## 🔸 扩展 1：常见问题与误区
- `synchronized` 和 `ReentrantLock` 不是简单的快慢关系，先看竞争形态，再看可中断/超时/公平性需求
- 看到 `futex_wait` 不等于一定是 Java 锁，native mutex 和条件变量也会走同一类睡眠路径
- 主线程卡在 Binder 上，不代表服务端一定在“算得慢”，也可能是在等服务端对象锁或等 Binder worker
- 无锁结构能消掉阻塞，但不保证总是更快，高竞争下 CAS 重试一样会放大开销
- PI 机制不是万灵药，是否值得引入要看实时性目标、信任模型和实现代价

## 🔸 扩展 2：与其他机制的关系
- **1.4 Binder IPC**：回答“跨进程调用怎么走”，本节回答“为什么调用会在等待里耗时”
- **1.5 线程模型**：决定谁是 owner、谁是 waiter，以及谁会被谁抢占
- **1.13 DeliQueue**：展示 MessageQueue 这条具体路径如何从 monitor 迁移到无锁生产者模型
- **2.4 / 2.5 渲染调度**：主线程或 RenderThread 一旦被锁竞争拖住，就会直接变成掉帧
- **7.1 / 9.1**：卡顿和 ANR 最终都需要回到“关键线程为什么没有继续运行”这个问题

## 🔸 扩展 3：读者诊断清单
- 先分清等待类型，再决定工具，不要把所有等待都当成“锁竞争”
- 先看调用方，再看 owner，再看 owner 是否又在等别人
- 先判断是同进程锁还是跨进程 Binder，再决定改线程模型还是改 IPC 设计
- 先用 Perfetto 找最长等待，再回 AOSP 或业务代码找持锁区间
- 修复后必须回到 trace 验证，确认等待时间和关键线程调度都真的变短了
<!-- outline-end -->

## 为什么锁是性能分析的核心议题

Perfetto 里最容易让人误判的一类问题，是线程看起来“没在跑代码”，但一帧还是掉了，或者启动还是慢了。把时间轴放大以后，通常会看到主线程、RenderThread，或者 Binder worker 停在 Waiting / Sleeping 状态。接下来要回答的是：它到底在等哪一种等待。

如果把 Java monitor、native mutex、Binder driver wait queue、MessageQueue 自身的串行化问题都混成“同一种锁”，后面的诊断就会一路跑偏。Java monitor 要看 ART monitor；native 锁要看 `pthread_mutex` / `ConditionVariable`；Binder 要看驱动侧 wait queue 和服务端对象锁；MessageQueue 则要单独看主线程消息投递路径。把这四类路径分开，才能知道该去查哪段代码、该看哪个 track、该改哪一种设计。

锁问题之所以常常直接变成 jank 或 ANR，是因为一旦从用户态的 CAS 快速路径掉进睡眠路径，成本就会立刻跳到上下文切换级。关键线程如果在错误的地方睡下去，16.6ms 的帧预算和 5s 的 ANR 窗口都会很快被吃光。

## Android 中的锁类型全景

先把 Android 里最常见的四类等待拆开。

第一类是 **Java monitor**。`synchronized`、`wait()`、`notify()` 这一套都属于它。它的关键点是 ART 怎样把对象头里的 lock word、竞争升级和等待队列组织起来。Perfetto 的 `android.monitor_contention` 模块就是专门为这条路径准备的。

第二类是 **native mutex / condition variable**。这类等待经常出现在 RenderThread、SurfaceFlinger、AudioFlinger，以及系统服务的 C++ 代码里。表面上看，trace 里它和 Java monitor 一样也会出现 `futex_*`，但 owner、调用栈、锁对象全都不一样。看见 `futex_wait`，不能自动把它判成 Java 锁。

第三类是 **Binder driver wait queue**。跨进程调用时，调用方常常睡在 `binder_thread_read` 或 reply 等待上。这里要看的是 Binder worker 有没有空、目标服务是不是被对象锁卡住、驱动是不是还在排队分发事务。

第四类是 **MessageQueue / DeliQueue**。这是主线程消息投递路径的特例。它和 Binder、native mutex 都不一样，因为它讨论的是主线程内部事件循环怎样接收来自多个生产者的消息。Android 17 的 DeliQueue 把这里的生产者路径改成无锁，就是因为这条路径足够高频，足够容易把高优先级线程拖进等待里。

这四类路径的共同点只有一个，都是“等待”。差异在于等待对象、唤醒机制、Perfetto 表现和优化手段都不同。

## Monitor Lock 的实现细节

`synchronized` 的底层是 ART monitor，不是什么抽象的“Java 锁”。对象头里的 lock word 先尝试走 thin lock，只有在竞争出现，或者调用 `wait()` 这类需要等待队列的操作时，才会膨胀成 fat monitor。`art/runtime/lock_word.h` 里定义了 `Unlocked`、`ThinLocked`、`FatLocked` 这些状态，`art/runtime/monitor.cc` 里则能看到 monitor 进入、膨胀和等待的实际实现。[已验证: AOSP android-16.0.0_r1, `art/runtime/monitor.cc` + `art/runtime/lock_word.h`]

这条设计解释了为什么“无竞争的 `synchronized`”和“竞争下的 `synchronized`”完全不是一个量级。前者基本上是一次对象头 CAS，后者要创建 fat monitor、进入等待队列、让线程睡眠，再等待别人把它唤醒。`wait()` 也会强制这条路径进入 fat monitor，因为只有 fat monitor 才有完整的等待集合。

ART 还提供一个明确的观测点。`monitor.cc` 里的 `kLongWaitMs` 设为 100ms，等待超过这个阈值会打出长等待日志。Perfetto 的 monitor contention 轨和 SQL 标准库，正是围绕这类事件组织起来的。换句话说，Java monitor 这条路径不是“只能靠猜”，它有明确的数据面。

## Futex：用户态与内核态的桥梁

futex 的价值在于把“无竞争时的原子操作”和“有竞争时的线程睡眠”连在一起。无竞争时，线程只在用户态改一个共享字，几乎不需要内核介入；竞争出现后，再通过 `FUTEX_WAIT` / `FUTEX_WAKE` 进入慢速路径。ART monitor、bionic 的 `pthread_mutex`、条件变量，都会建立在这套机制上。

但这里有一个很容易写错的地方。**“系统支持 futex”不等于“所有等待都叫 futex 锁竞争”，也不等于“具体锁路径启用了 PI-futex”。** `android-9.0.0_r1` 的 bionic 里已经提供 `pthread_mutexattr_setprotocol(..., PTHREAD_PRIO_INHERIT)`，这说明 native mutex 层具备 PI mutex 能力；可它只说明“可以这样配置”，并不说明系统里每一把 mutex 都真的这么配了。[已验证: AOSP android-9.0.0_r1, `platform/bionic/libc/bionic/pthread_mutex.cpp`]

Binder 更不能直接写成 “Binder = futex / PI-futex”。Binder 的等待和唤醒主要由 binder driver 的 wait queue、事务分发和线程选择逻辑处理。驱动里需要重点核对的入口，是 `binder_transaction_priority()`、`binder_select_thread_ilocked()`、`binder_wakeup_thread_ilocked()` 这一类函数，而不是把它硬套到 Java monitor 的语义里。[已验证: kernel/common `drivers/android/binder.c`]

## 优先级反转：从模型到 Android 现场

优先级反转的模式很简单，低优先级线程持有关键资源，中优先级线程抢占 CPU，高优先级线程反而拿不到锁。麻烦在于，它在 Android 里不只发生在一种锁上。

如果是 Java monitor，典型现象是主线程等一个后台线程释放对象锁。线程明明不忙，却一直在等。 如果是 native mutex，常见位置会出现在 SurfaceFlinger、RenderThread、Audio 等实时或半实时路径。 如果是 Binder，现象更容易绕，调用方看上去像是在等 IPC，根因却可能是服务端 Binder worker 拿着全局锁，又被别的线程抢占了。

Linux 提供 PI-futex，是为了解决这类问题的一种机制。但 Android 官方关于音频延迟与 priority inversion 的文档讲得很直白，实时路径不一定适合直接依赖 PI-futex，因为系统调用成本、信任模型和 DoS 风险都要算进去。所以更稳妥的写法应限定为：“Linux 与 bionic 提供了这类机制，具体是否启用要按子系统、按锁类型核实”，不要扩写成“Android 某某子系统统一用了 PI-futex”。[已验证: `source.android.com/docs/core/audio/latency/priority-inversion`]

Binder 这一侧也应该分开写。它要看的重点是驱动怎样给事务传播优先级，怎样挑 Binder worker，怎样唤醒等待线程。把“Binder transaction priority inheritance”和“Java / ART monitor 等待”混成一条实现链，读者到了 trace 现场基本一定会判断错。

SurfaceFlinger 和 InputDispatcher 不能直接写成“Android 14+ 全面启用 PI-futex”。公开源码里，SurfaceFlinger 常见的 `mStateLock` 路径经 `android::Mutex` 默认初始化，InputDispatcher 主分发路径使用 `std::mutex`；这些锚点本身不足以证明已配置 `PTHREAD_PRIO_INHERIT`。在 Perfetto 中观察到 SF 或 Input 路径锁等待异常时，仍要回到 owner / waiter、调用栈和具体锁初始化代码核对，不要把“内核支持 PI-futex”扩写成“该子系统核心锁已启用 PI”。[已确认: 2026-05-18 Task9 抽检]

## Binder 框架中的锁竞争

Binder 的问题，通常不是“调用慢”这四个字能概括的。调用方睡在 Binder 上，只说明它在等目标进程；瓶颈常常在服务端对象锁、Binder worker 数量，或者服务端 worker 持锁时又去做了别的慢操作。

`ProcessState.cpp` 在 `android-7.1.2_r39` 和 `android-8.0.0_r1` 两个 tag 里都把 `DEFAULT_MAX_BINDER_THREADS` 定义为 15。所以“Android 8 把 Binder 默认线程从 8 提到 16”这个说法站不住脚。常见 Binder worker 上限长期稳定在 15 个工作线程，外加调用上下文里能看到的主线程或主 Binder 线程，trace 里才会让人形成“像是 16 条线程”的体感。[已验证: AOSP `frameworks/native/libs/binder/ProcessState.cpp` at `android-7.1.2_r39` / `android-8.0.0_r1`]

system_server 里的典型热点在服务端全局锁，不在 Binder 驱动本身。比如 WindowManager 的 `WindowManagerGlobalLock`，AMS/PMS 的大对象锁，都会把一个 Binder 调用拖成一整串等待。调用方主线程睡在 `binder_thread_read`，服务端 Binder worker 可能睡在 `futex_wait`，而持锁的 owner 线程可能又在跑磁盘 I/O、跨服务调用，或者干脆在等另一把锁。只看调用方只能看到结果；把 Binder worker 和 owner 一起看，根因才会露出来。

这就是为什么 Binder 场景里要同时看三层信息，调用方在等什么，服务端 worker 在干什么，持锁线程是不是又被别人卡住了。少看一层，就会把跨进程等待误判成“单点慢函数”。

## 在 Perfetto 中识别锁竞争

Perfetto 里分析锁竞争，先做分类，再做归因。

**第一步，判断是不是 Java monitor。** 如果 trace 打开了相关数据源，可以直接用 `android.monitor_contention` 模块看 owner / waiter 关系，而不是先去翻 raw slice 名字。

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  process_name,
  blocked_thread_name AS waiter_thread,
  blocking_thread_name AS owner_thread,
  short_blocked_method AS waiter_method,
  short_blocking_method AS owner_method,
  CAST(dur / 1e6 AS FLOAT) AS wait_ms
FROM android_monitor_contention
WHERE process_name = 'system_server'
ORDER BY dur DESC
LIMIT 20;
```

这条查询直接给出等待线程、持锁线程和等待时长。它适合查 Java monitor，尤其适合 system_server 这类 owner / waiter 链比较复杂的场景。这里的模块名必须是 `android.monitor_contention`，不是 `android.monitor`。[已验证: Perfetto stdlib `android/monitor_contention.sql`]

**第二步，判断是不是 native mutex / condition variable。** 这类等待通常不会出现在 `android_monitor_contention` 里，而会反映在 `thread_state.blocked_function` 的 `futex_*`、`__futex_wait` 一类函数上。它们说明线程睡下去了，但不会直接标出锁对象。这个时候要结合 owner 线程的调用栈、同进程其他线程状态一起看。

**第三步，判断是不是 Binder wait queue。** 如果主线程或 Binder caller 线程长时间停在 `binder_thread_read`、binder reply 或事务等待上，不要直接说“服务端处理慢”。先看目标进程 Binder worker 有没有打满，再看这些 worker 是在 Running、在 `futex_wait`，还是在别的 Binder 调用里。

下面这条 raw SQL 更适合扫 native mutex 和 Binder driver 两种等待：

```sql
SELECT
  process.name AS process_name,
  thread.name AS thread_name,
  thread_state.state,
  thread_state.blocked_function,
  CAST(thread_state.dur / 1e6 AS FLOAT) AS blocked_ms
FROM thread_state
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name IN ('system_server', 'surfaceflinger')
  AND thread_state.blocked_function IS NOT NULL
  AND (
    thread_state.blocked_function GLOB 'futex*' OR
    thread_state.blocked_function GLOB 'binder*'
  )
ORDER BY thread_state.dur DESC
LIMIT 40;
```

如果在 system_server 里同时看到这些现象，主线程或 App 线程睡在 binder，system_server 的 Binder worker 又睡在 `futex_*`，并且 `android_monitor_contention` 里能看到 `WindowManagerGlobalLock` 之类的大锁，那基本就能判断这是“Binder 调用被服务端对象锁拖慢”，而不是“调用方自己代码慢”。这条诊断路径能把调用方等待、服务端对象锁和 Binder worker 状态连起来。

## 锁竞争优化的系统级策略

锁优化别一上来就谈无锁。更稳的顺序是，先缩短临界区，再减少共享范围，再考虑换锁或无锁。

如果问题出在 Java monitor，优先把耗时操作搬出 `synchronized`，把大对象锁拆小。Android 16 起，ART 的逃逸分析已经能自动消除线程私有对象上的冗余 `synchronized` 指令——比如局部变量中的 `StringBuffer` 锁。如果 trace 里的 monitor contention 消失了但问题仍在，要考虑是否被编译器静默优化过。 如果问题出在 native mutex，要看是不是把计算、I/O、等待别的条件也塞进了持锁路径。 如果问题出在 Binder，重点是避免 Binder worker 持锁时再去做跨服务调用、磁盘 I/O，或者长时间等待。 Binder 事务的持锁区间一旦拉长，整个线程池都会跟着排队。

Android 17 的 DeliQueue 是这类优化的一个案例。它面向 targetSdk 37+ 应用，把多生产者插入路径改成无锁，单消费者排序和消费继续留给 Looper 自己处理。Google 给出的数据是，主线程花在 lock contention 上的时间下降 15%，应用 missed frames 下降 4%，SystemUI / Launcher 的 missed frames 下降 7.7% 到 9.1%。这组数据只支撑 MessageQueue 生产者路径的优化收益，不能外推到其他锁路径。[已验证: Android Developers Blog, 2026-02-17 DeliQueue]

无锁也没有免费收益。CAS 重试、cache line bouncing、生产者突发写入带来的 drain 压力，都会把收益吃回去。所以 trace 里看见“没有 monitor contention 了”，并不代表问题自然消失，还要继续看 CPU 时间、owner 行为和关键线程延迟有没有一起变好。

## 版本演进中的锁优化

| 版本 | 可以确认的变化 | 对分析的意义 |
|------|----------------|--------------|
| Android 5.0 | Java monitor 的讨论应以 ART `monitor.cc` / `lock_word.h` 为准 | 讨论 `synchronized` 时，不要再沿用 Dalvik 时代的实现想象 |
| Android 7.1.2 / 8.0 | `ProcessState.cpp` 两个 tag 的 `DEFAULT_MAX_BINDER_THREADS` 都是 15 | “Android 8 把 Binder 线程从 8 提到 16”这个说法不成立 |
| Android 9 | bionic 已提供 `pthread_mutexattr_setprotocol(..., PTHREAD_PRIO_INHERIT)` | 说明 native 层具备 PI mutex 能力，但是否真的启用要看具体锁属性 |
| Android 16 | ART 强化逃逸分析，可自动消除线程私有对象上的冗余 `synchronized` 指令（如局部变量中的 `StringBuffer` 锁） | 分析 monitor contention 时，如果对象是方法局部变量且未逃逸，可能已被编译器移除，trace 里不会出现 | 
| Android 14+ | 未找到公开源码证据证明 SurfaceFlinger / InputDispatcher 核心锁“全面启用 PI-futex” | 分析 SF/Input 路径锁等待时，要按具体锁初始化代码核对，不能按版本直接假设 PI 保护 |
| Android 17 | DeliQueue 把 targetSdk 37+ 应用的 MessageQueue 生产者路径改成无锁 | 分析主线程消息投递等待时，要把 Android 17 targetSdk 37+ 与旧行为分开看 |

## 常见问题与误区

### 1. `synchronized` 一定比 `ReentrantLock` 慢吗

不是。无竞争时，两者都可能非常快。决定差距的，往往是竞争形态、是否需要可中断/超时、公平性，以及是否把慢操作塞进持锁区间。先看 trace，再决定换不换锁。

### 2. 看到 `futex_wait` 就能断定是 Java 锁吗

不能。Java monitor、native mutex、条件变量都会在竞争后走到类似的睡眠路径。没有 `android_monitor_contention` 的 owner / waiter 数据，或者没有对应 native 调用栈时，不能只凭一个 `futex_*` 就下判断。

### 3. 主线程卡在 Binder 上，就一定是对端服务慢吗

也不能这么写。主线程睡在 Binder 上，只说明它在等对端结果。对端慢，可能是业务逻辑慢，也可能是 Binder worker 不够、全局锁冲突、持锁线程又在等别人。Binder 场景里，单看调用方基本不够。

### 4. 无锁一定更快吗

不一定。无锁消掉的是阻塞，不是成本本身。高竞争下的 CAS 重试、共享缓存行抖动，同样会变成热点。DeliQueue 之所以成立，是因为它只把最容易出问题的“多生产者插入路径”改成无锁，没有把整套消息处理全部重写成 lock-free。

### 5. PI 机制能一次性解决优先级反转吗

不能。PI-futex 只是一种机制，而且有使用前提和代价。不同子系统对实时性、信任模型、可维护性的要求不同。写技术文档时，最忌讳的就是把“内核支持 PI”直接扩写成“系统所有关键锁都用了 PI”。

## 与其他机制的关系

锁竞争从来不是孤立的问题。它和线程模型绑在一起，因为优先级、调度类、owner / waiter 关系都来自线程模型；它和 Binder 绑在一起，因为很多“看起来像 IPC 慢”的问题，根因是服务端对象锁；它和渲染调度绑在一起，因为主线程、RenderThread 一旦被等待拖住，掉帧会直接出现在 `doFrame` 预算里；它和 ANR 绑在一起，因为 5 秒超时统计的本质，就是关键线程有没有继续推进。

这一节不要求背几种锁名字，重点是建立诊断习惯。看到等待，先问是哪条路径；看到主线程卡住，先找 owner；看到 owner，再问它是不是又在等别人。顺着这条链往下查，锁竞争问题通常都能落到具体代码和具体线程上。

## 读者诊断清单

1. **先抓对 trace。** 至少带上 `sched`、Binder 相关事件，以及能支持 monitor contention 分析的数据源。没有线程状态和 owner / waiter 信息，后面只能猜。
2. **先给等待分类。** `android_monitor_contention` 命中的是 Java monitor；`futex_*` 但没有 monitor 数据，多半是 native mutex / condvar；`binder_thread_read` / binder reply 则先按 Binder 路径查。
3. **先找 owner，再找 owner 的 owner。** 调用方不是根因。让等待拉长的，往往是持锁线程自己又被别的资源拖住了。
4. **system_server 要双向看。** 一边看 App 或调用方主线程，一边看 system_server 的 Binder worker、服务线程和全局锁。只看一边，结论很容易少一层。
5. **修完必须回 trace。** 只把锁换了还不够，还要确认关键线程等待时间、Binder 排队时间、帧预算占用都真的降下来了。

## 小结

锁竞争分析难的地方在于，不同等待路径长得太像，特别容易被混写。把 Java monitor、native mutex、Binder driver wait queue、MessageQueue 这四类路径拆开，再回到 Perfetto 里看线程状态、owner / waiter、Binder worker 和关键线程预算，很多原本糊成一团的问题就会变得非常具体。到这一步，优化才会变成有目标的修改。

[需重写: 文末仍保留源码调研原始块，需判断哪些内容已进入正文，剩余素材移入素材库或合并后删除。]

<!-- AIW-源码调研-2026-05-06 -->
## 补充：AMS mGlobalLock / mProcLock 双锁架构与 Perfetto 识别

本节于 2026-05-06 通过源码调研补充，聚焦 Android 10+ 双锁架构及其在 Perfetto 中的识别路径。

### 双锁架构演进

| 版本 | 锁配置 | 关键变化 |
|------|--------|---------|
| Android 9- | 单一全局锁（AMS.this） | 所有组件竞争同一锁 |
| Android 10-11 | mGlobalLock + mProcLock | 读写分离，ENABLE_PROC_LOCK 可能为 false |
| Android 12+ | mGlobalLock + mProcLock | ENABLE_PROC_LOCK 恒为 true，双锁完全并行 |

**源码锚点**：`ActivityManagerService.java` 行 668-707（android14-release）
```java
final ActivityManagerGlobalLock mGlobalLock = ActivityManagerService.this;
private static final boolean ENABLE_PROC_LOCK = true;
final ActivityManagerProcLock mProcLock = ENABLE_PROC_LOCK
        ? new ActivityManagerProcLock() : mGlobalLock;
```

### @CompositeRWLock 读写语义

```java
@CompositeRWLock({"this", "mProcLock"})
int getUidState(int uid) { ... }
```
- **读取**：持有 `this`（mGlobalLock）或 `mProcLock` 任一即可
- **写入**：需同时持有两者

### mGlobalLock 热区函数

| 函数 | 行号 | 触发场景 |
|------|------|----------|
| `updateOomAdjLocked()` | 567 | OomAdjuster 回调，每帧可达多次 |
| `attachApplicationLocked()` | 4920 | 进程绑定/启动 |
| `serviceTimeoutLocked()` | ~1810 | Service ANR 判定 |
| `processStartTimedOutLocked()` | ~3425 | App 启动超时 |

### mProcLock 职责

`mProcLock` 主要保护进程状态读取（LRU list、ProcessRecord 读写），由 `OomAdjuster.updateOomAdjLSP()` 使用：
```java
// OomAdjuster.java 行 574-595
mProcessList.forEachLruProcessesLOSP(false, process -> {
    // mProcLock 保护的遍历
});
```

### Perfetto 识别模式

```
binder_transaction (thread: system_server binder #N, duration: >16ms)
  → android.os.Binder.execTransact()
    → ActivityManagerService.onTransact()
      → updateOomAdjLocked() 或 attachApplicationLocked()
        → [synchronized(mGlobalLock/mProcLock) 持锁等待]
```
当 `binder_transaction` duration 超过单帧（>16.67ms@60Hz）且 call stack 包含 AMS 内部同步块，即为锁竞争根因。关键 trace points：`binder_transaction`、`ActivityManagerService.updateOomAdjLocked`、`ActivityManagerService.attachApplicationLocked`。

> 本调研同步更新至 §1.8 AMS 章节原始素材。

<!-- AIW-源码调研-2026-05-06 END -->



<!-- AIW-源码调研-2026-05-09: PI-Mutex 实现细节补充 -->

## PI-Mutex 实现细节补充（源码级）

> 本节补充 2026-05-09 源码调研成果，关于 Bionic `pthread_mutex` 的 `PTHREAD_PRIO_INHERIT` 实现及 32 位架构限制。

### Bionic PI-Mutex 协议配置接口

Bionic 从 `android-9.0.0_r1` 起提供完整的 PI-Mutex 属性接口：

```cpp
// bionic/libc/include/pthread.h
// @ AOSP android-9.0.0_r1
#define PTHREAD_PRIO_NONE        0
#define PTHREAD_PRIO_INHERIT     1  // 继承等待者最高优先级
```

`pthread_mutexattr_setprotocol(attr, PTHREAD_PRIO_INHERIT)` 设置后，后续 `pthread_mutex_init()` 创建的 mutex 才会请求优先级继承协议。`PTHREAD_PRIO_PROTECT` 不在这些公开 tag 的 bionic `pthread.h` 可用协议里，文档中不要把 POSIX 可选协议直接写成 Android 已实现能力。

### PI-Futex 与普通 Futex 的区别

**普通 futex 等待**（`FUTEX_WAIT` / `FUTEX_WAKE`）：
- 内核以 FIFO 顺序维护 wait queue
- 不涉及优先级调度
- Perfetto 中表现为 `futex_wait` / `futex_wake`

**PI-futex 等待**（`FUTEX_LOCK_PI` / `FUTEX_UNLOCK_PI`）：
- 内核以 priority order 维护 wait queue（按优先级排序）
- 持锁线程优先级被动态提升
- Perfetto 中表现为 `futex_wait_requeue_pi`
- `FUTEX_UNLOCK_PI` 时内核自动唤醒最高优先级等待者

关键差异：PI-futex 的 `FUTEX_UNLOCK_PI` 语义保证"持锁线程释放时最高优先级等待者立即被唤醒"，不需要额外的 wake 操作。

### 32 位架构 owner TID 编码边界

PI futex 的用户态 word 里会编码 owner TID。bionic 在 32 位 ABI 上对 `pthread_mutex_t` 的布局更紧，公开实现里有 owner tid 编码位数的限制；讨论这类边界时，应写成“32 位 ABI 下 owner TID 编码空间有限，需要按 bionic tag 核对”，不要写成 `android_pid_t` / `ANDROID_PID_MAX` 或“Android 12+ 64-bit PID 修复”。当前公开 AOSP 证据不足以支撑这些符号和版本结论。

### SurfaceFlinger / InputDispatcher 锁路径核对

Task9 抽检没有在公开 AOSP 锚点中确认 SurfaceFlinger / InputDispatcher 核心锁统一启用 PI-futex。可确认的边界是：bionic 支持 `PTHREAD_PRIO_INHERIT`，但具体锁是否启用取决于初始化属性；SurfaceFlinger、InputDispatcher 这类路径要逐个看 `pthread_mutexattr_setprotocol()`、`android::Mutex` 初始化参数或 `std::mutex` 实现，不能按模块名推断。

Perfetto 里出现 SF / Input 相关锁等待时，排查顺序仍然是 owner / waiter、线程优先级、持锁期间调用栈和被等待资源。只有源码锚点能证明该锁启用了 PI，才把优先级继承纳入结论。
