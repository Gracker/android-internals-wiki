---
title: FrameMetrics
chapter: '19'
section: '19.12'
status: "finalized"
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1 FrameMetrics.java / Window.java / FrameMetricsObserver.java / FrameMetricsReporter.cpp / FrameInfo.h / CanvasContext.cpp; Android Developers FrameMetrics API reference through API 37"
confidence: medium
tags:
- apm
related_chapters:
- '19.0'
sources:
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
task2b_state: fixed
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-03T08:38:28+08:00"
task2b_result: "fixed-lite"
last_task2b_at: '2026-05-31T17:35:00+08:00'
last_task2b_lite_at: '2026-05-31'
repaired_date: '2026-04-25'
repaired_by: openclaw-task2b
last_task9_audit: "2026-07-03"
last_task9_audit_log: "logs/deep-review/2026-07-03-03-audit.md"
last_task9_review_log: "logs/deep-review/2026-07-03-08-deep-review.md"
queue_entry: "task9-audit-2026-05-19-19-12-framemetrics-version-boundary"
task9_review_notes: "2026-06-02 Task9 deep review: pass-tech-review。复核 FrameMetrics API 24-37 字段、API 31 DEADLINE/GPU_DURATION 与 Android 12/13+ duration 边界；无 P0/P1，自动晋升 finalized。 | 2026-07-03 Task9 闲时抽检 AUTO-FIX：按 AOSP android-17.0.0_r1 重锚 FrameMetrics 源码基线；修正延伸阅读中 FrameInfo 索引数量旧口径（Android 17 为 FRAME_STATS_COUNT=25），回到 Task6 复审。 | 2026-07-03 Task9 deep review: pass-tech-review；无 P0/P1/P2；task6 已通过且 queue.json 无 pending，自动晋升 finalized；详见 logs/deep-review/2026-07-03-08-deep-review.md。"
last_task6_audit: "2026-07-03"
last_task9_autofix_at: "2026-07-03"
last_task2b_verifier_at: "2026-07-03T07:32:03+08:00"
last_task2b_verifier_log: "logs/rework/2026-05-31-23-task2b-verifier.md"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-07-03"
task6_reviewed_date: "2026-06-01"
last_task6_at: "2026-07-03T08:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-01-02-review.md"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
task6_review_notes: "2026-06-01 02:05 Task6 revisiting-review: L1/L2 扫描无新增正文修复；锚点 10/10 覆盖，无新增 Task2B 回炉项，送 Task9 复核。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-11
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
updated_by: "openclaw-task9"
updated_date: "2026-07-03"
p0: 0
p1: 0
p2: 0
---

# FrameMetrics

## FrameMetrics 提供一帧内部耗时分项

`FrameMetrics` 是 Android 7.0（API 24）加入的平台 API。它监听一个硬件加速 `Window` 由 HWUI 渲染出的帧，并给出输入、动画、布局、绘制、RenderThread 同步、GPU 命令提交、buffer swap 等阶段的时间。

平台源码锚点是 Android 17 / API 37 的 `android-17.0.0_r1`。FrameMetrics 的公开链路位于 framework 与 HWUI，相关结论不依赖某个 kernel 函数；需要追查 dma-fence、sync file 或驱动等待时，kernel 统一以 `android17-6.18-2026-06_r6` 为准，并结合目标设备的 vendor trace。

FrameMetrics 适合回答“这个 Window 的慢帧更集中在哪个阶段”。它不提供业务调用栈，也不直接观察 SurfaceFlinger、HWC、显示驱动或屏幕 present。看到 `DRAW_DURATION` 升高，只能把范围收窄到 UI 绘制与 display-list 生成附近，不能直接认定某个 View、Composable 或业务函数是根因。

## 数据从哪里来

Android 17 的 UI 线程和 RenderThread 共同填写一份 `FrameInfo` 时间戳数组。`FrameMetrics.java` 再按固定的起止索引计算公开指标。`FrameInfo.h` 与 `FrameMetrics.java` 都把数组长度定义为 25；这 25 项包含 flags、vsync id、input event id、frame deadline 和若干内部时间点，并不代表存在 25 个公开 duration。

`FrameMetricsObserver` 为公开 listener 复用同一个 `FrameMetrics` 对象，`FrameMetricsReporter` 在每帧完成后把对应数组送给 observer。注册 listener 之前已经排队的旧 surface / old frame 会被过滤，不会补发成历史数据。

