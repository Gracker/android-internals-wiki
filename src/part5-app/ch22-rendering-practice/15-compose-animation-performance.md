---
title: "Jetpack Compose 动画性能实战"
chapter: "22.15"
section: "22.15"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Compose BOM 2026.08.00 / Compose 1.12.0 source JAR；Android 17 android-17.0.0_r1"
confidence: high
sources:
  - type: research
    path: "DeepResearch/2026-06-01-android-compose-animation-performance-bottlenecks.md"
  - type: research
    path: "DeepResearch/2026-06-02-android-compose-110-strong-skipping-mechanism.md"
  - type: research
    path: "DeepResearch/2026-06-02-android-compose-derivedstate-sso-deep-source-analysis.md"
tags: [compose, animation, animated-visibility, transition, animatable, strong-skipping, performance]
related_chapters: ["22.3", "22.5", "7.7", "2.11"]
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/32-compose-infinite-animation-vector-converter-performance.md"
  - "src/part5-app/ch22-rendering-practice/44-compose-pager-advanced-animations.md"
---

# Jetpack Compose 动画性能实战

Compose 动画每帧会做多少工作，取决于动画值在哪个阶段读取、哪些阶段因此失效、过渡期间保留多少界面内容，以及应用提交帧后的显示过程。本文以 Compose BOM 2026.08.00 对应的 Compose 1.12.0 为库版本基线，以 Android 17、API 37 的 `android-17.0.0_r1` 为平台基线。Compose 独立于 Android 平台发布，不能用 API 37 推导 Compose 行为。

普通 Compose 页面仍由宿主应用窗口的硬件加速界面渲染系统（HWUI）生成画面。状态计算，以及部分组合（Composition）、布局（Layout）和绘制（Draw）工作发生在主线程；`RenderThread` 整理硬件绘制命令，GPU 执行命令，BLAST 负责传递图形缓冲区，`SurfaceFlinger` 与硬件合成器（Hardware Composer，HWC）完成系统合成和送显。完整边界见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)。本文只讨论动画额外增加的工作。

## 1. 用状态读取阶段判断动画成本

`Animatable.value`、`Transition.animate*` 和 `animate*AsState` 返回的动画值都受 Compose 快照（Snapshot）系统观察。API 名称不会预先决定失效阶段；在哪个阶段读取动画值，值变化时就会请求哪个阶段再次执行。一个值若在多个阶段读取，也会建立多处观察关系。

| 动画值的读取位置 | 值变化后的主要工作 | 常见写法 | 判断要点 |
| --- | --- | --- | --- |
| 可组合函数体 | 组合；后续是否进入布局、绘制取决于输出变化 | `Box(Modifier.alpha(alpha))` 中先在函数体读取 `alpha` | 高频值容易让当前重组作用域逐帧执行 |
| 测量或放置回调（lambda） | 布局的相应子阶段，随后绘制 | `Modifier.offset { IntOffset(x, 0) }` | 可跳过组合，但位置或尺寸变化仍有布局成本 |
| 绘制回调 | 绘制 | `drawBehind { drawRect(color) }` | 适合颜色、路径参数和 `Canvas` 内容 |
| `graphicsLayer {}` 回调 | 图层属性更新与绘制提交 | `graphicsLayer { translationX = x }` | 不重组、不重新测量；仍会产生 `RenderThread`/GPU 工作 |

`drawWithCache` 也会观察缓存构建代码中读取的 `State`，依赖变化时会重建缓存。绘制阶段并没有统一关闭 Snapshot 读取观察。把高频值延后到绘制回调或图层回调中读取，组合阶段才无需处理这次更新。

下面的示例用于把透明度动画值延后到图层属性更新。

```kotlin
@Composable
fun FadingPanel(
    visible: Boolean,
    content: @Composable () -> Unit,
) {
    val alpha = remember { Animatable(if (visible) 1f else 0f) }

    LaunchedEffect(visible) {
        alpha.animateTo(if (visible) 1f else 0f)
    }

    Box(
        Modifier.graphicsLayer {
            this.alpha = alpha.value
        }
    ) {
        content()
    }
}
```

