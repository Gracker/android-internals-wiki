---
title: "RecyclerView 最佳实践"
chapter: "22.2"
section: "22.2"
status: finalized
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
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
task6_result: "pass-light-edit"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-30"
task6_reviewed_date: "2026-06-30"
last_task6_at: "2026-06-30T03:11:11+08:00"
last_task6_audit: "2026-06-07"
last_task6_review_log: "logs/review/2026-06-30-03-review.md"
task6_reviewed_at: "2026-06-30T02:13:00+08:00"
task6_reviewed_by: openclaw-task6
task6_review_notes: "2026-06-30 Task6 revisit复审：Task9 auto-fix已收敛源码锚点到 androidx.recyclerview:1.4.0 sources.jar；写作质检通过（禁用词0/高频词0/物理动词0/结构元叙述0/锚点全覆盖）；无L1/L2问题，无需小修；task9_result为auto-fixed，待Task9最终确认后可晋升finalized。"
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-30"
last_task9_at: "2026-06-30T04:35:04+08:00"
last_task9_audit: "2026-06-30"
last_task2b_lite_at: "2026-06-30"
last_task9_review_log: "logs/deep-review/2026-06-30-04-deep-review.md"
task9_review_notes: "2026-06-30 Task9 闲时抽检：P1 版本/源码锚点问题；AndroidX sources 原使用移动分支，需固定到可接受基线或标注未进入 Android 17。 | 2026-06-30 Task9 auto-fix：源码锚点从移动分支收敛到 androidx.recyclerview:recyclerview:1.4.0 sources.jar；1.4.0 source jar 已验证包含 RecyclerView/DiffUtil/AsyncListDiffer/ListAdapter/LinearLayoutManager/GapWorker/SimpleItemAnimator 等本文引用标识符；回到 Task6 复审。 | 2026-06-30 Task9 final review：AndroidX RecyclerView 1.4.0 source jar 与官方文档复核通过；本轮无 P0/P1/P2；Task6 已通过且 queue.json 中 22.2 无 pending，自动晋升 finalized。"
last_task9_autofix_at: "2026-06-30"
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-16
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/16-deliqueue-recyclerview-prefetch.md"
---

# RecyclerView 最佳实践

RecyclerView 优化不该从“调几个参数”开始，要从滑动路径里的成本来源开始：创建 ViewHolder、绑定数据、计算差异、预取下一屏、处理嵌套滑动。7.8 节已经展开 RecyclerView 内部布局、缓存和 GapWorker 机制；这里把机制转成应用侧写法、验收方法和取舍边界。

平台部分以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点，内核侧统一到 `android17-6.18-2026-06_r6`。RecyclerView 是独立发布的 AndroidX 库，代码基线固定为 `androidx.recyclerview:recyclerview:1.4.0` source jar，不能用 platform tag 替代它的版本。普通列表主体仍沿标准 HWUI App Window 出图：主线程完成输入、滚动、绑定与 Traversal，RenderThread 生成窗口 buffer，BLAST、SurfaceFlinger 和 HWC 再完成采纳、合成与 present。

## ViewHolder 复用与 ItemType 设计

ViewHolder 设计的目标是让滑动过程尽量走缓存命中，减少反复 `inflate` 和完整绑定。AndroidX RecyclerView 源码里，`RecycledViewPool` 支持在多个 RecyclerView 之间共享 ViewHolder，默认按 `viewType` 分桶；每个类型的池容量可通过 `setMaxRecycledViews()` 调整。RecyclerView 自身还有 `mCachedViews`，默认缓存大小是 2。详见 7.8 节的四级缓存说明。


`viewType` 的划分要按“布局结构是否不同”来做，避免按业务枚举一项一项拆。两个 item 如果 XML 结构一致，只是文案、图片、按钮状态不同，应该共用同一个 `viewType`。过多 `viewType` 会把池子切碎：每个类型都有自己的容量限制，某一类刚回收的 ViewHolder 无法服务另一类 item，滑动时就会重新创建。

实践中可以按这张表做判断：

