---
title: Jetpack Compose 性能优化
chapter: '7.7'
section: '7.7'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-01'
last_verified_against: Android 17 (API 37) / Compose Runtime 1.8.0-1.11.3 source jars
confidence: medium
tags:
- smoothness
- jank
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
sources:
- type: reference
  path: 朱涛·沉思录:如何优化 Compose 的性能(微信公众号)
- type: reference
  path: Android官方文档:Jetpack Compose Performance
---

# 7.7 Jetpack Compose 性能优化

Compose 性能问题不能只用“重组次数多”来解释。一帧可能慢在 Composition（组合）、Layout（布局）、Drawing（绘制），也可能慢在 RenderThread（渲染线程）、GPU、BufferQueue（图形缓冲队列）、SurfaceFlinger（系统合成服务）或显示侧。有效的优化应从慢帧证据出发，再把耗时定位到对应阶段和代码。

平台基线为 Android 17 / API 37 / `android-17.0.0_r1`，内核基线为 `android17-6.18-2026-06_r6`。Compose Runtime（运行时）、UI、Foundation（基础组件库）和 Compiler（编译器）独立于 Android 平台发布；复现实验时还要记录 Kotlin、Compose Compiler、Compose BOM（用于统一 Compose 依赖的版本清单）与各组件版本。Android API level（平台 API 级别）无法说明 Strong Skipping、Lazy 预取或 Runtime 内部机制是否存在。

## 先建立完整的帧模型

### Compose 的三个工作阶段

Compose 把 UI 工作划分为 Composition、Layout 和 Drawing。一次状态写入会触发哪些工作，取决于状态在哪里被读取，以及这次变更是否使节点、尺寸、位置或绘制内容失效。

| 阶段 | 主要工作 | 常见成本 | 可观察线索 |
|---|---|---|---|
| Composition | 执行失效的 restart scope（可单独重新执行的范围），更新运行时 group/slot（调用分组/存储位置）记录，再由 applier（节点变更应用器）更新节点 | 业务计算、对象分配、范围过大的状态读取、频繁子组合 | composition tracing（组合跟踪）、主线程 slice（时间区间）、Compiler 报告 |
| Layout | 测量和放置 `LayoutNode`，处理约束、intrinsic（固有尺寸测量）、subcomposition（布局期间生成内容）、lookahead（预估后续布局）等 | 重复测量、复杂自定义布局、列表 item 测量、尺寸抖动 | 主线程 measure/layout slice、Layout Inspector（布局检查器）、trace |
| Drawing | 生成或更新绘制命令、图层内容与图层属性 | 大范围重录、复杂 path（路径）、阴影、模糊、过度离屏、填充率 | UI 线程 draw、RenderThread、GPU counter（性能计数器）、trace |

这三个阶段可以按需跳过。某个状态只在 draw lambda（绘制回调）中读取时，变更可以只让对应绘制范围失效，无需重新执行 Composition 和 Layout。状态在测量或放置 lambda 中读取时，也可以把更新限制在布局阶段。状态在 composable（可组合）函数体内读取时，失效入口位于 Composition；后续是否还要布局或绘制，由应用变更后的结果决定。

