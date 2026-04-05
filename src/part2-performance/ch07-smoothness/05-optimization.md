---
title: "优化策略"
chapter: "7.5"
status: ready-for-review
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-04-01"
last_verified_against: "AOSP android-16.0.0_r1, Android 官方文档"
confidence: medium
sources:
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
  - type: official
    path: "developer.android.com/topic/performance/recycler-view"
  - type: official
    path: "developer.android.com/develop/ui/compose/performance"
  - type: official
    path: "developer.android.com/develop/ui/views/layout/constraint-layout"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewStub.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java (LAYER_TYPE_HARDWARE)"
tags: ['optimization', 'layout', 'RecyclerView', 'Compose', 'overdraw', 'hardware-layer', 'thread', 'Binder']
related_chapters: ["7.1", "7.2", "7.3", "7.4", "2.4", "2.5", "2.7", "2.8", "1.4", "1.5"]
---

reviewed_date: "2026-04-04"
reviewed_by: "openclaw-task6"
rework_date: "2026-04-04"
rework_by: "openclaw-task2b"

# 优化策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 布局优化：减少层级、ConstraintLayout、ViewStub 延迟加载
- 🔹 RecyclerView 优化：预创建 ViewHolder、DiffUtil、SnapHelper 性能考量
- 🔹 渲染优化：减少 overdraw、合理使用 Hardware Layer、Canvas 操作简化
- 🔹 线程优化：耗时操作异步化、Binder 调用优化、合理的线程池配置
- 🔹 Compose 性能优化：减少重组（Recomposition）、stable 标记、remember/derivedStateOf

### 扩展（可选深入）

- 🔸 RenderEffect / Blur 等特效的性能考量
- 🔸 预渲染（Prefetch）与预计算策略
<!-- outline-end -->

## 为什么要单独讲优化策略

在前面的章节里，我们走完了卡顿的定义（7.1）、原因体系（7.2）、分析方法论（7.3）和典型场景分析（7.4）。知道了"卡顿是什么"和"卡顿怎么查"，这一章要解决的问题是：**查到原因之后，怎么改？**

同样是"主线程耗时"，有的是布局层级太深导致 measure 反复执行，有的是 RecyclerView 的 onBindViewHolder 里做了不该做的事，有的是一个看似无害的 Binder 调用正好赶上了系统服务繁忙。每一种原因对应的优化策略都不同，用错方法不仅白费力气，还可能引入新问题。

这一章按照优化的"作用域"来组织——从最底层的布局结构，到列表控件，再到渲染管线和线程模型，最后是 Compose。每一条策略都回答三个问题：**为什么有效**、**在 Trace 中怎么验证效果**、**容易踩什么坑**。



## 布局优化：减少层级、ConstraintLayout、ViewStub 延迟加载

### 为什么布局层级会影响性能

Android 的渲染管线在每一帧都需要执行 measure → layout → draw 三个阶段（参见 [2.4 Choreographer 与渲染流水线](part1-fundamentals/ch02-rendering/04-choreographer.md)）。measure 和 layout 阶段的耗时与 View 树的深度直接相关——measure 是递归的，父 ViewGroup 需要先遍历所有子 View 确定尺寸，然后才能确定自己的尺寸。布局嵌套越深，递归层数越多。

更糟糕的是某些 ViewGroup 需要**多次测量**。`RelativeLayout` 需要先做一遍测量确定各子 View 之间的依赖关系，然后再做一遍确定最终位置。`LinearLayout` 使用 `layout_weight` 时也有类似问题。

[已验证: 官方文档, developer.android.com/develop/ui/views/layout/constraint-layout — ConstraintLayout 通过消除嵌套来减少 measure/layout pass 次数]

### ConstraintLayout：扁平化布局的核心武器

`ConstraintLayout` 的设计目标是**用一层布局替代多层嵌套**。它通过约束系统让每个子 View 直接描述自己相对于其他 View 或父容器的位置关系。

Google 官方基准测试表明，在同等布局效果下，ConstraintLayout 的 measure 阶段比多层嵌套的 RelativeLayout 方案快约 40%。原理是 ConstraintLayout 内部用优化过的约束求解器，只需要一趟遍历就能确定所有子 View 的位置和大小。

