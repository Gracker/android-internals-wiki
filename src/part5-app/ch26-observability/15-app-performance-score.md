---
title: "App Performance Score 与性能质量评分归因"
chapter: "26.15"
section: "26.15"
status: finalized
applicable_versions: "Android 11 (API 30) - Android 17 (API 37); App Performance Score Preview 2026"
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "App Performance Score Preview and Android Vitals pages updated 2026-05-19; current Macrobenchmark, Baseline Profiles, and Android Performance Analyzer docs; Android 17 android-17.0.0_r1 SystemHealthManager and PerformanceHintManager sources, retrieved 2026-08-15"
confidence: high
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/5.33-android17-performance-score-attribution-sourcecode.md"
tags: [app-performance-score, android-vitals, macrobenchmark, baseline-profile, performance-governance, observability]
related_chapters: ["15.3", "15.6", "15.9", "19.11", "26.3", "26.6", "26.12"]
sources:
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 6.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 24.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 28.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: official
    path: "https://developer.android.com/topic/performance/app-score"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/measure-baselineprofile"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer"
  - type: official
    path: "https://developer.android.com/reference/android/os/health/SystemHealthManager"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java"
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java"
task6_state: reviewed
pipeline_stage: ready-to-publish
task9_state: reviewed
task2b_state: fixed
last_draft_polish_at: "2026-08-15T21:41:25+08:00"
last_draft_polish_run_id: "20260815-214125-gracker-writing-476"
last_review_finalize_at: "2026-08-15T21:41:25+08:00"
last_review_finalize_run_id: "20260815-214125-gracker-writing-476"
last_rework_at: "2026-08-15T21:41:25+08:00"
last_rework_run_id: "20260815-214125-gracker-writing-476"
---

# 26.15 App Performance Score 与性能质量评分归因

