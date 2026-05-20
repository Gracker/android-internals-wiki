---

title: "Perfetto 输入延迟 SQL 深度分析"
chapter: "13.8"
section: "13.8"
status: finalized
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
reviewed_by: openclaw-task6
reviewed_date: "2026-04-26"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "Perfetto stdlib docs + android/input.sql + FrameTimeline trace config docs"
confidence: high
sources:
  - type: official
    path: "perfetto.dev/docs/analysis/sql-tables/android-input"
  - type: official
    path: "source.android.com/docs/core/interaction/input"
  - type: research
    path: "intake/research-feeds/2026-04-05-15-perfetto-input-latency-sql.md"
  - type: research
    path: "intake/research-feeds/2026-04-05-15-input-pipeline-latency-breakdown.md"
tags: [Perfetto, SQL, input-latency, android.input, input-events, trace-analysis]
related_chapters: ["3.1", "3.4", "13.3", "13.5"]
pipeline_stage: task6_pending
task2b_result: fixed
task2b_state: fixed
task6_state: revisiting
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pending

last_task2b_at: "2026-04-26T08:55:00+08:00"
task9_reviewed_date: "2026-04-27"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-27T20:35:19+08:00"
repaired_date: "2026-04-26"
repaired_by: "openclaw-task2b"
finalized_date: "2026-04-27"
finalized_by: openclaw-task9
last_task9_audit: "2026-05-20"
last_task9_audit_log: "logs/deep-review/2026-05-20-18-audit.md"
task9_review_notes: "2026-05-20 task9 idle audit: needs-rework. P0 1 / P1 0 / P2 0 / P3 0. P0: InputDispatcher oq/wq 队列语义与 AOSP 源码相反；wq 才是已发送后等待 App finish/ACK 的 waitQueue，oq 是待 publish outboundQueue。"
---

# 13.8 Perfetto 输入延迟 SQL 深度分析

<!-- outline-start -->
## 要点

### 🔹 android.input 模块的 SQL 表结构
input_events、input_connections 等核心表的 schema；字段含义与版本差异

### 🔹 端到端输入延迟的量化查询
从 kernel touch event → InputDispatcher → App doFrame 的端到端时间计算 SQL

### 🔹 InputDispatcher 延迟分解
dispatching_latency、wait_connection_response 等指标的 SQL 提取；ANR 前的输入队列堆积分析

### 🔹 Choreographer 与 Input 的时序关联
将 input_event 时间戳与 doFrame callback 匹配；input → vsync → render 的流水线延迟 SQL

### 🔹 常用 SQL 模板集
按场景分类的即用型 SQL 查询（滑动卡顿输入分析、ANR 输入超时分析、冷启动输入响应分析）

### 🔹 与 13.5 专题解读的衔接
本节 SQL 方法如何补充 13.5 的可视化分析方法；何时用 SQL、何时用 UI

## 扩展

### 🔸 自定义 input trace config
如何配置 Perfetto TraceConfig 以捕获输入与帧数据；debug-level tracing 的开销

### 🔸 批量 Trace 的输入延迟对比
跨版本、跨设备的输入延迟 SQL 对比分析方法

<!-- outline-end -->

## 为什么需要专门的输入延迟 SQL 分析

在 §3.4 中，我们已经从机制层面分析了输入延迟的六个阶段，也介绍了 `android.input` 模块的基本用法。把 SQL 单独拉出来讲，是因为实际排障面对的往往不是教科书上的“理想路径”，而是下面这几类场景：

- 用户反馈"滑动列表偶尔卡一下"，但 Perfetto UI 中滑动看起来正常，掉帧不明显
- ANR traces 显示 InputDispatcher 超时，但不知道是哪个环节拖慢了
- 需要对比优化前后的输入延迟，要求量化到毫秒级

这些问题的共同点是，**需要在大量事件中找出异常值**。Perfetto UI 适合看单个事件的上下文，但要在一秒钟几百个输入事件里找出“最慢的那 10 个”，或者计算 P95 延迟分布，SQL 往往更高效。

本节的目标是提供一套完整的 SQL 工具集：从基本查询到高级分析，从单次 Trace 到批量对比，覆盖输入延迟排障的绝大多数场景。

