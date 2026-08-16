---
title: RecyclerView 列表滑动性能深度优化
chapter: '7.8'
section: '7.8'
status: finalized
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
last_verified: '2026-06-29'
last_verified_against: AndroidX RecyclerView 1.4.0 sources.jar + Android Developers MessageQueue docs + RecyclerView 1.4.0 release notes + AOSP android-17.0.0_r1 View/Display
confidence: medium
sources:
- type: androidx
  path: androidx.recyclerview:recyclerview:1.4.0 sources.jar (RecyclerView.java)
- type: androidx
  path: androidx.recyclerview:recyclerview:1.4.0 sources.jar (GapWorker.java)
- type: androidx
  path: androidx.recyclerview:recyclerview:1.4.0 sources.jar (LinearLayoutManager.java)
- type: androidx
  path: androidx.recyclerview:recyclerview:1.4.0 sources.jar (DiffUtil.java)
- type: aosp
  path: platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java
- type: aosp
  path: platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Display.java
- type: official
  path: https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/recyclerview
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 7.8 RecyclerView 列表滑动性能深度优化

列表滑动是 Android 用户最高频的操作之一，也是流畅性问题集中的场景。RecyclerView 作为列表渲染的标准组件，内部涉及缓存复用、预取、嵌套滑动和增量更新，这几层机制都会直接影响滑动帧耗时。

Perfetto 中常见的问题集中在布局、bind（数据绑定）、缓存与预取阶段。

平台版本以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核版本以 `android17-6.18-2026-06_r6` 为准。RecyclerView 独立于 Android 平台发布，组件行为按稳定版 `androidx.recyclerview:recyclerview:1.4.0` sources jar（源码包）核对。平台标签用于 `View`、`Display`、MessageQueue 和 FrameTimeline；内核标签只用于解释线程调度与 fence（同步栅栏）等系统现象，不能替代 AndroidX 版本。

## RecyclerView 的布局流程

RecyclerView 1.4.0 的完整 `dispatchLayout()` 由三个步骤组织。它们属于由内部状态控制的处理流程，Perfetto 中没有同名的 slice（时间区间）：

| 内部步骤 | 源码职责 | Trace 解读 |
|---|---|---|
| `dispatchLayoutStep1()` | 处理 Adapter（列表数据适配器）更新和动画标记，记录 pre-layout（更新前布局）信息；启用 predictive animation（预测动画）时还会执行一次 pre-layout | 位于包含本次 `dispatchLayout()` 的外层 slice 内，没有单独名称 |
| `dispatchLayoutStep2()` | 消费更新，进入最终状态的 `LayoutManager.onLayoutChildren()`；非 EXACT（父容器给出精确尺寸）测量等情形可能执行多次 | 在 `RV OnLayout`、`RV FullInvalidate` 或 `RV PartialInvalidate` 的调用栈中寻找 `onLayoutChildren()`、measure、layout、create 和 bind |
| `dispatchLayoutStep3()` | 记录 post-layout（更新后布局）信息，匹配并启动 item animation（条目动画），回收 scrap（布局期间暂存的 holder），恢复焦点并清理状态 | 仍在外层布局 slice 内，不能用一条后续动画 slice 代表整个 step3 |

`RV OnLayout` 来自 View 系统对 `RecyclerView.onLayout()` 的调用。`RV FullInvalidate` 和 `RV PartialInvalidate` 来自 `consumePendingUpdateOperations()`：

- 首次布局未完成、数据集整体失效，或存在 add/remove/move 等结构更新时，常进入 `RV FullInvalidate` 并调用 `dispatchLayout()`；
- 只有 `UPDATE` 类型的局部更新时，`RV PartialInvalidate` 会先让 `AdapterHelper` 预处理；可见 holder（持有列表项 View 的对象）受影响时才调用 `dispatchLayout()`，否则只消费 postponed updates（延后处理的更新）；
- 这些外层 slice 可能包含 step1、step2、step3，不能把 `RV FullInvalidate` 直接标成 step1。

