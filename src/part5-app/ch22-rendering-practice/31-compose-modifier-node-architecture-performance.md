---
title: "Compose Modifier.Node 架构与性能迁移"
chapter: "22.31"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, modifier-node, performance, architecture-migration, recomposition]
related_chapters: ["22.3", "22.20", "22.21", "22.22", "22.25", "22.28", "7.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "Compose BOM 2025.12.00 (Compose 1.10), Kotlin 2.2, AOSP android-17.0.0_r1"
confidence: high
gap_source: "AOSP结构+官方文档"
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/compose/custom-modifiers"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/ModifierNodeElement.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/NodeCoordinator.kt"
  - type: talk
    path: "Google I/O 2024 — Compose Modifiers deep dive"
  - type: talk
    path: "Compose 1.7 release notes — Modifier.Node stable"
---

# 22.31 Compose Modifier.Node 架构与性能迁移

`Modifier.Node` 是 Compose UI 的自定义 Modifier 基础设施。它把短生命周期的配置对象与可跨重组复用的运行节点分开，适合实现绘制、测量、语义、焦点和输入等底层行为。以下说明它解决的问题、节点复用机制、无需使用它的场景，以及迁移时容易写错的生命周期和失效逻辑。

验证基线如下：

- Android 平台：Android 17、API 37、`android-17.0.0_r1`
- 内核：`android17-6.18-2026-06_r6`
- Compose：Compose BOM `2026.06.01`，Compose UI 与 Foundation `1.11.4`
- Compose UI 源码：AndroidX 提交 `854220f44ea8ea80fee824a6c5a045f39bede289`

`Modifier.Node` 随 Compose UI 库发布，不由设备 API 级别或 Linux 内核版本提供。Android 17 与内核锚点用于限定系统环境；节点复用、链更新和自动失效语义应以应用实际依赖的 Compose UI 版本为准。

`Modifier.Node` API 在 Compose UI 1.3.0 以实验形式出现。当前项目采用 1.11.4 稳定版，因此正文不再用“从某个 Android 版本开始支持”描述它，也不把早期实验版本的内部实现当成当前契约。

## 1. 先判断是否需要自定义节点

官方文档给出的选择顺序很实用：

| 需求 | 合适的实现 |
| --- | --- |
| 只需组合现有 Modifier | 编写普通、非 `@Composable` 的 Modifier 工厂并链接现有 Modifier |
| 只需把参数传给现有 Modifier | 继续使用现有 Modifier，不增加 Node |
| 必须读取组合调用点的值，且无法改为节点侧读取 | 谨慎使用 `@Composable` Modifier 工厂 |
| 需要新的绘制、测量、语义、焦点或输入行为 | `ModifierNodeElement` + `Modifier.Node` |
| 节点内部需要跨重组状态或附着期任务 | 在 Node 字段与 `coroutineScope` 中管理 |

下面的工厂只组合已有能力，增加 Node 反而会提高维护成本。

```kotlin
fun Modifier.articleCard(
    background: Color,
    shape: Shape,
): Modifier = this
    .clip(shape)
    .background(background)
    .padding(horizontal = 16.dp, vertical = 12.dp)
```

这段代码没有自定义阶段行为。`clip`、`background` 和 `padding` 已有各自的节点实现，普通工厂还能在组合外创建并复用。

需要新行为时，Node 的主要收益来自运行对象复用和明确的阶段接口。它并不保证每个自定义 Modifier 都更快；热点是否改善仍要通过分配、帧时间和阶段执行记录确认。

## 2. Element 与 Node 各自保存什么

一个 Node 型 Modifier 包含两类对象：

- `ModifierNodeElement<N>` 是轻量配置值。Composable 执行时仍可能创建新的 Element。
- `Modifier.Node` 是附着在 `LayoutNode` 的运行对象，可以保存状态并跨多次重组复用。

Element 负责 `create()` 与 `update(node)`。Node 通过所实现的接口声明自己参加哪些阶段，例如：

| 节点接口 | 作用 |
| --- | --- |
| `LayoutModifierNode` | 测量与放置 |
| `DrawModifierNode` | 绘制 |
| `SemanticsModifierNode` | 语义与无障碍 |
| `PointerInputModifierNode` | 指针命中与事件分发 |
| `CompositionLocalConsumerModifierNode` | 读取附着位置的 `CompositionLocal` |
| `ObserverModifierNode` | 观察显式 `observeReads` 中的快照读取 |
| `LayoutAwareModifierNode` | 尺寸或放置回调 |

Node 可以实现多个接口。运行时会据此计算节点的 `kindSet` 位集合，用于跳过不相关的链区间并触发对应阶段的自动失效。

### 2.1 一个最小、可复用的绘制节点

下面的示例增加一个圆形绘制行为，结构与 Compose 1.11.4 官方示例一致。

```kotlin
private class CircleNode(
    var color: Color,
) : Modifier.Node(), DrawModifierNode {

    override fun ContentDrawScope.draw() {
        drawCircle(color)
        drawContent()
    }
}

private data class CircleElement(
    val color: Color,
) : ModifierNodeElement<CircleNode>() {

    override fun create(): CircleNode = CircleNode(color)

    override fun update(node: CircleNode) {
        node.color = color
    }

    override fun InspectorInfo.inspectableProperties() {
        name = "circle"
        properties["color"] = color
    }
}

fun Modifier.circle(color: Color): Modifier =
    this then CircleElement(color)
```

`CircleElement` 只保存输入，`CircleNode` 保存当前运行状态。相同位置继续使用 `CircleElement` 时，颜色变化会更新现有 Node；默认自动失效随后安排绘制，无需在这个 `update()` 中再次调用 `invalidateDraw()`。

示例调用了 `drawContent()`，所以链中更内侧的绘制和组件内容仍会执行。如果设计目标是完全替换内容绘制，才应省略它。

## 3. NodeChain 如何决定复用、更新或替换

节点链的所有权与差分逻辑位于 `LayoutNode.nodes` 对应的 `NodeChain`。`NodeCoordinator` 负责坐标、绘制、命中和布局协作；它不是 Element 列表的所有者，也不独自执行整条 Modifier 差分。

Compose UI 1.11.4 的 `NodeChain.actionForModifiers()` 规则如下：

| 旧 Element 与新 Element | 动作 | Node 结果 |
| --- | --- | --- |
| `prev == next` | 复用 | 沿用 Node，不调用 `update()` |
| 不相等，但运行时类型相同 | 更新 | 沿用 Node，调用新 Element 的 `update(node)` |
| 运行时类型不同 | 替换 | 移除旧 Node，创建新 Node |

等长、类型顺序稳定的链走线性快速路径。出现插入、删除或类型变化后，`NodeChain` 使用修改过的 Myers 差分算法计算结构变化。`LayoutModifierNode` 需要专用的 `LayoutModifierNodeCoordinator`；其他节点会与所在链段共享协调器。

这套规则带来三个实现要求：

1. Element 的 `equals()` 与 `hashCode()` 必须覆盖所有会改变 Node 行为的输入。
2. `update()` 必须把这些输入同步到现有 Node。
3. 不要把会频繁变化的运行状态放进 Element；它应留在 Node，或由节点观察外部状态。

参数型 Element 使用 `data class` 通常最安全。无参数 Element 可以使用单例，并提供稳定的相等与散列语义。错误的 `equals()` 会让运行时错误地跳过 `update()`；遗漏字段则可能让界面保留旧配置。

Node 复用不等于 Element 零分配。Modifier 工厂在 Composable 内执行时，新的轻量 Element 仍可能出现；复用的是 Element 背后的 Node 及其状态。

## 4. update() 与自动失效

`Modifier.Node.shouldAutoInvalidate` 默认返回 `true`。同类型 Element 发生更新后，运行时会按 Node 接口自动安排相关工作：

- `LayoutModifierNode`：使测量结果失效；
- `DrawModifierNode`：使绘制层失效；
- `SemanticsModifierNode`：使语义配置失效；
- `LayoutAwareModifierNode`：按具体回调类型安排测量、放置或位置通知；
- 其他支持自动失效的节点类型：执行各自的失效处理。

所以，常规 `update()` 只同步字段即可。无条件手动调用 `invalidateDraw()` 或 `invalidateMeasurement()` 会重复表达运行时已经知道的信息。

### 4.1 何时关闭自动失效

一个 Node 同时实现多个阶段接口，而某些参数只影响其中一个阶段时，可以把 `shouldAutoInvalidate` 设为 `false`，再由 `update()` 精确选择失效范围。这样写的责任更大：遗漏调用会造成 UI 不更新。

下面的节点只参与绘制，用它演示手动失效的完整约束。

```kotlin
private class StripeNode(
    var color: Color,
    var visible: Boolean,
) : Modifier.Node(), DrawModifierNode {

    override val shouldAutoInvalidate: Boolean = false

    override fun ContentDrawScope.draw() {
        drawContent()
        if (visible) {
            drawRect(
                color = color,
                size = Size(width = size.width, height = 2.dp.toPx()),
            )
        }
    }
}

private data class StripeElement(
    val color: Color,
    val visible: Boolean,
) : ModifierNodeElement<StripeNode>() {

    override fun create(): StripeNode = StripeNode(color, visible)

    override fun update(node: StripeNode) {
        val visualChanged =
            node.color != color || node.visible != visible

        node.color = color
        node.visible = visible

        if (visualChanged) {
            node.invalidateDraw()
        }
    }
}

fun Modifier.bottomStripe(
    color: Color,
    visible: Boolean,
): Modifier = this then StripeElement(color, visible)
```

这里关闭自动失效后，`update()` 只在可见结果变化时安排绘制。若节点还实现 `LayoutModifierNode`，尺寸参数变化应调用 `invalidateMeasurement()`；只影响放置逻辑的参数可调用 `invalidatePlacement()`。当前公开 API 中没有 `invalidateLayout()` 这个 `LayoutModifierNode` 扩展函数。

默认自动失效适合绝大多数业务节点。只有剖析结果表明无效阶段调用值得优化，并且测试能覆盖每个参数分支时，才考虑手动模式。

## 5. 生命周期、协程与可复用内容

Node 有四个生命周期入口需要区分：

- `create()` 创建对象；Node 此时尚未附着。
- `onAttach()` 表示 Node 已进入 UI 树，可以访问 `owner` 和 `coroutineScope`；实现相应消费接口后也可读取 `CompositionLocal`。
- `onDetach()` 在 Node 离开当前 UI 树前调用；之后节点协程作用域会被取消。
- `onReset()` 在可复用布局进入复用池前调用，例如 Lazy 列表中的内容被移出可见区域。

`onDetach()` 后同一个 Node 仍可能再次附着。`onReset()` 还表示它未来可能服务于语义上不同的数据项，因此焦点、按压、拖拽进度和临时选择等数据项级状态需要清理。

Node 自带的 `coroutineScope` 仅在附着期间可访问。无需从 Element 传入外部作用域，也不能在 Node 中调用 `LaunchedEffect`。下面用两个短节点分别展示附着期动画和复用状态清理。

```kotlin
private class EntranceOverlayNode :
    Modifier.Node(), DrawModifierNode {

    private val progress = Animatable(0f)

    override fun onAttach() {
        coroutineScope.launch {
            progress.snapTo(0f)
            progress.animateTo(1f)
        }
    }

    override fun ContentDrawScope.draw() {
        drawContent()
        val alpha = (1f - progress.value) * 0.08f
        if (alpha > 0f) {
            drawRect(Color.Black.copy(alpha = alpha))
        }
    }
}

private class SelectableNode : Modifier.Node() {
    var selected by mutableStateOf(false)

    override fun onReset() {
        selected = false
    }
}
```

`EntranceOverlayNode` 每次附着都在新作用域中重置并启动动画；解除附着后，作用域由 Node 自动取消。`Animatable.value` 在绘制阶段读取，快照变化会使绘制阶段重新执行。`SelectableNode` 则在进入复用流程时清除与旧数据项绑定的选择状态。

## 6. Modifier.composed 与 @Composable 工厂的准确边界

`Modifier.composed {}` 可以保存实例专属状态。块中的 `remember` 在组合位置保持不变时会复用，并不会因为每次重组就必然创建和丢弃。它的问题来自另一组成本：

- `composed` Element 应用到布局前要经过 `Composer.materialize()`；
- 工厂为每个应用位置进入组合并生成实际 Modifier 链；
- 状态和副作用依赖组合槽位生命周期，而非 Node 的附着与复用生命周期；
- 相比 Node，会增加组合工作和中间对象。

官方当前文档把 `composed {}` 标为“不再推荐”，没有把所有重载从公开 API 删除。维护旧代码时，应依据热点数据安排迁移，避免把“不推荐”写成“运行即错误”。

`@Composable` Modifier 工厂也有相似限制。返回值不是 `Unit` 的 Composable 函数不能被 Compose 编译器跳过，因此这种工厂即使输入稳定，也会在调用者重组时执行。它读取的 `CompositionLocal` 值来自工厂调用位置，而普通 Node 工厂可在使用位置读取附着环境。

下面的代码用于说明调用位置语义，不是推荐模板。

```kotlin
@Composable
fun Modifier.localTint(): Modifier {
    val tint = LocalContentColor.current
    return drawWithContent {
        drawContent()
        drawRect(tint.copy(alpha = 0.08f))
    }
}
```

`LocalContentColor` 在 `localTint()` 被调用的位置解析。如果构造出的 Modifier 被传到另一个具有不同 `CompositionLocalProvider` 的子树，它不会自动改用应用位置的值。需要应用位置语义时，应让 Node 实现 `CompositionLocalConsumerModifierNode`。

## 7. 在 Node 中读取 CompositionLocal

Node 不能调用 `CompositionLocal.current`。实现 `CompositionLocalConsumerModifierNode` 后，可以通过 `currentValueOf(local)` 读取 Node 所附着布局位置的值。

下面的绘制节点在 draw 阶段读取本地背景色。

```kotlin
private class LocalBackgroundNode :
    Modifier.Node(),
    DrawModifierNode,
    CompositionLocalConsumerModifierNode {

    override fun ContentDrawScope.draw() {
        val color = currentValueOf(LocalArticleBackground)
        drawRect(color)
        drawContent()
    }
}
```

测量、绘制、语义等受快照观察的阶段会跟踪 `currentValueOf()` 读取。对应 `CompositionLocal` 改变后，Compose 会使读取它的阶段失效。

如果读取发生在这些阶段之外，需要同时实现 `ObserverModifierNode`，并在每次通知后重新进入 `observeReads`。

```kotlin
private class LocalPolicyNode :
    Modifier.Node(),
    CompositionLocalConsumerModifierNode,
    ObserverModifierNode {

    private var policy: ArticlePolicy? = null

    override fun onAttach() {
        readPolicy()
    }

    override fun onObservedReadsChanged() {
        readPolicy()
    }

    override fun onDetach() {
        policy = null
    }

    private fun readPolicy() {
        observeReads {
            policy = currentValueOf(LocalArticlePolicy)
        }
    }
}
```

`observeReads` 的通知是一次性的观察回调。`onObservedReadsChanged()` 必须再次读取，才能继续观察后续变化。`currentValueOf()` 只能在 Node 已附着时调用。

## 8. LayoutModifierNode：复用不等于测量缓存

`LayoutModifierNode.measure()` 与 `LayoutModifier.measure()` 遵守相同的单子项测量协议：接收父约束、选择传给被包裹内容的约束、取得 `Placeable`，再返回自身尺寸和放置逻辑。

下面的示例给内容增加水平方向的内边距，用于展示约束传播。

```kotlin
private class HorizontalInsetNode(
    var inset: Dp,
) : Modifier.Node(), LayoutModifierNode {

    override fun MeasureScope.measure(
        measurable: Measurable,
        constraints: Constraints,
    ): MeasureResult {
        val insetPx = inset.roundToPx()
        val horizontal = insetPx * 2
        val childConstraints =
            constraints.offset(horizontal = -horizontal)
        val placeable = measurable.measure(childConstraints)

        val width =
            constraints.constrainWidth(placeable.width + horizontal)
        val height =
            constraints.constrainHeight(placeable.height)

        return layout(width, height) {
            placeable.placeRelative(insetPx, 0)
        }
    }
}

private data class HorizontalInsetElement(
    val inset: Dp,
) : ModifierNodeElement<HorizontalInsetNode>() {

    override fun create(): HorizontalInsetNode =
        HorizontalInsetNode(inset)

    override fun update(node: HorizontalInsetNode) {
        node.inset = inset
    }
}

fun Modifier.horizontalInset(inset: Dp): Modifier {
    require(inset.value >= 0f)
    return this then HorizontalInsetElement(inset)
}
```

默认自动失效会在 `inset` 更新后安排重新测量。示例限制了非负值；生产实现还要根据产品允许的最大尺寸防止像素加法溢出。

这段代码用于解释测量协议。业务仅需水平内边距时，应直接使用 `Modifier.padding(horizontal = inset)`；只有内置 Modifier 无法表达布局语义时才保留自定义节点。

Node 的持久化可以减少 Node 创建与链结构更新，但不会为每个 `LayoutModifierNode` 自动提供“参数不变就复用上次 MeasureResult”的公开保证。是否跳过测量由 `LayoutNode` 的测量状态、父约束、子项状态和读取依赖共同决定。不要把 Node 复用当成测量缓存。

`LayoutModifierNode` 已为四种固有尺寸测量方法提供默认实现，它们通过节点的 `measure()` 估算结果。自定义布局若需要不同语义，应覆写对应方法并保持约束一致性；源码没有承诺由 `NodeCoordinator` 为每个 Modifier 单独缓存固有尺寸结果。

## 9. PointerInputModifierNode：消费发生在 change 上

Compose UI 1.11.4 中，接口签名为：

```kotlin
fun onPointerEvent(
    pointerEvent: PointerEvent,
    pass: PointerEventPass,
    bounds: IntSize,
)
```

方法返回 `Unit`。需要消费事件时，对相应的 `PointerInputChange` 调用 `consume()`；不能用 Boolean 返回值声明消费。

下面的节点只观察 Initial pass，并把事件交给调用者。

```kotlin
private class PointerObserverNode(
    var onEvent: (PointerEvent) -> Unit,
) : Modifier.Node(), PointerInputModifierNode {

    override fun onPointerEvent(
        pointerEvent: PointerEvent,
        pass: PointerEventPass,
        bounds: IntSize,
    ) {
        if (pass == PointerEventPass.Initial) {
            onEvent(pointerEvent)
        }
    }

    override fun onCancelPointerInput() = Unit
}

private data class PointerObserverElement(
    val onEvent: (PointerEvent) -> Unit,
) : ModifierNodeElement<PointerObserverNode>() {

    override fun create(): PointerObserverNode =
        PointerObserverNode(onEvent)

    override fun update(node: PointerObserverNode) {
        node.onEvent = onEvent
    }
}
```

直接实现该接口适合明确理解三个事件分发阶段、命中路径和消费规则的底层组件。复杂手势继续使用 `Modifier.pointerInput`、`awaitPointerEventScope` 与 Foundation 手势检测器通常更安全。当前 `pointerInput` 本身已经由 `SuspendingPointerInputModifierNode` 支持，挂起式手势的结构化并发、取消和重启语义有实际价值，不能简单归类为应消除的“协程调度开销”。

## 10. graphicsLayer 与阶段读取

`Modifier.graphicsLayer { ... }` 的 lambda 版本允许在图层属性配置阶段读取状态。状态变化时可以只更新图层属性，避开组合与布局阶段，适合 `alpha`、`scale`、`translation` 等视觉属性动画。

下面的代码用于把动画值放到图层阶段读取。

```kotlin
val alpha by transition.animateFloat(
    transitionSpec = { tween() },
    label = "article-alpha",
) { visible ->
    if (visible) 1f else 0f
}

Box(
    Modifier.graphicsLayer {
        this.alpha = alpha
    }
)
```

这一模式已经使用 Compose 内部的 Node 实现。业务代码无需为了“使用 Node”再复制内部 `GraphicsLayerModifierNode`。公开 `graphicsLayer` API 还能处理图层创建、属性更新和平台渲染后端适配，通常比自建绘制节点更稳妥。

Node 本身也不会阻止父 Composable 重组。性能收益来自把状态读取放在需要的阶段、复用运行节点并减少 `materialize()` 展开或节点替换；父级是否重组仍由 Compose Runtime 的状态读取和跳过规则决定。

## 11. 迁移步骤

### 11.1 清点旧实现

优先检查：

- `Modifier.composed {}` 中存在状态、动画或副作用；
- `@Composable` Modifier 工厂在滚动列表或动画热点中频繁执行；
- 自定义旧式 `DrawModifier`、`LayoutModifier` 或 `PointerInputFilter`；
- Element 的输入频繁变化，且当前实现出现明显分配或链替换；
- 同一行为需要精确管理附着、取消或复用状态。

只组合内置 Modifier 的普通工厂可以保留。低频页面也无需因为 API 更新而强制迁移。

### 11.2 分开配置与运行状态

迁移时可按下表安排字段：

| 字段 | 放置位置 |
| --- | --- |
| 调用者传入的颜色、尺寸、回调、策略 | Element，并在 `update()` 同步给 Node |
| 按压、拖拽、焦点、动画进度、缓存对象 | Node |
| 只在附着期间运行的任务 | Node 的 `coroutineScope` |
| 与复用数据项绑定的临时状态 | Node，并在 `onReset()` 清理 |
| 应用位置的 CompositionLocal | `CompositionLocalConsumerModifierNode` |

Element 应保持轻量与不可变。Node 中不要保存 Activity、View 或长生命周期对象，除非拥有明确的释放规则。

### 11.3 保持 Element 类型稳定

同一链位置在两个不同 Element 子类之间切换会导致 Node 替换。可选行为如果能够由同一个 Element 的参数表达，通常更利于复用；但不要为此制造包含大量互斥字段的通用 Node。类型设计仍应以职责清晰为前提。

### 11.4 选择失效策略

先使用默认自动失效，确认功能和阶段行为正确。若节点实现多个接口且更新非常频繁，再通过跟踪记录观察是否存在多余测量或绘制。只有证据充分时才关闭自动失效，并为每个输入写出对应的 `invalidateDraw()`、`invalidateMeasurement()`、`invalidatePlacement()` 或语义失效调用。

## 12. 性能验证：测什么，怎样解释

迁移前后要使用同一构建类型、设备状态、操作脚本和样本窗口。推荐至少观察以下四类证据：

| 证据 | 工具 | 可回答的问题 |
| --- | --- | --- |
| 分配记录 | Android Studio Memory Profiler、分配跟踪 | Element、lambda、Node 或手势对象分配是否减少 |
| 主线程阶段 | Perfetto、Compose tracing | Composition、Measure、Layout、Draw 的工作是否变化 |
| 用户可见帧表现 | Macrobenchmark、FrameTimingMetric | P50、P90、P95、P99 与超时帧是否改善 |
| 编译器可跳过性 | Compose compiler reports/metrics | 相关 Composable 的稳定性与跳过条件是否合理 |

不要预设“迁移后 Composable 重组次数一定下降”。Modifier 工厂所在的父函数仍可能重组，Element 也可能重建。更可靠的预期是：

- 相同 Element 类型保留既有 Node；
- `composed` 的 `materialize()` 展开成本消失；
- Node 内状态不再依赖额外的 Modifier 组合层；
- 参数变化只触发节点声明的阶段；
- 热点路径中的对象分配和阶段耗时有机会下降。

Macrobenchmark 的目标值应由当前产品基线、设备档位和业务场景确定，不使用脱离项目数据的固定百分比。若帧时间没有改善，也要检查瓶颈是否位于图片解码、文本布局、GPU、Binder、I/O 或其他部分。

### 12.1 一条实用的源码断言

调试 Element 是否复用时，可以把 Compose 1.11.4 的链动作规则作为断言模型：

```text
equals -> reuse without update
same runtime type, not equals -> reuse node and update
different runtime type -> replace node
```

这段规则适合帮助解释 `create()` 与 `update()` 的调用次数。它属于 Compose UI 内部实现，升级 Compose 后仍应回到目标版本源码复核，不能将其视为跨所有未来版本不变的二进制契约。

## 13. Android 17 与多平台边界

Android 17 不改变 `ModifierNodeElement` 的复用协议。它可能通过平台输入、窗口、渲染、无障碍或硬件加速行为影响具体组件，但这些影响要在对应 Android API 章节单独验证。

`Modifier.Node` 与主要节点接口位于 Compose UI 的 `commonMain` 源码，因此 Compose Multiplatform 也共享这套抽象。平台渲染后端、输入接入和窗口系统并不相同，不能由 Android 的 HardwareRenderer 行为推导 iOS、Desktop 或 Web 的帧表现。跨平台项目应在各目标平台分别测量。

Linux 内核锚点 `android17-6.18-2026-06_r6` 不参与 Node 链差分。只有分析调度、频率、GPU 驱动或输入延迟的系统跟踪时，内核版本才进入证据范围。

## 14. 源码导航与核查清单

相关结论以 Compose UI 1.11.4 发布提交为准，关键文件如下：

- [`ModifierNodeElement.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/ModifierNodeElement.kt)：`create()`、`update()`、`equals()` 与 `hashCode()` 要求
- [`Modifier.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/Modifier.kt)：Node 生命周期、`coroutineScope`、`shouldAutoInvalidate`
- [`NodeChain.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/NodeChain.kt)：Element 差分、Node 复用和协调器同步
- [`NodeKind.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/NodeKind.kt)：节点类型识别与自动失效
- [`LayoutModifierNode.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/LayoutModifierNode.kt)：测量、固有尺寸默认实现与布局失效 API
- [`PointerInputModifierNode.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/PointerInputModifierNode.kt)：事件签名、取消与命中扩展
- [`CompositionLocalConsumerModifierNode.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/node/CompositionLocalConsumerModifierNode.kt)：应用位置的 `CompositionLocal` 读取与观察规则
- [`ComposedModifier.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/ComposedModifier.kt)：`composed` Element 与 `materialize()` 展开

版本与用法文档：

- [Compose BOM mapping](https://developer.android.com/develop/ui/compose/bom/bom-mapping)
- [Compose UI release notes](https://developer.android.com/jetpack/androidx/releases/compose-ui)
- [Custom modifiers](https://developer.android.com/develop/ui/compose/custom-modifiers)
- [Modifier.Node API reference](https://developer.android.com/reference/kotlin/androidx/compose/ui/Modifier.Node)

提交迁移代码前，逐项确认：

- Element 的全部行为输入都参与 `equals()` 与 `hashCode()`；
- `update()` 同步了所有 Element 输入；
- 默认自动失效没有被重复手动调用；
- 关闭自动失效后，每类变化都有对应失效调用；
- `currentValueOf()` 只在附着期读取，阶段外读取使用 `observeReads`；
- 附着期任务使用 Node 的 `coroutineScope`；
- 可复用内容的临时状态在 `onReset()` 清理；
- 指针输入通过 `PointerInputChange.consume()` 表达消费；
- 测量逻辑遵守父约束，没有假设 Node 自带 MeasureResult 缓存；
- 性能结论来自迁移前后的同条件数据。
