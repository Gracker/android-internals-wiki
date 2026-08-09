---
title: "Android 17 Display Mode 选择与 RefreshRateSelector 评分机制"
chapter: "2.34"
status: "ready-for-review"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-17"
last_verified_against: "AOSP android-17.0.0_r1"
last_idle_audit_at: "2026-08-05"
last_idle_audit_run_id: "20260805-223530-idle-audit-20677657"
task9_state: "body-applied"
pipeline_stage: "ready-for-review"
confidence: high
drafted_date: "2026-07-17"
last_task6_audit: "2026-07-17"
last_body_apply_at: "2026-08-09T09:17:01+08:00"
last_body_apply_run_id: "20260809-091529-696a441f"
task2b_state: "body-applied"
task6_state: "pending-review"
tags: [rendering, surfaceflinger, refresh-rate, frame-rate-override, display-mode, android17, hwc, vrr]
related_chapters: ["2.30", "2.6"]
created_by: "task3-source-research"
created_date: "2026-07-17"
gap_source: "DeepResearch 2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md"
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

# Android 17 Display Mode 选择与 RefreshRateSelector 评分机制

本文以 AOSP `android-17.0.0_r1` 为平台锚点，以 common kernel `android17-6.18-2026-06_r6` 为内核锚点。这里讨论的是 Android 17 中可以从源码确认的行为；面板切换耗时、显示驱动 tracepoint 和功耗收益仍由具体设备实现决定。

## 1. 先分清五个帧率

显示问题中最常见的误判，是把内容帧率、渲染帧率和面板刷新率都叫作“FPS”。Android 17 源码至少需要区分下面五个量：

| 名称 | 源码中的代表 | 含义 |
|---|---|---|
| 内容帧率 | `LayerRequirement::desiredRefreshRate` | 视频、游戏或 UI layer 希望采用的节拍，例如 24 fps、60 fps |
| 渲染帧率 | `FrameRateMode::fps` | Scheduler 给应用回调与合成调度采用的 render cadence |
| VSYNC rate | `DisplayMode::getVsyncRate()` | 当前物理 mode 对外描述的 VSYNC 基准频率 |
| 峰值刷新率 | `DisplayMode::getPeakFps()` | 该 mode 可用于 present 的最高频率；有 VRR 配置时由 `minFrameIntervalNs` 换算 |
| 本轮 present 时间 | FrameTimeline / present fence | 某一轮 display frame 到达 Android 显示 present 边界的时间 |

`FrameRateMode` 把“渲染节拍”和“物理 mode”放在一起：

- `fps` 是 render frame rate；
- `modePtr` 指向 `DisplayMode`；
- 两个 `FrameRateMode` 即使引用同一个 `modePtr`，也可能因 `fps` 不同而表示不同调度结果。

例如，一块带 VRR 配置的显示可以保持同一个物理 mode，同时把 render rate 从 120 fps 调成 60 fps。此时不需要更换 mode id，但 Scheduler、VSYNC callback 和应用收到的 frame-rate override 仍可能变化。

## 2. Android 17 的选择链路

Android 17 的决策路径可以压缩为以下顺序：

1. DisplayManager 侧策略给出默认 mode、primary ranges、app-request ranges，以及是否允许跨 group。
2. `LayerHistory` 根据活跃 layer、显式 `setFrameRate()`、内容检测、frame-rate category 和 Game Mode intervention 生成 `LayerRequirement`。
3. `Scheduler::chooseDisplayModes()` 为各物理 display 调用 `RefreshRateSelector`，得到排序后的 `FrameRateMode`。
4. `Scheduler::applyPolicy()` 把选中结果包装成 `DisplayModeRequest`，经 callback 交给 SurfaceFlinger。
5. `SurfaceFlinger::setDesiredMode()` 调用 `DisplayModeController::setDesiredMode()`，按返回的 `DesiredModeAction` 更新 render rate，或发起物理 mode 切换。
6. 需要换 mode id 时，`DisplayModeController::initiateModeChange()` 调用 Composer/HWC；切换完成后再更新 active mode、VSYNC 模型和 display event。