[已验证: Google Developers Blog, ConstraintLayout 性能基准测试 — 在复杂布局场景下比 RelativeLayout 快约 40%]

**使用建议：** 对于复杂布局优先用 ConstraintLayout 替代嵌套；在 RecyclerView 的 item 布局中尤其重要——item 布局会被 inflate 和 measure 成百上千次，每减少一层嵌套都会被放大。

### ViewStub：按需加载的利器

`ViewStub` 是一个零大小、不可见、不参与 layout 的占位符。当调用 `inflate()` 或设置 `VISIBLE` 时，它将自己从 View 树中替换为实际的布局。inflate 之前几乎零性能开销；inflate 之后 ViewStub 对象被释放。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/ViewStub.java — inflate() 通过 replaceViewInLayout 替换自身]

**注意事项：** ViewStub 只能 inflate 一次；不支持 `<merge>` 标签；只适合"大概率不显示"的 UI 元素。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — 腾讯 WeSing 使用 ViewStub 对"游客模式"布局做按需加载，减少进房 inflate 耗时]

### 减少层级的其他手段

除了 ConstraintLayout 和 ViewStub，还有几个手段能有效降低布局层级。

`<merge>` 标签是最容易被忽视的一个。当一个布局通过 `<include>` 被嵌入到另一个布局中时，如果被 include 的布局的根元素是 `<merge>`，LayoutInflater 会跳过根节点的创建，直接将子 View 添加到父容器中——不会额外产生一层 ViewGroup 嵌套。在 TabHost、自定义标题栏等场景中，`<merge>` 能省下一到两层不必要的 FrameLayout 或 LinearLayout。

对于子 View 数量在运行时才能确定的场景（如动态标签组、筛选条件列表），动态添加 View 比在 XML 中预定义一堆 `visibility="GONE"` 的 View 要高效得多。`GONE` 状态的 View 虽然不参与 draw，但在 measure 阶段仍然会被遍历；而且它们在 inflate 时就被创建了，白白占用了内存。动态添加则按需创建，数量和时机完全可控。

另外，`layout_weight` 是一个常被忽视的性能陷阱。LinearLayout 在使用 weight 时需要做两次 measure：第一次确定剩余空间，第二次按 weight 比例分配。ConstraintLayout 的 `match_constraint`（0dp + 约束）在效果上等同于 weight，但只需要一次 measure。如果项目中还有使用 weight 的布局，优先用 ConstraintLayout 替代。

在 Perfetto 中，布局层级过深表现为 measure 阶段耗时突增。打开 Trace 后，在主线程（ui_thread）的每个 `doFrame` slice 中可以看到 inflate → measure → layout → draw 的细分。如果某个 doFrame 中 measure 耗时超过 2-3ms，且对应的 View 树 depth 在 Perfetto 的 View hierarchy 信息中超过 10 层，就是布局层级需要优化的信号。[待补充：布局层级过深的 Perfetto Trace 截图]

## RecyclerView 优化：预创建、DiffUtil、预取

RecyclerView 是卡顿的高发地带——滑动场景下每一帧的预算只有 8-16ms，而列表滑动会频繁触发 onBindViewHolder 和 requestLayout。

### onBindViewHolder：最关键的瓶颈

`onBindViewHolder()` 应该只做"轻量级数据绑定"。常见错误：在里边创建对象（`new Paint()`）、做 I/O 操作、做复杂计算、调用 Binder。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — WeSing 发现 onBindViewHolder 中的日志字符串拼接耗时 18ms]

### DiffUtil：精确更新替代全局刷新

`notifyDataSetChanged()` 导致所有可见 ViewHolder 重新 bind。`DiffUtil` 通过比较新旧列表计算最小变更集，只对变化的 item 调用对应的 notify 方法。

```java
public class MessageAdapter extends ListAdapter<Message, MessageViewHolder> {
    protected MessageAdapter() {
        super(new DiffUtil.ItemCallback<Message>() {
            @Override
            public boolean areItemsTheSame(@NonNull Message old, @NonNull Message neu) {
                return old.id == neu.id;
            }
            @Override
            public boolean areContentsTheSame(@NonNull Message old, @NonNull Message neu) {
                return old.equals(neu);
            }
        });
    }
}
```

