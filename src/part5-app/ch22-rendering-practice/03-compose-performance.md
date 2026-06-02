---
title: "Jetpack Compose 性能优化"
chapter: "22.3"
section: "22.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-02"
last_verified_against: "Compose BOM 2025.12.00, Kotlin 2.2"
confidence: high
drafted_date: "2026-05-12"
polish_count: 0
sources:
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/PausableComposition.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow.kt"
tags: [compose, recomposition, stability, derivedStateOf, pausable-composition, strong-skipping]
related_chapters: ["7.7", "2.4", "22.1"]
pipeline_stage: ready-to-publish
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
last_task6_at: "2026-06-02T13:05:00+08:00"
task9_state: reviewed
last_task2b_at: "2026-06-02T12:54:00+08:00"
last_task2b_lite_at: "2026-05-31T15:35:00+08:00"
task6_result: pass-light-edit
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-02"
last_task9_at: "2026-06-02T17:23:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-02-17-deep-review.md"
task9_review_notes: "2026-06-02 Task9 deep-review: pass-tech-review。复核 Strong Skipping、Pausable Composition、LazyLayoutCacheWindow 与 Android 17/Compose 工具链边界，无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task6_review_log: "logs/review/2026-06-02-13-review.md"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-02"
review_notes: "2026-06-02 13:05 Task6 复审：L1 小修 10 处；修正 AndroidX 源码锚点格式与中英文混排，未发现新增回炉项。"
task2b_notes: "2026-06-02 Task2B：删除发布正文中的调研补遗块，统一 Pausable Composition 为 Compose/Foundation 工具链能力，移出未闭合的 AOSP master/androidx-main 正文结论。"
last_task2b_verifier_at: "2026-05-31T23:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-05-31-23-task2b-verifier.md"
last_task9_autofix_at: "2026-06-01"
task9_p0_issues: 2
task9_p1_issues: 1
task9_p2_issues: 2
---
# Jetpack Compose 性能优化实战

Compose 渲染管线的原理和机制在 §7.7 已详细说明。本节聚焦工程实战：怎么写出不会卡顿的 Compose 代码，怎么用工具定位性能问题，以及 2025 年底 Compose 运行时的几个关键变化如何改变了优化策略的优先级。

本节使用 **Compose BOM 2025.12.00（对应 Compose 1.10）** 作为版本基线。Pausable Composition、Strong Skipping 和 LazyLayoutCacheWindow 都取决于项目引入的 Compose / Kotlin 版本，不由 Android 17（API 37）平台本身决定。没有公开测试条件的滚动性能数据不作为本文结论，只作为阅读官方演讲资料时的背景。

## 重组控制：从手动优化到编译器自动跳过

### Compose 重组的触发条件与成本

Compose 的渲染管线包含三个阶段：Composition → Layout → Draw。重组（Recomposition）就是重新执行 Composition 阶段：重新调用 `@Composable` 函数，根据新的状态值生成新的 UI 树。

重组的开销来自两个地方:

1. **被调用的 Composable 函数本身的执行时间**:函数里有复杂计算、对象分配或子树嵌套深,重组一次的 CPU 时间就高。
2. **下游传播**:一个 Composable 重组后,如果它的子 Composable 参数也变了,子 Composable 也会跟着重组。

控制重组的核心思路:**让状态变化只触发最小范围的 Composable 重新执行**。

Compose 运行时的跳过(skip)机制:如果一个 `@Composable` 函数的所有参数与上次调用相比都"相等"(通过 `equals()` 判断),运行时会跳过整个函数体的执行,直接复用上一次的结果。这就是 Stability 标记和 Strong Skipping Mode 要解决的问题。

### Strong Skipping Mode(Kotlin 2.0.20 起默认启用)

Compose compiler 从 **Kotlin 2.0.20** 起默认启用 Strong Skipping Mode。Kotlin 2.0.0-2.0.10 需要在 `build.gradle.kts` 中显式开启:

```kotlin
composeCompiler {
    enableStrongSkippingMode = true
}
```

这个变化会调整 Compose 性能优化的优先级。

