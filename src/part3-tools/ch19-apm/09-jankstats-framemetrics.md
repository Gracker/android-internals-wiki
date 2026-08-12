---

title: JankStats 与 FrameMetrics
chapter: '19'
section: '19.09'
status: "finalized"
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: '2026-05-31'
last_verified_against: AndroidX metrics-performance 1.0.0 JankStatsApi16/24/26/31 implementation + PerformanceMetricsState + AOSP FrameMetrics Android 11/12 DEADLINE boundary
confidence: medium
tags:
- apm
related_chapters:
- '19.0'
consolidated_from:
- "src/part3-tools/ch19-apm/12-framemetrics.md"
sources:
- type: official
  path: https://developer.android.com/reference/androidx/metrics/performance/JankStats
- type: official
  path: https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/maven-metadata.xml
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
---


# JankStats 与 FrameMetrics

## JankStats 是官方帧级卡顿入口

JankStats 属于 `androidx.metrics:metrics-performance`，用于按帧收集 UI jank 信息。Google Maven metadata 当前稳定版本为 `1.0.0`。这里复核的 AAR SHA-256 是 `efe2e0d92c7cb2f40c77d337052623fdb631d684ba145881e5a52a664d5614a0`，sources JAR SHA-256 是 `55c5478b4fde6e1cded38d647e9d995a6d9d08e3b8abd28268b5d5a5c3e700a2`。

它会把每帧耗时、是否被库判为 jank、当时的 UI 状态回调给应用，但不会自动上传数据。它适合作为线上流畅性监控的第一层信号源，不负责生成 trace、抓取堆栈或提供看板。它擅长回答“哪些页面、交互和版本的异常帧更多”，不能独立回答“哪段代码让这一帧超时”。

版本下限要区分源码和发布物。1.0.0 sources 保留 `JankStatsApi16Impl`，类注释也描述了 API 16+ 的 fallback；当前 1.0.0 AAR manifest 却明确声明 `minSdkVersion=23`。正常依赖解析应按发布物执行，因此新接入的最低系统是 Android 6（API 23），不应再把稳定 AAR 写成 API 16+。不建议用 manifest override 强行绕过这个限制。

## 它输出什么

回调参数的静态类型是 `FrameData`，运行时类型随系统版本变化：

| 运行时类型 | 系统路径 | 可读字段 |
|---|---|---|
| `FrameData` | API 23 的 pre-draw fallback | `frameStartNanos`、`frameDurationUiNanos`、`isJank`、`states` |
| `FrameDataApi24` | API 24-30 的 `FrameMetrics` 路径 | 再增加 `frameDurationCpuNanos` |
| `FrameDataApi31` | API 31-37 的 deadline 路径 | 再增加 `frameDurationTotalNanos`、`frameOverrunNanos` |

`frameDurationUiNanos` 是 UI 相关阶段的合计，不包含完整 RenderThread 和 GPU 时间。API 24-30 的 `frameDurationCpuNanos` 在 1.0.0 源码中直接取自 `FrameMetrics.TOTAL_DURATION`；API 31+ 才使用 `TOTAL_DURATION - GPU_DURATION + SWAP_BUFFERS_DURATION` 计算非 GPU 部分。跨版本聚合时必须携带 API level，不能假定同名字段在所有分支上来自同一套平台数据。

`frameOverrunNanos` 只在 API 31+ 提供，计算式是 `TOTAL_DURATION - DEADLINE`。正数表示总渲染时间越过 deadline，负数表示仍有余量。它与 `isJank` 不是同一个布尔口径，后文会解释两者为何可能不一致。

UI context 是 JankStats 相比直接使用 `Choreographer.FrameCallback` 更有价值的部分。只知道“异常帧发生了”还不够，线上还要知道它发生在哪个页面和交互阶段。

下面的 View 示例先创建 JankStats，再获取非空的 `PerformanceMetricsState`。这个顺序不能颠倒，因为 holder 的 `state` 由 JankStats 初始化：

