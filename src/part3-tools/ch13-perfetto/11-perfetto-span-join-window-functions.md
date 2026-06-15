---
title: "Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数"
chapter: "13.11"
section: "13.11"
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
related_chapters: ["13.10", "13.6", "14.10"]
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
task2b_state: fixed
task2b_result: fixed
last_task2b_main_at: 2026-06-16T02:50:00+08:00
---

# 13.11 Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数

Perfetto SQL 里最容易写错的一类查询，是把两个时间区间表按重叠关系关联起来。帧在一段时间内运行，线程调度在另一组时间段内发生，CPU 频率又是一组离散 counter；如果只用普通 `JOIN` 加 `ts` 条件，很快会遇到重复行、漏算边界和全表扫描。

`SPAN_JOIN` 是 Trace Processor 提供的 operator table，专门计算两个 span 表的时间交集。本节把它和窗口函数放在一起讲：窗口函数负责把离散事件整理成 `ts + dur` 的 span，`SPAN_JOIN` 负责把两组 span 按时间切成可统计的小段。

<!-- outline-start -->

- **SPAN_JOIN 处理的是区间交集**：span 的定义，与普通 JOIN 的区别，`SPAN_JOIN` 的语法与语义
- **用窗口函数把 counter 变成 span**：`LEAD` 补 duration，`counter → span` 的通用模板
- **PARTITIONED 的约束比语法更要紧**：分区键、同分区不重叠、违反约束的后果
- **案例：把每帧运行时间拆到 CPU 频率上**：frame × CPU 频率的完整查询，帧边界裁剪
- **帧 × Binder / 锁 / GC 的交叉分析**：Binder 重叠、GC pause window 合并与帧关联
- **与 Trace Processor 标准库配合**：标准库模块化视图，减少手写 JOIN
- **SPAN_LEFT_JOIN 与 SPAN_OUTER_JOIN**：左连接与外连接的适用场景
- **查询成本与索引策略**：大 trace 性能优化
- **在 CI 中复用复杂 Perfetto SQL**：CI 集成模式
- **排查清单**：常见错误与自查项

<!-- outline-end -->

## SPAN_JOIN 处理的是区间交集

Perfetto 文档把 span 定义为包含 `ts` 和 `dur` 两列的行。`ts` 是起点，`dur` 是持续时间，`slice`、`sched`、`thread_state` 这类表天然就是 span；`counter` 只有采样点，需要先补出每个值的有效区间。

[已验证: Perfetto Trace Processor docs, perfetto.dev/docs/analysis/trace-processor]

普通 SQL 更擅长等值关联，比如 `slice.track_id = thread_track.id`。时间重叠关联属于区间关系，常见写法是：

```sql
-- 用普通 JOIN 表达区间重叠，适合小表验证，不适合大 Trace 长期复用
SELECT
  a.ts AS a_ts,
  a.dur AS a_dur,
  b.ts AS b_ts,
  b.dur AS b_dur,
  MAX(a.ts, b.ts) AS overlap_ts,
  MIN(a.ts + a.dur, b.ts + b.dur) - MAX(a.ts, b.ts) AS overlap_dur
FROM table_a AS a
JOIN table_b AS b
  ON a.ts < b.ts + b.dur
 AND b.ts < a.ts + a.dur;
```

这段 SQL 的判断条件没有错，但工程上很容易失控：两张表没有按目标进程、线程、CPU、时间窗收窄时，候选组合会迅速膨胀；`overlap_dur` 还要额外过滤 `> 0`；如果某一边同一分区内存在重叠 span，聚合结果会重复计入。

`SPAN_JOIN` 把这类查询换成虚拟表：

```sql
-- table_a 与 table_b 都必须包含 ts 和 dur，两边按同一个整数分区列对齐
CREATE VIRTUAL TABLE joined
USING SPAN_JOIN(table_a PARTITIONED part_id, table_b PARTITIONED part_id);

SELECT ts, dur, part_id
FROM joined
WHERE dur > 0;
```