**Strong Skipping 之前**:只有参数类型被标记为 `@Stable` 或 `@Immutable` 的 Composable 函数才会被跳过。Lambda 参数默认不被 memoize,每次父 Composable 重组时,lambda 参数都是新对象(引用不等),导致接收 lambda 的子 Composable 无法跳过。

**Strong Skipping 之后**:

- 所有 **restartable** Composable 函数都会被标记为 skippable,不再要求参数类型必须是 Stable。非 restartable 的 Composable(如内联函数体内的 Composable 调用)仍然不可跳过。
- 对于 unstable 参数,跳过比较使用实例相等(`===`);stable 参数使用 `equals()`。
- **所有 lambda 参数都会被自动 memoize**。Compose compiler 为每个 lambda 生成一个包装类,在参数列表的捕获值没变时复用同一个对象。

运行时执行跳过时，编译器生成的调用会走到 `Composer.skipToGroupEnd()`。这个判断还受 `Composer.skipping` 约束；如果 Composable 读取了 non-static `CompositionLocal`，参数相等也不一定能跳过函数体。工程排查时不要只看参数类型，还要看调用点是否引入了 CompositionLocal、状态读取和副作用。

```kotlin
// Strong Skipping 之前:每次重组都创建新的 lambda → Clickable 无法跳过
@Composable
fun MyScreen(viewModel: ViewModel) {
    // onClick 是新 lambda,ButtonItem 每次都重组
    ButtonItem(onClick = { viewModel.doSomething() })
}

// Strong Skipping 之后:compiler 自动 memoize lambda → ButtonItem 可以跳过
// 不需要手动 remember { { viewModel.doSomething() } }
```

**代价**:自动 memoize 会增加 `remember` 缓存的内存占用。在 lambda 数量极多(数百个)的 Composable 树中,这部分开销需要关注。但和减少的重组次数相比,绝大多数场景下是正收益。

**对已有代码的影响**:很多以前必须手写的 `remember { }` 包裹 lambda 的优化代码,现在可以删掉了。如果项目已经升级到 Kotlin 2.0+,手动 `remember` lambda 的代码不会出错,但属于冗余操作。

[适用版本: Kotlin 2.0.20+ 默认启用;Kotlin 2.0.0-2.0.10 需显式开启]

### 协程作用域与副作用管理:rememberCoroutineScope 和 produceState

Strong Skipping 解决了"什么时候可以跳过重组"，但没有解决"副作用应该在哪个作用域执行"。这两个 API 是 Compose 副作用管理的核心。

**`rememberCoroutineScope` 的重组安全性：**

```kotlin
@Composable
fun MyScreen() {
    val scope = rememberCoroutineScope()
    Button(onClick = {
        scope.launch { doSomething() }  // 在 Composition 外启动，不触发重组
    }) { Text("Click") }
}
```

`rememberCoroutineScope()` 返回的 `CoroutineScope` 通过 `remember` 机制缓存在 Composition 中。重组时返回同一实例，不会创建新协程体。协程作用域的生命周期与 Composition 实例绑定——Composable 离开重组树时，作用域被 cancel（由 Compose 的取消语义保证）。

**`produceState` 的协程生命周期：**

```kotlin
@Composable
fun userProfile(userId: String): State<User?> {
    return produceState<User?>(initialValue = null, userId) {
        value = fetchUser(userId)
    }
}
```

`produceState` 内部持有 `remember { mutableStateOf(initialValue) }`，并在 `LaunchedEffect` 中启动 producer。`userId` 这类被 producer 使用、且变化后必须重新拉取的数据要作为 key 传入；key 变化时旧协程被 cancel，新 producer 启动。只有要跟随调用点生命周期、输入变化不重启的场景，才使用 `Unit` 或 `true` 这类常量 key。

**性能边界：**
- `produceState` 每次 `value = newValue` 写入触发 Snapshot 事务，高频更新场景（如动画、传感器数据）可能造成性能压力。可考虑 `snapshotFlow` + `collectAsState` 代替直接写入。
- `rememberCoroutineScope` 在高频重组 Composable 中调用 `launch {}` 启动协程时，需确保旧协程被正确 cancel，否则可能积累大量并发协程。

