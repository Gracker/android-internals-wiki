---
title: RecyclerView 列表滑动性能深度优化
chapter: '7.8'
section: '7.8'
status: 'ready-for-review'
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
tags:
- recyclerview
- scrolling
- jank
- prefetch
- diffutil
- nested-scrolling
- arr
- viewholder
- viewcache
- gapworker
related_chapters:
- '7.1'
- '7.2'
- '7.4'
- '7.5'
- '2.4'
- '2.18'
- '9.4'
created_by: task2a-knowledge-gap
created_date: '2026-04-06'
drafted_date: '2026-04-06'
drafted_by: openclaw-task2a
last_verified: '2026-05-27'
last_verified_against: AndroidX androidx-main + Android Developers MessageQueue docs 2026-05-12 + RecyclerView 1.4.0 release notes + Android API 35/36 refs
confidence: medium
polish_count: 1
polish_date: '2026-04-08'
polish_by: task2b-polish
reviewed_date: "2026-05-27"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
sources:
- type: androidx
  path: platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/RecyclerView.java
- type: androidx
  path: platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/GapWorker.java
- type: androidx
  path: platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/LinearLayoutManager.java
- type: androidx
  path: platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/DiffUtil.java
- type: aosp
  path: platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/View.java
- type: aosp
  path: platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/Display.java
- type: official
  path: https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/recyclerview
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
last_task9_at: "2026-05-27T03:29:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-27"
review_notes: '2026-05-27 task6 review: needs-rework。L1/L2 已小修；2026-05-27 Task2B 已合并清理后半段调研素材，回流 Task6 复审；2026-05-27 Task6复审：pass-light-edit，L1/L2 小修 10 处，无回炉项，等待 Task9 复审。'
task9_review_notes: "2026-05-13 02:51 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 2；Android 17 DeliQueue 版本/数据口径需补一手证据；ViewHolder 缓存语义与 GapWorker 研究块作为 P2 整理。 | 2026-05-27 01:22 Task9 deep-review：needs-rework。P0 0 / P1 1 / P2 0；后半段 GapWorker measure 盲区与 DeliQueue 过程材料已由 Task2B 合并进正文，等待 Task6 复审。 | 2026-05-27 03:29 Task9 deep-review：auto-fixed。P0 0 / P1 1 / P2 1；修正 setHasFixedSize(true) 语义与 create/bind Trace 命中判断，回到 Task6 复审。"
last_task2b_verifier_at: '2026-05-26T23:25:00+08:00'
last_task2b_at: '2026-05-27T02:50:00+08:00'
last_task6_at: "2026-05-27T03:14:00+08:00"
last_review_log: "logs/review/2026-05-27-03-review.md"
last_task9_review_log: "logs/deep-review/2026-05-27-03-deep-review.md"
last_task9_autofix_at: "2026-05-27"
---


# 7.8 RecyclerView 列表滑动性能深度优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 RecyclerView 三阶段布局流程，以及 `dispatchLayoutStep1/2/3` 在 Trace 中的定位方式
- 🔹 ViewHolder 四级缓存与 `onCreateViewHolder()` / `onBindViewHolder()` 的缓存命中判断
- 🔹 GapWorker 预取、`setInitialPrefetchItemCount()` 与嵌套列表预取调优
- 🔹 DiffUtil、`AsyncListDiffer` 与 payload 局部刷新
- 🔹 嵌套滑动、共享 `RecycledViewPool` 与常见滑动卡顿根因
- 🔹 在 Perfetto 中分析 RecyclerView 滑动卡顿的顺序和 SQL 查询

### 扩展（可选深入）

- 🔸 RecyclerView 1.4 与 Adaptive Refresh Rate
- 🔸 自定义 LayoutManager、ItemDecoration、ItemAnimator 的性能代价

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 需要继续核对源码或版本边界的内容，保留 `[需确认]`，不要把猜测写成结论。
<!-- outline-end -->

列表滑动是 Android 用户最高频的操作之一，也是流畅性问题最集中的场景。RecyclerView 作为列表渲染的标准组件，内部涉及缓存复用、预取、嵌套滑动和增量更新，这几层机制都会直接影响滑动帧时间。

这篇文章聚焦那些最容易在 Perfetto 里暴露出来的点，用于在看到卡顿时判断问题落在布局、bind、缓存还是预取阶段。

## RecyclerView 的布局流程

RecyclerView 的一次完整布局仍然由 `dispatchLayoutStep1()`、`dispatchLayoutStep2()`、`dispatchLayoutStep3()` 组成，但 Perfetto 不会直接把这三个阶段显示成同名 slice。当前 AndroidX 主线打点的是外层入口：`onLayout()` 对应 `RV OnLayout`，`consumePendingUpdateOperations()` 在整表失效时打 `RV FullInvalidate`，在局部更新路径上打 `RV PartialInvalidate`。因此，Trace 里看到的是外层布局切片，分析时再结合调用栈和更新类型判断 step1/2/3 落在什么位置。

