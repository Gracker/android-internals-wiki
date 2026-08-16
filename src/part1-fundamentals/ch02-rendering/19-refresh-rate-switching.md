---
title: "刷新率切换与帧率适配性能"
chapter: "2.19"
section: "2.19"
status: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: AOSP android-17.0.0_r1, Composer3 AIDL, Perfetto android-17.0.0_r1, kernel android17-6.18-2026-06_r6, Android MRR / frame-rate / ARR 官方文档, Writer rendering_pipelines S01 / S08 / S12
confidence: high
sources:
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
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_atomic_helper.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
- type: official-doc
  path: https://source.android.com/docs/core/graphics/multiple-refresh-rate
- type: official-doc
  path: https://source.android.com/docs/core/graphics/arr
- type: official-doc
  path: https://developer.android.com/media/optimize/performance/frame-rate
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S08_native_graphics_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
tags: [refresh-rate, frame-rate, SurfaceFlinger, VSync, setFrameRate, jank, rendering, display-mode, ARR]
related_chapters: ["2.2", "2.3", "2.4", "2.6", "2.18"]
---

# 2.19 刷新率切换与帧率适配性能

刷新率变化附近出现掉帧时，先分清三个时刻：

1. SurfaceFlinger 选出了新的显示模式；
2. Composer HAL 开始执行模式切换；
3. SurfaceFlinger 将目标模式更新为 active。

第三步有两种完成方式：DisplayCommand modeset（通过显示命令切换模式）成功且不要求刷新帧时，平台立即更新 active（当前生效）状态；HAL（硬件抽象层）要求先提交刷新帧时，SurfaceFlinger 会等待相关 `FrameTarget`（本轮显示提交的状态记录）退出待定状态。后一条路径用到 present fence（显示提交完成信号）状态，但 fence 只能证明对应显示提交已经完成，不能单独证明面板内部的 PLL（Phase-Locked Loop，锁相环）、命令序列或扫描周期。

这些时刻可能相隔若干次合成。只看应用主线程、`Choreographer#doFrame` 或某一帧的 CPU 耗时，无法证明显示模式是否已经切换，也无法证明掉帧由模式切换引起。

平台源码以 Android 17/API 37 的 `android-17.0.0_r1` 为锚点，以下内容讨论离散多刷新率显示（Multiple Refresh Rate，MRR）的模式切换、应用帧率请求和系统侧诊断。ARR（Adaptive Refresh Rate，自适应刷新率）面板可在同一配置内按 TE/VSync 同步信号的离散倍数改变刷新节奏，无需为每次节奏变化切换显示配置；相关机制见 [2.18 自适应刷新率：原理、接口与策略](18-adaptive-refresh-rate.md)。

## 1. 先区分三类变化

“帧率变了”可能指三件不同的事。它们的控制路径、可见现象和诊断证据都不同。

| 变化 | Android 17 中的含义 | 是否一定调用 HWC（Hardware Composer，硬件合成器）modeset |
|---|---|---|
| Render rate（内容渲染帧率）变化 | SurfaceFlinger 改变调度和合成节奏，物理 display mode 不变 | 否 |
| MRR 模式切换 | 在多个离散 display mode 之间切换，例如 60 Hz → 120 Hz | 是 |
| ARR 刷新节奏调整 | 在一个 ARR 配置内按 TE/VSync 的离散倍数改变刷新或自刷新间隔；配置的 `vsyncPeriod` 仍表示 TE/VSync 基准 | 否，走 ARR cadence（连续帧展示节奏）提示与面板自刷新控制路径 |

### 1.1 Render rate 变化不等于显示模式切换

Android 17 的 `DisplayModeController::setDesiredMode()` 会比较请求中的物理模式和当前模式：

- 物理模式没有变化，只有 `renderRate` 变化时，返回 `InitiateRenderRateSwitch`；
- 物理模式变化时，返回 `InitiateDisplayModeSwitch`；
- 请求与当前状态相同，或者已有相同请求在处理时，不启动新的切换。

Perfetto 中看到应用或 SurfaceFlinger 的调度频率变化时，不能直接写成“面板从 60 Hz 切到了 120 Hz”，还需要查看 `ActiveModeFps` 等显示模式证据。

