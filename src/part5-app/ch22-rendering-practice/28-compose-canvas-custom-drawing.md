---
title: "Compose Canvas：自定义绘制与性能"
chapter: "22.28"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1；Compose UI 1.12.0（963bf914f78b389bdddef0da7f36bee19d897274）；android17-6.18-2026-06_r6；Android/Compose 官方文档"
confidence: high
tags: [compose, canvas, custom-drawing, drawbehind, drawwithcontent, graphicslayer, rendernode]
related_chapters: ["2.1", "2.3", "7.7", "22.3", "22.19", "22.25"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: "2026-08-15T05:46:46+08:00"
last_draft_polish_run_id: "20260815-054646-gracker-writing"
last_review_finalize_at: "2026-08-15T05:46:46+08:00"
last_review_finalize_run_id: "20260815-054646-gracker-writing-review"
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
    note: "Compose 阶段与状态读取后的重启范围"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/draw/brush"
    note: "RuntimeShader / ShaderBrush 与 API 33 可用性"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt"
    note: "Compose UI 1.12.0 Canvas = Spacer + drawBehind 源码锚点"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt"
    note: "Compose UI 1.12.0 DrawScope Paint 复用源码锚点"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt"
    note: "Compose UI 1.12.0 Android graphicsLayer / RenderNode / compositing 源码锚点"
  - type: official
    path: "https://developer.android.com/reference/kotlin/androidx/compose/ui/graphics/LayerOutsets"
    note: "Compose UI 1.12.0 图形层可视边界扩展"
  - type: official
    path: "https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui/maven-metadata.xml"
    note: "Compose UI 稳定版与预览版核对"
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

# Compose Canvas：自定义绘制与性能

## 1. 范围与版本锚点

讨论对象是 Android 上的 Compose Canvas。平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，内核固定为 `android17-6.18-2026-06_r6`；Compose 采用独立发布的 UI 1.12.0，源码快照为 `963bf914f78b389bdddef0da7f36bee19d897274`。截至 2026 年 8 月 15 日，Google Maven 中的最新稳定版是 1.12.0，1.13.0-alpha01 属于预览版。

HWUI 是 Android 的硬件加速 UI 渲染器；RenderNode 记录一组绘制命令，display list 是这些命令的列表；RenderThread 是执行 HWUI 渲染工作的线程；buffer 是窗口提交的像素缓冲区。

平台、Compose 和内核版本必须分开记录：

- Android platform 决定 View、RecordingCanvas、RenderNode、HWUI、RenderThread 与窗口 buffer 的路径；
- Compose UI 决定 `Canvas`、绘制类 `Modifier`、`DrawScope` 与 `GraphicsLayer` 的实现；
- 内核和设备厂商实现会影响线程调度、频率、内存压力与 GPU 驱动等待。

同一台 API 37 设备可以运行多个 Compose 版本，因此不能从 `android-17.0.0_r1` 推导 Compose 1.12.0 的具体实现。

### 1.1 常见说法与适用边界

这些说法需要带上绘制目标、Compose 版本和设备实现等前提。

| 常见说法 | Android 17 / Compose 1.12.0 的适用边界 |
| --- | --- |
| 每次 Compose Canvas 调用都直接进入 Skia/GPU | 标准 `AndroidComposeView` 接收 framework Canvas；硬件窗口通常先把命令录入 RenderNode/display list，再由 RenderThread 执行。绘制到 `ImageBitmap` 等软件目标时走 CPU 即时栅格路径 |
| Compose 会逐帧创建 Paint | `CanvasDrawScope` 会延迟创建并复用内部填充/描边 `Paint`；应用自己创建的 Path、Brush、Shader、文本测量器与 `android.graphics.Paint` 仍需管理 |
| 用 `rememberObject` 缓存绘制资源 | Compose 没有这项通用公开 API；组合阶段使用 `remember`，资源依赖尺寸或仅供绘制时使用 `drawWithCache` |
| `graphicsLayer` 等于硬件纹理缓存 | 图形层先提供 RenderNode/display list 隔离；alpha（透明度）、RenderEffect（渲染效果）、混合模式、颜色滤镜或显式策略需要时，才会进入离屏合成 |
| `drawBehind` 不触发重组 | 状态在 draw lambda（绘制回调）中读取时，变化只请求重新绘制；若状态已在组合阶段读取，仍会触发重组 |
| Perfetto 的 `FrameTimeslice` 可标记绘制 | Android/Perfetto 没有可依赖的稳定事件名；应结合 FrameTimeline、`Choreographer#doFrame`、当前源码中的 `AndroidOwner:draw`、RenderThread `DrawFrame` 与 GPU 轨道 |
| Profile Installer 保证绘制代码 AOT | Baseline Profile 只引导 ART 对覆盖到的代码路径做 AOT（Ahead-of-Time，预编译）；它不会减少 Skia shader 指令、GPU 像素填充、纹理带宽或离屏 pass（渲染步骤） |
| Android 17 固定改变了 Skia GPU 线程模型 | 该 tag 仍同时保留 HWUI 的 Skia OpenGL 与 Vulkan pipeline（后端管线）；设备选择、驱动和功能开关需要实机证据，平台没有给应用统一切换到某种模型 |

## 2. Compose Canvas 怎样进入 Android 17 HWUI

### 2.1 `Canvas` 是没有子内容的绘制 Modifier

Compose Foundation 1.12.0 的实现只有一行关键代码：

`Canvas(modifier, onDraw) = Spacer(modifier.drawBehind(onDraw))`

> 当前源码锚点：[`Canvas.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt)（Compose UI 1.12.0 快照）。

这条源码说明：

- `Canvas` 仍参加 Compose layout（布局），需要 `Modifier` 给出尺寸；
- `onDraw` 在 drawing phase（绘制阶段）执行，不处于 composition scope（组合作用域）；
- `Canvas` 没有可由 `drawContent()` 绘制的业务子节点；
- `Canvas` 自身不会创建独立 Surface、BufferQueue 或 SurfaceFlinger layer。

在 `onDraw` 中调用 `@Composable` 函数会报错。需要准备字体测量器、图片、Shader、Path 或 `android.graphics.Paint` 时，应在外层组合阶段创建，或使用 `drawWithCache`。

### 2.2 `DrawScope` 包装 Android Canvas

Android 端用 `AndroidCanvas` 包装平台 Canvas。`AndroidComposeView.dispatchDraw(android.graphics.Canvas)` 通过可复用的 `CanvasHolder` 把 framework Canvas 交给 Compose 根节点；`DrawScope.drawIntoCanvas` 把对应的 Compose Canvas 传给绘制回调，`nativeCanvas` 可再取得 `android.graphics.Canvas`。

> 当前源码锚点：[`AndroidCanvas.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/AndroidCanvas.android.kt)、[`AndroidComposeView.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt)。

这层包装不会把每个 `drawRect()` 直接变成一个独立 GPU 调用。标准硬件窗口中的大致路径是：

1. UI Thread（应用主线程）执行 Compose 绘制 lambda；
2. `DrawScope` 把 draw 参数转换为 Android Canvas 调用；
3. framework RecordingCanvas / RenderNode 记录绘制命令；
4. `syncAndDrawFrame()` 把当前 RenderNode 树状态交给 RenderThread；
5. RenderThread 准备树并通过 Skia OpenGL 或 Vulkan pipeline 生成 GPU 工作；
6. App Window buffer 经 BLAST 缓冲提交机制、SurfaceFlinger 系统合成器和 HWC（Hardware Composer，硬件合成器）进入显示。

> 平台源码锚点：[`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)、[Skia OpenGL pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp) / [Vulkan pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)（`android-17.0.0_r1`）。

UI Thread 上的 draw lambda 耗时主要反映 Kotlin 计算、Path/Brush 构造、文本测量、display list 录制和调用开销。draw op 是一条绘制操作；GPU 执行这些操作的时间位于后续 RenderThread/GPU 区间，不能用 draw lambda 的同步耗时替代。

### 2.3 绘制目标决定执行方式

同一套 Compose Canvas API 可以面对不同目标。

| 目标 | 常见行为 | 诊断重点 |
| --- | --- | --- |
| 硬件加速 App Window | UI Thread 录制 display list，RenderThread/GPU 生成窗口 buffer | 绘制录制、RenderThread、GPU、FrameTimeline |
| `Canvas(ImageBitmap)` / software Bitmap | CPU 对 Bitmap 执行软件 Canvas 绘制 | CPU 栅格、Bitmap 分配、内存带宽 |
| `GraphicsLayer` | 录制到独立 RenderNode/display list；按属性决定是否离屏 | 图形层重录、属性更新、离屏面积 |
| `SurfaceView` 或 front-buffer renderer（前缓冲渲染器） | 独立 Surface 与生产节奏 | 自有渲染线程、BufferQueue、图层同步 |

因此，“Compose Canvas 使用 GPU”只对标准硬件目标成立。即使 Activity 窗口开启硬件加速，把同一 View 或 Compose 内容画入 Bitmap 时，当前 Canvas 仍可能是软件 Canvas。

### 2.4 与 View `onDraw()` 的关系

Compose Canvas 与 View `onDraw(Canvas)` 都能进入 Android Canvas/HWUI，但两者的 invalidation（失效后请求重绘）、节点树、图形层管理和状态观察不同。给定相同几何、Paint、目标面积和硬件 Canvas，后半段 Skia/GPU 成本可能接近；UI Thread 录制成本与失效范围仍可能不同。

“Compose Canvas 比 View Canvas 快”或“二者完全等价”都缺少前提。迁移评估要使用相同图形、相同构建类型、相同设备和相同帧指标。

## 3. 三种绘制 Modifier 的语义

### 3.1 `drawBehind`

`DrawBackgroundModifier.draw()` 的顺序是调用自定义 `onDraw()`，再调用 `drawContent()`。它适合背景、装饰线、选中态、网格和不遮挡内容的效果。

`Canvas` 采用的就是这个 `Modifier`。给现有 `Text`、`Image` 或容器增加背景时，直接使用 `drawBehind` 可以少建一个布局节点。

### 3.2 `drawWithContent`

`drawWithContent` 把顺序交给调用方。以下行为都由 `drawContent()` 的位置决定：

- 在自定义绘制之前调用：后续绘制会覆盖业务内容；
- 在自定义绘制之后调用：业务内容会覆盖已有的自定义绘制；
- 不调用：业务内容不会被画出；
- 调用多次：业务内容也会被重复绘制。

遮罩、局部高亮、前景装饰和混合效果常用它。涉及 `BlendMode.Clear`、`DstIn` 等影响目标像素的操作时，还要判断是否需要 `CompositingStrategy.Offscreen`，否则混合操作可能作用到图形层之外已有的窗口内容。

### 3.3 `drawWithCache`

`drawWithCache` 把工作分成缓存构建与实际绘制：

- 缓存构建 block（回调）可以创建 Brush、Shader、Path、`TextLayoutResult`、Stroke 或受管 `GraphicsLayer`；
- `onDrawBehind` / `onDrawWithContent` 返回每次绘制都会执行的 block；
- `size`、density（屏幕密度）、layout direction（LTR/RTL 布局方向）、缓存构建 block 的身份，或该 block 读取的 snapshot 状态变化时，缓存失效；
- 绘制 block 中读取的 snapshot 状态只请求重新绘制，不会重建缓存构建 block。

snapshot 状态是 Compose 可观察状态的一种。静态 Path 和 Brush 适合放在缓存构建 block；进度、alpha（透明度）、指针坐标等高频状态留在返回的绘制 block。

这个折线图示例按画布尺寸和 `samples` 缓存折线路径，只在绘制阶段读取动画进度。

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

这段代码中，`samples` 或 `Modifier` lambda 更新会重建缓存，尺寸变化也会重建 Path；`progress.value` 位于绘制 block，只让绘制失效。每个动画帧仍会重新录制 `drawPath` 和 clip（裁剪）命令；缓存保存的是对象与几何计算结果，不会自动保存上一帧像素。

没有可缓存对象时，`drawWithCache` 会增加 lambda 与缓存管理。简单的单色 `drawRect()` 使用 `drawBehind` 更合适。

### 3.4 坐标、density 与变换

`DrawScope.size` 与绘制 API 使用像素坐标，原点为 `(0, 0)`，x 轴正方向向右，y 轴正方向向下。设计尺寸使用 `dp.toPx()`，与画布大小成比例的图形直接基于 `size` 计算。

`translate`、`rotate`、`scale`、`inset` 和 `withTransform` 只改变当前绘制的坐标，不改变节点在布局阶段报告的宽高。图形变换后越过 `bounds`（节点矩形边界）时，是否可见取决于父级裁剪、图形层、离屏范围和窗口边界。视觉位置变化还要与输入区域、语义和相邻布局一起验证。

## 4. 状态读取决定重启哪个阶段

Compose 会记录 snapshot 状态在哪个 restart scope（可重启作用域）中被读取。状态变化后，系统从对应阶段重新执行必要工作。

| 读取位置 | 状态变化后的最小工作范围 | 例子 |
| --- | --- | --- |
| Composable 函数体 | Composition，必要时继续 Layout/Drawing | 在 `Modifier` 参数外读取 `colorState.value` |
| placement lambda（放置回调） | Layout placement 与 Drawing | `Modifier.offset { ... }` |
| `Canvas` / `drawBehind` / `drawWithContent` | Drawing | 在绘制 lambda 内读取动画颜色 |
| `graphicsLayer {}` | 图形层属性更新 | 在 block 内读取旋转角度或 alpha 状态 |
| `drawWithCache` 缓存构建 block | 缓存重建与 Drawing | 用状态生成 Path 或 Shader |

### 4.1 状态的读取位置决定阶段

这两种写法观察同一个状态，工作范围不同：

- 在 Composable 函数体求出 `val color = colorState.value`，再传给 `Modifier`：变化触发 composition；
- 在 `drawBehind { drawRect(colorState.value) }` 内读取：变化只触发 drawing。

高频动画只改变像素而不改变节点结构与尺寸时，延后到绘制阶段读取可以省去 composition 和 layout。若颜色变化还会影响语义、布局或子节点选择，就应在对应的较早阶段读取，不能只为减少重组而隐藏必要更新。

### 4.2 绘制失效仍可能重录 display list

“只触发 drawing”表示 Compose 不需要重跑 composition/layout，但绘制回调和 display list 仍可能更新，已有像素也不会自动增量复用。

当 draw node（绘制节点）失效时，Compose 会重新执行相关绘制 block，并更新对应 display list 或图形层。一个不断增长的 Path 仍可能逐帧重录整条路径。可以采用这些处理方式：

- 把历史笔迹按 segment（路径分段）拆开，只有活动分段高频变化；
- 对过密输入点做有误差界限的简化；
- 把不变背景放进独立图形层；
- 对低延迟墨迹评估 front-buffer（前缓冲）专用方案。

## 5. 对象分配与缓存

### 5.1 DrawScope 已复用内部 Paint

Compose UI 1.12.0 的 `CanvasDrawScope` 有两个延迟创建字段：

- `fillPaint` 用于 Fill；
- `strokePaint` 用于 Stroke。

> 当前源码锚点：[`CanvasDrawScope.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt)。

第一次需要时创建，后续 draw call 复用。因此，使用 `drawRect(color)`、`drawCircle()` 或 `drawPath(..., style = Stroke)` 不会为每次调用新建底层 Paint。

仍需留意这些应用对象：

- 每帧新建复杂 `Path`；
- 每帧生成渐变 Brush/Shader；
- 每帧执行文本测量；
- 每帧构造大的点列表、排序或几何索引；
- `drawIntoCanvas` 中新建 `android.graphics.Paint`、Path、Drawable；
- 每帧创建 Bitmap 或改变 Bitmap 像素。

### 5.2 `remember` 与 `drawWithCache` 的选择

| 对象依赖 | 合适位置 |
| --- | --- |
| 与绘制尺寸无关，且有组合作用域 | `remember(key)` |
| 依赖当前 `size`、density 或 layout direction | `drawWithCache` 的缓存构建 block |
| 每帧变化的标量 | 在绘制 block 中直接读取，不要放进缓存键 |
| 由后台计算的大数据 | ViewModel/worker（工作线程）生成不可变快照，UI 只消费 |
| Android native 绘制对象 | 外层 `remember`，在 `drawIntoCanvas` 中使用 |

这个示例调用只接受 framework Canvas 的旧 `Drawable`，并把对象创建留在组合阶段。

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

这段代码每次绘制只更新 `bounds` 并调用 `Drawable.draw()`，不会新建 Drawable 或 Paint。`drawIntoCanvas` 是兼容入口；已有 `DrawScope` API 能表达的图形优先使用 Compose API，减少平台类型耦合。

### 5.3 缓存不能脱离生命周期

缓存 Path、Bitmap、Shader 或 GraphicsLayer 时还要定义生命周期边界：

- 数据改变时怎样失效；
- size/density 改变时怎样重算；
- 页面离开后怎样释放 native（平台层）/GPU 资源；
- 是否会同时保留旧列表和新几何；
- 多窗口或不同 density 下是否发生错误共享。

大对象保留时间过长，可能用内存压力换取较小的 CPU 节省。缓存策略要结合对象分配、GC（垃圾回收）、图形内存与帧数据验证。

## 6. `graphicsLayer`：display list 隔离与离屏合成

### 6.1 API 29+ 使用公开 RenderNode

Compose UI 1.12.0 的 Android `GraphicsLayerV29`：

- 创建 `RenderNode("graphicsLayer")`；
- 用 `beginRecording()` / `endRecording()` 录制图形层内容；
- 用 `Canvas.drawRenderNode()` 把图形层放进父 Canvas；
- 通过 RenderNode 属性设置平移、缩放、旋转、alpha、裁剪、阴影和 RenderEffect。

> 当前源码锚点：[`GraphicsLayerV29.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt)。

Android 12—17 都走 API 29+ 实现。`graphicsLayer` 仍属于宿主 App Window 的 RenderNode 树，SurfaceFlinger 通常看不到同名的独立图层。

### 6.2 图形层不等于离屏纹理

图形层的基础能力是隔离绘制指令。内容未失效时，父节点变化可以重新引用已有 display list，不必执行子树的 Kotlin 绘制代码。是否把结果栅格化到离屏 buffer，由 compositing（合成）条件决定。

| `CompositingStrategy` | 行为 | 使用边界 |
| --- | --- | --- |
| `Auto` | 由 alpha、效果等属性决定；默认策略 | 通用选择 |
| `Offscreen` | 总是先画到图形层 `bounds` 大小的中间目标 | 遮罩、受控混合、明确需要隔离 |
| `ModulateAlpha` | 把 alpha 调制到各 draw op，通常省去 alpha 离屏 | 内容不重叠且视觉结果允许 |

当前 Android 后端实现还会在这些条件下强制使用离屏合成层：

- `RenderEffect` 非空；
- `blendMode` 不是 `SrcOver`；
- `colorFilter` 非空；
- 显式 `Offscreen`。

`Auto` 下 alpha 小于 1 会创建离屏 buffer；overscroll（越界滚动效果）与 RenderEffect 也会需要离屏。离屏目标通常采用图形层 `bounds`，局部效果不宜包住全屏父节点。

Compose UI 1.12.0 增加了 `LayerOutsets`。它能在 Android 12 及以上扩大图形层的可视边界，避免内容进入离屏 buffer 后被原始边界裁掉；它不改变布局尺寸，也不改变 `clip`、阴影或变换的基准。`outsets` 越大，离屏 buffer 的像素面积越大，应按效果所需范围设置。

### 6.3 `ModulateAlpha` 会改变重叠像素

`ModulateAlpha` 对图形层内每条 draw command（绘制命令）分别应用 alpha。两个图形重叠时，重叠区域会叠加多次，结果与“先把整个图形层画为不透明，再统一乘 alpha”不同。

确认图形层内内容不重叠，或差异符合设计时，才适合用它减少离屏工作。透明文本、阴影、图片和多层图形通常要实机对比。

### 6.4 属性动画使用 lambda overload

`graphicsLayer {}` 允许在 block 内读取 Compose 状态；变化只更新图形层属性，不触发 recomposition（重组）与 remeasure（重新测量）。block 可能被调用多次，内部应只做属性赋值。

这个示例旋转一份内容不变的图标。

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

这段代码在 `angle.value` 变化时更新 RenderNode rotation（旋转）属性；图标内容没有失效时，无需重跑绘制 block。RenderThread/GPU 仍要在每个可见动画帧合成变换后的图形层。

### 6.5 多层嵌套的成本

每个 `graphicsLayer` 至少增加 RenderNode、属性同步、几何变换/裁剪处理和 display list 引用。触发 offscreen（离屏渲染）时，还会增加中间 render target（GPU 渲染目标）、清理、栅格化与采样。

嵌套数量本身没有通用安全阈值。评审时检查：

- 哪些层只为一个默认属性而存在；
- 多个相邻变换能否放进同一层；
- 离屏图形层的像素面积；
- 子内容是否每帧失效，导致缓存价值消失；
- alpha、模糊、阴影与混合是否叠加多个 pass；
- 图形层是否扩大裁剪或越界绘制范围。

## 7. 离屏、BlendMode、模糊与阴影

### 7.1 `saveLayer()` 与 Offscreen 都产生中间结果

硬件加速 Canvas 的 `saveLayer()`、`CompositingStrategy.Offscreen`、RenderEffect 和某些 alpha/混合路径都可能生成 GPU 中间目标，不应描述为 CPU Bitmap 缓存。

中间目标常见成本包括：

- 按 `bounds` 分配或复用 render target；
- 清理目标；
- 把内容栅格化一次；
- 再采样并合成到父目标；
- 增加 GPU 内存与带宽；
- 大范围模糊还会扩大采样区域或增加 pass。

使用 `saveLayer()` 时应给出满足效果的最小 `bounds`。全屏透明层、全屏模糊和多个嵌套遮罩会把局部视觉效果扩大为整屏像素工作。

### 7.2 BlendMode 要先定义作用域

`BlendMode.Clear`、`DstIn`、`SrcIn` 等需要明确与哪些像素混合。没有离屏隔离时，操作可能影响父 Canvas 已有内容；使用 `Offscreen` 可以把影响限制在当前图形层 `bounds`。

不要为所有混合操作固定使用 Offscreen。简单的 `SrcOver`、不重叠 alpha 或普通裁剪可能不需要中间目标。正确性可用对照截图验证，性能再用 GPU 与帧数据判断。

### 7.3 渐变与 RuntimeShader

AGSL 是 Android Graphics Shading Language（Android 图形着色语言）。大面积渐变和 AGSL 的成本取决于覆盖像素数、shader（着色器）指令复杂度、采样次数、精度与后端/驱动。Shader 对象和不变 uniform（着色器参数）应缓存，每帧只更新动态 uniform。

`android.graphics.RuntimeShader` 从 API 33 提供。这个示例缓存 shader 与 brush，在 `size` 改变时更新 `resolution`，动画时间只在绘制阶段写入。

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

这段代码要求 API 33，并应在低版本提供普通 Brush 作为降级方案。它避免每帧编译 AGSL 或新建 Shader；全屏 `drawRect` 仍会执行每个 fragment（片元，最终对应待计算像素）的着色工作，缓存对象不会降低逐像素数学成本。

## 8. Bitmap 与 Canvas 的互操作

### 8.1 Hardware Bitmap 适合作为只读绘制源

`Bitmap.Config.HARDWARE` 从 API 26 提供，像素位于图形内存且 Bitmap 永远不可变。它适合解码后只用于显示的图片：

- 可以包装为 Compose `ImageBitmap` 并画到标准硬件 Canvas；
- 不能作为可变 Bitmap 继续写像素；
- 不能作为 `Canvas(bitmap)` 的可写目标；
- 也不能作为图片源画到 software Canvas；
- 需要读回像素、软件滤镜或画入 Bitmap 时，应选择软件内存分配或显式复制。

Hardware Bitmap 不保证任何场景都零拷贝。缩放、颜色空间转换、采样、RenderEffect、离屏图形层与窗口合成都可能增加 GPU 工作。

### 8.2 频繁修改软件 Bitmap 会引入上传

如果应用每帧在 CPU Bitmap 上改像素，再把它画进硬件窗口，HWUI 需要让更新后的内容对 GPU 可见，可能产生纹理上传和同步。动态图表、粒子或墨迹通常应直接录制矢量绘制命令；复用像素结果能减少更多工作时，再考虑 Bitmap 像素缓存。

### 8.3 `drawImage` 仍要控制解码与目标尺寸

Canvas 不负责替应用选择合适的解码尺寸。大图缩到很小仍会占用解码内存和采样带宽。图片加载应在解码阶段设置目标尺寸、颜色空间和 allocator（像素存储分配方式），详见 22.26。

## 9. 常见自定义绘制场景

### 9.1 图表

图表适合 Compose Canvas，因为大量图元可以放在一个 layout node（布局节点）中。可以按这个顺序优化：

1. 数据排序、聚合与坐标索引放到数据层或缓存构建阶段；
2. Path、网格 Brush、Stroke 和文字测量按数据与 `size` 缓存；
3. 只生成当前 viewport（可视区域）内的点和标签；
4. 手势状态在绘制或 placement（放置）阶段读取；
5. 大数据更新使用不可变快照，避免 draw 时遍历正在修改的集合；
6. 用 Macrobenchmark（针对完整应用场景的 Jetpack 基准测试）固定缩放、拖动和 fling（惯性滚动）场景。

Canvas 减少了 Composable 节点数量，但 draw op 数量、Path 复杂度和文字栅格成本仍在。

### 9.2 粒子与动画背景

一个 Canvas 画多个粒子通常比为每个粒子创建 Composable 更轻。仍需控制：

- 活跃粒子数量与屏幕外剔除；
- 每帧对象分配；
- 随机数、碰撞和物理计算；
- 透明 overdraw（同一像素在一帧内被重复绘制）；
- 大面积模糊、阴影与混合；
- UI Thread 录制时间。

粒子状态可以在后台计算后提交不可变帧快照，但 Canvas 绘制 block 本身由 Compose 绘制阶段调用，不能随意迁移到后台线程。需要独立的生产节奏或更重的 GPU 管线时，应评估 SurfaceView、OpenGL/Vulkan 或专用引擎。

### 9.3 墨迹与手写

普通表单签名可以用 Canvas：

- 合并同一指针事件携带的历史采样点；
- 按 stroke/segment（笔画/路径分段）保存 Path；
- 活动笔画高频更新，已完成笔画分组缓存；
- 缩小无效区域和对象分配；
- 在后台做保存、压缩与矢量简化。

专业手写关注触笔到像素显示的总延迟。`CanvasFrontBufferedRenderer` 使用 SurfaceView、front buffer（前缓冲）与 multi buffer（多缓冲），并在内部渲染线程回调，适合评估低延迟路径。它会引入独立图层、Surface 生命周期、transaction（提交事务）和 tearing（画面撕裂）等权衡，不能当成普通 Compose Canvas 的透明替换。

### 9.4 动态全屏 Shader

RuntimeShader 适合连续程序化背景，但应准备：

- API 32 及以下的降级方案；
- 编译失败或设备不兼容时的降级方案；
- 不同分辨率与刷新率的压力测试；
- 低功耗或减少动态效果模式；
- shader uniform 与时间基准；
- 大面积离屏、RenderEffect 和多重采样检查。

减少 Kotlin 分配不会消除 shader 的 GPU 成本。Perfetto 要同时查看应用帧、RenderThread、GPU frequency/queue（频率与任务队列）和设备热状态。

### 9.5 自定义绘制仍要提供语义

Canvas 中的线、点、柱和图标不会自动成为独立语义节点。纯装饰可以由父组件描述；表达业务信息或响应点击时，应使用带 `contentDescription` 的 Canvas overload（重载）、`Modifier.semantics`、custom action（自定义无障碍操作），或为可交互元素提供可访问的 Compose 节点。

一张图表画得更快，却让读屏服务无法获得数据，不能算完成优化。语义节点数量也应按可操作信息设计，避免为每个装饰像素创建节点。

## 10. 何时转向 SurfaceView

| 需求 | Compose Canvas | SurfaceView / 前缓冲 / 原生生产者 |
| --- | --- | --- |
| 图表、装饰、有限动画 | 合适，容易与 UI 布局和语义协作 | 通常增加不必要的复杂度 |
| 与 UI 同步刷新的 shader | 可用，应测量 UI 录制与 GPU | 全屏高负载且需独立调度时再评估 |
| 视频、相机、外部 decoder（解码器） | 不适合作为持续像素生产者 | SurfaceView 更符合独立 buffer 语义 |
| 专业手写低延迟 | 普通签名可用 | 前缓冲路径更适合低延迟目标 |
| 游戏或大量持续 GPU 工作 | UI overlay 可保留 Compose | 主体使用 EGL/Vulkan/引擎 |
| 需要独立渲染线程 | 绘制 block 仍由 Compose 绘制阶段调用 | 独立生产者可自行调度 |

SurfaceView 会创建独立 SurfaceControl layer，并带来 Z-order（图层前后顺序）、同步、生命周期、截图和无障碍协调。TextureView 把外部 buffer 再采样进宿主窗口，也不是默认的性能升级。选择要依据像素生产者、刷新节奏与合成需求。

## 11. 性能工具：分别量 UI 录制、RenderThread 与 GPU

### 11.1 Macrobenchmark 作为回归入口

`FrameTimingMetric` 是 Macrobenchmark 的帧时间指标，提供：

- API 31+ 的 `frameOverrunMs`，表示超出帧截止时间的毫秒数；
- UI Thread 与 RenderThread 相关的 `frameDurationCpuMs`；
- `frameCount`，用于识别无效帧数量变化。

Canvas 性能场景应固定输入轨迹、数据、动画时长、viewport、图片缓存和 shader warmup（预热）。目标应用应允许性能分析（profileable）且不是调试构建（non-debuggable），并保留每轮 trace。

### 11.2 Perfetto 没有稳定的 Canvas 单节点事件

Perfetto trace 是按时间记录系统与应用事件的性能轨迹。Compose 1.12.0 的 `AndroidComposeView.dispatchDraw()` 带有 `AndroidOwner:draw` 事件，但它覆盖根节点绘制与 dirty layer（待更新图形层）处理，不等于某个 Canvas 的耗时。

[Composition Tracing](22-compose-compiler-recomposition-diagnostics.md) 记录 Composable 在组合阶段的执行时序，不会自动给每个绘制 Modifier 的函数体或 GPU draw op 建立 slice（带起止时间的区间事件）。两类 trace 不能混用。

定位按层次进行：

1. 在 FrameTimeline（关联计划帧与实际帧的时间线）中找到目标 App SurfaceFrame（应用 Surface 对应的一帧）；
2. UI Thread 查看 `Choreographer#doFrame`、Traversal（View 树遍历）、`AndroidOwner:draw` 与自定义 marker（追踪标记）；
3. 检查绘制区间里的 GC、锁、Binder、I/O 和线程调度状态；
4. RenderThread 查看 `DrawFrame`、buffer 出队/入队与 GPU completion（完成时刻）；
5. 结合 GPU 轨道、频率和 render stage（渲染阶段）判断 shader、像素填充、纹理与离屏 pass；
6. App 按时完成后，继续检查 SurfaceFlinger actual timeline（实际时间线）与 present（送显时刻）。

不存在的 `FrameTimeslice` 不应出现在查询或监控协议中。内部 slice 名会随 Compose/HWUI 版本变化，录制后先确认当前 trace。

### 11.3 自定义 trace 只测 draw recording

可以在一个耗时已经确认偏高的绘制 block 外围使用 `androidx.tracing`，名称保持固定且不含动态数据。该 slice 记录 UI Thread 执行 lambda 与录制命令的实际经过时间，不能代表 GPU 执行时间。

不要给每个 draw primitive（基础绘制操作）添加 marker。大量 trace event 会改变被测代码的耗时和 trace 体积。

### 11.4 Layout Inspector 的边界

Layout Inspector 可以检查 Compose tree（节点树）、图形层、recomposition/skip（重组/跳过）计数和 `Modifier` 顺序。它不统计绘制失效次数，也不提供每个 Canvas 的 GPU 时间。正式计时要关闭 Inspector，再用接近发布配置的构建复测。

### 11.5 Baseline Profile 的边界

Baseline Profile 可以覆盖图表页面、Canvas 绘制代码、数据准备和交互路径，引导 ART 对包含的方法做 AOT 优化。它不能改善：

- 过大的 Path 或 draw op 数量；
- 全屏 overdraw；
- GPU shader 指令；
- Bitmap 上传；
- RenderEffect/Offscreen 带宽；
- SurfaceFlinger 或驱动等待。

生成 profile 后要用 `CompilationMode.Partial` 等对应生产条件验证，不能用“已经依赖 Profile Installer”代替测量。

## 12. Android 12—17 的版本边界

### Android 12 / API 31

标准 Compose Canvas 已经运行在 Android View/HWUI 路径上。API 31 提供公开 RenderEffect，模糊等效果更容易实现，也更容易引入离屏 pass。Compose UI 1.12.0 的 `LayerOutsets` 也只在 Android 12 及以上支持。FrameTimeline 可用于现代帧诊断。

### Android 13 / API 33

公开 `RuntimeShader` 让 AGSL 可用于 Compose `ShaderBrush`。Hardware Bitmap 仍是只读绘制源；shader 与 bitmap 都位于图形侧，也要计算目标面积、采样和颜色空间转换成本。

### Android 14 / API 34

公开 `HardwareBufferRenderer` 提供 `RenderNode → HardwareBuffer` 的离屏 HWUI 能力。它用于明确的离屏生产，不会替换普通 Compose Canvas 的宿主窗口路径。

### Android 15 / API 35

Canvas/RenderNode/HWUI 主路径延续。设备刷新率、frame-rate hint（帧率提示）、GPU 后端与厂商驱动可能改变结果，跨版本比较要固定设备和应用构建。

### Android 16 / API 36

没有需要把 Compose Canvas 改写成独立 Surface 的公开架构变化。Compose artifact（库制品）继续独立更新，平台升级测试必须同时记录 Compose 版本。

### Android 17 / API 37

当前固定 tag 中：

- `AndroidComposeView` 仍在 `dispatchDraw()` 接收 framework Canvas；
- framework 硬件绘制仍使用 RecordingCanvas/RenderNode/display list；
- `DrawFrameTask` 与 `CanvasContext` 仍把树状态交给 HWUI RenderThread；
- Skia OpenGL 与 Vulkan pipeline 源码都存在；
- 最终 App Window buffer 仍经过 BLAST、SurfaceFlinger 与 HWC。

因此，不能声称 Android 17 为 Compose Canvas 固定切换 Vulkan，或固定更改 Skia GPU 线程模型。实机后端应结合设备配置、trace、dumpsys 和驱动证据确认。

## 13. 评审清单

- Android platform 是否固定为 `android-17.0.0_r1`，Compose UI 是否单独固定为 1.12.0；
- 是否把 `Canvas` 说明为 `Spacer + drawBehind`，并为它提供明确尺寸；
- 是否把标准硬件 Canvas 的 UI Thread 录制与 RenderThread/GPU 执行分开；
- 是否根据目标 Canvas 判断硬件或软件路径；
- `drawWithContent` 是否在正确位置调用且只调用所需次数的 `drawContent()`；
- 简单绘制是否避免无意义的 `drawWithCache`；
- Path、Brush、Shader、Stroke 和文本测量是否按尺寸与状态正确缓存；
- 高频状态是否在绘制 block 读取，避免每帧重建缓存；
- 是否错误地把绘制阶段重启理解为增量保存上一帧像素；
- 是否知道 DrawScope 已复用内部 fill/stroke Paint；
- `android.graphics.Paint`、Drawable 和 Path 是否在绘制回调外创建；
- `graphicsLayer` 是否用于明确需要的隔离、变换或效果；
- 是否误把 RenderNode/display list 图形层当作固定离屏纹理；
- alpha、RenderEffect、blend、color filter 和 Offscreen 是否扩大中间目标；
- 使用 `ModulateAlpha` 时内容是否存在重叠；
- 多层嵌套是否产生重复离屏、模糊、阴影或大面积透明合成；
- `LayerOutsets` 是否只扩到效果所需范围，避免放大离屏像素面积；
- Hardware Bitmap 是否只作为不可变绘制源；
- 是否每帧修改 software Bitmap 并触发上传；
- RuntimeShader 是否只在 API 33+ 使用，并有低版本降级方案；
- shader 是否缓存，动态 uniform 是否在绘制阶段更新；
- 图表是否只处理 viewport 内的数据，文本和 Path 是否缓存；
- 墨迹是否按 segment 管理，低延迟需求是否评估前缓冲；
- Canvas 中的重要信息与操作是否提供语义；
- 是否把 SurfaceView/TextureView 当成无条件优化；
- Macrobenchmark 是否使用 profileable、non-debuggable 构建和固定脚本；
- Perfetto 是否从 FrameTimeline 关联 UI、RenderThread、GPU 和送显时刻；
- 是否删除了不存在的 `FrameTimeslice` 假设；
- Layout Inspector 计数是否没有被误当成 draw/GPU 计时；
- Baseline Profile 是否覆盖目标用户路径，并与 GPU/带宽优化分开；
- 内核结论是否止于 `android17-6.18-2026-06_r6` 的标准机制，没有推断设备 GPU 驱动策略。

## 14. 结论

Compose Canvas 在 Android 上沿用 Canvas、RenderNode 和 HWUI 路径。`Canvas` 是一个带 `drawBehind` 的 Spacer；`DrawScope` 提供绘制接口并复用内部 Paint；AndroidComposeView 再把命令送入宿主窗口的 display list。

性能分析要区分三段：UI Thread 的几何计算与录制、RenderThread 的树准备与 Skia 提交、GPU 的像素和离屏工作。`drawWithCache` 处理对象与几何复用，`graphicsLayer` 处理指令隔离和属性变换；它们都不会自动减少复杂 Path、全屏 shader 或多重离屏的像素成本。

Android 17 没有 Compose Canvas 专属显示管线。分析时应固定 Compose 与平台版本，控制状态读取阶段和缓存失效范围，再用 Macrobenchmark 与 Perfetto 沿 FrameTimeline、UI Thread、RenderThread、GPU、SurfaceFlinger 逐段验证。

## 参考资料

- [Graphics in Compose](https://developer.android.com/develop/ui/compose/graphics/draw/overview)：Canvas、DrawScope、坐标、Path、文本、图片和 `drawIntoCanvas`。
- [Graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)：`drawBehind`、`drawWithContent`、`drawWithCache`、图形层与合成策略。
- [Jetpack Compose phases](https://developer.android.com/develop/ui/compose/phases)：Composition、Layout、Drawing 的状态读取与重启范围。
- [Brush and RuntimeShader](https://developer.android.com/develop/ui/compose/graphics/draw/brush)：AGSL `RuntimeShader`、`ShaderBrush` 与 API 33 边界。
- [Compose UI release notes](https://developer.android.com/jetpack/androidx/releases/compose-ui)：Compose UI 各版本变化与 `LayerOutsets` 引入记录。
- [Google Maven：Compose UI 版本元数据](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui/maven-metadata.xml)：核对 1.12.0 稳定版与 1.13.0-alpha01 预览版。
- [`LayerOutsets` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/graphics/LayerOutsets)：扩大图形层可视边界的语义与限制。
- [`Canvas.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt)：`Spacer(modifier.drawBehind(onDraw))` 实现。
- [`DrawModifier.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/draw/DrawModifier.kt)：绘制 Modifier 顺序、缓存失效与 `CacheDrawScope`。
- [`CanvasDrawScope.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt)：内部填充/描边 Paint 的延迟创建与复用。
- [`AndroidCanvas.android.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/AndroidCanvas.android.kt)：framework Canvas 包装、`CanvasHolder` 与 `nativeCanvas`。
- [`GraphicsLayerModifier.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/graphics/GraphicsLayerModifier.kt)：图形层属性、状态读取、placement 与 `LayerOutsets`。
- [`GraphicsLayerV29.android.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt)：RenderNode 录制、合成策略与强制离屏条件。
- [`AndroidComposeView.android.kt`（Compose 1.12.0 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt)：`dispatchDraw()`、`AndroidOwner:draw` 与待更新图形层。
- [`Canvas.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt)：保留旧版 `Canvas` 实现锚点。
- [`DrawModifier.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/draw/DrawModifier.kt)：保留旧版绘制节点锚点。
- [`CanvasDrawScope.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt)：保留旧版 Paint 复用锚点。
- [`AndroidCanvas.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/AndroidCanvas.android.kt)：保留旧版 Canvas 包装锚点。
- [`GraphicsLayerModifier.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/commonMain/kotlin/androidx/compose/ui/graphics/GraphicsLayerModifier.kt)：保留旧版图形层 Modifier 锚点。
- [`GraphicsLayerV29.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt)：保留旧版 Android 图形层锚点。
- [`AndroidComposeView.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt)：保留旧版宿主 View 锚点。
- [Android hardware acceleration](https://developer.android.com/topic/performance/hardware-accel)：hardware Canvas 的 display list 模型、View layer 与 `saveLayer()` 边界。
- [`RecordingCanvas.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RecordingCanvas.java)：Android 17 framework 硬件绘制录制入口。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp) 与 [`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：UI Thread 到 RenderThread 的同步、树准备与绘制。
- [Skia OpenGL pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp) 与 [Skia Vulkan pipeline](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp)：Android 17 tag 中并存的 HWUI backend。
- [FrameTimingMetric](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric) 与 [FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：帧回归 metric 和 App/SF 时序分析。
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)：ART AOT 覆盖范围与 Profile Installer 边界。
- [`Bitmap.Config.HARDWARE`](https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE)：Hardware Bitmap 的不可变与只读显示语义。
- [`CanvasFrontBufferedRenderer`](https://developer.android.com/reference/androidx/graphics/lowlatency/CanvasFrontBufferedRenderer)：SurfaceView front/multi-buffer 低延迟绘制路径。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线；Compose Canvas 没有专属 kernel API。

### 旧版本参考锚点

以下链接保留用于核对 Compose 1.11.4（含 BOM 2026.06.00）到 1.12.0 的实现差异；正文版本边界仍以文中说明为准。

- [`Canvas.kt`（Compose 1.11.4 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/foundation/foundation/src/commonMain/kotlin/androidx/compose/foundation/Canvas.kt)
- [`CanvasDrawScope.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/commonMain/kotlin/androidx/compose/ui/graphics/drawscope/CanvasDrawScope.kt)
- [`AndroidCanvas.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/AndroidCanvas.android.kt)
- [`GraphicsLayerV29.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui-graphics/src/androidMain/kotlin/androidx/compose/ui/graphics/layer/GraphicsLayerV29.android.kt)
- [`AndroidComposeView.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt)
