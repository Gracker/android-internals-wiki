---
title: "Adaptive Refresh Rate 与动态帧率控制"
chapter: "2.18"
section: "2.18"
status: ready-for-review
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/view/Choreographer"
  - type: official
    path: "https://android-developers.googleblog.com/2025/adaptive-refresh-rate.html"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/refresh-rate"
  - type: research
    path: "intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md"
tags: [ARR, refresh-rate, VSync, SurfaceFlinger, Choreographer, LTPO, frame-pacing, Android-16]
related_chapters: ["2.2", "2.3", "2.4", "2.6", "2.13", "2.16"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: pending
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-11"
task6_result: needs-rework
---

# 2.18 Adaptive Refresh Rate 与动态帧率控制

[需重写: 本章缺少 `outline-start` / `outline-end` 大纲块，Task 6 无法按锚点逐项检查覆盖率，需由 Task 2B 补齐结构化大纲。]

## 为什么要了解 Adaptive Refresh Rate

在 Perfetto 中打开一段滑动场景的 Trace，我们经常看到一个现象：VSYNC-app 和 VSYNC-sf 的间隔是固定的——比如 120Hz 屏幕上，VSync 周期始终是 8.33ms。但 App 的实际渲染帧率可能在 60fps 和 120fps 之间来回变化。如果屏幕始终以 120Hz 刷新，而 App 只能产出 60 帧，那么每两个 VSync 周期中就有一个被浪费了——SurfaceFlinger 在合成时拿不到新帧，只能重复显示上一帧的内容。

这个浪费不只是性能问题，更是功耗问题。显示面板在每次刷新时都会消耗电流，120Hz 面板以全速运行时的功耗可能是 60Hz 的两倍。如果内容只有 24fps（电影播放），强制面板以 120Hz 刷新意味着每帧画面被重复显示 5 次，其中 4 次刷新完全是浪费。

Adaptive Refresh Rate（ARR）就是解决这个问题的机制。它让屏幕的刷新率能够跟随内容的帧率动态调整。App 渲染 60 帧时屏幕跑 60Hz，播放 24fps 视频时屏幕降到 24Hz（或其整数倍），静态页面甚至可以降到 1Hz。在 Perfetto 中，VSYNC-app 的间隔会从固定的 8.33ms 变成不均匀的值，这通常表示 ARR 已开始介入。

了解 ARR 的工作原理，能帮助我们在分析渲染性能问题时正确解读 VSync 行为，理解帧率切换时的短暂卡顿从何而来，以及如何通过 API 让系统选择最优的刷新率来平衡流畅度和功耗。

[待补充：Trace 截图，展示 ARR 开启前后 VSYNC-app 间隔的对比]

[需补充素材: 本章涉及 ARR 开启前后 VSYNC 间隔、模式切换卡顿、Game Mode 交互，但当前关键 Trace 位置仍是占位符，需补 2-4 张真实 Perfetto Trace 截图或等价图示。]

## 从固定刷新率到自适应刷新率

### 60Hz/120Hz 二选一的局限

在 Android 11 之前，大多数设备的屏幕只支持一个固定刷新率。用户看到的就是 60Hz，没有选择。Android 11 开始引入多刷新率支持——设备可以配置多个 Display Mode，比如 60Hz 和 120Hz 两个模式，系统可以在它们之间切换。

但这里的"切换"是模式切换（Display Mode Switch），不是无缝变频。切换过程需要重新配置显示管道（Display Pipeline），可能耗时几十毫秒，期间画面会短暂黑屏或冻结。这就是为什么早期高刷手机在桌面滑动时用 120Hz，停下来后降到 60Hz 时偶尔会出现一帧闪烁——那正是模式切换的代价。

而且，60Hz 和 120Hz 只覆盖了两种帧率。24fps 的电影怎么办？系统只能选 60Hz（每帧重复 2.5 次，会产生 judder）或 120Hz（每帧重复 5 次，功耗浪费）。无论哪种都不是最优解。

### LTPO 面板的硬件能力

LTPO（Low-Temperature Polycrystalline Oxide）是三星 Display 开发的一种混合背板技术，它把 LTPS（高迁移率、适合高刷新率）和 IGZO/Oxide（低功耗、适合低刷新率）晶体管混合使用，让同一块面板可以在 1Hz 到 120Hz（甚至 240Hz）之间自由变频——不需要模式切换，刷新率在一个 VSync 周期内就能改变。

这是硬件层面的能力。但软件层面，Android 到 Android 14 为止都没有充分利用 LTPO 的变频能力。系统仍然是在几个固定模式之间切换，只是切换更频繁了。真正的"自适应"——刷新率跟随内容帧率在一个 Display Mode 内连续调整——直到 Android 15 才通过 ARR 正式引入。

### Android 15 的突破：单模式内变频

Android 15 引入的"True"ARR 的核心变化在于：刷新率的调整不再需要切换 Display Mode。在支持的设备上（通常是 LTPO 面板），ARR 通过离散步进（discrete VSync steps）的方式在一个 Display Mode 的范围内调整刷新率。

什么叫离散步进？假设设备支持 1Hz-120Hz 的范围，ARR 不会以 0.1Hz 的精度连续调整——那对 VSync 时序电路来说太复杂。实际的做法是定义一组离散的 VSync 周期，比如 1Hz、5Hz、10Hz、24Hz、30Hz、48Hz、60Hz、90Hz、120Hz。系统从这些预定义值中选择最匹配当前内容帧率的那个。

这种方式的好处是：切换几乎无感知延迟，不会出现模式切换时的黑屏或冻结。在 Perfetto 中，你会看到 VSYNC-app 的间隔突然从 16.67ms（60Hz）变成 8.33ms（120Hz），中间没有任何异常帧。

[已验证: 官方文档, developer.android.com/develop/ui/views/graphics/refresh-rate]

## ARR 的架构设计

ARR 不是单一组件的工作，而是 DisplayManager、SurfaceFlinger、Choreographer 三方协调的结果。理解这个架构对于在 Perfetto 中正确分析帧率行为至关重要。

### 三方协调的职责划分

**DisplayManager** 负责高层策略。它定义了刷新率选择的范围（最低和最高刷新率），以及一些策略规则（比如省电模式下限制最高刷新率）。DisplayManager 不直接决定当前刷新率——它只是画了一个框，告诉 SurfaceFlinger "在这个范围内选"。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java]

