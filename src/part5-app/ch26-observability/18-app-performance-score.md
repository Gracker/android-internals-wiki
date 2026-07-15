---
title: "App Performance Score 与性能质量评分归因"
chapter: "26.18"
section: "26.18"
status: finalized
drafted_date: "2026-05-23"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37); App Performance Score Preview 2026"
last_verified: "2026-05-23"
last_verified_against: "Android Developers App Performance Score / Android Vitals / Macrobenchmark / Baseline Profiles docs"
confidence: high
tags: [app-performance-score, android-vitals, macrobenchmark, baseline-profile, performance-governance, observability]
related_chapters: ["15.3", "15.6", "15.10", "19.14", "26.3", "26.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "官方文档"
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 6.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 24.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 28.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md"
  - type: clipping
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
task6_state: revisiting
pipeline_stage: task6_pending
last_task2a_at: "2026-05-23T20:04:00+08:00"
task2a_result: drafted
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-23"
task6_result: pass-light-edit
task9_state: reviewed
last_task6_at: "2026-05-23T20:16:21+08:00"
last_task6_audit: "2026-07-15"
task9_result: auto-fixed
last_task9_at: "2026-05-23T20:25:42+08:00"
last_task9_audit: "2026-07-07"
last_task9_autofix_at: 2026-07-15
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-23"
task9_review_notes: "2026-05-23 20:25 Task9 深度技术审计：pass-tech-review。P0 0 / P1 0 / P2 0；官方 App Performance Score、Vitals、Macrobenchmark、Baseline Profiles、APA 口径复核通过；自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
---

# 26.18 App Performance Score 与性能质量评分归因

<!-- outline-start -->
## 要点

### 🔹 App Performance Score 的定位
说明 App Performance Score 如何把性能治理拆成静态评分与动态评分，和 Android Vitals、Macrobenchmark、Perfetto、APM 平台分别解决哪些问题。

### 🔹 静态评分：低成本配置项先补齐
整理 AGP 版本、R8 优化、Baseline Profile、Startup Profile、Compose 版本等静态项，说明它们为什么属于低成本高收益动作。

### 🔹 动态评分：用真实设备校验用户路径
覆盖冷启动、通知启动、核心页面滑动、动画路径和低端机验证，明确手动测量、Macrobenchmark、UiAutomator 三档投入差异。

### 🔹 从 0-100 分到工程优先级
把分数拆成团队可执行队列：先补静态项，再补自动化测试，再进入 trace 分析和自建性能框架。

### 🔹 和 Android Vitals / Play Console 的关系
说明 Vitals 负责线上坏行为阈值和 Play 可见性，App Performance Score 更适合研发阶段的体检与改进路线。

### 🔹 质量门禁与回归防护
把评分项接入发版门禁、CI、灰度监控和性能预算，避免分数只停留在一次性体检。

### 🔹 常见误用边界
说明 App Performance Score 不能替代业务指标、端侧 trace、机型分层和专项问题分析，避免把单一分数当成全部性能结论。

## 扩展

### 🔸 App Performance Score 与 Android Performance Analyzer 联动
可补充 APA、Perfetto、Android Studio Profiler 在动态评分后的定位路径。

### 🔸 分数口径的团队协作模板
可整理一份研发、测试、产品都能读懂的评分报告模板。

### 🔸 低端机样本池建设
可补充低端机、低存储、弱网和高温场景的最小测试组合。

<!-- outline-end -->

团队拿到一个 0–100 的性能分数之后，最常见的反应是“然后呢？”App Performance Score 是 Google 给出的应用性能体检框架，它把改进项拆成两类：一类是能从工程配置里直接检查的静态项，另一类是必须在设备上跑路径才能得到的动态项。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score]

这节的重点不是复述评分表，而是把分数转成研发队列。对团队来说，分数只回答“哪里还有改进空间”；能推进的是后面的任务拆分：补配置、补测试、补 trace 证据，再把风险接进发版门禁。

把质量平台放在开发、CI、测试、灰度和发布流程里理解；26.3 节分别提供了启动与渲染问题的测量顺序；26.15 节提供了灰度验证和上报组件的组织方式。这里借用的是覆盖顺序和问题分类，不复用原文段落与代码。

## App Performance Score 的定位

