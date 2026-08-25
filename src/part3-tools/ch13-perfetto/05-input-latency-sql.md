---
title: Perfetto 输入延迟 SQL 深度分析
chapter: '13.5'
section: '13.5'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-08-13'
last_verified_against: Android 17 / android-17.0.0_r1 Perfetto ece66975738007dd0978b911d8a2077e49b8f31e + frameworks/native ae266dcb706d083868578cfedce381ef44488a07; Perfetto v57.2-da1d152cf stdlib docs; android17-6.18-2026-06_r6
confidence: high
sources:
- type: official
  path: https://perfetto.dev/docs/analysis/sql-tables/android-input
- type: official
  path: https://perfetto.dev/docs/analysis/trace-processor
- type: research
  path: intake/research-feeds/2026-04-05-15-input-pipeline-latency-breakdown.md
tags:
- Perfetto
- SQL
- input-latency
- android.input
- input-events
- trace-analysis
related_chapters:
- '3.1'
- '3.2'
- '13.2'
- '13.7'
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
---

# Perfetto 输入延迟 SQL 深度分析

输入延迟 SQL 的关键不是拼出一张大表，而是先选定事件身份、时间窗口和终点语义。只有把 InputDispatcher 队列、应用消费与 FrameTimeline 的 token 关系对齐，计算出的 input-to-display 延迟才可复查。

## 分析边界与源码基线

输入延迟排障常遇到三类问题：慢事件藏在大量正常样本中、ANR（Application Not Responding，应用无响应）发生前的队列状态不清楚、一次输入究竟关联了哪一帧。时间线界面适合观察单个现场，SQL 更适合筛选异常样本、计算分位数和复用判定逻辑。分位数描述样本排序后的位置，例如 P50 是中位数，P95 表示约 95% 的样本不高于该值。

本文核对的平台源码基线是 Android 17 / API 37 / `android-17.0.0_r1`。Perfetto 对应提交为 `ece66975738007dd0978b911d8a2077e49b8f31e`，`frameworks/native` 对应提交为 `ae266dcb706d083868578cfedce381ef44488a07`。调度事件的内核语义以 `android17-6.18-2026-06_r6` 为准。Perfetto 标准库还可以由较新的 Trace Processor 提供，因此分析报告需要同时记录系统版本、采集配置和 Trace Processor 版本。

`InputReader` 从 Linux 输入设备读取并解释事件，`InputDispatcher` 决定事件要投递给哪些窗口，应用处理完后通过输入通道返回 `FINISHED` 确认。SurfaceFlinger 是 Android 的显示合成服务，FrameTimeline 记录应用帧与合成帧的预期和实际时间。分析需要区分三段时间：

- 输入事件的语义时间戳到 `InputReader` 读取；语义时间戳表示事件自身携带的发生时刻，不等同于 Trace 记录写入时刻；
- `InputDispatcher` 发出消息到应用完成并返回 `FINISHED`；
- `InputReader` 读取到关联帧在 `SurfaceFlinger FrameTimeline` 中结束。

三段数据的来源和缺失条件不同。没有帧关联时，输入往返时间仍可能完整；没有完整的发送、接收和确认切片时，`android_input_events` 不会生成该行。分析时要把“没有记录”与“耗时为零”分开。

## `android.input` 中的两条数据链路

### 生命周期与帧关联

`android_input_events` 由 ATrace（Android 代码埋点形成的时间片）和 FrameTimeline 派生。Android 17 的 `android/input.sql` 会解析下列信息：

- `sendMessage(...)` 与 `receiveMessage(...)`：建立 `InputDispatcher`、应用接收、应用发送确认、系统收到确认四个节点；
- `UnwantedInteractionBlocker::notifyMotion(...)`：取得 `input_event_id`、`event_time` 和 `read_time`；
- `deliverInputEvent src=...` 与 `Choreographer#doFrame`：建立输入与应用帧的关联；
- `actual_frame_timeline_slice`：把应用帧映射到 `SurfaceFlinger` 帧，并取得呈现时间。

这条链路不依赖 `android.input.inputevent` 调试数据源。常规 `user` 量产构建也可以采集所需的 ATrace 与 FrameTimeline，但采集配置必须包含 `input`、`view`、`gfx` 类别、目标应用和 FrameTimeline 数据源。

下面这条查询用于确认标准库对象能够加载，并快速观察当前跟踪的覆盖率：

```sql
INCLUDE PERFETTO MODULE android.input;

SELECT
  COUNT(*) AS event_count,
  SUM(read_time IS NOT NULL) AS with_read_time,
  SUM(frame_id IS NOT NULL) AS with_frame,
  SUM(is_speculative_frame = 1) AS speculative_frame_count,
  SUM(end_to_end_latency_dur IS NOT NULL) AS with_end_to_end_latency
FROM android_input_events;
```

这里的覆盖率指有多少输入行同时具备读取时间、帧关联或端到端延迟。结果全为零时，应先检查采集配置和场景是否产生输入，不能据此判断输入很快。`NULL` 表示字段缺失，不代表耗时为零；`with_frame` 明显少于 `event_count` 时，需要核对 FrameTimeline、应用 ATrace 和场景结束位置是否完整。

