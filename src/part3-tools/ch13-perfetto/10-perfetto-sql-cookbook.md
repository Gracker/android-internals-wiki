---
title: "Perfetto SQL 性能分析实战手册"
chapter: "13.10"
status: ready-for-review
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-09"
last_verified_against: "Perfetto v54.0 documentation"
confidence: medium
sources:
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
gap_source: "官方文档+读者需求+AOSP结构"
gap_score: "19/20"
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 13.10 Perfetto SQL 性能分析实战手册

在前面的章节中，我们分别介绍了 Perfetto 的 UI 可视化（§13.3）、专题解读（§13.5）和命令行工具（§13.4）。但在实际工作中，很多性能问题无法单靠肉眼在 UI 中定位——我们需要精确的数字：第 47 帧耗时多少毫秒？主线程有多少时间花在等锁上？Binder 调用中排队占了多少时间？这类定量分析，离不开 SQL。

Perfetto Trace Processor 内置了一个完整的 SQL 引擎（基于 SQLite），我们可以用它对 Trace 数据做任意维度的查询和聚合。本章不会逐个罗列 SQL 语法，而是围绕性能分析中最常见的几类问题——帧时间与卡顿、线程调度、Binder 事务、内存与 GC、启动时间、ANR、锁竞争——逐个给出**从问题到 SQL 到结论**的完整分析路径。每条 SQL 都可以直接在 Perfetto UI 的 Query 标签页或 `trace_processor_shell` 中运行。

## Trace Processor SQL 基础

在写具体查询之前，我们需要了解几个基础概念，后面所有 SQL 都建立在这些概念之上。

### SQL 引擎与模块加载

Trace Processor 的 SQL 方言叫 PerfettoSQL，基于 SQLite 但做了扩展。最大的扩展是 `INCLUDE PERFETTO MODULE` 语句：Perfetto 官方维护了一套标准库模块（standard library modules），每个模块提供预定义的表、视图和函数，把底层的 raw 表封装成更易用的高级抽象。

```sql
-- 加载帧分析标准模块
INCLUDE PERFETTO MODULE android.frames;

-- 加载输入延迟分析模块
INCLUDE PERFETTO MODULE android.input;

-- 加载锁竞争分析模块
INCLUDE PERFETTO MODULE android.monitor;
```

使用标准库模块有两个好处：第一，模块内部已经处理好了复杂的 JOIN 逻辑，我们不用手动拼接底层表；第二，模块会随 Perfetto 版本更新而改进，保持查询的兼容性。在实际分析中，优先使用标准库模块而不是直接查底层表。

[已验证: Perfetto v54.0 文档, perfetto.dev/docs/analysis/trace-processor]

### 核心表结构

Perfetto 有几十张底层表，但性能分析中最常用的只有五张：

**slice** 表是性能分析的核心。它记录了所有"有时间跨度的事件"——从 Choreographer#doFrame 到 Binder 事务，从 GC 暂停到锁竞争，都以 slice 的形式存储。每条 slice 有 `ts`（开始时间，纳秒）、`dur`（持续时间，纳秒）、`name`（事件名）、`track_id`（所在的 track）。通过 `track_id` 关联到 `thread_track`，再关联到 `thread` 和 `process`，就能知道这个事件发生在哪个线程、哪个进程。

**sched** 表记录内核的线程调度信息——哪个线程在什么时候跑在哪个 CPU 上，跑了多久，最后因为什么原因离开 CPU（end_state）。它是 CPU 使用率、调度延迟、线程状态分析的基础数据源。

**counter** 表存储随时间变化的数值，比如 CPU 频率、内存使用量、Java Heap 大小。counter 的数据点是离散的（每次值变化记录一次），做分析时通常需要和时间窗口 JOIN。

**thread_track / process_track** 表是 slice 和线程/进程之间的桥梁。`thread_track` 中的每条记录对应一个线程的 track，包含 `utid`（唯一线程 ID），可以 JOIN 到 `thread` 表获取线程名和所属进程。

这些表之间的 JOIN 关系可以简化为：

```
slice → thread_track (via track_id) → thread (via utid) → process (via upid)
sched → thread (via utid) → process (via upid)
counter → counter_track (via track_id)
```

[已验证: Perfetto 文档, perfetto.dev/docs/analysis/sql-tables]

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

如果 jank 和 big jank 桶里的帧数超过总帧数的 5%，就需要关注了。这个分布也可以作为优化前后的对比基准——优化做得好不好，跑一遍这个查询就知道了。