Android 17 的 `FrameMetricsObserver` 创建 `HardwareRendererObserver` 时明确传入 `false /* waitForPresentTime */`。因此公开回调不等待 display present time；“收到了 FrameMetrics”只能证明 HWUI 帧统计已可用，不能证明这帧已经被 SurfaceFlinger 采纳或已经送到屏幕。

## 指标表：先看时间区间，再谈归因

Android 17 的公开指标及源码区间如下。`A → B` 表示用时间点 B 减去 A：

| 指标 | API | Android 17 的时间区间或取值 | 可以说明什么 |
|---|---:|---|---|
| `UNKNOWN_DELAY_DURATION` | 24+ | `INTENDED_VSYNC → HANDLE_INPUT_START` | UI 线程晚于目标 Vsync 开始处理本帧，可能有前序消息、调度等待或线程阻塞 |
| `INPUT_HANDLING_DURATION` | 24+ | `HANDLE_INPUT_START → ANIMATION_START` | 本帧输入处理区间的成本 |
| `ANIMATION_DURATION` | 24+ | `ANIMATION_START → PERFORM_TRAVERSALS_START` | Choreographer animation callback 区间的成本 |
| `LAYOUT_MEASURE_DURATION` | 24+ | `PERFORM_TRAVERSALS_START → DRAW_START` | View hierarchy 的 measure / layout 及其附近 traversal 成本 |
| `DRAW_DURATION` | 24+ | `DRAW_START → SYNC_QUEUED` | UI 线程记录或更新 display list 并把同步任务排给 RenderThread 的成本 |
| `SYNC_DURATION` | 24+ | `SYNC_START → ISSUE_DRAW_COMMANDS_START` | RenderThread 同步 UI 线程提交的渲染树状态所用时间 |
| `COMMAND_ISSUE_DURATION` | 24+ | `ISSUE_DRAW_COMMANDS_START → SWAP_BUFFERS` | RenderThread 向 GPU 发出绘制命令直到进入 swap 的区间 |
| `SWAP_BUFFERS_DURATION` | 24+ | API 31-37 为 `SWAP_BUFFERS → SWAP_BUFFERS_COMPLETED` | buffer swap 调用区间；旧系统定义更宽，版本边界见下文 |
| `TOTAL_DURATION` | 24+ | `INTENDED_VSYNC → FRAME_COMPLETED` | HWUI 生产并把帧发往 display subsystem 的总区间，不是屏幕 present duration |
| `FIRST_DRAW_FRAME` | 24+ | `FLAG_WINDOW_VISIBILITY_CHANGED` 的布尔结果 | 新 Window layout 的首个 draw，应与稳态动画和滚动分开 |
| `INTENDED_VSYNC_TIMESTAMP` | 26+ | `INTENDED_VSYNC` 时间戳 | 目标帧起点 |
| `VSYNC_TIMESTAMP` | 26+ | `VSYNC` 时间戳 | 本帧回调采用的 Vsync 时间；与 intended 不同表示 UI 线程未及时响应原目标 |
| `GPU_DURATION` | 31+ | API 33-37 为 `COMMAND_SUBMISSION_COMPLETED → GPU_COMPLETED` | GPU 完成本帧命令的区间 |
| `DEADLINE` | 31+ | `INTENDED_VSYNC → FRAME_DEADLINE` | 系统分配给应用生产该帧的预算 |
| `FRAME_TIMELINE_VSYNC_ID` | 36+ | 本帧选择的 FrameTimeline Vsync id | 将 HWUI 帧与 compositor jank data 关联的 join key |

这张表是“阶段线索表”，不是“根因表”。例如 `UNKNOWN_DELAY_DURATION` 高只能说明本帧起跑晚；主线程在执行长任务、处于 runnable 但没有获得 CPU、等待 Binder 或锁，都可能产生相似结果。

`getMetric()` 在指标不可用时返回 `-1`。客户端仍应先按 API level 守卫新增常量，再把负值当作缺失数据；不能把 `-1 ns` 写入直方图，也不能用零补齐后伪装成有效观测。

### `TOTAL_DURATION` 为什么不等于阶段之和

`TOTAL_DURATION` 直接使用 `FRAME_COMPLETED - INTENDED_VSYNC`，各阶段则分别使用自己的时间点。以下情况会让两者无法简单相加：