这条路径里，DisplayManager 策略负责划定允许范围，layer vote 负责表达内容需求，Scheduler 负责排名，`DisplayModeController` 负责执行。`DisplayModeRequest` 不是应用直接提交给 SurfaceFlinger 的公共请求。

### 2.1 Policy 有两层范围

`RefreshRateSelector::Policy` 中最需要关注的是 `primaryRanges` 与 `appRequestRanges`：

- `primaryRanges` 是常态选择区域；
- `appRequestRanges` 可以更宽，显式 layer 请求在满足条件时允许离开 primary range；
- 候选始终不能越过 app-request range；
- `allowGroupSwitching` 决定能否考虑其他 mode group。源码把同 group 视为 seamless switching 的重要条件。

每个范围又分为 `physical` 与 `render`。前者约束 `DisplayMode::getPeakFps()`，后者约束 `FrameRateMode::fps`。因此“允许 120 Hz 物理 mode”不等于“应用一定以 120 fps 收到回调”。

## 3. 候选不是一张简单的 mode 表

### 3.1 `DisplayMode` 保存什么

Android 17 的 `DisplayMode` 保存 mode id、HWC config id、分辨率、DPI、group、VSYNC rate、可选 VRR config 和 HDR output type。`getPeakFps()` 的定义值得单独记住：

- 没有 VRR config：峰值刷新率等于 `mVsyncRate`；
- 有 VRR config：峰值刷新率由 `minFrameIntervalNs` 换算。

所以在 ARR/VRR 设备上，`getVsyncRate()`、`getPeakFps()` 和当前 `FrameRateMode::fps` 不能互相替代。

### 3.2 构造候选时的过滤

`constructAvailableRefreshRates()` 以 policy 的 default mode 为基准，过滤条件包括：

- 分辨率与 default mode 相同；
- DPI 与 default mode 相同；
- group 满足 policy；
- peak refresh rate 位于 physical range；
- render rate 位于 render range；关闭 frame-rate override 时，物理峰值也要满足 render range；
- 开启 `enable_user_preferred_hdr_mode` 时，HDR output type 与 default mode 相同。

Selector 分别构造 `mPrimaryFrameRates`、`mAppRequestFrameRates` 和 `mAllFrameRates`。参与 layer 评分的主集合是 `mAppRequestFrameRates`，并非设备公布的所有 mode。

### 3.3 MRR 与 VRR 的 divisor 生成不同

`createFrameRateModes()` 会对每个通过过滤的 `DisplayMode` 生成一个或多个 render rate：

- frame-rate override 关闭时，只生成 divisor 1；
- 没有 VRR config 的 mode 按 VSYNC rate 的整数 divisor 枚举；divisor 大于 1 时，低于 20 Hz 的候选会被截掉；
- 有 VRR config 的 mode 使用锚点 `{1, 2, 5, 10, 15, 20, 24, 30, 48, 60}`，再加入范围端点，并按最大间隙补点，最多形成 15 个 divisor；
- 同一个 render fps、同一个 group 出现多个物理 mode 时，通常保留物理峰值更低的那个；primary physical range 是单值时，优先留在该范围内。

这里的 VRR 候选不是“面板能在 1 Hz 到 120 Hz 之间任意连续取值”的承诺。它是 SurfaceFlinger 为调度与 override 建立的离散 `FrameRateMode` 集合，仍受 HWC 能力和设备 policy 约束。

## 4. Layer vote 从哪里来

### 4.1 Compatibility 与内部 vote 不是同一个枚举

`FrameRateCompatibility.h` 描述 layer 输入侧的 compatibility；`RefreshRateSelector::LayerVoteType` 才是评分阶段使用的类型。Android 17 中后者包含：

