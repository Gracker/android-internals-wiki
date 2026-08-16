---
title: "ANR 与 Kernel Trace 联合诊断"
chapter: "9.7"
section: "9.7"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [anr, ftrace, kernel-trace, atrace, perfetto, diagnosis, system-events]
related_chapters: ["9.3", "9.5", "13.8", "26.4"]
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

# 9.7 ANR 与 Kernel Trace 联合诊断

ANR trace（线程转储）回答“取样时各线程停在哪里”，Perfetto 回答“超时窗口内发生过什么”。两份证据处理的是两个时间尺度，联合诊断的目的，是把线程转储中的等待点放回调度、Binder、文件系统和块设备的时间线上。

`nativePollOnce`、`BinderProxy.transactNative` 和 `D` 状态都只是现象：

- 主线程停在 `nativePollOnce`，可能只是消息队列在正常休眠；若超时消息仍未执行，还要检查输入焦点、消息投递和取样延迟。
- 主线程等待同步 Binder，瓶颈可能在调用方、对端用户空间代码、对端调度、嵌套 Binder 调用或驱动路径。
- 线程处于 `D` 状态，说明它在不可中断睡眠中；块 I/O、direct reclaim（由申请内存的线程直接回收内存页）、驱动等待都可能产生这种状态。

因此，看到 native 帧不能直接判定“内核故障”。本章的平台实现以 `android-17.0.0_r1` 为核对版本，内核事件以 `android17-6.18-2026-06_r6` 为准。版本演进只用于解释旧设备差异。

## 1. ANR trace 的能力边界

Android 17 的 ANR 处理采用异步队列，并行安排目标进程的 early dump（优先线程转储）。检测路径把记录交给 `AnrHelper.appNotResponding()`；`AnrHelper` 先把目标进程的临时转储提交给 early-dump executor（执行器），再由 `AnrConsumer` 依次处理队列并调用 `ProcessErrorStateRecord.appNotResponding()`。后者设置 `notResponding` 状态、写入 `AM_ANR` EventLog、发出 Perfetto ANR instant（瞬时事件），随后组织目标进程、parent（父进程）、`system_server`、persistent（常驻系统进程）及 native interest（系统关注的 native 进程）转储。

这个实现解释了两个诊断现象：

- 目标进程的 early dump 更接近超时现场，后续进程的栈可能晚数秒。
- 排队超过 10 秒或开机 10 分钟内的记录会走 `onlyDumpSelf`（只转储目标进程），不能从“文件里没有对端栈”推导“系统没有尝试采集对端”。

`StackTracesDumpHelper` 对 Java 进程调用 tombstoned/ART 的 Java backtrace（调用栈）接口；Java 转储失败时才回退到 native backtrace。转储可以包含线程状态、Java 帧、native 边界和调度统计，但它仍是某个时间点附近的样本，缺少等待起点、唤醒者、run queue（CPU 运行队列）延迟和历史 Binder 事务流。

一份 ANR trace 可以可靠提供：

- 取样时的线程栈与 Java monitor（`synchronized` 使用的对象锁）关系；
- 主线程当时所处的用户态或 native 边界；
- 同一份转储中已采集进程的瞬时状态；
- trace header（文件头）、ANR reason（超时原因）和进程调度摘要。

它不能单独证明：

- 某个栈帧持续了整个超时窗口；
- `RUNNABLE` 线程一直占用 CPU；Java/ART 栈中的该状态不能区分线程正在运行还是等待调度，也不能给出整个窗口的 CPU 占用；
- `D` 状态由哪一个块请求导致；
- 同步 Binder 的耗时属于驱动、对端排队或对端业务代码；
- 转储时看到的状态就是触发超时那一刻的状态。

当栈已经给出完整证据链，例如主线程持锁做长计算且业务日志覆盖整个窗口，无需为每个 ANR 补抓内核事件。下面这些情况更适合引入 Perfetto：

- 主线程栈与超时原因对不上，怀疑 dump 到达时现场已经变化；
- 主线程在同步 Binder、`fsync`、page fault（缺页异常）、direct reclaim 或驱动等待附近；
- 主线程长时间处于 `R`/`R+`，但 CPU 运行片段很少；
- 多个进程同时卡顿，需要区分全局资源压力与单进程缺陷；
- 问题只在特定 SoC（片上系统）、存储介质、thermal（温控）状态或厂商内核上出现。

## 2. 采集前先定义问题

内核 trace 事件量很大。采集前至少记录以下信息：

