---
title: "Compose LazyList 与预取调度性能"
chapter: "22.16"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Compose BOM 2026.08.00 / Foundation 与 Runtime 1.12.0 source JAR；Android 17 android-17.0.0_r1"
confidence: high
tags: [compose, lazylist, lazygrid, jank, recomposition, performance, scrolling, recycling]
related_chapters: ["22.3", "22.2", "22.15", "7.9", "18.12"]
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
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/33-compose-pausable-composition-performance.md"
---

# Compose LazyList 与预取调度性能

惰性布局（Lazy layout）把数据集总量与同时参与组合的列表项数量分开，但不会自动消除单项耗时过长、身份错误、重复测量、同步输入输出或 GPU 过载。本文以 Compose BOM 2026.08.00 对应的 Foundation 1.12.0 为库版本基线，以 Android 17、API 37 的 `android-17.0.0_r1` 为平台基线。Compose Foundation 独立发布，`targetSdk=37` 不会改变 LazyList 的键、复用或预取语义。

普通 `LazyColumn` 和惰性网格仍通过宿主应用窗口的标准 HWUI 路径生成画面。主线程上的组合（Composition）、测量（measure）、放置（placement）和 `DisplayList` 更新只是前半程，后续还有 `RenderThread`、GPU、图形缓冲区提交、`SurfaceFlinger`、硬件合成器（HWC）与送显。显示边界见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)，重组基础见 [22.3 Compose 性能](03-compose-performance.md)，列表动画的阶段判断见 [22.15 Compose 动画性能](15-compose-animation-performance.md)。

## 1. LazyLayout 每次滚动会做什么

`LazyColumn`、`LazyRow`、普通网格和交错网格都建立在 `LazyLayout`/`SubcomposeLayout` 一类机制上。DSL（用于声明列表结构的配置语法）描述整个数据集，测量策略只为当前需要的索引请求界面内容。这里的“需要”通常包括可见列表项，也可能包括预取项、复用缓存、焦点或无障碍功能要求的可见区域外项目（beyond-bounds）、粘性项目和动画暂时保留的项目。

滚动增量不一定触发一次完整重测。Compose 1.12.0 的 `LazyListState.onScroll()` 会先尝试 `copyWithScrollDeltaWithoutRemeasure()`：

- 可见列表项集合不变、增量没有跨过项目边界、也没有粘性项目等特殊情况时，可以直接更新位置，只请求放置阶段。
- 新项目进入、旧项目离开、首项变化、约束变化或特殊布局条件出现时，会重新测量。
- 重新测量时，`LazyListMeasuredItemProvider` 按索引取得键、`contentType` 和已测量的可放置对象；已有的兼容组合可以复用，缺失或失效的内容才需要执行相应组合。

因此，跟踪数据中出现布局区间，不能直接推导出“所有可见项目都重新组合”。排查时要分清组合、测量和放置，并核对本帧是否跨过项目边界。

## 2. key 管业务身份

没有提供自定义键时，`LazyLayout` 使用位置生成默认键。显式写 `key = { index -> index }` 与默认位置身份没有行为差别。列表头插入数据后，数字键 `0、1、2...` 仍然存在，但这些位置已经对应不同的业务对象。常见后果包括：

- `remember` 状态可能跟着位置留给另一条数据。
- 内层 LazyRow 的滚动位置、输入状态或动画身份可能错配。
- 原本只需移动位置的项目需要按新参数更新。
- `animateItem()` 无法按业务实体识别新增、删除和移动。

准确的描述是“位置键仍然存在，但它对应的业务对象变了”。不能写成“所有索引键都变了，所以所有项目一律销毁”，后一句不符合位置键的行为。

自定义键必须稳定、唯一，并且在 Android 上可由 `Bundle` 保存，才能支持项目内 `rememberSaveable` 的恢复。数据库主键、稳定的 `Long`/`String` ID 或可保存的复合 ID 都可以。`hashCode()` 可能碰撞，也可能随对象实现变化，不能替代唯一身份。

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

`id` 要在同一列表中唯一，`kind` 要反映可组合内容的结构。数据移动时，`LazyLayout` 可以用键查找新索引、维持首个可见项目的业务身份，并让保存状态跟随项目移动。

## 3. contentType 管复用兼容性