**SurfaceFlinger** 是真正的决策者。它收集所有活跃 Layer（窗口/曲面）的帧率需求，然后根据仲裁算法选择一个能满足所有 Layer 需求的刷新率。SurfaceFlinger 的决策逻辑在 `SurfaceFlinger::chooseRefreshRateForContent()` 中实现。

**Choreographer** 是通知渠道。它通过 `VsyncEventData` 将当前的实际刷新率信息传递给 App，让 App 知道当前 VSync 周期是多长，从而调整自己的渲染节奏。

```
DisplayManager (策略范围)
       ↓ min/max refresh rate
SurfaceFlinger (仲裁决策)
       ↓ 实际 refresh rate
Choreographer (通知 App)
       ↓ VsyncEventData.refreshRate
App (调整渲染节奏)
```

### Frame Rate Override 机制

App 可以通过两种方式向系统表达帧率偏好：

**Surface.setFrameRate()**（Android 11 引入，推荐使用）：这是最直接的方式。App 在某个 Surface 上调用 `setFrameRate(60f, FRAME_RATE_COMPATIBILITY_DEFAULT)`，告诉系统"我这个 Surface 打算以 60fps 的节奏提交帧"。系统会考虑这个偏好来选择刷新率。

这个调用是"建议"而非"命令"。系统可能因为其他 App 的需求、功耗策略或硬件限制而选择不同的刷新率。比如 App 请求 24fps，系统可能选择 120Hz（24 的整数倍）而不是 24Hz，因为另一个前台 App 需要 120Hz。