1. ANR 类型和 timeout reason（超时原因）；
2. 目标包名、进程 PID、主线程 TID；
3. 需要覆盖的时间窗；
4. 想验证的假设，例如“主线程等 system_server 的同步 Binder”；
5. 目标 build fingerprint（系统构建标识）、平台 tag（版本标签）与 kernel release（内核版本）。

不同 ANR 的 deadline（完成期限）并不相同，不能固定向前看 5 秒。输入超时、广播、Service、ContentProvider 和 Job 的计时起点各有边界；窗口应从对应 timeout record（超时记录）或业务事件起点向后覆盖到系统识别 ANR。若起点未知，可以先抓取更宽的环形窗口，再用证据缩小范围。

## 3. Android 17 中可用的数据源

### 3.1 atrace category 与 ftrace event

Android 17 的 `atrace.cpp` 定义了 category（事件类别）到 tracepoint（内核埋设的事件记录点）的对应关系。诊断时应区分“category 名称”和“内核 event 名称”。

| 目标 | Android 17 配置 | Perfetto 侧主要入口 | 能回答的问题 |
|---|---|---|---|
| ActivityManager 标记 | atrace `am`；Track Event `debug.anr` | `slice`（带起止时间的事件片段）、Track Event（自定义时间标记） | ANR instant、系统侧阶段与 error id（事件标识） |
| 调度 | atrace `sched` | `sched`、`thread_state` | 运行、Runnable、Sleep、D-state 各持续多久 |
| CPU 频率 | atrace `freq`，按需加 `idle` | CPU frequency/idle counters（计数器） | 当时的频点、idle 和频率上限 |
| Binder | atrace `binder_driver` | Binder slices、flow（跨线程关联线）、`android.binder` stdlib（标准查询库） | 调用方、对端、事务与回复的 wall time（实际经过时间） |
| 文件系统与 bio | atrace `disk` | raw ftrace（原始内核事件）、filesystem slices | sync、writeback（脏页写回）、bio queue/complete |
| 块请求 | 显式启用 `block/block_rq_*` | `ftrace_event` 与 `args` | request 的 insert（入队）、issue（下发）、complete（完成）阶段 |
| 内存回收 | atrace `memreclaim` | reclaim slices/raw ftrace | 主线程或系统是否进入 direct reclaim |

这里有三条容易混淆的实现细节：

- Android 17 的磁盘 category 叫 `disk`，没有名为 `block` 的 atrace category。
- `binder_driver` 只要求 transaction、received 和 alloc-buffer 事件。`binder_lock` 是另一个可选 category；`android17-6.18-2026-06_r6` 的 common kernel `binder_trace.h` 没有这些旧式全局锁事件。
- `ftrace_event` 的事件字段存放在 `args`（参数）表中，不能把 `debug_id`、`to_proc`、`sector` 当作 `ftrace_event` 的直接列。

### 3.2 先检查设备暴露了哪些 tracepoint

下面的命令用于检查目标设备是否暴露分析所需的 event，避免采集结束后才发现数据源缺失：

```bash
adb shell '
for event in \
  sched/sched_switch \
  sched/sched_waking \
  sched/sched_blocked_reason \
  binder/binder_transaction \
  binder/binder_transaction_received \
  block/block_rq_insert \
  block/block_rq_issue \
  block/block_rq_complete \
  power/cpu_frequency; do
  if [ -e "/sys/kernel/tracing/events/$event/enable" ]; then
    echo "yes $event"
  else
    echo "no  $event"
  fi
done'
```

`no` 可能来自内核配置、厂商裁剪、权限或 tracefs（内核追踪文件系统）挂载路径差异。它表示该设备无法按当前方式采集，不能写成“事件没有发生”。

### 3.3 推荐的 Perfetto 配置

下面的 textproto（Perfetto 文本配置格式）用于实验室复现。它保留调度、Binder、块请求、频率、idle 和 reclaim 事件，并抓取进程与线程的对应关系：

```textproto
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 30000

data_sources {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      atrace_categories: "am"

      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"

      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_transaction_alloc_buf"

      ftrace_events: "block/block_rq_insert"
      ftrace_events: "block/block_rq_issue"
      ftrace_events: "block/block_rq_complete"
      ftrace_events: "block/block_bio_queue"
      ftrace_events: "block/block_bio_complete"

      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_frequency_limits"
      ftrace_events: "power/cpu_idle"

      ftrace_events: "vmscan/mm_vmscan_direct_reclaim_begin"
      ftrace_events: "vmscan/mm_vmscan_direct_reclaim_end"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    target_buffer: 0
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}

data_sources {
  config {
    name: "track_event"
    target_buffer: 0
    track_event_config {
      enabled_categories: "debug.anr"
    }
  }
}
```

