---
title: "Compose LazyList/LazyGrid 滑动性能深度优化"
chapter: "22.22"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-08"
last_verified_against: "Compose BOM 2025.12.00 (Compose 1.10), Kotlin 2.2, AndroidX androidx-main"
confidence: medium-high
drafted_date: "2026-06-08"
tags: [compose, lazylist, lazygrid, jank, recomposition, performance, scrolling, recycling]
related_chapters: ["22.3", "22.2", "22.20", "22.21", "7.9", "18.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-08"
gap_source: "参考书结构/章节深挖/官方文档/社区热点"
gap_score:
  素材丰富度: 4
  与全书目标相关性: 5
  读者需求度: 5
  时效性: 4
  total: 18
material_count: 5
queue_priority: 80
sources:
  - type: androidx
    path: "platform/frameworks/support/+/androidx-main/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/LazyList.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-main/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/LazyListMeasure.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-main/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/LazyListItemProvider.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-main/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutPrefetchState.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-main/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow.kt"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/lists"
  - type: research
    path: "intake/research-feeds/2026-04-01-12-compose-performance-milestone-2025.md"
---

# 22.22 Compose LazyList/LazyGrid 滑动性能深度优化

Lazy layout 把数据集总量与同时 Composition 的 item 数量分开，但它不会自动消除慢 item、错误身份、重复测量、同步 I/O 或 GPU 过载。库基线为 Compose Foundation 1.10.0，平台基线为 Android 17 / API 37 的 `android-17.0.0_r1`。Compose Foundation 独立发布，`targetSdk=37` 不会改变 LazyList 的 key、复用或预取语义。

普通 LazyColumn、LazyGrid 仍通过宿主 App Window 的标准 HWUI 路径出图。主线程上的 Composition、measure、placement 和 DisplayList 更新只是前半程，后面还有 RenderThread、GPU、buffer 提交、SurfaceFlinger、HWC 与 present。显示边界见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)，重组基础见 [22.3 Compose 性能](03-compose-performance.md)，列表动画的阶段判断见 [22.21 Compose 动画性能](21-compose-animation-performance.md)。

## 1. LazyLayout 每次滚动会做什么

`LazyColumn`、`LazyRow`、普通 Grid 和 Staggered Grid 都建立在 LazyLayout/SubcomposeLayout 一类机制上。DSL 描述整个数据集，measure policy 只为当前需要的索引请求 content。这里的“需要”通常包括可见 item，也可能包含预取、复用缓存、焦点或无障碍 beyond-bounds、sticky item 和动画保留的 item。

滚动增量不会必然触发一次完整重测。Compose 1.10.0 的 `LazyListState.onScroll()` 会尝试 `copyWithScrollDeltaWithoutRemeasure()`：

- 可见 item 集合不变、增量没有跨过边界、没有 sticky 等特殊 item 时，可以直接更新位置并只请求 placement。
- 新 item 进入、旧 item 离开、首项变化、约束变化或特殊布局条件出现时，会进入 remeasure。
- remeasure 中，`LazyListMeasuredItemProvider` 按索引取得 key、`contentType` 和 placeables；已有兼容 composition 可以复用，缺失或失效的 content 才需要执行相应 Composition。

因此，trace 中出现 Layout slice 不能直接推导“所有可见 item 都重新 Composition”。要分清 Composition、measure 和 placement，并核对本帧是否跨过 item 边界。

## 2. key 管的是业务身份

没有提供自定义 key 时，LazyLayout 使用位置生成默认 key。显式写 `key = { index -> index }` 与默认位置身份没有本质差别。列表头插入数据后，数字 key `0、1、2...` 仍然存在；变化的是这些位置现在对应了不同业务对象。常见后果包括：

- `remember` 状态可能跟着位置留给另一条数据。
- 内层 LazyRow 的滚动位置、输入状态或动画身份可能错配。
- 原本只移动位置的 item 需要按新参数更新。
- `animateItem()` 无法按业务实体识别新增、删除和移动。

这与“所有 index key 都变了，所以所有 item 一律销毁”是两种描述。前者符合位置 key 的行为，后者会误导排查。

