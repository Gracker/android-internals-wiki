---
title: "响应速度原理"
chapter: "8.1"
section: "8.1"
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
reviewed_date: "2026-05-01"
reviewed_by: openclaw-task6
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
last_verified: "2026-03-30"
last_verified_against: "AOSP android-16.0.0_r1, 官方文档最新版本"
confidence: medium
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2a"
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://source.android.google.cn/docs/core/tests/debug/eval_perf"
  - type: cubox
    path: "Cubox/华为-交互流畅体验设计-2025-02-18.md"
  - type: cubox
    path: "Cubox/评估性能 - Android 开源项目 --- Evaluating Performance - ...-2024-01-10.md"
  - type: cubox
    path: "Cubox/Android Vitals - Tap Response Time 👉 - DEV Community-2022-01-17.md"
  - type: web
    path: "https://web.dev/articles/rail"
tags: [responsiveness, TTID, TTFD, RAIL, input-latency, perceived-performance]
related_chapters: ["2.3", "2.4", "3.1", "7.1", "8.2", "9.1", "15.3", "15.5", "15.9"]
review_notes: "2026-04-30 task9 deep-review: needs-rework。P0 3，P1 1，P2 2。"
task6_state: reviewed
task6_result: pass-light-edit
task2b_state: fixed
task2b_result: fixed
task6_reviewed_date: "2026-05-01"
task6_spotcheck_date: "2026-05-15"
task6_spotcheck_result: pass-light-edit
last_task6_audit: "2026-05-22"
review_round: 1
status: ready-for-review
pipeline_stage: task6_pending
task9_result: needs-rework
task9_state: reviewed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-23"
last_task9_at: "2026-05-23T09:31:49+08:00"
task9_review_notes: "2026-05-23 Task9 闲时抽检：needs-rework。P0 0 / P1 1 / P2 1；TTID/TTFD Android 12 归因需修正，RAIL Load 大纲阈值需同步。详见 logs/deep-review/2026-05-23-09-audit.md。"
last_task9_audit: "2026-05-23"
last_task9_review_log: "logs/deep-review/2026-05-23-09-audit.md"
---

# 响应速度原理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 响应速度的定义：用户操作到视觉反馈的完整延迟
- 🔹 RAIL 模型在 Android 场景的应用：Response < 100ms, Animation 命中 VSync Deadline, Idle, Load < 1000ms
- 🔹 系统级响应路径：Input → App 处理 → 渲染 → 上屏
- 🔹 Android Vitals 中的响应速度指标
- 🔹 感知速度 vs 实际速度：骨架屏、占位图、过渡动画的视觉优化

### 扩展（可选深入）

- 🔸 Interaction-to-Next-Paint（INP）概念在 Android 的对应物
- 🔸 Google Play Console 中的 App 性能数据解读

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解响应速度

我们在 Perfetto 中看到的那些间隙——从 Input 事件到达 App，到画面最终显示在屏幕上——这段"空白"就是响应速度要解决的问题。

响应速度之所以重要，是因为它直接影响用户对设备质量的第一印象。Google 在 AOSP 官方文档的《Evaluating Performance》中明确指出：**Touch latency is immediately noticeable and significantly contributes to the perception of a device.** [已验证: 官方文档, source.android.google.cn/docs/core/tests/debug/eval_perf]

用户也许无法区分 500ms 和 600ms 的启动时间，但对触摸响应的延迟极其敏感。一个设备启动再快，如果触摸之后画面纹丝不动，用户会觉得这台机器"卡"。这就是为什么 Google 认为，在性能优先级排序中，**UI 渲染管线的流畅性高于一切**——包括应用启动速度。

从用户体验治理角度看，响应速度和流畅性属于同一类问题。如果把 `7.1` 里提出的“广义流畅性”概念展开来看，响应慢就是同一条体验路径上的另一种失效形式：掉帧是“画面没按节奏到达”，响应慢是“反馈来得太晚”，ANR 是“晚到系统已经判定不可接受”。这也是为什么本章要和 `7.1`、`9.1`、`15.3`、`15.5` 一起看，才能形成完整判断。

了解响应速度的完整路径之后，我们就能在 Perfetto 中精准定位：延迟到底发生在 Input 分发阶段、App 主线程处理阶段、还是渲染合成阶段。每一种瓶颈的优化方向完全不同，搞清楚"慢在哪里"是解决问题的第一步。