- UI 与 RenderThread 的部分工作可以并行。
- `SYNC_QUEUED → SYNC_START` 的 RenderThread 排队间隙没有独立公开 stage 指标，但会进入 total 区间。
- GPU completion 可能晚于 `FRAME_COMPLETED`；`GPU_DURATION` 也不保证被 total 完整包含。
- API 24-30、31-32、33-37 的 GPU / swap 起止点不同。

因此，`total - sum(stages)` 不能命名为“其它耗时”后直接归因。它只表示公开阶段没有覆盖或存在并行关系，下一步要回到 Perfetto 时间线。

### GPU 与 swap 的版本边界

按系统版本分桶是聚合的必要条件：

| 系统版本 | `SWAP_BUFFERS_DURATION` | `GPU_DURATION` | `DEADLINE` |
|---|---|---|---|
| API 24-30 | `SWAP_BUFFERS → FRAME_COMPLETED` | 不可用 | 不可用 |
| API 31-32 | `SWAP_BUFFERS → SWAP_BUFFERS_COMPLETED` | `SWAP_BUFFERS → GPU_COMPLETED` | 可用 |
| API 33-35 | `SWAP_BUFFERS → SWAP_BUFFERS_COMPLETED` | `COMMAND_SUBMISSION_COMPLETED → GPU_COMPLETED` | 可用 |
| API 36-37 | 同 API 33+ | 同 API 33+ | 可用，并增加 `FRAME_TIMELINE_VSYNC_ID` |

这也是为什么 API 24-30 的高 `SWAP_BUFFERS_DURATION` 比 API 31+ 更宽泛。跨桶比较原始数值会把平台定义变化误当成性能变化。

## Window 范围决定了它看得见什么

FrameMetrics 的观察对象是注册 listener 的硬件加速 Window。先确认页面的出图拓扑，再解释指标：

| 页面内容 | FrameMetrics 能看到的部分 | 看不到的部分 |
|---|---|---|
| 普通 View 页面 | 宿主 Window 的 UI / RenderThread / swap 阶段 | SurfaceFlinger、HWC 和最终 present |
| 标准宿主中的 Compose | 同一个宿主 Window 阶段 | 某个 Composable 的函数级成本与重组原因 |
| TextureView | 外部 buffer 被 HWUI 采样、混合并写入宿主 Window 后产生的宿主成本 | 外部 Producer 自己的解码、Camera、EGL/Vulkan 生产和第一套 BufferQueue 背压 |
| SurfaceView | 宿主 UI、hole-punch、几何或控制层对应的宿主帧 | 独立 Surface 的内容 Producer、独立 BufferQueue 与内容 layer 帧 |
| 多 Window、Dialog、PopupWindow | 每个已注册 Window 各自的帧 | 未注册 Window；不同 Window 不会自动合并 |
| 软件渲染 Window | 无可用的硬件渲染帧统计 | 软件 Canvas 的完整耗时 |

`SurfaceView`、视频、相机和游戏常有独立 Producer。宿主主线程很空、宿主 FrameMetrics 正常，都不能证明主体内容按时到达屏幕。此时要按内容 layer 查 producer queue、acquire/release fence、SurfaceFlinger latch、HWC 与 present timing。

TextureView 的情况相反：外部 stream 会在应用内由 HWUI 采样进宿主 App Window。FrameMetrics 可能表现出 RenderThread、GPU 或 swap 成本增加，但外部输入 buffer 为什么晚到，仍需查看 SurfaceTexture 队列与它自己的 fence。

## 正确接入 listener

下面的示例只适用于 API 24+。调用方应在 `setContentView()` 之后、Window 已有 DecorView 时创建 tracker，并在同一 Window 不再采集时调用 `close()`：

