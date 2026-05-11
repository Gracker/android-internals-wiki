---
title: "Jetpack Compose 性能优化"
chapter: "22.3"
section: "22.3"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-12"
last_verified_against: "Compose BOM 2025.12.00, Kotlin 2.2"
confidence: high
drafted_date: "2026-05-12"
polish_count: 0
sources:
  - type: official
    path: "Compose BOM 2025.12.00 release notes"
  - type: blog
    path: "Google Android Developers Blog - Compose 1.10 性能对等公告 (2025.12)"
  - type: aosp
    path: "androidx/compose/runtime/ PausableComposition"
tags: [compose, recomposition, stability, derivedstateof, pausable-composition, strong-skipping]
related_chapters: ["7.7", "2.4", "22.1"]
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: fixed
---

# Jetpack Compose 性能优化

Compose 渲染管线的原理和机制在 §7.7 已详细拆解。本节聚焦工程实战：怎么写出不会卡顿的 Compose 代码，怎么用工具定位性能问题，以及 2025 年底 Compose runtime 的几个关键变化如何改变了优化策略的优先级。

先建立一条基准线：**Compose BOM 2025.12.00（对应 Compose 1.10）官方宣布在滚动性能上与 View 系统达到性能对等**。Google 内部长列表滚动基准测试的卡顿率降至 0.2%。这不是说 Compose 不需要优化，而是说运行时层面最大的性能坑（长列表组合阻塞主线程）已经被 Pausable Composition 解决了。剩下需要开发者关注的，是组合范围控制、状态读取阶段和互操作开销。

## 重组控制：从手动优化到编译器自动跳过

### Compose 重组的触发条件与成本

Compose 的渲染管线分三阶段：Composition → Layout → Draw。重组（Recomposition）就是重新执行 Composition 阶段——重新调用 `@Composable` 函数，根据新的状态值生成新的 UI 树。

重组的开销来自两个地方：

1. **被调用的 Composable 函数本身的执行时间**：函数里有复杂计算、对象分配或子树嵌套深，重组一次的 CPU 时间就高。
2. **下游传播**：一个 Composable 重组后，如果它的子 Composable 参数也变了，子 Composable 也会跟着重组。

控制重组的核心思路：**让状态变化只触发最小范围的 Composable 重新执行**。

Compose runtime 的跳过（skip）机制：如果一个 `@Composable` 函数的所有参数与上次调用相比都"相等"（通过 `equals()` 判断），runtime 会跳过整个函数体的执行，直接复用上一次的结果。这就是 Stability 标记和 Strong Skipping Mode 要解决的问题。

### Strong Skipping Mode（Kotlin 2.0 起默认启用）

Compose compiler 从 Kotlin 2.0 起默认启用 Strong Skipping Mode。这个变化直接改写了 Compose 性能优化的最佳实践。

**Strong Skipping 之前**：只有参数类型被标记为 `@Stable` 或 `@Immutable` 的 Composable 函数才会被跳过。Lambda 参数默认不被 memoize，每次父 Composable 重组时，lambda 参数都是新对象（引用不等），导致接收 lambda 的子 Composable 无法跳过。

**Strong Skipping 之后**：
- 所有 `@Composable` 函数都会被标记为 skippable，不再要求参数类型必须是 Stable。
- **所有 lambda 参数都会被自动 memoize**。Compose compiler 为每个 lambda 生成一个包装类，在参数列表的捕获值没变时复用同一个对象。

```kotlin
// Strong Skipping 之前：每次重组都创建新的 lambda → Clickable 无法跳过
@Composable
fun MyScreen(viewModel: ViewModel) {
    // onClick 是新 lambda，ButtonItem 每次都重组
    ButtonItem(onClick = { viewModel.doSomething() })
}

// Strong Skipping 之后：compiler 自动 memoize lambda → ButtonItem 可以跳过
// 不需要手动 remember { { viewModel.doSomething() } }
```

**代价**：自动 memoize 会增加 `remember` 缓存的内存占用。在 lambda 数量极多（数百个）的 Composable 树中，这部分开销需要关注。但对比减少的重组次数，绝大多数场景下是正收益。

**对已有代码的影响**：很多以前必须手写的 `remember { }` 包裹 lambda 的优化代码，现在可以删掉了。如果项目已经升级到 Kotlin 2.0+，手动 `remember` lambda 的代码不会出错，但属于冗余操作。

[适用版本: Kotlin 2.0+ (Compose Compiler 1.5+)]

