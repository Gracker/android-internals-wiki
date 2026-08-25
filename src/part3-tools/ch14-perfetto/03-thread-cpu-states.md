---
title: 线程 CPU 状态分析
section: '14.3'
chapter: '14.3'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-08-13'
last_verified_against: AOSP android-17.0.0_r1 external/perfetto, android17-6.18-2026-06_r6, perfetto.dev (2026-08-13)
confidence: high
sources:
- type: blog
  path: https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/
- type: blog
  path: https://www.androidperformance.com/2022/01/21/android-systrace-cpu-state-runnable/
- type: blog
  path: https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-running/
- type: blog
  path: https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://perfetto.dev/docs/case-studies/scheduling-blockages
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/common/thread_state_tracker.cc
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/ftrace/ftrace_parser.cc
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/tables/sched_tables.py
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/sched/latency.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/sched/time_in_state.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/ftrace/ftrace_config.proto
- type: source
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h
- type: source
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h
- type: source
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c
tags:
- perfetto
- thread-state
- sched-switch
- running
- runnable
- sleep
- uninterruptible-sleep
- cpu-scheduling
related_chapters:
- '5.1'
- '14.1'
- '14.7'
- '14.9'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 线程 CPU 状态分析

线程状态回答的是“这段墙钟时间（wall-clock time，即现实经过的时间）里，线程是否具备运行条件，是否占着 CPU”。它不会自动回答线程在执行哪个函数、等待哪把锁或哪次 I/O。可靠的分析要把状态区间与 Slice（Trace 时间轴上的事件区间）、调用栈、唤醒者、Binder（Android 的进程间通信机制）、文件系统和设备事件放在同一时间范围内核对。

本文核对的源码基线是 Android 17 / API 37 / `android-17.0.0_r1` 的 Perfetto 导入逻辑和 `android17-6.18-2026-06_r6` 内核。旧平台也有调度事件，但字段、内核符号和标准库模块可能不同。

## 13.3.1 状态从哪里来

### Linux 状态与 Perfetto 状态分属不同层次

Linux 6.18 的 `include/linux/sched.h` 把 `TASK_RUNNING` 定义为 0。这个值既覆盖正在 CPU 上执行的任务，也覆盖具备运行条件的任务；只看 `task_struct->__state` 无法区分 Running 与 Runnable。

Perfetto 依靠事件补出时间线：

- `sched_switch` 说明前一个线程何时离开 CPU、下一个线程何时进入 CPU。Perfetto 把下一个线程记为 `Running`，并用 `prev_state` 为离开的线程打开后续状态区间。
- `sched_waking` 说明某个事件正在把线程变为可运行。Perfetto 关闭原来的阻塞区间，打开 `R`，并尽量记录 `waker_utid`、`waker_id` 和 `irq_context`。
- 下一次 `sched_switch` 选中该线程时，Perfetto 关闭 `R` 或 `R+`，打开 `Running`。

`utid` 是 Perfetto 在一份 Trace 内分配的线程唯一标识，`upid` 则是进程唯一标识；它们用于区分操作系统进程号（PID）或线程号（TID）被复用后的不同实例。`waker_utid` 标识执行唤醒动作的线程，`waker_id` 指向该唤醒线程当时的 `thread_state` 行，`irq_context` 标记唤醒是否发生在中断环境。这些标识只在当前 Trace 内有效。

`sched_slice` 从 CPU 视角记录“哪个 `utid` 在哪个 CPU 上运行多久，切出时是什么状态”。`thread_state` 从线程视角记录连续状态，并附带 CPU、I/O 等待、阻塞函数和唤醒者等可选字段。两张表中的 `dur = -1` 表示区间没有结束时间，常见于 Trace 结束或数据丢失；聚合时应排除。

### Android 17 中可见的状态

| Perfetto 状态 | 含义 | 能直接得出的事实 |
| --- | --- | --- |
| `Running` | 线程被调度在某个 CPU 上 | 该调度区间占用 CPU 时间线 |
| `R` | Runnable | 线程具备运行条件，尚未进入 CPU |
| `R+` | Runnable (Preempted) | 前一次切出被内核标为抢占式切换 |
| `S` | Sleeping | 线程处于可中断睡眠 |
| `D` | Uninterruptible Sleep | 线程处于不可中断睡眠 |
| `T` | Stopped | 线程被停止 |
| `t` | Traced | 线程受跟踪控制 |
| `X` / `Z` / `x` | 退出、僵尸或死亡相关状态 | 线程处于退出流程 |
| `I` / `P` / `W` / `K` / `N` | Idle（空闲任务）、Parked（停驻）、Waking（正在唤醒）、Wake Kill（可由致命信号唤醒）、No Load（不计入负载） | 特殊调度状态，按原始事件解释 |

