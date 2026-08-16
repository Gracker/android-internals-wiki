---
title: "Android 17 显示模式选择与 RefreshRateSelector 评分机制"
chapter: "2.34"
status: "finalized"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-08-12"
last_verified_against: "AOSP android-17.0.0_r1; common kernel android17-6.18-2026-06_r6"
last_idle_audit_at: "2026-08-05"
last_idle_audit_run_id: "20260805-223530-idle-audit-20677657"
task9_state: "reviewed"
pipeline_stage: "finalized"
confidence: high
last_body_apply_at: "2026-08-10T19:15:18+08:00"
last_body_apply_run_id: "20260810-191518-8c420f19"
task2b_state: "fixed"
task6_state: "reviewed"
tags: [rendering, surfaceflinger, refresh-rate, frame-rate-override, display-mode, android17, hwc, vrr]
related_chapters: ["2.30", "2.6"]
last_review_finalize_at: "2026-08-12T14:05:07+08:00"
last_review_finalize_run_id: "20260812-140507-01043da4"
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Display/DisplayModeController.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Display/DisplayModeRequest.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameRateCompatibility.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameRateOverrideMappings.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/LayerHistory.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/include/scheduler/FrameRateMode.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DisplayHardware/DisplayMode.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/VSyncReactor.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp"
  - type: aosp
    path: "frameworks/native/libs/nativewindow/include/android/native_window.h"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Surface.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Display.java"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
---

# Android 17 显示模式选择与 RefreshRateSelector 评分机制

以下分析以 AOSP `android-17.0.0_r1` 为平台锚点，以通用内核 `android17-6.18-2026-06_r6` 为内核锚点。文中只陈述可由 Android 17 源码确认的行为；面板切换耗时、显示驱动跟踪点和功耗收益仍由具体设备实现决定。

本章主要核对三组源码：`DisplayModeController` 判断目标模式无需处理、只需更新渲染节拍、可以合并到待处理请求，还是必须切换物理模式；SurfaceFlinger 的帧调度器 Scheduler 通过 `RefreshRateSelector` 同时接收图层投票、全局信号与 DisplayManager 策略；`FrameRateOverrideMappings` 维护按 UID 生效的帧率覆盖，其中内部接口直接写入的覆盖值优先于根据内容计算的覆盖值。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp, Scheduler/RefreshRateSelector.cpp, Scheduler/FrameRateOverrideMappings.cpp @ android-17.0.0_r1]

## 1. 先分清五个容易混淆的量

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

## 2. Android 17 的选择链路

Android 17 的决策路径可以压缩为以下顺序：

1. DisplayManager 策略给出默认模式、主范围、应用请求范围，以及是否允许跨模式组。
2. `LayerHistory` 根据活动图层、显式 `setFrameRate()`、内容检测、帧率类别和游戏模式干预，生成表示图层需求的 `LayerRequirement`。
3. `Scheduler::chooseDisplayModes()` 为各物理显示器调用 `RefreshRateSelector`，得到排序后的 `FrameRateMode`。
4. `Scheduler::applyPolicy()` 把选中结果包装成 `DisplayModeRequest`，经回调交给 SurfaceFlinger。
5. `SurfaceFlinger::setDesiredMode()` 调用 `DisplayModeController::setDesiredMode()`，按返回的 `DesiredModeAction` 更新渲染帧率，或发起物理模式切换。
6. 需要更换模式 ID 时，`DisplayModeController::initiateModeChange()` 通过 Composer 调用 HWC；切换完成后再更新活动模式、VSYNC 模型和显示事件。

在这条路径中，DisplayManager 策略划定允许范围，图层投票（vote）表达内容偏好，Scheduler 负责排列候选顺序，`DisplayModeController` 负责执行。`DisplayModeRequest` 是 SurfaceFlinger 内部请求，并非应用可以直接提交的公共接口。

排障时可以按照“策略边界 → 图层需求 → 评分排名 → 执行动作”拆分日志：策略只决定候选集合，`LayerHistory` 决定每个可见图层的投票，`getRankedFrameRatesLocked()` 再把投票、触摸、空闲、点亮等全局信号和并列裁决规则（tie-break）合成排序结果。最终是否调用 HWC（硬件合成器）设置物理模式，还要看 `DisplayModeController::setDesiredMode()` 返回的动作。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp, Display/DisplayModeController.cpp @ android-17.0.0_r1]