有些组件会在布局期间生成内容，例如读取父约束的 `BoxWithConstraints`、支持子组合的 `SubcomposeLayout` 和 Lazy 容器。因此，三个阶段并不总是互不交叉的直线流程。Compose 官方的[运行阶段说明](https://developer.android.com/develop/ui/compose/phases)和[性能阶段说明](https://developer.android.com/develop/ui/compose/performance/phases)给出了阶段跳过与状态读取位置的约束。

### `SlotTable` 不是 UI 树

Composition 会维护 group（调用分组）、key（位置或身份标识）、`remember` 值和调用结构等运行时信息。`SlotTable` 是这些信息的紧凑存储表，不负责测量和绘制。Compose UI 的布局与绘制主体是 `LayoutNode` 树；节点上的 modifier（修饰符）、coordinator（协调修饰符与节点的内部对象）、layer（图层）等对象再参与布局和绘制。

把 `SlotTable` 当成 UI 树容易造成两个误判：

- 看到 recomposition（重组）就推断整棵 UI 树重建；
- 看到某个 `LayoutNode` 变化就推断每个节点都有独立 Android `RenderNode`。

失效的 restart scope 可以局部重新执行，未变化且满足跳过条件的子 scope 可以跳过。大多数普通 `LayoutNode` 也不会各自创建 Android `RenderNode`；绘制内容通常记录到最近的图层边界中。

### Compose 页面仍是 Android App Window

普通硬件加速 Compose 页面由 `AndroidComposeView` 接入 Android View 树。Compose 完成状态处理、节点更新、测量、放置和绘制记录后，窗口侧仍沿 Android 17 的标准路径继续处理：

1. `Choreographer` 和 `ViewRootImpl` 安排窗口 traversal（测量、布局和绘制遍历）。
2. `AndroidComposeView` 在所需的 `onMeasure()`、`onLayout()`、`dispatchDraw()` 入口处理 Compose 节点。
3. UI 线程经 `ThreadedRenderer` 更新 View/Compose 对应的 RenderNode display list（绘制指令列表）。
4. `HardwareRenderer.syncAndDrawFrame()` 把树状态交给 RenderThread。
5. RenderThread 同步渲染树，获取窗口 buffer（图形缓冲区），并通过 Skia/GPU 生成该帧。
6. App Window 的 BLAST BufferQueue 接收 buffer 和 fence（同步栅栏）。
7. SurfaceFlinger 选择可用 buffer，确定 layer 合成计划，再交给 HWC（Hardware Composer，硬件合成器）或 RenderEngine（GPU 合成引擎）。
8. present fence（显示完成栅栏）用于判断该帧何时完成显示。

因此，Composition 或 Drawing 结束都不表示画面已经显示；`queueBuffer()` 返回也不表示 SurfaceFlinger 已经 latch（获取并采用）该缓冲区。完整证据链参见[Jetpack Compose 渲染管线架构](../ch18-rendering-pipelines/23-compose-rendering-pipeline.md)。

Android 17 平台侧可从 [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)、[`ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)、[`HardwareRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)和 [`RenderThread.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)核对窗口帧入口。内核标签用于解释线程调度、频率、fence 与 dma-buf（设备间共享缓冲区）行为，不定义 Recomposition、`LayoutNode` 或 Strong Skipping。

## Recomposition 的准确含义

Recomposition 是 Compose Runtime 重新执行失效的可重启 scope（作用域），并把产生的变更应用到 composition 所管理对象的过程。它不等同于“把整个页面的 composable 全部调用一次”，也不保证每次重新执行都会引发 Layout 或 Drawing。

一次常见的状态更新可拆成四步：

1. Snapshot（Compose 的状态快照系统）状态写入并提交。
2. 读取过该状态的观察范围被标记为需要处理。
3. Recomposer（安排重组工作的运行时组件）在合适的帧时机执行失效的 restart scope；参数未变化且满足跳过条件的 scope 可以跳过。
4. Runtime 应用节点或值变更，必要时请求 Layout、Drawing 或 Android 窗口 traversal。

Compose Compiler 会改写 composable 调用，并附加 Composer（组合过程的运行时接收者）、change mask（参数变化位标记）、group 和重启信息，但这些生成细节会随 Compiler 版本变化。应用代码不应依赖某个版本生成的 `$changed` 位掩码布局或 `startRestartGroup` 调用序列。性能结论应建立在稳定性报告、trace 和对应版本源码上。

### 状态在哪里读，比状态在哪里写更重要

Compose 会跟踪 Snapshot state（快照状态）的读取位置。下面这张表用于选择改动方向：

| 读取位置 | 变更后的主要失效入口 | 优化问题 |
|---|---|---|
| composable 函数体 | Composition | 读取范围是否过大，参数是否频繁变化 |
| measure lambda（测量回调） | Layout 测量 | 尺寸是否需要随状态变化 |
| placement lambda（放置回调） | Layout 放置 | 能否避免重新测量 |
| draw lambda（绘制回调） | Drawing | 能否把高频视觉变化留在绘制阶段 |
| `graphicsLayer {}` | 图层属性或绘制相关更新 | 是否可复用内容，是否引入离屏成本 |

Composition 的状态读取由 Runtime、Composer 和 recompose scope（重组作用域）机制管理；Android owner（Compose 在 Android 上的宿主）还会观察布局与绘制中的读取。`SnapshotStateObserver` 是相关实现组件之一，但不能用这个内部类概括三个阶段的全部公开行为。排查应用问题时，应检查读取发生在哪个阶段，避免依赖内部类的字段或调用顺序。

## 稳定性与 Strong Skipping

稳定性帮助 Compiler 判断参数未变化时能否跳过可重启 composable。它既是正确性承诺，也是优化条件，不能当成一项越高越好的评分。

Kotlin 2.0.20 起，Strong Skipping（强跳过模式）默认启用。按官方说明，它会让可重启 composable 具备跳过重组的能力；稳定参数通常按 `equals()` 比较，不稳定参数通常按实例身份 `===` 比较；composable 内创建的 lambda 也会得到 memoization（复用先前创建的函数对象）。具体规则以项目使用的 Kotlin/Compose Compiler 版本为准，可查阅[Strong Skipping 文档](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)。

Strong Skipping 不会放宽状态模型的正确性要求。直接修改同一个可变对象的字段，再把该实例继续向下传递时，身份比较可能认为参数没有变化；若字段也不是可观察的 Compose state，界面可能收不到更新。合理做法包括用新的不可变值替换旧值、使用 `State`/`SnapshotStateList` 等可观察容器，或把变化集中到定义清楚的 UI state（界面状态模型）中。

### `@Stable` 与 `@Immutable` 是承诺

`@Immutable` 表示对象创建后，公开且可观察的状态不会变化。`@Stable` 表示同一实例上的公开属性变化能够通知 Compose，并满足稳定属性的其他规则。错误标注可能让 Compose 跳过本应执行的更新。

普通 `List<T>` 接口无法向 Compiler 保证不会被外部修改。即使元素类型不可变，包含 `List<T>` 的类也可能被推断为不稳定。可选方案包括：

- 在 UI 边界转换为项目认可的不可变集合；
- 用稳定 wrapper（包装类型）封装，并通过代码审查维护这份承诺；
- 将可变集合改成 Snapshot 可观察容器；
- 为受控类型配置 stability configuration（稳定性配置），同时验证配置是否正确。

来自没有运行 Compose Compiler 的外部模块的类型，也常被视为不稳定。不要只为让报告显示“稳定”就给每个 DTO（数据传输对象）添加注解；应先用 trace 证明稳定性问题带来了用户可感知的耗时，再决定使用 wrapper、调整模块边界或增加配置。官方[稳定性说明](https://developer.android.com/develop/ui/compose/performance/stability)和[诊断指南](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)都强调先确认问题。

## 管理状态和计算成本

### `remember` 管的是 composition 生命周期

`remember` 在当前 composition 位置和 key（缓存键）不变时保留值。它适合保存重组之间可以复用的对象或计算结果，但有明确的生命周期边界：

- 该位置离开 composition 后，值可被遗忘；
- key 改变时会重新计算；
- 配置变化或进程重建后，普通 `remember` 不会恢复；
- 需要保存可序列化 UI 状态时，评估 `rememberSaveable` 和合适的 `Saver`（保存与恢复规则）；
- 数据库、网络连接、线程或大型缓存仍应由具备明确释放策略的组件管理。

漏写 key 会复用过期结果，key 包含过多无关变化又会导致反复计算。判断依据应是“计算依赖哪些输入”，不能只看“这段计算是否昂贵”。

### `derivedStateOf` 只适合降低结果变化频率

`derivedStateOf` 会观察它读取的 state，并在派生结果变化时通知读取方。它本身有观察和比较成本，适用于输入变化频繁、输出变化较少的场景，例如滚动位置连续变化，而界面只关心“是否越过顶部”。

若输入和输出几乎一一对应，直接计算通常更简单。若派生值是集合或复杂对象，还要确认相等性和 mutation policy（状态变更判定策略）是否符合预期。它不会自动把耗时计算移到后台线程，也不能替代分页、缓存或数据层计算。

### 把高频读取延后到所需阶段

位置、透明度、颜色等高频状态若只影响视觉结果，可以考虑在 placement、draw 或 layer lambda（图层属性回调）中读取，从而缩小失效范围。

动画 API 的名字无法决定执行阶段。`animate*AsState`、`Animatable` 和 `updateTransition` 产出的是随时间变化的状态；该状态在哪个阶段被读取，决定后续工作。例如，保留 `State<Float>` 并在 `graphicsLayer { alpha = alphaState.value }` 中读取，可以让透明度读取发生在图层属性 lambda 中；若在 composable 函数体中先读取成 `Float`，读取就已经发生在 Composition。

布局尺寸、文字换行或父子约束发生变化时，`graphicsLayer` 无法消除 Layout 成本。用缩放模拟尺寸变化还可能改变触摸命中区域、清晰度和无障碍边界，应根据交互语义选择实现方式。

## Lazy 列表性能

Lazy 容器只组合和布局视口（屏幕当前可见区域）附近的 item（列表项），但“Lazy”不表示 item 成本可以忽略。滚动中的子组合、测量、图片解码、数据转换和副作用都可能占用帧预算。

### `key` 保留身份，不保证只重组一个 item

稳定且唯一的 `key` 帮助 Compose 在插入、删除和移动后识别同一个 item，并保留与该身份关联的状态。缺少合适的 key 时，位置变化可能使状态迁移和节点复用更困难。

`key` 不提供“数据只改一项就只重组一项”的保证。父 scope 的读取、参数稳定性、共享状态、item lambda 和副作用都会影响失效范围。验证时应同时查看 item identity（条目身份）、参数变化和 tracing（跟踪数据）。

### `contentType` 提高兼容内容的复用机会

异构列表可以为 item 提供 `contentType`（内容类型）。Lazy 容器可以在相同或兼容类型之间复用已有的 composition/节点结构，避免让结构完全不同的 item 互相复用。类型划分应反映结构兼容性；为每个 item 设置唯一类型会失去复用价值。

Compose 官方[列表文档](https://developer.android.com/develop/ui/compose/lists)说明了 `key`、`contentType` 和 Lazy API。列表基准应使用 release-like（接近发布版本）的构建，并启用项目生产配置中的 R8（代码优化与压缩工具），因为 debug 构建会明显改变 Compose 的性能表现。

### 预取属于 Compose Foundation 版本能力

Lazy prefetch（预取）的策略、缓存窗口和 `PausableComposition` 路径会随 Foundation/Runtime 版本调整。`PausableComposition` 支持分段推进稍后要使用的子 composition，典型用途是利用帧内可用时间准备接近视口的内容；它不是应用层通用的“把所有重组分到多帧执行”工具，也不是 Android 17 平台提供的能力。

判断预取是否有收益，需要比较即将进入视口的 item 准备时间、主线程可用时间、内存占用和滚动慢帧。项目升级 Compose 后应重新测量，不能把某个 release（发布版本）的 flag（开关）默认值当作长期不变的平台行为。

## 绘制、图层与动画

`Modifier.graphicsLayer` 可以把内容置于独立图层边界，并让 translation、scale、rotation、alpha（位移、缩放、旋转、透明度）等属性在内容不变时复用绘制记录。图层本身也有成本：

- 某些 alpha、`RenderEffect`、blend（混合）或显式 offscreen（离屏渲染）策略会生成中间纹理；
- 图层数量增加会提高内存、同步和合成管理成本；
- 模糊、阴影、大面积透明和过度重绘仍会增加 GPU 工作；
- draw lambda 中的 CPU 计算也会占用 UI 线程时间。

优化动画时，先区分变化是否影响布局。位置放置和 draw/layer 属性变化可能跳过 Composition；宽高、文本排版和约束变化通常需要 Layout。使用接收 lambda 的 offset、draw modifier（绘制修饰符）或 `graphicsLayer {}`，只是改变状态读取的位置；是否更快仍要由 trace 和基准测试确认。官方[动画性能指南](https://developer.android.com/develop/ui/compose/animation/quick-guide)和[绘制 modifier 文档](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)可用于核对 API 语义。

## Compose 与 View 互操作

### `ComposeView`

在 View 页面嵌入 Compose 时，要为 composition 选择与宿主生命周期匹配的释放策略。`ViewCompositionStrategy.Default` 当前对应 `DisposeOnDetachedFromWindowOrReleasedFromPool`：普通 detach（从窗口分离）会释放；处于 RecyclerView 等池化容器时，则会等到离开复用池或宿主生命周期销毁。Fragment 中还要让 composition 与 `viewLifecycleOwner` 所代表的 View 生命周期保持一致。

频繁创建和销毁 `ComposeView` 会重复执行 composition、测量和图形资源分配。列表中嵌入时应验证池化复用、状态 key 和释放时机。官方[Compose in Views 文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)列出了策略选择。

### `AndroidView`

`AndroidView` 把传统 View 放进 Compose 节点树。`update` lambda（更新回调）会在它读取的 Compose state 变化、相关 scope 执行更新时运行，不能概括为“父组件每次重组都无条件调用”。

在 Lazy 容器中复用创建成本较高的 View 时，可以评估带 `onReset` 和 `onRelease` 的重载。`onReset` 需要清除旧 item 留下的可变状态，`onRelease` 负责在无法继续复用时释放资源。WebView、地图、播放器等组件还要遵守各自的 pause/resume（暂停/恢复）、surface 和线程约定。

互操作成本来自两套生命周期、测量协议、状态桥接、绘制路径和嵌入组件自身的工作。笼统归结为“框架切换开销”无法定位问题，应分别测量创建、更新、布局、绘制和资源释放的耗时。

## 工具：从慢帧走到代码

### 第一步：用 FrameTimeline 选出慢帧

对可复现操作录制 Perfetto trace，先查看 App 和 SurfaceFlinger 的 FrameTimeline（逐帧时间线）。目标是确认：

- 帧是否超过 deadline（截止时间）；
- App 侧、SurfaceFlinger 侧或两侧是否出现 jank（卡顿帧）；
- 主线程、RenderThread、GPU、buffer 等待和 present（呈现）分别占了多少时间；
- 慢帧是否与输入、动画、列表滚动或后台工作相关。

只看平均 FPS（每秒帧数）会掩盖少量耗时很长的帧。排查方法参见[卡顿分析方法论](03-jank-methodology.md)。

### 第二步：按需开启 composition tracing

普通 system trace（系统跟踪）默认不会列出每个 composable 函数。需要引入与项目 Compose 版本匹配的 `runtime-tracing`，并按官方流程录制。[Composition tracing 文档](https://developer.android.com/develop/ui/compose/tooling/tracing)还列出了最低 API、Android Studio、Compose 版本和 trace 大小等限制。

用于性能结论的构建应是 profileable（允许性能分析）、不可调试并接近发布配置。Tracing 会增加字符串处理和 trace 数据开销，适合定位 Composition 中耗时集中的位置，不宜据此直接给出线上绝对耗时。

### 第三步：用 Inspector 和 Compiler 报告缩小候选范围

Layout Inspector 的 recomposition/skip（重组/跳过）计数可以提示某个节点频繁执行，但它本身不是性能指标。一个执行很快的 composable 即使重组很多次，也可能没有用户可感知的影响；重组次数很少但其中包含 I/O 或大对象分配，同样可能造成慢帧。

Compiler stability/metrics（稳定性/指标）报告可以解释某个参数为何无法跳过。应在确认稳定性与慢帧相关后再使用报告，不建议设定“skippable（可跳过）必须达到 80%”之类的统一门槛。强行提高比例可能增加包装、比较与维护成本。

### 第四步：用 Macrobenchmark 验证改动

Compose UI 场景适合用 [Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)测量启动、滚动、导航和动画。测试应固定设备状态、操作路径、编译模式、刷新率与数据集，并保留多次迭代的结果分布。

至少比较：

- `frameDurationCpuMs`（单帧 CPU 耗时）等帧指标的中位数和高分位；
- jank 比例或 deadline overrun（超出截止时间）的分布；
- 主线程和 RenderThread 工作量；
- 分配、GC、图片和 I/O 是否发生变化；
- 优化前后的功能与视觉结果。

微基准适合验证纯计算或局部数据结构，不能替代包含窗口、GPU 和显示过程的端到端测量。

## Baseline Profile 的能力边界

Baseline Profile（基线配置文件）让 ART（Android Runtime，Android 运行时）在安装或后台优化阶段预编译关键代码路径，可以减少冷启动、首轮导航和首次滚动中的 JIT（即时编译）/解释执行成本。它不能修复同步 I/O、布局范围过大、图片解码、锁等待、GPU overdraw（过度绘制）或 SurfaceFlinger 合成压力。

评估方式是对同一场景分别测量无预编译、带 Baseline Profile 和充分编译等模式，确认收益来自编译状态。不要套用固定百分比。Compose 的[Baseline Profile 指南](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)和[测量说明](https://developer.android.com/topic/performance/baselineprofiles/measure-baselineprofile)提供了生成与对照方法。

## 一套可执行的排查顺序

| 证据 | 更可能的瓶颈 | 下一步 |
|---|---|---|
| composition tracing 中某些 scope 持续变长 | Composition 计算或失效范围 | 检查状态读取、参数变化、同步工作、稳定性 |
| measure/layout slice 变长 | 约束、intrinsic、subcomposition、尺寸抖动 | 缩小布局变化，检查自定义 Layout 和 Lazy item |
| UI draw 变长 | draw lambda、display list 重录、路径计算 | 缓存可复用数据，缩小绘制范围 |
| RenderThread/GPU 变长 | shader（着色器）、模糊、离屏、填充率、buffer 压力 | 查 GPU counter、layer 和 fence |
| App 正常而 SurfaceFlinger FrameTimeline 慢 | 系统合成或 present 侧 | 查 layer、HWC、RenderEngine 和 present fence |
| 首轮慢、后续稳定 | 编译、类加载、初始化或资源准备 | 对照 CompilationMode（编译模式）、Baseline Profile、I/O |
| 列表进入新 item 时耗时突然上升 | 子组合、测量、绑定、图片、预取不足 | 检查 key/contentType、item 工作和预取证据 |

每次只改一个可以验证的因素，并保留 trace、基准参数和构建信息。Compose、Kotlin 或平台升级后，要重新确认 Compiler 规则、Runtime 行为与测量结果。

## 常见误判

- **“状态变了就一定重组。”** 读取发生在 Layout 或 Drawing 时，可以只让对应阶段失效。
- **“重组就会重绘。”** 重组应用的结果可能没有改变布局或绘制内容。
- **“Strong Skipping 会修好可变对象。”** 它改变跳过规则，不会替开发者发出缺失的状态通知。
- **“有 key 就只更新一个 item。”** key 管身份与状态保留，失效范围还受参数和状态读取影响。
- **“`derivedStateOf` 是通用缓存。”** 它适合输入频繁而输出较少变化的派生状态。
- **“动画 API 决定了快慢。”** 状态读取阶段、变化范围、图层和 GPU 效果共同决定成本。
- **“Compose 自己提交到 SurfaceFlinger。”** 普通 Compose 页面仍通过 Android App Window 的 HWUI（Android 硬件加速 UI 渲染管线）/BLAST 路径提交。
- **“重组次数越少越好。”** 目标是满足帧 deadline 和交互体验，次数只是诊断线索。
- **“Baseline Profile 能解决全部 Compose 卡顿。”** 它改善代码编译状态，对 I/O、布局和 GPU 问题无能为力。

## 复核清单

- 是否同时记录 Android、kernel（内核）、Kotlin、Compose Compiler、Runtime/UI/Foundation 版本；
- 是否从 FrameTimeline 选定具体慢帧，而非只看平均 FPS；
- 是否区分 Composition、Layout、Drawing、RenderThread、GPU 和 SurfaceFlinger；
- 是否确认高频 state 的读取阶段与观察范围；
- 是否把 `@Stable`、`@Immutable` 和 stability configuration 当作正确性契约；
- Lazy item 是否有稳定唯一 key、合理 `contentType` 和受控的 item 工作；
- 动画是否区分布局变化与绘制/图层属性变化；
- ComposeView/AndroidView 的生命周期和池化复用是否经过验证；
- 性能构建是否 profileable、不可调试并接近 release（发布版本）；
- 改动是否通过 Macrobenchmark 和 trace 前后对照。

## 相关章节

- [卡顿定义与 FrameTimeline](01-jank-definition.md)
- [卡顿分析方法论](03-jank-methodology.md)
- [卡顿优化原则](05-optimization.md)
- [RecyclerView 性能优化](08-recyclerview-performance.md)
- [Jetpack Compose 渲染管线架构](../ch18-rendering-pipelines/23-compose-rendering-pipeline.md)
- [AOSP 标准 View/HWUI 渲染管线](../ch18-rendering-pipelines/02-android-view-standard.md)

## 参考资料

- [Compose performance](https://developer.android.com/develop/ui/compose/performance)
- [Compose phases](https://developer.android.com/develop/ui/compose/phases)
- [Compose performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices)
- [Compose lifecycle](https://developer.android.com/develop/ui/compose/lifecycle)
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)
- [Diagnose stability issues](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Android 17 `Choreographer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 17 `ThreadedRenderer`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)
- [Android 17 HWUI `RenderThread`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)
