---
title: Compose First 与 View/Compose 互操作性能实战
chapter: '22.11'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
tags:
- compose
- interop
- androidview
- composeview
- rendering-performance
- migration
related_chapters:
- '22.3'
- '22.2'
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_draft_polish_at: '2026-08-15T01:15:55+08:00'
last_draft_polish_run_id: 20260815-011555-gracker-writing-review
last_verified: '2026-08-15'
last_verified_against: Android android-17.0.0_r1; AndroidX Compose BOM 2026.08.00 / UI Runtime Foundation 1.12.0; Kotlin/Compose compiler plugin 2.4.10; Compose 1.11.4 source artifacts retained as the previous verification baseline; android17-6.18 kernel notes only for device-side mechanisms
confidence: high
last_review_finalize_at: '2026-08-15T01:15:55+08:00'
last_review_finalize_run_id: 20260815-011555-gracker-writing-review
sources:
- type: reference
  path: 'Android developer documentation: Views in Compose / Compose in Views / Compose testing interoperability'
- type: official
  path: AndroidX Compose BOM 2026.08.00; UI, UI ViewBinding, Runtime, Foundation 1.12.0 source artifacts and public API references; 1.11.4 artifacts retained for comparison
- type: aosp
  path: AOSP android-17.0.0_r1 ViewRootImpl, Choreographer, SurfaceView, TextureView, HWUI WebViewFunctor
consolidated_from:
- src/part5-app/ch22-rendering-practice/15-compose-first-view-migration-performance.md
---

# Compose First 与 View/Compose 互操作性能实战

Compose 与 View 互操作有两个方向：

- `AndroidView` 把一个传统 `View` 接入 Compose 的布局、绘制、输入与生命周期；
- `ComposeView` 把一个 Compose 根接入既有 View 树。

两种方向都有桥接成本，但来源不同。`AndroidView` 关注 View 创建、`measure/layout/draw`、事件转发和实例复用；`ComposeView` 关注 Composition（组合）根、提供生命周期与状态保存能力的宿主、状态恢复，以及池化容器中的销毁时机。

池化容器会暂存离屏子项以便再次使用，例如 `RecyclerView`。只用“混合页面更慢”概括，会漏掉实例是否复用、属性设置调用是否重复、嵌套滚动和独立 Surface 等关键差异。

## 版本基线与术语校正

版本基线如下：

| 层级 | 基线 | 适用范围 |
| --- | --- | --- |
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | ViewRoot、HWUI、Surface、帧率请求与显示路径 |
| Jetpack Compose | Compose BOM 2026.08.00；`androidx.compose.ui`、`androidx.compose.runtime`、`androidx.compose.foundation` 1.12.0 | `AndroidView`、`ComposeView`、复用、跟踪与测试 |
| Kotlin / Compose 编译器 | Kotlin 2.4.10 / Compose Compiler Gradle 插件 2.4.10 | 编译报告与生成代码边界 |
| Android 内核 | `android17-6.18-2026-06_r6` | 调度、同步栅栏（fence）等设备侧机制；不决定互操作 API 语义 |

Compose 与 Android 平台分别发布。`android-17.0.0_r1` 能固定 `ViewRootImpl`、`SurfaceView`、`TextureView` 和 HWUI 的平台实现，不能固定 AndroidX Compose 的实现；后者要按对应构件的源码核查。

截至 2026 年 8 月 15 日，Google Maven 中最新的稳定 Compose BOM 是 2026.08.00，其中 `androidx.compose.ui`、`androidx.compose.runtime` 和 `androidx.compose.foundation` 都映射到 1.12.0。BOM（物料清单）只协调 Compose 库版本，不会自动添加依赖，也不管理 Kotlin 编译器插件；Kotlin 2.0 起，Compose Compiler Gradle 插件与 Kotlin 使用同一版本，因此这里都取 2.4.10。

本文保留 1.11.4 源码链接，用来说明上一轮核验依据，不代表推荐继续使用旧版本。

Compose 1.12.0 还要求 `compileSdk 37` 和 Android Gradle Plugin 9。`compileSdk` 决定编译时能引用哪些平台 API，不会自动改变应用的 `targetSdk` 行为；暂时无法升级构建工具的项目，应在自己能使用的 Compose 版本上核验本文机制和基准数据。

### Compose First 是新增能力的默认入口，不是存量重写命令

官方的 Compose First 路线表示新 UI 能力、示例和工具投入优先进入 Compose。Android View 工具包，以及 Fragment、RecyclerView 等官方列出的基于 View 的库已进入维护模式：继续接收关键修复，但不再有显著功能更新。官方仍支持 View/Compose 互操作，并建议存量应用渐进迁移；既有页面不会因此立刻失去支持。

迁移候选应按业务改版计划、状态模型、平台适配收益和当前性能基线排序，不必为了统一技术栈一次性重写。

新页面可以默认使用 Compose，但相机、地图、广告、WebView、播放器和厂商 SDK 仍可能只提供 View 或独立 Surface。每个长期互操作边界都要记录宿主归属、替换条件、生命周期、状态来源和性能负责人。页面已经稳定、指标达标且依赖复杂 View SDK 时，保留 View 往往比没有基线就迁移更可控。

迁移工具只能完成 XML、主题和组件结构转换，不能证明导航、状态保存、焦点、输入法（IME）、无障碍、资源释放与帧性能等价。每批只改变一个边界清楚的区域，保留旧实现的截图、发布构建基准结果和性能跟踪；验证通过后再扩大范围。

Compose Multiplatform 属于另一项跨平台决策，Android 页面迁移成功不能直接推导 iOS、桌面或 Web 的组件、输入与性能表现。

三项常见说法需要收窄：

