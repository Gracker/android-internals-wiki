---
title: "Compose Pausable Composition与Choreographer FrameData协作"
chapter: "1.25"
status: "ready-for-review"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["memory", "optimization", "android17", "compose", "choreographer"]
created_by: "task2a-content-processing"
created_date: "2026-07-03"
gap_source: "研究素材/素材驱动"
drafted_date: "2026-07-03"
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: "high"
sources:
  - type: "deepresearch"
    path: "2026-04-10-07-compose-pausable-composition-choreographer-deadline.md"
  - type: "deepresearch"
    path: "2026-04-10-07-frame-timeline-perfetto-visualization-choreographer-api33.md"
related_chapters: ["1.4", "2.4"]
---

# 1.25 Compose Pausable Composition 与 Choreographer FrameData

Pausable Composition、Lazy Layout 预取调度器和 `Choreographer.FrameData` 都与帧时间有关，但它们属于三个不同层级。Compose Runtime 提供可暂停子组合；Compose Foundation 决定何时推进 Lazy item 预取；Android 平台通过 Choreographer 提供 VSync 与候选 FrameTimeline。AndroidX 1.11.4 的 Android 预取调度器没有直接读取 `FrameData` 的 deadline。

这一区分会影响优化方案。把三者写成一条公开 API 调用链，会引出不存在的 `rememberFrameData()`、`PausableContent`、`compositionOf()` 等接口，也会让开发者误判卡顿原因。

本文以 Compose Runtime、Foundation、UI 1.11.4 和 AOSP `android-17.0.0_r1` 为审阅基线。Compose 独立于 Android 平台发布，同一个 Android 17 设备可以运行不同 Compose 版本。

## 1. 三个层级各自负责什么

| 层级 | 主要对象 | 职责 | 不负责的工作 |
|---|---|---|---|
| Compose Runtime | `PausableComposition`、`PausedComposition` | 分段推进尚未投入使用的子组合，完成后应用记录的节点操作 | 选择 Lazy item、计算帧预算、控制 SurfaceFlinger |
| Compose Foundation / UI | Lazy 预取请求、`PausedPrecomposition`、Android prefetch scheduler | 选择待预取 item，估算剩余时间，驱动 compose、apply、measure | 提供平台 FrameTimeline，拆分任意业务重组 |
| Android 平台 | `Choreographer`、`FrameData`、`FrameTimeline` | 分发 VSync，描述候选 timeline、deadline 与 VSync ID | 自动驱动 Compose 的暂停子组合 |

“协作”在这里表示它们共同影响一帧内的主线程工作安排，不表示 Runtime 与 `FrameData` 之间存在公开的直接连接。

## 2. 版本边界

Pausable Composition 来自 AndroidX，不能按 Android API Level 推断是否启用。

| 版本 | 变化 | 工程含义 |
|---|---|---|
| Runtime 1.7.x | 没有公开的 `PausableComposition` API | 旧项目不能照搬后续对象模型 |
| Runtime 1.8.0-alpha02 | 加入 `PausableComposition` | API 起点 |
| Runtime 1.8.0 | 1.8 稳定线包含该机制 | 仍需让 Runtime、Foundation、UI 保持兼容版本 |
| Foundation 1.10.0-alpha05 | Lazy 预取开关默认启用 | Foundation 开始默认采用暂停式预取 |
| Foundation 1.10.6 | 因稳定性问题默认关闭该开关 | 不能只看 API 是否存在 |
| Runtime / Foundation 1.11.4 | 本文 AndroidX 基线；1.11.4 Foundation 源码中的开关为 `true` | 升级后仍要做列表滚动回归 |

Runtime 1.8.0-alpha02 的引入记录见 [Compose Runtime 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)，Foundation 的开关变化见 [Compose Foundation 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-foundation)。版本解析结果比 BOM 名称更可靠，排查时应记录 Gradle 最终选中的 Runtime、Foundation 和 UI artifact。

`FrameData` 与 `FrameTimeline` 则是 Android 13 / API 33 加入的公开平台 API。它们在 Android 17 / API 37 中继续存在。应用能读取这些对象，不代表所用 Compose 版本会读取它们。

