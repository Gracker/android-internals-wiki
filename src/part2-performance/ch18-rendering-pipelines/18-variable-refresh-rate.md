---
title: "Android 17 可变刷新率（ARR/VRR）渲染管线"
chapter: "18.18"
section: "18.18"
section_title: "Android 17 可变刷新率（ARR/VRR）渲染管线"
status: finalized
applicable_versions: "多刷新率背景：Android 11 (API 30) - Android 14；ARR 主体：Android 15 QPR1 - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "android-17.0.0_r1 (MediaCodec, View, ViewGroup, ViewRootImpl, Display, FrameRateVelocityPoint, Surface, Window, WindowManager, SurfaceControl, BufferQueueConsumer, Scheduler, LayerHistory, RefreshRateSelector, HWComposer) / Android 17 API 37 与 Compose 1.9.0、1.10.0 官方文档 / Perfetto FrameTimeline 与 android.frames.timeline / android17-6.18-2026-06_r6 (drm_vblank.c, drm_vblank.h)"
confidence: high
sources:
  - type: internal-reference
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S12_video_framerate_present_pipeline/source.md"
    role: "视频 release timing、buffer desired-present timestamp、layer vote、Scheduler 与 display present 的关系"
  - type: official
    path: "https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate"
    role: "ARR 设备条件、View 投票生命周期与公开用法"
  - type: official
    path: "https://developer.android.com/reference/android/view/View"
    role: "API 35+ requested frame rate 与 content velocity"
  - type: official
    path: "https://developer.android.com/reference/android/view/ViewGroup"
    role: "API 36+ 子树 requested frame rate 传播"
  - type: official
    path: "https://developer.android.com/reference/android/view/Display"
    role: "API 36 ARR 查询及 API 37 per-display velocity mapping"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameRateVelocityPoint"
    role: "API 37 fps 与 dp/s 阈值数据结构"
  - type: official
    path: "https://developer.android.com/reference/android/view/Surface"
    role: "Surface frame-rate compatibility、切换策略与 API 37 producer throttling"
  - type: official
    path: "https://developer.android.com/reference/android/view/Window"
    role: "API 35 touch boost 与 power-savings policy"
  - type: official
    path: "https://developer.android.com/reference/android/media/MediaCodec"
    role: "带纳秒时间戳释放视频输出 buffer"
  - type: official
    path: "https://developer.android.com/reference/kotlin/androidx/compose/ui/preferredFrameRate.modifier"
    role: "Compose 1.9.0 数值重载与 1.10.0 category 重载"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
    role: "FrameTimeline 目标与真实帧时间模型"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
    role: "android.frames.timeline 表与字段"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java"
    role: "View vote、下一绘制帧有效期与 velocity-to-rate 映射"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewGroup.java"
    role: "requested frame rate 对 View 子树的传播"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java"
    role: "聚合 View vote 并通过 SurfaceControl transaction 下发 layer frame rate"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Display.java"
    role: "ARR 能力、建议 render rate、支持值与 per-display velocity mapping"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameRateVelocityPoint.java"
    role: "API 37 帧率与滚动速度阈值对象"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Surface.java"
    role: "稳定 setFrameRate API、AT_LEAST、flagged FrameRateParams 与 producer throttling"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Window.java"
    role: "Window touch boost 与 power-savings policy"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/WindowManager.java"
    role: "Window 帧率策略字段及 Android 17 默认值"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/SurfaceControl.java"
    role: "ViewRootImpl 到 layer frame-rate transaction 的接口"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/MediaCodec.java"
    role: "releaseOutputBuffer(index, renderTimestampNs) 的 Surface 时间戳语义"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/Surface.cpp"
    role: "native Surface frame-rate vote 与 producer throttling 转发"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp"
    role: "desired-present timestamp、过早 buffer 延后 acquire 与 PRESENT_LATER"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp"
    role: "content requirements、pacesetter/follower Display 与全局信号"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/LayerHistory.cpp"
    role: "Surface compatibility 到 VRR/MRR layer vote 的映射"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp"
    role: "候选 render rate 与 physical mode 的 layer 评分和排序"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp"
    role: "HWC validate/present 与 Display present fence"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c"
    role: "通用 DRM CRTC vblank 计数、时间戳与中断生命周期"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/drm/drm_vblank.h"
    role: "通用 DRM vblank 状态、计数与时间接口"
