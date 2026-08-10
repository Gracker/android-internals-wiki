---


task2b_rework_date: "2026-05-25T11:23:10+08:00"

title: Adaptive Refresh Rate 与动态帧率控制
chapter: '2.18'
section: '2.18'
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
applicable_versions: ARR 主体：Android 15-QPR1 - Android 17 (API 37)；背景：Android 11-14 多刷新率支持
last_verified: '2026-07-25'
last_verified_against: "Android 17 / API 37 / android-17.0.0_r1；android17-6.18-2026-06_r6；Composer3 v3+；Android ARR 与 Perfetto 官方文档；Writer rendering_pipelines S01/S08/S12"
confidence: high
sources:
- type: official
  path: https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
- type: official
  path: https://source.android.com/docs/core/graphics/arr
- type: official
  path: https://developer.android.com/reference/android/view/Display
- type: official
  path: https://developer.android.com/reference/android/view/View
- type: official
  path: https://developer.android.com/reference/android/view/Surface
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer.FrameData
- type: official
  path: https://developer.android.com/games/sdk/frame-pacing
- type: research
  path: intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Window.java
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
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/diagrams/S01_baseline_12_anchor_pipeline/source.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S08_native_graphics_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
tags:
- ARR
- refresh-rate
- VSync
- SurfaceFlinger
- Choreographer
- LTPO
- frame-pacing
- Android-17
related_chapters:
- '2.2'
- '2.3'
- '2.4'
- '2.6'
- '2.13'
- '2.16'
task6_state: "reviewed"
task2b_state: "fixed"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-14"
task6_result: pass-light-edit
task2b_result: "fixed"
last_task2b_at: '2026-05-17T19:17:39'
repaired_date: '2026-04-26'
repaired_by: openclaw-task2b
task6_reviewed_date: "2026-06-14"
last_task6_at: "2026-06-14T13:08:00+08:00"
last_task6_review_log: "logs/review/2026-06-14-13-review.md"
task6_review_notes: "2026-06-14 Task6 revisiting review: 全文 L1-L4 扫描通过，零禁用词，零填充词，零翻译腔。确实(1次)功能用法。2个[待验证]标注合理。Task9 auto-fix(EarlyGpu)已纳入。无L1/L2需修，无B类大问题。自动晋升finalized。"
status: "finalized"
pipeline_stage: "ready-to-publish"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-14"
last_task9_at: "2026-06-14T12:30:44+08:00"
last_task9_review_log: "logs/deep-review/2026-06-14-12-audit.md"
task9_review_notes: "2026-06-14 Task9 idle audit:auto-fixed VsyncModulator config name EarlyGl -> EarlyGpu against AOSP android-16.0.0_r1;no queue entry;returned to Task6."
p0: 0
p1: 0
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-14
last_task9_audit: "2026-06-14"
last_task9_autofix_at: "2026-06-14"
---


# 2.18 Adaptive Refresh Rate 与动态帧率控制

固定刷新率设备给人的错觉是：60Hz 的帧预算永远是 16.67ms，120Hz 永远是 8.33ms。支持自适应刷新率（Adaptive Refresh Rate，ARR）的设备会按内容更新节奏改变显示间隔。滚动时可以提高刷新率，页面静止后可以降低刷新率。此时再拿固定的 16.67ms 阈值检查每一帧，会把正常降频误判成卡顿，也可能漏掉高刷场景中的超时。

理解 ARR 要先分清三个量：

- **内容帧率（content/render rate）**：应用或某个图层产生新帧的节奏，例如视频 24fps、UI 60fps、游戏 120fps。
- **显示刷新率（display refresh rate）**：面板更新屏幕图像的节奏。
- **VSync/TE 信号频率**：系统和面板用来对齐时序的硬件节拍。ARR 配置里，它可以高于显示刷新率。

应用只能表达内容需求和偏好。最终刷新率还要同时满足用户设置、低电量模式、温度策略、其他可见图层、显示硬件能力和厂商策略。任何 `setFrameRate` 或视图投票都不等于“强制屏幕切到某个 Hz”。

## 1. 多刷新率与 ARR 是两套机制

### 1.1 Android 11—14：在多个固定模式之间选择

