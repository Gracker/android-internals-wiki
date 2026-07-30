---
title: "Perfetto SQL 查询手册与性能分析实战查询库"
chapter: "13.22"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['perfetto', 'sql', 'trace-analysis', 'performance-query']
related_chapters: ['13.10', '13.11', '13.14', '13.20', '13.21', '13.27', '14.32']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "章节深挖"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "finalized"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1 Perfetto stdlib + Perfetto v57.2 host toolchain"
last_draft_polish_at: "2026-07-30T19:35:11+08:00"
last_draft_polish_run_id: "20260730-193511-draft-polish-61cb8abd"
reviewed_date: "2026-07-30"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-30T20:11:15+08:00"
last_review_finalize_run_id: "20260730-201115-18996eb0"
confidence: "medium-high"
status: finalized
sources:
  - "AOSP android-17.0.0_r1 Perfetto stdlib (android.frames.timeline, android.cujs.sysui_cujs, sched.latency, android.binder, android.memory.dmabuf)"
  - "Perfetto v57.2 host Trace Processor release"
  - "PerfettoSQL official documentation (perfetto.dev)"
  - "android17-6.18-2026-06_r6 kernel baseline"
---

# 13.22 Perfetto SQL 查询手册与性能分析实战查询库

<!-- outline-start -->
## 要点

### 🔹 Perfetto trace_processor SQL 架构与表结构
### 🔹 帧性能 SQL：FrameTimeline / Jank CUJ 查询模板
### 🔹 CPU 调度 SQL：sched/slice 表与线程状态分析
### 🔹 内存 SQL：heap_profile / counter / dmabuf 查询
### 🔹 Binder IPC SQL：binder_transaction 与延迟分析
### 🔹 Perfetto v54 Data Explorer 与 SQL 标准库
### 🔹 trace_processor Python API 与自动化分析
### 🔹 跨 trace 聚合查询与 CI/CD 集成

## 扩展

### 🔸 自定义 SQL 函数与数学运算
### 🔸 Perfetto Metrics extension 机制
### 🔸 Android 17 Perfetto v57 AI 技能与 SQL 结合

<!-- outline-end -->

本节以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码锚点，以 Perfetto v57.2 的宿主机 Trace Processor 复核查询。Android 17 固定源码中的 Perfetto 属于 v54 时代快照，并带有后续 AOSP 改动；设备负责采集，宿主机工具负责解析和查询，两条版本线应分别记录。

§13.10 已覆盖 PerfettoSQL 基础和常见查询，§13.11 介绍区间连接与窗口函数，§13.14 讨论 Data Explorer 和 Jank CUJ。本节把这些能力整理成一套可以进入评审、批处理和 CI 的查询规范。重点放在数据门控、稳定表、单位、空结果和版本兼容，不重复罗列 UI 操作。

## 1. Trace Processor 把 trace 变成什么

Trace Processor 读取 Perfetto protobuf、ftrace、Chrome JSON、Simpleperf 等格式，经过事件排序和各格式 importer，把数据写入内部列式存储，再通过 PerfettoSQL 暴露给查询端。查询层可以分成三层：

| 层级 | 示例 | 稳定性与用途 |
|---|---|---|
| Prelude / 内置表 | `slice`、`sched`、`thread_state`、`counter`、`process`、`thread` | 打开 trace 后直接可查，适合数据探测和底层验证 |
| PerfettoSQL 标准库 | `android_frames`、`android_binder_txns`、`android_memory_cumulative_dmabuf` | 用 `INCLUDE PERFETTO MODULE` 加载，封装领域关联逻辑 |
| 项目查询与摘要 | 自定义函数、SQL package、Trace Summary、CI 阈值 | 由团队维护，要固定输入、版本、单位和输出 schema |

PerfettoSQL 以 SQLite 语法为基础，并增加 `INCLUDE PERFETTO MODULE`、`CREATE PERFETTO FUNCTION`、区间表、图算法等能力。它不是设备上的 SQLite 数据库：`upid`、`utid` 是 Trace Processor 为一次 trace 分配的身份键；Linux `pid`、`tid` 可能在长 trace 中复用，关联时优先使用前两者。

