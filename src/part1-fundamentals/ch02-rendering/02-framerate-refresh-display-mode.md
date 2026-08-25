---
title: 帧率、刷新率与显示模式选择
chapter: '2.2'
section: '2.2'
status: finalized
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: '2026-08-24'
last_verified_against: 'AOSP android-17.0.0_r1: Choreographer/Display/View/ViewGroup/Window/Surface/SurfaceControl/FrameMetrics, SurfaceFlinger RefreshRateSelector/LayerHistory/Scheduler/FrameTimeline; Composer3 ARR AIDL; kernel android17-6.18-2026-06_r6 DRM vblank boundary; Writer rendering_pipelines S01/S02/S13'
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
- type: official
  path: https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
- type: official
  path: https://developer.android.com/reference/android/view/View
- type: official
  path: https://developer.android.com/reference/android/view/Surface
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer.FrameData
- type: research
  path: intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/DisplayInfo.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Window.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/display/mode/DisplayModeDirector.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/VsyncModulator.cpp
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/IComposerClient.aidl
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/metrics/sql/android/jank/frames.sql
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/diagrams/S01_baseline_12_anchor_pipeline/source.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S08_native_graphics_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayCommand.aidl
- type: aosp
  path: https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/ActiveConfigCommand.aidl
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_atomic_helper.c
- type: official-doc
  path: https://source.android.com/docs/core/graphics/multiple-refresh-rate
- type: official-doc
  path: https://source.android.com/docs/core/graphics/arr
- type: official-doc
  path: https://developer.android.com/media/optimize/performance/frame-rate
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: aosp
  path: frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/Display/DisplayModeController.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/Display/DisplayModeRequest.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameRateCompatibility.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameRateOverrideMappings.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/include/scheduler/FrameRateMode.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/DisplayHardware/DisplayMode.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/VSyncReactor.cpp
- type: aosp
  path: frameworks/native/libs/nativewindow/include/android/native_window.h
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
- VSync
- Choreographer
- Android-17
- frame-rate
- setFrameRate
- rendering
- display-mode
- surfaceflinger
- frame-rate-override
- android17
- hwc
- vrr
related_chapters:
- '2.1'
- '2.3'
- '2.9'
- '7.1'
- '2.8'
- '2.12'
- '22.13'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch02-rendering/02-framerate.md
- src/part1-fundamentals/ch02-rendering/18-adaptive-refresh-rate.md
- src/part1-fundamentals/ch02-rendering/19-refresh-rate-switching.md
- src/part1-fundamentals/ch02-rendering/34-display-mode-refresh-rate-selection.md
- src/part2-performance/ch13-rendering-pipelines/13-variable-refresh-rate.md
---

# 帧率、刷新率与显示模式选择

打开 Perfetto 后，应用轨道里可能有一帧标红，Display 轨道的刷新率又恰好从 120 Hz 切到 60 Hz。仅凭这两个现象，不能断定刷新率切换导致了卡顿。红色帧可能来自应用迟交、GPU 迟完成或 BufferQueue 积压；刷新率变化也可能只是内容投票，或系统 policy（结合功耗、温度和硬件能力形成的选择范围）的正常结果。

分析帧率问题时，先把三个量分开：

- **应用帧率**：应用向某个 Surface 产出新帧的速率；
- **显示刷新率**：显示设备更新画面的速率；
- **呈现节拍**：连续 display frame 在时间轴上的间隔是否均匀。

平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为基线，以下说明这些量如何进入 Choreographer、LayerHistory、RefreshRateSelector、FrameTimeline 和 HWC。涉及 Linux 显示子系统 DRM/KMS（Direct Rendering Manager / Kernel Mode Setting）与垂直消隐事件 VBlank 的通用边界时，kernel 基线为 `android17-6.18-2026-06_r6`。

应用帧率、显示刷新率和物理显示模式是三个不同变量。系统先收集内容需求和设备约束，再选择模式并安排切换；掉帧、抖动与功耗问题需要分别检查帧生产、模式评分和切换时序。

## 帧率、刷新率与截止时间

### 1. 术语与统计口径

#### 1.1 FPS 只说明一段时间内产出了多少帧

FPS（Frames Per Second）是单位时间内生成或呈现的帧数。使用它之前要说明统计对象：

| 写法 | 统计对象 | 适合回答的问题 |
| --- | --- | --- |
| App FPS | 应用提交的 SurfaceFrame | 应用平均生产速度如何 |
| GPU FPS | GPU 完成的应用帧 | GPU 能否持续完成目标负载 |
| 显示 FPS（Present FPS） | 显示端实际呈现的新帧 | 用户看到的新内容更新速度如何 |
| 显示刷新率（Display refresh rate） | 显示扫描或更新频率 | 显示设备当前以什么节拍工作 |

一个应用可以在 120 Hz 显示上稳定输出 60 FPS。显示端通常在两个刷新周期里使用同一应用帧，呈现节拍仍可保持均匀。反过来，应用平均值达到 60 FPS，也可能夹杂长帧簇或长时间停顿。

因此，FPS 适合比较一段稳定区间的吞吐量，不适合单独解释某一帧为什么晚。

#### 1.2 刷新周期与目标呈现间隔

固定刷新率下，周期可按下面的公式估算：

```text
refresh period = 1 second / refresh rate

60 Hz  ≈ 16.67 ms
90 Hz  ≈ 11.11 ms
120 Hz ≈  8.33 ms
144 Hz ≈  6.94 ms
```

这些数值描述相邻刷新机会的距离，不等于主线程、RenderThread 和 GPU 必须串行塞进同一个时间片。Android 图形管线允许不同阶段并行处理不同帧。目标帧仍需满足自身的 FrameTimeline deadline（截止时间），但不能把各线程的 Perfetto slice（带起止时间的事件区间）简单相加后与 8.33 ms 比较。

#### 1.3 “帧时间（Frame Time）”至少有四种口径

工程讨论中最容易混淆的是帧时间。FrameTimeline 把某个 Surface 产出的应用帧记为 SurfaceFrame，把 SurfaceFlinger 组织的一次显示帧记为 DisplayFrame；expected 表示系统计划的时间线，actual 表示实际结果。常见口径如下：

| 口径 | 起点与终点 | 能证明什么 |
| --- | --- | --- |
| `Choreographer#doFrame` duration | 主线程进入到退出该回调 | 主线程本轮 frame callback 的占用时间 |
| RenderThread `DrawFrame` duration | RenderThread 处理该任务的 CPU 区间 | 同步、准备、提交及可能的等待 |
| App SurfaceFrame actual duration | 应用帧起点到 `max(GPU completion, buffer post)` | 应用侧是否按 expected timeline 完成 |
| DisplayFrame actual duration | SurfaceFlinger/display 帧的 actual timeline | 系统合成与显示端是否按计划完成 |

`doFrame` 不包含完整 GPU 和显示阶段；RenderThread CPU duration 也不能代替 GPU duration。若文章、指标平台或测试报告只写“Frame Time”，需要先追问它使用了哪一组时间戳。

#### 1.4 呈现间隔比平均 FPS更接近视觉节奏

连续新画面的 present-to-present 间隔能反映节拍是否均匀。例如，60 FPS 可以是稳定的 16.67 ms，也可能夹杂 8 ms、25 ms、8 ms、25 ms 的交替。

不均匀节拍常见于：

- 内容帧率与显示刷新率没有良好的整数倍关系；
- Producer 没有正确进行 frame pacing（主动对齐帧的生成与提交节奏），帧时早时晚；
- 某些帧错过 deadline；
- BufferQueue 中有多帧积压；
- 显示模式或渲染帧率（render rate）在观测区间内变化。

呈现间隔仍不是输入延迟。input-to-present 指从输入事件产生到对应画面呈现的总时间，还要计入输入采样、业务处理、GPU、队列和显示阶段。

### 2. 帧率与刷新率怎样匹配

#### 2.1 整数倍关系

若显示刷新率是内容帧率的整数倍，每个内容帧可以保持相同数量的显示周期：

| 内容帧率 | 显示刷新率 | 理想节拍（cadence） |
| --- | --- | --- |
| 60 FPS | 120 Hz | 每帧保持 2 个刷新周期 |
| 30 FPS | 120 Hz | 每帧保持 4 个刷新周期 |
| 24 FPS | 120 Hz | 每帧保持 5 个刷新周期 |
| 45 FPS | 90 Hz | 每帧保持 2 个刷新周期 |

整数倍只说明 cadence（内容帧在各刷新周期中的重复规律）容易均匀，不保证应用按时交帧，也不保证系统一定选择该显示配置。

#### 非整数倍关系

24 FPS 内容放在 60 Hz 显示上，常见做法是 3:2 下拉（pulldown）：有的内容帧保持 3 个刷新周期，有的保持 2 个。内容播放速度可以正确，但帧保持时长交替，平移镜头中容易看到节拍抖动（judder）。

45 FPS 内容若直接映射到 120 Hz，也需要在 2 个和 3 个刷新周期之间安排 cadence。设备若同时支持 90 Hz，90 Hz 往往更适合 45 FPS；最终选择仍受其他 Layer、显示 policy、seamless（切换时不出现明显黑屏或闪烁）限制和设备能力影响。

#### 2.3 没有新帧时显示端会继续使用旧内容

显示设备到达下一刷新机会时，如果目标 Layer 没有可用新缓冲区，系统可以继续显示旧缓冲区。这个行为本身不等于“丢弃了一帧”：

- 应用可能按设计只输出 30 FPS；
- 静态页面没有必要每个 VSync 都重画；
- 视频可能按源帧率工作；
- 应用也可能因为晚交而错过目标帧。

是否属于 jank（时序异常帧），要结合该帧的 expected timeline、actual timeline、呈现类型（present type）和业务目标判断。

### 3. MRR、ARR、VRR 与 LTPO

这些词描述不同层级，不能互相替换。

#### 3.1 MRR：多个显示配置之间切换

Android 11 为多刷新率（Multiple Refresh Rate，MRR）增加了专门的平台和 Composer HAL 2.4 支持。设备可以暴露多个 display config（包含分辨率、刷新率等参数的显示配置），例如 1080p@60 Hz 和 1080p@120 Hz。

`CONFIG_GROUP` 用于标识哪些配置适合相互切换。同组通常表示除刷新率外的关键显示属性兼容，平台可以要求 seamless switch（无明显画面中断的切换）。是否能在某个时刻无缝切换仍由 HWC 返回结果决定，不能只凭“分辨率相同”下结论。

MRR 的特征是：选择结果可能要求从一个 display mode 切换到另一个 mode。

#### 3.2 ARR：单个显示配置内按离散 VSync 步进更新

Android 15 引入 Adaptive Refresh Rate（ARR）。在支持 ARR 的配置中：

- display VSync/TE 节拍与内容实际刷新节拍可以解耦；TE（Tearing Effect）是面板给出的扫描时序信号；
- 面板在同一 display mode 内按离散 VSync 步进选择呈现时机；
- 内容刷新率可以取 TE 速率允许的离散除数；
- 减少了仅为改变刷新率而切换 display mode 的需求。

Composer3 的 `DisplayConfiguration.aidl` 与 `VrrConfig.aidl` 描述 `vsyncPeriod`、`minFrameIntervalNs` 等能力。特定 display configuration 的 `vrrConfig` 为空时，它按非 ARR 配置处理。应用不能仅凭设备采用 LTPO 面板就推断 ARR 已启用。

#### 3.3 VRR：硬件能力的泛称

可变刷新率（Variable Refresh Rate，VRR）描述显示硬件可以改变刷新节拍的能力。AOSP ARR 代码中也会使用 `vrr` 命名，但硬件市场中的 VRR、Composer3 `VrrConfig` 和 Android 的 ARR policy 不应视为完全相同的概念。

验证 Android ARR 应至少确认：

1. 系统版本与设备实现满足 ARR 要求；
2. `Display.hasArrSupport()` 在 API 36 及以上返回 true；
3. trace 或 dumpsys 显示当前配置和 render rate 确有变化；
4. HWC/vendor 实现按该配置提供相应能力。

#### 3.4 LTPO 是面板技术，Android 只使用它暴露的能力

LTPO（Low-Temperature Polycrystalline Oxide）是显示面板的背板技术，通常有利于实现较低刷新率和较宽的动态范围，但“LTPO”这个产品名称不能证明：

- 最低一定达到 1 Hz；
- 1 到 120 Hz 之间可以连续取任意值；
- 所有亮度、分辨率、AOD（Always-On Display，息屏显示）和温度条件下范围相同；
- Android ARR 已启用；
- 切换一定无感且没有功耗代价。

Android framework 看到的是 HWC 报告的 display configuration、mode group、VSync period 与 ARR 配置。具体面板驱动、TE 和厂商功耗策略需要在目标设备上验证。

### 4. SurfaceFlinger 如何选择 render rate

这里的 render rate 是系统为内容生产与应用 VSync 安排的目标节拍，它可以与当前显示配置的 physical refresh（物理刷新基准）不同。Layer vote 是每个 Layer 提交的需求或偏好，display policy 则限定系统当前允许选择的 mode 与帧率范围。

Android 17 的选择过程不是“找到所有 Layer 帧率的最小公倍数”。系统先收集 vote，再在 policy 允许的候选中评分。

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
选定 FrameRateMode / 需要时切换 display mode
        ↓
