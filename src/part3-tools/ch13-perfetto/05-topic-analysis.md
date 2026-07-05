---
title: 专题解读
chapter: '13.5'
section: '13.5'
status: finalized
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-03'
last_verified_against: perfetto.dev stdlib/docs, AOSP android-17.0.0_r1, 高爷博客原创
confidence: medium
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
  path: https://perfetto.dev/docs/analysis/sql-tables#frame-timeline-tables
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://perfetto.dev/docs/data-sources/java-heap-profiler
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

当一个 Trace 里同时铺开 `system_server`、`zygote64`、App 主线程和 `RenderThread` 时，打开 Perfetto 只是第一步；真正的难点在于知道先看哪里、什么算异常、下一步该追哪条线索。

本节把日常最常见的五类分析场景——启动、流畅性、Binder、内存、I/O——整理成独立专题工作流。每个专题都按“问题现象 → 抓取配置 → Trace 中的定位步骤 → 关键判读方法”的顺序展开，拿到问题后可以直接照着走一遍。

## 13.5.1 启动分析专题：从 Trace 中定位冷启动各阶段耗时

### 为什么要单独讲启动分析

冷启动是 Android 性能优化里最复杂的分析场景之一。它横跨多个进程，涉及大量 Binder 调用，还会叠加 Zygote fork、类加载和首帧渲染。

Trace 里通常会同时铺开 `system_server`、`zygote64`、App 主线程和 `RenderThread` 在几百毫秒内的密集协作。没有一套清晰的分析顺序，很容易在信息洪流里迷路。

在开始之前，建议先回顾 §1.2 系统启动全流程和 §8.1 响应速度原则，了解冷启动各阶段在系统层面的含义。以下内容侧重用 Perfetto 把这些阶段拆开，逐一测量耗时。

### 抓取配置

冷启动分析需要覆盖的维度比较广，建议使用以下配置：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 30000

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_set_priority"
      ftrace_events: "block/block_rq_issue"
      ftrace_events: "block/block_rq_complete"
      ftrace_events: "oom/oom_score_adj_update"
      ftrace_events: "task/task_rename"
      ftrace_events: "task/task_newtask"
      atrace_categories: "am"
      atrace_categories: "view"
      atrace_categories: "dalvik"
      atrace_categories: "input"
      atrace_categories: "wm"
      atrace_apps: "<你的目标App包名>"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

抓取时的操作流程是：先启动 Perfetto 录制，然后在桌面上点击目标 App 的图标（或使用 `adb shell am start` 触发冷启动），等 App 首帧完全渲染后停止录制。

### 在 Trace 中定位各阶段

[图：冷启动全流程在 Perfetto 中的表现，标注 fork → bindApplication → Activity.onCreate → 首帧渲染的关键节点]

冷启动的完整流程在 Trace 中大致呈现这样的时序：

**第一阶段：Zygote fork**

当 `system_server` 的 `ActivityManagerService` 决定启动一个新进程时，会向 Zygote 发送 socket 请求。Zygote 进程收到请求后执行 fork，产生新的 App 进程。在 Trace 中的定位方式如下：

- 在 `system_server` 进程中搜索 `ActivityManagerService` 相关的 Slice，找到 `startProcess` 或 `handleProcessStartedLocked` 调用
- 在 Zygote 进程（64 位设备上是 `zygote64`）中搜索 `Zygote` 相关的 Slice
- 新进程出现的时间点可以通过 Process Stats 区域的进程创建事件来确认

`task/task_newtask` 和 `task/task_rename` 这两个 ftrace 事件可以精确确认进程创建的时间点。当新进程被创建时，内核会产生 `task_newtask` 事件；当进程从 `zygote64` 改名为目标 App 的包名时，会产生 `task_rename` 事件。

**第二阶段：Application 初始化与 ContentProvider**

fork 完成后，新进程进入 `ActivityThread.main()`，开始执行 `Application.onCreate()` 之前的一系列初始化操作，包括创建 `Context`、加载 APK 资源、实例化并调用所有 `ContentProvider` 的 `onCreate`。在 Trace 中：

- 展开 App 进程的主线程轨道，找到 `bindApplication` Slice
- `bindApplication` 内部包含了 `ActivityThread.handleBindApplication` 的完整执行过程
- 如果 App 声明了多个 `ContentProvider`，它们的 `onCreate` 会按安装顺序依次调用，每个都会作为一个子 Slice 出现在 Trace 中

在实际分析中，我们经常发现某些 App 的冷启动慢是因为 `ContentProvider` 的初始化过于耗时——特别是使用了某些第三方 SDK（如 Firebase、LeakCanary）的自动初始化机制。这些 SDK 利用 `ContentProvider` 作为无需代码侵入的初始化入口，但代价就是拖慢了所有使用该 SDK 的 App 的启动速度。

**第三阶段：Activity 生命周期**

`Application` 初始化完成后，`system_server` 通过 Binder 通知 App 进程创建并启动目标 `Activity`。在 Trace 中：

