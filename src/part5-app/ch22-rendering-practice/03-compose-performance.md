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
last_task6_at: "2026-06-22T02:07:00+08:00"
task9_state: reviewed
last_task2b_at: "2026-06-02T12:54:00+08:00"
last_task2b_lite_at: "2026-05-31T15:35:00+08:00"
task6_result: pass-light-edit
task9_result: pass-tech-review
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-22"
last_task9_at: "2026-06-21T22:30:33+08:00"
last_task9_review_log: "logs/deep-review/2026-06-21-22-audit.md"
task9_review_notes: "2026-06-02 Task9 deep-review: pass-tech-review。复核 Strong Skipping、Pausable Composition、LazyLayoutCacheWindow 与 Android 17/Compose 工具链边界，无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 2026-06-21 Task9 idle audit auto-fix: 修正 produceState Snapshot 写入链路中不存在的 registerMutableSnapshot/notifyReaders/scheduleRevalidation 方法名，收窄 Strong Skipping 报告检查与 produceState key 重载边界；P0/P1=1/0，回到 Task6 复审。"
last_task6_review_log: "logs/review/2026-06-22-02-review.md"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-22"
review_notes: "2026-06-02 13:05 Task6 复审：L1 小修 10 处；修正 AndroidX 源码锚点格式与中英文混排，未发现新增回炉项。 2026-06-22 Task6 revisiting 复审：Task9 idle audit 修复 produceState 方法名后回审；L1/L2 全部通过，无新增问题；task9_result 确认 pass-tech-review；task6 无 B 类问题且 queue 无 pending，自动晋升 finalized。"
task2b_notes: "2026-06-02 Task2B：删除发布正文中的调研补遗块，统一 Pausable Composition 为 Compose/Foundation 工具链能力，移出未闭合的 AOSP master/androidx-main 正文结论。"
last_task2b_verifier_at: "2026-06-02T19:27:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-02-19-task2b-verifier.md"
last_task9_autofix_at: "2026-06-21"
task9_p0_issues: 1
task9_p1_issues: 0
task9_p2_issues: 2
last_task9_audit: "2026-07-12"
last_task9_audit_at: "2026-07-12T02:29:38+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-12-02-audit.md"
last_task9_audit_result: "pass-idle-audit"
last_task9_audit_notes: "idle audit: 维度1（源码引用准确性）和维度3（版本差异覆盖）复核通过；AndroidX androidx-compose-release 中 PausableComposition/ProduceState/SnapshotState/LazyLayoutCacheWindow 路径可核，官方 Strong Skipping 与 Compose Foundation 1.10.0-alpha05/1.10.6 release notes 口径一致，AOSP android-17.0.0_r1 ART generational GC 锚点可核；未发现 Android 18/API 38+ 或 P0/P1。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-26
---
# Jetpack Compose 性能优化实战

Compose 性能优化要回答两个问题：哪一段工作错过了本帧 deadline，以及哪些状态或输入让这段工作重复发生。只统计重组次数，容易漏掉 Layout、Drawing、RenderThread 和显示系统；只看整帧耗时，又无法定位到具体 Composable。

版本基线固定为三组：

- Android 平台以 Android 17 / API 37 / `android-17.0.0_r1` 为源码锚点，kernel 以 `android17-6.18-2026-06_r6` 为锚点。
- Compose 依赖以 BOM `2025.12.00` 为基线。该 BOM 把 Runtime、Foundation 和 UI 固定到 `1.10.0`。
- Compose Compiler 随 Kotlin 2.2 Gradle plugin 使用。Strong Skipping 属于编译器行为，Lazy 预取属于 Foundation 行为，两者都不能从 Android platform tag 推断。

普通 `ComposeView` 不会单独创建 Surface。内容仍由当前 App Window 的 HWUI 路径输出：UI 线程完成 Composition、Layout、Drawing 记录，经 `HardwareRenderer.syncAndDrawFrame()` 交给 RenderThread，随后经过 BLAST、SurfaceFlinger、HWC 和 present。页面嵌入 `SurfaceView`、`TextureView`、WebView 或视频组件后，要按对应 Producer 和 layer 重新分类。完整管线可结合 [Compose 渲染管线架构](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md) 阅读。

## 从状态读取阶段控制工作范围

