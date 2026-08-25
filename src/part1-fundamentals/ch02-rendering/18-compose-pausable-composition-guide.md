---
title: Compose Pausable Composition 实战指南
chapter: '2.18'
section: '2.18'
status: ready-to-publish
applicable_versions: Compose Runtime 1.8.0 - 1.11.4; Android 6.0 (API 23) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: Compose Runtime/Foundation/UI 1.11.4 + Android 17 / API 37
confidence: high
sources:
- type: aosp
  path: androidx/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/PausableComposition.kt
- type: aosp
  path: androidx/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/ComposeFoundationFlags.kt
- type: aosp
  path: androidx/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutPrefetchState.kt
- type: aosp
  path: androidx/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow.kt
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/compose-runtime
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/compose-foundation
- type: official
  path: https://developer.android.com/develop/ui/compose/performance/bestpractices
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
tags:
- Pausable Composition
- Compose
- 性能优化
- 增量加载
- 时间切片
related_chapters:
- '2.3'
- '22.3'
- '22.2'
---

# Compose Pausable Composition 实战指南

Pausable Composition（可暂停组合）对应用工程师的价值主要体现在 Lazy Layout（懒加载布局）的预取：Foundation 可以把即将进入视口的列表项分批完成子组合，也就是先为列表项建立一部分 Compose 界面结构；当前帧的剩余执行时间不足时先暂停，后续再继续。业务代码通常不直接创建 `PausableComposition`，也没有公开的“时间片大小、并发组合数、优先级权重”配置。

应用实践集中在四个问题：

1. 怎样确认项目中的版本和默认行为；
2. 怎样编写有利于 Lazy Layout 预取的列表；
3. 怎样用同一版本做可重复的开关对照；
4. 怎样从 Macrobenchmark（宏基准测试）和 Perfetto 系统跟踪中判断瓶颈位于哪个阶段。

Compose Runtime 的对象模型、状态机、`RecordingApplier` 与 Lazy Layout 预取的公共边界，可配合[第 22 章 Compose 性能优化](../../part5-app/ch22-rendering-practice/03-compose-compiler-modifier-diagnostics.md)阅读；本文聚焦应用侧的使用和测量。

## 1. 先确认三个版本轴

### 1.1 Compose 版本决定能力

Pausable Composition 属于 AndroidX Compose，不属于 Android 17 的 framework API（系统框架接口）：

| 版本阶段 | 行为 |
|---|---|
| Runtime 1.8.0-alpha02 | 首次加入 Pausable Composition |
| Runtime 1.8.0 | 公共 API 进入 1.8 稳定线 |
| Runtime 1.9.0 | 补充 `isApplied`、`isCancelled` 状态 |
| Foundation 1.10.0-alpha05 | Lazy Layout 预取开关默认启用 |
| Foundation 1.10.6 | 因稳定性问题默认关闭 |
| Runtime、Foundation、UI 1.11.4 | 源码基线；Foundation 源码中开关为 `true` |

项目可能通过 Compose BOM（物料清单）、version catalog（版本目录）、直接依赖或第三方库约束版本。不能只看 Gradle 文件中声明的某个版本号，还要检查依赖解析的最终结果。

下面的命令用于检查应用运行时 classpath（类路径）中解析出的 Compose 模块版本：

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

输出中应确认 Runtime、Foundation、UI 是否处于同一版本线，以及是否被其他依赖强制升级或降级。构建变体名称不同时，应把 `releaseRuntimeClasspath` 换成相应的 Gradle configuration（配置）名称。

### 1.2 Android API 级别决定测试平台，不决定开关

1.11.4 的 Android AAR（Android 库归档包）声明 `minSdkVersion 23`。同一 Compose 版本可以运行在多个 Android 版本上，Pausable Composition 不需要通过 `Build.VERSION.SDK_INT >= 37` 判断是否启用。

Android 17（API 37）是平台源码锚点。测试仍应覆盖业务最低版本和主流设备，因为 `Choreographer` 帧调度、显示刷新率、CPU、GPU、厂商调度与内存条件都会影响测量结果。

### 1.3 默认开关随 Foundation 补丁版本变化

`ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 是一个临时的 `@ExperimentalFoundationApi` 回退开关。1.11.4 源码默认值为 `true`，而 1.10.6 发布说明记录的默认值为关闭。

这项开关的使用边界如下：

- 不能用“Compose 1.10+ 一定默认开启”概括所有补丁版本；
- 不能把该开关作为长期业务配置；
- 升级时同时检查发布说明、源码默认值和项目解析版本；
- 发现回归时可以短期关闭做定位，并向 AndroidX 报告可复现问题。

## 2. 应用侧能控制什么

### 2.1 使用稳定的 `key`

Lazy Layout 列表项的索引可能因插入、删除和排序而变化。稳定且唯一的 `key` 用来标识数据身份，帮助 Compose 识别“同一个列表项移到了新位置”，也让预取请求能判断某个索引对应的数据是否已经变化。

```kotlin
@Composable
fun MessageList(
    messages: List<Message>,
    modifier: Modifier = Modifier,
) {
    LazyColumn(modifier = modifier) {
        items(
            items = messages,
            key = { message -> message.id },
        ) { message ->
            MessageRow(message)
        }
    }
}
```

`key` 应来自持久 ID，不能使用会随位置变化的索引，也不应在每次组合时生成 UUID（通用唯一标识符）。`key` 变化会让已有预取请求失效，已经准备好的组合槽位（slot）也可能被取消或释放。

### 2.2 准确 `contentType`

Foundation 1.11.4 会按 `contentType` 保存预取各阶段的平均耗时。异构列表若不区分类型，标题、文本卡片、视频卡片和广告位会共享一组耗时估计，调度器（scheduler）便难以判断剩余时间是否足够。

```kotlin
sealed interface FeedItem {
    val id: Long

    data class Header(
        override val id: Long,
        val title: String,
    ) : FeedItem

    data class Story(
        override val id: Long,
        val title: String,
        val imageUrl: String,
    ) : FeedItem
}

@Composable
fun Feed(items: List<FeedItem>) {
    LazyColumn {
        items(
            items = items,
            key = { it.id },
            contentType = {
                when (it) {
                    is FeedItem.Header -> "header"
                    is FeedItem.Story -> "story"
                }
            },
        ) { item ->
            when (item) {
                is FeedItem.Header -> FeedHeader(item)
                is FeedItem.Story -> StoryRow(item)
            }
        }
    }
}
```

类型数量应反映布局和组合成本的主要差异。若把每个列表项的 ID 都作为 `contentType`，便无法按同类列表项汇总平均耗时。

### 2.3 让列表项的组合路径保持轻量

暂停采用协作机制。`ShouldPauseCallback` 返回 `true` 后，Runtime 仍要执行到预设的暂停点，才能交还控制权。以下工作若直接出现在列表项的组合路径中，仍可能形成较长的连续执行片段（slice）：

- 同步文件或数据库 I/O；
- Bitmap 解码；
- 大集合排序、过滤或 JSON 解析；
- 在 `Composable` 函数体中反复创建复杂对象；
- 自定义 `Layout` 中耗时较长的测量（measure）；
- 不受 Compose 暂停点控制的阻塞调用。

可复用结果应在 `ViewModel`、数据仓库（repository）或明确的后台任务中准备；与组合输入相关的高成本纯计算，可以在输入变化时缓存。Pausable Composition 无法消除列表项内部的同步阻塞。

### 2.4 减少无效重组

可暂停预取处理的是“预取组合怎样分段执行”，不会自动减少本可避免的重组（recomposition）。稳定参数、延后状态读取、`remember`、`derivedStateOf` 和正确的状态归属仍需单独处理。

例如，“是否显示回到顶部按钮”只在首个可见列表项的索引是否为 0 时变化，可以用派生状态缩小重组范围：

```kotlin
val listState = rememberLazyListState()
val showScrollToTop by remember {
    derivedStateOf {
        listState.firstVisibleItemIndex > 0
    }
}

LazyColumn(state = listState) {
    // items(...)
}

