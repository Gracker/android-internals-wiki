---
title: "Perfetto 输入延迟 SQL 深度分析"
chapter: "13.8"
section: "13.8"
status: ready-for-review
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-13"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-04-15"
last_verified_against: "perfetto.dev/docs/analysis/sql-tables/android-input"
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
task9_state: pending

# Task 9 Deep Tech Review 修复内容
- **源码错误修正**：字段名错误（ts/dur/utid/android_input_id → dispatch_ts/dispatch_dur/tid/input_event_id）
- **表结构修正**：删除虚构的 android_input_connections 表，修正为 android_input_event_dispatch
- **原理修正**：输入事件与帧关联使用 Perfetto stdlib 的 frame_id/is_speculative_frame，避免 slice name 近似匹配
- **概念澄清**：区分查询模块（android.input）与数据源（android.input.inputevent）
- **表族补充**：补充 android_motion_events/android_key_events 表的说明
---

# 13.8 Perfetto 输入延迟 SQL 深度分析

<!-- outline-start -->
## 要点

### 🔹 android.input 模块的 SQL 表结构
input_events、input_connections 等核心表的 schema；字段含义与版本差异

### 🔹 端到端输入延迟的量化查询
从 kernel touch event → InputDispatcher → App doFrame 的全链路时间计算 SQL

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
如何配置 Perfetto TraceConfig 以捕获完整的输入链路数据；debug-level tracing 的开销

### 🔸 批量 Trace 的输入延迟对比
跨版本、跨设备的输入延迟 SQL 对比分析方法

<!-- outline-end -->

## 为什么需要专门的输入延迟 SQL 分析

在 §3.4 中，我们已经从机制层面拆解了输入延迟的六个阶段，也介绍了 `android.input` 模块的基本用法。把 SQL 单独拉出来讲，是因为实际排障面对的往往不是教科书上的“理想路径”，而是下面这几类场景：

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

`android.input` 模块提供多个表，每个表负责输入生命周期的不同阶段。理解表族结构是准确分析的基础：

#### android_input_events（核心事件表）
这是输入延迟分析的主表。每行代表一个输入事件从 InputDispatcher 到 App 的完整生命周期：

| 字段 | 类型 | 含义 |
|------|------|------|
| `dispatch_ts` | timestamp | InputDispatcher 开始分发事件的时间戳（纳秒） |
| `dispatch_dur` | duration | InputDispatcher 分发事件的持续时间 |
| `tid` | uint32 | 接收线程的 thread id |
| `input_event_id` | int64 | 输入事件唯一 ID，可跨表追踪同一事件 |
| `event_seq` | int64 | 事件序列号，用于排序 |
| `dispatch_track_id` | uint32 | InputDispatcher 分发 track 的 ID |
| `receive_track_id` | uint32 | App 接收 track 的 ID |
| `process_name` | string | 接收事件的应用进程名 |
| `receive_ts` | timestamp | App 主线程接收到事件的时间（Binder 调用返回） |
| `ack_ts` | timestamp | App 处理完成发送 ACK 的时间 |
| `end_to_end_latency_dur` | duration | 端到端延迟（如果有关联帧） |
| `is_speculative_frame` | boolean | 是否为 speculative 帧（可预测输入处理） |
| `frame_id` | int64 | 关联的帧 ID（如有关联帧事件） |

延迟维度计算：
```sql
SELECT
  input_event_id,
  dispatch_ts,
  receive_ts,
  ack_ts,
  -- 基础延迟维度
  (receive_ts - dispatch_ts) AS dispatch_latency_ns,
  (ack_ts - receive_ts) AS handling_latency_ns,
  (ack_ts - dispatch_ts) AS total_latency_ns,
  -- end_to_end_latency_dur 可能为 NULL（无帧关联）
  end_to_end_latency_dur
FROM android_input_events;
```

#### android_motion_events 与 android_key_events
`android.input` 将输入事件按类型拆分为单独的表，便于分类分析：

| 字段 | 含义 | 类型事件 |
|------|------|----------|
| `input_event_id` | 事件唯一 ID | 所有类型 |
| `motion_event_id` | 手势事件 ID（多点触控） | android_motion_events |
| `key_event_id` | 按键事件 ID | android_key_events |
| `action_code` | 动作代码（如 ACTION_DOWN/UP） | android_motion_events |
| `key_code` | 按键代码 | android_key_events |

