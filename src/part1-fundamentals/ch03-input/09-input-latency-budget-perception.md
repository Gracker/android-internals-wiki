---

title: "端到端输入延迟预算与感知阈值"
chapter: "3.9"
section: "3.9"
status: "finalized"
drafted_date: "2026-05-16"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1 + Perfetto docs 2026-05"
confidence: medium
sources:
  - type: official
  - type: official
  - type: official
  - type: official
  - type: official
  - type: aosp
  - type: aosp
  - type: aosp
  - type: aosp
  - type: aosp
  - type: paper
  - type: research
    path: "DeepResearch/2026-05-11-hci-perception-input-latency-analysis.md"
tags: [input-latency, hci, touch, jank, perception]
related_chapters: ["3.2", "3.4", "7.9", "13.8", "15.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/官方文档"
task6_state: "reviewed"
task6_result: pass-light-edit
last_task6_at: "2026-07-01T09:07:00+08:00"
task6_review_notes: "2026-07-01 Task6 revisiting re-review (idle-audit auto-fix 后): pass-light-edit。L1/L2 无新增问题；Task9 idle-audit source version anchoring（android-16→17）后写作复审通过。自动晋升 finalized。"
reviewed_date: "2026-07-01"
reviewed_by: "openclaw-task6"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
task9_result: "auto-fixed"
task9_reviewed_date: "2026-07-01"
task9_reviewed_by: "openclaw-task9"
task2b_state: "fixed"
last_task9_at: "2026-05-17T15:29:34+08:00"
last_task9_review_log: "logs/deep-review/2026-05-17-15-deep-review.md"
task9_review_notes: "2026-05-17 15 Task9 re-review: pass-tech-review。Perfetto android.input stdlib schema 已修正；AOSP Resampler/GameMode/RefreshRatePolicy 边界复核通过。预算表与 HCI 阈值 P2 既有 suggestions 保留。自动晋升 finalized。"
last_task9_autofix_at: "2026-07-01"
last_task9_audit: "2026-07-01"
last_task9_audit_log: "logs/deep-review/2026-07-01-05-audit.md"
last_task9_audit_result: "auto-fixed-source-version-audit"
last_task9_audit_notes: "idle audit: updated AOSP verification anchors from android-15/16 to android-17.0.0_r1 after Gitiles verification; no queue item."
p0: 0
p1: 0
p2: 2
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-01
last_task6_audit: "2026-07-01"
---

# 3.9 端到端输入延迟预算与感知阈值

输入延迟不能只按 InputDispatcher 或主线程耗时判断。用户感知到的是从手指动作到屏幕反馈之间的端到端距离，这段距离同时受触控硬件、输入分发、应用处理、渲染提交、SurfaceFlinger 合成和显示刷新影响。

本节把 HCI 感知阈值、Android 输入路径和 Perfetto 指标放在同一个口径下，给后续排查留一张预算表。3.2 节已经讲触摸响应路径，3.4 节已经讲重采样和预测输入；这里补齐“多少算慢、慢在哪一段、怎样和用户体感对上”这三个问题。

[已验证: source.android.com/docs/core/interaction/input; developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features]

## 端到端输入延迟的拆分口径

Android 官方输入文档给出的路径是：物理设备产生信号，Linux 驱动转成 evdev 事件，EventHub 读取事件，InputReader 解码成 Android 输入事件，再交给 InputDispatcher 分发到目标窗口。应用收到事件后，才进入 ViewRootImpl、View 树分发和渲染提交阶段。

对性能分析来说，这条路径要拆成两类时间：

- **输入到应用消费**：从触控样本进入内核，到应用主线程开始处理 `MotionEvent`。这部分受硬件采样率、EventHub 读取、InputReader 坐标转换、InputDispatcher 队列和 Binder/socket 传输影响。
- **应用消费到画面呈现**：从应用处理输入，到新画面被 SurfaceFlinger 合成并在显示设备上呈现。这里受 Choreographer 回调、主线程工作、RenderThread、BufferQueue、SurfaceFlinger 合成和 VSync 节奏影响。

一条滑动出现“跟手性差”时，先把输入交付和画面呈现拆开看。输入阶段只决定事件何时交给应用；用户看到的反馈还要等应用提交新 buffer，并且等到对应 present 时刻。

[已验证: 官方文档, source.android.com/docs/core/interaction/input] [已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync]

## 一张预算表：从触摸到上屏

下面这张表用于估算端到端延迟，不用于给所有设备设固定 SLO。触摸 IC、显示面板、刷新率、内核调度、OEM 提频策略都会改变数值，表里的范围只适合作为排查时的分段参照。

| 阶段 | 典型责任边界 | 常见预算 | 主要观测点 | 超预算后的判断 |
| --- | --- | ---: | --- | --- |
| 触控采样与驱动上报 | 触控 IC、固件、Linux input driver | 4-16 ms | 硬件采样率、`/dev/input/event*` 时间戳 | 高采样率只能缩短样本间隔，不能保证画面更早呈现 |
| EventHub / InputReader | evdev 读取、设备映射、坐标转换 | 1-5 ms | input 线程 slice、InputReader 日志 | 这里异常通常和设备配置、驱动事件风暴或线程调度有关 |
| InputDispatcher | 命中窗口、队列、派发到 InputChannel | 1-8 ms | `android_input_event_dispatch`、`iq/oq/wq` 队列 | 队列积压时先看目标窗口是否阻塞 ACK |
| 应用主线程消费 | ViewRootImpl、ViewGroup、业务回调 | 1-16 ms | 主线程 `deliverInputEvent`、`doFrame`、业务 slice | UI 线程阻塞会把输入延迟和帧延迟同时抬高 |
| 渲染提交 | Choreographer、RenderThread、GPU 提交 | 1 个刷新周期内 | FrameTimeline app frame、RenderThread | 渲染在 deadline 内完成才有机会赶上本帧 |
| SurfaceFlinger 合成与 present | BufferQueue、HWC/GPU composition、显示刷新 | 1-2 个刷新周期 | FrameTimeline SF frame、present time | late present 会让帧率看起来平稳，但输入反馈滞后一帧以上 |

[已验证: Perfetto docs, perfetto.dev/docs/data-sources/frametimeline]

## HCI 阈值和 Android 工程指标的换算

HCI 研究中的延迟阈值来自受控实验，Android 工程指标来自真实设备和生产负载。两类数据不能直接互换，但可以放在同一张表里建立分层判断。

| 体感区间 | HCI / 产品含义 | Android 侧工程解释 | 建议指标口径 |
| --- | --- | --- | --- |
| < 20 ms | 用户很难稳定区分延迟差异，手写笔、绘图等场景仍可能受影响 | 需要高采样率、低处理耗时、低延迟渲染同时成立 | 用实验室设备测 click-to-photon 或 stylus-to-photon |
| 20-50 ms | 多数普通 UI 仍可接受，精细拖动会开始变钝 | 端到端通常只容纳 2-3 个 120Hz 刷新周期 | 看 P50/P90，不只看均值 |
| 50-100 ms | 拖动、游戏、手写会明显感到滞后 | 常见原因是主线程阻塞、渲染错过 present、BufferQueue 积压 | 以场景级 P90 / P95 作为治理线 |
| > 100 ms | 交互反馈迟钝，用户会停止动作或重复点击 | 输入、应用、渲染任一阶段长尾都可能把总耗时推过阈值 | 必须拆分输入阶段和呈现阶段 |
| 秒级 | 已经不是体感延迟，而是无响应或卡死 | InputDispatcher / ANR 保护开始介入 | 交给 ANR、Watchdog、主线程堆栈分析 |

HCI 研究报告过 2 ms 级别的触摸延迟差异可被感知，也有研究把当前移动设备触摸延迟放在约 50-200 ms 的范围。这个结论适合提醒工程团队：ANR 的 5 秒阈值只说明系统容错边界，和“用户觉得跟手”不是一个指标。

[引用: ACM MobileHCI 2016 "Software-reduced touchscreen latency"; J. Pratt et al., "User Perception of Touch Screen Latency"]

## InputReader 到应用消费的预算

输入事件进入 Android 后，InputReader 和 InputDispatcher 的目标是把事件可靠送到焦点窗口，而不是主动决定用户看到什么。官方文档里的路径足够清楚：EventHub 读取 evdev，InputReader 按设备类型和配置文件解码，InputDispatcher 把事件转发给合适窗口。

这段预算要重点看三件事：

- **样本是否稳定进入系统**：触控硬件采样不稳、驱动上报抖动、设备配置错误，会让后续所有平滑策略都只能补救视觉轨迹，不能补回原始样本质量。
- **InputDispatcher 是否排队**：如果目标窗口没有及时 ACK，dispatcher 的 outbound / wait queue 会增长，后续输入会被拖住。这里和 ANR 有关系，但几十毫秒的输入长尾不能等同于 ANR。
- **应用主线程何时拿到事件**：`ViewRootImpl` 收到输入后，事件还要经过输入阶段、动画阶段、遍历阶段。主线程上一段同步 I/O、锁等待或重布局都会推迟消费时间。

输入重采样属于这一段的特殊处理。AOSP `InputConsumer.cpp` 和 `Resampler.cpp` 中定义了 `RESAMPLE_LATENCY = 5ms`、`RESAMPLE_MIN_DELTA = 2ms`、`RESAMPLE_MAX_PREDICTION = 8ms` 等参数，用插值或外推把触摸坐标贴近 VSync 时刻。它改善的是轨迹平滑和视觉贴合，不等于把端到端延迟减少 5 ms。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/input/InputConsumer.cpp] [已验证: AOSP android-17.0.0_r1, frameworks/native/libs/input/Resampler.cpp] [交叉引用: §3.4 输入延迟与预测输入技术]

