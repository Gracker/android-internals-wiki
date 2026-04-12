---
title: "过度绘制"
chapter: "2.8"
status: ready-for-review
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
applicable_versions: "Android 4.2 (API 17) - Android 16"
last_verified: "2026-04-12"
last_verified_against: "AOSP android-16.0.0_r1"
drafted_date: "2026-03-30"
confidence: high
reviewed_date: "2026-04-12"
reviewed_by: openclaw-task6
task6_result: needs-rework
task2b_result: fixed
sources:
  - type: blog
    path: "Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md"
  - type: blog
    path: "Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md"
  - type: official
    path: "developer.android.com/topic/performance/rendering/overdraw"
  - type: official
    path: "developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "developer.android.com/reference/android/graphics/Canvas#clipRect"
  - type: official
    path: "developer.android.com/reference/android/graphics/Canvas#quickReject"
  - type: official
    path: "developer.android.com/develop/ui/views/graphics/hardware-accel"
  - type: official
    path: "developer.android.com/training/improving-layouts/optimizing-layout"
  - type: official
    path: "developer.android.com/studio/profile/monitor"
  - type: official
    path: "developer.android.com/studio/debug/layout-inspector"
  - type: official
    path: "developer.android.com/develop/ui/compose/graphics/draw/modifiers"
