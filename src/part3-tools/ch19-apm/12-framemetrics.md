---
title: "FrameMetrics"
chapter: "19"
section: "19.12"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "Android FrameMetrics API reference"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
pipeline_stage: drafted
---

# FrameMetrics

## FrameMetrics 拆的是一帧内部耗时

`FrameMetrics` 是 Android 7.0（API 24）加入的平台 API，用来获取 Window 每一帧的耗时拆解。它比 JankStats 更接近渲染阶段：输入、动画、布局测量、绘制、同步、GPU 命令提交、buffer 交换、总耗时等。

它适合在高版本设备上补“慢帧像发生在哪一段”。它仍然不是完整 trace。拿到 `DRAW_DURATION` 高，只能说明 draw 阶段耗时高；要确认是哪棵 View、哪个 Compose 节点或哪段业务代码，还要继续抓 Perfetto 或 Profiler。

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
| `SWAP_BUFFERS_DURATION` | Buffer 交换耗时 | 图形缓冲区相关等待 |
| `TOTAL_DURATION` | 帧总耗时 | 该帧完整耗时 |
| `DEADLINE` | 系统给应用生成该帧的时间预算 | API 31+，可用于判断是否 missed deadline |

Android 官方文档说明：API 31 起 `DEADLINE` 表示系统分配给应用生成该帧的总时间。如果 `TOTAL_DURATION < DEADLINE`，这帧命中了预期 deadline，用户侧不会看到 jank。

## 接入方式

下面的代码展示 `FrameMetrics` 的基本监听方式，重点是给回调准备独立 `HandlerThread`，避免把每帧处理放回主线程。

```kotlin
class FrameMetricsTracker(private val activity: Activity) {
    private val thread = HandlerThread("frame-metrics").apply { start() }
    private val handler = Handler(thread.looper)

    private val listener = Window.OnFrameMetricsAvailableListener { _, metrics, _ ->
        val total = metrics.getMetric(FrameMetrics.TOTAL_DURATION)
        val draw = metrics.getMetric(FrameMetrics.DRAW_DURATION)
        val sync = metrics.getMetric(FrameMetrics.SYNC_DURATION)
        reportFrame(totalDurationNanos = total, drawNanos = draw, syncNanos = sync)
    }

    fun start() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            activity.window.addOnFrameMetricsAvailableListener(listener, handler)
        }
    }

    fun stop() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            activity.window.removeOnFrameMetricsAvailableListener(listener)
        }
        thread.quitSafely()
    }
}
```

这段代码省略了采样和批量上报。线上实现要避免每帧都创建大量对象，否则监控逻辑会增加 GC 压力。

## 它的边界

FrameMetrics 数据来自 Window。它适合观察应用 UI 帧，但不覆盖所有系统层细节：

- 它不能直接告诉你 CPU 被哪个线程抢走。
- 它不能完整解释 SurfaceFlinger、HWC、GPU driver 的问题。
- 它不能替代方法调用栈。
- 它不能自动关联业务页面状态。

所以 FrameMetrics 更适合做 JankStats 的增强字段。比如线上慢帧率抬升时，同时看高版本设备的 `LAYOUT_MEASURE_DURATION` 是否抬升，可以快速判断问题更像 UI 树复杂度，还是主线程消息等待。

## 使用建议

接入时不要全量上传每一帧原始数据。更合适的是按页面和交互做窗口聚合：

- 总帧数、慢帧数。
- `TOTAL_DURATION` 的 P50 / P90 / P95 / P99。
- 各阶段耗时的 P95 或异常样本。
- 首帧和转场帧单独标记。

FrameMetrics 给的是阶段线索。修问题时，仍然要把异常页面用 Perfetto 复现，再把主线程、RenderThread、GPU 和 SurfaceFlinger 放在同一条时间线上看。

## 每个阶段对应的排查方向

FrameMetrics 的价值在于把慢帧拆成阶段。读数时要把阶段和可能原因对应起来：

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
val deadline = metrics.getMetric(FrameMetrics.DEADLINE)
val missedDeadline = deadline > 0 && total > deadline
```

如果设备低于 API 31，再按刷新率估算预算。不要在所有设备上硬编码 16ms。

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

## HandlerThread 不是可选项

`addOnFrameMetricsAvailableListener()` 传入的 `Handler` 决定回调在哪个线程执行。如果传主线程，监控回调本身会参与主线程负担；如果回调里再做聚合、对象创建或上报，就会污染指标。

推荐做法：

- 专用 `HandlerThread` 接收回调。
- 回调内只读取需要的 metric，写入轻量 ring buffer。
- 后台任务定时聚合。
- Activity destroy 时移除 listener，避免泄漏 Window。

FrameMetrics 采的是每帧数据，任何额外对象分配都会放大。

## 和 Compose / View 的关系

FrameMetrics 不直接告诉你 Compose 哪个 Composable 慢，也不告诉你 View 树哪个节点慢。它只告诉你阶段。比如 `LAYOUT_MEASURE_DURATION` 高：

- View 场景可以用 Layout Inspector、`ViewDebug`、Perfetto 的 view 相关 trace 继续查。
- Compose 场景要看 recomposition、布局层级、lazy list item 复杂度和 state 更新范围。

所以 FrameMetrics 适合线上分流：先判断慢在布局、绘制、sync 还是 GPU 提交，再选择对应线下工具。