团队拿到一个 0～100 的性能分数后，需要判断它能否转化为可复测的工程任务。[App Performance Score](https://developer.android.com/topic/performance/app-score) 是 Google 在 2026 年仍标为 Preview 的评估框架，包含静态与动态两类评分：静态评分检查源码配置和工具采用情况，动态评分测量指定物理设备上的运行表现。

分数只表示评估表中还有多少改进空间，无法概括线上用户体验。团队仍需维护自己的 KPI（关键绩效指标，用于持续衡量业务或质量目标）。评分项可转换成配置修正、自动化路径、trace 分析和发布验证四类任务；trace 是按时间记录线程、调度、I/O 等事件的性能跟踪文件，Android 17 平台指标可作为环境旁证。

26.3 介绍端侧性能采集，26.6 介绍实验统计，26.12 说明 Android Vitals 与 Play 的线上口径。这里讨论评分到行动的映射，不重复这些章节的采集实现。

## App Performance Score 的定位

App Performance Score 适合研发阶段的快速评估。官方页面给出 0～100 分，低分表示改进空间较大；静态分和动态分可以分别使用。Play Console 使用线上数据判断发布质量和商店可见性，App Performance Score 则用于研发评估，两者用途不同。评分规则、评估方式和建议仍可能随着 Preview 迭代。

它和常见工具的边界可以这样划分：

| 工具或系统 | 回答的问题 | 适合阶段 | 不适合做的事 |
|---|---|---|---|
| App Performance Score | 工程配置和受测路径是否存在评分表覆盖的缺口 | 研发评估、专项立项、版本验收前 | 不能直接给出根因，也不能替代线上监控 |
| Android Vitals / Play Console | Play 用户最近窗口内是否出现坏行为，是否影响商店可见性 | 线上质量裁决、版本趋势复核 | 数据有窗口延迟，不能替代实时报警；详见 26.12 节 |
| Macrobenchmark | 某条启动、滚动或页面路径在受控设备上的耗时与 trace 证据 | CI、专项回归、性能预算 | 不能覆盖所有真实用户路径；脚本质量决定结论质量 |
| Perfetto / Android Studio Profiler | 某次慢启动、慢帧或线程调度异常的时间线证据 | 根因定位、案例复盘、前后 trace 对比 | 单次 trace 不能代表用户总体分布 |
| 自建应用性能监控（APM） | 版本、设备、渠道、用户路径上的长期指标和报警 | 灰度、发布、线上治理 | 指标口径容易漂移，需要记录定义和版本 |

评分项命中后要回到受测场景。启动问题结合 TTID（首次画面显示所需时间）、TTFD（完整内容可用所需时间）、主线程和进程状态；渲染问题结合 FrameTimeline（记录每帧预期与实际时间线的平台数据）、UI thread、RenderThread、SurfaceFlinger 与 GPU；设备差异结合 SoC（系统级芯片，即设备的主处理器平台）、内存、存储、温度和后台负载。分数用于选择调查方向，根因需要可复现路径与 trace。

## 静态评分：低成本配置项先补齐

静态评分不运行 App，需要读取项目源码。官方当前列出的项目包括：使用最新 Android Gradle Plugin、以 full mode（完整优化模式）启用 R8 并把 keep 例外限制在必要范围、正确应用 Baseline Profiles 且覆盖至少一条用户路径、用 Startup Profiles 优化 DEX 布局、采用最新稳定版 Compose，以及在内容可用时调用 `FullyDrawnReporter` 或 `reportFullyDrawn()`。

keep 规则会阻止指定代码被裁剪、优化或改名。Baseline Profiles 是随应用发布、供 Android 运行时（ART）预编译关键代码路径的规则集；Startup Profiles 则指导 R8/D8 调整启动代码在 DEX 文件中的排列。

这些项的价值在于成本低、失败信号清楚、适合接进持续集成（CI）。

| 静态项 | 检查方式 | 改进收益 | 推荐归属 |
|---|---|---|---|
| Android Gradle Plugin 版本 | CI 读取插件解析后的 AGP 版本，不只搜索根工程文本 | 获取当前 R8 与 profile 工具链能力 | 构建负责人 |
| R8 full mode 与例外控制 | 检查 release variant 的 minify 配置、优化模式与 keep 规则范围 | 降低代码体积并启用优化 | 架构 / 构建负责人 |
| Baseline Profile | 验证生成任务、产物内 profile 与关键路径覆盖 | 让所含代码路径从首次运行起获得 AOT（安装时预编译）优化 | 性能专项负责人 |
| Startup Profile | 检查 `startup-prof.txt` 是否生成并被 release 构建消费 | 改善启动期 DEX 布局 | 启动专项负责人 |
| Compose 稳定版本 | 解析 version catalog、BOM 与直接依赖后的版本 | 获取当前稳定版本的性能与修复 | UI 基建负责人 |
| `reportFullyDrawn()` | 检查各启动入口是否在内容可交互时报告 | 为 TTFD 提供业务完成点 | 业务页面负责人 |

[Baseline Profiles 官方说明](https://developer.android.com/topic/performance/baselineprofiles/overview)给出的总体经验是，纳入 profile 的路径从首次运行起可避免解释执行和部分 JIT（即时编译）成本，许多应用测得约 30% 的代码执行性能改善。这个数字来自多款应用的测量经验，具体收益取决于路径覆盖、设备、构建配置和测量方式。

Startup Profiles 在构建时影响 DEX 布局，官方建议与 Baseline Profiles 同时使用。

profile 生成构建与发布构建的配置不同：生成 profile 的 variant（构建变体）应关闭 R8 混淆和优化，以保持规则与方法签名可匹配；最终 release 则应启用 R8，构建工具会把规则重写到优化后的代码。CI 若只检查仓库中存在 `baseline-prof.txt`，无法证明 release 产物已经包含且使用 profile。

静态检查应成为版本基线。新用户路径没有 profile 覆盖、keep 规则范围扩大、release 关闭 R8、关键启动入口缺少 TTFD 报告，都应生成带模块、产物和负责人信息的诊断结果。

## 动态评分：用真实设备校验用户路径

动态评分依赖运行时数据。官方要求使用物理设备，并建议覆盖能代表用户群体的多台设备；低端设备可放大性能差异。分数属于该设备、该构建和该次观察条件，不能脱离这些条件横向排名应用。

当前动态评分覆盖两类指标。slow frame 与 frozen frame 是官方对超出渲染时限和长时间停顿帧的分类；本文保留英文名称，以免和团队自行定义的卡顿阈值混为一谈。

| 动态类别 | 官方评估口径 | 工程侧补充字段 | 关联章节 |
|---|---|---|---|
| Application startup | 从启动到 App 可交互的持续时间，口径指向 TTFD | 启动模式、入口来源、首屏 Activity、进程与编译状态、设备档位 | 21.8、26.3 |
| Rendering performance | 滚动、动画和全屏渲染中的 slow frames / frozen frames 占比 | 页面、刷新率、列表数据量、图片数量、是否 Compose、是否 SurfaceView / TextureView | 22.8、26.3 |

动态评分要分三档投入。

| 档位 | 做法 | 适用场景 | 主要风险 |
|---|---|---|---|
| 手动评估 | 固定构建、设备和前置状态，人工执行路径，记录分数与现象 | 新项目初筛、专项启动前 | 操作差异大，难以稳定复测 |
| Macrobenchmark | 建独立 `com.android.test` benchmark module，用脚本驱动启动、滚动、动画路径，输出 JSON 和 trace | CI 回归、版本对比、性能预算 | 脚本覆盖的只是选定路径 |
| 设备池自动化 | 在低端、主流、高刷、低存储和不同温度状态下运行同一组本地可重复路径 | 发版门禁、灰度前验收 | 设备维护成本高，环境漂移会污染结果 |

[Macrobenchmark 官方文档](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)要求测试位于独立 `com.android.test` 模块。Macrobenchmark 是从应用外部驱动完整用户路径的宏基准测试。

被测 App 需要开启 `profileable`，让 shell 工具能在非调试构建上读取详细 trace 信息；构建应接近生产，关闭 debuggable 标志，并启用 minification（代码压缩与优化）。库会输出控制台结果、JSON 和 trace；它用于建立可重复指标，覆盖范围仍由测试脚本决定。

TTFD 依赖 App 在合适时机调用 `reportFullyDrawn()`。如果首页首帧已经显示，但核心内容尚未加载或输入仍被阻塞，报告点就不应停在 Activity 第一次 draw。通知、深链、支付、扫码和搜索等入口的内容可用点不同，需要分别定义路径；若没有调用报告 API，动态启动评估缺少可信的业务完成边界。

## 从 0-100 分到工程优先级

分数本身不能直接排期。可执行的转换方式是把评分项分成配置、测试、trace 和平台四类队列。

| 队列 | 进入条件 | 处理顺序 | 交付物 |
|---|---|---|---|
| 配置项 | 静态评分缺失或 CI 可自动识别 | AGP / R8 → Baseline Profile → Startup Profile → Compose / `reportFullyDrawn()` | 合并请求（MR）、构建报告、profile 覆盖清单 |
| 测试项 | 动态评分没有稳定脚本或路径覆盖不足 | 冷启动 → 通知启动 → 首页滚动 → 核心交易路径 → 动画 / 全屏路径 | Macrobenchmark 用例、设备列表、结果 JSON、trace 文件 |
| trace 项 | 动态分数低且单靠指标无法归因 | 固定场景 → 采 trace → 标注时间区间 → SQL 量化 → 归因到线程、I/O、Binder、GPU 或资源 | Perfetto 证据、SQL、截图或时间戳 |
| 平台项 | 分数反复波动或线上指标无法解释 | 端侧采集 → 上报 → 聚合 → 版本 / 设备 / 场景分组 → 告警 | APM 字段、看板、报警、灰度规则 |

静态分和动态分都偏低时，官方建议先改善静态项，因为配置修正也可能提升动态表现。之后用 Macrobenchmark 固定启动和渲染路径；复现稳定且数据仍然偏离预算时，再进入 trace 定位。若动态问题会阻断核心业务，也不能因为静态项尚未全部完成而延后处理。

高分仍可能伴随评分表未覆盖的风险。当前页面明确说明这是 App Performance Score 的第一版，评分、评估与建议以后可能变化。版本报告应保存评分日期、页面版本或规则快照，避免把不同规则生成的分数直接画在同一条趋势线上。

## 和 Android Vitals / Play Console 的关系

Android Vitals 反映 Play 用户的线上质量，App Performance Score 反映研发评估表覆盖的改进空间。两者可以建立指标映射，但不能强行统一字段、样本和时间窗口，更不能合成一个总分。

| 维度 | App Performance Score | Android Vitals / Play Console |
|---|---|---|
| 时间位置 | 发版前、专项中、回归测试中 | 发版后，Play 用户窗口内 |
| 数据来源 | 源码配置检查 + 物理设备动态测量 | 用户同意后由 Android 设备采集，Play Console / Reporting API 展示 |
| 主要指标 | 静态配置、启动到可交互、渲染 slow / frozen frames | crash、ANR、partial wake lock、启动、慢渲染、LMK、Slow Sessions 等 |
| 决策用途 | 找改进队列、评估专项收益、设置 CI 预算 | 判断线上坏行为、发版暂停、商店可见性风险 |
| 盲区 | 覆盖路径有限，设备组合有限 | 有窗口延迟，国内渠道和非 Play 分发覆盖不足 |

[Android Vitals 官方说明](https://developer.android.com/topic/performance/vitals)覆盖稳定性、性能、电池和权限等问题。2026 年面向一般应用的核心指标（core vitals）包括用户感知崩溃率、用户感知 ANR 率，以及 excessive partial wake lock；Wear OS 表盘应用还包含 excessive battery usage（过度耗电）。

partial wake lock 会让 CPU 在屏幕关闭后继续运行，持续时间过长会造成额外耗电。部分阈值会影响 Google Play 可见性，具体阈值、设备类型和执行日期见 26.12；App Performance Score 不提供这些线上阈值。

发版前用 App Performance Score 与 benchmark 查出可预防问题，例如 release 未启用 R8、profile 未进入产物、受控设备上的启动或渲染回归；上线后用 Vitals 与自建 APM 判断用户是否受影响。实验室结果良好而线上指标恶化时，应按版本、设备、入口和用户路径比较 Play 分组、内部 APM、benchmark trace 与变更记录，不能用实验室分数否定线上数据。

## 质量门禁与回归防护

App Performance Score 接入门禁时，不能只保存总分。门禁需要保存评分规则版本、分项、构建产物、设备、路径、前置状态、原始结果、trace、负责人和处置动作。

| 门禁层级 | 检查项 | 失败处理 | 记录字段 |
|---|---|---|---|
| 合并前 | R8、AGP、profile 文件、Compose 版本、`reportFullyDrawn()` 标记 | 阻断或要求性能负责人批准 | commit、模块、失败项、豁免原因 |
| 周期性 CI | 冷启动、通知启动、首页滚动、核心页面动画 | 标记回归，生成统计与 trace 对比 | 设备、系统版本、应用版本、样本数、分布、trace 路径 |
| 发版前 | App Performance Score 静态 + 动态项、低端机组合 | 暂停发布或缩小灰度 | 分数、路径覆盖、低端机结果、未解决项 |
| 灰度中 | 自建 APM 指标、Vitals 早期信号、用户日志 | 控量、回滚、补丁或下架灰度 | 版本、渠道、设备、实验组、报警时间 |
| 发布后 | Vitals 当前窗口、趋势和设备分布 | 建专项或回退策略 | Play 指标定义、内部指标、责任模块 |

门禁可以允许豁免，但豁免需要负责人、依据、影响路径、用户占比、替代防护和到期时间。没有这些字段，分数只能形成一次性报告。

回归防护适合使用团队自己的性能预算，无须追求 App Performance Score 满分。启动预算可以包含 TTFD 分布与超预算比例，渲染预算可以包含卡顿（jank）、slow/frozen frame 分布和连续卡顿。门禁同时检查样本量、设备状态和统计不确定性；调整预算时，应提供同一构建产物的 trace、实验记录或明确的业务取舍。

## 常见误用边界

业务指标仍需单独监控。一个应用分数高，但支付页点击后等待很久、搜索首屏空白、消息通知进入会话慢，用户仍会觉得差。业务路径的可用时间、成功率和取消率要由 APM 与业务埋点记录。

动态评分只能指出受测路径偏慢，根因仍要由 trace 验证。Perfetto 或 Android Studio Profiler 可以检查线程运行、Runnable 排队、I/O、Binder、锁等待、GPU、SurfaceFlinger 和资源加载。长 slice（trace 时间线中带起止时间的任务片段）可能包含睡眠或等待，需结合 `thread_state` 判断 CPU 是否持续执行；详见 13.1、15.3 和 26.3。

设备分层也要单独设计。官方建议选择代表用户群体的设备，并提示低端设备能放大问题。只用一台旗舰机测量，会遗漏低速存储、低内存、高温和 OEM 调度差异。弱网属于业务路径的额外测试条件，当前 App Performance Score 动态评分没有把它列为独立类别。

专项判断需要更细的证据。R8、Baseline Profile、Startup Profile、Compose 版本这些静态项适合快速修正；数据库膨胀、图片解码、页面预加载、SurfaceView 合成、GPU 带宽和后台任务唤醒等问题则要另行测量。分数可以提示调查方向，无法列举全部根因。

## App Performance Score 与 Android Performance Analyzer 联动

动态评分发现问题后，工具要按工作负载选择。[Android Performance Analyzer](https://developer.android.com/android-performance-analyzer) 当前官方定位面向游戏性能分析，重点能力包括 Vulkan render pass（组织一组渲染操作的 Vulkan 单元）的调试标注，以及基于项目的多 trace 比较。

普通 Android App 的启动、UI 线程和 FrameTimeline 分析以 Perfetto 或 Android Studio 为主；包含 Vulkan 游戏渲染时，再使用 APA 的专用视图。

推荐路径如下：

| 评分异常 | 主要工具与观察点 | 后续动作 |
|---|---|---|
| TTFD 变慢 | Perfetto：app launch、main thread、Binder、I/O、CPU frequency、`thread_state` | 标注进程启动、首帧、内容可用与可交互点 |
| 滚动 slow frames 上升 | Perfetto：FrameTimeline、UI thread、RenderThread、SurfaceFlinger | 按帧区间判断 App、合成或 GPU deadline miss |
| Vulkan 游戏动画异常 | APA：Vulkan debug markers、render pass、多 trace 项目 | 固定场景并比较相同设备上的前后 trace |
| 低端机波动大 | Perfetto 与设备状态：频率、thermal、内存、I/O、后台负载 | 同一设备重复采样，量化环境差异 |

不论使用哪种查看器，报告都要保留原始 trace、关键时间戳、设备与构建信息、采集配置、查询语句和工具版本。截图只能辅助说明，不能替代可复查的 trace。

## 分数口径的团队协作模板

一次评分报告应该让研发、测试、产品都能读懂，但字段不能变成宣传稿。推荐模板如下：

| 字段 | 写法 |
|---|---|
| 测试对象 | 应用版本、commit（源码修订标识）、构建类型、是否启用代码压缩与优化（minify）、是否带 profile |
| 设备组合 | 设备型号、SoC、Android 版本、刷新率、存储剩余、温度起点 |
| 静态项 | AGP、R8、Baseline Profile、Startup Profile、Compose、TTFD 标记 |
| 动态路径 | 冷启动、通知启动、首页滚动、核心页面、动画或全屏路径 |
| 分数变化 | 总分、静态分、动态分、变化项，不只写总分 |
| 证据 | Macrobenchmark JSON、Perfetto 或 APA trace、截图、SQL、APM 链接 |
| 决策 | 立即处理、进入下个版本、限期豁免、无需处理 |
| 责任人 | 模块、负责人、截止日期、复测时间 |

报告应写清已完成项、仍超预算的路径、证据和后续动作。例如：“release 已启用 R8，产物已验证包含 Baseline Profile；低端设备 A 的冷启动分布仍超团队预算，trace 显示首页数据预加载占用主线程，进入 21.8 启动专项。”这种结论可以被分派和复测。

## 低端机样本池建设

动态评分离不开设备池。官方提醒低端设备能放大性能问题，也要求选择接近用户群体的设备。样本池不必很大，但要覆盖会改变结论的主要维度。

| 设备类型 | 覆盖目的 | 最小要求 |
|---|---|---|
| 低端机 | 放大启动、I/O、内存、线程调度问题 | 低内存、低存储、eMMC 或低速 UFS 存储、60Hz |
| 主流机 | 覆盖主要用户群体体验 | 当前线上占比最高的 SoC / OEM 组合 |
| 高刷机 | 检查刷新率变化下的帧表现 | 记录运行时刷新率与标称垂直同步（nominal VSync）间隔，不把固定 16.6ms 套给所有设备 |
| 低存储设备 | 复现安装、数据库、缓存、dexopt（DEX 安装后编译）和 I/O 波动 | 使用团队定义的低存储分组，并记录实际可用空间和清理策略 |
| 弱网场景 | 区分业务可用时间中的网络与本地执行 | 固定网络整形参数，即人为设定带宽、延迟和丢包；与 App Performance Score 分项报告 |
| 高温前后 | 检查热状态（thermal）对 CPU / GPU 频率和动态分的影响 | 同场景冷机、热机各跑多轮 |

每台设备都要绑定维护规则：系统版本、刷新率、供电、后台状态、编译模式、缓存/数据处理、可用存储和温度起点都要记录。官方也提醒动态分数可能在代码未变时波动；应连续运行多轮并报告常见表现与分布。环境字段缺失时，评分只能作为线索。

## Android 17 的 CPU/GPU headroom 边界

CPU/GPU headroom 是处理器与图形处理器的剩余容量估计，独立于 App Performance Score、Play 和自建 APM 的指标。Android 16（API 36）加入这项能力，适合在重复、持续且负载较高的场景中作为 trace 与 benchmark 的环境旁证。

Android 17 通过 [`SystemHealthManager`](https://developer.android.com/reference/android/os/health/SystemHealthManager) 提供公开查询入口；`PerformanceHintManager` 用于另一类运行时协作。

`android-17.0.0_r1` 的 [`SystemHealthManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java) 暴露 `getCpuHeadroom()` 与 `getGpuHeadroom()`。有效结果为 0～100，0 表示当前估算没有更多容量；暂时无法估算时可能返回 `Float.NaN`，设备不支持时抛出 `UnsupportedOperationException`。

调用方还应读取设备支持的计算窗口、CPU TID（线程 ID）数量上限与最小轮询间隔，不能把一套参数固定到所有设备。

headroom 侧重近期历史负载，无法预测未来性能。AOSP 注释所说的 TOCTOU，指查询与采取动作之间系统状态已经变化：快速调度和动态调频可能让刚读到的余量迅速失效，因此不宜每次轮询都激进调整工作负载。热限制或电源控制降低频率时，相同工作量的容量占比也会变化。它适合在同一设备、同一路径、相近温度和供电状态下辅助比较；单次读数不足以定义“低端机”，CPU 或 GPU 的单项值也不足以判定根因。

每次有效查询至少包含一次同步 Binder 调用，也就是调用线程要等待系统服务返回的跨进程请求。源码说明这一步可能超过 1ms，首次查询或参数变化后还可能更慢。不要在 UI、RenderThread 或受测关键区间同步等待；采集器需保留 `unsupported`、`NaN` 与参数信息，禁止把缺失值记成 0。

[`PerformanceHintManager`](https://developer.android.com/reference/android/os/PerformanceHintManager) 提供性能提示 API。它从 Android 12（API 31）开始允许 App 为周期性工作创建 hint session；这种会话把执行同一周期任务的一组长期线程视为整体，App 每轮报告目标与实际工作时长，系统据此在期限和功耗之间调节资源。

Android 17 实现见 [`PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)。CPU/GPU headroom 查询属于 `SystemHealthManager`。

隐藏的 AIDL（Android 接口定义语言，用于声明跨进程接口）、测试专用 hint 常量和 HAL（硬件抽象层）内部方法均不属于普通 App 可依赖的稳定接口。

把这两套 API 放进性能报告时，应分清“测量”和“调节”：`SystemHealthManager` 的 headroom 是可选环境样本，`PerformanceHintManager` 是运行时协作机制。二者都不会自动提高 App Performance Score，评分改善仍需由同一构建产物、同一设备和同一路径的动态结果验证。
