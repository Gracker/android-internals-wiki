---
title: "帧率监控与线上卡顿治理"
chapter: "22.8"
section: "22.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
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
    path: "src/part3-tools/ch19-apm/11-jankstats.md"
  - type: aiw
    path: "src/part3-tools/ch19-apm/12-framemetrics.md"
  - type: aiw
    path: "src/part3-tools/ch19-apm/06-blockcanary.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [frame-rate, jankstats, choreographer, online-monitoring]
related_chapters: ["22.1", "22.3", "7.2", "7.9", "19.06", "19.11", "19.12", "26.3"]
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
---

# 帧率监控与线上卡顿治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Choreographer.FrameCallback 帧率采集
- 🔹 JankStats API 集成
- 🔹 线上卡顿堆栈采集方案
- 🔹 卡顿归因与自动告警

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

22.8 节讲应用侧怎样在线上发现、聚合、定位卡顿。7.2 节已经讲过卡顿成因，19.11 和 19.12 节分别介绍了 JankStats、FrameMetrics。这里的目标是把工具接入转成可执行的线上流程：采什么字段、怎样降噪、怎样把一组慢帧转成可分派的问题。


## 监控数据的三层口径

帧率监控容易写成一个 FPS 数字，但线上治理靠单一 FPS 很难分派。一个页面平均 55 FPS，可能是每秒稳定丢 5 帧，也可能是一次 300 ms 卡住后其余时间满帧。两者对用户的感受和修复方向完全不同。

建议把数据拆成三层：

| 层级 | 采集对象 | 适合回答的问题 | 典型工具 |
|------|----------|----------------|----------|
| 帧节奏 | 每帧开始时间、帧间隔、慢帧数量 | 哪个页面、哪个版本、哪类设备慢帧率升高 | `Choreographer.FrameCallback`、JankStats |
| 阶段耗时 | input、animation、layout、draw、sync、GPU、deadline | 慢在主线程布局、绘制、GPU，还是 deadline 未命中 | FrameMetrics、JankStats API 31+ 字段 |
| 代码上下文 | 主线程堆栈、业务场景、网络/数据状态、页面状态 | 该分给哪个模块、哪个责任人，复现路径是什么 | Looper block 监控、采样堆栈、业务埋点 |

`Choreographer.FrameCallback` 适合低成本记录节奏；JankStats 适合把帧耗时和 UI 状态绑定；FrameMetrics 适合把一帧拆成阶段。三者不是互斥关系。线上默认用 JankStats 聚合，命中阈值后再按采样率启用 Looper 堆栈或 FrameMetrics，会比所有用户全量采堆栈更稳。