**Strong Skipping 下的非 restartable Composable：**
- Strong Skipping 主要改变 restartable Composable 的 skippable 推断；non-restartable Composable 不会获得独立的重启边界，不应作为跳过优化目标。
- `@NonRestartableComposable` 和 `@NonSkippableComposable` 的含义不同：前者不提供重启边界，常见于副作用 API 内部；后者仍可 restartable，但强制每次父组分重组时执行函数体。
- `rememberCoroutineScope` 依赖 remember 机制，应放在可正常进入 Composition 的调用点，不要用它掩盖 Composable body 里的副作用
- 正确做法：使用 `LaunchedEffect` / `produceState` 管理副作用，而不是直接在 Composable body 执行副作用



**produceState 内部实现细节（源码级）：**

`produceState` 本质是 `LaunchedEffect` 的语法糖，源码位于 `platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ProduceState.kt`：

```kotlin
@Composable public fun <T> produceState<T>(
    initialValue: T,
    key1: Any?,
    producer: suspend ProduceStateScope<T>.() -> Unit,
): State<T> {
    val result = remember { mutableStateOf(initialValue) }
    LaunchedEffect(key1) { ProduceStateScopeImpl(result, coroutineContext).producer() }
    return result
}
```

**内存分配时机表：**

| 操作 | 分配对象 | 触发时机 |
|------|----------|----------|
| `remember { mutableStateOf }` | `SnapshotMutableStateImpl`（约 48-64B） | Composable 进入时 |
| `LaunchedEffect(key)` | `Job + Continuation` | Composable 进入时 |
| `ProduceStateScopeImpl(result, coroutineContext)` | 接口包装对象 | Composable 进入时 |
| `value = newValue` | **无堆分配**（in-place 写） | producer 执行时 |

`value` 写入触发 Snapshot 写事务链：`ProduceStateScope.value setter → Snapshot.registerMutableSnapshot → notifyReaders() → Recomposer.scheduleRevalidation() → 下帧重组评估`。producer 内每执行一次 `value = it` 就触发一次重组评估，因此 `produceState` **不适合驱动 UI 动画**（动画应使用 `animateFloatAsState` 等专用 API）。

### Stability 标记:什么时候还需要手动标注

Strong Skipping 减少了 `@Stable` / `@Immutable` 注解的使用频次,但它们在两个场景下仍然有意义:

**场景一:第三方 Composable 函数的跳过**。如果第三方库的 Composable 函数没有启用 Strong Skipping(较旧版本),它的跳过行为仍然依赖参数的 Stability。

**场景二:`mutableStateOf` 之外的自定义状态容器**。`mutableStateOf` 返回的 `MutableState<T>` 已经被 Compose 运行时标记为 `@Stable`。自定义状态容器类需要手动标注:

```kotlin
// 自定义状态容器:需要手动标注 @Stable
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

`@Stable` 的契约要求:
1. `equals()` 的结果在多次调用间必须稳定(同一个实例、同样的值,返回结果一致)。
2. 当属性变化时,Compose 运行时能收到通知(通过 `mutableStateOf` 或 `mutableStateListOf` 等机制)。
3. 所有公开属性的类型也是 Stable 的。

`@Immutable` 比 `@Stable` 更严格:要求类的所有属性在构造后不可变。用于 data class 或 val-only 的类,是一个编译器承诺而非运行时检查--错误标注 `@Immutable`(例如对实际包含可变字段的类加注解)会让 Compose 运行时误判参数未变,跳过本应执行的重组,导致 UI 不更新(stale UI)。这类问题难以排查,因为运行时不会报错,只是 UI 状态不再响应用户操作或数据变化。

反例:

```kotlin
// ❌ 错误:data class 有 var 字段,不应标注 @Immutable
@Immutable
data class UserProfile(
    val id: String,
    var displayName: String  // 可变字段违反 @Immutable 契约
)

