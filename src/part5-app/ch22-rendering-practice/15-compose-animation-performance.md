---
title: "Jetpack Compose 动画性能实战"
chapter: "22.15"
section: "22.15"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-05"
last_verified_against: "AndroidX androidx-main 分支 Compose Runtime/Animation 源码；Compose BOM 2025.12.00 行为"
confidence: medium-high
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

Compose 动画每帧会做多少工作，取决于动画值在哪里被读取、哪些阶段因此失效、过渡期间保留了多少内容，以及 App 交帧后的显示链路。库版本基线为 Compose 1.10.0，平台基线为 Android 17 / API 37 的 `android-17.0.0_r1`。Compose 独立于 Android 平台发布，不能用 API 37 推导 Compose 行为。

普通 Compose 页面仍由宿主 App Window 的 HWUI 管线出图。状态计算和部分 Composition、Layout、Draw 工作发生在主线程，RenderThread、GPU、BLAST、SurfaceFlinger 与 HWC 继续负责后半程。完整边界见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)。这里聚焦动画给这条路径增加的工作。

## 1. 用“读取阶段”判断动画成本

`Animatable.value`、`Transition.animate*` 和 `animate*AsState` 返回的动画值都受 Snapshot 观察。API 名称不会预先决定失效阶段；读取发生在哪一阶段，值变化时就会请求哪一阶段重跑。一个值若在多个阶段读取，也会建立多处观察关系。

| 动画值的读取位置 | 值变化后的主要工作 | 常见写法 | 判断要点 |
| --- | --- | --- | --- |
| Composable 函数体 | Composition；后续是否 Layout、Draw 由输出变化决定 | `Box(Modifier.alpha(alpha))` 中先在函数体解引用 `alpha` | 高频值容易让当前重组作用域逐帧执行 |
| 测量或放置 lambda | Layout 的相应子阶段，随后 Draw | `Modifier.offset { IntOffset(x, 0) }` | 可绕过 Composition，但位置或尺寸变化仍有布局成本 |
| 绘制 lambda | Draw | `drawBehind { drawRect(color) }` | 适合颜色、路径参数和 Canvas 内容 |
| `graphicsLayer {}` lambda | 图层属性更新与绘制提交 | `graphicsLayer { translationX = x }` | 不重组、不重新测量；仍会产生 RenderThread/GPU 工作 |

`drawWithCache` 也会观察其构建块读取的 State，并在依赖变化时重建缓存。Draw 阶段没有普遍关闭 Snapshot 读观察。把高频值延后到 draw lambda 或 layer lambda，才能让 Composition 避开这次更新。

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

这里的 `alpha.value` 只在 `graphicsLayer` 的 block 内读取，所以透明度变化不会要求 `FadingPanel` 逐帧重组或重新布局。透明度低于 1 时，图层可能需要中间合成；省下主线程工作不等于 GPU 成本为零。应在目标设备上同时观察 UI thread、RenderThread 和 FrameTimeline。

## 2. 动画时钟与 Android 17 帧时间

Compose 1.10.0 的 `AndroidUiFrameClock.withFrameNanos()` 注册 `Choreographer.FrameCallback`。`Transition` 的帧循环和 `Animatable` 的动画循环都通过 `withFrameNanos` 一类接口等待下一帧。Android 上不存在一套脱离 `Choreographer`、自行匀速 tick 的 Compose UI 时钟。

主线程及时收到回调时，动画按这次帧时间计算 play time。主线程被阻塞后，回调会延迟；下一次执行看到更大的时间差，动画值会向前跳。它不会补画所有错过的中间帧。用户看到的现象通常是停顿后跳变。

Android 17 的 `Choreographer.FrameData` 同时携带候选 FrameTimeline、preferred timeline、deadline 和 expected presentation time。性能判断应使用当前帧的 deadline 或 FrameTimeline expected/actual 结果，不能把 16.6 ms、11.1 ms、8.3 ms 固化成设备常量。可变刷新率、帧率投票和调度选择都会改变某一帧可用的时间。

