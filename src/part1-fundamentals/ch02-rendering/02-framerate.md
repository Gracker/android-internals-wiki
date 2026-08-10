---
title: 帧率与刷新率
chapter: '2.2'
section: '2.2'
status: finalized
reviewed_date: "2026-04-30"
reviewed_by: openclaw-task6
review_note: Task 6 三审(2026-04-30):移除 AIW 编辑注释 3 处、frontmatter 去重 1 处;task9 仍 needs-rework
rework_date: '2026-04-02'
rework_by: openclaw-task2b
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: 2026-07-25
last_verified_against: "AOSP android-17.0.0_r1: Choreographer/Display/View/ViewGroup/Window/Surface/SurfaceControl/FrameMetrics, SurfaceFlinger RefreshRateSelector/LayerHistory/Scheduler/FrameTimeline; Composer3 ARR AIDL; kernel android17-6.18-2026-06_r6 DRM vblank boundary; Writer rendering_pipelines S01/S02/S13"
confidence: high
sources:
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer
- type: official
  path: https://developer.android.com/games/sdk/frame-pacing
- type: official
  path: https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api
- type: official
  path: https://developer.android.com/reference/android/view/Surface#setFrameRate(float,int,int)
- type: official
  path: https://developer.android.com/reference/android/view/Surface#setProducerThrottlingEnabled(boolean)
- type: official
  path: https://developer.android.com/reference/android/view/Display
- type: official
  path: https://developer.android.com/develop/ui/views/layout/swinging-area
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
- type: official
  path: https://developer.android.com/reference/android/view/View#setRequestedFrameRate(float)
- type: official
  path: https://developer.android.com/reference/android/view/Window#setFrameRatePowerSavingsBalanced(boolean)
- type: official
  path: https://developer.android.com/reference/android/view/SurfaceControl.Transaction#setFrameTimeline(long)
- type: official
  path: https://source.android.com/docs/core/graphics/multiple-refresh-rate
- type: official
  path: https://source.android.com/docs/core/graphics/arr
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: aosp
  path: frameworks/base/core/java/android/view/DisplayEventReceiver.java
- type: aosp
  path: frameworks/base/core/java/android/view/SurfaceControl.java
- type: research
  path: Android-Internal-Wiki/intake/research-feeds/2026-03-30-15-arr-vsync-android15-16.md
- type: aosp
  path: frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
- type: aosp
  path: frameworks/base/core/java/android/view/Choreographer.java
- type: aosp
  path: frameworks/base/core/java/android/view/Display.java
- type: aosp
  path: frameworks/base/core/java/android/view/View.java
- type: aosp
  path: frameworks/base/core/java/android/view/ViewGroup.java
- type: aosp
  path: frameworks/base/core/java/android/view/Window.java
- type: aosp
  path: frameworks/base/core/java/android/view/Surface.java
- type: aosp
  path: frameworks/base/core/java/android/view/FrameMetrics.java
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp
- type: aosp
  path: hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl
- type: aosp
  path: hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl
- type: kernel
  path: drivers/gpu/drm/drm_vblank.c
- type: kernel
  path: include/drm/drm_vblank.h
- type: research
  path: Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: research
  path: Writer/rendering_pipelines/S02_aosp_standard_type.md
- type: research
  path: Writer/rendering_pipelines/S13_game_type.md
tags:
- framerate
- refresh-rate
- frame-time
- jank
- frame-pacing
- LTPO
- VRR
- ARR
- SurfaceFlinger
related_chapters:
- '2.1'
- '2.3'
- '2.4'
- '2.6'
- '2.9'
- '7.1'
re-review-result: 已纳入1条素材(部分纳入:OEM VSync修改误区+交叉引用),0处修正,待正常review质检
pipeline_stage: ready-to-publish
task6_result: pass-light-edit
task6_state: reviewed
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: 2026-06-15
task2b_result: fixed
task2b_state: fixed
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-15T00:20:00+08:00"
last_task9_audit: 2026-06-15
last_task9_audit_log: "logs/deep-review/2026-06-15-00-audit.md"
task9_review_notes: "2026-06-15 idle audit auto-fixed: corrected SurfaceControl.Transaction.setFrameTimeline(long) public SDK boundary from Android 16 to Android 15/API 35. P0 1 auto-fixed / P1 0 / P2 1 log-only; returned to Task6 revisit."
task2b_rework_note: "2026-05-22 2B修复: getSnapshot→summarize+chooseRefreshRateForContent; LayerVoteType 7→9种(补ExplicitGte/ExplicitCategory); ExplicitExact条件化(supportsAppFrameRateOverrideByContent). 前轮: Frame Time口径拆分; setFrameTimeline版本边界拆分"
last_task6_audit: "2026-06-12"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
last_task9_autofix_at: 2026-06-15
last_task6_at: "2026-06-15T04:09:51+08:00"
last_task6_review_log: logs/review/2026-06-15-04-review.md
task6_reviewed_date: 2026-06-15
task6_reviewed_by: openclaw-task6
finalized_date: 2026-06-15
finalized_by: openclaw-task6
auto_promoted_date: 2026-06-15
auto_promoted_by: openclaw-task6
---

# 帧率与刷新率

打开 Perfetto 后，应用轨道里可能有一帧标红，Display 轨道的刷新率又恰好从 120 Hz 切到 60 Hz。仅凭这两个现象，不能断定刷新率切换导致了卡顿。红色帧可能来自应用迟交、GPU 迟完成或 BufferQueue 积压；刷新率变化也可能只是内容投票或系统策略的正常结果。

