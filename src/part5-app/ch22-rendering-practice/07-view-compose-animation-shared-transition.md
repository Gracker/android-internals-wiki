---
title: View、Compose 动画与共享元素性能
chapter: '22.7'
section: '22.7'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1; Lottie 6.7.1; ConstraintLayout 2.2.2
confidence: high
sources:
- type: clippings
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings
  path: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md
- type: research
  path: Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-rendereffect-gpu-rendering-pipeline-analysis.md
- type: source
  path: intake/external-resources/blog-gracker-series.md
- type: aosp
  path: frameworks/base/core/java/android/view/ViewPropertyAnimator.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/RenderEffect.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/view/View.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/transition/TransitionManager.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/drawable/AnimatedVectorDrawable.java @ android-17.0.0_r1
- type: official
  path: developer.android.com/develop/ui/views/animations/prop-animation
- type: official
  path: developer.android.com/develop/ui/views/animations/transitions
- type: source
  path: github.com/airbnb/lottie-android/LottieAnimationView.java
- type: official
  path: androidx.constraintlayout:constraintlayout:2.2.2
- type: research
  path: DeepResearch/2026-06-01-android-compose-animation-performance-bottlenecks.md
- type: research
  path: DeepResearch/2026-06-02-android-compose-110-strong-skipping-mechanism.md
- type: research
  path: DeepResearch/2026-06-02-android-compose-derivedstate-sso-deep-source-analysis.md
- type: official
  path: https://developer.android.com/develop/ui/compose/animation/shared-elements
- type: official
  path: https://developer.android.com/develop/ui/compose/animation/shared-elements/customize
- type: official
  path: https://developer.android.com/develop/ui/compose/animation/shared-elements/navigation
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/compose-animation
- type: aosp
  path: android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedTransitionScope.kt
- type: aosp
  path: android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedContentNode.kt
- type: aosp
  path: android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedElementEntry.kt
- type: official
  path: https://developer.android.com/develop/ui/compose/system/predictive-back
- type: official
  path: https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-16
- type: official
  path: https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/maven-metadata.xml
- type: aosp
  path: android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java
- type: aosp
  path: android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java
tags:
- animation
- property-animation
- lottie
- render-effect
- transition
- motionlayout
- compose
- animated-visibility
- animatable
- strong-skipping
- performance
- Compose
- SharedTransition
- Animation
- Performance
- Rendering
related_chapters:
- '22.1'
- '7.1'
- '2.4'
- '22.3'
- '13.8'
- '2.1'
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
- src/part5-app/ch22-rendering-practice/11-animated-vector-drawable-performance.md
- src/part5-app/ch22-rendering-practice/32-compose-infinite-animation-vector-converter-performance.md
- src/part5-app/ch22-rendering-practice/44-compose-pager-advanced-animations.md
- src/part5-app/ch22-rendering-practice/05-animation-performance.md
- src/part5-app/ch22-rendering-practice/15-compose-animation-performance.md
- src/part5-app/ch22-rendering-practice/27-compose-shared-transition.md
last_consolidated_at: '2026-08-24'
---

# View、Compose 动画与共享元素性能

动画掉帧可能出现在 UI 线程推进属性值时，也可能出现在 RenderThread 绘制、窗口缓冲区排队、SurfaceFlinger 合成或显示提交阶段。只观察 Animator 回调时长，会漏掉后半段问题。

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，Linux 内核观察基线固定为 `android17-6.18-2026-06_r6`。普通 View 动画走应用窗口的标准 HWUI（Android 硬件加速 UI 渲染系统）路径：

`vsync-app → Choreographer#doFrame → input / animation / insets animation / traversal / commit → HardwareRenderer.syncAndDrawFrame() → RenderThread → BLAST → SurfaceFlinger → HWC → present`

这条路径中的 input、animation、insets animation、traversal 与 commit，分别对应输入、动画、窗口边衬区变化动画（如系统栏或输入法区域变化）、View 树遍历和提交回调。RenderThread 是专用渲染线程，BLAST 负责在应用窗口与 SurfaceFlinger 之间交接缓冲区，SurfaceFlinger 是系统合成服务，HWC 是硬件合成器，present 表示显示系统确认的上屏时刻。

动画 API 的状态推进主要位于 Android 框架和应用进程。内核基线用于解释线程调度、GPU 驱动、fence（跨 CPU、GPU、显示设备传递完成状态的同步对象）与显示侧现象，不能拿内核标签推导 Animator 的 Java 语义。完整显示路径可结合 [Android View 标准渲染路径](../../part2-performance/ch13-rendering-pipelines/01-android-view-pipeline-analysis.md) 阅读。

动画性能取决于每帧更新发生在哪个线程、是否触发布局以及中间图层如何合成。Compose 动画延续相同原则，SharedTransition 还要在两个内容状态之间匹配元素和同步边界。

## 属性更新、布局触发与 RenderThread

### 属性动画与帧动画：先看每帧改变什么

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

#### 变换属性不会修改布局语义

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

#### `withLayer()` 只用于内容稳定的短时合成

`withLayer()` 会在下一次动画开始前设置 `LAYER_TYPE_HARDWARE`，结束时恢复调用前的图层类型。它适合内容复杂、动画期间内容保持不变、外层只做 `alpha` 或 transform（几何变换）的 View。View 内容每帧失效时，硬件图层仍需更新；大面积图层还会增加 GPU 内存，以及把内容先画到中间缓冲区的离屏渲染成本。默认 View 已有 RenderNode / DisplayList 复用能力，静态内容不需要长期强制硬件图层。

#### 逐帧图片按解码后像素估算

假设 30 张互不复用的 1920 × 1080 图片都以 RGBA_8888 常驻，仅像素数据就需要：

`1920 × 1080 × 4 × 30 = 248,832,000 bytes ≈ 237.3 MiB`

这个数字只包含未经额外填充的像素数据，不能直接当成 `AnimationDrawable` 的固定内存占用。资源 density（密度）缩放、采样、Bitmap 复用、硬件位图、Drawable 类型和缓存生命周期都会改变驻留位置与数量；GPU 纹理也可能按绘制时机上传。评审时要用目标资源的解码尺寸、内存记录和 GPU 轨迹验证。大尺寸长动画通常更适合视频、受控的矢量动画或按需自绘，选型还要比较视觉保真、功耗和启动成本。

### Lottie：以当前稳定版 6.7.1 解释渲染模式

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

### RenderEffect：控制输入面积、效果状态与降级

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

### 动画与 UI 线程：按显示阶段归因

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

#### 把不变计算移出更新回调

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

`setSamples()` 只在动画开始前复制数据并建立几何缓存；`setProgress()` 只更新可见区间并调用 `invalidate()`。API 21 起，应用传给 `invalidate(Rect)` 的 dirty rectangle（局部脏区域）会被忽略，因此不能依赖它缩小 View 的重录范围。需要隔离更新时，应把内容分到不同的 View 或 RenderNode。`onDraw()` 的对象复用、刷新和 RenderNode 边界详见 [22.1 自定义 View 性能优化](01-view-layout-custom-drawing.md)。

#### 动画要随可见性停止

页面 `onStop()`、View 从窗口分离或 RecyclerView 列表项回收后，Animator、Lottie、粒子系统和 `postOnAnimation()` 循环都应停止或暂停。恢复时要从业务状态计算进度，避免重复注册回调。生命周期处理既影响帧性能，也影响后台功耗和对象引用。

#### Android 17 的缓冲区积压恢复

Android 17 源码包含 buffer stuffing recovery（缓冲区积压恢复）。窗口生产者等待空闲缓冲区超过半个帧周期时，`Choreographer.onWaitForBufferRelease()` 会把当前状态标为 stuffed（已积压）；等待时长来自 `BBQBufferQueueProducer::waitForBufferRelease()`，经渲染器回调与 `ViewRootImpl` 连接到 `Choreographer`。恢复逻辑可以主动延迟一帧，再用 `Negative offset` 调整后续动画的 frame time（动画时间基准），让缓冲区积压有时间下降。

Perfetto 中遇到动画帧间隔异常时，可搜索 `Buffer stuffing recovery`、`buffer stuffed` 和 `Negative offset`，再检查 `dequeueBuffer` 等待、FrameTimeline 的 `Buffer Stuffing`、目标图层的 `BufferTX` 与后续缓冲区积压。出现主动延迟时，该帧不能直接归因为 Animator 计算或 CPU 算力不足。`bufferStuffingMultiRecovery`、`bufferStuffingRecoveryThreshold` 等 aconfig（Android 平台功能开关机制）配置会改变恢复细节，设备行为要以当前构建配置和 trace 为准。

### AnimatedVectorDrawable：先确认运行线程再优化

Android 17 的 `AnimatedVectorDrawable`（AVD）默认使用 `VectorDrawableAnimatorRT`，API 25 起可以在 RenderThread 推进动画。动画尚未启动、却先绘制到软件 Canvas 时，源码会调用 `fallbackOntoUI()` 切到 UI 线程实现；平台内部也保留强制 UI 动画的入口。

`Animatable2.AnimationCallback` 不会让动画退回 UI 线程。RenderThread 动画完成后，结束回调经 Handler 返回 UI 侧，而且可能比 RenderThread 完成晚一帧。排查时应在 Perfetto 中分别查看主线程、RenderThread 和 GPU；主线程没有逐帧更新，也不能证明动画已经按期 present。

