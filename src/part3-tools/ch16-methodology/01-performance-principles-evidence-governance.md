---
title: Android 性能优化原则、实证与治理
chapter: '16.1'
section: '16.1'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1；Android SDK API 37；AndroidX Benchmark 1.4.1（当前稳定版）；Android Developers 与 Perfetto 文档
confidence: medium-high
sources:
- type: aosp
  tag: android-17.0.0_r1
  path: packages/modules/Profiling/framework/java/android/os/ProfilingManager.java
- type: aosp
  tag: android-17.0.0_r1
  path: packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/base/core/java/android/view/FrameMetrics.java
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  tag: android-17.0.0_r1
  path: art/profman/profman.cc
- type: aosp
  tag: android-17.0.0_r1
  path: system/extras/simpleperf/README.md
- type: official
  path: developer.android.com/topic/performance
- type: official
  path: developer.android.com/topic/performance/benchmarking/benchmarking-overview
- type: official
  path: developer.android.com/jetpack/androidx/releases/benchmark
- type: official
  path: developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- type: official
  path: developer.android.com/reference/androidx/profileinstaller/ProfileVerifier.CompilationStatus
- type: official
  path: developer.android.com/reference/android/os/Build.VERSION
- type: official
  path: developer.android.com/topic/performance/tracing
- type: official
  path: developer.android.com/topic/performance/vitals
- type: blog
  path: abseil.io/fast/hints.html
- type: book
  path: Brendan Gregg - Systems Performance, 2nd Edition
- type: paper
  path: arxiv.org/abs/2407.05090
- type: paper
  path: https://arxiv.org/pdf/2407.05090v3
- type: artifact
  path: https://github.com/Dianshu-Liao/Android-Performance-Analysis
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
- type: official
  path: https://developer.android.com/topic/performance/performance-measurement-examples
- type: official
  path: https://developer.android.com/reference/android/view/View#invalidate()
- type: official
  path: https://developer.android.com/reference/android/view/View#requestLayout()
- type: official
  path: https://developer.android.com/reference/android/content/SharedPreferences
- type: official
  path: https://source.android.com/docs/core/perf/cached-apps-freezer
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java
- type: source
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/IPCThreadState.cpp
- type: source
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/benchmarking-overview
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci
- type: source
  path: https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro/1.4.1/benchmark-macro-1.4.1-sources.jar
- type: source
  path: https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro-junit4/1.4.1/benchmark-macro-junit4-1.4.1-sources.jar
- type: official
  path: https://developer.android.com/topic/performance/vitals
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles
- type: official
  path: https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations
- type: official
  path: https://perfetto.dev/docs/instrumentation/track-events
- type: source
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1
tags:
- methodology
- philosophy
- tools
- best-practices
- android
- research
- code-review
- performance-patterns
- empirical-study
- governance
- observability
- benchmark
- ci
- budget
- release
related_chapters:
- '14.1'
- '16.2'
- '16.3'
- '16.7'
- '7.1'
- '8.1'
- '8.3'
- '9.1'
- '15.6'
- '15.10'
- '16.5'
consolidated_from:
- 15.12 Android 性能优化研究方法论
- 15.9 从采集到治理的反馈回路
- 15.10 性能治理工程化
- src/part3-tools/ch16-methodology/01-philosophy.md
- src/part3-tools/ch16-methodology/08-empirical-performance-issues.md
- src/part3-tools/ch16-methodology/09-performance-governance.md
pipeline_stage: ready-to-publish
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
last_consolidated_at: '2026-08-24'
---

# Android 性能优化原则、实证与治理

性能工作从用户场景和可测指标开始，经过证据采集、责任定位、单变量修改和回归验证，最后进入长期门禁。经验模式可以帮助提出假设，但结论必须回到当前版本和设备数据。

## 目标、指标、工具与实验设计

### 道、术、器的分工

性能工程面对的对象，是一个在特定设备、系统版本、构建产物和运行环境中执行的完整系统。一次卡顿可能同时包含主线程排队、Binder 等待、RenderThread 提交、GPU 执行和 SurfaceFlinger 合成；一次启动变慢也可能来自编译状态、磁盘缓存、进程状态或业务初始化。Binder 负责 Android 跨进程调用，RenderThread 提交应用的绘制命令，GPU 执行图形任务，SurfaceFlinger 负责系统级图层合成。只盯住某个函数耗时，很容易把症状当成原因。

「道、术、器」分别承担三类工作：

- 「道」决定要改善哪个用户场景，以及用什么数据判断改善是否成立。
- 「术」规定从现象到证据、从假设到验证的分析顺序。
- 「器」负责采集、查询和呈现证据，每种工具都有可见范围与扰动成本。

平台结论以 Android 17 / API 37 / `android-17.0.0_r1` 为上限。Android 7、10、11 等历史节点用于说明 API 和观测口径的演进。这里不分析内核实现，因此不引用 `android17-6.18-2026-06_r6` 的具体行为。

### 「道」：从用户场景定义性能

#### 从关键用户旅程开始

「应用很慢」无法直接转成实验。工程师需要把反馈改写成可复现的关键用户旅程（Critical User Journey，CUJ），并记录清楚起点、终点和成功条件。

| 用户反馈 | 可复现的 CUJ | 适合观察的结果 |
|---|---|---|
| 打开首页慢 | 进程不存在时点击图标，直到首页达到可交互状态 | TTID、TTFD、冷启动分位数、首帧前主线程任务 |
| 列表不流畅 | 固定数据集、固定手势滚动同一列表 | 超时帧分布、FrameTimeline（Android 12+ 的预期/实际帧时间线）、主线程与 RenderThread 活动 |
| 点击后没反应 | 从输入事件到目标界面或业务确认信号 | 输入延迟、主线程 runnable（可运行、等待 CPU）/blocked（阻塞等待）、Binder 与 I/O（存储或网络输入输出）等待 |
| 使用一段时间后内存上涨 | 重复进入并退出同一业务流程 | Java/native heap（Java/原生代码堆内存）、RSS/PSS（进程驻留内存/按共享比例计入的物理内存）、对象保留路径、分配调用栈 |
| 后台耗电 | 固定时长进入后台并保持相同网络条件 | wakelock（唤醒锁）、alarm（定时触发）、job（后台任务）、网络活动、thermal（温控状态）与电量归因 |

TTID（Time to Initial Display）关注首帧出现，TTFD（Time to Full Display）还包含应用调用 `reportFullyDrawn()` 前的工作。后者是否可信，取决于应用是否在业务内容稳定可用后调用这个方法。

同一个指标不能替代用户旅程。冷启动 P50 改善，并不能证明温启动、低端机或首次安装后的体验也改善；平均帧耗时降低，也不能覆盖少量冻结帧。性能结论至少要写成下面这组条件：

> CUJ × App 版本 × 构建类型 × 设备档位 × Android 版本 × 编译状态 × 环境条件 × 统计量

缺少其中一项，后续复测就可能换了实验对象。

#### 用户感知与系统指标要能互相定位

用户感知提供优先级，系统指标提供归因线索。两者之间需要一层稳定映射：

- 启动体验可映射到 TTID、TTFD、冷/温/热启动类型，以及首帧前各阶段耗时。
- 流畅度可映射到错过 deadline（每帧完成时限）的帧、冻结帧、实际刷新率和当时的 UI 状态。
- 响应性可映射到输入事件、消息队列、线程调度、锁等待、Binder 和 I/O。
- 稳定性可映射到用户感知 ANR（应用无响应）、崩溃、OOM（内存不足错误）、LMK（系统因低内存结束进程）与对应场景。
- 功耗可映射到任务执行时间、唤醒来源、网络无线电活动、thermal 状态和电量统计。

指标只负责描述现象。即使 Trace 显示某帧主线程发生 GC（垃圾回收），也需要继续判断分配来自哪里、GC 是否跨过该帧 deadline、同一问题能否在相同条件下复现。

#### 实验室数据与线上数据各有职责

实验室测量适合控制变量、复现问题和验证改动。线上数据适合判断影响范围、设备分布和长尾趋势。二者无法互相替代：

- Macrobenchmark（端到端性能基准测试）能稳定重复启动或滚动 CUJ，但测试设备不能代表全部用户。
- Android vitals（Google Play 汇总的线上质量数据）能给出真实设备上的崩溃、ANR、慢渲染和电量信号，但聚合数据通常不足以直接定位代码。
- JankStats（Jetpack 帧监控库）能把帧耗时与应用提供的 UI 状态一起交给回调，但应用仍要设计采样、聚合、上传、隐私和版本维度。
- Perfetto（系统级 trace 工具）能保存一次复现过程的运行时间线，但未启用的数据源不会事后出现在 Trace 中。

推荐的工作顺序是：用线上数据选择场景和设备层级，用实验室环境复现并定位，再用基准测试和按版本、设备等维度分组的线上数据验证改动。

#### 性能维护要进入日常变更流程

性能会随业务代码、依赖、编译器、系统版本和设备环境变化。一次专项优化只能改变当时的基线。可持续的维护机制包含四类记录：

1. 关键 CUJ 的负责人、测试脚本与版本化指标定义。
2. 固定设备或可比较设备池上的基准数据。
3. 超出预算后的复核规则，包含允许的噪声范围和人工豁免。
4. 按发布版本、设备型号和 Android 版本拆分的线上指标。

预算不应只写一个数字。例如“冷启动低于 1.5 秒”缺少启动类型、设备、编译模式和分位数；“帧耗时低于 16.67 ms”也忽略了动态刷新率和平台计算的 frame deadline。可执行的预算会同时写明测量协议。

### 「术」：从现象到可复查结论

#### 六步分析流程

##### 1. 定义现象

记录 CUJ、出现频率、受影响版本、设备和网络条件。若来自线上告警，还要记录指标口径、时间窗口和样本量。此时不要提前指定根因。

##### 2. 建立基线

在修改代码前运行同一套测试。保留原始结果、构建产物标识、设备温度、刷新率、编译模式和系统版本。P50（中位数）反映典型情况，P90/P95/P99 等高分位用于观察长尾；小样本应同时保留每次测量值。

##### 3. 采集能区分假设的证据

