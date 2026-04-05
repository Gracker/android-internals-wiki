---
title: "过度绘制"
chapter: "2.8"
status: ready-to-publish
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
applicable_versions: "Android 4.2 (API 17) - Android 16 (API 36)"
last_verified: "2026-03-30"
last_verified_against: "AOSP android-16.0.0_r1"
drafted_date: "2026-03-30"
confidence: high
reviewed_date: "2026-04-05"
reviewed_by: openclaw-task6
sources:
  - type: blog
    path: "Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md"
  - type: blog
    path: "Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md"
  - type: official
    path: "developer.android.com/topic/performance/rendering/overdraw"
  - type: official
    path: "developer.android.com/reference/android/graphics/Canvas#clipRect"
tags: [overdraw, GPU, rendering, clipRect, quickReject, 性能优化, Compose, DisplayList]
related_chapters: ["2.1", "2.4", "2.5", "7.2"]
---

# 过度绘制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 过度绘制的定义：同一像素在一帧内被绘制多次
- 🔹 过度绘制的性能影响：GPU fillrate 消耗、内存带宽浪费
- 🔹 检测方法：开发者选项中的 GPU 过度绘制调试工具（颜色层次：蓝-绿-粉-红）
- 🔹 常见过度绘制原因：多层背景叠加、不必要的全屏绘制、透明区域
- 🔹 优化手段：移除多余背景、clipRect、减少层级、自定义 View 的 canvas.clipRect/quickReject

### 扩展（可选深入）

- 🔸 Compose 中过度绘制的特点与排查
- 🔸 GPU Profiler 中观察 overdraw 的方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要关注过度绘制

打开 Android 设备的开发者选项，启用"调试 GPU 过度绘制"，我们会看到屏幕上覆盖了一层彩色滤镜——蓝色、绿色、粉色、红色交织在一起。这些颜色不是 UI 的一部分，而是系统在标记每个像素被绘制的次数。红色越多的区域，说明 GPU 在做更多无用功。如果一个像素被绘制了四次、五次，而用户最终只能看到最上面那一层的结果，那么前面几次绘制就是纯粹的浪费。

过度绘制（Overdraw）指的是屏幕上同一像素在一帧内被绘制了多次。在一个典型的 Android 应用中，界面由多层 View 叠加组成——Window 背景层、Activity 布局层、Fragment 层、各种 ViewGroup 和 View 依次叠加。如果每一层都绘制了背景，那么最底层那个被完全遮挡的背景就是在做无用功。

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

## 过度绘制怎么影响性能

GPU 的渲染能力有一个上限——fillrate（填充率），即每秒能填充多少像素。当过度绘制严重时，GPU 需要填充的像素总量远大于屏幕实际像素数。以一台 1080×2400 分辨率的手机为例，一帧需要填充约 260 万个像素。如果整屏平均 3x 过度绘制，GPU 实际要处理 780 万个像素——其中 520 万个是画完就被覆盖的。

但过度绘制的性能影响并不是线性的。关键因素是"GPU 有没有空闲时间"。如果 GPU 本来就很快，渲染一帧只用了 5ms，那即使有 3x 的过度绘制，总耗时可能也就 8ms，仍然在 16.6ms 的 VSync 周期内，用户感知不到卡顿。真正的危险出现在 GPU 已经接近满负载的场景——比如在低端设备上、或者界面本身就很复杂（大量透明度混合、自定义绘制、复杂阴影）的时候。这时过度绘制会成为压垮骆驼的最后一根稻草，让一帧从 15ms 涨到 20ms 以上，产生肉眼可见的掉帧。

内存带宽是另一个容易被忽视的瓶颈。每一次像素写入都要占用内存带宽，而移动设备的内存带宽是有限的。当过度绘制严重时，GPU 和 CPU 争抢内存带宽，可能连累 CPU 的性能表现，导致整个系统的响应变慢。

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

## 检测工具：从颜色到数据

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

一般性的优化验收标准是：控制大部分区域在蓝色以内（2x 以内），不允许存在大面积红色区域，不允许存在面积超过屏幕 1/4 的粉色区域。

这个工具从 Android 4.2（API 17）开始提供。早期版本中还能在状态栏显示一个数值型的过度绘制倍率（比如"2.35x"），但在 Android 5.0 之后这个数值显示被移除了，只保留了颜色叠加视图。