```kotlin
class HomeActivity : AppCompatActivity() {
    private lateinit var jankStats: JankStats
    private var metricsState: PerformanceMetricsState? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        jankStats = JankStats.createAndTrack(window) { frameData ->
            val api24 = frameData as? FrameDataApi24
            val api31 = frameData as? FrameDataApi31
            val sample = JankFrameSample(
                isJank = frameData.isJank,
                frameDurationUiNanos = frameData.frameDurationUiNanos,
                frameDurationCpuNanos = api24?.frameDurationCpuNanos,
                frameDurationTotalNanos = api31?.frameDurationTotalNanos,
                frameOverrunNanos = api31?.frameOverrunNanos,
                states = frameData.states.associate { stateInfo -> stateInfo.key to stateInfo.value }
            )
            frameAccumulator.record(sample)
        }

        metricsState = checkNotNull(
            PerformanceMetricsState.getHolderForHierarchy(window.decorView).state
        ) {
            "PerformanceMetricsState is unavailable before JankStats is created"
        }
        metricsState?.putState("screen", "Home")
    }

    override fun onResume() {
        super.onResume()
        jankStats.isTrackingEnabled = true
    }

    override fun onPause() {
        jankStats.isTrackingEnabled = false
        super.onPause()
    }

    override fun onDestroy() {
        metricsState?.removeState("screen")
        super.onDestroy()
    }
}

data class JankFrameSample(
    val isJank: Boolean,
    val frameDurationUiNanos: Long,
    val frameDurationCpuNanos: Long?,
    val frameDurationTotalNanos: Long?,
    val frameOverrunNanos: Long?,
    val states: Map<String, String>
)
```

这段代码还保留了正常帧。只上报 `isJank=true` 的帧会丢失分母，服务端无法计算 jank rate。示例中的 `frameAccumulator.record()` 应只更新内存计数器和有界直方图；`associate` 是为了展示字段，流量较大时应改为按所需 key 读取，避免每帧创建 Map。

`createAndTrack()` 要求 `Window.peekDecorView()` 非空，因此应先通过 `setContentView()` 或其他方式建立 DecorView。条件不满足时，1.0.0 源码会直接抛出 `IllegalStateException`。

`OnFrameListener` 回调里的 `FrameData` 只适合做当前帧内的轻量处理。要把事件交给后台线程、批量聚合或异步上报时，先复制 `isJank`、`frameDurationUiNanos` 和 `states` 到自己的 DTO。不要把 `FrameData` 对象本身跨线程保存，也不要在回调里做同步 I/O 或复杂序列化。

如果希望保留完整的版本化字段，也可以在回调内调用 `frameData.copy()`；各子类会复制成对应的 `FrameDataApi24` 或 `FrameDataApi31`。这仍会产生每帧分配，不能无条件写入无界队列。

回调线程也有版本差异。API 23 的 `OnPreDrawListener` 运行在 UI 线程；API 24+ 的实现把 `FrameMetrics` listener 放在名为 `FrameMetricsAggregator` 的共享 `HandlerThread`。客户端不应依赖某条分支的线程身份，跨线程交接仍要使用有界结构。

状态关联依赖一条时间线。`PerformanceMetricsState.putState()` / `removeState()` 用 `System.nanoTime()` 记录每个 `StateInfo` 的添加和移除时间；JankStats 在生成 `FrameData` 时，用帧的 `[frameStart, frameEnd]` 区间调用 `getIntervalStates()` 做区间交集判断。`screen=Home`、`interaction=scroll` 等标签对应帧覆盖的状态区间，不只是回调发生瞬间的当前值。

## API 版本差异

JankStats 1.0.0 只有 API 16、24、26、31 四个实现类。当前 AAR 的 `minSdkVersion` 是 23，所以正常接入时会用到后三档加 API 23 fallback：

| Android 版本 | AndroidX 实现路径 | 行为 |
|---|---|---|
| API 23 | `JankStatsApi16Impl` | 用 `OnPreDrawListener` 估算帧时间，并反射 `Choreographer.mLastFrameTimeNanos`；精度低于平台 `FrameMetrics` |
| API 24-25 | `JankStatsApi24Impl` | 使用 `Window.addOnFrameMetricsAvailableListener()`；帧起点仍来自低版本 fallback，CPU 字段取 `TOTAL_DURATION` |
| API 26-30 | `JankStatsApi26Impl` | 沿用 `FrameMetrics`，帧起点改用 API 26 新增的 `INTENDED_VSYNC_TIMESTAMP` |
| API 31-37 | `JankStatsApi31Impl` | 用 `DEADLINE` 作为 expected duration，并增加 total、CPU 与 overrun 字段 |