采集配置应由假设决定。启动问题需要进程启动、主线程、Binder、I/O 和 ART（Android Runtime，Android 运行时）相关事件；掉帧需要 FrameTimeline、Choreographer（帧回调调度器）、RenderThread、SurfaceFlinger、调度与频率信息；C/C++ 等 native CPU 热点需要采样栈和符号。把所有数据源都打开，会增大 Trace、提高扰动并降低分析效率。

##### 4. 提出可证伪的假设

“某 SDK 很慢”过于宽泛。更可用的写法是：“冷启动首帧前，主线程同步调用该 SDK 的初始化函数，并占据一段连续执行时间；延后该调用后，TTID 分布应下降，且 TTFD 和功能可用性不回退。”假设中要包含证据、改动和预期结果。

##### 5. 一次只改变一个主要变量

同时修改线程模型、缓存、布局和编译配置，即使指标改善，也很难判断贡献来自哪里。高风险改动可分阶段提交，每一阶段保留独立测量结果。

##### 6. 复测并检查副作用

使用相同协议复测，比较分布与置信区间（估计结果的不确定范围），并检查内存、功耗、稳定性和业务正确性。把主线程工作移动到后台线程可能改善帧耗时，也可能增加 CPU 竞争、启动后的尾部延迟或耗电。

#### 用证据等级约束结论

性能调查很容易从“两个事件同时出现”跳到“其中一个导致另一个”。报告应把结论分成四级，并明确当前停在哪一级：

| 证据等级 | 需要回答的问题 | 可以写出的结论 |
|---|---|---|
| 观测 | 目标窗口里发生了什么 | 两个事件在时间上重叠，或某项指标发生变化 |
| 机制 | 调用、等待或资源关系怎样连接两者 | 存在一条能解释影响方向的路径 |
| 干预 | 改变该机制后，预期中间量是否随之变化 | 当前改动与改善一致 |
| 复现 | 不同轮次、设备或灰度（分批发布）对照是否保持同方向 | 结论适用于已经覆盖的总体 |

每个候选原因还应写成“假设—预期观测—反证—状态”。例如，若假设主线程 CPU bound（耗时主要来自 CPU 计算），预期 wall time（经过的总时间）接近 on-CPU time（线程实际占用 CPU 的时间），且采样栈集中在稳定调用链；如果大部分时间实际是 Runnable、Binder 等待或锁等待，这条假设就应降级或被排除。保留被证伪的假设，可以避免下一位排查者重复同一条无效路径。

#### 测量协议比“多跑几次”更有价值

常见偏差及控制方法如下：

| 偏差来源 | 会改变什么 | 控制方法 |
|---|---|---|
| Debug 与 Release 构建差异 | 优化、插桩、断言、资源与代码布局 | 使用接近发布配置的可测构建，并记录签名和混淆状态 |
| JIT（运行时即时编译）/AOT（预先编译）/Baseline Profile（随应用提供的重点代码编译规则）状态 | 启动和热点代码执行时间 | Macrobenchmark 中固定 `CompilationMode`，不要混合比较不同编译状态 |
| 设备温度与 DVFS（动态电压与频率调节） | CPU/GPU 频率和持续性能 | 记录 thermal 状态，随机化实验顺序，必要时等待设备回到同一温度区间 |
| 刷新率变化 | 帧 deadline 与 jank（卡顿）判定 | 记录实际刷新率，优先使用 FrameTimeline deadline，不套用固定 16.67 ms |
| 缓存与进程状态 | 冷/温/热启动、磁盘和网络耗时 | 明确清理范围；不要把清进程、清数据、清页缓存混为同一种“冷启动” |
| 采样或插桩 | CPU 时间、调度和 Trace 体积 | 使用能回答问题的最低采样率和最小数据源集合，并做有/无采集对照 |
| 自动化脚本不稳定 | 手势路径、页面状态和等待条件 | 用语义条件等待页面，不用固定 `sleep` 代替业务完成信号 |

AndroidX 官方将 Macrobenchmark 定位为进程外的端到端测量工具，并允许控制启动和编译状态；Microbenchmark 用于进程内代码片段。二者的结果范围不同，不能直接互换。

#### Android 17 的平台观测边界

##### FrameMetrics 与 FrameTimeline

`FrameMetrics` 从 API 24 提供窗口帧的阶段耗时。Android 17 的 `FrameMetrics.java` 仍定义 `TOTAL_DURATION`、`DEADLINE`、`GPU_DURATION` 和 `FRAME_TIMELINE_VSYNC_ID` 等指标。`TOTAL_DURATION < DEADLINE` 是源码注释给出的 deadline 判断关系；应用仍要考虑回调开销、丢失的帧信息和 UI 工具栈差异。

Android 12 引入的 FrameTimeline 为应用帧与 SurfaceFlinger 帧提供关联和 jank 信息。分析 Android 17 Trace 时，应沿实际 vsync ID（垂直同步标识）、deadline 和 jank type（卡顿类型）追踪，避免只按 60 Hz 预算做推断。

##### Perfetto

Android 官方文档把 Perfetto 定义为 Android 10 起的平台级 tracing 工具。它能合并应用、Framework、Native 服务和内核数据源，但 Trace 只包含采集配置启用且生产者实际写入的事件。没有方法级事件时，系统 Trace 无法自动给出某行 Java/Kotlin 代码的耗时；这类问题需要应用插桩、Android Studio CPU Profiler、Simpleperf（Android CPU 采样工具）或可映射回函数名的采样栈补充。

Trace Processor 会把采集数据解析成可查询表。SQL 结果能复现筛选和聚合过程，适合放进回归检查；查询仍要注明 Perfetto 版本、输入 Trace，以及预置 metric（指标）和表结构的版本。

##### ProfilingManager 与 ProfilingTrigger

Android 17 的 Profiling Mainline 模块（可独立更新的系统性能采集模块）保留主动采集接口 `requestProfiling()`，并由 `registerForAllProfilingResults()` 注册全局结果回调；它也支持由系统事件触发的 profiling trigger。`addAllProfilingTriggers()` 和 `requestRunningSystemTrace()` 都存在于 API 37 SDK 与 `ProfilingManager.java` 中，但官方 API 参考把它们的首次引入版本标为 36.1。需要兼容 minor SDK（同一 Android 主版本内追加 API 的小版本）的代码应使用 `SDK_INT_FULL` 和 `VERSION_CODES_FULL` 判断，不能只比较 `SDK_INT`。

`ProfilingTrigger.java` 在 `android-17.0.0_r1` 中枚举了 fully drawn、ANR、运行中 trace 请求、若干 kill 原因、OOM、异常、过量 CPU、冷启动和兼容性等类型。源码的 `isValidRequestTriggerType()` 对多种类型使用 feature flag（系统功能开关），系统还会执行限流、权限和资源判断。系统触发的结果只能通过全局回调接收，内容可能是 Trace、调用栈采样或 heap dump（堆快照）；注册成功不保证每次事件都会返回文件。

##### Baseline Profiles 与 ART

Baseline Profile 属于构建、分发和 ART 编译协作能力，不绑定某一个 Android 大版本。当前官方流程会把人类可读规则编译为二进制文件：APK 中的路径是 `assets/dexopt/baseline.prof`，AAB（Android App Bundle）中的路径是 `BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`。Play 安装、ProfileInstaller（Jetpack profile 安装库）和设备后台 dexopt（DEX 优化与编译）的参与方式取决于 Android 版本与安装渠道。

Android 17 的 `art/profman/profman.cc` 仍负责读取、合并和分析 profile，编译决策还会进入 ART 的 dexopt/dex2oat 路径。`ProfileVerifier` 的安装或编译状态要按其枚举语义读取，不能只凭 APK 内存在 `baseline.prof` 就判定目标代码已经完成 AOT 编译。

##### BLAST 的版本含义

AOSP（Android Open Source Project，Android 开源项目）在 Android 11 tag（版本标签）已包含 `frameworks/native/libs/gui/BLASTBufferQueue.cpp`，Android 17 仍保留该实现。BLAST 负责协调图形 buffer（缓冲区）与 SurfaceControl transaction（事务），但这个历史节点不等于所有旧版 BufferQueue 指标都失效，也不代表 App 侧某个超时能直接归因到 BLAST。渲染诊断仍需结合 FrameTimeline、BufferQueue/SurfaceFlinger 事件、fence（图形生产者与消费者之间的同步信号）和线程调度。

#### 按瓶颈类型选择优化方向

| 证据形态 | 常见方向 | 仍需排除的情况 |
|---|---|---|
| 关键线程长时间 runnable，CPU 饱和 | 减少工作量、改进算法和数据布局、消除重复计算 | 线程被更高优先级任务抢占、thermal 降频、错误的 CPU affinity（允许运行的核心集合） |
| 关键线程 blocked 或 sleeping（睡眠/等待态） | 检查锁、Binder、futex（用户态同步需要阻塞时的内核等待）、I/O 和条件等待 | 正常的异步等待、缺失唤醒事件、Trace 时间轴或区间关联错误 |
| RenderThread/GPU 超过 deadline | 减少绘制复杂度、过度绘制、昂贵 shader（GPU 着色程序）或资源上传 | SurfaceFlinger 合成、fence 等待、刷新率切换、驱动与 GPU 频率 |
| Java heap 持续增长 | 检查保留路径、生命周期、缓存上限 | 预期缓存、延迟 GC、native/graphics 内存被误算为 Java heap |
| native 分配持续增长 | 用 heapprofd（Perfetto 原生堆采样器）或其他采样栈定位分配点，核对释放路径 | 采样偏差、allocator（内存分配器）缓存未归还、`mmap` 映射/共享内存和 GPU 内存 |
| 网络阶段长尾 | 拆分 DNS 域名解析、连接、TLS 加密握手、TTFB（收到首字节的时间）、下载和重试 | 服务端排队、无线电状态、代理/VPN（虚拟专用网络）、缓存命中差异 |
| 长时间高功耗或发热 | 缩短活动时间、减少唤醒与无效任务、检查 thermal 反馈 | 电量归因窗口过短、设备充电状态、其他进程和屏幕亮度 |

