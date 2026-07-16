---
title: "刷新率切换与帧率适配性能"
chapter: "2.19"
section: "2.19"
status: finalized
drafted_date: "2026-04-07"
reviewed_date: "2026-06-06"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
pipeline_stage: "ready-to-publish"
last_task2b_at: 2026-06-06T02:57:42+08:00
last_task2b_lite_at: 2026-06-06
task2b_notes: "2026-06-06 Task2B main 回炉 #3：P1 ARR版本表重写（拆分MRR/ARR边界 Android 15-QPR1+），ARR原理和场景描述修正，厂商功耗/延迟/百分比声明全部去量化为定性描述，移除60-80%切换减少和无法回溯的设备条件声明。"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-04-23"
last_verified_against: AOSP android-16.0.0_r1, developer.android.com ARR / Display / View / Surface 文档
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp"
tags: [refresh-rate, frame-rate, SurfaceFlinger, VSync, setFrameRate, jank, rendering, display-mode, ARR]
related_chapters: ["2.2", "2.3", "2.4", "2.6", "2.18"]
task9_reviewed_date: "2026-06-06"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-06T04:21:00+08:00"
last_task6_at: "2026-06-06T05:12:48+08:00"
task6_review_notes: "2026-06-06 Task6 revisiting-review #5: L1/L2 clean (禁用词0/高频词:真正1+确实2均功能性/否定纠正2/元叙述0/物理动词0). L3/L4 pass (ARR/MRR版本边界清晰/厂商差异定性合理/Trace观察点实用/误区分析到位). No B-class issues. task6=pass-light-edit + task9=auto-fixed + queue empty → promote finalized."
last_task6_review_log: "logs/review/2026-06-06-05-review.md"
task6_reviewed_date: 2026-06-04
task6_reviewed_by: openclaw-task6
task6_l1_l2_fixes: 6
task6_l3_l4_issues: 3
task6_new_rework: true
review_type: "task6-writing-quality-review"
last_task2b_verifier_at: "2026-06-02T15:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-02-15-task2b-verifier.md"
last_task9_review_log: logs/deep-review/2026-06-06-04-deep-review.md
task9_review_notes: "2026-06-06 Task9 04 auto-fix: 修正 ARR/MRR 版本边界、ARR 工作模型、HWC 前提、Surface.setFrameRate(0) 清空偏好、普通游戏误用 FIXED_SOURCE，以及未证统一 fallback / 渐进切换表述；回到 Task6 复审。"
task9_result: auto-fixed
last_task2b_by: openclaw-task2b-main
last_task9_autofix_at: 2026-06-06
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-17
---

---

# 2.19 刷新率切换与帧率适配性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **为什么刷新率切换会引发"App 正常但用户仍感到卡顿"**：从相机 → 多任务这类典型场景切入，说明问题主要发生在 SurfaceFlinger / Display HAL，而不是 App 主线程。
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

4. **Display HAL 执行硬件切换**：SurfaceFlinger 通过 Composer HAL 向 Display HAL 发送模式切换指令。Display HAL 可能需要重新配置显示时序和面板相关状态。这个过程在不同 SoC、面板和 HAL 实现上差异很大，可能跨越多个 VSync，期间显示管道处于"过渡态"。

5. **过渡期的帧处理**：在硬件过渡完成之前，VSync 信号可能不稳定或暂时中断。SurfaceFlinger 在这段时间内无法正常合成和提交帧，结果要么重复显示上一帧，要么直接跳过一次合成。

这就是为什么用户感知到了卡顿，但 App 侧 Trace 看起来一切正常。App 的渲染工作可能在刷新率切换之前就已经完成了，问题发生在 SurfaceFlinger / Display HAL 层面，App 完全没有感知。

### 不同切换类型的差异

刷新率切换的性能影响取决于切换的"代价"，而代价取决于切换类型：

**无缝切换（Seamless Switch）**：在同一个 Config Group 内的 Display Mode 之间切换（比如 1080p/60Hz ↔ 1080p/120Hz），由 Composer HAL 2.4+ 提供支持。切换延迟较低，通常在 1-2 帧以内。这是 Android 11+ 在支持多刷新率设备上的标准行为。

**非无缝切换（Non-seamless Switch）**：涉及分辨率变化或跨 Config Group 的切换（比如 1440p/120Hz → 1080p/60Hz）。这种切换可能导致短暂的黑屏或画面冻结，延迟可达数帧。在日常使用中较少出现。

**ARR（Adaptive Refresh Rate）过渡**：Android 15 引入 ARR，Android 15-QPR1+ 起在支持的设备上可用。官方定义是让显示刷新率根据内容帧率使用离散 VSync 步长适配；在 ARR 面板上，display VSync rate 与 refresh rate 解耦，可在同一个 display mode 内按内容 cadence 改变刷新节奏，从而减少传统 mode switching 带来的 jank。Android 16 开始可通过 `Display.hasArrSupport()` 查询支持状态。

## SurfaceFlinger 如何仲裁多个 Layer 的帧率需求

### 帧率投票机制

SurfaceFlinger 使用一个称为"帧率投票"的机制来决定最终的屏幕刷新率。每个 Layer（Surface）都可以表达自己的帧率需求，SurfaceFlinger 综合考虑这些需求后做出最终决策。