| 常见说法 | Compose UI 1.12.0 中的边界 |
| --- | --- |
| `ViewTreeHostingRegistry` 优化 | 公开 API 名为 `ComposeViewContext`，1.12.0 已去掉实验注解；当前源码没有名为 `ViewTreeHostingRegistry` 的通用公开 API |
| `PausableComposition` 让 `AndroidView` 区域变快 | 可暂停的预组合能让 Lazy 布局和 `SubcomposeLayout` 的预取分批执行 Composition；View 的 `factory` 一旦调用，创建、测量和绘制仍由 View 自己完成 |
| `Modifier.Node` 优化 View 事件链 | 基于节点的修饰符实现能减少 Compose 一侧的对象分配与更新成本；`MotionEvent` 仍要经过 `pointerInteropFilter`，再进入 View 的事件分发链 |

性能分析需要分别判断 Compose 侧成本、View 侧成本和显示系统成本，不能从某个 Compose 版本特性直接推导整个混合页面提速。

## 一、两种互操作方向经过哪些对象

### `AndroidView`：一个 Compose 布局节点代理一个 View 承载器

Compose UI 1.12.0 的 `AndroidView` 会创建 `ViewFactoryHolder`，其父类 `AndroidViewHolder` 是一个 `ViewGroup`。这个承载器（holder）同时关联一个 Compose `LayoutNode`，后者是 Compose 布局树中的节点：

1. Compose 测量策略把自身的 `Constraints`（可用尺寸约束）与 View 的 `LayoutParams` 合成为 `MeasureSpec`；
2. 承载器调用被包装 View 的 `measure()`；
3. Compose 用 View 的 `measuredWidth`、`measuredHeight` 确定 `LayoutNode` 尺寸；
4. 放置阶段调用 View 的 `layout()`；
5. Compose 绘制修饰符经 `AndroidViewsHandler` 调用承载器的 `draw()`；
6. 指针输入、嵌套滚动、无障碍语义、窗口避让信息和“滚入可见区域”请求经过各自的互操作桥。

View 并没有转成可组合函数。View 的测量、布局、绘制和事件模型仍然存在，外层调度则由 Compose `LayoutNode` 接管。

### `ComposeView`：一个 ViewGroup 承载一个 Compose 根

`AbstractComposeView` 是 `ViewGroup`，内部只允许 Compose 创建的 `AndroidComposeView` 子节点。`ComposeView.setContent` 会保存内容函数；View 已附着到窗口时会立即保证 Composition 存在，尚未附着时通常等到首次附着。创建 Composition 时，父级 `CompositionContext` 按以下顺序解析：

1. 显式设置的父级 `CompositionContext`；
2. View 树中可找到的 `CompositionContext`；
3. 仍然有效的缓存 `CompositionContext`；
4. 当前窗口的 `Recomposer`。`Recomposer` 负责接收状态变化并安排重组。

同一窗口中的多个 `ComposeView` 通常会找到相同的窗口 `Recomposer`。这不等于它们共享一个 Compose 根：每个实例仍有自己的 Composition、`AndroidComposeView`、`LayoutNode` 树、语义管理对象、状态注册和 View 测量边界。

### 普通互操作不会自动增加一个可见 Surface

只包含普通 View 与 Compose 内容时，`AndroidView` 和 `ComposeView` 仍走应用主窗口（App Window）的标准出图路径：

`Snapshot / Recomposer → Compose measure/layout/draw → AndroidComposeView → ViewRootImpl / HWUI → RenderThread → App Window BLASTBufferQueue → SurfaceFlinger → HWC → present`

`Snapshot` 是 Compose 跟踪状态变化的快照系统，RenderThread 是 HWUI 执行渲染工作的线程，`present` 表示缓冲区进入显示阶段。BLASTBufferQueue 管理应用窗口缓冲区的提交，HWC 是显示硬件合成器。

桥接本身会增加主线程对象与调用，不会凭空创建一条独立缓冲区流。`SurfaceView` 会维护独立的内容 Surface、`BufferQueue` 和 SurfaceFlinger 子层；`TextureView` 的外部缓冲区由宿主 HWUI 采样进应用主窗口，输入流通常不会成为独立可见图层。

标准硬件加速 WebView 的页面主体也通过 HWUI 接口合入宿主窗口，网页视频、受保护内容或自定义 Surface 才可能增加媒体覆盖层。地图、视频和相机控件采用哪种结构取决于控件实现，排查时应以帧生产者（Producer）、缓冲队列和图层树为证据。

## 二、`AndroidView` 的成本模型

### `factory`、`update`、`onReset` 与 `onRelease`

官方契约和 1.12.0 源码给出的生命周期如下：

| 回调 | 调用语义 | 适合执行的工作 |
| --- | --- | --- |
| `factory` | 每个 View 实例调用一次，在 UI 线程执行 | 构造 View、设置一次性属性、注册长期监听器 |
| `update` | `factory` 后至少调用一次；读取的 Compose 状态改变后可再次调用，在 UI 线程执行 | 以幂等方式把当前界面模型写入 View |
| `onReset` | 使用支持复用的重载时，在兼容实例准备复用前调用 | 清除瞬时状态、动画、按压、临时监听器或旧列表项内容 |
| `onRelease` | 实例永久离开 Compose 管理时调用一次 | 释放播放器、WebView、传感器、线程、回调等资源 |

在 `factory` 中加载复杂 XML、构造 WebView 或启动播放器，都会直接占用当前 UI 线程时间。把 View 预先放进 `remember` 不能绕过这个成本，还可能破坏宿主、附着和复用语义。官方建议在 `factory` 内创建 View。

`AndroidViewHolder` 会用 `OwnerSnapshotObserver` 观察 `update` 内读取的 Snapshot（快照）状态，也就是 Compose 可跟踪的状态。假设 `title` 与 `image` 是两个状态属性，而这个代码块只读取 `model.title`，`model.image` 变化不会触发本次观察。