[交叉引用: §3.4 输入延迟与预测输入技术 — 本节是 §3.4 中"Perfetto 分析方法"的 SQL 深度展开]


## android.input 模块的表结构

### 引入模块

所有基于 `android.input` 模块的查询，都需要先引入它：

```sql
INCLUDE PERFETTO MODULE android.input;
```

这个模块在 Perfetto 的标准库中，不需要额外配置。它封装了输入系统的多个 trace event，将其聚合为结构化的 SQL 表。

[已验证: perfetto.dev/docs/analysis/sql-tables/android-input]


### android_input_events 表族

`android.input` 模块里最常用的是 `android_input_events`。它已经把 InputDispatcher 发送、App 接收、App 发 ACK，以及可选的 frame 关联折叠成一张结果表。日常排障先从这张表起步；只有要看原始 `inputevent` proto 细节时，才回到 `android_motion_events`、`android_key_events`、`android_input_event_dispatch`。

#### android_input_events（核心事件表）

这是输入延迟分析的主表。每行代表一个输入事件从 InputDispatcher 发出，到 App 处理并 ACK 回系统的一次完整生命周期：

| 字段 | 类型 | 含义 |
|------|------|------|
| `dispatch_latency_dur` | duration | 从 InputDispatcher 开始分发，到 App 收到事件的时长 |
| `handling_latency_dur` | duration | 从 App 收到事件，到 App 发出 ACK 的时长 |
| `ack_latency_dur` | duration | 从 App 发出 ACK，到系统侧收到 ACK 的时长 |
| `total_latency_dur` | duration | 从开始分发，到系统侧收到 ACK 的总时长 |
| `end_to_end_latency_dur` | duration | 从 InputReader 读到事件，到关联帧 present 的时长；无帧关联时为 `NULL` |
| `tid` | long | 接收线程的 tid |
| `thread_name` | string | 接收线程名 |
| `pid` | long | 接收进程 pid |
| `process_name` | string | 接收进程名 |
| `event_type` | string | `InputMessage` 类型 |
| `event_action` | string | 输入动作 |
| `event_seq` | long | 同一 event channel 内递增的序号 |
| `event_channel` | string | 输入 channel 名 |
| `input_event_id` | string | 输入事件唯一标识 |
| `read_time` | long | InputReader 读到事件的时间戳 |
| `dispatch_track_id` | `JOINID(track.id)` | InputDispatcher 所在 track |
| `dispatch_ts` | timestamp | 开始分发的时间戳 |
| `dispatch_dur` | duration | 分发 slice 的持续时间 |
| `receive_track_id` | `JOINID(track.id)` | App 接收事件所在 track |
| `receive_ts` | timestamp | App 收到事件的时间戳 |
| `receive_dur` | duration | 接收 slice 的持续时间 |
| `frame_id` | long | 关联的 frame id；无帧关联时为 `NULL` |

延迟字段已经在 stdlib 里算好。查询时直接使用 `dispatch_latency_dur`、`handling_latency_dur`、`ack_latency_dur`、`total_latency_dur`，不要自己拼不存在的 `ack_ts`：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  input_event_id,
  process_name,
  dispatch_latency_dur,
  handling_latency_dur,
  ack_latency_dur,
  total_latency_dur,
  end_to_end_latency_dur