### Stability 标记：什么时候还需要手动标注

Strong Skipping 减少了 `@Stable` / `@Immutable` 注解的使用频次，但它们在两个场景下仍然有意义：

**场景一：第三方 Composable 函数的跳过**。如果第三方库的 Composable 函数没有启用 Strong Skipping（较旧版本），它的跳过行为仍然依赖参数的 Stability。

**场景二：`mutableStateOf` 之外的自定义状态容器**。`mutableStateOf` 返回的 `MutableState<T>` 已经被 Compose runtime 标记为 `@Stable`。但如果自定义一个状态容器类，需要手动标注：

```kotlin
// 自定义状态容器：需要手动标注 @Stable
@Stable
class ScrollState(
    initialOffset: Float = 0f
) {
    var offset: Float by mutableStateOf(initialOffset)
        private set

    fun updateOffset(newOffset: Float) {
        offset = newOffset
    }
}
```

`@Stable` 的契约要求：
1. `equals()` 的结果在多次调用间必须稳定（同一个实例、同样的值，返回结果一致）。
2. 当属性变化时，Compose runtime 能收到通知（通过 `mutableStateOf` 或 `mutableStateListOf` 等机制）。
3. 所有公开属性的类型也是 Stable 的。

`@Immutable` 比 `@Stable` 更严格：要求类的所有属性在构造后不可变。用于 data class 或 val-only 的类，是一个编译器承诺而非运行时检查——标注了 `@Immutable` 但实际有可变字段，运行时不会报错，但可能导致应该跳过的重组没有跳过。



## 状态读取阶段：性能差距的分水岭

### Composition、Layout、Draw 三阶段的 State 读取

Compose 渲染管线的三个阶段各自有一个状态读取点。**一个 State 在哪个阶段被读取（调用 `.value`），决定了状态变化时会触发哪几个阶段的重新执行**。

| 读取阶段 | 触发范围 | 典型位置 |
|----------|---------|---------|
| Composition | 重组整个 Composable 函数 | Composable 函数体内直接使用 `state.value` 作为参数 |
| Layout | 只重新测量/布局，跳过 Composition | `Modifier.onSizeChanged { }`、`Modifier.layout { }` 内读取 |
| Draw | 只重绘，跳过 Composition 和 Layout | `Modifier.drawBehind { }`、`Modifier.graphicsLayer { }` 内读取 |

```kotlin
@Composable
fun AnimatedBox() {
    // 场景 A：Composition 阶段读取 → 每帧重组
    val color by animateColorAsState(Color.Red)
    Box(modifier = Modifier.background(color))
    // color 作为 Composable 参数传递，每帧触发 Composition

    // 场景 B：Draw 阶段读取 → 跳过 Composition 和 Layout
    val color2 by animateColorAsState(Color.Red)
    Box(modifier = Modifier.drawBehind {
        drawRect(color = color2)  // 只在 Draw scope 内解包
    })
    // 状态变化只触发 Draw，Composition 和 Layout 完全跳过
}
```

场景 B 的性能优势在动画场景下非常明显：一个 60fps 的颜色动画，如果走 Composition 阶段，每秒触发 60 次重组；如果走 Draw 阶段，每秒只触发 60 次绘制——绘制本身是 GPU 操作，比重新执行 Composable 函数函数体的 CPU 开销小一到两个数量级。

**实战判断规则**：
- 如果 State 变化只影响视觉效果（颜色、透明度、位移、缩放），用 `Modifier.graphicsLayer` 或 `Modifier.drawBehind` 在 Draw 阶段读取。
- 如果 State 变化影响布局尺寸或子元素数量，必须在 Composition 阶段读取，此时用 `derivedStateOf` 控制触发频率。

[已验证: 官方文档 Jetpack Compose Performance - Defer reads as long as possible]


### derivedStateOf 的使用条件和滥用陷阱

`derivedStateOf` 的作用是把高频变化的状态映射成低频变化的结果，从而减少重组次数。

**使用条件**（三个条件缺一不可）：
1. 输入状态变化频率高（如 `scrollState.value` 在滚动期间每帧都在变）。
2. 派生结果变化频率低（如 `scrollState.value > 100` 只在阈值处变化一次）。
3. 派生计算是纯函数——无副作用（不修改外部状态）、无内存分配（不在 lambda 内创建新对象）。`derivedStateOf` 的失效监听机制（`SnapshotStateObserver`）依赖计算的确定性，副作用或对象分配会导致监听判断失准，反而增加无效重组。