Compose 把 UI 更新分成 Composition、Layout 和 Drawing 三个阶段。状态在哪个阶段被读取，运行时就在哪个阶段记录依赖；状态变化后，从对应 restart scope 开始执行必要工作。

| 读取位置 | 状态变化后的起点 | 适合的变化 |
| --- | --- | --- |
| Composable body 或参数构造 | Composition，结果变化时还会进入 Layout / Drawing | 节点增删、文本内容、布局结构 |
| measure / placement lambda | Layout；placement 与 measurement 还有独立的 restart scope | 位置、约束内尺寸、对齐 |
| draw lambda 或 layer property lambda | Drawing 或图层属性更新 | 颜色、透明度、绘制偏移、缩放 |

这张表描述失效起点，不代表后续阶段必然执行。Composition 的输出没有改变时，Layout 和 Drawing 仍可跳过。`LazyColumn`、`BoxWithConstraints` 和 `SubcomposeLayout` 会在布局过程中决定子内容，不能套用“Composition 总在 Layout 之前一次完成”的简化模型。

下面的示例把滚动偏移推迟到 placement lambda 中读取，并把透明度放进 `graphicsLayer` 的属性 lambda。两个高频值都不再由 Composable body 解包。

```kotlin
@Composable
fun ParallaxHeader(
    listState: LazyListState,
    alpha: State<Float>,
) {
    Image(
        painter = painterResource(R.drawable.header),
        contentDescription = null,
        modifier = Modifier
            .offset {
                IntOffset(
                    x = 0,
                    y = listState.firstVisibleItemScrollOffset / 2,
                )
            }
            .graphicsLayer {
                this.alpha = alpha.value
            },
    )
}
```

`offset { ... }` 的状态读取发生在 placement 阶段，`graphicsLayer { ... }` 的读取用于更新图层属性。若位置变化会改变兄弟节点的测量约束，仍应使用能表达该约束关系的布局；视觉平移不能冒充布局位置。

状态影响节点数量、文本或语义属性时，Composition 无法省略。优化方向是缩小读取范围：把状态传成 lambda、把读取移到较低层的 Composable，或把一个过大的重组作用域拆成有清晰输入的子函数。

## Strong Skipping 与 Stability

### 跳过条件要分函数和参数

Kotlin 2.0.20 起默认启用 Strong Skipping。这里使用 Kotlin 2.2，无需再设置 `enableStrongSkippingMode`。它改变两项编译结果：

- 所有 restartable Composable 默认可标记为 skippable；non-restartable 函数仍不可跳过，`@NonSkippableComposable` 可以显式退出。
- Composable 内部创建的 lambda 会自动 memoize。捕获值用作缓存 key；stable 捕获值按 `equals()` 比较，unstable 捕获值按 `===` 比较。`@DontMemoize` 可以让某个 lambda 退出自动缓存。

进入重组时，skippable 函数还要比较本次与上次参数。Stable 参数使用 `equals()`，unstable 参数使用实例相等。参数相等只解决父级执行传播；函数内部读取的 Snapshot state 或动态 `CompositionLocal` 发生变化时，对应重组作用域仍会失效。

Strong Skipping 没有让 Stability 失去作用。它决定参数采用哪种比较方式，也约束可变对象如何通知 Compose：

- 普通 `List`、`Set`、`Map` 接口仍被编译器视为 unstable。同一个可变集合实例原地修改时，实例比较可能让调用被跳过，集合本身也不会发送 Snapshot 通知。
- `SnapshotStateList`、`SnapshotStateMap` 能通知运行时；不可变 UI model 配合新集合实例，则能提供清晰的新旧快照。
- `@Stable` 与 `@Immutable` 是开发者向编译器作出的契约。对象含有不可观察的可变字段时不能标注；错误契约可能让 UI 漏掉更新。
- 手写 `remember` lambda 可能包含特定 key 或生命周期语义，不能只因升级 Kotlin 就批量删除。应对照编译器生成规则和调用方需求逐处确认。

### 用编译器报告验证推断

编译器报告适合回答“这个函数怎样被编译”和“哪个类型被判定为 unstable”，不能单独证明某次卡顿由 Stability 引起。下面的 Gradle 配置用于 Kotlin 2.x Compose Compiler plugin。

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