更新应用 VSync/render rate 与 HWC 显示配置
```

“应用请求 120 FPS”到“显示最终运行在 120 Hz”之间，还有多个决策层。

#### 4.1 LayerHistory 收集哪些信息

Android 17 的 `LayerHistory::summarize()` 会为活跃 Layer 生成 `LayerRequirement`。重要字段包括：

- Layer 名称与 owner UID（Android 为应用沙箱分配的 Linux 用户标识）；
- vote 类型和期望帧率；
- 帧率类别（frame rate category）；
- 是否要求 seamless；
- Layer 在显示区域中的面积权重；
- Layer 是否 focused；
- 该 Layer 适用于哪个输出显示。

显式 `setFrameRate()` 请求、根据内容提交节拍作出的启发式判断、View category、Game Mode override（系统或厂商对应用帧率作出的覆盖设置）等信息都会影响投票。不可见或不活跃 Layer 不应与前台主内容等权处理。

#### 4.2 Android 17 的九种投票类型

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
| `ExplicitCategory` | 应用提交 LOW、NORMAL、HIGH 等 category |

这些类型的评分方式不同。比如：

- 整数倍匹配通常得到高分；
- 分数倍对（fractional pair，例如 24 FPS 内容与 60 Hz 显示）有专门判断；
- `ExplicitGte` 对大于等于请求值的候选给高分；
- `ExplicitExact` 在支持 content frame-rate override 时可以接受其整数倍候选，再按该应用的 UID 覆盖其 render rate；
- category 会先映射到设备配置的范围；
- non-seamless 候选会受到惩罚或直接被某些 Layer 排除。

现行源码中的 `0.95`、`0.8` 等常量属于特定评分分支。它们不是跨版本稳定的公开契约，也不应简化成所有 Layer 通用的固定公式。

#### 4.3 policy 与全局信号改变候选范围

候选模式还会受到以下条件约束：

- DisplayManager 设置的 primary/physical/render ranges；
- 当前和默认 display mode group；
- Layer 是否允许 non-seamless 切换；
- touch、idle、display power 等全局信号；
- 当前是否有显式 Layer vote；
- power-on、多个显示器的 pacesetter/follower 关系；pacesetter 是调度基准显示器，follower 跟随其节拍；
- 省电、温度和 vendor policy 最终形成的允许范围。

Android 17 代码中，touch 与 idle 都有提前返回的分支，但触发条件受显式投票、category 和 policy 影响。不能写成“任何触摸都会无条件拉满，停止后固定若干秒降频”。

#### 4.4 24 FPS 视频与 60 FPS UI 的例子

假设屏幕上同时有：

- 一个 focused 的 24 FPS 视频 Layer，使用固定源（fixed-source）语义；
- 一个持续更新的 60 FPS UI Layer；
- 候选 render rates 为 60、90、120 Hz。

120 Hz 同时是 24 和 60 的整数倍，通常具有较好的 cadence。但以下条件都可能改变结果：

- 120 Hz 不在当前 policy 范围；
- fixed-source multiple threshold（固定源参与高倍频候选评分的阈值）限制低帧率 Layer 对高档位的贡献；
- 某 Layer 只允许 seamless；
- UI 没有持续更新或面积权重很低；
- 设备处于省电、热限制或其他策略状态；
- 当前 display configuration 只支持另一组 render rates。

源码能说明算法如何评分；具体设备在某一帧选了什么，需要 trace 或 dumpsys 证据。

### 5. 应用怎样表达帧率需求

#### 5.1 `Surface.setFrameRate()`

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

该调用只提供投票。游戏仍要控制逻辑节拍、GPU in-flight frame（已提交但尚未完成呈现的帧）数量和 presentation time（期望呈现时间）。

#### 5.2 `View.setRequestedFrameRate()`

Android 15 / API 35 为 View 增加帧率偏好。可以传正数，也可以传 category：

```java
recyclerView.setRequestedFrameRate(
        View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
progressView.setRequestedFrameRate(60f);
```

请求在该 View 持续 invalidated 时才有意义。调用 ViewGroup 的同名方法不会自动把偏好传给所有子 View。Android 16 / API 36 另有 `ViewGroup.propagateRequestedFrameRate()`，是否强制覆盖子节点由参数决定。

category 由平台和显示配置解释，HIGH 不等于所有设备固定 120 Hz。对于普通 View 动画，category 往往比硬编码某个赫兹值更能适配不同设备。

#### 5.3 Window 级功耗与触摸提示

Android 15 / API 35 的 Window API 包括：

- `setFrameRatePowerSavingsBalanced(boolean)`；
- `setFrameRateBoostOnTouchEnabled(boolean)`。

前者允许系统在该窗口上更积极地平衡帧率与功耗；后者控制窗口是否参与 touch boost（触摸期间短暂偏向更高帧率）。它们没有承诺某个固定刷新率、持续时间或功耗比例。

#### 5.4 查询 ARR 与设备建议值

Android 16 / API 36 提供：

- `Display.hasArrSupport()`；
- `Display.getSuggestedFrameRate(FRAME_RATE_CATEGORY_NORMAL/HIGH)`。

应用可先查询设备建议，再把结果用于 Surface 或渲染循环。`getSuggestedFrameRate()` 返回设备定义的建议值，不是当前显示刷新率，也不是应用必须达到的性能承诺。

Android 17 / API 37 的 `Display.getFrameRateVelocityMapping()` 暴露滚动速度到建议帧率的配置点，View 滚动组件可以随速度降低逐步降低请求值。映射与 Display 相关，不能在应用里假设固定阈值。

#### 5.5 `SurfaceControl.Transaction.setFrameTimeline()`

Android 13 / API 33 的 `Choreographer.FrameData` 可以提供多个候选 timeline。公开的 `SurfaceControl.Transaction.setFrameTimeline(long vsyncId)` 在 Android 15 / API 35 加入 SDK：

```java
Choreographer.getInstance().postVsyncCallback(frameData -> {
    Choreographer.FrameTimeline timeline =
            frameData.getPreferredFrameTimeline();

    transaction.setFrameTimeline(timeline.getVsyncId());
    transaction.apply();
});
```

选择某个 `vsyncId` 只是告诉 SurfaceFlinger 期望使用哪个 presentation target（目标呈现时机）；acquire fence、事务顺序和 deadline 仍需满足。普通 View/HWUI 窗口由框架维护 timeline，业务代码通常不需要自行设置。

#### 5.6 `preferredDisplayModeId` 的使用边界

`WindowManager.LayoutParams.preferredDisplayModeId` 指定包含分辨率、刷新率等属性的 display mode。它比帧率 hint 更容易触发 mode 变化，适合明确知道目标 mode 且能处理切换影响的场景，例如部分电视播放。

只需要表达内容帧率时，优先使用 Surface/View 的帧率 API，让系统结合其他 Layer 和 policy 选择。

### 6. Choreographer 与 Frame Pacing

#### 6.1 Choreographer 合并待处理帧请求

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

#### 6.2 FrameData 提供多个候选 timeline

API 33 及以上的 `Choreographer.VsyncCallback` 接收 `FrameData`。每个 `FrameTimeline` 包含：

- `vsyncId`；
- expected presentation time；
- deadline。

`getPreferredFrameTimeline()` 是平台建议值。自建 SurfaceControl transaction 可以选另一个可满足的 timeline，再通过 API 35 的 `setFrameTimeline()` 提交。选择更晚 timeline 会改变目标呈现时机，但不能减少渲染工作本身。

#### 6.3 Frame pacing 控制的是 cadence 和队列深度

Frame pacing 的目标包括：

- 让内容帧在正确的显示机会呈现；
- 避免短帧和长帧造成不均匀 cadence；
- 限制 in-flight frame，减少 queue stuffing（队列内等待的帧持续增加）；
- 在允许的显示配置中表达合适帧率。

“每次收到 VSync 就立即渲染”只覆盖起帧节奏。若 producer 总是尽快提交，BufferQueue 可能积压，输入延迟仍会升高。

#### 6.4 Swappy 适合游戏与自建渲染循环

AGDK（Android Game Development Kit）中的 Frame Pacing Library 又称 Swappy，支持 OpenGL ES 和 Vulkan 游戏。它结合：

- Choreographer 时序；
- presentation timestamp；
- EGL/Vulkan 同步对象；
- swap interval（每隔多少个显示周期交换一次缓冲区）与 pipeline mode（帧在 CPU/GPU 阶段的并行方式）；
- 多刷新率设备的 frame-rate hint。

Swappy 可以主动等待以限制队列深度。trace 中看到 swap 或 fence wait 时，要先判断它是合理的 pacing、GPU 依赖还是被动背压，不能一律当成性能浪费。

#### 6.5 Buffer stuffing 会维持吞吐量却增加延迟

producer 连续提交速度高于显示消费速度时，多个缓冲区可能在队列中等待。表现可能是：

- FPS 看起来稳定；
- 帧总是比 expected timeline 晚一个或多个周期；
- input-to-present 延迟增加；
- producer 最终卡在 dequeue、swap 或 present；
- FrameTimeline 标记 `Buffer Stuffing`。

Android 17 的 Choreographer/HWUI 还包含 buffer stuffing recovery（积压恢复机制）。看到 recovery trace 时，应同时检查队列深度、主动延迟和后续积压是否回落。

#### 6.6 Android 17 的 producer throttling

API 37 增加 `Surface.setProducerThrottlingEnabled(boolean)`，用于控制 Vulkan/EGL Producer 的 CPU throttling（主动阻塞生产线程以限制提交速度）。默认机制会在 Consumer 仍处理前一缓冲区时给 Producer 施加背压。

这个 API 不负责选择刷新率，也不能代替 frame pacing。官方建议 Vulkan Producer 在具备正确显式同步时关闭默认 throttling，避免把 `vkPresentKHR()` 中的 CPU stall（阻塞等待）当成 Producer/Consumer 同步；队列耗尽时的自然 dequeue 背压仍会发生。异步模式下 throttling 始终启用，此开关没有效果。

### 7. Janky、late、dropped 与 missed

这些词在口语中经常混用，诊断时要回到工具字段。

#### 7.1 FrameTimeline 的两类帧

FrameTimeline 同时描述：

- **SurfaceFrame**：某个 Layer/Surface 的应用帧；
- **DisplayFrame**：SurfaceFlinger 把多个 SurfaceFrame 组合成的一次显示帧。

两者 token 不同：

- `surface_frame_token` 关联应用 producer；
- `display_frame_token` 关联系统显示帧。

一个 DisplayFrame 可以包含多个进程、多个 Layer 的 SurfaceFrame。不能把两种 token 合成一个“端到端帧号”。

#### 7.2 Expected 与 Actual

预期时间线（Expected timeline）表示调度器给该帧的预期时间窗口，实际时间线（Actual timeline）表示该帧的实际执行/呈现结果。

对应用 SurfaceFrame，actual end 覆盖应用提交和 GPU 完成边界；对 SurfaceFlinger DisplayFrame，actual timeline覆盖系统合成与显示呈现。应用 actual 按时，只能证明 producer 侧达标，不能证明 DisplayFrame 一定按时。

#### 7.3 当前 Perfetto 文档中的颜色

| 颜色 | 常见含义 |
| --- | --- |
| 绿色 | 没有检测到 jank |
| 红色 | 当前进程被归因为 jank 来源 |
| 黄色 | 应用帧异常，但原因归到 SurfaceFlinger |
| 蓝色 | 丢帧（dropped frame） |
| 浅绿色 | 高延迟状态（high-latency state），节拍可能稳定但整体呈现偏晚 |

颜色是 UI 辅助。结论应读取 `jank_type`（异常原因分类）、`present_type`（呈现结果类型）、`on_time_finish`（是否按期完成）、Layer 名称和对应 flow（Perfetto 中连接相关事件的因果线）。

#### 7.4 Janky 不等于“duration 大于一个刷新周期”

帧 deadline 由当前调度和 timeline 决定。以下情况都可能产生不同分类：

- 应用完成晚，错过自己的 deadline；
- 应用按时，SurfaceFlinger CPU 或 GPU 合成晚；
- DisplayHAL 没按目标 VSync 呈现；
- prediction error（系统预测的呈现时机与实际条件不符）；
- buffer stuffing 导致稳定但高延迟；
- 一帧被更新的帧替代；
- UI 状态没有及时同步到 RenderThread。

固定拿 16.67 ms 或 8.33 ms 与任意 slice 比较，会在高刷、ARR、pipeline overlap（不同阶段并行处理不同帧）和调度相位场景中误判。

#### 7.5 Missed 与 dropped 要描述具体对象

“错过目标帧（missed frame）”可以表示错过目标 deadline，也可以泛指显示端没有更新新内容。“丢帧（dropped frame）”在 FrameTimeline 有具体分类：SurfaceFlinger 可能选择更新的帧，应用侧也可能没有及时把 UI 状态推给 RenderThread。

不要写“所有 missed 都属于 janky”这类集合关系。可操作的表述是：

- 哪一个 SurfaceFrame；
- 它的 expected 与 actual 是什么；
- 是否关联到 DisplayFrame；
- `present_type` 与 `jank_type` 是什么；
- 旧帧被重复、目标帧晚呈现，还是该帧没有进入最终显示。

### 8. 测量工具的正确边界

#### 8.1 FrameMetrics

`FrameMetrics` 从 API 24 起提供窗口帧分段指标。常用字段包括：

| 字段 | 语义 |
| --- | --- |
| `TOTAL_DURATION` | 帧从开始到渲染完成并提交给显示子系统的总时长 |
| `DEADLINE` | 系统分配给应用生产该帧的时间，API 31+ |
| `GPU_DURATION` | 该应用帧的 GPU 完成时间，API 31+ |
| `LAYOUT_MEASURE_DURATION` | 失效 View 层级的 measure/layout 时间 |
| `DRAW_DURATION` | draw callback 阶段 |
| `SYNC_DURATION` | DisplayList 与 RenderThread 同步时间 |
| `COMMAND_ISSUE_DURATION` | 向 GPU 发出绘制命令的时间 |
| `SWAP_BUFFERS_DURATION` | 向显示子系统提交 framebuffer 的时间 |
| `INTENDED_VSYNC_TIMESTAMP` / `VSYNC_TIMESTAMP` | 预期与实际应用 VSync 时间 |

API 31 及以上可用 `TOTAL_DURATION < DEADLINE` 判断应用是否满足其生产 deadline。`TOTAL_DURATION` 不是屏幕 present 时间，各阶段还可能并行，因此它不一定等于所有 duration 字段之和。

监听回调可能因处理线程繁忙而丢失中间通知，`dropCountSinceLastInvocation` 表达的是 listener（监听器）通知丢失数量，不是屏幕掉帧数量。

#### 8.2 JankStats

JankStats 为不同 API 级别封装 frame timing（帧耗时数据）并附加 UI 状态。默认 heuristic multiplier（启发式倍数）为 2，但这是库的报告阈值，不是系统 FrameTimeline 的 jank 定义。

用于线上监控时，应记录：

- JankStats/metrics library 版本；
- 设备 API、刷新率和窗口状态；
- `frameDurationUiNanos` 等实际字段；
- 页面、交互和业务状态；
- 采样、聚合与上报规则。

不要把 JankStats、FrameMetrics 和 FrameTimeline 的“jank count”直接合并，它们的覆盖面与判定口径不同。

#### 8.3 `dumpsys gfxinfo`

`adb shell dumpsys gfxinfo <package>` 适合快速查看 View/HWUI 窗口的帧统计和分位数。它不覆盖所有自建 Surface、视频、Camera、游戏或外部 compositor 路径。

分位数能显示慢帧落在分布中的位置，通常比平均值更有用，但仍要结合场景持续时间和样本量。没有统一的“jank 超过 5% 就一定可感知”阈值，刷新率、交互类型和长帧聚集方式都会改变体验。

#### 8.4 Perfetto FrameTimeline

先用下面的查询列出目标进程的 actual SurfaceFrame，不要用 `doFrame` 数量代替帧数：

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

查询结果先按 `layer_name` 区分 App Window、SurfaceView、视频或其他 Surface。再用 token 和 flow 找到对应 expected frame 与 SurfaceFlinger DisplayFrame。表结构可能随 Perfetto 版本演进，执行前应查看当前 trace processor schema（Trace Processor 的表与字段定义）。

### 9. 一套可重复的诊断顺序

#### 第一步：记录测试条件

至少记录：

- 设备、系统 build、分辨率和 display mode；
- 当前 physical refresh（显示配置的物理刷新基准）、render rate 与 ARR 支持；
- App 目标 FPS 与调用的帧率 API；
- Surface 类型和 Layer 名称；
- 电量模式、游戏模式（Game Mode）、温度、亮度和充电状态；
- 测试动作、持续时间和 trace config（采集的数据源与缓冲区配置）。

刷新率和热状态不同的两次 trace 不适合直接比较帧预算。

#### 第二步：锁定目标 SurfaceFrame

在 FrameTimeline 选择异常帧，确认：

- 进程和 Layer 名称；
- surface/display token；
- expected 与 actual；
- `jank_type`、`present_type` 和 `on_time_finish`；
- flow 指向哪个 DisplayFrame。

若主体是 SurfaceView、视频或游戏 Surface，应跟踪它自己的 Layer，不能只看宿主 App Window。

#### 第三步：判断应用是否晚

沿同一帧检查：

- `Choreographer#doFrame` 是否晚启动；
- INPUT、ANIMATION、INSETS_ANIMATION、TRAVERSAL、COMMIT；
- RenderThread `DrawFrame`；
- GPU submission 与 completion；
- dequeue/queue 和 producer fence；
- App SurfaceFrame actual end。

主线程短不代表应用帧按时，RenderThread slice 长也不等于 GPU 一直忙。

#### 第四步：判断队列是否积压

检查：

- `dequeueBuffer` 是否等待；
- queue depth 与 release fence；
- `BufferTX - <layerName>`；
- BLAST transaction 与 SurfaceFlinger latch；
- `Buffer Stuffing` 分类与 recovery trace；
- present-to-present 间隔和输入延迟。

稳定 FPS 加上稳定的晚呈现，往往比偶发长帧更像队列延迟问题。

#### 第五步：判断系统显示阶段是否晚

检查：

- SurfaceFlinger actual timeline；
- HWC validate/present；
- CLIENT/DEVICE composition；
- DisplayHAL jank；
- present fence；
- display mode 或 render rate 是否在该帧附近改变。

若应用 SurfaceFrame 按时、DisplayFrame 迟到，问题范围才进入 SurfaceFlinger、HWC 或显示端。

#### 第六步：解释刷新率选择

需要把以下证据放在一起：

- 当前 display policy ranges；
- active display mode/group；
- Layer vote 与 desired frame rate；
- touch/idle/power 信号；
- MRR mode switch 或 ARR render-rate 变化；
- 选定的 mode/帧率；
- 切换前后的 expected timeline。

只看到刷新率轨道变化，不能说明是哪一个 Layer 请求，也不能说明它导致了当前 jank。

### 10. Game Mode 与 120 Hz 功耗

#### 10.1 Game Mode 是协作接口

Game Mode API 在部分 Android 12 设备提供，Android 13 及以上设备支持更完整。`PERFORMANCE` 与 `BATTERY` 让游戏针对低延迟/帧率或续航调整自身策略。

它没有承诺：

- 固定 CPU/GPU 频率；
- 固定 120 Hz；
- OEM 一定采用相同 intervention（厂商侧干预策略）；
- 切到 PERFORMANCE 后 FPS 一定提高。

游戏应在 `onResume()` 查询当前模式，并根据自身能力选择分辨率、画质、目标 FPS 和 pacing。测试时还要记录 OEM intervention 是否生效。

#### 10.2 高刷新率功耗不能套固定百分比

从 60 Hz 提升到 120 Hz 可能增加：

- 面板与显示控制器更新次数；
- SurfaceFlinger/HWC 活动；
- 应用 CPU/GPU 出帧频率；
- 内存带宽与 buffer 周转；
- 高性能状态驻留时间。

增长幅度受面板、亮度、内容、合成方式、SoC 和应用是否真的提高帧率影响。没有目标设备测量时，不应给出固定百分比。

#### 10.3 选择稳定目标比追逐峰值更重要

一个游戏若只能在 120 FPS 与 80 FPS 之间持续波动，稳定 90 FPS 或 60 FPS 可能提供更均匀的 cadence、更低的队列压力和更好的持续性能。判断目标值时同时看：

- CPU/GPU frame-time 分布；
- 1% low（最慢 1% 帧对应的帧率水平）与长帧簇；
- 温升后的稳态性能；
- input-to-present；
- 功耗和表面温度；
- 设备支持的 render rates。

Swappy 或引擎 pacing 应根据这些数据选择 swap interval，而不是每帧都临时追随瞬时耗时。

### 11. Kernel 与 vendor 显示边界

Framework 的 RefreshRateSelector 负责投票与 policy，Composer HAL 把所选配置或 present 时机交给设备实现。再往下可能涉及 vendor display driver、面板 TE、DRM/KMS、VBlank、时钟和电源管理。DRM/KMS 是 Linux 内核的显示设备与模式设置框架，VBlank 是一次扫描结束到下一次扫描开始之间的垂直消隐事件。

在 `android17-6.18-2026-06_r6` 中，`drivers/gpu/drm/drm_vblank.c` 与 `include/drm/drm_vblank.h` 提供通用 DRM VBlank 计数、事件和时间戳机制。但要注意：

- Android 设备不保证都用相同 DRM 驱动路径；
- common kernel 不包含所有 vendor 面板与显示控制器实现；
- framework 的 render-rate 选择不能从通用 vblank 源码反推；
- 面板的最低刷新率、TE 与无缝切换能力必须查设备配置和 vendor trace。

当问题已经定位到 HWC 之后，可继续收集：

- Composer HAL 调用与返回；
- display mode/refresh callbacks；
- vendor display tracepoints（内核或驱动记录的显示事件点）；
- DRM VBlank/page-flip 事件（设备支持时）；page-flip 表示显示控制器切换到另一扫描缓冲区；
- present fence；
- 面板或外接显示器的硬件测量。

### 12. 版本演进到 Android 17

| 版本 | 帧率与刷新率边界 |
| --- | --- |
| Android 4.1 / API 16 | Java `Choreographer` 建立应用 VSync 帧调度基线 |
| Android 11 / API 30 | 平台正式支持 MRR、Composer HAL 2.4、config group；`Surface.setFrameRate(float, int)` 公开 |
| Android 12 / API 31 | 三参数 `Surface.setFrameRate()`；FrameTimeline 可用于 Perfetto；FrameMetrics 增加 `DEADLINE`、`GPU_DURATION` |
| Android 13 / API 33 | `Choreographer.FrameData` / `FrameTimeline` 公开多个候选 timeline |
| Android 15 / API 35 | ARR 平台能力；View/Window 帧率提示；公开 `SurfaceControl.Transaction.setFrameTimeline()` |
| Android 16 / API 36 | `Display.hasArrSupport()`、`getSuggestedFrameRate()`；ViewGroup 帧率请求传播 API |
| Android 17 / API 37 | `Display.getFrameRateVelocityMapping()`；`Surface` producer throttling 控制；RefreshRateSelector 现行九类 vote 与 ARR/MRR 分支按 `android-17.0.0_r1` 解读 |

当前源码能证明 Android 17 的实现状态，不能自动证明某段逻辑是 Android 17 首次加入。涉及“从某版本开始”的结论，应同时检查 API level、旧 tag 或官方版本说明。

### 13. Android 17 源码索引

#### 应用 API 与帧时序

- `frameworks/base/core/java/android/view/Choreographer.java`
- `frameworks/base/core/java/android/view/DisplayEventReceiver.java`
- `frameworks/base/core/java/android/view/Display.java`
- `frameworks/base/core/java/android/view/View.java`
- `frameworks/base/core/java/android/view/ViewGroup.java`
- `frameworks/base/core/java/android/view/Window.java`
- `frameworks/base/core/java/android/view/Surface.java`
- `frameworks/base/core/java/android/view/SurfaceControl.java`
- `frameworks/base/core/java/android/view/FrameMetrics.java`

#### SurfaceFlinger 调度

- `frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.h`
- `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp`
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`

#### ARR 与 kernel 边界

- `hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl`
- `hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl`
- `drivers/gpu/drm/drm_vblank.c`
- `include/drm/drm_vblank.h`

### Android 17 的帧率协作边界

帧率评估需要检查 producer、SurfaceFlinger 和显示设备能否以一致的目标节拍协作：

1. FPS 是吞吐量，present interval 描述视觉节拍，input-to-present 描述交互延迟；
2. `doFrame`、RenderThread、SurfaceFrame 和 DisplayFrame 各有不同的 frame-time 口径；
3. MRR 在 display mode 之间切换，ARR 在支持的配置内按离散 VSync 步进改变刷新节拍，LTPO 只是可能提供这些能力的面板技术；
4. Android 17 通过 LayerHistory 汇总 Layer vote，再由 RefreshRateSelector 在 policy 允许的候选中评分；
5. Surface、View、Window 和 SurfaceControl API 都是提示或目标表达，不能代替应用自身 pacing；
6. Jank 结论应来自目标 SurfaceFrame、DisplayFrame、token、deadline、fence 和 present 证据；
7. 平均 FPS、单条 `doFrame`、单次刷新率切换都不足以独立解释卡顿。

排查时先锁定目标 Surface 和 FrameTimeline，再判断应用、队列、SurfaceFlinger 与显示端谁先错过时序。刷新率变化需要放回 Layer vote、display policy 与选模结果中解释。

### 常见误区

| 误判 | 更可靠的检查 |
| --- | --- |
| 相邻 `doFrame` 间隔 33 ms，所以屏幕掉了一帧 | 查看目标 SurfaceFrame 与 DisplayFrame；静态窗口本就可能没有回调 |
| 120 Hz 下每个线程都必须在 8.33 ms 内结束 | 以目标帧 deadline 和跨线程依赖为准，保留 pipeline overlap |
| 60 FPS 在 120 Hz 一定浪费一半 GPU | 应用只需生产 60 帧；显示重复不要求 GPU 重画同一帧 |
| 高刷新率一定更流畅 | 检查应用是否按时、cadence、输入延迟和队列深度 |
| LTPO 等于 Android ARR | 查询 `hasArrSupport()`、HWC 配置和 trace |
| 1–120 Hz LTPO 可以取任意连续值 | 查看设备报告的离散能力和限制条件 |
| `setFrameRate(120)` 会把屏幕锁到 120 Hz | 它是 Layer vote，最终受 policy、其他 Layer 和设备能力影响 |
| `Display.getRefreshRate()` 不等于请求值，所以发生 override | 可能是正常选模、policy、其他 Layer 或 ARR；需要系统侧证据 |
| Game Mode PERFORMANCE 会锁高频 | Game Mode 表达用户选择，游戏和 OEM intervention（厂商按模式施加的帧率、分辨率等调整）共同决定策略 |
| FrameMetrics `TOTAL_DURATION` 是触摸到屏幕延迟 | 它只计算到提交给显示子系统为止，不包含完整输入与面板边界 |
| `DrawFrame` 很长就说明 GPU 慢 | 区分 CPU 工作、dequeue/fence wait、GPU completion |
| 平均 FPS 达标就没有卡顿 | 同时看分位数、长帧簇、present interval 和 high-latency state |

## 自适应刷新率的输入与约束

固定刷新率只需要判断应用是否按期产帧，自适应刷新还要结合触摸、动画、视频节奏、功耗和面板能力动态调整。

固定刷新率设备给人的错觉是：60 Hz 的帧预算永远是 16.67 ms，120 Hz 永远是 8.33 ms。支持自适应刷新率（Adaptive Refresh Rate，ARR）的设备会按内容更新节奏改变显示间隔。滚动时可以提高刷新率，页面静止后可以降低刷新率。此时再拿固定的 16.67 ms 阈值检查每一帧，会把正常降频误判成卡顿，也可能漏掉高刷场景中的超时。

理解 ARR 要先分清三个量：

- **内容帧率（content/render rate）**：应用或某个 Layer（图层）产生新帧的节奏，例如视频 24 FPS、UI 60 FPS、游戏 120 FPS。
- **显示刷新率（display refresh rate）**：面板更新屏幕图像的节奏。
- **VSync/TE 信号频率**：系统和面板用来对齐时序的硬件节拍。TE（Tearing Effect，防撕裂同步信号）通常由面板提供；在 ARR 配置里，它的频率可以高于实际显示刷新率。

应用只能表达内容需求和偏好。最终刷新率还要同时满足用户设置、低电量模式、温度策略、其他可见 Layer、显示硬件能力和厂商策略。任何 `setFrameRate` 或 View 投票都不等于“强制屏幕切到某个 Hz”。

### 1. 多刷新率与 ARR 是两套机制

#### 1.1 Android 11—14：在多个固定模式之间选择

Android 11（API 30）公开 `Surface.setFrameRate()` 后，应用可以声明 Surface 的内容帧率。传统多刷新率（Multiple Refresh Rate，MRR）设备通常提供若干固定显示模式，例如 60 Hz 和 120 Hz。系统需要改变 active mode（当前生效的显示模式）才能改变物理刷新节奏；部分切换可以无缝完成，另一些切换可能出现短暂黑屏或时序抖动。

Android 12（API 31）的三参数 `Surface.setFrameRate()` 允许应用说明是否接受非无缝切换。这仍属于 mode switching（显示模式切换）：候选对象是若干固定模式。

#### 1.2 Android 15 起：同一显示配置内改变刷新间隔

Android 15 引入 ARR 平台能力。面向应用的官方指南把可用边界写为 Android 15 QPR1（Quarterly Platform Release 1，季度平台更新 1）及以上，并要求设备实现对应的 Composer HAL（显示合成硬件抽象层）接口。系统版本满足条件仍不够，应用应在 API 36 及以上调用 `Display.hasArrSupport()` 检查当前 Display。

ARR 配置中，显示 VSync/TE 信号频率与实际刷新率可以解耦。面板按照 TE 周期接收机会，但不必在每个 TE 都刷新；实际刷新率只能取 TE 频率的整数分频。

以官方示例为例：

- `vsyncPeriod = 4.16 ms`，对应 240 Hz TE；
- `minFrameIntervalNs = 8.33 ms`，表示两次有效刷新至少间隔 8.33 ms，因此最高刷新率是 120 Hz；
- 之后可以在满足最小间隔的 TE 边界展示新帧，例如 120 Hz、80 Hz、60 Hz 等离散档位。

`DisplayConfiguration.vrrConfig != null` 表示该显示配置支持 ARR；`vrrConfig == null` 表示普通非 ARR 配置。Composer3 的定义要求一个配置按 ARR 或 MRR 解释，不能把同一个配置同时描述成两者。

LTPO（Low-Temperature Polycrystalline Oxide，低温多晶氧化物）面板常用于实现宽范围刷新率，但 Android 公共 API 没有要求应用先判断面板材料。应用需要关注 `hasArrSupport()`、系统支持的 render rate（内容渲染帧率）和自身内容节奏。

### 2. Android 17 的控制链

把系统路径拆成“约束候选范围”和“按内容选择”两段，会更容易读懂源码。

#### 2.1 DisplayModeDirector 先计算允许范围

Android 17 的 `DisplayModeDirector` 是系统显示模式策略组件。它的 `getDesiredDisplayModeSpecs(int)` 从 `VotesStorage` 读取全局投票和指定 Display 的投票，再由 `VoteSummary` 合并约束。输入包括：

- 用户设置的最低、峰值和默认刷新率；
- 低电量、亮度、温度与系统策略；
- 应用请求的尺寸、物理刷新率范围和 render frame-rate 范围；
- 是否允许同组或跨组 mode switching；
- 设备支持的 mode、ARR 能力和 work duration（调度工作时长）配置。

结果是 `DesiredDisplayModeSpecs`：其中包含 base mode（基准显示模式）、primary/app-request 两组 physical/render rate range（物理刷新率与内容渲染帧率范围）、`allowGroupSwitching` 等信息。`DisplayManagerService.DesiredDisplayModeSpecsObserver` 把结果写入 `LogicalDisplay`，`LocalDisplayAdapter` 再转换为 `SurfaceControl.DesiredDisplayModeSpecs` 交给 SurfaceFlinger。

这一段决定“哪些模式和帧率仍可被选择”，不负责逐帧估算当前内容需要多少 Hz。

#### 2.2 SurfaceFlinger Scheduler 再按可见内容选择

SurfaceFlinger 完成 transaction flush（处理已提交的窗口状态事务）和 buffer latch（锁存本轮使用的 buffer）后，Android 17 在 `SurfaceFlinger.cpp` 的 `Refresh Rate Selection` trace 区间调用：

```cpp
mScheduler->chooseRefreshRateForContent(
        &mLayerHierarchyBuilder.getHierarchy(),
        updateAttachedChoreographer);
```

这段代码说明选择发生在 Layer 状态更新之后。`Scheduler::chooseRefreshRateForContent()` 先让 `LayerHistory` 汇总可见内容，再把 content requirements（内容帧率需求）应用到刷新率策略。产生 mode request（显示模式请求）后，SurfaceFlinger 仍会调用 `RefreshRateSelector::isModeAllowed()` 检查候选是否符合 DisplayManager 下发的范围。

当调用参数允许更新应用节奏时，`chooseRefreshRateForContent()` 还会把已选的 pacesetter fps（主导显示设备的帧率）交给 `updateAttachedChoreographers()`。该函数遍历 layer hierarchy（图层层级），依据 `FIXED_SOURCE`、`DEFAULT` 等 vote 计算显示节奏与应用回调节奏之间的整数 divisor（分频系数），再更新对应的 `EventThreadConnection.frameRate`。因此，trace 中 `VSYNC-app` 间隔的变化既可能来自应用请求，也可能是显示选择结果反馈给 attached Choreographer；只观察物理 Display mode 会漏掉这一层。

因此，分析“为什么没有升到 120 Hz”时，至少要同时检查：

1. Layer 有没有给出帧率偏好，更新节奏又是多少；
2. 用户峰值刷新率、低电量和温度策略是否收窄范围；
3. 当前显示配置是 MRR 还是 ARR；
4. 其他可见 Layer 是否给出更高或不兼容的请求；
5. Scheduler 最终选择的 render rate 和 mode。

#### 2.3 Composer HAL 把 ARR cadence 交给显示硬件

这里的 cadence 指连续帧的展示节奏。ARR 设备需要 Composer3 v3 或更高版本的接口。Android 17 的关键字段和调用如下：

- `DisplayConfiguration.vsyncPeriod`：ARR 配置中表示 TE 信号周期；
- `VrrConfig.minFrameIntervalNs`：两次展示之间的最小间隔，也就是该配置的最高刷新率边界；
- `DisplayCommand.frameIntervalNs`：提示后续帧的 cadence；
- `IComposerClient.notifyExpectedPresent()`：在下一帧偏离既有 cadence，或空闲时间超过 HAL 声明的 timeout（超时时间）时，提前通知期望展示时间与后续间隔。

SurfaceFlinger 的 `onExpectedPresentTimePosted()` 会读取当前 mode 的 `VrrConfig.notifyExpectedPresentConfig`。`notifyExpectedPresentIfRequired()` 判断下一帧是否仍在原 cadence 内、是否超时；需要通知时，再经 `HWComposer::notifyExpectedPresent()` 进入 Composer HAL。

`notifyExpectedPresentConfig == null` 时，框架不会调用这项 HAL 提示；`timeoutNs == 0` 表示每帧都要提示。非零 `headsUpNs` 则给出提示必须领先下一次 expected-present（预期显示时刻）的最短时间。它们描述的是显示硬件需要多少准备时间，不代表应用获得了额外帧预算。

这套接口允许面板在不切换 mode 的情况下准备下一次刷新。它无法替应用修复晚提交、错误时间戳、BufferQueue 堆积或 acquire fence 过晚的问题。

#### 2.4 VsyncModulator 负责工作预算，不负责选择刷新率

`VsyncModulator` 经常和刷新率切换同时出现在 trace 中，但职责不同。Android 17 的 `VsyncModulator` 在以下配置间切换：

- `Early`：刷新率正在变化、有提前唤醒请求或近期 transaction（窗口状态事务）；
- `EarlyGpu`：近期使用 GPU composition（GPU 合成）；
- `Late`：常规状态。

这些配置调整应用与 SurfaceFlinger 的 work duration/offset（工作时长与相对 VSync 的偏移），让事务、GPU 合成或 mode transition（显示模式切换）获得合适的执行时间。刷新率由 Display policy（显示策略）、`LayerHistory` 和 `RefreshRateSelector` 决定，`VsyncModulator` 只改变调度预算。看到 `Vsync-Early` 或 `Vsync-EarlyGpu` counter（计数轨道）时，不能把它当成刷新率选择结果。

### 3. 普通 UI：优先使用 View 和 Compose

多数 View 应用无需改代码也能从 ARR 获益。系统会收集本帧发生重绘的 View 投票，合并后把偏好传到下层 Layer。常规策略倾向于采用最高的有效投票，但实现细节可能随平台版本调整。

#### 3.1 View 的类别投票

Android 17 中常用的类别是：

- `REQUESTED_FRAME_RATE_CATEGORY_DEFAULT`：清除显式请求，恢复框架默认判断；
- `REQUESTED_FRAME_RATE_CATEGORY_NO_PREFERENCE`：该 View 明确不影响本帧帧率选择；
- `REQUESTED_FRAME_RATE_CATEGORY_NORMAL`：适合普通动画，通常接近 60 Hz；
- `REQUESTED_FRAME_RATE_CATEGORY_HIGH`：适合对平滑度要求较高的动画，会增加功耗。

下面的代码让普通动画保持 `Normal`，只在快速运动阶段投 `High`，结束后恢复默认：

```java
private void updateFrameRateVote(View animatedView, boolean fastMotion) {
    animatedView.setRequestedFrameRate(
            fastMotion
                    ? View.REQUESTED_FRAME_RATE_CATEGORY_HIGH
                    : View.REQUESTED_FRAME_RATE_CATEGORY_NORMAL);
}

private void clearFrameRateVote(View animatedView) {
    animatedView.setRequestedFrameRate(
            View.REQUESTED_FRAME_RATE_CATEGORY_DEFAULT);
}
```

`setRequestedFrameRate()` 也接受 30、60、120 等正数。数值表示内容偏好，不要求它正好等于设备的物理刷新率。多个数值投票互为整数倍时，`ViewRootImpl` 选择能覆盖其他投票的较高值；无法整除时，源码会设置 conflict（冲突）标记，停止直接提交该数值，并按最大请求是否高于 60 fps 回退到 `HIGH` 或 `NORMAL` 类别。因此，trace 中出现类别投票不一定表示业务直接调用了类别 API，也可能是数值冲突后的回退结果。官方文档明确说明这套合并策略可能调整，业务代码不应依赖精确的内部优先级。

还有两条容易遗漏的边界：

- View 只有在需要重绘时才参与当前帧投票；
- 在 `ViewGroup` 上设置请求不会自动传给所有子 View。

Android 17 `View.java` 仍含受 flag（功能开关）管理的 `REQUESTED_FRAME_RATE_CATEGORY_LOW`。当前 ARR 开发指南的标准类别列表没有把 `LOW` 作为普通应用的主要入口。若项目准备使用它，应以所用 `compileSdk`（编译时采用的 Android API 版本）、设备 flag 和 API 文档为准；通用代码优先使用 `DEFAULT`、`NO_PREFERENCE`、`NORMAL`、`HIGH` 或明确的正数。

#### 3.2 滚动组件要提供速度

触摸按下期间，系统通常通过 touch boost（触摸升频）提高 render rate；手指抬起进入 fling（惯性滚动）后，刷新率可以随速度下降。`ScrollView`、`ListView`、`GridView` 已接入这类策略。AndroidX 侧至少需要：

- `androidx.recyclerview:recyclerview:1.4.0`；
- `androidx.core:core:1.15.0`，用于 `NestedScrollView` 等组件。

自定义滚动组件需要在 fling 的每一帧调用 `View.setFrameContentVelocity(float)`，单位是像素每秒。该值会在 View 每次重绘后重置，只在启动 fling 时设置一次不会持续生效。

下面的片段展示自定义 View 在每帧把当前速度交给框架：

```java
private void reportFlingVelocity(View scrollingView, float velocityPxPerSecond) {
    scrollingView.setFrameContentVelocity(Math.abs(velocityPxPerSecond));
}
```

框架利用速度判断 fling 处于快速还是减速阶段。非滚动 View 的位移和尺寸动画已有独立策略，调用这个 API 不会额外产生预期效果。

#### 3.3 Compose 入口

Compose 1.9 提供 `Modifier.preferredFrameRate(...)`，可以传具体帧率或 `FrameRateCategory`。它表达的是 Composable（Compose UI 节点）的偏好，最终仍由窗口、其他内容与显示策略共同决定。无需为“启用 ARR”而把整个界面固定在 High；默认策略不足时，再对有明确体验问题的局部动画增加请求。

#### 3.4 Window 级开关

Android 15（API 35）提供两个 Window 级控制：

- `setFrameRateBoostOnTouchEnabled(boolean)`：控制触摸时是否升频，默认启用；
- `setFrameRatePowerSavingsBalanced(boolean)`：控制该 Window 是否允许 ARR 的功耗平衡策略，默认启用。

关闭 touch boost 会影响触摸响应；关闭 power-savings balance（功耗平衡）可能增加高刷新率驻留时间和功耗。官方指南只建议在出现严重兼容问题时关闭，并要求用目标设备上的 trace 和功耗数据证明必要性。

### 4. Surface：给独立 Layer 声明内容节奏

视频、游戏引擎、自建 EGL/Vulkan Surface 或独立 `SurfaceView` 更常直接使用 `Surface.setFrameRate()`。Android 17 中，兼容性参数应按内容类型选择：

| 内容 | compatibility | 含义 |
|---|---|---|
| 视频 | `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` | 内容帧率固定，系统应优先选择便于形成整数倍 cadence 的显示刷新率 |
| 游戏 | `FRAME_RATE_COMPATIBILITY_DEFAULT` | 游戏可以适应系统最终选择的 render rate |
| UI、动画、滚动、fling | `FRAME_RATE_COMPATIBILITY_AT_LEAST` | API 36 起，请求显示帧率不低于给定值 |

下面的代码分别声明 24 FPS 视频和最低 60 FPS 的 UI Surface，并在内容结束时清理旧请求：

```java
videoSurface.setFrameRate(
        24f,
        Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
        Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);

uiSurface.setFrameRate(
        60f,
        Surface.FRAME_RATE_COMPATIBILITY_AT_LEAST,
        Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);

videoSurface.clearFrameRate(); // API 34+
```

`frameRate` 可以不等于设备公开的物理档位。系统可能让 24 FPS 内容运行在 48 Hz、72 Hz、120 Hz 等兼容节奏上，也可能因其他图层或策略维持当前模式。

`setFrameRate()` 只影响 SurfaceFlinger 对显示帧率的选择，不会限制 Producer（buffer 生产者）的产帧速度。它可能间接改变 Choreographer 回调时间和 buffer 释放间隔，但不能代替 frame pacing。引擎仍需控制 `eglSwapBuffers()`、`vkQueuePresentKHR()` 或播放器提交时间戳，否则高频生产会让 queue 填满，增加输入延迟。

Android 17（API 37）的 `Surface.setProducerThrottlingEnabled()` 调整 EGL/Vulkan Producer 在 queue 阶段承受的 CPU backpressure（下游忙时对上游形成的反压），属于队列节拍控制，不是刷新率投票。该 API 的细节见 2.11；排查 ARR 时应分别检查 `setFrameRate()` 的投票和 producer 限速。

### 5. Display 与 Choreographer 能查到什么

#### 5.1 Display 能力查询

API 36 及以上可以先判断 ARR 能力，再读取系统对 Normal/High 类别的建议值：

```java
Display display = context.getDisplay();
if (display != null && display.hasArrSupport()) {
    float normal = display.getSuggestedFrameRate(
            Display.FRAME_RATE_CATEGORY_NORMAL);
    float high = display.getSuggestedFrameRate(
            Display.FRAME_RATE_CATEGORY_HIGH);
    float[] renderRates = display.getSupportedRefreshRates();
}
```

这段代码有三条语义边界：

- `getSuggestedFrameRate(int)` 只接受 `FRAME_RATE_CATEGORY_NORMAL` 和 `FRAME_RATE_CATEGORY_HIGH`，不能用于把任意帧率映射到最接近的显示档位；
- `getSupportedRefreshRates()` 从 API 21 就存在，但 API 36 起返回 Display 支持的 render rate；API 35 及以下只返回默认 mode 的刷新率，需要更多物理 mode 时读取 `getSupportedModes()`；
- 多屏、折叠屏内外屏或外接显示器的能力可以不同，窗口迁移 Display 后要重新查询。

Android 17 的 `DisplayInfo#getRefreshRate()` 会优先返回应用可感知的 override/render frame rate（覆盖值或内容渲染帧率）；没有这两项时才回退到 active mode refresh rate。`Display.getRefreshRate()` 因而适合观察当前框架报告给应用的节奏，但一次读取不能证明整个测试区间的 ARR 行为。诊断仍应记录持续变化和实际 present。

#### 5.2 Choreographer.FrameData 没有 refreshRate 字段

公开回调是 `Choreographer.VsyncCallback.onVsync(FrameData)`。API 33 起的 `FrameData` 提供：

- `getFrameTimeNanos()`；
- `getFrameTimelines()`；
- `getPreferredFrameTimeline()`。

下面的回调读取当前帧的首选时间线，用它安排动画或渲染工作：

```java
Choreographer.getInstance().postVsyncCallback(frameData -> {
    long frameStartNs = frameData.getFrameTimeNanos();
    Choreographer.FrameTimeline preferred =
            frameData.getPreferredFrameTimeline();
    long expectedPresentNs =
            preferred.getExpectedPresentationTimeNanos();
    long deadlineNs = preferred.getDeadlineNanos();

    // 仅在当前回调中读取这些值，用于本帧的动画和渲染决策。
});
```

`FrameData` 只在回调期间有效，也没有公开 `refreshRate` 字段。不能把内部 `DisplayEventReceiver.VsyncEventData` 的字段写进应用示例。判断节奏变化时，应结合连续回调间隔、Display 信息和系统 trace。

### 6. Perfetto：先确认刷新节奏，再判断 jank

分析 ARR trace 时，不应先套用“是否超过 16.67 ms”的固定阈值。可以按以下顺序观察。

#### 6.1 先记录测试条件

至少记录设备与固件、Display、分辨率、亮度、用户刷新率设置、低电量模式、温度、应用版本、内容类型和目标帧率。游戏还要记录 Game Mode（游戏模式）、FPS intervention（系统对游戏帧率的干预）和引擎 pacing 配置。缺少这些条件，跨设备或跨版本的 Hz 对比没有可重复性。

#### 6.2 在同一时间窗内看四组证据

1. **应用节拍**：`vsync-app`、`Choreographer#doFrame` 或引擎 frame marker（帧标记）；
2. **内容生产**：RenderThread、EGL/Vulkan present、BufferQueue 和 acquire/release fence；
3. **系统选择**：SurfaceFlinger 的 `Refresh Rate Selection`、active mode、render rate 与相关 counter（计数轨道）；
4. **最终显示**：FrameTimeline、SurfaceFlinger DisplayFrame、HWC（Hardware Composer，硬件合成器）、present fence 和设备显示驱动事件。

滑动期间应用节拍变短，fling 减速后逐步变长，同时 FrameTimeline 没有连续 jank（卡顿归因），通常符合 ARR 策略。若 mode change 附近出现黑屏或长间隔，更接近传统 MRR 的非无缝切换。若 Producer 已经晚交 buffer，刷新率变化只是背景条件，不能把根因写成 SurfaceFlinger 选错档位。

Perfetto 官方文档目前对 SurfaceView 的 FrameTimeline 支持有限。标准 HWUI（Android 硬件加速 UI 渲染库）应用窗口可以优先查看应用的 actual/expected timeline；SurfaceView、视频和游戏还需要核对独立 Layer、buffer timestamp、fence、HWC 与 present。

#### 6.3 用正确的键关联 expected/actual FrameTimeline

以下查询用于检查指定进程的应用 FrameTimeline。它沿用 Android 17 Perfetto metric（预置分析指标）的关联方式，以 `upid + name` 连接 expected 与 actual；`upid` 是 Perfetto 为进程分配的唯一标识，`name` 是 frame token（帧关联标识）的字符串形式。

```sql
SELECT
  process.name AS process_name,
  actual.name AS frame_id,
  actual.layer_name,
  ROUND(actual.ts / 1e6, 2) AS actual_start_ms,
  ROUND(actual.dur / 1e6, 2) AS actual_duration_ms,
  ROUND(expected.dur / 1e6, 2) AS expected_duration_ms,
  actual.present_type,
  actual.on_time_finish,
  actual.jank_type
FROM actual_frame_timeline_slice AS actual
LEFT JOIN expected_frame_timeline_slice AS expected
  ON expected.upid = actual.upid
 AND expected.name = actual.name
JOIN process
  ON process.upid = actual.upid
WHERE process.name = 'your.package.name'
ORDER BY actual.ts;
```

查询结果适合回答两个问题：系统给应用的预算是否随节奏变化，以及实际帧是否伴随 `jank_type`、`present_type` 恶化。`actual.ts` 是 actual timeline slice（实际时间线片段）的起点，不是面板物理 present 时间；判断最终上屏仍要结合 SurfaceFlinger timeline、flow（跨轨道关联线）、present fence 或显示驱动证据。

不能用 `display_frame_token` 是否逐一连续来判断 ARR 正常与否。应用可以按低于 TE 的节奏产帧，Surface 也不必每个 VSync 都提交新 buffer；trace 裁剪还会造成 token gap（标识不连续）。token 用于关联同一帧，不能单独充当“漏 VSync”计数器。

#### 6.4 判断问题属于哪一层

| 现象 | 优先检查 |
|---|---|
| View 已投 `High`，仍长期保持较低 render rate | Window 开关、用户峰值、低电量与温度策略、其他图层、设备 ARR 能力 |
| render rate 已提高，应用仍短帧与长帧交替 | 应用 pacing、提交时间戳、BufferQueue 深度 |
| 应用按时完成，SurfaceFlinger/DisplayFrame 仍晚 | SurfaceFlinger work duration、GPU/HWC composition、present fence、显示驱动 |
| 惯性滚动结束后一直不降频 | 每帧 velocity 是否更新、View 是否持续重绘、touch boost 与窗口策略 |
| 静态页面仍驻留高刷 | 活跃动画、不可见但持续 invalidate（请求重绘）的 View、视频/Surface 请求、系统 UI Layer |
| 切换时只有单次长间隔 | 区分 ARR cadence 调整与 MRR mode switch，再检查是否持续复现 |

### 7. 功耗、体验与设备实现边界

高刷新率会增加面板、显示控制器、合成和应用产帧负担，但没有一个适用于所有设备的固定功耗百分比。面板、亮度、分辨率、SoC（System on Chip，系统级芯片）、内容、OEM（设备厂商）策略和环境温度都会改变结果。评估应同时记录：

- 高刷新率驻留时间与实际 render/present cadence；
- 应用、GPU、SurfaceFlinger 和显示子系统功耗；
- 触摸到显示延迟、帧时间分布与连续 jank；
- 测试过程中的亮度、温度和系统模式。

低频面板的 Gamma（灰阶到亮度的映射）、亮度补偿或 self-refresh（面板自行维持静态画面）细节通常由面板、固件与厂商显示 HAL 实现。Android 17 Composer3 的 ARR 标准接口定义了 `vrrConfig`、`minFrameIntervalNs`、`notifyExpectedPresent` 和 `frameIntervalNs`，没有提供通用的“实时 Gamma 补偿”应用 API。缺少设备厂商文档或驱动证据时，不应把低亮闪烁归因于某个 AOSP Gamma 算法。

### 8. 内核与驱动证据

内核源码以 `android17-6.18-2026-06_r6` 为锚点。公共同步语义可从以下源码理解：

- `drivers/dma-buf/dma-fence.c`：跨设备异步工作完成关系；
- `drivers/dma-buf/sync_file.c`：把 dma-fence 暴露为 sync_file 文件描述符；
- `drivers/gpu/drm/drm_vblank.c`：采用 DRM/KMS（Linux 的显示与模式设置框架）的设备上，vblank（垂直消隐期）计数与时间事件的公共实现。

ARR 的面板控制、TE 分频、self-refresh、带宽和时钟策略通常位于厂商显示驱动、固件和 Composer HAL。Android 设备也不保证使用主线 DRM/KMS 路径。排查具体机型时，应在 AOSP trace 之外补充厂商 HWC 日志、display tracepoint（显示驱动跟踪事件点）、present fence、时钟与带宽配置请求及面板事件，不能用通用内核 tag（版本标签）推断某款面板的私有策略。

### 9. Android 11—17 版本边界

| 版本 | 相关变化 |
|---|---|
| Android 11/API 30 | `Surface.setFrameRate(float, int)` 与 Surface frame-rate compatibility 公开，多刷新率设备可按 Layer 内容选择 mode |
| Android 12/API 31 | 三参数 `setFrameRate()` 允许说明是否接受非无缝切换；FrameTimeline 成为现代显示诊断基线 |
| Android 13/API 33 | `Choreographer.FrameData` 与 `FrameTimeline` 公开；HWC HAL 转向 AIDL |
| Android 14/API 34 | `Surface.clearFrameRate()` 公开，便于撤销旧请求 |
| Android 15/API 35 | ARR 平台能力进入支持设备；View/Window 帧率管理 API 与触摸、滚动策略成为应用入口 |
| Android 16/API 36 | `Display.hasArrSupport()`、`getSuggestedFrameRate()` 与 render-rate 查询语义公开；增加 `FRAME_RATE_COMPATIBILITY_AT_LEAST` |
| Android 17/API 37 | 源码锚点更新到 Android 17；DisplayManager、SurfaceFlinger Scheduler 与 Composer3 ARR 主路径延续。新增 `Surface.setProducerThrottlingEnabled()`，用于控制 Producer 反压，不参与 ARR 投票 |

版本表只说明 API 和平台能力的边界。某台设备是否支持 ARR、支持哪些 render rate、是否允许某类 mode switch，仍要在运行时查询，并以 trace 为准。

### 常见误区

**把 ARR 写成 60 Hz/120 Hz mode switching。**

ARR 可以在同一显示配置内按 TE 的离散分频改变刷新间隔；MRR 则在多个固定 mode 之间切换。

**把 `setFrameRate()` 写成强制刷新率。**

它是 Layer 的内容帧率提示。系统还会合并其他图层和全局约束。

**认为刷新率选择等于 frame pacing。**

刷新率选择决定系统倾向于什么显示节奏；pacing 决定 Producer 在何时提交哪一帧。缺少任一环节，都可能让 queue 填满或形成不均匀 cadence。

**把 `getSuggestedFrameRate()` 当成任意 FPS 映射器。**

它只接受 `Normal` 和 `High` 两个类别。

**从 `FrameData` 读取不存在的 `refreshRate`。**

公开 API 提供帧起点与候选时间线。刷新节奏要通过连续样本、Display 和 trace 判断。

**看到 VSync 间隔改变就判为掉帧。**

先确认当前目标预算是否也改变，再看 actual timeline、jank 类型和最终 present。

**把 `VsyncModulator` 当成刷新率选择器。**

它调整 Early/EarlyGpu/Late 工作预算；内容选择发生在 Scheduler 和 `RefreshRateSelector`。

## 模式切换、应用适配与抖动

策略选出目标刷新率后，显示链路还要完成 mode switch。应用请求、SurfaceFlinger 调度与硬件切换不同步时，会出现短时卡顿或节奏波动。

刷新率变化附近出现掉帧时，先分清三个时刻：

1. SurfaceFlinger 选出了新的显示模式；
2. Composer HAL 开始执行模式切换；
3. SurfaceFlinger 将目标模式更新为 active。

第三步有两种完成方式：DisplayCommand modeset（通过显示命令切换模式）成功且不要求刷新帧时，平台立即更新 active（当前生效）状态；HAL（硬件抽象层）要求先提交刷新帧时，SurfaceFlinger 会等待相关 `FrameTarget`（本轮显示提交的状态记录）退出待定状态。后一条路径用到 present fence（显示提交完成信号）状态，但 fence 只能证明对应显示提交已经完成，不能单独证明面板内部的 PLL（Phase-Locked Loop，锁相环）、命令序列或扫描周期。

这些时刻可能相隔若干次合成。只看应用主线程、`Choreographer#doFrame` 或某一帧的 CPU 耗时，无法证明显示模式是否已经切换，也无法证明掉帧由模式切换引起。

平台源码以 Android 17/API 37 的 `android-17.0.0_r1` 为锚点，以下内容讨论离散多刷新率显示（Multiple Refresh Rate，MRR）的模式切换、应用帧率请求和系统侧诊断。ARR（Adaptive Refresh Rate，自适应刷新率）面板可在同一配置内按 TE/VSync 同步信号的离散倍数改变刷新节奏，无需为每次节奏变化切换显示配置；相关机制见 [2.2 帧率、刷新率与显示模式选择](02-framerate-refresh-display-mode.md)。

### 1. 先区分三类变化

“帧率变了”可能指三件不同的事。它们的控制路径、可见现象和诊断证据都不同。

| 变化 | Android 17 中的含义 | 是否一定调用 HWC（Hardware Composer，硬件合成器）modeset |
|---|---|---|
| Render rate（内容渲染帧率）变化 | SurfaceFlinger 改变调度和合成节奏，物理 display mode 不变 | 否 |
| MRR 模式切换 | 在多个离散 display mode 之间切换，例如 60 Hz → 120 Hz | 是 |
| ARR 刷新节奏调整 | 在一个 ARR 配置内按 TE/VSync 的离散倍数改变刷新或自刷新间隔；配置的 `vsyncPeriod` 仍表示 TE/VSync 基准 | 否，走 ARR cadence（连续帧展示节奏）提示与面板自刷新控制路径 |

#### 1.1 Render rate 变化不等于显示模式切换

Android 17 的 `DisplayModeController::setDesiredMode()` 会比较请求中的物理模式和当前模式：

- 物理模式没有变化，只有 `renderRate` 变化时，返回 `InitiateRenderRateSwitch`；
- 物理模式变化时，返回 `InitiateDisplayModeSwitch`；
- 请求与当前状态相同，或者已有相同请求在处理时，不启动新的切换。

Perfetto 中看到应用或 SurfaceFlinger 的调度频率变化时，不能直接写成“面板从 60 Hz 切到了 120 Hz”，还需要查看 `ActiveModeFps` 等显示模式证据。

#### 1.2 MRR 是离散配置之间的切换

MRR 设备向系统暴露多个显示配置。每个配置包含分辨率、VSync 周期以及 `configGroup` 等属性。SurfaceFlinger 在显示策略允许的范围内，根据可见 Layer（图层）的请求、内容检测结果和系统信号选择候选模式。

MRR 不意味着应用能指定最终模式。`Surface.setFrameRate()` 提供内容帧率偏好，调度器还要考虑：

- DisplayManager 下发的最小、最大和默认模式策略；
- 前台 Layer 的帧率投票及其可见性、焦点状态；
- 省电模式等系统限制；
- 设备支持的模式及其切换能力；
- 厂商在平台允许范围内加入的策略。

应用必须能在请求没有被满足时正常运行。

#### 1.3 ARR 在一个配置内调整实际刷新节奏

Android 15 QPR1 起的平台 ARR 支持允许兼容硬件在一个显示配置内调整实际刷新节奏。ARR 配置中的 `DisplayConfiguration.vsyncPeriod` 表示 TE 信号周期；面板可以在满足 `minFrameIntervalNs` 的前提下，选择 TE/VSync 周期的离散倍数来展示下一帧。Android 17 中，`FRAME_RATE_CATEGORY_*`、`requestedFrameRate` 以及平台的启发式分类可参与 ARR 决策。

ARR 减少了频繁切换离散模式的需求，却不会消除应用自身的帧生产抖动、错误的 presentation timestamp（期望显示时间戳）、GPU 超预算或 HWC 合成延迟。排查时仍要把“应用生产”“SurfaceFlinger 合成”“显示消费”分开观察。

### 2. 无缝切换的契约

#### 2.1 `configGroup` 表达什么

Composer3 的 `DisplayConfiguration.configGroup` 是显示配置分组标识。同组配置除 VSync 周期外，其余属性应当相似，Android 可以据此识别“只改变刷新率”的候选配置。

同组是请求无缝切换的必要条件，但不是硬件一定能在当前时刻无缝切换的保证。Composer3 对两类失败作了区分：

- `EX_SEAMLESS_NOT_ALLOWED`：请求要求无缝，但目标配置与当前配置不在同一组；
- `EX_SEAMLESS_NOT_POSSIBLE`：配置关系允许无缝切换，但显示硬件在当前条件下无法避免可见伪影。

当条件变化后，Composer HAL 可以通过 `onSeamlessPossible` 回调通知客户端重试。应用不应假设“同分辨率”或“同组”就必然立即切换成功。

#### 2.2 应用如何表达是否接受非无缝切换

三参数 `Surface.setFrameRate()` 的 `changeFrameRateStrategy` 决定应用是否接受可能出现可见中断的模式切换。下面的调用用于声明固定帧率视频只接受无缝切换：

```kotlin
videoSurface.setFrameRate(
    sourceFrameRate,
    Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
    Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS
)
```

这段调用说明视频源帧率固定，并且当前内容只接受无缝模式切换。它是偏好，不是强制命令。

对于长时间播放的电影，应用可以在用户也开启“匹配内容帧率”的前提下使用 `CHANGE_FRAME_RATE_ALWAYS`。此时系统可以选择非无缝切换；开始或结束播放处可能出现显示中断。短视频、滚动列表中的自动播放内容通常不值得为此接受一次中断。

#### 2.3 `getAlternativeRefreshRates()` 的边界

Android 12/API 31 增加了 `Display.Mode.getAlternativeRefreshRates()`。返回值表示：如果系统在当前模式与这些刷新率之间切换，该切换保证无缝。它不承诺系统会切换，也不绕过显示策略。

只想表达刷新率偏好时，应优先使用 `Surface.setFrameRate()` 或 `WindowManager.LayoutParams.preferredRefreshRate`。`preferredDisplayModeId` 还会绑定分辨率等模式属性，更适合确实需要指定某个显示模式的场景。

### 3. Android 17 的模式切换状态机

从诊断角度，可以把 Android 17 的显示模式请求分成 `desired`（已选目标）、`pending`（已提交、待完成）和 `active`（当前生效）三个阶段。这套模型能解释“选择已经发生，但 SurfaceFlinger 还没有把目标模式记为 active”的 trace。

源码中的内部状态还受 `modeset_state_machine` 平台 flag（功能开关）控制。启用新状态机时，`pendingModeOpt` 明确保存待完成请求；旧路径还会使用 `isModeSetPending`。flag 会改变请求合并、pending 保存和完成清理的实现。下面的三阶段模型及四组 trace 计数器仍适合跨设备定位问题，但不能据此假定所有 Android 17 系统镜像都走相同的内部代码分支。

```text
Layer 请求 / 内容检测 / 系统策略
                │
                ▼
      RefreshRateSelector 选出候选
                │
                ▼
             desired
                │  提交给 HWC
                ▼
             pending
                │  立即完成，或等待刷新帧退出 pending
                ▼
             active
```

图中的 `desired` 表示策略选择结果，`pending` 表示已经提交但尚未完成，`active` 表示当前生效模式。三者的时间差是判断切换延迟的重点。

#### 3.1 选择候选模式

`RefreshRateSelector` 对 Layer 需求、显示策略和全局信号进行评分。Android 17 源码没有一张固定的“视频最高、动画居中、静态最低”优先级表；结果取决于投票类型、焦点、候选模式、无缝约束和策略范围。

`Surface.setFrameRate()` 的兼容性参数在 `LayerHistory` 中映射为不同投票：

| 应用参数 | SurfaceFlinger 投票语义 | 适用内容 |
|---|---|---|
| `FRAME_RATE_COMPATIBILITY_DEFAULT` | `ExplicitDefault` | 游戏及一般渲染 |
| `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` | `ExactOrMultiple` | 固定帧率视频 |
| `FRAME_RATE_COMPATIBILITY_AT_LEAST` | `Gte`（greater than or equal，不低于请求值）；MRR 上按高刷新倾向处理 | UI 动画、滚动、fling |

`AT_LEAST` 从 API 36 提供，适合 UI 动画一类“显示刷新率至少达到请求值”的需求。它不适合作为普通游戏的默认选择；游戏应先使用 `DEFAULT`，再根据稳定帧率和功耗目标调整请求。

#### 3.2 `desired`：记录最新请求

SurfaceFlinger 调用 `DisplayModeController::setDesiredMode()`。同一帧内出现多个请求时，控制器保留最新的 desired 请求，后续在合成边界处理。

若需要物理模式切换，`SurfaceFlinger::setDesiredMode()` 会：

- 请求调度下一次合成；
- 让 Scheduler 针对目标模式重新同步 VSync 预测模型；
- 通过 `VsyncModulator` 进入刷新率变化期间的调度状态；
- 标记有待处理的模式变化。

这里表示系统准备切换，尚不能说明硬件已采用新模式。

#### 3.3 `pending`：向 Composer HAL 发起切换

`SurfaceFlinger::initiateDisplayModeChanges()` 构造 `VsyncPeriodChangeConstraints`（VSync 周期切换约束）：

- `desiredTimeNanos`：`CLOCK_MONOTONIC`（系统单调时钟）时间点；显示周期不得早于该时间改变；
- `seamlessRequired`：这次切换是否必须无缝。

Android 17 的 `DisplayModeController::initiateModeChange()` 会根据 Composer 能力选择两条路径：

- Composer 不支持 DisplayCommand modeset：调用 `setActiveModeWithConstraints()`，向 HAL 请求受约束的 active config（当前生效配置）切换，并接收 `VsyncPeriodChangeTimeline`；
- Composer 支持 DisplayCommand modeset：调用 `setDisplayMode()`，由 `DisplayCommand.activeConfig` 携带目标 config 和 `seamlessRequired`。源码把成功结果视为立即生效，设置 `refreshRequired = false`，并以当前 `systemTime()` 填入 `newVsyncAppliedTimeNanos`。

受约束切换路径返回的 `VsyncPeriodChangeTimeline` 是硬件预计的周期切换时间线，包含：

- `newVsyncAppliedTimeNanos`：硬件预计开始使用新周期的时间；
- `refreshRequired`：切换前是否需要客户端再提交一帧；
- `refreshTimeNanos`：需要提交该帧的预计时间。

Scheduler 使用时间线调整 VSync 预测。如果 `refreshRequired` 为真，SurfaceFlinger 会安排相应的合成；Composer 后续也可以通过 timing-changed（切换时间变化）回调更新这条时间线。DisplayCommand 分支以及其他返回 `refreshRequired = false` 的成功路径会直接调用 `finalizeDisplayModeChange()`，不进入刷新帧等待。

#### 3.4 `active`：完成平台侧状态更新

需要刷新帧的模式切换不会在命令提交后立即被记为 active。Android 17 的 commit（提交）路径通过 `FrameTarget::isFramePending()` 检查相关前序显示提交；该状态包含 present fence 的完成情况：

- `FrameTarget` 仍 pending：安排下一帧，继续等待；
- `FrameTarget` 退出待定状态：调用 `finalizeDisplayModeChange()`；
- 完成后更新 active mode、active render rate 和 `RefreshRateSelector` 的当前模式。

DisplayCommand modeset 成功且 `refreshRequired = false` 时不经过这段等待，SurfaceFlinger 会立即 finalize（完成状态更新）。对于需要等待的路径，present fence 给出了“对应显示提交已经完成”的时序证据，通常比请求发起时间更接近用户看到新模式的时刻；它仍不能独立测量面板内部时序。

#### 3.5 分辨率切换要单独分析

跨配置组切换可能同时改变分辨率。Android 17 在完成模式切换时会区分纯刷新率变化和分辨率变化；后者还可能触发 `DisplayDevice` 或 framebuffer（帧缓冲）相关重建。

跨分辨率模式切换的代价不能套用纯 60 Hz → 120 Hz 刷新率切换的结论。trace、`dumpsys` 和 HWC 日志都应同时记录模式 ID、分辨率、`configGroup` 与刷新率。

### 4. 切换附近为什么会出现卡顿

#### 4.1 帧预算突然改变

从 60 Hz 切到 120 Hz 后，一次刷新周期从约 16.67 ms 变为约 8.33 ms。即使硬件完成无缝切换，应用的 CPU 与 GPU 负载若只能稳定在 60 fps，画面也不会自动变成稳定 120 fps。

游戏尤其需要区分：

- 屏幕已经在 120 Hz；
- 游戏请求了 120 FPS；
- 游戏引擎能否持续按 8.33 ms 预算生产帧。

第三项需要用 FrameTimeline、CPU/GPU slice（时间片段）和 present timing（显示时序）证明，不能由 display mode 推断。

#### 4.2 受约束切换的 HAL 时间线可能要求额外刷新帧

`setActiveModeWithConstraints()` 路径中的某些显示实现需要 SurfaceFlinger 在切换前发送一帧，Composer HAL 会通过 `refreshRequired` 和 `refreshTimeNanos` 明确表达。若该帧准备、合成或显示较晚，切换窗口附近会出现较长帧。Android 17 的 DisplayCommand modeset 成功路径明确填写 `refreshRequired = false`，不能把“额外刷新帧”当成所有模式切换的固定步骤。

这里没有固定的“一到三帧”规则。持续时间取决于面板、显示控制器、Composer 实现、当前队列和切换类型，必须从目标设备的 trace 与 HAL 证据得出。

#### 4.3 非无缝切换可以产生可见中断

电视、机顶盒及部分面板在切换模式时可能黑屏。Android 默认不会仅因 `setFrameRate()` 请求而选择这类非无缝切换；应用和用户都允许后，系统才可以采用。

把这种显示中断记作应用掉帧会误导优化方向。应用时间线可能平稳，显示输出却在模式重配置期间不可见。

#### 4.4 模式切换和队列抖动可能同时发生

应用开始播放视频或进入战斗场景时，通常会同时发生资源加载、解码器启动、Surface 更新和帧率请求。一次 trace 中，“切换计数器变化”和“jank（卡顿）帧”相邻只能说明时间接近，不能直接证明因果。

确认因果至少要回答：

1. 新模式请求何时进入目标状态；
2. 何时进入 pending，何时成为 active；
3. jank 帧阻塞在应用、GPU、SurfaceFlinger 还是显示阶段；
4. 对照实验中禁用模式切换后，其他工作负载是否保持不变。

### 5. 应用如何提交正确的帧率请求

#### 5.1 视频：提交源的准确帧率

视频应提交准确源帧率，不要把 29.97 四舍五入为 30：

```kotlin
fun updateVideoFrameRate(
    surface: Surface,
    sourceFrameRate: Float,
    allowNonSeamlessSwitch: Boolean
) {
    val strategy = if (allowNonSeamlessSwitch) {
        Surface.CHANGE_FRAME_RATE_ALWAYS
    } else {
        Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS
    }

    surface.setFrameRate(
        sourceFrameRate,
        Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
        strategy
    )
}
```

`FIXED_SOURCE` 告诉系统源帧率不可自由调整，系统可以选择该帧率的整数倍，例如 24 FPS 内容可匹配 48 Hz、72 Hz 或 120 Hz。最终结果仍由设备模式和系统策略决定。

视频 Surface 仍然可见但已经暂停，或播放完毕并停止提交 buffer 时，应传入 0，或在 API 34 以上调用 `clearFrameRate()` 清除偏好。Surface 已销毁或因切换应用而隐藏时，无需额外清除。

播放端还要设置正确的 presentation timestamp。即使系统没有采用请求的刷新率，显示系统也能据此避免过早展示帧，并按可用周期转换节拍。

#### 5.2 游戏：请求可持续的目标

游戏通常使用 `FRAME_RATE_COMPATIBILITY_DEFAULT`：

```kotlin
gameSurface.setFrameRate(
    targetFps,
    Surface.FRAME_RATE_COMPATIBILITY_DEFAULT,
    Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS
)
```

这段调用适合游戏在画质档、场景或热状态变化后更新目标帧率。不要在每一帧重复调用，也不要为了得到高刷新率把游戏伪装成固定帧率视频。

从 Android 15 开始，系统对游戏的默认刷新率可能限制为 60 Hz；需要高刷新率的游戏应主动请求。请求值应来自可持续的渲染能力，并配合 Android Frame Pacing Library（Swappy，帧节奏控制库）或等价的 present timing 控制。屏幕进入 120 Hz 后仍以不规则节奏提交 70～100 FPS，不会得到稳定的 120 FPS 观感。

#### 5.3 普通 UI：让 View 系统表达分类

Android 17 上，普通 View/Compose UI 优先使用框架提供的 ARR 与 View 帧率分类能力。若有明确的自定义动画需求，可对合适的 View 使用 `requestedFrameRate` 或 frame-rate category（帧率类别）。

直接对 Window 或 Surface 设置长期高帧率偏好，会影响整个 Surface。只有一个局部动画时，这个请求范围往往过大。调用频率也要受控：在场景状态变化时更新，不要跟随每一帧的瞬时耗时来回请求。

#### 5.4 多 Surface：分别报告各自内容

画中画、分屏、视频控件加 UI 覆盖层时，各 Surface 应报告自身内容帧率。不要把多个 Surface 的需求预先合成一个值再提交给所有 Surface。

SurfaceFlinger 负责在多个 Layer 之间选择显示模式。应用若把 UI、视频和游戏画面全部写成同一个高帧率，会丢失内容信息，也会让系统无法做出合理选择。

### 6. 用 Perfetto 判断切换发生在哪里

#### 6.1 先看 Android 17 的四组显示计数器

`DisplayModeController` 为每个物理显示创建以下计数器：

- `HasDesiredMode <physical-display-id>`
- `PendingModeFps <physical-display-id>`
- `ActiveModeFps <physical-display-id>`
- `RenderRateFps <physical-display-id>`

下面的查询用于列出这些计数器的变化。它的目的，是把请求、待完成模式、活动模式和渲染节奏放到同一时间轴：

```sql
SELECT
  t.name,
  c.ts,
  c.value
FROM counter AS c
JOIN counter_track AS t
  ON c.track_id = t.id
WHERE t.name GLOB 'HasDesiredMode *'
   OR t.name GLOB 'PendingModeFps *'
   OR t.name GLOB 'ActiveModeFps *'
   OR t.name GLOB 'RenderRateFps *'
ORDER BY c.ts;
```

读数时注意：

- `HasDesiredMode` 变化：存在尚未提交或合并处理的目标请求；
- `PendingModeFps` 变化：物理模式切换已经提交到显示路径，仍在等待完成；
- `ActiveModeFps` 变化：SurfaceFlinger 已完成模式状态更新；
- 只有 `RenderRateFps` 变化：可能只是调度节奏变化，没有发生物理 modeset。

计数器名字包含 physical display ID（物理显示标识）。折叠屏、外接屏或虚拟显示场景中，先确认分析的是哪块物理显示。

#### 6.2 再看选择过程

SurfaceFlinger 的 trace 中可见 `Refresh Rate Selection` 一类选择区间。它适合回答“为什么候选模式改变”，但选择区间结束不等于面板完成切换。

分析顺序建议固定为：

1. 找到用户可见的 jank 帧；
2. 查看相邻时间内的 `HasDesiredMode` 和选择事件；
3. 查看 `PendingModeFps` 到 `ActiveModeFps` 的间隔；
4. 对齐 SurfaceFlinger commit、present fence 和 FrameTimeline；
5. 回到应用、RenderThread、GPU/HWC 路径确定最长阶段。

#### 6.3 FrameTimeline 回答帧卡在哪里

FrameTimeline 可以区分应用生产帧和 SurfaceFlinger 展示帧的 deadline（截止时间）。常见组合包括：

| 证据 | 更可能的方向 |
|---|---|
| 应用帧已 missed（错过截止时间），模式计数器无变化 | 应用 CPU/GPU 或帧节奏问题 |
| 应用按时完成，SurfaceFlinger 帧 missed，恰有 pending 窗口 | 继续检查 HWC、present fence 和切换时间线 |
| `ActiveModeFps` 已改变，后续应用连续 missed | 新帧预算下应用负载过高 |
| 只有 `RenderRateFps` 改变 | 先按调度/帧节奏问题分析，不要归因于 modeset |

Perfetto 展示的是时序证据。某个 OEM（设备厂商）是否在显示驱动内执行 PLL 重配置、面板命令序列如何安排，要用该设备的 Composer、内核或固件资料确认，不能由通用 AOSP trace 名称推断。

#### 6.4 `dumpsys` 适合看快照

`dumpsys SurfaceFlinger` 和 `dumpsys display` 可用于确认当前 active mode、策略范围和支持模式。`dumpsys` 输出是采样时刻的状态快照，不适合测量一次短暂切换的起止时间。

开发者选项中的“显示刷新率”overlay（屏幕叠加层）也只适合快速确认当前值。做因果分析时，仍以 Perfetto 计数器、FrameTimeline 和显示路径 fence 为准。

### 7. 三个常见场景

#### 7.1 视频开始或暂停

视频开始播放时，播放器设置准确源帧率，SurfaceFlinger 可能选择匹配模式或其整数倍。若只允许无缝切换，系统也可能保持当前模式。

暂停后：

- Surface 继续可见且不再提交帧：清除帧率偏好；
- Surface 隐藏或销毁：无需额外清除；
- 暂停画面上仍有 UI 动画：UI Surface 应继续提交自己的需求。

诊断时同时记录解码器启动和首帧提交。首帧慢与显示模式切换可以落在同一个时间窗口。

#### 7.2 游戏菜单进入战斗

菜单可能稳定在较低帧率，战斗场景请求更高帧率。切换前先确认目标帧率能否持续达到；否则显示进入高刷新模式后，GPU 仍会不断错过更短的 deadline。

比较实验应至少保留：

- 相同画质和负载，只固定显示模式；
- 相同显示模式，只改变游戏目标帧率；
- 同时查看 `ActiveModeFps`、FrameTimeline 和 GPU 完成时间。

这样才能区分“模式切换瞬间的显示延迟”和“高刷新率下长期性能不足”。

#### 7.3 相机与系统转场

不能把“相机一定运行在 60 Hz、桌面一定运行在 120 Hz”当作平台规则。相机预览帧率、相机应用的 Surface 请求、系统动画、厂商显示策略和面板能力都会改变结果。

从相机进入多任务时，应先用 trace 确认是否有 `PendingModeFps` 和 `ActiveModeFps` 变化。如果没有物理模式变化，就应继续检查预览 Surface 消失、窗口动画、GPU 合成和 RenderThread，而不能按刷新率切换问题修复。

### 8. 平台、HAL 与内核的责任边界

Android 17 平台锚点 `android-17.0.0_r1` 能确认：

- SurfaceFlinger 如何选择和记录模式请求；
- Composer3 约束与时间线怎样传递；
- Scheduler 如何调整 VSync 预测；
- present fence 如何参与模式完成确认。

内核锚点 `android17-6.18-2026-06_r6` 中，主线 DRM（Linux 显示管理框架）的 `drm_vblank.c`、atomic modeset helper（原子模式设置辅助代码）和 DMA fence 提供了 VBlank（垂直消隐期）、原子提交与 fence 的通用实现参考。但量产 Android 设备常使用厂商显示驱动、专用 Composer 实现和面板固件。

因此，下面这些结论必须来自目标设备：

- 一次模式切换是否重配 PLL；
- 面板是否需要特定命令序列或空白期；
- HWC 何时返回 `refreshRequired`；
- 非无缝切换的可见时长；
- 驱动如何标记和追踪模式提交。

AOSP 给出契约与上层状态机，内核和厂商实现决定具体硬件时序。

### 9. 排查清单

1. 记录设备支持模式、当前模式、`configGroup` 和系统刷新率设置。
2. 明确应用设置帧率的 Surface、准确值、compatibility 和 change strategy。
3. 在 Perfetto 中定位 `HasDesiredMode`、`PendingModeFps`、`ActiveModeFps`、`RenderRateFps`。
4. 用 FrameTimeline 判断应用还是 SurfaceFlinger 错过截止时间。
5. 对齐 HWC 与 present fence，确认模式何时完成。
6. 区分纯刷新率切换、跨分辨率切换、render rate 调整和 ARR 刷新节奏变化。
7. 在目标设备上核对 Composer 与内核日志，不用芯片平台经验替代证据。
8. 固定显示模式做对照实验，避免把同时发生的解码、加载或 GPU 压力误归因给 modeset。

### 常见误区

#### 误区一：`setFrameRate(60)` 会把屏幕固定到 60 Hz

它是内容偏好。系统可能选择 60 Hz、可整除的更高刷新率，或因策略限制保持当前模式。

#### 误区二：同组模式一定能立即无缝切换

同组只满足配置关系约束。当前硬件条件不允许时，HAL 仍可返回 `EX_SEAMLESS_NOT_POSSIBLE`。

#### 误区三：看到 VSync 周期变化就说明发生了 modeset

ARR 或 render rate 调整也会改变调度观测。需要 `PendingModeFps`、`ActiveModeFps` 和显示路径证据确认 MRR modeset。

#### 误区四：高刷新率一定更流畅

高刷新率缩短了帧预算。应用若不能稳定生产帧，呈现间隔仍会抖动，还会增加功耗。

#### 误区五：相机、多任务、游戏都有固定刷新率

Android 平台没有这种通用映射。结果由内容请求、系统策略、设备模式和厂商实现共同决定。

#### 误区六：一次相邻事件足以证明因果

模式计数器变化与 jank 帧相邻只能作为线索。还要检查 pending 窗口、FrameTimeline 阶段、present fence，并做控制变量实验。

## RefreshRateSelector 的候选模式与评分

Android 17 把多类投票转成候选模式分数。复现模式选择时，需要同时保存 layer vote、触摸状态、idle timer、设备配置和最终得分。

以下分析以 AOSP `android-17.0.0_r1` 为平台锚点，以通用内核 `android17-6.18-2026-06_r6` 为内核锚点。文中只陈述可由 Android 17 源码确认的行为；面板切换耗时、显示驱动跟踪点和功耗收益仍由具体设备实现决定。

本章主要核对三组源码：`DisplayModeController` 判断目标模式无需处理、只需更新渲染节拍、可以合并到待处理请求，还是必须切换物理模式；SurfaceFlinger 的帧调度器 Scheduler 通过 `RefreshRateSelector` 同时接收图层投票、全局信号与 DisplayManager 策略；`FrameRateOverrideMappings` 维护按 UID 生效的帧率覆盖，其中内部接口直接写入的覆盖值优先于根据内容计算的覆盖值。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp, Scheduler/RefreshRateSelector.cpp, Scheduler/FrameRateOverrideMappings.cpp @ android-17.0.0_r1]

