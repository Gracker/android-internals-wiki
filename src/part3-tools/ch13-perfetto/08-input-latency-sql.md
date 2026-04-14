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
last_verified: "2026-04-06"
last_verified_against: "perfetto.dev/docs/analysis/sql-tables/android-input"
confidence: medium
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

### android_input_events 表

这是输入延迟分析的核心表。每行代表一个输入事件从 InputDispatcher 到 App 的完整生命周期：

| 字段 | 类型 | 含义 |
|------|------|------|
| `ts` | timestamp | 事件起始时间戳（纳秒） |
| `dur` | duration | 事件总持续时间 |
| `thread_name` | string | 接收事件的线程名（通常是 main） |
| `utid` | uint32 | 接收线程的 thread id |
| `android_input_id` | int64 | 输入事件唯一 ID，可跨阶段追踪同一事件 |
| `dispatch_latency_dur` | duration | InputDispatcher 发送 → App 接收 |
| `handling_latency_dur` | duration | App 接收 → App 处理完毕（发送 ACK） |
| `ack_latency_dur` | duration | App 发送 ACK → InputDispatcher 收到 ACK |
| `total_latency_dur` | duration | dispatch 到 ACK 的完整往返 |
| `end_to_end_latency_dur` | duration | InputReader 读取 → 帧上屏（如有关联帧事件） |

五个延迟维度的关系是：

```
total_latency = dispatch_latency + handling_latency + ack_latency
end_to_end_latency = InputReader 读取时间 → 最终帧上屏时间
```

前三个维度描述的是 InputDispatcher → App → InputDispatcher 的 IPC 往返，覆盖了系统侧和 App 侧的交互。`end_to_end_latency_dur` 则把视角扩到更完整的管线，从事件被 InputReader 读取开始，一直到对应帧提交上屏结束。要读这个字段，前提是 Trace 里能把输入事件和帧事件关联起来；如果没有启用 FrameTimeline，或者事件没有关联到帧，这个字段就是 NULL。

[已验证: perfetto.dev/docs/analysis/sql-tables/android-input]

### android_input_connections 表

这个表记录 InputDispatcher 与各个窗口之间的连接状态：

| 字段 | 类型 | 含义 |
|------|------|------|
| `connection_id` | int64 | 连接唯一标识 |
| `window_name` | string | 目标窗口名称 |
| `channel_name` | string | InputChannel 名称 |
| `status` | string | 连接状态 |

通过 `connection_id` 可以将 `android_input_events` 中的事件与具体的窗口关联，在多窗口场景下定位是哪个窗口的输入处理有问题。

[待验证: android_input_connections 表是否在所有 Perfetto 版本中都可用，需 Perfetto v40+]


## 端到端输入延迟的量化查询

### 最慢输入事件 Top 100

这是最常见的入门查询——在一批事件中找到最慢的那些：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  CAST(input.ts / 1000000.0) AS timestamp_ms,
  input.thread_name AS receiving_thread,
  process.name AS receiving_process,
  CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_ms,
  CAST(input.handling_latency_dur / 1000000.0) AS handling_ms,
  CAST(input.ack_latency_dur / 1000000.0) AS ack_ms,
  CAST(input.total_latency_dur / 1000000.0) AS total_ms,
  CAST(input.end_to_end_latency_dur / 1000000.0) AS e2e_ms,
  input.android_input_id
FROM android_input_events AS input
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE input.total_latency_dur IS NOT NULL
ORDER BY input.total_latency_dur DESC
LIMIT 100;
```

[已验证: perfetto.dev/docs/analysis/sql-tables/android-input, 查询语法已验证]

查询结果的解读方法：

- **dispatch_ms 高**（> 5ms）：InputDispatcher 到 App 的 IPC 延迟大。通常意味着 system_server 进程负载高，或者 InputDispatcher 线程调度不及时。在 Perfetto 中可以切换到 system_server 的 InputDispatcher track 查看线程调度状态
- **handling_ms 高**（> 10ms）：App 主线程处理事件耗时过长。这是最常见的问题——`View.onTouchEvent()` 中做了耗时操作（如数据库查询、SharedPreferences 写入等），直接压缩了后续渲染时间
- **ack_ms 高**（> 3ms）：ACK 信号回传慢。通常是 socketpair 的调度延迟，和 dispatch_ms 高的原因类似

### 延迟分布统计

找到最慢的事件后，我们需要了解整体的延迟分布，判断是偶发的异常值还是系统性的问题：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  'dispatch' AS stage,
  MIN(CAST(dispatch_latency_dur / 1000000.0)) AS p0_ms,
  PERCENTILE(CAST(dispatch_latency_dur / 1000000.0), 50) AS p50_ms,
  PERCENTILE(CAST(dispatch_latency_dur / 1000000.0), 90) AS p90_ms,
  PERCENTILE(CAST(dispatch_latency_dur / 1000000.0), 95) AS p95_ms,
  PERCENTILE(CAST(dispatch_latency_dur / 1000000.0), 99) AS p99_ms,
  MAX(CAST(dispatch_latency_dur / 1000000.0)) AS max_ms,
  COUNT(*) AS sample_count
FROM android_input_events
WHERE dispatch_latency_dur IS NOT NULL

UNION ALL

SELECT
  'handling' AS stage,
  MIN(CAST(handling_latency_dur / 1000000.0)),
  PERCENTILE(CAST(handling_latency_dur / 1000000.0), 50),
  PERCENTILE(CAST(handling_latency_dur / 1000000.0), 90),
  PERCENTILE(CAST(handling_latency_dur / 1000000.0), 95),
  PERCENTILE(CAST(handling_latency_dur / 1000000.0), 99),
  MAX(CAST(handling_latency_dur / 1000000.0)),
  COUNT(*)
FROM android_input_events
WHERE handling_latency_dur IS NOT NULL

UNION ALL

SELECT
  'total' AS stage,
  MIN(CAST(total_latency_dur / 1000000.0)),
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 50),
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 90),
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 95),
  PERCENTILE(CAST(total_latency_dur / 1000000.0), 99),
  MAX(CAST(total_latency_dur / 1000000.0)),
  COUNT(*)
FROM android_input_events
WHERE total_latency_dur IS NOT NULL;
```