[已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

### 在 Perfetto 中的表现

过度绘制本身不会直接出现在 Perfetto 的某个独立 Track 中，但过度绘制严重的场景会在以下 Track 中留下痕迹：

- **GPU Track**：如果 GPU 渲染某一帧的耗时明显偏长（比如接近或超过 VSync 周期），过度绘制可能是原因之一。可以结合 GPU 渲染分析工具进一步确认。
- **主线程 Track 中的 draw 阶段**：对于软件渲染的 View，`draw()` 操作本身的耗时可能受过度绘制影响。在硬件加速渲染路径中，draw 阶段主要是构建 DisplayList，过度绘制对这一步影响不大——真正的开销发生在 GPU 执行 DisplayList 时。
- **RenderThread Track**：`DrawFrame` 操作中 `syncFrameState` 之后的 GPU 执行阶段耗时可能与过度绘制有关。

[待补充：Perfetto 中 GPU 执行耗时的具体 Track 名称和判断方法]

### 其他检测工具

**Android Studio Layout Inspector** 可以检查 View 层级，帮我们理解哪些 View 叠加在一起导致过度绘制。**Profile GPU Rendering**（开发者选项中的"显示 GPU 渲染分析"）会在屏幕上显示一个柱状图，每一根柱子代表一帧的渲染耗时——如果柱子经常超过绿线（16.6ms），结合过度绘制颜色图就可以判断 GPU 是否因为过度绘制而成为瓶颈。

在实战分析中还可以使用 **Tracer for OpenGL ES** 工具（位于 Android Device Monitor 中），它可以逐帧记录 OpenGL ES 的绘制命令，让我们看到哪些 draw call 是在绘制被完全遮挡的内容。优化前后对比 Tracer 输出，能清晰看到减少的无效绘制命令。

[来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md]

## 常见的过度绘制来源

过度绘制不会凭空出现，它总是来自于 UI 层级中某些不必要的设计。我们逐个分析最常见的几种来源。

### 1. Window 默认背景

每个 Activity 的 Window 都有一个默认背景。这个背景由 Activity 的主题（Theme）决定，通常是一个不透明的颜色或 drawable。当我们在 Activity 的布局根节点又设置了自己的背景时，Window 的默认背景就被完全遮挡了——但它仍然被绘制了一次。

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

这种层层叠加的背景在复杂布局中非常普遍。排查方法是打开 GPU 过度绘制调试工具，然后用 Hierarchy Viewer（或 Layout Inspector）对照查看每个 View 的区域和背景设置。

实战排查流程如下：通过 Hierarchy Viewer 定位到 CustomViewBehind 这个 View 设置了不必要的背景色（`R.color.mz_slidingmenu_background_light`），而这个 View 的内容在运行时会被上层完全覆盖。去掉这行代码后，中间区域的过度绘制从绿色（2x）降到蓝色（1x）。

[来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md]

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

半透明的 View（alpha < 1.0）天然会导致过度绘制，因为 GPU 必须先绘制底层的所有内容，再将半透明层混合上去。这个混合过程是不可避免的——我们不能简单地"跳过"底层绘制，因为最终用户要看到两层内容的混合效果。

对于透明区域，可以做的是：如果某个 View 的部分区域完全透明（比如一个不规则形状的 Drawable），可以用 `clipRect` 限制绘制区域，避免在透明区域浪费 GPU 算力。

## 优化手段

上一节我们梳理了过度绘制的几种常见来源，接下来逐个击破。优化的核心思路只有一条：**减少 GPU 对同一像素的重复填充**。不同来源有不同的应对手段，我们按投入产出比从高到低排列。

### 移除多余背景

这是投入产出比最高的优化。核心原则是：**如果一个背景会被其上层内容完全遮挡，就移除它。**

实际操作中，自底向上逐层检查：

1. Window 背景：是否与根布局背景重复？如果是，透明化 Window 背景。
2. 根布局背景：是否被子布局完全覆盖？
3. 中间层背景：是否有装饰性但不必要的背景？
4. Selector 背景：normal 状态是否可以设为透明？

### 布局层级扁平化

布局嵌套越深，过度绘制的可能性越大——每一层 ViewGroup 都可能添加自己的背景。使用 Lint 工具可以自动检测到许多布局问题：

- **Useless leaf**：没有子 View 也没有背景的布局，可以移除。
- **Useless parent**：只有一个子 View、没有背景、不是 ScrollView 的布局，可以移除并把子 View 提到上一层。
- **Deep layouts**：嵌套过深的布局，考虑用 RelativeLayout、ConstraintLayout 或 GridLayout 来扁平化。
- **Merge root frame**：如果根 FrameLayout 没有设置背景和 padding，可以用 `<merge>` 标签替代。

[已验证: 官方文档, developer.android.com/training/improving-layouts/optimizing-layout] [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]

### 自定义 View 中的 clipRect 和 quickReject

当我们在自定义 View 的 `onDraw()` 中绘制多个元素时，系统不知道哪些元素会被其他元素遮挡。如果不做任何处理，所有元素都会被完整绘制，即使部分元素最终被完全覆盖。

`Canvas.clipRect()` 可以限制后续绘制操作的生效区域。比如，我们有一个列表，每个 Item 由文本和图标组成，但文本可能被 Item 的边界裁剪。与其让系统绘制完整的文本再裁剪，不如在绘制前用 `clipRect` 限定区域：

```java
@Override
protected void onDraw(Canvas canvas) {
    // 限定绘制区域，避免文本溢出到 Item 边界之外
    canvas.clipRect(left, top, right, bottom);
    canvas.drawText(text, x, y, paint);
}
```

`Canvas.quickReject()` 则用于在绘制前判断一个矩形是否完全在当前裁剪区域之外。如果是，就可以跳过整个绘制操作：

```java
@Override
protected void onDraw(Canvas canvas) {
    for (Item item : items) {
        Rect itemBounds = item.getBounds();
        // 如果这个 Item 完全不可见，直接跳过
        if (!canvas.quickReject(itemBounds.left, itemBounds.top,
                                itemBounds.right, itemBounds.bottom)) {
            item.draw(canvas);
        }
    }
}
```

这两个 API 的配合使用，对于包含大量子元素的自定义 View（如自定义列表、图表、游戏界面）效果尤为明显。`clipRect()` 告诉 GPU "只在区域内绘制"，`quickReject()` 则在 CPU 侧就过滤掉完全不可见的元素，连 draw call 都不提交。

注意：`clipRect()` 带 `Region.Op` 参数的变体在 API 26 中被废弃了。对于复杂形状的裁剪，推荐直接用对应形状的绘制方法（比如 `drawCircle` 而不是 `clipPath` + `drawColor`），因为复杂裁剪本身可能带来额外开销，而且可能不支持抗锯齿。

[已验证: 官方文档, developer.android.com/reference/android/graphics/Canvas#clipRect] [已验证: 官方文档, developer.android.com/reference/android/graphics/Canvas#quickReject]

### ViewStub 延迟加载

对于不是立即需要的布局（比如错误提示页、高级设置面板），使用 `ViewStub` 可以在需要时才 inflate 和绘制，避免这些布局参与初始帧的渲染，同时也减少了它们在不可见时的过度绘制。

## 与其他章节的关系

过度绘制并不是孤立的性能问题，它和渲染管线的多个环节都有交集：

- **2.1 渲染架构全景**：过度绘制发生在 GPU 渲染阶段，是渲染管线中 GPU 执行环节的效率问题。2.1 节对 App 渲染管线和 SurfaceFlinger 合成管线的区分有助于理解过度绘制的定位。
- **2.4 Choreographer 与渲染流水线**：如果过度绘制导致 GPU 执行超时，帧就无法在当前 VSync 周期内完成，产生掉帧。
- **2.5 MainThread 与 RenderThread 协作**：在硬件加速渲染路径下，过度绘制不直接影响 MainThread，但会增加 RenderThread → GPU 的执行时间。
- **7.2 卡顿原因体系**：过度绘制是 GPU 侧导致卡顿的常见原因之一。

## 版本演进

过度绘制的检测和优化手段在 Android 版本中持续改进：

- **Android 4.2（API 17）**：引入"显示 GPU 过度绘制"开发者选项。
- **Android 4.3（API 18）**：引入 `clipRect` 和 `quickReject` 在硬件加速渲染路径中的支持（此前仅软件渲染有效）。
- **Android 5.0（API 21）**：移除了过度绘制数值显示（如"2.35x"），只保留颜色叠加。引入 RenderThread，过度绘制的主要性能影响从 MainThread 转移到 RenderThread → GPU 侧。
- **Android 7.0（API 24）**：增强 SurfaceFlinger 合成路径中的过度绘制优化（比如 HWC 的客户端合成减少）。
- **Android 8.0（API 26）**：`clipRect()` 的 `Region.Op` 变体被标记为废弃。
- **Android 12（API 31）**：引入新的渲染管线优化，包括更积极的 DisplayList 合并，间接降低了过度绘制的影响。

[待验证：Android 12/13/14 中过度绘制检测工具的具体变化]

## Jetpack Compose 中的过度绘制

[自动发现: 来源 developer.android.com/develop/ui/compose/performance]

前面讨论的检测和优化手段主要基于传统 View 系统。Jetpack Compose 采用声明式 UI 模型，渲染管线和组合机制与传统 View 不同，过度绘制的来源和优化手段也有差异。

### 检测方式

Compose 应用同样使用"调试 GPU 过度绘制"开发者选项来检测。此外，Android Studio 的 **Layout Inspector** 可以检查 Compose 的组合树（Composition tree），帮助定位哪些 Composable 叠加在一起。

### Compose 特有的过度绘制来源

Compose 的默认行为比传统 View 系统更激进地渲染——每个 Composable 默认都可能参与绘制，不会像 View 那样根据硬件加速层自动跳过不可见区域。常见的过度绘制来源包括：

1. **Modifier.background() 的叠加**：多个嵌套的 `Box` 或 `Column` 各自设置了 `background` 修饰符，会导致同一像素被绘制多次。优化方式是只在外层设置背景。
2. **Elevation 和阴影**：带有 `elevation` 的 Composable 会绘制阴影，增加过度绘制。
3. **Alpha 和透明度**：与 View 系统一样，半透明 Composable 天然导致过度绘制。

### Compose 特有的优化手段

- **使用 `drawBehind` 代替 `background` 修饰符**：对于需要频繁变化的背景色（如动画），`drawBehind { drawRect(color) }` 比 `background(color)` 更高效，因为前者只触发绘制阶段，不触发组合和布局阶段。
- **`derivedStateOf` 减少不必要的重组**：虽然重组（recomposition）不直接等于过度绘制，但减少无效重组可以间接减少不必要的绘制工作。
- **Lazy 布局**：`LazyColumn` 和 `LazyRow` 只组合和绘制可见项，天然避免了不可见区域的过度绘制。

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance]

## 常见问题与误区

### 误区：过度绘制一定能被感知到

过度绘制本身不等于卡顿。如果 GPU 有足够的算力在 VSync 周期内完成所有绘制，那么即使 3x 过度绘制用户也感知不到。过度绘制是一个**潜在的性能风险**——它降低了 GPU 的性能余量，使得未来添加更复杂的 UI 或在低端设备上更容易出现卡顿。

### 误区：所有蓝色区域都需要优化

蓝色（1x 过度绘制）在大多数应用中是不可避免的——文字绘制在背景上就是 1x。优化的优先级应该是：红色 > 粉色 > 绿色 > 蓝色。全屏蓝色是一个可以接受的状态，不需要追求零过度绘制。

### 误区：Compose 的 Recomposition 等于过度绘制

Recomposition（重组）是 Compose 在组合阶段重新执行 Composable 函数的过程，过度绘制则是 GPU 在绘制阶段对同一像素的重复填充。两者都可能导致帧率下降，但发生在完全不同的阶段，排查工具也不同：Layout Inspector 显示重组次数，GPU 过度绘制调试工具显示像素填充次数。一个实用的判断方法是——关闭 GPU 过度绘制调试后帧率恢复正常，说明瓶颈在 GPU 填充（过度绘制）；如果在 Layout Inspector 中看到某个 Composable 每帧都在重组，但 GPU 负载不高，瓶颈在 CPU 侧的重组开销。

## 参考资料

- AOSP 源码路径：`frameworks/base/libs/hwui/OpenGLRenderer.cpp`（早期版本的过度绘制渲染逻辑）
- [已验证: 官方文档, developer.android.com/topic/performance/rendering/overdraw]
- [已验证: 官方文档, developer.android.com/reference/android/graphics/Canvas]
- [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-1.md]（高爷原创：Android 性能优化之过渡绘制 - 理论篇）
- [来源: obsidian/Personal-Knowlodge/source/android-performance-optimization-overdraw-2.md]（高爷原创：Android 性能优化之过渡绘制 - 实战篇）
- [引用: https://www.youtube.com/watch?v=URyoiAt8098]（Romain Guy 的优化案例）