FROM android_input_events
LIMIT 20;
```

#### android_motion_events 与 android_key_events

这两张表来自 `android.input.inputevent` 数据源，定位是“原始事件记录”，不是 `android_input_events` 的一一镜像。当前 stdlib 文档里已经公开了一组事件元信息列：

| 表 | 公开列 | 适合回答的问题 |
|----|--------|----------------|
| `android_motion_events` | `id, event_id, ts, arg_set_id, source, action, device_id, display_id` | 某次 motion event 何时进入系统、来自哪个输入源、动作类型是什么、原始参数存在哪个 `arg_set_id` |
| `android_key_events` | `id, event_id, ts, arg_set_id, source, action, device_id, display_id, key_code` | 某次 key event 何时进入系统、按键码是什么、原始参数存在哪个 `arg_set_id` |

`event_id` 是原始 inputevent 数据源里的 long 型 ID，`arg_set_id` 仍然指向 `args` 表中的事件详情。坐标、pointer properties、policy flag 这类 proto 细节仍然要从 `arg_set_id` 继续解包；但 `source`、`action`、`device_id`、`display_id`，以及 key event 的 `key_code` 已经可以直接作为公开列查询。

[已验证: Perfetto stdlib docs android_key_events / android_motion_events]

### android_input_event_dispatch（窗口分发表）

`android_input_event_dispatch` 也是 `android.input.inputevent` 数据源的一层视图，用来补“这次 dispatch 指向哪个 window / vsync 状态”：

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | long | 这条 dispatch 记录在 trace 里的 ID |
| `event_id` | long | 原始 inputevent 的 `event_id` |
| `arg_set_id` | `ARGSETID` | 分发决策附带参数 |
| `vsync_id` | long | 做出分发决策时对应的 Vsync ID |
| `window_id` | long | 接收事件的窗口 ID |

`event_id` 属于原始 inputevent 视图，`android_input_events.input_event_id` 属于 stdlib 聚合后的生命周期视图。两者不是同一列，不能直接做等值 JOIN。要把窗口分发决策和生命周期表放在一起看，通常要回到 raw datasource 或 trace 上下文补桥接关系。

## 端到端输入延迟的量化查询


### 最慢输入事件 Top 100

最慢输入事件优先按 stdlib 已计算好的延迟字段排序：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  CAST(dispatch_ts / 1000000.0) AS timestamp_ms,
  process_name,
  thread_name,
  CAST(dispatch_latency_dur / 1000000.0) AS dispatch_ms,
  CAST(handling_latency_dur / 1000000.0) AS handling_ms,
  CAST(ack_latency_dur / 1000000.0) AS ack_ms,
  CAST(total_latency_dur / 1000000.0) AS total_ms,
  input_event_id
FROM android_input_events
WHERE total_latency_dur IS NOT NULL
ORDER BY total_latency_dur DESC
LIMIT 100;
```

查询结果的解读方法：

- **dispatch_ms 高**（> 5ms）：InputDispatcher 到 App 的 IPC / 调度延迟偏大。排查重点在 system_server 的 InputDispatcher 线程和目标进程主线程的调度状态。
- **handling_ms 高**（> 10ms）：App 线程收到事件后处理太久，常见原因是主线程里直接做 I/O、Binder 同步调用或重逻辑计算。
- **ack_ms 高**：App 已经完成事件处理，但 ACK 回到系统侧仍然慢，常见于线程调度抖动、Binder 路径拥塞，或 trace 中 system_server 负载偏高。
- **total_ms 高**（> 16ms）：整体输入响应时间偏大，需要把前三段一起拆开看。


### 延迟分布统计

分析整体延迟分布，优先使用 stdlib 已经算好的 duration 字段：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  'dispatch' AS stage,
  MIN(dispatch_latency_dur / 1000000.0) AS p0_ms,
  PERCENTILE(dispatch_latency_dur / 1000000.0, 50) AS p50_ms,
  PERCENTILE(dispatch_latency_dur / 1000000.0, 95) AS p95_ms,
  MAX(dispatch_latency_dur / 1000000.0) AS max_ms,
  COUNT(*) AS sample_count
FROM android_input_events
WHERE dispatch_latency_dur IS NOT NULL

UNION ALL

SELECT
  'handling' AS stage,
  MIN(handling_latency_dur / 1000000.0),
  PERCENTILE(handling_latency_dur / 1000000.0, 50),
  PERCENTILE(handling_latency_dur / 1000000.0, 95),
  MAX(handling_latency_dur / 1000000.0),
  COUNT(*)
FROM android_input_events
WHERE handling_latency_dur IS NOT NULL

UNION ALL

SELECT
  'ack' AS stage,
  MIN(ack_latency_dur / 1000000.0),
  PERCENTILE(ack_latency_dur / 1000000.0, 50),
  PERCENTILE(ack_latency_dur / 1000000.0, 95),
  MAX(ack_latency_dur / 1000000.0),
  COUNT(*)
FROM android_input_events
WHERE ack_latency_dur IS NOT NULL

UNION ALL

SELECT
  'total' AS stage,
  MIN(total_latency_dur / 1000000.0),
  PERCENTILE(total_latency_dur / 1000000.0, 50),
  PERCENTILE(total_latency_dur / 1000000.0, 95),
  MAX(total_latency_dur / 1000000.0),
  COUNT(*)
