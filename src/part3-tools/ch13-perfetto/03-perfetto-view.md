---
title: "Perfetto View 解读"
chapter: "13.3"
section: "13.3"
status: finalized
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-28"
last_verified_against: "perfetto.dev FrameTimeline docs + source.android FrameTimeline + Perfetto thread-state/lock-contention docs + AOSP android-12.1.0_r1/android-13.0.0_r1/android-16.0.0_r1"
confidence: medium-high
reviewed_date: "2026-05-28"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_l1_l2_fixes: 4
task6_l3_l4_issues: 0
last_task6_at: "2026-05-28T12:10:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-12-review.md"
task6_review_notes: "2026-05-28 12 Task6 复审：L1/L2 小修 4 处，清理重复表述、冗余强调和少量术语化表达；无 L3/L4 回炉项，送 Task9 技术复审。"
sources:
  - type: blog
    path: "https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/"
  - type: official
    path: "https://perfetto.dev/docs/visualization/perfetto-ui"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-protractor"
  - type: official
    path: "https://perfetto.dev/docs/quickstart/traceconv"
  - type: official
    path: "https://source.android.com/docs/core/display/frame_timeline"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp"
  - type: blog
    path: "https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247487984&idx=1&sn=713bdccc885ef503b2f691fbd6e8f93"
tags:
  - android
  - perfetto
  - trace-view
  - frame-timeline
  - binder
  - thread-state
  - cpu-scheduling
related_chapters: ["13.1", "13.2", "13.4", "2.6", "14.2", "14.3"]
polish_count: 1
polish_date: "2026-04-10"
polish_by: "task2b-polish"
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
task9_result: auto-fixed
last_task2b_at: "2026-05-28T10:50:00+08:00"
task2b_fixed_by: openclaw-task2b
updated_date: "2026-06-09"
updated_by: openclaw-task9
last_task9_audit: "2026-06-09"
last_task9_at: "2026-06-09T17:25:15+08:00"
last_task6_audit: "2026-05-19"
last_task9_review_log: "logs/deep-review/2026-06-09-17-audit.md"
last_task9_autofix_at: "2026-06-09"
task9_review_notes: "2026-05-28 11 Task9 auto-fix: 修正 Perfetto UI 404 文档链接/打开入口说明，并修正 SurfaceFlinger Android 13+ commit/composite/present 排查入口；回到 Task6 复审。 | 2026-05-28 12 Task9 复审：pass-tech-review。P0 0 / P1 0 / P2 0；自动晋升 finalized。 | 2026-06-09 17 Task9 idle audit auto-fix: 修正 Perfetto v52 暗色主题实验状态与当前 UI Theme 命令说明；未发现 Android/API 38+ 越界内容，回到 Task6 复审。"
task9_reviewed_date: "2026-06-09"
task9_reviewed_by: openclaw-task9
p0: 0
p1: 0
p2: 0
---


# Perfetto View 解读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Perfetto UI 的基本操作：缩放、搜索、Pin Track、时间选区
- 🔹 关键 Track 的含义：CPU 频率/调度、进程/线程 Slice、FrameTimeline、SurfaceFlinger
- 🔹 Slice 详情面板的解读：Wall Duration、CPU Duration、Self Time
- 🔹 Flow Events 的跟踪：Binder 调用的配对
- 🔹 颜色编码：线程状态色（Running/Runnable/Sleep/Uninterruptible/锁竞争红色标记）

### 扩展（可选深入）

- 🔸 Perfetto UI 的快捷键与效率技巧
- 🔸 与 Android Studio Profiler 中的 Trace 视图的对比

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要专门学 Perfetto View

13.1 节讲了 Perfetto 的定位和架构，13.2 节讲了怎么抓 Trace。但抓到 Trace 只是第一步——面对一个动辄几百 MB 的 `.perfetto-trace` 文件，如果不知道怎么看，数据再多也没用。

第一次打开 Perfetto UI，常见感受是"信息过载"：满屏幕的色块、密密麻麻的 Track、各种看不懂的缩写。Perfetto 展示的是整个 Android 系统在抓取时段内的全部活动——所有进程、所有线程、所有 CPU 核心、所有图形管线——信息量很大。

换成分析动作看，读 Trace 不需要逐条看每一个事件，而是先定位时间区间、关键 Track 和线程状态颜色，再顺着异常片段往下追。

本节解决这三个问题。读完之后，再打开一个 Perfetto Trace，应该能快速找到主线程在做什么、渲染线程跑在哪个核心、Binder 调用跳到了哪个进程、掉帧发生时系统各模块的状态——这些是日常性能分析最常用的操作。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

## Perfetto UI 的基本操作

### 打开 Trace 文件

