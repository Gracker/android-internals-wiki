---
title: 卡顿分析方法论
chapter: '7.3'
section: '7.3'
reviewed_date: '2026-05-05'
last_task2b_at: '2026-05-05T10:47:46.821502'
reviewed_by: openclaw-task6
rework_date: '2026-04-04'
rework_by: openclaw-task2b
rework_type: review回炉修复（Task9/External 问题单）
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: '2026-03-31'
last_verified_against: AOSP android-16.0.0_r1, Perfetto 官方文档
confidence: high
sources:
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: blog
  path: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android卡顿监测的方方面面.md
- type: official
  path: https://perfetto.dev/docs/analysis/trace-probe-checks
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
tags:
- jank
- methodology
- Perfetto
- Systrace
- FrameTimeline
- FrameMetrics
- CPU
- checklist
related_chapters:
- '7.1'
- '7.2'
- '2.4'
- '2.5'
- '2.6'
- '2.18'
- '1.5'
- '13.3'
task6_state: reviewed
task6_result: pass-light-edit
task2b_result: fixed
task6_reviewed_date: '2026-05-05'
review_round: 3
status: 'finalized'
pipeline_stage: 'ready-to-publish'
task9_result: 'pass-tech-review'
task9_state: 'reviewed'
task2b_state: fixed
task9_reviewed_by: 'openclaw-task9'
task9_reviewed_date: '2026-05-13'
last_task9_at: '2026-05-13T02:51:35+08:00'
last_task9_audit: '2026-05-25'
task9_review_notes: '2026-05-05 11:20 task9 deep-review: needs-rework；P0 0 / P1 1 / P2 1。 | 2026-05-13 02:51 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；满足 task6_result=pass-light-edit 且 queue 无 pending，自动晋升 finalized / ready-to-publish。'
last_task6_at: '2026-05-05T11:05:00+08:00'
last_task6_audit: '2026-06-06'
review_notes: '2026-05-05 task6 revisit: L1/L2 小修完成；待 Task9 复审。'
---


# 卡顿分析方法论

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 流畅性问题的完整分析流程：复现 → 抓 Trace → 定位帧 → 分析主线程/RenderThread/SF
- 🔹 Perfetto 中定位 Jank 帧的方法：FrameTimeline、Expected vs Actual
- 🔹 Systrace 中关键标记的解读：doFrame、DrawFrame、SurfaceFlinger onMessageReceived
- 🔹 CPU 调度问题导致的 Jank：识别 Runnable 过长、Uninterruptible Sleep
- 🔹 分析模板：标准化的 Jank 分析 Checklist

### 扩展（可选深入）

- 🔸 FrameMetrics API 在线上监控中的应用
- 🔸 使用 SQL 查询 Perfetto Trace 进行批量分析

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要掌握一套分析方法论

卡顿分析这件事，最怕的是"看错方向"。

我们在 Perfetto 里打开一份 Trace，面对密密麻麻的色块，很容易陷入一种"漫无目的地找红色"的状态——看到哪帧红了就点进去，看到一个耗时的 Slice 就去追，追了半天发现是个无关紧要的日志打印。更糟糕的情况是，明明用户反馈了"滑动卡"，抓了 Trace 却找不到任何异常帧，因为卡顿的原因不在 App 进程里，而在系统的 CPU 调度或者 SurfaceFlinger 的合成环节。

因此需要一套稳定的分析流程。它是一个有经验的工程师面对卡顿问题时脑子里的决策路径：先判断问题类型，再确定分析工具，然后沿着正确的路径追踪，最终定位到根因。掌握这套方法，拿到一份 Trace 后应该在 10 分钟内给出初步结论——是 App 自身的问题还是系统环境的问题，瓶颈在主线程还是渲染线程还是 GPU，是代码执行慢还是 CPU 没给够。

本节的内容基于大量的实战经验总结。其中分析流程和方法论框架主要参考了高爷在 androidperformance.com 上的 Systrace 流畅性实战系列文章 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md] [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md]，以及 Perfetto 系列中关于 Trace 解读的方法 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md]。

## 流畅性问题的完整分析流程

### 第一步：明确问题现象和背景

在动手抓 Trace 之前，先搞清楚几个关键信息。这一步经常被跳过，但它直接决定了后续分析的效率。

第一步是区分用户说的"卡"属于哪种类型。用户的"卡"和开发人员的"卡"不是一回事——用户觉得"滑动的时候一卡一卡的"是流畅度问题，"点了图标半天没反应"是响应速度问题，"界面卡住了然后弹了关闭对话框"是 ANR（稳定性问题）。这三类问题在技术上的根源虽然都和主线程执行超时有关，但分析路径完全不同。本章只讨论流畅度问题，响应速度和 ANR 分别在第八章和第九章讨论。

确认是流畅度问题后，接下来需要了解：复现概率是多少？是否只在特定机型或特定场景下出现？竞品在同样的操作下是否也卡？这些信息决定了分析重心应该放在 App 自身还是系统环境上。如果竞品同样操作不卡，那基本可以排除硬件瓶颈；如果只在低端机上出现，可能是 CPU 调度问题。

### 第二步：抓取合适的 Trace

复现问题后，用 Perfetto 抓取 Trace。抓取时的配置很关键——配置不对，可能抓不到分析所需的信息。

对于流畅度分析，至少需要以下数据源 [已验证: 官方文档 perfetto.dev]：

```protobuf
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "sched/sched_wakeup"
            ftrace_events: "sched/sched_waking"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            atrace_categories: "gfx"
            atrace_categories: "view"
            atrace_categories: "input"
            atrace_categories: "wm"
            atrace_categories: "am"
            atrace_categories: "dalvik"
        }
    }
}

data_sources: {
    config {
        name: "android.surfaceflinger.frametimeline"
    }
}
```

这里有几个要点。`gfx` category 涵盖了 SurfaceFlinger 和渲染相关的 atrace 标记；`view` 涵盖了 Choreographer、doFrame 等 UI 渲染标记；`input` 涵盖了触摸事件的分发；`sched_switch` 和 `sched_wakeup` 则是分析 CPU 调度问题必不可少的 ftrace 事件。FrameTimeline 由 `android.surfaceflinger.frametimeline` 数据源提供，它不属于 `gfx` 或 `view` atrace category；后文要在 Perfetto UI 查看 Expected / Actual Timeline，或用 SQL 查询 `actual_frame_timeline_slice`、`expected_frame_timeline_slice`，trace 里必须包含这个数据源。如果遗漏了 `sched` 相关事件，当主线程长时间处于 Sleep 状态时，就无法追踪唤醒路径，分析就断线了。

抓取时长也有讲究。如果问题容易复现，抓 5-10 秒就够了——太长的 Trace 反而增加定位的难度。如果问题偶尔出现，可以适当加长到 30 秒甚至更长，但要相应增大 buffer 大小。

### 第三步：在 Trace 中定位问题帧

打开 Trace 后的第一步是看全局环境 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md]，确认环境正常后再进入帧级定位 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md]。

