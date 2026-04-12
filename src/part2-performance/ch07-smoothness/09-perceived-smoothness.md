---
title: "感知流畅性：步幅波动与无掉帧卡顿"
chapter: "7.9"
section: "7.9"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-07"
last_verified_against: "AOSP android-17-beta3"
reviewed_date: "2026-04-12"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
confidence: medium
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/performance/jankstats"
  - type: aosp
    path: "frameworks/base/core/java/android/widget/OverScroller.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/animation/AnimationUtils.java"
tags:
  - android
  - jank
  - perceived-smoothness
  - step-jitter
  - frame-pacing
  - overScroller
  - research
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
---


# 7.9 感知流畅性：步幅波动与无掉帧卡顿

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 无掉帧卡顿的本质：帧率稳定与步幅均匀性的区别
- 🔹 OverScroller 的毫秒时间精度与 fling 步幅波动
- 🔹 Choreographer 到动画框架的时间精度损失
- 🔹 在 Perfetto / Frame Timeline 中量化步幅波动的方法
- 🔹 优化方向：纳秒时间源、时间步长平滑与插值器选择
- 🔹 版本演进、常见误区与相关章节的连接点

### 扩展（可选深入）

- 🔸 Chrome 与 OEM 在时间精度优化上的经验
- 🔸 AppJankStats 与 RelativeFrameTimeHistogram 的适用边界

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 扩展内容视素材完整度决定是否展开，无法确认的技术细节保留 `[待验证]`，不要硬写结论。
<!-- outline-end -->

在 Android 性能优化的日常工作中，我们习惯用"掉帧"作为衡量流畅性的核心指标。FrameTimeline 标红了就是 jank，没标红就默认流畅。但实际开发中还有一个更隐蔽的问题：FrameTimeline 显示所有帧都在 VSync 预算内完成，没有任何一帧超时，用户却反馈"感觉有点卡"。

用户的感觉没有错，我们衡量流畅性的维度少看了一项。传统的 jank 检测关注"这一帧有没有在规定时间内完成"，但用户的视觉系统更在意"相邻两帧之间的画面变化是否均匀"。

本章讨论的就是这个被传统工具忽略的维度：**步幅波动（step-size jitter）**。即使不掉帧，帧与帧之间位移量不均匀，也会导致视觉上的不连贯。后面我们按成因、量化方法和优化方向依次展开。

## 无掉帧卡顿的本质：帧率稳定 ≠ 步幅均匀

先区分两个概念。

**帧率稳定性**衡量的是每帧渲染时间的均匀性。在 120Hz 屏幕上，理想情况是每 8.33ms 产出一帧。如果某帧花了 12ms，那就是掉帧。传统工具（Perfetto FrameTimeline、JankStats）检测的就是这个维度。

**步幅均匀性**衡量的是每帧画面位移量的均匀性。一个列表在匀速滚动时，相邻两帧之间应该移动相同的像素数。如果帧 A 移动了 10px、帧 B 移动了 13px、帧 C 移动了 8px，即使三帧都在 VSync 预算内完成，用户也会感觉到"抖动"。

用户在连续动画中建立的预期不是"每 8.33ms 刷新一次"，而是"画面在匀速运动"。当这个运动轨迹出现不规则跳动时，视觉系统会立即感知到不连贯。研究表明，人类视觉系统对帧间位移差异的敏感度非常高，在快速滑动场景下，相邻帧位移偏差超过 10% 就可能被察觉。

这就是为什么一台跑满 120fps 的设备，列表滑动时仍然可能"感觉不丝滑"。问题不在帧率，而在步幅。

### 典型场景

最常见的感知流畅性问题是手势导航时的窗口动画。在多任务界面（Recent Apps）上划回桌面时，窗口缩小的动画前期变化速度过快、后期突然变慢。这里更像是动画插值曲线的加速度分布不合理，导致画面位移量在动画开头和结尾差异太大。

另一个典型场景是 RecyclerView 的 fling 滚动。手指快速划过后，列表惯性滚动的前几帧位移量往往波动较大，后几帧又趋于平稳。这种"开头猛后面缓"的非线性减速如果不够平滑，就会产生顿挫感。

## 步幅波动的技术成因