这里的 `alpha.value` 只在 `graphicsLayer` 回调中读取，所以透明度变化不会要求 `FadingPanel` 逐帧重组或重新布局。透明度低于 1 时，图层可能需要中间合成；减少主线程工作不表示 GPU 无需工作。应在目标设备上同时观察界面线程、`RenderThread` 和帧时间线（`FrameTimeline`）。

## 2. 动画时钟与 Android 17 帧时间

Compose 1.12.0 的 `AndroidUiFrameClock.withFrameNanos()` 会注册 `Choreographer.FrameCallback`。`Transition` 和 `Animatable` 的逐帧循环都通过 `withFrameNanos` 一类接口等待下一帧。Android 上没有一套脱离 `Choreographer`、按固定间隔自行计时的 Compose 界面时钟。

主线程及时收到回调时，动画按本次帧时间计算已经播放的时长。主线程被阻塞后，回调会延迟；下一次执行看到更大的时间差，动画值会向前跳。Compose 不会补画所有错过的中间帧，用户通常会看到画面停顿后直接跳到较后的状态。

Android 17 的 `Choreographer.FrameData` 同时携带候选帧时间线、首选帧时间线、截止时间和预计呈现时间。性能判断应使用当前帧的截止时间，或 `FrameTimeline` 中的预期/实际结果，不能把 16.6 ms、11.1 ms、8.3 ms 固化成设备常量。可变刷新率、帧率请求和调度选择都会改变某一帧可用的时间。

Perfetto 中的 `Choreographer#doFrame` 区间事件（slice）覆盖应用主线程回调，不包含应用 GPU 完成、图形缓冲区入队后的 SurfaceFlinger 合成和送显。它变长只能证明主线程帧回调变长，不能单独代表端到端帧耗时。

## 3. Animatable：互斥动画与手势跟随

`Animatable<T, V>` 内部持有 `AnimationState`，其 `value` 由 `mutableStateOf` 保存。它提供数值连续性、边界约束、速度信息和互斥控制；读取位置仍会决定失效阶段，不能假定它只触发绘制。

同一个 `Animatable` 启动新的 `animateTo`、`animateDecay`、`snapTo` 或 `stop` 时，`MutatorMutex` 会取消正在运行的变更。新的 `animateTo` 从当前值继续；弹簧动画（spring）还会延续当前速度。取消会以 `CancellationException` 沿协程父子关系传播，需要释放的资源应在 `finally` 中清理。

手指位置直接跟随适合在拖动期间使用 `snapTo`，松手后再用 `animateDecay` 或 `animateTo` 收尾。每个触摸采样点都调用 `animateTo`，会连续取消前一个动画，产生与输入延迟、动画参数和采样频率有关的追赶效果。若产品需要这种柔性跟随，可以保留，但它仍有逐帧更新和协程取消的成本。

API 选择可以按控制语义划分：

- 单个或少量数值、协程中顺序控制、手势打断：`Animatable`。
- 一个离散状态协调多项属性：`Transition`。
- 单值随目标自动过渡，且无需等待完成或主动取消：`animate*AsState`。
- 内容进入、退出或替换：`AnimatedVisibility`、`AnimatedContent`。

无关组件各自维护状态迁移，更容易限定生命周期。跨组件共享一个 `Transition` 虽然能减少对象数，却会把状态、取消和完成条件耦合在一起，不能作为通用优化。

## 4. Transition 会参与组合

`updateTransition(targetState)` 是可组合函数。Compose 1.12.0 会在当前位置通过 `remember` 保存一个 `Transition`，随后调用 `animateTo(targetState)`，并用 `DisposableEffect` 处理离开组合时的清理。参数或被观察的 `State` 变化仍可能让相关可组合函数重新执行，`Transition` 并不提供“组合永不重启”的语义。

`Transition` 让多个子动画共享状态迁移和帧进度，也支持运行中改变目标。目标变化时，它会更新由起点和终点组成的迁移段（segment）及目标；不同动画参数对中断连续性的处理不同，不能一概描述成“每次切换都从头重启”。