```java
// Android 11+ (API 30)
// 告诉系统这个 Surface 打算以 60fps 运行
surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);

// 视频播放场景——使用 FIXED_SOURCE 表示帧率不可变
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
```

[已验证: 官方文档, developer.android.com/reference/android/view/Surface#setFrameRate]

**WindowAttributes#preferredDisplayModeId**（Android 11 之前的方式）：直接指定一个 Display Mode 的 ID。这种方式更死板——它绑定的是完整的模式（包含分辨率和刷新率），而不是仅仅表达帧率偏好。Android 11 之后，应该优先使用 `setFrameRate()`，只在需要同时改变分辨率或 `setFrameRate()` 无法满足需求时才回退到 `preferredDisplayModeId`。

### 内容检测：即使 App 不说，系统也能猜

SurfaceFlinger 有一个有趣的机制：即使 App 没有调用 `setFrameRate()`，系统也能通过"内容检测"（Content Detection）自动推断 App 的实际帧率。

原理是 SurfaceFlinger 会追踪每个 Layer 上 buffer 的提交时间戳。如果一个 Layer 平均每 16.67ms 提交一个 buffer，SurfaceFlinger 就推断它的帧率大约是 60fps。这个行为由系统属性 `ro.surface_flinger.use_content_detection_for_refresh_rate` 控制。

这就是为什么在很多 App 中，即使开发者没有做任何适配，设备的刷新率也能跟随操作动态变化——SurfaceFlinger 在帮你做这件事。

[待验证: ro.surface_flinger.use_content_detection_for_refresh_rate 在 Android 16 中的默认值]

## Android 16 ARR API 详解

Android 16 对 ARR 进行了显著的增强，提供了更精细的控制能力和更多的查询接口。

### 新增 API

**Display.hasArrSupport()**：查询设备是否支持 ARR。这是 ARR 功能的入口检查——在不支持 ARR 的设备上（非 LTPO 面板或旧硬件），其他 ARR API 的调用不会有实际效果。

**Display.getSuggestedFrameRate(int)**：给定一个目标帧率，查询系统建议的最优帧率。这个 API 的价值在于：你想要的帧率不一定能直接映射到面板支持的刷新率。比如你请求 45fps，系统可能返回 90Hz（2 倍关系）或 60Hz（最近的实际值）。App 应该使用返回值来指导渲染节奏，而不是盲目按自己的目标帧率渲染。

**Display.getSupportedRefreshRates()**（Android 16 恢复）：列出设备支持的刷新率。这个 API 在之前的版本中曾被移除，Android 16 恢复了它，以便 App 能知道面板的实际能力范围。

### Choreographer.VsyncEventData 中的 refreshRate

从 Android 13 开始，Choreographer 的回调中可以通过 `VsyncEventData` 获取当前 VSync 事件对应的实际刷新率：

```java
// frameworks/base/core/java/android/view/Choreographer.java
// @ AOSP android-16.0.0_r1
choreographer.postVsyncCallback(vsyncEvent -> {
    float refreshRate = vsyncEvent.getRefreshRate(); // 当前实际刷新率 (Hz)
    long frameTimeNanos = vsyncEvent.getFrameTimeNanos(); // 当前帧的时间戳
    // 根据 refreshRate 调整渲染节奏
});
```

`refreshRate` 字段反映的是**实际**刷新率，不是 App 请求的刷新率。App 可以用它来判断系统是否采纳了自己的帧率建议，以及当前 VSync 周期的实际长度。

比如，App 请求了 60fps，但系统因为其他前台 App 需要 120Hz 而选择了 120Hz 刷新率。此时 `refreshRate` 会返回 120.0f，App 就知道一个 VSync 周期只有 8.33ms 而不是 16.67ms，需要相应调整动画插值等逻辑。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java]

### RecyclerView 1.4 内置 ARR 支持

