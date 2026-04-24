---
title: "JankStats"
chapter: "19"
section: "19.11"
status: ready-for-review
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "AndroidX JankStats API reference"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://developer.android.com/reference/androidx/metrics/performance/JankStats"
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: pending
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

JankStats 属于 `androidx.metrics:metrics-performance`，用于按帧收集 UI jank 信息。它会把每帧耗时、是否 jank、当时 UI 状态回调给应用，由应用自行聚合和上传。

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

        jankStats = JankStats.createAndTrack(window) { frameData ->
            if (frameData.isJank) {
                reportJank(
                    durationUiNanos = frameData.frameDurationUiNanos,
                    states = frameData.states
                )
            }
        }

        val metricsState = PerformanceMetricsState.getHolderForHierarchy(window.decorView).state
        metricsState.putState("screen", "Home")
    }
}
```

这段代码只能说明接入方式，线上还要在 `reportJank()` 里做采样、聚合和批量上报。不要在回调里做同步 I/O 或复杂序列化。

## API 版本差异

JankStats 官方文档明确说明：不同 API 级别下，底层帧时间来源不同。

| Android 版本 | 行为 |
|---|---|
| API 16 以下 | 不工作，因为缺少可靠帧时间数据 |
| API 16-23 | 使用较粗的帧时间估算 |
| API 24-30 | 基于平台帧 timing API，数据更可靠 |
| API 31+ | 平台暴露更多 frame timing 信息，判定更准确 |

本章适用范围从 Android 8 起，所以通常会落在 API 26+。这意味着 JankStats 在目标设备上已经能利用较可靠的帧 timing 能力。

## jank 阈值不是固定 16ms

JankStats 通过 `jankHeuristicMultiplier` 控制 jank 判定，默认值是 2。官方文档说明它会结合当前刷新率计算帧时长阈值。60Hz、90Hz、120Hz 屏幕下，直接写死 16ms 都会带来口径偏差。

线上指标建议用这些口径：

- 慢帧率：jank frame 数 / 总 frame 数。
- 页面慢帧率：按 screen 或 route 聚合。
- 交互慢帧率：按滚动、点击、转场等状态聚合。
- 分位耗时：P50、P90、P95、P99 帧耗时。

平均 FPS 不适合作为唯一指标。前半秒卡死、后半秒补很多帧，平均数可能还不错，但用户已经感到卡顿。

## 和 FrameMetrics 的分工

JankStats 更适合线上统一口径，FrameMetrics 更适合高版本上拆帧阶段。二者可以同时存在：

- JankStats 负责跨版本的慢帧事件和 UI context。
- FrameMetrics 在 API 24+ 上补 `DRAW_DURATION`、`SYNC_DURATION`、`COMMAND_ISSUE_DURATION`、`DEADLINE` 等细分指标。

如果只接 FrameMetrics，低版本和 UI 状态关联要自己补。如果只接 JankStats，慢帧原因仍然很粗。线上体系里，两者组合更容易从“哪里慢”走到“像是哪一段慢”。

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