[已验证: 官方文档, developer.android.com/topic/performance/jankstats]
[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

## Choreographer.FrameCallback 帧率采集

`Choreographer` 接收显示系统的 VSync 节奏，并把 input、animation、traversal 等工作安排到下一帧。`postFrameCallback()` 注册的回调只执行一次，执行后会自动移除；要持续采集，回调里需要再次注册自己。`FrameCallback.doFrame(frameTimeNanos)` 运行在该 `Choreographer` 绑定的 `Looper` 线程上，通常是主线程。

[已验证: 官方文档, developer.android.com/reference/android/view/Choreographer]
[已验证: AOSP android-16.0.0_r1, `frameworks/base/core/java/android/view/Choreographer.java`]

这类采集只做帧节奏和慢帧计数，不要在回调里做聚合、序列化或网络上报。回调本身跑在渲染节奏里，写重了会制造新的卡顿。

这段代码演示最小采集器：记录相邻帧的 `frameTimeNanos` 差值，按当前刷新率推导预算，并把结果写入内存窗口。

```kotlin
class FrameCadenceSampler(
    private val displayRefreshHz: Float,
    private val sink: (FrameSample) -> Unit
) : Choreographer.FrameCallback {
    private val choreographer = Choreographer.getInstance()
    private var lastFrameTimeNanos: Long = 0L
    private var running = false

    fun start() {
        if (running) return
        running = true
        choreographer.postFrameCallback(this)
    }

    fun stop() {
        running = false
        choreographer.removeFrameCallback(this)
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running) return

        val previous = lastFrameTimeNanos
        lastFrameTimeNanos = frameTimeNanos
        if (previous != 0L) {
            val frameIntervalNanos = frameTimeNanos - previous
            val budgetNanos = (1_000_000_000f / displayRefreshHz).toLong()
            val skippedFrames = (frameIntervalNanos / budgetNanos - 1).coerceAtLeast(0)
            sink(FrameSample(frameTimeNanos, frameIntervalNanos, skippedFrames))
        }

        choreographer.postFrameCallback(this)
    }
}

data class FrameSample(
    val frameTimeNanos: Long,
    val frameIntervalNanos: Long,
    val skippedFrames: Long
)
```

`frameTimeNanos` 表示这一帧被调度开始的稳定时间基准，不等于本帧完成时间。它能帮助估算帧间隔和跳过了多少个 VSync，但不能告诉你慢在 Measure、Draw 还是 GPU。阶段归因要交给 FrameMetrics 或线下 Perfetto。

[已验证: 官方文档, developer.android.com/reference/android/view/Choreographer.FrameCallback]

线上接入时要处理三个边界：

- **刷新率不能写死**：60 Hz 设备预算约 16.67 ms，120 Hz 设备预算约 8.33 ms。阈值应从当前 display refresh rate 或 JankStats 提供的 expected duration 口径推导。
- **后台页面要停采**：Activity `onPause()` 后停止回调，避免后台 Window 产生无意义数据，也避免持有 Activity。
- **只上传窗口聚合**：端侧按 10-30 秒或一次页面停留聚合 `frame_count`、`slow_frame_count`、`frozen_frame_count`、P90/P99 间隔，不逐帧上传。

## JankStats API 集成

JankStats 是 AndroidX 提供的帧级卡顿采集入口。它按 `Window` 创建实例，每帧通过 `OnFrameListener` 回调 `FrameData`，字段包含 `isJank`、`frameDurationUiNanos`、`frameStartNanos` 和当前 UI 状态。API 24 及以上可以借助平台 FrameMetrics 获取更可靠的帧时间，API 31 及以上还提供 `frameOverrunNanos` 等字段。详见 19.11 节。

[已验证: 官方文档, developer.android.com/reference/androidx/metrics/performance/JankStats]
[已验证: AIW 19.11]

JankStats 的价值在于把卡顿判定和页面状态绑在一起。没有状态标签的慢帧只会变成“首页慢帧率升高”；加上状态标签后，才能拆成“首页 feed 列表 settling 阶段慢帧率升高”“商品详情大图加载时 `frameOverrunNanos` 升高”。

这段接入骨架展示三个关键点：按 Window 创建、生命周期启停、在回调里复制字段后交给后台聚合。`frameAggregator` 和 `JankFrameEvent` 是业务侧自定义聚合器与数据对象。

```kotlin
class FeedActivity : AppCompatActivity() {
    private lateinit var jankStats: JankStats
    private lateinit var metricsStateHolder: PerformanceMetricsState.Holder

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_feed)

        metricsStateHolder = PerformanceMetricsState.getHolderForHierarchy(
            findViewById(android.R.id.content)
        )
        jankStats = JankStats.createAndTrack(window) { frameData ->
            frameAggregator.enqueue(
                JankFrameEvent(
                    page = "feed",
                    startNanos = frameData.frameStartNanos,
                    durationUiNanos = frameData.frameDurationUiNanos,
                    isJank = frameData.isJank,
                    states = frameData.states.associate { it.key to it.value }
                )
            )
        }
    }

    override fun onResume() {
        super.onResume()
        jankStats.isTrackingEnabled = true
    }

    override fun onPause() {
        frameAggregator.flush(reason = "activity_paused")
        jankStats.isTrackingEnabled = false
        super.onPause()
    }

    fun onFeedScrollStateChanged(state: Int) {
        val metricsState = metricsStateHolder.state ?: return
        when (state) {
            RecyclerView.SCROLL_STATE_DRAGGING -> metricsState.putState("feed_list", "dragging")
            RecyclerView.SCROLL_STATE_SETTLING -> metricsState.putState("feed_list", "settling")
            else -> metricsState.removeState("feed_list")
        }
    }
}
```

官方文档提醒两件事：`OnFrameListener` 会按帧触发，回调线程取决于平台能力；`FrameData` 对象会复用，回调返回后应视为过期。代码里要复制需要的字段，立刻返回，再由后台线程按页面和时间窗口聚合。

[已验证: 官方文档, developer.android.com/topic/performance/jankstats]

JankStats 的阈值口径也要进入配置系统。默认启发式会用当前刷新率的倍数判断 jank；测试场景可以调 `jankHeuristicMultiplier`，线上不要为了“数字好看”随意放宽阈值。更稳的做法是保留官方 `isJank`，同时上报原始 duration、overrun、refresh rate 和页面状态，让服务端按业务场景做二次分析。

## [自动发现] FrameMetrics 负责阶段归因

当 JankStats 报告某个页面慢帧率升高，但没有足够信息判断原因时，可以对小流量打开 FrameMetrics。`FrameMetrics` 提供多种阶段耗时字段，按 API 级别分层：

- **API 24+**（基础指标）：`UNKNOWN_DELAY_DURATION`、`INPUT_HANDLING_DURATION`、`ANIMATION_DURATION`、`LAYOUT_MEASURE_DURATION`、`DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION`、`TOTAL_DURATION`、`FIRST_DRAW_FRAME` 等。
- **API 31+**（扩展指标）：`GPU_DURATION`（GPU 渲染耗时）、`DEADLINE`（系统给应用生成该帧的时间预算）。Android 10 / 11 上调用 `FrameMetrics.getMetric()` 传入这两个 id 会返回 `-1`，不能用于 GPU 阶段归因和 deadline miss 统计。

API 29 / 30 的帧预算判断可以用 `TOTAL_DURATION`、`VSYNC_TIMESTAMP` / `INTENDED_VSYNC_TIMESTAMP`、当前刷新率预算或 `JankStats` 的 `isJank` 口径兜底。详见 19.12 节。[已验证: AOSP `FrameMetrics.java`, Added in API level 标注]

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]
[已验证: AOSP android-16.0.0_r1, `frameworks/base/core/java/android/view/FrameMetrics.java`]
[已验证: AIW 19.12]

