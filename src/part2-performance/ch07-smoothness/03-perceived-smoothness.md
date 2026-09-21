---
title: 感知流畅性：步幅波动与无掉帧卡顿
chapter: '7.3'
section: '7.3'
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-03'
last_verified_against: AOSP android-17.0.0_r1 OverScroller / Choreographer / AnimationUtils / InputConsumer / AppJankStats / RelativeFrameTimeHistogram; Android Choreographer/View API docs; Perfetto FrameTimeline docs
confidence: medium-high
sources:
- type: aosp-source
  version: android-17.0.0_r1
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/OverScroller.java
- type: aosp-source
  version: android-17.0.0_r1
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java
- type: aosp-source
  version: android-17.0.0_r1
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/animation/AnimationUtils.java
- type: aosp-source
  version: android-17.0.0_r1
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputConsumer.cpp
- type: official-api
  path: https://developer.android.com/reference/android/app/jank/AppJankStats
- type: official-api
  path: https://developer.android.com/reference/android/app/jank/RelativeFrameTimeHistogram
- type: official-api
  path: https://developer.android.com/reference/android/view/Choreographer
- type: official-api
  path: https://developer.android.com/reference/android/view/View#reportAppJankStats%28android.app.jank.AppJankStats%29
- type: official-doc
  path: https://perfetto.dev/docs/data-sources/frametimeline
tags:
- perceived-smoothness
- step-jitter
- frametimeline
- overscroller
- android-performance
status: finalized
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: '2026-08-01T22:35:12+08:00'
last_idle_audit_run_id: 20260801-223512-idle-audit-66741ef6
last_rework_at: '2026-08-03T09:42:34+08:00'
last_rework_run_id: 20260803-094234-rework-66741ef6
last_review_finalize_at: '2026-08-03T10:05:40+08:00'
last_review_finalize_run_id: 20260803-100522-554de959
---

# 感知流畅性：步幅波动与无掉帧卡顿

帧在 deadline（截止时间）前完成，只能证明调度与渲染没有触发对应的 jank（卡顿帧）判定。画面中的对象是否沿预期轨迹移动，还取决于输入采样、运动模型、数值精度、像素取整、buffer（图形缓冲区）提交、刷新率选择和 present（呈现）节拍。

平台版本以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核版本以 `android17-6.18-2026-06_r6` 为准。平台源码用于核对 `OverScroller`、`Choreographer`、`AnimationUtils`、InputConsumer（输入事件消费组件）与 FrameTimeline（逐帧时间线）；内核只解释调度和 fence（同步栅栏）等现象，不定义动画轨迹。

## “帧准时”与“运动均匀”是两组数据

流畅性分析至少包含三条时间线：

| 时间线 | 观察对象 | 常用证据 |
|---|---|---|
| 帧生产与呈现 | App 是否按期交帧、SurfaceFlinger（系统合成服务）是否按期合成与 present | Expected/Actual FrameTimeline（预期/实际帧时间线）、RenderThread（渲染线程）、GPU、present fence（显示完成栅栏） |
| 运动轨迹 | 每个呈现机会对应的坐标、速度、加速度是否符合设计曲线 | App 自定义 counter（计数轨道）、动画值、列表累计位移、高速相机 |
| 输入到画面 | 输入样本、重采样坐标、App 消费、画面更新之间是否稳定 | InputReader/InputDispatcher/InputConsumer（输入读取/分发/消费组件）、MotionEvent（触摸事件）、自定义状态、present |

FrameTimeline 中的绿色帧表示该帧没有被判为 jank。它不保存 `scrollY`、`translationX`、相机视角或动画进度。连续出现绿色帧，无法单独证明运动轨迹均匀。

减速 fling（惯性滑动）的每帧位移本来就应逐渐缩小。直接计算 `Δx`（相邻帧位移）的方差，会把设计曲线中的减速也算作抖动。测量时应比较观测轨迹与目标轨迹，或在期望速度近似恒定的短时间窗口内比较步幅。

### 先按现象分类