自定义 key 必须稳定、唯一，并且在 Android 上可由 `Bundle` 保存，才能支持 item 内 `rememberSaveable` 的恢复。数据库主键、稳定的 `Long`/`String` ID 或可保存的复合 ID 都可以。`hashCode()` 可能碰撞，也可能随对象实现变化，不能替代唯一身份。

下面的列表同时声明业务身份和结构类型。

```kotlin
LazyColumn {
    items(
        items = rows,
        key = { row -> row.id },
        contentType = { row -> row.kind },
    ) { row ->
        when (row) {
            is FeedRow.Article -> ArticleRow(row)
            is FeedRow.Ad -> AdRow(row)
            is FeedRow.Divider -> DividerRow(row)
        }
    }
}
```

`id` 要在同一列表中唯一，`kind` 要反映 Composable 结构。数据移动时，LazyLayout 可以用 key 查找新索引、维持首个可见 item 的业务身份，并让保存状态跟着 item 移动。

## 3. contentType 管的是复用兼容性

`contentType` 不负责业务身份。它告诉 LazyLayout 哪些 item composition 结构兼容，可以在旧 slot 滚出后复用给新 item。默认值 `null` 也是有效类型；未提供时，所有 item 都被视为同一兼容类型。

Compose Foundation 1.10.0 的 `LazyLayoutItemReusePolicy` 用 `contentType` 相等判断 slot 是否兼容，并为每种类型最多保留 7 个可复用 slot。这个数量属于内部实现，不是开发者可依赖的 API 合同。

类型划分应遵循两条约束：

- 文章卡、广告、分隔线、加载行等结构差异明显的 item 使用不同类型。
- 同一结构、只有文本或数据不同的 item 共用一个类型。

把每个业务 ID 当作 `contentType` 会阻断跨 item 复用；把所有差异很大的结构都留为 `null`，会让 runtime 尝试在不相似的 content 之间复用。复用仍可能执行重组来写入新数据，它不等同于复制旧画面。

RecyclerView 的 `viewType` 与 Compose 的 `contentType` 都表达兼容分组，但容器、状态和复用实现不同。不能由这个对应关系推导两者内存或帧率相同。

## 4. item 状态：remember、rememberSaveable 与数据状态

普通 `remember` 只在对应 composition 存活时保留。item 滚出后可能暂时处在复用或 behind cache 中，也可能被 dispose；一旦 dispose，普通 `remember` 值会结束生命周期。稳定 key 不会让普通 `remember` 永久留在内存。

LazyLayout 用 `SaveableStateHolder` 包装 item。key 可保存时，`rememberSaveable` 可以在 item 滚出又回来时恢复，也能参与 Activity 重建恢复。需要跨滚动长期保存的少量 UI 状态可使用它；业务数据和大对象应放在 ViewModel、repository 或专用缓存中。

这也解释了嵌套 LazyRow 的状态要求：外层 item 使用稳定 key，内层用 `rememberLazyListState()`。该状态本身通过 `rememberSaveable` 保存，外层业务身份移动后仍能恢复到对应行。若外层只用位置身份，内层滚动位置可能跟错行。

### 列表数据更新时缩小无效工作

在页面层收集一份列表 State 是常见且合理的结构。列表引用更新会让读取它的作用域失效，但 LazyLayout 只为当前需要的 item 执行 content；Strong Skipping 还能跳过参数未变且满足比较条件的行。把同一 Flow 分散到每个 item 里收集，可能建立大量 collector，并不构成通用优化。

更可靠的做法包括：

- 行模型使用不可变数据，未变化的行尽量复用实例。
- Composable 参数表达当前行需要的数据，避免把整个 screen state 传进每一行。
- 回调捕获稳定 ID；让 compiler report 和 Layout Inspector 证明哪些行可跳过。
- 排序、分组、日期格式化等工作放在数据层，或按输入用 `remember` 缓存。
- item content 中禁止同步数据库、文件读取和图片解码。

`remember(item.createdAt) { formatter.format(item.createdAt) }` 能避免同一 composition 的重复计算，但 item dispose 后仍会重算。线程安全也取决于 formatter 实现，不能只从 `remember` 判断安全。

## 5. 高频滚动状态放在合适的观察位置

