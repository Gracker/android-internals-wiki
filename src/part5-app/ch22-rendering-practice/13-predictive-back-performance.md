---
title: "Predictive Back 动画与页面切换性能"
chapter: "22.13"
section: "22.13"
status: ready-for-review
drafted_date: "2026-05-18"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37); AndroidX Activity 1.8.0+; AndroidX Fragment 1.7.0+; AndroidX Transition 1.5.0+; AndroidX NavigationEvent 1.0+"
last_verified: "2026-05-18"
last_verified_against: "Android Developers docs; AndroidX Activity / Fragment / Transition / NavigationEvent release notes; Perfetto FrameTimeline docs"
confidence: medium
tags: [predictive-back, rendering, animation, fragment, compose]
related_chapters: ["3.3", "7.4", "18.2", "22.3", "22.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "官方文档/AndroidX 版本演进/AOSP 结构"
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

# 22.13 Predictive Back 动画与页面切换性能

<!-- outline-start -->
## 要点

### 🔹 平台 Back 分发与 AndroidX 兼容层
从 `OnBackInvokedCallback`、`OnBackInvokedDispatcher`、`OnBackPressedDispatcher` 和 AndroidX Activity 的桥接关系建立版本边界，说明 Android 13+ predictive back 与旧回退处理的差异。

### 🔹 手势进度如何进入动画系统
整理 predictive back 事件中的 progress、edge、cancel、complete 四类信号，区分 View property animation、Fragment transition、Activity transition 和 Compose `NavigationEvent` 的接入方式。

### 🔹 Fragment / Navigation 页面切换性能边界
结合 Fragment 1.7+、Transition 1.5+ 和 Navigation 版本演进，说明返回手势期间哪些工作应限制在动画属性更新，哪些 View inflate、数据加载和事务提交要避开手势进行中阶段。

### 🔹 Compose NavigationEvent 与重组成本
分析 `NavigationEventHandler`、`rememberNavigationEventState`、`NavigationEventTransitionState.InProgress` 的使用边界，重点检查手势进度驱动状态更新时的重组范围、布局成本和取消回滚逻辑。

### 🔹 Perfetto 观察点与问题定位
列出输入事件、主线程消息、Choreographer、FrameTimeline、RenderThread 和 GPU completion 的观察点，用于区分输入分发延迟、动画每帧计算过重、布局重算和合成阶段阻塞。

### 🔹 工程治理清单
给出接入 predictive back 的最小改造路径：版本开关、回调注册顺序、动画对象复用、手势取消复位、页面释放时机、WebView / Fragment / Compose 混合栈的兜底策略。

## 扩展

### 🔸 WebView predictive back
梳理 WebView 自身历史返回与 Activity 返回手势之间的优先级，避免页面内回退和系统返回动画互相抢占。

### 🔸 跨 Activity 转场
补充自定义 cross-activity predictive back 动画的版本要求、性能风险和低版本降级方案。

### 🔸 大屏与多窗口场景
分析 predictive back 在多窗口、桌面模式和 foldable 上的边缘手势、动画幅度和窗口尺寸变化问题。

<!-- outline-end -->

Predictive Back 把“返回”从一次离散事件改成一段可取消、可预览、可按进度驱动的交互。页面切换性能的判断点也随之移动：卡顿不再只发生在 `popBackStack()` 或 `finish()` 之后，手指从屏幕边缘滑动的每一帧都可能暴露主线程、布局、动画和合成成本。系统手势入口见 3.3 节，View 一帧时序见 18.2 节，FragmentTransaction 的提交语义见 22.12 节；本节关注应用侧怎么接入、怎么降级、怎么用 Perfetto 定位慢帧。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md] 参考书把速度问题拆成 CPU 指令、缓存命中和任务调度三类成本，本节沿用这种拆法：每帧计算量、状态读写范围、主线程排队和渲染提交分开看。[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md] 参考书强调任务调度会改变响应延迟，本节把这个点落在返回手势期间：不要把数据加载、页面销毁和事务提交挤进 progress 回调。

## Back 分发：Android 13 之后多了一段“可预览”的返回过程

