---
title: "FrameTracer 与 Graphics Frame Event 数据通路"
chapter: "13.19"
status: ready-for-review
drafted_date: "2026-06-27"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Layer.cpp"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto"
  - type: research
    path: "DeepResearch/2026-06-26-android17-frametracer-graphics-frame-event.md"
tags: [perfetto, frametracer, graphics, buffer-lifecycle, surfaceflinger, gpu]
related_chapters: ["13.5", "13.14", "13.15", "13.17", "2.6", "18.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "研究素材"
---

# 13.19 FrameTracer 与 Graphics Frame Event 数据通路

## 两条数据源，两个问题

SurfaceFlinger 进程内运行着两条容易混淆的 Perfetto 数据源：

| 数据源 | 承载文件 | 回答的问题 |
|--------|---------|-----------|
| `android.surfaceflinger.frametimeline` | `Scheduler/FrameTimeline.cpp` | 这帧是否按时，为何延迟 |
| `android.surfaceflinger.frame` | `FrameTracer/FrameTracer.cpp` | buffer 在 GPU↔HWC 流水线上卡在哪一步 |

FrameTimeline 产出 jank 分类（App deadlined miss / SurfaceFlinger deadlined miss / Display halo / Dropped / Missed），对「帧有没有问题」给出定性判断。FrameTracer 产出的是 buffer 生命周期事件——从 App 端 `dequeueBuffer` 到 SF 释放 `RELEASE_FENCE`，每一步都有时间戳。它回答的是「这帧在流水线的哪一段花的时间最长」。

两者通过 `buffer_id` + `frame_number` 在 trace processor 侧可关联。典型工作流：先用 FrameTimeline 找到 jank 帧，再用 FrameTracer 定位卡在哪个阶段。

> 源码级细节（初始化路径、proto 定义、Layer.cpp 调用点分布）详见 13.17 §1.7-1.8。本节聚焦实战诊断方法。

## Buffer 生命周期事件链

FrameTracer 追踪的是一个 GraphicBuffer 从 App dequeue 到最终显示再释放的完整旅程。13 种 `BufferEventType` 中，AOSP 代码中实际发射的只有 6 种，其余是 proto 占位符或 OEM 自定义。下图展示的是 AOSP 可观测的完整链路：

```mermaid
sequenceDiagram
    participant App
    participant BufferQueue
    participant SF as SurfaceFlinger
    participant HWC
    participant Display

    App->>BufferQueue: dequeueBuffer
    Note over App,BufferQueue: ◀ DEQUEUE (Layer.cpp:982)
    App->>BufferQueue: queueBuffer
    Note over App,BufferQueue: ◀ QUEUE (Layer.cpp:986)
    BufferQueue->>SF: acquireBuffer + acquireFence
    Note over SF: ◀ ACQUIRE_FENCE (Layer.cpp:1269)
    SF->>SF: latchBuffer
    Note over SF: ◀ LATCH (Layer.cpp:1271)
    alt HWC 合成
        SF->>HWC: validate + present
        Note over SF: ◀ HWC_COMPOSITION_QUEUED (OEM 自定义)
    else GPU 合成 (FALLBACK)
        SF->>SF: RenderEngine::drawLayers
        Note over SF: ◀ FALLBACK_COMPOSITION (Layer.cpp:1453)
    end
    HWC->>Display: present
    Note over SF: ◀ PRESENT_FENCE (Layer.cpp:1476)
    SF->>BufferQueue: releaseBuffer + releaseFence
    Note over SF: ◀ RELEASE_FENCE
```

六个阶段的时间含义：

| 阶段 | 起止 | 含义 |
|------|------|------|
| DEQUEUE → QUEUE | App 端 | App 拿到 buffer 后的绘制耗时（CPU + GPU 提交） |
| QUEUE → ACQUIRE_FENCE | BufferQueue 传输 | buffer 从 App 进程到 SF 进程的传输 + acquire fence signal 等待（GPU 完成渲染） |
| ACQUIRE_FENCE → LATCH | SF 内部 | SF acquire buffer 到决定 latch 的间隔，通常接近 0（同一帧内） |
| LATCH → FALLBACK_COMPOSITION | GPU 合成 | 仅 GPU 合成路径有此事件，表示 GPU 实际完成合成的时刻 |
| LATCH → PRESENT_FENCE | 显示呈现 | latch 到上屏的时间，包含 HWC 合成或 GPU 合成 + 显示控制器刷新 |
| PRESENT_FENCE → RELEASE_FENCE | buffer 回收 | buffer 被显示控制器读取完毕，归还给 BufferQueue 供 App 复用 |

关键区分点：`HWC_COMPOSITION_QUEUED`（类型 6）在 AOSP 源码中**没有发射点**——`FrameTracer.cpp`、`Layer.cpp`、`SurfaceFlinger.cpp`、`HWComposer.cpp` 均无对应的 `traceTimestamp/traceFence` 调用。该 proto 值是给 OEM HWC HAL 使用的占位符，Pixel/Samsung 等闭源实现可能自行发射。如果在 trace 中看到 `HWC_COMPOSITION_QUEUED`，来源是 OEM 扩展而非 AOSP。详见 13.17 §1.8 的校正分析。

## Perfetto SQL 实战：buffer 阶段耗时分析

FrameTracer 数据存储在 `android.surfaceflinger.frame` track 中。下面是四个递进的诊断查询。

### 查询 1：查看 trace 中有哪些 layer 的 buffer 事件

```sql
-- 快速查看 trace 中有哪些 layer 产生了 FrameTracer 事件
SELECT DISTINCT
  EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.layer_name') AS layer_name,
  COUNT(*) AS event_count
FROM slice
WHERE name = 'graphics_frame_event'
GROUP BY layer_name
ORDER BY event_count DESC;
```

### 查询 2：单帧全阶段耗时分解

```sql
-- 将 FrameTracer 事件展开为每帧每阶段的耗时表
WITH frame_events AS (
  SELECT
    EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.layer_name') AS layer_name,
    EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.frame_number') AS frame_number,
    EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.type') AS event_type,
    ts,
    dur
  FROM slice
  WHERE name = 'graphics_frame_event'
)
SELECT * FROM frame_events
WHERE layer_name = 'com.example.app/com.example.app.MainActivity'
  AND frame_number = 42
ORDER BY ts;
```

结果示例（单帧 7 个事件，时间戳单位 ns）：

```
layer_name         | frame_number | event_type           | ts           | dur
-------------------|--------------|----------------------|--------------|-----
com.example...     | 42           | DEQUEUE (1)          | 100034000000 | 0
com.example...     | 42           | QUEUE (2)            | 100048000000 | 0
com.example...     | 42           | ACQUIRE_FENCE (4)    | 100050200000 | 5600000
com.example...     | 42           | LATCH (5)            | 100050200000 | 0
com.example...     | 42           | FALLBACK_COMPOSITION | 100053800000 | 0
com.example...     | 42           | PRESENT_FENCE (8)    | 100066600000 | 0
```

这一帧的瓶颈在读这张表时一目了然：
- App 绘制（DEQUEUE → QUEUE）：14ms
- GPU 渲染（QUEUE → ACQUIRE_FENCE signal）：2.2ms + 5.6ms fence wait
- GPU 合成（LATCH → FALLBACK_COMPOSITION）：3.6ms
- 上屏（FALLBACK_COMPOSITION → PRESENT_FENCE）：12.8ms（含 vsync 等待）

### 查询 3：批量计算每帧总延迟和阶段占比

```sql
-- 按帧聚合，计算 DEQUEUE 到 PRESENT_FENCE 的端到端延迟
-- 以及各阶段耗时占比
WITH events_pivot AS (
  SELECT
    layer_name,
    frame_number,
    MAX(CASE WHEN event_type = 1 THEN ts END) AS ts_dequeue,
    MAX(CASE WHEN event_type = 2 THEN ts END) AS ts_queue,
    MAX(CASE WHEN event_type = 4 THEN ts END) AS ts_acquire,
    MAX(CASE WHEN event_type = 5 THEN ts END) AS ts_latch,
    MAX(CASE WHEN event_type = 7 THEN ts END) AS ts_fallback,
    MAX(CASE WHEN event_type = 8 THEN ts END) AS ts_present
  FROM (
    SELECT
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.layer_name') AS layer_name,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.frame_number') AS frame_number,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.type') AS event_type,
      ts
    FROM slice
    WHERE name = 'graphics_frame_event'
  )
  GROUP BY layer_name, frame_number
)
SELECT
  layer_name,
  frame_number,
  (ts_present - ts_dequeue) / 1e6 AS total_ms,
  (ts_queue - ts_dequeue) / 1e6 AS app_draw_ms,
  (ts_acquire - ts_queue) / 1e6 AS gpu_render_ms,
  (ts_latch - ts_acquire) / 1e6 AS sf_latch_ms,
  COALESCE((ts_fallback - ts_latch) / 1e6, 0) AS gpu_compose_ms,
  (ts_present - COALESCE(ts_fallback, ts_latch)) / 1e6 AS present_ms
FROM events_pivot
WHERE ts_present IS NOT NULL AND ts_dequeue IS NOT NULL
ORDER BY total_ms DESC
LIMIT 20;
```

### 查询 4：识别频繁 GPU 合成的 layer

```sql
-- 统计每个 layer 的 GPU 合成占比
-- FALLBACK_COMPOSITION 出现 = HWC 无法合成该 layer
WITH composition_stats AS (
  SELECT
    layer_name,
    COUNT(DISTINCT CASE WHEN event_type = 7 THEN frame_number END) AS gpu_compose_frames,
    COUNT(DISTINCT CASE WHEN event_type = 8 THEN frame_number END) AS total_presented_frames
  FROM (
    SELECT
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_name.layer_name') AS layer_name,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.frame_number') AS frame_number,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.type') AS event_type
    FROM slice
    WHERE name = 'graphics_frame_event'
  )
  GROUP BY layer_name
)
SELECT
  layer_name,
  gpu_compose_frames,
  total_presented_frames,
  ROUND(100.0 * gpu_compose_frames / NULLIF(total_presented_frames, 0), 1) AS gpu_compose_pct
FROM composition_stats
WHERE total_presented_frames > 0
ORDER BY gpu_compose_pct DESC;
```

`gpu_compose_pct` 高意味着大量帧走了 GPU 合成而非 HWC overlay。常见原因：layer 数量超过 HWC overlay plane 上限、layer 带有复杂变换（缩放/旋转/半透明叠加）、HWC 不支持的像素格式。

## GPU Stall 三种典型模式

用 FrameTracer 数据能区分三种性能瓶颈：

**模式一：ACQUIRE_FENCE 等待过长（GPU 渲染慢）**

QUEUE 到 ACQUIRE_FENCE 的间隔包含 buffer 跨进程传递 + acquire fence signal 等待。fence signal 时间取决于 GPU 完成渲染的时刻。如果这个间隔 > 1 帧（16.6ms @ 60Hz / 8.3ms @ 120Hz），说明 GPU 渲染本身是瓶颈。

```sql
-- 找出 GPU 渲染耗时超过 1 帧周期的帧
SELECT
  layer_name,
  frame_number,
  (ts_acquire - ts_queue) / 1e6 AS gpu_wait_ms
FROM (
  SELECT
    EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.layer_name') AS layer_name,
    EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.frame_number') AS frame_number,
    EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.type') AS event_type,
    ts
  FROM slice WHERE name = 'graphics_frame_event'
)
PIVOT(
  MAX(ts) FOR event_type IN (2 AS ts_queue, 4 AS ts_acquire)
)
WHERE (ts_acquire - ts_queue) / 1e6 > 16.6  -- 超过 60Hz 单帧
ORDER BY gpu_wait_ms DESC;
```

**模式二：FALLBACK_COMPOSITION 频繁触发（HWC 合成能力不足）**

`FALLBACK_COMPOSITION` 表示 HWC 决策该 layer 走 GPU 合成（`requiresClientComposition() == true`）。频繁出现意味着 HWC overlay 处于不健康状态。

判定函数（`OutputLayer.cpp:1137-1140`，android-17.0.0_r1）：

```cpp
bool OutputLayer::requiresClientComposition() const {
    const auto& state = getState();
    return !state.hwc || state.hwc->hwcCompositionType == Composition::CLIENT;
}
```

触发条件有两个：`state.hwc == nullptr`（layer 没有 HWC 关联）或 `hwcCompositionType == Composition::CLIENT`（HWC 主动决策回退到 GPU）。其余 6 种 composition type（DEVICE / SOLID_COLOR / CURSOR / SIDEBAND / DISPLAY_DECORATION / REFRESH_RATE_INDICATOR）走 HWC 路径。

**模式三：LATCH 到 PRESENT_FENCE 间隔异常（合成 + 上屏延迟）**

这个间隔包含 HWC/GPU 合成执行 + 显示控制器刷新等待。如果 HWC 合成正常但此间隔过长，问题可能在显示控制器端（如 vsync 等待过长、刷新率切换中）。

## 版本边界与数据可用性

| Android 版本 | FrameTracer 状态 | 可用事件 | 注意事项 |
|-------------|-----------------|---------|---------|
| 10 (API 29) 及以下 | 不存在 | 无 | 只能用 `ATRACE_TAG_GRAPHICS` atrace 手工对齐时间戳 |
| 11 (API 30) | 引入 | 7 种（核心 6 种 + RELEASE_FENCE） | 无 FrameTimeline 配套，诊断能力有限 |
| 12 (API 31) | 稳定 | 13 种 proto 定义，6 种实际发射 | FrameTimeline 同步引入，可联合分析 |
| 13-14 (API 33-34) | 默认启用 | 同上 | `gfxinfo framestats` 也开始输出对应数据 |
| 15 (API 35) | 稳定 | 同上 + 部分 OEM 扩展 | Pixel 设备可能额外发射 `HWC_COMPOSITION_QUEUED` |
| 16-17 (API 36-37) | 稳定 | 同上，`getCurrentBufferId()` → `getLatchedBufferId()` API 一致性改动 | buffer 标识获取方式变更，不影响事件类型 |

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/]