## 应用渲染到上屏的预算

应用消费输入后，只有产生新画面并赶上 present，用户才会感到反馈。VSync 文档说明了显示管线的同步对象：应用渲染、SurfaceFlinger 合成、HWC present 都要围绕 VSync 节奏运行。应用错过一个节拍，端到端延迟就增加一个刷新周期。

FrameTimeline 对这段很有用。Perfetto 文档把 high latency state 标成浅绿色：帧率是平稳的，但帧呈现晚了，输入延迟增加。Buffer Stuffing 也是同类问题，应用不断提交新帧，队列里堆着尚未呈现的 buffer，每帧都可能至少晚一个 VSync。

排查时要把“做完”和“显示出来”分开：

- 主线程和 RenderThread 都在 deadline 内完成，只说明应用侧没有明显慢帧。
- SurfaceFlinger present 晚，用户仍会感觉输入反馈慢。
- BufferQueue 被塞满时，后续 dequeue 可能阻塞，应用看起来又会变成渲染慢。

[已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync] [已验证: Perfetto docs, perfetto.dev/docs/data-sources/frametimeline]

## Perfetto 中怎样关联输入事件和帧

Perfetto 的 `android.input` 标准库把 InputReader、InputDispatcher 和应用 ACK 之间的阶段整理成表。`android_input_events` 是输入延迟的主表，包含事件 ID、时间戳等核心字段。`android_input_event_dispatch` 作为补充表，提供窗口 ID（`window_id`）和 vsync 决策（`vsync_id`）等信息，但不包含 display、dispatch 开始与结束等字段——这些字段分布在 `android_input_event_motion` / `android_input_event_key` 等事件子表中。标准库还暴露 `total_latency_dur` 和 `end_to_end_latency_dur` 这类时间。