输出表里的 `ts` 是两边起点的较大值，`dur` 是两边终点的较小值减去这个起点。源码里的 `Column()` 分支也按这个公式返回结果：`max(t1.ts, t2.ts)` 与 `min(t1.raw_ts_end(), t2.raw_ts_end()) - max_start`。

[已验证: AOSP external/perfetto, span_join_operator.cc]

适合用 `SPAN_JOIN` 的场景有三个特征：

- **两边都是时间段**：例如帧区间、调度区间、线程状态区间、锁等待区间、GC pause 区间。
- **结果要按重叠时长加权**：例如一帧内 2ms 在 710MHz、4ms 在 1804MHz，不能只取某个采样点。
- **需要复用 SQL 模板**：例如同一套查询用于多条 trace、CI 回归或问题库归因。

## 用窗口函数把 counter 变成 span

CPU 频率、内存、温度、功耗估算等数据通常来自 `counter` 表。counter 记录“某个时间点值发生变化”，缺少“这个值持续了多久”。要把它和帧、线程运行段关联，先要用窗口函数补出 `dur`。

`LEAD()` 的用途是拿到同一 track 内下一条 counter 的时间戳：

```sql
-- 把 cpufreq counter 转成带 dur 的 span 视图
CREATE VIEW cpu_freq_span AS
SELECT
  counter.ts,
  LEAD(counter.ts) OVER (
    PARTITION BY counter.track_id
    ORDER BY counter.ts
  ) - counter.ts AS dur,
  cpu_counter_track.cpu,
  CAST(counter.value AS INT) AS freq_khz
FROM counter
JOIN cpu_counter_track
  ON counter.track_id = cpu_counter_track.id
WHERE cpu_counter_track.name = 'cpufreq';
```

`PARTITION BY counter.track_id` 不能省。CPU 0 和 CPU 4 的频率 track 各自独立，如果只按全局 `ts` 排序，某个 CPU 的当前值会被另一个 CPU 的下一条 counter 截断，`dur` 会变成跨 track 的假区间。

[已验证: Perfetto getting started 示例与 Trace Processor docs]

末尾 counter 没有下一条记录，`LEAD()` 会返回 `NULL`。处理方式取决于查询目标：

```sql
-- 用 trace_end() 给末尾段补边界，便于做完整窗口统计
CREATE PERFETTO TABLE cpu_freq_span_bounded AS
WITH raw AS (
  SELECT
    counter.ts,
    LEAD(counter.ts) OVER (
      PARTITION BY counter.track_id
      ORDER BY counter.ts
    ) AS next_ts,
    cpu_counter_track.cpu,
    CAST(counter.value AS INT) AS freq_khz
  FROM counter
  JOIN cpu_counter_track
    ON counter.track_id = cpu_counter_track.id
  WHERE cpu_counter_track.name = 'cpufreq'
)
SELECT
  ts,
  COALESCE(next_ts, trace_end()) - ts AS dur,
  cpu,
  freq_khz
FROM raw
WHERE COALESCE(next_ts, trace_end()) > ts;
```

如果分析只关心某个短时间窗，也可以把 `trace_end()` 换成窗口结束时间。不要让 `NULL dur` 直接进入 `SPAN_JOIN`；结果可能报错，也可能让后续聚合悄悄少一段。

## PARTITIONED 的约束比语法更要紧

`PARTITIONED` 告诉 `SPAN_JOIN`：只在同一个分区内计算重叠。调度与频率要按 `cpu` 分区，线程状态与 slice 要按 `utid` 分区，帧与进程级事件可以用 `upid` 或自定义整数键。

Perfetto 文档明确写了两个限制：分区列必须是整数；同一表、同一分区内的 span 不能重叠。源码里的 `Query::CursorNext()` 会检查分区列类型，非整数会返回 `SPAN_JOIN: partition is not an INT column`。

[已验证: Perfetto Trace Processor docs + AOSP external/perfetto span_join_operator.cc]

字符串分区需要先转成整数。官方文档提到可用 `HASH()` 处理字符串列：