| 现象 | 更可能的方向 | 仍需排除 |
|---|---|---|
| FrameTimeline 按期，模型坐标相对目标曲线有周期残差（观测位置与目标位置之差） | 时间量化、积分方式、插值、整数像素取整 | 采样点是否对应同一帧 |
| 模型坐标平稳，Actual/Present 间隔波动 | buffer、SurfaceFlinger、刷新率切换、显示侧 | App counter 记录时刻与显示时刻的差异 |
| 跟手阶段异常，抬手后的 fling 正常 | 输入采样、重采样、velocity estimate（速度估算）、预测 | 业务手势处理和主线程调度 |
| fling 异常，手指跟随阶段正常 | `OverScroller`、自定义物理模型、SnapHelper、item 尺寸 | create/bind/layout 和图片回调 |
| App 与显示节奏都平稳，高速相机仍看到不连续 | 面板扫描、像素响应、内容对比度或设备显示处理 | 相机曝光、快门和同步误差 |

“无掉帧卡顿”适合作为用户现象描述，不能直接作为根因结论。

## Android 17 的 OverScroller 时间模型

### 整数毫秒来自哪里

Android 17 的 `SplineOverScroller.update()` 通过 `AnimationUtils.currentAnimationTimeMillis()` 取得当前时间，再计算 `currentTime = time - mStartTime`。常规 fling 的 `SPLINE`（样条减速曲线）分支把 elapsed time（已经过的时间）除以 `mSplineDuration`，在 101 个 `SPLINE_POSITION` 采样点之间做线性插值，再把结果乘以 `mSplineDistance`。位置写入 `mCurrentPosition` 前，还会通过 `Math.round(distance)` 取整到像素。

这条路径包含三种离散化：

1. VSync（垂直同步）纳秒时间进入 legacy animation clock（旧动画时钟）时变成整数毫秒；
2. spline（样条曲线）使用固定采样表并在相邻点之间插值；
3. `mCurrentPosition` 是整数像素。

第二项是分段线性近似，不一定产生可见问题。第三项在低速末段很常见，一个像素的停留与跳变可能来自整数位置。三者是否会被用户看到，需要结合速度、屏幕密度、内容边缘和 present 节拍测量。

Android 17 的源码入口是 [`OverScroller.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/OverScroller.java)。

### 8/9 ms 交替是量化结果，不是随机 ±1 ms

`Choreographer.doFrame()` 保留纳秒级 `frameTimeNanos`，但调用 legacy animation clock 时会执行 `frameTimeNanos / NANOS_PER_MS`。整数除法会向下截断。理想的 120 Hz 周期约为 8.333 ms，映射到整数毫秒后，相邻 animation time（动画时间）的差值会分布在 8 ms 与 9 ms；60 Hz 常见 16/17 ms，90 Hz 常见 11/12 ms。

具体序列受起始相位、显示模式、VSync 预测和是否跳帧影响。它是由整数换算规则决定的时间量化，并非每帧随机增加或减少 1 ms。把 1 ms 除以 8.33 ms 得到约 12%，只能描述两个时间数值的比例，不能直接写成位移误差或用户感知概率。

若 `OverScroller` 正处于高速、曲线斜率较大的区间，相邻整数毫秒采样可能形成不同的整数像素步幅。内容速度较低、屏幕密度较高，或显示侧节拍同时发生变化时，结果也会不同。只有轨迹采样能说明当前设备是否受到影响。

## Choreographer 保留了哪些精度

Android 17 的 `Choreographer` 在 `doFrame()` 内维护纳秒级 frame time（帧时间）、frame interval（帧间隔）、deadline 和可能存在的 frame timelines。公开的 `FrameCallback.doFrame(frameTimeNanos)` 也接收纳秒值。API 33 起，`postVsyncCallback()` 还能提供 `FrameData` 和候选 presentation timeline（呈现时间线）。

精度从纳秒变为毫秒，发生在 legacy View animation clock 的转换位置：`AnimationUtils.lockAnimationClock(frameTimeNanos / NANOS_PER_MS)`。同一主线程帧内调用 `currentAnimationTimeMillis()` 的旧动画与滚动代码会读到锁定的整数毫秒值，并通过 `max(currentVsyncTimeMillis, lastReportedTimeMillis)` 防止时间倒退。

因此，下面三句话应分开：

- Choreographer 的帧时间是纳秒级；
- legacy `AnimationUtils` 消费者使用整数毫秒；
- Compose frame clock（帧时钟）、自定义 `FrameCallback` 或其他引擎是否保留纳秒精度，要按各自实现核对。

平台源码可在 [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)和 [`AnimationUtils.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/animation/AnimationUtils.java)复核。

