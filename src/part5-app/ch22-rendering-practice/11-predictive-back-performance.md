---
title: "Predictive Back 动画与页面切换性能"
chapter: "22.11"
section: "22.11"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37); AndroidX Activity 1.8.0+; AndroidX Fragment 1.7.0+; AndroidX Transition 1.5.0+; AndroidX NavigationEvent 1.0+"
last_verified: "2026-05-18"
last_verified_against: "Android Developers docs; AndroidX Activity / Fragment / Transition / NavigationEvent release notes; Perfetto FrameTimeline docs"
confidence: medium
tags: [predictive-back, rendering, animation, fragment, compose]
related_chapters: ["3.3", "7.4", "18.2", "22.3", "22.10"]
sources:
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture"
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

# Predictive Back 动画与页面切换性能

Predictive Back 把“返回”从一次离散事件改成一段可取消、可预览、可按进度驱动的交互。页面切换性能的判断点也随之移动：卡顿不再只发生在 `popBackStack()` 或 `finish()` 之后，手指从屏幕边缘滑动的每一帧都可能暴露主线程、布局、动画和合成成本。系统手势入口见 [§3.3 手势导航](../../part1-fundamentals/ch03-input/03-gesture-navigation.md)，View 一帧时序见 [§18.2 Android View 标准管线](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)，FragmentTransaction 的提交语义见 [§22.10 FragmentTransaction 提交链路](10-fragment-transaction-performance.md)；以下聚焦应用侧的接入、降级和 Perfetto 定位方法。

分析时把每帧计算量、状态读写范围、主线程排队和渲染提交分开看。任务调度会改变响应延迟，因此不要把数据加载、页面销毁和事务提交挤进 progress 回调。

平台 Back 分发和窗口动画固定到 Android 17 / API 37 的 `android-17.0.0_r1`；线程调度现象按 `android17-6.18-2026-06_r6` 观察。Activity、Fragment、Transition 与 NavigationEvent 都是独立发布的 AndroidX 库，版本结论以各自 release notes 为准，不能从 Android 17 platform tag 推导。

## Back 分发：Android 13 之后多了一段“可预览”的返回过程

Android 13 引入 `OnBackInvokedDispatcher` / `OnBackInvokedCallback`，提供新的返回完成分发；Android 14 的 `OnBackAnimationCallback` 才把 start、progress、cancel 事件公开给应用。AndroidX Activity 1.8.0 为 `OnBackPressedCallback` 增加 `handleOnBackStarted()`、`handleOnBackProgressed()`、`handleOnBackCancelled()` 和 `handleOnBackPressed()`，但 Android 13 及更低版本没有平台 progress 事件，不能运行按手势 fraction seek 的同等动画。

当前官方文档把 Predictive Back 视为默认启用能力，`android:enableOnBackInvokedCallback="false"` 用于应用级或 Activity 级 opt-out。设为 false 会关闭系统 predictive back 动画，并让系统忽略平台 `OnBackInvokedCallback`；AndroidX `OnBackPressedCallback` 仍会收到完成回调。Android 15 起，back-to-home、cross-task 与 cross-activity 系统动画不再依赖开发者选项，但仍要求对应 Activity 没有消费型 callback 抢走返回。

这几个入口的分工要拆开看：

- `OnBackInvokedCallback`：Android 13+ 的平台完成回调。用 `PRIORITY_DEFAULT` 或 `PRIORITY_OVERLAY` 注册消费型 callback 后，系统 predictive back 动画不再运行，应用要负责自己的 UI 反馈和返回动作。
- `OnBackAnimationCallback`：Android 14+ 的平台 progress 接口，继承 `OnBackInvokedCallback`，增加 started、progressed 和 cancelled；完成仍走 `onBackInvoked()`。
- `OnBackPressedDispatcher`：AndroidX 兼容层，低版本仍能处理返回完成；Activity 1.8.0+ 暴露四段式方法，只有 Android 14+ 能从平台得到连续 progress。
- `PredictiveBackHandler`：Compose 入口，来自 `androidx.activity:activity-compose:1.8.0+`，以 `Flow<BackEventCompat>` 提供手势事件；取消会结束 Flow 并抛出 `CancellationException`。
- `NavigationEventDispatcher`：面向 Compose、KMP 和自定义导航容器的更底层抽象。Activity 1.12.0 已把 `OnBackPressed` API 重写到 NavigationEvent 之上；截至 2026-07-29，Activity 稳定版为 1.13.0，NavigationEvent 稳定版为 1.1.2。

