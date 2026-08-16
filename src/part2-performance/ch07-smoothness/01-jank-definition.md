---
title: 卡顿的定义与分类
section: '7.1'
chapter: '7.1'
status: "finalized"
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: "2026-07-11"
last_verified_against: "AOSP android-17.0.0_r1 FrameTimeline/JankInfo/VsyncConfiguration + Perfetto android.frames.timeline/android.binder stdlib / Android Developers docs"
task2b_state: "fixed"
task6_state: reviewed
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
confidence: high
sources:
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp
- type: aosp
  path: frameworks/native/libs/gui/include/gui/JankInfo.h
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://developer.android.com/topic/performance/vitals/render
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/metrics/performance/JankStats
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
- type: blog
  path: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/VsyncConfiguration.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/sysprop/SurfaceFlingerProperties.sysprop
tags:
- jank
- smoothness
- FrameTimeline
- Choreographer
- 掉帧
- 渲染性能
related_chapters:
- '2.1'
- '2.3'
- '2.4'
- '2.5'
- '7.2'
- '7.3'
- '7.4'
- '8.1'
- '9.1'
---
# 7.1 卡顿的定义与分类

## 从用户描述到可验证问题

“页面有点卡”可能对应三类问题：画面节奏异常、输入到可见反馈过慢、应用没有在系统规定的时间内响应。它们都会破坏流畅体验，但要从不同的证据开始分析。

| 现象 | 工程口径 | 主要证据 |
|------|----------|----------|
| 滑动或动画出现停顿、跳变 | 渲染 jank（画面节奏异常） | FrameTimeline、Choreographer、RenderThread、SurfaceFlinger、HWC |
| 点击后很久才出现反馈，画面仍可能稳定 | 响应延迟 | Input（输入分发）、主线程消息、Binder、启动与业务处理路径 |
| 系统判定应用没有及时响应 | ANR（Application Not Responding，应用无响应） | ANR reason（系统记录的触发原因）、超时类型、主线程与相关进程栈、系统事件 |

三类问题可以在广义流畅性范围内一起治理，诊断时仍要保留各自边界。渲染慢帧不一定引发 ANR，平均 FPS（Frames Per Second，每秒帧数）正常也不能排除输入延迟。

## Jank 的 Android 17 口径

在 FrameTimeline（逐帧时间线）的语义里，一帧的实际呈现时间偏离 Scheduler（调度器）预测的呈现时间时，该帧会进入异常分类。偏离可能表现为帧间隔不稳定，也可能表现为画面节奏均匀、输入延迟却逐帧增加。因此，jank 分析要同时回答“何时完成”和“何时呈现”。

刷新周期给出最直观的时间尺度：

| 刷新率 | 相邻刷新周期 |
|--------|--------------|
| 60 Hz | 16.67 ms |
| 90 Hz | 11.11 ms |
| 120 Hz | 8.33 ms |

这些数字表示显示刷新周期，并非主线程（MainThread）、RenderThread 和 SurfaceFlinger 必须依次执行完毕的总耗时。Android 显示栈采用流水线：标准 HWUI（Android 硬件加速 UI 渲染器）窗口通常经过 `Choreographer#doFrame`（一帧 UI 工作的回调入口）、RenderThread（渲染线程）、BLASTBufferQueue（图形缓冲区队列）、SurfaceFlinger（系统合成服务）、HWC（Hardware Composer，硬件合成器）与 display present（显示提交）。每一段都有自己的调度窗口和同步边界。120 Hz 会缩短相邻刷新周期，但不能据此要求每个 slice（时间区间）都小于 8.33 ms；应比较该帧的 expected timeline、actual timeline、finish 状态与 present 结果。

同一个应用还可能存在多种出图路径。标准 App Window 的像素生产者通常在应用进程，SurfaceView、Camera、Video、Native Graphics、Flutter 或游戏可能使用独立 Surface、独立 layer（图层）或其他生产线程。分析前应确认四个对象：谁生产 buffer（图形缓冲区）、buffer 进入哪个 Surface、对应哪个 layer，以及由 HWC 还是 RenderEngine（SurfaceFlinger 的 GPU 合成引擎）完成相关合成。出图类型判断错误时，针对主线程或 RenderThread 得出的结论便无法覆盖整幅画面。

## FrameTimeline 如何描述一帧