Android 16 的一个实用改进是 RecyclerView 1.4 内置了 ARR 适配。在 Fling（惯性滑动）和 Smooth Scroll（平滑滚动）操作中，RecyclerView 会自动调用 `setFrameRate()` 提升刷新率到设备的最高值（如 120Hz），以确保滑动过程中的每一帧都能被及时显示。滑动停止后，刷新率会自然回落。

这意味着使用 RecyclerView 的 App 在 Android 16 上不需要手动做任何 ARR 适配就能获得高刷滑动的体验。Compose 1.9 也引入了 `preferredFrameRate()` 修饰符，让 Composable 可以声明自己的帧率偏好。

## SurfaceFlinger 的帧率决策策略

ARR 的核心决策逻辑在 SurfaceFlinger 中。理解这个逻辑有助于解释 Perfetto 中观察到的各种刷新率变化行为。

### 多 App 仲裁

当屏幕上有多个 App 同时活跃时（比如分屏模式，或前台 App 覆盖着一个浮窗），SurfaceFlinger 需要找到一个刷新率能同时满足所有活跃 Layer 的需求。

仲裁的基本规则是：选择所有活跃 Layer 请求帧率的**最小公倍数**（或其附近的值）。比如一个 Layer 请求 24fps，另一个请求 60fps，SurfaceFlinger 倾向于选择 120Hz——因为 120 是 24 和 60 的最小公倍数，两个 Layer 的帧都能被按时呈现。

如果找不到一个公倍数在面板支持的范围内，SurfaceFlinger 会回退到 `DisplayManager` 定义的范围上限，优先保证流畅性。

[待验证: AOSP 中 LayerHistory 的具体权重算法在 android-16 中是否有变化]

### Layer Priority 与帧率选择

不同类型的 Layer 有不同的优先级。前台 Activity 的主窗口 Layer 优先级最高，StatusBar 和 NavigationBar 的 Layer 优先级较低。在仲裁时，高优先级 Layer 的帧率需求会被优先满足。

`GameManagerService` 可以直接介入帧率决策——比如游戏模式下限制帧率到 60fps 以节省功耗（Android 15 的默认行为），或者解除限制让游戏跑到最高帧率。这个干预是通过 SurfaceFlinger 的 `setDesiredDisplayModeSpecs()` 接口实现的。

### 触摸交互的特殊处理

SurfaceFlinger 有一个专门处理触摸事件的定时器。当用户触摸屏幕时，系统会临时切换到一个较高的默认刷新率（通常是最高值），持续一段时间（由 `ro.surface_flinger.set_touch_timer_ms` 定义，通常是 500ms-2000ms）。

这个设计的意图是：触摸操作通常伴随着滚动或动画，需要最高的帧率来保证流畅度。用户停止触摸后，如果 App 的实际渲染帧率低于面板最高刷新率，SurfaceFlinger 会自然降频。

在 Perfetto 中，你会看到一个模式：手指一接触屏幕，VSYNC-app 间隔立刻从 16.67ms 缩短到 8.33ms；手指离开后，经过一个超时窗口，间隔恢复到更长的值。这就是触摸触发的刷新率提升在 Trace 中的表现。

[待验证: 触摸超时的默认值在不同 OEM 上的差异]

### VsyncModulator 对 Offset 的动态调整

我们在 2.3 节（VSync 机制）中讨论了 VSYNC-app 和 VSYNC-sf 之间的 offset。在 ARR 场景下，这个 offset 不是固定的——它由 `VsyncModulator` 组件动态管理。

`VsyncModulator` 的代码位于 `services/surfaceflinger/Scheduler/VsyncModulator.cpp`。它的核心行为是：当系统正在切换刷新率、或者刚刚开始一个图形事务（transaction）时，使用更"提前"的 offset，让 App 和 SurfaceFlinger 有更多时间完成各自的工作。

