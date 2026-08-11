---
title: 卡顿分析方法论
chapter: '7.3'
section: '7.3'
reviewed_date: '2026-06-19'
last_task2b_at: '2026-05-05T10:47:46.821502'
reviewed_by: openclaw-task6
rework_date: '2026-04-04'
rework_by: openclaw-task2b
rework_type: review回炉修复（Task9/External 问题单）
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-03-31'
last_verified_against: AOSP android-16.0.0_r1, Perfetto 官方文档
confidence: high
consolidated_from:
- src/part2-performance/ch07-smoothness/15-scenario-playbooks.md
sources:
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android卡顿监测的方方面面.md
- type: official
  path: https://perfetto.dev/docs/analysis/trace-probe-checks
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
tags:
- jank
- methodology
- Perfetto
- Systrace
- FrameTimeline
- FrameMetrics
- CPU
- checklist
related_chapters:
- '7.1'
- '7.2'
- '2.4'
- '2.5'
- '2.6'
- '2.18'
- '1.5'
- '13.3'
task6_state: reviewed
task6_result: pass-light-edit
task2b_result: fixed
task6_reviewed_date: '2026-06-19'
review_round: 3
status: "finalized"
pipeline_stage: ready-to-publish
task9_result: 'auto-fixed'
task9_state: 'reviewed'
task2b_state: fixed
task9_reviewed_by: 'openclaw-task9'
task9_reviewed_date: '2026-06-19'
last_task9_at: '2026-06-19T11:28:24+08:00'
last_task9_audit: '2026-06-19'
task9_review_notes: '2026-05-05 11:20 task9 deep-review: needs-rework；P0 0 / P1 1 / P2 1。 | 2026-05-13 02:51 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；满足 task6_result=pass-light-edit 且 queue 无 pending，自动晋升 finalized / ready-to-publish。 | 2026-06-19 11:28 Task9 idle-audit: auto-fixed。P0 2 / P1 0 / P2 0；修正 FrameMetrics 表中 INPUT_HANDLING_DURATION 常量名与 INTENDED_VSYNC_TIMESTAMP API 引入版本，回 Task6 复审。'
last_task6_at: '2026-06-19T12:09:00+08:00'
last_task6_audit: '2026-06-18'
review_notes: '2026-05-05 task6 revisit: L1/L2 小修完成；待 Task9 复审。 | 2026-06-19 Task6 revisit: Task9 auto-fix 修正 FrameMetrics 表常量名与 API 版本后复审；L1 禁用词零命中，L2 通过；修复参考资料区 Binder/FrameTimeline 链接合并错误；无 B 类大问题；自动晋升 finalized。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-19
last_task9_autofix_at: '2026-06-19'
last_task9_review_log: 'logs/deep-review/2026-06-19-11-audit.md'
---


# 7.3 卡顿分析方法论

## 分析目标：把异常帧变成可复核因果链

卡顿分析的交付物不应停在“主线程有一个长 slice”或“CPU 频率较低”。一份可复核结论要记录复现场景、目标 SurfaceFrame / DisplayFrame、责任边界、关键线程或 fence，以及修复后的同场景对照。

推荐使用以下证据顺序：

1. 复现并固定环境；
2. 检查 trace 是否包含所需 probe；
3. 定位异常 SurfaceFrame 和对应 DisplayFrame；
4. 按 JankType 选择 App、SurfaceFlinger、HWC / display 或 buffer 路径；
5. 在帧窗口内分析线程状态、Binder、GC、I/O、GPU 与 fence；
6. 用相同设备状态和操作脚本验证修复。

每一步都要保留帧 token、进程、线程、layer 和时间区间。只靠视觉上相邻的 slice 容易把后台事件误归给目标帧。

## 抓取前先固定现场

复现记录至少包含：设备与 build、应用版本、刷新率 / 显示模式、温控状态、是否充电、前后台状态、页面与手势脚本、复现次数、首次还是稳态运行。涉及 SurfaceView、WebView、Camera、Video、Flutter、游戏或 Native Graphics 时，还要记录 Producer、Surface 与 layer 结构。

“竞品不卡”只能提供比较线索。两个应用可能使用不同刷新率请求、Surface 结构、解码路径和画质，不能据此排除设备或系统瓶颈。低端设备才复现也不自动等于 CPU 调度问题，应继续区分计算量、内存带宽、GPU、I/O 与 thermal。

