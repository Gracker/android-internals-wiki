---
title: 专题解读
chapter: '13.5'
section: '13.5'
status: finalized
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1 external/perfetto stdlib/protos, perfetto.dev, 高爷博客原创
confidence: high
sources:
- type: blog
  path: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/
- type: blog
  path: https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/
- type: blog
  path: https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://perfetto.dev/docs/data-sources/java-heap-profiler
- type: official
  path: https://perfetto.dev/docs/data-sources/memory-counters
- type: official
  path: https://perfetto.dev/docs/data-sources/battery-counters
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startups.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startup_breakdowns.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/process_stats/process_stats_config.proto
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/proto/system_probes_parser.cc
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/block_io.sql
- type: source
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/kernel_wakelocks.sql
tags:
- perfetto
- cpu
- vsync
- surfaceflinger
- binder
- heapprofd
- io
- frame-timeline
- jank
related_chapters:
- '13.1'
- '13.2'
- '13.3'
- '13.4'
- '2.1'
- '2.4'
- '4.1'
- '5.1'
- '7.1'
- '8.1'
- '9.1'
task9_state: reviewed
task2b_state: "fixed"
task9_result: auto-fixed
task2b_result: "fixed"
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: "2026-05-19"
reviewed_by: openclaw-task6
pipeline_stage: ready-to-publish
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-19"
last_task9_at: "2026-07-03T07:39:55+08:00"
last_task9_autofix_at: "2026-07-03"
last_task6_at: "2026-05-19T16:12:00+08:00"
last_task6_audit: '2026-06-07'
last_task6_audit_result: l1-light-edit
last_task9_audit: "2026-07-03"
last_task9_audit_result: "auto-fixed-idle-audit"
last_task9_review_log: "logs/deep-review/2026-07-03-07-audit.md"
task9_review_notes: "2026-05-19 Task9 deep review: pass-tech-review。P0 0 / P1 0 / P2 0；FrameTimeline、Binder stdlib、process_stats 内存 Counter、sched_blocked_reason 与 linux.block_io 口径复核通过。 | 2026-07-03 Task9 闲时抽检 AUTO-FIX: 将 Perfetto 专题的数据源/stdlib 版本边界复核到 AOSP android-17.0.0_r1；修正 Android 10-16/10+/11+/12+/14+ 这类未封顶或停在 16 的范围，回 Task6 复审。"
last_task2b_at: "2026-05-19T15:20:11+08:00"
last_task6_review_log: "logs/review/2026-05-19-16-review.md"
finalized_date: "2026-05-19"
finalized_by: openclaw-task9-auto-promote
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-26
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-05
---

# 专题解读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 启动分析专题：从 Trace 中定位冷启动各阶段耗时
- 🔹 流畅性分析专题：FrameTimeline 分析、Jank 帧定位
- 🔹 Binder 分析专题：Binder 调用频率、耗时、跨进程追踪
- 🔹 内存分析专题：heapprofd、RSS/PSS counter
- 🔹 I/O 分析专题：block I/O events、filesystem events

### 扩展（可选深入）

- 🔸 功耗分析专题：CPU freq、suspend/resume、wakelock
- 🔸 多进程协同分析：System Server + App 进程联合分析

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

Perfetto 专题分析最容易在找到一段长 Slice 后过早结束：耗时已经看见，归因却还没有完成。一个可复核的判断至少要同时回答四件事：哪段业务动作变慢、哪条线程或设备时间线贡献了延迟、等待由谁唤醒、相同条件下的对照 Trace 是否消除了偶发现象。

这一章以 Android 17 / API 37 / `android-17.0.0_r1` 为平台锚点，覆盖启动、帧、Binder、内存、I/O 和功耗。SQL 以该标签内置的 PerfettoSQL 标准库为准。旧版本是否能直接执行同一模块，取决于设备生成的数据和用于分析的 `trace_processor` 版本；离线分析时应固定工具版本，并把版本号写进结果记录。

## 13.5.1 分析前的证据约束

### 从用户动作划定时间范围