tags: ["VRR", "ARR", "Variable-Refresh-Rate", "LTPO", "setFrameRate", "FrameTimeline", "渲染管线"]
related_chapters: ["2.3", "2.18", "2.19"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: "2026-07-26T10:37:31+08:00"
last_idle_audit_run_id: "20260726-103558-idle-audit-c11ac4a7"
---

# 18.18 Android 17 可变刷新率（ARR/VRR）渲染管线

## 为什么这一节容易误判

固定刷新率设备的帧预算容易计算：60 Hz 对应约 16.67 ms，120 Hz 对应约 8.33 ms。支持多刷新率或 ARR 后，`VSYNC-app` 和 `VSYNC-sf` 的间隔会随当前 render rate、physical mode（面板正在使用的物理显示模式）与设备实现变化。滚动可能使用较短周期，静态页面和低帧率内容可能使用较长周期，因此分析工具不能始终套用 16.67 ms 阈值。

刷新周期变长也无法补救已经错过 deadline 的帧。刷新率选择要经过 App vote、内容节奏判断、Scheduler 决策和设备能力约束。某一帧错过自己的 `expected_frame_timeline_slice`（FrameTimeline 为该帧给出的目标时间窗）后，Perfetto 仍会记录 app jank 或 sf jank。ARR 可以调整目标节拍，但每一帧仍有对应 deadline。

分析时还要分开三种频率：

- **内容帧率**：视频、游戏或动画每秒产生多少个不同内容帧，例如 24 fps。
- **应用 render rate**：Choreographer/producer 被允许或选择以多快的节奏生成帧。
- **Display refresh rate**：面板每秒刷新多少次，例如 120 Hz。

24 fps 内容可以在 120 Hz Display 上按 5:5 cadence 显示，即每个内容帧连续显示 5 个刷新周期；60 fps render rate 也可以运行在 120 Hz 面板上。`setFrameRate(24)` 只表达内容或渲染偏好，不保证面板切到 24 Hz，也不会限制 producer 的供帧速度。

## VRR、多刷新率和 ARR 的边界

| 名称 | 关注点 | 分析含义 |
| --- | --- | --- |
| 多刷新率（MRR） | 设备在 60 Hz、90 Hz、120 Hz 等固定 Display mode 之间选择 | Android 11–14 的公开帧率 API 主要在这个背景下使用 |
| VRR（Variable Refresh Rate） | 面板/Composer 能在能力范围内动态改变 VSync 周期，不必把每个 render rate 都表示成独立固定 mode | 属于显示硬件与 HAL 能力，不能只由“面板是 LTPO”推出 |
| ARR（Adaptive Refresh Rate） | Android 根据 View/Surface vote、内容 cadence、touch/transition 等策略选择 render/refresh rate | 支持设备从 Android 15 QPR1+ 提供，Android 16 增加公开能力查询 |

LTPO（Low-Temperature Polycrystalline Oxide）描述面板背板技术，ARR 描述 Android 的调度能力，两者不能互相替代。官方 ARR 文档要求设备运行 Android 15 QPR1 或更高版本，并具备相应 Composer HAL 能力。应用到 API 36 才能通过 `Display.hasArrSupport()` 查询公开能力。返回 `false` 时，设备仍可能支持多个固定 Display mode，此时应按 MRR 的离散 mode switching 分析，不能套用 ARR 动态周期模型。

## 系统如何决定刷新节奏

刷新率选择可以分成三层：

- **App 投票层**：Android 11+ 的 `Surface.setFrameRate()`、Android 15（API 35）的 `View.setRequestedFrameRate()`，以及滚动时的 `setFrameContentVelocity()` 表达内容更新需求。Compose 的 `preferredFrameRate()` 会把 composable 偏好传给平台。
- **系统策略层**：SurfaceFlinger 汇总可见 layer 的 vote 与历史 cadence，再结合 focus、touch boost、window transition、idle、policy range 等信号，为候选 render rate 和 physical rate 评分。
- **设备能力层**：Display mode、seamless switch group（可无明显黑屏完成切换的一组模式）、面板和 device-specific HAL support 约束最终能否使用 ARR；不满足 ARR 条件时仍可能进行离散 mode switching。

下面的链路区分 App 表达偏好、系统选择节奏和应用实际供帧三个阶段：

```text
App vote / content cadence
        ↓
SurfaceFlinger + Scheduler choose refresh rate
        ↓
VSYNC-app / VSYNC-sf interval changes
        ↓
App draw → queueBuffer → SurfaceFlinger compose → present
```

vote 只是候选选择的一项输入。其他可见 App/SystemUI layer、触控状态和电源策略都可能改变结果。即使观察到刷新周期变化，也不能反向证明某一个 View vote 被原样采纳。

## App 端 API

### Android 11+：`Surface.setFrameRate()` 表达 Surface 内容节奏

Android 11 将 `Surface.setFrameRate()` 加入公开 API。视频、游戏和独立 `SurfaceView` producer 可以用它声明当前 Surface 的内容或渲染节奏。下面三个调用分别展示固定源、一般偏好和清除偏好：

```java
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
surface.setFrameRate(0f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
```

这三个调用依次表示固定 24 fps 内容、可随显示节奏运行的 60 fps 偏好，以及清除偏好。`FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 适合视频等固定 cadence 内容，系统可以选择其整数倍刷新率。`DEFAULT` 在 Android 17 更适合游戏。API 36 新增的 `FRAME_RATE_COMPATIBILITY_AT_LEAST` 适合 UI、滚动和动画，表示候选 render rate 不低于给定值。

`setFrameRate()` 不会替应用完成 pacing（控制实际提交节奏）。请求 60 fps 后仍以 120 fps 连续 `queueBuffer()`，依旧可能填满队列并增加功耗。API 31+ 的三参数重载还允许选择 `CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS` 或 `CHANGE_FRAME_RATE_ALWAYS`。后者允许非无缝 mode switch，可能出现黑屏或闪烁，只适合长时间视频等切换收益足以覆盖视觉代价的场景。清除 vote 时可传 0；API 34+ 也可调用语义更清楚的 `clearFrameRate()`。

Android 17 的 `Surface.FrameRateParams` 出现在 `android-17.0.0_r1` 源码中，但带有 `@FlaggedApi`，表示公开可用性还受 feature flag 控制。同一实现还保留“min/max plumbing 尚未完成”的 TODO：当前逻辑优先取 `fixedSourceRate`，否则只取 `desiredMinRate`。跨设备代码应继续使用官方 API reference 稳定列出的 `setFrameRate(float, int[, int])`，不能根据源码中出现类名就推断所有 API 37 设备都完整支持区间投票。

### Android 17：producer throttling 和刷新率投票分属两套控制

API 37 的 `Surface.setProducerThrottlingEnabled(boolean)` 控制 EGL/Vulkan producer 在 `queueBuffer()` 附近的 CPU back-pressure（让生产线程等待下游容量）。默认开启时，`eglSwapBuffers()` 或 `vkQueuePresentKHR()` 可能等待 consumer 处理前一帧；关闭后，队列填满时仍会在后续 dequeue 或 `vkAcquireNextImageKHR()` 处自然阻塞。异步模式下关闭请求无效，throttling 仍保持开启。

这个 API 不提交 Hz，也不改变 `LayerHistory` 的 frame-rate vote。关闭 queue-time back-pressure 前，Vulkan producer 还要具备明确的 CPU/GPU 同步和在途帧控制，不能把它当成通用低延迟开关。排查线程为何卡在 swap/present 时，应查看 producer throttling、queue 深度和 fence；排查系统为何选择 60/90/120 Hz 时，则查看 `setFrameRate()`、View vote 与 Scheduler。两套信号混在一起，会把队列背压误判成刷新率选择。

### Android 15：View / Compose 开始直接表达刷新率偏好

`View.setRequestedFrameRate(float)` 在 API 35 加入，既可以传入具体 fps，也可以传入类别常量。普通 UI 组件可以在 View 层表达偏好，滚动场景还可通过 `setFrameContentVelocity(float)` 上报内容移动速度。下面的调用展示类别 vote 与速度 vote：

```java
view.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_NORMAL);
animationView.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
slowVisualizer.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_LOW);
list.setFrameContentVelocity(2400f);
```

View vote 有三个容易漏掉的约束：

- View 只有在 redraw 时才参与投票；静止且不再 invalidated 的 View 不会永久占用高刷。
- API 35 在 `ViewGroup` 上调用不会自动传给 child View；API 36+ 若需要对子树生效，可调用 `ViewGroup.propagateRequestedFrameRate(frameRate, forceOverride)`。`forceOverride=false` 会保留 child 自己的请求，`true` 才覆盖整棵子树。
- `setFrameContentVelocity()` 的单位是 pixels/second，值只对下一次 drawn frame 有效；自定义 fling 组件需要在每个绘制帧更新，手势开始时的一次调用无法覆盖后续帧。

Compose 的版本边界需要单独记录：`Modifier.preferredFrameRate(frameRate: Float)` 加入 Compose UI 1.9.0，`Modifier.preferredFrameRate(frameRateCategory: FrameRateCategory)` 加入 1.10.0。多个 composable 的数值偏好会汇总为可行值，偏好也只在 composable 被绘制时有效；最终仍要经过 View 和 SurfaceFlinger 策略。

`Display.hasArrSupport()` 不属于 API 35。面向 Android 15 的代码要把刷新率投票与设备能力查询分开：投票使用 `View` / Compose，公开能力查询只能在 API 36+ 调用。

### Android 16：`Display` 查询 API 用来读能力和建议值

Android 16（API 36）补充了公开查询入口。`Display.hasArrSupport()` 判断当前 Display 是否公开支持 ARR，`Display.getSuggestedFrameRate(int)` 读取系统为 NORMAL/HIGH 类别配置的建议值。`getSupportedRefreshRates()` 在 Android 16+ 返回 Display 支持的 render rates；若要调查旧平台，或核对分辨率与刷新率组合，还要查看 `getSupportedModes()`。

```java
Display display = context.getDisplay();
if (display != null && display.hasArrSupport()) {
    float normal = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_NORMAL);
    float high = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_HIGH);
    float[] supported = display.getSupportedRefreshRates();
}
```

`getSuggestedFrameRate(int)` 的入参是类别，不接受任意 fps。它适合回答系统建议普通动画采用什么节奏，或 HIGH 类别对应哪个建议值；45 fps、72 fps 等业务目标不能直接传入该接口做映射。

Android 15 QPR1 设备可能已经具备 ARR 调度逻辑，却没有 API 36 的公开查询。应用在 API 35 上可以安全提交 View/Surface hint，由系统按能力处理；无需读取私有属性或维护机型白名单。诊断时再结合设备文档、实际 VSync 周期和 SurfaceFlinger refresh-rate selection 证据确认是否启用。

### Android 17：滚动速度映射属于当前 Display

API 37 的 `Display.getFrameRateVelocityMapping()` 返回只读的 `FrameRateVelocityPoint` 列表。每个点由 fps 与 dp/s（每秒移动的 density-independent pixels）阈值组成，供 RecyclerView、ScrollView 一类 fling 场景把内容速度映射到帧率。`View` 源码先把 pixels/second 按 density 换算成 dp/s，再按当前 Display 的列表查找匹配帧率。

这份映射按 Display 提供，不是全设备常量。窗口从折叠屏外屏移到内屏，或移到外接显示器后，要从新窗口关联的 `Display` 重新查询；收到 `DisplayListener.onDisplayChanged()` 时也要更新缓存。业务层若自行实现 velocity-to-rate 逻辑，应读取该映射并保留平台回退路径，不能把 120 fps / 300 dp/s 之类的文档示例写成固定阈值。

### Android 15+：Window 级策略开关

API 35 还提供 Window 级的 `setFrameRateBoostOnTouchEnabled()` 和 `setFrameRatePowerSavingsBalanced()`。`android-17.0.0_r1` 的 `WindowManager.LayoutParams` 将两项都初始化为 `true`：touch boost 在触摸期间提高节奏，power-savings balance 允许 toolkit 按需调整刷新率。普通交互窗口应保留默认值；只有 trace 表明策略本身造成体验问题时，才适合缩小范围测试关闭某一项的影响。

这些开关属于 Window policy，不会给某一帧指定 Hz。局部动画优先使用 View/Compose vote，视频或游戏 Surface 则使用 `Surface.setFrameRate()`。

### 静态页面与视频不要用同一套 vote

静态页面没有新 invalidation/buffer 时，Scheduler 可以根据 idle 与 layer history 降低驻留刷新率；没有必要让每个静态 View 长期投 LOW。进入滚动或动画后，View toolkit 的 touch/motion policy 与新的 redraw vote 会再次提高节奏。

视频更适合在承载视频的 Surface 上提交 `FIXED_SOURCE` vote，例如 24/30 fps，让系统选择匹配 cadence 的 rate 或整数倍。若视频上方还有持续以 60/120 fps 更新的控件、字幕或 SystemUI layer，整屏选择要综合这些可见 layer，不能只根据视频 fps 预测。

视频链路里还有一个容易与 vote 混淆的时间信号。两者的职责如下：

- `Surface.setFrameRate(24, FIXED_SOURCE)` 给 layer 提交内容 cadence 偏好，供 Scheduler 选择 render rate 与 Display mode；
- `MediaCodec.releaseOutputBuffer(index, renderTimestampNs)` 给当前输出 buffer 设置期望呈现时间；
- `BufferQueueConsumer::acquireBuffer(expectedPresent)` 比较 buffer 的 desired-present timestamp 与 consumer 的目标呈现时刻；buffer 还太早时返回 `PRESENT_LATER`，本轮不 acquire；
- HWC present 产生的 present fence 表示 Display 侧完成时点，可用于后续调度和 trace 归因。

因此，正确的 24 fps vote 无法修正错误的 `renderTimestampNs`。时间戳过早、过晚或单位错误，会造成延后 acquire、丢帧或 cadence 抖动。buffer timestamp 正确也不能保证整屏采用 24/48/120 Hz，因为其他可见 layer 与 policy 仍参与选择。分析时应沿 `player release timing → BufferQueue desired present → Scheduler/HWC timing → display feedback` 逐段对齐证据。

## Android 17 的 Scheduler 怎样处理 vote

View 路径会先在窗口内聚合。每个 View 在绘制过程中调用内部 `votePreferredFrameRate()`：正数 requested rate 使用 `FIXED_SOURCE`，由 velocity 换算出的 rate 使用 `AT_LEAST`。`ViewRootImpl` 汇总本帧 vote，再通过 `SurfaceControl.Transaction.setFrameRate()` 把结果提交给窗口 layer。`setFrameContentVelocity()` 只对下一张 drawn frame 有效，因此 fling 组件必须逐帧更新速度。

多个数值 vote 之间存在整倍数关系时，`ViewRootImpl` 选择其中较高、且能覆盖其他 vote 的值。两组 vote 互相不能整除时，源码会设置 conflict 标记，停止直接提交该数值，并根据最大值是否高于 60 fps 回退到 HIGH 或 NORMAL category。因此，trace 中出现 category vote 不一定来自应用直接调用 category API，也可能是数值冲突后的回退结果。

SurfaceFlinger 收到 layer 属性后，Android 17 的 `Scheduler::chooseRefreshRateForContent()` 让 `LayerHistory` 汇总可见 layer 的近期需求，再把 content requirements 交给 policy/selector。`RefreshRateSelector` 会对候选 render rate 与 physical mode 评分并排序，考虑因素包括：

- layer 的可见权重、focus 和期望 frame rate；
- `ExplicitExact`、`ExplicitExactOrMultiple`、`ExplicitGte`、`ExplicitDefault`、`ExplicitCategory`、`Heuristic` 等 vote 语义；这些名称分别表达精确值、精确值或倍数、不低于目标、默认偏好、类别偏好和历史推断；
- 候选刷新率是否能整除/覆盖内容 cadence；
- switch 是否 seamless、候选是否在 primary physical/render range；
- touch、idle、power mode 等全局信号。

这里不存在一张脱离场景的固定 vote 优先级表。例如，`ExplicitExact` 在支持 per-app frame-rate override 时可以接受目标 rate 的整数倍；`ExplicitGte` 会给不低于目标的候选满分；`NoVote`、`NoPreference` 和 `Min` 在 layer 评分循环中跳过。最终结果还要叠加其他可见 layer 的权重与系统 policy。

`AT_LEAST` 在两类设备上的转换需要单独检查。`LayerHistory.cpp` 在 VRR Display 上将它转换为 `ExplicitGte`；在只能切换固定 mode 的 MRR Display 上则转换为 `Max`。源码注释解释，离散 mode switch 可能带来 jank，因此动画与滚动会偏向较高刷新率以保持流畅。相同 API 调用在两台设备上得到不同选择结果，可能来自这一能力分支。

多个 Display 也不是彼此完全独立的 Scheduler。`Scheduler::chooseDisplayModes()` 先为 pacesetter Display（主导节奏的显示设备）排序，再把 pacesetter fps 传给已上电的 follower Display。每个 Display 使用自己的 `RefreshRateSelector`，idle/power 信号可以按 Display 读取，但 content requirements 与 pacesetter 关系仍会形成约束。窗口跨屏后，要同时核对目标 Display、pacesetter/follower 关系和该 Display 的 mode 集合。

`chooseRefreshRateForContent()` 完成 policy 更新后，还可以把已选 pacesetter fps 传给 `updateAttachedChoreographers()`。该函数遍历 layer hierarchy，为 `FIXED_SOURCE` / `DEFAULT` 等 vote 计算合适的 divisor（显示节奏与应用回调节奏的整数分频），再更新相应 `EventThreadConnection.frameRate`。这条路径会把 Display 选择反馈到 attached Choreographer 的回调节奏，是 `VSYNC-app` 间隔随选择结果变化的源码依据之一。

源码入口是 [Android 17 `Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)、[`LayerHistory.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/LayerHistory.cpp) 与 [`RefreshRateSelector.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp) 的 `chooseRefreshRateForContent()`、`chooseDisplayModes()`、`calculateLayerScoreLocked()` 和 `getRankedFrameRates()`。