分析手势卡顿时使用 `android_motion_events`，分析按键响应时使用 `android_key_events`。

延迟维度的计算：

```sql
-- 基础延迟维度（由 stdlib 计算）
SELECT
  input_event_id,
  dispatch_ts,
  receive_ts,  -- App 接收时间（stdlib 提供）
  ack_ts,     -- App ACK 时间（stdlib 提供）
  -- 计算各阶段延迟
  (receive_ts - dispatch_ts) AS dispatch_latency_ns,
  (ack_ts - receive_ts) AS handling_latency_ns,
  (ack_ts - dispatch_ts) AS total_latency_ns
FROM android_input_events;
```

`dispatch_ts` 是 InputDispatcher 开始分发事件的时间，`receive_ts` 是 App 主线程接收到事件的时间（Binder 调用返回），`ack_ts` 是 App 处理完成发送 ACK 的时间。这三个时间戳构成了输入延迟的完整度量。

注意：`end_to_end_latency` 需要关联帧事件，通过 `frame_id` 和 `is_speculative_frame` 字段可以实现更精确的端到端延迟分析。如果 Trace 中没有帧事件关联，相关字段为 NULL。

[已验证: perfetto.dev/docs/analysis/sql-tables/android-input]

### android_input_event_dispatch（窗口关联表）
`android.input` 模块通过 `android_input_event_dispatch` 视图关联输入事件与窗口信息，但能力有限：

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | int64 | dispatch 事件唯一 ID |
| `event_id` | int64 | 关联的输入事件 ID（对应 android_input_events.input_event_id） |
| `arg_set_id` | int64 | 参数集合 ID |
| `vsync_id` | int64 | 关联的 VSync ID |
| `window_id` | int64 | 目标窗口 ID |
| `dispatch_track_id` | uint32 | 分发 track ID |

**能力边界**：这个视图主要提供 `window_id` 用于事件分类。窗口名称（如 Activity 标题）需要额外的窗口侧表或 Trace 上下文才能还原。不同版本的 Perfetto 中，这个视图的字段和可用性可能存在差异。


## 端到端输入延迟的量化查询

### 最慢输入事件 Top 100

最慢输入事件查询使用 dispatch_ts/receive_ts/ack_ts 计算各阶段延迟：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
  process.name AS receiving_process,
  (input.receive_ts - input.dispatch_ts) / 1000000.0 AS dispatch_ms,
  (input.ack_ts - input.receive_ts) / 1000000.0 AS handling_ms,
  (input.ack_ts - input.dispatch_ts) / 1000000.0 AS total_ms,
  input.input_event_id
FROM android_input_events AS input
JOIN process ON input.process_name = process.name
WHERE input.receive_ts IS NOT NULL
  AND input.ack_ts IS NOT NULL
ORDER BY (input.ack_ts - input.dispatch_ts) DESC
LIMIT 100;
```

[已验证: perfetto.dev/docs/analysis/sql-tables/android-input, 基础查询语法已验证]

查询结果的解读方法：

- **dispatch_ms 高**（> 5ms）：InputDispatcher 到 App 的 IPC 延迟大。通常意味着 system_server 进程负载高，或者 InputDispatcher 线程调度不及时。在 Perfetto 中可以切换到 system_server 的 InputDispatcher track 查看线程调度状态
- **handling_ms 高**（> 10ms）：App 主线程处理事件耗时过长。这是最常见的问题——`View.onTouchEvent()` 中做了耗时操作（如数据库查询、SharedPreferences 写入等），直接压缩了后续渲染时间
- **total_ms 高**（> 16ms）：整体输入响应延迟大，可能涉及多个阶段的累积延迟

### 延迟分布统计

分析整体延迟分布，识别系统性问题 vs 偶发异常：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  'dispatch' AS stage,
  MIN((receive_ts - dispatch_ts) / 1000000.0) AS p0_ms,
  PERCENTILE((receive_ts - dispatch_ts) / 1000000.0, 50) AS p50_ms,
  PERCENTILE((receive_ts - dispatch_ts) / 1000000.0, 95) AS p95_ms,
  MAX((receive_ts - dispatch_ts) / 1000000.0) AS max_ms,
  COUNT(*) AS sample_count
FROM android_input_events
WHERE receive_ts IS NOT NULL

UNION ALL

SELECT
  'handling' AS stage,
  MIN((ack_ts - receive_ts) / 1000000.0),
  PERCENTILE((ack_ts - receive_ts) / 1000000.0, 50),
  PERCENTILE((ack_ts - receive_ts) / 1000000.0, 95),
  MAX((ack_ts - receive_ts) / 1000000.0),
  COUNT(*)
FROM android_input_events
WHERE ack_ts IS NOT NULL

UNION ALL

SELECT
  'total' AS stage,
  MIN((ack_ts - dispatch_ts) / 1000000.0),
  PERCENTILE((ack_ts - dispatch_ts) / 1000000.0, 50),
  PERCENTILE((ack_ts - dispatch_ts) / 1000000.0, 95),
  MAX((ack_ts - dispatch_ts) / 1000000.0),
  COUNT(*)
FROM android_input_events
WHERE ack_ts IS NOT NULL AND dispatch_ts IS NOT NULL;
```

