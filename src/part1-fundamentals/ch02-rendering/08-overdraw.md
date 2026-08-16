---
title: 过度绘制
chapter: 2.8
section: 2.8
applicable_versions: Android 4.2 (API 17) - Android 17 (API 37)
last_verified: 2026-07-25
last_verified_against: AOSP android-17.0.0_r1 Properties.h/Properties.cpp, SkiaPipeline.cpp, RenderNodeDrawable.cpp, Canvas.java; androidx.compose.ui:ui:1.11.4 GraphicsLayerModifier.kt/GraphicsLayerScope.kt; kernel android17-6.18-2026-06_r6 dma-buf/dma-fence
confidence: high
task2b_state: fixed
task9_state: reviewed
task6_state: reviewed
pipeline_stage: ready-to-publish
status: finalized
sources:
  - type: aosp
    path: frameworks/base/libs/hwui/Properties.h
    ref: android-17.0.0_r1
  - type: aosp
    path: frameworks/base/libs/hwui/Properties.cpp
    ref: android-17.0.0_r1
  - type: aosp
    path: frameworks/base/libs/hwui/pipeline/skia/SkiaPipeline.cpp
    ref: android-17.0.0_r1
  - type: aosp
    path: frameworks/base/libs/hwui/pipeline/skia/RenderNodeDrawable.cpp
    ref: android-17.0.0_r1
  - type: aosp
    path: frameworks/base/graphics/java/android/graphics/Canvas.java
    ref: android-17.0.0_r1
  - type: kernel
    path: kernel/common/drivers/dma-buf/dma-buf.c
    ref: android17-6.18-2026-06_r6
  - type: kernel
    path: kernel/common/drivers/dma-buf/dma-fence.c
    ref: android17-6.18-2026-06_r6
  - type: kernel
    path: kernel/common/drivers/dma-buf/sync_file.c
    ref: android17-6.18-2026-06_r6
  - type: official
    path: https://developer.android.com/develop/ui/compose/graphics/draw/modifiers
  - type: official
    path: https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui/1.11.4/ui-1.11.4-sources.jar
  - type: obsidian
    path: Writer/rendering_pipelines/S01_rendering_types_overview.md
  - type: obsidian
    path: Writer/rendering_pipelines/S02_aosp_standard_type.md
  - type: obsidian
    path: Writer/rendering_pipelines/S03_surfaceview_type.md
  - type: obsidian
    path: Writer/rendering_pipelines/S04_textureview_type.md
  - type: obsidian
    path: Writer/rendering_pipelines/S05_mixed_rendering_type.md
  - type: obsidian
    path: Writer/rendering_pipelines/S07_software_offscreen_type.md
  - type: obsidian
    path: Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
tags: [overdraw, hwui, skia, gpu, compose, perfetto, agi]
related_chapters: ["2.6", "2.7", "2.10", "7.1", "7.5"]
---

# 2.8 过度绘制

## 过度绘制的边界

过度绘制（overdraw）指同一目标像素在一帧的绘制过程中被多次覆盖。常见例子是 Window 背景、根布局背景和列表项背景依次画在同一片不透明区域，最终只有最上层颜色可见。

本文所说的“逻辑绘制次数”来自 HWUI 对 View/Compose 绘制命令的重放。它不等于 GPU 实际执行的片元数，也不包含 SurfaceFlinger 对多个窗口 Layer 的全部合成工作。先分清这三个口径，后面的颜色和性能数据才不会混用。

这里有三个容易混淆的层次：

1. **应用提交的逻辑绘制**：HWUI（Android 的 View 硬件加速渲染管线）重放显示列表时，多条绘制命令覆盖同一像素。这是“调试 GPU 过度绘制”主要观察的对象。
2. **GPU 执行的片元、采样与混合**：片元是光栅化后等待着色、混合并写入目标像素的候选结果。驱动可以裁剪、合批（把可一起提交的绘制命令组合起来）或剔除部分工作，移动 GPU 还可能在 tile memory（处理一个画面分块时使用的片上存储）中完成中间结果。逻辑上多画一次，不等于外部内存一定多写一整次。
3. **SurfaceFlinger 的多 Layer 合成**：App Window、`SurfaceView`、系统栏、弹窗等可以是不同的 SurfaceFlinger Layer。它们可能由 HWC 的硬件 plane（显示控制器可独立处理的图层通道）合成，也可能由 RenderEngine 先合成到 client target（交给 HWC 的 GPU 合成结果），属于显示合成阶段。

