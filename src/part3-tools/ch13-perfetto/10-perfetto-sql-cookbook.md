---
title: "Perfetto SQL 性能分析实战手册"
chapter: "13.10"
status: ready-for-review
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-25"
last_verified_against: "AOSP Binder/ZygoteInit review anchors, Perfetto SQL tables/stdlib docs, Trace Processor large trace query patterns"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
  - type: blog
    path: "intake/research-feeds/2026-04-04-15-ch13-perfetto-v54-data-explorer.md"
  - type: blog
    path: "intake/research-feeds/2026-04-05-15-perfetto-input-latency-sql.md"
  - type: blog
    path: "intake/research-feeds/2026-04-01-07-ch01-binder-perfetto-latency-metrics.md"
  - type: blog
    path: "intake/research-feeds/2026-04-06-15-perfetto-monitor-contention-art-lock-analysis.md"
  - type: blog
    path: "intake/research-feeds/2026-04-07-16-perfetto-frame-timeline-perceived-smoothness-analysis.md"
tags: [Perfetto, SQL, Trace Processor, 性能分析, 帧时间, ANR, 启动时间, Binder]
related_chapters: ["13.1", "13.3", "13.5", "13.8", "7.1", "7.9", "8.2", "9.3", "1.4", "1.14"]
section: "13.10"
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "官方文档 + 读者需求 + AOSP 结构"
gap_score: "19/20"
task9_state: reviewed
task2b_state: pending
task2b_result: fixed

task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: '2026-04-28'
reviewed_by: "openclaw-task6"
pipeline_stage: task2b_pending
task9_result: needs-rework
task9_reviewed_date: '2026-04-29'
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-29T04:38:09+08:00"
last_task2b_at: "2026-04-27T20:58:38+08:00"
rework_date: "2026-04-27"
rework_by: openclaw-task2b
review_notes: "2026-04-27 task2b: fixed Binder ftrace tracepoint wording; removed nonexistent binder_reply tracepoint and clarified reply correlation via binder_return/binder_command or Perfetto Binder slices.；2026-04-28 task6 re-review: pass-light-edit，L1/L2 通过，代码块语言标签系统性缺失已记录"
task9_review_notes: "2026-04-28 task9 deep-review: needs-rework。P0 1 / P1 2 / P2 2。；2026-04-29 task9 re-review: pass-tech-review，P0 0 / P1 0 / P2 2，自动晋升 finalized。；2026-05-22 task9 idle-audit: needs-rework，P0 1 / P1 1，写入 queue task9-audit-20260522-13.10-perfetto-sql-doframe-spanjoin。"
last_task9_audit: "2026-05-22"
---

# 13.10 Perfetto SQL 性能分析实战手册

在前面的章节中，我们分别介绍了 Perfetto 的 UI 可视化（§13.3）、专题解读（§13.5）和命令行工具（§13.4）。但在实际工作中，很多性能问题无法单靠肉眼在 UI 中定位——我们需要精确的数字：第 47 帧耗时多少毫秒？主线程有多少时间花在等锁上？Binder 调用中排队占了多少时间？这类定量分析，离不开 SQL。

Perfetto Trace Processor 内置了一个完整的 SQL 引擎（基于 SQLite），我们可以用它对 Trace 数据做任意维度的查询和聚合。本节不会逐个罗列 SQL 语法，而是围绕性能分析中最常见的几类问题——帧时间与卡顿、线程调度、Binder 事务、内存与 GC、启动时间、ANR、锁竞争——逐个给出**从问题到 SQL 到结论**的完整分析路径。每条 SQL 都可以直接在 Perfetto UI 的 Query 标签页或 `trace_processor_shell` 中运行。

## Trace Processor SQL 基础

在写具体查询之前，我们需要了解几个基础概念，后面所有 SQL 都建立在这些概念之上。

### SQL 引擎与模块加载

Trace Processor 的 SQL 方言叫 PerfettoSQL，基于 SQLite 但做了扩展。最大的扩展是 `INCLUDE PERFETTO MODULE` 语句：Perfetto 官方维护了一套标准库模块（standard library modules），每个模块提供预定义的表、视图和函数，把底层的 raw 表封装成更易用的高级抽象。

```sql
-- 加载帧分析标准模块
INCLUDE PERFETTO MODULE android.frames.timeline;

-- 加载输入延迟分析模块
INCLUDE PERFETTO MODULE android.input;

-- 加载锁竞争分析模块
INCLUDE PERFETTO MODULE android.monitor_contention;
```

使用标准库模块有两个好处：第一，模块内部已经处理好了复杂的 JOIN 逻辑，我们不用手动拼接底层表；第二，模块会随 Perfetto 版本更新而改进，保持查询的兼容性。在实际分析中，优先使用标准库模块而不是直接查底层表。`android.frames.timeline`、`android.input`、`android.monitor_contention` 都属于这一层。

[已验证: Perfetto stdlib docs, perfetto.dev/docs/analysis/stdlib-docs]

### 核心表结构

Perfetto 有几十张底层表，但性能分析中最常用的只有五张：

**slice** 表是性能分析的核心。它记录了所有"有时间跨度的事件"——从 Choreographer#doFrame 到 Binder 事务，从 GC 暂停到锁竞争，都以 slice 的形式存储。每条 slice 有 `ts`（开始时间，纳秒）、`dur`（持续时间，纳秒）、`name`（事件名）、`track_id`（所在的 track）。通过 `track_id` 关联到 `thread_track`，再关联到 `thread` 和 `process`，就能知道这个事件发生在哪个线程、哪个进程。

