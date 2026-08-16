---
title: "Frame Timeline API 33 Perfetto 深度分析：Expected vs Actual Timeline"
chapter: "13.19"
status: finalized
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Perfetto, FrameTimeline, Jank, Choreographer, 渲染性能分析]
related_chapters: ["2.4", "2.32", "13.7", "13.9", "13.13", "13.18"]
last_verified: "2026-08-13"
last_verified_against: "AOSP android-17.0.0_r1 / Perfetto v57.2 / Android Developers API 33 references / official FrameTimeline docs"
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

# 13.19 Frame Timeline API 33 Perfetto 深度分析：Expected vs Actual Timeline

FrameTimeline 使用一组可关联的帧 ID 记录调度预测、应用出帧、SurfaceFlinger 合成和显示提交，适合回答三个问题：哪一帧偏离了预测，偏差发生在应用侧还是显示合成侧，下一步应查看哪条线程或 buffer 路径。

本文核对的平台源码版本是 Android 17 / API 37 / `android-17.0.0_r1`。FrameTimeline trace 数据源从 Android 12 / API 31 起可用；标题中的 API 33 指 `Choreographer.VsyncCallback`、`FrameData` 与 `FrameTimeline` 公共 API 的引入版本。涉及 DMA-BUF（跨驱动共享的 buffer）、`sync_file`（把 fence 暴露为文件描述符的内核接口）或 `dma-fence`（内核中的同步对象）时，对应的内核版本是 `android17-6.18-2026-06_r6`。SQL 已按 Perfetto v57.2 的内置表验证。

FrameTimeline 的内部对象与分类流程见 §2.32，buffer 阶段事件见 §13.18，CUJ 聚合见 §13.13。这里集中处理 Expected/Actual 语义、API 33 回调、采集配置和可执行 SQL。

## 两类帧

FrameTimeline 同时记录应用的 SurfaceFrame 和 SurfaceFlinger（下文简称 SF）的 DisplayFrame。SurfaceFrame 表示某个 layer 提交的一帧，DisplayFrame 表示 SF 把一个或多个 SurfaceFrame 合成后送去显示的一帧：

| 对象 | `surface_frame_token` | `display_frame_token` | 代表什么 |
| --- | ---: | ---: | --- |
| 应用 SurfaceFrame | 非空 | 非空 | 某进程向一个 layer 提交的一帧 |
| SF DisplayFrame | `NULL` | 非空 | SurfaceFlinger 组合后提交给某个 display 的一帧 |

token 在这里是用于关联记录的帧 ID。一个 DisplayFrame 可以组合来自多个进程、多个 layer 的 SurfaceFrame，因此多条应用行可以共享同一个 `display_frame_token`。它适合从应用帧追到显示帧，不能直接用于连接应用 Expected 与应用 Actual；后一种连接要使用同一 `upid` 下的 `surface_frame_token`。`upid` 是 Trace Processor 为进程分配的内部唯一 ID，可避免直接使用可能被系统复用的 PID。

DisplayFrame 的 protobuf 记录只有自己的 display token，没有 surface token。Perfetto v57.2 因此把 DisplayFrame 行的 `surface_frame_token` 保留为 `NULL`，也就是 SQL 中的空值；部分文档示例仍把这一格显示为 0。查询应按字段是否为空区分两类帧，不能依赖数值 0。

标准 HWUI（Android 硬件加速 UI 渲染器）App Window 的 SurfaceFrame 数据最完整。SurfaceView 由独立 Producer（生成并提交 buffer 的一方）和独立 Surface 出帧，Perfetto 官方文档仍将其列为 FrameTimeline 不支持的路径。Camera、Video、游戏 Surface、WebView overlay（独立叠加层）和跨进程嵌入也要先确认真正的 Producer 与 layer，不能拿宿主窗口的 token 代替独立 Surface 的帧 ID。

## Expected 与 Actual 各自量什么

每个有可见帧的应用进程会得到 Expected Timeline 和 Actual Timeline，SurfaceFlinger 也有自己的一对 track。

### 应用侧

