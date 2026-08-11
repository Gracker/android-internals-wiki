---
title: "Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数"
chapter: "13.10"
section: "13.10"
section_title: "Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数"
status: finalized
drafted_date: "2026-05-15"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-15"
last_verified_against: "Perfetto Trace Processor docs + google/perfetto source master, external/perfetto mirror"
confidence: high
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-13-perfetto-span-join-window-function.md"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/analysis/perfetto-sql-getting-started"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
  - type: aosp
    path: "external/perfetto/src/trace_processor/perfetto_sql/intrinsics/operators/span_join_operator.cc"
  - type: aosp
    path: "external/perfetto/src/trace_processor/perfetto_sql/intrinsics/operators/span_join_operator.h"
  - type: aosp
    path: "external/perfetto/src/trace_processor/perfetto_sql/stdlib/sched/thread_executing_span_with_slice.sql"
tags: ["perfetto", "sql", "span-join", "trace-processor", "frame-analysis"]
related_chapters: ["13.9", "13.5", "14.23"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/研究素材"
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-16"
task6_reviewed_date: "2026-06-16"
last_task6_at: "2026-06-16T03:07:00+08:00"
task6_review_notes: "2026-06-16 Task6 复审:pass-light-edit。无禁用词/高频词/AI套话命中。frontmatter 格式清理(删除空行)。L1/L2 全部通过,无B类问题。Task9 needs-rework 状态保持,不可自动晋升。"
pipeline_stage: ready-to-publish
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-16"
last_task9_at: "2026-06-16T03:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-16-03-deep-review.md"
task9_review_notes: "2026-06-16 Task9 复审:pass-tech-review。frame/cpufreq 边界裁剪与 GC pause window 运行最大结束时间合并算法已通过复核；queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task9_audit: "2026-07-13"
last_task9_audit_at: "2026-07-13T00:26:22+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-13-00-audit.md"
last_task9_audit_result: "pass-idle-audit"
task2b_state: fixed
task2b_result: fixed
last_task2b_main_at: 2026-06-16T02:50:00+08:00
updated_by: "openclaw-task6"
updated_date: "2026-06-30"
last_task6_audit: "2026-06-30"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
last_task9_audit_notes: "idle audit: 维度1（源码引用准确性）和维度3（版本差异覆盖）检查通过；AOSP android-17.0.0_r1 external/perfetto 的 SPAN_JOIN、sched.cpu/ucpu、cpu_frequency_counters 与 flattened slice 路径复核通过；无 P0/P1/P2。"
---

# 13.10 Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数

区间关联最容易出现“SQL 能运行，数字却多算或少算”的问题。帧、线程调度状态和锁等待已经带有 `ts + dur`；CPU 频率、内存等计数器只有采样时刻，要先补出有效区间。输入区间一旦重叠、分区键选错或末端边界没有定义，`SPAN_JOIN` 不会替查询者修正语义。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`，调度事件对应的内核锚点为 `android17-6.18-2026-06_r6`。示例使用 Android 17 Perfetto SQL 标准库和该版本的 `span_join_operator` 约束；历史版本可以保留各自字段差异，但分析结果不得套用高于 Android 17 的平台假设。

## `SPAN_JOIN` 处理区间交集

Perfetto 把含 `ts` 和 `dur` 的一行称为时间段（`span`）。区间采用半开形式 `[ts, ts + dur)`；相邻区间在同一个端点接触时，交集长度为零。`slice`、`sched` 和 `thread_state` 已经是时间段，`counter` 表中仍是离散采样点。

普通 SQL 也能计算交集。两段时间相交的条件为 `a.ts < b.end_ts AND b.ts < a.end_ts`，交集起点取两个起点的较大值，终点取两个终点的较小值。下面用固定数据验证这套公式，便于观察边界。

```sql
WITH
  table_a(id, ts, dur) AS (
    VALUES
      (1, 10, 10),
      (2, 30, 10)
  ),
  table_b(id, ts, dur) AS (
    VALUES
      (11, 15, 20),
      (12, 40, 5)
  )
SELECT
  table_a.id AS a_id,
  table_b.id AS b_id,
  MAX(table_a.ts, table_b.ts) AS overlap_ts,
  MIN(
    table_a.ts + table_a.dur,
    table_b.ts + table_b.dur
  ) - MAX(table_a.ts, table_b.ts) AS overlap_dur
FROM table_a
JOIN table_b
  ON table_a.ts < table_b.ts + table_b.dur
 AND table_b.ts < table_a.ts + table_a.dur
ORDER BY a_id, b_id;
```

第一段交集是 `[15, 20)`，时长为 5。`table_a` 的第二段结束于 40，`table_b` 的第二段从 40 开始，两者只接触端点，因此不会输出一行。对小表或可能嵌套的事件，普通区间条件通常更容易保留事件身份。

`SPAN_JOIN` 把交集计算实现为虚拟表算子。它会将两侧区间按时间切开，并把两侧除 `ts`、`dur` 和分区键以外的列带到结果中。下面的合成数据演示按整数分区关联。

```sql
CREATE PERFETTO TABLE demo_left (
  ts TIMESTAMP,
  dur DURATION,
  part_id LONG,
  left_name STRING
) AS
WITH data(ts, dur, part_id, left_name) AS (
  VALUES
    (10, 10, 1, 'left-a'),
    (30, 10, 1, 'left-b'),
    (10, 10, 2, 'left-c')
)
SELECT * FROM data;

CREATE PERFETTO TABLE demo_right (
  ts TIMESTAMP,
  dur DURATION,
  part_id LONG,
  right_name STRING
) AS
WITH data(ts, dur, part_id, right_name) AS (
  VALUES
    (15, 20, 1, 'right-a'),
    (12, 4, 2, 'right-b')
)
SELECT * FROM data;

CREATE VIRTUAL TABLE demo_intersection
USING SPAN_JOIN(
  demo_left PARTITIONED part_id,
  demo_right PARTITIONED part_id
);

SELECT
  ts,
  dur,
  part_id,
  left_name,
  right_name
FROM demo_intersection
ORDER BY part_id, ts;
```

分区 1 会输出 `[15, 20)` 与 `[30, 35)`，分区 2 会输出 `[12, 16)`。脚本会在当前 Trace Processor 会话创建对象；重复运行前要删除这些对象或更换名称。

### 算子不会检查同分区重叠

Android 17 的实现会按分区和 `ts` 推进两侧游标。为了保持这一算法的成本可控，算子要求同一输入表、同一分区内的时间段互不重叠。源码和官方文档都明确说明：违反约束时可能静默产生错误行，算子不会主动报错。

输入还要满足以下条件：

- 两侧都必须有 `ts`，且至少一侧必须有 `dur`。点事件本身不定义覆盖范围，区间分析会为两侧都显式提供 `dur`。
- `dur` 应大于零；`dur = -1` 的开放区间要先裁到查询窗口或 `trace_end()`。
- 分区列必须是整数。两侧都分区时，列名必须相同。
- 分区键必须表达同一种实体，例如 `ucpu` 对 `ucpu`、`utid` 对 `utid`。
- 只给一侧分区也受支持，未分区表会分别与每个分区求交。

字符串可以用 `HASH()` 转成整数，但哈希只解决列类型。两个字符串字段的业务含义不同，转成整数后依旧不具备关联关系；自动化查询还应评估哈希碰撞是否可接受。

## 用窗口函数把计数器点变成时间段

计数器在 `ts` 处记录“数值从此刻开始变为 value”。前向有效区间通常为 `[当前 ts, 下一条 ts)`，同一轨道的末条记录延续到明确的窗口末端。`LEAD()` 必须按 `track_id` 分区，否则一个 CPU 的频率点会被另一个 CPU 的采样时刻截断。

手工把 `cpufreq` 计数器转成前向区间，并通过 `cpu` 表取得跨机器 Trace 也唯一的 `ucpu`，可以核对标准库的输入语义。

```sql
WITH frequency_points AS (
  SELECT
    counter.ts,
    LEAD(counter.ts) OVER (
      PARTITION BY counter.track_id
      ORDER BY counter.ts
    ) AS next_ts,
    counter.track_id,
    cpu_desc.ucpu,
    track.cpu,
    CAST(counter.value AS INTEGER) AS freq_khz
  FROM counter
  JOIN cpu_counter_track AS track
    ON track.id = counter.track_id
  JOIN cpu AS cpu_desc
    ON cpu_desc.machine_id IS track.machine_id
   AND cpu_desc.cpu = track.cpu
  WHERE track.name = 'cpufreq'
)
SELECT
  ts,
  COALESCE(next_ts, trace_end()) - ts AS dur,
  ucpu,
  cpu,
  freq_khz
FROM frequency_points
WHERE COALESCE(next_ts, trace_end()) > ts
ORDER BY ucpu, ts;
```

`cpu` 是单机中常见的逻辑 CPU 编号，`ucpu` 是 Trace 内的唯一 CPU 标识。多机器 Trace 应按 `ucpu` 分区。末条记录裁到 `trace_end()` 只表示“最近一次已知值延续到 Trace 结束”，不能补出首个采样点之前的频率。

Android 17 标准库已经封装了同一过程。`linux.cpu.frequency` 通过 `counters.intervals` 生成 `cpu_frequency_counters`，并输出 `ts`、`dur`、`freq`、`ucpu` 和 `cpu`。正式查询优先使用该表。

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

SELECT
  ts,
  dur,
  ucpu,
  cpu,
  freq
FROM cpu_frequency_counters
WHERE dur > 0
ORDER BY ucpu, ts;
```

频率表为空时，应检查 `power/cpu_frequency` ftrace 事件或 `linux.sys_stats` 的 CPU 频率轮询是否启用。事件驱动采集可能在 Trace 开头缺少初始频率；`SPAN_JOIN` 会保留这个数据缺口，不会猜测频率。

## `PARTITIONED` 前先验证输入

`sched` 按 `ucpu` 分区时天然互斥，因为同一个 CPU 同一时刻只运行一个线程。`thread_state` 按 `utid` 分区也应形成互斥状态区间。普通线程 `slice` 带有父子嵌套，直接按 `utid` 交给 `SPAN_JOIN` 会重复计算父层和子层。

下面的检查使用“前序最大结束时间”寻找同一 `utid` 中的重叠。相比只看 `LAG(ts + dur)`，运行最大值可以识别 `[1, 10)`、`[2, 3)`、`[9, 12)` 这类嵌套后再次相交的序列。

```sql
WITH
  candidate_span AS (
    SELECT
      slice.id,
      slice.ts,
      slice.dur,
      thread_track.utid,
      slice.name
    FROM slice
    JOIN thread_track
      ON thread_track.id = slice.track_id
    WHERE slice.name GLOB 'Choreographer#doFrame*'
      AND slice.dur > 0
  ),
  checked AS (
    SELECT
      candidate_span.*,
      MAX(ts + dur) OVER (
        PARTITION BY utid
        ORDER BY ts, dur
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
      ) AS previous_max_end
    FROM candidate_span
  )
SELECT
  id,
  ts,
  dur,
  utid,
  name,
  previous_max_end
FROM checked
WHERE ts < previous_max_end
ORDER BY utid, ts;
```

有输出就说明候选表违反互斥约束。处理方式取决于分析目标：限定具体层级或事件名可以保留事件身份；只关心覆盖时长时，可以先合并区间；需要保留多重重叠身份时，应使用普通区间关联或 `intervals.intersect`。

`intervals.overlap` 提供 `interval_merge_overlapping_partitioned!`，可以按多个分区列生成最小的不重叠覆盖集。下面把目标进程的 `doFrame` 区间按 `upid`、`utid` 合并，适合在只统计覆盖时长时清理输入。

```sql
INCLUDE PERFETTO MODULE intervals.overlap;
INCLUDE PERFETTO MODULE slices.with_context;

WITH target_intervals AS (
  SELECT
    ts,
    dur,
    upid,
    utid
  FROM thread_slice
  WHERE process_name = 'com.example.app'
    AND name GLOB 'Choreographer#doFrame*'
    AND dur > 0
)
SELECT
  ts,
  dur,
  upid,
  utid
FROM interval_merge_overlapping_partitioned!(
  (SELECT * FROM target_intervals),
  (upid, utid)
)
ORDER BY upid, utid, ts;
```

合并后无法再区分原始 `slice.id`。诊断单个事件时应保留原始表；计算某类事件对窗口的总覆盖时间时，合并可以避免嵌套或重复事件被累计多次。

## 案例：每帧运行时间与 CPU 频率

`Choreographer#doFrame` 的墙上时间同时包含运行、等待 CPU 和睡眠。分析频率时只应关联 `sched` 中的 `Running` 区间。Android 17 的 `android.frames.timeline` 已经给出帧与 `doFrame` 的对应关系，避免手工按名称和行号生成不稳定的帧 id。

异构 SoC 上，不同 CPU 簇的频率范围与每 MHz 性能不同。把所有 CPU 的 kHz 混成一个平均值没有可比性。查询输出每帧、每个 `ucpu`、每个频点的运行驻留时间；解释性能时再结合 CPU capacity、簇信息和同设备基线。

下面的完整脚本先关联调度与频率，再按 `utid` 将结果裁进 `doFrame`。两个 `SPAN_JOIN` 的输入在各自分区内均为互斥区间。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE linux.cpu.frequency;

CREATE PERFETTO TABLE cookbook_do_frames (
  ts TIMESTAMP,
  dur DURATION,
  utid LONG,
  upid LONG,
  frame_id LONG,
  frame_wall_dur DURATION
) AS
SELECT
  do_frame.ts,
  do_frame.dur,
  frames.ui_thread_utid AS utid,
  frames.upid,
  frames.frame_id,
  frames.dur AS frame_wall_dur
FROM android_frames AS frames
JOIN slice AS do_frame
  ON do_frame.id = frames.do_frame_id
WHERE frames.process_name = 'com.example.app'
  AND do_frame.dur > 0
  AND frames.dur > 0;

CREATE PERFETTO TABLE cookbook_ui_sched (
  ts TIMESTAMP,
  dur DURATION,
  ucpu LONG,
  utid LONG
) AS
SELECT
  sched.ts,
  sched.dur,
  sched.ucpu,
  sched.utid
FROM sched
JOIN (
  SELECT DISTINCT utid
  FROM cookbook_do_frames
) AS target_threads
  USING (utid)
WHERE sched.dur > 0
  AND sched.ucpu IS NOT NULL;

CREATE VIRTUAL TABLE cookbook_sched_frequency
USING SPAN_JOIN(
  cookbook_ui_sched PARTITIONED ucpu,
  cpu_frequency_counters PARTITIONED ucpu
);

CREATE VIRTUAL TABLE cookbook_frame_running_frequency
USING SPAN_JOIN(
  cookbook_do_frames PARTITIONED utid,
  cookbook_sched_frequency PARTITIONED utid
);

SELECT
  upid,
  frame_id,
  ROUND(frame_wall_dur / 1e6, 3) AS frame_wall_ms,
  ROUND(
    SUM(SUM(dur)) OVER (PARTITION BY upid, frame_id) / 1e6,
    3
  ) AS known_frequency_running_ms,
  ucpu,
  cpu,
  freq AS freq_khz,
  ROUND(SUM(dur) / 1e6, 3) AS residency_ms,
  ROUND(
    100.0 * SUM(dur)
      / SUM(SUM(dur)) OVER (PARTITION BY upid, frame_id),
    2
  ) AS frame_running_share_pct
FROM cookbook_frame_running_frequency
GROUP BY
  upid,
  frame_id,
  frame_wall_dur,
  ucpu,
  cpu,
  freq
ORDER BY upid, frame_id, ucpu, freq;
```

`known_frequency_running_ms` 只累计同时具有 `sched` 和频率数据的运行时间。它小于该帧的主线程总运行时间时，可能存在频率采集缺口。`frame_running_share_pct` 的分母也是已知频率运行时间，不能当作 `doFrame` 的 CPU 占用比例。

频率低不自动等于调频故障。线程可能运行在能效核，短任务也可能在升频前完成；温控、ADPF、线程优先级、CPU affinity 和厂商调度策略都可能影响选择。判断应比较同一设备、同一场景和同一采集配置，并将 `ucpu` 映射到 CPU capacity 或簇。

## 帧 × Binder / 锁 / GC 的交叉分析

`SPAN_JOIN` 适合互斥区间流。Binder 事务可能出现嵌套调用，普通 `slice` 也有父子层级；此时直接按 `utid` 送入算子会违反约束。Android 17 标准库已经提供 Binder、monitor 锁竞争和 GC 事件的语义表，可以先按 `doFrame` 裁剪，再按事件类型合并覆盖区间。

这条查询分别计算 UI 线程 Binder 客户端区间、UI 线程 monitor 锁等待和进程 GC 活动与 `doFrame` 的重叠。`interval_merge_overlapping_partitioned!` 会在每个帧和事件类型内合并重叠，避免同类嵌套事件重复累计。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.binder;
INCLUDE PERFETTO MODULE android.monitor_contention;
INCLUDE PERFETTO MODULE android.garbage_collection;
INCLUDE PERFETTO MODULE intervals.overlap;

WITH
  frame_windows AS (
    SELECT
      frames.upid,
      frames.frame_id,
      frames.ui_thread_utid,
      do_frame.ts,
      do_frame.dur
    FROM android_frames AS frames
    JOIN slice AS do_frame
      ON do_frame.id = frames.do_frame_id
    WHERE frames.process_name = 'com.example.app'
      AND do_frame.dur > 0
  ),
  binder_overlap AS (
    SELECT
      MAX(frames.ts, binder.client_ts) AS ts,
      MIN(
        frames.ts + frames.dur,
        binder.client_ts + binder.client_dur
      ) - MAX(frames.ts, binder.client_ts) AS dur,
      frames.upid,
      frames.frame_id,
      CASE
        WHEN binder.is_sync = 1 THEN 'binder_sync_client'
        ELSE 'binder_async_send'
      END AS event_kind
    FROM frame_windows AS frames
    JOIN android_binder_txns AS binder
      ON binder.client_upid = frames.upid
     AND binder.client_utid = frames.ui_thread_utid
     AND binder.client_ts < frames.ts + frames.dur
     AND binder.client_ts + binder.client_dur > frames.ts
    WHERE binder.client_dur > 0
  ),
  lock_overlap AS (
    SELECT
      MAX(frames.ts, contention.ts) AS ts,
      MIN(
        frames.ts + frames.dur,
        contention.ts + contention.dur
      ) - MAX(frames.ts, contention.ts) AS dur,
      frames.upid,
      frames.frame_id,
      'monitor_contention' AS event_kind
    FROM frame_windows AS frames
    JOIN android_monitor_contention AS contention
      ON contention.upid = frames.upid
     AND contention.blocked_utid = frames.ui_thread_utid
     AND contention.ts < frames.ts + frames.dur
     AND contention.ts + contention.dur > frames.ts
    WHERE contention.dur > 0
  ),
  gc_overlap AS (
    SELECT
      MAX(frames.ts, gc.gc_ts) AS ts,
      MIN(
        frames.ts + frames.dur,
        gc.gc_ts + gc.gc_dur
      ) - MAX(frames.ts, gc.gc_ts) AS dur,
      frames.upid,
      frames.frame_id,
      'gc_activity' AS event_kind
    FROM frame_windows AS frames
    JOIN android_garbage_collection_events AS gc
      ON gc.upid = frames.upid
     AND gc.gc_ts < frames.ts + frames.dur
     AND gc.gc_ts + gc.gc_dur > frames.ts
    WHERE gc.gc_dur > 0
  ),
  all_overlap AS (
    SELECT * FROM binder_overlap
    UNION ALL
    SELECT * FROM lock_overlap
    UNION ALL
    SELECT * FROM gc_overlap
  ),
  merged_overlap AS (
    SELECT *
    FROM interval_merge_overlapping_partitioned!(
      (
        SELECT
          ts,
          dur,
          upid,
          frame_id,
          event_kind
        FROM all_overlap
        WHERE dur > 0
      ),
      (upid, frame_id, event_kind)
    )
  )
SELECT
  upid,
  frame_id,
  event_kind,
  ROUND(SUM(dur) / 1e6, 3) AS covered_ms
FROM merged_overlap
GROUP BY upid, frame_id, event_kind
ORDER BY upid, frame_id, covered_ms DESC;
```

三类覆盖时间不能相加为“总阻塞时间”，因为 Binder、锁和 GC 活动可能彼此重叠。同步 Binder 的客户端区间包含等待回复；异步事务的客户端区间只描述发送。monitor 锁竞争直接说明 UI 线程等锁。`gc_activity` 覆盖整个标准库 GC 事件，包含并发工作与等待，不能等同于 stop-the-world 暂停。

确定因果关系还要检查 `thread_state` 和事件层级。帧内出现 GC 活动，只能证明时间相关；主线程在同一时段是否停顿，需要查看主线程状态和 ART 暂停事件。合并后的表也不再保留原始事务或 GC id，追踪单个事件时应回查标准库源表。

## 与 Trace Processor 标准库配合

标准库封装了解析差异和常见区间关系。Android 17 中直接相关的模块包括：

- `linux.cpu.frequency`：把 `cpufreq` 计数器转成 `cpu_frequency_counters`。
- `counters.intervals`：提供计数器前向区间宏。
- `intervals.overlap`：统计、展平和合并重叠区间。
- `intervals.intersect`：对多个区间表求交，并保留输入 id。
- `slices.with_context`：提供带线程与进程信息的 `thread_slice` 等视图。
- `android.frames.timeline`、`android.binder`、`android.monitor_contention`、`android.garbage_collection`：提供 Android 平台语义表。

`sched.thread_executing_span_with_slice` 的 Android 17 源码展示了标准库内部做法：先使用展平后的 `slice`，确保同一 `utid` 的输入互斥，再用 `SPAN_LEFT_JOIN` 关联 `thread_state`。该模块导出的很多对象以 `_` 开头，属于内部实现细节，业务查询不应依赖这些名字。

选择工具时按输入形状判断：

- 两侧都是互斥时间段，且只关心交集切片：`SPAN_JOIN`。
- 一侧或两侧的未匹配区间也要保留：`SPAN_LEFT_JOIN` / `SPAN_OUTER_JOIN`。
- 输入含嵌套或需要保留多重事件身份：普通区间条件或 `intervals.intersect`。
- 只统计一类事件的总覆盖：先用 `interval_merge_overlapping_partitioned!` 合并。

## `SPAN_LEFT_JOIN` 与 `SPAN_OUTER_JOIN`

`SPAN_JOIN` 只输出两侧真实区间的交集。`SPAN_LEFT_JOIN` 会用影子时间段（`shadow span`）补足左侧未匹配的时间，`SPAN_OUTER_JOIN` 会补足两侧未匹配时间。结果中的另一侧业务列为空，可以区分“有覆盖”和“没有覆盖”。

下面的固定数据演示左连接如何保留左侧空档。

```sql
CREATE PERFETTO TABLE left_demo (
  ts TIMESTAMP,
  dur DURATION,
  part_id LONG,
  left_name STRING
) AS
WITH data(ts, dur, part_id, left_name) AS (
  VALUES
    (10, 20, 1, 'left-a')
)
SELECT * FROM data;

CREATE PERFETTO TABLE right_demo (
  ts TIMESTAMP,
  dur DURATION,
  part_id LONG,
  right_name STRING
) AS
WITH data(ts, dur, part_id, right_name) AS (
  VALUES
    (15, 5, 1, 'right-a')
)
SELECT * FROM data;

CREATE VIRTUAL TABLE left_demo_result
USING SPAN_LEFT_JOIN(
  left_demo PARTITIONED part_id,
  right_demo PARTITIONED part_id
);

SELECT
  ts,
  dur,
  part_id,
  left_name,
  right_name
FROM left_demo_result
ORDER BY ts;
```

结果会把左侧 `[10, 30)` 切成 `[10, 15)`、`[15, 20)`、`[20, 30)`；中间一段带有 `right_name`，两侧空档的该列为 `NULL`。这类输出适合计算“帧内没有 Binder 覆盖的时间”，前提是左表本身满足互斥约束。

分区表为空时有一个已记录的特殊行为：空分区表参加 `outer join`，或作为 `left join` 的右表时，即便另一侧非空，也可能不输出时间段。官方文档将其归因于分区影子区间的定义。依赖未匹配区间的自动化查询要加入空表测试，不能直接套用普通 SQL 外连接的直觉。

## 查询成本与索引策略

`SPAN_JOIN` 不构造完整笛卡尔积。Android 17 的 `CreateSqlQuery()` 会为子查询生成按分区和 `ts` 排序的读取，游标再按较早结束的一侧向前移动。总体成本仍由输入构造、排序和输出交集数量决定。

大 Trace 查询按以下顺序控制成本：

1. 按 `upid`、`utid`、`ucpu` 和明确时间窗过滤原始表。
2. 用 `CREATE PERFETTO TABLE` 物化会重复使用的窗口函数结果。
3. 只带入后续需要的列，避免把大字符串和完整 `args` 放进虚拟表。
4. 在每个分区检查重叠和非正 `dur`，防止错误输入扩大输出。
5. 用 `EXPLAIN QUERY PLAN` 检查普通筛选与关联，再决定是否创建索引。

Perfetto 原生表的 id 查询已有专门优化。需要为物化表加索引时使用 `CREATE PERFETTO INDEX`，并评估内存成本。索引可以帮助筛选和等值关联，但不能消除 `SPAN_JOIN` 为时间顺序读取所需的排序，也不能修复重叠输入。

## 在 CI 中复用复杂 Perfetto SQL

CI 查询要固定采集配置、Trace Processor 版本、输出列与比较方法。设备型号、构建、刷新率、温控前置条件和场景步骤也要随结果保存。缺少 `sched_switch` 或 `cpufreq` 时，查询应显式报告覆盖不足，不能把空值当成零。

在独立 Trace Processor 进程中执行 SQL 文件并把结果写到 CSV，可以让流水线同时保留查询脚本和原始输出。

```bash
trace_processor_shell \
  trace.perfetto-trace \
  --query-file frame_cpu_frequency.sql \
  > frame_cpu_frequency.csv
```

每次启动独立进程也能避免前一次查询创建的临时表污染当前运行。回归判断应比较同设备、同场景的基线分布，并在仓库中记录阈值来源；16.67 ms、某个固定 kHz 或任意百分比都不具备跨设备通用性。

## 排查清单

提交区间查询前逐项核对：

- 输入表是否都有有效 `ts` 与正数 `dur`。
- `dur = -1` 是否已裁到明确窗口。
- 分区列是否为整数，两侧是否表达同一种实体。
- 单机 `cpu` 与 Trace 内唯一 `ucpu` 是否用在正确场景。
- 同一输入、同一分区内是否存在嵌套或重叠。
- 计数器是否按 `track_id` 生成前向区间，首尾缺口是否被记录。
- 结果是否使用交集 `dur` 加权，是否误用原始事件时长。
- 不同事件类型的覆盖时间是否发生重叠，汇总时是否重复累计。
- FrameTimeline、Binder、GC、锁与调度事件是否在采集配置中启用。
- 空结果究竟表示“没有事件”，还是数据源、解析或关联条件缺失。

`SPAN_JOIN` 解决的是互斥区间流的时间交集。把输入约束、采集缺口和分区语义写进查询，结果才具备复查价值。

## 源码与文档依据

- [PerfettoSQL 入门：`SPAN_JOIN` 与窗口函数](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started)
- [PerfettoSQL 语法与索引](https://perfetto.dev/docs/analysis/perfetto-sql-syntax)
- [Perfetto SQL 标准库索引](https://perfetto.dev/docs/analysis/stdlib-docs)
- [CPU 频率采集与已知边界](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Android 17 `span_join_operator.cc`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/intrinsics/operators/span_join_operator.cc)
- [Android 17 `span_join_operator.h`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/intrinsics/operators/span_join_operator.h)
- [Android 17 `linux.cpu.frequency` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/frequency.sql)
- [Android 17 `intervals.overlap` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/intervals/overlap.sql)
- [Android 17 `android.frames.timeline` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)
- [Android 17 `android.binder` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)
- [Android 17 `android.garbage_collection` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/garbage_collection.sql)
- [Android 17 kernel 6.18 `sched` tracepoint 定义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