`Scheduler.cpp` 中的 `FPS_THRESHOLD_FOR_KERNEL_TIMER = 65_Hz` 用于 hardware VSync idle 控制：timer reset 且当前 peak rate 高于 65 Hz 时允许重新同步 hardware VSync；timer expired 且 rate 不高于 65 Hz 时可关闭空闲 hardware VSync。该阈值不控制应用帧率，也不能用于解释某个 layer 的 frame-rate vote。

### Kernel 锚点只能说明通用 vblank 记账

kernel 基线是 `android17-6.18-2026-06_r6`。这里的 DRM 指 Direct Rendering Manager 内核图形子系统，CRTC 是驱动中代表显示扫描控制器的对象。通用 `drm_vblank.c` 维护 CRTC vblank（相邻扫描周期之间的垂直消隐边界）计数与时间戳，驱动在 vblank 中断中调用 `drm_crtc_handle_vblank()`；`drm_vblank.h` 暴露 count/time、vblank on/off 与 wait 接口。这些代码只能说明内核/驱动需要提供显示时序事件。

这些通用代码不能证明某台 Android 设备的面板 VRR 范围、DPU 编程方式或 Composer HAL 决策。手机 SoC 的 Display driver 和面板控制通常位于厂商代码中，AOSP common kernel 只提供通用参考。遇到面板没有切到某一 Hz 的问题时，还要补充目标设备的 Composer capability、HWC trace、vendor Display driver 与面板 mode，不能从 `drm_vblank.c` 反推产品实现。