跨版本诊断建议：Android 11 以下无法使用 FrameTracer，需要用 `systrace` 抓 `gfx` + `view` category，手工对齐 `RenderThread` 的 `eglSwapBuffers` 时间戳与 SF 的 `composite` 时间戳。Android 12+ 可以直接在 Perfetto UI 中用 `android.surfaceflinger.frame` track 可视化查看。

## FrameTracer + FrameTimeline 联合诊断

FrameTracer 的 buffer 阶段数据 + FrameTimeline 的 jank 分类数据，组合起来才能回答「这帧为什么 jank」和「jank 卡在哪一步」两个层面的问题。

关联键：FrameTracer 的 `frame_number` + `layer_name` ↔ FrameTimeline 的 `frame_number` + layer 信息。

```sql
-- 联合查询：找出被 FrameTimeline 标记为 jank 的帧，
-- 并从 FrameTracer 数据定位延迟阶段
WITH jank_frames AS (
  SELECT
    layer_name,
    frame_number,
    jank_tag,
    prediction_type
  FROM android.frames
  WHERE jank_tag IS NOT NULL AND jank_tag != 'None'
),
frame_stages AS (
  SELECT
    layer_name,
    frame_number,
    (ts_present - ts_dequeue) / 1e6 AS total_ms,
    (ts_queue - ts_dequeue) / 1e6 AS app_draw_ms,
    (ts_acquire - ts_queue) / 1e6 AS gpu_render_ms,
    COALESCE((ts_fallback - ts_latch) / 1e6, 0) AS gpu_compose_ms
  FROM (
    SELECT
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.layer_name') AS layer_name,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.frame_number') AS frame_number,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.type') AS event_type,
      ts
    FROM slice WHERE name = 'graphics_frame_event'
  )
  PIVOT(
    MAX(ts) FOR event_type IN (
      1 AS ts_dequeue, 2 AS ts_queue, 4 AS ts_acquire,
      5 AS ts_latch, 7 AS ts_fallback, 8 AS ts_present
    )
  )
)
SELECT
  j.layer_name,
  j.frame_number,
  j.jank_tag,
  f.total_ms,
  f.app_draw_ms,
  f.gpu_render_ms,
  f.gpu_compose_ms,
  CASE
    WHEN f.app_draw_ms > 16.6 THEN 'App draw slow'
    WHEN f.gpu_render_ms > 16.6 THEN 'GPU render slow'
    WHEN f.gpu_compose_ms > 8 THEN 'GPU compose heavy'
    ELSE 'SF scheduling / HWC delay'
  END AS likely_bottleneck
FROM jank_frames j
JOIN frame_stages f USING (layer_name, frame_number)
ORDER BY f.total_ms DESC
LIMIT 30;
```