```sql
-- 把字符串事件名转成整数分区，再参与 SPAN_JOIN
CREATE PERFETTO TABLE named_slice_span AS
SELECT
  ts,
  dur,
  HASH(name) AS name_hash,
  name,
  track_id
FROM slice
WHERE dur > 0;
```

`HASH(name)` 解决的是类型限制，不解决语义问题。只有当两边的字符串含义完全一致时，hash 后的分区才有意义；如果一边是线程名，另一边是 slice 名，转成整数也不能关联。

同一分区内不能重叠，是比类型更容易踩的坑。`sched` 按 `cpu` 分区天然不重叠，因为一个 CPU 同一时刻只能运行一个线程；`thread_state` 按 `utid` 分区也应当连续互斥。普通 `slice` 就不同了，同一线程 track 上可能有嵌套 slice，同一时间有父子多层调用。直接拿 `slice PARTITIONED utid` 去 join，往往会把父子层级一起算进去。

处理重叠数据有三种常用方式：

- **只取目标层级**：例如 `slice.depth = 0` 或取某个具体 `name`，让同一 track 内保留互斥区间。
- **先 flatten**：使用标准库里的 flattened slice 视图，把嵌套调用整理成互斥片段后再 join。
- **改用 interval 标准库**：需要保留两边重叠层级时，使用 `intervals.overlap` / `intervals.intersect` 这类模块比强塞进 `SPAN_JOIN` 更稳。

Perfetto 标准库的 `thread_executing_span_with_slice.sql` 就展示了这条思路：先构造受限的 `thread_state` 和 flattened slice 视图，再用 `SPAN_LEFT_JOIN` 按 `utid` 关联。

[已验证: AOSP external/perfetto, perfetto_sql/stdlib/sched/thread_executing_span_with_slice.sql]

## 案例：把每帧运行时间拆到 CPU 频率上

帧耗时高时，单看 `Choreographer#doFrame` 的 `dur` 只能说明主线程这一帧忙了多久。要判断“忙的时候 CPU 频率是否足够”，需要把帧区间、线程运行区间和 CPU 频率区间放到同一条时间轴上。

这个例子用主线程的 `Choreographer#doFrame` slice 作为帧窗口，用 `sched` 找出主线程在各 CPU 上运行的片段，再用 `SPAN_JOIN` 把运行片段与 cpufreq span 关联起来。

```sql
-- 参数：把 com.example.app 换成目标进程名
CREATE PERFETTO TABLE target_main_thread AS
SELECT
  thread.utid,
  process.upid,
  process.name AS process_name
FROM thread
JOIN process USING (upid)
WHERE process.name = 'com.example.app'
  AND (thread.is_main_thread = 1 OR thread.tid = process.pid)
LIMIT 1;

CREATE PERFETTO TABLE frame_span AS
SELECT
  ROW_NUMBER() OVER (ORDER BY slice.ts) AS frame_id,
  slice.ts,
  slice.dur,
  thread_track.utid
FROM slice
JOIN thread_track
  ON slice.track_id = thread_track.id
JOIN target_main_thread
  ON target_main_thread.utid = thread_track.utid
WHERE slice.name = 'Choreographer#doFrame'
  AND slice.dur > 0;

CREATE PERFETTO TABLE main_sched_span AS
SELECT
  sched.ts,
  sched.dur,
  sched.cpu,
  sched.utid
FROM sched
JOIN target_main_thread
  ON target_main_thread.utid = sched.utid
WHERE sched.dur > 0;

CREATE PERFETTO TABLE cpu_freq_span AS
WITH raw AS (
  SELECT
    counter.ts,
    LEAD(counter.ts) OVER (
      PARTITION BY counter.track_id
      ORDER BY counter.ts
    ) AS next_ts,
    cpu_counter_track.cpu,
    CAST(counter.value AS INT) AS freq_khz
  FROM counter
  JOIN cpu_counter_track
    ON counter.track_id = cpu_counter_track.id
  WHERE cpu_counter_track.name = 'cpufreq'
)
SELECT
  ts,
  COALESCE(next_ts, trace_end()) - ts AS dur,
  cpu,
  freq_khz
FROM raw
WHERE COALESCE(next_ts, trace_end()) > ts;

CREATE VIRTUAL TABLE sched_with_freq
USING SPAN_JOIN(main_sched_span PARTITIONED cpu, cpu_freq_span PARTITIONED cpu);
```