```kotlin
// 正确用法：滚动偏移量（高频变化）→ 是否超过阈值（低频变化）
@Composable
fun ScrollingList(scrollState: LazyListState) {
    val showButton by remember {
        derivedStateOf { scrollState.firstVisibleItemIndex > 5 }
    }
    if (showButton) {
        ScrollToTopButton()
    }
}

// 错误用法：输入和输出变化频率一样，derivedStateOf 白白增加开销
@Composable
fun BadUsage(scrollState: LazyListState) {
    // scrollState.value * 2 和 scrollState.value 一样每帧变化
    // derivedStateOf 的监听机制有额外开销，这里完全无收益
    val doubledOffset by remember {
        derivedStateOf { scrollState.firstVisibleItemScrollOffset * 2 }
    }
    Text("$doubledOffset")
}
```

`derivedStateOf` 内部维护了一套依赖监听机制，有对象创建和订阅成本。滥用 `derivedStateOf` 的典型模式：把所有 State 操作都包一层 `derivedStateOf`，以为能"自动优化"。实际效果是增加了 `SnapshotStateObserver` 的订阅数量，没有减少任何重组。

[已验证: AOSP Compose Runtime, DerivedState.kt]

### remember 和 key 的使用场景

**`remember`**：在 Composable 函数内缓存对象，避免每次重组都重新创建。最常用于缓存计算结果、Lambda 和状态容器。

```kotlin
@Composable
fun ExpensiveView(data: List<Item>) {
    // 重组时只在 data 变化时才重新排序
    val sortedData = remember(data) {
        data.sortedBy { it.timestamp }
    }
    LazyColumn {
        items(sortedData) { item -> ItemRow(item) }
    }
}
```

`remember` 的 key 参数：当 key 变化时，`remember` 会丢弃旧值并重新执行 lambda。不传 key 则只在首次组合时计算一次。

**`key`**：在 LazyColumn 等容器中为每个 item 提供稳定标识。Compose runtime 用 key 来追踪 Composable 实例在列表中的位置变化。

```kotlin
LazyColumn {
    items(
        count = list.size,
        key = { index -> list[index].stableId }  // 用业务 ID 做 key
    ) { index ->
        ItemRow(item = list[index])
    }
}
```

不用 `key` 或用 `index` 做 key 的后果：当列表发生插入/删除时，Compose 无法区分"位置 3 的 item 变了"和"item 移动了"，会导致比实际需要更多的重组。用 `index` 做 key 在列表有插入/删除时比不用还差——因为 Compose 会认为 key=3 的 item 内容变了（因为原来 key=3 的 item 被移走了，新 item 占了位置 3）。

[已验证: AOSP Compose Runtime, ComposeNode.kt, key 追踪逻辑]

## Pausable Composition 与 LazyColumn 预取

### Pausable Composition（Compose 1.10 默认启用）

Pausable Composition 是 Compose 1.10 引入的运行时改进，也是 Compose 达到 View 系统性能对等的关键机制。

**之前的行为**：Composition 必须在单个帧内完成。如果 Composable 树很深或 LazyColumn 的可见 item 很多，组合阶段的 CPU 时间可能超过 16.67ms 帧预算，直接导致掉帧。

**Pausable Composition 的行为**：Compose runtime 将组合工作切分成可暂停的块。在每一块执行完后，runtime 通过 `shouldPause` 回调检查帧截止时间（FrameData deadline）是否临近。如果临近，暂停组合，让主线程处理当前帧的绘制任务；下一帧继续剩余的组合工作。

```kotlin
// 内部控制流（简化）
// setPausableContent() → PausedComposition 对象
// resume() → 执行分块组合
//   内部通过 shouldPause lambda 检查帧 deadline
//   shouldPause == true → 暂停，主线程去绘制当前帧
// resume() 再次调用 → 继续下一块
// isComplete == true → apply() 提交所有变更到 UI 树
```

`apply()` 是 Pausable Composition 的提交阶段：只有当所有组合工作完成后，变更才会被提交到 UI 树。未完成的 UI 子树不会被渲染。

**对开发者的意义**：
1. 长列表滚动的卡顿率显著降低，不需要开发者做任何代码改动。
2. 以前为了规避组合阻塞而做的各种拆分优化（手动将大 Composable 拆成小函数），在 Compose 1.10 上的效果减弱了——runtime 层面已经做了时间切片。
3. 但 `derivedStateOf`、key、stable 参数等优化仍然有效——Pausable Composition 解决的是单帧阻塞问题，不解决不必要的重组问题。

