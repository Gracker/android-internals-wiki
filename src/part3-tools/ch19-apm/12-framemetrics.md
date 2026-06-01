---
title: FrameMetrics
chapter: '19'
section: '19.12'
status: finalized
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: '2026-05-31'
last_verified_against: "AOSP FrameMetrics.java android-7.0.0_r1 - android-16.0.0_r1 + Android FrameMetrics API reference through API 37; android-17.0.0_r1 Gitiles tag unavailable"
confidence: medium
tags:
- apm
related_chapters:
- '19.0'
sources:
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
task2b_state: "fixed"
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-06-02"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-02T04:21:00+08:00"
task2b_result: "fixed-lite"
last_task2b_at: '2026-05-31T17:35:00+08:00'
last_task2b_lite_at: '2026-05-31'
repaired_date: '2026-04-25'
repaired_by: openclaw-task2b
last_task9_audit: "2026-05-19"
last_task9_review_log: "logs/deep-review/2026-06-02-04-deep-review.md"
queue_entry: "task9-audit-2026-05-19-19-12-framemetrics-version-boundary"
task9_review_notes: "2026-06-02 Task9 deep review: pass-tech-review。复核 FrameMetrics API 24-37 字段、API 31 DEADLINE/GPU_DURATION 与 Android 12/13+ duration 边界；无 P0/P1，自动晋升 finalized。"
last_task6_audit: '2026-05-20'
last_task9_autofix_at: "2026-05-31"
last_task2b_verifier_at: "2026-05-31T23:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-05-31-23-task2b-verifier.md"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-01"
task6_reviewed_date: "2026-06-01"
last_task6_at: "2026-06-01T02:05:00+08:00"
last_task6_review_log: "logs/review/2026-06-01-02-review.md"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task9_state: reviewed
pipeline_stage: ready-to-publish
task6_review_notes: "2026-06-01 02:05 Task6 revisiting-review: L1/L2 扫描无新增正文修复；锚点 10/10 覆盖，无新增 Task2B 回炉项，送 Task9 复核。"
---

# FrameMetrics

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 FrameMetrics 用来拆一帧内部耗时，适合分析 layout、draw、sync、command issue、swap 等阶段分布。
- 🔹 [指标表] 列出 `TOTAL_DURATION`、`INPUT_HANDLING_DURATION`、`LAYOUT_MEASURE_DURATION`、`DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION`、`SWAP_BUFFERS_DURATION`、`DEADLINE` 等指标含义和版本边界。
- 🔹 [接入方式] 展开 `Window.addOnFrameMetricsAvailableListener`、HandlerThread、Window 生命周期、页面切换和回收。
- 🔹 [阶段归因] 每个阶段给对应排查方向：主线程布局、RenderThread、GPU、Surface、系统调度、资源加载。
- 🔹 [DEADLINE] 说明高刷新率设备下为什么应优先看 deadline / expected duration 相关口径。
- 🔹 [聚合策略] 设计端侧窗口聚合，不保留所有原始帧；字段包含 page、frame count、p50/p95、slow count、stage max。
- 🔹 [边界] 说明 FrameMetrics 不提供业务函数栈、网络状态、后台线程细节，需要和 tracing / Perfetto 配合。
- 🔹 [Compose / View] 写清 Compose 最终仍落到 Window / View 渲染指标，但 UI 状态需要额外标记。
- 🔹 [使用建议] 说明哪些页面适合采、哪些场景应降采样，如何避免 listener 泄漏和后台线程拥塞。
- 🔹 [与 JankStats] 对比事件粒度、字段语义、易用性、线上聚合成本和专项诊断价值。

### 扩展（可选深入）

- 🔸 增加 FrameMetrics 接入代码，并标注 HandlerThread 和 Window 生命周期关键行。
- 🔸 补一张“指标阶段 -> 可能原因 -> 下一步工具”的表。
- 🔸 对 Android FrameMetrics API reference 做版本核对，特别是 DEADLINE 可用性。
- 🔸 增加一个高刷新率设备上 16ms 口径失效的例子。
- 🔸 补充与 Macrobenchmark FrameTimingMetric 的关系。

### 流水线加工要求

- 指标解释要绑定具体阶段，不要只翻译 API 名称。
- 每个阶段都要写一个可执行的下一步排查动作。
- 接入代码必须包含线程和生命周期清理，否则不算完整示例。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## FrameMetrics 提供一帧内部耗时分项

`FrameMetrics` 是 Android 7.0（API 24）加入的平台 API，用来获取 Window 每一帧的耗时分项。它比 JankStats 更接近渲染阶段：输入、动画、布局测量、绘制、同步、GPU 命令提交、buffer 交换、总耗时等。

它适合在高版本设备上回答“慢帧发生在哪一段”。它仍然不是完整的 Trace。看到 `DRAW_DURATION` 高，只能说明 draw 阶段耗时高；要确认是哪棵 View、哪个 Compose 节点或哪段业务代码，还要继续抓 Perfetto 或 Profiler。

## 主要指标

