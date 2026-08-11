---
title: "帧率监控与线上卡顿治理"
chapter: "22.8"
section: "22.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-13"
last_verified_against: "AOSP android-16.0.0_r1, AndroidX JankStats docs, Android FrameMetrics docs"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
reviewed_date: "2026-06-13"
reviewed_by: openclaw-task6
review_type: task6-writing-quality-review
task6_result: pass-light-edit
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/jankstats"
  - type: official
    path: "https://developer.android.com/reference/androidx/metrics/performance/JankStats"
  - type: official
    path: "https://developer.android.com/reference/android/view/Choreographer"
  - type: official
    path: "https://developer.android.com/reference/android/view/Choreographer.FrameCallback"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
  - type: official
    path: "https://developer.android.com/reference/android/view/Window.OnFrameMetricsAvailableListener"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/FrameMetrics.java"
  - type: aiw
    path: "src/part3-tools/ch19-apm/09-jankstats-framemetrics.md"
  - type: aiw
    path: "src/part3-tools/ch19-apm/08-open-source-apm-history.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [frame-rate, jankstats, choreographer, online-monitoring]
related_chapters: ["22.1", "22.3", "7.2", "7.9", "19.8", "19.9", "26.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
last_task6_at: '2026-06-13'
task9_state: reviewed
task2b_state: fixed
task9_result: auto-fixed
task9_reviewed_date: '2026-05-19'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-05-19T07:31:24+08:00'
task2b_result: "fixed"
last_task9_review_log: "logs/deep-review/2026-06-12-20-audit.md"
last_task6_audit: "2026-06-09"
task9_review_notes: "2026-05-19 Task9：复核 6 维度无 P0/P1；queue 无 pending，task6_result=pass-light-edit，自动晋升 finalized。既有 P2 建议已在 intake/suggestions.md，不重复写入。 | 2026-06-12 Task9 idle audit AUTO-FIX：将 FrameMetrics.DEADLINE 从“帧截止时间戳”修正为系统给应用生成该帧的时间预算；证据为 Android FrameMetrics API reference through API 37 与 AOSP android-16.0.0_r1 FrameMetrics.java。回到 Task6 复审。"
last_task9_audit: "2026-06-12"
last_task9_autofix_at: "2026-06-12"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/09-rendering-case-studies.md"
---

# 帧率监控与线上卡顿治理

线上卡顿治理需要把发现、聚合和定位接成一条可执行流程：明确观测边界，保留可归因字段，用受控采样补充代码上下文，再把异常聚合成可分派的问题。卡顿成因见 7.2 节，JankStats 与 FrameMetrics 的接口细节见 19.9 节。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。涉及线程调度与 fence 等内核证据时，锚点是 `android17-6.18-2026-06_r6`。

## 先确定“这一帧”观测到了哪里

标准 App Window 的主要路径可以压缩为：VSync → Choreographer → UI 线程 → RenderThread → BLAST / BufferQueue → SurfaceFlinger → HWC 或 RenderEngine → display present。每种监控接口只覆盖其中一段：

| 观测入口 | 主要覆盖范围 | 能回答什么 | 不能单独证明什么 |
|---|---|---|---|
| `Choreographer.FrameCallback` | 绑定 Looper 收到并执行回调的节奏 | 主线程回调是否成簇延迟、采样窗口内的 callback cadence | Window 是否产出 buffer、该 buffer 是否显示 |
| JankStats | 某个 `Window` 的帧时长、jank 判定和 UI 状态 | 哪个页面、交互状态、版本和设备段变差 | 独立 Surface 内容是否顺滑、最终 present 的系统侧原因 |
| FrameMetrics | Window 一帧的 UI、RenderThread、GPU 与 deadline 等指标 | 应用侧主要耗时阶段、是否超过应用帧预算 | SurfaceFlinger 最终是否按期 present |
| `SurfaceControl.JankData` | API 36+ 的 compositor jank 分类 | 同一 VSync 是应用、composer 还是其他系统组件错过调度 | Java 方法级根因 |
| 堆栈与 Perfetto | 代码现场及跨进程时间线 | 阻塞方法、调度、fence、latch、composition、present | 只有一次样本时的普遍性 |

这个边界会直接影响结论。`queueBuffer()` 表示 producer 提交了 buffer，不能据此认定 SurfaceFlinger 已收到、latch 或 present。FrameMetrics 的 `TOTAL_DURATION` 结束于“渲染完成并交给显示子系统”，也没有覆盖 panel 扫描。

页面含 `SurfaceView`、Camera、视频、WebView、Flutter 或游戏引擎时，还要画清 Surface 拓扑。宿主 App Window 的指标可能很平稳，独立 Producer 对应的内容却在重复旧 buffer。此类页面要按目标 layer 补 producer queue、fence、FrameTimeline 与 present 证据，不能只用宿主 Window 的 JankStats 结案。

## Choreographer.FrameCallback：只把它当作回调节奏探针

`Choreographer` 接收显示侧 timing pulse，并在绑定的 `Looper` 上安排 input、animation、traversal 等回调。`postFrameCallback()` 注册的是一次性回调；持续采样需要在回调内再次注册。`doFrame(frameTimeNanos)` 的参数属于 `System.nanoTime()` 时间基准，是本轮渲染使用的稳定 frame time，不是回调开始执行的墙钟时间，也不是帧完成时间。

持续自注册会让 Looper 在每个采样周期执行额外回调。线上应把它限制在可见、正在交互且命中采样的短窗口内。回调里只写预分配的内存缓冲区，不做对象图构造、分位数计算、磁盘写入或网络上报。

下面的探针只记录原始 callback 间隔，不根据一个固定刷新率推导“掉了几帧”。`CadenceRingBuffer` 应由业务实现为有容量上限、写满即覆盖或拒绝写入的内存结构。

```kotlin
@MainThread
class CallbackCadenceProbe(
    private val ringBuffer: CadenceRingBuffer
) : Choreographer.FrameCallback {
    private val choreographer = Choreographer.getInstance()
    private var lastFrameTimeNanos = 0L
    private var running = false

    fun start() {
        if (running) return
        running = true
        lastFrameTimeNanos = 0L
        choreographer.postFrameCallback(this)
    }

    fun stop() {
        if (!running) return
        running = false
        choreographer.removeFrameCallback(this)
        lastFrameTimeNanos = 0L
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running) return

        val previous = lastFrameTimeNanos
        lastFrameTimeNanos = frameTimeNanos
        if (previous != 0L) {
            ringBuffer.offer(
                frameTimeNanos = frameTimeNanos,
                callbackIntervalNanos = frameTimeNanos - previous
            )
        }

        if (running) choreographer.postFrameCallback(this)
    }
}
```

这段数据只能说明回调时间轴出现了空档。自注册回调本身也会申请后续 VSync，因此它测到的是探针参与后的 callback cadence。若页面没有内容更新，采到一串稳定回调也不能解释为一串已显示的新帧；若主线程长时间繁忙，间隔变大也不能区分 CPU 执行、runnable 等待、锁、Binder 或 I/O。

刷新率会因 display mode、应用 frame-rate vote、内容类型和节能策略变化。把构造时读到的 `Display.getRefreshRate()` 当作整个页面停留期的预算，会在自适应刷新设备上产生错判。API 31+ 优先使用 FrameMetrics 的 `DEADLINE` 或 JankStats 对当前帧给出的判定；低版本保留原始分布并通过同设备、同场景基线比较。

### API 33+ 用 VsyncCallback 保存 timeline 身份

API 33 增加 `Choreographer.VsyncCallback`。它提供多个候选 `FrameTimeline` 以及平台选择的 preferred timeline，其中包含 deadline、expected presentation time 和 VSync ID。`FrameData` 与内部 `FrameTimeline` 在回调外无效，必须在回调内复制基础数值。

下面的代码保存当前 preferred timeline 的四个标量，供诊断窗口与其他帧记录对时。

```kotlin
@RequiresApi(33)
@MainThread
class VsyncTimelineProbe(
    private val ringBuffer: TimelineRingBuffer
) : Choreographer.VsyncCallback {
    private val choreographer = Choreographer.getInstance()
    private var running = false

    fun start() {
        if (running) return
        running = true
        choreographer.postVsyncCallback(this)
    }

    fun stop() {
        if (!running) return
        running = false
        choreographer.removeVsyncCallback(this)
    }

    override fun onVsync(data: Choreographer.FrameData) {
        if (!running) return

        val timeline = data.preferredFrameTimeline
        ringBuffer.offer(
            frameTimeNanos = data.frameTimeNanos,
            deadlineNanos = timeline.deadlineNanos,
            expectedPresentationTimeNanos = timeline.expectedPresentationTimeNanos,
            vsyncId = timeline.vsyncId
        )

        if (running) choreographer.postVsyncCallback(this)
    }
}
```

deadline 是帧需要 ready 的时间戳，回调刚开始时还没有完成时间，所以上述探针不能在 `onVsync()` 内判定本帧是否超期。VSync ID 的用途是关联同一帧的 FrameMetrics、SurfaceFlinger 数据或自建 `SurfaceControl.Transaction`，并不等同于“该帧已经显示”。

## JankStats：线上默认入口

JankStats 按 `Window` 跟踪帧，并把帧数据与 `PerformanceMetricsState` 中的 UI 状态一同交给监听器。API 16—23 使用较粗的 timing 估计；API 24+ 依赖平台 FrameMetrics，时长更可信；API 31+ 又增加 CPU、CPU + GPU 总时长与 overrun 信息。适用范围为 Android 10—17，但服务端仍应带上 `api_level` 和 timing capability，不能把不同能力层的数据直接混成一条基线。

常用字段的含义要分开：

| 类型 | 字段 | 含义 |
|---|---|---|
| `FrameData` | `frameDurationUiNanos` | UI 线程部分，不能代表 RenderThread 或 GPU 总时长 |
| `FrameDataApi24` | `frameDurationCpuNanos` | 非 GPU 的 CPU 部分 |
| `FrameDataApi31` | `frameDurationTotalNanos` | CPU 与 GPU 合计的帧时长 |
| `FrameDataApi31` | `frameOverrunNanos` | 相对 deadline 的超期量；正值表示超期，负值表示提前完成 |
| 所有可用层级 | `isJank` | JankStats 按平台能力与 heuristic 得出的判定 |

`createAndTrack(window)` 要求 Window 已处于 active 状态且 DecorView 非空，因此应在 `setContentView()` 之后创建。实例创建后默认开始跟踪；页面不可见时关闭，恢复可见时再启用。

这段接入骨架保留原始 `FrameData` 子类型。监听器收到对象后立即调用 `copy()`，因为原对象会被后续帧复用；`frameQueue.offer()` 必须是有界、非阻塞且线程安全的写入。

```kotlin
class FeedActivity : AppCompatActivity() {
    private lateinit var jankStats: JankStats
    private lateinit var stateHolder: PerformanceMetricsState.Holder

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_feed)

        val content = findViewById<View>(android.R.id.content)
        stateHolder = PerformanceMetricsState.getHolderForHierarchy(content)
        jankStats = JankStats.createAndTrack(window) { volatileFrameData ->
            val snapshot = volatileFrameData.copy()
            frameQueue.offer(
                page = "feed",
                apiLevel = Build.VERSION.SDK_INT,
                frameData = snapshot
            )
        }
    }

    override fun onResume() {
        super.onResume()
        jankStats.isTrackingEnabled = true
    }

    override fun onPause() {
        jankStats.isTrackingEnabled = false
        frameQueue.flushAsync(reason = "activity_paused")
        super.onPause()
    }

    fun onFeedScrollStateChanged(scrollState: Int) {
        val state = stateHolder.state ?: return
        when (scrollState) {
            RecyclerView.SCROLL_STATE_DRAGGING ->
                state.putState("feed_list", "dragging")
            RecyclerView.SCROLL_STATE_SETTLING ->
                state.putState("feed_list", "settling")
            else ->
                state.removeState("feed_list")
        }
    }
}
```

JankStats 的监听线程随 API 层级变化：API 23 及以下通常是 Main/UI 线程，API 24+ 是内部 FrameMetrics 线程。队列和聚合器不能假设回调总在主线程，也不能在回调中访问只允许 UI 线程读取的业务对象。把页面、组件和交互状态提前写入 `PerformanceMetricsState`，回调只复制快照。

状态标签应采用低基数枚举，例如 `page=feed`、`feed_list=settling`。列表 position、搜索词、URL、订单号和用户输入会造成高基数与隐私风险，不应进入帧标签。每个临时状态都要有对应的 `removeState()`；否则后续帧会携带已经失效的上下文。

JankStats 的默认 jank heuristic multiplier 是产品口径的一部分。线上修改它会改变趋势，调整时必须登记策略版本并建立新基线。更合适的上报方式是保留 `isJank`，同时按能力层记录 UI duration、CPU duration、total duration、overrun 和状态；服务端可以在不篡改客户端原判定的前提下分析严重程度。

## FrameMetrics：拆分 Window 帧的应用侧阶段

JankStats 已能覆盖多数线上趋势。某个页面出现稳定回归后，可以按远程配置对少量会话开启 FrameMetrics，补充阶段耗时和 VSync ID。字段按平台版本分层：

- API 24+：`UNKNOWN_DELAY_DURATION`、`INPUT_HANDLING_DURATION`、`ANIMATION_DURATION`、`LAYOUT_MEASURE_DURATION`、`DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION`、`SWAP_BUFFERS_DURATION`、`TOTAL_DURATION`、`FIRST_DRAW_FRAME`。
- API 26+：`INTENDED_VSYNC_TIMESTAMP` 与 `VSYNC_TIMESTAMP`。两者不同表示 UI 线程未及时响应原定 VSync。
- API 31+：`GPU_DURATION` 与 `DEADLINE`。`DEADLINE` 是系统给应用产出该帧的总时间预算，单位是时长。
- API 36+：`FRAME_TIMELINE_VSYNC_ID`，用于关联 compositor timeline。

API 31+ 可计算 `TOTAL_DURATION - DEADLINE`。结果大于零表示应用没有命中该帧预算；结果小于零表示仍有余量。API 29 / 30 没有 `DEADLINE`，`getMetric()` 对不支持的 id 返回 `-1`。这一层不要用某个固定 refresh rate 制造一条“精确 deadline”，应使用 JankStats 判定、同场景分布与 Perfetto 复核。

`Window.OnFrameMetricsAvailableListener` 把回调投递到注册时指定的 `Handler`。回调中的 `FrameMetrics` 会复用，必须当场构造副本。第三个参数是上次回调以来丢失的**指标报告数**，说明监控消费者跟不上；它不是用户侧掉帧数。

下面的诊断会话让复制和聚合都运行在专用 HandlerThread，不再把副本二次 `post` 到同一线程。

```kotlin
@RequiresApi(24)
class WindowFrameMetricsSession(
    private val aggregator: FrameMetricsAggregator
) : Closeable {
    private val thread = HandlerThread("window-frame-metrics").apply { start() }
    private val handler = Handler(thread.looper)
    private var window: Window? = null

    private val listener = Window.OnFrameMetricsAvailableListener {
            _, volatileMetrics, droppedReports ->
        val snapshot = FrameMetrics(volatileMetrics)
        aggregator.add(
            metrics = snapshot,
            telemetryReportsDropped = droppedReports
        )
    }

    fun start(target: Window) {
        check(window == null)
        window = target
        target.addOnFrameMetricsAvailableListener(listener, handler)
    }

    override fun close() {
        val target = window ?: return
        window = null
        target.removeOnFrameMetricsAvailableListener(listener)
        handler.post {
            aggregator.flush()
            thread.quitSafely()
        }
    }
}
```

`telemetryReportsDropped` 要独立上报并进入 coverage 计算。数值升高通常说明监听器或下游聚合过重，此时采样数据本身已经有偏，不能用剩余报告推算完整 jank rate。

`FIRST_DRAW_FRAME` 通常不进入滚动或动画 jank 分母，但这类帧不能直接丢弃。把它们放进 startup / navigation 首帧桶，交给 21.8 或 26.3 的启动与页面切换指标分析。`TOTAL_DURATION` 也只覆盖应用渲染到提交显示子系统的阶段；即使它小于 `DEADLINE`，需要 compositor 侧证据才能解释最终 present。

## API 36+：把 FrameMetrics 与 compositor jank 对齐

API 36 起，`Window.getRootSurfaceControl()` 返回的 `AttachedSurfaceControl` 可以注册 `SurfaceControl.OnJankDataListener`。SurfaceFlinger 会异步、批量回传每帧分类：

- `JANK_APPLICATION`：应用错过调度；
- `JANK_COMPOSER`：composer 错过调度；
- `JANK_OTHER`：其他系统组件导致；
- `JANK_NONE`：按期完成。

`JankData.getVsyncId()` 可以与 `FrameMetrics.FRAME_TIMELINE_VSYNC_ID` 连接。`scheduledAppFrameTimeNanos` 是系统分配给应用的时长，可能因 CPU/GPU 并行而大于 display frame interval；`actualAppFrameTimeNanos` 是应用完成该帧所用时长。

下面的会话把 compositor 数据写入有界队列。停止时传入诊断窗口内记录到的有效 VSync ID，可以等待该帧的延迟分类送达；若无需等待，`removeAfter(0)` 会立即移除监听器。

```kotlin
@RequiresApi(36)
class CompositorJankSession(
    window: Window,
    executor: Executor,
    private val sink: CompositorJankSink
) {
    private val registration =
        checkNotNull(window.rootSurfaceControl) {
            "Call after setContentView() while the Window is attached"
        }.registerOnJankDataListener(executor) { batch ->
            batch.forEach { data ->
                sink.offer(
                    vsyncId = data.vsyncId,
                    jankType = data.jankType,
                    scheduledAppTimeNanos = data.scheduledAppFrameTimeNanos,
                    actualAppTimeNanos = data.actualAppFrameTimeNanos
                )
            }
        }

    fun stopAfter(lastVsyncId: Long?) {
        registration.flush()
        registration.removeAfter(lastVsyncId?.takeIf { it > 0L } ?: 0L)
    }
}
```

`flush()` 可能触发 in-band 回调，`sink` 仍需线程安全。注册对象也要由页面或诊断会话强引用，直到停止完成。

这一组 API 适合标准 App Window。页面里的 SurfaceView、Camera、视频、WebView renderer 或引擎可能拥有独立 buffer layer；宿主 root surface 的分类不能自动覆盖每条独立内容流。遇到“Window 指标正常、内容仍跳动”，需要回到目标 layer 的 producer、BufferQueue、fence、FrameTimeline 和 present-to-present 间隔。

## Android 17 的 buffer-stuffing recovery 会制造主动延迟

Android 17 的 `Choreographer` 源码包含 buffer-stuffing recovery。BLAST producer 等待 buffer release 的时间超过半个 frame interval 后，`onWaitForBufferRelease()` 会标记 stuffed 状态；后续 `doFrame()` 可以主动推迟一帧，降低排队 buffer 数，并在恢复期调整 animation timeline。相关 aconfig flag 会影响同一段动画能否多次恢复以及累计主动延迟上限，设备取值需要从 trace 或配置确认。

Perfetto 中出现 `Buffer stuffing recovery`、`buffer stuffed` 或 `Negative offset` 时，这一帧的迟到可能是系统为了排空队列而安排的恢复动作。归因时应同时检查 `dequeueBuffer` wait、queued buffer、FrameTimeline 的 `Buffer Stuffing` 分类及恢复后的 backlog。只看 UI/CPU duration 就把责任分给业务代码，会漏掉队列已经过深这一前因。

该机制处理排队造成的额外延迟，不会提升 GPU 或显示吞吐。若恢复频繁出现，还要追查 producer 产出节奏、RenderThread/GPU 完成时间、release fence 和 consumer 释放速度。

## 线上卡顿堆栈：按策略采样，给指标补代码现场

帧指标告诉我们异常发生在哪个时间段和阶段，Java 堆栈用于识别当时执行的方法。常见入口有两类：

- Looper dispatch 超时：记录一次主线程 message 的开始、结束和超时样本。`Looper.setMessageLogging()` 只有一个 Printer 槽位，接入前要评估与调试器、其他 SDK 的冲突，卸载时也不能误清掉别人的 Printer。
- 慢帧簇触发：JankStats 或 FrameMetrics 在短窗口内连续超期后，从后台线程按间隔读取主线程 Java 栈。

`Thread.getStackTrace()` 会暂停并遍历目标线程，采得太密也会扰动现场。它只能看到采样瞬间的 Java 栈；native 执行、GPU、SurfaceFlinger、fence 和 scheduler 原因需要 Perfetto 或更受控的 native profiling。线上采样必须有发布构建开关、会话采样率、冷却时间、单次样本数、栈深、报告字节数和全局日配额。

下面的采样器不提供通用默认阈值。所有上限都来自带版本号的远程策略，并在 `finally` 中恢复状态；`close()` 用于结束会话持有的执行器。

```kotlin
data class StackSamplingPolicy(
    val windowMillis: Long,
    val intervalMillis: Long,
    val maxSamples: Int,
    val maxDepth: Int
) {
    init {
        require(windowMillis > 0)
        require(intervalMillis > 0)
        require(maxSamples > 0)
        require(maxDepth > 0)
    }
}

class MainThreadStackSampler(
    private val mainThread: Thread,
    private val reporter: (StackSampleBatch) -> Unit
) : Closeable {
    private val executor = Executors.newSingleThreadExecutor()
    private val sampling = AtomicBoolean(false)

    fun sampleWindow(reason: String, policy: StackSamplingPolicy) {
        if (!sampling.compareAndSet(false, true)) return

        executor.execute {
            try {
                val deadline = SystemClock.uptimeMillis() + policy.windowMillis
                val samples = ArrayList<StackSample>(policy.maxSamples)

                while (
                    samples.size < policy.maxSamples &&
                    SystemClock.uptimeMillis() < deadline
                ) {
                    val frames = mainThread.stackTrace
                        .asSequence()
                        .take(policy.maxDepth)
                        .map(StackTraceElement::toString)
                        .toList()

                    samples += StackSample(
                        uptimeMillis = SystemClock.uptimeMillis(),
                        frames = frames
                    )
                    SystemClock.sleep(policy.intervalMillis)
                }

                reporter(StackSampleBatch(reason, samples))
            } finally {
                sampling.set(false)
            }
        }
    }

    override fun close() {
        executor.shutdown()
    }
}
```

端侧应把连续样本按方法序列生成稳定签名，同一 `app_version + page + ui_state + signature` 只上传少量代表样本。重复命中同一栈的价值高于一次偶发快照；多个样本分别落在 binder proxy、锁等待和业务方法时，应保留分布，不能强行选一个栈当根因。

报告不得携带完整 URL、搜索词、聊天内容、订单号、地理位置或可还原用户身份的数据。业务上下文使用枚举；方法名需要混淆映射时，在服务端按受控 mapping file 解析。

## 从指标到归因

服务端以“版本 + 设备层级 + 页面 + 交互状态 + Surface 拓扑 + 证据范围”为基本分组。平均 FPS 会掩盖偶发长帧和连续慢帧簇，至少要保留帧数、jank 数、overrun 分布、最长连续 jank 数、阶段分布与监控丢数。

| 现象组合 | 当前证据支持的判断 | 下一步 |
|---|---|---|
| `frameDurationUiNanos`、layout/draw 高，重复 Java 栈落在业务代码 | UI 线程工作量或阻塞可疑 | 检查布局、绘制、锁、Binder、I/O 与调用方 |
| UI 时长低，`frameDurationCpuNanos` 高 | RenderThread、native 或其他 CPU 阶段可疑 | 对齐 DrawFrame、sync、command issue 与线程调度 |
| CPU 阶段按时，`GPU_DURATION` 高 | GPU workload、driver、频率或带宽可疑 | 采 GPU slice/counter、频率、thermal 与 fence |
| FrameMetrics 超期且 `JANK_APPLICATION` | 应用侧 deadline miss 有 compositor 佐证 | 用同一 VSync ID 串起阶段和堆栈 |
| FrameMetrics 按时且 `JANK_COMPOSER` | SF/HWC/显示侧可疑 | 查看 SF scheduling、composition、HWC 与 present |
| 宿主 Window 正常，独立内容停顿 | 当前 Window 指标覆盖不足 | 找到内容 layer 与 producer，检查独立时间线 |
| `Buffer stuffing recovery` 与 queue backlog 同时出现 | 系统正在主动排队恢复 | 追查 backlog 来源和 release fence |
| `telemetryReportsDropped` 升高 | 监控消费者过重或队列容量不足 | 降低采样、缩短回调、修复 coverage 后再比较 |

主线程处于等待态时，栈顶只是等待位置。若 trace 显示线程 runnable 却长期没有获得 CPU，进入 `android17-6.18-2026-06_r6` 的 scheduler 证据；若 `dequeueBuffer` 或 buffer 复用被 fence 卡住，检查 dma-fence / sync_file 与 vendor GPU、display driver。只有在应用层证据指向这些方向时才下沉，避免从一个 Java 样本直接猜内核原因。

## 自动告警：用策略、基线和置信度约束噪声

推荐的聚合字段如下：

| 字段组 | 字段示例 | 用途 |
|---|---|---|
| 版本 | `app_version`、`build_id`、`api_level` | 判断回归开始点与平台能力 |
| 设备 | `device_tier`、`soc_family`、`os_build`、`thermal_state` | 分离硬件、厂商和温控差异 |
| 场景 | `page`、`component`、`ui_state`、`rendering_topology` | 定位用户操作及 Surface 边界 |
| 帧分布 | `frame_count`、`jank_count`、`overrun_p50/p90/p99`、`max_jank_streak` | 描述频率、尾部与成簇程度 |
| 严重度 | `severe_overrun_count`、`severity_policy_version` | 使用项目自有、可追溯的严重帧定义 |
| 归因 | `stage_distribution`、`jank_type_mask`、`stack_signature` | 连接应用阶段、composer 分类与代码 |
| 质量 | `reports_expected`、`reports_received`、`reports_dropped`、`queue_rejected` | 判断样本是否具备可比性 |

若产品沿用 Android Vitals 的 frozen frame 名称，要把它当作外部指标口径单独保存。自研监控采用不同阈值时使用 `severe_overrun` 等名称并携带策略版本，避免两个系统都叫 frozen 却统计不同对象。

下面的规则展示告警需要哪些约束，变量由页面和设备层级对应的策略提供。

```text
group_by = [app_version, device_tier, page, ui_state, rendering_topology]
sample_users >= policy.min_users
coverage_rate >= policy.min_coverage
lower_confidence_bound(jank_rate - baseline_jank_rate)
    >= policy.min_absolute_regression
relative_jank_rate >= baseline_jank_rate * policy.min_relative_regression
overrun_p99 >= baseline_overrun_p99 + policy.min_p99_regression
```

这条规则同时要求样本量、监控覆盖、绝对劣化、相对劣化和尾部分布变化。低流量页面可以采用更长观察窗或贝叶斯/分层模型，不能沿用高流量首页的瞬时阈值。告警命中后附上策略版本、基线窗口、置信区间、top device、top state、jank type、阶段分布、栈签名及最近代码变更，负责人才能复现和验收。

## 端侧接入与验收清单

- 按 Window 创建 JankStats；页面不可见时关闭，恢复可见时启用。
- 在 JankStats 回调内立刻 `copy()`；队列有容量上限、非阻塞，并统计拒绝写入。
- UI 状态使用低基数枚举，状态结束时移除，不采集用户内容。
- API 31+ 用 `TOTAL_DURATION` 与 `DEADLINE` 判断应用侧超期；低版本不伪造精确 deadline。
- FrameMetrics 复制对象后再处理；`dropCountSinceLastInvocation` 记作监控报告丢失。
- API 36+ 通过 VSync ID 关联 FrameMetrics 与 `JankData`，并处理批量、延迟回调。
- 页面含独立 Surface 时登记 `rendering_topology`，为内容 layer 补充对应证据。
- FrameCallback/VsyncCallback 只在短诊断窗口运行，回调只写预分配内存。
- 堆栈采样具有远程开关、版本化策略、冷却时间、大小与隐私限制。
- 告警按版本、设备层级、页面、状态和 Surface 拓扑分组，先检查 coverage 再判断趋势。
- 线下回放至少验证一个 UI 线程、一个 RenderThread/GPU、一个 compositor 以及一个独立 Surface 场景。
- Android 17 trace 中出现 buffer-stuffing recovery 时，把主动恢复和原始 backlog 分开解释。

验收目标是一条可以复核的证据链：异常属于哪个 Window 或 Surface、哪一组用户和交互状态、应用是否超过 deadline、compositor 怎样分类、哪一段耗时或代码栈重复出现。具备这些信息后，问题才能稳定分派，修复也能用同一口径验证。

## 从监控告警回到一次可复核的渲染复盘

案例不再单独汇编，而是用同一份复盘契约回流到监控闭环。每次问题至少保留以下字段：

| 字段 | 必填内容 |
| --- | --- |
| 用户场景 | 页面、操作、数据规模、前后台、窗口模式 |
| 样本条件 | app commit、构建类型、设备/系统、刷新率、温控、网络与缓存冷热 |
| 现象 | deadline miss 分布、JankStats state、首个异常时间点 |
| 分层证据 | 主线程、RenderThread/GPU、BufferQueue、SurfaceFlinger/HWC 各自的正常与异常证据 |
| 根因 | 最早偏离预期时间线的对象，以及排除过的相邻候选 |
| 改动 | 只改变的变量、降级与回滚开关 |
| 验收 | 相同脚本下的 P50/P90/P95/P99、慢帧率、内存/功耗和视觉正确性 |

大型首页、复杂动画、图片列表和 WebView 的表象不同，复盘顺序相同：先由线上分桶找到稳定场景，再用 release-like Macrobenchmark 复现，最后在 Perfetto 中从异常 App SurfaceFrame/DisplayFrame 反向定位。一次 trace 只能解释一次执行，不能代替线上分布；全局平均 FPS 也不能证明某个局部修复有效。

结论必须写清“证据边界”。例如 `onDraw` 很长只能证明 UI 录制慢，`queueBuffer()` 返回只能证明 Producer 提交，某个 Composable 高频执行也不能证明它让帧错过 deadline。复盘关闭前还要把修复固化为自动化用户旅程、JankStats state、阈值与负责人；否则案例只是一次性的排障故事。

## 源码与文档索引

### Android 17 / API 37

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)：FrameCallback、VsyncCallback、FrameTimeline 与 buffer-stuffing recovery。
- [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：各阶段时长、`DEADLINE` 与 `FRAME_TIMELINE_VSYNC_ID`。
- [`SurfaceControl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java) 与 [`AttachedSurfaceControl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/AttachedSurfaceControl.java)：compositor jank 分类与注册接口。
- [JankStats 指南](https://developer.android.com/topic/performance/jankstats)、[JankStats API](https://developer.android.com/reference/androidx/metrics/performance/JankStats) 与 [`FrameDataApi31`](https://developer.android.com/reference/androidx/metrics/performance/FrameDataApi31)：Window 帧、状态、对象复用与 overrun。
- [`Choreographer` API](https://developer.android.com/reference/android/view/Choreographer)、[`FrameData`](https://developer.android.com/reference/android/view/Choreographer.FrameData) 与 [`FrameTimeline`](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline)：回调生命周期、deadline、expected presentation time 与 VSync ID。
- [`FrameMetrics` API](https://developer.android.com/reference/android/view/FrameMetrics)、[`OnFrameMetricsAvailableListener`](https://developer.android.com/reference/android/view/Window.OnFrameMetricsAvailableListener)、[`JankData`](https://developer.android.com/reference/android/view/SurfaceControl.JankData) 与 [`AttachedSurfaceControl`](https://developer.android.com/reference/android/view/AttachedSurfaceControl)：应用阶段、报告丢失和 compositor 分类。
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：expected/actual timeline、SurfaceFrame 与 DisplayFrame 的线下核对方法。

### Kernel `android17-6.18-2026-06_r6`

- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c)：UI/RenderThread runnable 与调度证据。
- [`drivers/dma-buf/dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)：GPU、HWC 与 buffer 生命周期相关的 fence 基础实现。
