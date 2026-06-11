---
title: "SurfaceFlinger Transaction Queue 无锁架构与消息分流"
chapter: "2.27"
status: ready-for-review
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
drafted_date: "2026-06-11"
last_verified: "2026-06-11"
last_verified_against: "AOSP android-16.0.0_r4"
confidence: high
tags: ['SurfaceFlinger', 'LocklessQueue', 'Transaction', 'MPSC', '渲染管线']
related_chapters: ["2.6", "2.22", "2.23"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
gap_source: "DeepResearch 调研结果（score 17）+ AOSP 源码结构"
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/LocklessQueue.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrontEnd/TransactionHandler.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrontEnd/TransactionHandler.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BLASTBufferQueue.cpp"
  - type: research
    path: "DeepResearch/2026-06-08-android-17-sf-transaction-queue-lockless-architecture.md"
---

# 2.27 SurfaceFlinger Transaction Queue 无锁架构与消息分流

<!-- outline-start -->
## 要点

### 🔹 锚点 1：LocklessQueue<T> 无锁 MPSC 队列实现
LocklessQueue 使用 compare_exchange_weak CAS 操作维护链表头，push 路径不依赖 mutex，多 binder 线程并发入队不阻塞。pop 通过 mPush.exchange(nullptr) 原子夺取整条链表并就地反转后串行消费。

### 🔹 锚点 2：TransactionHandler 事务批处理流水线
flushPendingTransactionQueues + 多 TransactionFilter 回调实现事务批处理。过滤维度包括时间、buffer barrier、unsignaled fence，未就绪事务留在 mPendingTransactionQueues 等待下次 flush。

### 🔹 锚点 3：setTransactionState 到 applyTransactionState 的落地路径
SurfaceFlinger::setTransactionState 现在只在事务被 applyToken 驱动时才进入 applyTransactionState 落地。期间不持 mStateLock 全局临界区，减少主线程与 binder 线程的锁争用。

### 🔹 锚点 4：FrontEnd 重构后的事务状态拆分
FrontEnd 将客户端提交的事务与合成时读取的状态完全解耦。事务不再直接操作 Layer，而是先入 LocklessQueue 再由主线程批量 drain 过滤后落地。mCurrentState/mDrawingState 双缓冲在新的架构下的角色变化。

### 🔹 锚点 5：BLASTBufferQueue 与 SurfaceFlinger 侧的缓冲区拉取
BLASTBufferQueue 作为 SurfaceFlinger 拉取 buffer 的接口：acquireNextBufferLocked、releaseBufferCallback 承担缓冲区生命周期。与 TransactionQueue 的协作关系。

### 🔹 锚点 6：LocklessQueue vs mutex+condvar 的性能对比
无锁队列省掉 futex 系统调用，避免主线程被 binder 线程争用阻塞。在高并发事务场景（多窗口、桌面模式）下的延迟改善量化分析。

### 🔹 锚点 7：从 Android 15 到 17 的 Transaction 架构演进
Android 15 的 mutex 事务队列 → 16 的 LocklessQueue 引入 → 17 的 TransactionFilter 深化。各版本中事务处理路径的变化与性能影响。

## 扩展

### 🔸 扩展点 1
LocklessQueue 在多窗口/桌面模式高并发事务下的 Perfetto 观察方法

### 🔸 扩展点 2
TransactionFilter 自定义过滤策略的扩展接口与 OEM 定制场景

### 🔸 扩展点 3
SF Transaction Queue 与 Choreographer VSync 对齐的时序关系

<!-- outline-end -->

## 为什么单独讲 Transaction Queue 的无锁架构

§2.22 讲了 FrontEnd 如何把客户端请求状态和合成输入状态拆开，TransactionHandler 作为 FrontEnd 的入口组件负责接收和过滤事务。那一节覆盖了 `TransactionHandler` 的就绪判断逻辑和 `TransactionReadiness` 四种状态。

本节聚焦一个更底层的工程问题：`TransactionHandler` 用什么数据结构接收来自多个 binder 线程的并发事务，以及这个选择对 SurfaceFlinger 主线程延迟的影响。

Android 16 引入的 `LocklessQueue<T>` 是一个无锁 MPSC（Multi-Producer Single-Consumer）队列。在它之前，SurfaceFlinger 用 `std::mutex` 保护事务入队路径，binder 线程和主线程在事务队列上存在锁争用。引入 `LocklessQueue` 之后，binder 线程入队只做一次 CAS 操作，不再进入内核态等待 futex，主线程消费时也不需要加锁。

这条改动的影响范围是：多窗口场景下大量 SurfaceControl 事务并发到达 SurfaceFlinger 时，主线程在 `commit` 阶段因为锁等待造成的延迟。

[已验证: AOSP android-16.0.0_r4, `LocklessQueue.h`]

## LocklessQueue 的实现

### 链表式 MPSC 队列

`LocklessQueue<T>` 的核心是两个原子指针：`mPush` 指向链表头（生产者端），`mPop` 指向反转后的消费端。

[已验证: AOSP android-16.0.0_r4, `frameworks/native/services/surfaceflinger/LocklessQueue.h`]

```
push 路径（binder 线程调用）:
  entry->mNext = mPush.load()        // 读当前链表头
  compare_exchange_weak(mPush, entry) // CAS 把 entry 换到链表头
  // CAS 失败时 previousHead 自动更新为最新值，循环重试

pop 路径（SurfaceFlinger 主线程调用）:
  1. 如果 mPop 非空，直接取 mPop 节点返回
  2. 如果 mPop 为空，mPush.exchange(nullptr) 原子夺取整条链表
  3. 反转链表（因为 push 是头插法，链表顺序和入队顺序相反）
  4. 反转后的头部存入 mPop，逐个返回
```

几个设计约束：

- **多生产者安全**：多个 binder 线程可以同时调用 `push`，`compare_exchange_weak` 保证链表头更新的原子性。CAS 失败的线程自动重试，不会阻塞。
- **单消费者**：`pop` 只由 SurfaceFlinger 主线程调用。`mPush.exchange(nullptr)` 把整条链表一次性拿走，之后主线程在本地反转和消费，不需要任何同步操作。
- **无系统调用**：整个 push/pop 路径不进入内核态，不调用 futex。和 `std::mutex` 的 `lock()/unlock()` 相比，省掉了持锁期间的上下文切换开销。

### 与旧架构的对比

Android 15 及之前，事务入队使用 `std::mutex` + `std::queue`（或等价的互斥保护容器）。入队流程是：

```
旧路径:
  binder 线程 → lock(mutex) → queue.push(state) → unlock(mutex)
  主线程    → lock(mutex) → queue.pop() → unlock(mutex)
```

当多个 binder 线程同时提交事务（多窗口、动画、转场），binder 线程之间、binder 线程与主线程之间会在同一个 mutex 上争用。争用到一定程度后，`lock()` 调用会触发 futex 系统调用，把当前线程挂起等待锁释放。

新路径下，binder 线程只做一次 CAS 就完成入队，不和主线程或其他 binder 线程发生互斥等待：

```
新路径:
  binder 线程 → CAS(mPush, entry)            // 无锁
  主线程    → mPush.exchange(nullptr) + 反转  // 无锁，批量取走
```

| 对比维度 | std::mutex + queue | LocklessQueue |
| --- | --- | --- |
| 入队操作 | lock → push → unlock | CAS（用户态） |
| 出队操作 | lock → pop → unlock | exchange + 本地反转 |
| 系统调用 | 高争用时触发 futex | 无 |
| 多生产者安全性 | mutex 保证 | CAS 保证 |
| 适用场景 | 通用 | MPSC，单消费者 |

[已验证: AOSP android-16.0.0_r4, `LocklessQueue.h`]

## TransactionHandler 的双层队列

### 从 LocklessQueue 到 per-applyToken 队列

`TransactionHandler` 维护两层队列：

1. **`mLocklessTransactionQueue`**：`LocklessQueue<QueuedTransactionState>` 实例，binder 线程直接写入。
2. **`mPendingTransactionQueues`**：`std::unordered_map<sp<IBinder>, std::queue<QueuedTransactionState>>`，按 `applyToken` 分桶的 FIFO 队列。

[已验证: AOSP android-16.0.0_r4, `TransactionHandler.h`]

处理流程：

```
collectTransactions():
  while (auto state = mLocklessTransactionQueue.pop()) {
      mPendingTransactionQueues[state->applyToken].push(std::move(*state));
  }
```

`collectTransactions()` 把 `LocklessQueue` 中的事务全部排空，按 `applyToken` 分配到对应的 FIFO 队列。这一步把无锁队列中的无序事务整理成有序的 per-token 队列。

`applyToken` 是事务顺序的边界。SurfaceFlinger 只保证同一 `applyToken` 下的事务顺序；不同 `applyToken`（通常对应不同进程或不同 buffer producer）的事务之间没有顺序约束。这避免了一个客户端的事务队列阻塞另一个客户端。

### 三阶段过滤器

事务进入 `mPendingTransactionQueues` 后，`flushTransactions()` 通过外部注册的 `TransactionFilter` 回调逐个判断是否可以应用。

[已验证: AOSP android-16.0.0_r4, `TransactionHandler.h` / `TransactionHandler.cpp`]

`TransactionHandler` 最多注册 3 个过滤器（`ftl::SmallVector<TransactionFilter, 3>`）：

1. **时间过滤器（`transactionReadyTimelineCheck`）**：检查 `desiredPresentTime` 是否已到。App 可以通过 `SurfaceControl.Transaction.setDesiredPresentTime` 指定事务的期望呈现时间，未到时间的事务留在队列等待。
2. **Buffer 过滤器（`transactionReadyBufferCheck`）**：检查 barrier frame 和 buffer 是否就绪。涉及 BLASTBufferQueue 的 buffer latch 顺序约束。
3. **自定义过滤器**：业务层注入的过滤器，例如动画系统的事务调度策略。

过滤结果用 `TransactionReadiness` 枚举表示：

| 状态 | 含义 | 处理方式 |
| --- | --- | --- |
| `Ready` | 可以应用 | 从 pending 队列取出，加入本轮 apply 列表 |
| `NotReady` | 条件未满足 | 留在 pending 队列，等下次 flush |
| `NotReadyBarrier` | 被 barrier frame 挡住 | 留在 pending 队列，等前序 buffer latch |
| `NotReadyUnsignaled` | fence 未 signal | 仅当它是本轮唯一就绪事务时单独应用 |

barrier 的 TTL 是 5 秒（`mTransactionBarrierTtl = std::chrono::seconds(5)`），超时后 barrier 自动失效，防止事务被永久卡住。

### flushTransactions 的循环扫描

`flushTransactions()` 不是扫描一遍就结束。`flushPendingTransactionQueues` 会循环扫描，直到没有新事务变为 `Ready` 状态为止。这是因为某些事务的 barrier 依赖可能在扫描过程中被解除——前一个事务被 apply 后，依赖它的后续事务可能变为 `Ready`。

unsignaled buffer 的处理有一个边界条件：代码只在当前没有其他 ready 事务时，才把 `queueWithUnsignaledBuffer` 对应的事务单独取出。如果已有 ready 事务，unsignaled buffer 的事务会被跳过，并在 Perfetto 中打出 `fence unsignaled` trace。这样避免把多个未完成 buffer 一起推进合成阶段。

## setTransactionState 到 applyTransactionState 的完整路径

### 入队阶段（binder 线程）

`SurfaceFlinger::setTransactionState` 是事务的 IPC 入口，在 binder 线程上执行。

[已验证: AOSP android-16.0.0_r4, `SurfaceFlinger.cpp`, line 5359]

```
setTransactionState(transactionState, applyToken):
  1. sanitize 权限检查、ADPF workload hint 提取
  2. 构造 QueuedTransactionState（resolvedStates、displayStates、flags、applyToken、inputWindowCommands、desiredPresentTime、barriers 等）
  3. ftl::FakeGuard(kMainThreadContext) // 声明归属，不实际加锁
  4. mTransactionHandler.queueTransaction(std::move(state)) // LocklessQueue::push
  5. setTransactionFlags(eTransactionFlushNeeded, schedule, frameHint) // 触发主线程处理
  6. scheduleCommit(frameHint) // 请求下一帧 commit
```

第 3 步的 `ftl::FakeGuard` 是一个声明式标记，告诉 Clang thread safety analysis 这段代码逻辑上属于主线程上下文，但实际执行在 binder 线程上。它不产生任何运行时锁操作。

入队阶段的关键特性：**不持 `mStateLock`**。整个入队过程只做一次 CAS 写入 `LocklessQueue`，不需要获取 SurfaceFlinger 的全局状态锁。

### 消费阶段（SurfaceFlinger 主线程）

主线程在下一帧的 commit 周期中处理积压的事务：

```
SurfaceFlinger::onMessageInvalidate / commit:
  → TransactionProcessor::flush():
    → mTransactionHandler.collectTransactions()
        // 排空 LocklessQueue → 分配到 mPendingTransactionQueues
    → mTransactionHandler.flushTransactions()
        // 按 applyToken 分桶扫描
        // 三阶段过滤: timeline → buffer → custom
        // 返回就绪事务列表
  → applyTransactions(transactions):
      Mutex::Autolock lock(mStateLock)
      → applyTransactionsLocked(transactions):
          for each transaction:
              → applyTransactionState(...)
                  → updateLayerCallbacksAndStats(...)
                  → addInputWindowCommands(...)
                  → setTransactionFlags(transactionFlags)
```

`applyTransactionState` 在 `mStateLock` 保护下修改 Layer 状态。这是整条链路中唯一需要持全局锁的步骤，而且主线程此时已经知道哪些事务可以应用，不需要在锁内做过滤判断。

### 空动画事务的 back-pressure 机制

一个特例：如果 `transactionFlags == 0` 但事务标记了 `eAnimation`，代码会强制设置 `eTransactionNeeded`。这是动画系统的 back-pressure 机制——空动画事务仍然触发一次 commit/flush 周期，让动画系统可以感知 SurfaceFlinger 的处理节奏。

## FrontEnd 架构下的事务状态拆分

Android 15 引入 FrontEnd 之后，事务处理路径和旧架构有三点核心差异（详见 §2.22）：

### 请求状态与合成状态分离

`RequestedLayerState` 只保存客户端请求（position、alpha、crop、parent、buffer 等），`LayerSnapshot` 保存叠加了父级变换、可见性、z-order 等信息的合成输入。事务只修改 `RequestedLayerState`，不直接操作 Layer 对象。

### 变更标记驱动增量更新

`RequestedLayerState` 的 `Changes` bitmask 把变更分为 `Hierarchy`、`Geometry`、`Content`、`Z`、`Buffer` 等类型。后续组件根据 change flags 决定是否需要重建层级、更新 snapshot 或重新计算 z-order。纯 buffer 更新可以走 fast path，不需要刷新层级图。

### 双缓冲的角色变化

旧架构中，`mCurrentState`（可变）和 `mDrawingState`（正在合成）的切换是主循环的核心。FrontEnd 引入后，`mCurrentState` 的更新路径变成了：`LocklessQueue` → `mPendingTransactionQueues` → `flushTransactions` → `applyTransactionState` → `RequestedLayerState` → `LayerLifecycleManager.commitChanges()`。`mDrawingState` 的角色没有变，仍然是合成阶段读取的快照。

## BLASTBufferQueue 与 Transaction Queue 的协作

BLASTBufferQueue 是 App 侧 buffer 提交到 SurfaceFlinger 侧消费的接口（Android 11 引入，详见 §2.6）。它和 Transaction Queue 有两层交互：

### buffer 事务的提交

App 调用 `BLASTBufferQueue::update()` 时，内部构造一笔 `SurfaceControl.Transaction`，设置 `applyToken` 为 BBQ 自己的 token，然后以 one-way 模式提交。one-way 事务绕过正常 transaction flush 的同步等待，降低了 buffer 提交路径的延迟。

[已验证: AOSP android-16.0.0_r4, `BLASTBufferQueue.cpp`, line 266]

### buffer 就绪判断

TransactionHandler 的 buffer 过滤器（`transactionReadyBufferCheck`）在判断事务是否可以应用时，需要检查对应 buffer 的 acquire fence 是否已 signal。这是 buffer 路径和事务路径的交汇点：

- buffer 通过 `BLASTBufferQueue::acquireNextBufferLocked` 进入 SurfaceFlinger（详见 §2.6）。
- 事务通过 `LocklessQueue` → `flushTransactions` 路径到达 `applyTransactionState`。
- 两者在 `TransactionReadiness` 判断处汇合：fence 未 signal 的事务被标记为 `NotReadyUnsignaled`，留在队列等待。

## 性能影响分析

### 锁争用消除

旧架构下的事务入队路径涉及 `std::mutex`，在以下场景会触发 futex 系统调用：

- 多个 App 同时提交 SurfaceControl 事务（多窗口、桌面模式）
- 动画系统高频更新 position/alpha
- WMS 在窗口转场时批量 reparent/reorder layer

引入 `LocklessQueue` 后，这些场景下 binder 线程的入队操作不再需要获取互斥锁。CAS 操作在用户态完成，即使发生竞争也只是重试，不会导致线程挂起。

### 批量过滤减少空 apply

三阶段过滤器的意义不只是排序，更重要的是**提前剔除本帧不能应用的事务**。旧架构中，所有事务在 `handleTransaction` 中逐个 apply，如果某个事务的 buffer 未就绪，整个 apply 流程仍然要处理它。新架构下，未就绪事务在 `flushTransactions` 阶段就被拦在 pending 队列里，不会进入 `applyTransactionState`。

### Barrier TTL 防止死等

`mTransactionBarrierTtl = 5s` 确保长时间未触发的 barrier 自动失效。如果没有这个机制，一个 barrier frame 永远不到达的极端情况下，后续所有依赖该 barrier 的事务会堆积在 pending 队列里，直到队列溢出。

### 可量化的影响方向

| 场景 | 旧架构瓶颈 | 新架构收益 |
| --- | --- | --- |
| 多 App 并发事务 | mutex 争用 → futex wait | CAS 入队 → 无系统调用 |
| 大量未就绪事务 | 全部 apply 后发现 buffer 未就绪 | flush 阶段过滤，只 apply 就绪事务 |
| barrier 依赖链 | 串行扫描，可能多帧延迟 | 循环扫描 + TTL 超时 |
| 动画事务 back-pressure | 需要实际事务触发 flush | 空动画事务也能触发 |

给出具体毫秒数需要同机型、同刷新率、同事务压力的对照测试数据。目前没有这样的公开基准数据，只能定性说明影响方向。

## 从 Android 15 到 17 的 Transaction 架构演进

| 版本 | 事务入队方式 | 主线程处理 | 过滤机制 | BufferQueue 路径 |
| --- | --- | --- | --- | --- |
| Android 15 | `std::mutex` + `std::queue` | 单 `handleTransaction` 顺序应用 | 无显式过滤 | BLASTBufferQueue |
| Android 16 | `LocklessQueue<MPSC>` + `TransactionHandler` | `flushTransactions` 三阶段过滤 | timeline / buffer / custom | BLASTBufferQueue 增强 barrier |
| Android 17 | 同 Android 16 | 同 Android 16（待公开 tag 验证） | 同（待验证） | 同（待验证） |

[已验证: AOSP android-16.0.0_r4; Android 17 基于 Android 16 延续性推断，android-17.0.0_r1 公开 tag 截至 2026-06-11 未发布]

Android 15 的架构在低事务量场景下没有明显问题。瓶颈出现在两个地方：

1. **mutex 争用**：多 binder 线程同时入队时，futex wait 的延迟会叠加到 SurfaceFlinger 主线程的 commit 路径上。
2. **无过滤**：所有事务不管是否就绪都要走一遍 apply 路径。未就绪事务被 apply 后发现条件不满足，白白消耗了持锁时间。

Android 16 的 `LocklessQueue` + `TransactionHandler` 组合同时解决了这两个问题。Android 17 在此基础上的演进细节需要等公开 tag 发布后验证。

## 多窗口/桌面模式下高并发事务的 Perfetto 观察方法

在多窗口或桌面模式下，多个 App 同时提交 SurfaceControl 事务，是观察 LocklessQueue 效果的最佳场景。

### Trace 采集配置

```bash
adb shell perfetto -o /data/misc/perfetto-traces/trace.perfetto-trace -t 15s \
  sched freq idle am wm gfx view binder_driver hal surfaceflinger
```

### 关键观察点

1. **TransactionQueue counter**：Perfetto 中 `surfaceflinger` 轨道下的 `TransactionQueue` counter 反映事务队列深度。如果这个值在多窗口场景下持续增长，说明 `flushTransactions` 来不及消费。
2. **SurfaceFlinger 主线程 commit slice**：`commit` 阶段的耗时。如果 `commit` 中 `flushPendingTransactionQueues` 占比高，说明事务过滤或 apply 路径是瓶颈。
3. **binder 线程锁等待**：旧架构下会看到 binder 线程在 `mStateLock` 上的等待。新架构下 binder 线程应该只有短暂的 CAS 重试，不会有长时间的 `sched` sleep。
4. **fence unsignaled trace**：如果大量事务被标记为 `NotReadyUnsignaled`，说明 buffer 供给跟不上事务提交节奏，问题在 buffer 路径而不是事务队列路径。

### 排查顺序

1. 先看 `TransactionQueue` 是否持续积压
2. 如果积压，看 `commit` 中 `flushPendingTransactionQueues` 的耗时
3. 如果 flush 慢，看是不是 barrier 依赖链过长（`NotReadyBarrier` 数量多）
4. 如果 flush 不慢但 `applyTransactionsLocked` 慢，问题在 apply 阶段
5. 如果队列不长但 `present` 或 fence wait 异常，转向 §2.16 Sync Fence 和 §2.6 HWC 路径

## TransactionFilter 扩展接口与 OEM 定制

`TransactionHandler::addTransactionReadyFilter()` 允许注册自定义过滤器。AOSP 默认注册了 timeline 和 buffer 两个，第三个槽位留给业务层。

OEM 定制场景举例：

- **游戏模式事务优先级**：在游戏模式下，让游戏 App 的事务比后台 App 优先通过过滤
- **分屏转场事务调度**：分屏进入/退出时，按特定顺序过滤转场事务，确保动画节奏一致
- **低功耗模式事务节流**：在低电量模式下，延迟非关键事务的 apply，减少 SurfaceFlinger 唤醒频率

自定义过滤器需要实现 `TransactionFilter` 签名（`std::function<TransactionReadiness(const TransactionFlushState&)>`），返回 `Ready` / `NotReady` / `NotReadyBarrier` / `NotReadyUnsignaled` 之一。

注意：第三个过滤器槽位目前没有在 AOSP 中被默认使用。如果 OEM 注册了自定义过滤器，需要确保不会和 timeline / buffer 过滤器产生冲突——三个过滤器是串行应用的，前一个返回 `Ready` 后才会进入下一个。

## SF Transaction Queue 与 Choreographer VSync 的时序关系

事务从 App 提交到 SurfaceFlinger 应用，中间经过的时序节点：

```
App 主线程:
  Choreographer.doFrame()
    → SurfaceControl.Transaction.apply()    // 提交事务
      → Binder IPC → SurfaceFlinger.setTransactionState()
        → LocklessQueue.push()              // 入队完成

SurfaceFlinger 主线程（下一个 VSync-sf）:
  VSync-sf 信号到达
    → commit 周期开始
      → collectTransactions()                // 排空 LocklessQueue
      → flushTransactions()                  // 三阶段过滤
      → applyTransactionsLocked()            // 持 mStateLock 应用
    → composite 周期
      → latch buffers
      → HWC / RenderEngine 合成
    → present
```

事务从 `apply()` 到 SurfaceFlinger 主线程 `applyTransactionState` 的延迟，取决于两个因素：

1. **Binder IPC 延迟**：通常在 0.5-2ms 范围内，但高负载时可能更长。
2. **VSync-sf 时序**：如果事务在 VSync-sf 之后到达，需要等下一个 VSync-sf 才会被处理。

Android 16 的 `scheduleCommit(frameHint)` 机制可以在事务到达后请求提前唤醒 SurfaceFlinger，减少等待时间。这和 `Choreographer` 侧的 `scheduleVsync()` 类似——不等下一个 VSync 周期，而是请求立即处理。

## 参考资料

- [已验证: AOSP android-16.0.0_r4, `frameworks/native/services/surfaceflinger/LocklessQueue.h`]
- [已验证: AOSP android-16.0.0_r4, `frameworks/native/services/surfaceflinger/FrontEnd/TransactionHandler.h`]
- [已验证: AOSP android-16.0.0_r4, `frameworks/native/services/surfaceflinger/FrontEnd/TransactionHandler.cpp`]
- [已验证: AOSP android-16.0.0_r4, `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`, line 5359 / 5275-5579 / 5075]
- [已验证: AOSP android-16.0.0_r4, `frameworks/native/libs/gui/BLASTBufferQueue.cpp`, line 266 / 470 / 556]
- [来源: `DeepResearch/2026-06-08-android-17-sf-transaction-queue-lockless-architecture.md`]

> ⚠️ **版本边界声明**：android-17.0.0_r1 公开 tag 截至 2026-06-11 未发布。本文所有源码验证基于 android-16.0.0_r4。标注"Android 17"的内容基于 Android 16 代码的延续性推断，不得作为 Android 17 的确定性结论。
