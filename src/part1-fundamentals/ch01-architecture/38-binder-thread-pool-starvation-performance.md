---
title: "Binder 线程池管理与 IPC 线程饥饿性能边界"
chapter: "1.38"
status: ready-for-review
drafted_date: "2026-06-28"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/libs/binder/ProcessState.cpp"
  - type: aosp
    path: "frameworks/native/libs/binder/IPCThreadState.cpp"
  - type: aosp
    path: "drivers/android/binder.c (kernel android16-6.12)"
  - type: official
    path: "developer.android.com/reference/android/os/Binder"
  - type: blog
    path: "DeepResearch/2026-06-24-android-17-binder-ipc-latency-analysis-and-optimization.md"
  - type: blog
    path: "DeepResearch/2026-06-26-android17-binder-perf-monitor-recording-aidl-trace.md"
  - type: blog
    path: "DeepResearch/2026-06-27-android17-binder-async-frozen-batch-pipeline.md"
tags: [binder, thread-pool, starvation, ANR, IPC, system_server]
related_chapters: ["1.4", "1.8", "1.25", "1.34", "9.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-28"
gap_source: "AOSP结构+章节深挖"
---

# 1.38 Binder 线程池管理与 IPC 线程饥饿性能边界

<!-- outline-start -->
## 要点

### 🔹 Binder 线程池基础架构
Android 进程的 Binder 线程池工作机制：ProcessState 初始化、默认池大小（15 + 1 binder thread）、最大线程数限制；spawn_thread_pooled 的按需创建策略；IPCThreadState::joinThreadPool 的生命周期管理。

### 🔹 system_server 的特殊线程池配置
system_server 的 binder 线程池大小差异（通常 >30）；binder 准备线程（BC_ENTER_LOOPER vs BC_REGISTER_LOOPER）；system_server 中 binder 线程饥饿导致系统级卡顿的典型案例。

### 🔹 线程饥饿的触发场景
Nested binder call 场景：Service A 在 onTransact 中调用 Service B，占用了两个 binder 线程；同步 binder 调用阻塞在远程锁/数据库/IO 上导致的连锁饥饿；binder oneway spam 检测机制对线程池的影响。

### 🔹 Binder 线程池与 ANR 关系
Binder 线程耗尽如何间接导致 ANR；Service ANR（前台 20s / 后台 200s）与 binder 线程占用分析的关联；InputDispatcher ANR 中 binder 线程状态的诊断方法。

### 🔹 Binder 线程调试与诊断
dumpsys binder_calls_stats 的线程池统计解读；/proc/[pid]/task 中 binder 线程的识别和状态分析；Perfetto 中 binder thread blocked slice 的识别方法；bstat 工具的使用。

### 🔹 Android 17 Binder 线程池新特性
Android 17 中 binder 线程优先级继承的改进；Binder Freeze 机制对 cached 进程线程池的影响；async pipeline（1.25 节）对线程池压力的缓解。

## 扩展

### 🔸 Binder 线程池调优建议
应用自定义 Service 的 binder 线程池优化；setThreadPoolMaxThreadCount 的正确使用场景；避免在 Binder onTransact 中执行耗时操作的模式。

### 🔸 AIDL 自动生成的 Stub 与线程池交互
AIDL 生成的 onTransact 分发机制；oneway interface 对线程池利用的影响；大型 AIDL 接口的分发性能。

### 🔸 Binder 线程池与 Flutter/Compose 的交互
平台线程（Platform Channel / Method Channel）与 binder 线程池的协作；Compose 的副作用调度器在 binder 回调中的行为。

<!-- outline-end -->

## Binder 线程池基础架构

### ProcessState 与线程池初始化

每个 Android 进程在首次使用 Binder 时，`ProcessState::self()` 会完成一系列初始化：打开 `/dev/binder`（或 binderfs 下的设备节点）、`mmap` 1MB 共享内存区域（`BINDER_VM_SIZE`）、设置最大线程数为 `DEFAULT_MAX_BINDER_THREADS`（值为 15）。这个 15 是**工作线程上限**，不含主线程——主线程在 Activity 启动时通过 `IPCThreadState::joinThreadPool()` 以 `BC_ENTER_LOOPER` 注册自身，也可处理进站事务。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/ProcessState.cpp, DEFAULT_MAX_BINDER_THREADS=15, BINDER_VM_SIZE=1MB]