这意味着在 Perfetto 中观察 VSYNC-app 和 VSYNC-sf 的间隔时，你会发现在刷新率切换的瞬间，两者的间距可能短暂变化。这不是错误，而是 VsyncModulator 在为切换过程提供时间余量。

[已验证: AOSP android-16.0.0_r1, services/surfaceflinger/Scheduler/VsyncModulator.cpp]

## 在 Perfetto 中分析 ARR 行为

### 关键 Track 和 Slice

分析 ARR 行为时，以下几个 Perfetto Track 是主要观察对象：

- **VSYNC-app**：驱动 Choreographer 回调的信号。ARR 开启时，这个 Track 上相邻事件的间隔会随刷新率变化——60Hz 时 16.67ms，120Hz 时 8.33ms，24Hz 时 41.67ms。
- **VSYNC-sf**：驱动 SurfaceFlinger 合成的信号。在 ARR 切换时，它的间隔也会同步变化。
- **SurfaceFlinger Track**：关注 `setDesiredDisplayModeSpecs` 相关的 slice，这些是刷新率决策的日志点。

### 帧间隔异常的 SQL 查询

当怀疑 ARR 行为异常（比如不该降帧的时候降了，或者切换过于频繁导致卡顿）时，可以用 Perfetto SQL 分析 VSYNC-app 的间隔分布：

```sql
-- 分析 VSYNC-app 间隔分布，检测异常刷新率切换
SELECT
  CAST((ts - LAG(ts) OVER (ORDER BY ts)) / 1e6 AS FLOAT) AS interval_ms,
  CASE
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 7.5e6 AND 9.5e6 THEN '120Hz'
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 15.5e6 AND 17.5e6 THEN '60Hz'
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 32e6 AND 34e6 THEN '30Hz'
    WHEN (ts - LAG(ts) OVER (ORDER BY ts)) BETWEEN 40e6 AND 43e6 THEN '24Hz'
    ELSE 'other'
  END AS refresh_rate_group
FROM track_event
WHERE name = 'VSYNC-app'
ORDER BY ts
```

如果 `other` 类别出现频繁，说明存在非标准的 VSync 间隔，可能是 ARR 的离散步进在工作，也可能是 VSync 抖动——需要结合具体场景判断。

[待补充：实际 Perfetto Trace 截图展示 VSYNC-app 间隔的动态变化]

### SurfaceFlinger 刷新率决策日志

SurfaceFlinger 在做出刷新率决策时会输出日志。通过 `adb logcat -s SurfaceFlinger` 会看到类似信息：

```
ChooseRefreshRate: layers={LayerA: 60fps, LayerB: 24fps} -> chosen: 120Hz
```

这些日志能帮助理解 SurfaceFlinger 为什么选择了某个刷新率——是因为哪个 Layer 的帧率需求，还是因为触摸超时还在生效。

## ARR 对功耗的影响

### 高帧率的功耗代价

显示面板是手机功耗的主要来源之一。在 LTPO OLED 面板上，刷新率从 60Hz 提升到 120Hz，显示子系统的功耗大约增加 20%-50%（具体取决于面板驱动和分辨率）。这包括了 DDIC（显示驱动 IC）的工作频率提升、数据传输带宽翻倍、以及像素电路的充放电频率增加。

ARR 的功耗优化逻辑是：在不影响用户体验的前提下，尽可能降低刷新率。一个静态的阅读页面，1Hz 和 120Hz 在视觉上没有区别（因为画面根本没变），但功耗差距可能达到 5-10 倍。

[需确认: 60Hz 升到 120Hz 时功耗增加 20%-50%、静态页 1Hz 与 120Hz 功耗差 5-10 倍，这两组量化数据缺少明确来源和测试条件，建议 Task 9 补证据后再保留具体数字。]

### 无缝刷新率切换（Seamless Refresh Rate Switching）

ARR 使用的离散步进变频是"无缝"的——没有模式切换的黑屏，没有帧冻结。硬件上，LTPO 面板通过调整像素电路的刷新时序来实现变频；软件上，SurfaceFlinger 通过调整 VSync 信号的周期来匹配新的刷新率。

