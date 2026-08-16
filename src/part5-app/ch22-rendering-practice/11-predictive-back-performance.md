---
title: "预测式返回动画与页面切换性能"
chapter: "22.11"
section: "22.11"
status: finalized
applicable_versions: "Android 13 (API 33) - Android 17 (API 37); AndroidX Activity 1.8.0+; AndroidX Fragment 1.7.0+; AndroidX Transition 1.5.0+; AndroidX NavigationEvent 1.0+"
last_verified: "2026-08-15"
last_verified_against: "Android 16 behavior changes; Android 17 platform source; AndroidX Activity / Fragment / Transition / NavigationEvent / Navigation 3 release notes; Perfetto FrameTimeline docs"
confidence: high
tags: [predictive-back, rendering, animation, fragment, compose]
related_chapters: ["3.3", "7.4", "18.2", "22.3", "22.10"]
sources:
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/support-animations"
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/support-animations-views"
  - type: official
    path: "https://developer.android.com/guide/navigation/navigation-event/handle-back"
  - type: official
    path: "https://developer.android.com/guide/fragments/animate"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/activity"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/fragment"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/transition"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/navigationevent"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/versions"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: clipping
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
---

# 预测式返回动画与页面切换性能

预测式返回（Predictive Back）把“返回”从一次离散事件改成一段可以取消、预览并由进度值驱动的交互。页面切换的性能观察点也随之提前：卡顿不再只发生在 `popBackStack()` 或 `finish()` 之后，手指从屏幕边缘滑动的每一帧都可能暴露主线程、布局、动画和合成成本。系统手势入口见 [§3.3 手势导航](../../part1-fundamentals/ch03-input/03-gesture-navigation.md)，View 一帧的执行顺序见 [§18.2 Android View 标准管线](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)，FragmentTransaction 的提交语义见 [§22.10 FragmentTransaction 提交链路](10-fragment-transaction-performance.md)；本节聚焦应用侧的接入、降级和 Perfetto 定位方法。

分析时要分别看每帧计算量、状态读写范围、主线程排队和渲染提交。任务调度会改变响应延迟，因此不要把数据加载、页面销毁和事务提交放进手势进度回调。

平台返回事件分发和窗口动画以 Android 17 / API 37 的 `android-17.0.0_r1` 源码为准。Activity、Fragment、Transition 与 NavigationEvent 都是独立发布的 AndroidX 库，版本结论要分别查阅各自的发布说明，不能从 Android 平台版本推导。

## 返回事件分发：Android 13 之后多了一段“可预览”的过程

Android 13 引入 `OnBackInvokedDispatcher` / `OnBackInvokedCallback`，提供新的返回完成分发；Android 14 的 `OnBackAnimationCallback` 才把开始、进度和取消事件公开给应用。AndroidX Activity 1.8.0 为 `OnBackPressedCallback` 增加 `handleOnBackStarted()`、`handleOnBackProgressed()`、`handleOnBackCancelled()` 和 `handleOnBackPressed()`，但 Android 13 及更低版本没有平台进度事件，无法运行由连续手势进度控制的同类动画。

Android 15 起，返回主屏幕、跨任务和跨 Activity 的系统动画不再受开发者选项控制，但应用仍须迁移到受支持的返回 API，并且没有启用中的消费型回调拦截本次返回。消费型回调会接管返回动作，使系统无法继续预览原来的返回目标。对于运行在 Android 16 及更高版本、同时以 API 36 及更高版本为目标的应用，这些系统动画默认启用；旧的 `onBackPressed()` 不再被调用，`KEYCODE_BACK` 也不再作为返回键事件分发。迁移期间可以在应用或 Activity 上设置 `android:enableOnBackInvokedCallback="false"` 临时关闭：系统动画会停用，平台 `OnBackInvokedCallback` 会被忽略，但 AndroidX `OnBackPressedCallback` 的完成回调仍可工作。

这几个入口分别负责不同层次的返回处理：