- 在主线程轨道中找到 `activityStart`、`activityResume` 等 Slice
- `Activity.onCreate()` 内部的操作会作为子 Slice 出现
- 重点关注 `setContentView`（布局 inflate）、`findViewById`（如果布局很深的话）、以及 `onCreate` 中的任何同步 I/O 或 Binder 调用

**第四阶段：首帧测量与渲染**

`Activity` 的生命周期走完后，接下来就是第一帧的渲染。具体来说，`Activity.onResume()` 之后，系统会通过 `Choreographer` 安排第一个 `Traversal`（即 `performTraversals`），执行 `measure` → `layout` → `draw`。在 Trace 中：

- 主线程轨道中找到 `Choreographer#doFrame` Slice
- 其内部依次出现 `performTraversals`、`measure`、`layout`、`draw`
- `draw` 完成后，数据会交给 `RenderThread` 进行 GPU 渲染
- 最终通过 `BlastBufferQueue` 提交给 `SurfaceFlinger`，在下一个 `VSYNC-sf` 时完成合成并上屏

### 关键耗时判读技巧

分析启动 Trace 时，一个高效的切入点是看主线程的 **CPU 状态占比**。在 Perfetto 中选中主线程从进程创建到首帧完成的时间范围，底部信息区会显示这段时间内 `Running`、`Runnable`、`Sleep`、`D`（Uninterruptible Sleep）的占比。

这个占比能直接看出瓶颈所在：

- **Running 占比高但整体很慢**：主线程在做太多事情（通常是 `onCreate` 里塞了太多逻辑），需要拆分或延迟初始化
- **Runnable 占比高**：主线程已就绪但 CPU 被其他线程抢占，需要看 CPU 摆核和调度情况（参见 §5.1）
- **Sleep 占比高**：主线程在等锁或等 Binder 返回，需要进一步查看 Binder 事务和锁竞争
- **D 状态占比高**：主线程在做磁盘 I/O，通常是读取布局文件、DEX、资源文件等

[图：冷启动主线程 CPU 状态面板。时间范围从进程创建到首帧上屏，右侧标出 Running / Runnable / S / D 占比，下方同步显示主线程、RenderThread、关键 Binder 线程的时间窗。]

另一个常用技巧是 Perfetto 的 **Critical Path** 功能。选中主线程的某个长耗时 Slice，在底部信息区点击 "Critical path"，Perfetto 会自动高亮与这个 Slice 有依赖关系的所有 Task，快速追溯"到底是谁拖了后腿"。这个功能在启动分析中尤其好用，因为冷启动的流程很长，手动追踪唤醒关系非常耗时。

### Perfetto SQL 辅助分析

对于需要量化分析的场景，Perfetto SQL 可以快速统计关键阶段耗时。以下是一个查询冷启动各阶段耗时的示例：

```sql
-- 查询冷启动各关键阶段的耗时
SELECT
  slice.name,
  (slice.dur / 1e6) AS duration_ms,
  track.name AS track_name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = '<你的App包名>'
  AND thread.name = '<你的App包名>'  -- 主线程通常与进程同名
  AND slice.name IN (
    'bindApplication',
    'activityStart',
    'activityResume',
    'Choreographer#doFrame',
    'performTraversals'
  )
ORDER BY slice.ts;
```

## 13.5.2 流畅性分析专题：FrameTimeline 分析与 Jank 帧定位

### 流畅性分析的核心思路

流畅性问题（卡顿、掉帧）的本质，是某一帧没能在当前刷新周期内完成。120Hz 设备的预算大约是 8.33ms，60Hz 设备大约是 16.67ms。分析时要先找出哪一帧超时，再拆出超时发生在 App、RenderThread 还是 SurfaceFlinger。

FrameTimeline 是 Android 12-17 的主入口，Android 10/11 还得回到 `Choreographer#doFrame`、`thread_state`、`VSYNC-app` 和 `SurfaceFlinger` 轨道做 fallback。先把后面会反复用到的数据源和判读入口摆清楚，章节里的口径才不会混在一起。

### 版本、数据源与判读入口对照表