## 响应速度的完整定义

响应速度（Responsiveness）是指**从用户执行操作（点击、滑动、按键），到系统产生对应的视觉反馈之间的时间间隔**。这个时间间隔越短，用户感觉系统"越跟手"。

响应速度和处理速度要分开看。一个操作可能后台处理需要 500ms，但如果 50ms 内已经给出视觉反馈（比如按钮变色、进度条出现），用户的感知就是这个系统"很快"。感知速度部分会展开这个问题。

### 响应速度的度量维度

在实际工程中，我们通常从以下几个维度度量响应速度：

**1. 点击响应速度（Tap Response Time）**——用户点击屏幕到系统给出视觉反馈的时间。这是最直观的响应速度指标。公开 Android Vitals 目前不单列 Tap Response Time 核心指标；排查时通常结合 Perfetto Input 轨道、慢帧、冻结帧和 ANR 数据判断。

**2. 滑动响应速度（Swipe Response Time）**——用户手指滑动到画面开始跟随移动的时间。滑动的感知比点击更敏锐，因为用户的眼睛在跟踪手指运动，任何微小的延迟都会被捕捉到。

**3. 启动响应速度（Launch Response Time）**——用户点击 App 图标到 App 界面出现的时间。这个指标在 Android Vitals 中被拆分为 TTID（Time To Initial Display，首次绘制时间）和 TTFD（Time To Full Display，完全绘制时间）两个子指标。

华为在《交互流畅体验设计》文档中给出了更精细的推荐指标：点击响应时延 ≤ 100ms，抛滑响应时延 ≤ 80ms，拖滑响应时延 ≤ 60ms。[来源: Cubox/华为-交互流畅体验设计-2025-02-18.md]

## RAIL 模型与 Android 性能目标

RAIL 是 Google 提出的以用户感知为中心的性能模型，最初用于 Web 前端，但其核心理念同样适用于 Android。RAIL 将用户交互拆解为四个阶段，每个阶段都有明确的性能目标。[已验证: 官方文档, web.dev/articles/rail]

### Response——响应（< 100ms）

用户执行操作后，系统在 100ms 内必须给出可见的反馈。这个 100ms 来自用户感知研究：100ms 是人类感知"即时反馈"的临界点。操作和反馈之间的间隔超过 100ms，用户就会觉得"系统在处理"，即时回应感会下降。

在 Android 中的具体含义：
- 主线程（UI Thread）的任何操作都不能阻塞超过 100ms
- 所有耗时操作（网络请求、数据库读写、复杂计算）都必须放到后台线程
- 如果某个操作需要超过 100ms，应该在 50ms 内先给出一个过渡态反馈（比如显示 loading 状态），然后异步处理

### Animation——动画（命中 VSync Deadline）

动画和滚动场景下，每一帧的渲染必须在当前刷新率对应的 VSync 周期内完成。传统写法是 60Hz 屏幕 16ms、120Hz 屏幕 8ms，但 Android 15+ 广泛采用自适应刷新率（ARR）后，帧预算变成了动态值——系统调度器会根据内容意图（滑动、动画、静止）动态切换 VSync 周期。Animation 阶段的目标是"命中调度器分配的 Expected Deadline"，而非死守某个固定数值。这个时间包括 Input 事件处理、业务逻辑更新、measure/layout/draw 整套流程。

Android 通过 Choreographer 机制来同步 VSync 信号，如果某一帧的处理时间超过了 VSync 周期，就会产生"掉帧"（jank），用户会感知到画面卡顿。关于 Choreographer 的详细机制，我们在 [2.4 Choreographer 与渲染流水线](04-choreographer.md) 中专门讨论。

### Idle——空闲

当用户没有主动操作时，系统应该尽量保持空闲状态。空闲时间有两个用途：一是确保下一次用户操作到来时系统能立即响应；二是利用空闲时间做预加载、缓存等优化工作。

关键原则：后台任务应该拆分成小块执行（每块不超过 50ms），这样即使突然有用户输入到来，系统也不会因为后台任务正在执行而无法及时响应。

### Load——加载（首次 < 5s，后续 < 2s）