- `OnBackInvokedCallback`：Android 13+ 的平台完成回调。用 `PRIORITY_DEFAULT` 或 `PRIORITY_OVERLAY` 注册消费型回调后，系统预测式返回动画不再运行，应用要自行提供界面反馈并执行返回动作。
- `OnBackAnimationCallback`：Android 14+ 的平台进度接口。它继承 `OnBackInvokedCallback`，增加开始、进度和取消回调；完成仍走 `onBackInvoked()`。
- `OnBackPressedDispatcher`：AndroidX 兼容层，低版本仍能处理返回完成。Activity 1.8.0+ 提供四段式方法，但只有 Android 14+ 能从平台得到连续进度。
- `PredictiveBackHandler`：Compose 入口，来自 `androidx.activity:activity-compose:1.8.0+`。它通过 `Flow<BackEventCompat>` 连续发送手势事件；手势取消时，收集这个异步事件流的协程会收到 `CancellationException`。
- `NavigationEventDispatcher`：面向 Compose、Kotlin Multiplatform（KMP，Kotlin 多平台）和自定义导航容器的底层抽象。Activity 1.12.0 已在 NavigationEvent 之上重写 `OnBackPressed` API；截至 2026-08-15，Activity 稳定版为 1.13.0，NavigationEvent 稳定版为 1.1.2。