App Performance Score 适合做研发阶段的性能体检。官方文档把它描述为一个标准化框架，用少量深入技术任务评估应用性能，并给出改进建议；评分范围是 0-100，分数越低，表示改进空间越大。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score]

它和常见工具的边界可以这样划分：

| 工具或系统 | 回答的问题 | 适合阶段 | 不适合做的事 |
|---|---|---|---|
| App Performance Score | 这个应用的性能配置和关键路径有没有明显短板 | 研发体检、专项立项、版本验收前 | 不能直接给出根因，也不能替代线上监控 |
| Android Vitals / Play Console | Play 用户最近窗口内是否出现坏行为，是否影响商店可见性 | 线上质量裁决、版本趋势复核 | 数据有窗口延迟，不能替代实时报警；详见 26.15 节 |
| Macrobenchmark | 某条启动、滚动或页面路径在受控设备上的耗时与 trace 证据 | CI、专项回归、性能预算 | 不能覆盖所有真实用户路径；脚本质量决定结论质量 |
| Perfetto / Android Performance Analyzer | 某次慢启动、慢帧、GPU 压力或线程调度异常的时间线证据 | 根因定位、案例复盘、A/B trace 对比 | 不负责把问题自动转成组织任务 |
| 自建 APM | 版本、设备、渠道、用户路径上的长期指标和报警 | 灰度、发布、线上治理 | 指标口径容易和平台口径分叉，需要和 Vitals 保持同一套口径 |

这个定位决定了它更像一张检查清单，而不是性能系统的终点。评分项命中后，还要回到具体场景：启动慢看 TTID / TTFD 和主线程；滑动慢看帧耗时、RenderThread、SurfaceFlinger 与 GPU；低端机差看设备档位、存储、温度和后台负载——分数指路，根因还是要靠 trace。

## 静态评分：低成本配置项先补齐

静态评分不跑设备。它检查的是项目是否采用了对启动和渲染有稳定收益的工具与配置。官方列出的静态项包括：使用较新的 Android Gradle Plugin，启用 full mode R8 和最小化例外，正确应用 Baseline Profiles，覆盖一个或多个用户旅程，使用 Startup Profiles 做 DEX layout optimization，使用最新稳定版 Compose，并在合适时机调用 `FullyDrawnReporter` / `reportFullyDrawn()`。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score]

这些项的价值在于成本低、失败信号清楚、适合接进 CI。

| 静态项 | 检查方式 | 改进收益 | 推荐归属 |
|---|---|---|---|
| Android Gradle Plugin 版本 | CI 读取根工程和 convention plugin 中的 AGP 版本 | 解锁构建、R8、profile 工具链能力 | 构建负责人 |
| R8 full mode 与例外收敛 | 检查 release / benchmark variant 的 `isMinifyEnabled`、混淆规则数量和 `-keep` 范围 | 减少 DEX、资源和启动路径负担 | 架构 / 构建负责人 |
| Baseline Profile | 检查 APK / AAB 是否带 profile，脚本是否覆盖启动和关键页面 | 首次启动和首次交互路径更稳 | 性能专项负责人 |
| Startup Profile | 检查 `startup-prof.txt` 是否生成并被 release 构建消费 | 改善启动期 DEX 布局 | 启动专项负责人 |
| Compose 稳定版本 | 检查 Compose BOM / compiler / runtime 版本 | 减少已知渲染与重组问题 | UI 基建负责人 |
| `reportFullyDrawn()` | 检查首屏内容可用点是否调用，避免只统计首帧 | 让 TTFD 更贴近用户可用时间 | 业务页面负责人 |

Baseline Profiles 的官方文档写明，它通过把关键路径提前 AOT 编译，帮助应用从首次启动起提升执行速度；文档给出的经验值是许多应用优化后约 30% 的性能提升。Startup Profiles 则在构建时优化 DEX 布局，官方建议两者一起使用。[已验证: 官方文档, https://developer.android.com/topic/performance/baselineprofiles/overview]

静态项不要等专项排查时才补。更合理的做法是把它们做成版本基线：新模块没有 profile 覆盖、新增 `-keep` 过宽、release 构建关闭 R8、首屏没有 TTFD 标记，都应该在合并或发版前给出提示。

## 动态评分：用真实设备校验用户路径

动态评分依赖运行时数据。官方文档要求使用物理设备，因为动态分数会随设备能力变化；文档也建议使用低端设备放大性能问题，从低分场景开始改。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score]