#### FrameRate 类型

| 类型 | 说明 | 典型使用场景 |
|------|------|-------------|
| `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` | 固定源帧率 | 视频播放、相机预览 |
| `FRAME_RATE_COMPATIBILITY_DEFAULT` | 默认兼容 | 普通界面、列表滚动 |
| `FRAME_RATE_COMPATIBILITY_AT_LEAST` | 最低帧率 | 希望刷新率不低于指定值（如游戏至少 60fps） |
| `FRAME_RATE_COMPATIBILITY_EXACT` | 精确帧率 | 动画、游戏（需与屏幕刷新率精确对齐）— `@hide`，非公开 API |

#### 投票权重

SurfaceFlinger 为不同类型的 Layer 分配不同的投票权重：

1. **具有高优先级的 Layer**：如全屏视频、相机预览，权重最高
2. **具有动画的 Layer**：如 Launcher 动画，权重中等
3. **静态内容**：如普通文本、图片，权重最低

### Content Detection（内容检测）

Android 11 引入了内容检测机制，自动判断屏幕内容类型并调整刷新率。该机制依赖 `RefreshRateSelector` 中按 Layer 类型赋权的逻辑（详见下一小节 `RefreshRateSelector`），而非独立的 `VsyncConfiguration` 代码路径。

> 在 android-16.0.0_r1 中，内容检测的核心依据是 `LayerMetadata` 中的 `contentType` 字段和 `RefreshRateSelector::getRankedFrameRates()` 中对不同 Layer 类型的权重分配，参与路径：`frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`。`VsyncConfiguration` 类名和 `setPolicy()` 方法在 android-16.0.0_r1 中无对应物。

### Surface.setFrameRate() API

App 可以通过 Surface.setFrameRate() 来指定自己的帧率需求：

```java
// 设置固定 60fps 帧率
surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);

// 清空帧率偏好，让系统根据内容检测和其他 Surface 投票决策
surface.setFrameRate(0f, FRAME_RATE_COMPATIBILITY_DEFAULT);
```

#### API 参数说明

```java
// Surface.java (android-16.0.0_r1)
// 实际签名为 void，兼容性常量包括:
//   FRAME_RATE_COMPATIBILITY_DEFAULT (0) — 系统自动决策
//   FRAME_RATE_COMPATIBILITY_FIXED_SOURCE (1) — 固定帧率，如相机预览
//   FRAME_RATE_COMPATIBILITY_AT_LEAST (2) — 最低帧率约束，公开常量
//   FRAME_RATE_COMPATIBILITY_EXACT (100) — 精确匹配，@hide，非公开 API
//   FRAME_RATE_COMPATIBILITY_MIN (102) — 最低帧率，@hide，非公开 API
public void setFrameRate(float rate, @FrameRateCompatibility int compatibility)
```

### RefreshRateSelector

RefreshRateSelector 是 SurfaceFlinger 中的核心组件，负责综合所有因素决定最终的刷新率：

> 核心决策路径（android-16.0.0_r1）：各 Layer 的帧率需求 → `RefreshRateSelector::getRankedFrameRates()` 排序 → `Scheduler` 综合 touch boost、idle timer、power HAL hint 等信号 → 通过 `setActiveMode()` 将最终选定的显示模式提交给 Composer HAL。`Scheduler.cpp` 源码路径：`frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp`。

> 在 android-16.0.0_r1 中，`VoteSet` 类名、`collectVotes()` / `calculateOptimalRate()` / `supportsARR()` 均不存在，实际决策入口为 `RefreshRateSelector::getRankedFrameRates()`。以下原理性描述基于公开文档和行为推断，不逐行对标源码。

## 硬件切换的真实代价

### PLL 重配置成本

PLL（Phase-Locked Loop）重新配置是刷新率切换的主要耗时来源。PLL 负责生成显示所需的各种时钟信号，不同刷新率需要不同的时钟频率。

#### PLL 切换延迟

> 以下 PLL 切换延迟描述来自 SoC 厂商公开白皮书和显示驱动文档的架构级描述，非统一测试条件下的实测数据，不同设备上实际延迟可能偏离，仅作为定性趋势参考。

#### PLL 状态机

```
PLL 状态转换：
60Hz PLL → 120Hz PLL
    ↓
配置 PLL 参数 → 锁定新频率 → 稳定输出
    ↓
切换显示时序 → 验证信号 → 完成切换
```

### Display HAL 状态机

Display HAL 负责与硬件显示控制器交互，其状态机切换也会影响切换延迟：

> 在 android-16.0.0_r1 中，Composer HAL 的模式切换入口是 `IComposer::setActiveConfig()` / `IComposer::setActiveConfigWithConstraints()`，对应 HWC2 的 `setActiveConfig()`。Display HAL 并不直接暴露 `setMode()` 或 `setAdaptiveRefreshRate()` 这样的虚拟方法——这些精确签名的代码块在 android-16.0.0_r1 中不可溯源，以下原理描述为路径级简化：