## 渲染过程里的 deadline 没有消失

在支持 ARR 的设备上，`VSYNC-app` 和 `VSYNC-sf` 的节拍会随当前内容变化。滚动时周期可能缩短，静态页面可能拉长，SurfaceFlinger 侧也会出现 refresh-rate selection 相关的决策 slice。这些变化会直接改变当前帧预算。

预算会变化，deadline 仍然存在。`expected_frame_timeline_slice` 给出的窗口一旦确定，App 线程、RenderThread 或 SurfaceFlinger 任一阶段超时，`actual_frame_timeline_slice` 仍会通过 `on_time_finish`、`present_type`、`jank_type` 等字段记录结果。分析慢帧时，应分别回答当前目标周期是多少，以及这一帧有没有按时完成。

## 在 Perfetto 中分析 VRR / ARR

可以按以下顺序观察，并与 §2.3、§2.18 的方法保持一致：

- `VSYNC-app`：App 侧收到的节拍是否从 8.33 ms 变为 16.67 ms、33.3 ms 或其他档位；
- `VSYNC-sf`：SurfaceFlinger 的合成节拍是否同步变化；
- `expected_frame_timeline_slice`：当前帧的目标窗口；
- `actual_frame_timeline_slice`：真实完成情况，以及 `on_time_finish`、`present_type`、`jank_type`；
- refresh-rate selection slice：刷新率选择是否频繁来回切换。