抓取时长由复现概率决定。稳定复现适合短 trace，减少噪声；偶发问题适合 ring buffer、触发式停止或多轮采样。buffer 大小要覆盖目标窗口，并在结果中检查数据是否丢失。

## Android 17 的基础 Perfetto 配置

下面的配置用于开发和测试环境中的标准 HWUI 卡顿采集，包名、时长和 buffer 大小应按现场调整。

```protobuf
buffers: {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources: {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_return"

      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "input"
      atrace_categories: "wm"
      atrace_categories: "am"
      atrace_categories: "dalvik"
      atrace_apps: "com.example.app"
    }
  }
}

data_sources: {
  config {
    name: "android.surfaceflinger.frametimeline"
    target_buffer: 0
  }
}

duration_ms: 15000
```

该配置提供 FrameTimeline、应用 / 系统 atrace、调度、blocked reason、CPU 频率和 Binder 基线。GPU render stages、memory counters、heapprofd、thermal 或厂商图形数据源需要按设备支持和问题类型追加；一次塞入所有高频 probe 会增加开销并缩短有效窗口。

抓完后要检查 `traced` / `traced_probes` 错误、数据源是否启动、目标 App 是否出现在 atrace 中、FrameTimeline 表是否有行，以及 trace buffer 是否发生 overwrite。没有采到某项数据时，结论应标为缺证据，不用空轨道反推系统行为。

## 帧级定位：Expected、Actual 与两类 token

Android 12 / API 31 起，FrameTimeline 是标准入口。应用的 SurfaceFrame 和 SurfaceFlinger 的 DisplayFrame 分别有 expected / actual timeline；Perfetto 通过 flow 关联两者。`surface_frame_token` 与 `display_frame_token` 是不同标识，一个 DisplayFrame 可以合成多个 layer frame。

选择应用 `Actual Timeline` slice 后，依次记录：

- `Layer Name` 与 `Is Buffer`；
- `surface_frame_token` 与 `display_frame_token`；
- `On time finish`、`Present Type`、`Jank Type`；
- 对应 expected window；
- flow 指向的 DisplayFrame，以及 SF 侧的 GPU composition 与 present 状态。

颜色只用于导航。红色、黄色或浅绿色不能代替字段；`JankType` 还是位标志，同一帧可能有多个原因。`BufferStuffing`、Dropped、PredictionError 和显示模式切换还要读取相邻帧。

SurfaceView、视频 overlay、Camera 和某些引擎路径可能没有完整的 App FrameTimeline。此时从目标 layer、buffer update、acquire fence、SF latch、composition type、present fence 与 release fence 组织证据。出图类型识别参见 [渲染管线总览](../ch18-rendering-pipelines/01-pipeline-overview.md)。

## 从帧回到线程与系统

### MainThread 与 RenderThread

`Choreographer#doFrame` 是应用帧调度入口，常见 callback 顺序为 Input、Animation、Insets Animation、Traversal、Commit。`DrawFrame` 位于 RenderThread，覆盖 HWUI 的渲染准备与提交工作。两者是回溯锚点，不能替代 FrameTimeline 的完成与呈现结论。

主线程 `doFrame` 开始晚时，检查前序 Looper 消息、同步 Binder、锁、I/O 和 wakeup latency。`doFrame` 内部拉长时，再拆 callback 与业务 slice。MainThread 在 `syncFrameState` 一带等待可能是与 RenderThread 的预期同步，也可能被前一帧、纹理上传或 buffer backpressure 放大；应沿 wait 的唤醒源继续追踪。

RenderThread `DrawFrame` 长时，区分 Running、Runnable、buffer / fence wait 和 GPU completion。RenderThread CPU slice 短也不能证明 GPU 按时完成，FrameTimeline 的 finish、GPU track 与 acquire fence 仍要核对。

### SurfaceFlinger 与显示末端

`SurfaceFlingerCpuDeadlineMissed` 应检查 SF 主线程、transaction、layer snapshot、composition strategy 和 HWC validate/present。`SurfaceFlingerGpuDeadlineMissed` 应检查 RenderEngine、client target 和 GPU fence。`DisplayHAL` 应继续到 Composer HAL、present fence、显示模式与驱动。

`onMessageReceived` 是旧版和底层 trace 中常见的 SF 工作锚点，但 slice 名、拆分方式和厂商 instrumentation 会变化。Android 17 分析应优先依赖 DisplayFrame、flow 与明确的 SF / HWC 事件，不以某个 slice 名缺失判定“SF 没有合成”。

## CPU 调度与等待状态

线程状态要按 Linux 调度语义解释：

