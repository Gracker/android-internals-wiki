---
title: "刷新率切换与帧率适配性能"
chapter: "2.19"
section: "2.19"
status: "ready-for-review"
drafted_date: "2026-04-07"
reviewed_date: "2026-05-30"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task6_state: "revisiting"
task9_state: "pending"
task9_result: pass-tech-review
task2b_state: "fixed"
task2b_result: "fixed"
pipeline_stage: "task6_pending"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-04-23"
last_verified_against: "AOSP android-16.0.0_r1, developer.android.com ARR / Display / View / Surface 文档，外部 review 2.19 问题单"
confidence: medium
sources: 
- type: aosp
path: "frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp"
tags: [refresh-rate, frame-rate, SurfaceFlinger, VSync, setFrameRate, jank, rendering, display-mode, ARR]
related_chapters: ["2.2", "2.3", "2.4", "2.6", "2.18"]
task9_reviewed_date: "2026-05-13"
task9_reviewed_by: "openclaw-task9"
last_task9_at: 2026-05-30T09:20:00+08:00
last_task6_at: "2026-05-30T01:05:00+08:00"
task6_review_notes: "2026-05-30 01: Task6 revisiting review: pass-light-edit；L1/L2 小修 2 处；保留既有截图/厂商数据待补充标注，无新增回炉项，送 Task9 复审。"
last_task6_review_log: "logs/review/2026-05-30-01-review.md"
task6_reviewed_date: "2026-05-30"
task6_reviewed_by: "openclaw-task6"
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
task6_new_rework: false
review_type: "task6-writing-quality-review"
last_task2b_at: "2026-05-30T00:50:00+08:00"
task2b_notes: "修复 Task6 2026-05-29 回炉问题：补准 ARR API 公开/flagged 边界，拆入 VRR/ARR 与 RefreshRateSelector 口径，删除尾部素材卡片。"
---


# 2.19 刷新率切换与帧率适配性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **为什么刷新率切换会引发“App 正常但用户仍感到卡顿”**：从相机 → 多任务这类典型场景切入，说明问题主要发生在 SurfaceFlinger / Display HAL，而不是 App 主线程。
- 🔹 **SurfaceFlinger 如何理解和仲裁多个 Layer 的帧率需求**：覆盖 `Surface.setFrameRate()`、内容检测、投票机制和系统级覆盖因素。
- 🔹 **硬件切换的真实代价来自哪里**：解释 PLL 重配置、Display HAL 状态机，以及无缝切换、非无缝切换、ARR 离散步进的差异。
- 🔹 **在 Perfetto 中如何识别刷新率切换卡顿**：覆盖 VSync 周期跳变、FrameTimeline 特征和 SurfaceFlinger 日志三个观察面。
- 🔹 **ARR 为什么能缓解切换卡顿，以及它的边界是什么**：说明硬件过渡缩短后，软件调度仍然可能带来卡顿。
- 🔹 **App 与系统两侧分别能做什么**：给出 `setFrameRate()`、预测性切换、过渡期缓冲策略和场景化建议。

### 扩展（可选深入）

- 🔸 **版本演进与常见误区**：把 Android 11-17 的刷新率相关演进和常见误判放在一起，方便回查。
- 🔸 **Camera / 游戏 / OEM 三类高频场景**：分别讨论预览、游戏帧率锁定和厂商定制策略。
<!-- outline-end -->

## 为什么要了解刷新率切换

在 Android 手机上，有一个几乎所有厂商都难以完全消除的卡顿场景：从相机界面划到多任务，再返回桌面的动画。无论旗舰还是中端，无论高通、联发科还是三星芯片，这个场景都很常见。问题通常出在屏幕刷新率切换。

相机界面通常以 60Hz 运行（Camera 传感器采集帧率有限，更高刷新率只会增加功耗），而桌面动画需要 120Hz 才能更顺滑。当用户从相机上划触发多任务动画时，系统需要把刷新率从 60Hz 切到 120Hz。这个切换不只是改一个配置值，它还涉及 PLL 时钟重配置、Display HAL 状态机切换和 VSync 信号源周期调整。整个过程中，若干帧可能被延迟或丢弃，用户就会看到一瞬间的卡顿。

