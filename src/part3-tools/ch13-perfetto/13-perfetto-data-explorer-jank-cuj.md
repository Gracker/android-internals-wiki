---


title: "Perfetto DataGrid 与 Jank CUJ 标准库"
chapter: "13.13"
section: "13.13"
status: "finalized"
drafted_date: "2026-05-16"
applicable_versions: "Perfetto v54+ / Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-19"
last_verified_against: "Perfetto v54.0 source (ab21398/v54.0); AOSP android-17.0.0_r1 ViewRootImpl/JankTracker/ProfileData/FrameTracker/JankInfo/Cuj/UIInteractionFrameInfoReported"
confidence: medium
sources:
  - type: official
    path: "https://github.com/google/perfetto/releases/tag/v54.0"
  - type: source
    path: "google/perfetto src/trace_processor/metrics/sql/android/jank/android_jank_cuj_init.sql @ ab21398"
  - type: source
    path: "google/perfetto src/trace_processor/metrics/sql/android/jank/internal/counters.sql @ ab21398"
  - type: source
    path: "google/perfetto src/trace_processor/metrics/sql/android/android_jank_cuj.sql @ ab21398"
  - type: source
    path: "google/perfetto src/trace_processor/perfetto_sql/stdlib/android/cujs/threads.sql @ ab21398"
  - type: source
    path: "google/perfetto src/trace_processor/perfetto_sql/stdlib/android/memory/heap_graph/heap_graph_stats.sql @ ab21398"
  - type: official
    path: "https://raw.githubusercontent.com/google/perfetto/v54.0/docs/data-sources/frametimeline.md"
  - type: research
    path: "intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md"