专题分析应从可重复的用户动作开始，例如“点击设置图标到首帧显示”“滑动列表的 5 秒”“按下开关到系统服务返回”。录制前固定设备、构建类型、温度、刷新率和测试数据，保留一份未修改代码的对照 Trace。单次 Trace 可以定位机制，性能收益仍要靠多轮同条件测量确认。

选择时间范围后，依次核对以下证据：

- Trace 是否覆盖动作起点和可观察终点，缓冲区有没有覆盖或数据源错误。
- 进程身份是否用 `upid` 区分。PID 和进程名都可能在长 Trace 中重复。
- 长墙钟耗时由运行、可运行、睡眠还是不可中断睡眠构成。
- 跨线程或跨进程结论能否由 Flow、Binder 事务 ID、帧令牌或相同时间范围连接。
- 优化建议能否指向代码、系统服务或内核事件，是否写明适用版本和权限。

线程状态只描述调度事实，不能单独充当根因：

- `Running` 表示线程正在 CPU 上执行；还要结合调用栈、Slice 和所在 CPU 判断工作内容。
- `R` 或 `Runnable` 表示线程已具备运行条件但尚未获得 CPU；长时间可运行常与 CPU 竞争、优先级或放置策略有关。
- `S` 表示可中断睡眠，可能在等 Binder、futex、条件变量、定时器或其他唤醒源。
- `D` 表示不可中断睡眠，常见于设备驱动和内核等待。磁盘 I/O 只是其中一种可能，必须再找 block、文件系统或内核调用栈证据。

下面这份通用配置适合 20 秒左右的启动、帧、Binder 和块设备联合录制，示例目标是系统设置进程：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 20000

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "block/block_rq_issue"
      ftrace_events: "block/block_rq_complete"
      ftrace_events: "task/task_newtask"
      ftrace_events: "task/task_rename"

      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "view"
      atrace_categories: "dalvik"
      atrace_categories: "binder_driver"
      atrace_categories: "disk"
      atrace_apps: "com.android.settings"
    }
  }
}

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
      proc_stats_poll_ms: 1000
    }
  }
}
```

`com.android.settings` 是可直接录制的例子。分析其他应用时，应先用 `adb shell pidof` 或 `adb shell ps -A` 核对进程命令行，再修改 `atrace_apps`。`proc_stats_poll_ms` 的 1000 毫秒也是显式采样周期；AOSP 配置协议只规定它必须大于 100 毫秒，并没有 1000 毫秒默认值。设备缺少某个 ftrace 事件时，Perfetto 会在 Trace 统计中记录未知或启用失败事件，正式分析前要查看这些错误。

## 13.5.2 启动：以系统定义的启动区间为入口

冷启动跨越 `system_server`、Zygote、应用主线程、`RenderThread` 和 SurfaceFlinger。只搜索 `bindApplication`、`activityStart` 或 `performTraversals` 容易受版本、插桩类别和厂商实现影响。Android 17 标签中的 `android.startup.startups` 模块已经把不同平台格式归一为启动 ID、起止时间、包名和启动类型，适合作为时间范围入口。

### 确认启动样本与显示时间

下面的查询列出 Trace 中的启动，并关联初始显示时间 TTID 与完整显示时间 TTFD：

```sql
INCLUDE PERFETTO MODULE android.startup.startups;
INCLUDE PERFETTO MODULE android.startup.time_to_display;

SELECT
  s.startup_id,
  s.package,
  s.startup_type,
  ROUND(s.dur / 1e6, 3) AS startup_ms,
  ROUND(t.time_to_initial_display / 1e6, 3) AS ttid_ms,
  ROUND(t.time_to_full_display / 1e6, 3) AS ttfd_ms,
  t.ttid_frame_id,
  t.ttfd_frame_id
FROM android_startups AS s
LEFT JOIN android_startup_time_to_display AS t
  USING (startup_id)