这种卡顿有一个让人头疼的特征：在 App 侧的 Perfetto Trace 中看起来完全正常。Choreographer#doFrame 的耗时没有异常，主线程没有阻塞，RenderThread 也没有超时，但用户还是会觉得不流畅。如果我们不知道刷新率切换会导致这种卡顿，就会在错误的 Track 上浪费大量分析时间。

分析这类问题，需要把四件事串起来：刷新率切换在系统层面到底发生了什么、SurfaceFlinger 如何仲裁多个 Surface 的帧率需求、在 Perfetto 中如何识别刷新率切换导致的卡顿，以及 App 开发者和系统工程师分别能做什么来减少这类卡顿。

## 帧率切换导致卡顿的机制

### 一个典型的切换场景

相机界面 → 多任务动画 → 桌面，这个过程中发生了什么？

1. **相机界面阶段**：Camera App 通过 `Surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE)` 告诉系统"我的帧率是固定的 60fps"。SurfaceFlinger 据此将屏幕刷新率设为 60Hz（或其整数倍中最低满足帧率需求的值）。

2. **用户上划触发多任务**：WindowManager 开始执行多任务动画，Launcher 的 Surface 变为活跃状态。Launcher 并没有设置特定的帧率偏好，但动画场景的 `Content Detection` 可能会检测到帧率需求上升。另一条常见路径是触摸事件触发了 SurfaceFlinger 的 touch boost 机制，将刷新率临时提升到最高值（通常是 120Hz）。

3. **SurfaceFlinger 决策切换**：SurfaceFlinger 收集所有活跃 Layer 的帧率需求，通过 `RefreshRateSelector` 判断当前 60Hz 无法满足新出现的 120Hz 需求，决定切换到 120Hz。

4. **Display HAL 执行硬件切换**：SurfaceFlinger 通过 Composer HAL 向 Display HAL 发送模式切换指令。Display HAL 需要重新配置 PLL（Phase-Locked Loop）时钟，调整显示时序参数。这个过程在不同 SoC 平台上耗时不同：通常在 1-3 帧之间（16ms-50ms @ 60Hz），期间显示管道处于"过渡态"。

5. **过渡期的帧处理**：在硬件过渡完成之前，VSync 信号可能不稳定或暂时中断。SurfaceFlinger 在这段时间内无法正常合成和提交帧，结果要么重复显示上一帧，要么直接跳过一次合成。

[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]
[来源: intake/research-feeds/2026-04-06-gracker-jank-insights.md — 高爷专家洞察]

这就是为什么用户感知到了卡顿，但 App 侧 Trace 看起来一切正常。App 的渲染工作可能在刷新率切换之前就已经完成了，问题发生在 SurfaceFlinger / Display HAL 层面，App 完全没有感知。

### 不同切换类型的差异

刷新率切换的性能影响取决于切换的"代价"，而代价取决于切换类型：

**无缝切换（Seamless Switch）**：在同一个 Config Group 内的 Display Mode 之间切换（比如 1080p/60Hz ↔ 1080p/120Hz），由 Composer HAL 2.4+ 提供支持。切换延迟较低，通常在 1-2 帧以内。这是 Android 11+ 在支持多刷新率设备上的标准行为。

**非无缝切换（Non-seamless Switch）**：涉及分辨率变化或跨 Config Group 的切换（比如 1440p/120Hz → 1080p/60Hz）。这种切换可能导致短暂的黑屏或画面冻结，延迟可达数帧。在日常使用中较少出现。

**ARR 离散步进**（Android 15+）：在 LTPO 面板上，ARR 通过离散 VSync 步进调整刷新率，不需要完整的 Display Mode 切换。理论上过渡几乎无感知延迟，因为 PLL 仍然在同一个频率范围内微调，而不是跳变。这是目前最优的切换方式，但仅限支持 ARR 的 LTPO 设备。