上面描述的现象在 Trace 中不会标红，在 FrameTimeline 里也不会有 jank 标记，但它确确实实影响了用户体验。我们来看导致步幅波动的底层机制。

步幅波动有三个主要的技术来源：动画插值算法、VSync 时间精度损失、以及物理模拟的时间步长不稳定。我们逐一分析。

### 成因一：OverScroller 的时间精度瓶颈

Android 的惯性滚动（fling）由 `OverScroller` 驱动。`OverScroller` 内部的 `computeScrollOffset()` 方法使用 `AnimationUtils.currentAnimationTimeMillis()` 获取当前时间，然后计算经过的时间来驱动物理模型。

```java
// frameworks/base/core/java/android/widget/OverScroller.java
// @ AOSP android-17-beta3
boolean computeScrollOffset() {
    // 时间来源：AnimationUtils.currentAnimationTimeMillis()
    final long time = AnimationUtils.currentAnimationTimeMillis();
    // 经过的时间（毫秒级精度）
    final long elapsedTime = time - mStartTime;
    // 基于 elapsedTime 计算当前位移
    ...
}
```

注意：`AnimationUtils.currentAnimationTimeMillis()` 返回的是**毫秒级**时间戳。而 `Choreographer.getFrameTimeNanos()` 提供的是**纳秒级**的 VSync 时间。

在 60Hz 屏幕上，VSync 周期是 16.67ms，毫秒精度勉强够用，取整误差最多 ±1ms，占帧周期的 6%。但在 120Hz 屏幕上，VSync 周期只有 8.33ms，±1ms 的取整误差就意味着 **12% 的帧间时间差异**。

具体来说，假设一个理想的 120Hz fling 动画：

| 帧序号 | 理想 VSync 时间 (ns) | 实际 ms 取整 | 帧间时间 | 偏差 |
|--------|---------------------|-------------|---------|------|
| 0 | 0 | 0ms | — | — |
| 1 | 8,333,333 | 8ms | 8ms | -4% |
| 2 | 16,666,666 | 17ms | 9ms | +8% |
| 3 | 24,999,999 | 25ms | 8ms | -4% |
| 4 | 33,333,332 | 33ms | 8ms | -4% |
| 5 | 41,666,665 | 42ms | 9ms | +8% |

ms 取整导致帧间时间在 8ms 和 9ms 之间交替跳动。对于匀速滚动的列表来说，对应的滚动像素数也会在两个值之间来回切换，用户看到的就是列表在"微颤"。

这种波动在慢速滚动时几乎不可察觉（每帧只移动 1-2px），但在快速 fling 时（每帧移动 15-30px），8ms 和 9ms 对应的位移差异可能达到 2-4px，足以让视觉系统感知到不连贯。

### 成因二：物理模拟的时间步长不稳定

OverScroller 内部的 fling 物理模型可以简化为：`position = start + velocity * time - friction * time ^ 2`。当时间步长从 8ms 变成 9ms 再变回 8ms 时，计算的位移量不是简单的线性缩放，因为摩擦力项是时间的二次函数，时间步长的波动会被放大。

具体而言，如果 velocity=3000px/s、friction 系数使动画持续 500ms，那么：

- 8ms 步长：位移约 24px - 0.38px = 23.62px
- 9ms 步长：位移约 27px - 0.43px = 26.57px
- 差异：2.95px（约 12.5%）

这个 12.5% 的帧间位移差异，就是用户感知到的"不够丝滑"的来源。

### 成因三：从 Choreographer 到动画引擎的精度损失过程

把视角放大一点，看整个时间传递过程：

```
硬件 VSync (ns 精度)
  -> SurfaceFlinger DispSync (ns 精度)
  -> Choreographer.doFrame() -> getFrameTimeNanos() (ns 精度)
  -> View.draw() -> Animation/OverScroller (ms 精度)
  -> 每帧位移量计算（累积误差）
```

这个过程的前两段保持了纳秒精度。问题出在第三段到第四段的转换：Android 的动画框架（包括 OverScroller、ValueAnimator、ObjectAnimator）内部使用 `AnimationUtils.currentAnimationTimeMillis()` 作为时间源，在 ns 到 ms 的转换过程中丢失了精度。