ORDER BY s.ts;
```

`android_startups.ts` 到 `ts_end` 是后续查看的统一时间范围。TTID 对应初始显示帧；TTFD 依赖应用调用 `reportFullyDrawn()` 并匹配后续帧，没有上报时会为空。TTFD 为空不能解释成完整显示为零。

冷启动、温启动和热启动的准备状态不同，不能混在同一分布中比较。冷启动测试还应记录是否执行了 `am force-stop`、应用数据是否保留、dex 与文件页缓存处于什么状态。`force-stop` 能稳定进程状态，却不会自动清空所有系统缓存。

### 查看主线程的互斥延迟归因

Android 17 的 `android.startup.startup_breakdowns` 模块会把启动主线程上的 Slice 与线程状态组合成互不重叠的区间，每个区间只有一个 `reason`。下面的查询按启动和原因汇总墙钟时间：

```sql
INCLUDE PERFETTO MODULE android.startup.startup_breakdowns;

WITH reason_totals AS (
  SELECT
    startup_id,
    reason,
    SUM(dur) AS reason_dur
  FROM android_startup_opinionated_breakdown
  GROUP BY startup_id, reason
)
SELECT
  startup_id,
  reason,
  ROUND(reason_dur / 1e6, 3) AS reason_ms,
  ROUND(
    100.0 * reason_dur
      / SUM(reason_dur) OVER (PARTITION BY startup_id),
    1
  ) AS startup_share_pct
FROM reason_totals
ORDER BY startup_id, reason_dur DESC;
```

这个表适合筛选候选原因，命中项仍要回到对应的 `slice_id` 或 `thread_state_id` 查看。标准库源码也明确建议采集 Binder、ART、`am` 和 `view` 事件；数据源不足会降低归因粒度。

### 沿时间线验证启动阶段

把启动区间固定到顶部后，按以下关系阅读：

- `system_server` 决定启动目标进程，Zygote 接收请求并创建进程。`task_newtask` 与 `task_rename` 可以确认内核看到的创建和改名时刻，但它们不等同于完整的进程启动原因。
- 应用主线程处理 `bindApplication`、组件安装和 Activity 生命周期。框架 Trace Slice 是否细到某个 `ContentProvider.onCreate()`，取决于平台插桩与应用自定义 Trace；不能假定每个 Provider 都自动拥有独立 Slice。
- 主线程通过 Choreographer 处理首帧，`RenderThread` 执行渲染工作。TTID 所在的 `frame_id` 能把启动分析接到帧分析。
- SurfaceFlinger 的 FrameTimeline 和 Flow 可确认应用帧进入合成后的结果。`BlastBufferQueue` 提交、合成和物理显示是不同事件，不能用“提交后的下一个 VSYNC 必然显示”替代帧令牌证据。

启动主线程长时间 `Running` 时，展开 Slice 或采样调用栈找类加载、布局、资源解析和应用初始化。长时间 `Runnable` 时，查看同一时间的 CPU 运行者、唤醒到运行延迟与优先级。`S` 状态应继续追唤醒方；`D` 状态应联合块设备、文件系统或内核栈确认等待对象。

### 把结论落到代码

启动结论应包含具体区间和调用来源，例如：

- 某个初始化 Slice 占用主线程 CPU，并由应用代码或库调用栈确认，可考虑按首屏依赖拆分初始化时机。
- 同步 Binder 的客户端墙钟时间较长，且服务端运行时间短、客户端 `Runnable` 长，排查重点是调度与 CPU 竞争。
- 文件系统事件与主线程 `D` 区间重叠，调用栈指向数据库或配置写入，再评估移动线程、批量提交或避免启动期同步。

“`onCreate()` 很长”只描述现象；缺少子区间、线程状态或调用栈时，还不足以选择修改点。

## 13.5.3 流畅性：按 FrameTimeline deadline 判断帧

Android 12 / API 31 起，FrameTimeline 为应用和 SurfaceFlinger 记录 Expected Timeline 与 Actual Timeline。Expected Slice 表示调度器给这一帧的时间窗口，起点是 Choreographer 回调计划运行的时刻；Actual Slice 覆盖应用从 `doFrame` 开始到 GPU 完成或向 SurfaceFlinger 提交的较晚时刻。

帧预算不能固定写成“60 Hz 等于 16.67 ms，120 Hz 等于 8.33 ms”后逐帧套用。调度偏移、刷新率切换、可变刷新率和预测更新都会改变具体帧的截止时刻。Expected Timeline 已经携带该帧的时间窗口，Actual 相对 Expected 的结束差值才是这条 Trace 的直接证据。

### 用标准库统计错过截止时刻的帧

下面的查询按 `upid` 统计帧数和正向 overrun，避免把同名进程实例合在一起：

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;

SELECT
  f.upid,
  f.process_name,
  COUNT(*) AS frame_count,
  SUM(CASE WHEN o.overrun > 0 THEN 1 ELSE 0 END) AS missed_frame_count,
  ROUND(
    100.0 * SUM(CASE WHEN o.overrun > 0 THEN 1 ELSE 0 END) / COUNT(*),
    2
  ) AS missed_frame_pct,
  ROUND(AVG(f.dur) / 1e6, 3) AS avg_actual_ms,
  ROUND(MAX(o.overrun) / 1e6, 3) AS max_overrun_ms
FROM android_frames AS f
JOIN android_frames_overrun AS o
  USING (frame_id)
GROUP BY f.upid, f.process_name
ORDER BY missed_frame_count DESC, frame_count DESC;
```