是否对快速点击做防抖（debounce）属于交互约束：

- 若每次输入都有效，允许动画重新定向，并检查中断后的连续性。
- 若后端操作或导航只允许一次，按业务状态屏蔽重复输入。
- 若需要观察进入、退出是否结束，使用 `MutableTransitionState.isIdle` 与 `currentState`。

Compose 1.12.0 已弃用接收 `MutableTransitionState` 的 `updateTransition` 重载，应改用 `rememberTransition(transitionState)`；接收普通目标值的 `updateTransition(targetState)` 仍可使用。`MutableTransitionState` 提供可观察的状态迁移入口，本身不会减少每帧工作。1.12.0 的 `DeferredTransitionState` 与 `mutableTransform` 面向预测性返回等“先手动改变属性、再启动自动过渡”的场景，也不是通用性能开关。

## 5. AnimatedVisibility：尺寸变化和退出内容保留

`AnimatedVisibility` 使用自定义 `Layout` 承载界面内容。普通 `AnimatedVisibility(visible=...)` 的测量策略会测量子项，以最大宽高作为容器尺寸，并把子项放在坐标 `(0, 0)`；Row/Column 作用域重载有各自适配的默认过渡。普通重载的默认进入/退出动画包含展开和收缩，因此容器报告给父布局的尺寸会随动画变化；依赖该尺寸的父容器和同级元素也可能反复测量或放置。

不同过渡类型产生的工作不同：

- 淡入淡出和缩放主要更新图层属性。
- 滑动会改变子项的放置偏移量，不缩小容器报告的尺寸，但仍会执行 `LayoutModifier` 的放置逻辑。
- 展开和收缩会产生尺寸动画。
- 子内容自身的尺寸变化、`animateContentSize` 或自定义布局修饰符还可能增加布局工作。

如果父布局无须跟随内容伸缩，可以给外层稳定约束，并在内部使用淡入淡出、缩放或滑动。裁剪（clip）只限制绘制范围，不会阻止尺寸变化传给父布局。

退出时，界面内容会保留到内建进入/退出动画，以及注册在 `AnimatedVisibilityScope.transition` 上的自定义动画全部完成。保留期间有以下生命周期行为：

- 内容仍在组合中，也会响应自己观察的 `State`。
- `LaunchedEffect` 和 `rememberCoroutineScope` 启动的任务尚未因离开组合而取消。
- `DisposableEffect.onDispose` 尚未执行。
- 内容持有的图片、订阅和其他对象仍然存活。

独立创建的 `animate*AsState` 不属于 `AnimatedVisibilityScope.transition`，容器不知道它何时结束，因而可能先移除内容。需要与退出完成同步的自定义动画，应注册到作用域提供的 `transition` 上。

缩短退出时长只能缩短保留窗口，没有一个适用于所有产品的固定毫秒数。内容很重时，可把昂贵订阅移到更高层统一管理，或在退出开始后停止不再需要的数据更新；这属于业务生命周期设计，不能靠 `visible=false` 自动完成。

## 6. AnimatedContent：过渡期间新旧内容共存

`AnimatedContent` 切换目标时会同时查找新旧状态对应的界面内容。新内容执行进入动画，旧内容执行退出动画；旧内容在退出完成后才从组合中移除。默认 `SizeTransform` 还会为容器尺寸变化创建动画。快速连续切换时，可能同时保留多份尚未退出的内容。

使用 `AnimatedContent` 时要评估：

- 新旧内容同时参与组合、测量和绘制的成本。
- 旧内容在退出期间保留的副作用任务与资源。
- `SizeTransform` 是否让父布局持续变化。
- 目标状态变化频率是否高于用户能够辨认的切换频率。

内容回调必须使用它收到的 `targetState` 参数构建对应内容。`contentKey` 定义哪些目标状态属于同一内容身份；两个目标状态映射到同一个键时，不会触发内容切换动画。它适合过滤“状态对象改变但视觉身份不变”的更新，不能用来掩盖错误的状态建模。

`AnimatedVisibility` 适合一个内容节点的出现与消失，`AnimatedContent` 适合不同内容身份之间的替换。两者都可能保留退出内容，也都可能触发布局；应按业务语义和跟踪结果选择。