Android 11（API 30）公开 `Surface.setFrameRate()` 后，应用可以声明 Surface 的内容帧率。传统多刷新率（Multiple Refresh Rate，MRR）设备通常提供若干固定显示模式，例如 60Hz 和 120Hz。系统需要改变 active mode 才能改变物理刷新节奏；部分切换可以无缝完成，另一些切换可能出现短暂黑屏或时序抖动。

Android 12（API 31）的三参数 `Surface.setFrameRate()` 允许应用说明是否接受非无缝切换。这仍属于 mode switching：候选对象是若干固定模式。

### 1.2 Android 15 起：同一显示配置内改变刷新间隔

Android 15 引入 ARR 平台能力。面向应用的官方指南把可用边界写为 Android 15-QPR1 及以上，并要求设备实现对应的 Composer HAL 接口。系统版本满足条件仍不够，应用应在 API 36 及以上调用 `Display.hasArrSupport()` 检查当前 Display。

ARR 配置中，显示 VSync/TE 信号频率与实际刷新率可以解耦。面板按照 TE 周期接收机会，但不必在每个 TE 都刷新；实际刷新率只能取 TE 频率的整数分频。

以官方示例为例：

- `vsyncPeriod = 4.16ms`，对应 240Hz TE；
- `minFrameIntervalNs = 8.33ms`，表示两次有效刷新至少间隔 8.33ms，因此最高刷新率是 120Hz；
- 之后可以在满足最小间隔的 TE 边界展示新帧，例如 120Hz、80Hz、60Hz 等离散档位。

`DisplayConfiguration.vrrConfig != null` 表示该显示配置支持 ARR；`vrrConfig == null` 表示普通非 ARR 配置。Composer3 的定义要求一个配置按 ARR 或 MRR 解释，不能把同一个配置同时描述成两者。

LTPO 常用于实现宽范围刷新率，但 Android 公共 API 没有要求应用先判断面板材料。应用需要关注 `hasArrSupport()`、系统支持的 render rate 和自身内容节奏。

## 2. Android 17 的控制链

把系统路径拆成“约束候选范围”和“按内容选择”两段，会更容易读懂源码。

### 2.1 DisplayModeDirector 先计算允许范围

Android 17 的 `DisplayModeDirector#getDesiredDisplayModeSpecs(int)` 从 `VotesStorage` 读取全局投票和指定 Display 的投票，再由 `VoteSummary` 合并约束。输入包括：

- 用户设置的最低、峰值和默认刷新率；
- 低电量、亮度、温度与系统策略；
- 应用请求的尺寸、物理刷新率范围和 render frame-rate 范围；
- 是否允许同组或跨组 mode switching；
- 设备支持的模式、ARR 能力和工作时长配置。

结果是 `DesiredDisplayModeSpecs`：其中包含 base mode、primary/app-request 两组物理/渲染帧率区间，以及 `allowGroupSwitching` 等信息。`DisplayManagerService.DesiredDisplayModeSpecsObserver` 把结果写入 `LogicalDisplay`，`LocalDisplayAdapter` 再转换为 `SurfaceControl.DesiredDisplayModeSpecs` 交给 SurfaceFlinger。

这一段决定“哪些模式和帧率仍可被选择”，不负责逐帧估算当前内容需要多少 Hz。

### 2.2 SurfaceFlinger Scheduler 再按可见内容选择

SurfaceFlinger 完成 transaction flush 和 buffer latch 后，Android 17 在 `SurfaceFlinger.cpp` 的 `Refresh Rate Selection` trace 区间调用：

```cpp
mScheduler->chooseRefreshRateForContent(
        &mLayerHierarchyBuilder.getHierarchy(),
        updateAttachedChoreographer);
```

这段代码说明选择发生在图层状态更新之后。`Scheduler::chooseRefreshRateForContent()` 先让 `LayerHistory` 汇总可见内容，再把 content requirements 应用到刷新率策略。产生 mode request 后，SurfaceFlinger 仍会调用 `RefreshRateSelector::isModeAllowed()` 检查候选是否符合 DisplayManager 下发的范围。

因此，分析“为什么没有升到 120Hz”时，至少要同时检查：

1. Layer 有没有给出帧率偏好，更新节奏又是多少；
2. 用户峰值刷新率、低电量和温度策略是否收窄范围；
3. 当前显示配置是 MRR 还是 ARR；
4. 其他可见图层是否给出更高或不兼容的请求；
5. Scheduler 最终选择的 render rate 和模式。

### 2.3 Composer HAL 把 ARR 节拍交给显示硬件