时间戳和时长统一以纳秒保存。区间按 `[ts, ts + dur)` 理解；`dur = -1` 表示事件在 trace 结束前仍未闭合，参与聚合前要单独处理。`slice.dur`、`sched.dur`、FrameTimeline `dur` 的语义各不相同，不能只因列名相同就相加。

## 2. 每份 trace 都先过数据门控

查询返回 0 行可能表示“现象没有发生”，也可能表示数据源没采、环形缓冲区覆盖、解析失败、进程名没匹配或分析器版本不支持。性能结论前应检查 trace 覆盖和 importer 统计。

下面的查询用于确认关键表是否有数据：

```sql
SELECT
  (trace_end() - trace_start()) / 1e9 AS trace_duration_s,
  (SELECT COUNT(*) FROM sched) AS sched_rows,
  (SELECT COUNT(*) FROM thread_state) AS thread_state_rows,
  (SELECT COUNT(*) FROM actual_frame_timeline_slice) AS frame_timeline_rows,
  (SELECT COUNT(*) FROM heap_profile_allocation) AS heap_profile_rows,
  (SELECT COUNT(*) FROM counter) AS counter_rows,
  (
    SELECT COUNT(*)
    FROM slice
    WHERE name GLOB 'binder*'
  ) AS binder_slice_rows;
```

这行结果是采集覆盖概览，不能当作各领域数据的完整性证明。例如 `binder_slice_rows > 0` 只说明存在名称匹配的 slice；Binder 事务能否配对，还要加载 `android.binder` 并检查结果。

下面的查询读取解析阶段报告的 data loss 与 error：

```sql
SELECT
  name,
  severity,
  source,
  value,
  description
FROM stats
WHERE severity IN ('data_loss', 'error')
  AND value > 0
ORDER BY severity, value DESC;
```

`stats` 中有 data loss 时，应把受影响的数据源写进报告，不能用剩余行数估算被覆盖的事件。

表结构随分析端版本演进。复制旧查询前，可以用下面的 schema 探测确认列名：

```sql
SELECT
  name AS column_name,
  type AS column_type
FROM pragma_table_info('actual_frame_timeline_slice')
ORDER BY cid;
```

`pragma_table_info()` 对不存在的表返回空集，适合做 feature detection。自动化脚本应把“表不存在”和“表存在但无行”分成两个状态。

## 3. 帧性能：从完整帧集合开始

### 3.1 `android_frames` 适合做覆盖与分布

Android 17 固定源码已经包含 `android.frames.timeline`。该模块把 `Choreographer#doFrame`、`DrawFrame`、Expected FrameTimeline 与 Actual FrameTimeline 对齐为 `android_frames`，并保留每帧匹配到的记录数量。

> 源码参照: `android.frames.timeline` 标准库 — `android-17.0.0_r1` `src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql`。该模块由 Perfetto stdlib 维护，表/列 schema 随分析端版本演进，查询前应用 `pragma_table_info()` 确认。

下面的查询统计目标进程帧时长分位数，同时检查缺少 Actual/Expected 记录的帧：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  process_name,
  COUNT(*) AS frame_count,
  ROUND(PERCENTILE(dur / 1e6, 50), 3) AS p50_ms,
  ROUND(PERCENTILE(dur / 1e6, 90), 3) AS p90_ms,
  ROUND(PERCENTILE(dur / 1e6, 95), 3) AS p95_ms,
  ROUND(PERCENTILE(dur / 1e6, 99), 3) AS p99_ms,
  SUM(
    CASE WHEN actual_frame_timeline_count = 0 THEN 1 ELSE 0 END
  ) AS missing_actual_frames,
  SUM(
    CASE WHEN expected_frame_timeline_count = 0 THEN 1 ELSE 0 END
  ) AS missing_expected_frames
FROM android_frames
WHERE process_name = 'com.example.app'
  AND dur > 0