### 2.1 策略包含两层范围

`RefreshRateSelector::Policy`（选择策略）的两个主要字段是 `primaryRanges` 与 `appRequestRanges`：

- `primaryRanges` 是常态选择区域；
- `appRequestRanges` 可以更宽，显式图层请求在满足条件时允许离开主范围；
- 候选始终不能越过应用请求范围；
- `allowGroupSwitching` 决定能否考虑其他模式组。一个模式组通常收纳可以无缝互切的模式，因此源码把“是否同组”作为判断无缝切换的重要条件。

每个范围又分为 `physical` 与 `render`。前者约束物理模式的峰值刷新率 `DisplayMode::getPeakFps()`，后者约束渲染节拍 `FrameRateMode::fps`。“允许选择 120 Hz 物理模式”不等于“应用一定会以 120 fps 收到回调”。

## 3. 候选不等于一张简单的模式表

### 3.1 `DisplayMode` 保存什么

Android 17 的 `DisplayMode` 保存模式 ID、HWC 配置 ID、分辨率、DPI（像素密度）、模式组、VSYNC 频率、可选的 VRR 配置和 HDR 输出类型。`getPeakFps()` 的定义如下：

- 没有 VRR 配置：峰值刷新率等于 `mVsyncRate`；
- 有 VRR 配置：峰值刷新率由 `minFrameIntervalNs` 换算。

因此，在 ARR（Android 自适应刷新率）或 VRR 设备上，`getVsyncRate()`、`getPeakFps()` 和当前 `FrameRateMode::fps` 代表不同层次，不能互相替代。

### 3.2 构造候选时的过滤

`constructAvailableRefreshRates()` 以策略中的默认模式为基准，过滤条件包括：

- 分辨率与默认模式相同；
- DPI 与默认模式相同；
- 模式组满足策略；
- 峰值刷新率位于物理范围；
- 渲染帧率位于渲染范围；关闭帧率覆盖时，物理峰值也要满足渲染范围；
- 开启 `enable_user_preferred_hdr_mode` 时，HDR 输出类型与默认模式相同。

选择器分别构造 `mPrimaryFrameRates`、`mAppRequestFrameRates` 和 `mAllFrameRates`。实际参与图层评分的主要集合是 `mAppRequestFrameRates`，并非设备公布的所有模式。

### 3.3 MRR 与 VRR 生成渲染帧率候选的方式不同

MRR 指通过多个固定刷新率模式进行切换的传统方式，VRR 则允许显示器在可变范围内调整刷新节拍。`createFrameRateModes()` 会为每个通过过滤的 `DisplayMode` 生成一个或多个渲染帧率，源码用 divisor（除数）表示“物理频率每经过多少个周期产生一次渲染节拍”：

- 帧率覆盖关闭时，只生成除数 1，也就是渲染节拍与物理频率相同；
- 没有 VRR 配置的模式按 VSYNC 频率的整数除数枚举；除数大于 1 时，低于 20 Hz 的候选会被截掉；
- 有 VRR 配置的模式先使用除数集合 `{1, 2, 5, 10, 15, 20, 24, 30, 48, 60}`，再加入范围端点，并在最大间隙中补充候选，最多形成 15 个除数；
- 同一个渲染帧率、同一个组出现多个物理模式时，通常保留物理峰值更低的那个；主物理范围是单值时，优先保留该范围内的模式。

这里的 VRR 候选不表示面板能在 1 Hz 到 120 Hz 之间任意连续取值。它是 SurfaceFlinger 为调度和帧率覆盖建立的一组离散 `FrameRateMode`，仍然受 HWC 能力与设备策略约束。

## 4. 图层投票从哪里来

### 4.1 公共兼容性参数与内部投票使用不同枚举

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

### 4.2 游戏模式干预的优先级

游戏模式的两个值保存在 `LayerHistory::mGameFrameRateOverride`，每个 UID 对应一个系统干预帧率和一个游戏默认帧率。活动图层按以下优先级选择帧率意见：