`debug.anr` 是 Android 17 `PerfettoCategories.ANR_CATEGORY` 的 category 名。64 MB 环形缓冲和 30 秒时长只是复现起点。应根据设备事件速率、丢事件统计、问题周期和内存预算调整，不能把这组数值直接搬到线上。

临时复现也可以用 atrace 快速抓取。下面的命令会在设备上抓 30 秒并把输出保存到主机：

```bash
adb shell atrace -z -b 32768 -t 30 \
  sched freq idle binder_driver disk memreclaim am \
  > anr-repro.atrace
```

`-b 32768` 的单位是 KB。atrace 对各 category 的覆盖由目标版本 `atrace.cpp` 决定；若要拿到 `block_rq_insert/issue/complete`，应使用前面的显式 Perfetto 配置。

## 4. 建立可靠的时间参照

Android 17 的 `ProcessErrorStateRecord` 在 ANR 处理中写入 `AM_ANR` EventLog，并通过 Perfetto SDK 发出名为 `ANR Detected` 的 instant（没有持续时间的瞬时事件），参数可以包含 `anrId`、`errorId`、timeout、PID。这个 instant 比“猜一个 `am_anr` slice 名”可靠，但它仍可能受 feature flag（功能开关）、ANR 路径和 trace category 影响。

建议按下面的优先级定位：

1. 在 Perfetto 中搜索 `ANR Detected`，核对 PID、ANR id 或 error id；
2. 用 `AM_ANR`、stats atom（系统统计事件）、系统日志和 timeout reason 交叉确认；
3. 用 ANR 文件 header 辅助对齐，不把文件写入时间当成检测时刻；
4. 缺少系统 instant 时，用应用自定义 Track Event 标记输入、生命周期或任务起点。

Perfetto SQL 的 `ts` 使用 trace 内部时钟，EventLog 和日志文件常带 wall clock（日期时间）。手工对齐不同产物时，应使用 trace 中的 clock snapshot（时钟对应关系快照）或同一个业务标记做换算，不能直接拿“纳秒 ts”和日期字符串相减。

## 5. 从主线程状态开始

### 5.1 `sched` 与 `thread_state` 各自表示什么

`sched` 的每一行表示某线程在 CPU 上运行的一段时间，线程键 `utid` 是 Perfetto 在本次 trace 内分配的线程标识。`end_state` 表示该运行片段结束后进入的状态：

| 值 | 含义 |
|---|---|
| `R` / `R+` | 离开 CPU 后仍可运行，常见于抢占或时间片结束 |
| `S` | 可中断睡眠，等待唤醒 |
| `D` | 不可中断睡眠 |
| `X` / `Z` | 退出或 zombie（进程已结束但退出状态尚未被父进程回收） |
| `NULL` | trace 在该片段结束前停止 |

`end_state` 不会用 `Running` 表示当前片段；行本身就是 Running 区间。需要统计等待时间时应查询 `thread_state`，该表会提供 `Running`、`R`、`S`、`D` 等状态区间。

下面的 SQL 用于列出目标进程主线程在分析窗口内的状态，并把跨越窗口边界的 slice 裁剪到窗口以内：

```sql
WITH
params AS (
  SELECT
    'com.example.app' AS process_name,
    123000000000 AS window_start,
    133000000000 AS window_end
),
target AS (
  SELECT t.utid
  FROM thread t
  JOIN process p USING (upid)
  JOIN params
  WHERE p.name = params.process_name
    AND t.is_main_thread = 1
  LIMIT 1
)
SELECT
  MAX(s.ts, params.window_start) AS ts,
  MIN(s.ts + s.dur, params.window_end)
    - MAX(s.ts, params.window_start) AS dur,
  s.state,
  s.io_wait,
  s.blocked_function
FROM thread_state s
JOIN target USING (utid)
JOIN params
WHERE s.dur > 0
  AND s.ts < params.window_end
  AND s.ts + s.dur > params.window_start
ORDER BY ts;
```

把三个参数替换为 trace 中的包名和时间边界。结果先描述“线程经历了什么状态”，根因仍需与栈、Binder flow、reclaim、I/O 和 CPU 负载在时间上对齐。

下面的聚合查询用于计算窗口内各状态的时长分布：