AnimatedVisibility(visible = showScrollToTop) {
    ScrollToTopButton()
}
```

这段优化针对快速变化的滚动状态读取，与可暂停预取解决的是不同问题。

## 3. `LazyLayoutCacheWindow` 怎样使用

`LazyLayoutCacheWindow` 决定滚动方向前方的预取距离，以及后方已经滚过内容的保留距离。它属于 `@ExperimentalFoundationApi`，调用方需要用 `@OptIn` 明确接受实验性 API。

下面的示例把缓存窗口（cache window）配置给 `rememberLazyListState()`，再把返回的列表状态交给 `LazyColumn`：

```kotlin
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CachedMessageList(
    messages: List<Message>,
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState(
        cacheWindow = LazyLayoutCacheWindow(
            aheadFraction = 1.0f,
            behindFraction = 0.5f,
        )
    )

    LazyColumn(
        state = listState,
        modifier = modifier,
    ) {
        items(
            items = messages,
            key = { it.id },
            contentType = { it.kind },
        ) { message ->
            MessageRow(message)
        }
    }
}
```

比例值以视口长度为单位。另一个重载接收 `ahead: Dp` 和 `behind: Dp`，其中 `Dp` 是与屏幕密度无关的长度单位，运行时会换算成滚动方向上的像素距离；两种配置都不表示列表项数量。

示例中的 `1.0f` 和 `0.5f` 只用于展示 API。窗口越大，越可能提前准备更多列表项，也会保留更多 `Composition` 组合状态、`LayoutNode` 布局节点、图片和其他资源。调整参数时必须同时观察帧超时、预取命中和内存，不能只凭滚动是否流畅的主观感受判断。

### 3.1 先用默认策略建立基线

建议按以下顺序测试：

1. 默认 `rememberLazyListState()`；
2. 保持数据、手势和构建产物不变，采集多轮基线；
3. 再引入缓存窗口；
4. 分别改变前方预取距离 `ahead` 和后方保留距离 `behind`；
5. 比较 `FrameTiming` 帧耗时指标、跟踪记录中的执行阶段与内存；
6. 只保留可重复收益。

一次手动滑动无法说明参数有效。快速惯性滑动（fling）、慢速拖动、方向反转、列表更新、嵌套列表和图片缓存的冷热状态都会改变结果。

## 4. 怎样做同版本开关对照

比较 Foundation 1.10.6 与 1.11.4，会同时引入许多其他修复，无法把差异全部归因于可暂停预取。更容易确定因果关系的做法，是在**同一 Foundation 版本、同一代码和同一设备**上构建两个基准测试变体（benchmark variant）。

回退变体可以在 `Application` 初始化的最早阶段关闭临时功能开关（flag）。下面的代码只用于定位性能回归：

```kotlin
@OptIn(ExperimentalFoundationApi::class)
class BenchmarkLegacyPrefetchApp : Application() {
    override fun onCreate() {
        ComposeFoundationFlags
            .isPausableCompositionInPrefetchEnabled = false
        super.onCreate()
    }
}
```

另一个变体保持 1.11.4 的默认值 `true`。两者都应使用接近发布环境（release-like）、禁止调试（non-debuggable）且允许性能分析（profileable）的构建，并保持 R8 代码压缩与优化、Baseline Profile（基线配置文件）、数据、图片缓存和网络状态一致。

源码明确警告：Compose 代码加载后再修改这个开关会产生未定义行为。不能在同一个进程运行到一半时动态切换；每个变体都应冷启动一个独立进程。

这个开关是 AndroidX 为高风险功能提供的临时回退 API，后续可能被移除。生产环境若长期关闭它，便无法获得该路径上的后续修复，因此应优先升级到包含修复的补丁版本。

## 5. Macrobenchmark：先证明有无回归

Macrobenchmark 是 Android 官方提供的宏基准测试工具。测试列表滚动时，应使用独立的 `com.android.test` 测试模块，从应用进程外通过 UI Automator 自动操作接近发布环境的应用。

为了让 UI Automator 稳定找到 Compose 列表，可以在测试构建中把 Compose 的语义标签映射为资源 ID：

```kotlin
LazyColumn(
    state = listState,
    modifier = Modifier
        .semantics { testTagsAsResourceId = true }
        .testTag("message_list"),
) {
    // items(...)
}
```

`testTagsAsResourceId` 会让 `By.res("message_list")` 能找到该节点。基准测试不能依赖屏幕坐标定位列表，否则窗口尺寸或系统栏变化会使脚本失效。

下面是最小滚动基准：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
@OptIn(ExperimentalMetricApi::class)
class MessageListBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun flingDown() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(
            FrameTimingMetric(),
            TraceSectionMetric("compose:lazy:prefetch:compose"),
            TraceSectionMetric("compose:lazy:prefetch:apply"),
            TraceSectionMetric("compose:lazy:prefetch:measure"),
        ),
        iterations = 10,
        startupMode = StartupMode.WARM,
        setupBlock = {
            pressHome()
        },
    ) {
        startActivityAndWait()
        val list = device.findObject(By.res("message_list"))
        list.setGestureMargin(device.displayWidth / 5)
        list.fling(Direction.DOWN)
        device.waitForIdle()
    }
}
```