Perfetto Trace 文件在 [ui.perfetto.dev](https://ui.perfetto.dev/) 中打开。当前 UI 可以从侧边栏点击 "Open trace file" 选择本地文件，也可以直接把 Trace 文件拖进浏览器窗口。

如果使用的是 13.2 节介绍的官方脚本抓取，脚本会在抓取结束后自动在浏览器中打开这个页面并加载 Trace。

Perfetto UI 对浏览器内存有要求。如果 Trace 文件超过 500 MB，浏览器加载可能会很慢甚至失败。这种情况下可以参考 13.4 节介绍的命令行方案，用 Trace Processor Shell 直接做 SQL 分析，或者用官方 `traceconv text <input> <output>` 把 `.perfetto-trace` 转成文本再查。`traceconv` 是 Perfetto 对外公开的 CLI，`trace_to_text` 更接近仓库内部脚本名，不适合写成读者默认入口。

[已验证: 官方文档, perfetto.dev/docs/visualization/perfetto-ui]

### 界面布局

Trace 加载完成后，界面可以分为四个区域：

最左边（侧边栏）是导航区，包含几个常用入口：Show Timeline（回到 Trace 主视图）、Query（SQL 查询）、Metrics（预设分析指标）、Info and Stats（Trace 概要信息）。日常分析中大部分时间都在 Timeline 主视图里操作，侧边栏只在需要 SQL 查询或查看预设指标时才会切换过去。

上方是时间标尺区，显示时间轴和缩放级别。通过时间标尺可以快速判断当前查看的时间窗口是毫秒级、秒级还是分钟级。

中间是 Trace 内容区，也是操作最多的区域。最上面的几组 Track 是系统级的：CPU 各核心的调度和频率、ftrace 事件等。下面是以进程为单位组织的：每个进程下面展示它的各种线程、Input 事件、Binder 调用、Memory 信息等。进程之间用进程名分隔，比如 `com.android.systemui`、`system_server`、`surfaceflinger` 等。

最下方是详情面板，选中任何一个 Slice（Trace 中的一个事件块）后，这里会展示该事件的详细信息：耗时、CPU 时间、线程状态分布、唤醒源等。这个面板是深入分析的主要入口。

[图：Perfetto UI 四大区域标注——侧边栏、时间标尺、Trace 内容区、详情面板]

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

### 缩放与导航

Perfetto 的导航操作继承了 Systrace 的设计，但流畅度有了质的飞跃——Systrace 打开稍大的 Trace 就会明显卡顿，而 Perfetto 即使加载 500 MB 的 Trace 依然操作顺滑。这是因为 Perfetto UI 使用了 WebGL 渲染和智能数据聚合，不会在缩放时尝试绘制所有事件。

核心导航操作围绕 WASD 键布局：`W` 放大、`S` 缩小、`A` 左移、`D` 右移。这套键位设计让左手可以不离开键盘就能完成大部分浏览操作，右手操作鼠标做选择和点击。

最常用的操作是 `F`（Fit）：选中一个 Slice 后按 `F`，视图会自动缩放到刚好容纳这个 Slice 的大小。再按一次 `F`，会进一步缩放到填满整个视图。日常分析中经常用它处理长 Slice——比如主线程出现一个很长的 `doFrame` Slice，按 `F` 就可以立刻看到这一帧内部的全部细节。

时间选区用鼠标拖拽实现：按住鼠标左键在时间轴上拖动，会选中一个时间区间。选中后，底部面板会展示这个区间内的统计信息，包括各线程状态（Running/Runnable/Sleep/Uninterruptible）的占比，并结合红色锁竞争标记判断等待原因。这适合分析 App 启动场景——选中从 `Activity.onCreate` 到第一帧渲染完成的区间，就能直观地看到主线程有多少时间在执行代码，多少时间在等待 CPU 或 I/O。

[已验证: 官方文档, perfetto.dev UI keyboard shortcuts]

### 搜索

在 Trace 中搜索事件有两种方式。一是使用顶部搜索栏直接输入关键词，比如输入 `doFrame` 可以高亮所有名为 `Choreographer#doFrame` 的 Slice。二是使用 SQL 查询（在侧边栏的 Query 面板或搜索栏中输入 `:` 前缀），这适合更精确的筛选，比如"找出 system_server 中耗时超过 50ms 的所有 Slice"。SQL 查询的用法在后续 13.5 节专题分析中会详细介绍。

### Pin Track

每个 Thread Track 的最左边有一个图钉图标，点击后这个 Track 会被固定到 Trace 内容区的顶部，不再随进程分组滚动。这个功能适合分析跨进程问题——比如把 App 的 MainThread、RenderThread 和 SurfaceFlinger 的主线程都 Pin 到顶部，观察掉帧时，三个关键线程的时间线就在同一个视野里，不需要上下滚动来回对照。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

### 标记与旗子

Perfetto 提供了两种标记方式，用来在 Trace 上做注释。

`M` 键创建临时标记（Temporary Mark）。选中一个时间区间后按 `M`，区间会被高亮标注。但它只保留最新的一个——如果再对另一个区间按 `M`，前一个就会自动消失。临时标记适合快速对比两个点的时间差。

`Shift+M` 创建持久标记（Sticky Mark）。持久标记不会自动消失，除非手动删除。分析长 Trace 时，可以用它标记所有掉帧点，然后逐个检查。标记创建后，点击小旗子图标就能查看标记区间的详细信息。删除标记的方法是点击标记上方的三角箭头，在底部的 Current Selection 面板中点击 Remove。

此外，把鼠标放到 Trace 最上方的时间轴上会出现一个旗子图标，点击可以在时间轴上插一个点标记（不是区间标记），用来标注某个关键时间点，比如"用户点击了按钮"。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]
[已验证: 官方文档, perfetto.dev UI documentation]

## 关键 Track 的含义

Perfetto 的 Trace 内容区由许多水平排列的 Track 组成。每个 Track 展示某一类信息在同一根时间轴上的变化。理解这些 Track 的含义，是读懂 Trace 的基础。

### CPU 频率与调度 Track

CPU 相关的 Track 位于 Trace 内容区的最顶部，分为三组。