### 1. Android 17 的选择链路

Android 17 的决策路径可以压缩为以下顺序：

1. DisplayManager 策略给出默认模式、主范围、应用请求范围，以及是否允许跨模式组。
2. `LayerHistory` 根据活动图层、显式 `setFrameRate()`、内容检测、帧率类别和游戏模式干预，生成表示图层需求的 `LayerRequirement`。
3. `Scheduler::chooseDisplayModes()` 为各物理显示器调用 `RefreshRateSelector`，得到排序后的 `FrameRateMode`。
4. `Scheduler::applyPolicy()` 把选中结果包装成 `DisplayModeRequest`，经回调交给 SurfaceFlinger。
5. `SurfaceFlinger::setDesiredMode()` 调用 `DisplayModeController::setDesiredMode()`，按返回的 `DesiredModeAction` 更新渲染帧率，或发起物理模式切换。
6. 需要更换模式 ID 时，`DisplayModeController::initiateModeChange()` 通过 Composer 调用 HWC；切换完成后再更新活动模式、VSYNC 模型和显示事件。

在这条路径中，DisplayManager 策略划定允许范围，图层投票（vote）表达内容偏好，Scheduler 负责排列候选顺序，`DisplayModeController` 负责执行。`DisplayModeRequest` 是 SurfaceFlinger 内部请求，并非应用可以直接提交的公共接口。