AutoMeasure（RecyclerView 自动测量）还会改变观察位置。宽高不都是 `EXACT` 时，`onMeasure()` 可以先执行 step1/step2；`onLayout()` 随后可能只补 step3，或因尺寸变化再次执行 step2。若 `LayoutManager.shouldMeasureTwice()` 返回 `true`，step2 会在测量中再执行一次。看到单个 `RV OnLayout` 很短，不足以证明列表布局成本低，还要检查同一帧的 measure 调用栈。

分析时先从 FrameTimeline（逐帧时间线）选定慢帧，再展开主线程中的 `RV Scroll`、更新 slice 和 `RV OnLayout`。调用栈可以区分 Adapter 更新、`onLayoutChildren()`、item create/bind（创建/绑定）、子 View 测量与动画信息记录；没有调用栈的 trace 只能给出候选阶段。

## ViewHolder 回收复用的四级缓存

“四级缓存”适合入门记忆，但它省略了 changed scrap（发生变化的暂存 holder）、hidden child（被隐藏的子 View）、stable ID（稳定条目标识）查找和 holder 校验。`tryGetViewHolderForPositionByDeadline()` 的主要查找顺序更接近下面这张表：

| 来源 | 何时参与 | 取得后是否可能 bind |
|---|---|---|
| Changed scrap | pre-layout 期间按 position（条目位置）或 stable ID 查找变化前的 holder | 由 pre-layout 状态与 holder 标记决定 |
| Attached scrap / hidden child / CachedViews | 先按 position 查找并校验 type/ID（视图类型/条目标识） | 有效且未标记 update/invalid（待更新/无效）时可直接复用；scrap 也允许被 rebound（重新绑定） |
| Stable-ID 二次查找 | Adapter 开启 stable IDs 时，按 ID 与 viewType 查 scrap/cache | holder 状态要求更新时仍会 bind |
| `ViewCacheExtension` | 应用显式提供扩展时 | 由返回 holder 状态决定 |
| `RecycledViewPool` | 前面均未取得兼容 holder | `resetInternal()` 后通常需要 bind |
| 新建 holder | Pool 也未找到可用 holder，且 deadline（截止时间）允许 | create 后继续 bind |

Attached scrap 是布局期间暂时分离、但在语义上仍属于父 RecyclerView 的 holder 集合。源码注释明确允许它被复用或重新绑定，因此“scrap 一定不 bind”不成立。Change animation（变更动画）还会使用独立的 changed scrap。

CachedViews 的请求上限默认是 2，但实际的 `mViewCacheMax` 等于请求值加上 LayoutManager 观察到的预取数量。缓存中的 holder 会保留绑定信息和 position；一旦带有 update、invalid、removed（待更新、无效、已移除）等标记，就可能不再进入该缓存，或在取出后被重新校验。`setItemViewCacheSize()` 应根据回滑场景中的 create/bind、内存与 GC（垃圾回收）对照来决定，不能预设 4～6 为通用值。

RecycledViewPool 默认每个 viewType（视图类型）最多保存 5 个 holder。holder 入池时会重置内部绑定状态，复用后要重新 bind。Pool 可以跨 RecyclerView 共享，但只有 viewType、item View 结构和 bind 规则兼容时才安全。

RecyclerView 1.4.0 的 trace 名称是 `RV onCreateViewHolder type=0x%X` 与 `RV onBindViewHolder type=0x%X`。fling（惯性滑动）中出现 create，说明当前获取路径没有拿到可用 holder；出现 bind 只能证明 holder 需要绑定，无法据此判断它一定来自 Pool。只有 `RV Prefetch` 而没有 create/bind，还可能是目标已经 attached（挂接）、缓存中已有可直接复用的 holder，或预算判断终止了普通预取任务。

## GapWorker 预取机制