### 调试级原始事件

`android_motion_events`、`android_key_events` 与 `android_input_event_dispatch` 来自 `android.input.inputevent`。Android 17 的配置协议明确限制该数据源只能用于 `userdebug` 或 `eng` 调试构建，不能在普通 `user` 量产构建上启用。它记录 `InputDispatcher` 处理的原始事件字段和窗口分发决策，适合回答事件来源、动作、设备、窗口及隐私规则是否生效等问题。

两条链路不能当作同一张表拆分后的结果。原始视图使用数值型 `event_id`；生命周期表的 `input_event_id` 来自 ATrace 名称，通常是带 `0x` 等表示方式的十六进制文本。标准库没有公开、稳定的桥接视图。原始事件与窗口分发可以用同为数值型的 `event_id` 关联，跨到 `android_input_events` 时应回到同一事件的时间线和源码格式核验；直接用 `CAST` 转换类型后做等值连接，可能把格式差异或 ID 碰撞误当成同一事件。

这条查询展示原始动作事件、内核事件时间和窗口分发的一对多关系：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE time.conversion;

SELECT
  event.event_id,
  time_to_ms(event.ts) AS dispatcher_processed_at_ms,
  time_to_ms(EXTRACT_ARG(event.arg_set_id, 'kernel_time')) AS kernel_event_at_ms,
  event.source,
  event.action,
  event.device_id,
  event.display_id,
  dispatch.vsync_id,
  dispatch.window_id
FROM android_motion_events AS event
LEFT JOIN android_input_event_dispatch AS dispatch
  USING (event_id)
ORDER BY event.ts, dispatch.window_id
LIMIT 200;
```

`EXTRACT_ARG` 从 `arg_set_id` 对应的键值参数集中读取 `kernel_time`。同一事件可能投递给前台窗口、监视窗口或其他目标，因此结果出现多行并非重复数据。解析器会把协议消息中单调时钟域的 `event_time_nanos` 转为 Trace 时间域；单调时钟只持续向前，不受墙上时间校准影响。转换后的值以 `kernel_time` 写入 `args`，原始表的 `ts` 则是系统处理该 Trace 数据包的时间。

## 公共表结构与延迟公式

### `android_input_events`

每一行表示一个已经匹配到完整消息往返的输入投递。Android 17 的公开字段可以按用途分成四组：

| 分组 | 字段 | 含义 |
|---|---|---|
| 往返延迟 | `dispatch_latency_dur` | InputDispatcher 发出事件到应用收到事件 |
| 往返延迟 | `handling_latency_dur` | 应用收到事件到应用发送 `FINISHED` |
| 往返延迟 | `ack_latency_dur` | 应用发送 `FINISHED` 到 InputDispatcher 收到确认 |
| 往返延迟 | `total_latency_dur` | InputDispatcher 发出事件到系统收到确认 |
| 呈现延迟 | `end_to_end_latency_dur` | InputReader 读取到关联帧呈现；无关联帧时为 `NULL` |
| 接收端 | `tid`, `thread_name`, `upid`, `pid`, `process_name` | 处理投递的线程与进程 |
| 事件 | `event_type`, `event_action`, `event_seq` | 消息类型、动作及通道内递增的文本序号 |
| 通道 | `event_channel`, `normalized_event_channel` | 原始通道名与标准库归一化结果 |
| 输入锚点 | `input_event_id`, `read_time`, `event_time` | 事件标识、InputReader 读取时间、事件发生时间 |
| 投递切片 | `dispatch_track_id`, `dispatch_ts`, `dispatch_dur` | InputDispatcher 侧切片 |
| 接收切片 | `receive_track_id`, `receive_ts`, `receive_dur` | 应用接收侧切片 |
| 帧关联 | `frame_id`, `is_speculative_frame` | 关联帧的 Vsync ID 与是否为推测关联 |

`tid` 和 `pid` 是操作系统线程号与进程号，`upid` 是 Perfetto 在当前 Trace 内分配的进程唯一标识，可区分 PID 被系统复用后的不同实例。Vsync ID 是一次垂直同步周期的标识。`normalized_event_channel` 会按 Android 17 标准库规则去掉部分对象前缀、冒号后缀或末尾数字，便于分组；它不是跨版本稳定的连接 ID。

四段消息节点的计算关系如下：

| 指标 | 计算式 |
|---|---|
| `dispatch_latency_dur` | `receive.ts - dispatch.ts` |
| `handling_latency_dur` | `finish.ts - receive.ts` |
| `ack_latency_dur` | `finish_ack.ts - finish.ts` |
| `total_latency_dur` | `finish_ack.ts - dispatch.ts` |

输入传输使用基于 socket 的输入通道，ACK 是 acknowledgment（确认消息）的缩写。`ack_latency_dur` 不是 Binder（Android 进程间通信机制）往返耗时；将它归因于 Binder 拥塞会把排查方向带偏。应用收到事件后，`handling_latency_dur` 也可能覆盖输入批处理和框架分发开销，不能直接等同于某个业务回调的执行时间。

### 三张原始视图

原始视图的公开列在 Android 17 中保持紧凑，复杂 protobuf 消息字段通过 `arg_set_id` 对应的参数集查询：

| 视图 | 公开列 | 用途 |
|---|---|---|
| `android_motion_events` | `id`, `event_id`, `ts`, `arg_set_id`, `source`, `action`, `device_id`, `display_id` | MotionEvent 元信息及参数 |
| `android_key_events` | 上述字段加 `key_code` | KeyEvent 元信息及按键码 |
| `android_input_event_dispatch` | `id`, `event_id`, `arg_set_id`, `vsync_id`, `window_id` | 事件到窗口的分发决策 |

坐标、指针轴、策略标志、`down_time` 和 `kernel_time` 等字段保存在 `args`。字段是否存在还受脱敏等级影响；脱敏会省略敏感字段，因此查询必须允许 `NULL`。

## 输入往返延迟

### 找出慢样本

下面的查询把目标进程写在单行参数中，并按总往返时间列出最慢样本：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE time.conversion;

WITH params(process_name) AS (
  VALUES ('com.example.reader')
)
SELECT
  time_to_ms(event.dispatch_ts) AS dispatch_at_ms,
  event.input_event_id,
  event.event_action,
  event.thread_name,
  event.normalized_event_channel,
  time_to_ms(event.dispatch_latency_dur) AS dispatch_ms,
  time_to_ms(event.handling_latency_dur) AS handling_ms,
  time_to_ms(event.ack_latency_dur) AS ack_ms,
  time_to_ms(event.total_latency_dur) AS total_ms
FROM android_input_events AS event
JOIN params
  USING (process_name)
ORDER BY event.total_latency_dur DESC
LIMIT 100;
```