状态名称应以详情面板或 SQL 字段为准。Perfetto UI 的颜色会受版本、主题和选中状态影响，不能把某种颜色当作稳定接口。

### `R+` 的源码边界

Tracepoint 是内核预先定义的静态事件记录点。Android 17 所用的 6.18 内核在 `sched_switch` Tracepoint 中按下面的逻辑编码抢占：

```c
if (preempt)
    return TASK_REPORT_MAX;

/* TP_printk() 在 TASK_REPORT_MAX 置位时追加 "+"。 */
```

这段逻辑把抢占式切出的线程统一呈现为 `R+`。它没有限定“线程必须在内核态”，也没有在 `R+` 中保存抢占者身份或抢占原因。时间片、调度类、优先级和唤醒抢占等因素还要结合同一 CPU 上随后的 `sched_slice`、线程优先级与调度策略判断。

`R` 也不等于“由睡眠刚刚唤醒”。线程在保持可运行状态时离开 CPU，同样可能产生 `R`。只有存在对应 `sched_waking` 和 `waker_utid` 时，才能讨论这次可运行区间的唤醒来源。

## 13.3.2 采集与 UI 读取

下面的配置通过 ftrace（Linux 内核跟踪机制）采集线程状态、唤醒、D 状态原因、频率和中断，适合十几秒的定点复现：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 15000

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      compact_sched {
        enabled: true
      }

      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_wakeup_new"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "sched/sched_process_exit"
      ftrace_events: "sched/sched_process_free"
      ftrace_events: "task/task_newtask"
      ftrace_events: "task/task_rename"

      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"

      ftrace_events: "irq/irq_handler_entry"
      ftrace_events: "irq/irq_handler_exit"
      ftrace_events: "irq/softirq_entry"
      ftrace_events: "irq/softirq_exit"

      symbolize_ksyms: true
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

`RING_BUFFER` 表示缓冲区写满后覆盖最早的数据，因此事件突增时可能丢掉 Trace 开头。`sched_switch` 是构建 Running 和切出状态的基础，`sched_waking` 补充唤醒与 Runnable 起点，`sched_blocked_reason` 补充 D 状态的 `io_wait` 和睡眠函数。`compact_sched` 使用紧凑格式记录高频调度事件，减少 Trace 体积。`symbolize_ksyms` 把内核地址解析成函数名；它要求 Perfetto 的特权采集进程 `traced_probes` 具备 root（超级用户）权限，或设备放宽 `kptr_restrict`（内核地址可见性限制）。权限不足时，调度状态仍可用，`blocked_function` 可能为空。

设备可能缺少某些 Tracepoint，量产构建也可能限制内核符号。录制后应检查 Trace Processor 自诊断用的 `stats` 表，重点看 `unknown_ftrace_events`、`failed_ftrace_events` 和 ftrace 丢包；如果同时启用了 `linux.perf`，还要看 Perf 采样丢失。空字段只能说明证据缺失，不能直接解释为“没有发生”。

在 UI 中有两个互补入口：

- CPU Scheduling 轨道按 CPU 展示 `sched_slice`。选中区间可查看 `utid`、CPU、优先级和 `end_state`，也能看到之前的 Runnable 延迟与唤醒信息。
- 进程下的 `Thread State` 轨道按线程展示 `thread_state`。选中状态可查看持续时间、CPU、`io_wait`、`blocked_function`、唤醒者和中断环境。

分析关键路径时，先固定业务 Slice 或 FrameTimeline 帧，再看该时间范围内的线程状态。FrameTimeline 是 Android 12 起记录预期帧与实际帧时间线的机制；Looper 是 Android 线程处理消息队列的循环。整条线程生命周期的状态占比通常会被 Looper 的正常睡眠主导，对一次掉帧或启动没有直接解释力。

## 13.3.3 Running：已被调度，不等于应用代码独占 CPU