彩色区域只能定位需要检查的位置，不能单独证明 GPU 已超出帧预算，也不能代表整屏所有 Layer 的最终合成成本。

## Android 17 怎样生成过度绘制颜色

Android 17 / API 37 的源码锚点是 `android-17.0.0_r1`。HWUI 通过 `debug.hwui.overdraw` 属性控制调试功能：

- [`Properties.h`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/Properties.h) 定义属性名、调试状态和颜色集；
- [`Properties.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/Properties.cpp) 在当前实现中识别 `show` 和 `show_deuteranomaly`；
- [`SkiaPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaPipeline.cpp) 负责计数重放和着色。

开启调试后，`SkiaPipeline::renderFrame()` 先完成正常帧绘制，再调用 `renderOverdraw()`。后者会创建一个与目标表面等大的 A8 离屏表面；A8 是每个像素只保存 8 位 alpha（透明度通道）的格式。`SkOverdrawCanvas` 会在该表面上再重放一次 HWUI 绘制内容，以 alpha 值累计“这个像素会被画几次”，随后通过颜色过滤器把计数映射成覆盖色。

这段实现带来两个重要结论：

- 颜色来自 **HWUI 绘制命令的诊断性重放**，不是 GPU 驱动返回的硬件计数器；
- 调试模式本身多了一张全尺寸 A8 表面、一次重放和一次着色合成，不能在开启它时测量页面的正常 GPU 时长。

诊断重放还有一个 Hardware Layer 边界。Android 17 的 `RenderNodeDrawable` 遇到已有 layer surface 的 RenderNode 时，会通过 `drawImageRect()` 合成 layer snapshot，不会在最终窗口的 overdraw pass（过度绘制诊断的这次重放）中逐条展开该 layer 内部的 DisplayList。源码还保留了刚重绘 layer 的透明矩形调试分支，但不能据此把最终叠加色解释成 layer 内部所有 draw op（绘制操作）的逐像素计数。看到 layer build/update 或离屏 pass 时，还要结合 [2.7 Hardware Layer](07-hardware-layer.md) 的 RenderThread、GPU 和内存证据。

### 颜色应该怎样读

Android 17 默认颜色数组的前两个位置是透明色，之后依次是蓝、绿、粉红和红。按“相对基线多画了几次”解读更准确：

| 屏幕叠加色 | 本帧逻辑绘制次数 | 相对一次基线绘制 |
| --- | ---: | ---: |
| 无叠加色 | 0 或 1 次 | 额外 0 次 |
| 蓝色 | 2 次 | 额外 1 次 |
| 绿色 | 3 次 | 额外 2 次 |
| 粉红色 | 4 次 | 额外 3 次 |
| 红色 | 5 次及以上 | 额外 4 次以上 |

`show_deuteranomaly` 会换用一套面向绿色弱（deuteranomaly）的配色，计数含义不变。实际显示还会受底图颜色和显示设备影响，排查时应关注区域与操作的对应关系，不要用肉眼比较色深来估计时间。

红色也不等于“前四次全是无用功”。文字绘制在背景上、半透明遮罩与底图混合、阴影覆盖边缘，都可能是视觉结果所必需的。优化对象是没有视觉贡献或可以减少面积的绘制。

## 性能成本：fill rate、带宽和离屏 pass

fill rate 指 GPU 在单位时间内生成并写出像素或片元结果的能力；render pass 是围绕一个渲染目标组织的一组 GPU 绘制。过度绘制可能影响两者，但逻辑覆盖次数不能直接换算成耗时。

