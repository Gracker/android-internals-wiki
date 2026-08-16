---
title: "RecyclerView 最佳实践"
chapter: "22.2"
section: "22.2"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AndroidX current-version table (updated 2026-08-12); RecyclerView 1.4.0 sources.jar and API docs; Android 17 MessageQueue guidance (updated 2026-08-13); AIW 7.8/22.1/2.4"
confidence: medium-high
androidx_source_note: "截至 2026-08-14，AndroidX 版本总表仍将 androidx.recyclerview:recyclerview:1.4.0 列为稳定版。本文以其 sources.jar 为不可变源码基线；RecyclerView 是独立 AndroidX artifact，不属于 android-17.0.0_r1 platform tag。"
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
    path: "https://developer.android.com/jetpack/androidx/versions"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.Adapter"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/ListAdapter"
  - type: official
    path: "https://developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager#setInitialPrefetchItemCount(int)"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/lists"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/bestpractices"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/messagequeue"
  - type: official
    path: "https://developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue"
  - type: official
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java"
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
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/16-deliqueue-recyclerview-prefetch.md"
---

# RecyclerView 最佳实践

RecyclerView 优化不应从“调几个参数”开始，而要先定位滑动路径里的成本：创建 `ViewHolder`、绑定数据、计算列表差异、预取下一屏，以及处理嵌套滑动。`ViewHolder` 是持有一条 item 的根 View 和子 View 引用的复用单元；GapWorker 则是 RecyclerView 在主线程执行的预取任务。缓存查找顺序和 GapWorker 源码见 [7.8 RecyclerView 滑动性能深度优化](../../part2-performance/ch07-smoothness/08-recyclerview-performance.md)，本节侧重应用写法、验收方法和取舍边界。