`NoVote`、`Min`、`Max`、`Heuristic`、`ExplicitDefault`、`ExplicitExactOrMultiple`、`ExplicitExact`、`ExplicitGte`、`ExplicitCategory`。

`LayerHistory` 的主要映射如下：

| Layer compatibility / 来源 | VRR/ARR display | MRR display |
|---|---|---|
| `Default` | `ExplicitDefault` | `ExplicitDefault` |
| `Min` | `Min` | `Min` |
| `ExactOrMultiple` | `ExplicitExactOrMultiple` | `ExplicitExactOrMultiple` |
| `Exact` | `ExplicitExact` | `ExplicitExact` |
| `Gte` | `ExplicitGte` | `Max` |
| `NoVote` | `NoVote` | `NoVote` |
| 未显式指定、由内容检测估算 | `Heuristic` | `Heuristic` |

`Gte` 在 MRR 上转成 `Max`，源码注释给出的理由是滚动和动画更看重平滑，而 MRR 无法像 ARR 那样在同一 mode 内平滑改变 render cadence。

Java 公共常量 `FRAME_RATE_COMPATIBILITY_AT_LEAST` 进入 native layer 后对应这里的 `Gte` 语义。应用层名称与 Selector 内部枚举不同，读 trace 或 dump 时要按这张映射表转换。

### 4.2 Game Mode intervention 的优先级

Game Mode 的两个值保存在 `LayerHistory::mGameFrameRateOverride`，每个 UID 对应 intervention rate 与 game-default rate。活跃 layer 的选择顺序是：

1. 有效的 Game Mode intervention；
2. 应用自己的 `setFrameRate()` 或 frame-rate category；
3. Game default frame rate；
4. ARR 上仍有效、但在 MRR 上不适用的剩余 opinion；
5. 没有可用意见时恢复普通内容检测。

这解释了一个常见现象：游戏代码明明请求 90 fps，系统仍稳定给出 60 fps。若设备配置了 FPS throttling intervention，平台侧意见会先于应用 vote。排障时应同时检查 Game Mode、应用请求和 active render rate。

## 5. 排名不是一个通用公式

旧资料常把 `RefreshRateSelector` 简化为“计算目标值与候选值的距离，再把所有 layer 相加”。Android 17 不是这样实现的。源码按 vote 类型走不同分支，距离分只覆盖其中一部分。

### 5.1 距离分的含义

`calculateDistanceScoreLocked(reference, refresh)` 先用较小值除以较大值，再返回平方：

`score = (min(reference, refresh) / max(reference, refresh))²`

结果位于 0 到 1。两个帧率相等时为 1，偏离越大分数越低。这个函数用于 `Max`、`ExplicitGte` 未达到下限时，以及部分 category 边界匹配；它不是所有 vote 的总公式。

### 5.2 各 vote 的评分规则

| vote | Android 17 的主要行为 |
|---|---|
| `ExplicitCategory` | 候选落入 category range 得 1；落在范围外时按边界做非精确匹配；`HighHint` 留给 touch boost |
| `Max` | 候选越接近 app-request 集合的最高 render rate，距离分越高 |
| `ExplicitExact` | 支持 content frame-rate override 时，目标的整数倍可得分；不支持时只接受 divisor 1 |
| `ExplicitGte` | 达到或高于目标得 1；低于目标时按距离降分 |
| `ExplicitDefault` | 可以接受非整数倍，但会按 cadence 匹配质量降分 |
| `ExplicitExactOrMultiple` / `Heuristic` | 整数倍得高分；59.94/60 一类 fractional pair 可得 0.8；其他比例按最多 10 个 display frame 的拟合结果评分 |
| `Min`、`NoVote`、`NoPreference` | 在常规逐 layer 评分循环中跳过，并由专门分支处理 |