`Choreographer#doFrame` slice 覆盖 App 主线程回调，不包含 App GPU 完成、buffer post 之后的 SurfaceFlinger 合成和显示 present。它变长能证明主线程帧回调变长，不能单独代表端到端帧耗时。

## 3. Animatable：互斥动画与手势跟随

`Animatable<T, V>` 内部持有 `AnimationState`，其 `value` 由 `mutableStateOf` 支撑。它提供数值连续性、边界约束、速度信息和互斥控制；它没有“天然只触发 Draw”的保证。

同一个 `Animatable` 启动新的 `animateTo`、`animateDecay`、`snapTo` 或 `stop` 时，`MutatorMutex` 会取消正在运行的变更。新 `animateTo` 从当前值继续；spring 动画还会延续当前速度。调用方要允许 `CancellationException` 按结构化并发向外传播，清理资源时放在 `finally` 中。

手指位置直接跟随适合在拖动期间使用 `snapTo`，松手后再用 `animateDecay` 或 `animateTo` 收尾。每个 pointer sample 都调用 `animateTo` 会连续取消前一个动画，产生与输入滞后、动画规格和采样频率有关的追赶效果。若产品需要这种柔性跟随，可以保留；它不应被当成无成本的“每帧 snap”。

API 选择可以按控制语义划分：

- 单个或少量数值、协程中顺序控制、手势打断：`Animatable`。
- 一个离散状态协调多项属性：`Transition`。
- 单值随目标自动过渡，且无需等待完成或主动取消：`animate*AsState`。
- 内容进入、退出或替换：`AnimatedVisibility`、`AnimatedContent`。

多个无关组件各自维护自己的状态机更容易限定生命周期。为了减少对象数而跨组件共享一个 `Transition`，会把状态、取消和完成条件耦合在一起，不能作为通用优化。

## 4. Transition 会参与 Composition

`updateTransition(targetState)` 是 Composable。Compose 1.10.0 在当前位置 `remember` 一个 `Transition`，随后调用 `animateTo(targetState)`，并用 effect 管理离开 Composition 时的清理。参数或观察到的 State 变化仍可能让相关 Composable 重新执行；“非重启式组合”不是 `Transition` 的语义。

`Transition` 的价值在于让多个子动画共享状态迁移和帧进度，并支持中途改目标。目标变化时，运行中的 transition 会调整 segment 和目标；有些 animation spec 能保持较好的连续性，有些视觉上会出现拐点。不能统一描述成“每次 toggle 都从头重启”。

快速点击是否要 debounce 属于交互约束：

- 若每次输入都有效，保留 retarget，并检查中断后的连续性。
- 若后端操作或导航只允许一次，按业务状态屏蔽重复输入。
- 若需要观察进入、退出是否结束，使用 `MutableTransitionState.isIdle` 与 `currentState`。

`MutableTransitionState` 增加可观察的状态机入口，本身不会减少每帧工作。

## 5. AnimatedVisibility：尺寸变化和退出保留

`AnimatedVisibility` 使用自定义 `Layout` 承载 content。measure policy 会测量子项，以最大宽高作为容器尺寸，并把子项放在左上角。默认 enter/exit 包含 expand/shrink，所以默认配置常会改变对父布局可见的尺寸；父容器和兄弟若依赖这个尺寸，可能随动画反复测量或放置。

“所有 AnimatedVisibility 每帧都改尺寸”也不成立：

- fade 和 scale 主要更新图层属性。
- slide 改变子项的 placement offset，不缩小容器上报的尺寸，但仍有 LayoutModifier 的放置工作。
- expand/shrink 会产生尺寸动画。
- 子内容自身的尺寸变化、`animateContentSize` 或自定义 layout modifier 还可能增加布局工作。

如果父布局无须跟随内容伸缩，可以给外层稳定约束，并在内部使用 fade、scale 或 slide。`clip` 只裁剪绘制范围，不会阻止尺寸变化向父布局传播。

退出时，content 会保留到内建 enter/exit 动画和 `AnimatedVisibilityScope.transition` 上注册的自定义动画完成。保留期间会出现这些生命周期结果：

