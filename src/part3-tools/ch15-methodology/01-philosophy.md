---
title: 性能优化的术、道、器
chapter: '15.1'
section: '15.1'
status: ready-for-review
drafted_date: '2026-04-04'
drafted_by: openclaw-task2a
applicable_versions: Android 5.0 (API 21) - Android 16 (API 36)
last_verified: '2026-04-04'
last_verified_against: AOSP android-16.0.0_r1
confidence: high
sources:
- type: blog
  path: androidperformance.com/2024/05/21/Android-Perfetto-01-What-is-perfetto/
- type: blog
  path: abseil.io/fast/hints.html (Jeff Dean Performance Hints)
- type: blog
  path: kernel工匠 - 为什么要建立性能工程团队 (Brendan Gregg 2025)
- type: blog
  path: androidperformance.com - OS 设计之性能设计 (Yingyun)
- type: blog
  path: androidperformance.com/2015/04/19/Android-Performance-Patterns/
- type: book
  path: Brendan Gregg - Systems Performance (性能之巅)
- type: official
  path: developer.android.com/topic/performance
tags:
- methodology
- philosophy
- tools
- best-practices
related_chapters:
- '13.1'
- '13.2'
- '15.2'
- '15.3'
- '15.7'
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task2b_result: fixed
task2b_state: pending
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-05"
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-04-30
last_task9_at: "2026-05-23T08:36:45+08:00"
last_task2b_at: "2026-04-30T17:46:37.750688"
task2b_fixed_at: "2026-04-27T13:40:00+08:00"
task9_review_notes: "2026-05-23 task9 idle audit: needs-rework。P0 2 / P1 0 / P2 0。"
task6_reviewed_date: "2026-05-05"
last_task6_at: "2026-05-05T22:07:00+08:00"
last_task9_audit: "2026-05-23"
last_task9_audit_log: "logs/deep-review/2026-05-23-08-audit.md"
---
# 性能优化的术、道、器

<!-- outline-start -->

## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 性能优化之「道」:用户体验驱动、数据驱动、持续优化
- 🔹 性能优化之「术」:分析方法、优化策略、防劣化手段
- 🔹 性能优化之「器」:工具链的选择与组合
- 🔹 性能优化的投入产出思维:优先高频场景、高影响面
- 🔹 性能优化的误区:过早优化、局部优化、忽视度量

### 扩展(可选深入)

- 🔸 Google 的性能文化:speed matters、performance budget
- 🔸 性能工程师的能力模型

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么这一章要从「术、道、器」讲起

性能问题最容易把人陷入细节。  
App 启动慢、列表滑动卡顿、ANR、功耗高，这些问题都很重要，后面也都有专门章节。但如果一上来只学"怎么抓 trace、怎么改代码、怎么调参数"，很容易出现一种很熟悉的状态：问题看过很多，方法也学了不少，换个场景还是像第一次遇到。

所以第 15 章不再继续补系统细节,而是把前面那些知识重新整合成一套思维框架:遇到性能问题时,先怎么想,怎么判断轻重缓急,怎么选工具,怎么验证结果。它讲的是工程师在现场会用到的判断顺序。

Brendan Gregg 在《Systems Performance(性能之巅)》中对性能工程的本质有过一段精准的描述:**性能是主观的、系统是复杂的、通常有多个问题并存** [已验证: Brendan Gregg, Systems Performance, Chapter 2]。这三句话听起来简单,但它们构成了性能分析方法论的地基。性能是主观的--被一个用户认为「不好」的体验,另一个用户可能觉得「还行」,所以不能用「感觉变快了」来衡量优化效果，而需要量化的指标。系统是复杂的--性能问题往往不是出在单个组件上,而是出在组件之间的交互上,修复一个问题可能只是把瓶颈推到了系统的另一个地方。多个问题并存——在复杂软件中通常不止一个性能问题，更难的是辨别哪些问题最重要。

理解了这三点,再谈「道」「术」「器」,才不会把性能优化误解成"学会几个工具和几个优化技巧"。

## 性能优化之「道」

「道」是方向。没有方向,再多的技巧和工具都只是盲目的忙碌。Android 性能优化的「道」,可以归纳为三个原则:用户体验驱动、数据驱动、持续优化。

### 用户体验驱动:性能优化的起点是用户感受

性能优化的终点不是跑分,也不是图表更漂亮,而是用户操作时真的更顺。这句话很容易说,但在工程里最容易被忘。

我们常常看到这样的场景:团队花了大量精力优化了某个方法的执行时间,从 50ms 降到了 30ms,自认为做了一次很棒的优化。但如果这个方法只在后台同步数据时被调用,用户感知不到这次优化带来的变化，那这 40% 的性能提升对用户等于零。

