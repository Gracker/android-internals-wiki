---
title: 性能优化的术、道、器
chapter: '15.1'
section: '15.1'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-07-30'
last_verified_against: AOSP android-17.0.0_r1；Android SDK API 37；AndroidX Benchmark 1.4.1
confidence: high
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
  path: developer.android.com/topic/performance/baselineprofiles/overview
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
- '15.9'
consolidated_from:
- '15.12 Android 性能优化研究方法论'
pipeline_stage: "ready-to-publish"
task9_state: "reviewed"
task2b_state: fixed
task6_state: "reviewed"
---

# 性能优化的术、道、器

## 道、术、器的分工

性能工程面对的对象，是一个在特定设备、系统版本、构建产物和运行环境中执行的完整系统。一次卡顿可能同时包含主线程排队、Binder 等待、RenderThread 提交、GPU 执行和 SurfaceFlinger 合成；一次启动回退也可能来自编译状态、磁盘缓存、进程状态或业务初始化。只盯住某个函数耗时，很容易把症状当成原因。

「道、术、器」分别承担三类工作：

- 「道」决定要改善哪个用户场景，以及用什么数据判断改善是否成立。
- 「术」规定从现象到证据、从假设到验证的分析顺序。
- 「器」负责采集、查询和呈现证据，每种工具都有可见范围与扰动成本。

平台结论以 Android 17 / API 37 / `android-17.0.0_r1` 为上限。Android 7、10、11 等历史节点用于说明 API 和观测口径的演进。这里不分析内核实现，因此不引用 `android17-6.18-2026-06_r6` 的具体行为。

## 「道」：从用户场景定义性能

### 从关键用户旅程开始

「应用很慢」无法直接转成实验。工程师需要把反馈改写成可复现的关键用户旅程（Critical User Journey，CUJ），并记录清楚起点、终点和成功条件。

| 用户反馈 | 可复现的 CUJ | 适合观察的结果 |
|---|---|---|
| 打开首页慢 | 进程不存在时点击图标，直到首页达到可交互状态 | TTID、TTFD、冷启动分位数、首帧前主线程任务 |
| 列表不流畅 | 固定数据集、固定手势滚动同一列表 | 超时帧分布、FrameTimeline、主线程与 RenderThread 活动 |
| 点击后没反应 | 从输入事件到目标界面或业务确认信号 | 输入延迟、主线程 runnable/blocked、Binder 与 I/O 等待 |
| 使用一段时间后内存上涨 | 重复进入并退出同一业务流程 | Java/native heap、RSS/PSS、对象保留路径、分配调用栈 |
| 后台耗电 | 固定时长进入后台并保持相同网络条件 | wakelock、alarm、job、网络活动、thermal 与电量归因 |

TTID（Time to Initial Display）关注首帧出现，TTFD（Time to Full Display）还包含应用调用 `reportFullyDrawn()` 前的工作。后者是否可信，取决于应用是否把 fully drawn 信号放在业务可交互的稳定位置。

同一个指标不能替代用户旅程。冷启动 P50 改善，并不能证明温启动、低端机或首次安装后的体验也改善；平均帧耗时降低，也不能覆盖少量冻结帧。性能结论至少要写成下面这组条件：

> CUJ × App 版本 × 构建类型 × 设备档位 × Android 版本 × 编译状态 × 环境条件 × 统计量

缺少其中一项，后续复测就可能换了实验对象。

### 用户感知与系统指标要能互相定位

用户感知提供优先级，系统指标提供归因线索。两者之间需要一层稳定映射：

- 启动体验可映射到 TTID、TTFD、冷/温/热启动类型，以及首帧前各阶段耗时。
- 流畅度可映射到错过 deadline 的帧、冻结帧、实际刷新率和当时的 UI 状态。
- 响应性可映射到输入事件、消息队列、线程调度、锁等待、Binder 和 I/O。
- 稳定性可映射到用户感知 ANR、崩溃、OOM、LMK 与对应场景。
- 功耗可映射到任务执行时间、唤醒来源、网络无线电活动、thermal 状态和电量统计。

指标只负责描述现象。即使 Trace 显示某帧主线程发生 GC，也需要继续判断分配来自哪里、GC 是否跨过该帧 deadline、同一问题能否在相同条件下复现。

### 实验室数据与线上数据各有职责

实验室测量适合控制变量、复现问题和验证改动。线上数据适合判断影响范围、设备分布和长尾趋势。二者无法互相替代：

