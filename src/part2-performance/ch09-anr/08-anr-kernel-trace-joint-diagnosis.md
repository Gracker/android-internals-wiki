---
title: "ANR Kernel Trace 联合诊断与系统事件关联"
chapter: "9.8"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [anr, ftrace, kernel-trace, atrace, perfetto, diagnosis, system-events]
related_chapters: ["9.3", "9.5", "13.9", "26.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
drafted_date: "2026-06-05"
drafted_by: "openclaw-task2a"
last_verified: "2026-06-05"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: research
    path: "DeepResearch/2026-06-03-anr-monitoring-ftrace.md"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Trace.java"
  - type: aosp
    path: "frameworks/native/cmds/atrace/atrace.cpp"
  - type: aosp
    path: "external/perfetto/src/traced/"
  - type: research
    path: "intake/research-feeds/2026-04-02-19-ch09-anr-helper-aosp-pipeline.md"
  - type: research
    path: "intake/research-feeds/2026-04-02-19-ch09-profiling-manager-anr-trigger.md"
  - type: research
    path: "intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md"
---

# 9.8 ANR Kernel Trace 联合诊断与系统事件关联

ANR 诊断的标准流程是看 /data/anr/ 下的 Java 堆栈 dump（详见 9.3 节）。这套流程能解决大部分应用侧主线程阻塞的问题，但遇到以下场景就会卡住：主线程堆栈显示 `nativePollOnce` 或 `BinderProxy.transactNative`，看起来什么也没干，CPU 时间却被吃掉了；或者 ANR 发生时主线程根本不在运行——被调度器挂起了，或者卡在 D-state 等待 I/O 完成。

这些场景的共同特征是根因不在 Java 层，而在内核态：CPU 调度延迟、Binder 驱动层排队、block I/O 阻塞、内存压力导致的 direct reclaim。Java 堆栈 dump 看不到这些信息，需要 kernel trace（ftrace/atrace）配合 Perfetto 做端到端时序关联。

本节讲的就是怎么把 ANR 诊断从"看堆栈猜原因"推进到"时序关联定位"。9.3 节已经覆盖了基于 traces.txt 和 Perfetto 的基础分析方法，本节不再重复，而是聚焦在 kernel trace 数据源的选择、Perfetto 中的关联查询方法，以及 Binder / 调度 / I/O 三类系统侧 ANR 的诊断路径。Tracing 基础设施（ftrace 三种模式、atrace category、trace_marker 写入路径）的细节见 13.9 节。

## ANR 堆栈 dump 的信息边界

先明确 /data/anr/trace 文件能提供什么、不能提供什么，再决定什么时候需要引入 kernel trace。

**能看到的：**

- 各线程的 Java 调用栈。主线程在哪个 Java 方法上阻塞，锁信息（`- locked <0x...>`、`- waiting to lock <0x...>`），线程状态（TIMED_WAITING / WAITING / RUNNABLE 等）
- Binder 线程池中各线程的当前状态。哪些在等事务，哪些在处理事务
- 部分系统状态摘要：进程的 nice 值、前台的 Activity 名称

**看不到的：**

- **native/kernel 层耗时**：JNI 调用进入 native 后的执行路径，堆栈里只留一个 `native method` 占位。例如 `SharedPreferencesImpl.waitToFinish()` 调用 `fsync()` 进入内核，堆栈停在那里，无法判断是磁盘慢还是内核锁竞争
- **CPU 调度状态**：线程堆栈显示 RUNNABLE，但实际可能在 run queue 上排队等 CPU，也可能刚被 wake up 还没得到调度。堆栈里的线程状态和实际 CPU 运行状态之间有鸿沟
- **Binder 驱动层的排队情况**：堆栈能看到"在等 Binder 调用返回"，但看不到这个 transaction 在驱动层排了多久的队、对端服务线程池是否已满
- **I/O 阻塞的具体设备层信息**：知道卡在 I/O，不知道是哪个 block 设备、请求队列深度多少、是磁盘本身的延迟还是 I/O scheduler 的排队策略导致

**dump 过程本身的开销：** Android 17 中 ANR dump 的调用链是 `ActivityManagerService.appNotResponding()` → `AnrHelper.recordAnr()` → `StackTracesDumpHelper.dumpStackTraces()`。AnrHelper 使用独立的 `AnrConsumerThread` 异步处理，避免阻塞 system_server 主线程。但 dumpStackTraces() 需要向目标进程发送 SIGQUIT 信号、等待所有线程完成堆栈序列化、写入 /data/anr/ 文件——这个过程在中低端设备上可能引入 100-200ms 的额外 I/O 开销，在高频 ANR 场景下会叠加。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java]
[来源: intake/research-feeds/2026-04-02-19-ch09-anr-helper-aosp-pipeline.md]