[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

## SurfaceFlinger 的刷新率选择策略

SurfaceFlinger 是多个 Layer 帧率需求的仲裁者，决策逻辑相当复杂。

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

当屏幕上有多个活跃 Layer 时（比如前台 App + 浮窗 + StatusBar），SurfaceFlinger 需要在设备支持的刷新率集合里挑一个当前最合适的值。把这段逻辑理解成“候选模式排序”更贴近源码，而不是“最小公倍数规则”。

在 `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` 里，发起仲裁的是 `mScheduler->chooseRefreshRateForContent(...)`。Scheduler 会把可见 Layer 整理成 `LayerRequirement` 列表，再交给 `RefreshRateSelector::getRankedFrameRates()` 生成一个按分数排序的候选结果。

每个 Layer 都带着自己的 `LayerVoteType` 进入打分流程。android-16.0.0_r1 里常见的票型有 `Min`、`Max`、`Heuristic`、`ExplicitDefault`、`ExplicitExactOrMultiple`、`ExplicitGte` 和 `ExplicitCategory`。`RefreshRateSelector::calculateLayerScoreLocked()` 会按票型、目标帧率、候选模式是否支持 seamless 切换来计算单层 score，再把所有 Layer 的 score 汇总后排序。注意，Android 15/16 中该函数的内部实现经历了多次重构：部分票型的评分逻辑已经拆分到独立的 helper 方法（如 `getScoreForLayer()` 系列），`calculateLayerScoreLocked()` 本身的职能已从"集中计算"转向"入口分发"。读者在源码中定位时，应该顺着这个函数的调用链往下追，而不是只看函数体本身。

ARR 和 VRR 的边界也要放在这条仲裁路径里看。ARR 是 Android 15+ 对 App 公开的能力表达：系统在支持硬件上用离散 VSync 步进匹配内容帧率，减少完整 mode switch。VRR 更偏底层配置和显示能力，描述的是显示端允许呈现间隔随内容变化的范围。`LayerVoteType`、内容检测、触摸 boost、idle timer、Display policy 都会进入 `RefreshRateSelector` 的候选排序；App 侧不要把 ARR API 理解成直接控制 VRR 参数。

24fps 视频和 60fps 前台动画同时存在时，120Hz 往往会排在前面，因为它同时满足 24fps 的整数倍关系和 60fps 的交互需求，还常常落在可 seamless 切换的候选集合里。但这不是写死的规则。只要 Battery Saver、GameManager、Display policy 或 App 请求范围收窄了候选集合，排序结果就可能变成 60Hz、90Hz 或别的模式。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp + frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp]

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

PLL 重配置的过程是：先解除锁定 → 调整分频系数 → 重新锁定到目标频率。这个"重新锁定"的时间就是切换延迟的主要来源。不同 SoC 的切换代价差异很大，不能把一台设备的结果直接套到所有平台。经验上，高通旗舰平台更常见 dual-PLL 或动态分频路径，联发科部分中端平台更容易落到完整重锁流程。

- **支持 seamless / dual-PLL / 动态分频的高端平台**：同一 config group 内切换时，过渡常能压到 0-1 帧内
- **仍依赖单 PLL 完整重锁的中端平台**：更容易出现 stop → relock → resume 的完整过程，常见代价是 1-2 帧
- **跨 config group 的 non-seamless 切换**：通常最贵，除了重锁定，还可能伴随分辨率或时序重配，冻结时间会进一步拉长

所以排查时要同时看设备支持的 display mode、是否属于 seamless switch，以及 Perfetto / SurfaceFlinger 日志里的实际切换结果，不要只记一个固定的“5-15ms”。

ARR（Adaptive Refresh Rate）的离散步进变频之所以更平滑，是因为 LTPO 面板可以在同一组时序能力内调整 VSync 步进，很多场景不需要走完整的 mode switch。硬件切换成本降下来了，软件调度问题也更容易暴露出来。

### Display HAL 的状态机

Display HAL（通过 Composer HAL / HWC 接口）在收到 SurfaceFlinger 的模式切换请求后，会执行一个状态机流程：

1. **准备阶段**：HAL 保存当前显示状态，准备新的时序参数
2. **切换执行**：将新参数写入显示控制器寄存器，触发 PLL 重配置
3. **等待稳定**：等待 PLL 锁定到新频率，显示输出稳定
4. **确认完成**：通过回调通知 SurfaceFlinger 切换完成