- Macrobenchmark 能稳定重复启动或滚动 CUJ，但测试设备不能代表全部用户。
- Android vitals 能给出真实设备上的崩溃、ANR、慢渲染和电量信号，但聚合数据通常不足以直接定位代码。
- JankStats 能把帧耗时与应用提供的 UI 状态一起交给回调，但应用仍要设计采样、聚合、上传、隐私和版本维度。
- Perfetto 能保存一次复现过程的时间线证据，但未启用的数据源不会事后出现在 Trace 中。

推荐的工作顺序是：用线上数据选择场景和设备层级，用实验室环境复现并定位，再用基准测试和线上分群观察验证改动。

### 性能维护要进入日常变更流程

性能会随业务代码、依赖、编译器、系统版本和设备环境变化。一次专项优化只能改变当时的基线。可持续的维护机制包含四类记录：

1. 关键 CUJ 的负责人、测试脚本与版本化指标定义。
2. 固定设备或可比较设备池上的基准数据。
3. 超出预算后的复核规则，包含允许的噪声范围和人工豁免。
4. 线上分群指标与发布版本、设备型号、Android 版本之间的关联。

预算不应只写一个数字。例如“冷启动低于 1.5 秒”缺少启动类型、设备、编译模式和分位数；“帧耗时低于 16.67 ms”也忽略了动态刷新率和平台计算的 frame deadline。可执行的预算会同时写明测量协议。

## 「术」：从现象到可复查结论

### 六步分析流程

#### 1. 定义现象

记录 CUJ、出现频率、受影响版本、设备和网络条件。若来自线上告警，还要记录指标口径、时间窗口和样本量。此时不要提前指定根因。

#### 2. 建立基线

在修改代码前运行同一套测试。保留原始结果、构建产物标识、设备温度、刷新率、编译模式和系统版本。P50 反映典型情况，P90/P95/P99 用于观察长尾；小样本应同时保留每次测量值。

#### 3. 采集能区分假设的证据

采集配置应由假设决定。启动问题需要进程启动、主线程、Binder、I/O 和 ART 相关事件；掉帧需要 FrameTimeline、Choreographer、RenderThread、SurfaceFlinger、调度与频率信息；Native CPU 热点需要采样栈和符号。把所有数据源都打开，会增大 Trace、提高扰动并降低分析效率。

#### 4. 提出可证伪的假设

“某 SDK 很慢”过于宽泛。更可用的写法是：“冷启动首帧前，主线程同步调用该 SDK 的初始化函数，并占据一段连续执行时间；延后该调用后，TTID 分布应下降，且 TTFD 和功能可用性不回退。”假设中要包含证据、改动和预期结果。

#### 5. 一次只改变一个主要变量

同时修改线程模型、缓存、布局和编译配置，即使指标改善，也很难判断贡献来自哪里。高风险改动可分阶段提交，每一阶段保留独立测量结果。

#### 6. 复测并检查副作用

使用相同协议复测，比较分布与置信区间，并检查内存、功耗、稳定性和业务正确性。把主线程工作移动到后台线程可能改善帧耗时，也可能增加 CPU 竞争、启动后的尾部延迟或耗电。

### 用证据等级约束结论

性能调查很容易从“两个事件同时出现”跳到“其中一个导致另一个”。报告应把结论分成四级，并明确当前停在哪一级：

| 证据等级 | 需要回答的问题 | 可以写出的结论 |
|---|---|---|
| 观测 | 目标窗口里发生了什么 | 两个事件在时间上重叠，或某项指标发生变化 |
| 机制 | 调用、等待或资源关系怎样连接两者 | 存在一条能解释影响方向的路径 |
| 干预 | 改变该机制后，预期中间量是否随之变化 | 当前改动与改善一致 |
| 复现 | 不同轮次、设备或灰度对照是否保持同方向 | 结论适用于已经覆盖的总体 |

每个候选原因还应写成“假设—预期观测—反证—状态”。例如，若假设主线程 CPU bound，预期 wall time 接近 on-CPU time，且采样栈集中在稳定调用链；如果大部分时间实际是 Runnable、Binder 等待或锁等待，这条假设就应降级或被排除。保留被证伪的假设，可以避免下一位排查者重复同一条无效路径。

### 测量协议比“多跑几次”更有价值

常见偏差及控制方法如下：

