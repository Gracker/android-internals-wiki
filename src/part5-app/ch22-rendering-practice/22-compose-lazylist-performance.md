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

Compose 重组控制的基础机制（Stability、Strong Skipping Mode、derivedStateOf）在 §22.3 已详细说明。本节聚焦 LazyColumn / LazyRow / LazyGrid 在滑动场景下的性能行为：key 和 contentType 对 item 复用的影响、item 内部重组范围控制、预取机制源码行为、嵌套滚动、Paging 3 集成、以及 Perfetto 诊断 SQL 模板。

本节使用 **Compose BOM 2025.12.00（Compose 1.10）** 作为版本基线。LazyList 的内部实现（预取、item pool、Pausable Composition）取决于 Compose Foundation 版本，不由 Android 平台版本决定。[已验证: AndroidX androidx-main, Compose Foundation 1.10]

## LazyList 滑动卡顿的分类与归因

LazyList 滑动时的帧超时可以归入四类瓶颈，排查时按顺序排除：

**1. 重组开销**：item Composable 的重组范围过大或参数不稳定，导致滑动时每个可见 item 都被重新组合。在 Perfetto 中表现为 Composition 阶段的 CPU slice 持续占据主线程。Strong Skipping（§22.3）减少了 lambda 参数导致的无效重组，但如果 item 内部读取了高频变化的 `State`，重组仍然无法跳过。

**2. 布局计算开销**：嵌套 LazyList（水平列表嵌在垂直列表 item 内）、自定义 `Layout` 的 measure policy 中存在 O(n²) 遍历、或者 `SubcomposeLayout` 在 item 内部使用。Perfetto 中 Layout 阶段的 slice 占比异常。

**3. 数据加载耗时**：item 绑定数据时触发同步 IO（图片解码、数据库查询、SharedPreferences 读取）。Perfetto 中能看到主线程上的 IO wait slice。

**4. GC / 内存抖动**：item 创建大量临时对象（lambda、Pair、data class 实例），高频滑动时 GC 暂停累积。Perfetto 中通过 `android.java.heap_stats` 数据源可以看到 GC pause 与帧 timeline 的叠加。

归因路径：先用 Perfetto 的帧 timeline 定位掉帧位置 → 检查对应帧的 Composition / Layout / Draw 阶段耗时 → 如果 Composition 占比高，检查 item 是否有不稳定参数 → 如果 Layout 占比高，检查嵌套 LazyList 或自定义 Layout → 如果帧内有 IO slice 或 GC pause，走第 3/4 类排查。具体 SQL 模板见本节后半部分。

## key 与 contentType 的性能影响

### key：item 身份追踪与复用

`key {}` 的作用是为 LazyList 中的每个 item 提供稳定的身份标识。Compose Runtime 用 key 追踪 Composable 实例在列表中的位置变化——当列表数据发生增删或移动时，相同 key 的 item 会被复用而不是重新创建。[已验证: AndroidX androidx-main, LazyListItemProvider.kt]

```kotlin
LazyColumn {
    items(
        count = list.size,
        key = { index -> list[index].stableId }
    ) { index ->
        ItemContent(list[index])
    }
}
```

**错误用例——用 index 做 key**：

```kotlin
// key = index → 列表头部插入新 item 时，所有 item 的 key 都变了
// Runtime 认为每个位置的 item 都是"新的"，触发全部重组
items(
    count = list.size,
    key = { index -> index }  // 错误：index 不稳定
) { index -> ... }
```

当列表头部插入一条数据时，index-based key 导致所有 item 的身份重排。Runtime 执行的是"销毁旧 item → 创建新 item"而非"移动已有 item"，重组范围覆盖整个可见区域。如果 item 有复杂的子树（图片 + 多行文本 + 动画），这个开销在 Perfetto 中表现为连续多帧的 Composition 峰值。

**正确做法**：使用业务唯一标识（数据库主键、UUID、组合键）作为 key。如果数据源没有天然唯一标识，用 `hashCode()` 或 `Objects.hash(field1, field2)` 作为备选。