| 场景 | 公开采集入口 | UI / SQL 主入口 | 适用版本 | 说明 |
| --- | --- | --- | --- | --- |
| 流畅性（FrameTimeline） | FrameTimeline | `Expected Timeline`、`Actual Timeline`、`actual_frame_timeline_slice` | Android 12-13 | `jank_type`、`present_type`、`on_time_finish` 都来自 `actual_frame_timeline_slice` |
| 流畅性（FrameTimeline） | FrameTimeline | `Expected Timeline`、`Actual Timeline`、`actual_frame_timeline_slice` | Android 14-17 | 主入口不变，还是先看 `jank_type`、`present_type`、`on_time_finish`，再回到 App / RenderThread / SurfaceFlinger 时间窗 |
| 流畅性 fallback | `Choreographer` / `SurfaceFlinger` / `thread_state` | `Choreographer#doFrame`、`VSYNC-app`、`VSYNC-sf`、主线程与 `RenderThread` 线程态 | Android 10-11 | 没有 `actual_frame_timeline_slice` 时，用这组入口复盘卡顿 |
| Binder | `linux.ftrace` 的 Binder 与 `sched` 事件，加 `atrace_categories` / `atrace_apps` 保留 framework 与 App slice | Flow 箭头、Binder slice、`android_binder_txns` | Android 10-17 | `aidl_name` / `interface` / `method_name` 只有在 trace 里已有 AIDL / HIDL slice 时才会填充 |
| 锁竞争 | trace 中已有 `monitor contention` slice | `android_monitor_contention` | 以 trace 是否含该 slice 为准 | 它和 `android.java_hprof` 是两套独立入口 |
| Native heap | `android.heapprofd` | Heap Profile diamond、flamegraph、`heap_profile_allocation` | Android 10-17 | 看 native alloc / free 的调用栈 |
| Java allocation sampling | `android.heapprofd` + `heaps: "com.android.art"` | Heap Profile diamond、allocation flamegraph | Android 12-17 | 看 Java 对象分配调用栈，不给 retained graph |
| Java retained heap | `android.java_hprof` | Heap dump diamond、retention graph | Android 11-17 | 看对象保留关系，不给 call-site flamegraph |
| Block I/O | `linux.ftrace` 的 block / ext4 / f2fs / sched 事件 | `track.type='block_io'`、`linux.block_io` | Android 10-17，受内核事件可用性影响 | 设备级视角，进程归因还要再结合 `thread_state` 和文件系统事件 |

### 关键轨道解读

[图：Perfetto 中同一段滚动 Trace 的 `Expected Timeline`、`Actual Timeline`、`Choreographer#doFrame` 与主线程 `thread_state`。标出一帧 `jank_type`、`present_type`、`on_time_finish` 的查看位置。]

**Expected Timeline 与 Actual Timeline**

在 Android 12-17 的 App 进程轨道里，`Expected Timeline` 给的是系统希望这一帧在哪个窗口内完成，`Actual Timeline` 给的是这帧最终的实际完成情况。把两行放在同一时间轴下比较，超时帧会很快冒出来。

选中 `Actual Timeline` 里的单帧后，先看 Details 面板的三组字段：

- `jank_type`：卡顿归因。公开 schema 和 `android.frames.jank_type` 模块里能对上的常见值有 `App Deadline Missed`、`Buffer Stuffing`、`SurfaceFlinger CPU Deadline Missed`、`SurfaceFlinger GPU Deadline Missed`、`SurfaceFlinger Scheduling`、`Prediction Error`、`Display HAL`
- `present_type`：这一帧的呈现结果，UI 会显示 on time / early / late 等类型
- `on_time_finish`：该帧是否在 deadline 之前完成，0 表示 missed deadline

这里不要再用 `Slow UI thread`、`Slow bitmap uploads`、`Slow issue draw commands` 这类旧口径去解释 FrameTimeline。它们和 `actual_frame_timeline_slice` 的公开枚举不是一回事。

**Android 10/11 的 fallback**

Android 10/11 没有 FrameTimeline 主表时，判读入口要回到 `Choreographer#doFrame`、主线程 / `RenderThread` 的 `thread_state`、`VSYNC-app` / `VSYNC-sf`，以及 `SurfaceFlinger` 的合成轨道。工作顺序还是先找超时帧，再拆 UI thread、RenderThread、SurfaceFlinger 三段耗时，只是归因字段从 `jank_type` 换成时间轴和线程态本身。

**VSYNC-app 轨道**

在 `SurfaceFlinger` 进程下方，通常会出现 `VSYNC-app` 和 `VSYNC-sf` 两个信号轨道。`VSYNC-app` 每到一次，App 侧就有机会进入下一轮 `Choreographer#doFrame()`。如果一段卡顿里 `doFrame` 的开始时间不断向后拖，问题多半已经发生在主线程或 `RenderThread`。

**FrameTimeline 轨道（Android 12-17）**

`FrameTimeline` 把一帧从 App 提交到最终上屏的过程拆成可直接点选的 timeline slice。最省时间的做法，是先锁定一帧，再看 `jank_type`、`present_type`、`on_time_finish`，随后再顺着同一时间窗往下翻到 `Choreographer#doFrame`、`DrawFrame`、`SurfaceFlinger` 合成轨道。

### Jank 帧的定位步骤

流畅性分析的实战步骤可以总结为"三步走"：

**第一步：全局扫描，找到异常帧**

在 `Actual Timeline` 轨道上扫一遍，找到所有红色（超时）的帧。也可以用 `shift+m` 在这些位置插旗子标记，方便后续逐个分析。

Perfetto 还提供了内置的 `Metrics` 功能来快速统计掉帧概况。在右侧面板点击 `Metrics`，搜索 `jank` 相关指标，会显示总帧数、掉帧数、掉帧率等汇总数据。

**第二步：定位超时帧的瓶颈阶段**