`dispatchLayoutStep1()` 负责消费 Adapter 更新、决定是否运行 predictive animation、保存旧布局信息。列表收到 `notifyDataSetChanged()` 这类整表失效时，外层 slice 往往是 `RV FullInvalidate`。收到局部更新并且 `AdapterHelper` 能在一次 pass 里处理时，更常见的是 `RV PartialInvalidate`。

`dispatchLayoutStep2()` 进入最终布局阶段，`LayoutManager.onLayoutChildren()` 在这里摆放 item。LinearLayoutManager、GridLayoutManager、StaggeredGridLayoutManager 的差异，主要都体现在这一段。Perfetto 里通常只能看到 `RV OnLayout` 或前面的 invalidation slice，而看不到名为 `dispatchLayoutStep2` 的独立标签。所以判断 step2，靠的是展开 `RV OnLayout` 的调用栈，确认时间是不是花在 `onLayoutChildren()`、子 view measure/layout，或者布局前后紧邻的 bind / inflate。

`dispatchLayoutStep3()` 负责记录 post-layout 信息、驱动 ItemAnimator、清理 scrap 和旧状态。源码同样没有给 step3 单独打 `Trace.beginSection()`，只能通过 `dispatchLayout()` 尾部调用和随后的动画行为侧推。

把三阶段和 Trace 对应起来时，用下面这组映射更稳妥：

- step1：`RV FullInvalidate` / `RV PartialInvalidate` 外层 slice，常伴随 Adapter 更新处理
- step2：`RV OnLayout` 内部的 `LayoutManager.onLayoutChildren()` 和子 view layout
- step3：`dispatchLayout()` 收尾后的动画、scrap 回收与状态清理，通常没有独立 slice 名

对性能分析来说，先盯 `RV OnLayout`。如果它在一个 `doFrame` 里反复出现，或者单次耗时已经吃掉大半帧预算，再继续展开调用栈区分是布局本身慢，还是前面的更新合并、bind、动画准备把时间吃掉了。

RecyclerView 和 ListView 的差别主要在两处。布局策略交给 `LayoutManager`，不同布局可以单独优化。ViewHolder 回收复用体系把 create/bind 的成本尽量从滑动路径上挪开，后面几节的缓存、预取和共享 Pool 都围绕这件事展开。

[图：RecyclerView 三阶段布局与 `RV FullInvalidate` / `RV PartialInvalidate` / `RV OnLayout` 的对应关系]

## ViewHolder 回收复用的四级缓存

RecyclerView 的缓存体系分为四级，理解每一级的工作方式，是在 Trace 中分析滑动卡顿的基础。

第一级是 **AttachedScrap**。当 RecyclerView 发生布局变化但不需要移除任何 ViewHolder 时（比如 item 位置移动），被移出屏幕但还会回来的 ViewHolder 会暂时放在这里。AttachedScrap 中的 ViewHolder 仍然附着在 RecyclerView 上，不需要重新 bind。在 ItemAnimator 执行动画期间，旧的 ViewHolder 就存放在 Scrap 中。

第二级是 **CachedViews**。这是一个默认大小为 2 的 ArrayList，存储刚滑出屏幕的 ViewHolder。CachedViews 的特点是：存在这里的 ViewHolder 不需要重新 bind——它们的 position 和数据都是有效的，直接拿来用就行。缓存大小可以通过 `setItemViewCacheSize()` 调整。对于频繁上下滑动的场景，适当增大这个值（比如设为 4-6）可以减少 bind 调用次数。

第三级是 **ViewCacheExtension**。这是一个可选的、由开发者自定义的缓存层。Google 官方文档对它的定位是"给开发者留的扩展点"，但多数项目里用不到它。如果需要这一层缓存，要特别注意它和 RecycledViewPool 的查找顺序——ViewCacheExtension 在 Pool 之前被查询。

第四级是 **RecycledViewPool**。这是最终的缓存池，默认每个 ViewType 缓存 5 个 ViewHolder。Pool 中的 ViewHolder 会被清除绑定状态（resetInternal），再次使用时必须重新 bind。Pool 的一个重要特性是可以跨 RecyclerView 共享——对于嵌套 RecyclerView 的场景（比如外层列表中每个 item 内部都有一个水平滑动列表），共享 Pool 可以减少重复 inflate 开销。

缓存查找的顺序是：AttachedScrap → CachedViews → ViewCacheExtension → RecycledViewPool。如果在所有缓存中都没找到，才会调用 `onCreateViewHolder()` 创建新的。