**对列表更新动画的影响**：key 的稳定性直接影响 `LazyLayoutItemAnimator` 的动画效果。stable key + 数据移动 = 位移动画；index key + 数据移动 = 淡入淡出动画（因为 Runtime 认为旧位置 item 被删除、新位置 item 被创建）。

### contentType：item pool 分池回收

`contentType` 是 Compose 1.4 引入的 LazyList API，作用是按类型标记 item，让 LazyList 内部的 item pool 按类型分池回收。[已验证: AndroidX androidx-main, LazyListIntervalContent.kt]

```kotlin
LazyColumn {
    items(
        count = list.size,
        key = { index -> list[index].stableId },
        contentType = { index -> if (list[index].isAd) "ad" else "content" }
    ) { index ->
        if (list[index].isAd) AdItem(list[index]) else ContentItem(list[index])
    }
}
```

没有 contentType 时，LazyList 的 item pool 是一个统一池——滚出屏幕的 ad item 会被复用来显示 content item，触发完全的子树重组（因为 Composable 结构不同）。加上 contentType 后，pool 按 type 分区：ad item 只复用给 ad，content item 只复用给 content，减少子树结构的差异。

**适用场景**：列表中有两种以上结构性不同的 item 类型（如内容 + 广告 + 分隔线 + 加载指示器）。单一 item 类型的列表不需要 contentType。

**与 RecyclerView 的对应关系**：RecyclerView 的 `getItemViewType()` + `RecycledViewPool` 做的事情和 Compose 的 contentType 是同一件事。RecyclerView 默认按 viewType 分池，每个类型默认缓存 5 个 ViewHolder；Compose LazyList 的 contentType 机制在 Foundation 层自动管理池大小，开发者不需要手动调参。

## 重组范围控制：LazyList item 内部的状态管理

§22.3 介绍了 Compose 重组控制的基础机制。本节补充 LazyList item 内部的状态管理对滑动性能的影响。

### 不稳定 lambda 导致的整列表重组

LazyList item 接收的 lambda 参数如果不稳定（每次父重组都创建新实例），会导致所有可见 item 被重新组合。Strong Skipping（Kotlin 2.0.20+）自动 memoize lambda，但在以下场景仍然会失效：

```kotlin
@Composable
fun MyList(viewModel: MyViewModel) {
    val items by viewModel.items.collectAsState()
    LazyColumn {
        items(count = items.size, key = { items[it].id }) { index ->
            val item = items[index]
            // 每次父重组都创建新的 onClick lambda
            // Strong Skipping 会 memoize，但如果 lambda 捕获了变化的值，
            // memoize 的结果仍然是新实例（因为捕获值变了）
            ItemRow(
                item = item,
                onClick = { viewModel.handleClick(item.id) }  // 捕获 item.id
            )
        }
    }
}
```

当 `viewModel.items` 更新时，整个 `MyList` 重组。如果 `ItemRow` 的 `onClick` lambda 捕获了 `item.id`（这个值在 items 变化时可能没变），Strong Skipping 的 memoize 机制会比较捕获值：如果 `item.id` 没变，lambda 复用旧实例，`ItemRow` 跳过重组。

但如果 item 数据本身是 `val items by viewModel.items.collectAsState()`，State 读取在 LazyColumn 外层建立了订阅。items 的任何变化（包括单条更新）都会触发 `MyList` 重组。解决方案是缩小 State 读取范围——把 `collectAsState()` 的读取放到 item 内部，或者用 `derivedStateOf` 派生出 item 粒度的状态。[详见 §22.3 derivedStateOf 模式]

### remember 在 item 内部的使用模式

LazyList item 内部使用 `remember` 时需要注意：item 滚出屏幕再滚回来时，如果 key 没变，`remember` 的缓存仍然有效；如果 key 变了，`remember` 重新初始化。

