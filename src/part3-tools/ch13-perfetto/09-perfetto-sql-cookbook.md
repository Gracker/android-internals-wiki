---
title: 13.9 Perfetto SQL 性能分析实战手册
chapter: '13.9'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- tools
- perfetto
- sql
- cookbook
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_verified: 2026-08-13
last_verified_against: "AOSP android-17.0.0_r1, android17-6.18-2026-06_r6, Perfetto Trace Processor v57.2 standard library and official docs (2026-08-13)"
confidence: high
sources:
- type: official
  path: https://perfetto.dev/docs/analysis/perfetto-sql-getting-started
- type: official
  path: https://perfetto.dev/docs/analysis/perfetto-sql-syntax
- type: official
  path: https://perfetto.dev/docs/analysis/sql-tables
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-freq
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/per_frame_metrics.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/garbage_collection.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startups.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/time_to_display.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/anrs.sql
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/monitor_contention.sql
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h
last_idle_audit_at: 2026-07-31T18:35:16+08:00
last_idle_audit_run_id: 20260731-183516-idle-audit-68cd3ad3
---

# 13.9 Perfetto SQL 性能分析实战手册

Perfetto UI 适合寻找可疑时间段，SQL 适合回答能复查的定量问题：某一帧错过了多少时间预算，主线程在分析窗口内运行了多久，Binder（Android 的进程间通信机制）客户端时间由哪些调度状态组成，一次 GC（垃圾回收）从开始到结束的实际耗时中有多少时间在等待 CPU。下文把这种实际经过的时间称为“墙上时间”，其中既有线程运行时间，也有等待时间。查询结果只说明 Trace 中已经采集到的事件。缺少 FrameTimeline（系统记录的帧期望与实际时间线）、调度、Binder 或 ART（Android Runtime）事件时，空表不能证明系统没有发生对应行为。

平台源码基线为 Android 17 / API 37 / `android-17.0.0_r1`，内核基线为 `android17-6.18-2026-06_r6`。示例优先查询 Android 17 Perfetto SQL 标准库，再在需要理解原始数据时使用 `slice`（时间轴区间事件）、`sched`、`thread_state` 和 `counter` 等基础表。查询已按 Android 17 源码中的表结构复核，主机侧验证版本固定为 Trace Processor v57.2；换用其他版本时仍要重新检查模块、列和查询结果。

## 查询前先固定分析口径

PerfettoSQL 是基于 SQLite 扩展的 SQL 方言，增加了 `INCLUDE PERFETTO MODULE`、`CREATE PERFETTO TABLE`、`SPAN_JOIN` 等追踪分析能力；其中 `SPAN_JOIN` 用于计算两组时间区间的交集。标准库模块会创建已经整理好的表、视图和函数。以 Binder 为例，`android.binder` 已经通过 flow（连接相关区间的事件关系）配对客户端事务与服务端回复，也会区分同步调用和 `oneway` 单向异步调用。直接用 `slice.name GLOB '*binder*'` 做通配匹配，无法获得同等语义。

标准库属于 Trace Processor，而非设备系统镜像中的固定数据库。设备运行 Android 17，不代表任意年代的 Trace Processor 都有相同模块和列。团队查询应固定 Trace Processor 版本；升级二进制时，要重新执行语法测试与基准 Trace 回归。

### 四类标识不要混用

常用表之间有四类标识：

- `pid`（进程 ID）、`tid`（线程 ID）是操作系统可见编号，进程或线程退出后可能复用。
- `upid`、`utid` 是 Trace Processor 在一份 Trace 内为进程和线程分配的唯一标识，关联表时优先使用它们。
- `track_id` 表示事件所在轨道。它不能替代帧号、Binder 事务号或 `slice.id`。
- `slice.id`、`frame_id`、`binder_txn_id` 属于对应事件模型，只在该模型规定的关系中关联。

查询目标进程、主线程和 Trace 边界，可以检查对象是否唯一，也能避免把同名的历史进程实例合并。

```sql
WITH settings(process_name) AS (
  VALUES ('com.example.app')
)
SELECT
  process.upid,
  process.pid,
  process.name AS process_name,
  thread.utid,
  thread.tid,
  thread.name AS thread_name,
  thread.is_main_thread,
  trace_start() AS trace_start_ns,
  trace_end() AS trace_end_ns
FROM settings
JOIN process
  ON process.name = settings.process_name
JOIN thread
  USING (upid)
WHERE thread.is_main_thread = 1
   OR thread.tid = process.pid
ORDER BY process.start_ts, thread.start_ts;
```

结果可能有多行：同一个包名在采集期间重启时，会出现多个 `upid`。查询中的 `OR` 只是用 `tid = pid` 兼容 `is_main_thread` 信息缺失的 Trace，同一线程同时满足两个条件也只会返回一行。正式查询应选定与问题时段相交的 `upid`，并确认主线程候选唯一；不能只按进程名对整份 Trace 聚合。

### 时间、开放区间与窗口裁剪

`ts` 和 `dur` 的单位都是纳秒。毫秒换算使用 `dur / 1e6`，秒换算使用 `dur / 1e9`。`trace_start()` 与 `trace_end()` 返回 Trace 的时间边界。部分正在进行的 `slice` 或调度状态会以 `dur = -1` 表示未闭合，计算结束时间前要把它裁到 `trace_end()`。

时间窗口采用半开区间 `[start_ts, end_ts)`，也就是包含起点、不包含终点，这样更容易处理首尾相接的事件。两个区间相交的条件是 `a.ts < b.end_ts AND a.end_ts > b.ts`，交集长度为 `MIN(a.end_ts, b.end_ts) - MAX(a.ts, b.ts)`。先按 `upid`、`utid` 与窗口过滤，再做区间关联，可以大幅减少大 Trace 的计算量。

下面的模板把主线程状态裁到由分析者给定的窗口。两个数值是查询参数，不代表平台超时或性能标准。

```sql
WITH
  settings(process_name, start_ts, end_ts) AS (
    VALUES (
      'com.example.app',
      10000000000,
      15000000000
    )
  ),
  target_main_thread AS (
    SELECT thread.utid
    FROM settings
    JOIN process
      ON process.name = settings.process_name
    JOIN thread
      USING (upid)
    WHERE thread.is_main_thread = 1
       OR thread.tid = process.pid
  ),
  states AS (
    SELECT
      thread_state.*,
      CASE
        WHEN thread_state.dur = -1 THEN trace_end()
        ELSE thread_state.ts + thread_state.dur
      END AS state_end_ts
    FROM thread_state
    JOIN target_main_thread USING (utid)
  )
SELECT
  states.id,
  states.utid,
  states.state,
  states.io_wait,
  states.blocked_function,
  MAX(states.ts, settings.start_ts) AS ts,
  MIN(states.state_end_ts, settings.end_ts)
    - MAX(states.ts, settings.start_ts) AS dur
FROM states
CROSS JOIN settings
WHERE states.ts < settings.end_ts
  AND states.state_end_ts > settings.start_ts
ORDER BY ts;
```

输出中的每一行都已经裁到目标窗口。需要反复使用结果时，可以用 `CREATE PERFETTO TABLE` 先计算并保存，也就是把查询结果物化；这适合几十秒以上且包含全量调度事件的 Trace。一次性检查则保留 CTE（Common Table Expression，由 `WITH` 定义的临时结果集）即可。