在 Perfetto 中，缓存命中率不能靠假想的 `RV OnBindView` 名字判断。当前 AndroidX 打点使用的是 `RV Prefetch`、`RV onCreateViewHolder type=0x%X` 和 `RV onBindViewHolder type=0x%X`。fling 过程中频繁出现 create slice，通常说明 scrap、CachedViews、ViewCacheExtension 和 RecycledViewPool 都没有命中，只能新建 holder；频繁出现 bind slice，则说明拿到的 holder 需要重新绑定，可能来自 RecycledViewPool，也可能来自 invalid / stale holder，不能简单判成 Pool 未命中。如果只有 `RV Prefetch`，没有后续 create/bind，就要继续看 GapWorker 的时间预算是不是提前放弃了这轮预取，或者目标 holder 已经 attached / cache 命中。

[已验证: AndroidX androidx-main，`RecyclerView.java` `tryGetViewHolderForPositionByDeadline()` / Adapter trace sections]

## GapWorker 预取机制

RecyclerView 的预取不是 `Choreographer#doFrame()` 的一个公开阶段。当前 AndroidX 主线里，触发点在滚动遍历之后：`scrollByInternal()` 和 `ViewFlinger.run()` 在还有滚动位移时调用 `mGapWorker.postFromTraversal()`，后者把滚动向量写进 `mPrefetchRegistry`，再用 `recyclerView.post(this)` 把 `GapWorker` 作为 Runnable 投到主线程消息队列。

```java
// RecyclerView.java
if (mGapWorker != null && (x != 0 || y != 0)) {
    mGapWorker.postFromTraversal(this, x, y);
}

// GapWorker.java
void postFromTraversal(RecyclerView recyclerView, int prefetchDx, int prefetchDy) {
    if (mPostTimeNs == 0) {
        mPostTimeNs = recyclerView.getNanoTime();
        recyclerView.post(this);
    }
    recyclerView.mPrefetchRegistry.setPrefetchVector(prefetchDx, prefetchDy);
}
```

这段调用路径说明两件事。第一，GapWorker 跟随滚动事件调度，不挂在 `doFrame()` 的 COMMIT 回调里。第二，预取请求先记录滚动方向和距离，执行时再统一排序和消费。

具体要预取哪些 position，由 `LayoutManager.collectAdjacentPrefetchPositions()` 和 `collectInitialPrefetchPositions()` 决定。前者服务滑动中的相邻 item，后者服务嵌套列表首次可见时的 initial prefetch。`setInitialPrefetchItemCount()` 调的就是这条 initial prefetch 路径。

`GapWorker.run()` 会读取最近一次 `getDrawingTime()`，再加上刷新周期，估算下一帧 deadline。随后 `prefetchPositionWithDeadline()` 进入 `Recycler.tryGetViewHolderForPositionByDeadline()`。这里不会无条件 create/bind。创建前，Pool 先看 `willCreateInTime()`；绑定前，再看 `willBindInTime()`。这两个判断读取 `RecycledViewPool` 中对应 `viewType` 的 `ScrapData.mCreateRunningAverageNs` / `mBindRunningAverageNs`，用 `approxCurrentNs + expectedDurationNs < deadlineNs` 判断剩余时间是否足够。平均值以 `viewType` 为 key 保存在同一个 Pool 里，不混用不同类型 item 的 create/bind 成本；首次记录直接取本次耗时，后续通过 `old * 3/4 + new * 1/4` 的衰减滑动平均更新。

```java
// RecyclerView.Recycler
if (deadlineNs != FOREVER_NS
        && !mRecyclerPool.willBindInTime(viewType, startBindNs, deadlineNs)) {
    return false;
}

if (deadlineNs != FOREVER_NS
        && !mRecyclerPool.willCreateInTime(type, start, deadlineNs)) {
    return null;
}
```

这个预算判断会直接反映到 Trace。`RV Prefetch` 说明 GapWorker 已经开始工作；如果随后能看到 `RV onCreateViewHolder type=...` 或 `RV onBindViewHolder type=...`，说明这次预取真的执行了 create 或 bind。Trace 里如果只有 `RV Prefetch`，没有 create/bind，常见原因有三种：目标 position 已经 attached，缓存命中后不需要额外 bind，或者 `willCreateInTime()` / `willBindInTime()` 判断赶不上 deadline，提前退出。嵌套列表还可能出现 `RV Nested Prefetch`，含义和外层 prefetch 一样，只是目标 RecyclerView 变成了内层列表。

嵌套 RecyclerView 场景下，`setInitialPrefetchItemCount()` 仍然可以调整，但它控制的是 initial prefetch 请求数量，不保证这些请求都能在本帧预算内完成。item inflate 或 bind 很重时，请求数设得再大，也可能被时间预算提前截断。

GapWorker 的时间预算只覆盖 ViewHolder 获取、create 和 bind 路径，不覆盖下一帧进入 `RV OnLayout` 后的 measure/layout。复杂 item 使用 `ConstraintLayout`、`match_constraint`、Barrier 或多层依赖时，`willBindInTime()` 可能根据 2ms 左右的 bind 均值判断赶得上 deadline，但下一帧 measure/layout 仍可能把 8.33ms 或 16.6ms 帧预算吃完。