### 不要用“层数 × 屏幕像素”代替 GPU 成本

过度绘制可能增加以下工作：

- 片元着色、纹理采样和颜色写入；
- 半透明内容的读取与混合；
- 大面积效果、阴影或模糊引入的中间渲染目标；
- 离屏表面的分配、清理、渲染和回合成；
- GPU 活跃时间、频率和功耗。

多数移动 GPU 使用 tile-based（分块渲染）架构。驱动和 GPU 可以在片上存储中处理一个 tile，并对裁剪、不透明覆盖和不可见区域做优化，因此三次逻辑覆盖不保证产生三倍外部内存写入。半透明混合、纹理采样、复杂 shader（在 GPU 上执行的着色程序）和额外 render pass 仍可能消耗计算与带宽。具体代价由 GPU 架构、驱动、绘制顺序、格式、分辨率和内容共同决定。

工程判断应落到可测量的关联上：

> 这片重复绘制是否与目标设备上的 GPU 完成时间、帧截止时间或功耗变化同时出现？

如果页面始终有足够余量，蓝色或绿色区域未必需要立刻修改。如果大面积热区随滚动或动画出现，并且同一操作发生 `AppDeadlineMissed`（应用帧错过预期截止时间）、GPU 完成变晚或频率抬升，就应继续定位。

### 透明内容不等于无效内容

半透明内容需要读取底层结果并做混合，这通常是设计所需。完全透明的绘制有时会被上层框架、Skia、驱动或 GPU 跳过，但不能依靠“alpha 为 0”保证零成本。业务层确认内容不可见时，可直接跳过相应绘制；需要透明效果时，应限制作用面积并测量结果。

## 工具各自回答什么问题

### Debug GPU Overdraw：找空间位置

入口通常是：

**设置 → 开发者选项 → 调试 GPU 过度绘制 → 显示过度绘制区域**

它适合回答：

- 哪一块 App Window 内容被重复覆盖；
- 热区是否跟随某个列表项、遮罩、动画或背景移动；
- 删除一层背景后，逻辑绘制次数是否下降。

它不适合回答：

- 正常运行时一帧耗时多少；
- 哪条 GPU 命令最慢；
- `SurfaceView`、其他窗口与系统 UI 的跨 Layer 合成总成本；
- HWC 使用了 DEVICE composition 还是 CLIENT composition。

正确用法是先开启叠加定位区域，记录场景，然后关闭叠加，再采集性能数据。

### Layout Inspector：找绘制对象

布局检查器（Layout Inspector）用来对应 View、Composable（Compose UI 中声明界面的函数节点）、尺寸、背景和层级。层级深并不自动产生像素过度绘制：没有背景且不执行绘制的 `ViewGroup` 会增加测量、布局或遍历成本，却不会仅因存在就覆盖像素。

看到热区以后，应检查该区域内哪些对象会画：

- `windowBackground`、根布局和容器背景；
- `foreground`、selector、分割线和装饰；
- 自定义 `onDraw()` / `dispatchDraw()`；
- Compose 的 `background`、`drawBehind`、`Canvas`、`graphicsLayer` 等 modifier；modifier 是依次为 Composable 添加布局、绘制或交互行为的修饰链；
- 阴影、模糊、alpha 和离屏合成。

### Profile GPU Rendering：看 HWUI 阶段压力

“GPU 呈现模式分析”（Profile GPU Rendering）柱状图展示 HWUI 一帧若干阶段的耗时代理；这里的代理值用于提示阶段压力，不是每条 GPU 命令的精确执行时长。`Draw`、`Issue Commands`（向图形 API 提交命令）等区段各有含义，不能把任何一个长柱直接解释成“过度绘制”。

它适合快速观察操作前后是否长期接近帧预算。若柱状图变长，还要结合线程 Trace 和 GPU 证据区分显示列表记录、RenderThread 工作、命令提交、GPU 执行或资源上传。

### Perfetto / FrameTimeline：找迟到的帧和责任边界

