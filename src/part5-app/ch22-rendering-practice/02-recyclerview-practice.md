---
title: "RecyclerView 最佳实践"
chapter: "22.2"
section: "22.2"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "AndroidX RecyclerView 1.4.0 sources.jar + Android Developers docs + AIW 7.8/22.1/2.4；AndroidX RecyclerView 为独立 artifact，不属于 android-17.0.0_r1 platform tag"
confidence: medium
androidx_source_note: "AndroidX RecyclerView 源码以 androidx.recyclerview:recyclerview:1.4.0 sources.jar 为不可变基线；RecyclerView 是 AndroidX artifact，不属于 android-17.0.0_r1 platform tag。"
drafted_date: "2026-05-13"
polish_count: 1
sources:
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (RecyclerView.java)"
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (DiffUtil.java)"
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (AsyncListDiffer.java)"
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (ListAdapter.java)"
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (LinearLayoutManager.java)"
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (GapWorker.java)"
  - type: androidx
    path: "androidx.recyclerview:recyclerview:1.4.0 sources.jar (SimpleItemAnimator.java)"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/recyclerview#recyclerview-1.4.0"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/ListAdapter"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager#setInitialPrefetchItemCount(int)"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/lists"
  - type: aiw
    path: "src/part2-performance/ch07-smoothness/08-recyclerview-performance.md"
  - type: aiw
    path: "src/part5-app/ch22-rendering-practice/01-layout-optimization.md"
  - type: aiw
    path: "src/part1-fundamentals/ch02-rendering/04-choreographer.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 24.md"
tags: [recyclerview, viewholder, diffutil, prefetch, nested-scroll]
related_chapters: ["22.1", "7.8", "2.4"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-30"
task6_reviewed_date: "2026-06-30"
last_task6_at: "2026-06-30T02:13:00+08:00"
last_task6_audit: "2026-06-07"
last_task6_review_log: logs/review/2026-06-30-02-review.md
task6_reviewed_at: "2026-06-30T02:13:00+08:00"
task6_reviewed_by: openclaw-task6
task6_review_notes: "2026-06-30 Task6 revisit：Task2B Lite 已补充移动分支源码锚点标注；写作质检通过（禁用词0/高频词0/锚点全覆盖），清理 4 行 [结构参考] 处理残留；task9_result 仍为 needs-rework，等待 Task9 复核 Lite 修复。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-30"
last_task9_at: "2026-06-30T02:25:45+08:00"
last_task9_audit: "2026-06-30"
last_task2b_lite_at: "2026-06-30"
last_task9_review_log: "logs/deep-review/2026-06-30-02-deep-review.md"
task9_review_notes: "2026-06-30 Task9 闲时抽检：P1 版本/源码锚点问题；AndroidX sources 原使用移动分支，需固定到可接受基线或标注未进入 Android 17。 | 2026-06-30 Task9 auto-fix：源码锚点从移动分支收敛到 androidx.recyclerview:recyclerview:1.4.0 sources.jar；1.4.0 source jar 已验证包含 RecyclerView/DiffUtil/AsyncListDiffer/ListAdapter/LinearLayoutManager/GapWorker/SimpleItemAnimator 等本文引用标识符；回到 Task6 复审。"
last_task9_autofix_at: "2026-06-30"
task9_p0_issues: 0
task9_p1_issues: 1
task9_p2_issues: 0
---

# RecyclerView 最佳实践

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ViewHolder 复用与 ItemType 设计
- 🔹 DiffUtil 与增量更新
- 🔹 预取（Prefetch）机制与配置
- 🔹 嵌套滚动与多 RecyclerView 场景优化

### 扩展（可选深入）

- 🔸 RecyclerView vs LazyColumn 性能对比

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

RecyclerView 优化不该从“调几个参数”开始，而要从滑动路径里的成本来源开始：创建 ViewHolder、绑定数据、计算差异、预取下一屏、处理嵌套滑动。7.8 节已经展开 RecyclerView 内部布局、缓存和 GapWorker 机制；这里把机制转成应用侧写法、验收方法和取舍边界。

> **⚠️ 源码锚点说明**：本节 AndroidX RecyclerView 源码以 `androidx.recyclerview:recyclerview:1.4.0` 的 `recyclerview-1.4.0-sources.jar` 为不可变基线。RecyclerView 是 AndroidX artifact，不属于 `android-17.0.0_r1` platform tag；本文不使用移动分支作为 Android 17 结论依据。


## ViewHolder 复用与 ItemType 设计

ViewHolder 设计的目标是让滑动过程尽量走缓存命中，减少反复 `inflate` 和完整绑定。AndroidX RecyclerView 源码里，`RecycledViewPool` 支持在多个 RecyclerView 之间共享 ViewHolder，默认按 `viewType` 分桶；每个类型的池容量可通过 `setMaxRecycledViews()` 调整。RecyclerView 自身还有 `mCachedViews`，默认缓存大小是 2。详见 7.8 节的四级缓存说明。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `RecyclerView.java`, `RecycledViewPool`, `mCachedViews`, `DEFAULT_CACHE_SIZE`]