```kotlin
@Composable
fun ItemRow(item: ItemData) {
    // 如果 item 的 key 没变，这个 remember 的值会被复用
    val formattedDate = remember(item.createdAt) {
        dateFormat.format(item.createdAt)
    }
    Text(formattedDate)
}
```

`remember(item.createdAt)` 的 key 是 `createdAt`——只要 key（由 LazyList 的 `key {}` 提供）和 `createdAt` 都没变，`formattedDate` 不会重新计算。这比在 `Text()` 参数里直接调用 `dateFormat.format()` 更高效，因为后者在每次重组时都执行。

### derivedStateOf 在 LazyList 中的典型模式

`derivedStateOf` 在 LazyList 中最常见的用法是过滤高频状态变化，只让"越过阈值"的事件触发重组：

```kotlin
@Composable
fun ScrollToTopButton(listState: LazyListState) {
    // listState.firstVisibleItemIndex 每帧都可能变
    // derivedStateOf 只在 isCollapsed 的值变化时触发重组
    val isCollapsed by remember {
        derivedStateOf { listState.firstVisibleItemIndex > 5 }
    }
    AnimatedVisibility(visible = isCollapsed) {
        IconButton(onClick = {
            // 使用 rememberCoroutineScope 启动滚动
        }) { Icon(Icons.Default.ArrowUpward, "scroll to top") }
    }
}
```

如果不加 `derivedStateOf`，`listState.firstVisibleItemIndex` 的每一帧变化都会触发 `ScrollToTopButton` 重组。加上后，只有 `index > 5` 的结果从 false 变成 true（或反过来）时才重组。


<!-- AIW-源码调研-2026-06-24 -->
## SlotTable 与 RecomposeScope：LazyList 性能行为的运行时底座

§22.22 上文讨论的 key / contentType / derivedStateOf 都只是 Compose Runtime 提供的"用户层杠杆"。要理解为什么这些杠杆有效，需要直接看 androidx-main 的 `SlotTable` 数据结构。本节从源码角度补充 LazyList 滚动时 SlotTable 实际发生的事。

### SlotTable 的双 IntArray + gap buffer 结构

`compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SlotTable.kt` 中 `internal class SlotTable`（line 82）持有两个核心数组：

- `groups: IntArray` —— 存储 group fields，每个 group 占用 `Group_Fields_Size` 个连续 int（key / nodeCount / groupSize / parentAnchor / dataAnchor + flags）
- `slots: Array<Any?>` —— 存储 Composable 实际状态值（`remember` 结果、CompositionLocal 等）

源码注释（`SlotTable.kt:31-77` 的 `Nomenclature` 段落）明确定义了 Anchor 的语义：

> Anchor — an encoding of Index that allows it to not need to be updated when groups or slots are inserted or deleted. An anchor is positive if the Index it is tracking is before the gap and negative if it is after the gap.

这一设计是 Compose 滚动不移动状态引用、RecomposeScope 命中稳定的根本原因。LazyList 滚出 item 时，对应 group 被删除（gap 移动到该位置）；RecomposeScope 通过 Anchor 仍能命中 gap 之后的真实位置。

### LazyList 的 subcomposition 路径

源码 `compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/LazyListMeasuredItemProvider.kt:46`：

```kotlin
fun getAndMeasure(index: Int): LazyListMeasuredItem {
    val key = itemProvider.getKey(index)
    val contentType = itemProvider.getContentType(index)
    val placeables = measureScope.measure(index, childConstraints)
    return createItem(index, key, contentType, placeables)
}
```

调用链：`measureLazyList`（`LazyListMeasure.kt:43`）→ 对每个可见 item 调 `getAndMeasure` → `LazyLayoutMeasureScope.measure(index, ...)` → `SubcomposeLayout.subcompose(slotId, content)` → `Composer` 在 SlotTable 上开 `SlotWriter` 写新 group。每次 `subcompose` 都会触碰 `anchors: ArrayList<Anchor>`（`SlotTable.kt:133`）并走 `ArrayList.search` 二分查找（`SlotTable.kt:3370`）。