Android 12 / API 31 起，SurfaceFlinger 的 FrameTimeline 会为应用提交的 SurfaceFrame（某个 Surface 的一帧）和最终显示侧的 DisplayFrame（一次显示合成帧）记录预测与实测时间。Surface 是应用向显示系统提交图形缓冲区的接口。Android 17 的实现锚点是 `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp`，类型定义位于 `frameworks/native/libs/gui/include/gui/JankInfo.h`。

### Expected Timeline 与 Actual Timeline

应用侧 `Expected Timeline` 表示调度器为该 SurfaceFrame 预留的时间窗口，起点对应 Choreographer（按显示节奏安排帧回调的组件）计划运行回调的时间。`Actual Timeline` 从 `Choreographer#doFrame` 或 `AChoreographer_vsyncCallback` 开始，结束点取应用提交 buffer 和 GPU 完成时间中较晚的一个。SurfaceFlinger 也有自己的 expected/actual track（轨道），范围覆盖合成工作及显示栈下游的 present。

判断一帧时要一起读取以下字段：

- `Present Type`：early（早于预期）、on-time（按时）或 late（晚于预期）；
- `On time finish`：本侧工作是否在 deadline（截止时间）前完成；
- `Jank Type`：SurfaceFlinger 给出的原因位标志；
- `Prediction Type`：调度预测仍然有效还是已经过期；
- `GPU Composition`：该 DisplayFrame 是否使用 GPU 合成；
- `Layer Name` 与 `Is Buffer`：当前 slice 对应哪个 layer，以及它是否携带图形 buffer。

仅凭 actual slice 很长无法确定责任方。应用可能按时交帧，显示末端仍然晚；应用也可能晚交帧，但本次 present 受前一帧或 buffer 队列状态影响。`On time finish`、`Present Type` 和 `Jank Type` 需要放在同一个 SurfaceFrame / DisplayFrame 关系中解释。

### SurfaceFrame token 与 DisplayFrame token

Perfetto SQL 同时提供 `surface_frame_token` 和 `display_frame_token`。token 是关联同一帧记录的标识：前者标识应用或 layer 的 SurfaceFrame，后者标识 SurfaceFlinger 组织的 DisplayFrame。一个 DisplayFrame 可以合成多个 layer frame，因此两类 token 不能互换。

应用 token 会出现在应用 timeline，并作为调试信息写入 `doFrame` 与 RenderThread slice；SurfaceFlinger 的显示工作也有对应 token。Perfetto 的 flow（跨轨道关联线）把应用 SurfaceFrame 指向参与合成的 DisplayFrame。可靠的做法是沿 flow 或两列 token 建立关系，不根据时间是否接近来猜测两条记录属于同一帧。

### FrameTimeline 的覆盖边界

Perfetto 官方文档明确指出，FrameTimeline 对 SurfaceView 的支持仍然有限。独立 Surface、视频 overlay（硬件叠加层）、Camera、Native Graphics 等路径也可能缺少完整的应用 `doFrame` 关联。此时没有 App timeline，不代表没有渲染工作。

分析这类 trace（跟踪记录）时，应回到实际的出图对象，检查目标 layer、buffer 更新、acquire fence（等待生产完成的同步栅栏）、SurfaceFlinger latch（锁定本帧 buffer）、composition type（合成类型）、display present fence（显示完成栅栏）与 release fence（buffer 可再次使用的栅栏）。只有标准 HWUI 窗口适合把 App timeline、`doFrame` 和 RenderThread 当作一条完整主线。

## Android 17 的 JankType

`JankType` 是位标志：每一位代表一种原因，因此同一帧可以同时携带多个原因，UI 展示的字符串也可能组合多个值。以下表格以 `android-17.0.0_r1` 的 `JankInfo.h` 与 `FrameTimeline.cpp` 为准。表中的 SF 是 SurfaceFlinger，HAL（Hardware Abstraction Layer）是硬件抽象层，deadline 是本阶段按调度计划完成工作的截止时间。