## 怎样量化步幅波动

### 采集四组数据

一次可复现测试至少记录：

- `frameTimeNanos` 或选定 frame timeline 的 expected presentation time（预期呈现时间）；
- 运动模型输出，例如 scroller（滚动模型）位置、动画 progress（进度）、目标 transform（变换）；
- View 层消费后的结果，例如 RecyclerView 本帧累计 `dx/dy` 或稳定 item anchor（条目参照点）的 decorated position（含装饰偏移的位置）；
- FrameTimeline 中的 App SurfaceFrame（应用 Surface 帧记录）与 SurfaceFlinger DisplayFrame（整屏显示帧记录）。

UI 线程 counter 记录的是应用在该时刻准备的状态，不表示像素已经显示在屏幕上。要证明“用户看到的步幅”，应通过 surface/display token（Surface/显示帧标识）和时间，把 counter 与对应显示帧关联起来；精度要求更高时，可以使用与 VSync 同步的高速相机或光学传感器。

RecyclerView 的 `computeVerticalScrollOffset()` 可能受 LayoutManager 的 scrollbar（滚动条）估算策略影响。更稳妥的做法是记录同一个稳定 item 的 adapter ID、decorated top（包含装饰偏移的顶部位置）和列表累计消费位移，并合并同一 VSync 周期内的多次 `onScrolled()`。

### 用目标曲线计算残差

设采样为 `(t_i, x_i)`，基础量包括：

- 时间步长 `Δt_i = t_i - t_(i-1)`；
- 位移步长 `Δx_i = x_i - x_(i-1)`；
- 观测速度 `v_i = Δx_i / Δt_i`；
- 目标位置 `x_expected(t_i)`；
- 轨迹残差 `e_i = x_i - x_expected(t_i)`。

在匀速时间窗口中，可以比较 `Δx` 或 `v` 的标准差与极差（最大值减最小值）。减速、回弹和贝塞尔动画应优先比较 `e_i`，并观察残差是否按 8/9 ms、11/12 ms 或刷新率切换呈现周期。只有少数离群点（明显偏离其他样本的点）时，还要检查跳帧、GC（垃圾回收）、调度和 item 布局。

避免只报告平均值。报告应包含设备、刷新模式、Android build（系统构建版本）、初速度、内容、采样长度、中位数、P95/P99（第 95/99 百分位）、残差分布和重复次数。

### Perfetto 的作用边界

Perfetto 负责回答以下问题：

1. Expected Timeline 给了 App 多长的工作时间；
2. Actual Timeline 中的 App work（应用工作）、GPU completion（GPU 完成）与 buffer post（缓冲区提交）是否按期；
3. SurfaceFlinger DisplayFrame 与 present 是否稳定；
4. 刷新率、线程调度、buffer stuffing（缓冲区积压）或合成是否在同一时间窗口发生变化；
5. App 自定义 counter 对应哪一帧。

FrameTimeline 从 Android 12 / API 31 起可用。App Actual slice 的结束时间取 App buffer post 与 GPU completion 中较晚的一项；SurfaceFlinger timeline 继续覆盖合成与显示阶段。具体字段以 [Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)为准。

## 一套对照实验

### 实验 A：时间量化

保留同一条运动曲线、初始位置和初速度，比较两种自有动画实现：

- 方案 A 使用每帧的 `frameTimeNanos`，计算从统一起点开始的绝对 elapsed time；
- 方案 B 先把同一个 `frameTimeNanos` 截断成整数毫秒，再计算 elapsed time。

两组都使用相同的布局与绘制。若 B 的轨迹残差出现与整数毫秒取值相关的周期，而 A 的残差明显减小，实验就支持时间量化假设。这个实验可以验证自有模型，不能证明 RecyclerView 的所有感知问题都由 `OverScroller` 造成。