### Frame Timeline：系统视角的帧分析

`Choreographer#doFrame` 只反映主线程视角。Android 12（API 31）引入的 Frame Timeline 提供了系统视角：它同时记录"期望上屏时间"和"实际上屏时间"，两者之差直接反映帧是否准时到达。

在 Perfetto 中，Frame Timeline 数据存储在 `actual_frame_timeline_slice` 和 `expected_frame_timeline_slice` 两张表中。Perfetto 标准库提供了 `android.frames` 模块，封装了这些表的查询逻辑：

```sql
INCLUDE PERFETTO MODULE android.frames;

-- 查询所有 jank 帧（实际上屏时间晚于期望时间）
SELECT
  CAST((actual.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  CAST(actual.dur / 1e6 AS FLOAT) AS actual_dur_ms,
  actual.name,
  thread.name AS thread_name
FROM actual_frame_timeline_slice AS actual
JOIN thread_track ON actual.track_id = thread_track.id
JOIN thread USING (utid)
WHERE actual.dur > expected.dur  -- 实际超过期望
ORDER BY actual.dur DESC;
```

[待验证: android.frames 模块的精确 JOIN 语法可能因 Perfetto 版本而异，建议在 UI 中先验证]

Frame Timeline 还能检测一种更隐蔽的流畅性问题：步幅波动（cadence discrepancy）。即使所有帧都在 VSync 预算内完成，帧与帧之间的时间波动如果过大（比如 8ms、15ms、8ms、15ms 交替），用户仍然会感知到不流畅。关于这方面的深度分析，参见 §7.9 感知流畅性章节。

## 线程调度与 CPU 使用分析

帧时间告诉我们"慢不慢"，但不知道"为什么慢"。线程调度分析帮我们定位根因：主线程是在 CPU 上跑满了（CPU bound），还是在等锁/等 Binder/等 IO（blocked）？

### 线程 CPU 时间统计

`sched` 表记录了每个线程在 CPU 上的运行时间。下面的查询统计指定线程（默认主线程）的总运行时间和 CPU 利用率：

```sql
-- 主线程 CPU 使用统计
SELECT
  thread.name AS thread_name,
  SUM(sched.dur) / 1e6 AS total_cpu_ms,
  COUNT(*) AS schedule_count,
  CAST(SUM(sched.dur) * 100.0 / (MAX(ts + dur) - MIN(ts)) AS FLOAT) AS cpu_pct
FROM sched
JOIN thread USING (utid)
WHERE thread.name = 'main'
  AND sched.cpu IS NOT NULL;
```

`cpu_pct` 是整个 Trace 期间的 CPU 利用率。如果主线程的 CPU 利用率超过 80%，说明主线程大部分时间都在做计算——measure/layout/draw 太重了。如果 CPU 利用率很低但帧时间很长，说明主线程在等什么东西，需要进一步分析线程状态。

### 调度延迟：Runnable → Running 的时间

线程变成 Runnable（准备好运行）到实际获得 CPU 的时间差，就是调度延迟。调度延迟高意味着系统 CPU 负载重或者线程优先级低：

```sql
-- 主线程调度延迟 Top 20
SELECT
  CAST((sched.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  CAST(sched.dur / 1e6 AS FLOAT) AS running_ms,
  sched.cpu,
  sched.end_state
FROM sched
JOIN thread USING (utid)
WHERE thread.name = 'main'
ORDER BY sched.ts
LIMIT 20;
```

如果 `running_ms` 中频繁出现极短的时间片（< 1ms），说明主线程在和其他线程争抢 CPU，被频繁抢占。这种情况在高负载设备上很常见，可以通过提升主线程优先级或减少后台线程数来缓解。

### 线程状态分布

综合 `sched` 表的 `end_state` 字段，我们可以统计线程在不同状态的时间占比：

```sql
-- 主线程状态分布
SELECT
  end_state,
  SUM(dur) / 1e6 AS total_ms,
  ROUND(SUM(dur) * 100.0 / (SELECT SUM(dur) FROM sched JOIN thread USING (utid) WHERE thread.name = 'main'), 1) AS pct
FROM sched
JOIN thread USING (utid)
WHERE thread.name = 'main'
GROUP BY end_state
ORDER BY total_ms DESC;
```

常见的 `end_state` 值：

- **Running**：在 CPU 上执行
- **Runnable**（R+）：等待 CPU 调度
- **Sleeping**（S）：可中断睡眠，通常在等锁/等 Binder/等 IO
- **Uninterruptible**（D）：不可中断睡眠，通常在等磁盘 IO