`sched_with_freq` 的每一行都表示：主线程在某个 CPU 上运行的一小段时间，以及这段时间内该 CPU 的频率。再把它裁进帧窗口：

```sql
-- 按帧统计主线程实际运行时间、加权平均频率和低频运行占比
-- 关键：用 overlap_dur 裁剪到帧边界，避免跨帧 sched 段污染指标
SELECT
  frame.frame_id,
  ROUND(frame.dur / 1e6, 3) AS frame_wall_ms,
  ROUND(SUM(
    MIN(joined.ts + joined.dur, frame.ts + frame.dur)
    - MAX(joined.ts, frame.ts)
  ) / 1e6, 3) AS main_cpu_ms,
  ROUND(
    SUM(
      (MIN(joined.ts + joined.dur, frame.ts + frame.dur) - MAX(joined.ts, frame.ts))
      * joined.freq_khz
    ) * 1.0
    / SUM(
      MIN(joined.ts + joined.dur, frame.ts + frame.dur)
      - MAX(joined.ts, frame.ts)
    )
  ) AS avg_freq_khz,
  ROUND(
    SUM(CASE
      WHEN joined.freq_khz < 1000000
      THEN MIN(joined.ts + joined.dur, frame.ts + frame.dur) - MAX(joined.ts, frame.ts)
      ELSE 0
    END) * 100.0
    / SUM(
      MIN(joined.ts + joined.dur, frame.ts + frame.dur)
      - MAX(joined.ts, frame.ts)
    ),
    2
  ) AS low_freq_pct
FROM frame_span AS frame
JOIN sched_with_freq AS joined
  ON joined.utid = frame.utid
 AND joined.ts < frame.ts + frame.dur
 AND frame.ts < joined.ts + joined.dur
WHERE joined.dur > 0
GROUP BY frame.frame_id
ORDER BY frame.frame_id;
```

这里用普通 `JOIN` 做重叠判断，但所有度量（运行时间、加权频率、低频占比）都基于 `overlap_dur = MIN(joined.end, frame.end) - MAX(joined.start, frame.start)` 裁剪到帧边界。如果某个 `sched` 段跨越帧边界，只有落在帧内的部分被计入，不会把帧外时间污染进该帧指标。如果帧量很大，也可以把 `frame` 与 `sched_with_freq` 做一个按 `utid` 的 `SPAN_JOIN`，`SPAN_JOIN` 内部会自动做边界裁剪。

这个统计能回答两个问题：帧的墙上时间里主线程占用 CPU 跑了多久；主线程运行期间 CPU 频率处在哪个区间。如果 `frame_wall_ms` 很高但 `main_cpu_ms` 很低，瓶颈更可能是等锁、等 Binder、等 I/O 或调度排队，详见 §13.6。若 `main_cpu_ms` 高且 `avg_freq_khz` 长期偏低，需要继续看温控、后台功耗限制、线程优先级和厂商调度策略，eBPF 侧的频率驻留统计可作为补充，详见 §14.10。

上述查询已经用 `MIN(joined.end, frame.end) - MAX(joined.start, frame.start)` 裁剪重叠时长，frame 边界是安全的。如果改为 `SPAN_JOIN(frame_span PARTITIONED utid, sched_with_freq PARTITIONED utid)`，`SPAN_JOIN` 内部会按交集自动切段，聚合 `joined.dur` 也不会越界——这是等价写法，选择哪种取决于查询规模和调试习惯：普通 JOIN + overlap 公式适合快速验证少量帧；`SPAN_JOIN` 适合大 trace 时把边界裁剪交给算子，减少 SQL 里的重复公式。

## 帧 × Binder / 锁 / GC 的交叉分析