| 偏差来源 | 会改变什么 | 控制方法 |
|---|---|---|
| Debug 与 Release 构建差异 | 优化、插桩、断言、资源与代码布局 | 使用接近发布配置的可测构建，并记录签名和混淆状态 |
| JIT/AOT/Baseline Profile 状态 | 启动和热点代码执行时间 | Macrobenchmark 中固定 `CompilationMode`，不要混合比较不同编译状态 |
| 设备温度与 DVFS | CPU/GPU 频率和持续性能 | 记录 thermal 状态，随机化实验顺序，必要时等待设备回到同一温度区间 |
| 刷新率变化 | 帧 deadline 与 jank 判定 | 记录实际刷新率，优先使用 FrameTimeline deadline，不套用固定 16.67 ms |
| 缓存与进程状态 | 冷/温/热启动、磁盘和网络耗时 | 明确清理范围；不要把清进程、清数据、清页缓存混为同一种“冷启动” |
| 采样或插桩 | CPU 时间、调度和 Trace 体积 | 使用能回答问题的最低采样率和最小数据源集合，并做有/无采集对照 |
| 自动化脚本不稳定 | 手势路径、页面状态和等待条件 | 用语义条件等待页面，不用固定 sleep 代替业务完成信号 |

AndroidX 官方将 Macrobenchmark 定位为进程外的端到端测量工具，并允许控制启动和编译状态；Microbenchmark 用于进程内代码片段。二者的结果范围不同，不能直接互换。

### Android 17 的平台观测边界

#### FrameMetrics 与 FrameTimeline

`FrameMetrics` 从 API 24 提供窗口帧的阶段耗时。Android 17 的 `FrameMetrics.java` 仍定义 `TOTAL_DURATION`、`DEADLINE`、`GPU_DURATION` 和 `FRAME_TIMELINE_VSYNC_ID` 等指标。`TOTAL_DURATION < DEADLINE` 是源码注释给出的 deadline 判断关系；应用仍要考虑回调开销、丢失的帧信息和 UI 工具栈差异。

Android 12 引入的 FrameTimeline 为应用帧与 SurfaceFlinger 帧提供关联和 jank 信息。分析 Android 17 Trace 时，应沿实际 vsync ID、deadline 和 jank type 追踪，避免只按 60 Hz 预算做推断。

#### Perfetto

Android 官方文档把 Perfetto 定义为 Android 10 起的平台级 tracing 工具。它能合并应用、Framework、Native 服务和内核数据源，但 Trace 只包含采集配置启用且生产者实际写入的事件。没有方法级事件时，系统 Trace 无法自动给出某行 Java/Kotlin 代码的耗时；这类问题需要应用插桩、Android Studio CPU Profiler、Simpleperf 或可符号化采样补充。

Trace Processor 会把采集数据解析成可查询表。SQL 结果能复现筛选和聚合过程，适合放进回归检查；查询仍要注明 Perfetto 版本、输入 Trace 和 metric/schema 版本。

#### ProfilingManager 与 ProfilingTrigger

Android 17 的 Profiling Mainline 模块保留 `requestProfiling()` 与全局结果 listener，并提供基于系统事件的 profiling trigger。API 37 新增的 `addAllProfilingTriggers()` 和 `requestRunningSystemTrace()` 也能在 `ProfilingManager.java` 中找到。

`ProfilingTrigger.java` 在 `android-17.0.0_r1` 中枚举了 fully drawn、ANR、运行中 trace 请求、若干 kill 原因、OOM、异常、过量 CPU、冷启动和兼容性等类型。源码的 `isValidTriggerType()` 对多种类型使用 feature flag，系统还会执行限流、权限和资源判断。应用应把结果回调当作“可能获得的系统制品”，不能把注册成功解释为每次事件都有 Trace 或 heap dump。

#### Baseline Profiles 与 ART

Baseline Profile 属于构建、分发和 ART 编译协作能力，不绑定某一个 Android 大版本。当前官方流程会把人类可读规则编译为 APK/AAB 中的 `assets/dexopt/baseline.prof`；Play 安装、ProfileInstaller 和设备后台 dexopt 的参与方式取决于 Android 版本与安装渠道。

Android 17 的 `art/profman/profman.cc` 仍负责读取、合并和分析 profile，编译决策还会进入 ART 的 dexopt/dex2oat 路径。`ProfileVerifier` 的安装或编译状态要按其枚举语义读取，不能只凭 APK 内存在 `baseline.prof` 就判定目标代码已经完成 AOT 编译。

#### BLAST 的版本含义

AOSP 在 Android 11 tag 已包含 `frameworks/native/libs/gui/BLASTBufferQueue.cpp`，Android 17 仍保留该实现。BLAST 参与 buffer 与 transaction 的协作，但这个历史节点不等于所有旧版 BufferQueue 指标都失效，也不代表 App 侧某个超时能直接归因到 BLAST。渲染诊断仍需结合 FrameTimeline、BufferQueue/SurfaceFlinger 事件、fence 和线程调度。

### 按瓶颈类型选择优化方向