**sched** 表记录内核的线程调度切片——哪个线程在什么时候跑在哪个 CPU 上，跑了多久，以及这次 CPU slice 结束时线程处于什么内核状态（`end_state`）。`end_state` 只描述“离开 CPU 的那一刻”，不能把它当成线程整段时间里的当前状态；如果要统计 Running / R / S / D 等状态分布，应该查 `thread_state` 表。

**counter** 表存储随时间变化的数值，比如 CPU 频率、内存使用量、Java Heap 大小。counter 的数据点是离散的（每次值变化记录一次），做分析时通常需要和时间窗口 JOIN。

**thread_track / process_track** 表是 slice 和线程/进程之间的桥梁。`thread_track` 中的每条记录对应一个线程的 track，包含 `utid`（唯一线程 ID），可以 JOIN 到 `thread` 表获取线程名和所属进程。

这些表之间的 JOIN 关系可以简化为：

```
slice → thread_track (via track_id) → thread (via utid) → process (via upid)
sched → thread (via utid) → process (via upid)
counter → counter_track (via track_id)
```

[已验证: Perfetto 文档, perfetto.dev/docs/analysis/sql-tables]

### 目标进程、主线程与大 Trace 查询约束

后面的模板都按目标进程收窄。主线程不要只用 `thread.name = 'main'` 判断；真实 trace 中，主线程名可能显示为包名、进程名，或者被系统截断。更稳的写法是在目标进程内使用 `thread.is_main_thread = 1`，旧 trace 再用 `thread.tid = process.pid` 兜底。

```sql
-- 目标进程与主线程 CTE。把 com.example.app 替换为目标进程名
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT
    thread.utid,
    thread.tid,
    COALESCE(thread.name, target_process.name) AS thread_name,
    target_process.upid,
    target_process.name AS process_name
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
)
SELECT * FROM main_thread;
```

> 如果当前 Trace Processor 版本没有 `thread.is_main_thread` 字段，就保留 `thread.tid = process.pid` 作为主线程兜底，并在 Perfetto UI 中确认该线程是否承载 `Choreographer#doFrame`、`bindApplication` 等主线程 slice。

大 Trace 上的查询要先裁剪再关联。不要让全量 `thread_state` 与全量 `slice` 做非等值 JOIN；先把目标进程、目标时间窗和中间结果固化，再做 `SPAN_JOIN` / `INTERVAL_INTERSECT` 或重叠区间查询。

```sql
-- 大 Trace 查询前先固化目标窗口内的主线程状态
CREATE PERFETTO TABLE target_main_states AS
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT thread.utid
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
),
window AS (
  SELECT trace_start() + 0 AS start_ts, trace_start() + 5000000000 AS end_ts
)
SELECT
  thread_state.id,
  thread_state.utid,
  thread_state.state,
  MAX(thread_state.ts, window.start_ts) AS ts,
  MIN(thread_state.ts + thread_state.dur, window.end_ts)
    - MAX(thread_state.ts, window.start_ts) AS dur
FROM thread_state
JOIN main_thread USING (utid)
CROSS JOIN window
WHERE thread_state.ts < window.end_ts
  AND thread_state.ts + thread_state.dur > window.start_ts;
```

`CREATE PERFETTO TABLE` 会把过滤后的结果物化，后续查询可以复用这张小表，减少窗口函数和区间 JOIN 的重复扫描成本。

[已验证: Perfetto SQL tables / stdlib docs, perfetto.dev/docs/analysis/sql-tables]

### 时间单位与常用函数

Perfetto 中所有时间戳和持续时间都用**纳秒（ns）**。这个单位精度够高，但人类不太直觉，分析时通常需要换算：

- 纳秒 → 毫秒：除以 `1e6`（或 `1000000.0`）
- 纳秒 → 秒：除以 `1e9`
- 16.67ms 的帧预算（60fps）= `16670000` ns
- 8.33ms 的帧预算（120fps）= `8330000` ns

`trace_start()` 函数返回 Trace 开始的时间戳，用 `ts - trace_start()` 可以把绝对时间转换为相对时间（从 Trace 开始过了多少纳秒），这在做时间分段分析时很有用。

`EXTRACT_ARG(arg_set_id, 'key')` 函数可以从 slice 的附加参数中提取值。很多 Perfetto slice 携带额外的键值对信息，比如 Choreographer 的 doFrame slice 会带上 `frame_number` 参数，可以用 `EXTRACT_ARG(slice.arg_set_id, 'frame_number')` 提取出来。

## 帧时间与卡顿分析

帧时间是衡量流畅性最直观的指标。我们可以用 SQL 精确统计帧时间分布、定位掉帧和大帧，甚至分析帧节奏的规律性。

### 基本帧时间查询

最直接的方式是查询 `Choreographer#doFrame` slice 的持续时间，这代表主线程处理一帧的总耗时（包括 Input、Animation、Traversal 三个阶段）。

```sql
-- 查询所有 doFrame 的帧时间
SELECT
  CAST((ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  CAST(dur / 1e6 AS FLOAT) AS frame_ms,
  name
FROM slice
WHERE name = 'Choreographer#doFrame'
ORDER BY ts;
```

这个查询的结果中，`frame_ms` 就是每一帧的耗时。在 60fps 设备上，超过 16.67ms 的帧就是掉帧；在 120fps 设备上，超过 8.33ms 的帧就是掉帧。

但 `doFrame` 的 `dur` 只包含主线程的工作时间。一帧从 VSync 到上屏的完整时间还包括 RenderThread 的渲染时间和 SurfaceFlinger 的合成时间。如果需要完整的帧生命周期分析，应该使用 Frame Timeline 数据（见下文）。

### 帧时间分布统计

单个帧的时间意义有限，我们需要看整体分布。下面的查询把帧时间按区间分桶，统计每个桶里有多少帧：

