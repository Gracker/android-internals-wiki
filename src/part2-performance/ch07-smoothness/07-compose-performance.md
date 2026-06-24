---
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
auto_promoted_by: \"openclaw-task6\
auto_promoted_date: \"2026-05-04\
chapter: 7.7
confidence: medium
deepseek_cn_review_state: done
drafted_by: openclaw-task2a
drafted_date: 2026-04-01
last_deepseek_cn_review_at: 2026-06-23
last_task2b_at: 2026-06-24T08:57:16+08:00+08:00
last_task6_at: 2026-06-24T09:15:00+08:00
last_task6_audit: 2026-06-24
last_task6_audit_log: logs/review/2026-06-24-09-review.md
last_task6_audit_result: pass-light-edit
last_task9_at: \"2026-06-04T20:24:00+08:00\
last_task9_audit: 2026-06-24
last_task9_audit_result: needs-rework
last_task9_autofix_at: 2026-06-04
last_verified: 2026-06-24
last_verified_against: Android 16 Developer Preview
path: Personal-Knowlodge/source/2026-03-08_wechat_沉思录_如何优化_Compose_的性能_通过_底层原理_寻找答案.md
pipeline_stage: task6_pending
polish_by: task2b-polish
polish_count: 1
polish_date: 2026-04-04
review_round: 3
review_type: post-polish-quality-gate
reviewed_by: openclaw-task6
reviewed_date: 2026-06-04
section: 7.7
status: finalized
tags: ['smoothness', 'jank']
task2b_lite_at: 2026-06-24
task2b_result: fixed-lite
task2b_state: fixed
task6_result: pass-light-edit
task6_state: revisiting
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-04
task9_state: reviewed
title: Jetpack Compose 性能优化---


# Jetpack Compose 性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 Compose 渲染模型:Composition → Layout → Drawing 三阶段与传统 View 体系的对比
- 🔹 Recomposition 的触发条件与最小化策略:stable 标记、remember、derivedStateOf
- 🔹 Compose 中的性能陷阱:不稳定参数导致的过度重组、LazyColumn 的 key 策略
- 🔹 Compose 性能检测:Layout Inspector Recomposition 计数、Compose Compiler Metrics
- 🔹 Compose 与 View 混合布局的性能考量(ComposeView / AndroidView 开销)

### 扩展(可选深入)

- 🔸 Compose Multiplatform 的性能差异
- 🔸 Compose 动画性能:animate*AsState vs Animatable vs transition

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要关注 Compose 的性能

在默认的 system trace 里看不到单个 composable function。Perfetto 通常只有 Choreographer、主线程、RenderThread、FrameTimeline 这些线程级或帧级轨道；必须显式开启 composition tracing，system trace 才会把 composable function 写进去。很多人习惯性去翻 "CM / Compose Manager" 这类不存在的入口，排查方向一开始就偏了。

Compose 需要单独建立一套分析视角。它的渲染管线、状态管理和重组机制都不同于传统 View。卡顿可能不是布局层级太深，而是某个状态读取范围过大，导致页面在短时间内重复重组。

理解 Compose 的性能模型之后，才能把 Perfetto、Layout Inspector 和 Compiler Metrics 串成一条可复现的排查路径：先确认帧在哪个阶段超时，再判断有没有不必要的重组，再回到具体 Composable 或状态设计上收敛问题。

## Compose 的渲染模型:Composition → Layout → Drawing

[已验证: 官方文档, developer.android.com/develop/ui/compose/mental-model]

传统 View 体系的渲染过程，我们在前面章节已经讲过了：measure → layout → draw，由 Choreographer 驱动，每个 VSync 周期最多执行一轮。Compose 的渲染过程同样有 Layout 和 Drawing，但在前面多了一个 Composition 阶段。

**Composition(组合)** 会执行 @Composable 函数，更新运行时记录的 group / slot 信息，并通过 Applier 维护后续阶段要消费的节点。这里不能把 `SlotTable` 写成 UI 树：`SlotTable` 是 Compose runtime 的扁平存储结构，底层用 gap buffer 管理 group 和 slot，保存 Composition 过程中产生的调用结构、key、`remember` 值等信息。

进入 **Layout** 阶段时，负责测量和布局的是 `LayoutNode` 树。`LayoutNode` 对应 Compose UI 的布局节点，承接 measure、layout、draw 相关的 modifier / coordinator 信息。Composition 更新运行时状态与节点关系，Layout / Drawing 再沿 `LayoutNode` 树完成尺寸协商和绘制提交。

进入 **Drawing** 阶段后,Compose 的 UI 元素会通过 Android 的 Canvas 进行绘制。Jetpack Compose 是全新的 UI 框架,底层仍没有脱离 Android 的渲染体系--像素还是要画到 Canvas 上。

主要区别在于：传统 View 体系只在 UI 结构发生变化时才重新创建 View 对象（比如 addView/removeView），而 **Compose 的 Composition 阶段在每次状态变化时都可能重新执行**。这就是所谓的“Recomposition”（重组）。

`PausableComposition` 属于 Compose Runtime 的内部子组合机制，从 Compose Runtime 1.0 起就已存在于源码中，但主要用于 `LazyList` 等惰性布局的内部实现，不是面向应用开发者的公开 API。