### 指标必须带上分母和边界

“主线程 CPU 占用 80%”缺少窗口就无法复查。“Binder 超过 1 ms 就慢”也忽略了接口语义、设备负载与调用是否同步。SQL 可以稳定地产生 P50、P90、P99：P50 是中位数，P90 和 P99 分别表示 90% 与 99% 的样本不超过该值。分位数依旧需要同场景、同设备配置、同采集配置的对照组。

帧分析还要区分三个量：

- `Choreographer#doFrame` 的 `dur` 是 UI 线程回调区间，可用于定位 UI 线程工作。
- FrameTimeline 的期望/实际区间用于判断帧是否按期呈现。
- 刷新周期会随显示模式和可变刷新率变化，固定的 16.67 ms 或 8.33 ms 不能代替每帧截止时间。

## 帧时间与卡顿分析

### `Choreographer#doFrame` 用于寻找 UI 线程耗时工作

Android 版本和追踪点实现会让 `doFrame` 名称带上帧号等后缀，因此查询使用 `GLOB 'Choreographer#doFrame*'`；`GLOB` 会按通配模式匹配名称。这张表适合做 UI 线程耗时排序与分布统计，不能单独给出系统级卡顿结论。

计算目标进程 `doFrame` 的墙上时间分位数，可以判断 UI 线程回调是否相对基线变慢，并找出少量最慢、需要回到时间线检查的样本。

```sql
INCLUDE PERFETTO MODULE slices.with_context;

WITH do_frames AS (
  SELECT
    id,
    ts,
    dur,
    name
  FROM thread_slice
  WHERE process_name = 'com.example.app'
    AND is_main_thread = 1
    AND name GLOB 'Choreographer#doFrame*'
    AND dur >= 0
)
SELECT
  COUNT(*) AS frame_count,
  ROUND(AVG(dur) / 1e6, 3) AS avg_do_frame_ms,
  ROUND(PERCENTILE(dur / 1e6, 50), 3) AS p50_do_frame_ms,
  ROUND(PERCENTILE(dur / 1e6, 90), 3) AS p90_do_frame_ms,
  ROUND(PERCENTILE(dur / 1e6, 99), 3) AS p99_do_frame_ms,
  ROUND(MAX(dur) / 1e6, 3) AS max_do_frame_ms
FROM do_frames;
```

这些分位数描述主线程回调的墙上时间，其中可能同时包含 `Running`、`Runnable`、睡眠和锁等待。若 P99 变长，应继续用 `thread_state` 分解长帧，不能直接归因为业务代码计算量增加。

### FrameTimeline 给出系统判帧依据

FrameTimeline 从 Android 12 / API 31 开始提供每帧的期望与实际时间线。`actual_frame_timeline_slice` 包含 `jank_type`、`jank_severity_type`、`on_time_finish` 和 `present_type` 等平台判定；`android.frames.timeline` 会把 UI 线程的 `Choreographer#doFrame`、RenderThread 的 `DrawFrame` 与时间线事件整理为 `android_frames`。

Android 17 的 `android_frames` 仍有明确边界：同一帧可能关联多个 `layer`（由系统合成的显示图层），表会聚合它们；当前实现只选第一个 `DrawFrame`，源码保留了对应待改进项；缺失或重复时间线事件时，`actual_frame_timeline_count` 与 `draw_frame_count` 会暴露异常。自动化统计应保留这些完整性列，避免把关联异常算成正常帧。

逐帧列出平台判定和截止时间超额量，并以 `actual_frame_timeline_id` 精确关联 `actual_frame_timeline_slice`。按 `track_id` 或模糊名称配对容易产生重复。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;

SELECT
  frames.upid,
  frames.frame_id,
  frames.ts,
  ROUND(frames.dur / 1e6, 3) AS frame_wall_ms,
  ROUND(overrun.overrun / 1e6, 3) AS deadline_overrun_ms,
  actual.jank_type,
  actual.jank_severity_type,
  actual.on_time_finish,
  actual.present_type,
  frames.actual_frame_timeline_count,
  frames.expected_frame_timeline_count,
  frames.draw_frame_count,
  frames.ui_thread_utid,
  frames.render_thread_utid
FROM android_frames AS frames
LEFT JOIN actual_frame_timeline_slice AS actual
  ON actual.id = frames.actual_frame_timeline_id
LEFT JOIN android_frames_overrun AS overrun
  USING (frame_id)
WHERE frames.process_name = 'com.example.app'
ORDER BY frames.ts;
```

`deadline_overrun_ms > 0` 表示实际结束时间晚于期望结束时间。负值表示仍有余量。`jank_type` 由平台记录，可继续区分应用、SurfaceFlinger（Android 的显示合成服务）、调度等类别。表为空时应检查采集配置、Android 版本与目标进程是否产生了 FrameTimeline 数据。

按平台标签聚合帧数与超额分布，适合比较同一测试方案的多次运行。查询不设置跨设备通用的“卡顿率及格线”。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;

WITH frame_results AS (
  SELECT
    frames.upid,
    frames.frame_id,
    actual.jank_type,
    actual.jank_severity_type,
    overrun.overrun
  FROM android_frames AS frames
  LEFT JOIN actual_frame_timeline_slice AS actual
    ON actual.id = frames.actual_frame_timeline_id
  LEFT JOIN android_frames_overrun AS overrun
    USING (frame_id)
  WHERE frames.process_name = 'com.example.app'
)
SELECT
  upid,
  COALESCE(jank_type, 'Missing FrameTimeline verdict') AS jank_type,
  COALESCE(jank_severity_type, 'Unknown severity') AS severity,
  COUNT(*) AS frame_count,
  ROUND(PERCENTILE(overrun / 1e6, 50), 3) AS p50_overrun_ms,
  ROUND(PERCENTILE(overrun / 1e6, 90), 3) AS p90_overrun_ms,
  ROUND(MAX(overrun) / 1e6, 3) AS max_overrun_ms
FROM frame_results
GROUP BY upid, jank_type, severity
ORDER BY frame_count DESC;
```

缺少平台判定的行应单独保留。把它们合入“无卡顿”会掩盖采集不完整或关联失败；比较版本时也应同步记录缺失比例。

## 线程调度与 CPU 使用

### `sched` 回答线程何时占用 CPU

`sched` 的一行表示某个线程在一个 CPU 上连续运行的区间。`dur` 累加后得到 CPU 运行时间；除以明确的墙上时间窗口，才得到该线程在此窗口内的 CPU 占用比例。单线程占用比例通常位于 0% 到 100% 之间，多线程进程的各线程比例相加可以超过 100%。

按线程统计目标进程在指定窗口中的 CPU 运行时间，可以把“CPU 很忙”转换成带窗口的线程排名。