`likely_bottleneck` 列给出的是基于阈值的初步判断，不是精确归因。实际分析还需结合线程 slice 数据（App 主线程、RenderThread、SF 主线程）确认。但这一步已经把 jank 帧从几十上百帧缩小到了「App 侧问题还是 SF/GPU 侧问题」的二分判断，后续下钻方向就明确了。

## 扩展

### FrameTracer 与 GPU 内存 counter 的联合观测

FrameTracer 记录 buffer 生命周期，结合 `gpu_memory` counter track 可以观察 GPU 内存随帧的变化趋势。当 App 频繁 allocate/free 大尺寸 GraphicBuffer（如相机预览、视频解码、大图加载）时，GPU 内存曲线会出现阶梯式波动。

观测方法：在 Perfetto UI 中同时勾选 `android.surfaceflinger.frame`（slice track）和 `gpu_memory`（counter track），按时间轴对齐。SQL 侧可以按 frame_number 分组，关联 buffer 生命周期内的 GPU 内存变化：

```sql
-- 每帧期间 GPU 内存峰值与均值
WITH frame_windows AS (
  SELECT
    layer_name,
    frame_number,
    MIN(ts) AS frame_start,
    MAX(ts) AS frame_end
  FROM (
    SELECT
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.layer_name') AS layer_name,
      EXTRACT_ARG(arg_set_id, 'graphics_frame_event.buffer_event.frame_number') AS frame_number,
      ts
    FROM slice WHERE name = 'graphics_frame_event'
  )
  GROUP BY layer_name, frame_number
)
SELECT
  f.layer_name,
  f.frame_number,
  MAX(c.value) / 1e6 AS peak_gpu_mb,
  AVG(c.value) / 1e6 AS avg_gpu_mb
FROM frame_windows f
JOIN counter c
  ON c.ts BETWEEN f.frame_start AND f.frame_end
JOIN counter_track t ON c.track_id = t.id
WHERE t.name LIKE '%gpu_memory%'
GROUP BY f.layer_name, f.frame_number
ORDER BY peak_gpu_mb DESC
LIMIT 20;
```