这种盲区在 Perfetto 里有一组稳定特征：`RV Prefetch` 已经出现，`RV onBindViewHolder type=...` 耗时正常，下一帧的 `RV OnLayout` 或子 view measure/layout 明显变长。处理方向是固定 item 尺寸、减少约束求解、降低嵌套层级，并把 bind 与 measure 分开计时。

### Android 17 DeliQueue 对预取调度的影响

Android 17 为 `targetSdkVersion >= 37` 的应用启用新的 lock-free `MessageQueue` 实现 DeliQueue；低于这个 target 的应用默认仍走旧的 lock-based 实现，debuggable build 可用 `adb am compat enable USE_NEW_MESSAGEQUEUE <package>` 提前测试。这个边界来自 Android 17 MessageQueue behavior change 文档，不依赖 AOSP benchmark 代码。

`GapWorker` 通过 `recyclerView.post(this)` 把自己投到主线程队列。旧实现中，后台线程 `Handler.post()`、`AsyncListDiffer` diff 结果回调和主线程 `next()` 共享同一把 `MessageQueue` monitor；后台线程持锁时被调度器抢占，主线程就可能在取消息阶段等待。DeliQueue 的设计口径来自 Google Android Developers Blog：入队侧使用 Treiber stack，Looper 侧使用 min-heap 处理按 `when` 排序的消息，目标是移除这条 monitor contention 路径。

Google 官方 benchmark 给出的数字是 MessageQueue 级别收益：应用 missed frames 下降约 4%，System UI / Launcher 交互 missed frames 下降约 7.7%，首帧 P95 耗时下降约 9.1%。这些数字来自 Android Developers Blog，不是 RecyclerView 专项 benchmark，也不是 AOSP commit 中可直接复算的数据。

落到 RecyclerView，DeliQueue 影响的是 `recyclerView.post(this)` 到 `GapWorker.run()` 开始执行之间的队列等待。它不会改变 `collectAdjacentPrefetchPositions()`、`willCreateInTime()`、`willBindInTime()` 的算法，也不会降低 `onBindViewHolder()` 或 measure/layout 的耗时。只有 trace 中能看到 `MessageQueue` monitor contention 挤压主线程时，DeliQueue 才能让预取任务更稳定地进入 deadline 窗口；瓶颈在 bind、inflate、measure 时，仍要回到 item 结构和缓存策略处理。

诊断 DeliQueue 是否和 RecyclerView 滑动相关时，可以先筛 `android_monitor_contention` 中阻塞主线程、方法名包含 `MessageQueue` 的记录，再和 jank frame 对齐。若 trace 中没有这类等待，DeliQueue 的收益就不该被归因到本次 RecyclerView 卡顿；若等待集中发生在 `RV Prefetch` 之前或同一段 `doFrame` 附近，再继续看 `GapWorker.run()` 是否被推迟。

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;
INCLUDE PERFETTO MODULE android.frames.jank_type;

SELECT
  process_name,
  SUM(dur) / 1000000 AS sum_dur_ms,
  COUNT(*) AS count_contention
FROM android_monitor_contention
WHERE is_blocked_thread_main
  AND short_blocked_method LIKE '%MessageQueue%'
  AND upid IN (
    SELECT DISTINCT(upid)
    FROM actual_frame_timeline_slice
    WHERE android_is_app_jank_type(jank_type) = TRUE
  )
