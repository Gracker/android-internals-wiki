---
title: "Compose ↔ View 互操作性能实战"
chapter: "22.41"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, interop, androidview, composeview, rendering-performance, migration]
related_chapters: ["22.3", "22.15", "22.22", "22.31"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "AOSP结构/官方文档/章节深挖"
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_draft_polish_at: "2026-08-05T19:35:05+08:00"
last_draft_polish_run_id: "20260805-193505-draft-polish-8643c743"
last_verified: "2026-08-05"
last_verified_against: "Android android-17.0.0_r1; AndroidX Compose BOM 2026.06.01 / UI Runtime Foundation 1.11.4; Kotlin/Compose compiler 2.4.10; android17-6.18 kernel notes only for device-side mechanisms"
confidence: medium-high
reviewed_date: "2026-08-05"
reviewed_by: hermes-aiw-review-finalize-apply
last_review_finalize_at: "2026-08-05T20:06:52+08:00"
last_review_finalize_run_id: "20260805-200652-bf2f8aa5"
sources:
- type: reference
  path: 'Android developer documentation: Views in Compose / Compose in Views / Compose testing interoperability'
- type: official
  path: AndroidX Compose UI, UI ViewBinding, Foundation 1.11.4 source artifacts and public API references
- type: aosp
  path: AOSP android-17.0.0_r1 ViewRootImpl, Choreographer, SurfaceView, TextureView, HWUI WebViewFunctor
---

# 22.41 Compose ↔ View 互操作性能实战

Compose 与 View 互操作有两个方向：

- `AndroidView` 把一个传统 `View` 接入 Compose 的布局、绘制、输入与生命周期；
- `ComposeView` 把一个 Compose 根接入既有 View 树。

两种方向都要付桥接成本，但成本来源不同。`AndroidView` 关注 View 创建、`measure/layout/draw`、事件转发和复用；`ComposeView` 关注 Composition 根、View owner、状态保存与池化容器中的处置时机。只用“混合页面更慢”概括，会漏掉可复用实例、无效 setter、嵌套滚动和独立 Surface 等差异。

## 版本基线与术语校正

版本基线如下：

| 层级 | 基线 | 适用范围 |
| --- | --- | --- |
| Android platform | Android 17 / API 37 / `android-17.0.0_r1` | ViewRoot、HWUI、Surface、帧率投票与显示路径 |
| Jetpack Compose | Compose BOM 2026.06.01；UI、Runtime、Foundation 1.11.4 | `AndroidView`、`ComposeView`、复用、追踪与测试 |
| Kotlin / Compose compiler | Kotlin 2.4.10 / Compose compiler plugin 2.4.10 | 编译报告与生成代码边界 |
| Android kernel | `android17-6.18-2026-06_r6` | 调度、fence 等设备侧机制；不决定互操作 API 语义 |

Compose 独立于 Android platform 发布。`android-17.0.0_r1` 能固定 `ViewRootImpl`、`SurfaceView`、`TextureView` 和 HWUI，不能固定 AndroidX Compose 1.11.4 的实现；Compose 的实现要按对应 artifact 源码核查。

Google Maven 中的 Compose BOM 2026.06.01 把 UI、Runtime 和 Foundation 都约束为 1.11.4。BOM 只负责 AndroidX library 版本，Kotlin 2.4.10 与 Compose compiler plugin 2.4.10 仍按 Kotlin 工具链配置。

三项常见说法需要收窄：

| 常见说法 | Compose UI 1.11.4 中的边界 |
| --- | --- |
| `ViewTreeHostingRegistry` 优化 | 公开类型名是实验性的 `ComposeViewContext`；内部另有 `ViewTreeHostDefaultProvider`。当前源码没有名为 `ViewTreeHostingRegistry` 的通用优化 API |
| `PausableComposition` 让 `AndroidView` 区域变快 | 可暂停的预组合能帮助 Lazy/Subcompose 预取分批执行 Composition；View 的 `factory` 一旦调用，创建、测量和绘制成本仍由 View 负责 |
| `Modifier.Node` 优化 View 事件链 | Node 架构能减少 Compose modifier 一侧的分配与更新成本；`MotionEvent` 仍要跨过 `pointerInteropFilter` 并进入 View 的 dispatch 链 |

性能分析需要分别判断 Compose 侧成本、View 侧成本和显示系统成本，不能从某个 Compose 版本特性直接推导整个混合页面提速。

## 一、两种互操作方向经过哪些对象

### `AndroidView`：一个 LayoutNode 代理一个 View holder

Compose UI 1.11.4 的 `AndroidView` 会创建 `ViewFactoryHolder`，其父类 `AndroidViewHolder` 是一个 `ViewGroup`。holder 同时关联一个 Compose `LayoutNode`：

1. Compose measure policy 把 `Constraints` 与 View `LayoutParams` 合成为 `MeasureSpec`；
2. holder 调用被包装 View 的 `measure()`；
3. Compose 用 View 的 `measuredWidth`、`measuredHeight` 确定 LayoutNode 尺寸；
4. 放置阶段调用 View 的 `layout()`；
5. Compose draw modifier 经 `AndroidViewsHandler` 调用 holder 的 `draw()`；
6. 指针、nested scroll、semantics、insets 与 bring-into-view 经过各自的互操作桥。

View 并没有转成 composable。View 的测量、布局、绘制和事件模型仍然存在，外层调度则由 Compose `LayoutNode` 接管。

### `ComposeView`：一个 ViewGroup 承载一个 Compose 根

`AbstractComposeView` 是 `ViewGroup`，内部只允许 Compose 创建的 `AndroidComposeView` 子节点。`ComposeView.setContent` 会保存 content；View 已附着时立即保证 Composition 存在，尚未附着时通常等到首次 attach。创建 Composition 时，父 CompositionContext 按以下顺序解析：

1. 显式设置的 parent context；
2. View tree 中可找到的 composition context；
3. 尚存活的缓存 context；
4. 当前 window 的 `Recomposer`。

同一窗口中的多个 `ComposeView` 通常会找到相同的 window `Recomposer`。这不等于它们共享一个 Compose 根：每个实例仍有自己的 Composition、`AndroidComposeView`、LayoutNode 树、semantics owner、状态注册和 View 测量边界。

### 普通互操作不会自动增加一个可见 Surface

只包含普通 View 与 Compose 内容时，`AndroidView` 和 `ComposeView` 仍走标准 App Window：

`Snapshot / Recomposer → Compose measure/layout/draw → AndroidComposeView → ViewRootImpl / HWUI → RenderThread → App Window BLASTBufferQueue → SurfaceFlinger → HWC → present`

桥接本身会增加主线程对象与调用，不会凭空创建一条独立 buffer stream。`SurfaceView` 会维护独立的内容 Surface、BufferQueue 和 SurfaceFlinger 子层；`TextureView` 的外部 buffer 由宿主 HWUI 采样进 App Window，输入流通常不会成为独立可见 layer。标准硬件加速 WebView 的页面主体也经 functor 合入宿主窗口，网页视频、受保护内容或自定义 Surface 才可能增加媒体 overlay。地图、视频和相机控件使用哪种拓扑取决于控件实现，排查时应以 Producer、BufferQueue 和 layer tree 为证据。

## 二、`AndroidView` 的成本模型

### `factory`、`update`、`onReset` 与 `onRelease`

官方契约和 1.11.4 源码给出的生命周期如下：

| 回调 | 调用语义 | 适合执行的工作 |
| --- | --- | --- |
| `factory` | 每个 View 实例调用一次，在 UI 线程执行 | 构造 View、一次性属性、注册长期 listener |
| `update` | `factory` 后至少调用一次；读取的 Compose State 改变后可再次调用，在 UI 线程执行 | 把当前 UI model 以幂等方式写入 View |
| `onReset` | 使用复用 overload 时，在兼容实例进入复用前调用 | 清除瞬时状态、动画、按压、临时 listener 或旧 item 内容 |
| `onRelease` | 实例永久离开 Compose 管理时调用一次 | 释放播放器、WebView、传感器、线程、回调等资源 |

`factory` 里 inflate 一个复杂 XML、构造 WebView 或启动播放器，都直接占用当前 UI 线程时间。把 View 预先放进 `remember` 不能绕过这个成本，还可能破坏 owner、attachment 和复用语义。官方建议在 `factory` 内创建 View。

`AndroidViewHolder` 会用 `OwnerSnapshotObserver` 观察 `update` 内部读取的 Snapshot State。假设 `title` 与 `image` 是两个由 State 委托的属性，而 block 只读取 `model.title`，`model.image` 变化不会触发这次观察。普通参数捕获走另一条路径：宿主 composable 重组并提供新的 `update` block 时，holder 也会执行新 block。无论由哪条路径触发，昂贵 setter 都可能把一次轻量状态更新扩大成 View 的重新布局、重绘或资源请求。

下面的宿主实现展示一次性 listener、幂等更新和资源释放各自所在的位置。

```kotlin
@Composable
fun LegacyChartHost(
    model: ChartModel,
    onSelectionChanged: (Long) -> Unit,
    modifier: Modifier = Modifier,
) {
    val currentSelectionCallback by rememberUpdatedState(onSelectionChanged)

    AndroidView(
        modifier = modifier,
        factory = { context ->
            LegacyChartView(context).apply {
                setOnSelectionChangedListener { id ->
                    currentSelectionCallback(id)
                }
            }
        },
        update = { view ->
            if (view.model !== model) {
                view.model = model
            }
        },
        onRelease = { view ->
            view.setOnSelectionChangedListener(null)
            view.release()
        },
    )
}
```

listener 只安装一次，并通过 `rememberUpdatedState` 取得当前回调；`update` 在引用未变化时跳过 setter；终止回调放在 `onRelease`。若 model 是可变对象且原地更新，引用比较不足以识别内容变化，应改用不可变 UI model、版本号或字段比较。

### `AndroidViewBinding` 沿用同一套桥接与复用语义

`AndroidViewBinding` 来自 `androidx.compose.ui:ui-viewbinding:1.11.4`。它调用生成的 ViewBinding factory 完成 inflate，把 binding 保存在根 View 上，再用 `AndroidView` 承载这个根节点。因此，它减少的是手写 `findViewById` 和类型转换，不会省去 XML inflate、View measure/layout/draw 或输入桥的成本。

1.11.4 同样提供带 `onReset`、`onRelease` 的 overload。非空 `onReset` 才允许 View 与 binding 在兼容的 Lazy item 之间复用；两个回调的时序与 `AndroidView` 一致。布局包含 `FragmentContainerView` 时还有额外边界：

- `AndroidViewBinding` 会优先使用父 Fragment 的 `LayoutInflater`，让 XML 中的 Fragment 成为正确的 child Fragment；
- release 时先运行调用方的 `onRelease`，再遍历根布局中的 `FragmentContainerView`；
- 找到 Fragment 且 `FragmentManager.isStateSaved == false` 时，内部用 `commitNow` 移除；状态已经保存时不会强行提交事务；
- 官方源码不建议为承载 Fragment 的 binding 刻意启用 Lazy 复用，Fragment 有独立的 View lifecycle，通常也不处于能稳定获益的复用场景。

因此，普通 XML item 可以按 `AndroidView` 的复用方法处理；包含 Fragment 的布局则应优先保证 FragmentManager、状态保存和销毁顺序正确，不能只看 View 创建次数。

### Compose 状态变化不等于 View 一定重新布局

一次 Compose State 变化会触发哪些工作，取决于读取位置和 setter 行为：

- State 在 `update` 中被读取：Snapshot observer 会安排 `update`；
- setter 只调用 `invalidate()`：`AndroidViewHolder` 最终调用 `LayoutNode.invalidateLayer()`；原始 dirty rect 不会原样传到 Compose layer；
- setter 调用 `requestLayout()`：`AndroidViewsHandler.requestLayout()` 找到 holder 对应的 LayoutNode，并调用 `requestRemeasure()`；
- View 的测量尺寸变化：Compose 在 remeasure 后重新放置受影响节点；
- State 只在父级 modifier 或布局中读取：可能改变 Compose 布局，却不运行无关的 View setter。

Compose UI 1.11.4 还处理了绘制期间发生的 View invalidation。`AndroidViewHolder` 若正在 draw，会用 `postOnAnimation` 把 layer invalidation 延后到下一帧，避免同一帧重复重画同一内容。

因此，分析性能时要区分四个计数：`update` 次数、View `requestLayout` 次数、View `invalidate` 次数和最终帧数。重组计数无法替代后三项。

### 避免 View → Compose → View 的反馈循环

双向控件容易形成下面的循环：

1. Compose 把值写入 View；
2. View setter 同步触发 listener；
3. listener 又写 Compose State；
4. 新 State 促使 `update` 再写 View。

处理方式是确定一个状态所有者，并在两边都做等值保护。下面以传统滑块为例。

```kotlin
@Composable
fun LegacySliderHost(
    value: Int,
    onValueChange: (Int) -> Unit,
) {
    val currentOnValueChange by rememberUpdatedState(onValueChange)

    AndroidView(
        factory = { context ->
            LegacySlider(context).apply {
                setOnValueChangedListener { newValue, fromUser ->
                    if (fromUser) {
                        currentOnValueChange(newValue)
                    }
                }
            }
        },
        update = { slider ->
            if (slider.value != value) {
                slider.value = value
            }
        },
        onRelease = { slider ->
            slider.setOnValueChangedListener(null)
        },
    )
}
```

Compose 参数是状态源；View 只上报用户操作；`update` 避免重复赋值。如果旧控件没有 `fromUser` 参数，可以在宿主维护“正在应用外部状态”的标记，或在 listener 中比较新旧值。不要在 `update` 内无条件回写 Compose State。

### View 的成本要按操作拆分

| 操作 | 常见主线程成本 | 可能引起的后续工作 |
| --- | --- | --- |
| inflate / constructor | XML 解析、反射/构造、资源读取、子 View 创建 | measure、layout、首次 draw |
| setter | 文本测量、drawable 更新、listener 通知 | `requestLayout()` 或 `invalidate()` |
| measure | ViewGroup 遍历、文本/图片尺寸计算 | 父子布局变化 |
| layout | 坐标分配、滚动/焦点/Insets 相关处理 | draw、位置回调 |
| draw | Canvas 记录、图片上传、复杂 path/shader | RenderThread/GPU |
| input bridge | MotionEvent 转发、手势识别、nested scroll | 状态更新与新帧 |
| release | 停止异步任务、解绑 listener、销毁 native 资源 | 回收抖动或泄漏风险 |

固定控件尺寸能减少一部分测量波动，但不能消除 View 自身 measure。设置同一个文本也未必是空操作，取决于控件实现；业务层的幂等保护应以目标 View 源码或基准为依据。

## 三、Lazy 容器中的 `AndroidView` 复用

### 不提供 `onReset` 时不会复用 View 实例

Compose UI 提供两组 `AndroidView` overload。没有 `onReset` 的版本在 reusable content 中不会复用 View；带非空 `onReset` 的版本会创建 reusable node。兼容性由 composable group 结构决定，不只由业务 `key` 决定。

下面的 item 宿主明确区分重置和永久释放。

```kotlin
@Composable
fun LegacyVideoRow(
    item: VideoRowModel,
    modifier: Modifier = Modifier,
) {
    AndroidView(
        modifier = modifier,
        factory = { context -> LegacyVideoPreview(context) },
        update = { preview ->
            preview.bind(item)
        },
        onReset = { preview ->
            preview.pause()
            preview.clearTransientUi()
            preview.setPressed(false)
        },
        onRelease = { preview ->
            preview.release()
        },
    )
}
```

`onReset` 之后可能进入暂时 deactivated 状态，下一次 `update` 不保证立刻发生，所以 reset 后的 View 必须处于安全、无旧内容泄露的状态。`onRelease` 具有终止语义，同一实例后续不会再复用。

### 复用时应清理什么

复用检查至少覆盖：

- 旧 item 的 listener、tag、selection、pressed、activated 与 accessibility 文案；
- 尚在运行的 animator、runnable、图片请求、协程或播放器任务；
- `RecyclerView`、WebView、地图、视频组件自己的滚动与资源状态；
- transient state 和焦点；
- 与旧 LifecycleOwner、SavedStateRegistryOwner 或业务 owner 绑定的订阅；
- 失败占位、错误文案与内容描述。

清理过少会串 item；清理过度会让每次复用接近重新创建。资源型 View 可保留可复用引擎，把 item 专属会话停在 `onReset`，把 native 引擎销毁留到 `onRelease`，前提是组件 API 明确支持这种生命周期。

### 列表性能要同时记录创建数和绑定数

只观察平均帧率很难定位复用是否生效。建议为每种 View 记录：

- `factory` 调用数；
- `onReset`、`update`、`onRelease` 调用数；
- 单次 inflate/create 与 bind 的 wall time；
- `requestLayout()` 和 `invalidate()` 频率；
- 滚动期间 allocation、GC 与 retained instance；
- UI thread、RenderThread 与 FrameTimeline deadline miss。

在同一数据集和相同滚动脚本下，`factory` 数明显下降而 bind 时间稳定，才能说明复用减少了创建成本。若 `onReset + update` 比新建还贵，应回到控件实现调整复用边界。

## 四、`ComposeView` 嵌入 View 树

### Composition 处置策略

Compose UI 1.11.4 的默认策略是 `DisposeOnDetachedFromWindowOrReleasedFromPool`：

- 普通 View 树中，detach 会处置 Composition；
- 位于 `RecyclerView` 等 pooling container 时，短暂 detach 会保留 Composition；
- item 从池中永久释放、容器 detach 或池满丢弃时，pooling listener 处置 Composition。

Fragment 的 View 生命周期短于 Fragment 实例生命周期，推荐把 Composition 绑定到下一次附着时找到的 ViewTree LifecycleOwner。下面的写法适用于 Fragment view。

```kotlin
override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
    val composeView = view.findViewById<ComposeView>(R.id.compose_content)
    composeView.setViewCompositionStrategy(
        ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed
    )
    composeView.setContent {
        AppTheme {
            ProfileContent()
        }
    }
}
```

该策略会在 Fragment 的 view lifecycle `ON_DESTROY` 时处置 Composition，避免 Fragment 保留期间继续持有已销毁 View 树。自定义 View owner 或手工创建窗口中仍需核对 ViewTreeLifecycleOwner 与 SavedStateRegistryOwner 是否存在。

### RecyclerView 中不要在临时回收时盲目 dispose

默认 pooling 策略就是为 RecyclerView 临时 detach 设计的。`onViewRecycled()` 每次都调用 `disposeComposition()`，会丢失池化带来的保留收益，并在列表再次滚回该位置时重新创建整个 Composition。

一种稳定写法是在 holder 初始化时调用一次 `setContent`，bind 时只更新 holder 持有的 Compose State。

```kotlin
class ComposeItemHolder(
    parent: ViewGroup,
) : RecyclerView.ViewHolder(ComposeView(parent.context)) {

    private var model by mutableStateOf<ItemUiModel?>(null)

    init {
        (itemView as ComposeView).apply {
            setViewCompositionStrategy(
                ViewCompositionStrategy.DisposeOnDetachedFromWindowOrReleasedFromPool
            )
            setContent {
                AppTheme {
                    model?.let { FeedRow(it) }
                }
            }
        }
    }

    fun bind(newModel: ItemUiModel) {
        model = newModel
    }

    fun clearBinding() {
        model = null
    }
}
```

`setContent` 只执行一次，RecyclerView bind 转为 State 更新。`clearBinding` 可清除旧 item 引用，但不处置 Composition。若 item 含 `remember` 的 item 专属状态，应使用稳定 key、把状态提升到列表 model，或明确设计保存/恢复策略。

### 多个 ComposeView 的内存模型

“每个 ComposeView 都有一个 Recomposer”不符合默认 window 路径。同一窗口通常共享 window `Recomposer`；每个 ComposeView 仍保留以下实例级对象：

- 自己的 Composition 和 slot table；
- `AndroidComposeView` 与 LayoutNode 树；
- semantics、focus、pointer input 和 snapshot observation 状态；
- 每个根的 measure/layout/draw 边界；
- SaveableStateRegistry 接入与注册内容；
- 业务层 `remember`、effect、图片和缓存对象。

因此，十个很小的 ComposeView 与一个包含十个 child 的 ComposeView 在内存、调度和 inspector 结构上不会相同。差额没有跨项目固定字节数，应在目标版本上用 heap dump、allocation profile 和 Macrobenchmark 测量。

多个静态 `ComposeView` 还要使用唯一 View ID，官方文档明确要求这样才能让 `savedInstanceState` 正确工作。RecyclerView item 内的局部 UI 状态更适合提升到稳定 item model；依赖 holder 临时 ID 保存业务状态，会受到复用和进程重建影响。

### Compose UI 1.11 的 `ComposeViewContext`

Compose UI 1.11 引入实验性的 `ComposeViewContext`。当前源码会让 owner 兼容的多个 ComposeView 共享一部分宿主对象，例如：

- configuration state 与资源 ID / vector cache；
- font loader / resolver；
- accessibility、clipboard、haptic 和 window info 相关对象；
- shared draw scope、CanvasHolder 等内部结构。

共享范围受 View `Context`、LifecycleOwner、SavedStateRegistryOwner 和部分 feature flag 约束。Fragment 建立新的 owner 边界后，查找可能在该处停止或创建新的 context。每个 Composition 的业务状态不会因此合并。

实验 API 还允许用已附着 View 创建 `ComposeViewContext`，再为尚未 attach 的 ComposeView 调用 `createComposition(context)`，可用于 RecyclerView 预组合。若预创建的 ComposeView 从未附着，调用方必须执行 `disposeComposition()`。这属于显式预热策略，不能直接当成所有 ComposeView 的自动预取保证。

## 五、RecyclerView 与 Lazy 容器混合滚动

### 帧预算属于整帧共享资源

常见刷新率对应的理论周期如下：

| 刷新率 | 周期 |
| --- | ---: |
| 60 Hz | 16.67 ms |
| 90 Hz | 11.11 ms |
| 120 Hz | 8.33 ms |

这些时间由输入、动画、Compose、View traversal、RenderThread、GPU、SurfaceFlinger 和显示阶段共同使用。不能给 Compose 8 ms、View 8 ms，再把两者相加当成 60 Hz 安全预算；FrameTimeline 的 deadline 才是当前帧的系统约束。

### `AndroidView` 放进 LazyColumn

适合的做法包括：

- 提供非空 `onReset`，验证实例复用；
- 给 item 使用稳定 `key` 和合理 `contentType`；
- 避免 bind 时无条件请求布局；
- View 高度尽量稳定，异步内容到达后减少反复改尺寸；
- 在 reset 中停止旧 item 动画和异步请求；
- 在 release 中关闭不可复用资源。

若 AndroidView 自己又包含竖向 RecyclerView，外层 LazyColumn 与内层列表会争夺滚动、预取、测量和可见性管理。短内容可让内层一次性展开，但大数据会失去虚拟化收益；大数据场景通常应选一个竖向滚动 owner。

### ComposeView 放进 RecyclerView

适合的做法包括：

- holder 初始化时 `setContent` 一次；
- bind 只更新稳定、不可变的 UI model；
- 默认 pooling strategy 保留在临时 detach 期间的 Composition；
- item 状态按稳定 ID 存在 model/ViewModel，而不依赖 holder 位置；
- 记录 holder create、bind、recomposition 与 measure 次数；
- 为图片、富文本和自定义布局建立单独 trace。

RecyclerView 的预取与 Compose 的 composition/layout 各自有调度成本。Compose UI 1.11 的实验预组合能力可提前完成一部分 Composition，但预热过多 item 会把 CPU 和内存压力前移。预取数量应由滚动速度、item 成本和设备档位共同决定。

### nested scroll 桥能传递增量，不能解决所有 ownership 冲突

`AndroidViewHolder` 实现 `NestedScrollingParent3`，当内部 View 开启 nested scrolling 时，会把 pre-scroll、post-scroll 和 fling 数据交给 Compose dispatcher。它能让很多标准嵌套滚动场景工作。

以下情况仍需专项验证：

- 两个同方向、都可无限滚动的容器；
- 内层使用 `requestDisallowInterceptTouchEvent` 改变手势 owner；
- RecyclerView item 内嵌高度不受限的 LazyColumn；
- fling 交接时两边都启动衰减动画；
- overscroll、pull-to-refresh、AppBar 和 accessibility scroll 同时存在；
- SurfaceView/地图等组件还有自己的手势和帧循环。

最稳妥的页面结构通常只有一个主竖向滚动 owner。横向 carousel 放在竖向列表中属于常见且可测的例外。

### 分批迁移与全量迁移怎样比较

迁移策略应按风险和测量结果选择：

| 策略 | 优点 | 风险 | 适合场景 |
| --- | --- | --- | --- |
| 页面级 ComposeView | owner 和回退边界清楚；便于 A/B | 新建一个 Compose 根；页面内仍可能调用旧 View | 独立新页面、功能边界完整 |
| Fragment 内局部替换 | 改动范围小；可逐块验证 | 多个根、焦点/状态/布局交界增多 | 老页面中低耦合区域 |
| RecyclerView item 使用 ComposeView | 可逐 item type 迁移 | 高频 bind、池化、状态恢复要求高 | item 类型少且基准完备 |
| Compose 中保留 AndroidView | 可复用成熟地图、视频、编辑器 | View 创建、布局、事件和资源生命周期仍在 | 暂无等价 Compose 组件 |
| 一次全量迁移 | 根与滚动 owner 容易统一 | 回归面大，难定位差异来源 | 页面较小、测试充分、旧实现负担高 |

全 Compose 导航栈也不保证更快；它能减少部分 View/Compose 边界，却可能引入新的 composition、导航、图片或布局成本。每个阶段都应和同一用户旅程、相同数据与 release 构建比较。

## 六、Inspector、Compiler Metrics 与 Perfetto

### Layout Inspector 负责结构和重组线索

混合页面在 Layout Inspector 中会同时出现 View hierarchy 与 Compose 节点。`AndroidView` 仍能在 View 一侧找到被包装实例；`ComposeView` 下面会显示对应 Compose 根和 semantics/layout 信息。

它适合回答：

- 页面有多少 Compose 根和 AndroidView；
- 某个 composable 是否频繁重组或跳过；
- View/Compose 边界的尺寸、位置和 owner 是否符合预期；
- 相同 item 是否不断创建新根。

Inspector 会插桩并增加开销，不应在连接 Inspector 的进程里采集性能结论。先用它定位对象，再关闭工具运行 release Macrobenchmark 与 Perfetto。

### Compose Compiler Metrics 看不到 View 内部成本

Compiler reports 会把 `AndroidView` 宿主 composable 当作普通 composable 分析，可显示 restartable、skippable 与参数稳定性。它不会提供：

- `factory` 调用了多少次；
- View `measure/layout/draw` 花了多久；
- setter 是否触发 `requestLayout()`；
- listener 是否形成反馈循环；
- RecyclerView 是否复用了 holder；
- SurfaceView Producer 是否按时提交 buffer。

因此，报告适合查宿主函数的生成属性，View 内部需要自定义 trace、计数器和系统 trace。

### 自定义 trace 标出桥接业务工作

下面用 `androidx.tracing.trace` 标记昂贵的 View 更新和 item bind。

```kotlin
AndroidView(
    factory = { context ->
        trace("LegacyMap.factory") {
            LegacyMapView(context)
        }
    },
    update = { mapView ->
        trace("LegacyMap.update") {
            mapView.render(model)
        }
    },
    onRelease = { mapView ->
        trace("LegacyMap.release") {
            mapView.destroy()
        }
    },
)
```

这些 slice 会出现在 system trace 中，便于和 `Choreographer#doFrame`、View traversal、RenderThread 及 FrameTimeline 对齐。名称应稳定且避免带用户数据；高频小 setter 不要逐个创建 trace，以免测量开销反过来干扰样本。

Compose Runtime Tracing 能提供 composable 级 trace 信息。它不会自动展开某个 AndroidView 内所有 View 方法，所以仍要给工厂、绑定、异步结果处理和资源释放补自定义 slice。

### Perfetto 的阅读顺序

对互操作卡顿，建议按下面顺序建立证据：

1. 用 FrameTimeline 找 missed deadline 的应用帧；
2. 查看 App main thread 的 Compose、View traversal、自定义 trace 和 scheduler 状态；
3. 对齐 RenderThread 的 `DrawFrame`、GPU completion 与 dequeue/queue；
4. 确认页面属于标准 App Window、SurfaceView、TextureView 或混合出图；
5. 有独立 Surface 时，单独追对应 Producer、BufferQueue、layer transaction 与 fence；
6. 回到调用计数，确认是 create、bind、remeasure、redraw、GC 还是显示侧等待。

主线程空闲不能证明页面正常：SurfaceView 的 Producer、RenderThread、GPU、SurfaceFlinger 或 display 仍可能迟到。主线程繁忙也不能只归因于 Compose：传统 View 的 inflate、文本测量和 listener 可能占据同一段时间。

## 七、Compose UI 1.11 特性的合理边界

### PausableComposition

`PausableComposition` API 从 Runtime 1.8.0 起存在。Foundation 1.11.4 的 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 默认值为 `true`，Lazy 预取可以把一项预组合分段执行，避免长 item 的全部 Composition 集中在单个调度片段。应用仍可关闭这个回归保护开关，因此性能报告要记录 flag；该机制也不能推广到所有 Composition。

以下成本仍需单独处理：

- `AndroidView.factory` 已开始后，View constructor/inflate 仍在 UI 线程执行；
- View 的 `measure/layout/draw` 不会被 pausable composition 拆分；
- 复用仍要求非空 `onReset` 和兼容 group 结构；
- WebView、地图、视频等内部线程与 native 资源不受 Compose pause 语义管理；
- 预组合未附着的 ComposeView 仍要遵守显式 dispose 规则。

因此，PausableComposition 适合作为预取调度工具，不是互操作组件的统一加速开关。

### Modifier.Node

`AndroidViewHolder` 的 core modifier 涉及 nested scroll、semantics、`pointerInteropFilter`、draw 与全局位置回调。Compose UI 内部使用 Node 架构后，modifier 更新可以减少部分对象创建和链遍历。

View 侧仍会收到标准 `MotionEvent`，继续执行 `dispatchTouchEvent`、手势识别、nested scrolling 和 listener。若地图或复杂手势控件出现输入延迟，应同时测 Compose pointer bridge 与 View 自身 dispatch，不能只对比 modifier allocation。

### ComposeViewContext

1.11.4 默认开启的共享实现能减少同一 owner 区域内多个 ComposeView 的部分重复宿主对象。这个收益不包括业务 Composition、每个根的 LayoutNode 或 `remember` 内容。

公开 `ComposeViewContext` 仍带实验注解。应用若显式使用它做离树预组合，需要把 Compose UI 版本锁定、封装实验 API，并测试 attach、取消预取、owner 切换和永不 attach 四条路径。

## 八、SurfaceView、TextureView 与帧率适配

### 三种出图拓扑

| 内嵌内容 | 内容 buffer 去向 | SurfaceFlinger 可见结构 | 常见额外风险 |
| --- | --- | --- | --- |
| 普通 View | 记录进宿主 HWUI / App Window | 主体仍是 App Window layer | 主线程 traversal、RenderThread/GPU |
| TextureView | 外部 buffer 被 HWUI 采样进 App Window | 外部流通常没有独立可见 layer | 两次生产、纹理采样、宿主帧依赖 |
| SurfaceView | Producer 提交到独立 Surface | 宿主 layer 加 SurfaceView 子层树 | 两条帧节奏、几何 transaction、fence/HWC |

`AndroidView` 只描述 UI 宿主方式，不能据此判断出图类型。包装普通 TextView 与包装视频 SurfaceView 的性能模型相差很大。

### Adaptive Refresh Rate 的投票边界

Android 15 QPR1 起，受支持设备可使用 Adaptive Refresh Rate；Android 17 仍要先用 `Display.hasArrSupport()` 确认设备支持。View 可以通过 `requestedFrameRate` 投票，Compose 1.9 起提供 `Modifier.preferredFrameRate`。

混合树中应遵守这些边界：

- ViewGroup 的 frame-rate 请求不会自动传播给 child View；
- Compose modifier 的偏好不会自动设置 AndroidView 内部 View 的 `requestedFrameRate`；
- 独立 Surface 的 Producer 还可能需要在 Surface、媒体或图形 API 边界表达自己的帧率；
- 系统会汇总可见内容投票，最终显示模式仍受面板能力、功耗策略和其他 layer 约束；
- 60/90/120 Hz 切换结果要从 trace、SurfaceFlinger 信息和设备显示状态确认。

例如，Compose 外层动画希望 high category，而内嵌视频保持 24/30 fps，这两条内容节奏可以不同。宿主 UI 每帧重组也不会让视频凭空产生新 buffer；SurfaceView 视频更新也不要求宿主 App Window 同步重画。

## 九、测试互操作边界

### 把 View 构造抽成窄接口

复杂 Android View 很难在纯 JVM 测试中忠实模拟。可以把工厂抽象出来，使宿主状态映射可测试，同时让仪器测试继续使用真实 View。

```kotlin
fun interface LegacyChartFactory {
    fun create(context: Context): LegacyChartView
}

@Composable
fun ChartHost(
    factory: LegacyChartFactory,
    model: ChartModel,
) {
    AndroidView(
        factory = factory::create,
        update = { chart -> chart.render(model) },
        onReset = { chart -> chart.resetForReuse() },
        onRelease = { chart -> chart.release() },
    )
}
```

单元测试可覆盖 `ChartModel` 映射和 factory 选择；Robolectric 或 instrumented test 覆盖 Looper、View owner、measure/layout、input 与资源生命周期。深度 mock `View` 构造通常无法重现这些平台行为。

### Espresso 与 ComposeTestRule 混用

官方测试 API 支持在同一个 instrumented test 中分别查询 View 与 Compose 节点。下面的测试先操作传统按钮，再断言 Compose 文案。

```kotlin
@get:Rule
val composeRule = createAndroidComposeRule<InteropActivity>()

@Test
fun legacyButtonUpdatesComposeState() {
    onView(withId(R.id.legacy_increment)).perform(click())

    composeRule
        .onNodeWithText("Count: 1")
        .assertIsDisplayed()
}
```

Compose test rule 会同步它掌握的 Compose 工作；虚拟测试时钟不会控制 Android View 的 measure/draw、外部线程或播放器回调。等待 View/外部条件时使用语义明确的 idling resource 或 `waitUntil`，不要用固定 sleep 掩盖竞态。

### 互操作测试范围

至少覆盖：

- attach → detach → reattach；
- Fragment view destroy 后 Fragment 仍存活；
- RecyclerView recycle、pool reuse、pool discard；
- Lazy item deactivate、reuse、release；
- configuration change、进程状态恢复与唯一 View ID；
- accessibility focus 在 View/Compose 之间移动；
- nested scroll、fling、返回手势与 `requestDisallowInterceptTouchEvent`；
- SurfaceView/TextureView 可见性、尺寸、前后台和资源释放；
- 预组合取消且 View 永不 attach；
- 60/90/120 Hz 与 ARR 支持设备上的 frame-rate vote。

## 十、三阶段迁移与性能门槛

### 阶段 1：单页面 `ComposeView`

这一阶段应确认：

- Fragment 使用正确的 composition strategy；
- 首次 `setContent`、first composition 和首帧耗时；
- 页面只有预期数量的 Compose 根；
- ViewModel、saved state、back press、Insets 和 accessibility 正常；
- release Macrobenchmark 与旧页面使用相同旅程。

### 阶段 2：Fragment 内 Compose 与 View 混合

这一阶段增加以下观察项：

- AndroidView `factory/update/reset/release` 计数；
- View `requestLayout/invalidate` 是否被不必要 setter 放大；
- 焦点、IME、nested scroll 和手势 owner；
- 多 ComposeView 的 retained roots 与 heap；
- SurfaceView/TextureView 的独立 Producer 路径。

### 阶段 3：Compose 导航栈

导航统一后继续监控：

- cold/warm startup 与首个可交互帧；
- destination composition 的创建、保留和处置；
- back stack save/restore；
- Lazy 列表、图片和动画的 P50/P90/P95/P99 帧；
- Baseline Profile 覆盖；
- minified release 的内存峰值、GC 和 ANR 风险。

### 可复现的 A/B 记录

| 维度 | 固定条件 | 记录指标 |
| --- | --- | --- |
| 构建 | 同 commit 逻辑、同 AGP/Kotlin/Compose、同设备 APK | APK hash、R8、Baseline Profile |
| 数据 | 相同 item 数、图片缓存状态和网络响应 | create/bind/update 数 |
| 设备 | 同型号、系统、刷新率、温度区间和电源状态 | thermal、频率、后台负载 |
| 旅程 | 相同启动、滚动、点击和返回脚本 | startup、frame deadline、交互延迟 |
| 追踪 | 相同 Perfetto 配置与迭代次数 | main、RenderThread、FrameTimeline、Surface |
| 统计 | 足够 warmup 与多次迭代 | median、P90/P95/P99、异常样本说明 |

迁移 gate 不宜只看平均 FPS。平均值可能掩盖首次创建、快速滚动和池满释放时的长尾。应同时设定 deadline miss、P95/P99 frame、startup、内存峰值和功能正确性阈值。

## 十一、排查清单

### `AndroidView`

- [ ] View 在 `factory` 内创建；
- [ ] `factory` 没有可延后的重型初始化；
- [ ] `update` 只读取必要 State；
- [ ] setter 有等值保护，并确认是否会请求布局；
- [ ] View listener 不会无条件回写 Compose State；
- [ ] Lazy 容器需要复用时提供非空 `onReset`；
- [ ] reset 后不会显示旧 item 内容；
- [ ] `onRelease` 关闭所有终止型资源；
- [ ] SurfaceView/TextureView/WebView 按自身出图路径追踪。

### `ComposeView`

- [ ] Fragment 使用 `DisposeOnViewTreeLifecycleDestroyed`；
- [ ] RecyclerView 保留 pooling-aware 默认策略；
- [ ] holder 只在初始化时 `setContent`；
- [ ] bind 更新 State，不反复重建 Composition；
- [ ] 多个 ComposeView 有唯一 ID；
- [ ] item 业务状态按稳定 ID 提升；
- [ ] 记录 Compose 根数量、heap 与处置时机；
- [ ] 显式预组合路径覆盖取消和 dispose。

### 性能证据

- [ ] Inspector 只用于结构定位；
- [ ] Compiler Metrics 不代替 View 内部计时；
- [ ] factory、bind、update、reset、release 有低开销计数；
- [ ] 自定义 trace 与 FrameTimeline 对齐；
- [ ] release、minified、无 Inspector 环境采样；
- [ ] 一条独立 Surface 对应一套 Producer、BufferQueue 和 fence 证据；
- [ ] Android 17 platform 与 Compose 1.11.4 版本线分开记录；
- [ ] kernel tag 只用于解释对应设备内核机制。

## 结论

`AndroidView` 的主要成本来自 View 实例创建、Compose Constraints 到 MeasureSpec 的转换、View measure/layout/draw、输入桥和资源生命周期。`update` 内读取的 Snapshot State 变化会由 holder 的观察器触发执行；普通参数变化则可以随宿主重组提供新的 block。是否重测量或重绘取决于 View setter 发出的 `requestLayout()` 与 `invalidate()`。

`ComposeView` 在同一窗口中通常共享 window `Recomposer`，但每个实例仍是独立 Composition 与布局/语义根。Fragment 应按 ViewTree lifecycle 处置，RecyclerView 应保留 pool-aware 策略并避免每次 bind 重新 `setContent`。Compose UI 1.11 的 `ComposeViewContext` 能共享部分宿主对象并支持实验性离树预组合，不能消除每个根的业务状态和布局成本。

互操作性能优化的有效顺序是：确认出图拓扑，测量 factory/bind/update/measure/draw，修复状态反馈与生命周期，再比较迁移阶段。PausableComposition、Modifier.Node、Runtime Tracing 与 ARR 各自解决一段问题，没有任何一个特性能替代整帧证据。

## 相关章节

- [Compose 性能优化实战](03-compose-performance.md)
- [Compose First 与 View/Compose 混合迁移性能边界](15-compose-first-view-migration-performance.md)
- [Compose LazyList/LazyGrid 滑动性能深度优化](22-compose-lazylist-performance.md)
- [Compose Modifier.Node 架构与性能迁移](31-compose-modifier-node-architecture-performance.md)

## 参考资料

- [Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)
- [Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)
- [Compose UI releases](https://developer.android.com/jetpack/androidx/releases/compose-ui)
- [Compose BOM](https://developer.android.com/develop/ui/compose/bom)
- [Google Maven：Compose BOM 2026.06.01 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.06.01/compose-bom-2026.06.01.pom)
- [`AndroidView` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/viewinterop/AndroidView.composable)
- [`AndroidViewBinding` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/viewinterop/AndroidViewBinding.composable)
- [`ViewCompositionStrategy` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/platform/ViewCompositionStrategy)
- [`ComposeViewContext` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/platform/ComposeViewContext)
- [`PausableComposition` API](https://developer.android.com/reference/kotlin/androidx/compose/runtime/PausableComposition)
- [Compose phases](https://developer.android.com/develop/ui/compose/performance/phases)
- [Compose performance tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Define custom trace events](https://developer.android.com/topic/performance/tracing/custom-events)
- [Compose testing interoperability](https://developer.android.com/develop/ui/compose/testing/interoperability)
- [Compose test synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization)
- [Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [`Modifier.preferredFrameRate` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/preferredFrameRate.modifier)
- [Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Compose UI Android 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.11.4/ui-android-1.11.4-sources.jar)
- [Compose UI ViewBinding 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-viewbinding/1.11.4/ui-viewbinding-1.11.4-sources.jar)
- [Compose Foundation Android 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.11.4/foundation-android-1.11.4-sources.jar)
- [Android 17 `ViewRootImpl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Android 17 `Choreographer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 17 `SurfaceView`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/SurfaceView.java)
- [Android 17 `TextureView`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/TextureView.java)
- [Android 17 HWUI `WebViewFunctor`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h)
- [Android 17 kernel tag `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