普通参数捕获走另一条路径：宿主可组合函数重组并提供新的 `update` 函数时，承载器也会执行新函数。无论由哪条路径触发，昂贵的属性设置调用都可能把一次轻量状态更新扩大成 View 的重新布局、重绘或资源请求。

下面的宿主实现展示一次性监听器、幂等更新和资源释放各自所在的位置。

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

监听器只安装一次，并通过 `rememberUpdatedState` 取得当前回调；`update` 在引用未变化时跳过属性设置；终止型清理放在 `onRelease`。若模型是可变对象且在原对象上更新，引用比较不足以识别内容变化，应改用不可变界面模型、版本号或字段比较。

### `AndroidViewBinding` 沿用同一套桥接与复用语义

`AndroidViewBinding` 来自 `androidx.compose.ui:ui-viewbinding:1.12.0`。它调用生成的 ViewBinding 工厂函数加载 XML，把绑定对象保存在根 View 上，再用 `AndroidView` 承载这个根节点。因此，它减少的是手写 `findViewById` 和类型转换，不会省去 XML 加载、View 测量/布局/绘制或输入桥的成本。

1.12.0 同样提供带 `onReset`、`onRelease` 的重载。只有提供非空 `onReset`，View 与绑定对象才能在结构兼容的 Lazy 列表项之间复用；两个回调的时序与 `AndroidView` 一致。布局包含 `FragmentContainerView` 时还有额外边界：

- `AndroidViewBinding` 会优先使用父 Fragment 的 `LayoutInflater`，让 XML 中的 Fragment 成为父 Fragment 的正确子 Fragment；
- 永久释放时先运行调用方的 `onRelease`，再遍历根布局中的 `FragmentContainerView`；
- 找到 Fragment 且 `FragmentManager.isStateSaved == false` 时，内部用 `commitNow` 移除；状态已经保存时不会强行提交事务；
- 官方源码不建议为承载 Fragment 的绑定对象刻意启用 Lazy 复用，因为 Fragment 有独立的 View 生命周期，通常也不处于能稳定获益的复用场景。

因此，普通 XML 列表项可以按 `AndroidView` 的复用方法处理；包含 Fragment 的布局则应优先保证 FragmentManager、状态保存和销毁顺序正确，不能只看 View 创建次数。

### Compose 状态变化不等于 View 一定重新布局

一次 Compose 状态变化会触发哪些工作，取决于读取位置和属性设置行为：

- 状态在 `update` 中被读取：Snapshot 状态观察器会安排再次执行 `update`；
- 属性设置只调用 `invalidate()`：`AndroidViewHolder` 最终调用 `LayoutNode.invalidateLayer()`；View 报告的局部脏区不会原样传到 Compose 图层；
- 属性设置调用 `requestLayout()`：`AndroidViewsHandler.requestLayout()` 找到承载器对应的 `LayoutNode`，并调用 `requestRemeasure()` 请求重新测量；
- View 的测量尺寸变化：Compose 在重新测量后再次放置受影响节点；
- 状态只在父级修饰符或布局中读取：可能改变 Compose 布局，却不会运行无关的 View 属性设置。

Compose UI 1.12.0 还处理了绘制期间发生的 View 失效请求。`AndroidViewHolder` 若正在绘制，会用 `postOnAnimation` 把图层失效延后到下一帧，避免同一帧重复绘制同一内容。

因此，分析性能时要区分四个计数：`update` 次数、View `requestLayout` 次数、View `invalidate` 次数和最终帧数。重组计数无法替代后三项。

### 避免 View → Compose → View 的反馈循环

双向控件容易形成下面的循环：

1. Compose 把值写入 View；
2. View 的属性设置同步触发监听器；
3. 监听器又写入 Compose 状态；
4. 新状态促使 `update` 再写 View。

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

Compose 参数是唯一状态源；View 只上报用户操作；`update` 避免重复赋值。如果旧控件没有 `fromUser` 参数，可以在宿主维护“正在应用外部状态”的标记，或在监听器中比较新旧值。不要在 `update` 内无条件回写 Compose 状态。

### View 的成本要按操作拆分

| 操作 | 常见主线程成本 | 可能引起的后续工作 |
| --- | --- | --- |
| XML 加载 / 构造 | XML 解析、反射或构造、资源读取、子 View 创建 | 测量、布局、首次绘制 |
| 属性设置 | 文本测量、可绘制资源（drawable）更新、监听器通知 | `requestLayout()` 或 `invalidate()` |
| 测量 | ViewGroup 遍历、文本或图片尺寸计算 | 父子布局变化 |
| 布局 | 坐标分配、滚动、焦点和窗口避让处理 | 绘制、位置回调 |
| 绘制 | Canvas 指令记录、图片上传、复杂路径或着色器 | RenderThread / GPU 工作 |
| 输入桥 | `MotionEvent` 转发、手势识别、嵌套滚动 | 状态更新与新帧 |
| 永久释放 | 停止异步任务、解绑监听器、销毁原生资源 | 回收抖动或泄漏风险 |

固定控件尺寸能减少一部分测量波动，但不能消除 View 自身的测量。重复设置同一段文本也未必是空操作，具体取决于控件实现；业务层是否添加幂等保护，应以目标 View 源码或基准测试为依据。

## 三、Lazy 容器中的 `AndroidView` 复用

### 不提供 `onReset` 时不会复用 View 实例

Compose UI 提供两组 `AndroidView` 重载。没有 `onReset` 的版本不会在可复用内容容器中复用 View；带非空 `onReset` 的版本会创建可复用节点。两个 `AndroidView` 能否互换，取决于它们在 Compose 中是否具有相同的分组结构，不只取决于业务 `key`。