| 设计点 | 推荐写法 | 风险写法 | Trace 表现 |
| --- | --- | --- | --- |
| `viewType` | 按布局结构分组 | 按业务状态、颜色、角标拆类型 | `RV onCreateViewHolder type=...` 在滑动中频繁出现 |
| `onCreateViewHolder()` | 只做 inflate、子 View 查找、一次性对象创建 | 发起请求、解码图片、读取磁盘 | create slice 在慢帧中持续占据较大比例 |
| `onBindViewHolder()` | 只绑定当前数据，重活交给异步组件 | 每次 bind 都重建复杂对象、重复设置监听 | `RV onBindViewHolder type=...` 在慢帧里变长 |
| Pool | 嵌套同构列表共享 `RecycledViewPool` | 每个子列表独立持有池 | 外层滑动时内层列表反复 create |


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

这段代码把多个子列表的回收池合并到一个对象里。共享前要保证相同 `viewType` 在所有 Adapter 中创建兼容的 ViewHolder；不同 Adapter 恰好复用了同一个整数，却对应不同布局时，池命中会造成类型转换或错误绑定。`TYPE_CARD` 的容量可按“屏幕上可能同时出现的子列表数 × 每个子列表可见卡片数”估算，再用 Perfetto 验证滑动中 `RV onCreateViewHolder` 是否下降。`setMaxRecycledViews()` 只修改上限，不会预先创建 holder；容量过大会增加内存占用。


`setHasStableIds(true)` 只适合 item 有稳定业务 ID 的列表。它能帮助 RecyclerView 在更新和动画期间识别同一个 item，但不能代替 DiffUtil，也不能修复错误的 `viewType` 设计。开启后必须保证 `getItemId(position)` 在同一条业务数据生命周期内不变，否则会出现复用错位、动画异常和状态串扰。

## DiffUtil 与增量更新

整表刷新是列表卡顿的高发来源。`notifyDataSetChanged()` 会让 RecyclerView 丢失细粒度变更信息，后续布局、动画和绑定都只能按大范围变更处理。`DiffUtil` 的价值是计算新旧列表差异，再把插入、删除、移动、内容变化分发给 Adapter。AndroidX 源码说明它使用 Eugene W. Myers 差分算法；`calculateDiff(callback, detectMoves)` 可以控制是否检测移动。


应用侧优先使用 `ListAdapter` 或 `AsyncListDiffer`。`ListAdapter#submitList()` 内部委托 `AsyncListDiffer`，后者在后台线程计算 diff，完成后再回到主线程分发更新。官方文档也把 `submitList()` 作为 Room / LiveData 场景的标准接入方式。


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

payload 只是一条优化路径，不能承载正确性。目标 ViewHolder 未 attach 时，payload 可能被丢弃；无 payload 的完整 bind 必须能从当前 item 恢复全部 UI 状态，包括清理旧图片、选中态、监听器和无障碍描述。

大列表还有两个边界：

- 数据源已经按时间排序且不支持拖拽移动时，可以关闭 move 检测，减少二次扫描开销。
- `equals()` 不要带入无关字段。埋点时间戳、临时曝光状态、调试字段如果参与内容比较，会让 DiffUtil 误判内容变化。
- 提交给 `ListAdapter` / `AsyncListDiffer` 的列表及其参与比较的字段在 diff 期间应视为不可变。`AsyncListDiffer` 对相同 List 实例会直接返回；原地修改旧列表再重复 `submitList()`，既破坏新旧快照，也可能不触发任何更新。应创建新的列表和不可变 item。

## 预取机制与配置

RecyclerView 的预取由 GapWorker 驱动。AndroidX 1.4.0 源码中，滚动路径会调用 `mGapWorker.postFromTraversal()`，记录滚动方向和距离，再通过 `recyclerView.post(this)` 把 GapWorker 投到主线程消息队列。它不是独立后台线程；预取 create / bind 也会消耗主线程时间。

`GapWorker.run()` 根据最近一次 drawing time 加刷新周期估算 deadline，并按滚动向量、距离和是否为下帧所需排序任务。普通任务在创建和绑定前分别经过 `willCreateInTime()`、`willBindInTime()`，判断依据是共享 Pool 中按 `viewType` 记录的 create / bind 运行均值。标记为 `neededNextFrame` 的任务会传入 `FOREVER_NS` 强制执行，不走这两个 deadline 拒绝分支；因此不能假设所有预取都会因预算不足自动停止。


