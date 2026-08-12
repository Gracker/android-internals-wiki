---
title: "Compose SharedTransitionLayout 共享元素性能"
chapter: "22.27"
status: finalized
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [Compose, SharedTransition, Animation, Performance, Rendering]
related_chapters: ["22.5", "22.15", "22.3", "2.1"]
last_verified: "2026-08-01"
last_verified_against: "AndroidX Compose Animation 1.11.4 源码快照 854220f44ea8ea80fee824a6c5a045f39bede289；Android 17 / API 37 / android-17.0.0_r1；内核 android17-6.18-2026-06_r6；官方 Compose Shared elements 文档"
confidence: high
pipeline_stage: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
last_draft_polish_at: "2026-08-01T11:35:38+08:00"
last_draft_polish_run_id: "20260801-113538-draft-polish-9c0d3e58"
last_review_finalize_at: "2026-08-01T12:06:00+08:00"
last_review_finalize_run_id: "20260801-120559-a2aecf57"
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/compose/animation/shared-elements"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/animation/shared-elements/customize"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/animation/shared-elements/navigation"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/compose-animation"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedTransitionScope.kt"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedContentNode.kt"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedElementEntry.kt"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/system/predictive-back"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java"
---

# Compose SharedTransitionLayout 共享元素性能

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Compose Animation：`1.11.4`
> - AndroidX 源码快照：`854220f44ea8ea80fee824a6c5a045f39bede289`
>
> `SharedTransitionLayout` 位于 Compose Animation 的 `commonMain`，匹配、Lookahead、图形层和 overlay 都由 AndroidX 实现。Android Framework 与内核没有名为 SharedTransitionLayout 的专用渲染路径；Android 17 负责它进入 HWUI 后的标准窗口绘制、BufferQueue、SurfaceFlinger 与显示流程。

这里关注共享元素过渡对组合、布局、绘制和 GPU 的影响。一般 Compose 性能方法见 [22.3 Compose 性能](./03-compose-performance.md)，普通动画成本见 [22.5 动画性能](./05-animation-performance.md) 与 [22.15 Compose 动画性能](./15-compose-animation-performance.md)。

## 1. 先校正常见误差

### 1.1 API 版本由 Compose 依赖决定

Shared Transition API 在 Compose Animation 1.7 以实验 API 形式发布，到 1.10 才稳定。当前锚点 1.11.4 已经是稳定 API，并增加了共享元素可视化调试等能力。

这套 API 没有 Android 15 / API 35 的平台门槛。只要应用使用的 Compose 版本及其 Android 最低版本满足要求，就能使用共享元素。Android 15 在这里的特殊意义主要来自 Predictive Back 默认启用，不是 SharedTransitionLayout 的引入版本。

### 1.2 Lookahead pass 不会自动生成第二次 GPU 渲染

`SharedTransitionScope` 内部使用 `LookaheadScope`。Lookahead pass 计算目标尺寸和目标坐标，approach pass 根据动画中的 bounds 测量或放置节点。它们是布局阶段的不同 pass。

一帧仍按 Compose 的布局结果进入绘制。Lookahead 增加的是目标布局计算；是否多次测量、是否记录额外图形层、是否绘制进入和退出内容，要看 modifier 和 resize mode。把 Lookahead 概括成“两次 GPU 绘制”会把 CPU 布局和 GPU 工作混为一谈。

### 1.3 sharedElement 不复用位图

Compose 1.11.4 为共享内容创建 `GraphicsLayer`，在 draw 阶段通过 `layer.record { drawContent() }` 记录内容，再在原位置或 SharedTransition overlay 中 `drawLayer()`。这是 Compose 图形层，不是把源 Composable 截成 Bitmap 后交给目标端复用。

图片内容是否复用同一个解码结果，由 Coil、Glide 或业务缓存决定。共享元素 key 只负责过渡匹配，不能代替图片缓存 key。

### 1.4 overlay 不会创建独立 SurfaceFlinger layer