**版本边界**：`PausableComposition` 本身是 Compose Runtime 的类，不依赖 Android API level。但在 Android 17 (API 37) 环境中，其外部可见行为受 Compose UI 版本影响——`LazyList` 的预组合窗口在 Compose UI 1.3+ 中逐步扩大，1.5+ 中进一步优化了跨帧拆分策略。建议在使用时明确标注 Compose BOM 版本，确保与 Android 17 兼容。

**使用场景**：它的典型用途是 `LazyList` 在列表滚动时，利用帧间隙预先组合即将进入视口的 item，避免 item 出现时才同步组合导致的帧超时。调用方（`LazyList` 内部）通过 `pausableComposition()` 工厂函数创建子组合，并在每帧预算允许的范围内推进组合工作。应用开发者不需要直接使用此类；排查重组性能时，如果 Perfetto 中看到 Composition 阶段被拆成多段，通常就是 `PausableComposition` 在生效。

不要把 `PausableComposition` 理解成系统会自动把任意 Composition 跨帧续跑——只有显式通过 `pausableComposition()` 创建的子组合才具备这种能力，普通顶层 Composition 仍然是单帧内完成的。

[图:Compose 渲染管线三阶段示意--Composition 更新 SlotTable 并维护 LayoutNode 树 → Layout 沿 LayoutNode 测量定位 → Drawing 绘制到 Canvas,与传统 View 体系 measure → layout → draw 对比]

### 重组到底是什么

[已验证: 官方文档, developer.android.com/develop/ui/compose/mental-model#recomposition]

"重组"这个词听起来像是一个复杂的机制,但它的本质非常简单:**重新调用一次 @Composable 函数**。

Compose 编译器插件在编译时会改造每个 @Composable 函数。以一个简单的 Greeting 组件为例:

```kotlin
@Composable
fun Greeting(msg: String) {
    Text(text = "Hello $msg!")
}
```

编译后,这个函数的签名会多出 `Composer` 和 `$changed` 两个参数,函数体里会被插入 `startRestartGroup` 和 `endRestartGroup` 调用。`$changed` 是一个位掩码,编译器把每个参数的变化状态编码进这个 `Int` 里,运行时再配合 `composer.changed(...)` 做按位判断,决定当前调用是直接 skip,还是继续执行函数体。`endRestartGroup` 会返回一个 `ScopeUpdateScope` 对象,开发者可以往上面注册一个回调,当状态变化导致这个函数需要重组时,Compose 运行时就通过这个回调递归调用函数自身。

整个机制基于 Compose 的**状态快照系统(Snapshot)**。当我们通过 `mutableStateOf` 创建一个 State 变量时,它的 getter 和 setter 是自定义的:setter 会通知快照系统"这个值变了",快照系统再找到订阅了这个值的 ScopeUpdateScope,触发重组。

所以当我们说"某个 Composable 发生了重组",准确的意思是:Compose 运行时重新调用了一次这个 @Composable 函数。重组的范围取决于状态读取发生在哪个 Scope--**状态读取发生在哪个 Scope,状态更新时哪个 Scope 就发生重组**。

这个原则非常重要,因为它是所有 Compose 性能优化策略的理论基础。后面我们讲到的 derivedStateOf、延迟读取、Lambda 包装等优化手段,核心都是通过改变状态读取的 Scope 来缩小重组范围。

### 与传统 View 体系的性能对比


社区做过 LazyColumn 和 RecyclerView 的对比测试：同一个列表页面，两套 UI 实现，在不同 Android 版本的设备上测量快速滑动 FPS。

其中一组常被引用的数据是：高端设备（Android 11+）上两者都能接近 60fps；中低端 Android 7.1 设备上，LazyColumn 约 43fps，RecyclerView 约 60fps。同一位测试者在粒子动画场景里又发现 Compose 和 View 的 Canvas 绘制几乎一致。这类数据更适合当成"特定设备、特定版本、特定页面结构下的抽样观察"，不能直接外推成通用结论。真要拿来做项目决策，至少用 Macrobenchmark 的 `FrameTimingMetric` 或 Perfetto，在自己的机型、刷新率、Compose 版本和滚动场景上复测。

这组对比说明的方向没有变:**Compose 本身的渲染性能(Layout + Drawing)已经和传统 View 接近,差距更多出现在 Composition 阶段,也就是重组的开销**。如果我们的 Compose 页面掉帧,大概率就是"Compose 重组了不该重组的东西"。

这也解释了为什么 Compose 性能优化的核心策略就是:**减少不必要的重组、缩小重组的范围**。

[待补充:Compose 和 View 在 Perfetto 中的帧耗时对比截图]

## Recomposition 的触发条件与最小化策略

理解重组的本质之后,下一步是具体的触发条件和优化策略。这部分决定了 Compose 性能优化的方向。

### Strong Skipping 与 stable 标记:让 Compose 更容易跳过重组

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/strongskipping]

Strong Skipping 的版本演进分为三个阶段：

