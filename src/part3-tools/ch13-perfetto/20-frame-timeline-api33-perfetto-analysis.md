---
title: "Frame Timeline API 33 Perfetto 深度分析：Expected vs Actual Timeline"
chapter: "13.20"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Perfetto, FrameTimeline, Jank, Choreographer, 渲染性能分析]
related_chapters: ["2.4", "2.32", "13.5", "13.8", "13.14", "13.19"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.h"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/JankTracker.cpp"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: research
    path: "intake/research-feeds/2026-04-10-07-frame-timeline-perfetto-visualization-choreographer-api33.md"
---

# 13.20 Frame Timeline API 33 Perfetto 深度分析：Expected vs Actual Timeline

FrameTimeline 是 Android 12 引入、Android 13 对应用层开放 API 的帧级性能诊断能力。它回答一个核心问题：**某一帧是"按预期完成"还是"超时了"，如果超时，责任在 App、SurfaceFlinger、还是显示硬件。**

本节聚焦 Perfetto 中 Frame Timeline 数据源的可视化分析方法论——如何读 Expected / Actual 两条时间线 Track、如何用颜色编码做 jank 归因、如何通过 FrameData API 和 SQL 查询定位问题帧。FrameTimeline 的内部数据结构（SurfaceFrame、TokenManager、JankClassificationThresholds）详见 §2.32；Buffer 级事件追踪（FrameTracer）详见 §13.19；CUJ 场景级聚合分析详见 §13.14。

## 要点

### 🔹 Expected Timeline 与 Actual Timeline 的物理含义

FrameTimeline 在 Perfetto 中产出的核心数据是两条并排的 Track：**Expected Timeline** 和 **Actual Timeline**。理解它们各自度量什么，是 jank 诊断的起点。

**Expected Timeline** 记录的是系统为应用分配的帧时间窗口。每个 slice 的起始时间对应 Choreographer 回调的预期调度时刻，结束时间对应预期完成渲染的时刻。这个"预期"不是简单的 VSync-app 时刻——它由 SurfaceFlinger 的 VSyncPredictor 综合以下因素计算得出：

- **VSync offset**：VSYNC-sf 与 VSYNC-app 之间的相位差（典型值 1-3ms），决定了 App 和 SF 各自的可用工作时间窗
- **SurfaceFlinger 合成时间预算**：SF 需要在 VSYNC-sf 之前完成合成准备工作
- **Display 显示延迟**：从 SF 提交到像素实际出现在屏幕上的时间

三者的叠加构成了 Expected Timeline slice 的起止边界。因此 Expected Timeline slice 的起点与 VSYNC-app 信号时刻之间存在可观测的时间差——这个差值就是 VSync offset 加上 SF 合成预算。

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.h:83-94; perfetto.dev/docs/data-sources/frametimeline]

**Actual Timeline** 记录的是应用实际完成帧渲染（含 GPU 工作）并发送给 SurfaceFlinger 的真实耗时。Actual Timeline slice 的结束时间取 `max(gpu_completion_time, post_time)`——也就是说，它等待 GPU 真正完成渲染后才标记帧结束。这是 Actual Timeline 与 Choreographer#doFrame slice 的关键区别：doFrame 只反映 CPU 侧的回调执行耗时，而 Actual Timeline 包含了 GPU 异步渲染的等待时间。

两条 Timeline 的偏差即为 jank：当 Actual Timeline slice 的结束时间超出 Expected Timeline slice 的边界，这一帧就是 jank 帧。

### 🔹 Perfetto 中的三条关键 Track

打开一份包含 Frame Timeline 数据源的 Perfetto trace，需要在 UI 中定位三条 Track 才能完成帧级诊断：

| Track 名称 | 位置 | 回答的问题 |
|------------|------|-----------|
| **Expected Timeline** | SurfaceFlinger 进程下 | 系统为每帧分配的时间窗口是什么 |
| **Actual Timeline** | SurfaceFlinger 进程下 | 每帧实际花了多长时间 |
| **Choreographer#doFrame** | App 主线程 Track 中 | App 侧每帧的 CPU 执行耗时是多少 |

三者按时间轴对齐后，诊断逻辑如下：