`Running` 表示调度器让该线程占据某个 CPU 的任务时间线。它可能在用户态执行，也可能在系统调用或异常处理的内核态执行。硬中断（HardIRQ）会立即暂停当前任务去处理设备事件，但不一定发生 `sched_switch`；这段 IRQ 时间仍落在外层 Running 调度区间里。SoftIRQ 是随后处理延迟中断工作的机制，既可能在当前 CPU 的中断返回路径执行，也可能交给 `ksoftirqd` 内核线程。

因此，长 Running 区间需要分层验证：

- 应用或框架 Slice 能否解释这段工作。
- `linux.perf`（Perfetto 的 Linux perf 采样数据源）或 simpleperf（Android 原生性能采样器）样本中的 `cpu_mode` 和调用栈指向用户态还是内核态；`cpu_mode` 表示样本落在用户态、内核态或其他执行模式。
- 同一 CPU 的 IRQ / SoftIRQ 轨道是否覆盖其中一部分。
- 线程运行在哪个 CPU，该 CPU 的 `capacity`、频率和空闲状态如何；`capacity` 是调度器描述 CPU 相对计算能力的指标，不是实时利用率。
- 该区间是否位于启动、帧、输入或 Binder 的关键路径。

Running 长不等于算法有问题。一次必须完成的后台计算可以合法地占满 CPU；一段很短的 Running 也可能因为频繁唤醒、缓存失效或跨线程串行化而拖慢关键路径。

### 帧分析不要套固定毫秒阈值

60 Hz 的名义周期约为 16.67 毫秒，120 Hz 约为 8.33 毫秒，但单个 `doFrame` 的 Running 时间不能直接与这两个数字比较。帧还包含 Runnable、同步等待、`RenderThread`、GPU 和 SurfaceFlinger（Android 显示合成服务），调度偏移、刷新率切换与预测也会改变 deadline（截止时刻）。Android 12 及以上应读取 FrameTimeline 的 Expected / Actual Timeline（预期 / 实际帧时间线）和 overrun（实际帧超出预期截止时刻的时间），再回看线程状态。

### CPU 类型与频率只解释执行环境

CPU 编号与大小核布局由 SoC（System on Chip，系统级芯片）决定，不能把“0—3 是小核、4—7 是大核”写成通用规则。Perfetto 的 `cpu` 表可提供 `cluster_id`、`processor` 和 `capacity`，频率轨道提供该时刻的 kHz。相同频率下，不同微架构和容量的 CPU 吞吐量可能不同；高频也不证明线程负载高，因为 Governor（动态调频策略）、Boost（临时提高性能目标）与热策略都会影响频点。

手工绑核会缩小调度器可选 CPU 集合，还会受 cpuset、在线 CPU 和权限限制。亲和性（affinity）限定线程可以在哪些 CPU 上运行，cpuset 用控制组给一组任务划定可用 CPU，uclamp 则限制调度器看到的任务利用率提示范围。普通应用不应依赖 CPU 编号或固定亲和性。平台侧若要调整这些参数，应使用同场景 Trace 验证延迟、能耗和热稳定性。

## 13.3.4 Runnable：测量唤醒到运行的等待

Runnable 区间表示线程具备运行条件却未在 CPU 上执行。对由 `sched_waking` 打开的 `R`，其持续时间近似“被唤醒到被调度”的延迟；`R+` 则从抢占式切出持续到下一次运行。

Runnable 变长常见于：

- 所有合适的 CPU 都在运行其他任务，或高调度优先级、实时任务和 IRQ 持续占用。
- 线程的调度类（如普通公平调度或实时调度）、nice（普通调度任务的相对优先级）、cpuset、亲和性、uclamp 或厂商策略限制了可用 CPU 与竞争顺序。
- CPU 离线、热限制、频率降低或设备容量不足，使队列消化速度下降。
- 唤醒放置（线程被唤醒时选择目标 CPU）与负载均衡暂时保留线程所在 CPU，避免跨核迁移成本。
- cgroup（Linux 控制组）的 CPU 带宽配额、实时节流（限制实时任务持续占用 CPU）或其他资源控制延后执行。

看到空闲 CPU 也不能直接判定调度器错误。Perfetto 官方文档指出，普通 Linux 调度配置不保证严格 work-conserving；这个术语指“只要存在可运行任务和可用 CPU，就尽量不让 CPU 空闲”。调度器可能暂缓迁移，让线程留在原 CPU 复用缓存并降低迁移功耗，还要确认目标线程是否允许在那颗 CPU 运行。

