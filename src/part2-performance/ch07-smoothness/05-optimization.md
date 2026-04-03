---
title: "优化策略"
chapter: "7.5"
status: reviewed
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

reviewed_date: "2026-04-04"
reviewed_by: "openclaw-task6"---

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

[需补充素材: 开头承诺了"在Trace中怎么验证效果"，但布局优化、RecyclerView优化、线程优化三个主要段落均缺少具体的Perfetto track/counter定位方法。建议补充：布局层级过深在Trace中的表现（measure耗时突增）、RecyclerView滑动卡顿的Trace特征、Binder调用耗时的观察方法。]

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

[需重写: 此段落使用纯列表格式，违反 writing-guide.md 叙述优先规范。应将三条建议融入连贯段落，解释每条手段为什么有效、在什么场景适用。]

- **`<merge>` 标签**：作为被 include 的子布局根元素时不生成额外的 ViewGroup
- **动态添加 View**：对于数量不固定的子 View，用代码动态添加比预定义一堆 `GONE` 的 View 更高效
- **避免 `layout_weight`**：用 ConstraintLayout 的 `match_constraint` 替代

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

[需重写: 此段落使用纯列表格式，违反叙述规范。应将各条优化策略以“为什么→怎么做→在Trace中怎么看”的叙述逻辑串联。]

- **缓存系统服务查询结果**：`PackageManager.getPackageInfo()` 只需查一次
- **避免在渲染路径上调用**：滑动、动画中不应触发 Binder 调用
- **批量替代逐条**：使用 `ContentProviderOperation` 批量操作
- **注意 oneway 调用**：不需要返回值的场景用 `oneway` 让调用异步

[已验证: 官方文档, developer.android.com/reference/android/content/ContentProvider — 批量操作减少跨进程调用次数]

### 合理的线程池配置

[需重写: 纯列表格式，需转为叙述风格，补充每条建议的技术原理和实战经验。]

- 控制并发数（核心线程数不超过 CPU 核心数）
- 使用有意义的线程名方便 Perfetto 定位
- Activity/Fragment 销毁时取消相关任务
- 通过 `adb shell ps -T | grep <package>` 监控线程数

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md — WeSing 发现 SDK 升级后新增 30 个未命名线程]

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

[需重写: 纯列表格式，需展开为叙述段落，解释每种预取策略的工作原理和适用场景。]

- **RecyclerView Prefetch**：GapWorker 在主线程空闲时提前创建即将可见的 ViewHolder
- **Compose LazyList Prefetch**：LazyColumn 内部同样实现了 Prefetch
- **预加载图片**：Coil、Glide 都支持预加载
- **预计算布局**：StaticLayout 等提前在后台线程计算好

[来源: 预渲染和预计算在 RecyclerView 和 Compose 中都有系统级支持。来源: 官方文档 + web_search]

## 常见误区

1. **"优化就是减少代码量"**：更多时候是关于"在正确的时间做正确的事"
2. **"Compose 天生比 View 快"**：BOM 2025.12.00 声明性能对等，但使用不当可以更慢 [需确认: BOM 2025.12.00 版本号是否准确，以及"性能对等"的具体声明来源]
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