1. 有效的游戏模式干预值；
2. 应用自己的 `setFrameRate()` 或帧率类别；
3. 游戏默认帧率；
4. 在 ARR 上仍有效、但在 MRR 上不适用的其他意见；
5. 没有可用意见时恢复普通内容检测。

这可以解释游戏请求 90 fps、系统却稳定给出 60 fps 的情况。若设备配置了 FPS 限速干预，平台侧意见会优先于应用投票。排障时应同时检查游戏模式、应用请求和当前渲染帧率。

## 5. 排名不是一个通用公式

旧资料常把 `RefreshRateSelector` 简化为“计算目标值与候选值的距离，再累加所有图层的分数”。Android 17 会按照投票类型进入不同分支，距离分只适用于其中一部分。

阅读源码时，不能把连续数值评分理解成唯一公式。Android 17 确实在多个分支使用距离或比例分数，但 `ExplicitCategory`、`ExplicitExact`、`ExplicitDefault`、触摸后的延迟升频、空闲状态的提前返回，以及分数相同后的高低帧率偏好，都会改变最终顺序。因此，一次异常只能结合具体投票类型和当时的全局信号解释，不能只用“目标帧率越近，得分越高”概括。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp @ android-17.0.0_r1]

### 5.1 距离分的含义

`calculateDistanceScoreLocked(reference, refresh)` 会先用两个帧率中的较小值除以较大值，再对比值求平方：

`score = (min(reference, refresh) / max(reference, refresh))²`

结果位于 0 到 1 之间。两个帧率相等时结果为 1，偏离越大，分数越低。这个函数用于 `Max`、`ExplicitGte` 未达到下限时，以及部分类别的边界匹配；它不能代表所有投票的评分方式。

### 5.2 各类投票的评分规则

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

### 5.3 评分前后的全局信号

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

## 6. 多显示器与节奏基准显示器

Scheduler 会为多个物理显示器生成选择结果。节奏基准显示器（pacesetter）提供全局调度参照；跟随显示器能否独立选择，取决于 `follower_arbitrary_refresh_rate_selection_combined` 等平台配置。

在旧路径中，跟随显示器收到有效的 `pacesetterFps` 时，会先在活动模式组内寻找峰值帧率相同的候选，找不到时才继续常规选择。新路径允许综合考虑多个显示器，但仍不能假定内屏和外接屏完全独立。分析投屏、桌面模式或双屏设备时，应分别记录：

- 每个显示器的物理 ID、活动模式 ID 和组；
- 哪块显示器是节奏基准；
- 各显示器的 `ActiveModeFps` 和 `RenderRateFps`；
- 每个显示器自己的送显栅栏和 FrameTimeline。

不要用默认屏的一条 VSYNC 或送显栅栏解释外接屏。

## 7. `DisplayModeController` 怎样执行选择结果

### 7.1 `DesiredModeAction` 表示本次调用要执行的动作

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

### 7.2 两条 Composer 与 HWC 路径

`initiateModeChange()` 会根据 Composer（SurfaceFlinger 到 HWC 的合成接口）能力选择以下路径：

- 不支持 DisplayCommand 模式设置时：调用 `setActiveModeWithConstraints()`，由 HAL 返回 `VsyncPeriodChangeTimeline`（VSYNC 周期变更时间线）；
- 支持 DisplayCommand 模式设置时：调用 `setDisplayMode()`；调用成功后，SurfaceFlinger 在该分支把 `refreshRequired` 设为 `false`，并把 `newVsyncAppliedTimeNanos` 设为当前 `systemTime()`。

源码中的“立即”只描述 SurfaceFlinger 在 DisplayCommand 成功分支中的状态处理，不能外推为“面板像素会在固定帧数内完成响应”。另一条路径的时间线由厂商 HAL 提供，AOSP 同样没有统一规定 1～3 帧的切换延迟。

取证时应分开记录两条 Composer 路径：`setActiveModeWithConstraints()` 的时间线来自 HAL 返回值；DisplayCommand 的 `setDisplayMode(seamlessRequired)` 成功后，SurfaceFlinger 在该分支把 `refreshRequired` 设为 `false`，并把 `newVsyncAppliedTimeNanos` 设为 `systemTime()`。后者只表示系统框架完成了这一步状态更新，不代表面板像素的光学响应已经完成。