GROUP BY process_name;
```

`android_frames.dur` 优先取匹配的 Actual FrameTimeline 时长；缺少 Actual 时，标准库会退回到 `doFrame` 起点与末个 `DrawFrame` 终点之间的区间。分位数混入 fallback 帧时，应同时报告两列 `missing_*`。固定 16.67 ms 阈值只适用于 60 Hz 的简化判断；可变刷新率场景应结合 Expected FrameTimeline、VSYNC period 和平台 jank 分类。

逐帧归责、`surface_frame_token` 与 `display_frame_token` 对齐见 §13.20。不要用 `track_id` 充当帧身份。

### 3.2 Jank CUJ 只覆盖有 CUJ marker 的场景

Android 17 的 `android.cujs.sysui_cujs` 模块面向 Framework `InteractionJankMonitor` 产生的 Jank CUJ marker，常见数据来自 SystemUI 和系统组件。普通第三方应用没有 marker 时，该表为空。

> 源码参照: `android.cujs.sysui_cujs` 标准库 — `android-17.0.0_r1` `src/trace_processor/perfetto_sql/stdlib/android/cujs/sysui_cujs.sql`。CUJ marker 由 `InteractionJankMonitor`（frameworks/base）写入 trace，该模块负责解析和对齐。

下面的查询用于比较已完成 CUJ 的墙钟时长分布：

```sql
INCLUDE PERFETTO MODULE android.cujs.sysui_cujs;

SELECT
  process_name,
  cuj_name,
  COUNT(*) AS occurrence_count,
  ROUND(AVG(dur) / 1e6, 3) AS avg_ms,
  ROUND(PERCENTILE(dur / 1e6, 95), 3) AS p95_ms,
  ROUND(MAX(dur) / 1e6, 3) AS max_ms
FROM android_sysui_jank_cujs
WHERE state = 'completed'
  AND dur > 0
GROUP BY process_name, cuj_name
ORDER BY p95_ms DESC;
```

CUJ 时长和 jank 帧数属于不同指标。v54 加入的 relevant-thread 与 counter-based weighted jank 逻辑用于增强 CUJ metric，不能从 `dur` 推导。需要 weighted jank 时应运行对应版本的官方 `android_jank_cuj` metric，并保留 metric 输出；第三方应用则使用 FrameTimeline、JankStats 或自定义 marker 建立场景边界。

## 4. CPU 调度：运行时间、排队时间和睡眠状态分开查

### 4.1 `sched` 只累计 Running

下面的查询按线程累计目标进程在 CPU 上运行的时间，并给出单次调度片段的 p95：

```sql
SELECT
  p.upid,
  p.pid,
  p.name AS process_name,
  t.utid,
  t.tid,
  t.name AS thread_name,
  COUNT(*) AS running_slice_count,
  ROUND(SUM(s.dur) / 1e6, 3) AS running_ms,
  ROUND(PERCENTILE(s.dur / 1e6, 95), 3) AS running_slice_p95_ms
FROM sched AS s
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
  AND s.dur > 0
GROUP BY
  p.upid,
  p.pid,
  p.name,
  t.utid,
  t.tid,
  t.name
ORDER BY running_ms DESC;
```

`SUM(sched.dur)` 是线程获得 CPU 后的运行时间，不包含 Runnable 排队、futex、Binder 或 I/O 等待。它也不是进程 CPU 利用率；若要算比例，分母要明确是 trace 墙钟、某个场景窗口、单核容量还是所有 CPU 容量。

### 4.2 `sched.latency` 给出 Running 前的 Runnable 时长

Android 17 固定源码中的 `sched.latency` 会把每个 Running interval 连接到同线程紧邻的 Runnable 状态。下面的查询用于发现调度排队较重的线程：

> 源码参照: `sched.latency` 标准库 — `android-17.0.0_r1` `src/trace_processor/perfetto_sql/stdlib/sched/latency.sql`。该模块依赖 `thread_state` 表中的 Runnable/Running 状态配对，未配对成功的 interval 不会出现在结果中。

```sql
INCLUDE PERFETTO MODULE sched.latency;

