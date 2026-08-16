---
title: "Jetpack Compose 性能优化实战"
chapter: "22.3"
section: "22.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Compose BOM 2026.08.00 (Compose 1.12.0), Kotlin 2.4.10; historical checks: Compose 1.10.0 and Foundation 1.10.6"
confidence: high
sources:
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/PausableComposition.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow.kt"
tags: [compose, recomposition, stability, derivedStateOf, pausable-composition, strong-skipping]
related_chapters: ["7.7", "2.4", "22.1"]
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/20-compose-performance-blind-spots.md"
---
# Jetpack Compose 性能优化实战

Compose 性能优化要回答两个问题：哪一段工作错过了本帧 deadline（必须完成提交的截止点），以及哪些状态或输入让这段工作重复发生。只统计重组次数，容易漏掉 Layout、Drawing、RenderThread 和显示系统；只看整帧耗时，又无法定位到具体 Composable。

截至 2026-08-14，本文使用下面三组基线：

- Android 平台以 Android 17 / API 37 / `android-17.0.0_r1` 为源码锚点，Linux kernel 以 `android17-6.18-2026-06_r6` 为锚点。
- 当前依赖基线为 Compose BOM `2026.08.00`，其 POM 把 Runtime、Foundation 和 UI 约束到 `1.12.0`。文中另保留 BOM `2025.12.00` / Compose `1.10.0` 与 Foundation `1.10.6`，用于说明 Pausable Composition 的历史变化和复现实验。
- Compose Compiler 随 Kotlin `2.4.10` Gradle plugin 使用。Strong Skipping 属于编译器行为，Lazy 预取属于 Foundation 行为，两者都不能从 Android platform 源码标签推断。

普通 `ComposeView` 不会单独创建 Surface。内容仍由当前应用窗口的 HWUI（Android 硬件加速 UI 渲染器）路径输出：UI 线程完成 Composition（根据状态生成或更新 UI 树）、Layout（测量与摆放）和 Drawing（记录绘制命令），经 `HardwareRenderer.syncAndDrawFrame()` 交给 RenderThread（执行渲染命令的专用线程），再通过 BLAST BufferQueue 提交图形缓冲区，由 SurfaceFlinger 合成，并交给 HWC（Hardware Composer，硬件合成器），最终显示到屏幕。页面嵌入 `SurfaceView`、`TextureView`、WebView 或视频组件后，还要跟踪这些组件自己的图像生产者（producer）和 Surface layer（合成图层）。完整管线可结合 [Compose 渲染管线架构](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md) 阅读。

## 从状态读取阶段控制工作范围

Compose 把 UI 更新分成 Composition、Layout 和 Drawing 三个阶段。状态在哪个阶段被读取，运行时就在哪个阶段记录依赖；状态变化后，从对应的重启作用域（restart scope，可被单独标记失效并重新执行的范围）开始工作。

| 读取位置 | 状态变化后的起点 | 适合的变化 |
| --- | --- | --- |
| Composable 函数体或参数构造 | Composition，结果变化时还会进入 Layout / Drawing | 节点增删、文本内容、布局结构 |
| 测量 / 摆放 lambda | Layout；摆放与测量还有独立的重启作用域 | 位置、约束内尺寸、对齐 |
| draw lambda 或 layer property lambda | Drawing 或图层属性更新 | 颜色、透明度、绘制偏移、缩放 |

这张表描述失效（invalidation，即状态变化通知运行时某段结果已过期）的起点，不代表后续阶段必然执行。Composition 的输出没有改变时，Layout 和 Drawing 仍可跳过。`LazyColumn`、`BoxWithConstraints` 和 `SubcomposeLayout` 会在布局过程中决定子内容，不能套用“Composition 总在 Layout 之前一次完成”的简化模型。

下面的示例把滚动偏移推迟到 placement lambda 中读取，并把透明度放进 `graphicsLayer` 的属性 lambda。两个高频值都不再由 Composable 函数体读取。

```kotlin
@Composable
fun ParallaxHeader(
    listState: LazyListState,
    alpha: State<Float>,
) {
    Image(
        painter = painterResource(R.drawable.header),
        contentDescription = null,
        modifier = Modifier
            .offset {
                IntOffset(
                    x = 0,
                    y = listState.firstVisibleItemScrollOffset / 2,
                )
            }
            .graphicsLayer {
                this.alpha = alpha.value
            },
    )
}
```