反过来,一个 App 的冷启动时间从 2 秒降到 1.5 秒,数字上看只快了 500ms,但这 500ms 直接影响了用户每次打开 App 的第一印象--用户对「快」和「慢」的感知往往集中在几个关键节点上:启动、页面切换、列表滚动、按钮点击后的响应。这些就是性能优化的高价值战场。

Google 早在 2015 年推出 Android Performance Patterns 系列视频时,就明确表达了这一理念:这些视频的核心目的在于帮你建立正确的性能意识--**知道该用什么工具,该采取什么样的步骤,需要达到什么样的目标** [已验证: 来源见 androidperformance.com/2015/04/19/Android-Performance-Patterns/]。这正是用户体验驱动思维的体现。

关于性能对用户体验的影响,业界的量化数据已经很充分了。Amazon 在 2006 年发现,页面加载时间每增加 100ms,销售额就会下降 1% [已验证: 来源见 Greg Linden, Amazon, 2006]。Google 的研究则表明,搜索结果页生成时间每增加 0.5 秒,流量会下降 20% [已验证: 来源见 Google Search performance research, 2006]。在移动端,53% 的用户会放弃加载时间超过 3 秒的网页 [已验证: 来源见 Google/SOASTA research, 2017/2018; developer.android.com]。这些数字翻译成收入,可能是数百万甚至数十亿美元的差别。

在 Android 开发中，用户体验驱动要求先回答一个问题：**用户在哪里感受到了慢？** 这个问题的答案决定了分析应该从哪里入手。如果用户反馈「列表滑动卡顿」,那我们的分析起点应该是渲染管线和主线程耗时(本书第 7 章和第 2 章的内容);如果用户反馈「点击按钮没反应」,那分析起点应该是输入事件分发和主线程阻塞(本书第 8 章和第 3 章的内容)。

### 数据驱动:没有度量,就没有可靠的优化

Lord Kelvin 的名言在性能优化里可以更进一步:**如果不能量化它,连它是不是问题都不一定说得准。**

Brendan Gregg 把性能问题描述为「主观的」,正因如此,我们更需要客观的数据来判断性能的好坏。用户说「感觉有点卡」,这句话提供了问题的方向,但不能作为优化的依据。我们需要把它翻译成可量化的指标:是哪一帧超时了?超时了多少?是 measure/layout 耗时过长,还是 draw 阶段被 GPU 操作阻塞了?在 Perfetto 中,这些问题都有精确的答案。

数据驱动的方法论包含三个步骤:

第一步,**建立基线(Baseline)**。在优化之前,先用工具抓取当前状态的数据。这个数据就是我们的基准线,后续所有的优化效果都要与之对比。对于启动速度,基线可能是连续 10 次冷启动的中位数耗时;对于滑动流畅度,基线可能是一段标准滑动操作中的掉帧率。

第二步,**量化问题**。有了基线之后,用工具(Perfetto、Android Studio Profiler、benchmark 等)定位具体的性能瓶颈,并量化它的影响范围和严重程度。第 13 章详细介绍了 Perfetto 的使用方法,第 14 章介绍了其他工具的使用场景。

第三步,**量化收益**。优化完成后,用相同的方法和条件重新测量,与基线对比。Jeff Dean 在他的 Performance Hints 文档中反复强调这一点:性能优化必须有数据支撑 [已验证: 来源见 abseil.io/fast/hints.html, Jeff Dean & Sanjay Ghemawat, 2025]。如果一个优化在数据上看不到改善,那它就不是有效的优化,无论代码看起来多么「巧妙」。

### 测量本身会影响被测系统

上面三步建立了一个完整的「度量→定位→验证」循环,但有一个前提容易被忽略:**测量本身会影响被测系统**。

Perfetto 的 trace event 插桩会给每个被追踪的函数增加微秒级开销;Simpleperf 的采样频率越高,对目标线程的干扰越大;Macrobenchmark 连续跑几十次冷启动,设备可能因发热触发降频,导致后几轮数据偏低。这些影响在单次测量中往往可以忽略,但在精确到毫秒级的性能对比中就可能引入偏差。

减少测量偏差的常见做法:

- **预热轮次(warm-up)**:正式测量前先跑几轮,让 JIT 编译、缓存、CPU 调频都稳定下来再开始计时。
- **控制热降频**:长时 benchmark 注意设备温度,必要时在两次采样之间加入冷却间隔,配合固定屏幕亮度减少变量。
- **统一编译状态**:Macrobenchmark 冷启动测量中更大的变量是编译状态。`CompilationMode.None` / `Partial` / `Full` / `DEFAULT` 会改变 JIT、AOT、Baseline Profile 的参与方式。`StartupMode.COLD` 本身会在迭代间处理进程冷启动。对比时应保持相同 `CompilationMode`、相同 profile 状态、同机型温控条件,而不是依赖 `always_finish_activities` 这样的旧版设置。
- **对比不同采样率**:如果 Simpleperf 在 99Hz 和 999Hz 下给出一致的热点排名,说明采样干扰在可接受范围内。
- **多次测量取分布**:不要只测一次。多次测量取中位数或 P50/P90/P99 分布,才能区分「真实性能差异」和「测量噪声」。