[已验证: 官方文档, developer.android.com/reference/androidx/recyclerview/widget/DiffUtil — 使用 Eugene W. Myers 差异算法计算最小变更集]

**注意：** DiffUtil 计算默认在调用线程执行，建议使用 `AsyncListDiffer` 或在子线程调用。

### ViewHolder 预取（Prefetch）

RecyclerView 从 25.1.0 开始支持预取——在主线程空闲的间隙提前创建并缓存即将需要的 ViewHolder。对于嵌套 RecyclerView，内层需要设置 `setInitialPrefetchCount(3)` 来配置预取数量。

[已验证: 官方文档, developer.android.com/topic/performance/recycler-view — GapWorker 在主线程空闲时预取]

### RecycledViewPool：跨 RecyclerView 共享 ViewHolder

通过共享 `RecycledViewPool`，一个 RecyclerView 回收的 ViewHolder 可以被另一个复用，减少 inflate 次数。

### SnapHelper 的性能考量

`findSnapView` 和 `calculateDistanceToFinalSnap` 在滑动停止时调用。自定义 SnapHelper 要确保时间复杂度不超过 O(log n)。

[待验证: SnapHelper 在 Android 16 中是否有新的优化]

### RecyclerView 卡顿在 Perfetto 中的定位

在 Perfetto 中排查 RecyclerView 滑动卡顿，关注三个 Track。首先是主线程的 `ui_thread` Track——在 doFrame 的调用栈中搜索 `onBindViewHolder` 或 `onCreateViewHolder`，如果它们的耗时超过 1ms，说明绑定或创建逻辑太重。其次是 `RenderThread` Track——如果主线程的 doFrame 很快完成但 RenderThread 耗时突增，说明问题不在数据绑定而在渲染本身（比如 item 布局过于复杂）。第三是 FrameMetrics 的 `FrameTimeline` Track——持续观察整段滑动过程中的帧时间分布，如果大量帧超过 VSync 周期（120Hz 设备为 8.33ms），且对应的调用栈集中在 RecyclerView 相关方法上，就是列表优化需要重点关注的区域。[待补充：RecyclerView 滑动卡顿的 Perfetto Trace 截图]

## 渲染优化：减少 Overdraw、Hardware Layer、Canvas 简化

### Overdraw：画了又画

检测方式：开发者选项 → "调试 GPU 过度绘制"。无色=绘制 1 次，蓝色=2 次，绿色=3 次，粉色=4 次。

常见优化：移除不透明 Activity 的 Window 背景、使用 clipPath 裁剪、`View.setWillNotDraw(true)` 跳过不需要绘制的 ViewGroup。

详见 [2.8 过度绘制](part1-fundamentals/ch02-rendering/08-overdraw.md)。

### Hardware Layer：动画加速器

Hardware Layer 把 View 渲染成 GPU 纹理，属性动画只操作纹理不需要重新 draw。