- Expected slice 的起点是 Choreographer 回调被计划运行的时刻；slice 表示系统为应用准备该帧安排的时间窗口。
- Actual slice 的起点是 `Choreographer#doFrame` 或 `AChoreographer_vsyncCallback` 开始运行的时刻。
- Actual slice 的终点取 GPU 完成时间与 post time 的较晚者；post time 表示应用把这一帧提交给 SurfaceFlinger 的时刻。

`Choreographer#doFrame` 只覆盖主线程回调区间。Actual SurfaceFrame 还考虑异步 GPU 工作和提交时刻，所以较短的 `doFrame` 不能证明该帧在 ready deadline（必须准备完成的时间）之前就绪。Android 17 的 trace 名为 `Choreographer#doFrame <vsyncId>`，例如 `Choreographer#doFrame 12345`；方括号形式不符合该 tag 的源码。

### SurfaceFlinger 侧

SF Expected slice 表示当前 DisplayFrame 的预测工作窗口。SF Actual slice 从 SF 主线程开始处理该帧，覆盖 Composer 与 Display HAL（显示硬件抽象层）相关路径，终点是 Android 显示栈报告 on-screen update 的时刻。

这个 present 时间可以用于分析 Android 显示管线，但不能证明面板像素已经完成扫描和光学响应。测量从触摸到屏幕发光的端到端延迟，仍要同时记录输入时间戳、显示链路，并使用外部光学设备。

### 不能把 Expected 宽度当刷新周期

Expected slice 的宽度来自该回调的调度预算，即系统预计 App 或 SF 完成工作的可用时间。官方示例中应用 Expected slice 约 20.5 ms，SF Expected slice 约 10.5 ms；它们都不能用“90 Hz 就应固定为 11.1 ms”来校验。

Android 17 的 `VSyncDispatchTimerQueueEntry::schedule()` 以预测的目标 VSYNC 为参考时间，并使用 `workDuration`、`readyDuration` 计算 wakeup（唤醒）与 ready（应当就绪）时刻：

```text
nextReadyTime  = nextVsyncTime - readyDuration
nextWakeupTime = nextReadyTime - workDuration
```

公式先从目标 VSYNC 减去 `readyDuration` 得到应当就绪的时间，再向前减去 `workDuration` 得到唤醒时间。固定的“VSYNC-app 提前 1～3 ms、再叠加 SF 预算”模型无法描述动态刷新率、不同工作预算、VSync 重同步或 Buffer Stuffing（队列持续积压），不应用来反推 Expected slice。

## 三个字段要一起看

Actual slice 至少包含以下三组相互独立的信息：

| 字段 | 问题 | 常见值 |
| --- | --- | --- |
| `present_type` | 该帧何时 present | `Early Present`、`On-time Present`、`Late Present`、`Dropped Frame` |
| `on_time_finish` | 生产该帧的工作是否按时结束 | 0 或 1 |
| `jank_type` / `jank_tag` | FrameTimeline 检测到的原因，以及原因归在当前进程还是其他进程 | `App Deadline Missed`、`Buffer Stuffing`、`Self Jank`、`Other Jank` 等 |

时间轴上的偏差适合发现候选帧，分类字段用于说明系统怎样判断这帧。`on_time_finish = 0` 只表示工作超出 ready deadline，不能作为全部 jank 的过滤条件。Buffer Stuffing 常见 `on_time_finish = 1` 和 `Late Present` 同时出现：应用生产工作虽然按时结束，队列中积压的 buffer 仍会增加输入延迟。

Perfetto UI 用颜色表示状态，以及原因归在当前进程还是其他进程：

| 颜色 | UI 含义 | 判读 |
| --- | --- | --- |
| 绿色 | good frame | 没有检测到 jank |
| 浅绿色 | high-latency state | 帧节奏可能平滑，但帧持续晚 present，输入延迟增加 |
| 红色 | self jank | 当前 slice 所属进程被判为原因 |
| 黄色 | other jank | 只用于应用 track；当前应用帧受 SF/display 侧问题影响 |
| 蓝色 | dropped frame | 应用状态更新未及时交给 RenderThread，或 SF 选择较新的显示帧 |

