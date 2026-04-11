---
title: "刷新率切换与帧率适配性能"
chapter: "2.19"
section: "2.19"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-04-07"
last_verified_against: "AOSP android-16.0.0_r1, 官方文档最新版本"
confidence: medium
sources:
  - type: expert-insight
    path: "intake/research-feeds/2026-04-06-gracker-jank-insights.md"
  - type: official
    path: "https://developer.android.com/reference/android/view/Surface#setFrameRate"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/refresh-rate"
  - type: research
    path: "intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp"
  - type: aosp
    path: "services/surfaceflinger/Scheduler/VsyncModulator.cpp"
tags: [refresh-rate, frame-rate, SurfaceFlinger, VSync, setFrameRate, jank, rendering, display-mode, ARR]
related_chapters: ["2.2", "2.3", "2.4", "2.6", "2.18"]
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 2.19 刷新率切换与帧率适配性能

## 为什么要了解刷新率切换

在 Android 手机上，有一个几乎所有厂商都无法彻底消除的卡顿场景：从相机界面划到多任务，再返回桌面的动画。无论旗舰还是中端，无论高通、联发科还是三星芯片，这个场景几乎必卡。原因不是 App 渲染慢了，也不是 GC 暂停了——而是系统在切换屏幕刷新率。

相机界面通常以 60Hz 运行（Camera 的传感器采集帧率有限，高刷新率纯属浪费功耗），而桌面动画需要 120Hz 才能流畅。当用户从相机上划触发多任务动画时，系统需要把刷新率从 60Hz 切到 120Hz。这个切换不是软件层面改个数字那么简单——它涉及 PLL 时钟重配置、Display HAL 状态机切换、VSync 信号源周期调整。整个过程中，若干帧可能被延迟或丢弃，用户就看到了一瞬间的卡顿。

这种卡顿有一个让人头疼的特征：在 App 侧的 Perfetto Trace 中看起来完全正常。Choreographer#doFrame 的耗时没有异常，主线程没有阻塞，RenderThread 也没有超时——但用户就是感受到了不流畅。如果我们不知道刷新率切换会导致这种卡顿，就会在错误的 Track 上浪费大量分析时间。

读完这一节，我们会知道：刷新率切换在系统层面到底发生了什么、SurfaceFlinger 如何仲裁多个 Surface 的帧率需求、在 Perfetto 中如何识别刷新率切换导致的卡顿、以及 App 开发者和系统工程师分别能做什么来减少这类卡顿。

## 帧率切换导致卡顿的机制

### 一个典型的切换场景

相机界面 → 多任务动画 → 桌面，这个过程中发生了什么？

1. **相机界面阶段**：Camera App 通过 `Surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE)` 告诉系统"我的帧率是固定的 60fps"。SurfaceFlinger 据此将屏幕刷新率设为 60Hz（或其整数倍中最低满足帧率需求的值）。

2. **用户上划触发多任务**：WindowManager 开始执行多任务动画，Launcher 的 Surface 变为活跃状态。Launcher 并没有设置特定的帧率偏好，但动画场景的 `Content Detection` 会检测到帧率需求上升——或者更直接地，触摸事件触发了 SurfaceFlinger 的 touch boost 机制，将刷新率临时提升到最高值（通常是 120Hz）。

3. **SurfaceFlinger 决策切换**：SurfaceFlinger 收集所有活跃 Layer 的帧率需求，通过 `RefreshRateSelector` 判断当前 60Hz 无法满足新出现的 120Hz 需求，决定切换到 120Hz。

4. **Display HAL 执行硬件切换**：SurfaceFlinger 通过 Composer HAL 向 Display HAL 发送模式切换指令。Display HAL 需要重新配置 PLL（Phase-Locked Loop）时钟，调整显示时序参数。这个过程在不同 SoC 平台上耗时不同：通常在 1-3 帧之间（16ms-50ms @ 60Hz），期间显示管道处于"过渡态"。

5. **过渡期的帧处理**：在硬件过渡完成之前，VSync 信号可能不稳定或暂时中断。SurfaceFlinger 在这段时间内无法正常合成和提交帧——它可能重复显示上一帧，或者完全跳过合成。