### 对性能排查的具体含义

1. **滚动卡顿如果是 Composition 阶段占比高**：怀疑 item 内部 `State` 写入频繁 → RecomposeScope 频繁 invalid → 多次重写 SlotTable。`derivedStateOf` 把高频 state 转成低频派生是最直接的修复。
2. **如果是 Layout 阶段占比高**：检查是否有嵌套 LazyList 或 `SubcomposeLayout` 在 item 内被调用 —— 因为 `SubcomposeLayout` 会在每次 measure 时强制重走 SlotWriter 路径。
3. **如果是 GC 暂停叠加**：检查 `key {}` 是否稳定。`key = index` 会让 list 头部插入新 item 时所有 group 被销毁重建，groups 数组触发扩容。
4. **预取的内存代价**：`LazyLayoutPrefetchState.schedulePrefetch(index, ...)`（`LazyLayoutPrefetchState.kt:30`）会让 prefetcher 提前对远端 item 调 `measureScope.measure`，这些 item 也会进入 SlotTable。默认 prefetch 策略较保守；自定义时要权衡"少 subcomposition 延迟"和"多 SlotTable 内存占用"。

### 与已有 best practices 的对应关系

| §22.22 上层建议 | SlotTable 底层机制 |
|----------------|------------------|
| `key {}` 必须稳定 | 避免 Anchor 失效 → 避免 group 树频繁插入 / 删除 → 避免 `IntArray` 扩容 |
| `contentType` 分池 | 相同 contentType 的 item 复用 group 节点，slots 数组增量更新 |
| `derivedStateOf` | 减少 RecomposeScope.invalidate 调用次数 → 减少 `Composer.invalidations` 队列长度 |
| `remember(calculation) { ... }` | 让结果进入 `slots: Array<Any?>` 一次，多次 recomposition 命中已有 slot 而非重新计算 |

[源码锚点: androidx-compose-integration-release / SlotTable.kt (3480行) / LazyListMeasure.kt (580行) / LazyListState.kt (509行) / LazyLayoutPrefetchState.kt (61行) / LazyListMeasuredItemProvider.kt (64行)]

## LazyList 预取、子项合成与嵌套滚动

### 预取机制源码行为

LazyList 的预取在 `LazyLayoutPrefetchState` 中实现。当用户滑动时，LazyList 根据滑动方向和速度，提前组合（precompose）即将进入视口的 item。[已验证: AndroidX androidx-main, LazyLayoutPrefetchState.kt]

预取的触发点在 `LazyLayout` 的 measure 阶段结束后。`LazyLayoutPrefetchState` 通过 `schedulePrecomposition(index)` 或 `schedulePrecompositionAndPremeasure(index, constraints)` 调度预取任务。前者只做 Composition，后者同时做 Composition + Measure。

**预取与 Pausable Composition 的关系**：Compose 1.10 引入的 Pausable Composition（§22.3）允许预取的 Composition 工作被切分成可暂停的块。当帧预算不足时，预取的 Composition 被暂停，下一帧继续。这避免了预取阻塞当前帧的渲染。但 Pausable Composition 在 Compose Foundation 1.10.6 中因稳定性问题被默认禁用，使用前需确认目标 Foundation 版本的默认 flag 状态。[已验证: Compose Foundation 1.10 release notes]

**预取窗口控制**：`LazyLayoutCacheWindow` API（Compose 1.9）允许自定义预取窗口：

```kotlin
val listState = rememberLazyListState(
    firstVisibleItemIndex = 0,
    firstVisibleItemScrollOffset = 0,
    cacheWindow = LazyLayoutCacheWindow(ahead = 150.dp, behind = 100.dp)
)
```

`ahead` 控制滑动方向前方的预取距离，`behind` 控制反方向的缓存距离。简单 item（纯文本）不需要大的预取窗口；复杂 item（图片 + 多行文本）适当增大 `ahead` 可以减少首次可见时的组合卡顿。