sources 中的 `JankStatsApi16Impl` 仍描述 API 16-23，但发布物的 manifest 会阻止 API 16-22 工程正常依赖。历史 alpha 或自行构建源码可能有不同下限，生产文档必须写出确切 artifact 版本，不能只看实现类名称。

`FrameMetrics.DEADLINE` 从 API 31 才可用。AOSP android-11.0.0_r1 的 `FrameMetrics` 没有这个字段；android-12.0.0_r1 加入 `DEADLINE = 13`。因此 API 24-30 上只能依赖 duration 类指标和 AndroidX 的 expected duration 估算，API 31+ 才能把 deadline overrun 写进同一套分析口径。

### Android 17 仍走 API 31 实现

平台源码统一以 AOSP `android-17.0.0_r1` 为锚点。Android 16（API 36）已经给 `FrameMetrics` 增加 `FRAME_TIMELINE_VSYNC_ID`，并提供 `SurfaceControl.OnJankDataListener` / `SurfaceControl.JankData`，可以用 vsync id 关联 HWUI frame 与 compositor 给出的 jank classification。

JankStats 1.0.0 没有 API 36 或 API 37 实现类。在 Android 17（API 37）上，它仍选择 `JankStatsApi31Impl`，也没有把 `FRAME_TIMELINE_VSYNC_ID` 或 `SurfaceControl.JankData` 暴露到 `FrameDataApi31`。因此：

- JankStats 仍适合按 Window、页面状态和交互状态统计异常帧。
- `frameOverrunNanos` 不能替代 SurfaceFlinger/compositor 的 jank classification。
- 需要判断 App deadline miss、SurfaceFlinger scheduling、buffer stuffing 等类型时，要直接接 API 36+ 的 jank data 或使用 Perfetto。

## jank 阈值不是固定 16ms

JankStats 通过 `jankHeuristicMultiplier` 控制 `isJank`，默认值是 `2.0f`：

- API 23-30 首次需要阈值时根据 `Display.refreshRate` 估算帧周期，再乘 multiplier。
- API 31-37 读取 `FrameMetrics.DEADLINE`，再乘 multiplier。
- 两条路径都以 `frameDurationUiNanos > expectedDuration * multiplier` 判定 `isJank`。

60 Hz 下，一帧周期约 16.67 ms，默认 `isJank` 阈值接近 33.3 ms；120 Hz 下则接近 16.67 ms。把 `isJank` 理解为“超过 16 ms”是错误的。

1.0.0 的 API 23-30 实现会把首次算出的帧周期保存在进程级 `JankStatsBaseImpl.frameDuration` 中，显示模式切换不会自动触发重算。给 `jankHeuristicMultiplier` 赋值会清除此缓存；这不适合作为刷新率变化通知机制。动态刷新率设备应单独记录显示模式，并避免把低版本 JankStats 阈值描述成逐帧 deadline。

API 31+ 还会计算 `frameOverrunNanos = frameDurationTotalNanos - DEADLINE`。由于 overrun 比较 total duration 与一次 deadline，而 `isJank` 比较 UI duration 与默认两倍 deadline，一帧可能出现 `frameOverrunNanos > 0` 但 `isJank == false`。服务端应把这两个字段分开统计。

线上指标建议用这些口径：

- JankStats jank rate：`isJank` frame 数 / 总 frame 数。
- Deadline miss rate：API 31+ 中 `frameOverrunNanos > 0` 的 frame 数 / 总 frame 数。
- Frozen frame rate：选定 duration 超过 700 ms 的 frame 数 / 总 frame 数，并写明使用 UI 还是 total duration。
- 页面慢帧率：按 screen 或 route 聚合。
- 交互慢帧率：按滚动、点击、转场等状态聚合。
- 分位耗时：分别记录 UI、CPU、total 与 overrun 的 P50、P90、P95、P99。

Firebase Performance 的 slow rendering frame 使用固定 16 ms，frozen frame 使用 700 ms，而且官方文档明确说明 slow frame 假定 60 Hz。这套口径可以作为 Firebase 兼容指标，但不能与 JankStats 默认 `isJank` 混用。