应在 release variant 上生成报告。`reportsDestination` 输出 `*-classes.txt`、`*-composables.txt` 和 `*-composables.csv`；`metricsDestination` 另行输出模块统计。Strong Skipping 开启后，`restartable` 函数通常也会显示 `skippable`，因此还要检查参数比较、状态读取位置和现场重组次数。追求“全模块全部 skippable”会增加错误标注和维护成本。

## `remember`、`derivedStateOf` 与副作用

### `remember` 缓存一次计算，不负责数据一致性

`remember(keys...)` 在 key 保持相等时复用缓存值，key 变化时丢弃旧值并重新计算。它适合缓存排序结果、状态容器和创建成本较高的对象，但输入必须能表达一份稳定快照。

下面的写法假定 `items` 是不可变列表，数据更新时会提交新实例。

```kotlin
@Composable
fun SortedFeed(items: List<FeedItem>) {
    val sortedItems = remember(items) {
        items.sortedByDescending(FeedItem::timestamp)
    }

    LazyColumn {
        items(
            items = sortedItems,
            key = FeedItem::id,
            contentType = FeedItem::type,
        ) { item ->
            FeedRow(item)
        }
    }
}
```

如果调用方原地修改同一个普通列表，`remember(items)` 不会重新排序，Lazy 列表也拿不到可靠的新旧输入。修复点在数据所有权和可观察性，不在增加更多 `remember`。

### `derivedStateOf` 只处理输入、输出频率不匹配

`derivedStateOf` 适合把高频输入收敛为低频结果，例如滚动位置持续变化，而按钮只在跨过阈值时切换可见性。它会建立派生状态和依赖跟踪，本身有成本。

下面的示例只在“是否越过首项”改变时更新读取者。

```kotlin
@Composable
fun FeedWithScrollToTop(items: List<FeedItem>) {
    val listState = rememberLazyListState()
    val showScrollToTop by remember {
        derivedStateOf {
            listState.firstVisibleItemIndex > 0
        }
    }

    Box {
        LazyColumn(state = listState) {
            items(items, key = FeedItem::id) { item ->
                FeedRow(item)
            }
        }
        AnimatedVisibility(showScrollToTop) {
            ScrollToTopButton()
        }
    }
}
```

字符串拼接、数值乘法这类“输入每次变，输出也每次变”的表达式不需要 `derivedStateOf`。直接计算通常更清楚，运行时工作也更少。

### `rememberCoroutineScope` 面向事件，`produceState` 面向外部数据

`rememberCoroutineScope()` 返回与调用点 Composition 生命周期绑定的 scope，调用点离开 Composition 后 scope 会取消。它适合点击、拖动结束、Snackbar 等事件回调。不要在 Composable body 中直接 `launch`；每次函数执行都可能启动新任务。

`produceState` 用协程把外部数据转成 Compose `State`。Compose Runtime 1.10.0 的带 key 重载使用 `remember { mutableStateOf(initialValue) }` 保存结果，并用 `LaunchedEffect(key)` 运行 producer。key 变化会取消旧 producer 并启动新 producer，离开 Composition 也会取消。返回的 `State` 会合并相等值；连续快速写入时，观察者可能只读到较新的值。

下面的示例把用户 ID 和 repository 都作为 producer 的身份输入。

```kotlin
@Composable
fun userProfile(
    userId: String,
    repository: UserRepository,
): State<User?> {
    return produceState(
        initialValue = null,
        userId,
        repository,
    ) {
        value = repository.load(userId)
    }
}
```

缺少 key 会让 producer 继续使用旧输入；塞入每次重组都变化的 key 又会反复取消请求。非挂起订阅可在 producer 中注册，并用 `awaitDispose` 解除。高频且每次都不同的数据仍可能使读取者频繁失效，应在数据源侧采样、聚合，或把仅影响绘制的读取延迟到 Drawing。`snapshotFlow` 的方向是把 Compose Snapshot state 转成 Flow，它不能替代外部高频数据到 UI state 的节流。

Strong Skipping 不管理 producer 协程。跳过规则作用于 Composable 调用，协程的启动、取消和异常处理仍由 Effect key 与 scope 生命周期决定。

## Lazy 列表：身份、类型与预取

### `key` 保持 item 身份，`contentType` 约束复用兼容性