[已验证: 官方文档, developer.android.com/develop/ui/views/graphics/refresh-rate]
[来源: intake/research-feeds/2026-04-06-gracker-jank-insights.md — 高爷专家洞察]

这就是为什么用户感知到了卡顿，但 App 侧 Trace 看起来一切正常。App 的渲染工作可能在刷新率切换之前就已经完成了——问题发生在 SurfaceFlinger / Display HAL 层面，App 完全没有感知。

### 不同切换类型的差异

刷新率切换的性能影响取决于切换的"代价"，而代价取决于切换类型：

**无缝切换（Seamless Switch）**：在同一个 Config Group 内的 Display Mode 之间切换（比如 1080p/60Hz ↔ 1080p/120Hz），由 Composer HAL 2.4+ 提供支持。切换延迟较低，通常在 1-2 帧以内。这是 Android 11+ 在支持多刷新率设备上的标准行为。

**非无缝切换（Non-seamless Switch）**：涉及分辨率变化或跨 Config Group 的切换（比如 1440p/120Hz → 1080p/60Hz）。这种切换可能导致短暂的黑屏或画面冻结，延迟可达数帧。在日常使用中较少出现。

**ARR 离散步进**（Android 15+）：在 LTPO 面板上，ARR 通过离散 VSync 步进调整刷新率，不需要完整的 Display Mode 切换。理论上过渡几乎无感知延迟，因为 PLL 仍然在同一个频率范围内微调，而不是跳变。这是目前最优的切换方式，但仅限支持 ARR 的 LTPO 设备。

[已验证: 官方文档, developer.android.com/reference/android/hardware/display/DisplayManager]

## SurfaceFlinger 的刷新率选择策略

SurfaceFlinger 不是简单地"听到什么帧率就切什么刷新率"。它是多个 Layer 帧率需求的仲裁者，决策逻辑相当复杂。

### Layer 的帧率表达方式

每个 Layer（一个 Surface 对应一个 Layer）可以通过以下方式向 SurfaceFlinger 表达帧率偏好：

**显式声明（`Surface.setFrameRate()`）**：Android 11 引入，推荐使用。App 在 Surface 上调用此 API 告诉系统预期的渲染帧率。有两个关键参数：帧率值和兼容性类型。

```java
// Android 11+ (API 30)
// frameworks/base/core/java/android/view/Surface.java
// 告诉系统这个 Surface 以 60fps 渲染
surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);

// 视频播放——帧率不可变，系统应选择精确匹配的刷新率
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
```