排障时可以按照“策略边界 → 图层需求 → 评分排名 → 执行动作”拆分日志：策略只决定候选集合，`LayerHistory` 决定每个可见图层的投票，`getRankedFrameRatesLocked()` 再把投票、触摸、空闲、点亮等全局信号和并列裁决规则（tie-break）合成排序结果。最终是否调用 HWC（硬件合成器）设置物理模式，还要看 `DisplayModeController::setDesiredMode()` 返回的动作。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp, Display/DisplayModeController.cpp @ android-17.0.0_r1]

#### 1.1 策略包含两层范围

`RefreshRateSelector::Policy`（选择策略）的两个主要字段是 `primaryRanges` 与 `appRequestRanges`：

- `primaryRanges` 是常态选择区域；
- `appRequestRanges` 可以更宽，显式图层请求在满足条件时允许离开主范围；
- 候选始终不能越过应用请求范围；
- `allowGroupSwitching` 决定能否考虑其他模式组。一个模式组通常收纳可以无缝互切的模式，因此源码把“是否同组”作为判断无缝切换的重要条件。

每个范围又分为 `physical` 与 `render`。前者约束物理模式的峰值刷新率 `DisplayMode::getPeakFps()`，后者约束渲染节拍 `FrameRateMode::fps`。“允许选择 120 Hz 物理模式”不等于“应用一定会以 120 fps 收到回调”。