Android 16 增加 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER`：应用可以在不消费返回事件的前提下记录 root Activity 返回，系统 back-to-home 动画仍可播放。Android 17 的 `OnBackInvokedDispatcher` 明确写出版本差异：API 36 同时只能注册一个 observer callback，API 37 起不再限制数量。observer 只适合日志或不改变导航结果的收尾工作，不能拦截返回，也不要负责页面切换。

## 手势进度进入动画系统后，回调只能做每帧能承受的事

Predictive Back 事件至少包含四类信号：

- start: 手势开始，适合创建或取得动画控制对象，记录起始状态。
- progress: 手指移动过程，`progress` 取值范围为 `0f..1f`，用于 seek 动画；它已经由系统按手势模型插值，不要再按“滑动像素 ÷ 屏幕宽度”重复计算。`swipeEdge` 用于区分左右边缘，Android 16 / API 36 还加入 `frameTimeMillis` 与代表三键或硬件返回的 `EDGE_NONE`；AndroidX Activity 1.11.0 把这两个字段带入 `BackEventCompat`。
- cancel: 手势取消，应用必须把临时 UI 状态恢复到起点。
- complete: 手势越过提交阈值，应用执行返回动作，例如 `popBackStack()`、`finish()` 或更新导航状态。

相较于会触发 measure / layout 的参数，`translationX`、`alpha`、`scaleX`、`scaleY` 更适合由 progress 驱动，但大图层的透明度和缩放仍会增加 GPU 或合成压力。Fragment transition 和 shared element transition 还可能牵涉 View 层级匹配、Transition 捕获和目标状态计算。Compose 接入时，进度事件会进入状态系统，读取范围如果没有压住，手势期间可能反复执行 Composition + Layout。

这段 Kotlin 展示 View 场景下的最小接入方式。`handleOnBackProgressed()` 只写不会触发布局的属性，完成回调直接交给当前导航 owner，避免再次分发同一个返回事件。

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

`onBackCommitted` 应由 FragmentManager、NavController、Navigation 3 back stack 或页面自己的状态机提供。Activity 1.9.0 已加入 lint 警告：在 `OnBackPressedCallback`、`BackHandler` 或 `PredictiveBackHandler` 处理期间再次调用 `onBackPressedDispatcher.onBackPressed()`，会破坏 predictive back animation。`EDGE_NONE` 没有边缘位移可映射，示例只保留 alpha / scale 收尾；产品也可以直接降级成离散返回。

## Fragment / Navigation：手势期间不要制造新的页面切换成本

Fragment 1.7.0+ 支持 predictive in-app back，但连续 seek 只在 Android 14 / API 34+ 生效。返回事务使用 `Animator` 或 AndroidX Transition 1.5.0+ 时，FragmentManager 可以按手势进度 seek，再根据完成或取消提交或回滚；旧 `Animation` 和 framework `Transition` 不支持这条路径。

版本边界要写进治理清单：

| 场景 | 最低版本 | 性能边界 |
| --- | --- | --- |
| `OnBackPressedCallback` progress API | Activity 1.8.0+；连续 progress 需要 Android 14+ | progress 回调内只更新动画状态，不做导航提交 |
| AndroidX Transition seek | Transition 1.5.0+，Android 14+ | 用 `controlDelayedTransition()` / `TransitionSeekController` 控制进度 |
| Fragment predictive back | Fragment 1.7.0+，Android 14+ | 返回事务涉及的动画必须全是 `Animator` 或可 seek 的 AndroidX Transition |
| Compose `PredictiveBackHandler` | Activity Compose 1.8.0+；连续 progress 需要 Android 14+ | 进度状态读写范围要限制在动画层 |
| NavigationEvent | NavigationEvent 1.0+ | 手势状态与导航历史分开观察，避免每帧改导航栈 |

Fragment 官方 release notes 中多次修复 predictive back 取消、快速连续返回、空白页、生命周期状态不一致等问题。这说明工程接入时不能只看 API 是否存在，还要固定最低 Fragment / Transition 版本，并把取消回滚作为测试用例。

截至 2026-07-29，Activity 稳定版是 1.13.0、Fragment 是 1.8.9、Transition 是 1.7.0。Activity 1.12.2 修复了 lifecycle-aware callback 的 `isEnabled` 状态问题；Fragment 与 Transition 已进入 maintenance mode。新工程应优先评估当前稳定版，表中的最低版本只表示功能入口出现，不代表包含后续取消、predictive back 与生命周期修复。

Fragment 页面切换的性能边界可以按三段预算拆：

- 手势开始: 准备动画控制对象、读取当前 View 尺寸、确认 FragmentManager 已有可预览的返回目标。不要在应用 callback 里手动 inflate 上一页。
- 手势进行: 只改动画 fraction 或可合成属性。不要在这里执行 `commitNow()`、网络请求、数据库读取、图片解码、WebView 初始化。
- 手势完成: 只提交返回动作与轻量状态。生命周期要求同步释放的引用照常清理；磁盘写入、缓存整理和其他阻塞工作交给后台线程，不能靠 `post` 到下一帧来维持正确性。

`TransitionManager.controlDelayedTransition()` 的用法与普通 `beginDelayedTransition()` 不同：前者返回可控制进度的对象，适合把 `BackEvent.progress` 映射到 `currentFraction`；后者启动后由时间驱动，不适合手势直接 seek。

下面的代码只展示同一 View 容器内部状态的 transition seek，不要把它套在 FragmentManager 已经接管的 predictive back 事务外层。

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

`controlDelayedTransition()` 需要 Android 14+，并且每次动画只使用一个 controller；自定义 Transition 还要明确支持 seeking。这里的排查点是 `showPreviousStateForPreview()`：如果它触发新的 Fragment inflate、`RecyclerView` 首屏绑定或图片加载，返回手势一开始就会吃掉主线程预算。Fragment 返回栈由 Fragment 1.7+ 自己 seek 时，不应再手动创建第二个 controller 或额外调用 `popBackStack()`；事务执行边界见 [§22.10](10-fragment-transaction-performance.md)。

## Compose NavigationEvent：把进度状态限制在动画层

Compose 需要先判断导航 owner。Navigation 3 已内建 predictive back 时，使用它提供的 back stack 和动画，不再叠加自定义 handler；`PredictiveBackHandler` 适合页面内自定义动画；NavigationEvent 适合自定义导航容器、跨平台组件或需要独立观察手势状态的场景。官方 NavigationEvent 文档把 `NavigationEventTransitionState.InProgress`、`rememberNavigationEventState()`、`NavigationBackHandler()` 组合使用：`transitionState` 表示手势状态，导航历史由另一组状态描述。

Compose 的性能风险来自状态读取位置。`progress` 如果被上层导航容器、整页 scaffold 或复杂列表读取，手指移动会扩大重组范围；如果在 `graphicsLayer` 更新块内读取稳定的 State 对象，变化可以直接失效 layer 属性，避开 Composition 和 Layout。Compose 的状态读取阶段与排查方法见 [§22.3 Compose 性能](03-compose-performance.md)。

这段 Compose 代码接收稳定的 `FloatState` / `State<Int>` 对象，并只在 `graphicsLayer` 更新块里读取它们。调用方应通过 `remember { mutableFloatStateOf(...) }` 等方式保留同一 State 实例。

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

这里的 layer 更新不会自动让内容获得“零成本动画”：大面积 alpha、scale 仍可能增加离屏或 GPU 合成压力；`content()` 内部读取同一个 progress 状态，也会扩大失效范围。用 Compose tracing 检查 Composition / Layout 是否随手势反复出现，再沿 RenderThread、GPU 和 SurfaceFlinger 检查显示后段。

取消路径要和完成路径同等测试。`PredictiveBackHandler` 的 Flow 会在取消时抛出 `CancellationException`；Activity release notes 还记录过“同一帧禁用后仍处理手势”、callback 顺序与 lifecycle-aware `isEnabled` 的问题。handler 应保持在 Composition 中，通过 `enabled` 表达是否接管返回，避免在条件分支里反复添加和移除。工程测试至少覆盖快速半滑取消、连续返回、返回过程中页面状态变化、空返回栈和配置变更后返回。

## Perfetto：按输入、主线程、FrameTimeline、RenderThread 四段定位

Predictive Back 的慢帧通常分四类：输入分发慢、主线程进度回调慢、布局/重组扩大、渲染提交或 GPU 完成慢。Perfetto 不只看一条主线程轨道，要把输入、`Choreographer#doFrame`、FrameTimeline、RenderThread、SurfaceFlinger 放在同一时间窗口里读。