[待验证: `gpu_memory` counter track 名称在不同设备/版本上可能不同，需对照实际 trace 确认]

### FrameTracer 在游戏场景的限制

游戏通常使用 `SurfaceView` 或 ANativeWindow 直出，buffer 流转路径与普通 View 体系不同：

- **事件链更短**：缺少 View 测量/布局/绘制的对应 slice，DEQUEUE → QUEUE 的间隔直接对应游戏引擎的帧渲染耗时（Unity/Godot/自定义引擎），中间没有 `RenderThread` 参与的痕迹。
- **HWC 事件可能缺失**：部分游戏使用 `SECURE` 或 `PROTECTED` buffer，HWC 行为与普通 buffer 不同，`PRESENT_FENCE` 可能延迟或缺失。
- **多 buffer 深度**：游戏常使用 triple buffering（`minUndequeuedBuffers = 2`），buffer 流水线深度更大，DEQUEUE 到 PRESENT_FENCE 的端到端延迟天然比双 buffer 长，分析时需调整预期基线。
- **帧率不匹配**：游戏跑 30/60/90/120fps 时，FrameTimeline 的 vsync 周期预期不同。FrameTracer 的 `frame_number` 是连续的，但并非每个 frame_number 都对应一次上屏——游戏丢帧时 buffer 被 cancel 或 reuse。