选中一个超时帧，放大到 `Choreographer#doFrame` 的范围。`doFrame` 内部按顺序执行 `CALLBACK_INPUT` → `CALLBACK_ANIMATION` → `CALLBACK_INSETS_ANIMATION` → `CALLBACK_TRAVERSAL` → `CALLBACK_COMMIT`。检查哪个阶段的 Slice 最长：

- 如果 `CALLBACK_INPUT` 耗时长：说明事件处理（如 `dispatchTouchEvent`）太慢
- 如果 `CALLBACK_ANIMATION` 耗时长：说明动画计算（如属性动画的 `ValueAnimator`）太复杂
- 如果 `CALLBACK_TRAVERSAL` 耗时长：展开 `performTraversals`，进一步区分是 `measure`、`layout` 还是 `draw` 的锅

**第三步：追溯瓶颈的根因**

确定了瓶颈在哪个阶段之后，继续放大到具体的耗时 Slice，结合主线程的 `thread_state` 轨道来判读：

- 如果线程处于 `Running` 状态，说明是 CPU 密集型操作（如复杂布局的 measure、大量对象的创建）
- 如果线程处于 `S`（Sleeping）状态，说明在等待某个外部资源——通常是 Binder 调用或锁
- 如果线程处于 `D`（Uninterruptible Sleep）状态，说明在做磁盘 I/O——可能是读取资源文件

### Perfetto SQL 查询掉帧统计

```sql
INCLUDE PERFETTO MODULE android.frames.jank_type;

SELECT
  process.name AS process_name,
  COUNT(*) AS total_frames,
  SUM(CASE WHEN android_is_app_jank_type(jank_type) THEN 1 ELSE 0 END) AS app_janks,
  SUM(CASE WHEN android_is_sf_jank_type(jank_type) THEN 1 ELSE 0 END) AS sf_janks,
  SUM(CASE WHEN on_time_finish = 0 THEN 1 ELSE 0 END) AS missed_deadline_frames,
  ROUND(AVG(dur / 1e6), 2) AS avg_frame_ms,
  ROUND(MAX(dur / 1e6), 2) AS max_frame_ms
FROM actual_frame_timeline_slice
JOIN process USING (upid)
WHERE upid IS NOT NULL
GROUP BY process.name
ORDER BY missed_deadline_frames DESC, app_janks DESC;
```

这条查询直接落在 `actual_frame_timeline_slice` 的公开字段上。Android 10/11 没有这张表时，回到 `Choreographer#doFrame` 与线程态做手工判读，别把这条 SQL 硬套到旧版本 trace 上。

## 13.5.3 Binder 分析专题：调用频率、耗时与跨进程追踪

### Binder 分析为什么重要

Binder 是 Android 跨进程通信的核心机制。App 与 `system_server` 之间的几乎所有交互，包括启动 Activity、获取系统服务、窗口操作等，都通过 Binder 完成。某个 Binder 调用一旦变慢，依赖它的整条路径都会被拖慢，严重时甚至会触发 ANR。

Binder 分析的难点在于"跨进程"——一次调用涉及 Client 和 Server 两个进程，需要把两端的 Trace 拼在一起看。Perfetto 的 Flow 箭头功能正是为此而生。

### 抓取配置

公开可复现的 Binder 方案还是 `linux.ftrace` + `sched`。`android.binder` 这个数据源和 `android_binder_config` 这组字段，在公开的 `DataSourceConfig` 文档里找不到，因此不列入通用配置。

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      ftrace_events: "binder/binder_set_priority"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_blocked_reason"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "view"
      atrace_apps: "<你的目标App包名>"
    }
  }
}
```

`android_binder_txns` 是 trace processor 侧的标准库表，不是抓取阶段单独开启的数据源。trace 里只有 Binder driver 事件时，它仍然能给出 client / server 两端的 tids、进程名和 wall clock dur；如果同一段 trace 里还有 AIDL / HIDL slice，`aidl_name`、`interface`、`method_name` 这些字段才会补齐。

### 三步 Binder 分析工作流

面对一次 Binder 性能问题，先判断自己手里是哪一种 trace。

- **只有 ftrace 的 trace**：先靠 Binder driver 事件和 `thread_state` 复盘 client / server 两端的等待关系
- **含 framework / AIDL slice 的 trace**：在上面的基础上，再用 `android_binder_txns` 把接口名、client / server 线程和 Flow 箭头串起来

**步骤一：先把最慢的事务找出来**

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  aidl_name,
  client_process,
  client_thread,
  ROUND(client_dur / 1e6, 2) AS client_ms,
  server_process,
  server_thread,
  ROUND(server_dur / 1e6, 2) AS server_ms
FROM android_binder_txns
WHERE client_process = '<你的App包名>'
ORDER BY client_dur DESC
LIMIT 20;
```

`client_dur` 是调用方从发起请求到拿到回复的 wall clock 时间，`server_dur` 是服务端 slice 的执行时间。两者一起看，能先把问题切成两类：

- `client_dur` 长、`server_dur` 短，常见是排队、调度、抢锁，或者 server 线程迟迟没被唤醒
- `client_dur` 和 `server_dur` 都长，说明服务端自己就在慢路径里