**CPU Frequency Track** 展示每个 CPU 核心的运行频率随时间的变化。频率用阶梯状的折线表示——因为 CPU 频率是离散调节的，不会平滑变化。在分析性能问题时，频率 Track 是排查"CPU 跑低了"的第一站。比如主线程的一段代码执行了 10ms，但看代码逻辑不应该这么慢，这时候就应该去查对应时间点大核频率是否被限制在了低频。这种情况在厂商的温控策略或调度策略配置不当时经常出现。

**CPU Scheduling Track** 展示每个核心上正在执行哪个线程。每个色块代表一个线程在某个时间段内占用了这个核心。鼠标悬停在色块上时，同一线程的其他执行段也会高亮——这个功能可以快速了解某个线程的"摆核"情况，即它在大核和小核之间迁移的规律。对于性能敏感的线程（如主线程、RenderThread），理想情况是稳定跑在大核上；如果频繁被迁移到小核，可能意味着调度策略需要优化。

**CPU Idle Track** 展示每个核心的低功耗状态（C-State）。核心进入深度休眠说明它完全空闲，这对功耗分析很有价值。但在性能分析中，我们更关注的是反常情况：如果某个关键线程本该运行，但它被分配到的 CPU 核心却处于空闲状态，说明线程可能在等锁、等 I/O，或者没有被调度到。

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu]
[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

[图：CPU Frequency/Scheduling/Idle Track 示例，标注大核频率变化和线程摆核]

### 进程与线程 Track

CPU Track 下面是以进程为单位组织的 Track 区域。每个进程有一个可折叠的分组，展开后会列出该进程下的各个线程。

**Thread Track** 是日常分析最多的 Track 类型。每个线程 Track 上展示两种信息：下方是 Slice（事件片段），对应代码中 `Trace.beginSection()` / `ATRACE_BEGIN` 记录的事件；上方是线程状态条，用不同颜色表示线程在每个时刻的 CPU 状态（Running、Runnable、Sleep、Uninterruptible Sleep），并用红色锁竞争 slice 提醒 Java/ART monitor 等等待问题。线程状态条的颜色编码在下一节详细介绍。

对于 App 进程，我们最常关注的线程是：

- **MainThread**（也称 UI 线程）：处理 Input 事件、动画计算、View 的 measure/layout/draw。在 Trace 中，MainThread 上的 `Choreographer#doFrame` Slice 是分析每帧渲染耗时的入口。
- **RenderThread**：从 Android 5.0 引入，负责将 MainThread 绘制的 DisplayList 提交给 GPU 执行。在 Trace 中，RenderThread 上的 `DrawFrame` Slice 包含了 GPU 命令提交和 Fence 等待的细节。
- **Binder 线程**（如 `Binder:1234_5`）：处理来自其他进程的 Binder 调用。Binder 线程上的 Slice 通常是系统服务方法的执行，比如 `ActivityManagerService.startActivity`。

对于 `system_server` 进程，除了各种 Binder 线程外，还有 `android.display`、`android.fg`（Foreground Thread）、`ActivityManager` 等系统线程，它们分别处理显示相关的同步操作、前台优先级的后台任务、以及 Activity 生命周期管理。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]
[已验证: AOSP, frameworks/base/core/java/android/os/Trace.java — Trace.beginSection API]

### FrameTimeline Track

FrameTimeline 是 Android 12（API 31）引入的轨道，位于 App 进程的线程 Track 上方。它通常分成两行：上面是 Expected Timeline，下面是 Actual Timeline。

Expected Timeline 表示系统为这一帧预留的完成窗口。60 Hz 设备上一格约 16.6ms，120 Hz 设备上一格约 8.3ms。Actual Timeline 表示这帧最终的实际结果。把两行放在同一时间轴下比较，超时帧会直接冒出来。

选中 Actual Timeline 里的单帧后，先看 Details 面板里的 `Jank Type`。官方 FrameTimeline 文档列出的 jank 类型包括 `AppDeadlineMissed`、`BufferStuffing`、`SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed`、`DisplayHAL`、`PredictionError`。Perfetto UI 可能显示带空格的中文/英文文案，报告里应保留原始字段值。蓝色 Dropped frame 是帧状态，文档标注为不属于 jank，不能和 `Jank Type` 枚举并列归因。

| Android 版本 | 主入口 | 回看哪些轨道 | 归因方式 |
| --- | --- | --- | --- |
| Android 10-11 | `Choreographer#doFrame` | `VSYNC-app`、`VSYNC-sf`、主线程、`RenderThread`、`SurfaceFlinger` | 没有 FrameTimeline 主表，靠时间轴和线程态手工判断 |
| Android 12-13 | `Expected Timeline` + `Actual Timeline` | `doFrame`、`DrawFrame`、`surfaceflinger` 主线程 | 先看 `Jank Type`，再回到线程级 slice |
| Android 14+ | `Expected Timeline` + `Actual Timeline` | `doFrame`、`DrawFrame`、`commit` / `composite` / `present` | 主入口不变，但 SurfaceFlinger 侧要按新主循环读 |

这样读，Android 10/11 不会被误导去找不存在的 FrameTimeline，Android 12+ 也不用再靠旧的 `app_missed` / `sf_missed` 私有口径猜原因。

[图：FrameTimeline Track 示例——Expected（灰色）与 Actual（绿色/黄色/红色/蓝色）对比，标注 `Jank Type` 查看位置]