`overrun` 为正表示 Actual 的结束晚于 Expected 的结束；负值表示在截止时刻前完成。`android_frames` 会按帧和进程聚合多个 Layer，同时保留 `actual_frame_timeline_count`，因此进程级统计不会因为同一帧更新多块 Surface 而简单重复计数。

### 用 Layer 与 Jank 类型缩小范围

一个进程可能在同一帧更新多个 Surface。下面的查询保留原始 Actual Timeline 的 Layer、呈现结果和 Jank 类型，适合检查系统设置进程：

```sql
SELECT
  a.upid,
  p.name AS process_name,
  a.surface_frame_token,
  a.display_frame_token,
  ROUND(a.dur / 1e6, 3) AS actual_ms,
  a.jank_type,
  a.present_type,
  a.on_time_finish,
  a.prediction_type,
  a.gpu_composition,
  a.layer_name
FROM actual_frame_timeline_slice AS a
LEFT JOIN process AS p
  USING (upid)
WHERE p.name = 'com.android.settings'
ORDER BY a.ts;
```

相同 `surface_frame_token` 出现多行时，要用 `layer_name` 区分 Surface。`display_frame_token` 可连接 SurfaceFlinger 的 DisplayFrame。应用 Actual Slice 变红表示该进程被归因为掉帧来源；黄色表示应用帧受 SurfaceFlinger 掉帧影响；浅绿色表示帧率可能平稳但呈现延迟增加。颜色用于导航，自动化统计应读取字段。

Perfetto 的 FrameTimeline 文档仍把 `SurfaceView` 列为不支持对象。游戏、视频和相机等大量使用独立 Surface 的场景，应联合应用帧节奏、BufferQueue、GPU、SurfaceFlinger 与显示事件，不能把缺少应用 FrameTimeline 记录解释为没有掉帧。

### 从帧结果回看线程

选中异常 Actual Slice 后，按同一帧令牌查看 `Choreographer#doFrame`、应用主线程、`RenderThread`、GPU 和 SurfaceFlinger：

- 主线程 `Running` 长：检查输入、动画、布局、绘制、Compose 重组或应用自定义 Slice。
- 主线程 `Runnable` 长：查看唤醒时刻、CPU 竞争、优先级和任务放置。
- 主线程等待 `RenderThread`：检查 `DrawFrame`、GPU 队列、纹理上传和同步栅栏。
- 应用按时完成但显示帧晚：沿 Flow 查看 SurfaceFlinger、HWC、DisplayHAL 和预测结果。
- `BufferStuffing`：应用持续提交快于显示消费，帧可能保持节奏却增加输入到显示延迟；缩短单帧 CPU 时间未必能消除队列积压。

FrameTimeline 解释“哪一帧、由哪一侧错过哪个预测”。它不会自动指出应用函数。函数级归因还要依赖 Slice、CPU 采样、锁、Binder 或 GPU 事件。