从 Android 12 起，FrameTimeline 可以把 App 的 `SurfaceFrame`（应用向某个 Surface 提交的一帧）与最终 `DisplayFrame`（显示系统合成并呈现的一帧）对应起来。`Expected Timeline` 是系统预测的时间目标，`Actual Timeline` 记录实际结果；后者晚于前者只说明帧迟到，不能单凭这一条认定 GPU 是原因。App 帧完成时间会综合 buffer post（应用提交窗口 buffer）与 GPU 完成，SurfaceFlinger 也可能单独迟到。

建议按下面顺序检查：

1. 选中一次可复现操作中的 janky `SurfaceFrame`（被 FrameTimeline 判定为卡顿的应用帧），记下 VSyncId、Layer 和 jank type；VSyncId 用于关联同一轮帧调度中的记录。
2. 看 UI 线程的 `Choreographer#doFrame`、traversal 与显示列表记录。
3. 看 RenderThread 的 `DrawFrame`、资源上传、提交和等待。
4. 若设备提供可靠的 GPU completion（GPU 工作完成时间）、GPU slices、频率或 counter（硬件性能计数器），再判断 GPU 是否构成关键路径。
5. 对照对应 `DisplayFrame`、SurfaceFlinger 和 composition type（CLIENT、DEVICE 等合成方式），确认问题位于 App Window 内部，还是多 Layer 合成阶段。

“UI 线程不忙，Actual Timeline 迟到”仍不足以证明过度绘制。可能原因还包括 acquire fence（保护 buffer 读取时机的同步对象）迟迟未完成、RenderThread CPU 工作、shader 编译、纹理上传、GPU 竞争和 SurfaceFlinger 合成。

### AGI：深入一帧的 GPU 工作

Android GPU Inspector（AGI）的 Frame Profiler 可分析受支持应用的一帧，查看 Vulkan API 调用、render pass、draw call（一次绘制提交）、framebuffer（渲染目标及其附件）、shader、纹理和 GPU 性能数据。它适合回答“哪一批命令覆盖了这块区域”“是否多了一次离屏 pass”“某个 shader 或纹理采样是否昂贵”。

AGI 的 API、设备、驱动和可调试应用都有支持边界，抓帧也会引入插桩开销。它用于分析命令和相对差异，不应把 capture（抓帧采集）期间的时间当作用户正常运行时延。

### GPU counter：只做同设备、同场景的 A/B 证据

A/B 指保持其他条件一致，只比较修改前后的两组结果。Perfetto 或 AGI 能看到哪些 counter，取决于设备和驱动。counter 可能统计片元、采样、tile、周期、render target（渲染目标）写入或 GPU busy（GPU 处于工作状态的时间比例），定义并不统一。

这种公式不能作为通用 overdraw 倍率：

```text
counter / (屏幕宽度 × 屏幕高度)
```

分子可能包含多 render pass、多个目标、缩放、MSAA（多重采样抗锯齿）、裁剪、系统工作或其他上下文，分母也未必等于实际渲染分辨率。使用 counter 时先确认厂商定义，只在同一设备、同一分辨率、同一场景和相近热状态下比较修改前后。

## 页面的 Surface 拓扑

过度绘制颜色主要覆盖 HWUI App Window 的诊断重放。页面还有独立 Surface 时，要分别分析。

### SurfaceView

`SurfaceView` 的内容通常进入独立的 child Surface，也就是挂在宿主窗口之下、拥有自己 buffer 提交路径的 Surface。宿主 App Window 负责普通 View、控件和遮罩，SurfaceFlinger 再把两者放进同一个 Layer 树。视频、相机或游戏画面是否走 HWC 的 DEVICE composition，要由每帧的格式、缩放、旋转、alpha、protected（受保护内容）属性、可用 plane 和带宽共同决定。

宿主窗口的颜色叠加不能代表 `SurfaceView` 内容内部的重复绘制，也不能显示 SurfaceFlinger/HWC 的最终合成策略。应检查对应 Layer、buffer、fence 和 composition type。

### TextureView