ARR 设备需要 Composer3 v3 或更高版本的接口。Android 17 的关键字段和调用如下：

- `DisplayConfiguration.vsyncPeriod`：ARR 配置中表示 TE 信号周期；
- `VrrConfig.minFrameIntervalNs`：两次展示之间的最小间隔，也就是该配置的最高刷新率边界；
- `DisplayCommand.frameIntervalNs`：提示后续帧的节拍；
- `IComposerClient.notifyExpectedPresent()`：在下一帧偏离既有节拍，或空闲时间超过 HAL 声明的 timeout 时，提前通知期望展示时间与后续间隔。

SurfaceFlinger 的 `onExpectedPresentTimePosted()` 会读取当前模式的 `VrrConfig.notifyExpectedPresentConfig`。`notifyExpectedPresentIfRequired()` 判断下一帧是否仍在原节拍内、是否超时；需要通知时，再经 `HWComposer::notifyExpectedPresent()` 进入 Composer HAL。

`notifyExpectedPresentConfig == null` 时，框架不会调用这项 HAL 提示；`timeoutNs == 0` 表示每帧都要提示。非零 `headsUpNs` 则给出提示必须领先下一次 expected-present 的最短时间。它们描述的是显示硬件需要多少准备时间，不是应用可支配的额外帧预算。

这套接口允许面板在不切换模式的情况下准备下一次刷新。它无法替应用修复晚提交、错误时间戳、BufferQueue 堆积或 acquire fence 过晚的问题。

### 2.4 VsyncModulator 负责工作预算，不负责选择刷新率

`VsyncModulator` 经常和刷新率切换同时出现在 Trace 中，但职责不同。Android 17 的 `VsyncModulator` 在以下配置间切换：

- `Early`：刷新率正在变化、有提前唤醒请求或近期 transaction；
- `EarlyGpu`：近期使用 GPU composition；
- `Late`：常规状态。

这些配置调整应用与 SurfaceFlinger 的 work duration/offset，让事务、GPU 合成或 mode transition 获得合适的执行时间。刷新率由 Display policy、`LayerHistory` 和 `RefreshRateSelector` 决定，`VsyncModulator` 只改变调度预算。看到 `Vsync-Early` 或 `Vsync-EarlyGpu` counter 时，不能把它当成刷新率选择结果。

## 3. 普通 UI：优先使用 View 和 Compose

多数 View 应用无需改代码也能从 ARR 获益。系统会收集本帧发生重绘的 View 投票，合并后把偏好传到下层图层。常规策略倾向于采用最高的有效投票，但实现细节可能随平台版本调整。

### 3.1 View 的类别投票

Android 17 中常用的类别是：

- `REQUESTED_FRAME_RATE_CATEGORY_DEFAULT`：清除显式请求，恢复框架默认判断；
- `REQUESTED_FRAME_RATE_CATEGORY_NO_PREFERENCE`：该 View 明确不影响本帧帧率选择；
- `REQUESTED_FRAME_RATE_CATEGORY_NORMAL`：适合普通动画，通常接近 60Hz；
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

`setRequestedFrameRate()` 也接受 30、60、120 等正数。数值表示内容偏好，不要求它正好等于设备的物理刷新率。多个数值投票互为整数倍时，框架通常取较高值；不互为整数倍时，超过 60Hz 的请求按 `High` 倾向处理，其余按 `Normal` 倾向处理。官方文档明确说明这套合并策略可能调整，业务代码不应依赖精确的内部优先级。

还有两条容易遗漏的边界：

- View 只有在需要重绘时才参与当前帧投票；
- 在 `ViewGroup` 上设置请求不会自动传给所有子 View。

Android 17 `View.java` 仍含受 flag 管理的 `REQUESTED_FRAME_RATE_CATEGORY_LOW`。当前 ARR 开发指南的标准类别列表没有把 `LOW` 作为普通应用的主要入口。若项目准备使用它，应以所用 `compileSdk`、设备 flag 和 API 文档为准；通用代码优先使用 `DEFAULT`、`NO_PREFERENCE`、`NORMAL`、`HIGH` 或明确的正数。

### 3.2 滚动组件要提供速度

触摸按下期间，系统通常通过 touch boost 提高 render rate；手指抬起进入 fling 后，刷新率可以随速度下降。`ScrollView`、`ListView`、`GridView` 已接入这类策略。AndroidX 侧至少需要：

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

