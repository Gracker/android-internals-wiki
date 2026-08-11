---
title: "渲染优化排查框架与案例模板"
chapter: "22.9"
section: "22.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-13"
last_verified_against: "Android Developers docs (Slow rendering, JankStats, Macrobenchmark, Compose performance) + Clippings structure references"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/topic/performance/jankstats"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/bestpractices"
  - type: official
    path: "https://developer.android.com/codelabs/jetpack-compose-performance"
  - type: official
    path: "https://developer.android.com/topic/performance/measuring-performance"
  - type: clipping
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [case-study, rendering, optimization, recyclerview, compose, jank]
related_chapters: ["22.1", "22.2", "22.3", "22.8", "7.8", "13.6", "19.15"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: "fixed"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-19"
task6_result: pass-light-edit
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-14"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-14T06:32:15+08:00"
last_task9_audit: "2026-06-30"
last_task9_audit_at: "2026-06-30T19:29:26+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-30-19-audit.md"
last_task9_audit_result: "pass-idle-audit"
last_task9_review_log: logs/deep-review/2026-05-14-06-deep-review.md
task9_review_notes: "2026-05-14 Task9 06: pass-tech-review。无 P0/P1；P2 1：FrameTimingMetric 验收建议补 frameOverrunMs / deadline miss 口径。未自动晋升：Task6/queue 仍有 pending。 已写入 logs/deep-review/2026-05-14-06-deep-review.md。"
task2b_result: "fixed"
last_task6_at: "2026-05-19T08:16:46+08:00"
last_task6_audit: "2026-06-11"
last_task6_review_log: logs/review/2026-05-19-08-review.md
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-12
---

# 渲染优化排查框架与案例模板

## 这套框架解决什么问题

渲染案例常见两种缺陷：只列优化技巧，缺少问题现场；只给优化前后数字，缺少可复现条件。前者容易把无关配置塞进项目，后者无法判断收益来自代码、缓存、编译状态、设备温度还是测试波动。

以下固定评审流程覆盖列表滑动、Compose 迁移和复杂页面，并串起 22.1—22.8 的专项知识。平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`；需要检查 scheduler 或 fence 时，内核锚点是 `android17-6.18-2026-06_r6`。

一次案例应沿下面五步推进：

1. 定义 Critical User Journey（CUJ），固定入口、数据、缓存、手势与结束条件。
2. 记录测试契约，包括 build、编译状态、设备、display mode、温度和网络。
3. 用帧指标找到回归，再从 trace 中建立同一帧的证据链。
4. 每轮只修改有证据支持的瓶颈，并写清代价与适用边界。
5. 用同一契约复测，同时观察线上分组指标。

这套顺序的重点是可证伪。一次 Perfetto 样本可以提出假设，不能替代多轮 benchmark；一个分位数改善可以说明结果变化，不能单独解释原因。

## 建立统一测量契约

### 先分清渲染拓扑

标准 View 或 Compose 页面通常沿 Choreographer → UI 线程 → RenderThread → BLAST / BufferQueue → SurfaceFlinger → HWC / RenderEngine → present 前进。`ComposeView` 仍属于宿主 View hierarchy，不会仅因使用 Compose 就创建独立 Surface。

页面含 `SurfaceView`、Camera、视频、WebView、Flutter 或游戏引擎时，内容可能来自独立 Producer。宿主 Window 的 `FrameTimingMetric`、JankStats 或 FrameMetrics 正常，只能说明宿主窗口覆盖的帧正常；目标内容 layer 仍可能重复旧 buffer、错过 latch 或延迟 present。案例开头必须记录 Window、Surface、Producer、关键线程和目标 layer，避免查错对象。

### Lab、线上与 trace 各司其职

| 层级 | 入口 | 主要用途 | 解读边界 |
|---|---|---|---|
| 回归基线 | Macrobenchmark `FrameTimingMetric` | 重复执行 CUJ，比较帧分布 | 结果依赖 build、CompilationMode、设备与用例 |
| 场景分组 | JankStats + `PerformanceMetricsState` | 按页面、交互、版本、设备段观察线上变化 | 以 Window 为边界，状态必须低基数 |
| 应用阶段 | FrameMetrics | 检查 UI、RenderThread、GPU、deadline | `TOTAL_DURATION` 不证明最终 present |
| 跨进程证据 | Perfetto FrameTimeline、线程、fence、SF/HWC | 解释某帧在哪个阶段错过时间 | 独立 Surface 要找到自己的 layer/token |

API 31+ 的 Macrobenchmark `FrameTimingMetric` 会输出 `frameOverrunMs`：正值表示超出 deadline，负值表示提前完成。它能自然适配高刷新率和可变刷新率，回归判断应优先看它。`frameDurationCpuMs` 只覆盖 UI 线程与 RenderThread 的 CPU 产帧时间，是定位 CPU 压力的辅助指标。两者都会给出 P50、P90、P95、P99；还要检查 `frameCount`，因为删除无效的轻量帧后，剩余帧的分位数可能升高，功耗和总工作量却下降。

Android 10 / 11 没有 `frameOverrunMs`。这两个版本保留 CPU duration、JankStats 判定和 trace 证据，不要用测试开始时读到的固定 refresh rate 伪造精确 deadline。

### Benchmark 本身也要被评审

Macrobenchmark 目标应用应接近 release：non-debuggable、profileable，建议启用与生产一致的 minify 和资源裁剪。Compose 在 debug build 中的执行特征不具代表性。使用物理设备，固定 benchmark 版本、`CompilationMode`、Baseline Profile 状态、启动模式、测试数据和手势；修改上述任一条件都要重建基线。

设备记录至少包含型号、SoC、Android build、display mode、亮度、充电、power mode、thermal 状态和后台进程约束。冷缓存与热缓存分开跑，不能在同一分布里混合。Benchmark 每次迭代生成的 trace 要与 JSON 结果一起归档，使异常分位点可以回到原始帧。

## 案例一：RecyclerView 滑动出现长帧簇

### 定义用例和症状

示例 CUJ 是“进入 feed → 等待首屏稳定 → 连续 fling 到分页边界 → 停止滚动”。至少拆成以下状态：

- `data_state=cold_cache|warm_cache`
- `scroll_state=dragging|settling|idle`
- `load_state=steady|append`
- `image_state=memory_hit|disk_or_network`

这些状态既用于 benchmark 的数据夹具，也用于线上 JankStats。不要把 position、URL 或内容 id 放进状态标签。

如果 `frameOverrunMs` 只在 `append + settling` 升高，排查范围会比“feed P95 变差”小很多。打开对应 trace，围绕超期帧检查：

| 证据 | 可能原因 | 需要补的验证 |
|---|---|---|
| `RV OnBindView` / 自定义 `FeedBind` 长 | bind 中有格式化、解析、同步 I/O 或大对象构造 | 方法采样、自定义子 section |
| `RV CreateView` 成簇 | viewType、预取或复用池不匹配 | create 次数、pool、嵌套列表状态 |
| UI 按时，DrawFrame / GPU 晚 | 图片上传、裁剪、阴影、path、overdraw | RenderThread、GPU slice/counter |
| UI / RenderThread runnable 等待 | 后台解码、Diff、埋点等竞争 CPU | CPU 调度、线程池并发、thermal |
| GC 与长帧重叠 | 滑动路径分配量过大 | allocation 归属和重复样本 |
| `dequeueBuffer` 等待且队列积压 | consumer 释放或 GPU/fence 较晚 | BufferQueue、release fence、FrameTimeline |

Android 17 trace 若出现 `Buffer stuffing recovery`，要把系统主动延迟和造成 backlog 的前序帧分开。恢复动作的目标是排空队列，不能直接归为当前业务函数 CPU 过重。

### 只对命中的原因动手

常见改动包括：

- 把 JSON 解析、日期格式化、数据库读取和图片尺寸计算移出 bind。
- 用 `ListAdapter` / `AsyncListDiffer` 计算不可变列表的 Diff；列表及参与比较的字段提交后不能原地修改。
- 只在视觉字段局部变化时使用 payload，结构变化仍做完整 bind。
- 请求接近显示尺寸的图片，复核 decode、缓存、纹理上传与回收。
- 给解码、分页、曝光和日志队列设置并发上限，避免后台线程长期占满 CPU。

payload 可能在 ViewHolder 未 attach 时被丢弃。空 payload 必须执行完整 bind；非空 payload 可以合并多次变化。下面的示例用位掩码减少临时集合，并保留完整绑定兜底。

```kotlin
private const val PAYLOAD_LIKED = 1
private const val PAYLOAD_COMMENT_COUNT = 1 shl 1

class FeedDiff : DiffUtil.ItemCallback<FeedItem>() {
    override fun areItemsTheSame(oldItem: FeedItem, newItem: FeedItem): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: FeedItem, newItem: FeedItem): Boolean {
        return oldItem == newItem
    }

    override fun getChangePayload(oldItem: FeedItem, newItem: FeedItem): Any? {
        var mask = 0
        if (oldItem.liked != newItem.liked) mask = mask or PAYLOAD_LIKED
        if (oldItem.commentCount != newItem.commentCount) {
            mask = mask or PAYLOAD_COMMENT_COUNT
        }
        return mask.takeIf { it != 0 }
    }
}