`Window.OnFrameMetricsAvailableListener` 的文档要求回调里尽快复制 `FrameMetrics`，再把计算和存储转到其他线程；回调如果执行过慢，生产者不会等待消费者，报告可能被丢弃。

```kotlin
private val metricsThread = HandlerThread("frame-metrics").apply { start() }
private val metricsHandler = Handler(metricsThread.looper)
private val frameMetricsListener = Window.OnFrameMetricsAvailableListener { _, metrics, dropped ->
    val snapshot = FrameMetrics(metrics)
    metricsHandler.post {
        frameMetricsAggregator.add(snapshot, dropped)
    }
}

fun startFrameMetrics(window: Window) {
    window.addOnFrameMetricsAvailableListener(frameMetricsListener, metricsHandler)
}

fun stopFrameMetrics(window: Window) {
    window.removeOnFrameMetricsAvailableListener(frameMetricsListener)
    metricsHandler.post { frameMetricsAggregator.flush() }
}
```

FrameMetrics 更适合短期开关、灰度诊断和重点页面，不建议全量长期保留每帧明细。端侧可以只保留阶段 P90/P99、超过 deadline 的帧数、`FIRST_DRAW_FRAME` 过滤后的慢帧数，以及异常窗口里的少量样本。

[已验证: 官方文档, developer.android.com/reference/android/view/Window.OnFrameMetricsAvailableListener]

## 线上卡顿堆栈采集方案

帧级指标告诉你“慢了”，堆栈采样帮助判断“慢在哪里”。线上常用方案分两类：

- **Looper message 超时**：监控主线程一次 message dispatch 的开始和结束，如果超过阈值，记录 message、耗时、页面状态和主线程堆栈。BlockCanary 这类工具属于这个思路，现代项目可以保留原理，重新实现轻量版本。详见 19.06 节。
- **慢帧窗口采样**：JankStats 或 FrameMetrics 发现连续慢帧后，在 1-3 秒窗口内按固定间隔采主线程栈，再和页面状态、线程 CPU、内存水位一起上报。

[已验证: AIW 19.06]

采样线程不能阻塞主线程。主线程已经在执行慢任务时，后台线程读取 `mainThread.stackTrace` 能拿到 Java 堆栈快照；Native 堆栈、锁等待、Binder 等待需要更重的方案，线上要按采样率和开关控制。

这段伪代码展示慢帧触发后的短窗口采样。它不在每帧回调里抓栈，只在命中条件后启动后台任务；`StackSample` 和 `StackSampleBatch` 是业务侧自定义数据对象。