线程的按需创建由内核驱动决定。当驱动发现目标进程的所有等待线程都在处理事务、且当前线程数未达上限时，会通过 `binder_proc:4287-4298` 向目标进程发送 `BR_SPAWN_LOOPER` 命令。用户态 `IPCThreadState::getAndExecuteCommand()` 收到 `BR_SPAWN_LOOPER` 后，调用 `ProcessState::spawnPooledThread()` 创建新线程，新线程以 `BC_REGISTER_LOOPER` 注册进入池中。

[已验证: AOSP, drivers/android/binder.c, binder_thread_read 中 BR_SPAWN_LOOPER 发送逻辑]

两种注册方式的区别：

| 注册命令 | 使用者 | 角色 |
|---------|--------|------|
| `BC_ENTER_LOOPER` | 主线程 / 主动调用 `joinThreadPool` 的线程 | 永久 binder 线程，不受 `mMaxThreads` 计数约束 |
| `BC_REGISTER_LOOPER` | 由 `BR_SPAWN_LOOPER` 触发创建的线程 | 动态池化线程，计入 `mMaxThreads` 上限 |

> 详见 1.4 节关于 Binder 线程池模型的基础介绍。本节聚焦线程饥饿的性能边界场景。

### 线程池耗尽的用户态行为

当所有工作线程都在执行事务且线程数达到 `mMaxThreads` 时，新进站事务会在内核侧排队。此时，调用方的 `waitForResponse()` 会被阻塞在 `binder_thread_read` 上。同时，目标进程中如果有新线程试图发起 Binder 调用（而非处理进站事务），`IPCThreadState::blockUntilThreadAvailable()` 会使其等待：