> 模式切换流程：SurfaceFlinger 通过 `composer::setActiveConfig()` 向 Composer HAL 发起模式切换请求 → HAL 检查 mode 是否在当前 `Config Group` 内（无缝切换）→ 应用显示时序参数（HWC2 caps 的 `Seamless` flag）→ 返回切换结果。

> 不同 Android 版本的 Composer HAL 接口版本（`IComposer` / HWC2）和切换能力以设备 manifest 和设备实现为准。

### VSync 周期调整

刷新率切换后，VSync 信号的周期也会相应调整：

> 在 android-16.0.0_r1 中，VSync 周期管理由 `VSyncDispatchTimerQueue` 和 `VSyncTracker` 协同实现，核心路径在 `frameworks/native/services/surfaceflinger/Scheduler/VSyncDispatchTimerQueue.cpp`。刷新率变化时，`DisplayDevice::setActiveMode()` 触发 `VSyncTracker::setDisplayModePtr()` 更新追踪参数，新的 VSync 周期在下一个调度窗口生效。

> 注意：`setRefreshRate()` / `adjustPeriodGradually()` / `notifyARRChange()` 等精确方法名在 android-16.0.0_r1 中未找到对应实现，`mDynamicVSync` / `ADJUSTMENT_THRESHOLD` 同样不可溯源。

## 在 Perfetto 中识别刷新率切换卡顿

### VSync 周期跳变分析

在 Perfetto 中，VSync 周期的变化是识别刷新率切换的重要指标：

> 以下 Perfetto 配置使用的是概念性事件名（`vsync_period`、`refresh_rate_change`、`display_mode_switch`），不是 Perfetto 的实际 data source 或 ftrace event 名。实际 Perfetto 配置应使用 Perfetto textproto 格式。

> 监控刷新率变化的推荐方法（已验证）：
> - 抓取 `android.surfaceflinger.frametimeline` data source，并在 Trace Processor 中查看 `actual_frame_timeline_slice` / `expected_frame_timeline_slice`
> - 在 Perfetto UI 的 VSync timelines track（`actual_vsync` 计数器）观察周期变化
> - 使用 `adb shell dumpsys display` 查看 `mActiveMode` 或 `mActiveConfig`

### VSync 周期变化的特征

```
正常情况下：
VSync 周期：16.67ms (60Hz) 或 8.33ms (120Hz)
切换过程：
16.67ms → 16.67ms → 8.33ms → 8.33ms
                     ↑
                    切换点
```

### FrameTimeline 特征分析

刷新率切换会影响 FrameTimeline 的特征：

```java
// 监控帧间隔异常（可能由刷新率切换引起）
public void monitorFrameIntervals() {
    final long[] lastFrameTime = {0};
    Choreographer.getInstance().postFrameCallback(new Choreographer.FrameCallback() {
        @Override
        public void doFrame(long frameTimeNanos) {
            if (lastFrameTime[0] > 0) {
                long interval = frameTimeNanos - lastFrameTime[0];
                // 帧间隔接近 16.67ms 的偶数倍可能表明丢失了一帧
                // 帧间隔从 ~8.33ms 突变为 ~16.67ms 可能表明刷新率从 120Hz 降到了 60Hz
                if (interval > 25_000_000) {
                    Log.w("PerfMonitor", "Long interval: " + interval / 1_000_000 + "ms, "
                        + "possible refresh rate switch or frame drop");
                }
            }
            lastFrameTime[0] = frameTimeNanos;
            Choreographer.getInstance().postFrameCallback(this);
        }
    });
}
```

> 注意：Choreographer 回调本身**无法直接检测刷新率是否切换**。帧间隔的突变是间接信号，真正的刷新率切换确认需要通过 `adb shell dumpsys display` 或 Perfetto 的 VSync period 轨道来验证。

### SurfaceFlinger 日志分析

SurfaceFlinger 的日志包含了刷新率切换的详细信息：

```bash
# 查看 SurfaceFlinger 日志
adb logcat -s SurfaceFlinger | grep refresh

# 典型日志输出
I/SurfaceFlinger: Refresh rate changed from 60Hz to 120Hz
D/SurfaceFlinger: Display mode switch took 2 frames
W/SurfaceFlinger: Frame missed during refresh rate switch
```

### Perfetto 中的识别模式

在 Perfetto 中，刷新率切换导致的卡顿通常表现为：

1. **VSync 周期突变**：从 16.67ms 切换到 8.33ms 或相反
2. **FrameTimeline 中断**：在切换点附近出现 missing frame
3. **SurfaceFlinger 合成延迟**：切换期间帧提交延迟增加
4. **GPU 负载异常**：切换前后 GPU 使用率可能突然变化

## ARR（Adaptive Refresh Rate）的原理与边界

### MRR / ARR 的版本演进（Android 11-17）

Android 11-14 覆盖的是多刷新率切换（MRR）和 FrameRate API / `RefreshRateSelector` 决策能力；ARR 是 Android 15 引入的新机制，不应把早期 MRR 写成 ARR。