这几个指标的边界要分清：

- `total_latency_dur` 更接近 input dispatch 到 input ACK 的耗时，适合看窗口是否及时消费输入。
- `end_to_end_latency_dur` 关联到 frame present，适合看输入反馈是否被渲染和呈现阶段拉长。
- 没有关联帧的输入事件不能硬算“触摸到上屏”，只能作为输入分发样本分析。

这条规则能避免一个常见误判：看到 InputDispatcher 耗时很短，就判断用户不会感到延迟。输入阶段健康，只能说明事件交付及时；画面晚到仍然会形成可感知延迟。

[已验证: Perfetto stdlib docs, perfetto.dev/docs/analysis/stdlib-docs#android-input] [交叉引用: §13.8 Perfetto 输入延迟 SQL 深度分析]

## 刷新率改变预算，不自动解决延迟

刷新率决定的是显示节拍，也就是“晚一帧”的时间成本。60Hz 下一帧约 16.67 ms，90Hz 约 11.11 ms，120Hz 约 8.33 ms，144Hz 约 6.94 ms。高刷新率缩短了等待下一个 present 的时间，但不会让主线程同步任务、GPU 工作或 SurfaceFlinger 合成自动变短。

| 刷新率 | 单帧间隔 | 50 ms 内大约容纳的帧数 | 对输入延迟的影响 |
| --- | ---: | ---: | --- |
| 60Hz | 16.67 ms | 3 帧 | 错过一帧的体感成本高，输入反馈容易跨过 50 ms |
| 90Hz | 11.11 ms | 4-5 帧 | present 等待缩短，但应用长任务仍会主导延迟 |
| 120Hz | 8.33 ms | 6 帧 | 手写、拖动收益更明显，调度和功耗压力也更高 |
| 144Hz | 6.94 ms | 7 帧 | 适合游戏和低延迟渲染，稳定供帧比峰值刷新率更重要 |

如果业务只把刷新率拉高，却没有减少输入回调、布局、绘制、GPU 提交和队列积压，高刷只会把问题拆得更细，不会消除端到端长尾。

[已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync] [交叉引用: §2.18 Adaptive Refresh Rate 与动态帧率控制]

## 低延迟模式的验证方法

厂商游戏模式、触控增强、低延迟渲染通常会同时改动刷新率、触控采样率、CPU/GPU 频率和调度策略。标准 AOSP GameMode 主要管理 GameMode 状态、帧率策略和 Power HAL `Mode.GAME`，没有公开的“输入优先级提升”API。焦点窗口机制、`requestDisallowInterceptTouchEvent(true)`、游戏窗口的刷新率选择优先级，是公开框架里能确认的能力。

验证低延迟模式时，FPS 不是唯一指标。更稳的办法是抓两组同场景 Perfetto：

1. 固定刷新率、亮度、温控状态和操作脚本，分别记录普通模式与低延迟模式。
2. 对比 InputDispatcher dispatch / ACK、主线程 `deliverInputEvent`、FrameTimeline present、SurfaceFlinger 合成耗时。
3. 对比 P50、P90、P95，不只看某一次滑动的最小值。
4. 如果低延迟模式只改善 present 等待，结论应写成“渲染呈现延迟降低”；如果 InputDispatcher 队列也下降，才讨论输入分发侧收益。

厂商私有 HAL 或 Framework 修改没有公开源码时，只能标成 `[待验证]`。营销名词不能写成 AOSP 机制。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/app/GameManagerService.java / frameworks/base/services/core/java/com/android/server/wm/RefreshRatePolicy.java / frameworks/base/core/java/android/view/ViewGroup.java]