```kotlin
@RequiresApi(Build.VERSION_CODES.N)
class FrameMetricsTracker(
    private val window: Window,
    private val sink: (WindowFrameSample) -> Unit
) : Closeable {
    private var callbackThread: HandlerThread? = null
    private var started = false

    private val listener =
        Window.OnFrameMetricsAvailableListener { _, metrics, droppedReports ->
            val total = metrics.getMetric(FrameMetrics.TOTAL_DURATION)
            val deadline =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    metrics.getMetric(FrameMetrics.DEADLINE)
                        .takeIf { it > 0 }
                } else {
                    null
                }
            val vsyncId =
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.BAKLAVA) {
                    metrics.getMetric(FrameMetrics.FRAME_TIMELINE_VSYNC_ID)
                        .takeIf { it > 0 }
                } else {
                    null
                }

            sink(
                WindowFrameSample(
                    totalDurationNanos = total,
                    layoutMeasureNanos =
                        metrics.getMetric(FrameMetrics.LAYOUT_MEASURE_DURATION),
                    drawNanos = metrics.getMetric(FrameMetrics.DRAW_DURATION),
                    syncNanos = metrics.getMetric(FrameMetrics.SYNC_DURATION),
                    commandIssueNanos =
                        metrics.getMetric(FrameMetrics.COMMAND_ISSUE_DURATION),
                    swapBuffersNanos =
                        metrics.getMetric(FrameMetrics.SWAP_BUFFERS_DURATION),
                    gpuNanos =
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                            metrics.getMetric(FrameMetrics.GPU_DURATION)
                                .takeIf { it >= 0 }
                        } else {
                            null
                        },
                    deadlineNanos = deadline,
                    missedAppDeadline =
                        deadline != null && total > deadline,
                    firstDraw =
                        metrics.getMetric(FrameMetrics.FIRST_DRAW_FRAME) == 1L,
                    frameTimelineVsyncId = vsyncId,
                    droppedReportsSinceLastCallback = droppedReports
                )
            )
        }

    @MainThread
    fun start() {
        if (started) return

        val thread = HandlerThread("window-frame-metrics").apply { start() }
        window.addOnFrameMetricsAvailableListener(
            listener,
            Handler(thread.looper)
        )
        callbackThread = thread
        started = true
    }

    @MainThread
    override fun close() {
        if (!started) return

        window.removeOnFrameMetricsAvailableListener(listener)
        started = false
        callbackThread?.quitSafely()
        callbackThread = null
    }
}

data class WindowFrameSample(
    val totalDurationNanos: Long,
    val layoutMeasureNanos: Long,
    val drawNanos: Long,
    val syncNanos: Long,
    val commandIssueNanos: Long,
    val swapBuffersNanos: Long,
    val gpuNanos: Long?,
    val deadlineNanos: Long?,
    val missedAppDeadline: Boolean,
    val firstDraw: Boolean,
    val frameTimelineVsyncId: Long?,
    val droppedReportsSinceLastCallback: Int
)
```

示例在回调返回前只读取数值，没有保存复用的 `FrameMetrics` 引用。`sink` 必须是线程安全的轻量内存聚合器；文件写入、JSON 序列化和网络上传不能放在逐帧回调里。若业务确需把整份对象交给其它线程，应使用 `FrameMetrics(metrics)` 创建副本，但这会增加每帧分配。

`droppedReportsSinceLastCallback` 表示 FrameMetrics 报告投递没有跟上，并不表示屏幕丢了同样数量的帧。该值大于零时，本窗口的分母和分位数已经有观测缺口，应单独累计并标记数据质量，不能把它加到 jank frame 数。

`Handler` 决定 listener 回调线程。使用专用 `HandlerThread` 可以避免监控逻辑占用主线程，但回调依然要足够轻；线程队列拥塞会让报告被丢弃。注册、移除 listener 与 Window 生命周期操作放在主线程更容易保持顺序。

## `DEADLINE` 是应用预算，不是完整显示结论

API 31+ 的 `DEADLINE` 由 `FRAME_DEADLINE - INTENDED_VSYNC` 得到。它比固定 16.6 ms 更适合 90 Hz、120 Hz 和可变刷新率设备，因为预算由系统按本帧时间线给出。

服务端可以把 `TOTAL_DURATION > DEADLINE` 定义为 App deadline miss，并把比较规则写进 schema。这个判断仍有三条边界：

- `TOTAL_DURATION` 的终点是 HWUI `FRAME_COMPLETED`，不是 present fence。
- 应用按时完成后，SurfaceFlinger、HWC 或显示链后段仍可能错过目标 present。
- `FIRST_DRAW_FRAME` 常受窗口初始化和转场遮挡影响，应从滚动、动画等稳态分母中拆出。