### 嵌套 LazyList 的子项复用

嵌套 LazyList（水平 LazyRow 作为垂直 LazyColumn 的 item）的预取行为分两层：

1. 外层 LazyColumn 预取即将可见的 item（包括内部的 LazyRow）
2. LazyRow 自身通过 `onNestedPrefetch` 回调递归预取自己的子 item

`LazyLayoutPrefetchState` 的构造参数 `onNestedPrefetch` 用于这种嵌套场景。当外层预取触发到内层 LazyRow 的 Composition 时，LazyRow 可以利用这个时机预先组合自己的第一个 item。[已验证: AndroidX androidx-main, LazyLayoutPrefetchState.kt]

**嵌套 LazyList 的性能陷阱**：外层 LazyColumn 每次滚动时，滚出屏幕的 LazyRow 整个子树被 dispose，滚回来时重新创建。如果 LazyRow 有很多 item，重新组合的开销会集中在单帧内。解决方案：

- 给 LazyRow 设置固定的 `userScrollEnabled = false` 并改用 `Row` + `Modifier.horizontalScroll`，如果数据量不大（< 20 项）
- 使用 `rememberLazyListState()` 在外层 item key 不变时复用 LazyRow 的状态
- 将 LazyRow 的数据缓存到 `remember` 中，避免在外层重组时重新计算

### nestedScroll 与滑动连贯性

Compose 的 `nestedScroll` 连接通过 `NestedScrollConnection` 和 `NestedScrollDispatcher` 实现。LazyList 内部已经集成了 `nestedScroll` 机制，当嵌套使用时（如 LazyColumn 内嵌水平 LazyRow），fling 手势的剩余速度会从内层传递到外层。

与 RecyclerView 的 `nestedScrolling` 机制相比，Compose 的实现在 API 层面更统一（都是 `Modifier.nestedScroll`），但在边界情况下行为不同：

- RecyclerView 的 `NestedScrollingChild3` 有明确的"消费了多长距离"的回调
- Compose 的 `NestedScrollConnection` 使用 `consume` / `available` 语义，dispatch 和 consume 分两步
- 如果自定义 `NestedScrollConnection` 拦截了消费但没有正确报告 consumed 值，外层 LazyList 会认为滚动还没被消费，出现"双重滚动"

## Perfetto 诊断 LazyList 卡顿的 SQL 模板

以下 SQL 可直接用于 Perfetto trace_processor。抓取 trace 时需要启用 `compose-recomposition` 数据源：

```
atrace --app=com.example.yourapp compose --compose-recomposition
```

### 查询 LazyList 重组次数最多的 Composable

```sql
SELECT
    name,
    COUNT(*) as recomposition_count,
    SUM(CASE WHEN skipped THEN 1 ELSE 0 END) as skipped_count,
    SUM(CASE WHEN NOT skipped THEN 1 ELSE 0 END) as actual_recomp
FROM slice
WHERE name LIKE '%recompose%'
    AND name NOT LIKE '%skipped%'
GROUP BY name
ORDER BY actual_recomp DESC
LIMIT 20;
```

`skipped_count` 高说明 Strong Skipping 生效，是正常行为。`actual_recomp` 高的 Composable 需要检查参数稳定性。

### 关联帧 timeline 与 LazyList 滑动帧

```sql
SELECT
    jank.id,
    jank.ts,
    jank.dur / 1e6 as dur_ms,
    jank.type
FROM actual_frame_timeline_slice jank
WHERE jank.type = 'Janky'
    AND jank.ts BETWEEN ({start_ts}) AND ({end_ts})
ORDER BY jank.dur DESC;
```

把掉帧帧与同一时间段的 Compose 重组 slice 做 `SPAN_JOIN`，可以定位是哪个 Composable 的重组导致了帧超时。

### GC 暂停与 LazyList 滑动的时序关联