[已验证: Compose 1.10 release notes, Pausable Composition 默认启用]
[已验证: Google 内部基准测试，长列表滚动卡顿率 0.2%]
[待验证: Pausable Composition 在 Perfetto 中的具体表现（被切分的 composition slice 形态）]

### LazyColumn 预取策略

LazyColumn / LazyRow 的预取系统与 Pausable Composition 深度集成：

1. 预取系统根据滚动速度预测即将进入可见区域的 item。
2. 在主线程空闲时，调用 `PausedComposition.resume()` 执行增量组合，提前完成即将可见的 item 的 Composition 阶段。
3. 预取工作也可以被暂停——如果帧 deadline 临近，预取让位给当前帧的绘制。

Compose 1.9 引入的 `LazyLayoutCacheWindow` API 允许开发者精确控制预取窗口大小：

```kotlin
LazyColumn(
    modifier = Modifier.lazyLayoutCacheWindow(
        // 预取可见区域前后各 3 个 item
        prefetchWindow = LazyLayoutCacheWindow(3)
    )
) {
    // ...
}
```

预取窗口大小需要根据 item 的组合复杂度调整：简单的列表项（纯文本）不需要预取太多；复杂的列表项（图片 + 多行文本 + 操作按钮）适当增大预取窗口可以减少首次可见时的组合卡顿。

[已验证: Compose 1.9 LazyLayoutCacheWindow API]

## Compose 编译器报告与性能诊断

### 编译器报告的生成与解读

Compose compiler 可以在编译时生成性能报告，帮助发现稳定性（Stability）和跳过（Skip）相关的问题。

在 Gradle 中启用：

```groovy
// build.gradle.kts
kotlinOptions {
    freeCompilerArgs += [
        "-P",
        "plugin:androidx.compose.compiler.plugins.kotlin:reportsDestination=" +
            project.buildDir.absolutePath + "/compose_metrics"
    ]
    freeCompilerArgs += [
        "-P",
        "plugin:androidx.compose.compiler.plugins.kotlin:metricsDestination=" +
            project.buildDir.absolutePath + "/compose_metrics"
    ]
}
```

编译后会在 `build/compose_metrics/` 下生成三个文件：

| 文件 | 内容 |
|------|------|
| `*_composables.txt` | 每个 @Composable 函数的分析结果：是否 restartable、是否 skippable、参数稳定性 |
| `*_classes.txt` | 类级别的稳定性推断结果 |
| `*_module.json` | 模块级别的组合指标（Kotlin 2.0+ 格式） |

关注 `*_composables.txt` 中的关键字段：

```
restartable     — 函数可以被独立重启（不在内联 Composable 内部）
skippable       — 函数可以被跳过（所有参数都是 Stable）
```

如果 `skippable = false`，说明有参数类型被推断为 Unstable。需要检查哪个参数导致了不稳定，然后决定是否标注 `@Stable` / `@Immutable`，或者升级到 Kotlin 2.2 利用 Strong Skipping 自动处理。

[待验证: Kotlin 2.2 Strong Skipping 下编译器报告的 skippable 字段是否全部为 true]

### Layout Inspector 和 Perfetto 中的 Compose 性能观测

**Layout Inspector（Android Studio）**：
- 显示 Composable 树的节点数量和每个节点的重组次数。
- 重组次数高的节点是优化目标。
- 支持 Live Edit 模式下实时查看重组情况。

**Perfetto**：
- Compose 的组合工作在主线程上表现为 `composition` 相关的 slice。
- Pausable Composition 可能表现为被切分的多个短 slice，中间穿插其他系统回调。
- LazyColumn 预取的组合工作也在主线程上，但会被 `shouldPause` 中断。
- 重组异常（如整个页面因一个按钮状态变化而重组）会在主线程上表现为超大的 `composition` slice，超过 16.67ms 即为掉帧。

**Perfetto SQL 查询示例**：

```sql
-- 查看主线程上 Compose 相关的耗时操作
SELECT slice.name, slice.dur / 1e6 as dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
WHERE thread.name = 'main'
  AND (slice.name LIKE '%composition%'
    OR slice.name LIKE '%layout%'
    OR slice.name LIKE '%Choreographer%')
  AND slice.dur > 8e6  -- 超过 8ms 的操作
ORDER BY slice.dur DESC
LIMIT 20;
```

[待验证: Pausable Composition slice 在 Perfetto 中的实际 name 模式]

## Compose 与 View 互操作的性能开销