```cpp
// IPCThreadState::blockUntilThreadAvailable() — Android 17
void IPCThreadState::blockUntilThreadAvailable() {
    std::unique_lock lock_guard_(mProcess->mOnThreadAvailableLock);
    mProcess->mOnThreadAvailableWaiting++;
    mProcess->mOnThreadAvailableCondVar.wait(lock_guard_, [&] {
        size_t max = mProcess->mMaxThreads;
        size_t cur = mProcess->mExecutingThreadsCount;
        if (cur < max) return true;
        ALOGW("Waiting for thread to be free. mExecutingThreadsCount=%zu mMaxThreads=%zu\n",
              cur, max);
        return false;
    });
    mProcess->mOnThreadAvailableWaiting--;
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/IPCThreadState.cpp]

这个等待是**进程内的**——它限制的是本进程新发起 binder 调用的线程，而非进站事务的处理。因此当 binder 线程池满载时，表现是：外部调用方看到延迟升高，本进程新调用方看到 `Waiting for thread to be free` 告警。两者同时出现是线程池压力的强信号。

### 100ms 饥饿告警

`IPCThreadState::getAndExecuteCommand()` 在工作线程计数达到 `mMaxThreads` 时记录起始时间戳到 `mStarvationStartTime`，回落时计算持续时间。超过 100ms 打 `ALOGE`：

```
binder thread pool (15 threads) starved for 234 ms
```

排查命令：`adb logcat -s libbinder.IPCThreadState:E | grep starved`

这条日志反映的是**本进程**线程池的饥饿时长——所有工作线程都在忙、新事务在排队等待空线程。它是线程池压力最直接的系统级信号。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/IPCThreadState.cpp, mStarvationStartTime 机制]

## system_server 的特殊线程池配置

### 为什么 system_server 需要更多线程

`system_server` 承载了 ActivityManagerService、PackageManagerService、WindowManagerService 等数十个核心系统服务，几乎所有 App 的 IPC 调用最终都会到达这里。默认的 15 个工作线程远远不够。

在 Android 17 中，`system_server` 的线程池上限通过 `ProcessState::setThreadPoolMaxThreadCount()` 在 `SystemServer.java` 初始化阶段调高。AOSP 默认配置将 `system_server` 的 binder 线程上限设为 **31**（部分厂商 ROM 可能更高）。此外 `system_server` 的主线程也参与 Binder 事务处理。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/java/com/android/server/SystemServer.java]

判断方式：

```bash
# 查看 system_server 的 binder 线程数
adb shell ps -T -p $(adb shell pidof system_server) | grep binder: | wc -l
# 或通过 dumpsys
adb shell dumpsys binder_calls_stats | grep "Binder thread"
```

### system_server 线程饥饿的系统级影响

当 `system_server` 的 binder 线程池耗尽时，影响面远大于普通进程：

1. **全局 IPC 延迟升高**：所有 App 调用 AMS/WMS/PMS 等服务都会被阻塞
2. **ANR 连锁触发**：前台 App 等待 system_server 响应超时，触发 InputDispatcher ANR 或 Service ANR
3. **Binder watchdog 告警**：`Binder WATCHDOG` 机制会检测 system_server 内部 binder 调用延迟（不同于应用层饥饿检测）

典型场景：某 OEM 预装应用在 `system_server` 中执行大量同步 binder 调用（如批量查询 ContentProvider），每个调用阻塞 50-100ms，15-20 个并发请求迅速耗尽线程池，导致全局卡顿。

诊断要点：在 Perfetto 中搜索 `system_server` 进程的 binder 线程状态分布。如果多数 `binder:*` 线程处于 Running 状态且各执行时间 > 50ms，而其他进程的 `binder transaction` slice 宽度明显增大，即可判定 system_server 线程池瓶颈。

## 线程饥饿的触发场景

### 场景一：嵌套 Binder 调用（Nested Binder Call）

最经典的饥饿模式。Service A 的 `onTransact()` 在处理客户端请求时，同步调用了 Service B。此时：

- 客户端线程：等待 A 的 reply（占客户端 1 个线程）
- Service A 的 worker 线程：等待 B 的 reply（占 A 进程 1 个 binder 线程）
- Service B 的 worker 线程：实际执行（占 B 进程 1 个 binder 线程）

单次嵌套就同时占用 3 个 binder 线程（分布在 3 个进程）。如果 B 内部再调用 C，链条继续延长。在高并发场景下（多个客户端同时调用 A），A 的线程池会被嵌套等待迅速耗尽。

在 Perfetto 中的表现：`binder transaction` slice 内嵌套了另一个 `binder transaction`——外层 slice 的 `server_dur` 远大于内层实际处理时间，差值就是嵌套等待的开销。使用 `android_binder_txns` SQL 标准库视图可以通过 `flow` 边追踪完整调用链。

[已验证: AOSP, frameworks/native/libs/binder/IPCThreadState.cpp, transact → waitForResponse 调用链]
[引用: Perfetto stdlib android/binder.sql]

### 场景二：同步调用阻塞在锁/IO/数据库

Binder worker 在 `onTransact()` 中执行数据库查询、文件 IO 或等待 Java 锁时，该线程被占用的时间等于阻塞时间。其他进站事务必须等待空闲 worker。

常见模式：

- **ContentProvider.query()** 在 binder 线程中执行 SQLite 查询，如果数据库文件在加密状态或锁竞争中，单次查询可能耗时数百毫秒
- **Service 同步调用其他 Service** 时持有自身锁（如 `synchronized` 方法），导致其他调用方在 binder 层排队
- **文件操作**在 binder 线程中直接读写 `/data/data/` 下的文件，IO 延迟直接转化为 worker 占用时间

这些场景的共同特征是：worker 处于 Running 状态但 CPU 使用率低（在 `sched` 轨道可以看到大量 `S` (Sleeping) 或 `D` (Disk sleep) 状态）。

### 场景三：Oneway 风暴与缓冲区耗尽

Android 12+ 引入的 oneway spam detection（`BINDER_ENABLE_ONEWAY_SPAM_DETECTION`）在 Android 17 中默认开启（`DEFAULT_ENABLE_ONEWAY_SPAM_DETECTION=1`）。当某个 pid 发出的 oneway 事务消耗过多 async buffer 空间时，内核标记 `oneway_spam_suspect` 并发出 `BR_ONEWAY_SPAM_SUSPECT` 告警。

需要注意的是，oneway spam detection 是**诊断信号而非限流**——它不会拒绝事务，但会通过 netlink report 通知系统。如果接收方进程的 async buffer 耗尽（`binder_alloc_new_buf` 返回 `-ENOSPC`），后续 oneway 事务会失败。

对于线程池的影响：oneway 事务在服务端仍然需要 worker 线程处理。大量 oneway 事务堆积会导致 worker 线程持续被占用，间接排挤同步事务的处理。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/ProcessState.cpp:50, DEFAULT_ENABLE_ONEWAY_SPAM_DETECTION=1]
[已验证: AOSP, drivers/android/binder.c, oneway_spam_suspect 逻辑]

> oneway 异步机制的完整分析详见 1.25 节。

## Binder 线程池与 ANR 关系

### ANR 触发链路

Binder 线程池耗尽并不直接触发 ANR——ANR 是由 framework 层的超时机制触发的。但线程池耗尽是 ANR 的常见**间接原因**：

| ANR 类型 | 超时阈值 | 与 binder 线程池的关系 |
|---------|---------|---------------------|
| Service ANR（前台） | 20s | Service.onCreate/onStartCommand 在主线程执行，如果主线程被 binder 调用阻塞，会导致 Service 启动超时 |
| Service ANR（后台） | 200s | 同上，后台 Service 容忍度更高 |
| InputDispatcher ANR | 5s | 主线程在等待 binder reply 时无法处理输入事件，InputDispatcher 等待焦点窗口响应超时 |
| ContentProvider ANR | 因 Publisher 而异 | ContentProvider.query 在 binder 线程执行，如果 provider 进程线程池满，调用方会超时 |

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

### 诊断方法

当 ANR 发生时，ANR trace 文件（`/data/anr/traces.txt` 或 `dumpsys activity processes`）会包含所有 binder 线程的堆栈。关键检查点：

1. **主线程状态**：如果主线程在 `binder_thread_read` 或 `waitForResponse` 上等待，说明它被同步 binder 调用阻塞
2. **Binder 线程数量**：统计名为 `binder:<pid>_*` 的线程数，如果接近 `mMaxThreads`，说明线程池接近满载
3. **各 binder 线程的堆栈**：如果多数 worker 堆栈停在同一个锁对象或数据库方法上，说明存在锁竞争导致的线程占用

```
// ANR trace 中的典型模式
"main" prio=5 tid=1 Native
  | group="main" sCount=1 dsCount=0 obj=0x... self=0x...
  | sysTid=1234 nice=-10 cgrp=top-app sched=0/0 handle=0x...
  | state=S schedstat=( ... ) utime=... stime=... cores=...
  #00 pc 0x... /system/lib64/libbinder.so (android::IPCThreadState::waitForResponse(...))
  #01 pc 0x... /system/lib64/libbinder.so (android::BpBinder::transact(...))
  ...