平均 FPS 不适合作为唯一指标。某个短窗口先长时间停顿、随后连续出帧，平均值可能尚可，但用户已经感受到停顿。

## 帧性能工具分工

JankStats 更适合线上统计和 UI context，FrameMetrics 更适合读取平台阶段数据。二者可以组合，但不要把阶段耗时直接写成根因：

- JankStats 负责跨版本的慢帧事件和 UI context。
- FrameMetrics 在 API 24+ 上提供 `DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION` 等指标；`DEADLINE` 从 API 31 开始可用。
- SurfaceControl jank data 在 API 36+ 补 compositor 分类，并可通过 `FRAME_TIMELINE_VSYNC_ID` 与 FrameMetrics 关联。

FrameMetrics 的部分阶段可能并行，`TOTAL_DURATION` 也不等于各字段简单相加。某帧 `DRAW_DURATION` 较高只是一条定位线索，仍需 Perfetto、业务 trace 或可复现 benchmark 验证。

### FrameMetrics 的数据边界

Android 17 的 UI 线程和 RenderThread 共同填写 `FrameInfo` 时间戳数组，`FrameMetrics` 再按固定起止索引计算公开指标。公开 listener 会复用同一个 `FrameMetrics` 对象，并且 `FrameMetricsObserver` 不等待 display present time。因此收到回调只表示 HWUI 帧统计已经可用，不表示 SurfaceFlinger 已采纳该 buffer 或屏幕已经呈现。

| 指标 | API | Android 17 时间区间或取值 | 排查入口 |
|---|---:|---|---|
| `UNKNOWN_DELAY_DURATION` | 24+ | `INTENDED_VSYNC → HANDLE_INPUT_START` | 前序消息、调度、Binder 或锁使 UI 线程晚启动 |
| `INPUT_HANDLING_DURATION` | 24+ | `HANDLE_INPUT_START → ANIMATION_START` | 输入处理 |
| `ANIMATION_DURATION` | 24+ | `ANIMATION_START → PERFORM_TRAVERSALS_START` | animation callback 与状态更新 |
| `LAYOUT_MEASURE_DURATION` | 24+ | `PERFORM_TRAVERSALS_START → DRAW_START` | measure/layout 与 `requestLayout()` 扩散 |
| `DRAW_DURATION` | 24+ | `DRAW_START → SYNC_QUEUED` | display-list 记录和自定义绘制 |
| `SYNC_DURATION` | 24+ | `SYNC_START → ISSUE_DRAW_COMMANDS_START` | RenderNode 状态同步、RenderThread 压力 |
| `COMMAND_ISSUE_DURATION` | 24+ | `ISSUE_DRAW_COMMANDS_START → SWAP_BUFFERS` | RenderThread CPU 与 driver submission |
| `SWAP_BUFFERS_DURATION` | 24+ | API 31+ 为 `SWAP_BUFFERS → SWAP_BUFFERS_COMPLETED` | BufferQueue 背压、swap 或消费等待 |
| `TOTAL_DURATION` | 24+ | `INTENDED_VSYNC → FRAME_COMPLETED` | HWUI 生产并提交帧的总区间，不是 present duration |
| `FIRST_DRAW_FRAME` | 24+ | window visibility-change flag | 新 Window 首次 draw，需与稳态帧分开 |
| `GPU_DURATION` | 31+ | API 33+ 为 submission complete 到 GPU complete | GPU workload 或 contention 线索 |
| `DEADLINE` | 31+ | `INTENDED_VSYNC → FRAME_DEADLINE` | 应用生产本帧的预算 |
| `FRAME_TIMELINE_VSYNC_ID` | 36+ | FrameTimeline Vsync id | 与 compositor jank data 关联的 join key |

指标不可用时 `getMetric()` 返回 `-1`，不能用零补齐。各阶段还可能并行，`SYNC_QUEUED → SYNC_START` 等间隙没有独立公开字段，GPU completion 也不保证被 total 完整包含，所以 `TOTAL_DURATION - sum(stages)` 不能命名为“其他耗时”后直接归因。

GPU 与 swap 的定义必须按 API 分桶：API 24—30 的 swap 结束于 `FRAME_COMPLETED` 且没有 GPU/deadline；API 31—32 的 GPU 从 swap 起算；API 33—35 改为从 command submission complete 起算；API 36—37 再增加 Vsync id。跨桶比较原始值会把平台定义变化误判成回归。