AVD 适合路径、颜色和 transform 数量有限的图标动画。路径节点、关键帧和同时播放实例越多，属性插值、矢量绘制与 GPU 覆盖成本越高；退回 UI 线程时还要承担主线程更新与绘制记录。可以从 `Drawable.ConstantState` 创建实例以复用不可变配置，但每个可见控件仍需独立的可变动画状态。列表复用时必须在从窗口分离或回收时停止动画并重置进度，避免不可见 ViewHolder 继续占用帧时钟。

出现版本或设备差异时，建立三组对照：原 AVD、等价静态矢量图、简化路径或关键帧的 AVD。若静态组仍慢，问题不在动画插值；若主线程组明显改善但 GPU 耗时不变，说明只是移动了 CPU 工作。软件 Canvas、截图和离屏 Bitmap 路径也要单独验证，因为它们不能沿用硬件窗口的 RenderThread 结论。

### 转场动画：限制捕获范围和目标数量

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

### 扩展：MotionLayout 性能实践

截至 2026-08-14，Google Maven 中 ConstraintLayout 的当前稳定版是 `2.2.2`，本文以该版本为库基线。MotionLayout 属于 AndroidX ConstraintLayout，其行为由依赖版本和 `MotionScene` 决定，Android 17 平台标签不能替代库版本记录。`progress` 是从 0 到 1 的转场进度；MotionLayout 适合用它同时驱动多个 View 的约束、位置、尺寸、透明度和关键帧。

接入时检查三类输入：

1. 只包含 `translation`、`scale`、`rotation` 或 `alpha` 的简单动效，可以先比较属性动画；MotionLayout 更适合需要约束关系和关键帧协同的场景。
2. 尺寸、约束、文本或 ConstraintHelper（如 Barrier、Group 等约束辅助控件）状态随 `progress` 变化时，观察 `performTraversals`、测量 / 摆放次数和每帧参与计算的 View 数量。
3. 复杂首屏或低性能设备要有简化 MotionScene、缩小参与范围或跳过动效的产品方案，并验证无障碍与“减少动态效果”设置。

判断 MotionLayout 性能时，应固定 ConstraintLayout 版本、设备刷新率、动画输入和页面数据。若 UI 线程的摆放时间随 `progress` 稳定升高，可以逐项移除尺寸或约束变化，确认哪一组目标造成成本；若 UI 线程按时，则继续检查 RenderThread 和显示后段。

### 上线前检查清单

- 记录 Android 平台、Lottie / ConstraintLayout 等库版本、设备固件、刷新率和测试输入。
- 区分绘制变换与布局几何；同时验证触摸区域、无障碍边界和同级 View 排布。
- 检查 Animator 更新回调、setter 和动态属性回调中是否存在重复计算、对象分配、I/O 或 `requestLayout()`。
- 逐帧图片按解码尺寸估算内存，并用运行时记录确认驻留与纹理上传。
- Lottie 对比目标资源的三种 RenderMode，记录 mask / matte、图片和同屏播放数量。
- RenderEffect 限制输入区域，复用固定状态，提供 `null` 清理和设备降级。
- 转场使用最小 scene root，并显式配置 target / exclude；验证取消、页面退出和重复触发。
- API 31—37 优先检查 FrameTimeline；API 29—30 结合 UI/RenderThread、BufferQueue、SurfaceFlinger 和显示时序。
- UI 与 RenderThread 按时仍不等于按期 present；继续检查 BLAST、SurfaceFlinger、HWC 和 fence。

## Compose 状态驱动动画与重组范围

View 动画按属性和线程判断成本，Compose 动画还要检查状态读取是否扩大重组和测量范围。

Compose 动画每帧会做多少工作，取决于动画值在哪个阶段读取、哪些阶段因此失效、过渡期间保留多少界面内容，以及应用提交帧后的显示过程。本文以 Compose BOM 2026.08.00 对应的 Compose 1.12.0 为库版本基线，以 Android 17、API 37 的 `android-17.0.0_r1` 为平台基线。Compose 独立于 Android 平台发布，不能用 API 37 推导 Compose 行为。

普通 Compose 页面仍由宿主应用窗口的硬件加速界面渲染系统（HWUI）生成画面。状态计算，以及部分组合（Composition）、布局（Layout）和绘制（Draw）工作发生在主线程；`RenderThread` 整理硬件绘制命令，GPU 执行命令，BLAST 负责传递图形缓冲区，`SurfaceFlinger` 与硬件合成器（Hardware Composer，HWC）完成系统合成和送显。完整边界见 [13.8 Jetpack Compose 渲染管线：Composition、Layout 与 RenderNode](../../part2-performance/ch13-rendering-pipelines/08-compose-rendering-pipeline.md)。本文只讨论动画额外增加的工作。

### 1. 用状态读取阶段判断动画成本

`Animatable.value`、`Transition.animate*` 和 `animate*AsState` 返回的动画值都受 Compose 快照（Snapshot）系统观察。API 名称不会预先决定失效阶段；在哪个阶段读取动画值，值变化时就会请求哪个阶段再次执行。一个值若在多个阶段读取，也会建立多处观察关系。

| 动画值的读取位置 | 值变化后的主要工作 | 常见写法 | 判断要点 |
| --- | --- | --- | --- |
| 可组合函数体 | 组合；后续是否进入布局、绘制取决于输出变化 | `Box(Modifier.alpha(alpha))` 中先在函数体读取 `alpha` | 高频值容易让当前重组作用域逐帧执行 |
| 测量或放置回调（lambda） | 布局的相应子阶段，随后绘制 | `Modifier.offset { IntOffset(x, 0) }` | 可跳过组合，但位置或尺寸变化仍有布局成本 |
| 绘制回调 | 绘制 | `drawBehind { drawRect(color) }` | 适合颜色、路径参数和 `Canvas` 内容 |
| `graphicsLayer {}` 回调 | 图层属性更新与绘制提交 | `graphicsLayer { translationX = x }` | 不重组、不重新测量；仍会产生 `RenderThread`/GPU 工作 |

`drawWithCache` 也会观察缓存构建代码中读取的 `State`，依赖变化时会重建缓存。绘制阶段并没有统一关闭 Snapshot 读取观察。把高频值延后到绘制回调或图层回调中读取，组合阶段才无需处理这次更新。

下面的示例用于把透明度动画值延后到图层属性更新。

```kotlin
@Composable
fun FadingPanel(
    visible: Boolean,
    content: @Composable () -> Unit,
) {
    val alpha = remember { Animatable(if (visible) 1f else 0f) }

    LaunchedEffect(visible) {
        alpha.animateTo(if (visible) 1f else 0f)
    }

    Box(
        Modifier.graphicsLayer {
            this.alpha = alpha.value
        }
    ) {
        content()
    }
}
```

这里的 `alpha.value` 只在 `graphicsLayer` 回调中读取，所以透明度变化不会要求 `FadingPanel` 逐帧重组或重新布局。透明度低于 1 时，图层可能需要中间合成；减少主线程工作不表示 GPU 无需工作。应在目标设备上同时观察界面线程、`RenderThread` 和帧时间线（`FrameTimeline`）。

### 2. 动画时钟与 Android 17 帧时间

Compose 1.12.0 的 `AndroidUiFrameClock.withFrameNanos()` 会注册 `Choreographer.FrameCallback`。`Transition` 和 `Animatable` 的逐帧循环都通过 `withFrameNanos` 一类接口等待下一帧。Android 上没有一套脱离 `Choreographer`、按固定间隔自行计时的 Compose 界面时钟。

主线程及时收到回调时，动画按本次帧时间计算已经播放的时长。主线程被阻塞后，回调会延迟；下一次执行看到更大的时间差，动画值会向前跳。Compose 不会补画所有错过的中间帧，用户通常会看到画面停顿后直接跳到较后的状态。

Android 17 的 `Choreographer.FrameData` 同时携带候选帧时间线、首选帧时间线、截止时间和预计呈现时间。性能判断应使用当前帧的截止时间，或 `FrameTimeline` 中的预期/实际结果，不能把 16.6 ms、11.1 ms、8.3 ms 固化成设备常量。可变刷新率、帧率请求和调度选择都会改变某一帧可用的时间。

Perfetto 中的 `Choreographer#doFrame` 区间事件（slice）覆盖应用主线程回调，不包含应用 GPU 完成、图形缓冲区入队后的 SurfaceFlinger 合成和送显。它变长只能证明主线程帧回调变长，不能单独代表端到端帧耗时。

### 3. Animatable：互斥动画与手势跟随

`Animatable<T, V>` 内部持有 `AnimationState`，其 `value` 由 `mutableStateOf` 保存。它提供数值连续性、边界约束、速度信息和互斥控制；读取位置仍会决定失效阶段，不能假定它只触发绘制。

同一个 `Animatable` 启动新的 `animateTo`、`animateDecay`、`snapTo` 或 `stop` 时，`MutatorMutex` 会取消正在运行的变更。新的 `animateTo` 从当前值继续；弹簧动画（spring）还会延续当前速度。取消会以 `CancellationException` 沿协程父子关系传播，需要释放的资源应在 `finally` 中清理。

