---
title: "卡顿的定义与分类"
chapter: "7.1"
status: ready-for-review
applicable_versions: "Android 4.1 (API 16) - Android 16 (API 36)"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTimeline/JankInfo.h"
  - type: official
    path: "developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "developer.android.com/reference/android/view/FrameMetrics"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_Android卡顿监测的方方面面.md"
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md"
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md"
tags: [jank, smoothness, FrameTimeline, Choreographer, 掉帧, 渲染性能]
related_chapters: ["2.1", "2.3", "2.4", "2.5", "7.2", "7.3"]
---

# 卡顿的定义与分类

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Jank 的标准定义：帧未在预期 VSync 周期内完成（60Hz=16.67ms / 90Hz=11.11ms / 120Hz=8.33ms）
- 🔹 Google 的 Jank 分类：App Jank vs SF Jank vs Display Jank
- 🔹 FrameTimeline 与 JankType 的对应关系（Android 12+）
- 🔹 掉帧率（Janky Frame Rate）、连续掉帧（Frozen Frame）的区别
- 🔹 用户感知与技术指标的映射：多少 ms 延迟人能感知到

### 扩展（可选深入）

- 🔸 各厂商对 Jank 定义的差异（如华为的标准 vs Google 的标准）
- 🔸 Perfetto FrameTimeline 中 Jank 类型的详细解读

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要搞清楚"卡顿"的定义

在 Perfetto 中打开一段 Trace，你会在 Expected Timeline 和 Actual Timeline 之间看到不对齐的帧——有些帧的实际渲染时间比预期的长，系统把这些帧标记成了红色或黄色。这些颜色不是装饰，而是系统在告诉你：这一帧出了问题。但"出了问题"具体是什么问题？是 App 渲染太慢？是 SurfaceFlinger 合成太慢？还是屏幕显示出了延迟？

如果我们对"卡顿"只有一个模糊的感觉——"滑动不够流畅"、"动画有卡顿感"——那优化就只能靠试。明确卡顿的定义和分类，是系统性优化流畅性的起点。它决定了我们用什么指标衡量问题、用什么工具定位问题、以及优化后怎么验证效果。读完本节，你应该能在 Perfetto 中准确识别每一帧的状态（正常/卡顿/掉帧），并知道该去哪个 Track 找原因。

## Jank 的标准定义：帧没有如期到达

Android 系统的渲染管线是围绕 VSync 信号构建的。在 60Hz 屏幕上，VSync 信号每 16.67ms 到来一次；在 120Hz 屏幕上，这个间隔缩短到 8.33ms。每一个 VSync 周期，系统预期 App 能渲染出一帧新内容、SurfaceFlinger 能完成合成、最终屏幕能显示这一帧。

**Jank 的标准定义是：某一帧没有在预期的 VSync 周期内完成渲染和上屏。**

这里的"预期"非常关键。系统不是简单地看"这一帧渲染花了多长时间"，而是看"这一帧实际被呈现（present）的时间，是否与调度器（Scheduler）预测的呈现时间一致"。如果实际呈现时间晚于预期，那就是 Jank。

打个比方：VSync 就像一列准点运行的地铁。每一帧内容就像一个乘客，需要在对应的班次上车。如果乘客（帧）没赶上自己那班地铁（VSync），就得等下一班。这个"没赶上"就是 Jank——它导致画面更新的节奏被打乱，用户感知到不连贯。

### 不同刷新率下的帧预算

屏幕刷新率决定了每一帧的"预算时间"——系统必须在这么长时间内完成从 App 渲染到屏幕显示的全过程：

| 刷新率 | VSync 周期 | 帧预算 |
|--------|-----------|--------|
| 60Hz | 16.67ms | 16.67ms |
| 90Hz | 11.11ms | 11.11ms |
| 120Hz | 8.33ms | 8.33ms |

刷新率越高，留给每一帧的时间窗口越窄。在 120Hz 设备上，一帧只有 8.33ms——这意味着 App 的主线程渲染（measure/layout/draw）加上 RenderThread 的 GPU 执行，再加上 SurfaceFlinger 的合成，全部加起来必须在 8.33ms 内完成。任何环节超时，都会导致 Jank。

[已验证: 官方文档, developer.android.com/develop/ui/views/layout/swing-animations]
[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md]

### 一个关键区分：FPS ≠ 流畅度