### Window 与外部内容的观察范围

| 页面内容 | FrameMetrics 能看到 | 看不到 |
|---|---|---|
| 普通 View / 标准 Compose | 宿主 Window 的 UI、RenderThread 与 swap | 具体 View/Composable 调用栈、SurfaceFlinger 和 present |
| TextureView | 外部 buffer 被 HWUI 采样并混合后的宿主成本 | 外部 Producer 自身的生产、第一套 BufferQueue 与输入 fence |
| SurfaceView | 宿主 UI、hole-punch、几何和控制层帧 | 独立内容 Surface 的 Producer、BufferQueue 与 layer 帧 |
| Dialog、PopupWindow、多窗口 | 每个已注册 Window 各自的帧 | 未注册 Window，且不同 Window 不会自动合并 |
| 软件渲染 Window | 无硬件渲染帧统计 | 软件 Canvas 完整耗时 |

视频、相机、游戏或 SurfaceView 主体内容慢时，宿主 FrameMetrics 正常不能排除问题。需要按内容 layer 继续查 producer queue、acquire/release fence、SurfaceFlinger latch、HWC 与 present timing。

### 直接监听 FrameMetrics

只在 API 24+、硬件加速且 DecorView 已建立的 Window 注册。listener 所在 Handler 应是专用线程，回调返回前只复制需要的数值并更新有界聚合；文件、JSON 与网络不能进入逐帧路径。停止采集时先移除 listener，再退出线程。`droppedReportsSinceLastCallback` 表示观测器来不及消费，不等于显示系统丢了相同数量的帧，但它意味着统计分母已有缺口，必须单列数据质量。

页面状态不能在延迟回调到达时直接读取“当前 route”。API 26+ 使用 `INTENDED_VSYNC_TIMESTAMP` 与应用维护的状态区间做交集；API 24—25 只做 Window session 级聚合，或在路由切换时明确结束旧窗口。Vsync id 是逐帧高基数，只保存在有限异常样本或短期 join cache 中。

JankStats 在 API 24+ 内部已经注册 FrameMetrics listener。若应用再直接注册一条 listener，必须量化重复回调、聚合和对象分配成本。常规线上分布优先用 JankStats；只有需要 layout/draw/sync/command/swap/GPU 分段或 API 36+ compositor join 时，才对受控样本开启直接 FrameMetrics。

### 帧性能监控工具横向对比

下面按“能回答什么”比较相关工具：

| 工具 | 数据来源与使用位置 | 能回答的问题 | 关键边界 |
|---|---|---|---|
| JankStats 1.0.0 | API 23+，应用内逐帧回调 | 哪个 Window、页面状态或交互的 jank / overrun 上升 | 不上传、不抓 trace；API 37 仍走 Api31Impl |
| FrameMetrics | API 24+，应用内逐帧回调 | UI、draw、sync、swap 等平台阶段提供了什么时间线索 | 没有业务状态；阶段值不能直接证明代码根因 |
| SurfaceControl jank data | API 36+，compositor 批量回调 | App、SurfaceFlinger 或调度侧属于哪类 jank | 要自行和 FrameMetrics、页面状态关联 |
| Perfetto | Android 9+ 可用平台 on-device 工具；旧系统另走 host 工具 | 线程调度、Binder、锁、CPU、RenderThread 与 SurfaceFlinger 如何交互 | trace 成本较高，适合实验室或按需采集 |
| Macrobenchmark | 当前 AndroidX 以 API 23+ 为基础，测试设备运行 | 一段可复现交互在变更前后是否退化 | 反映受控测试，不代表线上设备分布 |
| Firebase Performance | SDK 自动 screen rendering trace | 页面实例的 fixed-16-ms slow 与 700-ms frozen 趋势 | slow 指标假定 60 Hz，无法增加自定义 screen metrics / attributes |
| Android Vitals | 系统与 Google Play 聚合 | Play 分发用户中的 slow / frozen 质量趋势 | 没有 JankStats 的自定义 UI context，也不提供逐帧原始事件 |

工具组合应按问题逐层升级：