`LazyListState.layoutInfo` 会在每次 scroll 或 remeasure 后更新。`firstVisibleItemScrollOffset` 可随滚动频繁变化，`firstVisibleItemIndex` 只在首个可见 item 跨界时变化。把这些值直接读在大范围 Composable 中，会扩大重组作用域。

`derivedStateOf` 适合把高频输入压成低频布尔或离散结果；`snapshotFlow` 适合把滚动变化送给埋点等副作用。两者职责不同。

下面的示例让按钮只在阈值变化时重组，并把首次离开顶部作为一次副作用事件。

```kotlin
@Composable
fun ScrollSignals(
    listState: LazyListState,
    onLeftTop: () -> Unit,
) {
    val showScrollToTop by remember {
        derivedStateOf { listState.firstVisibleItemIndex > 0 }
    }
    val currentOnLeftTop by rememberUpdatedState(onLeftTop)

    LaunchedEffect(listState) {
        snapshotFlow { listState.firstVisibleItemIndex > 0 }
            .filter { it }
            .collect { currentOnLeftTop() }
    }

    AnimatedVisibility(showScrollToTop) {
        ScrollToTopButton()
    }
}
```

`derivedStateOf` 的输出只有跨过列表顶部时才改变；`snapshotFlow` 不参与绘制，只驱动回调。若 UI 需要连续视差，可在 `Modifier.offset { ... }`、draw lambda 或 `graphicsLayer` lambda 中读取 offset，把更新延后到 Layout 或 Draw 阶段。

## 6. item 边界和尺寸比“总条数”更影响首屏

LazyLayout 的虚拟化单位是 DSL 中的一个 `item`。一个 item block 同时发出多个大组件时，只要其中一部分需要显示，整块都要 Composition 和 measure；`scrollToItem()` 也只能定位到这个共同索引。分隔线很轻时可与相邻内容放在同一 item，大片内容应各有索引。

零尺寸或严重低估尺寸的 placeholder 会让容器判断一个 viewport 能容纳很多 item，从而在首轮请求更多 content。异步加载后尺寸突变，又会改变可见范围和滚动位置。图片流建议尽早给出宽高比或稳定高度；Paging placeholder 应接近加载后尺寸。

item 尺寸不必全部相同。需要关注的是尺寸计算是否稳定：

- 文本、图片比例和约束是否在加载前后大幅跳变。
- `animateContentSize`、expand/shrink 与 placement animation 是否叠加。
- item 内的 SubcomposeLayout、自定义 intrinsic 测量或多次 measure 是否出现在慢帧。
- 同一帧新进入的复杂 item 数是否过多。

列表长度达到十万条也不必然增加同屏 Composition 成本。数据容器、Paging 内存、key-index 查找、图片缓存和一次更新的差异规模仍需单独测量。

## 7. 预取运行在主线程的剩余时间里

Compose 1.10.0 默认 `LazyListPrefetchStrategy` 会根据滚动方向请求相邻的下一个 item，执行预组合和预测量；方向改变或目标失效时会取消旧请求。接近进入 viewport 时，请求可标为 urgent。

嵌套场景中，父 LazyLayout 预取到包含子 LazyList 的 item 后，会解析子预取状态。默认内层策略从当前首项开始预组合 2 个子 item，并可依据历史结果调整数量。这个过程是 best effort，数据或子树在解析后变化时不保证重新覆盖全部情况。

Android 的 `AndroidPrefetchScheduler` 通过 `View.post` 和 `Choreographer.FrameCallback` 调度请求。它估算当前帧剩余时间，并把未完成工作留到后续帧。Composition 与 measure 仍在 UI 线程；“预取”不代表后台线程构建 UI。

Compose Foundation 1.10.0 中 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 默认是 `true`。打开时，一个复杂 item 的 precomposition 可以 resume、pause，再在后续机会继续，完成后才 apply 和 premeasure。它降低单次抢占风险，仍会消耗主线程时间和内存。该 flag 是临时实验开关，项目应以锁定版本源码和回归数据为准。

### LazyLayoutCacheWindow 的边界

1.10.0 提供实验性的 `LazyLayoutCacheWindow`：

- ahead window 预先准备滚动方向前方的 item。
- behind window 保留反方向已经离开 viewport 的 item，减少快速回滚时的重建。

下面的示例展示 Dp 窗口的接入方式。