```sql
WITH
params AS (
  SELECT
    'com.example.app' AS process_name,
    123000000000 AS window_start,
    133000000000 AS window_end
),
target AS (
  SELECT t.utid
  FROM thread t
  JOIN process p USING (upid)
  JOIN params
  WHERE p.name = params.process_name
    AND t.is_main_thread = 1
  LIMIT 1
),
clipped AS (
  SELECT
    s.state,
    MIN(s.ts + s.dur, params.window_end)
      - MAX(s.ts, params.window_start) AS clipped_dur
  FROM thread_state s
  JOIN target USING (utid)
  JOIN params
  WHERE s.dur > 0
    AND s.ts < params.window_end
    AND s.ts + s.dur > params.window_start
)
SELECT state, SUM(clipped_dur) / 1e6 AS duration_ms
FROM clipped
GROUP BY state
ORDER BY duration_ms DESC;
```

运行占比没有通用的 30% 分界线。10 秒窗口里主线程只运行 50 ms，可能是在等待一个正常的异步结果，也可能遭遇调度饥饿；必须结合它在等待什么、何时被唤醒，以及完成期限是否已经到期。

### 5.2 Runnable 时间

`thread_state.state` 为 `R` 或 `R+` 时，线程具备运行条件却没有占用 CPU。长 Runnable 区间要继续检查：

- 同期哪些进程消耗了 CPU；
- 目标线程的 nice（普通调度优先级）、cgroup（控制组）、uclamp（CPU 性能需求上下限）和调度策略；
- 是否有实时线程、长 IRQ（硬件中断）或 vendor driver activity（厂商驱动活动）；
- CPU 是否 online（已启用），频率上限是否受 thermal/power policy（温控或功耗策略）约束；
- 唤醒发生在哪个 CPU，线程迁移是否频繁。

下面的查询用于列出窗口内 CPU 时间最高的进程：

```sql
WITH params AS (
  SELECT
    123000000000 AS window_start,
    133000000000 AS window_end
)
SELECT
  COALESCE(p.name, '[kernel]') AS process_name,
  SUM(
    MIN(s.ts + s.dur, params.window_end)
      - MAX(s.ts, params.window_start)
  ) / 1e6 AS cpu_ms
FROM sched s
JOIN thread t USING (utid)
LEFT JOIN process p USING (upid)
JOIN params
WHERE s.dur > 0
  AND s.ts < params.window_end
  AND s.ts + s.dur > params.window_start
GROUP BY process_name
ORDER BY cpu_ms DESC
LIMIT 20;
```

这里统计的是各 CPU 上运行时间的总和，多核设备的 `cpu_ms` 可以高于实际经过的窗口时长。排名只能说明同期有哪些 CPU 竞争者，不能仅凭 `sched_switch.next_pid` 指认“谁抢走了主线程的 CPU”。

### 5.3 `sched_blocked_reason`

在 `android17-6.18-2026-06_r6` 中，`sched_blocked_reason` 的注释和事件定义都限定为 uninterruptible sleep（不可中断睡眠）。事件字段为：

- `pid`：被记录的线程；
- `caller`：`__get_wchan()` 得到的内核等待位置；
- `io_wait`：该 task（内核任务）当时的 `in_iowait` 标记。

Perfetto 会把可解析结果放入 `thread_state.blocked_function` 和 `io_wait`。它不会为普通的 `S` 状态 futex（快速用户态互斥锁）等待提供通用调用栈，`futex_wait_queue_me` 也不应列作 D-state 的固定模式。

`blocked_function` 只是等待位置线索。`io_schedule`、文件系统 wait、driver completion（驱动完成回调）或 reclaim 函数，都要结合相邻事件和符号化质量（地址能否正确解析为函数名）解释。`io_wait=1` 能增强 I/O 假设，却不能标识某个具体 request（请求）。

### 5.4 CPU 频率与 thermal

低频本身不能证明 thermal throttling（温控限频）。线程休眠或负载很低时，DVFS（动态电压频率调节）主动降频是正常行为。认定 thermal 影响至少需要同时满足：

- 目标线程存在持续 Runnable 等待或业务工作量；
- `cpu_frequency` 与 `cpu_frequency_limits` 显示可用上限下降；
- thermal zone（温度区域）、cooling device（限频或散热控制设备）或厂商 power/thermal track 在同一时间变化；
- 高频竞争、CPU hotplug（CPU 核动态上下线）和 idle 无法更好地解释现象。

如果 trace 只采到了 `cpu_frequency`，结论应写成“低频与延迟时间重合，thermal 原因待补证”。

## 6. Binder：拆开客户端等待与服务端处理