```sql
WITH
  settings(process_name, start_ts, end_ts) AS (
    VALUES (
      'com.example.app',
      10000000000,
      15000000000
    )
  ),
  target_threads AS (
    SELECT
      thread.utid,
      thread.tid,
      thread.name AS thread_name
    FROM settings
    JOIN process
      ON process.name = settings.process_name
    JOIN thread
      USING (upid)
  ),
  clipped_sched AS (
    SELECT
      target_threads.utid,
      target_threads.tid,
      target_threads.thread_name,
      MAX(sched.ts, settings.start_ts) AS ts,
      MIN(
        CASE
          WHEN sched.dur = -1 THEN trace_end()
          ELSE sched.ts + sched.dur
        END,
        settings.end_ts
      ) - MAX(sched.ts, settings.start_ts) AS dur
    FROM sched
    JOIN target_threads USING (utid)
    CROSS JOIN settings
    WHERE sched.ts < settings.end_ts
      AND CASE
            WHEN sched.dur = -1 THEN trace_end()
            ELSE sched.ts + sched.dur
          END > settings.start_ts
  )
SELECT
  tid,
  thread_name,
  ROUND(SUM(dur) / 1e6, 3) AS cpu_time_ms,
  ROUND(
    100.0 * SUM(dur) / (settings.end_ts - settings.start_ts),
    2
  ) AS one_core_occupancy_pct
FROM clipped_sched
CROSS JOIN settings
GROUP BY utid, tid, thread_name
ORDER BY SUM(dur) DESC;
```

`one_core_occupancy_pct` 以单个 CPU 核心在查询中的 5 秒可用时间为分母。高占用只说明线程经常运行；函数热点仍需结合采样栈、调用栈或 `slice`。低占用伴随长延迟时，应检查 `Runnable` 排队、睡眠、I/O 与同步等待。

### `thread_state` 直接给出 `Runnable` 等待

`sched.end_state` 只描述线程离开 CPU 时的状态，不能代表离开 CPU 后整段时间。`thread_state` 已把 `sched_switch`、wakeup 与阻塞原因整理成连续区间：

- `Running`：线程正在 CPU 上运行。
- `R` / `R+`：线程可运行，但尚未获得 CPU；`R+` 表示线程被抢占后仍保持可运行。
- `S`：可中断睡眠，常见于等待事件、条件变量或 Binder 回复。
- `D`：不可中断睡眠；`io_wait = 1` 时可进一步判断为内核 I/O 等待。
- `blocked_function`：采集并完成内核符号化时，记录阻塞所在的内核函数。
- `waker_utid`：记录唤醒方，但并非每行都可用。

汇总目标主线程在窗口内的调度状态，可以区分 CPU 计算、等待 CPU、等待 I/O 与其他阻塞时间。

```sql
WITH
  settings(process_name, start_ts, end_ts) AS (
    VALUES (
      'com.example.app',
      10000000000,
      15000000000
    )
  ),
  main_thread AS (
    SELECT thread.utid
    FROM settings
    JOIN process
      ON process.name = settings.process_name
    JOIN thread
      USING (upid)
    WHERE thread.is_main_thread = 1
       OR thread.tid = process.pid
  ),
  clipped AS (
    SELECT
      thread_state.state,
      thread_state.io_wait,
      thread_state.blocked_function,
      MIN(
        CASE
          WHEN thread_state.dur = -1 THEN trace_end()
          ELSE thread_state.ts + thread_state.dur
        END,
        settings.end_ts
      ) - MAX(thread_state.ts, settings.start_ts) AS dur
    FROM thread_state
    JOIN main_thread USING (utid)
    CROSS JOIN settings
    WHERE thread_state.ts < settings.end_ts
      AND CASE
            WHEN thread_state.dur = -1 THEN trace_end()
            ELSE thread_state.ts + thread_state.dur
          END > settings.start_ts
  )
SELECT
  state,
  io_wait,
  COALESCE(blocked_function, '<no blocked function>') AS blocked_function,
  COUNT(*) AS interval_count,
  ROUND(SUM(dur) / 1e6, 3) AS total_ms,
  ROUND(MAX(dur) / 1e6, 3) AS longest_ms
FROM clipped
GROUP BY state, io_wait, blocked_function
ORDER BY SUM(dur) DESC;
```

较长的 `R` / `R+` 区间说明线程已经具备运行条件，却在运行队列中等待。它可能来自 CPU 争用、优先级、CPU 亲和性、`cgroup`（控制组的 CPU 配额或调度限制）或频率策略，不能只凭时长归因。较长的 `S` 也要与 Binder、`futex`（用户空间同步原语发生争用时使用的内核等待机制）、monitor（Java `synchronized` 使用的对象锁）竞争和应用 `slice` 对时。

列出最长的 `Runnable` 区间及唤醒方，可以从汇总值回到具体时刻，并定位谁把主线程唤醒。

```sql
WITH target_main_thread AS (
  SELECT thread.utid
  FROM process
  JOIN thread USING (upid)
  WHERE process.name = 'com.example.app'
    AND (thread.is_main_thread = 1 OR thread.tid = process.pid)
)
SELECT
  state.ts,
  ROUND(state.dur / 1e6, 3) AS runnable_ms,
  state.state,
  state.cpu,
  waker.tid AS waker_tid,
  waker.name AS waker_thread,
  waker_process.name AS waker_process,
  state.irq_context
FROM thread_state AS state
JOIN target_main_thread
  ON target_main_thread.utid = state.utid
LEFT JOIN thread AS waker
  ON waker.utid = state.waker_utid
LEFT JOIN process AS waker_process
  ON waker_process.upid = waker.upid
WHERE state.state IN ('R', 'R+')
  AND state.dur >= 0
ORDER BY state.dur DESC
LIMIT 30;
```

`waker_utid` 为空不等于没有唤醒；旧 Trace、缺少 wakeup 事件、数据丢失和内核路径差异都会让字段缺失。内核锚点中的 `sched_switch` 与 `sched_waking` 提供原始事件，Trace Processor 再把它们整理成这里的状态区间。

## Binder 事务分析

### 用 `android_binder_txns` 配对客户端与服务端

Android 17 的 `android.binder` 模块同时整理同步事务和 `oneway` 异步事务。同步事务中，`client_dur` 覆盖客户端发起调用到收到回复的墙上时间，`server_dur` 覆盖服务端处理与回复区间。异步事务没有同步等待关系，客户端发送与服务端接收可能相隔较远；统计时必须按 `is_sync` 分组。

`interface`、`method_name` 与 `aidl_name` 依赖 AIDL（Android Interface Definition Language）或 HIDL（HAL Interface Definition Language，用于硬件抽象层接口）追踪 `slice`。字段为空时，事务配对仍可能有效，只是 Trace 缺乏接口名。`client_monotonic_dur` 和 `server_monotonic_dur` 使用剔除全机休眠时间的单调时钟口径；分析用户感知延迟时仍要保留墙上时间对照。

按接口、方法和同步类型统计目标进程发起的 Binder 事务，可以找出高频接口和少量最慢的调用，同时保留样本量。

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_upid,
  is_sync,
  COALESCE(interface, '<unresolved interface>') AS interface,
  COALESCE(method_name, '<unresolved method>') AS method_name,
  server_process,
  COUNT(*) AS call_count,
  ROUND(PERCENTILE(client_dur / 1e6, 50), 3) AS p50_client_ms,
  ROUND(PERCENTILE(client_dur / 1e6, 90), 3) AS p90_client_ms,
  ROUND(PERCENTILE(client_dur / 1e6, 99), 3) AS p99_client_ms,
  ROUND(MAX(client_dur) / 1e6, 3) AS max_client_ms