Android 17 `SurfaceFrame::isSelfJanky()` 将 `AppDeadlineMissed`、`AppResyncedJitter` 和 `Unknown` 视为应用自身 jank。SF scheduling、SF CPU/GPU deadline、Display HAL 和 Prediction Error 会形成系统侧原因。黄色只说明 FrameTimeline 把当前帧归到系统侧；复杂 layer、GPU 负载或 composition 变化仍可能由应用行为触发，排障时还要检查 flow（跨 track 的事件关联线）、layer 和系统负载。

`jank_type` 是 bitmask（用不同二进制位同时表示多个原因的整数）转换成的字符串，一帧可以同时带多个原因。Perfetto v57.2 还提供 `jank_tag`，把结果归并为 `Self Jank`、`Other Jank`、`Buffer Stuffing`、`SurfaceFlinger Stuffing`、`Dropped Frame`、`Non-perceivable Jank` 等预计算类别。做统计时应优先使用这个分类，避免靠字符串包含关系自行分组。

Android 17 的 Actual SurfaceFrame protobuf 记录还包含 `present_delay_millis`（present 延迟）、`vsync_resynced_jitter_millis`（VSync 重同步抖动）、`jank_severity_type` 与 `jank_severity_score`；DisplayFrame 没有 VSync 重同步抖动字段。Perfetto v57.2 在内置表中把 severity score 命名为 `jank_score`。这些值可以描述偏差幅度和严重程度，但不能脱离 `jank_type`、present 状态与采集版本，另行定义一套 jank 判定。protobuf 中带 `experimental` 的 jank、present 与 debug 字段明确标注为调试数据，不应进入正式 jank 指标。

## API 33 的 `FrameData` 用法

API 33 新增 `Choreographer.postVsyncCallback(VsyncCallback)`。这个一次性回调接收 `FrameData`，公开方法如下：

| 类型 | 方法 | 返回内容 |
| --- | --- | --- |
| `FrameData` | `getFrameTimeNanos()` | 当前回调使用的 frame time |
| `FrameData` | `getFrameTimelines()` | 按时间排序的候选 `FrameTimeline[]` |
| `FrameData` | `getPreferredFrameTimeline()` | 平台当前选中的候选 timeline |
| `FrameTimeline` | `getVsyncId()` | 与 HWUI、SurfaceFlinger trace 关联的 VSYNC id |
| `FrameTimeline` | `getExpectedPresentationTimeNanos()` | 预测 present 时间，使用 `System.nanoTime()` 时基 |
| `FrameTimeline` | `getDeadlineNanos()` | 该候选帧应当 ready 的时间，使用 `System.nanoTime()` 时基 |

`FrameData.getLastFrameTimeNanos()`、`FrameData.getIntervalNanos()`、`Choreographer.getFrameData()` 都不属于公共 API。deadline 也不等同于“主线程 CPU 工作结束时间”；应用的 buffer 与 GPU 工作要在这个时刻前满足后续 Consumer 的读取条件。

下面的 Java 片段演示如何在 API 33+ 复制一次回调中的标量值。

```java
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
    Choreographer choreographer = Choreographer.getInstance();
    choreographer.postVsyncCallback(frameData -> {
        Choreographer.FrameTimeline preferred =
                frameData.getPreferredFrameTimeline();

        long frameTimeNanos = frameData.getFrameTimeNanos();
        long vsyncId = preferred.getVsyncId();
        long deadlineNanos = preferred.getDeadlineNanos();
        long expectedPresentNanos =
                preferred.getExpectedPresentationTimeNanos();

        recordFramePlan(
                frameTimeNanos,
                vsyncId,
                deadlineNanos,
                expectedPresentNanos);
    });
}
```

这段代码要在带 `Looper`（Android 线程消息循环）的线程调用，回调会在 `Choreographer` 绑定的同一线程执行。`FrameData` 与其中的 `FrameTimeline` 只在 `onVsync` 执行期间有效；Android 17 源码在回调外访问时会抛出 `IllegalStateException`。需要异步记录时，只复制 `long` 等标量值。`postVsyncCallback()` 执行一次后会移除，连续观测要由调用方再次注册，并控制日志写入和对象分配成本。