在 Perfetto 顶部的 CPU 区域扫一眼：CPU 频率是否正常（有没有被温控压低），整体负载是否很高（是不是高负载场景），有没有频繁的 CPU 迁移。这些信息能帮助快速判断是"App 自己慢"还是"系统环境差导致 App 被拖累"。

然后进入 App 进程，定位到主线程（MainThread）和渲染线程（RenderThread）。在 Perfetto 中，主线程上方有一个 Frame 标记行，每个帧会根据耗时被标记为不同颜色：

- **绿帧**：在一个 VSync 周期内完成，正常帧
- **黄帧**：超过一个 VSync 周期但不到两个，可能有问题
- **红帧**：超过两个 VSync 周期，大概率有问题

[已验证: Perfetto FrameTimeline 功能在 Android 12 (S) 及以上版本可用, developer.android.com]

**单看主线程的帧颜色，不能确定是否产生用户可见掉帧**。在 [流畅性实战 3](https://www.androidperformance.com/2021/04/24/android-systrace-smooth-in-action-3/) 中，高爷详细解释了为什么会出现"黄帧但不掉帧"和"黄帧且掉帧"两种情况。原因是 Android 的多缓冲机制（Triple Buffer 或更多 Buffer）提供了缓冲空间——即使 App 某一帧画得慢了一点，只要 BufferQueue 中还有之前准备好但未消费的帧，屏幕上就不会出现空白，用户也就感知不到卡顿 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md]。

所以，**判断掉帧是否会被用户感知，必须看 SurfaceFlinger**。

### 第四步：确认掉帧是否会被用户感知——看 SurfaceFlinger

要确认一帧是否会导致用户可见卡顿，需要切换到 SurfaceFlinger 进程看两个东西 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md]：

第一，看 App 对应的 BufferQueue 中 Buffer 的状态。如果在某个 VSync-sf 周期内，SurfaceFlinger 要合成这一帧却发现 BufferQueue 里没有可用的 Buffer（即 App 还没画完），那这一帧就会被丢掉。

第二，看 SurfaceFlinger 主线程在 VSync-sf 到来时是否执行了合成。如果 SurfaceFlinger 在某个 VSync 周期没有合成操作，而 App 侧仍在渲染，但 BufferQueue 为空——这就是卡顿的铁证。

在 Perfetto 中，可以把 App 的 MainThread、RenderThread 和 SurfaceFlinger 主线程 Pin 到一起（点击线程名左边的图钉按钮），这样就能在同一个视图中看到三者之间的时间关系 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md]。高爷在文章中提到，这是他日常分析掉帧问题最常用的技巧——把从 App 到 SF 的关键线程放在一起，一眼就能看出是 App 画得慢还是 SF 合成慢。

[待补充：Trace 截图 — 主线程、RenderThread、SurfaceFlinger 三线程 Pin 在一起的视图，标注掉帧处 BufferQueue 为空的时刻]

### 第五步：分析根因

确认了掉帧之后，下一步要回答：**这帧为什么画得慢？**

根据耗时发生在哪个线程，分析方向完全不同：

如果耗时在**主线程**（doFrame 的 Input、Animation、Insets Animation、Traversal、Commit 阶段拉长），可能的原因包括：布局过于复杂（measure/layout 耗时）、View 数量过多、在主线程做了 I/O 操作、大量的对象创建导致 GC、Binder 调用阻塞、锁竞争等。

如果耗时在**渲染线程**（DrawFrame 阶段拉长），可能的原因包括：绘制命令过于复杂（大量 Path 操作、阴影效果）、GPU 负载过重、CPU 跑在了小核或频率过低。

如果主线程和渲染线程看起来都不慢，但帧还是没画完，那就需要看**调度问题**——CPU 有没有及时把时间片分配给对应线程。这部分在后面"CPU 调度问题导致的 Jank"中详细展开。

## Perfetto 中定位 Jank 帧的方法：FrameTimeline、Expected vs Actual

上面讲的是"看帧颜色 + 看 SurfaceFlinger"的经典方法。在 Android 12 及以上版本，Perfetto 提供了一个更精确的工具：**FrameTimeline**。

### FrameTimeline：Expected vs Actual

FrameTimeline 是 Android 12 引入的一套帧时间线追踪机制，它在 Perfetto 中展示为两个并排的 Track：**Expected Timeline** 和 **Actual Timeline** [已验证: 官方文档 perfetto.dev, Android 12+]。它只在 Android 12 及以上版本可用，而且当前不覆盖 SurfaceView。分析普通 View 或 TextureView 场景，可以直接依赖这组轨道；分析 SurfaceView、游戏或视频播放场景时，要回到 BufferQueue 的 buffered frames、`gpu.renderstages` 轨道，以及引擎侧的 Swappy stats。

Expected Timeline 展示的是系统为这一帧分配的时间预算。每一帧在 Choreographer 回调被调度时，系统就计算好了这一帧"应该"在什么时间完成渲染、什么时候被 SurfaceFlinger 合成、什么时候最终显示在屏幕上。这个预算基于当前的 VSync 信号周期和 offset 配置。

Android 15-QPR1+ 引入 Adaptive Refresh Rate 后，Expected Timeline 的预算会跟当前显示节奏一起变化。分析这类 Trace 时，不要按 60Hz/120Hz 固定阈值硬套。优先读取这一帧对应的 Expected Slice 宽度，再把 App FrameTimeline、SurfaceFlinger FrameTimeline、Display/VSYNC 轨道和 token 放在同一时间窗核对：如果 Expected 本身已经变成 33.3ms 或更长，Actual 在该窗口内完成，通常属于正常降频；如果 Expected 很窄而 Actual 溢出，再按掉帧继续追主线程、RenderThread、GPU 或 SurfaceFlinger。动态刷新率的策略与适配见 [2.18 Adaptive Refresh Rate 与动态帧率控制](../../part1-fundamentals/ch02-rendering/18-adaptive-refresh-rate.md)。

Actual Timeline 展示的是这一帧实际执行的过程。从 Choreographer 的 doFrame 开始，到 RenderThread 完成绘制，到 SurfaceFlinger 完成合成，每一个环节的实际耗时都如实记录。主线程归因时不要只盯 Input / Animation / Traversal 三段，现代 Android 的 doFrame 常见顺序还包括 `CALLBACK_INSETS_ANIMATION` 与 `CALLBACK_COMMIT`，完整视角应该是 Input → Animation → Insets Animation → Traversal → Commit。前者承接系统栏、IME 等 Insets 动画，后者负责提交后的收尾和时间信息修正。

当 Actual 的某个 Slice 超过了对应的 Expected Slice，就意味着这个环节出现了延迟。在 Perfetto UI 中，超时的帧会被标记为红色，一目了然。

[待补充：Trace 截图 — Perfetto 中 FrameTimeline 的 Expected vs Actual Track 对比图，标注红色超时帧]