分析帧率问题时，先把三个量分开：

- **应用帧率**：应用向某个 Surface 产出新帧的速率；
- **显示刷新率**：显示设备更新画面的速率；
- **呈现节拍**：连续 display frame 在时间轴上的间隔是否均匀。

平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为基线，以下说明这些量如何进入 Choreographer、LayerHistory、RefreshRateSelector、FrameTimeline 和 HWC。涉及通用 DRM VBlank 边界时，kernel 基线为 `android17-6.18-2026-06_r6`。

## 1. 术语与统计口径

### 1.1 FPS 只说明一段时间内产出了多少帧

FPS（Frames Per Second）是单位时间内生成或呈现的帧数。使用它之前要说明统计对象：

| 写法 | 统计对象 | 适合回答的问题 |
| --- | --- | --- |
| 应用 FPS（App FPS） | 应用提交的 SurfaceFrame | 应用平均生产速度如何 |
| GPU FPS | GPU 完成的应用帧 | GPU 能否持续完成目标负载 |
| 显示 FPS（Present FPS） | 显示端实际呈现的新帧 | 用户看到的新内容更新速度如何 |
| 显示刷新率（Display refresh rate） | 显示扫描或更新频率 | 显示设备当前以什么节拍工作 |

一个应用可以在 120 Hz 显示上稳定输出 60 FPS。显示端通常在两个刷新周期里使用同一应用帧，呈现节拍仍可保持均匀。反过来，应用平均值达到 60 FPS，也可能夹杂长帧簇或长时间停顿。

因此，FPS 适合比较一段稳定区间的吞吐量，不适合单独解释某一帧为什么晚。

### 1.2 刷新周期与目标呈现间隔

固定刷新率下，周期可按下面的公式估算：

```text
refresh period = 1 second / refresh rate

60 Hz  ≈ 16.67 ms
90 Hz  ≈ 11.11 ms
120 Hz ≈  8.33 ms
144 Hz ≈  6.94 ms
```

这些数值描述相邻刷新机会的距离，不等于主线程、RenderThread 和 GPU 必须串行塞进同一个时间片。Android 图形管线允许不同阶段并行处理不同帧。目标帧仍需满足自身的 FrameTimeline deadline，但不能把各线程切片简单相加后与 8.33 ms 比较。

### 1.3 “帧时间（Frame Time）”至少有四种口径

工程讨论中最容易混淆的是帧时间。常见口径如下：

| 口径 | 起点与终点 | 能证明什么 |
| --- | --- | --- |
| `Choreographer#doFrame` duration | 主线程进入到退出该回调 | 主线程本轮 frame callback 的占用时间 |
| RenderThread `DrawFrame` duration | RenderThread 处理该任务的 CPU 区间 | 同步、准备、提交及可能的等待 |
| App SurfaceFrame actual duration | 应用帧起点到 `max(GPU completion, buffer post)` | 应用侧是否按 expected timeline 完成 |
| DisplayFrame actual duration | SurfaceFlinger/display 帧的 actual timeline | 系统合成与显示端是否按计划完成 |

`doFrame` 不包含完整 GPU 和显示阶段；RenderThread CPU 持续时间也不能代替 GPU duration。若文章、指标平台或测试报告只写“Frame Time”，需要先追问它使用了哪一组时间戳。

### 1.4 呈现间隔比平均 FPS更接近视觉节奏

连续新画面的显示间隔（present-to-present）能反映节拍是否均匀。例如，60 FPS 可以是稳定的 16.67 ms，也可能夹杂 8 ms、25 ms、8 ms、25 ms 的交替。

不均匀节拍常见于：

- 内容帧率与显示刷新率没有良好的整数倍关系；
- producer 没有正确 pacing，帧时早时晚；
- 某些帧错过 deadline；
- BufferQueue 中有多帧积压；
- 显示模式或渲染帧率（render rate）在观测区间内变化。

呈现间隔仍不是输入延迟。输入到显示还要加上输入采样、业务处理、GPU、队列和显示阶段。

## 2. 帧率与刷新率怎样匹配

### 2.1 整数倍关系

若显示刷新率是内容帧率的整数倍，每个内容帧可以保持相同数量的显示周期：

| 内容帧率 | 显示刷新率 | 理想节拍（cadence） |
| --- | --- | --- |
| 60 FPS | 120 Hz | 每帧保持 2 个刷新周期 |
| 30 FPS | 120 Hz | 每帧保持 4 个刷新周期 |
| 24 FPS | 120 Hz | 每帧保持 5 个刷新周期 |
| 45 FPS | 90 Hz | 每帧保持 2 个刷新周期 |

整数倍只说明节拍容易均匀，不保证应用按时交帧，也不保证系统一定选择该显示配置。

### 2.2 非整数倍关系

24 FPS 内容放在 60 Hz 显示上，常见做法是 3:2 下拉（pulldown）：有的内容帧保持 3 个刷新周期，有的保持 2 个。内容播放速度可以正确，但帧保持时长交替，平移镜头中容易看到节拍抖动（judder）。

45 FPS 内容若直接映射到 120 Hz，也需要在 2 个和 3 个刷新周期之间安排节拍。设备若同时支持 90 Hz，90 Hz 往往更适合 45 FPS；最终选择仍受其他 Layer、显示策略、seamless 限制和设备能力影响。

### 2.3 没有新帧时显示端会继续使用旧内容

显示设备到达下一刷新机会时，如果目标 Layer 没有可用新缓冲区，系统可以继续显示旧缓冲区。这个行为本身不等于“丢弃了一帧”：