| 观察对象 | Perfetto 里看什么 | 典型结论 |
| --- | --- | --- |
| 输入事件 | InputDispatcher / app 主线程消息间隔 | 手势事件进入应用前已经排队，问题偏系统负载或主线程消息拥塞 |
| 主线程回调 | `handleOnBackProgressed()` 附近的自定义 trace、`Choreographer#doFrame` | 每帧计算、状态写入、同步 I/O 或锁等待占用预算 |
| View / Compose 布局 | `performTraversals`、Compose composition / layout slice | progress 触发 measure / layout 或大范围重组 |
| RenderThread | `DrawFrame`、`syncAndDrawFrame`、GPU submit | 主线程轻但绘制复杂，可能是阴影、模糊、大图层或过多 RenderNode 更新 |
| FrameTimeline（Android 12+） | App `SurfaceFrame` 与 SF `DisplayFrame` 的 Expected / Actual、jank reason | 区分应用生产未按 deadline 与显示侧合成 / present 超期 |
| SurfaceFlinger | `BufferTX`、目标 layer latch、composition 与 present timing | 应用侧交帧及时但系统采纳或显示晚，继续查 buffer、fence、GPU / HWC |

FrameTimeline 从 Android 12 起可用。App actual `SurfaceFrame` 的结束位置综合 buffer post 与 GPU completion，用来判断应用侧是否按 deadline 产出；SF actual `DisplayFrame` 才继续覆盖 layer latch、合成与 present。App actual 按时不能证明窗口已经显示，仍要对齐 SF DisplayFrame、目标 layer 和 present timing。