// 当 displayName 变化时,Compose 可能跳过重组,UI 不会更新
```

## 状态读取阶段:性能差异的来源

### Composition、Layout、Draw 三阶段的状态读取

Compose 渲染管线的三个阶段各自有一个状态读取点。**一个状态值在哪个阶段被读取(调用 `.value`),决定了状态变化时会触发哪几个阶段的重新执行**。

| 读取阶段 | 触发范围 | 典型位置 |
|----------|---------|---------|
| Composition | 重组整个 Composable 函数 | Composable 函数体内直接使用 `state.value` 作为参数 |
| Layout | 只重新测量/布局,跳过 Composition | `Modifier.onSizeChanged { }`、`Modifier.layout { }` 内读取 |
| Draw | 只重绘,跳过 Composition 和 Layout | `Modifier.drawBehind { }`、`Modifier.graphicsLayer { }` 内读取 |

```kotlin
@Composable
fun AnimatedBox() {
    // 场景 A:Composition 阶段读取 → 每帧重组
    val color by animateColorAsState(Color.Red)
    Box(modifier = Modifier.background(color))
    // color 作为 Composable 参数传递,每帧触发 Composition

    // 场景 B:Draw 阶段读取 → 跳过 Composition 和 Layout
    val color2 by animateColorAsState(Color.Red)
    Box(modifier = Modifier.drawBehind {
        drawRect(color = color2)  // 只在 Draw scope 内解包
    })
    // 状态变化只触发 Draw,Composition 和 Layout 完全跳过
}
```

场景 B 的差别主要体现在 CPU 侧工作量:一个 60fps 的颜色动画,如果走 Composition 阶段,每秒触发 60 次重组;如果走 Draw 阶段,每秒只触发 60 次绘制,避免反复执行 Composable 函数体。

**实战判断规则**:
- 如果状态变化只影响视觉效果(颜色、透明度、位移、缩放),用 `Modifier.graphicsLayer` 或 `Modifier.drawBehind` 在 Draw 阶段读取。
- 如果状态变化影响布局尺寸或子元素数量,必须在 Composition 阶段读取,此时用 `derivedStateOf` 控制触发频率。

[已验证: 官方文档 Jetpack Compose Performance - Defer reads as long as possible]


### derivedStateOf 的使用条件和滥用陷阱

`derivedStateOf` 的作用是把高频变化的状态映射成低频变化的结果,从而减少重组次数。

**使用条件**(三个条件缺一不可):
1. 输入状态变化频率高(如 `scrollState.value` 在滚动期间每帧都在变)。
2. 派生结果变化频率低(如 `scrollState.value > 100` 只在阈值处变化一次)。
3. 派生计算是纯函数--无副作用(不修改外部状态)，并尽量避免在 lambda 内创建新对象。`derivedStateOf` 只在结果变化频率低于输入变化频率时有收益；对象分配不会让依赖监听失准，但会增加派生计算本身的成本。

```kotlin
// 正确用法:滚动偏移量(高频变化)→ 是否超过阈值(低频变化)
@Composable
fun ScrollingList(scrollState: LazyListState) {
    val showButton by remember {
        derivedStateOf { scrollState.firstVisibleItemIndex > 5 }
    }
    if (showButton) {
        ScrollToTopButton()
    }
}