```

## Binder 线程调试与诊断

### dumpsys binder_calls_stats

Android 9+ 提供了 `binder_calls_stats` 机制，按 binder 事务的接口/方法维度统计调用次数、平均/最大耗时、CPU 时间：

```bash
adb shell dumpsys binder_calls_stats
```

关键输出字段：

| 字段 | 含义 | 线程池相关解读 |
|------|------|--------------|
| `calls` | 调用次数 | 高频调用可能是线程池压力来源 |
| `avg_latency` / `max_latency` | 延迟 | 如果 avg 远超单次处理时间，可能因排队 |
| `cpu_time` | 实际 CPU 时间 | cpu_time 远小于 latency 说明大量时间花在等待 |

Android 17 中 `binder_calls_stats` 的统计粒度通过 `recorded_transactions` 机制增强。`BBinder::startRecordingTransactions(fd)` 可以将每条进站事务完整记录为 `RecordedTransaction` 二进制块（Header → Sent Parcel → Reply Parcel → End），用于离线分析。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/Binder.cpp:399-456, RecordedTransaction]

### Perfetto 中的 Binder 线程分析

Perfetto 是诊断 binder 线程池问题最有效的工具。关键分析路径：

**1. 线程状态总览**

在 Perfetto UI 中选中目标进程，展开线程列表，筛选 `binder:` 前缀的线程。查看它们在时间范围内的状态分布：

- 全部处于 `Running` → 线程池满载
- 多数处于 `Sleeping` 且 `blocked_function = binder_thread_read` → 空闲等待（正常）
- 多数处于 `Uninterruptible Sleep` → IO 阻塞
- 多数处于 `Runnable` 但非 Running → 调度压力（CPU 不是瓶颈，时间片不够分）

**2. Binder Transaction slice 分析**

使用 `android_binder_txns` SQL 标准库视图查询：

```sql
SELECT server_process, server_tid, aidl_name,
       server_dur / 1e6 as server_ms,
       dur / 1e6 as total_ms
FROM android_binder_txns
WHERE server_process = 'system_server'
  AND server_dur > 50e6  -- server 端处理 > 50ms