### 2. 候选不等于一张简单的模式表

#### 2.1 `DisplayMode` 保存什么

Android 17 的 `DisplayMode` 保存模式 ID、HWC 配置 ID、分辨率、DPI（像素密度）、模式组、VSYNC 频率、可选的 VRR 配置和 HDR 输出类型。`getPeakFps()` 的定义如下：

- 没有 VRR 配置：峰值刷新率等于 `mVsyncRate`；
- 有 VRR 配置：峰值刷新率由 `minFrameIntervalNs` 换算。

因此，在 ARR（Android 自适应刷新率）或 VRR 设备上，`getVsyncRate()`、`getPeakFps()` 和当前 `FrameRateMode::fps` 代表不同层次，不能互相替代。

#### 2.2 构造候选时的过滤

`constructAvailableRefreshRates()` 以策略中的默认模式为基准，过滤条件包括：

- 分辨率与默认模式相同；
- DPI 与默认模式相同；
- 模式组满足策略；
- 峰值刷新率位于物理范围；
- 渲染帧率位于渲染范围；关闭帧率覆盖时，物理峰值也要满足渲染范围；
- 开启 `enable_user_preferred_hdr_mode` 时，HDR 输出类型与默认模式相同。

选择器分别构造 `mPrimaryFrameRates`、`mAppRequestFrameRates` 和 `mAllFrameRates`。实际参与图层评分的主要集合是 `mAppRequestFrameRates`，并非设备公布的所有模式。