FROM android_binder_txns
WHERE client_process = 'com.example.app'
  AND client_dur >= 0
GROUP BY client_upid, is_sync, interface, method_name, server_process
ORDER BY p99_client_ms DESC, call_count DESC;
```

同步与异步结果的 `client_dur` 含义不同，不能把两组数合成一个延迟分布。接口名缺失的事务也要保留；若直接过滤空值，最难解释的调用会从报表消失。

### 把 Binder 墙上时间分解为调度状态

客户端调用耗时长，可能是服务端执行慢，也可能是客户端等待回复期间被调度、设备休眠或数据不完整。`android_sync_binder_thread_state_by_txn` 已经对客户端和服务端区间分别执行 `SPAN_JOIN`，给出各调度状态的累计时间。

列出目标进程同步事务两端的状态分解，可以判断长事务主要消耗在 `Running`、`Runnable` 还是睡眠状态。

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  binder.binder_txn_id,
  COALESCE(binder.interface, '<unresolved interface>') AS interface,
  COALESCE(binder.method_name, '<unresolved method>') AS method_name,
  binder.client_thread,
  binder.server_process,
  binder.server_thread,
  states.thread_state_type,
  states.thread_state,
  states.thread_state_count,
  ROUND(states.thread_state_dur / 1e6, 3) AS state_ms
FROM android_binder_txns AS binder
JOIN android_sync_binder_thread_state_by_txn AS states
  USING (binder_txn_id)
WHERE binder.client_process = 'com.example.app'
  AND binder.is_sync = 1
ORDER BY binder.client_dur DESC, binder.binder_txn_id, state_ms DESC;
```

`thread_state_type = 'binder_txn'` 表示客户端区间，`binder_reply` 表示服务端回复区间。客户端处于 `S` 往往符合等待同步回复的预期；服务端出现较长 `R` / `R+`，才为“服务端线程排队等 CPU”提供直接证据。仍需回到该事务的 `slice` 子树，也就是事务区间内嵌套的子区间，确认具体工作。

所谓“Binder 线程池利用率”也要给出容量与窗口。只累加 Binder 线程 CPU 时间，得到的是运行时间，无法表示多少线程正在占用或还有多少空闲线程。线程池可能睡眠等待工作，也可能在处理非 Binder `slice`；若要判断线程池是否饱和，也就是是否缺少空闲线程接收新事务，应同时观察服务端并发事务数、可用 Binder 线程数、事务排队与各线程状态。

## 内存与 GC 分析

### GC 事件的墙上时间不等于全线程暂停

ART 的垃圾回收包含并发阶段与暂停阶段。`*concurrent*GC` 顶层 `slice` 的 `dur` 覆盖整个回收事件，不能当作所有 Java 线程的停顿时间。Android 17 的 `android.garbage_collection` 模块会把 GC 区间与执行该 GC 的线程状态相交，并结合 `Heap size (KB)` 计数器估算回收量。

读取标准库整理好的 GC 事件，可以同时观察墙上时间、CPU 运行、`Runnable`、I/O 等待和回收量，避免只盯着一个 `dur`。

```sql
INCLUDE PERFETTO MODULE android.garbage_collection;

SELECT
  upid,
  gc_id,
  gc_ts,
  gc_type,
  is_mark_compact,
  thread_name,
  ROUND(gc_dur / 1e6, 3) AS wall_ms,
  ROUND(gc_running_dur / 1e6, 3) AS running_ms,
  ROUND(gc_runnable_dur / 1e6, 3) AS runnable_ms,
  ROUND(gc_unint_io_dur / 1e6, 3) AS uninterruptible_io_ms,
  ROUND(gc_unint_non_io_dur / 1e6, 3) AS uninterruptible_non_io_ms,
  ROUND(gc_int_dur / 1e6, 3) AS interruptible_sleep_ms,
  ROUND(reclaimed_mb, 3) AS reclaimed_mb,
  ROUND(min_heap_mb, 3) AS min_heap_mb,
  ROUND(max_heap_mb, 3) AS max_heap_mb
FROM android_garbage_collection_events
WHERE process_name = 'com.example.app'
ORDER BY gc_ts;
```

`reclaimed_mb` 依赖 GC 前后的堆计数器，计数器缺失时相关列可能为空。状态分解描述 GC 工作线程，不等同于应用所有线程的暂停分解。研究暂停时，应在 GC 时间窗内检查主线程和其他应用执行线程的 `slice`、调度状态及 ART 暂停标记。

### Java 堆计数器是离散采样点

`Heap size (KB)` 每次变化产生一个计数器点。两点之间只能解释为“最近一次记录值持续到下一次更新”，无法推导未采集时刻的分配细节。查询这些采样点，可以检查目标进程的 Java 堆趋势和采样间隔。

```sql
SELECT
  process.upid,
  counter.ts,
  ROUND(counter.value / 1024.0, 3) AS heap_mib,
  ROUND(
    (
      LEAD(counter.ts) OVER (
        PARTITION BY counter.track_id
        ORDER BY counter.ts
      ) - counter.ts
    ) / 1e6,
    3
  ) AS until_next_sample_ms
FROM counter
JOIN process_counter_track AS track
  ON track.id = counter.track_id
JOIN process
  USING (upid)
WHERE process.name = 'com.example.app'
  AND track.name = 'Heap size (KB)'
ORDER BY counter.ts;
```

这里用 1024 把 KiB 换成 MiB。标准库中的列名采用 `*_mb`，该模块按自身约定换算；跨报表比较时应标明单位，避免把 MB 与 MiB 混在一列。

## 启动时间分析

### 平台启动事件优先于手工拼 `slice`

手工用 `bindApplication` 到第一个 `doFrame` 推导冷启动，容易漏掉 `system_server`（承载 Android 核心系统服务的进程）发起阶段、`RenderThread` 渲染线程、可见帧以及热启动分支。`android.startup.startups` 会按 Trace 中记录的 SDK 版本与事件格式选择解析路径，输出 `android_startups` 和 `android_startup_processes`。`android.startup.time_to_display` 继续关联首帧与 `reportFullyDrawn()`，提供 TTID（Time To Initial Display，首次显示耗时）与 TTFD（Time To Full Display，完全显示耗时）。

列出目标包的启动区间与显示时间，可以保留平台识别的 `cold`、`warm`、`hot` 分类。这三类对应进程和 Activity 是否已经存在的不同启动路径，不能只按耗时长短命名；查询同时区分启动区间、首次显示与完全显示。

```sql
INCLUDE PERFETTO MODULE android.startup.startups;
INCLUDE PERFETTO MODULE android.startup.time_to_display;

SELECT
  startups.startup_id,
  startups.ts,
  startups.startup_type,
  ROUND(startups.dur / 1e6, 3) AS startup_interval_ms,
  ROUND(display.time_to_initial_display / 1e6, 3) AS ttid_ms,
  ROUND(display.time_to_full_display / 1e6, 3) AS ttfd_ms,
  display.ttid_frame_id,
  display.ttfd_frame_id,
  processes.upid,
  processes.pid
FROM android_startups AS startups
LEFT JOIN android_startup_time_to_display AS display
  USING (startup_id)
LEFT JOIN android_startup_processes AS processes
  USING (startup_id)
WHERE startups.package = 'com.example.app'
ORDER BY startups.ts;
```