`TextureView` 的外部 Producer 先把 buffer 送到 `SurfaceTexture`（把 BufferQueue 内容暴露为可采样纹理的对象），宿主 RenderThread 再将它采样进 App Window buffer。SurfaceFlinger 通常只看到宿主窗口。因此，覆盖在 `TextureView` 上的普通 View 会参与宿主 HWUI 的绘制关系，视频或相机画面还多了一次纹理采样。

`TextureView` 便于使用 View 的变换、clip、alpha 和动画，但不能因此断言一定更慢。应比较实际视觉需求、Surface 拓扑和目标设备数据。

### 多窗口与系统合成

弹窗、输入法、系统栏、画中画和分屏会改变可见 Layer 集合。SurfaceFlinger 的 CompositionEngine 可能生成 client target，HWC 也可能把 Layer 分配到硬件平面。App 内部 overdraw 下降后，如果 DisplayFrame 仍迟到，就要继续检查 SurfaceFlinger 与 HWC，不能只看宿主 App 的颜色。

## 常见来源与安全的修改方式

### 1. Window 背景与根布局背景重复

主题的 `windowBackground` 会参与 starting window（应用首帧到来前由系统显示的启动窗口）、启动过渡以及首个 App buffer 到来前的视觉。根布局完全覆盖它以后，两层背景可能在正常帧中重叠；直接改成透明却可能引入启动闪烁、边缘漏底或窗口过渡异常。

修改前先确认：

- 根内容是否从首个 App buffer 起就不透明地覆盖整个窗口；
- 状态栏、导航栏、圆角、display cutout（刘海或挖孔等屏幕缺口）和 edge-to-edge（内容延伸到系统栏区域）布局是否留下空隙；
- SplashScreen / starting window 的背景和品牌图是否已正确配置；
- 透明窗口相关主题属性是否会改变合成、安全或性能行为。

满足这些条件后，可以让背景只在一个正确的层绘制。不要把下面的透明设置当作所有 Activity 的固定模板：

```xml
<style name="Theme.Example" parent="...">
    <item name="android:windowBackground">@android:color/transparent</item>
</style>
```

这段配置只适用于已经处理好启动窗口与全窗口覆盖的页面。多数应用更适合保留主题背景，并移除内容树中重复的同色背景。

### 2. 多层 background、foreground 与 selector

父容器、子容器和列表项若在同一矩形内绘制相同的不透明色，应保留视觉上负责该区域的一层。selector 的默认态也要按视觉需求设置，不能一律换成透明：如果默认态负责卡片底色，删掉会改变界面。

一个透明默认态 selector 可以这样写：

```xml
<selector xmlns:android="http://schemas.android.com/apk/res/android">
    <item
        android:state_pressed="true"
        android:drawable="@color/item_pressed" />
    <item android:drawable="@android:color/transparent" />
</selector>
```

这段写法适用于底色已经由下层稳定提供、默认态不需要单独填色的条目。修改后还要验证 pressed、focused、selected、disabled 和无障碍高对比场景。

### 3. 不必要的全屏绘制

自定义 View 常见的低效写法是每帧清空整块区域，却只更新一小部分；或者先绘制完整底图，随后用不透明面板覆盖大半区域。应先从业务数据和可见区域减少 draw call，再考虑 Canvas 裁剪。

对列表、图表或大画布，可以：

- 只遍历与当前 viewport（当前可见的内容窗口）相交的数据；
- 把脏区域映射到内容坐标；
- 跳过完全不可见的对象；
- 对静态内容谨慎缓存，避免每帧重建资源；
- 避免为了局部效果创建全屏离屏层。

### 4. 半透明遮罩、阴影与模糊

半透明遮罩必须与底图混合，不能简单删除。优化方向是缩小矩形、减少渲染轮次、避免在不可见页面继续绘制，并确认动画期间是否需要整屏更新。

阴影和模糊可能扩大有效绘制边界，还可能触发离屏处理。裁剪过紧会切掉视觉效果，裁剪过大又失去收益。边界应包含 blur radius（模糊半径）、shadow offset（阴影偏移）、stroke（描边宽度）和动画变换后的范围。