整数倍匹配还会考虑 seamlessness：跨 group 的 seamed 候选有 `0.95` 系数，非精确匹配再乘一个 `0.95` 系数。Focused layer、允许的 seamlessness、primary range 和当前/default group 都可能让某个候选不参与该 layer 的评分。

每个 layer 的贡献是 `layer.weight × layerScore`。Fixed-source layer 低于设备配置的 multiple threshold 时，源码把“阈值以上”和“阈值以下”的分数暂存到两个池，再根据其他 layer 是否已经把最佳 mode 推到阈值以上决定是否合入。这可以避免一个 24 fps 视频单独把显示长期推到过高物理刷新率，同时仍允许 UI 或其他内容把系统带到高刷。

分数相同也不是随机选：

- 没有 `Max` vote 时，平分候选倾向较低 render rate；
- 存在 `Max` vote 时，平分候选按高帧率优先；
- 没有 layer 得到有效分数时，Selector 还会尝试保留当前 config，或回到 primary range。

### 5.3 评分前后的全局信号

`getRankedFrameRatesLocked()` 有多条早返回和后处理分支：

- follower display 在相关 flag 关闭时尝试跟随 pacesetter 的 peak fps；
- `powerOnImminent` 选择当前 group 的最高候选；
- touch 且没有显式 vote 时直接选择高候选；
- idle 且没有“单值 primary range + 显式 vote”例外时选择低候选；
- 没有有效 vote 时选择当前 anchor group 的高候选；
- 所有 layer 都是 `NoPreference` 时保留 active `FrameRateMode`；
- 所有 layer 都是 `Min`/`NoVote` 时选择低候选。

有显式 vote 时，touch boost 延后到评分完成后判断。`ExplicitDefault` 常用于游戏限制帧率，因此会阻止全局 touch 信号擅自推翻该请求。`HighHint` 只有在同 UID 没有 `ExplicitDefault` 时才作为 app touch boost。

“touch 一律 120 Hz”或“idle 一律最低 Hz”都不符合源码。它们还要经过 policy、group、显式 vote、display 类型和候选集合。

## 6. 多显示器与 pacesetter

Scheduler 会为多个 physical display 生成 choice。Pacesetter 提供全局调度参照；follower 是否能独立选择，取决于 `follower_arbitrary_refresh_rate_selection_combined` 等平台配置。

旧路径中，follower 收到有效 `pacesetterFps` 时会在 active group 内找 peak fps 相同的候选，找不到才继续普通选择。新路径允许组合考虑多个 display，但仍不能假定内屏和外接屏各自完全独立。分析投屏、桌面模式或双屏设备时，应分别记录：

- 每个 display 的 physical id、active mode id 和 group；
- pacesetter 是哪块 display；
- 各 display 的 `ActiveModeFps`、`RenderRateFps`；
- 每个 display 自己的 present fence 和 FrameTimeline。

不要用默认屏的一条 VSYNC 或 present fence解释外接屏。

## 7. `DisplayModeController` 怎样执行选择结果

### 7.1 `DesiredModeAction` 是动作分类

`DisplayModeController::setDesiredMode()` 返回四种动作：

| 动作 | 触发条件概括 | SurfaceFlinger 的处理 |
|---|---|---|
| `None` | mode id 与 render fps 都不需要变化 | 不安排切换 |
| `InitiateRenderRateSwitch` | mode id 不变，只改变 `FrameRateMode::fps` | 更新 Scheduler render rate 与 phase config，按需发送事件 |
| `MergeDisplayModeSwitch` | 已有 desired request，新的请求可合并 | 更新目标；启用 modeset state machine 时重新同步到 peak render rate |
| `InitiateDisplayModeSwitch` | 需要换 mode id，或请求要求强制执行 | 安排 composite、重同步硬件 VSYNC、调制 VSYNC，并标记 mode change pending |

这四个值是 `setDesiredMode()` 的返回动作，不宜理解为一个固定按序走完的四态自动机。例如仅改变 render rate 时不会经过物理 mode switch。