### 查询每次运行前的 Runnable 延迟

Android 17 的 `sched.latency` 标准库把每个 Running 状态关联到它之前的 Runnable 状态。下面的查询列出 SystemUI 主线程最长的 20 次延迟：

```sql
INCLUDE PERFETTO MODULE sched.latency;

SELECT
  p.upid,
  running.ts AS running_ts,
  runnable.state AS runnable_state,
  ROUND(l.latency_dur / 1e6, 3) AS latency_ms,
  ss.cpu,
  ss.priority,
  wp.name AS waker_process,
  wt.name AS waker_thread,
  runnable.irq_context
FROM sched_latency_for_running_interval AS l
JOIN thread_state AS running
  ON running.id = l.thread_state_id
JOIN thread_state AS runnable
  ON runnable.id = l.runnable_latency_id
JOIN sched_slice AS ss
  ON ss.id = l.sched_id
JOIN thread AS t
  ON t.utid = running.utid
JOIN process AS p
  USING (upid)
LEFT JOIN thread AS wt
  ON wt.utid = runnable.waker_utid
LEFT JOIN process AS wp
  ON wp.upid = wt.upid
WHERE p.name = 'com.android.systemui'
  AND t.is_main_thread
ORDER BY l.latency_dur DESC
LIMIT 20;
```

查询按 `upid` 区分同名进程的不同实例。`waker_process` 为空可能来自 `R+`、Trace 开头、数据丢失或缺少 `sched_waking`。`irq_context = 1` 表示唤醒事件发生在 HardIRQ 或 SoftIRQ 环境，此时当前任务名称通常不能代表业务上的唤醒发起者。

### 解读 `R` 与 `R+`

`R+` 多说明线程遭遇抢占式切换，但次数或占比高不能直接推出优先级设置错误。要查看切出后哪条任务在相同 CPU 上运行、它属于哪个调度类、目标线程允许在哪些 CPU 执行，以及这段等待是否越过业务 deadline。

`R` 包含唤醒后的排队，也可能来自线程保持可运行状态时的切出。具备 `waker_utid` 的 `R` 才能沿 UI 中的 Woken by（由谁唤醒）关系查看唤醒线程。唤醒者负责把线程变为可运行，不一定是锁持有者、Binder 服务端或设备中断的源头；这层业务关系还需 Binder Flow（Binder 事务的跨线程因果连线）、锁事件或代码路径确认。

## 13.3.5 Sleeping：找到等待条件和唤醒者

`S` 是可中断睡眠。Looper 调用 `epoll_wait()` 等待文件描述符（进程访问文件、socket 等内核对象所用的编号）上的消息事件、线程等待条件变量或 futex（用户态锁常用的内核等待机制）、同步 Binder 客户端等待回复、定时器等待到期，都可能表现为 `S`。大多数线程长期 Sleeping 是健康的空闲状态。

关键 Slice 内出现长 `S` 时，可按以下证据追查：

- Slice 名称或事件触发采样栈说明线程在哪个等待 API 进入睡眠。
- `thread_state.waker_utid` 与 `waker_id` 指向哪个线程状态。
- Binder 事务、Monitor Contention（Java / Kotlin 监视器锁竞争）、futex、Flow（Trace 事件之间的因果连线）或定时器事件能否解释唤醒关系。
- 从唤醒到 Running 的 `R` 是否又贡献了明显调度延迟。

一次同步等待可以同时包含 `S + R + Running`：线程睡眠等待条件，条件满足后进入 Runnable，获得 CPU 后继续执行。只量 `S` 会漏掉唤醒后的排队。

### Woken by 的边界

Woken by 是 Perfetto UI 对唤醒来源的展示。Android 17 的 `ThreadStateTracker::PushWakingEvent()` 仅在被唤醒线程原本处于阻塞状态时关闭旧状态并打开 `R`。线程已处于 Running 或 Runnable 时收到的重复唤醒会进入 `spurious_sched_wakeup`（无须改变状态的重复唤醒记录），不会重写当前状态。

Woken by 记录的是执行唤醒动作的线程：