1. 看 **Expected Timeline**：帧的预期开始和结束时刻，确认刷新率是否正确（90Hz 设备的 Expected slice 宽度应约 11.1ms）
2. 看 **Actual Timeline**：帧的实际耗时 slice 是否超出 Expected 边界
3. 看 **Choreographer#doFrame**：如果 Actual 超时，进一步确认 CPU 侧 doFrame 耗时是否合理——doFrame 快但 Actual 慢说明瓶颈在 GPU 异步渲染；doFrame 本身慢说明 CPU 侧（measure/layout/draw）是瓶颈

一个常见误区是只看 Choreographer#doFrame 就下结论。doFrame 在主线程上只是一个 CPU 侧的 slice，它结束时 GPU 可能还在异步渲染。如果只看 doFrame 耗时正常就判定"没有 jank"，会漏掉 GPU 渲染超时导致的帧。Actual Timeline 的价值正在于它包含了 GPU 完成时间。

> Choreographer#doFrame slice 中还携带 vsyncId 参数（如 `Choreographer#doFrame [vsyncId=12345]`），可以用来与 Expected/Actual Timeline 中的对应帧精确对齐。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java — doFrame 回调链; perfetto.dev/docs/data-sources/frametimeline]

### 🔹 颜色编码规则与 Jank 归因

Perfetto UI 中 Expected 和 Actual Timeline 的 slice 使用颜色编码标识 jank 类型。这套颜色编码是 FrameTimeline 在 SurfaceFlinger 侧计算后写入 trace 的，不需要开发者手动判定。

| 颜色 | 含义 | 判定条件 |
|------|------|---------|
| 🟢 绿色 | 帧按时完成，无 jank | Actual 在 Expected 边界内完成 |
| 🔴 红色 | App 导致 jank | Actual 超出 Expected，且 `jank_type` 包含 `AppDeadlineMissed` 或 `AppResyncedJitter` |
| 🟡 黄色 | SurfaceFlinger 导致 jank | Actual 超出 Expected，且 `jank_type` 包含 `SurfaceFlingerCpuDeadlineMissed` / `SurfaceFlingerGpuDeadlineMissed` / `SurfaceFlingerScheduling` |
| 灰色 | 非 jank 的掉帧或特殊状态 | `Dropped`、`DisplayHAL`、`PredictionError` 等 |

红色的判定依据来自 FrameTimeline 的 `isSelfJunky()` 检查（§2.32）：只有 `AppDeadlineMissed | AppResyncedJitter | Unknown` 三种 jank 类型被视为 App 自身造成的 jank。SurfaceFlinger 调度延迟、HWC 超时、预测误差等原因导致的掉帧不会标记为红色——它们的责任不在 App。

这意味着一个重要的实践结论：**看到 Actual Timeline 中有红色 slice，App 开发者需要关注；看到黄色 slice，问题出在系统侧（可能是 HWC overlay 不足、SF 合成超时或设备调度问题），App 侧优化无法解决。**

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp:562-573 — isSelfJanky() 判定逻辑]

### 🔹 FrameData API 核心方法

Android 13（API 33）在 Choreographer 中引入了 `FrameData` 内部类，向应用层暴露 FrameTimeline 的关键时间戳。这是应用层第一次能在代码中直接获取帧调度信息，而不依赖 Perfetto trace 的事后分析。

`Choreographer.FrameData` 包含四个核心方法：

| 方法 | 返回值 | 含义 |
|------|--------|------|
| `getFrameTimeNanos()` | `long` | 当前帧的 VSync 时间戳（即 frameTimeNanos，与 `doFrame(long frameTimeNanos)` 参数一致） |
| `getLastFrameTimeNanos()` | `long` | 上一帧的 VSync 时间戳 |
| `getIntervalNanos()` | `long` | 帧间隔（由当前刷新率决定，60Hz 约 16.6ms，120Hz 约 8.3ms） |
| `getDeadlineNanos()` | `long` | 帧截止时间（帧必须在此时间前完成 CPU 侧工作） |

`getDeadlineNanos()` 是其中最有诊断价值的方法。它返回的时间戳表示当前帧的 CPU 侧工作截止时刻——超过这个时间，帧就有 jank 风险。Compose 的 PausableComposition 正是基于 `FrameData.deadlineNanos` 做暂停判定：当 deadline 临近时暂停 Composition，让出主线程给当前帧的绘制任务（详见 §2.28）。