| 指标 | 含义 | 常见解读 |
|---|---|---|
| `UNKNOWN_DELAY_DURATION` | Vsync 到处理开始前的等待 | 主线程消息队列或调度延迟 |
| `INPUT_HANDLING_DURATION` | 输入事件处理耗时 | 触摸、手势、输入分发耗时 |
| `ANIMATION_DURATION` | 动画回调耗时 | 属性动画、过渡动画计算 |
| `LAYOUT_MEASURE_DURATION` | measure / layout 耗时 | View 树过深、约束复杂 |
| `DRAW_DURATION` | 构建 DisplayList 耗时 | View draw 或 Compose 绘制成本 |
| `SYNC_DURATION` | UI 线程和 RenderThread 同步 | display list 同步、资源上传等待 |
| `COMMAND_ISSUE_DURATION` | GPU 命令提交耗时 | 渲染命令提交压力 |
| `GPU_DURATION` | GPU 完成本帧命令的耗时 | API 31+，用于区分 GPU 渲染压力和 UI / RenderThread 阶段压力 |
| `SWAP_BUFFERS_DURATION` | Buffer 交换耗时 | 图形缓冲区相关等待 |
| `TOTAL_DURATION` | 帧总耗时 | 该帧完整耗时 |
| `DEADLINE` | 系统给应用生成该帧的时间预算 | API 31+，可用于判断是否 missed deadline |

Android 官方文档说明：API 31 起 `DEADLINE` 表示系统分配给应用生成该帧的总时间，`GPU_DURATION` 表示 GPU 完成本帧命令的耗时。低于 API 31 的设备不要读取这两个字段，按 `TOTAL_DURATION` 和刷新率估算预算。

`TOTAL_DURATION` 不是各阶段 duration 的简单求和。AOSP `FrameMetrics.java` 通过每个指标自己的起止时间戳计算 duration，部分阶段可能并行或重叠。

按 Android 版本聚合时要做 API 分桶。`android.view.FrameMetrics` 在 Android 7-11（API 24-30）没有 `GPU_DURATION` / `DEADLINE`，`SWAP_BUFFERS_DURATION` 覆盖 `SWAP_BUFFERS -> FRAME_COMPLETED`；Android 12 / 12L（API 31-32）的 `GPU_DURATION` 是 `SWAP_BUFFERS -> GPU_COMPLETED`；Android 13+（API 33-37）改为 `COMMAND_SUBMISSION_COMPLETED -> GPU_COMPLETED`，`SWAP_BUFFERS_DURATION` 则从 Android 12 起收敛为 `SWAP_BUFFERS -> SWAP_BUFFERS_COMPLETED`。线上对比 GPU / swap 原始时长时，不要把这些版本直接合并。

## 接入方式

下面的代码展示 `FrameMetrics` 的基本监听方式，重点是给回调准备独立 `HandlerThread`，避免把每帧处理放回主线程。官方 API 还要求 Window 处于硬件渲染模式；禁用硬件加速的窗口不会产生可用的帧统计。

```kotlin
class FrameMetricsTracker(private val activity: Activity) {
    private var thread: HandlerThread? = null
    private var handler: Handler? = null
    private var started = false

    private val listener = Window.OnFrameMetricsAvailableListener { _, metrics, dropCount ->
        val total = metrics.getMetric(FrameMetrics.TOTAL_DURATION)
        val draw = metrics.getMetric(FrameMetrics.DRAW_DURATION)
        val sync = metrics.getMetric(FrameMetrics.SYNC_DURATION)
        reportFrame(
            totalDurationNanos = total,
            drawNanos = draw,
            syncNanos = sync,
            droppedReports = dropCount
        )
    }

    fun start() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N || started) return

        val metricsThread = HandlerThread("frame-metrics").apply { start() }
        thread = metricsThread
        handler = Handler(metricsThread.looper)
        activity.window.addOnFrameMetricsAvailableListener(listener, handler)
        started = true
    }

    fun stop() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && started) {
            activity.window.removeOnFrameMetricsAvailableListener(listener)
        }
        started = false
        handler = null
        thread?.quitSafely()
        thread = null
    }
}
```

这段代码省略了采样和批量上报。`FrameMetrics` 回调参数会被复用，回调返回前只提取基础类型值；如果要保留完整对象，用 `FrameMetrics(metrics)` 复制一份。`dropCount` 大于 0 时，说明回调侧处理过慢或线程拥塞，已经有帧报告被丢弃。

## 它的边界

FrameMetrics 数据来自 Window。它适合观察应用 UI 帧，但不覆盖所有系统层细节：

- 它不能直接告诉你 CPU 被哪个线程抢走。
- 它不能完整解释 SurfaceFlinger、HWC、GPU driver 的问题。
- 它不能判断 SurfaceView、播放器或相机预览内部生产帧的耗时。
- 它不能替代方法调用栈。
- 它不能自动关联业务页面状态。

FrameMetrics 更适合做 JankStats 的增强字段。比如线上慢帧率抬升时，同时看高版本设备的 `LAYOUT_MEASURE_DURATION` 是否抬升，可以快速判断问题更像 UI 树复杂度，还是主线程消息等待。