1. JankStats 或既有平台先定位回归集中在哪个页面、交互、版本和设备层。
2. API 24+ 可附带低采样 FrameMetrics；API 36+ 再按需关联 compositor jank data。
3. 可复现问题用 Perfetto 查看线程、RenderThread、GPU 与 SurfaceFlinger 时间线。
4. 修复方案写成 Macrobenchmark 场景，在固定设备和编译模式下做回归。

如果项目已经接入 Firebase Performance，应先比较它的 screen 定义、60 Hz 固定阈值和数据延迟能否满足需求。需要自定义 UI context、deadline overrun 或原始聚合时再加 JankStats，并测量双重帧监听的开销。Android Vitals 不需要客户端再接一个 SDK，但其聚合维度也不能替代应用自己的交互标签。

## 使用建议

JankStats 上线前要先定义指标协议：

- 明确 `ui_duration`、`cpu_duration`、`total_duration`、`overrun` 与 `is_jank` 的字段名、单位和 API 可用范围。
- `jankHeuristicMultiplier` 固定为配置的一部分。调整 multiplier 后要带新配置版本，不能把两种阈值的事件直接合并。
- 对同一统计窗口保留全部帧计数。不能只采样 jank frame，否则分母与分位数都会失真。
- 若需降低成本，按稳定哈希选择 session / device，或在端上先聚合整个窗口；不要对正常帧和 jank 帧使用不同的随机采样率。
- 以 Activity 可交互或 Window 可见策略启停 `isTrackingEnabled`，并记录策略，避免后台与多窗口数据含义不清。
- 回调内只更新预分配计数器、直方图或有界队列。文件写入、压缩和上传放在后台。

## UI context 的设计

JankStats 的数据能不能用于线上治理，关键不在 `isJank`，而在 UI context。没有 context，慢帧只能按 Activity 聚合；有 context，才能知道是首页列表、详情页转场、播放器拖动还是搜索结果页滚动。

推荐字段要少而稳定：

| 字段 | 示例 | 说明 |
|---|---|---|
| `screen` | `Home`、`Detail`、`Search` | 页面或路由名 |
| `interaction` | `idle`、`scroll`、`transition`、`refresh` | 当前交互状态 |
| `content_type` | `feed`、`video`、`image_grid` | 可选，页面内内容形态 |
| `first_screen` | `true` / `false` | 首屏阶段要单独看 |
| `list_size_bucket` | `0-20`、`20-100`、`100+` | 避免上传真实列表大小 |

不建议把商品 id、帖子 id、搜索词、完整 URL 放进 context。JankStats context 会跟随帧事件上报，高基数字段会让平台聚合失效。

同一 View hierarchy 只有一个 `PerformanceMetricsState`，相同 key 的新值会替换旧值。页面容器、列表组件和基础库如果都写 `state`、`screen` 这类通用 key，很容易互相覆盖。团队应明确 key 的 owner：

- 页面容器独占 `screen`，进入时写入，退出时删除。
- 当前交互独占 `interaction`，滚动、转场和刷新结束后恢复为 `idle` 或删除。
- 可复用组件使用带命名空间的 key，例如 `feed.list_state`，并在 detach 时清理。
- 只需要标记下一帧的短事件使用 `putSingleFrameState()`，避免忘记调用 `removeState()`。

## Compose 场景的状态标记

JankStats 没有单独的 Compose 采集器。Compose 内容仍绘制在 Activity 的 Window 中，UI context 通过 `LocalView.current` 找到同一个 View hierarchy。Activity 必须已经为该 Window 创建 JankStats，否则 holder 的 `state` 仍是 `null`。

下面的示例把页面状态和滚动状态的更新分开，避免每次 `isScrolling` 改变时删除再重建全部状态：

```kotlin
@Composable
fun HomeScreen(isScrolling: Boolean) {
    val view = LocalView.current
    val state = remember(view) {
        checkNotNull(
            PerformanceMetricsState.getHolderForHierarchy(view).state
        ) {
            "Create JankStats for the Activity window before composing HomeScreen"
        }
    }

    DisposableEffect(state) {
        state.putState("screen", "Home")

        onDispose {
            state.removeState("screen")
            state.removeState("interaction")
        }
    }

    LaunchedEffect(state, isScrolling) {
        state.putState(
            "interaction",
            if (isScrolling) "scroll" else "idle"
        )
    }
}
```