对游戏场景，建议同时开启 `gfx` + `gpu` atrace category 配合 FrameTracer 分析，`gpu` category 包含 GPU 频率和 GPU queue 深度信息，能补齐 FrameTracer 在 GPU 侧的观测盲区。


<!-- AIW-源码调研-2026-06-28 -->
## FrameTimeline 数据结构详解（android-17.0.0_r1 补充）

### FrameTimelineEvent proto 与 JankType bitmask

**源码位置**：`external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto`（android-17.0.0_r1）

FrameTimeline 的核心是 `FrameTimelineEvent` 消息，按 `oneof event` 区分五类子消息：`ExpectedDisplayFrameStart` / `ActualDisplayFrameStart` / `ExpectedSurfaceFrameStart` / `ActualSurfaceFrameStart` / `FrameEnd`。每条事件通过 `cookie`（int64）关联 start / end，每帧内部由若干 SurfaceFrame 和一个 DisplayFrame 组成（多对一关系：`One DisplayFrame can map to N SurfaceFrame(s)`，通过 `display_frame_token` 字段关联）。

`ActualSurfaceFrameStart` 是诊断 jank 的核心字段（节选）：

| 字段 | 类型 | 含义 |
|------|------|------|
| `present_type` | enum | 帧实际呈现时机：ON_TIME=1 / LATE=2 / EARLY=3 / DROPPED=4 / UNKNOWN=5 |
| `on_time_finish` | bool | 是否在预测 deadline 内完成 |
| `gpu_composition` | bool | **GPU 合成 vs HWC 合成的边界标志** |
| `jank_type` | int32 | **bitmask，可同时标记多个 jank 原因** |
| `prediction_type` | enum | PREDICTION_VALID=1 / EXPIRED=2 / UNKNOWN=3 |
| `is_buffer` | bool | 是否为 buffer 路径（vs bufferless） |
| `jank_severity_type` | enum | SEVERITY_UNKNOWN=0 / NONE=1 / PARTIAL=2 / FULL=3 |
| `present_delay_millis` | float | 上屏相对预测时刻的延迟（ms） |
| `vsync_resynced_jitter_millis` | float | vsync 重新同步后的抖动（ms） |
| `jank_severity_score` | float | 综合严重度分数（连续值） |

