---
title: "Jetpack Compose 动画性能深度优化"
chapter: "22.21"
section: "22.21"
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
related_chapters: ["22.3", "22.5", "22.20", "7.7", "2.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "研究素材"
drafted_date: "2026-06-05"
---

# 22.21 Jetpack Compose 动画性能深度优化

Compose 动画的三层管线（状态驱动 → 重组/重绘 → 帧信号同步）与 View 动画的区别不在 API 表面，而在每帧工作的触发路径。本节从源码层面拆解 `AnimatedVisibility`、`Transition`、`Animatable`、`produceState` 在动画场景中的性能行为，给出可观测的优化判断依据。Compose 渲染管线的机制背景见 2.11 节；Compose 重组控制和 Strong Skipping 基础见 22.3 节；View 属性动画和帧动画的对比见 22.5 节。

本节使用 **Compose BOM 2025.12.00（对应 Compose 1.10）** 作为版本基线。Strong Skipping、Pausable Composition、`derivedStateOf` 的 `readableHash` 优化都取决于项目引入的 Compose 版本，不由 Android 平台版本决定。

## AnimatedVisibility：双重重绘与退出延迟

`AnimatedVisibility` 的入口是一个 `updateTransition(visible, label)` 调用。源码 `AnimatedVisibility.kt` 第 102 行把这个调用包装进一个 `Layout` Composable，measure policy 遍历所有子元素取最大宽高。[已验证: AndroidX androidx-main, androidx.compose.animation/AnimatedVisibility.kt]

动画期间 Layout 的每一帧尺寸都在变化（从 0 到目标尺寸，或反过来）。如果父容器使用 `wrap_content`，每一帧尺寸变化都会触发父容器重测。这不是 AnimatedVisibility 的 bug，是 `Layout` 在动画期间动态尺寸与父容器布局协议的组合结果。修复方式是在外层加固定尺寸或 `clip`，限制尺寸传播范围。

退出动画是另一个性能陷阱。`AnimatedVisibility` 的退出语义是：exit 动画全部完成后，content 才从 Composition 中移除。即使 `visible=false` 已设置，只要有 exit 动画在播，content Composable 仍在树中保持活跃。两个后果：

1. content 在退出期间仍然是重组参与者。如果 content 内有高频状态读取，退出动画期间的重组成本不会因为 `visible=false` 而消失。
2. content 内的副作用和订阅在退出期间不会清理。`LaunchedEffect`、`rememberCoroutineScope` 启动的协程、`DisposableEffect` 的 onDispose 都要等到动画结束。

快速 toggling `visible`（比如用户快速点一个展开/收起按钮）会加剧这个问题。每次 toggle 都会中断当前动画重启新动画，帧预算被动画重启消耗。处理方式是用 `MutableTransitionState` 替代 boolean `visible`，手动控制状态机，或在外层做 debounce。

## Transition 状态机与非重启式组合

`Transition` 是 `AnimatedVisibility` 的底层状态机。`updateTransition(targetState, label)` 的语义是：在同一 Composable 位置复用已有的 Transition 实例，而不是每次重组创建新实例。状态机的状态转换发生在 `MutableTransitionState`，通过 Snapshot 系统广播给订阅者。[已验证: AndroidX androidx-main, Compose Runtime]

这意味着 Transition 是**非重启式组合**。它不会因为参数变化而重新执行 Composable 函数体，而是通过 Snapshot 通知机制更新内部状态。这是 Transition 可以协调多个子动画的基础——所有子动画订阅同一个状态源，由 Transition 统一管理帧进度。

动画时钟方面，Transition 内部的动画运行在 Compose 的 `AnimationClock` 上。这个时钟与 `Choreographer` 帧信号有关联但不是同一套。Transition 在一帧内可以协调多个子动画的进度计算，但进度到帧的映射取决于 `AnimationClock` 的 tick 频率。如果主线程被阻塞导致帧丢失，Transition 的动画进度仍然按时间推进，不会等帧信号。这对动画流畅性是好事（不会因为掉帧而暂停），但排查时要注意：Perfetto 里看到的帧间隔和动画进度曲线可能不完全同步。

## Animatable：不触发重组的动画驱动

`Animatable<T>` 是单值动画状态持有者。`animateTo(target)` 在协程中运行，每一帧更新内部值，但**不触发重组**——只触发重绘（Draw 阶段）。

这背后的机制是 `SnapshotStateObserver` 的三阶段失效。`Animatable` 的值变化通过 Drawing 阶段的 `Modifier.drawWithContent` 读取，Drawing 阶段使用 `withoutReadObservation()` 暂停读观察。状态读取不建立 Composition 阶段的订阅关系，变更只 invalidate 图形层，完全跳过 Composition 和 Layout。[已验证: AndroidX androidx-main, SnapshotStateObserver.kt]

`Animatable` 与 `Transition` 的选型区别：

| 维度 | Animatable | Transition / AnimatedVisibility |
|------|-----------|-------------------------------|
| 触发阶段 | Draw only | Composition + Layout + Draw |
| 状态管理 | 单值，手动控制 | 状态机，自动管理 |
| 适用场景 | 精密动画、手势跟随、Canvas 绘制 | 出现/消失、多属性协调动画 |
| 重组风险 | 无 | 退出期间内容仍参与重组 |

手势跟随动画优先用 `Animatable`。手势的每一帧都更新目标值，`animateTo` 的协程会在每帧 snap 到新目标，全程不触发重组。如果用手势驱动 `Transition`，状态机的 MutableTransitionState 每帧变化会触发 Composition 阶段的快照广播，重组范围可能扩大。

## produceState 在动画场景中的陷阱

`produceState` 内部使用 `LaunchedEffect(Unit)` 启动协程，key 固定为 `Unit`。Composable 在同一位置重组时 producer 不会重启。但 producer 内每次 `state.value = newValue` 都触发 Snapshot 写事务，通知所有 State 观察者。[已验证: AndroidX androidx-main, androidx.compose.runtime/produceState.kt]

在动画场景中，这个行为会放大：60fps 动画 + produceState 状态驱动 = 每帧一次 Snapshot 写事务 + 重组范围评估。如果动画元素在列表中，O(n) 的重组传播会导致帧超时。

produceState 的设计意图是"异步数据源到 Compose State 的桥接"（网络请求、数据库查询、回调转 State），不是"驱动 UI 动画"。动画状态驱动应该用：

- `animateFloatAsState` / `animateDpAsState` 等声明式动画 API，内部使用 `Animatable` 且优化了帧同步
- `Animatable` + `LaunchedEffect` 手动控制动画进度
- `snapshotFlow` 将高频动画状态转成 Flow，在 Flow 侧做 debounce/throttle 后再驱动 UI

produceState 在动画场景中的替代方案可以压成一个判断：如果状态更新频率接近或超过帧率，不用 produceState。

## AnimatedVisibility vs AnimatedContent

这两个 API 处理内容切换的方式不同，对帧预算的影响也不同。

**AnimatedVisibility**：exit 动画全部完成后内容才从 Composition 移除。退出期间 content 仍参与重组，尺寸动画会传播到父/兄弟。

**AnimatedContent**：内容切换时立即替换 Composition 中的内容。旧的退出动画和新内容的进入动画同时进行，但旧内容不在 Composition 树中（由 `AnimatedContent` 内部管理独立的动画层）。重组风险低，因为活跃的 Composition 内容只有新内容。

列表场景中的选型：`AnimatedContent` 更适合列表项的内容切换（如列表项展开/收起时内容整体替换）；`AnimatedVisibility` 适合浮层、菜单、tooltip 这类内容不变只是出现/消失的场景。如果 AnimatedVisibility 的 content 很复杂，考虑用 `animateEnterExit` 拆分动画单元，减少退出期间活跃内容对帧预算的占用。

## Strong Skipping 对动画代码的影响

Compose Compiler 1.10+ 的 Strong Skipping 改变了 Composable 的跳过判断逻辑。对于动画相关的 Composable，影响集中在两个地方。

**Lambda 捕获的稳定性要求**。Strong Skipping 自动 memoize 所有 lambda 参数，但 memoize 的复用条件是"捕获值没变"。动画 Composable 中常见的模式是 lambda 捕获动画状态值（如 `offset`、`progress`），这些值每帧变化，导致 memoize 的 lambda 每帧都是新对象，下游 Composable 无法跳过。处理方式是把动画值作为 Composable 的正式参数传入，而不是通过 lambda 捕获。

**`rememberCoroutineScope` / `produceState` 在 Strong Skipping 下的行为**。Strong Skipping 触发 `skipToGroupEnd()` 时，group 内的 RememberObserverHolder 被标记为停用，协程被暂停。如果动画 Composable 的参数未变化但内部有活跃协程，Strong Skipping 的 skip 不会取消这些协程，只是跳过函数体执行。这是安全的（协程在 Composable 离开 Composition 时才会被 cancel），但要理解 skip 期间动画协程仍在运行——如果协程在更新 Compose 状态，状态更新会排队等下次 Composition 处理。

Strong Skipping 对动画代码的优化策略：把动画驱动的 Composable 标记为非 restartable（如果动画不需要被父级重启），让编译器使用 `startReplaceGroup` 而非 `startRestartGroup`，减少 group 管理开销。这需要在编译器插件层面配置，不是运行时 API。大多数场景下 Strong Skipping 的默认行为已经足够，只在极端场景（数百个动画 Composable 同时运行）才需要考虑 group 类型优化。

## 动画帧预算与 Perfetto 观测

Compose 动画的帧预算和 View 动画相同：16.6ms（60Hz）或 8.3ms（120Hz）。区别在于 Compose 动画的帧工作分布在 Composition、Layout、Draw 三个阶段，需要分别看。

Perfetto 中识别 Compose 动画帧延迟的入口：

1. **Compose Tracing（Android 12+）**：Perfetto 中的 `Compose` 轨道显示重组计数和跳过计数。动画运行期间如果重组计数每帧都在增长，说明动画触发了不必要的重组。
2. **Choreographer 轨道**：`Choreographer#doFrame` slice 的持续时间就是帧总耗时。动画场景下如果 doFrame 超出帧预算，先看是 Composition、Layout 还是 Draw 占大头。
3. **FrameMetrics**：`FrameMetrics.ANIMATION_DURATION` 可以区分动画帧和非动画帧的延迟。线上监控用 FrameMetrics 分位值判断动画卡顿范围。

定位动画导致的帧超时的排查顺序：

1. 确认帧超时发生在哪个阶段（Composition / Layout / Draw）
2. 如果 Composition 阶段超时：检查动画期间活跃的 Composable 是否过多（AnimatedVisibility 退出延迟是常见原因）
3. 如果 Layout 阶段超时：检查动画是否触发了父容器重测（wrap_content + AnimatedVisibility 尺寸动画）
4. 如果 Draw 阶段超时：检查动画的图形复杂度（路径、阴影、clip）是否超出 GPU 帧预算

## 优化实践清单

### P0 级：必须避免的动画反模式

- **AnimatedVisibility content 内执行高频状态更新**。退出动画期间 content 仍在 Composition 中，高频更新会放大重组成本。
- **快速 toggling visible 不做 debounce**。每次 toggle 中断当前动画重启新动画，帧预算被耗尽。
- **produceState 驱动 UI 动画**。produceState 的 Snapshot 写事务频率接近帧率时，每帧一次重组范围评估。
- **动画期间每帧改 layoutParams / 触发 requestLayout**。这个在 View 动画中也是反模式，Compose 中对应的是动画期间改变 `Modifier.layout` 的测量结果。

### P1 级：推荐优化实践

- **手势跟随动画用 Animatable**。Animatable 只触发 Draw 阶段，不触发 Composition 和 Layout。
- **AnimatedVisibility 配合固定尺寸容器或 clip**。限制尺寸动画的传播范围。
- **用 MutableTransitionState 替代 boolean visible**。手动控制状态机，可以在需要时跳过动画直接切换。
- **动画值作为 Composable 正式参数传入**。不要通过 lambda 捕获动画值，避免 Strong Skipping 的 memoize 失效。
- **列表项内容切换用 AnimatedContent**。避免 AnimatedVisibility 退出期间活跃内容对帧预算的占用。

### P2 级：进阶优化

- **derivedStateOf 做动画值分箱**。`derivedStateOf { scrollOffset / itemHeight }` 把连续的滚动偏移离散化为整数索引，只在索引变化时通知下游。底层机制是 `readableHash` 比较，hash 不变则跳过重组。[已验证: AndroidX androidx-main, DerivedState.kt]
- **Baseline Profile 覆盖常用动画路径**。Compose 动画的编译路径（Strong Skipping 生成的 `skipToGroupEnd`、`Animatable` 的协程调度）可以被 Baseline Profile 预热。
- **Transition 复用**。多个同类型动画共享同一个 Transition 实例，减少状态机创建开销。

## Compose 动画与 View 动画的互操作

`ComposeView` 内嵌 View 动画或 `AndroidView` 内嵌 Compose 动画时，帧预算是共享的。Choreographer 的 `doFrame` 回调会依次处理 View 树和 Compose 树的帧工作。如果 View 侧动画占用了大部分帧预算，Compose 侧的动画就会掉帧；反之亦然。

排查混合栈动画卡顿时，Perfetto 中需要同时看 `Choreographer#doFrame`（View 侧）和 `Compose` 轨道（Compose 侧）的帧耗时占比。不要只看一侧就下结论。

[适用版本: Compose BOM 2025.12.00; Android 12+ 支持 Compose Tracing]

## 大规模列表中的动画策略

`LazyColumn` 中 item 出现/消失动画的帧预算控制要分两层看：

1. **Composition 层**：item 进入视口时创建 Composable，离开时销毁。如果使用 `AnimatedVisibility` 做出现/消失动画，离开视口的 item 在动画结束前不会被销毁，内存和 Composition 开销比无动画版本高。
2. **Draw 层**：列表滚动期间每帧都要绘制可见 items。如果每个 item 都有活跃动画，Draw 阶段的工作量是 O(visible_items × active_animations)。

推荐策略：列表 item 的出现/消失动画用 `animateEnterExit` 限制动画范围，exit 动画时长控制在 200ms 以内。item 内容的持续动画（如进度条、脉动效果）用 `Animatable` + `InfiniteTransition` 驱动，确保只走 Draw 阶段。避免在 `LazyColumn` item 内使用 `AnimatedVisibility` 的完整退出动画——列表滚动时 item 离开视口的速度可能比退出动画完成的速度快，导致大量"正在退出但已经不可见"的 Composable 堆积在 Composition 中。

## 动画 Benchmark 方法

Macrobenchmark 测量 Compose 动画帧率的方法：录制一段包含目标动画的操作（如展开/收起、页面切换），用 `@BenchmarkRule` 的 `measureRepeated` 循环执行。关注 `frameDurationCpuMs` 的 P50/P90/P99 分位值，以及 `jankFrameCount`。

Compose Animation Inspector（Android Studio 的 Layout Inspector 扩展）可以实时显示每个 Composable 的重组频率。动画运行时如果看到某个 Composable 的重组计数异常高，就是优化目标。但 Animation Inspector 只适用于开发调试，不能用于线上监控。

线上监控用 `FrameMetrics` + 自定义 `OnFrameMetricsAvailableListener`，把动画场景的帧时间按 Activity/Fragment/Composable 路径分桶上报。配合 26.3 节的性能指标采集体系，可以建立动画帧率的分位值基线和回归告警。

[待补充: Macrobenchmark 动画测试的具体 TraceConfig 配置和 Compose Animation Inspector 的使用截图]