当前动态评分覆盖两类指标：

| 动态类别 | 官方评估口径 | 工程侧补充字段 | 关联章节 |
|---|---|---|---|
| Application startup | 从启动到应用可交互的持续时间，口径指向 TTFD | 启动类型、入口来源、首屏 Activity、是否通知启动、是否冷设备、低端机档位 | 21.8、26.3 |
| Rendering performance | 滚动、动画和全屏渲染中的 slow frames / frozen frames 占比 | 页面、刷新率、列表数据量、图片数量、是否 Compose、是否 SurfaceView / TextureView | 22.8、26.3 |

动态评分要分三档投入。

| 档位 | 做法 | 适用场景 | 主要风险 |
|---|---|---|---|
| 手动测量 | 固定设备、清数据、重启、人工执行路径，记录分数和现象 | 新项目初筛、专项启动前 | 操作不稳定，难以复现 |
| Macrobenchmark | 建独立 `com.android.test` benchmark module，用脚本驱动启动、滚动、动画路径，输出 JSON 和 trace | CI 回归、版本对比、性能预算 | 脚本覆盖的只是选定路径 |
| 场景自动化组合 | 在低端机、主流机、高刷机、低存储、弱网、高温前后跑同一组路径 | 发版门禁、灰度前验收 | 设备维护成本高，失败归因要回到 trace |

Macrobenchmark 官方文档要求使用独立的 `com.android.test` 模块，被测应用应尽量接近 release：非 debuggable，最好开启 minification，并能输出结果 JSON 和 trace 文件供 Android Studio 分析。[已验证: 官方文档, https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview]

动态评分里最容易漏掉通知启动和“首页可见但不可操作”。启动专项常把结束点放在首帧，但 App Performance Score 关心的是应用可交互时间。对于消息、支付、扫码、搜索等入口，应该单独记录启动路径；对于首页出来后仍在加载数据、预热框架或阻塞滑动的场景，TTFD 要放到内容可用点，而不是 Activity 第一次 draw。

## 从 0-100 分到工程优先级

分数本身不能直接排期。可执行的转换方式是把评分项拆成四类队列：配置项、测试项、trace 项、平台项。

| 队列 | 进入条件 | 处理顺序 | 交付物 |
|---|---|---|---|
| 配置项 | 静态评分缺失或 CI 可自动识别 | AGP / R8 → Baseline Profile → Startup Profile → Compose / `reportFullyDrawn()` | MR、构建报告、profile 覆盖清单 |
| 测试项 | 动态评分没有稳定脚本或路径覆盖不足 | 冷启动 → 通知启动 → 首页滚动 → 核心交易路径 → 动画 / 全屏路径 | Macrobenchmark 用例、设备列表、结果 JSON、trace 文件 |
| trace 项 | 动态分数低且单靠指标无法归因 | 固定场景 → 采 trace → 标注时间区间 → SQL 量化 → 归因到线程、I/O、Binder、GPU 或资源 | Perfetto / APA 证据、SQL、截图或时间戳 |
| 平台项 | 分数反复波动或线上指标无法解释 | 端侧采集 → 上报 → 聚合 → 版本 / 设备 / 场景分组 → 告警 | APM 字段、看板、报警、灰度规则 |

分数低时，不建议直接开 trace 专项。配置项的回报通常更快，也更容易复查；配置项补齐后，再用 Macrobenchmark 把启动和渲染路径稳定下来；只有复现路径稳定、数据仍然差，才进入 trace 定位。

分数高也不代表没有风险。App Performance Score 当前还是 preview 文档中的第一版评分框架，官方明确写到评分、评估和建议未来可能变化。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score] 因此它适合当体检入口，不适合成为唯一 KPI。

## 和 Android Vitals / Play Console 的关系

Android Vitals 看的是 Play 用户质量，App Performance Score 看的是研发阶段的性能改进空间。两者的字段和时间窗口要统一，但不要合并成一个数字。