使用时只需修改 `VALUES` 中的进程名。`dispatch_ms` 高时检查 `InputDispatcher` 与目标线程的可运行、运行和睡眠状态；`handling_ms` 高时展开应用接收线程；`ack_ms` 高时检查应用发出确认后的调度与输入通道路径。单个分段偏高只能提供排查入口，不能独立证明根因。

### 建立同场景分布

这条查询为四个分段计算 P50、P95、P99、最大值和样本量。P95、P99 用来观察最慢的 5% 和 1% 尾部样本，必须与 `sample_count` 一起解读：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE time.conversion;

WITH params(process_name) AS (
  VALUES ('com.example.reader')
),
samples(stage, dur) AS (
  SELECT 'dispatch', dispatch_latency_dur
  FROM android_input_events JOIN params USING (process_name)
  UNION ALL
  SELECT 'handling', handling_latency_dur
  FROM android_input_events JOIN params USING (process_name)
  UNION ALL
  SELECT 'ack', ack_latency_dur
  FROM android_input_events JOIN params USING (process_name)
  UNION ALL
  SELECT 'total', total_latency_dur
  FROM android_input_events JOIN params USING (process_name)
)
SELECT
  stage,
  COUNT(*) AS sample_count,
  time_to_ms(PERCENTILE(dur, 50)) AS p50_ms,
  time_to_ms(PERCENTILE(dur, 95)) AS p95_ms,
  time_to_ms(PERCENTILE(dur, 99)) AS p99_ms,
  time_to_ms(MAX(dur)) AS max_ms
FROM samples
WHERE dur IS NOT NULL
GROUP BY stage
ORDER BY CASE stage
  WHEN 'dispatch' THEN 1
  WHEN 'handling' THEN 2
  WHEN 'ack' THEN 3
  ELSE 4
END;
```

输入延迟没有脱离设备、刷新率、手势类型和负载的通用毫秒阈值。可靠的性能回退判定应固定设备、构建、Trace 配置、交互脚本、温度区间和样本量，再比较分位数及尾部样本。最大值对单次调度抖动很敏感，不适合单独作为门禁；门禁是持续集成中自动决定构建是否通过的规则。

## 从事件发生到帧呈现

### 三段时间的组合

`end_to_end_latency_dur` 在 Android 17 标准库中的定义是 `present_time - read_time`。若 `event_time` 可用，可以再计算事件发生到 `InputReader` 读取，以及事件发生到关联帧呈现：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE time.conversion;

SELECT
  input_event_id,
  process_name,
  event_action,
  time_to_ms(read_time - event_time) AS event_to_read_ms,
  time_to_ms(end_to_end_latency_dur) AS read_to_present_ms,
  time_to_ms(
    (read_time - event_time) + end_to_end_latency_dur
  ) AS event_to_present_ms,
  frame_id,
  is_speculative_frame
FROM android_input_events
WHERE event_time IS NOT NULL
  AND read_time IS NOT NULL
  AND end_to_end_latency_dur IS NOT NULL
ORDER BY event_to_present_ms DESC
LIMIT 100;
```

这里的 `event_time` 是输入事件携带并由 `InputReader` 的 ATrace 输出的事件时间，不是原始 evdev（Linux 输入设备事件接口）上的 Tracepoint（内核预定义事件记录点）。它比 `dispatch_ts` 更靠近设备事件，但仍不能描述成触摸控制器中断时间。FrameTimeline 的呈现时间是 SurfaceFlinger 帧区间的结束，不代表屏幕像素实际发光的物理时刻。