Android 13 引入 `OnBackInvokedDispatcher` / `OnBackInvokedCallback`，应用可通过 manifest 的 `android:enableOnBackInvokedCallback` 选择是否启用 predictive back 系统动画。AndroidX Activity 继续保留 `OnBackPressedDispatcher`，并在 Activity 1.8.0 起给 `OnBackPressedCallback` 增加 `handleOnBackStarted()`、`handleOnBackProgressed()`、`handleOnBackCancelled()` 和 `handleOnBackPressed()` 四段式回调。[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back-gesture][已验证: 官方文档, developer.android.com/jetpack/androidx/releases/activity]

这几个入口的分工要拆开看：

- `OnBackInvokedCallback`: 平台 API，面向 Android 13+。如果用 `PRIORITY_DEFAULT` 或 `PRIORITY_OVERLAY` 消费返回事件，系统的 predictive back 动画不会继续播放，应用要自己完成返回处理。
- `OnBackPressedDispatcher`: AndroidX 兼容层，旧版本仍可工作；Activity 1.8.0+ 通过 `OnBackPressedCallback` 暴露手势开始、进度、取消和完成。
- `PredictiveBackHandler`: Compose 入口，来自 `androidx.activity:activity-compose:1.8.0+`，以 `Flow<BackEventCompat>` 形式提供进度事件。
- `NavigationEventDispatcher`: AndroidX NavigationEvent 的更底层抽象，面向 Compose、KMP 和自定义导航容器；Activity 1.12 系列已经把部分 Back API 改到 NavigationEvent 之上。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/navigationevent]

Android 16 增加 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 的使用场景：应用可以在不消费返回事件的前提下记录 root Activity 的返回行为或执行业务清理，系统 back-to-home 动画仍然播放。[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back-gesture] 这类观察回调适合埋点，不适合放页面切换逻辑。

## 手势进度进入动画系统后，回调只能做每帧能承受的事

Predictive Back 事件至少包含四类信号：

- start: 手势开始，适合创建或取得动画控制对象，记录起始状态。
- progress: 手指移动过程，`progress` 取值范围为 `0f..1f`，`swipeEdge` / `edge` 用于区分左右边缘方向，Android 16 还把 `frameTimeMillis` 和 `EDGE_NONE` 带入 AndroidX `BackEventCompat`。
- cancel: 手势取消，应用必须把临时 UI 状态恢复到起点。
- complete: 手势越过提交阈值，应用执行返回动作，例如 `popBackStack()`、`finish()` 或更新导航状态。

View property animation 的成本最低，通常只改 `translationX`、`alpha`、`scaleX`、`scaleY` 这类不触发布局的属性。Fragment transition 和 shared element transition 的成本更高，因为它们可能牵涉 View 层级匹配、Transition 捕获和目标状态计算。Compose 接入时，进度事件会进入状态系统，重组范围如果没有压住，每帧都可能变成 Composition + Layout 的组合成本。

这段 Kotlin 展示 View 场景下的最小接入方式；重点是 `handleOnBackProgressed()` 只写属性，返回提交放到 `handleOnBackPressed()`。

```kotlin
val callback = object : OnBackPressedCallback(true) {
    override fun handleOnBackStarted(backEvent: BackEventCompat) {
        contentView.animate().cancel()
        contentView.pivotX = if (backEvent.swipeEdge == BackEventCompat.EDGE_LEFT) 0f else contentView.width.toFloat()
    }

    override fun handleOnBackProgressed(backEvent: BackEventCompat) {
        val p = backEvent.progress.coerceIn(0f, 1f)
        contentView.translationX = if (backEvent.swipeEdge == BackEventCompat.EDGE_LEFT) p * contentView.width else -p * contentView.width
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
        isEnabled = false
        requireActivity().onBackPressedDispatcher.onBackPressed()
    }
}
```

这段代码的风险点在收尾两行：Activity release notes 已提示，在处理返回时再调用 `onBackPressedDispatcher.onBackPressed()` 会破坏 predictive back animation 的连续性。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/activity] 工程里更稳的做法是让当前导航容器直接执行 `popBackStack()` 或业务定义的完成动作，避免把同一个返回事件再次塞回 dispatcher。

## Fragment / Navigation：手势期间不要制造新的页面切换成本