ORDER BY server_dur DESC
LIMIT 20;
```

`server_dur` 大但 CPU 时间小 → worker 在等待锁/IO，不是计算密集。`total_ms` 与 `server_ms` 差值大 → 时间花在排队或调度。

[引用: Perfetto stdlib android/binder.sql, android_binder_txns 视图]

**3. 饥饿时间戳对齐**

当 logcat 出现 `binder thread pool starved for Xms` 时，用该时间戳在 Perfetto 中定位对应时间窗口。检查该窗口内：
- 哪些 worker 在执行什么事务（binder transaction slice 的 AIDL 方法名）
- 这些事务的 `server_dur` 分布
- 是否有锁竞争（`Lock contention` slice）

### /proc/[pid]/task 线程检查

快速检查某进程的 binder 线程状态（无需 trace）：

```bash
# 列出目标进程的所有 binder 线程名
adb shell ls /proc/$(adb shell pidof com.example.app)/task/ | \
  while read tid; do adb shell cat /proc/$(adb shell pidof com.example.app)/task/$tid/comm; done | \
  grep binder:

# 检查每个 binder 线程的当前状态
adb shell "for tid in $(ls /proc/$(pidof com.example.app)/task/); do
  name=\$(cat /proc/$(pidof com.example.app)/task/\$tid/comm 2>/dev/null)
  stat=\$(cat /proc/$(pidof com.example.app)/task/\$tid/stat 2>/dev/null | awk '{print \$3}')
  [[ \$name == binder:* ]] && echo \"\$tid \$name \$stat\"