获取 FrameData 的方式：

```java
// Java — 在 Choreographer.FrameCallback 中获取
choreographer.postFrameCallback(new Choreographer.FrameCallback() {
    @Override
    public void doFrame(long frameTimeNanos) {
        // API 33+ 可通过 FrameTimeline 获取扩展信息
        if (Build.VERSION.SDK_INT >= 33) {
            // FrameData 通过 Choreographer 实例获取
            // 实际 API 路径：Choreographer.getFrameData() (API 33+, hidden 到 System API)
        }
    }
});
```

```kotlin
// Kotlin — 通过 FrameTimeline 获取多帧预测
if (Build.VERSION.SDK_INT >= 33) {
    val frameTimelines = choreographer.frameTimelines // List<FrameTimeline>
    val preferred = choreographer.preferredFrameTimeline // 当前最优帧调度计划
    // preferred.frameTimeNanos / preferred.deadlineNanos / preferred.expectedPresentationTimeNanos
}
```

`getFrameTimelines()` 返回系统支持的所有帧时间线列表（Android 17 中 `FRAME_TIMELINES_CAPACITY = 7`），`getPreferredFrameTimeline()` 返回系统推荐的最优帧调度计划。多帧时间线预测能力使得 App 可以提前知道未来几帧的调度计划，做资源预加载或自适应渲染决策。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java — FrameData 内部类定义; §2.32 FrameTimeline 数据结构]

### 🔹 FrameTimeline 数据源在 Perfetto 中的配置

FrameTimeline 数据通过 Perfetto 数据源 `android.surfaceflinger.frametimeline` 发射。要在一个 Perfetto trace 中获得 Frame Timeline 数据，需要确保 trace 配置中包含该数据源。

**方法一：通过 atrace 命令快速采集**（适合开发调试）

```bash
# 基础 atrace 配置：包含 FrameTimeline 必需的 category
adb shell atrace -z -b 32768 \
  sched freq idle am wm gfx view binder_driver hal \
  -t 10 -o /sdcard/trace.trace
```

其中 `gfx` 和 `view` 是 FrameTimeline 数据的关键 atrace category。`gfx` 启用 SurfaceFlinger 侧的 FrameTimeline track 输出；`view` 启用 App 侧的 Choreographer#doFrame slice。

**方法二：通过 perfetto 命令行精确配置**（适合生产环境精确采集）

```bash
# 使用 perfetto 命令行，通过 config 文件精确控制数据源
adb shell perfetto -o /data/misc/perfetto-traces/trace.perfetto-trace -t 15s \
  sched freq idle am wm gfx view binder_driver hal
```

**方法三：通过 Perfetto config 文件（推荐生产使用）**

```protobuf
# perfetto-config.pbtxt
duration_ms: 15000
buffers { size_kb: 65536 }

# FrameTimeline 数据源（SurfaceFlinger 侧）
data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
    target_buffer: 0
  }
}

# FrameTracer 数据源（Buffer 级事件，可选但推荐）
data_sources {
  config {
    name: "android.surfaceflinger.frame"
    target_buffer: 0
  }
}

# atrace categories（App 侧 Choreographer#doFrame）
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_categories: "view"
      atrace_categories: "gfx"
      atrace_categories: "sched"
      atrace_apps: "*"
    }
  }
}
```

**采集注意事项**：

- FrameTimeline 数据源的输出在 Perfetto UI 中显示为 SurfaceFlinger 进程下的 Expected Timeline 和 Actual Timeline Track
- 如果 trace 中缺少这两条 Track，首先检查设备是否 Android 12+（FrameTimeline 从 Android 12 开始可用），以及 atrace/perfetto 配置是否包含 `gfx` category
- `android.surfaceflinger.frametimeline` 和 `android.surfaceflinger.frame` 是两个独立数据源（详见 §13.19），前者回答"帧是否按时"，后者回答"buffer 卡在哪个阶段"

[已验证: AOSP android-17.0.0_r1; perfetto.dev/docs/data-sources/frametimeline]

### 🔹 Expected Timeline 与 VSYNC-app 的时间差分析

