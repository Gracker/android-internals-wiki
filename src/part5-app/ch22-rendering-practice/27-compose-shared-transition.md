---
title: "Compose SharedTransitionLayout：共享元素的渲染与性能"
chapter: "22.27"
status: finalized
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [Compose, SharedTransition, Animation, Performance, Rendering]
related_chapters: ["22.5", "22.15", "22.3", "2.1"]
last_verified: "2026-08-15"
last_verified_against: "AndroidX Compose Animation 1.12.0 源码快照 963bf914f78b389bdddef0da7f36bee19d897274；Android 17 / API 37 / android-17.0.0_r1；内核 android17-6.18-2026-06_r6；官方 Compose Shared elements 与 Predictive Back 文档"
confidence: high
pipeline_stage: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
last_draft_polish_at: "2026-08-15T05:31:12+08:00"
last_draft_polish_run_id: "20260815-053112-gracker-writing"
last_review_finalize_at: "2026-08-15T05:31:12+08:00"
last_review_finalize_run_id: "20260815-053112-gracker-writing-review"
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
    path: "android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedTransitionScope.kt"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedContentNode.kt"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/animation/animation/src/commonMain/kotlin/androidx/compose/animation/SharedElementEntry.kt"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/system/predictive-back"
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/androidx/compose/animation/animation/maven-metadata.xml"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java"
---

# Compose SharedTransitionLayout：共享元素的渲染与性能

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Compose Animation：`1.12.0`
> - AndroidX 源码快照：`963bf914f78b389bdddef0da7f36bee19d897274`
>
> `SharedTransitionLayout` 位于 Compose Animation 的 `commonMain`（Kotlin Multiplatform 的公共源码集），元素匹配、Lookahead 布局、图形层和 overlay 都由 AndroidX 实现。Android Framework 与内核没有名为 SharedTransitionLayout 的专用渲染路径；Android 17 只负责内容进入 HWUI（Android 的硬件加速 UI 渲染器）后的窗口绘制、BufferQueue、SurfaceFlinger 与显示流程。

共享元素过渡会把两个页面中代表同一对象的内容匹配起来，在页面切换时连续改变位置和尺寸。这里关注它对组合、布局、绘制和 GPU 的影响。一般 Compose 性能方法见 [22.3 Compose 性能](./03-compose-performance.md)，普通动画成本见 [22.5 动画性能](./05-animation-performance.md) 与 [22.15 Compose 动画性能](./15-compose-animation-performance.md)。

为便于对照 API 和源码，本文保留几个常用英文词：`key` 是两端内容的匹配标识；`bounds` 是包含位置与尺寸的矩形边界；`entry` 是某个 `key` 在源端或目标端的一条注册记录；`overlay` 是 `SharedTransitionScope` 根节点内用于置顶绘制的覆盖区域。这些词都指 Compose 作用域内的匹配、布局或绘制概念。

## 1. 容易混淆的五个边界

### 1.1 API 版本由 Compose 依赖决定

Shared Transition API 在 Compose Animation 1.7 以实验 API 形式发布，到 1.10 转为稳定 API。截至 2026 年 8 月 15 日，Google Maven 中最新稳定版是 1.12.0；1.13.0-alpha01 属于预览版。1.12.0 继续提供实验性的共享元素可视化调试能力。

这套 API 没有 Android 15 / API 35 的平台门槛。只要应用使用的 Compose 版本及其 Android 最低版本满足要求，就能使用共享元素。Android 15 起取消了 Predictive Back 开发者开关；应用迁移到受支持的返回 API 后可以获得对应系统动画。这与 `SharedTransitionLayout` 的引入版本无关。

### 1.2 Lookahead pass 不等于第二次 GPU 渲染

`SharedTransitionScope` 内部使用 `LookaheadScope`。这里的 pass 是布局系统对节点树的一次遍历：Lookahead pass 先计算动画结束时的尺寸和坐标，approach pass 再按当前动画 `bounds` 测量或放置节点。两者都属于布局阶段。

