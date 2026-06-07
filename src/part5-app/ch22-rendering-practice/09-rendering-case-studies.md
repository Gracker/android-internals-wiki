---
title: "渲染优化排查框架与案例模板"
chapter: "22.9"
section: "22.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
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
related_chapters: ["22.1", "22.2", "22.3", "22.8", "7.8", "13.6", "19.18"]
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
last_task9_audit: "2026-06-08"
last_task9_review_log: logs/deep-review/2026-05-14-06-deep-review.md
task9_review_notes: "2026-05-14 Task9 06: pass-tech-review。无 P0/P1；P2 1：FrameTimingMetric 验收建议补 frameOverrunMs / deadline miss 口径。未自动晋升：Task6/queue 仍有 pending。 已写入 logs/deep-review/2026-05-14-06-deep-review.md。"
task2b_result: "fixed"
last_task6_at: "2026-05-19T08:16:46+08:00"
last_task6_review_log: logs/review/2026-05-19-08-review.md
---


# 渲染优化排查框架与案例模板

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 列表滑动卡顿优化实战
- 🔹 Compose 迁移性能踩坑
- 🔹 复杂页面渲染优化

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->
## 为什么要了解渲染优化排查框架

渲染问题很少只由一个点造成。列表滑动卡顿可能同时来自 `onBindViewHolder()` 过重、图片解码抢占 CPU、主线程等待 I/O、局部刷新退化成整项刷新；Compose 迁移后的卡顿也可能来自频繁重组、缺少 `key`、过度使用 Lazy 容器、主线程 Binder 调用。本节的价值，是把 22.1 到 22.8 节里的单点技术放进同一条排查路径里：量化帧耗时，定位主线程、RenderThread、GPU 或后台线程干扰，再用同一组指标验收。

> **定位说明**：本节提供排查框架和复盘模板，覆盖列表滑动、Compose 迁移和复杂页面三个高频场景。团队拿到自己的 Macrobenchmark / JankStats / Perfetto 数据后，按末尾“案例复盘模板”填写，就能产出可复查的优化记录；有可脱敏分享的真实案例时，再补充到对应场景。

Android 官方把慢帧定义为渲染时间超过设备刷新周期的帧。60Hz 设备的单帧预算约 16ms，90Hz 约 11ms，120Hz 约 8ms；超过 700ms 的帧会被 Android vitals 单独归为 frozen frame。线上排查不能只看平均帧率，至少要看 P90/P95/P99、慢帧比例、frozen frame 数量和用户场景标签。`JankStats` 适合端侧带场景标签采集，`Macrobenchmark` 的 `FrameTimingMetric` 适合回归测试，Perfetto 负责解释为什么某几帧变慢。[已验证: 官方文档, developer.android.com/topic/performance/vitals/render][已验证: 官方文档, developer.android.com/topic/performance/jankstats][已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]

参考书给出的结构线索是「CPU 时间、缓存、任务调度」三类因素：减少主线程工作量、把可提前准备的数据放到空闲期、把 CPU 型任务和 I/O 型任务分池处理、避免后台任务抢主线程和 RenderThread 的时间片。这里借用这个分析顺序，具体建议重新对照 Android 官方文档和已有章节组织，不搬运参考书原文。[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md][结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md][结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md][结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]

## 列表滑动卡顿优化实战

排查列表卡顿，先固定一段可重复的滑动用例，不从 RecyclerView 配置项清单开始。用 `Macrobenchmark` 固定启动方式、滑动距离和迭代次数，采集 `FrameTimingMetric`；同时用自定义 trace 标记 `createViewHolder`、`bindViewHolder`、图片加载回调、Diff 计算和主线程任务。线上版本再用 `JankStats` 给列表场景加状态，例如 `FeedList=Scrolling`、`Tab=Home`、`DataState=ColdCache`。这样 P95 变差时能区分是首屏冷缓存、快速滑动、分页加载还是局部刷新引发的问题。详见 22.8 节。[已验证: 官方文档, developer.android.com/topic/performance/jankstats][已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]

列表滑动常见的慢帧来源可以按线程拆开：

- 主线程: `onBindViewHolder()` 做格式化、JSON 解析、同步数据库读取、Bitmap 尺寸计算，或者 `notifyDataSetChanged()` 让可复用项全部失效。
- RenderThread: 圆角裁剪、阴影、复杂 path、过大的图片纹理提交，让 draw 阶段持续超预算。
- 后台线程: 图片解码、Diff 计算、分页请求和日志上报没有限流，CPU 长时间被后台任务占用，主线程进入 runnable 但拿不到足够运行时间。
- GC: 滑动中频繁创建临时对象，`HeapTaskDaemon` 抢 CPU，Perfetto 上能看到 GC 与慢帧重叠。

处理顺序建议固定下来。先把全量刷新改成 Diff + payload，再压缩 bind 阶段的 CPU 工作量；接着检查图片尺寸和缓存命中，保证进入 bind 的图片已经是目标尺寸附近的结果；然后把分页、曝光、埋点和预取放到有界队列中，避免后台线程池让 CPU 长时间满负载。RecyclerView 复用、DiffUtil、预取和嵌套列表的细节见 22.2 节；图片加载细节见 22.6 节。

