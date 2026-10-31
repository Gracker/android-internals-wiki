---
title: 感知流畅性：步幅波动与无掉帧卡顿
chapter: '7.3'
section: '7.3'
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-10-23'
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
- type: aosp-source
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_view_InputEventReceiver.cpp
- type: aosp-source
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/jank/AppJankStats.java
- type: aosp-source
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/jank/RelativeFrameTimeHistogram.java
- type: aosp-source
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java
- type: official-doc
  path: https://source.android.com/docs/core/graphics/arr
- type: official-doc
  path: https://perfetto.dev/docs/concepts/clock-sync
- type: official-source
  path: https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar
- type: blog
  path: https://gafferongames.com/post/fix_your_timestep/
tags:
- perceived-smoothness
- step-jitter
- frametimeline
- overscroller
- android-performance
status: finalized
last_idle_audit_at: '2026-08-01T22:35:12+08:00'
last_rework_at: '2026-08-03T09:42:34+08:00'
last_review_finalize_at: '2026-08-03T10:05:40+08:00'
---

# 感知流畅性：步幅波动与无掉帧卡顿

> ⚠️ 校勘（2026-10-23）：旧文把 App 准时完成概括为未触发 jank，并把 8/9 ms 写成“交替”；下文分别按显示链责任与绝对时间量化示例更正。Buffer Stuffing Recovery 的多次延后/阈值分支，以及 histogram 的调用方职责和区间端点，也已按 r1 源码复核。

App 在自身 deadline（截止时间）前完成一帧，通常说明它满足了这一帧的完成预算；但这一帧到用户眼前还要经过 SurfaceFlinger、显示末端等环节，任何一处仍可能出现其他分类的 jank。而且画面里的对象是否沿预期轨迹移动，还要看输入采样、运动模型、数值精度、像素取整、buffer（图形缓冲区）提交、刷新率选择和 present（呈现）节拍。我们把这两类问题分开叫：“帧准时”与“运动均匀”。

> 源码基线：AOSP `android-17.0.0_r1`；内核 `android17-6.18-2026-06_r6`。

源码核对覆盖 `OverScroller`、`Choreographer`、`AnimationUtils`、InputConsumer（输入事件消费组件）与 FrameTimeline（逐帧时间线）；内核只用来解释调度和 fence（同步栅栏）这类现象，动画轨迹由平台这一层定义。

## “帧准时”与“运动均匀”是两组数据

做流畅性分析时，我们至少要看三条时间线：

| 时间线 | 观察对象 | 常用证据 |
|---|---|---|
| 帧生产与呈现 | App 是否按期交帧、SurfaceFlinger（系统合成服务）是否按期合成与 present | Expected/Actual FrameTimeline（预期/实际帧时间线）、RenderThread（渲染线程）、GPU、present fence（显示呈现栅栏） |
| 运动轨迹 | 每个呈现机会对应的坐标、速度、加速度是否符合设计曲线 | App 自定义 counter（计数轨道）、动画值、列表累计位移、高速相机 |
| 输入到画面 | 输入样本、重采样坐标、App 消费、画面更新之间是否稳定 | InputReader/InputDispatcher/InputConsumer（输入读取/分发/消费组件）、MotionEvent（触摸事件）、自定义状态、present |

FrameTimeline 里的绿色帧，只说明这一帧没有被判成 jank。FrameTimeline 保存的是帧的时间信息，`scrollY`、`translationX`、相机视角、动画进度都不在里面；所以哪怕一路全绿，要确认运动轨迹均匀，还得单独采样轨迹。

再看运动本身：减速 fling（惯性滑动）的每帧位移本来就该逐渐缩小，直接计算 `Δx`（相邻帧位移）的方差，会把设计曲线里的减速也算成抖动。所以测量时我们要么比较观测轨迹与目标轨迹，要么选一个期望速度近似恒定的短时间窗口，在窗口内比较步幅。


### 先按现象分类

