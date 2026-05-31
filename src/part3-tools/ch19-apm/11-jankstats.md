---

title: JankStats
chapter: '19'
section: '19.11'
status: "ready-for-review"
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: '2026-05-31'
last_verified_against: AndroidX metrics-performance 1.0.0 JankStatsApi16/24/26/31 implementation + PerformanceMetricsState + AOSP FrameMetrics Android 11/12 DEADLINE boundary
confidence: medium
tags:
- apm
related_chapters:
- '19.0'
sources:
- type: official
  path: https://developer.android.com/reference/androidx/metrics/performance/JankStats
- type: official
  path: https://dl.google.com/android/maven2/androidx/metrics/metrics-performance/maven-metadata.xml
pipeline_stage: "task9_pending"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-31"
task6_result: pass-light-edit
task6_state: "reviewed"
last_task6_audit: "2026-05-20"
last_task6_at: "2026-05-31T21:05:00+08:00"
task9_state: "pending"
task2b_state: "fixed"
task9_result: "pending"
task9_reviewed_date: "2026-04-27"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-27T10:57:00+08:00"
task2b_result: "fixed"
last_task2b_at: "2026-05-31T20:52:00+08:00"
repaired_date: '2026-05-31'
repaired_by: openclaw-task2b
task6_reviewed_date: "2026-05-31"
last_task6_review_log: "logs/review/2026-05-31-21-review.md"
task6_review_notes: "2026-05-31 Task6 revisiting-review: L1/L2 小修 3 处；Compose 示例补齐 state 清理，送 Task9 复核。"
last_task9_audit: 2026-05-21
last_task9_audit_at: "2026-05-21T10:23:28+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-21-10-audit.md"
task9_review_notes: "2026-05-21 Task9 闲时抽检：发现 JankStatsApi24Impl 状态同步机制与 FrameMetrics DEADLINE 版本边界 P0/P1 问题，已写入 queue，转 Task2B 回炉。"
last_task2b_rework_log: "Task2B 2026-05-31: 按 2026-05-21 Task9 fallback 问题修正 JankStats API16/24/26/31 实现分层与 FrameMetrics.DEADLINE API31 版本边界。"

---


# JankStats

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 JankStats 是 AndroidX 提供的帧级卡顿入口，适合线上采集慢帧分布和页面上下文。
- 🔹 [输出数据] 展开 `FrameData`、`isJank`、frame duration、expected duration、states 的含义，给字段样例。
- 🔹 [API 版本] 核对 AndroidX metrics-performance 版本、最低系统要求、View / Window 接入方式和 Compose 支持方式。
- 🔹 [阈值口径] 说明 jank 判断和刷新率、expected duration、deadline 的关系，避免固定用 16ms。
- 🔹 [UI context] 设计页面、列表、tab、弹窗、加载状态、Compose state 的命名规则和生命周期清理方式。
- 🔹 [Compose] 写 `PerformanceMetricsState` 在 Compose 场景中的状态更新方式，避免 stale state 影响聚合。
- 🔹 [批量聚合] 说明端侧不要逐帧上传，应该按页面、时间窗口、版本、机型聚合 slow / frozen / jank rate。
- 🔹 [工具分工] 和 FrameMetrics、Perfetto、Macrobenchmark、Firebase Performance 的数据边界做表格。
- 🔹 [误判] 覆盖页面状态缺失、后台帧、动画预期耗时、列表预加载、低端机 CPU 争抢等误判来源。
- 🔹 [使用建议] 给 Release 接入、采样、远程开关、字段脱敏和服务端聚合建议。

### 扩展（可选深入）

- 🔸 补一个 View 页面接入示例和一个 Compose 页面状态标记示例。
- 🔸 增加一份端侧批量聚合数据结构，便于后续平台章节接入。
- 🔸 对 AndroidX JankStats API reference 做 L1 核对，标注过期 API 或实验状态。
- 🔸 增加一个“慢帧率升高但单帧 trace 不明显”的案例，说明聚合指标的价值。
- 🔸 补充与 Google Play Vitals / Firebase 的关系，避免重复采集同一指标。

### 流水线加工要求