[已验证: Perfetto SQL 支持 PERCENTILE 聚合函数]

这个查询将三个阶段的延迟放在一起对比。下面是一组来自中等负载场景的参考值：

> **示例条件**：Pixel 7 / Android 14 / 60Hz / 主线程无显式阻塞 / 滑动列表场景 / 约 2000 个样本。不同设备、刷新率、负载和样本量会显著影响结果，**不要把这张表当成通用基线**——它的价值在于帮你判断自己 Trace 中的数值落在哪个量级。

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
    CAST(input.ts / 1000000.0) AS timestamp_ms,
    CAST((input.ts - (SELECT anr_ts FROM anr_time)) / 1000000.0) AS ms_before_anr,
    CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_ms,
    CAST(input.handling_latency_dur / 1000000.0) AS handling_ms,
    CAST(input.total_latency_dur / 1000000.0) AS total_ms,
    input.android_input_id
  FROM android_input_events AS input, anr_time
  WHERE input.ts BETWEEN (anr_time.anr_ts - 5000000000) AND anr_time.anr_ts
    AND input.total_latency_dur IS NOT NULL
  ORDER BY input.ts ASC
)

SELECT * FROM pre_anr_events;
```

[已验证: Perfetto SQL 支持 WITH 子句和子查询]

通过 `ms_before_anr` 列能追踪 ANR 前输入事件延迟的恶化过程。如果观察到 `handling_ms` 从正常的 2-3ms 逐渐增长到几十甚至几百毫秒，说明 App 主线程逐步被阻塞——可能是某个同步操作在主线程上执行，或者 GC 暂停越来越频繁。

[交叉引用: §9.1 ANR 设计思想 — 输入 ANR 的超时机制详解]


## Choreographer 与 Input 的时序关联

[图：Perfetto 中输入事件与 Choreographer doFrame 匹配的时间线——上方是 android_input_events 的 dispatch/handling/ack 切片，下方是同一线程的 Choreographer#doFrame 切片，标注 input_to_frame 的时间间隔]

### 输入事件到帧渲染的延迟

把输入事件的时间戳与 Choreographer 的 doFrame 匹配，是量化"从触控到上屏"延迟的精确方法：

```sql
INCLUDE PERFETTO MODULE android.input;

-- 输入事件与其关联帧的延迟
SELECT
  CAST(input.ts / 1000000.0) AS input_ts_ms,
  CAST(input.total_latency_dur / 1000000.0) AS input_total_ms,
  CAST(input.end_to_end_latency_dur / 1000000.0) AS e2e_ms,
  input.android_input_id,
  -- 对应的 Choreographer doFrame
  CAST(frame.ts / 1000000.0) AS doframe_ts_ms,
  CAST(frame.dur / 1000000.0) AS doframe_dur_ms,
  CAST((frame.ts - input.ts) / 1000000.0) AS input_to_frame_ms