RecyclerView 的预取不是 `Choreographer#doFrame()` 的公开阶段。在 RecyclerView 1.4.0 源码中，触发点位于滚动遍历之后：`scrollByInternal()` 和 `ViewFlinger.run()` 在仍有滚动位移时调用 `mGapWorker.postFromTraversal()`。后者把滚动方向与距离写入 `mPrefetchRegistry`，再用 `recyclerView.post(this)` 把 `GapWorker`（预取工作器）作为 Runnable（待执行任务）投递到主线程消息队列。

下面的缩写代码用于展示滚动路径如何登记一次 GapWorker Runnable，并持续更新预取方向：

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

这段调用路径说明两件事。第一，GapWorker 跟随滚动事件调度，不属于 `doFrame()` 的 COMMIT（帧提交）回调。第二，预取请求会先记录滚动方向和距离，执行时再统一排序和处理。

具体要预取哪些 position，由 `LayoutManager.collectAdjacentPrefetchPositions()` 和 `collectInitialPrefetchPositions()` 决定。前者用于滑动中的相邻 item，后者用于嵌套列表首次可见时的 initial prefetch（初始预取）。`setInitialPrefetchItemCount()` 调整的就是这条 initial prefetch 路径。

`GapWorker.run()` 读取可见 RecyclerView 最近的 `getDrawingTime()`，加上 `mFrameIntervalNs` 估算下一帧 deadline，然后按“下一帧是否预计需要”、列表速度和 item 距离为任务排序。普通任务进入 `tryGetViewHolderForPositionByDeadline()` 时，创建前检查 `willCreateInTime()`，绑定前检查 `willBindInTime()`。

下面的源码摘录用于说明 deadline 判断的位置，省略了 holder 查找与状态校验分支：

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

创建和绑定的运行均值保存在 Pool 中对应 viewType 的 `ScrapData`。首次记录采用本次耗时，后续按旧值 3/4、新值 1/4 更新。共享 Pool 也会共享这些耗时估算。

预计下一帧就要使用的 adjacent task（相邻条目任务）会传入 `FOREVER_NS`，强制执行 create/bind，并在启用 tracing（跟踪）时出现 `RV Prefetch forced - needed next frame`。这条分支会跳过上面的 deadline 拒绝判断。其余 task 才受估算 deadline 限制，因此不能假定“GapWorker 在预算不足时总会停止”。

`RV Prefetch` 之后没有 create/bind，可能是目标 position 已经 attached、已有 holder 可以直接复用，或普通 task 被预算拒绝。嵌套列表还会出现 `RV Nested Prefetch`；内层 initial prefetch 使用外层传入的 deadline。

`LinearLayoutManager.setInitialPrefetchItemCount()` 只控制嵌套 RecyclerView 初次进入视口前请求的 item 数。可以从内层列表首次可见的数量开始测试；过大的值会增加 View 创建、bind、缓存和活跃对象。GapWorker 预算也只覆盖 holder 获取、create 和 bind，不覆盖下一帧 item 的 measure/layout。若 prefetch bind 正常，而紧接着的 `RV OnLayout` 很长，应继续检查 item 约束、intrinsic（固有尺寸）测量、图片尺寸变化和自定义布局。

### Android 17 DeliQueue 对预取调度的影响

Android 17 对运行在该平台且 `targetSdkVersion >= 37` 的应用默认启用无锁 MessageQueue 实现 DeliQueue。可调试应用可以使用 `adb shell am compat enable USE_NEW_MESSAGEQUEUE <package>` 提前验证；切换后需要重启进程。

GapWorker 通过 `recyclerView.post(this)` 投递到主线程队列。legacy MessageQueue（旧消息队列）的生产者入队和 Looper（消息循环）取消息会竞争同一个 monitor（对象锁），其他线程持锁时可能阻塞主线程。DeliQueue 把主要的生产者提交改为 CAS（Compare-And-Set，比较并设置）发布，再由 Looper 私有的 heap（按执行时间排序的堆结构）维护时序，从而消除这项对象锁竞争。