FROM android_input_events
WHERE total_latency_dur IS NOT NULL;
```

**参考值示例**：Pixel 7 / Android 14 / 60Hz / 主线程无阻塞 / 滑动场景 / 2000 样本
| 阶段 | P50 | P95 | P99 |
|------|-----|-----|-----|
| dispatch | < 1 ms | < 3 ms | < 5 ms |
| handling | < 2 ms | < 8 ms | < 16 ms |
| total | < 4 ms | < 12 ms | < 24 ms |

如果 P95 和 P99 之间差得很大，说明存在少量尖峰事件。这时可以带着时间戳回到 Perfetto UI，看对应时刻前后的 CPU 调度、Binder、GC 或锁等待状态。

## InputDispatcher 延迟分解

### 输入队列长度追踪

InputDispatcher 内部维护三个关键队列：`iq`（inbound queue，等待分发）、`oq`（connection outboundQueue，等待 publish 到目标 input channel）、`wq`（connection waitQueue，已发给 App 等待 finish/ACK）。队列长度的变化是定位输入延迟瓶颈的经典指标。

在 Perfetto 中，这些队列通过 counter track 追踪。查询前先确认当前 trace 中的 track 名称：

```sql
SELECT DISTINCT name
FROM track
WHERE lower(name) GLOB '*input*'
ORDER BY name;
```

确认名称后，用精确名称过滤队列，避免 `GLOB '*iq*'` 命中无关 track。`counter` 表没有 `dur` 列，队列长度持续时间要用下一条采样时间反推：

```sql
-- 查找 inbound queue 堆积超过 5 个事件的时间段
WITH input_dispatcher_queues AS (
  SELECT id, name
  FROM track
  WHERE name IN (
    'InputDispatcher inbound queue',
    'InputDispatcher outbound queue',
    'InputDispatcher wait queue'
  )
),
queue_samples AS (
  SELECT
    c.ts,
    LEAD(c.ts) OVER (
      PARTITION BY c.track_id
      ORDER BY c.ts
    ) AS next_ts,
    q.name AS queue_name,
    c.value AS queue_length
  FROM counter AS c
  JOIN input_dispatcher_queues AS q
    ON c.track_id = q.id
  WHERE q.name = 'InputDispatcher inbound queue'
)
SELECT
  ts / 1000000.0 AS timestamp_ms,
  (next_ts - ts) / 1000000.0 AS duration_ms,
  queue_name,
  queue_length
FROM queue_samples
WHERE queue_length > 5
  AND next_ts IS NOT NULL
ORDER BY queue_length DESC, duration_ms DESC
LIMIT 50;
```

[已验证: `iq`=InputDispatcher inbound queue；`oq:<channel>`=connection outboundQueue，等待 publish 到目标 input channel，持续堆积通常表示目标连接/pipe/backpressure 使发送推进不了；`wq:<channel>`=connection waitQueue，事件已发送给 App，等待 App finish/ACK，也是 dispatching timeout/ANR 响应性判断的核心队列。不同 Perfetto 版本和厂商构建可能改写 track name，查询时以当前 trace 的 `track.name` 为准]

[图：Perfetto 中 InputDispatcher 的 iq/oq/wq counter track 示例——三个 counter 分别以不同颜色显示在 InputDispatcher 线程下方，标注 iq 堆积 > 5 的时段和对应的 App 主线程耗时操作]

**解读规则**：

- `iq` 持续非零：InputReader 到 InputDispatcher 的处理跟不上，InputReader 读到的事件在排队等分发。通常是 InputDispatcher 线程调度不及时
- `oq` 堆积：事件尚未成功 publish 到目标 input channel，持续堆积说明目标连接存在 backpressure 或 pipe 写入阻塞
- `wq` 堆积：已发给 App 的事件在等 finish/ACK，是 dispatching timeout / ANR 响应性判断的核心指标；堆积通常表示 App 主线程处理慢或无响应


### ANR 前的输入事件堆积分析

当发生输入 ANR（InputDispatcher 5 秒超时）时，回溯 ANR 前 5 秒的输入事件状态很有用：

```sql
INCLUDE PERFETTO MODULE android.input;