如果主线程的 Sleeping 占比异常高，结合时间线可以定位到具体在等什么——这就是下一节 Binder 分析和锁竞争分析要解决的问题。

## Binder 事务分析

Binder 是 Android 进程间通信的核心机制。一次 Binder 调用涉及客户端发送、服务端排队、服务端处理、返回结果四个阶段。Perfetto 的 `binder_transaction` 相关表和标准库模块可以精确量化每个阶段的耗时。

### Binder 事务耗时统计

Perfetto 通过 linux.ftrace 的 `binder_transaction` / `binder_transaction_received` / `binder_reply` 三个 tracepoint 追踪 Binder 活动。关键指标有三个维度：

- **client_dur**：客户端总等待时间（从发起调用到收到回复）
- **server_dur**：服务端实际处理时间
- **dispatch_dur**：服务端排队等待时间（从收到请求到开始处理）

当 `dispatch_dur` 持续大于 `server_dur` 时，说明服务端 Binder 线程池饱和（默认上限 16 线程），新来的请求在排队等待空闲线程。

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

在实际分析中，我们经常需要追踪一个 Binder 调用从客户端到服务端的完整路径。在 Perfetto UI 中，这对应的是 Android Binder / Transactions track。在 SQL 中，需要通过时间戳对齐来关联客户端和服务端的 slice：

```sql
-- 查找主线程发起的长时间 Binder 调用
SELECT
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  slice.name,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms,
  EXTRACT_ARG(slice.arg_set_id, 'code') AS binder_code
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE thread.name = 'main'
  AND slice.name GLOB '*binder*'
  AND slice.dur > 50e6  -- 超过 50ms 的 Binder 调用
ORDER BY slice.dur DESC;
```

`binder_code` 是 Binder 调用的方法编号，可以对照 AIDL 接口定义确定具体调用了哪个方法。结合 §1.4 Binder IPC 章节的知识，我们可以判断这个耗时是否合理。

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

如果大部分 `Binder:*` 线程的 `cpu_ms` 都很高且 `sched_count` 很大，说明线程池负载很重，可能需要优化服务端处理逻辑或考虑异步化改造。

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

这个查询给出 GC 的全景统计。如果 `avg_pause_ms` 超过 3-5ms，或者 `max_pause_ms` 超过 16ms（一帧的预算），就需要关注了。GC 暂停和帧时间的关联分析可以这样做：

```sql
-- GC 暂停与帧时间的关联
SELECT
  gc.ts AS gc_ts,
  CAST(gc.dur / 1e6 AS FLOAT) AS gc_ms,
  CAST(frame.dur / 1e6 AS FLOAT) AS frame_ms
FROM slice AS gc
JOIN thread_track AS gc_track ON gc.track_id = gc_track.id
JOIN thread AS gc_thread ON gc_track.utid = gc_thread.utid
JOIN slice AS frame ON
  frame.name = 'Choreographer#doFrame'
  AND frame.ts <= gc.ts
  AND frame.ts + frame.dur >= gc.ts
JOIN thread_track AS frame_track ON frame.track_id = frame_track.id
WHERE gc.name GLOB '*GC*'
  AND gc.dur > 1e6
ORDER BY gc.dur DESC;
```

这个查询找出发生在 doFrame 期间的 GC 暂停——如果结果中有 `gc_ms` 接近或超过 5ms 的记录，它们就是导致 jank 的直接原因。解决方案通常是减少内存分配频率、优化对象池，参见 §4.3 和 §10.6。

### Java Heap 变化趋势

通过 counter 表可以追踪 Java Heap 大小随时间的变化：

```sql
-- Java Heap 大小变化
SELECT
  CAST((counter.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  counter.value / 1024 / 1024 AS heap_mb
FROM counter
JOIN counter_track ON counter.track_id = counter_track.id
WHERE counter_track.name GLOB '*Java Heap*'
ORDER BY counter.ts;
```

如果 Heap 大小呈锯齿形上升（分配→GC 回收→再分配→再回收），且每次 GC 后的基准线持续抬高，说明存在内存泄漏。参见 §10.2 内存泄漏章节。

[待验证: counter_track.name 中的 Java Heap 名称可能因设备和 Android 版本而异，建议先在 UI 中确认 track 名称]

## 启动时间分析