一帧仍按 Compose 的布局结果进入绘制。Lookahead 增加的是目标布局计算；是否多次测量、是否记录额外图形层、是否同时绘制进入端与退出端，要看 `Modifier` 和 resize mode（尺寸适配方式）。把 Lookahead 概括成“两次 GPU 绘制”，会混淆 CPU 布局与 GPU 绘制。

### 1.3 sharedElement 不复用位图

Compose 1.12.0 在需要 overlay 绘制时为共享内容创建 `GraphicsLayer`。`GraphicsLayer` 是记录绘制命令并允许复用这些命令的 Compose 图形层；实现会在 draw 阶段通过 `layer.record { drawContent() }` 记录内容，再以 `drawLayer()` 绘制。它不会把源 Composable 截成 Bitmap 后交给目标端复用。

图片内容是否复用同一个解码结果，由 Coil、Glide 等图片加载库或业务缓存决定。共享元素 `key` 只负责过渡匹配，不能代替图片内存缓存的 `key`。

### 1.4 overlay 不会创建独立 SurfaceFlinger layer

SharedTransition overlay 是 `SharedTransitionScope` 根节点 draw pass 内的绘制区域。共享内容仍进入同一个 App Window buffer（应用窗口提交的像素缓冲区），SurfaceFlinger 这个系统合成器通常只看到宿主窗口的 layer。

共享元素可能增加应用侧的图形层记录、裁剪、缩放、透明混合和过绘制，进而推迟窗口 buffer 完成时间；进入 Compose overlay 不会直接增加 HWC（Hardware Composer，硬件合成器）要合成的窗口 layer 数量。

按生产者与结果位置来判断，App 内部的 GPU 图形层或离屏中间结果仍由宿主窗口消费。只有通过 `SurfaceControl` 独立提交的 buffer，才会自然对应独立的 SurfaceFlinger layer。BufferQueue 的 slot（可循环使用的缓冲槽位）、GraphicBuffer 复用与生产者/消费者模型见 [2.13 图形缓冲区管理](../../part1-fundamentals/ch02-rendering/13-buffer-queue.md)。

### 1.5 没有“最多五个元素”的平台阈值

源码没有 `≤5` 的限制或推荐值。一个简单图标和一个包含大图、模糊、阴影的卡片，成本差距远大于元素数量本身。活跃数量应结合内容复杂度、屏幕覆盖面积、resize mode、设备 GPU 和目标刷新率评估。

## 2. API 架构：scope、可见性与 key

`scope` 是一组 API 共享的作用域；这里负责限定哪些内容可以互相匹配。源端（source）指正在退出的内容，目标端（target）指正在进入的内容。

`SharedTransitionLayout` 做两件事：

1. 创建 `SharedTransitionScope`，集中管理 `key` 匹配、`bounds` 动画和过渡是否活跃；
2. 创建一个 `Box` 布局，在根 `Modifier` 中取得当前坐标与 Lookahead 目标坐标，并提供 overlay 绘制入口。

Compose 1.12.0 还提供 `SharedTransitionScope { modifier -> ... }` 这个 Composable（可组合函数）入口。它不额外创建 `Box`，但调用方必须把回调给出的 `Modifier` 放在最上层子节点；该节点还要适合作为 overlay 的最高绘制根。大多数页面使用 `SharedTransitionLayout`，更容易保持正确坐标与 z-order（同一绘制区域中的前后顺序）。

### 2.1 AnimatedVisibilityScope 告诉系统谁在进入

`sharedElement()` 和 `sharedBounds()` 通常接收 `AnimatedVisibilityScope`，让共享过渡知道哪一端正在进入、哪一端正在退出。这个 scope 来自：

- `AnimatedContent`
- `AnimatedVisibility`
- Navigation 2 的 destination content（导航目的地内容）
- Navigation 3 的 `LocalNavAnimatedContentScope`

`SharedTransitionScope` 根据可见性过渡判断相同 `key` 的哪一端正在变为可见，并用该端的 Lookahead `bounds` 作为目标。只创建相同 `key`、却没有传入正确的可见性 scope，系统无法稳定确定进入端。