`SPAN_JOIN` 的价值不只在 CPU 频率。只要把事件整理成 `ts + dur + 分区键`，就能把帧窗口与 Binder、锁竞争、GC pause 关联起来。

Binder 分析常用主线程上的 Binder slice 或标准库视图。查询目标应落到 Binder 与帧重叠了多久，而不只判断“这一帧里有没有 Binder”：

```sql
-- 主线程帧窗口与 Binder slice 的重叠时长
CREATE PERFETTO TABLE main_binder_span AS
SELECT
  slice.ts,
  slice.dur,
  thread_track.utid,
  slice.name
FROM slice
JOIN thread_track
  ON slice.track_id = thread_track.id
JOIN target_main_thread
  ON target_main_thread.utid = thread_track.utid
WHERE slice.dur > 0
  AND slice.name GLOB '*binder*';

CREATE VIRTUAL TABLE frame_binder_overlap
USING SPAN_JOIN(frame_span PARTITIONED utid, main_binder_span PARTITIONED utid);

SELECT
  frame_id,
  ROUND(SUM(dur) / 1e6, 3) AS binder_ms,
  COUNT(*) AS binder_segments
FROM frame_binder_overlap
WHERE dur > 0
GROUP BY frame_id
ORDER BY binder_ms DESC
LIMIT 20;
```

如果某些帧的 `binder_ms` 高，不要直接下结论说 Binder 慢。Binder slice 可能包含服务端处理、客户端等待、线程调度和锁等待等多种成本，下一步应回到 Binder 章节或服务端线程 trace 做调用关系确认。

锁竞争与 GC 也可以用同样的模型。锁竞争通常来自 `monitor contention` 或应用自定义 trace；GC pause 在 ART 相关 slice 中体现。写查询时要把事件名收窄到具体来源，避免把无关 slice 一并统计进去。

```sql
-- Step 1: 收集 GC 事件，先按 ts 合并为同线程内互不重叠的 pause window
-- 目的：避免不同 GC 阶段/嵌套 GC 的重叠 slice 违反 SPAN_JOIN 同分区不重叠约束
CREATE PERFETTO TABLE gc_pause_window AS
WITH raw_gc AS (
  SELECT
    thread_track.utid,
    slice.ts,
    slice.ts + slice.dur AS end_ts,
    slice.name
  FROM slice
  JOIN thread_track
    ON slice.track_id = thread_track.id
  WHERE slice.dur > 0
    AND (slice.name GLOB '*GC*' OR slice.name GLOB '*Garbage*')
),
merged AS (
  SELECT
    utid,
    ts,
    end_ts,
    name,
    -- 用运行最大结束时间判定合并组起点。
    -- LAG(end_ts) 只比较前一行的 end，遇到嵌套区间（如 A[1,10]、B[2,3]、C[9,12]）时
    -- C 只与 B.end=3 比较会被误判为新组，产出两个重叠窗口违反 SPAN_JOIN 同分区不重叠约束。
    -- MAX(end_ts) OVER 取前序所有行的最大结束时间，嵌套区间可正确合并到同一组。
    CASE WHEN ts <= MAX(end_ts) OVER (
      PARTITION BY utid
      ORDER BY ts, end_ts
      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    )
      THEN 0 ELSE 1 END AS is_start
  FROM raw_gc
),
groups AS (
  SELECT
    *,
    SUM(is_start) OVER (PARTITION BY utid ORDER BY ts) AS grp
  FROM merged
)
SELECT
  utid,
  MIN(ts) AS ts,
  MAX(end_ts) - MIN(ts) AS dur
FROM groups
GROUP BY utid, grp;

-- Step 2: 与主线程帧窗口做 SPAN_JOIN（数据已保证同 utid 不重叠）
CREATE VIRTUAL TABLE frame_gc_overlap
USING SPAN_JOIN(frame_span PARTITIONED utid, gc_pause_window PARTITIONED utid);

-- Step 3: 按帧聚合 GC 重叠时长
SELECT
  frame_id,
  ROUND(SUM(dur) / 1e6, 3) AS gc_overlap_ms
FROM frame_gc_overlap
WHERE dur > 0
GROUP BY frame_id
ORDER BY gc_overlap_ms DESC
LIMIT 20;
```