如果 `aidl_name` 是空，不要急着怀疑 trace。本次录制没有保留可命名的 AIDL / HIDL slice 时，仍然能继续用 `client_tid`、`server_tid`、`client_ts`、`server_ts` 追下去。

**步骤二：用同一时间窗把 client 和 server 串起来**

在 UI 里点中 client 侧的 Binder slice 后，先看同一时间窗里的 Flow 箭头和 server Binder thread。trace 里有 AIDL slice 时，`binder reply` 这一段下面通常还能看到接口名对应的子 slice；没有 AIDL slice 时，就退回 `binder_transaction` / `binder_transaction_received` 事件，加 `thread_state` 看 server thread 何时被调度到 CPU。

这一步要把一笔 transaction 的 client 发起时间、server 开始处理时间、server 处理完成时间放到同一时间轴里。三段时间一旦落稳，问题在 client、调度还是 server 端逻辑，基本就分出来了。

**步骤三：继续拆调度、锁竞争和服务端工作**

调度和阻塞路径可以直接查标准库视图：

```sql
INCLUDE PERFETTO MODULE android.binder;

SELECT
  binder_txn_id,
  thread_state_type,
  thread_state,
  ROUND(thread_state_dur / 1e6, 2) AS state_ms
FROM android_sync_binder_thread_state_by_txn
WHERE client_tid = <关注的ClientTid> OR server_tid = <关注的ServerTid>
ORDER BY thread_state_dur DESC;
```

如果某一侧长期落在 `Runnable`，先看 CPU 竞争；如果大量时间落在 `S` 且 `blocked_function` 指向 `futex`，再怀疑锁竞争。需要进一步拿到 Java 层锁名时，再看 trace 里有没有 `monitor contention` slice：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  process_name,
  blocking_thread_name,
  blocked_thread_name,
  short_blocking_method,
  short_blocked_method,
  ROUND(dur / 1e6, 2) AS blocked_ms