`viewType` 的划分要按“布局结构是否不同”来做，避免按业务枚举一项一项拆。两个 item 如果 XML 结构一致，只是文案、图片、按钮状态不同，应该共用同一个 `viewType`。过多 `viewType` 会把池子切碎：每个类型都有自己的容量限制，某一类刚回收的 ViewHolder 无法服务另一类 item，滑动时就会重新创建。

实践中可以按这张表做判断：

| 设计点 | 推荐写法 | 风险写法 | Trace 表现 |
| --- | --- | --- | --- |
| `viewType` | 按布局结构分组 | 按业务状态、颜色、角标拆类型 | `RV onCreateViewHolder type=...` 在滑动中频繁出现 |
| `onCreateViewHolder()` | 只做 inflate、子 View 查找、一次性对象创建 | 发起请求、解码图片、读取磁盘 | create slice 超过单帧预算的一小半 |
| `onBindViewHolder()` | 只绑定当前数据，重活交给异步组件 | 每次 bind 都重建复杂对象、重复设置监听 | `RV onBindViewHolder type=...` 在慢帧里变长 |
| Pool | 嵌套同构列表共享 `RecycledViewPool` | 每个子列表独立持有池 | 外层滑动时内层列表反复 create |

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `RecyclerView.java`, Adapter trace sections]

嵌套横向列表的共享池可以写成下面这样。重点是让同构子列表共用同一批 ViewHolder，再按首屏数量调容量。

```kotlin
private val sharedPool = RecyclerView.RecycledViewPool().apply {
    setMaxRecycledViews(TYPE_CARD, 12)
    setMaxRecycledViews(TYPE_BANNER, 4)
}

fun bindHorizontalList(holder: SectionHolder, items: List<Card>) {
    val list = holder.recyclerView
    if (list.recycledViewPool !== sharedPool) {
        list.setRecycledViewPool(sharedPool)
        (list.layoutManager as? LinearLayoutManager)?.setRecycleChildrenOnDetach(true)
    }
    holder.adapter.submitList(items)
}
```

这段代码把多个子列表的回收池合并到一个对象里。`TYPE_CARD` 的容量按“屏幕上可能同时出现的子列表数 × 每个子列表可见卡片数”估算，再用 Perfetto 验证滑动中 `RV onCreateViewHolder` 是否下降。容量过大会增加内存占用，不能只按峰值堆上去。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `RecyclerView.RecycledViewPool#setMaxRecycledViews`, `LinearLayoutManager#setRecycleChildrenOnDetach`]

[自动发现] `setHasStableIds(true)` 只适合 item 有稳定业务 ID 的列表。它能帮助 RecyclerView 在更新和动画期间识别同一个 item，但不能代替 DiffUtil，也不能修复错误的 `viewType` 设计。开启后必须保证 `getItemId(position)` 在同一条业务数据生命周期内不变，否则会出现复用错位、动画异常和状态串扰。

## DiffUtil 与增量更新