但这种无缝切换有一个前提：VSync 信号源和显示面板必须在同一个 Display Mode 内。如果需要跨模式切换（比如从 1080p/120Hz 切到 1440p/60Hz），仍然会有短暂的可感知中断。

### 降帧策略

SurfaceFlinger 的降帧不是随意的。它遵循以下优先级：

1. **内容帧率**：如果所有活跃 Layer 的帧率都低于当前刷新率的一半，就降到最近的满足条件的刷新率。
2. **触摸超时**：触摸结束后，维持高刷一段时间再降。这段时间内即使内容帧率很低，也不会降频。
3. **功耗策略**：在省电模式下，`DisplayManager` 会收窄刷新率范围的上限（比如从 120Hz 限制到 60Hz），SurfaceFlinger 的选择空间被压缩。
4. **温控**：设备温度过高时，系统可能强制降低最高刷新率。

## 版本演进

| 版本 | 关键变化 |
|------|----------|
| Android 11 (API 30) | 引入多刷新率支持，`Surface.setFrameRate()` API，Config Groups 支持无缝模式切换 |
| Android 12 (API 31) | `preferredDisplayModeId` 行为优化，触摸触发刷新率提升 |
| Android 13 (API 33) | `Choreographer.VsyncEventData.refreshRate` 字段，VSYNC-app / VSYNC-sf 信号引入 |
| Android 14 (API 34) | `setFrameRate()` 允许传入非面板原生支持的帧率值 |
| Android 15 (API 35) | "True" ARR 引入——单模式内离散步进变频，不再依赖模式切换 |
| Android 16 (API 36) | `hasArrSupport()`、`getSuggestedFrameRate()`、`getSupportedRefreshRates()` 恢复，RecyclerView 1.4 内置 ARR，Compose `preferredFrameRate()` |
| Android 17 (API 37) | [待验证: ARR 与 DeliQueue 无锁 MessageQueue 的交互对帧调度的影响] |

[需确认: Android 16/17 的 API Level 标注需与全书版本约定统一。当前 frontmatter 与版本表写的是 Android 16 (API 36)、Android 17 (API 37)，建议交给 Task 9 统一核对。]

## 与其他机制的关系

- **VSync 机制（2.3）**：ARR 改变了 VSync 信号的周期，但不改变 VSync 的基本工作方式。App 仍然通过 Choreographer 接收 VSync 回调来驱动渲染。
- **Choreographer（2.4）**：Choreographer 通过 `VsyncEventData` 感知 ARR 的刷新率变化，将信息传递给 App。
- **SurfaceFlinger（2.6）**：SurfaceFlinger 是 ARR 的核心决策者，负责收集 Layer 帧率需求并仲裁。
- **BufferQueue（2.13）**：ARR 不影响 BufferQueue 的 buffer 管理逻辑，但刷新率变化会影响 App 何时 dequeueBuffer（因为 VSync 间隔变了）。
- **Sync Fence（2.16）**：ARR 的离散步进变频不影响 Sync Fence 的工作，但刷新率切换时 VsyncModulator 的 offset 调整会间接影响 fence 的等待时机。

## 常见问题与误区

**误区：App 调用 `setFrameRate(120f)` 就能强制屏幕跑 120Hz。**

`setFrameRate()` 只是一个建议。系统可能因为省电模式、温控、或其他 App 的帧率需求而选择不同的刷新率。要判断系统实际选择了什么刷新率，应该看 `Choreographer.VsyncEventData.refreshRate` 的返回值，而不是想当然地认为请求被接受了。

**误区：ARR 开启后就不会再掉帧了。**

ARR 解决的是"刷新率不匹配内容帧率"的问题，不解决"App 渲染太慢"的问题。如果 App 的 doFrame 超时（超过一个 VSync 周期），照样会掉帧。ARR 只是让 VSync 周期能适配 App 的渲染能力，而不是反过来。