### 7.3 完成模式切换的边界

新的待处理模式通过检查后，`finalizeModeChange()` 会完成以下状态更新：

- 比较旧活动模式与待处理模式的分辨率；
- 更新选择器的活动模式 ID 与渲染帧率；
- 更新 `ActiveModeFps` 和 `RenderRateFps` 系统跟踪计数器；
- 分辨率相同返回 `RefreshRateChange`；
- 分辨率不同返回 `ResolutionChange`；
- 显示器、待处理请求或模式 ID 不合法时返回 `NoModeChange`。

分辨率切换还需要 DisplayManager 配合提交显示尺寸事务。`setDesiredMode()` 已经执行，并不代表分辨率事务、VSYNC 模型更新和应用事件通知都已完成。

## 8. UID 帧率覆盖与游戏模式使用不同的数据通路

`FrameRateOverrideMappings` 有两个映射表：

- `mFrameRateOverridesFromBackdoor`：由 `setPreferredRefreshRateForUid()` 写入；Android 17 的 SurfaceFlinger 内部事务 1039 可以触发它，源码将这类直接写入路径称为 backdoor，值为 0 表示删除；
- `mFrameRateOverridesByContent`：由 `RefreshRateSelector::getFrameRateOverrides()` 根据当前内容需求计算，再通过 `updateFrameRateOverridesByContent()` 整表替换。

查询某个 UID 时，内部接口直接写入的值优先。设备不支持内容帧率覆盖时，根据内容计算的映射表不会对外生效。

内容帧率覆盖用于在显示器保持某个物理刷新率时，按 UID 为应用事件回调选择一个可以整除该物理频率的较低渲染帧率。例如，120 Hz 可以按每两个物理周期一次回调得到 60 fps。MRR 分支不会给出低于 30 fps 的覆盖值；ARR 分支会从应用请求候选中保留能整除当前显示刷新率的值。某个 UID 含有 `Max` 或 `Heuristic` 图层、满足触摸升频条件，或者没有可评分意见时，也可能不生成覆盖值。

游戏模式干预值和游戏默认帧率不会写入这两个映射表。它们进入 `LayerHistory` 改变图层投票，再间接影响模式排名和后续的内容帧率覆盖计算。若把两者看成同一张 UID 表，就会混淆显示模式选择与应用回调限频。

如果正在排查“应用请求了 60 fps，但 UID 覆盖值不是 60”的问题，应先区分两个映射表：直接写入表按 UID 设置并优先返回，内容表则由选择器根据当前内容需求整体刷新。游戏模式干预不会直接写入这两个映射，而是先改变 `LayerHistory` 的投票，再间接影响模式选择与覆盖值生成。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Scheduler/FrameRateOverrideMappings.cpp, Scheduler/LayerHistory.cpp @ android-17.0.0_r1]

## 9. 内核空闲计时器的平台边界

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

## 10. 应用怎样表达需求

### 10.1 Java `Surface.setFrameRate()`

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

### 10.2 NDK `ANativeWindow`

原生图形缓冲区生产者可以用下面的 API 提交同类帧率提示：

