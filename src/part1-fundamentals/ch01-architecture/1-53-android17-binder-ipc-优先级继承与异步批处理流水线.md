---
title: "Android 17 Binder IPC 优先级继承与异步批处理流水线"
chapter: "1.53"
status: ready-for-review
applicable_versions: "Android 17 (API 37)"
tags: ["Android17", "性能优化", "系统机制"]
related_chapters: ['ch01']
created_by: "task2a-knowledge-gap"
drafted_date: "2026-07-03"
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "drivers/android/binder.c"
  - type: aosp
    path: "frameworks/native/libs/binder/IPCThreadState.cpp"
created_date: "2026-07-03"
gap_source: "AOSP结构+研究素材"
gap_score: 20
---

# 1.53 Android 17 Binder IPC 优先级继承与异步批处理流水线

<!-- outline-start -->
## 要点

### 🔹 Android 17 Binder IPC 优先级继承机制

Android 17 中 Binder IPC 采用事务隐式传递优先级机制，通过 `binder_transaction_priority()` 在同步事务执行时自动继承调用方优先级。这一机制的关键在于当目标线程被 `binder_select_thread_ilocked()` 选中后，内核调用 `binder_transaction_priority(thread, t, node)` 将调用方的优先级注入到目标线程。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/IPCThreadState.cpp:921]

该机制确保高优先级请求（如 UI 渲染、用户输入响应）能够优先得到处理，避免低优先级任务阻塞关键路径。与 Android 12 及之前版本依赖显式的 BC_SET_PRIORITY 不同，Android 17 完全通过事务隐式传递，减少了协议开销。

### 🔹 三层调度架构解析

Binder IPC 在 Android 17 中实现了精密的三层调度架构，每层服务于不同的使用场景：

1. **Thread TODO 队列** (`thread->todo`)：处理单线程内部的事务调度，当调用方已明确指定目标线程时使用。`binder_select_thread_ilocked()` 采用 FIFO 算法从 `proc->waiting_threads` 链表选择目标线程，选中后唤醒采用 `wake_up_interruptible_sync()` 以减少调度延迟。

2. **Proc TODO 队列** (`proc->todo`)：管理进程级别的事务优先级，当无明确目标线程且目标进程不存在未完成 oneway 事务时使用。这类事务通常是跨进程但不指定具体线程的同步调用。

3. **Node TODO 队列** (`node->async_todo`)：处理跨进程通信的异步批处理，当无明确目标线程且同一 node 存在未完成 oneway 事务时使用。此队列确保同一目标 node 的多个 oneway 事务串行处理，避免并发竞争。

[已验证: AOSP android-17.0.0_r1, drivers/android/binder.c:3032-3149]

### 🔹 内核级批处理流水线

内核 binder.c 引入了精细的批处理机制，包含以下关键特性：

**1. 1MB 缓冲区管理**：每个进程通过 mmap 获得 `BINDER_VM_SIZE`（1MB - 2页）的缓冲区空间。同步与异步事务共享同一 mmap 空间，通过 `free_async_space` 配额隔离，不存在独立的"异步内存池"。

**2. 溢出处理策略**：当事务超出 1MB 限制时，内核返回 `BR_FAILED_REPLY`，用户态映射为 `FAILED_TRANSACTION`。此机制在 `binder_alloc_new_buf_locked()` 中实现，对同步和异步事务均适用。

**3. Death notification 四态机**：注册 → 死亡通知派发 → 确认 → 清理的完整状态机，确保长生命周期事件的可靠传递。核心状态包括 `BINDER_WORK_DEAD_BINDER`、`BINDER_WORK_DEAD_BINDER_AND_CLEAR` 和 `BINDER_WORK_CLEAR_DEATH_NOTIFICATION`。

[已验证: AOSP android-17.0.0_r1, drivers/android/binder.c:5188-5230]

### 🔹 同步事务防死锁内核护栏

Android 17 内核在 `binder_transaction()` 函数的行 3466-3479 实现了关键的防死锁检查：