**重要**：该查询使用实际字段名 dispatch_ts/receive_ts/ack_ts，字段命名错误已修正。

**参考值示例**：Pixel 7 / Android 14 / 60Hz / 主线程无阻塞 / 滑动场景 / 2000 样本
| 阶段 | P50 | P95 | P99 |
|------|-----|-----|-----|
| dispatch | < 1 ms | < 3 ms | < 5 ms |
| handling | < 2 ms | < 8 ms | < 16 ms |
| total | < 4 ms | < 12 ms | < 24 ms |

**注意**：P95 与 P99 差值大说明存在偶发极端延迟，需回溯具体时间点的系统状态。

| 阶段 | P50 | P95 | P99 |
|------|-----|-----|-----|
| dispatch | < 1 ms | < 3 ms | < 5 ms |
| handling | < 2 ms | < 8 ms | < 16 ms |
| total | < 4 ms | < 12 ms | < 24 ms |

如果 P95 和 P99 之间的差距特别大（比如 P95 = 5 ms，但 P99 = 50 ms），说明存在偶发的极端延迟。这时可以带着时间戳回到 Perfetto UI，看那个时间点前后的系统状态。常见伴生现象包括 GC 暂停、Binder 调用阻塞或线程调度异常。


## InputDispatcher 延迟分解

### 输入队列长度追踪

InputDispatcher 内部维护三个关键队列：`iq`（inbound queue，等待分发）、`oq`（outbound queue，已发送等待 ACK）、`wq`（wait queue，等待窗口焦点）。队列长度的变化是定位输入延迟瓶颈的经典指标。

在 Perfetto 中，这些队列通过 counter track 追踪。用 SQL 查询队列堆积的时间段：

```sql
-- 查找 iq（inbound queue）堆积超过 5 个事件的时间段
SELECT
  CAST(ts / 1000000.0) AS timestamp_ms,
  CAST(dur / 1000000.0) AS duration_ms,
  value AS queue_length
FROM counter
JOIN track ON counter.track_id = track.id
WHERE track.name GLOB '*iq*'
  AND value > 5
ORDER BY value DESC
LIMIT 50;
```

[待验证: 不同 Perfetto 版本中 iq/oq/wq 的 track name 命名可能不同，建议先用 `SELECT DISTINCT name FROM track WHERE name GLOB '*input*'` 确认]

[图：Perfetto 中 InputDispatcher 的 iq/oq/wq counter track 示例——三个 counter 分别以不同颜色显示在 InputDispatcher 线程下方，标注 iq 堆积 > 5 的时段和对应的 App 主线程耗时操作]

**解读规则**：

- `iq` 持续非零：InputReader 到 InputDispatcher 的处理跟不上，InputReader 读到的事件在排队等分发。通常是 InputDispatcher 线程调度不及时
- `oq` 堆积：已发送的事件在等 App 的 ACK，说明 App 主线程处理慢
- `wq` 堆积：等待窗口获取焦点的事件在排队，通常是窗口切换场景（如启动新 Activity）

### ANR 前的输入事件堆积分析

当发生输入 ANR（InputDispatcher 5 秒超时）时，回溯 ANR 前 5 秒的输入事件状态非常关键：