**Android 17 新增的 JankType bitmask 项**：

| bit 值 | 名称 | 引入版本 |
|--------|------|----------|
| 8192 | `JANK_DISPLAY_NOT_ON` | **Android 17 新增** |
| 16384 | `JANK_DISPLAY_MODE_CHANGE_IN_PROGRESS` | **Android 17 新增** |
| 32768 | `JANK_DISPLAY_POWER_MODE_CHANGE_IN_PROGRESS` | **Android 17 新增** |

判断依据：`frame_timeline_event.proto` 在 android-12.0.0_r1 起即存在，bit 0-12 共 13 个 JankType；Android 14 引入 `JANK_APP_RESYNCED_JITTER`（bit 12）；Android 17 新增 bit 13-15 三个 display 相关 jank 原因，反映 17 对 display power / mode 切换的额外关注。

完整 bitmask 表（android-17.0.0_r1，按 bit 位置排序）：

```
bit 0: JANK_UNSPECIFIED = 0
bit 1: JANK_NONE = 1
bit 2: JANK_SF_SCHEDULING = 2
bit 3: JANK_PREDICTION_ERROR = 4
bit 4: JANK_DISPLAY_HAL = 8
bit 5: JANK_SF_CPU_DEADLINE_MISSED = 16
bit 6: JANK_SF_GPU_DEADLINE_MISSED = 32
bit 7: JANK_APP_DEADLINE_MISSED = 64
bit 8: JANK_BUFFER_STUFFING = 128
bit 9: JANK_UNKNOWN = 256
bit 10: JANK_SF_STUFFING = 512
bit 11: JANK_DROPPED = 1024
bit 12: JANK_NON_ANIMATING = 2048
bit 13: JANK_APP_RESYNCED_JITTER = 4096   (Android 14+)
bit 14: JANK_DISPLAY_NOT_ON = 8192          (Android 17+)
bit 15: JANK_DISPLAY_MODE_CHANGE_IN_PROGRESS = 16384  (Android 17+)
bit 16: JANK_DISPLAY_POWER_MODE_CHANGE_IN_PROGRESS = 32768  (Android 17+)
```