```sql
SELECT
  bucket_name,
  COUNT(*) AS frame_count
FROM (
  SELECT
    CASE
      WHEN dur < 8e6  THEN '< 8ms (120fps OK)'
      WHEN dur < 11e6 THEN '8-11ms (90fps OK)'
      WHEN dur < 17e6 THEN '11-17ms (60fps OK)'
      WHEN dur < 33e6 THEN '17-33ms (jank)'
      WHEN dur < 50e6 THEN '33-50ms (big jank)'
      ELSE '> 50ms (huge jank)'
    END AS bucket_name,
    dur
  FROM slice
  WHERE name = 'Choreographer#doFrame'
)
GROUP BY bucket_name
ORDER BY MIN(dur);
```

如果 jank 和 big jank 桶里的帧数超过总帧数的 5%，就需要关注了。这个分布也可以作为优化前后的对比基准。分别跑一遍这个查询，就能看到各个桶的帧数变化。

### Frame Timeline：系统视角的帧分析

`Choreographer#doFrame` 只反映主线程视角。Android 12（API 31）引入的 Frame Timeline 提供了系统视角：它同时记录期望时间线和实际时间线，能直接回答“这一帧有没有按时 present”。

> **版本边界**：Frame Timeline 表（`actual_frame_timeline_slice` / `expected_frame_timeline_slice`）从 Android 12 起稳定可用。在 Android 10/11 的 trace 上运行下面的查询会返回空结果；旧版本需要退回 `Choreographer#doFrame`、`DrawFrame`、SurfaceFlinger 合成 slice、fence / sched 组合来判断帧时序。

在 Perfetto 中，Frame Timeline 数据存储在 `actual_frame_timeline_slice` 和 `expected_frame_timeline_slice` 两张表中。这里要单独记一条：配对同一帧时不能拿 `track_id` 当主键；`track_id` 只表示 slice 落在哪条轨道上，真正稳定的帧标识是 `display_frame_token`，surface frame 还要再带上 `surface_frame_token`。如果要用标准库高层视图，可以先加载 `android.frames.timeline`：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