FROM android_monitor_contention
WHERE process_name = 'system_server'
ORDER BY dur DESC
LIMIT 20;
```

`android_monitor_contention` 只会解析 trace 里已经存在的 `monitor contention` slice。它和 `android.java_hprof` 没关系。trace 里没有这组 slice 时，锁竞争分析就退回 `thread_state`、`blocked_function` 和 Binder 时序本身。

### 实战经验

启动和窗口切换里最常见的慢 Binder，大致有两类。

一类是 App 主线程在 Binder 上挂了二三十毫秒，跳到 `system_server` 后发现 `server_dur` 并不长，时间主要耗在 server 线程被唤醒之前，或者耗在 `futex` 等等待路径上。这种场景先查 Binder thread pool 是否饱和，再查 `WindowManagerService`、`ActivityTaskManagerService` 一类大锁附近的竞争。

另一类是 `server_dur` 本身就很长。这个时候不要继续盯 Binder 事件本身，直接落到 service 线程里的业务 slice，确认是布局、数据库、PackageManager 扫描，还是别的同步工作把 transaction 拉长。

[图：Binder 慢调用的等价图示。上方是 client 主线程发起 transaction，下方是 server Binder thread 开始处理、进入 `futex` 等待、恢复执行并返回 reply 的完整时间窗。]

## 13.5.4 内存分析专题：heapprofd 与 RSS/PSS 追踪

### Perfetto 中的内存观测层次

内存专题最容易混淆的地方，是“分配调用栈”“对象保留关系”“进程 RSS / PSS 曲线”对应三套不同工具。

- `linux.process_stats` 采样的是进程级 RSS、PSS 等指标，适合看宏观趋势
- `android.heapprofd` 采的是分配调用栈，主战场是 native heap；Android 12-17 还能把 Java allocation sampling 记到同一条 `Heap Profile` 轨道里
- `android.java_hprof` 记录的是 Java heap dump，关注 retained graph，也就是对象之间是谁在持有谁

把这三层分开后，分析路径会清楚很多。想找“谁在频繁分配内存”，用 heapprofd；想找“为什么对象还活着”，用 `android.java_hprof`；想看“系统什么时候开始顶不住”，再把进程级 Counter 放回时间轴里。

### heapprofd 的使用

`heapprofd` 的公开数据源名是 `android.heapprofd`。最常见的两种用法，是 native heap sampling 和 Java allocation sampling。

```protobuf
data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      process_cmdline: "<进程名>"
      sampling_interval_bytes: 4096
    }
  }
}
```

这条配置走的是 native heap profiling，追的是 `malloc` / `free`、`new` / `delete` 这类分配调用栈。它回答的问题，是哪条 native call stack 在吃内存。

如果怀疑 Java 侧在高频分配对象，而不是 native heap 长大，要把采样目标换成 ART heap：

```protobuf
data_sources {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      process_cmdline: "<进程名>"
      heaps: "com.android.art"
    }
  }
}
```

这时拿到的是 Java allocation sampling。它保留的是“对象在哪个 call stack 被创建”，不保留对象后来有没有被 GC，也不给 retained graph。

要看 retained graph，用的是另一套入口：

```protobuf
data_sources {
  config {
    name: "android.java_hprof"
    java_hprof_config {
      process_cmdline: "<进程名>"
      dump_smaps: true
    }
  }
}
```

`android.java_hprof` 记录的是 Java heap dump。它回答的是“Object X 通过哪条引用链把 Object Y 留在堆里”。这一层没有 heapprofd 那种 call-site flamegraph。

在 `user` build 上，`android.heapprofd` 仍然要求 App 带 `debuggable` 或 `profileable`。做 App 侧问题定位时，先确认 Manifest 已经开了对应标志。

### 在 Perfetto UI 中分析堆数据

`android.heapprofd` 和 `android.java_hprof` 都会在进程轨道附近留下 diamond 标记，但点开后的含义不同。

**heapprofd / Java allocation sampling**

点开 `Heap Profile` 轨道上的 diamond 后，Perfetto 会打开 flamegraph。对 native heap 来说，最常用的是这几种视图：

- `space`：当前仍未释放的字节数，适合看哪条 call stack 持续占内存
- `alloc_space`：整个录制期间累计分配的字节数，适合看内存抖动
- `objects`：当前仍未释放的对象数
- `alloc_objects`：整个录制期间累计分配的对象数

[图：Heap Profile 轨道与 flamegraph 等价图。上半部分标出 diamond 采样点，下半部分标出 `space` / `alloc_space` 两个视图以及一条最宽调用栈。]

**android.java_hprof / Java heap dump**

Java heap dump 也会落在 `Heap Profile` 轨道上，但点开后看的是 retention graph。这里要找的是大对象、长引用链、GC roots 到目标对象的保留路径，不是 alloc call stack。要查 `Bitmap`、`Activity`、`View` 为何还活着，这条链最直接。

Java heap sampling 和 Java heap dump 经常一起用。前者定位谁在分配，后者定位谁没被释放。

### 进程级内存 Counter

除了堆分析，Perfetto 的 `linux.process_stats` 数据源会定期采集进程级内存指标。默认配置下（`proc_stats_poll_ms: 1000`，即每秒一次）采集的是 RSS 相关指标。在 Trace 中展开进程轨道，会看到 `mem.rss`、`mem.rss.anon`、`mem.rss.file`、`mem.rss.shmem` 等 Counter 曲线。

PSS 不在默认输出中。只有在 `ProcessStatsConfig` 中设置 `scan_smaps_rollup: true` 时，Perfetto 才会从 `/proc/pid/smaps_rollup` 采集 `mem.smaps.pss` / `mem.smaps.pss.anon` 等轨道，且该操作需要读取 `/proc/pid/smaps_rollup` 的权限——`user` build 上非自身进程通常无法读取。

这些 Counter 曲线对于以下场景特别有用：

- **对比内存与性能的关联**：把内存 Counter 和掉帧时间点放到同一时间窗里比较，判断是否是内存压力导致的 GC 暴发进而引起卡顿
- **观察内存增长趋势**：在长时间使用的 Trace 中，看 `mem.rss.anon` 是否在持续上涨而不回落——这是内存泄漏的典型信号
- **量化 LMK 的影响**：结合 `oom_score_adj_update` 事件和内存 Counter，可以判断系统何时开始杀后台进程以回收内存

```sql
-- 查询进程 RSS anon 变化趋势
SELECT
  ts,
  (value / 1024) AS rss_anon_kb
FROM counter
JOIN process_counter_track ON counter.track_id = process_counter_track.id
JOIN process USING (upid)
WHERE process.name = '<App包名>'
  AND process_counter_track.name = 'mem.rss.anon'
ORDER BY ts;
```

RSS anon 对应匿名内存页（Java 堆、native heap、mmap 匿名映射），是内存泄漏排查的首选指标。Trace Processor 中 counter value 按 bytes 存储，`value / 1024` 得到 KB。

```protobuf
# 采集配置示例（只含 RSS）
data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      proc_stats_poll_ms: 1000
    }
  }
}
```

```protobuf
# 采集配置示例（含 PSS，需要额外权限）
data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      proc_stats_poll_ms: 1000
      scan_smaps_rollup: true
    }
  }
}
```

## 13.5.5 I/O 分析专题：Block I/O 与文件系统事件追踪

### I/O 问题为什么难查

Android 上的 I/O 性能问题通常表现为线程进入 `D`（Uninterruptible Sleep）状态，即“不可中断的磁盘睡眠”。和普通的 `S` 状态不同，`D` 状态的线程不响应信号。即使 ANR 的超时计时已经开始，线程也只能等 I/O 完成后再恢复执行，这也是主线程做磁盘 I/O 特别危险的原因。

I/O 分析的难点在于，"线程在等 I/O"只是表象，需要知道等的是什么 I/O、请求的扇区在哪里、排队等了多久。Perfetto 通过 ftrace 的 block 层事件提供了这些信息。

### 抓取配置

I/O 分析需要在 ftrace 中开启 block 层事件和文件系统事件：

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "block/block_rq_issue"
      ftrace_events: "block/block_rq_complete"
      ftrace_events: "block/block_rq_insert"
      ftrace_events: "ext4/ext4_da_write_begin"
      ftrace_events: "ext4/ext4_da_write_end"
      ftrace_events: "ext4/ext4_sync_file_enter"
      ftrace_events: "ext4/ext4_sync_file_exit"
      ftrace_events: "f2fs/f2fs_write_begin"
      ftrace_events: "f2fs/f2fs_write_end"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_blocked_reason"
    }
  }
}
```