`LinearLayoutManager#setInitialPrefetchItemCount()` 只影响嵌套 RecyclerView 首次出现时的 initial prefetch 数量。官方文档对它的定义是：当这个 LayoutManager 的 RecyclerView 嵌套在另一个 RecyclerView 中时，设置要预取的内部 item 数量。它不能当作“越大越流畅”的开关；请求过多会占用主线程和缓存，非强制任务也可能因 deadline 不足而提前放弃。


配置建议按这几步做：

1. 横向子列表首屏能露出 3 个半卡片，就把 initial prefetch 设为 4 或 5；不要直接设成整组数据长度。
2. 子列表 item 结构相同，先共享 `RecycledViewPool`，再调 `setInitialPrefetchItemCount()`；没有共享池时，预取仍会被 create 成本拖慢。
3. bind 中图片加载要交给图片库缓存和异步解码，Adapter 只提交 URL 和占位状态；不要在 bind 里同步解码 Bitmap。
4. 用 Perfetto 看 `RV Prefetch`、`RV Nested Prefetch`、带 `forced - needed next frame` 的预取切片，以及 `RV onCreateViewHolder type=...`、`RV onBindViewHolder type=...` 的相对位置。预取 slice 出现但下一帧仍然 create，说明目标 position、预算、缓存或 itemType 还要继续核对。

GapWorker 预取 holder、create 和 bind，不会替下一帧完成 item 的 Measure / Layout。若 trace 中 prefetch 和 bind 都正常，下一帧 `RV OnLayout` 或 framework `measure` / `layout` 仍然很长，问题应转向 item 尺寸、布局结构和图片结果触发的 `requestLayout()`。

共享 Pool 也共享按 `viewType` 统计的 create / bind 运行均值。多个 Adapter 共享同一 Pool 时，除了 ViewHolder 结构要兼容，构造和绑定成本也不宜差异悬殊，否则一个 Adapter 的历史均值会影响另一个 Adapter 的 deadline 判断。

Android 17 对 `targetSdkVersion >= 37` 的应用启用新的 MessageQueue 实现。它可能减少 `recyclerView.post(this)` 入队相关的锁竞争，却没有改变 GapWorker 的 position 收集、排序、create / bind 预算或主线程执行属性。trace 没有 MessageQueue contention 时，不应把列表优化收益归因到这项平台变化。

`setItemViewCacheSize()` 只适合少量、可复用、短距离往返滑动的列表。它会让刚滑出屏幕的 ViewHolder 保持绑定状态，减少 bind，但也会持有更多 View 和图片引用。Feed 流、瀑布流、长列表不要先调大这个缓存，先修 itemType、payload 和共享 Pool。

## 嵌套滚动与多 RecyclerView 场景优化

多 RecyclerView 场景常见于首页 Feed、频道页、卡片流和 ViewPager2。性能问题通常来自多层列表在同一帧里同时触发布局、绑定和预取，不能只归因于“嵌套”。


处理顺序可以固定下来：

- **避免无界测量**：不要把 RecyclerView 放进纵向 `NestedScrollView` 后再让它展开全部 item。这样会破坏回收，列表会接近普通 `LinearLayout`。
- **同向嵌套要收敛**：纵向 RecyclerView 里再放纵向 RecyclerView，触摸分发、NestedScrolling 和测量都会变复杂。能用单个 RecyclerView + 多 `viewType` / `ConcatAdapter` 表达的页面，优先合并。
- **异向嵌套先共享 Pool**：纵向 Feed 里的横向卡片列表，给内层列表共享 `RecycledViewPool`，再设置 initial prefetch。
- **容器尺寸不受数据影响时声明 fixed size**：`setHasFixedSize(true)` 表示 Adapter 内容变化不会改变 RecyclerView 自身的测量宽高。它不要求每个 item 等高，也不会阻止 item 内部重新 Measure / Layout。RecyclerView 为固定高度或 `match_parent` 时常可使用；若 RecyclerView 自身为 `wrap_content`，增删 item 会改变容器尺寸，就不应开启。
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