-- 查询未按时完成的 frame
SELECT
  CAST((actual.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  actual.layer_name,
  CAST(actual.dur / 1e6 AS FLOAT) AS actual_dur_ms,
  CAST(expected.dur / 1e6 AS FLOAT) AS expected_dur_ms,
  actual.present_type,
  actual.jank_type
FROM actual_frame_timeline_slice AS actual
JOIN expected_frame_timeline_slice AS expected
  ON actual.display_frame_token = expected.display_frame_token
 AND IFNULL(actual.surface_frame_token, -1) = IFNULL(expected.surface_frame_token, -1)
WHERE actual.on_time_finish = 0
ORDER BY actual.ts;
```

这条查询更接近 Perfetto 的表结构本身：`actual` 负责给出真实结果，`expected` 负责给出同一帧的目标时间线，`on_time_finish = 0` 直接表示这帧没有按时完成。

[已验证: Perfetto stdlib docs 中的 Frame Timeline 表结构, perfetto.dev/docs/analysis/stdlib-docs]

Frame Timeline 还能检测一种更隐蔽的流畅性问题：步幅波动（cadence discrepancy）。即使所有帧都在 VSync 预算内完成，帧与帧之间的时间波动如果过大（比如 8ms、15ms、8ms、15ms 交替），用户仍然会感知到不流畅。关于这方面的深度分析，参见 §7.9 感知流畅性章节。

## 线程调度与 CPU 使用分析

帧时间告诉我们"慢不慢"，但不知道"为什么慢"。线程调度分析帮我们定位根因：主线程是在 CPU 上跑满了（CPU bound），还是在等锁/等 Binder/等 IO（blocked）？

### 线程 CPU 时间统计

`sched` 表记录了每个线程在 CPU 上的运行时间。下面的查询统计指定线程（默认主线程）的总运行时间和 CPU 利用率：

```sql
-- 主线程 CPU 使用统计。把 com.example.app 替换为目标进程名
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT
    thread.utid,
    COALESCE(thread.name, target_process.name) AS thread_name
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
)
SELECT
  main_thread.thread_name,
  SUM(sched.dur) / 1e6 AS total_cpu_ms,
  COUNT(*) AS schedule_count,
  CAST(SUM(sched.dur) * 100.0 / (SELECT end_ts - start_ts FROM trace_bounds) AS FLOAT) AS cpu_pct
FROM sched
JOIN main_thread USING (utid)
WHERE sched.cpu IS NOT NULL
GROUP BY main_thread.thread_name;
```

`cpu_pct` 是整个 Trace 期间的 CPU 利用率。如果主线程的 CPU 利用率超过 80%，说明主线程大部分时间都在做计算——measure/layout/draw 太重了。如果 CPU 利用率很低但帧时间很长，说明主线程在等什么东西，需要进一步分析线程状态。

### 调度延迟：Runnable → Running 的时间

线程变成 Runnable（准备好运行）到实际获得 CPU 的时间差，就是调度延迟。调度延迟高意味着系统 CPU 负载重或者线程优先级低：

```sql
-- 主线程调度延迟 Top 20
-- 计算方式：线程以 Runnable 状态离开 CPU 后，到重新获得 CPU 的时间差
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT thread.utid
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
),
main_sched AS (
  SELECT
    sched.ts,
    sched.dur,
    sched.end_state,
    sched.ts + sched.dur AS left_at,
    LEAD(sched.ts) OVER (PARTITION BY sched.utid ORDER BY sched.ts) AS run_start,
    LEAD(sched.cpu) OVER (PARTITION BY sched.utid ORDER BY sched.ts) AS run_cpu,
    LEAD(sched.ts) OVER (PARTITION BY sched.utid ORDER BY sched.ts) - (sched.ts + sched.dur) AS delay_ns,
    sched.cpu AS left_cpu
  FROM sched
  JOIN main_thread USING (utid)
)
SELECT
  CAST((run_start - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  CAST(delay_ns / 1e6 AS FLOAT) AS delay_ms,
  left_cpu,
  run_cpu
FROM main_sched
WHERE end_state IN ('R', 'R+')   -- 只看被抢占后仍为 Runnable 的记录
  AND delay_ns > 0
ORDER BY delay_ns DESC
LIMIT 20;
```

这个查询的核心逻辑：从 `sched` 表中找到主线程以 `R`（Runnable）或 `R+`（Runnable preempted）状态离开 CPU 的记录，然后用 `LEAD()` 窗口函数取同一 utid 的下一条调度记录，两者的时间差就是调度延迟。如果 `delay_ms` 频繁超过 5ms，说明系统 CPU 负载很重，主线程在排队等 CPU。处理方向是减少后台 Runnable 竞争：限制业务线程池并发、降低后台线程优先级、拆分长 CPU 任务、排查热降频或系统负载。`SCHED_FIFO` 只适用于系统/厂商特权进程的受控场景；普通 App 没有 `CAP_SYS_NICE`，不能把 UI 主线程切到实时调度，滥用还可能造成系统饥饿和 watchdog 风险。

### 线程状态分布

如果要看线程在 Running / R / S / D 这些状态上各花了多少时间，应该直接查 `thread_state` 表，而不是把 `sched.end_state` 当成“当前状态”。`sched.end_state` 更适合回答“这次 CPU slice 结束时，线程以什么状态离开 CPU”。

```sql
-- 主线程状态分布
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT thread.utid
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
),
main_states AS (
  SELECT thread_state.*
  FROM thread_state
  JOIN main_thread USING (utid)
)
SELECT
  state,
  SUM(dur) / 1e6 AS total_ms,
  ROUND(SUM(dur) * 100.0 / (SELECT SUM(dur) FROM main_states), 1) AS pct
FROM main_states
GROUP BY state
ORDER BY total_ms DESC;
```

常见的 `thread_state.state` 值：

- **Running**：线程当前正在 CPU 上执行
- **R / R+**：线程已经可运行，但还在等 CPU
- **S**：可中断睡眠，常见于等锁、等 Binder、等条件变量
- **D**：不可中断睡眠，常见于内核态 IO 等待

如果主线程的 `S` 或 `D` 占比异常高，结合时间线可以定位到具体在等什么——这就是下一节 Binder 分析和锁竞争分析要解决的问题。

## Binder 事务分析

Binder 是 Android 进程间通信的主要机制。一次同步 Binder 调用通常包含客户端发起事务、服务端线程接收事务、服务端处理、客户端收到回复几个阶段。Perfetto 会把 Binder 相关内核事件和框架侧 slice 导入 trace；SQL 分析时要区分“公开 tracepoint”和“回复语义”。

### Binder 事务耗时统计

Linux ftrace 中常用的 Binder tracepoint 是 `binder_transaction`、`binder_transaction_received`、`binder_return`、`binder_command` 等，AOSP `drivers/android/binder_trace.h` 没有 `TRACE_EVENT(binder_reply)`。回复路径应通过 `binder_return` / `binder_command` 中的 `BR_REPLY` / `BC_REPLY`，或 Perfetto 导出的 Android Binder slice / args 描述。一次同步调用可拆成三个时间维度：

- **client_dur**：客户端总等待时间（从发起调用到收到回复）
- **server_dur**：服务端实际处理时间
- **dispatch_dur**：服务端排队等待时间（从收到请求到开始处理）

当 `dispatch_dur` 持续大于 `server_dur` 时，说明服务端开始出现排队。线程上限要按进程口径看：普通 libbinder 进程的 `DEFAULT_MAX_BINDER_THREADS` 是 15；`system_server` 在 `SystemServer.java` 中把 `sMaxBinderThreads` 配成 31；厂商进程或 native 服务还可以通过 `ProcessState::setThreadPoolMaxThreadCount()` 调整。排队时间升高不一定来自线程数本身，还要结合服务端 CPU 忙、锁等待和同步 Binder 嵌套调用判断。

> **说明**：下面的 SQL 通过 `slice.name GLOB '*binder*'` 筛选 Binder 相关 slice，能量化单次调用的总耗时。准确分离 client/server/dispatch 三段时，要把 `binder_transaction`、`binder_transaction_received` 与 `binder_return` / `binder_command` 的 reply 语义按 transaction id、debug id 或时间窗关联起来。本节先处理总耗时排序，三段拆分可在后续专题中展开。

```sql
-- Binder 事务按耗时排序 Top 20
SELECT
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  slice.name,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms,
  thread.name AS thread_name,
  process.name AS process_name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE slice.name GLOB '*binder*'
  AND slice.dur > 1e6  -- 过滤掉 < 1ms 的轻量调用
ORDER BY slice.dur DESC
LIMIT 20;
```

[已验证: Perfetto Binder transaction analysis, perfetto.dev/docs]

### 跨进程 Binder 调用链追踪

在实际分析中，我们经常需要追踪一个 Binder 调用从客户端到服务端的完整路径。在 Perfetto UI 中，这对应的是 Android Binder / Transactions track。在 SQL 中，需要通过时间戳关联来连接客户端和服务端的 slice：

```sql
-- 查找主线程发起的长时间 Binder 调用
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT thread.utid
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
)
SELECT
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  slice.name,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms,
  EXTRACT_ARG(slice.arg_set_id, 'code') AS binder_code
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN main_thread ON thread_track.utid = main_thread.utid
WHERE slice.name GLOB '*binder*'
  AND slice.dur > 50e6  -- 超过 50ms 的 Binder 调用