整表刷新是列表卡顿的高发来源。`notifyDataSetChanged()` 会让 RecyclerView 丢失细粒度变更信息，后续布局、动画和绑定都只能按大范围变更处理。`DiffUtil` 的价值是计算新旧列表差异，再把插入、删除、移动、内容变化分发给 Adapter。AndroidX 源码说明它使用 Eugene W. Myers 差分算法；`calculateDiff(callback, detectMoves)` 可以控制是否检测移动。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `DiffUtil.java`, `calculateDiff()`, `detectMoves`, Myers algorithm]

应用侧优先使用 `ListAdapter` 或 `AsyncListDiffer`。`ListAdapter#submitList()` 内部委托 `AsyncListDiffer`，后者在后台线程计算 diff，完成后再回到主线程分发更新。官方文档也把 `submitList()` 作为 Room / LiveData 场景的标准接入方式。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `ListAdapter.java`, `AsyncListDiffer.java`; 官方文档 `ListAdapter`, `AsyncListDiffer`]

DiffUtil 写得好不好，取决于三个回调：

- `areItemsTheSame()`：判断是否是同一个业务对象，通常比较服务端 ID 或本地稳定 ID。
- `areContentsTheSame()`：判断内容是否完全一致，避免同一个对象无变化时重复绑定。
- `getChangePayload()`：描述哪些字段变化，让 Adapter 走局部绑定。

下面这段示例只展示 payload 绑定路径。读代码时看两个点：同一 item 只改标题时，不重新加载图片；没有 payload 时才走完整绑定。

```kotlin
data class TitleChanged(val title: String)
data class AvatarChanged(val url: String)

class CardDiff : DiffUtil.ItemCallback<Card>() {
    override fun areItemsTheSame(oldItem: Card, newItem: Card): Boolean {
        return oldItem.id == newItem.id
    }

    override fun areContentsTheSame(oldItem: Card, newItem: Card): Boolean {
        return oldItem == newItem
    }

    override fun getChangePayload(oldItem: Card, newItem: Card): Any? {
        val changes = mutableListOf<Any>()
        if (oldItem.title != newItem.title) changes += TitleChanged(newItem.title)
        if (oldItem.avatarUrl != newItem.avatarUrl) changes += AvatarChanged(newItem.avatarUrl)
        return changes.takeIf { it.isNotEmpty() }
    }
}

class CardAdapter : ListAdapter<Card, CardHolder>(CardDiff()) {
    override fun onBindViewHolder(holder: CardHolder, position: Int, payloads: MutableList<Any>) {
        if (payloads.isEmpty()) {
            holder.bind(getItem(position))
            return
        }
        val changes = payloads.flatMap { (it as? List<*>) ?: listOf(it) }
        changes.forEach { payload ->
            when (payload) {
                is TitleChanged -> holder.bindTitle(payload.title)
                is AvatarChanged -> holder.bindAvatar(payload.url)
            }
        }
    }
}
```

这段写法的收益来自减少完整 bind 的次数，diff 计算本身不会因此变少。列表中只有标题、点赞数、关注状态这类小字段变化时，payload 能明显缩短主线程绑定时间；如果 item 布局会因为字段变化触发布局重新测量，还要回到 22.1 节检查布局成本。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `DiffUtil.ItemCallback#getChangePayload`, `Adapter#onBindViewHolder(holder, position, payloads)`]

大列表还有两个边界：

- 数据源已经按时间排序且不支持拖拽移动时，可以关闭 move 检测，减少二次扫描开销。
- `equals()` 不要带入无关字段。埋点时间戳、临时曝光状态、调试字段如果参与内容比较，会让 DiffUtil 误判内容变化。

## 预取机制与配置

RecyclerView 的预取由 GapWorker 驱动。AndroidX 源码中，滚动路径会调用 `mGapWorker.postFromTraversal()`，记录滚动方向和距离，再把 GapWorker 作为 Runnable 投到主线程队列。执行时，GapWorker 根据下一帧 deadline 尝试预取目标 position；创建和绑定前会分别经过 `willCreateInTime()`、`willBindInTime()` 预算判断。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `RecyclerView.java#postFromTraversal`, `GapWorker.java`, `RecyclerView.RecycledViewPool#willCreateInTime/willBindInTime`]