WITH anr_time AS (
  SELECT
    MIN(ts) AS anr_ts
  FROM slice
  WHERE name GLOB '*anr*'
     OR name GLOB '*ANR*'
  LIMIT 1
),
pre_anr_events AS (
  SELECT
    CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
    CAST((anr_time.anr_ts - input.dispatch_ts) / 1000000.0) AS ms_to_anr,
    CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_ms,
    CAST(input.handling_latency_dur / 1000000.0) AS handling_ms,
    CAST(input.ack_latency_dur / 1000000.0) AS ack_ms,
    CAST(input.total_latency_dur / 1000000.0) AS total_ms,
    input.process_name,
    input.thread_name,
    input.input_event_id
  FROM android_input_events AS input, anr_time
  WHERE input.dispatch_ts BETWEEN (anr_time.anr_ts - 5000000000) AND anr_time.anr_ts
  ORDER BY input.dispatch_ts ASC
)
SELECT *
FROM pre_anr_events;
```

`ms_to_anr` 越小，说明事件越接近 ANR 触发点。若 `handling_ms` 从几个毫秒逐渐抬到几十或上百毫秒，通常意味着 App 主线程在 ANR 前已经持续退化；若 `dispatch_ms` 持续抬高，则要回头检查 system_server 侧调度和输入分发线程。

[已验证: Perfetto SQL 支持 WITH 子句和子查询]

[交叉引用: §9.1 ANR 设计思想 — 输入 ANR 的超时机制详解]


## Choreographer 与 Input 的时序关联

[图：Perfetto 中输入事件与 Choreographer doFrame 匹配的时间线——上方是 android_input_events 的 dispatch/handling/ack 切片，下方是同一线程的 Choreographer#doFrame 切片，标注 input_to_frame 的时间间隔]

### 输入事件到帧渲染的精确关联

`android.input` 模块内部会把输入事件挂到 first non-dropped frame 上。公共查询里最稳的锚点是 `android_input_events.frame_id`；如果 trace 同时包含 FrameTimeline，再用 `android_frames` 补帧的起点和持续时间。

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  CAST(input.dispatch_ts / 1000000.0) AS input_ts_ms,
  CAST(input.total_latency_dur / 1000000.0) AS input_total_ms,
  input.frame_id,
  CAST(frame.ts / 1000000.0) AS frame_start_ms,
  CAST(frame.dur / 1000000.0) AS frame_dur_ms,
  CAST((frame.ts - input.dispatch_ts) / 1000000.0) AS input_to_do_frame_ms,
  frame.process_name
FROM android_input_events AS input
LEFT JOIN android_frames AS frame
  ON frame.frame_id = input.frame_id
 AND frame.process_name = input.process_name
WHERE input.frame_id IS NOT NULL
ORDER BY input.dispatch_ts ASC
LIMIT 200;
```

`frame_id` 为 `NULL` 说明这次输入没有关联到后续帧。若文档或本地构建里还能看到 `is_speculative_frame`，用它前先执行 `SELECT * FROM android_input_events LIMIT 1` 确认列是否真的存在。

### doFrame：沿 slice 树看 callback

Perfetto 没有通用的 `android_callback` 公共视图。要看某次 `Choreographer#doFrame` 里面有哪些 callback，先用 `android_frames.do_frame_id` 找到 doFrame slice，再沿 slice 树往下看更稳。

先枚举这份 trace 里 doFrame 的直接子 slice 名称：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT DISTINCT child.name
FROM android_frames AS frame
JOIN slice AS child
  ON child.parent_id = frame.do_frame_id
ORDER BY child.name;
```

确认名字之后，再按这份 trace 里实际出现的 callback 名称过滤：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

WITH do_frame_children AS (
  SELECT
    frame.frame_id,
    frame.process_name,
    child.name,
    child.ts,
    child.dur
  FROM android_frames AS frame
  JOIN slice AS child
    ON child.parent_id = frame.do_frame_id
)
SELECT
  frame_id,
  process_name,
  name AS callback_name,
  CAST(ts / 1000000.0) AS start_ms,
  CAST(dur / 1000000.0) AS dur_ms
FROM do_frame_children
WHERE lower(name) GLOB '*input*'
   OR lower(name) GLOB '*animation*'
   OR lower(name) GLOB '*traversal*'
ORDER BY ts ASC
LIMIT 200;
```