很多人用 FPS（Frames Per Second，每秒帧数）来衡量流畅度，但这其实是一个容易误导的指标。FPS 衡量的是一秒内总共渲染了多少帧，但它**不反映帧的时间分布是否均匀**。

举个极端的例子：一秒内渲染了 50 帧。如果这 50 帧是均匀分布的（每 20ms 一帧），用户看到的是稳定的 50fps 体验，虽然不是最流畅，但不会觉得"卡"。但如果前 200ms 只渲染了 1 帧，后 800ms 突然渲染了 49 帧，FPS 同样是 50，但用户会感受到明显的卡顿——因为那 200ms 的空白期打破了视觉惯性。

腾讯音乐技术团队在分析中特别指出了这个误区：**帧率不能直接反映是否卡顿**。稳定在 40fps 的体验比在 60fps 和 30fps 之间来回跳变的体验好得多。这就是为什么 Google 在 Jank 的定义中不是看"平均帧率"，而是看"每一帧有没有准时到达"——它关注的是节奏的稳定性，而不是总产量。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]

## Google 的 Jank 分类体系

从 Android 12 开始，SurfaceFlinger 内部引入了 **FrameTimeline** 模块，它负责追踪每一帧从 App 渲染到最终上屏的完整生命周期，并判断 Jank 的责任归属。FrameTimeline 将 Jank 分为几个明确的类型，让我们不仅能知道"有没有卡顿"，还能知道"卡顿是谁的责任"。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/FrameTimeline/JankInfo.h]

### App Jank（AppDeadlineMissed）

这是最常见的 Jank 类型。当 App 侧的渲染工作（主线程的 measure/layout/draw + RenderThread 的 GPU 执行）超过了系统分配给这一帧的截止时间（deadline），就会产生 App Jank。

在 Perfetto 中，你可以在 App 的 Expected Timeline 和 Actual Timeline 之间看到不对齐——Actual Timeline 的帧结束时间超出了 Expected Timeline 的截止线。FrameTimeline 会将这类 Jank 标记为 **AppDeadlineMissed**。

导致 App Jank 的典型原因：
- 主线程在 draw 阶段做了耗时操作（复杂布局、大量自定义绘制）
- RenderThread 等待 GPU 完成超时（过度绘制、复杂 shader）
- 主线程被其他消息阻塞（Binder 调用、IO 操作、锁等待）

在 Perfetto 中的 Track 名称是 `Choreographer#doFrame`（主线程侧）和 `RenderThread`（渲染线程侧），对应 Perfetto 中的 Expected Timeline / Actual Timeline Slice。

[已验证: 官方文档, source.android.com/docs/core/graphics/frame-timeline]

### SF Jank（SurfaceFlingerCpuDeadlineMissed）

SurfaceFlinger 负责将各个 App 的图层合成为最终的画面。如果 SurfaceFlinger 的主线程在合成阶段超过了它的 deadline（即 VSYNC-SF 到来后没有在规定时间内完成合成），就会产生 SF Jank。

SF Jank 的典型原因包括：
- 图层过多，HWC（Hardware Composer）无法全部处理，回退到 GPU 合成
- Device State 变更（分辨率切换、屏幕旋转）期间合成逻辑被打乱
- SurfaceFlinger 主线程被其他耗时操作阻塞

在 Perfetto 中，SF Jank 体现在 SurfaceFlinger 进程的 Expected Timeline 和 Actual Timeline 之间的不对齐。FrameTimeline 会将其标记为 **SurfaceFlingerCpuDeadlineMissed**，明确告诉我们问题不在 App 侧，而在系统合成侧。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp]

### Display HAL Jank

这是比较少见但确实存在的一类 Jank。SurfaceFlinger 已经按时完成了合成工作，把帧交给了 Display HAL（显示硬件抽象层），但 Display HAL 没有在预期的 VSync 周期内完成上屏——帧被延迟到了下一个 VSync 才显示出来。

这种情况通常与硬件驱动或 SoC 平台的显示子系统实现有关，App 开发者基本无法控制。在 Perfetto 中，这类 Jank 在 SurfaceFlinger 的 Actual Timeline 中表现为"SurfaceFlinger 侧的工作按时完成了，但帧的最终 present 时间比预期晚了一个 VSync"。

### Dropped Frame（掉帧）

掉帧和 Jank 虽然都表现为"帧没有按时呈现"，但它们的机制不同。Jank 是"帧渲染太慢，没赶上截止时间"；掉帧是"帧直接被丢弃了"。