优化时优先删掉不必要的关键路径工作。异步化只能改变执行位置；后台线程仍会消耗 CPU、内存带宽和电量，也可能与渲染线程竞争。

### 「器」：按问题选择证据工具

#### 工具能力对照表

| 工具 | 适合回答 | 无法单独回答 |
|---|---|---|
| Macrobenchmark | 启动、滚动、动画等端到端 CUJ 是否回退 | 某个内部函数为何变慢 |
| Microbenchmark | 一段进程内 CPU 代码在受控循环中的成本 | 完整 App、系统调度、I/O 和用户旅程 |
| Perfetto / Trace Processor | 多进程时间线、调度、FrameTimeline、Binder、频率和已启用数据源 | 未采集的方法、对象保留关系、业务语义 |
| Android Studio CPU Profiler | App 方法、线程活动和采样/插桩调用栈 | 完整系统因果关系；不同模式的扰动也不同 |
| Android Studio Memory Profiler / heap dump | Java/Kotlin 分配与对象保留关系 | native/GPU/共享内存的完整归因 |
| heapprofd | 可采样的 native heap 分配调用栈 | 每次分配的无损记录、Java 对象引用图 |
| Simpleperf | CPU 采样、调用栈、硬件事件；函数符号和权限齐全时可覆盖 Java、Native 与部分内核 | 阻塞等待的完整因果关系、GPU 命令时间线 |
| JankStats | 帧级 jank 启发式判断和应用 UI 状态 | 系统侧根因与完整渲染管线 |
| Android vitals | 线上设备分布、版本趋势和若干质量指标 | 单次问题的完整 Trace 与代码级根因 |
| `dumpsys` | 读取某一时刻的系统服务状态和聚合计数 | 高精度时序和跨进程因果关系 |

“Perfetto 只看线程、Simpleperf 只看 Native”这类记忆法会误导选型。Perfetto 可包含调用栈和多类 profiling 数据，Simpleperf 在配置、运行环境和符号齐全时也能分析 Java、Native 与内核代码。证据范围取决于本次实际采集的字段，不能由工具名称推断。

#### 三条常用组合路径

##### 启动

1. Macrobenchmark 固定 `StartupMode`、`CompilationMode` 和 CUJ，建立 TTID/TTFD 分布。
2. Perfetto 查看进程创建、首帧前主线程、Binder、I/O、ART、RenderThread 与 SurfaceFlinger。
3. 对可疑函数补充应用 slice（自定义时间区间）、CPU Profiler 或 Simpleperf 采样。
4. 修改后复跑相同基准，检查启动后的交互、内存和功耗。

##### 流畅度

1. 用 JankStats 或线上指标找到受影响的页面、版本和设备组。
2. 在相同刷新率和数据集下采集 FrameTimeline Trace。
3. 沿超时帧检查主线程、RenderThread、GPU、SurfaceFlinger、fence 和调度。
4. 用 Macrobenchmark 的 `FrameTimingMetric`（帧时序指标）或项目指标做回归测试。

##### 内存

1. 用 RSS/PSS、Java/native heap 和 GC 趋势确认增长发生在哪个内存域。
2. Java 对象保留使用 heap dump；native 分配使用 heapprofd 或采样工具。
3. 将调用栈映射到版本一致的函数符号和源码，区分业务持有、allocator 保留和共享内存。
4. 重复同一 CUJ，验证增长斜率、峰值和退出后的回落。

### 投入产出与性能预算

#### 排优先级时看四个维度

- **影响人数**：受影响用户、设备型号、系统版本和发布版本占比。
- **出现频率**：每次启动、每天一次，还是极少出现。
- **体验损失**：延迟长度、操作是否中断、数据是否丢失、是否导致退出。
- **修复把握与成本**：证据是否充分，改动范围、验证成本和副作用风险。

可以用“影响人数 × 频率 × 损失程度”帮助排序，但不要把主观评分伪装成精确数学模型。低频的严重 ANR、OOM 或数据损坏仍可能高于高频的轻微波动。

#### 预算是一份版本化测量合同

一条可执行预算应包含：

- CUJ 和起止信号；
- App 版本、构建类型和混淆状态；
- 设备档位、Android 版本和刷新率；
- 编译模式、安装渠道与 profile 状态；
- 样本次数、统计量和允许噪声；
- 超限后的复测、审批与回滚规则。

预算也要随产品阶段调整。新增安全检查或无障碍能力可能带来可接受成本；团队应记录成本、用户收益和批准人，避免为了守住旧数字而隐藏必要工作。

#### 用回归测试保护已经取得的收益

基准测试适合监控稳定 CUJ。CI（Continuous Integration，持续集成）中出现波动时，应先检查设备、温度、系统任务和测试脚本，再判断代码回退。单次失败不宜自动归因给最近提交；连续分布漂移也不应被一句“测试不稳定”长期忽略。

线上发布后继续按版本和设备组观察。Android vitals 的用户感知崩溃率、ANR、慢渲染和电量指标各有采集条件与评估窗口，项目内指标也要记录采样率和分母。

### 性能工程师的能力模型

- **系统理解**：能从 App、Framework、Native 服务、内核调度到硬件资源解释一次 CUJ。
- **实验设计**：知道怎样固定变量、选择样本和识别测量扰动。
- **工具使用**：能配置采集、写查询、处理符号，并识别工具的不可见范围。
- **源码阅读**：能把 Trace 事件、API 行为和版本差异映射到对应版本 tag 的代码。
- **统计判断**：能看分布、长尾和置信范围，不用单次结果下结论。
- **工程决策**：能比较用户影响、修复成本、副作用和维护成本。
- **协作表达**：能提交复现步骤、证据、假设、改动与复测结果，让其他团队复查。

一份合格的性能报告，至少让没有参与排查的人回答五个问题：什么场景、影响谁、证据在哪里、为何采用这项改动、复测怎样证明收益。

### 让调查结果可以复用

每次调查至少留下问题场景、设备与构建、原始数据、查询或时间窗、源码 tag、候选假设、干预结果、副作用、适用边界和回退条件。截图可以辅助沟通，但不能替代可重跑的查询和妥善保存的原始文件。

机制文档与操作手册分开维护：前者解释源码、数据语义和版本边界，后者记录环境、命令、预期输出、失败处理与清理步骤。机制变化时不必重写每份操作记录，工具入口变化时也不应改写历史结论。最终把问题、证据、修改、复测和未确认项关联到同一个版本化记录，再交给后文的团队治理流程持续验收。

### 交付前检查表

- [ ] CUJ、起止信号和成功条件是否明确？
- [ ] Android、App、构建、设备和编译状态是否记录？
- [ ] 原始数据与查询是否可复查？
- [ ] Trace 配置是否包含区分当前假设所需的数据源？
- [ ] 结论是否区分观测事实、推断和待排除项？
- [ ] 改动前后是否使用同一测量协议？
- [ ] 是否检查内存、功耗、稳定性和功能副作用？
- [ ] 是否建立可重复的回归测试或按版本、设备拆分的线上指标？

### 小结

「道」把模糊反馈转换为有边界的用户旅程和指标；「术」用可证伪假设、受控实验和复测形成可复查结论；「器」提供各自范围内的证据。团队把这三部分写进同一份性能报告，后续版本才能复用结论，也能判断旧结论在 Android 17 上是否仍成立。

## 真实问题模式与证据要求

工作流程建立后，常见问题模式用于缩小候选范围。代码模式只能提示风险，仍需运行证据确认是否构成瓶颈。

性能团队很容易被手边的工具塑造优先级：有 heap dump（堆内对象及引用关系的快照），就多查泄漏；有功耗实验室，就多查能耗；有帧时间面板，就多查卡顿。实证研究能提供另一组参照：用户报告什么、开发者讨论和修复什么、论文研究什么。

这类研究适合校准问题覆盖面，不能直接代替本产品的线上数据。样本来源、过滤方法、最终样本量和 Android 版本都会限制结论的外推范围，也就是这些结论能否推广到其他产品、版本或人群。

### 固定论文版本与统计口径