```cpp
ANativeWindow_setFrameRateWithChangeStrategy(
        window,
        60.0f,
        ANATIVEWINDOW_FRAME_RATE_COMPATIBILITY_DEFAULT,
        ANATIVEWINDOW_CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

`ANativeWindow_setFrameRate()` 从 API 30 开始提供；带有切换策略的 `ANativeWindow_setFrameRateWithChangeStrategy()` 从 API 31 开始提供。传入 0 可以清除请求。NDK 注释同样说明：系统可能不采用目标值，这个调用也不会自动限制应用提交缓冲区的速率。

## 11. 24 fps、游戏和混合场景怎么读

### 11.1 24 fps 视频

24 fps 视频在 120 Hz 上可以让每个视频帧连续显示 5 个刷新周期，也就是采用 5:5 节拍，无须切换到 24 Hz。选择器还要同时考虑 UI 叠加层、字幕、触摸、功耗策略、模式组切换和其他可见图层。`setFrameRate(24, FIXED_SOURCE, ...)` 调用成功只表示请求已被记录，不表示下一帧已经完成模式切换。

即使活动模式选择正确，下面几种问题仍会造成视频卡顿：

- 解码器输出晚；
- 缓冲区时间戳错误；
- 队列中堆了过多旧帧；
- acquire fence 发出信号太晚，导致缓冲区尚不可读；
- 图层在目标锁存时刻尚未就绪。

排查时要把请求帧率、活动模式、渲染帧率、缓冲区时间戳、SurfaceFlinger 锁存和送显时间放到同一条时间线上。

### 11.2 游戏

游戏需要同时查看目标 FPS、游戏模式干预、引擎帧节奏、BufferQueue 深度、GPU 完成时间和温控状态。开始运行时能够达到 120 fps，不代表长时间运行后仍能维持；CPU、GPU 降频、内存带宽限制和厂商功耗策略都会改变应用生成帧的能力。

只有游戏缓冲区已经在截止时间前就绪，但仍在锁存、合成或送显阶段变晚时，才应把排查重点放到显示侧。若 acquire fence 已经晚到，高刷新率模式只能提供更多显示机会，无法补回生产端错过的截止时间。

### 11.3 UI + 视频 + 叠加层

混合场景中不存在“主图层独占刷新率”。视频图层的固定源投票、宿主 UI 的类别、浮层动画和触摸都会进入同一轮排名。焦点、可见性、图层权重、无缝切换要求和模式组共同决定每个候选是否得分。排障时必须确认当时有哪些图层可见，不能只看播放器的调用参数。

## 12. Perfetto 与状态转储取证

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

## 13. 与 FrameTimeline 的关系

刷新率选择会改变候选渲染节拍、VSYNC 预测、回调间隔和可能采用的物理模式；FrameTimeline 则依据当前预测时间判断应用帧与显示帧是否按期。

两者的职责边界如下：

- 选择器选中 120 fps，不代表生产者每隔 8.33 ms 都能交付新缓冲区；
- FrameTimeline 标记迟到，也不能单凭该结果证明刷新率选择错误；
- 显示帧的实际送显时间使用 HWC 和送显栅栏反馈，其中仍包含厂商显示路径；
- 模式切换期间要同时查看 VSYNC 周期切换、请求待处理状态、完成状态和 FrameTimeline，不能假定切换会在固定的几十毫秒内完成。

FrameTimeline 的令牌、预期与实际 `SurfaceFrame`、`DisplayFrame` 和栅栏边界，见 [2.30 Android 17 FrameTimeline](30-android17-frametimeline-composition-boundary.md)。

## 14. 版本演进边界

| Android 版本 | 可确认的公开节点 |
|---|---|
| Android 11（API 30） | `Surface.setFrameRate()` 与 `ANativeWindow_setFrameRate()` 提供内容帧率提示 |
| Android 12（API 31） | 公共 API 增加帧率切换策略；NDK 增加带 `WithChangeStrategy` 后缀的版本 |
| Android 15 QPR1 | ARR 平台能力在满足 Composer3 与设备配置的硬件上进入系统路径 |
| Android 16（API 36） | `Display.hasArrSupport()` 公开报告当前显示器是否支持 ARR |
| Android 17（API 37） | `DisplayModeController`、`RefreshRateSelector`、图层类别、ARR 候选与受功能开关控制的 `FrameRateParams` 均以 `android-17.0.0_r1` 为准 |

表中描述各版本可确认的 API 或平台节点，不表示所有设备从该版本起都支持相同的刷新率范围。设备还要满足面板、Composer HAL、厂商策略、系统功能开关和功耗配置。

延伸阅读：

- [Adaptive Refresh Rate](../../part1-fundamentals/ch02-rendering/18-adaptive-refresh-rate.md)：ARR 的 Composer3、预期送显时间与能力边界。
- [刷新率切换机制](../../part1-fundamentals/ch02-rendering/19-refresh-rate-switching.md)：从策略到 HWC 模式切换的基础路径。
- [VSYNC、Scheduler 与 DisplayFrameRate](../../part1-fundamentals/ch02-rendering/23-vsync-scheduler-displayframerate.md)：物理刷新率、渲染帧率和应用回调的关系。

## 15. 源码核查清单

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