| 维度 | App Performance Score | Android Vitals / Play Console |
|---|---|---|
| 时间位置 | 发版前、专项中、回归测试中 | 发版后，Play 用户窗口内 |
| 数据来源 | 源码配置检查 + 物理设备动态测量 | 用户同意后由 Android 设备采集，Play Console / Reporting API 展示 |
| 主要指标 | 静态配置、启动到可交互、渲染 slow / frozen frames | crash、ANR、partial wake lock、启动、慢渲染、LMK、Slow Sessions 等 |
| 决策用途 | 找改进队列、评估专项收益、设置 CI 预算 | 判断线上坏行为、发版暂停、商店可见性风险 |
| 盲区 | 覆盖路径有限，设备组合有限 | 有窗口延迟，国内渠道和非 Play 分发覆盖不足 |

官方 Vitals 页写明，Android Vitals 跟踪稳定性、性能、电池使用和权限问题，core vitals 包括 user-perceived crash rate、user-perceived ANR rate 和 excessive partial wake locks；core vitals 会影响 Google Play 可见性。[已验证: 官方文档, https://developer.android.com/topic/performance/vitals]

发版时可以这样分工：App Performance Score 负责拦截“还没上线就能发现”的问题，例如没启用 R8、没有 Baseline Profile、冷启动脚本变慢、低端机滑动掉帧；Vitals 负责验证“真实 Play 用户是否已经受影响”，例如某机型 crash / ANR 越线、partial wake lock 过高、LMK 或慢渲染趋势变差。两者出现冲突时，优先补证据：拿内部 APM 分组、Play Console 分组、Macrobenchmark trace 和版本变更记录放在同一张表里比对。

## 质量门禁与回归防护

App Performance Score 接进门禁时，不要只存一个总分。门禁应该保存评分项、设备、路径、版本、trace 文件、负责人和处置动作。

| 门禁层级 | 检查项 | 失败处理 | 记录字段 |
|---|---|---|---|
| 合并前 | R8、AGP、profile 文件、Compose 版本、`reportFullyDrawn()` 标记 | 阻断或要求性能负责人批准 | commit、模块、失败项、豁免原因 |
| 每日 CI | 冷启动、通知启动、首页滚动、核心页面动画 | 标记回归，生成对比报告 | 设备、系统版本、应用版本、P50/P90/P99、trace 路径 |
| 发版前 | App Performance Score 静态 + 动态项、低端机组合 | 暂停发布或缩小灰度 | 分数、路径覆盖、低端机结果、未解决项 |
| 灰度中 | 自建 APM 指标、Vitals 早期信号、用户日志 | 控量、回滚、补丁或下架灰度 | 版本、渠道、设备、实验组、报警时间 |
| 发布后 | Vitals 28 天窗口、趋势和机型分布 | 建专项或回退策略 | Play 指标、内部指标、责任模块 |

这套门禁要允许豁免，但豁免必须有到期时间。比如某个低端机动态评分长期偏低，如果团队决定先不处理，就要写清影响路径、用户占比、下一次检查日期和替代防护。没有这些字段，分数会变成一次性体检，不会改变后续版本质量。

回归防护更适合用“预算”表达，而不是用“必须满分”表达。启动可以设 P90、P99、慢启动比例和 TTFD 预算；渲染可以设 jank 比例、frozen frame 比例和最大连续慢帧时长；静态项可以设为零豁免或限期豁免。预算一旦变化，必须有同版本 trace 或实验记录支撑。

## 常见误用边界

App Performance Score 不能替代业务指标。一个应用分数高，但支付页点击后等待很久、搜索首屏空白、消息通知进入会话慢，用户仍会觉得差。业务路径的可用时间、成功率和取消率要由 APM 与业务埋点记录。

App Performance Score 不能替代 trace。动态评分告诉团队哪条路径慢，Perfetto 或 Android Performance Analyzer 才能回答时间花在线程运行、Runnable 排队、I/O、Binder、锁等待、GPU、SurfaceFlinger 还是资源加载上。长 slice 也不等于 CPU 正在执行，线程状态仍要查证；详见 13.1、15.3 和 26.3 节。

App Performance Score 不能替代机型分层。官方文档建议选择代表用户群体的设备，并提示低端设备能放大问题。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score] 如果只用一台旗舰机测，动态分数会掩盖低端存储、低内存、高温、弱网和 OEM 调度差异。

App Performance Score 不能替代专项判断。R8、Baseline Profile、Startup Profile、Compose 版本这些静态项适合快速补齐；但某些专项问题需要更细的证据，例如数据库膨胀、图片解码、页面预加载、SurfaceView 合成、GPU 带宽、后台任务唤醒。分数可以触发问题，不能定义全部根因。