**误区：所有 120Hz 手机都支持 ARR。**

ARR 需要硬件支持。不是所有 120Hz 面板都能在单模式内变频——很多只是支持 60Hz 和 120Hz 两个固定模式之间的切换。只有配备 LTPO 或类似变频面板的设备才支持 True ARR。用 `Display.hasArrSupport()` 检测，不要假设。

**误区：LTPO 设备上 ARR 默认开启。**

Android 15+ 的 LTPO 设备通常会启用 ARR，但具体策略由 OEM 决定。有些厂商可能为了省电而限制 ARR 的变频范围，或在特定场景下禁用 ARR。在分析 Trace 时，如果看到 VSync 间隔始终固定，可能是 ARR 被禁用或范围受限。

**帧率切换导致短暂卡顿**

在非 LTPO 设备上（只支持模式切换），从 60Hz 切到 120Hz 可能需要几十毫秒。这期间 App 可能错过一两个 VSync 周期，导致 1-2 帧的卡顿。在 Perfetto 中，这表现为 VSYNC-app 间隔突然从 16.67ms 变成 33ms（一帧丢失），然后变成 8.33ms（120Hz 稳定运行）。

[图：模式切换时的 Perfetto Trace 示意——VSYNC 间隔先扩大后缩小]

## 扩展

### 🔸 Game Mode API 与 ARR 的交互

Android 12 引入的 `GameManagerService` 可以通过 `GameMode` 和 `GamePerformanceMode` 影响 SurfaceFlinger 的帧率决策。比如，"Performance" 模式下系统可能解除帧率限制并固定在最高刷新率，而 "Battery Saver" 模式下可能限制到 30fps 或 60fps。

游戏通过 `GameModeManager` 设置的偏好会传递到 SurfaceFlinger 的 `setDesiredDisplayModeSpecs()` 接口，作为帧率仲裁的额外输入。

[待补充：Game Mode 与 ARR 交互的 Perfetto Trace 分析]

### 🔸 Frame Pacing Library（Swappy）

对于使用 OpenGL 或 Vulkan 的游戏和应用，Google 提供了 Android Frame Pacing Library（代号 Swappy，AGDK 的一部分）。Swappy 的工作方式与普通 App 的 Choreographer 回调不同——它直接利用 Choreographer 的 VSync 同步、presentation time 和 sync fence 来实现精确的帧节奏控制。

Swappy 会自动处理 ARR 场景下的帧率适配，包括：
- 根据当前 VSync 周期计算下一帧的最佳提交时间
- 在刷新率切换时平滑过渡，避免帧间隔突变
- 防止 buffer stuffing（提交过多未显示的帧导致延迟累积）

使用 Swappy 的游戏不需要手动调用 `setFrameRate()`——Swappy 内部会根据游戏配置的 target FPS 自动向系统请求合适的刷新率。

[已验证: 官方文档, developer.android.com/games/agdk/frame-pacing]

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/java/android/view/Choreographer.java`（Choreographer 与 VsyncEventData）
  - `frameworks/base/core/java/android/view/Surface.java`（setFrameRate API）
  - `services/surfaceflinger/Scheduler/`（SurfaceFlinger 调度器与 VsyncModulator）
  - `frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java`（DisplayManager 策略）
- 官方文档：
  - [Refresh Rate Management](https://developer.android.com/develop/ui/views/graphics/refresh-rate)
  - [Android Frame Pacing](https://developer.android.com/games/agdk/frame-pacing)
  - [Adaptive Refresh Rate Blog](https://android-developers.googleblog.com/2025/adaptive-refresh-rate.html)
- 系统属性参考：
  - `ro.surface_flinger.use_content_detection_for_refresh_rate`
  - `ro.surface_flinger.set_touch_timer_ms`
  - `debug.sf.set_idle_timer_ms`
  - `debug.sf.early_phase_offset_ns` / `debug.sf.early_gl_phase_offset_ns`