- 应用可能按设计只输出 30 FPS；
- 静态页面没有必要每个 VSync 都重画；
- 视频可能按源帧率工作；
- 应用也可能因为晚交而错过目标帧。

是否属于卡顿，要结合该帧的 expected timeline、actual timeline、显示类型（present type）和业务目标判断。

## 3. MRR、ARR、VRR 与 LTPO

这些词描述不同层级，不能互相替换。

### 3.1 MRR：多个显示配置之间切换

Android 11 为多刷新率（Multiple Refresh Rate，MRR）增加了专门的平台和 Composer HAL 2.4 支持。设备可以暴露多个 display config，例如 1080p@60 Hz 和 1080p@120 Hz。

`CONFIG_GROUP` 用于标识哪些配置适合相互切换。同组通常表示除刷新率外的关键显示属性兼容，平台可以要求无缝切换（seamless switch）。是否能在某个时刻无缝切换仍由 HWC 返回结果决定，不能只凭“分辨率相同”下结论。

MRR 的特征是：选择结果可能要求从一个 display mode 切换到另一个模式。

### 3.2 ARR：单个显示配置内按离散 VSync 步进更新

Android 15 引入 Adaptive Refresh Rate（ARR）。在支持 ARR 的配置中：

- display VSync/TE 节拍与内容实际刷新节拍可以解耦；
- 面板在同一 display mode 内按离散 VSync 步进选择呈现时机；
- 内容刷新率可以取 TE 速率允许的离散除数；
- 减少了仅为改变刷新率而切换 display mode 的需求。

Composer3 的 `DisplayConfiguration.aidl` 与 `VrrConfig.aidl` 描述 `vsyncPeriod`、`minFrameIntervalNs` 等能力。特定 display configuration 的 `vrrConfig` 为空时，它按非 ARR 配置处理。应用不能仅凭设备采用 LTPO 面板就推断 ARR 已启用。

### 3.3 VRR：硬件能力的泛称

可变刷新率（Variable Refresh Rate，VRR）描述显示硬件可以改变刷新节拍的能力。AOSP ARR 代码中也会使用 `vrr` 命名，但硬件市场中的 VRR、Composer3 `VrrConfig` 和 Android 的 ARR 策略不应视为完全相同的概念。

验证 Android ARR 应至少确认：

1. 系统版本与设备实现满足 ARR 要求；
2. `Display.hasArrSupport()` 在 API 36 及以上返回 true；
3. trace 或 dumpsys 显示当前配置和 render rate 确有变化；
4. HWC/vendor 实现按该配置提供相应能力。

### 3.4 LTPO 是面板技术，Android只消费它暴露的能力

LTPO 面板通常有利于较低刷新率和较宽的动态范围，但“LTPO”这个产品名称不能证明：

- 最低一定达到 1 Hz；
- 1 到 120 Hz 之间可以连续取任意值；
- 所有亮度、分辨率、AOD 和温度条件下范围相同；
- Android ARR 已启用；
- 切换一定无感且没有功耗代价。

Android 框架看到的是 HWC 报告的 display configuration、mode group、VSync period 与 ARR 配置。具体面板驱动、TE 和厂商功耗策略需要在目标设备上验证。

## 4. SurfaceFlinger 如何选择 render rate

Android 17 的选择过程不是“找到所有 Layer 帧率的最小公倍数”。系统先收集需求，再在策略允许的候选中评分。

```text
应用/API/内容检测/系统信号
        ↓
LayerHistory：维护活跃 Layer 与投票
        ↓
LayerHistory::summarize()
        ↓
Scheduler::chooseRefreshRateForContent()
        ↓
RefreshRateSelector：过滤候选、评分、排序
        ↓
选定帧率模式 / 需要时切换显示模式
        ↓
更新应用 VSync/render rate 与 HWC 显示配置
```

“应用请求 120 FPS”到“显示最终运行在 120 Hz”之间，还有多个决策层。

### 4.1 LayerHistory 收集哪些信息

Android 17 的 `LayerHistory::summarize()` 会为活跃 Layer 生成 `LayerRequirement`。重要字段包括：

- Layer 名称与所有者 UID；
- vote 类型和期望帧率；
- 帧率类别（frame rate category）；
- 是否要求 seamless；
- Layer 在显示区域中的面积权重；
- Layer 是否 focused；
- 该 Layer 适用于哪个输出显示。

显式 `setFrameRate()` 请求、内容提交节拍的启发式判断、View category、Game Mode 覆盖等信息都会影响投票。不可见或不活跃 Layer 不应与前台主内容等权处理。

### 4.2 Android 17 的九种投票类型

`RefreshRateSelector.h` 中的 `LayerVoteType` 有九种：

| 类型 | 语义 |
| --- | --- |
| `NoVote` | 对帧率没有意见 |
| `Min` | 偏好允许范围内的最低帧率 |
| `Max` | 偏好允许范围内的最高帧率 |
| `Heuristic` | 平台根据内容节拍估算的帧率 |
| `ExplicitDefault` | 应用以 default compatibility 提交具体帧率 |
| `ExplicitExactOrMultiple` | 应用希望精确值或整数倍 |
| `ExplicitExact` | 应用希望精确 render rate |
| `ExplicitGte` | 应用希望至少达到给定帧率 |
| `ExplicitCategory` | 应用提交 LOW、NORMAL、HIGH 等类别 |

这些类型的评分方式不同。比如：