`offset { ... }` 的状态读取发生在 placement 阶段，`graphicsLayer { ... }` 的读取用于更新图层属性。若位置变化会改变兄弟节点的测量约束，仍应使用能表达该约束关系的布局；视觉平移不能冒充布局位置。

状态影响节点数量、文本或语义属性时，Composition 无法省略。优化方向是缩小读取范围：把状态读取封装进 lambda、把读取移到更靠近使用位置的 Composable，或把一个过大的重组作用域拆成输入清晰的子函数。

## Strong Skipping 与 Stability

### 跳过条件要分函数和参数

Kotlin 2.0.20 起默认启用 Strong Skipping，本文当前基线 Kotlin `2.4.10` 无需再设置旧选项 `enableStrongSkippingMode`。它改变两项编译结果：

- 所有 restartable（运行时可单独重新执行）的 Composable 默认也可标记为 skippable（参数满足条件时可跳过）；non-restartable 函数仍不可跳过，`@NonSkippableComposable` 可以显式禁止跳过。
- Composable 内部创建的 lambda 会自动记忆并复用（memoize）。捕获值用作缓存 key；stable 捕获值按 `equals()` 比较，unstable 捕获值按 `===` 比较。`@DontMemoize` 可以让某个 lambda 退出自动缓存。

Stability（稳定性）是编译器对“参数能否可靠比较、属性变化能否被观察”的判定。进入重组时，skippable 函数还要比较本次与上次参数：`stable` 参数使用 `equals()`，`unstable` 参数使用实例相等 `===`。参数相等只能阻断父级重组向下传播；函数内部读取的 Snapshot 状态（能被 Compose 观察的快照状态）或动态 `CompositionLocal`（沿 Composition 树向下提供的值）发生变化时，对应重组作用域仍会失效。

Strong Skipping 没有让 Stability 失去作用。它决定参数采用哪种比较方式，也约束可变对象如何通知 Compose：

- 普通 `List`、`Set`、`Map` 接口仍被编译器视为 unstable。同一个可变集合实例原地修改时，实例比较可能让调用被跳过，集合本身也不会发送 Snapshot 通知。
- `SnapshotStateList`、`SnapshotStateMap` 能通知运行时；不可变 UI 数据模型配合新集合实例，则能提供边界清晰的新旧快照。
- `@Stable` 与 `@Immutable` 是开发者向编译器作出的契约。对象含有不可观察的可变字段时不能标注；错误契约可能让 UI 漏掉更新。
- 手写 `remember` lambda 可能包含特定 key 或生命周期语义，不能只因升级 Kotlin 就批量删除。应对照编译器生成规则和调用方需求逐处确认。

### 用编译器报告验证推断

编译器报告适合回答“这个函数怎样被编译”和“哪个类型被判定为 unstable”，不能单独证明某次卡顿由 Stability 引起。下面的 Gradle 配置适用于 Kotlin 2.x 的 Compose Compiler Gradle plugin。

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

应在 release variant（发布构建变体）上生成报告。`reportsDestination` 输出 `*-classes.txt`、`*-composables.txt` 和 `*-composables.csv`；`metricsDestination` 另行输出模块统计。Strong Skipping 开启后，`restartable` 函数通常也会显示 `skippable`，因此还要检查参数比较、状态读取位置和现场重组次数。追求“全模块全部 skippable”会增加错误标注和维护成本。

## `remember`、`derivedStateOf` 与副作用

### `remember` 缓存一次计算，不负责数据一致性

`remember(keys...)` 在 key 比较相等时复用缓存值，key 变化时丢弃旧值并重新计算。这里的 key 是缓存身份，不是业务列表中随意挑选的字段。它适合缓存排序结果、状态容器和创建成本较高的对象，但输入必须能表达一份稳定快照。

下面的写法假定 `items` 是不可变列表，数据更新时会提交新实例。

```kotlin
@Composable
fun SortedFeed(items: List<FeedItem>) {
    val sortedItems = remember(items) {
        items.sortedByDescending(FeedItem::timestamp)
    }

    LazyColumn {
        items(
            items = sortedItems,
            key = FeedItem::id,
            contentType = FeedItem::type,
        ) { item ->
            FeedRow(item)
        }
    }
}
```