Android 17 内部的 `DisplayEventReceiver.VsyncEventData` 为候选数组预留 7 个槽位，但 `FrameData.update()` 会按事件携带的 `frameTimelinesLength` 重新分配数组。公共 API 没有承诺固定返回 7 项，业务代码应读取实际数组长度，并使用平台标出的 preferred 项。

这些 API 提供的是本次回调可选的调度计划，不能替代 FrameTimeline trace。应用进程无法只凭 `FrameData` 得到最终 present、SF 分类、其他 layer 或 Display HAL 结果。

## 正确启用数据源

FrameTimeline 是原生 Perfetto 数据源 `android.surfaceflinger.frametimeline`。`gfx`、`view` 属于 atrace category（Android trace 事件分类），可以补充 `Choreographer#doFrame`、`DrawFrame` 和图形 slice，但不会自动打开 FrameTimeline 数据源。

下面的配置片段同时启用 FrameTimeline、FrameTracer、应用图形 slice 和线程调度信息，需合并到已经定义采集时长与 buffer 的完整配置中。

```textproto
data_sources {
  config { name: "android.surfaceflinger.frametimeline" }
}
data_sources {
  config { name: "android.surfaceflinger.frame" }
}
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "view"
      atrace_categories: "gfx"
      atrace_categories: "wm"
      atrace_apps: "com.example.app"
    }
  }
}
```

这段内容不能单独作为采集配置运行。采集时长和 buffer 容量应根据复现窗口、设备内存与实际数据速率设定，不存在适用于所有场景的固定数值。`android.surfaceflinger.frame` 是可选的 buffer 阶段数据源，见 §13.18。定位单个应用时，应把 `atrace_apps` 换成目标包名；使用全局 `*` 会增加 ftrace 数据量。生产问题还要按待验证的原因加入 GPU counter、Binder、memory 或 power 数据，避免无关数据占满 ring buffer（写满后覆盖旧数据的环形缓冲区）。

下面的命令使用文本配置采集并拉回 trace。

```bash
adb push frame_timeline.pbtxt /data/local/tmp/
adb shell perfetto --txt \
  -c /data/local/tmp/frame_timeline.pbtxt \
  -o /data/misc/perfetto-traces/frame_timeline.perfetto-trace
adb pull /data/misc/perfetto-traces/frame_timeline.perfetto-trace
```

命令依次把文本配置推到设备、启动 Perfetto 采集，再把 trace 文件拉回电脑。采集结束后，先在 Trace Processor 中确认两张 FrameTimeline 表有数据。若 UI 缺少应用 Expected/Actual track，依次检查平台是否为 Android 12+、原生数据源是否启用、目标应用在采集区间内是否产生可见帧，以及目标路径是否属于独立 Surface 或未覆盖的 SurfaceView。

## UI 排障顺序

一次可靠的帧级分析可以按下面的顺序进行：

1. 在目标进程下选中红色、黄色、浅绿色或蓝色 Actual slice，记录 `surface_frame_token`、`display_frame_token`、layer、`jank_tag`、`jank_type`、`present_type` 和 `on_time_finish`。
2. 用 `surface_frame_token` 找同进程的 Expected slice，比较计划起点、实际回调起点、ready 窗口和 Actual 终点。
3. 沿 UI flow（跨 track 的关联线）跟到 SurfaceFlinger 的 DisplayFrame。一个显示帧可能连接多条应用 layer，不要把同 token 的所有行当成重复数据。
4. `Self Jank` 时检查同一 VSYNC id 的 `Choreographer#doFrame <id>`、RenderThread `DrawFrame <id>`、CPU scheduling（调度状态）、GPU 与 acquire fence（限制 Consumer 读取时机的同步栅栏）。
5. `Other Jank` 时检查 SF actual track、composition type（合成类型）、RenderEngine、HWC/Display HAL、刷新率和 mode/power change。
6. `Buffer Stuffing` 时检查 Producer 的提交节奏、连续 late present、dequeue 阻塞和 FrameTracer phase（阶段区间）；`on_time_finish = 1` 不能排除这类高延迟状态。