`TraceSectionMetric` 仍是实验性 API。若当前 Benchmark 版本不接受这些内部跟踪区段名称，就保留 `FrameTimingMetric()`，再打开每轮自动生成的 Perfetto 跟踪文件分析。

`FrameTimingMetric` 的主要输出是：

- `frameOverrunMs`：正值表示超过该帧的截止时间（deadline），负值表示仍有余量；API 31 及以上可用；
- `frameDurationCpuMs`：UI 线程（主线程）与 `RenderThread` 生成该帧所用的 CPU 时间。

应比较 p50、p90、p95、p99 等耗时分位数，不能只取一次平均帧率。高刷新率设备留给每帧的时间短于 60 Hz 设备，固定用“16 ms”判断慢帧并不适用。

### 5.1 固定测试条件

对照至少记录：

- 设备型号、Android 构建版本与 Android 17（API 37）源码标签的对应关系；
- 显示器刷新率和分辨率；
- Foundation、Runtime、UI、Compiler、Benchmark 版本；
- 构建类型、R8、Baseline Profile 和编译模式；
- 数据集内容与 `contentType` 分布；
- 图片、磁盘和网络缓存状态；
- 每轮起始位置、手势方向和速度；
- 温度、充电状态与后台负载。

官方不建议用模拟器产出面向用户的性能数据。持续集成（CI）环境可用于发现相对回归，最终结论仍应在具有代表性的物理设备上复核。

## 6. Perfetto：再定位原因

Foundation 1.11.4 的 Lazy Layout 预取路径包含以下跟踪区段；区段名称是源码中的标识符，分析时应按原名搜索：

- `compose:lazy:schedule_prefetch:index`
- `compose:lazy:prefetch:available_time_nanos`
- `compose:lazy:prefetch:execute:item`
- `compose:lazy:prefetch:execute:urgent`
- `compose:lazy:prefetch:compose`
- `compose:lazy:prefetch:apply`
- `compose:lazy:prefetch:resolve-nested`
- `compose:lazy:prefetch:measure`
- `compose:lazy:prefetch:idle_frame`

Macrobenchmark 每轮都会生成 system trace（系统跟踪文件）。需要更完整的 Compose 组合过程跟踪时，可以按照 Benchmark 官方说明启用插桩参数 `androidx.benchmark.fullTracing.enable`；完整跟踪会增加运行开销，不宜把它的结果与轻量指标采集结果直接混合比较。

### 6.1 正常的暂停式预取长什么样

同一个列表项索引的工作可能分散到调度器的多轮执行中。下面展示一次预取从调度、暂停到完成的典型顺序：

```text
schedule index
  -> compose / resume
  -> 预算不足，退出本轮
  -> 下一帧前再次 compose / resume
  -> measure
  -> 解析嵌套预取
  -> apply
```

看到多个较短的 `compose` 执行片段，并不代表发生了错误重组。应结合列表项索引、时间顺序和 `available_time_nanos`（当前可用的纳秒数），判断这些片段是否属于同一个预取请求。

### 6.2 看不到预取跟踪区段

依次检查：

1. 当前控件是否为支持该路径的 Lazy Layout；
2. 是否发生了足以触发预取的滚动；
3. Foundation 解析版本和功能开关值；
4. 列表项是否已经准备好，或请求是否被快速取消；
5. Android `View` 是否可见、调度器是否处于活动状态；
6. 当前帧是否一直没有剩余预算。