class FeedAdapter : ListAdapter<FeedItem, FeedViewHolder>(FeedDiff()) {
    override fun onBindViewHolder(holder: FeedViewHolder, position: Int) {
        holder.bindAll(getItem(position))
    }

    override fun onBindViewHolder(
        holder: FeedViewHolder,
        position: Int,
        payloads: MutableList<Any>
    ) {
        if (payloads.isEmpty()) {
            onBindViewHolder(holder, position)
            return
        }

        val item = getItem(position)
        val mask = payloads.filterIsInstance<Int>().fold(0, Int::or)
        if (mask and PAYLOAD_LIKED != 0) holder.bindLiked(item.liked)
        if (mask and PAYLOAD_COMMENT_COUNT != 0) {
            holder.bindCommentCount(item.commentCount)
        }
    }
}
```

这段改动只减少特定更新的 bind 工作量。若长帧来自图片上传、layout、GPU 或 CPU 竞争，payload 不会带来对应改善。复测时对比 `frameOverrunMs`、`frameDurationCpuMs`、`frameCount`、create/bind 次数以及命中的 trace section；任何“提升百分比”都要附设备、用例、分位数和置信范围。

## 案例二：View 迁移到 Compose 后滚动回归

### 先排除不公平比较

迁移前后要使用相同数据、图片缓存、手势、设备和 build 类型。Compose 版本还要固定 Kotlin/Compose Compiler、runtime、Baseline Profile 和 `CompilationMode`。若 View 版本已经经过 profile 编译，而 Compose 版本用首次安装后的无 profile 状态，比较会混入编译差异。

普通 Compose 内容仍写入宿主 App Window。Perfetto 中从 Choreographer、Compose composition/layout/draw、RenderThread、BLAST 到 SF 的主线应能对齐。页面嵌有 `AndroidView` 不一定改变拓扑；`SurfaceView`、视频、地图或 WebView 才需要额外核对独立 layer。

### 从 trace 判断是哪一类成本

| 现象 | 常见原因 | 有针对性的处理 |
|---|---|---|
| composition section 成簇且昂贵 | 函数体排序/过滤/格式化、状态读取范围过大 | 上移计算、`remember(input)`、缩小读取范围 |
| Lazy item 身份频繁变化 | 缺稳定 `key`，数据对象原地变异 | 稳定业务 key、不可变快照 |
| 固定少量子项出现独立 subcomposition | 小集合使用 Lazy 容器或其他 `SubcomposeLayout` | 验证后改用普通 Row/Column |
| 高频状态触发低频 UI 重组 | 直接读取 scroll/animation 状态 | `derivedStateOf` 或延迟到 layout/draw 的 lambda |
| composition 内出现 Binder transaction | 系统服务查询或注册进入主线程热路径 | 缓存、移出热路径；必须在主线程的调用保留 |
| UI 阶段短，DrawFrame/GPU 长 | 问题不在 composition | 检查绘制、纹理、RenderThread、GPU |

重组次数本身不是结论。一次昂贵重组足以造成长帧；大量很轻且可按期完成的重组也可能不影响用户。要把 composition section 与同一帧的 `frameOverrunMs` 对齐。

下面的迁移边界让排序在上层状态生产阶段完成，并为 Lazy item 提供稳定身份和 `contentType`。

```kotlin
@Immutable
data class FeedUiState(
    val sortedItems: ImmutableList<FeedItem>
)