[已验证: 官方文档, source.android.com/docs/core/display/frame_timeline]
[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

### SurfaceFlinger Track

SurfaceFlinger 是 Android 系统的合成服务（详见 2.6 节），读这条 Track 一定要按版本拆开。

Android 12.1 仍能看到 `SurfaceFlinger::onMessageReceived`、`onMessageInvalidate`、`onMessageRefresh` 这组旧消息入口。读 Android 12 trace 时，可以先用 `INVALIDATE` / `REFRESH` 判断事务收敛和合成窗口。

Android 13 已经进入 `Scheduler/MessageQueue.cpp::Handler::handleMessage` 直接调用 `compositor.commit()`、`compositor.composite()`、`sample()` 的路径，`SurfaceFlinger.cpp` 中也已有 `SurfaceFlinger::commit()`。从 Android 13 开始，trace 入口不能继续按 Android 12 的旧消息模型归类。

Android 14-16 继续由 `Scheduler::onFrameSignal()` 组织 `commit` / `composite`，提交显示结果落到 CompositionEngine 的 `Output::present()` / `presentFrameAndReleaseLayers()`。分析掉帧时，App Track 只是入口，SurfaceFlinger Track 是下游验证点：Android 12.1 看 `REFRESH` 是否跨过刷新窗口；Android 13+ 看 `commit` / `composite` / `present` 是否拉长，再判断是事务处理、Client composition 还是显示提交拖慢了这一帧。

如果 `composite` 下方出现 `drawLayers`、`renderengine` 或 GPU render stage 相关子调用，通常表示本帧触发了 Client Composition。此时再回看图层数量、透明混合、圆角/阴影、Protected content 等因素，判断是 HWC 无法直接接管，还是 GPU 合成工作本身过重。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

### Counter Track

除了 Slice Track 外，Perfetto 还有一种 Counter Track，展示数值随时间的变化。常见的 Counter Track 包括：

- **Memory Counter**：在进程分组下展示 Java Heap、Native Heap、GPU Memory 等内存指标的变化曲线。内存泄漏问题通常表现为某条曲线持续上升。
- **CPU Counter**：在 CPU 分组下展示各核心的频率曲线、系统 CPU 使用率。
- **GPU Counter**：如果抓 Trace 时启用了 GPU 数据源，可以查看 GPU 各单元的利用率和带宽。

Counter Track 的数值点来自应用、系统模块、native 代码和内核数据源。普通 App 侧公开入口是 `Trace.setCounter(String, long)`；平台代码和系统模块可见隐藏的 `Trace.traceCounter()`；native 侧常用 `ATRACE_INT` / `ATRACE_INT64`；内核侧则来自 ftrace 事件。它们以面积图（Area Chart）的形式呈现，底色填充区域表示数值变化范围，鼠标悬停时会显示每个点的精确值。在内存分析场景中，面积图的"持续上升"形态比表格数据更直观。

[来源: Perfetto 分析进阶, https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247487984]
[已验证: 官方文档, perfetto.dev/docs/data-sources]

掌握各 Track 的含义后，下一步是学会看单个事件的详细信息。Perfetto 的 Slice 详情面板是深入分析的核心入口——它不仅告诉你"这个事件持续了多久"，还揭示"这段时间里线程在干什么"。

## Slice 详情面板的解读

选中任何一个 Slice 后，底部面板会展示该 Slice 的详细信息：事件持续时间、线程状态、唤醒源，以及这段时间里的 CPU / 等待组成。

### Wall Duration 与 CPU Duration

**Wall Duration**（墙上时间）是 Slice 从开始到结束的真实经过时间。就像用秒表计时一样，不管线程是在运行还是在睡觉，Wall Duration 都在走。它直接对应 Trace 中看到的 Slice 宽度——越宽的 Slice，Wall Duration 越长。

**CPU Duration**（CPU 时间）是线程在这个 Slice 期间在 CPU 上执行指令的时间。它排除了线程被挂起（Sleep）、等待 CPU 调度（Runnable）、等待 I/O（Uninterruptible Sleep）的时间。

理解这两个指标的关系是性能分析的核心基本功。它们之间的关系可以写成：

> Wall Duration = CPU Duration + 等待时间（Runnable + Sleep + Uninterruptible）

举一个具体的例子：MainThread 上一个 `bindApplication` Slice 的 Wall Duration 是 200ms，但 CPU Duration 只有 30ms。也就是说，200ms 中有 170ms 线程没有在执行代码——它在等什么？切换到详情面板的 Thread States 标签，就能看到这 170ms 的组成：可能是 80ms 的 Sleep（等 Binder 调用返回），60ms 的 Runnable（等 CPU 调度），30ms 的 Uninterruptible Sleep（等磁盘 I/O）。每种等待的优化方向完全不同，因此要同时看 Wall Duration 和 CPU Duration。

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-protractor — slice details]

### Self Time

**Self Time**（自身时间）是 Slice 的 Wall Duration 减去其子 Slice 的 Wall Duration。它表示"这个 Slice 自身直接消耗的时间"，不包括它调用的子函数。

Self Time 的意义在于定位瓶颈层级。比如 `doFrame` 的 Wall Duration 是 20ms，但 Self Time 只有 1ms——说明时间都花在了它的子 Slice 里（比如 `performTraversals` 里的 `measure` 5ms + `layout` 3ms + `draw` 11ms）。进一步看 `draw` 的 Self Time 可能也只有 2ms，因为大部分时间在子 Slice `RenderThread:DrawFrame` 里。这样逐层展开，就能精确找到时间花在了哪一层。