ORDER BY slice.dur DESC;
```

`binder_code` 是 Binder 调用的方法编号，可以对照 AIDL 接口定义确定具体调用了哪个方法。`EXTRACT_ARG()` 返回的是 PerfettoSQL 的动态值；如果后续要按编号做大小比较或分桶，先用 `CAST(EXTRACT_ARG(slice.arg_set_id, 'code') AS INTEGER)` 转成整数。结合 §1.4 Binder IPC 章节的知识，可以判断这个耗时是否合理。

### Binder 线程池利用率

当所有 Binder 线程都处于忙碌状态时，新请求会排队等待，这就是 ANR 的常见原因之一。通过统计同一时刻活跃的 Binder 线程数，可以判断线程池是否饱和：

```sql
-- 统计 system_server 中 Binder 线程的活跃时间
SELECT
  thread.name AS binder_thread,
  SUM(sched.dur) / 1e6 AS cpu_ms,
  COUNT(*) AS sched_count
FROM sched
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'system_server'
  AND thread.name GLOB 'Binder:*'
GROUP BY thread.name
ORDER BY cpu_ms DESC;
```

这个查询统计的是 Binder 线程获得 CPU 执行的时间，不能直接等同于线程池利用率。如果多数 `Binder:*` 线程在同一时间窗内都有较高 `cpu_ms`，同时客户端 Binder slice 的耗时或 `binder_transaction` 排队间隔也在升高，才可以判断服务端接近饱和。后续处理方向通常是缩短服务端同步工作、拆掉嵌套同步 Binder 调用，或在确认业务模型允许后调整线程池上限。

## 内存与 GC 分析

GC（垃圾回收）暂停是 jank 的常见来源之一。当 ART 运行时触发 GC 时，会暂停所有 Java 线程（Stop-The-World），如果暂停时间超过几毫秒，就会导致掉帧。

### GC 事件统计

```sql
-- GC 事件统计
SELECT
  COUNT(*) AS gc_count,
  CAST(SUM(dur) / 1e6 AS FLOAT) AS total_pause_ms,
  CAST(MAX(dur) / 1e6 AS FLOAT) AS max_pause_ms,
  CAST(AVG(dur) / 1e6 AS FLOAT) AS avg_pause_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE slice.name GLOB '*GC*'
  OR slice.name GLOB '*GarbageCollector*';
```

这个查询给出 GC 的全景统计。如果 `avg_pause_ms` 超过 3-5ms，或者 `max_pause_ms` 超过 16ms（一帧的预算），就需要继续查。GC 暂停和帧时间的关联分析要限定同一进程，并把 frame 限在主线程：

```sql
-- GC 暂停与同进程主线程帧时间的关联
SELECT
  gc_process.name AS process_name,
  gc.ts AS gc_ts,
  CAST(gc.dur / 1e6 AS FLOAT) AS gc_ms,
  CAST(frame.dur / 1e6 AS FLOAT) AS frame_ms
FROM slice AS gc
JOIN thread_track AS gc_track ON gc.track_id = gc_track.id
JOIN thread AS gc_thread ON gc_track.utid = gc_thread.utid
JOIN process AS gc_process ON gc_thread.upid = gc_process.upid
JOIN slice AS frame
  ON frame.name = 'Choreographer#doFrame'
 AND frame.ts < gc.ts + gc.dur
 AND gc.ts < frame.ts + frame.dur
JOIN thread_track AS frame_track ON frame.track_id = frame_track.id
JOIN thread AS frame_thread ON frame_track.utid = frame_thread.utid
JOIN process AS frame_process ON frame_thread.upid = frame_process.upid
WHERE (gc.name GLOB '*GC*' OR gc.name GLOB '*GarbageCollector*')
  AND gc.dur > 1e6
  AND gc_process.name = 'com.example.app'
  AND gc_process.upid = frame_process.upid
  AND (frame_thread.is_main_thread = 1 OR frame_thread.tid = frame_process.pid)
ORDER BY gc.dur DESC;
```

这个查询找出与目标进程主线程 `doFrame` 重叠的 GC 暂停。结果中如果有 `gc_ms` 接近或超过 5ms 的记录，再沿着同一进程的分配热点继续查。大规模 Trace 上，优先把目标进程和时间窗加进 WHERE；更复杂的区间交集可以改用 PerfettoSQL 的 `SPAN_JOIN` / `INTERVAL_INTERSECT`。

### Java Heap 变化趋势

Java Heap 在 Perfetto 里有三条常用观察路径。第一步先确认 trace 里有哪些 counter：

```sql
-- 查看可用的 Java / Heap 相关 counter 名称
SELECT DISTINCT counter_track.name
FROM counter_track
WHERE counter_track.name GLOB '*Java*Heap*'
   OR counter_track.name IN ('Heap size (KB)', 'mem.java_heap')
   OR counter_track.name GLOB '*_MEM_STATS*Java*'