GROUP BY process_name
ORDER BY SUM(dur) DESC;
```

### 反射 MessageQueue 的监控库兼容性

DeliQueue 改变了 `MessageQueue` 的内部实现。部分基于反射访问 `MessageQueue.mMessages` 链表的 RecyclerView 性能监控库（如通过反射 hook `dispatchMessage` 来追踪 `doFrame` 内各阶段耗时），在 Android 17 上可能拿不到预期的字段值或回调时机。如果项目依赖这类库，建议切换到官方 `FrameMetrics` / `JankStats` 方案，或使用 `Choreographer.FrameCallback` + `FrameData` (API 33+) 的公开 API。

[已验证: AndroidX androidx-main，`RecyclerView.java` `scrollByInternal()` / `ViewFlinger.run()` / `tryGetViewHolderForPositionByDeadline()`，`GapWorker.java` `postFromTraversal()` / `run()` / `prefetchPositionWithDeadline()`]

## DiffUtil 与增量更新

当列表数据发生变化时，最简单的做法是调用 `notifyDataSetChanged()`——但这会触发整个列表的重新布局，即使只有一个 item 发生了变化。DiffUtil 解决的就是这个问题：它通过计算新旧列表之间的最小差异集，只更新变化的 item。

DiffUtil 的核心算法是 Eugene W. Myers 的差分算法。这个算法的时间复杂度是 O(N + D²)，其中 N 是两个列表的总长度，D 是编辑距离（插入/删除/修改的数量）。对于大多数实际场景（少量 item 变化），D 很小，算法非常快。但如果数据变化很大（比如清空后重新加载），D 接近 N，时间复杂度会退化到 O(N²)。

`AsyncListDiffer` 将 diff 计算放到后台线程。它的 `submitList()` 方法会先在后台线程执行 `DiffUtil.calculateDiff()`，计算完成后在主线程分发更新通知。这能把耗时从滑动帧里移出去：如果 diff 计算耗时超过 16ms（一帧的预算），放在主线程就会直接导致掉帧。

DiffUtil 有两个核心回调需要正确实现。`areItemsTheSame()` 判断两个 item 是否代表同一个对象（通常比较 id），`areContentsTheSame()` 判断同一个对象的内容是否完全一致。这两个方法的实现直接影响 diff 的性能和正确性。

一个经常被忽略的优化是 Payload 机制。当 `areItemsTheSame()` 返回 true 但 `areContentsTheSame()` 返回 false 时，DiffUtil 会调用 `getChangePayload()` 来获取变化的详情。如果返回了非 null 的 payload，Adapter 会收到 `onBindViewHolder(holder, position, payloads)` 而不是完全的重新绑定。这样只更新变化的部分（比如一个文字标签），而不需要重新绑定整个 item 的所有数据。

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

[已验证: AndroidX androidx-main，`DiffUtil.java` Myers 差分算法实现]

### RecycledViewPool 共享的典型实现

嵌套 RecyclerView 场景下，共享 RecycledViewPool 的作用，是把多个内层列表的 ViewHolder 放进同一组缓存桶里。这样内层列表滑出屏幕后，外层列表里下一个同类型模块可以直接复用，不用每次重新 inflate。

```java
private final RecyclerView.RecycledViewPool sharedPool = new RecyclerView.RecycledViewPool();

@Override
public void onBindViewHolder(@NonNull ParentViewHolder holder, int position) {
    RecyclerView innerRv = holder.innerRecyclerView;
    innerRv.setRecycledViewPool(sharedPool);

    RecyclerView.LayoutManager lm = innerRv.getLayoutManager();
    if (lm instanceof LinearLayoutManager) {
        LinearLayoutManager llm = (LinearLayoutManager) lm;
        llm.setInitialPrefetchItemCount(4);
        llm.setRecycleChildrenOnDetach(true);
    }
}
```

`setRecycleChildrenOnDetach(true)` 属于 `LinearLayoutManager`，`GridLayoutManager` 也能直接复用这条 API，因为它继承自 `LinearLayoutManager`。如果内层列表用的是自定义 LayoutManager，就不能把这行代码直接照抄到 `RecyclerView` 上。

`setMaxRecycledViews()` 仍然需要按 viewType 单独调。数值过小，create/bind 会频繁回到滑动路径；数值过大，则只是在拿内存换命中率。起步值可以略高于同屏可见 item 数，再用 Trace 看 create/bind 是否明显下降。

### 共享 Pool 的边界

`RecycledViewPool` 内部用 `SparseArray<ScrapData>` 按 viewType 分组，每组维护一个 `ArrayList<ViewHolder>`。`getRecycledView()` 和 `putRecycledView()` 直接操作这些集合，没有 `synchronized` 修饰——方法本身不是线程安全的。

单 RecyclerView 场景下，这些调用都跑在主线程，没有并发问题。但在多线程初始化场景下（比如后台线程预构建 ViewHolder），需要外部同步；否则并发 `putRecycledView()` 可能导致 `ArrayList` 内部状态不一致。共享 Pool 的另一个边界是不同 Adapter 共用 viewType 时，`create/bind` running average 会被互相污染，导致 `willCreateInTime()` / `willBindInTime()` 的 deadline 估计失准。

源码锚点：`androidx.recyclerview.widget.RecyclerView.RecycledViewPool`，`getRecycledView()` / `putRecycledView()` 非 synchronized 方法，内部操作 `ScrapData.mScrapHeap`（`ArrayList<ViewHolder>`）。

## 嵌套滑动的性能影响

嵌套滑动（NestedScrolling）是 Android 处理嵌套可滑动容器之间协作的协议。RecyclerView 通过 `NestedScrollingChild3` 接口参与这个协议，允许父 View 在子 View 滑动之前或之后拦截滑动事件。

嵌套滑动的完整流程是：子 View 开始滑动 → 分发给父 View `onNestedPreScroll()` → 父 View 消耗部分滑动距离 → 子 View 处理剩余距离 → 子 View 将未消耗的距离通过 `onNestedScroll()` 回传给父 View。这个流程在每一帧的触摸事件中都会执行。

对于嵌套 RecyclerView（最典型的场景是 ViewPager2 + 外层 RecyclerView），性能影响主要来自两个方面。第一，内外两层 RecyclerView 的布局互相触发——内层 RecyclerView 的 item 变化可能触发外层的 requestLayout，反过来也是。第二，嵌套滑动的协议本身有开销——每帧需要经过多次 dispatchNestedScroll / onNestedPreScroll 的调用。

在 Perfetto 中，嵌套滑动导致的性能问题通常表现为频繁的 `requestLayout` 调用和重复的 measure/layout pass。如果在一个 doFrame 中看到多次 layout 事件，很可能是嵌套滑动导致的。

针对嵌套 RecyclerView 的优化策略：

- 共享 RecycledViewPool：为所有内层 RecyclerView 设置同一个 Pool 实例，避免每个子列表各自维护独立的缓存池
- `LinearLayoutManager#setRecycleChildrenOnDetach(true)`：在内层列表使用 `LinearLayoutManager` / `GridLayoutManager` 时，滑出屏幕后立即把子 ViewHolder 回收到共享 Pool
- `setMaxRecycledViews()` 调整 Pool 大小：根据可见 item 数量合理配置
- 禁用 OverScroll 效果：`setOverScrollMode(View.OVER_SCROLL_NEVER)`，减少不必要的绘制开销