不同 build 的 Scheduler slice/counter 名称可能变化。应先用 SurfaceFlinger/Scheduler 轨道确认 active physical mode 与 render rate，再按时间关联 `chooseRefreshRateForContent`、ranking/selection、VSync 周期和 FrameTimeline token。仅凭模糊匹配到的一条 “RefreshRate” slice，无法得出可靠结论。

### Android 12+：以 FrameTimeline 为入口

FrameTimeline 是 Android 12+ 更稳定的入口。下面的查询按 `upid + surface_frame_token + layer_name` 对齐 expected/actual，用于查看同一 SurfaceFrame 的预算与实际结果。正确模块名是 `android.frames.timeline`，`jank_type` 来自 actual 表；不要使用错误的 `android_frames.jank_type` 列名或不存在的 `android.frames` 模块。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

WITH target_process AS (
  SELECT upid
  FROM process
  WHERE name = 'com.example.app'
  LIMIT 1
),
expected AS (
  SELECT *
  FROM expected_frame_timeline_slice
  WHERE upid = (SELECT upid FROM target_process)
    AND surface_frame_token IS NOT NULL
),
actual AS (
  SELECT *
  FROM actual_frame_timeline_slice
  WHERE upid = (SELECT upid FROM target_process)
    AND surface_frame_token IS NOT NULL
)
SELECT
  CAST(e.ts / 1e6 AS INTEGER) AS expected_ts_ms,
  e.layer_name,
  e.surface_frame_token,
  e.display_frame_token,
  CAST(e.dur / 1e6 AS FLOAT) AS budget_ms,
  CAST(a.dur / 1e6 AS FLOAT) AS actual_ms,
  a.on_time_finish,
  a.present_type,
  a.jank_type