### 3.3 Compose 入口

Compose 1.9 提供 `Modifier.preferredFrameRate(...)`，可以传具体帧率或 `FrameRateCategory`。它表达的是 Composable 的偏好，最终仍由窗口、其他内容与显示策略共同决定。无需为“启用 ARR”而把整个界面固定在 High；默认策略不足时，再对有明确体验问题的局部动画增加请求。

### 3.4 Window 级开关

Android 15（API 35）提供两个 Window 级控制：

- `setFrameRateBoostOnTouchEnabled(boolean)`：控制触摸时是否升频，默认启用；
- `setFrameRatePowerSavingsBalanced(boolean)`：控制该 Window 是否允许 ARR 的功耗平衡策略，默认启用。

关闭 touch boost 会影响触摸响应；关闭 power-savings balance 可能增加高刷新率驻留时间和功耗。官方指南只建议在出现严重兼容问题时关闭，并要求用目标设备上的 Trace 和功耗数据证明必要性。

## 4. Surface：给独立图层声明内容节奏

视频、游戏引擎、自建 EGL/Vulkan Surface 或独立 `SurfaceView` 更常直接使用 `Surface.setFrameRate()`。Android 17 中，兼容性参数应按内容类型选择：

| 内容 | compatibility | 含义 |
|---|---|---|
| 视频 | `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` | 内容帧率固定，系统应优先选择便于形成整数节拍的显示刷新率 |
| 游戏 | `FRAME_RATE_COMPATIBILITY_DEFAULT` | 游戏可以适应系统最终选择的 render rate |
| UI、动画、滚动、fling | `FRAME_RATE_COMPATIBILITY_AT_LEAST` | API 36 起，请求显示帧率不低于给定值 |

下面的代码分别声明 24fps 视频和最低 60fps 的 UI Surface，并在内容结束时清理旧请求：

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

`frameRate` 可以不是设备公开的物理档位。系统可能让 24fps 内容运行在 48、72、120Hz 等兼容节奏上，也可能因其他图层或策略维持当前模式。

`setFrameRate()` 只影响 SurfaceFlinger 对显示帧率的选择，不会限制 Producer 产帧速度。它可能间接改变 Choreographer 回调时间和 buffer 释放间隔，但不能代替 frame pacing。引擎仍需控制 `eglSwapBuffers()`、`vkQueuePresentKHR()` 或播放器提交时间戳，否则高频生产会填满队列，增加输入延迟。

Android 17（API 37）的 `Surface.setProducerThrottlingEnabled()` 调整 EGL/Vulkan 生产者在入队阶段承受的 CPU backpressure，属于队列节拍控制，不是刷新率投票。该 API 的细节见 2.17；排查 ARR 时应分别检查 `setFrameRate()` 的投票和生产者限速。

## 5. Display 与 Choreographer 能查到什么

### 5.1 Display 能力查询

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
- `getSupportedRefreshRates()` 从 API 21 就存在，但 API 36 起返回 Display 支持的 render rate；API 35 及以下只返回默认模式的刷新率，需要更多物理模式时读取 `getSupportedModes()`；
- 多屏、折叠屏内外屏或外接显示器的能力可以不同，窗口迁移 Display 后要重新查询。

Android 17 的 `DisplayInfo#getRefreshRate()` 会优先返回应用可感知的 override/render frame rate；没有这两项时才回退到 active mode refresh rate。`Display.getRefreshRate()` 因而适合观察当前框架报告给应用的节奏，但一次读取不能证明整个测试区间的 ARR 行为。诊断仍应记录持续变化和实际 present。

### 5.2 Choreographer.FrameData 没有 refreshRate 字段

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

`FrameData` 只在回调期间有效，也没有公开 `refreshRate` 字段。不能把内部 `DisplayEventReceiver.VsyncEventData` 的字段写进应用示例。判断节奏变化时，应结合连续回调间隔、Display 信息和系统 Trace。

## 6. Perfetto：先确认刷新节奏，再判断卡顿

ARR Trace ARR 跟踪数据时，不应先套用“是否超过 16.67ms”的固定阈值。可以按以下顺序观察。

### 6.1 先记录测试条件

至少记录设备与固件、Display、分辨率、亮度、用户刷新率设置、低电量模式、温度、应用版本、内容类型和目标帧率。游戏还要记录 Game Mode、FPS intervention 和引擎节拍配置。缺少这些条件，跨设备或跨版本的 Hz 对比没有可重复性。