在 Perfetto trace 中仔细观察会发现：Expected Timeline slice 的起始时间与 VSYNC-app 信号时刻并不重合，两者之间存在一个可观测的时间差。理解这个时间差的来源，是正确解读 FrameTimeline 数据的关键。

VSYNC-app 是 App 收到 VSync 信号并开始执行 doFrame 回调的时刻。Expected Timeline 的起始时间则是一个**经过 VSyncPredictor 优化计算后的调度计划时刻**，它考虑了整个渲染管线的时间预算分配：

```text
VSync 信号周期 (T)
├── VSYNC-app offset ──→ App 可用工作时间窗
│   └── App 在此窗口内完成 measure/layout/draw + GPU 提交
├── VSYNC-sf offset ──→ SurfaceFlinger 可用工作时间窗
│   └── SF 在此窗口内完成 layer 合成准备
└── Display latency ──→ 像素实际出现在屏幕上

Expected Timeline = [VSYNC-app, VSYNC-app + App工作预算 + SF合成预算 + Display延迟]
```

具体来说，Expected Timeline 的起始时间对应 `VsyncEventData.preferredFrameTimeline().vsyncId` 映射的时间戳，而非原始的 `frameTimeNanos`。在 Android 17 中，Choreographer 的多帧时间线预测架构（`FRAME_TIMELINES_CAPACITY = 7`）支持同时维护 7 条候选帧时间线，`getPreferredFrameTimeline()` 返回其中最优的一条。

**这个时间差的实际影响**：

1. 不能用 `SystemClock.nanoTime() - frameTimeNanos` 来判断帧是否超时——正确的参照是 `FrameData.getDeadlineNanos()` 而非 `frameTimeNanos + frameInterval`
2. 高刷新率设备（120Hz/144Hz）的 VSync offset 更小，App 可用工作窗口更窄，Expected 与 Actual 的偏差容忍度更低
3. Buffer Stuffing Recovery（Android 16 引入，详见 §2.25）会在 buffer 等待时对 FrameTimeline 施加负偏移，进一步改变 Expected Timeline 的节拍

### 🔹 Perfetto SQL 查询：从 Frame Timeline 提取 jank 数据

Perfetto UI 的可视化适合定性分析（"有没有 jank"），SQL 查询适合定量分析（"多少帧 jank 了，各是什么类型"）。FrameTimeline 数据在 Trace Processor 中存储在两张核心表中：`expected_frame_timeline_slice` 和 `actual_frame_timeline_slice`。

**查询 1：列出所有 jank 帧**

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  actual.slice_name,
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

`on_time_finish = 0` 表示帧未按时完成（jank 帧）。`display_frame_token` 是连接 Expected 和 Actual 的外键——同一个 frame token 在两条 timeline 中各有一个 slice。`jank_type` 是 SurfaceFlinger 写入的 jank 分类字符串。

**查询 2：按 jank 类型统计**

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.frames.jank_type;

SELECT
  jank_type,
  COUNT(*) AS frame_count,
  CAST(AVG(dur / 1e6) AS FLOAT) AS avg_dur_ms,
  CAST(MAX(dur / 1e6) AS FLOAT) AS max_dur_ms
FROM actual_frame_timeline_slice
WHERE on_time_finish = 0
GROUP BY jank_type
ORDER BY frame_count DESC;
```

`jank_type` 的值与颜色编码的映射关系：包含 `AppDeadlineMissed` 的帧在 UI 中显示为红色；包含 `SurfaceFlingerCpuDeadlineMissed` 或 `SurfaceFlingerGpuDeadlineMissed` 的帧显示为黄色。jank 类型的完整列表和 `isSelfJanky()` 判定逻辑详见 §2.32。

**查询 3：计算 P50/P90/P99 帧耗时分布**

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

WITH frame_durations AS (
  SELECT
    CAST(dur / 1e6 AS FLOAT) AS dur_ms,
    on_time_finish,
    jank_type
  FROM actual_frame_timeline_slice
  -- 可选：按 layer/进程名过滤
  -- WHERE slice_name LIKE 'com.example.%'
)
SELECT
  COUNT(*) AS total_frames,
  SUM(CASE WHEN on_time_finish = 0 THEN 1 ELSE 0 END) AS jank_frames,
  CAST(SUM(CASE WHEN on_time_finish = 0 THEN 1.0 ELSE 0 END) / COUNT(*) * 100 AS FLOAT) AS jank_rate_pct,
  APPROX_QUANTILE(dur_ms, 0.5) AS p50_ms,
  APPROX_QUANTILE(dur_ms, 0.9) AS p90_ms,
  APPROX_QUANTILE(dur_ms, 0.99) AS p99_ms
FROM frame_durations;
```