### 2.2 key 是匹配身份，不是重组开关

`rememberSharedContentState(key)` 在 1.12.0 中通过 `remember(key)` 保存 `SharedContentState`。`remember` 会让该对象跨重组保留；列表和详情页应从同一个业务 ID 派生相同 `key`，例如 `article-image:42`。

Compose 的 `key()` 可以在组合结构移动时保留节点身份，但不会自动缩小重组范围。减少重组要从稳定参数、延后状态读取、避免每帧在 Composition（Compose 生成并维护 UI 树的组合阶段）中读取动画值等方面处理。

相同 `key` 通常应同时存在一个退出 `entry` 和一个进入 `entry`。快速连续导航可能短暂产生多条记录，源码会从可见记录中选择目标。若同一个 `key` 出现多个正在进入的内容，匹配结果便不明确。

## 3. 一套可维护的基本写法

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

## 4. Lookahead、approach 与每帧成本

### 4.1 Lookahead 负责取得目标

`SharedBoundsNode.measure()` 在 Lookahead pass 测量子节点，完成放置后记录目标尺寸和位置。坐标相对 `SharedTransitionScope` 根节点，而不是相对整个 window（应用窗口）。

这带来两个边界：

- `SharedTransitionLayout` 自身在窗口中移动时，目标坐标也会随之移动；
- 滚动容器会被标记为 motion frame of reference（运动参考系），源码借此区分结构位置变化与滚动位移；连续滚动仍可能增加节点放置工作。

`skipToLookaheadPosition()` 可以让节点在过渡期间使用目标位置，但父布局频繁移动时会增加 placement pass，也就是放置阶段的重复遍历。它适合解决明确的目标位置问题，不宜普遍加在每个共享节点上。

### 4.2 approach 决定重测还是缩放

`sharedElement()` 的子节点会使用动画 `bounds` 生成的固定 constraints（布局给出的宽高限制）重新测量和布局。它与 `RemeasureToBounds` 的成本特征相近：`bounds` 尺寸逐帧变化时，子节点可能逐帧执行 measure/layout（测量与布局）。

`sharedBounds()` 提供两种 resize mode：

| resize mode | 1.12.0 行为 | 适合内容 | 主要成本 |
| --- | --- | --- | --- |
| `scaleToBounds()` | 用 Lookahead constraints 得到稳定的目标布局，过渡期间缩放到动画 `bounds` | `Text`、不适合频繁改变约束的复杂布局 | 图形缩放与可能的裁剪；子节点无需逐帧重排 |
| `RemeasureToBounds` | 用动画 `bounds` 生成的固定 constraints 重新测量子节点 | 背景、宽高比不同的图片、能低成本响应尺寸变化的布局 | 动画期间可能逐帧 measure/layout |

`Text` 在宽度变化时可能重新换行。对它使用 `RemeasureToBounds`，字符排版和父子尺寸可能逐帧改变；官方文档因此优先建议 `scaleToBounds()`。如果图片需要随宽高比持续改变裁剪结果，`RemeasureToBounds` 可能更符合视觉要求，但要实测 CPU 成本。

### 4.3 placeholder 决定父布局是否跟随

placeholder 是共享内容过渡时留在原布局中的占位区域。默认的 `PlaceholderSize.ContentSize` 让退出端向父布局报告初始内容尺寸，让进入端报告 Lookahead 目标尺寸；父布局不会跟随每一帧的动画 `bounds` 改变。

`PlaceholderSize.AnimatedSize` 会把动画尺寸报告给父布局。它能让周边内容随共享元素移动，也可能使更大的父子树逐帧重新布局。交互没有这种联动要求时，保留默认值通常更稳定。

## 5. sharedElement 与 sharedBounds 的性能边界

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

## 6. GraphicsLayer、overlay 与裁剪

### 6.1 活跃的 overlay entry 按需持有 GraphicsLayer

