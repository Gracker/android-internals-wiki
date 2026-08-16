---
title: "动画性能优化"
chapter: "22.5"
section: "22.5"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1; Lottie 6.7.1; ConstraintLayout 2.2.2"
confidence: high
sources:
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: research
    path: "Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-rendereffect-gpu-rendering-pipeline-analysis.md"
  - type: source
    path: "intake/external-resources/blog-gracker-series.md"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewPropertyAnimator.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderEffect.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/transition/TransitionManager.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/drawable/AnimatedVectorDrawable.java @ android-17.0.0_r1"
  - type: official
    path: "developer.android.com/develop/ui/views/animations/prop-animation"
  - type: official
    path: "developer.android.com/develop/ui/views/animations/transitions"
  - type: source
    path: "github.com/airbnb/lottie-android/LottieAnimationView.java"
  - type: official
    path: "androidx.constraintlayout:constraintlayout:2.2.2"
tags: [animation, property-animation, lottie, render-effect, transition, motionlayout]
related_chapters: ["22.4", "7.1", "2.5", "2.7"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
  - "src/part5-app/ch22-rendering-practice/11-animated-vector-drawable-performance.md"
---

# 动画性能优化

动画掉帧可能出现在 UI 线程推进属性值时，也可能出现在 RenderThread 绘制、窗口缓冲区排队、SurfaceFlinger 合成或显示提交阶段。只观察 Animator 回调时长，会漏掉后半段问题。

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，Linux 内核观察基线固定为 `android17-6.18-2026-06_r6`。普通 View 动画走应用窗口的标准 HWUI（Android 硬件加速 UI 渲染系统）路径：

`vsync-app → Choreographer#doFrame → input / animation / insets animation / traversal / commit → HardwareRenderer.syncAndDrawFrame() → RenderThread → BLAST → SurfaceFlinger → HWC → present`

这条路径中的 input、animation、insets animation、traversal 与 commit，分别对应输入、动画、窗口边衬区变化动画（如系统栏或输入法区域变化）、View 树遍历和提交回调。RenderThread 是专用渲染线程，BLAST 负责在应用窗口与 SurfaceFlinger 之间交接缓冲区，SurfaceFlinger 是系统合成服务，HWC 是硬件合成器，present 表示显示系统确认的上屏时刻。

动画 API 的状态推进主要位于 Android 框架和应用进程。内核基线用于解释线程调度、GPU 驱动、fence（跨 CPU、GPU、显示设备传递完成状态的同步对象）与显示侧现象，不能拿内核标签推导 Animator 的 Java 语义。完整显示路径可结合 [Android View 标准渲染路径](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md) 阅读。

## 属性动画与帧动画：先看每帧改变什么

选择动画方案时，应把“每帧输入”“是否触发布局”“绘制输入规模”分开评估。

| 模型 | Android 17 中的每帧工作 | 合适场景 | 主要风险 |
| --- | --- | --- | --- |
| `ViewPropertyAnimator` | UI 线程上的一个 `ValueAnimator` 推进一组 View 属性，并合并相应重绘请求 | `alpha`、`translation`、`scale`、`rotation` 等 View 属性组合 | 更新回调做业务计算；目标内容频繁失效；把视觉变换当成布局语义变化 |
| `ObjectAnimator` | `PropertyValuesHolder` 计算值，再经 `Property`、优化调用路径或已解析的 setter（属性写入方法）写入目标 | View 之外的对象属性、自定义属性 | setter 内分配对象、执行 I/O、调用 `requestLayout()` 或触发大范围重绘 |
| 逐帧 Drawable | 到时切换子 Drawable，随后进入绘制 | 小面积、较短、逐帧美术效果 | 解码后像素内存、纹理上传、包体和资源切换 |
| 自绘动画 | 更新进度并使 View 失效，UI 线程按需重录 DisplayList（显示列表） | 图表、波形、进度和业务图形 | 每帧重建几何、分配对象或提交过多绘制命令 |
| Lottie | 推进 composition（解析后的动画模型）中各节点的进度，并绘制矢量、图片、mask（同层路径遮罩）与 matte（由另一图层决定可见区域） | 设计工具导出的矢量动效 | 节点遍历、路径计算、mask / matte、图片和渲染模式 |

Android 17 的 `ViewPropertyAnimator.startAnimation()` 创建一个 `ValueAnimator`。它在 UI 线程的更新回调中计算各属性值，直接更新 View 对应状态，再合并发出一次失效请求（invalidation）。它没有把动画回调自动迁移到 RenderThread；RenderThread 消费更新后的 RenderNode（渲染节点）与 DisplayList 状态。`ViewPropertyAnimator` 的优势是专用 View 属性接口、组合写法和失效请求合并。

`ObjectAnimator` 也不能统一描述为“每帧都用反射”。传入 `Property<T, V>` 时可以直接调用 `Property.set()`；传入属性名时，`PropertyValuesHolder` 会解析并缓存 getter（属性读取方法）与 setter，随后经反射或针对部分数值属性的优化路径写值。性能判断仍要回到目标 setter 的副作用。

### 变换属性不会修改布局语义

下面的反例在每个动画 tick（进度更新回调）中修改宽度，因此会持续发起布局请求。

```kotlin
ValueAnimator.ofInt(startWidth, targetWidth).apply {
    addUpdateListener { animator ->
        view.updateLayoutParams {
            width = animator.animatedValue as Int
        }
    }
}.start()
```

`updateLayoutParams` 会把新参数重新设置给 View，并触发 `requestLayout()`。受影响范围取决于父容器、约束与测量缓存；不能把它简化成“只改当前 View 的宽度”。

只需要视觉展开、且布局占位与触摸区域可以保持目标尺寸时，可以用变换属性表达同一段视觉过程。

```kotlin
view.pivotX = 0f
view.scaleX = 0f
view.animate()
    .scaleX(1f)
    .start()
```

`scaleX` 改变绘制变换，不会缩小 measured width（测量宽度）、layout bounds（摆放边界）、触摸命中区域或无障碍节点边界。产品要求周围内容随宽度移动、收起后不可点击或无障碍边界同步变化时，应更新布局和交互状态，并通过性能 trace（时间轴）确认参与重排的子树及其耗时；不能用 `scaleX` 冒充几何变化。

### `withLayer()` 只用于内容稳定的短时合成

`withLayer()` 会在下一次动画开始前设置 `LAYER_TYPE_HARDWARE`，结束时恢复调用前的图层类型。它适合内容复杂、动画期间内容保持不变、外层只做 `alpha` 或 transform（几何变换）的 View。View 内容每帧失效时，硬件图层仍需更新；大面积图层还会增加 GPU 内存，以及把内容先画到中间缓冲区的离屏渲染成本。默认 View 已有 RenderNode / DisplayList 复用能力，静态内容不需要长期强制硬件图层。

### 逐帧图片按解码后像素估算

假设 30 张互不复用的 1920 × 1080 图片都以 RGBA_8888 常驻，仅像素数据就需要：

`1920 × 1080 × 4 × 30 = 248,832,000 bytes ≈ 237.3 MiB`

这个数字只包含未经额外填充的像素数据，不能直接当成 `AnimationDrawable` 的固定内存占用。资源 density（密度）缩放、采样、Bitmap 复用、硬件位图、Drawable 类型和缓存生命周期都会改变驻留位置与数量；GPU 纹理也可能按绘制时机上传。评审时要用目标资源的解码尺寸、内存记录和 GPU 轨迹验证。大尺寸长动画通常更适合视频、受控的矢量动画或按需自绘，选型还要比较视觉保真、功耗和启动成本。

## Lottie：以当前稳定版 6.7.1 解释渲染模式

截至 2026-08-14，Maven Central 与上游 GitHub 的 Lottie Android 稳定版都是 `6.7.1`。库版本独立于 Android API 级别；项目升级 Lottie 后，要重新核对 `RenderMode`、缓存和异步更新行为。

`RenderMode.AUTOMATIC` 在 Lottie 6.7.1 中按这些条件选择软件绘制：

- 含 dash pattern（虚线图案）且系统低于 Android 9；
- mask 与 matte 总数超过 4；
- 系统不高于 Android 7.1。

在 Android 10—17 上，第一个和第三个兼容分支不会命中，主要自动切换条件是 mask / matte 总数超过 4。源码注释说明这个阈值只试过少量动画，要求开发者手动比较两种模式。它不能证明第 5 个 mask 一定更慢，也不能替代目标设备测量。软件模式会把内容绘制到 Lottie 管理的 Bitmap，复杂动画仍可能产生较高的 CPU 与内存成本。

`LottieAnimationView` 的 `cacheComposition` 默认开启。常规 assets 目录资源、raw 资源和 URL 加载通过 `LottieCompositionFactory` 返回异步任务，编辑器预览分支仍有同步解析。异步加载只把动画模型的解析与构建移出当前调用，播放期间的进度传播、动态属性回调和 Canvas 绘制仍要计入帧成本。

Lottie 6.7.1 还提供 `setPerformanceTrackingEnabled()` 与 `getPerformanceTracker()`，用于观察各图层的渲染时间。`AsyncUpdates` 在该版本被标为实验 API，`AUTOMATIC` 的注释写明当前按禁用处理；项目没有显式启用并验证时，不能认为节点更新已经离开 UI 线程。

评审一份 Lottie 资源时，可以按四组输入记录结果：

| 输入 | 要核对的内容 | 验证方法 |
| --- | --- | --- |
| 动画模型（composition） | 图层、路径点、trim path（路径裁切）、表达式或动态回调 | PerformanceTracker、CPU trace、设计稿简化前后对比 |
| 合成效果 | mask、matte、透明叠加和大面积裁剪 | 检查导出 JSON，并比较 `AUTOMATIC`、`HARDWARE`、`SOFTWARE` |
| 图片资源 | 解码尺寸、复用、色彩格式和首次上传 | 内存记录、RenderThread/GPU 轨迹、冷启动与热启动对比 |
| 播放策略 | 同屏数量、循环、可见性和生命周期 | RecyclerView 滚动、页面切后台与长时间功耗测试 |

这四组输入必须随同一份动画资源一起记录。只写 `RenderMode` 或平均帧率，无法解释一次资源简化、缓存命中或同屏数量变化带来的差异。

RecyclerView 中的动画应绑定列表项可见性和业务焦点。离屏列表项停止播放，回收时移除动态回调或引用；同屏数量多时，可以给非焦点列表项使用静态帧。首屏动画模型的预加载和缓存要与内存预算一起评估，避免每次绑定数据时重复发起加载。

## RenderEffect：控制输入面积、效果状态与降级

`RenderEffect` 从 API 31 公开。Android 17 的 `View.setRenderEffect()` 把效果设置到 View 背后的 RenderNode；RenderNode 状态变化后，View 会触发属性失效，让渲染系统同步新状态。blur（模糊）、shader（着色器）或多个效果组成的链可能需要中间渲染目标，成本随输入区域、采样范围、像素格式、效果组合和更新频率变化。

评审 RenderEffect 时，要记录这一帧处理了多少像素、处理几次，以及输入是否改变。全屏模糊、滚动容器上的模糊、半径持续变化，以及效果与复杂透明叠加同时出现，都需要单独测量。低性能设备档位、省电模式和降级路径可以关闭效果、缩小作用 View，或改用经过设计确认的静态背景与半透明色块。

视觉只需要几个固定状态时，可以复用已经创建的 RenderEffect。下面的控制器由调用方长期持有，半径来自设计资源或设备分档测试，没有写入通用阈值。

```kotlin
@RequiresApi(Build.VERSION_CODES.S)
class BlurController(
    compactRadiusPx: Float,
    expandedRadiusPx: Float,
) {
    enum class State { OFF, COMPACT, EXPANDED }

    private val compact = RenderEffect.createBlurEffect(
        compactRadiusPx,
        compactRadiusPx,
        Shader.TileMode.CLAMP,
    )
    private val expanded = RenderEffect.createBlurEffect(
        expandedRadiusPx,
        expandedRadiusPx,
        Shader.TileMode.CLAMP,
    )

    fun apply(view: View, state: State) {
        view.setRenderEffect(
            when (state) {
                State.OFF -> null
                State.COMPACT -> compact
                State.EXPANDED -> expanded
            },
        )
    }
}
```

这个示例避免在每帧重复创建相同效果，并保留 `null` 清理路径。半径由视觉目标与实机数据决定，关闭状态直接传 `null`。动画必须连续改变半径时，缓存固定状态无法消除每帧输入变化，应缩小 View 的输入边界，并比较关闭效果前后的 FrameTimeline（关联应用、系统合成与显示阶段的帧时间线）、RenderThread、GPU 和功耗差值。

`RenderThread DrawFrame` 变长也不能直接写成“GPU 慢”。这段时间可能包含 RenderThread 的 CPU 工作、runnable（线程已就绪但仍在等 CPU）时间、`dequeueBuffer` 等待、驱动调用或 GPU 同步。还要检查线程状态、调度延迟、`dequeueBuffer` / `queueBuffer` 耗时、GPU slice（时间轴上的工作区间）和 fence。UI 与 RenderThread 都按时而 present 偏晚时，应继续检查 BLAST 的缓冲区积压、SurfaceFlinger 的 latch（接收本帧缓冲区）与合成、HWC 和显示反馈。

## 动画与 UI 线程：按显示阶段归因

`Choreographer` 在 Android 17 中依次执行 input、animation、insets animation、traversal 和 commit 回调。`ValueAnimator`、`ViewPropertyAnimator` 的进度推进以及应用注册的更新回调通常运行在创建它们的 Looper 线程；Looper 是按队列处理消息和回调的线程循环。View 动画应在 UI 线程创建和操作。属性最终写入 RenderNode，也不会省掉 UI 线程上的插值、回调和状态更新。

一帧动画应沿以下观察点逐段检查：

| 阶段 | Perfetto 观察点 | 可以支持的结论 | 还不能推出的结论 |
| --- | --- | --- | --- |
| UI 线程 | `Choreographer#doFrame`、animation 回调、`performTraversals`、自定义 trace | 回调计算、布局或 DisplayList 重录是否超预算 | GPU 是否已经完成 |
| RenderThread | `syncFrameState`、`DrawFrame`、线程状态、dequeue / queue 耗时 | RenderNode 同步、绘制准备或缓冲区等待位于何处 | 整段 `DrawFrame` 都是 GPU 执行 |
| GPU / 图像生产者 | `GPU slices`（GPU 工作区间）、提交与完成栅栏 | GPU 工作是否跨过应用帧 deadline（截止时间） | 缓冲区是否已经上屏 |
| BLAST / SurfaceFlinger | `BufferTX - <layerName>`、latch（接收缓冲区）、composition（合成）、FrameTimeline | 缓冲区到达、合成和 display frame（显示帧）是否按期 | 屏幕面板的像素响应已经完成 |
| HWC / 显示设备 | composition type（合成类型）、present feedback（上屏反馈）、相关 fence | Android 显示栈观察到的 present 时刻 | 用户已经感知到像素变化 |

这张表的边界是“某一阶段按时”只能排除该阶段已经观察到的延迟。判断动画是否按期可见，仍要把同一帧从应用回调关联到最终 present。

### 把不变计算移出更新回调

下面的反例会在每个 tick 遍历数据并重建 Path。

```kotlin
ValueAnimator.ofFloat(0f, 1f).apply {
    addUpdateListener { animator ->
        chartPath.reset()
        rebuildPath(chartPath, data, animator.animatedFraction)
        chartView.invalidate()
    }
}.start()
```

即使这段代码没有产生 Java 对象，路径计算、DisplayList 记录和几何处理仍可能超过帧预算。

输入数据不变时，应先构建稳定采样结果，并只在每帧更新进度。

```kotlin
val samples = buildPathSamples(data)
chartView.setSamples(samples)

ValueAnimator.ofFloat(0f, 1f).apply {
    addUpdateListener { animator ->
        chartView.setProgress(animator.animatedFraction)
    }
}.start()
```

`setSamples()` 只在动画开始前复制数据并建立几何缓存；`setProgress()` 只更新可见区间并调用 `invalidate()`。API 21 起，应用传给 `invalidate(Rect)` 的 dirty rectangle（局部脏区域）会被忽略，因此不能依赖它缩小 View 的重录范围。需要隔离更新时，应把内容分到不同的 View 或 RenderNode。`onDraw()` 的对象复用、刷新和 RenderNode 边界详见 [22.4 自定义 View 性能优化](04-custom-view-optimization.md)。

### 动画要随可见性停止

页面 `onStop()`、View 从窗口分离或 RecyclerView 列表项回收后，Animator、Lottie、粒子系统和 `postOnAnimation()` 循环都应停止或暂停。恢复时要从业务状态计算进度，避免重复注册回调。生命周期处理既影响帧性能，也影响后台功耗和对象引用。

### Android 17 的缓冲区积压恢复

Android 17 源码包含 buffer stuffing recovery（缓冲区积压恢复）。窗口生产者等待空闲缓冲区超过半个帧周期时，`Choreographer.onWaitForBufferRelease()` 会把当前状态标为 stuffed（已积压）；等待时长来自 `BBQBufferQueueProducer::waitForBufferRelease()`，经渲染器回调与 `ViewRootImpl` 连接到 `Choreographer`。恢复逻辑可以主动延迟一帧，再用 `Negative offset` 调整后续动画的 frame time（动画时间基准），让缓冲区积压有时间下降。

Perfetto 中遇到动画帧间隔异常时，可搜索 `Buffer stuffing recovery`、`buffer stuffed` 和 `Negative offset`，再检查 `dequeueBuffer` 等待、FrameTimeline 的 `Buffer Stuffing`、目标图层的 `BufferTX` 与后续缓冲区积压。出现主动延迟时，该帧不能直接归因为 Animator 计算或 CPU 算力不足。`bufferStuffingMultiRecovery`、`bufferStuffingRecoveryThreshold` 等 aconfig（Android 平台功能开关机制）配置会改变恢复细节，设备行为要以当前构建配置和 trace 为准。

## AnimatedVectorDrawable：先确认运行线程再优化

Android 17 的 `AnimatedVectorDrawable`（AVD）默认使用 `VectorDrawableAnimatorRT`，API 25 起可以在 RenderThread 推进动画。动画尚未启动、却先绘制到软件 Canvas 时，源码会调用 `fallbackOntoUI()` 切到 UI 线程实现；平台内部也保留强制 UI 动画的入口。

`Animatable2.AnimationCallback` 不会让动画退回 UI 线程。RenderThread 动画完成后，结束回调经 Handler 返回 UI 侧，而且可能比 RenderThread 完成晚一帧。排查时应在 Perfetto 中分别查看主线程、RenderThread 和 GPU；主线程没有逐帧更新，也不能证明动画已经按期 present。

AVD 适合路径、颜色和 transform 数量有限的图标动画。路径节点、关键帧和同时播放实例越多，属性插值、矢量绘制与 GPU 覆盖成本越高；退回 UI 线程时还要承担主线程更新与绘制记录。可以从 `Drawable.ConstantState` 创建实例以复用不可变配置，但每个可见控件仍需独立的可变动画状态。列表复用时必须在从窗口分离或回收时停止动画并重置进度，避免不可见 ViewHolder 继续占用帧时钟。

出现版本或设备差异时，建立三组对照：原 AVD、等价静态矢量图、简化路径或关键帧的 AVD。若静态组仍慢，问题不在动画插值；若主线程组明显改善但 GPU 耗时不变，说明只是移动了 CPU 工作。软件 Canvas、截图和离屏 Bitmap 路径也要单独验证，因为它们不能沿用硬件窗口的 RenderThread 结论。

## 转场动画：限制捕获范围和目标数量

`TransitionManager.beginDelayedTransition(sceneRoot, transition)` 会立即捕获 start values（变化前的属性），并安排在下一次 pre-draw（绘制前回调）捕获 end values（变化后的属性），然后为有差异的目标创建 Animator。`sceneRoot` 是转场捕获和动画的根容器；范围过大时，遍历、布局影响和候选目标都会增加。具体成本还取决于 Transition 类型，以及 target / exclude（纳入 / 排除目标）配置。

场景根节点应选能容纳目标变化的最小共同父容器，再显式限制 target。下面的例子让筛选面板和结果列表的外框参与转场，同时排除列表项。

```kotlin
val transition = AutoTransition().apply {
    addTarget(filterPanel)
    addTarget(resultList)
    excludeChildren(resultList, true)
}

TransitionManager.beginDelayedTransition(contentContainer, transition)
filterPanel.isVisible = showFilters
```

`resultList` 自身可以随筛选面板展开而移动，RecyclerView 的子 View 不会成为 transition target。`contentContainer` 必须同时包含两个目标；如果页面结构不满足这个前提，应调整 scene root 或改成局部动画。

常见转场问题可以按触发条件处理：

| 现象 | 检查内容 | 处理方向 |
| --- | --- | --- |
| start / end 捕获很长 | scene root 层级、target 数量、自定义 `capture*Values()` | 缩小根节点，使用 `addTarget()` / `excludeTarget()` |
| View 树遍历连续变长 | 边界、约束、文本和子 View 尺寸是否在变化 | 减少参与重排的子树，预先计算文本与几何 |
| RecyclerView 列表项被创建大量 Animator | 列表是否落在 scene root，子 View 是否被排除 | 排除子 View，或让列表避开该转场 |
| UI 线程按时但画面仍晚 | 大面积 `alpha`、阴影、RenderEffect、缓冲区积压和 SurfaceFlinger / 显示设备 | 沿 RenderThread、GPU、BLAST、SurfaceFlinger、HWC 继续定位 |

转场期间临时启用的图层、点击禁用状态和视觉属性，应在取消与正常结束两条路径都恢复。复杂转场还要验证系统动画缩放、页面快速退出、旋转和多次触发，防止监听器遗漏导致状态残留。

## 扩展：MotionLayout 性能实践

截至 2026-08-14，Google Maven 中 ConstraintLayout 的当前稳定版是 `2.2.2`，本文以该版本为库基线。MotionLayout 属于 AndroidX ConstraintLayout，其行为由依赖版本和 `MotionScene` 决定，Android 17 平台标签不能替代库版本记录。`progress` 是从 0 到 1 的转场进度；MotionLayout 适合用它同时驱动多个 View 的约束、位置、尺寸、透明度和关键帧。

接入时检查三类输入：

1. 只包含 `translation`、`scale`、`rotation` 或 `alpha` 的简单动效，可以先比较属性动画；MotionLayout 更适合需要约束关系和关键帧协同的场景。
2. 尺寸、约束、文本或 ConstraintHelper（如 Barrier、Group 等约束辅助控件）状态随 `progress` 变化时，观察 `performTraversals`、测量 / 摆放次数和每帧参与计算的 View 数量。
3. 复杂首屏或低性能设备要有简化 MotionScene、缩小参与范围或跳过动效的产品方案，并验证无障碍与“减少动态效果”设置。

判断 MotionLayout 性能时，应固定 ConstraintLayout 版本、设备刷新率、动画输入和页面数据。若 UI 线程的摆放时间随 `progress` 稳定升高，可以逐项移除尺寸或约束变化，确认哪一组目标造成成本；若 UI 线程按时，则继续检查 RenderThread 和显示后段。

## 上线前检查清单

- 记录 Android 平台、Lottie / ConstraintLayout 等库版本、设备固件、刷新率和测试输入。
- 区分绘制变换与布局几何；同时验证触摸区域、无障碍边界和同级 View 排布。
- 检查 Animator 更新回调、setter 和动态属性回调中是否存在重复计算、对象分配、I/O 或 `requestLayout()`。
- 逐帧图片按解码尺寸估算内存，并用运行时记录确认驻留与纹理上传。
- Lottie 对比目标资源的三种 RenderMode，记录 mask / matte、图片和同屏播放数量。
- RenderEffect 限制输入区域，复用固定状态，提供 `null` 清理和设备降级。
- 转场使用最小 scene root，并显式配置 target / exclude；验证取消、页面退出和重复触发。
- API 31—37 优先检查 FrameTimeline；API 29—30 结合 UI/RenderThread、BufferQueue、SurfaceFlinger 和显示时序。
- UI 与 RenderThread 按时仍不等于按期 present；继续检查 BLAST、SurfaceFlinger、HWC 和 fence。

## 参考资料

- [AOSP Android 17 `ViewPropertyAnimator.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewPropertyAnimator.java)
- [AOSP Android 17 `PropertyValuesHolder.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/animation/PropertyValuesHolder.java)
- [AOSP Android 17 `RenderEffect.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/RenderEffect.java)
- [AOSP Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)
- [AOSP Android 17 `TransitionManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/transition/TransitionManager.java)
- [AOSP Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [AOSP Android 17 `AnimatedVectorDrawable.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/drawable/AnimatedVectorDrawable.java)
- [AOSP Android 17 `ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)
- [AOSP Android 17 `CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)
- [AOSP Android 17 `BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [Lottie 6.7.1 `RenderMode.java`](https://github.com/airbnb/lottie-android/blob/v6.7.1/lottie/src/main/java/com/airbnb/lottie/RenderMode.java)
- [Lottie 6.7.1 `LottieAnimationView.java`](https://github.com/airbnb/lottie-android/blob/v6.7.1/lottie/src/main/java/com/airbnb/lottie/LottieAnimationView.java)
- [Lottie 6.7.1 `AsyncUpdates.java`](https://github.com/airbnb/lottie-android/blob/v6.7.1/lottie/src/main/java/com/airbnb/lottie/AsyncUpdates.java)
- [Lottie Android releases](https://github.com/airbnb/lottie-android/releases)
- [Android 属性动画文档](https://developer.android.com/develop/ui/views/animations/prop-animation)
- [Android Transition 文档](https://developer.android.com/develop/ui/views/animations/transitions)
- [Android MotionLayout 文档](https://developer.android.com/develop/ui/views/animations/motionlayout)
- [ConstraintLayout 2.2.2 POM](https://dl.google.com/dl/android/maven2/androidx/constraintlayout/constraintlayout/2.2.2/constraintlayout-2.2.2.pom)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 17 kernel common `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