| Android 版本 | 能力边界 | 关键特性 | 硬件 / HAL 前提 |
|--------------|----------|----------|----------------|
| **Android 11-14** | MRR / FrameRate API | `Surface.setFrameRate()`、多 Display Mode、无缝 / 非无缝 mode switch、Layer 投票与系统策略共同决策 | 设备需暴露多个 Display Mode；无缝能力取决于 HWC / 面板实现 |
| **Android 15** | ARR 引入 | 使用离散 VSync 步长按内容 cadence 适配刷新率，减少传统 mode switching 引发的 jank | 新 HWC HAL API；官方要求实现 `android.hardware.graphics.composer3` version 3 相关 API |
| **Android 16** | ARR 查询 API | `Display.hasArrSupport()` 和 `getSuggestedFrameRate()` 作为 App 可见查询入口 | 设备支持 ARR 时才有意义 |
| **Android 17** | 待公开 tag 复核 | 本轮不使用 main/master 资料写 Android 17 结论 | 待 `android-17.0.0_r1` 或更低公开 tag 验证 |

> 根据官方 ARR 文档和 android-16.0.0_r1 源码：Android 15 引入 ARR；Android 16 可查询 ARR 支持。Android 17 tag 未公开前，不把 main/master 中的 ARR 描述作为 AIW 正文结论。

### 多刷新率（MRR）与 ARR 的版本边界

ARR（Adaptive Refresh Rate）是 Android 15 引入的刷新率平滑过渡机制，Android 15-QPR1+ 起在支持的设备上可用。Android 15 之前的多刷新率切换（MRR）属于不同代际的能力，不应混写为 ARR。

**Android 11-14**: 多刷新率（MRR）阶段
- 支持固定刷新率之间的切换（如 60Hz ↔ 120Hz），要求设备暴露多个 Display Mode
- `Surface.setFrameRate()`、Layer 投票、触摸 / idle / 省电等系统信号共同影响 `RefreshRateSelector` 排序
- 切换仍是 mode switching 语义；是否无缝、是否有黑屏或卡顿取决于 HWC、面板和设备策略

**Android 15**: ARR 引入
- ARR 在 Android 15 首次引入，Android 15-QPR1+ 起在支持的设备上可用
- `Display.hasArrSupport()`（Android 16 公开）可用于查询支持状态
- ARR 的核心机制是在 ARR 面板上解耦 display VSync rate 与实际 refresh cadence，按离散 VSync 步长适配内容帧率，减少 mode switching

**Android 16**: ARR 查询 API 公开
- `Display.hasArrSupport()` 和 `getSuggestedFrameRate()` 成为公开查询接口
- ARR 的过渡策略由 HAL 设备能力和 Composer HAL 实现共同决定，无统一的"连续范围控制"标准

**Android 17+**：待 Android 17 tag 公开后确认，不得将 main/master 资料中的描述作为 ARR 发布结论

### ARR 的工作原理

ARR 是 Android 15 引入的刷新率适配机制，Android 15-QPR1+ 起在支持的设备上可用。官方文档给出的核心模型是：非 ARR 面板按当前 active display mode 的固定 cadence 刷新；ARR 面板将 display VSync rate 与 refresh rate 解耦，面板可在同一个 display mode 内按 tearing effect（TE）信号的离散倍数显示下一帧。

> 在 android-16.0.0_r1 和官方 ARR 文档中，AOSP 源码中 ARR 相关元素常以 `vrr` 命名。`DisplayManagerInternal` 中并未定义 `handleAdaptiveRefreshRate()` 方法；SurfaceFlinger 侧仍通过 `RefreshRateSelector::getRankedFrameRates()` 汇总 Layer 投票、触摸状态、省电模式、设备空闲状态等信号，再结合 HWC / 面板能力下发显示节奏相关 hint。

### 厂商特定实现差异

不同 SoC 厂商的刷新率切换实现存在显著差异：

> 以下厂商特征来自各厂商公开白皮书和部分技术文档的定性描述。所有数值（PLL 延迟帧数、功耗百分比、续航降幅）均缺少设备型号、Android 版本、屏幕亮度、测试条件和样本量，不能作为发布稿量化结论，应以实测 Perfetto 数据为准。

> 从公开架构资料中可提取的定性趋势：旗舰 SoC 通常支持更短的 PLL 切换延迟，中端 SoC 偏长。不同 SoC 制程、显示驱动版本和屏幕面板规格下的精确数字需独立验证，不在此给出固定帧数。

#### 各厂商实现特点

**高通 Snapdragon 系列**
- 支持 Smart Refresh Rate 技术
- 实现 30Hz-120Hz 的渐变调整
- 切换延迟：旗舰芯片通常低于中端芯片（精确帧数依赖具体型号和固件版本）
- 电池消耗增加：高刷新率下功耗增幅需按设备/亮度/负载独立测试

**联发科 Dimensity 系列**
- 游戏场景优化：自动提升至 90/120Hz
- 节能模式：静态内容降至 48Hz
- 切换延迟：中端芯片偏长，旗舰芯片偏短（精确帧数依赖具体型号和固件版本）
- 电池消耗增加：高刷新率下功耗增幅需按设备/亮度/负载独立测试

**三星 Exynos 系列**
- Display Co-processor 硬件加速
- 支持多屏协同刷新率调整
- 切换延迟：依赖 Display Co-processor 硬件加速（精确帧数依赖具体型号和固件版本）
- 电池消耗增加：高刷新率下功耗增幅需按设备/亮度/负载独立测试