FrameTimeline 的核心价值是：它把"是否卡顿"的判断标准化了。不再需要人工去对比帧颜色和 BufferQueue 状态。FrameTimeline 直接展示每一帧有没有超时、在哪个环节超时、超了多少。它同时覆盖了 App 侧（doFrame + RenderThread）和 SurfaceFlinger 侧（合成），用同一个 token 关联起来，可以在 Perfetto 中通过点击 Slice 直接跳转到对应的 App 或 SF 帧 [已验证: perfetto.dev Trace Processor 文档]。

### Systrace 中关键标记的解读：doFrame、DrawFrame、SurfaceFlinger onMessageReceived

如果分析的设备还在 Android 11 或更早的版本，没有 FrameTimeline Track，可以回到经典方法：看主线程上方的帧颜色标记 + SurfaceFlinger 的 BufferQueue 状态。这套方法虽然繁琐一些，但逻辑上是等价的——都是在回答"这一帧有没有在 VSync 周期内完成"这个问题。

在 Systrace 中（Perfetto 的前身），关键的标记包括 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md]：

- **Choreographer#doFrame**：主线程处理一帧的入口。现代 Android 常见的回调顺序是 Input → Animation → Insets Animation → Traversal → Commit，分别对应输入、普通动画、Insets 动画、measure/layout/draw 与提交后的收尾
- **DrawFrame**：渲染线程的绘制入口，将主线程构建的 DisplayList 转化为 GPU 指令
- **SurfaceFlinger#onMessageReceived**：SurfaceFlinger 在 VSync-sf 到来时执行合成的入口，可以确认 SF 是否处理了这一帧

这三个标记在 Perfetto 中同样存在（因为底层用的都是 atrace），只是呈现形式略有不同。

## CPU 调度问题导致的 Jank：最容易被忽略的根因

很多工程师在分析卡顿时有一个盲区：只关注线程在 Running 时做了什么，不关注线程在"等待 Running"时发生了什么。

在 Perfetto 中，线程的状态用不同的颜色表示。Running（绿色）是正在执行，Sleep（灰色）是等待事件，Runnable（蓝色）是准备好执行但还没被调度上 CPU，Uninterruptible Sleep（深橙色）是在等待 I/O 且不可中断。对于流畅性分析，最值得关注的是 Runnable 和 Uninterruptible Sleep 这两种状态。

[待补充：Trace 截图 — Perfetto 线程状态颜色图例，标注 Running（绿）、Runnable（蓝）、Sleep（灰）、Uninterruptible Sleep（深橙）]

### Runnable 过长：CPU 没空理你

Runnable 状态表示线程已经准备好执行，正在排队等 CPU 分配时间片。如果一段任务前面有一段很长的蓝色（Runnable），意味着线程虽然被唤醒了，但 CPU 在忙别的事情，没顾上执行它。

在 Perfetto 中，通过点击 Runnable 状态可以查看唤醒源（Waker），了解是谁唤醒了这个线程 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md]。更强大的功能是 **Critical Path**——Perfetto 会自动追踪与当前任务有依赖关系的整条依赖路径。点击一个 Running 状态，在下方信息区点击 "Critical path"，就能看到从最初唤醒到当前执行的全部依赖关系。

高爷在 Perfetto 系列第三篇中详细介绍了这个功能的用法 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md]：比如想追踪 RenderThread 的唤醒路径：点击 Running 前面的 Runnable 状态，在下方信息区的 Related thread states 中就能看到 Waker 信息。连续追踪，就能还原出完整的唤醒路径：SurfaceFlinger → MainThread → RenderThread。

[待补充：Trace 截图 — Critical Path 功能演示，展示从 SF 唤醒到 RT 执行的完整依赖链]

Runnable 过长的典型场景包括：整机高负载（所有核心都满了，目标线程排不上队）、CPU 频率过低（任务虽然被调度上去了但执行慢）、线程被调度到了小核（大核被其他高优先级任务占满）。

### Uninterruptible Sleep：I/O 阻塞

Uninterruptible Sleep 状态（在 Perfetto 中显示为深橙色）表示线程在等待 I/O 操作完成且不能被信号中断。这在流畅性分析中经常出现，尤其是在低内存场景下。

当系统内存紧张时，App 在主线程执行过程中可能触发 page fault（访问的内存页被回收了），需要从磁盘或 ZRAM 中把数据读回来。这个过程中主线程就处于 Uninterruptible Sleep 状态，看起来像是"卡住了但没有执行业务代码"。在 Perfetto 中，如果主线程出现大量深橙色片段，且时间点恰好与 kswapd（内核内存回收线程）或 lmkd（Low Memory Killer）的活动重合，那基本可以确定是低内存导致的 I/O 阻塞 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]。


<!-- AIW-源码调研-2026-04-20: Android TrimMemory 机制补充 -->
#### TrimMemory 机制与 Jank 的关联（源码级补充）

上述低内存导致的 Uninterruptible Sleep 背后，是一条从内核 PSI 监控到应用组件回调的完整路径。Android 14 源码验证了以下关键细节：

**lmkd 的 PSI 监控（Android 10+ 默认）**：lmkd（Low Memory Killer Daemon）已从 C 实现迁移至 C++（`platform/system/memory/lmkd/lmkd.cpp`），默认使用内核 PSI（Pressure Stall Information）监控内存压力，相比旧版 `vmpressure` 更准确反映任务阻塞延迟。关键参数：`PSI_WINDOW_SIZE_MS=1000`（窗口大小），`PSI_POLL_PERIOD_SHORT_MS=10`（高压力时轮询周期）。AMS 与 lmkd 通过 socket 通信，命令码定义在 `ProcessList.java`（`LMK_TARGET=0`、`LMK_PROCPRIO=1`、`LMK_PROCREMOVE=2`、`LMK_PROCKILL=6` 等）。

**OOM Adj 分数体系**（`services/core/java/com/android/server/am/ProcessList.java`）：FOREGROUND_APP_ADJ=0（前台）到 CACHED_APP_MAX_ADJ=999（缓存进程上限）。`mOomMinFree` 数组定义内存阈值，当可用内存低于阈值时，同档 oom_adj 及以上的进程成为候选杀死目标。

**TrimMemory 完整调用链**：lmkd 判断需要回收内存 → AMS `appTrimMemory()` 计算 trim level（`TRIM_MEMORY_RUNNING_MODERATE=5` ~ `TRIM_MEMORY_COMPLETE=80`，定义在 `ComponentCallbacks2.java`）→ `IApplicationThread.scheduleTrimMemory(level)` → `ActivityThread.handleTrimMemory()` → 遍历所有 `ComponentCallbacks2` 实例逐一调用 `onTrimMemory(level)`。