- 整数倍匹配通常得到高分；
- 分数倍对（fractional pair）有专门判断；
- `ExplicitGte` 对大于等于请求值的候选给高分；
- `ExplicitExact` 在支持 content frame-rate override 时可以接受其整数倍候选，再对该 UID 应用 render-rate override；
- category 会先映射到设备配置的范围；
- non-seamless 候选会受到惩罚或直接被某些 Layer 排除。

现行源码中的 `0.95`、`0.8` 等常量属于特定评分分支。它们不是跨版本稳定的公开契约，也不应简化成所有 Layer 通用的固定公式。

### 4.3 policy 与全局信号改变候选范围

候选模式还会受到以下条件约束：

- DisplayManager 设置的 primary/physical/render ranges；
- 当前和默认显示模式组；
- Layer 是否允许 non-seamless 切换；
- 触摸、空闲、显示电源等全局信号；
- 当前是否有显式 Layer vote；
- power-on、多个显示器的 pacesetter/follower 关系；
- 省电、温度和 vendor policy 最终形成的允许范围。

Android 17 代码中，touch 与 idle 都有提前返回的分支，但触发条件受显式投票、category 和策略影响。不能写成“任何触摸都会无条件拉满，停止后固定若干秒降频”。

### 4.4 24 FPS 视频与 60 FPS UI 的例子

假设屏幕上同时有：

- 一个 focused 的 24 FPS 视频 Layer，使用固定源（fixed-source）语义；
- 一个持续更新的 60 FPS UI Layer；
- 候选 render rates 为 60、90、120 Hz。

120 Hz 同时是 24 和 60 的整数倍，通常具有较好的节拍。但以下条件都可能改变结果：

- 120 Hz 不在当前策略范围；
- fixed-source multiple threshold 限制低帧率 Layer 对高档位的贡献；
- 某 Layer 只允许 seamless；
- UI 没有持续更新或面积权重很低；
- 设备处于省电、热限制或其他策略状态；
- 当前显示配置只支持另一组渲染帧率。

源码能说明算法如何评分；具体设备在某一帧选了什么，需要 trace 或 dumpsys 证据。

## 5. 应用怎样表达帧率需求

### 5.1 `Surface.setFrameRate()`

Android 11 / API 30 增加两参数版本，Android 12 / API 31 增加带切换策略的三参数版本。它向系统表达该 Surface 的内容帧率，不会替应用限速，也不会保证系统切换到相同刷新率。

下面的调用用于长时间播放的固定 24 FPS 视频：

```java
surface.setFrameRate(
        24f,
        Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
        Surface.CHANGE_FRAME_RATE_ALWAYS);
```

`FIXED_SOURCE` 适合视频等固有帧率内容。`CHANGE_FRAME_RATE_ALWAYS` 允许 non-seamless 切换，长视频可以在用户接受一次切换中断的前提下使用。短视频、普通 UI 和游戏通常不应照搬这组参数。

游戏或自建渲染器若以 60 FPS 为目标，通常使用默认兼容性（default compatibility），并自行 pacing：