`contentType` 不负责业务身份。它告诉 `LazyLayout` 哪些项目的组合结构兼容，可以把滚出后的旧槽位（slot，即可复用的组合位置）交给新项目。默认值 `null` 也是有效类型；未提供时，所有项目都被视为同一兼容类型。

Compose Foundation 1.12.0 的 `LazyLayoutItemReusePolicy` 用 `contentType` 相等判断槽位是否兼容，并为每种类型最多保留 7 个可复用槽位。这个数量属于当前内部实现，不是开发者可依赖的 API 合同。

类型划分应遵循两条约束：

- 文章卡、广告、分隔线、加载行等结构差异明显的项目使用不同类型。
- 同一结构、只有文本或数据不同的项目共用一个类型。

把每个业务 ID 当作 `contentType` 会阻断跨项目复用；把差异很大的结构都留为 `null`，会让 Compose 运行时尝试在不相似的内容之间复用。复用仍可能执行重组来写入新数据，不等于复制旧画面。

RecyclerView 的 `viewType` 与 Compose 的 `contentType` 都表达兼容分组，但容器、状态和复用实现不同。不能由这个对应关系推导两者内存或帧率相同。

## 4. 项目状态：remember、rememberSaveable 与数据状态

普通 `remember` 只在对应组合存活时保留。项目滚出后可能暂时处在复用区或缓存区，也可能从组合中移除；一旦移除，普通 `remember` 值就结束生命周期。稳定键不会让普通 `remember` 永久留在内存。

`LazyLayout` 用 `SaveableStateHolder` 包装项目。键可保存时，`rememberSaveable` 可以在项目滚出又回来时恢复，也能参与 `Activity` 重建后的恢复。需要跨滚动长期保存的少量界面状态可使用它；业务数据和大对象应放在 `ViewModel`、数据仓库或专用缓存中。

嵌套 `LazyRow` 的状态也遵循这条规则：外层项目使用稳定键，内层使用 `rememberLazyListState()`。该状态本身通过 `rememberSaveable` 保存，外层业务身份移动后仍能恢复到对应行。若外层只用位置身份，内层滚动位置可能跟错行。

### 列表数据更新时缩小无效工作

在页面层收集一份列表 `State` 是常见结构。列表引用更新会让读取它的作用域失效，但 `LazyLayout` 只为当前需要的项目执行内容；强跳过模式（Strong Skipping）还能跳过参数未变且满足比较条件的行。把同一个 `Flow` 分散到每个项目中收集，可能建立大量收集协程，不能作为通用优化。

更可靠的做法包括：

- 行模型使用不可变数据，未变化的行尽量复用实例。
- 可组合函数参数只表达当前行需要的数据，避免把整个页面状态传进每一行。
- 回调捕获稳定 ID；用编译器报告和 Layout Inspector 确认哪些行可以跳过。
- 排序、分组、日期格式化等工作放在数据层，或按输入用 `remember` 缓存。
- 项目内容中不要同步执行数据库查询、文件读取和图片解码。

`remember(item.createdAt) { formatter.format(item.createdAt) }` 能避免同一次组合生命周期内重复计算，但项目离开组合后仍会重算。线程安全也取决于格式化器实现，不能只从 `remember` 判断安全。

## 5. 高频滚动状态放在合适的观察位置

`LazyListState.layoutInfo` 会在每次滚动或重新测量后更新。`firstVisibleItemScrollOffset` 可随滚动频繁变化，`firstVisibleItemIndex` 只在首个可见项目跨界时变化。把这些值直接读在大范围可组合函数中，会扩大重组作用域。

`derivedStateOf` 适合把高频输入转换成低频布尔值或离散结果；`snapshotFlow` 适合把滚动变化发送给埋点等副作用逻辑。前者控制状态通知频率，后者把 Compose 状态转换成可收集的数据流。

下面的示例让按钮只在阈值变化时重组；每次回到顶部后再次离开，都会触发一次副作用回调。

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

`derivedStateOf` 的输出只有跨过列表顶部时才改变；`snapshotFlow` 不参与绘制，只驱动回调。若界面需要连续视差，可在 `Modifier.offset { ... }`、绘制回调或 `graphicsLayer` 回调中读取偏移量，把更新延后到布局或绘制阶段。

## 6. 项目边界和尺寸比总条数更影响首屏