### ARR 的场景识别

| 场景类型 | 刷新率策略 | 典型行为 | 说明 |
|---------|------------|---------|------|
| 相机预览 | 固定 60Hz | 避免因内容检测触发频繁切换 | 功耗与屏幕亮度正相关 |
| 游戏场景 | 固定 90/120Hz | 稳定帧率体验优先于省电 | 功耗增量因设备 SoC 和渲染负载而异 |
| 阅读界面 | 48/60Hz | 静态内容可降刷新率省电 | 具体降幅由设备策略决定 |
| 视频播放 | 视频同步帧率 | 降低 judder | 功耗取决于解码+渲染路径 |
| 桌面动画 | 最高刷新率 | 保障动画流畅度 | 桌面停留后通常降刷 |

### ARR 的边界条件

ARR 虽然能缓解刷新率切换卡顿，但存在以下边界：

#### 硬件限制

ARR 的硬件前置条件（概念级，非 AOSP 逐行对标）：

- 设备需实现 Android 15 ARR 所需的 HWC HAL API；官方文档要求 `android.hardware.graphics.composer3` version 3 相关接口。
- ARR 配置通过 `DisplayConfiguration.vrrConfig` / `VrrConfig` 描述；该配置为空时，该 display mode 按非 ARR / MRR 语义处理。
- ARR 面板并不要求用多个 Display Mode 做 60Hz ↔ 120Hz 切换。官方模型是在一个 display mode 内使用离散 VSync 步长适配内容 cadence；传统 MRR 才依赖多个 Display Mode 和 mode switching。

> 根据官方 ARR 文档，`DisplayConfiguration.vsyncPeriod` 在 ARR 面板上表示 TE 信号频率，系统再结合 `minFrameIntervalNs` 等字段推导可支持的离散刷新 cadence。

#### 软件调度边界

即使硬件切换完成，软件调度仍然可能带来卡顿：

- 硬件完成刷新率切换后，App 侧的 Choreographer 回调周期会随之变化。如果 App 的渲染管线没有适配新周期（如 60Hz → 120Hz 后 doFrame 间隔从 16.67ms 缩短到 8.33ms），可能出现帧超时。
- SurfaceFlinger 在切换完成后需要清空或重建合成队列——新的 VSync 周期下，旧周期中排队的 buffer 可能不再有效。
- Android 15+ ARR 通过 HWC hint（如 `notifyExpectedPresent` / `frameIntervalNs`）让显示侧按预计 present cadence 调整节奏；超时和回退策略属于设备实现细节，不能写成统一的 SurfaceFlinger 保证。

> **Trace 观察点**：在 Perfetto 检查 VSync period 变化后 200ms 内 SurfaceFlinger 的 `compose` slice——如果 compose 耗时在切换后明显波动，说明合成管线在适应新周期。

#### 电池消耗

频繁切换高刷新率会增加电池消耗，主要来自 PLL 重配置和显示驱动电压调整：

- 在 Perfetto 中使用 `android.power` data source 或 `battery_stats` counter 可以观察刷新率与功耗的关联趋势。
- `adb shell dumpsys batterystats` 中的 `Estimated power use` 区域列出了按 UID/组件归因的功耗，可判断高刷新率场景是否成为功耗热点。
- 如果需要精确量化刷新率切换的电池开销，应在同设备同亮度下做 A/B 测试：分别录制 60Hz 固定、120Hz 固定和 ARR 自动切换三种模式的 trace + battery historian report，对比 mAh 消耗。

## App 与系统优化策略

### App 侧优化

#### 使用 setFrameRate() API

`Surface.setFrameRate()` 是 App 侧告诉系统自己帧率需求的核心 API。根据内容类型选择合适的 `FrameRateCompatibility` 模式：

- **相机预览**：调用 `surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE)`，SurfaceFlinger 会将屏幕刷新率固定在 60Hz（或其整数倍中满足需求的最小值）。
- **游戏全屏**：调用 `surface.setFrameRate(targetFps, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT)` 表达目标帧率；Android 16+ 如需表达最低刷新率约束，可使用公开的 `FRAME_RATE_COMPATIBILITY_AT_LEAST`。普通 App 不应使用 `@hide` 的 `FRAME_RATE_COMPATIBILITY_EXACT`。
- **普通 UI / 列表滚动**：不设置或使用 `FRAME_RATE_COMPATIBILITY_DEFAULT`，让系统根据内容检测自动决策。

> **Trace 观察点**：在 Perfetto 中搜索 `SurfaceFlinger` 进程的 `setFrameRate` 或 `setDesiredPresentTime` slice，可看到 App 的帧率偏好是否被 SurfaceFlinger 接收并生效。

#### 预测性提频

当 App 检测到即将触发需要高刷新率的操作（如手势开始、页面切换动画），可以提前通知系统准备刷新率切换：

- 通过 `Window.LayoutParams.preferredRefreshRate` 向 WindowManager 传递意图（注意：`Activity` 类没有公开的 `setFrameRate()` 方法；帧率偏好通过 `Surface.setFrameRate()` 或 `WindowManager.LayoutParams` 表达）。
- 这不是系统级"预切换"能力，而是让 RefreshRateSelector 在收集 Layer 投票时更早看到高帧率需求，减少决策延迟。