## 7. produceState、snapshotFlow 与 derivedStateOf

`produceState` 用 `remember { mutableStateOf(initialValue) }` 保存结果，并由 `LaunchedEffect` 启动负责生产状态值的协程。它提供无键、单键和多键重载；这里的键是决定协程何时重启的输入，不能把实现概括为固定的 `LaunchedEffect(Unit)`。键改变时，旧协程会取消并启动新协程；离开组合时也会取消。对回调式数据源，可用 `awaitDispose` 注销回调。

返回的 `State` 会合并相等值；写入与当前值相等的结果不会触发重组。不同值若按帧更新，下游仍会按其读取阶段失效。`produceState` 适合把外部异步或订阅式数据转成 Compose `State`；外部数据频率高不构成误用，判断依据是界面是否需要每个样本，以及读取位置是否合适。

`snapshotFlow` 把 Snapshot `State` 读取转换成冷流（cold Flow，即有人收集时才开始执行），适合驱动埋点、持久化等副作用。`distinctUntilChanged`、`sample` 或 `debounce` 会改变事件或时间语义，不适合替代屏幕上的逐帧动画。

`derivedStateOf` 适合输入变化频繁、输出变化较少的派生结果。例如滚动偏移不断变化，而界面只关心“是否越过阈值”。它根据派生结果的相等性策略决定是否通知读取方。若派生结果每帧都不同，`derivedStateOf` 只会增加观察与计算开销。

## 8. 强跳过模式能解决什么

强跳过模式（Strong Skipping）从 Kotlin 2.0.20 起默认启用。启用后，可重启的可组合函数即使带有不稳定参数，也可以被标记为允许跳过；稳定参数仍用对象相等性比较，不稳定参数则用实例相等性比较。编译器还会自动记忆可组合函数内的 lambda，并用它捕获的值作为键。

这些规则主要减少父级重组向子级传播，以及 lambda 的重复分配。它们不会改变以下行为：

- 可组合函数体直接读取的动画 `State` 变化后，读取作用域仍会失效。
- 布局、绘制或图层回调中的 `State` 读取仍由对应阶段观察。
- 跳过一个可组合函数不会暂停 `LaunchedEffect` 或 `rememberCoroutineScope` 的任务。
- `State` 更新不会因为某个可组合组被跳过而推迟到未来某次组合；对应观察者仍会按 Snapshot 机制收到失效通知。

较省工作的写法是捕获稳定的 `State` 持有者，在布局、绘制或 `graphicsLayer` 回调内读取其值。若先在可组合函数体中把 `State` 读取成每帧变化的标量，再让回调捕获这个标量，组合阶段已经建立了高频读取关系。

不要为了动画批量添加 `@NonRestartableComposable` 等编译器注解。它们会改变重组入口和可跳过性，只有编译器报告、基准数据和明确热点同时支持时才值得调整。

## 9. Lazy 列表中的动画所有权

惰性布局（Lazy layout）决定哪些列表项进入、保留或离开组合，预取和保留策略也由它控制。列表项内部的 `AnimatedVisibility` 只能管理该项仍在组合时的内容退出；当列表项离开 `LazyColumn` 的管理范围后，它不能要求外层继续保留退出动画。

列表数据的新增、删除和重排应优先使用稳定且唯一的键，配合 `Modifier.animateItem()`；列表项内部局部区域的显示隐藏再使用 `AnimatedVisibility`。这样可以分别处理数据项身份变化与项内内容可见性。

`rememberInfiniteTransition` 在宿主仍处于组合时持续请求动画帧。在可组合函数体读取它返回的值会触发组合；在绘制或图层回调中读取，才能把更新限定到后续阶段。离屏列表项是否仍在运行，取决于惰性布局是否仍保留该项，不能只根据像素是否可见推断。

大量列表动画的检查项包括：