Compose 1.12.0 不会在 `SharedBoundsNode.onAttach()` 时立刻分配图形层。节点需要在 overlay 中绘制时，才调用 `createGraphicsLayer()`，并在 draw 阶段把子节点的绘制命令记录进去；退出 overlay、节点 detach（从树中分离）或节点 reset（被复用）时会释放该层。

这层资源用于在原位置与 overlay 之间移动绘制结果。它不等于固定大小的 Bitmap 缓存，也不能按 `width × height × 4` 推导全部内存。RenderNode（HWUI 的可记录绘制节点）、display list（录制后的绘制命令列表）、离屏纹理和 GPU backing（GPU 侧实际存储）是否出现，取决于图形效果与渲染后端。

应用无需在过渡结束时手工清理图形层。实现会在不再需要 overlay 或节点离开 Composition 时释放它。若使用 caller-managed visibility（由调用方直接传入可见状态的 API），不可见节点可能继续留在树中；官方文档建议在 `isTransitionActive == false` 后移除不可见端。

### 6.2 overlay 会改变父级效果边界

默认情况下，共享内容在 scope overlay 里绘制，不再受原父节点的 clip（裁剪）、alpha 或 scale（缩放）影响。视觉上仍需要这些效果时，要把它们明确应用到共享节点或 overlay。

需要圆角或裁剪时，应根据语义选择：

- 把 `clip()` 放在 `sharedElement()` / `sharedBounds()` 后，让裁剪成为图形层内容的一部分；
- 使用 `clipInOverlayDuringTransition` 提供 overlay 坐标系中的 clip path（矢量裁剪路径）；
- 嵌套 `sharedBounds()` 时复用父级裁剪；
- 父级没有裁剪、淡入淡出或缩放等影响时，再考虑 `renderInOverlayDuringTransition = false`。

`zIndexInOverlay` 只控制 scope overlay 内的顺序。Compose 1.12.0 在绘制前按 zIndex 排序 renderer（负责绘制某个 `entry` 的对象）；活跃 renderer 较多时，排序与逐个 `drawLayer()` 也会增加 CPU/GPU 工作。

### 6.3 modifier 顺序会改变目标 bounds

共享 `Modifier` 前的尺寸与 padding（内边距）会参与确定初始和目标 `bounds`；后续 `Modifier` 接收共享节点给出的动画 constraints。列表端与详情端顺序不一致时，位置或尺寸容易在起始帧跳变。

`requiredSize()` 还会覆盖约束，放置位置不同会让父布局观察到不同尺寸。遇到跳变时，应比较两端完整的 `Modifier` 链，再调整动画参数。

## 7. 常见性能风险与对应处理

### 7.1 在 Composition 中读取每帧状态

`BoundsAnimation` 的主要状态在 layout/draw 阶段读取，不要求业务逐帧重组。若业务在大范围 Composable 中读取 transition progress（通常为 0 到 1 的过渡进度），再据此构造颜色、尺寸、图片请求或列表，就会把本可在布局或绘制阶段完成的更新扩大到 Composition。

适合放在 `graphicsLayer {}`、`drawWithContent {}` 或 layout lambda（布局回调）中的值，应延后到对应阶段读取。确需重组时，用 Layout Inspector 的 recomposition count（重组次数）确认范围，不要把所有动画帧都称为“重组风暴”。

### 7.2 重复添加 graphicsLayer

共享 `Modifier` 已经按需维护内部 `GraphicsLayer`。业务再为同一节点增加多个 `graphicsLayer()`、模糊、阴影、alpha 或离屏 compositing（先画到中间缓冲再合成），可能引入更多 render pass（一次渲染任务）和中间纹理。

只保留有明确视觉用途的层，并在 Perfetto/GPU 工具中验证。无作用的 layer 可以删除；有些属性动画适合在 layer 上更新，因此不能把所有 `graphicsLayer()` 都视为问题。

### 7.3 大面积 alpha 与 overdraw