- content 仍在 Composition，仍可能响应自己观察的 State。
- `LaunchedEffect` 和 `rememberCoroutineScope` 启动的任务尚未因离开 Composition 而取消。
- `DisposableEffect.onDispose` 尚未执行。
- content 持有的图片、订阅和其他对象仍然存活。

独立创建的 `animate*AsState` 不属于 `AnimatedVisibilityScope.transition`，容器不知道它何时结束，因而可能先移除 content。需要与退出完成同步的自定义动画应挂到 scope 提供的 `transition` 上。

缩短退出时长只能缩短保留窗口，没有一个适用于所有产品的固定毫秒数。内容很重时，可把昂贵订阅移到更高层统一管理，或在退出开始后停止不再需要的数据更新；这属于业务生命周期设计，不能靠 `visible=false` 自动完成。

## 6. AnimatedContent：过渡期间新旧内容共存

`AnimatedContent` 切换目标时会同时查找新状态和旧状态的 content。新内容执行 enter，旧内容执行 exit；旧内容在退出完成后才 dispose。默认 `SizeTransform` 还会为容器尺寸变化创建动画。快速连续切换时，尚未退出的 content 可能不止一份。

因此，`AnimatedContent` 没有“只保留新内容”的性能特征。选它时要评估：

- 新旧 content 同时 Composition、measure 和 draw 的成本。
- 旧 content 在退出期间保留的 effect 与资源。
- `SizeTransform` 是否让父布局持续变化。
- target 变化频率是否高于用户能够辨认的切换频率。

content lambda 必须使用它收到的 `targetState` 参数构建对应内容。`contentKey` 用来定义哪些 target 属于同一内容身份；两个 target 映射到同一个 key 时不会触发内容切换动画。它适合过滤“状态对象变了但视觉身份没变”的更新，不能用来掩盖错误的状态建模。

`AnimatedVisibility` 适合一个内容节点的出现与消失，`AnimatedContent` 适合不同内容身份之间的替换。两者都可能保留退出内容，也都可能触发布局；应按语义和 trace 结果选择。

## 7. produceState、snapshotFlow 与 derivedStateOf

`produceState` 用 `remember { mutableStateOf(initialValue) }` 保存结果，并由带 keys 的 `LaunchedEffect` 启动 producer。它有无 key、单 key 和多 key overload，不能概括为固定的 `LaunchedEffect(Unit)`。key 改变会取消旧 producer 并启动新 producer；离开 Composition 也会取消。对回调式数据源，可用 `awaitDispose` 注销回调。

返回的 State 会合并相等值。不同值若以帧率更新，下游仍会按其读取阶段失效。`produceState` 适合把外部异步或订阅式数据转成 Compose State；外部源恰好高频，并不会让这个 API 失效。要检查的是 UI 是否需要每个样本，以及读取位置是否合适。

`snapshotFlow` 把 Snapshot State 读取转成冷 Flow，适合驱动埋点、持久化等副作用。用 `distinctUntilChanged`、`sample` 或 `debounce` 会改变事件语义和时间语义，不宜拿来替代屏幕上的逐帧动画。

`derivedStateOf` 适合输入变化频繁、输出变化较少的派生结果。例如滚动偏移不断变化，而 UI 只关心“是否越过阈值”。它根据派生结果的变更策略决定是否通知读取方，没有面向业务的 `readableHash` 快捷路径。若派生结果每帧都不同，`derivedStateOf` 还会增加观察与计算开销。

## 8. Strong Skipping 能解决什么

启用 Strong Skipping 后，restartable composable 即使带不稳定参数也可以被标记为 skippable；参数比较规则仍区分稳定和不稳定类型。编译器还会对 composable 内的 lambda 做自动 memoization，并以捕获值作为 keys。

这些规则主要减少父级重组向下传播和 lambda 重新分配。它们不会改变下面的行为：