**Perfetto 追踪点**：通过 Perfetto stdlib 查询 LMK 事件：`INCLUDE PERFETTO MODULE android.memory.lmk;` 后查询 `android_lmk_events` 表。底层采集路径因版本而异：2025+ 使用 instant `lowmemorykiller` track；2021-2025 使用 `lmk,...` ATrace slice；更早版本使用 `kill_one_process` counter 或 legacy kernel ftrace `lowmemorykiller/lowmemory_kill`。kswapd/lmkd 在时间线上密集出现，配合 `TRIM_MEMORY_*` 级别应用回调，是判断低内存导致 Jank 的直接证据。

[源码验证: ComponentCallbacks2.java (android14-release), ProcessList.java (android14-release), lmkd.cpp (android-14.0.0_r44)]

### 分析 CPU 调度问题的工具技巧

在 Perfetto 中分析 CPU 调度问题，有几个非常实用的技巧 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-03-how-to-analysis-perfetto.md] [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]：

**Pin 线程到顶部**：把最关注的线程（如 MainThread、RenderThread、SurfaceFlinger 主线程）Pin 到一起，方便在一个视图中对比它们的状态变化。这是分析掉帧问题时最常用的操作。

**CPU Info 区域的 Task 高亮**：在 CPU 区域把鼠标悬停在某个 Task 上，该 Task 所属线程的所有 Task 都会高亮显示。用这个方法可以快速判断线程是否在大小核之间频繁迁移——如果渲染线程的任务分散在各个核心上，特别是跑到小核上去了，就可能导致渲染超时。

**查看唤醒延迟**：Perfetto 的信息区会自动计算唤醒延迟（从线程被唤醒到进入 Running 的时间）。如果这个延迟超过 1-2ms，就需要关注了——在 120fps 设备上，一个 VSync 周期才 8.3ms，调度延迟吃掉 2ms 就很可观了。

**CPU 频率追踪**：在 CPU Frequency Track 展示每个核心的频率变化。如果发现关键线程运行时 CPU 频率很低（比如被温控限制到了最低频率），那就是性能瓶颈的直接证据。

## 标准化 Jank 分析 Checklist

经过前面的分析，我们把卡顿分析浓缩成一个可执行的分析模板。它是一个有经验的工程师面对卡顿问题时的思考框架——每次分析都可以沿着走一遍，确保不遗漏关键环节。

### 第一阶段：环境排查（1-2 分钟）

- [ ] CPU 频率是否正常？有没有被温控压低？
- [ ] 整体 CPU 负载如何？是否处于高负载场景？
- [ ] 是否有大量内存回收活动（kswapd/lmkd 频繁出现）？
- [ ] 是否有频繁的 I/O 阻塞（Uninterruptible Sleep 增多）？
- [ ] 设备是否开启了 VRR/ARR？刷新率是否在分析窗口内发生变化？（检查 VSYNC 轨道的间隔变化）

如果环境排查就发现了问题（比如 CPU 被压到了最低频率），那后续的帧级分析可能就不那么重要了——先解决环境问题。

### 第二阶段：帧级定位（3-5 分钟）

- [ ] 找到 App 主线程上方的 Frame 行，标记黄帧和红帧
- [ ] 切换到 SurfaceFlinger，确认这些帧是否会被用户感知为掉帧
- [ ] 如果有 FrameTimeline Track（Android 12+），直接看 Expected vs Actual 的差异——**不要用固定 16.67ms/8.33ms 阈值**，以 Expected Slice 宽度为准
- [ ] 记录掉帧的时间点和持续时长

### 第三阶段：线程级分析（5-10 分钟）

对每一个确认掉帧的帧，分析耗时发生在哪个环节：

- [ ] **主线程 doFrame**：耗时是否超过 VSync 周期？如果是，哪个阶段（Input / Animation / Insets Animation / Traversal / Commit）最耗时？
- [ ] **渲染线程 DrawFrame**：耗时是否过长？GPU 负载如何？
- [ ] **主线程等待渲染线程**：主线程有没有因为 syncFrameState 阻塞在等待渲染线程？如果是，说明前一帧的渲染还没完成 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md]
- [ ] **Binder 调用**：主线程有没有被 Binder 调用阻塞？点击 Binder Slice 会显示对端进程

### 第四阶段：调度级排查（3-5 分钟）

如果线程级分析没有发现明显的代码执行问题，就查调度：

- [ ] 关键线程（MainThread、RenderThread）有没有过长的 Runnable 状态？
- [ ] 有没有 Uninterruptible Sleep？如果有，是在等什么 I/O？
- [ ] 线程是否被调度到了小核？用 CPU 区域的 Task 高亮查看
- [ ] 唤醒路径是否正常？用 Critical Path 追踪唤醒依赖

### 第五阶段：得出结论

经过前面四个阶段的分析，应该能得出以下结论之一：

1. **App 自身问题**：主线程或渲染线程有明确的耗时操作，可以对应到具体的代码路径
2. **系统环境问题**：CPU 调度不给力、内存紧张导致频繁 GC 和 I/O 阻塞、温控降频
3. **设计问题**：需要在架构层面调整，比如把耗时操作从主线程移到子线程、减少布局层级、优化绘制逻辑

回到开头的问题——"拿到 Trace 后从哪里下手"——经过这五个阶段，答案应该已经清晰了。

[自动发现: 来源 obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md] 腾讯音乐技术团队在 Wesing（全民 K 歌国际版）的卡顿治理实践中，总结了一套"横纵结合"的分析方法：横向看一个阶段内所有方法调用的时序分布（用 CPU Profiler），纵向看单个方法在不同条件下的耗时变化。这种"先定位帧，再定位方法，再定位场景"的三级逐层深入思路，和我们的 Checklist 框架是一致的。

## FrameMetrics API：线上卡顿监控的基石

前面的分析都是基于 Trace 文件的线下分析。在生产环境中，我们不可能给每个用户抓 Trace——线上监控需要一种更轻量的方式来度量帧的性能。Android 提供的 **FrameMetrics API**（Android 7.0+, API 24）就是为这个目的设计的 [已验证: 官方文档 developer.android.com, android.view.FrameMetrics]。

### FrameMetrics 的工作原理

向 Window 注册一个 `OnFrameMetricsAvailableListener`，系统就会在每一帧渲染完成后触发回调，提供这一帧各个环节的耗时数据。

```java
// [已验证: 官方文档 developer.android.com, android.view.Window#addOnFrameMetricsAvailableListener]
window.addOnFrameMetricsAvailableListener(
    (window, frameMetrics, dropCountSinceLastInvocation) -> {
        // 获取各阶段耗时（单位：纳秒）
        long totalDuration = frameMetrics.getMetric(FrameMetrics.TOTAL_DURATION);
        long drawDuration = frameMetrics.getMetric(FrameMetrics.DRAW_DURATION);
        long layoutDuration = frameMetrics.getMetric(FrameMetrics.LAYOUT_MEASURE_DURATION);
        long syncDuration = frameMetrics.getMetric(FrameMetrics.SYNC_DURATION);

        // 判断是否卡顿：总耗时是否超过一帧的 deadline
        long deadline;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {  // API 31+
            deadline = frameMetrics.getMetric(FrameMetrics.DEADLINE);
        } else {
            // 回退：根据显示屏刷新率计算 deadline
            // 60Hz → 16,666,667 ns, 90Hz → 11,111,111 ns, 120Hz → 8,333,333 ns
            float refreshRate = window.getContext().getSystemService(DisplayManager.class)
                    .getDisplay(Display.DEFAULT_DISPLAY).getRefreshRate();
            deadline = (long) (1_000_000_000.0 / refreshRate);
        }

        if (totalDuration > deadline) {
            // 记录卡顿帧的详细信息
            logJankFrame(totalDuration, drawDuration, layoutDuration, syncDuration);
        }
    },
    handler // 指定回调的 Handler
);
```