```c
w = list_first_entry_or_null(&thread->todo, struct binder_work, entry);
if (!(tr->flags & TF_ONE_WAY) && w && w->type == BINDER_WORK_TRANSACTION) {
    binder_user_error("%d:%d new transaction not allowed when there is a transaction on thread todo", proc->pid, thread->pid);
    binder_inner_proc_unlock(proc);
    return_error = BR_FAILED_REPLY;
    return_error_param = -EPROTO;
    return_error_line = __LINE__;
    goto err_bad_todo_list;
}
```

[已验证: AOSP android-17.0.0_r1, drivers/android/binder.c:3466-3479]

该内核护栏确保线程在等待同步事务回复期间不能发起新的同步事务，防止 A→等B→B等A 的经典死锁循环。此检查仅对同步事务生效，oneway 事务不受限制。

### 🔹 用户态双层批处理优化

除内核批处理外，用户态也实现了双层批处理架构：

**第一层 - ioctl 批量处理**：单次 `ioctl()` 调用可返回多达 128 条 BR 命令，通过 `binder_thread_read()` 的批量读取机制实现。`IPCThreadState::talkWithDriver()` 在驱动读取循环中处理多条命令，减少 ioctl 系统调用开销。

**第二层 - 事务批处理**：`BINDER_WRITE_READ` 协议允许一次读写操作包含多个事务，通过 `Parcel` 对象的序列化/反序列化实现批量数据交换。特别是在 Android 17 中，`TF_UPDATE_TXN` 标志支持异步事务的智能去重，避免重复处理相同事务。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/IPCThreadState.cpp:1246-1362]

## 扩展

### 🔸 多进程路由的 FIFO 语义与优先级继承

三层调度架构的 FIFO 选择机制看似简单，但结合 `binder_transaction_priority()` 的优先级继承，形成了高效的调度体系。当 `binder_select_thread_ilocked()` 选中目标线程后，被选中的线程立即继承调用方的优先级，确保关键事务获得及时处理。

这种设计避免了传统的"实时调度器 + 优先级队列"的复杂实现，而是将调度复杂度交给内核的 CFS/RT 调度器，Binder 本身只负责事务路由和优先级标记。

### 🔸 1MB 缓冲区的边界管理策略

1MB 缓冲区虽然是固定大小，但 Android 17 提供了精细的边界管理：

- **大事务预警**：建议应用对超过 256KB 的 parcel 实现 `FAILED_TRANSACTION` 异常处理
- **异步配额隔离**：`free_async_space` 确保异步事务不会消耗过多同步事务空间
- **TF_UPDATE_TXN 智能替换**：在目标进程 frozen 且存在未处理事务时，新事务可替换旧事务，避免资源浪费

### 🔸 Death notification 的生命周期管理

Death notification 的四态机设计解决了 Binder 中唯一的长生命周期事件管理问题：

- **注册阶段**：`BC_REQUEST_DEATH_NOTIFICATION` 建立 death 监听
- **派发阶段**：目标进程死亡时触发 `BR_DEAD_BINDER`
- **确认阶段**：调用方通过 `BC_DEAD_BINDER_DONE` 确认收到
- **清理阶段**：`BR_CLEAR_DEATH_NOTIFICATION_DONE` 完成内存释放

此机制确保了跨进程服务的可靠注销，避免了内存泄漏。


## 🔬 源码级深挖（2026-07-11 调研补充）

<!-- AIW-源码调研-2026-07-11 -->
> 本节基于 `android-17.0.0_r1` + kernel `android17-6.18` 源码深挖，补充 §1.53 原稿未覆盖的内核态优先级状态机与 IPCThreadState 角色定位。

### 🔹 IPCThreadState.cpp 在优先级继承中的真实角色

经全文检索（1869 行），`IPCThreadState.cpp` 在优先级继承链路中**几乎不参与计算**，仅承担 **2 个职责**：

1. **背景调度守门**（IPCThreadState.cpp:431-438）：`gDisableBackgroundScheduling` 原子 bool 决定 Parcel.cpp:288 是否走默认 nice=19
   ```cpp
   static std::atomic<bool> gDisableBackgroundScheduling = false;
   void IPCThreadState::disableBackgroundScheduling(bool disable) { ... }
   ```