下面的 trace 示例使用固定 section 名，并用 counter 保存 progress，便于把回调成本和手势位置对齐：

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

不要把百分比、页面 ID 或 URL 拼进 section 名；那会制造高基数 slice，妨碍聚合。输入 progress 事件也不等于 Choreographer 帧，分析时按时间戳对齐相邻 App `SurfaceFrame`，再回主线程与 RenderThread 判断这次属性更新落入哪一帧。

## 工程治理清单

Predictive Back 接入不要一次改完整个导航系统。更稳的路径是按页面类型分层推进：

1. 清点返回入口：Activity、Fragment、Compose、WebView、Dialog、底部弹窗分别列出当前使用的 `onBackPressed()`、`OnBackPressedCallback`、`BackHandler`、`OnBackInvokedCallback`。
2. 固定依赖：记录 Activity、Fragment、Transition、Navigation / NavigationEvent 的确切版本。新接入优先使用当前稳定线；最低版本只用于解释功能边界。
3. 审计 opt-out：检查 application 与各 Activity 的 `android:enableOnBackInvokedCallback`。从返回目标单一的页面开始移除 false，再验证系统动画、自定义 callback 和低版本回退。
4. 分离埋点和消费：日志走 Android 16+ 的 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 或在页面销毁时记录，不要用消费型 callback 只为了打点。API 36 还要遵守只能注册一个 observer 的限制。
5. 压低 progress 回调成本：只改属性、fraction 或轻量状态；禁止同步 I/O、图片解码、数据库读取、网络请求和新的 Fragment 事务。
6. 控制动画对象生命周期：Transition 配置、Animator、`Animatable` 与 `graphicsLayer` 容器避免每帧重建；`TransitionSeekController` 每次手势创建一个，取消或完成后丢弃。
7. 覆盖取消测试：半滑取消、快速连续返回、返回时切后台、横竖屏切换、空返回栈、进程恢复后返回。
8. 建立 Perfetto 基线：每类页面至少留一条正常返回 trace 和一条半滑取消 trace，记录设备刷新率、Android 版本、Activity / Fragment / Compose 版本。

混合栈页面要显式定义返回优先级：WebView history、页面内弹层、Fragment back stack、Activity finish 不能同时抢同一次手势。优先级不清会产生更严重的语义错误：preview 指向一个目标，完成后却退到另一个目标。

## 扩展：WebView predictive back

WebView 有自己的 `canGoBack()` / `goBack()` 历史栈。页面里嵌 WebView 时，返回优先级建议写成状态机：

- WebView 可回退: 手势开始时固定本次目标为网页历史；progress 只驱动 WebView 容器或提示层，完成后调用 `webView.goBack()`，Activity 不出栈。
- WebView 不可回退但页面有弹层: 弹层消费返回，手势动画绑定弹层退出。
- 页面无内部返回目标: 交给 Fragment / Activity 返回栈。