这段配置假设内层 RecyclerView 的自身尺寸由外层卡片确定，Adapter 内容变化不会改变它的测量宽高。内层 item 可以有不同宽度或高度，`setHasFixedSize(true)` 也不会掩盖 child 的尺寸变化；它只改变 RecyclerView 处理 Adapter 更新时能否依赖容器尺寸不变。如果 change animation 是产品体验的一部分，也不能直接关闭，要按慢帧和视觉结果取舍。

## 变更动画与局部刷新要一起看

局部刷新做完后，还要看 ItemAnimator。`getChangePayload()` 能减少绑定范围，但默认 change animation 仍可能让旧 ViewHolder 和新 ViewHolder 同时参与动画，增加布局和绘制压力。点赞、关注、计数器这类高频状态变更，通常只需要文本或图标状态切换，不需要整行 change animation。

在同一台设备上录两段 Perfetto，一段保留 change animation，一段关闭 `supportsChangeAnimations`。如果关闭后 `RV OnLayout`、`RV onBindViewHolder` 和慢帧数量下降，并且交互视觉没有损失，就把关闭范围限定在对应 Adapter 或页面，不要全局一刀切。


## RecyclerView vs LazyColumn 性能对比

## Android 17 DeliQueue：只改变消息入队，不替代列表优化

Android 17 在 `targetSdkVersion >= 37` 时启用新的 DeliQueue 路径：生产者通过无锁栈提交消息，Looper 再把同步、异步消息整理进各自的堆。它缓解的是旧 `MessageQueue` monitor 上的生产者/消费者竞争，不会缩短 `onCreateViewHolder()`、`onBindViewHolder()`、item measure/layout、图片解码、RenderThread 或 SurfaceFlinger 的工作。

RecyclerView 1.4.0 的 `GapWorker.postFromTraversal()` 仍通过 `RecyclerView.post()` 把一次预取任务送入主线程队列。DeliQueue 可以减少这次 post 与后台生产者争锁的概率，但从 post 到 `GapWorker.run()` 之间仍可能有前序消息、长 callback 和 CPU 调度延迟。预取自身也只覆盖 holder 获取、create 和 bind；下一帧的 measure/layout 仍需单独分析。

排查时按证据分流：

- 主线程出现指向 legacy `MessageQueue` 的 `monitor contention`，才把队列锁列为候选；切换 `USE_NEW_MESSAGEQUEUE` 后必须重启进程再做同 APK A/B。
- `RV Prefetch` 很晚、却没有队列锁等待时，检查前序 Looper 消息、主线程 Runnable 时间和调度轨道。
- `RV onCreateViewHolder` / `RV onBindViewHolder` 很长时，回到 pool、payload、图片和数据转换；`RV OnLayout` 很长时，回到约束和布局层级。
- App SurfaceFrame 按时而 DisplayFrame 迟到时，继续检查目标 layer、fence、SurfaceFlinger 与 HWC，不把它归到 DeliQueue。

target 37 适配还要清点反射 `MessageQueue.mMessages` 的测试、监控和调试工具；DeliQueue 路径保留该字段只为二进制兼容，其值不再代表真实队列。官方要求的 Espresso/Robolectric 版本与 Looper mode 应纳入回归。业务侧仍要合并同一 item 的高频结果、限制一次主线程 drain 的批量，并让 lifecycle 能取消尚未应用的更新；无锁队列不能修复消息风暴。

`LazyColumn` 和 RecyclerView 都围绕可见窗口按需准备 item，也都可能为预取或 beyond-bounds 操作准备窗口之外的内容。列表中有多种 item 时，`contentType` 可以帮助 Compose 在兼容类型之间复用组合。这个方向和 RecyclerView 的 `viewType` / Pool 很像：类型划分越接近可兼容的 UI 结构，复用效果越稳定。


两者选型不要用固定结论：