## 13.5.4 Binder：分开看客户端等待与服务端执行

Binder 同步事务横跨客户端调用、驱动传递、服务端线程调度、服务端执行和回复。客户端 `client_dur` 是调用方看到的墙钟时间，服务端 `server_dur` 是服务端处理端的墙钟时间，两者不能互换。`oneway` 事务没有同步回复，应单独观察发送频率、服务端队列和线程池压力。

Android 17 的 `android.binder` 模块输出 `android_binder_txns`，其中包含事务 ID、双方进程与线程、同步标记、客户端与服务端耗时，以及 Trace 中能解析到的 AIDL 接口和方法名。

### 统计调用量与耗时

下面的查询按客户端进程、同步类型和端点统计事务，未记录 AIDL 名称的事务保留为单独分组：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  client_upid,
  client_process,
  CASE WHEN is_sync THEN 'sync' ELSE 'oneway' END AS txn_type,
  COALESCE(aidl_name, '未解析 AIDL 名称') AS endpoint,
  COUNT(*) AS txn_count,
  ROUND(AVG(client_dur) / 1e6, 3) AS avg_client_ms,
  ROUND(MAX(client_dur) / 1e6, 3) AS max_client_ms,
  ROUND(AVG(server_dur) / 1e6, 3) AS avg_server_ms
FROM android_binder_txns
GROUP BY
  client_upid,
  client_process,
  is_sync,
  COALESCE(aidl_name, '未解析 AIDL 名称')
ORDER BY txn_count DESC, max_client_ms DESC
LIMIT 100;
```

AIDL 名称依赖相应 Trace 标注，空值不代表事务异常。高频小事务常提示调用粒度过细，但是否适合批量化还要考虑数据新鲜度、Parcel 大小和接口语义。低频长事务更适合按事务 ID 检查双方线程。

### 区分排队、服务端执行与客户端调度

下面的查询取最慢的同步事务，并汇总客户端事务区间与服务端回复区间中的线程状态：

```sql
INCLUDE PERFETTO MODULE android.binder;

WITH slowest_sync AS (
  SELECT binder_txn_id
  FROM android_binder_txns
  WHERE is_sync
  ORDER BY client_dur DESC
  LIMIT 1
)
SELECT
  s.binder_txn_id,
  s.client_tid,
  s.server_tid,
  s.thread_state_type,
  s.thread_state,
  ROUND(s.thread_state_dur / 1e6, 3) AS state_ms,
  s.thread_state_count
FROM android_sync_binder_thread_state_by_txn AS s
JOIN slowest_sync
  USING (binder_txn_id)
ORDER BY s.thread_state_type, s.thread_state_dur DESC;
```

`binder_txn` 行描述客户端一侧，`binder_reply` 行描述服务端一侧。服务端区间短、客户端同步等待长时，还需查看事务送达前后的调度和 Binder 线程池。服务端 `Runnable` 长指向 CPU 竞争；服务端 Slice 内出现 Monitor Contention 时，应检查锁持有者；服务端 `Running` 长则继续分析执行代码。客户端回复已到达后仍长时间 `Runnable`，延迟来自客户端重新获得 CPU。

评估 `oneway` 堆积时，不能套用同步回复模型。应沿服务端 Binder 线程查看异步事务 Slice 的排队、处理频率与目标对象的串行规则，并结合线程池、锁竞争和同一服务进程中的其他流量。

## 13.5.5 内存：把占用、分配与保留分开

内存 Trace 中常见的三类数据回答不同问题：

- RSS、匿名 RSS、文件 RSS、Swap 描述进程在采样时刻的驻留与交换情况。
- heapprofd 记录一段时间内的 native 分配和释放样本，也可在 Android 12 及以上记录 ART 分配调用栈。
- Android 11 及以上的 ART Heap Dump 记录一次 Java/Kotlin 活对象引用图，不包含对象字段数据，也不提供分配调用栈。

RSS 上升只能说明进程驻留内存发生变化。页缓存、分配器碎片、线程栈、图形内存映射、匿名页和存活对象都可能贡献变化。泄漏判断需要可重复增长、生命周期边界和分配或保留证据。

### 采集进程内存计数

下面的配置每秒读取一次 `/proc/<pid>/status` 中的进程计数：

```protobuf
data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
      proc_stats_poll_ms: 1000
    }
  }
}
```

采样会漏掉短于周期的尖峰。支持 `rss_stat` 的内核可用事件驱动计数补充短时变化，采集成本也会增加。`scan_smaps_rollup: true` 可加入 PSS 等 `/proc/<pid>/smaps_rollup` 数据，但 Android 17 的 `ProcessStatsConfig` 源码明确写明：系统 `traced_probes` 默认无法读取这些文件，通常需要 root 或通过 `PTRACE_MODE_READ` 检查，还可能受 procfs `hidepid` 限制。没有权限时不能把缺失 PSS 解释为零。

下面的查询列出系统设置进程的 RSS、匿名 RSS、文件 RSS 和 Swap 时间序列：

```sql
SELECT
  c.ts,
  p.upid,
  p.pid,
  p.name AS process_name,
  t.name AS counter_name,
  ROUND(c.value / 1024.0, 1) AS value_kib