### 1.2 MRR 是离散配置之间的切换

MRR 设备向系统暴露多个显示配置。每个配置包含分辨率、VSync 周期以及 `configGroup` 等属性。SurfaceFlinger 在显示策略允许的范围内，根据可见 Layer（图层）的请求、内容检测结果和系统信号选择候选模式。

MRR 不意味着应用能指定最终模式。`Surface.setFrameRate()` 提供内容帧率偏好，调度器还要考虑：

- DisplayManager 下发的最小、最大和默认模式策略；
- 前台 Layer 的帧率投票及其可见性、焦点状态；
- 省电模式等系统限制；
- 设备支持的模式及其切换能力；
- 厂商在平台允许范围内加入的策略。

应用必须能在请求没有被满足时正常运行。

### 1.3 ARR 在一个配置内调整实际刷新节奏

Android 15 QPR1 起的平台 ARR 支持允许兼容硬件在一个显示配置内调整实际刷新节奏。ARR 配置中的 `DisplayConfiguration.vsyncPeriod` 表示 TE 信号周期；面板可以在满足 `minFrameIntervalNs` 的前提下，选择 TE/VSync 周期的离散倍数来展示下一帧。Android 17 中，`FRAME_RATE_CATEGORY_*`、`requestedFrameRate` 以及平台的启发式分类可参与 ARR 决策。

ARR 减少了频繁切换离散模式的需求，却不会消除应用自身的帧生产抖动、错误的 presentation timestamp（期望显示时间戳）、GPU 超预算或 HWC 合成延迟。排查时仍要把“应用生产”“SurfaceFlinger 合成”“显示消费”分开观察。

## 2. 无缝切换的契约

### 2.1 `configGroup` 表达什么

Composer3 的 `DisplayConfiguration.configGroup` 是显示配置分组标识。同组配置除 VSync 周期外，其余属性应当相似，Android 可以据此识别“只改变刷新率”的候选配置。

同组是请求无缝切换的必要条件，但不是硬件一定能在当前时刻无缝切换的保证。Composer3 对两类失败作了区分：

- `EX_SEAMLESS_NOT_ALLOWED`：请求要求无缝，但目标配置与当前配置不在同一组；
- `EX_SEAMLESS_NOT_POSSIBLE`：配置关系允许无缝切换，但显示硬件在当前条件下无法避免可见伪影。

当条件变化后，Composer HAL 可以通过 `onSeamlessPossible` 回调通知客户端重试。应用不应假设“同分辨率”或“同组”就必然立即切换成功。

### 2.2 应用如何表达是否接受非无缝切换

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

### 2.3 `getAlternativeRefreshRates()` 的边界

Android 12/API 31 增加了 `Display.Mode.getAlternativeRefreshRates()`。返回值表示：如果系统在当前模式与这些刷新率之间切换，该切换保证无缝。它不承诺系统会切换，也不绕过显示策略。

只想表达刷新率偏好时，应优先使用 `Surface.setFrameRate()` 或 `WindowManager.LayoutParams.preferredRefreshRate`。`preferredDisplayModeId` 还会绑定分辨率等模式属性，更适合确实需要指定某个显示模式的场景。

## 3. Android 17 的模式切换状态机

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

### 3.1 选择候选模式

`RefreshRateSelector` 对 Layer 需求、显示策略和全局信号进行评分。Android 17 源码没有一张固定的“视频最高、动画居中、静态最低”优先级表；结果取决于投票类型、焦点、候选模式、无缝约束和策略范围。

`Surface.setFrameRate()` 的兼容性参数在 `LayerHistory` 中映射为不同投票：

| 应用参数 | SurfaceFlinger 投票语义 | 适用内容 |
|---|---|---|
| `FRAME_RATE_COMPATIBILITY_DEFAULT` | `ExplicitDefault` | 游戏及一般渲染 |
| `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` | `ExactOrMultiple` | 固定帧率视频 |
| `FRAME_RATE_COMPATIBILITY_AT_LEAST` | `Gte`（greater than or equal，不低于请求值）；MRR 上按高刷新倾向处理 | UI 动画、滚动、fling |

`AT_LEAST` 从 API 36 提供，适合 UI 动画一类“显示刷新率至少达到请求值”的需求。它不适合作为普通游戏的默认选择；游戏应先使用 `DEFAULT`，再根据稳定帧率和功耗目标调整请求。