掉帧有两种场景：
1. **SurfaceFlinger 侧掉帧**：SurfaceFlinger 在合成时发现有一个更新的帧已经到了，就跳过当前帧直接用更新的帧。这对用户来说通常是不可感知的——因为显示的是更新的内容。
2. **App 侧掉帧**：App 的 UI 线程没能及时将最新的状态更新推送到 RenderThread。RenderThread 只好用旧的状态绘制了一帧，导致用户看到的内容"卡"在了旧状态。

[已验证: 官方文档, perfetto.dev/docs/data-sources/frametimeline]

### Buffer Stuffing

Buffer Stuffing 是一种特殊状态：App 持续不断地向 SurfaceFlinger 发送新帧，比屏幕能显示的还快。结果是缓冲区队列被"塞满"了——App 在不断地渲染新帧，但中间的帧可能永远不会被显示。这不会直接导致 Jank（帧率可能看起来很高），但会导致**输入延迟增加**——用户的操作要等好几帧之后才能在屏幕上看到反馈。这种情况在游戏等持续渲染场景中比较常见。

### Jank 类型在 Perfetto 中的颜色编码

FrameTimeline 在 Perfetto 中使用颜色来区分不同的帧状态：

| 颜色 | JankType | 含义 |
|------|----------|------|
| 绿色 | None | 正常帧，没有 Jank |
| 浅绿色 | High Latency State | 帧率稳定但帧呈现延迟较高 |
| 红色 | AppDeadlineMissed | App 侧导致的 Jank |
| 黄色 | SurfaceFlinger Jank | SurfaceFlinger 侧导致的 Jank |
| 蓝色 | Dropped Frame | 帧被丢弃 |

[已验证: 官方文档, perfetto.dev/docs/data-sources/frametimeline]

## FrameTimeline：Android 12+ 的 Jank 追踪核心

理解了 Jank 的分类之后，我们需要了解 FrameTimeline 是怎么工作的，因为它是我们分析 Jank 的主要工具。

### Expected Timeline vs Actual Timeline

FrameTimeline 在 Perfetto 中引入了两条关键的 Track：

- **Expected Timeline**：系统预期这一帧的生命周期——从 Choreographer 唤醒开始，到预期被呈现（present）到屏幕上为止。这条线代表的是"计划"。
- **Actual Timeline**：这一帧实际的生命周期——从 App 实际开始渲染，到实际被呈现到屏幕上。这条线代表的是"现实"。

当 Expected 和 Actual 对齐时，帧没有问题；当 Actual 超出了 Expected 的截止时间，就产生了 Jank。

### FrameTimeline 的工作原理

FrameTimeline 的核心思路是"端到端追踪"：它给每一帧分配一个唯一的标识（Token），这个 Token 从 App 的 Choreographer 发出，经过 RenderThread、BufferQueue、SurfaceFlinger，一直到达 Display HAL。每个环节在处理这一帧时都会记录时间戳，FrameTimeline 通过 Token 把这些时间戳串联起来，就能看到一帧在整条渲染管线中的完整旅程。

```
[Choreographer 唤醒] → [App 渲染] → [GPU 执行] → [提交 BufferQueue] 
    → [SurfaceFlinger 合成] → [Display HAL 上屏] → [Present]
```

每个环节都有自己的 deadline，任何一个环节超时都可能导致最终的 Jank。FrameTimeline 的价值在于：它能精确定位是哪个环节超时了，而不是让开发者去猜。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/FrameTimeline/]

### 在 Perfetto 中的具体位置

在 Perfetto UI 中，FrameTimeline 的数据展示在以下位置：

1. **App 进程下**：你会看到 `Expected Timeline` 和 `Actual Timeline` 两个 Track，分别对应系统预期和实际的帧时间线。点击某一个帧的 Slice，可以在详情面板中看到 `Jank Type` 字段。
2. **SurfaceFlinger 进程下**：同样有 Expected/Actual Timeline，展示 SurfaceFlinger 侧的帧处理情况。

在 Android 12 之前的设备上，没有 FrameTimeline 数据。此时只能通过观察主线程的 `Choreographer#doFrame` Slice 和 RenderThread 的 `DrawFrame` Slice 来手动判断帧是否超时。

[已验证: 官方文档, perfetto.dev/docs/data-sources/frametimeline]