TTFD 依赖应用调用 `reportFullyDrawn()` 以及对应追踪事件；空值不能当作零毫秒。进程在启动期间死亡并重建时，一个 `startup_id` 可能关联多个进程，查询会保留每个 `upid`，但 TTID / TTFD 仍是该启动实例的一组显示时间，会在这些进程行中重复。若要确认标准库最终用哪个进程匹配首帧，应同时查看 `android_startup_time_to_display.upid`。

### 标准库分解启动主线程时间

`android.startup.startup_breakdowns` 会把启动主线程 `slice` 与 `thread_state` 裁成互斥区间，并按标准库规则给每段生成 `reason`。这些原因是派生分类，不是设备直接记录的原始事件；它们适合筛选候选原因，仍要用原始时间线和源码确认。

按启动和原因汇总耗时，可以找出 `Running`、`Runnable`、Binder、I/O、类加载等时间主要落在哪些区间。

```sql
INCLUDE PERFETTO MODULE android.startup.startup_breakdowns;

SELECT
  startups.startup_id,
  startups.startup_type,
  breakdown.reason,
  COUNT(*) AS interval_count,
  ROUND(SUM(breakdown.dur) / 1e6, 3) AS total_ms,
  ROUND(MAX(breakdown.dur) / 1e6, 3) AS longest_ms
FROM android_startups AS startups
JOIN android_startup_opinionated_breakdown AS breakdown
  USING (startup_id)
WHERE startups.package = 'com.example.app'
GROUP BY startups.startup_id, startups.startup_type, breakdown.reason
ORDER BY startups.startup_id, SUM(breakdown.dur) DESC;
```

模块源码明确建议采集 Binder、ART、`am` 和 `view` 事件。缺少这些数据时，原因分类会变粗，查询仍能执行却无法提供相同解释力。

### 启动区间内的 Binder 事务

启动期间的 Binder 调用需要同时满足进程映射与时间相交。仅按进程名搜索会混入启动之前、之后或旧进程实例的调用。

按启动实例汇总应用发起的 Binder 事务，可以区分同步等待与异步发送，并保留服务端进程和接口维度。

```sql
INCLUDE PERFETTO MODULE android.startup.startups;
INCLUDE PERFETTO MODULE android.binder;

SELECT
  startup.startup_id,
  startup.startup_type,
  binder.is_sync,
  binder.server_process,
  COALESCE(binder.interface, '<unresolved interface>') AS interface,
  COALESCE(binder.method_name, '<unresolved method>') AS method_name,
  COUNT(*) AS call_count,
  ROUND(SUM(binder.client_dur) / 1e6, 3) AS summed_client_ms,
  ROUND(MAX(binder.client_dur) / 1e6, 3) AS max_client_ms
FROM android_startups AS startup
JOIN android_startup_processes AS startup_process
  USING (startup_id)
JOIN android_binder_txns AS binder
  ON binder.client_upid = startup_process.upid
 AND binder.client_ts < startup.ts_end
 AND binder.client_ts + binder.client_dur > startup.ts
WHERE startup.package = 'com.example.app'
  AND binder.client_dur >= 0
GROUP BY
  startup.startup_id,
  startup.startup_type,
  binder.is_sync,
  binder.server_process,
  binder.interface,
  binder.method_name
ORDER BY startup.startup_id, summed_client_ms DESC;
```

各事务可能互相重叠，`summed_client_ms` 是事务时长之和，不能当作启动区间中的独占时间。同步主线程事务更接近直接阻塞候选；后台线程或异步事务需要继续核对依赖关系。

## ANR（Application Not Responding，应用无响应）分析

### ANR 没有统一的 5 秒窗口

输入分发超时常见默认值为 5 秒，Broadcast、Service、JobService、前台服务和 `system_server` 看门狗使用不同规则；这里的看门狗是检测系统线程长时间无响应的超时机制。OEM（设备厂商）与前后台状态还可能改写超时。Android 17 的 `android.anrs` 模块会从 `system_server` 的 ErrorId、Subject 与计时事件中解析 `anr_type`、`anr_dur_ms` 和 `default_anr_dur_ms`；源码也明确标注默认值仅对应 AOSP（Android Open Source Project）/ Pixel 的常见配置。

查询 Trace 中的 ANR，可以检查解析出的类型、主题和时长。这个入口比按日志文字模糊搜索更可靠。

```sql
INCLUDE PERFETTO MODULE android.anrs;

SELECT
  ts,
  process_name,
  pid,
  upid,
  error_id,
  anr_type,
  anr_dur_ms,
  default_anr_dur_ms,
  ROUND(timer_delay / 1e6, 3) AS timer_delay_ms,
  subject,
  intent,
  component
FROM android_anrs
ORDER BY ts;
```

该表依赖对应平台事件被写入 Trace。表为空时，可以另查 `android_logs` 或外部 `bugreport` 诊断包，但日志与 Trace 需要有可校准的时间基准。`default_anr_dur_ms` 适合解释平台默认路径，不应覆盖设备现场配置。

### 从 ANR 时刻向前检查主线程

分析窗口应由 ANR 类型和现场信息决定。下面的模板选择目标进程最近一次 ANR，并向前查看 10 秒、向后查看 1 秒。两个窗口值是分析参数，运行前应按 `anr_dur_ms`、事件类型和 Trace 覆盖范围修改。

```sql
INCLUDE PERFETTO MODULE android.anrs;

WITH
  settings(process_name, lookback_ns, after_ns) AS (
    VALUES (
      'com.example.app',
      10000000000,
      1000000000
    )
  ),
  chosen_anr AS (
    SELECT android_anrs.*
    FROM android_anrs
    JOIN settings
      ON settings.process_name = android_anrs.process_name
    ORDER BY android_anrs.ts DESC
    LIMIT 1
  ),
  main_thread AS (
    SELECT thread.utid
    FROM chosen_anr
    JOIN thread
      ON thread.upid = chosen_anr.upid
    WHERE thread.is_main_thread = 1
       OR thread.tid = chosen_anr.pid
  ),
  state_intersections AS (
    SELECT
      thread_state.state,
      thread_state.io_wait,
      thread_state.blocked_function,
      MIN(
        CASE
          WHEN thread_state.dur = -1 THEN trace_end()
          ELSE thread_state.ts + thread_state.dur
        END,
        chosen_anr.ts + settings.after_ns
      ) - MAX(
        thread_state.ts,
        chosen_anr.ts - settings.lookback_ns
      ) AS overlap_dur
    FROM thread_state
    JOIN main_thread USING (utid)
    CROSS JOIN chosen_anr
    CROSS JOIN settings
    WHERE thread_state.ts < chosen_anr.ts + settings.after_ns
      AND CASE
            WHEN thread_state.dur = -1 THEN trace_end()
            ELSE thread_state.ts + thread_state.dur
          END > chosen_anr.ts - settings.lookback_ns
  )
SELECT
  state,
  io_wait,
  COALESCE(blocked_function, '<no blocked function>') AS blocked_function,
  COUNT(*) AS interval_count,
  ROUND(SUM(overlap_dur) / 1e6, 3) AS total_ms,
  ROUND(MAX(overlap_dur) / 1e6, 3) AS longest_ms
FROM state_intersections
GROUP BY state, io_wait, blocked_function
ORDER BY SUM(overlap_dur) DESC;
```