### 3.2 `desired`：记录最新请求

SurfaceFlinger 调用 `DisplayModeController::setDesiredMode()`。同一帧内出现多个请求时，控制器保留最新的 desired 请求，后续在合成边界处理。

若需要物理模式切换，`SurfaceFlinger::setDesiredMode()` 会：

- 请求调度下一次合成；
- 让 Scheduler 针对目标模式重新同步 VSync 预测模型；
- 通过 `VsyncModulator` 进入刷新率变化期间的调度状态；
- 标记有待处理的模式变化。

这里表示系统准备切换，尚不能说明硬件已采用新模式。

### 3.3 `pending`：向 Composer HAL 发起切换

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

### 3.4 `active`：完成平台侧状态更新

需要刷新帧的模式切换不会在命令提交后立即被记为 active。Android 17 的 commit（提交）路径通过 `FrameTarget::isFramePending()` 检查相关前序显示提交；该状态包含 present fence 的完成情况：

- `FrameTarget` 仍 pending：安排下一帧，继续等待；
- `FrameTarget` 退出待定状态：调用 `finalizeDisplayModeChange()`；
- 完成后更新 active mode、active render rate 和 `RefreshRateSelector` 的当前模式。

DisplayCommand modeset 成功且 `refreshRequired = false` 时不经过这段等待，SurfaceFlinger 会立即 finalize（完成状态更新）。对于需要等待的路径，present fence 给出了“对应显示提交已经完成”的时序证据，通常比请求发起时间更接近用户看到新模式的时刻；它仍不能独立测量面板内部时序。

### 3.5 分辨率切换要单独分析

跨配置组切换可能同时改变分辨率。Android 17 在完成模式切换时会区分纯刷新率变化和分辨率变化；后者还可能触发 `DisplayDevice` 或 framebuffer（帧缓冲）相关重建。

跨分辨率模式切换的代价不能套用纯 60 Hz → 120 Hz 刷新率切换的结论。trace、`dumpsys` 和 HWC 日志都应同时记录模式 ID、分辨率、`configGroup` 与刷新率。

## 4. 切换附近为什么会出现卡顿

### 4.1 帧预算突然改变

从 60 Hz 切到 120 Hz 后，一次刷新周期从约 16.67 ms 变为约 8.33 ms。即使硬件完成无缝切换，应用的 CPU 与 GPU 负载若只能稳定在 60 fps，画面也不会自动变成稳定 120 fps。

游戏尤其需要区分：

- 屏幕已经在 120 Hz；
- 游戏请求了 120 FPS；
- 游戏引擎能否持续按 8.33 ms 预算生产帧。

第三项需要用 FrameTimeline、CPU/GPU slice（时间片段）和 present timing（显示时序）证明，不能由 display mode 推断。

### 4.2 受约束切换的 HAL 时间线可能要求额外刷新帧

`setActiveModeWithConstraints()` 路径中的某些显示实现需要 SurfaceFlinger 在切换前发送一帧，Composer HAL 会通过 `refreshRequired` 和 `refreshTimeNanos` 明确表达。若该帧准备、合成或显示较晚，切换窗口附近会出现较长帧。Android 17 的 DisplayCommand modeset 成功路径明确填写 `refreshRequired = false`，不能把“额外刷新帧”当成所有模式切换的固定步骤。

这里没有固定的“一到三帧”规则。持续时间取决于面板、显示控制器、Composer 实现、当前队列和切换类型，必须从目标设备的 trace 与 HAL 证据得出。

### 4.3 非无缝切换可以产生可见中断

电视、机顶盒及部分面板在切换模式时可能黑屏。Android 默认不会仅因 `setFrameRate()` 请求而选择这类非无缝切换；应用和用户都允许后，系统才可以采用。

把这种显示中断记作应用掉帧会误导优化方向。应用时间线可能平稳，显示输出却在模式重配置期间不可见。

### 4.4 模式切换和队列抖动可能同时发生

应用开始播放视频或进入战斗场景时，通常会同时发生资源加载、解码器启动、Surface 更新和帧率请求。一次 trace 中，“切换计数器变化”和“jank（卡顿）帧”相邻只能说明时间接近，不能直接证明因果。