SELECT
  p.name AS process_name,
  t.name AS thread_name,
  t.tid,
  COUNT(*) AS wakeup_count,
  ROUND(AVG(l.latency_dur) / 1e6, 3) AS avg_runnable_ms,
  ROUND(PERCENTILE(l.latency_dur / 1e6, 95), 3) AS p95_runnable_ms,
  ROUND(MAX(l.latency_dur) / 1e6, 3) AS max_runnable_ms
FROM sched_latency_for_running_interval AS l
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
  AND l.latency_dur > 0
GROUP BY p.name, t.utid, t.name, t.tid
ORDER BY p95_runnable_ms DESC;
```

`latency_dur` 只代表被该模块成功配对的紧邻 Runnable 区间。高值说明线程已经可运行却迟迟没有获得 CPU；原因还要结合 CPU 利用、优先级、cpuset、频率、IRQ 和同核竞争判断。

### 4.3 时间窗内保留原始 `thread_state`

下面的模板检查主线程与给定窗口有交集的状态。`start_ns`、`end_ns` 应替换成 FrameTimeline、启动或 ANR 事件的绝对 trace 时间：

```sql
WITH
  params(start_ns, end_ns) AS (
    VALUES (1000000000, 1100000000)
  ),
  target_thread AS (
    SELECT
      t.utid,
      t.name
    FROM thread AS t
    JOIN process AS p USING (upid)
    WHERE p.name = 'com.example.app'
      AND t.is_main_thread = 1
  )
SELECT
  ts.ts,
  ts.dur,
  ts.state,
  ts.io_wait,
  ts.blocked_function
FROM thread_state AS ts
JOIN target_thread AS t USING (utid)
CROSS JOIN params
WHERE ts.dur > 0
  AND ts.ts < params.end_ns
  AND ts.ts + ts.dur > params.start_ns
ORDER BY ts.ts;
```

`Running`、`R`/`R+`、`S`、`D` 要保留原始值。`D` 配合 `io_wait = 1` 才更接近内核 I/O 等待；`S` 可能来自 Binder、futex、条件变量或主动睡眠。`blocked_function` 是内核阻塞点线索，不等于用户态调用栈。

## 5. 内存：三种表回答三种问题

### 5.1 `heap_profile_allocation` 观察 sampled native heap

Heapprofd 导入后的 `heap_profile_allocation.size` 是有符号增量：分配为正，释放为负。下面的查询重建每个进程实例的估算 live bytes，并统计采样窗口内的分配/释放 churn：

```sql
WITH
  deltas AS (
    SELECT
      h.id,
      h.ts,
      h.upid,
      p.pid,
      p.name AS process_name,
      h.size
    FROM heap_profile_allocation AS h
    JOIN process AS p USING (upid)
    WHERE p.name = 'com.example.app'
  ),
  live AS (
    SELECT
      *,
      SUM(size) OVER (
        PARTITION BY upid
        ORDER BY ts, id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      ) AS live_bytes
    FROM deltas
  )
SELECT
  upid,
  pid,
  process_name,
  ROUND(MAX(live_bytes) / 1024.0 / 1024.0, 3) AS peak_sampled_live_mib,
  ROUND(SUM(ABS(size)) / 1024.0 / 1024.0, 3) AS sampled_churn_mib
FROM live
GROUP BY upid, pid, process_name
ORDER BY peak_sampled_live_mib DESC;
```

Heapprofd 使用抽样与权重估计时，`live_bytes` 是 profile 模型下的估算值。采集开始前已经存在的分配、丢失的 free、进程退出和截断 trace 都会影响基线。定位热点还要通过 `callsite_id` 连接 stack profile 表或使用火焰图。

### 5.2 counter 查询前先看名称和单位

RSS、Swap、Java heap、GPU 或自定义 counter 可能落在不同 track 类型中。下面的查询只枚举目标进程的 process counter 范围，不预设单位：

```sql
SELECT
  p.pid,
  p.name AS process_name,
  pct.name AS counter_name,
  pct.unit,
  COUNT(*) AS sample_count,
  MIN(c.value) AS min_value,
  MAX(c.value) AS max_value