| JankType | 值 | 表达的边界 | 诊断入口 |
|----------|----|------------|----------|
| `DisplayHAL` | `0x1` | SF 按时完成，而显示末端的 present 仍然偏离预期 | HWC、Composer HAL、present fence、显示驱动 |
| `SurfaceFlingerCpuDeadlineMissed` | `0x2` | SF 在 CPU / HWC 工作阶段错过 deadline | SF 主线程、HWC validate/present（验证合成方案/提交显示）、调度延迟 |
| `SurfaceFlingerGpuDeadlineMissed` | `0x4` | SF 使用 GPU composition（GPU 合成）时错过 deadline | RenderEngine、GPU queue（GPU 任务队列）、client target fence（GPU 合成目标的完成栅栏） |
| `AppDeadlineMissed` | `0x8` | 应用或应用提交的 GPU 工作没有按时准备好 | MainThread、RenderThread、GPU、queueBuffer（提交缓冲区）/acquire fence |
| `PredictionError` | `0x10` | VSync 预测与硬件节奏的偏差超出分类阈值 | Scheduler 预测、HW VSync（硬件垂直同步信号）、刷新率变化 |
| `SurfaceFlingerScheduling` | `0x20` | SF 的工作调度时机造成异常呈现 | SF 的 runnable/running（可运行/运行中）状态、wakeup（唤醒）与 latch 时序 |
| `BufferStuffing` | `0x40` | 前一 buffer 占用了本帧期望的呈现周期，后续 buffer 被推迟 | BufferQueue（缓冲区队列）深度，以及入队、latch、present 的顺序 |
| `Unknown` | `0x80` | 现有证据不足以归入已知原因 | 检查 trace 配置、fence 与上下文 |
| `SurfaceFlingerStuffing` | `0x100` | 前一 DisplayFrame 运行过长，把当前 SF frame 推迟到后续周期 | 连续 DisplayFrame 与 SF 工作时长 |
| `Dropped` | `0x200` | 更新后的 frame 替代当前 frame，当前 frame 未呈现 | App 与 SF 两侧的 dropped slice（未呈现帧区间）、buffer 替换关系 |
| `NonAnimating` | `0x400` | 呈现不准时，但内容不属于动画；源码不将其计入严重度计算 | layer 是否在动画或跟手交互路径 |
| `AppResyncedJitter` | `0x800` | 应用修改了该帧的 VSync time（垂直同步时间） | App frame timeline、resync（重新对齐）行为 |
| `DisplayNotOn` | `0x1000` | 屏幕关闭或处于 doze（低功耗待机） | display power state（显示电源状态） |
| `DisplayModeChangeInProgress` | `0x2000` | 显示模式切换进行中 | 刷新率、分辨率与 mode switch（模式切换）区间 |
| `DisplayPowerModeChangeInProgress` | `0x4000` | 显示电源模式切换进行中 | 亮灭屏与 power mode（电源模式）时序 |

源码中的 `calculateJankSeverity()` 还会把这些位分成参与严重度计算和仅描述状态的集合。`BufferStuffing`、`SurfaceFlingerStuffing`、`NonAnimating` 以及三类显示状态位不直接进入 jank 严重度计算，但仍有诊断价值。例如，Buffer Stuffing 常对应 Perfetto 的 high-latency state（高延迟状态）：帧间隔可能保持稳定，输入到显示的延迟却在增加。

Android 17 还定义了 `JankSeverityType`：`Partial` 表示超出 deadline 的部分小于一个应用 frame interval（帧间隔），`Full` 表示超出量达到或超过一个应用 frame interval。严重度计算依赖有效的 expected/actual present delta（预期与实际呈现时间差）；证据不足时为 `Unknown`。

### App、SurfaceFlinger 与 Display 三层归因

工程排查可以把位标志按责任边界归成三层，但这只是导航，不应覆盖源码枚举：

- App 层关注 `AppDeadlineMissed`、`AppResyncedJitter`，并检查 UI 线程、RenderThread、应用 GPU 与 buffer 提交；
- SurfaceFlinger 层关注 CPU/GPU deadline、SF scheduling 与 SF stuffing，检查合成线程、RenderEngine、HWC 调用和调度；
- Display 层关注 `DisplayHAL` 及显示状态变化，检查 Composer HAL、present fence、显示模式与电源模式切换。

`PredictionError`、`Dropped`、`Unknown` 和 `BufferStuffing` 需要结合 SurfaceFrame、DisplayFrame 及相邻帧判断。直接归给单一进程，会遗漏形成结果所需的前后条件。

### 颜色只用于导航

Perfetto 当前 UI 用绿色、浅绿色、红色、黄色和蓝色区分正常帧、高延迟状态、当前进程负责的 jank、应用无责的 jank 与 dropped frame（未呈现帧）。颜色属于界面展示约定，不能代替 `Jank Type`。工具版本、主题或可视化实现变化后，固定色值没有稳定的接口含义。分析记录应写出字段和 token，不应只写“红色帧”。