首次打开应用或页面的加载时间应控制在 5 秒以内（中端设备），后续加载应在 2 秒以内。Android 通过 SplashScreen API（Android 12+）提供了标准的启动画面机制，让开发者可以在加载过程中给用户提供即时视觉反馈。

[图：RAIL 模型四个阶段及其性能目标]

## 系统级响应路径：从触摸到像素

理解响应速度的关键，是搞清楚用户一次触摸操作经历了哪些环节。我们从头到尾拆解这条路径。

### 第一步：Input 事件的捕获与分发

当用户触摸屏幕时，硬件产生一个中断，内核的触摸驱动将其转换为输入事件。随后 InputReader（运行在 system_server 的 InputFlinger 线程中）读取这些事件，交给 InputDispatcher 进行分发。

InputDispatcher 通过 InputChannel 将事件发送给目标 App 进程。AOSP android-16.0.0_r1 中，InputDispatcher::publishMotionEvent() 调用 connection->inputPublisher.publishMotionEvent()；InputPublisher 将 MotionEvent 序列化到 InputChannel 的共享消息缓冲区，再通过 Unix domain socket/socketpair 发送通知并传递输入消息。App 侧 NativeInputEventReceiver 监听 fd，InputConsumer 取出事件后封装为 Java 层 MotionEvent，投递到主线程消息队列。Binder 只参与窗口和 InputChannel 的创建、传递阶段，不承载每个 MotionEvent 的分发。

这条路径在 Perfetto 中对应的是 Input Track 和对应 App 主线程上的 Input 事件处理 slice。从 InputDispatcher 发出到 App 收到，通常耗时在 1-2ms；如果主线程被阻塞（比如正在执行长时间的 measure/layout），这个时间会显著增加。

关于 Input 分发的完整机制，我们在 [3.1 Input 事件分发全流程](01-input-dispatch.md) 中详细讨论。

### 第二步：App 主线程处理

App 主线程收到 Input 事件后，工作按固定顺序展开：事件处理、UI 状态标记、注册下一个 VSync-app。`View.onTouchEvent()` 被调用；如果设置了 `OnClickListener`，点击事件会传递到业务逻辑层，触发数据更新或界面跳转。需要重绘界面时，系统会调用 `View.invalidate()` 或 `View.requestLayout()`，把对应的 View 标记为"需要重新绘制"或"需要重新布局"。随后 Choreographer 向 SurfaceFlinger 注册下一个 VSync-app 信号，告诉渲染管线"下一帧有新内容需要画"。

这一步是开发者最能控制的部分，也是最常见的性能瓶颈来源。如果在 onClick() 中执行了数据库查询、网络请求、或者复杂的 JSON 解析，主线程就会被阻塞，导致后续的渲染流程无法按时启动。

在 Perfetto 中，我们可以在 App 主线程上看到这些工作的 trace slice。如果某个 slice 特别长（比如一个黄色的 "bindApplication" 或 "performTraversals" 延伸到了下一个 VSync 周期之后），那就是问题所在。

### 第三步：渲染与合成

VSync-app 信号到来后，Choreographer.doFrame() 被触发，主线程依次执行：
- Input callbacks（处理待处理的输入事件）
- Animation callbacks（更新动画属性值）
- Traversal callbacks（执行 performTraversals：measure → layout → draw）

在 draw 阶段，主线程生成 DisplayList（绘制命令列表），然后交给 RenderThread（Android 5.0+）进行 GPU 渲染。RenderThread 通过 GPU 将 DisplayList 转换为像素数据，写入 GraphicBuffer。

SurfaceFlinger 在 VSync-sf 信号到来时，将所有 Layer 的 GraphicBuffer 合成，通过 Hardware Composer（HWC）提交给显示控制器，最终显示在屏幕上。

在 Perfetto 中，我们可以在对应的 App 进程里看到主线程的 "Choreographer#doFrame" slice，以及 RenderThread 的 GPU 渲染工作。SurfaceFlinger 进程中有 "Commit" 和各 Layer 的合成操作。

[图：完整的响应路径时序图：触摸 → InputReader → InputDispatcher → InputChannel → App 主线程 → Choreographer → RenderThread → SurfaceFlinger → 屏幕]

### 路径中的瓶颈分布

根据 AOSP 官方文档的分析框架，性能问题可以归结为两类：**Capacity（容量）不足**和 **Jitter（抖动）过大**。[已验证: 官方文档, source.android.google.cn/docs/core/tests/debug/eval_perf]