FrameMetrics 常量按版本分批引入：

| 常量 | 引入版本 | 用途 |
|:---|:---|:---|
| `TOTAL_DURATION` / `DRAW_DURATION` / `LAYOUT_MEASURE_DURATION` / `SYNC_DURATION` / `HANDLE_INPUT_DURATION` / `ANIMATION_DURATION` / `SWAP_BUFFERS_DURATION` / `INTENDED_VSYNC_TIMESTAMP` / `FIRST_DRAW_FRAME` | API 24 (Android 7.0) | 基础帧阶段指标 |
| `VSYNC_TIMESTAMP` | API 26 (Android 8.0) | 实际 VSync 时间戳，可精确还原帧提交时机 |
| `DEADLINE` / `GPU_DURATION` | API 31 (Android 12) | 系统计算的帧截止时间 / GPU 渲染耗时 |
| `FRAME_TIMELINE_VSYNC_ID` | API 36 (Android 16) | 帧与 Perfetto FrameTimeline token 的关联键，用于线上帧数据与 Trace 帧时间线对齐 |

版本兼容性的边界需要写清楚。`FrameMetrics.DEADLINE` 是 Android 12（API 31）才引入的常量。更早版本只能自己按刷新率估一个 budget，例如 60Hz≈16.6ms、90Hz≈11.1ms、120Hz≈8.3ms。这个估算只能拿来做粗筛，不能把它当成系统真实 deadline。原因有两点，一是系统侧的 `DEADLINE` 会把 VSync offset 和当前帧率策略算进去，二是多缓冲会在部分瞬时波动里留出缓冲空间。手工公式看不到这些边界，适合做趋势告警，不适合给单帧下绝对结论。[已确认: developer.android.com/reference/android/view/FrameMetrics, DEADLINE 从 API 31 引入]

关键指标说明：

- **TOTAL_DURATION**：一帧从 Choreographer 回调开始到 GPU 完成渲染的总耗时。这是判断是否卡顿的核心指标。
- **DEADLINE**：这一帧的预算时间。对于 60fps 设备是 16.6ms，120fps 设备是 8.3ms。将 TOTAL_DURATION 与 DEADLINE 比较，比硬编码 16.6ms 更准确——因为不同设备可能运行不同的帧率 [已验证: developer.android.com]。
- **DRAW_DURATION**：RenderThread 执行绘制命令的耗时。如果这个值异常大，可能是绘制逻辑过于复杂。
- **LAYOUT_MEASURE_DURATION**：主线程 measure 和 layout 的耗时。如果这个值大，说明布局层级太深或布局逻辑太复杂。
- **SYNC_DURATION**：主线程将绘制信息同步到 RenderThread 的耗时。正常情况下很短（< 1ms），如果异常增大，说明 DisplayList 非常大。

### FrameMetrics 与 Trace 分析的定位差异

FrameMetrics 和 Trace 分析解决的是不同层面的问题：FrameMetrics 是"度量"工具，展示"有卡顿、卡了多少"；Trace 是"诊断"工具，展示"为什么卡"。两者是互补关系，不是替代关系。

典型的线上监控流程是：用 FrameMetrics 采集卡顿帧的统计数据（总耗时、各阶段耗时），聚合后上报到监控平台；当发现某个版本的卡顿率异常升高时，再回到线下用 Perfetto 抓 Trace 进行深入分析。

### JankStats：Google 的官方封装

Google 在 2022 年推出了 **JankStats** 库（`androidx.metrics:metrics-performance`），它封装了 FrameMetrics API，提供了更易用的接口 [已验证: 官方文档 developer.android.com]：

- API 24+ 采 FrameMetrics，早期版本用 OnPreDrawListener 回退；`JankStatsApi31Impl` 额外提供 total duration 和 overrun 等扩展字段
- `isJank` 判定基于 UI duration 与 expected duration 的比较，后者受 `jankHeuristicMultiplier` 影响——不是简单的 `TOTAL_DURATION > DEADLINE`，`TOTAL_DURATION - DEADLINE` 只是 `frameOverrunNanos` 字段的语义
- 支持附加 UI 状态信息（当前页面、操作类型），方便在监控平台上按场景聚合
- 提供可配置的卡顿判定阈值

JankStats 降低了线上卡顿监控的接入成本，但它的判定逻辑与手写 FrameMetrics 判断不完全等价——`jankHeuristicMultiplier` 会在系统 deadline 基础上做偏移调整，且 API 24 与 API 31 实现的判断路径不同。

[自动发现: 来源 obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android卡顿监测的方方面面.md] 业界的卡顿监测方案还包括基于 Handler 消息执行时间的监测（如 BlockCanary、Matrix）和基于 Choreographer 回调间隔的监测。这些方案的优势在于可以在卡顿发生时抓取主线程的调用栈，帮助定位具体的代码路径；劣势在于采样精度不如 FrameMetrics，且有一定的性能开销。如果团队已有成熟的 APM 框架，可以将 FrameMetrics 数据和堆栈采集结合起来，实现更完整的线上卡顿诊断能力。

## [自动发现] 线上动态 Trace：Perfetto SDK 方案

对于偶发性卡顿——线下难以复现、用户侧低概率触发——传统的"复现→抓 Trace"流程容易失效。`androidx.tracing:tracing-perfetto` 的边界是：它主要把 App 内的 trace section 写入 Perfetto，便于线下或平台侧 Trace 看到 App 自己标记的阶段；它不能替代平台侧 `perfetto` 进程去回溯系统 ftrace、atrace category 和 FrameTimeline。

工程上常见做法分两层：线上用 JankStats / FrameMetrics 发现异常场景并记录页面、操作、版本、设备状态；需要现场 Trace 时，在可控测试包、dogfood 包或平台测试环境里保持一段 ring buffer Perfetto session，触发后 stop/save。App 自身要补充更细的业务阶段标记，可以接入 Perfetto C++ SDK 的 Track Event 数据源。最小模式如下：