下面的列表项宿主明确区分“准备给新内容复用”和“实例永久退出”两种情况。

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

`onReset` 之后，View 可能进入 `deactivated`（暂时停用但仍由 Compose 保留）状态，下一次 `update` 不保证立刻发生。因此，重置后的 View 必须处于安全状态，不能继续显示旧内容。`onRelease` 具有终止语义，同一实例后续不会再复用。

### 复用时应清理什么

复用检查至少覆盖：

- 旧列表项的监听器、标签、选择态、按压态、激活态与无障碍文案；
- 尚在运行的动画、延迟任务、图片请求、协程或播放器任务；
- `RecyclerView`、WebView、地图、视频组件自己的滚动与资源状态；
- 瞬时状态和焦点；
- 与旧 `LifecycleOwner`、`SavedStateRegistryOwner` 或业务宿主绑定的订阅；
- 失败占位、错误文案与内容描述。

清理过少会让不同列表项串内容；清理过度会让每次复用接近重新创建。资源型 View 可以保留可复用引擎，把列表项专属会话停在 `onReset`，把原生引擎销毁留到 `onRelease`，前提是组件 API 明确支持这种生命周期。

### 列表性能要同时记录创建数和绑定数

只观察平均帧率很难定位复用是否生效。建议为每种 View 记录：

- `factory` 调用数；
- `onReset`、`update`、`onRelease` 调用数；
- 单次加载或创建与数据绑定的实际耗时；
- `requestLayout()` 和 `invalidate()` 频率；
- 滚动期间的对象分配量、垃圾回收次数与未释放实例；
- UI 线程、RenderThread 与 FrameTimeline 中的帧期限错过情况。FrameTimeline 是 Perfetto 中关联应用帧、合成帧和显示期限的轨道。

在同一数据集和相同滚动脚本下，`factory` 次数明显下降而数据绑定耗时稳定，才能说明复用减少了创建成本。若 `onReset + update` 比新建还贵，应回到控件实现调整复用边界。

## 四、`ComposeView` 嵌入 View 树

### Composition 的销毁策略

Compose UI 1.12.0 的默认策略是 `DisposeOnDetachedFromWindowOrReleasedFromPool`：

- 在普通 View 树中，从窗口分离会销毁 Composition；
- 位于 `RecyclerView` 等池化容器时，列表项短暂分离会保留 Composition；
- 列表项从池中永久释放、容器与窗口分离或池满丢弃时，池化监听器会销毁 Composition。

Fragment 的 View 生命周期短于 Fragment 实例生命周期，推荐把 Composition 绑定到下一次附着时找到的 View 树 `LifecycleOwner`。下面的写法适用于 Fragment 的 View。

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

该策略会在 Fragment 的 View 生命周期进入 `ON_DESTROY` 时销毁 Composition，避免 Fragment 实例仍然保留时继续持有已销毁的 View 树。在自定义宿主或手工创建的窗口中，仍需确认 `ViewTreeLifecycleOwner` 与 `SavedStateRegistryOwner` 是否存在。

### RecyclerView 临时回收时不要主动销毁 Composition

默认池化策略就是为 RecyclerView 的短暂分离设计的。如果在每次 `onViewRecycled()` 中都调用 `disposeComposition()`，会失去对象池保留 Composition 的收益，并在列表再次需要该 ViewHolder 时重新创建整个 Composition。

一种稳定写法是在 ViewHolder 初始化时调用一次 `setContent`，数据绑定时只更新 ViewHolder 持有的 Compose 状态。

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

`setContent` 只执行一次，RecyclerView 的数据绑定转为状态更新。`clearBinding` 可以清除旧列表项引用，但不会销毁 Composition。若列表项含有通过 `remember` 保存的专属状态，应使用稳定 `key`、把状态提升到列表模型，或明确设计保存与恢复策略。

### 多个 ComposeView 的内存模型

“每个 ComposeView 都有一个 Recomposer”不符合默认窗口路径。同一窗口通常共享窗口 `Recomposer`；每个 `ComposeView` 仍保留以下实例级对象：

- 自己的 Composition 和槽位表（slot table）；槽位表是 Compose 运行时记录组合结构与 `remember` 数据的内部表；
- `AndroidComposeView` 与 LayoutNode 树；
- 无障碍语义、焦点、指针输入和 Snapshot 状态观察；
- 每个根各自的测量、布局和绘制边界；
- `SaveableStateRegistry` 的接入与注册内容；
- 业务层 `remember`、副作用、图片和缓存对象。

因此，十个很小的 `ComposeView` 与一个包含十个子节点的 `ComposeView`，在内存、调度和检查器结构上并不相同。差额没有跨项目通用的固定字节数，应在目标版本上用堆转储、对象分配分析和 Macrobenchmark 测量。Macrobenchmark 是从应用进程外驱动启动、滚动等完整操作路径的基准测试框架。

多个静态 `ComposeView` 还要使用唯一 View ID，官方文档明确要求这样才能正确恢复 `savedInstanceState`。RecyclerView 列表项内的局部界面状态更适合提升到稳定的列表项模型；依赖 ViewHolder 的临时 ID 保存业务状态，会受到复用和进程重建影响。

### Compose UI 1.12 的 `ComposeViewContext`

`ComposeViewContext` 在 Compose UI 1.11 引入，1.12.0 已去掉实验注解。使用兼容 `Context` 和宿主边界的多个 `ComposeView` 时，它可以共享一部分宿主对象，例如：

- 配置状态、资源 ID 缓存与矢量图缓存；
- 字体加载器与字体解析器；
- 无障碍、剪贴板、触觉反馈和窗口信息相关对象；
- 共享绘制作用域、`CanvasHolder` 等绘制辅助结构。