做批量分析时，不要手写一长串父子 Slice 扣减逻辑。新版 Trace Processor 的 `slices.self_dur` stdlib 模块提供 `slice_self_dur` 表，`self_dur` 列就是已经扣掉子 Slice 的自身耗时；旧版本没有这组 stdlib 时，再退回到 `slice` 表父子关系手工计算。

### Thread States 标签

详情面板中的 Thread States 标签用饼图和列表展示 Slice 期间线程各状态的占比。结合 Wall Duration 和 CPU Duration，这里给出了最完整的时间分解：

- **Running 占比高**（接近 100%）：说明线程一直在执行代码，优化方向是减少计算量（算法优化、减少布局层级等）。
- **Runnable 占比高**：说明线程准备好了但 CPU 不给它执行，优化方向是调度策略（提升线程优先级、减少背景负载）。
- **Sleep 占比高**：说明线程在等待某个事件（锁、Binder 回复、条件变量），优化方向取决于它在等什么。
- **Uninterruptible Sleep 占比高**：说明线程在等磁盘 I/O 或其他内核操作，通常需要从 I/O 模式优化（异步化、减少磁盘读写）。

[已验证: 官方文档, perfetto.dev — thread_state SQL table]

### 唤醒源（Waker）

当选中一个线程的 Runnable 状态段时，详情面板会显示"Related thread states"，其中最重要的信息是 Waker（唤醒源）：是哪个线程、在哪个 CPU 核心上唤醒了当前线程。这个信息直接决定能否还原事件传递链。

比如主线程在某个时刻从 Sleep 变为 Runnable，通过查看唤醒源，有时会看到唤醒线程来自 SurfaceFlinger 的 `app` 线程——这通常对应 VSync-app 信号到达后，SurfaceFlinger 通过 callback 通知 Choreographer，Choreographer 再唤醒主线程开始这一帧的渲染。

在 Perfetto 中追踪唤醒链的步骤很短：点击线程状态条上的 Runnable 段，底部面板展示唤醒源，点击唤醒源旁边的小箭头可以直接跳转到唤醒线程的对应位置。连续点击这个箭头，可以沿着唤醒链一路往回追溯，直到找到最初的触发者。这个操作适合分析"响应为什么慢"——响应慢往往是因为中间某个环节的唤醒延迟过大。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

单个 Slice 只能解释当前线程的内部细节。很多性能问题跨线程、跨进程：Binder 调用跨了进程，VSync 信号连接了 App 和 SurfaceFlinger，Input 事件从内核一路传到 App 主线程。追踪这些事件流，需要用到 Flow Events。

## Flow Events 的跟踪

### 什么是 Flow Events

Flow Events（流事件）是 Perfetto 中连接跨线程、跨进程事件的机制。在 UI 中，Flow Events 表现为从一个 Slice 到另一个 Slice 的箭头。最典型的场景就是 Binder IPC：App 进程发起一个 Binder 调用，这个调用通过内核传递到 `system_server`（或其他服务进程）的 Binder 线程执行，执行结果再通过内核返回给 App。

如果不看 Flow Events，只能看到 App 的某个 Slice 里有一段 Sleep 或 Binder 等待，但不知道对端在做什么。有了 Flow Events 的箭头，就可以直接看到这段等待对应的是哪个进程的哪个方法执行。

### Binder 调用的追踪

在 Perfetto 中追踪 Binder 调用的步骤很短。选中一个包含 Binder 调用的 Slice 后，底部面板会显示与这个调用相关的 Flow 信息。点击箭头可以在发起端和响应端之间跳转。

具体操作流程是这样的：假设 App 主线程上有一个 `bindService` Slice，它内部包含一段 Binder 通信。选中这段 Binder 通信的 Slice 后，详情面板会展示目标进程和目标方法。点击跳转箭头，视图会自动跳转到 `system_server` 中处理这个调用的 Binder 线程，并看到 `ActiveServices.bindServiceInstance` 这个 Slice 以及它的完整执行过程。

这种跨进程跳转能力是 Perfetto 相比传统日志分析的核心优势。在日志里分析 Binder 调用需要手动匹配两个进程的时间戳和调用 ID；在 Perfetto 里，点一下箭头就完成了。

[图：Binder Flow Event 箭头——App 主线程到 system_server Binder 线程的跨进程跳转]

Flow Events 的箭头在默认视图中可能不会全部显示。如果箭头太密集，Perfetto 会自动省略一些。选中某个 Slice 后，与它相关的 Flow 箭头会高亮显示。

[已验证: 官方文档, perfetto.dev — Flow events documentation]
[已验证: 官方文档, perfetto.dev — Binder transaction analysis]

### Critical Path

除了单个 Flow Event 的追踪，Perfetto 还提供了一个更高级的功能：**Critical Path**。选中一个 Slice 的 Running 状态段后，在底部面板中点击 "Critical path"，Perfetto 会自动计算并高亮显示所有与这个 Slice 有依赖关系的上游 Slice。

例如，选中的 Slice 是 e，它依赖 d 的完成，d 依赖 c，c 依赖 b，b 依赖 a，那么 Critical Path 会把 a → b → c → d → e 这条依赖路径全部高亮出来。这适合分析启动流程的端到端耗时——从用户点击到界面显示的完整依赖链上，每个环节花了多少时间，瓶颈在哪里，都能沿着高亮路径检查。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

## 颜色编码：线程状态色

