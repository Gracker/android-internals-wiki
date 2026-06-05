---
title: "Jetpack Compose 性能优化盲区：rememberCoroutineScope、produceState 与 Strong Skipping"
chapter: "22.20"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-05"
last_verified_against: "Compose BOM 2025.12.00, Kotlin 2.2, Compose Runtime 1.10"
confidence: medium-high
drafted_date: "2026-06-05"
tags: [compose, coroutine, strong-skipping, performance, recomposition, memory]
related_chapters: ["22.3", "7.7", "2.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "素材驱动"
sources:
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ProduceState.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Remember.kt"
  - type: research
    path: "intake/research-feeds/2026-04-01-12-compose-performance-milestone-2025.md"
  - type: research
    path: "intake/research-feeds/2026-04-10-07-compose-pausable-composition-choreographer-deadline.md"
---

# 22.20 Jetpack Compose 性能优化盲区：rememberCoroutineScope、produceState 与 Strong Skipping

Compose 重组控制的基础机制（Stability 推断、Strong Skipping Mode、derivedStateOf）在 §22.3 已详细说明。本节聚焦三个容易在工程中被误用的 API：`rememberCoroutineScope`、`produceState`，以及它们与 Strong Skipping 的交互。这些 API 的行为受 Compose Runtime 版本约束（不由 Android 平台版本决定），版本升级后可能出现静默性能退化。

本节使用 **Compose BOM 2025.12.00（Compose 1.10）** 作为版本基线。Strong Skipping Mode 在 Kotlin 2.0.20 起默认启用（详见 §22.3），但 `rememberCoroutineScope` 和 `produceState` 的协程生命周期管理与编译器 skipping 行为是两套独立机制，本节拆开讲。

## rememberCoroutineScope 的生命周期与泄漏边界

`rememberCoroutineScope` 返回一个绑定当前 Composition 生命周期的 `CoroutineScope`。Composition 离开树时，scope 被取消。

### 作用域绑定与取消时序

`rememberCoroutineScope` 内部通过 `remember` + `ReusableComposition` 的 `RememberObserver` 回调管理 scope 的创建和取消。当 Composable 离开 Composition：

1. `onRemembered` 的逆操作触发 → scope 的 `SupervisorJob` 被 cancel
2. scope 内所有子协程收到 `CancellationException`
3. 协程的 `finally` 块执行

这个取消是异步的——`onForgotten` 回调在 Composition 完成移除后才触发，协程的取消信号不会阻塞帧的渲染。如果在协程的 `finally` 块里做了重计算，这个开销会出现在下一帧。

### 常见泄漏模式

`rememberCoroutineScope` 本身不会泄漏——scope 随 Composition 取消。泄漏发生在协程内部持有的外部引用上：

```kotlin
// 泄漏：协程持有 ViewModel 引用，Composable 已移除但协程还在执行
@Composable
fun LeakExample(viewModel: MyViewModel) {
    val scope = rememberCoroutineScope()
    // Composable 进入时启动
    LaunchedEffect(Unit) {
        scope.launch {
            // viewModel 实例的生命周期 > Composition
            // 如果协程是长时间运行（如 while(true) 轮询），
            // viewModel 被 scope 的 job 间接持有
            viewModel.pollData() // Composable 移除后，scope cancel → 协程 cancel → 无泄漏
        }
    }
    
    // 但如果协程捕获了非 Compose 管理的资源：
    DisposableEffect(Unit) {
        val bitmap = decodeLargeBitmap() // 非 Compose 管理的资源
        scope.launch {
            processBitmap(bitmap) // 协程持有 bitmap 引用
        }
        onDispose {
            // scope cancel 会取消协程，但 bitmap 的释放取决于协程是否还在使用
            // 如果 processBitmap 是挂起函数且协程被 cancel 时恰好在 await，
            // bitmap 引用在 finally 之前不会被释放
        }
    }
}
```

**Perfetto 观察方式**：协程泄漏在 Perfetto 中表现为 `kotlinx.coroutines` 线程池中活跃协程数持续增长。用 `DebugProbes`（kotlinx-coroutines-debug）注入后，可以在 trace 中看到 `CoroutineTracker` slice 的数量。如果在离开 Composable 页面后协程数没有下降，排查 `rememberCoroutineScope` 启动的协程是否持有外部引用。

### 与 LaunchedEffect 的选择

| 维度 | `LaunchedEffect` | `rememberCoroutineScope` |
|------|------------------|--------------------------|
| 生命周期 | Composition 进入/退出 + key 变化时自动重启 | Composition 退出时取消 |
| 触发时机 | Composable 进入 Composition 时自动执行 | 需要手动 `scope.launch` |
| Key 感知 | key 变化 → 取消旧协程 + 启动新协程 | 无 key 机制 |
| 典型场景 | 事件驱动的副作用（网络请求、动画） | 用户交互触发的异步操作（点击、滚动） |

选择原则：需要随参数变化自动重启用 `LaunchedEffect`；用户交互触发的、不依赖 Composition 参数的操作用 `rememberCoroutineScope`。

## produceState 的数据流与 recomposition 开销

`produceState` 将非 Compose 数据源（Flow、LiveData、callback）转换为 `State<T>`，让 Composable 可以通过 `value` 属性读取。它的内部实现是一个绑定 Composition 生命周期的协程。

### 内部机制

```kotlin
// produceState 的简化签名
@Composable
fun <T> produceState(
    initialValue: T,
    key1: Any?, // key 变化时 producer 重启
    producer: suspend ProduceStateScope<T>.() -> Unit
): State<T>
```

`ProduceStateScope` 继承自 `MutableState<T>` 和 `CoroutineScope`。producer 协程在 Composition 进入时启动，退出时取消。`awaitDispose` 是一个挂起函数，协程在这行暂停直到 Composition 退出。

```kotlin
@Composable
fun <T> observeFlow(flow: Flow<T>): State<T?> {
    return produceState<T?>(initialValue = null) {
        flow.collect { value = it }
        // collect 是挂起函数，协程在这里持续运行
        // 如果 Flow 是 cold flow，collect 不会返回
        // awaitDispose 在 collect 下方，永远不会执行
    }
}
```

这个写法有两个问题：

1. **`awaitDispose` 不可达**：如果 `collect` 是无限流（如 `callbackFlow`、`channelFlow`），`awaitDispose` 永远不会执行，资源清理逻辑无法运行
2. **Key 未指定时每次 recomposition 都不会重启 producer**——但如果上游 Flow 的创建依赖 Composable 参数，参数变化后 producer 读取的是旧参数

### 正确用法：指定 key + awaitDispose

```kotlin
@Composable
fun <T> observeFlow(flow: Flow<T>): State<T?> {
    return produceState<T?>(initialValue = null, key1 = flow) {
        // flow 作为 key：flow 实例变化时 producer 重启
        flow.collect { value = it }
        awaitDispose { /* 清理逻辑 */ }
    }
}
```

或者用 `launchIn` + `awaitDispose` 分离收集和清理：

```kotlin
@Composable
fun observeLocation(provider: LocationProvider): State<Location?> {
    return produceState<Location?>(initialValue = null, key1 = provider) {
        provider.locationFlow()
            .onEach { value = it }
            .launchIn(this)
        awaitDispose { /* provider 的资源释放 */ }
    }
}
```

### 与 collectAsState 的性能对比

| 维度 | `produceState` | `collectAsState` |
|------|----------------|------------------|
| 适用场景 | 需要自定义 producer 逻辑（多源合并、条件过滤） | 直接收集 Flow 到 State |
| Key 重启 | 显式 key 参数控制 | Flow 实例变化自动重启 |
| 资源清理 | `awaitDispose` 手动管理 | 自动（协程随 Composition 取消） |
| 内存开销 | `ProduceStateScope` 额外分配 | 更轻量，只有 State + Job |

选择原则：单 Flow → State 的场景优先 `collectAsState`（或 `collectAsStateWithLifecycle`）；需要合并多个数据源或执行初始化逻辑时用 `produceState`。

## Strong Skipping 与稳定性推断对协程 API 的影响

Strong Skipping Mode 的行为在 §22.3 有完整说明。这里只讨论它对 `rememberCoroutineScope` 和 `produceState` 的具体影响。

### Strong Skipping 开启后 rememberCoroutineScope 的变化

Strong Skipping Mode 开启后，编译器对所有 `@Composable` 函数启用 skipping，包括那些接收 `CoroutineScope` 参数的函数。

```kotlin
// Strong Skipping 前：每次父 Composable 重组，lambda 参数是新对象 → 子 Composable 不跳过
@Composable
fun Parent(viewModel: MyViewModel) {
    val scope = rememberCoroutineScope()
    // scope 每次重组都是同一个对象（remember 缓存）
    // 但 onClick lambda 每次都是新对象
    Child(onClick = { scope.launch { viewModel.doWork() } })
}

// Strong Skipping 后：lambda 被 compiler 自动 memoize
// onClick 参数的引用稳定性由 compiler 保证 → Child 可以跳过
```

**注意**：`rememberCoroutineScope` 返回的 scope 对象在 Composition 生命周期内是稳定的（同一个引用）。Strong Skipping 不改变 scope 本身的行为，但改变了**接收 scope 相关 lambda 的子 Composable 的 skipping 行为**。

### @Stable 注解误用对 produceState 的影响

`produceState` 返回的 `State<T>` 对象在 Composition 生命周期内是稳定的。但如果 `T` 是可变类型且被标记为 `@Stable`，Compose runtime 会基于错误的稳定性推断做出错误的 skipping 决策：

```kotlin
// 错误：MutableUiState 是可变类，不应标记 @Stable
@Stable
data class MutableUiState(var isLoading: Boolean, var data: List<Item>)

@Composable
fun MyScreen(): State<MutableUiState> {
    return produceState(MutableUiState(false, emptyList())) {
        // 每次 value = newState 都会触发 recomposition
        // 但因为 MutableUiState 标记了 @Stable，
        // 下游 Composable 可能错误地跳过重组
        // 导致 UI 显示旧数据
    }
}
```

判断标准：如果 `equals()` 不能准确反映"内容是否变化"，就不要标记 `@Stable`。`data class` 的 `equals()` 基于所有属性值，如果属性是 `var` 且被外部修改，`equals()` 可能返回 `true`（因为引用没变）但内容已变。

## rememberCoroutineScope + produceState 的组合陷阱

### 作用域叠加与取消时序

在 `produceState` 内部使用 `rememberCoroutineScope` 获取的 scope 会导致双重作用域叠加：

```kotlin
@Composable
fun BuggyExample(repository: Repository): State<Data> {
    val outerScope = rememberCoroutineScope() // 绑定 Composition 生命周期
    return produceState(Data.Empty, repository) {
        // produceState 自身的 CoroutineScope 绑定 Composition 生命周期
        // outerScope 和 producer scope 是两个独立的 scope
        
        // 如果在 producer 里用 outerScope 启动子协程：
        outerScope.launch {
            // 这个协程的生命周期由 outerScope 控制
            // produceState 的 producer 取消时，这个协程不会自动取消
            // 只有 Composition 退出时才取消
        }
        
        // 正确做法：直接在 producer scope 里启动
        launch {
            // 这个协程跟随 producer 的生命周期
            // producer 取消 → 协程取消
        }
    }
}
```

`produceState` 的 producer 在 key 变化时会重启（取消旧的 → 启动新的）。如果在 producer 内用 `rememberCoroutineScope` 的 scope 启动协程，这些协程不受 producer 重启影响，可能读取过期数据。

### 多个 produceState 的数据竞争

```kotlin
@Composable
fun MultiSourceScreen(viewModel: ViewModel) {
    val sourceA by produceState(Result.Loading, viewModel) {
        value = viewModel.fetchA()
    }
    val sourceB by produceState(Result.Loading, viewModel) {
        value = viewModel.fetchB()
    }
    
    // 两个 producer 独立运行，完成顺序不确定
    // 如果 UI 需要两个结果都完成后才渲染：
    if (sourceA is Result.Success && sourceB is Result.Success) {
        // 在两个 producer 都完成之前，每次任一 producer 更新 value 都会触发重组
        // 重组次数 = sourceA 更新次数 + sourceB 更新次数
    }
}
```

合并策略：用 `combine` 或 `zip` 在 Flow 层合并多个数据源，只产生一个 `produceState`：

```kotlin
@Composable
fun CombinedSourceScreen(viewModel: ViewModel) {
    val combined by produceState(Pair(Result.Loading, Result.Loading), viewModel) {
        combine(viewModel.flowA, viewModel.flowB) { a, b -> a to b }
            .collect { value = it }
    }
    // 只有一个 State，每次上游更新只触发一次重组
}
```

## Compose 编译器版本与性能行为变化

`rememberCoroutineScope` 和 `produceState` 的行为在不同 Compose 版本间基本稳定，但 Compose Runtime 的整体性能行为有几次关键变化：

### 版本矩阵

| Compose 版本 | 协程相关变化 | 对本章内容的影响 |
|---|---|---|
| 1.7 (2024 Q3) | Strong Skipping Mode 实验性引入 | Lambda 参数被自动 memoize，减少了手动 `remember { }` 的需要 |
| 1.9 (2025 Q3) | LazyLayout 预取改进 + 后台文本预取 | `produceState` 在 LazyColumn item 中使用时，预取可能在 Composition 外触发 |
| 1.10 (2025 Q4) | Pausable Composition 成为默认 | 长时间运行的 `produceState` producer 可能在帧边界被暂停，不影响功能但改变了时序假设 |
| Kotlin 2.2 | Strong Skipping 默认启用 | 所有 `@Composable` 函数自动 skippable，不再需要 `enableStrongSkippingMode` 配置 |

### Pausable Composition 对 produceState 的影响

Pausable Composition（Compose 1.10 默认，详见 §22.3）的暂停机制作用在 Composition 阶段。`produceState` 的 producer 协程运行在 Composition 之外（挂起函数在协程调度器上运行），不受 Pausable Composition 的暂停影响。

受影响的是**读取 `produceState` 返回值的 Composable**：如果 Composition 在帧边界被暂停，State 值的更新可能在下一帧才被读取。这不改变数据正确性，但改变了状态更新的可见时序。

### 版本升级导致的静默性能退化案例

**案例：Kotlin 2.0 → 2.2 升级后 LazyColumn 重组增加**

Kotlin 2.2 默认启用 Strong Skipping 后，所有 lambda 被自动 memoize。但在 LazyColumn 中，如果 item 的 `key` 使用了不稳定的对象（如 `data class` 实例），key 的 `equals()` 在每次比较时可能返回不同的结果，导致 LazyColumn 认为列表项发生了变化，触发不必要的重组。

```kotlin
// 问题：key 用了 data class 实例，每次父 Composable 重组时可能是新对象
LazyColumn {
    items(items = list, key = { it /* 如果 it 是 data class 且属性变了，key 变了 */ }) {
        ItemComposable(it)
    }
}

// 修复：使用稳定的 key（如数据库 ID）
LazyColumn {
    items(items = list, key = { it.id /* Long 或 String，值稳定 */ }) {
        ItemComposable(it)
    }
}
```

这个退化是静默的——没有编译错误或运行时异常，只在 Perfetto 中表现为重组计数增加。

## Perfetto 中诊断 Compose 性能盲区

Perfetto 中诊断 Compose 性能问题的通用方法在 §22.3 和 §13.10 已有详细说明。本节只补充 `rememberCoroutineScope` 和 `produceState` 相关的诊断 SQL。

### 识别 rememberCoroutineScope 泄漏

```sql
-- 查找活跃协程数异常增长的时段
SELECT
    ts,
    name,
    value AS active_coroutines
FROM counter
JOIN track ON counter.track_id = track.id
WHERE track.name LIKE '%coroutine%'
AND value > 50
ORDER BY ts
LIMIT 100;
```

协程泄漏的特征：页面退出后（对应的 Composition slice 结束），活跃协程数没有回落。结合 `NavigationController` 的页面切换 slice，对比切换前后的协程数变化。

### 识别 produceState 的无效更新

```sql
-- 查找频繁的 State 更新 slice
SELECT
    slice.name,
    COUNT(*) AS update_count,
    AVG(slice.dur) AS avg_duration_ns
FROM slice
WHERE slice.name LIKE '%Compose%'
AND slice.name LIKE '%state%'
GROUP BY slice.name
HAVING update_count > 100
ORDER BY update_count DESC;
```

`produceState` 的每次 `value = newValue` 都会触发一次 State 写入，如果上游 Flow 发射频率很高（如传感器数据每 16ms 一次），State 写入会驱动下游 Composable 频繁重组。用 `distinctUntilChanged()` 或 `debounce()` 在 Flow 层过滤无效更新。

### 重组热力图定位

Compose Tracing（Android 12+，`compose.tracing` trace config）在 Perfetto 中生成重组计数的 counter track。结合 Perfetto SQL 可以定位哪些 Composable 被频繁重组：

```sql
-- 重组次数最多的 Composable
SELECT
    slice.name AS composable_name,
    COUNT(*) AS recomposition_count
FROM slice
WHERE slice.name LIKE 'CC:%'
GROUP BY slice.name
ORDER BY recomposition_count DESC
LIMIT 20;
```

`CC:` 前缀的 slice 对应 Compose Compiler 插入的重组计数标记。重组次数与页面停留时间之比高于阈值的 Composable 是优化目标。判断阈值需要结合帧时间——如果重组没有导致帧超时（16.67ms / 8.33ms），优化优先级可以降低。

> [结构参考: 研究素材 2026-04-01 Compose 性能里程碑 + 2026-04-10 Pausable Composition 机制]
> [已验证: Compose Runtime 1.10 Pausable Composition 为默认行为, BOM 2025.12.00]
> [已验证: Strong Skipping Mode Kotlin 2.0.20 起默认启用]
> [待验证: Perfetto 中 Compose Tracing 的 slice 命名前缀在不同 Compose 版本中的差异]