如果调用方原地修改同一个普通列表，`remember(items)` 不会重新排序，Lazy 列表也拿不到可靠的新旧输入。修复点在数据所有权和可观察性，不在增加更多 `remember`。

### `derivedStateOf` 只处理输入、输出频率不匹配

`derivedStateOf` 适合把高频输入收敛为低频结果，例如滚动位置持续变化，而按钮只在跨过阈值时切换可见性。它会建立派生状态和依赖跟踪，本身有成本。

下面的示例只在“是否越过首项”改变时更新读取者。

```kotlin
@Composable
fun FeedWithScrollToTop(items: List<FeedItem>) {
    val listState = rememberLazyListState()
    val showScrollToTop by remember {
        derivedStateOf {
            listState.firstVisibleItemIndex > 0
        }
    }

    Box {
        LazyColumn(state = listState) {
            items(items, key = FeedItem::id) { item ->
                FeedRow(item)
            }
        }
        AnimatedVisibility(showScrollToTop) {
            ScrollToTopButton()
        }
    }
}
```

字符串拼接、数值乘法这类“输入每次变，输出也每次变”的表达式不需要 `derivedStateOf`。直接计算通常更清楚，运行时工作也更少。

### `rememberCoroutineScope` 面向事件，`produceState` 面向外部数据

`rememberCoroutineScope()` 返回与调用点 Composition 生命周期绑定的 `CoroutineScope`；调用点离开 Composition 后，其中的协程会收到取消信号。它适合点击、拖动结束、Snackbar 等事件回调。不要在 Composable 函数体中直接 `launch`；每次函数执行都可能启动新任务。

`produceState` 用协程把外部数据转成 Compose `State`，其中 producer 指负责持续产出状态值的协程代码块。Compose Runtime `1.12.0` 的带 key 重载使用 `remember { mutableStateOf(initialValue) }` 保存结果，并用 `LaunchedEffect(key)` 运行 producer。key 变化会取消旧 producer 并启动新 producer，离开 Composition 也会取消。返回的 `State` 会合并相等值；连续快速写入时，观察者也可能跳过中间值，只读到较新的结果。

下面的示例把用户 ID 和 repository 都作为 producer 的身份输入。

```kotlin
@Composable
fun userProfile(
    userId: String,
    repository: UserRepository,
): State<User?> {
    return produceState(
        initialValue = null,
        userId,
        repository,
    ) {
        value = repository.load(userId)
    }
}
```

缺少 key 会让 producer 继续使用旧输入；塞入每次重组都变化的 key 又会反复取消请求。key 变化也不会自动把同一个 `State` 恢复成 `initialValue`；若切换用户时必须立刻显示“加载中”，要在新的 producer 开头显式赋值。非挂起订阅可在 producer 中注册，并用 `awaitDispose` 解除。高频且每次都不同的数据仍可能使读取者频繁失效，应在数据源侧采样、聚合，或把仅影响绘制的读取延迟到 Drawing。`snapshotFlow` 用于把 Compose Snapshot 状态转成 Flow，不能替代外部高频数据到 UI 状态的节流。

Strong Skipping 不管理 producer 协程。跳过规则作用于 Composable 调用，协程的启动、取消和异常处理仍由 Effect key 与作用域生命周期决定。

## Lazy 列表：身份、类型与预取

### `key` 保持列表项身份，`contentType` 约束复用兼容性

Lazy 列表未提供业务 key 时按位置维护身份；显式使用 index 基本等同于位置身份。列表头部插入或中间删除后，后续列表项会被视作换了身份，`remember` / `rememberSaveable` 状态和组合复用都可能受到影响。

业务 key 应稳定且唯一。列表项使用 `rememberSaveable` 时，key 还要满足 Android `Bundle` 可保存类型的要求。`contentType` 用于告诉 Lazy 布局哪些列表项的组合结构可以复用；广告、标题、普通卡片结构不同，就应使用不同类型。

构建列表内容时还要避免排序、过滤、日期格式化、同步图片解码和阻塞 I/O。把纯计算移到上游或以不可变输入为 key 缓存，把 I/O 放进数据层和异步加载组件。