SharedTransition overlay 是 `SharedTransitionScope` 根节点 draw pass 内的绘制区域。共享内容仍进入同一个 App Window buffer，SurfaceFlinger 通常只看到宿主窗口 layer。

共享元素可以增加应用侧的图形层记录、裁剪、缩放、透明混合和过绘制，进而推迟窗口 buffer 完成时间；它不会因为进入 Compose overlay 就直接增加 HWC 要合成的窗口 layer 数量。

按生产者/结果位置模型，App 内部的 GPU 图形层或离屏中间结果仍由宿主窗口消费，只有独立提交给 `SurfaceControl` 的 buffer 才会自然对应独立 SurfaceFlinger layer。BufferQueue 的 slot、GraphicBuffer 复用与 SurfaceFlinger 生产者/消费者模型见 [2.13 图形缓冲区管理](../../part1-fundamentals/ch02-rendering/13-buffer-queue.md)。

### 1.5 没有“最多五个元素”的平台阈值

源码没有 `≤5` 的限制或推荐值。一个简单图标和一个包含大图、模糊、阴影的卡片，成本差距远大于元素数量本身。活跃数量应由内容复杂度、屏幕覆盖面积、resize mode、设备 GPU 和目标刷新率共同决定。

## 2. API 架构：scope、可见性与 key

`SharedTransitionLayout` 做两件事：

1. 创建 `SharedTransitionScope`，集中管理 key 匹配、bounds 动画和 transition 活跃状态；
2. 创建一个 Box 布局，并在根 modifier 中取得普通与 Lookahead 坐标，同时提供 overlay 绘制入口。

Compose 1.11.4 还提供 `SharedTransitionScope { modifier -> ... }` 这个 Composable 入口。它不额外创建 Box，但调用方必须把回调给出的 modifier 放到最上层子节点；该节点还要适合作为 overlay 的最高绘制根。大多数页面使用 `SharedTransitionLayout` 更容易保持正确的坐标和 z-order。

### 2.1 AnimatedVisibilityScope 告诉系统谁在进入

`sharedElement()` 和 `sharedBounds()` 通常接收 `AnimatedVisibilityScope`。这个 scope 来自：

- `AnimatedContent`
- `AnimatedVisibility`
- Navigation 2 的 destination content
- Navigation 3 的 `LocalNavAnimatedContentScope`

SharedTransitionScope 根据 visibility transition 判断相同 key 的哪一端正在变为可见，并用该端的 Lookahead bounds 作为目标。只创建相同 key、却没有正确的可见性 scope，系统无法稳定确定进入端。

### 2.2 key 是匹配身份，不是重组开关

`rememberSharedContentState(key)` 在 1.11.4 中通过 `remember(key)` 保存 `SharedContentState`。列表和详情页应从同一个业务 id 派生相同 key，例如 `article-image:42`。

Compose 的 `key()` 可以在组合结构移动时保存身份，但不会自动缩小重组范围。减少重组应从稳定参数、延后状态读取、避免每帧在 Composition 中读取动画值等方面处理。

相同 key 通常应同时存在一个退出端和一个进入端。快速连续导航可能短暂产生多个 entry；源码会从可见 entry 中选择目标。若同 key 出现多个“正在进入”的内容，结果就不再明确。

## 3. 一套可维护的基本写法

下面的示例让卡片容器使用 `sharedBounds()`，其中视觉内容相同的图片使用 `sharedElement()`。列表和详情端必须传入相同的业务 id。

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

`sharedBounds()` 放在尺寸 modifier 前面，让它能用动画 bounds 约束后续内容；图片两端内容相同，因此使用 `sharedElement()`。示例省略了列表与详情周边布局，生产代码还要让图片请求使用一致的内存缓存 key，避免目标端重新解码后产生内容跳变。

## 4. Lookahead、approach 与每帧成本

### 4.1 Lookahead 负责取得目标

`SharedBoundsNode.measure()` 在 Lookahead pass 测量 child，placement 完成后记录目标尺寸和目标位置。坐标相对 SharedTransitionScope 根节点，而不是相对整个 window。

这带来两个边界：