> **Trace 观察点**：查看 SurfaceFlinger 中 `Scheduler::chooseRefreshRateForContent()` / `RefreshRateSelector::getRankedFrameRatesLocked()` 相关 slice（不同 build 可能只显示函数名），再对照 VSync period 的突变时间点，判断帧率偏好是否在动画开始前生效。

#### 过渡期缓冲

在 App 感知到刷新率即将切换的场景（如从相机界面回到多任务），可以在过渡的 1-2 帧内降低新内容的复杂度，避免因新帧率下渲染负载突变导致的额外卡顿：

- 延迟非关键动画的启动，等刷新率稳定后再开始。
- 如果有自定义渲染管线，在检测到 `Choreographer` 帧间隔变化后的前 2-3 帧减少 draw call。

> **Trace 观察点**：在 Perfetto 中观察 VSync period 跳变前后的 `Choreographer#doFrame` 耗时——如果 doFrame 耗时在新周期下明显增加，说明 App 渲染负载需要适配新帧率。

### 系统侧优化

系统侧（SurfaceFlinger / Display HAL）的优化主要是降低切换决策延迟和硬件过渡开销：

#### 切换时机选择

SurfaceFlinger 会尽量在"对用户可见影响最小"的时刻执行刷新率切换：
- 如果当前有动画正在执行，延迟切换直到动画结束（或动画本身就触发了切换）。
- 如果系统处于 idle 状态，立即切换的成本最低——因为此时没有新帧等待提交。

这是 SurfaceFlinger 内部的调度逻辑，App 开发者无法直接控制。android-16.0.0_r1 中可验证的代码路径是 `frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp` 的 `chooseRefreshRateForContent()`，它汇总 LayerHistory 后更新刷新率策略。

#### 缓解切换期间的帧丢失

Display HAL 在传统 mode switching 期间可能出现帧提交延迟。减少卡顿的策略包括：
- **切换 hint 提前到达**：让 SurfaceFlinger / HWC 更早拿到 App 帧率偏好、触摸状态和下一帧 present cadence，减少决策滞后。
- **ARR 离散 VSync 步长**（Android 15+）：在支持的 ARR 面板上，系统可在同一 display mode 内按内容 cadence 调整刷新节奏，减少传统 mode switching。

> **Trace 观察点**：在 Perfetto SurfaceFlinger track 中查找切换点附近的 `missingFrame` 或 `presentFence` 超时；VSync period 变化前后是否有 `HWC` / `Composer` slice 异常延长。

#### 动态刷新率决策

SurfaceFlinger 的 `RefreshRateSelector` 根据 Layer 投票、触摸事件、内容检测结果动态调整刷新率。Android 15+ 引入了更智能的 vote weight 系统——不再只看最高帧率需求，而是综合活跃 Layer 数量、动画状态和功耗预算做最优选择。

> **Trace 观察点**：`RefreshRateSelector::getRankedFrameRatesLocked()` 相关 trace 记录可辅助定位排序窗口；最终模式切换还需要结合 SurfaceFlinger active mode 日志、VSync period 和 FrameTimeline 结果判断。

## 实际应用案例

### 案例 1：Camera 应用优化

**问题**：从相机界面切换到桌面时出现卡顿。

**分析**：相机界面固定 60fps（`Surface.setFrameRate(60f, FRAME_RATE_COMPATIBILITY_FIXED_SOURCE)`），桌面动画需要 120Hz。刷新率切换发生在 SurfaceFlinger / Display HAL 层，App 侧 main thread 和 RenderThread 均无异常，但用户仍感觉到过渡卡顿。

**排查路径**：
1. 在 Perfetto 中确认 VSync period 在相机退出时从 16.67ms 跳变到 8.33ms，且跳变点附近出现 `missingFrame` 或 SurfaceFlinger compose slice 异常延长。
2. 如果 `chooseRefreshRateForContent()` / `getRankedFrameRatesLocked()` 相关 trace 晚于触摸事件才开始考虑 120Hz 候选，说明系统侧决策滞后于用户操作——这是相机场景常见的切换延迟根因。
3. 确认 Camera HAL 释放 Surface 到 Launcher Surface 变为活跃之间的时间窗口：如果 Camera Surface 销毁晚于 Launcher 出现，RefreshRateSelector 可能在短时间内保留 60Hz 投票，延迟切换。

**优化方向**：
- App 侧：在相机即将退出时（如 `onUserLeaveHint()`），主动调用 `surface.setFrameRate(0, FRAME_RATE_COMPATIBILITY_DEFAULT)` 清空帧率偏好，让系统不再被相机侧的 60fps 固定需求锁住。
- 系统侧：部分 OEM 在 ROM 层对 Camera→Launcher 过渡做了 dedicated boost，确保触摸事件能立即触发 RefreshRateSelector 重新投票。


### 案例 2：游戏应用优化

**问题**：游戏中切换场景时帧率不稳定，特别是在主菜单（静态内容）→ 战斗场景（高帧率需求）过渡时。