@Composable
fun FeedScreen(
    uiState: FeedUiState,
    onOpen: (FeedItem) -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(modifier = modifier) {
        items(
            items = uiState.sortedItems,
            key = FeedItem::id,
            contentType = FeedItem::type
        ) { item ->
            FeedCard(
                item = item,
                onOpen = onOpen
            )
        }
    }
}
```

`@Immutable` 只能标注满足不可变契约的类型；错误标注会让 Compose 在数据变化时跳过应执行的更新。`key` 必须在兄弟 item 中稳定且唯一，`contentType` 应表达可复用布局类别。排序若依赖频繁变化的输入，也要在 ViewModel 或 `remember` 处明确输入边界，不能靠注解掩盖工作量。

Compose 性能 codelab 提到 Lazy layout、`BoxWithConstraints` 及其他 `SubcomposeLayout` 会在父布局阶段决定子项 composition。把固定少量标签从 `LazyRow` 改成 `Row` 只适用于不需要懒加载且 trace 已显示子组合成本的场景。不能将它扩展成“禁用 Lazy”的项目规则。

## 案例三：含视频、WebView 和长列表的详情页

### 按用户里程碑拆任务

复杂页面需要同时管理首屏、可交互时间和后续滚动。把所有模块塞进首帧会拉长 TTID；把所有任务统一延后，又可能在用户开始操作时形成长帧簇。任务应按用户里程碑和依赖拆分：

| 阶段 | 应保留的内容 | 调度要求 | 验收指标 |
|---|---|---|---|
| 首次显示 | 稳定骨架、标题、主图占位、关键操作 | 不做可延后的解析与模块挂载 | `timeToInitialDisplayMs`、首帧 trace |
| 可完整交互 | 首屏数据、必要监听、关键控件状态 | 通过 `reportFullyDrawn()` 定义产品完成点 | `timeToFullDisplayMs`、交互正确性 |
| 连续滚动 | 评论、推荐、广告、图片、曝光 | 小批量提交 UI，后台队列有并发上限 | `frameOverrunMs`、jank streak |
| 独立内容 | 视频、WebView、地图或 Camera | 单独记录 producer、layer 与生命周期 | 内容 present-to-present、FrameTimeline |

占位区域应尽量稳定尺寸，避免异步内容到达后触发大范围 relayout。数据准备可以在后台执行，View/Compose 树变更仍要回到 UI 线程，并按 trace 观察到的成本切成可控批次。“主线程空闲时一次性挂载全部模块”没有 deadline 保证，也可能把工作推到用户第一次滑动。

### 用一条 CUJ 覆盖阶段切换

下面的流程文本定义可复现的详情页用例和所需证据。

```text
CUJ:
  冷启动进入详情页
  等待首次显示
  等待 reportFullyDrawn 对应帧完成
  fling 到评论区并触发分页
  播放视频或进入 WebView 交互
  返回顶部

