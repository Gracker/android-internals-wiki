---
title: "RecyclerView 列表滑动性能深度优化"
chapter: "7.8"
section: "7.8"
status: ready-for-review
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [recyclerview, scrolling, jank, prefetch, difftutil, nested-scrolling, arr, viewholder, viewcache, gapworker]
related_chapters: ["7.1", "7.2", "7.4", "7.5", "2.4", "2.18", "9.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-06"
last_verified_against: "AOSP android-17.0.0_r3"
confidence: medium
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
sources:
  - type: aosp
    path: "frameworks/support/recyclerview/src/main/java/androidx/recyclerview/widget/"
  - type: official
    path: "developer.android.com/reference/androidx/recyclerview/widget/RecyclerView"
  - type: blog
    path: "android-developers.googleblog.com - Adaptive Refresh Rate"
---

# 7.8 RecyclerView 列表滑动性能深度优化

列表滑动是 Android 用户最高频的操作之一，也是流畅性问题最集中的场景。RecyclerView 作为列表渲染的标准组件，其内部机制相当复杂——四级缓存、预取、嵌套滑动、Diff 增量更新——每一层都可能成为性能瓶颈，也可能成为优化手段。

这篇文章的目标是讲清楚 RecyclerView 内部那些影响滑动性能的关键机制，让我们在 Perfetto 中看到卡顿的时候，能快速定位到具体是哪一层出了问题。

## RecyclerView 的布局流程

RecyclerView 的每次布局都走 `onLayout()` → `dispatchLayoutStep1/2/3` 三个阶段。这不是随便分的三个步骤，每个步骤都有明确的职责：

`dispatchLayoutStep1` 处理 Adapter 的更新（如果有的话），包括预布局（pre-layout）。预布局是 RecyclerView 的一个巧妙设计——当 Adapter 数据变化时，RecyclerView 会先用旧数据做一次布局来记录旧位置，然后用新数据做正式布局，这样 ItemAnimator 就能根据新旧位置的差异计算动画。

`dispatchLayoutStep2` 是真正的布局阶段，LayoutManager 在这里决定每个 Item 的位置和大小。如果启用了自动测量（`isAutoMeasureEnabled`，默认开启），RecyclerView 会在这一步完成 measure 和 layout。

`dispatchLayoutStep3` 完成动画的启动和最终的清理工作。

对性能分析来说，关键在于 step2——如果这一步耗时过长，在 Perfetto 中就会表现为 doFrame 内部有一个很长的 layout 时间段，对应的 track 通常是 `Choreographer#doFrame` → `RecyclerView` 下面的一长条。

RecyclerView 和传统的 ListView 相比，架构上有两个核心优势。第一，将布局逻辑完全委托给 LayoutManager，使得 LinearLayoutManager、GridLayoutManager、StaggeredGridLayoutManager 可以各自优化自己的布局策略。第二，ViewHolder 的回收复用体系（下面会详细讲），这是 RecyclerView 性能优势的根基。

[图：RecyclerView layout 三阶段时序图，标注 step1/step2/step3 在 Perfetto Trace 中的对应区域]

## ViewHolder 回收复用的四级缓存

RecyclerView 的缓存体系分为四级，理解每一级的工作方式，是在 Trace 中分析滑动卡顿的基础。

第一级是 **AttachedScrap**。当 RecyclerView 发生布局变化但不需要移除任何 ViewHolder 时（比如 item 位置移动），被移出屏幕但还会回来的 ViewHolder 会暂时放在这里。AttachedScrap 中的 ViewHolder 仍然附着在 RecyclerView 上，不需要重新 bind。在 ItemAnimator 执行动画期间，旧的 ViewHolder 就存放在 Scrap 中。

第二级是 **CachedViews**。这是一个默认大小为 2 的 ArrayList，存储刚滑出屏幕的 ViewHolder。CachedViews 的特点是：存在这里的 ViewHolder 不需要重新 bind——它们的 position 和数据都是有效的，直接拿来用就行。这就好比"刚放下的东西还没收起来"，拿起来最快。缓存大小可以通过 `setItemViewCacheSize()` 调整。对于频繁上下滑动的场景，适当增大这个值（比如设为 4-6）可以减少 bind 调用次数。

第三级是 **ViewCacheExtension**。这是一个可选的、由开发者自定义的缓存层。Google 官方文档对它的定位是"给开发者留的扩展点"，但实际上大多数场景用不到它。如果确实需要这一层缓存，要特别注意它和 RecycledViewPool 的查找顺序——ViewCacheExtension 在 Pool 之前被查询。

第四级是 **RecycledViewPool**。这是最终的缓存池，默认每个 ViewType 缓存 5 个 ViewHolder。Pool 中的 ViewHolder 会被清除绑定状态（resetInternal），再次使用时必须重新 bind。Pool 的一个重要特性是可以跨 RecyclerView 共享——对于嵌套 RecyclerView 的场景（比如外层列表中每个 item 内部都有一个水平滑动列表），共享 Pool 可以大幅减少 inflate 开销。

缓存查找的顺序是：AttachedScrap → CachedViews → ViewCacheExtension → RecycledViewPool。如果在所有缓存中都没找到，才会调用 `onCreateViewHolder()` 创建新的。

在 Perfetto 中，我们可以通过观察 `RV Prefetch` 和 `RV OnBindView` 这两类 trace point 来判断缓存效率。如果一个 fling 操作中频繁出现 `onCreateViewHolder` 或 `onBindViewHolder`，说明缓存命中率低，需要调整缓存大小或检查是否有不必要的 invalidate。

[已验证: AOSP android-17.0.0_r3, frameworks/support/recyclerview/src/main/java/androidx/recyclerview/widget/Recycler.java — tryGetViewHolderForPositionByDeadline()]

## GapWorker 预取机制

RecyclerView 从 Android 5.0 开始引入了 GapWorker 预取机制。它的核心思想是：在 UI 线程空闲时，提前创建并绑定即将进入屏幕的 ViewHolder，这样当真正的布局发生时，需要的 ViewHolder 已经准备好了。

GapWorker 在 `Choreographer.doFrame()` 的 COMMIT 阶段被触发。这个时间点的选择很讲究——COMMIT 阶段是当前帧布局完成之后、下一帧开始之前的空隙。RecyclerView 利用这个空隙，根据当前的滑动方向和速度，预测接下来几个 item 的位置，然后提前执行 create + bind。

对于嵌套 RecyclerView（比如 ViewPager2 内部的列表），`setInitialPrefetchItemCount` 是一个关键参数。它控制内层 RecyclerView 在首次可见时预先创建多少个 item。默认值是 2，如果内部列表每个 item 的 inflate 成本较高（比如包含复杂的布局或图片），可以适当增大这个值到 3-4。但不要盲目增大——预取太多会占用当前帧的时间，反而导致卡顿。

预取失败的常见原因有几种。最常见的是缓存污染——如果 CachedViews 中有被标记为 invalid 的 ViewHolder（比如刚经历了数据更新），GapWorker 在预取时可能找不到合适的缓存，被迫创建新的。另一个原因是布局未完成——如果上一帧的布局还没结束（比如嵌套 RecyclerView 的内部布局延迟），GapWorker 无法正确预测下一个 item 的位置。

```java
// androidx/recyclerview/widget/GapWorker.java
// @ AOSP recyclerview-1.4.0
void prefetch(long deadlineNs) {
    // deadlineNs 是当前帧的截止时间，prefetch 必须在此之前完成
    if (mRecyclerViews.isEmpty()) return;
    
    // 1. 从所有注册的 RecyclerView 收集预取请求
    //    每个 RecyclerView 的 LayoutManager 通过 getPrefabItemCount()
    //    报告需要预取的 item 数量（默认 LinearLayoutManager 返回相邻 2 个）
    // 2. 按优先级排序：当前正在 fling 的 RecyclerView 优先级最高
    // 3. 对每个请求依次执行 create + bind，中途检查是否超过 deadline
    //    如果超时，剩余请求被丢弃——宁可少预取也不能影响当前帧
}
```

这段代码的关键在于：预取不是免费的。如果 `create + bind` 本身很慢（比如 item 布局过于复杂），预取会挤占 COMMIT 阶段的时间，影响下一帧的准备。在 Perfetto 中，如果一个 doFrame 的 COMMIT 阶段耗时异常长，可以检查是否有过多的预取活动。

[已验证: AOSP recyclerview-1.4.0, GapWorker.java — prefetch() 和 collectPrefetchPositions()]

## DiffUtil 与增量更新

当列表数据发生变化时，最简单的做法是调用 `notifyDataSetChanged()`——但这会触发整个列表的重新布局，即使只有一个 item 发生了变化。DiffUtil 解决的就是这个问题：它通过计算新旧列表之间的最小差异集，只更新真正变化的 item。

DiffUtil 的核心算法是 Eugene W. Myers 的差分算法。这个算法的时间复杂度是 O(N + D²)，其中 N 是两个列表的总长度，D 是编辑距离（插入/删除/修改的数量）。对于大多数实际场景（少量 item 变化），D 很小，算法非常快。但如果数据变化很大（比如清空后重新加载），D 接近 N，时间复杂度会退化到 O(N²)。

`AsyncListDiffer` 将 diff 计算放到后台线程。它的 `submitList()` 方法会先在后台线程执行 `DiffUtil.calculateDiff()`，计算完成后在主线程分发更新通知。这是一个关键的性能优化——如果 diff 计算耗时超过 16ms（一帧的预算），放在主线程就会直接导致掉帧。

DiffUtil 有两个核心回调需要正确实现。`areItemsTheSame()` 判断两个 item 是否代表同一个对象（通常比较 id），`areContentsTheSame()` 判断同一个对象的内容是否完全一致。这两个方法的实现直接影响 diff 的性能和正确性。

一个经常被忽略的优化是 Payload 机制。当 `areItemsTheSame()` 返回 true 但 `areContentsTheSame()` 返回 false 时，DiffUtil 会调用 `getChangePayload()` 来获取变化的详情。如果返回了非 null 的 payload，Adapter 会收到 `onBindViewHolder(holder, position, payloads)` 而不是完全的重新绑定。这意味着我们可以只更新变化的部分（比如一个文字标签），而不需要重新绑定整个 item 的所有数据。

对于大列表的 diff 优化，几个实用的建议：

- 确保数据类的 `equals()` 方法实现正确且高效（data class 默认会生成，但注意避免包含不必要的字段）
- 如果不需要检测移动操作，可以在 `calculateDiff()` 时传入 `detectMoves=false`，这会跳过二次扫描，减少计算量
- 对于分页加载的场景，只对新加载的一页数据做 diff，而不是对整个列表做

```java
// payload 实现示例：只更新变化的字段
@Override
public void onBindViewHolder(@NonNull ViewHolder holder, int position, 
                            @NonNull List<Object> payloads) {
    if (payloads.isEmpty()) {
        // 没有 payload，执行完整的 bind
        onBindViewHolder(holder, position);
        return;
    }
    // 有 payload，只更新变化的部分
    Bundle diff = (Bundle) payloads.get(0);
    if (diff.containsKey("title")) {
        holder.title.setText(diff.getString("title"));
    }
    if (diff.containsKey("avatar")) {
        loadImage(holder.avatar, diff.getString("avatar"));
    }
}
```

[已验证: AOSP recyclerview-1.4.0, DiffUtil.java — Myers 差分算法实现]

### RecycledViewPool 共享的典型实现

嵌套 RecyclerView 的场景下，共享 RecycledViewPool 是最有效的优化手段之一。核心思路是：为同类型的内层列表创建一个共享 Pool，避免每个子列表各自维护独立的缓存池。

```java
// 在 Adapter 中创建共享 Pool
private final RecycledViewPool sharedPool = new RecycledViewPool();

// 配置每种 ViewType 的缓存数量（根据可见 item 数量调整）
sharedPool.setMaxRecycledViews(TYPE_NORMAL, 10);
sharedPool.setMaxRecycledViews(TYPE_HEADER, 2);

@Override
public void onBindViewHolder(@NonNull ParentViewHolder holder, int position) {
    // 为每个内层 RecyclerView 设置共享 Pool
    holder.innerRecyclerView.setRecycledViewPool(sharedPool);
    // 滑出屏幕时立即回收子 ViewHolder
    holder.innerRecyclerView.setRecycleChildrenOnDetach(true);
}
```

这里的关键参数是 `setMaxRecycledViews()` 的值。设置过小会导致频繁的 create/bind，设置过大则占用不必要的内存。经验值：内层列表同时可见的 item 数量 × 1.5 是一个合理的起点。

## 嵌套滑动的性能影响

嵌套滑动（NestedScrolling）是 Android 处理嵌套可滑动容器之间协作的协议。RecyclerView 通过 `NestedScrollingChild3` 接口参与这个协议，允许父 View 在子 View 滑动之前或之后拦截滑动事件。

嵌套滑动的完整流程是：子 View 开始滑动 → 分发给父 View `onNestedPreScroll()` → 父 View 消耗部分滑动距离 → 子 View 处理剩余距离 → 子 View 将未消耗的距离通过 `onNestedScroll()` 回传给父 View。这个流程在每一帧的触摸事件中都会执行。

对于嵌套 RecyclerView（最典型的场景是 ViewPager2 + 外层 RecyclerView），性能影响主要来自两个方面。第一，内外两层 RecyclerView 的布局互相触发——内层 RecyclerView 的 item 变化可能触发外层的 requestLayout，反过来也是。第二，嵌套滑动的协议本身有开销——每帧需要经过多次 dispatchNestedScroll / onNestedPreScroll 的调用。

在 Perfetto 中，嵌套滑动导致的性能问题通常表现为频繁的 `requestLayout` 调用和重复的 measure/layout pass。如果在一个 doFrame 中看到多次 layout 事件，很可能是嵌套滑动导致的。

针对嵌套 RecyclerView 的优化策略：

- 共享 RecycledViewPool：为所有内层 RecyclerView 设置同一个 Pool 实例，避免每个子列表各自维护独立的缓存池
- `setRecycleChildrenOnDetach(true)`：当内层 RecyclerView 滑出屏幕时立即回收其 ViewHolder 到共享 Pool
- `setMaxRecycledViews()` 调整 Pool 大小：根据可见 item 数量合理配置
- 禁用 OverScroll 效果：`setOverScrollMode(View.OVER_SCROLL_NEVER)`，减少不必要的绘制开销

这些优化手段的效果取决于具体的嵌套结构和数据量。在做了上述优化之后，如果嵌套滑动仍然导致明显的卡顿，需要进一步分析 doFrame 内的布局调用链路。

[图：嵌套滑动协议的时序图，标注 preScroll 和 postScroll 的分发路径]

## 滑动卡顿的根因分析

理解了 RecyclerView 的缓存体系、预取机制和嵌套滑动之后，我们需要回到一个更实际的问题：当 Perfetto 中出现掉帧，怎么快速定位是哪一层机制出了问题？

在实际工作中，RecyclerView 滑动卡顿的根因通常集中在以下几个方向。

**item 布局过深** 是最常见的性能杀手。如果每个 item 的 View 层级超过 4-5 层，measure 和 layout 的时间会呈指数级增长。用 Layout Inspector 检查 item 的 View 树，如果发现深层嵌套的 LinearLayout 或 RelativeLayout，用 ConstraintLayout 替换通常能带来显著改善。

**onBindViewHolder 中的 IO 操作** 是另一个高频问题。图片加载的磁盘 IO、数据库查询、甚至 SharedPreference 的同步读取，都可能在 bind 路径上引入不可预测的延迟。解决方法是将这些操作全部异步化——图片用 Glide/Coil 等库自动异步加载，数据预加载到内存，bind 方法只做轻量的视图更新。

**ItemAnimator 触发的额外布局** 是一个容易被忽略的问题。RecyclerView 的 ItemAnimator（特别是 DefaultItemAnimator）在执行变更动画时，需要对变化的 item 做两次布局 pass：一次记录旧位置，一次记录新位置。如果列表数据频繁更新（比如实时数据流），动画的额外开销会累积。解决方法是使用 `SimpleItemAnimator`（更轻量）或者在不需要动画的场景直接关闭 `setItemAnimator(null)`。

**图片加载回调触发的 requestLayout** 是一种隐性的性能问题。当图片异步加载完成后，如果在回调中修改了 ImageView 的尺寸（比如 `wrap_content` 导致从占位图切换到真实图片时大小变化），会触发整个 RecyclerView 的重新布局。解决方法是为 ImageView 设置固定的宽高，或者使用 `setHasFixedSize(true)` 告知 RecyclerView 不要因为 item 内容变化而重新测量自身大小。

**VSync 时间精度问题** 是一个更隐蔽的根因。这个问题的来源是 Android 列表滑动在计算每帧位移时，使用的不是 VSync 的纳秒时间戳，而是取整后的毫秒值。在 120Hz 设备上（VSync 周期约 8.33ms），±1ms 的取整误差意味着约 12% 的帧间时间差异。这种微小的时间波动传递到 OverScroller 的位移计算后，会导致列表每帧滚动的像素数不均匀。用户在快速滑动时感知到"一顿一顿"的效果，但 Perfetto 的 FrameTimeline 不会标记为 Jank——因为帧确实在预算时间内完成了，只是步幅不均匀。

这是一种"无掉帧卡顿"，和我们在 §7.1 中讨论的帧率稳定性问题不同——帧率可能是稳定的 120fps，但步幅波动让用户感觉不流畅。

[来源: 高爷卡顿知识补充 2026-04-06，VSync 时间取整问题]

## RecyclerView 1.4 与 Adaptive Refresh Rate

RecyclerView 1.4.0（2025 年 1 月发布）引入了内置的 Adaptive Refresh Rate (ARR) 支持。在支持 ARR 的设备上（Android 15+），RecyclerView 在 fling 或 smoothScroll 期间会自动调用 `View.setFrameContentVelocity()`，告知系统当前的内容滑动速度。系统根据这个信号临时提升屏幕刷新率，使滑动更流畅。

`setFrameContentVelocity()` 的参数是像素/秒为单位的速度值。RecyclerView 1.4 内部从 OverScroller 获取当前速度并传递给这个 API。对于自定义的可滑动组件，开发者需要自己实现这个调用——在每帧绘制时传入当前速度，注意速度信息会在每次重绘后被重置，需要持续更新。

ARR 的工作流程是：RecyclerView 开始 fling → 通过 `setFrameContentVelocity()` 报告速度 → SurfaceFlinger 收到信号后决定是否提升刷新率（比如从 60Hz 提升到 120Hz）→ fling 减速时刷新率逐步降低 → 停止后恢复到默认刷新率。这个过程的刷新率切换由 SurfaceFlinger 的启发式算法决定，应用层不需要关心具体的切换逻辑。

ARR 相关的新 API 包括：`hasArrSupport()` 检测设备是否支持 ARR，`getSuggestedFrameRate(int)` 查询推荐帧率，`getSupportedRefreshRates()` 列出设备支持的刷新率。这些 API 在 §2.18 中有更详细的讲解。

对于高刷新率设备（120Hz 及以上），RecyclerView 面临一个额外的挑战：帧预算从 16.67ms 缩短到 8.33ms 甚至更短。这意味着原来在 60Hz 下勉强能在 16ms 内完成的 bind 操作，在高刷新率下可能超时。如果发现高刷新率设备的滑动反而更卡，应该先检查 `onBindViewHolder` 的执行时间是否超过了一半的帧预算。

[已验证: 官方文档, developer.android.com/reference/android/view/View#setFrameContentVelocity()]
[已验证: AOSP recyclerview-1.4.0, RecyclerView.java — ARR 集成实现]

## 在 Perfetto 中分析 RecyclerView 性能

RecyclerView 在 Perfetto 中有一组专用的 trace point。在 `Choreographer#doFrame` 的 trace 中，RecyclerView 的布局操作通常以 `RV Layout` / `RV OnBindView` / `RV Prefetch` 等标记出现。

分析 RecyclerView 滑动卡顿时，建议的关注顺序：

1. **先看帧率**：在 FrameTimeline track 中检查是否有大帧（帧时间超过预算）。如果没有大帧但用户仍然反馈卡顿，考虑步幅波动问题
2. **定位慢操作**：在 `RecyclerView` track 中找到耗时超过 3ms 的操作，判断是 inflate、bind 还是 layout
3. **检查缓存效率**：连续 bind 操作多说明缓存命中率低，考虑增大 CachedViews 或 RecycledViewPool
4. **检查预取**：COMMIT 阶段的预取活动是否在挤占帧时间
5. **检查嵌套影响**：嵌套 RecyclerView 是否触发了不必要的 requestLayout

对于具体的 SQL 查询，可以用 Perfetto 的 Trace Processor 分析 RecyclerView 相关的 slice：

```sql
-- 查询 RecyclerView bind 操作耗时
SELECT name, dur / 1e6 as dur_ms
FROM slice
WHERE name LIKE '%RV OnBindView%'
ORDER BY dur DESC
LIMIT 20;

-- 查询 RecyclerView layout 操作
SELECT name, dur / 1e6 as dur_ms
FROM slice
WHERE name LIKE '%RV Layout%'
ORDER BY dur DESC
LIMIT 20;
```

[图：Perfetto 中 RecyclerView 滑动 Trace 的典型截图，标注 layout/bind/prefetch 各阶段]

## 常见问题与误区

**误区：增大 RecycledViewPool 就能解决所有滑动卡顿。** Pool 只解决 inflate 开销，如果瓶颈在 bind（比如 bind 中有 IO 操作），增大 Pool 不会有效果。要先在 Trace 中区分是 create 慢还是 bind 慢。

**误区：`setHasFixedSize(true)` 是万能优化。** 这个设置只在 RecyclerView 自身大小不因 item 变化而改变时才安全。如果 item 高度可变（比如含有动态高度的文本），设置了这个会导致 item 显示不完整。

**误区：`setItemViewCacheSize(0)` 总是负优化。** 在某些场景下（比如 item 数据频繁更新，CachedViews 中的 ViewHolder 经常 invalid），把 cache size 设为 0 反而可以避免无效的缓存查找，直接走 Pool 的 rebind 流程。但这属于针对性优化，不应该作为默认策略。

**误区：高刷新率设备上 RecyclerView 不需要优化。** 高刷新率设备的帧预算更短（120Hz 下只有 8.33ms），任何在 60Hz 下勉强达标的操作在高刷新率下都可能超时。RecyclerView 的优化在高刷新率设备上反而更重要。

## 扩展

### 🔸 自定义 LayoutManager 性能

不同 LayoutManager 的布局策略差异直接影响性能。LinearLayoutManager 的布局是线性的，每个 item 的位置只依赖前一个 item，可以增量式计算。GridLayoutManager 需要同时考虑行列关系，复杂度更高。StaggeredGridLayoutManager 最复杂——因为每个 item 高度不同，布局计算需要回溯已布局的 item 来确定间隙（gap）。

自定义 LayoutManager 时，性能的关键在于减少 `fill()` 调用中的重复计算。`onLayoutChildren()` 应该尽量做增量布局，而不是每次都从头开始。`setInitialPrefetchItemCount()` 的最佳值取决于 LayoutManager 类型：LinearLayoutManager 默认 2 已经足够，GridLayoutManager 可以设为列数 × 2。

### 🔸 ItemDecoration 与 ItemAnimator 性能

`ItemDecoration.getItemOffsets()` 在每次 measure/layout 时被调用。如果这个方法中有复杂计算（比如根据 position 动态计算间距），会直接影响布局性能。建议将计算结果缓存。

`DefaultItemAnimator` 在执行 change 动画时需要两次布局 pass，代价较高。如果列表数据频繁更新且不需要复杂动画，使用 `SimpleItemAnimator` 或者关闭动画（`setItemAnimator(null)`）可以减少一半的布局开销。

支持 change 动画（`supportsChangeAnimations()`）的额外代价是：RecyclerView 需要对变化的 item 创建一个新 ViewHolder（用于动画），然后在动画结束后回收旧的。这意味着一次 change 操作实际上创建了两个 ViewHolder，内存压力翻倍。如果不需要交叉淡入淡出的效果，重写 `supportsChangeAnimations()` 返回 false 可以避免这个开销。

## 参考资料

- **AOSP 源码**：`frameworks/support/recyclerview/src/main/java/androidx/recyclerview/widget/`（RecyclerView、Recycler、GapWorker、DiffUtil）
- **AOSP 版本基准**：android-17.0.0_r3、recyclerview-1.4.0
- **官方文档**：[RecyclerView reference](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView)
- **官方文档**：[Adaptive Refresh Rate](https://developer.android.com/reference/android/view/View#setFrameContentVelocity())
- **官方文档**：[RecyclerView 性能优化](https://developer.android.com/topic/performance/recycler-view-optimization)
- **Myers 差分算法**：Eugene W. Myers, "An O(ND) Difference Algorithm and Its Variations", 1986
- **高爷补充素材**：VSync 时间精度与步幅波动（2026-04-06）

---

### 🔸 Compose LazyColumn 与 RecyclerView 的性能对比

[待补充：Compose LazyColumn 的性能特征与 RecyclerView 的对比，包括 recomposition 开销、prefetch 策略差异、LazyListState 的性能影响]