| 现象 | 更可能的方向 | 仍需排除 |
|---|---|---|
| FrameTimeline 按期，模型坐标相对目标曲线有周期残差（观测位置与目标位置之差） | 时间量化、积分方式、插值、整数像素取整 | 采样点是否对应同一帧 |
| 模型坐标平稳，Actual/Present 间隔波动 | buffer、SurfaceFlinger、刷新率切换、显示侧 | App counter 记录时刻与显示时刻的差异 |
| 跟手阶段异常，抬手后的 fling 正常 | 输入采样、重采样、velocity estimate（速度估算）、预测 | 业务手势处理和主线程调度 |
| fling 异常，手指跟随阶段正常 | `OverScroller`、自定义物理模型、SnapHelper、item 尺寸 | create/bind/layout 和图片回调 |
| App 与显示节奏都平稳，高速相机仍看到不连续 | 面板扫描、像素响应、内容对比度或设备显示处理 | 相机曝光、快门和同步误差 |

“无掉帧卡顿”是用户能观察到的现象，也是我们排查的起点；要落到根因，还得顺着上表的方向继续取证。

## OverScroller 的时间模型

### 整数毫秒来自哪里

先看时间从哪里来。`SplineOverScroller.update()` 通过 `AnimationUtils.currentAnimationTimeMillis()` 取得当前时间，再计算 `currentTime = time - mStartTime`。常规 fling 走 `SPLINE`（样条减速曲线）分支：把 elapsed time（已经过的时间）除以 `mSplineDuration`，在 101 个 `SPLINE_POSITION` 采样点之间做线性插值，再把结果乘以 `mSplineDistance`。位置写入 `mCurrentPosition` 前，还要经过 `Math.round(distance)` 取整到像素。

这条路径上有三种离散化在叠加：

1. VSync（垂直同步）纳秒时间进入 legacy animation clock（旧动画时钟）时变成整数毫秒；
2. spline（样条曲线）使用固定采样表并在相邻点之间插值；
3. `mCurrentPosition` 是整数像素。

<!-- gracker-diagram: ch07-03-overscroller-discretization -->
![OverScroller 的三处离散化](../../assets/diagrams/ch07/ch07-03-overscroller-discretization.png)

图：这是普通 SPLINE 更新路径：整数毫秒输入、分段线性插值和整数像素输出分处不同位置。BALLISTIC、CUBIC、结束与边界处理另有分支；三处离散化都需结合轨迹验证。

这三项的影响并不相同。第二项是分段线性近似，未必产生可见问题；第三项在低速末段很常见——位置停在一个像素上，或者突然跳过一个像素，都可能是整数位置造成的；第一项取决于整数毫秒换算，我们放到下一小节单独算。至于三项会不会真的被用户看到，要结合速度、屏幕密度、内容边缘和 present 节拍测量。

<!-- gracker-diagram: ch07-03-pixel-rounding-example -->
![整数像素会怎样改变低速步幅](../../assets/diagrams/ch07/ch07-03-pixel-rounding-example.png)

图：示意的分数像素模型每次增加 0.4 px，经 Java Math.round 后，输出可能重复一个像素，再前进一个像素。此例只隔离取整效应，不是 OverScroller 减速曲线或目标设备实测。