发起物理切换前，Controller 会暂时把当前 mode 的 render rate 恢复到 peak fps，让下一帧尽早被调度。启用 `modeset_state_machine` 后，`desiredModeOpt` 和 `pendingModeOpt` 分别表示尚待发起与已经交给 HWC 的请求；新请求能否合并还要看分辨率。

源码核查时可以把 `setDesiredMode()` 看成三个判定门：先看是否已有未消费的 `desiredModeOpt` 可合并，再看目标 mode id 已经 active 时是否只是 render-rate-only，最后才进入真正的 display-mode request；启用 `modeset_state_machine()` 后，`pendingModeOpt` 与 `desiredModeOpt` 分离，用来避免已经交给 HWC 的请求和后来请求互相覆盖。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp]

### 7.2 两条 Composer/HWC 路径

`initiateModeChange()` 根据 Composer 能力选择：

- 不支持 DisplayCommand modeset：调用 `setActiveModeWithConstraints()`，`VsyncPeriodChangeTimeline` 由 HAL 返回；
- 支持 DisplayCommand modeset：调用 `setDisplayMode()`；调用成功后，SurfaceFlinger 在本分支把 `refreshRequired` 置为 `false`，并把 `newVsyncAppliedTimeNanos` 设为当前 `systemTime()`。

源码中的“immediate”描述的是 SurfaceFlinger 对 DisplayCommand 成功分支的状态处理，不能外推成“面板像素在一个固定帧数内完成响应”。另一条路径的 timeline 由 vendor HAL 提供，也没有 AOSP 统一规定的 1～3 帧延迟。

取证时要把这两条 Composer 路径分开记录：`setActiveModeWithConstraints()` 的 timeline 来自 HAL 返回值；DisplayCommand `setDisplayMode(seamlessRequired)` 成功后，SurfaceFlinger 在本分支把 `refreshRequired` 置为 `false` 并把 `newVsyncAppliedTimeNanos` 设为 `systemTime()`，这只是框架状态机的完成语义，不是面板光学响应时间。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp]

### 7.3 finalize 的边界

新的 pending mode 通过检查后，`finalizeModeChange()` 会：

- 比较旧 active mode 与 pending mode 的分辨率；
- 更新 selector 的 active mode id 与 render fps；
- 更新 `ActiveModeFps`、`RenderRateFps` trace counter；
- 分辨率相同返回 `RefreshRateChange`；
- 分辨率不同返回 `ResolutionChange`；
- display、pending request 或 mode id 不合法时返回 `NoModeChange`。

分辨率切换还需要 DisplayManager 配合 display size transaction。看到 `setDesiredMode()` 已执行，不代表分辨率 transaction、VSYNC 模型和应用事件都已完成。

## 8. UID frame-rate override 与 Game Mode 是两套数据

`FrameRateOverrideMappings` 有两个 map：

- `mFrameRateOverridesFromBackdoor`：由 `setPreferredRefreshRateForUid()` 写入；Android 17 的 SurfaceFlinger backdoor transaction 1039 可以触发它，0 表示删除；
- `mFrameRateOverridesByContent`：由 `RefreshRateSelector::getFrameRateOverrides()` 根据当前 content requirements 计算，再通过 `updateFrameRateOverridesByContent()` 整表替换。

查询某 UID 时，backdoor 优先。设备不支持 content override 时，content map 不会对外生效。

content override 的用途是：显示仍以某个物理刷新率运行时，按 UID 给应用事件节拍选择一个可整除的较低 render rate。MRR 分支不会给出低于 30 fps 的 override；ARR 分支从 app-request 候选里保留能整除当前 display refresh rate 的值。某 UID 含 `Max` 或 `Heuristic` layer、touch boost 条件成立，或没有可评分意见时，也可能不生成 override。