这一原则在 Brendan Gregg 的《Systems Performance》中有专门讨论--他称之为「观察者效应(Observer Effect)」:任何观察行为都会改变被观察系统的行为 [已验证: Brendan Gregg, Systems Performance, Chapter 2]。

### 持续优化:性能从来不是做完一次就结束

很多团队对性能优化的认知是「做一次,然后就可以不管了」。这是一种非常危险的误解。

Android 系统在持续演进,每一代新版本都可能引入新的性能特性或改变既有行为。App 自身也在持续迭代,每次新增功能都可能引入新的性能问题。甚至用户的使用习惯和设备环境也在变化--从 60Hz 屏幕到 120Hz 屏幕、从 4GB 内存到 16GB 内存、从单应用到多窗口--这些变化都在改变性能优化的优先级和策略。

持续优化在实践中意味着三件事:

**防劣化**是最基本的底线。每次提交代码之前,自动化的性能测试应该跑一遍,确保关键指标没有回退。AndroidX 的 Macrobenchmark 库就是为此设计的--它可以在 CI 环境中自动测量 App 的启动时间、帧率等指标,并在指标回退时发出警告 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark]。

**定期巡检**是更主动的做法。即使没有新功能发布,也应该定期(比如每周或每两周)用 Perfetto 抓取一次 Trace,检查关键路径上有没有新增的耗时操作。就像身体健康需要定期体检一样,App 的性能也需要定期「体检」。

**版本跟进**是长期投入。每当 Android 发布新版本,都应该评估新版本对既有优化策略的影响。比如 Android 12 引入了 BlastBufferQueue 替代 BufferQueue,这改变了渲染管线的行为(详见第 2 章和第 2.6 节)。如果我们的优化策略依赖于旧的行为模型,就需要及时调整。

从工具演进看,这条时间线可以拆成几处明确的里程碑:

- **API 24 / Android 7.0**:`FrameMetrics` 已经提供逐帧耗时观测能力。
- **Android 9-10**:Perfetto 逐步成为系统级 trace 主线,systrace 更多退到兼容入口。
- **Android 11**:BLAST 改变了 buffer 交接模型,渲染路径的观测口径开始和旧 BufferQueue 时代分开。
- **Android 12**:FrameTimeline 和更细的 jank 证据链让帧级诊断更直接。
- **Baseline Profiles**:这是 Jetpack ProfileInstaller + ART 的能力,不属于某一个 Android 大版本。Profile 规则随 APK/AAB 打包,ProfileInstaller 可在 API 24+ 设备上回填到 ART;如果讨论 Play Cloud Profiles,需要和本地 Baseline Profile 分开写。
- **API 35 / Android 15**:`android.os.ProfilingManager` 正式进入平台 API,应用可通过 `requestProfiling()` 发起采样,并通过 `registerForAllProfilingResults()` 接收 profiling 结果。源码入口是 `frameworks/base/core/java/android/os/ProfilingManager.java` 与系统侧 `ProfilingManagerService`。
- **API 36 / Android 16**:`android.os.ProfilingTrigger` 与 `ProfilingManager.addProfilingTriggers(List<ProfilingTrigger>)` 允许应用注册系统触发式 profiling,例如启动、ANR 或其他平台定义的触发器。触发式采样有系统限流,结果通过全局 listener 返回,系统也可能因为配额、负载或隐私策略跳过本次采样。

Baseline Profiles 的处理路径可以拆成几段:AGP / profgen 把人类可读规则转成二进制 `baseline.prof`,随包进入 `assets/dexopt/`;ProfileInstaller 在设备端安装或合并 profile;ART 侧 `art/profman/profman.cc` 分析 profile,`art/dex2oat/dex2oat.cc` 在 `speed-profile` 等编译过滤器下编译热点方法。`ENQUEUED` 只表示编译任务进入队列,`COMPILED` 才表示 profile 已被编译消费。

Android 14-16 继续扩展 Perfetto 的 Track 覆盖(Jobscheduler Track、App Startup Track),并强化了后台执行限制,后台任务的分析需要额外关注系统级的调度约束。

了解这些代际变化,有助于在阅读旧版技术文章或分析老版本设备的 Trace 时,正确理解工具和数据含义的差异。

## 性能优化之「术」

「术」是方法。知道了方向之后,我们需要一套系统的方法来定位问题、实施优化、防止回退。

### 分析方法:从宏观到微观

性能分析最忌讳的是「一上来就扎进细节」。正确的做法是从宏观到微观,逐步缩小问题范围。