```cpp
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include <perfetto.h>

PERFETTO_DEFINE_CATEGORIES(
    perfetto::Category("android.jank")
        .SetDescription("Jank capture points"));
PERFETTO_TRACK_EVENT_STATIC_STORAGE();

void InitPerfettoTracing() {
    perfetto::TracingInitArgs args;
    // kSystemBackend 接入系统 tracing service；权限不足或只做进程内标记时用 kInProcessBackend。
    args.backends = perfetto::kSystemBackend;
    perfetto::Tracing::Initialize(args);
    perfetto::TrackEvent::Register();
}

std::unique_ptr<perfetto::TracingSession> StartAppTraceSession() {
    perfetto::TraceConfig config;
    config.add_buffers()->set_size_kb(32768);

    perfetto::TraceConfig::DataSource* data_source = config.add_data_sources();
    data_source->mutable_config()->set_name("track_event");

    auto session = perfetto::Tracing::NewTrace();
    session->Setup(config);
    session->StartBlocking();
    return session;
}

void StopAndSaveTrace(perfetto::TracingSession* session,
                      const std::string& path) {
    session->StopBlocking();
    std::vector<char> trace = session->ReadTraceBlocking();
    std::ofstream output(path, std::ios::binary);
    output.write(trace.data(), static_cast<std::streamsize>(trace.size()));
}
```

使用时在关键路径加 `TRACE_EVENT("android.jank", "FeedBindViewHolder")` 这类标记。JankStats 发现异常后保存业务上下文；Trace 文件由测试框架或平台侧 session 导出，再和 FrameMetrics 的帧统计一起分析。

> **注意**：ftrace 事件、atrace category、FrameTimeline 这些系统数据源由平台 tracing service 采集，第三方 App 不能假设自己能随时开启并回溯完整系统 Trace。实际 API 和权限边界以 Perfetto SDK 官方文档为准：https://perfetto.dev/docs/instrumentation/tracing-sdk 。

[来源: Perfetto SDK 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk；AndroidX 官方库, androidx.tracing:tracing-perfetto]

## 使用 SQL 查询 Perfetto Trace 进行批量分析

手动在 Perfetto UI 中一帧一帧地点击分析，适合定位具体问题。但有时候我们需要更宏观的视角：比如"这次滑动总共掉了多少帧"、"哪些帧的调度延迟最大"、"各个线程的 CPU 占用分布如何"。这种批量分析场景，Perfetto 的 SQL 查询功能就能派上用场 [已验证: 官方文档 perfetto.dev]。

Perfetto UI 右侧面板中有一个 Query 入口，可以直接编写 SQL 查询 Trace 数据库。以下是一些常用的卡顿分析查询。

### 查询掉帧统计

**推荐方法：基于 FrameTimeline Expected/Actual 对比**（Android 12+，适用于所有刷新率包括 VRR/ARR）

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

-- 基于 FrameTimeline 的掉帧统计，自动适配 VRR/ARR 动态帧间隔
-- Expected vs Actual 对比是判断掉帧的基准，不要用固定阈值
WITH frame_timeline AS (
    SELECT
        actual.upid,
        process.name AS process_name,
        actual.layer_name,
        actual.display_frame_token,
        actual.surface_frame_token,
        actual.ts,
        expected.dur AS expected_dur_ns,
        actual.dur AS actual_dur_ns,
        actual.present_type,
        actual.jank_type,
        actual.on_time_finish
    FROM actual_frame_timeline_slice AS actual
    LEFT JOIN expected_frame_timeline_slice AS expected
      ON actual.display_frame_token = expected.display_frame_token
     AND IFNULL(actual.surface_frame_token, -1) = IFNULL(expected.surface_frame_token, -1)
    LEFT JOIN process
      ON actual.upid = process.upid
)
SELECT
    process_name,
    layer_name,
    display_frame_token,
    surface_frame_token,
    ts,
    expected_dur_ns / 1000000.0 AS expected_ms,
    actual_dur_ns / 1000000.0 AS actual_ms,
    (actual_dur_ns - expected_dur_ns) / 1000000.0 AS overrun_ms,
    present_type,
    jank_type
FROM frame_timeline
WHERE (on_time_finish = 0 OR jank_type != 'None')
  -- AND process_name = 'com.example.app'
ORDER BY overrun_ms DESC
LIMIT 50;
```

这条查询直接使用 Perfetto FrameTimeline 表：`expected_frame_timeline_slice` 给出目标时间窗，`actual_frame_timeline_slice` 给出真实完成情况和 `jank_type`。配对同一帧时用 `display_frame_token`，Surface frame 再补 `surface_frame_token`；不要从通用 `slice` 表按 `Expected%` / `Actual%` 名称猜测，也不要把 `track_id` 当成帧标识。FrameTimeline 的 Expected Slice 宽度直接来自系统调度器的 `frameIntervalNs`，在 VRR/ARR 设备上会随刷新率档位变化。用 Expected 宽度做基准，不需要猜测当前是 60Hz 还是 120Hz。

**60Hz 快速粗筛**（仅适用于确认固定 60Hz 的 trace）：

```sql
-- 仅适用于确认固定 60Hz 的 trace，VRR 设备请用上面的 FrameTimeline 查询
WITH params AS (
    SELECT 16666667 AS frame_budget_ns
)
SELECT
    slice.name,
    slice.ts,
    slice.dur / 1000000.0 AS frame_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
CROSS JOIN params
WHERE thread.name = 'main'
  AND slice.name LIKE 'Choreographer#doFrame%'
  AND slice.dur > params.frame_budget_ns
ORDER BY slice.dur DESC
LIMIT 50;
```

这条查询只适合 60Hz trace 的快速粗筛，不等同于最终呈现掉帧。90Hz、120Hz 或自适应刷新率场景要把 budget 改成对应显示模式的 frame deadline。Android 12+ 应优先使用 FrameTimeline 的 Expected / Actual timeline 做判断，API 31+ 线上侧再结合 `FrameMetrics.DEADLINE`。

### 查询各线程 CPU 时间占比

```sql
-- 查询目标进程中各线程的 CPU 时间占用
SELECT
    thread.name as thread_name,
    SUM(sched.dur) / 1000000.0 as cpu_time_ms,
    COUNT(*) as sched_count
FROM sched
JOIN thread ON sched.utid = thread.utid
WHERE thread.name IN ('main', 'RenderThread', 'AsyncTask #1')
GROUP BY thread.name
ORDER BY cpu_time_ms DESC;
```

### 查询被明确抢占时间最长的 Runnable 片段

```sql
-- [已确认: Perfetto 中 sched.end_state = 'R+' 表示 Runnable (Preempted)，
-- 'R' 只表示线程被切出 CPU 时仍处于 runnable 状态。]
SELECT
    sched.ts,
    sched.dur / 1000000.0 as runnable_ms,
    thread.name as thread_name
FROM sched
JOIN thread ON sched.utid = thread.utid
WHERE thread.name = 'main'
    AND sched.end_state = 'R+'  -- Runnable (Preempted)