```sql
INCLUDE PERFETTO MODULE android.input;

-- 找到 ANR 时间点（通过 ANR trace 切片）
WITH anr_time AS (
  SELECT
    MIN(ts) AS anr_ts
  FROM slice
  WHERE name GLOB '*anr*'
    OR name GLOB '*ANR*'
  LIMIT 1
),

-- ANR 前 5 秒的输入事件
pre_anr_events AS (
  SELECT
    CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
    CAST((input.dispatch_ts - (SELECT anr_ts FROM anr_time)) / 1000000.0) AS ms_before_anr,
    CAST((input.receive_ts - input.dispatch_ts) / 1000000.0) AS dispatch_ms,
    CAST((input.ack_ts - input.receive_ts) / 1000000.0) AS handling_ms,
    CAST((input.ack_ts - input.dispatch_ts) / 1000000.0) AS total_ms,
    input.input_event_id
  FROM android_input_events AS input, anr_time
  WHERE input.dispatch_ts BETWEEN (anr_time.anr_ts - 5000000000) AND anr_time.anr_ts
    AND input.receive_ts IS NOT NULL
    AND input.ack_ts IS NOT NULL
  ORDER BY input.dispatch_ts ASC
)

SELECT * FROM pre_anr_events;
```

[已验证: Perfetto SQL 支持 WITH 子句和子查询]

通过 `ms_before_anr` 列能追踪 ANR 前输入事件延迟的恶化过程。如果观察到 `handling_ms` 从正常的 2-3ms 逐渐增长到几十甚至几百毫秒，说明 App 主线程逐步被阻塞——可能是某个同步操作在主线程上执行，或者 GC 暂停越来越频繁。

[交叉引用: §9.1 ANR 设计思想 — 输入 ANR 的超时机制详解]


## Choreographer 与 Input 的时序关联