`LaunchedEffect` 在 `isScrolling` 变化时更新状态，`DisposableEffect` 在该页面离开 composition 时统一清理。若 Navigation 转场期间两个页面短暂共存，两个页面不能同时拥有同一个 `screen` key；应由 NavHost 或 Activity 级 owner 写入当前 route。

## 批量聚合方式

JankStats 每帧回调一次，逐帧上传会放大序列化、存储和网络成本，还可能反过来干扰被测页面。端侧更适合按“页面 + 交互 + API 桶 + 固定时间窗口”维护计数器和有界直方图，到窗口结束时只上报聚合结果。

下面是一份 API 31-37 窗口的协议示例；字段名应在客户端和服务端共同版本化：

```json
{
  "schema_version": 2,
  "metrics_artifact": "androidx.metrics:metrics-performance:1.0.0",
  "api_bucket": "31-37",
  "screen": "Home",
  "interaction": "scroll",
  "window_ms": 10000,
  "total_frames": 612,
  "jank_frames": 37,
  "deadline_eligible_frames": 612,
  "deadline_miss_frames": 81,
  "frozen_total_frames": 0,
  "jank_multiplier": 2.0,
  "ui_duration_ms": {
    "p50": 8.4,
    "p95": 26.2,
    "p99": 45.7
  },
  "total_duration_ms": {
    "p50": 9.1,
    "p95": 29.8,
    "p99": 51.3
  },
  "overrun_ms": {
    "p50": -2.4,
    "p95": 6.7,
    "p99": 19.5
  }
}
```

`jank_frames` 只累计 `isJank`，`deadline_miss_frames` 只累计 `frameOverrunNanos > 0`，两者不能互相推算。这里把 frozen 定义为 API 31+ 的 `frameDurationTotalNanos > 700 ms`；若平台选择 UI duration，字段名和 schema version 也要随之变化。API 23-30 没有 total/overrun 字段，应将对应直方图和 `deadline_eligible_frames` 留空或置零，不能拿 UI duration 填充后伪装成同一口径。

`FrameData` 没有公开 refresh rate 字段。API 31+ 可以按帧用 `frameDurationTotalNanos - frameOverrunNanos` 还原本帧 deadline；API 23-30 若另行采集 `Display` 刷新率，要把数据来源和采样时刻写进协议。设备可能在窗口内切换显示模式，而且 JankStats 1.0.0 的低版本路径会缓存首次估算值，所以比起只记录一个 `refresh_rate=120`，按 expected-duration 或观测到的 display-mode 桶拆窗口更稳妥。

端侧聚合用于版本趋势、页面排名和设备分层。若仍需保留单帧样本，应按 session 稳定采样并设置数量上限，不能只保留异常帧后再用样本计算比例。

## 慢帧率的口径

“慢帧率”必须同时写清判定条件、分子、分母和维度。建议至少保留三条相互独立的判定：

- **JankStats jank rate**：`isJank=true` 的帧数 / 同一窗口内全部回调帧数，阈值受 expected duration 和 multiplier 影响。
- **Deadline miss rate**：API 31+ 中 `frameOverrunNanos > 0` 的帧数 / 具有 overrun 字段的帧数。
- **Frozen frame rate**：超过约定 duration 阈值的帧数 / 具有该 duration 字段的帧数；使用 700 ms 时应注明这是与 Firebase / Android Vitals 对齐的兼容指标。

全页面、滚动、转场、刷新和首屏属于聚合维度，不应再用含义模糊的一个 `slow_rate` 字段承载。把 idle 帧和 scroll 帧混在一起会稀释问题：页面静止 10 秒、滚动 1 秒，页面总量可能正常，滚动窗口却已经连续错过 deadline。

首屏还需要单独设计边界。JankStats 的 `FrameData` 不公开 `FrameMetrics.FIRST_DRAW_FRAME`，客户端可以在首屏开始和内容稳定之间写入 `first_screen=true`；API 24+ 若要识别平台标记的首个 draw，则需要直接读取 `FrameMetrics.FIRST_DRAW_FRAME`。这两个定义分别代表业务首屏区间和平台首次绘制，不能用同一个字段代替。