手指位置直接跟随适合在拖动期间使用 `snapTo`，松手后再用 `animateDecay` 或 `animateTo` 收尾。每个触摸采样点都调用 `animateTo`，会连续取消前一个动画，产生与输入延迟、动画参数和采样频率有关的追赶效果。若产品需要这种柔性跟随，可以保留，但它仍有逐帧更新和协程取消的成本。

API 选择可以按控制语义划分：

- 单个或少量数值、协程中顺序控制、手势打断：`Animatable`。
- 一个离散状态协调多项属性：`Transition`。
- 单值随目标自动过渡，且无需等待完成或主动取消：`animate*AsState`。
- 内容进入、退出或替换：`AnimatedVisibility`、`AnimatedContent`。

无关组件各自维护状态迁移，更容易限定生命周期。跨组件共享一个 `Transition` 虽然能减少对象数，却会把状态、取消和完成条件耦合在一起，不能作为通用优化。

### 4. Transition 会参与组合

`updateTransition(targetState)` 是可组合函数。Compose 1.12.0 会在当前位置通过 `remember` 保存一个 `Transition`，随后调用 `animateTo(targetState)`，并用 `DisposableEffect` 处理离开组合时的清理。参数或被观察的 `State` 变化仍可能让相关可组合函数重新执行，`Transition` 并不提供“组合永不重启”的语义。

`Transition` 让多个子动画共享状态迁移和帧进度，也支持运行中改变目标。目标变化时，它会更新由起点和终点组成的迁移段（segment）及目标；不同动画参数对中断连续性的处理不同，不能一概描述成“每次切换都从头重启”。

是否对快速点击做防抖（debounce）属于交互约束：

- 若每次输入都有效，允许动画重新定向，并检查中断后的连续性。
- 若后端操作或导航只允许一次，按业务状态屏蔽重复输入。
- 若需要观察进入、退出是否结束，使用 `MutableTransitionState.isIdle` 与 `currentState`。

Compose 1.12.0 已弃用接收 `MutableTransitionState` 的 `updateTransition` 重载，应改用 `rememberTransition(transitionState)`；接收普通目标值的 `updateTransition(targetState)` 仍可使用。`MutableTransitionState` 提供可观察的状态迁移入口，本身不会减少每帧工作。1.12.0 的 `DeferredTransitionState` 与 `mutableTransform` 面向预测性返回等“先手动改变属性、再启动自动过渡”的场景，也不是通用性能开关。

### 5. AnimatedVisibility：尺寸变化和退出内容保留

`AnimatedVisibility` 使用自定义 `Layout` 承载界面内容。普通 `AnimatedVisibility(visible=...)` 的测量策略会测量子项，以最大宽高作为容器尺寸，并把子项放在坐标 `(0, 0)`；Row/Column 作用域重载有各自适配的默认过渡。普通重载的默认进入/退出动画包含展开和收缩，因此容器报告给父布局的尺寸会随动画变化；依赖该尺寸的父容器和同级元素也可能反复测量或放置。

不同过渡类型产生的工作不同：

- 淡入淡出和缩放主要更新图层属性。
- 滑动会改变子项的放置偏移量，不缩小容器报告的尺寸，但仍会执行 `LayoutModifier` 的放置逻辑。
- 展开和收缩会产生尺寸动画。
- 子内容自身的尺寸变化、`animateContentSize` 或自定义布局修饰符还可能增加布局工作。

如果父布局无须跟随内容伸缩，可以给外层稳定约束，并在内部使用淡入淡出、缩放或滑动。裁剪（clip）只限制绘制范围，不会阻止尺寸变化传给父布局。

退出时，界面内容会保留到内建进入/退出动画，以及注册在 `AnimatedVisibilityScope.transition` 上的自定义动画全部完成。保留期间有以下生命周期行为：

- 内容仍在组合中，也会响应自己观察的 `State`。
- `LaunchedEffect` 和 `rememberCoroutineScope` 启动的任务尚未因离开组合而取消。
- `DisposableEffect.onDispose` 尚未执行。
- 内容持有的图片、订阅和其他对象仍然存活。

独立创建的 `animate*AsState` 不属于 `AnimatedVisibilityScope.transition`，容器不知道它何时结束，因而可能先移除内容。需要与退出完成同步的自定义动画，应注册到作用域提供的 `transition` 上。

缩短退出时长只能缩短保留窗口，没有一个适用于所有产品的固定毫秒数。内容很重时，可把昂贵订阅移到更高层统一管理，或在退出开始后停止不再需要的数据更新；这属于业务生命周期设计，不能靠 `visible=false` 自动完成。

### 6. AnimatedContent：过渡期间新旧内容共存

`AnimatedContent` 切换目标时会同时查找新旧状态对应的界面内容。新内容执行进入动画，旧内容执行退出动画；旧内容在退出完成后才从组合中移除。默认 `SizeTransform` 还会为容器尺寸变化创建动画。快速连续切换时，可能同时保留多份尚未退出的内容。

使用 `AnimatedContent` 时要评估：

- 新旧内容同时参与组合、测量和绘制的成本。
- 旧内容在退出期间保留的副作用任务与资源。
- `SizeTransform` 是否让父布局持续变化。
- 目标状态变化频率是否高于用户能够辨认的切换频率。

内容回调必须使用它收到的 `targetState` 参数构建对应内容。`contentKey` 定义哪些目标状态属于同一内容身份；两个目标状态映射到同一个键时，不会触发内容切换动画。它适合过滤“状态对象改变但视觉身份不变”的更新，不能用来掩盖错误的状态建模。

`AnimatedVisibility` 适合一个内容节点的出现与消失，`AnimatedContent` 适合不同内容身份之间的替换。两者都可能保留退出内容，也都可能触发布局；应按业务语义和跟踪结果选择。

### 7. produceState、snapshotFlow 与 derivedStateOf

`produceState` 用 `remember { mutableStateOf(initialValue) }` 保存结果，并由 `LaunchedEffect` 启动负责生产状态值的协程。它提供无键、单键和多键重载；这里的键是决定协程何时重启的输入，不能把实现概括为固定的 `LaunchedEffect(Unit)`。键改变时，旧协程会取消并启动新协程；离开组合时也会取消。对回调式数据源，可用 `awaitDispose` 注销回调。

返回的 `State` 会合并相等值；写入与当前值相等的结果不会触发重组。不同值若按帧更新，下游仍会按其读取阶段失效。`produceState` 适合把外部异步或订阅式数据转成 Compose `State`；外部数据频率高不构成误用，判断依据是界面是否需要每个样本，以及读取位置是否合适。

`snapshotFlow` 把 Snapshot `State` 读取转换成冷流（cold Flow，即有人收集时才开始执行），适合驱动埋点、持久化等副作用。`distinctUntilChanged`、`sample` 或 `debounce` 会改变事件或时间语义，不适合替代屏幕上的逐帧动画。

`derivedStateOf` 适合输入变化频繁、输出变化较少的派生结果。例如滚动偏移不断变化，而界面只关心“是否越过阈值”。它根据派生结果的相等性策略决定是否通知读取方。若派生结果每帧都不同，`derivedStateOf` 只会增加观察与计算开销。

### 8. 强跳过模式能解决什么

强跳过模式（Strong Skipping）从 Kotlin 2.0.20 起默认启用。启用后，可重启的可组合函数即使带有不稳定参数，也可以被标记为允许跳过；稳定参数仍用对象相等性比较，不稳定参数则用实例相等性比较。编译器还会自动记忆可组合函数内的 lambda，并用它捕获的值作为键。

这些规则主要减少父级重组向子级传播，以及 lambda 的重复分配。它们不会改变以下行为：

- 可组合函数体直接读取的动画 `State` 变化后，读取作用域仍会失效。
- 布局、绘制或图层回调中的 `State` 读取仍由对应阶段观察。
- 跳过一个可组合函数不会暂停 `LaunchedEffect` 或 `rememberCoroutineScope` 的任务。
- `State` 更新不会因为某个可组合组被跳过而推迟到未来某次组合；对应观察者仍会按 Snapshot 机制收到失效通知。

较省工作的写法是捕获稳定的 `State` 持有者，在布局、绘制或 `graphicsLayer` 回调内读取其值。若先在可组合函数体中把 `State` 读取成每帧变化的标量，再让回调捕获这个标量，组合阶段已经建立了高频读取关系。

不要为了动画批量添加 `@NonRestartableComposable` 等编译器注解。它们会改变重组入口和可跳过性，只有编译器报告、基准数据和明确热点同时支持时才值得调整。

### 9. Lazy 列表中的动画所有权

惰性布局（Lazy layout）决定哪些列表项进入、保留或离开组合，预取和保留策略也由它控制。列表项内部的 `AnimatedVisibility` 只能管理该项仍在组合时的内容退出；当列表项离开 `LazyColumn` 的管理范围后，它不能要求外层继续保留退出动画。

列表数据的新增、删除和重排应优先使用稳定且唯一的键，配合 `Modifier.animateItem()`；列表项内部局部区域的显示隐藏再使用 `AnimatedVisibility`。这样可以分别处理数据项身份变化与项内内容可见性。

`rememberInfiniteTransition` 在宿主仍处于组合时持续请求动画帧。在可组合函数体读取它返回的值会触发组合；在绘制或图层回调中读取，才能把更新限定到后续阶段。离屏列表项是否仍在运行，取决于惰性布局是否仍保留该项，不能只根据像素是否可见推断。

大量列表动画的检查项包括：