Android 16 增加 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER`：应用可以用观察型回调记录根 Activity 离开，而不消费返回事件，返回主屏幕的系统动画仍可播放。Android 17 的 `OnBackInvokedDispatcher` 明确写出版本差异：API 36 同时只能注册一个此类回调，API 37 起不再限制数量。多个观察型回调的执行顺序没有保证，因此它们只适合日志或不改变导航结果的收尾工作，不能拦截返回，也不要负责页面切换。

## 手势进度进入动画系统后，回调只能做每帧能承受的事

预测式返回至少包含四类信号：

- 开始：适合创建或取得动画控制对象，并记录起始状态。
- 进度：`progress` 的范围为 `0f..1f`，用于按进度定位（seek）动画。系统已经把手势距离换算成平滑进度，不要再按“滑动像素 ÷ 屏幕宽度”重复计算。`swipeEdge` 用于区分左右边缘。Android 16 / API 36 还加入帧时间 `frameTimeMillis`，以及代表三键或硬件返回、没有触摸边缘的 `EDGE_NONE`；此时 `touchX`、`touchY` 可能是“不是有效数值”的 `NaN`，不能用于计算动画中心。AndroidX Activity 1.11.0 把这些字段带入 `BackEventCompat`。
- 取消：用户取消后，系统仍可能继续发送进度事件，直到 `progress` 平滑退回 `0f`。取消回调无论执行一次还是多次，都应把临时界面状态恢复到起点，不能依赖某次进度事件完成清理。
- 完成：手势越过提交阈值后，应用执行返回动作，例如 `popBackStack()`、`finish()` 或更新导航状态。

与会触发测量、布局的参数相比，`translationX`、`alpha`、`scaleX`、`scaleY` 更适合由进度驱动，但大图层的透明度和缩放仍会增加 GPU 或合成压力。Fragment 转场和共享元素转场还可能牵涉 View 层级匹配、Transition 起止状态捕获和目标状态计算。Compose 接入时，进度事件会进入状态系统；如果读取这个状态的范围太大，手势期间可能反复执行组合（Composition）和布局（Layout）。

这段 Kotlin 展示 View 场景下的最小接入方式。`handleOnBackProgressed()` 只写不会触发布局的属性，完成回调直接交给负责当前页面的导航对象，避免再次分发同一个返回事件。

```kotlin
fun createPredictiveBackCallback(
    contentView: View,
    onBackCommitted: () -> Unit,
) = object : OnBackPressedCallback(true) {
    override fun handleOnBackStarted(backEvent: BackEventCompat) {
        contentView.animate().cancel()
        contentView.pivotX = when (backEvent.swipeEdge) {
            BackEventCompat.EDGE_LEFT -> 0f
            BackEventCompat.EDGE_RIGHT -> contentView.width.toFloat()
            else -> contentView.width / 2f
        }
    }

    override fun handleOnBackProgressed(backEvent: BackEventCompat) {
        val p = backEvent.progress.coerceIn(0f, 1f)
        val direction = when (backEvent.swipeEdge) {
            BackEventCompat.EDGE_LEFT -> 1f
            BackEventCompat.EDGE_RIGHT -> -1f
            else -> 0f
        }
        contentView.translationX = direction * p * contentView.width
        contentView.alpha = 1f - 0.18f * p
        contentView.scaleX = 1f - 0.04f * p
        contentView.scaleY = 1f - 0.04f * p
    }

    override fun handleOnBackCancelled() {
        contentView.animate()
            .translationX(0f)
            .alpha(1f)
            .scaleX(1f)
            .scaleY(1f)
            .setDuration(120L)
            .start()
    }

    override fun handleOnBackPressed() {
        onBackCommitted()
    }
}
```

`onBackCommitted` 应由 FragmentManager、NavController、Navigation 3 返回栈或页面自己的状态机提供。Activity 1.9.0 已加入 Lint 静态检查警告：在 `OnBackPressedCallback`、`BackHandler` 或 `PredictiveBackHandler` 处理期间再次调用 `onBackPressedDispatcher.onBackPressed()`，会破坏预测式返回动画。`EDGE_NONE` 表示事件不是从屏幕边缘手势开始：示例不会产生横向位移，即使收到进度也只会更新透明度和缩放。三键或硬件返回通常没有可连续映射的滑动距离，可以只在返回完成时执行动作，不提供连续预览。

## Fragment / Navigation：手势期间不要制造新的页面切换成本

Fragment 1.7.0+ 支持应用内预测式返回，但连续按进度定位动画只在 Android 14 / API 34+ 生效。返回事务使用 `Animator` 或 AndroidX Transition 1.5.0+ 时，FragmentManager 可以按手势进度控制动画，再根据完成或取消提交或回滚；旧的 `Animation` 和平台 `Transition` 不支持这条路径。

项目应明确记录这些版本边界：

| 场景 | 最低版本 | 性能边界 |
| --- | --- | --- |
| `OnBackPressedCallback` 进度 API | Activity 1.8.0+；连续进度需要 Android 14+ | 进度回调内只更新动画状态，不提交导航动作 |
| AndroidX Transition 进度控制 | Transition 1.5.0+，Android 14+ | 用 `controlDelayedTransition()` / `TransitionSeekController` 控制进度 |
| Fragment 预测式返回 | Fragment 1.7.0+，Android 14+ | 返回事务涉及的动画必须全是 `Animator` 或支持按进度控制的 AndroidX Transition |
| Compose `PredictiveBackHandler` | Activity Compose 1.8.0+；连续进度需要 Android 14+ | 进度状态的读写范围要限制在动画层 |
| NavigationEvent | NavigationEvent 1.0+ | 手势状态与导航历史分开观察，避免每帧改导航栈 |

Fragment 的官方发布说明中多次记录预测式返回取消、快速连续返回、空白页和生命周期状态不一致等修复。因此，接入时不能只看 API 是否存在，还要固定最低 Fragment / Transition 版本，并把取消回滚列入测试用例。

截至 2026-08-15，Activity 稳定版是 1.13.0，Fragment 稳定版是 1.8.9、候选发布版是 1.9.0-rc01，Transition 稳定版是 1.7.0，NavigationEvent 稳定版是 1.1.2，Navigation 3 稳定版是 1.1.5。Activity 1.12.2 修复了能感知生命周期的回调在 `isEnabled` 状态上的问题；Fragment 与 Transition 已进入仅维护、不再积极扩展功能的阶段。新工程应优先评估当前稳定版，表中的最低版本只表示功能入口已经出现，不代表包含后续的取消、预测式返回和生命周期修复。

Fragment 页面切换的性能预算可以分成三段：

- 手势开始：准备动画控制对象、读取当前 View 尺寸，并确认 FragmentManager 已有可预览的返回目标。不要在应用回调中手动创建上一页的 View。
- 手势进行：只改动画进度或可由合成阶段处理的属性。不要执行 `commitNow()`、网络请求、数据库读取、图片解码或 WebView 初始化。
- 手势完成：只提交返回动作与轻量状态。生命周期要求同步释放的引用照常清理；磁盘写入、缓存整理和其他阻塞工作交给后台线程，不能靠 `post` 到下一帧来维持正确性。

`TransitionManager.controlDelayedTransition()` 的用法与普通 `beginDelayedTransition()` 不同：前者返回可以控制进度的对象，适合把 `BackEvent.progress` 映射到 `currentFraction`；后者启动后由时间驱动，不适合由手势直接定位动画进度。

这段代码只展示如何在同一 View 容器内按进度控制 Transition。FragmentManager 已经接管预测式返回事务时，不要为同一事务再创建一层控制器。

```kotlin
private val backTransition = TransitionSet()
    .addTransition(Fade(Fade.MODE_OUT))
    .addTransition(ChangeBounds())
    .addTransition(Fade(Fade.MODE_IN))

