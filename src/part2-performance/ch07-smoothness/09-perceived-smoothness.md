---

title: "感知流畅性：步幅波动与无掉帧卡顿"
chapter: "7.9"
section: "7.9"
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-16"
last_verified_against: "AOSP android-16.0.0_r1; Android 17 public tag unavailable"
task6_reviewed_date: "2026-06-16"
last_task6_audit: "2026-06-16"
review_type: "task6-writing-quality-review"
confidence: medium
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
rework_count: 3
rework_date: 2026-05-05
rework_by: task2b-rework
sources:
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
tags: [perceived-smoothness, step-jitter, frametimeline, overscroller, android-performance]
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-16"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-16T17:44:26+08:00"
task9_review_notes: "2026-06-16 Task9 idle audit: AUTO-FIX P1 version anchor. InputConsumer resampling constants were labeled AOSP mainline; verified against android-16.0.0_r1 and updated the source anchor. No Android 18/API 38 material used; Android 17 public AOSP tag unavailable. | 2026-06-16 17 Task9 deep-review AUTO-FIX: 修正 SplineOverScroller 状态边界、FrameTimeline/AppJankStats 说明、输入重采样 5ms latency 边界与 EMA 建议；证据为 AOSP android-16.0.0_r1 OverScroller/InputConsumer/Choreographer 与官方 Perfetto/NDK 文档；回到 Task6 复审。"
review_notes: "2026-06-16 Task6：修正 outline 块格式问题，L1/L2 通过，送回 Task9 处理技术项。"
last_task9_audit: "2026-06-16"
status: "ready-for-review"
pipeline_stage: "task9_pending"
task6_state: "reviewed"
task9_state: "pending"
task2b_state: "fixed"
task2b_result: "fixed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-16"
task6_result: "pass-light-edit"
last_task6_at: 2026-06-16T22:15:00+08:00
last_task2b_verifier_at: "2026-06-16T23:28:12+08:00"
task2b_verifier_notes: "2026-06-16 Task2B Verifier: state reconciliation — task9_state reviewed→pending; Task6 已 pass-light-edit，需 Task9 复审 auto-fixed 内容"
last_task6_review_log: "logs/review/2026-05-24-01-review.md"
task6_review_notes: "2026-05-24 Task6 revisiting review: pass-light-edit。L1/L2 小修 5 处（压低否定-纠正式句式、移除 AIW 编辑注释、把新增 Buffer Stuffing Recovery 段移到参考资料前）。无新增 Task6 回炉；InputConsumer DEBUG tag 已由 Task2B 修复，等待 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-06-16-17-deep-review.md"
last_task9_audit_at: "2026-06-16T10:28:38+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-16-10-audit.md"
last_task9_audit_result: "auto-fixed-p1-version-anchor"
task9_audit_notes: "2026-06-16 Task9 idle audit: auto-fixed unversioned AOSP mainline anchor for InputConsumer constants to android-16.0.0_r1; sent back to Task6."
last_task9_autofix_at: "2026-06-16"
---
-


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
> 扩展内容视素材完整度决定是否展开，无法确认的技术细节保留 `[待验证]`，不要硬写结论。<!-- outline-end -->

在 Android 性能优化的日常工作中，我们习惯用"掉帧"作为衡量流畅性的关键指标。FrameTimeline 标红了就是 jank，没标红就默认流畅。但实际开发中还有一个更隐蔽的问题：FrameTimeline 显示所有帧都在 VSync 预算内完成，没有任何一帧超时，用户却反馈"感觉有点卡"。用户的感觉没有错，我们衡量流畅性的维度少看了一项。传统的 jank 检测关注"这一帧有没有在规定时间内完成"，但用户的视觉系统更在意"相邻两帧之间的画面变化是否均匀"。本节讨论的就是这个被传统工具忽略的维度：**步幅波动（step-size jitter）**。即使不掉帧，帧与帧之间位移量不均匀，也会导致视觉上的不连贯。排查这类问题时，先确认成因，再量化位移采样，之后选择对应的优化方向。## 无掉帧卡顿的本质：帧率稳定 ≠ 步幅均匀