这条路径的源码入口是 [`OverScroller.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/widget/OverScroller.java)。

### 8/9 ms 混合从哪里来

`Choreographer.doFrame()` 保留着纳秒级 `frameTimeNanos`，但调用 legacy animation clock 时会执行 `frameTimeNanos / NANOS_PER_MS`，整数除法向下截断。理想的 120 Hz 周期约为 8.333 ms，映射到整数毫秒后，相邻 animation time（动画时间）的差值就分布在 8 ms 与 9 ms 之间：零相位的理想算术示例为 `0, 8, 16, 25, 33, 41, 50 ms`，差值为 `8, 8, 9, 8, 8, 9 ms`。60 Hz 常见 16/17 ms，90 Hz 常见 11/12 ms；这组整数序列是换算示例，不是设备实测。

具体序列会随起始相位、显示模式、VSync 预测和是否跳帧而变，但它是整数换算规则的量化结果，规律来自截断位置，与每帧随机增减 1 ms 是两回事。把 1 ms 除以 8.33 ms 得到约 12%，描述的只是两个时间数值的比例；要把它说成位移误差或用户感知概率，还需要轨迹与呈现证据。

<!-- gracker-diagram: ch07-03-quantized-time-example -->
![120 Hz 的绝对时间量化示例](../../assets/diagrams/ch07/ch07-03-quantized-time-example.png)

图：理想 120 Hz、零相位的算术示例：先截断每个绝对时间戳，再相减得到 8、8、9 ms 的重复组合。轨道按这些理想数值绘制，属于换算示意，不是设备采集数据。

落到 `OverScroller` 上：高速、曲线斜率较大的区间，相邻整数毫秒采样可能形成不同的整数像素步幅；内容速度较低、屏幕密度较高，或显示侧节拍同时变化时，观测到的步幅又会不同。某台设备究竟有没有受影响，只有轨迹采样说了算。

## Choreographer 保留了哪些精度

`Choreographer` 这边保留的精度更高：`doFrame()` 内部维护纳秒级 frame time（帧时间）、frame interval（帧间隔）和 deadline，以及平台可能提供的 frame timeline（帧时间线）；公开的 `FrameCallback.doFrame(frameTimeNanos)` 接收的也是纳秒时间。不过单位为 ns 不表示硬件或调度具有 1 ns 的实测精度。API 33 起，`postVsyncCallback()` 还能提供 `FrameData` 和候选 presentation timeline（呈现时间线）。`FrameData` / `FrameTimeline` 只在该 VSync 回调内有效，需要异步留存时，应在回调内复制 vsync ID、expected presentation 和 deadline 等数值。

精度在哪里降下来？就在 legacy View animation clock 的转换位置：`AnimationUtils.lockAnimationClock(frameTimeNanos / NANOS_PER_MS)`。这把锁是线程局部的：执行该 Choreographer 回调的同一线程里，旧动画与滚动代码读到的是 `max(currentVsyncTimeMillis, lastReportedTimeMillis)`。`lastReportedTimeMillis` 记录最近一次未锁定时的 `uptimeMillis()` 读数，作用是避免锁定时间退到该读数之前；至于全局时钟或跨线程同步，它管不到。

下面三句说的对象各不相同，我们分开核对：

<!-- gracker-diagram: ch07-03-clock-precision-scope -->
![纳秒帧时间与线程局部毫秒动画钟](../../assets/diagrams/ch07/ch07-03-clock-precision-scope.png)

图：Choreographer 保留以 ns 为单位的帧信息，legacy AnimationUtils 消费线程局部的整数毫秒值。其他动画框架按各自实现核对；API 33+ 的 FrameData/FrameTimeline 需要在 VSync 回调内读出并复制必要字段。

- Choreographer 的帧时间是纳秒级；
- legacy `AnimationUtils` 消费者使用整数毫秒；
- Compose frame clock（帧时钟）、自定义 `FrameCallback` 或其他引擎是否保留纳秒精度，要按各自实现核对。

平台源码可在 [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java) 和 [`AnimationUtils.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/animation/AnimationUtils.java)复核。

## 输入重采样的条件

跟手性问题查到输入这一层时，我们先要弄清重采样发生在哪条路径上。本文核对的是常规 ViewRootImpl 的 JNI 路径：`NativeInputEventReceiver` 在目标应用进程内使用 `InputConsumer`，重采样逻辑在 `frameworks/native/libs/input/InputConsumer.cpp`。启用重采样且 frame time 有效时，批量消费的目标 sample time 从 frame time 回退 `RESAMPLE_LATENCY = 5 ms`。

接下来的分支看样本条件：有 future sample（目标时刻之后的样本）时，算法在前后样本之间插值；只有历史样本时才外推，也就是按已有趋势预测后续位置。外推上限同时受最近样本间隔的一半和 `RESAMPLE_MAX_PREDICTION = 8 ms` 限制。插值要求前后样本间隔至少 2 ms；外推要求最近两个真实样本的间隔在 `[2, 20] ms` 内，并受 pointer/source、工具类型、显示屏及 MOVE 等条件约束。遇到无效 frame time（例如 `-1`）时，批次会被直接消费，不走这条重采样路径。

这里要防一个误读：5 ms 是算法挑重采样时刻用的偏移，端到端响应是否因此固定多出 5 ms，要看触控采样率、VSync 时序、历史样本、触控工具类型（手指或触控笔等）和预测方向。

<!-- gracker-diagram: ch07-03-input-resampling-branches -->
![目标采样时间、插值与受限外推](../../assets/diagrams/ch07/ch07-03-input-resampling-branches.png)

图：图限常规 ViewRootImpl JNI 的 InputConsumer。有效帧时间和启用条件满足时，目标为 frameTime−5 ms；前后样本可插值，只有历史样本时才受限外推。条件不满足时保留真实数据路径，不把 5 ms 解释成额外睡眠。

