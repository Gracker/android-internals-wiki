---
title: "Kotlin Flow 背压、操作符链与响应式性能边界"
chapter: "8.17"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [kotlin, flow, coroutines, backpressure, reactive, performance]
related_chapters: ["8.6", "5.10", "7.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-25"
gap_source: "章节深挖"
last_verified: "2026-08-09"
last_verified_against: "AOSP android-17.0.0_r1; kernel android17-6.18-2026-06_r6; kotlinx.coroutines 1.11.0; Android lifecycle/Compose/benchmark official docs"
confidence: "high"
sources:
  - type: official
    path: "https://kotlinlang.org/docs/coroutines-flow.html"
  - type: official
    path: "https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-flow/"
  - type: source
    path: "https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/operators/Context.kt"
  - type: source
    path: "https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/SharedFlow.kt"
  - type: source
    path: "https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/StateFlow.kt"
  - type: source
    path: "https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/operators/Merge.kt"
  - type: source
    path: "https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/ui/kotlinx-coroutines-android/src/HandlerDispatcher.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Looper.java"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c"
last_deep_review_at: "2026-08-01T12:35:46+08:00"
last_deep_review_run_id: "20260801-123546-deep-review-9d1e8e3a"
---

# 8.17 Kotlin Flow 背压、操作符链与响应式性能边界

Flow 的性能问题很少能用“操作符太多”概括。更常见的原因是语义选错：不能丢的数据用了 conflation，允许覆盖的 UI 状态排成了长队；冷流被多个界面重复收集，热流又在无人订阅时持续访问上游；CPU 转换留在主线程，或用无上限并发放大网络和内存压力。

平台上限为 Android 17 / API 37，库侧按 `kotlinx.coroutines` 1.11.0 的公开 API 和源码校验。Flow 属于可独立升级的 Kotlin 库，同一 Android 17 设备可以运行不同版本；分析线上问题时要同时记录应用使用的协程库版本。

## 1. Flow 默认怎样传递压力

普通 `flow {}` 是冷流。每次执行 terminal operator，例如 `collect`、`first`、`toList`，都会重新运行 builder 及其上游代码。冷流默认顺序执行，生产、各级转换和消费位于同一个收集协程中；下游没有处理完当前元素时，上游的 `emit` 不能继续推进。

下面的例子展示冷流重复执行和默认的顺序传递。

```kotlin
fun rows(): Flow<Row> = flow {
    database.queryRows().forEach { row ->
        emit(row)
    }
}

suspend fun readTwice() {
    rows().collect { consumeForScreen(it) }
    rows().collect { consumeForExport(it) }
}
```

`queryRows()` 在这里会运行两次。这不自动等于浪费：两个 collector 可能需要不同时间点的数据、不同生命周期或独立错误边界。只有当业务要求共享同一上游实例时，才应使用 `shareIn`、`stateIn` 或仓库级缓存。

Flow 的默认压力传递依靠挂起，没有 Reactive Streams 的显式 `request(n)` 调用。它能通过 `kotlinx-coroutines-reactive` 适配器与 Reactive Streams 互操作，但阅读普通 Flow 代码时，应从“哪一个 suspend 点会等待”入手。

### 1.1 默认顺序不产生队列

不使用 `buffer`、`flowOn`、`channelFlow`、并发 flatten 等边界时，下游慢会直接延长上游下一次 `emit` 的返回时间。此时不会在 Flow 内部无限堆积元素，代价是生产者与消费者不能重叠执行。

阻塞线程和挂起协程也要分清：

- `delay`、支持取消的挂起 I/O 会让出线程；
- 数据库驱动、文件 API 或业务 SDK 的同步调用仍可能阻塞当前线程；
- 挂起函数不承诺自动运行在后台 dispatcher；
- Flow 能限制元素推进速度，不能把阻塞调用变成非阻塞调用。

## 2. `buffer`、丢弃与取消是三种语义

下面的表格按数据结果区分常用操作符：

| 方式 | 慢消费者出现时 | 是否丢值 | 主要风险 |
|---|---|---|---|
| 默认顺序 Flow | 上游 `emit` 挂起 | 否 | 上下游无法并行 |
| `buffer(n)` + `SUSPEND` | 队列满后上游挂起 | 否 | 排队延迟与对象驻留 |
| `buffer(n, DROP_OLDEST)` | 丢最旧的排队值 | 是 | 中间状态不可恢复 |
| `buffer(n, DROP_LATEST)` | 丢正在进入的新值 | 是 | 最新输入可能未处理 |
| `conflate()` | 上游继续，collector 取得最近值 | 是 | 只适合可覆盖状态 |
| `collectLatest` | 新值到来时取消旧 action | 旧 action 可能未完成 | 副作用可能被中断 |
| `debounce` | 等待一段静默期 | 是 | 引入用户可见等待 |
| `sample` | 周期性取该窗口最近值 | 是 | 采样边界不等于显示帧 |

### 2.1 `buffer()` 默认不是 rendezvous

`buffer()` 的默认 capacity 是 `Channel.BUFFERED`。显式 `buffer(0)` 或 `buffer(Channel.RENDEZVOUS)` 才表示零容量通道。`buffer` 会在执行时把上游放到独立协程，通过 Channel 与下游连接，因此上下游工作可以重叠。

下面的写法适合“不能丢数据，但允许有限排队”的解析管线。

```kotlin
source
    .buffer(
        capacity = 32,
        onBufferOverflow = BufferOverflow.SUSPEND,
    )
    .map { packet -> decode(packet) }
    .collect { decoded -> persist(decoded) }
```

32 只是示例容量。工程值应由元素大小、峰值生产速率、消费时长和允许排队时间共同决定。容量增大可能提高吞吐，也可能把拥塞改成更长的尾延迟和更高的堆占用。

相邻的 `channelFlow`、`flowOn`、`buffer` 和 `produceIn` 会进行 operator fusion，通常只保留一个按规则合成的 Channel。不能按源码表面出现几个操作符，就推算运行时一定有几个队列。

### 2.2 `conflate()` 适合可覆盖状态

`conflate()` 等价于 `buffer(capacity = 0, onBufferOverflow = DROP_OLDEST)` 的语义：发射者不因慢 collector 挂起，collector 总是取得最近可用值。进度、温度、滚动位置等状态快照常可采用这一策略；支付事件、日志序列、数据库变更命令不能随意丢弃。

`StateFlow` 已经按 `Any.equals` 做强相等合并，再对它调用 `conflate()` 没有效果。若状态类破坏 `equals` 合同，StateFlow 的行为没有定义；可变对象原地修改也可能让更新无法被识别。

### 2.3 `collectLatest` 取消的是 action

`collectLatest` 收到新值后取消前一个 action，再启动新 action。`flatMapLatest` 会取消前一个内部 Flow；`mapLatest` 会取消前一个 transform。三者不能互换。

下面的搜索例子让新查询替换旧查询，并在查询文本稳定一段时间后访问仓库。

```kotlin
queryText
    .debounce(300)
    .distinctUntilChanged()
    .flatMapLatest { query ->
        repository.search(query)
    }
    .collect { results ->
        render(results)
    }
```

旧的 `repository.search()` 必须支持协作式取消，替换才会及时。长时间无 suspend 点的 CPU 循环应定期检查 `ensureActive()`；不能取消的阻塞 SDK 即使外层协程已取消，也可能继续占用线程或网络资源。取消耗时取决于代码和资源，没有通用的 5–10 ms 结论。

## 3. StateFlow 与 SharedFlow 的成本来自订阅者和缓冲

### 3.1 StateFlow 是状态容器

`MutableStateFlow` 始终有一个当前值，新订阅者会收到该值；设置与旧值相等的新值不会产生更新。它本身不启动一条常驻协程。只有 `stateIn` 等操作符把冷上游共享到指定 scope 时，才会创建用于收集上游的协程。

官方实现说明给出了两个有用的复杂度边界：

- 增加订阅者的摊销成本为 O(1)；
- 更新 value 的成本为 O(N)，N 是活跃订阅者数量。

因此，StateFlow 很适合单一 UI 状态和少量订阅者。若同一状态被大量内部组件独立订阅，发射成本也应进入基准测试。它基于协程库内部的状态槽实现，不依赖 Compose 的 `mutableStateListOf` 等 UI 侧容器。

### 3.2 SharedFlow 是广播

`MutableSharedFlow` 的公开参数是 `replay`、`extraBufferCapacity` 和 `onBufferOverflow`。`replay` 既给新订阅者回放，也参与慢订阅者缓冲；每次 emit 的实现成本随订阅者数量 O(N) 增长。

下面的配置用于允许丢弃旧样本的传感器遥测，不适用于必须执行的业务命令。

```kotlin
private val _samples = MutableSharedFlow<SensorSample>(
    replay = 0,
    extraBufferCapacity = 32,
    onBufferOverflow = BufferOverflow.DROP_OLDEST,
)

val samples: SharedFlow<SensorSample> = _samples.asSharedFlow()

fun offerSample(sample: SensorSample): Boolean {
    return _samples.tryEmit(sample)
}
```

没有订阅者时，SharedFlow 只保留 `replay` 指定的元素，`extraBufferCapacity` 不生效。这个例子中 `replay = 0`，无人订阅时样本会丢失。默认的 `MutableSharedFlow()` 也有一个反直觉边界：没有订阅者时 `tryEmit` 返回 `true`，值却会立即丢失；有订阅者且没有可用容量时则返回 `false`。

SharedFlow 不会正常完成，也不能像 Channel 那样 close。完成、错误、重试或“任务已消费”都要建模成数据或放到另一条有持久化语义的通道。

### 3.3 `shareIn` / `stateIn` 管理共享上游

下面的 ViewModel 把仓库冷流共享为 UI StateFlow，并在短暂配置变更时保留上游。

```kotlin
val uiState: StateFlow<UiState> =
    repository.observeDashboard()
        .map { model -> UiState.Ready(model) }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(
                stopTimeoutMillis = 5_000,
            ),
            initialValue = UiState.Loading,
        )
```

5 秒是示例策略，不是库的性能推荐值。`WhileSubscribed()` 默认在末位订阅者离开后立即停止上游，并永久保留 replay；`stopTimeoutMillis` 可延迟停止，`replayExpirationMillis` 可控制缓存何时重置。上游是 GPS、socket 或高成本查询时，生命周期策略会直接影响功耗、连接和重复初始化次数。

`Eagerly` 会在首个订阅者出现前启动，超过 replay 的值可能直接丢弃；`Lazily` 在首个订阅者出现后启动，并在之后没有订阅者时继续保持上游。不要只因“查询贵”就把所有冷流改成永久热流。

## 4. 操作符链不会为每一级创建 Job

`map`、`filter`、`onEach` 等顺序操作符会返回包装后的 Flow，但不会各自复制一份 `CoroutineContext`、创建 dispatcher 或建立父子 Job。默认链仍在 collector 的协程中顺序运行。会引入协程或 Channel 边界的主要是 `buffer`、跨 dispatcher 的 `flowOn`、`channelFlow`、`callbackFlow`、`shareIn`、`stateIn` 和并发 flatten 操作。

因此，“链长超过 5 就合并操作符”没有通用依据。把 map 和 filter 塞进一个大 transform 可能减少少量包装，也会损失可读性、复用与测试边界。应在热路径上用 AndroidX Microbenchmark 比较真实元素类型、编译模式和操作符组合。

Sequence 也不能写成“零分配”。它是同步、拉取式抽象，Flow 支持 suspend、取消和异步边界。纯内存集合且没有挂起需求时可以比较 List 循环、Sequence 与 Flow；涉及生命周期、异步数据源或持续事件时，语义通常比微小包装成本更早决定选择。

## 5. 并发 flatten 要服从资源上限

### 5.1 `flatMapMerge`

`flatMapMerge(concurrency)` 顺序调用 transform，随后并发收集返回的内部 Flow，输出顺序不稳定。当前默认 `DEFAULT_CONCURRENCY` 是 16，属于 preview 配置，并可在 JVM 上通过系统属性改变；业务代码不应依赖默认值。

并发度应同时满足：

- 服务端、数据库连接池或文件描述符上限；
- 单任务内存与响应体大小；
- dispatcher 可运行线程和设备 CPU；
- 失败、重试与取消造成的瞬时放大；
- 是否允许结果乱序。

把并发从 16 调到 32 不保证吞吐提高。瓶颈在服务端限流、磁盘或单核 CPU 时，更高并发可能只增加队列、上下文切换和尾延迟。

### 5.2 `flatMapConcat` 与普通 `map`

`flatMapConcat` 按顺序完整收集每一个内部 Flow。若每个输入只调用一次 suspend 函数并返回一个值，普通 `map { repository.load(it) }` 更直观。只有 transform 本身要返回多值 Flow，并且业务要求前一个内部 Flow 完成后再进入下一个，才需要 concat 语义。

### 5.3 `flatMapLatest`

latest 适合“旧结果失效”的输入，例如搜索词、选中的账号或地图视口。它不适合付款、消息发送、写文件等必须完成的副作用。若副作用已发到远端，取消本地等待也不表示远端操作被撤销，业务仍要使用幂等键和服务端状态查询。

## 6. `flowOn` 只改变上游

`flowOn(context)` 影响它之前、且没有自有 context 的操作符，不会把 dispatcher 泄漏到下游。dispatcher 发生变化时，库会用上游协程和默认缓冲 Channel 连接 collector；前后显式 `buffer` 可以指定这个融合 Channel 的容量。

下面的例子把 CPU 解码放到 Default，同时让 UI collector 留在调用方的 Main context。

```kotlin
repository.observePackets()
    .map { packet -> decodePacket(packet) }
    .flowOn(Dispatchers.Default)
    .map { decoded -> toUiModel(decoded) }
    .collect { model ->
        render(model)
    }
```

`observePackets` 与 `decodePacket` 位于 `flowOn` 上游，都会在 Default 执行；`toUiModel` 和 `collect` 使用 collector context。若 `toUiModel` 也很重，应调整操作符位置或增加经过测量的 context 边界。

不要习惯性给 Room Flow、Retrofit suspend 调用或已有线程管理的数据源再套 `Dispatchers.IO`。这些库可能已经把阻塞工作放到自己的 executor；多一次 `flowOn` 仍会引入协程、Channel 和取消边界，却未必迁移任何阻塞工作。

普通 `flow {}` 要求在同一 coroutine context 中 emit。下面这种跨 context emit 会违反 Flow invariant；需要切换上游时使用 `flowOn`，需要多个协程并发 send 时使用 `channelFlow` 或 `callbackFlow`。

```kotlin
val invalid = flow {
    emit(loadCached())
    withContext(Dispatchers.IO) {
        emit(loadRemote()) // 运行时会触发 Flow invariant 异常
    }
}
```

`channelFlow` 仍是冷流，每次 terminal collection 都重新执行 block。它允许子协程并发 `send`，也会引入 Channel；只在确有多个并发生产者时使用。

## 7. Android 生命周期决定上游是否继续工作

### 7.1 View UI

直接在 `lifecycleScope.launch` 中 collect，会一直运行到 Lifecycle 销毁。页面进入 STOPPED 后若无需更新 UI，应使用 `repeatOnLifecycle`；多个 Flow 需要并行收集时，在 repeat block 内分别 `launch`。

下面的 View 示例只在界面至少处于 STARTED 时收集。

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        launch {
            viewModel.uiState.collect { state ->
                render(state)
            }
        }
        launch {
            viewModel.effects.collect { effect ->
                handle(effect)
            }
        }
    }
}
```

进入 STOPPED 时，repeat block 及其子协程会取消；回到 STARTED 时重新启动。冷流会随之重新运行，上游是否应共享由仓库或 ViewModel 的 `stateIn` / `shareIn` 决定。`launchWhenStarted` 只暂停协程的旧写法可能让上游继续工作，官方建议使用 `repeatOnLifecycle`。

### 7.2 Compose

Android Compose UI 推荐使用 `collectAsStateWithLifecycle()`，它把 Flow 最新值转换成 Compose State，并按照 Lifecycle 控制 collection。

```kotlin
@Composable
fun DashboardScreen(viewModel: DashboardViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    DashboardContent(uiState)
}
```

一次 emit 不保证整个 Composable 树都重组，更不保证 composition、measure、layout、draw 四个阶段全部执行。StateFlow 会抑制相等值，Compose 还能依据 state 读取范围、参数稳定性和 skipping 跳过不受影响的代码。

高频输入应按产品语义降低 UI 状态变化：

- 显示连续进度时可用 conflation，但要接受中间状态被覆盖；
- 搜索输入可用 debounce，但延迟值要通过输入体验验证；
- 相等 UI model 可用 `distinctUntilChanged`，StateFlow 本身已有相等合并；
- `sample(16)` 只是 16 ms 时间采样，不与 vsync 对齐，也不适配 90/120 Hz 屏幕；
- 只在滚动越过阈值时更新 UI，可在 Compose 中使用经过测量的 `derivedStateOf`。

## 8. 观测排队、取消与执行线程

Flow 没有向业务公开所有内部 Channel 的实时队列长度。诊断时应在语义边界记录：

- `emitted_at`、`processing_started_at`、`processing_finished_at`；
- 元素序号、相邻序号跳变和业务丢弃计数；
- active request、取消、超时和重试数；
- SharedFlow 的 `subscriptionCount` 与 replay 配置；
- collector 生命周期状态与协程库版本。

下面的自定义 slice 用于测量同步 CPU 转换；名称保持低基数，避免把用户 ID 拼进 trace。

```kotlin
fun decodeWithTrace(packet: Packet): DecodedPacket {
    Trace.beginSection("flow.decode_packet")
    return try {
        decodePacket(packet)
    } finally {
        Trace.endSection()
    }
}
```

这段 slice 只能覆盖同步函数执行时间。跨 suspend 点的阶段要使用 async trace 或请求级指标，不能用一个 thread slice 包住可能在不同线程恢复的协程。

在 Perfetto 中可通过标准 `slice`、`thread_track` 和 `thread` 表找到这些自定义区间。下面的 SQL 按耗时排序应用添加的 `flow.*` slice。

```sql
SELECT
  s.ts,
  s.dur,
  s.name,
  t.name AS thread_name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