done"
```

线程状态字母：`R` = Running, `S` = Sleeping, `D` = Disk sleep, `Z` = Zombie。

## Android 17 Binder 线程池新特性

### Binder Freeze 对 cached 进程的影响

Android 12 引入、Android 17 完善的 Binder Freeze 机制对 cached/后台进程的线程池行为有重要影响：

当进程被 `BINDER_FREEZE` ioctl 冻结后：
- **同步调用**被拒收，调用方收到 `BR_FROZEN_REPLY`
- **oneway 调用**被缓冲在 `node->async_todo` 队列，返回 `BR_TRANSACTION_PENDING_FROZEN`
- 解冻后缓冲的事务才投递给 worker 线程

这意味着 frozen 进程的 binder 线程池实际上处于**休眠状态**——没有事务需要处理。解冻瞬间，大量缓冲事务涌入可能导致短暂的线程池压力突增。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/IPCThreadState.cpp:1820-1836, BINDER_FREEZE ioctl]
[已验证: AOSP, drivers/android/binder.c, binder_proc_transaction 冻结路径]

监控冻结状态：

```cpp
// IPCThreadState::getProcessFreezeInfo(pid, &sync, &async)
// 返回目标进程在冻结前已处理完成的 sync/async transaction 数
uint32_t sync_recv, async_recv;
IPCThreadState::self()->getProcessFreezeInfo(pid, &sync_recv, &async_recv);
```

[已验证: AOSP android-17.0.0_r1, IPCThreadState.cpp:1787-1798, BINDER_GET_FROZEN_INFO]

### 内核线程选择的 FIFO 特性

Android 17 内核（android16-6.12 codeline）的 `binder_select_thread_ilocked()` 仍采用 `list_first_entry_or_null` 从 `waiting_threads` 链表头部选取线程——**纯 FIFO**，不区分线程优先级或 CPU 亲和性。

```c
// drivers/android/binder.c
static struct binder_thread *
binder_select_thread_ilocked(struct binder_proc *proc)
{
    struct binder_thread *thread;
    thread = list_first_entry_or_null(&proc->waiting_threads,
                                      struct binder_thread, waiting_thread_node);
    if (thread)
        list_del_init(&thread->waiting_thread_node);
    return thread;
}
```

这意味着 binder 线程池中不存在"优先级线程"——所有 worker 平等竞争 CPU 时间片。如果一个低优先级进程的 binder 线程被选中处理事务，它和其他线程一样受 CFS/EEVDF 调度器管理。

[已验证: AOSP, drivers/android/binder.c:614-625, kernel android16-6.12]

### Oneway Spam Detection 默认开启

Android 17 将 `DEFAULT_ENABLE_ONEWAY_SPAM_DETECTION` 设为 1（`ProcessState.cpp:50`）。进程初始化时自动调用 `enableOnewaySpamDetection(true)`，通过 `BINDER_ENABLE_ONEWAY_SPAM_DETECTION` ioctl 告知内核开启检测。

特性探测通过 binderfs 完成：

```cpp
// ProcessState::isDriverFeatureEnabled() — 读取 /dev/binderfs/features/
// 缓存为 static bool，单进程只读一次
```

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/ProcessState.cpp:538-567]

### ATRACE_TAG_AIDL 与事务级 Trace

Android 17 在 `BBinder::execTransact()` 中增加了基于 `ATRACE_TAG_AIDL = (1 << 24)` 的 trace 注入。每个进站 binder 事务在 Perfetto 中会显示为一个独立 slice，名称包含 AIDL 接口名和方法名。这比之前只能看到通用 `binder transaction` slice 有了显著提升——可以直接定位是哪个 AIDL 方法的执行占用了 worker 线程。

```cpp
// Binder.cpp:479-491 — startTrace(code) 按 code 查表得到 AIDL 方法名
// trace_begin(ATRACE_TAG_AIDL, name)
```

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/binder/Binder.cpp:479-491, ATRACE_TAG_AIDL]

### async pipeline 对线程池压力的缓解

1.25 节详述的批处理流水线机制从侧面缓解了线程池压力：单次 `ioctl(BINDER_WRITE_READ)` 可以同时处理多个 BC_/BR_ 命令，减少了 syscall 次数和上下文切换开销。对于高频小事务场景（如 UI 状态同步），这意味着 worker 线程能更快释放回池中。

## 扩展

### 🔸 Binder 线程池调优建议

**`setThreadPoolMaxThreadCount()` 的正确使用场景**

大多数应用不需要修改默认的 15 个线程上限。只有在以下场景才考虑调高：

- **ContentProvider 宿主进程**：如果对外提供高频查询接口，且每个查询涉及 IO/数据库操作
- **多进程架构中的核心服务进程**：如 IPC 中枢进程，需要同时服务多个 App 进程
- **媒体编解码服务**：binder 调用涉及长时间 GPU/编解码器操作

**调高线程数的风险**：更多线程意味着更多内存开销（每个线程默认栈 1MB）、更多上下文切换、更多锁竞争。如果线程池满载的原因是单个方法执行过慢（如数据库锁等待），增加线程数只是延迟问题暴露。

**避免在 onTransact 中执行耗时操作的模式**：

1. 将耗时操作 dispatch 到专用线程池（如 `ExecutorService`），binder 方法只负责入队
2. 使用 `AsyncTask` 或 Kotlin Coroutines 的 `Dispatchers.IO` 处理 IO 密集型操作
3. 对于需要返回结果的操作，使用 callback / `oneway` 接口异步返回
4. ContentProvider 的 `query()` 应确保数据库查询在合理时间内完成（使用 WAL 模式 + 合理索引）

### 🔸 AIDL 自动生成的 Stub 与线程池交互

AIDL 生成的 `onTransact()` 方法通过 `switch(code)` 分发到具体接口方法。所有进站事务都在 binder worker 线程上执行——没有额外的线程调度。`oneway` interface 方法仍然占用 worker 线程执行，只是调用方不等待返回。

大型 AIDL 接口（数十个方法）的 `switch` 分发本身开销可忽略。性能关注点应在各方法的实际实现复杂度上。

[待补充: AIDL 接口方法数与 binder 分发延迟的量化基准]

### 🔸 Binder 线程池与 Flutter/Compose 的交互

Flutter 的 Platform Channel 通过 `MethodChannel` 调用原生代码时，底层最终可能触发 binder 调用（如查询系统服务）。这些调用在 Flutter 的 platform 线程（即主线程）上执行，如果 binder 调用阻塞，会导致 Flutter UI 线程卡顿。

Jetpack Compose 的副作用（`LaunchedEffect`、`produceState`）默认在 `Dispatchers.Main`（即主线程）上运行。如果副作用中发起同步 binder 调用（如查询 ContentProvider），阻塞会直接导致 recomposition 延迟。

最佳实践：在 Compose 中使用 `Dispatchers.IO` 或自定义 dispatcher 包裹所有可能涉及 IPC 的操作，通过 `withContext(Dispatchers.IO) { ... }` 确保 binder 调用不阻塞主线程。

[适用版本: Android 12 - Android 17]