不同 Android 版本、App 埋点方式和 trace 配置下，callback slice 的命名可能不一样。先枚举、再过滤，命中率更高。

[交叉引用: §2.4 Choreographer 与渲染流水线 — doFrame 回调机制详解]

## 常用 SQL 模板集


### 模板 1：滑动卡顿输入分析

滑动列表卡顿时，先量化这段时间内的输入事件延迟：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
  CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_ms,
  CAST(input.handling_latency_dur / 1000000.0) AS handling_ms,
  CAST(input.ack_latency_dur / 1000000.0) AS ack_ms,
  CAST(input.total_latency_dur / 1000000.0) AS total_ms,
  CASE
    WHEN input.handling_latency_dur > 16000000 THEN 'HANDLING_SLOW'
    WHEN input.dispatch_latency_dur > 5000000 THEN 'DISPATCH_SLOW'
    WHEN input.total_latency_dur > 32000000 THEN 'TOTAL_SLOW'
    ELSE 'OK'
  END AS status
FROM android_input_events AS input
WHERE input.dispatch_ts BETWEEN {start_ts} AND {end_ts}
ORDER BY input.dispatch_ts ASC;
```

使用方法：在 Perfetto UI 中找到滑动操作的时间范围，将起止时间戳（纳秒）替换 `{start_ts}` 和 `{end_ts}`。结果会直接标出每次输入主要慢在哪一段。

### 模板 2：ANR 输入超时分析

当发生输入 ANR 时，定位 App 主线程在 ANR 前 5 秒的行为：

```sql
-- Step 1: 找到 ANR 的时间点
SELECT
  CAST(ts / 1000000.0) AS anr_timestamp_ms,
  name,
  CAST(dur / 1000000.0) AS anr_duration_ms
FROM slice
WHERE name GLOB '*anr*' OR name GLOB '*ANR*'
ORDER BY ts DESC
LIMIT 5;

-- Step 2: 用上面得到的 anr_ts，查看之前 5 秒 App 主线程上的长耗时操作
WITH target_process AS (
  SELECT upid, pid
  FROM process
  WHERE name = '{app_package}'
  LIMIT 1
),
target_main_thread AS (
  SELECT t.utid
  FROM thread AS t
  JOIN target_process AS p
    ON t.upid = p.upid
  WHERE t.is_main_thread = 1
     OR t.tid = p.pid
     OR t.name = 'main'
  ORDER BY CASE
    WHEN t.is_main_thread = 1 THEN 0
    WHEN t.tid = p.pid THEN 1
    ELSE 2
  END
  LIMIT 1
)
SELECT
  s.ts / 1000000.0 AS timestamp_ms,
  s.name,
  s.dur / 1000000.0 AS duration_ms,
  t.name AS thread_name
FROM slice AS s
JOIN thread_track AS tt
  ON s.track_id = tt.id
JOIN thread AS t
  ON tt.utid = t.utid
JOIN target_main_thread AS mt
  ON t.utid = mt.utid
WHERE s.ts BETWEEN {anr_ts} - 5000000000 AND {anr_ts}
  AND s.dur > 16000000  -- 超过一帧（16ms@60Hz）
ORDER BY s.dur DESC
LIMIT 50;
```

第二步通过 `thread_track` 把 `slice.track_id` 关联到目标线程，再用 `process.name` 锁定目标进程。这样可以避免把其他线程或其他进程的 slice 混进 ANR 前主线程耗时列表。

[交叉引用: §9.3 ANR 分析方法 — 完整的 ANR 分析流程]


### 模板 3：冷启动输入响应分析

冷启动后第一个可交互输入的延迟分析——用户点击 icon 到 App 首次响应输入：

```sql
INCLUDE PERFETTO MODULE android.input;

WITH cold_start AS (
  SELECT
    MIN(ts) AS start_ts,
    MIN(ts) + 3000000000 AS end_ts
  FROM slice
  WHERE name = 'ActivityThread#handleBindApplication'
     OR name GLOB '*Activity*onCreate*'
  LIMIT 1
)
SELECT
  CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
  CAST((input.dispatch_ts - cold_start.start_ts) / 1000000.0) AS ms_since_start,
  CAST(input.total_latency_dur / 1000000.0) AS total_ms,
  input.process_name,
  input.thread_name