### 5. 层级很深，但没有重复绘制

布局扁平化可以减少测量、布局、遍历和对象数量，却不保证颜色叠加变轻。判断某个父节点能否删除时，要同时检查 layout 行为、padding、clip、touch、accessibility（无障碍信息与操作）、transition 和背景。

`ViewStub` 的主要收益是延后 inflate（从布局资源创建 View 对象）、节省初始对象和遍历成本。普通 `GONE` View 本来就不参与绘制，因此 `ViewStub` 不是通用的 overdraw 修复；只有它阻止了原本会出现的可见重叠内容时，像素覆盖才会改变。

## 自定义 View：减少提交，再限制裁剪范围

### 用 quickReject 跳过 clip 外对象

以下示例面向 API 30+，用当前 clip（Canvas 当前允许绘制的区域）和画布变换对矩形做保守拒绝：

```java
private final RectF tmpBounds = new RectF();

@Override
protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);

    for (Item item : items) {
        tmpBounds.set(item.left, item.top, item.right, item.bottom);
        if (canvas.quickReject(tmpBounds)) {
            continue;
        }
        item.draw(canvas);
    }
}
```

`quickReject()` 返回 `true` 时，变换后的矩形与当前 clip 不相交，可以安全跳过绘制。返回 `false` 只表示“不能快速排除”；对于 Path 等复杂几何，bounds（外接边界）与 clip 相交也不保证形状最终可见。API 30 之前可使用带 `Canvas.EdgeType` 的旧重载，Android 17 中该参数已被忽略，旧重载也已废弃。

### 用 save/restore 限定裁剪作用域

需要限制一组绘制命令时，应让 clip 只在明确的作用域内生效：

```java
@Override
protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);

    int saveCount = canvas.save();
    try {
        canvas.clipRect(contentLeft, contentTop, contentRight, contentBottom);
        drawVisibleContent(canvas);
    } finally {
        canvas.restoreToCount(saveCount);
    }

    drawOverlay(canvas);
}
```

`save()` 和 `restoreToCount()` 把 clip 的作用范围限制在两次调用之间，防止裁剪状态影响后续 overlay。`clipRect()` 只限制之后的绘制，不会自动减少数据遍历；如果 `drawVisibleContent()` 仍为所有对象构建 Path、文本布局和资源，CPU 开销依然存在。

复杂 clip 自身也有成本。Android 硬件加速文档记录了早期 API 的支持边界；在 Android 17 上功能已成熟，仍应通过目标设备测量。能用矩形 viewport 和业务可见性判断解决时，通常不需要更复杂的 Path 裁剪。

## Jetpack Compose 中的过度绘制

Compose 与 View 最终都可能进入 HWUI App Window，因此像素覆盖的基本判断相同。需要把 recomposition（状态变化后重新执行相关 Composable）、绘制命令和离屏合成分开看。

以下 `graphicsLayer` 结论固定到 `androidx.compose.ui:ui:1.11.4` 的 `GraphicsLayerModifier.kt` 与 `GraphicsLayerScope.kt`，并与 Android Developers 文档交叉核对。应用若使用其他 Compose UI 版本，应按实际依赖重新确认；Android 17 平台版本不会替应用固定 Compose 实现。

### 多层背景仍会多画

多个 `Modifier.background()`、`Surface` 或 `Canvas` 覆盖同一区域时，不能假设 Compose 会自动合并父子背景。若外层已经提供不透明底色，内层只在需要的范围画自身视觉。

`drawWithCache` 可以缓存绘制准备阶段创建的对象，减少 CPU 工作；它不会自动减少最终提交的像素。`derivedStateOf` 用于从其他状态派生一个只有结果变化时才通知读取方的 State，可能影响重组频率，但它也不是 overdraw 开关。

### graphicsLayer 的合成策略

官方 graphics modifiers 文档给出的边界如下：