在整个阶段 2-3 期间，显示管道的输出可能不稳定。SurfaceFlinger 通常会在这段时间暂停帧提交，等待 HAL 确认完成后再恢复。这就是过渡期出现帧丢失的原因。

[图：Display HAL 模式切换状态机流程图，展示从 SurfaceFlinger 请求到 HAL 确认的完整时序]

### Composer AIDL expectedPresentTime 与预判式切换

`expectedPresentTime` 字段位于 Composer AIDL 的 `DisplayCommand.aidl`，android-13.0.0_r1 已存在。SurfaceFlinger 在提交合成请求时把预期的呈现时间戳一并告诉 Display HAL，让 HAL 能提前启动硬件配置，把部分过渡开销隐藏在合成流水线的等待时间里。

Android 16 强制要求 AIDL V4 Composer HAL，进一步巩固了这条路径。但 `expectedPresentTime` 本身不是 Android 16 引入的。

在支持 dual-PLL 的高端平台上，预判式切换可以把硬件过渡从"1-2 帧冻结"压到"0-1 帧"。预判式切换的前提是 SurfaceFlinger 能准确预测下一帧的呈现时间。如果 VSync 调度出现抖动（比如 ARR 刚好在切换点调整了步进），预测偏差可能导致 Display HAL 提前完成的 PLL 重锁与实际呈现时间之间出现间隙。

[已验证: AOSP android-13.0.0_r1, hardware/interfaces/graphics/composer/aidl/.../DisplayCommand.aidl — expectedPresentTime 字段已存在]

## 在 Perfetto 中识别刷新率切换卡顿

识别刷新率切换卡顿时，我们要把重点放在 SurfaceFlinger 和 VSync Track 上，而不是先在 App 侧找问题。

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

这个区分会决定排查方向。如果我们在 FrameTimeline 中看到 `AppDeadlineMissed`，那说明 App 本身有性能问题，不是刷新率切换的锅。如果只有 SurfaceFlinger 侧的 deadline miss，且时间点与 VSync 间隔跳变吻合，才能判定为刷新率切换卡顿。

### SurfaceFlinger 日志

SurfaceFlinger 在做出刷新率决策时会输出日志：

```bash
adb logcat -s SurfaceFlinger | grep -i "refresh\|mode\|setFrameRate"
```

可能看到类似这样的信息：

```text
ChooseRefreshRate: layers={CameraPreview: 60fps, Launcher: Max} -> chosen: 120Hz
DisplayMode: switching from 60Hz to 120Hz (seamless)
```

这些日志能帮助确认 SurfaceFlinger 的决策逻辑，也能帮助我们判断究竟是哪个 Layer 的帧率需求触发了切换。

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

2.18 节已经展开 Adaptive Refresh Rate 的工作原理。这里聚焦 ARR 对帧率切换性能的影响。

### ARR 减少了切换的"硬代价"

传统模式切换需要 Display HAL 执行完整的硬件状态机（PLL 重配置 + 时序参数重写），过渡期在 1-3 帧之间。ARR 的离散步进变频在 LTPO 面板上通过调整像素电路的刷新时序来实现，不需要完整的模式切换。

在支持 ARR 的设备上，相机→多任务的切换理论上会更平滑。SurfaceFlinger 仍然需要从 60Hz 调到 120Hz，但硬件层面的过渡时间会从"若干帧"缩短到"几乎无感知"。

### 但 ARR 不能消除所有切换卡顿

即使硬件过渡是无缝的，软件层面的调度仍然可能导致卡顿：

1. **SurfaceFlinger 的仲裁延迟**：从检测到 Layer 帧率需求变化到做出刷新率决策，存在一定的计算延迟。如果 App 突然开始提交 120fps 的帧，但 SurfaceFlinger 还在以 60Hz 的节奏调度 VSync，中间可能出现帧间隔不匹配。