记录:
  StartupTimingMetric + FrameTimingMetric
  JankStats: page / phase / scroll_state / module_state
  Perfetto: UI / RenderThread / BLAST / SF / HWC / FrameTimeline
  独立内容: producer / BufferQueue / layer / fence / present
```

这条用例要按 cold/warm cache 分开运行。视频或 WebView 的内容帧不能只靠宿主 Window 验收：`queueBuffer()` 只代表提交，仍要确认目标 layer 的 latch、composition 和 present。宿主窗口 overrun 也需要与独立内容的时间线分开统计。

若 UI 与 RenderThread 已按期完成，FrameTimeline 仍显示 composer 侧 jank，排查方向应转到 SurfaceFlinger scheduling、composition、HWC 和显示模式。若线程 runnable 长时间未获 CPU，再检查 `android17-6.18-2026-06_r6` scheduler；若 buffer 复用等待 fence，补 dma-fence、GPU 和 display driver 证据。没有这些下沉信号时，不从应用长帧直接推断内核根因。

## 案例复盘模板

每个案例保存以下字段，缺项会影响复查：

| 字段 | 必填内容 |
|---|---|
| CUJ | 入口、步骤、手势、结束条件、cold/warm 状态 |
| 构建 | commit、variant、debuggable/profileable、minify、依赖版本 |
| 编译 | `CompilationMode`、Baseline Profile、安装与预热方式 |
| 设备 | 型号、SoC、Android build、display mode、power/thermal 状态 |
| 拓扑 | Window、Surface、Producer、进程/线程、目标 layer |
| 症状 | `frameOverrunMs`、CPU duration、frame count、线上 jank 分组 |
| 观察事实 | trace 中可直接定位的 slice、状态、VSync ID 与时间 |
| 根因假设 | 从事实推导出的候选原因，标注尚缺的证据 |
| 实验 | 单一改动、预期影响、兼容与资源代价 |
| 结果 | 同契约前后分布、迭代数、波动或置信范围 |
| 灰度 | 线上分组、监控 coverage、回滚条件 |
| 结论边界 | 可推广范围、反例、仍待验证项 |

复盘记录要分开写“观察事实”“推断”“验证结果”。自动分析工具可以聚类栈签名、连接 VSync ID 和生成候选检查项，输出仍属于假设。只有同契约实验和线上灰度都支持时，才能把相关性升级为根因结论。

## 评审核对单

- CUJ、build、CompilationMode、缓存、设备和 display mode 都已记录。
- API 31+ 优先比较 `frameOverrunMs`，同时核对 CPU duration 与 frame count。
- Perfetto 中已经找到目标 Window/Surface、线程、layer 和超期帧。
- RecyclerView payload 有完整 bind 兜底，列表与比较字段保持不可变。
- Compose 比较使用 non-debuggable build，并对齐 Baseline Profile 与编译状态。
- 复杂页面分别验收 TTID、TTFD、滚动和独立内容 present。
- Android 17 的 buffer-stuffing recovery 被识别为队列恢复信号。
- 调度与 fence 结论分别有 `android17-6.18-2026-06_r6` 对应证据。
- 每轮改动与一个已观测瓶颈对应，并记录内存、功耗或复杂度代价。
- 复测保存原始 JSON/trace，线上灰度先检查采集 coverage。

## 源码与文档索引

### Android 17 / API 37

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java) 与 [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：帧调度、Traversal 与 buffer-stuffing recovery。
- [`FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：应用阶段、deadline 与 VSync ID。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp) 与 [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)：buffer transaction、SF 调度与显示主线。
- [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)、[`FrameTimingMetric`](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric) 与 [Macrobenchmark 编写指南](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)：帧分布、测试构建与 trace 归档。
- [JankStats](https://developer.android.com/topic/performance/jankstats)、[Compose performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices) 与 [Compose performance codelab](https://developer.android.com/codelabs/jetpack-compose-performance)：线上状态、Compose 热路径与 composition tracing。
- [`RecyclerView.Adapter`](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.Adapter) 与 [`DiffUtil`](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)：payload、完整绑定兜底与异步 Diff 的数据约束。
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：App/SF expected 与 actual timeline。

### Kernel `android17-6.18-2026-06_r6`

- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c)：UI/RenderThread 与后台线程的调度证据。
- [`drivers/dma-buf/dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)：GPU、HWC 和 buffer 生命周期使用的 fence 基础。