FROM expected e
LEFT JOIN actual a
  ON a.upid = e.upid
 AND a.surface_frame_token = e.surface_frame_token
 AND a.layer_name = e.layer_name
ORDER BY e.ts DESC
LIMIT 30;
```

查询结果中的 `budget_ms` 随当前调度目标变化属于正常现象。即使 `actual_ms > budget_ms`，也要结合 `on_time_finish`、`present_type` 和 `jank_type` 判断 FrameTimeline 结果。刷新率切换附近若出现异常，应把 selection slice、VSync 周期和对应 SurfaceFrame/DisplayFrame 放在同一时间窗；一个长 duration 不能单独证明存在切换抖动。

### Android 10/11：回到 `doFrame` 和 VSync 时间窗

Android 10/11 没有 FrameTimeline 主表时，需要在同一时间窗内对齐 `Choreographer#doFrame`、`VSYNC-app`、`VSYNC-sf` 和 SurfaceFlinger。固定 16.67 ms 阈值在低帧率目标下会误报；诊断时先确认当前节拍，再判断 `doFrame` 是否真的超出该档预算。

```sql
SELECT
  CAST(ts / 1e6 AS INTEGER) AS ts_ms,
  CAST(dur / 1e6 AS FLOAT) AS doframe_ms
FROM slice
WHERE name GLOB 'Choreographer#doFrame*'
ORDER BY dur DESC
LIMIT 20;
```

