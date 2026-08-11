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

`rememberCoroutineScope`、`produceState` 和 Strong Skipping 分属三个层次：Composition 生命周期、Runtime effect、Compose Compiler。把它们放进同一条“减少重组”规则，容易得到错误的取消、key 和性能结论。

分析使用三组固定锚点：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`；
- kernel：`android17-6.18-2026-06_r6`；
- UI 工具链：Compose BOM `2025.12.00`、Compose Runtime `1.10.0`、Kotlin `2.2`。

Compose Runtime 是随应用发布的 AndroidX 库，Android platform tag 不包含对应代码。Android 17 提供 Looper、Choreographer、HWUI、FrameTimeline 等宿主能力；Runtime 和 Compiler 行为要按项目解析出的依赖版本核查。重组、稳定性和阶段性读取的通用方法见 [22.3 Compose 性能优化](03-compose-performance.md)，显示路径见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)。

## `rememberCoroutineScope`：用于事件，不用于启动副作用

Compose Runtime 1.10.0 的 `rememberCoroutineScope()` 通过 `remember` 保存同一个 `RememberedCoroutineScope`。该对象自己实现 `RememberObserver`：

- 第一次访问 `coroutineContext` 时，才创建 `Job(parentContext[Job])`；
- 默认 dispatcher 来自当前 Composition 的 applying dispatcher；
- 调用点被遗忘或放弃时，`onForgotten()` / `onAbandoned()` 调用 `cancelIfCreated()`；
- `getContext` 返回值不能包含 `Job`。传入 `Job` 时，API 不在组合期间抛异常，而会返回带失败 Job 的 scope。

这里创建的是普通 child `Job`，源码没有使用 `SupervisorJob`。一个事件任务抛出未处理异常时，不要假定同一 scope 中的其他任务一定保持独立；业务可预期的失败应在任务边界处理。

下面的按钮只在点击回调中启动任务，scope 的 owner 与按钮所在的 Composition 位置一致。

```kotlin
@Composable
fun SaveButton(
    enabled: Boolean,
    onSave: suspend () -> Unit,
) {
    val scope = rememberCoroutineScope()

    Button(
        enabled = enabled,
        onClick = {
            scope.launch {
                onSave()
            }
        },
    ) {
        Text("保存")
    }
}
```

Composable 重组不会重复启动这项工作。按钮离开 Composition 后，scope 会收到取消；`onSave()` 仍需遵守结构化并发和可取消约定。连续点击应由 UI 状态、互斥、任务去重或“取消上一项”策略明确处理，scope 本身不会替业务选择并发策略。

需要随 key 进入、变化和退出自动管理的持续工作，应直接放在 `LaunchedEffect`。下面的 producer 随 `userId` 或 repository 变化而重启，`rememberUpdatedState` 只负责让长任务读取最新回调。

```kotlin
@Composable
fun ObserveUserEvents(
    userId: String,
    repository: UserRepository,
    onEvent: (UserEvent) -> Unit,
) {
    val currentOnEvent by rememberUpdatedState(onEvent)

    LaunchedEffect(userId, repository) {
        repository.events(userId).collect { event ->
            currentOnEvent(event)
        }
    }
}
```

这里不再套一层 `rememberCoroutineScope().launch`。`LaunchedEffect` 的 key 变化会取消旧 collector，并把新 collector 纳入新的 effect 生命周期。若把收集任务发到外层 remembered scope，effect key 只取消启动者，外层任务可能继续处理旧用户的数据。

## 取消发生了，不代表清理已经完成

Composition 应用移除操作时会调用 `onForgotten()`，`Job.cancel()` 随即把取消状态传播给子任务。协程何时结束，取决于 dispatcher、挂起点以及代码是否配合取消。以下情况会延长对象引用和资源占用：

- 长时间 CPU 循环不检查 `isActive`，也不调用可取消挂起函数；
- 阻塞 I/O 忽略线程中断或没有取消接口；
- `NonCancellable` cleanup 执行耗时操作；
- 工作被转交给 `GlobalScope`、ViewModel scope、repository scope 或自建 executor；
- callback 注册在外部对象上，却没有与 owner 对应的反注册。

因此，页面退出后短时间仍能观察到任务或对象引用，不能直接判定为 scope 泄漏；要确认取消是否到达、任务是否完成、外部注册是否解除。ViewModel 的生命周期长于某个 Composable 也属于正常所有权关系。问题通常出在工作越过了预期 owner，或取消后仍长期不退出。

清理代码没有固定的“下一帧执行”保证。`finally` 可能在当前调度轮次运行，也可能等待目标 dispatcher；阻塞 cleanup 还会占用对应线程。主线程 cleanup 应保持短小，大文件关闭、编码收尾或数据库提交需要单独设计线程与超时。

## `produceState` 的实现：remembered State 加 keyed effect

Compose Runtime 1.10.0 的每个 `produceState` 重载都由两部分组成：

1. `remember { mutableStateOf(initialValue) }` 保存结果；
2. `LaunchedEffect(keys...)` 创建 `ProduceStateScopeImpl` 并运行 producer。

这带来四个直接后果：

- 无 key 重载使用固定的 `Unit`，重组不会重启 producer；
- key 变化会取消旧 producer，再启动新 producer；
- 返回的 State 在 key 变化时仍是同一个 remembered 对象；
- `initialValue` 只参与第一次 State 创建，key 变化不会自动把值重置为新的 initial value。

加载场景若希望切换 key 后立即回到 Loading，需要由 producer 明确写入。下面的示例同时把 `userId` 和 repository 作为任务身份，并避免吞掉协程取消异常。

```kotlin
@Composable
fun rememberUserProfile(
    userId: String,
    repository: UserRepository,
): State<ProfileResult> {
    return produceState<ProfileResult>(
        initialValue = ProfileResult.Loading,
        key1 = userId,
        key2 = repository,
    ) {
        value = ProfileResult.Loading
        value = try {
            ProfileResult.Success(repository.load(userId))
        } catch (error: IOException) {
            ProfileResult.Error(error)
        }
    }
}
```

`IOException` 是该 repository 声明的业务失败边界；代码没有捕获 `Throwable`，因此 key 变化或离开 Composition 产生的 `CancellationException` 可以继续传播。项目若有领域错误模型，应在 repository 或 use case 层完成映射。

key 选择表达的是 producer 身份：

- producer 读取 `userId` 和 repository，这两个值就应进入 key；
- 每次重组都新建且不相等的 key 会反复取消工作；
- 可变对象原地修改且 identity/equals 不变，会让 producer 保留旧任务；
- key 适合放稳定 ID、不可变配置或明确代表数据源实例的对象。

Strong Skipping 不替 `produceState` 补 key。Compiler 负责决定某个 Composable 调用能否跳过；`LaunchedEffect(keys)` 负责 producer 的取消和重启。

## `awaitDispose` 只服务订阅式数据源

`ProduceStateScope.awaitDispose()` 通过可取消挂起等待 owner 退出，并在 `finally` 中执行回调。它返回 `Nothing`，适合“注册 callback 后一直等待取消”的数据源。

下面的适配器注册一次监听，并保证 source 变化或调用点离开时解除注册。

```kotlin
@Composable
fun rememberConnectivity(
    monitor: ConnectivityMonitor,
): State<Boolean> {
    return produceState(
        initialValue = monitor.currentValue,
        key1 = monitor,
    ) {
        val listener = ConnectivityListener { connected ->
            value = connected
        }

        monitor.addListener(listener)
        awaitDispose {
            monitor.removeListener(listener)
        }
    }
}
```

`currentValue` 应是便宜的内存读取。注册函数如果可能部分成功后抛异常，需要由 adapter 自己维护可释放句柄，避免 `awaitDispose` 尚未到达时遗留 callback。

对无限 Flow 调用 `collect` 时，不要把 `awaitDispose` 写在 `collect` 后面。正常收集期间那一行不可达；取消时 `collect` 会退出并执行 Flow 自己的 `finally` / `callbackFlow.awaitClose`。额外资源可用 `try/finally` 包围 `collect`，或把 callback 生命周期封装进 Flow。

Android 界面直接收集 Flow 时，优先使用 lifecycle-aware API。下面的调用只在 Lifecycle 达到配置的 active state 时保留这条 UI collector；上游 hot flow 是否继续运行，由 `stateIn` / `shareIn` 的 sharing policy 和 owner 决定。

```kotlin
val uiState by viewModel.uiState.collectAsStateWithLifecycle()
```

`collectAsState()` 适合不依赖 Android Lifecycle 的公共代码。Compose Runtime 1.10.0 的 `collectAsState()` 本身也通过 `produceState(initial, flow, context)` 实现，因此两者的选择依据是生命周期和语义，不能用“少一个 ProduceStateScope 分配”解释。

## State conflation 不等于上游节流

`produceState` 的文档明确说明返回值会 conflated。默认 `mutableStateOf` 使用结构相等策略：

- 新值与旧值 `equals()` 相等时，不通知读取者；
- 多个值在 Composition 消费前快速写入时，读取者可能只观察到较新的值；
- producer 里的网络、解析、映射和每次赋值仍然执行，conflation 不会减少上游工作。

高频传感器、滚动或媒体进度要按交互需求选择 `sample`、`conflate`、`distinctUntilChanged` 或领域聚合。`debounce` 会引入等待，不适合所有实时 UI。只影响像素位置或透明度的高频值，还可以把读取推迟到 Layout、Drawing 或 layer property，减少 Composition 工作。

可变对象尤其危险。若 `value` 指向某个对象，代码原地修改字段后又把同一引用赋回，结构相等策略看不到变化。手工添加 `@Stable` 只会向 Compiler 作出更强承诺，无法让普通 `var` 发送 Snapshot 通知。

可靠的 UI model 通常采用以下一种形式：

- 所有字段为 `val`，更新时创建新实例；
- 可变字段使用 `MutableState`、`SnapshotStateList` 等 Snapshot 容器；
- 外部可变模型在进入 UI 层前转换为不可变快照。

`@Stable` / `@Immutable` 属于契约。字段变化无法被 Compose 观察时，不应添加这些注解来追求 compiler report 变绿。

## Strong Skipping 只改变调用与 lambda

Kotlin 2.0.20 起默认启用 Strong Skipping，这里的 Kotlin 2.2 基线已经包含该行为。[Strong Skipping 官方说明](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)

它对上述代码有两项影响：

- restartable Composable 即使带 unstable 参数，也能在参数满足比较规则时跳过；
- Composable 内创建的 lambda 会自动 memoize，捕获值成为 key。Stable 捕获值按 `equals()` 比较，unstable 捕获值按实例比较。

`rememberCoroutineScope` 在 Composition 生命周期内返回同一个对象，这来自 `remember`，与 Strong Skipping 无关。Strong Skipping 可以减少 `onClick` lambda 的重复创建，并让接收该 lambda 的子 Composable 更容易跳过；它不会改变 scope 的 Job、dispatcher、取消时机或异常传播。

`produceState` 返回的 `State<T>` 也由 `remember` 保持身份。State 写入会失效读取它的 restart scope；父调用能否跳过，无法阻止这个依赖触发。性能评审要分清三个问题：

| 问题 | 对应机制 |
| --- | --- |
| producer 何时启动或重启 | `LaunchedEffect` keys |
| 新值是否通知读取者 | Snapshot state mutation policy |
| 父级传播到子 Composable 时能否跳过 | Compiler stability + Strong Skipping |

把 unstable model 原地修改，会同时破坏 State 变更检测和参数比较。这个问题应从数据所有权修复，不能依赖 Strong Skipping 掩盖。

## 多数据源：独立失效与一致快照之间取舍

两个 `produceState` 独立运行时，完成顺序没有保证。Compose 可能把同一调度窗口里的多次 Snapshot 变更合并进一次 Composition，所以“两个 State 必然产生两次重组”不成立。

选择方式取决于 UI 消费关系：

- 两块互不相关的 UI 分别读取两个 State，独立 producer 可以缩小失效范围；
- 同一块 UI 必须同时看到 A/B 的一致组合，应在 ViewModel 或 repository 生成一个不可变 `UiState`；
- `combine` 会在任一上游变化时发射，不能自动减少发射次数；
- `zip` 按配对语义等待两侧，不适合替代所有 combine 场景。

Flow 的组合、重试和缓存一般放在 ViewModel，再通过 `stateIn` 暴露稳定的 `StateFlow`。Composable 每次执行时临时创建一条新 Flow，会让 `collectAsState*` 把它视作新数据源并重启收集。

## Pausable Composition 不会暂停已启动的 producer

Compose Runtime 的 Pausable Composition 切分的是 Composition 工作。`produceState` 要等对应 change 被应用、`LaunchedEffect` 被 remembered 后才启动；尚未 apply 的暂停内容不会提前启动 producer。

producer 已启动后，它按协程 dispatcher 和挂起点运行。Pausable Composition 没有一条通用机制去暂停已运行的网络请求、Flow collector 或 callback。State 写入何时被下一次 Composition 消费，又受 Recomposer 调度、Snapshot 通知和帧 deadline 影响，不能承诺固定延后一帧。

Foundation 的 Lazy 预取是否使用 Pausable Composition，还受具体 Foundation 补丁版本和 flag 影响。它与 `produceState` 的协程取消协议是两个问题；列表预取边界见 [22.3 Compose 性能优化](03-compose-performance.md)。

## 诊断：用可验证的事件替代猜测

Perfetto 默认没有名为 `CoroutineTracker` 的标准 Compose 轨道，也没有保证存在 `CC:` 前缀的重组 slice。`kotlinx-coroutines-debug` 的 `DebugProbes` 适合调试或测试中的 coroutine dump，不会自动生成可跨设备依赖的 Perfetto counter。

诊断时按问题选择证据：

| 目标 | 建议证据 |
| --- | --- |
| scope 是否在 owner 退出后取消 | 测试 Job 状态、任务 `finally` 计数、外部订阅计数 |
| producer 是否因 key 抖动重启 | 应用自定义 start/cancel/complete 事件与 key 日志 |
| State 写入是否过频 | 上游 emission、写入、相等值丢弃和读取者执行次数 |
| 哪些 Composable 执行 | `runtime-tracing` + profileable、non-debuggable 构建 |
| 参数为何不能稳定跳过 | Compose Compiler metrics/reports |
| 是否造成用户可见卡顿 | Macrobenchmark、FrameTimeline、UI/RenderThread/GPU 对齐 |
| 对象为何未释放 | heap dump、引用链、callback/executor owner |

Composition tracing 需要显式加入 `androidx.compose.runtime:runtime-tracing`；官方前提包含 API 30+、Compose UI/Compiler 1.3.0+ 和受支持的 Android Studio。Android 14—17 满足设备 API 前提，但仍要确认依赖已加入。抓 trace 后应先查看文件中存在的 slice 名称，再编写 SQL，避免用不存在的通用名称查询。[Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)

FrameTimeline 负责标记 App frame 和 display frame 的 deadline/jank。它无法直接告诉你某个 `produceState` 写入造成了哪次重组；要用 timestamp、线程、应用事件和 Compose slice 对齐。标准 App Window 的 App SurfaceFrame、DisplayFrame 与 present 边界见 [Android 17 FrameTimeline 数据结构](../../part1-fundamentals/ch02-rendering/2.32-android-17-frametimeline-数据结构.md)。

## Android 17 与 kernel 的责任边界

`rememberCoroutineScope`、`produceState`、Snapshot 和 Strong Skipping 都不在 Android 17 platform 或 Linux kernel 中实现。平台负责主线程消息、Choreographer 回调、View/HWUI 帧提交和 FrameTimeline；kernel 负责线程调度、定时、futex 与设备驱动等待。

CPU 调度延迟或主线程 runnable 堆积可能推迟 Recomposer/producer continuation，仍不能从 scheduler slice 反推 effect key 是否正确。应用层先验证 owner、key、取消和 State 写入，再沿 Android 17 的 Choreographer/FrameTimeline 证据检查是否错过 deadline。kernel 分析固定在 `android17-6.18-2026-06_r6`，只解释调度与等待，不解释 Compose Runtime 语义。

## 评审清单

- `rememberCoroutineScope` 只从事件回调启动任务，没有在 Composable body 或 `LaunchedEffect` 中再套 launch；
- 长任务使用 `LaunchedEffect(keys)`，需要最新 callback 时使用 `rememberUpdatedState`；
- scope 没有被保存到 ViewModel、单例或其他长生命周期 owner；
- producer 读取的身份输入全部进入 key，key 本身不会无故变化；
- key 变化后的 Loading reset 已在代码中处理；
- callback 数据源使用 `awaitDispose` 对称反注册，Flow 不在无限 `collect` 后追加它；
- UI state 使用不可变新实例或 Snapshot 容器；
- 高频上游先控制 emission 和语义，再看重组次数；
- Strong Skipping 只用于解释调用跳过和 lambda memoization；
- trace 查询基于当前文件存在的事件名，帧性能由 Macrobenchmark/FrameTimeline 验收。

## 小结

`rememberCoroutineScope` 管理事件任务，`produceState` 用 keyed `LaunchedEffect` 把外部数据写入 remembered State，Strong Skipping 管理 Composable 调用与 lambda memoization。三者互相影响性能，却没有共享一套生命周期规则。

稳定实现依赖四个明确选择：scope owner、producer key、State 变更语义、上游 emission 频率。取消只代表信号已经发出，清理完成仍要靠协作；conflation 只控制观察结果，上游工作仍需单独治理；Compiler 跳过也不会修复错误的 key 或可变数据模型。

## 源码与官方资料

- [Compose Runtime 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.10.0/runtime-1.10.0-sources.jar)：`Effects.kt`、`ProduceState.kt`、`SnapshotFlow.kt` 的精确版本输入。
- [`rememberCoroutineScope` / `produceState` 官方指南](https://developer.android.com/develop/ui/compose/side-effects)：事件 scope、effect 生命周期与 callback adapter。
- [Compose State 官方指南](https://developer.android.com/develop/ui/compose/state)：Android 上的 `collectAsStateWithLifecycle()` 与平台无关的 `collectAsState()`。
- [Strong Skipping 官方说明](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)：参数比较、restartable/skippable 与 lambda memoization。
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)：`runtime-tracing` 依赖、profileable 构建与 Perfetto 采集前提。
- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java) 与 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：Android 17 帧调度与系统显示时间线。
- [`core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c) 与 [`waitwake.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/futex/waitwake.c)：kernel 侧线程调度与 futex 等待边界。