2. **Choreographer 的节奏调整**：当刷新率从 60Hz 变到 120Hz 时，Choreographer 的 VSync 回调间隔从 16.67ms 缩短到 8.33ms。如果 App 中的动画插值是基于固定 delta time 计算的（而不是基于实际 frameTimeNanos），可能会在过渡期出现位移不均匀。

3. **VsyncModulator 的 offset 调整**：刷新率切换时，`VsyncModulator` 会通过 `setVsyncConfigSet()` 切换当前的 vsync config set，把新的 `VSYNC-app` / `VSYNC-sf` phase offsets 应用到调度器里。这样 App 的唤醒时点和 SurfaceFlinger 的合成时点才能跟上新的刷新周期。若 config set 切换滞后，App 还按旧节奏产帧，SurfaceFlinger 已按新节奏消费，中间就会空出 1-2 帧的预算。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp]

### VsyncModulator 的 phase offset 切换机制

刷新率切换时，`VsyncModulator` 需要把新的 VSync phase offset 应用到调度器。当前 android-16.0.0_r1 的实现中，`setVsyncConfigSet()` 通过 `std::lock_guard<std::mutex>` 保护 `mVsyncConfigSet` 的写入，按值替换整个 config set。VSync 线程在每次唤醒时读取当前 config set 来计算唤醒偏移。

Binder 线程（提交 Transaction）和 VSync 线程共享这把锁。锁持有时间很短（一次结构体赋值），但刷新率切换瞬间如果两条线程恰好竞争，VSync 线程可能等一垒锁后才能拿到新配置，导致那一帧的唤醒时点有微秒级抖动。在 120Hz 设备上，一次 VSync 周期只有 8.33ms，相位偏移的抖动如果超过 1ms 就可能被用户感知。当前实现的锁持有方差对大多数场景影响有限，但在极端压力场景下仍有改进空间。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp — setVsyncConfigSet() 使用 std::lock_guard<std::mutex>]

### 精确 fps 请求、category 请求和 range 请求怎么选

Android 11-14 的主入口还是 `Surface.setFrameRate(float, int)`。Android 16 的公开 SDK 增加了 `Display.hasArrSupport()` 和 `Display.getSuggestedFrameRate(int)`，同时让 `getSupportedRefreshRates()` 更适合 ARR 设备读取 render rate 集合。App 侧的稳定路径要优先使用公开 SDK；`Surface.FrameRateParams` / `setFrameRate(FrameRateParams)` 这类范围提示路径仍按 flagged API 处理，不写成普通三方 App 可直接依赖的接口。

| 场景 | 首选 API | 适合什么时候用 | 备注 |
|------|----------|----------------|------|
| 视频、Camera 预览、固定帧率游戏画面 | `Surface.setFrameRate(..., FRAME_RATE_COMPATIBILITY_FIXED_SOURCE)` | 内容生产速率固定，系统只需要找整数倍刷新率 | 24fps / 30fps / 60fps 这类场景最稳妥 |
| 普通 View 动画 | `View.setRequestedFrameRate(120f)` 或 `View.REQUESTED_FRAME_RATE_CATEGORY_HIGH` | 只想表达“这里需要更高刷新率”，不想把值绑死到某个 mode | category 请求更适合 ARR 设备 |
| Compose 动画 | `Modifier.preferredFrameRate(...)` | Compose 组件的局部动画、滚动和过渡 | 语义和 View 侧一致 |
| 自定义滚动控件 | `View.setFrameContentVelocity(...)` | 刷新率应该跟着 fling / smooth scroll 速度变化 | 系统按速度决定是否升降刷新率 |
| 底层 Surface 需要范围提示 | `Surface.FrameRateParams` / `setFrameRate(FrameRateParams)` | 系统组件或受控平台构建需要同时表达范围与固定片源约束 | flagged API 路径；普通三方 App 的稳定路径仍以 `Surface.setFrameRate(float,int[,int])`、`View.setRequestedFrameRate()`、`Display.getSuggestedFrameRate()` 为主 |