判断是否需要引入 kernel trace 的简单标准：如果 /data/anr/trace 中主线程堆栈指向以下任一模式，就应该抓 Perfetto trace 做 kernel 级关联分析：

- `nativePollOnce`（主线程可能在等锁、等 Binder、等 I/O，但 Java 层看不到）
- `BinderProxy.transactNative` 或 `BinderInternal.transactNative`
- `FileOutputStream.write` / `FileDescriptor.sync` / `SharedPreferencesImpl.waitToFinish`
- 线程状态 RUNNABLE 但 ANR info 中 CPU 使用率异常低（说明被调度器挂起）

## ATrace/Ftrace 基础设施与 ANR 可见性

13.9 节详细拆解了 ftrace 的三种模式、atrace 的分类机制和 Perfetto 的数据流。这里只列 ANR 诊断场景下最常用的数据源和对应关系。

### ANR 诊断所需的 atrace tag

| atrace tag | 对应的 ftrace tracepoint | 在 Perfetto 中的表现 | ANR 诊断用途 |
|-----------|-------------------------|---------------------|-------------|
| `am` | 无（用户空间 tag） | `track_event` slice，进程名为 system_server | ActivityManagerService 的 ANR 检测、进程状态变更时间点 |
| `sched` | `sched_switch`, `sched_wakeup`, `sched_wakeup_new`, `sched_blocked_reason` | `sched` 表，线程状态的 slice 视图 | 主线程何时在运行、何时被调度出去、等多久才回来 |
| `freq` | `cpu_frequency`, `cpu_idle` | `cpu_frequency_counters` 表 | CPU 频率是否被 thermal 限频或 DVFS 降到最低 |
| `binder_driver` | `binder_transaction`, `binder_transaction_received`, `binder_lock` | `ftrace_event` 原始表（按 `name` 过滤） | Binder transaction 的发送/接收时序、驱动层锁竞争 |
| `block` | `block_rq_issue`, `block_rq_complete`, `block_rq_insert` | `ftrace_event` 原始表 | I/O 请求从提交到完成的延迟 |

[已验证: AOSP android-17.0.0_r1, frameworks/native/cmds/atrace/atrace.cpp k_categories]

**一个关键区别：** `binder_driver` 和 `block` 的 tracepoint 数据在 Perfetto 中只存在于 `ftrace_event` 原始表，不像 `sched_switch` 那样有专门的派生表。分析时需要用 SQL 直接查 `ftrace_event`，按 `name` 过滤事件类型。

### Perfetto 抓取配置

用 Perfetto 抓取 ANR 诊断所需的完整数据，最小配置需要以下数据源：

```
atrace categories: sched, freq, binder_driver, block, am
ftrace events: sched_switch, sched_wakeup, sched_blocked_reason,
               binder_transaction, binder_transaction_received,
               block_rq_issue, block_rq_complete,
               cpu_frequency, cpu_idle
```

用 Perfetto CLI 或 `android.os.PerfettoManager`（Android 17+）都可以指定这个配置。如果是用 `atrace` 命令直接抓：

```bash
atrace -b 32768 sched freq binder_driver block am -t 30
```

`-b 32768` 把 per-CPU buffer 设到 32MB，避免高频 sched 事件把 buffer 冲掉。30 秒的采集窗口通常够覆盖 ANR 发生前后的完整时序。如果 ANR 是偶发的，需要更长时间的采集，要把 buffer 进一步加大。

用 Perfetto 配置文件可以更精细地控制每个数据源的 buffer 分配和刷新策略。具体配置方法见 13.2 节。

## Perfetto 端到端 ANR 诊断流程

拿到 Perfetto trace 后，ANR 诊断的核心任务是：在时间线上定位 ANR 触发点，然后沿着时间轴向前回溯主线程的活动，逐 track 关联系统级事件。

### Step 1：定位 ANR 触发时间点

ANR 触发会在多个 track 上留下标记：