WHERE s.name GLOB 'flow.*'
ORDER BY s.dur DESC;
```

Perfetto 不会凭空生成一条包含每个 Flow 操作符的稳定 coroutine track。线程调度轨迹只能说明某线程何时运行；挂起原因、元素身份和丢弃语义需要应用 slice、日志或 metrics 补足。

`kotlinx-coroutines-debug` 的 `DebugProbes` 适合开发和测试环境查看协程栈与 Job 状态，会改变执行和内存行为，不应把开启 probes 后的数字当作 production 基线。操作符成本使用 AndroidX Microbenchmark，页面滚动和重组问题使用 Macrobenchmark、Compose tracing 与 Layout Inspector。

## 9. Android 17 的平台与 kernel 边界

Android 17 AOSP 不实现 `Flow`、`StateFlow` 或 `SharedFlow`。它提供主线程 Looper、Handler、线程调度、Binder 和网络等运行环境；`kotlinx-coroutines-android` 的 Main dispatcher 通过 Handler 把 continuation 调度到 Android 主线程。

可复核的源码锚点包括：

- kotlinx.coroutines 1.11.0 [`Context.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/operators/Context.kt)：`buffer`、`flowOn` 与 Channel fusion。
- kotlinx.coroutines 1.11.0 [`SharedFlow.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/SharedFlow.kt)：replay、缓冲、订阅者与发射路径。
- kotlinx.coroutines 1.11.0 [`StateFlow.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/StateFlow.kt)：相等合并与状态更新。
- kotlinx.coroutines 1.11.0 [`Merge.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/flow/operators/Merge.kt)：flatten/flatMap 并发实现。
- kotlinx.coroutines 1.11.0 [`HandlerDispatcher.kt`](https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/ui/kotlinx-coroutines-android/src/HandlerDispatcher.kt)：Android Main dispatcher 与 Handler。
- AOSP `android-17.0.0_r1` [`Looper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Looper.java)：主线程消息循环。
- kernel `android17-6.18-2026-06_r6` [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c)：线程成为 runnable 后的通用调度机制。

