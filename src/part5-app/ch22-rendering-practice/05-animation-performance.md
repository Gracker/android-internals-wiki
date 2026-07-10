---
title: "动画性能优化"
chapter: "22.5"
section: "22.5"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1 ViewPropertyAnimator/RenderEffect/View/TransitionManager/Choreographer; Lottie upstream API names spot-checked"
confidence: medium
drafted_date: "2026-05-13"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-07-10"
polish_count: 1
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
  - type: official
    path: "developer.android.com/develop/ui/views/animations/prop-animation"
  - type: official
    path: "developer.android.com/develop/ui/views/animations/transitions"
  - type: source
    path: "github.com/airbnb/lottie-android/LottieAnimationView.java"
tags: [animation, property-animation, lottie, render-effect, transition, motionlayout]
related_chapters: ["22.4", "7.1", "2.5", "2.7"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-10"
last_task9_at: "2026-07-10T07:28:29+08:00"
last_task9_review_log: "logs/deep-review/2026-07-10-07-audit.md"
task9_review_notes: "2026-07-10 Task9 idle-audit AUTO-FIX: P0 0 / P1 1 / P2 0；将 AOSP 验证锚点从 android-16.0.0_r1 升级并固定到 android-17.0.0_r1；复核 ViewPropertyAnimator/RenderEffect/View/TransitionManager/Choreographer 关键行为未变，回到 Task6 复审。详见 logs/deep-review/2026-07-10-07-audit.md。 | 2026-05-14 Task9：needs-rework。P0 0 / P1 1 / P2 2；scaleX 替代宽高动画示例缺少初始/目标状态，帧动画内存估算和 FrameTimeline 版本边界需补。 | 2026-05-28 10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 1；Task2B 已补齐上轮 scaleX 初始状态、帧动画内存口径、FrameTimeline 版本边界；本轮复核未发现 P0/P1。 自动晋升 finalized。"
last_task2b_lite_at: "2026-05-28"
last_task6_at: "2026-07-10T08:12:38+08:00"
last_task6_audit: "2026-07-06"
last_task6_review_log: "logs/review/2026-05-28-10-review.md"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_review_notes: "2026-07-10 Task6 revisiting-review: pass-light-edit;L1 banned word fix (对齐/链路);outline covered;无 L3/L4 回炉项。Task9 auto-fixed 已确认。"
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-07-10T08:12:38+08:00"
finalized_by: openclaw-task9-auto-promote
finalized_date: "2026-07-10"
p0: 0
p1: 0
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-04
last_task9_audit: "2026-07-10"
updated_by: openclaw-task9
updated_date: "2026-07-10"
last_task9_autofix_at: "2026-07-10"
---

# 动画性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 属性动画 vs 帧动画的性能差异
- 🔹 Lottie / RenderEffect 性能注意事项
- 🔹 动画与主线程的关系
- 🔹 转场动画优化

### 扩展（可选深入）

- 🔸 MotionLayout 性能实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解动画性能优化

动画问题很少只属于动画库。一次掉帧可能来自主线程每帧执行属性 setter，也可能来自 `RenderThread` 的纹理上传、`RenderEffect` 的离屏渲染，或者转场期间触发整棵 View 树重新测量。

动画优化可以拆成四类决策：选哪种动画模型、哪些视觉效果会推高 GPU 成本、主线程每帧要做多少事、转场是否扩大了布局和绘制范围。具体的渲染管线原理详见 2.5 节；动画侧的排查重点是模型选择、GPU 成本、主线程工作量和转场范围。


## 属性动画 vs 帧动画的性能差异

属性动画和帧动画的差异，不在于“哪个 API 更高级”，而在于每一帧到底改了什么。

| 类型 | 每帧工作 | 适合场景 | 性能风险 |
|------|----------|----------|----------|
| `ViewPropertyAnimator` / 属性动画 | 修改 `translationX/Y`、`alpha`、`scale` 等 View 属性 | 位移、缩放、透明度、轻量交互反馈 | 动画属性如果触发布局或复杂重绘，主线程成本会上升 |
| `ObjectAnimator` | 反射或属性对象调用目标 setter | 非 View 属性、业务状态驱动动画 | setter 里如果调用 `requestLayout()` 或分配对象，会把动画变成每帧业务执行 |
| 帧动画 / 逐帧 Drawable | 每帧切换一张图或一段绘制资源 | 小尺寸、短时长、强设计稿还原的动效 | 图片解码、纹理上传、内存占用和包体积都会放大 |
| 自绘动画 | 每帧 `invalidate()` 后进入 `onDraw()` | 波形、进度、粒子、业务图形 | `onDraw()` 分配对象或路径计算过重，容易形成稳定掉帧 |

AOSP `ViewPropertyAnimator` 的类注释直接说明：同时动画多个 View 属性时，它会把多次属性变化合并到一次 invalidation，而不是让每个属性各自触发一次刷新。这个特性适合做 `alpha`、`translationX/Y`、`scaleX/Y`、`rotation` 这类不改变测量结果的动画。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/ViewPropertyAnimator.java]
[已验证: 官方文档, developer.android.com/develop/ui/views/animations/prop-animation]