FROM counter AS c
JOIN process_counter_track AS t
  ON c.track_id = t.id
JOIN process AS p
  USING (upid)
WHERE
  p.name = 'com.android.settings'
  AND t.name IN (
    'mem.rss',
    'mem.rss.anon',
    'mem.rss.file',
    'mem.swap'
  )
ORDER BY c.ts, t.name;
```

进程统计协议中的输入字段以 KiB 表示；Android 17 的 `SystemProbesParser::ParseProcessStats()` 会乘以 1024，再把值写入 Trace Processor。因此查询除以 1024 后得到 KiB。长 Trace 中要按 `upid` 分开进程实例，不能只按名称或 PID 聚合。

### 用 heapprofd 定位 native 分配调用栈

下面的配置对系统设置进程采样 native 分配，每 10 秒生成一个剖面快照：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 30000

data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      process_cmdline: "com.android.settings"
      sampling_interval_bytes: 4096
      continuous_dump_config {
        dump_phase_ms: 10000
        dump_interval_ms: 10000
      }
    }
  }
}
```

4096 字节是这份配置显式指定的平均采样间隔，不是精确记录每次分配。间隔越小，数据量和被测进程开销越高。量产 `user` 构建只允许分析 `debuggable` 或声明 `<profileable android:shell="true"/>` 的应用；系统服务通常需要调试构建和相应权限。

heapprofd 默认分析 native `malloc/free` 或 `new/delete`。将 `heaps: "com.android.art"` 加入 `heapprofd_config` 后，可在 Android 12 及以上分析 Java 分配抖动。ART 分配剖面记录创建对象时的调用栈，不记录对象何时被 GC，也不能直接回答“谁仍在持有对象”。

怀疑 Java 对象保留时，应采集 ART Heap Dump，沿 `heap_graph_object`、`heap_graph_reference` 或标准库的类汇总树查看到 GC Root 的引用关系。Heap Dump 解释存活图，分配剖面解释创建来源；两者合用才能区分高分配率与持续保留。

### 解释不一致的内存数字

heapprofd 的未释放采样、分配器统计与 RSS 可能不同：

- 分配器会按页向内核申请内存，碎片和线程缓存可能使 RSS 高于应用仍请求的字节数。
- ZRAM 与换出可能让 RSS 下降，而分配器视角中的未释放对象没有同步下降。
- 文件映射和共享页计入 RSS 的方式与 native heap 不同。
- Java Heap Dump 的 `self_size` 不覆盖所有 native 附属内存；Android 13 及以上能为部分 `NativeAllocationRegistry` 对象呈现额外 native 大小。

因此，RSS 曲线适合确认何时增长，heapprofd 与 Heap Dump 用于解释增长来源，PSS 用于估算共享页按比例分摊后的进程占用。三个数字不能互相替代。

## 13.5.6 I/O：设备队列与文件操作需要两层证据

块设备事件描述请求何时进入和离开设备队列，文件系统事件描述更高层的读写、同步和页操作。单独看到线程进入 `D` 状态，无法确认它正在等待存储；单独看到块设备繁忙，也无法确认请求来自目标进程。