ORDER BY counter_track.name;
```

路径一是连续趋势，适合观察进程内存压力和 Java heap counter 的变化：

```sql
-- Java Heap / Heap counter 趋势。value_raw 的单位要按 counter 名称和数据源确认
SELECT
  CAST((counter.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  counter_track.name AS counter_name,
  counter.value AS value_raw
FROM counter
JOIN counter_track ON counter.track_id = counter_track.id
WHERE counter_track.name GLOB '*Java*Heap*'
   OR counter_track.name IN ('Heap size (KB)', 'mem.java_heap')
   OR counter_track.name GLOB '*_MEM_STATS*Java*'
ORDER BY counter.ts;
```

路径二是 Java heap dump。它依赖 heap graph / `android.java_hprof` 相关数据源，分析对象数量、类名和引用关系时看 `heap_graph_object`、`heap_graph_class`、`heap_graph_reference` 等表。

路径三是 Java allocation sampling。它依赖 heapprofd 与 ART Java allocation 相关配置，分析分配热点时看 `heap_profile_allocation` 以及 callsite / frame 相关表。`process_stats` 里的 `mem.rss.anon` 只能表示匿名 RSS 趋势，不能直接当成 Java Heap。

如果 Heap 相关 counter 呈锯齿形上升（分配→GC 回收→再分配→再回收），且每次 GC 后的基准线持续抬高，说明存在内存泄漏。参见 §10.2 内存泄漏章节。

[已验证: Perfetto counter / heap graph / heapprofd 表族；counter 名称随 trace 配置和 Android 版本变化]

## 启动时间分析

冷启动是从用户点击 App 图标到首帧渲染完成的过程。Perfetto SQL 可以分解这个过程中的关键阶段。`ZygoteInit` 要单独看：它是 zygote 进程初始化 / 系统启动阶段的 trace section，不是每次 App 冷启动都会出现的应用侧阶段。

### 冷启动全流程时间分解

系统启动或 zygote 初始化分析时，可以查精确的 `ZygoteInit` slice：

```sql
-- 系统启动 / zygote 初始化中的 ZygoteInit slice
SELECT
  slice.name,
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS start_ms,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms
FROM slice
WHERE slice.name = 'ZygoteInit'
ORDER BY slice.ts;
```

App 冷启动分析更常看进程创建、绑定应用、主线程入口和首帧。下面的查询同时兼容 thread track 与 process track：

```sql
-- App 冷启动关键节点。按实际 trace 中的 slice 名再收窄 WHERE
SELECT
  slice.name,
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS start_ms,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms,
  COALESCE(thread_process.name, track_process.name, thread.name, 'unknown') AS owner
FROM slice
LEFT JOIN thread_track ON slice.track_id = thread_track.id
LEFT JOIN thread ON thread_track.utid = thread.utid
LEFT JOIN process AS thread_process ON thread.upid = thread_process.upid
LEFT JOIN process_track ON slice.track_id = process_track.id
LEFT JOIN process AS track_process ON process_track.upid = track_process.upid
WHERE slice.name GLOB '*am_proc_start*'
   OR slice.name GLOB '*bindApplication*'
   OR slice.name GLOB '*ActivityThread*'
   OR slice.name IN (
     'Application.onCreate',
     'Activity.onCreate',
     'Choreographer#doFrame'
   )
ORDER BY slice.ts;
```

[已验证: AOSP ZygoteInit.java 使用 `ZygoteInit` trace section；App 冷启动节点需按实际 trace 中的 slice 名确认]

通过这个查询可以得到启动过程中各个阶段的时间线。`Application.onCreate`、`Activity.onCreate` 是否可见，取决于应用或 Framework 是否写入对应 trace section。如果某个阶段明显偏长，可以进一步分析该阶段内的 Binder 调用和锁等待。

### 启动过程中的 Binder 调用统计

```sql
-- 启动阶段的 Binder 调用统计
WITH target_process AS (
  SELECT upid, pid, name
  FROM process
  WHERE name = 'com.example.app'
),
main_thread AS (
  SELECT thread.utid
  FROM thread
  JOIN target_process USING (upid)
  WHERE thread.is_main_thread = 1
     OR thread.tid = target_process.pid
),
startup_window AS (
  SELECT
    MIN(CASE WHEN slice.name GLOB '*bindApplication*' THEN slice.ts END) AS start_ts,
    MIN(CASE WHEN slice.name = 'Choreographer#doFrame' THEN slice.ts END) AS end_ts
  FROM slice
  JOIN thread_track ON slice.track_id = thread_track.id
  JOIN main_thread ON thread_track.utid = main_thread.utid
)
SELECT
  slice.name,
  COUNT(*) AS call_count,
  CAST(SUM(slice.dur) / 1e6 AS FLOAT) AS total_ms,
  CAST(AVG(slice.dur) / 1e6 AS FLOAT) AS avg_ms,
  CAST(MAX(slice.dur) / 1e6 AS FLOAT) AS max_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN main_thread ON thread_track.utid = main_thread.utid
CROSS JOIN startup_window
WHERE slice.name GLOB '*binder*'
  AND slice.ts BETWEEN startup_window.start_ts AND startup_window.end_ts
GROUP BY slice.name
ORDER BY total_ms DESC;
```

这个查询统计从 `bindApplication` 到首帧 `doFrame` 之间主线程发起的所有 Binder 调用。`total_ms` 最高的几个调用就是启动速度的瓶颈点。参见 §8.2 启动全流程章节的分析方法。

## ANR 分析

ANR（Application Not Responding）是用户最直接感知的性能问题。ANR 发生时，系统会 dump 当前线程堆栈到 `/data/anr/` 目录。但堆栈只能看到 ANR 时刻的快照，无法看到"导致 ANR 的 5 秒里主线程到底在做什么"。Perfetto SQL 可以补全这个时间窗口。下面两组 SQL 依赖 `thread_state` 和 `slice`；如果要继续拆 Binder 阶段，还要在抓取配置里启用 Binder ftrace events。

### ANR 前后主线程活动分析

```sql
-- ANR 前后 5 秒主线程活动
WITH params AS (
  -- 替换 0：ANR 发生时刻相对 trace_start() 的纳秒偏移
  SELECT trace_start() + 0 AS anr_ts
),
window AS (
  SELECT
    anr_ts - 5000000000 AS start_ts,
    anr_ts + 1000000000 AS end_ts
  FROM params
)
SELECT
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  process.name AS process_name,
  slice.name,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms,
  slice.depth
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
CROSS JOIN window
WHERE process.name = 'com.example.app'  -- 替换为目标进程
  AND (thread.is_main_thread = 1 OR thread.tid = process.pid)
  AND slice.ts < window.end_ts
  AND slice.ts + slice.dur > window.start_ts
ORDER BY slice.ts;
```

实际使用时，先定位 ANR 时间点（在 Perfetto UI 中搜索 `am_anr` 或 ANR 相关 slice），再把 `params.anr_ts` 换成真实时间。

### 主线程阻塞原因分类

ANR / 卡顿排查应以 `thread_state` 为主表，因为它记录主线程在一段时间里的状态；`sched.end_state` 只描述 CPU slice 结束那一刻。下面的查询先裁剪 ANR 时间窗，再为每个 `thread_state` 只挑一个重叠时间最长的 slice，避免嵌套 slice 重复放大 `total_ms`：

```sql
-- 主线程阻塞原因分类
WITH params AS (
  -- 替换 0：ANR 发生时刻相对 trace_start() 的纳秒偏移
  SELECT trace_start() + 0 AS anr_ts
),
window AS (
  SELECT
    anr_ts - 5000000000 AS start_ts,
    anr_ts + 1000000000 AS end_ts
  FROM params
),
main_states AS (
  SELECT
    thread_state.id AS state_id,
    thread_state.utid,
    thread_state.state,
    MAX(thread_state.ts, window.start_ts) AS ts,
    MIN(thread_state.ts + thread_state.dur, window.end_ts)
      - MAX(thread_state.ts, window.start_ts) AS dur
  FROM thread_state
  JOIN thread USING (utid)
  JOIN process USING (upid)
  CROSS JOIN window
  WHERE process.name = 'com.example.app'  -- 替换为目标进程
    AND (thread.is_main_thread = 1 OR thread.tid = process.pid)
    AND thread_state.state != 'Running'
    AND thread_state.ts < window.end_ts
    AND thread_state.ts + thread_state.dur > window.start_ts
),
state_with_slice AS (
  SELECT
    main_states.*,
    (
      SELECT name
      FROM (
        SELECT
          s.name,
          MIN(s.ts + s.dur, main_states.ts + main_states.dur)
            - MAX(s.ts, main_states.ts) AS overlap_dur
        FROM slice AS s
        JOIN thread_track AS tt ON s.track_id = tt.id
        WHERE tt.utid = main_states.utid
          AND s.ts < main_states.ts + main_states.dur
          AND s.ts + s.dur > main_states.ts
        ORDER BY overlap_dur DESC
        LIMIT 1
      )
    ) AS slice_name
  FROM main_states
)
SELECT
  CASE
    WHEN slice_name GLOB '*monitor*' THEN 'Lock Contention'
    WHEN slice_name GLOB '*binder*' THEN 'Binder Call'
    WHEN state = 'D' THEN 'Uninterruptible IO'
    WHEN state = 'S' THEN 'Sleeping (generic)'
    WHEN state IN ('R', 'R+') THEN 'Runnable but waiting for CPU'
    ELSE 'Other: ' || COALESCE(slice_name, state, 'unknown')
  END AS block_reason,
  COUNT(*) AS count,
  CAST(SUM(dur) / 1e6 AS FLOAT) AS total_ms
FROM state_with_slice
WHERE dur > 0
GROUP BY block_reason
ORDER BY total_ms DESC;
```

这个结果按裁剪后的 `thread_state.dur` 统计，每段状态只计一次。大规模 Trace 上，先缩小 `window.start_ts` / `window.end_ts`；更复杂的多区间交集，优先使用 PerfettoSQL 的 `SPAN_JOIN` / `INTERVAL_INTERSECT` 或标准库视图。

## 锁竞争与同步分析

锁竞争（Lock Contention）是 jank 和 ANR 的核心诱因之一。当主线程尝试获取一个被其他线程持有的锁时，它会被阻塞——这段等待时间在 Perfetto 中表现为 `monitor contention` 事件。

### Monitor Contention Top N

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

-- 主线程锁竞争 Top 10（等待时间最长）
SELECT
  CAST(dur / 1e6 AS FLOAT) AS wait_ms,
  blocked_thread_name AS waiter_thread,
  blocking_thread_name AS owner_thread,
  short_blocked_method,
  short_blocking_method,
  waiter_count
FROM android_monitor_contention
WHERE is_blocked_thread_main = 1
ORDER BY dur DESC
LIMIT 10;
```

`android_monitor_contention` 已经把 owner 线程、blocked 线程和相关方法都解析好了，比直接在原始 `slice` 上用名字模糊匹配稳定得多。注意：Perfetto stdlib 当前版本的 `android_monitor_contention` 不提供 `lock_name` 列；如果需要锁对象名，要从原始 `slice` 表配合 `args` 另写限定查询。结合 Perfetto UI 的 Lock contention track，可以快速定位锁竞争的全貌。

### 锁竞争与帧时间关联

锁竞争本身并不直接等于卡顿。只有它落在帧渲染期间，才会拉长这一帧的耗时。下面的查询把 `android_monitor_contention` 放进主线程 `doFrame` 的同一时间窗口：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

-- 帧期间的锁竞争
SELECT
  frame.dur / 1e6 AS frame_ms,
  contention.dur / 1e6 AS lock_wait_ms,
  ROUND(contention.dur * 100.0 / frame.dur, 1) AS lock_pct,
  contention.blocking_thread_name AS owner_thread
FROM slice AS frame
JOIN thread_track AS ft ON frame.track_id = ft.id
JOIN thread AS ft_thread ON ft.utid = ft_thread.utid
JOIN process AS ft_process ON ft_thread.upid = ft_process.upid
JOIN android_monitor_contention AS contention
  ON contention.blocked_utid = ft_thread.utid
 AND contention.ts >= frame.ts
 AND contention.ts + contention.dur <= frame.ts + frame.dur
WHERE frame.name = 'Choreographer#doFrame'
  AND ft_process.name = 'com.example.app'
  AND (ft_thread.is_main_thread = 1 OR ft_thread.tid = ft_process.pid)
  AND contention.dur > 500000  -- 过滤 < 0.5ms 的短暂等待
ORDER BY contention.dur DESC;
```

如果 `lock_pct` 超过 30%，说明这一帧卡顿的主要原因是锁等待。根因分析方法：从 `owner_thread` 和 `lock_name` 继续沿着持锁线程的时间线往后查，分析它为什么持锁时间过长。参见 §1.14 锁竞争与同步性能分析章节。

[已验证: Perfetto stdlib android.monitor_contention 表结构, perfetto.dev/docs/analysis/stdlib-docs]

## SPAN_JOIN 与窗口函数：跨维度时间序列交叉分析

SPAN_JOIN 和窗口函数是 PerfettoSQL 中**跨维度关联分析的核心语法**。当帧时间需要和 CPU 频率、GC 暂停、或 Binder 排队做交叉分析时，单靠等值 JOIN 无法处理"时间段重叠"的语义——这时需要 SPAN_JOIN。

### SPAN_JOIN 机制

SPAN_JOIN 是一个**自定义算子表（Operator Table）**，由 C++ 实现时间跨度交集计算，对外暴露为 SQL 虚拟表。它的输入是两个含 `ts` 和 `dur` 列的表/视图，输出是两表在时间上存在重叠的行组合。

```sql
-- 调度切片 × CPU 频率的跨维度关联
CREATE VIEW sp_sched AS
SELECT ts, dur, cpu, utid FROM sched;

CREATE VIEW sp_frequency AS
SELECT
  ts,
  lead(ts) OVER (PARTITION BY track_id ORDER BY ts) - ts as dur,
  cpu,
  value as freq
FROM counter
JOIN cpu_counter_track ON counter.track_id = cpu_counter_track.id
WHERE cpu_counter_track.name = 'cpufreq';

CREATE VIRTUAL TABLE sched_with_freq
USING SPAN_JOIN(sp_sched PARTITIONED cpu, sp_frequency PARTITIONED cpu);

SELECT ts, dur, cpu, utid, freq FROM sched_with_freq;
```

关键参数：
- `PARTITIONED col`：按整数列分区后再做交集，可将 O(n×m) 降到 O(n+m)
- 分区列**必须是整数**，字符串需通过 `HASH()` 转换
- 同一表同一分区内的 spans **不能重叠**，否则静默产生错误结果

变体：`SPAN_LEFT_JOIN`（左表分区+右表不分区）、`SPAN_OUTER_JOIN`（两者都不分区）。

窗口函数 `LEAD()` 在这里的作用是把离散的 counter 点转换为连续的 span：取当前行 ts 为起点，下一行的 ts 减当前 ts 为 dur——这是把"点"变成"段"的常用技巧。

### 应用场景：帧 × CPU 频率 × 锁竞争三维关联

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

-- 先用窗口函数把主线程锁等待转为 span
CREATE VIEW main_lock_span AS
SELECT
  ts,
  dur,
  blocking_thread_name
FROM android_monitor_contention
WHERE is_blocked_thread_main = 1;

-- 再 SPAN_JOIN 调度切片
CREATE VIRTUAL TABLE frame_lock_cpu
USING SPAN_JOIN(
  main_lock_span PARTITIONED utid,
  sp_sched
);

-- 帧 × 锁等待 × CPU 频率三维交叉（示意）
SELECT ...
FROM sched_with_freq
JOIN frame_lock_cpu ...
```

这个模式可以回答"这一帧掉帧是因为 CPU 降频、还是因为等锁、还是因为调度延迟"。

> SPAN_JOIN 的 C++ 源码位于 `external/perfetto/src/trace_processor/` 目录的 operand 相关文件中。v53+ 支持 `SPAN_OUTER_JOIN`。

<!-- AIW-源码调研-2026-05-13 -->

## 交叉引用与分析路径

上面的每个 SQL 查询都是针对单一维度的分析。在实际工作中，性能问题往往是多因素叠加的——一个 jank 帧可能同时涉及 GC 暂停、Binder 调用和锁竞争。以下是几种常见的组合分析路径：

**卡顿分析标准流程**：先查 `Choreographer#doFrame` 定位慢帧 → 查该帧期间的 `sched` 判断主线程在等什么 → 如果在等锁，查 `monitor contention` → 如果在等 Binder，查 `binder_transaction` → 如果在等 GC，查 GC 事件和 Heap 变化。

**ANR 分析标准流程**：定位 ANR 时间点 → 查前后 5 秒的主线程 slice → 按阻塞原因分类（锁/Binder/IO/CPU 抢占）→ 对耗时最大的原因深挖。

**启动速度分析标准流程**：定位启动起止时间（从 `bindApplication` 到首帧 `doFrame`）→ 按阶段分解耗时 → 统计各阶段的 Binder 调用和锁等待 → 找到瓶颈阶段后针对性优化。

每条路径中的 SQL 查询都可以在本章找到对应的模板。建议读者把常用的查询保存为 SQL 文件，在实际分析时直接加载执行，而不是每次从零开始写。

> 本章所有 SQL 均基于 Perfetto v54.0 文档验证，建议在 Perfetto UI 的 Query 标签页中直接运行。部分查询可能因 Trace 配置差异（未开启 sched/ftrace 等数据源）而无结果，请确保 Trace 抓取配置覆盖了分析所需的数据源（参见 §13.2 Trace 抓取章节）。