- Composable 函数体直接读取的动画 State 变化后，读取作用域仍会失效。
- layout、draw 或 layer lambda 中的 State 读取仍由对应阶段观察。
- 跳过一个 composable 不会暂停 `LaunchedEffect` 或 `rememberCoroutineScope` 的任务。
- State 更新不会因为 group 被 skip 而排队到某次未来 Composition；对应观察者会按 Snapshot 机制收到失效。

常见的高效写法是捕获稳定的 State 持有者，在 layout、draw 或 `graphicsLayer` lambda 内解引用。若先在 Composable 函数体把 State 解引用成每帧变化的标量，再把标量捕获进 lambda，Composition 已经建立了高频读取关系。

不要为动画批量追求 non-restartable group。编译器注解或生成的 group 类型会改变重组入口与可跳过性，只有编译器报告、基准和明确热点共同支持时才值得调整。

## 9. Lazy 列表中的动画所有权

Lazy layout 决定哪些 item 进入、保留或离开 Composition，预取和保留策略也由它控制。item 内层的 `AnimatedVisibility` 只能管理自己仍在 Composition 时的内容退出；它不能要求 LazyColumn 在 item 离开布局管理范围后继续保留退出动画。

列表数据的新增、删除和重排优先使用稳定 key 配合 `Modifier.animateItem()`。item 内部局部区域的显示隐藏再使用 `AnimatedVisibility`。这样能把“数据项身份变化”和“项内内容可见性”分开。

`rememberInfiniteTransition` 在其宿主仍处于 Composition 时持续请求动画帧。它返回的值读在 Composable 函数体会触发 Composition，读在 draw 或 layer lambda 才能把更新限定到后续阶段。离屏 item 是否仍在运行，取决于该 item 是否仍被 Lazy layout 保留；不能只根据像素是否可见推断。

大量列表动画的检查项包括：

- item 是否有稳定且唯一的 key。
- 同屏活跃动画数量是否随滚动或数据更新持续增长。
- 离屏后仍无产品价值的无限动画是否及时离开 Composition。
- expand/shrink、`animateContentSize` 和 placement animation 是否叠加触发布局。
- 图片、模糊、阴影和 alpha 图层是否把瓶颈移到 RenderThread 或 GPU。

## 10. 从 Compose 阶段看到显示结果

`graphicsLayer`、draw lambda 或跳过 Composition 只改变 App 前半程的工作量。标准 HWUI 页面仍要经过 RenderThread、GPU、App Window 的 buffer 提交、SurfaceFlinger 和 HWC。alpha、clip、blur、复杂 path 或较大的离屏层可能让主线程变轻，同时增加 GPU 或内存带宽成本。

`ComposeView` 与 View 动画共用窗口和主线程帧回调；`AndroidView` 也不会得到独立帧预算。混合页面应在同一条 FrameTimeline 上分析 View traversal、Compose 工作、RenderThread 和系统合成，不能把某一侧的 trace slice 当成整帧。

Android 17 的 kernel 基线是 `android17-6.18-2026-06_r6`。kernel scheduler、cpufreq、thermal 和 fence wait 会影响线程何时运行或等待，却不定义 `Animatable`、`Transition` 和 content disposal 的语义。遇到 runnable 延迟、频率受限或 fence wait 时再进入 kernel 证据；仅凭动画卡顿不能归因给调度器。

## 11. Perfetto、Studio 与线上指标各看什么

一轮可靠的排查可以按以下顺序进行：

1. 在 release、profileable、non-debuggable 构建上复现固定交互。
2. 用 FrameTimeline 对齐 expected 与 actual，确认哪些帧 late、App 是否按时完成。
3. 查看主线程 `Choreographer#doFrame`、Compose composition tracing、Layout 和 Draw 相关 slice。
4. 查看 RenderThread、GPU、App Window buffer post 和 SurfaceFlinger；避免把 GPU/present 时间塞进 `doFrame`。
5. 将慢帧映射回动画状态、目标切换、活跃 content 数和读取阶段。

工具的职责要分开：