ORDER BY sched.dur DESC
LIMIT 20;
```

注意这个查询和调度延迟的区别。`sched.end_state = 'R+'` 找的是线程正在 CPU 上执行、随后被更高优先级任务或中断打断的片段；`sched.end_state = 'R'` 只说明线程被切出 CPU 时仍然 runnable，不等同于明确抢占。这个值越多，说明主线程更容易在关键路径上被打断。

如果要测量的是**调度延迟**，更稳妥的做法是直接用 Perfetto 官方公开的 `thread_state` 和 `sched` 表。Runnable 片段的起点就是线程进入就绪队列的时刻，片段结束点就是它进入 Running 的时刻；两者之间的 `dur` 就是等待 CPU 的时间。

```sql
-- 基于官方 thread_state / sched 表统计主线程的 wakeup latency
WITH target_thread AS (
    SELECT utid
    FROM thread
    WHERE name = 'main'
),
runnable AS (
    SELECT
        ts,
        dur,
        utid,
        waker_id
    FROM thread_state
    WHERE utid IN (SELECT utid FROM target_thread)
      AND state = 'R'
      AND dur > 0
)
SELECT
    runnable.ts AS runnable_ts,
    (runnable.ts + runnable.dur) AS running_ts,
    runnable.dur / 1000000.0 AS wakeup_latency_ms,
    waker_thread.name AS waker_thread
FROM runnable
JOIN sched
  ON sched.utid = runnable.utid
 AND sched.ts = runnable.ts + runnable.dur
LEFT JOIN thread_state waker_state
  ON runnable.waker_id = waker_state.id
LEFT JOIN thread waker_thread
  ON waker_state.utid = waker_thread.utid
ORDER BY wakeup_latency_ms DESC
LIMIT 20;
```

这条查询统计的是线程进入 Runnable 后到进入 Running 之间的等待时长。`waker_id` 可以把当前 Runnable 片段回连到唤醒它的线程状态，再还原出唤醒源。如果要直接查询 raw `sched_wakeup` / `sched_waking` 事件，需要先展开 `ftrace_event` 表；不要把 `sched_wakeup` 当成 Trace Processor 默认就存在的 SQL 表。

### 查询 Binder Transaction 耗时与异常诊断 [自动发现]

Binder Transaction 是 Android IPC 的核心，也是主线程卡顿的常见根因。Perfetto 通过 `linux.ftrace` 捕获内核 `binder_transaction` 系列 tracepoint，再经 `android.binder` 标准库 SQL 模块解析，可实现精细的 IPC 耗时归因。

数据流向为：**内核 ftrace 原始事件**（`binder_transaction` / `binder_transaction_received` / `binder_transaction_alloc_buf` / `binder_return`） → **Perfetto Trace Processor** → **`android.binder` 标准库模块**（`INCLUDE PERFETTO MODULE android.binder;`）。Perfetto stdlib 内部会把 flow 另一端归一成 server-side reply slice（内部的 CTE 命名），这不是内核 tracepoint，而是 Perfetto 的 SQL 层抽象。`android_binder_txns` 表是最核心的分析对象 [已验证: AOSP Perfetto 源码 `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql`，内核 tracepoint 定义 `kernel/common/drivers/android/binder_trace.h`]。

**关键 Duration 指标**：
- `client_dur`：同步调用中客户端从发出请求到收到回复的 wall-clock 时长；oneway 调用中为 0
- `server_dur`：服务端从处理开始到发送回复的 wall-clock 时长
- **dispatch 延迟**（需手动计算）：`server_ts - client_ts`，反映请求在服务端队列中等待调度的时间。`android_binder_txns` 表不直接提供 `dispatch_dur` 列，需要用 `server_ts - client_ts` 计算获得 [已验证: AOSP Perfetto stdlib `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql`]

**核心诊断 SQL**：

```sql
INCLUDE PERFETTO MODULE android.binder;

-- 慢同步事务排序
SELECT
    aidl_name,
    method_name,
    client_process,
    client_dur / 1e6                AS client_ms,
    server_dur / 1e6                AS server_ms,
    (server_ts - client_ts) / 1e6   AS dispatch_ms
FROM android_binder_txns
WHERE is_sync = 1
ORDER BY client_dur DESC
LIMIT 20;
```

**归因判断树**：
- `client_dur` 长 + `server_dur` 短 → 问题在 **dispatch/queue**（服务端线程池饱和或调度延迟）
- `server_dur` 很长 → 问题在 **服务端业务逻辑**（锁竞争、I/O 阻塞、深层 RPC）
- `(server_ts - client_ts)` 持续 >5ms → **Binder 线程池饱和**，所有 worker thread busy

**Binder 线程池饱和识别**：

```sql
SELECT client_process, server_process,
       AVG((server_ts - client_ts) / 1e6) AS avg_dispatch_ms,
       AVG(server_dur / 1e6)              AS avg_server_ms,
       COUNT(1)                            AS txn_count
FROM android_binder_txns
WHERE is_sync = 1
GROUP BY client_process, server_process
HAVING avg_dispatch_ms > 5.0
ORDER BY avg_dispatch_ms DESC;
```

**Oneway 事务 spam 识别**（Binder Spam）：

```sql
SELECT client_process, server_process,
       COUNT(1) AS oneway_count
FROM android_binder_txns
WHERE is_sync = 0
GROUP BY client_process, server_process
ORDER BY oneway_count DESC
LIMIT 10;
```

Perfetto UI 中，**Android Binder / Transactions** 轨道以 Flow 箭头连接客户端和服务端 Slice，同步事务显示完整往返 Flow，oneway 事务仅显示单向箭头。客户端线程在等待同步回复时通常处于 `S`（Sleeping）状态，`blocked_function` 为 `binder_thread_read` 或 `ioctl(BINDER_WRITE_READ)`。服务端则可通过 `Binder:xxx_y` 线程轨道判断线程池繁忙程度。

抓取配置参考（Perfetto config）：
```protobuf
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "binder/binder_transaction"
            ftrace_events: "binder/binder_transaction_received"
            ftrace_events: "binder/binder_transaction_alloc_buf"
            ftrace_events: "binder/binder_return"
            ftrace_events: "sched/sched_switch"
            ftrace_events: "sched/sched_wakeup"
        }
    }
}
```
atrace 等效命令：`adb shell atrace --async_start -b 20000 -c binder_driver am wm dalvik`

核心数据源：内核 `TRACE_EVENT(binder_transaction)` 定义于 `kernel/common/drivers/android/binder_trace.h`，驱动层通过 `trace_binder_transaction()` 记录发起，通过 `trace_binder_transaction_received()` 记录服务端接收；Perfetto 标准库 `android_binder_txns` 表由 `external/perfetto/src/trace_processor/perfetto_sql/stdlib/android/binder.sql` 定义。



### 大型 Trace 的 SQL 性能优化 [自动发现]

当 Trace 文件超过 500MB（例如长时间录制或高频事件场景），在 Perfetto UI 中直接执行复杂 SQL 查询可能导致页面无响应甚至崩溃。以下是处理大型 Trace 的实用建议：

**1. 使用命令行离线分析**

```bash
# 先用 trace_processor_shell 离线查询，避免 UI 卡顿
trace_processor_shell trace.pb --query-file analysis.sql > result.csv
```

**2. 用临时表缓存高频过滤结果**

```sql
-- 避免在全量 slice 表上反复 JOIN，先过滤到目标线程
CREATE TEMP TABLE main_thread_slices AS
SELECT slice.*
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
WHERE thread.name = 'main';