`doFrame` 较长只能说明主线程回调占用明显。`doFrame` 较短而 Actual 较长时，RenderThread、GPU、提交等待或 Producer 与 SF 的交接过程仍可能有问题。要确认原因，还需查询对应线程、GPU、fence 或 BufferQueue 数据。

## Perfetto SQL：按正确身份对齐

`expected_frame_timeline_slice` 与 `actual_frame_timeline_slice` 是 Trace Processor 导入 trace 时直接生成的内置表，查询它们不需要 `INCLUDE PERFETTO MODULE android.frames.timeline`。Perfetto v57.2 的表结构包含 `name`、两个 token、`upid`、`layer_name`、`present_type`、`on_time_finish`、`jank_type` 与 `jank_tag`，没有 `slice_name` 列。

### 查询 1：逐帧比较应用 Expected 与 Actual

下面的查询只选择应用 SurfaceFrame，并用 `upid + surface_frame_token` 连接 Expected 与 Actual。两个字段一起使用，可以避免不同进程恰好出现相同 token 时发生误连。

```sql
WITH app_actual AS (
  SELECT
    a.*,
    p.name AS process_name
  FROM actual_frame_timeline_slice AS a
  LEFT JOIN process AS p USING (upid)
  WHERE a.surface_frame_token IS NOT NULL
),
app_expected AS (
  SELECT
    upid,
    surface_frame_token,
    ts AS expected_ts,
    dur AS expected_dur
  FROM expected_frame_timeline_slice
  WHERE surface_frame_token IS NOT NULL
)
SELECT
  a.process_name,
  a.layer_name,
  a.surface_frame_token,
  a.display_frame_token,
  a.ts / 1e6 AS actual_start_ms,
  a.dur / 1e6 AS actual_dur_ms,
  e.expected_ts / 1e6 AS expected_start_ms,
  e.expected_dur / 1e6 AS expected_dur_ms,
  (a.ts + a.dur - e.expected_ts - e.expected_dur) / 1e6
    AS end_delta_ms,
  a.present_type,
  a.on_time_finish,
  a.jank_tag,
  a.jank_type
FROM app_actual AS a
JOIN app_expected AS e
  USING (upid, surface_frame_token)
WHERE a.process_name = 'com.example.app'
ORDER BY a.ts;
```

`end_delta_ms` 是 Actual 终点减去 Expected 终点得到的时间差，只用于排序和定位，不能单独当作 jank 判定。若同一 token 对应多个 layer，结果会保留多条 Actual 行；每一行都代表一个 layer，不能用 `DISTINCT` 去重后隐藏。

### 查询 2：按原因归属、present 与 ready 状态统计

下面的查询保留 Buffer Stuffing、Dropped Frame 和 non-perceivable 状态，不使用 `on_time_finish = 0` 预先删行。

```sql
SELECT
  a.jank_tag,
  a.jank_type,
  a.present_type,
  a.on_time_finish,
  COUNT(*) AS frame_count,
  AVG(a.dur) / 1e6 AS avg_actual_ms,
  MAX(a.dur) / 1e6 AS max_actual_ms
FROM actual_frame_timeline_slice AS a
LEFT JOIN process AS p USING (upid)
WHERE a.surface_frame_token IS NOT NULL
  AND p.name = 'com.example.app'
GROUP BY
  a.jank_tag,
  a.jank_type,
  a.present_type,
  a.on_time_finish
ORDER BY frame_count DESC;
```

这份聚合能区分“工作超 deadline”“present 晚”“队列积压”和“原因归在其他进程”。`dur` 来自 FrameTimeline 的 Actual slice，不能统一解释为主线程、GPU 或端到端显示耗时。

### 查询 3：把应用帧连接到 SF DisplayFrame

下面的查询用 `display_frame_token` 找到应用 SurfaceFrame 对应的 SF DisplayFrame，并通过 `surface_frame_token IS NULL` 只保留 DisplayFrame 行，防止连接到其他应用 layer。