## 掉帧率、连续掉帧与卡顿率

在实际的性能优化工作中，我们不会只看某一帧是否 Jank，而是看一段时间的统计指标。以下是几个关键指标：

### 掉帧率（Janky Frame Rate）

掉帧率 = Janky 帧数 / 总帧数 × 100%。它衡量的是"有多大比例的帧出了问题"。Google 推荐的 AndroidX JankStats 库会统计这个指标。一般的优化目标是将掉帧率控制在 5% 以下。

### 连续掉帧（Frozen Frame）

Frozen Frame（也称为 Big Jank）指的是渲染时间超过 700ms 的帧。在这 700ms 内，用户看到的是完全冻结的画面，没有任何更新。这种体验非常糟糕——用户可能会以为 App 崩溃了。

Google 对帧的严重程度有一个分级：

| 指标 | 时间范围 | 用户感知 |
|------|---------|---------|
| 正常帧 | < 1 个 VSync 周期 | 流畅 |
| 慢帧（Slow Frame） | 16ms - 700ms | 轻微卡顿感 |
| 冻结帧（Frozen Frame） | 700ms - 5s | 画面冻结，用户焦虑 |
| ANR | > 5s | 系统弹窗 |

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

### Stutter（卡顿率）

Stutter 是性能测试工具 PerfDog 提出的一个指标，它不只是数有多少帧 Jank，而是把所有 Jank 帧的"延迟时间"加起来，除以测试总时长。Stutter = ∑JankTime / TotalTime。这个指标的优点是它能反映卡顿的"严重程度"——一次 50ms 的 Jank 和一次 200ms 的 Jank 在掉帧率中都算 1 帧，但对用户体验的影响完全不同，Stutter 会把它们区分开。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]

### Google Jank vs PerfDog Jank

值得一提的是，不同工具对 Jank 的判定标准不同：

**Google 的 Jank 判定**：基于 VSync 对齐——如果连续一次 VSync 没有新画面刷新，就认为是一次 Jank。这个标准比较严格。

**PerfDog 的 Jank 判定**：需要同时满足两个条件：
1. 当前帧耗时 > 前三帧平均耗时的 2 倍
2. 当前帧耗时 > 两帧电影帧耗时（约 84ms）

PerfDog 的 BigJank 则要求：
1. 当前帧耗时 > 前三帧平均耗时的 2 倍
2. 当前帧耗时 > 三帧电影帧耗时（约 125ms）

Google 的标准从系统底层出发，关注 VSync 对齐；PerfDog 的标准从用户感知出发，关注帧耗时突变。两者各有优势，在不同场景下选择合适的标准来衡量。

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]

## 用户感知与技术指标的映射

了解了各种技术指标之后，一个关键问题是：这些数字对用户意味着什么？用户不会看 Perfetto Trace，他们只会说"这个列表滑起来不顺手"或"这个动画一卡一卡的"。

### 视觉惯性与帧率稳定性

用户对流畅度的感知不仅取决于帧率的高低，更取决于帧率的**稳定性**。这涉及到一个概念叫"视觉惯性"——当用户持续看到 60fps 的画面时，潜意识里预期下一帧也是同样的节奏。如果突然有一帧延迟了，打破了这种惯性，用户就会感知到"卡了一下"。

这就是为什么稳定的 40fps 可能比在 60fps 和 30fps 之间来回跳变的体验更好——稳定低帧率让用户建立了新的视觉惯性，而不稳定的帧率不断打破惯性。

电影帧率（24fps，约每帧 41.67ms）是一个参考下限。低于这个帧率，人眼基本能感知到画面的不连续性。但电影有自然运动模糊来"掩盖"低帧率，而 UI 动画没有这种效果，所以 UI 对帧率的要求更高。

### 延迟感知的阈值

研究表明，用户对延迟的感知有几个关键阈值：

- **< 100ms**：用户感觉系统是"即时响应"的。Jakob Nielsen 的研究表明，100ms 是用户感觉"系统在直接响应我的操作"的极限。在这个范围内，用户认为操作和结果是直接关联的。
- **100ms - 300ms**：用户能感知到延迟，但仍然觉得在"可接受"范围内。此时用户能感觉到操作和结果之间有轻微的间隔。
- **300ms - 1s**：用户明显感到等待，注意力开始分散。
- **> 1s**：用户的思维连续性被打断，开始觉得系统"慢"。
- **> 5s**：用户失去耐心，系统弹出 ANR 对话框。