`LazyLayout` 的虚拟化单位是 DSL 中的一个 `item`。一个项目代码块同时生成多个大型组件时，只要其中一部分需要显示，整个代码块都要参与组合和测量；`scrollToItem()` 也只能定位到这个共同索引。分隔线很轻时可以与相邻内容放在同一项目，大块内容则应各有索引。

零尺寸或严重低估尺寸的占位内容（placeholder），会让容器判断一个可见区域（viewport）能容纳很多项目，从而在首轮请求更多内容。异步加载后尺寸突变，又会改变可见范围和滚动位置。图片流应尽早给出宽高比或稳定高度；Paging 占位内容应接近加载后的尺寸。

项目尺寸不必全部相同，需要检查尺寸计算是否稳定：

- 文本、图片比例和约束是否在加载前后大幅跳变。
- `animateContentSize`、展开/收缩与位置动画是否叠加。
- 项目内的 `SubcomposeLayout`、自定义固有尺寸（intrinsic）测量或多次测量是否出现在慢帧。
- 同一帧新进入的复杂项目是否过多。

列表长度达到十万条也不一定增加同屏组合成本。数据容器、Paging 内存、键到索引的查找、图片缓存和单次更新的差异规模仍需单独测量。

## 7. 预取运行在主线程的剩余时间里

Compose 1.12.0 默认的 `LazyListPrefetchStrategy` 会根据滚动方向请求相邻的下一个项目，执行预组合和预测量；方向改变或目标失效时会取消旧请求。项目接近可见区域时，请求可标为紧急：只要本帧仍有剩余时间就可以执行，不再要求剩余时间超过该步骤的历史平均耗时。

嵌套场景中，父 `LazyLayout` 预取到包含子 LazyList 的项目后，会解析子列表的预取状态。默认内层策略从当前首项开始预组合 2 个子项目，并可依据历史结果调整数量。嵌套预取采用尽力而为（best effort）策略；数据或子树在解析后发生变化时，不保证重新覆盖所有情况。

Android 的 `AndroidPrefetchScheduler` 通过 `View.post` 和 `Choreographer.FrameCallback` 调度请求。它用 `View.drawingTime`、最近一次帧起点和显示刷新周期估算当前帧的剩余时间，把未完成工作留到后续帧。组合与测量仍在界面线程执行；“预取”不表示后台线程会构建界面。

Compose Foundation 1.12.0 中，实验性回退标志 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 默认是 `true`。启用后，复杂项目的预组合可以多次恢复和暂停，后续有预算时再继续；组合完成后才应用结果并预测量。这样可以缩短单次占用主线程的时间，但不会消除主线程和内存成本。`ComposeFoundationFlags` 允许应用在遇到回归时临时关闭新路径，但官方将这些标志定义为临时入口，不能依赖它们长期存在。

### LazyLayoutCacheWindow 的边界

1.12.0 的 `LazyLayoutCacheWindow` 仍标注为实验 API：

- 前向窗口（ahead window）预先准备滚动方向前方的项目。
- 后向窗口（behind window）保留反方向上已经离开可见区域的项目，减少快速回滚时的重建。

窗口既可用 `Dp` 指定，也可按可见区域比例指定。两种形式表达的是缓存范围，不是项目数量。

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

`200.dp/100.dp` 只用于说明 API，不是推荐参数。窗口越大，越可能提前完成组合和测量，也会保留更多组合、图片请求和状态。是否采用及窗口大小，应根据目标设备上的滚动速度、项目成本、内存峰值和 `frameOverrunMs` 决定。

## 8. 嵌套滚动先处理约束和轴向

垂直 `LazyColumn` 内放水平 `LazyRow` 是官方支持的常见结构。两个方向的手势、预取和状态仍需分别分析。自定义 `NestedScrollConnection` 要按滚动前/后与惯性滚动前/后的协议报告已消费位移或速度；错误的消费值可能造成位移丢失、父子同时响应或速度突变。

同方向可滚动容器在子项没有有限尺寸时会遇到无限约束，典型例子是在带 `verticalScroll` 的 `Column` 内直接放入没有固定高度的 `LazyColumn`。此结构会抛出 `IllegalStateException`。可选设计包括：

- 合并为一个 LazyColumn，用 `item`、`items`、`stickyHeader` 表达页面段落。
- 子列表确有独立滚动语义时，给它有限高度。
- 父子使用不同滚动方向。