| 证据形态 | 常见方向 | 仍需排除的情况 |
|---|---|---|
| 关键线程长时间 runnable，CPU 饱和 | 减少工作量、改进算法和数据布局、消除重复计算 | 线程被更高优先级任务抢占、thermal 降频、错误的 CPU 亲和性 |
| 关键线程 blocked 或 sleeping | 检查锁、Binder、futex、I/O 和条件等待 | 正常的异步等待、缺失唤醒事件、trace 时钟或切片关联错误 |
| RenderThread/GPU 超过 deadline | 减少绘制复杂度、过度绘制、昂贵 shader 或资源上传 | SurfaceFlinger 合成、fence 等待、刷新率切换、驱动与 GPU 频率 |
| Java heap 持续增长 | 检查保留路径、生命周期、缓存上限 | 预期缓存、延迟 GC、native/graphics 内存被误算为 Java heap |
| native 分配持续增长 | 用 heapprofd/采样栈定位分配点，核对释放路径 | 采样偏差、allocator 保留、mmap/共享内存和 GPU 内存 |
| 网络阶段长尾 | 拆分 DNS、连接、TLS、TTFB、下载和重试 | 服务端排队、无线电状态、代理/VPN、缓存命中差异 |
| 长时间高功耗或发热 | 缩短活动时间、减少唤醒与无效任务、检查 thermal 反馈 | 电量归因窗口过短、设备充电状态、其他进程和屏幕亮度 |

优化时优先删掉不必要的关键路径工作。异步化只能改变执行位置；后台线程仍会消耗 CPU、内存带宽和电量，也可能与渲染线程竞争。

## 「器」：按问题选择证据工具

### 工具能力对照表

| 工具 | 适合回答 | 无法单独回答 |
|---|---|---|
| Macrobenchmark | 启动、滚动、动画等端到端 CUJ 是否回退 | 某个内部函数为何变慢 |
| Microbenchmark | 一段进程内 CPU 代码在受控循环中的成本 | 完整 App、系统调度、I/O 和用户旅程 |
| Perfetto / Trace Processor | 多进程时间线、调度、FrameTimeline、Binder、频率和已启用数据源 | 未采集的方法、对象保留关系、业务语义 |
| Android Studio CPU Profiler | App 方法、线程活动和采样/插桩调用栈 | 完整系统因果关系；不同模式的扰动也不同 |
| Android Studio Memory Profiler / heap dump | Java/Kotlin 分配与对象保留关系 | native/GPU/共享内存的完整归因 |
| heapprofd | 可采样的 native heap 分配调用栈 | 每次分配的无损记录、Java 对象引用图 |
| Simpleperf | CPU 采样、调用栈、硬件事件；有符号和权限时可覆盖 Java、Native 与部分内核 | 阻塞等待的完整因果关系、GPU 命令时间线 |
| JankStats | 帧级 jank 启发式判断和应用 UI 状态 | 系统侧根因与完整渲染管线 |
| Android vitals | 线上设备分布、版本趋势和若干质量指标 | 单次问题的完整 Trace 与代码级根因 |
| `dumpsys` | 某一时刻的系统服务状态和聚合计数 | 高精度时序和跨进程因果关系 |

“Perfetto 只看线程、Simpleperf 只看 Native”这类记忆法会误导选型。Perfetto 可包含调用栈和多类 profile 数据，Simpleperf 在配置、运行环境和符号齐全时也能分析 Java、Native 与内核代码。应查看本次采集得到的字段，而不是根据工具名称推断证据范围。

### 三条常用组合路径

#### 启动

1. Macrobenchmark 固定 `StartupMode`、`CompilationMode` 和 CUJ，建立 TTID/TTFD 分布。
2. Perfetto 查看进程创建、首帧前主线程、Binder、I/O、ART、RenderThread 与 SurfaceFlinger。
3. 对可疑函数补充应用 slice、CPU Profiler 或 Simpleperf 采样。
4. 修改后复跑相同基准，检查启动后的交互、内存和功耗。

#### 流畅度

1. 用 JankStats 或线上指标找到页面、版本和设备分群。
2. 在相同刷新率和数据集下采集 FrameTimeline Trace。
3. 沿超时帧检查主线程、RenderThread、GPU、SurfaceFlinger、fence 和调度。
4. 用 Macrobenchmark 的 FrameTimingMetric 或项目指标做回归测试。

#### 内存

1. 用 RSS/PSS、Java/native heap 和 GC 趋势确认增长发生在哪个内存域。
2. Java 对象保留使用 heap dump；native 分配使用 heapprofd 或采样工具。
3. 将调用栈映射到版本一致的符号和源码，区分业务持有、allocator 保留和共享内存。
4. 重复同一 CUJ，验证增长斜率、峰值和退出后的回落。