2. **caller 元数据透传**（IPCThreadState.cpp:1515-1611）：在 BR_TRANSACTION 入口保存 origPid，tr.sender_pid 写入 mCallingPid；恢复时还原。这与调度优先级**正交**，仅服务于 `Binder.getCallingPid()` Java API。

**结论**：所谓"IPCThreadState.cpp 中的优先级继承"实际上**不存在**于该文件，全部优先级逻辑都在 `Parcel.cpp`（用户态编码）+ `kernel binder.c`（内核态决策）双侧。

### 🔹 Parcel.cpp 编码端（frameworks/native/libs/binder/Parcel.cpp:247-326）

`schedPolicyMask(policy, priority)` 把 `mPolicy/mPriority/mInheritRt` 三个独立字段打包进 `flat_binder_object.flags` 低 12 位：

- bit[0..7] = `FLAT_BINDER_FLAG_PRIORITY_MASK`（nice -20..19 或 RT 1..99）
- bit[9..10] = `FLAT_BINDER_FLAG_SCHED_POLICY_MASK`（仅 4 种 policy：NORMAL/FIFO/RR/BATCH）
- bit[11] = `FLAT_BINDER_FLAG_INHERIT_RT`（独立位）

`BBinder::setInheritRt()` 不变量守门（Binder.cpp:910-912）：
```cpp
LOG_ALWAYS_FATAL_IF(wasParceled(),
    "setInheritRt() should not be called after a binder object is parceled/sent to another process");
```
已 parceled 后再调用直接 LOG_ALWAYS_FATAL——保证 flags 不会被事后篡改。

### 🔹 内核态 prio_state 三态机（kernel/android17-6.18/binder.c:778-862）

binder 驱动维护 `binder_thread->prio_state` 状态机，是**嵌套事务优先级冲突**的根因：

| 状态 | 触发条件 | 行为 |
|------|---------|------|
| `BINDER_PRIO_PENDING` | target 正在修改自身优先级（save/restore 过渡） | 新事务到来时标 ABORT |
| `BINDER_PRIO_SET` | target 当前优先级由 caller 强加 | 处理完毕恢复 saved_priority |
| `BINDER_PRIO_ABORT` | 嵌套事务打断，放弃恢复 | 新事务直接接管，不恢复 |

**嵌套事务 abort 逻辑**（binder.c:851-862）：
```c
spin_lock(&thread->prio_lock);
if (thread->prio_state == BINDER_PRIO_PENDING) {
    t->saved_priority = thread->prio_next;
    thread->prio_state = BINDER_PRIO_ABORT;  // 标记放弃恢复
    ...
}
```

### 🔹 三层合并顺序（binder.c:819-869 binder_transaction_priority）

`binder_transaction_priority()` 在 `binder_set_priority()` 之前的 3 步处理：

1. **RT 降级守门**：`!node->inherit_rt && is_rt_policy(desired.sched_policy)` → 强制 SCHED_NORMAL + nice 0
2. **node min 优先级仲裁**：`node_prio.prio < desired.prio || (同 prio && SCHED_FIFO)` → node 最低优先级胜出
3. **saved_priority 保存** + 嵌套事务 abort 处理

注意 SCHED_FIFO 在同优先级时**优先于** SCHED_RR（避免 RR 时间片饿死）

### 🔹 CAP_SYS_NICE 双路径验证（binder.c:723-808 binder_do_set_priority）

- **RT 路径**（verify=true && is_rt_policy && !has_cap_nice）：
  - `RLIMIT_RTPRIO == 0` → 强制降 SCHED_NORMAL + MIN_NICE
  - 否则钳位到 rlimit
- **fair 路径**（verify=true && is_fair_policy && !has_cap_nice）：
  - 检查 `RLIMIT_NICE`，钳位 nice 上限
- **`SCHED_RESET_ON_FORK` flag**（binder.c:798）：保证 RT 策略不通过 fork 逃逸到子进程
- **`verify=false` 路径**（binder_restore_priority）：恢复自己原优先级时跳过 CAP_SYS_NICE 校验

### 🔹 RT 写调用（binder.c:793-800）