Game Mode intervention 和 game-default rate 不写这两个 map。它们进入 `LayerHistory`，改变 layer vote，再间接影响 mode 排名和后续 content override 计算。把两者看成同一张 UID 表，会把“显示 mode 选择”和“应用回调限频”混为一谈。

## 9. Kernel idle timer 的平台边界

`DisplayModeController` 支持两种配置通道：

- `HwcApi`：调用 Composer `setIdleTimerEnabled(displayId, timeout)`；
- `Sysprop`：切换 `graphics.display.kernel_idle_timer.enabled`。

`RefreshRateSelector::getIdleTimerAction()` 的判断是：

- device min 低于 policy min：关闭，避免内核把刷新率降到 policy 不允许的值；
- policy 的 min 与 max 指向同一 mode：只有 primary physical min 低于 device min 时开启，否则关闭；
- 其他情况开启。

`VSyncReactor::onDisplayModeChanged()` 还明确排除了带 VRR config 的 mode：kernel idle timer 只在 `mSupportKernelIdleTimer && !modePtr->getVrrConfig()` 时参与 period transition。

common kernel `android17-6.18-2026-06_r6` 提供 DRM atomic、vblank、dma-fence 等通用机制，但没有为所有 Android 设备定义上述 sysprop 的统一显示驱动行为。属性由谁监听、能降到哪个 panel mode、切换是否闪屏、节省多少功耗，都要查 vendor Composer、display HAL 和内核驱动。AOSP 这段代码只能证明控制入口与 policy guard。

因此，看到 dumpsys 或 trace 中 kernel idle timer 状态变化，只能说明 SurfaceFlinger 已按 `RefreshRateSelector::getIdleTimerAction()` 选择了 HWC API 或 sysprop 通道；若 active mode 带 VRR config，`VSyncReactor::onDisplayModeChanged()` 还会把 kernel idle timer 排除在 period transition 外。设备是否真的降频，仍必须结合 vendor HAL、panel driver 或实测 present/功耗证据判断。[来源: DeepResearch/2026-07-17-android17-displaymode-refreshrateselector-sourcecode.md; 已验证: frameworks/native/services/surfaceflinger/Display/DisplayModeController.cpp, frameworks/native/services/surfaceflinger/Scheduler/VSyncReactor.cpp]

## 10. 应用怎样表达需求

### 10.1 Java `Surface.setFrameRate()`

下面示例用于游戏或普通 UI，含义是“这个 Surface 偏好 60 fps，并能适应系统选择的其他帧率”：

```java
surface.setFrameRate(
        60f,
        Surface.FRAME_RATE_COMPATIBILITY_DEFAULT,
        Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

`DEFAULT` 适合游戏、UI 和非固定源内容。调用只提供选择依据，不会限制 render loop，也不保证显示立即切到 60 Hz；应用仍应使用 Choreographer、Swappy 或引擎 pacing 控制提交节奏。

下面示例用于 24 fps 固定帧率视频：

```java
surface.setFrameRate(
        24f,
        Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
        Surface.CHANGE_FRAME_RATE_ALWAYS);