“没有对应的跟踪区段”不能直接等同于“Pausable Composition 失效”。

### 6.3 单个 `compose` 执行片段仍然很长

常见原因是列表项中存在长时间无法暂停的调用，或者这段 `Composable` 尚未执行到暂停点。可以依次检查：

- 同步 I/O、解码和解析；
- 大集合计算；
- 自定义 `Layout` 的测量过程；
- 复杂对象分配和垃圾回收（GC）；
- 组合过程跟踪中对应的 `Composable`；
- 主线程同期发生的 Binder 调用、锁竞争和调度延迟。

增大缓存窗口只会更早、更多地调度这些工作，不能缩短单次阻塞时间。

### 6.4 `available_time_nanos` 经常为 0

Android 端调度器的预算，是用下一帧的预计开始时间减去当前时间得到的。若当前可见帧的 UI 工作、`RenderThread` 或其他主线程任务已经耗尽这段间隙，预取只能推迟。

此时应优先优化当前可见列表项和同一线程上的工作。盲目扩大前方预取窗口只会产生更多等待请求。

### 6.5 `apply` 或 `measure` 占比高

暂停机制只会分段推进组合。录制界面变更后仍要通过 `apply()` 把变更应用到节点树，随后还要执行预测量（premeasure）。可以按瓶颈所在阶段继续检查：

- `apply`：检查节点数量、`Modifier` 更新、`RememberObserver` 生命周期回调与 `SideEffect` 副作用；
- `measure`：检查自定义 `Layout`、固有尺寸测量（intrinsic measurement）、嵌套约束和 `Placeable`（可放置的测量结果）数量；
- 嵌套预取（nested prefetch）：检查嵌套 Lazy Layout 的层级和预取数量。

不能把整段预取成本都归给 `resume()`。

### 6.6 请求频繁取消

Foundation 会在索引越界、`key` 改变、列表状态失效或策略取消时清理预取。频繁全量替换数据、不稳定的 `key` 和快速反转滚动方向，都会降低预取命中率。

应先修正数据身份和更新方式，再讨论缓存窗口。请求取消本身不是内存泄漏的证据；判断泄漏时，还要检查预取句柄（handle）是否释放、对象是否仍被引用，以及堆内存是否持续增长。

## 7. 怎样解释内存变化

预组合会提前创建 `Composition` 状态、`LayoutNode` 和业务对象，图片组件还可能触发解码或缓存。可暂停预取的目标并不包括降低峰值内存。

内存对照应至少分开：

- Java/Kotlin 堆内存；
- 原生堆内存（native heap）；
- 图形与纹理内存；
- 图片缓存；
- 预组合槽位数量；
- 垃圾回收次数与停顿时长；
- 缓存窗口前方和后方的保留范围。

若帧超时下降但内存明显增加，需要继续缩小 `ahead` 或 `behind`，或者减少列表项在组合时创建的大型资源。没有采集对象数量和各类内存数据时，不能宣称“峰值内存降低 30%”。

## 8. 升级与回退流程

### 8.1 升级前

1. 保存当前解析依赖树；
2. 建立使用固定数据和手势的 Macrobenchmark；
3. 保存基线 JSON 与系统跟踪文件；
4. 记录当前功能开关的默认值；
5. 覆盖快速惯性滑动、慢速拖动、方向反转、列表刷新和嵌套列表。

### 8.2 升级后

1. 确认 Runtime、Foundation、UI 没有混用版本；
2. 重跑同一个基准测试；
3. 先看 `FrameTiming` 分位数，再看跟踪记录中的执行阶段；
4. 检查发布说明中与 Pausable Composition、预取和缓存窗口有关的修复；
5. 若出现回归，用同版本的功能开关 A/B 对照缩小范围；
6. 保留最小复现、设备信息、系统跟踪文件和依赖树，提交 AndroidX 问题报告。

### 8.3 生产回退

只有证据指向可暂停预取，而且短期内无法通过升级修复时，才考虑在应用启动的最早阶段关闭临时功能开关。回退后必须重新测量，因为旧的完整组合路径也可能占用主线程更长时间。

该开关只是一项临时兼容措施。长期方案应是升级到修复版本、修正列表项代码或调整预取窗口。

## 9. 常见错误做法