结果的解释依赖状态：大量 `Running` 要结合调用栈和 `slice` 找 CPU 工作；大量 `R` / `R+` 指向调度排队；`D` 且 `io_wait = 1` 指向内核 I/O 等待；`S` 还需检查 Binder 回复、`futex`、monitor contention 与应用等待事件。单凭 `blocked_function` 不能判断 Java 层持锁者。

## 锁竞争与同步分析

### Monitor contention 提供阻塞方与持锁方

Monitor contention 指线程进入 Java `synchronized` 代码时，对象锁已被其他线程持有而发生等待。ART 会把这类锁竞争记录成带方法信息的 `slice`。Android 17 的 `android.monitor_contention` 模块解析阻塞线程、持锁线程、方法、源码位置、锁名和 Binder 回复关系。`lock_name` 已是标准表字段，但它来自周围 `slice` 的解析，缺失时应回到 `blocking_method` 与 `blocked_method`。

列出目标进程最长的 monitor 锁竞争，可以同时确认谁被阻塞、谁持锁，以及主线程是否参与。

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  upid,
  id,
  ts,
  ROUND(dur / 1e6, 3) AS wait_ms,
  lock_name,
  blocked_thread_name,
  blocked_thread_tid,
  blocked_method,
  blocked_src,
  blocking_thread_name,
  blocking_thread_tid,
  blocking_method,
  blocking_src,
  waiter_count,
  is_blocked_thread_main,
  is_blocking_thread_main,
  binder_reply_id
FROM android_monitor_contention
WHERE process_name = 'com.example.app'
  AND dur >= 0
ORDER BY dur DESC
LIMIT 30;
```

`waiter_count` 使用从零开始的序号：值为 0 表示当前线程是第一个等待者，不表示没人等待。因此它不能直接当作线程池总等待人数。`binder_reply_id` 有值时，持锁工作可能发生在 Binder 服务线程；应继续检查对应事务和持锁线程状态。

### 锁等待与帧要按交集长度关联

锁等待可能从 `doFrame` 开始前延续到回调内，也可能在回调结束后继续。只用“contention 完全包含于 `doFrame`”会漏掉两端跨界事件。正确做法是计算两个半开区间的交集。

统计每个应用帧的 `doFrame` 中，UI 线程被 monitor 锁竞争覆盖的时间，可以识别锁等待与慢帧的时间相关性。查询不预设固定毫秒阈值。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;
INCLUDE PERFETTO MODULE android.monitor_contention;

WITH lock_overlap AS (
  SELECT
    frames.upid,
    frames.frame_id,
    do_frame.dur AS do_frame_dur,
    contention.id AS contention_id,
    contention.lock_name,
    contention.blocking_thread_name,
    MIN(do_frame.ts + do_frame.dur, contention.ts + contention.dur)
      - MAX(do_frame.ts, contention.ts) AS overlap_dur
  FROM android_frames AS frames
  JOIN slice AS do_frame
    ON do_frame.id = frames.do_frame_id
  JOIN android_monitor_contention AS contention
    ON contention.blocked_utid = frames.ui_thread_utid
   AND contention.ts < do_frame.ts + do_frame.dur
   AND contention.ts + contention.dur > do_frame.ts
  WHERE frames.process_name = 'com.example.app'
    AND frames.dur >= 0
    AND do_frame.dur >= 0
    AND contention.dur >= 0
)
SELECT
  frames.upid,
  frames.frame_id,
  ROUND(frames.dur / 1e6, 3) AS frame_wall_ms,
  ROUND(lock_overlap.do_frame_dur / 1e6, 3) AS do_frame_ms,
  ROUND(overrun.overrun / 1e6, 3) AS deadline_overrun_ms,
  COUNT(lock_overlap.contention_id) AS contention_count,
  ROUND(SUM(lock_overlap.overlap_dur) / 1e6, 3) AS lock_overlap_ms,
  GROUP_CONCAT(DISTINCT lock_overlap.lock_name) AS lock_names
FROM android_frames AS frames
JOIN lock_overlap
  USING (upid, frame_id)
LEFT JOIN android_frames_overrun AS overrun
  USING (frame_id)
WHERE frames.process_name = 'com.example.app'
GROUP BY
  frames.upid,
  frames.frame_id,
  frames.dur,
  lock_overlap.do_frame_dur,
  overrun.overrun
ORDER BY lock_overlap_ms DESC;
```

同一段 `doFrame` 中的多个锁等待通常不会在同一个 UI 线程上重叠，若采集数据或解析结果出现重叠，简单求和可能超过回调时长。遇到这种情况要检查原始 `slice`，或先把重叠区间归并后再求和。

## `SPAN_JOIN` 与跨维度时间关联

### `SPAN_JOIN` 计算两个区间流的交集

`SPAN_JOIN` 接受两张至少含 `ts`、`dur` 的表或视图，并输出它们的时间交集。`PARTITIONED cpu` 会先按 CPU 编号分组，只让编号相同的区间求交。每张输入表在同一分区内都不能出现互相重叠的区间；Perfetto 不保证为这种输入报错，结果可能静默出错。普通业务 `slice` 经常嵌套，直接交给 `SPAN_JOIN` 会破坏这个前提。

CPU 运行区间和 CPU 频率区间是典型用法。`sched` 已按 CPU 给出不重叠运行片段；`counter` 需要用下一采样点补出 `dur`。把两者交给 `SPAN_JOIN`，可计算目标进程每个线程在各 CPU 频率上的运行时间。

```sql
CREATE PERFETTO VIEW cookbook_sched AS
SELECT
  ts,
  dur,
  cpu,
  utid
FROM sched
WHERE dur >= 0;

CREATE PERFETTO TABLE cookbook_frequency (
  ts TIMESTAMP,
  dur DURATION,
  cpu LONG,
  freq_khz LONG
) AS
SELECT
  counter.ts,
  COALESCE(
    LEAD(counter.ts) OVER (
      PARTITION BY counter.track_id
      ORDER BY counter.ts
    ),
    trace_end()
  ) - counter.ts AS dur,
  cpu_counter_track.cpu,
  CAST(counter.value AS INTEGER) AS freq_khz
FROM counter
JOIN cpu_counter_track
  ON cpu_counter_track.id = counter.track_id
WHERE cpu_counter_track.name = 'cpufreq';

CREATE VIRTUAL TABLE cookbook_sched_with_frequency
USING SPAN_JOIN(
  cookbook_sched PARTITIONED cpu,
  cookbook_frequency PARTITIONED cpu
);

SELECT
  process.name AS process_name,
  thread.name AS thread_name,
  cookbook_sched_with_frequency.cpu,
  cookbook_sched_with_frequency.freq_khz,
  ROUND(SUM(cookbook_sched_with_frequency.dur) / 1e6, 3) AS running_ms
FROM cookbook_sched_with_frequency
JOIN thread
  USING (utid)
JOIN process
  USING (upid)
WHERE process.name = 'com.example.app'
GROUP BY
  process.name,
  thread.utid,
  thread.name,
  cookbook_sched_with_frequency.cpu,
  cookbook_sched_with_frequency.freq_khz
ORDER BY running_ms DESC;
```