### 输入与 `doFrame` 的关联规则

标准库会在同一应用线程上查找与 `deliverInputEvent` 区间相交的 `Choreographer#doFrame`。找到交集时标记为精确关联；没有交集时，选择该线程上紧随其后的帧并标记 `is_speculative_frame = 1`。这里的“精确”只表示两个区间按规则相交，不自动证明业务因果。映射到 SurfaceFlinger 后，标准库还会选择不早于关联应用帧的首个未丢弃帧。

这些规则带来三个限制：

- 推测关联只说明时间上最接近，不能证明该输入触发了该帧；
- 被丢弃的应用帧可能使 `frame_id` 指向后续未丢弃帧；
- 一个帧可合并多个 MOVE 事件，输入行与帧不是一一关系。

Android 17 的 `_input_read_time` 只匹配 motion 事件的 `UnwantedInteractionBlocker::notifyMotion*` Slice，按键事件可以有完整往返时间，却没有 `read_time`、`event_time` 或呈现延迟。以下划线开头表示标准库内部对象，外部查询不应依赖它。该版本选择未丢弃帧的内部标量查询（预期返回单个值的子查询）也没有显式增加 `upid` 条件；多应用同时绘制时，应把 `frame_id` 当作候选锚点，并用目标进程再次校验。

下面的查询把输入结果连接到 `android_frames`，同时保留关联质量：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE time.conversion;

SELECT
  event.input_event_id,
  event.process_name,
  event.frame_id,
  event.is_speculative_frame,
  time_to_ms(event.dispatch_ts) AS dispatch_at_ms,
  time_to_ms(frame.ts) AS do_frame_at_ms,
  time_to_ms(frame.dur) AS frame_dur_ms,
  frame.do_frame_id,
  frame.draw_frame_id
FROM android_input_events AS event
JOIN android_frames AS frame
  ON frame.frame_id = event.frame_id
  AND frame.upid = event.upid
WHERE event.frame_id IS NOT NULL
ORDER BY event.dispatch_ts
LIMIT 200;
```

同时使用 `frame_id` 和 `upid` 可以避开不同进程复用 Vsync ID 造成的误连接。帧持续时间长不等于输入处理慢，仍需展开 `doFrame`、负责渲染提交的 `RenderThread`、SurfaceFlinger 和调度上下文。

### 展开 `doFrame` 的全部后代切片

直接连接 `slice.parent_id = do_frame_id` 只能看到第一层子切片。定位输入、动画或遍历阶段时，应遍历完整的切片子树。下面的参数行选择一个应用和帧 ID：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE time.conversion;

WITH params(process_name, frame_id) AS (
  VALUES ('com.example.reader', 123456)
)
SELECT
  frame.frame_id,
  slice.name,
  slice.depth,
  time_to_ms(slice.ts) AS start_ms,
  time_to_ms(slice.dur) AS dur_ms
FROM android_frames AS frame
JOIN params
  USING (process_name, frame_id)
JOIN descendant_slice(frame.do_frame_id) AS descendant
JOIN slice
  ON slice.id = descendant.id
ORDER BY slice.ts, slice.depth;
```

`descendant_slice()` 是递归遍历 Slice 父子关系的表函数。修改参数行后，查询会返回 `doFrame` 下所有层级的后代 Slice；具体回调名称受系统版本、应用埋点和采集类别影响，应先查看完整结果，再筛选当前 Trace 中存在的名称。

## `InputDispatcher` 的 `iq`、`oq` 与 `wq`

`InputDispatcher` 运行在承载 Android 核心系统服务的 `system_server` 进程中。Android 17 的 `InputDispatcher.cpp` 直接用 ATrace 计数器记录三类队列：

- `iq`（inbound queue）：`InputDispatcher` 尚未处理的全局入站队列；
- `oq:<channel>`（outbound queue）：每条连接上等待写入应用输入通道的出站队列；
- `wq:<channel>`（wait queue）：已经写给应用、仍等待 `FINISHED` 确认的队列。

这里的 channel 是 InputDispatcher 与一个输入目标之间的连接。源码中的计数器名称缓冲区长度为 40 字节，过长的通道名可能被截断。查询应使用 `oq:`、`wq:` 前缀，并在需要时结合目标时间和进程现场定位连接。

这条查询用于确认当前跟踪中存在的 `InputDispatcher` 计数器：

```sql
INCLUDE PERFETTO MODULE time.conversion;

SELECT
  process.name AS process_name,
  track.name AS queue_name,
  time_to_ms(counter.ts) AS sample_at_ms,
  counter.value AS queue_length
FROM counter
JOIN process_counter_track AS track
  ON track.id = counter.track_id
JOIN process
  USING (upid)
WHERE process.name = 'system_server'
  AND (
    track.name = 'iq'
    OR track.name GLOB 'oq:*'
    OR track.name GLOB 'wq:*'
  )
ORDER BY counter.ts, track.name
LIMIT 500;
```