这些优化手段的效果取决于具体的嵌套结构和数据量。在做了上述优化之后，如果嵌套滑动仍然导致明显的卡顿，需要进一步分析 doFrame 内的布局调用路径。

[图：嵌套滑动协议的时序图，标注 preScroll 和 postScroll 的分发路径]

## 滑动卡顿的根因分析

理解 RecyclerView 的缓存体系、预取机制和嵌套滑动之后，分析时要回到一个更实际的问题：当 Perfetto 中出现掉帧，怎么快速定位是哪一层机制出了问题？

在实际工作中，RecyclerView 滑动卡顿的根因通常集中在以下几个方向。

**item 布局过深** 是常见的耗时来源。如果每个 item 的 View 层级超过 4-5 层，measure 和 layout 的时间会明显增加。用 Layout Inspector 检查 item 的 View 树，如果发现深层嵌套的 LinearLayout 或 RelativeLayout，用 ConstraintLayout 替换通常能减少 measure/layout 时间。

**onBindViewHolder 中的 IO 操作** 是另一个高频问题。图片加载的磁盘 IO、数据库查询、甚至 SharedPreferences 的同步读取，都可能在 bind 路径上引入不可预测的延迟。解决方法是将这些操作全部异步化——图片用 Glide/Coil 等库自动异步加载，数据预加载到内存，bind 方法只做轻量的视图更新。

**ItemAnimator 触发的额外布局** 也是常见原因。默认的 `DefaultItemAnimator` 本身就继承自 `SimpleItemAnimator`。当 change animation 开着时，RecyclerView 需要同时保留旧、新两份位置信息来计算过渡，列表高频更新时，这部分布局和动画记录开销会持续叠加。更直接的优化做法有两种：一是对默认动画器调用 `((SimpleItemAnimator) rv.getItemAnimator()).setSupportsChangeAnimations(false)`，先关掉 change animation；二是在页面不需要任何列表动画时直接 `rv.setItemAnimator(null)`。

**图片加载回调触发的 requestLayout** 是一种隐性的性能问题。当图片异步加载完成后，如果在回调中修改了 ImageView 的尺寸（比如 `wrap_content` 导致从占位图切换到真实图片时大小变化），会触发整个 RecyclerView 的重新布局。处理方向是为 ImageView 设置固定宽高，避免占位图和真实图片切换时改变 item 测量结果；如果 Adapter 内容变化不会改变 RecyclerView 自身宽高，再配合 `setHasFixedSize(true)` 减少整表 layout invalidation。

**VSync 时间精度问题** 是一个更隐蔽的根因。这个问题的来源是 Android 列表滑动在计算每帧位移时，使用的不是 VSync 的纳秒时间戳，而是取整后的毫秒值。在 120Hz 设备上（VSync 周期约 8.33ms），±1ms 的取整误差意味着约 12% 的帧间时间差异。这种微小的时间波动传递到 OverScroller 的位移计算后，会导致列表每帧滚动的像素数不均匀。用户在快速滑动时感知到"一顿一顿"的效果，但 Perfetto 的 FrameTimeline 不会标记为 Jank——因为帧在预算时间内完成了，只是步幅不均匀。

这是一种"无掉帧卡顿"，和 §7.1 中讨论的帧率稳定性问题不同。帧率可能稳定在 120fps，但步幅波动仍会让用户感觉不流畅。

[来源: 高爷卡顿知识补充 2026-04-06，VSync 时间取整问题]

## RecyclerView 1.4 与 Adaptive Refresh Rate