容量问题指的是系统计算资源不足以在规定时间内完成所有工作。比如布局太复杂，measure+layout 花了 20ms，超出了 16ms 的帧预算。

抖动问题指的是系统虽然有足够的平均性能，但偶尔会出现执行时间的剧烈波动。比如某一帧因为 GC 暂停、Binder 调用慢、或者锁竞争导致执行时间从 5ms 飙升到 50ms。抖动问题的危害往往比容量问题更大——因为用户对"偶尔卡一下"的感知比对"一直慢"更强烈。

Google 在评估指南中给出了一个精彩的例子来解释这个问题：假设有两个 SoC 运行同样的渲染 benchmark——SoC A 每帧稳定在 10ms，总分 10000；SoC B 在 99% 的情况下每帧 1ms，但有 1% 的帧需要 100ms，总分 19900。从 benchmark 分数看 SoC B "更快"，但在实际使用中，SoC A 的体验会远好于 SoC B，因为 SoC B 每 1.5 秒就会出现一次明显的卡顿。

## Android Vitals 中的响应速度指标

Android Vitals 是 Google Play 内置的应用质量监控系统，它会自动采集用户设备上的性能数据，并在 Play Console 中向开发者展示。

### 呈现速度（Render Time）

Android Vitals/Play Console 的呈现速度指标主要关注慢帧和冻结帧：

- 慢帧（Slow rendering）：帧渲染时间超过当前刷新率对应的帧预算。60Hz 场景常用 16ms 作为参考；90Hz、120Hz 下预算约为 11ms、8ms。
- 冻结帧（Frozen frames）：单帧渲染时间超过 700ms，用户通常会感知为明显停顿。
- 游戏场景还会关注 slow sessions，用会话内慢帧占比评价玩家体验。

### 启动时间（App Startup Time）

Android Vitals 区分三种启动类型，并分别设定了"过长"的告警阈值：

| 启动类型 | 定义 | 告警阈值 |
|---------|------|---------|
| 冷启动（Cold） | 进程不存在，需要完整创建 | > 5s |
| 温启动（Warm） | 进程存在但 Activity 需重建 | > 2s |
| 热启动（Hot） | 进程和 Activity 都在后台 | > 1.5s |

[已验证: 官方文档, developer.android.com/topic/performance/vitals]

Android Vitals 当前用两个更精细的启动指标描述启动体验：

**TTID（Time To Initial Display）**——从系统收到启动 Intent 到 App 第一帧绘制完成的时间。这个指标由系统自动上报，反映的是用户从点击图标到看到 App 画面的时间。

**TTFD（Time To Full Display）**——从启动到 App 调用 `Activity.reportFullyDrawn()` 的时间。`reportFullyDrawn()` 从 API 19（Android 4.4）起就已存在；这个指标反映的是 App 内容完全加载并可交互的时间。开发者需要主动调用 `reportFullyDrawn()` 来触发上报，如果不调用，TTFD 就不会被记录。[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time；AOSP android-4.4_r1 Activity.reportFullyDrawn() 已存在]

Android 12（API 31）在启动体验方面引入的是 SplashScreen API，为所有 App 提供系统级启动画面，与 TTID/TTFD 指标本身是独立的版本点。

### ANR（Application Not Responding）

ANR 是响应速度问题的极端表现。当主线程被阻塞超过一定时间（Input 事件 5 秒、Service 20 秒、BroadcastReceiver 10 秒），系统会弹出"应用无响应"对话框。ANR 率直接影响应用在 Google Play 上的可见性和推荐权重。

## 感知速度 vs 实际速度

这一节讨论的可能是整个响应速度优化中最实用的一个观点：**用户感知到的速度，不完全等于实际的执行速度。**

### 为什么感知速度更重要

人类对"等待"的感知呈非线性变化。心理学研究表明：
- 0-100ms：感觉"即时"，操作和反馈融为一体
- 100-300ms：感觉"略有延迟"，但仍在可接受范围
- 300-1000ms：感觉"正在处理"，需要某种反馈来维持信心
- 1s 以上：感觉"在等"，注意力开始分散

这 100ms 的临界点可以通过视觉技巧来"骗过"。如果我们不能在 100ms 内完成完整处理，但能在 50ms 内给用户一个视觉反馈（即使这个反馈不包含最终结果），用户的感知仍然是"系统立即响应了我"。