```c
struct sched_param params;
params.sched_priority = is_rt_policy(policy) ? priority : 0;
sched_setscheduler_nocheck(task, policy | SCHED_RESET_ON_FORK, &params);
if (is_fair_policy(policy))
    set_user_nice(task, priority);
```

- **RT 走 `sched_setscheduler_nocheck`**：跳过越权检查（caller 已 verify 过）
- **fair 走 `set_user_nice`**：Linux v6.18 EEVDF 下改为改 `latency_weight` 与 `weight`，不直接改 `vruntime`

### 🔹 完整调用链（同步事务，App → system_server RT 升级场景）

1. App 主线程 `IPCThreadState::transact()` 写 `BC_TRANSACTION`
2. `talkWithDriver()` ioctl 进驱动；驱动 `binder_transaction()` 复制 caller policy/prio 到 `t->priority`（binder.c:3555-3566）
3. `binder_select_thread_ilocked()` 从 system_server waiting_threads 选 worker
4. `binder_transaction_priority()` 执行三层合并
5. `binder_set_priority()` (verify=true) → `binder_do_set_priority()` → CAP_SYS_NICE 检查 + `sched_setscheduler_nocheck`
6. system_server worker 处理业务（被临时升级到 RT）
7. 写 `BC_REPLY`，`binder_restore_priority()` (verify=false) → 恢复 saved_priority
8. App 端 `talkWithDriver()` 返回

<!-- /AIW-源码调研-2026-07-11 -->

<!-- outline-end -->

> 审校说明：上方区域是受流水线保护的历史提纲，原样保留不代表其中每项结论仍然有效。本节正文以平台 `android-17.0.0_r1` 和内核 `android17-6.18-2026-06_r6` 重新核对实现。旧提纲中的“三层调度”“内核事务批处理”“128 条 BR 命令”“固定 1 MB 单事务上限”均需按下文修正。

## 一次同步调用如何继承优先级

Binder 优先级继承解决的是服务端 Binder 线程以过低优先级执行同步请求的问题。同步调用方会等待回复，服务端处理速度直接影响调用方延迟。Android 官方文档把机制分为事务优先级继承、节点最低优先级和实时优先级继承三类；这里的“三类”描述优先级来源与约束，不是三个事务队列。

Android 17 内核中的决策顺序如下：

1. `binder_transaction()` 创建非 oneway 事务时，若调用线程采用驱动支持的 `SCHED_NORMAL`、`SCHED_BATCH`、`SCHED_FIFO` 或 `SCHED_RR`，便把调用线程的 policy 和 priority 写入 `t->priority`。oneway 事务及不支持的调度策略改用目标进程的 `default_priority`。
2. Binder 节点的 `min_priority`、`sched_policy` 与 `inherit_rt` 来自节点对象。Native Binder 可在对象首次被 Parcel 化之前调用 `BBinder::setMinSchedulerPolicy()` 和 `BBinder::setInheritRt()`；`Parcel::flattenBinder()` 把这些配置编码到 `flat_binder_object.flags`。
3. 事务已经匹配到目标线程时，`binder_transaction_priority()` 选择本次执行优先级。若事务要求实时调度而节点没有启用 `inherit_rt`，驱动将期望值降为 `SCHED_NORMAL`、nice 0；随后再比较事务期望值与节点最低优先级，采用优先级更高的一方。同一数值下，节点指定的 `SCHED_FIFO` 优先于 `SCHED_RR`。
4. `binder_do_set_priority(..., verify=true)` 依据 `CAP_SYS_NICE`、`RLIMIT_RTPRIO` 与 `RLIMIT_NICE` 裁剪请求，设置服务线程的 scheduler policy 或 nice。配置一个高优先级节点并不等于调用一定能越过进程的调度权限。
5. 服务端回复后，驱动用事务保存的 `saved_priority` 恢复该 Binder 线程。嵌套同步调用可能在恢复期间又投递新事务，`BINDER_PRIO_SET`、`BINDER_PRIO_PENDING` 和 `BINDER_PRIO_ABORT` 只负责协调这段优先级恢复竞争。

这条路径也解释了两个常见现象。同步事务可继承调用方优先级，oneway 不继承调用方优先级；若异步工作也有明确的时延要求，服务端应通过节点最低优先级配置表达。实时优先级继承默认关闭，必须对具体 Binder 节点启用。