RecyclerView 1.4.0 的 release notes 把这项能力写成 `Adaptive refresh rate support`。变化点很具体：RecyclerView 在 `OverScroller` 驱动的 fling 或 smooth scroll 过程中，会在 `ViewFlinger.run()` 里调用 `View.setFrameContentVelocity()`，把当前滚动速度上报给系统。

当前 AndroidX 主线的代码路径也很直接：`ViewFlinger.run()` 在继续滚动时拿 `scroller.getCurrVelocity()`，API 35 及以上通过 `Api35Impl.setFrameContentVelocity(RecyclerView.this, Math.abs(scroller.getCurrVelocity()))` 写入 view。RecyclerView 1.4 做的是速度上报这一步，不负责查询设备是否支持 ARR，也不直接决定系统会切到多少 Hz。

设备能力查询属于平台 `Display` API。`android-16.0.0_r1` 的 `Display.java` 里，`hasArrSupport()`、`getSupportedRefreshRates()` 和 `getSuggestedFrameRate(int)` 都定义在 `android.view.Display` 上。它们回答的是设备支持情况和系统建议值，版本边界应和平台 API 一起写，不要和 RecyclerView 1.4.0 的库版本混成一层。

工程上可以把这两层分开理解：

- RecyclerView 1.4.0：滚动时调用 `View.setFrameContentVelocity()`
- Android 16 `Display` API：查询设备是否支持 ARR，以及系统建议的刷新率区间

这样写，`§2.18` 讲平台能力，`§7.8` 讲 RecyclerView 在滑动场景里怎样把速度信号交给系统，边界就清楚了。

[已验证: AndroidX RecyclerView 1.4.0 release notes（2025-01-15），`RecyclerView.java` `ViewFlinger.run()`，AOSP `android-16.0.0_r1` `View.java` / `Display.java`]

## 在 Perfetto 中分析 RecyclerView 性能

RecyclerView 没有固定的 “RecyclerView track”。这些 slice 出现在触发它们的线程上，最常见是主线程。分析时不要先去找一个不存在的专用 track，而是从卡顿帧所在的主线程 `doFrame` 展开，再看其中有没有 `RV OnLayout`、`RV FullInvalidate`、`RV PartialInvalidate`、`RV Prefetch`、`RV onCreateViewHolder type=...`、`RV onBindViewHolder type=...`。

排查顺序可以按这个次序走：

1. 先在 FrameTimeline 找超预算帧，确认卡顿发生在哪几个 `doFrame`
2. 展开对应主线程 slice，判断大头是在 `RV OnLayout`、`RV FullInvalidate` 还是 `RV PartialInvalidate`
3. 如果外层布局不长，再看同一帧里有没有 `RV onCreateViewHolder type=...` 或 `RV onBindViewHolder type=...`
4. 再看 `RV Prefetch` / `RV Nested Prefetch`，确认预取是在帮忙，还是因为预算不够提前退出

这条 SQL 可以把常见 RecyclerView slice 拉出来：

```sql
SELECT
  s.name,
  ROUND(s.dur / 1e6, 2) AS dur_ms,
  COALESCE(th.name, 'unknown') AS thread_name
FROM slice s
LEFT JOIN thread_track tt ON s.track_id = tt.id
LEFT JOIN thread th ON tt.utid = th.utid
WHERE s.name IN (
    'RV OnLayout',
    'RV FullInvalidate',
    'RV PartialInvalidate',
    'RV Prefetch',
    'RV Nested Prefetch'
)
   OR s.name GLOB 'RV onCreateViewHolder type=0x*'
   OR s.name GLOB 'RV onBindViewHolder type=0x*'
ORDER BY s.dur DESC
LIMIT 50;
```

如果要先看哪一类 slice 最重，再跑一条聚合查询：

```sql
SELECT
  name,
  COUNT(*) AS cnt,
  ROUND(AVG(dur) / 1e6, 2) AS avg_ms,
  ROUND(MAX(dur) / 1e6, 2) AS max_ms
FROM slice
WHERE name IN (
    'RV OnLayout',
    'RV FullInvalidate',
    'RV PartialInvalidate',
    'RV Prefetch',
    'RV Nested Prefetch'
)
   OR name GLOB 'RV onCreateViewHolder type=0x*'
   OR name GLOB 'RV onBindViewHolder type=0x*'
GROUP BY name
ORDER BY max_ms DESC;
```

有两个判断点很常用。`RV OnLayout` 很长，通常说明布局、measure 或动画准备在吃时间。`RV Prefetch` 很明显，但后面没有 create/bind，则多半是预算检查提前结束了预取，或者目标 ViewHolder 已经在缓存里。

`dispatchLayoutStep1/2/3` 不会直接出现在 Trace 名字里。看到 `RV FullInvalidate`、`RV PartialInvalidate`、`RV OnLayout` 之后，还要回到上一节的阶段映射去解释它们分别对应哪一段布局流程。