## 3. Runtime 的暂停对象模型

`PausableComposition` 是面向 Compose 基础设施的低层接口。它需要 `Applier` 和父 `CompositionContext`，普通页面通常不会自行创建。Runtime 1.11.4 的关键接口可概括为以下声明。

```kotlin
public sealed interface PausableComposition : ReusableComposition {
    public fun setPausableContent(
        content: @Composable () -> Unit
    ): PausedComposition

    public fun setPausableContentWithReuse(
        content: @Composable () -> Unit
    ): PausedComposition
}

public sealed interface PausedComposition {
    public val isComplete: Boolean
    public val isApplied: Boolean
    public val isCancelled: Boolean

    public fun resume(shouldPause: ShouldPauseCallback): Boolean
    public fun apply()
    public fun cancel()
}
```

这段接口给出了完整的控制边界：`setPausableContent*()` 创建一次暂停任务，调用方反复 `resume()`，完成后调用一次 `apply()`。请求失效时可以 `cancel()`，取消后的对象不能继续使用。

`ShouldPauseCallback` 是协作式检查。返回 `true` 只表示请求 Runtime 在可暂停位置交还控制权，正在执行的任意 Kotlin 函数不会因此被抢占。回调会频繁执行，里面不应进行 I/O、复杂状态计算或大量分配。

### 3.1 完成组合不等于结果可用

暂停子组合的结果先由 `RecordingApplier` 记录。`isComplete == true` 表示组合阶段已结束，节点操作还没有回放到目标 `Applier`。调用 `apply()` 后，结果才能交给后续布局流程。

一次预取的大致状态顺序如下：

```text
setPausableContent()
    → resume(shouldPause)
    → 仍未完成：等待下一次预算
    → resume(shouldPause)
    → isComplete
    → apply()
    → premeasure
    → item 进入可复用的预取结果
```

这条顺序也解释了为何 trace 中 compose 结束后仍可能看到 apply 和 measure。只统计 compose slice 会漏掉预取请求的后续成本。

暂停期间读取的 Snapshot 状态可能变化。Runtime 会让已完成的对象重新回到待重组状态，因此调用方要在 `apply()` 前再次检查 `isComplete`。Foundation 已封装这套生命周期，业务层自行驱动时很容易遗漏取消、状态失效和宿主销毁。

### 3.2 它能暂停哪些工作

Pausable Composition 针对可暂停的子组合执行路径。以下工作不在它的暂停契约内：

- 已经开始的网络请求、数据库查询或 `Flow` 收集；
- `LaunchedEffect` 中正在运行的协程；
- Composable body 内的一次长时间同步调用；
- apply、measure、layout、draw；
- RenderThread、GPU、SurfaceFlinger 的工作；
- 普通页面的任意重组。

因此，Bitmap 解码、大集合排序、JSON 解析或同步文件访问放在 item 的组合路径中，依然会形成长主线程 slice。运行时只能在编译器与 Runtime 支持的位置响应暂停请求。

## 4. Lazy 预取如何使用暂停组合

Foundation 的 Lazy 预取是应用最容易遇到的接入点。滚动策略选出可能进入视口的 item 后，`SubcomposeLayout` 创建 `PausedPrecomposition`。调度器在预算允许时逐步推进：

1. 校验 index、稳定 key 与 `contentType`。
2. 创建或继续 paused precomposition。
3. 组合完成后执行 apply。
4. 解析嵌套 Lazy 容器的预取。
5. 对生成的 placeable 做 premeasure。

Foundation 1.11.4 按 `contentType` 保存 compose、resume、pause response、apply、measure 等阶段的历史耗时。稳定 key 用于确认 index 背后的数据项是否仍相同。业务层更有效的控制点是提供稳定 key、合理的 `contentType`，并让 item 的同步组合路径保持轻量。

下面的示例只演示应用层应提供的信息，不直接创建 `PausableComposition`。