把 `LazyRow` 换成 `Row.horizontalScroll()` 会一次组合全部子项，适合数据量明确且总内容较少的情况。能否承受取决于项目成本和设备，不能用固定 20 项作为边界。

## 9. Paging 3：数据预取和界面预取分开理解

Paging 的 `prefetchDistance` 控制访问列表位置时何时请求更多数据；`LazyLayout` 的预取和缓存窗口控制哪些界面项目提前组合、测量或保留。两者的单位与触发条件不同，参数数值无需相等。

下面的接入方式同时提供 Paging 的业务键和内容类型。

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

`itemKey` 让已加载实体保持身份，`itemContentType` 也为占位内容提供 Paging 定义的兼容处理。`72.dp` 必须换成接近产品项目的尺寸；占位内容过小，可能让负责远端与本地数据协调的 `RemoteMediator` 连续加载多页，直到可见区域被填满。

`refresh()` 会启动新一代 `PagingData` 数据流，不会让十万条尚未进入组合的项目全部重组。界面成本取决于新的数据快照、当前需要的项目、键/`contentType` 兼容性和加载状态结构。

Paging 路径还要检查：

- `map`、`insertSeparators` 等转换放在 `PagingData` 数据流上，避免在项目函数体中同步执行耗时工作。
- 加载/错误行有独立键和结构类型，动画数量受控。
- 占位内容与真实内容的尺寸接近。
- 数据加载线程、数据库查询和网络耗时与主线程界面跟踪数据分开分析。

## 10. 网格与交错网格

Compose Foundation 1.12.0 包含 `LazyVerticalStaggeredGrid` 和 `LazyHorizontalStaggeredGrid`。普通网格按行（line）组织项目，交错网格按轨道（lane）安排主轴尺寸不同的项目；交错布局不需要依赖第三方库。

普通网格的跨列数（span）会影响行划分和每个项目的尺寸约束。列数、可用宽度或跨列数变化后，相关可见行需要重新测量。复用兼容性仍由 `contentType` 判断，公开 API 没有承诺按 `(contentType, spanSize)` 组合分组复用。

网格页面重点检查：

- `GridCells.Adaptive` 在窗口或折叠状态变化后是否改变列数。
- 自定义跨列数回调是否轻量，跨满整行的标题是否过多。
- 同一行中高度差异是否造成额外空白或频繁尺寸变化。
- 交错网格图片是否提前提供宽高比，避免加载后轨道大幅调整。
- 项目位置动画是否与列数变化同时运行。

大屏、多窗口和桌面模式下，交叉轴尺寸约束可能频繁变化。Android 17 平台决定窗口、VSync、`FrameTimeline` 和 HWUI 行为，网格的行/跨列算法仍由所用 Compose Foundation 版本决定。

## 11. 内存边界

`LazyLayout` 同时持有的内容可能来自多处：

- 当前测量需要的可见项目。
- 按 `contentType` 保留的可复用槽位。
- 尚未消费或取消的预取。
- 缓存窗口中的前向/后向项目。
- 当前被粘性定位、焦点、无障碍、动画或可见区域外操作固定的项目。
- `SaveableStateHolder` 保存的少量项目界面状态。

粘性标题只在候选项成为当前固定标题等需要时参与布局，不会让历史上的每个标题永久留在组合中。项目离开组合后，普通 `remember` 持有的大对象可以释放；图片加载库、业务缓存或 `ViewModel` 中的引用可能继续持有对象，需要分别检查这些缓存。

内存评估应记录稳定的用户流程：冷启动进入列表、连续滚动、反向滚动、刷新和离开页面。比较 Java/Kotlin 堆、原生图形内存、图片缓存和垃圾回收（GC）停顿；单次 `Debug.getMemoryInfo()` 快照无法说明对象由谁持有。

## 12. 用 Perfetto 和 Macrobenchmark 归因

测量应使用发布（release）、启用 R8 优化、可分析（profileable）且不可调试（non-debuggable）的构建。Debug 版本的解释执行、调试检查和工具连接会放大惰性布局成本。

推荐的证据顺序如下：