#### 2.3 MRR 与 VRR 生成渲染帧率候选的方式不同

MRR 指通过多个固定刷新率模式进行切换的传统方式，VRR 则允许显示器在可变范围内调整刷新节拍。`createFrameRateModes()` 会为每个通过过滤的 `DisplayMode` 生成一个或多个渲染帧率，源码用 divisor（除数）表示“物理频率每经过多少个周期产生一次渲染节拍”：

- 帧率覆盖关闭时，只生成除数 1，也就是渲染节拍与物理频率相同；
- 没有 VRR 配置的模式按 VSYNC 频率的整数除数枚举；除数大于 1 时，低于 20 Hz 的候选会被截掉；
- 有 VRR 配置的模式先使用除数集合 `{1, 2, 5, 10, 15, 20, 24, 30, 48, 60}`，再加入范围端点，并在最大间隙中补充候选，最多形成 15 个除数；
- 同一个渲染帧率、同一个组出现多个物理模式时，通常保留物理峰值更低的那个；主物理范围是单值时，优先保留该范围内的模式。

这里的 VRR 候选不表示面板能在 1 Hz 到 120 Hz 之间任意连续取值。它是 SurfaceFlinger 为调度和帧率覆盖建立的一组离散 `FrameRateMode`，仍然受 HWC 能力与设备策略约束。