- JankStats 段落必须把 UI context 当成重点写，不能只解释 `isJank`。
- 所有阈值都要绑定刷新率或 expected duration，不写固定 16ms 结论。
- 示例需要能直接落到线上字段，而不是只适合本地 demo。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## JankStats 是官方帧级卡顿入口

JankStats 属于 `androidx.metrics:metrics-performance`，用于按帧收集 UI jank 信息。AndroidX Maven metadata 当前稳定版本为 `1.0.0`。它会把每帧耗时、是否 jank、当时 UI 状态回调给应用，由应用自行聚合和上传。

它适合作为线上流畅性监控的第一层信号源。它不负责 trace 文件、不负责堆栈、不负责平台看板，也不告诉你某一帧为什么慢。它回答的是：哪些页面、哪些交互、哪些版本出现了更多慢帧。

## 它输出什么

JankStats 的一条帧事件通常包含三类信息：

- **帧耗时**：这一帧花了多久。
- **jank 判定**：这一帧是否超过当前刷新率对应的阈值。
- **UI context**：当时页面或交互状态，比如 `screen=Home`、`state=scrolling`。

UI context 是它比裸 `Choreographer.FrameCallback` 更有用的地方。只知道“慢帧发生了”还不够，线上更需要知道“慢帧发生在哪个页面、哪个用户动作里”。

下面这段代码展示 JankStats 的最小接入，重点看 `createAndTrack()` 和 `PerformanceMetricsState` 的状态标记。

```kotlin
class HomeActivity : AppCompatActivity() {
    private lateinit var jankStats: JankStats

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        val decorView = window.decorView
        val metricsState = PerformanceMetricsState.getHolderForHierarchy(decorView).state

        jankStats = JankStats.createAndTrack(window) { frameData ->
            val sample = JankFrameSample(
                isJank = frameData.isJank,
                frameDurationUiNanos = frameData.frameDurationUiNanos,
                states = frameData.states.associate { stateInfo -> stateInfo.key to stateInfo.value }
            )

            if (sample.isJank) {
                reportJank(sample)
            }
        }

        metricsState.putState("screen", "Home")
    }
}

data class JankFrameSample(
    val isJank: Boolean,
    val frameDurationUiNanos: Long,
    val states: Map<String, String>
)
```

这段代码先通过 `setContentView()` 建立 `DecorView`，再调用 `createAndTrack()`。AndroidX reference 对这个调用有明确约束：`window` 必须已经处于可用状态，且 `DecorView` 不能为空；如果在 `setContentView()` 前初始化，`createAndTrack(window, ...)` 可能直接抛 `IllegalStateException`。

`OnFrameListener` 回调里的 `FrameData` 只适合做当前帧内的轻量处理。要把事件交给后台线程、批量聚合或异步上报时，先复制 `isJank`、`frameDurationUiNanos` 和 `states` 到自己的 DTO。不要把 `FrameData` 对象本身跨线程保存，也不要在回调里做同步 I/O 或复杂序列化。

状态关联依赖一条时间线。`PerformanceMetricsState.putState()` / `removeState()` 在 UI 线程用 `System.nanoTime()` 记录每个 `StateInfo` 的添加和移除时间；JankStats 在生成 `FrameData` 时，用帧的 `[frameStart, frameEnd]` 区间调用 `getIntervalStates()` 做区间交集判断，交集命中的状态会进入这一帧的 `states`。这样 `screen=Home`、`interaction=scroll` 这类标签对应的是帧覆盖的状态区间，避免退化成“回调触发瞬间的当前页面状态”。

## API 版本差异

JankStats 官方文档明确说明：不同 API 级别下，底层帧时间来源不同。

| Android 版本 | AndroidX 实现路径 | 行为 |
|---|---|---|
| API 16 以下 | 不支持 | 不工作，因为缺少可靠帧时间数据 |
| API 16-23 | `JankStatsApi16Impl` | 通过 `OnPreDrawListener` 估算帧时间，精度低于平台 `FrameMetrics` 路径 |
| API 24-25 | `JankStatsApi24Impl` | 使用 `Window.addOnFrameMetricsAvailableListener` 接收 `FrameMetrics`，再和 `PerformanceMetricsState` 的状态区间匹配 |
| API 26-30 | `JankStatsApi26Impl` | 沿用 `FrameMetrics` listener，并可读取更完整的帧 duration 指标 |
| API 31+ | `JankStatsApi31Impl` | 读取 `FrameMetrics.DEADLINE`，计算 `frameOverrunNanos`，jank 判定和 deadline / expected duration 关系更直接 |