`sharedBounds()` 默认同时显示进入和退出内容，并用 `fadeIn`/`fadeOut` 过渡。两张全屏图或复杂列表长时间重叠，会产生明显的 fill rate（GPU 单位时间处理像素的能力）和显存带宽压力，也会增加 overdraw（同一像素在一帧内被重复绘制）。

可以缩小共享容器范围、减少同时变化的背景层、调整进入/退出动画，或把静态不透明背景放在共享区域外。优化依据是覆盖面积和 GPU duration（GPU 完成该帧所需时间），不是共享 `key` 的数量。

### 7.4 共享过渡与列表滚动同时进行

列表仍在惯性滚动时启动共享过渡，会同时发生 Lazy layout（只布局可见项及预取项）、图片请求、Lookahead、approach placement 和窗口绘制。motion frame of reference 能处理滚动坐标，却不会消除这些工作。

产品交互允许时，可以结束 fling（松手后的惯性滚动）再切换详情；需要并行时，要保证 item key（列表项身份）稳定、图片已命中缓存，并减少 `AnimatedSize`、`RemeasureToBounds` 和大面积渐变的叠加。

### 7.5 动画 spec 的求值成本通常较小

默认 bounds transform 使用中低 stiffness（弹簧刚度）的 spring（弹簧动画）。spring 的结束时间由收敛条件决定，tween（按时间插值的动画）的 duration 固定；两者逐帧求值的成本通常远小于复杂内容重测、文字排版和 GPU 绘制。

选择 animation spec（动画规格）时，应先满足交互与中断连续性，再观察它让高成本内容活跃了多少帧。缩短 duration（持续时间）可能减少总工作，也可能增大逐帧变化幅度并造成视觉突兀，不能只按“spring 更耗性能”判断。

## 8. LazyList 中的共享元素

`LazyList` 的难点是源列表项可能在过渡结束前离开 Composition。可靠实现需要同时满足：

- `items(key = ...)` 使用稳定的业务 ID；
- `rememberSharedContentState()` 的 `key` 与详情端一致；
- 源端与目标端位于同一个 `SharedTransitionScope`；
- 目标端完成组合、测量和放置后，系统才能获得有效的 Lookahead `bounds`；
- 两端图片使用一致的图片内存缓存 `key`；
- 使用 caller-managed visibility 时，在过渡结束后移除不可见节点。

若点击后立刻替换整个列表树，源 `entry` 可能在目标端获得 `bounds` 前 detach。`AnimatedContent`、Navigation 或官方 `AnimatedVisibility` 示例会让进入和退出内容在过渡窗口内同时存在，适合优先作为可见性容器。

预取应准备数据、图片和目标页面不可避免的昂贵资源。提前组合整个详情树会延长对象生命周期，也可能让未展示页面参与状态观察；只有 trace（按时间记录系统与应用事件的性能轨迹）证明首次组合是瓶颈时，再设计受控的 precompose（预先组合）。

## 9. Predictive Back

Predictive Back（预测性返回）让用户在返回手势完成前预览目的地。`SharedTransitionLayout` 自身不读取系统 back progress（0 到 1 的返回手势进度）；Navigation 或调用方负责把进度送入目的地的 transition，共享元素再从对应的 `AnimatedVisibilityScope` 获得进入、退出状态和目标。

截至 2026 年 8 月，官方给出的集成边界是：

- Navigation 3 各版本支持 Predictive Back；
- Navigation Compose 2 使用 2.8.0 或更高版本；
- Android 15 及以上不再提供 Predictive Back 开发者开关；应用仍需使用受支持的返回 API。`targetSdk >= 35` 时无需把 `enableOnBackInvokedCallback` 设为 `true`，`targetSdk <= 34` 时仍需显式开启；
- Android 14 设备还要在开发者选项中启用 Predictive Back；
- 应用运行在 Android 16 及以上且 `targetSdk >= 36` 时，系统预测性返回动画默认启用；迁移期间仍可按官方说明临时选择退出。