1. Macrobenchmark 用 UI Automator 重复同一次惯性滚动或拖动，采集 `FrameTimingMetric`。
2. API 31 及以上查看 `frameOverrunMs`、`frameDurationCpuMs` 和 `frameCount`。
3. 在 Perfetto 的应用 `FrameTimeline` 中对齐预期/实际时间线，确定哪些帧迟到，以及应用是否按时完成。
4. 查看主线程上的组合、测量、放置、输入输出和 ART/GC 区间。
5. 查看 `RenderThread`、GPU、图形缓冲区入队与 SurfaceFlinger，排查图片、阴影、透明度、模糊或缓冲区反压。
6. 用组合跟踪（Composition tracing）或 Layout Inspector 验证具体项目的组合/跳过范围。

`Choreographer#doFrame` 只覆盖应用主线程帧回调，不能代表 GPU 完成和送显。组合跟踪需要 Compose Runtime 的跟踪支持与 Perfetto `track_event` 数据源；系统没有通用的 `compose-recomposition` atrace 开关。Perfetto 的 `slice` 表记录有起止时间的区间事件，也没有可直接求和的通用 `skipped` 列。写查询前要确认当前版本产生的区间名称和字段。

下面的 PerfettoSQL 用于列出指定交互时间段中的应用卡顿帧。

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

`$start_ts/$end_ts` 使用跟踪数据的纳秒时间基准。`actual_dur_ms` 是应用实际帧时间线区间的时长，结束点取应用 GPU 完成与图形缓冲区入队中较晚的时刻；它不等同于主线程 CPU 时间。

下面的查询用于列出同一时间段内主线程最长的区间事件。

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

先从结果中识别 Compose、测量、图片、业务跟踪或 GC 相关名称，再回到时间轴核对线程状态。区间名称会随库版本和是否开启组合跟踪而变化，不能把固定字符串当成跨版本指标。

如果怀疑对象频繁分配和回收，应使用分配记录（allocation recording）或合适的堆分析器（heap profiler）查找分配调用栈；堆大小计数器只能显示存量变化，不能给出每次分配的类型与调用点。GC 与卡顿同时出现只说明时间上相关，还要找出造成回收压力的对象来源。

## 13. PausableComposition：只切分预组合阶段

`PausableComposition` 是 Compose Runtime 提供的可暂停子组合状态机，Foundation 的惰性预取决定是否使用它。它不会把所有组合自动改成可暂停，也不能切分测量、图片解码、Binder、GPU 或任意 Kotlin 代码。Foundation 1.12.0 把一次预取分成组合、应用、嵌套预取和测量；只有组合阶段能在编译器生成的合法可重启作用域边界暂停。

公开控制流是 `setPausableContent()` → 多次 `resume(shouldPause)` → `apply()`。`shouldPause=true` 只是暂停请求，当前调用可能继续到下一个合法边界；组合完成后，如果已读取的 `State` 在 `apply()` 前发生变化，`isComplete` 也可能恢复为 `false`。`cancel()` 后创建该暂停句柄的组合处于不确定状态，必须丢弃；异常也会让暂停组合失效。因此，普通业务代码通常不应直接构造和管理它。

Android 端预取调度器在主线程消息队列的帧间空隙运行。Foundation 1.12.0 使用 `View.drawingTime`、最近一次帧起点、静态缓存的显示刷新周期，以及历史组合/测量成本判断是否还有预算；它不直接读取 Android 17 `FrameData` 的截止时间。平台首选 `FrameTimeline` 与 Compose 预取预算来自不同数据源，跟踪分析时要分别记录。

`LazyLayoutCacheWindow` 决定前方准备和后方保留的范围，`PausableComposition` 只改变候选项目的组合调度。扩大前向窗口会增加 CPU 预取，扩大后向窗口会延长节点、状态和图片资源的生命周期。判断回归时，应分别查看 `compose:lazy:prefetch:*` 中的 `compose`、`apply`、`measure` 区间、下一帧启动时间、`FrameTimeline` 超期时间与内存峰值。组合区间变短而应用或测量区间仍然很长，预取仍可能造成卡顿。

业务优化顺序仍是提供稳定键和合适的 `contentType`、移出同步输入输出与复杂转换、稳定项目尺寸，再调整缓存窗口与预取。A/B 实验要记录版本标志、显示刷新率、数据集、构建类型和设备热状态；“升级到某版 Compose”不能代替实验数据。

## 14. Android 17 与内核边界