### 确认设备提供的事件

不同设备可能使用 F2FS、EROFS、ext4 或厂商事件。录制前可用下面的命令查看设备公开的文件系统和块事件：

```bash
adb shell 'cat /sys/kernel/tracing/available_events' \
  | grep -E '^(block|f2fs|ext4|erofs):'
```

命令输出决定 `ftrace_events` 能写哪些事件。内核配置、SELinux 和构建类型都可能缩小列表。不要复制另一台设备的事件名称后默认采集成功；Trace 的 `stats` 表还应检查 `unknown_ftrace_events` 与 `failed_ftrace_events`。

### 查看块设备队列

Android 17 的 `linux.block_io` 模块基于 `track.type = 'block_io'` 的 Slice 计算每台设备在队列或设备中的活动操作数。下面的查询把设备号拆成 major/minor：

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

这张表回答“哪台块设备在什么时刻还有多少请求”，不包含应用进程和文件路径。连续高队列深度可能增加完成延迟，也可能来自系统后台写回、安装、日志或其他进程。

### 把设备活动关联到调用方

应用归因应同时满足时间和调用证据：

- 目标线程的文件、SQLite、资源加载或自定义 Trace Slice 与设备活动重叠。
- 线程在同一区间进入 `D`，`sched_blocked_reason` 或内核调用栈指向块层、文件系统或页故障路径。
- 文件系统事件携带的 inode、设备或操作类型与块设备请求相符。
- 停止该操作或移动到对照场景后，目标区间和设备压力同步变化。

`SharedPreferences.commit()` 会同步等待结果，适合检查主线程调用；`apply()` 先更新内存并安排磁盘写入，但进程生命周期中的 `QueuedWork` 等待仍可能让异步写入影响组件停止。选择 `apply()` 不能替代 Trace 验证。SQLite 事务、`fsync`、首次资源页故障和系统回写也要按各自事件分析。

全量 `raw_syscalls/sys_enter` 与 `sys_exit` 能补充系统调用证据，事件量通常很高。应缩短录制时间、提高缓冲区容量并限定复现场景；需要文件路径时，再结合 inode 映射、eBPF 或应用 Trace，而不要从 block Slice 猜文件名。

## 13.5.7 功耗：频率、空闲与休眠要联合解释

CPU 频率高只表示策略在该区间选择了较高频点，不能单独推出 CPU 正在执行大量工作。调度负载、Governor、Boost、热限制、CPU 容量和任务所在集群都会影响频率。功耗分析至少要联合 CPU 运行时间、频率、空闲状态、Suspend 和唤醒锁。

下面的配置采集 CPU 频率、空闲、系统休眠与内核唤醒锁：

```protobuf
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}
duration_ms: 30000

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
    kernel_wakelocks_config {
      poll_ms: 1000
    }
  }
}
```

部分设备不会公开完整的 suspend、wakeup source 或 idle 事件。USB 调试连接本身也可能持有唤醒锁，导致设备无法进入完整系统休眠；测试报告应写明供电与连接方式。

### 汇总休眠与唤醒锁

下面的查询把系统休眠区间和每个唤醒锁的持有时间放进同一结果集：

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

`android_suspend_state` 把 Trace 时间补成 `awake` 与 `suspended` 区间。`android_kernel_wakelocks.held_dur` 是相邻采样点之间的累计持有时间增量；`awake_dur` 从区间长度中排除 Suspend，`held_ratio` 以 `awake_dur` 为分母。唤醒锁持有与耗电相关，但仍需找到持有者和该区间中的工作内容。

### 查看 CPU 频率驻留

下面的查询按 CPU 计算录制区间内的时间加权平均频率和最高频点：

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

`freq` 的单位是 kHz。加权平均频率用于比较相同设备和场景中的策略结果，不是能量估算。CPU 可能在高频点空闲，也可能在低频点持续运行；还要关联 `cpu_idle_counters`、`sched`、功率轨和电池电流。