| 阶段 | Compose Compiler | Kotlin | Strong Skipping | 稳定性推断 | Android API 兼容性 |
|------|-----------------|--------|----------------|-----------|------------------|
| 早期（2023） | 1.4.x - 1.5.0 | 1.8.x - 1.9.0 | 不支持 | 仅 `@Stable`/`@Immutable` 手动标记的类才可能让 Composable skippable；不稳定参数导致 Composable 完全不 skippable | Android 8-13 (API 26-33) |
| 过渡期（2024 上半年） | 1.5.1 - 1.5.9 | 1.9.10 - 1.9.24 | 实验性，需显式开启 `experimentalStrongSkipping = true` | 不稳定参数开始支持引用相等比较，但仍需编译器 flag | Android 14-15 (API 34-35) |
| 当前（2024 中至今） | 1.5.10+ / 2.0.0+ | 2.0.20+ | 默认开启 | 所有 restartable Composable 默认 skippable；稳定参数 `equals()` 比较，不稳定参数 `===` 比较 | Android 16-17 (API 36-37) |

关键转折点是 Kotlin 2.0.20 + Compose Compiler 2.0+ 的组合——从这个版本起，Strong Skipping 不需要任何编译器 flag 或显式 opt-in，所有使用新版 Kotlin/Compose 的项目自动获得跳过能力。

从 Kotlin 2.0.20 开始,默认开启。现在判断一个 restartable Composable 能不能跳过重组,优先看的是"这次参数和上次是不是同一个输入":稳定参数按 `Object.equals()` 比较,不稳定参数按引用相等 `===` 比较。只要比较结果没变,这个 Composable 就可以被跳过。

这改变了优化顺序。老规则里,开发者经常要先把参数都做成稳定类型,才能拿到 skippable。现在大多数 restartable Composable 默认就有跳过机会,很多只为"让它能跳过"而加的包装层可以省掉。编译器还会自动 memoize Composable 内部创建的 lambda,减少因为回调对象重新分配带来的连锁重组。

这条规则也改变了可变集合的失败方式。不稳定参数按引用比较,`ArrayList`、`MutableList` 这类对象如果原地修改后继续传同一个引用,restartable Composable 会把它视为同一个输入。UI 是否刷新还取决于上游状态容器有没有发出新值;如果 ViewModel 只执行 `items.add(newItem)`,再把同一个列表引用传下去,StateFlow / Compose 都可能看不到这次内容变化。

**Android 12-14 兼容性注意**：在 Android 12-14 (API 31-34) 设备上，部分 Kotlin 1.8.x 版本可能存在 Strong Skipping 实验性功能的不稳定性。建议在这些版本上显式使用 `@Stable` 注解或不可变集合，避免引用比较带来的刷新不一致问题。

```kotlin
// 容易漏刷新:原地修改同一个 ArrayList
_items.value.add(newItem)
_items.value = _items.value

// 更稳:发布一个新的 List 实例
_items.value = _items.value + newItem
```

Strong Skipping 降低了稳定性标记的门槛,但没有替代不可变数据设计。列表、Map、复杂状态对象仍要避免原地修改。

有一个边界条件需要注意：Strong Skipping 的稳定性推断仅对当前模块（已开启 Compose 编译器插件）生效。如果一个不稳定类定义在独立的数据模块或三方库中（未启用 Compose 编译器），即使 UI 模块开启了 Strong Skipping，编译器也无法推断该类的稳定性——它仍然会被视为不稳定参数，走引用相等比较。这种情况下，要么在数据模块的 `build.gradle` 中也启用 Compose 编译器插件，要么为跨模块传递的类型显式添加 `@Stable` / `@Immutable` 标记。

稳定性没有失效,但角色变了。`@Stable`、`@Immutable`、不可变集合和清晰的 State holder 设计,现在更像是在解决三类问题:

- **语义正确**:避免把"内容变了但引用没变"的对象误当成没变化
- **集合可预测**:`List`、`Map`、`Set` 这类默认不稳定的集合,仍然建议用不可变集合或稳定的包装类型来传递
- **报告可读**:让 Compiler Metrics 更容易看出哪些参数设计还在扩大重组范围

有两种常见手段可以显式表达这种语义:

**@Immutable**：标记完全不可变的类。一旦创建，内部任何内容都不会改变。这适合纯数据模型：

```kotlin
@Immutable
data class ProductListState(
    val products: List<Product>,
    val isLoading: Boolean
)
```

**Android 版本兼容性**：`@Immutable` 注解在 Android 8+ (API 26+) 中稳定可用。在 Android 11 (API 30) 之前的版本中，确保使用 Kotlin 1.6.0+ 以获得完整的注解支持。


**@Stable**：标记"属性会变，但变化路径对 Compose 可见"的类，常见于 State holder：

```kotlin
@Stable
class ProductListState(
    val products: List<Product>,
    val isLoading: Boolean
)
```

`@Immutable` 和 `@Stable` 是**契约**，不是提示。如果标记和真实行为不一致，Compose 可能会跳过本该执行的重组，UI 反而更难排查。

### remember:跨重组保持数据