ahead-of-time 分发要求手势开始前就确定谁接管返回。官方 WebView codelab 在 `WebViewClient.doUpdateVisitedHistory()` 中用 `webView.canGoBack()` 更新 `OnBackPressedCallback.isEnabled`：有网页历史时由 WebView callback 接管，没有历史时禁用 callback，让外层 Fragment 或 Activity 成为下一位 owner。已有自定义 `WebViewClient` 时应把这段状态更新并入原实现，不能为了返回处理覆盖其他导航、证书或资源回调。

`canGoBack()` / `goBack()` 只提供历史判断与完成动作，没有提供上一网页的可 seek surface。手势开始后要锁定本轮 WebView owner；progress 只读这个决定并更新容器或提示层，不反复查询历史、执行 JavaScript 或读取 DOM。取消时只恢复容器，不能调用 `goBack()`。

## 扩展：跨 Activity 转场

跨 Activity 和 back-to-home 动画属于系统可见转场。Android 15 起相关系统动画不再依赖开发者选项；应用要移除 root Activity 上无必要的消费型 callback，并确认没有通过 manifest opt-out。Android 16 增加观察型 callback，允许日志在不消费返回的情况下运行；Android 17 则取消 API 36 的单 observer 数量限制。

跨 Activity 自定义动画的风险在于目标窗口准备时间。如果上一个 Activity 需要冷启动、恢复复杂 View 树或重新绑定列表，手势预览阶段会露出空白、快照或旧内容。治理动作是把返回目标 Activity 的首帧准备纳入页面切换预算，和 21.x 启动优化、22.10 Fragment 事务预算一起看。

## 扩展：大屏、多窗口与 foldable

大屏和多窗口下，返回手势的 edge、窗口宽度、任务边界和转场幅度都可能变化。动画距离不要写死为手机全屏宽度，应该基于当前 window bounds 或容器尺寸计算；foldable 还要考虑铰链区域、分屏比例变化和任务窗口移动。

这类场景的测试范围至少覆盖：手机全屏、平板横屏、分屏、桌面窗口、foldable 展开态。每个场景都要跑完成与取消两条路径，因为取消路径更容易暴露状态恢复错误。

## 源码与文档入口

- [`OnBackInvokedDispatcher.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/OnBackInvokedDispatcher.java)、[`OnBackAnimationCallback.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/OnBackAnimationCallback.java) 与 [`BackEvent.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/BackEvent.java)：核对 Android 17 callback priority、observer 数量差异、progress、edge 与 frame time。
- [`WindowOnBackInvokedDispatcher.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/WindowOnBackInvokedDispatcher.java) 与 [`BackNavigationController.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/BackNavigationController.java)：核对窗口侧 callback 注册、top callback 与 WMS back navigation 控制边界。
- [Predictive Back 迁移](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture)、[Compose 自定义动画](https://developer.android.com/guide/navigation/custom-back/support-animations) 与 [View / AndroidX Transition 动画](https://developer.android.com/guide/navigation/custom-back/support-animations-views)：核对 opt-out、callback 优先级与 Android 14+ progress 动画。
- [Activity](https://developer.android.com/jetpack/androidx/releases/activity)、[Fragment](https://developer.android.com/jetpack/androidx/releases/fragment)、[Transition](https://developer.android.com/jetpack/androidx/releases/transition) 与 [NavigationEvent](https://developer.android.com/jetpack/androidx/releases/navigationevent) release notes：核对独立 AndroidX 版本和 predictive back 修复。
- [Fragment predictive back 动画](https://developer.android.com/guide/fragments/animate)、[NavigationEvent handle-back](https://developer.android.com/guide/navigation/navigation-event/handle-back)、[Navigation 3](https://developer.android.com/guide/navigation/navigation-3)、[WebView Back codelab](https://codelabs.developers.google.com/handling-gesture-back-navigation) 与 [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：核对受支持的动画类型、Compose handler 状态、内建导航 owner、WebView callback enabled 状态与 trace 字段。

## 小结

Predictive Back 的性能治理重点是把返回拆成 start、progress、cancel、complete 四段，并让 progress 阶段只负责每帧能完成的动画更新。Fragment、Compose、WebView 和 Activity 混合栈需要同时管住返回优先级、状态恢复和每帧成本。Perfetto 中先对齐输入、主线程和 App `SurfaceFrame`，再沿 RenderThread、SF `DisplayFrame`、目标 layer 与 present timing 判断慢帧落在哪一段。