`LinearLayoutManager#setInitialPrefetchItemCount()` 只影响嵌套 RecyclerView 首次出现时的 initial prefetch 数量。官方文档对它的定义是：当这个 LayoutManager 的 RecyclerView 嵌套在另一个 RecyclerView 中时，设置要预取的内部 item 数量。它不能当作“越大越流畅”的开关；item inflate 或 bind 很重时，GapWorker 会因为 deadline 不够而提前放弃。

[已验证: 官方文档 `LinearLayoutManager#setInitialPrefetchItemCount(int)`; AndroidX `LinearLayoutManager#collectInitialPrefetchPositions`]

配置建议按这几步做：

1. 横向子列表首屏能露出 3 个半卡片，就把 initial prefetch 设为 4 或 5；不要直接设成整组数据长度。
2. 子列表 item 结构相同，先共享 `RecycledViewPool`，再调 `setInitialPrefetchItemCount()`；没有共享池时，预取仍会被 create 成本拖慢。
3. bind 中图片加载要交给图片库缓存和异步解码，Adapter 只提交 URL 和占位状态；不要在 bind 里同步解码 Bitmap。
4. 用 Perfetto 看 `RV Prefetch`、`RV Nested Prefetch`、`RV onCreateViewHolder type=...`、`RV onBindViewHolder type=...` 的相对位置。预取 slice 出现但下一帧仍然 create，说明预算、缓存或 itemType 还有问题。

`setItemViewCacheSize()` 只适合少量、可复用、短距离往返滑动的列表。它会让刚滑出屏幕的 ViewHolder 保持绑定状态，减少 bind，但也会持有更多 View 和图片引用。Feed 流、瀑布流、长列表不要先调大这个缓存，先修 itemType、payload 和共享 Pool。

## 嵌套滚动与多 RecyclerView 场景优化

多 RecyclerView 场景常见于首页 Feed、频道页、卡片流和 ViewPager2。性能问题通常来自多层列表在同一帧里同时触发布局、绑定和预取，不能只归因于“嵌套”。

[已验证: AIW 7.8 嵌套滑动与共享 Pool；AIW 2.4 Choreographer 帧调度]

处理顺序可以固定下来：

- **避免无界测量**：不要把 RecyclerView 放进纵向 `NestedScrollView` 后再让它展开全部 item。这样会破坏回收，列表会接近普通 `LinearLayout`。
- **同向嵌套要收敛**：纵向 RecyclerView 里再放纵向 RecyclerView，触摸分发、NestedScrolling 和测量都会变复杂。能用单个 RecyclerView + 多 `viewType` / `ConcatAdapter` 表达的页面，优先合并。
- **异向嵌套先共享 Pool**：纵向 Feed 里的横向卡片列表，给内层列表共享 `RecycledViewPool`，再设置 initial prefetch。
- **固定尺寸就声明固定尺寸**：item 高度和 RecyclerView 尺寸稳定时使用 `setHasFixedSize(true)`，减少 Adapter 更新后触发的整体布局成本。尺寸会随内容变化的列表不要硬开。
- **动画按收益打开**：频繁局部刷新、点赞态变化、倒计时列表中，`DefaultItemAnimator` 的 change animation 可能带来额外布局和闪烁。可以只关闭 change animation，保留其他有收益的动画。

下面这段代码用于“外层纵向 Feed + 内层横向卡片”的基础配置。重点看三个动作：固定尺寸、共享池、按首屏卡片数设置 initial prefetch。

```kotlin
fun RecyclerView.configureHorizontalCards(
    sharedPool: RecyclerView.RecycledViewPool,
    visibleCardCount: Int,
) {
    setHasFixedSize(true)
    setRecycledViewPool(sharedPool)
    layoutManager = LinearLayoutManager(context, RecyclerView.HORIZONTAL, false).apply {
        initialPrefetchItemCount = visibleCardCount + 1
        recycleChildrenOnDetach = true
    }
    (itemAnimator as? SimpleItemAnimator)?.supportsChangeAnimations = false
}
```