这张表适合作为帧性能的量化基线：P50 反映典型帧耗时，P90 反映用户体验下限（10% 的帧比这更慢），jank_rate_pct 反映整体流畅度。

[已验证: Perfetto v54.0 — `android.frames.timeline` / `android.frames.jank_type` 标准库模块]

## 扩展

### 🔸 自定义 Frame Timeline 可视化分析

Perfetto UI 的 Expected/Actual Timeline Track 适合单次 trace 分析，但在团队协作和持续监控场景下，需要把帧数据导出为结构化报告。

**方法一：Perfetto Trace Processor + Python 脚本**

```python
# 使用 trace_processor Python API 批量提取帧性能数据
from perfetto.trace_processor import TraceProcessor

tp = TraceProcessor(trace='trace.perfetto-trace')
query = """
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  CAST((actual.ts - trace_start()) / 1e6 AS INTEGER) AS time_ms,
  CAST(actual.dur / 1e6 AS FLOAT) AS actual_ms,
  actual.on_time_finish,
  actual.jank_type
FROM actual_frame_timeline_slice AS actual
WHERE actual.on_time_finish = 0
ORDER BY actual.ts
"""
df = tp.query(query).as_pandas_dataframe()
# 导出为 CSV 或接入 Grafana / Power BI
df.to_csv('jank_report.csv', index=False)
```

**方法二：结合 CUJ 标准库做场景级分析**

当需要把 jank 帧关联到具体的用户交互场景（如"列表滚动"、"页面返回"）时，使用 `android.cujs.base` 模块（详见 §13.14）。CUJ 分析会把 jank 帧按交互场景分组，计算每个场景的 weighted jank score——这比单纯的帧数统计更能反映用户体验。

注意：`android.cujs.base` 默认仅覆盖 `com.android.*` 和 `com.google.android.*` 进程。第三方 App 需要使用 AndroidX JankStats API 或自定义 atrace marker 扩展（三条路径详见 §13.14）。

### 🔸 与 Compose PausableComposition 的联动分析

Compose 1.10（2025 年 12 月稳定）将 PausableComposition 设为默认行为。该机制在帧 deadline 临近时暂停 Composition，让出主线程给当前帧的绘制任务。通过 Frame Timeline 可以直接观察 PausableComposition 的效果。

**观察方法**：

1. 在 Perfetto trace 中找到 Compose 应用的主线程 Track
2. 观察 `Choreographer#doFrame` slice 内部的 Composition 相关 slice（如 `Compose:recompose`、`Compose:applyChanges`）
3. 对比 Expected Timeline：如果 Composition slice 在 deadline 前暂停（slice 出现间隙），下一帧的 Actual Timeline 应该显示帧按时完成
4. 如果暂停后仍然 jank（Actual 超出 Expected），说明即使暂停了 Composition，剩余的绘制 + GPU 渲染仍然超出了帧预算——需要优化 UI 复杂度或减少 layout 次数

**shouldPause 回调与 FrameData.deadline 的关系**：

PausableComposition 的 `shouldPause` lambda 内部检查 `FrameData.getDeadlineNanos() - System.nanoTime() < threshold`。当剩余时间小于阈值时返回 true，Composition 暂停。这意味着：

- deadline 的准确性直接影响 PausableComposition 的效果
- 如果 Expected Timeline 与 Actual Timeline 的偏差较大（PredictionError jank 频繁），说明 VSyncPredictor 的预测不准，PausableComposition 基于 deadline 的暂停判定也会受影响
- 在高刷新率设备上（120Hz/144Hz），帧间隔更短，deadline 更紧，PausableComposition 的暂停频率更高，每次暂停的代价（上下文切换）相对于帧预算的占比也更大

[结构参考: intake/research-feeds/2026-04-10-07-compose-pausable-composition-choreographer-deadline.md]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java — FrameData.deadlineNanos]

<!-- outline-end -->