Perfetto 中最直观也最常用的视觉信息就是线程状态条的颜色。每个 Thread Track 的上方都有一条细细的状态条，用不同颜色表示线程在每个时刻的 CPU 状态。掌握这些颜色的含义，就掌握了快速定位性能瓶颈的能力。

### Running（绿色）

绿色表示线程正在 CPU 上执行指令。一段连续的绿色说明线程在"干活"。但这并不意味着绿色越长越好——如果主线程上有一段很长的绿色，对应的 Slice 是 `measure` 或 `layout`，说明布局计算太复杂了，需要优化布局层级或减少不必要的 measure。

### Runnable（浅绿色）

浅绿色表示线程已经准备好执行（在 CPU 的运行队列中），但 CPU 还没有调度到它。Runnable 段出现在 Running 段前面——线程先进入 Runnable 状态等 CPU 分配，然后进入 Running 状态执行。

Runnable 段过长是"调度延迟"的信号。常见原因包括：系统负载太高（太多线程抢 CPU）、线程优先级太低（被高优先级线程抢占）、或者 CPU 核心不够（所有大核都忙）。在分析启动速度时，如果主线程频繁出现长 Runnable 段，可能需要检查是否有后台进程在占用 CPU，或者是否需要提升主线程的调度优先级（通过 `setThreadPriority` 或 cgroup）。

### Sleeping（灰色）

灰色表示线程在等待某个事件：锁释放、Binder 回复、条件变量通知、或者 `Object.wait()`。Sleeping 是正常的——线程不可能一直在运行。但如果在不该等待的场景下出现长 Sleeping 段，就需要排查它在等什么。

点击 Sleeping 段，底部面板会显示线程的阻塞原因。比如 `futex_wait_queue_me` 表示在等一个 futex（Fast Userspace Mutex），这通常对应 Java 层的 `synchronized` 锁或 `ReentrantLock`。如果看到 `binder_write_read`，说明在等 Binder 调用返回。

### Blocked / 锁竞争（红色）

红色通常出现在 `Lock contention on a monitor lock` 这类锁等待 slice 或锁竞争标记上，表示线程正在等 Java/Kotlin monitor、ART monitor 或 native lock。它和 Running、Runnable、Sleeping 属于两层信息：底层调度状态可能仍然是 Sleep，但红色 slice 直接指出等待原因是锁。

选中红色段后，先看详情面板里的持锁线程、等待线程和锁对象信息；如果面板给出 `waking_thread`、owner 或跳转箭头，沿着它回到持锁线程的同一时间窗。主线程出现长红色段时，排查顺序是：持锁线程当时是否在 Running、是否又在等 Binder / I/O、锁持有范围是否过大。

红色段不等于严重优先级翻转。判断它是否影响当前卡顿，要看红色段是否位于这次掉帧或 ANR 的关键路径，持锁线程是否占着 CPU，或者持锁线程本身又被 Binder / I/O 阻塞。

### Uninterruptible Sleep（深橙色）

深橙色是性能分析中需要特别关注的颜色——它表示线程在等待磁盘 I/O 或其他不可中断的内核操作。Uninterruptible 意味着即使发送信号（如 `kill`）也无法唤醒这个线程，只能等 I/O 操作完成。

Uninterruptible Sleep 段过长通常指向 I/O 瓶颈。常见场景包括：App 启动时读取大量 dex 文件、加载大图、读取 SharedPreferences（虽然 SP 在内存中但初次加载涉及磁盘 I/O）。在低端设备或 I/O 负载高的场景下，这个问题尤其明显。

[已验证: Linux 内核, kernel/sched/core.c — TASK_UNINTERRUPTIBLE state]
[已验证: 官方文档, perfetto.dev — thread_state color coding]

### 快速判断思路

总结一下，在 Trace 中看到线程状态条时，可以用这个思路快速判断：

- **绿色长，其他短**：计算密集型瓶颈，优化方向是减少计算量。
- **浅绿色长**：调度瓶颈，优化方向是降低系统负载或提升线程优先级。
- **灰色长**：锁、IPC 或条件等待，需要看具体在等什么。
- **红色长**：锁竞争瓶颈，先跳到持锁线程，看它为什么不释放锁。
- **橙色长**：I/O 瓶颈，需要看具体在读什么。

实际情况往往比这组判断更复杂——可能一个 Slice 里同时有绿色、灰色和深橙色。这时候就需要用前面介绍的 Thread States 标签来看精确的百分比分解。

Perfetto UI 支持亮色和暗色两种主题。暗色主题从 Perfetto v52 起引入，但 v52 发布说明仍标记为 experimental；当前 UI 可在 Settings 的 `UI Theme` 中切换，或通过命令面板 `Ctrl/Cmd+Shift+P` 执行 `Toggle UI Theme (Dark/Light)`。两种主题下颜色编码的对应关系不变：绿色 = Running、浅绿 = Runnable、灰色 = Sleep、红色 = 锁竞争、深橙色 = Uninterruptible。暗色主题在长时间分析 Trace 时对眼睛更友好，建议默认开启。

[图：线程状态条颜色编码对照——Running(绿)/Runnable(浅绿)/Sleep(灰)/Blocked 锁竞争(红)/Uninterruptible(深橙)，附 Perfetto Trace 实际截图]

## 进阶操作与效率技巧

### 快捷键速查

除了前面提到的 WASD、F、M 键外，以下几个快捷键在日常分析中使用频率也很高：

`Q` 键切换底部详情面板的显示和隐藏。底部面板展开后，Trace 区域会被压缩。熟练使用 Q 键——看 Slice 时打开面板，浏览 Trace 时关闭面板——可以减少来回缩放和滚动。