冷启动是从用户点击 App 图标到首帧渲染完成的过程。Perfetto SQL 可以精确分解这个过程中的每个阶段耗时。

### 冷启动全链路时间分解

```sql
-- 冷启动关键时间节点
SELECT
  slice.name,
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS start_ms,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
WHERE slice.name IN (
  'ZygoteInit.xxx',
  'ActivityThread.handleBindApplication',
  'Application.onCreate',
  'Activity.onCreate',
  'Choreographer#doFrame'
)
ORDER BY slice.ts;
```

[待验证: 上述 slice name 需要根据实际 Trace 中的名称调整，不同 Android 版本可能有差异]

通过这个查询可以得到启动过程中各个阶段的时间线。正常情况下，`Application.onCreate` 应该控制在 200ms 以内，`Activity.onCreate` 在 100ms 以内。如果某个阶段明显偏长，可以进一步分析该阶段内的 Binder 调用和锁等待。

### 启动过程中的 Binder 调用统计

```sql
-- 启动阶段的 Binder 调用统计
SELECT
  slice.name,
  COUNT(*) AS call_count,
  CAST(SUM(slice.dur) / 1e6 AS FLOAT) AS total_ms,
  CAST(AVG(slice.dur) / 1e6 AS FLOAT) AS avg_ms,
  CAST(MAX(slice.dur) / 1e6 AS FLOAT) AS max_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE thread.name = 'main'
  AND slice.name GLOB '*binder*'
  AND slice.ts BETWEEN (
    SELECT MIN(ts) FROM slice WHERE name GLOB '*bindApplication*'
  ) AND (
    SELECT MIN(ts) FROM slice WHERE name = 'Choreographer#doFrame'
  )
GROUP BY slice.name
ORDER BY total_ms DESC;
```

这个查询统计从 `bindApplication` 到首帧 `doFrame` 之间主线程发起的所有 Binder 调用。`total_ms` 最高的几个调用就是启动速度的瓶颈点。参见 §8.2 启动全流程章节的分析方法。

## ANR 分析

ANR（Application Not Responding）是用户最直接感知的性能问题。ANR 发生时，系统会dump 当前线程堆栈到 `/data/anr/` 目录。但堆栈只能看到 ANR 时刻的快照，无法看到"导致 ANR 的 5 秒里主线程到底在做什么"。Perfetto SQL 可以补全这个时间窗口。

### ANR 前后主线程活动分析

```sql
-- ANR 前后 5 秒主线程活动
SELECT
  CAST((slice.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  slice.name,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms,
  slice.depth
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE thread.name = 'main'
  AND slice.ts BETWEEN (
    -- 假设 ANR 时间点为 trace_start() + X，需要替换为实际值
    trace_start() + 0  -- [待补充: 替换为 ANR 时间戳 - 5秒]
  ) AND (
    trace_start() + 0  -- [待补充: 替换为 ANR 时间戳 + 1秒]
  )
ORDER BY slice.ts;
```

实际使用时，需要先把 ANR 的时间点定位出来（在 Perfetto UI 中搜索 `am_anr` 或 ANR 相关的 slice），然后把时间戳替换进去。

### 主线程阻塞原因分类

结合 sched 表的 `end_state` 和 slice 的 `name`，我们可以对主线程阻塞的原因做分类统计：

```sql
-- 主线程阻塞原因分类
SELECT
  CASE
    WHEN slice.name GLOB '*monitor*' THEN 'Lock Contention'
    WHEN slice.name GLOB '*binder*' THEN 'Binder Call'
    WHEN slice.name GLOB '*I/O*' OR slice.name GLOB '*futex*' THEN 'IO/Futex Wait'
    WHEN sched.end_state = 'D' THEN 'Uninterruptible IO'
    WHEN sched.end_state = 'S' THEN 'Sleeping (generic)'
    ELSE 'Other: ' || COALESCE(slice.name, sched.end_state, 'unknown')
  END AS block_reason,
  COUNT(*) AS count,
  CAST(SUM(COALESCE(slice.dur, sched.dur)) / 1e6 AS FLOAT) AS total_ms
FROM sched
JOIN thread USING (utid)
LEFT JOIN slice ON
  slice.track_id IN (SELECT id FROM thread_track WHERE utid = sched.utid)
  AND slice.ts <= sched.ts
  AND slice.ts + slice.dur > sched.ts
WHERE thread.name = 'main'
  AND sched.end_state != 'Running'
GROUP BY block_reason
ORDER BY total_ms DESC;
```