-- 后续查询直接走临时表
SELECT name, dur / 1000000.0 AS ms
FROM main_thread_slices
WHERE name LIKE 'Choreographer#doFrame%'
  AND dur > 16666667
ORDER BY dur DESC
LIMIT 50;
```

**3. 限制返回行数**

在每次查询末尾加 `LIMIT`，避免返回数万行拖慢 UI。先 `LIMIT 50` 看分布，确认查询逻辑正确后再按需放开。

**4. 利用 `INCLUDE PERFETTO MODULE` 标准库**

Perfetto 标准库提供了预构建的模块和视图（如 `android.binder`、`android.frames.timeline` / `android_frames`），比自己写 JOIN 更高效且更准确。优先检查是否已有标准库模块覆盖目标分析场景，再决定手写 SQL。




SQL 分析的好处是能快速处理整份 Trace 的数据，给出统计级别的结论。比如，可以用第一个查询快速统计出"这次 10 秒的滑动操作中，总共出现了 23 次卡顿帧，其中 5 次超过 32ms"——这种宏观信息是手动点击很难得到的。

高爷在 Perfetto 系列 CPU 篇中也提到了 SQL 分析的重要性 [来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]：通过 SQL 查询各线程的 CPU 时间占用，可以发现一些在 UI 中不容易注意到的异常——比如某个后台线程的 CPU 占用竟然超过了主线程，那它很可能在抢主线程的时间片。

## 常见问题与误区

### 误区："帧率 FPS 可以直接反映是否卡顿"

帧率高不代表不卡。一个 FPS 为 50 的页面，如果前 200ms 画了一帧、后 800ms 画了 49 帧，平均帧率是 50，但用户会明显感到不流畅。反过来，一个均匀的 15fps（比如视频播放），帧率虽低但不会让人觉得卡。所以衡量卡顿，看的是帧间隔的均匀性（掉帧次数和掉帧程度），而不是平均帧率 [来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]。

### 误区："没有红帧就没有卡顿"

在分析中，黄帧（超过一个 VSync 周期但不到两个）同样需要关注。连续的黄帧可能在多缓冲机制的保护下不导致掉帧，但如果连续出现，缓冲迟早会被消耗完，最终还是会出现可见的卡顿 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md]。而且黄帧还说明渲染已经到了极限边缘，任何微小的波动都可能把它推过阈值。

### 误区："主线程 Sleep 就不是主线程的问题"

这个误区很常见。看到主线程长时间处于 Sleep 状态，就下结论"不是主线程的问题"。但主线程 Sleep 的原因可能是等待前一帧的 RenderThread 完成——syncFrameState 操作会阻塞主线程直到渲染线程把前一帧的数据同步完成。所以虽然主线程在等，但根因可能是渲染线程太慢，而渲染线程慢又可能是前一帧绘制命令太复杂。追根溯源，问题还是在 App 自身的绘制逻辑 [来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md]。

### 误区："抓 Trace 一定要抓很长时间"

Trace 不是越长越好。5-10 秒的精简 Trace 远比 60 秒的"大杂烩"好分析。Trace 太长会导致 Perfetto UI 卡顿、关键信息被淹没、分析时间成倍增加。正确的做法是：精确复现问题，在最短的时间内复现卡顿，然后停止抓取。

## 与其他章节的关系

本节建立在前几章的基础之上，阅读时保留以下交叉关系：

- **7.1 卡顿的定义与分类**：定义了什么是卡顿以及卡顿的分类体系，是本节分析方法论的认知基础
- **7.2 卡顿原因体系**：系统梳理了卡顿的所有可能原因，本节的 Checklist 中的排查项与此一一对应
- **2.4 Choreographer 与渲染流水线**：理解 doFrame 的五类回调（Input → Animation → Insets Animation → Traversal → Commit）是分析主线程耗时的基础
- **2.5 MainThread 与 RenderThread 协作**：理解 syncFrameState 的阻塞关系是判断"主线程等待渲染线程"场景的关键
- **2.6 SurfaceFlinger 与合成**：理解 BufferQueue 的工作机制是判断"是否会产生可见掉帧"的前提
- **1.5 线程模型**：理解 Binder 线程、Handler 机制是分析 Binder 调用阻塞和锁竞争的基础
- **2.18 Adaptive Refresh Rate 与动态帧率控制**：Android 15-QPR1+ 动态刷新率会改变 Expected Timeline 的预算宽度，分析 FrameTimeline 时要参考本章的 ARR 规则
- **13.3 Perfetto View 解读**：Perfetto UI 的详细操作指南，本节中的操作技巧在 13.3 中有更系统的介绍

## 参考资料

- 高爷原创文章：
  - [Android Systrace 流畅性实战 2：案例分析](https://www.androidperformance.com/2021/04/24/android-systrace-smooth-in-action-2/) — 完整的桌面滑动卡顿分析案例，展示了从 Input 事件追踪到 SurfaceFlinger 确认的全过程
  - [Android Systrace 流畅性实战 3：卡顿分析过程中的一些疑问](https://www.androidperformance.com/2021/04/24/android-systrace-smooth-in-action-3/) — 解答了帧颜色含义、黄帧与掉帧的关系等常见困惑
  - [Android Perfetto 系列 3：熟悉 Perfetto View](https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/) — Perfetto UI 操作技巧，包括唤醒源查看、Critical Path、Pin 等功能
  - [Android Perfetto 系列 9：CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/) — CPU 调度分析、频率追踪、核心架构等
  - [Android 中的卡顿丢帧原因概述 - 方法论](https://www.androidperformance.com/2019/09/05/Android-Jank-Debug/)
- 官方文档：
  - [Perfetto Trace Processor SQL Documentation](https://perfetto.dev/docs/analysis/sql-tables)
- [Perfetto Docs - Analyzing Android Binder Transactions](https://perfetto.dev/docs/analysis/binder) — 官方 Binder 分析指南，含 `android.binder` 模块用法 [AIW-源码调研-2026-04-29] — SQL 查询 Trace 数据的完整参考
  - [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline) — FrameTimeline 的可用版本、轨道含义与 SurfaceView 使用边界
  - [Android FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics) — FrameMetrics 各指标的官方说明
  - [JankStats Library](https://developer.android.com/topic/performance/jankstats) — Google 官方的线上卡顿监控库
- 其他参考：
  - [Android 深入卡顿分析与实践 - 腾讯音乐技术团队](https://mp.weixin.qq.com/s/...) — Wesing 卡顿治理的完整实战案例，包含多个具体的优化方向
  - [Android 卡顿监测的方方面面](https://juejin.cn/post/7214635327407308859) — 业界卡顿监测方案的全面梳理，包括 BlockCanary、Matrix 等
