---
title: "布局优化策略"
chapter: "22.1"
section: "22.1"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 ViewRootImpl/ViewGroup/LayoutInflater/ViewStub/FrameMetrics; current Android Developers layout guidance; AndroidX AsyncLayoutInflater 1.1.0 API and release notes; AIW 7.10/22.3"
confidence: medium-high
sources:
  - type: aiw
    path: "src/part2-performance/ch07-smoothness/10-view-layout-performance.md"
  - type: aiw
    path: "src/part1-fundamentals/ch02-rendering/05-main-render-thread.md"
  - type: aiw
    path: "src/part5-app/ch22-rendering-practice/03-compose-performance.md"
  - type: official
    path: "https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html"
  - type: official
    path: "https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies"
  - type: official
    path: "https://developer.android.com/reference/android/view/ViewStub"
  - type: official
    path: "https://developer.android.com/reference/androidx/asynclayoutinflater/view/AsyncLayoutInflater"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [layout, constraintlayout, viewstub, inflate, hierarchy]
related_chapters: ["22.3", "7.10", "2.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 布局优化策略

应用侧布局优化要把 View 体系的递归测量、`LayoutInflater` 流程和 `requestLayout()` 触发路径转成页面改造、代码选型和 trace 验收方法；相关机制见 [7.10 View 布局性能](../../part2-performance/ch07-smoothness/10-view-layout-performance.md)。这里的 trace 指 Perfetto 等工具记录的线程与渲染时间线，deadline 是一帧按时完成的截止时间。目标很具体：减少首帧和页面切换里的主线程 Measure / Layout 时间，为同一帧的其他工作留出预算。

平台源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点，内核侧统一到 `android17-6.18-2026-06_r6`。这些改动位于标准 HWUI App Window，也就是普通硬件加速应用窗口的主线程准备阶段。`ViewRootImpl` 通过 `Choreographer` 安排 Traversal（遍历 View 树的一轮工作），再按脏标记，也就是“哪些阶段需要重新执行”的状态，选择 Measure、Layout 和 Draw；硬件加速路径随后通过 `syncAndDrawFrame()` 同步 RenderNode 绘制节点树，并把后续工作交给 RenderThread。布局变快只证明 App 主线程少做了工作，不能直接证明图形 buffer 已被 SurfaceFlinger 按时选中并送往显示。

## 布局层级对渲染性能的影响

布局优化要从一帧里发生了什么看起。子 View 的 `requestLayout()` 沿父链传播到 `ViewRootImpl` 后，根节点设置 `mLayoutRequested` 并安排一次 Traversal；已有 traversal 尚未执行时，重复的调度请求会被合并。这个合并不保证一帧只布局一次：若 View 在首轮 layout 期间留下有效的 `requestLayout()`，Android 17 可以在同一帧再执行一轮 measure/layout；第二轮期间再次提出的请求会延后。`performTraversals()` 会根据窗口和 View 树状态决定是否调用 `performMeasure()`、`performLayout()` 与 `performDraw()`，三段工作并非每帧固定执行。

Measure 是递归过程：父容器通过 `MeasureSpec` 告诉子节点尺寸是精确值、上限还是未指定，子节点报告测量结果，父容器再据此确定自己的尺寸。Layout 随后为各子节点分配位置。节点越多、嵌套越深、父容器规则越复杂，主线程执行的代码通常越多；多轮测量会进一步放大这部分成本。详见前述 7.10 节。

布局层级不只涉及深度。更常见的成本来自三类结构：

- **重复测量的容器**：`RelativeLayout`、带 `layout_weight` 的 `LinearLayout`、复杂约束容器都可能让子 View 被测量多次。层级一深，重复测量会沿树放大。
- **高频出现的列表项**：单个 item（列表条目）的成本可能很小，列表首屏同时 inflate 多个、滑动中又频繁创建和绑定时，累计成本仍可能造成连续掉帧。
- **提前创建的低频内容**：标准 `ViewGroup.measureChildren()` 会跳过 `View.GONE` 子节点，绘制也通常跳过它，但对象与子树已经完成 inflate，父容器仍会遍历并检查状态，自定义容器还可以采用不同测量规则。大块低频内容更适合延迟创建。

判断一个布局是否需要优化，要看 trace 里的时间与调用次数。Android 17 的 `performMeasure()` 和 `performLayout()` 分别用 `measure`、`layout` 作为 framework trace 切片名；`FrameMetrics.LAYOUT_MEASURE_DURATION` 合并报告本帧中被标记需要更新的 View 树部分所花的测量与布局时间。没有跨刷新率通用的“3～5 ms 即异常”阈值，应把这两段放回 FrameTimeline（记录每帧目标与实际时间的系统轨道）的 deadline、同场景分位数和完整 `Choreographer#doFrame` 中判断。

慢帧若主要耗在 `performDraw()`、UI 等待 RenderThread、RenderThread 的 `dequeueBuffer` / `queueBuffer`、GPU 工作队列或显示侧，压平布局的收益会很小。`queueBuffer()` 按时只说明 Producer（内容生产者）把一块 buffer 提交进队列；后面仍要核对 `BufferTX - <layerName>` 这类 buffer 事务切片、latch（SurfaceFlinger 选定本帧 buffer）、FrameTimeline actual slice（实际完成轨道）和 present timing（呈现时间）。

工程上建议按这个顺序处理：

1. **先改首屏和高频列表 item**：启动首帧、页面切换、RecyclerView item 的收益最稳定。
2. **再改被多处复用的公共布局**：标题栏、卡片、空态页、错误页一旦优化，多个页面同时受益。
3. **低频深层布局按证据处理**：设置页、二级弹窗这类入口少的页面，除非线上 trace 证明它们造成卡顿。

## ConstraintLayout vs 传统布局的性能对比

`ConstraintLayout` 的价值是用约束关系减少嵌套。一个“图标 + 标题 + 副标题 + 操作按钮”的卡片，如果用多层 `LinearLayout` / `RelativeLayout` 组合，常见结果是 3～5 层；改成 `ConstraintLayout` 后，子 View 可以直接挂在同一个父容器下，Measure/Layout 的遍历路径更短。

Google 在 2017 年用注册表单页面做过公开测试：传统 `RelativeLayout` 嵌套版本在 20 秒 Systrace 窗口中出现 80 次 expensive measure/layout alerts，也就是当时工具按启发式阈值给出的高成本测量/布局警告；改成扁平的 `ConstraintLayout` 后，警告明显减少，并在 `FrameMetrics.LAYOUT_MEASURE_DURATION` 上测得约 40% 的平均耗时下降。测试环境是 Nexus 5X、Android 8.0 和 ConstraintLayout 1.0.2，约 40% 是 100 帧的平均结果。这个历史实验支持“压平该页面层级有收益”，不能把 40% 当成所有项目的固定比例；设备、AndroidX 版本、布局复杂度和刷新率都会改变结果。

选型时用三条规则：

- **复杂相对关系用 `ConstraintLayout`**：多个 View 需要互相对齐、文字基线对齐、比例约束、Barrier（由多个 View 边界计算出的虚拟参考线）或 Chain（把一组 View 按链式规则排列）时，`ConstraintLayout` 通常比嵌套容器更合适。
- **简单线性结构继续用 `LinearLayout` / `FrameLayout`**：2-3 个子 View 的水平或垂直排列，不需要为“统一技术栈”改成 `ConstraintLayout`。
- **列表 item 要实测**：item 很简单时，约束求解器计算约束关系的固定开销可能抵消层级收益；item 很复杂时，扁平化更容易带来改善。用 Macrobenchmark（端到端场景基准）、Perfetto 或 `FrameMetrics.LAYOUT_MEASURE_DURATION` 对比两版。

一个实用的迁移方式是从“层级深、存在重复测量且复用多”的布局下手。Layout Inspector 能帮助定位冗余父节点和多层相对关系，但层数本身没有合格线。对公共卡片、列表 item 或首屏头部区域做一版等价布局，再用同一设备、同一数据量、同一操作路径抓 trace；Measure / Layout 分位数和完整帧指标都改善后再推广。

## ViewStub、merge、include 的正确使用

`ViewStub`、`<merge>`、`<include>` 解决的是三种不同问题。这里的 inflate 指解析 XML、创建 View 对象并设置属性；attach 指把 View 加入父容器。混用这些工具会让布局更难维护。

| 工具 | 解决的问题 | 适合场景 | 常见风险 |
|------|------------|----------|----------|
| `ViewStub` | 延迟创建低频 View 树 | 空态、错误态、权限说明、调试面板 | 首次显示会发生同步 inflate，不能在动画关键帧里触发 |
| `<merge>` | 减少被 include 或自定义 View 内部的多余根容器 | 自定义组合 View、公共标题栏、卡片根布局 | 必须依赖外部父容器提供布局参数，单独预览和复用受限 |
| `<include>` | 复用 XML 布局 | 多页面共用 header/footer/状态区 | 只复用结构，不减少运行时 inflate 成本；要降层级通常要配合 `<merge>` |

`ViewStub` 适合“大概率不显示”的内容。错误页、空态页、折叠的高级筛选区，如果直接写在主布局里，首帧就会执行 inflate 和对象创建；换成 `ViewStub` 后，首帧只创建一个轻量占位符。首次需要显示时再调用 `inflate()`，拿到真实根 View 后缓存引用，后续切换只改 `visibility`。

`ViewStub` 调用 `inflate()` 后会被新 View 替换，不能对原 stub 再次 inflate。以下代码缓存替换后的 View，避免每次显示都查找并创建：

```kotlin
private var errorPanel: View? = null

fun showError(root: View) {
    val panel = errorPanel ?: root.findViewById<ViewStub>(R.id.stub_error_panel)
        .inflate()
        .also { errorPanel = it }

    panel.isVisible = true
}
```

这段代码只验证一件事：`ViewStub` 的收益来自“首次之前不创建”。一旦创建完成，它和普通 View 没区别，后续应该复用缓存引用。若引用保存在 Fragment 字段中，要在 `onDestroyView()` 清空，避免旧 View 树跨越视图生命周期。

`<merge>` 适合去掉组合 View 内部的壳。自定义 `TitleBar : FrameLayout` 如果 inflate 一个根节点也是 `FrameLayout` 的 XML，就会得到两层容器。把 XML 根换成 `<merge>`，子 View 会直接挂到 `TitleBar` 上，减少一次容器遍历。下面的 XML 只表达待合入父容器的两个子节点：

```xml
<merge xmlns:android="http://schemas.android.com/apk/res/android">
    <ImageButton
        android:id="@+id/back"
        android:layout_width="48dp"
        android:layout_height="48dp" />

    <TextView
        android:id="@+id/title"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content" />
</merge>
```

`<merge>` 没有可独立返回的根 View，只能在 inflater 已得到父容器并且 `attachToRoot=true` 时使用。调用 `inflate(resource, parent, false)` 加载 `<merge>` 根布局会抛出 `InflateException`，因此它不适用于需要先构建、稍后再 attach 的预加载方案。

`<include>` 更偏工程复用。它不会自动让布局更快，`LayoutInflater.parseInclude()` 仍要解析被 include 的资源并创建 View。被 include 的布局可以用 `<merge>` 去掉冗余根容器，也可以把 `<include>` 放进 `ViewStub` 指向的低频子树；是否有收益取决于运行时少创建、少测量了什么。

## 布局预加载与异步 Inflate

布局预加载会转移创建时间，却不会消除解析、构造和绑定成本。只有未来使用概率较高、可安全缓存，并且预加载不会挤占输入或当前帧时，这种转移才有收益。

可选方案分三类：

- **主线程空闲预加载**：在 `Looper.myQueue().addIdleHandler` 或页面稳定后的延迟任务里 inflate 下一步大概率会用到的布局。IdleHandler 是消息队列暂时空闲时执行的回调，仍运行在主线程；执行期间到达的新消息只能等待，因此任务必须够短，并带页面销毁、配置变化和用户转向时的取消条件。
- **受控复用**：RecyclerView 的 `RecycledViewPool` 具有清晰的回收协议。普通 View 不宜随意放入全局对象池；预创建 View 必须保持未 attach 状态，且 Context、主题、配置和旧数据都与使用点一致。
- **`AsyncLayoutInflater`**：尝试把 XML 解析和 View 构造放到后台线程，完成后再 attach。适合复杂但不需要立刻展示的布局；不满足后台构造条件时会回退到 UI 线程。

`AsyncLayoutInflater` 的使用边界要写清楚。后台 inflate 要求父容器的 `generateLayoutParams(AttributeSet)` 线程安全，被创建的 View 构造过程不能创建 `Handler` 或调用 `Looper.myLooper()`。它仍不支持直接设置 `LayoutInflater.Factory` / `Factory2`，也不支持包含 fragment 的布局；但 AndroidX 1.1.0 可以在构造时传入 `AsyncLayoutFactory`，AppCompat 场景可使用 `AsyncAppCompatFactory` 正确创建 AppCompat View。遇到无法在后台构建的布局，AndroidX 会回退到 UI 线程 inflate；功能可以继续，但本次解析和构造没有移出 UI 线程。

不传 callback executor 的默认重载会在 UI 线程执行完成回调，而且返回的 View 尚未加入 `parent`。下面的接入在回调中完成 attach 和绑定：

```kotlin
AsyncLayoutInflater(context).inflate(
    R.layout.panel_filter,
    parent
) { view, _, targetParent ->
    targetParent?.addView(view)
    bindFilterPanel(view)
}
```

`bindFilterPanel()` 与 `addView()` 仍在主线程执行。异步 inflate 只迁移了布局解析和 View 构造的一部分成本；数据绑定、图片解码和网络请求需要按各自线程约束另行安排。AndroidX 1.1.0 也提供 callback executor（指定完成回调在哪个执行器运行）的重载；若回调不在 UI 线程，调用 `addView()` 和修改 View 前仍需切回 UI 线程。

验收方式看 trace：使用前，`Activity.onCreate()` 或点击事件后方能看到较长的 `inflate` 区间；使用后，这段区间应移到后台线程，主线程只保留较短的 `addView` / bind 区间。如果主线程仍出现完整 `inflate`，布局可能触发了回退；若主线程只剩 bind 却依然超时，瓶颈已经转到回调工作。还要记录预加载未命中率，也就是已创建却从未使用的比例，以及被取消数量，避免用更多 CPU、内存换来很少的命中。

## Compose 与 View 混合布局的性能陷阱

View/Compose 混合场景要同时核对两套边界：`ComposeView` 放进 View 树后，它既要参与父 View 的 Measure / Layout，又有自己的 Composition、Layout、Drawing 阶段。Composition 根据状态构建或更新 Compose 节点，Layout 测量并放置节点，Drawing 记录绘制内容。普通 `ComposeView` 和不创建独立 Surface 的 `AndroidView` 仍可以沿宿主 `ViewRootImpl → RenderThread → App Window` 的标准路径出图；Compose 由 AndroidX 独立发布，其运行时和编译器行为要按项目实际依赖版本核对，不能由 Android 17 platform tag 推断。

常见风险有三类：

- **RecyclerView item 里嵌套 `ComposeView`**：item 复用、Composition 生命周期、状态清理都要处理。滑动慢帧可能来自 ViewHolder（列表条目容器）创建，也可能来自 Compose 首次组合。
- **Compose 页面里嵌入复杂 Android View**：`AndroidView` 承载 WebView、地图或播放器时，View 自身的 measure/layout 和生命周期成本仍然存在。组件还可能拥有 Chromium 渲染线程、`SurfaceView` 或 `TextureView` 输入，届时只看宿主 App Window 不足以解释内容生产成本。
- **状态跨边界传播过宽**：View 层一次数据刷新导致整个 `ComposeView` 重新组合，或者 Compose 状态变化触发外层 View `requestLayout()`，都会让本应局部处理的变化波及更大的页面范围。

混合方案的边界要少，生命周期要清楚，trace 要分开看。Perfetto 里先确认慢帧落在 framework 的 `measure` / `layout`，Compose runtime / drawing，还是独立 Producer 与 Surface，再决定改 View 结构、Compose 状态读取或子组件管线。没有证据时，不要把问题直接归因给 Compose 或 View。

## 验收清单

布局优化完成后，用同一台设备、同一份数据、同一条操作路径验证。至少检查这些项目：

- `Choreographer#doFrame` 中 `measure` / `layout` 的 P50、P90、P95 以及调用次数是否下降；P95 表示按耗时排序后 95% 的样本不超过该值。
- `FrameMetrics.LAYOUT_MEASURE_DURATION` 和 FrameTimeline overrun（超过该帧 deadline 的时长）是否同时改善，不能只看单帧最小值。
- 首帧、页面切换或列表交互的用户可感知耗时是否下降。
- Layout Inspector 中冗余父节点和重复测量结构是否减少；节点总数只作为解释材料。
- 低 RAM 设备和高刷新率设备上是否同时通过。120 Hz 的名义 VSync 间隔约为 8.33 ms，当前帧仍应以 FrameTimeline 给出的 deadline 为准。
- 若 App 侧按时完成，继续核对 RenderThread、`queueBuffer`、`BufferTX`、latch 与 present，避免把显示侧延迟记到布局。
- 视觉一致性、无障碍层级、点击热区没有被改坏。

布局优化的完成标准，是关键帧里的主线程测量与布局成本下降，同时完整帧指标和用户体验没有退化。布局切片只回答 App 主线程这一段；帧是否显示及时，还要沿标准 HWUI 路径检查到 present。

## 源码与文档

- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：`requestLayout()`、Traversal、`measure` / `layout` trace 与 HWUI 交接。
- [Android 17 `LayoutInflater.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/LayoutInflater.java)：`inflate` trace、`<include>` 与 `<merge>` 解析约束。
- [Android 17 `ViewStub.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewStub.java)：占位 View 被替换和首次 inflate 的行为。
- [Android 17 `FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：`LAYOUT_MEASURE_DURATION` 的统计语义。
- [Performance and view hierarchies](https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies)：重复测量、层级诊断与布局压平。
- [ConstraintLayout performance experiment](https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html)：2017 年实验条件与 Measure / Layout 结果。
- [`AsyncLayoutInflater` API](https://developer.android.com/reference/androidx/asynclayoutinflater/view/AsyncLayoutInflater)：后台构建条件、回退、attach 和 callback executor 边界。
- [AsyncLayoutInflater releases](https://developer.android.com/jetpack/androidx/releases/asynclayoutinflater)：1.1.0 稳定版、`AsyncLayoutFactory` 与 callback executor 更新。