FROM counter AS c
JOIN process_counter_track AS pct
  ON pct.id = c.track_id
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
GROUP BY
  p.upid,
  p.pid,
  p.name,
  pct.id,
  pct.name,
  pct.unit
ORDER BY pct.name;
```

确认 `counter_name`、`unit` 和采样周期后，再写阈值查询。counter 值是瞬时值还是累计值由数据源定义；相邻值相减前应核对 counter 模式和 reset 行为。

### 5.3 DMA-BUF 需要内核事件，Binder 能改善归属

`android.memory.dmabuf` 读取 `dmabuf_allocs` ftrace 事件，并尝试沿 gralloc Binder 事务把 buffer 归还给请求进程。下面的查询给出目标进程的峰值和 trace 结束前末次观测值：

> 源码参照: `android.memory.dmabuf` 标准库 — `android-17.0.0_r1` `src/trace_processor/perfetto_sql/stdlib/android/memory/dmabuf.sql`。该模块依赖 `dmabuf_allocs` 内核 ftrace 事件（需要启用），释放记录为负值。

```sql
INCLUDE PERFETTO MODULE android.memory.dmabuf;

SELECT
  upid,
  process_name,
  ROUND(MAX(value) / 1024.0 / 1024.0, 3) AS peak_dmabuf_mib,
  ROUND(
    VALUE_AT_MAX_TS(ts, value) / 1024.0 / 1024.0,
    3
  ) AS ending_dmabuf_mib
FROM android_memory_cumulative_dmabuf
WHERE process_name = 'com.example.app'
GROUP BY upid, process_name;
```

结果为空时要检查 `dmabuf_allocs` 是否启用。缺少 Binder tracing 时，gralloc 代分配可能只能归到服务端线程；`android_dmabuf_allocs.buf_size` 的释放记录为负值，所以 ending 和 peak 不能互换。

## 6. Binder：客户端墙钟与服务端执行不能混写

`android.binder` 标准库依据 Binder slice 和 flow 关系，配对同步、异步事务，并补充 AIDL endpoint、客户端、服务端、OOM score 等信息。Android 17 固定源码已包含该模块。

> 源码参照: `android.binder` 标准库 — `android-17.0.0_r1` `src/trace_processor/perfetto_sql/stdlib/android/binder.sql`。配对逻辑依赖 Binder slice 的 flow 关系，缺少 `binder_transaction` ftrace 或 flow 关联时 `aidl_name` 可能为空。

下面的查询统计目标进程发起的同步 Binder 事务，分别报告客户端等待和服务端处理分位数：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  COALESCE(aidl_name, '<unresolved>') AS endpoint,
  server_process,
  COUNT(*) AS transaction_count,
  ROUND(PERCENTILE(client_dur / 1e6, 95), 3) AS client_p95_ms,
  ROUND(PERCENTILE(server_dur / 1e6, 95), 3) AS server_p95_ms,
  ROUND(
    AVG((client_dur - server_dur) / 1e6),
    3
  ) AS avg_non_server_ms
FROM android_binder_txns
WHERE client_process = 'com.example.app'
  AND is_sync = 1
  AND client_dur > 0
GROUP BY
  COALESCE(aidl_name, '<unresolved>'),
  server_process
ORDER BY client_p95_ms DESC
LIMIT 50;
```

`client_dur` 覆盖客户端发起到收到 reply 的墙钟区间，`server_dur` 覆盖服务端事务 slice。两者差值还混有服务端排队、Binder 驱动、客户端重新调度等时间，因此列名使用 `non_server`，不能直接标为 dispatch latency。`aidl_name` 为空通常表示缺少接口标注或解析证据，不能按时间近邻猜接口。

若客户端 p95 高而服务端 p95 低，继续查客户端 Runnable、服务端接单前排队和 reply 后重新调度；两者都高时，再检查服务端 CPU、锁、下游 Binder 和 I/O。

## 7. Data Explorer v54 的正确定位