- SharedTransitionLayout 自身在窗口中移动时，目标坐标也随它移动；
- 滚动容器属于 motion frame of reference，源码会区分结构位置与滚动位移，连续滚动仍可能增加 placement 工作。

`skipToLookaheadPosition()` 可以让节点在 transition 中使用目标位置，但父布局频繁移动时会增加 placement pass 成本。它适合解决明确的目标位置问题，不应普遍加在每个共享节点上。

### 4.2 approach 决定重测还是缩放

`sharedElement()` 的 child 会使用动画 bounds 生成的固定 constraints 重新测量和布局。这与 `RemeasureToBounds` 的成本特征相近：bounds 尺寸每帧变化时，child 可能每帧 measure/layout。

`sharedBounds()` 提供两种 resize mode：

| resize mode | 1.11.4 行为 | 适合内容 | 主要成本 |
| --- | --- | --- | --- |
| `scaleToBounds()` | 用 Lookahead constraints 得到稳定目标布局，transition 中用缩放适配动画 bounds | Text、不能频繁响应 constraints 的复杂布局 | 图形缩放与可能的裁剪，避免每帧重排 child |
| `RemeasureToBounds` | 用动画 bounds 的固定 constraints 重新测量 child | 背景、不同宽高比图片、能便宜响应尺寸变化的布局 | 动画期间可能每帧 measure/layout |

Text 在宽度变化时可能换行。对 Text 使用 `RemeasureToBounds`，字符布局和父子尺寸可能每帧改变；官方文档因此优先建议 `scaleToBounds()`。如果图片需要在变化的宽高比中持续改变裁剪结果，`RemeasureToBounds` 可能更符合视觉要求，但要测量 CPU 成本。

### 4.3 placeholder 决定父布局是否跟随

默认 `PlaceholderSize.ContentSize` 让退出端向父布局报告初始内容尺寸，让进入端报告 Lookahead 目标尺寸，父布局不会跟着每个动画 bounds 改变。

`PlaceholderSize.AnimatedSize` 会把动画尺寸报告给父布局。它能实现周边内容随共享元素移动的效果，也可能让更大的父子树每帧重新布局。除非交互明确需要这种联动，保留默认值通常更稳定。

## 5. sharedElement 与 sharedBounds 的性能边界

两者的选择依据是视觉内容是否相同，不是初始尺寸是否相等。

| 维度 | `sharedElement()` | `sharedBounds()` |
| --- | --- | --- |
| 内容关系 | 两端应是相同视觉内容 | 两端内容可以不同，只共享容器 bounds |
| transition 中的内容 | 只绘制正在进入的 target 内容 | 进入和退出内容通过 enter/exit transition 共存 |
| child 尺寸处理 | 按动画 bounds 重测、重排 | 默认 `scaleToBounds()`，可选每帧重测 |
| 常见用途 | hero image、相同 icon、movable content | 卡片到详情、Text 样式变化、container transform |
| 透明混合 | 通常只有 target 内容 | 默认 fadeIn/fadeOut 可能同时混合两端 |

`sharedBounds()` 可能保留两棵内容子树并同时绘制，alpha 混合区域较大时 GPU 成本会上升。`sharedElement()` 只绘制目标内容，但它仍有每帧 constraints 变化和 GraphicsLayer 记录成本。没有一条规则能保证某个 modifier 在所有内容上更快。

两者也没有固有的重组范围差异。重组来自各自内容读取的 Compose State；sharedBounds 的进入和退出内容同时存活，因而可能有更多活跃 Composition，但具体范围由调用方的状态结构决定。

## 6. GraphicsLayer、overlay 与裁剪

### 6.1 每个共享 entry 都持有 GraphicsLayer

`SharedBoundsNode.onAttach()` 调用 `createGraphicsLayer()`，draw 时把 child 内容记录进 layer。节点 detach 时调用 `releaseGraphicsLayer()`。

这层资源服务于在原位置与 overlay 之间移动绘制结果。它不等于固定大小的 Bitmap 缓存，也不能按 `width × height × 4` 直接推导其全部内存。RenderNode、display list、离屏纹理和 GPU backing 的使用取决于效果与渲染后端。