Lazy 列表未提供业务 key 时按位置维护身份；显式使用 index 基本等同于位置身份。列表头部插入或中间删除后，位置后的 item 会换身份，`remember` / `rememberSaveable` 状态和组合复用都可能受到影响。

业务 key 应稳定且唯一。item 使用 `rememberSaveable` 时，key 还要满足 Android `Bundle` 可保存类型的要求。`contentType` 用于告诉 Lazy layout 哪些 item 的组合结构可以复用；广告、标题、普通卡片结构不同，就应使用不同类型。

列表 body 中还要避免排序、过滤、日期格式化、同步图片解码和阻塞 I/O。把纯计算移到上游或以不可变输入为 key 缓存，把 I/O 放进 repository 和异步加载组件。

### Pausable Composition 的边界

Compose Runtime 1.10.0 提供 `PausableComposition`，Foundation 1.10.0 在 Lazy 预取中默认打开 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled`。源码路径可以拆成四步：

1. Android 端 `AndroidPrefetchScheduler` 通过宿主 View 的 `post()` 在 UI 线程执行请求，并用 drawing time、`Choreographer` frame time 与刷新周期计算剩余时间。
2. Lazy prefetch 为目标 index 安排预组合和预测量；普通请求参考同 `contentType` 的历史耗时，urgent 请求只要求本帧仍有剩余时间。
3. flag 开启时，预组合调用 `PausedComposition.resume(shouldPause)`。暂停请求只在可暂停点生效，不保证每次回调返回 `true` 都立即停下。
4. 组合完成后单独 `apply()`，再按约束执行 premeasure。Pausable Composition 只切分预组合，不能把 apply、measure 或已进入可见窗口的同步工作一并切开。

Foundation `1.10.6` 的发布说明记录了一个后续变化：因稳定性问题，该 flag 默认关闭。使用 BOM `2025.12.00` 时是 Foundation `1.10.0` 的默认值；升级补丁版本后必须重新核对依赖解析结果和 flag，不能用“Compose 1.10”概括所有补丁版本。

这项能力没有覆盖普通首帧 Composition、常规重组或非 Lazy 子树。拆分重组作用域、降低 item 组合成本、提供稳定 key 和控制状态读取范围仍然有效。

### `LazyLayoutCacheWindow` 同时控制 ahead 与 behind

Foundation 1.10.0 的 `LazyLayoutCacheWindow` 仍是实验 API。ahead window 用于准备滚动方向前方的 item，behind window 用于保留反方向窗口内已经准备好的 item。窗口增大会增加预组合、预测量和保留节点的成本，不能按“越大越顺”设置。

下面的配置只用于展示 API 形态，比例需要在目标页面和目标设备上测量后确定。

```kotlin
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TunedFeed(items: List<FeedItem>) {
    val listState = rememberLazyListState(
        cacheWindow = LazyLayoutCacheWindow(
            aheadFraction = 0.75f,
            behindFraction = 0.25f,
        ),
    )

    LazyColumn(state = listState) {
        items(
            items = items,
            key = FeedItem::id,
            contentType = FeedItem::type,
        ) { item ->
            FeedRow(item)
        }
    }
}
```

调参时同时观察 `compose:lazy:prefetch:compose`、`compose:lazy:prefetch:apply`、`compose:lazy:prefetch:measure`、目标 item 首次可见帧成本和内存峰值。只有预取工作前移且后续关键帧变轻，才能说明窗口设置有收益。预取 slice 增加、关键帧不变或内存明显上升，通常说明窗口过大、命中不准或 item 工作仍在可见帧发生。

## 工具：从重组证据走到屏幕 present

### Layout Inspector、Composition Tracing 与 Macrobenchmark 分工

- Layout Inspector 的重组与跳过计数适合确认失效范围。Debug 构建和 Inspector 本身会改变耗时，不能把它的时间数据当作线上帧基线。
- Compose compiler report 适合核对 restartable、skippable 和 Stability 推断，不能显示运行时哪一帧发生了什么。
- Composition Tracing 能把单个 Composable 记录进 system trace。系统 trace 默认没有这些细粒度 slice；项目要加入 `androidx.compose.runtime:runtime-tracing`，终端自定义 Perfetto 配置还要启用 `track_event`。
- Macrobenchmark 应运行 profileable、non-debuggable 的 release-like 构建，覆盖冷启动、首屏、稳定滚动和主要交互。升级 Compose 后重新采集 Baseline Profile，并用相同设备状态、刷新率和数据集建立新基线。

下面的依赖写法让 BOM 决定 runtime-tracing 的版本。

```kotlin
val composeBom = platform("androidx.compose:compose-bom:2025.12.00")
implementation(composeBom)
implementation("androidx.compose.runtime:runtime-tracing")
```

依赖加入后仍要确认被测 APK 保留 tracing 支持，并使用适合性能测量的构建。自定义 trace 没有 `track_event` data source 时，不能因为搜索不到 Composable 名就断言没有重组。

### Perfetto 按四个关口收敛

1. **Composition**：目标状态写入后，哪些 restart scope 被 invalidated；函数是否因参数或内部 state 重新执行；Lazy 预取是否把目标 item 的 compose / apply 前移。
2. **Layout 与 Drawing**：Composition 正常时，检查 measure、placement、draw、图层更新和 `requestLayout()` / invalidation 的来源。Lazy item 在 precompose 后仍可能把 premeasure 或可见布局成本留给后续帧。
3. **HWUI 与 buffer 提交**：UI 线程按时完成后，检查 `syncAndDrawFrame()`、RenderThread `DrawFrame`、dequeue、GPU 工作和 `queueBuffer()`。
4. **显示出口**：用目标 App Window 的 FrameTimeline、`BufferTX - <layerName>`、latch、SurfaceFlinger actual timeline、HWC composition 与 present timing 判断 App 之后的延迟。

刷新率决定单帧预算，不能把 `16.67 ms` 或任意一条固定毫秒线套到所有设备。Compose slice 变短也不等于屏幕更早显示；比较应闭合到同一帧的 actual present。

## Compose 与 View 互操作

### RecyclerView 中的 `ComposeView`

Compose UI 1.10.0 的默认 `ViewCompositionStrategy` 是 `DisposeOnDetachedFromWindowOrReleasedFromPool`。不在 pooling container 中时，View detach 会销毁 Composition；位于 RecyclerView 等 pooling container 时，临时 detach 不会立即销毁，容器 detach 或 item 被池丢弃时才释放。

ViewHolder 中应让 `setContent()` 只执行一次，再用可观察状态完成 bind。下面的 `key(model.id)` 用于把 item 身份切换显式告诉 Composition，避免 holder 复用时把 `remember` 状态带给另一条数据。

```kotlin
class ComposeItemHolder(
    context: Context,
) : RecyclerView.ViewHolder(ComposeView(context)) {
    private val composeView = itemView as ComposeView
    private var model by mutableStateOf<FeedItem?>(null)

    init {
        composeView.setContent {
            model?.let { current ->
                key(current.id) {
                    FeedRow(current)
                }
            }
        }
    }

    fun bind(value: FeedItem) {
        model = value
    }

    fun clear() {
        model = null
    }
}
```

`onViewRecycled()` 可以清空业务数据和外部资源，不应无条件调用 `disposeComposition()`；默认策略保留池内 Composition 是为了复用。Fragment XML 中的一对一 `ComposeView` 更适合 `DisposeOnViewTreeLifecycleDestroyed`，它绑定下一次 attach 所在 View tree 的 `LifecycleOwner`。

### Lazy 列表中的 `AndroidView`

`AndroidView.factory` 在 UI 线程创建 View，并且对当前实例只调用一次；`update` 会在 factory 后调用，也会随其中读取的 State 变化而再次运行。重操作不能塞进 `update`，但 View 属性修改仍应留在 UI 线程。

Lazy 列表中要使用带非空 `onReset` 的重载才能启用兼容 View 实例复用。下面的例子在复用前清理瞬时状态，并在永久离开 Composition 时释放资源。

```kotlin
LazyColumn {
    items(
        items = charts,
        key = ChartModel::id,
    ) { model ->
        AndroidView(
            factory = { context -> ChartView(context) },
            update = { view -> view.render(model) },
            onReset = { view -> view.resetForReuse() },
            onRelease = { view -> view.release() },
        )
    }
}
```

`onReset` 可能先于下一次 `update`，也可能进入暂时停用后才被释放；清理逻辑应允许重复调用。若嵌入的是 `SurfaceView`、WebView、播放器或相机预览，图形分析还要跟随它自己的 BufferQueue 和 SurfaceFlinger layer，不能只看 Compose 宿主窗口。

## 升级与验收

升级 Kotlin 或 Compose 时，先记录解析后的精确依赖。下面的命令用于确认 app 的 Runtime、Foundation 和 UI 版本，configuration 名按项目 variant 调整。

```bash
./gradlew :app:dependencyInsight \
  --dependency androidx.compose.runtime:runtime \
  --configuration releaseRuntimeClasspath