| 页面条件 | 更适合 RecyclerView | 更适合 LazyColumn |
| --- | --- | --- |
| 既有 View 页面 | 已有 Adapter、图片库、曝光、分页和共享 Pool | 为单个 Compose 模块引入 View/Compose 混排成本高 |
| item 类型很多 | Pool、`viewType`、payload 已经调好 | `key`、`contentType` 清晰，状态提升做得好 |
| 高频局部刷新 | payload 和 ItemAnimator 可细调 | 状态粒度拆得足够细，避免整行重组 |
| 团队能力 | 熟悉 Perfetto + RecyclerView trace | 熟悉 Compose recomposition、layout inspector、Macrobenchmark |

迁移判断要看同机数据。至少对比四组指标：慢帧率、P95 帧耗时、内存峰值、首屏可交互时间。Compose 写法中不要在 `LazyColumn` 的 `items` 里排序、过滤或创建大对象；官方性能文档也把这类操作列为列表重组中的常见开销。

## RecyclerView 1.4 与 Android 刷新率协作

RecyclerView 1.4.0 在 API 35 及以上的 fling 和 smooth scroll 路径中，通过 `View.setFrameContentVelocity()` 上报当前滚动速度。这是给平台刷新率策略的输入信号，RecyclerView 不查询面板能力，也不决定切换到哪个 Hz。Android 17 上若要判断效果，应同时核对 RecyclerView 版本、速度上报、Display 支持范围、系统刷新率决策和帧数据，不能把面板切换结果归因给单个 Adapter 参数。


## 验收清单

RecyclerView 优化完成后，至少跑一次本地 trace 和一次线上指标回看：

- Perfetto 中 `RV onCreateViewHolder type=...` 若在稳定滑动阶段持续出现，回看 Pool、`viewType`、新类型进入窗口和 initial prefetch。
- `RV onBindViewHolder type=...` 应结合完整帧 deadline 与同一帧其他主线程工作判断；如果 bind 分位数持续变长，回看 payload、图片加载、文本处理和同步 I/O。
- `RV Prefetch` / `RV Nested Prefetch` 及 forced 变体出现后，核对目标 position 的 create / bind 是否前移，并检查后续关键帧成本；不要只按切片是否存在判断命中。
- 慢帧集中在 `RV OnLayout` 时，回到 22.1 节查 item 布局层级、`requestLayout()` 来源和 change animation。
- UI 线程按时完成后仍有 jank，继续检查 RenderThread、`queueBuffer`、`BufferTX - <layerName>`、latch 与 FrameTimeline present；列表切片不能解释完整显示链。
- 线上按页面、机型、刷新率、列表类型拆指标；只看全局平均值会把低端机和复杂页面的问题稀释掉。

这套检查的目标是把 RecyclerView 问题拆成四类：复用没命中、增量更新没生效、预取没赶上、嵌套布局太重。分类清楚后，优化动作才不会互相抵消。

## 源码与文档

- [RecyclerView 1.4.0 source jar](https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar)：`RecyclerView`、`GapWorker`、`DiffUtil`、`AsyncListDiffer`、`ListAdapter` 与 `LinearLayoutManager` 的固定源码基线。
- [RecyclerView 1.4.0 release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview#recyclerview-1.4.0)：版本变化与 Adaptive Refresh Rate 支持边界。
- [`RecyclerView.setHasFixedSize()`](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView#setHasFixedSize(boolean))：RecyclerView 自身尺寸不受 Adapter 内容影响的契约。
- [`DiffUtil`](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)：差异计算、move 检测与回调语义。
- [`AsyncListDiffer`](https://developer.android.com/reference/androidx/recyclerview/widget/AsyncListDiffer)：后台 diff、列表提交与只读当前列表。
- [`LinearLayoutManager.setInitialPrefetchItemCount()`](https://developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager#setInitialPrefetchItemCount(int))：嵌套列表 initial prefetch 的范围。
- [Compose lists](https://developer.android.com/develop/ui/compose/lists)：Lazy 列表、key 与 `contentType`。
- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)：`setFrameContentVelocity()` 的平台入口。
- [Android 17 MessageQueue behavior change](https://developer.android.com/about/versions/17/changes/messagequeue)：target SDK 37 的 MessageQueue 边界。