属性动画的安全边界是：动画过程中只更新渲染属性，不更新布局约束。下面这类写法会让每一帧都进入 `requestLayout()`，再触发 measure/layout/draw，代价远高于只更新 RenderNode 变换属性。

```kotlin
// 反例：每帧修改 layoutParams，动画成本扩散到整棵 View 树
ValueAnimator.ofInt(0, targetWidth).apply {
    duration = 240
    addUpdateListener { animator ->
        val width = animator.animatedValue as Int
        view.layoutParams = view.layoutParams.apply { this.width = width }
        view.requestLayout()
    }
}.start()
```

同样的视觉效果如果能用 `scaleX` 或裁剪区域表达，就不要每帧改宽高：

```kotlin
// 更低成本：只修改变换属性，不触发布局
// 前提：View 当前处于 collapsed 状态（scaleX = 0f），展开到正常宽度
view.pivotX = 0f
view.scaleX = 0f // 确保初始状态为收起
view.animate()
    .scaleX(1.0f) // 展开到正常宽度
    .setDuration(240)
    .withLayer()
    .start()
```

`withLayer()` 会在动画期间临时启用硬件 layer，动画结束后恢复原 layer type。适用对象是内容复杂但动画期间内容不变的 View，例如透明度和位移动画。对每帧内容都变化的 View 开 layer 会反复更新纹理，收益会被纹理重建抵消。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/ViewPropertyAnimator.java]

帧动画的主要风险来自资源侧。30 张 1920×1080 RGBA_8888 图片解码后约 248.8 MB，按二进制单位约 237.3 MiB，计算口径是 `1920 × 1080 × 4 × 30`。压缩包体积、硬件位图、采样缩放和目标纹理格式会改变实际占用，但解码后内存与 GPU 纹理上传压力仍会集中到动画开始后的几帧。帧动画只建议用于小尺寸、短时长、不可用矢量或属性动画表达的视觉效果；长时长动效优先评估矢量、Lottie 或自绘方案。

[已确认: 帧动画内存估算按 RGBA_8888 解码后内存计算，实际项目需结合图片尺寸、采样策略和纹理格式复核]

## Lottie / RenderEffect 性能注意事项

Lottie 和 RenderEffect 都能把设计效果交给运行时渲染，但它们的性能瓶颈不同。Lottie 的瓶颈通常在矢量路径、mask、matte、图片资源和每帧求值；RenderEffect 的瓶颈通常在离屏 buffer、模糊半径、GPU 填充率和合成路径。

### Lottie：先判断动画复杂度，再判断渲染模式

Lottie 官方源码中 `LottieAnimationView.setRenderMode()` 的注释说明，默认 `AUTOMATIC` 会在多数场景使用硬件加速；但 pre-Pie 设备上的 dash path、超过 4 个 mask/matte，以及多个大面积 mask/matte 场景可能走软件渲染或建议同时测试两种模式。源码也提供 `setPerformanceTrackingEnabled()` 和 `getPerformanceTracker()`，用于定位慢 layer。

[已验证: github.com/airbnb/lottie-android/lottie/src/main/java/com/airbnb/lottie/LottieAnimationView.java]

实战里可以按下面的顺序处理：

1. **设计稿约束**：控制 layer 数、mask/matte 数量、路径点数量，避免在一个首屏动画里放大面积半透明遮罩。
2. **资源约束**：图片资源单独评估尺寸和复用；能用矢量表达的元素不要导出成多张大图。
3. **运行时约束**：首屏或列表内 Lottie 禁止同步解析 JSON；composition 缓存打开后，再评估内存占用。
4. **渲染模式验证**：同一动画在目标机型上对比 `AUTOMATIC`、`HARDWARE`、`SOFTWARE`。API 31+ 优先看 `FrameTimeline` jank，API 29-30 回退到 UI Thread、RenderThread `DrawFrame`、SurfaceFlinger/gfx 帧间隔和 CPU 使用率。

Lottie 不适合放在 RecyclerView 大量 item 中同时播放。列表里如果需要动效，只让可见且有交互焦点的 item 播放，其余 item 停在静态帧。这个策略能同时压住 CPU 求值、GPU 绘制和电量消耗。