## 游戏、手写和普通 UI 的阈值差异

不同交互对延迟的容忍度不同。普通点击更关注“点了以后有没有反馈”，拖动和手写更关注轨迹是否贴着手指，游戏还会叠加判定窗口和操作节奏。

| 场景 | 用户最敏感的部分 | 建议关注指标 | 常见优化方向 |
| --- | --- | --- | --- |
| 普通点击 | 点击后首个视觉反馈 | click-to-display P90/P95 | 减少主线程同步任务，保证首帧反馈先出 |
| 列表拖动 | 手指位置和内容位移的差距 | input-to-present、步幅波动、FrameTimeline | 重采样、稳定刷新率、减少布局和绘制抖动 |
| 手写 / 绘图 | 笔尖和墨迹之间的距离 | stylus-to-photon、预测误差 | MotionPredictor、前缓冲渲染、低延迟画笔路径 |
| 游戏 | 操作到画面反馈和命中判定 | input-to-frame、P95、温控后长尾 | 高刷稳定供帧、GameMode、减少队列堆积 |

Android 的高级手写笔文档把低延迟拆成硬件和 OS 输入处理、应用处理、系统合成、硬件渲染几个部分，并推荐低延迟图形和运动预测来改善笔迹体验。这些技术适合对轨迹贴合敏感的场景，不适合作为所有 UI 的默认方案。

[已验证: 官方文档, developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features] [交叉引用: §7.9 感知流畅性：步幅波动与无掉帧卡顿]

## 常见误判

### 误判一：InputDispatcher 很快，端到端延迟就低

InputDispatcher 快，只说明输入事件较快交给目标窗口。应用消费、渲染提交、SurfaceFlinger present 仍可能让用户晚一帧或多帧看到反馈。

### 误判二：刷新率越高，触摸就一定越跟手

高刷新率缩短 present 节拍，触摸采样率提高缩短样本间隔。两者都不能替应用主线程、RenderThread 和 GPU 减少工作量。高刷下错过一帧的时间更短，但持续错过 deadline 时，用户仍会感到拖拽滞后。

### 误判三：ANR 阈值能代表输入体验

ANR 是系统容错机制，处理的是秒级无响应。输入体验通常在几十毫秒级发生变化，不能用 5 秒超时去评估跟手性。

### 误判四：低延迟模式一定改了输入系统

公开 AOSP 里没有通用的游戏输入优先级 API。低延迟模式可能只是提频、锁高刷、调整帧率选择、改变触控固件参数或启用厂商私有路径。没有 trace 和源码证据时，不要把效果归因到 InputDispatcher。

## 与其他章节的关系

- 3.2 节讲触摸响应路径，本节给路径加预算和体感阈值。
- 3.4 节讲重采样、MotionPredictor 和低延迟图形，本节解释这些技术放在端到端预算里的位置。
- 7.9 节讲感知流畅性，本节补输入到画面呈现之间的延迟口径。
- 13.8 节给 Perfetto SQL，这里定义指标边界。
- 15.3 节讲指标体系，本节把 click-to-display / input-to-present 纳入响应速度指标。

## 参考资料

- [已验证: 官方文档, source.android.com/docs/core/interaction/input]
- [已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync]
- [已验证: 官方文档, developer.android.com/develop/ui/views/touch-and-input/stylus-input/advanced-stylus-features]
- [已验证: Perfetto docs, perfetto.dev/docs/data-sources/frametimeline]
- [已验证: Perfetto stdlib docs, perfetto.dev/docs/analysis/stdlib-docs#android-input]
- [已验证: AOSP android-17.0.0_r1, frameworks/native/libs/input/InputConsumer.cpp]
- [已验证: AOSP android-17.0.0_r1, frameworks/native/libs/input/Resampler.cpp]
- [引用: https://dl.acm.org/doi/10.1145/2935334.2935381]
- [引用: https://www.researchgate.net/publication/221100500_User_Perception_of_Touch_Screen_Latency]