### Pausable Composition 的边界

`PausableComposition` 允许尚未提交的 Composition 在运行时定义的安全点暂停，并在之后继续。它仍在原有调度路径上执行，不会把任意 Composable 或协程抢占到后台线程。Compose Runtime `1.10.0` 提供该能力后，Foundation `1.10.0` 在 Lazy 预取中默认打开 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled`。当前 Foundation `1.12.0` 源码中的默认值也为 `true`，其预取路径分为四步：

1. Android 端 `AndroidPrefetchScheduler` 通过宿主 View 的 `post()` 在 UI 线程执行请求，并结合绘制时间、`Choreographer` 帧时间与刷新周期估算本帧余量。
2. Lazy prefetch 为目标 index 安排 precompose（提前组合）和 premeasure（提前测量）。普通请求会参考相同 `contentType` 的历史耗时；urgent 请求表示目标即将可见，只要本帧还有时间就会继续尝试。
3. 开关启用时，预组合调用 `PausedComposition.resume(shouldPause)`。暂停请求只在运行时提供的可暂停点生效，不能理解成回调返回 `true` 后立即中断任意一行代码。
4. 组合完成后单独 `apply()`，把结果提交到 Composition，再按约束执行 premeasure。Pausable Composition 只切分 precompose，不能把 apply、measure 或已进入可见窗口的同步工作一并切开。

这个默认值经历过反复：Foundation `1.10.0` 默认开启，`1.10.6` 因稳定性问题改为默认关闭，当前 `1.12.0` 源码又恢复为默认开启。现场行为取决于 Foundation 的精确版本和该版本中的开关值，不能只看“Compose 1.x”这一大版本号。本文保留 BOM `2025.12.00` / Foundation `1.10.0` 作为历史复现点。

这项能力没有覆盖普通首帧 Composition、常规重组或非 Lazy 子树。拆分重组作用域、降低列表项的组合成本、提供稳定 key 和控制状态读取范围仍然有效。

### `LazyLayoutCacheWindow` 同时控制 ahead 与 behind

Foundation `1.12.0` 的 `LazyLayoutCacheWindow` 仍是实验 API。ahead window 是滚动方向前方的准备窗口，behind window 是反方向的保留窗口。窗口增大会增加 precompose、premeasure 和保留节点的成本，不能按“越大越顺”设置。

下面的配置只用于展示 API 形态，比例需要在目标页面和目标设备上测量后确定。

```kotlin
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TunedFeed(items: List<FeedItem>) {
    val listState = rememberLazyListState(
        cacheWindow = LazyLayoutCacheWindow(
            aheadFraction = 0.75f,
            behindFraction = 0.25f,
        ),
    )

    LazyColumn(state = listState) {
        items(
            items = items,
            key = FeedItem::id,
            contentType = FeedItem::type,
        ) { item ->
            FeedRow(item)
        }
    }
}
```

调参时同时观察 `compose:lazy:prefetch:compose`、`compose:lazy:prefetch:apply`、`compose:lazy:prefetch:measure` 这些 trace slice（时间轴上的工作片段）、目标列表项首次可见帧成本和内存峰值。只有预取工作前移且后续关键帧变轻，才能说明窗口设置有收益。预取片段增加、关键帧不变或内存明显上升，通常说明窗口过大、命中不准或列表项的工作仍在可见帧发生。

## 工具：从重组证据走到实际显示

### Layout Inspector、Composition Tracing 与 Macrobenchmark 分工

- Layout Inspector 的重组与跳过计数适合确认失效范围。Debug 构建和 Inspector 本身会改变耗时，不能把它的时间数据当作发布版本的帧耗时基线。
- Compose compiler report 适合核对 restartable、skippable 和 Stability 推断，不能显示运行时哪一帧发生了什么。
- Composition Tracing 能把单个 Composable 记录进 system trace（系统级时间轴）。系统 trace 默认没有这些细粒度工作片段；项目要加入 `androidx.compose.runtime:runtime-tracing`，设备需为 API 30 或更高，终端自定义 Perfetto 配置还要启用 `track_event` 数据源。
- Macrobenchmark 应运行可被性能工具分析（profileable）、不可调试（non-debuggable）、接近发布配置（release-like）的构建，覆盖冷启动、首屏、稳定滚动和主要交互。升级 Compose 后重新采集 Baseline Profile；它记录应用热路径，帮助运行时提前编译关键代码。新旧结果要在相同设备状态、刷新率和数据集下比较。

下面的依赖片段故意保留 BOM `2025.12.00`，用于复现 Compose `1.10.0` 的历史现场；新建当前基线实验时应使用 BOM `2026.08.00`。两种写法都让 BOM 决定 `runtime-tracing` 的版本。

```kotlin
val composeBom = platform("androidx.compose:compose-bom:2025.12.00")
implementation(composeBom)
implementation("androidx.compose.runtime:runtime-tracing")
```

依赖加入后仍要确认被测 APK 保留 tracing 支持，并使用适合性能测量的构建。自定义 trace 没有 `track_event` data source 时，不能因为搜索不到 Composable 名就断言没有重组。

### Perfetto 按四段定位耗时

1. **Composition**：目标状态写入后，哪些重启作用域被标记失效；函数是否因参数或内部状态重新执行；Lazy 预取是否把目标列表项的 `compose` / `apply` 前移。
2. **Layout 与 Drawing**：Composition 正常时，检查 `measure`（测量）、`placement`（摆放）、`draw`（绘制）、图层更新和 `requestLayout()` / invalidation 的来源。Lazy 列表项在 precompose 后仍可能把 premeasure 或可见布局成本留给后续帧。
3. **HWUI 与 buffer 提交**：UI 线程按时完成后，检查 `syncAndDrawFrame()`、RenderThread `DrawFrame`、`dequeueBuffer`（申请可写缓冲区）、GPU 工作和 `queueBuffer()`（提交完成的缓冲区）。
4. **显示出口**：用目标应用窗口的 FrameTimeline（把应用帧与实际显示结果关联起来的时间线）、`BufferTX - <layerName>` 图层事务片段、latch（SurfaceFlinger 选中并接收该缓冲区）、HWC composition 与 actual present（真正上屏的时间）判断应用提交之后的延迟。

刷新率决定单帧预算，不能把 `16.67 ms` 或任意一条固定毫秒线套到所有设备。Compose 工作片段变短也不等于屏幕更早显示；比较应追到同一帧的 actual present。

## Compose 与 View 互操作

### RecyclerView 中的 `ComposeView`

Compose UI `1.12.0` 的默认 `ViewCompositionStrategy` 是 `DisposeOnDetachedFromWindowOrReleasedFromPool`。pooling container 指 RecyclerView 这类会暂存并复用子 View 的容器：不在这类容器中时，View 从窗口 detach（分离）会销毁 Composition；位于其中时，临时 detach 不会立即销毁，容器从窗口分离或列表项被复用池淘汰时才释放。

ViewHolder 中应让 `setContent()` 只执行一次，再用可观察状态绑定数据。下面的 `key(model.id)` 会把列表项的身份切换明确告诉 Composition，避免 ViewHolder 复用时把 `remember` 状态带给另一条数据。

```kotlin
class ComposeItemHolder(
    context: Context,
) : RecyclerView.ViewHolder(ComposeView(context)) {
    private val composeView = itemView as ComposeView
    private var model by mutableStateOf<FeedItem?>(null)

    init {
        composeView.setContent {
            model?.let { current ->
                key(current.id) {
                    FeedRow(current)
                }
            }
        }
    }

    fun bind(value: FeedItem) {
        model = value
    }

    fun clear() {
        model = null
    }
}
```

`onViewRecycled()` 可以清空业务数据和外部资源，不应无条件调用 `disposeComposition()`；默认策略保留池内 Composition 是为了复用。Fragment XML 中的一对一 `ComposeView` 更适合 `DisposeOnViewTreeLifecycleDestroyed`，它会跟随下一次 attach 所在 View tree 的 `LifecycleOwner`（提供生命周期的所有者）销毁。

### Lazy 列表中的 `AndroidView`

`AndroidView.factory` 在 UI 线程创建 View，并且对当前实例只调用一次；`update` 会在 factory 后调用，后续还会随其中读取的 `State` 变化而运行。重操作不能塞进 `update`，但 View 属性修改仍应留在 UI 线程。

Lazy 列表中要使用带非空 `onReset` 的重载，才能让兼容的 View 实例参与复用。下面的例子在旧数据解绑、新数据绑定之前清理瞬时状态，并在永久离开 Composition 时释放资源。

```kotlin
LazyColumn {
    items(
        items = charts,
        key = ChartModel::id,
    ) { model ->
        AndroidView(
            factory = { context -> ChartView(context) },
            update = { view -> view.render(model) },
            onReset = { view -> view.resetForReuse() },
            onRelease = { view -> view.release() },
        )
    }
}
```

`onReset` 可能紧接着进入下一次 `update`，也可能先进入暂时停用状态，之后才被释放；清理逻辑应允许重复调用。若嵌入的是 `SurfaceView`、WebView、播放器或相机预览，图形分析还要跟随它自己的 BufferQueue 和 SurfaceFlinger layer，不能只看 Compose 宿主窗口。

## Effect 与 producer 的生命周期盲区

`rememberCoroutineScope()` 适合由点击、拖动等事件启动工作；需要随 key 进入、变化和退出自动管理的持续任务，应直接使用 `LaunchedEffect(key)`。把任务从 Effect 再转交给 `rememberCoroutineScope()` 保存的作用域，会让 key 变化只取消“启动者”，旧任务却继续消费旧数据。Composition 离开时，`Job.cancel()` 只是向协程传播取消信号；阻塞 I/O、没有检查取消的 CPU 循环、耗时的 `NonCancellable` 清理和未注销的外部回调都可能延长退出时间。验证时应查看任务的 `finally`、订阅计数和资源所有者，不能仅凭“页面退出后对象还在”判定泄漏。

`produceState` 的实现组合了由 `remember` 保留的 `MutableState` 和带 key 的 `LaunchedEffect`：key 变化会取消旧 producer，但不会新建状态容器。需要在切换用户或请求时立即显示“加载中”，producer 必须显式赋值；回调式数据源用 `awaitDispose` 解除注册，长期 Flow 则依靠 `collect` 自身的取消与 `finally`。无限收集不会自然返回，因此不要把 `awaitDispose` 写在它后面。

`State` 的 conflation（合并更新）只会过滤相等结果，或让观察者跳过来不及读取的中间值；它不会减少上游网络请求、解析和每次赋值。高频源要在数据层明确采用 `sample`（按周期取样）、`conflate`（消费跟不上时只保留较新值）、`distinctUntilChanged`（过滤连续相等值）或领域聚合。多个数据源必须共同满足一条业务约束时，应先在 ViewModel 产出一份不可变 `UiState`，不能期待两个独立 producer 恰好在同一帧完成。

Strong Skipping 只改变可组合调用和 lambda 的跳过机会，不改变作用域中的 Job、Effect key、状态变更策略（State mutation policy，判断新旧值是否等价）或 producer 取消语义。Pausable Composition 也只切分尚未 apply 的 Composition；已经启动的网络请求、Flow 收集协程和回调不会随它自动暂停。

## 升级与验收

升级 Kotlin 或 Compose 时，先记录解析后的精确依赖。下面的命令用于确认应用模块的 Runtime、Foundation 和 UI 版本；configuration（依赖配置）名称按项目的构建 variant 调整。

```bash
./gradlew :app:dependencyInsight \
  --dependency androidx.compose.runtime:runtime \
  --configuration releaseRuntimeClasspath