| 状态 | 含义 | 分析动作 |
|------|------|----------|
| Running | 正在某个 CPU 上执行 | 看调用栈、slice、核心与频率 |
| Runnable (`R`) | 可运行但尚未获得 CPU | 量化 wakeup-to-running，检查竞争者与调度组 |
| Sleeping (`S`) | 可中断等待 | 找等待对象、Binder flow、锁 owner 或唤醒源 |
| Uninterruptible Sleep (`D`) | 内核不可中断等待 | 结合 `io_wait`、`blocked_function` 与内核事件 |

Runnable duration 描述等待 CPU 的时间，不是前一段 `sched_slice.dur`。`sched_slice.end_state = R` 或 `R+` 描述线程离开 CPU 时仍可运行，适合解释为何被切出；它不直接给出后续等待了多久。测量调度延迟应使用 `thread_state` 的 Runnable 区间，必要时再结合 `sched_waking` 的唤醒关系。

`D` 状态也不等同于存储 I/O。fence、驱动、页错误和其他内核 wait queue 都可能形成不可中断等待。只有 `blocked_function`、`io_wait` 与相邻事件支持时，才写具体资源。

## 标准化分析 Checklist

### 现场与 trace 完整性

- [ ] 记录设备、build、应用版本、刷新率、thermal 和操作脚本；
- [ ] 标出目标问题的开始、结束和复现次数；
- [ ] 确认 FrameTimeline、sched、atrace 和所需专项 probe 有数据；
- [ ] 检查 buffer overwrite、数据丢失与 tracing overhead；
- [ ] 确认 Producer、Surface、layer 和合成路径。

### 帧与责任边界

- [ ] 记录 SurfaceFrame token、DisplayFrame token、layer name；
- [ ] 读取 expected / actual、finish、present 与 JankType；
- [ ] 沿 flow 找到对应 DisplayFrame；
- [ ] 检查相邻帧是否存在 stuffing、drop、mode / power transition；
- [ ] 按 App、SF CPU、SF GPU、Display 或 buffer 选择分支。

### 线程与依赖

- [ ] App 分支拆 MainThread、RenderThread、应用 GPU 和 buffer；
- [ ] SF 分支拆主线程、RenderEngine、HWC 与 present；
- [ ] 对长等待区分 Runnable、Sleeping、`D`、Binder、锁和 fence；
- [ ] GC 只计算与目标线程重叠的 pause，不把并发阶段全算作停顿；
- [ ] thermal、频率、内存压力和后台负载保留为需要时序验证的系统因素。

### 结论与验证

- [ ] 写出异常帧、责任方、关键路径事件和排除项；
- [ ] 区分直接证据、组合证据与相关现象；
- [ ] 修复前后使用同一设备状态、场景和 trace 配置；
- [ ] 比较 jank 类型、帧间隔分布、关键 slice / wait 和业务指标；
- [ ] 结论无法复现时保留不确定性和下一轮采集项。

## FrameMetrics 与 JankStats 的线上角色

`Window.OnFrameMetricsAvailableListener` 从 API 24 起提供 HWUI 窗口的逐帧指标。listener 在指定 Handler 上回调，处理过慢会产生 `dropCountSinceLastInvocation`；这个 drop count 表示指标回调丢失，不等于显示帧被 SurfaceFlinger 丢弃。跨线程保存数据时应复制 `FrameMetrics`。

| 指标 | API 边界 | 解释 |
|------|----------|------|
| `INPUT_HANDLING_DURATION`、`ANIMATION_DURATION`、`LAYOUT_MEASURE_DURATION`、`DRAW_DURATION` | API 24 | App UI / View 阶段耗时 |
| `SYNC_DURATION`、`COMMAND_ISSUE_DURATION`、`SWAP_BUFFERS_DURATION`、`TOTAL_DURATION` | API 24 | HWUI 同步、提交和总时长 |
| `INTENDED_VSYNC_TIMESTAMP`、`VSYNC_TIMESTAMP` | API 26 | 计划与采用的 VSync 时间 |
| `GPU_DURATION`、`DEADLINE` | API 31 | GPU 完成时间与应用帧预算 |
| `FRAME_TIMELINE_VSYNC_ID` | API 36 | 把 HWUI frame 与 compositor timeline 关联 |

`TOTAL_DURATION` 不是各阶段简单求和，部分阶段可并行。API 31+ 可用 `TOTAL_DURATION < DEADLINE` 判断应用是否满足该帧预算；这仍是 HWUI 窗口视角，不能覆盖独立 Surface 的全部像素生产和显示末端。

