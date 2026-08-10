---
title: "Compose PausableComposition 性能机制与 Choreographer 预算边界"
chapter: "22.33"
status: finalized
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Compose, PausableComposition, Choreographer, 渲染性能, FrameData]
related_chapters: ["2.4", "22.3", "22.21", "22.22"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "研究素材+章节深挖"
confidence: medium-high
sources:
- type: official
  path: AndroidX Compose Runtime/Foundation/UI 1.11.4 source snapshot 854220f44ea8ea80fee824a6c5a045f39bede289
- type: reference
  path: Android 17 Choreographer.java android-17.0.0_r1
- type: official
  path: AndroidX Compose Runtime/Foundation API reference and release notes
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_verified: "2026-08-08"
last_verified_against: "AndroidX Compose Runtime/Foundation/UI 1.11.4 source snapshot 854220f44ea8ea80fee824a6c5a045f39bede289; AOSP Choreographer.java @ android-17.0.0_r1; AndroidX API reference/release notes; local chapter consistency review 2026-08-08"
last_draft_polish_at: "2026-08-07T11:35:48+08:00"
last_draft_polish_run_id: "20260807-113548-draft-polish-25bb3663"
last_deep_review_at: "2026-08-07T12:39:40+08:00"
last_deep_review_run_id: "20260807-123556-deep-review-25bb3663"
reviewed_date: "2026-08-08"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-08-08T10:05:23+08:00"
last_review_finalize_run_id: "20260808-100504-aa8b541a"
---

# 22.33 Compose PausableComposition 性能机制与 Choreographer 预算边界

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Compose：Runtime、Foundation 与 UI `1.11.4`
> - AndroidX 源码快照：`854220f44ea8ea80fee824a6c5a045f39bede289`
>
> `PausableComposition` 的关键逻辑位于 Compose Runtime 与 Foundation，内核不参与暂停点选择。保留内核锚点是为了统一系统基线；直接证据来自 Android 17 `Choreographer` 和 Compose `1.11.4` 源码。Compose `1.11.4` 没有读取平台 FrameTimeline deadline，这里也不给出未经实测的帧率提升比例。

## 1. 先校正三个容易混淆的结论

### 1.1 公开 API 从 Compose Runtime 1.8.0 开始

`PausableComposition` 在 `1.8.0-alpha02` 首次作为公开 API 出现，稳定 API 的版本标记是 `1.8.0`。因此，不能把它写成 Compose 1.7 已经提供的公开能力。

这段历史需要区分两个时间点：

| 时间 | 能确认的事实 |
| --- | --- |
| `1.8.0-alpha02`，2024-09-18 | 发布说明首次记录 `PausableComposition`，并注明暂停依赖编译器支持 |
| `1.8.0`，2025-04-23 | `PausableComposition`、`PausedComposition` 进入稳定版；API Reference 标记为 Added in 1.8.0 |

`1.8.0-alpha06` 还调整过这组 API。阅读早期示例时，必须先核对其依赖版本，不能直接套用 alpha02 的签名或行为描述。

### 1.2 “Compose 1.10 默认启用”只适用于 Foundation Lazy 预取

Compose Runtime 提供暂停组合能力，Foundation 决定 Lazy 布局预取是否使用它。两者的版本开关记录如下：

| Foundation 版本 | `isPausableCompositionInPrefetchEnabled` |
| --- | --- |
| `1.10.0-alpha05` | 发布说明记录为默认启用 |
| `1.10.0` 至 `1.10.5` | 对应源码中的默认值为 `true` |
| `1.10.6` | 因稳定性问题改为默认关闭 |
| `1.11.0` 至当前基线 `1.11.4` | 对应源码中的默认值恢复为 `true` |

所以，“Compose 1.10 把所有 Composition 改成可暂停”这个说法不成立。准确表述是：Foundation 的 Lazy 预取路径从 1.10 系列开始分阶段启用 PausableComposition；普通根 Composition、非预取子组合，以及应用自己的 `@Composable` 调用不会因此自动获得跨帧调度。

这个开关也不是稳定 API 契约。版本升级时，应以目标 Foundation 版本的发布说明、源码和实测为准。

### 1.3 Compose 1.11.4 没有直接读取 `FrameData` deadline

Android 17 提供 `Choreographer.FrameData` 和 `FrameTimeline.getDeadlineNanos()`。但 Compose Foundation `1.11.4` 的 Android 预取调度器实现了另一套预算估算：

1. 读取 `View.drawingTime`；
2. 保存最近一次 `Choreographer.FrameCallback#doFrame(frameTimeNanos)` 的帧起点；
3. 取两者的较大值，再加缓存的显示刷新周期；
4. 用估算的下一帧起点减去 `System.nanoTime()`，得到当前可用时间。

这里的“Deadline 协作”是指 Compose 主动减少预取工作对下一帧的干扰，不代表当前实现读取了 Frame Timeline 的平台 deadline。

## 2. PausableComposition 解决了哪一段工作

一个复杂 Lazy item 的预取可能包含以下阶段：

| 阶段 | 主要工作 |
| --- | --- |
| Composition | 执行可组合函数，读取状态，生成 SlotTable 与 Applier 变更 |
| Apply | 把记录的节点操作交给真实 Applier，并分发 remember 与 `SideEffect` |
| Nested prefetch | 查找 item 内部嵌套的 Lazy 布局并预取其内容 |
| Measure | 用预取约束预先测量 placeable |
| Placement / Draw | item 进入可见区后参与放置、绘制与窗口提交 |

PausableComposition 只让第一行的组合工作具备暂停与恢复能力。Apply、嵌套预取、测量仍是独立阶段，各自需要重新检查剩余预算。它不能暂停任意 Kotlin 代码，也不能把一次很长的 measure、图片解码、Binder 调用或 GPU 工作自动分到多帧。

这条边界很重要。看到 `compose:lazy:prefetch:compose` 变短，不表示整个 item 的预取成本都已下降；后续的 apply、measure 或图片准备仍可能占用主线程或后台资源。

## 3. 公开控制流：创建、恢复、应用

`PausableComposition` 是一种可复用的子 Composition。调用 `setPausableContent()` 时只登记内容并返回 `PausedComposition`，还没有执行内容组合。

调用方随后驱动同一个 `PausedComposition`：

| 操作 | 约束 |
| --- | --- |
| `resume(shouldPause)` | 在未完成状态调用；返回 `false` 表示还需要后续恢复 |
| `isComplete` | 表示最近一次恢复完成，但在 `apply()` 前仍可能因状态变化回到 `false` |
| `apply()` | 只允许在完成后调用；应紧跟完成检查 |
| `cancel()` | 只用于连同原始 Composition 一起废弃的场景 |

下面的函数用于说明一次调度片如何正确处理返回值。它适合解释控制流，不建议普通业务自行创建 PausableComposition。

```kotlin
import androidx.compose.runtime.PausedComposition
import androidx.compose.runtime.ShouldPauseCallback

fun resumeOneSlice(
    paused: PausedComposition,
    shouldPause: ShouldPauseCallback,
): Boolean {
    val completed = paused.resume(shouldPause)
    if (!completed) return false

    // 状态可能在 resume() 与 apply() 之间失效，应用前必须再检查。
    if (!paused.isComplete) return false

    paused.apply()
    return true
}
```

返回 `false` 时，调用方应在后续调度机会继续驱动同一个对象。返回 `true` 表示变更已经应用。`resume()` 返回完成后不能再次调用；`apply()`、`cancel()` 也不能重复调用。

### 3.1 `isComplete` 为什么可能从 true 回到 false

暂停组合会读取 Snapshot state。如果 `resume()` 已经完成，而某个已读取状态在 `apply()` 之前发生变化，Runtime 会把内部状态从 `ApplyPending` 改回 `RecomposePending`。这时旧结果已经过期，需要再次 `resume()`。

API 文档要求完成检查与 `apply()` 同步、紧邻执行，原因就在这里。把已完成的 handle 放进队列，过一段时间再无条件 `apply()`，既违反契约，也可能触发 “paused composition has not completed yet” 一类异常。

### 3.2 `cancel()` 的影响比普通任务取消更大

`cancel()` 会分发 abandon 事件，并把 paused handle 标记为 `Cancelled`。公开文档明确说明：创建该 handle 的 Composition 已处于不确定状态，必须一并丢弃。

因此，列表预取请求失效时，应由拥有 `SubcomposeLayoutState` 生命周期的框架代码处理清理。自定义基础设施若调用 `cancel()`，不能继续把原 Composition 当作正常对象复用。

### 3.3 异常后的对象不可恢复

`resume()` 或 `apply()` 抛出异常时，`PausedCompositionImpl` 会进入 `Invalid`。之后再调用其方法会继续抛错。这个状态机避免调用方拿部分记录结果继续执行，但也意味着异常恢复要回到 Composition 所有者层级，不能只重试同一个 handle。

## 4. 暂停点来自 Compose Compiler 与 restart scope

暂停不是线程抢占。Runtime 只有在编译器生成的可恢复边界处，才有机会询问 `ShouldPauseCallback`。

Compose `1.11.4` 的 `LinkComposer.shouldExecute()` 表明，暂停判断需要同时满足这些条件：

- 当前处于 inserting 或 reusing；
- 当前函数不是一次已开始的恢复；
- 存在 `shouldPauseCallback`；
- 当前有可用的 recompose scope；
- 回调请求暂停，并且该 scope 没有处于 resuming。

满足条件后，Composer 会标记当前 scope 为 paused，记录 remember 顺序所需的占位信息，并把该 scope 报告给父 CompositionContext。后续 `resume()` 从这些 scope 继续。

### 4.1 `shouldPause()` 返回 true 只是请求

公开 API 特别注明：并非所有可组合函数都可暂停。回调即使返回 `true`，当前执行也可能继续到下一个合法边界。

由此可得两个工程结论：

- 回调要足够轻，只做读取时间与简单比较；它会被频繁调用。
- 一个体积很大、内部没有合适可恢复边界的可组合调用，仍可能单次执行较久。

把一个耗时循环放进 `@Composable` 函数，不会因为启用了 PausableComposition 就获得时间片。数据整理、排序、解析和图片处理仍应离开组合阶段，并按各自的并发与生命周期规则执行。

### 4.2 checkpoint 不在 LayoutNode 树

暂停位置属于 Composer、SlotTable、restart scope 和编译器生成代码。此时节点变更由 RecordingApplier 暂存，尚未写入真实布局树。

因此，用“LayoutNode 树 checkpoint”描述该机制会混淆两个层级：

- Composition 层计算要产生哪些节点和属性变更；
- Layout 层对已经应用的节点执行 measure、layout 与 draw。

PausableComposition 在前一层保存恢复所需状态。它没有冻结一个可见的半成品 LayoutNode 子树。

### 4.3 它与协程取消没有共同状态机

`ShouldPauseCallback` 是同步回调，`resume()` 也是同步方法。暂停时不会抛 `CancellationException`，也没有挂起函数 continuation。调度器保存的是 `PausedComposition`，恢复由下一次显式 `resume()` 发起。

这也解释了为什么在 `@Composable` 内用 `yield()` 或检查协程 Job，无法替代 Runtime 的暂停机制。两者控制的执行模型不同。

## 5. apply：完整后再把记录结果交给真实 Applier

公开方法名是 `PausedComposition.apply()`。`applyChanges()` 是 `PausedCompositionImpl` 的私有实现细节，不应作为业务可调用 API 描述。

组合进行期间，`RecordingApplier` 记录 insert、remove、move、up、down、reuse 和 apply 等操作。内部 `applyChanges()` 持锁执行以下顺序：

1. `RecordingApplier.playTo()` 把记录操作回放到真实 Applier；
2. `dispatchRememberObservers()` 分发 remember 生命周期；
3. `dispatchSideEffects()` 执行已记录的 `SideEffect`；
4. `dispatchAbandons()` 处理未采用对象；
5. 通知原 Composition，暂停组合已经结束。

所以，在 `isComplete && apply()` 之前，结果节点不得加入布局树或参与放置。框架不会显示一个只组合了一半的 Lazy item。

这并不代表 `apply()` 免费。节点回放、remember 回调和 `SideEffect` 都会产生 CPU 成本。Foundation 预取代码为 apply 单独维护平均耗时，并在执行前再次比较可用预算。

## 6. Lazy 预取怎样使用 PausableComposition

Compose Foundation `1.11.4` 中，Lazy 预取请求的执行顺序可以从 `LazyLayoutPrefetchState` 直接读出：

1. 校验 index、key 与请求是否仍有效；
2. 按 `contentType` 读取该类 item 的历史平均耗时；
3. 创建或恢复 paused precomposition；
4. 组合完成后单独 apply；
5. 解析并执行嵌套 Lazy 布局预取；
6. 在有约束时执行 premeasure；
7. 请求仍有工作时，交回调度器等待下一次机会。

### 6.1 暂停判断结合“剩余时间”和“历史成本”

Foundation 不会只检查剩余时间是否大于零。执行一项工作前，它会比较：

- 当前 `availableTimeNanos`；
- 同一 `contentType` 的历史平均成本；
- 当前请求是否为 urgent；
- 这一阶段是 resume、pause、apply 还是 measure。

paused composition 的回调每次被询问时，会更新本次消耗和剩余预算，再决定是否请求暂停。这样可以避免在预算只剩很少时启动一段历史上明显更贵的工作。

历史平均值是运行时观测，不是开发者可依赖的固定阈值。item 结构、设备性能、刷新率和热状态变化后，调度结果也会变化。

### 6.2 预取工作发生在帧间消息中

Android 实现的 `AndroidPrefetchScheduler` 同时实现 `Runnable` 和 `Choreographer.FrameCallback`：

- 新请求到来后，通过 `View.post()` 把 Runnable 放到主线程消息队列；
- 预算不足时，注册下一次 `FrameCallback`；
- `doFrame()` 只记录帧起点，再次 `View.post()`；
- Runnable 在该帧回调之后获得执行机会，继续预取。

因此，“shouldPause 为 true 后给当前帧绘制让路”不够准确。更贴近源码的说法是：预取工作在主线程帧间执行；估算下一帧已接近时停止本轮工作，等待后续帧回调之后再试。

如果主线程的其他消息、GC、Binder 调用或同一进程的窗口工作占用这段时间，估算出来的空档仍可能缩短。预取调度只能管理自己发起的工作，不能保留一段独占 CPU 时间。

### 6.3 可见性与生命周期保护

调度器只有在以下条件都成立时才继续：

- 请求队列非空；
- 已安排预取；
- View 仍 attached；
- `windowVisibility == View.VISIBLE`。

View detach 时，它会移除已投递的 Runnable 和 FrameCallback。该保护减少不可见窗口继续预取的机会，但业务仍需确保 item 的异步资源请求有正确生命周期。

## 7. 当前预算公式与 Android 17 FrameData 的边界

下面的函数等价表达 Foundation `1.11.4` 的核心时间计算，目的是看清输入来自哪里。

```kotlin
import java.util.concurrent.TimeUnit

fun estimateAvailableTimeNanos(
    frameStartTimeNanos: Long,
    viewDrawingTimeMillis: Long,
    frameIntervalNanos: Long,
    nowNanos: Long,
): Long {
    val drawingTimeNanos =
        TimeUnit.MILLISECONDS.toNanos(viewDrawingTimeMillis)
    val frameIdle =
        nowNanos > drawingTimeNanos + 2 * frameIntervalNanos

    if (frameIdle) return Long.MAX_VALUE

    val nextFrameTimeNanos =
        maxOf(frameStartTimeNanos, drawingTimeNanos) + frameIntervalNanos
    return maxOf(0L, nextFrameTimeNanos - nowNanos)
}
```

真实调度器缓存 `Display.refreshRate` 换算出的 `frameIntervalNs`，显示数据无效时使用 60 Hz。若 View 已有两个刷新周期没有绘制，它进入 frame-idle 模式，`availableTimeNanos()` 返回 `Long.MAX_VALUE`，表示本轮忽略帧预算；执行完一个请求后会退出该模式。

这里有三个限制：

- 刷新周期被静态缓存，源码没有为每个请求查询实时 mode；
- 下一帧时间由最近 draw/frame 起点和刷新周期推算；
- `Long.MAX_VALUE` 表示调度策略允许忽略时间约束，不表示 CPU 可以无限使用。

### 7.1 Android 17 的正确 deadline 访问链

在 `android-17.0.0_r1` 中，deadline 属于 `FrameTimeline`：

`FrameData.getPreferredFrameTimeline().getDeadlineNanos()`

`FrameData` 没有 `getDeadlineNanos()`。`FrameData` 和其中的 `FrameTimeline` 只在 `Choreographer.VsyncCallback#onVsync()` 执行期间有效；离开回调后访问会抛 `IllegalStateException`。

Compose Foundation 当前调度器实现的是 `Choreographer.FrameCallback`，接收到的只有 `frameTimeNanos`，没有 `FrameData`。所以不能用 Android 17 的 Frame Timeline API 反向解释现有 `shouldPause` 回调。

### 7.2 平台 deadline 与 Compose 预算关注的层级不同

平台 preferred FrameTimeline 给出候选 VSync 的 expected presentation time 和 deadline，用于描述应用帧应何时就绪。Compose 预取预算关注的是：主线程距离估算的下一帧起点还有多少时间，是否适合继续准备屏外 item。

二者都与避免下一帧延迟有关，但数据源、有效期和调用路径不同。分析 trace 时应分别保留：

- Compose 预取 slice 与 `available_time_nanos`；
- App FrameTimeline 的 expected/actual、deadline 和 jank type；
- 主线程 `Choreographer#doFrame`、Traversal；
- RenderThread、BufferQueue、SurfaceFlinger 与 present timing。

预取 slice 越过估算边界，可能推迟后续 `doFrame`；App deadline miss 也可能来自 RenderThread、GPU、SurfaceFlinger 或 HWC。只看其中一层无法归因。

## 8. CacheWindow 决定范围，PausableComposition 决定组合调度

`LazyLayoutCacheWindow` 在 Foundation `1.9.0` 加入。它定义可见区外两段范围：

| 参数 | 行为 |
| --- | --- |
| ahead window | 沿滚动方向预先准备 item |
| behind window | 在反方向保留已离开可见区的 item，减少回滚时重建 |

CacheWindow 决定准备或保留多少内容。PausableComposition 只参与其中的预组合阶段。扩大 ahead window 会增加候选预取项；扩大 behind window 会延长节点和相关状态的保留时间。CPU、内存与命中率要分别测量。

下面的示例只展示 API 关系。窗口值由调用方传入，避免把某个设备上的经验值写成通用答案。

```kotlin
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.layout.LazyLayoutCacheWindow
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.Dp

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CachedFeed(
    ahead: Dp,
    behind: Dp,
    content: @Composable () -> Unit,
) {
    val state = rememberLazyListState(
        cacheWindow = LazyLayoutCacheWindow(
            ahead = ahead,
            behind = behind,
        ),
    )

    LazyColumn(state = state) {
        item { content() }
    }
}
```

`rememberLazyListState(cacheWindow = ...)` 会选用 CacheWindow 对应的预取策略。生产列表仍应为 `items()` 提供稳定 `key`，并在存在多类 item 时提供 `contentType`；这有助于复用，也让预取成本按内容类型统计。

不要只用“滚动更顺”评价窗口配置。至少要观察：

- 快速向前滚动时，预取 item 进入可见区前是否已完成；
- 反向滚动时，behind window 的保留命中是否减少重建；
- 主线程预取 slice 是否挤压下一帧；
- P50、P90、P95、P99 帧耗时及 jank 分类；
- Java/Kotlin heap、native heap、图像缓存和节点数量；
- 冷启动后的首次滚动与缓存后的重复滚动。

这些结果需要在目标列表结构、目标设备和目标刷新率上取得。文章不提供固定 ahead/behind 数值，也不虚构 1.9 与 1.10 的帧率提升比例。

## 9. 性能排查：先确认成本处在哪个阶段

Compose `1.11.4` 为 Lazy 预取提供了可直接搜索的 trace 名称：

| Trace 名称 | 含义 |
| --- | --- |
| `compose:lazy:prefetch:execute:item` | 当前预取 item index |
| `compose:lazy:prefetch:compose` | 完整组合或 paused composition 的恢复工作 |
| `compose:lazy:prefetch:apply` | 把已完成的记录变更应用到真实 Applier |
| `compose:lazy:prefetch:resolve-nested` | 查找嵌套 Lazy 预取状态 |
| `compose:lazy:prefetch:measure` | 预先测量 item |
| `compose:lazy:prefetch:available_time_nanos` | 调度器记录的剩余预算 |
| `compose:lazy:prefetch:idle_frame` | frame-idle 模式下执行请求 |
| `PausedComposition:applyChanges` | Runtime 应用 paused composition 记录 |

具体诊断可按下面的证据顺序进行。

### 9.1 `compose` slice 很长

检查 item 内是否执行了数据转换、同步 I/O、大量对象创建、复杂文本构建或昂贵的 CompositionLocal 读取。再确认函数是否有足够的 restart scope；回调请求暂停不代表当前位置立即停止。

还要按 `contentType` 分组。若不同结构的 item 共用一个 contentType，历史平均值会混在一起，预算预测也更难解释。

### 9.2 `apply` slice 很长

关注节点数量、节点插入与移动、remember observer，以及 `SideEffect` 中的同步工作。组合阶段被分段后，Apply 仍可能一次执行完成。

若 `SideEffect` 做了数据库访问、Binder 调用或复杂计算，应把工作迁移到有明确生命周期的异步层。`SideEffect` 适合把已提交的 Compose 状态同步给非 Compose 对象，不适合执行长任务。

### 9.3 `measure` slice 很长

检查 item 的约束传播、intrinsic measurement、嵌套 `SubcomposeLayout`、文本测量以及图片尺寸是否稳定。PausableComposition 对 measure 没有暂停能力。

列表 item 尺寸在数据加载前后剧烈变化，还会降低预取结果的可用性。能从元数据获得宽高时，应在进入可见区前建立稳定约束。

### 9.4 Compose 预取正常，App FrameTimeline 仍迟到

沿标准 Android 渲染路径继续查看：

`vsync-app → Choreographer#doFrame → Traversal → RenderThread → BLASTBufferQueue → SurfaceFlinger → HWC → present`

主线程正常只能排除一部分应用侧原因。RenderThread 同步、GPU 完成 fence、BufferQueue、SurfaceFlinger 合成和 display present 都可能导致实际显示晚于 expected presentation。

### 9.5 预取本身造成下一帧启动晚

对齐这些时间：

- `compose:lazy:prefetch:*` 结束时间；
- 下一次 `Choreographer#doFrame` 开始时间；
- `available_time_nanos` 降到零的时刻；
- 主线程在二者之间运行的其他消息；
- 对应 App SurfaceFrame 的 deadline 与 jank type。

如果预取在估算预算不足后仍持续，需要区分原因：当前可组合函数没有可暂停边界、apply/measure 已经开始、urgent 请求允许超出平均成本判断，或设备调度和刷新模式变化使估算偏离。

## 10. Benchmark 设计：不把版本号当作实验结论

对比 Foundation 版本时，至少固定这些变量：

- 同一台设备、相同电源模式与热状态；
- 相同显示刷新率；
- 相同 Release 构建、R8 与 Baseline Profile 条件；
- 相同数据、图片缓存状态与网络条件；
- 相同滚动轨迹和输入速度；
- 相同 Lazy item `key`、`contentType` 与 CacheWindow；
- 分开记录冷运行与热运行。

Macrobenchmark 的 `FrameTimingMetric` 可以给出帧数据，但还要保存 Perfetto trace，确认变化来自 compose、apply、measure 或渲染后半段。只比较平均 FPS 会隐藏尾延迟，也无法说明 PausableComposition 是否参与。

版本对照至少包含：

| 组别 | 用途 |
| --- | --- |
| Foundation 1.10.5 | 观察 1.10 系列默认启用时的行为 |
| Foundation 1.10.6 | 观察同系列默认关闭后的差异 |
| Foundation 1.11.4 | 当前稳定基线，源码开关为 true |

如果项目直接修改 `ComposeFoundationFlags`，要在报告里记录该操作。这个字段属于 Foundation 开关，不能当作长期业务 API；测试结论也不能脱离具体版本外推。

## 11. 面向业务代码的优化顺序

多数应用不需要直接构造 `PausableComposition(applier, parent)`。该构造函数要求调用方拥有 Applier、CompositionContext、子组合生命周期和异常清理能力，通常由 `SubcomposeLayout`、Lazy 布局或自定义 UI 基础设施管理。

业务层更有效的工作顺序是：

1. 为 Lazy item 提供稳定 `key`；
2. 多种 item 结构提供准确 `contentType`；
3. 避免在组合阶段做 I/O、解析、排序和图片解码；
4. 让 item 约束尽量稳定，减少进入可见区后的重复测量；
5. 检查嵌套 Lazy 布局是否扩大了预取工作；
6. 用 trace 区分 compose、apply、measure 与 draw；
7. 有证据表明默认窗口不合适时，再实验 CacheWindow。

这里的顺序用于缩小变量范围。它不要求所有列表都配置自定义 CacheWindow，也不表示 PausableComposition 能修复全部滚动卡顿。

## 12. 常见误判

| 误判 | 源码支持的结论 |
| --- | --- |
| Compose 1.7 已提供公开 PausableComposition | 公开 API 从 Runtime 1.8.0 开始 |
| Compose 1.10 后所有组合都自动跨帧 | 默认开关只控制 Foundation Lazy 预取路径，并且 1.10.6 曾关闭 |
| `shouldPause=true` 会立即停止当前函数 | 它只请求在合法的编译器边界暂停 |
| 暂停点是 LayoutNode checkpoint | 暂停状态位于 Composer/restart scope，节点操作由 RecordingApplier 记录 |
| 当前实现读取 `FrameData.getDeadlineNanos()` | Android 17 的访问链是 `FrameData → preferred FrameTimeline → deadline`；Foundation 1.11.4 未使用 FrameData |
| 完成后可以稍后无条件 apply | 状态变化可让 `isComplete` 回到 false，apply 前要紧邻检查 |
| cancel 后可继续使用原 Composition | API 要求丢弃原 Composition |
| 组合可暂停，所以 measure 与 draw 也可暂停 | 这几个阶段有各自执行与预算边界 |
| 预取 slice 变短就证明显示帧正常 | 还要核对 doFrame、RenderThread、BufferQueue、SF、HWC 与 present |

## 13. 源码阅读入口

### Compose Runtime 1.11.4

- [`PausableComposition.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/PausableComposition.kt)：公开契约、状态机、RecordingApplier 与 apply 顺序。
- [`LinkComposer.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/LinkComposer.kt)：`shouldExecute()` 的暂停条件和 paused scope 记录。
- [`Composer.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composer.kt)：编译器生成 `shouldExecute()` 调用的接口说明。
- [PausableComposition API Reference](https://developer.android.com/reference/kotlin/androidx/compose/runtime/PausableComposition)。
- [PausedComposition API Reference](https://developer.android.com/reference/kotlin/androidx/compose/runtime/PausedComposition)。
- [Compose Runtime 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)。

### Compose Foundation 与 UI 1.11.4

- [`LazyLayoutPrefetchState.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutPrefetchState.kt)：compose、apply、nested prefetch 与 measure 的阶段控制。
- [`PrefetchScheduler.android.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation/src/androidMain/kotlin/androidx/compose/foundation/lazy/layout/PrefetchScheduler.android.kt)：Android 主线程调度与可用时间估算。
- [`ComposeFoundationFlags.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/ComposeFoundationFlags.kt)：当前基线的预取开关默认值。
- [`SubcomposeLayout.kt`](https://cs.android.com/androidx/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289:compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/layout/SubcomposeLayout.kt)：paused precomposition 与 SubcomposeLayout 的接口适配。
- [LazyLayoutCacheWindow API Reference](https://developer.android.com/reference/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow)。
- [Compose Foundation 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-foundation)。

### Android 17

- [`Choreographer.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)：`FrameData`、preferred `FrameTimeline`、deadline 与回调有效期。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：统一的内核基线；相关机制没有依赖其调度接口。

## 小结

PausableComposition 为子组合增加了显式的暂停、恢复和应用状态机。暂停粒度由 Compose Compiler 生成的 restart scope 与 Runtime 协作决定，返回 `shouldPause=true` 只是一项请求。组合完成前，节点操作保存在 RecordingApplier；完成并调用 `apply()` 后，真实 Applier、remember observer 与 `SideEffect` 才会收到变更。

Foundation `1.11.4` 把这项能力用于 Lazy 预取，并分别安排 compose、apply、嵌套预取和 measure。Android 端用最近帧起点、View drawing time 与刷新周期估算下一帧前的空档，没有读取 Android 17 `FrameData`。性能分析应把 Compose 预取 trace 与 App FrameTimeline、主线程、RenderThread、BufferQueue、SurfaceFlinger 和 present timing 放在同一时间轴上，再判断延迟发生在哪个阶段。