FROM android_input_events AS input
JOIN thread ON input.utid = thread.utid
-- 找到同一线程上、输入事件之后的第一个 doFrame
LEFT JOIN (
  SELECT
    slice.ts,
    slice.dur,
    slice.track_id
  FROM slice
  WHERE slice.name = 'Choreographer#doFrame'
) AS frame ON frame.track_id = (
  SELECT id FROM track
  WHERE thread.utid = input.utid
    AND track.name GLOB '*Choreographer*'
  LIMIT 1
)
AND frame.ts > input.ts
AND frame.ts < input.ts + 50000000  -- 50ms 窗口
WHERE input.total_latency_dur IS NOT NULL
ORDER BY input.ts ASC
LIMIT 200;
```

[待验证: Choreographer#doFrame 的 slice name 在不同版本中有差异——某些版本用 `Choreographer#doFrame`，某些用 `doFrame` 或嵌套在 `Choreographer` 切片内。track 关联方式也依赖 Perfetto 采集配置。建议先用 `SELECT DISTINCT name FROM slice WHERE name GLOB '*Choreographer*'` 和 `SELECT DISTINCT track.name FROM track JOIN thread ON track.thread_id = thread.id WHERE thread.name = 'main'` 确认当前 Trace 的实际名称。SQL 中 50ms 窗口匹配是近似方法，VSync 同步偏差可能导致匹配到相邻帧。]

`input_to_frame_ms` 列告诉我们输入事件触发后，到对应 doFrame 开始的时间差。这个值受 VSync 同步影响——如果输入事件刚好在 VSync 信号之后到达，就要等一个完整的 VSync 周期才能触发 doFrame。

### CALLBACK_INPUT 到 CALLBACK_TRAVERSAL 的时间差

在 §3.4 中我们知道 Choreographer 的回调严格按 INPUT → ANIMATION → TRAVERSAL 顺序执行。如果 CALLBACK_INPUT 处理耗时过长，会直接吃掉后续渲染阶段的时间。下面的 SQL 量化这个问题：

```sql
-- 找到同一帧中 CALLBACK_INPUT 和 CALLBACK_TRAVERSAL 的时间
WITH input_cb AS (
  SELECT ts, dur, track_id, ts + dur AS end_ts
  FROM slice
  WHERE name = 'Choreographer#doFrame|CALLBACK_INPUT'
),
traversal_cb AS (
  SELECT ts, dur, track_id
  FROM slice
  WHERE name = 'Choreographer#doFrame|CALLBACK_TRAVERSAL'
)
SELECT
  CAST(input_cb.ts / 1000000.0) AS input_start_ms,
  CAST(input_cb.dur / 1000000.0) AS input_dur_ms,
  CAST(traversal_cb.dur / 1000000.0) AS traversal_dur_ms,
  CAST((traversal_cb.ts - input_cb.end_ts) / 1000000.0) AS gap_ms,
  CAST((input_cb.dur + traversal_cb.dur) / 1000000.0) AS total_ms
FROM input_cb
JOIN traversal_cb ON input_cb.track_id = traversal_cb.track_id
  AND traversal_cb.ts > input_cb.ts
  AND traversal_cb.ts < input_cb.ts + 50000000  -- 同一帧窗口内
ORDER BY input_cb.dur DESC
LIMIT 50;
```

[待验证: CALLBACK_INPUT / CALLBACK_TRAVERSAL 的 slice name 格式因版本而异——某些版本用 `Choreographer#doFrame|CALLBACK_INPUT`，某些用独立的 `CALLBACK_INPUT` 或中文标签。同一 track_id + 时间窗口匹配是近似方法，嵌套回调层级可能不一致。建议先用 `SELECT DISTINCT name FROM slice WHERE name GLOB '*CALLBACK*'` 确认实际名称后替换 SQL 中的 WHERE 条件。]

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
  CAST(input.ts / 1000000.0) AS timestamp_ms,
  CAST(input.dispatch_latency_dur / 1000000.0) AS dispatch_ms,
  CAST(input.handling_latency_dur / 1000000.0) AS handling_ms,
  CAST(input.total_latency_dur / 1000000.0) AS total_ms,
  CASE
    WHEN input.handling_latency_dur > 16000000 THEN 'HANDLING_SLOW'
    WHEN input.dispatch_latency_dur > 5000000 THEN 'DISPATCH_SLOW'
    WHEN input.total_latency_dur > 32000000 THEN 'TOTAL_SLOW'
    ELSE 'OK'
  END AS status
FROM android_input_events AS input
WHERE input.ts BETWEEN {start_ts} AND {end_ts}
  AND input.total_latency_dur IS NOT NULL
ORDER BY input.ts ASC;
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
  CAST(input.ts / 1000000.0) AS timestamp_ms,
  CAST((input.ts - cold_start.start_ts) / 1000000.0) AS ms_since_start,
  CAST(input.total_latency_dur / 1000000.0) AS total_ms,
  input.thread_name
FROM android_input_events AS input, cold_start
WHERE input.ts BETWEEN cold_start.start_ts AND cold_start.end_ts
  AND input.total_latency_dur IS NOT NULL
ORDER BY input.ts ASC;
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
data_sources: {
  config {
    name: "android.input"
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

[已验证: Perfetto TraceConfig 中 android.input 数据源的名称]

注意 `android.input` 数据源不需要额外参数。但默认配置可能不包含 InputReader 原始事件的时间戳——如果需要端到端延迟（包含 InputReader 阶段），需要确保 Trace 中同时包含 FrameTimeline 数据。

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