```kotlin
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CachedFeed(rows: List<FeedRow>) {
    val state = rememberLazyListState(
        cacheWindow = LazyLayoutCacheWindow(
            ahead = 200.dp,
            behind = 100.dp,
        )
    )

    LazyColumn(state = state) {
        items(rows, key = { it.id }) { row ->
            FeedRowContent(row)
        }
    }
}
```

`200.dp/100.dp` 只用于说明 API，不是推荐参数。窗口越大，越可能把 Composition/measure 提前完成，也会保留更多 composition、图片请求和状态。应以目标设备上的滚动速度、item 成本、内存峰值和 `frameOverrunMs` 决定是否采用。

## 8. 嵌套滚动先处理约束和轴向

垂直 LazyColumn 内放水平 LazyRow 是官方支持的常见结构。两个方向的手势、预取和状态仍需分别分析。自定义 `NestedScrollConnection` 要按 pre/post scroll 与 pre/post fling 协议报告 consumed 值；错误消费可能造成位移丢失、父子同时响应或速度突变。

同方向可滚动容器在子项没有有限尺寸时会遇到无限约束，典型例子是 `verticalScroll` 的 Column 内直接放无固定高度 LazyColumn。此结构会抛出 `IllegalStateException`。可选设计有：

- 合并为一个 LazyColumn，用 `item`、`items`、`stickyHeader` 表达页面段落。
- 子列表确有独立滚动语义时，给它有限高度。
- 父子使用不同滚动方向。

把 LazyRow 换成 `Row.horizontalScroll()` 会一次 Composition 全部子项，适合数据量明确且总内容小的情况。是否“小”取决于 item 成本和设备，不能用固定 20 项作为边界。

## 9. Paging 3：数据预取和 UI 预取分开理解

Paging 的 `prefetchDistance` 控制访问列表位置时何时请求更多数据；LazyLayout prefetch/cache window 控制哪些 UI item 提前 Composition、measure 或保留。两者单位与触发条件不同，参数数值无需相等。

下面的接入方式同时提供 Paging 的业务 key 和 content type。

```kotlin
val lazyPagingItems = pager.flow.collectAsLazyPagingItems()

LazyColumn {
    items(
        count = lazyPagingItems.itemCount,
        key = lazyPagingItems.itemKey { message -> message.id },
        contentType = lazyPagingItems.itemContentType { "message" },
    ) { index ->
        val message = lazyPagingItems[index]
        if (message == null) {
            MessagePlaceholder(Modifier.height(72.dp))
        } else {
            MessageRow(message)
        }
    }
}
```

`itemKey` 让已加载实体保持身份，`itemContentType` 也为 placeholder 提供 Paging 定义的兼容处理。`72.dp` 必须换成接近产品 item 的尺寸；过小 placeholder 可能让 RemoteMediator 连续加载多页，直到 viewport 被填满。

`refresh()` 会启动新的 PagingData generation。它不等于让十万条未 Composition 的 item 都执行重组。UI 成本取决于新 snapshot、当前需要的 item、key/contentType 兼容性和 load state 结构。

Paging 路径还要检查：

- `map`、`insertSeparators` 等转换放在 PagingData 流上，避免在 item body 同步做重活。
- loading/error 行有独立 key 和结构类型，动画数量受控。
- placeholder 与真实内容的尺寸接近。
- 数据加载线程、数据库查询和网络耗时与主线程 UI trace 分开归因。

## 10. Grid 与 Staggered Grid

Compose Foundation 1.10.0 已包含 `LazyVerticalStaggeredGrid` 和 `LazyHorizontalStaggeredGrid`。普通 Grid 按 line 组织 item，Staggered Grid 按 lane 安排不同主轴尺寸的 item；不能把交错布局描述成只能依赖第三方库。

普通 Grid 的 span 会影响 line 划分和每个 item 的 constraints。列数、可用宽度或 span 变化后，相关可见 line 需要重新测量。复用兼容性仍由 `contentType` 判断，内部没有公开的 `(contentType, spanSize)` 复用分组合同。

Grid 页面重点检查：

- `GridCells.Adaptive` 在窗口或折叠状态变化后是否改变列数。
- 自定义 span lambda 是否轻量，full-span header 是否过多。
- 同一 line 中高度差异是否造成额外空白或频繁尺寸变化。
- Staggered Grid 图片是否提前提供宽高比，避免加载后 lane 大幅调整。
- item placement animation 是否与列数变化同时运行。