这段 SQL 先把 GC 事件按线程内时间顺序合并为互不重叠的 pause window，再与帧窗口做 `SPAN_JOIN`。合并步骤避免了不同 GC 阶段（如并发标记、STW pause）的嵌套/重叠 slice 违反 `SPAN_JOIN` 的同分区不重叠约束。它回答的是“GC 活动与主线程帧窗口在时间上重叠了多久”，不代表 GC 一定阻塞了主线程。若要判断主线程是否被 STW pause 阻塞，需要继续看 `thread_state`、ART slice 和应用线程是否同时出现停顿。

## 与 Trace Processor 标准库配合

复杂查询不应从 raw 表一路手写到底。Perfetto 标准库已经把很多稳定关系封装成模块，比如 thread / process 上下文、sched 派生视图、Frame Timeline、锁竞争和 interval 工具。直接用标准库能少写 JOIN，也能减少字段名随版本变化带来的维护成本。

常用选择是：

- **线程与进程上下文**：`thread_slice` / `process_slice` 这类视图把 `slice`、`thread_track`、`thread`、`process` 的关联封装好，适合按线程或进程筛选 slice。
- **调度视图**：`sched`、`thread_state` 和 sched 标准库视图负责描述线程什么时候 Running、Runnable、Sleeping，适合接到帧窗口或锁等待窗口后做 off-CPU 分析。
- **interval 模块**：当两边可能有嵌套层级、需要保留多重重叠，`intervals.overlap` / `intervals.intersect` 比 `SPAN_JOIN` 更适合。
- **宏与函数**：固定问题可以封装成 `CREATE PERFETTO MACRO`，把目标进程、时间窗、阈值作为参数传入。

[已验证: Perfetto stdlib docs 搜索结果 + AOSP external/perfetto stdlib 源码]

临时 SQL 变成团队可复用工具时，建议按这个顺序整理：

```sql
-- 用宏封装“目标线程在每帧内的 CPU 运行时间”这类固定问题
CREATE PERFETTO MACRO _target_main_thread(_process_name Expr)
RETURNS TableOrSubQuery AS
(
  SELECT thread.utid, process.upid, process.name AS process_name
  FROM thread
  JOIN process USING (upid)
  WHERE process.name = $_process_name
    AND (thread.is_main_thread = 1 OR thread.tid = process.pid)
  LIMIT 1
);
```

宏里只放稳定筛选逻辑，`CREATE VIRTUAL TABLE ... USING SPAN_JOIN` 这类中间结果仍然建议在外层显式创建。这样调试时可以逐张表 `SELECT * LIMIT 20`，避免把所有逻辑折叠成一条难排查的查询。

## SPAN_LEFT_JOIN 与 SPAN_OUTER_JOIN

`SPAN_JOIN` 只输出两边有交集的区间。`SPAN_LEFT_JOIN` 和 `SPAN_OUTER_JOIN` 用来保留缺失的一边，行为接近 SQL 的 left join / outer join，但因为时间轴和 shadow slice 的存在，边界比普通等值连接更复杂。

```sql
-- 左表保留：即使右表没有匹配区间，左表时间段仍可出现在结果里
CREATE VIRTUAL TABLE left_result
USING SPAN_LEFT_JOIN(left_span PARTITIONED part_id, right_span PARTITIONED part_id);

-- 两边都不分区的 outer span join
CREATE VIRTUAL TABLE outer_result
USING SPAN_OUTER_JOIN(left_span, right_span);
```

Perfetto 文档提到一个特殊情况：参与 outer join 的分区表为空，或者 left join 右侧的分区表为空时，即使另一边非空，也可能没有 slice 输出。这个行为来自 span join 对分区 shadow 的处理，不能完全按普通 SQL 外连接直觉理解。

[已验证: Perfetto Trace Processor docs]