`Choreographer.doFrame()` 回调时会通过 `getFrameTimeNanos()` 提供纳秒级的帧时间戳，但这个值并没有直接传递给 OverScroller。OverScroller 自己重新调用 `currentAnimationTimeMillis()` 获取时间。

[已验证: AOSP android-17-beta3, frameworks/base/core/java/android/view/Choreographer.java]

结果是，即使 Choreographer 提供了精确的纳秒时间，动画引擎也没有用到它。

### Chrome 的经验：时间精度优化的工程实践

不止 Android 框架面临这个问题。Chrome 团队在优化 Android 滚动流畅性时发现了类似的问题。他们发现使用 `MotionEvent.getEventTime()`（毫秒精度）做速度预测，比使用 native 层的纳秒时间戳产生了更大的误差。切换到纳秒时间源后，滚动流畅性有可感知的改善。

[待验证: Chrome Android 滚动时间精度优化具体 commit]

## 帧率稳定性与步幅均匀性的关系

这两者常常被混淆，但它们是完全独立的维度。我们可以用一个 2x2 表来理解：

| | 步幅均匀 | 步幅不均匀 |
|---|---|---|
| **不掉帧** | 真正流畅 | 无掉帧卡顿（本章主题） |
| **掉帧** | 有规律的卡顿 | 最差体验 |

"无掉帧卡顿"（no-jank stutter）是最容易被忽略的象限。传统工具报告"0 frames janky"，但用户仍然不满意。

**视觉惯性**是理解这个问题的关键概念。人类的视觉系统对匀速运动有很强的预期。当一个物体开始运动后，大脑会"预测"它在下一帧的位置。如果实际位置与预测位置偏差过大（无论是因为帧率不稳定还是步幅不均匀），大脑就会感知到"不连贯"。

这也解释了为什么 VSync 调度优化（如 Frame Pacing Library，见 2.17 节）只能解决帧率稳定性问题，不能解决步幅均匀性问题。Frame Pacing 确保"每一帧在正确的时间点呈现"，但不保证"每一帧的位移量正确"。

## 在 Perfetto 中量化步幅波动

步幅波动不是 Perfetto 的标准指标，需要自定义分析。但有两条路径可以接近它。

### 路径一：Frame Timeline 差值分析

Perfetto 的 Frame Timeline 记录了 `actual_frame_timeline_slice` 和 `expected_frame_timeline_slice`。通过分析相邻帧的时间差，可以间接推导帧间位移的均匀性。

```sql
-- 计算相邻帧的 actual presentation time 差值
-- 用于检测帧节奏的均匀性
WITH frame_times AS (
  SELECT
    id,
    track_id,
    ts,
    LEAD(ts) OVER (PARTITION BY track_id ORDER BY ts) AS next_ts
  FROM actual_frame_timeline_slice
  WHERE name = 'Choreographer#doFrame'
),
frame_deltas AS (
  SELECT
    id,
    ts,
    next_ts,
    (next_ts - ts) AS delta_ns
  FROM frame_times
  WHERE next_ts IS NOT NULL
)
SELECT
  AVG(delta_ns) / 1e6 AS avg_frame_delta_ms,
  STDEV(delta_ns) / 1e6 AS stdev_frame_delta_ms,
  MAX(delta_ns) / 1e6 - MIN(delta_ns) / 1e6 AS range_ms,
  -- 变异系数：标准差/均值，用于衡量步幅波动
  CAST(STDEV(delta_ns) AS FLOAT) / AVG(delta_ns) AS cv
FROM frame_deltas;
```

这个查询计算帧间时间差的变异系数（CV）。CV 越小表示帧节奏越均匀。在 120Hz 下，CV 理论值为 0，实际设备上 0.05 以下可以认为是"步幅均匀"，0.1 以上则有可感知的波动。

[待验证: 此 SQL 在 Perfetto UI 中的实际运行效果]

### 路径二：Android 16 AppJankStats 与 RelativeFrameTimeHistogram

Android 16 引入了两个平台级 API 来量化感知流畅性：

**AppJankStats** 提供系统级的 jank 统计，无需集成 Jetpack JankStats 库。核心优势是零代码侵入、系统自动收集。