```kotlin
@Composable
fun Feed(items: List<FeedItem>) {
    LazyColumn {
        items(
            items = items,
            key = { item -> item.id },
            contentType = { item -> item.layoutType },
        ) { item ->
            FeedRow(item)
        }
    }
}
```

这里的 `key` 应在插入、删除和排序后仍能识别同一数据项；`contentType` 应按布局与组合成本的大类划分。把位置当 key，或把每个 id 都当作独立 `contentType`，都会削弱预取复用与耗时估算。

## 5. Android 预取预算没有直接使用 FrameData deadline

Foundation 1.11.4 的 `PrefetchScheduler.android.kt` 使用 `View`、`Choreographer.FrameCallback` 和显示刷新率估算时间。其思路可以压缩为：

```text
frameIntervalNs = 1_000_000_000 / displayRefreshRate

nextFrameTimeNs =
    max(lastDoFrameTimeNs, viewDrawingTimeNs) + frameIntervalNs

availableTimeNanos =
    max(0, nextFrameTimeNs - System.nanoTime())
```

这段公式描述源码中的预算模型。`lastDoFrameTimeNs` 来自调度器收到的上一轮 `doFrame()` 时间，`viewDrawingTimeNs` 来自 `View.drawingTime` 的单位转换。View 已超过两个帧间隔没有绘制时，调度器可把当前时段视为 idle，放宽预取预算。

该实现没有调用：

```text
FrameData.getPreferredFrameTimeline().getDeadlineNanos()
```

上面的调用链是平台允许应用读取首选 timeline deadline 的方式，不是 Foundation 1.11.4 预取调度器的预算来源。可变刷新率、多显示器切换和高刷设备会放大“估算下一帧”与“平台当前 timeline”之间的差异，所以需要用目标设备 trace 验证。

## 6. FrameData 的公开数据模型

Android 17 的 [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java) 中，`VsyncCallback` 接收一个 `FrameData`。公开 API 可读取：

- `FrameData.getFrameTimeNanos()`；
- `FrameData.getFrameTimelines()`；
- `FrameData.getPreferredFrameTimeline()`；
- `FrameTimeline.getVsyncId()`；
- `FrameTimeline.getExpectedPresentationTimeNanos()`；
- `FrameTimeline.getDeadlineNanos()`。

`FrameData` 没有公开的 `intervalNanos`、`lastFrameTimeNanos` 或 `refreshRate` 字段。`FrameTimeline` 的 deadline 和 expected presentation time 使用 `System.nanoTime()` 时间基准。

下面的示例展示如何在 API 33 及以上复制首选 timeline 的基础值。

```kotlin
data class PreferredTimelineSnapshot(
    val frameTimeNanos: Long,
    val vsyncId: Long,
    val expectedPresentationTimeNanos: Long,
    val deadlineNanos: Long,
)

@RequiresApi(33)
fun requestTimelineSnapshot(
    choreographer: Choreographer,
    consume: (PreferredTimelineSnapshot) -> Unit,
) {
    choreographer.postVsyncCallback { frameData ->
        val timeline = frameData.preferredFrameTimeline
        consume(
            PreferredTimelineSnapshot(
                frameTimeNanos = frameData.frameTimeNanos,
                vsyncId = timeline.vsyncId,
                expectedPresentationTimeNanos =
                    timeline.expectedPresentationTimeNanos,
                deadlineNanos = timeline.deadlineNanos,
            )
        )
    }
}
```