1. **android.anr slice**：如果系统在 ANR 时记录了 `am_anr` tag（atrace `am` category），Perfetto 的 system_server track 上会出现一个 `am_anr` slice，标注进程名和 ANR 原因
2. **ANR 对话框出现时间**：在 `activity` 相关的 track 上可以找到 ANR 对话框的显示时间，作为辅助定位
3. **SIGQUIT 信号时间**：/data/anr/trace 文件头通常包含 dump 时间，可以和 Perfetto trace 做时间对齐

定位到 ANR 时间点后，向前回溯 5-10 秒（ANR 的触发阈值是 5 秒无响应，但根因可能在更早就开始了），这段窗口就是要分析的核心区间。

### Step 2：主线程调度状态分析

Perfetto 的 `sched` 表可以直接看到主线程（按 tid 过滤）在每个时刻的状态：

```sql
-- 主线程在 ANR 窗口内的调度切片
SELECT ts, dur, cpu, end_state
FROM sched
WHERE tid = (SELECT tid FROM thread WHERE name = 'main' AND upid = (SELECT upid FROM process WHERE name = 'com.example.app'))
AND ts BETWEEN <anr_start_ns> AND <anr_end_ns>
ORDER BY ts;
```

`end_state` 列的含义（这些是 Linux 内核的调度状态缩写）：

| end_state | 含义 | ANR 关联 |
|-----------|------|---------|
| `R` / `R+` | Runnable（在 run queue 上等 CPU） | CPU 饥饿——主线程想运行但拿不到 CPU 时间 |
| `S` | Interruptible sleep（可中断睡眠） | 等 Binder 返回、等锁释放、等 futex |
| `D` | Uninterruptible sleep（不可中断睡眠） | 等 I/O 完成、等内存分配（direct reclaim） |
| `Running` | 正在某个 CPU 上执行 | 看它到底在干什么（需要结合用户空间 trace） |

### Step 3：多 track 关联定位根因

把主线程的调度状态和其他 track 放在同一时间线上：

- **主线程是 `D` state** → 查 `block` track，看对应的 I/O 请求延迟
- **主线程是 `S` state + 堆栈指向 `BinderProxy.transactNative`** → 查 `binder_transaction` 事件，追踪对端服务
- **主线程是 `R` state 但不 Running** → 查 CPU frequency track 和其他进程的 CPU 占用，判断是 thermal 限频还是 CPU 争抢
- **主线程 Running 但在做 GC** → 查 ART GC 相关的 counter track

### Step 4：区分应用侧和系统侧 ANR

一个实用的判断框架：

| 信号 | 根因在应用侧 | 根因在系统侧 |
|------|------------|------------|
| 主线程长时间 Running | 在做耗时操作（主线程 I/O、死循环、密集计算） | — |
| 主线程 `S` state 等 Binder | — | 对端服务慢或 Binder 驱动层排队 |
| 主线程 `R` 但不 Running | — | CPU 饥饿（调度器问题、thermal 限频） |
| 主线程 `D` state | 应用侧发起了不必要的同步 I/O | 设备 I/O 性能差或内核 I/O 调度问题 |
| CPU 频率持续低位 | — | thermal 限频或 DVFS 策略保守 |

"根因在系统侧"不意味着应用无能为力。Binder 调用慢可能是对端服务的接口设计问题，I/O 慢可能是数据存储方式的选择问题——这些都属于应用可以优化的范畴。但如果 CPU 频率被 thermal 限到最低，或者系统内存压力导致频繁 direct reclaim，这些是应用层无法直接解决的，需要系统级优化或硬件调整。

## Binder 驱动层 ANR 诊断

ANR 中最常见的模式之一：主线程发起一个同步 Binder 调用，对端处理慢，导致主线程超时。Java 堆栈能告诉你"在等哪个 Binder 接口"，但无法区分以下三种情况：

1. 对端服务真的在处理你的请求，只是慢（对端逻辑问题）
2. 对端服务的线程池已满，你的请求在排队（对端负载问题）
3. Binder 驱动层本身有锁竞争或 transaction 排队（系统瓶颈）

### binder_transaction 事件的解读

`binder_transaction` tracepoint 在每次 Binder transaction 发起时触发，记录以下关键字段：