共享范围受 View `Context`、`LifecycleOwner`、`SavedStateRegistryOwner` 和部分功能开关约束。Fragment 建立新的宿主边界后，查找可能在该处停止或创建新的上下文。每个 Composition 的业务状态不会因此合并。

该 API 还允许用已附着的 View 创建 `ComposeViewContext`，再为尚未附着的 `ComposeView` 调用 `createComposition(context)`，可用于 RecyclerView 预组合。构造 `ComposeViewContext` 时作为锚点的 View 必须已经附着，并在这个上下文有效期间保持附着。

若预创建的 `ComposeView` 始终没有附着，调用方必须执行 `disposeComposition()`。这是一条需要自行管理取消与销毁的预热路径，不是所有 `ComposeView` 都会自动预取的保证。

## 五、RecyclerView 与 Lazy 容器混合滚动

### 帧预算属于整帧共享资源

常见刷新率对应的理论周期如下：

| 刷新率 | 周期 |
| --- | ---: |
| 60 Hz | 16.67 ms |
| 90 Hz | 11.11 ms |
| 120 Hz | 8.33 ms |

这些时间由输入、动画、Compose、View 树遍历、RenderThread、GPU、SurfaceFlinger 和显示阶段共同使用。不能给 Compose 8 ms、View 8 ms，再把两者相加当成 60 Hz 的安全预算；FrameTimeline 给出的帧期限才是当前帧的系统约束。

### `AndroidView` 放进 LazyColumn

外层使用 LazyColumn 时，检查以下六点：

- 提供非空 `onReset`，验证实例复用；
- 给列表项使用稳定 `key` 和合理 `contentType`；
- 避免数据绑定时无条件请求布局；
- 尽量保持 View 高度稳定，异步内容到达后减少反复改尺寸；
- 在 `onReset` 中停止旧列表项的动画和异步请求；
- 在 `onRelease` 中关闭不可复用资源。

若 `AndroidView` 自己又包含竖向 RecyclerView，外层 LazyColumn 与内层列表会争夺滚动、预取、测量和可见性管理。短内容可以让内层一次性展开，但大数据会失去“只创建可见列表项”的虚拟化收益；大数据场景通常只保留一个负责竖向滚动的容器。

### ComposeView 放进 RecyclerView

反向把 `ComposeView` 放进 RecyclerView 时，列表项按以下规则处理：

- ViewHolder 初始化时只调用一次 `setContent`；
- 数据绑定只更新稳定、不可变的界面模型；
- 保留默认池化策略，让 Composition 在短暂分离期间继续存在；
- 列表项状态按稳定 ID 存入模型或 ViewModel，不依赖 ViewHolder 位置；
- 记录 ViewHolder 创建、数据绑定、重组与测量次数；
- 为图片、富文本和自定义布局建立单独的性能跟踪区段。

RecyclerView 预取与 Compose 的组合、布局各有调度成本。Compose UI 1.12 的 `ComposeViewContext` 可以提前完成一部分 Composition，但预热过多列表项会提前消耗 CPU 和内存。预取数量应由滚动速度、列表项成本和设备档位共同决定。

### 嵌套滚动桥能传递增量，不能解决所有控制权冲突

`AndroidViewHolder` 实现了 `NestedScrollingParent3`。内部 View 开启嵌套滚动后，承载器会把滚动前、滚动后和惯性滑动数据交给 Compose 的调度器，因此常见的嵌套滚动可以跨越 View/Compose 边界。

以下情况仍需专项验证：

- 两个同方向、都可无限滚动的容器；
- 内层使用 `requestDisallowInterceptTouchEvent` 改变手势控制方；
- RecyclerView 列表项内嵌高度不受限的 LazyColumn；
- 惯性滑动交接时两边都启动衰减动画；
- 越界回弹、下拉刷新、AppBar 和无障碍滚动同时存在；
- SurfaceView/地图等组件还有自己的手势和帧循环。

多数页面只应有一个主要的竖向滚动容器。竖向列表中放横向轮播，是边界清楚且容易单独验证的常见例外。

### 分批迁移与全量迁移怎样比较

迁移策略应按风险和测量结果选择：

| 策略 | 优点 | 风险 | 适合场景 |
| --- | --- | --- | --- |
| 页面级 ComposeView | 宿主和回退边界清楚；便于 A/B 对比 | 新建一个 Compose 根；页面内仍可能调用旧 View | 独立新页面、功能边界完整 |
| Fragment 内局部替换 | 改动范围小；可逐块验证 | 多个根、焦点/状态/布局交界增多 | 老页面中低耦合区域 |
| RecyclerView 列表项使用 ComposeView | 可按列表项类型迁移 | 高频数据绑定、池化、状态恢复要求高 | 列表项类型少且基准完备 |
| Compose 中保留 AndroidView | 可复用成熟地图、视频、编辑器 | View 创建、布局、事件和资源生命周期仍在 | 暂无等价 Compose 组件 |
| 一次全量迁移 | 根与滚动控制方容易统一 | 回归面大，难定位差异来源 | 页面较小、测试充分、旧实现负担高 |

全 Compose 导航栈也不保证更快；它能减少部分 View/Compose 边界，却可能引入新的组合、导航、图片或布局成本。每个阶段都应使用同一条用户操作路径、相同数据与发布构建进行比较。

## 六、Layout Inspector、编译器指标与 Perfetto

### Layout Inspector 负责结构和重组线索

混合页面在 Layout Inspector 中会同时出现 View 层级与 Compose 节点。`AndroidView` 仍能在 View 一侧找到被包装实例；`ComposeView` 中会显示对应的 Compose 根、语义与布局信息。

它适合回答：

- 页面有多少 Compose 根和 AndroidView；
- 某个可组合函数是否频繁重组或跳过；
- View/Compose 边界的尺寸、位置和宿主是否符合预期；
- 相同列表项是否不断创建新根。