// 错误用法:输入和输出变化频率一样,derivedStateOf 白白增加开销
@Composable
fun BadUsage(scrollState: LazyListState) {
    // scrollState.value * 2 和 scrollState.value 一样每帧变化
    // derivedStateOf 的监听机制有额外开销,这里完全无收益
    val doubledOffset by remember {
        derivedStateOf { scrollState.firstVisibleItemScrollOffset * 2 }
    }
    Text("$doubledOffset")
}
```

`derivedStateOf` 内部维护了一套依赖监听机制,有对象创建和订阅成本。滥用 `derivedStateOf` 的典型模式:把所有状态操作都包一层 `derivedStateOf`,以为能"自动优化"。实际效果是增加 `SnapshotStateObserver` 的订阅数量,却没有减少重组。

[已验证: AndroidX androidx-compose-release, platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt]

### remember 和 key 的使用场景

**`remember`**:在 Composable 函数内缓存对象,避免每次重组都重新创建。最常用于缓存计算结果、Lambda 和状态容器。

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

`remember` 的 key 参数:当 key 变化时,`remember` 会丢弃旧值并重新执行 lambda。不传 key 则只在首次组合时计算一次。

**`key`**:在 LazyColumn 等容器中为每个 item 提供稳定标识。Compose 运行时用 key 来追踪 Composable 实例在列表中的位置变化。

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

不用 `key` 或用 `index` 做 key 的后果:当列表发生插入/删除时,Compose 无法区分"位置 3 的 item 变了"和"item 移动了",会导致比实际需要更多的重组。用 `index` 做 key 在列表有插入/删除时比不用还差--因为 Compose 会认为 key=3 的 item 内容变了(因为原来 key=3 的 item 被移走了,新 item 占了位置 3)。

[已验证: AOSP Compose Runtime, ComposeNode.kt, key 追踪逻辑]

## Pausable Composition 与 LazyColumn 预取

### Pausable Composition(Compose 1.10+)

Pausable Composition 是 Compose 1.10 引入的运行时改进。它主要作用在 LazyColumn/LazyRow 的预取路径中--运行时可将预取 item 的组合工作切分成可暂停的块,在帧预算不足时暂停并在下一帧继续。

**版本注意**:Pausable Composition 无 Android 平台版本门槛,只要 Compose Foundation 版本支持即可。Compose Foundation 1.10.0-alpha05 曾默认启用(通过 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled`),但 1.10.6 因稳定性问题已将其默认禁用。当前是否默认启用取决于具体 Foundation 版本,使用前要检查目标版本的默认值或手动设置 flag。对于首帧 Composition 和普通(非 Lazy)Composable,Pausable Composition 不适用--这些场景仍然在单帧内同步完成。

**之前的行为**:Composition 必须在单个帧内完成。如果 Composable 树很深或 LazyColumn 的可见 item 很多,组合阶段的 CPU 时间可能超过 16.67ms 帧预算,直接导致掉帧。

**Pausable Composition 的行为**:Compose 运行时将组合工作切分成可暂停的块。在每一块执行完后,运行时通过 `shouldPause` 回调检查帧截止时间(FrameData deadline)是否临近。如果临近,暂停组合,让主线程处理当前帧的绘制任务;下一帧继续剩余的组合工作。

```kotlin
// 内部控制流(简化)
// setPausableContent() → PausedComposition 对象
// resume() → 执行分块组合
//   内部通过 shouldPause lambda 检查帧 deadline
//   shouldPause == true → 暂停,主线程去绘制当前帧
// resume() 再次调用 → 继续下一块
// isComplete == true → apply() 提交所有变更到 UI 树
```

`apply()` 是 Pausable Composition 的提交阶段:只有当所有组合工作完成后,变更才会被提交到 UI 树。未完成的 UI 子树不会被渲染。

运行时接口的形态可以压缩成三个动作：`resume(shouldPause)` 继续执行预组合，`shouldPause` 在帧截止时间临近时返回暂停信号，`apply()` 在组合完成后一次性提交结果。开发者通常不会直接调用这些内部接口，能控制的是 Foundation 版本、预取窗口和列表 item 的组合成本。

**对开发者的意义**:
1. 在已启用的 LazyColumn/LazyRow 预取路径中,Pausable Composition 可以减少预取组合阻塞当前帧的概率;是否生效取决于具体 Foundation 版本和 flag 状态。
2. 以前为了规避组合阻塞而做的各种拆分优化(手动将大 Composable 拆成小函数),在 Compose 1.10 上的效果减弱了--运行时层面已经做了时间切片。
3. 但 `derivedStateOf`、key、stable 参数等优化仍然有效--Pausable Composition 解决的是单帧阻塞问题,不解决不必要的重组问题。

没有设备、场景、Foundation 版本和采样方式的滚动性能数字，不能直接迁移为项目基线。项目内验证时，用 Perfetto 对比主线程 `composition` slice 的耗时分布，再结合 Layout Inspector 的重组次数判断是否真的减少了当前帧阻塞。

### LazyColumn 预取策略

LazyColumn / LazyRow 的预取系统与 Pausable Composition 深度集成:

1. 预取系统根据滚动速度预测即将进入可见区域的 item。
2. 在主线程空闲时,调用 `PausedComposition.resume()` 执行增量组合,提前完成即将可见的 item 的 Composition 阶段。
3. 预取工作也可以被暂停--如果帧 deadline 临近,预取让位给当前帧的绘制。

Compose 1.9 引入的 `LazyLayoutCacheWindow` API 允许开发者精确控制预取窗口大小:

```kotlin
@OptIn(ExperimentalFoundationApi::class)
val listState = rememberLazyListState(
    // cacheWindow 定义预取窗口范围,单位为 viewport 外的 Dp 距离
    cacheWindow = LazyLayoutCacheWindow(ahead = 150.dp, behind = 100.dp)
    // 或使用 viewport fraction:
    // cacheWindow = LazyLayoutCacheWindow(aheadFraction = 1f, behindFraction = 0.5f)
)

LazyColumn(state = listState) {
    // ...
}
```

预取窗口大小需要根据 item 的组合复杂度调整:简单的列表项(纯文本)不需要预取太多;复杂的列表项(图片 + 多行文本 + 操作按钮)适当增大预取窗口可以减少首次可见时的组合卡顿。`LazyLayoutCacheWindow` 的构造参数随 Foundation 版本演进，接入时以项目锁定版本的 IDE 签名和 release notes 为准。

## Compose 编译器报告与性能诊断

### 编译器报告的生成与解读

Compose compiler 可以在编译时生成性能报告,帮助发现稳定性(Stability)和跳过(Skip)相关的问题。

在 Gradle 中启用:

```kotlin
// Kotlin 2.0+ build.gradle.kts(推荐)
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_metrics")
    metricsDestination = layout.buildDirectory.dir("compose_metrics")
}

// Kotlin 2.0 之前(兼容写法)
// kotlinOptions {
//     freeCompilerArgs += listOf(
//         "-P", "plugin:androidx.compose.compiler.plugins.kotlin:reportsDestination=${project.buildDir.absolutePath}/compose_metrics",
//         "-P", "plugin:androidx.compose.compiler.plugins.kotlin:metricsDestination=${project.buildDir.absolutePath}/compose_metrics"
//     )
// }
```

编译后会在 `build/compose_metrics/` 下生成三个文件:

| 文件 | 内容 |
|------|------|
| `*_composables.txt` | 每个 @Composable 函数的分析结果:是否 restartable、是否 skippable、参数稳定性 |
| `*_classes.txt` | 类级别的稳定性推断结果 |
| `*_module.json` | 模块级别的组合指标(Kotlin 2.0+ 格式) |

关注 `*_composables.txt` 中的这两个字段:

```text
restartable     - 函数可以被独立重启(不在内联 Composable 内部)
skippable       - 函数可以被跳过(所有参数都是 Stable)
```

如果 `skippable = false`,说明有参数类型被推断为 Unstable。需要检查哪个参数导致了不稳定,然后决定是否标注 `@Stable` / `@Immutable`,或确认项目已使用 Kotlin 2.0+ 以利用 Strong Skipping 自动处理。Kotlin 2.0+ 的报告格式和旧 Compose Compiler 插件不同，脚本解析报告时要按项目实际插件版本适配字段。

### Layout Inspector 和 Perfetto 中的 Compose 性能观测

**Layout Inspector(Android Studio)**:
- 显示 Composable 树的节点数量和每个节点的重组次数。
- 重组次数高的节点是优化目标。
- 支持 Live Edit 模式下实时查看重组情况。

**Compose Profiler(Android Studio Ladybug 2024.2.1+ Feature Drop)**:
- Android Studio 的 Profiler 工具窗口中新增 Compose 专项性能分析视图。
- 入口:View → Tool Windows → Profiler,选择目标进程后,在 CPU 时间线视图中查看 Compose activity。
- 显示每个 Composable 函数的重组次数、跳过次数和耗时,按重组频率排序后高亮不必要的重组。
- 使用边界:需要连接真机或模拟器运行 Debug 构建体;Compose Profiler 依赖运行时注入的重组追踪代码,Release 构建体不包含追踪钩子,无法使用。