旧提纲把上述机制描述为 Android 17 相对 Android 12 的协议替换，但没有给出对应版本提交。Android 17 Binder UAPI 中也没有提纲所称的 `BC_SET_PRIORITY` 命令，因此不能把该说法用作版本演进结论。

## 工作投递位置不是调度层级

`binder_proc_transaction()` 的工作是把事务交给可执行它的线程或待办链表。它的主要分支可以这样读：

- 已经指定或选中目标线程时，工作进入 `thread->todo`，驱动同时设置该线程本次事务的优先级。
- 没有可用目标线程，而且当前事务不是同一节点上排队的后续 oneway 时，工作进入 `proc->todo`，等待进程中的 Binder 线程领取。
- 同一节点已有 oneway 正在执行时，后续 oneway 进入 `node->async_todo`。前一笔处理结束后，驱动再推进下一笔，从而维持同一节点的异步事务顺序。

这些链表没有全局优先级排序。`binder_select_thread_ilocked()` 从 `proc->waiting_threads` 的链表头取线程，事务优先级在选中目标线程后交给 Linux 调度器生效。把 `thread->todo`、`proc->todo`、`node->async_todo` 称为三层优先级架构，会把“放到哪里等待”与“线程获得多少 CPU 调度优先级”混在一起。

oneway 的串行队列也不构成通用批处理。每次调用仍有独立的事务对象、缓冲区和完成通知。`TF_UPDATE_TXN` 是一个范围很窄的替换协议：目标进程需要处于 frozen 状态，旧事务和新事务都要同时带有 `TF_ONE_WAY | TF_UPDATE_TXN`，并且目标进程、事务码、完整 flags、发送者 PID、节点指针与 cookie 都要匹配。普通运行态下的重复 oneway 不会因此自动去重。

## `BINDER_WRITE_READ` 能合并协议往返，但没有 128 条保证

`IPCThreadState::talkWithDriver()` 把待写的 `mOut` 和可读的 `mIn` 一起放进 `binder_write_read`，再执行一次 `BINDER_WRITE_READ` ioctl。一个缓冲区可以容纳多条 BC 或 BR 命令，所以减少 ioctl 次数是这套流式协议的自然结果。

命令数量由缓冲区字节数和每条命令的结构大小共同决定。Android 17 的 `IPCThreadState` 构造函数将 `mIn` 与 `mOut` 初始容量设为 256 字节，源码没有“单次最多返回 128 条 BR 命令”的固定常量。读缓冲区装满后，剩余返回命令由后续 ioctl 读取；当前 Native libbinder 则要求驱动消费本轮完整的写缓冲区，部分消费会触发致命检查。`Parcel` 负责单笔事务的数据与对象序列化，它不会自动把多笔业务调用合成一笔事务。

分析 trace 时可以把同一次 ioctl 中出现多条协议命令称为“命令流合并”，但不宜据此推导业务事务被批量执行或去重。

## 缓冲区限制应按进程共享区分析

Android 17 的 `ProcessState.cpp` 把 Binder 映射大小定义为 `1 MiB - 2 × page size`。这块区域由目标进程的并发入站事务共同使用，不能当作每笔 Parcel 的可用载荷上限。驱动分配时还要考虑：

- 事务数据、offset 数组与额外对象缓冲区的对齐后总量；
- 当前仍由用户态持有的 Binder 缓冲区；
- 空闲区碎片能否提供足够大的连续区间；
- oneway 的异步空间配额。`binder_alloc_mmap_handler()` 把初始 `free_async_space` 设为映射区的一半，异步分配会单独扣减该配额；
- 安全上下文、Binder 对象和文件描述符复制期间出现的校验或资源错误。

因此，小于 1 MB 的调用也可能失败，超过某个业务自定阈值也不等于驱动一定失败。旧提纲中的 256 KB 预警值不是 Android 17 平台契约。应用可以设置更保守的工程阈值，但应把它标成自身约束，并通过并发压力测试验证。