Perfetto v54 发布公告把 Data Explorer 作为可视化查询构建器推出。`android-17.0.0_r1` 不是纯净的 v54.0 release：该固定 tag 已使用 `dev.perfetto.DataExplorer` plugin id，并包含查询图、DataGrid、图导入/导出和 dashboard 目录。用户可以从表、slice、时间范围等数据源开始，通过 filter、aggregate、join、interval intersect、sort 等节点构造查询图。

> 源码参照: Data Explorer plugin — `android-17.0.0_r1` `ui/src/plugins/dev.perfetto.DataExplorer/index.ts`。plugin id 为 `dev.perfetto.DataExplorer`，属分析端 UI，不改变设备端 `traced` / `traced_probes` / `perfetto` 二进制。

它适合两类工作：

- 不熟悉 trace 时，查看哪些标准库表有数据、有哪些列和值；
- 把一个复杂查询拆成节点，逐步核对过滤和聚合是否删错数据。

节点图仍会生成 PerfettoSQL。准备进入代码评审或 CI 时，应导出生成的 SQL 或查询图 JSON，并记录 UI/Trace Processor 版本。Data Explorer 属于分析端 UI；Android 17 固定 tag、上游 v54.0 release 和当前 v57.2 UI 的功能集合并不完全相同，操作说明应以正在使用的 UI commit 为准。

Data Explorer 的“has data”提示属于快速探测，不能替代前述 `COUNT(*)` 和 `stats` 门控。自动化门禁也不应依赖浏览器缓存或手工节点状态。

## 8. 自定义函数与查询成本

重复的单位换算可以封装为 session 内函数。下面的函数把纳秒转成毫秒，并用它查询最长 slice：

```sql
CREATE PERFETTO FUNCTION ns_to_ms(value LONG)
RETURNS DOUBLE AS
SELECT CAST($value AS DOUBLE) / 1e6;

SELECT
  ns_to_ms(MAX(dur)) AS max_slice_ms
FROM slice
WHERE dur > 0;
```

该函数只存在于当前 Trace Processor session。团队共享时，应放进自定义 SQL package，并由 `INCLUDE PERFETTO MODULE company.performance.units` 加载，避免每个查询复制一份定义。

大型 trace 的查询可以按以下规则收敛成本：

- 在最靠近原始表的位置限制 `upid`、`utid`、时间窗和 `dur > 0`；
- 明确列名，避免在百万行表上无目的使用 `SELECT *`；
- 字符串精确匹配优先 `=`，模式匹配使用 `GLOB` 并缩小候选范围；
- 同一复杂中间结果被多次读取时，用 `CREATE PERFETTO TABLE` 在 session 内物化；
- `ORDER BY`、窗口函数和区间连接前先过滤；
- 用 `EXPLAIN QUERY PLAN` 和结果行数评估查询，不凭 SQL 长度判断成本；
- 对 `PERCENTILE`、平均值和比率同时输出样本数，空分母用 `NULLIF` 处理。

`PERCENTILE(x, 95)` 会做分位插值。样本很少时，p95 可能接近最大值，CI 需要最低样本数门槛。

## 9. Python API：固定二进制再跑查询

官方 `perfetto` Python 包可以启动 Trace Processor、执行查询并转成 Pandas DataFrame。下面的脚本显式指定 v57.2 二进制，避免运行时静默下载更新版本：

```python
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

config = TraceProcessorConfig(
    bin_path="tools/trace_processor_shell-v57.2",
)

with TraceProcessor(
    trace="trace.perfetto-trace",
    config=config,
) as tp:
    rows = tp.query(
        """
        SELECT
          name,
          severity,
          source,
          value
        FROM stats
        WHERE severity IN ('data_loss', 'error')
          AND value > 0
        ORDER BY value DESC
        """
    )
    frame = rows.as_pandas_dataframe()
    print(frame.to_string(index=False))
```

`bin_path` 应指向仓库或制品库中经过校验的二进制；同时固定 Python 包版本和二进制 SHA-256。若省略 `bin_path`，包会使用其绑定版本；启用 `fetch_latest_trace_processor` 会降低结果可复现性，不适合回归门禁。

## 10. 跨 trace 聚合与 CI