### 实验 B：模型与呈现分离

在 App 中同时记录模型位置与 View 消费位置，并采集 FrameTimeline：

- 模型与 View 都波动，present 稳定：检查运动模型、像素取整和布局；
- 模型稳定，View 波动：检查 LayoutManager、item 尺寸、Snap（吸附）或更新回调；
- 两者稳定，present 波动：查 RenderThread、buffer、SurfaceFlinger、ARR 和显示；
- 三者都波动：从最早出现偏差的层开始。

### 实验 C：刷新率与起始相位

在设备支持的固定 60/90/120 Hz 刷新率下重复同一脚本，再测试 ARR（Adaptive Refresh Rate，自适应刷新率）。每种刷新率都要进行多次冷机和热机运行，也就是分别在设备温度较低和升温后的状态下测试，并固定初速度和数据。若残差周期随刷新率对应的毫秒量化序列变化，可以继续验证 time source（时间来源）；若残差只在 mode switch（显示模式切换）期间出现，则应检查刷新率选择与 present。

应用不能假设所有设备都允许固定模式，也不能把开发者选项强制刷新率当成产品修复。

## 优化策略及边界

### 自有动画使用统一的纳秒时间基准

可以控制的动画或物理模型，应根据同一个 VSync 时间基准计算绝对 elapsed time。不要在帧回调中额外读取 `uptimeMillis()`，也不要把每帧截断后的 `dt`（时间增量）累加成总时间。

发生一次帧延迟后，根据绝对时间重新求值，通常能让轨迹继续对应正确时间。物理模拟若需要固定步长，应使用 accumulator（累加器）执行次数受限的 simulation step（模拟步进），再为显示结果插值；同时要限制补算量，避免在一帧内集中执行过多工作。

### 不要用平滑器掩盖时间错误

对 `dt` 或坐标应用 EMA（指数移动平均）可以减少高频变化，但也会增加相位延迟，使输出变化晚于输入，并改变速度和手感。它适合处理经过测量确认的传感噪声，不适合作为时间量化、掉帧或输入预测错误的通用修复。

插值器也没有固定的性能排名。任何曲线在斜率较大处都会把时间误差转换为更大的位移误差。选择 `PathInterpolator`、spring（弹簧模型）或 spline 时，应以交互设计要求的速度/加速度连续性和轨迹残差为准。

### RecyclerView 的改造边界

RecyclerView 1.4.0 的 `ViewFlinger` 使用 `OverScroller`。应用没有公开 API 可以替换其内部 time source。发现与毫秒量化相关的问题后，应先确认它是否达到用户可感知的程度，再评估以下选择：

- 调整 fling 初速度、摩擦或 snap 行为，并做跨刷新率测量；
- 对特定控件实现受控的自定义滚动/动画；
- 向 AndroidX 或平台提交最小复现与轨迹证据。

重写 LayoutManager 或 fling 会影响 nested scrolling（嵌套滚动）、边界回弹、无障碍、焦点和手势行为约定，维护成本很高。

### 呈现节奏异常时修显示链

App 模型平稳而 present 不稳时，继续调整插值器没有帮助。应检查 expected/actual FrameTimeline、buffer backpressure（缓冲区反压，即生产速度超过消费速度）、RenderThread/GPU、SurfaceFlinger、刷新率选择和 present fence。完整过程参见[可变刷新率与帧率选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md)与[标准 View/HWUI 渲染管线](../ch13-rendering-pipelines/01-android-view-pipeline-analysis.md)。

## 输入重采样的边界

Android 17 的触摸重采样位于 `frameworks/native/libs/input/InputConsumer.cpp`。批量消费事件时，sample time（目标采样时刻）会从目标 frame time 回退 `RESAMPLE_LATENCY = 5 ms`。存在 future sample（目标时刻之后的样本）时，算法在前后样本之间插值；只有历史样本时则会外推，也就是根据已有趋势预测后续位置。外推上限同时受最近样本间隔的一半和 `RESAMPLE_MAX_PREDICTION = 8 ms` 限制。样本间隔小于 2 ms 或超出允许范围时，不会照常外推。