DeliQueue 不会清空主线程中排在前面的消息，也不保证 GapWorker 立即运行。`onBindViewHolder()`、item measure/layout、图片解码和 `willCreateInTime()` 算法都没有因此改变。只有 trace 在同一慢帧附近显示 MessageQueue monitor contention（消息队列锁竞争），才有理由把一部分延迟归到旧队列；缺少这项证据时，应继续检查前序 callback（回调）、线程调度和 RecyclerView 自身工作。

DeliQueue 还会影响通过反射读取 `MessageQueue.mMessages` 的监控或测试库：新实现为兼容保留了该字段，但字段始终为 `null`。Android 17 官方迁移要求 Espresso 3.7.0 及以上、Robolectric 4.17 及以上；应用监控应使用 FrameTimeline、JankStats（应用内卡顿监测库）、公开的 Looper 能力与自定义 trace。机制与 A/B（对照实验）方法参见[Android 17 DeliQueue 与 RecyclerView 预取时序](../../part5-app/ch22-rendering-practice/02-recyclerview-practice.md)。

## DiffUtil 与增量更新

`notifyDataSetChanged()` 会让 RecyclerView 把已有 item 视为失效，并进入整表更新路径。stable ID 可以帮助动画与 holder 建立对应关系，但不能恢复精确的插入、删除和内容变化信息。`DiffUtil` 计算新旧列表之间的插入、删除与内容变化，再把结果分发成更细的 Adapter update（适配器更新）。

RecyclerView 1.4.0 的 `DiffUtil.java` 明确给出了复杂度：Myers 差分算法部分使用 O(N) 空间，预期时间为 O(N + D²)，其中 N 是两份列表的总长度，D 是完成转换所需的最少插入/删除次数。开启 move detection（移动检测）后，还有 O(MN) 的第二阶段，其中 M、N 分别是新增项和删除项的数量。数据本来已经按同一稳定键排序，并且业务不需要 move animation（移动动画）时，可以关闭 move detection。

`AsyncListDiffer` 和 `ListAdapter` 把 diff 计算放到后台 executor（执行器），结果回到主线程后才分发更新。连续提交列表时，旧 generation（提交批次）的迟到结果会被丢弃。提交后的列表及参与比较的字段必须在 diff 完成前保持不变，否则比较结果可能与 Adapter 当前数据不一致。

三个回调分别负责不同的判断：

- `areItemsTheSame()` 判断两个条目是否代表同一业务实体，常用稳定 ID；
- `areContentsTheSame()` 判断该实体的可见内容是否一致，比较必须正确且耗时足够短；
- `getChangePayload()` 描述哪些字段可以局部更新。

Payload（变更载荷）是局部绑定的优化提示，不保证一定走局部绑定。多个 update 的 payload 可能合并传入；holder 未 attached 时，payload 也可能被丢弃并执行完整 bind。Adapter 必须确保无 payload 的 bind 能恢复全部 View 状态；局部 bind 则要遍历并合并所有 payload，不能只读取列表中的第一个元素。

分页列表不宜自行实现“只 diff 新一页”并绕过全局的条目身份关系。使用 Paging 3 时，由 `PagingDataAdapter` 管理异步差分、占位项与 generation；普通列表仍可提交新的不可变快照，再用 Macrobenchmark（宏基准测试）验证大列表 diff、主线程 update dispatch（更新分发）和动画成本。

### RecycledViewPool 共享的典型实现

垂直列表的每一行都包含结构相同的水平 RecyclerView 时，共享 Pool 可以让离开屏幕的内层 holder 供下一行复用。Pool 应由页面或 Adapter 持有，并在创建内层 RecyclerView 时设置，无需在每次父 item bind 时重复配置。

