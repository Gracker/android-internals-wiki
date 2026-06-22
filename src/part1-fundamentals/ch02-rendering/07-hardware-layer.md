---
title: "Hardware Layer"
chapter: "2.7"
section: "2.7"
status: "finalized"
drafted_date: "2026-03-30"
applicable_versions: "Android 3.0 (API 11) - Android 17 (API 37)"
last_verified: "2026-04-28"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
reviewed_date: "2026-05-08"
review_notes: "2026-05-07 16:08 task6 review (Task2B 修复后复审): pass-light-edit。轻修 4 处（16KB 分配粒度/数据描述/Compose offscreen 用词）；L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。评分: 结构5/5·措辞5/5·一致性5/5·验证4/5·元数据5/5。 | 2026-05-08 Task6 21:24：Task2B 修复后写作复审；轻修 5 处（开头读者指向、第一人称、操作原则句），L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。"
reviewed_by: openclaw-task6
polish_count: 2
polish_date: "2026-04-28"
polish_by: "task2b-polish"
sources:
  - type: blog
    path: "https://www.androidperformance.com/2019/07/27/Android-Hardware-Layer/ (高爷原创)"
  - type: official
    path: "developer.android.com/reference/android/view/View#setLayerType(int,%20android.graphics.Paint)"
  - type: official
    path: "developer.android.com/topic/performance/hardware-accel"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java (buildLayer/buildDrawingCache)"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/RenderNode.java (setUseCompositingLayer/getUseCompositingLayer)"
tags: [hardware-layer, LAYER_TYPE_HARDWARE, LAYER_TYPE_SOFTWARE, animation, RenderNode, compositing-layer, buildLayer, graphicsLayer, GPU-纹理缓存]
related_chapters: ["2.4", "2.5", "2.6", "7.1", "7.5"]
pipeline_stage: "ready-to-publish"
task6_result: pass-light-edit
task6_state: "reviewed"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
task2b_result: "fixed"
last_task2b_at: "2026-05-08T20:44:59+08:00"
task9_reviewed_date: "2026-05-08"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-08T21:35:11+08:00"
last_task9_audit: "2026-06-18"
last_task6_at: "2026-05-08T21:24:13+08:00"
last_task6_audit: "2026-06-23"
last_task6_review_log: "logs/review/2026-05-08-21-review.md"
task6_review_notes: "2026-05-07 Task6 16:08：Task2B 修复后写作复审；清理 L1/L2 用词 4 处，L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-08 Task6 21:24：Task2B 修复后写作复审；轻修 5 处（开头读者指向、第一人称、操作原则句），L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-05-08-21-deep-review.md"
task9_review_notes: "2026-05-08 Task9 21:32：pass-tech-review。无 P0/P1；P2 4 处记录在 deep-review/suggestions，不阻塞发布；自动晋升 finalized / ready-to-publish。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
last_task9_audit_log: "logs/deep-review/2026-06-18-16-audit.md"
---

# Hardware Layer

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Hardware Layer 的本质：将 View 树缓存为离屏 GPU 纹理
- 🔹 setLayerType(LAYER_TYPE_HARDWARE) 的适用场景：复杂子树复用、Alpha 与离屏合成
- 🔹 Hardware Layer 的代价：额外 GPU 内存、失效与重建开销
- 🔹 何时 Hardware Layer 能提升性能 vs 何时反而劣化

### 扩展（可选深入）

- 🔸 与 RenderNode compositing layer 的关系
- 🔸 在 Compose 中使用 graphicsLayer 的性能考量

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Hardware Layer

Perfetto 中一旦看到某一帧的 RenderThread 出现异常耗时的 `buildLayer` 调用，或者主线程出现不该有的 `buildDrawingCache/SW`，大概率就是 Hardware Layer（或 Software Layer）使用不当的信号。

Hardware Layer 这个名字容易让人困惑：Android 默认不是已经开启了硬件加速吗？为什么还有一个叫 "Hardware Layer" 的东西？这二者的区别正是本节要讲清楚的第一件事。理解了 Hardware Layer 的本质，才能判断什么时候该用它、什么时候它会帮倒忙；在实际性能优化中，因为 LayerType 误用导致卡顿的案例并不少见。

## 硬件加速 ≠ Hardware Layer

在讲 Hardware Layer 之前，需要把两个容易混淆的概念区分清楚。