Android 17 平台基线是 `android-17.0.0_r1`。它提供 `Choreographer`、`FrameTimeline`、HWUI、窗口和系统合成路径。Compose 1.12.0 的 `LazyLayout` 算法打包在应用内；升级 `targetSdk` 不能单独开启可暂停组合、缓存窗口或新的项目复用策略。

内核基线是 `android17-6.18-2026-06_r6`。内核调度器、CPU 调频（cpufreq）、热限制（thermal）、内存回收和同步栅栏等待（fence wait）会改变主线程、`RenderThread` 或 GPU 驱动任务何时运行，但不决定键/`contentType`、项目移除和 `PagingData` 代际。只有跟踪数据出现线程可运行但迟迟未获调度、频率或热限制、内存回收或栅栏等待时，才需要检查内核证据。

## 15. LazyList 与 RecyclerView 的选型

不存在脱离页面场景的固定胜者。Compose `LazyLayout` 与 `RecyclerView` 都支持按需创建和复用，但状态模型、布局、预取、动画和工具链不同。公开资料不能替代当前应用的发布版基准测试。

- 新 Compose 页面可优先使用 `LazyLayout`，并建立键/`contentType`、Paging 和 Macrobenchmark 基线。
- 已稳定运行的 `RecyclerView` 页面无需只为统一技术栈而迁移；迁移收益要覆盖互操作、功能回归和性能验证成本。
- `RecyclerView` 项目内大量使用 `ComposeView` 会增加组合生命周期管理；`LazyColumn` 中大量使用 `AndroidView` 也会增加 View 创建、复用和桥接成本。
- 同一页面的两种实现要在相同数据、图片缓存、编译模式、设备温度和交互脚本下比较。

## 16. 检查清单

- 键是否稳定、唯一、可由 `Bundle` 保存，并代表业务实体？
- `contentType` 是否代表结构兼容性，划分是否过粗或过细？
- 项目离开组合后，普通 `remember` 状态是否允许丢失？需要恢复的状态是否适合 `rememberSaveable`？
- 高频 `layoutInfo`/偏移量读取发生在组合、布局还是绘制阶段？
- 一个 DSL 项目是否包含过多独立内容？
- 占位内容与真实项目的尺寸是否接近？
- 默认预取、嵌套预取或缓存窗口是否增加主线程和内存压力？
- 同方向嵌套滚动是否有有限约束？
- Paging 数据预取与 `LazyLayout` 界面预取是否分别测量？
- 网格的列数、跨列数、轨道和图片比例变化是否造成重新测量？
- 慢帧是否由 `FrameTimeline`、主线程、`RenderThread`/GPU 和系统合成共同证明？

## 17. 源码与资料索引

Compose 行为按 BOM 2026.08.00 与 1.12.0 source JAR 复核：

- [Compose BOM 2026.08.00 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom)。
- [`androidx.compose.foundation:foundation:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/1.12.0/foundation-1.12.0-sources.jar)：`LazyListState.kt`、`LazyListMeasure.kt`、`LazyListPrefetchStrategy.kt`、`LazyLayout.kt`、`LazyLayoutItemContentFactory.kt`、`LazyLayoutPrefetchState.kt`、网格与交错网格实现。
- [`androidx.compose.foundation:foundation-android:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.12.0/foundation-android-1.12.0-sources.jar)：`PrefetchScheduler.android.kt`。
- [`androidx.compose.runtime:runtime:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.12.0/runtime-1.12.0-sources.jar)：`PausableComposition.kt`、Snapshot、Composition 与可保存状态的运行时边界。

以下 1.10.0 链接保留为上一轮核验基线：

- [`androidx.compose.foundation:foundation:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/1.10.0/foundation-1.10.0-sources.jar)：`LazyListState.kt`、`LazyListMeasure.kt`、`LazyListPrefetchStrategy.kt`、`LazyLayout.kt`、`LazyLayoutItemContentFactory.kt`、`LazyLayoutPrefetchState.kt`、Grid 与 Staggered Grid 实现。
- [`androidx.compose.foundation:foundation-android:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.10.0/foundation-android-1.10.0-sources.jar)：`PrefetchScheduler.android.kt`。
- [`androidx.compose.runtime:runtime:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.10.0/runtime-1.10.0-sources.jar)：Snapshot、Composition 与 saveable state 的运行时边界。

平台与内核固定基线：

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