API 24-30 没有 `DEADLINE`。如果产品必须估算，可按观测到的显示模式建立独立指标，并记录刷新率来源与采样时刻；不能把估算值伪装成平台 deadline，也不能在所有设备上写死 16 ms。

### Android 17：用 Vsync id 连接 compositor 证据

Android 16（API 36）新增 `FrameMetrics.FRAME_TIMELINE_VSYNC_ID`，Android 17（API 37）继续提供。它与 `SurfaceControl.JankData.getVsyncId()` 使用同一个关联键。

API 36+ 中，应用可在 View 已附着期间、UI 线程上通过 `View.getRootSurfaceControl()` 获得非空 `AttachedSurfaceControl`，再用 `registerOnJankDataListener()` 注册 compositor 的批量回调。`JankData.getJankType()` 返回 bitmask，多个原因可以同时出现：

- `JANK_APPLICATION`：应用错过 deadline。
- `JANK_COMPOSER`：composer 错过 deadline。
- `JANK_OTHER`：其它系统组件导致的 jank。
- scheduled / actual app frame time，以及对应 Vsync id。

JankData 是延迟、批量返回的分类数据。线上关联应使用有界的 `vsyncId → frame sample` 缓存并设置过期时间，不能假定它与 FrameMetrics callback 一一同步到达。注销 listener 时，`OnJankDataListenerRegistration.removeAfter(vsyncId)` 可以等待指定帧的分类返回；`flush()` 会请求发送仍在 pending 的批次，并可能在调用栈内触发 listener，调用方不能假定它总是异步。

这条关联补上了 FrameMetrics 的系统侧分类，但仍不会提供业务函数栈。`JANK_APPLICATION` 需要回看 FrameMetrics 阶段与应用 trace，`JANK_COMPOSER` 则应进入 Perfetto 的 SurfaceFlinger、DisplayFrame、HWC 和 present 证据。

## 每个阶段怎样继续排查

| 异常指标 | 可能方向 | 可执行的下一步 |
|---|---|---|
| `UNKNOWN_DELAY_DURATION` 高 | 前序主线程任务、runnable 等待、锁、Binder 或消息拥塞 | 在 Perfetto 中对齐 intended Vsync，检查 main thread sched state、Looper 与前一段长 slice |
| `INPUT_HANDLING_DURATION` 高 | 输入回调、手势识别、嵌套滚动或同步业务工作 | 给输入入口加业务 trace，结合 input dispatch 与方法采样确认调用者 |
| `ANIMATION_DURATION` 高 | Animator 回调、滚动计算、Compose 状态推进范围过大 | 查看 Choreographer animation slice、Compose tracing 和状态更新范围 |
| `LAYOUT_MEASURE_DURATION` 高 | `requestLayout()` 扩散、复杂约束、列表 item 反复测量 | 用 Layout Inspector 确认层级，再用 trace marker 标出关键 measure/layout |
| `DRAW_DURATION` 高 | 自定义绘制、文本、path、阴影、display-list 重录 | 结合 Profile HWUI、Compose drawing trace 与目标 View 的自定义 trace |
| `SYNC_DURATION` 高 | RenderNode 状态同步、资源上传准备或 RenderThread 压力 | 在 Perfetto 中检查 `syncAndDrawFrame`、RenderThread `DrawFrame` 与资源上传相关 slice |
| `COMMAND_ISSUE_DURATION` 高 | 绘制命令过多、RenderThread CPU 成本、driver submission | 对齐 RenderThread、GPU queue 与 HWUI/GPU counters；减少 overdraw 或复杂效果后做 A/B |
| `GPU_DURATION` 高 | fragment/vertex 工作、带宽、纹理采样或 GPU contention | 使用 Perfetto GPU 轨迹和设备 GPU 工具；记录 SoC、频率与温控状态 |
| `SWAP_BUFFERS_DURATION` 高 | App Window BufferQueue 背压、swap 等待或显示消费滞后 | 检查宿主 `dequeue/queueBuffer`、`BufferTX`、acquire/release fence、latch 与 present；先按 API 桶解释 |
| `TOTAL_DURATION` 高但各 stage 不高 | RenderThread queue gap、阶段重叠或未公开区间 | 对齐 `SYNC_QUEUED → SYNC_START`、线程调度和完整 HWUI trace |
| `FIRST_DRAW_FRAME` 高 | 新 Window layout、资源初始化或首屏工作 | 单独建立首帧/首屏指标，不与稳态交互一起排名 |