Fragment 1.7.0+ 支持 predictive in-app back：使用 `Animator` 或 AndroidX Transition 1.5.0+ 时，Fragment 可以按返回手势进度 seek 到上一个 Fragment，再根据完成或取消决定提交或回滚。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/fragment][已验证: 官方文档, developer.android.com/jetpack/androidx/releases/transition]

版本边界要写进治理清单：

| 场景 | 最低版本 | 性能边界 |
| --- | --- | --- |
| `OnBackPressedCallback` progress API | Activity 1.8.0+ | progress 回调内只更新动画状态，不做导航提交 |
| AndroidX Transition seek | Transition 1.5.0+，Android 14+ | 用 `controlDelayedTransition()` / `TransitionSeekController` 控制进度 |
| Fragment predictive back | Fragment 1.7.0+ | 同一事务内所有 Fragment 要使用 `Animator` 或可 seek 的 AndroidX Transition |
| Compose `PredictiveBackHandler` | Activity Compose 1.8.0+ | 进度状态读写范围要限制在动画层 |
| NavigationEvent | NavigationEvent 1.0+ | 手势状态与导航历史分开观察，避免每帧改导航栈 |

Fragment 官方 release notes 中多次修复 predictive back 取消、快速连续返回、空白页、生命周期状态不一致等问题。这说明工程接入时不能只看 API 是否存在，还要固定最低 Fragment / Transition 版本，并把取消回滚作为测试用例。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/fragment]

Fragment 页面切换的性能边界可以按三段预算拆：

- 手势开始: 准备动画控制对象、读取当前 View 尺寸、确认目标 Fragment 已具备可预览状态。不要在这里 inflate 大布局。
- 手势进行: 只改动画 fraction 或可合成属性。不要在这里执行 `commitNow()`、网络请求、数据库读取、图片解码、WebView 初始化。
- 手势完成: 提交返回动作和资源释放。大对象释放、埋点上报、缓存刷新应延后到下一帧之后，或者转到后台线程。

`TransitionManager.controlDelayedTransition()` 的用法与普通 `beginDelayedTransition()` 不同：前者返回可控制进度的对象，适合把 `BackEvent.progress` 映射到 `currentFraction`；后者启动后由时间驱动，不适合手势直接 seek。[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/support-animations-views]

这段代码只展示 transition 进度控制的形状；真实项目要把目标状态计算和 Fragment 事务放到导航容器里。

```kotlin
private var seekController: TransitionSeekController? = null

val callback = object : OnBackPressedCallback(true) {
    override fun handleOnBackStarted(backEvent: BackEventCompat) {
        val transition = TransitionSet()
            .addTransition(Fade(Fade.MODE_OUT))
            .addTransition(ChangeBounds())
            .addTransition(Fade(Fade.MODE_IN))
        seekController = TransitionManager.controlDelayedTransition(container, transition)
        showPreviousStateForPreview()
    }

    override fun handleOnBackProgressed(backEvent: BackEventCompat) {
        seekController?.currentFraction = backEvent.progress.coerceIn(0f, 1f)
    }

    override fun handleOnBackCancelled() {
        seekController?.animateToStart()
        restoreCurrentState()
    }

    override fun handleOnBackPressed() {
        seekController?.animateToEnd()
        navController.popBackStack()
    }
}
```

这里的排查点是 `showPreviousStateForPreview()`：如果它触发新的 Fragment inflate、`RecyclerView` 首屏绑定或图片加载，返回手势一开始就会吃掉主线程预算。详见 22.12 节，FragmentTransaction 的提交时机与帧回调不是同一个概念。

## Compose NavigationEvent：把进度状态限制在动画层

Compose 有两条接入路径：`PredictiveBackHandler` 适合页面内自定义动画；NavigationEvent 适合自定义导航容器、跨平台组件或需要观察手势状态与导航历史的场景。官方 NavigationEvent 文档把 `NavigationEventTransitionState.InProgress`、`rememberNavigationEventState()`、`NavigationBackHandler()` 组合在一起使用：`transitionState` 表示物理手势状态，导航历史由另一组状态描述。[已验证: 官方文档, developer.android.com/guide/navigation/navigation-event/handle-back]