private var seekController: TransitionSeekController? = null

private fun resetPreview() {
    restoreCurrentState()
    seekController = null
}

val callback = object : OnBackPressedCallback(true) {
    override fun handleOnBackStarted(backEvent: BackEventCompat) {
        seekController =
            TransitionManager.controlDelayedTransition(container, backTransition)
        showPreviousStateForPreview()
    }

    override fun handleOnBackProgressed(backEvent: BackEventCompat) {
        seekController
            ?.takeIf { it.isReady }
            ?.currentFraction = backEvent.progress.coerceIn(0f, 1f)
    }

    override fun handleOnBackCancelled() {
        val controller = seekController
        if (controller?.isReady == true) {
            controller.animateToStart { resetPreview() }
        } else {
            resetPreview()
        }
    }

    override fun handleOnBackPressed() {
        seekController?.animateToEnd()
    }
}
```

`controlDelayedTransition()` 需要 Android 14+，每次动画只能使用一个控制器，自定义 Transition 也要明确支持按进度控制。设备版本过低、同一容器正在捕获另一个 Transition，或者容器尚未完成布局时，该方法可能返回 `null`。这里要重点排查 `showPreviousStateForPreview()`：如果它触发新的 Fragment View 创建、`RecyclerView` 首屏绑定或图片加载，返回手势一开始就会占满主线程预算。Fragment 1.7+ 已自行控制返回栈动画时，不应再手动创建第二个控制器或额外调用 `popBackStack()`；事务执行边界见 [§22.10](10-fragment-transaction-performance.md)。

## Compose NavigationEvent：把进度状态限制在动画层

Compose 接入时要先确定由谁处理导航。Navigation 3 已内建预测式返回时，应使用它提供的返回栈和动画，不再叠加自定义处理器；`PredictiveBackHandler` 适合页面内自定义动画；NavigationEvent 适合自定义导航容器、跨平台组件，或需要独立观察手势状态的场景。官方示例组合使用 `NavigationEventTransitionState.InProgress`、`rememberNavigationEventState()` 和 `NavigationBackHandler()`：`transitionState` 只描述手势是否正在进行及其最新事件，页面历史则由另一组状态描述。

Compose 的性能风险来自状态读取位置。如果顶层导航容器、整页 `Scaffold` 布局或复杂列表读取 `progress`，手指移动就会扩大重组范围；如果只在 `graphicsLayer` 更新块中读取稳定的 State 对象，Compose 可以直接安排图层属性更新，避开组合和布局阶段。Compose 的状态读取阶段与排查方法见 [§22.3 Compose 性能](03-compose-performance.md)。

这段 Compose 代码接收稳定的 `FloatState` / `State<Int>` 对象，并只在 `graphicsLayer` 更新块中读取它们。调用方应通过 `remember { mutableFloatStateOf(...) }` 等方式保留同一 State 实例。

```kotlin
@Composable
fun PredictiveBackPage(
    progress: FloatState,
    edge: State<Int>,
    content: @Composable () -> Unit,
) {
    Box(
        modifier = Modifier
            .graphicsLayer {
                val p = progress.floatValue.coerceIn(0f, 1f)
                val direction = when (edge.value) {
                    BackEventCompat.EDGE_LEFT -> 1f
                    BackEventCompat.EDGE_RIGHT -> -1f
                    else -> 0f
                }
                translationX = size.width * p * direction
                alpha = 1f - p * 0.18f
                scaleX = 1f - p * 0.04f
                scaleY = 1f - p * 0.04f
            }
    ) {
        content()
    }
}
```

这里的图层更新不代表动画没有成本：大面积透明度、缩放仍可能增加离屏渲染或 GPU 合成压力；`content()` 内部如果读取同一个进度状态，也会扩大失效范围。先用 Compose tracing 检查组合和布局是否随手势反复出现，再沿 RenderThread、GPU 和 SurfaceFlinger 检查渲染与显示阶段。

取消路径要和完成路径同等测试。`PredictiveBackHandler` 的事件流会在取消时抛出 `CancellationException`；Activity 发布说明还记录过“同一帧禁用后仍处理手势”、回调顺序和生命周期感知回调的 `isEnabled` 状态问题。处理器应一直留在 Composition 中，通过 `enabled` 表达是否接管返回，避免在条件分支里反复添加和移除。工程测试至少覆盖快速半滑取消、连续返回、返回过程中页面状态变化、空返回栈和配置变更后的返回。

## Perfetto：按输入、主线程、FrameTimeline、RenderThread 四段定位

预测式返回的慢帧通常分四类：输入分发慢、主线程进度回调慢、布局或重组范围扩大、渲染提交或 GPU 完成慢。分析 Perfetto 时不能只看主线程轨道，要把输入、`Choreographer#doFrame`、FrameTimeline、RenderThread 和 SurfaceFlinger 放在同一时间窗口中观察。