`JankStats` 在 FrameMetrics / 平台 timing 上增加启发式 jank 判断和 UI state。它适合聚合“哪个页面或交互常出问题”；Perfetto 用于解释具体帧的跨进程原因。线上数据应按设备、刷新率、场景和版本聚合，不把不同 API level 的精度当作同一测量条件。

第三方应用的 Perfetto SDK 主要提供进程内 Track Event 和受支持的 tracing session。它不赋予应用读取任意 ftrace、SurfaceFlinger 或其他进程数据的权限。开发环境可通过 adb / Android Studio 采系统 trace；生产采集要使用平台允许的 profiling API、设备策略或应用内指标，并清楚记录数据源缺口。

## Perfetto SQL：从表结构开始

SQL 查询应和生成 trace 的 Trace Processor 版本配套。Android 17 的 AOSP 锚点为 `platform/external/perfetto` 的 `android.frames.timeline`、`android.binder` 与 `android.binder_breakdown` 模块。字段不存在、模块未包含或 trace 没有对应 probe 时，查询失败本身就是采集问题。

### 查询异常 SurfaceFrame

下面的查询使用 `android_frames_layers` 提供的 actual / expected id 配对，避免按 slice 名或 `track_id` 猜帧。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  f.process_name,
  f.frame_id,
  f.layer_name,
  a.surface_frame_token,
  a.display_frame_token,
  a.ts,
  a.dur / 1e6 AS actual_ms,
  e.dur / 1e6 AS expected_ms,
  ((a.ts + a.dur) - (e.ts + e.dur)) / 1e6 AS finish_delta_ms,
  a.on_time_finish,
  a.present_type,
  a.jank_type
FROM android_frames_layers AS f
JOIN actual_frame_timeline_slice AS a
  ON a.id = f.actual_frame_timeline_id
LEFT JOIN expected_frame_timeline_slice AS e
  ON e.id = f.expected_frame_timeline_id
WHERE a.on_time_finish = 0
   OR a.jank_type != 'None'
   OR a.present_type != 'On-time Present'
ORDER BY a.ts;
```

`finish_delta_ms` 比较 actual end 与 expected end，只用于该 SurfaceFrame 的窗口偏差；最终责任仍以 `jank_type`、DisplayFrame 和 flow 为准。`android_frames_layers` 对 layer 更友好，`android_frames` 则按进程与 frame 聚合，选表时要匹配问题粒度。

### 查询主线程与 RenderThread 的等待

下面的查询列出目标进程关键线程中最长的 Runnable 与不可中断等待，包名需要替换。

```sql
WITH params(process_name) AS (
  VALUES ('com.example.app')
)
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  s.ts,
  s.dur / 1e6 AS wait_ms,
  s.state,
  s.io_wait,
  s.blocked_function
FROM thread_state AS s
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
JOIN params ON params.process_name = p.name
WHERE (t.is_main_thread = 1 OR t.name = 'RenderThread')
  AND s.state IN ('R', 'D')
  AND s.dur > 0
ORDER BY s.dur DESC
LIMIT 100;
```

`R` 行的 duration 是等待调度时长；`D` 行要结合 `io_wait` 和 `blocked_function`。查询没有限制帧窗口，适合初筛；形成单帧结论时，应再与目标 frame 的 `[ts, ts + dur)` 做区间重叠。

### 把 Binder 限制在 AppDeadlineMissed 帧内

下面的查询只保留目标应用 UI / RenderThread 在 `App Deadline Missed` 帧窗口内发起的同步 Binder，避免从全局慢事务反推帧责任。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.binder;

WITH params(process_name) AS (
  VALUES ('com.example.app')
),
janky_frames AS (
  SELECT DISTINCT
    f.frame_id,
    f.ts,
    f.dur,
    f.upid,
    f.ui_thread_utid,
    f.render_thread_utid
  FROM android_frames_layers AS f
  JOIN actual_frame_timeline_slice AS a
    ON a.id = f.actual_frame_timeline_id
  JOIN params ON params.process_name = f.process_name
  WHERE a.jank_type GLOB '*App Deadline Missed*'
)
SELECT
  jf.frame_id,
  b.binder_txn_id,
  b.aidl_name,
  b.method_name,
  b.client_thread,
  b.server_process,
  b.server_thread,
  b.client_dur / 1e6 AS client_ms,
  b.server_dur / 1e6 AS server_ms
FROM janky_frames AS jf
JOIN android_binder_txns AS b
  ON b.client_upid = jf.upid
 AND (b.client_utid = jf.ui_thread_utid
      OR b.client_utid = jf.render_thread_utid)
 AND b.client_ts < jf.ts + jf.dur
 AND b.client_ts + b.client_dur > jf.ts
WHERE b.is_sync = 1
ORDER BY b.client_dur DESC;
```