- `debug_id`：transaction 的唯一标识，用于关联 send 和 receive
- `target_node`：对端 Binder 对象的 node id
- `to_proc` / `from_proc`：发送方和接收方的进程 PID
- `reply`：是否是回复 transaction
- `code`：接口方法编号（可以映射到具体的 AIDL 方法）

`binder_transaction_received` 在对端进程收到 transaction 时触发，带有相同的 `debug_id`。两个事件的时间差就是 transaction 在 Binder 驱动层的传输延迟。

### 诊断流程

用 Perfetto SQL 查询一段 Binder 调用的完整生命周期：

```sql
-- 查找主进程发起的 Binder transaction 及其接收时间
SELECT
  t1.ts AS send_ts,
  t2.ts AS recv_ts,
  (t2.ts - t1.ts) / 1e6 AS driver_latency_ms,
  t1.debug_id
FROM ftrace_event t1
JOIN ftrace_event t2 ON t1.debug_id = t2.debug_id
WHERE t1.name = 'binder_transaction'
  AND t2.name = 'binder_transaction_received'
  AND t1.from_proc = '<app_pid>'
ORDER BY t1.ts;
```

如果 `driver_latency_ms` 很高（>10ms），说明 Binder 驱动层有排队或锁竞争。如果驱动层延迟很低但对端处理时间很长，说明是对端服务本身的逻辑问题——需要去看对端进程的 CPU 时间和调度状态。

### 区分"对端慢"和"Binder 排队"

一个更完整的判断方法：

1. **看对端线程池的饱和度**：在 Perfetto 中过滤对端进程的 Binder 线程（通常叫 `Binder:<N>`），看它们的 CPU 占用率。如果所有 Binder 线程都在 Running，说明线程池满了，新请求在排队
2. **看 `binder_lock` 事件**：如果 Perfetto 中能看到 `binder_lock` / `binder_unlock` 事件，可以判断 Binder 驱动层的全局锁（`binder_proc_lock` 等）是否有竞争。不过这些事件在部分设备上默认不开启
3. **看 transaction 的 `code` 字段**：映射到具体的 AIDL 方法后，可以判断是哪个接口调用慢——是 `getWindowSession`、`getActivityToken` 还是 `getContentProvider`

[待验证: binder_transaction 的 code 字段到 AIDL 方法的映射关系因接口而异，需要对照 IActivityManager/IWindowManager 等 .aidl 文件确认]

## CPU 调度延迟与 ANR 关联

主线程堆栈显示 RUNNABLE，看起来在运行，但 CPU 使用率很低——这种 ANR 通常被归类为"CPU 饥饿"。Java 堆栈无法区分"线程在 CPU 上执行"和"线程在 run queue 上等 CPU"，需要看 kernel trace。

### sched 表的 ANR 诊断用法

Perfetto 的 `sched` 表记录了每个线程在 CPU 上的执行切片和状态切换。对 ANR 诊断来说，关键指标是：

- **Running 时间占比**：ANR 窗口内主线程实际在 CPU 上执行的时间占总窗口的百分比。如果低于 30%，说明大量时间在等调度
- **Run queue 延迟**：从 `sched_wakeup`（线程被唤醒）到 `sched_switch`（线程实际得到 CPU）之间的间隔。这个间隔就是调度延迟
- **被谁抢占**：`sched_switch` 事件记录了 next_pid（抢占者），可以判断是哪个线程/进程抢走了 CPU

```sql
-- 主线程在 ANR 窗口内的运行时间统计
SELECT
  SUM(CASE WHEN end_state = 'Running' THEN dur ELSE 0 END) / 1e6 AS running_ms,
  SUM(dur) / 1e6 AS total_window_ms,
  ROUND(100.0 * SUM(CASE WHEN end_state = 'Running' THEN dur ELSE 0 END) / SUM(dur), 1) AS running_pct
FROM sched
WHERE tid = <main_tid>
AND ts BETWEEN <anr_start_ns> AND <anr_end_ns>;
```

### sched_blocked_reason 的使用

`sched_blocked_reason` tracepoint 在线程因等待 I/O、锁、futex 等原因被阻塞时触发，记录阻塞原因的调用栈（kernel symbol）。这个事件在 Android 12+ 可用，需要在 Perfetto 配置中显式启用：

```
ftrace_events: "sched/sched_blocked_reason"
```