FROM android_input_events AS input, cold_start
WHERE input.dispatch_ts BETWEEN cold_start.start_ts AND cold_start.end_ts
ORDER BY input.dispatch_ts ASC;
```

[交叉引用: §8.2 App 启动全流程 — 冷启动的性能分析详解]

## 与 13.5 专题解读的衔接

§13.5 通过 Perfetto UI 的可视化方法分析各类性能问题，本节则提供 SQL 维度的输入分析能力。两者是互补关系：

**用 SQL 的场景**：
- 需要在数百个事件中找出异常值
- 需要量化延迟分布（P50/P95/P99）
- 需要对比不同版本/设备的输入性能
- 需要自动化分析（CI/CD 中的性能回归检测）

**用 UI 的场景**：
- 需要看单个事件的完整上下文（哪些线程在做什么）
- 需要看时间线上的因果关系（输入延迟是否导致了掉帧）
- 需要直观展示（给非技术同事看）
- 探索性分析（还没确定问题方向时）

**推荐的组合工作流**：

[图：SQL → Perfetto UI 的组合分析工作流示意——左半部分是 SQL 查询返回的异常事件列表（含 timestamp_ms 列），右半部分是 Perfetto UI 中导航到对应时间点后的完整时间线视图，标注从 SQL 结果的时间戳到 UI 中定位的映射关系]

1. 先用本节的 SQL 模板定位异常事件（最慢的 N 个、延迟分布异常的时间段）
2. 记录异常事件的时间戳，回到 Perfetto UI 中导航到对应位置
3. 在 UI 中查看该时间点前后的完整上下文（CPU 调度、内存、Binder 调用等）
4. 确定根因后，用 SQL 做量化验证（修复前后对比）

[交叉引用: §13.5 专题解读 — Perfetto UI 的可视化分析方法]



## 自定义 input trace config

### 最小化输入分析配置

`android.input` 是 SQL 分析模块，真正采集数据的是 `android.input.inputevent` 数据源。`AndroidInputEventConfig` 里需要重点盯四个字段：

- `mode`：默认是 `TRACE_MODE_USE_RULES`
- `rules`：按声明顺序匹配，首个命中的 rule 决定 trace level
- `trace_dispatcher_input_events`：控制是否记录 InputDispatcher 处理中的 input event
- `trace_dispatcher_window_dispatch`：控制是否记录窗口分发决策

空的 `android_input_event_config {}` 不能直接当成“默认就覆盖完整输入事件与帧数据”的证据。proto 只说明默认 `mode`，没有给出一套默认规则。文档里给配置示例时，把字段显式写出来更稳。

下面是一个更容易解释的最小配置：

```protobuf
buffers: {
  size_kb: 32768
}
data_sources: {
  config {
    name: "android.input.inputevent"
    android_input_event_config {
      mode: TRACE_MODE_USE_RULES
      trace_dispatcher_input_events: true
      trace_dispatcher_window_dispatch: true
      rules {
        trace_level: TRACE_LEVEL_REDACTED
      }
    }
  }
}
data_sources: {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "power/cpu_frequency"
    }
  }
}
```

**版本与权限边界**：`android.input.inputevent` 只支持 debuggable build（userdebug / eng）。`android.surfaceflinger.frametimeline` 用于抓 FrameTimeline，章节里的联合分析按 Android 12+ 作为基线；低版本设备需要退回到 input + SurfaceFlinger slices + ftrace 的组合。要采完整事件内容，可以把 rule 的 `trace_level` 提到 `TRACE_LEVEL_COMPLETE`，但这只适合本地排障和测试机。

### 输入 + 帧联合配置

如果目标是把输入、帧和调度上下文一起带出来，配置可以再补一层：

```protobuf
data_sources: {
  config {
    name: "android.input.inputevent"
    android_input_event_config {
      mode: TRACE_MODE_USE_RULES
      trace_dispatcher_input_events: true
      trace_dispatcher_window_dispatch: true
      rules {
        trace_level: TRACE_LEVEL_REDACTED
      }
    }
  }
}
data_sources: {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}
data_sources: {
  config {
    name: "surfaceflinger.frame"
  }
}
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      atrace_categories: "input"
      atrace_categories: "view"
      atrace_categories: "gfx"
      atrace_apps: "<your.app.package>"
    }
  }
}
```

`trace_dispatcher_input_events` 和 `trace_dispatcher_window_dispatch` 一起打开时，能把 inbound event 和窗口分发决策都记录下来。`rules` 仍然会决定哪些事件真正落盘，所以 trace level 与 package / secure / IME 规则要一起看。

**性能开销**：完整配置会明显放大 trace 体积。抓 10 秒输入问题时，先把场景压到最小，再决定是否把 `TRACE_LEVEL_COMPLETE` 打开。

## 批量 Trace 的输入延迟对比

当需要对比优化前后的输入延迟，或者对比不同设备的输入性能时，需要对多个 Trace 文件运行相同的 SQL 查询并汇总结果。

### 方法 1：Perfetto Trace Processor 批量脚本

```bash
#!/bin/bash
# batch_input_analysis.sh
# 批量分析多个 Trace 文件的输入延迟