`,` 和 `.` 键在同一个 Track 上移动到前一个/后一个 Slice。这在逐帧检查掉帧时很有用：定位到 `Choreographer#doFrame` 后，按 `.` 就能跳到下一帧的 `doFrame`，不需要鼠标点击。

`R` 键将当前选中的 Slice 转换为时间选区。统计某个 Slice 期间所有线程的活动时，这个操作比手动拖拽精确得多。

`Ctrl+Shift+P`（Mac 上 `Cmd+Shift+P`）打开命令面板，可以快速执行各种操作，比如切换到 Query 面板、调整 Trace 配置等。也可以在搜索栏中输入 `>` 来激活命令面板模式。

`?` 键会打开当前 UI 版本的快捷键列表。Perfetto UI 的快捷键随版本会有调整，团队内部文档记录快捷键时，最好把 UI 版本或验证日期一起写上。

[已验证: 官方文档, perfetto.dev — Keyboard shortcuts]

### 查看 Buffer 消费关系

App 的渲染输出通过 BufferQueue 传递给 SurfaceFlinger 消费。在 Perfetto 中，可以通过 App 进程的 Actual Timeline Track 追踪每一帧 Buffer 的消费情况：点击 Actual Timeline 上的一个色块，可以查到这个 Buffer 具体被 SurfaceFlinger 的哪一次合成操作消费了。这在分析"帧渲染完成但显示延迟"问题时很有用——可能帧画好了，但 SurfaceFlinger 等了两个 VSync 周期才合成它。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

### 查看锁竞争

当 Trace 中出现 `Lock contention on a monitor lock`（Java 层）或 `monitor contention`（ART 层）的红色 Slice 时，点击它可以在底部面板看到锁竞争详情：当前锁被谁持有、持锁线程正在执行什么方法、当前线程在哪个方法上被阻塞、以及当前有多少个线程在排队等这把锁。

锁竞争信息对于分析 ANR 和响应延迟很有用。一个典型的模式是：主线程调用 `ActivityManagerService` 的某个方法（通过 Binder），`system_server` 的 Binder 线程在处理这个调用时遇到了锁竞争，导致处理时间变长，主线程也就跟着等了更长时间。遇到红色段时，不要只盯着等待线程；沿详情面板里的 owner / waking 线索跳到持锁线程，才知道锁为什么没有及时释放。

[来源: Perfetto 分析进阶, https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247487984]

### 在 Trace 上查看 Log

Perfetto 支持在 Trace 上叠加显示 Logcat 日志。在底部面板切换到 "Android Logs" 标签，会列出抓取期间的所有日志输出。鼠标悬停到某一行日志上，Perfetto 会在 Trace 时间轴上画一条竖线标记这条日志对应的时刻。

这个功能把日志和 Trace 时间线关联起来，适合那些"日志说到了某一步，但 Trace 上不知道对应哪里"的场景。同样，切换到 "Ftrace Events" 标签会列出内核级别的 ftrace 事件，比如 `sched_switch`（调度切换）、`binder_transaction`（Binder 事务）等。

[来源: https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/]

## 与 Android Studio Profiler 的对比

Android Studio Profiler 也提供了 CPU Trace 的可视化视图，很多开发者的第一个性能分析工具就是它。那么 Perfetto View 相比 AS Profiler 的 Trace 视图有什么不同？

最核心的区别是**系统级视角 vs App 级视角**。AS Profiler 主要关注单个 App 的 CPU 使用、方法调用栈、内存分配，它看不到其他进程在做什么，也看不到 CPU 调度、SurfaceFlinger 合成、VSync 信号等系统级行为。而 Perfetto 的系统级 Trace 能看到所有进程、所有线程、所有 CPU 核心的活动——这是分析跨进程问题（Binder 延迟、SurfaceFlinger 合成延迟、系统服务阻塞）的必要条件。

在数据格式上，AS Profiler 使用的是 `.trace` 格式（基于 ART 的 method tracing），记录的是每个方法的调用关系和耗时。Perfetto 使用的是 `.perfetto-trace` 格式（基于 protobuf），记录的是系统级的 ftrace 事件和 atrace 事件。两者可以互补——用 AS Profiler 做 App 方法级的热点定位，用 Perfetto 做系统级的时间线分析。

另一个容易混淆的点是，AS Profiler 的 "System Trace" 模式（不是 "Java Method Trace" 模式）底层同样是 Perfetto，它抓取的就是 Perfetto 格式的 Trace，只是展示界面不同。如果需要 Perfetto 的完整分析能力，建议直接导出 Trace 文件到 ui.perfetto.dev 中查看。

[已验证: 官方文档, developer.android.com/studio/profile/cpu-profiler]

## 实战示例：快速定位掉帧原因

前面的操作、Track、详情面板、Flow Events 和颜色编码，在实际分析中通常要组合使用。可以用一个滑动卡顿场景把它们放到同一个排查流程里。

假设拿到一个用户反馈"滑动时偶尔卡一下"的 Trace。按照以下步骤可以在几分钟内定位到原因：

**第一步：按版本选入口**。Android 12+ 先在 App 进程里看 `Actual Timeline`，扫描异常颜色的帧。Android 10/11 没有 FrameTimeline 主表，就从 `Choreographer#doFrame`、`VSYNC-app` / `VSYNC-sf` 和 `SurfaceFlinger` 轨道开始，先圈出超时窗口。