`sched_blocked_reason` 的 `call_site` 字段是一个内核地址，对应到 `/proc/kallsyms` 可以查出是哪个内核函数导致的阻塞。常见的模式：

- `call_site` 指向 `io_schedule` → I/O 阻塞（关联到 block layer 的事件）
- `call_site` 指向 `futex_wait_queue_me` → futex 锁等待（关联到用户空间的锁竞争）
- `call_site` 指向 `wait_for_completion` → 等待某个内核操作完成

[已验证: Linux kernel, include/trace/events/sched.h sched_blocked_reason]
[待验证: sched_blocked_reason 在 Android 设备上的默认启用状态可能因厂商而异]

### CPU 频率与 thermal 限频

主线程 Run queue 延迟高，不一定是 CPU 被其他进程占满，也可能是 CPU 频率本身被限制了。在 Perfetto 的 CPU frequency track 上看 ANR 窗口内的频率变化：

- 如果所有核心频率都持续在最低档（如 300 MHz），大概率是 thermal 限频。结合 thermal track 可以确认
- 如果频率正常但仍然调度不过来，检查是否有更高优先级的中断或实时线程在抢占 CPU

CPU 频率分析的详细方法见 13.13 节。

## I/O 阻塞 ANR 的 Kernel Trace 定位

主线程卡在 I/O 操作上导致 ANR 是常见模式。典型的触发路径：SharedPreferences 的 `apply()` 后立即调用 `waitToFinish()`（或 `commit()` 直接同步写）、SQLite WAL checkpoint、AssetManager 读取压缩资源。Java 堆栈能定位到 I/O 调用点，但无法回答"I/O 慢在哪一层"。

### block 层 tracepoint 的作用

`block_rq_issue` 和 `block_rq_complete` 两个 tracepoint 分别在 I/O 请求提交到块设备和 I/O 请求完成时触发。它们的配对使用可以精确测量每个 I/O 请求在设备层的延迟。

在 Perfetto 中查询主进程的 I/O 延迟：

```sql
-- 查找 ANR 窗口内目标进程的 I/O 延迟
SELECT
  issue.ts AS issue_ts,
  complete.ts AS complete_ts,
  (complete.ts - issue.ts) / 1e6 AS io_latency_ms,
  issue.bytes AS io_bytes,
  issue.device AS block_device
FROM ftrace_event issue
JOIN ftrace_event complete
  ON issue.dev = complete.dev AND issue.sector = complete.sector
WHERE issue.name = 'block_rq_issue'
  AND complete.name = 'block_rq_complete'
  AND issue.ts BETWEEN <anr_start_ns> AND <anr_end_ns>
ORDER BY io_latency_ms DESC;
```

`block_rq_issue` 的 `bytes` 字段可以看出 I/O 请求的大小——如果是 4KB 对齐的小请求但延迟很高（>50ms），说明设备响应慢或 I/O 队列深度太高。如果请求本身很大（>1MB），延迟高是正常的。

### 从 Java 层到 block 层的追踪路径

一个同步 `write()` 调用从 Java 到内核的完整路径：

```
FileOutputStream.write()
  → libcore.io.Linux.writeBytes() (JNI)
    → write(2) syscall
      → vfs_write() → ext4_file_write_iter() (或其他文件系统)
        → submit_bio() → generic_make_request()
          → block_rq_issue tracepoint 触发
```

主线程在 `write(2)` syscall 中进入 `D` state（uninterruptible sleep），直到 block 层完成 I/O。在 Perfetto 中可以看到：主线程的 sched slice 变为 `D` 状态的起始时间，和 `block_rq_complete` 的完成时间——两者的差值就是这次 I/O 的端到端延迟。

### 区分"磁盘慢"和"I/O 排队"

- **磁盘慢**：每个 I/O 请求的 `block_rq_issue` → `block_rq_complete` 延迟都很高（>100ms），即使队列深度只有 1。通常是 eMMC/UFS 设备性能差或固件问题
- **I/O 排队**：单个请求的延迟正常，但 `block_rq_issue` 和前一个请求的 `block_rq_complete` 之间有大段间隔，说明请求在排队。检查同一时间段内其他进程的 I/O 请求量——如果 system_server、mediaserver 等系统进程在大量读写，应用层的 I/O 请求就会排队等

## Android 17 ANR 监控增强

### ProfilingManager 系统触发式 ANR Profiling