`GLOB 'oq:*'` 和 `GLOB 'wq:*'` 使用通配符匹配对应前缀。如果没有结果，检查 `linux.ftrace` 是否启用了 ATrace 的 `input` 类别。旧文档中常见的 `InputDispatcher inbound queue` 等名称并不是 Android 17 源码写出的计数器名称。

`counter` 只在值变化时记录采样点，没有 `dur`；一个值会持续到同轨道的下一次采样。下面的查询用下一次采样或 Trace 结束时间补出每段持续时间，并列出非零区间：

```sql
INCLUDE PERFETTO MODULE time.conversion;

WITH queue_samples AS (
  SELECT
    counter.track_id,
    track.name AS queue_name,
    counter.ts,
    counter.value AS queue_length,
    LEAD(counter.ts) OVER (
      PARTITION BY counter.track_id
      ORDER BY counter.ts
    ) AS next_ts
  FROM counter
  JOIN process_counter_track AS track
    ON track.id = counter.track_id
  JOIN process
    USING (upid)
  WHERE process.name = 'system_server'
    AND (
      track.name = 'iq'
      OR track.name GLOB 'oq:*'
      OR track.name GLOB 'wq:*'
    )
)
SELECT
  queue_name,
  time_to_ms(ts) AS start_ms,
  time_to_ms(COALESCE(next_ts, trace_end()) - ts) AS dur_ms,
  queue_length
FROM queue_samples
WHERE queue_length > 0
ORDER BY queue_length DESC, dur_ms DESC
LIMIT 200;
```

`LEAD()` 取得同一轨道的下一条采样时间，最后一条没有后继时，`COALESCE()` 改用 `trace_end()`。瞬间出现非零值是正常流转的一部分。持续的 `iq` 表明 InputDispatcher 尚未消费完入站事件；持续的 `oq` 表明连接上仍有待写入事件；持续的 `wq` 表明已写入事件还在等待完成确认。队列堆积能缩小范围，但不能单独证明应用主线程、socket 写入或 `system_server` 调度中的哪一项是根因。

## ANR 前的输入状态

### 以 `android_anrs` 为时间锚点

这里的时间锚点是用于界定查询窗口的可信事件时刻。通过名称通配符在 `slice` 中搜索 `ANR` 容易命中日志、应用自定义 Slice 或无关文本。`android.anrs` 模块会解析 `system_server` 的 `ErrorId`（平台为一次 ANR 生成的唯一标识）、subject（主题文本）和 ANR 计时器，并给出标准化的 `anr_type`。

这条查询列出输入分发类 ANR，以及跟踪中解析到的超时长度：

```sql
INCLUDE PERFETTO MODULE android.anrs;
INCLUDE PERFETTO MODULE time.conversion;

SELECT
  error_id,
  process_name,
  pid,
  time_to_ms(ts) AS anr_at_ms,
  anr_type,
  anr_dur_ms,
  default_anr_dur_ms,
  timer_delay,
  subject
FROM android_anrs
WHERE anr_type IN (
  'INPUT_DISPATCHING_TIMEOUT',
  'INPUT_DISPATCHING_TIMEOUT_NO_FOCUSED_WINDOW'
)
ORDER BY ts;
```

`InputDispatcher` 的超时时长并非固定五秒。Android 17 会优先读取目标窗口的分发超时时长，找不到窗口时才使用默认值，并可能按平台的硬件超时倍率放大。Perfetto 的 `anr_dur_ms` 优先来自平台计时器；`default_anr_dur_ms` 只是 AOSP / Pixel 的参考默认值，OEM 厂商可以修改。

### 查看 ANR 窗口内已完成的输入

下面的查询按照每个 ANR 的真实或默认超时窗口，列出 ANR 前已经完成往返的最近 50 个事件：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE android.anrs;
INCLUDE PERFETTO MODULE time.conversion;

WITH input_anrs AS (
  SELECT
    *,
    COALESCE(anr_dur_ms, default_anr_dur_ms) AS timeout_ms
  FROM android_anrs
  WHERE anr_type IN (
    'INPUT_DISPATCHING_TIMEOUT',
    'INPUT_DISPATCHING_TIMEOUT_NO_FOCUSED_WINDOW'
  )
),
ranked AS (
  SELECT
    anr.error_id,
    anr.process_name AS anr_process,
    anr.ts AS anr_ts,
    anr.timeout_ms,
    event.dispatch_ts,
    event.input_event_id,
    event.thread_name,
    event.dispatch_latency_dur,
    event.handling_latency_dur,
    event.ack_latency_dur,
    event.total_latency_dur,
    ROW_NUMBER() OVER (
      PARTITION BY anr.error_id
      ORDER BY event.dispatch_ts DESC
    ) AS recency
  FROM input_anrs AS anr
  LEFT JOIN android_input_events AS event
    ON event.process_name = anr.process_name
    AND event.dispatch_ts BETWEEN
      anr.ts - time_from_ms(anr.timeout_ms)
      AND anr.ts
)
SELECT
  error_id,
  anr_process,
  timeout_ms,
  time_to_ms(anr_ts - dispatch_ts) AS ms_before_anr,
  input_event_id,
  thread_name,
  time_to_ms(dispatch_latency_dur) AS dispatch_ms,
  time_to_ms(handling_latency_dur) AS handling_ms,
  time_to_ms(ack_latency_dur) AS ack_ms,
  time_to_ms(total_latency_dur) AS total_ms