[已验证: 官方文档, developer.android.com/develop/ui/compose/composition#remember]

`remember` 的作用是在 Composable 函数的多次重组中保持数据。每次重组时，普通变量会被重新初始化，而 `remember` 包裹的值会保留上一次的结果。

最常见的用法是配合 `mutableStateOf` 创建响应式状态:

```kotlin
var clickCount by remember { mutableStateOf(0) }
```

但 `remember` 也可以用来缓存计算结果,避免在每次重组时重复计算:

```kotlin
val sortedItems = remember(items) { items.sortedBy { it.priority } }
```

注意这里的 `items` 是 `remember` 的 key--只有当 items 变化时才会重新排序。如果不指定 key,排序结果会在整个 Composable 的生命周期内被缓存,即使 items 已经变了也不会更新。

### derivedStateOf:只在结果变化时触发重组

[已验证: 官方文档, developer.android.com/develop/ui/compose/side-effects#derivedstateof]

`derivedStateOf` 是减少不必要重组的利器。它创建一个"派生状态"——只有当派生表达式的**结果**发生变化时，才会通知 Compose 触发重组。

一个经典的场景是:根据列表滚动位置控制 FAB 按钮的显隐。

```kotlin
// 问题代码:每次 firstVisibleItemIndex 变化(每滑过一个 item)都触发重组
val shouldShowButton = state.firstVisibleItemIndex == 0

// 优化代码:只在 shouldShowButton 的值切换(true↔false)时才触发重组
val shouldShowButton by remember {
    derivedStateOf { state.firstVisibleItemIndex == 0 }
}
```

前者的状态读取发生在 MainLayout 的 Scope 中,所以每滑过一个 item,整个 MainLayout 都会重组。后者把读取包装在 `derivedStateOf` 里,只有当 `firstVisibleItemIndex == 0` 的布尔结果发生变化时才会通知--也就是从 0 变成 1 和从 1 变成 0 的那两次。其余的滑动完全不会触发重组。

**`derivedStateOf` 的滥用陷阱**:`derivedStateOf` 本身有对象创建和依赖追踪的开销。如果派生结果的变化频率和输入状态完全一样(比如 `derivedStateOf { scrollState.value * 2 }`),它并不能减少任何重组,反而增加了额外的计算层。只有当"输入高频变化,输出低频变化"时才有收益--典型的场景是把连续的滚动 offset 映射为离散的布尔值、索引值或分档结果。如果输入输出同频,直接读原始 State 即可。

### SnapshotStateObserver：三阶段失效的底层机制



前面讲到"状态读取发生在哪个 Scope,状态更新时哪个 Scope 就发生重组",但没有深入到运行时实现。`SnapshotStateObserver`(SSO)是这一机制的核心组件,理解它有助于精准判断 Compose 性能瓶颈的来源。

**核心数据结构**:

SSO 通过 `registerApplyObserver()` 在 snapshot apply 时被调用。当任何 mutable snapshot apply 时,SSO 收到通知。`observeReads(scope, onValueChangedForScope, block)` 在代码执行期间记录状态读取,构建"状态对象→失效作用域"的倒排索引(`ObservedScopeMap.valueToScopes`)。

```kotlin
// SnapshotStateObserver.kt 核心结构
public class SnapshotStateObserver(
    private val onChangedExecutor: (callback: () -> Unit) -> Unit
) {
    // pendingChanges 是 AtomicReference 实现的无锁队列
    private val pendingChanges = AtomicReference<Any?>(null)

    // 注册到 Snapshot.apply 时触发的 observer
    private val applyObserver: (Set<Any>, Snapshot) -> Unit = { applied, _ ->
        addChanges(applied)
        if (drainChanges()) sendNotifications()
    }

    // 读Observer:每次状态读取时调用
    private val readObserver: (Any) -> Unit = { state ->
        if (!isPaused) {
            synchronized(observedScopeMapsLock) { currentMap!!.recordRead(state) }
        }
    }
}
```

**三阶段失效的精确划分**:

| 阶段 | 观察机制 | 失效粒度 | 典型场景 |
|------|---------|---------|---------|
| Composition | `onValueChangedForScope` 回调 | restartable scope 重组 | 普通状态变化 |
| Layout | `LayoutResultObserver` | 仅 measure/layout 重新执行 | 尺寸相关状态 |
| Drawing | `Modifier.drawWithContent {}` / `drawBehind` 中的 layer-level callback | 仅图形层重绘 | `Animatable` 在 draw 阶段读取 |

关键设计:Drawing 阶段的 invalidation 最精细--当状态读取发生在 `Modifier.drawWithContent {}` 内时,状态变更只 invalidate 图形层,完全跳过 Composition 和 Layout。这是 `Animatable` 在 `drawWithContent` 中使用不触发重组的原因。

**DerivedState 去重**:

SSO 实现了 DerivedState 的智能去重:当依赖状态变更时,SSO 先检查 `DerivedState.currentRecord.currentValue` 是否等于 `recordedDerivedStateValues[derived]`。值未变则跳过去重,下游 Composable 不重组。这是 `derivedStateOf` 高效的底层原因。

**典型调用链**:

```
状态写入 → snapshot.apply()
         ↓
    registerApplyObserver 回调触发
         ↓
    SnapshotStateObserver.applyObserver(changes, snapshot)
         ↓
    addChanges(changes) → drainChanges() → sendNotifications()
         ↓
    onValueChangedForScope(scope) → Composable 被标记为需要重组
```

**withoutReadObservation()**:

`Snapshot.withoutReadObservation()` 在特定场景(如更新滚动位置、检查 ComposeView context)时临时暂停读观察,避免不必要的订阅。实现方式是通过 `isPaused` 标志使 `readObserver` 跳过记录。

### 延迟状态读取:缩小重组范围


这是 Android 官方推荐的另一项关键优化。核心思想是:**尽可能把状态的读取推迟到使用它的地方**,利用 Kotlin Lambda 的惰性求值(Laziness)来避免在 Composition 阶段产生不必要的订阅关系。

考虑一个滚动偏移影响标题位置的场景:

```kotlin
// 问题代码:在 Composition 阶段就读取了 scroll.value
@Composable
private fun Title(snack: Snack, scroll: Int) {
    val offset = with(LocalDensity.current) { scroll.toDp() }
    Column(modifier = Modifier.offset(y = offset)) {
        // ...
    }
}
```

当 scroll 值在每次滑动事件中变化时,Title 和它的父级 SnackDetail 都会重组--因为状态读取发生在它们的 Scope 里。

优化方式是把参数改为 Lambda，并把读取放进支持延迟读取的 modifier lambda:

```kotlin
// 优化代码:用 Lambda 延迟读取
@Composable
private fun Title(snack: Snack, scrollProvider: () -> Int) {
    Column(
        modifier = Modifier.offset { IntOffset(x = 0, y = scrollProvider()) }
    ) {
        // ...
    }
}

// 调用方:
Title(snack) { scroll.value }  // scroll.value 被包装在 Lambda 中
```

`Modifier.offset { ... }` 的 lambda 在布局/放置阶段执行，AndroidX 源码也标注这个重载用于频繁变化的 offset，可避免 offset 变化时触发重组。若像 `val offset = scrollProvider().toDp()` 这样在 Composable 函数体中立即调用，读取仍发生在 Composition 阶段，无法达到延迟读取效果。

## Compose 中的性能陷阱

了解优化策略之后，再看实际项目中最容易踩的坑。

### 陷阱一：不稳定参数导致整个页面被拖着重组

这是 Compose 性能问题中最常见的一类。把包含 `var` 属性的类，或者普通 `List<T>` 传给 Composable 时，编译器通常会把它们归为不稳定参数。Strong Skipping 默认开启后，这类问题会出现两种表现：父组件频繁创建新的 List 会让子项重组；原地修改同一个 MutableList 又可能因为引用没变而被跳过。

一个典型案例：ViewModel 暴露 `StateFlow<List<Item>>`，Compose 侧通过 `collectAsState()` 收集。安全的状态更新方式是把列表当成不可变快照，每次内容变化都发布新的 List 实例。直接修改 `ArrayList` 并复用原引用，既可能被 StateFlow 的相等性判断吞掉，也可能被 Strong Skipping 的引用比较跳过。

解决方案:

1. 把上游状态建模成不可变快照,更新时发布新的 `List` 实例
2. 用 `kotlinx.collections.immutable` 的不可变集合替代普通 List,让编译器能推断稳定性
3. 用 `@Immutable` 注解标记数据类(前提是必须保证不可变)
4. 在 Compose Compiler 1.5.5+ 中,通过 Stability Configuration File 声明外部类的稳定性

[已验证: Kotlin 2.0.20+ Strong Skipping 对不稳定参数使用引用相等比较;这能减少过度重组,也会放大可变集合原地修改的刷新风险。来源: Android Developers Strong Skipping 文档]

### 陷阱二：LazyColumn 缺少 key 导致整列表重组


LazyColumn 默认用 item 在列表中的位置(index)作为标识。所以当我们在列表头部插入一个新 item,Compose 会认为所有 item 都变了(因为它们的 index 都变了),导致整列表重组。

解决方案是给每个 item 提供一个稳定的 key:

```kotlin
LazyColumn {
    items(
        items = products,
        key = { it.id }  // 用稳定的业务 ID 而非位置
    ) { product ->
        ProductCard(product)
    }
}
```

有了 key 之后,Compose 就能识别出哪些 item 是新增的、哪些是移动的、哪些没变,只重组发生变化的 item。

### 陷阱三：在 Composable 函数中做计算

如果一个 Composable 函数里有排序、过滤等计算操作,而且这些操作的结果在多次重组间不会变化(或只在特定参数变化时才需要重新计算),那就应该用 `remember` 包裹:

```kotlin
// 错误:每次重组都排序
@Composable
fun ProductList(products: List<Product>) {
    val sorted = products.sortedBy { it.priority }  // 每次重组都执行!
    LazyColumn {
        items(sorted) { ... }
    }
}

// 正确:只在 products 变化时排序
@Composable
fun ProductList(products: List<Product>) {
    val sorted = remember(products) { products.sortedBy { it.priority } }
    LazyColumn {
        items(sorted) { ... }
    }
}
```

## Compose 性能检测工具

优化之前，先要能发现问题。Compose 提供了几个层次的检测工具。

### Perfetto / System Trace:先打开 composition tracing

Perfetto 能看到的内容，取决于 trace 是否启用了 composition tracing。官方文档给出的前提条件是：Android Studio Flamingo 或更高版本、Compose UI 1.3.0+、Compose Compiler 1.3.0+、API 30+ 设备或模拟器，以及工程里加入 `androidx.compose.runtime:runtime-tracing` 依赖。

```gradle
dependencies {
    implementation("androidx.compose.runtime:runtime-tracing")
}
```

如果项目使用 Compose BOM,`runtime-tracing` 使用同一组 BOM 版本即可。满足这些条件后,system trace 里会出现 composable function 的切片,可以直接把长帧回连到具体组合函数。没有满足时,Perfetto 仍然能看 FrameTimeline、`Choreographer#doFrame`、主线程和 RenderThread,但看不到细粒度的 composable 名称。这时要回退到 Layout Inspector 的 recomposition count、Compose Compiler Metrics,以及 FrameTimeline / Choreographer 的帧级观察。

### Layout Inspector:实时查看重组次数

[已验证: 官方文档, developer.android.com/studio/debug/layout-inspector/compose]

Android Studio 的 Layout Inspector 可以实时显示每个 Composable 的重组次数。使用方式:

1. 在 Android Studio 中打开 Layout Inspector(View → Tool Windows → Layout Inspector)
2. 连接正在运行的 debug 应用(需要 API 29+,Compose 1.2.0+)
3. 在 Component Tree 中找到"Show Recomposition Counts"选项并启用

启用后，每个 Composable 旁边会显示两个数字：**recomposition count**（实际重组的次数）和 **skip count**（被跳过的次数）。如果某个 Composable 的重组次数异常高——比如我们在滑动列表时，一个不相关的头部组件被重组了几十次——那就是需要优化的信号。

Layout Inspector 还会用颜色渐变来可视化重组热度:颜色越深表示重组越频繁。双击一个 Composable 可以直接跳转到源码。

### Compose Compiler Metrics:在编译阶段发现不稳定类型

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance#compose-compiler-metrics]

这是一个编译时工具,不需要运行应用就能分析 Compose 的稳定性。配置方式:

```gradle
// build.gradle (module level)
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

构建后会在 `build/compose_compiler/` 目录下生成几个关键文件:

- **module.json**:模块级汇总,包括 skippable Composable 占比、restartable Composable 占比等。如果 skippable 比例很低,说明很多 Composable 因为参数不稳定无法被跳过。
- **composables.txt**:每个 Composable 的详细信息--是否 restartable、是否 skippable、每个参数的稳定性。这个文件是定位问题的主力。
- **classes.txt**:每个类的稳定性推断结果。哪些类被判定为不稳定,以及原因。

社区工具 `compose-report-to-html` 可以把这些文本报告转换成更直观的 HTML 页面,方便团队分享。

建议在 CI 流水线中集成 Compiler Metrics 检查,设置 skippable 比例的阈值(比如低于 80% 就告警),在代码合并前就拦截潜在的性能问题。

### Baseline Profiles:把首启和首轮交互先做热

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/overview]

Compose 页面还有一条经常被忽略的性能轴:首次启动、首次进入页面、首次滚动。页面结构没问题,重组次数也控制住了,应用仍然可能在 cold start 或首轮交互里卡一下,原因往往是 Compose 运行时和业务热点路径还在解释执行或 JIT 预热。

Baseline Profiles 用来解决这个问题。它把关键用户路径上的方法提前交给 ART 做 AOT 编译,官方文档给出的典型收益是代码执行速度可提升约 30%。对 Compose 来说,这一点很实用,因为 Compose 运行时和大量 UI 代码都来自应用与库本身,不像平台 View 那样天然常驻系统镜像。

实践里有两层 Profile:

- **库自带 Profile**:Compose 与部分 Jetpack 库已经随 AAR 提供 baseline profile,能覆盖通用热点路径
- **应用自定义 Profile**:仍然要用 Macrobenchmark 覆盖自己的关键用户旅程,例如冷启动、首屏渲染、首页首滚、详情页切换
- **验收方式**:把 `StartupTimingMetric`、`FrameTimingMetric` 或 Perfetto Trace 放进基准测试,确认 profile 生效后启动时长和首轮 jank 是否收敛

一个常见误判是把首启卡顿全算成 Compose 重组慢。很多场景里,先补 Baseline Profiles,再看是否还存在稳定性、布局层级或状态读取范围的问题,效率更高。

## Compose 与 View 混合布局的性能考量

[已验证: 官方文档, developer.android.com/develop/ui/compose/migrate/interoperability-apis]

很少有项目能一次性把所有页面都迁移到 Compose。更常见的情况是项目中同时存在传统 View 和 Compose，通过互操作 API 桥接。但"桥"本身是有开销的。

### ComposeView:在传统布局中嵌入 Compose

`ComposeView` 是一个传统 View,我们可以在 XML 或代码中创建它,然后通过 `setContent` 设置 Compose 内容:

```xml
<androidx.compose.ui.platform.ComposeView
    android:id="@+id/compose_view"
    android:layout_width="match_parent"
    android:layout_height="wrap_content" />
```

`ComposeView` 的首次创建需要初始化 Composition 和 Compose UI 运行时；后续 item 复用时，成本主要来自内容更新、重组和布局/绘制。AndroidX 源码里 `AbstractComposeView` 会优先查找 View 树上的 `CompositionContext`，找不到时才使用 window-scoped Recomposer，并缓存可用上下文。因此，RecyclerView 中的多个 `ComposeView` 并不等于每个 item 都持有独立 `WindowRecomposer`。

缓解方式是复用 ViewHolder 里的 `ComposeView`，通过 `setContent` 更新内容，并保留默认的 `ViewCompositionStrategy.DisposeOnDetachedFromWindowOrReleasedFromPool`。该默认策略会在非 pooling container detach 时释放 Composition，在 RecyclerView 这类 pooling container 中等到释放出池时 dispose。只有明确要放弃复用缓存或 View 不会再回到窗口时，才手动调用 `disposeComposition()`。

[待验证: Compose 1.10 中 ReuseComposeView API 的稳定性]

### AndroidView:在 Compose 中嵌入传统 View

`AndroidView` 是反向的桥接——在 Compose 布局中嵌入一个传统 View。最常见的场景是使用 WebView、MapView 等没有 Compose 替代品的组件：

```kotlin
@Composable
fun WebViewScreen(url: String) {
    AndroidView(
        factory = { context -> WebView(context).apply { settings.javaScriptEnabled = true } },
        update = { webView -> webView.loadUrl(url) }
    )
}
```


性能注意事项:`factory` 只在首次创建 View 时调用,`update` 在每次重组时都会调用。如果把初始化逻辑错误地放在了 `update` 里,就会导致每次重组都重新执行--比如每次都重新创建 WebViewClient,这是完全没有必要的开销。

### 混合布局的通用建议

- **减少边界跨越**:每次从 Compose 切换到 View 或者反过来,都有上下文切换的开销。尽量把 UI 元素集中在同一种体系中,而不是大量穿插使用。
- **注意 View 的生命周期**:传统 View 有自己的生命周期(attach/detach),而 Compose 组件的生命周期由 Compose 管理。在混合布局中,要确保两者的生命周期同步--比如在 Compose 的 `DisposableEffect` 中清理 View 的监听器。
- **性能测试要覆盖混合场景**:纯 Compose 页面和纯 View 页面的性能我们可能都测过了,但混合页面的性能往往是意想不到的瓶颈。在 Perfetto 中,混合布局的帧延迟通常表现为 RenderThread 和主线程之间的额外同步等待。特别是在低端设备上,Compose 和 View 之间的交互可能引入额外的帧延迟。

## Compose 动画性能


前几节讨论了 Compose 的重组机制和常见的性能陷阱,这些优化手段已经能覆盖大部分场景。但还有一个特殊的性能敏感区域:动画。动画的特点是状态变化极为频繁(每秒 60 甚至 120 次),如果每一帧都走完整的 Composition → Layout → Draw 流程,开销会迅速累积。Compose 提供了三种层次的动画 API,性能特征各不相同:

**`animate*AsState`**(如 `animateColorAsState`、`animateDpAsState`):最简单的声明式动画 API。它返回一个 `State<T>` 对象,动画期间值会持续变化。是否触发重组取决于这个 State 在哪里被读取--如果在 Composable 参数中直接解包(`.value`),每一帧都会触发 Composition;如果延迟到 `Modifier.drawBehind` 或 `Modifier.graphicsLayer` 的 Draw 阶段才读取,则完全跳过 Composition 和 Layout,只触发重绘。区别的关键在于 State 读取的作用域,而不是 API 本身。

**`Animatable`**:更底层的 API,可以在 Coroutine 中手动驱动动画。它的优势在于可以在不触发重组的情况下直接修改绘制属性--比如通过 `Modifier.drawBehind` 在 Draw 阶段直接读取 `Animatable` 的当前值,从而完全跳过 Composition 和 Layout 阶段。**这是 Android 官方推荐的高性能动画方式。**

**`updateTransition`**:用于管理多个属性的联动动画。和 `animate*AsState` 一样,它也通过 State 变化驱动重组,但可以把多个动画的状态集中管理,避免创建多个独立的 State。

从性能角度,我们推荐的策略是:

**优先使用 Draw 阶段动画。** 如果动画只影响绘制属性(颜色、透明度、位移),用 `Animatable` + `Modifier.graphicsLayer{}` 或 `drawBehind`,跳过 Composition 和 Layout。这种方式的开销最小,因为完全不涉及重组。

**布局动画注意缩小重组范围。** 如果动画涉及布局变化(尺寸、位置),只能用 `animate*AsState` 或 `updateTransition`,此时要确保重组范围尽可能小--把动画状态的作用域限制在最小的 Composable 内。

**区分 State 读取阶段。** `animate*AsState` 和 `Animatable` 都会产生高频变化的 State。关键区别在于读取时机:在 Composable 函数参数中读取 → 触发重组;在 `Modifier.drawBehind` / `Modifier.graphicsLayer` 的 lambda 中读取 → 只触发 Draw。如果动画只影响绘制属性(颜色、透明度、缩放),即使使用 `animate*AsState`,只要把 `.value` 的读取放到 Draw 阶段,也不会触发重组。

**避免大范围动画重组。** 不要在动画的每一帧都触发整个页面的重组,这在 Perfetto 中表现为连续的长帧,帧耗时随动画进行不收敛。

[待补充:Compose 动画在 Perfetto 中的帧耗时对比--重组驱动动画 vs Draw 阶段动画的实际帧时间差异]

## 与其他章节的关系

我们在本章讨论的 Compose 性能问题，与本书其他章节有密切的关联。

从卡顿的定义来看（7.1），Compose 的卡顿仍然是"某帧耗时超限"，只是卡顿的来源从传统的 measure/layout/draw 变成了 Composition/Recomposition。从分析方法论来看（7.3），通用的分析框架同样适用——先定位到掉帧的时间段，再分析是什么导致了长帧，只是在 Compose 场景下需要额外检查重组次数。

在底层渲染管线上,Compose 的渲染同样由 Choreographer 驱动(2.4),VSync → doFrame → Composition/Layout/Draw 的过程和传统 View 一致。Composition 和 Layout 阶段在主线程执行,Draw 阶段可能涉及 RenderThread(2.5)。Jetpack Compose 与 Flutter(2.11)的渲染模型有相似的思路--都采用了组合式的 UI 树和差异化的更新策略,但两者的运行时实现完全不同。

## 常见问题与误区

**误区一："Compose 比 View 慢，所以不应该用 Compose"**

实际情况更微妙。Compose 的 Canvas 绘制性能与传统 View 几乎一致,差距主要在 LazyColumn 的快速滑动场景。对于大多数应用,这个差距在实际使用中并不显著。而且随着 Compose 版本迭代(特别是 1.5+ 的 Strong Skipping 和 1.9/1.10 的 API 优化),性能在持续改善。

**误区二:"给所有类加 @Stable 就能解决性能问题"**

`@Stable` 是一个契约,不是魔法。如果我们的类不满足稳定性的要求(比如内部有不受 State 管理的可变状态),加注解不仅不能提升性能,还会导致 UI 不更新的 bug。正确做法是先用 Compiler Metrics 找到实际不稳定的类,然后根据实际情况选择修复方式。

**误区三:"Compose 的 remember 就是缓存,什么都能往里塞"**

`remember` 有缓存效果,但它的语义是"跨重组保持状态",不是通用缓存。`remember` 不关心内存压力,不会被自动回收。如果我们用它缓存大量数据,可能导致内存问题。对于需要响应配置变更的场景,应该考虑 `rememberSaveable`。

**误区四:"Compose 就不需要关心过度绘制了"**

过度绘制(Overdraw)的检测方式在 Compose 中完全适用。虽然 Compose 在理论上可以更精确地控制重绘区域,但如果我们在 Compose 中堆叠了多层半透明组件,过度绘制的问题和传统 View 一样存在。可以用"Show GPU Overdraw"来检测。

## 参考资料

- [Jetpack Compose Performance | Android Developers](https://developer.android.com/develop/ui/compose/performance) [已验证: 官方文档]
- [Compose Mental Model | Android Developers](https://developer.android.com/develop/ui/compose/mental-model) [已验证: 官方文档]
- [Strong Skipping | Android Developers](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping) [已验证: 官方文档]
- [Baseline Profiles Overview | Android Developers](https://developer.android.com/topic/performance/baselineprofiles/overview) [已验证: 官方文档]
- [Compose Compiler Metrics | Android Developers](https://developer.android.com/develop/ui/compose/performance#compose-compiler-metrics) [已验证: 官方文档]
- [Layout Inspector for Compose | Android Developers](https://developer.android.com/studio/debug/layout-inspector/compose) [已验证: 官方文档]
- [Compose and View Interoperability | Android Developers](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis) [已验证: 官方文档]
- [朱涛·沉思录:如何优化 Compose 的性能](https://mp.weixin.qq.com/s?__biz=Mzg5MDY5ODk2MQ==&mid=2247485054)
- [提升 Jetpack Compose 性能 | Kotlin 社区](https://mp.weixin.qq.com/s?__biz=MzIyMzg2MzQxNg==&mid=2247486800)
- [Compose 渲染性能到底怎么样 | 程序员江同学](https://mp.weixin.qq.com/s?__biz=MzkzNjMxNzY5NQ==&mid=2247484027)
- [用 derivedStateOf 提升性能 | 郭霖](https://mp.weixin.qq.com/s?__biz=MzA5MzI3NjE2MA==&mid=2650284101)
- [掌握 Android Compose:从基础到性能优化全面指南](https://mp.weixin.qq.com/s?__biz=MzkyNTUyNDA5Nw==&mid=2247485870)

**[源码调研补遗 2026-06-02]**：`derivedStateOf` 底层源码已验证。一手来源：
- `androidx-main compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt`（`DerivedSnapshotState` 实现、`readableHash` 机制、`policy` 参数）
- `androidx-main compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/snapshots/SnapshotStateObserver.kt`（三阶段失效、`withoutReadObservation`）
详见：`DeepResearch/2026-06-02-android-compose-derivedstate-sso-deep-source-analysis.md`

**[源码调研补遗 2026-06-24]**：Compose Compiler 2.0 Strong Skipping 性能优化源码分析。一手来源：
- `plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/ComposePlugin.kt`（FeatureFlag.StrongSkipping 架构、编译器配置）
- `plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/lower/ComposerLambdaMemoization.kt`（Strong Skipping 代码生成、composer.startReplaceableGroup 跳过逻辑）
- `plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/lower/ClassStabilityTransformer.kt`（类稳定性标记、StabilityBits 位掩码）
- `plugins/compose/compiler-hosted/src/main/java/androidx/compose/compiler/plugins/kotlin/lower/ComposerParamTransformer.kt`（composer.changed[n] 参数生成、recomposition 优化）
详见：`DeepResearch/2026-06-24-compose-20-strong-skipping-performance.md`