### 6.2 在同一时间窗内看四组证据

1. **App 节拍**：`vsync-app`、`Choreographer#doFrame` 或引擎 frame marker；
2. **内容生产**：RenderThread、EGL/Vulkan present、BufferQueue 和 acquire/release fence；
3. **系统选择**：SurfaceFlinger 的 `Refresh Rate Selection`、active mode、render rate 与相关 counter；
4. **最终显示**：FrameTimeline、SurfaceFlinger DisplayFrame、HWC 展示围栏和设备显示驱动事件。

滑动期间应用节拍变短，fling 减速后逐步变长，同时 FrameTimeline 没有连续卡顿，通常符合 ARR 策略。若 mode change 附近出现黑屏或长间隔，更接近传统 MRR 的非无缝切换。若 Producer 已经晚交 buffer，刷新率变化只是背景条件，不能把根因写成 SurfaceFlinger 选错档位。

Perfetto 官方文档目前对 SurfaceView 的 FrameTimeline 支持有限。标准 HWUI 应用窗口可以优先查看 App actual/expected timeline；SurfaceView、视频和游戏还需要核对独立图层、buffer timestamp、fence、HWC 与 present。

### 6.3 用正确的键关联期望与实际 FrameTimeline

以下查询用于检查指定进程的应用 FrameTimeline。它沿用 Android 17 Perfetto 指标的关联方式，以 `upid + name` 连接 expected 与 actual；`name` 是 frame token 的字符串形式。

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

查询结果适合回答两个问题：系统给应用的预算是否随节奏变化，以及实际帧是否伴随 `jank_type`、`present_type` 恶化。`actual.ts` 是 actual timeline slice 的起点，不是面板物理展示时间；判断最终上屏仍要结合 SurfaceFlinger timeline、flow、present fence 或显示驱动证据。

不能用 `display_frame_token` 是否逐一连续来判断 ARR 正常与否。应用可以按低于 TE 的节奏产帧，Surface 也不必每个 VSync 都提交新 buffer；trace 裁剪还会造 token gap。token 用于关联同一帧，不能单独充当“漏 VSync”计数器。

### 6.4 判断问题属于哪一层

| 现象 | 优先检查 |
|---|---|
| View 已投 `High`，仍长期保持较低 render rate | Window 开关、用户峰值、低电量/温度、其他图层、设备 ARR 能力 |
| render rate 已提高，应用仍短帧/长帧交替 | 应用节拍、提交时间戳、BufferQueue 深度 |
| App on time，SurfaceFlinger/DisplayFrame late | SF work duration、GPU/HWC composition、present fence、显示驱动 |
| 惯性滚动结束后一直不降频 | 每帧速度是否更新、View 是否持续重绘、touch boost 与窗口策略 |
| 静态页面仍驻留高刷 | 活跃动画、不可见但持续 invalidate 的 View、视频/Surface 请求、系统 UI Layer |
| 切换时只有单次长间隔 | 区分 ARR 节拍调整与 MRR mode switch，再检查是否持续复现 |

## 7. 功耗、体验与设备实现边界

高刷新率会增加面板、显示控制器、合成和应用产帧负担，但没有一个适用于所有设备的固定功耗百分比。面板、亮度、分辨率、SoC、内容、OEM 策略和环境温度都会改变结果。评估应同时记录：

- 高刷新率驻留时间与实际 render/present cadence；
- App、GPU、SurfaceFlinger 和显示子系统功耗；
- 触摸到显示延迟、帧时间分布与连续卡顿；
- 测试过程中的亮度、温度和系统模式。

低频面板的 Gamma、亮度补偿或自刷新细节通常由面板、固件与厂商显示 HAL 实现。Android 17 Composer3 的 ARR 标准接口定义了 `vrrConfig`、`minFrameIntervalNs`、`notifyExpectedPresent` 和 `frameIntervalNs`，没有提供通用的“实时 Gamma 补偿”应用 API。缺少设备厂商文档或驱动证据时，不应把低亮闪烁归因于某个 AOSP Gamma 算法。

## 8. Kernel 与驱动证据

内核源码以 `android17-6.18-2026-06_r6` 为锚点。公共同步语义可从以下源码理解：