Compose 的性能风险来自状态读取位置。`progress` 如果被上层 `NavHost`、整页 scaffold 或复杂列表读取，手指移动的每一帧都会扩大重组范围；如果只在动画 wrapper 中读取，成本通常只落在少量 modifier 更新和绘制阶段。详见 22.3 节，Compose 的状态读取阶段决定了重组、布局、绘制三段成本分布。

这段 Compose 代码把 progress 读在页面外层动画容器里，业务内容不直接读取 progress。

```kotlin
@Composable
fun PredictiveBackPage(
    progress: Float,
    edge: Int,
    content: @Composable () -> Unit,
) {
    val direction = if (edge == BackEventCompat.EDGE_LEFT) 1f else -1f
    Box(
        modifier = Modifier
            .graphicsLayer {
                translationX = size.width * progress * direction
                alpha = 1f - progress * 0.18f
                scaleX = 1f - progress * 0.04f
                scaleY = 1f - progress * 0.04f
            }
    ) {
        content()
    }
}
```

`graphicsLayer` 可以把变换限制在绘制与合成相关路径，避免 progress 直接驱动整页布局。仍要用 Perfetto 或 Compose tracing 复核，因为 `content()` 内部如果读取同一个状态，重组范围仍会扩大。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/activity]

取消路径要和完成路径同等测试。`PredictiveBackHandler` 的 Flow 会在取消时抛出 `CancellationException`，Activity release notes 也记录过“同一帧禁用后仍处理手势”“回调顺序变化”“disabled 状态切换”等问题。工程里要覆盖这些用例：快速半滑取消、连续返回、返回过程中页面状态变化、空返回栈、配置变更后返回。

## Perfetto：按输入、主线程、FrameTimeline、RenderThread 四段定位

Predictive Back 的慢帧通常分四类：输入分发慢、主线程进度回调慢、布局/重组扩大、渲染提交或 GPU 完成慢。Perfetto 不只看一条主线程轨道，要把输入、`Choreographer#doFrame`、FrameTimeline、RenderThread、SurfaceFlinger 放在同一时间窗口里读。

| 观察对象 | Perfetto 里看什么 | 典型结论 |
| --- | --- | --- |
| 输入事件 | InputDispatcher / app 主线程消息间隔 | 手势事件进入应用前已经排队，问题偏系统负载或主线程消息拥塞 |
| 主线程回调 | `handleOnBackProgressed()` 附近的自定义 trace、`Choreographer#doFrame` | 每帧计算、状态写入、同步 I/O 或锁等待占用预算 |
| View / Compose 布局 | `performTraversals`、Compose composition / layout slice | progress 触发 measure / layout 或大范围重组 |
| RenderThread | `DrawFrame`、`syncAndDrawFrame`、GPU submit | 主线程轻但绘制复杂，可能是阴影、模糊、大图层或过多 RenderNode 更新 |
| FrameTimeline | Expected / Actual Timeline、jank reason | 实际完成时间超过预测呈现时间，能判断慢帧是否已经用户可见 |
| SurfaceFlinger | App frame 到达后的合成时间 | 应用提交及时但合成侧拥塞，继续查层数、buffer、GPU completion |