FrameMetrics 阶段只能确定排查入口。GPU driver、SurfaceFlinger 或 HWC 的函数与等待原因仍要靠 Perfetto、厂商 GPU 工具和目标设备证据。

## 页面状态要按时间关联

FrameMetrics 没有 JankStats 的 `PerformanceMetricsState`。如果回调到达时直接读取“当前 route”，页面已切换的情况下可能把前一个 Window frame 记到新页面。

API 26+ 可以使用 `INTENDED_VSYNC_TIMESTAMP` 与客户端维护的页面/交互状态区间做时间交集。API 24-25 没有这个公开时间戳，建议只做 Window session 级聚合，或在 route 切换时明确结束旧窗口并接受较粗的边界。页面字段还应遵守以下约束：

- 使用稳定 route 名，不上传 URL、内容 id、搜索词等高基数字段。
- 滚动、转场、刷新和 idle 分开，避免大量静止帧稀释交互问题。
- Dialog、PopupWindow 和多窗口分别注册、分别计数。
- 前后台、分屏和画中画状态写入 session 维度，不能只依赖 Activity 名。

## 端侧聚合协议

逐帧上传会制造额外开销，也会让后端数据量失控。下面是一份 API 36-37 窗口级示例，适合在端侧由计数器和固定桶直方图生成：

```json
{
  "schema_version": 3,
  "api_bucket": "36-37",
  "screen": "SearchResult",
  "interaction": "scroll",
  "window_ms": 10000,
  "observed_frames": 480,
  "first_draw_frames": 0,
  "deadline_eligible_frames": 480,
  "app_deadline_miss_frames": 42,
  "frame_metrics_reports_dropped": 0,
  "total_duration_ms": {
    "p50": 8.1,
    "p95": 27.8,
    "p99": 43.4
  },
  "stage_p95_ms": {
    "unknown": 1.2,
    "layout_measure": 9.1,
    "draw": 6.4,
    "sync": 4.2,
    "command_issue": 3.7,
    "swap": 2.6,
    "gpu": 7.8
  },
  "dominant_stage": "layout_measure"
}
```

`observed_frames` 只统计收到的报告，`frame_metrics_reports_dropped` 单独记录观测缺口。`app_deadline_miss_frames` 的分母必须是 deadline 可用帧；API 24-30 不应把刷新率估算混进这个字段。Vsync id 具有逐帧高基数，只应保存在有界的异常样本或短期关联缓存中，不进入常规聚合维度。

采样应按稳定的 device/session 哈希选择整段窗口，正常帧和异常帧采用同一规则。只保留慢帧会丢掉分母，也会让 P50/P95 失真。异常原始样本可以设置小容量上限，例如保留连续 deadline miss 窗口和各阶段极端值，不要维护无界队列。

## 与 JankStats 的分工

| 维度 | JankStats 1.0.0 | FrameMetrics |
|---|---|---|
| 正常发布物版本范围 | API 23+ | API 24+ |
| 回调数据 | `FrameData`、`isJank`、版本化 duration、UI context | Window 的原始阶段 duration、first draw、deadline、API 36+ vsync id |
| 业务状态 | 内置 `PerformanceMetricsState` 时间区间关联 | 需要客户端自行按时间关联 |
| 默认 jank 口径 | UI duration 大于两倍 expected duration | 没有内置 jank 布尔值；客户端可比较 total 与 deadline |
| 线上成本 | 字段较少，适合页面/交互分布 | 字段多，需严格聚合与降采样 |
| 专项价值 | 快速定位哪个页面和交互变差 | 判断变化更集中于 layout、draw、sync、command、swap 或 GPU |

JankStats 在 API 24+ 内部已经注册 FrameMetrics listener。若应用同时直接注册 FrameMetrics，就会为同一 Window 增加另一条逐帧回调链。两者可以共存，但上线前要测量回调、聚合和对象分配成本，避免为了重复的 total/jank 指标增加监听。

`JankStats.isJank` 与 `TOTAL_DURATION > DEADLINE` 也不能合并。JankStats 1.0.0 默认比较 UI duration 与两倍 expected duration；FrameMetrics deadline miss 比较 total 与一次应用预算。字段名、分子和分母必须分开。

## Compose、View 与外部内容