该脚本会在当前 SQL 会话创建对象，重复执行前要删除对象或更换名称。`cpufreq` 只在频率事件或轮询数据存在时有结果；事件驱动采集还可能缺失 Trace 开头的初始频率。空结果不能推断 CPU 没有运行。

### 锁等待不能与同线程 `Running` 区间做交集

被 monitor 锁竞争阻塞的线程在等待期间没有运行。同一个 `utid` 上，锁等待区间与 `sched` 的 `Running` 区间按定义互斥。对两者执行 `SPAN_JOIN` 得到空集属于正确结果，用它分析“锁等待时的 CPU 频率”在语义上也没有价值。

帧分析可以按以下关系组织：

1. 用 `android_frames` 取得帧窗口、`doFrame` 和 UI / `RenderThread` 的 `utid`。
2. 把 `doFrame` 与 UI 线程的 `thread_state` 相交，得到 `Running`、`Runnable`、睡眠与 I/O 等待时间。
3. 把 `doFrame` 与 `android_monitor_contention` 相交，得到锁等待覆盖时间。
4. 只对 `Running` 片段关联 `sched` 和 `cpufreq`，解释线程获得 CPU 后运行在哪个频率。

每段 `doFrame` 的 UI 线程状态分解和锁等待覆盖可以筛出后续要检查的帧；CPU 频率仍使用上一段 `SPAN_JOIN` 结果按时间窗另行关联。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;
INCLUDE PERFETTO MODULE android.monitor_contention;

WITH
  target_frames AS (
    SELECT
      frames.*,
      do_frame.ts AS do_frame_ts,
      do_frame.dur AS do_frame_dur
    FROM android_frames AS frames
    JOIN slice AS do_frame
      ON do_frame.id = frames.do_frame_id
    WHERE frames.process_name = 'com.example.app'
      AND frames.dur >= 0
      AND do_frame.dur >= 0
  ),
  state_overlap AS (
    SELECT
      frames.upid,
      frames.frame_id,
      states.state,
      states.io_wait,
      MIN(
        frames.do_frame_ts + frames.do_frame_dur,
        CASE
          WHEN states.dur = -1 THEN trace_end()
          ELSE states.ts + states.dur
        END
      ) - MAX(frames.do_frame_ts, states.ts) AS overlap_dur
    FROM target_frames AS frames
    JOIN thread_state AS states
      ON states.utid = frames.ui_thread_utid
     AND states.ts < frames.do_frame_ts + frames.do_frame_dur
     AND CASE
           WHEN states.dur = -1 THEN trace_end()
           ELSE states.ts + states.dur
         END > frames.do_frame_ts
  ),
  state_totals AS (
    SELECT
      upid,
      frame_id,
      SUM(CASE WHEN state = 'Running' THEN overlap_dur ELSE 0 END) AS running_dur,
      SUM(CASE WHEN state IN ('R', 'R+') THEN overlap_dur ELSE 0 END) AS runnable_dur,
      SUM(
        CASE
          WHEN state = 'D' AND io_wait = 1 THEN overlap_dur
          ELSE 0
        END
      ) AS io_wait_dur,
      SUM(
        CASE
          WHEN state = 'S' THEN overlap_dur
          ELSE 0
        END
      ) AS interruptible_sleep_dur
    FROM state_overlap
    GROUP BY upid, frame_id
  ),
  lock_totals AS (
    SELECT
      frames.upid,
      frames.frame_id,
      COUNT(*) AS contention_count,
      SUM(
        MIN(
          frames.do_frame_ts + frames.do_frame_dur,
          contention.ts + contention.dur
        ) - MAX(frames.do_frame_ts, contention.ts)
      ) AS lock_overlap_dur
    FROM target_frames AS frames
    JOIN android_monitor_contention AS contention
      ON contention.blocked_utid = frames.ui_thread_utid
     AND contention.ts < frames.do_frame_ts + frames.do_frame_dur
     AND contention.ts + contention.dur > frames.do_frame_ts
    WHERE contention.dur >= 0
    GROUP BY frames.upid, frames.frame_id
  )
SELECT
  frames.upid,
  frames.frame_id,
  frames.ts,
  ROUND(frames.dur / 1e6, 3) AS frame_wall_ms,
  ROUND(frames.do_frame_dur / 1e6, 3) AS do_frame_ms,
  ROUND(overrun.overrun / 1e6, 3) AS deadline_overrun_ms,
  ROUND(state_totals.running_dur / 1e6, 3) AS running_ms,
  ROUND(state_totals.runnable_dur / 1e6, 3) AS runnable_ms,
  ROUND(state_totals.io_wait_dur / 1e6, 3) AS io_wait_ms,
  ROUND(
    state_totals.interruptible_sleep_dur / 1e6,
    3
  ) AS interruptible_sleep_ms,
  COALESCE(lock_totals.contention_count, 0) AS contention_count,
  ROUND(COALESCE(lock_totals.lock_overlap_dur, 0) / 1e6, 3) AS lock_ms
FROM target_frames AS frames
LEFT JOIN android_frames_overrun AS overrun
  USING (frame_id)
LEFT JOIN state_totals
  USING (upid, frame_id)
LEFT JOIN lock_totals
  USING (upid, frame_id)
ORDER BY overrun.overrun DESC, frames.ts;
```

状态总量接近 `do_frame_ms`，说明调度事件覆盖较完整；差值较大时应检查 Trace 是否从区间中途开始、是否有数据丢失，或 UI 线程标识是否正确。锁时间属于睡眠时间中的一个具体原因，不应再与各状态相加作为“总耗时”。

## I/O：把线程等待与块设备活动分开

块设备事件描述请求何时进入和离开设备队列，文件系统事件描述更高层的读写、同步和页操作。线程进入 `D` 状态，不能单独证明它在等待存储；块设备繁忙，也不能单独证明请求来自目标进程。

录制前先检查目标设备公开的文件系统和块事件：

```bash
adb shell 'cat /sys/kernel/tracing/available_events' \
  | grep -E '^(block|f2fs|ext4|erofs):'
```

设备输出决定 `ftrace_events` 能配置哪些事件。采集结束后还要检查 Trace Processor 自诊断表 `stats` 中的 `unknown_ftrace_events` 与 `failed_ftrace_events`，它们分别表示事件名未知和事件启用失败；否则容易把未启用的数据源误读成“没有 I/O”。

Android 17 的 `linux.block_io` 模块可以按设备查看仍在队列或设备中的活动请求：

```sql
INCLUDE PERFETTO MODULE linux.block_io;

SELECT
  ts,
  linux_device_major_id(dev) AS major_id,
  linux_device_minor_id(dev) AS minor_id,
  ops_in_queue_or_device