华为在《交互流畅体验设计》文档中也强调了这一点：**感知流畅性不等同于系统性能。优秀的系统性能是保证用户感知流畅的必要条件，但好的系统性能不一定带来好的感知流畅性。** [来源: Cubox/华为-交互流畅体验设计-2025-02-18.md]

### 骨架屏（Skeleton Screen）

骨架屏是最常用的感知优化手段。核心思路是：在真实内容加载完成之前，先显示一个与最终布局结构一致的灰色占位界面。

骨架屏的核心作用体现在三个方面。**消除布局跳变**：用户看到的界面结构从一开始就是稳定的，不会出现内容加载完成后突然"跳"出来的情况，视觉上的连贯性得到了保证。**制造进度感**：即使内容还没加载完，灰色块的闪烁或渐变动画也在持续告诉用户"正在处理"。**降低等待焦虑**：心理学研究表明，明确的等待状态比不确定的等待更容易被接受，骨架屏恰好提供了一个明确的中间状态。

Android 12 的 SplashScreen API 提供了系统级的启动画面支持，可以在 App 初始化期间显示一个带图标的启动画面。

### 占位图与过渡动画

除了骨架屏，还有几种常用的感知优化技巧：

占位图（Placeholder）在图片加载前显示模糊缩略图或默认图标。Glide、Coil 等图片加载库都内置了 placeholder 支持，开发者只需在加载请求中指定占位资源即可。

过渡动画（Transition Animation）在状态切换时播放动画，起到"桥接"作用——把用户的注意力从前一个状态引导到后一个状态，让等待变得不那么明显。但动画时间需要控制——一般不超过 300ms，否则就从优化变成了浪费。

即时反馈（Immediate Feedback）是最直接也最有效的感知优化方式。按钮按下时立即变色、列表项滑动时立即跟随手指移动，这些"零延迟"反馈让用户确信系统接收到了操作。如果后续处理需要时间，可以在给出即时反馈之后再异步加载实际内容。

### 触摸预测（Touch Prediction）

Android 14（API 34）开始提供 MotionPredictor 公共 API。它用于根据历史 MotionEvent 预测未来触点位置，降低绘制与显示之间的视觉滞后。应用需要主动调用 `record(MotionEvent)` 记录输入历史，再调用 `predict(long predictionTimeNanos)` 获取预测事件；使用前还应通过 `isPredictionAvailable(deviceId, source)` 检查设备和输入源是否支持。

触摸预测不改变 Input 事件的实际分发延迟，它是在渲染侧做位置补偿。Android 16 可继续关注预测算法和系统侧集成的变化，但公共 API 入口在 Android 14（API 34）已经存在，本节不把“系统自动对所有触摸路径启用 ML 预测”写成已验证结论。

## UIL（User Interaction Latency）与端到端响应度量

UIL（User Interaction Latency）适合作为端到端响应分析口径，用来衡量从用户物理触摸屏幕到对应视觉反馈显示完成的全程延迟。它可以借鉴 Web INP（Interaction-to-Next-Paint）的分析思路，但 Google 公开文档目前未确认 UIL 已成为 Android Vitals 官方核心指标，也未公开确认 UIL 与 Google Play 排序存在直接关系。

**UIL 的工程目标**：P99 ≤ 200ms 可以作为内部推荐目标，来源是对 Web INP 200ms 阈值的借鉴，不应写成 Android 官方标准。超过 500ms 的交互延迟需要优先排查，但公开文档没有把它定义为 Input-based ANR 的提前触发阈值。

**UIL 的三大阶段拆解**：
1. **输入延迟**——从 InputDispatcher 发出事件到 App 主线程收到 MotionEvent，通常 1-2ms，主线程阻塞时会显著增加
2. **处理+渲染**——从 Choreographer.doFrame() 开始到帧被提交（measure → layout → draw → RenderThread GPU 渲染）
3. **合成+显示**——SurfaceFlinger 合成到 HWC 上屏

在 Android 上做响应速度优化，可以通过 Perfetto 手动拼装这三个阶段的耗时来获得完整视图。Perfetto 的 Frame Timeline 轨道中 Expected/Actual Deadline 的偏差直接反映了 UIL 中的处理+渲染阶段是否达标。