第一层,**确定问题类别**。Android 性能问题大致可以分为六大类:流畅性(卡顿/掉帧)、响应速度(启动/点击延迟)、ANR(主线程阻塞)、内存(泄漏/溢出)、功耗(后台耗电/发热)、稳定性(崩溃/死锁)。每一类问题都有对应的分析思路和工具。用错工具比没有工具更浪费时间--用 Perfetto 分析内存泄漏,或者用 MAT 分析掉帧问题,都是南辕北辙。

第二层，**确定影响范围**。它是全局性的还是特定场景的？只在低端设备上出现，还是在所有设备上都有？是偶发的还是必现的？这些信息决定了分析的策略和优先级。一个影响 10% 用户的必现问题,优先级通常高于一个影响 0.1% 用户的偶发问题。

第三层,**定位瓶颈**。在正确的工具和正确的场景下,定位具体的耗时操作或资源瓶颈。这一步需要结合本书前面各章的知识--比如看到主线程有一段很长的 binder call,就需要知道 Binder IPC 的机制(第 1.4 节)来判断是正常等待还是异常阻塞。

这种从宏观到微观的分析方法,与 Gracker 在 Perfetto 系列文章中提倡的「上帝视角」是一致的。Perfetto 之所以是 Android 性能分析的核心工具,正是因为它能在一个视图里展示 App、Framework、内核、硬件的协同运作。我们不需要一开始就知道问题出在哪,只需要先看全局,然后逐步聚焦到有异常的区域。

### 优化策略:对症下药

定位到瓶颈之后,优化策略的选择取决于瓶颈的类型。

**CPU 密集型瓶颈**:如果主线程或关键路径上有大量的计算操作,优化方向包括算法优化(降低时间复杂度)、延迟计算(只在需要时执行)、并行化(把计算移到后台线程)、缓存(避免重复计算)。在 Android 上,一个常见的场景是列表滑动时在主线程做 JSON 解析或 Bitmap 解码--这种问题通过异步预加载通常可以大幅改善。

**I/O 密集型瓶颈**:如果瓶颈是磁盘读写或网络请求,优化方向包括异步化(不阻塞主线程)、批量化(减少 I/O 次数)、缓存(避免重复 I/O)、预加载(提前准备好数据)。Android 的 StrictMode 就是用来检测主线程 I/O 的工具。

**内存瓶颈**:如果瓶颈来自内存分配过多导致 GC 频繁、内存泄漏导致可用内存逐渐减少，或者内存占用过大触发 LMK，优化方向各不相同。本书第 4 章和第 10 章分别从原理和实战角度讨论了内存优化。

**渲染瓶颈**:如果瓶颈表现为掉帧或画面撕裂，需要区分是 CPU 绑定的渲染瓶颈（measure/layout/draw 耗时过长）还是 GPU 绑定的瓶颈（GPU 命令过多或过度绘制）。前者通过简化布局、减少视图层级来解决,后者通过减少过度绘制、使用硬件层来缓解。本书第 2 章和第 7 章有详细的讨论。

无论哪种瓶颈，优化的核心原则都是一样的：**减少关键路径上的工作量**。目标是让关键路径需要做的工作变少——从源头砍掉工作量，比追求更快的执行速度更有效。有时候，让某个方法不再被调用，比优化方法本身的执行效率更快。

### 防劣化:性能的「免疫系统」

优化做完之后,如何确保效果不会在后续迭代中逐渐流失?这需要建立一套性能防劣化机制。

**自动化性能测试**是最有效的防线。AndroidX 提供了 Macrobenchmark 和 Microbenchmark 两套库,前者用于测量端到端的用户场景(如冷启动、列表滚动),后者用于测量代码片段的执行时间 [已验证: 官方文档, developer.android.com/topic/performance/benchmarking]。把这些测试集成到 CI 流水线中,每次提交都跑一遍,就能在性能回退发生的第一时间发现它。

**性能预算(Performance Budget)** 是一种更主动的约束机制。团队为关键指标设定上限,比如「冷启动 P50 不超过 1.5 秒」「90Hz 设备上主线程帧耗时尽量压到 11ms 以内」。这些只能作为示例阈值,正式预算要绑定 release 包、设备档位、刷新率、冷/温/热启动口径、样本次数和 P50/P90/P95 分位数。任何导致指标超过预算的代码提交,都必须在合并前解决性能问题,或者重新评估预算是否适合当前业务基线。

**线上监控**负责兜底。Google Play Console 的 Vitals 面板会展示 App 在真实用户设备上的性能数据,包括 ANR 率、崩溃率、卡顿率等 [已验证: 官方文档, developer.android.com/topic/performance/vitals]。这些数据反映的是实验室环境无法覆盖的复杂场景--低端设备、网络不稳定、后台应用多、系统负载高--它们是性能优化最终要面对的现实。