./gradlew :app:dependencyInsight \
  --dependency androidx.compose.foundation:foundation \
  --configuration releaseRuntimeClasspath

./gradlew :app:dependencyInsight \
  --dependency androidx.compose.ui:ui \
  --configuration releaseRuntimeClasspath
```

BOM 只约束它声明的 Compose artifacts（依赖模块），不会自动添加依赖，也不控制 Kotlin plugin。版本确认后再做同机对比，避免把 Kotlin 编译器、Foundation 预取、Baseline Profile 或业务代码的变化混成一个结果。

验收可以按下面的顺序执行：

1. 用 compiler report 确认目标 Composable 的 restartable / skippable 与参数 Stability，不为无性能问题的类型追加注解。
2. 用 Layout Inspector 复现一次状态变化，确认重组和跳过范围符合预期。
3. 用 Macrobenchmark 采集 release-like 构建，比较 FrameTiming、启动、内存和目标交互的分位数，例如中位数与 P95，而非只看平均值。
4. 用 Composition Tracing 关联目标 Composable、Lazy prefetch、Layout、Drawing 与同一帧 `Choreographer#doFrame` 帧回调。
5. 沿 RenderThread、BLAST、SurfaceFlinger、HWC 到 actual present 闭合显示链，区分 App 生产慢与系统显示慢。
6. 升级 Compose 后重新生成并验证应用 Baseline Profile；库自带 profile 不能覆盖业务 Composable 的完整热点路径。