FROM linux_active_block_io_operations_by_device
WHERE ops_in_queue_or_device > 0
ORDER BY ts;
```

这张表回答“哪台块设备在何时有多少请求”，不包含应用进程和文件路径。应用归因至少还需要以下证据中的两类：

- 目标线程的文件、SQLite、资源加载或自定义 Trace slice 与设备活动重叠；
- 同一区间的 `thread_state` 为 `D`，并且 `sched_blocked_reason` 或内核调用栈指向块层、文件系统或页故障路径；
- 文件系统事件携带的 inode（文件系统对象编号）、设备或操作类型与块设备请求相符；
- 停止目标操作或切换到对照场景后，线程等待和设备压力同步变化。

`SharedPreferences.commit()` 会同步等待结果；`apply()` 虽先更新内存并安排磁盘写入，但 Android 用来管理延后任务的 `QueuedWork` 仍可能在组件停止时等待后台任务。SQLite 事务、`fsync`（要求把文件修改同步到持久存储）、首次资源页故障和系统回写也要按各自事件验证。全量 `raw_syscalls/sys_enter` / `sys_exit` 事件率很高，只应在短窗口、足够大的缓冲区和明确复现场景下启用。

## 功耗：联合频率、空闲、Suspend 与唤醒锁

CPU 频率高只表示策略选择了较高频点，不能单独推出 CPU 正在持续执行大量工作。调度负载、Governor（动态选择 CPU 频率的策略）、Boost（短时提高性能档位的机制）、热限制、CPU 容量和任务所在核心集群都会影响频率。功耗分析至少要联合 CPU 运行时间、频率、空闲状态、Suspend（整机进入低功耗休眠）和唤醒锁；唤醒锁用于要求系统保持唤醒。

下面的配置片段采集频率、空闲、系统休眠和内核唤醒锁；buffer 与时长仍需按目标设备的数据率调整：

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
    }
  }
}

data_sources {
  config {
    name: "android.kernel_wakelocks"
    kernel_wakelocks_config { poll_ms: 1000 }
  }
}
```

部分设备不会公开完整的 suspend、wakeup source（内核记录的唤醒来源）或 idle 事件。USB 调试连接本身也可能阻止设备进入完整系统休眠，测试记录必须注明供电与连接方式。

下面的查询把系统休眠区间与唤醒锁累计持有时间放进同一结果集：

```sql
INCLUDE PERFETTO MODULE android.suspend;
INCLUDE PERFETTO MODULE android.kernel_wakelocks;

WITH power_summary AS (
  SELECT
    'suspend_state' AS category,
    power_state AS item,
    SUM(dur) AS total_dur
  FROM android_suspend_state
  GROUP BY power_state

  UNION ALL

  SELECT
    'wakelock' AS category,
    name AS item,
    SUM(held_dur) AS total_dur
  FROM android_kernel_wakelocks
  GROUP BY name
)
SELECT
  category,
  item,
  ROUND(total_dur / 1e9, 3) AS total_s
FROM power_summary
ORDER BY category, total_dur DESC;
```

`android_suspend_state` 将 Trace 时间补成 `awake` 与 `suspended` 区间。`android_kernel_wakelocks` 的每一行对应一个采样区间，`held_dur` 表示该区间内唤醒锁实际持有的累计时间。唤醒锁持有与耗电相关，但仍需找到持有者和同一区间中的实际工作。

CPU 频率应按区间做时间加权；直接平均离散采样点，会让持续时间不同的频点获得相同权重：

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

SELECT
  cpu,
  ROUND(SUM(freq * dur) / SUM(dur) / 1000.0, 1) AS weighted_avg_mhz,
  ROUND(MAX(freq) / 1000.0, 1) AS max_mhz,
  ROUND(SUM(dur) / 1e9, 3) AS covered_s
FROM cpu_frequency_counters
WHERE freq IS NOT NULL AND dur > 0
GROUP BY cpu
ORDER BY cpu;
```

`freq` 的单位是 kHz。加权平均频率适合比较相同设备和场景中的策略结果，不是能量估算：CPU 可能高频空闲，也可能低频持续运行。还要关联 `cpu_idle_counters`、`sched`、功率轨（芯片不同供电域的测量通道）和电池电流。系统无法 Suspend 时，再按时间顺序检查显示状态、用户空间 / 内核唤醒锁、活跃定时器和 `android.wakeups` 给出的唤醒或休眠失败原因。

## 跨进程证据使用稳定身份

启动、Binder 和显示都跨进程。启动使用 `startup_id` 与 `android_startup_processes.upid`；Binder 使用 `binder_txn_id` / `binder_reply_id`；帧使用 `surface_frame_token`、`display_frame_token` 与 flow 关系；调度使用 `utid` / `upid`。PID、TID、进程名和线程名只用于筛选与展示，不能承担唯一身份。

跨进程区间应来自同一录制会话。合并不同设备或不同会话的 Trace 时，必须有可验证的时钟快照和同步事件；时钟快照记录同一已知时刻在不同时间基准下的数值，用于建立换算关系。仅按文件起点平移，不能支撑毫秒级因果判断。

## 从 SQL 结果回到证据链

SQL 排名适合缩小范围，性能结论仍要经过时间、线程、事件和源码四项核对：

1. 记录 Trace 文件、采集配置、设备构建、刷新率、场景步骤和 Trace Processor 版本。
2. 从 FrameTimeline 判定、启动实例或 ANR 事件选定时间窗，避免先看整份 Trace 中排名前 N 的全局结果。
3. 用 `upid`、`utid` 和事件 `id` 固定对象；进程名与线程名只用于筛选和展示。
4. 用 `thread_state` 判断时间花在 `Running`、`Runnable` 还是等待，再选择采样栈、Binder、GC、锁或 I/O 查询。
5. 回到 Perfetto UI 检查事件的父子关系、相邻事件与数据缺口。
6. 用 Android 17 平台源码和内核基线确认追踪点语义；缺少证据时保留为候选原因。

一条可复查的结论应写成：“FrameTimeline 将帧 842 标记为 `App Deadline Missed`；该帧 UI 线程有 6.2 ms 的 `R` 状态，其中最长区间由某线程唤醒；同窗口未发现 monitor 锁竞争。”数字必须来自具体 Trace。不能把教程中的示例参数抄成产品阈值，也不能把时间相关性写成因果关系。

## 源码与文档依据

- [PerfettoSQL 入门与 `SPAN_JOIN`](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started)
- [PerfettoSQL 语法与模块加载](https://perfetto.dev/docs/analysis/perfetto-sql-syntax)
- [Trace Processor 基础表：`slice`、`sched`、`thread_state`](https://perfetto.dev/docs/analysis/sql-tables)
- [CPU 调度数据源与线程状态编码](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [FrameTimeline 数据源与原始表](https://perfetto.dev/docs/data-sources/frametimeline)
- [CPU 频率数据源与 `cpufreq` 计数器](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Android 17 `android.frames.timeline` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)
- [Android 17 `android.frames.per_frame_metrics` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/per_frame_metrics.sql)
- [Android 17 `android.binder` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)
- [Android 17 `android.garbage_collection` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/garbage_collection.sql)
- [Android 17 `android.startup.startups` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startups.sql)
- [Android 17 `android.startup.time_to_display` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/time_to_display.sql)
- [Android 17 `android.anrs` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/anrs.sql)
- [Android 17 `android.monitor_contention` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/monitor_contention.sql)
- [Android 17 `linux.block_io` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/block_io.sql)
- [Android 17 `android.suspend` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/suspend.sql)
- [Android 17 `android.kernel_wakelocks` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/kernel_wakelocks.sql)
- [Android 17 kernel 6.18 `sched` tracepoint 定义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