应用无需在 transition 完成时手工“清 layer”。节点离开 Composition 后会释放。若使用 caller-managed visibility 把不可见节点长期留在树中，节点和 layer 也会继续存在；官方文档建议在 `isTransitionActive == false` 后移除不可见端。

### 6.2 overlay 会改变父级效果边界

默认 transition 中，共享内容在 scope overlay 里绘制，避免被原父节点的 clip、alpha 或 scale 影响。代价是原父节点的这些效果也不再自动作用于共享内容。

需要圆角或裁剪时，应根据语义选择：

- 把 `clip()` 放在 `sharedElement()` / `sharedBounds()` 后面，让它成为 layer 内容的一部分；
- 使用 `clipInOverlayDuringTransition` 提供 overlay 坐标系中的 clip path；
- 嵌套 sharedBounds 时使用父级 clip；
- 只有父级没有 clip、fade、scale 等影响时，才考虑 `renderInOverlayDuringTransition = false`。

`zIndexInOverlay` 只控制 scope overlay 内的顺序。Compose 1.11.4 在 draw 前按 zIndex 排序 renderer；活跃 renderer 多时，这部分排序和逐个 drawLayer 也会增加 CPU/GPU 工作。

### 6.3 modifier 顺序会改变目标 bounds

共享 modifier 前面的尺寸与 padding 会参与确定初始和目标 bounds；后面的 modifier 接收共享节点给出的动画 constraints。列表端与详情端的顺序不一致，常见结果是位置或尺寸在开始帧跳变。

`requiredSize()` 还会覆盖约束，放置位置不同会让父布局观察到不同尺寸。遇到跳变时，应先比较两端完整 modifier 链，再调整动画参数。

## 7. 常见性能风险与对应处理

### 7.1 在 Composition 中读取每帧状态

BoundsAnimation 的主要状态在 layout/draw 阶段读取，不要求业务每帧重组。若业务把 transition progress 读进大范围 Composable，再据此构造颜色、尺寸、图片请求或列表，就会把本可在布局或绘制阶段完成的更新扩大到 Composition。

适合放在 `graphicsLayer {}`、`drawWithContent {}` 或 layout lambda 中的值，应尽量延后读取。需要重组时，用 Layout Inspector 的 recomposition count 确认范围，不要把所有动画帧都称为“重组风暴”。

### 7.2 重复添加 graphicsLayer

共享 modifier 已经维护内部 GraphicsLayer。业务再为同一节点增加多个 `graphicsLayer()`、模糊、阴影、alpha 或离屏 compositing，可能引入更多 render pass 和中间纹理。

保留有明确视觉用途的层，并在 Perfetto/GPU 工具中验证。删除一个无作用的 layer 有价值；把所有 graphicsLayer 视为错误同样不准确，因为某些属性动画正适合在 layer 上更新。

### 7.3 大面积 alpha 与 overdraw

sharedBounds 默认同时显示进入和退出内容，并用 fadeIn/fadeOut 过渡。两张全屏图或复杂列表在较长时间内重叠，会产生明显 fill rate 和带宽压力。

可以缩小共享容器范围、减少同时变化的背景层、调整 enter/exit，或把静态不透明背景放在共享区域外。优化依据是覆盖面积和 GPU duration，不是共享 key 数量。

### 7.4 transition 与列表滚动同时进行

列表还在惯性滚动时启动共享过渡，会同时发生 Lazy layout、图片请求、Lookahead、approach placement 和窗口绘制。源码支持 motion frame of reference，但支持滚动坐标并不会消除这批工作。

产品交互允许时，可以停止列表 fling 后再切换详情；必须并行时，要保证 item key 稳定、图片已命中缓存，并减少 `AnimatedSize`、`RemeasureToBounds` 和大面积渐变的组合。

### 7.5 动画 spec 不是主要 CPU 热点

