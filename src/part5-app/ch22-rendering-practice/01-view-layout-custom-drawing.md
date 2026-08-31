---
title: View 布局与自定义绘制优化
chapter: '22.1'
section: '22.1'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 ViewRootImpl/ViewGroup/LayoutInflater/ViewStub/ViewTreeObserver/FrameMetrics; current Android Developers layout guidance; AndroidX AsyncLayoutInflater 1.1.0 API and release notes
confidence: medium-high
sources:
- type: official
  path: https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html
- type: official
  path: https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies
- type: official
  path: https://developer.android.com/reference/android/view/ViewStub
- type: official
  path: https://developer.android.com/reference/androidx/asynclayoutinflater/view/AsyncLayoutInflater
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md
- type: clippings-structure-ref
  path: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md
- type: official
  path: developer.android.com/develop/ui/views/layout/custom-views/optimizing-view
- type: official
  path: developer.android.com/topic/performance/hardware-accel
- type: official
  path: perfetto.dev/docs/getting-started/system-tracing
- type: official
  path: developer.android.com/topic/performance/tracing/custom-events
- type: aosp
  path: frameworks/base/core/java/android/view/View.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/RenderNode.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/LayoutInflater.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewTreeObserver.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java
tags:
- layout
- constraintlayout
- viewstub
- inflate
- hierarchy
- custom-view
- ondraw
- canvas
- hardware-acceleration
- invalidate
- viewrootimpl
- hwui
related_chapters:
- '22.3'
- '2.4'
- '2.7'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch22-rendering-practice/01-layout-optimization.md
- src/part5-app/ch22-rendering-practice/04-custom-view-optimization.md
- src/part2-performance/ch07-smoothness/03-view-layout-rendering-optimization.md
---

# View 布局与自定义绘制优化

应用侧布局优化要把 View 体系的递归测量、`LayoutInflater` 对象创建、`requestLayout()` 传播与绘制失效放进同一帧时间线。本文统一维护这些机制、页面改造、代码选型和 trace 验收方法；这里的 trace 指 Perfetto 等工具记录的线程与渲染时间线，deadline 是一帧按时完成提交的截止点。目标很具体：减少首帧、页面切换和高频更新里的主线程 Measure / Layout / Draw 工作，为同一帧的输入、业务逻辑和渲染提交留出预算。

平台源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点，内核侧统一到 `android17-6.18-2026-06_r6`。这些改动位于标准 HWUI App Window，也就是普通硬件加速应用窗口的主线程准备阶段。`ViewRootImpl` 通过 `Choreographer` 安排 Traversal（遍历 View 树的一轮工作），再按脏标记，也就是“哪些阶段需要重新执行”的状态，选择 Measure、Layout 和 Draw；硬件加速路径随后通过 `syncAndDrawFrame()` 同步 RenderNode 绘制节点树，并把后续工作交给 RenderThread。布局变快只证明 App 主线程少做了工作，不能直接证明图形 buffer 已被 SurfaceFlinger 按时选中并送往显示。

View 性能从减少层级、无效遍历和过度绘制开始，自定义 View 还要控制对象分配、Path/Bitmap 复用、invalidate 范围和绘制算法。布局与绘制应在同一帧时间线中验证。

## 层级、inflate、测量与布局失效

### 布局层级对渲染性能的影响

布局优化要从一帧里发生了什么看起。子 View 的 `requestLayout()` 沿父链传播到 `ViewRootImpl` 后，根节点设置 `mLayoutRequested` 并安排一次 Traversal；已有 traversal 尚未执行时，重复的调度请求会被合并。这个合并不保证一帧只布局一次：若 View 在首轮 layout 期间留下有效的 `requestLayout()`，Android 17 可以在同一帧再执行一轮 measure/layout；第二轮期间再次提出的请求会延后。`performTraversals()` 会根据窗口和 View 树状态决定是否调用 `performMeasure()`、`performLayout()` 与 `performDraw()`，三段工作并非每帧固定执行。

Measure 是递归过程：父容器通过 `MeasureSpec` 告诉子节点尺寸是精确值、上限还是未指定，子节点报告测量结果，父容器再据此确定自己的尺寸。Layout 随后为各子节点分配位置。节点越多、嵌套越深、父容器规则越复杂，主线程执行的代码通常越多；多轮测量会进一步放大这部分成本。结论仍要回到当前页面的调用次数、单节点工作量和 FrameTimeline deadline。

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

### ConstraintLayout vs 传统布局的性能对比

`ConstraintLayout` 的价值是用约束关系减少嵌套。一个“图标 + 标题 + 副标题 + 操作按钮”的卡片，如果用多层 `LinearLayout` / `RelativeLayout` 组合，常见结果是 3～5 层；改成 `ConstraintLayout` 后，子 View 可以直接挂在同一个父容器下，Measure/Layout 的遍历路径更短。