下面的代码只演示 payload 的边界：列表项结构不变时只刷新变化字段，避免一次点赞状态变化触发整项重新绑定。

```kotlin
class FeedDiff : DiffUtil.ItemCallback<FeedItem>() {
    override fun areItemsTheSame(oldItem: FeedItem, newItem: FeedItem): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: FeedItem, newItem: FeedItem): Boolean {
        return oldItem == newItem
    }

    override fun getChangePayload(oldItem: FeedItem, newItem: FeedItem): Any? {
        val changed = mutableSetOf<String>()
        if (oldItem.liked != newItem.liked) changed += "liked"
        if (oldItem.commentCount != newItem.commentCount) changed += "commentCount"
        return changed.takeIf { it.isNotEmpty() }
    }
}

class FeedViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
    fun bind(item: FeedItem) {
        bindTitle(item.title)
        bindCover(item.coverUrl)
        bindLiked(item.liked)
        bindCommentCount(item.commentCount)
    }

    fun bind(item: FeedItem, payloads: List<Any>) {
        val changed = payloads.filterIsInstance<Set<String>>().flatten().toSet()
        if ("liked" in changed) bindLiked(item.liked)
        if ("commentCount" in changed) bindCommentCount(item.commentCount)
    }
}
```

这段代码不能单独保证滑动变快，它只减少主线程 bind 工作量。改完要复测同一段 Macrobenchmark，观察 `FrameTimingMetric` 的 P95/P99 和自定义 `TraceSectionMetric("RV OnBindView")` 是否下降；如果指标没有变化，继续查图片解码、布局层级和后台线程干扰。不要把 payload 改造当作固定收益项。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]

验收口径按三档记录：

| 指标 | 用途 | 采集方式 |
| --- | --- | --- |
| `frameDurationCpuMs` P95/P99 | 判断 CPU 侧是否持续超预算 | Macrobenchmark `FrameTimingMetric` |
| 慢帧状态标签 | 判断卡顿集中在哪个页面、tab、滚动状态 | JankStats `PerformanceMetricsState` |
| `RV OnBind` / 图片解码 trace | 判断优化动作是否命中目标函数 | `Trace.beginSection()` + Perfetto |

## Compose 迁移性能踩坑

Compose 迁移后的性能问题不能简化成「Compose 比 View 慢」。更常见的情况是 View 时代隐藏在 XML、Adapter 和自定义 View 里的工作，被迁移到 composable 函数体、状态读取和 Lazy 容器里，原本只在少数时刻发生的计算变成了频繁重组中的常规工作。Compose 官方建议把昂贵计算移出 composable 函数体，用 `remember` 缓存结果，为 Lazy item 提供稳定 `key`，并避免在频繁执行的路径里写入状态。[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/bestpractices]

迁移排查可以按四类问题看：

- 函数体计算过重: 排序、过滤、时间格式化、正则匹配和资源解析不应跟着每次重组运行。能放到 ViewModel 的放到 ViewModel；必须在 UI 侧计算的，用 `remember(input)` 固定输入边界。
- Lazy item 缺少 `key`: 列表重排、插入、删除时，如果没有稳定 key，Compose 会把移动误判成删除和新建，导致可跳过的 item 重新组合。
- 子组合成本过高: 小数量标签、固定按钮组不一定适合 `LazyRow`。官方 Compose 性能 codelab 提到 Lazy 容器基于 `SubcomposeLayout`，在不需要懒加载的场景会带来额外组合开销。[已验证: 官方 codelab, developer.android.com/codelabs/jetpack-compose-performance]
- 主线程副作用: `DisposableEffect`、`LaunchedEffect` 或 composable 直接触发系统服务调用时，Perfetto 上可能出现主线程 Binder transaction。必要的系统调用保留，不必要的注册、查询和格式化要移到后台或上层状态。

下面的代码展示列表迁移时最容易漏掉的两件事：给 item 稳定 key，并把排序从 composable 函数体移出去。

```kotlin
@Composable
fun FeedScreen(
    sortedItems: List<FeedItem>,
    onOpen: (FeedItem) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(modifier = modifier) {
        items(
            items = sortedItems,
            key = { item -> item.id },
            contentType = { item -> item.type },
        ) { item ->
            FeedCard(item = item, onOpen = onOpen)
        }
    }
}
```

`sortedItems` 应由 ViewModel 或上层状态提供；`key` 让移动、插入、删除有稳定身份；`contentType` 帮 Lazy 容器复用同类 item。迁移后不要只看重组次数，单次组合耗时也要看。官方 codelab 的案例说明，一个只执行少数几次但每次很重的 composable 也能制造可见卡顿。[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/bestpractices][已验证: 官方 codelab, developer.android.com/codelabs/jetpack-compose-performance]