Android 16（API 36）才公开 `Display.getSuggestedFrameRate(int category)`。调用时要传 `Display.FRAME_RATE_CATEGORY_NORMAL` 或 `Display.FRAME_RATE_CATEGORY_HIGH`，不要和 `View.REQUESTED_FRAME_RATE_CATEGORY_*` 混用，也不要在低版本直接调用。它返回的是系统给 normal / high 两类场景的建议刷新率，不负责回答“45fps 该映射到 60Hz 还是 90Hz”。45fps 这类具体映射仍然要交给 `RefreshRateSelector`、Display policy 和设备支持的刷新率集合去决定。

RecyclerView 1.4 和 `NestedScrollView` 这类滚动容器，做法是把滚动速度交给系统；Compose 动画更适合用 `Modifier.preferredFrameRate(...)` 或 View category 请求，让 ARR 自己选 normal 还是 high。

## 优化策略与最佳实践

### App 开发者：避免不必要的帧率切换

最好的优化是不需要切换。

**减少帧率变更频率**：如果 App 的某个界面需要高刷新率（比如过渡动画很多的页面），尽量在界面进入时就表达偏好，而不是等动画开始才触发仲裁。固定片源继续用 `Surface.setFrameRate()`；UI 层动画在 ARR 设备上更适合 `View.setRequestedFrameRate()`。

```java
// Android 15-QPR1+
// 在界面恢复时先表达高刷偏好，避免动画开始时才触发仲裁
@Override
protected void onResume() {
    super.onResume();
    final View decorView = getWindow().getDecorView();
    decorView.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
}
```

**Camera App 的帧率管理**：Camera 预览帧率通常由传感器决定（30fps 或 60fps），不需要屏幕跑 120Hz。但如果 Camera 界面有需要高刷的交互（比如滤镜选择器的横向滑动），可以考虑在交互时临时提升帧率，交互结束后降回来。更推荐的做法是使用 `RecyclerView 1.4` 的内置 ARR 支持，让系统自动处理。

**避免在关键动画路径上切换**：系统动画（多任务切换、返回桌面）期间的帧率切换由 WindowManager 和 SurfaceFlinger 协调，App 能做的有限。但如果是 App 内部动画（比如页面切换），确保动画开始前帧率已经稳定在目标值。

### 系统工程师：优化切换缓冲策略

**预测性切换**：如果 SurfaceFlinger 能提前预判即将发生的刷新率需求变化（比如从 InputDispatcher 获取到手势方向和目标 App），就可以在动画开始之前启动硬件切换，将过渡期隐藏在用户感知不到的地方。

**过渡期的帧缓冲**：在硬件过渡期间，SurfaceFlinger 可以采用"重复显示上一帧"策略，而不是让屏幕黑掉或冻结。这虽然不增加新帧，但比画面中断的感知好得多。大多数 OEM 已经实现了这种策略，但实现质量参差不齐。

**OEM 的 Display HAL 优化**：不同厂商的 Display HAL 实现差异很大。优化方向包括：缩短 PLL 重配置时间、提前准备目标模式的时序参数、在切换期间维持 VSync 信号（哪怕频率不稳定）以避免 Choreographer 的回调中断。

[待验证: 不同 OEM 厂商的 Display HAL 实现差异和切换性能数据]

### 观察实际刷新节奏时看什么

App 侧公开 API 没有直接暴露刷新率字段。`Choreographer.VsyncCallback#onVsync(FrameData data)` 暴露的是 `FrameData` / `FrameTimeline`，我们能直接读到的是 `getFrameTimeNanos()`、`getFrameTimelines()` 和 `getPreferredFrameTimeline()` 这类时间线信息。

调试时可以分成两层看：

- **看 FrameData / FrameTimeline**：用 `getPreferredFrameTimeline()` 和相邻帧的 expected presentation time，判断这一段动画是不是已经按新的节奏在调度。
- **看 Display API**：用 `Display.getRefreshRate()`、`DisplayManager.DisplayListener`、`Display.getSuggestedFrameRate()` 和 `Display.getSupportedRefreshRates()` 看当前模式、系统建议值和设备支持集合。
- **看 Trace**：把上面的 Display 变化放到和 Perfetto 的 VSYNC-app / VSYNC-sf 间隔跳变同一条时间轴里，确认卡顿究竟出在模式切换、调度延后，还是 App 自己没跟上。