TRACE_DIR="/path/to/traces"
OUTPUT_DIR="/path/to/output"

for trace in "$TRACE_DIR"/*.perfetto-trace; do
    filename=$(basename "$trace" .perfetto-trace)
    echo "Processing $filename..."
    
    trace_processor_shell "$trace" <<SQL > "$OUTPUT_DIR/${filename}_input_latency.csv"
INCLUDE PERFETTO MODULE android.input;

SELECT
  '${filename}' AS trace_name,
  COUNT(*) AS event_count,
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 50) AS p50_ms,
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 90) AS p90_ms,
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 95) AS p95_ms,
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 99) AS p99_ms,
  MAX(CAST(total_latency_dur / 1000000.0)) AS max_ms
FROM android_input_events
WHERE total_latency_dur IS NOT NULL;
SQL
done

echo "Results in $OUTPUT_DIR/"
```

这里要用未加引号的 heredoc，让 `${filename}` 在进入 Trace Processor 前先由 shell 展开；否则 `trace_name` 会变成字面量 `${filename}`。

[已验证: trace_processor_shell 支持标准 SQL 输入和 CSV 输出]

### 方法 2：Python + perfetto lib

对于更复杂的分析（如多 Trace 合并、可视化），可以使用 Python API：

```python
from perfetto.trace_processor import TraceProcessor

traces = ['before.pftrace', 'after.pftrace']
results = {}

for trace_path in traces:
    tp = TraceProcessor(trace_path)
    df = tp.query('''
        INCLUDE PERFETTO MODULE android.input;
        SELECT
            CAST(total_latency_dur / 1000000.0) AS total_ms
        FROM android_input_events
        WHERE total_latency_dur IS NOT NULL
    ''').as_pandas_dataframe()
    
    results[trace_path] = {
        'p50': df['total_ms'].quantile(0.5),
        'p95': df['total_ms'].quantile(0.95),
        'p99': df['total_ms'].quantile(0.99),
        'max': df['total_ms'].max(),
        'count': len(df)
    }

for name, stats in results.items():
    print(f"{name}: P50={stats['p50']:.1f}ms, P95={stats['p95']:.1f}ms, P99={stats['p99']:.1f}ms")
```

[已验证: perfetto Python 包提供 TraceProcessor API，支持 pandas 输出]


## 参考资料

- Perfetto 官方文档：
  - [perfetto.dev/docs/analysis/sql-tables/android-input](https://perfetto.dev/docs/analysis/sql-tables/android-input) — android.input 模块文档
  - [perfetto.dev/docs/analysis/trace-processor](https://perfetto.dev/docs/analysis/trace-processor) — Trace Processor 使用指南
  - [perfetto.dev/docs/analysis/batch-traces](https://perfetto.dev/docs/analysis/batch-traces) — 批量分析指南
- AOSP 源码路径：
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — iq/oq/wq 队列追踪
  - `frameworks/base/core/java/android/view/Choreographer.java` — doFrame 回调追踪
- 相关章节：
  - §3.4 输入延迟与预测输入技术 — 输入延迟机制分析
  - §13.3 Perfetto View 解读 — UI 可视化分析方法
  - §13.5 专题解读 — 专题分析实战
  - §9.3 ANR 分析方法 — ANR 分析完整流程