```
view.setLayerType(View.LAYER_TYPE_HARDWARE, null);
ObjectAnimator.ofFloat(view, "translationX", 0f, 100f).start();
// 动画结束后关闭
view.setLayerType(View.LAYER_TYPE_NONE, null);
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/View.java — LAYER_TYPE_HARDWARE 在硬件加速开启时生效]

**三个陷阱：** 不要长期开启（占 GPU 内存）；不要对频繁 invalidate 的 View 使用；对简单 View 没意义。详见 [2.7 Hardware Layer](part1-fundamentals/ch02-rendering/07-hardware-layer.md)。

### Canvas 操作简化

- 避免在 onDraw 中创建对象——会产生内存抖动触发 GC
- 使用预格式化对象（TextPaint、StaticLayout 提前创建）
- 减少 Path 的复杂度

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — onDraw 中创建对象是常见错误，产生内存抖动间接导致卡顿]

### RenderEffect / Blur 等特效的性能考量 🔸

Android 12 的 `RenderEffect` API 模糊效果是性能敏感操作。建议：降低模糊分辨率、缓存模糊结果、Android 13+ 使用 `RenderEffect.createBlurEffect()`。

[待验证: Android 16 中 RenderEffect 是否有新的硬件加速路径]

## 线程优化：耗时操作异步化、Binder 调用、线程池

### 耗时操作异步化的基本原则

**第一，"耗时"的阈值比你想象的低。** 120Hz 设备上一个 VSync 周期只有 8.33ms，扣除渲染固定开销 3-5ms，留给业务逻辑的时间只有 3-5ms。

**第二，Binder 调用的耗时不可预测。** 系统空闲时可能 0.5ms，繁忙时可能 20ms+。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — WeSing 发现主线程解析 JSON 18ms、初始化 SDK 115ms，移到子线程后显著改善卡顿率]

**第三，注意"间接耗时"。** 子线程过多会抢占 CPU 时间片。WeSing 统计：SDK 升级后新增 30 个线程、250 个 fd，卡顿率从 15% 升到 20%。

### Binder 调用优化

Binder 是 Android 进程间通信的核心机制（详见 [1.4 Binder IPC](part1-fundamentals/ch01-architecture/04-binder.md)），但它的耗时极度不可控。系统空闲时一次 Binder 调用可能只要 0.5ms，而系统繁忙时（比如多个 App 同时做 GC、SurfaceFlinger 正在合成、lmkd 在杀进程），同一次调用可能飙升到 20ms 甚至更久。在 120Hz 设备上，20ms 等于两个半 VSync 周期——一次 Binder 调用就能制造一个肉眼可见的卡顿。

针对 Binder 调用，有几条实践证明有效的优化策略。首先是**缓存系统服务查询结果**。`PackageManager.getPackageInfo()`、`ActivityManager.getProcessMemoryState()` 这类调用每次都会走 Binder，如果在启动路径或滑动路径上重复调用，开销会被放大。正确的做法是在 App 启动时查一次，把结果缓存在内存中。其次是**绝不把 Binder 调用放在渲染路径上**。滑动手势的 onScroll 回调、动画的 onAnimationUpdate、RecyclerView 的 onBind——这些地方哪怕一次 1ms 的 Binder 调用，在高速滑动时也会被连续触发，累积效果非常可观。如果确实需要在滑动过程中获取数据，应该在子线程提前获取并缓存，主线程只做轻量的数据绑定。

对于批量数据操作，使用 `ContentProviderOperation` 替代逐条调用。每次 `ContentResolver.insert()` 或 `update()` 都是一次完整的 Binder 往返（marshalling → 驱动传输 → unmarshalling → 执行 → 返回），批量操作能把多次往返压缩为一次。

[已验证: 官方文档, developer.android.com/reference/android/content/ContentProvider — 批量操作减少跨进程调用次数]

最后，对于不需要返回值的场景（如日志上报、状态通知），使用 AIDL 的 `oneway` 关键字让调用异步化——调用方不会阻塞等待对端执行完毕，而是直接返回。

在 Perfetto 中观察 Binder 调用耗时，可以在主线程的 Trace 中搜索 `binder_transaction` 事件。如果发现某个 `binder_transaction` 的持续时间超过 5ms，就需要关注它发生在什么上下文中——如果是在 doFrame 或 dispatchTouchEvent 的调用栈中，那就是需要优化的目标。另外，Perfetto 的 `binder` Track 会显示所有进程的 Binder 活动，可以用来判断"系统繁忙"是否是外部因素导致的。[待补充：Binder 调用耗时的 Perfetto Trace 截图]
### 合理的线程池配置

线程池配置不当是"优化了主线程，卡顿反而更严重"的典型原因。核心问题是：子线程和主线程共享同一组 CPU 核心，子线程越多，主线程能分到的时间片越少。

控制线程池的并发数是最基本的一条。CPU 密集型任务的线程数不应超过 CPU 核心数（可通过 `Runtime.availableProcessors()` 获取），I/O 密集型任务可以适当多一些，但也不建议超过核心数的两倍。很多 App 的做法是按功能模块各建一个线程池，加上第三方 SDK 自带的线程池，加起来可能有三四十个线程同时在跑。这种情况下 CPU 调度器需要在大量线程之间频繁切换，上下文切换的开销本身就成了性能瓶颈。

给线程池中的线程起有意义的名字，看起来是个小事，但在排查问题时价值巨大。Perfetto 中每个线程都按名字显示，如果看到的是 `pool-1-thread-3` 这种默认命名，很难判断它属于哪个功能模块。通过 `ThreadFactory` 给线程命名为 `ImageLoader-#1`、`DataSync-#2` 之后，在 Perfetto 中一眼就能定位到是哪个模块的线程在抢 CPU。WeSing 团队就曾通过这种方式快速定位到 SDK 升级后新增的 30 个未命名线程。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — WeSing 发现 SDK 升级后新增 30 个未命名线程]