- `drivers/dma-buf/dma-fence.c`：跨设备异步工作完成关系；
- `drivers/dma-buf/sync_file.c`：把 dma-fence 暴露为 sync_file 文件描述符；
- `drivers/gpu/drm/drm_vblank.c`：采用 DRM/KMS 的设备上，vblank 计数与时间事件的公共实现。

ARR 的面板控制、TE 分频、self-refresh、带宽和时钟策略通常位于厂商显示驱动、固件和 Composer HAL。Android 设备也不保证使用主线 DRM/KMS 路径。排查具体机型时，应在 AOSP 跟踪数据之外补充厂商 HWC 日志、display tracepoint、present fence、时钟/带宽投票与面板事件，不能用通用 kernel tag 推断某款面板的私有策略。

## 9. Android 11—17 版本边界

| 版本 | 相关变化 |
|---|---|
| Android 11 / API 30 | `Surface.setFrameRate(float, int)` 与 Surface 帧率兼容类型公开，多刷新率设备可按图层内容选择模式 |
| Android 12 / API 31 | 三参数 `setFrameRate()` 允许说明是否接受非无缝切换；FrameTimeline 成为现代显示诊断基线 |
| Android 13 / API 33 | `Choreographer.FrameData` / `FrameTimeline` 公开；HWC HAL 转向 AIDL |
| Android 14 / API 34 | `Surface.clearFrameRate()` 公开，便于撤销旧请求 |
| Android 15 / API 35 | ARR 平台能力进入支持设备；View/Window 帧率管理 API 与触摸、滚动策略成为应用入口 |
| Android 16 / API 36 | `Display.hasArrSupport()`、`getSuggestedFrameRate()` 与 render-rate 查询语义公开；增加 `FRAME_RATE_COMPATIBILITY_AT_LEAST` |
| Android 17 / API 37 | 源码锚点更新到 Android 17；DisplayManager、SurfaceFlinger Scheduler 与 Composer3 ARR 主路径延续。新增 `Surface.setProducerThrottlingEnabled()`，用于控制 Producer backpressure，不参与 ARR 投票 |

版本表只说明 API 和平台能力的边界。某台设备是否支持 ARR、支持哪些 render rate、是否允许某类 mode switch，仍要在运行时查询，并以 Trace 为准。

## 10. 常见误判

**把 ARR 写成 60/120Hz mode switching。**

ARR 可以在同一显示配置内按 TE 的离散分频改变刷新间隔；MRR 则在多个固定模式之间切换。

**把 `setFrameRate()` 写成强制刷新率。**

它是图层的内容帧率提示。系统还会合并其他图层和全局约束。

**认为刷新率选择等于 frame pacing。**

刷新率选择决定系统倾向于什么显示节奏；pacing 决定 Producer 在何时提交哪一帧。缺少任一环节，都可能填满队列或形成不均匀 cadence。

**把 `getSuggestedFrameRate()` 当成任意 fps 映射器。**

它只接受 `Normal` 和 `High` 两个类别。

**从 `FrameData` 读取不存在的 `refreshRate`。**

公开 API 提供帧起点与候选时间线。刷新节奏要通过连续样本、Display 和 Trace 判断。

**看到 VSync 间隔改变就判为掉帧。**

先确认当前目标预算是否也改变，再看 actual timeline、jank 类型和最终 present。

**把 `VsyncModulator` 当成刷新率选择器。**

它调整 Early/EarlyGpu/Late 工作预算；内容选择发生在 Scheduler 和 `RefreshRateSelector`。

## 总结

Android 17 的 ARR 分为四层：应用通过 View、Compose 或 Surface 表达内容需求；DisplayModeDirector 汇总系统约束并给出允许范围；SurfaceFlinger Scheduler 根据可见图层的更新节奏选择 render rate/mode；Composer3 把 `frameIntervalNs` 和必要的 `notifyExpectedPresent` 提示交给支持 ARR 的显示硬件。

诊断时先区分 MRR 与 ARR，再分别观察应用产帧、刷新率选择和最终展示。`setFrameRate()` 用于投票，ARR 调整显示节拍，Swappy 或引擎 pacing 控制提交时机。区分这三层后，才能判断问题来自应用、SurfaceFlinger、HWC 还是设备显示驱动。

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
- [Perfetto：FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto Android 17 metric：`frames.sql`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/metrics/sql/android/jank/frames.sql)
- [Android Frame Pacing Library](https://developer.android.com/games/sdk/frame-pacing)