Android 17 沿用这套标准机制，没有独立的 SharedTransitionLayout 帧同步平台 API。手势事件、Compose 过渡状态、Choreographer（主线程帧回调调度器）与 HWUI 提交，仍要在 Perfetto 中按同一 FrameTimeline（把计划帧与实际帧关联起来的时间线）检查。

### 9.1 BackHandler 与 PredictiveBackHandler

`BackHandler` 适合处理一次完成的返回动作，不提供连续 progress。需要自定义手势驱动动画时使用 `PredictiveBackHandler`，它提供一串 `BackEventCompat` 事件及 0 到 1 的进度；使用 Navigation 内建 Predictive Back 时，不要再添加会抢先消费同一手势的 handler（回调处理器）。

自定义进度流应更新专门的动画状态，避免每个事件都重建导航图、重发图片请求或重组整页。取消手势时要恢复初始状态，手势完成后再提交返回栈变化。

手势驱动的过渡可以暂停、反向或取消，比固定 tween 更容易暴露源端 detach、重复 `key` 和目标端尚未放置的问题。测试应覆盖完成、取消、快速往返和滚动中返回。

## 10. Perfetto、Layout Inspector 与可视化调试

### 10.1 源码没有专用 SharedTransition trace 轨道

Compose 1.12.0 的 `SharedTransitionScope.kt`、`SharedContentNode.kt` 与 `SharedElementEntry.kt` 没有为每个 `key` 写入固定的 Perfetto slice。Perfetto 是 Android 的系统级性能追踪工具；track 是一条事件轨道，slice 是带起止时间的区间事件。分析时应组合观察：

- UI Thread（应用主线程）上的 Choreographer、Compose recomposition、measure/layout 与 draw；
- RenderThread（HWUI 的渲染线程）的 `DrawFrame`、资源更新和命令提交；
- FrameTimeline 的 expected/actual frame（计划帧与实际帧）；
- GPU completion（GPU 完成时刻）与 GPU duration（GPU 执行时长）；
- 图片解码、列表预取和其他并行工作；
- 应用为导航开始、目标端首次放置和过渡结束增加的自定义 trace。

如果 approach 阶段的布局耗时变长，再结合代码配置确认原因是 `sharedElement()`、`RemeasureToBounds`、`AnimatedSize`，还是业务父布局反复失效。GPU duration 上升时，检查覆盖面积、alpha、裁剪、阴影和额外的 `graphicsLayer()`。

### 10.2 Layout Inspector 的适用范围

Compose Layout Inspector 可以检查：

- 两端 `key` 是否一致；
- `Modifier` 顺序；
- 源端与目标端是否同时在树中；
- recomposition count 与 skip count（重组次数与跳过重组次数）；
- 不可见的 caller-managed 节点是否长期保留。

它不能给出 GPU 渲染 pass 数量、`GraphicsLayer` backing 或 SurfaceFlinger composition type（合成类型）。Inspector 本身也会影响运行，正式性能采样应关闭 Inspector，再用 release/profileable（发布版或允许性能分析的构建）复测。

### 10.3 Compose 1.12.0 的视觉调试

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

### 10.4 建立对照实验

共享过渡评测至少保留三组相同导航：

1. 只有页面进入/退出动画，没有共享 `Modifier`；
2. 只启用一个 `sharedElement()`；
3. 启用完整的 `sharedElement()` / `sharedBounds()` 集合。

三组都要保持相同数据、图片缓存状态、构建类型、动画时长和设备温度。比较 frame deadline miss（未在截止时间内完成的帧）、UI Thread layout、RenderThread、GPU duration 和内存峰值，才能判断新增成本来自哪个层级。

## 11. 高级配置的安全边界

### 11.1 BoundsTransform 只定义 Rect 动画 spec

`BoundsTransform.createAnimationSpec(initialBounds, targetBounds)` 返回 `FiniteAnimationSpec<Rect>`。它能改变 timing（时间控制）、spring 或 keyframes（关键帧），但 API 本身没有沿任意几何 `Path` 移动的参数。