### RenderEffect：限制作用范围和模糊半径

`RenderEffect` 是作用在 `RenderNode` 上的中间渲染步骤。AOSP `RenderEffect.java` 注释说明，它可以配置到 `RenderNode`，也可以通过 `View.setRenderEffect()` 配置到 View 背后的 RenderNode；`View.setRenderEffect()` 内部调用 `mRenderNode.setRenderEffect()` 后触发 `invalidateViewProperty(true, true)`。

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/RenderEffect.java]
[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/View.java]

RenderEffect 的优化要点是缩小输入内容，而不是只盯着 API 调用本身。全屏 blur、列表背景 blur、滑动过程中不断变化的 blur 半径，都可能让 RenderThread 反复处理大面积纹理。更稳妥的做法是：

- 对小区域卡片、浮层、局部背景使用 RenderEffect；全屏背景优先使用预模糊位图或静态截图。
- 动画期间避免连续改变 blur radius；如果视觉允许，使用 2-3 个离散半径档位。
- 对低端机或省电模式提供降级：关闭 blur、降低半径、改用半透明色块。
- Perfetto 中同时看 UI Thread、RenderThread 和 GPU 相关 slice；如果 UI Thread 很短但 RenderThread `DrawFrame` 拉长，问题多半在 GPU 绘制或离屏合成。

下面的封装把 RenderEffect 限制在 API 31+，并集中处理降级：

```kotlin
fun View.applyBlurIfSupported(radiusPx: Float, enabled: Boolean) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return
    if (!enabled) {
        setRenderEffect(null)
        return
    }

    val radius = radiusPx.coerceIn(0f, 24f)
    setRenderEffect(
        RenderEffect.createBlurEffect(
            radius,
            radius,
            Shader.TileMode.CLAMP
        )
    )
}
```

这段代码的重点是半径上限和关闭路径。半径上限不是通用数值，正式接入前要用目标机型的 trace 校准；关闭路径保证低端设备、省电模式和业务降级能直接清掉 effect。

## 动画与主线程的关系

动画帧由 Choreographer 驱动。每个 VSync 周期里，主线程处理 input、animation、traversal 等阶段；RenderThread 再同步 RenderNode 状态并执行绘制。2.5 节已经展开主线程和 RenderThread 的协作；动画侧排查时，重点看每帧有多少工作留在 UI Thread，以及哪些绘制成本转移到了 RenderThread。

[详见 2.5 节]

动画卡顿通常分三类：

| 表现 | 主要观察点 | 常见原因 | 处理方式 |
|------|------------|----------|----------|
| UI Thread `doFrame` 超时 | `Choreographer#doFrame`、`performTraversals`、业务 trace | 每帧执行计算、分配对象、触发布局 | 移出每帧计算，缓存结果，避免 `requestLayout()` |
| RenderThread `DrawFrame` 超时 | `syncFrameState`、`DrawFrame`、纹理上传、GPU slice | DisplayList 太复杂、RenderEffect、图片纹理上传 | 减少绘制命令，预上传图片，缩小效果范围 |
| 帧率稳定但功耗高 | CPU 频率、GPU 频率、后台播放状态 | 不可见动画仍在跑，Lottie 或粒子动效常驻 | 页面不可见时暂停，列表 item 离屏时停止 |

属性动画的 update listener 里不要做重活。下面这种写法在功能上没问题，但它把路径计算放到每一帧：

```kotlin
ValueAnimator.ofFloat(0f, 1f).apply {
    addUpdateListener { animator ->
        val progress = animator.animatedFraction
        chartPath.reset()
        rebuildPath(chartPath, data, progress) // 每帧遍历 data
        chartView.invalidate()
    }
}.start()
```

如果 `data` 不变，路径采样表可以在动画开始前准备好，每帧只读当前位置：

```kotlin
val samples = buildPathSamples(data)
ValueAnimator.ofFloat(0f, 1f).apply {
    addUpdateListener { animator ->
        chartView.progress = animator.animatedFraction
        chartView.samples = samples
        chartView.invalidate()
    }
}.start()
```

自绘动画还要遵守 22.4 节的规则：`onDraw()` 零分配，`invalidate()` 只覆盖变化区域，不在 `onDraw()` 里递归触发下一帧。持续动画用 `ValueAnimator` 或 `postInvalidateOnAnimation()` 管住帧节奏。

[详见 22.4 节]

后台动画也要纳入功耗治理。页面 `onStop()` 后还在播放的属性动画、Lottie、定时器刷新，会在用户不可见时继续占用 CPU/GPU。页面不可见时暂停，回到前台再按业务状态恢复；这类问题适合通过生命周期钩子和页面级动画管理器统一兜底。