FROM ranked
WHERE recency <= 50
ORDER BY anr_ts, recency;
```

`android_input_events` 只包含四个消息节点都匹配成功的投递。卡住并触发 ANR 的事件可能没有 `finish_ack`（系统收到完成确认的节点），因此不会出现在结果里。ANR 附近没有行并不等于没有输入；此时应查看 `wq:` 计数器、目标主线程调度状态和 ANR 主题字段。

下面的查询把 ANR 窗口与非零队列采样放在同一结果中：

```sql
INCLUDE PERFETTO MODULE android.anrs;
INCLUDE PERFETTO MODULE time.conversion;

WITH input_anrs AS (
  SELECT
    *,
    COALESCE(anr_dur_ms, default_anr_dur_ms) AS timeout_ms
  FROM android_anrs
  WHERE anr_type IN (
    'INPUT_DISPATCHING_TIMEOUT',
    'INPUT_DISPATCHING_TIMEOUT_NO_FOCUSED_WINDOW'
  )
),
queue_samples AS (
  SELECT
    counter.ts,
    counter.value,
    track.name
  FROM counter
  JOIN process_counter_track AS track
    ON track.id = counter.track_id
  JOIN process
    USING (upid)
  WHERE process.name = 'system_server'
    AND (
      track.name = 'iq'
      OR track.name GLOB 'oq:*'
      OR track.name GLOB 'wq:*'
    )
)
SELECT
  anr.error_id,
  anr.process_name,
  queue.name AS queue_name,
  time_to_ms(anr.ts - queue.ts) AS ms_before_anr,
  queue.value AS queue_length
FROM input_anrs AS anr
JOIN queue_samples AS queue
  ON queue.ts BETWEEN
    anr.ts - time_from_ms(anr.timeout_ms)
    AND anr.ts
WHERE queue.value > 0
ORDER BY anr.ts, queue.ts, queue.name;
```

这份结果适合确认堆积发生在哪类队列、是否持续到 ANR 附近。目标连接名可能被截断，仍需在 `Perfetto UI` 中对齐同一时间段的 `InputDispatcher`、应用主线程和调度轨道。

## 三个可复用场景模板

### 滑动卡顿：按场景区间找尾部样本

参数行默认覆盖整份跟踪。复现实验时，把 `start_ts`、`end_ts` 改成场景标记的纳秒时间，并修改进程名：

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE time.conversion;

WITH params(process_name, start_ts, end_ts) AS (
  SELECT 'com.example.reader', trace_start(), trace_end()
),
events AS (
  SELECT event.*
  FROM android_input_events AS event
  JOIN params
    USING (process_name)
  WHERE event.dispatch_ts BETWEEN params.start_ts AND params.end_ts
),
baseline AS (
  SELECT PERCENTILE(total_latency_dur, 95) AS p95_total
  FROM events
  WHERE total_latency_dur IS NOT NULL
)
SELECT
  time_to_ms(event.dispatch_ts) AS dispatch_at_ms,
  event.input_event_id,
  event.event_action,
  event.normalized_event_channel,
  time_to_ms(event.dispatch_latency_dur) AS dispatch_ms,
  time_to_ms(event.handling_latency_dur) AS handling_ms,
  time_to_ms(event.ack_latency_dur) AS ack_ms,
  time_to_ms(event.total_latency_dur) AS total_ms,
  event.frame_id,
  event.is_speculative_frame
FROM events AS event
CROSS JOIN baseline
WHERE event.total_latency_dur >= baseline.p95_total
ORDER BY event.total_latency_dur DESC;
```

该模板把当前区间本身作为 baseline（比较基准），用其中的 P95 选出尾部样本，不给出脱离场景的固定阈值。把异常时间带回 UI 后，依次检查接收线程状态、`doFrame`、Binder Slice、GC（Garbage Collection，垃圾回收）、锁等待和 CPU 频率。

### 输入 ANR：标准化 ANR 加队列

输入 ANR 的 SQL 已在上一节给出。实际排查应把三份证据并排：

- `android_anrs` 的类型、主题字段、计时器和目标进程；
- `iq`、`oq:`、`wq:` 的非零持续区间；
- 应用主线程在超时窗口内的运行、可运行、睡眠状态及长切片。

已完成事件的分段延迟用于观察超时前是否已经退化，不能替代未完成投递的现场。

### 冷启动：第一个目标进程输入

“点击桌面图标到应用首帧”不属于 `android_input_events` 对目标应用的直接测量，因为启动手势先由 Launcher（桌面应用）接收。下面的查询回答一个更窄的问题：每次启动开始后，目标进程何时收到第一条可完整匹配的输入投递。