tags: [overdraw, GPU, rendering, clipRect, quickReject, 性能优化, Compose, DisplayList, LayoutInspector, AGI]
related_chapters: ["2.1", "2.4", "2.5", "7.2"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task9_result: needs-rework
---

# 过度绘制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 过度绘制的定义：同一像素在一帧内被绘制多次
- 🔹 过度绘制的性能影响：GPU fill rate 消耗、内存带宽浪费
- 🔹 检测方法：开发者选项中的 GPU 过度绘制调试工具，以及 Layout Inspector / Profile GPU Rendering / Perfetto 的配合方式
- 🔹 常见过度绘制原因：多层背景叠加、不必要的全屏绘制、透明区域
- 🔹 优化手段：移除多余背景、clipRect、减少层级、自定义 View 的 canvas 裁剪与可见性判断

### 扩展（可选深入）

- 🔸 Compose 中过度绘制的特点与排查
- 🔸 Perfetto / FrameTimeline / AGI 中如何继续确认 GPU 侧瓶颈

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要关注过度绘制

打开 Android 设备的开发者选项，启用“调试 GPU 过度绘制”后，屏幕上会覆盖一层彩色滤镜。蓝色、绿色、粉色、红色分别对应不同的重复绘制层级。这些颜色不是 UI 本身。系统用它们标记每个像素被绘制的次数。红色越多的区域，说明 GPU 在做更多无用功。如果一个像素被绘制了四次、五次，而用户最终只能看到最上面那一层的结果，那么前面几次绘制就是纯粹的浪费。

过度绘制（Overdraw）指的是屏幕上同一像素在一帧内被绘制了多次。在一个典型的 Android 应用中，界面由多层 View 叠加组成，Window 背景层、Activity 布局层、Fragment 层、各种 ViewGroup 和 View 依次叠加。如果每一层都绘制了背景，那么最底层那个被完全遮挡的背景就是在做无用功。

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

## 过度绘制怎么影响性能

GPU 的 fill rate（像素填充率）是有上限的。当过度绘制严重时，GPU 需要填充的像素总量会明显高于屏幕的实际像素数。以一台 1080 × 2400 分辨率的手机为例，一帧需要填充约 260 万个像素。如果整屏平均 3x 过度绘制，GPU 实际要处理 780 万个像素，其中约 520 万个像素写入会被后续图层覆盖。

过度绘制带来的耗时也不是线性增加的，还要看 GPU 当时有没有余量。如果 GPU 本来就很快，渲染一帧只用了 5 ms，那即使有 3x 过度绘制，总耗时也可能只是 8 ms，仍然落在 16.6 ms 的 VSync 周期内，用户未必能感知到卡顿。真正危险的是 GPU 已经接近满负载的场景，比如低端设备，或者界面本身就包含大量透明混合、自定义绘制和复杂阴影。这时过度绘制可能把单帧耗时从 15 ms 推到 20 ms 以上，直接跨过当前刷新周期的预算，出现肉眼可见的掉帧。

内存带宽是另一个容易被忽视的瓶颈。每一次像素写入都要占用内存带宽，而移动设备的内存带宽是有限的。当过度绘制严重时，GPU 和 CPU 争抢内存带宽，可能连累 CPU 的性能表现，导致整个系统的响应变慢。

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

## 检测工具：从颜色到证据

### 开发者选项：GPU 过度绘制调试

这是最直观的检测手段。打开路径：**设置 → 开发者选项 → 调试 GPU 过度绘制 → 显示过度绘制区域**。启用后，整个屏幕会覆盖一层颜色滤镜，每种颜色代表不同程度的过度绘制：

| 颜色 | 过度绘制次数 | 含义 |
|------|-------------|------|
| 原色（无叠加） | 0x | 每个像素只绘制一次，理想状态 |
| 蓝色 | 1x | 像素被绘制了 2 次，轻微浪费 |
| 绿色 | 2x | 像素被绘制了 3 次，需要关注 |
| 粉色 | 3x | 像素被绘制了 4 次，需要优化 |
| 红色 | 4x+ | 像素被绘制了 5 次以上，严重浪费 |

[图：GPU 过度绘制调试颜色叠加示例，展示蓝/绿/粉/红各层次覆盖效果]

更稳妥的工程判断是，优先处理任何连续的红色区域，以及会跟随滚动、动画一起移动的大片粉色区域。“粉色区域不超过屏幕 1/4”更适合作为团队经验阈值，不适合当作官方标准。

这个工具从 Android 4.2（API 17）开始提供。早期版本中还能在状态栏显示一个数值型的过度绘制倍率，比如“2.35x”，但在 Android 5.0 之后这个数值显示被移除了，只保留了颜色叠加视图。

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

### 把颜色图、柱状图和 Trace 串起来

Perfetto 不会直接告诉我们“这里有 3x 过度绘制”。它给的是帧预算、线程 slice 和 Layer 时间线，所以更适合做二次确认，判断这块重复填充有没有把 GPU 压到帧预算之外。

一条更实用的观测链如下：

1. **Debug GPU Overdraw**：先用颜色图锁定问题区域，确定是整屏背景、列表 Item、半透明蒙层，还是局部阴影。
2. **Profile GPU Rendering**：再看问题操作发生时的柱状图。官方文档说明它展示的是一帧各阶段的渲染耗时。如果颜色图已经很重，同时柱状图长期贴近或跨过帧预算线，GPU 填充压力就需要继续往下追。
3. **Perfetto / FrameTimeline（Android 12+）**：在 App 侧对照同一 Layer 的 **Expected Timeline** 和 **Actual Timeline**，再看该进程的 `doFrame` 与 `RenderThread` slice。Perfetto 文档明确说明，FrameTimeline 会把 App 侧 `doFrame`、`RenderThread` 和 SurfaceFlinger 的帧时间线串起来。如果 UI 线程没有明显堵塞，但 `Actual Timeline` 持续晚于 `Expected Timeline`，同时 `RenderThread` 的 `DrawFrame` 或相关 HWUI slice 被拉长，问题更像 GPU 侧。
4. **AGI**：当我们要继续追到单帧和 draw call 级别时，再用 Android GPU Inspector 抓一帧。AGI 官方站点说明它支持系统 trace、单帧 capture 和逐 draw call 分析，这一步适合确认到底是哪一层背景、阴影或透明 pass 在反复覆盖同一块像素。

如果设备能导出 GPU counter，再补看 GPU busy、fragment 相关计数或厂商 GPU counter 是否在同一时段一起抬高。没有这些 counter 也没关系，颜色图、柱状图和 FrameTimeline 已经足够先把问题归到 GPU 侧。

[图：同一段滚动操作里，先用 Debug GPU Overdraw 标出列表区域的粉色块，再在 Perfetto 中对照该 Layer 的 Expected Timeline / Actual Timeline 与 App 进程 RenderThread slice]
[待补充：真实 Perfetto FrameTimeline / AGI frame capture 截图]

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [已验证: 官方文档, developer.android.com/topic/performance/vitals/render] [已验证: Perfetto 文档, perfetto.dev/docs/data-sources/frametimeline] [已验证: 官方站点, gpuinspector.dev]

### 当前主线工具与历史工具

当前的主线工具链是 **Layout Inspector + Debug GPU Overdraw + Profile GPU Rendering + Perfetto / AGI**。Layout Inspector 用来确认 View 或 Composable 的叠层关系，颜色图用来确认像素是否被重复填充，Profile GPU Rendering 用来判断帧预算压力，Perfetto / AGI 负责继续下钻到 FrameTimeline、RenderThread 和 draw call。

如果我们在旧博客或旧分享里看到 **Hierarchy Viewer**、**Tracer for OpenGL ES**、**Android Device Monitor**，要先把它们当成历史名词。Android 官方文档已经写明，Android Device Monitor 在 Android Studio 3.1 废弃、3.2 移除。Hierarchy Viewer 的替代工具是 Layout Inspector，Tracer for OpenGL ES 也不该再作为当前 Android Studio 工具链来推荐。

[已验证: 官方文档, developer.android.com/studio/profile/monitor] [已验证: 官方文档, developer.android.com/studio/debug/layout-inspector] [已验证: 官方站点, gpuinspector.dev]

## 常见的过度绘制来源

过度绘制不会凭空出现，它总是来自于 UI 层级中某些不必要的设计。我们逐个分析最常见的几种来源。

### 1. Window 默认背景

每个 Activity 的 Window 都有一个默认背景。这个背景由 Activity 的主题（Theme）决定，通常是一个不透明的颜色或 drawable。当我们在 Activity 的布局根节点又设置了自己的背景时，Window 的默认背景就被完全遮挡了，但它仍然被绘制了一次。

在实际优化案例中发现了一个典型案例：文件管理器应用的 ActionBar 和内容区域整体呈现蓝色（1x 过度绘制），追踪后发现是整个 Window 的主题背景导致的。这个背景在所有内容之下，被完全覆盖，没有任何视觉贡献。

解决方法是透明化 Window 背景：

```java
// 在 Activity.onCreate() 中
getWindow().setBackgroundDrawableResource(android.R.color.transparent);
```

或者在主题中直接设置：

```xml
<style name="MyTheme" parent="...">
    <item name="android:windowBackground">@android:color/transparent</item>
</style>
```

去掉后，整屏的过度绘制层次可以立即下降一级。

[来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md]

### 2. 多层重叠背景

这是最常见的过度绘制来源。考虑一个典型的场景：一个 LinearLayout 设置了白色背景，里面包含一个 RelativeLayout 也设置了白色背景，再里面是 ListView 的 Item 布局又设置了白色背景。用户只能看到最上面那一层白色，但 GPU 需要画三层。

这种层层叠加的背景在复杂布局中非常普遍。当前更实用的排查方法是打开 GPU 过度绘制调试工具，再用 Layout Inspector 对照每个 View 的区域和背景设置。旧资料里经常会提到 Hierarchy Viewer，它适合帮助理解历史案例，但不该再作为当前 Android Studio 的主线工具来使用。

实战排查流程如下：通过 Layout Inspector 定位到 CustomViewBehind 这个 View 设置了不必要的背景色（`R.color.mz_slidingmenu_background_light`），而这个 View 的内容在运行时会被上层完全覆盖。去掉这行代码后，中间区域的过度绘制从绿色（2x）降到蓝色（1x）。

[来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md] [已验证: 官方文档, developer.android.com/studio/debug/layout-inspector]

### 3. Selector 背景的 normal 状态

ListView、RecyclerView 的 Item 经常使用 Selector 作为背景，用于显示按下、选中等状态。但 Selector 的 `normal` 状态如果不设置为透明，就会导致即使没有交互时也绘制了一层不透明的背景色。

解决方法是将 Selector 的 normal 状态设为透明：

```xml
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:state_pressed="true" android:drawable="@color/item_pressed" />
    <item android:drawable="@android:color/transparent" />
</selector>
```

### 4. 透明度和半透明元素

半透明的 View（alpha < 1.0）天然会导致过度绘制，因为 GPU 必须先绘制底层的所有内容，再将半透明层混合上去。这个混合过程不可避免，因为用户最终看到的就是两层内容的混合结果。

对于透明区域，可以做的是：如果某个 View 的部分区域完全透明，比如一个不规则形状的 Drawable，可以用 `clipRect` 限制绘制区域，避免在透明区域浪费 GPU 算力。

## 优化手段

上一节梳理了过度绘制的几种常见来源，下面按常见收益和改动成本来整理对应的优化手段。核心目标没有变化，就是**减少 GPU 对同一像素的重复填充**。

### 移除多余背景

这是最常见、通常也最划算的优化。原则很直接：**如果一个背景会被上层内容完全遮挡，就不要画它。**

实际操作中，自底向上逐层检查：

1. Window 背景：是否与根布局背景重复？如果是，透明化 Window 背景。
2. 根布局背景：是否被子布局完全覆盖？
3. 中间层背景：是否有装饰性但不必要的背景？
4. Selector 背景：normal 状态是否可以设为透明？

### 布局层级扁平化

布局嵌套越深，过度绘制的可能性越大，每一层 ViewGroup 都可能添加自己的背景。使用 Lint 工具可以自动检测到许多布局问题：

- **Useless leaf**：没有子 View 也没有背景的布局，可以移除。
- **Useless parent**：只有一个子 View、没有背景、不是 ScrollView 的布局，可以移除并把子 View 提到上一层。
- **Deep layouts**：嵌套过深的布局，考虑用 RelativeLayout、ConstraintLayout 或 GridLayout 来扁平化。
- **Merge root frame**：如果根 FrameLayout 没有设置背景和 padding，可以用 `<merge>` 标签替代。

[已验证: 官方文档, developer.android.com/training/improving-layouts/optimizing-layout] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

### 自定义 View 中的 clipRect 和 quickReject

当我们在自定义 View 的 `onDraw()` 中绘制多个元素时，系统不知道哪些元素会被其他元素遮挡。如果不做任何处理，所有元素都会被完整绘制，即使部分元素最终被完全覆盖。

`Canvas.clipRect()` 的普通重载只是把后续绘制限制在一个矩形裁剪区，这个语义从早期 Canvas API 就存在。`Canvas.quickReject()` 也是老 API，早期常见的是带 `Canvas.EdgeType` 的重载，它从 API 1 就存在；API 30 起又补了不带 `EdgeType` 的简化重载，并把旧重载标成 deprecated。

因此，这里真正要区分的不是“API 18 之前有没有 `clipRect()` / `quickReject()`”，而是**硬件加速下哪些复杂裁剪操作什么时候才可靠**。Android 的 hardware acceleration 文档把 `clipPath()`、`clipRegion()`、`clipRect(Region.Op.XOR)`、`clipRect(Region.Op.Difference)`、`clipRect(Region.Op.ReverseDifference)` 以及带 rotation / perspective 的 `clipRect()` 标成 API 18 才支持。普通的 `clipRect(left, top, right, bottom)` 不在这条限制里。

先看最常见的普通矩形裁剪：

```java
@Override
protected void onDraw(Canvas canvas) {
    // 限定绘制区域，避免文本溢出到 Item 边界之外
    canvas.clipRect(left, top, right, bottom);
    canvas.drawText(text, x, y, paint);
}
```

再看 `quickReject()`。下面这个写法保留了旧版重载，便于覆盖 API 30 之前的系统；如果应用只面向 API 30+，可以换成不带 `EdgeType` 的简化重载：

```java
private final RectF tmpRect = new RectF();

@Override
protected void onDraw(Canvas canvas) {
    for (Item item : items) {
        tmpRect.set(item.left, item.top, item.right, item.bottom);
        // 如果这个 Item 完全落在当前 clip 之外，直接跳过
        if (!canvas.quickReject(tmpRect, Canvas.EdgeType.AA)) {
            item.draw(canvas);
        }
    }
}
```

`quickReject()` 的意义是，先用当前 clip 和 matrix 粗判这个对象会不会完全落在可见区域之外。如果结果是完全不可见，就连 draw call 都不必继续往后走。对于包含大量子元素的自定义 View，比如自定义列表、图表、游戏界面，这类过滤通常比“先画出来再让 GPU 覆盖掉”更划算。

需要额外注意的是，`clipRect(..., Region.Op)` 和 `clipPath(..., Region.Op)` 这类旧接口在 API 26 开始废弃，P 之后只应继续使用 `INTERSECT` / `DIFFERENCE` 或对应的 `clipOut*` API。复杂 shape clip 本身也可能带来额外开销，所以它更适合做功能性裁剪，不该被当成过度绘制优化的默认解法。

[已验证: 官方文档, developer.android.com/reference/android/graphics/Canvas#clipRect] [已验证: 官方文档, developer.android.com/reference/android/graphics/Canvas#quickReject] [已验证: 官方文档, developer.android.com/develop/ui/views/graphics/hardware-accel]

### ViewStub 延迟加载

对于不是立即需要的布局，比如错误提示页、高级设置面板，使用 `ViewStub` 可以在需要时才 inflate 和绘制，避免这些布局参与初始帧的渲染，同时也减少了它们在不可见时的过度绘制。

## 与其他章节的关系

过度绘制并不是孤立的性能问题，它和渲染管线的多个环节都有交集：

- **2.1 渲染架构全景**：过度绘制发生在 GPU 渲染阶段，是渲染管线中 GPU 执行环节的效率问题。2.1 节对 App 渲染管线和 SurfaceFlinger 合成管线的区分有助于理解过度绘制的定位。
- **2.4 Choreographer 与渲染流水线**：如果过度绘制导致 GPU 执行超时，帧就无法在当前 VSync 周期内完成，产生掉帧。
- **2.5 MainThread 与 RenderThread 协作**：在硬件加速渲染路径下，过度绘制不直接影响 MainThread，但会增加 RenderThread → GPU 的执行时间。
- **7.2 卡顿原因体系**：过度绘制是 GPU 侧导致卡顿的常见原因之一。

## 版本演进

与过度绘制直接相关、且当前能核对的变化主要有下面几类：

- **Android 4.2（API 17）**：开发者选项加入“调试 GPU 过度绘制”。这是日常定位 overdraw 的起点。
- **Android 4.x 到 8.x 的硬件加速支持边界**：`clipPath()`、`clipRegion()`、`clipRect(Region.Op.XOR / Difference / ReverseDifference)` 以及带 rotation / perspective 的 `clipRect()` 从 API 18 起才支持。普通 `clipRect()` 不在这条限制里。
- **Android 8.0（API 26）**：`clipRect(..., Region.Op)`、`clipPath(..., Region.Op)` 这类旧接口开始废弃。P 之后只应继续使用 `INTERSECT` / `DIFFERENCE` 或对应的 `clipOut*` API。
- **Android 12（API 31）起**：Perfetto 的 FrameTimeline 成为定位 jank 的主线工具之一。它不直接显示 overdraw 次数，但能把 App、RenderThread 和 SurfaceFlinger 的帧预算串起来，帮助我们判断过度绘制有没有演变成可见掉帧。
- **Android Studio 3.1 / 3.2 之后**：Android Device Monitor 废弃并移除，Hierarchy Viewer / Tracer for OpenGL ES 退出主线，Layout Inspector 与 AGI 成为当前工具链。

[已验证: 官方文档, developer.android.com/develop/ui/views/graphics/hardware-accel] [已验证: 官方文档, developer.android.com/studio/profile/monitor] [已验证: Perfetto 文档, perfetto.dev/docs/data-sources/frametimeline]

## Jetpack Compose 中的过度绘制

[自动发现: 来源 developer.android.com/develop/ui/compose/graphics/draw/modifiers]

前面讨论的检测手段对 Compose 一样适用。Debug GPU Overdraw 看的是像素重复填充，Layout Inspector 看的是组合树和 layer 结构，必要时再用 Perfetto / AGI 继续下钻。

### 哪些场景会真的增加像素重复填充

Compose 中真正会把 overdraw 颜色图压重的，通常还是下面几类场景：

1. **多层 `Modifier.background()`、`Surface`、`Box` 叠在同一块区域**。外层已经是不透明背景时，里层再画一层同色背景，和 View 系统里的多层 background 属于同一类问题。
2. **`graphicsLayer { alpha < 1f }`、半透明蒙层、阴影与模糊**。Compose graphics modifiers 文档说明，当 layer 的 alpha 小于 1.0f，且没有使用 `CompositingStrategy.ModulateAlpha` 时，内容会先绘制到 offscreen buffer，再合成回目标表面。这会增加一次额外的填充或合成 pass。
3. **裁剪前先画满整块区域**。比如圆角卡片在外层先画整块不透明背景，再在内层叠半透明内容，GPU 仍然要先填满那块矩形，再做后续裁剪和合成。

### 哪些优化不该算作 overdraw 修复

`drawBehind`、`drawWithCache`、`derivedStateOf` 这些 API 有自己的价值，但它们解决的是不同层次的问题。`drawBehind` / `drawWithCache` 影响的是 Compose 的绘制组织方式，`derivedStateOf` 影响的是 state read 和 recomposition 频率。它们可以减少 CPU 侧的重组或重复准备工作，却不等于“同一像素少画了一次”。

排查 Compose 页面时，可以先问两个问题：

- 同一块像素是不是被多层不透明或半透明内容反复覆盖？
- 如果 overdraw 颜色图没有变轻，只是动画或滚动更顺了，那通常是 phase 开销变小，不是 overdraw 指标下降。

[已验证: 官方文档, developer.android.com/develop/ui/compose/graphics/draw/modifiers] [已验证: 官方文档, developer.android.com/studio/debug/layout-inspector]

## 常见问题与误区

### 误区：过度绘制一定能被感知到

过度绘制本身不等于卡顿。如果 GPU 有足够的算力在 VSync 周期内完成所有绘制，那么即使 3x 过度绘制用户也感知不到。过度绘制是一个**潜在的性能风险**，它会降低 GPU 的性能余量，让未来添加更复杂的 UI，或者切到低端设备时更容易出现卡顿。

### 误区：所有蓝色区域都需要优化

蓝色（1x 过度绘制）在大多数应用中不可避免，文字绘制在背景上就是 1x。优化的优先级应该是：红色 > 粉色 > 绿色 > 蓝色。全屏蓝色是一个可以接受的状态，不需要追求零过度绘制。

### 误区：Compose 的 Recomposition 等于过度绘制

Recomposition 是 Compose 在组合阶段重新执行 Composable 函数的过程，过度绘制则是 GPU 在绘制阶段对同一像素的重复填充。两个问题都可能导致帧率下降，但观察工具不同，修复手段也不同。重组次数更多地反映 CPU 侧的 state read 和组合压力，过度绘制颜色图、AGI frame capture 和 GPU 相关轨道反映的是像素填充与合成成本。

## 参考资料

- AOSP 源码路径（早期实现）：`frameworks/base/libs/hwui/OpenGLRenderer.cpp`
- AOSP 源码路径（android-16.0.0_r1，调试开关）：`frameworks/base/libs/hwui/Properties.h`、`frameworks/base/libs/hwui/Properties.cpp`（`debug.hwui.overdraw`）
- [已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw]
- [已验证: 官方文档, developer.android.com/topic/performance/vitals/render]
- [已验证: 官方文档, developer.android.com/reference/android/graphics/Canvas]
- [已验证: 官方文档, developer.android.com/develop/ui/views/graphics/hardware-accel]
- [已验证: 官方文档, developer.android.com/studio/profile/monitor]
- [已验证: 官方文档, developer.android.com/studio/debug/layout-inspector]
- [已验证: 官方文档, developer.android.com/develop/ui/compose/graphics/draw/modifiers]
- [已验证: Perfetto 文档, perfetto.dev/docs/data-sources/frametimeline]
- [已验证: 官方站点, gpuinspector.dev]
- [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]（高爷原创：Android 性能优化之过度绘制 - 理论篇）
- [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md]（高爷原创：Android 性能优化之过度绘制 - 实战篇）
- [引用: https://www.youtube.com/watch?v=URyoiAt8098]（Romain Guy 的优化案例）