| 观察对象 | Perfetto 里看什么 | 典型结论 |
| --- | --- | --- |
| 输入事件 | InputDispatcher / 应用主线程消息间隔 | 手势事件进入应用前已经排队，问题偏系统负载或主线程消息拥塞 |
| 主线程回调 | `handleOnBackProgressed()` 附近的自定义轨迹、`Choreographer#doFrame` | 每帧计算、状态写入、同步 I/O 或锁等待占用预算 |
| View / Compose 布局 | `performTraversals`、Compose 的组合与布局时间片 | 进度变化触发测量、布局或大范围重组 |
| RenderThread | `DrawFrame`、`syncAndDrawFrame`、GPU 提交 | 主线程耗时短但绘制复杂，可能是阴影、模糊、大图层或过多 RenderNode 更新 |
| FrameTimeline（Android 12+） | 应用 `SurfaceFrame` 与 SurfaceFlinger（SF）`DisplayFrame` 的 Expected / Actual、卡顿原因 | 区分应用未在截止时间前产出帧，还是显示侧合成或呈现超时 |
| SurfaceFlinger | 缓冲区事务 `BufferTX`、目标图层采纳（latch）、合成与呈现时间 | 应用侧交帧及时但系统采纳或显示晚，继续查缓冲区、同步栅栏（fence）、GPU 或硬件合成器（HWC） |

FrameTimeline 从 Android 12 起可用。Expected 表示系统为一帧安排的预期时间窗口，Actual 表示这一帧的实际执行记录。应用的 Actual `SurfaceFrame` 结束位置综合了缓冲区提交和 GPU 完成时间，可用于判断应用是否在截止时间前产出；SurfaceFlinger 的 Actual `DisplayFrame` 还覆盖图层采纳、合成与呈现。应用帧按时结束并不能证明窗口已经显示，仍要对照 SurfaceFlinger 的 `DisplayFrame`、目标图层和呈现时间。

这段代码使用固定的 Trace 区间名，并用计数器保存进度，便于按时间戳比较回调成本和手势位置：