```sql
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE android.startup.startups;
INCLUDE PERFETTO MODULE time.conversion;

WITH params(package_name) AS (
  VALUES ('com.example.reader')
),
target_startups AS (
  SELECT startup.*
  FROM android_startups AS startup
  JOIN params
    ON params.package_name = startup.package
),
ranked AS (
  SELECT
    startup.startup_id,
    startup.package,
    startup.startup_type,
    startup.ts AS startup_ts,
    startup.ts_end AS startup_end_ts,
    event.dispatch_ts,
    event.input_event_id,
    event.total_latency_dur,
    ROW_NUMBER() OVER (
      PARTITION BY startup.startup_id
      ORDER BY event.dispatch_ts
    ) AS input_order
  FROM target_startups AS startup
  LEFT JOIN android_input_events AS event
    ON (
      event.process_name = startup.package
      OR event.process_name GLOB startup.package || ':*'
    )
    AND event.dispatch_ts >= startup.ts
)
SELECT
  startup_id,
  package,
  startup_type,
  time_to_ms(startup_end_ts - startup_ts) AS startup_ms,
  time_to_ms(dispatch_ts - startup_ts) AS first_input_after_start_ms,
  CASE
    WHEN dispatch_ts IS NULL THEN NULL
    WHEN dispatch_ts <= startup_end_ts THEN 1
    ELSE 0
  END AS input_arrived_during_startup,
  time_to_ms(total_latency_dur) AS first_input_round_trip_ms,
  input_event_id
FROM ranked
WHERE input_order = 1
ORDER BY startup_ts;
```

第一条目标输入可能发生在启动结束很久之后，`first_input_after_start_ms` 因而不能直接当作可交互时间。若目标是启动手势到首帧，应结合 `android_startups`、启动方输入事件、Flow（Trace 事件之间的因果连线）或自定义场景标记，并对跨进程因果关系单独建模。

## SQL 与 Perfetto UI 的分工

SQL 适合重复执行的筛选和统计：

- 计算同场景 P50、P95、P99 与缺失率；
- 找出最慢事件、推测帧关联和队列非零区间；
- 在多份跟踪上运行相同判定；
- 固化修复前后的对比口径。

`Perfetto UI` 适合检查单个异常点周围的因果证据：

- 线程为何没有运行，或者运行后执行了什么；
- 输入处理是否落在 `doFrame` 内，是否错过目标 Vsync；
- Binder、锁、GC、I/O、频率与 `SurfaceFlinger` 是否同时异常；
- SQL 的进程、通道和帧关联是否符合现场。

实用流程是用 SQL 产出时间戳、事件 ID、进程、通道、帧 ID 和异常分段，再到 UI 展开该点；修复后用相同 SQL 与相同采集条件复测。§13.7 提供通用查询框架，这里进一步给出输入处理链路的可重复量化入口。

## `TraceConfig`：按问题选择采集面

### 常规输入往返与帧关联

TraceConfig 是声明缓冲区、采集时长和数据源的 protobuf 配置。下面是一份 Android 17 的文本格式示例，它采集输入 ATrace、应用视图与图形 Slice、FrameTimeline 以及调度上下文：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 10000

