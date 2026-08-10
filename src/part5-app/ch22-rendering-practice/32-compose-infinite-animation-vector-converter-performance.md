---
title: "Compose 无限动画与 VectorConverter 性能优化"
chapter: "22.32"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, animation, infinite-transition, vector-converter, performance]
related_chapters: ["22.5", "22.21", "22.11", "22.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构+章节深挖"
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: "2026-08-07T19:35:58+08:00"
last_draft_polish_run_id: "20260807-193558-draft-polish-c7c8c2be"
reviewed_date: "2026-08-07"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-08-07T20:13:52+08:00"
last_review_finalize_run_id: "20260807-200624-3002f692"
last_verified: "2026-08-07"
confidence: high
sources:
- type: reference
  path: Android 17 Choreographer.java (android-17.0.0_r1)
- type: official
  path: AndroidX Compose Animation/Core/UI 1.11.4 source snapshot 854220f44ea8ea80fee824a6c5a045f39bede289
- type: reference
  path: Android Developers Compose performance phases, animation tooling, TwoWayConverter, AnimatedImageVector, preferredFrameRate, Macrobenchmark metrics
---

# 22.32 Compose 无限动画与 VectorConverter 性能优化

`rememberInfiniteTransition()` 适合表达“进入组合后持续运行，离开组合后停止”的动画。它没有脱离 Compose 帧时钟，也不会为每个子动画申请一条独立 VSync 回调。性能问题通常来自三个位置：仍在组合中的动画数量、动画值被读取的阶段，以及每帧插值、对象创建和绘制的工作量。

验证基线如下：

- Android 平台：Android 17、API 37、`android-17.0.0_r1`
- 内核：`android17-6.18-2026-06_r6`
- Compose：Compose BOM `2026.06.01`，Animation Core、Animation Graphics 与 UI `1.11.4`
- AndroidX 源码：提交 `854220f44ea8ea80fee824a6c5a045f39bede289`

Compose 随应用依赖发布，其发布节奏与 Android 平台、内核相互独立。Android 17 与内核标签限定系统环境；`InfiniteTransition`、`TwoWayConverter` 和 `AnimatedImageVector` 的行为仍应以应用解析到的 Compose 版本为准。

当前源码中没有 `AnimationClockakov`、`InfiniteTransition.runInfiniteLoop()`、`DeratingStrategy` 或 `basedOnState` 这些 API。对应实现是 `MonotonicFrameClock`、`InfiniteTransition.run()`、组合生命周期与应用显式可见性状态。`TwoWayConverter` 和 Animated Vector XML 属于不同链路，需要分开分析。

## 1. 选择与生命周期相符的动画 API

无限重复只是时间曲线的一种形式。API 选择要从动画的结束条件和控制方式出发：

| 需求 | 合适的 API | 生命周期 |
| --- | --- | --- |
| 组件存在期间持续旋转、呼吸或流动 | `rememberInfiniteTransition()` | 子动画进入组合后开始，移出组合后注销 |
| 一组属性随离散状态一起变化 | `updateTransition()` | 由目标状态驱动，可自然结束 |
| 需要挂起、取消、抢占、手势跟随或显式 `stop()` | `Animatable` | 由调用者管理协程 |
| 单个目标值变化 | `animate*AsState()` | 到达目标后停止 |
| 播放 `<animated-vector>` 资源的起点与终点 | `AnimatedImageVector` + `rememberAnimatedVectorPainter()` | `atEnd` 变化驱动有限 Transition |
| 可由一个相位计算出的波形或粒子样式 | 一个动画值 + `Canvas` | 每帧计算集中在绘制阶段 |

能结束的状态变化不应改写成无限循环。例如下载进度、展开收起和选中反馈都有明确目标，有限动画在静止状态不会继续请求动画帧。

`InfiniteTransition` 也不等同于 `Transition` 的“高开销版本”。两者解决不同的状态模型：前者维护持续重复的 `TargetBasedAnimation`，后者在离散状态之间运行有限过渡。测量时应比较同一视觉效果和同一生命周期，不能只比较 API 名称。

## 2. InfiniteTransition 怎样取得每一帧

Compose Animation Core 1.11.4 的调用关系如下：

1. `rememberInfiniteTransition()` 通过 `remember` 保留一个 `InfiniteTransition`，随后调用内部 `run()`。
2. `run()` 在 `LaunchedEffect(this)` 中循环调用 `withInfiniteAnimationFrameNanos()`。
3. `withInfiniteAnimationFrameNanos()` 转到运行环境中的 `withFrameNanos()`；测试或预览环境可以用 `InfiniteAnimationPolicy` 截获无限操作。
4. Android 端默认 `MonotonicFrameClock` 是 `AndroidUiFrameClock`，它把回调交给 `AndroidUiDispatcher` 和 `Choreographer.postFrameCallback()`。
5. Android 17 的 `Choreographer` 把 `FrameCallback` 放入 `CALLBACK_ANIMATION` 队列。`doFrame()` 的阶段顺序是 INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT。
6. `InfiniteTransition` 用帧时间计算播放时间，遍历尚未完成的子动画，并把结果写入各自的 `State<T>`。

这条链路带来两个重要结论。

其一，同一个 `InfiniteTransition` 中的多个子动画共享一个帧循环。每个子动画仍有自己的 `TransitionAnimationState`、`TargetBasedAnimation` 和插值计算，因此子动画数量增加后，每帧工作也会增加。

其二，动画状态更新不代表整个页面必然重组。Compose 会记录动画值在哪个阶段被读取：

- 在 Composable 正文读取，变化会使相应组合重启域失效；
- 在 `Modifier.offset {}` 中读取，变化会请求放置和绘制；
- 在 `graphicsLayer {}` 中读取，变化可以只更新图层属性；
- 在 `Canvas`、`drawBehind` 或 `drawWithContent` 中读取，变化可以只请求绘制。

所以“无限动画每帧重组”只在动画值于组合阶段被读取时成立。诊断时必须先找到读取位置。

### 2.1 子动画的注册与移除

`animateFloat()` 最终调用 `animateValue()`。后者用 `remember` 保存子状态，用 `SideEffect` 检查起点和终点是否变化，并用 `DisposableEffect` 把子动画加入或移出父级列表。`DisposableEffect` 管理的是子动画注册；帧循环本身运行在 `LaunchedEffect` 中。

起点或终点变化会构造新的 `TargetBasedAnimation`，并从下一帧重新计时。源码没有保证这种更新保持速度或位置连续。需要在运行中连续改变目标时，`Animatable.animateTo()` 或有限 `Transition` 通常更合适。

### 2.2 系统动画时长缩放为零时

Compose 1.11.4 会读取协程上下文中的 `MotionDurationScale`。缩放因子为 `0` 时，`InfiniteTransition` 把子动画跳到目标值，然后通过 `snapshotFlow` 等待缩放恢复到大于零。在此期间不会持续执行帧循环。

这项行为用于尊重系统动画设置。业务仍要检查“目标值”是否是合适的静止画面。例如旋转动画常用 `0f` 到 `360f`，两端视觉一致；呼吸动画的目标端可能比起点更亮，应由产品和无障碍设计确定静止状态。

## 3. 可见性：停止动画要移出组合

官方契约很明确：`rememberInfiniteTransition()` 的子动画进入组合后开始，直到移出组合才停止。以下情况本身不会注销子动画：

- `alpha = 0f`；
- 被父容器裁剪；
- 被其他内容遮挡；
- 列表项暂时位于屏幕边界之外，但仍被 Lazy 布局保留；
- Composable 仍在树中，只是业务状态标记为“隐藏”。

应用应把是否需要动画表达为显式状态，并在不需要时移除包含 `rememberInfiniteTransition()` 的分支。下面的代码用于把加载动画的生命周期绑定到 `active`。

```kotlin
@Composable
fun LoadingIndicator(
    active: Boolean,
    modifier: Modifier = Modifier,
) {
    if (!active) {
        return
    }

    val transition =
        rememberInfiniteTransition(label = "loading-indicator")
    val angle =
        transition.animateFloat(
            initialValue = 0f,
            targetValue = 360f,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(
                        durationMillis = 900,
                        easing = LinearEasing,
                    ),
                    repeatMode = RepeatMode.Restart,
                ),
            label = "loading-angle",
        )

    Canvas(modifier.size(24.dp)) {
        rotate(angle.value) {
            drawArc(
                color = Color(0xFF3F51B5),
                startAngle = 20f,
                sweepAngle = 280f,
                useCenter = false,
                style = Stroke(width = 2.dp.toPx()),
            )
        }
    }
}
```

`angle.value` 在 `Canvas` 绘制块中读取。动画活动时，Compose 可以跳过组合与布局，只重新执行绘制。`active` 变为 `false` 后，动画对象和注册它的 Effect 一起离开组合，父级列表中不再保留这个子动画。

若静止状态仍需显示内容，可以把分支写成动画版本与静态版本，而不是保留动画后把透明度设为零。列表中的“当前可见”也应来自产品状态、分页状态或经过验证的可见项信息；不要假定 Lazy 列表一离开屏幕就立即释放所有相邻项目。

### 3.1 窗口生命周期提供的保护边界

Android 上的默认 `WindowRecomposer` 感知 ViewTree Lifecycle。Compose UI 1.11.4 在生命周期进入 `ON_STOP` 时调用 `pauseCompositionFrameClock()`，回到 `ON_START` 时恢复。这会暂停该窗口中等待 `withFrameNanos()` 的动画和其他帧 Effect。

这层保护针对整个窗口。页面已 `STARTED` 时，单个透明、遮挡或业务上不可见的组件仍需自行控制组合生命周期。自定义 Recomposer 或自定义 `MonotonicFrameClock` 也可能有不同策略，不能把默认窗口行为推广到所有 Compose 宿主。

## 4. 把动画值放在最晚需要它的阶段读取

优化动画时，状态的创建位置通常不如读取位置重要。Compose 分为组合、布局和绘制三个主要阶段，每个阶段都有独立或局部的重启域。频繁变化的动画值应尽量靠近消费它的阶段。

### 4.1 只改变视觉位置：graphicsLayer

下面的代码用于实现不改变布局坐标和兄弟节点位置的水平漂移动画。

```kotlin
@Composable
fun FloatingDot(
    active: Boolean,
    modifier: Modifier = Modifier,
) {
    if (!active) return

    val travelPx = with(LocalDensity.current) { 12.dp.toPx() }
    val transition =
        rememberInfiniteTransition(label = "floating-dot")
    val translation =
        transition.animateFloat(
            initialValue = -travelPx,
            targetValue = travelPx,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(700, easing = FastOutSlowInEasing),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "translation-x-px",
        )

    Box(
        modifier
            .size(8.dp)
            .graphicsLayer {
                translationX = translation.value
            }
            .background(Color(0xFF26A69A), CircleShape)
    )
}
```

`translation.value` 在图层属性块中读取，布局坐标保持不变。这种方式适合纯视觉位移、缩放、旋转和透明度。它可能创建或更新硬件图层，图层有内存、录制、上传与合成成本；小组件数量很大时仍需用跟踪记录确认收益。

### 4.2 位置属于布局语义：offset lambda

当命中区域、语义位置或父子布局关系需要随位置变化时，应保留布局位移。下面的代码把动画值读取推迟到放置步骤。

```kotlin
@Composable
fun BouncingBadge(
    active: Boolean,
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    if (!active) return

    val travelPx = with(LocalDensity.current) { 6.dp.toPx() }
    val transition =
        rememberInfiniteTransition(label = "bouncing-badge")
    val offsetY =
        transition.animateFloat(
            initialValue = 0f,
            targetValue = travelPx,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(600, easing = FastOutSlowInEasing),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "offset-y-px",
        )

    Box(
        modifier =
            modifier.offset {
                IntOffset(x = 0, y = offsetY.value.roundToInt())
            },
        content = content,
    )
}
```

`Modifier.offset {}` 在布局的放置步骤读取状态，可以跳过组合，也不会重新执行该节点的测量步骤。它仍会改变布局位置并安排绘制。`graphicsLayer` 与 `offset` 的取舍由坐标语义决定，没有一个固定替代关系。

### 4.3 颜色、形状和路径：draw 阶段

颜色、描边、进度弧线和波形通常只影响像素。把状态放进 `Canvas` 或绘制 Modifier，可省去每帧组合和测量。绘制阶段仍运行在 UI 渲染管线中；复杂路径运算、过多 draw call 或大面积透明混合依然可能使 UI 线程录制和 RenderThread 工作变长。

## 5. 用一个相位生成一组视觉值

同一 `InfiniteTransition` 会共享帧循环，但每个 `animateFloat()` 仍需维护状态和执行插值。若一组值可以由同一相位推导，保留一个动画子项通常更清晰。

下面的代码用于绘制八根共享相位的声纹柱。

```kotlin
@Composable
fun Waveform(
    active: Boolean,
    modifier: Modifier = Modifier,
) {
    if (!active) return

    val transition =
        rememberInfiniteTransition(label = "waveform")
    val phase =
        transition.animateFloat(
            initialValue = 0f,
            targetValue = (2f * PI).toFloat(),
            animationSpec =
                infiniteRepeatable(
                    animation = tween(1000, easing = LinearEasing),
                    repeatMode = RepeatMode.Restart,
                ),
            label = "waveform-phase",
        )

    Canvas(modifier.height(32.dp).fillMaxWidth()) {
        val barCount = 8
        val gap = size.width / (barCount * 2f)
        val barWidth = gap

        repeat(barCount) { index ->
            val wave =
                (
                    (
                        sin((phase.value + index * 0.72f).toDouble()) +
                            1.0
                    ) * 0.5
                ).toFloat()
            val barHeight = size.height * (0.25f + wave * 0.75f)
            val left = gap * (index * 2f)
            val top = (size.height - barHeight) * 0.5f

            drawRoundRect(
                color = Color(0xFF7E57C2),
                topLeft = Offset(left, top),
                size = Size(barWidth, barHeight),
                cornerRadius = CornerRadius(barWidth * 0.5f),
            )
        }
    }
}
```

代码每帧只更新一个 `State<Float>`，八根柱的高度在绘制时由相位计算。柱数、三角函数和绘制调用仍有成本；数量扩大后要用目标设备的帧时间和 CPU 采样判断是否需要查表、降低几何复杂度或改用其他渲染方式。

多个属性拥有不同周期、缓动或生命周期时，强行合并到一个相位会降低可读性，也可能改变视觉节奏。共享相位适用于数学关系明确的效果，不是通用规则。

## 6. TwoWayConverter 的职责与成本

`TwoWayConverter<T, V>` 定义两个函数：

- `convertToVector: (T) -> V`，把业务值映射为 `AnimationVector1D` 到 `AnimationVector4D`；
- `convertFromVector: (V) -> T`，把插值后的向量还原为业务值。

Animation Spec 对向量各维进行运算。`TargetBasedAnimation` 在建立动画时转换起点和终点；查询某个播放时间的值时，它取得插值向量，再调用 `convertFromVector()` 得到 `T`。自定义转换器的还原逻辑位于每帧热点中。

Compose 已为 `Float`、`Int`、`Dp`、`DpOffset`、`Offset`、`Size`、`IntOffset`、`IntSize` 和 `Rect` 提供转换器。能用内置类型清楚表达的数据，应优先使用内置转换器。

### 6.1 自定义二维值

下面的转换器用于同时动画化缩放与透明度，并保持向量维度与独立变量数量一致。

```kotlin
@Immutable
data class PulseStyle(
    val scale: Float,
    val alpha: Float,
)

val PulseStyleVectorConverter:
    TwoWayConverter<PulseStyle, AnimationVector2D> =
    TwoWayConverter(
        convertToVector = {
            AnimationVector2D(it.scale, it.alpha)
        },
        convertFromVector = {
            PulseStyle(scale = it.v1, alpha = it.v2)
        },
    )

@Composable
fun PulsingContent(
    active: Boolean,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    if (!active) {
        content()
        return
    }

    val transition =
        rememberInfiniteTransition(label = "pulsing-content")
    val style =
        transition.animateValue(
            initialValue = PulseStyle(scale = 0.96f, alpha = 0.65f),
            targetValue = PulseStyle(scale = 1f, alpha = 1f),
            typeConverter = PulseStyleVectorConverter,
            animationSpec =
                infiniteRepeatable(
                    animation = tween(850, easing = FastOutSlowInEasing),
                    repeatMode = RepeatMode.Reverse,
                ),
            label = "pulse-style",
        )

    Box(
        modifier.graphicsLayer {
            scaleX = style.value.scale
            scaleY = style.value.scale
            alpha = style.value.alpha
        }
    ) {
        content()
    }
}
```

转换器定义在稳定位置，不会随组合反复创建。两个 Float 使用 `AnimationVector2D`，每一维都有清楚的单位与范围。`convertFromVector()` 每次返回新的 `PulseStyle`，所以热点中可能产生对象；若剖析显示分配或 GC 已影响帧时间，可以改为两个内置 Float 动画，或只动画化一个相位并在图层块中推导属性。

`@Immutable` 帮助 Compose 编译器理解值语义，不会消除 `PulseStyle` 的构造。编译期稳定性与运行期分配是两类问题。

### 6.2 转换器设计约束

自定义转换器应满足以下条件：

- 双向转换在有效域内保持一致，避免往返后持续漂移；
- 每一维使用一致单位，不混合 dp、px、角度和无量纲比例；
- 维度只包含参与插值的独立量；
- `convertFromVector()` 不做 I/O、资源读取、集合排序或路径解析；
- 对非法值、边界和舍入策略有明确约定；
- 角度跨越 `0°/360°` 时先定义最短路径或固定方向，线性插值不会自动理解周期；
- 颜色使用 Compose 的颜色动画 API 及其颜色空间处理，不要自行把编码后的 ARGB 整数按四个普通数字插值。

`AnimationVector` 的内部对象可以由向量化 Animation Spec 复用和修改。转换器不应把收到的向量保存到业务对象或跨帧缓存。

## 7. Animated Vector XML 是另一条链路

`TwoWayConverter` 不读取 VectorDrawable XML，也不会把 XML 转成“Compose 动画树”。Compose Animation Graphics 1.11.4 的资源路径是：

1. `AnimatedImageVector.animatedVectorResource(id)` 用 `remember(id)` 调用资源加载器；
2. 加载器解析 `<animated-vector>`、基础 `ImageVector`、各 `<target>` 和 animator 资源；
3. 解析结果是 Compose 的 `AnimatedImageVector`，其中保存基础 `ImageVector` 与目标动画描述；
4. `rememberAnimatedVectorPainter(animatedImageVector, atEnd)` 建立以 Boolean 为状态的 `updateTransition()`；
5. 内部 animator 把 rotation、translation、alpha、trim path、颜色或 path data 等属性映射为 Transition 状态，绘制时把结果应用到 Vector group。

内部模型中有名为 `ObjectAnimator` 的数据类，但它属于 Animation Graphics 的 XML animator 表示。它与 Animation Core 的 `TwoWayConverter` 没有转换关系。Compose 这里使用的是 `AnimatedImageVector` 和 `Painter`，也不等于把 Android Framework 的 `AnimatedVectorDrawable` 实例直接嵌入组合。

下面的代码用于加载一次资源，并由 `atEnd` 驱动起点与终点之间的有限动画。

```kotlin
@Composable
fun SuccessAnimatedIcon(
    atEnd: Boolean,
    modifier: Modifier = Modifier,
) {
    val image =
        AnimatedImageVector.animatedVectorResource(
            id = R.drawable.avd_success,
        )
    val painter =
        rememberAnimatedVectorPainter(
            animatedImageVector = image,
            atEnd = atEnd,
        )

    Image(
        painter = painter,
        contentDescription = "操作成功",
        modifier = modifier.size(24.dp),
    )
}
```

资源对象由 `animatedVectorResource()` 按 `id` 记忆，`atEnd` 改变时执行有限 Transition。反复切换 `atEnd` 的中断语义由 Transition 处理，不需要额外包一层 `rememberInfiniteTransition()`。

Animated Vector 的成本受目标数量、路径节点数、path morph、透明混合和绘制面积影响。资源解析已被 `remember(id)` 避免在普通重组中重复执行；大量列表项仍会各自建立 Painter 与动画状态。此时应减少同时活动的项，并评估静态图标、有限动画或共享的 Canvas 效果是否更适合。

## 8. 刷新率、帧率请求与手动降频

Compose 动画使用帧时间计算播放进度，不按“执行了多少帧”累加固定步长。同一个 900 ms tween 在 60 Hz 与 120 Hz 屏幕上应保持相近时长，高刷新率可能产生更多采样点和更多每帧计算。

Compose UI 1.11.4 提供 `Modifier.preferredFrameRate()`。它表达内容偏好的帧率，多个请求会被聚合，偏好只在内容被绘制期间有效。源码实现会创建 `graphicsLayer()` 并把请求传到图层；Android 端仅在 API 35 及以上通过 `View.requestedFrameRate` 向平台投票，API 31 到 34 不会产生对应的平台请求。系统可以根据显示能力、其他内容与策略选择可行刷新率。这是帧率请求，不是动画暂停开关，也不保证每个 `InfiniteTransition` 严格按指定频率执行。

普通加载指示器不应把固定降频作为默认优化：

- 丢弃一部分动画结果仍可能每个 VSync 醒来并计算；
- 基于计数“每两帧更新一次”会在不同刷新率上得到不同速度；
- 较低采样率可能产生可见跳动；
- 帧率请求可能影响同一窗口或图层体系中的其他内容。

存在明确内容帧率时，例如 24 fps 或 30 fps 视频，才适合使用 `preferredFrameRate()`。动画页面的优化顺序通常是停止不可见动画、减少活动子项、推迟状态读取、降低每帧几何与分配，然后基于测量结果决定是否请求特定帧率。

## 9. alpha 与图层的成本边界

`graphicsLayer { alpha = ... }` 可以避免组合和布局，但透明度不是零成本属性：

- 图层可能需要额外缓冲区和内存；
- 内容发生变化时可能重新录制或更新；
- 非 1.0 alpha 可能触发离屏合成，具体取决于重叠、混合策略和平台实现；
- 大面积半透明会增加 GPU 读取、写入和混合带宽；
- 许多小图层会增加 RenderThread 与 SurfaceFlinger 侧的管理工作。

静态且复杂的内容做简单 alpha 或 transform 动画时，图层复用往往有效。内容本身每帧变化时，图层缓存收益可能很小。需要通过 Perfetto 的 UI 线程、RenderThread、GPU 和 FrameTimeline 证据判断瓶颈，不能仅凭 Modifier 名称推断。

## 10. 从 Compose 动画到屏幕显示

纯 Compose 页面没有创建独立 Surface 时，仍属于标准 App Window 渲染类型。按标准渲染管线，可以把一次动画帧分为四段：

| 区段 | 主要工作 | 可观察证据 |
| --- | --- | --- |
| App MainThread / Compose host | 帧回调、动画求值、快照失效、组合/布局/绘制记录 | `Choreographer#doFrame`、Compose trace、UI thread slice |
| RenderThread | 处理 DisplayList、准备 GPU 工作、提交 App Window buffer | RenderThread slice、`DrawFrame`、GPU queue |
| BufferQueue / BLAST | 生产者 `queueBuffer`，提交 buffer 与事务 | Buffer event、BLAST transaction、BufferTX |
| SurfaceFlinger / Display | latch、合成决策、HWC/GPU 合成、present | FrameTimeline、SurfaceFlinger、HWC、present fence |

`queueBuffer` 只证明生产者提交了 buffer，不能证明该帧已经显示。判断动画卡顿需要把 App frame timeline 与 SurfaceFlinger frame timeline 对齐，再查看 deadline、latch 和 present。

Android 17 的 `Choreographer` 源码说明动画回调位于 ANIMATION 阶段，随后才是 TRAVERSAL 与 COMMIT。Compose 动画计算过长会压缩同一帧后续布局、绘制记录与提交时间；RenderThread、GPU 或 SurfaceFlinger 也可能在主线程及时完成时造成展示延迟。

内核标签 `android17-6.18-2026-06_r6` 用于统一调度、频率、内存和驱动分析基线。Compose 1.11.4 的库变化不能归因于该内核版本。

## 11. 诊断工具各自回答什么

### 11.1 Compose Compiler 报告

Compose Compiler 报告描述参数稳定性、函数是否可重启、是否可跳过等编译期属性。它不记录某段动画运行时重组了多少次，也不提供每帧耗时。报告能帮助解释“为何某个 Composable 难以跳过”，运行频率仍要从 Layout Inspector 或跟踪记录取得。

### 11.2 Layout Inspector 与 Animation Preview

Layout Inspector 可以显示运行中 Composable 的组合与跳过计数，适合定位动画状态是否在过大的组合域读取。计数受操作时长和工具开销影响，应在相同交互窗口内比较。

Animation Preview 支持逐帧检查 `rememberInfiniteTransition()`、`updateTransition()` 等动画的值和时序，适合验证曲线、标签和状态转换。它不是设备帧成本分析器，不能替代 Release 构建上的 Perfetto 或 Macrobenchmark。

### 11.3 Perfetto 与 FrameTimeline

Perfetto 用于回答以下问题：

- 动画值更新后，主线程执行了组合、布局还是仅绘制；
- 同一帧中是否存在长 GC、锁等待、CPU 失调度或其他主线程任务；
- RenderThread、GPU queue 或 SurfaceFlinger 是否成为关键路径；
- App frame 是否错过 deadline，buffer 是否按时 latch 和 present；
- 优化前后的 P50、P90、P95、P99 分布是否改善。

Android 12 及以上可使用 FrameTimeline。不要依赖不存在的公开 `Choreographer.skippedFrames` 属性作为业务监控接口。

### 11.4 JankStats 与 Macrobenchmark

JankStats 适合现场收集帧卡顿和界面状态标签；它帮助回答哪些用户场景发生卡顿，不提供完整的系统线程因果链。Macrobenchmark 的 `FrameTimingMetric` 适合在固定用户流程、构建类型、设备状态和迭代次数下比较 `frameDurationCpuMs` 与 `frameOverrunMs` 分布。定位原因时仍应打开对应 Perfetto trace。

## 12. 一套可复现的检查顺序

对无限动画页面进行性能审阅时，可以按以下顺序执行：

1. 记录 Android tag、内核 tag、Compose BOM、解析后的各 Compose artifact 版本和构建类型。
2. 列出页面中所有 `rememberInfiniteTransition()`，标注它们进入和移出组合的条件。
3. 记录每个父 Transition 的子动画数量、Animation Spec、周期、RepeatMode 和自定义转换器。
4. 找到每个动画 `State` 的读取阶段，检查是否能从组合推迟到放置、图层或绘制。
5. 检查不可见状态是否只修改 alpha，确认动画对象是否仍在组合。
6. 检查 `convertFromVector()`、路径计算、集合操作和对象创建是否位于每帧路径。
7. 检查同一组视觉值能否由一个相位计算，或是否应改成有限动画。
8. 使用相同设备状态和交互脚本采集基线与修改后数据，比较分位数而非单次最优值。
9. 在慢帧上依次核对主线程、RenderThread、buffer transaction、SurfaceFlinger latch 和 present。
10. 保留画面正确性、无障碍动画缩放、生命周期切换和中断行为测试，防止性能修改改变语义。

## 13. 常见错误与修正方向

| 错误判断 | 源码支持的结论 | 修正方向 |
| --- | --- | --- |
| 每个子动画都有独立 VSync 回调 | 一个 `InfiniteTransition.run()` 驱动自己的子动画列表 | 生命周期一致的属性可共享父 Transition |
| 无限动画一定每帧重组整个页面 | 更新的是 `State<T>`；读取阶段决定失效范围 | 把读取推迟到所需阶段 |
| alpha 为零后动画会停止 | 子动画仍在组合就会继续注册 | 从组合移除动画分支 |
| `DisposableEffect` 执行帧循环 | 它注册和移除子动画；循环在 `LaunchedEffect` | 分清资源注册与帧任务 |
| `TwoWayConverter` 解析 Vector XML | 它只负责 `T` 与 `AnimationVector` 的双向映射 | XML 使用 Animation Graphics 资源 API |
| Animated Vector 直接复用 Framework Drawable | Compose 解析为 `AnimatedImageVector` 并用 Transition/Painter 绘制 | 按 Compose 的资源与 Painter 成本分析 |
| graphicsLayer 总比 offset 快 | 两者改变的坐标语义和执行阶段不同 | 按视觉变换或布局位置选择 |
| 编译器报告可显示运行时动画次数 | 报告描述稳定性与可跳过性 | 用 Layout Inspector 和 Perfetto 观察运行时 |
| `queueBuffer` 表示已经上屏 | 它是生产者提交点 | 继续核对 latch 与 present |
| Compose 新版行为由 Android 17 自动提供 | Compose 是应用依赖 | 同时记录平台与库版本 |

## 14. 源码与官方资料锚点

- Android 17 `Choreographer.java`：<https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java>
- Android 17 内核基线：<https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/>
- Compose 1.11.4 `InfiniteTransition.kt`：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/animation/animation-core/src/commonMain/kotlin/androidx/compose/animation/core/InfiniteTransition.kt>
- Compose 1.11.4 `InfiniteAnimationPolicy.kt`：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/animation/animation-core/src/commonMain/kotlin/androidx/compose/animation/core/InfiniteAnimationPolicy.kt>
- Compose 1.11.4 `VectorConverters.kt`：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/animation/animation-core/src/commonMain/kotlin/androidx/compose/animation/core/VectorConverters.kt>
- Compose 1.11.4 `WindowRecomposer.android.kt`：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/WindowRecomposer.android.kt>
- Compose 1.11.4 `AndroidUiFrameClock.android.kt`：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidUiFrameClock.android.kt>
- Compose 1.11.4 `FrameRate.kt`：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/FrameRate.kt>
- Compose 1.11.4 Android 帧率投票：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt>
- Compose 1.11.4 Animated Vector 资源加载：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/animation/animation-graphics/src/androidMain/kotlin/androidx/compose/animation/graphics/res/AnimatedVectorResources.android.kt>
- Compose 1.11.4 Animated Vector Painter：<https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/animation/animation-graphics/src/androidMain/kotlin/androidx/compose/animation/graphics/res/AnimatedVectorPainterResources.android.kt>
- Compose BOM 元数据：<https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml>
- 官方 Compose 阶段说明：<https://developer.android.com/develop/ui/compose/performance/phases>
- 官方 Compose 动画工具说明：<https://developer.android.com/develop/ui/compose/animation/tooling>
- 官方 `TwoWayConverter` API：<https://developer.android.com/reference/kotlin/androidx/compose/animation/core/TwoWayConverter>
- 官方 `AnimatedImageVector` API：<https://developer.android.com/reference/kotlin/androidx/compose/animation/graphics/vector/AnimatedImageVector>
- 官方 `preferredFrameRate` API：<https://developer.android.com/reference/kotlin/androidx/compose/ui/preferredFrameRate.modifier>
- 官方 Macrobenchmark 帧指标：<https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics>

## 小结

`rememberInfiniteTransition()` 的核心成本是持续参与帧时钟后的每帧工作。控制成本的有效手段是让动画对象只在需要时进入组合、减少同时活动的子动画、把状态读取放到所需的最晚阶段，并让每帧转换与绘制保持简单。

`TwoWayConverter` 只解决业务值与 `AnimationVector` 的映射。Animated Vector XML 由 Animation Graphics 资源加载器解析，再通过 `AnimatedImageVector`、`Transition` 和 Painter 绘制。把这两条链路分开后，解析成本、插值成本、对象分配与渲染成本才能分别测量。

性能结论需要沿完整显示链验证：Compose 主线程阶段、RenderThread、BLAST buffer transaction、SurfaceFlinger latch 与 present。以 Android 17、API 37、`android-17.0.0_r1` 和 `android17-6.18-2026-06_r6` 为系统基线时，Compose 版本仍应单独记录到具体 artifact 与源码提交。