### GPU/HWC 合成边界在 FrameTimeline 中的判定路径

FrameTimeline 的 `gpu_composition` 字段与 FrameTracer 的 `FALLBACK_COMPOSITION` 事件由同一段代码设置：

**源码位置**：`frameworks/native/services/surfaceflinger/Layer.cpp:1451-1462`（android-17.0.0_r1）

```cpp
const auto outputLayer = findOutputLayerForDisplay(display);
if (outputLayer && outputLayer->requiresClientComposition()) {
    nsecs_t clientCompositionTimestamp = outputLayer->getState().clientCompositionTimestamp;
    mFlinger->mFrameTracer->traceTimestamp(layerId, getLatchedBufferId(), mCurrentFrameNumber,
                                           clientCompositionTimestamp,
                                           FrameTracer::FrameEvent::FALLBACK_COMPOSITION);
    if (mDrawingState.bufferSurfaceFrameTX) {
        mDrawingState.bufferSurfaceFrameTX->setGpuComposition();   // ← 与 FrameTimeline 共享标志
    }
    ...
}
```

**数据通路**：`OutputLayer::requiresClientComposition()` → 返回 true → `setGpuComposition()` 写 SurfaceFrame → FrameTimeline 上报时读取该标志填充 `ActualSurfaceFrameStart.gpu_composition` 字段。

判断 GPU stall 的两步走法：

1. **过滤**：在 `actual_frame_timeline_slice` 中筛 `gpu_composition = true AND present_type = PRESENT_LATE OR PRESENT_DROPPED`，拿到所有 GPU 合成路径下的 jank 帧；
2. **关联**：用 `frame_number` + `display_frame_token` 关联到 `android.surfaceflinger.frame` 的 `FALLBACK_COMPOSITION` 事件，读 `clientCompositionTimestamp` 与 `ts_present` 的差值，量化 GPU 合成耗时。

### PRESENT_FENCE 双发射路径

**源码位置**：`frameworks/native/services/surfaceflinger/Layer.cpp:1473-1499`（android-17.0.0_r1）

```cpp
if (presentFence->isValid()) {
    mFlinger->mFrameTracer->traceFence(layerId, getLatchedBufferId(), mCurrentFrameNumber,
                                       presentFence,
                                       FrameTracer::FrameEvent::PRESENT_FENCE);   // 现代 HWC 路径
} else if (... && mFlinger->getHwComposer().isConnected(*displayId)) {
    // HWC doesn't support present fences, so use the present timestamp instead.
    const nsecs_t presentTimestamp = mFlinger->getHwComposer().getPresentTimestamp(*displayId);
    const nsecs_t vsyncPeriod = ...;
    const nsecs_t actualPresentTime = now - ((now - presentTimestamp) % vsyncPeriod);
    mFlinger->mFrameTracer->traceTimestamp(layerId, getLatchedBufferId(),
                                           mCurrentFrameNumber, actualPresentTime,
                                           FrameTracer::FrameEvent::PRESENT_FENCE);  // 老硬件路径
}
```