JankStats 的最低系统要求是 API 16。本书主体覆盖 Android 8 及以上设备，这些设备会走平台帧 timing 能力更完整的路径；如果产品仍覆盖 API 16-23，低版本数据要单独标记来源和精度。

`FrameMetrics.DEADLINE` 从 API 31 才可用。AOSP android-11.0.0_r1 的 `FrameMetrics` 没有这个字段；android-12.0.0_r1 加入 `DEADLINE = 13`。因此 API 24-30 上只能依赖 duration 类指标和 AndroidX 的 expected duration 估算，API 31+ 才能把 deadline overrun 写进同一套分析口径。

## jank 阈值不是固定 16ms

JankStats 通过 `jankHeuristicMultiplier` 控制 jank 判定，默认值是 2，表示阈值约为当前预期帧时长的两倍。官方文档说明它会结合当前刷新率计算帧时长阈值。60Hz、90Hz、120Hz 屏幕下，直接写死 16ms 都会带来口径偏差。

线上指标建议用这些口径：

- 慢帧率：jank frame 数 / 总 frame 数。
- 页面慢帧率：按 screen 或 route 聚合。
- 交互慢帧率：按滚动、点击、转场等状态聚合。
- 分位耗时：P50、P90、P95、P99 帧耗时。

平均 FPS 不适合作为唯一指标。前半秒卡死、后半秒补很多帧，平均数可能还不错，但用户已经感到卡顿。

## 帧性能工具分工

JankStats 更适合线上统一口径，FrameMetrics 更适合高版本上拆帧阶段。二者可以同时存在：

- JankStats 负责跨版本的慢帧事件和 UI context。
- FrameMetrics 在 API 24+ 上补 `DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION` 等细分指标；`DEADLINE` 从 API 31 开始可用。

如果只接 FrameMetrics，低版本和 UI 状态关联要自己补。如果只接 JankStats，慢帧原因仍然很粗。线上体系里，两者组合更容易从“哪里慢”走到“像是哪一段慢”。

### 帧性能监控工具横向对比

除了 JankStats 和 FrameMetrics，线上和线下还有几类常用工具。下面的表格覆盖了数据粒度、适用场景和各自的边界：

| 维度 | JankStats | FrameMetrics | Perfetto | Macrobenchmark | Firebase Performance |
|------|-----------|--------------|----------|----------------|---------------------|
| **数据粒度** | 帧级（duration + isJank + UI context） | 帧级（拆分 draw/sync/input 等阶段耗时） | 系统级完整 trace | 帧级 + 操作级基准指标 | 聚合级（慢帧率、冻结帧率按页面/版本聚合） |
| **线上/线下** | 线上 | 线上 | 线上（受限于 trace 大小和采集成本，通常用于按需抓取） | 线下基准测试 | 线上 |
| **能否定位根因** | 否（只标记“哪里慢”） | 部分（区分帧内阶段） | 是（可追到函数、线程调度和锁等待） | 否（对比前后版本帧时间变化） | 否（只看聚合趋势） |
| **UI context** | 支持（PerformanceMetricsState 标记页面/交互状态） | 不支持（只有帧时间数据） | 支持（自定义 trace event） | 不适用（自动化 benchmark 场景） | 支持（按 Screen / Activity 聚合） |
| **跨版本兼容** | API 16+（不同版本精度不同） | API 24+ | Android 5+（功能随版本增强） | Android 5+ | 集成 Firebase SDK 即可 |
| **适用场景** | 线上慢帧分布监控、按页面/交互维度聚合 | 线上帧阶段耗时分析、定位慢帧发生在 draw/sync/input 哪一段 | 根因分析：把单帧问题追到具体函数调用、线程调度、锁等待 | CI/CD 基准对比：量化代码变更对帧性能的影响 | 线上趋势监控：按版本/设备/页面看慢帧率和冻结帧率变化 |
| **边界** | 不提供堆栈、不提供帧内阶段拆分；回调里不能做重操作 | 不关联 UI 状态，不跨进程；低版本不可用 | trace 文件大，不适合全量线上采集；需要 Perfetto 知识 | 只能在测试环境运行，不反映线上真实用户场景 | 数据粒度粗，无法定位到具体帧；依赖 Firebase 生态 |