`BR_FAILED_REPLY` 同样不能直接翻译成“事务过大”。`binder_transaction()` 的无效句柄、SELinux 权限拒绝、错误对象布局、缓冲区分配失败、用户内存复制失败和事务栈协议错误等路径都可能返回它。Native libbinder 将该命令映射为 `FAILED_TRANSACTION`；Java 层可能再以 `TransactionTooLargeException` 报告，异常名称仍不足以单独证明根因。

## 同步事务护栏保护的是协议约束

驱动会拒绝以下组合：线程准备发起新的同步事务，同时该线程 `todo` 链表的队首已经是 `BINDER_WORK_TRANSACTION`。返回结果为 `BR_FAILED_REPLY`，扩展错误为 `-EPROTO`。源码注释把检查依据写得很具体：`binder_select_thread_ilocked()` 从 `waiting_threads` 选择线程，在等待链表期间不会再向该线程的 `todo` 链表追加其他工作，因此检查队首即可确认违规状态。

该逻辑不检查应用互斥锁，也不会遍历跨进程等待图。A 持锁调用 B、B 回调 A 后等待同一把锁之类的问题仍需在应用和系统服务设计中消除。Binder 对合法的嵌套同步回调另有处理：驱动沿调用线程的 `transaction_stack` 查找目标进程中的原调用线程，让回调回到合适的线程上下文。

排查疑似 Binder 死锁时，应同时检查调用栈、锁依赖、Binder 线程池占用和 trace 中的同步等待区间。仅看到 `BR_FAILED_REPLY` 不能下死锁结论。

## 死亡通知是命令与工作项协作

客户端用 `BC_REQUEST_DEATH_NOTIFICATION` 注册死亡接收者。目标节点死亡后，驱动通过 `BINDER_WORK_DEAD_BINDER` 或相关工作类型向用户态发送 `BR_DEAD_BINDER`；用户态处理后以 `BC_DEAD_BINDER_DONE` 确认。主动解除监听时，清理路径可能以 `BR_CLEAR_DEATH_NOTIFICATION_DONE` 结束。

这些名称描述工作类型和协议阶段，不是驱动公开的一套“四态机”接口。注册、节点死亡、用户确认和主动清理可能交错，`BINDER_WORK_DEAD_BINDER_AND_CLEAR` 也用于组合处理相应生命周期。客户端仍需保证死亡回调幂等，并处理“服务已经死亡后再注册”与“解除监听同时死亡”等竞争。

## 调优与验证清单

1. 对同步长尾，确认调用线程与服务线程的 scheduler policy、nice、节点最低优先级和 `inherit_rt`，不要只看调用方优先级。
2. 对 oneway 积压，按 Binder 节点分析队列。单个慢处理会阻塞同一节点的后续异步事务，但不会要求其他节点一起串行。
3. 对 `FAILED_TRANSACTION`，记录数据字节数、offset 数量、Binder 对象、文件描述符与并发事务数量，并结合扩展错误或驱动日志定位失败分支。
4. 对 ioctl 频率，区分协议命令流与业务事务。减少往返次数不等于减少事务数量。
5. 对实时优先级，验证 `CAP_SYS_NICE`、`RLIMIT_RTPRIO`、`RLIMIT_NICE` 与节点配置。实时线程还需要评估 CPU 占用和对普通任务的饥饿风险。
6. 对嵌套调用，画出同步等待与持锁关系；`BINDER_PRIO_*` 只维护优先级恢复，不提供业务锁死锁保护。

更完整的协议总览见 [Binder IPC 机制与性能影响](./04-binder.md)，oneway 与 frozen 事务替换见 [Binder 异步机制与批处理流水线](./01.25-binder-ipc-async-pipeline.md)。

## 源码与官方说明

- [Android 官方 Binder 优先级继承说明](https://source.android.com/docs/core/architecture/ipc/priority-inheritance)
- [AOSP `Parcel.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/Parcel.cpp)
- [AOSP `Binder.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/Binder.cpp)
- [AOSP `IPCThreadState.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/IPCThreadState.cpp)
- [AOSP `ProcessState.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [Android common kernel `binder.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [Android common kernel `binder_alloc.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c)
- [Android common kernel `binder_internal.h`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_internal.h)