**第二步：看归因字段或 fallback 线索**。Android 12+ 选中异常帧后，先看 `Jank Type`。如果是 `App Deadline Missed`，继续回到 `doFrame` 和 `RenderThread`；如果是 `SurfaceFlinger CPU Deadline Missed`、`SurfaceFlinger GPU Deadline Missed`、`SurfaceFlinger Scheduling` 或 `Display HAL`，直接把视线切到 `surfaceflinger` 进程。Android 10/11 则要靠 `doFrame`、`DrawFrame`、主线程 `thread_state` 和 SurfaceFlinger 时间窗手工拆分责任。

**第三步：看主线程**。向下滚动到 MainThread Track，找到同一时间窗里的 `Choreographer#doFrame` Slice。放大之后，先看 `CALLBACK_INPUT`、`CALLBACK_ANIMATION`、`CALLBACK_TRAVERSAL`、`CALLBACK_COMMIT` 哪一段最长。

**第四步：看线程状态颜色**。如果主线程大段是绿色，说明主要在执行 CPU 工作；灰色长，优先排查锁或 Binder 等待；红色长，点开详情里的 owner / `waking_thread` 并跳到持锁线程；深橙色长，优先排查 I/O。再结合 Wall Duration、CPU Duration、Self Time 判断瓶颈是计算、等待还是磁盘。

**第五步：继续看 RenderThread**。如果 `doFrame` 本身不长，但 `DrawFrame`、GPU work 或 fence wait 明显拉长，就把同一时间窗切到 `RenderThread`。这里要区分是 App 侧 GPU 提交慢，还是下游消费慢。

**第六步：按版本看 SurfaceFlinger**。Android 12/12L 重点检查 `onMessageReceived` / `REFRESH`；Android 13+ 重点检查 `commit` / `composite` / `present`。如果 SurfaceFlinger 侧也超时，再判断是 Client composition 增多、事务处理变重，还是显示提交阶段晚了。

通过这个流程，大部分掉帧问题都能在 5-10 分钟内定位到根因层级。剩下的是继续结合 13.5 节的专题 SQL、Android Studio Profiler 或源码做深挖。

[图：实战示例完整 Trace 片段——从 FrameTimeline 红色区域定位到 doFrame，展示各子 Slice drill-down 过程]

## 常见问题与误区

**误区一：Trace 上绿色的 Slice 就是"正常"的。** 绿色只是表示线程在运行，不代表运行得快。一个绿色 Slice 可能只有 2ms，也可能是 200ms——要看它的 Wall Duration 数值，而不是凭颜色判断。

**误区二：CPU Duration 低就说明没问题。** CPU Duration 低可能意味着大部分时间在等待——等 CPU 调度、等锁、等 I/O。等待本身也是性能问题，只是优化方向不同。

**误区三：Perfetto 可以分析方法级耗时。** Perfetto 展示的是 atrace 事件（`Trace.beginSection` 标记的代码段），不是每个方法的调用。如果需要方法级热点分析，应该使用 AS Profiler 的 Java Method Trace 或 Simpleperf（详见 14.2 节）。

**误区四：必须看懂所有 Track 才能做分析。** 日常 80% 的分析工作只涉及 3-4 个 Track：FrameTimeline、MainThread、RenderThread、SurfaceFlinger。其他 Track 在特定场景下才有价值（比如分析功耗时看 CPU Frequency，分析内存时看 Memory Counter）。

**误区五：Runnable 延迟一定是调度器的问题。** Runnable 延迟可能是因为系统负载高（很多线程在排队），也可能是因为当前线程优先级太低，还可能是因为 CPU 核心数量不够。需要结合 CPU Scheduling Track 的全局视图来判断，不能只看一个线程的 Runnable 段就下结论。

## 参考资料

- Perfetto UI 官方文档：[https://perfetto.dev/docs/visualization/perfetto-ui](https://perfetto.dev/docs/visualization/perfetto-ui)
- Perfetto UI 当前快捷键入口：`?` / Support > Keyboard shortcuts（[https://ui.perfetto.dev/](https://ui.perfetto.dev/)）
- traceconv 官方文档：[https://perfetto.dev/docs/quickstart/traceconv](https://perfetto.dev/docs/quickstart/traceconv)
- FrameTimeline 官方文档：[https://source.android.com/docs/core/display/frame_timeline](https://source.android.com/docs/core/display/frame_timeline)
- Android Performance — Perfetto 系列 3：[https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/](https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/)
- Perfetto 分析进阶（内核工匠）：[https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247487984](https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247487984)
- AOSP Trace API：`frameworks/base/core/java/android/os/Trace.java`


### Perfetto 近期版本更新要点

Perfetto 在 2025-2026 年的版本迭代中引入了多项影响分析体验的改进（基于 [Perfetto Releases](https://github.com/google/perfetto/releases)）：

- **UI 层**：暗色主题（v52 引入，v52 发布说明仍标记为 experimental）、触摸屏手势操作、多 Track 批量折叠/展开
- **分析层**：`android_anrs` 表新增 `anr_type` 字段用于 ANR 分类、`slice_self_dur` 辅助能力直接计算 Self Duration（不再需要手动减去子 Slice）、`regexp_extract()` 函数增强 SQL 文本处理
- **数据源**：`android.bitmaps` 表提供位图时序数据，可用于追踪 Bitmap 生命周期

[已验证: Perfetto GitHub Releases, github.com/google/perfetto/releases]