## App Performance Score 与 Android Performance Analyzer 联动

动态评分发现问题后，Android Performance Analyzer 可以作为 trace 入口。官方 APA 页面把它定位为 Android 生态的新 profiler 和性能分析工具，当前页面列出的能力包括 AI-powered analysis、Vulkan debug markers、project-based workflow，并支持多 trace 项目工作流。[已验证: 官方文档, https://developer.android.com/android-performance-analyzer]

推荐路径如下：

| 评分异常 | APA / Perfetto 观察点 | 后续动作 |
|---|---|---|
| TTFD 变慢 | app launch、main thread、RenderThread、Binder、I/O、CPU frequency、thread_state | 标注启动阶段，拆分首帧、首屏内容、可交互点 |
| 滚动 slow frames 上升 | FrameTimeline、RenderThread、UI thread、SurfaceFlinger、GPU counters | 标注场景帧区间，判断是应用绘制、合成还是 GPU 压力 |
| 动画 frozen frames | 主线程长任务、Choreographer、RenderThread、GPU completion、资源加载 | 固定动画路径，保存前后两个 trace 做对比 |
| 低端机波动大 | CPU frequency、thermal、内存水位、I/O 等待、后台进程 | 同一设备多轮采样，排除温度和后台负载干扰 |

APA 的价值在于减少工具切换，并把 trace 导航、对比和 SQL 分析放到更贴近 Android 性能工作的界面里。结论仍要保留原始 trace、关键时间戳、设备信息、采集配置和 SQL，方便 Task 6 / Task 9 或团队 review 复查。

## 分数口径的团队协作模板

一次评分报告应该让研发、测试、产品都能读懂，但字段不能变成宣传稿。推荐模板如下：

| 字段 | 写法 |
|---|---|
| 测试对象 | 应用版本、commit、构建类型、是否 minify、是否带 profile |
| 设备组合 | 设备型号、SoC、Android 版本、刷新率、存储剩余、温度起点 |
| 静态项 | AGP、R8、Baseline Profile、Startup Profile、Compose、TTFD 标记 |
| 动态路径 | 冷启动、通知启动、首页滚动、核心页面、动画或全屏路径 |
| 分数变化 | 总分、静态分、动态分、变化项，不只写总分 |
| 证据 | Macrobenchmark JSON、Perfetto / APA trace、截图、SQL、APM 链接 |
| 决策 | 立即处理、进入下个版本、限期豁免、无需处理 |
| 责任人 | 模块、负责人、截止日期、复测时间 |

报告里不要写“性能已达标”这种空泛结论。更好的写法是：“本版本静态项已补齐 R8 和 Baseline Profile；冷启动 P90 在低端机 A 上仍超过预算，已生成 trace，归因到首页数据预加载，进入 21.8 启动专项。”这类结论能直接分派任务，也能被复测。

## 低端机样本池建设

动态评分离不开设备池。官方文档明确提醒低端设备能放大性能问题。[已验证: 官方文档, https://developer.android.com/topic/performance/app-score] 样本池不必一开始很大，但要覆盖会改变性能结论的维度。

| 设备类型 | 覆盖目的 | 最小要求 |
|---|---|---|
| 低端机 | 放大启动、I/O、内存、线程调度问题 | 低内存、低存储、eMMC 或低速 UFS、60Hz |
| 主流机 | 覆盖主要用户群体体验 | 当前线上占比最高的 SoC / OEM 组合 |
| 高刷机 | 检查 90Hz / 120Hz 下帧预算变化 | 记录刷新率，区分 8.3ms / 11.1ms / 16.6ms 目标 |
| 低存储设备 | 复现安装、数据库、缓存、dexopt 和 I/O 抖动 | 存储剩余低于固定阈值并记录清理策略 |
| 弱网设备 | 区分启动慢来自网络还是本地执行 | 固定网络条件和超时策略 |
| 高温前后 | 检查 thermal 对 CPU / GPU 频率和动态分的影响 | 同场景冷机、热机各跑多轮 |

每台设备都要绑定维护规则：系统版本是否升级、后台是否清理、亮度和刷新率是否固定、采样前是否重启、是否清数据、温度起点是否记录。动态评分的波动很多来自环境，而不是代码变化；环境字段缺失时，评分报告只能作为线索，不能作为发版裁决。