**判断**：Pixel / 三星等现代设备的 trace 中 PRESENT_FENCE 几乎都来自 fence 路径；车机 / 旧 IoT 设备可能命中 timestamp 路径，分析时需要区分。

### AOSP 不发射的两个事件（边界确认）

通过 grep 验证（android-17.0.0_r1）：

| 事件 | proto 值 | AOSP 发射点 |
|------|----------|-------------|
| `HWC_COMPOSITION_QUEUED` | 6 | **0 个**（OEM HWC HAL 扩展占位） |
| `RELEASE_FENCE` | 9 | **0 个**（proto 保留，无 Layer.cpp / FrameTracer.cpp 调用） |

结论：trace 中看到 `HWC_COMPOSITION_QUEUED` 一定来自 OEM HAL；`RELEASE_FENCE` 在 AOSP 设备上不会出现，分析"上屏→buffer 回收"延迟只能依赖其他信号（如 buffer 复用率、BufferQueue counter track）。

### FrameTracer fence 处理：60s 过期机制

**源码位置**：`frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.h:72`

```cpp
static constexpr nsecs_t kFenceSignallingDeadline = 60'000'000'000; // 60 seconds
```

`FrameTracer::tracePendingFencesLocked()` 把未 signal 的 fence 挂到 `pendingFences[bufferID]` 列表，等下次同 buffer 的 trace 调用时检查；若 60s 内仍未 signal 则丢弃，避免旧 trace 的 fence 在新 trace 中误触发事件。

### Perfetto 标准表名

`actual_frame_timeline_slice` 和 `expected_frame_timeline_slice` 是 Perfetto UI 默认加载的标准化表，字段含义：

| 标准表字段 | 来源 proto 字段 |
|-----------|-----------------|
| `ts, dur` | 事件时间戳与持续时间 |
| `surface_frame_token` | `ActualSurfaceFrameStart.token`（App 侧工作 token） |
| `display_frame_token` | `ActualSurfaceFrameStart.display_frame_token`（SF 侧工作 token） |
| `process.name` | 通过 `upid` JOIN `process` 表获得 |

> 来源：[Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)（确认 GPU Composition 字段语义、Android 12+ 要求、数据源名 `android.surfaceflinger.frametimeline`）

### 与 HWC_COMPOSITION_QUEUED 校正报告的关系

本文档与 2026-06-27 的 `2026-06-27-android17-hwc-composition-queue-event-source.md` 是同根但不同侧重：本次校正已覆盖 HWC_COMPOSITION_QUEUED 的"AOSP 无发射点"事实，本节补充 FrameTimeline 数据结构与 Android 17 的 jank 原因新增项（`JANK_DISPLAY_NOT_ON` / `JANK_DISPLAY_MODE_CHANGE_IN_PROGRESS` / `JANK_DISPLAY_POWER_MODE_CHANGE_IN_PROGRESS`），二者不冲突。

## 延伸阅读

### Android 17 HWC Composition Queue 事件追踪与 GPU 渲染性能边界判定
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-27-android17-hwc-composition-queue-event-source.md
- 类型：DeepResearch 调研结果
- 摘要：基于 4 个 AOSP tag 的 proto diff 证明 HWC_COMPOSITION_QUEUED 自 Android 12 即存在且无 emit 站点，FALLBACK_COMPOSITION 才是真实 GPU 合成事件。完整记录 presentOrValidate 快速/慢速路径状态机、traceFence pending 队列机制，以及 GPU/HWC 合成边界的 OutputLayer 判定逻辑。
- 注入时间：2026-06-28
- 价值：修正 HWC_COMPOSITION_QUEUED 为 Android 17 新增的错误认知，提供 FrameTracer 事件 emit 站点的完整源码排查，对 Perfetto GPU 分析至关重要