[图：Perfetto 中 RecyclerView 滑动 Trace 的典型截图，标注 `RV OnLayout`、`RV Prefetch`、`RV onBindViewHolder` 的观察顺序]

## 常见问题与误区

**误区：增大 RecycledViewPool 就能解决所有滑动卡顿。** Pool 只解决 inflate 开销，如果瓶颈在 bind（比如 bind 中有 IO 操作），增大 Pool 不会有效果。要先在 Trace 中区分是 create 慢还是 bind 慢。

**误区：`setHasFixedSize(true)` 是万能优化。** 这个设置的判断对象是 RecyclerView 自身尺寸，不是每个 item 是否等高。只要 Adapter 内容变化不会改变 RecyclerView 的测量宽高（例如 RecyclerView 高度固定或 `match_parent`），动态高度 item 也可以使用；如果 RecyclerView 本身是 `wrap_content`，并且新增、删除或内容变化会改变它的测量尺寸，就不该打开。

**误区：`setItemViewCacheSize(0)` 总是负优化。** 在某些场景下（比如 item 数据频繁更新，CachedViews 中的 ViewHolder 经常 invalid），把缓存大小设为 0 反而可以避免无效的缓存查找，直接走 Pool 的 rebind 流程。但这属于针对性优化，不应该作为默认策略。

**误区：高刷新率设备上 RecyclerView 不需要优化。** 高刷新率设备的帧预算更短（120Hz 下只有 8.33ms），任何在 60Hz 下勉强达标的操作在高刷新率下都可能超时。RecyclerView 的优化在高刷新率设备上反而更重要。


## 扩展

### 自定义 LayoutManager 性能

不同 LayoutManager 的布局策略差异会直接影响滑动帧时间。LinearLayoutManager 的布局是线性的，每个 item 的位置只依赖前一个 item，可以增量计算；GridLayoutManager 还要处理行列关系；StaggeredGridLayoutManager 需要处理不同高度 item 的 gap，布局回溯成本更高。

自定义 LayoutManager 时，主要目标是减少 `fill()` 中的重复计算。`onLayoutChildren()` 应尽量复用当前锚点和已有子 View 信息，避免每次从头扫描 Adapter。`setInitialPrefetchItemCount()` 的取值也要贴合布局类型：LinearLayoutManager 默认值通常够用，GridLayoutManager 可以从列数乘以 2 起步，再用 `RV Nested Prefetch` 和 create/bind slice 验证。

### ItemDecoration 与 ItemAnimator 性能

`ItemDecoration.getItemOffsets()` 在 measure/layout 期间会被调用。如果这里根据 position 做复杂计算，布局阶段会被拖长。间距规则固定时，把计算结果缓存到 Adapter 数据或 ViewHolder 状态里，避免每帧重复算。

`DefaultItemAnimator` 继承自 `SimpleItemAnimator`。change animation 打开时，RecyclerView 需要同时保存 pre-layout 和 post-layout 信息，还可能短时间保留旧、新两个 ViewHolder。列表高频更新又不需要 change 动画时，可以对默认动画器调用 `((SimpleItemAnimator) rv.getItemAnimator()).setSupportsChangeAnimations(false)`；页面不需要列表动画时，再考虑 `rv.setItemAnimator(null)`。

## 参考资料

- **AndroidX 源码**：`platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/RecyclerView.java`
- **AndroidX 源码**：`platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/GapWorker.java`
- **AndroidX 源码**：`platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/LinearLayoutManager.java`
- **AndroidX 源码**：`platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/DiffUtil.java`
- **AndroidX 源码**：`platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/SimpleItemAnimator.java`
- **AndroidX 源码**：`platform/frameworks/support/+/androidx-main/recyclerview/recyclerview/src/main/java/androidx/recyclerview/widget/DefaultItemAnimator.java`
- **平台源码**：`platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/View.java`
- **平台源码**：`platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/Display.java`
- **官方文档**：[RecyclerView reference](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView)
- **官方文档**：[RecyclerView release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview)
- **官方文档**：[Adaptive Refresh Rate](https://developer.android.com/reference/android/view/View#setFrameContentVelocity())
- **官方文档**：[Android 17 MessageQueue behavior changes](https://developer.android.com/about/versions/17/changes/messagequeue)
- **官方博客**：[Under the hood: Android 17's lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- **内部调研**：`DeepResearch/2026-05-14-android17-deliqueue-recyclerview-prefetch-verification.md`
- **内部调研**：`DeepResearch/2026-05-13-recyclerview-deliqueue-messagequeue-analysis.md`
- **Myers 差分算法**：Eugene W. Myers, "An O(ND) Difference Algorithm and Its Variations", 1986
- **高爷补充素材**：VSync 时间精度与步幅波动（2026-04-06）