默认 bounds transform 使用中低 stiffness 的 spring。spring 的结束时间由收敛决定，tween 的 duration 固定；两者每帧求值通常远小于复杂内容的重测、文字排版和 GPU 绘制。

选择 spec 时优先满足交互与中断连续性，再观察它让高成本内容活跃了多少帧。缩短 duration 可能减少总工作，也可能提高每帧变化幅度和视觉突兀感，不能只按“spring 更耗性能”判断。

## 8. LazyList 中的共享元素

LazyList 的难点是 source item 可能在 transition 结束前离开 Composition。可靠实现需要同时满足：

- `items(key = ...)` 使用稳定业务 id；
- `rememberSharedContentState()` 的 key 与详情端一致；
- source 与 target 在同一个 SharedTransitionScope；
- target 被组合、测量并放置后，系统才能获得有效 Lookahead bounds；
- source 图片和 target 图片使用一致的图片内存缓存 key；
- caller-managed visibility 的不可见节点在 transition 结束后移除。

若点击后立刻替换整个列表树，source entry 可能在 target 获得 bounds 前 detach。`AnimatedContent`、Navigation 或官方 AnimatedVisibility 示例会让进入和退出内容在过渡窗口内同时存在，优先使用这些可见性容器。

预取应优先准备数据、图片和目标页面不可避免的昂贵资源。提前组合整个详情树会延长对象生命周期，也可能让未展示页面参与状态观察；只有 trace 证明首次组合是瓶颈时，再设计受控 precompose。

## 9. Predictive Back

SharedTransitionLayout 自身不读取系统 back progress。Navigation 或调用方负责把手势进度送入 destination transition，共享元素再从对应 `AnimatedVisibilityScope` 获得进入/退出状态和目标。

官方当前能力边界是：

- Navigation 3 各版本支持 Predictive Back；
- Navigation Compose 2 使用 2.8.0 或更高版本；
- Android 15 及以上默认启用 predictive back animation；
- Android 14 设备需要开发者选项；target Android 14 及以下的应用还需按官方说明配置 `enableOnBackInvokedCallback`。

Android 17 沿用这套标准机制，没有一个独立的“SharedTransitionLayout 帧同步”平台 API。手势事件、Compose transition、Choreographer 帧、HWUI 提交仍需在 Perfetto 中按同一 FrameTimeline 检查。

### 9.1 BackHandler 与 PredictiveBackHandler

`BackHandler` 适合处理一次完成的 back 动作，不提供连续 progress。需要自定义手势驱动动画时使用 `PredictiveBackHandler`；使用 Navigation 内建 Predictive Back 时，不要再添加会抢先消费同一手势的 handler。

自定义 progress 流应更新专门的动画状态，避免每个事件重建导航图、重发图片请求或重组整页。取消手势时要恢复初始状态，完成手势后再提交返回栈变化。

手势驱动 transition 可以随时暂停、反向或取消，比固定 tween 更容易暴露 source detach、重复 key 和目标尚未放置的问题。测试必须覆盖完成、取消、快速往返和滚动中返回。

## 10. Perfetto、Layout Inspector 与可视化调试

### 10.1 源码没有专用 SharedTransition trace track

Compose 1.11.4 的 SharedTransition 实现没有为每个 key 写入固定的 Perfetto slice。Perfetto 中应组合观察：

- UI Thread 上的 Choreographer、Compose recomposition、measure/layout 与 draw；
- RenderThread 的 `DrawFrame`、资源更新和命令提交；
- FrameTimeline expected/actual frame；
- GPU completion 与 GPU duration；
- 图片解码、列表预取和其他并行工作；
- 应用为导航开始、target 首次放置和 transition 结束增加的自定义 trace。

看到 approach 期间 layout 变长时，再用代码配置确认是 `sharedElement()`、`RemeasureToBounds`、`AnimatedSize`，还是业务父布局失效。看到 GPU duration 上升时，检查覆盖面积、alpha、clip、阴影和额外 graphicsLayer。

### 10.2 Layout Inspector 的适用范围

Compose Layout Inspector 可以检查：