Google 在 2017 年用注册表单页面做过公开测试：传统 `RelativeLayout` 嵌套版本在 20 秒 Systrace 窗口中出现 80 次 expensive measure/layout alerts，也就是当时工具按启发式阈值给出的高成本测量/布局警告；改成扁平的 `ConstraintLayout` 后，警告明显减少，并在 `FrameMetrics.LAYOUT_MEASURE_DURATION` 上测得约 40% 的平均耗时下降。测试环境是 Nexus 5X、Android 8.0 和 ConstraintLayout 1.0.2，约 40% 是 100 帧的平均结果。这个历史实验支持“压平该页面层级有收益”，不能把 40% 当成所有项目的固定比例；设备、AndroidX 版本、布局复杂度和刷新率都会改变结果。

选型时用三条规则：

- **复杂相对关系用 `ConstraintLayout`**：多个 View 需要互相对齐、文字基线对齐、比例约束、Barrier（由多个 View 边界计算出的虚拟参考线）或 Chain（把一组 View 按链式规则排列）时，`ConstraintLayout` 通常比嵌套容器更合适。
- **简单线性结构继续用 `LinearLayout` / `FrameLayout`**：2-3 个子 View 的水平或垂直排列，不需要为“统一技术栈”改成 `ConstraintLayout`。
- **列表 item 要实测**：item 很简单时，约束求解器计算约束关系的固定开销可能抵消层级收益；item 很复杂时，扁平化更容易带来改善。用 Macrobenchmark（端到端场景基准）、Perfetto 或 `FrameMetrics.LAYOUT_MEASURE_DURATION` 对比两版。

一个实用的迁移方式是从“层级深、存在重复测量且复用多”的布局下手。Layout Inspector 能帮助定位冗余父节点和多层相对关系，但层数本身没有合格线。对公共卡片、列表 item 或首屏头部区域做一版等价布局，再用同一设备、同一数据量、同一操作路径抓 trace；Measure / Layout 分位数和完整帧指标都改善后再推广。

### ViewStub、merge、include 的正确使用

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

### `LayoutInflater`：缓存构造器不等于消除创建成本

布局 XML 经 AAPT2 编译成 binary XML（编译后的二进制 XML），运行时仍要读取节点与属性、创建对象并组装 View 树。把整段工作都称为“XML 解析”会漏掉主题、资源和业务构造器的成本。一次 `inflate()` 可以按三段理解：

1. `Resources.getLayout()` 提供解析器，inflater 读取 `AttributeSet`，处理 `android:theme`、`<include>`、`<merge>`、`<tag>` 等特殊标签，并让父容器生成 `LayoutParams`；
2. `createViewFromTag()` 先经过 `Factory2 → Factory → private factory`。都未创建 View 时，才进入 `onCreateView()` 或按完整类名构造；AppCompat 的控件替换、Context 包装和 tint 也在这条 Factory 路径中；
3. `rInflateChildren()` 递归创建子节点、生成布局参数、加入父容器，并在子树完成后调用 `onFinishInflate()`。

`LayoutInflater` 的进程级构造器表可以省掉重复的类查找，却不会省掉 `Constructor.newInstance()`、View 构造函数、style、字体、Drawable 和自定义初始化。首次进入页面还可能包含类加载；因此冷启动与预热后的 trace 要分开比较，不能先假定反射就是主要耗时。

传入的 `root` 还决定 XML 根节点能否获得正确的父容器布局参数：

| 调用形态 | 返回值 | 已加入 `root` | 根节点 `LayoutParams` |
| --- | --- | ---: | --- |
| `inflate(res, root, true)` | `root` | 是 | 由 `root.generateLayoutParams()` 生成 |
| `inflate(res, root, false)` | XML 根 View | 否 | 仍由 `root.generateLayoutParams()` 生成 |
| `inflate(res, null, false)` | XML 根 View | 否 | 缺少父容器上下文，之后可能需要修正 |

所以“先传 `null`，稍后再 `addView()`”并不等价于传入真实 parent；而 `<merge>` 因为没有独立根节点，只能在已有 parent 且 `attachToRoot=true` 时展开。

### 布局预加载与异步 Inflate

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

### `ViewTreeObserver`：布局回调不是显示完成信号

Android 17 的 `ViewRootImpl.performTraversals()` 会在本轮发生 layout，或全局属性需要重新计算时调用 `dispatchOnGlobalLayout()`。因此 `OnGlobalLayoutListener` 只说明 View 树的全局布局状态已经处理到这一点；它不能证明某个 `View.layout()` 刚执行完，更不能证明 buffer 已提交、被 SurfaceFlinger 选中并显示。

回调要按它实际观察的范围使用：

- 只关心一个 View 的位置或尺寸时，优先用 `View.OnLayoutChangeListener` 或 AndroidX `doOnLayout`；
- 一次性 global listener 在条件满足后立即移除，回调内避免 I/O、同步 Binder、整树扫描和无条件 `requestLayout()`；
- `OnPreDrawListener.onPreDraw()` 返回 `false` 会取消当前 draw 并重新调度，条件长期不满足会形成连续取消；
- 首帧显示应使用 FrameTimeline、`reportFullyDrawn()` 或与产品目标含义相符的信号，而不是 global layout 的结束时间。