本书第 15.5 节会更详细地讨论线上监控体系的建设。

## 性能优化之「器」

「器」是工具。前两章(第 13 章和第 14 章)已经详细介绍了各种工具的使用方法,这里我们从方法论的角度讨论工具的选择和组合策略。

### 工具的选择逻辑

Android 性能分析工具很多,但它们各有定位。选择工具时先写清楚「要回答什么问题」,再选择能回答这个问题的工具。

| 场景 | 先看什么 | 首选工具 | 继续深入时看什么 |
|------|----------|----------|------------------|
| 启动慢 | 冷/温/热启动分位数、TTID/TTFD | Macrobenchmark + Perfetto App Startup Track | `Application.onCreate()`、ContentProvider、首帧前主线程长任务、`reportFullyDrawn()` |
| 滑动卡顿 | 超时帧、JankType、主线程/RenderThread 分工 | Perfetto FrameTimeline + JankStats | `Choreographer#doFrame`、`syncAndDrawFrame`、RenderThread `DrawFrame`、SurfaceFlinger `commit/composite` |
| 内存增长 | Java/native heap 趋势、GC 频率、RSS/PSS | Android Studio Memory Profiler + Perfetto heap/process memory | Heap dump 引用关系、heapprofd 分配栈、lmkd 事件、`ApplicationExitInfo` |
| 功耗/发热 | wakelock、alarm、job、thermal 状态 | Perfetto power rails / Battery Historian / `dumpsys batterystats` | Alarm 权限状态、JobScheduler 约束、Thermal API 初始快照与回调 |
| 网络慢 | 请求耗时、DNS/TLS/TTFB 分段 | App 端网络埋点 + Perfetto Network Track | OkHttp event listener、TrafficStats、radio active 时间、失败重试策略 |

**Perfetto** 是 Android 性能分析的「瑞士军刀」。它提供了全局视角--在一个 Trace 文件中能呈现 App、Framework、SurfaceFlinger、内核调度的完整运作。当问题不明朗,不知道是哪个模块导致的时候,Perfetto 是首选的入口。它特别适合分析流畅性、启动速度、响应速度、系统级交互等问题 [已验证: 来源见 Android-Perfetto-01-What-is-perfetto.md]。

**Android Studio Profiler** 更适合 App 开发者日常使用。它直接集成在 IDE 中,不需要额外抓 Trace,可以实时观察 CPU、内存、网络、电量的状态。适合在开发阶段快速定位问题,或者验证优化效果。

**Simpleperf** 用于 Native 代码的性能分析。当瓶颈在 C/C++ 代码中(比如 JNI 调用、Native 库、GPU 驱动),Simpleperf 能提供函数级别的热点分析。Perfetto 看到的是「哪个线程跑了多久」,Simpleperf 看到的是「哪个函数跑了多久」。

**内存分析工具**(Memory Profiler、MAT、heapprofd)各有分工。Memory Profiler 适合实时观察内存分配和回收;MAT 适合分析 Heap Dump 找内存泄漏;heapprofd(Perfetto 的内存分析组件)适合抓取生产环境的内存分配情况。

**dumpsys** 是系统信息查询的万能钥匙。`dumpsys meminfo` 查内存、`dumpsys gfxinfo` 查帧率、`dumpsys batterystats` 查电量、`dumpsys activity` 查进程状态。它不提供 Trace 级别的时序信息,但能快速获取系统状态的全貌。

### 工具的组合策略

单用一个工具往往不够。在实际分析中,我们通常需要组合使用多个工具,形成一套「分析流程」。

典型的流畅性分析流程:先用 Perfetto 抓取一次滑动场景的 Trace,定位到哪一帧超时了、超时发生在哪个阶段(measure/layout/draw/GPU);如果瓶颈在主线程的某个方法,再用 Android Studio Profiler 的 CPU 分析器或者代码插桩来确定具体是哪一行代码导致的;如果瓶颈在 GPU,用 GPU 渲染分析工具或 Perfetto 的 gpu_render_stages Track 来深入分析。

典型的启动速度分析流程:先用 Macrobenchmark 建立冷启动时间的基线;然后用 Perfetto 抓取启动过程的 Trace,从 Application.onCreate() 开始,沿着初始化路径逐步检查每个阶段的耗时;如果发现某个 SDK 初始化特别慢,再针对性地优化或延迟加载。

这种「Perfetto 定位 → 专项工具深入 → 优化 → 验证」的模式,是 Android 性能分析的标准工作流。本书第 13 章到第 14 章介绍的所有工具,都可以嵌入到这条工作流中使用。

### 工具不能替代思考

工具提供数据,但不能替代判断。一个经验丰富的工程师和一个新手用同一份 Perfetto Trace,能看到的东西可能完全不同--因为经验决定了你「知道该看什么」。