大屏、多窗口和桌面模式下，cross-axis constraints 可能频繁变化。Android 17 平台决定窗口、VSync、FrameTimeline 和 HWUI 行为，Grid 的 line/span 算法仍由所用 Compose Foundation 版本决定。

## 11. 内存边界

LazyLayout 同时持有的内容可能来自多处：

- 当前 measure 需要的可见 item。
- 按 `contentType` 保留的可复用 slot。
- 尚未消费或取消的预取。
- cache window 的 ahead/behind item。
- 当前被 sticky、焦点、无障碍、动画或 beyond-bounds 操作固定的 item。
- `SaveableStateHolder` 保存的少量 item UI 状态。

sticky header 只在对应候选成为当前 pinned header 等需要时参与布局，不会让历史上的每个 header 永久留在 Composition。普通 `remember` 大对象在 item dispose 后可释放；图片加载库、业务缓存或 ViewModel 中的引用可能继续持有对象，需要在各自缓存中检查。

内存评估应记录稳定的用户旅程：冷启动进入列表、连续滚动、反向滚动、刷新和离开页面。比较 Java/Kotlin heap、native graphics、图片缓存和 GC pause；单次 `Debug.getMemoryInfo()` 快照无法说明对象由谁持有。

## 12. 用 Perfetto 和 Macrobenchmark 归因

测量使用 release、R8 优化、profileable 且 non-debuggable 的构建。Debug 版本的解释执行、调试检查和工具连接会放大 Lazy layout 成本。

推荐的证据顺序如下：

1. Macrobenchmark 用 UI Automator 重复同一 fling 或 drag，采集 `FrameTimingMetric`。
2. API 31 及以上查看 `frameOverrunMs`、`frameDurationCpuMs` 和 `frameCount`。
3. 在 Perfetto 的 App FrameTimeline 对齐 expected/actual，确定 late frame 和 App on-time-finish。
4. 查看主线程 Composition、measure、placement、I/O 和 ART/GC slice。
5. 查看 RenderThread、GPU、buffer post 与 SurfaceFlinger，排除图片、阴影、alpha、blur 或 buffer backpressure。
6. 用 Composition tracing 或 Layout Inspector 验证具体 item 的 composition/skip 范围。

`Choreographer#doFrame` 只覆盖 App 主线程帧回调，不能代表 GPU 完成和 present。Composition tracing 需要 runtime tracing 支持和 `track_event` 数据源；不存在通用的 `compose-recomposition` atrace 开关。`slice` 表也没有可直接求和的通用 `skipped` 列，原始 trace 的名字和版本必须先确认。

下面的 PerfettoSQL 用于列出指定交互窗口中的 App jank frame。

```sql
SELECT
    a.ts / 1e6 AS ts_ms,
    a.dur / 1e6 AS actual_dur_ms,
    a.jank_type,
    a.on_time_finish,
    a.present_type,
    a.layer_name
FROM actual_frame_timeline_slice AS a
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
  AND a.ts BETWEEN $start_ts AND $end_ts
  AND a.jank_type != 'None'
ORDER BY a.ts;
```

`$start_ts/$end_ts` 使用 trace 的纳秒时间基准。`actual_dur_ms` 是 App actual timeline slice 时长，结束点覆盖 App 的 GPU completion 与 buffer post 中较晚者；它不等同于主线程 CPU 时间。

下面的查询用于列出同一窗口内主线程最长的 slices。

```sql
SELECT
    s.ts / 1e6 AS ts_ms,
    s.dur / 1e6 AS dur_ms,
    s.name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
JOIN process AS p ON t.upid = p.upid
WHERE p.name = 'com.example.app'
  AND t.tid = p.pid
  AND s.ts BETWEEN $start_ts AND $end_ts
ORDER BY s.dur DESC
LIMIT 100;
```

先从结果识别 Compose、measure、图片、业务 trace 或 GC 相关名称，再回到时间轴核对线程状态。slice 名称会随库版本和是否开启 Composition tracing 变化，不要用固定字符串冒充跨版本指标。