- 解锁路径中，它可能是释放锁的线程。
- Binder 回复中，它可能落在驱动或服务端执行路径。
- 中断唤醒中，`irq_context` 会标记 HardIRQ / SoftIRQ，当前被中断线程不应被当作设备事件的业务来源。
- 缺少事件、Trace 起点或 ftrace 丢包都会造成关系中断。

复杂等待可使用 UI 的 Critical Path（关键路径）视图辅助查看跨线程依赖。该视图根据唤醒关系推导路径，结果受 Trace 完整性影响，仍需回到原始状态、Slice 与代码确认。

Perfetto 官方的调度阻塞案例还展示了事件触发调用栈：用 `linux.perf` 在 `sched_switch` 和 `sched_waking` 发生时采样，并用 `prev_comm`、`next_comm` 或 `comm` 过滤目标线程；这里的 `comm` 是内核记录的任务名。若对全系统每次调度切换都取栈，采样器很快会跟不上事件速度，因此必须限制过滤范围并检查丢样统计。

## 13.3.6 Uninterruptible Sleep：D 只说明不可中断等待

Linux 6.18 把 `TASK_UNINTERRUPTIBLE` 定义为独立任务状态。处于该状态的普通信号不会让等待提前返回；条件满足后线程被唤醒，挂起的信号才有机会处理。内核还提供 `TASK_KILLABLE = TASK_WAKEKILL | TASK_UNINTERRUPTIBLE`，供允许致命信号唤醒的等待点使用。

D 状态可出现在块 I/O、Swap（交换区页面换入换出）、内存回收、页迁移、驱动等待和内核同步路径。Minor Page Fault（次缺页）通常表示所需页面已在内存中，不需要存储 I/O，也未必让线程睡眠；Major Page Fault（主缺页）可能等待文件页或 Swap 读入，仍需页故障和块设备证据。不能把所有 Page Fault 或所有 D 都归为磁盘。

### `io_wait` 与 `blocked_function` 的源码含义

锚点内核的 `sched_blocked_reason` Tracepoint 写入两个字段：

```c
__entry->caller = (void *)__get_wchan(tsk);
__entry->io_wait = tsk->in_iowait;
```

`io_wait` 来自任务的 `in_iowait` 记账标志。值为 1 能提高 I/O 等待的可能性，但不包含文件名、设备、请求类型或业务调用方；值为 0 也不能直接命名为“内核锁”。`caller` 来自 `__get_wchan()`，其中 wchan（wait channel）表示内核观察到的睡眠位置，不保证等于最初发起等待的应用函数或锁持有者。

Android 17 的 `FtraceParser::ParseSchedBlockedReason()` 把这两个字段写入最近的阻塞 `thread_state` 行。只有采集了该 Tracepoint 才会有 `io_wait`；只有内核符号成功解析时才会有 `blocked_function`。

### 查询 D 状态

下面的查询列出 SystemUI 主线程最长的 D 区间及其可用线索：

```sql
SELECT
  p.upid,
  ts.ts,
  ROUND(ts.dur / 1e6, 3) AS duration_ms,
  ts.io_wait,
  ts.blocked_function
FROM thread_state AS ts
JOIN thread AS t
  USING (utid)
JOIN process AS p
  USING (upid)
WHERE p.name = 'com.android.systemui'
  AND t.is_main_thread
  AND ts.state = 'D'
  AND ts.dur > 0
ORDER BY ts.dur DESC
LIMIT 20;
```

非 Running 状态没有“正在执行的 CPU”，需要从相邻调度区间或相关设备事件确定 CPU。`blocked_function` 为空时，应检查 Tracepoint、符号权限、数据丢失和工具版本；不能由空值推断“没有内核阻塞”。

归因 D 区间时，可按证据选择方向：

- `io_wait = 1` 且与块设备或文件系统事件重叠：继续查设备、inode（文件系统对象编号）、页故障、Swap 和发起调用栈。
- 内存回收、压缩或页迁移事件重叠：查看 PSI（Pressure Stall Information，资源压力停顿统计）、reclaim（内存回收）、compaction（内存页整理）和进程内存压力。
- `blocked_function` 指向驱动或同步路径：查对应子系统源码、等待条件与负责唤醒的执行路径。
- 多个线程等待同一资源：查持有者是否 Sleeping、Runnable 或被其他任务抢占，识别优先级反转（高优先级任务被持锁的低优先级任务间接拖延）和锁队列串行化。