```sql
WITH app_frame AS (
  SELECT
    a.*,
    p.name AS process_name
  FROM actual_frame_timeline_slice AS a
  LEFT JOIN process AS p USING (upid)
  WHERE a.surface_frame_token IS NOT NULL
    AND p.name = 'com.example.app'
),
display_frame AS (
  SELECT
    a.*
  FROM actual_frame_timeline_slice AS a
  LEFT JOIN process AS p USING (upid)
  WHERE a.surface_frame_token IS NULL
    AND p.name GLOB '*surfaceflinger'
)
SELECT
  app.surface_frame_token,
  app.display_frame_token,
  app.layer_name,
  app.jank_tag AS app_jank_tag,
  app.jank_type AS app_jank_type,
  sf.jank_tag AS sf_jank_tag,
  sf.jank_type AS sf_jank_type,
  sf.present_type AS sf_present_type
FROM app_frame AS app
LEFT JOIN display_frame AS sf
  USING (display_frame_token)
ORDER BY app.ts;
```

一个 SF DisplayFrame 对应多条应用 SurfaceFrame，因此查询结果出现重复的 `display_frame_token` 是正常的多对一关系。`GLOB '*surfaceflinger'` 使用通配符匹配 SF 进程名。UI flow 还保留时间位置与其他 layer，排查单帧时通常比只看表格直观。

## Android 17 新增的分类

Android 17 `frame_timeline_event.proto` 继续用 bitmask 表示原因，并在 Android 16 固定 tag 的基础上加入五项分类：

| bit | Android 17 枚举 | 诊断含义 |
| ---: | --- | --- |
| 2048 | `JANK_NON_ANIMATING` | 非动画内容或无法按动画节奏解释的 present 状态；源码将其放入 non-jank bitmask |
| 4096 | `JANK_APP_RESYNCED_JITTER` | 应用 VSYNC 重同步相关抖动 |
| 8192 | `JANK_DISPLAY_NOT_ON` | display 未处于 on 状态 |
| 16384 | `JANK_DISPLAY_MODE_CHANGE_IN_PROGRESS` | 显示模式切换进行中 |
| 32768 | `JANK_DISPLAY_POWER_MODE_CHANGE_IN_PROGRESS` | 显示电源模式切换进行中 |

后三项 display 状态会影响“用户是否能感知”和原因归属，不能全部算进应用 jank rate（卡顿帧比例）。Perfetto v57.2 已把 bitmask 转换为 `jank_type`、`jank_tag`、`jank_severity_type` 和 `jank_score`；自动化报告应保存原始类型和工具版本，避免把不同 Perfetto 版本生成的字段混进同一比较基线。

Buffer Stuffing、SurfaceFlinger Stuffing、Non Animating 和三项 display 状态在 Android 17 `FrameTimeline.cpp` 中都位于 non-jank bitmask。这些位单独出现时不会增加 `jank_severity_score`，却仍可能描述高延迟、不可感知或显示状态变化。性能报告应分别统计，不能全部并入 `No Jank`，也不能全部算作应用 jank。

## 按出图路径选择主要记录

不同渲染路径使用的 Producer、Surface、layer 和 fence 不同，分析时可按下表选择优先用于定位帧的记录：

| 出图路径 | 优先用于定位帧的记录 | 补充证据 |
| --- | --- | --- |
| 标准 View/Compose App Window | App Window 的 SurfaceFrame token | MainThread、RenderThread、HWUI、GPU、FrameTracer |
| SurfaceView / 游戏独立 Surface | 先找独立 layer；App Timeline 可能缺失 | Producer 线程、BufferQueue、FrameTracer、GPU |
| TextureView | 宿主 App Window token | 外部 SurfaceTexture Producer 与宿主合成时序 |
| Camera / Video Surface | preview/video layer 的 present 节奏 | HAL、codec、acquire fence；fence 来源未必是 GPU |
| Tunneled / sideband video | FrameTimeline 可能无法覆盖逐帧 buffer | HWC、HAL、sideband（视频经专用硬件路径交给显示系统）与显示状态 |
| WebView / Flutter / 跨进程嵌入 | 区分宿主窗口和独立 overlay | 各进程 layer、flow、buffer 与 composition type |
| Software / 离屏渲染 | 只有最终提交到可见 Surface 的帧可能进入 FrameTimeline | CPU raster（CPU 像素绘制）、Bitmap/ImageReader Consumer 与后续上传或提交 |
| Native EGL / Vulkan | 优先定位 ANativeWindow 对应的 layer | 引擎线程、swap/present、GPU queue、BufferQueue 与 fence |
| 多窗口 / 多 display | 每个可见窗口或独立 Surface 分别找 layer | 窗口可见性、目标 display、刷新模式与同一 DisplayFrame 的 layer 集合 |