聚合数据升高而实验室单次 trace 看不出长帧，并不矛盾。线上比例可能集中在某个 SoC、刷新率、温控状态或特定内容桶，单台高性能测试机没有复现对应条件。处理顺序是先按版本、设备、API、expected duration 和 UI context 缩小范围，再构造 Macrobenchmark 或按需 Perfetto 场景；不能从“一条 trace 正常”推导“线上聚合误报”。

## 常见误判

| 现象 | 可能误判 | 正确处理 |
|---|---|---|
| 低端机慢帧率高 | 直接判业务代码慢 | 先按设备档位分层，再看同档位版本差异 |
| 120 Hz 设备的 `isJank` 更多 | 直接判定体验回退 | 默认阈值约为两倍 expected duration，高刷新率阈值更紧；按 deadline / expected-duration 桶比较 |
| `frameOverrunNanos > 0`，但 `isJank=false` | 判定 AndroidX 数据冲突 | 前者比较 total 与一次 deadline，后者比较 UI 与默认两倍 deadline，应分列统计 |
| 动画持续 500 ms | 把动画总时长当成一帧耗时 | 动画可以持续很多帧；检查每帧是否按 deadline 产出，不用动画总时长判 jank |
| 列表滚动时 UI duration 不高 | 排除应用侧问题 | 预取、图片解码或后台任务可能争抢 CPU，需结合调度、频率和线程 trace |
| API 37 上 JankStats 未报 compositor jank | 判定 SurfaceFlinger 没问题 | 1.0.0 不读取 API 36+ jank classification，应查 SurfaceControl jank data 或 Perfetto |
| 首帧被判 jank | 直接并入滚动回归 | 用业务首屏状态或 `FIRST_DRAW_FRAME` 单列，不与稳态交互混算 |
| 页面切换后 context 仍是旧 route | 判定旧页面持续变慢 | 检查 key owner、转场重叠和 `removeState()`；同一 hierarchy 的同名 key 会被覆盖 |
| 后台或多窗口状态仍有帧事件 | 判定前台页面变慢 | 记录 Window 可见与交互策略，并在生命周期中启停 tracking |
| 回调线程上的聚合偶发竞态 | 归因于设备差异 | API 23 与 API 24+ 回调线程不同，不依赖线程身份，共享计数器要明确同步方式 |
| 单个 FrameMetrics 阶段升高 | 直接定位某个业务函数 | 阶段是时间线索，不是调用栈；用 Perfetto 或业务 trace 验证 |

JankStats 是线上定位入口，不是根因分析器。它把范围收敛到页面、交互、版本和设备层，后续仍要靠 FrameMetrics、SurfaceControl jank data、Perfetto、Macrobenchmark 或业务 trace 建立因果证据。

## 参考资料

- [Google Maven：metrics-performance metadata](https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/maven-metadata.xml)
- [Google Maven：metrics-performance 1.0.0 AAR](https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/1.0.0/metrics-performance-1.0.0.aar)
- [Google Maven：metrics-performance 1.0.0 sources JAR](https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/1.0.0/metrics-performance-1.0.0-sources.jar)
- [AndroidX Metrics release notes](https://developer.android.com/jetpack/androidx/releases/metrics#1.0.0)
- [JankStats API reference](https://developer.android.com/reference/androidx/metrics/performance/JankStats)
- [FrameData API reference](https://developer.android.com/reference/androidx/metrics/performance/FrameData)
- [FrameDataApi24 API reference](https://developer.android.com/reference/androidx/metrics/performance/FrameDataApi24)
- [FrameDataApi31 API reference](https://developer.android.com/reference/androidx/metrics/performance/FrameDataApi31)
- [PerformanceMetricsState API reference](https://developer.android.com/reference/androidx/metrics/performance/PerformanceMetricsState)
- [JankStats 使用指南](https://developer.android.com/topic/performance/jankstats)
- [FrameMetrics API reference](https://developer.android.com/reference/android/view/FrameMetrics)
- [SurfaceControl.JankData API reference](https://developer.android.com/reference/android/view/SurfaceControl.JankData)
- [AOSP android-17.0.0_r1：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP android-17.0.0_r1：SurfaceControl.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java)
- [Firebase Performance：screen rendering traces](https://firebase.google.com/docs/perf-mon/screen-traces?platform=android)
- [Android Vitals：slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Perfetto：Record traces on Android](https://perfetto.dev/docs/quickstart/android-tracing)