同步 Binder 的客户端 wall time（从调用开始到返回的实际经过时间）包含多段：

1. 客户端组包和进入驱动；
2. 事务投递及服务端 Binder 线程获得运行机会；
3. 服务端方法执行，期间还可能发起嵌套 Binder；
4. reply 投递；
5. 客户端线程重新被调度。

`binder_transaction` 在发送事务的线程上下文触发，Android 17 common kernel 字段包括 `debug_id`、`target_node`、`to_proc`、`to_thread`、`reply`、`code` 和 `flags`。发送方 PID 不在 payload（事件携带的数据字段）中，应通过 `ftrace_event.utid` 关联 `thread`、`process`。`binder_transaction_received` 只带相同的 `debug_id`。

从 send 到 received 的间隔不等于纯驱动执行时间，它还包含接收线程取得事务、获得 CPU，并运行到 received tracepoint 之前的等待。固定用 10 ms 判定“驱动竞争”，会把调度和线程池排队时间误算到驱动。

### 6.1 优先使用 Perfetto Binder 标准库

Perfetto 会根据 Binder tracepoint 生成 transaction slice 和 flow。下面的查询用于查看目标进程在窗口内发起的 Binder 调用：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_ts,
  client_dur / 1e6 AS client_wall_ms,
  client_process,
  client_thread,
  server_process,
  server_thread,
  server_dur / 1e6 AS server_wall_ms,
  aidl_name,
  interface,
  method_name
FROM android_binder_txns
WHERE client_process = 'com.example.app'
  AND client_ts BETWEEN 123000000000 AND 133000000000
ORDER BY client_dur DESC;
```

`client_wall_ms` 是客户端同步等待区间，`server_wall_ms` 是服务端处理并回复的实际经过时间。二者还需与双方 `thread_state` 联合分析：服务端长时间处于 `R`，更可能存在调度延迟；长时间 Running 表示执行量较大；`S` 则可能在等待锁或嵌套调用。

主机侧 Perfetto 工具支持较新的标准库时，可以加载 `android.binder_breakdown`，查看同一事务的延迟主要发生在 client 侧还是 server 侧：

```sql
INCLUDE PERFETTO MODULE android.binder;
INCLUDE PERFETTO MODULE android.binder_breakdown;

SELECT
  txn.client_ts,
  txn.client_process,
  txn.server_process,
  txn.aidl_name,
  breakdown.reason_type,
  breakdown.reason,
  SUM(breakdown.dur) / 1e6 AS duration_ms
FROM android_binder_txns txn
JOIN android_binder_client_server_breakdown breakdown
  USING (binder_txn_id)
WHERE txn.client_process = 'com.example.app'
GROUP BY
  txn.binder_txn_id,
  breakdown.reason_type,
  breakdown.reason
ORDER BY duration_ms DESC;
```

标准库会随 trace processor（Perfetto trace 解析器）演进。查询报“module/table 不存在”时，应升级主机侧 Perfetto 工具，原始 trace 无需重新采集。

### 6.2 原始事件用于核对，不直接引用虚构列

下面的查询用于确认 Binder 原始事件有哪些参数：

```sql
SELECT
  event.ts,
  event.name,
  thread.tid,
  process.pid,
  process.name AS process_name,
  args.key,
  args.int_value,
  args.string_value