查询结果证明 Binder 与责任线程帧窗口重叠。要解释延迟来源，再包含 `android.binder_breakdown`，按 `binder_txn_id` 汇总 `android_binder_client_breakdown` 和 `android_binder_server_breakdown` 的 `reason`。`server_ts - client_ts` 只表示服务端开始前的时间差；线程池饱和还需要服务端 worker、Runnable、嵌套 Binder 与队列证据，不能由固定毫秒阈值直接判定。

### 大型 trace

大型 trace 先用时间窗口、process / thread 和 `LIMIT` 缩小查询，再考虑 `MATERIALIZED` CTE 或临时表。命令行 `trace_processor_shell trace.pb --query-file analysis.sql` 适合离线批处理；SQL 文件应和 trace、Trace Processor 版本、查询参数一起归档，保证结果可重放。

## 常见失误

| 失误 | 修正 |
|------|------|
| 看到红色 slice 就写根因 | 读取 token、字段、flow 与责任线程 |
| 用固定 16.67 ms 处理所有设备 | 使用该帧 expected / deadline 和当时显示模式 |
| `doFrame` 短便排除 App | 继续检查 RenderThread、应用 GPU、buffer 与独立 Surface |
| 主线程 Sleeping 便认定 App 无责 | 找等待对象、服务端、owner 或 fence |
| `D` 状态都算磁盘 I/O | 检查 `blocked_function`、`io_wait` 与驱动事件 |
| Binder dispatch 超过某阈值便认定线程池耗尽 | 检查 server worker、调度、锁、嵌套事务和 breakdown |
| FrameMetrics listener drop 当作显示掉帧 | 它表示指标回调丢失 |
| App 启动 Perfetto SDK 就能拿系统 trace | 区分进程内 Track Event 与受权限保护的数据源 |
| trace 越长越有价值 | 选择能覆盖复现且数据完整的最小窗口 |

## Android 17 与 kernel 锚点

- Platform：`android-17.0.0_r1` 的 FrameTimeline、FrameMetrics、HWUI、SurfaceFlinger 和 Perfetto stdlib。
- Kernel：调度、Binder、blocked reason、dma-fence、PSI 与 reclaim 以 `android17-6.18-2026-06_r6` 为准。
- 版本演进：Android 12 前没有 FrameTimeline；API 24 起有 FrameMetrics，API 31 增加 `GPU_DURATION` / `DEADLINE`，API 36 增加 `FRAME_TIMELINE_VSYNC_ID`。历史工具可保留，但 Android 17 分析优先使用现代字段。

## 与其他章节的关系

- [7.1 卡顿的定义与分类](01-jank-definition.md)：JankType、token 与指标边界。
- [7.2 卡顿原因体系](02-jank-causes.md)：按 App、buffer、SF、display 与系统因素解释根因。
- [2.5 MainThread 与 RenderThread](../../part1-fundamentals/ch02-rendering/05-main-render-thread.md)：HWUI 线程同步。
- [FrameTimeline Perfetto 分析](../../part3-tools/ch13-perfetto/20-frame-timeline-api33-perfetto-analysis.md)：FrameTimeline 数据与 SQL。
- [Perfetto SQL Cookbook](../../part3-tools/ch13-perfetto/10-perfetto-sql-cookbook.md)：窗口查询和标准库用法。
- [BufferQueue 阻塞分析](../../part3-tools/ch13-perfetto/15-bufferqueue-blocking-perfetto.md)：slot、fence 与 backpressure。

## 参考资料

- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Perfetto trace configuration](https://perfetto.dev/docs/concepts/config)
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Perfetto trace processor](https://perfetto.dev/docs/analysis/trace-processor)
- [Perfetto SDK](https://perfetto.dev/docs/instrumentation/tracing-sdk)
- [Android FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Android JankStats](https://developer.android.com/topic/performance/jankstats)
- [AOSP Android 17 FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP Android 17 FrameTimeline.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
- [AOSP Android 17 frames/timeline.sql](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)
- [AOSP Android 17 binder.sql](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)
- [Android 17 kernel Binder tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_trace.h)