- 默认 `CompositingStrategy.Auto` 下，alpha 小于 1 或使用 `RenderEffect` 等场景可能创建离屏 buffer；
- overscroll（滚动越过边界时的视觉反馈）会使用离屏 buffer，不受指定合成策略影响；
- 非 `SrcOver`（把源内容覆盖到目标内容之上的默认混合模式）的 `blendMode` 或非空 `colorFilter` 会强制离屏，行为等价于 Offscreen；
- `CompositingStrategy.Offscreen` 强制先画入离屏 buffer，再合成到目标，而且内容会按 layer bounds 裁剪；
- `CompositingStrategy.ModulateAlpha` 在可用时把 alpha 分配到各绘制命令，省去 alpha 离屏层；如果同一 layer 内有重叠绘制，其混合结果可能与 Offscreen 不同。

下面的示例明确要求离屏合成，适合需要 `BlendMode` 隔离的场景：

```kotlin
Modifier.graphicsLayer {
    compositingStrategy = CompositingStrategy.Offscreen
}
```

这段代码会增加一个 render pass，只适用于像素混合需要彼此隔离的场景。若想换成 `ModulateAlpha`，必须先确认同一 layer 内绘制内容不会重叠，或重叠后的视觉差异可以接受。

### Compose 排查顺序

1. 用颜色叠加确认热区是否位于宿主 App Window。
2. 用 Layout Inspector 找到对应 Composable、modifier 和 layer。
3. 检查重复背景、全尺寸 `Canvas`、alpha、shadow、blur、clip 和 `graphicsLayer`。
4. 关闭颜色叠加后，用 Perfetto 确认 UI、RenderThread 和 GPU 的责任。
5. 有离屏 pass 或复杂 shader 疑问时，再用 AGI 检查受支持的一帧。

重组次数下降而颜色没有变化，说明 CPU 侧工作减少了；颜色下降而帧时间没有变化，说明被删掉的绘制尚未处在当前瓶颈上。两种修改都可能有价值，但证据和结论要分开记录。

## 一次可复现的验证流程

建议把优化做成受控 A/B：

1. 固定设备、刷新率、分辨率、页面数据和操作脚本，记录电量与热状态。
2. 开启“调试 GPU 过度绘制”，截图或录屏定位热区；不要记录此时的帧耗时。
3. 关闭叠加，预热页面后采集 Perfetto，找到具体的 janky `SurfaceFrame` 和对应 `DisplayFrame`。
4. 确认 UI 线程、RenderThread、GPU completion、buffer post 和 SurfaceFlinger 中谁位于关键路径。
5. 一次只修改一个背景、绘制范围或离屏策略。
6. 再次开启叠加验证逻辑覆盖是否下降，然后关闭叠加，用同样条件重采性能数据。
7. 比较帧截止时间、GPU 活跃时间、功耗或厂商 counter；保留没有改善的结果，避免把颜色变化写成性能结论。

如果问题涉及多个 Surface，还要列出每个 Producer、Consumer、SurfaceFlinger Layer、buffer 和 fence。宿主 App Window 的一次 FrameTimeline 无法代表视频、相机或游戏 Surface 的完整节拍。

## Kernel 与厂商驱动边界

kernel 源码锚点统一为 `android17-6.18-2026-06_r6`。通用内核能提供调度、dma-buf、dma-fence/`sync_file` 等基础机制：dma-buf 用于在设备与进程间共享缓冲内存，dma-fence 描述异步任务的完成依赖，`sync_file` 则把 fence 封装成可跨进程传递的文件描述符。这些机制可以帮助观察 GPU job（提交给 GPU 的一组工作）、buffer 与显示依赖何时完成。

片元剔除、tile 策略、颜色压缩、counter 定义和大量 GPU 调度细节位于硬件与厂商驱动。通用 kernel tag 不能说明某次逻辑 overdraw 执行了多少片元，也不能给出跨 GPU 通用的填充率模型。

一次长 fence wait（等待 fence 完成）只说明消费者在等待生产者。要判断是否由过度绘制引起，还要找到 fence 的创建者、GPU 提交、频率、工作量和同场景 A/B 结果。不能从 dma-fence 时长直接反推 overdraw 次数。