- 列表项是否有稳定且唯一的键。
- 同屏活跃动画数量是否随滚动或数据更新持续增长。
- 离屏后已无产品价值的无限动画是否及时离开组合。
- 展开/收缩、`animateContentSize` 和列表项位置动画是否叠加触发布局。
- 图片、模糊、阴影和透明度图层是否把瓶颈移到 `RenderThread` 或 GPU。

## 10. 从 Compose 阶段看到显示结果

`graphicsLayer`、绘制回调或跳过组合，只会改变应用生成帧前半程的工作量。标准 HWUI 页面仍要经过 `RenderThread`、GPU、应用窗口的图形缓冲区提交、SurfaceFlinger 和 HWC。透明度、裁剪、模糊、复杂路径或较大的离屏图层可能减少主线程工作，同时增加 GPU 或内存带宽成本。

`ComposeView` 与 View 动画共用窗口和主线程帧回调；`AndroidView` 也不会得到独立帧预算。混合页面应通过同一条 `FrameTimeline` 分析 View 树遍历、Compose 工作、`RenderThread` 和系统合成，不能把某个跟踪区间当成整帧耗时。

Android 17 的内核基线是 `android17-6.18-2026-06_r6`。内核调度器、CPU 调频（cpufreq）、热限制（thermal）和同步栅栏等待（fence wait）会影响线程何时运行或等待，却不定义 `Animatable`、`Transition` 和内容移除的语义。跟踪数据出现线程可运行但迟迟未获调度、频率受限或栅栏等待时，再检查内核证据；只凭动画卡顿不能归因给调度器。

## 11. Perfetto、Studio 与线上指标各看什么

一次排查可以按以下顺序进行：

1. 在发布（release）、可分析（profileable）且不可调试（non-debuggable）的构建上复现固定交互。
2. 用 `FrameTimeline` 对齐预期与实际时间线，确认哪些帧迟到，以及应用是否按时完成。
3. 查看主线程 `Choreographer#doFrame`、Compose 组合跟踪、布局和绘制相关区间。
4. 查看 `RenderThread`、GPU、应用窗口缓冲区入队和 SurfaceFlinger，避免把 GPU 或送显时间算进 `doFrame`。
5. 将慢帧对应到动画状态、目标切换、仍然活跃的内容数量和状态读取阶段。

工具的职责要分开：

- **组合跟踪（Composition tracing）**：在系统跟踪数据中显示可组合函数调用，适合定位重组代码和耗时。
- **Layout Inspector**：显示运行中可组合函数的组合/跳过计数，适合验证重组范围；连接工具本身有开销。
- **Animation Preview**：可以暂停动画、拖动时间轴并检查动画值，适合验证曲线与多动画协调；它不分析真实运行时性能。
- **FrameTimeline**：把应用帧和 SurfaceFlinger 帧的预期/实际时间，以及卡顿类型放在同一时间轴上。
- **JankStats**：给线上帧数据附加页面或交互状态，便于按场景聚合。

`FrameMetrics.ANIMATION_DURATION` 表示一帧中发出动画回调所用的时间。它不能区分“动画帧”和“非动画帧”，也不覆盖整帧。Android 12 及以上更适合关注 `FrameTimeline` 派生的超期时间（overrun）；线上数据还要结合当前界面状态，避免把整页慢帧都归给某个动画。

## 12. 用 Macrobenchmark 建立回归门槛

动画基准要覆盖一次完整、可重复的状态迁移，并让测试知道动画何时结束。测试页面可以在 `MutableTransitionState.isIdle` 变为 `true` 后，暴露一个只供测试识别的语义属性或测试标签（test tag）。