确认因果至少要回答：

1. 新模式请求何时进入目标状态；
2. 何时进入 pending，何时成为 active；
3. jank 帧阻塞在应用、GPU、SurfaceFlinger 还是显示阶段；
4. 对照实验中禁用模式切换后，其他工作负载是否保持不变。

## 5. 应用如何提交正确的帧率请求

### 5.1 视频：提交源的准确帧率

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

### 5.2 游戏：请求可持续的目标

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

### 5.3 普通 UI：让 View 系统表达分类

Android 17 上，普通 View/Compose UI 优先使用框架提供的 ARR 与 View 帧率分类能力。若有明确的自定义动画需求，可对合适的 View 使用 `requestedFrameRate` 或 frame-rate category（帧率类别）。

直接对 Window 或 Surface 设置长期高帧率偏好，会影响整个 Surface。只有一个局部动画时，这个请求范围往往过大。调用频率也要受控：在场景状态变化时更新，不要跟随每一帧的瞬时耗时来回请求。

### 5.4 多 Surface：分别报告各自内容

画中画、分屏、视频控件加 UI 覆盖层时，各 Surface 应报告自身内容帧率。不要把多个 Surface 的需求预先合成一个值再提交给所有 Surface。

SurfaceFlinger 负责在多个 Layer 之间选择显示模式。应用若把 UI、视频和游戏画面全部写成同一个高帧率，会丢失内容信息，也会让系统无法做出合理选择。

## 6. 用 Perfetto 判断切换发生在哪里

### 6.1 先看 Android 17 的四组显示计数器

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

### 6.2 再看选择过程

SurfaceFlinger 的 trace 中可见 `Refresh Rate Selection` 一类选择区间。它适合回答“为什么候选模式改变”，但选择区间结束不等于面板完成切换。

分析顺序建议固定为：

1. 找到用户可见的 jank 帧；
2. 查看相邻时间内的 `HasDesiredMode` 和选择事件；
3. 查看 `PendingModeFps` 到 `ActiveModeFps` 的间隔；
4. 对齐 SurfaceFlinger commit、present fence 和 FrameTimeline；
5. 回到应用、RenderThread、GPU/HWC 路径确定最长阶段。

### 6.3 FrameTimeline 回答帧卡在哪里

FrameTimeline 可以区分应用生产帧和 SurfaceFlinger 展示帧的 deadline（截止时间）。常见组合包括：

| 证据 | 更可能的方向 |
|---|---|
| 应用帧已 missed（错过截止时间），模式计数器无变化 | 应用 CPU/GPU 或帧节奏问题 |
| 应用按时完成，SurfaceFlinger 帧 missed，恰有 pending 窗口 | 继续检查 HWC、present fence 和切换时间线 |
| `ActiveModeFps` 已改变，后续应用连续 missed | 新帧预算下应用负载过高 |
| 只有 `RenderRateFps` 改变 | 先按调度/帧节奏问题分析，不要归因于 modeset |

Perfetto 展示的是时序证据。某个 OEM（设备厂商）是否在显示驱动内执行 PLL 重配置、面板命令序列如何安排，要用该设备的 Composer、内核或固件资料确认，不能由通用 AOSP trace 名称推断。

### 6.4 `dumpsys` 适合看快照

`dumpsys SurfaceFlinger` 和 `dumpsys display` 可用于确认当前 active mode、策略范围和支持模式。`dumpsys` 输出是采样时刻的状态快照，不适合测量一次短暂切换的起止时间。

开发者选项中的“显示刷新率”overlay（屏幕叠加层）也只适合快速确认当前值。做因果分析时，仍以 Perfetto 计数器、FrameTimeline 和显示路径 fence 为准。

## 7. 三个常见场景

### 7.1 视频开始或暂停

视频开始播放时，播放器设置准确源帧率，SurfaceFlinger 可能选择匹配模式或其整数倍。若只允许无缝切换，系统也可能保持当前模式。

暂停后：

- Surface 继续可见且不再提交帧：清除帧率偏好；
- Surface 隐藏或销毁：无需额外清除；
- 暂停画面上仍有 UI 动画：UI Surface 应继续提交自己的需求。