Layout Inspector 会插入额外观测代码并增加开销，不应在连接检查器的进程中采集最终性能数据。可以先用它定位对象，再关闭工具运行发布构建的 Macrobenchmark 与 Perfetto。

### Compose 编译器指标看不到 View 内部成本

编译器报告会把 `AndroidView` 的宿主可组合函数当作普通可组合函数分析，可显示函数能否重新执行、能否跳过，以及参数稳定性。它不会提供：

- `factory` 调用了多少次；
- View 的测量、布局和绘制花了多久；
- 属性设置是否触发 `requestLayout()`；
- 监听器是否形成反馈循环；
- RecyclerView 是否复用了 ViewHolder；
- SurfaceView 的帧生产者是否按时提交缓冲区。

因此，编译器报告适合检查宿主函数的生成属性；View 内部仍需要自定义跟踪区段、计数器和系统跟踪。

### 用自定义跟踪区段标出桥接工作

下面用 `androidx.tracing.trace` 标记昂贵的 View 更新和列表项数据绑定。

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

这些时间区段会出现在系统跟踪中，便于和 `Choreographer#doFrame`、View 树遍历、RenderThread 及 FrameTimeline 对齐。名称应保持稳定且不能携带用户数据；不要为每个高频、低成本的属性设置都创建跟踪区段，以免测量开销干扰样本。

Compose 运行时跟踪能提供可组合函数级跟踪信息。它不会自动展开某个 `AndroidView` 中的全部 View 方法，所以仍要给工厂创建、数据绑定、异步结果处理和资源释放补充自定义时间区段。

### Perfetto 的阅读顺序

对互操作卡顿，建议按下面顺序建立证据：

1. 用 FrameTimeline 找到错过显示期限的应用帧；
2. 查看应用主线程中的 Compose、View 树遍历、自定义跟踪区段和线程调度状态；
3. 对齐 RenderThread 的 `DrawFrame`、GPU 完成时间与缓冲区出队/入队操作；
4. 确认页面属于标准 App Window、SurfaceView、TextureView 或混合出图；
5. 有独立 Surface 时，单独跟踪对应的帧生产者、`BufferQueue`、图层事务与同步栅栏；
6. 回到调用计数，确认问题来自创建、数据绑定、重新测量、重绘、垃圾回收，还是显示侧等待。

图层事务负责把尺寸、位置、层级等变化提交给 SurfaceFlinger；同步栅栏（fence）表示某次缓冲区读写何时完成。主线程空闲不能证明页面正常：SurfaceView 的帧生产者、RenderThread、GPU、SurfaceFlinger 或显示设备仍可能迟到。主线程繁忙也不能只归因于 Compose：传统 View 的 XML 加载、文本测量和监听器可能占据同一段时间。

## 七、Compose UI 1.12 相关机制的适用边界

本节只解释这些 Compose 机制会怎样影响互操作边界；编译器诊断、稳定性判定和 Modifier 节点迁移的完整方法由 [Compose 编译器、稳定性与 Modifier.Node 性能诊断](03-compose-compiler-modifier-diagnostics.md) 展开。

### PausableComposition

`PausableComposition` API 从 `androidx.compose.runtime` 1.8.0 起存在。Foundation 1.12.0 的 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 默认值为 `true`，Lazy 预取可以把一个列表项的预组合分段执行，避免复杂列表项的全部 Composition 集中在同一个调度片段。

这个开关用于出现回归时暂时关闭新路径，且后续版本可能移除；性能报告应记录 Compose 版本和开关值，不能把该机制推广到所有 Composition。

以下成本仍需单独处理：

- `AndroidView.factory` 开始执行后，View 构造和 XML 加载仍占用 UI 线程；
- View 的测量、布局和绘制不会被可暂停组合拆分；
- 复用仍要求非空 `onReset` 和兼容的 Compose 分组结构；
- WebView、地图、视频等组件的内部线程与原生资源不受 Compose 暂停语义管理；
- 预组合但未附着的 `ComposeView` 仍要遵守主动销毁规则。

因此，PausableComposition 适合作为预取调度工具，不是互操作组件的统一加速开关。

### Modifier.Node

`AndroidViewHolder` 的核心修饰符涉及嵌套滚动、无障碍语义、`pointerInteropFilter`、绘制与全局位置回调。Compose UI 内部使用 `Modifier.Node` 架构后，修饰符更新可以减少部分对象创建和链遍历。

View 侧仍会收到标准 `MotionEvent`，继续执行 `dispatchTouchEvent`、手势识别、嵌套滚动和监听器。若地图或复杂手势控件出现输入延迟，应同时测量 Compose 指针桥和 View 自身的事件分发，不能只比较修饰符的对象分配量。

### ComposeViewContext

1.12.0 的共享实现能减少同一宿主区域内多个 `ComposeView` 的部分重复宿主对象。这个收益不包括业务 Composition、每个根的 `LayoutNode` 或 `remember` 内容。

公开的 `ComposeViewContext` 在 1.12.0 已不再带实验注解。应用若显式使用它做离树预组合，仍应固定 Compose UI 版本，并测试附着、取消预取、宿主切换和始终不附着四条路径；API 稳定不代表资源会自动销毁。

## 八、SurfaceView、TextureView 与帧率适配

本节只判断内嵌 View 会不会改变出图拓扑，以及宿主与内容的帧率请求是否需要分别表达。SurfaceView/TextureView 的生命周期治理与自适应刷新率策略分别由本章对应专题展开。

### 三种出图拓扑