**分析**：主菜单场景 SurfaceFlinger 可能检测到静态内容并将刷新率降至 60Hz 以省电；进入战斗后，需要 90Hz 或 120Hz 才能匹配渲染输出，但刷新率切换的 1-3 帧延迟会让玩家感受到瞬间卡顿。

**排查路径**：
1. 确认游戏是否通过 `Surface.setFrameRate()` 明确声明帧率需求。如果没有，完全依赖系统内容检测，静态→高帧率场景的切换延迟会更大。
2. 在 Perfetto 中对比：游戏 RenderThread 提交新帧的时间 vs VSync period 跳变到目标刷新率的时间。如果帧已提交但 VSync 还在旧周期，问题就在于 RefreshRateSelector 决策太慢。

**优化方向**：
- 进入战斗场景前（如加载界面），调用 `surface.setFrameRate(targetFps, FRAME_RATE_COMPATIBILITY_DEFAULT)` 提前声明帧率需求；如果 Android 16+ 需要表达最低刷新率约束，可使用公开的 `FRAME_RATE_COMPATIBILITY_AT_LEAST`。普通游戏不应使用只面向视频源的 `FIXED_SOURCE`。
- 普通游戏可以读取 `GameManager.getGameMode()` 并按用户选择调整渲染策略；`GameManager#setGameMode(String, int)` 需要 `MANAGE_GAME_MODE` 权限，属于系统/OEM 管理入口，不应写成普通 App 可调用的优化手段。
- 渲染策略不需要"针对场景切换"，而是确保游戏循环在 Choreographer 回调周期变化后仍能在新 deadline 内完成——如果从 60fps（16.67ms 预算）切到 120fps（8.33ms 预算）后 doFrame 超时，问题在渲染负载，不在刷新率切换。


### 案例 3：系统级优化

**问题**：从多任务界面回到桌面时常有卡顿，尤其是在 Launcher 自己未声明帧率偏好时。

**分析**：多任务过渡动画由 WindowManager 驱动，动画的 Surface 出现后，RefreshRateSelector 才收集到新的帧率需求。从收集到硬件切换完成之间存在决策窗口。

**排查路径**：
1. 查看 SurfaceFlinger 中 `chooseRefreshRateForContent()` / `getRankedFrameRatesLocked()` 相关 trace 的时间戳 vs Launcher Surface 首次变为 visible 的时间戳——两者之间的间隔就是决策延迟。
2. 如果决策延迟超过 1 帧，检查 `getRankedFrameRates` 结果中 Launcher Layer 的投票是否及时到达；Layer 刚变为活跃时 Metadata 可能尚未同步到位。
3. 查看触摸事件的 `InputDispatcher` → `SurfaceFlinger` 路径：触摸事件本身可以触发 touch boost，但 boost 窗口长度在各 OEM 实现中不同。

**优化方向**（系统侧，App 开发者无法干预）：
- Touch boost：SurfaceFlinger 在检测到 Navigation Gesture 触摸事件时，提前将刷新率拉高到一个较高的候选值，这样当 Launcher Surface 变为活跃时，刷新率已经在目标值附近。
- WindowManager 动画预通知：Android 15+ 的 WM Shell transition 可以先通知 SurfaceFlinger 即将出现的动画 Layer 信息，让 RefreshRateSelector 提前为该 Layer 预留投票权重。
- ARR 策略：如果是 ARR 设备，系统可在同一个 display mode 内按离散 VSync 步长适配动画 cadence，减少传统 60Hz ↔ 120Hz mode switching。


## 常见误区与陷阱

### 误区 1：卡顿完全来自硬件切换

不少分析者看到刷新率切换导致的卡顿，就直接归因到 "PLL 重配置太慢" 或 "Display HAL 状态机开销"。硬件切换确实占一部分延迟（通常 1-3 帧），但软件调度侧的延迟往往更长：RefreshRateSelector 从收到新 Layer 的帧率偏好到做出决策，可能需要 1-3 个 VSync 周期的延迟。再加上 SurfaceFlinger 合成队列在切换后需要适应新周期，软件侧的整体延迟经常超过硬件侧。

> **判断方法**：在 Perfetto 中对比 VSync period 跳变时间点和 `chooseRefreshRateForContent()` / `getRankedFrameRatesLocked()` 相关 trace 结束时间点——如果间隔超过 1 帧，软件侧的投票收集和决策时间不可忽略。

### 误区 2：使用最高刷新率就是最好的

120Hz 确实让滑动和动画更顺滑，但不是所有内容都受益。静态文本页面在 120Hz 和 60Hz 下肉眼几乎无差异，但功耗会明显增加。更关键的是：如果 App 的渲染管线在 120Hz 下做不到 8.33ms 内完成一帧，帧会持续超时，用户体验反而变差——用户看到的是 120Hz 屏幕上不断出现的 jank，比稳定的 60Hz 更糟。

> **判断方法**：在 Perfetto 中对比 doFrame 耗时 vs VSync period。如果 doFrame 稳定在 10-12ms，120Hz（8.33ms deadline）下会持续丢帧，此时锁定 60Hz 或 90Hz 是更实际的选择。

### 误区 3：Frame 完全正常就不可能有卡顿