tags: [perfetto, datagrid, jank, cuj, sql, frametimeline]
related_chapters: ["7.3", "7.4", "13.3", "13.7", "13.9", "13.10", "13.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/官方文档"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-07-11"
task6_result: "pass-light-edit"
last_task6_at: "2026-07-11T12:06:00+08:00"
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-11"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-11T12:37:01+08:00"
task2b_result: fixed-lite
task2b_state: "fixed"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
last_task2b_lite_at: "2026-05-28"
last_task6_review_log: "logs/review/2026-07-11-12-review.md"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-07-11 Task6 revisiting-review (round 6): pass-light-edit。Task9 idle-audit auto-fix(CUJ counter API: beginSection只写slice, counter需setCounter)回流后写作层复审通过；L1扫描命中'链路'1处(报告链路→报告路径)已修复；'对齐'3处均为技术语境(data/vsync alignment)非黑话用法；高频词达标；L2开头/节奏/结构/读者引导通过；outline 6/6锚点全覆盖；否定-纠正结构2处(限额内)；无L1/L2遗留, 无L3/L4回炉项。送Task9终审确认。"
last_task9_autofix_at: "2026-07-11"
last_task9_review_log: "logs/deep-review/2026-07-11-12-deep-review.md"
task9_review_notes: "2026-07-11 Task9 deep-review: pass-tech-review。P0/P1/P2 0；复核 Perfetto v54.0 DataGrid/ExplorePage、CUJ counter metrics、android.cujs.* 与 AOSP android-17.0.0_r1 JankTracker/Trace API 锚点；Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-07-11-12-deep-review.md。 | 2026-07-11 Task9 idle-audit AUTO-FIX: P0 1 / P1 0 / P2 0；修正自定义 CUJ marker 与 counter API 数据流：`Trace.beginSection()` / `endSection()` 只写 slice，counter metrics 需要 `Trace.setCounter(\"J<my_cuj>#totalFrames\", value)` 写出 `J<*>#*` process counter；同时把 FrameTimeline 文档来源从 Perfetto main 锚定到 v54.0；回到 Task6 复审。详见 logs/deep-review/2026-07-11-10-audit.md。 | 2026-07-10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；复核 Perfetto v54 DataGrid/ExplorePage summarizer API、android.cujs.*、weighted jank counter 与 AOSP JankTracker/FrameTimeline 锚点；Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-07-10-04-deep-review.md。 | 2026-07-10 Task9 idle-audit AUTO-FIX: P0 1 / P1 0 / P2 0；修正 Perfetto v54.0 ExplorePage 执行模型源码锚点：`engine.analyzeStructuredQuery` / `NodePanel.updateQuery()` 不属于当前 v54.0 调用链，改为 summarizer API（`createSummarizer` / `updateSummarizerSpec` / `querySummarizer`）与 `SQLDataSource` 物化表展示路径；回到 Task6 复审。详见 logs/deep-review/2026-07-10-03-audit.md。 | 2026-06-19 Task9 deep-review: pass-tech-review。复核 Perfetto v54.0 android.cujs.base / cuj_frame_counters / internal counters / ExplorePage，以及 AOSP android-17.0.0_r1 ViewRootImpl / JankTracker / FrameTracker / stats atoms；无 P0/P1/P2。Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-06-19-12-deep-review.md。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 1 / P1 0 / P2 0；修正 statsd 侧不存在的 `frame_missed` atom 标识，改为 android-17.0.0_r1 `UI_INTERACTION_FRAME_INFO_REPORTED` atom 及 `missed_frames` / `app_missed_frames` / `sf_missed_frames` 字段；回到 Task6 复审。详见 logs/deep-review/2026-06-19-07-deep-review.md。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 2 / P1 0 / P2 0；修正 android-17.0.0_r1 ViewRootImpl traversal 回调源码锚点（TraversalCallback#onVsync）与 JankTracker JankType 判定表（补入 kMissedDeadline / kMissedDeadlineLegacy 边界）；回到 Task6 复审。详见 logs/deep-review/2026-06-19-06-deep-review.md。 | 2026-06-18 Task9 idle-audit auto-fix：修正 android-17.0.0_r1 ViewRootImpl 行号、JankTracker 方法名、JankInfo/Cuj 源码锚点、Perfetto v54 CUJ counter 进程过滤和 weighted jank metric 转换口径；回到 Task6 复审。 | 2026-05-28 Task9 auto-fix：修正 android.cujs.base 源码路径、FrameTimeline/JankStats 版本表和 FrameTimeline trace data source 配置口径；回到 Task6 复审。 | 2026-05-28 06 Task9 auto-fix: 修正 JankStats API 级别，收窄 Perfetto v54.0 weighted_missed_frames 字段版本边界，回到 Task6 复审。 | 2026-05-28 17 Task9 deep-review: pass-tech-review。复核 Perfetto v54.0 DataGrid、CUJ counter metrics、android.cujs.* 与 FrameTimeline/JankStats 版本边界，无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 0 / P1 1 / P2 0；Perfetto v55.0 DataExplorer 只保留为非 Android 17 范围边界，移除 v55 操作建议，正文结论收窄到 v54.0 / Android 17；回到 Task6 复审。详见 logs/deep-review/2026-06-19-05-deep-review.md。"
p0: 0
p1: 0
p2: 0
task9_reviewed_at: "2026-07-11T12:37:01+08:00"
last_task6_audit: "2026-07-02"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-11
last_task9_audit: "2026-07-11"
last_task2b_verifier_at: "2026-07-11T11:34:06+08:00"
task2b_verifier_notes: "Task9 idle-audit auto-fix on 2026-07-11 set task6_state: revisiting + pipeline_stage: task6_pending, but status remained finalized. Corrected to ready-for-review for Task6 re-review."
auto_promoted_by: "openclaw-task9"
auto_promoted_date: "2026-07-11"
last_idle_audit_at: "2026-08-08"
last_idle_audit_run_id: "20260808-223555-idle-audit-4ec8c98d"
last_idle_audit_result: "pass-no-new-safe-fix"
last_idle_audit_log: "logs/audit/2026-08-08-20260808-223555-idle-audit-4ec8c98d-idle-audit.md"
updated_by: "aiw-polish-idle-audit"
updated_date: "2026-08-08"
---
# 13.13 Perfetto DataGrid 与 Jank CUJ 标准库

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，分析器锚点是该源码标签中的 Perfetto。上游 Perfetto v54.0 只作为版本演进参照：它引入了 DataGrid 改进、Jank CUJ 相关线程、基于计数器的加权卡顿、`heap_graph_stats` 和两种采样格式导入能力。Android 17 的 Perfetto 已包含 v54 之后的改动，不能用“Android 17 等于 v54.0”概括。

分析时要区分三层：

- DataGrid 是结果表组件，提供筛选、排序、透视等交互；
- Data Explorer 是节点式查询编辑器，负责组织结构化查询和中间结果；
- PerfettoSQL 标准库与指标脚本定义字段语义，是可复核结论的依据。

界面有助于缩小范围，SQL、trace 和源码决定证据是否成立。

## DataGrid 与 Data Explorer 的版本边界

Perfetto v54.0 的变更日志明确记录了 DataGrid 的三类改进：可配置透视表、`glob` / `contains` / `not-contains` 过滤器、过滤器的 distinct value picker（非重复值选择器）。同期的 snap-to-boundaries（吸附到边界）属于时间范围选择功能，与 DataGrid 过滤无关。[Perfetto v54.0 变更日志](https://github.com/google/perfetto/blob/v54.0/CHANGELOG)

v54.0 标签中已经存在节点式查询插件，插件标识为 `dev.perfetto.ExplorePage`。Android 17 固定标签把对应插件命名为 `dev.perfetto.DataExplorer`，并包含图编辑、导入导出、固定链接和仪表盘等实现。两个版本的 `QueryExecutionService` 都把节点图转成 `PerfettoSqlStructuredQuery`，通过 Trace Processor 的 `summarizer` 同步、查询和物化；DataGrid 再通过 `SQLDataSource` 读取物化表。[v54.0 ExplorePage 源码](https://github.com/google/perfetto/tree/v54.0/ui/src/plugins/dev.perfetto.ExplorePage) [Android 17 DataExplorer 源码](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/ui/src/plugins/dev.perfetto.DataExplorer/)

这套执行方式带来两个工程约束：

- 节点图生成的 SQL、物化表名和界面状态可能随 UI 版本变化，报告要记录 Perfetto UI 与 Trace Processor 版本；
- 可长期维护的资产应是输入 trace、明确的 SQL、字段单位和源码 tag，不能依赖某个自动生成的物化表名。

DataGrid 最适合承载“窄表”：一行表示一个 CUJ、一帧或一段线程状态，一列表示一个可解释维度。把未经约束的宽表直接做透视，重复行和多层 FrameTimeline 数据很容易放大计数。

## Android 17 系统 Jank CUJ 的输入

Android 17 的 Jank CUJ 指标汇合三组独立数据：

| 输入 | 产生者 | 在指标中的用途 |
|---|---|---|
| `J<CUJ_NAME>`、`FT#beginVsync`、`FT#endVsync` 等标记 | `InteractionJankMonitor` / Java `FrameTracker` | 定义 CUJ 名称、状态、进程、UI 线程和 vsync 边界 |
| `J<CUJ_NAME>#totalFrames`、`#weightedAppJank` 等计数器 | Java `FrameTracker.finishTraced()` | 提供 CUJ 结束后的聚合计数 |
| expected / actual FrameTimeline、`jank_type`、`jank_score` | SurfaceFlinger FrameTimeline | 给出逐帧时序与 App / SF 分类 |

HWUI 的 C++ `JankTracker` 是另一套帧统计实现。它计算 `kMissedDeadline`、`kSlowUI`、`kSlowSync`、`kSlowRT` 等本地帧指标，并通过 FrameMetrics 报告接口上报；它不会自动生成 `android_jank_cuj` 所需的 Java FrameTracker 计数器。两个类名相近，数据来源与职责不能混写。[Android 17 Java FrameTracker](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/jank/FrameTracker.java) [Android 17 HWUI JankTracker](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/JankTracker.cpp)

`android.cujs.base` 对输入有明确限制：

- CUJ 必须是 `process_track` 上持续时间大于零、名称匹配 `J<*>` 的 slice；
- 进程名必须匹配 `com.android.*` 或 `com.google.android*`；
- `FT#end`、`FT#cancel`、begin/end vsync、layer id 和 UI thread 标记用于修正状态与边界；
- `android_jank_cuj.state` 的实际输出是 `completed`、`canceled` 或 `NULL`。

第三方 App 即使写出同名标记，也不会自动进入这张表。该过滤是 Android 17 标准库源码行为，不是 DataGrid 的显示条件。[Android 17 `android.cujs.base`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/cujs/base.sql)

## 建立可筛选的 CUJ 窄表

这条查询使用 Android 17 公共标准库，列出系统 CUJ 及其 RenderThread。它适合作为 DataGrid 或 Data Explorer 的首张表。

```sql
INCLUDE PERFETTO MODULE android.cujs.base;
INCLUDE PERFETTO MODULE android.cujs.threads;

SELECT
  c.cuj_id,
  c.cuj_name,
  c.process_name,
  c.state,
  c.ts,
  c.dur,
  c.begin_vsync,
  c.end_vsync,
  r.utid AS render_thread_utid,
  r.track_id AS render_thread_track_id
FROM android_jank_cuj AS c
LEFT JOIN android_jank_cuj_render_thread AS r USING (cuj_id)
ORDER BY c.ts;
```

`LEFT JOIN` 会保留没有 RenderThread 记录的 CUJ。缺失可能来自场景没有走对应 HWUI 路径、线程名不匹配、CUJ 被截断或采集数据不足，不能直接解释为 RenderThread 未参与。

`android.cujs.threads` 的公共入口包括 `android_jank_cuj_app_thread(thread_name)` 和 `android_jank_cuj_render_thread`。GPU completion、HWC release、SurfaceFlinger main、SurfaceFlinger GPU completion 与 RenderEngine 等表由 `android/android_jank_cuj.sql` 的指标初始化过程继续创建。耐久脚本不要直接依赖 `_android_sf_process`、`_android_sf_thread()` 这类下划线开头的内部对象；它们没有公共兼容承诺。

## 基于计数器的加权卡顿

Android 17 的 Java `FrameTracker.finishTraced()` 在 CUJ 收尾后写出：

- `totalFrames`、`missedFrames`、`missedAppFrames`、`missedSfFrames`；
- `maxSuccessiveMissedFrames`、`maxFrameTimeMillis`、`totalAnimTime`；
- `weightedAppJank`、`weightedSfJank`。

计数器名称是 `J<CUJ_NAME>#COUNTER_NAME`。标准库先按 `upid` 和 CUJ 名找轨道，再由指标脚本把计数器匹配到对应 CUJ。相邻的同名 CUJ 会用下一个 CUJ 的结束时间限制搜索范围。`com.android.*` 与 Pixel Launcher 从 CUJ 结束时刻开始找计数器；其他已获标准库准入的 Google 进程允许向前回看 4 ms。这是 Android 17 SQL 中的兼容规则，不应复制成第三方 App 的通用时序约定。

这条查询运行 Android 17 Jank CUJ 指标，并把加权速率换算成当前 CUJ 窗口内的加权丢帧总量。

```sql
SELECT RUN_METRIC('android/android_jank_cuj.sql');

SELECT
  cuj_id,
  cuj_name,
  state,
  total_frames,
  missed_frames,
  missed_app_frames,
  missed_sf_frames,
  weighted_missed_app_frames * anim_duration_ms / 1000.0
    AS weighted_missed_app_frames_total,
  weighted_missed_sf_frames * anim_duration_ms / 1000.0
    AS weighted_missed_sf_frames_total,
  frame_dur_max / 1e6 AS frame_dur_max_ms
FROM android_jank_cuj_counter_metrics
ORDER BY
  COALESCE(weighted_missed_app_frames_total, 0) +
  COALESCE(weighted_missed_sf_frames_total, 0) DESC
LIMIT 20;
```

`weighted_missed_app_frames` 与 `weighted_missed_sf_frames` 在表中是速率：原始整数计数器除以 `1000` 后按 jank/s 解释。乘以 `anim_duration_ms / 1000` 才得到该次 CUJ 的加权总量。两个 `*_total` 是查询别名，不是表字段。[Android 17 计数器指标](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/metrics/sql/android/jank/internal/counters.sql) [Android 17 指标输出](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/metrics/sql/android/android_jank_cuj.sql)

加权总量适合排序严重程度，不提供根因。一次高分可能来自一个很重的超时，也可能来自连续多帧延迟。还要展开 FrameTimeline、相关线程和调用栈。

指标同时提供计数器指标、trace 指标与时间线指标：

- 计数器指标来自 Java FrameTracker 的事后汇总；
- trace 指标来自 `android_jank_cuj_frame`，包含 DoFrame、DrawFrame、GPU fence 与 FrameTimeline 的组合；
- 时间线指标直接按 `android_jank_cuj_frame_timeline` 聚合。

三者不一致时，要检查标记、计数器、FrameTimeline、回调漏采、trace 截断和分类版本，不能挑一个数覆盖其余数据。

## 从异常 CUJ 展开到异常帧

以下查询列出指标判断为 App missed 或 SF missed 的帧，并保留回调漏采标记。

```sql
SELECT RUN_METRIC('android/android_jank_cuj.sql');

SELECT
  c.cuj_name,
  f.cuj_id,
  f.frame_number,
  f.vsync,
  f.dur / 1e6 AS dur_ms,
  f.dur_expected / 1e6 AS expected_ms,
  f.app_missed,
  f.sf_missed,
  f.jank_score,
  f.sf_callback_missed,
  f.hwui_callback_missed
FROM android_jank_cuj_frame AS f
JOIN android_jank_cuj AS c USING (cuj_id)
WHERE COALESCE(f.app_missed, 0) != 0
   OR COALESCE(f.sf_missed, 0) != 0
ORDER BY f.jank_score DESC, f.dur DESC
LIMIT 50;
```

`app_missed` 与 `sf_missed` 来自 FrameTimeline `jank_type` 的分类函数。它们标出责任侧线索，还没有定位到具体函数、锁、调度或 GPU 等待。`sf_callback_missed` / `hwui_callback_missed` 表示 trace 没捕获到预期回调，不能当成 SurfaceFlinger 或 HWUI 自身掉帧。

Android 17 指标在 expected timeline 缺失时，会用 `16.6 ms` 作为 `dur_expected` 的兼容回退。这个值来自指标源码，不能据此声称设备当时运行在 60 Hz。报告中遇到该回退，应把 expected timeline 缺失列为采集限制。

FrameTimeline 的 `on_time_finish` 也不能单独充当全部 jank 判据。Buffer Stuffing 可能在 App 按期完成时仍被标为 jank；Prediction Error 也有独立语义。优先使用 `jank_type`、`jank_score`、expected/actual 时间线和标准库聚合结果。[Android 17 FrameTimeline 文档](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/docs/data-sources/frametimeline.md) [Android 17 jank type 分类](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/jank_type.sql)

## 用 thread_state 判断时间花在哪里

异常帧有了时间范围后，再把 UI 线程状态裁进帧窗口。这条查询按状态、I/O wait 与 blocked function 汇总相交时间。

```sql
SELECT RUN_METRIC('android/android_jank_cuj.sql');

WITH bad_frame AS (
  SELECT
    f.cuj_id,
    f.frame_number,
    f.ts,
    f.dur,
    mt.utid
  FROM android_jank_cuj_frame AS f
  JOIN android_jank_cuj_main_thread AS mt USING (cuj_id)
  WHERE f.dur > 0
    AND (
      COALESCE(f.app_missed, 0) != 0 OR
      COALESCE(f.sf_missed, 0) != 0
    )
),
intersection AS (
  SELECT
    b.cuj_id,
    b.frame_number,
    st.state,
    st.io_wait,
    st.blocked_function,
    MIN(b.ts + b.dur, st.ts + st.dur) -
      MAX(b.ts, st.ts) AS overlap_dur
  FROM bad_frame AS b
  JOIN thread_state AS st
    ON st.utid = b.utid
   AND st.dur > 0
   AND st.ts < b.ts + b.dur
   AND b.ts < st.ts + st.dur
)
SELECT
  cuj_id,
  frame_number,
  state,
  io_wait,
  blocked_function,
  SUM(overlap_dur) / 1e6 AS overlap_ms
FROM intersection
WHERE overlap_dur > 0
GROUP BY
  cuj_id,
  frame_number,
  state,
  io_wait,
  blocked_function
ORDER BY cuj_id, frame_number, overlap_ms DESC;
```

`Running` 表示线程正在 CPU 上执行；`R` 与 `R+` 表示 Runnable，其中 `R+` 带有被抢占语义；`D` 表示不可中断睡眠。`io_wait = 1` 和 `blocked_function` 能缩小排查范围，但字段缺失不能反向证明没有 I/O、锁或内核等待。Running 占比高也只说明 CPU 执行时间多，函数热点仍需采样剖析。

UI 线程只是应用侧的一部分。RenderThread 要改用 `android_jank_cuj_render_thread.utid`；GPU completion、HWC release 与 SurfaceFlinger 线程则使用指标初始化出的相关线程和 slice 表。每条线程都要在各自边界内做时间交集，不能把 UI 帧窗口机械套到所有线程。

## 第三方 App 的可执行路径

第三方 App 不在 `android_jank_cuj` 默认进程过滤范围。写 `J<*>` slice 或 `J<*>#*` 计数器也不会绕过 `JOIN android_jank_cuj USING (upid)`。单纯模仿系统计数器名称会混淆数据来源，数据仍由应用自己的 `Trace` 调用产生。

第三方 App 更适合组合三种能力：

- AndroidX JankStats 负责应用内帧指标与 UI 状态标签；
- `Trace` 写应用自有命名空间的阶段标记；
- FrameTimeline 与 `thread_state` 在 Perfetto 中完成逐帧和调度分析。

这段代码用公开 `Trace` API 标记一次跨回调的应用交互。标记使用应用命名空间，避免与系统 `J<*>` CUJ 混淆。

```kotlin
private const val FEED_SCROLL = "myapp.cuj.feed_scroll"

fun onScrollStarted(cookie: Int) {
    Trace.beginAsyncSection(FEED_SCROLL, cookie)
}

fun onScrollSettled(cookie: Int) {
    Trace.endAsyncSection(FEED_SCROLL, cookie)
}
```

同名并发交互必须使用不同 cookie，每次 begin 必须有一次匹配的 end。采集配置还要把目标包加入 `atrace_apps`，并启用 `android.surfaceflinger.frametimeline`；否则标记或帧数据会缺失。

随后用以下查询处理 thread track 与 process track 上的自定义 slice，并把它关联到 Android 17 `android_frames` 与 overrun。

```sql
INCLUDE PERFETTO MODULE slices.with_context;
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;

WITH custom_cuj AS (
  SELECT
    ts,
    dur,
    name,
    upid,
    process_name
  FROM thread_or_process_slice
  WHERE process_name = 'com.example.app'
    AND name = 'myapp.cuj.feed_scroll'
    AND dur > 0
)
SELECT
  c.name AS custom_cuj_name,
  f.frame_id,
  f.ts,
  f.dur / 1e6 AS frame_dur_ms,
  o.overrun / 1e6 AS overrun_ms,
  f.ui_thread_utid,
  f.render_thread_utid
FROM custom_cuj AS c
JOIN android_frames AS f
  ON f.upid = c.upid
 AND f.ts < c.ts + c.dur
 AND c.ts < f.ts + f.dur
LEFT JOIN android_frames_overrun AS o USING (frame_id)
ORDER BY f.ts;
```

把包名和标记名称替换为目标 App。`overrun > 0` 表示 actual frame end 晚于 expected frame end；`NULL` 表示无法形成对应 overrun，不能按零处理。这条路径不依赖系统 CUJ 进程白名单，也不会自动获得 Java FrameTracker 的加权计数器。

## `heap_graph_stats` 与 DMA-BUF

Jank 伴随内存上涨时，可以单独引入 `android.memory.heap_graph.heap_graph_stats`。它每行对应一次 ART heap graph，汇总 Java heap、NativeAllocationRegistry、对象数、OOM adj、anon RSS + swap 和 DMA-BUF RSS。

这条查询把主要内存字段换算成 MiB，便于在 DataGrid 中按采样时间比较。

```sql
INCLUDE PERFETTO MODULE android.memory.heap_graph.heap_graph_stats;

SELECT
  p.name AS process_name,
  h.graph_sample_ts,
  h.total_heap_size / 1024.0 / 1024.0 AS total_heap_mib,
  h.reachable_heap_size / 1024.0 / 1024.0 AS reachable_heap_mib,
  h.reachable_native_alloc_registry_size / 1024.0 / 1024.0
    AS reachable_native_registry_mib,
  h.anon_rss_and_swap_size / 1024.0 / 1024.0 AS anon_rss_swap_mib,
  h.dmabuf_rss_size / 1024.0 / 1024.0 AS dmabuf_rss_mib,
  h.oom_score_adj
FROM android_heap_graph_stats AS h
JOIN process AS p USING (upid)
ORDER BY h.graph_sample_ts;
```

模块为 OOM adj、RSS/swap 与 DMA-BUF 查找覆盖 heap dump 时刻的区间；没有覆盖时，允许选择 dump 之后 `500 ms` 内最近的数据点。各字段可能为 `NULL`，也不构成同一时刻的原子快照。trace 没有 ART heap graph 时，表自然为空。[Android 17 heap graph stats](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/memory/heap_graph/heap_graph_stats.sql)

Java heap 稳定而 DMA-BUF RSS 上涨，只能把范围转向图形 buffer、解码、Surface 生命周期和跨进程持有；它还不能直接指出泄漏对象。Java heap 与 DMA-BUF 同时上涨时，也要分别验证对象可达路径和图形资源所有权。

## 怎样迁移 v54 表结构变化

v54.0 的变化应按表结构处理，不能靠字符串替换：

| v54.0 变化 | 迁移原则 |
|---|---|
| 删除 `slice.stack_id` / `slice.parent_stack_id` | 使用 `slices.stack` 标准库的栈关系函数 |
| 所有表的 `machine_id` 改为非空，host 为 `0` | 删除 `machine_id IS NULL` 假设；多机 trace 在有该列的表上显式限定机器 |
| `metadata` 增加 `trace_id` 与 `machine_id` | 只在 metadata 语义需要时使用；不能假设每张业务表都有 `trace_id` |
| 删除 `--add-sql-module` / `--override-sql-module` | 改用 `--add-sql-package` / `--override-sql-package` |

标准库、指标与核心表的兼容级别不同。以下划线开头的对象、指标中间表、Data Explorer 物化表都更容易变化。生产查询应固定 Trace Processor 版本，入口尽量使用公开表和公开模块，并在升级时运行空 trace 语法测试与代表性 trace 回归。

## Collapsed Stack 与 Firefox Profiler 导入

v54.0 增加了 Collapsed Stack 和 Firefox Profiler preprocessed JSON 导入：

- Collapsed Stack 保存“调用栈 + 聚合计数”，适合迁移 FlameGraph 资产；
- Firefox Profiler preprocessed JSON 主要保留已处理的采样信息。

这两类输入通常没有 Android system trace 的 FrameTimeline、Binder、调度、CUJ 标记和设备计数器。它们可以回答 CPU 样本集中在哪些栈，无法单独解释某个 Android 帧为何超时。要做逐帧归因，仍需重新采集带 FrameTimeline、sched、应用 atrace 与必要系统数据源的 Perfetto trace。

## 一轮可复核的分析顺序

1. 记录 Android 构建、Perfetto UI、Trace Processor、采集配置和负载条件。
2. 查询标记、计数器、FrameTimeline、sched 与相关线程是否存在，列出采集缺口。
3. 区分系统 InteractionJankMonitor CUJ 与第三方 App 自定义窗口。
4. 生成一行一个 CUJ 的窄表，用加权总量、丢帧数和最大帧时排序。
5. 展开异常帧，分别查看 App / SF 分类、回调漏采与 expected timeline 回退。
6. 对 UI、RenderThread、GPU/HWC 和 SurfaceFlinger 线程做时间交集，再接函数采样、GPU fence、Binder 或内存证据。
7. 在报告中分开写观测、推断、采集限制和经过对照实验确认的根因。

DataGrid 和 Data Explorer 负责提高浏览效率。提交审阅的结论应能由保存的 SQL 在相同 Trace Processor 上复现，并能回到 Android 17 或 v54.0 的明确源码位置解释字段含义。

## 参考源码

- [Perfetto v54.0 release](https://github.com/google/perfetto/releases/tag/v54.0)
- [Android 17 DataExplorer plugin](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/ui/src/plugins/dev.perfetto.DataExplorer/index.ts)
- [Android 17 DataExplorer query execution](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/ui/src/plugins/dev.perfetto.DataExplorer/query_builder/query_execution_service.ts)
- [Android 17 CUJ threads](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/cujs/threads.sql)
- [Android 17 CUJ frame counters](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/cujs/cuj_frame_counters.sql)
- [Android 17 Jank CUJ metric initialization](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/metrics/sql/android/jank/android_jank_cuj_init.sql)
- [Android 17 Jank CUJ frames](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/metrics/sql/android/jank/frames.sql)
- [Android 17 InteractionJankMonitor](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/jank/InteractionJankMonitor.java)
- [Android 17 Trace API](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)