这就是为什么这本书前半部分花了大量篇幅讲机制原理。只有理解了 VSync 是怎么工作的(第 2.3 节),你才能在 Perfetto 中正确解读 VSYNC-app 和 VSYNC-sf 的信号间距;只有理解了 Binder 的通信模型(第 1.4 节),你才能判断一个 binder call 的耗时是正常的还是异常的。工具给你数据,知识给你判断力,方法论给你决策路径--三者缺一不可。

## 性能优化的投入产出思维

工程学就是资源分配的艺术。性能优化也是如此--我们的时间和精力是有限的,不可能同时优化所有东西。所以,我们需要一套判断优先级的方法。

### 优先高频场景

用户每天打开 App 50 次,其中 45 次是热启动、5 次是冷启动。如果我们只有时间优化一个,应该优化哪个?答案取决于用户体感。冷启动虽然只占 10% 的次数,但它是用户对 App 的第一印象,而且冷启动通常比热启动慢得多--2 秒 vs 200ms,差异是 10 倍。用户可能记不住那 45 次快速启动,但一定会记住那 5 次漫长的等待。

再比如列表滑动和页面跳转。如果用户在一个 App 里 80% 的时间都在滑动列表,那滑动流畅度就是最高优先级的优化目标。相比之下,某个设置页面打开慢了 100ms,几乎不会影响用户满意度。

判断场景优先级的关键数据是**使用频率 × 用户感知强度**。高频场景的优化即使幅度不大,累积的体验提升也很大;低频场景的优化即使幅度很大，用户可能注意不到。

### 量化影响面

一个性能问题影响了多少用户?在什么设备上出现?什么条件下触发?这些问题决定了优化的紧迫程度。

线上监控数据在这里起着决定性作用。Google Play Console 的 Vitals 面板可以告诉你:ANR 率是多少、卡顿集中在哪些设备上、用户报错最多的场景是什么。如果你的 App 有 1000 万用户,ANR 率从 0.5% 降到 0.3%,看似只改善了 0.2 个百分点,但实际影响的用户数是 2 万--这 2 万个用户体验的改善,值得投入工程资源。

Jeff Dean 提出了一个实用的「粗略估算(Back of the Envelope Calculation)」方法:在动手优化之前,先估算一下优化可能带来的收益,以及投入的工作量,然后判断值不值得做 [已验证: 来源见 abseil.io/fast/hints.html]。这种估算不需要很精确,但能帮我们排除那些「投入产出比」明显不合理的优化方向。

### 优化的边际收益

性能优化有一个普遍规律:**第一轮优化通常收益最大,越往后收益越小**。把冷启动时间从 3 秒优化到 1.5 秒可能只需要修改几个初始化顺序;但从 1.5 秒再优化到 1.2 秒,可能需要重构整个初始化框架。

Brendan Gregg 在讨论性能工程团队的 ROI 时提到,一个成熟的性能团队每年可以实现 5-10% 的基础设施成本下降--5% 是「良好」,10% 是「卓越」[已验证: 来源见 Brendan Gregg, Performance Engineering Teams, 2025]。这个数据说明了一个重要的现实:性能优化是持续性的工作,但单次优化的收益是递减的。

知道这一点,我们就不会在边际收益已经很低的优化上浪费太多时间。当一轮优化的效果从「明显改善」变成「勉强可测量」的时候,通常就应该转向下一个目标了。

## 性能优化的误区

即使理解了「道」「术」「器」,在实际工作中仍然容易掉进一些常见的坑。这些误区不仅浪费时间,还可能导致优化方向完全错误。

### 误区一:过早优化

Donald Knuth 的那句「过早优化是万恶之源」可能是软件工程领域被引用最多的话,也很容易被截断。原文的约束更完整:**在大约 97% 的情况下,应当忽略微小的效率提升;但在剩余 3% 的关键路径上,不能放弃必要优化。** [已验证: 来源见 D. Knuth, Structured Programming with go to Statements, 1974; abseil.io/fast/hints.html]

Jeff Dean 对此有更深入的分析。他指出,完全不关注性能的开发方式同样有害:如果在开发大型系统时完全不顾及性能,最终会得到一个「扁平的性能剖析结果」--性能损耗分散在各个环节,无法定位明显的热点,导致优化工作无从下手 [已验证: 来源见 abseil.io/fast/hints.html]。如果开发的是供他人使用的库,遭遇性能问题的使用者往往无法直接修复,他们还要理解库代码并推动维护者接受优化。

合适的态度是 Jeff Dean 的建议:**编写代码时,若对代码的可读性或复杂度无显著影响,应优先选择性能更优的实现方案** [已验证: 来源见 abseil.io/fast/hints.html]。这属于「不故意写慢代码」,不等同于过早优化。

### 误区二:局部优化

局部优化是指只盯着一个模块或一个指标优化,而忽略了全局效果。