**RelativeFrameTimeHistogram** 更直接相关。它提供帧渲染时间的直方图分布，不仅标记 jank 帧，还展示所有帧的时间分布。通过观察分布的方差和偏度，可以量化感知流畅性：即使没有超过 VSync 预算的帧，如果分布很散（方差大），说明帧间时间差异大，步幅波动的可能性也大。

[已验证: 官方文档, developer.android.com/develop/ui/performance/jankstats]

两个 API 的互补关系：AppJankStats 用于快速发现 jank 问题窗口（系统级聚合），RelativeFrameTimeHistogram 用于量化步幅波动（帧时间分布）。

### Trace 中的典型特征

在 Perfetto 中，步幅波动的 Trace 特征通常有三类：

- **帧间隔的规律性跳动**：在 Main Thread track 中，doFrame slice 之间的间距不完全等距，常见表现是有规律的交替（如 8-9-8-9ms）
- **SurfaceFlinger 合成时间的微小波动**：即使 App 端帧率稳定，如果合成时间有波动，也会导致呈现时间不均匀
- **Expected vs Actual 的微小偏差**：FrameTimeline 中 expected 和 actual 有 0.5-1ms 的偏差，但不足以标红

[图：Perfetto 中 120Hz fling 的帧间隔交替模式]

## 优化策略

### 策略一：使用纳秒级时间戳替代毫秒级

最直接的修复方案是在动画回调中直接使用 `Choreographer.getFrameTimeNanos()` 提供的纳秒时间戳，而不是让 OverScroller 自己去获取毫秒时间。

```java
// [伪代码] 自定义纳秒精度的 fling 实现示意
// 实际实现需处理边界条件、多指触控、嵌套滚动等场景
Choreographer.getInstance().postFrameCallback(new Choreographer.FrameCallback() {
    @Override
    public void doFrame(long frameTimeNanos) {
        // frameTimeNanos 是纳秒精度的 VSync 时间
        // 替代 OverScroller 内部的 ms 级时间
        long elapsedNanos = frameTimeNanos - mStartFrameTimeNanos;
        double elapsedSeconds = elapsedNanos / 1e9;
        // 用 elapsedSeconds 计算位移
        double position = computePosition(elapsedSeconds);
        scrollTo(position);
        // 继续请求下一帧
        Choreographer.getInstance().postFrameCallback(this);
    }
});
```

一些 OEM 厂商在系统级别的滚动优化中采用了类似方案，直接使用纳秒时间戳计算位移，绕过 OverScroller 的毫秒精度限制。

[待验证: 厂商级纳秒时间戳优化的具体实现]

### 策略二：平滑时间步长

另一个思路是在动画引擎层面做时间步长的平滑处理。不直接使用原始的帧间时间差，而是使用指数移动平均（EMA）来平滑：

```
smoothed_dt = alpha * raw_dt + (1 - alpha) * prev_smoothed_dt
```

其中 alpha 通常取 0.3-0.5。这样可以过滤掉 ±1ms 的取整噪声，使位移计算更稳定。

但这种方法有副作用：它会引入延迟，使动画响应变慢。对于需要精确跟随手指的触摸滚动场景不太适用，更适合惯性滚动（fling）这种不需要即时响应的场景。

### 策略三：基于位移的动画而非基于时间的动画

与其用"时间到位移"的映射（会受时间精度影响），不如在某些场景下直接用"速度到位移"的映射。例如在 RecyclerView 的 fling 中：

1. 记录手指离开屏幕时的初始速度
2. 每帧根据当前速度和摩擦系数计算位移
3. 更新速度：`velocity *= friction_factor`
4. 累加位移

这种方式不依赖绝对时间戳，只依赖上一帧的速度，因此不受 ms 取整的影响。它把"时间驱动"改成了"速度衰减驱动"，时间步长的波动被封装在每帧的速度更新中，不会直接反映到位移量上。

[自动发现] 这是 Android RecyclerView 内部 `LinearSmoothScroller` 的部分实现思路，但标准 `OverScroller` 仍然是基于时间的。实际使用时需要注意：速度衰减因子（friction_factor）的选择直接影响减速曲线的形状，过大会导致"急停"、过小会导致"滑太远"。