**硬件加速（Hardware Acceleration）** 指的是 Android 的渲染管线使用 GPU 来完成图形绘制，而不是用 CPU 调用 Skia 软件渲染。从 Android 4.0 开始，硬件加速默认开启。开启后，App 的渲染工作由主线程（记录 DisplayList）和 RenderThread（将 DisplayList 提交给 GPU 执行）协同完成。


**Hardware Layer** 指的是在硬件加速开启时，把某个 View 子树的绘制结果放进一块离屏 GPU render target，后续以纹理的形式参与合成。官方文档把它描述为 hardware layer 或 hardware texture。它解决的是“同一批绘制结果要被连续复用”的问题，例如 alpha、translation、scale、rotation 这些变换持续发生，但内容本身没有变化的场景。

Hardware Layer 能减少的是 RenderThread 侧对这棵子树 DisplayList 的重复 replay 和光栅化成本——现代 HWUI 是 retained DisplayList/RenderNode 模型，translation、scale、rotation、alpha 等属性动画通常不会让 UI 线程每帧重录 DisplayList。它本身不是 measure/layout 的跳过开关。布局能不能跳过，取决于这一帧有没有新的 layout request、尺寸约束有没有变化；内容一旦 `invalidate()`，layer 缓存仍然会失效并重建。

为了不把几个层级混在一起，可以把三个场景分开看：

- **整个 window/app 开启硬件加速，View 保持默认 `LAYER_TYPE_NONE`**：这是现代 Android 的常态。MainThread 记录 DisplayList，RenderThread 把 RenderNode 提交给 GPU。
- **单个 View 使用 `LAYER_TYPE_SOFTWARE`**：只有这个 View 子树改走软件缓存，先生成 Bitmap，再参与窗口合成；窗口其他部分仍然可以保持硬件加速。
- **整个 window/app 关闭硬件加速**：窗口没有 ThreadedRenderer，整帧绘制都回到软件管线，这才是“整个窗口没有 RenderThread”的情形。


## 三种 LayerType：NONE、SOFTWARE、HARDWARE

每个 View 都有一个 `layerType` 属性，通过 `View.setLayerType(int layerType, Paint paint)` 设置。三种类型的含义和适用场景差异很大。

### LAYER_TYPE_NONE（默认值）

这是所有 View 的默认状态。在这个状态下，View 不做任何特殊缓存处理，每一帧按照正常流程走 measure → layout → draw。

大多数情况下，保持默认值就够了。

### LAYER_TYPE_SOFTWARE

设置 `LAYER_TYPE_SOFTWARE` 后，系统会把该 View 渲染成一个 Bitmap 对象缓存起来。注意，这里的"软件"指的是缓存方式——即使 App 开启了硬件加速，Software Layer 仍然用 Bitmap（CPU 侧的像素缓冲区）来缓存 View 内容。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/View.java — buildLayer() 分支]

```java
// frameworks/base/core/java/android/view/View.java
// @ AOSP android-16.0.0_r1
public void buildLayer() {
    if (mLayerType == LAYER_TYPE_NONE) return;
    // 省略与本节无关的 attachInfo、尺寸和缓存状态检查
    switch (mLayerType) {
        case LAYER_TYPE_HARDWARE:
            updateDisplayListIfDirty();
            if (attachInfo.mThreadedRenderer != null && mRenderNode.hasDisplayList()) {
                attachInfo.mThreadedRenderer.buildLayer(mRenderNode);
            }
            break;
        case LAYER_TYPE_SOFTWARE:
            buildDrawingCache(true);  // 生成 Bitmap 缓存
            break;
    }
}
```

硬件层分支里，`updateDisplayListIfDirty()` 先把当前 View 子树的绘制命令同步到 `RenderNode`，随后再用 `mRenderNode.hasDisplayList()` 判断这个节点是否已经持有可复用的 DisplayList。`buildLayer()` 依赖的是“已经有 DisplayList 可以建层”，不是泛化的“节点有效”。

`LAYER_TYPE_SOFTWARE` 则走 `buildDrawingCache()` 路径，最终生成一个 Bitmap 缓存。这个操作发生在主线程。

Software Layer 的适用场景比较有限。最常见的情况是 App 没有开启硬件加速时，需要给 View 应用颜色过滤器、混合模式或半透明效果——此时 Software Layer 是唯一能提供离屏缓冲的方式。在硬件加速模式下，如果某个 View 使用了不被硬件渲染管线支持的 API（这类 API 列表可以在官方文档中查到），Software Layer 也可以作为一种降级方案，让该 View 用 CPU 渲染后以 Bitmap 形式参与后续合成。