D 状态不会直接触发 ANR（Application Not Responding，应用无响应）。ANR 由输入分发、服务、广播等框架监控条件触发；D 只有在阻止受监控工作按时完成时才会参与这条因果路径。不能给 D 单独套一个通用 ANR 秒数。

## 13.3.7 Stopped 与其他状态

`T` 常见于 `SIGSTOP`（强制暂停进程的信号）、Shell 作业控制或调试操作，`t` 表示被调试器等工具跟踪。它们在调试会话中可能完全符合预期。`Z` 表示退出后等待父进程回收的僵尸状态，短暂出现也不等于性能故障；持续堆积才需要检查父进程的回收逻辑。

`X`、`x`、`I`、`P`、`W`、`K`、`N` 属于退出或特殊调度状态。Perfetto 官方文档提醒，不是所有字符组合都有意义。遇到复合状态时，应保留原始 `end_state`，再对照锚点内核的 `TASK_*` 定义和产生该事件的代码。

## 13.3.8 IRQ / SoftIRQ：调度区间里的隐含执行

HardIRQ 在中断环境执行，会暂停当前 CPU 上的任务；SoftIRQ 可在中断返回路径执行，也可由 `ksoftirqd` 线程处理。HardIRQ 和在中断返回路径执行的 SoftIRQ 都不要求发生任务切换，外层线程在 `thread_state` 中仍可能连续显示 Running。把这整段 Running 都算成应用函数时间，会高估应用函数的执行时间。

下面的查询汇总已采集的 IRQ 与 SoftIRQ Slice：

```sql
SELECT
  tr.type AS interrupt_type,
  s.name,
  COUNT(*) AS event_count,
  ROUND(SUM(s.dur) / 1e6, 3) AS total_ms,
  ROUND(MAX(s.dur) / 1e6, 3) AS max_ms
FROM slice AS s
JOIN track AS tr
  ON tr.id = s.track_id
WHERE tr.type IN ('cpu_irq', 'cpu_softirq')
  AND s.dur > 0
GROUP BY tr.type, s.name
ORDER BY SUM(s.dur) DESC
LIMIT 30;
```

Android 17 的 Ftrace 导入器分别用 `cpu_irq` 和 `cpu_softirq` 轨道保存这些区间。汇总只能找出高频或长中断候选；判断它是否拖慢业务，还要计算中断区间与关键路径的时间交集，并结合网络、存储、显示或定时器对应的设备驱动和业务动作。

`ksoftirqd/<cpu>` 是每个 CPU 对应的可调度内核线程，它的 Running 会直接出现在 CPU Scheduling 轨道。统计时要区分 SoftIRQ 在中断返回路径中的执行与 `ksoftirqd` 执行，避免重复计算。

## 13.3.9 在业务区间内量化状态

线程整段生命周期的状态占比很少能定位一次卡顿。Android 17 的 `sched.time_in_state` 提供区间函数，可把线程状态裁剪到指定起止时间。下面的查询选取 SystemUI 主线程中最长的 `Choreographer#doFrame`，汇总该 Slice 内的状态：

```sql
INCLUDE PERFETTO MODULE sched.time_in_state;

WITH target AS MATERIALIZED (
  SELECT
    s.ts,
    s.dur,
    t.utid,
    p.upid
  FROM slice AS s
  JOIN thread_track AS tt
    ON s.track_id = tt.id
  JOIN thread AS t
    USING (utid)
  JOIN process AS p
    USING (upid)
  WHERE p.name = 'com.android.systemui'
    AND t.is_main_thread
    AND s.name GLOB 'Choreographer#doFrame*'
    AND s.dur > 0
  ORDER BY s.dur DESC
  LIMIT 1
)
SELECT
  target.upid,
  state,
  io_wait,
  blocked_function,
  ROUND(SUM(x.dur) / 1e6, 3) AS state_ms
FROM target
JOIN sched_time_in_state_for_thread_in_interval(
  target.ts,
  target.dur,
  target.utid
) AS x
GROUP BY target.upid, state, io_wait, blocked_function
ORDER BY SUM(x.dur) DESC;
```

`MATERIALIZED` 让 Trace Processor 先求值并复用 `target` 这段公共表表达式，`GLOB` 则按通配符匹配 Slice 名称。查询使用具体进程和 Slice，执行前应确认录制中确有 SystemUI 帧。`doFrame` 最长不等于最差用户体验帧；Android 12 及以上可以先由 FrameTimeline 的 overrun 选中错过 deadline 的 `frame_id`，再把帧区间交给状态函数。