调整参数时，应先根据同时可见的父行数、每行可见 item 数和 viewType 分布估算需求，再用 `RV onCreateViewHolder`、内存和 GC 数据校正。`setMaxRecycledViews(viewType, count)` 按 viewType 生效。`setInitialPrefetchItemCount()` 也应接近内层列表首次可见的数量，不能直接复制固定值。

`LinearLayoutManager.setRecycleChildrenOnDetach(true)` 会在 LayoutManager 从窗口分离时回收现有 children（子 View），适合内层 RecyclerView 随父 item 反复 detach（分离）的特定场景。它会改变 holder 生命周期与资源回调时机，使用前要验证图片、播放器、ComposeView 和其他有状态 child 的清理逻辑。

### 共享 Pool 的边界

Pool 按整数 viewType 分桶，也就是按视图类型分别保存 holder；它不知道 Adapter 类或布局资源。两个 Adapter 都返回 viewType 0，但创建的 item View 结构不同，交叉复用会产生错误的 ViewHolder、类型转换异常或残留状态。共享前应保证相同 viewType 对应相同的创建与绑定规则；无法保证时，应使用不同 Pool 或隔离 viewType 的取值空间。

create/bind 运行均值也存放在 Pool 的同一 `ScrapData` 中。不同 Adapter 的 View 结构即使兼容，若创建或绑定成本差异很大，仍会互相影响 GapWorker 的 deadline 估计。

`RecycledViewPool` 的集合操作没有线程同步，RecyclerView 也要求 View 与 Adapter 更新遵守主线程规则。不要在后台线程创建 holder 或并发操作共享 Pool；在 Pool 外部加锁，也无法让 Android View 变成线程安全对象。

## 嵌套滑动的性能影响

RecyclerView 通过 NestedScrollingChild3 协议与父容器协商滚动距离。一次滚动分发可以包含 pre-scroll（子列表滚动前由父容器消费）、子列表消费和 post-scroll（子列表滚动后继续交给父容器）；触摸、fling 与非触摸滚动使用各自的 nested-scroll type（嵌套滚动类型）。

协议调用本身通常只做少量方法分发，不会自动触发 measure/layout。重复布局往往来自父子回调中修改尺寸、Adapter 更新、图片尺寸变化、Insets（系统栏等占用区域）、动画或业务代码调用 `requestLayout()`。trace 中出现多次 layout 后，还要沿调用栈找到发起者，不能只凭页面存在嵌套滑动就作出归因。

嵌套 RecyclerView 的主要成本通常来自两套 holder、布局、预取和状态恢复。可以分别验证共享兼容 Pool、设置合理的 initial prefetch，以及固定内层 viewport（视口）尺寸。关闭 overscroll（越界滚动效果）只会改变边缘反馈与少量绘制，不能作为通用的列表优化。

## 滑动卡顿的根因分析

同样的“列表滑不动”可以来自不同阶段。优化动作应跟随证据：

| 证据 | 常见原因 | 修正方向 |
|---|---|---|
| `RV onCreateViewHolder` 长或密集 | inflate（创建布局）复杂、viewType 划分过细、Pool 不兼容、动画阻止回收 | 简化创建、检查回收规则、验证 Pool 容量与共享条件 |
| `RV onBindViewHolder` 长 | 同步 I/O、数据转换、文本处理、图片请求初始化、全量 bind | 预计算数据、移出同步 I/O、使用正确 payload、取消旧异步请求 |
| `RV OnLayout` 或 measure 长 | item 约束复杂、尺寸反复变化、AutoMeasure、predictive animation | 查调用栈与测量次数，稳定尺寸，简化证据指向的耗时部分 |
| 更新 slice 长 | 更新批次过大、`notifyDataSetChanged()`、大量 animation 记录 | 用 diff/范围更新，合并批次，评估动画价值 |
| `RV Prefetch forced` 长 | 下一帧所需 item create/bind 超出空闲区间 | 降低 item 准备成本；不要依赖 deadline 自动中止任务 |
| App 帧正常、DisplayFrame 异常 | RenderThread、GPU、SurfaceFlinger、HWC（Hardware Composer，硬件合成器）或 present（呈现） | 转入完整渲染过程分析 |