Compose 页面还要补两类测试：一类是 Macrobenchmark 滚动测试，验证 `FrameTimingMetric`；另一类是带 composition tracing 的 Perfetto trace，定位哪个 composable 或 lazy prefetch 段占用时间。编译器稳定性、Strong Skipping、Pausable Composition 和 Compose 编译器报告见 22.3 节；不要在案例集中重复解释机制。

## 复杂页面渲染优化

复杂页面的优化目标集中在两件事：首屏尽快可交互，后续滚动保持稳定。一个详情页可能包含头图、视频、价格区、推荐列表、评论、广告和运营浮层。如果所有模块在 `onCreate()` 或首帧前同步完成，慢帧会集中在页面打开阶段；如果都推迟到首帧后，又可能在用户刚开始滑动时集中抢 CPU。更稳妥的做法是按首屏需求把任务分成三类：首帧必须显示、首帧后立即补齐、滑动到附近才加载。

可执行的拆分规则如下：

- 首帧必须显示: 页面骨架、标题、主图占位、关键操作按钮。布局层级要短，图片先按目标尺寸占位，避免首帧后大幅改动高度。
- 首帧后立即补齐: 推荐卡片、价格细节、轻量状态。用主线程空闲期或协程调度，分批提交 UI 更新，避免一次性插入大量节点。
- 滑动到附近才加载: 评论、相关推荐、富文本、WebView、视频播放器。用占位高度稳定滚动位置，进入可见范围前再预取数据和资源。

这个拆分来自参考书中的 CPU 空闲期、I/O 分离和线程池分型思路，但页面侧必须加上帧指标约束：每批 UI 更新都要能在目标设备刷新预算内完成。60Hz 设备给 16ms 预算，120Hz 设备只有 8ms 左右；如果团队只在 60Hz 设备上验收，线上高刷设备仍可能暴露慢帧。[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md][已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

下面的流程适合作为复杂页面排查单：

```text
固定用例：冷启动进入详情页 → 等首屏稳定 → 快速滑动到评论区 → 返回顶部
采集指标：FrameTimingMetric + JankStats 状态标签 + Perfetto trace
定位线程：主线程、RenderThread、图片解码线程、网络回调线程、GC
改动顺序：首屏布局裁剪 → 图片尺寸与缓存 → 分批挂载模块 → 后台任务限流
验收条件：P95/P99 不回退，frozen frame 为 0，关键 trace section 耗时下降
```

首屏布局裁剪的细节见 22.1 节，动画和转场见 22.5 节，图片加载见 22.6 节，线上卡顿归因见 22.8 节。复杂页面的案例不要重复机制解释，只记录场景、证据、改动和验收指标。

## [自动发现] 案例复盘模板

渲染案例如果只写「优化前后提升多少」，后续很难判断结论能不能迁移。复盘建议固定记录七项内容：

| 字段 | 记录内容 |
| --- | --- |
| 场景 | 页面、入口、数据状态、设备刷新率、是否冷缓存 |
| 症状 | P95/P99、慢帧比例、frozen frame、用户可感知动作 |
| 证据 | Macrobenchmark 输出、JankStats 标签、Perfetto 关键 slice |
| 根因 | 主线程、RenderThread、GPU、I/O、GC 或后台线程干扰 |
| 改动 | 代码改动、配置改动、任务调度改动 |
| 代价 | 内存增加、预加载时机、代码复杂度、兼容边界 |
| 验收 | 同设备同用例复测结果，以及线上灰度指标 |

这个模板会让案例保留复查所需的场景、证据和验收口径。没有复测条件的结论只标「待验证」，不要写成通用建议。[已验证: 官方文档, developer.android.com/topic/performance/measuring-performance]

## 基于 AI 的渲染问题归因

AI 可以辅助做两件事：把 Perfetto trace、JankStats 标签和业务日志整理成候选原因；把历史案例按页面、线程、函数、设备和版本聚类。它不能替代指标复测，也不能直接给出收益数字。适合接入的输入是结构化数据：慢帧时间戳、页面状态、trace section 名称、线程名、提交版本、设备型号和 Android 版本。输出应限制为候选根因和下一步验证动作，例如「检查 `onBindViewHolder()` 中的图片尺寸计算」或「复测关闭某个曝光上报后的 P95」。

这类能力接入线上系统时要保留人工确认。AI 归因命中后，仍然要回到 Macrobenchmark、JankStats 和 Perfetto 做同场景复测；否则很容易把相关性写成因果关系。[待验证: AI 归因效果依赖团队历史案例库和 trace 标注质量]

## 本节验收清单

- 列表滑动案例覆盖了可重复用例、指标采集、主线程 bind、图片解码、后台线程干扰和复测口径。
- Compose 迁移案例覆盖了 `remember`、Lazy `key`、`contentType`、`SubcomposeLayout` 成本和主线程副作用。
- 复杂页面案例覆盖了首屏任务拆分、延迟加载、分批 UI 更新和高刷设备预算。
- 所有收益结论都要求用 Macrobenchmark、JankStats 或 Perfetto 复测，没有写未经验证的固定收益数字。
- 与 22.1、22.2、22.3、22.6、22.8 节只做交叉引用，没有重复展开原理。