一个典型的例子:团队发现 App 的帧率在低端设备上不稳定,于是投入大量精力优化渲染管线,把平均帧时间从 12ms 降到了 9ms。但用户反馈「还是觉得卡」。进一步调查发现，问题不在渲染慢，而在 Input 事件分发延迟——从触摸屏幕到 App 收到事件就花了 40ms，加上渲染的 9ms，总延迟接近 50ms，用户当然觉得「不跟手」。

另一个例子:优化了主线程的所有耗时操作,帧率提高了，但优化引入了大量后台线程的工作，导致整体功耗上升，用户抱怨「App 耗电太快」。

局部优化的根源是缺乏全局视角。Perfetto 的「上帝视角」就是为了解决这个问题--在一个视图里看到所有模块的协同运作,才能判断优化一个地方是否会引发另一个地方的瓶颈。

### 误区三:忽视度量

「我觉得优化有效果」--这是性能优化中最危险的一句话。

没有度量支撑的优化判断,就是猜测。而猜测在复杂的系统中几乎是不可靠的。一个优化在开发者的旗舰设备上「感觉更快了」,可能在低端设备上完全没有效果,甚至因为增加了代码路径的复杂度反而变慢了。

忽视度量还有另一种表现形式:只度量了平均值,忽略了长尾。如果 95% 的帧都在 8ms 内完成,但剩下 5% 的帧耗时超过 50ms,用户感知到的依然是「卡」。这种问题只有看 P99(第 99 百分位)帧时间才能发现。平均帧时间 8ms 和 P99 帧时间 50ms 同时存在,这就是为什么我们强调要看分布而不是只看均值。

### 误区四:优化没有优先级

什么都想优化,结果什么都做不好。

性能优化资源有限的情况下，正确的做法是先解决「用户感知最强烈」的问题，再解决「影响面最大」的问题，之后再打磨那些「只有实验室数据才能发现的微小改善」。

一个实用的优先级排序方法:

1. **P0:用户直接感知的问题**(启动慢、滑动卡顿、点击无响应)--立刻解决
2. **P1:影响大量用户的问题**(线上 ANR 率高、特定机型崩溃)--尽快解决
3. **P2:影响少数用户但体验很差的问题**(极端场景下的 OOM、特定操作路径卡死)--计划解决
4. **P3:实验室数据上的微小改善**(某个方法快了 5%、内存占用减少了 2MB)--有余力再做

### 误区五:迷信工具

工具有局限。Perfetto 只能告诉你「发生了什么」,不能告诉你「为什么」--后者需要你对系统机制的理解。

有时候,工程师过度依赖工具提供的现成分析结果(比如 Perfetto 的 Metrics 面板、Android Studio 的 Profiler 建议),而忽略了对问题本质的思考。工具说「主线程有 GC 操作」,但为什么会有 GC?可能是内存分配太频繁,也可能是内存泄漏导致可用空间不足触发频繁回收。这个「为什么」只有通过理解 App 自身的代码逻辑才能回答。

## 扩展:Google 的性能文化

Google 对性能的重视可以追溯到公司成立之初。两个经典的案例是:

**搜索速度**:Google 发现搜索结果页生成时间每增加 0.5 秒,流量会下降 20% [已验证: 来源见 Google, Marissa Mayer, Web 2.0 Summit, 2006]。这个发现直接推动了 Google 在搜索性能上的持续投入--从服务端渲染优化到 AMP 项目的推出,背后都是「速度即用户价值」的理念。

**Android Performance Patterns**:2015 年 Google 推出的这个系列视频,虽然每集只有 3-5 分钟,但覆盖了 Android 性能优化最核心的知识点:渲染性能、过度绘制、VSync、GPU 分析、内存管理。它的定位不是教具体的优化技巧,而是帮助开发者建立正确的性能意识--了解系统是怎么工作的,知道该用什么工具,该关注什么指标 [已验证: 来源见 androidperformance.com/2015/04/19/Android-Performance-Patterns/; YouTube Android Performance Patterns playlist]。

这种「工具 + 意识」的组合,是把性能从「事后补救」变成「开发过程中的基本素养」。Google 还通过 Play Console 的 Vitals 面板,把性能数据直接暴露给开发者,让「用户在实际设备上的体验」成为开发流程的一部分。

从 Android 12 开始,Google 持续丰富 Jetpack 中的性能工具。Baseline Profiles(2022 前后进入稳定使用)随 APK/AAB 打包,并通过 Jetpack ProfileInstaller 在 API 24+ 设备上安装到 ART,让 App 从首次启动起获得更接近 AOT 编译的收益;它不是 Android 13 才开始分发的系统能力。JankStats 库(2022 alpha)帮助开发者在生产环境中自动收集帧率数据;Macrobenchmark(2021-2022)让自动化性能测试进入 CI 流程 [已验证: 官方文档, developer.android.com]。到 Android 16,这些工具已迭代多个版本,Google 同时在 Perfetto 中加入更多系统级 Track(如 Jobscheduler Track、Frame Timeline 改进),并强化 Play Console Vitals 的性能指标覆盖。工具演进的方向很清楚:把性能分析从少数专家的手工流程,变成工程师日常开发的一部分。