先区分两个概念。**帧率稳定性**衡量的是每帧渲染时间的均匀性。在 120Hz 屏幕上，理想情况是每 8.33ms 产出一帧。如果某帧花了 12ms，那就是掉帧。传统工具（Perfetto FrameTimeline、JankStats）检测的就是这个维度。**步幅均匀性**衡量的是每帧画面位移量的均匀性。一个列表在匀速滚动时，相邻两帧之间应该移动相同的像素数。如果帧 A 移动了 10px、帧 B 移动了 13px、帧 C 移动了 8px，即使三帧都在 VSync 预算内完成，用户也会感觉到"抖动"。用户在连续动画中建立的预期是"画面按稳定速度前进"，刷新间隔只是其中一个条件。当这个运动轨迹出现不规则跳动时，视觉系统会立即感知到不连贯。在高刷新率滑动场景里，没有一个跨设备、跨 workload 通用的阈值可以直接套用。更稳妥的做法是把同一段轨迹里的位移采样拿出来看，确认是否持续出现可见的像素级交替。这就是为什么一台稳定运行 120fps 的设备，列表滑动时仍然可能"感觉不丝滑"。问题不在帧率，而在步幅。### 典型场景

最常见的一类感知流畅性场景出现在手势导航窗口动画里。在多任务界面（Recent Apps）上划回桌面时，窗口缩小的动画前期变化速度过快、后期突然变慢。这里更像是动画插值曲线的加速度分布不合理，导致画面位移量在动画开头和结尾差异太大。另一个典型场景是 RecyclerView 的 fling 滚动。手指快速划过后，列表惯性滚动的前几帧位移量往往波动较大，后几帧又趋于平稳。这种"开头猛后面缓"的非线性减速如果不够平滑，就会产生顿挫感。## 步幅波动的技术成因

上面描述的现象在 Trace 中不会标红，在 FrameTimeline 里也不会有 jank 标记，但它会影响用户体验。App 侧时间量化只是其中一类成因。先把 OverScroller 和 Choreographer 的时间模型讲清，再看怎样把它和显示侧、输入侧的问题分开。### 成因一：OverScroller 的毫秒时间量化

RecyclerView fling 常走 `OverScroller.computeScrollOffset()` 的 `FLING_MODE`。推进位置的是内部 `SplineOverScroller.update()`，它先读取 `AnimationUtils.currentAnimationTimeMillis()`，再按经过的时间推进当前位置。```java
// frameworks/base/core/java/android/widget/OverScroller.java
boolean computeScrollOffset() {...
    case FLING_MODE:
        if (!mScrollerX.mFinished) {
            if (!mScrollerX.update()) {... }
        }...
}

boolean update() {
    final long time = AnimationUtils.currentAnimationTimeMillis();
    final long currentTime = time - mStartTime;...
}
```

`currentAnimationTimeMillis()` 的返回值只有毫秒精度。60Hz 面板一帧 16.67ms，1ms 量化误差还比较隐蔽；120Hz 一帧 8.33ms，同样的 1ms 误差就会把相邻两帧推到 8ms / 9ms 两档。这个结论来自时间量化本身，不依赖经验阈值。| 帧序号 | 理想 VSync 时间 (ns) | 实际 ms 取整 | 帧间时间 | 偏差 |
|--------|---------------------|-------------|---------|------|
| 0 | 0 | 0ms | — | — |
| 1 | 8,333,333 | 8ms | 8ms | -4% |
| 2 | 16,666,666 | 16ms | 8ms | -4% |
| 3 | 24,999,999 | 24ms | 8ms | -4% |
| 4 | 33,333,332 | 33ms | 9ms | +8% |
| 5 | 41,666,665 | 41ms | 8ms | -4% |