**Perfetto**:
- Compose 的组合工作在主线程上表现为 `composition` 相关的 slice。
- Pausable Composition 可能表现为被切分的多个短 slice,中间穿插其他系统回调。
- LazyColumn 预取的组合工作也在主线程上,但会被 `shouldPause` 中断。
- 重组异常(如整个页面因一个按钮状态变化而重组)会在主线程上表现为超大的 `composition` slice,超过 16.67ms 即为掉帧。

**Perfetto SQL 查询示例**:

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

这个查询用于定位主线程上 Compose 相关的性能瓶颈，先看超过 8ms 的 `composition`、`layout` 和 `Choreographer` slice。

## Compose 与 View 互操作的性能开销

### ComposeView 嵌入传统布局

在 RecyclerView 等 View 系统容器中嵌入 ComposeView 时,性能瓶颈不在 Compose 的组合阶段,而在 ComposeView 的生命周期管理。

**Composition 与 Recomposer 的共享关系**:每个 ComposeView 拥有自己的 Composition,但通常共享父级或窗口级 `Recomposer`--而不是每个 ComposeView 持有独立渲染上下文和独立 WindowRecomposer。`AbstractComposeView.resolveParentCompositionContext()` 实际优化了 Recomposer 的查找逻辑,优先复用父级已存在的 CompositionContext。

`ViewCompositionStrategy` 决定了 ComposeView 内部的 Composition 何时被销毁和重建。

**默认策略 `DisposeOnDetachedFromWindowOrReleasedFromPool`** 是为 RecyclerView 等 pooling container 设计的。当 ComposeView 从窗口 detach 或从缓存池中被丢弃时,Composition 被正确处理。注意"ReleasedFromPool"指的是缓存池满时丢弃最旧的 ViewHolder,而不是每次 item 滚出屏幕就销毁--item 被 RecyclerView 临时回收进缓存池时,Composition 保持存活。

```kotlin
// RecyclerView ViewHolder 中使用--默认策略已适配 pooling container
val composeView = ComposeView(context).apply {
    // 无需手动 setViewCompositionStrategy,默认策略即为 pooling container 设计
    setContent {
        MyComposableItem(data)
    }
}
```

**`DisposeOnViewTreeLifecycleDestroyed`** 适用于 Fragment View 场景:Composition 的生命周期绑定到 Activity/Fragment 的 LifecycleOwner,而不是 View 自身的 attach/detach。在 Fragment View 因配置变更被销毁但 Fragment 仍存活时,这个策略能确保 Composition 在正确的时机被清理。把这个策略用在 RecyclerView ViewHolder 上会把 Composition 生命周期绑定到 Activity/Fragment,导致 Composition 在整个 Activity 生命周期内不被释放,增加内存压力。

```kotlin
// Fragment 中嵌入 ComposeView 时适用
val composeView = ComposeView(context).apply {
    setViewCompositionStrategy(
        ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed
    )
    setContent {
        MyComposableContent()
    }
}
```

如果需要在 ViewHolder 不再复用或确认存在内存泄漏时重置 Compose 状态,可以调用 `disposeComposition()` 手动销毁,但要承担重建 Composition 的完整开销。优先依赖默认 `DisposeOnDetachedFromWindowOrReleasedFromPool` 策略,让 Composition 随缓存池生命周期自然释放,不要在 `onViewRecycled()` 中盲目调用 `disposeComposition()`--回收进缓存池的 ViewHolder 还有可能被复用,提前销毁只会增加重建成本。实际项目要用滚动场景的重建次数和内存曲线验证策略选择，不要只看单个 ViewHolder 的生命周期回调。

### AndroidView 在 Compose 中嵌入 View

反过来,在 Compose 中嵌入传统 View 使用 `AndroidView`:

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

`update` lambda 在每次父 Composable 重组时都会执行。如果 `update` 里有耗时操作(如设置大图片、触发布局重算),会放大重组的性能影响。优化方式:把 `update` 里的操作限制在最小必要范围,耗时操作移到 `remember` 或 `LaunchedEffect` 中异步处理。

[已验证: 官方文档 ViewCompositionStrategy API]

## 版本迁移与优化策略变化

从旧版本 Compose 升级到 Compose 1.10+（Kotlin 2.0+）时，性能优化策略的优先级发生了变化。以下是迁移检查要点：