| 内嵌内容 | 内容缓冲区去向 | SurfaceFlinger 可见结构 | 常见额外风险 |
| --- | --- | --- | --- |
| 普通 View | 记录进宿主 HWUI / App Window | 主体仍是 App Window 图层 | 主线程遍历、RenderThread / GPU |
| TextureView | 外部缓冲区被 HWUI 采样进 App Window | 外部流通常没有独立可见图层 | 内容生产与宿主绘制两段工作、纹理采样、宿主帧依赖 |
| SurfaceView | 帧生产者提交到独立 Surface | 宿主图层加 SurfaceView 子层树 | 两条帧节奏、几何事务、同步栅栏与 HWC 合成 |

`AndroidView` 只描述 UI 宿主方式，不能据此判断出图类型。包装普通 TextView 与包装视频 SurfaceView 的性能模型相差很大。

### 自适应刷新率的请求边界

Android 15 QPR1（首个季度平台更新）起，受支持设备可使用自适应刷新率（Adaptive Refresh Rate，ARR），让系统按可见内容请求调整刷新率。Android 17 仍要先用 `Display.hasArrSupport()` 确认设备支持。View 可以通过 `requestedFrameRate` 发出请求，Compose 1.9 起提供 `Modifier.preferredFrameRate`。

混合树中应遵守这些边界：

- ViewGroup 的帧率请求不会自动传播给子 View；
- Compose 修饰符的偏好不会自动设置 `AndroidView` 内部 View 的 `requestedFrameRate`；
- 独立 Surface 的帧生产者还可能需要在 Surface、媒体或图形 API 边界表达自己的帧率；
- 系统会汇总可见内容的请求，最终显示模式仍受面板能力、功耗策略和其他图层约束；
- 60/90/120 Hz 的切换结果要从性能跟踪、SurfaceFlinger 信息和设备显示状态确认。

例如，Compose 外层动画可以请求高帧率类别，而内嵌视频保持 24/30 fps，两条内容节奏可以不同。宿主界面每帧重组不会让视频凭空产生新缓冲区；SurfaceView 视频更新也不要求宿主应用窗口同步重画。

## 九、测试互操作边界

### 把 View 构造抽成窄接口

复杂 Android View 很难在纯 JVM 测试中忠实模拟。可以把创建 View 的工厂抽成窄接口，让宿主状态映射可以单独测试，同时让 Android 仪器化测试继续使用真实 View。

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

单元测试可以覆盖 `ChartModel` 映射和工厂选择；Robolectric 或仪器化测试负责覆盖 Looper 消息循环、View 树宿主、测量/布局、输入与资源生命周期。大量模拟 `View` 内部行为，通常无法重现这些平台边界。

### Espresso 与 ComposeTestRule 混用

官方测试 API 支持在同一个仪器化测试中分别查询 View 与 Compose 节点。下面的测试先操作传统按钮，再断言 Compose 文案。

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

Compose 测试规则只会同步它能够观察的 Compose 工作；虚拟测试时钟不会控制 Android View 的测量、绘制、外部线程或播放器回调。等待 View 或外部条件时，应使用能表达“何时空闲”的 `IdlingResource`，或使用 `waitUntil` 轮询明确条件，不要用固定时长的休眠掩盖竞态。

### 互操作测试范围

至少覆盖：

- 附着 → 分离 → 再次附着；
- Fragment 的 View 销毁后，Fragment 实例仍然存活；
- RecyclerView 回收、对象池复用、对象池丢弃；
- Lazy 列表项暂时停用、复用、永久释放；
- 配置变更、进程状态恢复与唯一 View ID；
- 无障碍焦点在 View/Compose 之间移动；
- 嵌套滚动、惯性滑动、返回手势与 `requestDisallowInterceptTouchEvent`；
- SurfaceView/TextureView 可见性、尺寸、前后台和资源释放；
- 预组合取消且 View 始终不附着；
- 60/90/120 Hz 与支持 ARR 的设备上的帧率请求。

## 十、三阶段迁移与性能门槛

### 阶段 1：单页面 `ComposeView`

这一阶段应确认：

- Fragment 使用正确的 Composition 销毁策略；
- 首次 `setContent`、第一次组合和首帧耗时；
- 页面只有预期数量的 Compose 根；
- ViewModel、状态保存、返回操作、窗口避让和无障碍功能正常；
- 发布构建的 Macrobenchmark 与旧页面使用相同操作路径。

### 阶段 2：Fragment 内 Compose 与 View 混合

这一阶段增加以下观察项：

- `AndroidView` 的 `factory/update/onReset/onRelease` 计数；
- View 的 `requestLayout/invalidate` 是否被不必要的属性设置放大；
- 焦点、输入法、嵌套滚动和手势控制方；
- 多个 `ComposeView` 的未释放根节点与堆内存；
- SurfaceView/TextureView 的独立帧生产路径。

### 阶段 3：Compose 导航栈

导航统一后继续监控：

- 冷启动、热启动与首个可交互帧；
- 导航目标 Composition 的创建、保留和销毁；
- 返回栈的保存与恢复；
- Lazy 列表、图片和动画的 P50/P90/P95/P99 帧耗时；这些数字分别表示第 50、90、95、99 百分位；
- Baseline Profile 覆盖；Baseline Profile 是随应用发布的热点代码清单，可让这些路径提前编译；
- 经 R8 代码压缩与优化的发布构建中的内存峰值、垃圾回收和应用无响应（ANR）风险。

### 可复现的 A/B 记录

| 维度 | 固定条件 | 记录指标 |
| --- | --- | --- |
| 构建 | 同一代码提交、同一 AGP/Kotlin/Compose、同设备 APK | APK 哈希、R8、Baseline Profile |
| 数据 | 相同列表项数量、图片缓存状态和网络响应 | 创建、绑定、更新次数 |
| 设备 | 同型号、系统、刷新率、温度区间和电源状态 | 温控状态、频率、后台负载 |
| 操作路径 | 相同启动、滚动、点击和返回脚本 | 启动耗时、帧期限、交互延迟 |
| 跟踪 | 相同 Perfetto 配置与迭代次数 | 主线程、RenderThread、FrameTimeline、Surface |
| 统计 | 充分预热并执行多次迭代 | 中位数、P90/P95/P99、异常样本说明 |