`getViewTreeObserver()` 返回的对象也不是可跨整个 View 生命周期永久保存的句柄。未 attach 的 View 使用 floating observer；attach 时 listener 会合并到窗口 observer，旧对象随后失效。长期持有引用时要检查 `isAlive()`，移除 listener 时重新取得当前 observer 更稳妥。

### Compose 与 View 混合布局的性能陷阱

View/Compose 混合场景要同时核对两套边界：`ComposeView` 放进 View 树后，它既要参与父 View 的 Measure / Layout，又有自己的 Composition、Layout、Drawing 阶段。Composition 根据状态构建或更新 Compose 节点，Layout 测量并放置节点，Drawing 记录绘制内容。普通 `ComposeView` 和不创建独立 Surface 的 `AndroidView` 仍可以沿宿主 `ViewRootImpl → RenderThread → App Window` 的标准路径出图；Compose 由 AndroidX 独立发布，其运行时和编译器行为要按项目实际依赖版本核对，不能由 Android 17 platform tag 推断。

常见风险有三类：

- **RecyclerView item 里嵌套 `ComposeView`**：item 复用、Composition 生命周期、状态清理都要处理。滑动慢帧可能来自 ViewHolder（列表条目容器）创建，也可能来自 Compose 首次组合。
- **Compose 页面里嵌入复杂 Android View**：`AndroidView` 承载 WebView、地图或播放器时，View 自身的 measure/layout 和生命周期成本仍然存在。组件还可能拥有 Chromium 渲染线程、`SurfaceView` 或 `TextureView` 输入，届时只看宿主 App Window 不足以解释内容生产成本。
- **状态跨边界传播过宽**：View 层一次数据刷新导致整个 `ComposeView` 重新组合，或者 Compose 状态变化触发外层 View `requestLayout()`，都会让本应局部处理的变化波及更大的页面范围。

混合方案的边界要少，生命周期要清楚，trace 要分开看。Perfetto 里先确认慢帧落在 framework 的 `measure` / `layout`，Compose runtime / drawing，还是独立 Producer 与 Surface，再决定改 View 结构、Compose 状态读取或子组件管线。没有证据时，不要把问题直接归因给 Compose 或 View。

### 验收清单

布局优化完成后，用同一台设备、同一份数据、同一条操作路径验证。至少检查这些项目：

- `Choreographer#doFrame` 中 `measure` / `layout` 的 P50、P90、P95 以及调用次数是否下降；P95 表示按耗时排序后 95% 的样本不超过该值。
- `FrameMetrics.LAYOUT_MEASURE_DURATION` 和 FrameTimeline overrun（超过该帧 deadline 的时长）是否同时改善，不能只看单帧最小值。
- 首帧、页面切换或列表交互的用户可感知耗时是否下降。
- Layout Inspector 中冗余父节点和重复测量结构是否减少；节点总数只作为解释材料。
- 低 RAM 设备和高刷新率设备上是否同时通过。120 Hz 的名义 VSync 间隔约为 8.33 ms，当前帧仍应以 FrameTimeline 给出的 deadline 为准。
- 若 App 侧按时完成，继续核对 RenderThread、`queueBuffer`、`BufferTX`、latch 与 present，避免把显示侧延迟记到布局。
- 视觉一致性、无障碍层级、点击热区没有被改坏。

布局优化的完成标准，是关键帧里的主线程测量与布局成本下降，同时完整帧指标和用户体验没有退化。布局切片只回答 App 主线程这一段；帧是否显示及时，还要沿标准 HWUI 路径检查到 present。

### 源码与文档

- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：`requestLayout()`、Traversal、`measure` / `layout` trace 与 HWUI 交接。
- [Android 17 `LayoutInflater.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/LayoutInflater.java)：`inflate` trace、`<include>` 与 `<merge>` 解析约束。
- [Android 17 `ViewStub.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewStub.java)：占位 View 被替换和首次 inflate 的行为。
- [Android 17 `FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：`LAYOUT_MEASURE_DURATION` 的统计语义。
- [Performance and view hierarchies](https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies)：重复测量、层级诊断与布局压平。
- [ConstraintLayout performance experiment](https://android-developers.googleblog.com/2017/08/understanding-performance-benefits-of.html)：2017 年实验条件与 Measure / Layout 结果。
- [`AsyncLayoutInflater` API](https://developer.android.com/reference/androidx/asynclayoutinflater/view/AsyncLayoutInflater)：后台构建条件、回退、attach 和 callback executor 边界。
- [AsyncLayoutInflater releases](https://developer.android.com/jetpack/androidx/releases/asynclayoutinflater)：1.1.0 稳定版、`AsyncLayoutFactory` 与 callback executor 更新。


## 绘制分配、缓存与局部刷新

布局成本稳定后，自定义绘制继续检查 onDraw 中的分配、离屏层、复杂路径和无效区域。缓存只适合内容变化较少的部分。

优化自定义 View，需要查看状态变化触发的整条渲染路径。一次变化可能只触发 draw（绘制），也可能通过 `requestLayout()` 增加 measure（测量）和 layout（摆放）；UI 线程完成 DisplayList（绘制命令记录）后，后续线程和显示系统仍会决定这一帧何时上屏。

平台源码固定到 Android 17 / API 37 / `android-17.0.0_r1`，Linux 内核固定到 `android17-6.18-2026-06_r6`。普通自定义 View 没有独立 Surface，走应用窗口的标准 HWUI（Android 硬件加速 UI 渲染器）路径：`Choreographer#doFrame` 驱动 traversal（一次 View 树遍历），UI 线程更新 RenderNode（保存 View 绘制记录和变换属性的渲染节点）及其 DisplayList，`HardwareRenderer.syncAndDrawFrame()` 再把树状态交给专用渲染线程 RenderThread。

随后，BLAST BufferQueue 提交图形缓冲区，SurfaceFlinger（系统合成服务）完成合成，HWC（Hardware Composer，硬件合成器）参与显示，最终得到实际显示时间。显示后段可结合 [Android View 标准渲染链路](../../part2-performance/ch13-rendering-pipelines/01-android-view-pipeline-analysis.md) 阅读。

### 测量、摆放、绘制：按触发条件判断成本

`onMeasure()`、`onLayout()` 与 `onDraw()` 没有固定的优化优先级。应先用性能 trace（时间轴）判断哪一段执行过多或单次过长：

| 回调 | 常见触发条件 | 应避免的工作 |
| --- | --- | --- |
| `onMeasure()` | `requestLayout()`、父约束变化、挂载到窗口、窗口或配置变化 | I/O、重复解析文本、没有次数上限的多轮子 View 测量 |
| `onLayout()` | 布局请求，或 View 边界变化后仍需重新摆放 | 分配临时坐标对象、重复计算测量阶段已有的几何关系 |
| `onDraw()` | 绘制内容失效、动画、父级绘制或 DisplayList 需要重录 | 对象分配、同步 I/O、每帧重建不变的 Path / Shader |

`MeasureSpec` 把父容器给出的尺寸和模式编码在一个整数中。三种模式分别是固定尺寸的 `EXACTLY`、给出上限的 `AT_MOST`，以及不提供父级上限的 `UNSPECIFIED`。同一组 `MeasureSpec` 在没有强制布局标记时可能命中 `View.measure()` 的缓存，`onMeasure()` 不一定执行。

常规路径中的 `requestLayout()` 会清空当前 View 的测量缓存，设置内部标记 `PFLAG_FORCE_LAYOUT` 与 `PFLAG_INVALIDATED`，并向尚未请求布局的父级传播。若调用发生在布局过程中，`ViewRootImpl.requestLayoutDuringLayout()` 会决定本轮接受还是延后处理，不能把一次调用直接等同于一次完整遍历。最终哪些分支重新测量、摆放和绘制，还取决于标记、约束与窗口状态。

#### `onMeasure()` 的缓存必须覆盖完整输入

测量缓存不能只比较宽度。高度 `MeasureSpec`、内边距、数据版本、字体、语言与地区设置、布局方向、子 View 可见性和外边距都可能改变结果。缓存适合保存纯计算得到的几何结果，不能绕过 `setMeasuredDimension()` 或破坏父容器约束。

下面的示例用两个 `MeasureSpec` 和显式内容版本保护缓存。`computeGeometry()` 只做 CPU 计算，不修改 View 树。

```java
private int mLastWidthSpec = Integer.MIN_VALUE;
private int mLastHeightSpec = Integer.MIN_VALUE;
private int mLastContentVersion = -1;
private int mLastPaddingLeft = Integer.MIN_VALUE;
private int mLastPaddingTop = Integer.MIN_VALUE;
private int mLastPaddingRight = Integer.MIN_VALUE;
private int mLastPaddingBottom = Integer.MIN_VALUE;
private int mContentVersion;
private int mDesiredWidth;
private int mDesiredHeight;

@Override
protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
    if (widthMeasureSpec != mLastWidthSpec
            || heightMeasureSpec != mLastHeightSpec
            || mContentVersion != mLastContentVersion
            || getPaddingLeft() != mLastPaddingLeft
            || getPaddingTop() != mLastPaddingTop
            || getPaddingRight() != mLastPaddingRight
            || getPaddingBottom() != mLastPaddingBottom) {
        computeGeometry(widthMeasureSpec, heightMeasureSpec);
        mLastWidthSpec = widthMeasureSpec;
        mLastHeightSpec = heightMeasureSpec;
        mLastContentVersion = mContentVersion;
        mLastPaddingLeft = getPaddingLeft();
        mLastPaddingTop = getPaddingTop();
        mLastPaddingRight = getPaddingRight();
        mLastPaddingBottom = getPaddingBottom();
    }

    setMeasuredDimension(
            resolveSizeAndState(mDesiredWidth, widthMeasureSpec, 0),
            resolveSizeAndState(mDesiredHeight, heightMeasureSpec, 0));
}
```

数据、字体、语言与地区设置或布局方向发生变化，并且会影响期望尺寸时，更新 `mContentVersion` 后调用 `requestLayout()`。只改变颜色时不应增加测量版本。自定义 `ViewGroup` 还要为每个子 View 生成正确的 `MeasureSpec`、合并 measured state（子 View 报告的尺寸状态），并处理内边距、外边距和最小尺寸，不能用缓存跳过这些契约。

#### `onLayout()` 不能只看 `changed`

`changed` 表示当前 View 的 bounds（`left`、`top`、`right`、`bottom` 四条边界）相对上次是否变化。子 View 的测量尺寸、可见性、外边距、布局方向或业务排序变化时，即使父 View 的边界没变，子 View 位置也可能要更新。测量或几何计算阶段应产出一份与完整输入绑定的坐标缓存，`onLayout()` 只读取这份缓存。

若 trace 显示同一帧发生多轮测量与摆放，要查调用栈和请求源。常见原因包括在 `onLayout()` 中再次调用 `requestLayout()`、父子约束互相依赖、权重或 `wrap_content` 协商，以及 Adapter 更新时同时改变布局参数。

### `onDraw()`：移除热路径分配

硬件加速时，UI 线程把 View 的绘制命令记录到 RenderNode 的 DisplayList。内容没有失效的 View 可以复用已有记录；标为 dirty（绘制内容已过期）的节点才需要重录。RenderThread 消费这些命令并准备窗口缓冲区，`onDraw()` 本身仍在 UI 线程执行。

热路径分配会增加分配器工作、缓存扰动和垃圾回收（GC）负载。少量分配不一定产生可见卡顿，结论要由 allocation recording（对象分配记录）、GC 轨道和帧时间共同证明。应移除可避免的逐帧分配，不能用一个对象数量阈值代替测量。

下面是波形 View 的结构节选：它在构造阶段创建绘制对象，在尺寸或数据变化时更新几何，`onDraw()` 只提交绘制命令；`rebuildWavePath()`、`drawGrid()` 等业务辅助方法没有展开。

```java
public final class WaveformView extends View {
    private final Paint mGridPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mWavePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path mWavePath = new Path();
    private final RectF mContentBounds = new RectF();

    public WaveformView(Context context, AttributeSet attrs) {
        super(context, attrs);
        mGridPaint.setColor(0x40FFFFFF);
        mWavePaint.setStyle(Paint.Style.STROKE);
        mWavePaint.setStrokeWidth(2f);
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        mContentBounds.set(
                getPaddingLeft(),
                getPaddingTop(),
                w - getPaddingRight(),
                h - getPaddingBottom());
        rebuildWavePath(mWavePath, mContentBounds);
    }

    public void setSamples(float[] samples) {
        copySamplesAndRebuildPath(samples, mWavePath, mContentBounds);
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        drawGrid(canvas, mContentBounds, mGridPaint);
        canvas.drawPath(mWavePath, mWavePaint);
    }
}
```

`setSamples()` 必须在 UI 线程调用，并复制或接管一份稳定数据，避免调用方在绘制期间修改数组。若采样持续高速到达，还要在上游合并更新；主线程每收到一个点就重建整条 Path，仍可能让记录成本超过预算。

常见分配源包括 `String.format()`、临时 `String`、装箱集合、`new RectF()`、`new Path()`、临时数组和每帧创建的 Shader。文字格式化应在数据变化时完成，数组和几何对象应复用。不变 Path 可以预计算；持续修改复杂 Path 即使没有 Java 分配，也可能增加 HWUI 的几何处理和 GPU 工作。

`Canvas.save()` / `restore()` 管理的是 Canvas 状态栈，不能按 Java 对象分配解释。嵌套 layer（离屏层）、复杂 clip（裁剪）和 transform（几何变换）仍有执行成本，应把状态保存范围限制在需要隔离的绘制段。

### 硬件加速、图层与 `setWillNotDraw`

#### 以当前 Canvas 判断绘制后端

`View.isHardwareAccelerated()` 表示 View 所在窗口启用了硬件加速；当前绘制可能仍使用软件 Canvas，例如把 View 画入 Bitmap。绘制代码需要分支时，应检查 `canvas.isHardwareAccelerated()`。

Android 10—17 已支持 `clipPath()`、`drawPicture()` 和 `drawVertices()` 等过去受 API 版本限制的调用，其中 `drawVertices()` 从 API 29 起支持硬件 Canvas。兼容性仍要按当前官方表逐项核对；例如官方表仍把 `Paint.setLinearText()` 和 `setMaskFilter()` 标为不支持。问题可能表现为空白、异常或像素错误，系统不会为所有不支持的调用统一切到软件绘制。

#### `LAYER_TYPE_NONE` 仍然复用 DisplayList

`setLayerType()` 控制单个 View 是否增加离屏图层，不控制整个窗口是否硬件加速。

| 类型 | Android 17 语义 | 合适场景 | 主要代价 |
| --- | --- | --- | --- |
| `LAYER_TYPE_NONE` | 正常使用 View 的 RenderNode / DisplayList，不强制离屏缓冲区 | 默认选择 | 无额外图层；内容失效时仍需重录 |
| `LAYER_TYPE_HARDWARE` | 在硬件加速窗口中渲染到硬件纹理 | 复杂子树的短时 alpha / transform 动画，或明确的合成效果 | GPU 内存、创建图层与内容失效后的重新栅格化 |
| `LAYER_TYPE_SOFTWARE` | 子树由 CPU 绘制到 Bitmap，再参与宿主窗口绘制 | 硬件 Canvas 不支持且已验证的局部兼容路径 | Bitmap 内存、CPU 栅格化、纹理上传 |

窗口未启用硬件加速时，`LAYER_TYPE_HARDWARE` 的行为与 `LAYER_TYPE_SOFTWARE` 相同；它不能在单个 View 上开启硬件加速。

静态 View 在默认模式下已经能复用 DisplayList，没有必要仅因“内容复杂”长期强制硬件图层。硬件图层适合内容保持不变、外层 `alpha` / `translation` / `scale` / `rotation` 持续变化的短时动画。动画同时修改 View 内容并频繁 `invalidate()` 时，图层仍要重新栅格化，收益可能消失。栅格化指把绘制命令转换成像素。

`ViewPropertyAnimator.withLayer()` 会在动画前启用硬件图层，并在结束后恢复原来的图层类型。先用 trace 确认属性动画的主要成本来自重复栅格化，再考虑下面的局部优化。

```java
view.animate()
        .alpha(0f)
        .translationY(-view.getHeight() / 4f)
        .setDuration(220L)
        .withLayer()
        .start();
```

硬件图层会占用与 View 面积、像素格式相关的 GPU 资源，大面积 View 尤其要检查内存和 RenderThread。`hasOverlappingRendering()` 只有在 View 内容不存在重叠绘制时才可返回 `false`；错误返回会改变透明度合成结果。

#### `setWillNotDraw(true)` 只跳过 ViewGroup 自身绘制

纯布局 `ViewGroup` 可以设置 `setWillNotDraw(true)`，让框架跳过它自己的 `onDraw()`。子 View 仍会通过 `dispatchDraw()` 绘制。容器需要画背景、分隔线、调试标记或其他自身内容时，应清除该标记。

下面只截取容器设置绘制标记的构造函数。完整的非抽象 `ViewGroup` 还必须实现 `onMeasure()` 和 `onLayout()`，这段代码不能单独编译。

```java
public final class FlowLayout extends ViewGroup {
    public FlowLayout(Context context, AttributeSet attrs) {
        super(context, attrs);
        setWillNotDraw(true);
    }
}
```

给 ViewGroup 设置背景时，框架可能调整绘制标记。`setWillNotDraw(true)` 不能覆盖所有背景行为；增加自身绘制后应明确改为 `false` 并验证结果。

### `invalidate()`、动画刷新与 `requestLayout()`

| API | 调用线程与时机 | 适用变化 | Android 17 边界 |
| --- | --- | --- | --- |
| `invalidate()` | UI 线程，安排后续绘制 | 像素内容、颜色、Path、Drawable | 标记 View 绘制内容失效，并向父级传播重绘区域（damage） |
| `postInvalidateOnAnimation()` | 挂载到窗口（attach）后可从非 UI 线程调用，在下一动画时间步派发 | 与显示帧节奏对齐的自绘动画 | 未 attach 时没有 `AttachInfo`，调用不会安排刷新 |
| `requestLayout()` | UI 线程，向父级传播布局请求 | 期望尺寸、子 View 尺寸或位置 | 清测量缓存，设置强制布局与失效标记，再安排 View 树遍历 |

API 21 起，`invalidate(Rect)` 和四坐标重载传入的 dirty rectangle（调用方指定的局部脏区域）会被忽略，两个公开 API 也已弃用。Android 17 的 `View.java` 内部仍会传播重绘区域，并按 RenderNode 更新 DisplayList；应用侧应调用无参 `invalidate()`，再通过拆分 View 或 RenderNode 改变重录粒度。

下面的 setter 区分“只改像素”和“改变尺寸”。

```java
public void setWaveColor(int color) {
    if (mWavePaint.getColor() == color) return;
    mWavePaint.setColor(color);
    invalidate();
}

public void setLabelText(String text) {
    if (Objects.equals(mLabelText, text)) return;
    mLabelText = text;
    mContentVersion++;
    requestLayout();
    invalidate();
}
```

`requestLayout()` 不保证自动补齐所有业务绘制状态，因此尺寸与像素都变化时可以同时调用两者。若文字变化但固定边界与现有基线能容纳新内容，只需重建文字布局并调用 `invalidate()`；是否调用 `requestLayout()` 由尺寸契约决定。

#### 连续动画要有生命周期

在 `onDraw()` 中无条件调用 `invalidate()` 会持续请求后续帧，即使 View 不可见或动画已经完成。自绘动画可以使用 `postInvalidateOnAnimation()`，但必须有明确的运行状态，并在 detach、不可见或终止条件到达时停止。

下面的骨架只在动画活跃时请求下一帧。

```java
@Override
protected void onDraw(Canvas canvas) {
    drawFrame(canvas, mProgress);
    if (mRunning) {
        postInvalidateOnAnimation();
    }
}

@Override
protected void onDetachedFromWindow() {
    mRunning = false;
    super.onDetachedFromWindow();
}
```

这段骨架只展示从窗口分离时的停止逻辑。实际组件还要在不可见和业务终止时更新 `mRunning`；若改用 Animator，也要在对应生命周期节点取消动画。

`ValueAnimator` 能提供基于时钟的进度和取消机制，但它的更新回调仍可能每帧触发重绘。选择 Animator 是为了使用明确的时间模型和生命周期，并不会减少刷新次数。

#### `ViewCompat.postInvalidateOnAnimation()` 的版本位置

平台 `postInvalidateOnAnimation()` 从 API 16 提供。本文适用范围为 Android 10—17，可以直接调用平台 API。若这段代码还要共享给 API 15 或更低的项目，可考虑 `ViewCompat.postInvalidateOnAnimation()`，但要先确认项目采用的 AndroidX Core 版本仍支持该 `minSdk`。兼容层的选择不会改变 Android 17 的调度语义。

### 手动 `RenderNode`：按更新频率划分节点

公开 `RenderNode` 从 API 29 提供。每个 View 已经由框架持有一个 RenderNode，手动增加节点只适合自定义 View 内面积较大、更新频率不同且能独立记录的区域。若小图元很多、每帧全部变化，或软件 Canvas 必须完整支持，额外节点的管理成本可能超过复用收益。

下面的示例把静态网格和动态波形分成两个节点。节点在字段初始化时创建，硬件 Canvas 走 `drawRenderNode()`，软件 Canvas 直接调用原绘制函数，避免截图或 Bitmap 绘制得到空白。

```java
private final RenderNode mGridNode = new RenderNode("wave-grid");
private final RenderNode mWaveNode = new RenderNode("wave-data");
private boolean mGridDirty = true;
private boolean mWaveDirty = true;

@Override
protected void onSizeChanged(int w, int h, int oldw, int oldh) {
    super.onSizeChanged(w, h, oldw, oldh);
    mGridNode.setPosition(0, 0, w, h);
    mWaveNode.setPosition(0, 0, w, h);
    mGridDirty = true;
    mWaveDirty = true;
}

private void recordGridNode() {
    RecordingCanvas recordingCanvas = mGridNode.beginRecording();
    try {
        drawGrid(recordingCanvas);
    } finally {
        mGridNode.endRecording();
    }
}

private void recordWaveNode() {
    RecordingCanvas recordingCanvas = mWaveNode.beginRecording();
    try {
        drawWave(recordingCanvas);
    } finally {
        mWaveNode.endRecording();
    }
}

@Override
protected void onDraw(Canvas canvas) {
    if (!canvas.isHardwareAccelerated()) {
        drawGrid(canvas);
        drawWave(canvas);
        return;
    }

    if (mGridDirty || !mGridNode.hasDisplayList()) {
        recordGridNode();
        mGridDirty = false;
    }
    if (mWaveDirty || !mWaveNode.hasDisplayList()) {
        recordWaveNode();
        mWaveDirty = false;
    }

    canvas.drawRenderNode(mGridNode);
    canvas.drawRenderNode(mWaveNode);
}
```

内容更新时设置对应的失效标记并调用 `invalidate()`；尺寸变化要更新两个节点的位置。节点长期不再使用时可以调用 `discardDisplayList()` 释放 DisplayList 持有的原生资源。系统发现节点不再被绘制时也可能自动调用该方法，显式释放适合生命周期由业务代码明确控制的节点。

RenderNode 的 `translation`、`scale`、`rotation` 和 `alpha` 属性可以在不重录 DisplayList 的情况下更新。`setUseCompositingLayer(true, paint)` 会强制增加中间合成缓冲区，公开文档推荐保留默认值 `false`。当中间层能降低开销，或 `alpha` 与重叠绘制的组合要求使用中间层时，RenderNode 会自行建立合成层。只有特效要求或测量结果能证明收益时才应强制开启。

### Perfetto：区分 UI 记录、RenderThread 与显示出口

系统 trace 不会自动为每个自定义 View 生成稳定的 `onDraw` slice（有起止时间的工作区间）。`debug.hwui.profile` 用于生成 Profile HWUI Rendering 柱状图，不能替代 View 级 trace。定位目标 View 时，可以用自定义区间（trace section）包住热方法。

下面的埋点代码给 `onDraw()` 添加可在 Perfetto 中搜索的区间，`finally` 保证发生异常时也会关闭 section。

```java
@Override
protected void onDraw(Canvas canvas) {
    Trace.beginSection("WaveformView#onDraw");
    try {
        drawGrid(canvas, mContentBounds, mGridPaint);
        canvas.drawPath(mWavePath, mWavePaint);
    } finally {
        Trace.endSection();
    }
}
```

录制时要让配置收集目标进程的应用 trace section，并启用 `view`、`gfx`、`hwui`、线程调度和 FrameTimeline 数据。Macrobenchmark 会自动收集自定义区间；使用 systrace 命令行时要通过 `-a <package>` 指定应用。FrameTimeline 用于把应用帧与 SurfaceFlinger 的实际显示结果对应起来。性能判断按四段进行：

1. `WaveformView#onDraw` 长：检查应用绘制代码、CPU Bitmap、文字布局、Path 构建和同步等待。
2. UI 记录正常，RenderThread `DrawFrame` 长：先区分 CPU 执行与 runnable 时间，后者表示线程已经就绪但还在等待 CPU。然后检查 `dequeueBuffer`（申请可写缓冲区）、Skia 渲染库 / GPU 工作和 fence（跨 CPU、GPU、显示设备传递完成状态的同步对象），不能只写成“GPU 慢”。
3. `queueBuffer()` 之前正常，目标图层的 `BufferTX` / latch 晚：检查 BLAST、transaction readiness（事务依赖是否就绪）和 acquire fence（生产者是否已写完缓冲区）。latch 表示 SurfaceFlinger 选中并接收本帧缓冲区。
4. 应用与 latch 都按时，actual present（实际显示时间）仍超时：检查 SurfaceFlinger 合成、HWC、Display HAL（显示硬件抽象层）和 present timing。

对象分配要用 allocation recording 找调用栈，再与同一时间窗的 GC、主线程状态和 FrameTimeline 对齐。HeapTaskDaemon 是 Android Runtime 的后台堆任务线程；它出现 GC 工作只说明进程正在回收内存。没有主线程暂停或资源竞争证据时，不能把该帧直接归因给 `onDraw()` 分配。

### 验收清单

- `onMeasure()` 的昂贵计算是否由完整输入保护，数据只改颜色时有没有误调 `requestLayout()`。
- `onLayout()` 是否依赖子 View 尺寸、可见性、外边距和布局方向，是否在摆放过程中再次请求布局。
- `onDraw()` 是否含临时对象、格式化、同步 I/O、Bitmap CPU 绘制或逐帧重建不变几何。
- 默认 `LAYER_TYPE_NONE` 是否已经满足需求；硬件 / 软件图层是否有明确场景、开启区间和内存证据。
- `setWillNotDraw(true)` 是否只用于没有自身视觉内容的 ViewGroup。
- 自绘动画是否使用显示帧节奏，并在从窗口分离、不可见和终止状态停止。
- 手动 RenderNode 是否让独立更新区域分别记录，并为软件 Canvas 保留正确输出。
- UI 线程、RenderThread、BLAST、SurfaceFlinger、HWC 与 actual present 是否用同一帧证据关联。

## 全文小结

View 优化先区分布局失效和绘制失效：层级、inflate、测量与 `requestLayout()` 决定哪些节点重新布局，绘制分配、缓存和 RenderNode 决定哪些内容需要重新记录。减少其中一段工作后，还要沿同一帧检查 RenderThread、缓冲区与实际呈现时间，确认收益没有被图形内存增长或其他阶段的等待抵消。

## 源码与文档

- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)：`requestLayout()`、绘制失效、图层类型、`setWillNotDraw()` 与 View RenderNode 更新。
- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java) 与 [`ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)：View 树遍历、测量 / 摆放 / 绘制与 HWUI 同步入口。
- [Android 17 `RenderNode.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)、[`RecordingCanvas.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RecordingCanvas.java) 与 [`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)：DisplayList 记录、节点属性与 UI 到 RenderThread 的边界。
- [Optimize a custom view](https://developer.android.com/develop/ui/views/layout/custom-views/optimizing-view)：热路径、分配和布局遍历的官方建议。
- [Hardware acceleration](https://developer.android.com/topic/performance/hardware-accel)：DisplayList 模型、Canvas API 支持表和 View 图层契约。
- [`View` API](https://developer.android.com/reference/android/view/View) 与 [`RenderNode` API](https://developer.android.com/reference/android/graphics/RenderNode)：dirty rectangle、动画刷新、公开 RenderNode 和软件 Canvas 边界。
- [Slow rendering](https://developer.android.com/topic/performance/vitals/render)、[Perfetto system tracing](https://perfetto.dev/docs/getting-started/system-tracing) 与 [Define custom events](https://developer.android.com/topic/performance/tracing/custom-events)：UI 记录、RenderThread、GC、系统 trace 与应用自定义区间的观测入口。