Compose 在标准 Activity 中仍通过同一个 ViewRoot、RenderThread 和 App Window 输出。FrameMetrics 可以告诉你宿主 Window 的 layout/draw/sync 等阶段变慢，但不会标出某个 Composable。需要继续使用 Compose runtime tracing、compiler report、Layout Inspector 和业务 trace。

View 页面同样不能靠阶段数字定位到控件。`LAYOUT_MEASURE_DURATION` 高时要检查本帧是否发生大范围 `requestLayout()`；`DRAW_DURATION` 高时要检查 display-list 重录、自定义绘制和文本/path 成本。

嵌入外部内容时先判断汇合位置：

- TextureView 内容会被宿主 HWUI 采样，宿主 FrameMetrics 能反映这次采样及后续输出成本。
- SurfaceView 内容保持独立 layer，宿主 FrameMetrics 不包含其 Producer 帧。
- WebView、Flutter、Camera、Video 和游戏可能选择不同承载方式；框架名不能替代 Surface、BufferQueue 与 layer 拓扑检查。

## 与 Macrobenchmark FrameTimingMetric 的关系

`FrameTimingMetric` 用于受控测试，当前会输出 `frameDurationCpuMs`，并在 API 31+ 输出 `frameOverrunMs` 的 P50/P90/P95/P99。它适合回答同一交互在代码变更前后是否退化，不等同于线上直接上传每个 FrameMetrics stage。

建议把线上 FrameMetrics 用于发现“哪个版本、页面、设备桶和阶段发生变化”，再把相同交互写成 Macrobenchmark 场景。修复验收同时检查 benchmark 分布和真实用户分层，避免单台实验设备的结果掩盖低端机、温控或高刷新率差异。

## 上线检查清单

- 只在 API 24+、硬件加速且 DecorView 已建立的 Window 注册。
- 一个 Window 明确一个 listener owner，重复 start 不重复注册。
- listener 使用专用线程，回调只做数值读取和有界内存聚合。
- Window 停止采集时移除 listener，再退出 HandlerThread。
- 累计 report drop，并为存在观测缺口的窗口标记数据质量。
- API 24-30、31-32、33-35、36-37 分桶，尤其不混合 GPU / swap 定义。
- first draw、idle、滚动、转场与首屏使用独立维度。
- API 36+ 需要系统侧分类时，用 vsync id 关联 JankData，并处理延迟批次与缓存过期。
- SurfaceView、Camera、Video 等独立 Producer 按自身 layer 和 BufferQueue 另建证据链。
- 阶段异常进入 Perfetto 或专项工具验证，不把单个 duration 当作函数级根因。

## 参考资料

- [Android Developers：FrameMetrics](https://developer.android.com/reference/android/view/FrameMetrics)
- [Android Developers：Window.OnFrameMetricsAvailableListener](https://developer.android.com/reference/android/view/Window.OnFrameMetricsAvailableListener)
- [Android Developers：View.getRootSurfaceControl](https://developer.android.com/reference/android/view/View)
- [Android Developers：AttachedSurfaceControl](https://developer.android.com/reference/android/view/AttachedSurfaceControl)
- [Android Developers：SurfaceControl.JankData](https://developer.android.com/reference/android/view/SurfaceControl.JankData)
- [Android Developers：SurfaceControl.OnJankDataListenerRegistration](https://developer.android.com/reference/android/view/SurfaceControl.OnJankDataListenerRegistration)
- [Android Developers：Capture Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Android Developers：Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Perfetto：FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [AOSP android-17.0.0_r1：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP android-17.0.0_r1：Window.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Window.java)
- [AOSP android-17.0.0_r1：FrameMetricsObserver.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetricsObserver.java)
- [AOSP android-17.0.0_r1：FrameInfo.h](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/FrameInfo.h)
- [AOSP android-17.0.0_r1：FrameMetricsReporter.cpp](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/FrameMetricsReporter.cpp)
- [AOSP android-17.0.0_r1：CanvasContext.cpp](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)
- [AOSP android-17.0.0_r1：SurfaceControl.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java)
- [AOSP Android 11：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-11.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP Android 12：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-12.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP Android 13：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-13.0.0_r1/core/java/android/view/FrameMetrics.java)
- [Kernel android17-6.18-2026-06_r6：dma-fence.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
- [Kernel android17-6.18-2026-06_r6：sync_file.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