```kotlin
Trace.beginSection("pb_progress")
try {
    Trace.setCounter(
        "pb_progress_percent",
        (backEvent.progress.coerceIn(0f, 1f) * 100).toLong(),
    )
    updateBackProperties(backEvent)
} finally {
    Trace.endSection()
}
```

不要把百分比、页面 ID 或 URL 拼进 section 名；否则时间片名称会随动态值不断增多，形成难以聚合的高基数数据。输入进度事件也不等于 Choreographer 帧，分析时要按时间戳找到相邻的应用 `SurfaceFrame`，再回到主线程与 RenderThread，判断这次属性更新落入哪一帧。

## 工程接入清单

预测式返回不必一次改完整个导航系统，可以按页面类型分批接入：

1. 清点返回入口：Activity、Fragment、Compose、WebView、Dialog、底部弹窗分别列出当前使用的 `onBackPressed()`、`OnBackPressedCallback`、`BackHandler`、`OnBackInvokedCallback`。
2. 固定依赖：记录 Activity、Fragment、Transition、Navigation / NavigationEvent 的确切版本。新接入优先使用当前稳定版；最低版本只用于解释功能边界。
3. 检查临时关闭项：查看 application 与各 Activity 的 `android:enableOnBackInvokedCallback`。先在返回目标单一的页面移除 `false`，再验证系统动画、自定义回调和低版本回退。
4. 分离埋点和消费：日志使用 Android 16+ 的 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER`，或者在页面销毁时记录，不要为了打点注册消费型回调。API 36 还要遵守只能注册一个观察型回调的限制。
5. 压低进度回调成本：只改属性、动画进度或轻量状态；禁止同步 I/O、图片解码、数据库读取、网络请求和新的 Fragment 事务。
6. 控制动画对象生命周期：Transition 配置、Animator、`Animatable` 与 `graphicsLayer` 容器避免每帧重建；`TransitionSeekController` 每次手势创建一个，取消或完成后丢弃。
7. 覆盖取消测试：半滑取消、快速连续返回、返回时切后台、横竖屏切换、空返回栈、进程恢复后返回。
8. 建立 Perfetto 基线：每类页面至少保留一条正常返回轨迹和一条半滑取消轨迹，并记录设备刷新率、Android 版本以及 Activity / Fragment / Compose 版本。

混合栈页面要明确返回优先级：WebView 浏览历史、页面内弹层、Fragment 返回栈和 Activity 结束不能同时处理同一次手势。优先级不清会造成预览目标与最终返回目标不一致。

## 扩展：WebView 预测式返回

WebView 有自己的 `canGoBack()` / `goBack()` 历史栈。页面里嵌 WebView 时，返回优先级建议写成状态机：

- WebView 可回退：手势开始时固定本次目标为网页历史；进度只驱动 WebView 容器或提示层，完成后调用 `webView.goBack()`，Activity 不出栈。
- WebView 不可回退但页面有弹层：弹层消费返回，手势动画绑定弹层退出。
- 页面无内部返回目标：交给 Fragment / Activity 返回栈。

提前分发（ahead-of-time dispatch）要求在手势开始前就确定哪个处理器接管返回。官方 WebView codelab 在 `WebViewClient.doUpdateVisitedHistory()` 中用 `webView.canGoBack()` 更新 `OnBackPressedCallback.isEnabled`：有网页历史时由 WebView 回调接管，没有历史时禁用该回调，让外层 Fragment 或 Activity 处理。已有自定义 `WebViewClient` 时，应把这段状态更新并入原实现，不能为了处理返回而覆盖其他导航、证书或资源回调。

`canGoBack()` / `goBack()` 只提供历史判断与完成动作，并不提供一张可按手势进度控制的上一页画面。手势开始后要锁定本轮由 WebView 处理；进度回调只读取这个决定并更新容器或提示层，不反复查询历史、执行 JavaScript 或读取文档对象模型（DOM）。取消时只恢复容器，不能调用 `goBack()`。

## 扩展：跨 Activity 转场

跨 Activity 和返回主屏幕的动画属于系统转场。Android 15 起，这些动画不再依赖开发者选项；应用要移除根 Activity 上没有必要的消费型回调，并确认清单中没有临时关闭预测式返回。Android 16 增加观察型回调，允许日志在不消费返回的情况下运行；Android 17 则取消 API 36 只能注册一个此类回调的限制。

跨 Activity 自定义动画的风险之一是目标窗口的准备时间。如果返回目标 Activity 先前已被系统销毁，它需要重建复杂 View 树或重新绑定列表；在目标内容准备好之前，用户可能看到任务快照或尚未更新的内容。这不是每次跨 Activity 返回都会发生的固定流程，应结合 Activity 生命周期和实际轨迹判断。性能评估仍要包含返回目标 Activity 的首帧，并和 21.x 启动优化、22.10 Fragment 事务成本一起分析。

## 扩展：大屏、多窗口与折叠屏

大屏和多窗口下，返回手势的起始边缘、窗口宽度、任务边界和转场幅度都可能变化。动画距离不要写死为手机全屏宽度，应根据当前窗口边界或容器尺寸计算；折叠屏还要考虑铰链区域、分屏比例变化和任务窗口移动。

这类场景的测试范围至少覆盖手机全屏、平板横屏、分屏、桌面窗口和折叠屏展开态。每个场景都要测试完成与取消两条路径，因为取消路径更容易暴露状态恢复错误。

## 源码与文档入口

- [`OnBackInvokedDispatcher.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/OnBackInvokedDispatcher.java)、[`OnBackAnimationCallback.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/OnBackAnimationCallback.java) 与 [`BackEvent.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/BackEvent.java)：核对 Android 17 的回调优先级、观察型回调数量差异、进度、起始边缘与帧时间。
- [`WindowOnBackInvokedDispatcher.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/WindowOnBackInvokedDispatcher.java) 与 [`BackNavigationController.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/BackNavigationController.java)：核对窗口侧回调注册、最高优先级回调与 WMS 返回导航的控制范围。
- [Predictive Back 迁移](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture)、[Android 16 目标版本行为变化](https://developer.android.com/about/versions/16/behavior-changes-16)、[Compose 自定义动画](https://developer.android.com/guide/navigation/custom-back/support-animations) 与 [View / AndroidX Transition 动画](https://developer.android.com/guide/navigation/custom-back/support-animations-views)：核对临时关闭项、回调优先级、目标版本条件与 Android 14+ 进度动画。
- [AndroidX 版本总表](https://developer.android.com/jetpack/androidx/versions)、[Activity](https://developer.android.com/jetpack/androidx/releases/activity)、[Fragment](https://developer.android.com/jetpack/androidx/releases/fragment)、[Transition](https://developer.android.com/jetpack/androidx/releases/transition) 与 [NavigationEvent](https://developer.android.com/jetpack/androidx/releases/navigationevent) 发布说明：核对各库独立的版本号和预测式返回修复。
- [Fragment predictive back 动画](https://developer.android.com/guide/fragments/animate)、[NavigationEvent handle-back](https://developer.android.com/guide/navigation/navigation-event/handle-back)、[Navigation 3](https://developer.android.com/guide/navigation/navigation-3)、[WebView Back codelab](https://codelabs.developers.google.com/handling-gesture-back-navigation) 与 [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：核对受支持的动画类型、Compose 处理器状态、导航责任归属、WebView 回调启用状态与轨迹字段。

## 小结

预测式返回的性能重点是把返回拆成开始、进度、取消和完成四段，并让进度阶段只负责每帧能够完成的动画更新。Fragment、Compose、WebView 和 Activity 混合栈需要同时控制返回优先级、状态恢复和每帧成本。在 Perfetto 中，先按时间戳对应输入、主线程和应用 `SurfaceFrame`，再沿 RenderThread、SurfaceFlinger `DisplayFrame`、目标图层与呈现时间判断慢帧出现在哪个阶段。