**选型判断**：

- **线上入口**：JankStats + Firebase Performance 覆盖“哪里慢”和“版本趋势”。JankStats 给页面/交互级慢帧分布，Firebase 给版本级聚合趋势。
- **线上细分定位**：FrameMetrics 在 API 24+ 上拆帧阶段，判断慢帧发生在 draw / sync / input 哪一段。
- **线下根因**：Perfetto 做系统级 trace 分析，定位到具体函数、锁、调度问题。
- **CI/CD 守门**：Macrobenchmark 在每次代码变更后跑基准测试，量化帧时间变化。
- **组合使用**：JankStats 发现“首页滚动慢帧率 5%” → FrameMetrics 确认“draw 阶段占 70%” → Perfetto 追到“Bitmap 解码在主线程” → 修复后 Macrobenchmark 验证改善幅度。

## 使用建议

JankStats 上线前要先定义状态字段。字段太少，数据只能按页面聚合；字段太多，平台维度会爆炸。一般保留页面、交互状态、列表类型、是否首屏、是否动画中就够用。

回调里只做轻量处理。聚合、采样、落盘和上传放到后台线程。慢帧监控自己不能变成慢帧来源，这是线上性能 SDK 的基本红线。

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

## Compose 场景的状态标记

Compose 应用也需要主动维护 UI context。可以在页面进入、列表滚动、动画开始和结束时更新 `PerformanceMetricsState`。示意代码如下：

```kotlin
@Composable
fun HomeScreen(window: Window, isScrolling: Boolean) {
    val view = LocalView.current
    DisposableEffect(view, isScrolling) {
        val state = PerformanceMetricsState.getHolderForHierarchy(view).state
        state.putState("screen", "Home")
        state.putState("interaction", if (isScrolling) "scroll" else "idle")

        onDispose {
            state.removeState("screen")
            state.removeState("interaction")
        }
    }
}
```

状态要在生命周期结束时移除。否则页面切走后，后续慢帧可能仍带旧页面标签，平台会把问题归到错误页面。

## 批量聚合方式

JankStats 每帧回调一次。线上不应该逐帧上传，应该按窗口聚合。一个常见窗口是“页面 + 交互状态 + 10 秒”：

```text
screen=Home
interaction=scroll
window=10s
total_frames=612
jank_frames=37
p50_frame_ms=8.4
p95_frame_ms=26.2
p99_frame_ms=45.7
refresh_rate=120
```

这个聚合比单帧样本更适合看趋势。单帧样本可以按低采样率保留，用于回查；聚合指标用于版本和页面排名。

## 慢帧率的口径

线上至少区分三种口径：

- **全页面慢帧率**：页面可见期间所有帧，适合看整体体验。
- **交互慢帧率**：滚动、转场、刷新期间的帧，适合看用户感知。
- **首屏慢帧率**：页面首次绘制到首屏稳定期间，适合看启动和页面打开。

把 idle 帧和 scroll 帧混在一起，会稀释问题。一个页面静止 10 秒、滚动 1 秒，按全量帧统计可能看起来很好，但滚动期间已经明显卡顿。

## 常见误判

| 现象 | 可能误判 | 正确处理 |
|---|---|---|
| 低端机慢帧率高 | 直接判业务代码慢 | 先按设备档位分层，再看同档位版本差异 |
| 120Hz 设备慢帧多 | 判体验变差 | 高刷新率 deadline 更紧，要分刷新率看 |
| 首帧被判 jank | 判启动卡顿 | 首帧和窗口动画要单独口径，不和滚动混算 |
| 页面切换后 context 错乱 | 判旧页面变慢 | 检查 state 移除和生命周期绑定 |
| 后台仍有帧事件 | 判页面慢 | 过滤前后台和 window 可见状态 |

JankStats 是入口，不是根因分析器。它告诉你“哪段体验慢”，后面还要接 FrameMetrics、Perfetto 或业务 trace。