### ComposeView 嵌入传统布局

在 RecyclerView 等 View 系统容器中嵌入 ComposeView 时，性能瓶颈不在 Compose 的组合阶段，而在 ComposeView 的生命周期管理。

`ViewCompositionStrategy` 决定了 ComposeView 内部的 Composition 何时被销毁和重建。默认策略 `DisposeOnDetachedFromWindowOrReleasedFromPool` 在 RecyclerView 的 item 被回收到缓存池时会销毁 Composition，下次该 item 重新可见时从头创建——这意味着完整的 Composition 开销。

```kotlin
// 推荐：在 RecyclerView ViewHolder 中使用
val composeView = ComposeView(context).apply {
    setViewCompositionStrategy(
        ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed
    )
    setContent {
        MyComposableItem(data)
    }
}
```

`DisposeOnViewTreeLifecycleDestroyed` 让 Composition 的生命周期绑定到 Activity/Fragment 的 Lifecycle，而不是 RecyclerView item 的 attach/detach。item 被 RecyclerView 回收时，Composition 只是 detach 但不销毁，重新绑定时恢复，避免重复创建。

### AndroidView 在 Compose 中嵌入 View

反过来，在 Compose 中嵌入传统 View 使用 `AndroidView`：

```kotlin
AndroidView(
    factory = { context ->
        // 只在首次创建时调用
        TextView(context)
    },
    update = { textView ->
        // 每次 Composable 重组时调用
        // 控制这里的操作粒度
        textView.text = data.title
    }
)
```

`update` lambda 在每次父 Composable 重组时都会执行。如果 `update` 里有耗时操作（如设置大图片、触发布局重算），会放大重组的性能影响。优化方式：把 `update` 里的操作限制在最小必要范围，耗时操作移到 `remember` 或 `LaunchedEffect` 中异步处理。

[已验证: 官方文档 ViewCompositionStrategy API]
[待验证: RecyclerView 中 DisposeOnViewTreeLifecycleDestroyed 的内存占用差异实测数据]

## 版本迁移与优化策略变化

从旧版本 Compose 升级到 Compose 1.10+（Kotlin 2.0+）时，性能优化策略的优先级发生了变化。以下是迁移检查要点：

| 变化项 | 旧版本做法 | Kotlin 2.0+ 做法 |
|--------|-----------|-----------------|
| Lambda memoize | 手动 `remember { { ... } }` 包裹 | Strong Skipping 自动 memoize，手动包裹变为冗余 |
| `@Stable` / `@Immutable` 标注 | 大量手动标注以保证跳过 | Strong Skipping 下大部分场景不再需要，仅第三方库和自定义状态容器仍需标注 |
| 长列表组合阻塞 | 手动拆分大 Composable 函数 | Pausable Composition 自动切分，但 `derivedStateOf` / key 优化仍有效 |
| 编译器报告 | 关注 `skippable` 字段 | Strong Skipping 下所有 Composable 默认 skippable，关注点转向重组次数和状态读取阶段 |

迁移步骤：
1. 升级 Kotlin 到 2.0+，确认 Compose compiler 插件版本匹配。
2. 运行编译器报告，检查 `skippable` 字段是否全部为 `true`。
3. 清理冗余的手动 `remember { { lambda } }` 包裹代码。
4. 在 Layout Inspector 中对比升级前后的重组次数，确认 Strong Skipping 生效。
5. 更新 CI 中的性能基准测试，建立新版本的基线数据。

## 实战检查清单

| 场景 | 检查项 | 工具 |
|------|--------|------|
| 列表滚动卡顿 | LazyColumn item 是否提供 stable key | 编译器报告 + Layout Inspector |
| 列表滚动卡顿 | 预取窗口是否匹配 item 复杂度 | Perfetto 主线程 slice |
| 动画掉帧 | 动画状态是否延迟到 Draw 阶段读取 | Layout Inspector 重组计数 |
| 全页重组 | `derivedStateOf` 是否只用于高频→低频映射 | 编译器报告 + 代码审查 |
| Compose-View 混合 | ComposeView 的 ViewCompositionStrategy 是否正确 | 代码审查 |
| Lambda 传递 | Kotlin 2.2 之前需要 remember 包裹 lambda | 编译器报告 skippable 字段 |

[自动发现]：Compose 1.9 引入的后台文本布局预热功能，可以在后台线程预先完成文本的布局计算，减少主线程 Text Composable 的组合耗时。对长列表中包含大量文本的场景有显著帮助，无需开发者额外配置。