`8_333_333 × 4 = 33_333_332`，`floor(33_333_332 / 1_000_000) = 33`，比上一帧多了 9ms。这是因为累积的小数部分在第 4 帧超过了 1ms 阈值。ms 取整之后，时间推进以 8ms 为主、周期性出现 9ms 跳变。高速度 fling 段里，同样的 1ms 跳动会直接反映到位移采样。### 成因二：常规 fling 走样条表，再从 `SPLINE_POSITION` 表和相邻采样点的斜率里插值出 `distanceCoef` 与 `velocityCoef`。```java
// frameworks/base/core/java/android/widget/OverScroller.java
switch (mState) {
    case SPLINE:
        final float t = (float) currentTime / mSplineDuration;
        final int index = (int) (NB_SAMPLES * t);...
        final float d_inf = SPLINE_POSITION[index];
        final float d_sup = SPLINE_POSITION[index + 1];
        velocityCoef = (d_sup - d_inf) / (t_sup - t_inf);
        distanceCoef = d_inf + (t - t_inf) * velocityCoef;
        distance = distanceCoef * mSplineDistance;...
}
```

这段代码决定了常规 fling 的主要轨迹。`BALLISTIC` 和 `CUBIC` 只覆盖越界、回弹和 springback 等状态；常规 fling 不能用二次公式代表整段轨迹。

`SplineOverScroller.update()` 在 `SPLINE` 状态下不会按 `position = start + velocity * time - friction * time^2` 直接算位移。它先把 `currentTime / mSplineDuration` 映射到样条进度 `t`，不能拿来代表整段 fling。会受 8ms / 9ms 交替影响的是样条进度 `t` 的采样点，以及由此得到的 `distanceCoef` / `velocityCoef`。在高速段，样条表相邻采样点之间的位移差更大，所以 1ms 量化更容易变成肉眼可见的步幅抖动。### 成因三：Choreographer 把时间同步到 VSync，但精度仍停在毫秒

OverScroller 并没有完全绕开 `Choreographer`。`Choreographer.doFrame()` 在执行本帧回调前，会把当前线程的动画时钟锁到这一帧的 `frameTimeNanos`，同时记录期望呈现时间。```java
// frameworks/base/core/java/android/view/Choreographer.java
AnimationUtils.lockAnimationClock(
        frameTimeNanos / TimeUtils.NANOS_PER_MS,
        timeline.mExpectedPresentationTimeNanos);