## 投入产出与性能预算

### 排优先级时看四个维度

- **影响人数**：受影响用户、设备型号、系统版本和发布版本占比。
- **出现频率**：每次启动、每天一次，还是极少出现。
- **体验损失**：延迟长度、操作是否中断、数据是否丢失、是否导致退出。
- **修复把握与成本**：证据是否充分，改动范围、验证成本和副作用风险。

可以用“影响人数 × 频率 × 损失程度”帮助排序，但不要把主观评分伪装成精确数学模型。低频的严重 ANR、OOM 或数据损坏仍可能高于高频的轻微波动。

### 预算是一份版本化测量合同

一条可执行预算应包含：

- CUJ 和起止信号；
- App 版本、构建类型和混淆状态；
- 设备档位、Android 版本和刷新率；
- 编译模式、安装渠道与 profile 状态；
- 样本次数、统计量和允许噪声；
- 超限后的复测、审批与回滚规则。

预算也要随产品阶段调整。新增安全检查或无障碍能力可能带来可接受成本；团队应记录成本、用户收益和批准人，避免为了守住旧数字而隐藏必要工作。

### 用回归测试保护已经取得的收益

基准测试适合监控稳定 CUJ。CI 中出现波动时，应先检查设备、温度、系统任务和测试脚本，再判断代码回退。单次失败不宜自动归因给最近提交；连续分布漂移也不应被一句“测试不稳定”长期忽略。

线上发布后继续按版本和设备分群观察。Android vitals 的用户感知崩溃率、ANR、慢渲染和电量指标各有采集条件与评估窗口，项目内指标也要记录采样率和分母。

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

设计阶段可以选择同样清晰、成本更低的实现；复杂优化则需要基线和热点证据。Jeff Dean 与 Sanjay Ghemawat 的 Performance Hints 也建议：当可读性和复杂度没有明显代价时，选择更快的方案，同时用 profile 和 benchmark 验证。

## 性能工程师的能力模型

- **系统理解**：能从 App、Framework、Native 服务、内核调度到硬件资源解释一次 CUJ。
- **实验设计**：知道怎样固定变量、选择样本和识别测量扰动。
- **工具使用**：能配置采集、写查询、处理符号，并识别工具的不可见范围。
- **源码阅读**：能把 Trace 事件、API 行为和版本差异映射到对应 tag 的代码。
- **统计判断**：能看分布、长尾和置信范围，不用单次结果下结论。
- **工程决策**：能比较用户影响、修复成本、副作用和维护成本。
- **协作表达**：能提交复现步骤、证据、假设、改动与复测结果，让其他团队复查。

一份合格的性能报告，至少让没有参与排查的人回答五个问题：什么场景、影响谁、证据在哪里、为何采用这项改动、复测怎样证明收益。

## 让调查结果可以复用

每次调查至少留下问题场景、设备与构建、原始数据、查询或时间窗、源码 tag、候选假设、干预结果、副作用、适用边界和回退条件。截图可以辅助沟通，但不能替代可重跑的查询和受控保存的原始制品。

机制文档与操作手册分开维护：前者解释源码、数据语义和版本边界，后者记录环境、命令、预期输出、失败处理与清理步骤。机制变化时不必重写每份操作记录，工具入口变化时也不应改写历史结论。最终把问题、证据、修改、复测和未确认项关联到同一个版本化记录，再交给 §15.9 的团队治理流程持续验收。

## 交付前检查表

- [ ] CUJ、起止信号和成功条件是否明确？
- [ ] Android、App、构建、设备和编译状态是否记录？
- [ ] 原始数据与查询是否可复查？
- [ ] Trace 配置是否包含区分当前假设所需的数据源？
- [ ] 结论是否区分观测事实、推断和待排除项？
- [ ] 改动前后是否使用同一测量协议？
- [ ] 是否检查内存、功耗、稳定性和功能副作用？
- [ ] 是否建立可重复的回归测试或线上分群指标？

## 小结

「道」把模糊反馈转换为有边界的用户旅程和指标；「术」用可证伪假设、受控实验和复测形成可复查结论；「器」提供各自范围内的证据。团队把这三部分写进同一份性能报告，后续版本才能复用结论，也能判断旧结论在 Android 17 上是否仍成立。

## 参考资料

- [Android Developers：App performance](https://developer.android.com/topic/performance)
- [Android Developers：Benchmark your app](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [Android Developers：Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Android Developers：Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
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
- [Liao et al.：Automatically Analyzing Performance Issues in Android Apps: How Far Are We?](https://arxiv.org/abs/2407.05090)