`FRAME_RATE_COMPATIBILITY_DEFAULT` 表示"我希望这个帧率，但如果系统觉得其他帧率更好也行"。`FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 表示"我的帧率是固定的（比如视频源），请尽量精确匹配"。两者的区别在于：系统在仲裁时，DEFAULT 类型的请求可以被"向上取整"到更高的刷新率（比如 60fps → 120Hz），而 FIXED_SOURCE 会倾向于选择帧率的精确整数倍。

[已验证: 官方文档, developer.android.com/reference/android/view/Surface#setFrameRate]

**内容检测（Content Detection）**：即使 App 没有调用 `setFrameRate()`，SurfaceFlinger 也能通过追踪 Layer 上 buffer 的提交时间戳自动推断帧率。如果一个 Layer 平均每 16.67ms 提交一个 buffer，系统推断它的帧率大约是 60fps。这个机制由系统属性 `ro.surface_flinger.use_content_detection_for_refresh_rate` 控制。

**Display Mode 指定（`preferredDisplayModeId`）**：Android 11 之前的方式，直接指定 Display Mode 的 ID。这种方式粒度太粗（绑定完整的分辨率+刷新率），Android 11 之后应优先使用 `setFrameRate()`。

### 多 Layer 仲裁：SurfaceFlinger 怎么选

当屏幕上有多个活跃 Layer 时（比如前台 App + 浮窗 + StatusBar），SurfaceFlinger 需要找到一个能满足所有 Layer 需求的刷新率。这个仲裁逻辑在 `RefreshRateSelector.cpp` 中实现。

基本策略是选择所有活跃 Layer 请求帧率的**最小公倍数**或其附近的值。假设 Layer A 请求 24fps（视频播放），Layer B 请求 60fps（前台 App），SurfaceFlinger 会倾向于选择 120Hz——因为 120 是 24 和 60 的最小公倍数，两个 Layer 的帧都能被按时呈现。

但仲裁不只是数学题。`RefreshRateSelector` 使用了一种投票（voting）机制，每个活跃 Layer 根据自己的帧率偏好投出一票：

- **LayerVoteType::Max**：要求最高刷新率（通常是触摸交互、动画场景）
- **LayerVoteType::Min**：要求最低刷新率（静态内容，省电优先）
- **LayerVoteType::Heuristic**：启发式投票，基于内容检测自动判断
- **LayerVoteType::ExplicitDefault / ExplicitExact**：基于 `setFrameRate()` 的显式请求

SurfaceFlinger 收集所有 Layer 的投票后，通过 `getBestRefreshRate()` 计算最终决策。如果有任何一个 Layer 投了 Max 票，最终刷新率会倾向于最高值（触摸 boost 场景）。如果所有 Layer 都是 Min 或 Heuristic 且帧率需求很低，系统会降到较低的刷新率以节省功耗。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp]

### 系统级干预：谁有权覆盖 App 的请求

`setFrameRate()` 是一个"建议"而非"命令"。以下因素可以覆盖 App 的帧率请求：

**GameManagerService**：游戏模式下可以通过 `setDesiredDisplayModeSpecs()` 直接介入帧率决策。性能模式可能解除帧率限制到最高值，省电模式可能限制到 60fps 或更低。

**Battery Saver**：省电模式下 DisplayManager 会收窄刷新率范围的上限（比如从 120Hz 限制到 60Hz），SurfaceFlinger 的选择空间被压缩。

**温控**：设备温度过高时，系统可能强制降低最高刷新率。这是一种保底机制，优先级高于一切 App 请求。

**更高优先级的 Surface**：前台 Activity 的主窗口 Layer 优先级最高，StatusBar 和 NavigationBar 的 Layer 优先级较低。在仲裁时，高优先级 Layer 的帧率需求被优先满足。

## Display HAL 的硬件过渡过程

刷新率切换的"硬件代价"是帧率切换卡顿的物理根源。理解这个过程，有助于区分"软件能优化的部分"和"硬件限制导致的部分"。

### PLL 时钟重配置

显示面板需要一个精确的像素时钟来驱动刷新。这个时钟由 SoC 内部的 PLL（Phase-Locked Loop）电路生成。当刷新率从 60Hz 变到 120Hz 时，PLL 需要从输出一个频率"跳"到另一个频率。

PLL 重配置的过程是：先解除锁定 → 调整分频系数 → 重新锁定到目标频率。这个"重新锁定"的时间就是切换延迟的主要来源。在不同平台上：

- **高通 Snapdragon**：典型 PLL 重锁定时间在 5-15ms 范围
- **联发科 Dimensity**：类似量级，部分平台可能更长
- **三星 Exynos**：取决于具体的显示控制器实现

[待验证: 不同 SoC 平台的具体 PLL 重配置延迟数据]

值得注意的是，ARR（Adaptive Refresh Rate）的离散步进变频之所以能做到"无缝"，正是因为它在 LTPO 面板上不需要重新配置 PLL——面板通过调整像素电路的刷新时序来实现变频，而不是改变像素时钟频率。这是 ARR 比传统模式切换在硬件层面更有优势的根本原因。

### Display HAL 的状态机

Display HAL（通过 Composer HAL / HWC 接口）在收到 SurfaceFlinger 的模式切换请求后，会执行一个状态机流程：

1. **准备阶段**：HAL 保存当前显示状态，准备新的时序参数
2. **切换执行**：将新参数写入显示控制器寄存器，触发 PLL 重配置
3. **等待稳定**：等待 PLL 锁定到新频率，显示输出稳定
4. **确认完成**：通过回调通知 SurfaceFlinger 切换完成

在整个阶段 2-3 期间，显示管道的输出可能不稳定。SurfaceFlinger 通常会在这段时间暂停帧提交，等待 HAL 确认完成后再恢复。这就是过渡期出现帧丢失的原因。

[图：Display HAL 模式切换状态机流程图 — 展示从 SurfaceFlinger 请求到 HAL 确认的完整时序]

## 在 Perfetto 中识别刷新率切换卡顿

识别刷新率切换卡顿的关键在于：不在 App 侧找问题，而在 SurfaceFlinger 和 VSync Track 中找证据。

### VSync 周期跳变

这是最直接的特征。在 Perfetto 中，打开 VSYNC-app 和 VSYNC-sf Track，观察相邻 VSync 事件的时间间隔：

- 稳定 60Hz：间隔始终约 16.67ms
- 稳定 120Hz：间隔始终约 8.33ms
- **切换期间**：间隔出现跳变——可能突然从 16.67ms 变成 33.33ms（一帧丢失），然后变成 8.33ms（120Hz 稳定运行）

在 Perfetto 中可以使用以下 SQL 查询来定位 VSync 间隔异常：

```sql
-- 检测 VSync 周期跳变，标记刷新率切换位置
SELECT
  ts,
  CAST((ts - LAG(ts) OVER (ORDER BY ts)) / 1e6 AS FLOAT) AS interval_ms,
  CASE
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 7.5e6 AND 9.5e6 THEN '120Hz'
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 15.5e6 AND 17.5e6 THEN '60Hz'
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 32e6 AND 34.5e6 THEN 'dropped(60Hz)'
    ELSE 'TRANSITION'
  END AS rate_label