需要曲线路径、旋转或形变时，可以在共享 `bounds` 之外增加受控的 `graphicsLayer` 或绘制类 `Modifier`，也可以使用 caller-managed visibility 驱动视觉属性。过渡结束后，语义节点、点击区域和无障碍焦点都应回到目标布局。

### 11.2 SharedContentConfig 用于动态启停

1.12.0 的 `rememberSharedContentState(key, config)` 允许通过 `SharedContentConfig` 中的 `SharedContentState.isEnabled`，动态决定某个 `key` 是否参与匹配。导航方向、系统“减少动态效果”偏好或设备降级策略适合放在这里。

启停状态在过渡中变化时要定义清楚：立即取消、保持现有动画，还是等下一次导航生效。默认的 `shouldKeepEnabledForOngoingAnimation` 为 `true`，因此正在进行的动画会完成，禁用结果随后生效。若目标 `entry` 在动画中被移除，还可以通过 `alternativeTargetBoundsInTransitionScopeAfterRemoval` 提供替代终点；默认行为是取消这一组共享过渡。

### 11.3 多步骤过渡

多步骤场景应为每个持续身份使用稳定 `key`，并让每一步只有一个明确的进入端。复用一个 `key` 同时表示多个视觉对象，会让匹配状态机面对多个候选。

如果步骤需要让不同内容连续变形，可以用外层 `sharedBounds()` 保持容器连续性，内部按步骤使用独立的 `sharedElement()`；同时控制 overlay zIndex 与父级裁剪，避免嵌套层互相遮挡。

## 12. View 系统迁移边界

Compose Shared Transition 只在同一个 `SharedTransitionScope` 内匹配。目前官方明确不支持 View 与 Compose 共享元素互操作，包括 `AndroidView`，以及跨独立 window 的 `Dialog`、`ModalBottomSheet` 等容器。

它也不能直接替代 Activity 之间由 `ActivityOptions.makeSceneTransitionAnimation()` 和 Window Transition 管理的平台共享元素。两者的坐标、生命周期、snapshot（过渡使用的内容快照）、overlay 和 window 边界不同。

迁移可以分三种情况：

| 当前架构 | 建议路径 |
| --- | --- |
| Fragment 目的地中逐页迁移至 Compose | 保留 Fragment Navigation 和 View/Window transition 边界；不要尝试用 `key` 匹配 View 与 Compose 内容 |
| 同一 Compose `NavHost` 内的目的地 | 用 `SharedTransitionLayout` 包住 `NavHost`，传递 `SharedTransitionScope` 与目的地的 `AnimatedContentScope` |
| 已全部迁移到 Compose Navigation | 在 Navigation 2 或 Navigation 3 官方共享元素接口上配置，并同时验证 Predictive Back |

混合期若视觉上需要连续，可以用普通 enter/exit、crossfade（交叉淡入淡出）或业务自定义 snapshot 方案，但这些方案不具备 `SharedTransitionScope` 的自动 `key` 匹配。

## 13. 评审清单

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

## 14. 结论

`SharedTransitionLayout` 的性能成本主要来自额外的 Lookahead/approach 布局、活跃 overlay `entry` 按需使用的 `GraphicsLayer`，以及进入与退出内容可能同时绘制。SurfaceFlinger 通常只处理同一个 App Window，瓶颈更可能出现在应用 UI Thread、RenderThread 和 GPU。

`sharedElement()` 与 `sharedBounds()` 的选择取决于内容关系：相同视觉内容用 `sharedElement()`；容器连续但内容变化时用 `sharedBounds()`，再在 `scaleToBounds()` 与 `RemeasureToBounds` 之间选择。元素数量、spring 或 `key()` 都不能脱离具体内容单独作为性能结论。

Android 17 没有 SharedTransitionLayout 专属管线。排查时可用可视化与 Layout Inspector 确认 `key`、`bounds` 和 `Modifier`，关闭调试工具后，再用 Perfetto 对比 layout、draw、RenderThread、GPU 与 FrameTimeline。

## 参考资料

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