- 列表项是否有稳定且唯一的键。
- 同屏活跃动画数量是否随滚动或数据更新持续增长。
- 离屏后已无产品价值的无限动画是否及时离开组合。
- 展开/收缩、`animateContentSize` 和列表项位置动画是否叠加触发布局。
- 图片、模糊、阴影和透明度图层是否把瓶颈移到 `RenderThread` 或 GPU。

### 10. 从 Compose 阶段看到显示结果

`graphicsLayer`、绘制回调或跳过组合，只会改变应用生成帧前半程的工作量。标准 HWUI 页面仍要经过 `RenderThread`、GPU、应用窗口的图形缓冲区提交、SurfaceFlinger 和 HWC。透明度、裁剪、模糊、复杂路径或较大的离屏图层可能减少主线程工作，同时增加 GPU 或内存带宽成本。

`ComposeView` 与 View 动画共用窗口和主线程帧回调；`AndroidView` 也不会得到独立帧预算。混合页面应通过同一条 `FrameTimeline` 分析 View 树遍历、Compose 工作、`RenderThread` 和系统合成，不能把某个跟踪区间当成整帧耗时。

Android 17 的内核基线是 `android17-6.18-2026-06_r6`。内核调度器、CPU 调频（cpufreq）、热限制（thermal）和同步栅栏等待（fence wait）会影响线程何时运行或等待，却不定义 `Animatable`、`Transition` 和内容移除的语义。跟踪数据出现线程可运行但迟迟未获调度、频率受限或栅栏等待时，再检查内核证据；只凭动画卡顿不能归因给调度器。

### 11. Perfetto、Studio 与线上指标各看什么

一次排查可以按以下顺序进行：

1. 在发布（release）、可分析（profileable）且不可调试（non-debuggable）的构建上复现固定交互。
2. 用 `FrameTimeline` 对齐预期与实际时间线，确认哪些帧迟到，以及应用是否按时完成。
3. 查看主线程 `Choreographer#doFrame`、Compose 组合跟踪、布局和绘制相关区间。
4. 查看 `RenderThread`、GPU、应用窗口缓冲区入队和 SurfaceFlinger，避免把 GPU 或送显时间算进 `doFrame`。
5. 将慢帧对应到动画状态、目标切换、仍然活跃的内容数量和状态读取阶段。

工具的职责要分开：

- **组合跟踪（Composition tracing）**：在系统跟踪数据中显示可组合函数调用，适合定位重组代码和耗时。
- **Layout Inspector**：显示运行中可组合函数的组合/跳过计数，适合验证重组范围；连接工具本身有开销。
- **Animation Preview**：可以暂停动画、拖动时间轴并检查动画值，适合验证曲线与多动画协调；它不分析真实运行时性能。
- **FrameTimeline**：把应用帧和 SurfaceFlinger 帧的预期/实际时间，以及卡顿类型放在同一时间轴上。
- **JankStats**：给线上帧数据附加页面或交互状态，便于按场景聚合。

`FrameMetrics.ANIMATION_DURATION` 表示一帧中发出动画回调所用的时间。它不能区分“动画帧”和“非动画帧”，也不覆盖整帧。Android 12 及以上更适合关注 `FrameTimeline` 派生的超期时间（overrun）；线上数据还要结合当前界面状态，避免把整页慢帧都归给某个动画。

### 12. 用 Macrobenchmark 建立回归门槛

动画基准要覆盖一次完整、可重复的状态迁移，并让测试知道动画何时结束。测试页面可以在 `MutableTransitionState.isIdle` 变为 `true` 后，暴露一个只供测试识别的语义属性或测试标签（test tag）。

下面的骨架用于采集展开动画的 FrameTimingMetric。

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class ExpandAnimationBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun expand() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(FrameTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.WARM,
        setupBlock = {
            startActivityAndWait()
            device.findObject(By.res("reset_collapsed")).click()
            device.waitForIdle()
        },
    ) {
        device.findObject(By.res("toggle_animation")).click()
        check(
            device.wait(
                Until.hasObject(By.res("animation_idle_expanded")),
                2_000,
            )
        )
    }
}
```

`toggle_animation`、`reset_collapsed` 和完成标记需要通过 `testTagAsResourceId` 或真实资源 ID 暴露。完成标记应在目标状态达到且 `Transition` 空闲后出现，避免只测到动画起点。每轮准备阶段都回到同一初始状态，测量区间只包含目标交互。

应同时关注 `frameOverrunMs` 的 P50/P90/P95/P99、`frameDurationCpuMs` 和 `frameCount`。`frameOverrunMs` 在 API 31 及以上按每帧截止时间计算，能适应高刷新率和可变帧率；`frameDurationCpuMs` 只覆盖界面线程与 `RenderThread` 生成一帧所用的 CPU 时间。`frameCount` 是辅助指标：它变化时，可能表示实现减少或增加了请求帧数量，不能只比较耗时分位值。`FrameTimingMetric` 不提供通用的 `jankFrameCount`，也不应按固定 16.6 ms 自行推导卡顿帧数。

基准配置文件（Baseline Profile）可以让 Android 运行时（ART）提前编译关键用户流程覆盖的应用与库代码，减少首次运行时的解释执行和即时编译（JIT）成本。它不能预编译 GPU 着色器、消除离屏合成，也不会改变 Snapshot 失效范围。用同一组 Macrobenchmark 对比应用基准配置文件前后的数据，才能判断当前动画是否受编译状态影响。

### 13. 无限动画、VectorConverter 与资源动画

`rememberInfiniteTransition()` 表达“进入组合后持续运行，离开组合后停止”。同一个 `InfiniteTransition` 的子动画共享一条逐帧循环，不会为每个值注册独立 VSync；每个子项仍要维护状态并计算插值。只给组件设置 `alpha = 0f`、移到屏外或用其他内容遮挡，都不会使它离开组合。加载指示、呼吸光和背景粒子不可见且无需继续计时时，应让对应分支移出组合，或由业务状态停止动画。

系统动画时长缩放为 0 时，Compose 会把无限动画推进到目标值并等待缩放恢复，不会继续逐帧更新。产品要验证该目标值能否作为合理的静止画面，并为“减少动态效果”保留易于理解的界面状态。

一组视觉值若能由同一相位推导，可以只保留一个 `animateFloat()`，在绘制或图层阶段计算颜色、缩放和偏移。`TwoWayConverter<T, V>` 只负责业务值与 `AnimationVector1D`～`4D` 的双向映射；每个维度应对应一个独立变量，并明确单位和有效范围。若 `convertFromVector()` 每帧都会创建复杂对象，应比较改用内置标量动画或单一相位推导后的对象分配量。

Animated Vector XML 使用另一套资源机制：`AnimatedImageVector` 解析矢量图和动画器资源，并按动画进度绘制，不经过 `TwoWayConverter`。资源应按 ID 稳定记忆，避免在动画帧内重复解析；路径节点、关键帧和同时播放数量仍需在目标设备上测量。

### 14. Pager 动画：区分当前页、稳定页和目标页

Pager 的 `currentPage` 表示最接近吸附位置的页面，会在拖动跨过吸附判定点时变化，不代表滚动已经完成。`settledPage` 只在滚动和动画停止后更新，适合曝光、重资源归属和业务选中；`targetPage` 表示本次滚动预计停下的页面，可用于动画目标。任意页面到当前吸附位置的距离应使用 `getOffsetDistanceInPages(page)`，避免手写公式在 `currentPage` 切换时反转符号。

页面的透明度、缩放、旋转和平移值应在 `graphicsLayer {}` 中读取，让滚动只更新图层属性；在可组合函数体提前读取 `currentPageOffsetFraction`，会让依赖该值的页面持续重组。延后读取高频状态并不会消除动画成本，裁剪、阴影、透明度和大面积旋转仍可能增加离屏合成与 GPU 带宽。

`beyondViewportPageCount` 表示可见区域两侧额外组合、测量和放置的页面，不包含滚动方向上的内部预取页面；应从默认值开始逐页增加，并同时比较首次进入页面的组合/测量耗时、内存峰值与预取命中率。`visiblePagesInfo` 是随测量频繁更新的结果，不代表页面生命周期。视频、地图和 `WebView` 等重资源应由 `settledPage`、可见性和生命周期共同控制。

同向嵌套的 Pager/惰性容器要明确哪个容器消费嵌套滚动、惯性滚动如何交接，以及子容器到达边界后是否继续滚动父容器。负 `pageSpacing` 产生重叠时，还要验证 `zIndex` 层叠顺序、命中区域、裁剪和无障碍顺序。点击标签页启动的 `animateScrollToPage()` 可能被新手势或新的滚动操作取消；调用返回后，还要根据状态确认目标页是否已经稳定展示。

### 15. 源码与资料索引

Compose 行为按 BOM 2026.08.00 与以下 1.12.0 source JAR 复核：

- [Compose BOM 2026.08.00 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.08.00/compose-bom-2026.08.00.pom)。
- [`androidx.compose.animation:animation:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/1.12.0/animation-1.12.0-sources.jar)：`AnimatedVisibility.kt`、`AnimatedContent.kt`。
- [`androidx.compose.animation:animation-core:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation-core/1.12.0/animation-core-1.12.0-sources.jar)：`Animatable.kt`、`AnimationState.kt`、`Transition.kt`、`InfiniteTransition.kt`。
- [`androidx.compose.ui:ui-android:1.12.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.12.0/ui-android-1.12.0-sources.jar)：`AndroidUiFrameClock.android.kt`、`AndroidUiDispatcher.android.kt`、图层与绘制修饰符实现。