## 扩展:性能工程师的能力模型

如果要画一幅性能工程师的「能力雷达图」,它至少应该包含这几个维度:

**系统理解力**:理解 Android 从内核到 Framework 到 App 的完整栈。不需要每个模块都精通到能写代码,但需要知道每个模块的职责和它们之间的交互方式。这正是本书前半部分(第 1 章到第 6 章)所覆盖的内容。

**工具使用力**:熟练使用 Perfetto、Profiler、Simpleperf、内存分析工具等,知道什么时候该用什么工具,能从工具输出中提取有用的信息。第 13 章和第 14 章专门讲工具。

**分析推理力**:从数据到结论的推理能力。看到 Trace 中的一个异常,能推导出可能的原因,然后验证或排除。这需要实践积累,但也需要方法论--这正是本章讨论的核心。

**代码洞察力**:能从代码层面理解性能问题的根源。不是所有的性能问题都能从 Trace 中看出来,有时候需要读代码才能理解为什么某个操作会那么慢。

**成本/ROI 评估力**:性能优化也会影响基础设施成本、云资源和端侧功耗。面对大规模业务时,需要估算一次优化能减少多少 CPU 时间、带宽、存储或用户等待时间,再决定投入多少工程资源。

**沟通影响力**:性能优化往往涉及多个团队--App 团队、系统团队、SDK 团队。推动优化实施需要清晰地表达问题、量化影响、说服利益相关者。

Brendan Gregg 在讨论性能工程团队的价值时,特别强调了性能工程师的一个独特作用:他们的作用远不止修 bug--更重要的价值在于帮助整个团队建立性能意识和能力 [已验证: 来源见 Brendan Gregg, Performance Engineering Teams, 2025]。Netflix 的火焰图自助服务工具就是一个成功的例子--它不是一个团队关起门来优化性能,而是把性能分析的能力交给所有开发者,让每个人都能在自己的代码中找到优化机会。

## 小结

性能优化的「道」回答的是「为什么优化」和「朝什么方向优化」--用户体验是起点,数据是判断依据,持续优化是基本态度。

性能优化的「术」回答的是「怎么优化」--从宏观到微观的分析方法、对症下药的优化策略、从自动化测试到线上监控的防劣化体系。

性能优化的「器」回答的是「用什么优化」--Perfetto 是全局视角的入口,专项工具负责深入分析,工具链的组合使用形成了标准的工作流。

三者之间的关系是:道定方向,术给方法,器提效率。没有道的术是盲目的,没有术的道是空洞的,没有器配合的术是低效的。

后面的章节会继续深入这些方向:第 15.2 节讨论系统级优化和 App 级优化的差异与配合,第 15.3 节讨论如何建立和选择性能指标体系,第 15.7 节讨论如何高效地阅读和利用 AOSP 源码来深入理解系统行为。

## 参考资料

- Brendan Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd Edition, Addison-Wesley, 2020
- Jeff Dean & Sanjay Ghemawat, "Performance Hints", abseil.io/fast/hints.html, 2023-2025
- Brendan Gregg, "Why You Need a Performance Engineering Team", 2025 (kernel工匠 译文)
- Gracker, "Android Perfetto 系列 1:Perfetto 工具简介", androidperformance.com, 2024
- Gracker, "Android 性能优化典范综述", androidperformance.com, 2015
- Yingyun, "OS 设计之性能设计", androidperformance.com, 2023
- Google, "Android Performance Patterns", YouTube, 2015
- Google, "App performance", developer.android.com/topic/performance
- Google, "Benchmark your app", developer.android.com/topic/performance/benchmarking
- Google, "Android Vitals", developer.android.com/topic/performance/vitals
- Knuth, "Structured Programming with go to Statements", Computing Surveys, 1974

### A Comparative Study of Android Performance Issues in Real-world Applications and Literature
- 来源:https://arxiv.org/abs/2407.05090
- 类型:论文(ACM 期刊,2025-10)
- 摘要:对 Google Play(60,684 条负面评论)、Stack Overflow(749,067 帖子)、GitHub(16,977 issue + 344,922 commit)的大规模实证研究,构建了 7 类 Android 性能问题 + 82 个贡献因子分类体系。核心发现:研究者过度关注能耗(81.18%),用户最关心响应性(62.3%),开发者最头疼内存消耗(80.6%)。识别出 6 类代码模式:API 误用、未释放引用、冗余对象、大规模数据、UI 操作、其他。
- 入库时间:2026-04-07