```

`FIXED_SOURCE` 告诉系统，24、48、72、96、120 Hz 一类整数倍通常更利于稳定 cadence。`ALWAYS` 允许非 seamless 切换，适合收益能覆盖切换干扰的长视频；列表页短预览通常更适合 `ONLY_IF_SEAMLESS`。播放结束、Surface 改作他用或不再可见时，应调用 `surface.clearFrameRate()` 清除旧意见。

Android 17 还提供受 flag 控制的 `Surface.FrameRateParams`。源码中的 TODO 明确写着当前 plumbing 尚未完成：实现会在 fixed-source rate 与 min/max range 之间择一，不能按 API 形状推断完整区间语义已在所有设备可用。生产代码采用它之前，应确认设备 flag、SDK 暴露和 CTS/OEM 行为。

### 10.2 NDK `ANativeWindow`

Native producer 可以用下面的 API 提交同类提示：

```cpp
ANativeWindow_setFrameRateWithChangeStrategy(
        window,
        60.0f,
        ANATIVEWINDOW_FRAME_RATE_COMPATIBILITY_DEFAULT,
        ANATIVEWINDOW_CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

`ANativeWindow_setFrameRate()` 从 API 30 提供；带 change strategy 的 `ANativeWindow_setFrameRateWithChangeStrategy()` 从 API 31 提供。传入 0 可清除请求。NDK 注释同样强调：系统可能不采用目标值，调用也不会自动节流应用。

## 11. 24 fps、游戏和混合场景怎么读

### 11.1 24 fps 视频

24 fps 视频在 120 Hz 上可以按 5:5 cadence 显示，不一定非要切到 24 Hz。Selector 还要同时考虑 UI overlay、字幕、触摸、功耗 policy、group switching 和其他可见 layer。`setFrameRate(24, FIXED_SOURCE, ...)` 成功只表示请求被记录，不表示下一帧已经换 mode。

即使 active mode 选择正确，下面几种问题仍会造成视频卡顿：

- 解码器输出晚；
- buffer timestamp 错；
- queue 中堆了过多旧帧；
- acquire fence 太晚；
- layer 在目标 latch 时刻尚未 ready。

因此要把 requested frame rate、active mode、render rate、buffer timestamp、latch 和 present 放到同一条时间线上。

### 11.2 游戏

游戏要同时看目标 FPS、Game Mode intervention、引擎 pacing、BufferQueue 深度、GPU 完成时间和温控。首分钟能到 120 fps，不代表长时间运行后仍能维持；CPU/GPU 降频、内存带宽限制和 OEM power policy 都会改变产帧能力。

只有游戏 buffer 已在 deadline 前 ready，仍在 latch、composition 或 present 之后变晚，才应把重点放到 display 侧。若 acquire fence 已经晚到，高刷 mode 只能给更多显示机会，不能补回生产端错过的 deadline。

### 11.3 UI + 视频 + overlay

混合场景不存在“主 layer 独占刷新率”。视频 layer 的 fixed-source vote、宿主 UI 的 category、浮层动画和 touch 都会进入同一次排名。Focused、visible、layer weight、seamlessness 和 mode group 共同决定每个候选是否得分。排障时必须确认当时的可见 layer 集合，不能只看播放器调用参数。

## 12. Perfetto 与 dumpsys 取证

下面命令用于建立设备能力、当前 policy 和 SurfaceFlinger 内部状态的快照：

```bash
adb shell dumpsys display
adb shell dumpsys SurfaceFlinger
adb shell dumpsys SurfaceFlinger --displays
```

不同构建的 dump 文本会随 flag 和 vendor 补丁变化。重点搜索 active mode、supported modes、primary/app-request ranges、render rate、frame-rate override、LayerHistory vote、GameFrameRateOverrides、kernel idle timer 和 pacesetter；不要依赖固定行号。

Perfetto 中至少关联这些证据：

| 证据 | 回答的问题 |
|---|---|
| `ActiveModeFps <displayId>` | 当前物理 mode 的 VSYNC rate 是否变化 |
| `RenderRateFps <displayId>` | Scheduler 采用的 render cadence 是否变化 |
| `PendingModeFps <displayId>` | 是否已有物理 mode 请求交给 HWC |
| `HasDesiredMode <displayId>` | 是否还有尚待消费的 desired request |
| `FrameRateOverride <uid>` | 该 UID 是否拿到 content/backdoor override |
| layer vote / frame-rate category | 哪个可见 layer 推动了选择 |
| FrameTimeline expected/actual | 帧是否赶上当前调度预测 |
| buffer timestamp、acquire fence、latch | producer 是否按时交付且可读 |
| display present fence | 本轮显示在 Android 用户态可观察的 present 边界何时完成 |

`ActiveModeFps` 不变而 `RenderRateFps` 改变，常见于同一物理 mode 内调整 render cadence。`PendingModeFps` 出现后仍需等待 finalize；不要把 counter 写入时刻当作面板光学响应时刻。Present fence 是 Android 显示栈里靠后的时间锚点，也不等同于像素完成扫描或人眼看到。

推荐按下面的顺序检查一段异常：

1. 记录目标 Surface、UID、请求值、compatibility 与 change strategy。
2. 记录 DisplayManager policy、候选 mode、active mode、render rate 和 pacesetter。
3. 标出 vote 变化、desired/pending mode 与 finalize。
4. 对齐 producer queue、buffer timestamp、acquire fence、latch、FrameTimeline 和 present fence。
5. 游戏再补充 Game Mode、thermal、CPU/GPU frequency 与 queue depth；视频再补充解码输出和播放时间戳。

这样可以把“选择错了”“请求没有胜出”“切换尚未完成”“生产端晚到”和“显示后段晚”分成不同问题。

## 13. 与 FrameTimeline 的关系

Refresh-rate selection 改变候选 render cadence、VSYNC 预测、callback 间隔和可能采用的物理 mode；FrameTimeline 则依据当前预测时间判断应用帧与 display frame 是否按期。

两者的边界是：

- Selector 选中 120 fps，不代表 producer 每个 8.33 ms 都能交付新 buffer；
- FrameTimeline 标记 late，也不能单凭该结果证明刷新率选择错误；
- display actual present 使用 HWC/present-fence 反馈，仍包含 vendor 显示路径；
- mode 切换期间要同时看 VSYNC period transition、pending/finalize 和 FrameTimeline，不能假定固定“几十毫秒”完成。

FrameTimeline 的 token、Expected/Actual surface frame、display frame 和 fence 边界见 [2.30 Android 17 FrameTimeline](2.30-android17-frametimeline.md)。

## 14. 版本演进边界

| Android 版本 | 可确认的公开节点 |
|---|---|
| Android 11 / API 30 | `Surface.setFrameRate()` 与 `ANativeWindow_setFrameRate()` 提供内容帧率提示 |
| Android 12 / API 31 | 公共 API 增加 change-frame-rate strategy；NDK 增加 WithChangeStrategy 版本 |
| Android 15 QPR1 | ARR 平台能力在满足 Composer3 与设备配置的硬件上进入系统路径 |
| Android 16 / API 36 | `Display.hasArrSupport()` 公开报告当前 display 是否带 ARR 支持 |
| Android 17 / API 37 | 本文所述 `DisplayModeController`、`RefreshRateSelector`、layer category、ARR 候选与 flagged `FrameRateParams` 以 `android-17.0.0_r1` 为准 |

表中描述的是各版本可确认的 API 或平台节点，不表示所有设备从该版本起都支持相同刷新率范围。设备还要满足面板、Composer HAL、vendor policy、系统 flag 和功耗配置。

延伸阅读：

- [Adaptive Refresh Rate](../../part1-fundamentals/ch02-rendering/18-adaptive-refresh-rate.md)：ARR 的 Composer3、expected-present 与能力边界。
- [刷新率切换机制](../../part1-fundamentals/ch02-rendering/19-refresh-rate-switching.md)：从 policy 到 HWC mode switch 的基础路径。
- [VSYNC、Scheduler 与 DisplayFrameRate](../../part1-fundamentals/ch02-rendering/23-vsync-scheduler-displayframerate.md)：物理刷新率、render rate 和应用 callback 的关系。

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

内核边界核对 `android17-6.18-2026-06_r6` 的 DRM vblank、atomic helper、dma-fence 与 sync_file；vendor 面板和 Composer 实现不在 common kernel 结论范围内。

本文也吸收了 `rendering_pipelines` 中视频、游戏与公共显示路径的排障基线：请求值必须和 buffer readiness、latch、FrameTimeline、HWC present 共同取证，刷新率选择不能替代逐帧证据。