| 维度 | JankStats | FrameMetrics |
|---|---|---|
| 事件口径 | 慢帧事件 + UI 上下文 | Window 每帧阶段耗时 |
| 版本覆盖 | API 16+ | API 24+ |
| 适合线上用途 | 页面 / 交互慢帧率聚合 | 高版本设备阶段归因补充 |
| 主要缺口 | 根因仍需 Trace | 业务状态要自己关联 |

## 使用建议

接入时不要全量上传每一帧原始数据。更合适的是按页面和交互做窗口聚合：

- 总帧数、慢帧数。
- `TOTAL_DURATION` 的 P50 / P90 / P95 / P99。
- 各阶段耗时的 P95 或异常样本。
- 首帧和转场帧单独标记。

FrameMetrics 给的是阶段线索。修问题时，仍然要把异常页面用 Perfetto 复现，再把主线程、RenderThread、GPU 和 SurfaceFlinger 放在同一条时间线上看。

## 每个阶段对应的排查方向

FrameMetrics 的价值在于按阶段呈现慢帧。读数时要把阶段和可能原因对应起来：

| 阶段异常 | 常见原因 | 下一步工具 |
|---|---|---|
| `UNKNOWN_DELAY_DURATION` 高 | 主线程消息队列积压、调度等待、前一个任务太长 | Perfetto sched、Looper block 样本 |
| `INPUT_HANDLING_DURATION` 高 | 触摸回调做重活、手势分发复杂 | Perfetto + 方法 trace |
| `ANIMATION_DURATION` 高 | 动画回调里计算过重、状态更新过多 | Method trace、Compose recomposition 分析 |
| `LAYOUT_MEASURE_DURATION` 高 | View 层级深、约束复杂、频繁 requestLayout | Layout Inspector、Perfetto |
| `DRAW_DURATION` 高 | 自定义 View 绘制复杂、文本/路径/阴影成本高 | GPU rendering、Profile HWUI |
| `SYNC_DURATION` 高 | UI 线程到 RenderThread 同步压力、资源上传 | Perfetto RenderThread |
| `COMMAND_ISSUE_DURATION` 高 | GPU 命令提交多、渲染内容复杂 | GPU profiler、Perfetto |
| `SWAP_BUFFERS_DURATION` 高 | BufferQueue / GPU / SurfaceFlinger 等待 | Perfetto graphics |

这张表要和 Perfetto 一起用。FrameMetrics 只给阶段数字，Perfetto 才能看到线程和系统事件。

## DEADLINE 让高刷新率口径更稳

API 31 之后的 `DEADLINE` 很适合处理 90Hz、120Hz、可变刷新率设备。传统 16.6ms 阈值只适合 60Hz。高刷新率下，应用可用帧预算更短；可变刷新率下，预算还会随场景变化。

判断逻辑应优先使用：

```kotlin
val total = metrics.getMetric(FrameMetrics.TOTAL_DURATION)
val missedDeadline = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
    val deadline = metrics.getMetric(FrameMetrics.DEADLINE)
    deadline > 0 && total > deadline
} else {
    estimateMissedDeadlineFromRefreshRate(total)
}
```

`DEADLINE` 是 API 31+ 字段，低版本设备按刷新率估算预算。不要在所有设备上硬编码 16ms。

## 聚合时不要保留所有原始帧

FrameMetrics 原始帧数据很密。线上建议按页面和交互状态聚合：

```text
screen=SearchResult
interaction=scroll
frames=480
missed_deadline=42
layout_p95_ms=9.1
draw_p95_ms=6.4
sync_p95_ms=4.2
command_issue_p95_ms=3.7
total_p95_ms=27.8
```

这个聚合能支持页面排名和阶段归因。原始帧只保留少量异常样本，例如 `total_p99` 附近的帧，或者连续 missed deadline 的窗口。

## 用独立 HandlerThread 接收回调

`addOnFrameMetricsAvailableListener()` 传入的 `Handler` 决定回调在哪个线程执行。传主线程时，监控回调本身会参与主线程负担；如果回调里再做聚合、对象创建或上报，就会污染指标。

推荐做法：

- 专用 `HandlerThread` 接收回调。
- 回调内只读取需要的指标，写入轻量环形缓冲区。
- 后台任务定时聚合。
- Activity 销毁时移除 listener，避免泄漏 Window。

FrameMetrics 采的是每帧数据，任何额外对象分配都会放大。

## 和 Compose / View 的关系

FrameMetrics 不直接告诉你 Compose 哪个 Composable 慢，也不告诉你 View 树哪个节点慢。它只告诉你阶段。比如 `LAYOUT_MEASURE_DURATION` 高：

- View 场景可以用 Layout Inspector、`ViewDebug`、Perfetto 的 view 相关 Trace 继续查。
- Compose 场景要看 recomposition、布局层级、lazy list item 复杂度和状态更新范围。

FrameMetrics 适合做线上分流：先判断慢在布局、绘制、sync 还是 GPU 提交，再选择对应线下工具。