这段代码只复制 `Long` 值。`FrameData` 及其 `FrameTimeline` 对象只在 `onVsync()` 回调期间有效，异步代码不能保存对象引用后再读取。API 契约可在 [`FrameData`](https://developer.android.com/reference/android/view/Choreographer.FrameData) 与 [`FrameTimeline`](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline) 文档中核对。

应用读取 timeline 可用于自研动画或渲染调度、日志关联和实验测量。它不会自动改变 Compose Foundation 的预取预算，也不能作为业务代码控制 `PausedComposition` 的隐藏入口。

## 7. 怎样用 Perfetto 验证收益

观察 Pausable Composition 时，应把预取与可见帧放在同一时间轴上。Foundation 1.11.4 的 Lazy 预取路径包含以下 trace 名称：

- `compose:lazy:schedule_prefetch:index`；
- `compose:lazy:prefetch:available_time_nanos`；
- `compose:lazy:prefetch:execute:item`；
- `compose:lazy:prefetch:compose`；
- `compose:lazy:prefetch:apply`；
- `compose:lazy:prefetch:resolve-nested`；
- `compose:lazy:prefetch:measure`；
- `compose:lazy:prefetch:idle_frame`。

排查顺序可以按四个问题展开：

1. 预取 compose 是否被拆成多段，单次 resume 是否仍然过长？
2. apply、nested prefetch 或 measure 是否占用了可见帧？
3. 重型 item 是否集中在某个 `contentType`，key 是否频繁变化？
4. 滚动方向改变后，是否出现大量被取消或释放的预取结果？

还要同时查看 `Choreographer#doFrame`、主线程调度、RenderThread、FrameTimeline 和系统内存事件。Pausable Composition 可能降低某次预取连续占用主线程的时长，同时增加提前组合的 CPU 与内存成本。结论应来自 Macrobenchmark、帧时间分布和内存曲线，不能套用固定百分比。

## 8. 常见错误判断

### 8.1 “Android 17 默认让所有 Compose 组合跨帧”

是否具备该机制由 AndroidX 版本决定，是否使用则由具体接入路径与开关决定。普通 `setContent` 和常规重组不会自动变成暂停子组合。

### 8.2 “`shouldPause()` 返回 true 后能立刻中断”

暂停是协作式行为。长时间同步调用内部没有可用暂停点时，Runtime 要等调用返回后才能交还控制权。

### 8.3 “FrameData 提供固定刷新间隔”

公开 `FrameData` 描述本次 VSync 和候选 timeline，不提供 `refreshRate` 或 `intervalNanos`。帧间隔还会受刷新率切换、应用 cadence 与系统调度影响。

### 8.4 “组合完成后可以直接拿去 measure”

暂停组合完成后还要 apply。Lazy 预取随后可能继续做嵌套预取解析和 premeasure。

### 8.5 “开关打开就一定更流畅”

暂停式预取会提前消耗 CPU 和内存，也受 item 结构、滚动速度、设备刷新率和版本缺陷影响。Foundation 1.10.6 曾因稳定性问题默认关闭该路径，版本升级必须带着滚动、状态更新、item 删除和嵌套列表场景回归。

## 9. 工程检查清单

- 锁定并记录 Compose Runtime、Foundation、UI 的解析版本。
- 查看对应版本发布说明和源码默认开关，不从 Android API Level 推断。
- 为 Lazy item 提供稳定 key 与有意义的 `contentType`。
- 移出 Composable body 中的同步 I/O、解码和大规模数据计算。
- 在 60 Hz、高刷和可变刷新率设备上采集滚动 trace。
- 分开统计 compose、apply、measure 与被取消的预取工作。
- 读取 `FrameData` 时只在回调内访问对象，需要留存时复制基础值。
- 发现回归时先用 Foundation 的实验性回退开关做对照，再决定是否长期调整。

更完整的 Runtime 状态机、`RecordingApplier` 和 Lazy 预取源码分析见 [2.28 Compose Pausable Composition 深度分析](../ch02-rendering/2.28-Compose-Pausable-Composition-深度分析.md)，应用侧配置与排查步骤见 [2.29 Compose Pausable Composition 工程指南](../ch02-rendering/2.29-compose-pausable-composition-guide.md)。

## 参考资料

- [Compose Runtime 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)
- [Compose Foundation 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-foundation)
- [`PausableComposition` API](https://developer.android.com/reference/kotlin/androidx/compose/runtime/PausableComposition)
- [`PausedComposition` API](https://developer.android.com/reference/kotlin/androidx/compose/runtime/PausedComposition)
- [`Choreographer.FrameData` API](https://developer.android.com/reference/android/view/Choreographer.FrameData)
- [`Choreographer.FrameTimeline` API](https://developer.android.com/reference/android/view/Choreographer.FrameTimeline)
- [AOSP Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