另一个容易被忽视的点是生命周期管理。Activity 或 Fragment 销毁时，如果线程池中还有对应的任务在执行，这些任务可能持有 Activity 的引用导致内存泄漏，或者任务完成后尝试更新已销毁的 UI 导致崩溃。正确的做法是在 `onDestroy()` 中取消或中断相关任务。可以通过 `adb shell ps -T | grep <package>` 快速监控 App 的线程数量是否正常。

在 Perfetto 中，线程池问题通常表现为：在主线程的 doFrame 耗时突增的同时，同进程的其他线程（特别是 CPU 密集型线程）也占用了大量 CPU 时间。打开 Perfetto 的 CPU Track，观察主线程所在进程的所有线程的 CPU 使用分布——如果发现在掉帧发生的时间段，多个子线程同时处于 Running 状态，而主线程反而处于 Runnable 等待调度，就是线程池配置需要调整的信号。[待补充：线程竞争导致主线程调度的 Perfetto Trace 截图]

### 任务拆分与延迟初始化

- **任务拆解**：将一个大任务拆成多个小 Message，用 `Handler.post()` 分发到不同帧处理
- **优先级控制**：UI 更新任务用 `Handler.postAtFrontOfQueue()` 确保尽快执行
- **延迟初始化**：`by lazy(LazyThreadSafetyMode.NONE)` 减少首帧负担

```kotlin
val config by lazy(LazyThreadSafetyMode.NONE) { parseConfig() }
```

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — postAtFrontOfQueue 替代 post 解决了任务拆分后的 UI 刷新时序问题]

## Compose 性能优化：减少重组、stable 标记、remember/derivedStateOf

Compose 的声明式编程模型引入了新的性能陷阱——**不必要的 Recomposition**。传统 View 系统的优化核心是减少 measure/layout/draw 开销，Compose 多了一个 **composition** 阶段。

### 减少 Recomposition 的核心策略

**策略一：使用 Stable 类型让 Compose 跳过重组**

Compose 判断所有参数都是 stable 且值没变化时，就跳过重组。关键陷阱：标准 Kotlin 集合（List、Map、Set）默认是 unstable 的。

```kotlin
// ❌ 不稳定
@Composable
fun ItemList(items: List<String>) { ... }

// ✅ 标注 @Immutable 或使用 kotlinx.collections.immutable
@Immutable
data class ItemListState(val items: List<String>)

@Composable
fun ItemList(state: ItemListState) { ... }
```

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — Stable 类型和 Strong Skipping 模式]

**策略二：remember 和 derivedStateOf 缩小重组范围**

```kotlin
val processed = remember(data) { data.uppercase().trim() }

val showButton by remember {
    derivedStateOf { scrollState.value > threshold }
}
```

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — derivedStateOf 用于延迟读取状态]

**策略三：Lazy 列表中使用稳定的 key**

```kotlin
LazyColumn {
    items(items = messages, key = { it.id }) { message ->
        MessageRow(message)
    }
}
```

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — Lazy 列表的 key 优化]

**策略四：避免 Backward Writes** — 永远不要在 Composition 阶段修改 State，在事件回调中修改。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance — 避免在 composition 中修改 state]

**策略五：Modifier 顺序** — 将昂贵的 Modifier（如 `graphicsLayer`）放在链的最后。

### Compose 优化的验证

使用 Android Studio 的 **Layout Inspector** 观察每个 Composable 的重组次数。使用 `ComposeCompilerMetrics` 和 `Macrobenchmark` 进行自动化测试。

## 预渲染与预计算策略 🔸

"预"字诀的核心思想是：利用当前帧的空闲时间，提前为接下来的帧做好准备工作。它的有效性基于一个前提——用户操作（滑动、切换页面）在时间上有连续性和可预测性，我们大致知道接下来需要什么数据、需要渲染什么 UI，所以可以提前准备，避免等到真正需要时才仓促计算。

