---
title: "Compose Canvas 自定义绘制性能实战"
chapter: "22.28"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-01"
last_verified_against: "AOSP android-17.0.0_r1; Compose UI 1.11.4 (854220f44ea8ea80fee824a6c5a045f39bede289); android17-6.18-2026-06_r6; Android/Compose 官方文档"
confidence: high
tags: [compose, canvas, custom-drawing, drawbehind, drawwithcontent, graphicslayer, rendernode]
related_chapters: ["2.1", "2.3", "7.7", "22.3", "22.19", "22.25"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: "2026-07-31T23:42:23+08:00"
last_draft_polish_run_id: "20260731-234223-draft-polish-a8e2ab9f"
last_review_finalize_at: "2026-08-01T08:12:43+08:00"
last_review_finalize_run_id: "20260801-081243-625aae95"
last_idle_audit_at: "2026-08-09T04:49:28+08:00"
last_idle_audit_run_id: "20260809-044928-idle-audit-a8e2ab9f"
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/draw/overview"
    note: "Compose Canvas、DrawScope、坐标与 drawIntoCanvas 官方文档"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/draw/modifiers"
    note: "drawBehind、drawWithContent、drawWithCache、graphicsLayer 与 CompositingStrategy 边界"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/phases"
    note: "Compose phase 与 state read restart scope"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/draw/brush"
    note: "RuntimeShader / ShaderBrush 与 API 33 可用性"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt"
    note: "Compose UI 1.11.4 Canvas = Spacer + drawBehind 源码锚点"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt"
    note: "Compose UI 1.11.4 DrawScope Paint 复用源码锚点"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt"
    note: "Compose UI 1.11.4 Android graphicsLayer / RenderNode / compositing 源码锚点"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp"
    note: "Android 17 HWUI RenderThread draw frame 源码锚点"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp"
    note: "Android 17 HWUI CanvasContext 源码锚点"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp"
    note: "Android 17 tag 中 HWUI Skia OpenGL pipeline 源码锚点"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp"
    note: "Android 17 tag 中 HWUI Skia Vulkan pipeline 源码锚点"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
    note: "Baseline Profile / ART AOT 覆盖范围边界"
---

# Compose Canvas 自定义绘制性能实战

## 1. 范围与版本锚点

讨论对象是 Android 上的 Compose Canvas。平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，内核固定为 `android17-6.18-2026-06_r6`；Compose 采用独立发布的 UI 1.11.4，源码快照为 `854220f44ea8ea80fee824a6c5a045f39bede289`。

这三个版本必须分开记录：

- Android platform 决定 View、RecordingCanvas、RenderNode、HWUI、RenderThread 与窗口 buffer 路径；
- Compose UI 决定 `Canvas`、draw modifier、`DrawScope` 与 `GraphicsLayer` 的实现；
- kernel 与设备 vendor 实现影响线程调度、频率、内存压力和 GPU driver 等待。

同一台 API 37 设备可以运行多个 Compose 版本。Compose 1.11.4 的行为不能从 `android-17.0.0_r1` 推导。

### 1.1 先校正常见误差

相关说法按源码收窄如下。

| 常见说法 | Android 17 / Compose 1.11.4 的准确边界 |
| --- | --- |
| Skia direct binding 与 DisplayList 二选一 | 标准 `AndroidComposeView` 接收 framework Canvas；硬件窗口通常把绘制命令录入 RenderNode/display list，RenderThread 随后执行。绘制到 `ImageBitmap` 等软件目标时才是另一条即时栅格路径 |
| 每帧创建 Paint 是 Compose 常见问题 | `CanvasDrawScope` 已延迟创建并复用内部 fill/stroke `Paint`；手写 `drawIntoCanvas`、Path、Brush、Shader、文本测量等对象仍需管理 |
| `rememberObject` 缓存绘制资源 | Compose 没有这项通用公开 API；在 composition 中用 `remember`，依赖尺寸或 draw-only 状态时用 `drawWithCache` |
| `graphicsLayer` 等于硬件纹理缓存 | layer 先提供 RenderNode/display list 隔离；只有 alpha、RenderEffect、blend、color filter 或显式策略等条件需要时才进入离屏合成 |
| `drawBehind` 不触发重组 | 状态读取发生在 draw lambda 内时，变化只请求 drawing；若状态已在 composition 中读取，仍会触发重组 |
| Perfetto 的 `FrameTimeslice` 可标记绘制 | Android/Perfetto 没有可依赖的稳定事件名；使用 FrameTimeline、`Choreographer#doFrame`、Compose 当前源码中的 `AndroidOwner:draw`、RenderThread `DrawFrame` 和 GPU 轨道 |
| Profile Installer 保证绘制代码 AOT | Baseline Profile 只引导 ART 编译被 profile 覆盖的代码路径；它不优化 Skia shader、GPU fill、纹理带宽或离屏 pass |
| Android 17 改了固定的 Skia GPU 线程模型 | tag 中仍保留 HWUI 的 Skia OpenGL 与 Vulkan pipeline；设备选择、driver 和 flag 需要实机证据，没有面向应用的统一“Android 17 Canvas 新线程模型” |

## 2. Compose Canvas 怎样进入 Android 17 HWUI

### 2.1 `Canvas` 是一个没有子内容的 draw modifier

Compose Foundation 1.11.4 的实现只有一行核心代码：

`Canvas(modifier, onDraw) = Spacer(modifier.drawBehind(onDraw))`

> 源码锚点：[`Canvas.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt)（Compose UI 1.11.4 快照）。

这条源码说明：

- `Canvas` 仍参加 Compose layout，需要 modifier 给出尺寸；
- `onDraw` 在 drawing phase 执行，不处于 composition scope；
- `Canvas` 没有可由 `drawContent()` 绘制的业务子节点；
- Canvas 自身不会创建独立 Surface、BufferQueue 或 SurfaceFlinger layer。

在 `onDraw` 中调用 `@Composable` 函数会报错。需要准备字体测量器、图片、Shader、Path 或 native Paint 时，应在外层 composition 中创建，或使用 `drawWithCache`。

### 2.2 `DrawScope` 包装 Android Canvas

Android 端的 Compose `Canvas` 是 `AndroidCanvas` 包装。`AndroidComposeView.dispatchDraw(android.graphics.Canvas)` 用可复用的 `CanvasHolder` 把 framework Canvas 交给 Compose root；`DrawScope.drawIntoCanvas` 暴露同一层 Compose Canvas，`nativeCanvas` 再取得 `android.graphics.Canvas`。

> 源码锚点：[`AndroidCanvas.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/AndroidCanvas.android.kt)、[`AndroidComposeView.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt)。

这层包装不会把每个 `drawRect()` 直接变成一个独立 GPU 调用。标准硬件窗口中的大致路径是：

1. UI Thread 执行 Compose drawing lambda；
2. `DrawScope` 把 draw 参数转换为 Android Canvas 调用；
3. framework RecordingCanvas / RenderNode 记录绘制命令；
4. `syncAndDrawFrame()` 把当前 RenderNode 树状态交给 RenderThread；
5. RenderThread 准备树并通过 Skia OpenGL 或 Vulkan pipeline 生成 GPU 工作；
6. App Window buffer 经 BLAST、SurfaceFlinger、HWC 进入显示。

> 平台源码锚点：[`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)、[Skia OpenGL pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp) / [Vulkan pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)（`android-17.0.0_r1`）。

UI Thread 上的 draw lambda 耗时主要反映 Kotlin 计算、Path/Brush 构造、文本测量、display list 录制和调用开销。GPU 执行 draw op 的时间位于后续 RenderThread/GPU 区间，不能用 draw lambda 的同步耗时替代。

### 2.3 绘制目标决定执行方式

同一套 Compose Canvas API 可以面对不同目标。

| 目标 | 常见行为 | 诊断重点 |
| --- | --- | --- |
| 硬件加速 App Window | UI Thread 录制 display list，RenderThread/GPU 生成窗口 buffer | draw recording、RenderThread、GPU、FrameTimeline |
| `Canvas(ImageBitmap)` / software Bitmap | CPU 对 Bitmap 执行软件 Canvas 绘制 | CPU 栅格、Bitmap 分配、内存带宽 |
| `GraphicsLayer` | 录制到独立 RenderNode/display list；按属性决定是否离屏 | layer 重录、属性更新、离屏面积 |
| `SurfaceView` 或 front-buffer renderer | 独立 Surface 与 producer cadence | 自有 render 线程、BufferQueue、layer 同步 |

因此，“Compose Canvas 使用 GPU”只对标准硬件目标成立。即使 Activity 窗口开启硬件加速，把同一 View 或 Compose 内容画入 Bitmap 时，当前 Canvas 仍可能是软件 Canvas。

### 2.4 与 View `onDraw()` 的关系

Compose Canvas 与 View `onDraw(Canvas)` 最终都能进入 Android Canvas/HWUI，但两者的 invalidation、节点树、layer 管理和状态观察不同。给定相同几何、Paint、目标面积和硬件 Canvas，后半段 Skia/GPU 成本可能接近；UI Thread 录制成本与失效范围仍可能不同。

“Compose Canvas 比 View Canvas 快”或“二者完全等价”都缺少前提。迁移评估要使用相同图形、相同 build、相同设备和相同帧 metric。

## 3. 三种 draw modifier 的语义

### 3.1 `drawBehind`

`DrawBackgroundModifier.draw()` 的顺序是调用自定义 `onDraw()`，再调用 `drawContent()`。它适合背景、装饰线、选中态、网格和不遮挡内容的效果。

`Canvas` 采用的就是这个 modifier。给现有 `Text`、`Image` 或容器增加背景时，直接使用 `drawBehind` 可以少建一个布局节点。

### 3.2 `drawWithContent`

`drawWithContent` 把顺序交给调用方。以下行为都由 `drawContent()` 的位置决定：

- 先调用：自定义内容覆盖在业务内容上方；
- 后调用：自定义内容位于业务内容下方；
- 不调用：业务内容不会被画出；
- 调用多次：业务内容也会被重复绘制。

遮罩、局部高亮、前景装饰和 blend effect 常用它。涉及 `BlendMode.Clear`、`DstIn` 等影响目标像素的操作时，还要判断是否需要 `CompositingStrategy.Offscreen`，否则 blend 可能作用到 layer 外已有的窗口内容。

### 3.3 `drawWithCache`

`drawWithCache` 把工作分成 cache build 与实际 draw：

- cache block 可创建 Brush、Shader、Path、`TextLayoutResult`、Stroke 或受管 `GraphicsLayer`；
- `onDrawBehind` / `onDrawWithContent` 返回每次 drawing 执行的 block；
- size、density、layout direction、cache block 身份或 cache block 读取的 snapshot state 变化时，缓存失效；
- draw block 中读取的 snapshot state 只请求 drawing，不会因此重建 cache block。

这个差别对每帧动画很重要。静态 Path 和 Brush 放在 cache block；progress、alpha、指针坐标等高频状态留在返回的 draw block。

下面的折线图示例把归一化 Path 缓存在尺寸和 samples 变化范围内，只在 drawing 时读取动画进度。

```kotlin
@Composable
fun Sparkline(
    samples: List<Float>,
    progress: State<Float>,
    modifier: Modifier = Modifier,
) {
    Spacer(
        modifier = modifier.drawWithCache {
            val path = Path()
            val minValue = samples.minOrNull() ?: 0f
            val maxValue = samples.maxOrNull() ?: minValue
            val range = (maxValue - minValue).takeIf { it > 0f } ?: 1f
            val stepX =
                if (samples.size > 1) size.width / samples.lastIndex else 0f

            samples.forEachIndexed { index, value ->
                val x = index * stepX
                val y = size.height * (1f - (value - minValue) / range)
                if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }

            val stroke = Stroke(width = 2.dp.toPx())

            onDrawBehind {
                val right = size.width * progress.value.coerceIn(0f, 1f)
                clipRect(right = right) {
                    drawPath(path, color = Color(0xFF1565C0), style = stroke)
                }
            }
        }
    )
}
```

这段代码中，`samples` 或 modifier lambda 更新会重建 cache，尺寸变化也会重建 Path；`progress.value` 位于 draw block，只让绘制失效。它仍会在每个动画帧重新录制 `drawPath` 和 clip 命令，缓存的是对象与几何计算，不是自动保存上一帧像素。

官方也提醒：没有可缓存对象时，`drawWithCache` 会增加 lambda 与缓存管理。简单的单色 `drawRect()` 用 `drawBehind` 更合适。

### 3.4 坐标、density 与变换

`DrawScope.size` 与绘制 API 使用像素坐标，原点位于左上角。设计尺寸使用 `dp.toPx()`，与画布大小成比例的图形直接基于 `size` 计算。

`translate`、`rotate`、`scale`、`inset` 和 `withTransform` 只改变当前 drawing 的坐标，不改变节点在 layout 中报告的宽高。图形变换后越过 bounds 时，是否可见取决于父 clip、graphics layer、offscreen 范围和窗口边界。视觉位置变化需要与输入区域、语义和邻接布局一致验证。

## 4. 状态读取决定重启哪个阶段

Compose 记录 snapshot state 在哪个 restart scope 被读取。

| 读取位置 | 状态变化后的最小工作范围 | 例子 |
| --- | --- | --- |
| Composable 函数体 | Composition，必要时继续 Layout/Drawing | 在 modifier 参数外先读取 `colorState.value` |
| placement lambda | Layout placement 与 Drawing | `Modifier.offset { ... }` |
| `Canvas` / `drawBehind` / `drawWithContent` | Drawing | 在 draw lambda 内读取动画颜色 |
| `graphicsLayer {}` | layer 属性更新 | 在 block 内读取 rotation/alpha state |
| `drawWithCache` cache block | cache 重建与 Drawing | 用 state 生成 Path 或 Shader |

### 4.1 “状态在哪里创建”不决定阶段

阶段由读取位置决定。下面两种写法观察同一个 state，工作范围不同：

- 在 Composable 函数体求出 `val color = colorState.value`，再传给 modifier：变化触发 composition；
- 在 `drawBehind { drawRect(colorState.value) }` 内读取：变化只触发 drawing。

高频动画只改变像素而不改变节点结构与尺寸时，延后到 drawing 读取可以省去 composition 和 layout。若颜色变化还会影响语义、布局或子节点选择，就应在对应上游阶段读取，不能只为减少重组而隐藏必要更新。

### 4.2 Drawing invalidation 仍可能重录 display list

“只触发 drawing”表示 Compose 不需要重跑 composition/layout，不表示 GPU 只改一个参数，也不表示已有像素会自动增量更新。

当 draw node 失效时，Compose 会重新执行相关 draw block 并更新对应 display list/layer。一个不断增长的 Path 每帧仍可能重新录制整条 Path。需要降低成本时可以：

- 把历史笔迹按 segment 分块，只有活动 segment 高频变化；
- 对过密输入点做有误差界限的简化；
- 把不变背景放进独立 graphics layer；
- 对低延迟墨迹评估 front-buffer 专用方案。

## 5. 对象分配与缓存

### 5.1 DrawScope 已复用内部 Paint

Compose UI 1.11.4 的 `CanvasDrawScope` 有两个延迟创建字段：

- `fillPaint` 用于 Fill；
- `strokePaint` 用于 Stroke。

> 源码锚点：[`CanvasDrawScope.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt)。

第一次需要时创建，后续 draw call 复用。因此，使用 `drawRect(color)`、`drawCircle()` 或 `drawPath(..., style = Stroke)` 不会为每次调用新建底层 Paint。

仍需留意这些应用对象：

- 每帧新建复杂 `Path`；
- 每帧生成 gradient Brush/Shader；
- 每帧执行文本测量；
- 每帧构造大的点列表、排序或几何索引；
- `drawIntoCanvas` 中新建 native Paint、Path、Drawable；
- 每帧创建 Bitmap 或改变 Bitmap 像素。

### 5.2 `remember` 与 `drawWithCache` 的选择

| 对象依赖 | 合适位置 |
| --- | --- |
| 与 draw size 无关，且有 composition scope | `remember(key)` |
| 依赖当前 `size`、density 或 layout direction | `drawWithCache` cache block |
| 每帧变化的标量 | draw block 直接读取，避免放进 cache key |
| 由后台计算的大数据 | ViewModel/worker 生成不可变快照，UI 只消费 |
| Android native 绘制对象 | 外层 `remember`，在 `drawIntoCanvas` 中使用 |

下面的示例用于调用只接受 framework Canvas 的旧 `Drawable`，并把对象创建留在 composition。

```kotlin
@Composable
fun LegacyDrawableCanvas(
    modifier: Modifier = Modifier,
) {
    val drawable = remember {
        ShapeDrawable(OvalShape()).apply {
            paint.color = android.graphics.Color.rgb(21, 101, 192)
        }
    }

    Canvas(modifier = modifier) {
        drawIntoCanvas { canvas ->
            drawable.setBounds(0, 0, size.width.toInt(), size.height.toInt())
            drawable.draw(canvas.nativeCanvas)
        }
    }
}
```

这段代码每次 drawing 只更新 bounds 并调用 `Drawable.draw()`，不会新建 Drawable 或 Paint。`drawIntoCanvas` 是兼容入口；已有 `DrawScope` API 能表达的图形优先使用 Compose API，减少平台类型耦合。

### 5.3 缓存不能脱离生命周期

缓存 Path、Bitmap、Shader 或 GraphicsLayer 时还要定义：

- 数据改变时怎样失效；
- size/density 改变时怎样重算；
- 页面离开后怎样释放 native/GPU 资源；
- 是否会同时保留旧列表和新几何；
- 多窗口或不同 density 是否错误共享。

大对象保留时间过长可能用内存压力换取较小的 CPU 节省。缓存策略要用分配、GC、graphics memory 与帧数据共同验证。

## 6. `graphicsLayer`：DisplayList 隔离与离屏合成

### 6.1 API 29+ 使用公开 RenderNode

Compose UI 1.11.4 的 Android `GraphicsLayerV29`：

- 创建 `RenderNode("graphicsLayer")`；
- 用 `beginRecording()` / `endRecording()` 录制 layer 内容；
- 用 `Canvas.drawRenderNode()` 把 layer 放进父 Canvas；
- 通过 RenderNode 属性设置平移、缩放、旋转、alpha、clip、shadow 和 RenderEffect。

> 源码锚点：[`GraphicsLayerV29.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt)。

Android 12—17 都走 API 29+ 实现。`graphicsLayer` 仍属于宿主 App Window 的 RenderNode 树，SurfaceFlinger 通常看不到一个同名独立 layer。

### 6.2 Layer 不等于离屏纹理

layer 的基础能力是隔离绘制指令。内容未失效时，父节点变化可以重新引用已有 display list，不必执行子树的 Kotlin draw code。是否把结果栅格化到离屏 buffer，由 compositing 条件决定。

| `CompositingStrategy` | 行为 | 使用边界 |
| --- | --- | --- |
| `Auto` | 由 alpha、effect 等属性决定；默认策略 | 通用选择 |
| `Offscreen` | 总是先画到 layer bounds 大小的中间目标 | mask、受控 blend、明确需要隔离 |
| `ModulateAlpha` | 把 alpha 调制到各 draw op，通常省去 alpha 离屏 | 内容不重叠且视觉结果允许 |

当前 Android backend 还会在以下条件强制 compositing layer：

- `RenderEffect` 非空；
- `blendMode` 不是 `SrcOver`；
- `colorFilter` 非空；
- 显式 `Offscreen`。

官方文档还说明，`Auto` 下 alpha 小于 1 会创建离屏 buffer；overscroll 与 RenderEffect 也会需要离屏。离屏目标的范围通常是 layer bounds，局部效果应避免包住全屏父节点。

### 6.3 `ModulateAlpha` 会改变重叠像素

`ModulateAlpha` 对 layer 内每条 draw command 分别应用 alpha。两个图形重叠时，重叠区域会叠加多次，结果与“先把整个 layer 画为不透明，再统一乘 alpha”不同。

只有确认 layer 内内容不重叠，或差异符合设计时，才用它换取更少的离屏工作。透明文本、阴影、图片和多层图形通常要实机对比。

### 6.4 属性动画使用 lambda overload

`graphicsLayer {}` 的源码说明允许在 block 内读取 State；变化只更新 layer 属性，不触发 recomposition 与 remeasure。block 可能被调用多次，里面只做属性赋值。

下面的示例用于旋转一份不变的图标内容。

```kotlin
@Composable
fun RotatingIcon(
    angle: State<Float>,
    image: ImageVector,
    modifier: Modifier = Modifier,
) {
    Icon(
        imageVector = image,
        contentDescription = null,
        modifier = modifier.graphicsLayer {
            rotationZ = angle.value
        },
    )
}
```

这段代码在 `angle.value` 变化时更新 RenderNode rotation 属性；图标内容没有失效时，无需重跑它的 draw block。RenderThread/GPU 仍要在每个可见动画帧合成变换后的 layer。

### 6.5 多层嵌套的成本

每个 graphics layer 至少增加 RenderNode、属性同步、几何变换/clip 处理和 display list 引用。触发 offscreen 时，还会增加中间 render target、清理、栅格化与采样。

嵌套数量本身没有通用安全阈值。评审时检查：

- 哪些层只为一个默认属性而存在；
- 多个相邻 transform 能否放进同一层；
- 离屏 layer 的像素面积；
- 子内容是否每帧失效，导致缓存价值消失；
- alpha、blur、shadow 与 blend 是否叠加多个 pass；
- layer 是否扩大 clip 或越界绘制范围。

## 7. 离屏、BlendMode、模糊与阴影

### 7.1 `saveLayer()` 与 Offscreen 都产生中间结果

硬件加速 Canvas 的 `saveLayer()`、`CompositingStrategy.Offscreen`、RenderEffect 和某些 alpha/blend 路径都可能生成 GPU 中间目标，不应描述为 CPU Bitmap 缓存。

中间目标常见成本包括：

- 按 bounds 分配或复用 render target；
- 清理目标；
- 把内容栅格化一次；
- 再采样并合成到父目标；
- 增加 GPU 内存与带宽；
- 大范围 blur 还会扩大采样区域或增加 pass。

需要 `saveLayer()` 时给出尽量小且正确的 bounds。全屏透明层、全屏 blur 和多个嵌套 mask 很容易把局部视觉效果放大为整屏像素工作。

### 7.2 BlendMode 要先定义作用域

`BlendMode.Clear`、`DstIn`、`SrcIn` 等需要明确“与谁混合”。没有离屏隔离时，操作可能影响父 Canvas 已有内容；使用 `Offscreen` 可以把影响限制在当前 layer bounds。

不要为了任何 blend 都固定使用 Offscreen。简单 `SrcOver`、不重叠 alpha 或普通 clip 可能不需要中间目标。正确性先由对照截图验证，性能再由 GPU 和帧数据判断。

### 7.3 渐变与 RuntimeShader

大面积渐变和 AGSL 的主要变量是覆盖像素数、shader 指令复杂度、采样次数、精度与 backend/driver。Shader 对象和不变 uniform 应缓存，每帧只更新动态 uniform。

`android.graphics.RuntimeShader` 从 API 33 提供。下面的示例缓存 shader 与 brush，size 改变时更新 resolution，动画时间只在 drawing 时写入。

```kotlin
private const val WAVE_SHADER = """
    uniform float2 resolution;
    uniform float time;

    half4 main(float2 position) {
        float2 uv = position / resolution;
        float wave = 0.5 + 0.5 * sin(time + uv.x * 6.2831853);
        return half4(half(wave), half(uv.y), half(1.0 - wave), 1.0);
    }
"""

@RequiresApi(Build.VERSION_CODES.TIRAMISU)
@Composable
fun ShaderBackground(
    timeSeconds: State<Float>,
    modifier: Modifier = Modifier,
) {
    val shader = remember { RuntimeShader(WAVE_SHADER) }
    val brush = remember(shader) { ShaderBrush(shader) }

    Spacer(
        modifier = modifier.drawWithCache {
            shader.setFloatUniform("resolution", size.width, size.height)
            onDrawBehind {
                shader.setFloatUniform("time", timeSeconds.value)
                drawRect(brush)
            }
        }
    )
}
```

这段代码要求 API 33，并应在低版本提供普通 Brush fallback。它避免每帧编译 AGSL 或新建 Shader；全屏 `drawRect` 仍会执行全屏 fragment 工作，缓存对象不会降低每像素数学成本。

## 8. Bitmap 与 Canvas 的互操作

### 8.1 Hardware Bitmap 适合作为只读绘制源

`Bitmap.Config.HARDWARE` 从 API 26 提供，像素位于图形内存且 Bitmap 永远不可变。它适合解码后只显示的图片：

- 可以包装为 Compose `ImageBitmap` 并画到标准硬件 Canvas；
- 不能作为可变 Bitmap 继续写像素；
- 不能作为 `Canvas(bitmap)` 的可写目标；
- 也不能作为图片源画到 software Canvas；
- 需要读回像素、软件滤镜或画入 Bitmap 时，应选择 software allocation 或显式复制。

Hardware Bitmap 不等于“任何场景零拷贝”。缩放、颜色空间、采样、RenderEffect、离屏 layer 与最终窗口合成都可能增加 GPU 工作。

### 8.2 频繁修改软件 Bitmap 会引入上传

如果应用每帧在 CPU Bitmap 上改像素，再把它画进硬件窗口，HWUI 需要让更新后的内容对 GPU 可见，可能产生纹理上传和同步。动态图表、粒子或墨迹通常应直接录制矢量 draw commands；只有复用像素结果能明显减少更大成本时，才考虑 Bitmap cache。

### 8.3 `drawImage` 仍要控制解码与目标尺寸

Canvas 不负责替应用选择合适的 decode 尺寸。大图缩到很小仍会占用解码内存和采样带宽。图片加载应在 decode 阶段设置目标尺寸、颜色空间和 allocator，详见 22.26。

## 9. 四类实战场景

### 9.1 图表

图表适合 Compose Canvas，因为大量图元可以放在一个 layout node 中。优化顺序是：

1. 数据排序、聚合与坐标索引放到数据层或 cache build；
2. Path、网格 Brush、Stroke 和文字测量按数据与 size 缓存；
3. 只生成当前 viewport 可见的点和标签；
4. 手势状态在 drawing 或 placement 阶段读取；
5. 大数据更新使用不可变快照，避免 draw 时遍历正在修改的集合；
6. 用 Macrobenchmark 固定缩放、拖动和 fling 场景。

Canvas 减少了 Composable 节点数量，但 draw op 数量、Path 复杂度和文字栅格成本仍在。

### 9.2 粒子与动画背景

一个 Canvas 画多个粒子通常比为每个粒子创建 Composable 更轻。仍需控制：

- 活跃粒子数量与屏幕外剔除；
- 每帧对象分配；
- 随机数、碰撞和物理计算；
- 透明 overdraw；
- 大面积 blur、shadow 与 blend；
- UI Thread 录制时间。

粒子状态可以在后台计算后提交不可变帧快照，但 Canvas draw block 本身由 Compose drawing phase 调用，不能随意迁移到后台线程。需要独立 producer cadence 或更重 GPU pipeline 时，评估 SurfaceView、OpenGL/Vulkan 或专用引擎。

### 9.3 墨迹与手写

普通表单签名可以用 Canvas：

- coalesce historical pointer samples；
- 按 stroke/segment 保存 Path；
- 活动笔画高频更新，已完成笔画分组缓存；
- 缩小无效区域和对象分配；
- 在后台做保存、压缩与矢量简化。

专业手写关注触笔到光子的延迟。`CanvasFrontBufferedRenderer` 使用 SurfaceView、front buffer 与 multi buffer，并在内部 rendering thread 回调，适合评估低延迟路径。它会引入独立 layer、Surface 生命周期、transaction 和 tearing 权衡，不能当成普通 Compose Canvas 的透明替换。

### 9.4 动态全屏 shader

RuntimeShader 适合连续程序化背景，但应准备：

- API 32 及以下 fallback；
- 编译失败或设备兼容 fallback；
- 不同分辨率与刷新率的压力测试；
- 低功耗或减少动态效果模式；
- shader uniform 与时间基准；
- 大面积离屏、RenderEffect 和多重采样检查。

减少 Kotlin 分配不会消除 shader 的 GPU 成本。Perfetto 要同时看 app frame、RenderThread、GPU frequency/queue 和热状态。

### 9.5 自定义绘制仍要提供语义

Canvas 中的线、点、柱和图标不会自动成为独立语义节点。纯装饰可以由父组件描述；表达业务信息或响应点击时，应使用带 `contentDescription` 的 Canvas overload、`Modifier.semantics`、custom action，或为可交互元素提供可访问的 Compose 节点。

一张图表画得更快，却让读屏服务无法获得数据，不能算完成优化。语义节点数量也应按可操作信息设计，避免为每个装饰像素创建节点。

## 10. 何时转向 SurfaceView

| 需求 | Compose Canvas | SurfaceView / front-buffer / native producer |
| --- | --- | --- |
| 图表、装饰、有限动画 | 合适，与 UI layout/semantics 易协作 | 通常增加不必要复杂度 |
| 与 UI 同 cadence 的 shader | 可用，先测 UI recording 与 GPU | 全屏高负载且需独立调度时再评估 |
| 视频、相机、外部 decoder | 不适合作为持续像素 producer | SurfaceView 通常更符合独立 buffer 语义 |
| 专业手写低延迟 | 普通签名可用 | front-buffer 路径更适合低延迟目标 |
| 游戏或大量持续 GPU work | UI overlay 可保留 Compose | 主体使用 EGL/Vulkan/引擎 |
| 需要独立 render thread | draw block 仍由 Compose drawing 调用 | 独立 producer 可自行调度 |

SurfaceView 会创建独立 SurfaceControl layer，并带来 Z-order、同步、生命周期、截图和无障碍协调。TextureView 把外部 buffer 再采样进宿主窗口，也不是默认的性能升级。选择依据是 producer、cadence 和合成需求。

## 11. 性能工具：分别量 UI 录制、RenderThread 与 GPU

### 11.1 Macrobenchmark 作为回归入口

`FrameTimingMetric` 提供：

- API 31+ 的 `frameOverrunMs`，表示相对 deadline 的 overrun；
- UI Thread 与 RenderThread 相关的 `frameDurationCpuMs`；
- `frameCount`，用于识别无效帧数量变化。

Canvas 性能场景应固定输入轨迹、数据、动画时长、viewport、图片缓存和 shader warmup。使用 profileable、non-debuggable 目标应用，并保留每轮 trace。

### 11.2 Perfetto 没有稳定的 Canvas 单节点 slice

Compose 1.11.4 的 `AndroidComposeView.dispatchDraw()` 当前带有 `AndroidOwner:draw` trace，但它覆盖 root draw 与 dirty layer 更新，不等于某个 Canvas。

[Composition Tracing](22-compose-compiler-recomposition-diagnostics.md) 记录 Composable 在 composition 中的执行时序，不会自动给每个 draw modifier body 或 GPU draw op 建立 slice。两类 trace 不能混用。

定位按层次进行：

1. FrameTimeline 找到目标 App SurfaceFrame；
2. UI Thread 查看 `Choreographer#doFrame`、Traversal、`AndroidOwner:draw` 与自定义 marker；
3. 检查 draw 区间里的 GC、锁、Binder、I/O 和 thread state；
4. RenderThread 查看 `DrawFrame`、dequeue/queue buffer 与 GPU completion；
5. GPU 轨道、频率和 render stage 判断 shader、fill、texture 与离屏 pass；
6. App 按时完成后继续检查 SurfaceFlinger actual timeline 与 present。

不存在的 `FrameTimeslice` 不应出现在查询或监控协议中。内部 slice 名会随 Compose/HWUI 版本变化，录制后先确认当前 trace。

### 11.3 自定义 trace 只测 draw recording

可以在一个已确认过重的 draw block 外围使用 `androidx.tracing`，名称保持固定且不含动态数据。该 slice 记录 UI Thread 执行 lambda 与录制命令的墙钟时间，不能代表 GPU 执行时间。

不要给每个 draw primitive 添加 marker。大量 trace event 会改变被测代码和 trace 体积。

### 11.4 Layout Inspector 的边界

Layout Inspector 可以检查 Compose tree、layer、recomposition/skip 计数和 modifier 顺序。它不统计 draw invalidation 次数，也不提供每个 Canvas 的 GPU 时间。正式计时要关闭 Inspector 后用 release-like 构建复测。

### 11.5 Baseline Profile 的边界

Baseline Profile 可以覆盖图表页面、Canvas draw 代码、数据准备和交互路径，引导 ART 对包含的方法做 AOT 优化。它不能改善：

- 过大的 Path 或 draw op 数量；
- 全屏 overdraw；
- GPU shader 指令；
- Bitmap 上传；
- RenderEffect/Offscreen 带宽；
- SurfaceFlinger 或 driver 等待。

生成 profile 后要用 `CompilationMode.Partial` 等对应生产条件验证，不能用“已经依赖 Profile Installer”代替测量。

## 12. Android 12—17 的版本边界

### Android 12 / API 31

标准 Compose Canvas 已经运行在 Android View/HWUI 路径上。API 31 提供公开 RenderEffect，blur 和 effect 更容易使用，也更容易引入离屏 pass。FrameTimeline 可用于现代帧诊断。

### Android 13 / API 33

公开 `RuntimeShader` 让 AGSL 可用于 Compose `ShaderBrush`。Hardware Bitmap 仍是只读绘制源；不能因为 shader 与 bitmap 都位于图形侧，就忽略目标面积、采样和颜色空间。

### Android 14 / API 34

公开 `HardwareBufferRenderer` 提供 `RenderNode → HardwareBuffer` 的离屏 HWUI 能力。它用于明确的离屏生产，不会替换普通 Compose Canvas 的宿主窗口路径。

### Android 15 / API 35

Canvas/RenderNode/HWUI 主路径延续。设备刷新率、frame-rate hint、GPU backend 与 vendor driver 可能改变结果，跨版本比较要固定设备和应用构建。

### Android 16 / API 36

没有需要把 Compose Canvas 改写成独立 Surface 的公开架构变化。Compose artifact 继续独立更新，平台升级测试必须同时记录 Compose 版本。

### Android 17 / API 37

当前固定 tag 中：

- `AndroidComposeView` 仍在 `dispatchDraw()` 接收 framework Canvas；
- framework 硬件绘制仍使用 RecordingCanvas/RenderNode/display list；
- `DrawFrameTask` 与 `CanvasContext` 仍把树状态交给 HWUI RenderThread；
- Skia OpenGL 与 Vulkan pipeline 源码都存在；
- 最终 App Window buffer 仍经过 BLAST、SurfaceFlinger 与 HWC。

因此，不能声称 Android 17 为 Compose Canvas 固定切换 Vulkan，或固定更改 Skia GPU 线程模型。实机 backend 可从设备配置、trace、dumpsys 和 driver 证据确认。

## 13. 评审清单

- Android platform 是否固定为 `android-17.0.0_r1`，Compose UI 是否单独固定为 1.11.4；
- 是否把 `Canvas` 说明为 `Spacer + drawBehind`，并为它提供明确尺寸；
- 是否把标准硬件 Canvas 的 UI Thread 录制与 RenderThread/GPU 执行分开；
- 是否根据目标 Canvas 判断硬件或软件路径；
- `drawWithContent` 是否在正确位置调用且只调用所需次数的 `drawContent()`；
- 简单绘制是否避免无意义的 `drawWithCache`；
- Path、Brush、Shader、Stroke 和文本测量是否按 size/state 正确缓存；
- 高频 state 是否在 draw block 读取，避免每帧重建 cache；
- 是否错误地把 drawing restart 理解为增量保存上一帧像素；
- 是否知道 DrawScope 已复用内部 fill/stroke Paint；
- native Paint、Drawable 和 Path 是否在 draw 外创建；
- `graphicsLayer` 是否用于真实的隔离、transform 或 effect；
- 是否误把 RenderNode/display list layer 当作固定离屏纹理；
- alpha、RenderEffect、blend、color filter 和 Offscreen 是否扩大中间目标；
- 使用 `ModulateAlpha` 时内容是否存在重叠；
- 多层嵌套是否产生重复 offscreen、blur、shadow 或大面积透明合成；
- Hardware Bitmap 是否只作为不可变绘制源；
- 是否每帧修改 software Bitmap 并触发上传；
- RuntimeShader 是否只在 API 33+ 使用，并有低版本 fallback；
- shader 是否缓存，动态 uniform 是否在 drawing 更新；
- 图表是否只处理 viewport 数据，文本和 Path 是否缓存；
- 墨迹是否按 segment 管理，低延迟需求是否评估 front buffer；
- Canvas 中的重要信息与操作是否提供语义；
- 是否把 SurfaceView/TextureView 当成无条件优化；
- Macrobenchmark 是否使用 profileable、non-debuggable 构建和固定脚本；
- Perfetto 是否从 FrameTimeline 关联 UI、RenderThread、GPU 和 present；
- 是否删除了不存在的 `FrameTimeslice` 假设；
- Layout Inspector 计数是否没有被误当成 draw/GPU 计时；
- Baseline Profile 是否覆盖目标用户路径，并与 GPU/带宽优化分开；
- kernel 结论是否止于 `android17-6.18-2026-06_r6` 的标准机制，没有推断设备 GPU driver 策略。

## 14. 结论

Compose Canvas 在 Android 上沿用成熟的 Canvas、RenderNode 和 HWUI 路径。`Canvas` 只是一个带 `drawBehind` 的 Spacer；`DrawScope` 负责更安全的绘制接口和内部 Paint 复用；AndroidComposeView 再把命令送入宿主窗口的 display list。

性能优化要区分三段：UI Thread 的几何计算与录制、RenderThread 的树准备与 Skia 提交、GPU 的像素和离屏工作。`drawWithCache` 处理对象与几何复用，`graphicsLayer` 处理指令隔离和属性变换；它们都不会自动减少复杂 Path、全屏 shader 或多重离屏的像素成本。

Android 17 没有 Compose Canvas 专属显示管线。可靠做法是固定 Compose/平台版本，控制状态读取阶段与 cache invalidation，再用 Macrobenchmark 和 Perfetto 沿 FrameTimeline、UI Thread、RenderThread、GPU、SurfaceFlinger 逐段验证。

## 参考资料

- [Graphics in Compose](https://developer.android.com/develop/ui/compose/graphics/draw/overview)：Canvas、DrawScope、坐标、Path、文本、图片和 `drawIntoCanvas`。
- [Graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)：`drawBehind`、`drawWithContent`、`drawWithCache`、graphics layer 与 compositing strategy。
- [Jetpack Compose phases](https://developer.android.com/develop/ui/compose/phases)：Composition、Layout、Drawing 的 state read 与 restart scope。
- [Brush and RuntimeShader](https://developer.android.com/develop/ui/compose/graphics/draw/brush)：AGSL `RuntimeShader`、`ShaderBrush` 与 API 33 边界。
- [Compose UI release notes](https://developer.android.com/jetpack/androidx/releases/compose-ui)：Compose UI 1.11.4 稳定版本记录。
- [`Canvas.kt`（Compose 1.11.4 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt)：`Spacer(modifier.drawBehind(onDraw))` 实现。
- [`DrawModifier.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/draw/DrawModifier.kt)：draw modifier 顺序、cache invalidation 与 `CacheDrawScope`。
- [`CanvasDrawScope.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt)：内部 fill/stroke Paint 的延迟创建与复用。
- [`AndroidCanvas.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/AndroidCanvas.android.kt)：framework Canvas 包装、`CanvasHolder` 与 `nativeCanvas`。
- [`GraphicsLayerModifier.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/graphics/GraphicsLayerModifier.kt)：layer 属性、state read 与 placement 更新。
- [`GraphicsLayerV29.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt)：RenderNode recording、compositing strategy 与强制离屏条件。
- [`AndroidComposeView.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt)：`dispatchDraw()`、`AndroidOwner:draw` 与 dirty layer 更新。
- [Android hardware acceleration](https://developer.android.com/topic/performance/hardware-accel)：hardware Canvas 的 display list 模型、View layer 与 `saveLayer()` 边界。
- [`RecordingCanvas.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RecordingCanvas.java)：Android 17 framework 硬件绘制录制入口。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp) 与 [`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：UI Thread 到 RenderThread 的同步、树准备与绘制。
- [Skia OpenGL pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp) 与 [Skia Vulkan pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)：Android 17 tag 中并存的 HWUI backend。
- [FrameTimingMetric](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric) 与 [FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：帧回归 metric 和 App/SF 时序分析。
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)：ART AOT 覆盖范围与 Profile Installer 边界。
- [`Bitmap.Config.HARDWARE`](https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE)：Hardware Bitmap 的不可变与只读显示语义。
- [`CanvasFrontBufferedRenderer`](https://developer.android.com/reference/androidx/graphics/lowlatency/CanvasFrontBufferedRenderer)：SurfaceView front/multi-buffer 低延迟绘制路径。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线；Compose Canvas 没有专属 kernel API。