```java
surface.setFrameRate(
        60f,
        Surface.FRAME_RATE_COMPATIBILITY_DEFAULT,
        Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

该调用只提供投票。游戏仍要控制逻辑节拍、GPU 在途帧数量和 presentation time。

### 5.2 `View.setRequestedFrameRate()`

Android 15 / API 35 为 View 增加帧率偏好。可以传正数，也可以传类别：

```java
recyclerView.setRequestedFrameRate(
        View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
progressView.setRequestedFrameRate(60f);
```

请求在该 View 持续 invalidated 时才有意义。调用 ViewGroup 的同名方法不会自动把偏好传给所有子 View。Android 16 / API 36 另有 `ViewGroup.propagateRequestedFrameRate()`，是否强制覆盖子节点由参数决定。

category 由平台和显示配置解释，HIGH 不等于所有设备固定 120 Hz。对于普通 View 动画，category 往往比硬编码某个赫兹值更能适配不同设备。

### 5.3 Window 级功耗与触摸提示

Android 15 / API 35 的 Window API 包括：

- `setFrameRatePowerSavingsBalanced(boolean)`；
- `setFrameRateBoostOnTouchEnabled(boolean)`。

前者允许系统在该窗口上更积极地平衡帧率与功耗；后者控制窗口是否参与 touch boost。它们没有承诺某个固定刷新率、持续时间或功耗比例。

### 5.4 查询 ARR 与设备建议值

Android 16 / API 36 提供：

- `Display.hasArrSupport()`；
- `Display.getSuggestedFrameRate(FRAME_RATE_CATEGORY_NORMAL/HIGH)`。

应用可先查询设备建议，再把结果用于 Surface 或渲染循环。`getSuggestedFrameRate()` 返回设备定义的建议值，不是当前显示刷新率，也不是应用必须达到的 SLA。

Android 17 / API 37 的 `Display.getFrameRateVelocityMapping()` 暴露滚动速度到建议帧率的配置点，View 滚动组件可以随速度降低逐步降低请求值。映射与 Display 相关，不能在应用里假设固定阈值。

### 5.5 `SurfaceControl.Transaction.setFrameTimeline()`

Android 13 / API 33 的 `Choreographer.FrameData` 可以提供多个候选 timeline。公开的 `SurfaceControl.Transaction.setFrameTimeline(long vsyncId)` 在 Android 15 / API 35 加入 SDK：

```java
Choreographer.getInstance().postVsyncCallback(frameData -> {
    Choreographer.FrameTimeline timeline =
            frameData.getPreferredFrameTimeline();

    transaction.setFrameTimeline(timeline.getVsyncId());
    transaction.apply();
});
```

选择某个 vsyncId 只是告诉 SurfaceFlinger 期望的 presentation target；acquire fence、事务顺序和 deadline 仍需满足。普通 View/HWUI 窗口由框架维护 timeline，业务代码通常不需要自行设置。

### 5.6 `preferredDisplayModeId` 的使用边界

`WindowManager.LayoutParams.preferredDisplayModeId` 指定包含分辨率、刷新率等属性的 display mode。它比帧率提示更容易触发模式变化，适合明确知道目标模式且能处理切换影响的场景，例如部分电视播放。

只需要表达内容帧率时，优先使用 Surface/View 的帧率 API，让系统结合其他 Layer 和策略选择。

## 6. Choreographer 与 Frame Pacing

### 6.1 Choreographer 合并待处理帧请求

普通 View 窗口由 `ViewRootImpl` 和 `Choreographer` 对齐应用 VSync。Android 17 的 `mFrameScheduled` 用来合并尚未处理的 frame request，`doFrame()` 按以下顺序执行回调：

```text
INPUT
ANIMATION
INSETS_ANIMATION
TRAVERSAL
COMMIT
```

同一轮多次 `invalidate()` 通常汇入一个 pending frame。没有更新需求时，应用也不必在每个显示 VSync 执行一次完整 `doFrame()`。

因此，用相邻 `doFrame` 的起点间隔统计“显示 FPS”并不可靠：

- 静态窗口可能没有对应回调；
- callback 起点会受主线程调度影响；
- SurfaceView、视频或游戏主体可能由另一 producer 出帧；
- callback 完成后仍有 RenderThread、GPU、BufferQueue 和显示阶段。

`doFrame` 适合观察主线程帧调度，呈现结果应看 FrameTimeline 或显示侧时间戳。

### 6.2 FrameData 提供多个候选 timeline

API 33 及以上的 `Choreographer.VsyncCallback` 接收 `FrameData`。每个 `FrameTimeline` 包含：

- `vsyncId`；
- 预期呈现时间；
- 截止时间。

`getPreferredFrameTimeline()` 是平台建议值。自建 SurfaceControl 事务可以选另一个可满足的 timeline，再通过 API 35 的 `setFrameTimeline()` 提交。选择更晚 timeline 会改变目标呈现时机，但不能减少渲染工作本身。

### 6.3 Frame pacing 控制的是 cadence 和队列深度

Frame pacing 的目标包括：

- 让内容帧在正确的显示机会呈现；
- 避免短帧和长帧造成不均匀 cadence；
- 限制在途帧，减少队列堆积；
- 在允许的显示配置中表达合适帧率。

“每次收到 VSync 就立即渲染”只覆盖起帧节奏。若 producer 总是尽快提交，BufferQueue 可能积压，输入延迟仍会升高。

### 6.4 Swappy 适合游戏与自建渲染循环

AGDK Frame Pacing Library（Frame Pacing Library，Swappy）支持 OpenGL ES 和 Vulkan 游戏。它结合：

- Choreographer 时序；
- 呈现时间戳；
- EGL/Vulkan 同步对象；
- 交换间隔与管线模式；
- 多刷新率设备的 frame-rate hint。

Swappy 可以主动等待以限制队列深度。Trace 中看到交换或 fence wait 时，要先判断它是合理 pacing、GPU 依赖还是被动背压，不能一律当成性能浪费。

### 6.5 Buffer stuffing 会维持吞吐量却增加延迟

producer 连续提交速度高于显示消费速度时，多个缓冲区可能在队列中等待。表现可能是：

- FPS 看起来稳定；
- 帧总是比 expected timeline 晚一个或多个周期；
- 输入到显示的延迟增加；
- 生产者最终卡在出队、交换或显示提交；
- FrameTimeline 标记 `Buffer Stuffing`。

Android 17 的 Choreographer/HWUI 还包含 buffer stuffing recovery。看到 recovery trace 时，应同时检查队列深度、主动延迟和后续积压是否回落。

### 6.6 Android 17 的 producer throttling

API 37 增加 `Surface.setProducerThrottlingEnabled(boolean)`，用于控制 Vulkan/EGL 生产者的 CPU throttling。默认机制会在 consumer 仍处理前一缓冲区时给 producer 施加背压。

这个 API 不负责选择刷新率，也不能代替 frame pacing。官方建议 Vulkan 生产者在具备正确显式同步时关闭默认节流，避免把 `vkPresentKHR()` 的 CPU 停顿当成 producer/consumer 同步；队列耗尽时的自然出队背压仍会发生。异步模式下节流始终启用，此开关没有效果。

## 7. 卡顿、迟到、丢帧与错过目标帧

这些词在口语中经常混用，诊断时要回到工具字段。

### 7.1 FrameTimeline 的两类帧

FrameTimeline 同时描述：

- **SurfaceFrame**：某个 Layer/Surface 的应用帧；
- **DisplayFrame**：SurfaceFlinger 把多个 SurfaceFrame 组合成的一次显示帧。

两者 token 不同：

- `surface_frame_token` 关联应用 producer；
- `display_frame_token` 关联系统显示帧。

一个 DisplayFrame 可以包含多个进程、多个 Layer 的 SurfaceFrame。不能把两种标识合成一个“端到端帧号”。

### 7.2 预期时间线与实际时间线

预期时间线（Expected timeline）表示调度器给该帧的预期时间窗口，实际时间线（Actual timeline）表示该帧的实际执行/呈现结果。

对应用 SurfaceFrame，actual end 覆盖应用提交和 GPU 完成边界；对 SurfaceFlinger DisplayFrame，actual timeline覆盖系统合成与显示呈现。应用 actual 按时，只能证明 producer 侧达标，不能证明 DisplayFrame 一定按时。

### 7.3 当前 Perfetto 文档中的颜色

| 颜色 | 常见含义 |
| --- | --- |
| 绿色 | 没有检测到 jank |
| 红色 | 当前进程被归因为 jank 来源 |
| 黄色 | 应用帧异常，但原因归到 SurfaceFlinger |
| 蓝色 | 丢帧（dropped frame） |
| 浅绿色 | 高延迟状态（high-latency state），节拍可能稳定但整体呈现偏晚 |

颜色是 UI 辅助。结论应读取 `jank_type`、`present_type`、`on_time_finish`、Layer 名称和对应流程。

### 7.4 Janky 不等于“duration 大于一个刷新周期”

帧 deadline 由当前调度和 timeline 决定。以下情况都可能产生不同分类：

- 应用完成晚，错过自己的 deadline；
- 应用按时，SurfaceFlinger CPU 或 GPU 合成晚；
- DisplayHAL 没按目标 VSync 呈现；
- 预测误差；
- buffer stuffing 导致稳定但高延迟；
- 一帧被更新的帧替代；
- UI 状态没有及时同步到 RenderThread。

固定拿 16.67 ms 或 8.33 ms 与任意切片比较，会在高刷、ARR、pipeline overlap 和调度相位场景中误判。

### 7.5 Missed 与丢帧要描述具体对象

“错过目标帧（missed frame）”可以表示错过目标 deadline，也可以泛指显示端没有更新新内容。“丢帧（dropped frame）”在 FrameTimeline 有具体分类：SurfaceFlinger 可能选择更新的帧，应用侧也可能没有及时把 UI 状态推给 RenderThread。

不要写“所有 missed 都属于卡顿”这类集合关系。可操作的表述是：

- 哪一个 SurfaceFrame；
- 它的预期与实际时间线是什么；
- 是否关联到 DisplayFrame；
- `present_type` 与 `jank_type` 是什么；
- 旧帧被重复、目标帧晚呈现，还是该帧没有进入最终显示。

## 8. 测量工具的正确边界

### 8.1 FrameMetrics

`FrameMetrics` 从 API 24 起提供窗口帧分段指标。常用字段包括：

| 字段 | 语义 |
| --- | --- |
| `TOTAL_DURATION` | 帧从开始到渲染完成并 issued to display subsystem 的总时长 |
| `DEADLINE` | 系统分配给应用生产该帧的时间，API 31+ |
| `GPU_DURATION` | 该应用帧的 GPU 完成时间，API 31+ |
| `LAYOUT_MEASURE_DURATION` | 失效 View 层级的 measure/layout 时间 |
| `DRAW_DURATION` | draw callback 阶段 |
| `SYNC_DURATION` | DisplayList 与 RenderThread 同步时间 |
| `COMMAND_ISSUE_DURATION` | 向 GPU 发出绘制命令的时间 |
| `SWAP_BUFFERS_DURATION` | 向显示子系统提交 framebuffer 的时间 |
| `INTENDED_VSYNC_TIMESTAMP` / `VSYNC_TIMESTAMP` | 预期与实际应用 VSync 时间 |

API 31 及以上可用 `TOTAL_DURATION < DEADLINE` 判断应用是否满足其生产 deadline。`TOTAL_DURATION` 不是屏幕呈现时间，各阶段还可能并行，因此它不一定等于所有 duration 字段之和。

监听回调可能因处理线程繁忙而丢失中间通知，`dropCountSinceLastInvocation` 表达的是 listener 通知丢失数量，不是屏幕掉帧数量。

### 8.2 JankStats

JankStats 为不同 API 级别封装 frame timing 并附加 UI 状态。默认启发式倍数（heuristic multiplier）为 2，但这是库的报告阈值，不是系统 FrameTimeline 的卡顿定义。

用于线上监控时，应记录：

- JankStats/metrics library 版本；
- 设备 API、刷新率和窗口状态；
- `frameDurationUiNanos` 等实际字段；
- 页面、交互和业务状态；
- 采样、聚合与上报规则。

不要把 JankStats、FrameMetrics 和 FrameTimeline 的“jank count”直接合并，它们的覆盖面与判定口径不同。

### 8.3 `dumpsys gfxinfo`

`adb shell dumpsys gfxinfo <package>` 适合快速查看 View/HWUI 窗口的帧统计和分位数。它不覆盖所有自建 Surface、视频、Camera、游戏或外部 compositor 路径。

分位数比平均值更有用，但仍要结合场景持续时间和样本量。没有统一的“jank 超过 5% 就一定可感知”阈值，刷新率、交互类型和长帧聚集方式都会改变体验。

### 8.4 Perfetto FrameTimeline

先用下面的查询列出目标进程的实际 SurfaceFrame，不要用 `doFrame` 数量代替帧数：

```sql
SELECT
  a.ts,
  a.dur,
  a.surface_frame_token,
  a.display_frame_token,
  a.jank_type,
  a.present_type,
  a.on_time_finish,
  a.layer_name
FROM actual_frame_timeline_slice AS a
JOIN process AS p USING (upid)
WHERE p.name = 'com.example.app'
ORDER BY a.ts;
```

查询结果先按 `layer_name` 区分 App Window、SurfaceView、视频或其他 Surface。再用 token 和流程找到对应 expected frame 与 SurfaceFlinger DisplayFrame。表结构可能随 Perfetto 版本演进，执行前应查看当前 trace processor schema。

## 9. 一套可重复的诊断顺序

### 第一步：记录测试条件

至少记录：

- 设备、系统构建、分辨率和 display mode；
- 当前 physical refresh、render rate 与 ARR 支持；
- App 目标 FPS 与调用的帧率 API；
- Surface 类型和 Layer 名称；
- 电量模式、游戏模式（Game Mode）、温度、亮度和充电状态；
- 测试动作、持续时间和 trace config。

刷新率和热状态不同的两次跟踪不适合直接比较帧预算。

### 第二步：锁定目标 SurfaceFrame

在 FrameTimeline 选择异常帧，确认：

- 进程和 Layer 名称；
- surface/display token；
- 预期与实际时间线；
- `jank_type`、`present_type` 和 `on_time_finish`；
- flow 指向哪个 DisplayFrame。

若主体是 SurfaceView、视频或游戏 Surface，应跟踪它自己的 Layer，不能只看宿主 App Window。

### 第三步：判断应用是否晚

沿同一帧检查：

- `Choreographer#doFrame` 是否晚启动；
- INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT；
- RenderThread `DrawFrame`；
- GPU 提交与完成时间；
- 出队/入队和生产者栅栏；
- App SurfaceFrame actual end。

主线程短不代表应用帧按时，RenderThread 切片长也不等于 GPU 一直忙。

### 第四步：判断队列是否积压

检查：

- `dequeueBuffer` 是否等待；
- 队列深度与释放栅栏；
- `BufferTX - <layerName>`；
- BLAST transaction 与 SurfaceFlinger latch；
- `Buffer Stuffing` 分类与 recovery trace；
- present-to-present 间隔和输入延迟。

稳定 FPS 加上稳定的晚呈现，往往比偶发长帧更像队列延迟问题。

### 第五步：判断系统显示阶段是否晚

检查：

- SurfaceFlinger actual timeline；
- HWC validate/present；
- CLIENT/DEVICE composition；
- DisplayHAL jank；
- 显示栅栏；
- display mode 或 render rate 是否在该帧附近改变。

若应用 SurfaceFrame 按时、DisplayFrame 迟到，问题范围才进入 SurfaceFlinger、HWC 或显示端。

### 第六步：解释刷新率选择

需要把以下证据放在一起：

- 当前显示策略范围；
- 活动显示模式/模式组；
- Layer 投票与期望帧率；
- touch/idle/power 信号；
- MRR 模式切换或 ARR 渲染帧率变化；
- 选定的模式/帧率；
- 切换前后的预期时间线。

只看到刷新率轨道变化，不能说明是哪一个 Layer 请求，也不能说明它导致了当前 jank。

## 10. 常见误判

| 误判 | 更可靠的检查 |
| --- | --- |
| 相邻 `doFrame` 间隔 33 ms，所以屏幕掉了一帧 | 查看目标 SurfaceFrame 与 DisplayFrame；静态窗口本就可能没有回调 |
| 120 Hz 下每个线程都必须在 8.33 ms 内结束 | 以目标帧 deadline 和跨线程依赖为准，保留 pipeline overlap |
| 60 FPS 在 120 Hz 一定浪费一半 GPU | 应用只需生产 60 帧；显示重复不要求 GPU 重画同一帧 |
| 高刷新率一定更流畅 | 检查应用是否按时、cadence、输入延迟和队列深度 |
| LTPO 等于 Android ARR | 查询 `hasArrSupport()`、HWC 配置和 trace |
| 1–120 Hz LTPO 可以取任意连续值 | 查看设备报告的离散能力和限制条件 |
| `setFrameRate(120)` 会把屏幕锁到 120 Hz | 它是 Layer vote，最终受策略、其他 Layer 和设备能力影响 |
| `Display.getRefreshRate()` 不等于请求值，所以发生覆盖 | 可能是正常选模、policy、其他 Layer 或 ARR；需要系统侧证据 |
| Game Mode PERFORMANCE 会锁高频 | Game Mode 表达用户选择，游戏和 OEM 干预共同决定策略 |
| FrameMetrics `TOTAL_DURATION` 是触摸到屏幕延迟 | 它到 issued-to-display-subsystem 为止，不包含完整输入与面板边界 |
| `DrawFrame` 很长就说明 GPU 慢 | 区分 CPU 工作、dequeue/fence wait、GPU completion |
| 平均 FPS 达标就没有卡顿 | 同时看分位数、长帧簇、present interval 和 high-latency state |

## 11. Game Mode 与 120 Hz 功耗

### 11.1 Game Mode 是协作接口

Game Mode API 在部分 Android 12 设备提供，Android 13 及以上设备支持更完整。`PERFORMANCE` 与 `BATTERY` 让游戏针对低延迟/帧率或续航调整自身策略。

它没有承诺：

- 固定 CPU/GPU 频率；
- 固定 120 Hz；
- OEM 一定采用相同干预；
- 切到 PERFORMANCE 后 FPS 一定提高。

游戏应在 `onResume()` 查询当前模式，并根据自身能力选择分辨率、画质、目标 FPS 和 pacing。测试时还要记录 OEM 干预是否生效。

### 11.2 高刷新率功耗不能套固定百分比

从 60 Hz 提升到 120 Hz 可能增加：

- 面板与显示控制器更新次数；
- SurfaceFlinger/HWC 活动；
- 应用 CPU/GPU 出帧频率；
- 内存带宽与 buffer 周转；
- 高性能状态驻留时间。

增长幅度受面板、亮度、内容、合成方式、SoC 和应用是否真的提高帧率影响。没有目标设备测量时，不应给出固定百分比。

### 11.3 选择稳定目标比追逐峰值更重要

一个游戏若只能在 120 FPS 与 80 FPS 之间持续波动，稳定 90 FPS 或 60 FPS 可能提供更均匀的 cadence、更低的队列压力和更好的持续性能。判断目标值时同时看：

- CPU/GPU 帧时间分布；
- 1% low 与长帧簇；
- 温升后的稳态性能；
- 输入到显示延迟；
- 功耗和表面温度；
- 设备支持的 render rates。

Swappy 或引擎 pacing 应根据这些数据选择 swap interval，而不是在每帧临时追随瞬时耗时。

## 12. Kernel 与厂商显示边界

Framework 的 RefreshRateSelector 负责投票与策略，Composer HAL 把所选配置或显示时机交给设备实现。再往下可能涉及 vendor display driver、面板 TE、DRM/KMS VBlank、时钟和电源管理。

在 `android17-6.18-2026-06_r6` 中，`drivers/gpu/drm/drm_vblank.c` 与 `include/drm/drm_vblank.h` 提供通用 DRM VBlank 计数、事件和时间戳机制。但要注意：

- Android 设备不保证都用相同 DRM 驱动路径；
- Android 通用内核不包含所有厂商面板与显示控制器实现；
- framework 的 render-rate 选择不能从通用 vblank 源码反推；
- 面板的最低刷新率、TE 与无缝切换能力必须查设备配置和 vendor trace。

当问题已经定位到 HWC 之后，可继续收集：

- Composer HAL 调用与返回；
- 显示模式/刷新回调；
- 厂商显示跟踪点；
- DRM vblank/page-flip 事件（设备支持时）；
- 显示栅栏；
- 面板或外接显示器的硬件测量。

## 13. 版本演进到 Android 17

| 版本 | 帧率与刷新率边界 |
| --- | --- |
| Android 4.1 / API 16 | Java `Choreographer` 建立应用 VSync 帧调度基线 |
| Android 11 / API 30 | 平台正式支持 MRR、Composer HAL 2.4、config group；`Surface.setFrameRate(float, int)` 公开 |
| Android 12 / API 31 | 三参数 `Surface.setFrameRate()`；FrameTimeline 可用于 Perfetto；FrameMetrics 增加 `DEADLINE`、`GPU_DURATION` |
| Android 13 / API 33 | `Choreographer.FrameData` / `FrameTimeline` 公开多个候选 timeline |
| Android 15 / API 35 | ARR 平台能力；View/Window 帧率提示；公开 `SurfaceControl.Transaction.setFrameTimeline()` |
| Android 16 / API 36 | `Display.hasArrSupport()`、`getSuggestedFrameRate()`；ViewGroup 帧率请求传播 API |
| Android 17 / API 37 | `Display.getFrameRateVelocityMapping()`；`Surface` producer throttling 控制；RefreshRateSelector 现行九类投票与 ARR/MRR 分支按 `android-17.0.0_r1` 解读 |

当前源码能证明 Android 17 的实现状态，不能自动证明某段逻辑是 Android 17 首次加入。涉及“从某版本开始”的结论，应同时检查 API level、旧标签或官方版本说明。

## 14. Android 17 源码索引

### 应用 API 与帧时序

- `frameworks/base/core/java/android/view/Choreographer.java`
- `frameworks/base/core/java/android/view/DisplayEventReceiver.java`
- `frameworks/base/core/java/android/view/Display.java`
- `frameworks/base/core/java/android/view/View.java`
- `frameworks/base/core/java/android/view/ViewGroup.java`
- `frameworks/base/core/java/android/view/Window.java`
- `frameworks/base/core/java/android/view/Surface.java`
- `frameworks/base/core/java/android/view/SurfaceControl.java`
- `frameworks/base/core/java/android/view/FrameMetrics.java`

### SurfaceFlinger 调度

- `frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.h`
- `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp`
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`

### ARR 与内核边界

- `hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl`
- `hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl`
- `drivers/gpu/drm/drm_vblank.c`
- `include/drm/drm_vblank.h`

## Android 17 的帧率协作边界

帧率评估需要检查生产者、SurfaceFlinger 和显示设备能否以一致的目标节拍协作：

1. FPS 是吞吐量，present interval 描述视觉节拍，input-to-present 描述交互延迟；
2. `doFrame`、RenderThread、SurfaceFrame 和 DisplayFrame 各有不同的 frame-time 口径；
3. MRR 在 display mode 之间切换，ARR 在支持的配置内按离散 VSync 步进改变刷新节拍，LTPO 只是可能提供这些能力的面板技术；
4. Android 17 通过 LayerHistory 汇总 Layer vote，再由 RefreshRateSelector 在策略允许的候选中评分；
5. Surface、View、Window 和 SurfaceControl API 都是提示或目标表达，不能代替应用自身 pacing；
6. Jank 结论应来自目标 SurfaceFrame、DisplayFrame、token、deadline、fence 和显示证据；
7. 平均 FPS、单条 `doFrame`、单次刷新率切换都不足以独立解释卡顿。

排查时先锁定目标 Surface 和 FrameTimeline，再判断应用、队列、SurfaceFlinger 与显示端谁先错过时序。刷新率变化需要放回 Layer vote、display policy 与选模结果中解释。