### 3. 图层投票从哪里来

#### 3.1 公共兼容性参数与内部投票使用不同枚举

`FrameRateCompatibility.h` 描述图层提交帧率时声明的兼容方式；评分阶段使用的是内部枚举 `RefreshRateSelector::LayerVoteType`。Android 17 中后者包含：

`NoVote`、`Min`、`Max`、`Heuristic`、`ExplicitDefault`、`ExplicitExactOrMultiple`、`ExplicitExact`、`ExplicitGte`、`ExplicitCategory`。

`LayerHistory` 的主要映射如下：

| 图层兼容性或来源 | VRR 或 ARR 显示器 | MRR 显示器 |
|---|---|---|
| `Default` | `ExplicitDefault` | `ExplicitDefault` |
| `Min` | `Min` | `Min` |
| `ExactOrMultiple` | `ExplicitExactOrMultiple` | `ExplicitExactOrMultiple` |
| `Exact` | `ExplicitExact` | `ExplicitExact` |
| `Gte` | `ExplicitGte` | `Max` |
| `NoVote` | `NoVote` | `NoVote` |
| 未显式指定、由内容检测估算 | `Heuristic` | `Heuristic` |

`Gte` 在 MRR 显示器上会转换为 `Max`。源码注释给出的理由是，滚动和动画更看重平滑度，而 MRR 无法像 ARR 那样在同一个模式内平滑改变渲染节拍。

Java 公共常量 `FRAME_RATE_COMPATIBILITY_AT_LEAST` 进入原生图层后，对应这里的 `Gte` 语义。应用层名称与选择器内部枚举不同，读取系统跟踪或状态转储时要按照这张表转换。

#### 3.2 游戏模式干预的优先级

游戏模式的两个值保存在 `LayerHistory::mGameFrameRateOverride`，每个 UID 对应一个系统干预帧率和一个游戏默认帧率。活动图层按以下优先级选择帧率意见：

1. 有效的游戏模式干预值；
2. 应用自己的 `setFrameRate()` 或帧率类别；
3. 游戏默认帧率；
4. 在 ARR 上仍有效、但在 MRR 上不适用的其他意见；
5. 没有可用意见时恢复普通内容检测。

这可以解释游戏请求 90 fps、系统却稳定给出 60 fps 的情况。若设备配置了 FPS 限速干预，平台侧意见会优先于应用投票。排障时应同时检查游戏模式、应用请求和当前渲染帧率。

### 4. 排名不是一个通用公式

旧资料常把 `RefreshRateSelector` 简化为“计算目标值与候选值的距离，再累加所有图层的分数”。Android 17 会按照投票类型进入不同分支，距离分只适用于其中一部分。

阅读源码时，不能把连续数值评分理解成唯一公式。Android 17 确实在多个分支使用距离或比例分数，但 `ExplicitCategory`、`ExplicitExact`、`ExplicitDefault`、触摸后的延迟升频、空闲状态的提前返回，以及分数相同后的高低帧率偏好，都会改变最终顺序。因此，一次异常只能结合具体投票类型和当时的全局信号解释，不能只用“目标帧率越近，得分越高”概括。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp @ android-17.0.0_r1]

#### 4.1 距离分的含义

`calculateDistanceScoreLocked(reference, refresh)` 会先用两个帧率中的较小值除以较大值，再对比值求平方：

`score = (min(reference, refresh) / max(reference, refresh))²`

结果位于 0 到 1 之间。两个帧率相等时结果为 1，偏离越大，分数越低。这个函数用于 `Max`、`ExplicitGte` 未达到下限时，以及部分类别的边界匹配；它不能代表所有投票的评分方式。

#### 4.2 各类投票的评分规则

| 投票类型 | Android 17 的主要行为 |
|---|---|
| `ExplicitCategory` | 候选落入类别范围时得 1 分；落在范围外时按边界做非精确匹配；`HighHint` 用作触摸升频提示 |
| `Max` | 候选越接近应用请求集合的最高渲染帧率，距离分越高 |
| `ExplicitExact` | 支持内容帧率覆盖时，目标帧率的整数倍可以得分；不支持时只接受除数 1 |
| `ExplicitGte` | 达到或高于目标得 1；低于目标时按距离降分 |
| `ExplicitDefault` | 可以接受非整数倍，但会按节拍匹配质量降分 |
| `ExplicitExactOrMultiple`、`Heuristic` | 整数倍得高分；59.94 与 60 一类分数帧率对可得 0.8；其他比例按最多 10 个显示帧的拟合结果评分 |
| `Min`、`NoVote`、`NoPreference` | 在常规逐图层评分循环中跳过，并由专门分支处理 |

整数倍匹配还会考虑能否无缝切换：跨组的非无缝候选乘以 `0.95`，非精确匹配再乘以一个 `0.95`。焦点图层、允许的切换类型、主范围以及当前模式组和默认模式组，都可能使某个候选不参与该图层的评分。

每个图层的贡献是 `layer.weight × layerScore`，也就是图层权重乘以该候选在此图层上的得分。固定源图层低于设备配置的倍数阈值时，源码会把阈值以上和阈值以下的分数暂存到两个集合，再根据其他图层是否已经让最佳模式超过阈值，决定是否合入高刷新率一侧的分数。这样既能避免 24 fps 视频单独让显示器长期保持过高的物理刷新率，也允许 UI 或其他内容推动系统选择高刷新率。

分数相同也不是随机选：

- 没有 `Max` 投票时，平分候选倾向较低渲染帧率；
- 存在 `Max` 投票时，平分候选按高帧率优先；
- 没有图层得到有效分数时，选择器还会尝试保留当前配置，或回到主范围。

#### 4.3 评分前后的全局信号

`getRankedFrameRatesLocked()` 有多条早返回和后处理分支：

- 跟随显示器在相关开关关闭时，尝试跟随节奏基准显示器的峰值帧率；
- `powerOnImminent` 选择当前组的最高候选；
- 有触摸且没有显式投票时直接选择高候选；
- 空闲且不满足“单值主范围 + 显式投票”例外时选择低候选；
- 没有有效投票时选择当前锚点组的高候选；
- 所有图层都是 `NoPreference` 时保留活动的 `FrameRateMode`；
- 所有图层都是 `Min` 或 `NoVote` 时选择低候选。

有显式投票时，是否因触摸升频要等评分完成后再判断。`ExplicitDefault` 常用于游戏限帧，因此会阻止全局触摸信号直接覆盖该请求。只有同一 UID 没有 `ExplicitDefault` 时，`HighHint` 才会作为应用侧的触摸升频提示。

“触摸一律 120 Hz”或“空闲一律最低 Hz”都不符合源码。两种信号还要经过策略、模式组、显式投票、显示器类型和候选集合的约束。

### 5. 多显示器与节奏基准显示器

Scheduler 会为多个物理显示器生成选择结果。节奏基准显示器（pacesetter）提供全局调度参照；跟随显示器能否独立选择，取决于 `follower_arbitrary_refresh_rate_selection_combined` 等平台配置。

在旧路径中，跟随显示器收到有效的 `pacesetterFps` 时，会先在活动模式组内寻找峰值帧率相同的候选，找不到时才继续常规选择。新路径允许综合考虑多个显示器，但仍不能假定内屏和外接屏完全独立。分析投屏、桌面模式或双屏设备时，应分别记录：

- 每个显示器的物理 ID、活动模式 ID 和组；
- 哪块显示器是节奏基准；
- 各显示器的 `ActiveModeFps` 和 `RenderRateFps`；
- 每个显示器自己的送显栅栏和 FrameTimeline。

不要用默认屏的一条 VSYNC 或送显栅栏解释外接屏。

### 6. `DisplayModeController` 怎样执行选择结果

#### 6.1 `DesiredModeAction` 表示本次调用要执行的动作

`DisplayModeController::setDesiredMode()` 返回四种动作：

| 动作 | 触发条件概括 | SurfaceFlinger 的处理 |
|---|---|---|
| `None` | 模式 ID 与渲染帧率都不需要变化 | 不安排切换 |
| `InitiateRenderRateSwitch` | 模式 ID 不变，只改变 `FrameRateMode::fps` | 更新 Scheduler 的渲染帧率与相位配置，按需发送事件 |
| `MergeDisplayModeSwitch` | 已有目标请求，新的请求可合并 | 更新目标；启用模式设置状态机时重新同步到峰值渲染帧率 |
| `InitiateDisplayModeSwitch` | 需要更换模式 ID，或请求要求强制执行 | 安排合成、重同步硬件 VSYNC、调制 VSYNC，并标记模式切换待处理 |

这四个值是 `setDesiredMode()` 对本次调用返回的动作分类，不是必须依次经过的四个状态。例如，只改变渲染帧率时，不会进入物理模式切换路径。

发起物理切换前，控制器会暂时把当前模式的渲染帧率恢复到峰值，使下一帧尽早进入调度。启用 `modeset_state_machine` 后，`desiredModeOpt` 表示尚未交给 HWC 的目标请求，`pendingModeOpt` 表示已经交给 HWC、正在等待完成的请求；新请求能否合并还取决于分辨率是否兼容。

`setDesiredMode()` 依次进行三项判断：先检查是否已有可合并且尚未处理的 `desiredModeOpt`；若目标模式 ID 已经处于活动状态，再判断是否只需切换渲染帧率；其余情况才创建物理显示模式请求。启用 `modeset_state_machine()` 后，`pendingModeOpt` 与 `desiredModeOpt` 分开保存，避免已经交给 HWC 的请求被后续请求覆盖。

#### 6.2 两条 Composer 与 HWC 路径

`initiateModeChange()` 会根据 Composer（SurfaceFlinger 到 HWC 的合成接口）能力选择以下路径：

- 不支持 DisplayCommand 模式设置时：调用 `setActiveModeWithConstraints()`，由 HAL 返回 `VsyncPeriodChangeTimeline`（VSYNC 周期变更时间线）；
- 支持 DisplayCommand 模式设置时：调用 `setDisplayMode()`；调用成功后，SurfaceFlinger 在该分支把 `refreshRequired` 设为 `false`，并把 `newVsyncAppliedTimeNanos` 设为当前 `systemTime()`。

源码中的“立即”只描述 SurfaceFlinger 在 DisplayCommand 成功分支中的状态处理，不能外推为“面板像素会在固定帧数内完成响应”。另一条路径的时间线由厂商 HAL 提供，AOSP 同样没有统一规定 1～3 帧的切换延迟。

取证时应分开记录两条 Composer 路径：`setActiveModeWithConstraints()` 的时间线来自 HAL 返回值；DisplayCommand 的 `setDisplayMode(seamlessRequired)` 成功后，SurfaceFlinger 在该分支把 `refreshRequired` 设为 `false`，并把 `newVsyncAppliedTimeNanos` 设为 `systemTime()`。后者只表示系统框架完成了这一步状态更新，不代表面板像素的光学响应已经完成。

#### 6.3 完成模式切换的边界

新的待处理模式通过检查后，`finalizeModeChange()` 会完成以下状态更新：

- 比较旧活动模式与待处理模式的分辨率；
- 更新选择器的活动模式 ID 与渲染帧率；
- 更新 `ActiveModeFps` 和 `RenderRateFps` 系统跟踪计数器；
- 分辨率相同返回 `RefreshRateChange`；
- 分辨率不同返回 `ResolutionChange`；
- 显示器、待处理请求或模式 ID 不合法时返回 `NoModeChange`。

分辨率切换还需要 DisplayManager 配合提交显示尺寸事务。`setDesiredMode()` 已经执行，并不代表分辨率事务、VSYNC 模型更新和应用事件通知都已完成。

### 7. UID 帧率覆盖与游戏模式使用不同的数据通路

`FrameRateOverrideMappings` 有两个映射表：

- `mFrameRateOverridesFromBackdoor`：由 `setPreferredRefreshRateForUid()` 写入；Android 17 的 SurfaceFlinger 内部事务 1039 可以触发它，源码将这类直接写入路径称为 backdoor，值为 0 表示删除；
- `mFrameRateOverridesByContent`：由 `RefreshRateSelector::getFrameRateOverrides()` 根据当前内容需求计算，再通过 `updateFrameRateOverridesByContent()` 整表替换。

查询某个 UID 时，内部接口直接写入的值优先。设备不支持内容帧率覆盖时，根据内容计算的映射表不会对外生效。

内容帧率覆盖用于在显示器保持某个物理刷新率时，按 UID 为应用事件回调选择一个可以整除该物理频率的较低渲染帧率。例如，120 Hz 可以按每两个物理周期一次回调得到 60 fps。MRR 分支不会给出低于 30 fps 的覆盖值；ARR 分支会从应用请求候选中保留能整除当前显示刷新率的值。某个 UID 含有 `Max` 或 `Heuristic` 图层、满足触摸升频条件，或者没有可评分意见时，也可能不生成覆盖值。

游戏模式干预值和游戏默认帧率不会写入这两个映射表。它们进入 `LayerHistory` 改变图层投票，再间接影响模式排名和后续的内容帧率覆盖计算。若把两者看成同一张 UID 表，就会混淆显示模式选择与应用回调限频。

如果正在排查“应用请求了 60 fps，但 UID 覆盖值不是 60”的问题，应先区分两个映射表：直接写入表按 UID 设置并优先返回，内容表则由选择器根据当前内容需求整体刷新。游戏模式干预不会直接写入这两个映射，而是先改变 `LayerHistory` 的投票，再间接影响模式选择与覆盖值生成。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Scheduler/FrameRateOverrideMappings.cpp, Scheduler/LayerHistory.cpp @ android-17.0.0_r1]

### 8. 内核空闲计时器的平台边界

内核空闲计时器用于在显示长时间没有更新时触发更低的刷新节奏；具体能否降频以及降到哪里由设备实现。`DisplayModeController` 支持两种配置通道：

- `HwcApi`：调用 Composer `setIdleTimerEnabled(displayId, timeout)`；
- `Sysprop`：通过系统属性 `graphics.display.kernel_idle_timer.enabled` 开关该能力。

`RefreshRateSelector::getIdleTimerAction()` 按以下条件判断应开启还是关闭：

- 设备最低值低于策略最低值：关闭，避免内核把刷新率降到策略不允许的值；
- 策略最低值与最高值指向同一模式：只有主物理范围最低值低于设备最低值时开启，否则关闭；
- 其他情况开启。

`VSyncReactor::onDisplayModeChanged()` 还明确排除了带 VRR 配置的模式：内核空闲计时器只在 `mSupportKernelIdleTimer && !modePtr->getVrrConfig()` 时参与周期切换。

通用内核 `android17-6.18-2026-06_r6` 提供 DRM 原子提交、垂直消隐、dma-fence 等通用机制，但没有为所有 Android 设备定义上述系统属性对应的统一显示驱动行为。属性由谁监听、能够降到哪个面板模式、切换是否闪屏、可以节省多少功耗，都要检查厂商 Composer、显示 HAL 和内核驱动。AOSP 这段代码只能证明控制入口与策略保护条件。

状态转储或系统跟踪中的内核空闲计时器状态变化，只能说明 SurfaceFlinger 已按照 `RefreshRateSelector::getIdleTimerAction()` 选择 HWC API 或系统属性通道。若活动模式带有 VRR 配置，`VSyncReactor::onDisplayModeChanged()` 还会把内核空闲计时器排除在周期切换之外。设备是否已经实际降频，仍需结合厂商 HAL、面板驱动或实测的送显与功耗数据判断。

### 9. 应用怎样表达需求

#### 9.1 Java `Surface.setFrameRate()`

下面的游戏或普通 UI 示例表示：“这个 `Surface` 偏好 60 fps，并且能够适应系统选择的其他帧率。”