诊断时同时记录解码器启动和首帧提交。首帧慢与显示模式切换可以落在同一个时间窗口。

### 7.2 游戏菜单进入战斗

菜单可能稳定在较低帧率，战斗场景请求更高帧率。切换前先确认目标帧率能否持续达到；否则显示进入高刷新模式后，GPU 仍会不断错过更短的 deadline。

比较实验应至少保留：

- 相同画质和负载，只固定显示模式；
- 相同显示模式，只改变游戏目标帧率；
- 同时查看 `ActiveModeFps`、FrameTimeline 和 GPU 完成时间。

这样才能区分“模式切换瞬间的显示延迟”和“高刷新率下长期性能不足”。

### 7.3 相机与系统转场

不能把“相机一定运行在 60 Hz、桌面一定运行在 120 Hz”当作平台规则。相机预览帧率、相机应用的 Surface 请求、系统动画、厂商显示策略和面板能力都会改变结果。

从相机进入多任务时，应先用 trace 确认是否有 `PendingModeFps` 和 `ActiveModeFps` 变化。如果没有物理模式变化，就应继续检查预览 Surface 消失、窗口动画、GPU 合成和 RenderThread，而不能按刷新率切换问题修复。

## 8. 平台、HAL 与内核的责任边界

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

## 9. 版本边界

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

## 10. 常见误区

### 误区一：`setFrameRate(60)` 会把屏幕固定到 60 Hz

它是内容偏好。系统可能选择 60 Hz、可整除的更高刷新率，或因策略限制保持当前模式。

### 误区二：同组模式一定能立即无缝切换

同组只满足配置关系约束。当前硬件条件不允许时，HAL 仍可返回 `EX_SEAMLESS_NOT_POSSIBLE`。

### 误区三：看到 VSync 周期变化就说明发生了 modeset

ARR 或 render rate 调整也会改变调度观测。需要 `PendingModeFps`、`ActiveModeFps` 和显示路径证据确认 MRR modeset。

### 误区四：高刷新率一定更流畅

高刷新率缩短了帧预算。应用若不能稳定生产帧，呈现间隔仍会抖动，还会增加功耗。

### 误区五：相机、多任务、游戏都有固定刷新率

Android 平台没有这种通用映射。结果由内容请求、系统策略、设备模式和厂商实现共同决定。

### 误区六：一次相邻事件足以证明因果

模式计数器变化与 jank 帧相邻只能作为线索。还要检查 pending 窗口、FrameTimeline 阶段、present fence，并做控制变量实验。

## 11. 排查清单

1. 记录设备支持模式、当前模式、`configGroup` 和系统刷新率设置。
2. 明确应用设置帧率的 Surface、准确值、compatibility 和 change strategy。
3. 在 Perfetto 中定位 `HasDesiredMode`、`PendingModeFps`、`ActiveModeFps`、`RenderRateFps`。
4. 用 FrameTimeline 判断应用还是 SurfaceFlinger 错过截止时间。
5. 对齐 HWC 与 present fence，确认模式何时完成。
6. 区分纯刷新率切换、跨分辨率切换、render rate 调整和 ARR 刷新节奏变化。
7. 在目标设备上核对 Composer 与内核日志，不用芯片平台经验替代证据。
8. 固定显示模式做对照实验，避免把同时发生的解码、加载或 GPU 压力误归因给 modeset。

## 参考资料

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
- [AOSP：Adaptive refresh rate](https://source.android.com/docs/core/graphics/arr)
- [Android Developers：Frame rate](https://developer.android.com/media/optimize/performance/frame-rate)
- [Android Developers：`Surface.setFrameRate()`](https://developer.android.com/reference/android/view/Surface#setFrameRate(float,int,int))
- [Android Developers：`Display.Mode.getAlternativeRefreshRates()`](https://developer.android.com/reference/android/view/Display.Mode#getAlternativeRefreshRates())
- [Android Developers：Optimize refresh rates for games](https://developer.android.com/games/optimize/display-refresh-rate-change)
- [Android Developers：Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [`android17-6.18-2026-06_r6`：DRM VBlank](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c)
- [`android17-6.18-2026-06_r6`：DRM atomic helper](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_atomic_helper.c)
- [`android17-6.18-2026-06_r6`：DMA fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