- **Composition tracing**：在系统 trace 中显示 composable 调用，适合定位重组代码和耗时。
- **Layout Inspector**：显示运行中 composable 的 composition/skip 计数，适合验证重组范围；连接工具本身有开销。
- **Animation Preview**：暂停、拖动时间轴并检查动画值，适合验证曲线与多动画协调；它不是运行时性能分析器。
- **FrameTimeline**：把 App 和 SurfaceFlinger 的 expected/actual frame 及 jank 类型放在同一时间轴上。
- **JankStats**：给线上帧数据附加页面或交互状态，便于按场景聚合。

`FrameMetrics.ANIMATION_DURATION` 表示一帧中发出 animation callbacks 的耗时。它不能区分“动画帧”和“非动画帧”，也不覆盖整帧。Android 12 及以上更适合关注 FrameTimeline 派生的 overrun；线上需要结合当前 UI state，避免把整页的慢帧都归给某个动画。

## 12. 用 Macrobenchmark 建立回归门槛

动画基准要覆盖一次完整、可重复的状态迁移，并让测试知道动画何时结束。测试页面可以在 `MutableTransitionState.isIdle` 后暴露一个只供测试识别的 semantics/test tag。

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

`toggle_animation`、`reset_collapsed` 和完成标记需要通过 `testTagAsResourceId` 或真实 resource id 暴露。完成标记应在目标状态达到且 transition idle 后出现，避免只测到动画起点。每轮 setup 都回到同一初始状态，测量块只包含目标交互。

关注 `frameOverrunMs` 的 P50/P90/P95/P99，以及 `frameDurationCpuMs` 和 `frameCount`。`frameOverrunMs` 在 API 31 及以上能适应高刷和可变帧率；`frameDurationCpuMs` 只覆盖 UI thread 与 RenderThread 的 CPU 生产时间。`frameCount` 变化可能说明实现减少或增加了请求帧数量，不能只比较耗时分位值。Macrobenchmark 没有应当固定依赖的 `jankFrameCount` 结论。

Baseline Profile 可以让 ART 提前编译被关键用户旅程覆盖的 App 与库代码，减少首次运行时的解释和 JIT 成本。它不能预编译 GPU shader、消除离屏合成，也不会改变 Snapshot 失效范围。用同一 Macrobenchmark 对比 profile 前后数据，才知道当前动画是否受编译状态影响。

## 13. 无限动画、VectorConverter 与资源动画

`rememberInfiniteTransition()` 表达“进入 Composition 后持续运行，离开后停止”。同一个 transition 的子动画共享一条帧循环，不会为每个值注册独立 VSync；每个子项仍要维护状态并执行插值。隐藏组件只设 `alpha = 0f`、移到屏外或盖住它，都不会使其离开 Composition。对于明确不可见的 loading、呼吸光和背景粒子，应让对应分支真正移出组合，或由业务状态停止动画。

系统动画时长缩放为 0 时，Compose 会把无限动画推进到目标值并等待缩放恢复，不会继续逐帧 tick。产品要验证这个目标值是不是合理静止画面，并为“减少动态效果”保留可理解的 UI。

一组视觉值若能由同一相位推导，可只保留一个 `animateFloat()`，在 drawing/layer 阶段计算颜色、缩放和偏移。`TwoWayConverter<T, V>` 只负责业务值与 `AnimationVector1D`～`4D` 的双向映射；维度必须对应独立变量，单位和有效域要清楚。`convertFromVector()` 每帧创建复杂对象时，应比较拆成内置标量动画或相位推导的分配成本。

Animated Vector XML 是另一条资源链：`AnimatedImageVector` 解析 vector/animator 资源并按 progress 绘制，不经过 `TwoWayConverter`。资源应按 id 稳定记忆，避免在动画帧内重复解析；路径节点、关键帧和同时播放数量仍需在目标设备上测量。

## 14. Pager 动画：区分当前页、稳定页和目标页