5 ms 是算法选择重采样时刻时使用的偏移，不表示端到端响应固定增加 5 ms。效果取决于触控采样率、VSync 时序、历史样本、触控工具类型（手指或触控笔等）和预测方向。

`ro.input.resampling` 是系统只读产品属性，不是第三方 App 的运行时优化开关。OEM（设备厂商）、系统镜像或 userdebug（可调试系统构建）实验可以进行 A/B（对照实验）；普通应用应采集原始 MotionEvent、消费时刻、模型坐标和 present 证据。

Android 17 源码可查 [`InputConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputConsumer.cpp)。

## Buffer Stuffing Recovery 放在哪一层

Buffer stuffing 指生产者提交过快或消费者处理较慢，导致可用 buffer 不足、队列积压。Android 17 的 `Choreographer` 包含内部 `BufferStuffingState` 和 `onWaitForBufferRelease()`。客户端等待 buffer release（缓冲区释放）的时间超过上一帧周期的一半时，系统可以标记 stuffed（已积压）。恢复状态机会主动等待一个 VSync，以减少排队的 buffer 数量；随后给动画 timeline 添加负一个 frame interval（帧间隔）的 offset（时间偏移），直到检测到 idle（空闲）或满足其他恢复条件。

这套 API 带有 `@hide`，仅供平台内部使用，并受内部 flag（开关）与实现约束。它会改变调度和动画时间线；Perfetto 中还可能出现 `Buffer stuffing recovery` 轨道，或 FrameTimeline 的 `Buffer Stuffing` jank type（卡顿类型）。它与“所有帧绿色但位移抖动”属于不同问题。

排查时分开读：

- `OverScroller` 毫秒量化：App 运动模型输入时间的离散化；
- Buffer stuffing：窗口 Producer（生产者）因 buffer 不可用而受到 backpressure；
- Recovery：Choreographer 为减少排队 buffer，主动延后一帧并调整动画时间。

应用侧应处理 buffer 生产过快、GPU/Consumer（消费者）变慢或帧节奏错误等原因，不能调用内部 recovery API。

## AppJankStats 与 RelativeFrameTimeHistogram

Android 16 / API 36 加入 `AppJankStats`、`RelativeFrameTimeHistogram` 和 `View.reportAppJankStats()`。它们用于上报某个 widget（界面组件）、navigation component（导航组件）及其状态下的总帧数、jank 帧数与相对 deadline 的帧时间分布。

`RelativeFrameTimeHistogram.addRelativeFrameTimeMillis(int)` 接收整数毫秒，并按预定义区间累计。-20 ms 到 20 ms 的中间区域使用宽度为 2 ms 的桶（统计区间），外侧区间逐步变宽。它记录 render（渲染）完成时间相对 deadline 的差值，不包含坐标、速度或 present 后的像素变化。

这组 API 适合 widget 级聚合，不能替代轨迹采样，也不能替代 Perfetto 对 App、SurfaceFlinger 和显示栈的分析。公开契约参见 [AppJankStats](https://developer.android.com/reference/android/app/jank/AppJankStats)、[RelativeFrameTimeHistogram](https://developer.android.com/reference/android/app/jank/RelativeFrameTimeHistogram)和 [`View.reportAppJankStats()`](https://developer.android.com/reference/android/view/View#reportAppJankStats%28android.app.jank.AppJankStats%29)。

## ARR 与可变刷新率

刷新率切换会改变 frame interval，也会改变整数毫秒 animation time 的差值序列。60 Hz 的 16/17 ms、90 Hz 的 11/12 ms、120 Hz 的 8/9 ms 只是理想周期的映射示例；设备的 VSync 预测、切换相位和应用帧率请求还会影响观测结果。

不能仅根据机制推导“ARR 切换一定可见”。验证时，应在同一时间范围内核对 active mode（当前显示模式）、render rate（渲染帧率）、Expected/Actual FrameTimeline、App 位移 counter 与 present。只有残差集中在 mode switch 前后，才值得继续检查切换策略。

RecyclerView 1.4.0 会在 `OverScroller` 滚动时调用 API 35 的 `View.setFrameContentVelocity()`，向平台报告内容速度。它提供速度信号，不指定刷新率。相关机制见[RecyclerView 列表滑动性能](../../part5-app/ch22-rendering-practice/02-recyclerview-compose-lazylist.md)。

## 版本边界

| 版本 | 能力或行为 | 用途 |
|---|---|---|
| Android 12 / API 31 | FrameTimeline | 按时间关联 App SurfaceFrame、SurfaceFlinger DisplayFrame 与 present |
| Android 13 / API 33 | 公开 `Choreographer.VsyncCallback` 与 `FrameData` | 自有渲染可读取候选 frame timeline |
| Android 15 / API 35 | `View.setFrameContentVelocity()` | 滚动组件向平台提供内容速度 |
| Android 16 / API 36 | AppJankStats 与 RelativeFrameTimeHistogram | widget 级 jank 汇总，不含位移 |
| Android 17 / API 37 | 用于核对的平台源码版本 | 复核 OverScroller、Choreographer、InputConsumer、buffer recovery 与显示策略 |

平台和 OEM 可能修改 `OverScroller`、刷新率策略或输入参数。没有对应 build 源码时，应以设备 trace、轨迹 counter 和光学结果为准。Chrome 或 OEM 私有实现不能作为 AOSP（Android 开源项目）的通用结论。

## 常见误判

- **“FrameTimeline 全绿，用户反馈就没有依据。”** FrameTimeline 不记录内容坐标，运动轨迹仍需单独采样。
- **“120 Hz 下整数毫秒必然造成 12% 位移抖动。”** 12% 是 1 ms 与 8.33 ms 的数值比例，位移结果还受曲线、速度、像素取整和呈现节拍影响。
- **“Spline 查表就是抖动来源。”** 查表后还有线性插值；要比较目标曲线与输出残差。
- **“换成 PathInterpolator 就会平滑。”** 控制点决定曲线，API 名称不能保证斜率连续或低残差。
- **“给 dt 做 EMA 就能修复。”** 平滑会引入延迟并改变运动模型。
- **“5 ms 重采样等于触摸固定慢 5 ms。”** 它是目标采样时刻的回退量，端到端延迟需要测量从输入到显示的完整过程。
- **“Buffer Stuffing Recovery 是应用可调用的优化。”** 它是平台内部机制，应用应处理 Producer/Consumer 失衡。
- **“AppJankStats 可以测步幅。”** 它统计帧数和相对 deadline 的时间桶，不含位置。

## 复核清单

- 是否同时记录 Android build、设备、刷新模式、动画/列表实现和初始条件；
- 是否把 FrameTimeline、模型坐标、View 消费坐标与 present 分开；
- 是否按目标曲线计算残差，而非对减速轨迹直接算步幅方差；
- 是否说明 UI thread counter 不等于屏幕像素已经出现；
- 是否对固定刷新率和 ARR 分组；
- 是否排除 create/bind/layout、输入重采样、buffer 与显示侧问题；
- 自有动画是否使用统一的纳秒绝对时间；
- 是否通过多次重复与高分位分布验证收益。

## 相关章节

- [卡顿定义与 FrameTimeline](01-jank-definition-causes.md)
- [卡顿分析方法论](02-jank-methodology-scenarios-cases.md)
- [RecyclerView 列表滑动性能](../../part5-app/ch22-rendering-practice/02-recyclerview-compose-lazylist.md)
- [3.2 触摸延迟、预测与低延迟渲染](../../part1-fundamentals/ch03-input/02-touch-performance.md)
- [可变刷新率与帧率选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md)
- [标准 View/HWUI 渲染管线](../ch13-rendering-pipelines/01-android-view-pipeline-analysis.md)

## 参考资料

- [Android 17 `OverScroller.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/OverScroller.java)
- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 17 `AnimationUtils.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/animation/AnimationUtils.java)
- [Android 17 `InputConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputConsumer.cpp)
- [Choreographer API](https://developer.android.com/reference/android/view/Choreographer)
- [AppJankStats API](https://developer.android.com/reference/android/app/jank/AppJankStats)
- [RelativeFrameTimeHistogram API](https://developer.android.com/reference/android/app/jank/RelativeFrameTimeHistogram)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