```sql
SELECT
    gc.ts,
    gc.dur / 1e6 as gc_ms,
    reason
FROM slice gc
WHERE gc.name GLOB '*GC*'
    AND gc.ts BETWEEN ({start_ts}) AND ({end_ts})
ORDER BY gc.dur DESC;
```

GC 暂停 > 5ms 且与掉帧时间重叠时，排查 item 内部是否有大量临时对象分配。

### 内存分配热点

```sql
SELECT
    heap.allocations,
    heap.size,
    heap.type_name
FROM android_java_heap_stats heap
WHERE heap.ts BETWEEN ({start_ts}) AND ({end_ts})
ORDER BY heap.size DESC;
```

LazyList 滑动时如果 `java_heap_stats` 显示持续增长，检查 item 的 lambda 和 data class 是否在每次重组时创建新实例。

## 大列表优化策略：分页、占位与虚拟化边界

### Paging 3 + LazyList 集成

Paging 3 通过 `LazyPagingItems` 与 LazyList 集成。核心性能要点：

**刷新范围控制**：`LazyPagingItems` 的 `refresh()` 会触发整个列表的 invalidate。如果列表有 1000+ item 且其中 900+ 已经在屏幕外（不在可见范围），Compose Runtime 仍然会为所有已组合的 item 发送失效通知。`insertSeparators()` / `filter()` 等中间操作会增加这个开销。解决方案是在 Paging `RemoteMediator` 层做增量刷新，避免全量 invalidate。

**加载状态占位符的渲染开销**：Paging 3 的 `LoadState.Error` / `LoadState.Loading` 占位符在列表末端显示。如果占位符的 Composable 结构复杂（带动画、带骨架屏 shimmer），它在组合和布局阶段的成本可能比普通 item 还高。保持加载状态占位符的结构简单。

**预加载窗口**：Paging 3 的 `PagingConfig(prefetchDistance)` 控制"距离列表末端多远时触发加载下一页"。这个值需要与 LazyList 的 `LazyLayoutCacheWindow` 配合——如果 `prefetchDistance` 远大于 `cacheWindow.ahead`，Paging 数据已经在后台加载完成，但 LazyList 还没有预取到需要显示新数据的 item，造成"数据等 UI"的空窗。反过来，如果 `prefetchDistance` 远小于 `cacheWindow.ahead`，LazyList 预取到的 item 可能还是加载中状态。

### 超长列表的内存边界

LazyList 的虚拟化（只组合可见 item）限制了同时存在的 Composable 数量，但以下场景会打破这个限制：

- `beyondBoundsItemCount` 设得过大（默认 1-2 个，某些场景下开发者改到 10+），导致屏幕外有大量 item 保持组合状态
- `stickyHeader` 的 header 不会被 dispose，如果列表有多个不同 key 的 stickyHeader，它们会一直保留在 Composition 中
- `remember` 在 item 内部缓存大对象（Bitmap、大字符串），滚出屏幕后缓存不会释放

10 万+项的列表只要做好虚拟化（合理的 `cacheWindow` + 适当的 `beyondBoundsItemCount`），LazyList 本身的内存占用是可控的。瓶颈通常在数据层（Paging 的内存缓存）和图片层（图片加载库的内存缓存）。

## Android 17 LazyList 行为变化与适配

Android 17（API 37）平台本身不包含 Compose 工具链。LazyList 的行为变化来自 Compose Foundation 版本升级，不由 `targetSdk` 决定。以下列出与 Android 17 时间线对齐的 Compose 变更。[已验证: Compose BOM 2025.12.00 release notes]

**Compose Foundation 1.10 变更**（对应 BOM 2025.12.00）：

- **Pausable Composition**：在预取路径中可将 Composition 工作暂停到下一帧。1.10.0-alpha05 曾默认启用，1.10.6 因稳定性问题默认禁用。接入前检查目标 Foundation 版本的 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 默认值。
- **LazyLayoutCacheWindow**：API 签名在 1.9-1.10 间有调整（`ahead`/`behind` 参数从 px 改为 Dp），跨版本升级时需要检查构造参数。
- **Item Animator 改进**：`LazyLayoutItemAnimator` 在 1.10 中优化了 move 动画的插值算法，对 `key` 稳定的列表有更流畅的移动动画。