Android 16（API 36）为 ProfilingManager 引入了 System Triggered Profiling 能力，Android 17 继承并扩展了这个功能。开发者可以在应用启动时注册 ANR 触发器：

```java
// Android 16+ 可用
ProfilingManager pm = getSystemService(ProfilingManager.class);
pm.addProfilingTriggers(
    new ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
        .setRateLimitingPeriodHours(1)  // 限制触发频率
        .build()
);
```

当系统检测到 ANR 时，ProfilingManager 自动启动 Perfetto trace 采集，捕获 ANR 发生**之前**的历史数据。这个能力解决了 ANR 不可预测导致手动 Profiling 难以捕获根因的痛点。

采集到的 trace 数据通过 `ProfilingManager.registerForTraceProfiling()` 回调提供给应用，可以用 Perfetto UI 分析。与手动抓取 trace 的区别在于：系统触发式采集能确保 trace 覆盖 ANR 发生前的关键时段，而不是开发者事后补救。

[已验证: developer.android.com/reference/android/os/ProfilingManager]
[来源: intake/research-feeds/2026-04-02-19-ch09-profiling-manager-anr-trigger.md]

### AnrHelper 异步化

Android 17 的 AnrHelper 继续沿用 Android 14 引入的 `AnrConsumerThread` 异步架构。ANR 事件的处理流程：AMS 检测超时 → 更新 `ProcessErrorStateRecord` 标记为 `notResponding` → 入队给 AnrHelper → `AnrConsumerThread` 执行 `dumpStackTraces()` 写入 /data/anr/。

这套架构的设计目标是把 stack trace 采集从 system_server 主线程卸载，避免 ANR 处理本身导致系统卡顿。但在高频 ANR 场景下（连续多个进程同时 ANR），`dumpStackTraces()` 的 I/O 开销会累积，系统仍然可能出现短暂的性能抖动。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java]

## 扩展

### eBPF 辅助 ANR 实时诊断

Android 14 引入的 eBPF 能力（详见 14.10 节）可以挂载到 `sched_switch`、`binder_transaction` 等 tracepoint 上，实现近似零开销的事件采集。与 Perfetto 的离线分析相比，eBPF 可以做实时过滤和聚合——例如只记录主线程的调度延迟超过 100ms 的事件，或者实时统计 Binder transaction 的 P99 延迟。

目前（Android 17）eBPF 在生产环境中的使用仍有限制：需要系统签名或特权才能加载 BPF 程序，应用层无法直接使用。但系统服务（如 system_server）可以利用 eBPF 实现 ANR 相关事件的实时采集，减少全量 trace 的性能开销。

### 自动化 ANR 根因分类

基于 Kernel Trace 数据，可以构建一个自动化 ANR 根因分类框架：

1. 提取 ANR 窗口内的主线程调度状态序列
2. 根据状态分布判断主要阻塞类型（I/O / Binder / CPU 饥饿 / GC）
3. 对每种类型做进一步的关联分析（I/O → block 设备延迟，Binder → 对端服务，CPU → thermal/争抢）

这个框架需要和线上 APM 系统集成。26.4 节（ANR 监控体系）覆盖了线上 ANR 捕获和上报的基础架构，本节补充的是如何利用 kernel trace 数据做更精细的根因分类。

### 生产环境 Kernel Trace 采集策略

Kernel trace 的性能开销是生产环境部署的主要障碍。按数据源的开销分级：

| 数据源 | 典型 CPU 开销 | 是否适合持续开启 |
|--------|-------------|----------------|
| `sched_switch` | 2-5% | ✅ 可以持续开启，buffer 管好就行 |
| `cpu_frequency` | <1% | ✅ 数据量小 |
| `binder_transaction` | 3-8% | ⚠️ Binder 调用频率高的设备开销大 |
| `block_rq_*` | 1-3% | ⚠️ I/O 密集场景开销上升 |
| `sched_blocked_reason` | <2% | ✅ 只在有阻塞时触发 |

推荐的混合策略：持续开启 `sched` + `freq` + `sched_blocked_reason`（总开销 <8%），ANR 触发时按需追加 `binder_driver` + `block`。Android 16 的 ProfilingManager TRIGGER_TYPE_ANR 可以实现这个"按需追加"的逻辑。

[待验证: 以上开销数据来自测试环境估算，不同 SoC 和内核版本可能有显著差异]