迁移验收门槛不宜只看平均 FPS。平均值可能掩盖首次创建、快速滚动和对象池满后释放时的长尾。应同时设定错过帧期限的比例、P95/P99 帧耗时、启动耗时、内存峰值和功能正确性阈值。

## 十一、排查清单

### `AndroidView`

- [ ] View 在 `factory` 内创建；
- [ ] `factory` 没有可延后的重型初始化；
- [ ] `update` 只读取必要状态；
- [ ] 属性设置有等值保护，并确认是否会请求布局；
- [ ] View 监听器不会无条件回写 Compose 状态；
- [ ] Lazy 容器需要复用时提供非空 `onReset`；
- [ ] 重置后不会显示旧列表项内容；
- [ ] `onRelease` 关闭所有终止型资源；
- [ ] SurfaceView/TextureView/WebView 按自身出图路径追踪。

### `ComposeView`

- [ ] Fragment 使用 `DisposeOnViewTreeLifecycleDestroyed`；
- [ ] RecyclerView 保留能识别池化容器的默认策略；
- [ ] ViewHolder 只在初始化时调用 `setContent`；
- [ ] 数据绑定只更新状态，不反复重建 Composition；
- [ ] 多个 ComposeView 有唯一 ID；
- [ ] 列表项业务状态按稳定 ID 提升；
- [ ] 记录 Compose 根数量、堆内存与销毁时机；
- [ ] 显式预组合路径覆盖取消和主动销毁。

### 性能证据

- [ ] Layout Inspector 只用于结构定位；
- [ ] 编译器指标不代替 View 内部计时；
- [ ] `factory`、数据绑定、`update`、`onReset`、`onRelease` 有低开销计数；
- [ ] 自定义跟踪区段与 FrameTimeline 对齐；
- [ ] 在发布构建、启用 R8、未连接 Layout Inspector 的环境采样；
- [ ] 每条独立 Surface 都有对应的帧生产者、`BufferQueue` 和同步栅栏证据；
- [ ] Android 17 平台与 Compose 1.12.0 版本线分开记录；
- [ ] 内核标签只用于解释对应设备的内核机制。

## 全文小结

`AndroidView` 的主要成本来自 View 实例创建、Compose `Constraints` 到 `MeasureSpec` 的转换、View 测量/布局/绘制、输入桥和资源生命周期。`update` 内读取的 Snapshot 状态变化会由承载器的观察器触发执行；普通参数变化则可随宿主重组提供新的函数。是否重新测量或重绘，取决于 View 的属性设置是否发出 `requestLayout()` 或 `invalidate()`。

`ComposeView` 在同一窗口中通常共享窗口 `Recomposer`，但每个实例仍是独立的 Composition 与布局/语义根。Fragment 应按 View 树生命周期销毁 Composition；RecyclerView 应保留能识别对象池的策略，并避免每次数据绑定都重新调用 `setContent`。Compose UI 1.12 的稳定版 `ComposeViewContext` 能共享部分宿主对象并支持离树预组合，但不能消除每个根的业务状态和布局成本。

互操作性能优化可以按这个顺序进行：确认出图结构，测量创建、数据绑定、更新、测量与绘制，修复状态反馈和生命周期问题，再比较不同迁移阶段。`PausableComposition`、`Modifier.Node`、运行时跟踪与 ARR 各自只覆盖一段链路，不能替代整帧证据。

## 相关章节

- [Compose 性能优化实战](03-compose-compiler-modifier-diagnostics.md)
- [Compose LazyList/LazyGrid 滑动性能深度优化](02-recyclerview-compose-lazylist.md)
- [自适应刷新率：ARR 与应用帧率治理](12-adaptive-refresh-rate.md)
- [SurfaceView 与 TextureView：渲染拓扑、生命周期与性能取舍](17-surfaceview-textureview.md)

## 参考资料

- [Android is Compose-first](https://developer.android.com/develop/ui/compose/first)
- [Compose migration strategy](https://developer.android.com/develop/ui/compose/migrate/strategy)
- [Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)
- [Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)
- [Compose UI releases](https://developer.android.com/jetpack/androidx/releases/compose-ui)
- [Compose BOM](https://developer.android.com/develop/ui/compose/bom)
- [Compose dependencies and compiler setup](https://developer.android.com/develop/ui/compose/setup-compose-dependencies-and-compiler)
- [Google Maven：Compose BOM 2026.08.00 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom)
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
- [Compose UI Android 1.12.0 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.12.0/ui-android-1.12.0-sources.jar)
- [Compose UI ViewBinding 1.12.0 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-viewbinding/1.12.0/ui-viewbinding-1.12.0-sources.jar)
- [Compose Foundation Android 1.12.0 sources](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.12.0/foundation-android-1.12.0-sources.jar)
- [Compose UI Android 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.11.4/ui-android-1.11.4-sources.jar)
- [Compose UI ViewBinding 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-viewbinding/1.11.4/ui-viewbinding-1.11.4-sources.jar)
- [Compose Foundation Android 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.11.4/foundation-android-1.11.4-sources.jar)
- [Kotlin releases](https://kotlinlang.org/docs/releases.html)
- [Android 17 `ViewRootImpl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Android 17 `Choreographer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 17 `SurfaceView`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/SurfaceView.java)
- [Android 17 `TextureView`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/TextureView.java)
- [Android 17 HWUI `WebViewFunctor`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/private/hwui/WebViewFunctor.h)
- [Android 17 kernel tag `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