以下 1.10.0 链接保留为上一轮核验基线：

- [`androidx.compose.animation:animation:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/1.10.0/animation-1.10.0-sources.jar)：`AnimatedVisibility.kt`、`AnimatedContent.kt`。
- [`androidx.compose.animation:animation-core:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation-core/1.10.0/animation-core-1.10.0-sources.jar)：`Animatable.kt`、`AnimationState.kt`、`Transition.kt`、`InfiniteTransition.kt`。
- [`androidx.compose.ui:ui-android:1.10.0` 源码](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-android/1.10.0/ui-android-1.10.0-sources.jar)：`AndroidUiFrameClock.android.kt`、`AndroidUiDispatcher.android.kt`、图层与绘制修饰符实现。

平台和内核边界按固定标签复核：

- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)。
- [Android 17 `FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)。
- [`android17-6.18-2026-06_r6` kernel tag](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)。

API 用法、性能工具和测量口径参考：

- [Compose Animation 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-animation)。
- [Compose 动画性能 quick guide](https://developer.android.com/develop/ui/compose/animation/quick-guide)。
- [Compose phases](https://developer.android.com/develop/ui/compose/phases)。
- [Graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)。
- [AnimatedVisibility 与 AnimatedContent](https://developer.android.com/develop/ui/compose/animation/composables-modifiers)。
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)。
- [Compose side effects 与 produceState](https://developer.android.com/develop/ui/compose/side-effects)。
- [Lazy list item animations](https://developer.android.com/develop/ui/compose/lists)。
- [Compose Pager](https://developer.android.com/develop/ui/compose/layouts/pager)。
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)。
- [Layout Inspector 调试 Compose](https://developer.android.com/develop/ui/compose/tooling/debug)。
- [Animation Preview](https://developer.android.com/develop/ui/compose/tooling/animation-preview)。
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)。
- [Macrobenchmark FrameTimingMetric](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)。
- [Compose Baseline Profile](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)。

### 检查清单

- 动画值在哪个阶段读取？是否在更早阶段也被解引用？
- 值变化后需要组合、测量、放置、绘制还是图层属性更新？
- `AnimatedVisibility` 或 `AnimatedContent` 退出期间保留了哪些内容、副作用任务和资源？
- 动画中途改变目标时，是重新定向、取消后续工作，还是由产品层屏蔽输入？
- `produceState` 的键是否完整，外部订阅是否在 `awaitDispose` 中注销？
- `derivedStateOf` 的输出是否比输入低频？
- 惰性列表项的身份变化是否由稳定键和 `animateItem` 管理？
- 帧预算是否来自本帧 `FrameTimeline`，是否同时核对应用、GPU 与送显？
- Android Studio 工具、实验室基准和线上指标是否各自回答了合适的问题？
- 优化是否在发布版、可分析构建和代表性设备上复测？

## SharedTransition 元素匹配、绘制与同步

单个动画稳定后，共享元素过渡需要同时维护起止内容、overlay 绘制和布局坐标。元素匹配失败或重复测量会直接影响连续性。

### 1. 先界定实现层级

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Compose Animation：`1.12.0`
> - AndroidX 源码快照：`963bf914f78b389bdddef0da7f36bee19d897274`
>
> `SharedTransitionLayout` 位于 Compose Animation 的 `commonMain`（Kotlin Multiplatform 的公共源码集），元素匹配、Lookahead 布局、图形层和 overlay 都由 AndroidX 实现。Android Framework 与内核没有名为 SharedTransitionLayout 的专用渲染路径；Android 17 只负责内容进入 HWUI（Android 的硬件加速 UI 渲染器）后的窗口绘制、BufferQueue、SurfaceFlinger 与显示流程。

共享元素过渡会把两个页面中代表同一对象的内容匹配起来，在页面切换时连续改变位置和尺寸。这里关注它对组合、布局、绘制和 GPU 的影响。一般 Compose 性能方法见 [22.3 Compose 性能、Compiler 与 Modifier.Node 诊断](03-compose-compiler-modifier-diagnostics.md)，普通动画成本已由本文前两节建立基线。

为便于对照 API 和源码，本文保留几个常用英文词：`key` 是两端内容的匹配标识；`bounds` 是包含位置与尺寸的矩形边界；`entry` 是某个 `key` 在源端或目标端的一条注册记录；`overlay` 是 `SharedTransitionScope` 根节点内用于置顶绘制的覆盖区域。这些词都指 Compose 作用域内的匹配、布局或绘制概念。

### 2. API 架构：scope、可见性与 key

`scope` 是一组 API 共享的作用域；这里负责限定哪些内容可以互相匹配。源端（source）指正在退出的内容，目标端（target）指正在进入的内容。

`SharedTransitionLayout` 做两件事：

1. 创建 `SharedTransitionScope`，集中管理 `key` 匹配、`bounds` 动画和过渡是否活跃；
2. 创建一个 `Box` 布局，在根 `Modifier` 中取得当前坐标与 Lookahead 目标坐标，并提供 overlay 绘制入口。

Compose 1.12.0 还提供 `SharedTransitionScope { modifier -> ... }` 这个 Composable（可组合函数）入口。它不额外创建 `Box`，但调用方必须把回调给出的 `Modifier` 放在最上层子节点；该节点还要适合作为 overlay 的最高绘制根。大多数页面使用 `SharedTransitionLayout`，更容易保持正确坐标与 z-order（同一绘制区域中的前后顺序）。

#### 2.1 AnimatedVisibilityScope 告诉系统谁在进入

`sharedElement()` 和 `sharedBounds()` 通常接收 `AnimatedVisibilityScope`，让共享过渡知道哪一端正在进入、哪一端正在退出。这个 scope 来自：

- `AnimatedContent`
- `AnimatedVisibility`
- Navigation 2 的 destination content（导航目的地内容）
- Navigation 3 的 `LocalNavAnimatedContentScope`

`SharedTransitionScope` 根据可见性过渡判断相同 `key` 的哪一端正在变为可见，并用该端的 Lookahead `bounds` 作为目标。只创建相同 `key`、却没有传入正确的可见性 scope，系统无法稳定确定进入端。

#### 2.2 key 是匹配身份，不是重组开关

`rememberSharedContentState(key)` 在 1.12.0 中通过 `remember(key)` 保存 `SharedContentState`。`remember` 会让该对象跨重组保留；列表和详情页应从同一个业务 ID 派生相同 `key`，例如 `article-image:42`。

Compose 的 `key()` 可以在组合结构移动时保留节点身份，但不会自动缩小重组范围。减少重组要从稳定参数、延后状态读取、避免每帧在 Composition（Compose 生成并维护 UI 树的组合阶段）中读取动画值等方面处理。

相同 `key` 通常应同时存在一个退出 `entry` 和一个进入 `entry`。快速连续导航可能短暂产生多条记录，源码会从可见记录中选择目标。若同一个 `key` 出现多个正在进入的内容，匹配结果便不明确。

### 3. 一套可维护的基本写法

这段代码让卡片容器使用 `sharedBounds()`，其中视觉内容相同的图片使用 `sharedElement()`。列表端与详情端必须传入相同的业务 ID。

```kotlin
@Composable
fun ArticleTransitionHost(
    article: ArticleUi,
    expanded: Boolean,
) {
    SharedTransitionLayout {
        AnimatedContent(
            targetState = expanded,
            label = "article-detail",
        ) { isExpanded ->
            ArticleScene(
                article = article,
                expanded = isExpanded,
                animatedVisibilityScope = this@AnimatedContent,
            )
        }
    }
}

@Composable
private fun SharedTransitionScope.ArticleScene(
    article: ArticleUi,
    expanded: Boolean,
    animatedVisibilityScope: AnimatedVisibilityScope,
) {
    Column(
        modifier = Modifier.sharedBounds(
            sharedContentState = rememberSharedContentState(
                key = "article-container:${article.id}",
            ),
            animatedVisibilityScope = animatedVisibilityScope,
            resizeMode = SharedTransitionScope.ResizeMode.scaleToBounds(),
        ),
    ) {
        Image(
            painter = article.painter,
            contentDescription = null,
            modifier = Modifier
                .sharedElement(
                    sharedContentState = rememberSharedContentState(
                        key = "article-image:${article.id}",
                    ),
                    animatedVisibilityScope = animatedVisibilityScope,
                )
                .then(if (expanded) Modifier.fillMaxWidth() else Modifier.size(96.dp)),
        )
        Text(
            text = article.title,
            style = if (expanded) {
                MaterialTheme.typography.headlineMedium
            } else {
                MaterialTheme.typography.titleMedium
            },
        )
    }
}
```

`sharedBounds()` 放在尺寸 `Modifier` 前，让它能用动画 `bounds` 约束后续内容；图片两端的视觉内容相同，因此使用 `sharedElement()`。示例省略了列表与详情的周边布局。生产代码还要让图片请求使用一致的内存缓存 `key`，以免目标端重新解码时发生内容跳变。

### 4. Lookahead、approach 与每帧成本

#### 4.1 Lookahead 负责取得目标

`SharedBoundsNode.measure()` 在 Lookahead pass 测量子节点，完成放置后记录目标尺寸和位置。坐标相对 `SharedTransitionScope` 根节点，而不是相对整个 window（应用窗口）。

这带来两个边界：

- `SharedTransitionLayout` 自身在窗口中移动时，目标坐标也会随之移动；
- 滚动容器会被标记为 motion frame of reference（运动参考系），源码借此区分结构位置变化与滚动位移；连续滚动仍可能增加节点放置工作。

`skipToLookaheadPosition()` 可以让节点在过渡期间使用目标位置，但父布局频繁移动时会增加 placement pass，也就是放置阶段的重复遍历。它适合解决明确的目标位置问题，不宜普遍加在每个共享节点上。

#### 4.2 approach 决定重测还是缩放

`sharedElement()` 的子节点会使用动画 `bounds` 生成的固定 constraints（布局给出的宽高限制）重新测量和布局。它与 `RemeasureToBounds` 的成本特征相近：`bounds` 尺寸逐帧变化时，子节点可能逐帧执行 measure/layout（测量与布局）。

`sharedBounds()` 提供两种 resize mode：

| resize mode | 1.12.0 行为 | 适合内容 | 主要成本 |
| --- | --- | --- | --- |
| `scaleToBounds()` | 用 Lookahead constraints 得到稳定的目标布局，过渡期间缩放到动画 `bounds` | `Text`、不适合频繁改变约束的复杂布局 | 图形缩放与可能的裁剪；子节点无需逐帧重排 |
| `RemeasureToBounds` | 用动画 `bounds` 生成的固定 constraints 重新测量子节点 | 背景、宽高比不同的图片、能低成本响应尺寸变化的布局 | 动画期间可能逐帧 measure/layout |

`Text` 在宽度变化时可能重新换行。对它使用 `RemeasureToBounds`，字符排版和父子尺寸可能逐帧改变；官方文档因此优先建议 `scaleToBounds()`。如果图片需要随宽高比持续改变裁剪结果，`RemeasureToBounds` 可能更符合视觉要求，但要实测 CPU 成本。

#### 4.3 placeholder 决定父布局是否跟随

placeholder 是共享内容过渡时留在原布局中的占位区域。默认的 `PlaceholderSize.ContentSize` 让退出端向父布局报告初始内容尺寸，让进入端报告 Lookahead 目标尺寸；父布局不会跟随每一帧的动画 `bounds` 改变。

`PlaceholderSize.AnimatedSize` 会把动画尺寸报告给父布局。它能让周边内容随共享元素移动，也可能使更大的父子树逐帧重新布局。交互没有这种联动要求时，保留默认值通常更稳定。

### 5. sharedElement 与 sharedBounds 的性能边界

两者的选择依据是视觉内容是否相同，不是初始尺寸是否相等。

| 维度 | `sharedElement()` | `sharedBounds()` |
| --- | --- | --- |
| 内容关系 | 两端应是相同视觉内容 | 两端内容可以不同，只共享容器 `bounds` |
| 过渡期间的内容 | 只绘制正在进入的目标内容 | 进入与退出内容通过 enter/exit transition（进入/退出动画）共存 |
| 子节点尺寸处理 | 按动画 `bounds` 重测、重排 | 默认 `scaleToBounds()`，可选逐帧重测 |
| 常见用途 | 跨页主图（hero image）、相同图标、可移动内容 | 卡片到详情、`Text` 样式变化、容器变换 |
| 透明混合 | 通常只有目标内容 | 默认 `fadeIn`/`fadeOut` 可能同时混合两端 |

`sharedBounds()` 可能保留两棵内容子树并同时绘制；alpha（透明度）混合区域较大时，GPU 成本会上升。`sharedElement()` 只绘制目标内容，但它仍有逐帧 constraints 变化和 `GraphicsLayer` 记录成本。无法仅凭 `Modifier` 类型断定哪一种在所有内容上更快。

两者也没有固有的重组范围差异。重组来自各自内容读取的 Compose 可观察状态；`sharedBounds()` 的进入和退出内容同时存活，可能带来更多活跃的 Composition，具体范围仍由调用方的状态结构决定。

### 6. GraphicsLayer、overlay 与裁剪

#### 6.1 活跃的 overlay entry 按需持有 GraphicsLayer

Compose 1.12.0 不会在 `SharedBoundsNode.onAttach()` 时立刻分配图形层。节点需要在 overlay 中绘制时，才调用 `createGraphicsLayer()`，并在 draw 阶段把子节点的绘制命令记录进去；退出 overlay、节点 detach（从树中分离）或节点 reset（被复用）时会释放该层。

这层资源用于在原位置与 overlay 之间移动绘制结果。它不等于固定大小的 Bitmap 缓存，也不能按 `width × height × 4` 推导全部内存。RenderNode（HWUI 的可记录绘制节点）、display list（录制后的绘制命令列表）、离屏纹理和 GPU backing（GPU 侧实际存储）是否出现，取决于图形效果与渲染后端。

应用无需在过渡结束时手工清理图形层。实现会在不再需要 overlay 或节点离开 Composition 时释放它。若使用 caller-managed visibility（由调用方直接传入可见状态的 API），不可见节点可能继续留在树中；官方文档建议在 `isTransitionActive == false` 后移除不可见端。

#### 6.2 overlay 会改变父级效果边界

默认情况下，共享内容在 scope overlay 里绘制，不再受原父节点的 clip（裁剪）、alpha 或 scale（缩放）影响。视觉上仍需要这些效果时，要把它们明确应用到共享节点或 overlay。

需要圆角或裁剪时，应根据语义选择：

- 把 `clip()` 放在 `sharedElement()` / `sharedBounds()` 后，让裁剪成为图形层内容的一部分；
- 使用 `clipInOverlayDuringTransition` 提供 overlay 坐标系中的 clip path（矢量裁剪路径）；
- 嵌套 `sharedBounds()` 时复用父级裁剪；
- 父级没有裁剪、淡入淡出或缩放等影响时，再考虑 `renderInOverlayDuringTransition = false`。

`zIndexInOverlay` 只控制 scope overlay 内的顺序。Compose 1.12.0 在绘制前按 zIndex 排序 renderer（负责绘制某个 `entry` 的对象）；活跃 renderer 较多时，排序与逐个 `drawLayer()` 也会增加 CPU/GPU 工作。

#### 6.3 modifier 顺序会改变目标 bounds

共享 `Modifier` 前的尺寸与 padding（内边距）会参与确定初始和目标 `bounds`；后续 `Modifier` 接收共享节点给出的动画 constraints。列表端与详情端顺序不一致时，位置或尺寸容易在起始帧跳变。

`requiredSize()` 还会覆盖约束，放置位置不同会让父布局观察到不同尺寸。遇到跳变时，应比较两端完整的 `Modifier` 链，再调整动画参数。

### 7. 常见性能风险与对应处理

#### 7.1 在 Composition 中读取每帧状态

`BoundsAnimation` 的主要状态在 layout/draw 阶段读取，不要求业务逐帧重组。若业务在大范围 Composable 中读取 transition progress（通常为 0 到 1 的过渡进度），再据此构造颜色、尺寸、图片请求或列表，就会把本可在布局或绘制阶段完成的更新扩大到 Composition。

适合放在 `graphicsLayer {}`、`drawWithContent {}` 或 layout lambda（布局回调）中的值，应延后到对应阶段读取。确需重组时，用 Layout Inspector 的 recomposition count（重组次数）确认范围，不要把所有动画帧都称为“重组风暴”。

#### 7.2 重复添加 graphicsLayer

共享 `Modifier` 已经按需维护内部 `GraphicsLayer`。业务再为同一节点增加多个 `graphicsLayer()`、模糊、阴影、alpha 或离屏 compositing（先画到中间缓冲再合成），可能引入更多 render pass（一次渲染任务）和中间纹理。

只保留有明确视觉用途的层，并在 Perfetto/GPU 工具中验证。无作用的 layer 可以删除；有些属性动画适合在 layer 上更新，因此不能把所有 `graphicsLayer()` 都视为问题。

#### 7.3 大面积 alpha 与 overdraw

`sharedBounds()` 默认同时显示进入和退出内容，并用 `fadeIn`/`fadeOut` 过渡。两张全屏图或复杂列表长时间重叠，会产生明显的 fill rate（GPU 单位时间处理像素的能力）和显存带宽压力，也会增加 overdraw（同一像素在一帧内被重复绘制）。

可以缩小共享容器范围、减少同时变化的背景层、调整进入/退出动画，或把静态不透明背景放在共享区域外。优化依据是覆盖面积和 GPU duration（GPU 完成该帧所需时间），不是共享 `key` 的数量。

#### 7.4 共享过渡与列表滚动同时进行

列表仍在惯性滚动时启动共享过渡，会同时发生 Lazy layout（只布局可见项及预取项）、图片请求、Lookahead、approach placement 和窗口绘制。motion frame of reference 能处理滚动坐标，却不会消除这些工作。

产品交互允许时，可以结束 fling（松手后的惯性滚动）再切换详情；需要并行时，要保证 item key（列表项身份）稳定、图片已命中缓存，并减少 `AnimatedSize`、`RemeasureToBounds` 和大面积渐变的叠加。

#### 7.5 动画 spec 的求值成本通常较小

默认 bounds transform 使用中低 stiffness（弹簧刚度）的 spring（弹簧动画）。spring 的结束时间由收敛条件决定，tween（按时间插值的动画）的 duration 固定；两者逐帧求值的成本通常远小于复杂内容重测、文字排版和 GPU 绘制。

选择 animation spec（动画规格）时，应先满足交互与中断连续性，再观察它让高成本内容活跃了多少帧。缩短 duration（持续时间）可能减少总工作，也可能增大逐帧变化幅度并造成视觉突兀，不能只按“spring 更耗性能”判断。

### 8. LazyList 中的共享元素

`LazyList` 的难点是源列表项可能在过渡结束前离开 Composition。可靠实现需要同时满足：

- `items(key = ...)` 使用稳定的业务 ID；
- `rememberSharedContentState()` 的 `key` 与详情端一致；
- 源端与目标端位于同一个 `SharedTransitionScope`；
- 目标端完成组合、测量和放置后，系统才能获得有效的 Lookahead `bounds`；
- 两端图片使用一致的图片内存缓存 `key`；
- 使用 caller-managed visibility 时，在过渡结束后移除不可见节点。

若点击后立刻替换整个列表树，源 `entry` 可能在目标端获得 `bounds` 前 detach。`AnimatedContent`、Navigation 或官方 `AnimatedVisibility` 示例会让进入和退出内容在过渡窗口内同时存在，适合优先作为可见性容器。

预取应准备数据、图片和目标页面不可避免的昂贵资源。提前组合整个详情树会延长对象生命周期，也可能让未展示页面参与状态观察；只有 trace（按时间记录系统与应用事件的性能轨迹）证明首次组合是瓶颈时，再设计受控的 precompose（预先组合）。

### 9. Predictive Back

Predictive Back（预测性返回）让用户在返回手势完成前预览目的地。`SharedTransitionLayout` 自身不读取系统 back progress（0 到 1 的返回手势进度）；Navigation 或调用方负责把进度送入目的地的 transition，共享元素再从对应的 `AnimatedVisibilityScope` 获得进入、退出状态和目标。

截至 2026 年 8 月，官方给出的集成边界是：

- Navigation 3 各版本支持 Predictive Back；
- Navigation Compose 2 使用 2.8.0 或更高版本；
- Android 15 及以上不再提供 Predictive Back 开发者开关；应用仍需使用受支持的返回 API。`targetSdk >= 35` 时无需把 `enableOnBackInvokedCallback` 设为 `true`，`targetSdk <= 34` 时仍需显式开启；
- Android 14 设备还要在开发者选项中启用 Predictive Back；
- 应用运行在 Android 16 及以上且 `targetSdk >= 36` 时，系统预测性返回动画默认启用；迁移期间仍可按官方说明临时选择退出。

Android 17 沿用这套标准机制，没有独立的 SharedTransitionLayout 帧同步平台 API。手势事件、Compose 过渡状态、Choreographer（主线程帧回调调度器）与 HWUI 提交，仍要在 Perfetto 中按同一 FrameTimeline（把计划帧与实际帧关联起来的时间线）检查。

#### 9.1 BackHandler 与 PredictiveBackHandler

`BackHandler` 适合处理一次完成的返回动作，不提供连续 progress。需要自定义手势驱动动画时使用 `PredictiveBackHandler`，它提供一串 `BackEventCompat` 事件及 0 到 1 的进度；使用 Navigation 内建 Predictive Back 时，不要再添加会抢先消费同一手势的 handler（回调处理器）。

自定义进度流应更新专门的动画状态，避免每个事件都重建导航图、重发图片请求或重组整页。取消手势时要恢复初始状态，手势完成后再提交返回栈变化。

手势驱动的过渡可以暂停、反向或取消，比固定 tween 更容易暴露源端 detach、重复 `key` 和目标端尚未放置的问题。测试应覆盖完成、取消、快速往返和滚动中返回。

### 10. Perfetto、Layout Inspector 与可视化调试

#### 10.1 源码没有专用 SharedTransition trace 轨道

Compose 1.12.0 的 `SharedTransitionScope.kt`、`SharedContentNode.kt` 与 `SharedElementEntry.kt` 没有为每个 `key` 写入固定的 Perfetto slice。Perfetto 是 Android 的系统级性能追踪工具；track 是一条事件轨道，slice 是带起止时间的区间事件。分析时应组合观察：

- UI Thread（应用主线程）上的 Choreographer、Compose recomposition、measure/layout 与 draw；
- RenderThread（HWUI 的渲染线程）的 `DrawFrame`、资源更新和命令提交；
- FrameTimeline 的 expected/actual frame（计划帧与实际帧）；
- GPU completion（GPU 完成时刻）与 GPU duration（GPU 执行时长）；
- 图片解码、列表预取和其他并行工作；
- 应用为导航开始、目标端首次放置和过渡结束增加的自定义 trace。

如果 approach 阶段的布局耗时变长，再结合代码配置确认原因是 `sharedElement()`、`RemeasureToBounds`、`AnimatedSize`，还是业务父布局反复失效。GPU duration 上升时，检查覆盖面积、alpha、裁剪、阴影和额外的 `graphicsLayer()`。

#### 10.2 Layout Inspector 的适用范围

Compose Layout Inspector 可以检查：

- 两端 `key` 是否一致；
- `Modifier` 顺序；
- 源端与目标端是否同时在树中；
- recomposition count 与 skip count（重组次数与跳过重组次数）；
- 不可见的 caller-managed 节点是否长期保留。

它不能给出 GPU 渲染 pass 数量、`GraphicsLayer` backing 或 SurfaceFlinger composition type（合成类型）。Inspector 本身也会影响运行，正式性能采样应关闭 Inspector，再用 release/profileable（发布版或允许性能分析的构建）复测。

#### 10.3 Compose 1.12.0 的视觉调试

Compose Animation 1.12.0 继续提供实验性的 Lookahead animation visual debugging，可显示目标 `bounds`、运动轨迹、匹配数量、未匹配元素和过渡活跃状态。该 API 仍需使用 `ExperimentalLookaheadAnimationVisualDebugApi`，不应包装进正式页面的常驻路径。

这段包装只用于 debug 构建，帮助定位 `key` 匹配和目标位置问题。

```kotlin
@OptIn(ExperimentalLookaheadAnimationVisualDebugApi::class)
@Composable
fun SharedTransitionDebugOverlay(
    enabled: Boolean,
    content: @Composable () -> Unit,
) {
    LookaheadAnimationVisualDebugging(
        isEnabled = enabled,
        isShowKeyLabelEnabled = true,
        content = content,
    )
}
```

可视化会给整个 `content` 子树增加调试绘制，不能与正式帧耗时放在同一组结果中。用它排除坐标与匹配错误后，应关闭调试再录制 Perfetto。

#### 10.4 建立对照实验

共享过渡评测至少保留三组相同导航：

1. 只有页面进入/退出动画，没有共享 `Modifier`；
2. 只启用一个 `sharedElement()`；
3. 启用完整的 `sharedElement()` / `sharedBounds()` 集合。

三组都要保持相同数据、图片缓存状态、构建类型、动画时长和设备温度。比较 frame deadline miss（未在截止时间内完成的帧）、UI Thread layout、RenderThread、GPU duration 和内存峰值，才能判断新增成本来自哪个层级。

### 11. 高级配置的安全边界

#### 11.1 BoundsTransform 只定义 Rect 动画 spec

`BoundsTransform.createAnimationSpec(initialBounds, targetBounds)` 返回 `FiniteAnimationSpec<Rect>`。它能改变 timing（时间控制）、spring 或 keyframes（关键帧），但 API 本身没有沿任意几何 `Path` 移动的参数。

需要曲线路径、旋转或形变时，可以在共享 `bounds` 之外增加受控的 `graphicsLayer` 或绘制类 `Modifier`，也可以使用 caller-managed visibility 驱动视觉属性。过渡结束后，语义节点、点击区域和无障碍焦点都应回到目标布局。

#### 11.2 SharedContentConfig 用于动态启停

1.12.0 的 `rememberSharedContentState(key, config)` 允许通过 `SharedContentConfig` 中的 `SharedContentState.isEnabled`，动态决定某个 `key` 是否参与匹配。导航方向、系统“减少动态效果”偏好或设备降级策略适合放在这里。

启停状态在过渡中变化时要定义清楚：立即取消、保持现有动画，还是等下一次导航生效。默认的 `shouldKeepEnabledForOngoingAnimation` 为 `true`，因此正在进行的动画会完成，禁用结果随后生效。若目标 `entry` 在动画中被移除，还可以通过 `alternativeTargetBoundsInTransitionScopeAfterRemoval` 提供替代终点；默认行为是取消这一组共享过渡。

#### 11.3 多步骤过渡

多步骤场景应为每个持续身份使用稳定 `key`，并让每一步只有一个明确的进入端。复用一个 `key` 同时表示多个视觉对象，会让匹配状态机面对多个候选。

如果步骤需要让不同内容连续变形，可以用外层 `sharedBounds()` 保持容器连续性，内部按步骤使用独立的 `sharedElement()`；同时控制 overlay zIndex 与父级裁剪，避免嵌套层互相遮挡。

### 12. View 系统迁移边界

Compose Shared Transition 只在同一个 `SharedTransitionScope` 内匹配。目前官方明确不支持 View 与 Compose 共享元素互操作，包括 `AndroidView`，以及跨独立 window 的 `Dialog`、`ModalBottomSheet` 等容器。

它也不能直接替代 Activity 之间由 `ActivityOptions.makeSceneTransitionAnimation()` 和 Window Transition 管理的平台共享元素。两者的坐标、生命周期、snapshot（过渡使用的内容快照）、overlay 和 window 边界不同。

迁移可以分三种情况：

| 当前架构 | 建议路径 |
| --- | --- |
| Fragment 目的地中逐页迁移至 Compose | 保留 Fragment Navigation 和 View/Window transition 边界；不要尝试用 `key` 匹配 View 与 Compose 内容 |
| 同一 Compose `NavHost` 内的目的地 | 用 `SharedTransitionLayout` 包住 `NavHost`，传递 `SharedTransitionScope` 与目的地的 `AnimatedContentScope` |
| 已全部迁移到 Compose Navigation | 在 Navigation 2 或 Navigation 3 官方共享元素接口上配置，并同时验证 Predictive Back |

混合期若视觉上需要连续，可以用普通 enter/exit、crossfade（交叉淡入淡出）或业务自定义 snapshot 方案，但这些方案不具备 `SharedTransitionScope` 的自动 `key` 匹配。

### 13. 评审清单

- Compose 版本是否至少使用 1.10 的稳定 Shared Transition API；
- `SharedTransitionLayout` 是否位于源端与目标端的共同祖先；
- 两端是否使用相同且稳定的业务 `key`；
- `sharedElement()` 是否用于相同视觉内容，`sharedBounds()` 是否用于容器变化；
- `Text` 是否优先评估 `scaleToBounds()`；
- 是否误把 Lookahead pass 计作第二次 GPU 渲染；
- 是否误把 `GraphicsLayer` 写成 Bitmap 缓存；
- overlay 裁剪、父级 alpha、scale 与 zIndex 是否符合预期；
- `Modifier` 顺序是否在两端保持一致；
- `AnimatedSize` 或 `RemeasureToBounds` 是否扩大每帧布局范围；
- 大面积 fade、模糊、阴影和额外 `graphicsLayer()` 是否同时存在；
- `LazyList` 源端是否在目标端获得 Lookahead `bounds` 前被移除；
- 图片缓存 `key` 是否与共享内容 `key` 协调；
- Predictive Back 是否由 Navigation 或 `PredictiveBackHandler` 提供连续进度；
- Layout Inspector 与视觉调试是否只用于定位，正式采样是否关闭；
- Perfetto 是否同时查看 UI Thread、RenderThread、FrameTimeline 与 GPU；
- 是否把 Compose overlay 误判为独立 SurfaceFlinger layer。

### 14. SharedTransition 小结

`SharedTransitionLayout` 的性能成本主要来自额外的 Lookahead/approach 布局、活跃 overlay `entry` 按需使用的 `GraphicsLayer`，以及进入与退出内容可能同时绘制。SurfaceFlinger 通常只处理同一个 App Window，瓶颈更可能出现在应用 UI Thread、RenderThread 和 GPU。

`sharedElement()` 与 `sharedBounds()` 的选择取决于内容关系：相同视觉内容用 `sharedElement()`；容器连续但内容变化时用 `sharedBounds()`，再在 `scaleToBounds()` 与 `RemeasureToBounds` 之间选择。元素数量、spring 或 `key()` 都不能脱离具体内容单独作为性能结论。

Android 17 没有 SharedTransitionLayout 专属管线。排查时可用可视化与 Layout Inspector 确认 `key`、`bounds` 和 `Modifier`，关闭调试工具后，再用 Perfetto 对比 layout、draw、RenderThread、GPU 与 FrameTimeline。

## 常见误区

### API 版本由 Compose 依赖决定

Shared Transition API 在 Compose Animation 1.7 以实验 API 形式发布，到 1.10 转为稳定 API。截至 2026 年 8 月 15 日，Google Maven 中最新稳定版是 1.12.0；1.13.0-alpha01 属于预览版。1.12.0 继续提供实验性的共享元素可视化调试能力。

这套 API 没有 Android 15 / API 35 的平台门槛。只要应用使用的 Compose 版本及其 Android 最低版本满足要求，就能使用共享元素。Android 15 起取消了 Predictive Back 开发者开关；应用迁移到受支持的返回 API 后可以获得对应系统动画。这与 `SharedTransitionLayout` 的引入版本无关。

### Lookahead pass 不等于第二次 GPU 渲染

`SharedTransitionScope` 内部使用 `LookaheadScope`。这里的 pass 是布局系统对节点树的一次遍历：Lookahead pass 先计算动画结束时的尺寸和坐标，approach pass 再按当前动画 `bounds` 测量或放置节点。两者都属于布局阶段。

一帧仍按 Compose 的布局结果进入绘制。Lookahead 增加的是目标布局计算；是否多次测量、是否记录额外图形层、是否同时绘制进入端与退出端，要看 `Modifier` 和 resize mode（尺寸适配方式）。把 Lookahead 概括成“两次 GPU 绘制”，会混淆 CPU 布局与 GPU 绘制。

### sharedElement 不复用位图

Compose 1.12.0 在需要 overlay 绘制时为共享内容创建 `GraphicsLayer`。`GraphicsLayer` 是记录绘制命令并允许复用这些命令的 Compose 图形层；实现会在 draw 阶段通过 `layer.record { drawContent() }` 记录内容，再以 `drawLayer()` 绘制。它不会把源 Composable 截成 Bitmap 后交给目标端复用。

图片内容是否复用同一个解码结果，由 Coil、Glide 等图片加载库或业务缓存决定。共享元素 `key` 只负责过渡匹配，不能代替图片内存缓存的 `key`。

### overlay 不会创建独立 SurfaceFlinger layer

SharedTransition overlay 是 `SharedTransitionScope` 根节点 draw pass 内的绘制区域。共享内容仍进入同一个 App Window buffer（应用窗口提交的像素缓冲区），SurfaceFlinger 这个系统合成器通常只看到宿主窗口的 layer。

共享元素可能增加应用侧的图形层记录、裁剪、缩放、透明混合和过绘制，进而推迟窗口 buffer 完成时间；进入 Compose overlay 不会直接增加 HWC（Hardware Composer，硬件合成器）要合成的窗口 layer 数量。

按生产者与结果位置来判断，App 内部的 GPU 图形层或离屏中间结果仍由宿主窗口消费。只有通过 `SurfaceControl` 独立提交的 buffer，才会自然对应独立的 SurfaceFlinger layer。BufferQueue 的 slot（可循环使用的缓冲槽位）、GraphicBuffer 复用与生产者/消费者模型见 [2.8 BufferQueue、Gralloc 与 Sync Fence](../../part1-fundamentals/ch02-rendering/08-bufferqueue-gralloc-sync-fence.md)。

### 没有“最多五个元素”的平台阈值

源码没有 `≤5` 的限制或推荐值。一个简单图标和一个包含大图、模糊、阴影的卡片，成本差距远大于元素数量本身。活跃数量应结合内容复杂度、屏幕覆盖面积、resize mode、设备 GPU 和目标刷新率评估。

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

- [Compose Shared element transitions](https://developer.android.com/develop/ui/compose/animation/shared-elements)：scope、`Modifier` 顺序、overlay、限制与 Lazy 示例。
- [Customize shared element transitions](https://developer.android.com/develop/ui/compose/animation/shared-elements/customize)：resize mode、裁剪、zIndex 与动态启停。
- [Navigation with shared elements](https://developer.android.com/develop/ui/compose/animation/shared-elements/navigation)：Navigation 2/3 与 Predictive Back 集成。
- [Compose Animation release notes](https://developer.android.com/jetpack/androidx/releases/compose-animation)：1.7 实验发布、1.10 稳定与后续版本变化。
- [Google Maven：Compose Animation 版本元数据](https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/maven-metadata.xml)：核对 1.12.0 稳定版与 1.13.0-alpha01 预览版。
- [`SharedTransitionScope.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedTransitionScope.kt)：scope、overlay、`key` 匹配和公开 API。
- [`SharedContentNode.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedContentNode.kt)：Lookahead/approach measure、`GraphicsLayer` 记录与释放。
- [`SharedElementEntry.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedElementEntry.kt)：原位/overlay 选择和图形层状态。
- [`SharedTransitionScope.kt`（Compose 1.11.4 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedTransitionScope.kt)：保留旧版锚点，便于比较 API 与实现变化。
- [`SharedContentNode.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedContentNode.kt)：保留旧版节点实现锚点。
- [`SharedElementEntry.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedElementEntry.kt)：保留旧版 entry 实现锚点。
- [Predictive Back for Compose](https://developer.android.com/develop/ui/compose/system/predictive-back)：系统行为、Navigation 与自定义 progress。
- [Add support for the predictive back gesture](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture)：返回 API 迁移、Android 15 开发者开关变化与清单配置。
- [Android 16 behavior changes](https://developer.android.com/about/versions/16/behavior-changes-16)：target API 36 及以上时预测性返回系统动画的默认行为。
- [`Choreographer.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)：Android 17 应用帧起点与 FrameTimeline。
- [`ViewRootImpl.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：Compose 宿主窗口进入 HWUI 的平台入口。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线；SharedTransitionLayout 不直接依赖内核 API。