FROM track_event
WHERE name = 'VSYNC-app'
ORDER BY ts
```

当 `rate_label` 列出现 `TRANSITION` 或 `dropped` 时，就是刷新率切换发生的位置。

[待补充: 实际 Perfetto Trace 截图 — 展示相机→多任务场景中 VSYNC-app 间隔从 16.67ms 跳变到 33ms 再到 8.33ms 的过程]

### FrameTimeline 中的特征

在 FrameTimeline Track 中，刷新率切换卡顿表现为：

- **Expected Timeline 和 Actual Timeline 不对齐**：Expected Timeline 基于新的 VSync 周期（8.33ms）计算，但 Actual Timeline 因为切换过渡期延迟，实际呈现时间晚于预期。
- **JankType 可能显示 `SfCpuDeadlineMissed` 或 `SfGpuDeadlineMissed`**：SurfaceFlinger 在切换期间可能来不及完成合成，导致自己的 deadline 被突破。
- **但不会出现 `AppDeadlineMissed`**：App 的渲染工作正常完成了，问题不在 App。

这个区分非常关键。如果我们在 FrameTimeline 中看到 `AppDeadlineMissed`，那说明 App 本身有性能问题，不是刷新率切换的锅。如果只有 SurfaceFlinger 侧的 deadline miss，且时间点与 VSync 间隔跳变吻合，才能判定为刷新率切换卡顿。

### SurfaceFlinger 日志

SurfaceFlinger 在做出刷新率决策时会输出日志：

```
adb logcat -s SurfaceFlinger | grep -i "refresh\|mode\|setFrameRate"
```

可能看到类似这样的信息：

```
ChooseRefreshRate: layers={CameraPreview: 60fps, Launcher: Max} -> chosen: 120Hz
DisplayMode: switching from 60Hz to 120Hz (seamless)
```

这些日志能帮助确认 SurfaceFlinger 的决策逻辑——是因为哪个 Layer 的帧率需求触发了切换。

### 如何区分帧率切换卡顿和其他类型卡顿

| 特征 | 帧率切换卡顿 | App 渲染慢 | GC 暂停 | 锁竞争 |
|------|-------------|-----------|---------|--------|
| App 侧 doFrame 耗时 | 正常 (<8ms) | 偏高 (>16ms) | 突然飙高 | 突然飙高 |
| FrameTimeline JankType | SfCpuDeadlineMissed | AppDeadlineMissed | AppDeadlineMissed | AppDeadlineMissed |
| VSync 间隔跳变 | 有 | 无 | 无 | 无 |
| 主线程阻塞 | 无 | 可能有 | 有 | 有 |
| 卡顿发生场景 | 界面切换、返回桌面 | 滑动、动画 | 内存紧张时 | 并发操作 |

[来源: intake/research-feeds/2026-04-06-gracker-jank-insights.md — 高爷专家洞察]

## ARR 与帧率切换的关系

我们在 2.18 节详细讨论了 Adaptive Refresh Rate 的工作原理。这里聚焦于 ARR 如何影响帧率切换的性能。

### ARR 减少了切换的"硬代价"

传统模式切换需要 Display HAL 执行完整的硬件状态机（PLL 重配置 + 时序参数重写），过渡期在 1-3 帧之间。ARR 的离散步进变频在 LTPO 面板上通过调整像素电路的刷新时序来实现，不需要完整的模式切换。

这意味着在支持 ARR 的设备上，相机→多任务的切换理论上可以更平滑：SurfaceFlinger 仍然需要从 60Hz 调到 120Hz，但硬件层面的过渡时间从"若干帧"缩短到"几乎无感知"。

### 但 ARR 不能消除所有切换卡顿

即使硬件过渡是无缝的，软件层面的调度仍然可能导致卡顿：

1. **SurfaceFlinger 的仲裁延迟**：从检测到 Layer 帧率需求变化到做出刷新率决策，存在一定的计算延迟。如果 App 突然开始提交 120fps 的帧，但 SurfaceFlinger 还在以 60Hz 的节奏调度 VSync，中间可能出现帧间隔不匹配。

2. **Choreographer 的节奏调整**：当刷新率从 60Hz 变到 120Hz 时，Choreographer 的 VSync 回调间隔从 16.67ms 缩短到 8.33ms。如果 App 中的动画插值是基于固定 delta time 计算的（而不是基于实际 frameTimeNanos），可能会在过渡期出现位移不均匀。

3. **VsyncModulator 的 offset 调整**：刷新率切换时，VSYNC-app 和 VSYNC-sf 之间的 offset 会动态调整（由 `VsyncModulator` 管理）。在 offset 变化的瞬间，App 和 SurfaceFlinger 的时间余量可能不匹配。

[已验证: AOSP android-16.0.0_r1, services/surfaceflinger/Scheduler/VsyncModulator.cpp]

### Android 15/16/17 的持续优化

- **Android 15**：引入 True ARR，单模式内离散步进变频。首次在软件层面支持 LTPO 面板的完整变频能力。
- **Android 16**：新增 `Display.hasArrSupport()`、`Display.getSuggestedFrameRate()`、`Display.getSupportedRefreshRates()` API。RecyclerView 1.4 内置 ARR 支持——在 fling 和 smooth scroll 时自动提升刷新率。Compose 1.9 引入 `preferredFrameRate()` 修饰符。
- **Android 17**：[待验证: ARR 与 DeliQueue 无锁 MessageQueue 的交互对帧调度的影响]

## 优化策略与最佳实践

### App 开发者：避免不必要的帧率切换

最好的优化是不需要切换。

**减少帧率变更频率**：如果 App 的某个界面需要 120Hz（比如动画丰富的页面），尽量让它在进入时就以 120Hz 运行，而不是在动画开始时才请求切换。通过 `Surface.setFrameRate()` 提前声明帧率需求，给 SurfaceFlinger 留出提前切换的余量。

```java
// 在 Activity.onResume() 中声明帧率偏好，而不是在动画开始时
@Override
protected void onResume() {
    super.onResume();
    if (getWindow() != null && getWindow().getDecorView() != null) {
        getWindow().getDecorView().setFrameRate(120f,
            Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
    }
}
```

**Camera App 的帧率管理**：Camera 预览帧率通常由传感器决定（30fps 或 60fps），不需要屏幕跑 120Hz。但如果 Camera 界面有需要高刷的交互（比如滤镜选择器的横向滑动），可以考虑在交互时临时提升帧率，交互结束后降回来。更推荐的做法是使用 `RecyclerView 1.4` 的内置 ARR 支持，让系统自动处理。

**避免在关键动画路径上切换**：系统动画（多任务切换、返回桌面）期间的帧率切换由 WindowManager 和 SurfaceFlinger 协调，App 能做的有限。但如果是 App 内部动画（比如页面切换），确保动画开始前帧率已经稳定在目标值。

### 系统工程师：优化切换缓冲策略

**预测性切换**：如果 SurfaceFlinger 能提前预判即将发生的刷新率需求变化（比如从 InputDispatcher 获取到手势方向和目标 App），就可以在动画开始之前启动硬件切换，将过渡期隐藏在用户感知不到的地方。

**过渡期的帧缓冲**：在硬件过渡期间，SurfaceFlinger 可以采用"重复显示上一帧"策略，而不是让屏幕黑掉或冻结。这虽然不增加新帧，但比画面中断的感知好得多。大多数 OEM 已经实现了这种策略，但实现质量参差不齐。

**OEM 的 Display HAL 优化**：不同厂商的 Display HAL 实现差异很大。优化方向包括：缩短 PLL 重配置时间、提前准备目标模式的时序参数、在切换期间维持 VSync 信号（哪怕频率不稳定）以避免 Choreographer 的回调中断。

[待验证: 不同 OEM 厂商的 Display HAL 实现差异和切换性能数据]

### setFrameRate() 的正确使用

`setFrameRate()` 是 App 影响刷新率选择的主要手段，但用错了反而会导致更多切换。

**要做的**：
- 为视频播放使用 `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE`，帮助系统选择精确的刷新率整数倍
- 在游戏场景中声明目标帧率（比如 60fps），让系统知道不需要 120Hz
- 使用 `Choreographer.VsyncEventData.refreshRate` 监听实际刷新率，据此调整渲染节奏

**不要做的**：
- 不要在每一帧都调用 `setFrameRate()`——它不是逐帧 API，频繁调用只会增加 SurfaceFlinger 的仲裁负担
- 不要假设 `setFrameRate()` 的请求一定会被满足——始终通过 `VsyncEventData.refreshRate` 确认实际值
- 不要在 `setFrameRate()` 和 `preferredDisplayModeId` 之间反复切换——选一个，坚持用

## 版本演进

| 版本 | 关键变化 |
|------|----------|
| Android 11 (API 30) | `Surface.setFrameRate()` API，Composer HAL 2.4 Config Groups 支持无缝切换 |
| Android 12 (API 31) | `preferredDisplayModeId` 行为优化，触摸触发刷新率提升 |
| Android 13 (API 33) | `Choreographer.VsyncEventData.refreshRate` 字段，App 可感知实际刷新率 |
| Android 14 (API 34) | `setFrameRate()` 允许传入非面板原生支持的帧率值 |
| Android 15 (API 35) | ARR 引入——LTPO 面板单模式内离散步进变频，减少硬件切换代价 |
| Android 16 (API 36) | `hasArrSupport()` / `getSuggestedFrameRate()` API，RecyclerView 1.4 内置 ARR |
| Android 17 (API 37) | [待验证: ARR 帧率切换行为是否有进一步优化] |

## 与其他机制的关系

- **帧率与刷新率（2.2）**：本节是 2.2 节的延伸——2.2 讲的是帧率和刷新率的基础概念，本节聚焦于两者不匹配时的切换性能问题。
- **VSync 机制（2.3）**：刷新率切换直接改变 VSync 信号的周期，是 VSync 行为异常的常见原因之一。
- **Choreographer（2.4）**：Choreographer 通过 `VsyncEventData` 感知刷新率变化，App 需要根据变化调整动画节奏。
- **SurfaceFlinger（2.6）**：SurfaceFlinger 是刷新率决策和切换执行的核心组件。
- **Adaptive Refresh Rate（2.18）**：ARR 是减少刷新率切换性能代价的关键机制，本节讨论的很多卡顿场景在 ARR 设备上会得到缓解。

## 常见问题与误区

**误区：调用 `setFrameRate(120f)` 就能消除切换卡顿。**

恰恰相反，如果在 60fps 的场景中调用 `setFrameRate(120f)`，反而会触发一次不必要的刷新率切换。正确的做法是声明实际的渲染帧率，让系统决定最优的刷新率。

**误区：所有 120Hz 手机的切换延迟都一样。**

切换延迟取决于硬件实现。非 LTPO 面板需要完整的 Display Mode 切换（PLL 重配置），延迟在 1-3 帧。LTPO + ARR 设备可以通过离散步进无缝变频，几乎零延迟。用 `Display.hasArrSupport()` 检测设备能力。

**误区：帧率切换卡顿只在低端机上出现。**

高端旗舰同样有这个问题。相机→多任务的切换卡顿几乎在所有 Android 设备上都存在（截至 Android 16）。这是因为即使硬件切换够快，SurfaceFlinger 的软件仲裁和调度仍然需要时间。只有 ARR 设备在部分场景下能做到真正无缝。

**误区：App 可以通过提前渲染来解决切换卡顿。**

不行。帧率切换卡顿发生在 SurfaceFlinger / Display HAL 层面，App 侧渲染得再快也没用——问题在于 SurfaceFlinger 在过渡期无法正常合成和提交帧。提前渲染只会增加 BufferQueue 的积压（BufferStuffing），反而可能增加延迟。

## 扩展

### 🔸 Camera App 的帧率管理最佳实践

Camera App 是帧率切换卡顿的高发场景，因为它有独特的帧率需求：

- **预览帧率固定**：Camera 传感器采集帧率通常是 30fps 或 60fps，App 通过 `setFrameRate()` 声明这个固定帧率，避免系统误判。
- **拍照瞬间的帧率处理**：拍照时 Camera 可能短暂停止预览帧输出，这时系统可能误以为帧率需求下降而降低刷新率。拍照结束后又需要切回来，造成二次切换。
- **Camera 与系统动画的冲突**：Camera 界面上划触发多任务时，Camera 的 60fps 需求和 Launcher 动画的 120Hz 需求同时存在。SurfaceFlinger 的仲裁结果取决于哪个 Layer 优先级更高。

建议 Camera App 在非预览场景（比如相册浏览、设置页面）使用更高的帧率声明，避免频繁切换。在纯预览场景使用 `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 声明 60fps。

### 🔸 游戏引擎的帧率适配策略

游戏场景的帧率需求通常是固定的（30/60/120fps），但切换场景时可能变化：

- **使用 `setFrameRate()` 声明目标帧率**：游戏启动时声明目标帧率（如 60fps），系统会据此选择刷新率。
- **Frame Pacing Library（Swappy）**：对于 OpenGL/Vulkan 游戏，Swappy 自动处理帧率适配，包括 ARR 场景下的过渡处理。使用 Swappy 的游戏不需要手动调用 `setFrameRate()`。
- **避免动态帧率**：如果游戏帧率在 45-60fps 之间波动，系统可能反复切换刷新率。建议锁定到固定帧率（通过 `setFrameRate()` 或 `WindowManager` 参数）。

[已验证: 官方文档, developer.android.com/games/agdk/frame-pacing]

### 🔸 OEM 厂商对帧率切换的定制优化

OEM 厂商在 Display HAL 和 SurfaceFlinger 层面有大量定制空间：

- **过渡期帧策略**：有的厂商选择"重复最后一帧"，有的选择"在过渡期提前渲染一帧缓冲"。后者需要更复杂的 BufferQueue 管理，但视觉效果更好。
- **预判性切换**：部分厂商通过修改 WindowManager 的代码，在 App 切换开始前就启动硬件模式切换，将过渡期隐藏在应用切换的准备阶段。
- **帧率切换的 thermal 策略**：高温下是否允许高刷新率、是否在切换过程中添加额外的 thermal throttle 延迟，各厂商策略不同。

[待补充: 具体厂商的优化案例和数据]

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`（刷新率选择算法）
  - `frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp`（VSync offset 动态调整）
  - `frameworks/base/core/java/android/view/Surface.java`（setFrameRate API）
  - `frameworks/base/core/java/android/view/Choreographer.java`（VsyncEventData.refreshRate）
  - `frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java`（DisplayManager 策略）
- 官方文档：
  - [Refresh Rate Management](https://developer.android.com/develop/ui/views/graphics/refresh-rate)
  - [Surface.setFrameRate()](https://developer.android.com/reference/android/view/Surface#setFrameRate)
  - [Android Frame Pacing](https://developer.android.com/games/agdk/frame-pacing)
  - [Adaptive Refresh Rate Blog](https://android-developers.googleblog.com/2025/adaptive-refresh-rate.html)
- 系统属性参考：
  - `ro.surface_flinger.use_content_detection_for_refresh_rate`
  - `ro.surface_flinger.set_touch_timer_ms`
  - `debug.sf.set_idle_timer_ms`