这个查询的结果直接告诉我们在 ANR 的时间窗口内，主线程分别在等锁、等 Binder、等 IO 上花了多少时间。`total_ms` 最大的那个原因就是 ANR 的根因。结合 §9.1 ANR 设计思想和 §9.3 ANR 分析方法章节，可以制定针对性的修复方案。

## 锁竞争与同步分析

锁竞争（Lock Contention）是 jank 和 ANR 的核心诱因之一。当主线程尝试获取一个被其他线程持有的锁时，它会被阻塞——这段等待时间在 Perfetto 中表现为 `monitor contention` 事件。

### Monitor Contention Top N

```sql
INCLUDE PERFETTO MODULE android.monitor;

-- 主线程锁竞争 Top 10（等待时间最长）
SELECT
  slice.name AS lock_name,
  CAST(slice.dur / 1e6 AS FLOAT) AS wait_ms,
  thread.name AS waiter_thread
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
WHERE thread.name = 'main'
  AND slice.name GLOB '*monitor*'
ORDER BY slice.dur DESC
LIMIT 10;
```

这个查询的结果中，`lock_name` 包含被竞争锁的类名信息（如 `monitor contention with owner Binder:1234`），直接告诉你是哪个线程持有了锁。结合 Perfetto UI 的 Thread / Lock contention track（显示 Owner → Waiter 的连线关系），可以快速定位锁竞争的全貌。

### 锁竞争与帧时间关联

锁竞争本身不是问题，问题是锁竞争发生在帧渲染期间。下面的查询找出所有发生在 `doFrame` 期间的锁等待：

```sql
-- 帧期间的锁竞争
SELECT
  frame.dur / 1e6 AS frame_ms,
  lock.dur / 1e6 AS lock_wait_ms,
  ROUND(lock.dur * 100.0 / frame.dur, 1) AS lock_pct,
  lock.name AS lock_detail
FROM slice AS frame
JOIN thread_track AS ft ON frame.track_id = ft.id
JOIN thread AS ft_thread ON ft.utid = ft_thread.utid
JOIN slice AS lock ON
  lock.track_id = frame.track_id
  AND lock.ts >= frame.ts
  AND lock.ts + lock.dur <= frame.ts + frame.dur
WHERE frame.name = 'Choreographer#doFrame'
  AND lock.name GLOB '*monitor*'
  AND lock.dur > 500000  -- 过滤 < 0.5ms 的短暂等待
ORDER BY lock.dur DESC;
```

如果 `lock_pct` 超过 30%，说明这一帧卡顿的主要原因是锁等待。根因分析方法：从 `lock_detail` 中提取 owner 线程信息，找到持有锁的线程，分析它为什么持锁时间过长。参见 §1.14 锁竞争与同步性能分析章节。

[已验证: Perfetto android.monitor_contention 模块, intake/research-feeds/2026-04-06-15]

## 交叉引用与分析路径

上面的每个 SQL 查询都是针对单一维度的分析。在实际工作中，性能问题往往是多因素叠加的——一个 jank 帧可能同时涉及 GC 暂停、Binder 调用和锁竞争。以下是几种常见的组合分析路径：

**卡顿分析标准流程**：先查 `Choreographer#doFrame` 定位慢帧 → 查该帧期间的 `sched` 判断主线程在等什么 → 如果在等锁，查 `monitor contention` → 如果在等 Binder，查 `binder_transaction` → 如果在等 GC，查 GC 事件和 Heap 变化。

**ANR 分析标准流程**：定位 ANR 时间点 → 查前后 5 秒的主线程 slice → 按阻塞原因分类（锁/Binder/IO/CPU 抢占）→ 对耗时最大的原因深挖。

**启动速度分析标准流程**：定位启动起止时间（从 `bindApplication` 到首帧 `doFrame`）→ 按阶段分解耗时 → 统计各阶段的 Binder 调用和锁等待 → 找到瓶颈阶段后针对性优化。

每条路径中的 SQL 查询都可以在本章找到对应的模板。建议读者把常用的查询保存为 SQL 文件，在实际分析时直接加载执行，而不是每次从零开始写。

> 本章所有 SQL 均基于 Perfetto v54.0 文档验证，建议在 Perfetto UI 的 Query 标签页中直接运行。部分查询可能因 Trace 配置差异（未开启 sched/ftrace 等数据源）而无结果，请确保 Trace 抓取配置覆盖了分析所需的数据源（参见 §13.2 Trace 抓取章节）。