一份 trace 只能证明一次运行。官方 `BatchTraceProcessor` 为每个输入 trace 建立独立查询上下文，返回每份 trace 的 DataFrame；`query_and_flatten()` 可以再合并结果。不要用 SQL `ATTACH` 拼接 Trace Processor 内部数据库。

下面的 CI 示例逐份统计目标进程 SurfaceFrame 记录，并同时设置数据质量门槛和 jank 比例门槛：

```python
from glob import glob

from perfetto.batch_trace_processor.api import BatchTraceProcessor

TRACE_FILES = sorted(glob("traces/*.perfetto-trace"))
MIN_FRAME_COUNT = 120
MAX_JANK_PERCENT = 5.0

JANK_SQL = """
SELECT
  COUNT(*) AS frame_count,
  SUM(
    CASE
      WHEN jank_type IS NOT NULL
       AND jank_type != 'None'
      THEN 1
      ELSE 0
    END
  ) AS jank_frame_count,
  COALESCE(
    100.0 * SUM(
      CASE
        WHEN jank_type IS NOT NULL
         AND jank_type != 'None'
        THEN 1
        ELSE 0
      END
    ) / NULLIF(COUNT(*), 0),
    0.0
  ) AS jank_percent
FROM actual_frame_timeline_slice AS a
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
  AND a.surface_frame_token != 0
"""

if not TRACE_FILES:
    raise SystemExit("no trace artifacts found")

failures = []
with BatchTraceProcessor(TRACE_FILES) as batch:
    results = batch.query(JANK_SQL)

for trace_file, result in zip(TRACE_FILES, results, strict=True):
    row = result.iloc[0]
    frame_count = int(row["frame_count"])
    jank_percent = float(row["jank_percent"])

    if frame_count < MIN_FRAME_COUNT:
        failures.append(
            f"{trace_file}: insufficient frames ({frame_count})"
        )
    elif jank_percent > MAX_JANK_PERCENT:
        failures.append(
            f"{trace_file}: jank={jank_percent:.2f}%"
        )

if failures:
    raise SystemExit("\n".join(failures))
```

这里的分母是目标进程 SurfaceFrame 记录；多 layer 应用可能一帧对应多行，团队要按产品场景决定是否改用 `android_frames` 或指定 layer。5% 和 120 帧只是示例值，正式阈值应来自固定设备、固定场景、多次运行的基线分布。数据量不足直接失败，避免缺采集被误判成性能优秀。

CI 还应保存原始 trace、采集配置、设备 build fingerprint、内核版本、场景标签、查询文件 hash、Trace Processor 版本和结果表。涉及 perf、调度或 DMA-BUF 内核行为时，本文的内核锚点为 `android17-6.18-2026-06_r6`。

## 11. Metrics extension 与 Trace Summary

Perfetto 的旧版 v1 Metrics 使用 SQL + proto extension，并通过 `--run-metrics` 输出 `TraceMetrics`。该机制仍用于既有 `android_jank_cuj` 等 metric，但官方已把它标为 legacy。新建批量分析优先使用 v51 引入的 Trace Summarization：查询结果映射到稳定的 `TraceSummary` protobuf，更适合跨 trace 聚合。

下面的最小 `TraceSummarySpec` 使用标准库 `linux.memory.process`，按进程计算 duration-weighted RSS + Swap：

```textproto
metric_spec {
  id: "memory_per_process"
  dimensions: "process_name"
  value: "avg_rss_and_swap"
  query: {
    table: {
      table_name: "memory_rss_and_swap_per_process"
    }
    referenced_modules: "linux.memory.process"
    group_by: {
      column_names: "process_name"
      aggregates: {
        column_name: "rss_and_swap"
        op: DURATION_WEIGHTED_MEAN
        result_column_name: "avg_rss_and_swap"
      }
    }
  }
}
```

`referenced_modules` 让 summarizer 加载标准库模块，`dimensions` 和 `value` 固定输出 schema。自定义事件可以先放入团队 SQL package，再在 spec 中引用 package 内的公开表。

下面的命令运行指定 summary metric：