`block_rq_issue` 表示一个 I/O 请求被提交到块设备层；`block_rq_complete` 表示请求完成。两者之间的时间差就是单次 I/O 的实际耗时。`sched_blocked_reason` 记录线程进入 `D` 状态时的等待调用点（`caller` 字段）和 `io_wait` 标记——用于判断 D 状态等待是否由 I/O 引起。block device 和扇区信息不来自 `sched_blocked_reason`，需要同时间窗关联 `block_rq_issue` / `block_rq_complete` 或 `ext4_*` / `f2fs_*` 文件系统事件。

### 在 Trace 中定位 I/O 瓶颈

**第一步：先锁定进入 `D` 状态的线程**

在主线程或目标线程的 `thread_state` 轨道里，`D` 表示线程在等不可中断的内核 I/O。点开这个时间段后，先看 `blocked_function`，常见会落到 `do_page_fault`、`filemap_fault`、`ext4_file_read_iter`、`f2fs_*` 一类路径。

**第二步：再回到设备级 `block_io` 轨道**

同一时间窗里，到 `track.type='block_io'` 的设备轨道看切片。这里的每条 slice 代表一次块设备 I/O，视角是设备，不带进程名。它能回答“磁盘这会儿忙不忙、单次 I/O 拖了多久”，不能单独回答“哪一个 App 在背锅”。

**第三步：把设备 I/O 和线程等待重新拼回去**

进程归因要把三组证据放在一起看，线程的 `D` 状态、文件系统事件（`ext4_*` / `f2fs_*`）以及同一时间窗里的 `block_io` slice。如果只看 block 设备轨道，很容易把“设备忙”误写成“某个进程一定在慢 I/O”。

如果怀疑设备队列本身已经堆满，可以再用 `linux_active_block_io_operations_by_device` 看某个 block device 在一段时间里挂着多少未完成请求。

### 常见的 App 端 I/O 场景

实际分析中，App 端 I/O 问题大多集中在以下场景：

- **启动时读取 DEX 和资源文件**：冷启动时 ART 需要加载 DEX 文件，布局渲染需要读取资源 XML 和图片。如果这些文件没有被优化（如未启用 DEX 布局优化或资源压缩），会导致大量随机 I/O
- **SharedPreference 的同步写入**：`SharedPreferences.commit()` 是同步写磁盘操作，如果在主线程调用，线程会进入 `D` 状态直到写入完成。这就是为什么 Google 推荐使用 `apply()` 代替 `commit()`
- **数据库查询**：SQLite 的复杂查询或缺少索引的全表扫描可能导致磁盘 I/O
- **日志文件写入**：某些 App 的日志系统在主线程做同步文件写入

### Perfetto SQL 查询 I/O 耗时

```sql
INCLUDE PERFETTO MODULE linux.block_io;

SELECT
  linux_device_major_id(extract_arg(track.dimension_arg_set_id, 'block_device')) AS major,
  linux_device_minor_id(extract_arg(track.dimension_arg_set_id, 'block_device')) AS minor,
  COUNT(*) AS io_count,
  ROUND(AVG(slice.dur / 1e6), 2) AS avg_io_ms,
  ROUND(MAX(slice.dur / 1e6), 2) AS max_io_ms,
  ROUND(SUM(slice.dur / 1e6), 2) AS total_io_ms
FROM slice
JOIN track ON slice.track_id = track.id
WHERE track.type = 'block_io'
GROUP BY major, minor
ORDER BY total_io_ms DESC
LIMIT 20;
```

这条 SQL 统计的是设备级 `block_io` slice。要把它归回具体的 App 或线程，还得把结果再和 `thread_state`、`sched_blocked_reason`、`ext4_*` / `f2fs_*` 事件放到同一时间窗里。

## 13.5.6 功耗分析专题：CPU 频率、Suspend/Resume 与 Wakelock

> 本节为扩展内容，视素材丰富程度选择性深入。

### 为什么功耗分析需要 Perfetto

功耗优化的本质是让 CPU 和外设尽可能多地处于低功耗状态。Perfetto 可以呈现系统在每个时刻的运行状态：CPU 跑在什么频率、是否进入了 suspend、哪些 Wakelock 阻止了系统休眠。

### 关键轨道与指标

**CPU 频率轨道**

在 CPU Info 区域，每个 CPU 核心下方都有频率变化曲线（`cpufreq`）。如果某个核心长时间运行在高频率（如 2.84 GHz），说明有持续的 CPU 密集任务。对于功耗优化，理想情况是核心在空闲时降到最低频率、甚至被 hotplug off。