除了 UIL 拆解，排查响应速度时还应结合以下指标和 trace 观察点：
1. **Input dispatch delay**——从 InputDispatcher 发出事件到 App 收到 MotionEvent 的时间，可在 Perfetto Input 相关轨道和 App 主线程 slice 中观察
2. **Frame rendering time / slow frames / frozen frames**——从 Choreographer.doFrame() 到帧提交与显示的耗时，可结合 Frame Timeline 和 Android Vitals 呈现速度指标判断
3. **TTID / TTFD**——启动场景下的端到端响应指标

## 在 Perfetto 中分析响应速度

在实际工作中，我们通常按以下步骤在 Perfetto 中定位响应速度问题：

**Step 1：找到用户的操作时间点**。在 Perfetto 中打开 Input Track，定位触摸事件的 dispatch 时间。如果不确定事件发生的精确位置，可以先用搜索功能查找 `InputDispatcher` 关键词，从搜索结果跳转到对应时间轴位置。

**Step 2：追踪 App 主线程的处理**。从 App 主线程的 Input 事件 slice 开始，看 onClick() → invalidate() → scheduleVsync() 这个流程是否顺畅。如果主线程上有长时间的 binder 调用、锁等待、或者 GC，这里就能看到。

**Step 3：检查渲染管线**。从 Choreographer#doFrame 开始，看 performTraversals（measure/layout/draw）的耗时，以及 RenderThread 的 GPU 工作是否在 VSync 周期内完成。

**Step 4：检查 SurfaceFlinger 合成**。看 SurfaceFlinger 的 Commit 和合成操作是否按时完成。

关于 Perfetto 的使用方法，我们在 [第 13 章 Perfetto 工具链](01-perfetto-intro.md) 中详细讨论。

## 常见问题与误区

**误区 1："响应速度就是主线程不卡"**

不全对。响应速度涉及整条流程：Input 分发 → 主线程处理 → 渲染 → 合成 → 显示。主线程只是其中一个环节。即使主线程处理很快，如果 RenderThread 的 GPU 工作太重、SurfaceFlinger 的合成太慢、或者 Input 事件在 system_server 侧就排队了，响应速度照样会差。

**误区 2："只要把操作放到后台线程就行了"**

后台线程解决的是主线程阻塞问题，但不等于响应速度就好了。如果后台线程的处理结果需要回到主线程才能更新 UI，而这个回调因为主线程忙而被延迟执行，响应速度还是会差。正确的方式是：立即给出视觉反馈（主线程），然后异步处理（后台线程），处理完再更新 UI。

**误区 3："RAIL 模型是 Web 的，和 Android 没关系"**

RAIL 的核心思想——根据用户的感知阈值设定性能目标——是通用的。100ms 的响应临界点、动态的帧预算、以及对空闲时间的利用，这些在 Android 上同样适用。区别只在于实现手段不同。

## 参考资料

- [Evaluating Performance | Android Open Source Project](https://source.android.google.cn/docs/core/tests/debug/eval_perf) [已验证]
- [Android Vitals | Android Developers](https://developer.android.com/topic/performance/vitals) [已验证]
- [RAIL: A User-Centric Performance Model | web.dev](https://web.dev/articles/rail) [已验证]
- [华为 - 交互流畅体验设计](https://developer.huawei.com/consumer/cn/doc/best-practices-V5/bpta-smooth-application-design-V5) [来源: Cubox]
- AOSP 源码路径：
  - `frameworks/native/services/inputflinger/`（Input 分发）
  - `frameworks/base/core/java/android/view/Choreographer.java`（VSync 同步）
  - `frameworks/base/core/java/android/view/ViewRootImpl.java`（渲染管线入口）

---

> **验证状态**：本节核心内容（RAIL 模型、Android Vitals 指标、系统级响应路径）已通过 L2 官方文档验证。响应路径中的 InputChannel 描述已按 AOSP android-16.0.0_r1 源码修正。MotionPredictor 公共 API 入口按 Android 14（API 34）处理；Android 16 触摸预测系统侧变化和 UIL 官方地位不做未验证断言。
>
> **术语约定**：全文统一使用"响应速度"（Responsiveness）作为核心术语。"响应延迟"仅在引用外部指标定义时作为时间度量值使用，不作为独立术语。