| 变化项 | 旧版本做法 | Kotlin 2.0+ 做法 |
|--------|-----------|-----------------|
| Lambda memoize | 手动 `remember { { ... } }` 包裹 | Kotlin 2.0.20+ Strong Skipping 自动 memoize,手动包裹变为冗余 |
| `@Stable` / `@Immutable` 标注 | 大量手动标注以保证跳过 | Strong Skipping 下大部分场景不再需要,仅第三方库和自定义状态容器仍需标注 |
| 长列表组合阻塞 | 手动拆分大 Composable 函数 | Pausable Composition 自动切分，但是否默认启用取决于 Foundation 版本；`derivedStateOf` / key 优化仍有效 |
| 编译器报告 | 关注 `skippable` 字段 | Strong Skipping 下所有 restartable Composable 默认 skippable,关注点转向重组次数和状态读取阶段 |

迁移步骤:
1. 升级 Kotlin 到 2.0.20+(或 2.0.0-2.0.10 显式开启 `enableStrongSkippingMode`),确认 Compose compiler 插件版本匹配。
2. 运行编译器报告,检查 `skippable` 字段是否全部为 `true`。
3. 清理冗余的手动 `remember { { lambda } }` 包裹代码。
4. 在 Layout Inspector 中对比升级前后的重组次数,确认 Strong Skipping 生效。
5. 重新采集 Baseline Profile，覆盖冷启动、首屏列表和主要交互路径。
6. 更新 CI 中的性能基准测试,建立新版本的基线数据。

## 实战检查清单

| 场景 | 检查项 | 工具 |
|------|--------|------|
| 列表滚动卡顿 | LazyColumn item 是否提供 stable key | 编译器报告 + Layout Inspector |
| 列表滚动卡顿 | 预取窗口是否匹配 item 复杂度 | Perfetto 主线程 slice |
| 动画掉帧 | 动画状态是否延迟到 Draw 阶段读取 | Layout Inspector 重组计数 |
| 全页重组 | `derivedStateOf` 是否只用于高频→低频映射 | 编译器报告 + 代码审查 |
| Compose-View 混合 | ComposeView 的 ViewCompositionStrategy 是否正确 | 代码审查 |
| Lambda 传递 | Kotlin 2.0 之前需要手动 remember 包裹 lambda;2.0+ Strong Skipping 自动 memoize | 编译器报告 skippable 字段 |
| 冷启动偏慢 | Baseline Profile 是否覆盖 Compose 首屏路径 | Macrobenchmark + ProfileInstaller 状态 |

Android 17（API 37）上的 ART 分代 GC 会改善短生命周期对象回收成本，但 Compose 性能优化的优先级仍然是减少不必要重组、延迟状态读取和控制列表预取成本。GC 调参不能替代 Composition 层面的代码优化。


## 版本边界

Android 17（API 37）平台不内置 Compose 工具链，也不决定 Strong Skipping、Pausable Composition 或 LazyLayoutCacheWindow 的启用状态。应用侧是否获得这些优化，取决于项目锁定的 Kotlin、Compose Compiler、Compose Runtime 和 Compose Foundation 版本。

本文没有把仅来自 AOSP master 或 AndroidX androidx-main、且未进入 Android 17 的源码锚点作为 Android 17 正文结论。只能证明属于 Android 17/API 37 或项目依赖版本的资料，才用于正文判断；其余资料保留为后续复核线索。

## 参考资料

- DeepResearch: `2026-05-30-android-17-pausable-composition-compose-toolchain.md`。用于确认 Pausable Composition、LazyLayoutCacheWindow 与 Android 平台版本的边界。
- DeepResearch: `2026-05-31-android-compose-baseline-profile-integration.md`。用于补充 Baseline Profile、ProfileInstaller 写入链路和 Compose 库内置 profile 的迁移检查项。
- DeepResearch: `2026-05-27-android-17-art-generational-gc-compose-composition.md`。用于说明 Android 17 ART 分代 GC 与 Compose 短生命周期对象的关系；正文只保留优化优先级判断，不引用未闭合的源码行号。