所以这里有两条简单规则：
- 不要把 `Display.getSuggestedFrameRate()` 当成任意 fps → 刷新率映射器，它只接受 `FRAME_RATE_CATEGORY_NORMAL` / `FRAME_RATE_CATEGORY_HIGH`。
- 不要假设 `setFrameRate()` 请求一定会被满足，最终还是要回到 Display API 和 Perfetto 结果核对。

## 版本演进

| 阶段 | 已验证的变化 |
|------|--------------|
| Android 11-14 | 多刷新率 mode switching 成为常见实现，`Surface.setFrameRate()` 用来表达固定帧源或显式 fps 提示 |
| Android 15-QPR1+ | 支持对应 HAL API 的设备开始提供 ARR，刷新率可以在单一 mode 内跟随内容节奏变化 |
| Android 16 公开接口 | `Display.hasArrSupport()`、`Display.getSuggestedFrameRate()`、`Display.getSupportedRefreshRates()` 让 App 能直接读取设备能力和系统建议值 |
| Android 16 | `VsyncModulator` 的 `setVsyncConfigSet()` 通过 `std::lock_guard<std::mutex>` 保护 config set 写入，锁持有时间短，极端压力场景下仍有微秒级抖动空间 |
| Android 17 | 本轮只保留 `RefreshRateSelector` / `LayerVoteType` / VRR 配置关系作为 Task9 复核线索；未用 main/master 资料写成正文结论 |
| Android 16 | 16KB 页面大小推广，图形缓冲区分配需考虑页对齐影响 |
| AndroidX / Compose | RecyclerView 1.4、AndroidX core 1.15、Compose `preferredFrameRate()` 把滚动和局部动画的 ARR 适配放到更高层 API 里 |

## 与其他机制的关系

- **帧率与刷新率（2.2）**：本节是 2.2 节的延伸。2.2 讲的是帧率和刷新率的基础概念，本节聚焦于两者不匹配时的切换性能问题。
- **VSync 机制（2.3）**：刷新率切换直接改变 VSync 信号的周期，是 VSync 行为异常的常见原因之一。
- **Choreographer（2.4）**：Choreographer 提供 `FrameData / FrameTimeline` 这类调度时间线；刷新率数值本身仍要结合 Display API 来看。
- **SurfaceFlinger（2.6）**：SurfaceFlinger 是刷新率决策和切换执行的核心组件。
- **Adaptive Refresh Rate（2.18）**：ARR 是减少刷新率切换性能代价的关键机制，本节讨论的很多卡顿场景在 ARR 设备上会得到缓解。

## 常见问题与误区

**误区：调用 `setFrameRate(120f)` 就能消除切换卡顿。**

在 60fps 的场景中调用 `setFrameRate(120f)`，反而会触发一次不必要的刷新率切换。正确的做法是声明实际的渲染帧率，让系统决定最优的刷新率。

**误区：所有 120Hz 手机的切换延迟都一样。**

切换延迟取决于硬件实现。非 LTPO 面板需要完整的 Display Mode 切换（PLL 重配置），延迟在 1-3 帧。LTPO + ARR 设备可以通过离散步进无缝变频，几乎零延迟。用 `Display.hasArrSupport()` 检测设备能力。

**误区：帧率切换卡顿只在低端机上出现。**

高端旗舰同样有这个问题。相机→多任务的切换卡顿几乎在所有 Android 设备上都存在（截至 Android 16）。这是因为即使硬件切换够快，SurfaceFlinger 的软件仲裁和调度仍然需要时间。只有 ARR 设备在部分场景下能做到无缝过渡。

**误区：App 可以通过提前渲染来解决切换卡顿。**

不行。帧率切换卡顿发生在 SurfaceFlinger / Display HAL 层面，App 侧渲染得再快也没用，问题在于 SurfaceFlinger 在过渡期无法正常合成和提交帧。提前渲染只会增加 BufferQueue 的积压（BufferStuffing），反而可能增加延迟。

## 扩展

### 🔸 Camera App 的帧率管理最佳实践

Camera App 是帧率切换卡顿的高发场景，因为它有独特的帧率需求：