FrameTimeline 从 Android 12 起可用，Expected Timeline 表示系统给应用的渲染预算，Actual Timeline 表示应用完成一帧并交给 SurfaceFlinger 的时间，包含 GPU work 与 post time。[已验证: 官方文档, perfetto.dev/docs/data-sources/frametimeline] Android Vitals 文档也建议用 Perfetto FrameTimeline 跟踪 slow frame / frozen frame。[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

建议给返回手势加三类自定义 trace：

```kotlin
Trace.beginSection("pb_started")
Trace.endSection()

Trace.beginSection("pb_progress:${(backEvent.progress * 100).toInt()}")
Trace.endSection()

Trace.beginSection("pb_cancel_or_commit")
Trace.endSection()
```

这些 slice 不用于证明性能变好，只用于把手势状态对齐到 FrameTimeline。看到某一段 progress 后 Actual Timeline 连续超过 Expected Timeline，再回主线程和 RenderThread 找对应成本。

## 工程治理清单

Predictive Back 接入不要一次改完整个导航系统。更稳的路径是按页面类型分层推进：

1. 清点返回入口：Activity、Fragment、Compose、WebView、Dialog、底部弹窗分别列出当前使用的 `onBackPressed()`、`OnBackPressedCallback`、`BackHandler`、`OnBackInvokedCallback`。
2. 固定最低版本：Activity 1.8.0+ 才有 progress API；Fragment predictive back 建议 Fragment 1.7.1+ 与 Transition 1.5.0+ 起步，避免早期取消回滚问题。
3. 打开系统开关：manifest 里逐 Activity 配置 `android:enableOnBackInvokedCallback`，先覆盖单一返回栈页面，再覆盖混合栈页面。
4. 分离埋点和消费：日志、业务清理走 Android 16 的 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 或完成后异步任务；不要用消费型 callback 只为了打点。
5. 压低 progress 回调成本：只改属性、fraction 或轻量状态；禁止同步 I/O、图片解码、数据库读取、网络请求和新的 Fragment 事务。
6. 复用动画对象：Transition、Animator、`Animatable`、`graphicsLayer` 容器尽量复用，避免每帧分配。
7. 覆盖取消测试：半滑取消、快速连续返回、返回时切后台、横竖屏切换、空返回栈、进程恢复后返回。
8. 建立 Perfetto 基线：每类页面至少留一条正常返回 trace 和一条半滑取消 trace，记录设备刷新率、Android 版本、Activity / Fragment / Compose 版本。

[自动发现] 混合栈页面要显式定义返回优先级：WebView history、页面内弹层、Fragment back stack、Activity finish 不能同时抢同一次手势。优先级不清时，最常见的问题不是慢帧，而是 preview 指向一个页面，完成后却退到另一个页面。

## 扩展：WebView predictive back

WebView 有自己的 `canGoBack()` / `goBack()` 历史栈。页面里嵌 WebView 时，返回优先级建议写成状态机：

- WebView 可回退: 当前手势只驱动 WebView 容器动画，完成后调用 `webView.goBack()`，Activity 不出栈。
- WebView 不可回退但页面有弹层: 弹层消费返回，手势动画绑定弹层退出。
- 页面无内部返回目标: 交给 Fragment / Activity 返回栈。

WebView 场景不要在 progress 回调里查询复杂 DOM 状态或执行 JavaScript。`canGoBack()` 这类状态应在页面加载完成、history 变化或用户操作后缓存成普通字段，返回手势只读缓存值。[待验证: WebView 内部 history 状态与 predictive back observer 的最佳实践缺少官方专项文档]

## 扩展：跨 Activity 转场

跨 Activity 和 back-to-home 动画属于系统可见转场。Android 13/14 的主要迁移动作是启用 manifest 开关并停止拦截 root Activity 的系统返回；Android 16 增加观察型 callback，允许不消费事件的日志和业务处理。[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back-gesture]

跨 Activity 自定义动画的风险在于目标窗口准备时间。如果上一个 Activity 需要冷启动、恢复复杂 View 树或重新绑定列表，手势预览阶段会露出空白、快照或旧内容。治理动作是把返回目标 Activity 的首帧准备纳入页面切换预算，和 21.x 启动优化、22.12 Fragment 事务预算一起看。

## 扩展：大屏、多窗口与 foldable

大屏和多窗口下，返回手势的 edge、窗口宽度、任务边界和转场幅度都可能变化。动画距离不要写死为手机全屏宽度，应该基于当前 window bounds 或容器尺寸计算；foldable 还要考虑铰链区域、分屏比例变化和任务窗口移动。

这类场景的测试矩阵至少覆盖：手机全屏、平板横屏、分屏、桌面窗口、foldable 展开态。每个场景都要跑完成与取消两条路径，因为取消路径更容易暴露状态恢复错误。

## 小结

Predictive Back 的性能治理重点是把返回拆成 start、progress、cancel、complete 四段，并让 progress 阶段只承担每帧能完成的动画更新。Fragment、Compose、WebView 和 Activity 混合栈的难点不在 API 调用，而在返回优先级、状态恢复和每帧成本控制。Perfetto 的 FrameTimeline 可以把手势进度和可见慢帧对齐，定位时按输入、主线程、布局/重组、RenderThread 和合成阶段依次排查。