下面的骨架用于采集展开动画的 FrameTimingMetric。

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class ExpandAnimationBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun expand() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(FrameTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.WARM,
        setupBlock = {
            startActivityAndWait()
            device.findObject(By.res("reset_collapsed")).click()
            device.waitForIdle()
        },
    ) {
        device.findObject(By.res("toggle_animation")).click()
        check(
            device.wait(
                Until.hasObject(By.res("animation_idle_expanded")),
                2_000,
            )
        )
    }
}
```

`toggle_animation`、`reset_collapsed` 和完成标记需要通过 `testTagAsResourceId` 或真实资源 ID 暴露。完成标记应在目标状态达到且 `Transition` 空闲后出现，避免只测到动画起点。每轮准备阶段都回到同一初始状态，测量区间只包含目标交互。

应同时关注 `frameOverrunMs` 的 P50/P90/P95/P99、`frameDurationCpuMs` 和 `frameCount`。`frameOverrunMs` 在 API 31 及以上按每帧截止时间计算，能适应高刷新率和可变帧率；`frameDurationCpuMs` 只覆盖界面线程与 `RenderThread` 生成一帧所用的 CPU 时间。`frameCount` 是辅助指标：它变化时，可能表示实现减少或增加了请求帧数量，不能只比较耗时分位值。`FrameTimingMetric` 不提供通用的 `jankFrameCount`，也不应按固定 16.6 ms 自行推导卡顿帧数。

基准配置文件（Baseline Profile）可以让 Android 运行时（ART）提前编译关键用户流程覆盖的应用与库代码，减少首次运行时的解释执行和即时编译（JIT）成本。它不能预编译 GPU 着色器、消除离屏合成，也不会改变 Snapshot 失效范围。用同一组 Macrobenchmark 对比应用基准配置文件前后的数据，才能判断当前动画是否受编译状态影响。

## 13. 无限动画、VectorConverter 与资源动画

`rememberInfiniteTransition()` 表达“进入组合后持续运行，离开组合后停止”。同一个 `InfiniteTransition` 的子动画共享一条逐帧循环，不会为每个值注册独立 VSync；每个子项仍要维护状态并计算插值。只给组件设置 `alpha = 0f`、移到屏外或用其他内容遮挡，都不会使它离开组合。加载指示、呼吸光和背景粒子不可见且无需继续计时时，应让对应分支移出组合，或由业务状态停止动画。

系统动画时长缩放为 0 时，Compose 会把无限动画推进到目标值并等待缩放恢复，不会继续逐帧更新。产品要验证该目标值能否作为合理的静止画面，并为“减少动态效果”保留易于理解的界面状态。

一组视觉值若能由同一相位推导，可以只保留一个 `animateFloat()`，在绘制或图层阶段计算颜色、缩放和偏移。`TwoWayConverter<T, V>` 只负责业务值与 `AnimationVector1D`～`4D` 的双向映射；每个维度应对应一个独立变量，并明确单位和有效范围。若 `convertFromVector()` 每帧都会创建复杂对象，应比较改用内置标量动画或单一相位推导后的对象分配量。

Animated Vector XML 使用另一套资源机制：`AnimatedImageVector` 解析矢量图和动画器资源，并按动画进度绘制，不经过 `TwoWayConverter`。资源应按 ID 稳定记忆，避免在动画帧内重复解析；路径节点、关键帧和同时播放数量仍需在目标设备上测量。

## 14. Pager 动画：区分当前页、稳定页和目标页

Pager 的 `currentPage` 表示最接近吸附位置的页面，会在拖动跨过吸附判定点时变化，不代表滚动已经完成。`settledPage` 只在滚动和动画停止后更新，适合曝光、重资源归属和业务选中；`targetPage` 表示本次滚动预计停下的页面，可用于动画目标。任意页面到当前吸附位置的距离应使用 `getOffsetDistanceInPages(page)`，避免手写公式在 `currentPage` 切换时反转符号。

页面的透明度、缩放、旋转和平移值应在 `graphicsLayer {}` 中读取，让滚动只更新图层属性；在可组合函数体提前读取 `currentPageOffsetFraction`，会让依赖该值的页面持续重组。延后读取高频状态并不会消除动画成本，裁剪、阴影、透明度和大面积旋转仍可能增加离屏合成与 GPU 带宽。

`beyondViewportPageCount` 表示可见区域两侧额外组合、测量和放置的页面，不包含滚动方向上的内部预取页面；应从默认值开始逐页增加，并同时比较首次进入页面的组合/测量耗时、内存峰值与预取命中率。`visiblePagesInfo` 是随测量频繁更新的结果，不代表页面生命周期。视频、地图和 `WebView` 等重资源应由 `settledPage`、可见性和生命周期共同控制。

同向嵌套的 Pager/惰性容器要明确哪个容器消费嵌套滚动、惯性滚动如何交接，以及子容器到达边界后是否继续滚动父容器。负 `pageSpacing` 产生重叠时，还要验证 `zIndex` 层叠顺序、命中区域、裁剪和无障碍顺序。点击标签页启动的 `animateScrollToPage()` 可能被新手势或新的滚动操作取消；调用返回后，还要根据状态确认目标页是否已经稳定展示。

## 15. 检查清单

- 动画值在哪个阶段读取？是否在更早阶段也被解引用？
- 值变化后需要组合、测量、放置、绘制还是图层属性更新？
- `AnimatedVisibility` 或 `AnimatedContent` 退出期间保留了哪些内容、副作用任务和资源？
- 动画中途改变目标时，是重新定向、取消后续工作，还是由产品层屏蔽输入？
- `produceState` 的键是否完整，外部订阅是否在 `awaitDispose` 中注销？
- `derivedStateOf` 的输出是否比输入低频？
- 惰性列表项的身份变化是否由稳定键和 `animateItem` 管理？
- 帧预算是否来自本帧 `FrameTimeline`，是否同时核对应用、GPU 与送显？
- Android Studio 工具、实验室基准和线上指标是否各自回答了合适的问题？
- 优化是否在发布版、可分析构建和代表性设备上复测？

## 16. 源码与资料索引

Compose 行为按 BOM 2026.08.00 与以下 1.12.0 source JAR 复核：

- [Compose BOM 2026.08.00 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom)。
- [`androidx.compose.animation:animation:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/1.12.0/animation-1.12.0-sources.jar)：`AnimatedVisibility.kt`、`AnimatedContent.kt`。
- [`androidx.compose.animation:animation-core:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation-core/1.12.0/animation-core-1.12.0-sources.jar)：`Animatable.kt`、`AnimationState.kt`、`Transition.kt`、`InfiniteTransition.kt`。
- [`androidx.compose.ui:ui-android:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.12.0/ui-android-1.12.0-sources.jar)：`AndroidUiFrameClock.android.kt`、`AndroidUiDispatcher.android.kt`、图层与绘制修饰符实现。