`queueBuffer` 返回只代表 Producer 已提交 buffer；acquire fence 决定 Consumer（读取 buffer 的一方）何时可以安全读取。present fence 按 display/frame 生成，release fence 按 layer/frame 生成并决定旧 buffer 何时可复用。FrameTimeline 的 present 时间不能替代 release fence，也不能从 token 推导 BufferQueue frame number。

## 不同 Android 版本的能力

| 平台 | 能力 | 分析影响 |
| --- | --- | --- |
| Android 12 / API 31 | FrameTimeline 数据源进入平台 | Expected/Actual track 与两张内置表可用于判断帧是否偏离计划及原因归属 |
| Android 13 / API 33 | 公共 `VsyncCallback`、`FrameData`、`FrameTimeline` | 应用可在回调内读取候选 deadline、expected present 与 VSYNC id |
| Android 14～16 / API 34～36 | 公共模型延续，分类和调度实现继续演进 | 固定设备 build、刷新率和 Perfetto 版本后再比较 |
| Android 17 / API 37 | 本文核对的平台源码与 protobuf 版本 | 使用动态 work/ready budget、Android 17 jank bitmask 与 v57.2 表结构 |

FrameTimeline trace 的最低平台是 Android 12，API 33 只限定应用代码示例。结论范围不包含 Android 17 之后的行为。

## 使用限制

- Expected 是调度预测窗口，不是刷新周期的同义词。
- Actual 应用 slice 覆盖回调起点到 GPU/post 的较晚时刻，不等于 `doFrame` CPU 时长。
- `on_time_finish`、`present_type`、`jank_type`、`jank_tag` 要联合判断。
- `surface_frame_token` 对齐同一应用帧；`display_frame_token` 连接应用帧与显示帧。
- 一个 display frame 可以组合许多 layer，重复的 display token 不表示重复采样。
- 红色和黄色只提示原因归在哪一侧；确认 CPU、GPU、HWC 或队列问题时，仍需查看对应数据。
- SurfaceView 与独立 Surface 先确认覆盖范围，缺少 App Timeline 不能写成没有出帧。
- present 是 Android 显示栈报告的时间，release 和 panel 光学时刻需要其他数据。

在这些条件下，FrameTimeline 用于选择问题帧并判断原因归在 App 侧还是 SF 侧，线程、GPU、FrameTracer、HWC 与 display 数据再用于解释等待发生在哪里。

## 参考源码与验证材料

- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [API 33 `Choreographer.FrameData`](https://developer.android.com/reference/android/view/Choreographer.FrameData)、[`FrameTimeline`](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline) 与 [`VsyncCallback`](https://developer.android.com/reference/android/view/Choreographer.VsyncCallback)
- [Android 17 `Scheduler/FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
- [Android 17 `VSyncDispatchTimerQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/VSyncDispatchTimerQueue.cpp)
- [Android 17 `frame_timeline_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/trace/android/frame_timeline_event.proto)
- [Perfetto FrameTimeline 官方文档](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto v57.2 FrameTimeline importer](https://github.com/google/perfetto/blob/v57.2/src/trace_processor/importers/proto/frame_timeline_event_parser.cc)
- [Perfetto v57.2 `android.frames.timeline` 标准库](https://github.com/google/perfetto/blob/v57.2/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)
- §13.18 FrameTracer：buffer event、fence 与 frame identity 的对应关系和使用限制