data_sources {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "input"
      atrace_categories: "view"
      atrace_categories: "gfx"
      atrace_apps: "com.example.reader"
    }
  }
}

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
    target_buffer: 0
  }
}
```

`RING_BUFFER` 表示缓冲区写满后覆盖最早的数据。修改 `atrace_apps` 和采集时长后即可用于目标场景；`input` 类别提供 InputDispatcher 与队列计数器，应用侧 Slice 需要目标应用进入 ATrace 采集范围，FrameTimeline 用于 `frame_id` 和 `end_to_end_latency_dur`。缓冲区大小要按设备事件量和场景时长实测，不能把示例值视为固定配置。

### 原始输入与窗口分发

需要原始 `MotionEvent`、`KeyEvent` 或窗口分发决策时，可以在 `userdebug` 或 `eng` 调试设备上追加下面的数据源。示例使用 `TRACE_MODE_USE_RULES`，表示逐条按规则决定记录等级：

```protobuf
data_sources {
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
```

没有匹配条件的规则会匹配所有事件；规则按声明顺序处理，首个匹配项决定记录等级。`TRACE_LEVEL_REDACTED` 是脱敏记录等级，会省略指针坐标、按键码和硬件扫描码。事件没有匹配任何规则时，默认使用 `TRACE_LEVEL_NONE`，即不记录。

`TRACE_MODE_TRACE_ALL` 会绕过隐私措施并记录系统处理的全部输入，只适合本地受控设备和测试，禁止用于线上采集。包名规则检查一次事件的所有目标：`match_any_packages` 在任一目标包命中列表时成立，`match_all_packages` 要求所有目标包都位于列表中。同一事件常被发送给前台应用、监视窗口等多个目标，因此两种规则的覆盖面可能与直觉不同。坐标、按键、IME（Input Method Editor，输入法）连接状态和安全窗口均属于敏感信息。

原始事件数据源不会替代常规配置中的 ATrace 和 FrameTimeline。只打开它可以得到三张原始视图，却不保证 `android_input_events` 的消息往返与帧关联完整。

## 批量跟踪对比

批量比较前，应固定以下实验条件：

- 平台版本、设备型号、刷新率和电源模式；
- 场景脚本、输入注入方式、采集时长和预热方式；
- `TraceConfig`、`Trace Processor` 或 `perfetto` Python 包版本；
- 样本筛选条件、进程名、样本量和异常样本处理规则。

Perfetto 的 Batch Trace Processor 会为每份 Trace 启动独立解析实例，并对它们执行同一条 SQL。下面的脚本读取 `traces` 目录中的文件，逐份生成分位数、帧关联率和推测关联率，再用 Pandas（Python 表格分析库）合并结果：

```python
from glob import glob

import pandas as pd
from perfetto.batch_trace_processor.api import BatchTraceProcessor


TRACE_FILES = sorted(glob("traces/*.perfetto-trace"))
if not TRACE_FILES:
    raise SystemExit("traces 目录中没有 .perfetto-trace 文件")

QUERY = """
INCLUDE PERFETTO MODULE android.input;
INCLUDE PERFETTO MODULE time.conversion;

WITH params(process_name) AS (
  VALUES ('com.example.reader')
)
SELECT
  COUNT(*) AS event_count,
  time_to_ms(PERCENTILE(total_latency_dur, 50)) AS p50_ms,
  time_to_ms(PERCENTILE(total_latency_dur, 95)) AS p95_ms,
  time_to_ms(PERCENTILE(total_latency_dur, 99)) AS p99_ms,
  time_to_ms(MAX(total_latency_dur)) AS max_ms,
  ROUND(
    100.0 * SUM(frame_id IS NOT NULL) / NULLIF(COUNT(*), 0),
    2
  ) AS frame_match_percent,
  ROUND(
    100.0 * SUM(is_speculative_frame = 1) / NULLIF(COUNT(*), 0),
    2
  ) AS speculative_match_percent
FROM android_input_events
JOIN params
  USING (process_name)
WHERE total_latency_dur IS NOT NULL;
"""

with BatchTraceProcessor(TRACE_FILES) as batch:
    per_trace = batch.query(QUERY)

summary = pd.concat(
    [
        frame.assign(trace_path=trace_path)
        for trace_path, frame in zip(TRACE_FILES, per_trace)
    ],
    ignore_index=True,
)
summary.to_csv("input-latency-summary.csv", index=False)
print(summary.to_string(index=False))
```

`pd.concat()` 把每份 Trace 的 DataFrame（带列名的内存表格）纵向合并。修改查询参数行中的目标进程后，脚本会显式用文件路径标识每份结果，避免依赖地址解析器自动添加列的具体命名。`event_count`、帧匹配率和推测关联率必须与延迟分位数一起看；覆盖率变化意味着两组统计来自不同完整程度的样本，分位数可能失去可比性。每份 Trace 的解析结果都会常驻内存，输入规模较大时需要分批处理。

## 版本边界与核对清单

提交分析结论前，逐项确认：

- 设备平台高于 Android 17 时重新核验本文结论；当前平台源码基线记录为 `android-17.0.0_r1`；
- 涉及调度语义时，内核锚点记录为 `android17-6.18-2026-06_r6`；
- `Trace Processor` 版本支持当前查询中的公开列；
- 没有依赖以下划线开头的标准库内部对象；
- `android_input_events` 与原始 inputevent 视图没有被当作同一采集链路；
- `event_time`、`read_time`、`dispatch_ts` 和原始视图 `ts` 没有混用；
- 帧结果区分精确关联、推测关联和无关联；
- ANR 时间来自 `android_anrs`，超时长度没有写死；
- 队列轨道使用 Android 17 源码中的 `iq`、`oq:`、`wq:`；
- 修复前后采集条件、覆盖率与样本量一致。

## 参考资料

- [PerfettoSQL 标准库：`android.input`](https://perfetto.dev/docs/analysis/stdlib-docs#android-input)
- [PerfettoSQL 语法与模块引入](https://perfetto.dev/docs/analysis/perfetto-sql-syntax)
- [Perfetto `Batch Trace Processor`](https://perfetto.dev/docs/analysis/batch-trace-processor)
- [Perfetto `TraceConfig` 协议参考](https://perfetto.dev/docs/reference/trace-config-proto#AndroidInputEventConfig)
- [Android 17 `android/input.sql`](https://android.googlesource.com/platform/external/perfetto/+/ece66975738007dd0978b911d8a2077e49b8f31e/src/trace_processor/perfetto_sql/stdlib/android/input.sql)
- [Android 17 inputevent 配置协议](https://android.googlesource.com/platform/external/perfetto/+/ece66975738007dd0978b911d8a2077e49b8f31e/protos/perfetto/config/android/android_input_event_config.proto)
- [Android 17 inputevent `Trace Processor` 解析器](https://android.googlesource.com/platform/external/perfetto/+/ece66975738007dd0978b911d8a2077e49b8f31e/src/trace_processor/importers/proto/winscope/android_input_event_parser.cc)
- [Android 17 `InputDispatcher.cpp`](https://android.googlesource.com/platform/frameworks/native/+/ae266dcb706d083868578cfedce381ef44488a07/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [Android 17 通用内核 6.18 锚点](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
- §3.2 触摸延迟、预测与低延迟渲染
- §9.2 ANR 分析方法
- §13.2 Perfetto View 解读
- §13.7 Perfetto SQL 性能分析实战手册