| 现象 | 优先验证 | 常见误判 |
| --- | --- | --- |
| 小状态变化引发大范围重组 | 状态读取位置、重启作用域、参数实例 | 只给所有数据模型加 `@Stable` |
| 动画期间 Composition 持续出现 | 状态是否可延迟到 placement / drawing | 把每次变化都包进 `derivedStateOf` |
| Lazy 滚动进入新列表项时卡顿 | `key`、`contentType`、`compose` / `apply` / `measure` 预取 | 只把缓存窗口调大 |
| `ComposeView` 列表反复创建 | `setContent()` 次数、`ViewCompositionStrategy`、列表项身份 | 每次回收都调用 `disposeComposition()` |
| UI 线程正常仍有卡顿（jank） | RenderThread、缓冲区、SurfaceFlinger、HWC、actual present | 把所有慢帧归到重组 |

这五类现象都要先定位工作发生在哪个阶段，再决定改状态读取、列表身份、预取参数还是显示链；单看重组次数或某一个开关不足以完成验收。

## 源码与文档

- [Compose BOM `2026.08.00` POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom)：核对当前 Runtime、Foundation 与 UI 的 `1.12.0` 映射；[BOM mapping](https://developer.android.com/develop/ui/compose/bom/bom-mapping) 用于按 BOM 查询库版本。
- [Compose Runtime 1.12.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.12.0/runtime-1.12.0-sources.jar)、[Compose Foundation 1.12.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/1.12.0/foundation-1.12.0-sources.jar)、[Foundation Android 1.12.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.12.0/foundation-android-1.12.0-sources.jar) 与 [Compose UI Android 1.12.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.12.0/ui-android-1.12.0-sources.jar)：核对当前状态、Lazy 预取、缓存窗口、`ComposeView` 和 `AndroidView` 实现。
- [Kotlin releases](https://kotlinlang.org/docs/releases.html) 与 [Compose compiler options DSL](https://kotlinlang.org/docs/compose-compiler-options.html)：核对 Kotlin `2.4.10`、Strong Skipping 默认行为和编译器选项。
- [Compose BOM `2025.12.00` POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2025.12.00/compose-bom-2025.12.00.pom)：核对 Runtime、Foundation 与 UI 的 `1.10.0` 映射。
- [Compose Runtime 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.10.0/runtime-1.10.0-sources.jar)：`PausableComposition`、`ProduceState`、`DerivedState` 与 Snapshot 状态。
- [Compose Foundation 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/1.10.0/foundation-1.10.0-sources.jar) 与 [Android source jar](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.10.0/foundation-android-1.10.0-sources.jar)：Lazy 缓存窗口、预取状态与 Android 调度器。
- [Compose UI Android 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.10.0/ui-android-1.10.0-sources.jar)：`ComposeView`、`ViewCompositionStrategy` 与 `AndroidView`。
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)、[Compose phases](https://developer.android.com/develop/ui/compose/phases) 与 [Side-effects](https://developer.android.com/develop/ui/compose/side-effects)：编译器跳过、状态读取阶段和 Effect 契约。
- [Diagnose stability issues](https://developer.android.com/develop/ui/compose/performance/stability/diagnose) 与 [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)：编译器报告、重组计数与 system trace 配置。
- [Compose Foundation release notes](https://developer.android.com/jetpack/androidx/releases/compose-foundation#1.10.6)：Pausable Composition 开关在 `1.10.6` 的默认值变化。
- [Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views) 与 [Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)：pooling container、Fragment 生命周期和 `AndroidView` 复用。
- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java) 与 [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：平台帧调度与 App Window traversal 基线。