./gradlew :app:dependencyInsight \
  --dependency androidx.compose.foundation:foundation \
  --configuration releaseRuntimeClasspath

./gradlew :app:dependencyInsight \
  --dependency androidx.compose.ui:ui \
  --configuration releaseRuntimeClasspath
```

BOM 只约束它声明的 Compose artifacts，不会安装依赖，也不控制 Kotlin plugin。版本确认后再做同机对比，避免把 Kotlin 编译器、Foundation 预取、Baseline Profile 或业务代码的变化混成一个结果。

验收可以按下面的顺序执行：

1. 用 compiler report 确认目标 Composable 的 restartable / skippable 与参数 Stability，不为无性能问题的类型追加注解。
2. 用 Layout Inspector 复现一次状态变化，确认重组和跳过范围符合预期。
3. 用 Macrobenchmark 采集 release-like 构建，比较 FrameTiming、启动、内存和目标交互的分位数。
4. 用 Composition Tracing 关联目标 Composable、Lazy prefetch、Layout、Drawing 与同一帧 `Choreographer#doFrame`。
5. 沿 RenderThread、BLAST、SurfaceFlinger、HWC 到 actual present 闭合显示链，区分 App 生产慢与系统显示慢。
6. 升级 Compose 后重新生成并验证应用 Baseline Profile；库自带 profile 不能覆盖业务 Composable 的完整热点路径。