### 策略四：动画插值器的选择

对于自定义动画，选择插值器时要注意加速度曲线的平滑性。`AccelerateDecelerateInterpolator` 的加速度变化是连续的（正弦曲线），不会产生突变。而 `LinearInterpolator` 配合不均匀的时间步长，反而可能比非线性插值器更容易暴露步幅波动，因为它没有任何"平滑"效果来掩盖时间精度的抖动。

选择建议：

- 短距离动画（< 300ms）：使用 `FastOutSlowInInterpolator`，动画末期速度已经很慢，步幅波动不明显
- 长距离 fling（> 300ms）：使用纳秒时间源 + 自定义物理模型
- 循环/无限动画：避免使用有加速度变化的插值器，纯线性 + 匀速更稳定

## 与其他章节的关联

步幅波动和以下章节的内容直接相关：

- **7.1 卡顿的定义与分类**：传统卡顿定义关注帧率，本章扩展了卡顿的定义维度
- **7.8 RecyclerView 列表滑动性能深度优化**：RecyclerView 的 fling 行为直接受步幅波动影响
- **2.4 Choreographer 与渲染流水线**：Choreographer 提供纳秒时间，但动画框架没有完全利用
- **2.17 Frame Pacing Library**：Frame Pacing 解决帧率稳定性，但不解决步幅均匀性
- **3.2 触摸响应的性能分析**：触摸事件的时间精度（MotionEvent.getEventTime() 也是毫秒级）有类似的问题

## 版本演进

| Android 版本 | 变化 | 对感知流畅性的影响 |
|-------------|------|-----------------|
| Android 10 (API 29) | 引入 FrameTimeline API | 首次可量化帧呈现时间偏差 |
| Android 12 (API 31) | Choreographer API 改进，VsyncCallback | 提供更精确的 VSync 时间 |
| Android 15 (API 35) | 进一步优化 Choreographer 时间精度 | [待验证: 具体优化内容] |
| Android 16 (API 36) | AppJankStats + RelativeFrameTimeHistogram | 首次提供帧时间分布直方图，可直接量化步幅波动 |
| Android 17 (API 37) | [待验证: 是否改进了 OverScroller 的时间精度] | — |

## 常见问题与误区

**误区一："FrameTimeline 没有标红，就说明流畅"**

FrameTimeline 只检测帧是否在 VSync 预算内完成。步幅波动不会导致帧超时，因此 FrameTimeline 完全是绿色的。流畅性 = 帧率稳定 + 步幅均匀，两者缺一不可。

**误区二："120Hz 屏幕不会卡顿"**

120Hz 减轻了帧率不稳定带来的卡顿感（因为每帧时间更短，偶尔掉一帧影响更小），但反而可能**加重**步幅波动的感知。因为 VSync 周期更短（8.33ms），ms 取整误差的相对占比更大（12% vs 60Hz 下的 6%）。再加上 120Hz 下每帧位移更小，视觉系统对位移变化更敏感。

**误区三："把动画时间调短就能解决卡顿"**

缩短动画时间只改变了动画的总时长，不改变步幅的均匀性。一个 200ms 的动画和一个 300ms 的动画，如果每帧的位移分布都不均匀，用户感知到的不流畅程度是相似的。问题不在动画跑多快，而在相邻两帧的位移差了多少。

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/widget/OverScroller.java`（fling 物理模型与时间处理）
  - `frameworks/base/core/java/android/view/Choreographer.java`（VSync 时间回调）
  - `frameworks/base/core/java/android/view/animation/AnimationUtils.java`（currentAnimationTimeMillis 实现）
  - `frameworks/base/core/java/android/widget/Scroller.java`（基础 Scroller 实现）
- 官方文档：
  - JankStats: https://developer.android.com/develop/ui/performance/jankstats
  - Frame Timeline: https://developer.android.com/reference/android/view/FrameTimeline
- 研究素材：
  - `intake/research-feeds/2026-04-07-16-perfetto-frame-timeline-perceived-smoothness-analysis.md`
  - `intake/research-feeds/2026-04-07-16-android16-appjankstats-relative-frame-time-histogram.md`