## 聚合指标的适用范围

### Janky Frame Rate

`janky frames / observed frames` 表示异常帧数占观测帧数的比例，只有在分子、分母和场景定义一致时才可以比较。至少要记录刷新率、交互路径、统计窗口、是否包含启动过渡、帧来源与工具版本。把 60 Hz 与 120 Hz、持续滑动与页面首帧、标准 HWUI 与视频 overlay 混在一起，得到的数字便缺少解释力。

平均 FPS 只描述单位时间内呈现了多少帧。两个会话都可能是 50 FPS，其中一个帧间隔均匀，另一个却包含长停顿和密集补帧，体验差异很大。版本回归至少要同时保留帧间隔分布、jank 类型、最长连续异常区间和具体场景。

### Slow frame 与 Frozen frame

Android vitals（Google Play 质量指标）对 View / Canvas UI 的传统渲染统计使用以下口径：slow frame（慢帧）的渲染时间位于 16 ms 到 700 ms，frozen frame（冻结帧）超过 700 ms。官方文档也说明，这组数据无法覆盖 Vulkan、Unity、Unreal、OpenGL 等绕过 Android UI Toolkit（界面工具包）的全部画面。

16 ms 是面向 60 FPS 的传统阈值。在 90 Hz、120 Hz 或动态刷新率设备上，FrameTimeline 的 expected/actual 结果更贴近该帧当时的调度条件。Frozen frame 的 700 ms 阈值适合发现严重停顿，但不能替代逐帧 deadline 归因。

### ANR 属于另一套判定

系统会针对输入分发、广播、前台服务和 ContentProvider 等不同响应义务分别判定 ANR。超时时间受触发类型、进程状态和平台策略影响，“大于 5 秒就是 ANR”只适用于部分常见输入场景，不能作为通用公式。

一帧超过 700 ms 时，系统可能仍未触发 ANR；ANR 发生时也不要求应用正在绘制某一帧。二者可以由同一次主线程阻塞共同引发，结论仍要分别引用 FrameTimeline 或渲染统计，以及 ANR reason 与系统栈。

## 用户感知没有单一毫秒阈值

人对延迟和画面不连续的感知受任务影响。跟手滑动、手写、拖拽和游戏控制对时延更敏感；无交互的渐入动画、静态页面或视频播放采用不同的节奏与补偿机制。显示刷新率、触控采样、运动速度、运动模糊、连续异常帧数量也会改变感受。

因此，不能用“漏一帧通常无感”或“连续三帧必然可感知”给出跨设备结论。工程指标应从真实场景建立：记录输入事件到目标 layer 首次出现可见变化的延迟，再结合帧间隔、连续异常段和用户任务解释。电影的 24 FPS 也不适合作为 UI 流畅度下限，因为曝光产生的运动模糊、内容节奏和交互要求都不同。

## 一次可靠的 FrameTimeline 读取顺序

1. 复现单一场景，记录设备刷新率、显示模式、交互步骤和 trace 配置。
2. 确认出图类型：Producer（图形内容生产者）、Surface、layer、buffer 路径和合成方式。
3. 在应用 `Actual Timeline` 选择异常 SurfaceFrame，读取两类 token、layer、finish、present 与 jank 字段。
4. 沿 flow 找到 DisplayFrame，核对 SF actual/expected、GPU composition（GPU 合成）和 present 结果。
5. 根据位标志选择线程与子系统：App、SF CPU、SF GPU、HWC、display、buffer 或预测。
6. 在已经锁定的帧窗口内检查 Binder、调度、锁、I/O、GC（垃圾回收）、GPU queue 和 fence，避免从全局慢事件反推帧责任。
7. 观察相邻帧。Stuffing、Dropped、模式切换和预测偏差都依赖前后关系。

Binder transaction（Binder 调用）、GC 或某个长 slice 只能说明它与帧窗口重叠。要把它写成根因，还需证明它位于责任线程或依赖路径，并且足以解释 finish/present 的偏差。详细 SQL 与因果分析见 [7.3 卡顿分析流程与方法](03-jank-methodology.md)，这里只说明归因规则。

## JankStats 的角色