| 现象 | 优先验证 | 常见误判 |
| --- | --- | --- |
| 小状态变化引发大范围重组 | 状态读取位置、restart scope、参数实例 | 只给所有 model 加 `@Stable` |
| 动画期间 Composition 持续出现 | 状态是否可延迟到 placement / drawing | 把每次变化都包进 `derivedStateOf` |
| Lazy 滚动进入新 item 时卡顿 | key、contentType、compose / apply / measure 预取 | 只把 cache window 调大 |
| `ComposeView` 列表反复创建 | `setContent()` 次数、pool strategy、item 身份 | 每次回收都 dispose |
| UI 线程正常仍有 jank | RenderThread、buffer、SF、HWC、present | 把所有慢帧归到重组 |

## 源码与文档

- [Compose BOM `2025.12.00` POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2025.12.00/compose-bom-2025.12.00.pom)：核对 Runtime、Foundation 与 UI 的 `1.10.0` 映射。
- [Compose Runtime 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/runtime/runtime/1.10.0/runtime-1.10.0-sources.jar)：`PausableComposition`、`ProduceState`、`DerivedState` 与 Snapshot state。
- [Compose Foundation 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/1.10.0/foundation-1.10.0-sources.jar) 与 [Android source jar](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation-android/1.10.0/foundation-android-1.10.0-sources.jar)：Lazy cache window、预取状态与 Android 调度器。
- [Compose UI Android 1.10.0 source jar](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.10.0/ui-android-1.10.0-sources.jar)：`ComposeView`、`ViewCompositionStrategy` 与 `AndroidView`。
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)、[Compose phases](https://developer.android.com/develop/ui/compose/phases) 与 [Side-effects](https://developer.android.com/develop/ui/compose/side-effects)：编译器跳过、状态读取阶段和 Effect 契约。
- [Diagnose stability issues](https://developer.android.com/develop/ui/compose/performance/stability/diagnose) 与 [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)：编译器报告、重组计数与 system trace 配置。
- [Compose Foundation release notes](https://developer.android.com/jetpack/androidx/releases/compose-foundation#1.10.6)：Pausable Composition flag 在 `1.10.6` 的默认值变化。
- [Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views) 与 [Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)：pooling container、Fragment 生命周期和 `AndroidView` 复用。
- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java) 与 [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：平台帧调度与 App Window traversal 基线。