这段配置适用于内层 item 尺寸稳定、卡片类型数量有限的列表。如果内层卡片高度由远端内容决定，`setHasFixedSize(true)` 可能掩盖尺寸变化；如果 change animation 是产品体验的一部分，也不能直接关闭，要按慢帧和视觉结果取舍。

## [自动发现] 变更动画与局部刷新要一起看

局部刷新做完后，还要看 ItemAnimator。`getChangePayload()` 能减少绑定范围，但默认 change animation 仍可能让旧 ViewHolder 和新 ViewHolder 同时参与动画，增加布局和绘制压力。点赞、关注、计数器这类高频状态变更，通常只需要文本或图标状态切换，不需要整行 change animation。

在同一台设备上录两段 Perfetto，一段保留 change animation，一段关闭 `supportsChangeAnimations`。如果关闭后 `RV OnLayout`、`RV onBindViewHolder` 和慢帧数量下降，并且交互视觉没有损失，就把关闭范围限定在对应 Adapter 或页面，不要全局一刀切。

[已验证: AndroidX RecyclerView 1.4.0 sources.jar `SimpleItemAnimator#supportsChangeAnimations`; AIW 7.8 Perfetto 排查顺序]

## RecyclerView vs LazyColumn 性能对比

`LazyColumn` 和 RecyclerView 都只处理可见窗口附近的 item。官方 Compose 文档明确说明，Lazy 组件只组合和布局 viewport 中可见的元素；列表中有多种 item 时，`contentType` 可以让 Compose 在相同类型之间复用组合。这个方向和 RecyclerView 的 `viewType` / Pool 很像：类型划分越接近布局结构，复用效果越稳定。

[已验证: 官方文档 `Compose lists`, `LazyColumn`, `contentType`]

两者选型不要用固定结论：

| 页面条件 | 更适合 RecyclerView | 更适合 LazyColumn |
| --- | --- | --- |
| 既有 View 页面 | 已有 Adapter、图片库、曝光、分页和共享 Pool | 为单个 Compose 模块引入 View/Compose 混排成本高 |
| item 类型很多 | Pool、`viewType`、payload 已经调好 | `key`、`contentType` 清晰，状态提升做得好 |
| 高频局部刷新 | payload 和 ItemAnimator 可细调 | 状态粒度拆得足够细，避免整行重组 |
| 团队能力 | 熟悉 Perfetto + RecyclerView trace | 熟悉 Compose recomposition、layout inspector、Macrobenchmark |

迁移判断要看同机数据。至少对比四组指标：慢帧率、P95 帧耗时、内存峰值、首屏可交互时间。Compose 写法中不要在 `LazyColumn` 的 `items` 里排序、过滤或创建大对象；官方性能文档也把这类操作列为列表重组中的常见开销。

[已验证: 官方文档 `Compose performance best practices`, LazyColumn sorting example]

## 验收清单

RecyclerView 优化完成后，至少跑一次本地 trace 和一次线上指标回看：

- Perfetto 中 `RV onCreateViewHolder type=...` 不应在稳定滑动阶段持续出现；如果出现，回看 Pool、`viewType` 和 initial prefetch。
- `RV onBindViewHolder type=...` 单次耗时要落在页面帧预算内；如果 bind 稳定变长，回看 payload、图片加载、文本测量和同步 I/O。
- `RV Prefetch` / `RV Nested Prefetch` 出现后，下一帧 create/bind 应该减少；如果没有减少，回看 deadline、item 重量和共享池。
- 慢帧集中在 `RV OnLayout` 时，回到 22.1 节查 item 布局层级、`requestLayout()` 来源和 change animation。
- 线上按页面、机型、刷新率、列表类型拆指标；只看全局平均值会把低端机和复杂页面的问题稀释掉。

这套检查的目标是把 RecyclerView 问题拆成四类：复用没命中、增量更新没生效、预取没赶上、嵌套布局太重。分类清楚后，优化动作才不会互相抵消。