如果怀疑 allocation churn，使用 allocation recording 或合适的 heap profiler 找分配栈；heap size counter 只能显示存量变化，不能给出每次分配的类型与调用点。GC 与 jank 同时出现也只说明时序相关，还要找到导致回收压力的对象来源。

## 13. Android 17 与 kernel 边界

Android 17 平台锚点是 `android-17.0.0_r1`。它提供 `Choreographer`、FrameTimeline、HWUI、窗口和系统合成路径。Compose 1.10.0 的 LazyLayout 算法打包在 App 内；升级 targetSdk 不能单独开启 Pausable Composition、cache window 或新的 item reuse policy。

kernel 锚点是 `android17-6.18-2026-06_r6`。scheduler、cpufreq、thermal、memory reclaim 和 fence wait 会改变主线程、RenderThread 或 GPU 驱动任务何时运行，但不决定 key/contentType、item disposal 和 Paging generation。只有 trace 显示 runnable delay、频率/热限制、reclaim 或 fence wait 时，才进入 kernel 证据。

## 14. LazyList 与 RecyclerView 的选型

没有脱离页面的固定胜者。Compose LazyLayout 与 RecyclerView 都支持按需创建和复用，但状态模型、布局、预取、动画和工具链不同。公开资料不能替代当前 App 的 release benchmark。

- 新 Compose 页面可优先使用 LazyLayout，并建立 key/contentType、Paging 和 Macrobenchmark 基线。
- 已稳定运行的 RecyclerView 页面无需为统一技术栈而迁移；迁移收益要覆盖 interop、功能回归和性能验证成本。
- RecyclerView item 内大量 `ComposeView` 会增加 composition 生命周期管理；LazyColumn 中大量 `AndroidView` 也会增加 View 创建、复用和桥接成本。
- 同一页面的两种实现要在相同数据、图片缓存、编译模式、设备温度和交互脚本下比较。

## 15. 检查清单

- key 是否稳定、唯一、Bundle-saveable，并代表业务实体？
- contentType 是否代表结构兼容性，是否过粗或过细？
- item 内普通 `remember` 被 dispose 后是否允许丢失？需要恢复的状态是否适合 `rememberSaveable`？
- 高频 `layoutInfo`/offset 读取发生在 Composition、Layout 还是 Draw？
- 一个 DSL item 是否塞入了过多独立内容？
- placeholder 与真实 item 的尺寸是否接近？
- 默认预取、nested prefetch 或 cache window 是否增加主线程和内存压力？
- 同方向嵌套滚动是否有有限约束？
- Paging 数据预取与 LazyLayout UI 预取是否分别测量？
- Grid 的列数、span、lane 和图片比例变化是否造成 remeasure？
- 慢帧是否由 FrameTimeline、主线程、RenderThread/GPU 和系统合成共同证明？

## 16. 源码与资料索引

Compose 行为按精确版本复核：

- [`androidx.compose.foundation:foundation:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/1.10.0/foundation-1.10.0-sources.jar)：`LazyListState.kt`、`LazyListMeasure.kt`、`LazyListPrefetchStrategy.kt`、`LazyLayout.kt`、`LazyLayoutItemContentFactory.kt`、`LazyLayoutPrefetchState.kt`、Grid 与 Staggered Grid 实现。
- [`androidx.compose.foundation:foundation-android:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.10.0/foundation-android-1.10.0-sources.jar)：`PrefetchScheduler.android.kt`。
- [`androidx.compose.runtime:runtime:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.10.0/runtime-1.10.0-sources.jar)：Snapshot、Composition 与 saveable state 的运行时边界。

平台与 kernel 固定锚点：

- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)。
- [`android17-6.18-2026-06_r6` kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)。

API、测量和诊断资料：

- [Lazy lists、grids、staggered grids、key、contentType 与 Paging](https://developer.android.com/develop/ui/compose/lists)。
- [Compose 性能实践](https://developer.android.com/develop/ui/compose/performance/bestpractices)。
- [Compose phases 与延后 State 读取](https://developer.android.com/develop/ui/compose/phases)。
- [Paging `LazyPagingItems` API](https://developer.android.com/reference/kotlin/androidx/paging/compose/LazyPagingItems)。
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)。
- [Macrobenchmark FrameTimingMetric](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)。
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)。