FROM ftrace_event event
LEFT JOIN thread USING (utid)
LEFT JOIN process USING (upid)
JOIN args USING (arg_set_id)
WHERE event.name IN (
  'binder_transaction',
  'binder_transaction_received'
)
ORDER BY event.ts, args.key;
```

字段键名受 trace processor 版本影响，先查看 `args.key`，再编写 `EXTRACT_ARG()` 查询更稳妥。只有结合正确的 AIDL interface（接口）和该 build 生成的 transaction 常量，才能把 `code` 解释为具体方法。

### 6.3 判断路径

- 客户端长等待，服务端很晚才开始：检查服务端 Binder 线程可运行时间、线程池占用和调度压力。
- 服务端及时开始但执行很久：展开服务端 slice、嵌套 Binder、锁、I/O 和 CPU 栈。
- 服务端很快回复，客户端晚恢复：检查客户端 Runnable 时间、freezer（进程冻结机制）和优先级。
- 多个调用方同时等待同一服务：检查服务端共享锁、全局队列和资源依赖。
- trace 没有对应 transaction：核对采集窗口、PID/TID 复用、oneway（异步 Binder 事务）语义和 event 是否启用。

Binder 线程名随 Java/native 实现和进程而变化，不能只用 `Binder:<N>` 过滤。应以 flow、PID/TID 和事务 slice 为主。

## 7. I/O：区分调用点、文件系统和设备阶段

Java 栈停在 `FileDescriptor.sync()`、SQLite checkpoint 或资源读取附近，只能说明取样点接近 I/O。完整路径还可能经过 page cache（文件页缓存）、writeback（脏页写回）、文件系统 journal（日记账）、dm-crypt/dm-default-key（块设备加密层）、device mapper（设备映射层）、blk-mq（多队列块层）和 UFS 存储驱动。

### 7.1 `write()` 不等于立刻等待块设备

普通 buffered `write(2)`（缓冲写）往往把数据复制进 page cache 后返回。线程更容易在以下位置产生长等待：

- page fault 或内存分配进入 direct reclaim；
- dirty page throttling（脏页过多时限制继续写入）；
- `fsync`/`fdatasync` 等待数据和 metadata（元数据）持久化；
- SQLite transaction、WAL sync 或 checkpoint；
- direct I/O（绕过页缓存的直接读写）；
- 文件系统、device mapper 或驱动 completion。

因此，不能把每次 `write()` 描述为“主线程进入 D，直到 `block_rq_complete`”。

### 7.2 Android 17 / kernel 6.18 的块事件

块层用 request 表示送往设备的请求，用 bio 表示块 I/O 操作。`android17-6.18-2026-06_r6` 中的事件含义如下：

- `block_rq_insert`：request 即将插入队列；
- `block_rq_issue`：request 发送给 device driver；
- `block_rq_complete`：驱动报告 request 的一部分完成，可能仍有尚未完成的 bio；
- `block_bio_queue` / `block_bio_complete`：bio 进入块层及全部工作完成。

insert→issue 可以反映 request 在块队列中的一段等待，issue→complete 覆盖驱动可见的服务阶段。文件系统准备、page cache、reclaim、request merge（请求合并）、device mapper 和完成后的线程唤醒，都在这两个区间之外。

这些 raw event 没有一个能在所有事件中稳定使用的 request id。仅用 `dev + sector`（设备号与扇区号）配对，会在并发、merge、split（请求拆分）、重复访问同一扇区和 partial completion（部分完成）时发生错配。完成事件也常在 IRQ 或 kworker（内核工作线程）上下文触发，不能按 `ftrace_event.utid` 归属到最初发起 I/O 的应用。

下面的查询用于查看目标窗口内块事件的真实参数，避免进行依据不足的一对一配对：

```sql
SELECT
  event.ts,
  event.name,
  thread.name AS emitter_thread,
  process.name AS emitter_process,
  args.key,
  args.int_value,
  args.string_value
FROM ftrace_event event
LEFT JOIN thread USING (utid)
LEFT JOIN process USING (upid)
JOIN args USING (arg_set_id)
WHERE event.name IN (
  'block_rq_insert',
  'block_rq_issue',
  'block_rq_complete',
  'block_bio_queue',
  'block_bio_complete'
)
  AND event.ts BETWEEN 123000000000 AND 133000000000