这一步只负责找出候选慢帧窗口。后续还要回到 Perfetto UI，将 `VSYNC-app`、`VSYNC-sf` 和 SurfaceFlinger 合成片段放在同一时间窗内比较，确认问题位于 App、合成或刷新率选择阶段。

## 版本演进

| 版本 | 公开能力 | 分析重点 |
| --- | --- | --- |
| Android 11 | `Surface.setFrameRate()` + 多刷新率 mode switching | 区分固定 mode 切换和普通慢帧 |
| Android 12-14 | Android 12 开始有 FrameTimeline，可把目标窗口和真实完成时间拆开看 | 这一阶段仍以多刷新率背景为主 |
| Android 15 / 15-QPR1+ | `View.setRequestedFrameRate()`、`setFrameContentVelocity()`、Window touch/power policy；支持设备启用 ARR | 把 View vote、touch/scroll policy 与 Scheduler 决策放到同一时间窗 |
| Android 16 | `Display.hasArrSupport()`、`Display.getSuggestedFrameRate(int)`、`FRAME_RATE_COMPATIBILITY_AT_LEAST`、`ViewGroup.propagateRequestedFrameRate()` | 查询 ARR 与建议值；区分 VRR 的 `ExplicitGte` 和 MRR 的 `Max` |
| Android 17 | `Display.getFrameRateVelocityMapping()` / `FrameRateVelocityPoint`；`Surface.setProducerThrottlingEnabled()` | per-display 滚动映射；把 producer back-pressure 与 Hz 投票分开；以 `android-17.0.0_r1` 的 pacesetter/follower 排序为源码基线 |