布局层级数量没有统一的“超过 4～5 层就慢”阈值。一个简单的嵌套 ViewGroup 可能成本很低，单层自定义 View 也可能在测量或绘制中做大量工作。ConstraintLayout 也不能无条件替换 LinearLayout。应根据目标 item 的 measure/layout slice、调用次数和 Macrobenchmark 结果决定是否调整结构。

bind 应只执行当前 holder 必需的同步工作。数据库、磁盘和网络访问不能阻塞主线程。图片库虽然异步，但发起请求、切换占位内容和更新回调仍会占用主线程时间。复用时要取消旧请求，或使用能识别 View 生命周期的加载 API，避免迟到结果写入已经绑定到其他 position 的 holder。

高频 change animation 会记录 pre/post layout 状态，并可能同时保留新旧 holder。只想保留插入、删除和移动动画时，可以对 `SimpleItemAnimator` 关闭 change animation；只有页面不需要任何 item animation 时，才应把动画器设置为 `null`。两种改法都会改变交互反馈，需要结合产品行为验证。

图片或异步内容回调若改变 item 尺寸，会触发新的测量和布局。固定可以预知的宽高，或使用稳定的 aspect ratio（宽高比），可以减少尺寸抖动。`setHasFixedSize(true)` 表示 Adapter 内容变化不会改变 RecyclerView 自身的测量尺寸，不表示 item 等高；RecyclerView 为 `wrap_content` 且内容变化会改变自身尺寸时，不应开启该设置。

用户仍可能感到“帧都按期但运动不稳”。这时要按时间核对输入采样、`OverScroller` 位移、刷新率切换、每帧滚动距离和 present 间隔。仅凭 `getDrawingTime()` 或 `OverScroller` 使用毫秒时间，无法推导出固定的 ±1 ms 抖动比例；还需要通过实验排除调度、输入与显示节拍的影响。

## RecyclerView 1.4 与 Adaptive Refresh Rate

RecyclerView 1.4.0 的 release notes（发布说明）把这项能力称为 `Adaptive refresh rate support`（自适应刷新率支持，简称 ARR）。`ViewFlinger.run()` 在 API 35 及以上读取 `OverScroller.getCurrVelocity()`，调用 `View.setFrameContentVelocity(abs(velocity))`。该值的单位是 pixels/second（像素/秒），View 会在本次绘制后重置该值，因此 RecyclerView 会在滚动帧中持续上报。

组件与平台各自负责一层：

- RecyclerView 1.4.0：滚动时调用 `View.setFrameContentVelocity()`；
- Android 17 View/HWUI（Android 硬件加速 UI 渲染管线）：把速度随帧提交给窗口渲染信息；
- Android 17 Display 与显示策略：结合设备能力、其他刷新率请求和系统策略选择刷新行为。

速度上报并不是刷新率命令。RecyclerView 不查询设备是否支持 ARR，也不指定切换到多少 Hz。Android 17 的 `Display.hasArrSupport()`、`getSupportedRefreshRates()` 与 `getSuggestedFrameRate(int)` 属于平台能力查询。刷新率选择及 Perfetto 证据参见[可变刷新率与帧率选择](../ch18-rendering-pipelines/18-variable-refresh-rate.md)。

## 在 Perfetto 中分析 RecyclerView 性能

RecyclerView 没有固定的 “RecyclerView track（轨道）”。slice 会出现在执行对应代码的线程上，常见位置是主线程。应从 FrameTimeline 的目标慢帧展开 App 主线程，再查找 `RV Scroll`、布局、更新、预取、create 和 bind。

排查顺序可以按这个次序走：