```java
surface.setFrameRate(
        60f,
        Surface.FRAME_RATE_COMPATIBILITY_DEFAULT,
        Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

`DEFAULT` 适合游戏、UI 和非固定源内容。这个调用只向系统提供选择依据，不会限制应用的渲染循环，也不保证显示器立即切换到 60 Hz；应用仍应使用 `Choreographer`、Swappy 帧节奏库或引擎自身的帧节奏机制控制提交频率。

下面示例用于 24 fps 固定帧率视频：

```java
surface.setFrameRate(
        24f,
        Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
        Surface.CHANGE_FRAME_RATE_ALWAYS);
```

`FIXED_SOURCE` 告诉系统，24、48、72、96、120 Hz 这类整数倍频率通常更有利于稳定播放。`ALWAYS` 允许发生可能黑屏或闪烁的非无缝切换，适合切换收益足以抵消干扰的长视频；列表页中的短视频预览通常更适合 `ONLY_IF_SEAMLESS`。播放结束、`Surface` 改作其他用途或不再可见时，应调用 `surface.clearFrameRate()` 清除旧的帧率意见。

Android 17 还提供受功能开关控制的 `Surface.FrameRateParams`。源码中的 TODO 明确说明当前传递链路尚未完成：实现会在固定源帧率与最小、最大范围之间选择一种表达，不能仅根据 API 的字段形态推断完整区间语义已在所有设备上可用。生产代码使用它之前，应确认设备功能开关、SDK 暴露情况，以及 CTS 和厂商实现行为。

#### 9.2 NDK `ANativeWindow`

原生图形缓冲区生产者可以用下面的 API 提交同类帧率提示：

```cpp
ANativeWindow_setFrameRateWithChangeStrategy(
        window,
        60.0f,
        ANATIVEWINDOW_FRAME_RATE_COMPATIBILITY_DEFAULT,
        ANATIVEWINDOW_CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

`ANativeWindow_setFrameRate()` 从 API 30 开始提供；带有切换策略的 `ANativeWindow_setFrameRateWithChangeStrategy()` 从 API 31 开始提供。传入 0 可以清除请求。NDK 注释同样说明：系统可能不采用目标值，这个调用也不会自动限制应用提交缓冲区的速率。

### 10. 24 fps、游戏和混合场景怎么读

#### 10.1 24 fps 视频

24 fps 视频在 120 Hz 上可以让每个视频帧连续显示 5 个刷新周期，也就是采用 5:5 节拍，无须切换到 24 Hz。选择器还要同时考虑 UI 叠加层、字幕、触摸、功耗策略、模式组切换和其他可见图层。`setFrameRate(24, FIXED_SOURCE, ...)` 调用成功只表示请求已被记录，不表示下一帧已经完成模式切换。

即使活动模式选择正确，下面几种问题仍会造成视频卡顿：

- 解码器输出晚；
- 缓冲区时间戳错误；
- 队列中堆了过多旧帧；
- acquire fence 发出信号太晚，导致缓冲区尚不可读；
- 图层在目标锁存时刻尚未就绪。

排查时要把请求帧率、活动模式、渲染帧率、缓冲区时间戳、SurfaceFlinger 锁存和送显时间放到同一条时间线上。

#### 10.2 游戏

游戏需要同时查看目标 FPS、游戏模式干预、引擎帧节奏、BufferQueue 深度、GPU 完成时间和温控状态。开始运行时能够达到 120 fps，不代表长时间运行后仍能维持；CPU、GPU 降频、内存带宽限制和厂商功耗策略都会改变应用生成帧的能力。

只有游戏缓冲区已经在截止时间前就绪，但仍在锁存、合成或送显阶段变晚时，才应把排查重点放到显示侧。若 acquire fence 已经晚到，高刷新率模式只能提供更多显示机会，无法补回生产端错过的截止时间。

#### 10.3 UI + 视频 + 叠加层

混合场景中不存在“主图层独占刷新率”。视频图层的固定源投票、宿主 UI 的类别、浮层动画和触摸都会进入同一轮排名。焦点、可见性、图层权重、无缝切换要求和模式组共同决定每个候选是否得分。排障时必须确认当时有哪些图层可见，不能只看播放器的调用参数。

### 11. Perfetto 与状态转储取证

下面的命令用于建立设备能力、当前策略和 SurfaceFlinger 内部状态的快照：

```bash
adb shell dumpsys display
adb shell dumpsys SurfaceFlinger
adb shell dumpsys SurfaceFlinger --displays
```

不同构建的状态转储文本会随功能开关和厂商补丁变化。应搜索活动模式、支持模式、主范围、应用请求范围、渲染帧率、帧率覆盖、`LayerHistory` 投票、`GameFrameRateOverrides`、内核空闲计时器和节奏基准显示器，不要依赖固定行号。

Perfetto 中至少关联这些证据：

| 证据 | 回答的问题 |
|---|---|
| `ActiveModeFps <displayId>` | 当前物理模式的 VSYNC 频率是否变化 |
| `RenderRateFps <displayId>` | Scheduler 采用的渲染节拍是否变化 |
| `PendingModeFps <displayId>` | 是否已有物理模式请求交给 HWC |
| `HasDesiredMode <displayId>` | 是否还有尚待消费的目标请求 |
| `FrameRateOverride <uid>` | 该 UID 是否取得内容推导值或内部接口直接写入的覆盖值 |
| 图层投票与帧率类别 | 哪个可见图层推动了这次选择 |
| FrameTimeline 预期值与实际值 | 帧是否赶上当前调度预测 |
| 缓冲区时间戳、获取栅栏、锁存 | 生产者是否按时交付且内容可读 |
| 显示送显栅栏 | 本轮显示在 Android 用户态可观察的送显边界何时完成 |

`ActiveModeFps` 不变而 `RenderRateFps` 改变，通常表示系统在同一个物理模式内调整了渲染节拍。`PendingModeFps` 出现后仍需等待模式切换完成；不要把计数器写入时刻当作面板的光学响应时刻。送显栅栏是 Android 显示栈中较靠后的时间参照，也不等同于像素已经完成扫描或人眼已经看到画面。

推荐按下面的顺序检查一段异常：

1. 记录目标 Surface、UID、请求值、兼容性参数与切换策略。
2. 记录 DisplayManager 策略、候选模式、活动模式、渲染帧率和节奏基准显示器。
3. 标出投票变化、目标模式、待处理模式与完成切换的时间。
4. 对齐生产者入队、缓冲区时间戳、获取栅栏、锁存、FrameTimeline 和送显栅栏。
5. 游戏场景再补充游戏模式、温控、CPU 与 GPU 频率以及队列深度；视频场景再补充解码输出和播放时间戳。

这套顺序可以区分五类问题：候选选择不符合预期、请求没有在评分中胜出、切换尚未完成、生产端交付过晚，以及显示链路后段耗时过长。

### 12. 与 FrameTimeline 的关系

刷新率选择会改变候选渲染节拍、VSYNC 预测、回调间隔和可能采用的物理模式；FrameTimeline 则依据当前预测时间判断应用帧与显示帧是否按期。

两者的职责边界如下：

- 选择器选中 120 fps，不代表生产者每隔 8.33 ms 都能交付新缓冲区；
- FrameTimeline 标记迟到，也不能单凭该结果证明刷新率选择错误；
- 显示帧的实际送显时间使用 HWC 和送显栅栏反馈，其中仍包含厂商显示路径；
- 模式切换期间要同时查看 VSYNC 周期切换、请求待处理状态、完成状态和 FrameTimeline，不能假定切换会在固定的几十毫秒内完成。

FrameTimeline 的令牌、预期与实际 `SurfaceFrame`、`DisplayFrame` 和栅栏边界，见 [2.12 Android 17 FrameTimeline、FrameTracer 与合成边界](12-android17-frametimeline-composition-boundary.md)。

### 13. 版本演进边界

| Android 版本 | 可确认的公开节点 |
|---|---|
| Android 11（API 30） | `Surface.setFrameRate()` 与 `ANativeWindow_setFrameRate()` 提供内容帧率提示 |
| Android 12（API 31） | 公共 API 增加帧率切换策略；NDK 增加带 `WithChangeStrategy` 后缀的版本 |
| Android 15 QPR1 | ARR 平台能力在满足 Composer3 与设备配置的硬件上进入系统路径 |
| Android 16（API 36） | `Display.hasArrSupport()` 公开报告当前显示器是否支持 ARR |
| Android 17（API 37） | `DisplayModeController`、`RefreshRateSelector`、图层类别、ARR 候选与受功能开关控制的 `FrameRateParams` 均以 `android-17.0.0_r1` 为准 |

表中描述各版本可确认的 API 或平台节点，不表示所有设备从该版本起都支持相同的刷新率范围。设备还要满足面板、Composer HAL、厂商策略、系统功能开关和功耗配置。

延伸阅读：

- [Adaptive Refresh Rate](#自适应刷新率的输入与约束)：ARR 的 Composer3、预期送显时间与能力边界。
- [刷新率切换机制](#模式切换应用适配与抖动)：从策略到 HWC 模式切换的基础路径。
- [VSYNC、Scheduler 与 DisplayFrameRate](03-vsync-choreographer-sf-scheduling.md)：物理刷新率、渲染帧率和应用回调的关系。

### 14. 源码核查清单

平台源码统一为 `android-17.0.0_r1`：

- `frameworks/native/services/surfaceflinger/Display/DisplayModeController.{h,cpp}`
- `frameworks/native/services/surfaceflinger/Display/DisplayModeRequest.h`
- `frameworks/native/services/surfaceflinger/DisplayHardware/DisplayMode.h`
- `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.{h,cpp}`
- `frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/FrameRateOverrideMappings.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/include/scheduler/FrameRateMode.h`
- `frameworks/native/services/surfaceflinger/Scheduler/VSyncReactor.cpp`
- `frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp`
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
- `frameworks/native/libs/nativewindow/include/android/native_window.h`
- `frameworks/base/core/java/android/view/Surface.java`
- `frameworks/base/core/java/android/view/SurfaceControl.java`
- `frameworks/base/core/java/android/view/Display.java`

内核边界核对 `android17-6.18-2026-06_r6` 中的 DRM 垂直消隐、原子提交辅助函数、dma-fence 与 sync_file；厂商面板和 Composer 实现不在通用内核的结论范围内。

请求值必须结合缓冲区就绪时间、锁存、FrameTimeline 与 HWC 送显信息共同判断；刷新率选择结果不能替代逐帧证据。

### 常见误区

显示问题中常见的误判，是把内容帧率、渲染帧率和面板刷新率都称为“FPS”。Android 17 源码至少区分下面五个量，其中前四个是频率，最后一个是某一帧的时间点：

| 名称 | 源码中的代表 | 含义 |
|---|---|---|
| 内容帧率 | `LayerRequirement::desiredRefreshRate` | 视频、游戏或 UI 图层希望采用的节拍，例如 24 fps、60 fps |
| 渲染帧率 | `FrameRateMode::fps` | Scheduler 给应用回调与合成调度采用的渲染节拍 |
| VSYNC 频率 | `DisplayMode::getVsyncRate()` | 当前物理模式对外描述的 VSYNC 基准频率 |
| 峰值刷新率 | `DisplayMode::getPeakFps()` | 该模式可用于送显的最高频率；有 VRR（可变刷新率）配置时由 `minFrameIntervalNs` 换算 |
| 本轮送显时间 | FrameTimeline 与送显栅栏 | 某一显示帧到达 Android 用户态可观察的显示完成边界的时间 |

`FrameRateMode` 把渲染节拍和物理模式放在同一个对象中：

- `fps` 是渲染帧率；
- `modePtr` 指向描述分辨率、VSYNC 频率和模式组等属性的 `DisplayMode`；
- 两个 `FrameRateMode` 即使引用同一个 `modePtr`，也可能因 `fps` 不同表示不同的调度结果。

例如，一块带有 VRR 配置的显示器可以保持同一个物理模式，同时把渲染帧率从 120 fps 调整为 60 fps。此时无须更换模式 ID，但 Scheduler 的调度节拍、VSYNC 回调频率和应用收到的帧率覆盖值仍可能变化。

## 版本与实现边界

| 版本 | 相关变化 |
|---|---|
| Android 11/API 30 | 引入面向应用的 frame-rate API；平台 MRR 路径使用带约束的活动配置切换 |
| Android 12/API 31 | 三参数 `setFrameRate()` 与 `getAlternativeRefreshRates()` 可表达切换策略和无缝候选 |
| Android 14/API 34 | `clearFrameRate()`；`preferredRefreshRate` 可接受任意目标刷新率 |
| Android 15 | 游戏默认刷新率策略变化，需要高刷新率的游戏应主动请求 |
| Android 15 QPR1 | 平台 ARR 支持进入公开版本边界 |
| Android 16/API 36 | `FRAME_RATE_COMPATIBILITY_AT_LEAST` 与 View 帧率分类能力扩展 |
| Android 17/API 37 | 源码锚点更新到 Android 17；保留 MRR 状态机，并与 ARR、View 帧率分类共同工作 |

旧版本的 MRR 设计仍有参考价值，但源码类名、trace 字段和厂商实现可能不同。分析 Android 17 设备时，应以 `android-17.0.0_r1` 和设备上的 Composer 与内核实现为准。

## 结论

Android 17 的帧率协作分为四层：应用通过 View、Compose 或 Surface 表达内容需求；DisplayModeDirector 汇总系统约束并给出允许范围；SurfaceFlinger Scheduler 根据可见 Layer 的更新节奏选择 render rate/mode；DisplayModeController 在 MRR 路径上执行物理模式切换，Composer3 则在 ARR 路径上把 `frameIntervalNs` 和必要的 `notifyExpectedPresent` 提示交给显示硬件。

诊断时先区分 MRR 与 ARR，再分别观察应用产帧、刷新率选择和最终展示。`setFrameRate()` 用于投票，ARR 调整显示 cadence，Swappy 或引擎 pacing 控制提交时机。区分这三层后，才能判断问题来自应用、SurfaceFlinger、HWC 还是设备显示驱动。

## 参考资料

- [AOSP：Adaptive refresh rate](https://source.android.com/docs/core/graphics/arr)
- [Android Developers：Optimize frame rate with adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android 17 `DisplayModeDirector.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/display/mode/DisplayModeDirector.java)
- [Android 17 `DisplayManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayManagerService.java)
- [Android 17 `Display.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)
- [Android 17 `DisplayInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/DisplayInfo.java)
- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)
- [Android 17 `Window.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Window.java)
- [Android 17 `Surface.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java)
- [Android 17 `Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 17 `SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [Android 17 `Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)
- [Android 17 `RefreshRateSelector.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp)
- [Android 17 `VsyncModulator.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/VsyncModulator.cpp)
- [Android 17 Composer3 `DisplayConfiguration.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl)
- [Android 17 Composer3 `VrrConfig.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/VrrConfig.aidl)
- [Android 17 Composer3 `IComposerClient.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/composer/aidl/android/hardware/graphics/composer3/IComposerClient.aidl)
- [Android common kernel 17 6.18 `dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
- [Android common kernel 17 6.18 `sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
- [Android common kernel 17 6.18 `drm_vblank.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c)
- [Perfetto：FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto Android 17 metric：`frames.sql`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/metrics/sql/android/jank/frames.sql)
- [Android Frame Pacing Library](https://developer.android.com/games/sdk/frame-pacing)

- [AOSP `DisplayModeController`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp)
- [AOSP `SurfaceFlinger`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp)
- [AOSP `RefreshRateSelector`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp)
- [AOSP `LayerHistory`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp)
- [AOSP `HWComposer`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/services/surfaceflinger/DisplayHardware/HWComposer.cpp)
- [Composer3 `DisplayConfiguration.aidl`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayConfiguration.aidl)
- [Composer3 `DisplayCommand.aidl`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/DisplayCommand.aidl)
- [Composer3 `ActiveConfigCommand.aidl`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/ActiveConfigCommand.aidl)
- [Composer3 `IComposerClient.aidl`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/IComposerClient.aidl)
- [Composer3 `VsyncPeriodChangeConstraints.aidl`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/VsyncPeriodChangeConstraints.aidl)
- [Composer3 `VsyncPeriodChangeTimeline.aidl`](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/VsyncPeriodChangeTimeline.aidl)
- [AOSP：Multiple refresh rate](https://source.android.com/docs/core/graphics/multiple-refresh-rate)
- [Android Developers：Frame rate](https://developer.android.com/media/optimize/performance/frame-rate)
- [Android Developers：`Surface.setFrameRate()`](https://developer.android.com/reference/android/view/Surface#setFrameRate(float,int,int))
- [Android Developers：`Display.Mode.getAlternativeRefreshRates()`](https://developer.android.com/reference/android/view/Display.Mode#getAlternativeRefreshRates())
- [Android Developers：Optimize refresh rates for games](https://developer.android.com/games/optimize/display-refresh-rate-change)
- [Android Developers：Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [`android17-6.18-2026-06_r6`：DRM VBlank](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c)
- [`android17-6.18-2026-06_r6`：DRM atomic helper](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_atomic_helper.c)
- [`android17-6.18-2026-06_r6`：DMA fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