kernel scheduler 不理解 Flow 元素、Channel 容量或 conflation。Perfetto 中看到线程切换，只能证明 continuation 所在线程被调度；背压策略仍要回到库源码和业务观测解释。

## 10. 检查清单

- 数据是否允许丢弃、覆盖、取消或乱序？
- 默认顺序挂起是否已满足需求，是否有证据需要 `buffer`？
- buffer 是否有明确容量，元素体积和最大排队时间是否可估算？
- `conflate`、`debounce`、`sample` 是否改变了业务结果？
- latest 操作取消的代码是否支持协作式取消，远端副作用是否具备幂等保护？
- SharedFlow 无订阅者时的 replay 与丢值行为是否符合预期？
- StateFlow 的值是否不可变并遵守 `equals` 合同？
- `stateIn` / `shareIn` 的 scope 与 `SharingStarted` 是否会在无人订阅时持续占资源？
- `flatMapMerge` 并发度是否受服务端、连接池、CPU 和内存上限约束？
- `flowOn` 是否放在需要迁移的操作符下方，是否引入了多余 Channel？
- View 是否用 `repeatOnLifecycle`，Compose 是否用 `collectAsStateWithLifecycle`？
- 性能结论是否来自目标版本、release 构建和真实元素负载，而不是固定经验数字？

## 参考资料

- [Kotlin Flow 指南](https://kotlinlang.org/docs/coroutines-flow.html)
- [Flow API 与 context preservation](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-flow/)
- [`buffer` API 与 operator fusion](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/buffer.html)
- [`conflate` API](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/conflate.html)
- [StateFlow API 与实现说明](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-state-flow/)
- [SharedFlow API 与缓冲语义](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-shared-flow/)
- [`flowOn` API](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/flow-on.html)
- [Android View 的 lifecycle-aware collection](https://developer.android.com/topic/libraries/architecture/views/coroutines-views)
- [Compose 收集 Flow](https://developer.android.com/develop/ui/compose/state)
- [Android 性能基准测试概览](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)

## 交叉引用

- [**8.6 Kotlin Coroutine 性能实践**](06-coroutine-performance.md)：dispatcher、结构化并发与取消。
- [**5.8 JobScheduler/WorkManager 调度与后台任务性能**](../../part1-fundamentals/ch05-cpu-power/08-jobscheduler-workmanager-performance.md)：进程内异步工作与系统持久化后台任务的边界。
- [**7.7 Jetpack Compose 性能优化**](../ch07-smoothness/07-compose-performance.md)：重组、布局和绘制阶段的观测。