限制是：**如果 View 的内容频繁变化，不要使用 Software Layer。** 因为每次内容变化都会导致 Bitmap 缓存失效，需要重新在主线程执行 `buildDrawingCache`，这个过程比较耗时——尤其是硬件加速开启时，每次重建后还需要把 Bitmap 上传到 GPU 纹理。

### LAYER_TYPE_HARDWARE

设置 `LAYER_TYPE_HARDWARE` 后，系统会要求这个 View 子树优先以 hardware layer 的方式参与合成。官方文档明确写到，如果当前层级没有开启硬件加速，`LAYER_TYPE_HARDWARE` 的行为会退化成 software layer。

[已验证: 官方文档, developer.android.com/reference/android/view/View#setLayerType(int,%20android.graphics.Paint)]

在 Android 10 之后的 HWUI 里，手动 `setLayerType(LAYER_TYPE_HARDWARE)` 已经不是属性动画的默认动作。`RenderNode` 自己就有 compositing layer 机制：当 `alpha` 与 `hasOverlappingRendering()` 的组合需要离屏缓冲，或者系统判断这样更省时，它会自动提升为 composition layer。手动强制建层更适合两类场景：

- **Trace 已经看到复杂子树在动画期间被反复 replay/光栅化**：内容本身没变，但 RenderThread 每帧都在 replay 子树绘制命令并重新光栅化
- **需要稳定的离屏合成语义**：例如大 View 子树的 alpha 混合、ColorFilter，或者多帧连续复用同一批绘制结果

如果 View 很简单，或者动画过程中内容一直在变，手动强制建层只会多一层缓存维护成本。

如果 Trace 已经确认强制建层有收益，可以只在动画窗口内短暂启用：

```java
// 动画开始前启用 Hardware Layer
view.setLayerType(View.LAYER_TYPE_HARDWARE, null);
ObjectAnimator animator = ObjectAnimator.ofFloat(view, "rotationY", 0, 180);
animator.addListener(new AnimatorListenerAdapter() {
    @Override
    public void onAnimationEnd(Animator animation) {
        // 动画结束后关闭，释放 GPU 内存
        view.setLayerType(View.LAYER_TYPE_NONE, null);
    }
});
animator.start();
```

为什么要在动画结束后设回 `LAYER_TYPE_NONE`？因为 Hardware Layer 占用的是 GPU 显存，不及时释放会在 GPU 内存紧张时影响其他组件的渲染性能。

## Hardware Layer 的代价

Hardware Layer 不是万能的。它的收益来源于"缓存一次、复用多次"，但缓存本身有代价。

### 代价一：额外的 GPU 内存

每个 Hardware Layer 对应一块 GPU 纹理。如果同时有多个 View 设置了 Hardware Layer，或者 View 面积很大，显存消耗会非常可观。官方推荐只在动画期间启用，动画结束后立即释放。

16KB 页环境还有一个额外因素：GPU 显存分配粒度提升后，小面积硬件层可能产生更多填充浪费。例如一个 100×50 像素的 layer 理论需要约 20KB（RGBA_8888），在 16KB 页粒度下可能因为分配粒度占用更多空间。多个小 layer 累积起来的影响取决于 GPU 驱动的分配策略（sub-allocator、tile-based 渲染的内部缓冲管理等）。对于需要频繁建层/销毁的场景（如列表 item 动画），建议通过 `dumpsys gfxinfo` 和 `adb shell dumpsys meminfo <pkg>` 观察实际的 GPU 内存变化，不要仅凭理论估算做判断。

[待验证: 16KB 页对 GPU 纹理分配的实际影响需在具体设备上用 memtrack/gralloc 统计数据确认]

### 代价二：缓存建立的开销

建立 Hardware Layer 需要"先渲染 View 到纹理，再把纹理合成到窗口"两个步骤。如果 View 本身的绘制非常简单（比如一个纯色背景），那么建立 Hardware Layer 的开销可能比直接绘制还大。在 Perfetto 中可以直接看 RenderThread 上第一个 `buildLayer` slice：如果时长接近甚至超过一个 VSync 周期（16.6ms@60Hz），说明这个 View 的绘制复杂度不足以让缓存回本——与其花时间建纹理，不如直接画。缓存一个代价几乎为零的操作，缓存本身反而成了瓶颈。

### 代价三：缓存失效与重建

这是最容易踩坑的地方。Hardware Layer 缓存的是 View 的"绘制快照"。一旦 View 的内容发生变化（调用了 `invalidate()`、修改了子 View、改变了文本内容等），缓存就失效了，layer 内容被标脏并重绘。当尺寸/可渲染条件仍满足时，HWUI 在现有 layer surface 上重绘受损内容（`createOrUpdateLayer` + `LayerUpdateQueue`）；只有在不再是 layer、不可渲染、尺寸非法等场景下才会释放并重新分配 layer surface。

如果在动画过程中不断修改 View 的内容，就会出现"每帧都重建缓存"的情况——layer 每帧被标脏、重绘，如果尺寸也变了还会重新分配 layer surface——性能反而比不用 Hardware Layer 更差。在 Perfetto 中，这种问题的表现模式非常典型：RenderThread 的 Track 上出现密集的 `buildLayer` slice，每个 VSync 周期一个。如果看到这种模式，第一反应应该是检查该 View 是否在动画过程中被 `invalidate()` 了。

## 何时提升性能，何时反而劣化

高爷通过一个完整的实验（使用 gfxinfo 统计数据）对比了六种场景下的性能表现，数据展示了 Hardware Layer 的正反两面。


### 场景一：属性动画 + 不修改内容

| LayerType | Janky Frames | 99th percentile | 主线程负载 |
|-----------|-------------|-----------------|-----------|
| NONE | 46.67% | 32ms | 高（High input latency=30） |
| SOFTWARE | 3.23% | 16ms | 低（High input latency=0） |
| HARDWARE | 0% | 14ms | 极低（High input latency=0） |

**结论：不做内容修改的属性动画，Hardware Layer 性能最优。** 第一帧建立缓存后，后续帧只需要对纹理做变换，几乎零开销。

在 Perfetto 中可以清楚看到：使用 Hardware Layer 时，动画期间全部是绿帧，RenderThread 的 `flush commands` 耗时极短；而不用 LayerType 时，RenderThread 中 `flush commands` 明显耗时更长，出现黄帧。

### 场景二：属性动画 + 动态修改内容

| LayerType | Janky Frames | 99th percentile | 主线程负载 |
|-----------|-------------|-----------------|-----------|
| NONE | 38.71% | 29ms | 高 |
| SOFTWARE | 41.38% | 32ms | 高 |
| HARDWARE | 46.67% | 32ms | 高 |

**结论：动画过程中修改 View 内容时，Hardware Layer 和 Software Layer 性能反而比不用更差。** 因为每帧内容变化导致缓存失效，每帧都要重建缓存。

在 Perfetto 中的表现是：
- Software Layer：主线程每帧都出现 `buildDrawingCache/SW Layer` slice，执行时间很长
- Hardware Layer：RenderThread 每帧都出现 `buildLayer`，主线程和渲染线程都很忙

### 规律总结

两组实验数据放在一起，规律是：

**不修改内容时**：Hardware Layer ≥ Software Layer > No Layer

**修改内容时**：No Layer > Software Layer ≈ Hardware Layer

这条规律背后的判断是：**缓存的价值取决于命中率。** 内容不变时缓存一直有效，收益巨大；内容频繁变化时缓存一直失效，维护缓存的开销反而成了负担。

在性能优化的实际工作中，这条规律可以转化为一条操作原则：评估某个 View 是否该使用 Hardware Layer 时，先确认动画期间内容是否会变化。内容不变时，Hardware Layer 通常能提升性能；内容会变时，优先把内容变化和动画分离到不同的 View 上，再评估是否使用 Hardware Layer。


## 在 Perfetto 中识别 Hardware Layer 问题

如果怀疑某个卡顿问题与 LayerType 有关，在 Perfetto 中可以关注以下特征：

### Software Layer 缓存失效

在主线程（MainThread）的 slice 中看到重复出现的 `buildDrawingCache/SW Layer for XXXView`，说明 Software Layer 每帧都在重建。排查重点是：这个 View 是不是每帧都在调用 `invalidate()` 或者修改内容？

### Hardware Layer 缓存失效

在 RenderThread 中看到重复出现的 `buildLayer` 调用，说明 Hardware Layer 每帧都在重建。检查逻辑同上。

### Debug 工具：显示硬件层更新

Android 开发者选项中有一个"显示硬件层更新"（Show hardware layers updates）的开关。开启后，当 View 渲染 Hardware Layer 时，整个界面会闪烁绿色。

正常情况下：动画开始时闪烁一次（缓存建立），后续不再闪。
异常情况：整个动画期间持续闪烁绿色——说明缓存每帧都在失效重建。

两个工具配合使用：先用"显示硬件层更新"快速定位问题 View，再用 Perfetto 的 `buildLayer`/`buildDrawingCache` slice 确认根因。


## 与 RenderNode compositing layer 的关系

在 Android 的渲染引擎内部，每个 View 都对应一个 `RenderNode`，View 的绘制命令会记录进这个 `RenderNode` 的 DisplayList。Hardware Layer 在底层对应的就是 compositing layer 语义。

AOSP `frameworks/base/graphics/java/android/graphics/RenderNode.java` 的公开 API 是 `setUseCompositingLayer(boolean forceToLayer, Paint paint)` 和 `getUseCompositingLayer()`。原注释把边界写得很清楚：`RenderNode` 会在“这样更省时”或者 `alpha + hasOverlappingRendering()` 组合需要时，自动提升为 composition layer；`forceToLayer=false` 才是默认且推荐的值。`paint` 只在强制建层时生效，用来给这层额外叠加 blend mode、alpha 和 `ColorFilter`。

RenderNode 的自动升层（compositing layer）条件按版本逐步丰富。Android 10/11 已有 functor 隔离和 alpha+hasOverlappingRendering 的自动升层；Android 12 起可见 ImageFilter、StretchEffect 分支。以 `android-16.0.0_r1` 核验，`RenderProperties::promotedToLayer()` 的当前条件包括：functor 需要隔离、RenderNode 有 ImageFilter、StretchEffect 要求建层、alpha 在 (0,1) 区间（源码条件 `!MathUtils::isZero(mAlpha) && mAlpha < 1`）且 `hasOverlappingRendering()` 为 true，以及尺寸满足 `fitsOnLayer()`。这些条件是确定性的布尔组合，不是绘制指令复杂度评分。满足条件时 HWUI 自动为该 RenderNode 分配离屏缓冲，应用无需手动 `setLayerType`。

[已验证: AOSP android-16.0.0_r1, RenderProperties::promotedToLayer() 条件；functor + alpha+overlap 条件经 AOSP android-10.0.0_r47 核验存在，ImageFilter/StretchEffect 分支经 android-12.0.0_r1 核验存在]

```java
// frameworks/base/graphics/java/android/graphics/RenderNode.java
// @ AOSP android-16.0.0_r1
// 这里只保留公开 API 签名，省略实现。
public boolean setUseCompositingLayer(boolean forceToLayer, @Nullable Paint paint);
public boolean getUseCompositingLayer();
```

边界可以这样划分：`View.setLayerType()` 是 View 侧 API，操作对象是整个 View 子树；`RenderNode.setUseCompositingLayer(...)` 是更底层的 RenderNode API，用来显式要求中间缓冲并附带合成用的 `Paint`。二者谈的是同一类机制，但现代 HWUI 已经会自己做一部分自动建层，不需要应用把每个动画都手动改成 `LAYER_TYPE_HARDWARE`。

[已验证: AOSP android-16.0.0_r1, frameworks/base/graphics/java/android/graphics/RenderNode.java]

## 在 Jetpack Compose 中的对应：graphicsLayer

Jetpack Compose 没有直接暴露 `setLayerType`，对应概念是 `Modifier.graphicsLayer`。官方文档把它描述为“让内容绘制进一个 draw layer”。这个 layer 先提供绘制隔离，再决定是否要栅格化成 offscreen buffer。

这里需要分清两个概念：

- **draw layer**：把一组绘制指令隔离出来，便于单独做 translation、scale、rotation、alpha、shadow 等变换
- **offscreen compositing**：实际分配一块离屏 texture/bitmap，把输出先画进去，再把这块 buffer 合成回目标 surface

`graphicsLayer` 默认只是给出 draw layer 语义，不等于“每次都会创建离屏缓存”。Compose 文档对 `CompositingStrategy` 的描述比较清楚：

- `CompositingStrategy.Auto`：默认策略。`alpha < 1.0f` 或设置了 `RenderEffect` 时，会自动创建 offscreen buffer
- `CompositingStrategy.Offscreen`：总是先栅格化到离屏 texture/bitmap，再做合成
- `CompositingStrategy.ModulateAlpha`：把 alpha 直接作用到每条绘制指令上；如果没有 `RenderEffect`，`alpha < 1.0f` 时也可以不建离屏 buffer，但重叠内容的视觉结果会和 `Auto` 不一样

```kotlin
Box(
    modifier = Modifier.graphicsLayer {
        alpha = 0.7f
        rotationZ = 45f
        compositingStrategy = CompositingStrategy.Auto
    }
)
```

如果只有 layer 属性在变，Compose 可以高效重发这一层的绘制结果，不必重新测量和放置。可一旦 Composable 内容本身频繁变化，离屏层同样要重栅格化，收益会下降。

`rememberGraphicsLayer()` 是 Compose 1.7.0-alpha07+ 提供的另一组 API，主要用来显式创建 `GraphicsLayer`、录制内容并导出 `ImageBitmap`。它更接近 capture / advanced drawing 的能力，不是一个"共享 graphics layer 配置"的通用性能开关。

Compose 1.10 对 `graphicsLayer` 的纹理复用机制做了进一步优化：离屏缓冲池化（offscreen buffer pooling）。之前每次 `graphicsLayer` 需要离屏渲染时都会重新分配 GPU 纹理，用完即释放；1.10 开始，这些纹理会被池化复用。对 LazyLayout 滑动场景，item 离开可视区后其 layer 纹理不销毁，新 item 进入时直接从池中取用，省去了纹理分配和上传的开销；收益需要用掉帧率、GPU 纹理分配次数和 RenderThread 耗时一起确认。

## 与 RenderEffect 的关系

RenderEffect（API 31, Android 12+）与 Hardware Layer 都会用到 **offscreen rendering**，但它们服务的语义不同。

- **Hardware Layer**（`View.setLayerType(LAYER_TYPE_HARDWARE)`）：手动强制建立 offscreen GPU texture
- **RenderEffect**（`View.setRenderEffect(createBlurEffect(...))`）：自动建立 offscreen texture 并施加特效

二者底层都依赖 FBO（Framebuffer Object）在 GPU 显存中分配离屏渲染目标。当 RenderNode 有非 null 的 RenderEffect 时，HWUI 的 SkiaPipeline 会自动为其创建 offscreen FBO，渲染节点内容，执行 blur/color filter/AGSL shader 等特效，再将结果合成到主帧缓冲区。这个过程经 `SkiaOpenGLPipeline::draw(...)` 进入 `SkiaPipeline::renderFrame()`，再经 `renderLayersImpl()` 完成。RenderEffect / ImageFilter 的关键处理在 `RenderNodeDrawable` 与 `RenderNode::updateSnapshotIfRequired()` 一带。

两者的区别在语义上：Hardware Layer 解决的场景是"同一批绘制结果要被连续复用（动画/变换）"，RenderEffect 解决的场景是"要对绘制结果施加视觉特效"。当 RenderEffect 作用在一个内容不变的 View 上时，二者的性能收益类似——offscreen texture 建立一次，后续每帧只需要对纹理做操作。

详见 [7.5 优化策略](file:///Users/gracker/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki/src/part2-performance/ch07-smoothness/05-optimization.md)。

## 与其他章节的关系

Hardware Layer 是 Android 渲染管线中的一个优化手段，它与以下章节密切相关：

- **2.4 Choreographer 与渲染流水线**：Hardware Layer 的缓存建立发生在 `doFrame()` 的 Traversal 阶段，缓存命中时可以跳过后续帧的 draw 流程
- **2.5 MainThread 与 RenderThread 协作**：Hardware Layer 的 `buildLayer` 操作发生在 RenderThread，Software Layer 的 `buildDrawingCache` 发生在 MainThread
- **2.6 SurfaceFlinger 与合成**：Hardware Layer 先由 HWUI 合成进应用窗口 buffer，窗口 buffer 再交给 SurfaceFlinger/HWC 做跨窗口合成；View 级 hardware layer 与 SurfaceFlinger 的窗口 layer 不是同一层级
- **7.1 卡顿定义与 7.5 优化策略**：Hardware Layer 的合理使用是动画场景优化的关键手段，错误使用则是常见的卡顿根因；卡顿分析时 `buildLayer` 反复出现是需要重点排查的模式

## 版本演进

| 版本 | 变更 |
|------|------|
| Android 3.0 (API 11) | 引入 `setLayerType()` API 和 Hardware Layer 机制 |
| Android 4.0 (API 14) | 硬件加速默认开启，Hardware Layer 有了实际运行的基石 |
| Android 4.1 (API 16) | Project Butter 引入 VSync 和 Choreographer，Hardware Layer 的调度节拍与 VSync 同步 |
| Android 5.0 (API 21) | RenderThread 引入，Hardware Layer 的 buildLayer 从主线程移到 RenderThread |
| Android 10 (API 29) | `RenderNode.setUseCompositingLayer(boolean, Paint)` 与 `getUseCompositingLayer()` 作为公开 API 可用 |
| Android 12 (API 31) | Jetpack Compose 1.0 正式发布，`graphicsLayer` Modifier 基于底层 RenderNode compositing layer 机制提供声明式 layer 控制 |
| Android 10/11 (API 29/30) | `promotedToLayer()` 已包含 functor 隔离、alpha+hasOverlappingRendering 自动升层条件 |
| Android 12 (API 31) | 自动升层条件扩展 ImageFilter、StretchEffect 分支 |
| Android 16 (API 36) | 以 `android-16.0.0_r1` 核验当前自动升层条件全貌：functor 隔离、ImageFilter、StretchEffect、alpha+hasOverlappingRendering + fitsOnLayer() |
| Compose 1.10 | `graphicsLayer` 离屏缓冲池化，纹理复用减少 LazyLayout 滑动场景的 GPU 内存分配开销 |

[已验证: 官方文档, developer.android.com/reference/android/view/View#setLayerType(int,%20android.graphics.Paint)]
[已确认: RenderNode 公开 API 自 API 29 (Android 10) 起, developer.android.com/reference/android/graphics/RenderNode]

## 常见问题与误区

### 误区一："开了硬件加速就是开了 Hardware Layer"

这是最常见的混淆。硬件加速是渲染管线的整体策略（GPU vs CPU），Hardware Layer 是针对单个 View 的缓存优化。开启硬件加速不代表任何 View 自动获得 Hardware Layer——所有 View 默认都是 `LAYER_TYPE_NONE`。

### 误区二："属性动画一定要手动开 Hardware Layer"

现代 HWUI 下，translation、scale、rotation、alpha 这类动画经常已经能吃到 RenderNode 的自动 composition layer。手动 `setLayerType(LAYER_TYPE_HARDWARE)` 只有在 Trace 已经证明存在重复重绘，或者需要稳定离屏合成语义时才值得加。如果 View 很简单，或者动画过程中内容一直在变，手动强制建层只会增加缓存维护成本。

### 误区三："设置 Hardware Layer 后就不用管了"

Hardware Layer 占用 GPU 显存。长期保持 `LAYER_TYPE_HARDWARE` 而不释放，会导致显存压力增大。正确做法是：动画开始时设置，动画结束时设回 `LAYER_TYPE_NONE`。

### 误区四："在 Perfetto 中看到 buildDrawingCache 就说明用了 Hardware Layer"

`buildDrawingCache` 出现在主线程，对应的是 **Software Layer**（`LAYER_TYPE_SOFTWARE`）。Hardware Layer 的缓存建立操作 `buildLayer` 出现在 RenderThread。通过 slice 名称就能区分用的是哪种 LayerType。

## 参考资料

- 高爷原创：[Android 中的 Hardware Layer 详解](https://www.androidperformance.com/2019/07/27/Android-Hardware-Layer/)
- [来源: obsidian/Personal-Knowlodge/source/Android-Hardware-Layer.md]
- 官方文档：[Hardware acceleration](https://developer.android.com/guide/topics/graphics/hardware-accel)
- 官方 API：[View.setLayerType()](https://developer.android.com/reference/android/view/View#setLayerType(int,%20android.graphics.Paint))
- AOSP 源码：`frameworks/base/core/java/android/view/View.java`（buildLayer、buildDrawingCache 方法）
- AOSP 源码：`frameworks/base/graphics/java/android/graphics/RenderNode.java`（setUseCompositingLayer/getUseCompositingLayer 方法）
- 推荐阅读：[Android硬件加速原理与实现简介](https://www.mtyun.com/library/hardware-accelerate)
- 推荐阅读：[理解Android硬件加速的小白文](https://juejin.im/post/5a1f7b3e6fb9a0451b0451bb)
- 实验代码与 Trace 文件：[Android_HardwareLayer_Example (GitHub)](https://github.com/Gracker/Android_HardwareLayer_Example)