**Suspend/Resume 事件**

设备息屏后，理想状态下应该快速进入 suspend（CPU 完全停止）。如果 Trace 中发现息屏后 CPU 仍然长时间活跃，说明有东西在阻止系统休眠。

**Wakelock 轨道**

Wakelock 是 Android 中阻止 CPU 进入 suspend 的机制。App 或系统服务通过 `PowerManager.WakeLock` 申请 Wakelock 后，CPU 会保持运行直到 Wakelock 被释放。在 Perfetto 中，Wakelock 信息可以通过 `ftrace` 的 `power/wakeup_source_activate` 和 `power/wakeup_source_deactivate` 事件来追踪。

### 抓取配置建议

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
      atrace_categories: "power"
      atrace_categories: "sched"
    }
  }
}
```

## 13.5.7 多进程协同分析：System Server + App 联合分析

> 本节为扩展内容，视素材丰富程度选择性深入。

### 为什么需要多进程协同分析

Android 的很多操作都跨进程。App 发起请求，`system_server` 处理，`surfaceflinger` 合成，再到屏幕。只盯一个进程，很难知道延迟卡在 App、系统服务，还是合成阶段。Perfetto 的优势，是能把这几段工作放到同一时间轴里一起看。

### Pin 功能的实战应用

Pin 的价值，在于把分散在 Trace 里的关键线程固定到顶部，避免来回滚动时丢掉时间关系。

滑动和掉帧场景里，常用的一组线程是：

1. App 的 main thread
2. App 的 `RenderThread`
3. `surfaceflinger` 主线程
4. `system_server` 里和窗口、输入、显示有关的 Binder / service 线程

把它们固定到顶部后，横向扫同一段时间窗，就能直接看到 Input、`Choreographer#doFrame`、`DrawFrame`、`queueBuffer`、SurfaceFlinger 合成和 present 的先后顺序。

[图：多进程 Pin 等价图。把 App main thread、`RenderThread`、`surfaceflinger` 主线程、`system_server` Binder 线程固定到顶部，在同一时间轴标出 Input -> `Choreographer#doFrame` -> `DrawFrame` -> `queueBuffer` -> SurfaceFlinger composition -> present。]

### Flow 箭头的跨进程追踪

Flow 箭头是把不同进程串起来的最快办法。点中 Binder transaction slice 后，先沿着 Flow 跳到 server 侧，再看同一时间窗里的 `thread_state` 和 service slice。启动、窗口切换、多进程渲染这类问题，通常都是这样一段一段拼出来的。

### 分析技巧总结

多进程分析有一个固定顺序：

1. 在单一进程里先把异常时间窗缩小
2. 用 Binder Flow、FrameTimeline 或 `queueBuffer` / `SurfaceFlinger` 这类锚点，把相关线程拉到顶部
3. 用同一时间轴比较各段开始时间、结束时间和阻塞点
4. 再回到 SQL 或源码，确认最慢的那一段属于谁

## 本节小结

五个专题覆盖了 Android 性能分析中最常见的场景。它们共享同一套分析顺序：**定位异常（通过 Timeline、Counter 或 Metrics）→ 追溯根因（通过 thread_state、Flow 箭头、Critical Path）→ 量化评估（通过 Perfetto SQL）**。

几个贯穿各专题的通用技巧：

- **CPU 状态占比**是快速判断瓶颈类型的利器：Running 过多说明 CPU 密集，Sleep 过多说明在等外部资源，D 状态过多说明在做磁盘 I/O
- **Flow 箭头**是跨进程分析的桥梁，尤其在 Binder 分析和多进程协同分析里很有用
- **Pin 功能**可以把关注的线程集中到一起，对于时序关系的判断很有帮助
- **Perfetto SQL** 在需要量化分析时提供了强大的编程能力，但对于日常的快速定位，界面操作已经足够

本节内容与前面的基础章节形成了完整的分析工具链：§13.1-13.4 提供了工具基础，本节提供了分析框架。接下来 §13.6 和 §13.7 将进一步介绍线程 CPU 状态分析和 Perfetto 的高级用法。

## 参考资料

- [Perfetto 官方文档 - PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Perfetto 官方文档 - SQL Tables Reference](https://perfetto.dev/docs/analysis/sql-tables)
- [Perfetto 官方文档 - Frame Timeline tables](https://perfetto.dev/docs/analysis/sql-tables#frame-timeline-tables)
- [Perfetto 官方文档 - Native Heap Profiler (heapprofd)](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Perfetto 官方文档 - Java Heap Dumps](https://perfetto.dev/docs/data-sources/java-heap-profiler)
- [Android Perfetto 系列 3：熟悉 Perfetto View](https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/)（高爷原创）
- [Android Perfetto 系列 5：Choreographer 渲染流程](https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/)（高爷原创）
- [Android Perfetto 系列 10：Binder 调度与锁竞争](https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/)（高爷原创）
- [Android Systrace 线程 CPU 运行状态分析技巧](https://www.androidperformance.com/)（高爷原创）