- 两端 key 是否一致；
- modifier 顺序；
- source 与 target 是否同时在树中；
- recomposition count 与 skip count；
- 不可见 caller-managed 节点是否长期保留。

它不能给出 GPU pass、GraphicsLayer backing 或 SurfaceFlinger composition type。Inspector 本身也会影响运行，正式性能采样应关闭 Inspector 后用 release/profileable 构建复测。

### 10.3 Compose 1.11 的视觉调试

Compose Animation 1.11 增加实验性的 Lookahead animation visual debugging，可以显示目标 bounds、运动轨迹、匹配数量、未匹配元素和 transition 活跃状态。

下面的包装仅用于 debug 构建，帮助定位 key 匹配和目标位置问题。

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

可视化会给整个 content 子树增加调试绘制，不能与正式帧耗时放在同一组结果中。先用它排除坐标和匹配错误，再关闭后录制 Perfetto。

### 10.4 建立对照实验

共享过渡评测至少保留三组相同导航：

1. 只有页面 enter/exit，没有共享 modifier；
2. 只启用一个核心 sharedElement；
3. 启用完整 sharedElement/sharedBounds 集合。

三组都要保持相同数据、图片缓存状态、构建类型、动画时长和设备温度。比较 frame deadline miss、UI Thread layout、RenderThread、GPU duration 和内存峰值，才能确认增加的成本来自哪个层级。

## 11. 高级配置的安全边界

### 11.1 BoundsTransform 只定义 Rect 动画 spec

`BoundsTransform.createAnimationSpec(initialBounds, targetBounds)` 返回 `FiniteAnimationSpec<Rect>`。它能改变 timing、spring 或 keyframes，但 API 本身没有“沿任意几何 Path 移动”的参数。

需要曲线路径、旋转或形变时，可以在共享 bounds 之外增加受控的 graphicsLayer/draw modifier，或使用 caller-managed visibility 自己驱动视觉属性。自定义效果仍要让语义节点、点击区域和无障碍焦点在 transition 后回到目标布局。

### 11.2 SharedContentConfig 用于动态启停

1.11.4 的 `rememberSharedContentState(key, config)` 允许通过 `SharedContentConfig.isEnabled` 动态决定某个 key 是否参与匹配。导航方向、减少动态效果设置或设备降级策略适合放在这里。

启停状态在 transition 中变化时要定义清楚：立即取消、保持当前动画，还是等下一次导航生效。默认配置会在 in-flight animation 中保持 enabled，减少半途切换造成的视觉断点。

### 11.3 多步骤 transition

多步骤场景应为每个持续身份使用稳定 key，并让每一步只有明确的进入端。复用一个 key 同时表示多个视觉对象，会让匹配状态机面对多个候选。

如果步骤需要不同内容连续变形，可以用外层 sharedBounds 保持容器 continuity，内部按步骤使用独立 sharedElement；同时控制 overlay zIndex 和父 clip，避免嵌套层互相遮挡。

## 12. View 系统迁移边界

Compose Shared Transition 只在同一个 SharedTransitionScope 内匹配。目前官方明确不支持 View 与 Compose 共享元素互操作，包括 `AndroidView`，以及跨独立 window 的 `Dialog`、`ModalBottomSheet` 等包装。

它也不能直接替代 Activity 之间由 `ActivityOptions.makeSceneTransitionAnimation()` 和 Window Transition 管理的 platform shared element。两者的坐标、生命周期、snapshot/overlay 和 window 边界不同。

迁移可以分三种情况：

| 当前架构 | 建议路径 |
| --- | --- |
| Fragment destination 内逐页迁移 Compose | 保留 Fragment Navigation 和 View/Window transition 边界；不要尝试 View 与 Compose key 匹配 |
| 同一 Compose NavHost 内的 destination | 用 SharedTransitionLayout 包住 NavHost，传递 scope 与 destination 的 AnimatedContentScope |
| 已全部迁移到 Compose Navigation | 在 Navigation 2 或 Navigation 3 官方共享元素接口上配置，并同时验证 Predictive Back |