引用版本为 [arXiv:2407.05090v3](https://arxiv.org/pdf/2407.05090v3)，revision（修订版）日期为 2025-10-11。论文的复现资料位于 [Android-Performance-Analysis](https://github.com/Dianshu-Liao/Android-Performance-Analysis)。

版本号必须写进引用。当前 arXiv 摘要页、v3 PDF 和复现仓库 README 存在摘要数字不同步：

- v3 PDF 使用 85 篇论文、14 个公开工具、12 个公开数据集；
- v3 PDF 给出的未覆盖比例是：研究 57.14%、工具 63.41%、数据集 70.73%；
- arXiv 摘要页截至 2026-08-14 仍显示“工具未覆盖 76.39%、数据集未覆盖 66.67%”，与 v3 PDF 的 63.41% 和 70.73% 冲突；
- 复现仓库 README 对汇总表仍写“66 篇论文”，与 v3 PDF 纳入 85 篇冲突。

下文的分子、分母和比例全部以 v3 PDF 正文、表格及结论为准。引用“论文发现”时也要带 revision，避免将不同修订版的数字放在一张表里。

### 数据从哪里来

研究的现实世界部分采用“原始采集 → 87 个性能关键词过滤标题 → 两名作者人工核查”的流程。最终用于分类的样本远小于原始采集量：

| 数据源 | 原始数据 | 关键词过滤后 | 人工核查后 | 代表的视角 |
|---|---:|---:|---:|---|
| Google Play 负面评论 | 60,684 | 165 | 114 | 用户 |
| Stack Overflow Android 问题 | 749,067 | 2,158 | 1,484 | 开发者 |
| GitHub Issues | 16,977 | 149 | 69 | 开发者 |
| GitHub Commits | 344,922 | 558 | 222 | 开发者 |

Google Play 的 60,684 条负面评论来自 909,430 条评论的情感分析模型筛选，该模型用于判断文本偏正面还是负面。GitHub 数据来自 1,643 个同时出现在 F-Droid（开源 Android 应用仓库）与 Google Play 的开源应用。人工核查的一致性以 Cohen's kappa 评估；它是扣除偶然一致后衡量标注者一致性的指标，四组结果为 0.868 至 0.944。

论文部分从五个学术数据库检索，经 venue（期刊、会议等发表场所）过滤、人工排除和前后向 snowballing（沿参考文献与被引论文继续查找），纳入 85 篇 2012—2024 年的研究。论文、工具与数据集可同时覆盖多个性能类别，所以“69/85 篇研究能耗”不是互斥饼图。

#### 这些比例能回答什么

它们描述的是这项研究最终样本中的分布，可以用于：

- 检查团队是否只覆盖某一类性能后果；
- 比较用户可感知问题、开发者修复记录与研究投入的差异；
- 寻找静态工具较难覆盖的运行时因素；
- 设计 Code Review 和动态验证的互补范围。

它们无法直接回答：

- 某个产品的 ANR（Application Not Responding，应用无响应）、OOM（Out of Memory，内存不足）或耗电应占多少资源；
- 2026 年全部 Android 应用的总体问题分布；
- Android 17 新机制带来的增量风险；
- 某段可疑代码是否已经造成用户影响。

关键词只匹配标题，可能漏掉没有性能词的记录；最终用户评论只有 114 条，GitHub issue 只有 69 条；开源应用与商业闭源应用也可能不同。论文的 threats to validity（研究局限）章节明确列出了情感模型、抓取完整性、人工标注和样本代表性限制。

### 用户、开发者与研究者的关注点

#### 同一张表中的分母不同

| 视角与数据源 | 最常见类别 | 比例 | 分母含义 |
|---|---|---:|---|
| 用户：Google Play | Responsiveness | 62.3% | 114 条核查后评论 |
| 开发者：Stack Overflow | Memory Consumption | 66.1% | 1,484 个核查后问题 |
| 开发者：GitHub Issues | Memory Consumption | 60.0% | 69 个核查后 issue |
| 开发者：GitHub Commits | Memory Consumption | 80.6% | 222 个核查后 commit |
| 研究者：论文 | Energy Consumption | 81.18% | 69/85 篇论文，类别可重叠 |

用户最容易直接描述无响应、界面卡住、操作慢等结果。开发者的问答与修复提交更容易留下 OOM、泄漏、缓存和对象生命周期证据。85 篇论文中有 69 篇涉及能耗，研究投入明显偏向 Energy Consumption。

这些来源仍有交集。用户评论里也有能耗、存储和网络流量，开发者也修复响应性问题，研究也覆盖内存与响应性。研究支持的判断是“各来源的主导类别不同”，不能表述成“各方关注完全分离”。

#### 57.14%、63.41%、70.73% 的正确分子

论文先从现实世界样本归纳 63 个 contributing factors（促成因素），再纳入文献结果，形成包含 82 个因素的 taxonomy（分类体系）。最终分类体系比 63 个现实因素多 19 项；这个数字由 82−63 推得，论文没有另列一组 19 项统计。

| 覆盖对象 | 已覆盖 | 未覆盖 | 未覆盖比例 |
|---|---:|---:|---:|
| 学术研究对 63 个现实因素的覆盖 | 27/63 | 36/63 | 57.14% |
| 公开工具对 82 个综合因素的覆盖 | 30/82 | 52/82 | 63.41% |
| 公开数据集对 82 个综合因素的覆盖 | 24/82 | 58/82 | 70.73% |

27/63 是已研究的 42.86%，未研究数是 36，不能把 27 项写成未研究数量。14 个公开工具覆盖 30 个因素，12 个公开数据集覆盖 24 个因素；这里的“覆盖”只记录工具或数据集是否涉及某个因素，不等于工具对这些因素拥有稳定的工业检测率。

### 七类性能后果与 63/82 因素

论文刻意分开 consequence（后果）与 contributing factor（促成因素）：

- **后果**描述用户或工程系统观察到什么；
- **因素**描述哪些行为、资源或代码条件可能促成后果；
- 一个因素可以影响多个后果，一个后果也可能由多个因素共同产生。

例如，“主线程做图片解码”是因素；它可能引发响应性、内存与 CPU 后果。将“卡顿”“复杂布局”“主线程 I/O”写在同一层，会让告警、根因和修复措施混在一起。

为便于回查论文，表中保留英文类别名。Play Vitals 是 Google Play 汇总的线上质量指标，Macrobenchmark 是 Jetpack 的应用级基准测试工具，Binder 是 Android 的进程间通信机制，FrameTimeline 记录帧的预期与实际时间线。

`sched` 指内核调度事件；`heapprofd` 是 Perfetto 的 native 内存分配采样器；PSS 按比例分摊共享页，RSS 则统计进程驻留在内存中的全部页面；WAL 是 SQLite 的 write-ahead log（预写日志）。

| 论文后果类别 | Android 工程里的表现 | Android 17 常用证据 |
|---|---|---|
| Responsiveness | ANR、输入延迟、启动慢、帧延迟 | Play Vitals、ANR trace、Perfetto sched/Binder/FrameTimeline、Macrobenchmark |
| Memory Consumption | OOM、泄漏、频繁 GC、缓存增长 | heap dump、Memory Profiler、heapprofd、PSS/RSS、GC 与 kill 记录 |
| Energy Consumption | 后台 CPU、WakeLock、传感器/定位/网络活跃 | batterystats、Perfetto power/CPU、Job 与 alarm 记录、设备功耗计 |
| Storage Consumption | 数据库、缓存、日志、下载内容增长 | 应用目录分项、SQLite 大小与 WAL、文件 I/O、磁盘统计 |
| CPU Usage | 长时间 Running/Runnable、热点函数、线程竞争 | Perfetto sched、simpleperf、CPU time、线程池队列 |
| GPU Usage | GPU 工作过重、纹理/带宽压力、合成成本 | FrameTimeline、RenderThread、GPU counter（设备支持时）、SurfaceFlinger/HWC |
| Internet Data Usage | 重复下载、失控重试、后台传输 | Network Inspector、TrafficStats、抓包、请求与服务端日志 |

表里的工具是观测入口，不能与论文中的“自动检测工具覆盖率”混为同一指标。Perfetto 能展示调度、帧和 Binder 证据，但不会自动识别全部 82 个因素。

#### 版本边界

| 平台范围 | 响应性与帧证据 |
|---|---|
| Android 8—9 | `dumpsys gfxinfo ... framestats`、atrace/systrace、主线程与 RenderThread、ANR trace |
| Android 10—11 | 可使用 Perfetto system trace；FrameTimeline 尚不可用 |
| Android 12—17 | 可采集 FrameTimeline，并结合 sched、Binder、frequency、memory 与自定义 trace |

FrameTimeline 要求 Android 12 及以上。Expected Timeline 表示调度器给帧分配的时间窗；Actual Timeline 从 app 的 `Choreographer#doFrame` 或 native choreographer 回调开始，结束时间取 GPU 完成与 buffer post 中较晚者。它能帮助区分 app 与 SurfaceFlinger 侧 jank（卡顿帧），还要继续查看子 slice（有起止时长的区间事件）、线程状态、flow（跨轨道事件关联）与 `jank_type`（卡顿分类）。

下面的 Trace Processor SQL 用于列出 trace 中的 Actual Timeline 证据。Trace Processor 是 Perfetto 的 SQL 查询引擎：

```sql
SELECT
  process.name AS process_name,
  ts / 1e6 AS ts_ms,
  dur / 1e6 AS dur_ms,
  jank_type,
  present_type,
  on_time_finish,
  layer_name
FROM actual_frame_timeline_slice
LEFT JOIN process USING (upid)
ORDER BY ts
LIMIT 200;
```

查询结果给出帧归属、时长、present 与 jank 分类。它还没有定位 app 内部方法；需要用 token（帧标识）和 flow 对齐 `Choreographer#doFrame`、RenderThread、SurfaceFlinger。Running 表示线程正在 CPU 上执行，Runnable 表示已经可运行但仍在等待 CPU，Sleeping 通常表示正在等待事件；还要同时检查锁等待。

### 六类现实代码模式

论文从 Stack Overflow、GitHub issues 和 commits 的人工编码中归纳出六个宽泛类别。它们是经验分组，不是 Android API 规范，也不是看到一次就能判定为 bug 的静态规则。论文附带的个别代码片段同样要回到对应 Android 版本和运行证据复核。

#### 1. API Misuse（API 误用）

论文定义包含调用错误、调用顺序错误和参数错误。Android 工程中还可以把以下候选纳入审查：

- 主线程网络、文件、数据库或重计算；
- 主线程连续同步 Binder 调用；
- 生命周期结束后仍更新旧 UI；
- 对 API 的线程、顺序、资源释放或参数约束理解错误；
- 把异步 API 当作“没有 CPU、锁或磁盘成本”；
- 协程 scope（作用域）与工作生命周期不匹配。

`GlobalScope` 不会自动产生泄漏。它缺少结构化父任务；结构化并发要求子任务的生命周期与取消由父任务管理，而 `GlobalScope` 工作可能长于 Activity/Fragment。闭包若捕获页面、View 或回调，就可能延长引用生命周期。

页面工作通常使用 `lifecycleScope`，跨配置页面状态使用 `viewModelScope`，进程级长期任务需要明确 owner（负责管理任务生命周期的对象）、取消规则和持久化语义。取消 coroutine 也不会自动终止不支持取消的阻塞调用。

##### `requestLayout()` 与 `invalidate()` 不能互换

Android 17 的 `View.requestLayout()` 会清理 measure cache（测量结果缓存），设置 `PFLAG_FORCE_LAYOUT` 与 `PFLAG_INVALIDATED`，并在父节点尚未请求 layout 时向上传递。到 `ViewRootImpl.requestLayout()` 后，根节点设置 `mLayoutRequested` 并调度 traversal（一次 measure、layout、draw 流程）。当前帧是否重测整棵树，仍受父容器、measure spec（父节点给出的尺寸约束）、缓存、可见性和 traversal 状态影响。

`View.invalidate()` 标记绘制内容或区域失效，向父节点传播 damage（需要重绘的区域），必要时也会让 `ViewRootImpl` 调度 traversal。它通常不要求重新计算尺寸，但同一轮 traversal 可能因为其他状态执行 measure、layout、relayout 或 draw。几何尺寸与位置发生变化时用 `requestLayout()`；内容变化且边界不变时用 `invalidate()`；只改 transform、alpha 等渲染属性时还可能走 RenderThread 友好的属性动画路径。

“`requestLayout()` 必然完整 measure + layout + draw”与“`invalidate()` 只执行 draw”都过度简化了 Android 17 的实现。

#### 2. Unreleased References（未释放引用）

这一类关注长生命周期 owner 持有短生命周期对象：

- singleton、静态字段或进程级缓存持有 Activity、Fragment、View 或它们的 Context；
- listener、observer、callback、receiver 注册在长生命周期对象上，没有按协议解除；
- Fragment 的 ViewBinding 在 `onDestroyView()` 后仍被 Fragment 字段持有；
- Handler、Runnable、线程、coroutine 或 native callback 捕获已销毁页面；
- 无界缓存、集合或 map 保留旧 key/value。

匿名内部类和 lambda 不会一律捕获整个外部对象，应检查它们实际捕获的字段。注册与注销也应按 API 约定和 owner 生命周期判断，不能机械要求所有 listener 都在 `onDestroy()` 注销。

验证顺序是：观察 retained count（超过预期生命周期仍被保留的对象数）或 heap 增长，获取 heap dump，查看 dominator（释放后可连带释放大量下游对象的支配对象）与到 GC root（垃圾回收器起始引用）的路径，再确认对象已经越过预期生命周期。LeakCanary 适合开发和自动化场景，Memory Profiler 可继续分析 Java/Kotlin heap；native 分配问题再使用 `heapprofd`。单次 heap 大不等于泄漏。

#### 3. Redundant Objects（冗余对象）

论文把重复创建等价对象、互相递归创建对象和无意义重复实例化归到这一类。Android 10 及以上的默认 Concurrent Copying（CC）回收器以分代模式运行，会优先回收年轻对象；单次小对象分配不能直接判定为性能问题。高频分配仍可能增加 GC、CPU 和内存压力，影响要通过 allocation trace（分配记录）、GC 频率和帧证据验证。

下面的 View 代码展示可安全复用的绘制状态：

```kotlin
class StatusLineView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.RED
        strokeWidth = 2f
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val y = height / 2f
        canvas.drawLine(0f, y, width.toFloat(), y, linePaint)
    }
}
```

`Paint` 与 View 具有相同生命周期，并且只在 UI 线程使用，复用不会引入跨线程状态冲突。对象池不适合当作通用修复：池本身有生命周期、容量、清理和并发成本。优先移除已经证实的热点分配，修改后比较 allocation rate（单位时间的分配量）、GC 与帧指标。

Android Lint 的 `DrawAllocation` 可以发现一部分 draw/layout 内分配；Lint 告警是候选信号，运行时证据决定优先级。

#### 4. Large-Scale Data（大规模数据）

论文中的大数据模式包括一次性读取大文件、加载大图、上传大文件和处理超出设备资源的 payload（单次输入数据）。常见修复方向包括流式处理、分页、分块、限流、背压（让上游发送速度服从下游处理能力）、缓存和尺寸约束。

一张 4000 × 3000、每像素 4 byte 的 ARGB_8888 bitmap，像素数据为 48,000,000 byte，约 45.8 MiB（1 MiB = 2²⁰ byte）；实际占用还受 row bytes（每行实际占用字节数）、额外副本、纹理与解码流程影响。不能只按压缩图片文件大小估算内存。

审查大数据路径时记录：

- 输入上限和异常 payload；
- 是否把完整文件或响应读入单个数组/String；
- 解码目标尺寸与原图尺寸；
- 是否在主线程解析、拷贝或解码；
- 临时副本数与峰值内存；
- 取消、超时、重试和部分失败行为；
- 低内存设备与后台状态。

`InputStream.available()` 不是文件总大小，也不适合用来决定“读取完整文件”的 buffer。流式固定大小 buffer 或受控库通常更安全。

#### 5. UI Operations（UI 操作）

论文把 draw 循环、重复 UI 工作等归入 UI Operations。Android View 与 Compose 的审查方式不同，但都需要回答“哪些状态变化触发了多少工作”。

View 体系关注：

- 同一帧内重复 `requestLayout()` / `invalidate()`；
- 自定义 View 的 measure、layout、draw 与对象分配；
- RecyclerView 绑定、预取、复用与 payload 更新；
- 图片尺寸、阴影、模糊、clip、离屏渲染；
- 过深或多次测量的布局路径。

不存在通用的“超过 5 层一定慢”或“ConstraintLayout 一定更快”。约束求解、子节点数量、measure spec、权重、嵌套滚动和设备都会改变成本。用 Perfetto 的 `measure`、`layout`、`draw`、FrameTimeline 与 Macrobenchmark 量化。

Compose 关注 state 读取范围、recomposition（状态变化后重新执行受影响的 Composable）、remeasure/redraw、稳定性、Lazy 列表 key、昂贵计算和 snapshot（Compose 状态系统）写入。View 层级规则不能直接套到 Compose。

#### 6. Other Patterns（其他模式）

论文举出的其他模式包括一次投递大量 Runnable、主线程访问 `CookieManager` 等。工程中还常见：

- 主线程锁竞争；
- 线程池无界排队或并发过高；
- 反射、序列化或 JNI（Java 与 native 代码之间的接口）往返出现在高频路径；
- 重试没有上限或退避（失败后逐步拉长间隔）；
- 小 Binder 调用在循环中累积；
- 一个 observer、flow 或 callback 同时通知多个下游，造成重复工作。

单次调用快，循环后也可能超预算；单次调用慢，若在后台且不影响目标指标，也可能无需修改。Code Review 负责发现候选，benchmark、trace 和线上指标负责判定影响。

### 现代补充：主线程同步 Binder

主线程同步 Binder 把远端执行时间、服务端排队、锁、I/O 与 CPU 调度传给客户端。Android 官方 ANR 指南把 `slow binder call`（耗时 Binder 调用）和 `many consecutive binder calls`（连续多次 Binder 调用）列为输入分发 ANR 的常见原因。

在经典 kernel Binder 路径中，Android 17 的 `IPCThreadState::talkWithDriver()` 会通过 `BINDER_WRITE_READ` ioctl 与 Binder driver 交换命令。`ioctl` 是用户空间向设备驱动发控制请求的系统调用。Java Manager、ContentProvider 或第三方 SDK 的一行调用，可能跨到 system_server（承载核心 Java 系统服务的进程）、另一个 app、SurfaceFlinger 或 vendor service。

#### Perfetto 确认顺序

1. 在 app 主线程定位宽的 `binder transaction` 或等待区间。
2. 沿 Binder flow 到 reply/server 线程；缺少 flow 时用时间、pid/tid（进程 ID/线程 ID）与 transaction 上下文辅助。
3. 检查客户端等待期间的线程状态。Sleeping 可能是在等待 reply；Runnable 表示已经可运行但还在等 CPU；D 状态表示不可中断睡眠，通常需要继续检查 I/O。
4. 检查服务端 Binder 线程是否 Running、Runnable、锁等待、磁盘 I/O，或继续发起下游 Binder。
5. 检查 Binder 线程池是否耗尽，以及同一主线程是否连续发出大量小调用。
6. 对照 ANR trace、Perfetto 时间窗和源码服务入口。

`ioctl(BINDER_WRITE_READ)` 只有在 trace 采集了相关 syscall/ftrace 信息时才会直接显示。Binder transaction slice 与 flow 通常更适合作为入口。

#### 修复要按所有权选择

- 调用对首帧或输入不必要：延后、批量或移出主线程；
- 调用必须同步且团队拥有服务端：缩短服务逻辑、减少锁和 I/O；
- 多次查询结果允许短期复用：在明确一致性和失效策略后缓存；
- API 要求主线程：减少调用次数和输入规模，不要强行跨线程；
- 厂商/system_server 高负载：保留系统侧证据，避免把责任写成 app 单函数耗时；
- 第三方 SDK：限制初始化时机、审计 Provider/Manager 调用，并用版本对照验证。

缓存系统查询可能引入权限、包状态或配置过期，异步化也可能改变时序。性能修改要同时通过正确性测试。

### Android 17 cached-app freezer

Cached apps freezer（缓存进程冻结机制）从 Android 11 开始受到平台支持。cached 进程已经离开前台，但系统仍把它保留在内存中，以便后续快速恢复。Android 14 及以上的官方行为说明包括：受支持设备上的 cached 进程通常在进入 cached 状态一段时间后被冻结；生命周期事件会让进程解冻；context-registered broadcast（代码动态注册的广播）可排队到解冻后交付。

Android 17 的资源 `config_defaultFreezerDebounceTimeout` 默认是 10,000 ms；DeviceConfig namespace `activity_manager_native_boot` 下的 key `freeze_debounce_timeout` 可以调整它，厂商资源也会影响行为。DeviceConfig 是平台运行时配置系统；不要把“10 秒”当作所有 Android 17 设备不可变的常量。

进程冻结后，所有线程停止执行，不能做 GC，也不能处理 trim 回调（系统要求进程主动收缩内存的通知）。Android 14 及以上可能在进入 cached 状态后请求预冻结 GC；冻结后还可能执行 compaction（回收或换出进程内存页），包括把匿名页交换到 ZRAM（内存中的压缩交换设备）。系统恢复 Activity 等生命周期时会先解除冻结，后续线程调度、page fault（缺页处理）、GC、消息与业务工作才会继续。

#### 冻结进程收到 Binder 的边界

官方 freezer 文档明确说明：客户端向被冻结的 app 进程发出同步 Binder transaction 时，系统会立即终止被冻结的服务端进程，避免客户端无限等待。异步 `oneway` transaction（不等待返回的单向调用）的 buffer 也受到监控，空间耗尽可导致被冻结进程被终止。

因此，不能把“向 frozen 进程发同步 Binder”描述成“系统解冻后处理积压请求”。正常生命周期提升可以触发解冻；错误 IPC 可能走 kill 路径。退出原因可结合 `ApplicationExitInfo.REASON_FREEZER` 和系统日志调查。

#### 怎样判断解冻是否参与短时卡顿

Android 17 的 `CachedAppOptimizer.traceAppFreeze()` 在 `system_server` 的 `Freezer` track 记录 `Freeze` / `Unfreeze` instant（瞬时事件），附带进程名、pid 和 reason。分析切回慢或恢复后首个交互时，按同一时间窗查看：

- `Freezer` track 的 Unfreeze；
- app 主线程从停止到 Runnable/Running 的变化；
- page fault、I/O、GC、compaction 与 CPU frequency；
- Binder flow 与 system_server 工作；
- FrameTimeline、首帧与输入事件；
- 进程是否被 kill 后冷启动。

Unfreeze 与慢帧相邻只说明时间相关。只有在调度、page fault、GC、Binder 或业务工作上找到耗时，才能进一步归因。短时 CPU 竞争也要通过 Runnable 时间和同核竞争线程验证。

Framework 结论以 `android-17.0.0_r1` 的 `CachedAppOptimizer.java` 为固定版本依据。cgroup freezer（通过 control group 暂停进程的内核机制）、Binder driver 与调度器结论固定到 `android17-6.18-2026-06_r6`；厂商内核与 AOSP common tag 不一致时，以设备 kernel build（内核构建版本）和对应源码复核。

### 从数据看排查优先级

#### 用户面：响应性应有稳定入口

62.3% 的核查后用户评论归到 Responsiveness。团队至少需要覆盖 ANR、启动、帧、输入和明显交互延迟，并将用户动作、版本、机型和时间窗关联到 trace 或线上诊断数据。

#### 工程面：内存要覆盖泄漏、峰值和系统回收

Stack Overflow、GitHub issue 与 commit 的主导类别都是 Memory Consumption。只查 Java 泄漏不够，还要区分：

- Java/Kotlin heap retained object（超期保留对象）；
- native heap、graphics、mmap 与共享内存；
- 峰值分配与 OOM；
- PSS/RSS 增长；
- GC 频率与 CPU 影响；
- LMKD（Low Memory Killer Daemon，低内存终止守护进程）kill、后台存活与 cached-app 行为。

#### 研究面：能耗工具多，现实因素仍有空白

69/85 篇论文涉及能耗，但 v3 仍报告大面积因素、工具与数据集空白。能耗研究投入高，不代表任何产品都应把能耗排在响应性之前。业务场景、用户影响、发生频率、严重度、可恢复性和证据置信度共同决定顺序。

#### 更合适的使用方式

把论文用于“覆盖审计”：

1. 用自家线上数据形成问题排序；
2. 将问题映射到七类后果；
3. 检查是否持续忽略用户可感知类别；
4. 对工具未覆盖因素安排 Code Review、实验和专项 trace；
5. 修复后用原指标与同场景基线验证。

论文比例不能直接变成团队人力比例或发布门禁阈值。

### Code Review 性能检查清单

清单按“静态线索 → 运行证据”使用。命中线索时记录场景和验证方法，不要仅凭模式要求改代码。

| 审查问题 | 静态线索 | 运行时确认 |
|---|---|---|
| 主线程是否做阻塞工作 | 文件、网络、数据库、锁、同步等待 | StrictMode、ANR trace、Perfetto thread state/I/O |
| 是否连续同步 Binder | Manager/Provider 调用位于循环或启动关键路径 | Binder flow、服务端线程、调用次数与累计时间 |
| 异步工作的 owner 是否明确 | `GlobalScope`、裸 Thread、无取消 callback | 页面销毁后任务与引用、重复回调、线程队列 |
| 是否保留短生命周期对象 | singleton/static/cache/listener 捕获页面 | heap dominator、GC root、retained count |
| 高频路径是否重复分配 | draw/layout/bind/loop 内建大对象 | allocation trace、GC、CPU 与帧对照 |
| 大数据是否一次性进入内存 | `readBytes`、完整 JSON、原尺寸 bitmap、大数组 | 峰值 heap/RSS、I/O、解码和 OOM 设备 |
| UI 变化是否触发过量工作 | 高频 `requestLayout`、全量刷新、昂贵 draw | measure/layout/draw、FrameTimeline、Macrobenchmark |
| 数据库路径是否随数据量恶化 | 无界查询、N+1（主查询后逐行追加查询）、缺索引、大事务 | query plan（查询执行计划）、真实规模 benchmark、磁盘与锁 |
| 偏好设置是否阻塞生命周期 | 主线程读写、密集 `apply()`、同步 `commit()` | StrictMode、lifecycle pause、磁盘 trace |
| 后台资源是否按生命周期释放 | WakeLock、sensor、location、socket、Job | batterystats、后台 trace、超时与退出路径 |
| 重试和同步是否放大网络/CPU | 无上限重试、短周期轮询、重复下载 | 请求日志、TrafficStats、CPU/energy 时间窗 |
| freezer 是否改变恢复路径 | cached 多进程 IPC、恢复时大量工作 | Freezer track、exit reason、Unfreeze 后线程证据 |

#### SharedPreferences 不能只检查 `apply()` 与 `commit()`

`commit()` 同步写盘，不应在主线程执行。`apply()` 立即更新进程内数据并异步写盘，但 Framework 会在组件生命周期切换时等待未完成写入；密集 `apply()` 仍可能引发主线程阻塞和 ANR。官方当前文档不建议新存储需求继续采用 SharedPreferences。

审查时还要看读取是否触发磁盘、写入频率、durability（崩溃或重启后数据是否仍可靠保存）、一致性、多进程需求和迁移方案。将 `commit()` 机械替换成 `apply()` 只能消除调用点的同步写盘，不能解决所有生命周期 I/O。

### 实践步骤

这套方法可以落实为三项动作：

- 引用研究数字时同时写分子、分母、revision 和样本来源；
- 把性能后果、促成因素、代码模式与观测证据分层；
- 将静态审查结果送入可复现的 benchmark、trace 或线上指标验证。

遇到一条用户“卡”的反馈，可以从 Responsiveness 进入，再判断它对应帧延迟、输入等待、启动、Binder、I/O、锁、调度还是 freezer 恢复。遇到内存修复提交，可以区分 retained reference（超期保留引用）、高频分配与回收、峰值数据、native/graphics 占用和系统回收。遇到研究工具没有规则覆盖的因素，则补充场景化测试与运行时观测。

研究样本跨多个 Android 版本。Android 17 相关机制以 `android-17.0.0_r1` 为固定平台版本；涉及 Binder driver、cgroup freezer 和调度器时，以 `android17-6.18-2026-06_r6` 为固定内核版本。旧版本演进可以保留，不把当前结论外推到 Android 17 之后。

## 基线、归因、门禁与长期治理

单次优化结束后，指标口径、责任人、回归阈值和证据保留决定问题会不会再次出现。

### 从个人能力转为团队机制

会读 Perfetto（系统 trace 采集与分析工具）、会分析 heap dump（堆内对象及引用关系的快照）、熟悉 ART（Android Runtime）或 SurfaceFlinger（系统显示合成服务）的工程师仍然很重要。团队风险来自这些能力只存在于少数人手中：版本回归依靠临时救火，分析方法无法复用，修复完成后也没有稳定验收。

工程化治理要固定五类决策：

- 哪些用户旅程属于 Critical User Journey（CUJ，即必须稳定完成的关键用户操作路径）；
- 每条旅程采用什么指标、预算和设备；
- 什么变化需要评审或阻断，怎样灰度（先向少量用户发布）或回滚；
- 异常由谁调查，证据如何交接；
- 修复通过什么线下测试和线上指标验收。

机制的目标是可重复决策。不同工程师面对同一份数据，应得到相近的发布结论；对结论有异议时，也能查到预算、基线、例外和证据。

### 从信号到验收的反馈回路

监控平台持续收到数据，不等于问题正在被治理。一条异常只有完成“发现 → 归因 → 修复 → 验收”，才会改变后续版本。回路中需要同时保留四类对象：

| 对象 | 回答的问题 | 不能单独回答 |
|---|---|---|
| 指标与分布 | 影响范围、趋势和异常分群（按版本、设备或场景切出的样本组） | 单个样本为何变慢 |
| 事件与会话 | 某次操作经历了哪些业务阶段 | 调度、锁和跨进程根因 |
| trace（运行时间线）、profile（采样汇总）、heap dump、ANR trace（ANR 时的线程栈） | 现场执行和资源关系 | 对全部用户的影响 |
| 工单与发布记录 | 谁处理、何时交付、怎样验收 | 运行时技术事实 |

一条可执行的流程包含八个阶段：

1. **采集**：按 §16.3 的指标合同（指标定义、分母、单位、采集范围和平台边界）记录信号。
2. **采样**：把概率已知的基线样本与异常触发的诊断样本分开。
3. **聚合**：展示分母、样本量、缺失率、schema（字段、类型、单位等数据结构定义）和采样配置。
4. **归因**：从异常分群进入正常/异常样本，用 trace、源码和对照实验验证假设。
5. **告警**：同时检查绝对预算、相对回归、最小样本和数据健康。
6. **流转**：为问题指定当前 owner（当前负责推进的人或团队）、状态、时限和下一项动作。
7. **修复**：记录改动机制、风险、开关、回滚条件和守护指标（用于监测副作用的关联指标）。
8. **验收**：在线下同协议复测，并在线上同分群确认用户结果。

若工单缺少指标合同、可回查样本、当前 owner、修复版本或验收条件，流程就停在了中间。告警关闭也不能自动解释为修复成功；采样切换、上报中断或用户构成变化同样会让曲线下降。

### 五项治理要素

#### 1. 预算：先固定测量契约

性能预算不能只写“启动 2 秒以内”。至少包含：

TTID（Time To Initial Display）是首个画面显示时间，TTFD（Time To Full Display）是应用报告内容完整可用的时间。warm start 指应用进程仍在、Activity 可能需要重新创建的启动；frame overrun 表示一帧超过显示截止时间的幅度；RSS 是进程当前驻留在内存中的页面总量。

Baseline Profile 是随应用或库发布的类与方法规则，用来指导 ART 对关键代码做 Ahead-of-Time（AOT，提前）编译。

| 字段 | 示例含义 |
|---|---|
| CUJ | 冷启动到首页 TTID、warm start 到 TTFD、Feed 连续滑动 |
| 指标 | `timeToInitialDisplayMs`、frame overrun、峰值 RSS、包体积 |
| 人群/设备 | 低内存设备、主力 SoC（System on Chip，系统级芯片）、API 26、API 37 |
| 构建与编译状态 | benchmark/release 变体、R8（代码压缩与优化器）状态、Baseline Profile 模式 |
| 统计口径 | median（中位数）、P90（第 90 百分位）、失败率、样本数、窗口 |
| 预算 | 绝对上限、相对回归上限或两者组合 |
| 动作 | 提醒、阻断合入、停止灰度、回滚 |
| owner | 指标 owner、CUJ owner、批准例外的角色 |

预算可以分为三层：

- **用户体验 SLO**：SLO（Service Level Objective，服务水平目标）约束线上启动、帧、ANR（应用无响应）、crash（崩溃）、OOM（内存不足）、耗电等用户结果；
- **实验室回归预算**：固定设备与场景下的 Macrobenchmark（从进程外测量完整用户交互）、内存和 CPU 结果；
- **资源预算**：下载大小、安装大小、DEX（APK 中的 Android 字节码）/资源增长、启动初始化和后台资源。

三层不能互相代替。线下启动稳定不代表全部厂商设备稳定；线上曲线稳定也可能由灰度量小或采样延迟造成。发布决策要说明使用了哪一层证据。

#### 2. 基线：记录比较条件

预算描述目标，基线描述某组条件下已经测得的水平。更新基线时至少保留：

- git commit、version code、依赖锁文件与构建变体；
- benchmark/library/AGP（Android Gradle Plugin）/JDK（Java Development Kit）版本；
- 设备型号、serial（设备序列号）或实验室资产 ID、Android build fingerprint（系统构建指纹）；
- 电量、温度、刷新率、网络与测试数据；
- compilation mode（预编译条件）、startup mode（冷/温/热启动条件）、迭代数；
- JSON 结果、每轮 trace 和失败日志。

基线必须与候选版本使用同一设备和同一配置。把 Pixel 的结果与另一品牌设备比较，把 `CompilationMode.None`（不预先编译目标代码）与 `Partial`（按 profile 做部分预编译）比较，或把 debug 与 benchmark 变体比较，所得差值都包含测试条件变化。

基线也不是目标。某个历史版本已经超出 SLO 时，不能因为它“当前如此”就继续接受同等表现。预算变更与基线更新应由不同操作完成，并留下评审记录。

#### 3. 回归门禁：按证据确定强度

门禁可以分三类：

| 类型 | 适合内容 | 失败动作 |
|---|---|---|
| 确定性门禁 | CUJ 脚本可运行、APK（安装包）/AAB（Google Play 分发包）含 profile、包体积、禁用 API、缺少 R8 mapping（混淆映射）/native symbol（原生调试符号） | 直接阻断 |
| 测量门禁 | 启动、帧、内存、CPU benchmark | 达到样本与噪声规则后阻断；其余标记需复测 |
| 线上门禁 | 灰度 ANR/crash、启动 tail（高百分位的慢样本）、慢帧、OOM、退出原因 | 暂停扩量、关闭开关或回滚 |

Benchmark 是带噪测量，这里的噪声指同一条件下重复运行仍会出现的随机波动。Android 官方 CI（Continuous Integration，持续集成）文档明确提醒，它不像普通测试那样天然只有 pass/fail。可靠门禁要先测量设备自身的历史噪声，再规定：

- 候选与基线的最小重复次数；
- 可以比较的设备池；
- 允许的绝对差和相对差；
- 测量失败、thermal throttle（温控降频）、低电量和设备离线如何处理；
- 何时自动复测，复测几次后转人工判断；
- 哪些 trace 和 JSON 必须归档。

PR（Pull Request，合入请求）可以运行 dry run（只验证脚本、安装和导航，不用单次结果判断性能）。性能数值适合在稳定真机池的 nightly（夜间定时任务）、合入队列或发布流水线评估。官方强烈不建议用模拟器结果代表用户性能；模拟器可用于 CUJ 脚本冒烟和 Baseline Profile 规则生成。

不要在 CI 中全局压制 Macrobenchmark 的配置错误。target app 为 `debuggable`、Android 10/11 上未设为 `profileable`、设备为 emulator（模拟器）或低电量时，库会报告可能损害测量的错误。

`debuggable` 允许调试，会显著改变运行性能；`profileable` 允许性能工具读取详细 trace 而无须启用调试。单项抑制需要记录原因和到期时间。

#### 4. 灰度观测：验证设备分布

灰度需要覆盖：

- TTID、TTFD 和关键页面 tail；
- frame overrun、慢帧/冻帧与交互失败；
- user-perceived ANR（用户可感知的 ANR）、crash、OOM 与 `ApplicationExitInfo`（系统记录的进程退出信息）；
- 内存、后台 CPU、WakeLock（阻止设备进入部分休眠状态的系统锁）与网络异常；
- 设备型号、SoC/GPU、SDK、渠道、地域和实验分群。

灰度组与对照组要处于相同时间窗，并控制版本、设备和远程配置。服务端延迟、活动流量、网络变化和实验开关都可能改变客户端结果。只看全局平均值会隐藏少数高流量机型或低内存设备。

Google Play 的 Android vitals（Play Console 汇总的应用质量指标）提供发布质量信号，自建指标提供更细场景与更快回查。两者分母、延迟和覆盖范围不同，门禁页面要标明数据源。Play 的 bad behavior threshold（不良行为阈值）可以作为外部边界，内部预算通常要更早发现趋势。

灰度规则应预先写明扩量、暂停和回滚条件。临时调整条件要进入发布记录，避免数据出现后再选择更宽松的口径。

#### 5. 发布验收：把结论写回版本

发布验收记录至少包含：

- CUJ 线下结果与预算结论；
- profile、R8 mapping、native symbols 等构建产物检查；
- 灰度指标、样本量、观察窗口和重点设备；
- 未解决问题、已批准例外和到期日；
- 发布/暂停/回滚决定及批准人；
- 上线后复查时间和 owner。

验收结果关联 commit、build、benchmark JSON、trace、dashboard（监控看板）和工单。后续发现回归时，可以区分“当时没有信号”“规则没有触发”“例外放行”和“发布后环境变化”。

### Benchmark 与 Profile 在治理中的位置

Macrobenchmark 的工程配置、迭代、编译模式和统计处理由 §15.6 与 §16.5 统一说明。本节只保留治理要求：CI 必须把目标 APK、测试 APK、设备与环境 manifest（机器可读的环境配置清单）、原始 JSON、每轮 trace、失败日志和统计程序版本绑定到同一次运行。

门禁程序先验证条件一致与数据质量，再比较绝对预算、相对回归和历史噪声。临界结果在同一设备复测，阻断结果附正常与异常 trace。

Baseline Profile 与 Startup Profile 也分成三项验收：规则是否覆盖稳定 CUJ、产物是否正确打包、真机上的目标场景是否获得收益。Startup Profile 是 Baseline Profile 的子集，构建系统用它调整 APK 内 DEX 的类与方法布局。

profile 文件存在不能证明目标代码已完成预期编译，更不能证明用户指标改善。生成规则、检查产物和测量收益是三个独立动作；具体工具操作继续由 §15.6 与启动专题维护。

设备系统更新、电池老化、存储状态变化、Benchmark 升级或测试脚本变更后，应重新评估噪声并建立有迁移记录的新基线，不能静默沿用旧结果。

### 代码评审中的性能检查

以下变化应触发性能影响说明：

- `Application`、ContentProvider、App Startup initializer（AndroidX App Startup 的初始化组件）或首个 Activity 的初始化；
- 主线程文件/数据库/网络、同步 Binder、锁和反射；
- 图片、序列化、数据库 schema、缓存和大数据路径；
- View measure/layout/draw、Compose state/recomposition（状态变化后重新执行受影响的 Composable）与列表绑定；
- 新 SDK、动态特性（按需交付的功能模块）、native 库、资源或包体积增长；
- 后台 Job、alarm、WakeLock、定位、传感器和轮询；
- Baseline/Startup Profile 的 CUJ 或构建配置变化。

PR 模板可以要求作者填写：

- 受影响 CUJ 与线程；
- 新增工作在调用链中的位置；
- 预期复杂度、数据规模和设备边界；
- 已运行的 benchmark/trace 或无需测量的理由；
- 线上观察指标，以及异常时用于关闭或降级功能的开关。

评审线索用于决定是否测量，不能只凭“看起来可能慢”要求重写。命中高风险路径时补 Macrobenchmark、Microbenchmark（在进程内循环测量可独立调用的小段代码）或系统 trace；影响低且路径不频繁时，记录判断即可。

### 角色与交接

| 角色 | 主要责任 |
|---|---|
| Feature/CUJ owner | 场景脚本、代码修复、业务正确性、线上验收 |
| 性能平台团队 | 指标契约、真机池、benchmark 工具、采样与 dashboard |
| Release/值班角色 | 灰度节奏、门禁执行、暂停与回滚 |
| 系统/ROM（厂商系统镜像）团队 | framework、system_server（承载核心 Java 系统服务的进程）、调度、thermal（温控）、GPU/驱动问题 |
| 数据/服务端团队 | 服务延迟、实验分群、数据完整性与查询成本 |

每个问题只有一个当前 owner。跨团队协作可以有多名参与者，但调查状态、下一动作和时限由当前 owner 维护。转交给系统或厂商团队时，证据包至少包含：

- app build（应用构建版本）、复现步骤与发生率；
- 设备型号、Android build fingerprint、kernel build（内核构建版本）；
- 正常与异常对照；
- Perfetto/bugreport（系统诊断包）/tombstone（native 崩溃现场）等证据；
- 已排除的 app 侧假设；
- 期望对方验证的具体问题。

“trace 里 system_server 很忙”不足以完成转交。需要沿 Binder flow（跨进程调用的因果连线）、线程状态、锁、I/O 或调度证据指出可调查入口。涉及内核的判断固定到 `android17-6.18-2026-06_r6`；厂商设备按设备对应源码复核。

#### 工单状态与验收责任

性能工单可以使用 `detected（已发现） → triaged（已分诊） → investigating（调查中） → fixing（修复中） → validating（验收中） → resolved（已解决）`。

`false-positive（误报）`、`duplicate（重复）`、`cannot-reproduce（无法复现）` 与 `accepted-risk（已接受风险）` 应作为有理由、有操作者和时间戳的终态，不能全部写成“关闭”。

工单至少携带指标合同、异常窗口、基线与回归版本、受影响分群、样本量、采样配置、正常/异常证据、已确认事实、候选假设、当前 owner、计划版本和回滚条件。进入 `validating` 前，必须先写线上验收窗口、最小样本和成功条件，避免结果出现后再挑选口径。

### 证据连接与数据生命周期

聚合图、单次事件、诊断制品和发布记录需要稳定连接，但连接键不能进入高基数指标标签。高基数表示标签可能产生大量近乎唯一的取值，会放大时序数据库的存储和查询成本：

| 键 | 用途 |
|---|---|
| `event_id` | 让客户端重试产生的同一事件只入库一次 |
| `session_id` / `page_instance_id` | 关联一次会话或页面实例 |
| `process_instance_id` | 区分进程生命周期，避免只依赖会复用的 PID（进程 ID） |
| `trace_id` / artifact ID | 从异常事件进入受控保存的 trace、heap dump 或 tombstone 等诊断制品 |
| `build_id` / `version_code` | 对齐二进制、mapping、symbols 和发布记录 |
| `event_schema_version` / `sampling_config_version` | 解释字段、算法与采样策略变化 |

进程内阶段耗时使用明确的 monotonic clock（只单调递增，不受系统校时影响），跨设备和发布窗口使用 UTC wall time（可对应日历时间的 UTC 时间戳）；两类时间戳不能直接相减。schema 改变单位、分母或含义时升版本，数据上报端、查询端、看板和告警在同一变更记录中写明兼容窗口。

存储按用途分层：近期聚合和可检索事件服务告警，降采样（降低时间粒度或样本密度）后的趋势用于长期比较，trace、heap、tombstone 等高敏附件单独加密、缩短保留期并记录访问审计。每个数据源都要有 owner、日量、保留期、删除机制和停采条件。

多业务线共享平台时，`tenant_id`（租户，即一个独立业务或组织）必须来自受信任的服务端身份或发布配置。查询、缓存、附件、导出、告警和审计全程执行 tenant + role（租户与权限角色）校验；在 ID 前加租户前缀只能避免碰撞，不能构成访问隔离。

### 例外机制

业务可以在明确条件下接受性能回归。例外记录必须包含：

- 指标、设备/CUJ、回归量和用户影响；
- 放行原因、补偿措施与风险；
- owner、批准人和到期日期；
- 计划修复版本或重新评估条件；
- 灰度观察与回滚规则。

例外到期后自动恢复原门禁。若团队决定永久调整预算，应提交预算变更评审，展示用户影响、历史趋势和替代指标。不能通过更新基线隐藏回归，也不能无限延长同一例外。

### 日常、版本和事故

#### 日常

- PR dry run 验证 CUJ，风险变更补充性能影响说明；
- nightly 在固定真机跑关键 Macrobenchmark；
- 趋势任务检查设备噪声、结果缺失和 profile 产物；
- 线上 dashboard 按版本和设备分群审计。

#### 发布前与灰度

- 固定 benchmark、metric schema 和 sampling config 版本；
- 生成并检查 Baseline/Startup Profile；
- 运行 release candidate（待发布候选版本）的完整 CUJ 集；
- 检查未关闭工单、例外和回滚开关；
- 灰度阶段按预设规则扩量或暂停。

#### 事故

- 保留异常窗口、配置和证据；
- 通过暂停扩量、开关、降级或回滚限制影响；
- 比较正常/异常分群并验证归因；
- 修复后同时复测线下 CUJ 与线上指标；
- 只把稳定、可重复的检测方法加入日常门禁。

事故复盘的产物可能是新 CUJ、指标、告警、lint（静态检查规则）、profile journey（生成 profile 的自动化 CUJ）或操作手册。若问题依赖偶发外部条件，强行加入不稳定硬门禁会制造噪声；此时更适合线上预警或人工专项。

### 从小规模开始

一个可运行的最小版本包括：

1. 选择启动、首页和一个高频交互作为 CUJ。
2. 为每条 CUJ 写指标契约、预算和固定真机。
3. PR 跑脚本 dry run，nightly 跑完整 Macrobenchmark。
4. 生成 Baseline/Startup Profile 并检查发布产物。
5. 灰度观察启动、帧、ANR、crash、OOM 和退出原因。
6. 所有回归进入带 owner、验收和到期时间的工单。

稳定运行后再增加设备、场景和硬门禁。门禁数量不是成熟度指标；可靠覆盖高价值 CUJ、能够解释失败并持续验收，才说明机制有效。

### 与其他章节的关系

- §7、§8、§9 解释流畅性、启动和 ANR 的平台机制。
- §15.6 说明 Macrobenchmark 的用法与回归门禁边界。
- §16.3 定义性能指标契约、SLO、线上监控和保护开关。
- §16.5 讨论测试设计与统计可靠性。
- 本节把这些能力连接到采集、归因、工单、发布和验收流程，不再重复各工具的 API 教程。

平台源码依据固定为 Android 17 / API 37 / `android-17.0.0_r1`。Benchmark、Baseline Profile 与 ProfileInstaller（在设备上安装 Baseline Profile 的 AndroidX 库）属于 AndroidX/构建工具，版本应在项目依赖和基线记录中单独固定。

涉及 CPU 调度、Binder driver（Binder 内核驱动）、cgroup（control group，内核资源分组）或 thermal 的内核证据，使用 `android17-6.18-2026-06_r6`。

## 常见误区

### 没有基线就开始改代码

缺少修改前的数据，会让收益无法复查，也无法判断副作用。遇到无法稳定复现的线上问题，可以先保留版本、设备和场景分布，再设计诊断版本。

### 只看均值

均值会掩盖长尾和多峰分布。启动和响应时间至少同时观察中位数与高分位；帧数据还要区分慢帧、冻结帧、刷新率和场景状态。

### 把固定帧预算套到所有设备

16.67 ms 只对应 60 Hz 的一个周期。90 Hz、120 Hz、可变刷新率和 SurfaceFlinger 调度会改变 deadline。Android 17 的 FrameTimeline 已提供更直接的 deadline 和 jank 证据。

### 把工具标签当成根因

“GC”“Binder”“I/O”“GPU”只是观察到的活动。根因需要和业务调用、线程状态、持续时间、deadline 及对照实验关联。自动 metric 或 AI 辅助 SQL 可以提高检索效率，结论仍需回到原始事件和源码。

### 只改善局部指标

减少主线程耗时可能增加后台 CPU；缓存可能降低 I/O，也可能提高内存压力；更激进的并行可能缩短单次延迟，却恶化发热后的持续性能。复测应覆盖相邻指标和长时运行。

### 迷信“过早优化”这句口号

设计阶段可以选择同样清晰、成本更低的实现；复杂优化则需要基线和热点证据。Jeff Dean 与 Sanjay Ghemawat 的 Performance Hints 也建议：当可读性和复杂度没有明显代价时，选择更快的方案，同时用性能剖析和基准测试验证。

## 参考资料

### 性能方法、工具与平台证据

- [Android Developers：App performance](https://developer.android.com/topic/performance)
- [Android Developers：Benchmark your app](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [Android Developers：AndroidX Benchmark releases](https://developer.android.com/jetpack/androidx/releases/benchmark)
- [Android Developers：Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Android Developers：Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Android Developers：Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Android Developers：`ProfileVerifier.CompilationStatus`](https://developer.android.com/reference/androidx/profileinstaller/ProfileVerifier.CompilationStatus)
- [Android Developers：`Build.VERSION.SDK_INT_FULL`](https://developer.android.com/reference/android/os/Build.VERSION)
- [Android Developers：Overview of system tracing](https://developer.android.com/topic/performance/tracing)
- [Android Developers：JankStats](https://developer.android.com/topic/performance/jankstats)
- [Android Developers：Android vitals](https://developer.android.com/topic/performance/vitals)
- [Android API 37：ProfilingManager API diff](https://developer.android.com/sdk/api_diff/37/changes/android.os.ProfilingManager)
- [Android API 37：ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [AOSP android-17.0.0_r1：ProfilingManager.java](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [AOSP android-17.0.0_r1：ProfilingTrigger.java](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP android-17.0.0_r1：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP android-17.0.0_r1：BLASTBufferQueue.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [AOSP android-17.0.0_r1：profman.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/profman/profman.cc)
- [AOSP android-17.0.0_r1：Simpleperf README](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/README.md)
- [Perfetto：Trace Analysis Overview](https://perfetto.dev/docs/quickstart/trace-analysis)
- [Perfetto：Android Jank detection with FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [Perfetto：Callstack-based Allocation Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Jeff Dean、Sanjay Ghemawat：Performance Hints](https://abseil.io/fast/hints.html)
- Brendan Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd Edition, Addison-Wesley, 2020

### 实证研究与运行时模式

- [Liao et al., *A Comparative Study of Android Performance Issues in Real-world Applications and Literature*, arXiv:2407.05090v3](https://arxiv.org/pdf/2407.05090v3)
- [论文复现资料：Android-Performance-Analysis](https://github.com/Dianshu-Liao/Android-Performance-Analysis)
- [Android 官方：Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android 官方：Performance measurement examples](https://developer.android.com/topic/performance/performance-measurement-examples)
- [Android 官方：Memory management overview](https://developer.android.com/topic/performance/memory-overview)
- [Android 官方：SharedPreferences](https://developer.android.com/reference/android/content/SharedPreferences)
- [AOSP cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [Android 17 `View.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [Android 17 `ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [Android 17 `IPCThreadState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/IPCThreadState.cpp)
- [Android 17 `CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)

### 治理、基准与发布

- [Android 官方：Benchmark in CI](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Android 官方：Create Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [Android 官方：Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1)
