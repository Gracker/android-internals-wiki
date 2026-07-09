---


title: "Perfetto DataGrid 与 Jank CUJ 标准库"
chapter: "13.14"
section: "13.14"
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
    path: "https://raw.githubusercontent.com/google/perfetto/main/docs/data-sources/frametimeline.md"
  - type: research
    path: "intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md"
tags: [perfetto, datagrid, jank, cuj, sql, frametimeline]
related_chapters: ["7.3", "7.4", "13.3", "13.8", "13.10", "13.11", "13.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/官方文档"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-07-10"
task6_result: "pass-light-edit"
last_task6_at: "2026-07-10T04:12:20+08:00"
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-10"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-10T04:30:34+08:00"
task2b_result: fixed-lite
task2b_state: "fixed"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
last_task2b_lite_at: "2026-05-28"
last_task6_review_log: "logs/review/2026-07-10-04-review.md"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_review_notes: "2026-07-10 Task6 revisiting-review (round 5): pass-light-edit。Task9 auto-fix(ExplorePage summarizer API源码锚点)回流后写作层复审通过；L1 禁用词/高频词/物理动词/元叙述零命中（"对齐"3处均为技术语境data/vsync alignment，非黑话用法）；L2 开头/节奏/结构/读者引导全部通过；outline 6/6 锚点全覆盖；否定-纠正结构2处(限额内)；无 L1/L2 问题，无 L3/L4 回炉项。送 Task9 终审确认。"
last_task9_autofix_at: "2026-07-10"
last_task9_review_log: "logs/deep-review/2026-07-10-04-deep-review.md"
task9_review_notes: "2026-07-10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；复核 Perfetto v54 DataGrid/ExplorePage summarizer API、android.cujs.*、weighted jank counter 与 AOSP JankTracker/FrameTimeline 锚点；Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-07-10-04-deep-review.md。 | 2026-07-10 Task9 idle-audit AUTO-FIX: P0 1 / P1 0 / P2 0；修正 Perfetto v54.0 ExplorePage 执行模型源码锚点：`engine.analyzeStructuredQuery` / `NodePanel.updateQuery()` 不属于当前 v54.0 调用链，改为 summarizer API（`createSummarizer` / `updateSummarizerSpec` / `querySummarizer`）与 `SQLDataSource` 物化表展示路径；回到 Task6 复审。详见 logs/deep-review/2026-07-10-03-audit.md。 | 2026-06-19 Task9 deep-review: pass-tech-review。复核 Perfetto v54.0 android.cujs.base / cuj_frame_counters / internal counters / ExplorePage，以及 AOSP android-17.0.0_r1 ViewRootImpl / JankTracker / FrameTracker / stats atoms；无 P0/P1/P2。Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-06-19-12-deep-review.md。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 1 / P1 0 / P2 0；修正 statsd 侧不存在的 `frame_missed` atom 标识，改为 android-17.0.0_r1 `UI_INTERACTION_FRAME_INFO_REPORTED` atom 及 `missed_frames` / `app_missed_frames` / `sf_missed_frames` 字段；回到 Task6 复审。详见 logs/deep-review/2026-06-19-07-deep-review.md。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 2 / P1 0 / P2 0；修正 android-17.0.0_r1 ViewRootImpl traversal 回调源码锚点（TraversalCallback#onVsync）与 JankTracker JankType 判定表（补入 kMissedDeadline / kMissedDeadlineLegacy 边界）；回到 Task6 复审。详见 logs/deep-review/2026-06-19-06-deep-review.md。 | 2026-06-18 Task9 idle-audit auto-fix：修正 android-17.0.0_r1 ViewRootImpl 行号、JankTracker 方法名、JankInfo/Cuj 源码锚点、Perfetto v54 CUJ counter 进程过滤和 weighted jank metric 转换口径；回到 Task6 复审。 | 2026-05-28 Task9 auto-fix：修正 android.cujs.base 源码路径、FrameTimeline/JankStats 版本表和 FrameTimeline trace data source 配置口径；回到 Task6 复审。 | 2026-05-28 06 Task9 auto-fix: 修正 JankStats API 级别，收窄 Perfetto v54.0 weighted_missed_frames 字段版本边界，回到 Task6 复审。 | 2026-05-28 17 Task9 deep-review: pass-tech-review。复核 Perfetto v54.0 DataGrid、CUJ counter metrics、android.cujs.* 与 FrameTimeline/JankStats 版本边界，无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-19 Task9 deep-review AUTO-FIX: P0 0 / P1 1 / P2 0；Perfetto v55.0 DataExplorer 只保留为非 Android 17 范围边界，移除 v55 操作建议，正文结论收窄到 v54.0 / Android 17；回到 Task6 复审。详见 logs/deep-review/2026-06-19-05-deep-review.md。"
p0: 0
p1: 0
p2: 0
task9_reviewed_at: "2026-07-10T04:30:34+08:00"
last_task6_audit: "2026-07-02"
updated_by: "openclaw-task9"
updated_date: "2026-07-10"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-26
last_task9_audit: "2026-06-18"
---
# 13.14 Perfetto DataGrid 与 Jank CUJ 标准库

<!-- outline-start -->
## 要点

### 🔹 DataGrid 的适用场景
Perfetto v54 的官方发布说明写的是 DataGrid table viewer、pivot table 和筛选能力，不是独立的 Data Explorer 工作流。DataGrid 适合把 SQL 结果变成可筛选、可透视的表格，用来收窄异常帧、异常 CUJ 和异常线程。

### 🔹 从手写 SQL 到可视化分析管线
手写 SQL 仍然负责定义证据口径；DataGrid 负责交互式过滤、排序和分组；标准库负责把 FrameTimeline、CUJ、线程和 counter 这些高频分析对象封装成可复用入口。

### 🔹 Jank CUJ 标准库模块
v54 引入 relevant threads jank CUJ 相关能力，配合 `android.cujs.*` 标准库和 `android/android_jank_cuj.sql` metric，可以把一个交互场景里的主线程、RenderThread、GPU completion、HWC release、SurfaceFlinger 线程放到同一张分析表里。

### 🔹 counter-based weighted jank metrics
FrameTracker 在 CUJ 结束后会写出 total frames、missed frames、weighted jank 等 counter。Perfetto 的 jank CUJ pipeline 会把这些 counter 映射回对应 CUJ，避免只按掉帧数量判断卡顿严重程度。

### 🔹 与 FrameTimeline / thread_state 的联合分析
Jank CUJ 给出场景窗口，FrameTimeline 给出 app missed / SF missed 的帧级判定，`thread_state` 给出线程是在 Running、Runnable、Sleeping 还是 uninterruptible sleep。三者合在一起，才能判断是 App 执行超时、SF 合成超时、GPU/HWC 等待，还是线程调度问题。

### 🔹 v54 schema 变更与旧 SQL 迁移
v54 删除 `slice.stack_id` 和 `slice.parent_stack_id`，把相关能力迁移到 `slices.stack` 标准库；`machine_id` 变为非空；`metadata` 表加入 multi-trace / multi-machine 语义。旧 SQL 要按 schema 变更逐条迁移，不能只改字段名。

## 扩展

### 🔸 heap_graph_stats 与 dmabuf 分析入口
`android.memory.heap_graph.heap_graph_stats` 把 Java heap graph、NativeAllocationRegistry、RSS / swap、OOM score 和 DMA-BUF RSS 放到一张统计表里，适合用于 ch10 内存分析和图形内存问题。

### 🔸 Collapsed Stack / Firefox Profiler 格式导入
v54 Trace Processor 支持 Collapsed Stack 和 Firefox Profiler 预处理 JSON 导入。它适合迁移历史 profile 资产，但这类格式通常缺少 Android trace 的 FrameTimeline、Binder 和调度上下文。

## 系统 CUJ 与第三方 App 适用范围边界

### 关键发现

1. **`android_jank_cuj` 表默认只包含系统进程**
   - `android.cujs.base` 模块（`external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/cujs/base.sql`）中的 `android_jank_cuj` 表默认按进程名过滤
   - `com.android.*` / `com.google.android*` 进程数据进入 CUJ 分析，第三方 App 的 CUJ marker 不自动进入该表
   - 第三方 App 需要使用 AndroidX JankStats API 或自定义 SQL 扩展

2. **FrameTracker 与 CUJ 的数据流**
   ```text
   ViewRootImpl.scheduleTraversals()
     → Choreographer.postVsyncCallback(CALLBACK_TRAVERSAL, mTraversalCallback)
       → TraversalCallback#onVsync() → doTraversal()  (android-17.0.0_r1: L3330-L3331 / L11445-L11448 / L3347)
       → JankTracker::finishFrame(...)  // frameworks/base/libs/hwui/JankTracker.cpp
         → SurfaceFlinger FrameTimeline
           → Perfetto trace → android_jank_cuj 表
   ```
   - HWUI 在帧结束时通过 `JankTracker::finishFrame(...)` 记录帧耗时，legacy jank 判定比较各 `FrameInfo` 时间点与 frameInterval 阈值
   - CUJ marker 通过 `Choreographer#doFrame` slice 对齐 vsync ID

3. **CUJ SQL 模块的关键表**
   - `android_jank_cuj_vsync_boundary`：每个 CUJ 的 vsync 边界（通过 `_android_jank_cuj_do_frames` 关联）
   - `android_jank_cuj_main_thread_frame_boundary`：基于预期帧时间线的帧边界
   - `android_jank_cuj_boundary`：整体 CUJ 边界（app process 级别）

4. **第三方 App 扩展路径**
   - **AndroidX JankStats**（API 16+ 可用；API 24+ 计时数据更可靠，API 31+ 精度更高）：`androidx.performance:performance-jankstats` → `JankStats.createJankStats()`
   - **自定义 atrace marker**：使用 `Trace.beginSection()` 标记 CUJ，配合 Perfetto SQL 扩展 `_is_jank_slice`
   - **FrameTimeline direct join**：直接 join `actual_frame_timeline_slice` 和 `expected_frame_timeline_slice` 计算自定义帧耗时

### 源码锚点

| 文件 | 说明 |
|------|------|
| `frameworks/base/libs/hwui/JankTracker.cpp` | FrameTracker jank 跟踪器实现 |
| `frameworks/native/libs/gui/include/gui/JankInfo.h` | SurfaceFlinger `JankType` 枚举定义 |
| `frameworks/base/core/java/android/view/ViewRootImpl.java` (android-17.0.0_r1: L3330-L3331 / L11445-L11448 / L3347) | `scheduleTraversals()` 通过 `postVsyncCallback()` 进入 `TraversalCallback#onVsync()`，再调用 `doTraversal()` |
| `external/perfetto/src/trace_processor/metrics/sql/android/jank/cujs_boundaries.sql` | CUJ 边界计算核心逻辑 |
| `frameworks/base/core/java/com/android/internal/jank/Cuj.java` | AOSP CUJ ID / marker 定义 |

### 版本参考

| Android 版本 | CUJ 支持 |
|--------------|---------|
| Android 12 (API 31) | FrameTimeline trace 数据可用 |
| AndroidX JankStats 1.0.0 | API 16+ 可用；API 24+ 依赖 FrameMetrics，API 31+ 计时数据更准 |
| Android 13+ | InteractionJankMonitor 稳定化 |

### 第三方 App CUJ 分析的三条执行路径

`android.cujs.base` 默认仅覆盖系统进程。以下三条路径适用于第三方 App 做 CUJ 分析：

#### 路径一：AndroidX JankStats（API 16+ 可用，API 24/31 后计时更准）

```kotlin
val jankStats = JankStats.createAndTrack(window) { frameData ->
    // 回调里最少化操作：复制字段后立即返回
    val event = JankFrameEvent(
        page = "feed",
        durationNanos = frameData.frameDurationUiNanos,
        isJank = frameData.isJank,
        overrunNanos = frameData.frameOverrunNanos
    )
    backgroundHandler.post { aggregator.enqueue(event) }
}
// Activity 生命周期管理
jankStats.isTrackingEnabled = true   // onResume()
jankStats.isTrackingEnabled = false  // onPause() + flush
```
- `JankStats` 内部通过平台 FrameMetrics API（API 24+）获取帧数据
- 配合 `PerformanceMetricsState` 绑定 UI 状态（如列表滚动状态）
- 阈值默认按刷新率倍数判断，可通过 `jankHeuristicMultiplier` 调整
- **注意**：`OnFrameListener` 每帧触发，回调对象会复用，必须立即复制字段

#### 路径二：自定义 atrace marker

```kotlin
Trace.beginSection("J<my_custom_cuj>")
// ... user interaction ...
Trace.endSection()
```
- `Trace.beginSection()` 的 name 参数使用 `J<>` 前缀格式，可被 Perfetto SQL 筛选
- 第三方 App 的 CUJ 不进入 `android_jank_cuj` 表，需配合自定义 SQL 扩展
- 高频场景（滚动、动画）要注意标记密度，避免 atrace marker 本身成为开销

#### 路径三：FrameTimeline direct join

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  actual.slice_name,
  actual.ts,
  CAST((actual.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  CAST(actual.dur / 1e6 AS FLOAT) AS actual_ms,
  CAST(expected.dur / 1e6 AS FLOAT) AS expected_ms,
  actual.on_time_finish,
  actual.jank_type
FROM actual_frame_timeline_slice AS actual
JOIN expected_frame_timeline_slice AS expected
  ON actual.display_frame_token = expected.display_frame_token
WHERE actual.on_time_finish = 0
ORDER BY actual.ts
LIMIT 50;
```
- 不依赖 CUJ marker，直接用 `on_time_finish = 0` 判断异常帧
- 需要 trace 配置开启 `android.surfaceflinger.frametimeline`；若还要联动 `Choreographer#doFrame` / `DrawFrame` slice，再同时开启 `gfx` / `view` atrace category

#### FrameTracker 数据流（系统进程视角）

```text
ViewRootImpl.scheduleTraversals()
  → Choreographer.postVsyncCallback(CALLBACK_TRAVERSAL, mTraversalCallback)
    → TraversalCallback#onVsync() → doTraversal()  // frameworks/base/core/java/android/view/ViewRootImpl.java:3330-3331 / 11445-11448 / 3347
    → JankTracker::finishFrame(...)  // frameworks/base/libs/hwui/JankTracker.cpp
      → SurfaceFlinger FrameTimeline (BufferQueue feedback)
        → Perfetto trace → android_jank_cuj 表
```

| 文件 | 说明 |
|------|------|
| `frameworks/base/libs/hwui/JankTracker.cpp` | FrameTracker JankTracker 实现 |
| `frameworks/native/libs/gui/include/gui/JankInfo.h` | SurfaceFlinger `JankType` 枚举定义 |
| `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/cujs/base.sql` | `_is_jank_slice` 进程名过滤逻辑 |
| `android/performance-samples/JankStatsSample/` | JankStats 官方示例代码 |

**版本备注**：sched_ext 调度器可能影响 CUJ 帧时间判断（线程调度延迟 → 帧耗时），此方向有待进一步验证。

### android.cujs.base 进程名过滤两层结构与协作链

#### 进程名过滤是两层（不是一层）

**第一层 · `cujs/base.sql` `_is_jank_slice` 宏**：

```sql
$slice.name GLOB 'J<*>'
AND (
  $process.name GLOB 'com.google.android*' OR $process.name GLOB 'com.android.*'
);
```

**第二层 · `jank/internal/counters.sql` `cujs_ordered` CTE 决定 counter 起点**：

```sql
CASE
  WHEN process_name GLOB 'com.android.*' THEN ts_end
  WHEN process_name = 'com.google.android.apps.nexuslauncher' THEN ts_end
  -- Some processes publish counters just before logging the CUJ end
  ELSE MAX(ts, ts_end - 4000000)
END AS ts_earliest_allowed_counter
```

三层覆盖：
- `com.android.*` 系统服务：CUJ 进主表，counter 起点取 `ts_end`（0 回溯）
- `com.google.android.*` 进程：CUJ 进主表；除 `com.google.android.apps.nexuslauncher` 外，counter 起点走 `MAX(ts, ts_end - 4000000)` 回溯
- `com.google.android.apps.nexuslauncher`：Pixel Launcher 显式白名单，counter 起点取 `ts_end`
- 其他进程（如第三方 `com.example.*`）：CUJ **不进** 主表；即使命名为 `J<*>#*`，默认 counter 管线也不会消费，除非先用自定义 SQL 让该 `upid` 进入 CUJ 表

#### CUJ counter 命名规范（`cujs/cuj_frame_counters.sql`）

counter track 名必须满足 `GLOB 'J<*>#*'`，CUJ 名提取用 `str_split(str_split(track.name, '>#', 0), '<', 1)`，counter 名用 `str_split(track.name, '#', 1)`。但默认 `_android_jank_cuj_counter` 还会 `JOIN android_jank_cuj USING (upid)`；只有已进入 `android_jank_cuj` 的进程会被默认 counter 管线消费。第三方 App 需要先扩展 CUJ 入口，再按这套命名写 `process_counter_track`。

支持的 counter 名（从 `internal/counters.sql` 引用）：`totalFrames` / `missedFrames` / `missedAppFrames` / `missedSfFrames` / `maxSuccessiveMissedFrames` / `totalAnimTime` / `weightedAppJank` / `weightedSfJank` / `maxFrameTimeMillis`。

在 v54 SQL 中，`internal/counters.sql` 对 `weightedAppJank` / `weightedSfJank` 先除以 1000；最终 metric 在 `android/android_jank_cuj.sql` 再乘 `anim_duration_ms / 1000`，输出 total weighted missed frames。

#### Frame type 判定（`perfetto_sql/stdlib/android/frames/jank_type.sql`）

```sql
android_is_sf_jank_type(jank_type) :=
  GLOB '*SurfaceFlinger CPU Deadline Missed*'
  OR GLOB '*SurfaceFlinger GPU Deadline Missed*'
  OR GLOB '*SurfaceFlinger Scheduling*'
  OR GLOB '*Prediction Error*'
  OR GLOB '*Display HAL*'

android_is_app_jank_type(jank_type) :=
  GLOB '*App Deadline Missed*'
  OR GLOB '*App Resynced Jitter*'
```

`jank_type` 原始值来自 `frame_timeline_event.args.display_value['Jank type']`，由 SurfaceFlinger 写 frame timeline 时填入。

#### JankTracker.cpp 与 CUJ 的关系

`frameworks/base/libs/hwui/JankTracker.cpp` 在 native 层先按 `GpuCompleted >= FrameDeadline` 记录 `kMissedDeadline`，再对 deadline miss 的帧按四个阶段补充拆分；triple-buffered 状态下即使命中 deadline，也可能记录 `kHighInputLatency`。legacy 路径还会单独记录 `kMissedDeadlineLegacy`。

| JankType | 阈值/触发条件 | 时序范围 |
|----------|------|----------|
| `kMissedDeadline` | `GpuCompleted >= FrameDeadline` | IntendedVsync → GpuCompleted / FrameDeadline |
| `kMissedVsync` | 1 ns | IntendedVsync → Vsync |
| `kSlowUI` | 0.5× frameInterval | Vsync → SyncStart |
| `kSlowSync` | 0.2× frameInterval | SyncStart → IssueDrawCommandsStart |
| `kSlowRT` | 0.75× frameInterval | IssueDrawCommandsStart → FrameCompleted |
| `kHighInputLatency` | `mNextFrameStartUnstuffed - IntendedVsync > 0.1× frameInterval` | triple-buffered 状态命中 deadline |

报告链路：`JankTracker::finishFrame` → `ProfileDataContainer` + `FrameMetricsReporter::reportFrameMetrics` → 第三方 App 通过 `Window.OnFrameMetricsAvailableListener` 接收（也是 AndroidX JankStats 内部数据源）。

**JankTracker 与 CUJ 标准库独立运行**：JankTracker 的 legacy jank 计数不会自动映射到 CUJ metric 的 `missedFrames`；CUJ 事后聚合依赖 `J<CUJ_NAME>` slice、`J<CUJ_NAME>#*` counter track 和 FrameTimeline 数据。需要把两层数据对齐时，应核对 statsd 的 `UI_INTERACTION_FRAME_INFO_REPORTED` atom 字段（`missed_frames` / `app_missed_frames` / `sf_missed_frames`）和 trace counter。

#### `relevant_threads.sql` 迁移策略

旧表 `android_jank_cuj_sf_main_thread` / `android_jank_cuj_sf_thread(...)` 是对内部 `_android_sf_*` 的薄包装，保留向后兼容。**注释明确写「TODO(devianb): Removed once we migrate google3 pipelines away」**——第三方生产脚本不应长期依赖旧名，应直接用 `_android_sf_process` / `_android_sf_thread(thread_name)`。

#### 调用链总图

```
Choreographer traversal callback vsync=N
  → ViewRootImpl.doTraversals
     → HWUI rendering
        → RenderThread DrawFrames vsync=N
           → GPU completion fence_N
  ← JankTracker::finishFrame  (libs/hwui/JankTracker.cpp)
     ├─ calculateLegacyJank → ProfileDataContainer
     └─ reporter->reportFrameMetrics  → FrameMetricsReporter
                                        → 第三方 App OnFrameMetricsAvailableListener
Trace.beginSection("J<my_cuj>") ... Trace.endSection()
  → atrace process counter track: J<my_cuj>#totalFrames
                                ↓
                Perfetto trace_processor
                                ↓
_is_jank_slice!(slice, process)  ← cujs/base.sql 进程名过滤
                                ↓
_jank_cujs_slices / _cuj_state_markers / _cuj_instant_events
                                ↓
android_jank_cuj_main_thread / render_thread / gpu_completion_thread  (relevant_threads.sql)
                                ↓
android_jank_cuj_vsync_boundary / _main_thread_frame_boundary  (cujs_boundaries.sql)
                                ↓
android_jank_cuj_frame_timeline  (frames.sql + frames/jank_type.sql)
android_jank_cuj_frame  (do_frame + draw_frame + gpu_fence join)
                                ↓
android_jank_cuj_counter_metrics  (internal/counters.sql)
   ts_earliest_allowed_counter: com.android.*=ts_end / NexusLauncher=ts_end / else=ts_end-4ms
                                ↓
AndroidJankCujMetric proto  (android/android_jank_cuj.sql)
   counter_metrics / trace_metrics / timeline_metrics / frame / sf_frame
```

<!-- outline-end -->

Perfetto v54 让 Android 性能分析里的三类证据开始使用同一套工作流：UI 里的 DataGrid / pivot table 让 SQL 结果可以交互式探索，Jank CUJ 相关模块把交互场景变成结构化对象，weighted jank counter 让“掉了几帧”继续追到“这次卡顿有多重”。

这类能力最适合处理一种常见问题：一段滑动、展开、返回或者 Launcher 动画看上去只是“偶尔卡一下”，单看 FrameTimeline 能定位异常帧，但还不能判断异常来自 App、SurfaceFlinger、GPU completion、HWC release，还是调度等待。CUJ 把这段交互切成窗口，DataGrid 把结果筛出来，SQL 把判断口径固定下来。

## DataGrid 适合做什么

Perfetto v54 release notes 在 UI 部分写到的是 DataGrid table viewer 的改进：pivot table、glob / contains / not-contains filters、distinct value picker，以及 snap-to-boundaries。DataGrid 是 SQL 结果表的交互层；分析口径仍由 SQL 和标准库决定。**节点式数据流（node-based query builder）在 v54.0 已存在**，Android 17 范围内只按 `dev.perfetto.ExplorePage` 和基础节点能力讨论；后续版本的重命名与扩展节点不进入本节结论。详见本节末「节点式数据流补注」。

DataGrid 的价值在三类场景里最明显：

- 异常帧筛选：把 SQL 查出的帧结果按 `app_missed`、`sf_missed`、`jank_score`、`dur_ms` 排序，先找最重的一批帧。
- CUJ 聚合：按 `cuj_name`、进程名、状态和 weighted jank 做透视，判断问题集中在哪个交互场景。
- 线程证据核对：把 UI 线程、RenderThread、SurfaceFlinger main / RenderEngine、GPU completion 和 HWC release 的 slice 结果放在一起，检查同一 CUJ 里谁先超预算。

这种工作流不替代手写 SQL。SQL 决定表里有哪些列、每列怎么计算、跨表 join 的时间窗怎么取；DataGrid 只负责把结果变成可观察的表格。团队里多人复盘同一类卡顿时，应该把 SQL 留在文档或仓库里，把 DataGrid 当成交互式验证入口。

## 从手写 SQL 到可视化分析管线

PerfettoSQL 的稳定工作方式是先写出一个“窄表”：每一行对应一个可解释对象，例如一个 CUJ、一个 frame、一个 slice 或一个线程状态区间；每一列对应一个判断维度，例如是否 app missed、是否 SF missed、帧耗时、线程状态、blocked function、counter 值。窄表进入 DataGrid 后，排序、过滤、分组才有意义。

下面这段查询用于把 Jank CUJ metric 初始化，并列出 counter 口径下 App / SF weighted jank 最重的 CUJ。重点看 `weighted_missed_app_frames_total`、`weighted_missed_sf_frames_total`、`missed_app_frames` 和 `missed_sf_frames` 四组字段：

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
  weighted_missed_app_frames * anim_duration_ms / 1000 AS weighted_missed_app_frames_total,
  weighted_missed_sf_frames * anim_duration_ms / 1000 AS weighted_missed_sf_frames_total,
  frame_dur_max / 1e6 AS frame_dur_max_ms
FROM android_jank_cuj_counter_metrics
ORDER BY
  COALESCE(weighted_missed_app_frames_total, 0) +
  COALESCE(weighted_missed_sf_frames_total, 0) DESC
LIMIT 20;
```

这张表适合作为 DataGrid 的入口。`missed_frames` 回答“掉了多少帧”，`weighted_missed_app_frames_total` 和 `weighted_missed_sf_frames_total` 回答 counter 口径下 App / SF 两侧各自多重，`missed_app_frames` 和 `missed_sf_frames` 则把责任先粗分到 App 侧和 SurfaceFlinger 侧。后续再展开单帧和线程状态，不要在这一步直接下根因结论。

## Jank CUJ 标准库模块怎样组织线程

CUJ 分析的难点在于把同一段交互里的相关线程找齐。Perfetto 的 jank CUJ 初始化脚本会创建主线程、RenderThread、GPU completion、HWC release、SurfaceFlinger main、SurfaceFlinger GPU completion、RenderEngine 等表。`android.cujs.threads` 标准库里也提供了 `android_jank_cuj_app_thread(thread_name)` 这类入口，用线程名把 CUJ 和进程内线程关联起来。

下面这段查询用于检查每个 CUJ 是否能匹配到 RenderThread。读者只需要看 `cuj_id`、`cuj_name`、`utid` 和 `track_id`，后续追 slice 时会用到这些 ID：

```sql
INCLUDE PERFETTO MODULE android.cujs.base;
INCLUDE PERFETTO MODULE android.cujs.threads;

SELECT
  c.cuj_id,
  c.cuj_name,
  c.process_name,
  r.utid AS render_thread_utid,
  r.track_id AS render_thread_track_id
FROM android_jank_cuj AS c
LEFT JOIN android_jank_cuj_render_thread AS r USING (cuj_id)
ORDER BY c.ts;
```

`LEFT JOIN` 保留下没有 RenderThread 的 CUJ，避免把“采集缺口”误判成“线程没有参与”。如果某类 CUJ 总是缺 RenderThread，需要回到 trace config 和 App 场景确认：可能是场景本身不走 HWUI，也可能是 trace 缺少相关 track。

## weighted jank counter 解决什么问题

只看 dropped / missed frame 数量会漏掉严重程度。一个 CUJ 掉 3 帧，可能是 3 个轻微超时，也可能包含一次连续多帧延迟。v54 release notes 提到 counter-based weighted jank metrics；Perfetto v54.0 源码里的 `android_jank_cuj_counter_metrics` 会读取 FrameTracker 在 CUJ 结束后写出的 `weightedAppJank`、`weightedSfJank` counter，并除以 1000 转成每秒 jank 口径的浮点值。若要和最终 metric 的 counter metrics 对齐，还要乘以 `anim_duration_ms / 1000` 转成 App / SF 各自的 total weighted missed frames。`weightedJank` / `weighted_missed_frames` 总量字段出现在 main 分支后续版本，不能写成 v54.0 SQL 的固定字段。

这类 counter 有两个使用边界：

- 它依赖 CUJ 结束后的 counter 写入，短时间内同名 CUJ 连续出现时，脚本会用下一个同名 CUJ 的结束时间限制 counter 匹配范围。
- 它适合给排序和告警做权重，不适合单独解释根因。根因仍要回到 FrameTimeline、slice 和 `thread_state`。

Perfetto 的 metric 输出里同时保留 counter metrics、trace metrics 和 timeline metrics。counter metrics 来自 FrameTracker 的汇总，trace / timeline metrics 来自 trace 中逐帧数据。两者不一致时，先检查 trace 是否缺 frame 数据、CUJ marker 是否完整、采集窗口是否截断。

## 与 FrameTimeline 和 thread_state 联合分析

FrameTimeline 从 Android 12 开始提供 expected / actual timeline。App actual timeline 的结束时间取 `max(gpu time, post time)`，SurfaceFlinger actual timeline 覆盖 main thread 到屏幕更新的路径。Perfetto 文档把 jank 分成 AppDeadlineMissed、BufferStuffing、SurfaceFlingerCpuDeadlineMissed、SurfaceFlingerGpuDeadlineMissed、DisplayHAL、PredictionError 等类型。CUJ 级别分析应该顺着这些分类找证据。

下面这段查询从 Jank CUJ metric 生成的帧表里抽出异常帧。重点看 `app_missed`、`sf_missed` 和 `jank_score`：

```sql
SELECT RUN_METRIC('android/android_jank_cuj.sql');

SELECT
  cuj_id,
  frame_number,
  vsync,
  dur / 1e6 AS dur_ms,
  dur_expected / 1e6 AS expected_ms,
  app_missed,
  sf_missed,
  jank_score,
  sf_callback_missed,
  hwui_callback_missed
FROM android_jank_cuj_frame
WHERE app_missed OR sf_missed
ORDER BY jank_score DESC, dur DESC
LIMIT 50;
```

这张表只给出“哪一帧异常”。下一步要回到异常帧对应的时间窗，查看 UI 线程和 RenderThread 的 `thread_state`：Running 时间长说明 CPU 执行占满预算；Runnable 时间长说明线程想跑但没拿到 CPU；uninterruptible sleep 且 `io_wait = 1` 更像 I/O 或内核等待；blocked function 非空时要继续查锁、futex 或 Binder 等待。

## v54 schema 变更与旧 SQL 迁移

v54 的 Trace Processor 有几处会直接影响旧 SQL：

| 变化 | 旧写法风险 | 迁移方向 |
|---|---|---|
| `slice.stack_id` / `slice.parent_stack_id` 被删除 | 旧 SQL 直接查字段会失败 | 使用 `slices.stack` 标准库里的 stack 关系函数 |
| `machine_id` 变为非空 | 用 `NULL` 表示 host machine 的判断会失效 | host machine 按 0 处理，多机器 trace 显式过滤 `machine_id` |
| `metadata` 支持 `trace_id` / `machine_id` | 旧 SQL 默认单 trace，合并 trace 时会混数据 | join 时带上 `trace_id` 和 `machine_id` |
| `--add-sql-module` / `--override-sql-module` 移除 | 旧脚本启动 Trace Processor 会失败 | 改用 `--add-sql-package` / `--override-sql-package` |

迁移旧 SQL 时，先把查询拆成三层：原始表读取、标准库派生表、业务筛选条件。字段改名或移除只应该影响前两层，业务筛选条件不要和 schema 细节混在一段 SQL 里。这样同一套卡顿规则从 v53 迁到 v54 时，只需要替换入口表或标准库模块。

## heap_graph_stats 与 dmabuf 分析入口

v54 还新增了 `heap_graph_stats` 模块，并加入 DMA-BUF 支持。源码里 `android_heap_graph_stats` 每行对应一次 ART heap graph sample，字段包括 Java heap 总大小、reachable heap、NativeAllocationRegistry、对象数量、OOM score、anon RSS + swap，以及 `dmabuf_rss_size`。

下面这段查询用于把 Java heap 和图形内存放到同一张表里。重点看 `reachable_heap_mb` 和 `dmabuf_rss_mb` 是否同时上涨：

```sql
INCLUDE PERFETTO MODULE android.memory.heap_graph.heap_graph_stats;

SELECT
  process.name AS process_name,
  graph_sample_ts,
  reachable_heap_size / 1024.0 / 1024.0 AS reachable_heap_mb,
  reachable_native_alloc_registry_size / 1024.0 / 1024.0 AS native_registry_mb,
  anon_rss_and_swap_size / 1024.0 / 1024.0 AS anon_rss_swap_mb,
  dmabuf_rss_size / 1024.0 / 1024.0 AS dmabuf_rss_mb,
  oom_score_adj
FROM android_heap_graph_stats
JOIN process USING (upid)
ORDER BY graph_sample_ts;
```

这类数据适合接到图片、视频、Camera、SurfaceView 或 Compose 大图场景。Java heap 没涨但 `dmabuf_rss_size` 涨，排查方向应转向图形 buffer、解码缓存、Surface 生命周期和跨进程持有；Java heap 与 DMA-BUF 同时涨，才考虑对象持有和图形资源释放两个方向一起查。

## Collapsed Stack / Firefox Profiler 格式导入

v54 Trace Processor 支持 Collapsed Stack 格式和 Firefox Profiler 预处理 JSON。Collapsed Stack 是 `main;foo;bar 100` 这类火焰图输入，适合把 Brendan Gregg FlameGraph 生态里的历史数据导入 Perfetto；Firefox Profiler JSON 适合跨工具查看已有 profile。

这两类格式的使用边界要写清：它们能保留调用栈聚合信息，但通常没有 Android system trace 里的 FrameTimeline、Binder、调度、counter 和 CUJ marker。用它们做 CPU 热点归因可以，用它们解释“某一帧为什么掉了”证据不够。遇到具体卡顿，仍要重新采带 FrameTimeline、sched、freq、binder、gfx / view 相关 atrace category 的 Perfetto trace。

## 排障顺序

一条可复用的 Jank CUJ 分析顺序如下：

1. 用 `android/android_jank_cuj.sql` 生成 CUJ metric，按 App / SF weighted total 或 `missed_frames` 找最重的 CUJ。
2. 在 DataGrid 里按 `cuj_name`、进程、`missed_app_frames`、`missed_sf_frames` 分组，确认问题集中在哪类场景。
3. 展开 `android_jank_cuj_frame`，找 `jank_score` 最高的帧。
4. 回到该帧时间窗，看 UI 线程、RenderThread、GPU completion、HWC release、SurfaceFlinger main / RenderEngine 的 slice。
5. 用 `thread_state` 判断线程是在执行、抢 CPU、睡眠、I/O 等待还是阻塞。
6. 如果怀疑内存或图形 buffer，把同一时间窗接到 `android_heap_graph_stats`、RSS、DMA-BUF 和 OOM score。

这套顺序的约束是：CUJ 用来定场景，FrameTimeline 用来定帧，线程状态用来定等待类型，profile / heap graph 用来补调用栈和内存证据。任何一步缺采集数据，都应该标注采集缺口，不能用相邻证据替代。

## 节点式数据流补注：ExplorePage（节点图编辑器）

> Perfetto v54.0 已提供基础节点图编辑器，plugin id 是 `dev.perfetto.ExplorePage`。后续版本的重命名和扩展节点未进入 Android 17，本节不把它们作为正文结论或操作建议。

### 1. Android 17 范围内的源码锚点

| Perfetto 版本 | Android 出厂基线 | 节点式工具 | 源码根目录 | 关键能力 |
|---|---|---|---|---|
| v54.0 | Android 17 / API 37 | `dev.perfetto.ExplorePage` | `ui/src/plugins/dev.perfetto.ExplorePage/` | 基础节点图、Undo/Redo、Recent Graphs、server-side 分页/过滤/排序 |

v54.0 已有 `index.ts`、`explore_page.ts`、`query_builder/`、`node_registry.ts` 和 `core_nodes.ts`。可用节点覆盖 `slice`、`table`、`sql`、`timerange`、`add_columns`、`modify_columns`、`aggregation`、`filter_node`、`filter_during`、`filter_in`、`interval_intersect`、`join`、`union_node`、`create_slices`、`sort_node`、`limit_and_offset_node`、`metrics`、`counter_to_intervals`、`visualisation`。这些足够支撑 CUJ / 卡顿 trace 的探索式筛选。

### 2. 两阶段执行模型

`QueryExecutionService`（`query_builder/query_execution_service.ts`）负责把节点图同步给 Trace Processor summarizer，并在需要时触发物化查询：

- **自动执行路径**：`NodeExplorer.updateQuery()` → `service.processNode({ manual: false })` → `createSummarizer()` / `updateSummarizerSpec()` 同步 `PerfettoSqlStructuredQuery` 图，再通过 `querySummarizer()` 取回 `sql`、`textproto`、`standaloneSql`、物化表名、行数和列信息。
- **DataGrid 展示路径**：`Builder` 使用 Trace Processor 返回的物化表名创建 `SQLDataSource`，由 DataGrid 做 server-side 分页、过滤和排序；调试时应以返回的 `tableName` 为准，不把物化表命名规则当稳定接口。

这个模型说明节点图编辑器不是新的分析口径，而是把 PerfettoSQL 查询拆成可视化节点、结构化查询和可检查的中间表。技术结论仍应落回 SQL、标准库和 trace 数据。

### 3. 与 DataGrid / 手写 SQL 的关系

`dev.perfetto.ExplorePage` 不是 DataGrid 的替代品，而是把「写 PerfettoSQL 文本 + 单次 query」拆成「节点连边 + 自动生成 SQL + 物化中间结果」：

| 维度 | 手写 SQL | DataGrid | ExplorePage 节点图 |
|---|---|---|---|
| 适用对象 | 熟悉 PerfettoSQL 的工程师 | 任意人 | 任意人 |
| 中间结果可见性 | 一次 query 一个结果 | 一个 SQL 一个 DataGrid | 节点图每个节点一个物化表 |
| 可视化程度 | 纯文本 | 表格 + pivot | 节点图 + 表格 |
| 跨会话复用 | 保存 SQL 文件 | 保存 permalink | 保存 permalink + 节点图 JSON |

**结论**：Android 17 / Perfetto v54.0 范围内，不能说「v54 完全没有节点式数据流」。准确说法是：v54.0 已有基础 ExplorePage 节点图编辑器；后续版本的命名和扩展节点不进入本节结论。

---

## 参考资料

### Perfetto DataGrid 与 Jank CUJ 标准库第三方 App 适用性验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-22-perfetto-cujs-third-party-app-scope.md
- 类型：DeepResearch 调研结果
- 摘要：从 Perfetto google/perfetto cujs.sql 源码验证 android.cujs.base 默认仅覆盖 com.android.*/com.google.android.* 进程，第三方 App 的 CUJ 不自动进入 android_jank_cuj 表。梳理三条第三方可执行路径：AndroidX JankStats（推荐）、自定义 atrace marker（J<> 格式）、FrameTimeline direct join，含完整 FrameTracker 数据流和 JankStats vs FrameTracker 分工对比。

### Perfetto DataGrid 与 Jank CUJ 标准库 v54 · 进程过滤与 FrameTracker Join 深挖
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-15-perfetto-jank-cuj-v54-process-filter-and-frametracker-join.md
- 类型：DeepResearch 调研结果
- 摘要：对 Perfetto v54 Jank CUJ 标准库的二次深挖：确认 `android.cujs.base` 进程名过滤分两层（GLOB com.google.android*/com.android.*），第二层 `cujs_ordered` CTE 按进程名决定 counter 回溯窗口（系统进程 0 回溯、NexusLauncher 白名单、其他进程 MAX(ts, ts_end-4ms)）；`android_jank_cuj_frame` vs `android_jank_cuj_frame_timeline` 的分工（frame 用于拼完整帧范围，timeline 用于 jank_type 分类）；JankTracker.cpp deadline miss 主判定、阶段拆分 JankType 与 CUJ 标准库事后聚合的关系；`relevant_threads.sql` 的 SF 线程视图迁移策略（旧表有后续删除计划）。