## 转场动画优化

转场动画的问题在于范围容易失控。`TransitionManager.beginDelayedTransition(sceneRoot)` 会捕获 sceneRoot 下 View 层级在下一帧前后的变化，并为差异创建动画。sceneRoot 选得越大，状态捕获、布局变化和动画对象数量就越多。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/transition/TransitionManager.java]
[已验证: 官方文档, developer.android.com/develop/ui/views/animations/transitions]

转场优化的第一条规则：sceneRoot 只包住变化区域。不要在 Activity 根布局上随手调用 `beginDelayedTransition()`，除非整个页面都要参与转场。

```kotlin
// 只让筛选栏区域参与转场
TransitionManager.beginDelayedTransition(filterContainer, AutoTransition().apply {
    duration = 180
    excludeChildren(recyclerView, true)
})
filterPanel.isVisible = !filterPanel.isVisible
```

这段代码有两个约束：转场根节点是 `filterContainer`，列表被排除。这样展开筛选栏时，RecyclerView 不会因为父级转场捕获而创建大量 item 动画。

常见转场风险和处理方式：

| 风险 | 触发方式 | 处理方式 |
|------|----------|----------|
| 大范围布局重算 | 根布局转场、多个子树同时 `requestLayout()` | 缩小 sceneRoot，拆分局部转场 |
| 列表 item 被卷入 | RecyclerView 位于 sceneRoot 内 | `excludeChildren(recyclerView, true)` 或转场根节点避开列表 |
| 动画对象过多 | 多个 View 同时改变 bounds / alpha / translation | 合并状态变化，只保留关键视觉元素 |
| 低端机转场不稳定 | bounds 动画叠加阴影、圆角、blur | 提供无 blur / 短时长 / 直接切换降级 |

转场结束后要清理临时状态，例如硬件 layer、禁用的点击态、临时 elevated shadow。状态没恢复会让后续页面一直带着额外合成成本。

## 扩展

### 🔸 MotionLayout 性能实践

MotionLayout 适合复杂的多属性协同动画：一个进度值同时驱动位置、尺寸、透明度、约束和关键帧。它的优势是把动画关系声明在 `MotionScene` 中，减少业务代码里每帧手写 setter 的机会；代价是约束求解和布局变化可能被带到动画过程中。

[已验证: 官方文档, developer.android.com/develop/ui/views/animations/motionlayout]

接入 MotionLayout 时按三步检查：

1. **约束变化是否必要**：如果只是位移、透明度、缩放，优先使用 View 属性动画；MotionLayout 更适合多元素联动和复杂状态切换。
2. **是否每帧触发布局**：动画中改变 `layout_width/height`、约束关系、文本内容，都会扩大主线程成本；能用 transform 表达的效果不要改约束。
3. **是否容易降级**：复杂首屏动效要有简化版 MotionScene 或直接跳过动画的路径，尤其是低端机和省电模式。

MotionLayout 的调试重点放在 trace 里每帧成本是否稳定；动画能跑只是最低要求。发现 `performTraversals` 跟着 MotionLayout 进度稳定拉长时，先减少参与动画的子 View 数量，再把尺寸变化改成 scale / translation；如果仍然超时，再拆成多个小的 MotionLayout。

## 上线前检查清单

- 属性动画只修改渲染属性；涉及宽高、约束和文本变化的动画必须单独压测。
- `ViewPropertyAnimator.withLayer()` 只用于内容稳定的 alpha / translation / scale 动画，结束后确认 layer 恢复。
- Lottie 动画限制 layer、mask、matte 和图片资源数量，首屏和列表场景禁止同步解析。
- RenderEffect 限制作用范围和 blur 半径，低端机、省电模式、后台状态有关闭路径。
- 转场动画只包住变化区域，RecyclerView / ViewPager2 默认排除。
- Perfetto 在 API 31+ 同时看 UI Thread、RenderThread、FrameTimeline 和 CPU/GPU 频率；API 29-30 用 UI Thread、RenderThread、SurfaceFlinger/gfx 帧间隔和调度信号推断卡顿。

## 参考资料

- [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/ViewPropertyAnimator.java]
- [已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/RenderEffect.java]
- [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/view/View.java]
- [已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/transition/TransitionManager.java]
- [已验证: github.com/airbnb/lottie-android/lottie/src/main/java/com/airbnb/lottie/LottieAnimationView.java]
- [引用: developer.android.com/develop/ui/views/animations/prop-animation]
- [引用: developer.android.com/develop/ui/views/animations/transitions]
- [引用: developer.android.com/develop/ui/views/animations/motionlayout]