1. 在 FrameTimeline 中找到超过截止时间的 App SurfaceFrame（应用 Surface 的帧记录），并定位对应的主线程帧。
2. 展开 `RV Scroll`、`RV OnLayout`、`RV FullInvalidate` 与 `RV PartialInvalidate`。
3. 检查同一区间的 create/bind，按 viewType 汇总高分位耗时。
4. 检查普通、forced（强制）与 nested（嵌套）prefetch；结合前后帧判断预取工作是否直接影响该帧按时完成。
5. App 侧按期时，继续查看 RenderThread、GPU、SurfaceFlinger DisplayFrame（整屏显示帧记录）与 present。

下面的 SQL 用于列出常见的 RecyclerView slice：

```sql
SELECT
  s.name,
  ROUND(s.dur / 1e6, 2) AS dur_ms,
  COALESCE(th.name, 'unknown') AS thread_name
FROM slice s
LEFT JOIN thread_track tt ON s.track_id = tt.id
LEFT JOIN thread th ON tt.utid = th.utid
WHERE s.name IN (
    'RV Scroll',
    'RV OnLayout',
    'RV FullInvalidate',
    'RV PartialInvalidate',
    'RV Prefetch',
    'RV Prefetch forced - needed next frame',
    'RV Nested Prefetch',
    'RV Nested Prefetch forced - needed next frame'
)
   OR s.name GLOB 'RV onCreateViewHolder type=0x*'
   OR s.name GLOB 'RV onBindViewHolder type=0x*'
ORDER BY s.dur DESC
LIMIT 50;
```

结果用于按单次 duration（持续时间）筛选候选 slice；查询没有自动限定某个慢帧，仍要回到 Perfetto 界面中按时间范围核对。

下面的聚合查询用于比较各类 RecyclerView slice 的数量、平均值和最大值：

```sql
SELECT
  name,
  COUNT(*) AS cnt,
  ROUND(AVG(dur) / 1e6, 2) AS avg_ms,
  ROUND(MAX(dur) / 1e6, 2) AS max_ms
FROM slice
WHERE name IN (
    'RV Scroll',
    'RV OnLayout',
    'RV FullInvalidate',
    'RV PartialInvalidate',
    'RV Prefetch',
    'RV Prefetch forced - needed next frame',
    'RV Nested Prefetch',
    'RV Nested Prefetch forced - needed next frame'
)
   OR name GLOB 'RV onCreateViewHolder type=0x*'
   OR name GLOB 'RV onBindViewHolder type=0x*'
GROUP BY name
ORDER BY max_ms DESC;
```

查询结果只用于筛选候选项。`RV OnLayout` 很长时，再用调用栈区分布局、bind 与动画记录；`RV Prefetch` 没有 create/bind 时，检查 attached 状态、缓存中是否已有 holder，以及预算判断；forced prefetch 很长时，检查它是否与目标帧在时间上重叠。

`dispatchLayoutStep1/2/3` 不会直接出现在 Trace 名称中。看到 `RV FullInvalidate`、`RV PartialInvalidate`、`RV OnLayout` 后，还要根据上一节的阶段对应关系，判断它们分别覆盖了哪一段布局流程。

## 常见问题与误区

**误区：增大 RecycledViewPool 就能解决所有滑动卡顿。** Pool 主要减少 holder 创建，复用后仍要 bind，也无法降低 measure/layout、图片解码和 GPU 成本。应先根据 create、bind、layout 与绘制证据判断问题发生在哪个阶段。

**误区：`setHasFixedSize(true)` 是万能优化。** 这个设置的判断对象是 RecyclerView 自身尺寸，不是每个 item 是否等高。只要 Adapter 内容变化不会改变 RecyclerView 的测量宽高（例如 RecyclerView 高度固定或 `match_parent`），动态高度 item 也可以使用；如果 RecyclerView 本身是 `wrap_content`，并且新增、删除或内容变化会改变它的测量尺寸，就不该打开。