AndroidX `JankStats` 用于应用内逐帧监测，可以把页面、交互状态等 UI context（界面上下文）随 `FrameData`（单帧数据）上报。它从 API 16 起提供基础能力，API 24 起使用更可靠的平台 timing（计时数据），API 31 起可以利用更丰富的帧信息。不同 API 级别的精度不同。

`jankHeuristicMultiplier` 使用当前 frame period（帧周期）计算库侧的启发式阈值，默认值为 `2`。因此，JankStats 默认不会把每个刚超过一个刷新周期的 frame 都报告为 jank。该阈值属于 AndroidX 库的监测策略，与 SurfaceFlinger 的 FrameTimeline 分类不是同一套口径。

线上数据适合回答“哪个 UI 状态经常出现异常帧”；Perfetto 适合回答“这一帧在 App、SurfaceFlinger、HWC 或显示末端发生了什么”。常见流程是先用 JankStats 或回归平台定位高风险场景，再采集 trace 完成单帧归因。

## 常见误判

| 误判 | 修正方式 |
|------|----------|
| FPS 高，所以没有卡顿 | 检查帧间隔分布、连续异常段和 FrameTimeline 类型 |
| `AppDeadlineMissed` 只说明主线程慢 | 同时检查 RenderThread、应用 GPU、queueBuffer 与 acquire fence |
| App timeline 正常，应用一定无关 | 确认是否存在独立 Surface、额外 layer 或非 HWUI Producer |
| 红色对应一种固定 JankType | 读取 details（详情）面板中的位标志；颜色仅用于界面导航 |
| `BufferStuffing` 等于单帧渲染过长 | 对齐前一帧、队列深度、latch 与 present，确认延迟如何传播 |
| Frozen frame 会按同一阈值变成 ANR | 分别核对渲染统计和 ANR 触发原因 |
| 目标必须是全局 0% jank | 按场景、刷新率、统计窗口和设备档位设预算，并追踪可复现峰值 |

## 版本边界

- Android 12 / API 31：FrameTimeline 进入现代逐帧归因流程；旧设备仍需依赖 Choreographer、RenderThread、SurfaceFlinger 与 VSync 时序。
- Android 17 / API 37：源码锚点为 `android-17.0.0_r1` 的 Scheduler/FrameTimeline 与 `JankInfo.h`；`NonAnimating`、`AppResyncedJitter` 和显示状态相关位均按该版本标签解释。
- Kernel（内核）：相关结论位于 framework（Android 框架层）、SurfaceFlinger、Composer HAL 与 trace 数据层。追踪 dma-buf（用于设备间共享的 DMA 缓冲区；DMA 即 Direct Memory Access，直接内存访问）、dma-fence（DMA 同步栅栏）、sync_file（承载栅栏的文件对象）或显示驱动时，内核锚点使用 `android17-6.18-2026-06_r6`。

## 与其他章节的关系

- [2.1 渲染架构全景](../../part1-fundamentals/ch02-rendering/01-rendering-overview.md)：理解应用生产、SurfaceFlinger 合成与显示提交。
- [Android 17 FrameTimeline、FrameTracer 与合成边界](../../part1-fundamentals/ch02-rendering/30-android17-frametimeline-composition-boundary.md)：查看 FrameTimeline、FrameTracer、TimeStats 与 JankTracker 的职责边界。
- [渲染管线总览](../ch18-rendering-pipelines/01-pipeline-overview.md)：按 Producer、Surface、layer 与合成路径识别出图类型。
- [7.2 卡顿原因体系](02-jank-causes.md)：从归因类型进入 CPU、GPU、调度、同步与 buffer 根因。
- [7.3 卡顿分析流程与方法](03-jank-methodology.md)：把异常帧、线程状态和子系统证据组织成可复现结论。
- [FrameTimeline Perfetto 分析](../../part3-tools/ch13-perfetto/19-frame-timeline-api33-perfetto-analysis.md)：补充 trace 配置与 SQL 查询。

## 参考资料

- [Perfetto：Android Jank detection with FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android Developers：Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Android Developers：Diagnose and fix ANRs](https://developer.android.com/topic/performance/vitals/anr)
- [AndroidX JankStats API reference](https://developer.android.com/reference/androidx/metrics/performance/JankStats)
- [AOSP Android 17 JankInfo.h](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/include/gui/JankInfo.h)
- [AOSP Android 17 FrameTimeline.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