### 9.1 按设备档次设置固定时间片

公开 API 没有“8 ms、16 ms、32 ms”这组时间片参数。Foundation 根据当前可用时间和历史平均耗时决定是否继续，Android 端调度器也会按照显示刷新率估算下一帧时间。

### 9.2 在业务 Composable 中调用 `pause()` 和 `resume()`

业务层没有 `rememberPausableCompositionScope()`、`PausableContent` 或“暂停后台组合”的标准 API。低层 `PausableComposition` 需要 `Applier`（把组合变更写入目标树的适配器）和 `CompositionContext`（父组合上下文），适合 Compose 基础设施。

### 9.3 用 API 级别判断是否支持

Compose 版本决定库能力。`Build.VERSION.SDK_INT >= 37` 这样的分支会让 Android 17 以下设备错误地走旧路径，也会掩盖真正起作用的依赖版本。

### 9.4 把动画、网络加载和协程调度归入本机制

Pausable Composition 负责子组合。动画时钟、网络请求、`produceState` 启动的生产者协程和图片加载器都有各自的调度器，不会因为组合暂停而自动获得更高优先级。

### 9.5 只看平均帧率（FPS）

平均值会掩盖少量严重卡顿。需要结合 `frameOverrunMs` 的高分位、卡顿帧的系统跟踪记录和具体预取阶段，判断用户能感知到的长尾问题。

## 10. 实战检查表

### 接入前

- [ ] Runtime、Foundation、UI 的解析版本已记录；
- [ ] 当前 Foundation 的默认功能开关已从源码或发布说明确认；
- [ ] Lazy Layout 列表项有稳定的 `key`；
- [ ] 异构列表项有合理的 `contentType`；
- [ ] 列表项组合路径没有同步 I/O、解码和大计算；
- [ ] 默认预取策略已有 Macrobenchmark 基线。

### 调参时

- [ ] 已确认缓存窗口使用 `Dp` 还是视口比例；
- [ ] `ahead` 与 `behind` 分开调整；
- [ ] 构建产物、设备、刷新率、数据和手势保持固定；
- [ ] 同时观察 `FrameTiming`、系统跟踪记录和内存；
- [ ] 快速惯性滑动、方向反转、数据更新与嵌套列表均已覆盖。

### 回归时

- [ ] 已确认问题最早发生在 `compose`、`apply`、`measure` 或其他线程阶段；
- [ ] 同版本功能开关的 A/B 对照能稳定复现差异；
- [ ] 功能开关在进程初始化的最早阶段设置；
- [ ] 已尝试包含相关修复的补丁版本；
- [ ] 问题报告附带依赖树、最小复现、设备、基准测试结果和系统跟踪文件。

## 总结

应用使用 Pausable Composition 的主要方式，是让 Foundation 的 Lazy Layout 预取在正确版本和列表结构上工作。稳定的 `key`、准确的 `contentType`、轻量的列表项与可测量的缓存窗口，决定了预取是否值得执行、历史耗时估计是否可信，以及预取结果能否在列表项进入视口时被复用。

评估顺序应保持稳定：先确认依赖解析版本和默认功能开关，再用 Macrobenchmark 证明是否存在回归，最后用 Perfetto 区分 `compose`、`apply`、嵌套预取和 `measure` 阶段。没有同版本对照和系统跟踪证据时，不应给出固定时间片、固定设备档位或固定性能百分比。

## 源码与文档索引

- `compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/PausableComposition.kt`
- `compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/ComposeFoundationFlags.kt`
- `compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutPrefetchState.kt`
- `compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow.kt`
- `compose/foundation/foundation/src/androidMain/kotlin/androidx/compose/foundation/lazy/layout/PrefetchScheduler.android.kt`
- [Compose Runtime 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)
- [Compose Foundation 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-foundation)
- [Compose 性能实践](https://developer.android.com/develop/ui/compose/performance/bestpractices)
- [Macrobenchmark 编写指南](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)

### 关联章节

- [第 22 章 Compose 性能优化](../../part5-app/ch22-rendering-practice/03-compose-compiler-modifier-diagnostics.md)：Runtime 状态机、`RecordingApplier`、Lazy Layout 预取与应用级 Compose 性能边界