### 从状态走到修改点

| 区间特征 | 下一组证据 | 可以形成的结论 |
| --- | --- | --- |
| Running 为主 | Slice、用户态/内核态调用栈、CPU capacity/freq（相对容量 / 频率）、IRQ | 哪段执行或中断贡献 CPU 时间 |
| `R` 为主 | waker、同 CPU 运行者、调度类、cpuset/affinity（CPU 集合 / 亲和性）、CPU 在线状态 | 唤醒后为什么未及时运行 |
| `R+` 为主 | 切出后的任务、优先级、实时与 IRQ 活动 | 哪类抢占与 deadline 重叠 |
| `S` 为主 | 阻塞栈、waker、Binder、锁、Flow、定时器 | 等待条件由谁满足 |
| `D` 为主 | `io_wait`、`blocked_function`、页故障、回收、块设备、驱动 | 不可中断等待发生在哪个内核路径 |
| IRQ / SoftIRQ 高 | 中断名称、CPU、设备驱动、业务时间范围 | 中断处理占用了多少关键区间 |

状态只是分析入口。结论至少应包含业务区间、`upid` / `utid`、状态持续时间、至少一种能够解释原因的独立旁证，以及修改前后的同条件对照。

## 13.3.10 常见误读

### “线程 Running 占比高，所以它有性能故障”

Running 只表示线程被调度。还要确认它是否位于关键路径、执行内容是否可以减少，以及 IRQ 是否占用其中一部分。后台吞吐任务的高 CPU 使用率可能符合设计。

### “Runnable 长就是调度器选错”

Runnable 时长是观察到的排队结果。系统负载、调度类、优先级、亲和性、cpuset、CPU 容量、热限制、带宽控制和唤醒放置都可能贡献延迟。只看到空闲 CPU 也不足以判断，因为目标线程未必允许迁移过去。

### “`R+` 就是某条高优先级线程抢占”

`R+` 只保存这次切出带有抢占标志。具体抢占者和原因需要查看相同 CPU 上后续运行的任务、调度类和优先级。

### “Sleeping 不消耗 CPU，所以不影响性能”

空闲线程 Sleeping 很正常。关键路径中的 Sleeping 会增加墙钟时间，需要查等待条件、唤醒者和唤醒后的 Runnable 延迟。

### “D 或 `io_wait = 1` 就是应用磁盘 I/O”

D 覆盖多种不可中断等待，`in_iowait` 也是内核记账标志。应用归因还要依赖调用栈、页故障、文件系统、块设备或驱动事件。

### “把各进程 CPU 利用率相加后应小于 100%”

CPU 时间若以 Trace 墙钟时间为分母，多核进程可以超过 100%，全系统上限接近在线 CPU 数乘以 100%。报告必须写清百分比的分母：是按单核墙钟时间归一化、按设备总 CPU 容量归一化，还是直接报告 CPU 时间。

## 参考资料

- [Perfetto：CPU Scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Perfetto：用调度事件和调用栈分析阻塞](https://perfetto.dev/docs/case-studies/scheduling-blockages)
- [Android 17 `ThreadStateTracker` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/common/thread_state_tracker.cc)
- [Android 17 Ftrace Parser 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/ftrace/ftrace_parser.cc)
- [Android 17 `thread_state` 表定义](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/tables/sched_tables.py)
- [Android 17 `sched.latency` 标准库](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/sched/latency.sql)
- [Android 17 `sched.time_in_state` 标准库](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/sched/time_in_state.sql)
- [Android 17 `FtraceConfig` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/ftrace/ftrace_config.proto)
- [Android 17 / Linux 6.18 `TASK_*` 定义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h)
- [Android 17 / Linux 6.18 调度 Tracepoint 定义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
- [Android 17 / Linux 6.18 调度器主流程](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c)
- [高爷：Android Perfetto 系列 9，CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)
- [高爷：Systrace Runnable 分析](https://www.androidperformance.com/2022/01/21/android-systrace-cpu-state-runnable/)
- [高爷：Systrace Running 分析](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-running/)
- [高爷：Systrace Sleep 与 Uninterruptible Sleep 分析](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/)