**误区：`setItemViewCacheSize(0)` 一定更省资源。** 设为 0 会让离屏 holder 更快进入 Pool，减少保留已绑定的 holder，却可能增加回滑时的 bind。它适合进行有指标的 A/B（对照实验），不能作为默认优化。

**误区：120 Hz 永远只有 8.33 ms，ARR 可以自动补救慢帧。** 当前帧预算应读取 expected FrameTimeline（预期帧时间线）与刷新模式。ARR 可以改变目标节拍，无法让已经错过 deadline 的工作按期完成。


## 扩展

### 自定义 LayoutManager 性能

LinearLayoutManager、GridLayoutManager 与 StaggeredGridLayoutManager 的 anchor（布局起点）、span（跨列范围）、gap（间隙）和回收策略不同，成本还受 item 尺寸、数据变化和动画影响，不能只按类名排列性能高低。

自定义 LayoutManager 要正确处理 Adapter 更新、pre-layout、焦点、无障碍、滚动边界和回收规则。`onLayoutChildren()` 与滚动 fill（填充可见区域）路径应避免从头扫描全部数据，也不能复用已经失效的 position。prefetch 的位置和距离应根据布局几何计算；嵌套 initial prefetch 数量按首次可见 item 测量，再用 forced/nested prefetch 与内存数据验证。

### ItemDecoration 与 ItemAnimator 性能

`ItemDecoration.getItemOffsets()` 在布局计算中被调用，`onDraw()` / `onDrawOver()` 则会进入绘制阶段。这些方法应保持耗时较短，并正确处理 Adapter position 变化；复杂 path、对象分配或扫描整份列表会分别增加布局或绘制成本。缓存必须使用稳定输入作为 key，避免位置移动后继续使用旧结果。

`DefaultItemAnimator` 继承自 `SimpleItemAnimator`。change animation 开启时，RecyclerView 需要同时保存 pre-layout 和 post-layout 信息，还可能短时间保留旧、新两个 ViewHolder。列表高频更新且不需要 change 动画时，可以对默认动画器调用 `((SimpleItemAnimator) rv.getItemAnimator()).setSupportsChangeAnimations(false)`；页面不需要任何列表动画时，再考虑 `rv.setItemAnimator(null)`。

## 相关章节

- [卡顿定义与 FrameTimeline](01-jank-definition.md)
- [卡顿分析方法论](03-jank-methodology.md)
- [Jetpack Compose 性能优化](07-compose-performance.md)
- [可变刷新率与帧率选择](../ch18-rendering-pipelines/18-variable-refresh-rate.md)
- [Android 17 DeliQueue 与 RecyclerView 预取时序](../../part5-app/ch22-rendering-practice/02-recyclerview-practice.md)

## 参考资料

- **AndroidX 源码**：[RecyclerView 1.4.0 sources jar](https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar)
- **平台源码**：[Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)
- **平台源码**：[Android 17 `Display.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)
- **官方文档**：[RecyclerView reference](https://developer.android.com/reference/androidx/recyclerview/widget/RecyclerView)
- **官方文档**：[RecyclerView release notes](https://developer.android.com/jetpack/androidx/releases/recyclerview)
- **官方文档**：[DiffUtil reference](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)
- **官方文档**：[PagingDataAdapter reference](https://developer.android.com/reference/androidx/paging/PagingDataAdapter)
- **官方文档**：[Adaptive Refresh Rate](https://developer.android.com/reference/android/view/View#setFrameContentVelocity%28float%29)
- **官方文档**：[Android 17 MessageQueue behavior changes](https://developer.android.com/about/versions/17/changes/messagequeue)
- **官方博客**：[Under the hood: Android 17's lock-free MessageQueue](https://developer.android.com/blog/posts/under-the-hood-android-17-lock-free-message-queue)
- **官方文档**：[Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- **Myers 差分算法**：Eugene W. Myers, "An O(ND) Difference Algorithm and Its Variations", 1986