系统无法进入 Suspend 时，按时间顺序检查屏幕状态、用户空间唤醒锁、内核唤醒锁、活跃定时器和 `android.wakeups` 提供的唤醒或休眠失败原因。短时 Suspend 失败与长期唤醒锁是两类现象，优化位置也不同。

## 13.5.8 多进程协同：用稳定标识连接时间线

启动、Binder 和显示都跨进程。可靠的联合分析依赖稳定连接关系：

- 启动使用 `startup_id`，再通过 `android_startup_processes` 关联参与进程的 `upid`。
- Binder 使用 `binder_txn_id` 与 `binder_reply_id`，分别查看客户端和服务端。
- 帧使用 `surface_frame_token`、`display_frame_token` 和 Flow，连接应用 Surface 与 SurfaceFlinger DisplayFrame。
- 调度使用 `utid` 与 `upid`，避免 TID、PID 复用造成误关联。

Perfetto UI 的 Pin 功能适合把目标应用主线程、`system_server` Binder 线程、`RenderThread` 和 SurfaceFlinger 固定在同一视野。选中 `Runnable` 区间后查看唤醒事件，能从结果线程回到唤醒者；Critical Path 视图可辅助阅读依赖，但结论仍要核对原始 Slice、线程状态和 Flow。

跨进程区间应在同一录制会话中采集。合并来自不同设备或不同录制会话的 Trace 时，需要可验证的时钟快照和同步事件；仅按文件起点平移，无法支撑毫秒级因果判断。

联合分析可采用两遍阅读：

1. 从用户动作向后走，确认请求经过哪些进程和线程，找到可观察终点。
2. 从异常终点向前追，沿帧令牌、Binder 事务、Flow 和唤醒关系寻找贡献延迟的区间。

两遍都指向同一段代码或系统事件时，修改目标才足够明确。路径中断通常表示数据源不足、插桩缺失或标识选错，也可能说明原先假设的因果关系不成立。

## 13.5.9 结论记录模板

一条适合进入缺陷单或评审记录的 Perfetto 结论应包含：

- 平台与工具：设备构建、Android 版本、内核版本、`trace_processor` 版本。
- 复现场景：动作起止、次数、设备状态和对照条件。
- 时间证据：Trace 时间范围、`upid` / `utid`、启动 ID、事务 ID 或帧令牌。
- 归因证据：Slice、线程状态、调用栈、标准库查询、Flow 或设备事件。
- 结论边界：缺失数据源、采样误差、权限限制和仍待验证的推断。
- 验证结果：修改前后使用相同条件重复测量，报告分布及波动，不只报告最好一次。

这种记录方式能区分“Trace 中观察到的事实”“由多条证据支持的解释”和“准备验证的修改”。三者分开写，后续复盘时才能判断结论是否仍适用于新平台。

## 参考资料

- [PerfettoSQL 标准库文档](https://perfetto.dev/docs/analysis/stdlib-docs)
- [FrameTimeline 数据源与 Jank 类型](https://perfetto.dev/docs/data-sources/frametimeline)
- [Native 与 ART 分配剖面](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [ART Heap Dump](https://perfetto.dev/docs/data-sources/java-heap-profiler)
- [进程内存计数](https://perfetto.dev/docs/data-sources/memory-counters)
- [Android 17 `android.startup.startups` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startups.sql)
- [Android 17 `android.startup.startup_breakdowns` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startup_breakdowns.sql)
- [Android 17 `android.frames.timeline` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)
- [Android 17 `android.frames.per_frame_metrics` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/per_frame_metrics.sql)
- [Android 17 `android.binder` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)
- [Android 17 `ProcessStatsConfig` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/process_stats/process_stats_config.proto)
- [Android 17 `SystemProbesParser` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/importers/proto/system_probes_parser.cc)
- [Android 17 `linux.block_io` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/block_io.sql)
- [Android 17 `android.kernel_wakelocks` 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/kernel_wakelocks.sql)
- [高爷：熟悉 Perfetto View](https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/)
- [高爷：基于 Choreographer 的渲染流程](https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/)
- [高爷：Binder 调度与锁竞争](https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/)