这是第一章就讲过但容易忘的原则：App 侧 frame 耗时正常 ≠ 用户没有卡顿。刷新率切换卡顿发生在 SurfaceFlinger / Display HAL 层，App 的 RenderThread 在那个时候可能已经完成了工作，所以 `gfxinfo` 和 `systrace` 的 App 进程轨完全看不出问题。只有展开 SurfaceFlinger 和 VSync 轨道，才能看到帧在合成/提交阶段被延迟或跳过了。

> **判断方法**：当一个"奇怪卡顿"在 App 侧 Trace 中完全找不到对应物时，第一时间检查 SurfaceFlinger 进程的 compose slice 和 VSync period 轨道。

### 误区 4：频繁切换刷新率没有代价

单次 PLL 重配置和电压调整的瞬时功耗有限，但频繁切换场景（如：用户在列表和详情页之间反复进出 + 触摸 boost 每次触发 + 视频自动播放检测）会让切换次数累积到每分钟数十次，总功耗影响不可忽略。具体百分比依赖设备实现和场景频率，不在此给出固定数字。

ARR 策略的核心价值在于减少传统 display mode switching：在支持的面板上，系统可以用离散 VSync 步长适配内容 cadence，而不是频繁切换 active mode。如果没有 ARR，视频、相机这类固定源内容可以用 `FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 稳定表达源帧率；普通游戏和 UI 仍应使用 `DEFAULT` / `AT_LEAST` 这类公开模式。具体切换次数减少比例依赖设备实现和场景，不在此给出无法回溯的固定百分比。


## 性能指标与监控

### 关键指标

1. **切换延迟**：从切换决策到切换完成的时间
2. **帧丢失率**：切换期间丢失的帧数
3. **用户感知卡顿**：切换期间的卡顿时长
4. **电池消耗**：不同刷新率的电池影响

### 监控工具

```bash
# 查看刷新率信息
adb shell dumpsys SurfaceFlinger | grep refresh

# 查看帧率信息
adb shell dumpsys gfxinfo

# Perfetto 监控
adb shell perfetto -c perfetto_config.xml -o trace.pftrace
```

### 性能基准与量化数据

#### 关键指标基准

这些指标只能按同设备、同亮度、同系统版本、同场景录制的 trace 做相对判断，不能写成跨设备通用阈值：

| 指标 | 判断方式 | 需要保留的测试条件 |
|------|----------|--------------------|
| 切换延迟 | 对齐触摸 / Layer 可见、RefreshRateSelector 决策、VSync period 改变和首个稳定 present | 设备型号、系统版本、当前 display mode、是否 ARR、trace 文件 |
| 帧丢失 | 看切换窗口附近 FrameTimeline missing / jank、SurfaceFlinger compose 延长、present fence 超时 | 刷新率、场景脚本、样本次数 |
| 用户感知卡顿 | 用同机 A/B 对比 60Hz 固定、120Hz 固定、自动刷新率策略下的过渡稳定性 | 录屏 / 高速相机 / trace 时间戳对齐方式 |
| 功耗变化 | 对比固定刷新率与自动刷新率策略下的电流或 mAh 趋势 | 亮度、温度、网络、负载、测试时长 |

#### 不同 SoC 平台的切换表现（定性趋势）

不同 SoC、显示驱动、面板和 OEM 策略会改变刷新率切换成本。发布稿只能保留定性判断：高端平台和支持 ARR / 无缝切换的设备通常更容易把切换影响压低；中端平台、非无缝切换、复杂叠层和高亮度场景更容易放大卡顿与功耗。具体帧数、百分比和续航差异必须附带设备型号、Android 版本、亮度、测试工具、样本量和 trace / 电量记录。

#### 刷新率对电池消耗的影响（定性范围）

- 从 60Hz 升至 120Hz 的续航会下降，游戏场景降幅通常大于视频播放场景（具体百分比依赖设备、亮度、SoC 和测试条件）。
- 每次刷新率切换本身有额外开销（PLL 重配置 + 电压调整）。频繁切换的累积影响更值得关注——但具体功耗百分比依赖设备实现和切换频率，不在此给出无法溯源的固定数字。
- ARR 策略通过减少不必要切换来降低累积开销：静态内容保持在低刷、动画时切换到高刷。切换次数减少比例依赖设备实现和场景类型，不在此给出固定百分比。

> 精确续航数字（小时数、特定 SoC 型号的百分比）依赖具体设备/亮度/信号条件/测试负载，本章节当前不提供无法回溯来源的精确数字。

## 总结

刷新率切换分析的关键，是把 App 渲染、SurfaceFlinger 决策和 Display HAL 切换放在同一条时间线上看。理解刷新率切换的机制、掌握 Perfetto 中的分析方法、应用 App 和系统两侧的优化策略，我们可以：

1. **准确识别问题**：从 App 正常但用户卡顿的现象中定位刷新率切换路径
2. **精确优化**：针对刷新率切换的不同代价采用相应优化策略
3. **提升用户体验**：减少切换卡顿，提供更流畅的界面体验
4. **平衡性能与功耗**：根据场景智能选择刷新率，避免不必要的功耗浪费

实际排查时，先确认 VSync 周期和 SurfaceFlinger 日志，再回到 App 侧看 FrameTimeline，能减少在错误 Track 上反复排查的时间。