```

```java
// frameworks/base/core/java/android/view/animation/AnimationUtils.java
public static long currentAnimationTimeMillis() {
    AnimationState state = sAnimationState.get();
    if (state.animationClockLocked) {
        return Math.max(state.currentVsyncTimeMillis,
                state.lastReportedTimeMillis);
    }...
}
```

这说明 `AnimationUtils.currentAnimationTimeMillis()` 读到的是跟当前 VSync 同步过的线程本地动画时钟。Choreographer 内部维护的 `mLastFrameTimeNanos` 仍然是纳秒值，但传给 `AnimationUtils.lockAnimationClock()` 时已经执行了 `frameTimeNanos / NANOS_PER_MS` 这一步 long 整数除法。这里的行为是直接向下截断，不是四舍五入：`8_999_999ns / 1_000_000 = 8ms`，`9_000_001ns / 1_000_000 = 9ms`。两次 VSync 只差 2ns，动画时钟却会跨过完整的 1ms 档位。120Hz 面板上一帧只有 8.33ms，这种跳变会把样条进度和位移量一起放大。## 帧率稳定性与步幅均匀性的关系

这两者常常被混淆，但它们是完全独立的维度。我们可以用一个 2x2 表来理解：| | 步幅均匀 | 步幅不均匀 |
|---|---|---|
| **不掉帧** | 运动连续 | 无掉帧卡顿（本章主题） |
| **掉帧** | 有规律的卡顿 | 最差体验 |

"无掉帧卡顿"（no-jank stutter）是最容易被忽略的象限。传统工具报告"0 frames janky"，但用户仍然不满意。**视觉惯性**是理解这个问题的关键概念。人类的视觉系统对匀速运动有很强的预期。当一个物体开始运动后，大脑会"预测"它在下一帧的位置。如果实际位置与预测位置偏差过大（无论是因为帧率不稳定还是步幅不均匀），大脑就会感知到"不连贯"。这也解释了为什么 VSync 调度优化（如 Frame Pacing Library，见 2.17 节）只能解决帧率稳定性问题，不能解决步幅均匀性问题。Frame Pacing 确保"每一帧在正确的时间点呈现"，但不保证"每一帧的位移量正确"。## 在 Perfetto 中量化步幅波动

FrameTimeline 能回答“这一帧何时计划、何时提交、何时呈现”，但它不直接保存 `scrollY`、`translationX` 或动画值。帧时间均匀，只能说明调度节奏稳定，不能直接推出位移也均匀。### 路径一：在应用侧同步采样位移

最直接的办法是在 `FrameCallback`、动画更新回调或自定义 `RecyclerView.OnScrollListener` 中，同帧记录位移与时间。```kotlin
// [示意代码] 在同一条动画轨迹上记录 dt 和 displacement
class StepJitterProbe(
    private val view: View
): Choreographer.FrameCallback {
    private var lastFrameNanos = 0L
    private var lastScrollY = 0

    override fun doFrame(frameTimeNanos: Long) {
        val scrollY = view.scrollY
        if (lastFrameNanos!= 0L) {
            val dtMs = (frameTimeNanos - lastFrameNanos) / 1_000_000.0
            val dy = scrollY - lastScrollY
            record(frameTimeNanos, dtMs, dy)
        }
        lastFrameNanos = frameTimeNanos
        lastScrollY = scrollY
        Choreographer.getInstance().postFrameCallback(this)
    }
}
```

目标对象可以换成 `translationX`、`RecyclerView.computeVerticalScrollOffset()`、自定义动画值或 layer bounds。要算的是同一段轨迹上的 `位移方差`、`速度方差` 和 `时间方差`。其中 `dt variance` 只是辅助指标，不能替代位移采样。做对照实验时，可以保留同一条插值曲线，只把时间源切成 `frameTimeNanos`：`deltaSeconds = (frameTimeNanos - startNanos) / 1_000_000_000.0`，再用浮点时间推进位移。如果 FrameTimeline 形态不变、位移采样明显收敛，根因就更接近毫秒量化。### 路径二：用 FrameTimeline 判断呈现节奏是否是根因

Perfetto 的价值在于分型。Perfetto 文档对 FrameTimeline 的定义很清楚：Android 12(S)+ 才有这组数据；`Expected Timeline` 是调度器分给 App 的渲染窗口，`Actual Timeline` 是 App 实际完成并提交给 SurfaceFlinger 的时间。如果 displacement sample 明显波动，但 `Actual Timeline` 基本贴着 `Expected Timeline`，更像 App 侧的物理模型、插值或时间量化问题。如果位移采样相对平稳，`Actual Timeline` 到 SurfaceFlinger 的实际呈现时间仍有抖动，就要继续看合成、显示模式切换和 present fence。### 路径三：Android 16 的 AppJankStats 与 RelativeFrameTimeHistogram

Android 16 在 `android.app.jank` 包里提供了 `AppJankStats` 和 `RelativeFrameTimeHistogram`，但它们不是“系统自动收集、零代码侵入”的全局 Trace API。`AppJankStats` 用来描述单个 UI widget 在某个状态下的 jank 统计，`RelativeFrameTimeHistogram` 记录这些帧相对 deadline 的分布。把数据交给系统的入口是 `View.reportAppJankStats(AppJankStats)`。这组 API 更适合 library / widget 插桩，例如列表、播放器控件或复杂动画组件把自己的局部抖动统计上报给系统。它能补齐“哪个 widget 在什么状态下更容易抖”的视角，但不能替代 Perfetto 对整个显示栈的被动追踪。**精度限制**：`RelativeFrameTimeHistogram` 使用预定义毫秒桶（bucket），外侧依次为 5ms、10ms、50ms、100ms 等更粗粒度。输入 `addRelativeFrameTimeMillis(int)` 接受整数毫秒，记录结果落入预定义桶，并不是 1ms 精度的连续采样。-20ms 到 20ms 区间内为 2ms 桶，但输出统计落到对应桶内。同时，该 histogram 记录的是帧时间相对 deadline 的偏差，不包含位移、`scrollY` 或动画值信息，因此不能直接判断步幅波动的大小。对于步幅敏感场景（如列表 fling 滚动、跟手动画），官方统计 API 适合粗粒度的 widget 级帧时间分布画像，不能替代应用侧纳秒级时间 + 位移采样。如果需要检测细粒度步幅波动，仍应回到路径一的应用侧采样方案。### 根因分型：不要把所有“无掉帧卡顿”都归到 OverScroller

| 现象 | 重点看哪里 | 更像哪类问题 |
|---|---|---|
| `scrollY` / `translationX` 采样在同一段轨迹上交替跳动，FrameTimeline 仍大体贴线 | App 主线程、动画值采样、`OverScroller` / 自定义动画时间源 | App 侧毫秒量化或插值问题 |
| App 侧位移采样平稳，但 SurfaceFlinger 的 actual / present 时间不稳 | FrameTimeline、SurfaceFlinger tracks、display mode 切换、present fence | ARR 模式切换、buffer stuffing、present-time jitter |
| 主要出现在触摸跟手阶段，抬手后的 fling 反而正常 | InputDispatcher / InputReader、MotionEvent resampling、velocity estimate | 输入重采样或预测偏差 |

## 优化策略

### ARR 动态刷新率对步幅波动的可能影响

Android 15+ 的 Adaptive Refresh Rate（ARR，见 §2.18）会根据内容动态切换刷新率（如 60→90→120Hz）。切换瞬间 VSync 周期变化，动画时间模型和样条进度同步换档。由于 `Choreographer` 每帧基于当前 `frameTimeNanos / NANOS_PER_MS` 重新计算动画时钟（见成因三），毫秒截断误差本身不会“继承旧周期”累加。但在 ARR 切换边界上有两类潜在扰动值得观察：1. **VSync 周期跳变点**：从 60Hz（16.67ms）切到 120Hz（8.33ms）时，每帧的毫秒截断模式从 16/17 交替变为 8/9 交替，如果动画曲线正在高速段，样条进度的步长会发生一次突变
2. **非整数周期**：90Hz（11.11ms）等周期下，毫秒截断落在 11/12 交替，与 60Hz 的 16/17 或 120Hz 的 8/9 有不同的误差分布模式

这些扰动是否构成肉眼可见的阶跃感，目前缺少 AOSP 机制或 Perfetto + 位移采样证据。[待验证：需要一组 trace，把 Display mode track / vsyncId / App 侧 displacement sample 放到同一时间轴，确认步幅波动是否集中在 ARR 切换窗口。]

### 策略一：App 侧动画使用同一套 VSync 时间基准

当根因落在 `OverScroller` 或自定义动画时，首要目标是让位移计算和显示调度使用同一套时间基准。对可改造的动画逻辑，优先使用 `frameTimeNanos` 或 `VsyncCallback` 提供的 `FrameData`，不要在帧回调里额外采一次毫秒时钟。只有当位移采样已经证明“FrameTimeline 绿色，但 displacement variance 高”时，这类改造才值得做。### 策略二：显示节奏不稳时，先修 SurfaceFlinger 和刷新率切换

如果 Trace 显示 `Actual Timeline`、display mode 或 present fence 在抖，继续打磨 `OverScroller` 没什么用。这里更有效的是固定刷新率范围、减少 ARR 来回切换、检查 buffer stuffing 恢复，以及确认 SurfaceFlinger 合成负载是否在波动。判断依据是，App 侧位移采样相对平稳，但最终呈现时间不稳。### 策略三：插值器斜率与步幅均匀性

步幅敏感场景（如 fling 减速段、回弹动画）中，插值器的控制点斜率会影响位移对时间误差的敏感度。`AccelerateDecelerateInterpolator` 在加速/减速段斜率变化剧烈，`1ms` 的时间误差在高速段会被斜率放大成更大的位移跳动。`PathInterpolator` 允许通过贝塞尔控制点定义更平滑的切线斜率，配合 `Choreographer.FrameData`（API 33+）拿到纳秒级时间戳做时间同步，可以减少插值器本身对时间量化的放大效应。### 策略四：跟手动画要同时看输入采样和位移采样

触摸跟手场景里，平滑 `dt` 只是兜底手段。更常见的做法是先对比输入事件时间戳、resampling 后的位置和屏幕上的实际位移。如果问题集中在手指刚按下、即将抬起或快速变向，优先检查 velocity estimate 与 prediction，而不是直接给动画再包一层 EMA。EMA 会减小抖动，但也会带来额外跟手延迟。## 与其他章节的关联

步幅波动和以下章节的内容直接相关：- **7.1 卡顿的定义与分类**：传统卡顿定义关注帧率，本章扩展了卡顿的定义维度
- **7.8 RecyclerView 列表滑动性能深度优化**：RecyclerView 的 fling 行为直接受步幅波动影响
- **2.4 Choreographer 与渲染流水线**：Choreographer 提供纳秒时间，但动画框架没有完全利用
- **2.17 Frame Pacing Library**：Frame Pacing 解决帧率稳定性，但不解决步幅均匀性
- **3.2 触摸响应的性能分析**：触摸事件的时间精度（MotionEvent.getEventTime() 也是毫秒级）有类似的问题

## 版本演进

| Android 版本 | 变化 | 对本节分析的意义 |
|-------------|------|------------------|
| Android 12 (API 31) | Perfetto FrameTimeline / SurfaceFlinger FrameTimeline data source | 第一次能把 `Expected Timeline` 与 `Actual Timeline` 放到同一套 trace 里看 |
| Android 13 (API 33) | `Choreographer.postVsyncCallback(VsyncCallback)` 与 `FrameData` 成为公开 API | App 侧可以拿到多条 frame timeline、deadline 和 expected presentation time |
| Android 16 (API 36) | `View.reportAppJankStats(AppJankStats)`、`AppJankStats`、`RelativeFrameTimeHistogram` | 这是主动上报接口和数据容器，适合 library / widget 汇总局部 jank 统计，不等于被动 trace |

## 常见问题与误区

**误区一："FrameTimeline 没有标红，就说明流畅"**

FrameTimeline 只检测帧是否在 VSync 预算内完成。步幅波动不会导致帧超时，因此 FrameTimeline 完全是绿色的。流畅性 = 帧率稳定 + 步幅均匀，两者缺一不可。**误区二："120Hz 屏幕不会卡顿"**

120Hz 减轻了帧率不稳定带来的卡顿感（因为每帧时间更短，偶尔掉一帧影响更小），但反而可能**加重**步幅波动的感知。因为 VSync 周期更短（8.33ms），ms 取整误差的相对占比更大（12% vs 60Hz 下的 6%）。再加上 120Hz 下每帧位移更小，视觉系统对位移变化更敏感。**误区三："把动画时间调短就能解决卡顿"**

缩短动画时间只改变了动画的总时长，不改变步幅的均匀性。一个 200ms 的动画和一个 300ms 的动画，如果每帧的位移分布都不均匀，用户感知到的不流畅程度是相似的。问题不在动画跑多快，而在相邻两帧的位移差了多少。## 输入重采样（Motion Resampling）对跟手滑动的影响

**关联章节**：§7.9 感知流畅性 / §3.2 触摸响应的性能分析。这里补充输入重采样（Motion Resampling）对跟手滑动的影响机制。**机制位置**：Android Input 系统的触摸重采样位于 InputConsumer 层，在事件到达 App 之前对触摸坐标进行处理。核心流程在 `frameworks/native/libs/input/InputConsumer.cpp` 中：`consume()` → `consumeBatch()` 计算采样时间点 → `updateTouchState()` 更新历史样本 → `resampleTouchState()` 执行插值/外推。声明位于 `frameworks/native/include/input/InputConsumer.h`。**关键常量**（AOSP android-16.0.0_r1）：- `RESAMPLE_LATENCY = 5 * NANOS_PER_MS`（5ms 预期延迟，用于减少误预测影响）
- `RESAMPLE_MIN_DELTA = 2 * NANOS_PER_MS`（最小采样间隔，2ms）
- `RESAMPLE_MAX_PREDICTION = 8 * NANOS_PER_MS`（最大预测窗口，8ms）

**算法原理**：1. `consumeBatch()` 计算采样时间点：`sampleTime = frameTime - RESAMPLE_LATENCY`，其中 `frameTime` 是目标 VSync 时间，`RESAMPLE_LATENCY = 5ms` 是重采样延迟补偿。2. `updateTouchState()` 将原始触摸事件记录为历史样本（next/history 两个样本窗口，保存 timestamp、x、y）。3. 当历史样本间的时间差 `>= RESAMPLE_MIN_DELTA`（2ms）时，`resampleTouchState()` 进入重采样逻辑：若 `sampleTime` 在两个历史样本之间，执行线性插值（Interpolation）；若 `sampleTime` 超出最新样本，执行外推（Extrapolation），外推量不超过 `RESAMPLE_MAX_PREDICTION`（8ms）。4. 重采样后的坐标同步到 VSync 时间点，确保渲染新帧时使用的是同步后的坐标。**设计意图**：解决触摸采样率（通常 100-240Hz）与显示刷新率（60/90/120Hz）不同步导致的坐标跳跃。`RESAMPLE_LATENCY` 的 5ms 是重采样算法的延迟补偿参数，不代表固定最坏响应增量；它控制的是采样时间点相对于目标 VSync 的回退量，使得插值/外推有足够的历史数据支撑，降低误预测概率。**性能影响**：`RESAMPLE_LATENCY = 5ms` 表示重采样点相对目标 VSync 回退 5ms，可能增加跟手延迟感，但不能等同为端到端触摸响应固定或最坏增加 5ms；它的收益是降低采样率与刷新率不同步造成的帧内坐标抖动。关闭场景（延迟敏感游戏）可通过 `ro.input.resampling=0` 系统属性禁用重采样。**配置接口**：`ro.input.resampling` 系统属性（`1` 启用 / `0` 禁用，定义于 `InputConsumer.cpp` 中的 `PROPERTY_RESAMPLING_ENABLED`）；DEBUG 开关 `log.tag.InputTransportResampling=DEBUG`（user build 需重启生效，userdebug/debuggable build 可即时生效）

**关键源码文件**：- `frameworks/native/include/input/InputConsumer.h` — InputConsumer 类声明
- `frameworks/native/libs/input/InputConsumer.cpp` — `consume()` / `consumeBatch()` 事件消费、`resampleTouchState()` 重采样算法、`updateTouchState()` 历史样本更新
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — 事件分发与 stale event 判定

**与感知流畅性的关联**：输入重采样直接影响跟手滑动场景下的触摸坐标质量。当重采样算法误判速度方向或量级时，误预测的坐标会导致 RenderThread 在处理触摸触发的 UI 更新时产生视觉滞后感，与本节讨论的步幅波动问题形成跨输入-渲染的完整关联。## Choreographer Buffer Stuffing Recovery（Android 16 新增）

> 来源：源码调研 2026-05-20 | 一手源码：frameworks/base/core/java/android/view/Choreographer.java（android-16.0.0_r1）

Android 16 引入 **Buffer Stuffing Recovery** 机制，解决应用端 Buffer Dequeue 阻塞导致的帧节拍错位问题。这是 Android 16 针对帧节拍稳定性的新保障手段。### 核心组件：BufferStuffingState

Choreographer.java 中新增内部类 `BufferStuffingState`：```java
private static class BufferStuffingState {
    enum RecoveryAction {
        NONE,       // 无恢复
        OFFSET,     // 添加负偏移，提前下一帧
        DELAY_FRAME // 延迟一帧等待 Buffer 恢复
    }
    public AtomicBoolean isStuffed = new AtomicBoolean(false);
    public boolean isRecovering = false;
    public int numberWaitsForNextVsync = 0;
}
```

### onWaitForBufferRelease() API

新增 `@hide` API，供图形客户端通知 Choreographer 其正在等待 Buffer：```java
public void onWaitForBufferRelease(long durationNanos) {
    if (durationNanos > mLastFrameIntervalNanos / 2) {
        mBufferStuffingState.isStuffed.set(true);
    }
}
```

触发条件：客户端阻塞超过半帧周期时设 `isStuffed = true`。### 恢复机制

当 `isStuffed` 为 true 时，Recovery 进入以下两种模式之一：- **OFFSET**：添加负偏移，让下一帧提前，补偿 stuff 导致的延迟累积
- **DELAY_FRAME**：延迟一帧，等待 Buffer 计数恢复，防止帧时间倒退

`numberWaitsForNextVsync` 统计在 Recovery 期间额外等待的 VSync 次数，防止跳帧扩散。### mLastNoOffsetFrameTimeNanos

```java
private long mLastNoOffsetFrameTimeNanos;
```

保留不含 Buffer Stuffing 偏移的帧时间，用于判断系统是否处于空闲状态。### 与步幅波动的关系

Buffer Stuffing Recovery 解决的是**供给侧阻塞**导致的帧节拍错位，与本节讨论的需求侧（OverScroller 时间精度）形成互补。两类问题都会导致"不掉帧但感觉卡"的现象，需要分别从 Buffer 队列状态和动画时间源两个方向排查。## 参考资料

- AOSP 源码路径：- `frameworks/base/core/java/android/widget/OverScroller.java`（`computeScrollOffset()`、`SplineOverScroller.update()`）
  - `frameworks/base/core/java/android/view/Choreographer.java`（`doFrame()`、`postVsyncCallback()`）
  - `frameworks/base/core/java/android/view/animation/AnimationUtils.java`（`lockAnimationClock()`、`currentAnimationTimeMillis()`）
- 官方文档：- Choreographer VsyncCallback: https://developer.android.com/reference/android/view/Choreographer#postVsyncCallback(android.view.Choreographer.VsyncCallback)
  - View.reportAppJankStats: https://developer.android.com/reference/android/view/View#reportAppJankStats(android.app.jank.AppJankStats)
  - AppJankStats: https://developer.android.com/reference/android/app/jank/AppJankStats
  - RelativeFrameTimeHistogram: https://developer.android.com/reference/android/app/jank/RelativeFrameTimeHistogram
  - Perfetto FrameTimeline: https://perfetto.dev/docs/data-sources/frametimeline
- 研究素材：- `intake/research-feeds/2026-04-07-16-perfetto-frame-timeline-perceived-smoothness-analysis.md`
  - `intake/research-feeds/2026-04-07-16-android16-appjankstats-relative-frame-time-histogram.md`