`ro.input.resampling` 是系统只读产品属性，第三方 App 拿不到运行时优化开关；OEM（设备厂商）、系统镜像或 userdebug（可调试系统构建）实验可以做 A/B（对照实验）。普通应用这边，应采集原始 MotionEvent、消费时刻、模型坐标和 present 证据。

源码可查 [`InputConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputConsumer.cpp)。

## Buffer Stuffing Recovery 放在哪一层

buffer 一侧的问题要换一层看。Buffer stuffing 描述的是生产与消费节拍失配时额外排队、呈现延后的现象，也可能形成 dequeue / buffer release 等待。`Choreographer` 里对应的内部状态是 `BufferStuffingState` 和 `onWaitForBufferRelease()`：传入的等待时长严格大于 `mLastFrameIntervalNanos / 2` 时，后者把 `isStuffed` 置位。这个检测是 Choreographer 的恢复触发线索，和 FrameTimeline 的 `Buffer Stuffing` 分类属于不同层的判定。

恢复动作可以返回 `DELAY_FRAME`，安排下一个 VSync 并直接返回；也可以返回 `OFFSET`，把本次动画 frame time 减去当前一个 frame interval。开启 multi-recovery 时，同一次动画可以多次延后；threshold flag 要到累计主动延后达到 100 ms 才抑制进一步主动延后，并不立即结束恢复——源码要等 idle 判断通过后才 reset 恢复状态。

这套 API 带有 `@hide`，仅供平台内部使用，并受内部 flag（开关）与实现约束；它会改变调度和动画时间线。在 Perfetto 里，我们还可能看到 `Buffer stuffing recovery` 轨道，或 FrameTimeline 的 `Buffer Stuffing` jank type（卡顿类型）。buffer 排队恢复与模型坐标量化是两种机制，也可能在同一个现场同时存在，取证时要分别进行。

排查时我们分开读三样东西：

- `OverScroller` 毫秒量化：App 运动模型输入时间的离散化；
- Buffer stuffing：窗口 Producer（生产者）因 buffer 不可用而受到 backpressure；
- Recovery：Choreographer 为减少排队 buffer，主动延后一帧并调整动画时间。

应用侧该做的是处理 buffer 生产过快、GPU/Consumer（消费者）变慢或帧节奏错误这些源头；内部 recovery API 留给平台自己。

<!-- gracker-diagram: ch07-03-buffer-recovery-actions -->
![Buffer Stuffing Recovery 的三类动作](../../assets/diagrams/ch07/ch07-03-buffer-recovery-actions.png)

图：等待超过上一帧周期一半可置位 isStuffed；doFrame 再按恢复状态和 flags 选动作。multi-recovery 可重复延后；100 ms 阈值只限制进一步主动延后，idle 判定才复位恢复状态。

## 怎样量化步幅波动

### 采集四组数据

一次可复现的测试，我们至少要记下四组数据：

- 分别记录 `frameTimeNanos`、模型实际使用的评估时间 `t_eval`、选定 timeline 的 expected presentation time；实际 present 时间另从显示侧关联。它们的阶段不同，不能互相代替；
- 运动模型输出，例如 scroller（滚动模型）位置、动画 progress（进度）、目标 transform（变换）；
- View 层消费后的结果，例如 RecyclerView 本帧累计 `dx/dy` 或稳定 item anchor（条目参照点）的 decorated position（含装饰偏移的位置）；
- FrameTimeline 中的 App SurfaceFrame（应用 Surface 帧记录）与 SurfaceFlinger DisplayFrame（整屏显示帧记录）。


这里有个容易踩的坑：UI 线程 counter 记录的只是应用在该时刻准备好的状态，像素是否已经上屏，它说了不算。要证明“用户看到的步幅”，应保留进程、layer、actual slice ID 与 surface/display token，再把应用状态关联到实际被呈现的 buffer/显示帧；同一 surface token 可能出现在多个 layer，配对时只按 token 等值是不够的。

跨日志与 trace 比较前，还要核对单位和时钟域：`frameTimeNanos` 使用 `System.nanoTime()` 时间基，Perfetto 可通过 clock snapshot 映射多种时钟，日志里的数值与 trace 的 `ts` 直接相减没有意义。原理见 [Perfetto 时钟同步](https://perfetto.dev/docs/concepts/clock-sync)。精度要求更高时，可以使用与 VSync 校准的高速相机或光学传感器。

<!-- gracker-diagram: ch07-03-clock-and-frame-identity -->
![关联前先校准时钟与帧身份](../../assets/diagrams/ch07/ch07-03-clock-and-frame-identity.png)

图：frameTime 使用 System.nanoTime 时间基，Perfetto 的 ts 可能已经过时钟映射。日志与 trace 要确认单位、时钟域和同步关系；再以进程、layer、slice、buffer/token 关联到真正被呈现的状态。

列表侧取数要挑稳定的身份。RecyclerView 的 `computeVerticalScrollOffset()` 可能受 LayoutManager 的 scrollbar（滚动条）估算策略影响，更稳妥的做法是记录同一条目的稳定业务键，或在 Adapter 已启用 stable IDs 时记录 item ID，再记录 decorated top（包含装饰偏移的顶部位置）和列表累计消费位移。会变化的 adapter position 和默认 `NO_ID` 都当不了稳定身份；多次 `onScrolled()` 应按实际关联的应用帧合并，并保留调用顺序。

### 用目标曲线计算残差

设采样为 `(t_i, x_i)`，我们先用几个基础量把轨迹描述出来：

- 时间步长 `Δt_i = t_i - t_(i-1)`；
- 位移步长 `Δx_i = x_i - x_(i-1)`；
- 观测速度 `v_i = Δx_i / Δt_i`；
- 目标位置 `x_expected(t_i)`；
- 轨迹残差 `e_i = x_i - x_expected(t_i)`。

窗口怎么选取决于运动形态。匀速时间窗口里，可以比较 `Δx` 或 `v` 的标准差与极差（最大值减最小值）；减速、回弹和贝塞尔动画则优先比较 `e_i`，并观察残差是否按 8/9 ms、11/12 ms 或刷新率切换呈现周期。如果离群点只有少数几个（明显偏离其他样本的点），还要检查跳帧、GC（垃圾回收）、调度和 item 布局。

算残差之前，先说明时间轴：内部模型用 `x_model - x_expected(t_eval)`；评估可见运动时，则用实际呈现 buffer 的坐标，与目标曲线在实际 present 时刻的位置比较，并说明相位或预测约定——本来有阶段差的两个时间，不能当成同一时间。报告里保留带符号的 `e_i` 分布以观察偏置/周期，同时给 `|e_i|` 的中位数、P95/P99 和峰值来描述误差大小；设备、刷新模式、Android build、初速度、内容、采样长度和重复次数也要齐全。

<!-- gracker-diagram: ch07-03-residual-reference -->
![轨迹残差要用同一时间轴](../../assets/diagrams/ch07/ch07-03-residual-reference.png)

图：内部模型与目标曲线在同一 t_eval 比较；可见运动按实际呈现状态与 present 时间比较，并说明设计的相位或预测约定。减速过程本来有变化，直接统计步幅方差容易把设计运动算成误差。

### Perfetto 能回答哪些问题

在这套流程里，Perfetto 负责回答五个问题：

1. Expected Timeline 给了 App 多长的工作时间；
2. Actual Timeline 中的 App work（应用工作）、GPU completion（GPU 完成）与 buffer post（缓冲区提交）是否按期；
3. SurfaceFlinger DisplayFrame 与 present 是否稳定；
4. 刷新率、线程调度、buffer stuffing（缓冲区积压）或合成是否在同一时间窗口发生变化；
5. App 自定义 counter 对应哪一帧。

FrameTimeline 从 Android 12 / API 31 起可用。在有效提交与 fence 时间的常见路径中，App Actual slice 的结束取 App buffer post 与 GPU completion 中较晚的一项；无效/缺失 fence 走源码回退分支，自行用 0 补齐是错的。SurfaceFlinger timeline 继续覆盖合成与显示阶段。具体字段以 [Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)为准。

## 一套对照实验

### 实验 A：时间量化

保留同一条运动曲线、初始位置和初速度，我们比较两种自有动画实现：

- 方案 A 使用每帧的 `frameTimeNanos`，计算从统一起点开始的绝对 elapsed time；
- 方案 B 先把同一个 `frameTimeNanos` 截断成整数毫秒，再计算 elapsed time。

两组都使用相同的布局与绘制。若 B 的轨迹残差出现与整数毫秒取值相关的周期，而 A 的残差明显减小，实验就支持时间量化假设；它验证的是我们自己的模型，RecyclerView 的感知问题是否都由 `OverScroller` 造成，还要另行验证。


### 实验 B：模型与呈现分离

实验 B 把模型与呈现分开看：在 App 中同时记录模型位置与 View 消费位置，并采集 FrameTimeline，再按最先波动的层分流：

- 模型与 View 都波动，present 稳定：检查运动模型、像素取整和布局；
- 模型稳定，View 波动：检查 LayoutManager、item 尺寸、Snap（吸附）或更新回调；
- 两者稳定，present 波动：查 RenderThread、buffer、SurfaceFlinger、ARR 和显示；
- 三者都波动：从最早出现偏差的层开始。

<!-- gracker-diagram: ch07-03-model-view-present-triage -->
![模型、View 和 present 的分层诊断](../../assets/diagrams/ch07/ch07-03-model-view-present-triage.png)

图：先确认样本身份和时钟已对齐，再看哪一层最早偏离。present 稳定时重点拆模型与 View，模型和 View 稳定而 present 不稳时追显示依赖；多层异常仍需因果证据和受控修改。

### 实验 C：刷新率与起始相位

在设备支持的固定 60/90/120 Hz 刷新率下重复同一脚本，再测试 ARR（Adaptive Refresh Rate，自适应刷新率）。每种刷新率都要做多次冷机和热机运行——分别对应设备温度较低和升温后的状态——并固定初速度和数据。若残差周期随刷新率对应的毫秒量化序列变化，可以继续验证 time source（时间来源）；若残差只在 mode switch（显示模式切换）期间出现，则应检查刷新率选择与 present。

设备是否支持固定模式要看机型；开发者选项的强制刷新率只用于实验控制，不能当成产品修复。


## 优化策略

### 自有动画使用统一的纳秒时间基准

自有动画和物理模型，应按同一个 VSync 时间基准计算绝对 elapsed time。模型评估时间一旦选定，就不要用回调实际到达时重新读取的 `uptimeMillis()` 替换；额外读钟可以用来测量执行延迟，但应与模型时间分开。这里还要区分“截断绝对时间戳后相减”和“把每段 `dt` 分别截断后累加”：前者的分段差值会混合出现，后者可能持续丢掉小数并产生累计漂移。

<!-- gracker-diagram: ch07-03-absolute-versus-delta-floor -->
![绝对时间截断与逐段 dt 截断的区别](../../assets/diagrams/ch07/ch07-03-absolute-versus-delta-floor.png)

图：理想 120 Hz、零相位、120 个周期的算术示例：绝对时间戳截断后相减为 1000 ms；每个 dt 单独截断为 8 ms 再累加，仅得到 960 ms。它说明逐段丢小数会累计，不是设备测量或 OverScroller 收益数据。

发生一次帧延迟后，模型按绝对时间重新求值，通常还能让轨迹对应正确的时间。物理模拟若需要固定步长，可用 accumulator（累加器）驱动次数受限的 simulation step（模拟步进）：正常消耗后余量小于一个步长时，可按约定在 previous/current 状态间插值；达到补算上限后仍有积压，就要显式定义减速、丢弃时间或其他策略，把大于 1 的余量比例直接当普通插值权重是不行的。

还要记住，固定步长是模型时间，不是该步的 CPU 执行时长；相位和端到端延迟也要纳入验收。方法与取舍见 [Glenn Fiedler：Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/)。

<!-- gracker-diagram: ch07-03-bounded-fixed-step -->
![固定模拟步进与显示插值的边界](../../assets/diagrams/ch07/ch07-03-bounded-fixed-step.png)

图：这是自有物理模型的设计方式。累加真实经过时间后，最多执行限定次数的固定步进；正常剩余不足一个步长时才按约定插值。若达到上限仍有积压，需要显式处理时间策略，不能把大于 1 的比例直接当普通插值权重。 步长 h 是模型时间，不是单次模拟的 CPU 用时。

### 平滑器的代价与适用范围

对 `dt` 或坐标应用 EMA（指数移动平均）能减少高频变化，代价是增加相位延迟——输出变化晚于输入——并改变速度和手感。它适合处理经过测量确认的传感噪声；拿它当时间量化、掉帧或输入预测错误的通用修复，就找错了对象。

<!-- gracker-diagram: ch07-03-ema-timing-tradeoff -->
![坐标平滑会怎样改变输出时序](../../assets/diagrams/ch07/ch07-03-ema-timing-tradeoff.png)

图：计算示例取 alpha=0.5、初值 y0=0，输入位置 0、1、2、3 得到输出 0、0.5、1.25、2.125。滤波改变了运动轨迹；是否值得平滑，需要同时测残差、跟手性和延迟，不能靠它纠正时间基或显示排队。

插值器同样没有固定的性能排名：任何曲线在斜率较大处，都会把时间误差放大成更大的位移误差。所以选择 `PathInterpolator`、spring（弹簧模型）或 spline 时，以交互设计要求的速度/加速度连续性和轨迹残差为准。

<!-- gracker-diagram: ch07-03-curve-slope-time-error -->
![曲线斜率怎样放大时间误差](../../assets/diagrams/ch07/ch07-03-curve-slope-time-error.png)

图：在局部可导且时间误差足够小时，位移误差约为 v(t)×delta t。同样 0.5 ms 的误差，在 100 与 1000 px/s 的局部速度下，近似为 0.05 与 0.5 px；这是隔离变量的算术示例，之后还可能叠加像素取整与显示节拍。

### RecyclerView 能改什么

RecyclerView 1.4.0 的 `ViewFlinger` 使用 `OverScroller`，应用没有公开 API 可以替换它的内部 time source。发现与毫秒量化相关的问题后，我们先确认它是否达到用户可感知的程度，再评估这些选择：

- 调整 fling 初速度、摩擦或 snap 行为，并做跨刷新率测量；
- 对特定控件实现受控的自定义滚动/动画；
- 向 AndroidX 或平台提交最小复现与轨迹证据。

而重写 LayoutManager 或 fling，会牵动 nested scrolling（嵌套滚动）、边界回弹、无障碍、焦点和手势行为约定，维护成本很高。


### 呈现节奏异常时的排查路径

如果 App 模型平稳而 present 不稳，继续调插值器就没有帮助了；这时应检查 expected/actual FrameTimeline、buffer backpressure（缓冲区反压，即生产速度超过消费速度）、RenderThread/GPU、SurfaceFlinger、刷新率选择和 present fence。完整过程参见[可变刷新率与帧率选择](../../part1-fundamentals/ch02-rendering/02-framerate-refresh-display-mode.md) 与 [标准 View/HWUI 渲染管线](../ch13-rendering-pipelines/01-android-view-pipeline-analysis.md)。


## AppJankStats 与 RelativeFrameTimeHistogram

统计侧的新工具是 Android 16 / API 36 加入的 `AppJankStats`、`RelativeFrameTimeHistogram` 和 `View.reportAppJankStats()`。它们让库组件按 widget（界面组件）、navigation component（导航目标）和状态，组织并报告总帧数、jank 帧数与相对 deadline 的帧时间分布。统计值由调用方准备：构造 `AppJankStats`、给 histogram 加数值，本身不会自动测量坐标或帧完成时间；`View.reportAppJankStats()` 做的是把这些统计交给宿主报告链，与系统统计合并。

<!-- gracker-diagram: ch07-03-app-jank-reporting -->
![组件统计的准备、封装与报告](../../assets/diagrams/ch07/ch07-03-app-jank-reporting.png)

图：API 36+ 的 AppJankStats 与 histogram 组织调用方准备的计数和时间分布，View.reportAppJankStats 交给宿主报告链。它适合组件状态聚合，坐标轨迹与跨进程原因仍需其他记录。

`RelativeFrameTimeHistogram.addRelativeFrameTimeMillis(int)` 接收调用方提供的整数毫秒差值，并按预定义区间累计；按类契约使用 `render finish - deadline`，负值表示提前，正值表示迟到。中间区间 `[-20, 20) ms` 的桶宽为 2 ms，例如 `[-2, 0)`、`[0, 2)`；20 ms 已进入 `[20, 25)` 桶。所有普通桶按左闭右开解释，外侧区间逐步变宽。差值本身由调用方算好，坐标、速度或像素变化都不在这份载体里——例如 0 ms 与 1 ms 落进同一个桶，想从桶计数还原每帧精确时间，或拿它替代单独的 jank 帧数，都做不到。

<!-- gracker-diagram: ch07-03-histogram-bucket-boundaries -->
![相对帧时间的符号与桶边界](../../assets/diagrams/ch07/ch07-03-histogram-bucket-boundaries.png)

图：按类契约，relative time=render finish−deadline，负值提前、正值迟到。中心桶宽 2 ms，但 20 ms 已属于 [20,25)；0 与 1 ms 同在 [0,2)，桶计数不能还原精确逐帧结果。

所以这组 API 适合 widget 级聚合；轨迹采样、Perfetto 对 App、SurfaceFlinger 和显示栈的分析，仍要按前面几节的做法来做。公开契约参见 [AppJankStats](https://developer.android.com/reference/android/app/jank/AppJankStats)、[RelativeFrameTimeHistogram](https://developer.android.com/reference/android/app/jank/RelativeFrameTimeHistogram) 和 [`View.reportAppJankStats()`](https://developer.android.com/reference/android/view/View#reportAppJankStats%28android.app.jank.AppJankStats%29)。

## ARR 与可变刷新率

ARR 可以在同一个显示模式内按内容节拍改变刷新率，所以刷新节拍一变就写成 active mode 切换，会把机制看简单了。分析时我们分别记录显示 VSync/TE 周期、应用 frame time/interval、render rate 与实际 present 节拍，再看整数毫秒动画时间的差值序列。前面列出的 60 Hz 16/17 ms、90 Hz 11/12 ms、120 Hz 8/9 ms 只是理想周期的映射示例；设备的 VSync 预测、切换相位和应用帧率请求还会影响观测结果。

“ARR 切换一定可见”这个结论，机制本身给不出来，要靠验证：在同一时间范围内核对 active mode（当前显示模式）、render rate（渲染帧率）、Expected/Actual FrameTimeline、App 位移 counter 与 present。若残差或呈现节拍异常集中在 mode switch 前后，这就是继续检查切换策略的线索；同窗口内的工作量、调度、buffer 和合成变化仍需排除，只凭时间相邻就认定切换是根因，是不够的。

RecyclerView 1.4.0 会在 `OverScroller` 滚动时调用 API 35 的 `View.setFrameContentVelocity()`，向平台报告内容速度。它以 px/s 提供内容速度信号；r1 View 实现中该值只对下一次绘制有效，且受 View 已附着与对应功能开关等条件约束。平台在适用时用它参与帧率决策，调用本身并不指定刷新率。相关机制见[RecyclerView 列表滑动性能](../../part5-app/ch22-rendering-practice/02-recyclerview-compose-lazylist.md)。

<!-- gracker-diagram: ch07-03-arr-signals-and-results -->
![内容速度信号与 ARR 实际节拍](../../assets/diagrams/ch07/ch07-03-arr-signals-and-results.png)

图：RecyclerView 1.4.0 在 API 35+ 使用内容速度信号参与平台决策；该值按绘制周期更新。ARR 可以在同一模式内改变刷新节拍，需分别看 VSync/TE、应用 interval/render rate 和实际 present。

## 各版本能力对照

| 版本 | 能力或行为 | 用途 |
|---|---|---|
| Android 12 / API 31 | FrameTimeline | 按时间关联 App SurfaceFrame、SurfaceFlinger DisplayFrame 与 present |
| Android 13 / API 33 | 公开 `Choreographer.VsyncCallback` 与 `FrameData` | 自有渲染可读取候选 frame timeline |
| Android 15 / API 35 | `View.setFrameContentVelocity()` | 滚动组件向平台提供内容速度 |
| Android 16 / API 36 | AppJankStats 与 RelativeFrameTimeHistogram | widget 级 jank 汇总，不含位移 |
| Android 17 / API 37 | 用于核对的平台源码版本 | 复核 OverScroller、Choreographer、InputConsumer、buffer recovery 与显示策略 |

最后是适用范围：平台和 OEM 可能修改 `OverScroller`、刷新率策略或输入参数；没有对应 build 源码时，以设备 trace、轨迹 counter 和光学结果为准。Chrome 或 OEM 私有实现也代表不了 AOSP（Android 开源项目）的通用结论。

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

- [Perfetto 多时钟域同步](https://perfetto.dev/docs/concepts/clock-sync)
- [AOSP ARR：模式内的刷新节拍](https://source.android.com/docs/core/graphics/arr)
- [RecyclerView 1.4.0 源码包](https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/1.4.0/recyclerview-1.4.0-sources.jar)
- [Glenn Fiedler：Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/)