Pager 的 `currentPage` 会在拖动跨过 snap 判定点时变化，不代表滚动完成；曝光、资源 owner 和业务选中应优先观察 `settledPage`，动画目标可以使用 `targetPage`。任意 page 到当前吸附位置的距离用 `getOffsetDistanceInPages(page)`，避免手写公式在 `currentPage` 切换时反转符号。

页面的 alpha、scale、rotation 和 translation 读取应放进 `graphicsLayer {}`，让滚动只更新图层属性；正文提前读取 `currentPageOffsetFraction` 会让依赖该值的页面持续重组。高频 state 读取被延后不等于动画零成本：clip、shadow、alpha 和大面积旋转仍可能增加离屏与 GPU 带宽。

`beyondViewportPageCount` 表示额外组合、测量和放置的 page，不包含内部预取；从默认值开始逐页增加，并同时比较首次进入页的 compose/measure、内存峰值与命中率。`visiblePagesInfo` 是高频测量结果，不是页面生命周期。视频、地图和 WebView 等重资源应由 `settledPage`、可见性和 lifecycle 共同控制。

同向嵌套 Pager/Lazy 容器要明确 nested-scroll owner、fling 交接和到边后的继续滚动；负 `pageSpacing` 产生重叠时，还要验证 zIndex、命中区域、裁剪和无障碍顺序。点击 Tab 启动的 `animateScrollToPage()` 可被新手势或新 mutation 取消，调用返回后不能无条件认为目标页已经稳定展示。

## 15. 检查清单

- 动画值在哪个阶段读取？是否在更早阶段也被解引用？
- 值变化后需要 Composition、measure、placement、Draw 还是 layer property update？
- `AnimatedVisibility` 或 `AnimatedContent` 退出期间保留了哪些 content、effect 和资源？
- 动画中途改目标时，是 retarget、取消后续跑，还是产品层屏蔽输入？
- `produceState` 的 keys 是否完整，外部订阅是否在 `awaitDispose` 中注销？
- `derivedStateOf` 的输出是否比输入低频？
- Lazy item 的身份变化是否由稳定 key 和 `animateItem` 管理？
- 帧预算是否来自本帧 FrameTimeline，是否同时核对 App、GPU 与 present？
- Studio 工具、实验室基准和线上指标是否各自回答了合适的问题？
- 优化是否在 release/profileable 构建和代表性设备上复测？

## 16. 源码与资料索引

Compose 行为按以下 1.10.0 source JAR 复核：

- [`androidx.compose.animation:animation:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/1.10.0/animation-1.10.0-sources.jar)：`AnimatedVisibility.kt`、`AnimatedContent.kt`。
- [`androidx.compose.animation:animation-core:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation-core/1.10.0/animation-core-1.10.0-sources.jar)：`Animatable.kt`、`AnimationState.kt`、`Transition.kt`、`InfiniteTransition.kt`。
- [`androidx.compose.ui:ui-android:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.10.0/ui-android-1.10.0-sources.jar)：`AndroidUiFrameClock.android.kt`、`AndroidUiDispatcher.android.kt`、graphics layer 与 draw modifier 实现。

平台和 kernel 边界按固定 tag 复核：

- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)。
- [Android 17 `FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)。
- [`android17-6.18-2026-06_r6` kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)。

API 用法、性能工具和测量口径参考：

- [Compose 动画性能 quick guide](https://developer.android.com/develop/ui/compose/animation/quick-guide)。
- [Compose phases](https://developer.android.com/develop/ui/compose/phases)。
- [Graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)。
- [AnimatedVisibility 与 AnimatedContent](https://developer.android.com/develop/ui/compose/animation/composables-modifiers)。
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)。
- [Compose side effects 与 produceState](https://developer.android.com/develop/ui/compose/side-effects)。
- [Lazy list item animations](https://developer.android.com/develop/ui/compose/lists)。
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)。
- [Layout Inspector 调试 Compose](https://developer.android.com/develop/ui/compose/tooling/debug)。
- [Animation Preview](https://developer.android.com/develop/ui/compose/tooling/animation-preview)。
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)。
- [Macrobenchmark FrameTimingMetric](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)。
- [Compose Baseline Profile](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)。