对于 Android 的 UI 渲染来说，一个 VSync 周期（60Hz 下 16.67ms）的延迟通常不会让用户直接感知到——因为单帧的微小波动被前后帧的连续性"平滑"掉了。但如果连续多帧都 Jank，累积的延迟很快就会超过 100ms 的感知阈值。比如连续 3 个 VSync 周期没有新画面（约 50ms 的空白），在滑动场景下用户就能感知到"不跟手"。

[已验证: 官方文档, developer.android.com/topic/performance/vitals]
[引用: https://www.nngroup.com/articles/response-times-3-important-limits/]

### 不同场景下的感知差异

用户对卡顿的感知还取决于交互场景：

- **连续滑动**（列表、页面滚动）：这是用户对卡顿最敏感的场景。滑动时用户的视线在跟随手指移动内容，任何帧率的波动都能被感知到。推荐目标：稳定达到屏幕刷新率。
- **动画过渡**（页面切换、展开/收起）：对卡顿的敏感度略低于连续滑动，因为动画的方向和节奏是预设的。但突然的"跳帧"仍然很明显。
- **静态界面**：完全不对帧率有要求——画面不动就没有 Jank。

## [自动发现] JankStats：Google 官方的 Jank 监测库

来源：developer.android.com/develop/ui/views/performance/jankstats

AndroidX JankStats 库是 Google 提供的用于在运行时监测 Jank 的工具。它基于 `FrameMetrics` API（Android 7.0+）构建，在 Android 12+ 设备上还能获取 `frameOverrunNanos`（帧超时了多少纳秒），提供更精确的 Jank 判定。

JankStats 的工作原理：
1. 通过 `OnFrameListener` 监听每一帧的渲染时间
2. 将帧耗时与预设阈值比较（默认是帧是否超过 VSync 周期）
3. 如果判定为 Jank，记录当前的状态信息（Activity 名称、当前 UI 状态等）
4. 将 Jank 报告回调给开发者

开发者可以自定义 Jank 的判定阈值，也可以通过 `PerformanceMetricsState` 在 Jank 发生时附加上下文信息（比如"用户正在滑动首页列表"），方便后续分析。

[已验证: 官方文档, developer.android.com/develop/ui/views/performance/jankstats]

## 与其他章节的关系

- **2.1 渲染架构全景**：Jank 发生在渲染管线的各个环节，理解渲染架构是定位 Jank 的基础
- **2.3 VSync 机制**：Jank 的定义依赖于 VSync 周期，理解 VSync 才能理解 Jank 的"截止时间"
- **2.4 Choreographer 与渲染流水线**：App Jank 的核心检测点在 Choreographer 的 doFrame 流程中
- **2.5 MainThread 与 RenderThread 协作**：App Jank 可以进一步细分为主线程 Jank 和 RenderThread Jank
- **7.2 卡顿原因体系**：本节定义了"什么是卡顿"，7.2 则详细分析"卡顿是怎么产生的"
- **7.3 卡顿分析方法论**：基于本节的 Jank 分类，7.3 提供系统化的分析方法

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp` — FrameTimeline 核心逻辑
  - `frameworks/native/services/surfaceflinger/FrameTimeline/JankInfo.h` — JankType 枚举定义
  - `frameworks/base/core/java/android/view/Choreographer.java` — VSync 驱动渲染
  - `frameworks/base/core/java/android/view/FrameMetrics.java` — 帧性能指标
- 官方文档：
  - [FrameTimeline | Perfetto Docs](https://perfetto.dev/docs/data-sources/frametimeline)
  - [JankStats | Android Developers](https://developer.android.com/develop/ui/views/performance/jankstats)
  - [FrameMetrics API | Android Developers](https://developer.android.com/reference/android/view/FrameMetrics)
  - [Response Time Limits | Nielsen Norman Group](https://www.nngroup.com/articles/response-times-3-important-limits/)
- 博客与文章：
  - [来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]（腾讯音乐：Android 深入卡顿分析与实践）
  - [来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android卡顿监测的方方面面.md]（鸿洋：Android 卡顿监测的方方面面）
  - [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md]（高爷：Android Perfetto 系列 6 - 为什么是 120Hz）
  - [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md]（高爷：Android Perfetto 系列 5 - Choreographer 渲染流程）