平台行为以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。RecyclerView 是独立发布的 AndroidX 库；截至 2026 年 8 月 14 日，[AndroidX 版本总表](https://developer.android.com/jetpack/androidx/versions)仍将 1.4.0 列为稳定版，因此本文固定使用 `androidx.recyclerview:recyclerview:1.4.0` 的 `sources.jar`（源码包），不能用 Android 平台源码标签替代。RecyclerView 的 trace 主要呈现主线程侧的输入、滚动、绑定与 Traversal（View 树的测量、布局和绘制遍历）；之后还有 RenderThread、图形缓冲区、SurfaceFlinger 与 HWC（硬件合成器）的工作，完整链路见 [2.5 主线程与渲染线程](../../part1-fundamentals/ch02-rendering/05-main-render-thread.md)。

## ViewHolder 复用与 `viewType` 设计

ViewHolder 设计的目标是让滑动过程尽量命中缓存，减少反复 `inflate`（解析 XML 并创建 View 树）和完整绑定。`RecycledViewPool` 可以在多个 RecyclerView 之间共享 ViewHolder，并按 `viewType`（可复用的视图类型）分桶；1.4.0 中每种类型默认最多保留 5 个，应用可用 `setMaxRecycledViews()` 调整。RecyclerView 自身的 `mCachedViews` 会保留仍带绑定状态的 holder：请求大小默认是 2；启用 item prefetch（条目预取）时，实际最大值 `mViewCacheMax` 还会加上 LayoutManager 观察到的预取数量，因此不能把“2”理解为始终固定的总数。

`viewType` 应按“ViewHolder 是否能安全交叉复用”来划分。两个 item 的 View 结构和绑定规则相同，只是文案、图片或按钮状态不同，通常应共用同一个类型。若按颜色、角标等业务状态拆出过多类型，回收池会被切成许多小桶：一种类型刚回收的 ViewHolder 无法服务另一种类型，滑动时更容易重新创建。

Perfetto 中的 slice 是带起止时间的轨道条目，下表把代码决策与常见时间片对应起来：

| 设计点 | 推荐写法 | 风险写法 | Perfetto 表现 |
| --- | --- | --- | --- |
| `viewType` | 按兼容的 ViewHolder 结构和绑定规则分组 | 按业务状态、颜色、角标拆类型 | `RV onCreateViewHolder type=...` 在滑动中频繁出现 |
| `onCreateViewHolder()` | 只做 inflate、子 View 查找、一次性对象创建 | 发起请求、解码图片、读取磁盘 | create 时间片在慢帧中持续占据较大比例 |
| `onBindViewHolder()` | 只绑定当前数据，重活交给异步组件 | 每次 bind 都重建复杂对象、重复设置监听 | bind 时间片在慢帧里变长 |
| `RecycledViewPool` | 结构一致的嵌套列表共享回收池 | 每个子列表独立持有池 | 外层滑动时内层列表反复 create |

嵌套横向列表的共享池可以写成下面这样。重点是让 ViewHolder 结构与绑定规则一致的子列表共用同一批对象，再按首屏数量调容量。

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

这段代码把多个子列表的回收池合并到一个对象里。Pool 只认识整数 `viewType`，不知道 ViewHolder 来自哪个 Adapter；如果两个 Adapter 恰好使用同一个整数却创建不同布局，交叉复用会导致类型转换异常、错误绑定或残留状态。`TYPE_CARD` 的容量可按“屏幕上可能同时出现的子列表数 × 每个子列表可见卡片数”估算，再用 Perfetto 验证稳定滑动阶段的 `RV onCreateViewHolder` 是否减少。`setMaxRecycledViews()` 只修改上限，不会预先创建 holder；容量过大会增加 View、图片和其他绑定资源的内存占用。

`setHasStableIds(true)` 只适合每个 item 都有唯一且稳定业务 ID 的列表。即使条目移动到新位置，`getItemId(position)` 返回的 `long` 也必须保持不变；当前列表中的不同条目不能共用 ID。stable ID 能帮助 RecyclerView 在更新和动画期间识别同一个 item，但不能代替 DiffUtil，也不能修复错误的 `viewType` 设计。ID 重复或随位置变化会带来动画异常、状态串扰和错误复用。

## DiffUtil 与增量更新

整表刷新是列表卡顿的高发来源。`notifyDataSetChanged()` 没有说明哪些条目发生了插入、删除或内容变化，因此 LayoutManager 必须重新绑定并布局全部可见 View；启用 stable ID 时，RecyclerView 可以为可见项推导部分结构变化以维持动画，但不会省掉这次完整的重新绑定和重新布局。`DiffUtil` 会比较两份列表，再把插入、删除、移动和内容变化分发成细粒度 Adapter 更新。

`DiffUtil` 使用 Eugene W. Myers 差分算法寻找把旧列表变成新列表所需的最短插入/删除序列；移动不属于该算法的直接输出，需要再做一次检测。它的预期时间复杂度是 O(N + D²)，其中 N 是列表长度之和，D 是最短编辑序列长度；开启 move detection 后还会增加与新增项、删除项数量相关的扫描成本。`calculateDiff(callback, detectMoves)` 的第二个参数用于控制这轮移动检测。

应用侧通常优先使用 `ListAdapter` 或 `AsyncListDiffer`。`ListAdapter#submitList()` 内部委托 `AsyncListDiffer`：diff 在后台 executor（任务执行器）上计算，结果回到主线程后才更新当前列表并分发通知。连续提交多份列表时，已经被新提交取代的旧计算结果不会应用到 Adapter。

DiffUtil 写得好不好，取决于三个回调：

- `areItemsTheSame()`：判断新旧位置是否代表同一个业务对象，通常比较服务端 ID 或本地稳定 ID。
- `areContentsTheSame()`：比较所有会影响当前 UI 的内容；返回 `true` 时，RecyclerView 不需要重新绑定该 item。
- `getChangePayload()`：在身份相同、内容不同的情况下返回变更描述，让 Adapter 只更新受影响的 View。

payload 是一次局部更新携带的“变化说明”。下面的示例中，同一 item 只改标题时不会重新加载图片；没有 payload 时才走完整绑定。

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

这段写法减少的是完整 bind 次数，不会缩短 diff 计算本身。列表中只有标题、点赞数、关注状态这类小字段变化时，payload 往往能缩短主线程绑定时间；如果字段变化会改变 item 尺寸并触发重新测量，还要回到 [22.1 布局优化策略](./01-layout-optimization.md) 检查布局成本。

payload 只能优化局部绑定，不能承担状态正确性。目标 ViewHolder 未 attach（未挂接到当前 RecyclerView）时，payload 可能被丢弃；无 payload 的完整 bind 必须能仅凭当前 item 恢复全部 UI 状态，包括清理旧图片、选中态、监听器和无障碍描述。

大列表还有三个边界：

- 数据源按同一规则排序且 item 不会交换位置时，自行调用 `DiffUtil.calculateDiff(callback, false)` 可以省去 move detection。`ListAdapter` / `AsyncListDiffer` 的标准路径调用单参数重载，默认开启移动检测，`AsyncDifferConfig` 没有关闭开关；若改为自管 diff，还要自行处理提交批次、不可变快照和主线程更新分发。
- `areContentsTheSame()` 不要直接带入与 UI 无关的字段。埋点时间戳、临时曝光状态或调试字段如果参与比较，会让 DiffUtil 把无关变化判成需要更新。
- 提交给 `ListAdapter` / `AsyncListDiffer` 的列表及其参与比较的字段在 diff 期间应视为不可变。`AsyncListDiffer` 对相同 List 实例会直接返回；原地修改旧列表再重复 `submitList()`，既破坏新旧快照，也可能不触发任何更新。应创建新的列表和不可变 item。

## 预取机制与配置

GapWorker 是 RecyclerView 的预取任务：它根据滚动方向收集即将需要的 adapter position（Adapter 位置），并尝试在条目进入视口前取得、创建或绑定 ViewHolder。AndroidX 1.4.0 的滚动路径会调用 `mGapWorker.postFromTraversal()` 记录方向和距离，再通过 `recyclerView.post(this)` 把这个 Runnable 投递到主线程消息队列。GapWorker 不是后台线程；预取 create / bind 同样会占用主线程时间。

`GapWorker.run()` 用最近一次 drawing time（绘制时间）加刷新周期估算下一帧 deadline（截止时间），再按滚动速度、条目距离和下一帧是否需要来排列任务。普通任务在创建和绑定前分别经过 `willCreateInTime()`、`willBindInTime()`：它们根据 Pool 中按 `viewType` 记录的历史耗时，判断预计能否在截止时间前完成。预计下一帧就需要的任务会传入 `FOREVER_NS`，跳过这两个时间判断，并显示为 `RV Prefetch forced - needed next frame`；“forced”只表示不受这两个估算分支拦截，工作仍在主线程执行。

`LinearLayoutManager#setInitialPrefetchItemCount()` 只影响嵌套 RecyclerView 首次进入视口前的 initial prefetch（初始预取）数量；非嵌套列表调用它没有效果。该值应接近内层列表首次显示的 item 数。设得更大不会自动提高流畅度，反而会增加不必要的 bind、View 创建和活跃对象。

配置建议按这几步做：

1. 横向子列表首次出现时能看到 3 个完整卡片和半个卡片，就从 4 开始测试；不要直接设成整组数据长度。
2. 子列表 item 结构和绑定规则相同，可以先共享 `RecycledViewPool`，再调 `setInitialPrefetchItemCount()`。共享池不是预取生效的前提，但能减少内层列表重复创建 ViewHolder 的机会。
3. bind 中图片加载要交给图片库缓存和异步解码，Adapter 只提交 URL 和占位状态；不要在 bind 里同步解码 Bitmap。
4. 用 Perfetto 看 `RV Prefetch`、`RV Nested Prefetch`、带 `forced - needed next frame` 的预取切片，以及 `RV onCreateViewHolder type=...`、`RV onBindViewHolder type=...` 的相对位置。预取切片出现但下一帧仍然 create，说明目标 position、预算、缓存或 `viewType` 还要继续核对。

GapWorker 只提前取得 holder，并按需执行 create 和 bind，不会替下一帧完成 item 的 Measure / Layout（测量/布局）。若 trace 中 prefetch 和 bind 都正常，下一帧 `RV OnLayout` 或 framework `measure` / `layout` 仍然很长，问题应转向 item 尺寸、布局结构和图片结果触发的 `requestLayout()`。

共享 Pool 也共享按 `viewType` 统计的 create / bind 运行均值。多个 Adapter 共享同一 Pool 时，除了 ViewHolder 结构要兼容，构造和绑定成本也不宜差异悬殊，否则一个 Adapter 的历史均值会影响另一个 Adapter 的 deadline 判断。

Android 17 对 `targetSdkVersion >= 37` 的应用启用新的 MessageQueue 实现。它可以消除旧队列中的一类入队锁竞争，却没有改变 GapWorker 的 position 收集、排序、create / bind 预算或主线程执行属性；具体边界见后文 DeliQueue 小节。

`setItemViewCacheSize()` 会增大 `mCachedViews` 的请求值，让刚滑出屏幕的 ViewHolder 保持绑定状态，从而减少短距离回滑时的 bind；代价是持有更多 View、图片引用和 item 状态。Feed 流、瀑布流和长列表不要先凭经验调大，应先根据 create、bind、内存与 GC（垃圾回收）数据判断，并检查 `viewType`、payload 和共享 Pool。

## 嵌套滚动与多 RecyclerView 场景优化

多 RecyclerView 场景常见于首页 Feed、频道页、卡片流和 ViewPager2。性能问题通常来自多层列表在同一帧里同时触发布局、绑定和预取，“嵌套”本身不是足够具体的原因。

处理顺序可以固定下来：

- **避免无界测量**：不要把 RecyclerView 放进纵向 `NestedScrollView` 后，再让父容器要求它按全部内容高度测量。RecyclerView 可能一次准备大量 item，回收优势随之消失，行为接近把所有子 View 放进普通 `LinearLayout`。
- **优先合并同向列表**：纵向 RecyclerView 里再放纵向 RecyclerView，会增加触摸分发、NestedScrolling（父子容器协商滚动距离）和测量的复杂度。页面能由单个 RecyclerView 的多种 `viewType` 表达时，可以用 `ConcatAdapter` 把多个 Adapter 串成一个列表。
- **异向嵌套先共享 Pool**：纵向 Feed 里的横向卡片列表，如果 ViewHolder 创建规则兼容，可给内层列表共享 `RecycledViewPool`，再设置 initial prefetch。
- **容器尺寸不受数据影响时声明 fixed size**：`setHasFixedSize(true)` 表示 Adapter 内容变化不会改变 RecyclerView 自身的测量宽高。它不要求每个 item 等高，也不会阻止 item 内部重新 Measure / Layout。RecyclerView 为固定高度或 `match_parent` 时常可使用；若 RecyclerView 自身为 `wrap_content`，增删 item 会改变容器尺寸，就不应开启。
- **动画按收益打开**：频繁局部刷新、点赞态变化、倒计时列表中，`DefaultItemAnimator` 的 change animation（内容变更动画）可能带来额外布局和闪烁。可以只关闭这类动画，保留插入、删除或移动动画。

下面这段代码用于“外层纵向 Feed + 内层横向卡片”的基础配置。它声明容器尺寸稳定、共享回收池，并按首次可见卡片数设置 initial prefetch。

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

这段配置把 `visibleCardCount` 定义为“首次出现时完整可见的卡片数”，额外的 1 用来覆盖部分露出或紧邻视口的卡片。它还假设内层 RecyclerView 的自身尺寸由外层卡片确定，Adapter 内容变化不会改变其测量宽高。内层 item 可以有不同宽度或高度，`setHasFixedSize(true)` 也不会掩盖 child（子 View）的尺寸变化；它只表示 RecyclerView 处理 Adapter 更新时可以依赖容器尺寸不变。`recycleChildrenOnDetach = true` 会在 LayoutManager 分离时回收当前 child，可能改变图片、播放器或 ComposeView 的资源清理时机，需要随页面生命周期一起验证。

## 变更动画与局部刷新要一起看

局部刷新做完后，还要看 ItemAnimator。change animation 会比较 item 更新前后的状态；`getChangePayload()` 虽能减少绑定范围，动画器仍可能让旧、新 ViewHolder 同时参与过渡，增加布局和绘制压力。点赞、关注、计数器这类高频状态变更，通常只需要文本或图标状态切换，不需要整行 change animation。

在同一台设备上录两段 Perfetto，一段保留 change animation，一段关闭 `supportsChangeAnimations`。如果关闭后 `RV OnLayout`、`RV onBindViewHolder` 和慢帧数量下降，并且交互视觉没有损失，就把关闭范围限定在对应 Adapter 或页面，不要全局一刀切。

## Android 17 DeliQueue：只改变消息入队，不替代列表优化

Android 17 在 `targetSdkVersion >= 37` 时默认启用无锁 MessageQueue 实现 DeliQueue。旧实现用一个 monitor（Java 对象锁）保护按时间排序的消息链表；DeliQueue 让生产者通过 Treiber stack 提交消息——这是用 CAS（Compare-And-Swap，比较并交换）更新栈顶的无锁栈——再由 Looper 独占的 min-heap（按执行时间排序的最小堆）维护消费顺序。它消除的是旧 MessageQueue 的这类锁竞争，不会缩短 `onCreateViewHolder()`、`onBindViewHolder()`、item 测量/布局、图片解码、RenderThread 或 SurfaceFlinger 的工作。

RecyclerView 1.4.0 的 `GapWorker.postFromTraversal()` 仍通过 `RecyclerView.post()` 把预取任务送入主线程队列。从 post 到 `GapWorker.run()` 之间仍可能排着更早到期的消息，也可能遇到长回调或 CPU 调度延迟；无锁入队不等于立即执行。预取自身也只覆盖 holder 获取、create 和 bind，下一帧的测量/布局仍需单独分析。

排查时按证据分流：

- 主线程出现指向旧 `MessageQueue` 的 `monitor contention`（等待对象锁）时，才把队列锁列为候选；切换 `USE_NEW_MESSAGEQUEUE` 后要重启进程，再对同一个 APK 做 A/B 对照。
- `RV Prefetch` 很晚、却没有队列锁等待时，检查前序 Looper 消息、主线程 Runnable 执行时间和 CPU 调度轨道。
- `RV onCreateViewHolder` / `RV onBindViewHolder` 很长时，回到 Pool、payload、图片和数据转换；`RV OnLayout` 很长时，回到约束和布局层级。
- App SurfaceFrame（应用侧帧）按时而 DisplayFrame（显示侧帧）迟到时，继续检查目标 layer（图层）、fence（跨处理单元同步信号）、SurfaceFlinger 与 HWC，不把它归到 DeliQueue。

适配 `targetSdkVersion 37` 时，还要清点通过反射读取 `MessageQueue.mMessages` 的测试、监控和调试工具；DeliQueue 只为二进制兼容保留该字段，启用新实现后它始终为 `null`。官方要求升级到 Espresso 3.7.0 或更高版本、Robolectric 4.17 或更高版本，并把 Robolectric 的 `@LooperMode(LEGACY)` 迁移到 `@LooperMode(PAUSED)`。业务侧仍要合并同一 item 的高频结果、限制主线程单次批量消费的工作量，并在页面生命周期结束时取消尚未应用的更新；无锁队列不能修复消息堆积。

## RecyclerView vs LazyColumn 性能对比

`LazyColumn` 和 RecyclerView 都围绕可见窗口按需准备 item，也可能因预取或 beyond-bounds（焦点搜索、动画等越过当前布局边界的访问）准备窗口之外的内容。Compose 的 `key` 为 item 提供跨位置变化仍稳定的身份，`contentType` 则告诉 Lazy 列表哪些 item 具有可兼容的组合结构。它和 RecyclerView 的 `viewType` / Pool 思路相近：类型划分越贴近可复用的 UI 结构，复用越稳定。

两者选型不要用固定结论：

| 页面条件 | 更适合 RecyclerView | 更适合 LazyColumn |
| --- | --- | --- |
| 既有 View 页面 | 已有 Adapter、图片库、曝光、分页和共享 Pool | 为单个 Compose 模块引入 View/Compose 混排成本高 |
| item 类型很多 | Pool、`viewType`、payload 已经调好 | `key`、`contentType` 清晰，item 状态已移到稳定的数据层 |
| 高频局部刷新 | payload 和 ItemAnimator 可细调 | 状态粒度拆得足够细，避免整行重组 |
| 团队能力 | 熟悉 Perfetto + RecyclerView trace | 熟悉 Compose 重组、Layout Inspector、Macrobenchmark |

迁移判断要看同一设备、同一数据集和同一交互脚本。至少对比四组指标：慢帧率、P95 帧耗时（95% 的采样不超过该值）、内存峰值、首屏可交互时间。Compose 写法中不要在 `LazyColumn` 的 `items` 内容里反复排序、过滤或创建大对象；这些工作会随重组重复发生，应按[官方 Compose 性能建议](https://developer.android.com/develop/ui/compose/performance/bestpractices)移到列表外计算，并用 `remember` 或更上游的数据层保存结果。

## RecyclerView 1.4 与自适应刷新率协作

RecyclerView 1.4.0 要求 `compileSdk >= 35`；运行在 API 35 及以上时，它会在 `OverScroller` 驱动的 fling（手指离开后的惯性滑动）和 smooth scroll（程序控制的平滑滚动）路径中调用 `View.setFrameContentVelocity()`，把滚动速度作为平台刷新率策略的输入。RecyclerView 不查询面板能力，也不直接决定切换到哪个 Hz。Android 17 上若要判断效果，应同时核对 RecyclerView 版本、速度上报、Display 支持范围、系统刷新率决策和帧数据，不能把面板切换结果归因给单个 Adapter 参数。

## 验收清单

RecyclerView 优化完成后，至少跑一次本地 trace 和一次线上指标回看：

- Perfetto 中 `RV onCreateViewHolder type=...` 若在稳定滑动阶段持续出现，回看 Pool、`viewType`、新类型进入窗口和 initial prefetch。
- `RV onBindViewHolder type=...` 应结合完整帧 deadline 与同一帧其他主线程工作判断；如果 bind 耗时的高分位值持续变长，回看 payload、图片加载、文本处理和同步 I/O。
- `RV Prefetch` / `RV Nested Prefetch` 及 forced 变体出现后，核对目标 position 的 create / bind 是否前移，并检查后续关键帧成本；不要只按切片是否存在判断命中。
- 慢帧集中在 `RV OnLayout` 时，回到 22.1 节查 item 布局层级、`requestLayout()` 来源和 change animation。
- UI 线程按时完成后仍有 jank（卡顿），继续检查 RenderThread、`queueBuffer`（应用提交图形缓冲区）、`BufferTX - <layerName>`（目标图层的缓冲区事务）、latch（SurfaceFlinger 采纳缓冲区）与 FrameTimeline present（最终上屏时刻）；列表切片不能解释完整显示链。
- 线上按页面、机型、刷新率、列表类型拆指标；只看全局平均值会把低端机和复杂页面的问题稀释掉。

这套检查的目标是把 RecyclerView 问题拆成四类：复用没命中、增量更新没生效、预取没赶上、嵌套布局太重。分类清楚后，优化动作才不会互相抵消。

## 源码与文档

- [RecyclerView 1.4.0 source jar](https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar)：`RecyclerView`、`GapWorker`、`DiffUtil`、`AsyncListDiffer`、`ListAdapter` 与 `LinearLayoutManager` 的固定源码基线。
- [RecyclerView 1.4.0 release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview#recyclerview-1.4.0)：版本变化与 Adaptive Refresh Rate 支持边界。
- [AndroidX versions](https://developer.android.com/jetpack/androidx/versions)：当前稳定版与预览版总表。
- [`RecyclerView.Adapter`](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.Adapter)：stable ID、整表更新与 payload 的契约。
- [`RecyclerView.setHasFixedSize()`](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView#setHasFixedSize(boolean))：RecyclerView 自身尺寸不受 Adapter 内容影响的契约。
- [`DiffUtil`](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)：差异计算、move 检测与回调语义。
- [`AsyncListDiffer`](https://developer.android.com/reference/androidx/recyclerview/widget/AsyncListDiffer)：后台 diff、列表提交与只读当前列表。
- [`LinearLayoutManager.setInitialPrefetchItemCount()`](https://developer.android.com/reference/androidx/recyclerview/widget/LinearLayoutManager#setInitialPrefetchItemCount(int))：嵌套列表 initial prefetch 的范围。
- [Compose lists](https://developer.android.com/develop/ui/compose/lists)：Lazy 列表、key 与 `contentType`。
- [Compose performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices)：列表外预计算、`remember` 与重组控制。
- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)：`setFrameContentVelocity()` 的平台入口。
- [Android 17 MessageQueue behavior change](https://developer.android.com/about/versions/17/changes/messagequeue)：target SDK 37 的 MessageQueue 边界。
- [Android 17 lock-free MessageQueue internals](https://developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue)：Treiber stack、min-heap 与锁竞争分析。