```bash
trace_processor_shell summarize \
  --metrics-v2 memory_per_process \
  trace.perfetto-trace \
  spec.textproto
```

v55 起 Trace Processor CLI 改为 subcommand 架构；v54 时代二进制仍可能使用旧参数入口。CI 应固定二进制，并按该版本的 `--help` 选择调用形式。维护旧 v1 metric 时，SQL 热加载可以继续用于本地迭代，但新指标应评估迁移到 Trace Summary。

## 12. Android 17 trace 与 v57 AI skill 的组合

Perfetto AI skill 安装在宿主机代理环境中，它调用自己的 Trace Processor wrapper，不会升级 Android 17 设备里的 `traced`、`traced_probes` 或 `/system/bin/perfetto`。Android 17 trace 可以由 v57.2 分析端读取；查询能否成功取决于 trace 是否含对应数据，以及分析端是否有对应表和标准库模块。

代理生成 SQL 时应遵守同一套门控：

1. 报告 Trace Processor 版本、trace hash 和目标进程身份；
2. 用 `sqlite_master` / `pragma_table_info()` 探测表与列；
3. 用 `stats`、行数和时间范围检查数据质量；
4. 输出实际执行的 SQL、单位、结果行数和代表性样本；
5. 空结果写成“无数据”或“未观测到”，不能直接写成“没有发生”；
6. 结论回到 FrameTimeline、调度、Binder、profile 或源码证据。

v57.1 引入的 `state` 表属于分析端与 producer 数据格式的新能力，Android 17 固定平台源码没有这张表的生产链。代理应先检查 `sqlite_master` 中是否存在 `state`，再决定是否使用；完整边界见 §13.27。

## 13. 查询评审清单

- [ ] Android 平台、采集端 Perfetto、分析端 Perfetto 分别记录；
- [ ] front-end 结论能追到具体表、列和采集数据源；
- [ ] 使用 `upid` / `utid` 关联，展示时才输出 `pid` / `tid`；
- [ ] 时间单位、区间边界和 `dur = -1` 已处理；
- [ ] 空表、空分母、data loss 和最低样本数有独立分支；
- [ ] FrameTimeline 没有用固定 16.67 ms 代替平台分类；
- [ ] Runnable、Running、Sleeping、Binder client/server 没有混成一种耗时；
- [ ] counter 名称、单位、模式和 reset 行为已核对；
- [ ] 标准库模块与 Trace Processor 版本固定；
- [ ] CI 保存 trace、SQL、配置和工具 hash，可从失败结果回到原始时间窗。

## 参考源码与文档

- [Android 17 Perfetto changelog](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/CHANGELOG)
- [Android 17 `android.frames.timeline` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)
- [Android 17 `android.cujs.sysui_cujs` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/cujs/sysui_cujs.sql)
- [Android 17 `sched.latency` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/sched/latency.sql)
- [Android 17 `android.binder` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)
- [Android 17 `android.memory.dmabuf` 标准库源码](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/memory/dmabuf.sql)
- [Android 17 Data Explorer plugin](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/ui/src/plugins/dev.perfetto.DataExplorer/index.ts)
- [Perfetto v54 Data Explorer 发布公告](https://github.com/google/perfetto/discussions/5063)
- [Perfetto v57.2 release](https://github.com/google/perfetto/releases/tag/v57.2)
- [PerfettoSQL 入门](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started)
- [PerfettoSQL 语法](https://perfetto.dev/docs/analysis/perfetto-sql-syntax)
- [PerfettoSQL 标准库](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Perfetto Data Explorer](https://perfetto.dev/docs/visualization/data-explorer)
- [Trace Processor Python API](https://perfetto.dev/docs/analysis/trace-processor-python)
- [Batch Trace Processor](https://perfetto.dev/docs/analysis/batch-trace-processor)
- [Trace Summarization](https://perfetto.dev/docs/analysis/trace-summary)
- [Legacy trace-based metrics](https://perfetto.dev/docs/analysis/metrics)
- [Perfetto 官方 AI 使用说明](https://perfetto.dev/docs/getting-started/using-ai)