RecyclerView 的 GapWorker 就是系统级预取的典型实现。在主线程处理完当前帧之后、下一个 VSync 信号到来之前的空闲间隙，GapWorker 会根据滑动方向和速度，预测即将进入屏幕的 item，提前创建并绑定对应的 ViewHolder。这样当 item 真正出现在屏幕上时，onBindViewHolder 已经执行完了，省去了创建和绑定的耗时。嵌套 RecyclerView（如 ViewPager2 中的水平列表）需要额外配置 `setInitialPrefetchCount(3)`，让 GapWorker 知道内层列表需要预取多少个 item。

Compose 的 LazyColumn 内部也实现了类似的预取机制——当用户在滑动列表时，Compose 会在帧间空闲时间提前 compose 和 measure 即将进入视口的 item。加上 Compose 1.10（BOM 2025.12.00）引入的 pausable composition，如果在预取过程中发现当前帧时间即将用完，可以暂停 composition 并在下一帧恢复，而不是强行完成导致掉帧。

[来源: 预渲染和预计算在 RecyclerView 和 Compose 中都有系统级支持。来源: 官方文档 + web_search]

图片预加载是另一个重要的预取场景。Coil 和 Glide 都提供了预加载 API（如 Coil 的 `ImageRequest.Builder` 配合 `enqueue()`，Glide 的 `preload()`）。在用户还没滑动到图片位置时就在后台加载并缓存，滑动到时直接从内存缓存中读取，不再经历网络请求和解码的耗时。

预计算布局则是把渲染阶段的计算工作前置到后台线程。最常见的场景是文本排版——`StaticLayout` 的构建（特别是长文本和多行 Spannable）可以在后台线程提前完成，主线程的 `onDraw()` 只需要调用 `staticLayout.draw(canvas)` 即可。类似的思路也适用于复杂的 Path 计算、矩阵运算等。关键原则是：**所有可以在后台线程完成的纯计算工作，都不应该留到主线程的渲染路径上**。

## 常见误区

1. **"优化就是减少代码量"**：更多时候是关于"在正确的时间做正确的事"
2. **"Compose 天生比 View 快"**：BOM 2025.12.00 官方声明 Compose 性能已与 View 系统对等（内部滑动基准测试 jank 降至 0.2%），但使用不当反而可以更慢 [已确认: BOM 2025.12.00 为 2025 年 12 月稳定版，含 Compose 1.10 + Material 3 1.4；性能对等声明来源为 Google Android Developers Blog]
3. **"Hardware Layer 神器"**：只在属性动画场景有效，滥用反而增加开销
4. **"onBindViewHolder 调用越少越好"**：应关注单次调用的耗时，不是次数
5. **"子线程不影响主线程"**：大量子线程抢 CPU 时间片、增内存压力、导致更频繁 GC

## 参考资料

- [RecyclerView 官方指南](https://developer.android.com/topic/performance/recycler-view)
- [Jetpack Compose Performance](https://developer.android.com/develop/ui/compose/performance)
- [ConstraintLayout 性能优化](https://developer.android.com/develop/ui/views/layout/constraint-layout)
- [ViewStub 文档](https://developer.android.com/reference/android/view/ViewStub)
- [Hardware Layer](https://developer.android.com/reference/android/view/View#LAYER_TYPE_HARDWARE) — 另见本书 [2.7 Hardware Layer](part1-fundamentals/ch02-rendering/07-hardware-layer.md)
- AOSP：`ViewStub.java`、`View.java`、`Choreographer.java`
- 腾讯 WeSing：[Android 深入卡顿分析与实践](https://mp.weixin.qq.com/s?__biz=MzI1NjEwMTM4OA==&mid=2651236641)
- [Compose BOM 2025.12.00](https://developer.android.com/develop/ui/compose/bom)
- [ConstraintLayout 性能基准测试](https://android-developers.googleblog.com/constraintlayout-performance)
- [DiffUtil 官方文档](https://developer.android.com/reference/androidx/recyclerview/widget/DiffUtil)
- [RecyclerView Prefetch](https://medium.com/google-developers/recyclerview-prefetch-c64ad0d3e324)
- [Compose Strong Skipping](https://medium.com/androiddevelopers/strong-skipping-in-compose-984c37e8e8be)
- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [Compose 性能 Codelab](https://developer.android.com/codelabs/compose-performance)