- **预览帧率固定**：Camera 传感器采集帧率通常是 30fps 或 60fps，App 通过 `setFrameRate()` 声明这个固定帧率，避免系统误判。
- **拍照瞬间的帧率处理**：拍照时 Camera 可能短暂停止预览帧输出，这时系统可能把它判断为帧率需求下降并降低刷新率。拍照结束后又需要切回来，造成二次切换。
- **Camera 与系统动画的冲突**：Camera 界面上划触发多任务时，Camera 的 60fps 需求和 Launcher 动画的 120Hz 需求同时存在。SurfaceFlinger 的仲裁结果取决于哪个 Layer 优先级更高。

建议 Camera App 在非预览场景（比如相册浏览、设置页面）使用更高的帧率声明，避免频繁切换。在纯预览场景使用 `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 声明 60fps。

### 🔸 游戏引擎的帧率适配策略

游戏场景的帧率需求通常是固定的（30/60/120fps），但切换场景时可能变化：

- **使用 `setFrameRate()` 声明目标帧率**：游戏启动时声明目标帧率（如 60fps），系统会据此选择刷新率。
- **Frame Pacing Library（Swappy）**：对于 OpenGL/Vulkan 游戏，Swappy 自动处理帧率适配，包括 ARR 场景下的过渡处理。使用 Swappy 的游戏不需要手动调用 `setFrameRate()`。
- **避免动态帧率**：如果游戏帧率在 45-60fps 之间波动，系统可能反复切换刷新率。建议锁定到固定帧率（通过 `setFrameRate()` 或 `WindowManager` 参数）。

[已验证: 官方文档, developer.android.com/games/sdk/frame-pacing]

### 🔸 OEM 厂商对帧率切换的定制优化

OEM 厂商在 Display HAL 和 SurfaceFlinger 层面有大量定制空间：

- **过渡期帧策略**：有的厂商选择"重复最后一帧"，有的选择"在过渡期提前渲染一帧缓冲"。后者需要更复杂的 BufferQueue 管理，但视觉效果更好。
- **预判性切换**：部分厂商通过修改 WindowManager 的代码，在 App 切换开始前就启动硬件模式切换，将过渡期隐藏在应用切换的准备阶段。
- **帧率切换的 thermal 策略**：高温下是否允许高刷新率、是否在切换过程中添加额外的 thermal throttle 延迟，各厂商策略不同。

[待补充: 具体厂商的优化案例和数据]

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`（`mScheduler->chooseRefreshRateForContent(...)` 调用点）
  - `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`（候选模式排序与 score 计算）
  - `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.h`（`LayerVoteType` 定义）
  - `frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp`（VSync offset 动态调整）
  - `frameworks/base/core/java/android/view/Surface.java`（`setFrameRate()` 与 `FrameRateParams`）
  - `frameworks/base/core/java/android/view/View.java`（`setRequestedFrameRate()`、`setFrameContentVelocity()`）
  - `frameworks/base/core/java/android/view/Display.java`（`hasArrSupport()`、`getSuggestedFrameRate()`、`getSupportedRefreshRates()`）
  - `frameworks/base/core/java/android/view/Choreographer.java`（`VsyncCallback` 与 `FrameData`）
- 官方文档：
  - [Adaptive Refresh Rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
  - [Surface.setFrameRate()](https://developer.android.com/reference/android/view/Surface#setFrameRate)
  - [Display.getSuggestedFrameRate(int)](https://developer.android.com/reference/android/view/Display#getSuggestedFrameRate(int))
  - [View.setRequestedFrameRate(float)](https://developer.android.com/reference/android/view/View#setRequestedFrameRate(float))
  - [View.setFrameContentVelocity(float)](https://developer.android.com/reference/android/view/View#setFrameContentVelocity(float))
  - [Android Frame Pacing](https://developer.android.com/games/sdk/frame-pacing)
- 系统属性参考：
  - `ro.surface_flinger.use_content_detection_for_refresh_rate`
  - `ro.surface_flinger.set_touch_timer_ms`
  - `debug.sf.set_idle_timer_ms`