**targetSdk 36 → 37 的回归测试清单**：

1. 滑动帧率：用 Macrobenchmark 测量 LazyColumn 滑动 P90 帧时间，对比 targetSdk 36 和 37 的结果。Android 17 的后台执行限制变更（Excessive CPU Kill，§25.12）可能影响 Paging 的后台加载行为。
2. 内存占用：`Debug.getMemoryInfo()` 检查滑动 1000 项后的 Java Heap 增长。Android 17 的 `App Memory Limits`（§23.9）可能影响大列表的内存预算。
3. 嵌套滚动：如果列表使用了自定义 `NestedScrollConnection`，验证 fling 行为是否与 targetSdk 36 一致。Android 17 的 InputDispatcher 变更（§3.8）不直接影响 Compose 的 nestedScroll，但如果 App 同时使用了 View 体系的嵌套滚动，需要测试混合场景。
4. 预取行为：如果项目升级了 Compose Foundation 版本，检查 Pausable Composition 的 flag 状态是否与预期一致。

## LazyVerticalGrid / LazyHorizontalGrid 的特殊考量

LazyGrid 与 LazyList 共享 `LazyLayout` 的核心测量和预取机制，但有以下差异：

**span size 对 item pool 的影响**：Grid 的 `GridItemSpan` 允许一个 item 占多列。当 span 发生变化时（如列表从 2 列变 3 列），item pool 中的缓存 item 尺寸不匹配，需要重新 measure。Grid 的 pool 按 `(contentType, spanSize)` 组合分组，比 LazyList 的单一 contentType 分组更细。

**交错布局（Staggered）**：Compose Foundation 截至目前（BOM 2025.12.00）没有内置的 StaggeredGrid 实现。第三方库（如 `com.nlab.reminder:staggered-grid-compose`）通过自定义 `LazyLayout` 实现，需要自行验证 item pool 和预取行为。

**Grid 的 crossAxis 测量成本**：Grid 的每一行需要测量所有 crossAxis 上的 item 才能确定行高。如果 Grid 列数多（4+ 列）且 item 高度不一致，measure 阶段的遍历成本比同 item 数量的 LazyList 更高。

## 与 RecyclerView 性能对比选型

从四个维度对比（数据基于公开基准测试和社区反馈，非本文独立测试）：

| 维度 | Compose LazyList | RecyclerView |
|------|-----------------|--------------|
| **滑动帧率** | Compose 1.10+ 下接近 RecyclerView；复杂 item 差距更小 | 成熟优化，稳定帧率 |
| **内存占用** | item 组合对象比 ViewHolder 更重（Composable 子树 vs 单个 View） | ViewHolder 实例更轻量 |
| **首屏加载** | 首次组合比 inflate 慢（Composition 阶段额外开销）；Pausable Composition 部分缓解 | inflate 链路成熟，预加载可控 |
| **动态更新** | Strong Skipping + key 复用，性能接近 RecyclerView DiffUtil | DiffUtil + ItemAnimator 精确控制 |

**选型建议**：

- 新项目 / 新页面：用 Compose LazyList。Compose 1.10+ 的性能已经足够，长期维护成本更低。
- 已有 RecyclerView 的页面：不需要迁移。RecyclerView 在 Android 17 上仍然是被积极维护的 API。
- 混合场景：RecyclerView 嵌套 Compose item 或反过来，都有 interop 层的开销（`ComposeView` / `AbstractComposeView`）。如果列表性能是核心指标，保持单一实现（纯 Compose 或纯 View）。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 24.md]

[适用版本: Compose BOM 2025.12.00 / Kotlin 2.2 / Android 12 (API 31) - Android 17 (API 37)]