```kotlin
class MainThreadStackSampler(
    private val mainThread: Thread,
    private val reporter: (StackSampleBatch) -> Unit
) {
    private val executor = Executors.newSingleThreadExecutor()
    private val enabled = AtomicBoolean(false)

    fun sampleWindow(reason: String, durationMillis: Long = 2_000L, intervalMillis: Long = 80L) {
        if (!enabled.compareAndSet(false, true)) return

        executor.execute {
            val startedAt = SystemClock.uptimeMillis()
            val samples = mutableListOf<StackSample>()
            while (SystemClock.uptimeMillis() - startedAt < durationMillis) {
                samples += StackSample(
                    uptimeMillis = SystemClock.uptimeMillis(),
                    frames = mainThread.stackTrace.take(40).map(StackTraceElement::toString)
                )
                SystemClock.sleep(intervalMillis)
            }
            enabled.set(false)
            reporter(StackSampleBatch(reason, samples))
        }
    }
}
```

堆栈报告要裁剪。建议只保留前 30-50 层，过滤框架重复帧，按方法签名做本地聚合；同一页面同一版本同一签名只上传少量样本。涉及 URL、用户输入、订单号、地理位置等字段时，只保留枚举状态或脱敏后的业务标签。

## 卡顿归因与自动告警

线上治理建议以“页面 + 场景 + 阶段 + 堆栈签名”作为分派单元，而不是从单帧日志开始。服务端可以按以下字段聚合：

| 字段 | 用途 |
|------|------|
| `app_version` / `build_id` | 判断是否由新版本引入 |
| `device_model` / `soc` / `os_version` / `refresh_rate` | 区分低端机、厂商 ROM、高刷新率设备 |
| `page` / `component` / `ui_state` | 定位页面和交互阶段 |
| `frame_count` / `jank_count` / `frozen_count` | 计算慢帧率和严重卡顿率 |
| `p50` / `p90` / `p99` / `max_overrun` | 保留分布，不被平均值掩盖 |
| `stage_top` | 标记 layout、draw、GPU、input 等主导阶段 |
| `stack_signature` | 聚合同一类主线程阻塞 |
| `network_state` / `thermal_state` / `battery_saver` | 排除环境因素或形成设备画像 |

告警不要只看绝对阈值。一个低频页面慢帧率从 1% 到 4% 可能样本太少；首页 feed 从 3% 到 4.5% 可能已经影响大量用户。更稳的策略是同时看四个条件：样本量达标、相比基线劣化、影响用户数超过阈值、分布尾部变差。

可执行的告警规则示例：

```text
page = feed
and app_version = 8.12.0
and sample_users >= 5000
and jank_rate_p90_by_device_tier >= baseline * 1.3
and frozen_frame_rate >= baseline + 0.2%
and top_state in ["feed_list:settling", "feed_card:bind"]
```

这条规则不会因为少量测试设备误报，也不会被平均 FPS 掩盖。命中后，系统把报告分派给 `feed` 页面负责人，并附上 `top_device`、`top_state`、`top_stack_signature`、FrameMetrics 阶段分布和最近一次版本变更。

归因时要避免三类常见误判：

- **把首帧慢当滑动卡顿**：`FrameMetrics.FIRST_DRAW_FRAME` 标记的帧通常不纳入动画卡顿统计。启动和页面切换应进入 21.8 或 26.3 的指标体系。
- **把高刷新率设备按 16 ms 判断**：120 Hz 设备上 12 ms 已经可能错过当前帧 deadline；阈值必须绑定 refresh rate 或 deadline。
- **只看主线程堆栈**：主线程可能只是在等锁、等 Binder、等 I/O；归因时要结合线程 CPU、锁等待、Binder 调用和 Perfetto 样本。22.1、22.3、22.5 已分别覆盖布局、Compose、动画场景，本节只给线上聚合入口。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

## 端侧接入清单

上线前按这份清单检查：

- JankStats 按 Window 创建，Activity `onResume()` 启用、`onPause()` 停止并 flush。
- UI 状态至少包含 page、列表滚动状态、弹窗、加载态、关键业务组件；状态结束时必须 remove。
- 端侧只做窗口聚合，默认不上报逐帧明细。
- 慢帧触发堆栈采样时有远程开关、采样率、冷却时间和单次报告大小限制。
- 阈值按 refresh rate、deadline 或 JankStats 口径计算，不写固定 16 ms。
- FrameMetrics 只在重点页面或灰度诊断打开，回调里复制对象后立即返回。
- 服务端按版本、设备、页面、状态、阶段、堆栈签名聚合，并保留基线对比。

帧率监控的完成标准不是页面上出现一个 FPS 浮层，而是能在新版本慢帧率升高时，把问题收敛到页面、场景、阶段和责任模块。能分派，才算进入治理。