实战里优先用 `SPAN_JOIN`。只有在问题明确需要“没有匹配也要保留时间段”时，再用 `SPAN_LEFT_JOIN`。例如统计一帧内没有任何 Binder 的区间，或者把线程状态与 slice 关联后仍保留纯线程状态时间段。

## 查询成本与索引策略

`SPAN_JOIN` 在源码里没有把两表做笛卡尔积再过滤。`FindOverlappingSpan()` 会让两个 cursor 按分区和时间推进，`FindEarliestFinishQuery()` 按分区、结束时间、是否真实 slice 的顺序选择下一步推进哪一侧。每个子查询还会按 `partition, ts` 或 `ts` 排序。

[已验证: AOSP external/perfetto, span_join_operator.cc]

这不代表它可以直接吃全量 trace。大 trace 上，成本通常花在三处：构造子表、排序、输出交集行。优化方向也对应三处：

- **先收窄时间窗和目标对象**：目标进程、目标线程、目标 CPU、目标帧范围先过滤，再建 span 表。
- **物化中间表**：多次复用的子查询用 `CREATE PERFETTO TABLE` 固化，避免窗口函数反复计算。
- **控制输出粒度**：只选择需要的列，避免把大文本字段、args 展开结果带进虚拟表。

`CREATE INDEX` 对普通 SQLite 临时表有帮助，但对 `SPAN_JOIN` 的输入，排序和物化更影响查询成本。源码里的 `CreateSqlQuery()` 会生成按分区与 `ts` 排序的子查询；输入表已经足够小，比事后补索引更有效。

## 在 CI 中复用复杂 Perfetto SQL

Perfetto SQL 适合进入 CI，但不要把 UI 里临时调试出来的一长串 SQL 直接放进流水线。CI 查询需要三个特征：输入稳定、输出字段稳定、阈值能解释。

一个可维护的流程是：

1. 抓取固定场景 trace，例如冷启动、列表滑动、页面切换。
2. 用 SQL 输出少量指标，例如 P90 帧耗时、主线程 CPU ms、低频运行占比、Binder 重叠 ms。
3. 输出 CSV / JSON 后由 CI 判断阈值，阈值旁边记录设备型号、刷新率、温控条件和 trace 配置。

`trace_processor_shell` 可以在命令行执行 SQL 文件。SQL 文件里保留参数占位，通过外层脚本替换进程名、时间窗和阈值：

```bash
trace_processor_shell --query-file frame_cpu_freq.sql trace.perfetto-trace > frame_cpu_freq.csv
```

CI 里的阈值不要只写“超过 16.67ms 就失败”。120Hz、90Hz、60Hz 的预算不同，温控状态也会影响频率。更稳的做法是比较同设备、同场景、同版本基线：例如 P90 帧耗时回退超过 15%，或低频运行占比异常升高超过 20 个百分点。

## 排查清单

写 `SPAN_JOIN` 查询时，按下面几项检查，能避开大部分假结果：

- **输入表是否有 `ts` 和 `dur`**：counter 必须先用窗口函数补 `dur`，末尾段要给明确边界。
- **分区键是否是整数且语义一致**：`cpu` 对 `cpu`，`utid` 对 `utid`，不要把不同含义的整数列强行关联。
- **同分区内是否重叠**：普通 slice 有嵌套层级，进入 `SPAN_JOIN` 前要筛层级或 flatten。
- **时间单位是否统一**：Perfetto 的时间单位是 ns，输出给人看时再除以 `1e6`。
- **输出是否按重叠时长加权**：频率、温度、状态占比都要乘 `dur` 后再聚合。
- **边界是否被裁剪**：窗口开始和结束处要用 `MAX(start)` / `MIN(end)` 或通过 `SPAN_JOIN` 自动切段。

`SPAN_JOIN` 是 Perfetto 对时间区间分析的可复用算子。帧、调度、频率、Binder、锁、GC 都整理成同一种数据形状后，性能分析会从“看一条长 trace”变成“验证几个可重复的时间关系”。