混合期若视觉上必须连续，可以用普通 enter/exit、crossfade 或业务自定义 snapshot 方案过渡，但要明确它不具备 SharedTransitionScope 的自动 key 匹配。

## 13. 评审清单

- Compose 版本是否至少使用稳定 Shared Transition API；1.7 不能写成稳定版本；
- SharedTransitionLayout 是否位于 source 与 target 的共同祖先；
- 两端是否使用相同且稳定的业务 key；
- `sharedElement()` 是否用于相同视觉内容，`sharedBounds()` 是否用于容器变化；
- Text 是否优先评估 `scaleToBounds()`；
- 是否误把 Lookahead pass 计作第二次 GPU 渲染；
- 是否误把 GraphicsLayer 写成 Bitmap 缓存；
- overlay clip、父 alpha、scale 与 zIndex 是否符合预期；
- modifier 顺序是否在两端保持一致；
- `AnimatedSize` 或 `RemeasureToBounds` 是否扩大每帧布局范围；
- 大面积 fade、模糊、阴影和额外 graphicsLayer 是否同时存在；
- LazyList source 是否在 target 获得 Lookahead bounds 前被移除；
- 图片缓存 key 是否与 shared content key 协调；
- Predictive Back 是否由 Navigation 或 `PredictiveBackHandler` 提供 progress；
- Layout Inspector 与视觉调试是否只用于定位，正式采样是否关闭；
- Perfetto 是否同时查看 UI Thread、RenderThread、FrameTimeline 与 GPU；
- 是否把 Compose overlay 误判为独立 SurfaceFlinger layer。

## 14. 结论

SharedTransitionLayout 的性能成本主要来自额外 Lookahead/approach 布局、共享 entry 的 GraphicsLayer、overlay 绘制，以及进入和退出内容可能同时存在。SurfaceFlinger 通常只处理同一个 App Window，瓶颈更多出现在应用 UI Thread、RenderThread 和 GPU。

`sharedElement()` 与 `sharedBounds()` 的选择应从内容关系出发。相同视觉内容用 sharedElement；容器连续但内容变化时用 sharedBounds，再在 `scaleToBounds()` 与 `RemeasureToBounds` 之间选择。元素数量、spring 或 key() 都不是脱离内容就能判断的性能指标。

Android 17 没有 SharedTransitionLayout 专属管线。严谨的分析方法是：先用可视化与 Layout Inspector确认 key、bounds 和 modifier，再在关闭调试工具后用 Perfetto 对比 layout、draw、RenderThread、GPU 与 FrameTimeline。

## 参考资料

- [Compose Shared element transitions](https://developer.android.com/develop/ui/compose/animation/shared-elements)：scope、modifier 顺序、overlay、限制与 Lazy 示例。
- [Customize shared element transitions](https://developer.android.com/develop/ui/compose/animation/shared-elements/customize)：resize mode、clip、zIndex 与动态启停。
- [Navigation with shared elements](https://developer.android.com/develop/ui/compose/animation/shared-elements/navigation)：Navigation 2/3 与 Predictive Back 集成。
- [Compose Animation release notes](https://developer.android.com/jetpack/androidx/releases/compose-animation)：1.7 实验发布、1.10 稳定、1.11.4 当前版本与视觉调试。
- [`SharedTransitionScope.kt`（Compose 1.11.4 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedTransitionScope.kt)：scope、overlay、key 匹配和公开 API。
- [`SharedContentNode.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedContentNode.kt)：Lookahead/approach measure、GraphicsLayer 记录与绘制。
- [`SharedElementEntry.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedElementEntry.kt)：in-place/overlay 选择和 layer 生命周期。
- [Predictive Back for Compose](https://developer.android.com/develop/ui/compose/system/predictive-back)：系统行为、Navigation 与自定义 progress。
- [`Choreographer.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)：Android 17 应用帧起点与 FrameTimeline。
- [`ViewRootImpl.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：Compose 宿主窗口进入 HWUI 的平台入口。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线；SharedTransitionLayout 不直接依赖内核 API。