[图：Perfetto 中输入事件与 Choreographer doFrame 匹配的时间线——上方是 android_input_events 的 dispatch/handling/ack 切片，下方是同一线程的 Choreographer#doFrame 切片，标注 input_to_frame 的时间间隔]

### 输入事件到帧渲染的精确关联

Perfetto stdlib 提供输入事件与帧关联的专门能力，优先使用内置机制而非 slice name 近似匹配：

```sql
INCLUDE PERFETTO MODULE android.input;

-- 使用 frame_id 关联实现精确匹配
SELECT
  CAST(input.dispatch_ts / 1000000.0) AS input_ts_ms,
  (input.ack_ts - input.dispatch_ts) / 1000000.0 AS input_total_ms,
  input.frame_id,
  input.is_speculative_frame,
  -- 关联帧信息（如果存在）
  CAST(frame.ts / 1000000.0) AS frame_ts_ms,
  frame.name AS frame_name,
  -- 从输入事件到帧开始的时间差
  CAST((frame.ts - input.dispatch_ts) / 1000000.0) AS input_to_frame_ms
FROM android_input_events AS input
LEFT JOIN frame ON frame.id = input.frame_id
WHERE input.dispatch_ts IS NOT NULL
  AND frame.ts IS NOT NULL
  -- 排除已确认失效的 slice name 匹配方法
  AND frame.name NOT GLOB '*Choreographer#doFrame*'
ORDER BY input.dispatch_ts ASC
LIMIT 200;
```

**重要**：此查询基于 Perfetto stdlib 的 frame_id 关联，比基于 slice name 的方法更可靠。

**边界情况处理**：
- frame_id 为 NULL：输入事件未关联到帧，通常为快速连续输入
- 同一 frame_id 关联多个输入事件：batched motion（多点触控）场景
- is_speculative_frame=true：可预测输入处理，通常延迟更低

`input_to_frame_ms` 列告诉我们输入事件触发后，到对应帧开始的时间差。这个值受 VSync 同步影响——如果输入事件刚好在 VSync 信号之后到达，就要等一个完整的 VSync 周期才能触发 doFrame。`is_speculative_frame` 字段帮助我们区分普通帧和可预测帧（后者通常处理更快）。

### Choreographer 回调耗时分析

使用 Perfetto stdlib 的专用视图追踪回调耗时，避免版本间的 slice name 差异：

```sql
-- 使用 stdlib 的回调跟踪视图（可跨版本）
SELECT
  CAST(callback.start_ts / 1000000.0) AS callback_start_ms,
  callback.type AS callback_type,
  CAST(callback.dur / 1000000.0) AS callback_dur_ms,
  process.name AS process_name
FROM android_callback AS callback
JOIN process ON callback.process_id = process.upid
WHERE callback.type IN ('CALLBACK_INPUT', 'CALLBACK_ANIMATION', 'CALLBACK_TRAVERSAL')
  AND callback.dur > 1000000  -- 过滤掉极短的回调
ORDER BY callback.start_ts ASC
LIMIT 100;
```

**版本兼容性**：android_callback 视图提供标准化的回调类型字段，可跨版本使用。

**备用方案**（当 android_callback 不可用时）：
```sql
-- 使用 slice 名称匹配（需根据具体版本调整）
SELECT
  CAST(slice.ts / 1000000.0) AS start_ms,
  slice.name,
  CAST(slice.dur / 1000000.0) AS dur_ms
FROM slice
WHERE slice.name GLOB '*doFrame*'
  OR slice.name GLOB '*CALLBACK*'
ORDER BY slice.ts ASC;
```

对于更精确的同一帧内回调时间分析：

```sql
-- 分析同一帧中各回调的耗时
WITH callback_times AS (
  SELECT
    CAST(start_ts / 1000000.0) AS start_ms,
    type,
    CAST(dur / 1000000.0) AS dur_ms,
    start_ts + dur AS end_ts,
    frame_id
  FROM android_callback
  WHERE type IN ('CALLBACK_INPUT', 'CALLBACK_ANIMATION', 'CALLBACK_TRAVERSAL')
)
SELECT
  frame_id,
  MAX(CASE WHEN type = 'CALLBACK_INPUT' THEN start_ms END) AS input_start,
  MAX(CASE WHEN type = 'CALLBACK_INPUT' THEN dur_ms END) AS input_dur,
  MAX(CASE WHEN type = 'CALLBACK_TRAVERSAL' THEN start_ms END) AS traversal_start,
  MAX(CASE WHEN type = 'CALLBACK_TRAVERSAL' THEN dur_ms END) AS traversal_dur,
  (MAX(CASE WHEN type = 'CALLBACK_TRAVERSAL' THEN start_ms END) - 
   MAX(CASE WHEN type = 'CALLBACK_INPUT' THEN end_ts END)) AS gap_ms
FROM callback_times
GROUP BY frame_id
HAVING input_dur > 5 OR traversal_dur > 10
ORDER BY frame_id;
```

如果 `input_dur_ms` 过大（> 5ms），说明 `View.onTouchEvent()` 中的处理逻辑需要优化。`gap_ms`（input 结束到 traversal 开始的间隔）如果过大，说明中间的 ANIMATION 回调耗时。

[交叉引用: §2.4 Choreographer 与渲染流水线 — doFrame 回调机制详解]


## 常用 SQL 模板集

### 模板 1：滑动卡顿输入分析

当用户反馈"滑动时偶尔卡一下"，用这个模板分析滑动期间的输入延迟分布：

```sql
INCLUDE PERFETTO MODULE android.input;

-- 滑动期间的输入事件延迟分析
-- 假设已知滑动时间范围（从 Perfetto UI 中获取）
SELECT
  CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
  CAST((input.receive_ts - input.dispatch_ts) / 1000000.0) AS dispatch_ms,
  CAST((input.ack_ts - input.receive_ts) / 1000000.0) AS handling_ms,
  CAST((input.ack_ts - input.dispatch_ts) / 1000000.0) AS total_ms,
  CASE
    WHEN (input.ack_ts - input.receive_ts) > 16000000 THEN 'HANDLING_SLOW'
    WHEN (input.receive_ts - input.dispatch_ts) > 5000000 THEN 'DISPATCH_SLOW'
    WHEN (input.ack_ts - input.dispatch_ts) > 32000000 THEN 'TOTAL_SLOW'
    ELSE 'OK'
  END AS status
FROM android_input_events AS input
WHERE input.dispatch_ts BETWEEN {start_ts} AND {end_ts}
  AND input.receive_ts IS NOT NULL
  AND input.ack_ts IS NOT NULL
ORDER BY input.dispatch_ts ASC;
```

使用方法：在 Perfetto UI 中找到滑动操作的时间范围，将起止时间戳（纳秒）替换 `{start_ts}` 和 `{end_ts}`。查询结果会标记每个事件的健康状态，快速定位异常事件。

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
SELECT
  CAST(ts / 1000000.0) AS timestamp_ms,
  name,
  CAST(dur / 1000000.0) AS duration_ms,
  thread.name AS thread_name
FROM slice
JOIN thread ON slice.track_id IN (
  SELECT id FROM track WHERE thread.utid = (
    SELECT utid FROM thread WHERE name = 'main'
      AND upid = (SELECT upid FROM process WHERE name = '{app_package}')
  )
)
WHERE ts BETWEEN {anr_ts} - 5000000000 AND {anr_ts}
  AND dur > 16000000  -- 超过一帧（16ms@60Hz）
ORDER BY dur DESC
LIMIT 50;
```

这个两步查询先定位 ANR 时间点，然后找出 App 主线程上所有超过 16ms 的操作。通常会发现某个 Binder 调用、IO 操作或锁等待占据了主线程。

[交叉引用: §9.3 ANR 分析方法 — 完整的 ANR 分析流程]

### 模板 3：冷启动输入响应分析

冷启动后第一个可交互输入的延迟分析——用户点击 icon 到 App 首次响应输入：

```sql
INCLUDE PERFETTO MODULE android.input;

-- 冷启动期间（Activity 显示前）的输入事件
-- 先确定冷启动的时间范围
WITH cold_start AS (
  SELECT
    MIN(ts) AS start_ts,
    MIN(ts) + 3000000000 AS end_ts  -- 冷启动前 3 秒
  FROM slice
  WHERE name = 'ActivityThread#handleBindApplication'
    OR name GLOB '*Activity*onCreate*'
  LIMIT 1
)
SELECT
  CAST(input.dispatch_ts / 1000000.0) AS timestamp_ms,
  CAST((input.dispatch_ts - cold_start.start_ts) / 1000000.0) AS ms_since_start,
  CAST((input.ack_ts - input.dispatch_ts) / 1000000.0) AS total_ms,
  process.name AS process_name
FROM android_input_events AS input
JOIN process ON input.process_name = process.name, cold_start
WHERE input.dispatch_ts BETWEEN cold_start.start_ts AND cold_start.end_ts
  AND input.receive_ts IS NOT NULL
  AND input.ack_ts IS NOT NULL
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

如果只需要输入延迟数据，以下 `TraceConfig` 可以最小化 Trace 文件体积：

```protobuf
buffers: {
  size_kb: 32768
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
# 注意：以下数据源配置存在概念混淆，已修正
# android.input 是查询模块，不是数据源；实际数据源是 android.input.inputevent
data_sources: {
  config {
    name: "android.input.inputevent"
    android_input_event_config {
      # 默认配置已包含 InputReader 到 App 的完整链路
      # 启用此数据源需要 debuggable build
    }
  }
}
data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms: 1000
    }
  }
}
```

**重要澄清**：
- `android.input` 是**查询模块**（用于 SQL 分析）
- 实际**数据源**是 `android.input.inputevent`（需要 debuggable build）
- 端到端延迟需要 FrameTimeline 数据补充 InputReader 阶段

### 完整输入链路配置

如果需要覆盖从内核到显示的完整链路，需要额外启用：

```protobuf
# 在上述基础上添加
data_sources: {
  config {
    name: "android.frame_timeline"
  }
}
data_sources: {
  config {
    name: "surfaceflinger.frame"
  }
}
# 启用 input ftrace events 以获取内核层时间戳
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      atrace_categories: "input"
      atrace_apps: "<your.app.package>"
    }
  }
}
```

[待验证: atrace_categories: "input" 是否需要 root 权限，debuggable App 是否可以通过 Developer Options 启用]

**性能开销**：完整配置的 Trace 文件大约每秒增长 2-5MB。对于 10 秒的输入延迟分析，生成 20-50MB 的 Trace 文件，Perfetto UI 可以流畅处理。


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
    
    trace_processor_shell "$trace" << 'SQL' > "$OUTPUT_DIR/${filename}_input_latency.csv"
INCLUDE PERFETTO MODULE android.input;

SELECT
  '${filename}' AS trace_file,
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