以下 1.10.0 链接保留为上一轮核验基线：

- [`androidx.compose.animation:animation:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/1.10.0/animation-1.10.0-sources.jar)：`AnimatedVisibility.kt`、`AnimatedContent.kt`。
- [`androidx.compose.animation:animation-core:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation-core/1.10.0/animation-core-1.10.0-sources.jar)：`Animatable.kt`、`AnimationState.kt`、`Transition.kt`、`InfiniteTransition.kt`。
- [`androidx.compose.ui:ui-android:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.10.0/ui-android-1.10.0-sources.jar)：`AndroidUiFrameClock.android.kt`、`AndroidUiDispatcher.android.kt`、图层与绘制修饰符实现。

平台和内核边界按固定标签复核：

- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)。
- [Android 17 `FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)。
- [`android17-6.18-2026-06_r6` kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)。

API 用法、性能工具和测量口径参考：

- [Compose Animation 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-animation)。
- [Compose 动画性能 quick guide](https://developer.android.com/develop/ui/compose/animation/quick-guide)。
- [Compose phases](https://developer.android.com/develop/ui/compose/phases)。
- [Graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)。
- [AnimatedVisibility 与 AnimatedContent](https://developer.android.com/develop/ui/compose/animation/composables-modifiers)。
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)。
- [Compose side effects 与 produceState](https://developer.android.com/develop/ui/compose/side-effects)。
- [Lazy list item animations](https://developer.android.com/develop/ui/compose/lists)。
- [Compose Pager](https://developer.android.com/develop/ui/compose/layouts/pager)。
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)。
- [Layout Inspector 调试 Compose](https://developer.android.com/develop/ui/compose/tooling/debug)。
- [Animation Preview](https://developer.android.com/develop/ui/compose/tooling/animation-preview)。
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)。
- [Macrobenchmark FrameTimingMetric](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)。
- [Compose Baseline Profile](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)。