## 版本演进

| 版本 | 与过度绘制相关的变化 |
| --- | --- |
| Android 4.2 / API 17 | 开发者选项提供 GPU 过度绘制可视化，用于定位 App 内容的重复绘制区域。 |
| Android 12 / API 31 | FrameTimeline 成为分析 App `SurfaceFrame` 与最终 `DisplayFrame` 的重要数据源；它不直接给出 overdraw 次数。 |
| Android 17 / API 37 | 当前源码锚点。HWUI 仍通过 `debug.hwui.overdraw`、A8 计数表面和 `SkOverdrawCanvas` 重放生成叠加色；App、SurfaceFlinger 与 HWC 的责任边界仍需结合 Layer 和 Trace 判断。 |

Android Studio 和 AGI 会独立于平台版本更新。使用工具时应记录工具版本、设备驱动和 capture 配置，不要把 Android Studio 的发布时间写成 Android 平台行为。

## 常见误区

### “红色一定先改，蓝色不用看”

颜色只表达逻辑覆盖次数。优化优先级应综合区域大小、出现频率、视觉必要性、目标设备和实际帧证据。一个小红点可能无关紧要，大面积随滚动移动的绿色区域也可能值得处理。

### “删掉 ViewGroup 就会减少过度绘制”

只有该节点或它改变后的子节点少画了像素，颜色才会变化。空 ViewGroup 的主要成本在 CPU 侧布局和遍历。

### “FrameTimeline 迟到就说明 GPU fill rate 不够”

FrameTimeline 先用于确认哪一帧、哪一侧迟到。线程阻塞、资源上传、buffer/fence、GPU 竞争和 SurfaceFlinger 都可能产生相似现象，需要继续查看直接证据。

### “GPU counter 除以屏幕像素就是平均 overdraw”

counter 的统计单位、render target、pass 范围和上下文都可能不同。没有厂商定义和受控采集时，这个比值没有可比较的物理含义。

### “Compose 重组就是过度绘制”

重组发生在 Compose 运行时和 UI 构建阶段，overdraw 描述绘制目标上的像素覆盖。它们可能出现在同一慢帧中，但要分别用 Compose 状态与阶段分析工具、绘制 Trace 和 GPU 工具检查。

## 源码与官方资料

- [`Properties.h`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/Properties.h)、[`Properties.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/Properties.cpp)：`debug.hwui.overdraw` 属性与配色选择。
- [`SkiaPipeline.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaPipeline.cpp)：A8 表面、`SkOverdrawCanvas` 重放与颜色映射。
- [`RenderNodeDrawable.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/RenderNodeDrawable.cpp)：Hardware Layer snapshot 合成与本帧 layer repaint 的诊断计数。
- [`Canvas.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/Canvas.java)：`clipRect()`、`quickReject()` 及旧重载的废弃状态。
- [Canvas API reference](https://developer.android.com/reference/android/graphics/Canvas)：`quickReject()` 的返回语义。
- [Hardware acceleration](https://developer.android.com/develop/ui/views/graphics/hardware-accel)：Canvas 硬件加速模型和早期 API 支持边界。
- [Profile GPU Rendering](https://developer.android.com/topic/performance/rendering/profile-gpu)：各柱状阶段的语义。
- [FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)：App / SurfaceFlinger jank 分类和 App 帧完成时间。
- [AGI Frame Profiler](https://developer.android.com/agi/frame-trace/frame-profiler)：受支持帧中的 API 调用、render pass、draw call 和 GPU 数据。
- [Compose graphics modifiers](https://developer.android.com/develop/ui/compose/graphics/draw/modifiers)：`graphicsLayer`、离屏合成与 `CompositingStrategy`。
- [Compose UI 1.11.4 sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui/1.11.4/ui-1.11.4-sources.jar)：`GraphicsLayerModifier.kt`、`GraphicsLayerScope.kt` 的版本化语义。