Android 11–14 负责交代多刷新率背景，Android 15-QPR1+ 进入 ARR 主体，Android 16 补齐公开能力查询，Android 17 仍沿用同一职责划分。

Compose 1.9.0 的数值 `preferredFrameRate()` 与 1.10.0 的 category 重载属于 Jetpack 版本演进，不和某个 Android 平台版本一一绑定；能否产生 ARR 效果仍取决于运行设备的系统与 Display 能力。

## 与其他章节的关系

- **2.3 VSync 机制**：解释 `VSYNC-app`、`VSYNC-sf` 和 phase offset
- **2.18 Adaptive Refresh Rate**：展开 ARR 的机制、API 和 Scheduler 选择逻辑
- **2.19 刷新率切换与帧率适配**：继续看 mode switching 和切换开销

## 参考资料

- [Android Developers：Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android API：View](https://developer.android.com/reference/android/view/View)
- [Android API：ViewGroup](https://developer.android.com/reference/android/view/ViewGroup)
- [Android API：Display](https://developer.android.com/reference/android/view/Display)
- [Android API：FrameRateVelocityPoint](https://developer.android.com/reference/android/view/FrameRateVelocityPoint)
- [Android API：Surface](https://developer.android.com/reference/android/view/Surface)
- [Android API：Window](https://developer.android.com/reference/android/view/Window)
- [Android API：MediaCodec](https://developer.android.com/reference/android/media/MediaCodec)
- [Compose UI：preferredFrameRate](https://developer.android.com/reference/kotlin/androidx/compose/ui/preferredFrameRate.modifier)
- [Perfetto：FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [PerfettoSQL：android.frames.timeline](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Android 17 AOSP：View.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [Android 17 AOSP：ViewRootImpl.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Android 17 AOSP：Display.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Display.java)
- [Android 17 AOSP：Surface.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Surface.java)
- [Android 17 AOSP：WindowManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/WindowManager.java)
- [Android 17 AOSP：MediaCodec.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/MediaCodec.java)
- [Android 17 AOSP：BufferQueueConsumer.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)
- [Android 17 AOSP：Scheduler.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)
- [Android 17 AOSP：LayerHistory.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/LayerHistory.cpp)
- [Android 17 AOSP：RefreshRateSelector.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp)
- [Android 17 AOSP：HWComposer.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)
- [Android 17 common kernel：drm_vblank.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/gpu/drm/drm_vblank.c)