ORDER BY event.ts, event.name, args.key;
```

拿到 `dev`、`sector`、`nr_sector`、`rwbs`、`comm` 和 error 等键后，可以按目标内核字段制作局部分析脚本。结论中要保留 merge 与 partial completion 带来的不确定性。

### 7.3 联合判断

一条可信的 I/O 归因通常包含四组证据：

1. 应用栈或用户空间 slice 指向同步 I/O；
2. 主线程 `thread_state` 在同一时间进入 D、reclaim 或同步等待；
3. 文件系统/bio/request 事件在窗口内出现异常长尾或排队；
4. request 完成、reclaim 结束或锁释放后，主线程被唤醒并继续执行。

若只有“主线程 D + 全机有慢 block request”，结论只能写到相关性。要证明因果，还需要 syscall（系统调用）或内核栈采样、文件系统 trace、device mapper 路径或可控复现实验。

固定的 4 KB/50 ms、1 MB/100 ms 阈值不适用于所有设备。判断设备是否变慢，要与同机型、同温度、同队列深度、同 request 类型的正常数据比较，并分开观察耗时分位数和明显偏离主体分布的样本。

## 8. 内存回收和全局压力

主线程 D-state 或耗时较长的 syscall 也可能来自 direct reclaim。采集 `mm_vmscan_direct_reclaim_begin/end` 后，检查：

- reclaim 是否发生在目标线程上下文；
- 回收区间是否与主线程等待重合；
- PSI memory（资源压力导致任务停顿的时间）、major fault（需要从存储载入页面的缺页）、kswapd（后台内存回收线程）、compaction（内存规整）和 swap/zram（交换区或压缩内存）是否同时上升；
- 多个前台进程是否一起变慢；
- 触发点是一次大分配、缺页，还是全局内存压力。

应用发起大分配与系统内存紧张可以同时成立，没必要把责任强行二分为“应用侧”或“系统侧”。修复可能包括降低内存峰值、把工作移出完成期限、避免同步触发缺页，也可能需要调整系统内存参数和 vendor（厂商）策略。

## 9. Android 17 的系统触发式 profiling

`ProfilingManager` 在 Android 15（API 35）成为公开的 profiling（性能剖析）API。Android 16（API 36）的 `ProfilingTrigger.TRIGGER_TYPE_ANR` 支持在系统识别 ANR 后、可能终止进程前，请求正在后台运行的 system trace 快照。它不会等 ANR 发生后才启动一份 trace，因此产物能否覆盖超时前的过程，取决于 system trace 是否已经运行、缓冲区保留情况、系统限流和设备配置。

下面的 Kotlin 代码用于 API 36 及以上注册全局结果 listener 和 ANR trigger：

```kotlin
if (Build.VERSION.SDK_INT >= 36) {
    val profilingManager =
        context.getSystemService(ProfilingManager::class.java)

    profilingManager.registerForAllProfilingResults(
        context.mainExecutor
    ) { result ->
        val path = result.resultFilePath
        // 在回调外检查结果状态、复制文件并执行合规上传。
    }

    profilingManager.addProfilingTriggers(
        listOf(
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_ANR
            )
                .setRateLimitingPeriodHours(24)
                .build()
        )
    )
}
```

结果只投递给通过 `registerForAllProfilingResults()` 注册的全局 listener（监听器）。触发与产物都不保证成功，应用还要处理 error code（错误码）、文件生命周期、重复注册、用户隐私和系统 rate limit（频率限制）。Android 17（API 37）的 `TRIGGER_TYPE_ANOMALY` 面向更广的系统异常，没有替代专用的 ANR trigger。

公开 SDK 中没有 `android.os.PerfettoManager`。开发调试可用 Perfetto CLI；普通应用的系统触发入口是 `ProfilingManager`。

## 10. 读懂 AnrHelper 带来的取样偏差

Android 17 的 `AnrHelper` 会对同一 PID 的 predump（预转储）、queued ANR（已排队记录）和正在处理的 ANR 去重，并由 consumer（队列消费者）串行处理记录。目标进程的 early dump 会尽早提交，完整 ANR 处理则可能排队。排队过久后只转储目标进程，是为了避免已经失去时效的大范围采集继续增加系统压力。

排障时应记录：

- ANR 检测时刻；
- early dump 的时刻；
- 完整 trace 中各 PID 段落的时间；
- `reportLatency`、dump duration（转储耗时）、超时或 fallback（回退路径）日志；
- 是否处于 `onlyDumpSelf`，或 silent/background ANR（不弹出前台 ANR 对话框的后台处理）路径。

这组时间能解释“ANR 时主线程被卡住，trace 却已经回到 `nativePollOnce`”一类矛盾。线程可能在 dump 到达前恢复，栈没有错，只是样本晚了。

## 11. eBPF 的适用边界

Android 的 eBPF 基础设施早于 Android 14。系统组件可以在内核配置、SELinux、BPF loader（加载器）和稳定性评估允许时，用 BPF 在内核事件发生时进行过滤和聚合。普通第三方应用不能随意加载 BPF 程序，也不能把它当作通用的 ANR SDK。

BPF 程序仍会在事件路径上执行，事件频率、map（BPF 键值存储）操作、栈采样和上报都会产生开销。若系统团队采用它辅助 ANR，需在目标内核与 SoC 上测量 CPU、内存、功耗、丢事件情况和 verifier（内核安全校验器）限制，并提供停用开关。

## 12. 从证据生成分类，不让分类替代证据

自动分类可以按下面的顺序产出“候选原因”：

1. 用 ANR instant、reason 和 PID 定义窗口；
2. 计算主线程 `thread_state` 分布；
3. 对长 `S` 检查 monitor、Binder flow 和嵌套调用；
4. 对长 `R` 检查 CPU 竞争、优先级、频率上限与 thermal 状态；
5. 对长 `D` 检查 `blocked_function`、reclaim、文件系统和 block 事件；
6. 对长 Running 检查用户态 slice、CPU sampling（定期采样调用栈）、GC 和业务阶段；
7. 输出证据、反证、置信度及仍缺的数据。

分类结果不应只写“Binder ANR”或“I/O ANR”。更便于采取行动的描述是：“主线程在输入期限的 4.2 秒内等待同步 Binder；server 线程晚 3.6 秒开始运行；同一窗口 server 的全部 Binder 线程持续处理请求；未发现客户端长 Runnable。”这样的结论能指向服务端线程池、共享锁或请求合并策略，也保留后续验证空间。

## 13. 生产采集策略

不同 SoC、kernel config（内核配置）、trace processor 和业务负载下的事件采集成本差异很大，不能套用固定百分比。上线前应覆盖目标设备组合并测量：

- tracing 开关前后的 CPU、功耗、帧时延和 Binder/I/O P95/P99（95%/99% 样本不超过的分位值）；
- 每秒 trace 字节数、buffer wrap（环形缓冲覆盖一轮）周期与 `ftrace` 丢事件数量；
- ANR 快照成功率、覆盖时长、文件大小和限流命中率；
- 低内存、thermal、存储压力下的额外扰动；
- 脱敏、保留期、上传网络与用户授权。

实践上可分三层：

- 开发复现：按假设显式开启完整事件，保留 CPU sampling 和用户空间业务标记；
- 灰度诊断：只在一部分设备上启用，并限制时长和触发频率，验证数据质量及开销；
- 线上快照：优先使用系统提供的 trigger-based capture（按系统事件触发采集），只解析已经采到的类别，不声称 ANR 后能补回未采集的历史事件。

每次修改 category 都应重新测量。设备提供某个 tracepoint，并不代表它适合持续开启；低频测试结果也不能外推到 Binder 或 I/O 请求集中出现的场景。

## 14. 一份联合诊断报告应包含什么

交付给应用、Framework 或内核团队时，报告至少包含：

- build fingerprint、它与 `android-17.0.0_r1` 的对应关系，以及内核与 `android17-6.18-2026-06_r6` 的对应关系；
- ANR 类型、reason、检测时刻、目标 PID/TID；
- ANR trace 中主线程栈及该段转储时间；
- Perfetto 分析窗口和时钟对齐方法；
- 主线程 Running/R/S/D 时长；
- Binder、reclaim、filesystem（文件系统）、block（块设备）、frequency（CPU 频率）、thermal 的相关证据；
- 能排除的假设；
- 结论置信度、缺失事件与下一次复现要增加的数据源。

联合诊断的价值来自时间一致性：线程栈说明取样位置，scheduler（调度器）说明线程何时能运行，Binder flow 说明跨进程依赖，filesystem/block 说明 I/O 经过了哪些阶段。只有这些证据在同一窗口互相支持时，才适合把“相关”提升为“根因”。

## 参考资料

- [Android Developers：诊断和修复 ANR](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android Developers：ProfilingManager trigger-based capture](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Android Developers：ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [Android Developers：ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [AOSP android-17.0.0_r1：AnrHelper](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java)
- [AOSP android-17.0.0_r1：ProcessErrorStateRecord](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessErrorStateRecord.java)
- [AOSP android-17.0.0_r1：StackTracesDumpHelper](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/StackTracesDumpHelper.java)
- [AOSP android-17.0.0_r1：PerfettoCategories](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerfettoCategories.java)
- [AOSP android-17.0.0_r1：atrace categories](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp)
- [AOSP android-17.0.0_r1：ProfilingManager](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [AOSP android-17.0.0_r1：ProfilingTrigger](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [Perfetto：CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Perfetto：SQL tables](https://perfetto.dev/docs/analysis/sql-tables)
- [Perfetto：Binder standard library](https://perfetto.dev/docs/analysis/stdlib-docs#android-binder)
- [Perfetto：Android trace query cookbook](https://perfetto.dev/docs/analysis/common-queries)
- [Android Common Kernel android17-6.18-2026-06_r6：sched trace events](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
- [Android Common Kernel android17-6.18-2026-06_r6：Binder trace events](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h)
- [Android Common Kernel android17-6.18-2026-06_r6：block trace events](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/block.h)
- [§9.3 ANR 分析方法](03-anr-analysis.md)
- [§9.5 ANR 案例集](05-case-studies.md)
- [§13.8 ftrace / atrace / trace_marker](../../part3-tools/ch13-perfetto/08-tracing-infrastructure.md)
- [§26.4 ANR 监控体系](../../part5-app/ch26-observability/04-anr-monitoring.md)
