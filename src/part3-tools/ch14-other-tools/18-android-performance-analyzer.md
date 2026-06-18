---

title: Android Performance Analyzer 与系统性能分析
chapter: 14.18
status: ready-for-review
drafted_date: 2026-05-21
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: 2026-05-21
last_verified_against: Android Developers APA docs/blog 2026-05-19 + Perfetto tracing docs
confidence: medium
sources: 
  - type: official
    path: "https://developer.android.com/android-performance-analyzer"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/run"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer/analyze/ai"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/introducing-android-performance-analyzer.html"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/whats-new-android-developer-tools.html"
tags: [android-performance-analyzer, profiler, perfetto, gpu, tools]
related_chapters: ["13.10", "14.1", "14.8", "14.17", "26.14"]
created_by: task2a-knowledge-gap
created_date: 2026-05-21
gap_source: 每日信息/官方文档
---
-

# 14.18 Android Performance Analyzer 与系统性能分析

<!-- outline-start -->
## 要点

### 🔹 APA 在 Android profiling 工具体系中的位置
说明 Android Performance Analyzer 与 Android Studio Profiler、Perfetto UI、AGI、厂商 GPU 工具的分工，明确它适合回答 CPU、GPU、内存、功耗和系统行为交叉的问题。

### 🔹 采集入口与设备版本边界
梳理 standalone desktop app、Android Studio Panda 4+ System Trace viewer、Android 12+ 设备、GPU counter / render stage 可见性的版本与硬件边界。

### 🔹 Perfetto Trace 基础与自定义配置
说明 APA 依赖 Perfetto system tracing 的事实，整理 launch capture、manual trigger、自定义 Perfetto config、已有 trace 导入等常用采集路径。

### 🔹 GPU counter、SurfaceFlinger 与帧路径分析
围绕图形重负载场景，覆盖 Qualcomm、Arm、Imagination、Samsung GPU counter、SurfaceFlinger 事件、截图时间线和帧耗时定位方法。

### 🔹 项目化对比与回归分析
整理 project model、multiple traces、split windows、bookmarks、annotations、pinned tracks 在 A/B 测试、长期回归和团队协作中的使用方式。

### 🔹 AI 辅助 SQL 与可复核分析边界
说明 APA / System Profiler 中 AI 辅助 SQL 的使用边界：AI 可以生成查询草案，但结论必须回到 trace 数据、Perfetto SQL、设备和场景条件上复核。

## 扩展

### 🔸 GFXReconstruct 与未来帧调试能力
记录官方提到的 GFXReconstruct 图形 capture / replay 方向，后续等待公开文档或 release note 后再展开。

### 🔸 与 SmartPerfetto / Agent 分析协议的关系
对比官方 APA 和自建 SmartPerfetto / Agent 协议：前者偏交互式 profiler，后者偏可复用排障流程和自动化 SQL 分析。

### 🔸 线上观测与离线 profiler 的衔接
讨论 APA 发现的局部 trace 结论如何转成 statsd、APM、Macrobenchmark 或 CI 回归门禁规则。

<!-- outline-end -->

Android Performance Analyzer（APA）是 Google 在 2026 年推出的新一代 Android 性能分析工具。它把 CPU、GPU、内存、功耗和系统行为放在同一个系统追踪视图里，适合处理“帧耗时、线程调度、GPU counter、SurfaceFlinger 事件和功耗曲线同时变化”的问题。

这类问题用单一工具很容易看偏：Android Studio Profiler 更贴近 App 开发过程，Perfetto UI 更贴近通用 Trace 和 SQL，AGI 更贴近图形帧级分析。APA 的位置在中间：它基于 Perfetto Trace 工作，并把采集、GPU 数据、截图导航、项目化对比和 AI 辅助查询组合成一套更面向性能排障的桌面工作台。[已验证: 官方文档, developer.android.com/android-performance-analyzer][已验证: Android Developers Blog, 2026-05-19]

## APA 在 Android profiling 工具体系中的位置

APA 回答的是系统级相关性问题，而不是替代所有工具。

| 工具 | 主要回答的问题 | 适合场景 | 边界 |
|---|---|---|---|
| Android Studio Profiler | App 进程内 CPU、内存、网络、能耗和常规 System Trace | 开发期快速确认热点、堆对象、方法耗时，详见 14.1 节 | IDE 视角更强，跨 trace 对比和 GPU 专项数据不如 APA 集中 |
| Perfetto UI / Trace Processor | 通用 Trace 时间轴、Perfetto SQL、批量查询 | 需要写 SQL、处理大 Trace、复核系统事件顺序，详见 13.10 节 | 采集与项目管理需要自己组织，GPU counter 可见性依赖配置和设备 |
| Android Performance Analyzer | CPU / GPU / Memory / Power / SurfaceFlinger 同屏分析 | 图形重负载 App、游戏、系统行为交叉排障、A/B Trace 对比 | Beta 阶段；结论仍要回到 trace 数据和设备条件复核 |
| AGI / RenderDoc / 厂商 GPU 工具 | 帧级命令、shader、render target、厂商专用 counter | 已确认 GPU 侧瓶颈，需要看单帧或硬件细节，详见 14.8 节 | 帧捕获开销高，不适合拿来测量真实帧率 |
| statsd / APM | 线上事件、聚合指标、用户会话和回归趋势 | 线上发现异常、发布门禁、长期监控，详见 14.17 和 26.14 节 | 不能还原完整现场，需要 Perfetto / APA 回放局部时序 |

一条稳妥的使用顺序是：线上指标或测试脚本先定位异常窗口，APA 录制或导入对应 Trace，Perfetto SQL 复核关键时间段，必要时再转 AGI / RenderDoc 做帧级检查。这样能避免直接从某一条 counter 曲线推结论。

## 采集入口与设备版本边界

APA 目前有两种入口：独立桌面应用，以及 Android Studio Panda 4 Canary 及之后版本中的新版 System Trace viewer。独立应用不要求 Android Studio 工程或 Gradle 构建，官方说明它支持 Windows、macOS 和 Linux；Android Studio 集成入口更适合 IDE 内查看和排障。[已验证: Android Developers Blog, 2026-05-19]

版本和设备边界要先写在分析记录里：

- Android 12+ 设备提供更完整的系统级采集体验，尤其是 GPU counter 和 render stage 可见性。[已验证: Android Developers Blog, 2026-05-19]
- GPU counter 是否可选取决于设备、GPU 厂商和 APA 当前支持范围。官方录制文档写明：如果 APA 不支持该设备的 GPU counter，配置窗口里的 GPU Counters 入口可能不可用。[已验证: 官方文档, developer.android.com/android-performance-analyzer/run]
- APA 当前仍是 Beta 软件。团队内保存结论时，要记录 APA 版本、Android Studio 版本、设备型号、系统 build、GPU 型号和 TraceConfig。
- Vulkan 调试标记和截图能力依赖 Vulkan layer。截图功能依赖拦截标准 `VK_KHR_swapchain`；如果应用使用替代呈现机制，官方文档说明截图可能无法采集。[已验证: 官方文档, developer.android.com/android-performance-analyzer/run]

录制入口分两类：`Launch app and record` 会在开始录制后自动启动目标 App；`Record a running app` 只录制已经运行的场景，且只能手动开始录制。开始触发支持 Manual、On Startup、On Startup with Delay；结束触发支持 Manual 和 Duration。这个组合对启动、滑动、战斗场景、后台恢复这类场景很实用：启动用 On Startup，稳定复现场景用 Manual，长时间回归用 Duration。[已验证: 官方文档, developer.android.com/android-performance-analyzer/run]

## Perfetto Trace 基础与自定义配置

APA 的系统分析能力建立在 Perfetto system tracing 上。官方发布说明明确写到，APA 依赖 Perfetto 做系统追踪；录制文档也提供自定义 Perfetto `TraceConfig` proto 的入口。[已验证: Android Developers Blog, 2026-05-19][已验证: 官方文档, developer.android.com/android-performance-analyzer/run]

这决定了两件事。

第一，APA 的 trace 结论可以回到 Perfetto SQL 复核。帧时间、线程调度、CPU frequency、slice、counter、SurfaceFlinger 事件这些数据都应当能在 Trace Processor 里查到对应表或事件。遇到争议时，不要只截 UI 图；把时间区间、进程、线程、counter 名称和 SQL 查询一起留档。

第二，采集配置要按问题收缩。官方文档建议：录制超过一分钟的 Trace 时减少数据源，降低对测试设备的性能影响；一分钟以内的短 Trace 可以选择更多数据源。图形问题常见配置是 CPU scheduling、CPU frequency、目标进程 slices、GPU counters、SurfaceFlinger / FrameTimeline 相关事件、截图时间线。功耗问题再补电池和电源相关 counter；ANR 或输入问题再补 Binder、Input、sched wakeup 相关事件。

APA 的自定义配置入口有一个很实用的细节：切到自定义 `TraceConfig` 时，工具会按当前 UI 配置自动生成一份 proto 文本，工程师可以在这个基础上改。适合团队把“启动回归”“滑动回归”“GPU 热点”“功耗热区”做成几份模板，减少每次手工勾选带来的口径漂移。[已验证: 官方文档, developer.android.com/android-performance-analyzer/run]

## GPU counter、SurfaceFlinger 与帧路径分析

APA 最值得放进工具箱的场景，是图形重负载 App 或游戏的帧路径分析。官方发布说明列出 Qualcomm、Arm、Imagination、Samsung 多类 GPU counter 支持，并提到 SurfaceFlinger 事件、截图时间线、FPS 与 Frame Duration tracks。[已验证: Android Developers Blog, 2026-05-19]

排查一段掉帧时，可以按这个证据顺序走：

1. 锁定异常帧：先看 FPS / Frame Duration tracks，标出超过预算的帧或连续抖动窗口。
2. 对齐画面阶段：用截图时间线找到具体 UI / 场景状态，确认异常发生在首屏、转场、列表滑动、战斗特效还是后台恢复。
3. 分 CPU 和 GPU：如果目标线程长时间 Runnable 但迟迟拿不到 CPU，先看调度；如果 CPU 提交很快但 GPU counter、render stage 或 SurfaceFlinger 合成阶段变长，再转图形侧。
4. 查 SurfaceFlinger：合成、提交、显示相关事件可以把 App 渲染和系统显示阶段分开，避免把系统合成等待误判成 App 主线程耗时。
5. 必要时转帧级工具：APA 只能把问题定位到某段 GPU 或合成成本；shader、draw call、render target、纹理带宽这类问题仍要交给 AGI、RenderDoc 或厂商工具。

Vulkan 应用还可以在 APA 里开启 Vulkan layer：CPU timing layer 会把 Vulkan API 调用时间显示为调用线程上的 slices；Render Pass Debug Names 可以把代码里的 render pass 名称显示到 Trace 视图；Screenshots 可以把帧截图挂到时间轴上。官方文档也给了开销边界：`vkCmdDraw` 等高频函数会被排除在 CPU timing layer 外，因为记录它们会扭曲 profiling 结果。[已验证: 官方文档, developer.android.com/android-performance-analyzer/run]

这类数据适合做“定位”，不适合直接写成绝对性能结论。GPU counter 名称、单位、可见性和厂商实现有关；不同 SoC 的同名 counter 也可能有不同解释。跨设备对比时，优先比较同一设备、同一系统版本、同一场景的前后差异。

## 项目化对比与回归分析

APA 的 project model 让多个 Trace 保持在同一个项目侧栏里，官方把它定位为 A/B testing 和 longitudinal tests 的工作流。它还支持多 trace tab、split windows、bookmarks、annotations、pinned tracks 和 track size 持久化。[已验证: Android Developers Blog, 2026-05-19]

这些功能对团队协作很有价值。一次性能回归复盘可以这样留证据：

- baseline trace：旧版本、同设备、同脚本、同场景。
- candidate trace：新版本或实验分支，采集配置与 baseline 保持一致。
- 标注窗口：用 bookmark / annotation 标出异常帧、关键用户操作、场景切换点和系统事件。
- 固定轨道：把目标进程主线程、RenderThread、GPU counter、CPU frequency、SurfaceFlinger、Frame Duration tracks 固定在顶部。
- SQL 摘要：用 Perfetto SQL 导出 P50 / P90 / P99、慢帧数、目标线程 CPU 时间、GPU 忙碌区间占比等可复核指标。

这样生成的证据可以接回 26.14 节的实验统计口径：APA 负责解释“为什么这个窗口变慢”，Macrobenchmark / CI / APM 负责证明“这个变化是否稳定复现”。二者不能互相替代。一次本地 Trace 的优化收益，只能算机制证据；发布前仍要有自动化或线上分位值验证。

## AI 辅助 SQL 与可复核分析边界

APA 支持面向 AI Agent 的两个官方 skill：`perfetto-trace-analysis` 用于从高层问题给出分析起点，`perfetto-sql` 用于生成自定义 Perfetto SQL 查询草案。官方文档给出的例子是“Why is my app startup slow?”这类问题，以及让 Agent 帮忙写 SQL 查询。[已验证: 官方文档, developer.android.com/android-performance-analyzer/analyze/ai]

这里的边界要明确：AI 生成的是查询草案和分析路径，不是性能结论。可发布的结论至少要补四项条件：Trace 文件、设备和系统版本、场景复现步骤、SQL 或 UI 时间窗口证据。SQL 也要人工检查表名、单位和 join 条件。Perfetto 时间通常是纳秒；FrameTimeline、slice、counter、sched 表之间的 join 如果没按时间窗口裁剪，容易把相邻帧或相邻线程的数据算进去。

适合交给 Agent 的任务包括：

- 根据目标时间区间生成候选 SQL，例如统计目标进程线程 CPU 时间、Runnable 等待时间、GPU counter 均值和慢帧分布。
- 把一段 Trace 的观察点整理成复盘表，但每一行都带数据来源。
- 对比两段 Trace 的同名指标，指出需要人工复核的差异窗口。

不适合交给 Agent 的任务包括：直接判断根因、自动给出收益百分比、跨设备外推、从单次 Trace 推线上结论。Agent 没有现场上下文，设备状态、温度、刷新率、后台负载和实验分桶都可能改变结果。

## [自动发现] GFXReconstruct 与未来帧调试能力

官方发布说明写到，APA 后续的 frame profiling / debugging features 将由 LunarG 的 GFXReconstruct 技术提供图形 capture / replay 能力。当前公开文档能确认的是方向，不应写成已发布能力。[已验证: Android Developers Blog, 2026-05-19]

这条线和 14.8 节的 AGI、RenderDoc、Sokatoa 有交叉。等 APA 公开帧捕获文档后，需要重新划分工具边界：APA 是否承担单帧命令分析，AGI 是否继续作为专用帧级工具，RenderDoc 导出和 GFXReconstruct replay 是否进入官方推荐流程。

## [自动发现] 与 SmartPerfetto / Agent 分析协议的关系

13.18 节的 SmartPerfetto 更偏“把分析流程产品化”：固定采集模板、固定 SQL、固定判断表，把经验变成可重复运行的分析平台。APA 更偏官方交互式 profiler：现场录制、窗口浏览、多 trace 对比、GPU counter 和截图导航。

两者可以共存。APA 适合探索和复盘，SmartPerfetto 适合批量化和门禁。一个可行分工是：先用 APA 找到稳定的 trace 信号和 SQL，再把成熟查询迁移到 SmartPerfetto 或 CI 任务里。这样不会把人工探索留在截图里，也不会让自动化系统过早固化错误指标。

## [自动发现] 线上观测与离线 profiler 的衔接

APA 的结论要转成线上治理规则，必须降级成可稳定采集的信号。常见映射关系如下：

| APA 观察 | 可转化的线上或 CI 信号 | 复核方式 |
|---|---|---|
| 某场景 P90 帧耗时上升 | Macrobenchmark 帧耗时分布、JankStats 慢帧率、APM 页面卡顿指标 | 固定设备池 + 固定脚本 + 分位值置信区间 |
| CPU frequency 降低并伴随帧耗时上升 | 热状态、功耗指标、设备温度分桶、长时间压测结果 | Perfetto 电源 counter + statsd / APM 设备状态 |
| SurfaceFlinger 合成阶段变长 | 同场景离线 Trace 门禁、关键版本手工复测 | APA / Perfetto 保存 baseline 和 candidate Trace |
| GPU counter 指向 shader 或带宽压力 | AGI / RenderDoc 帧级报告、资源体积和 shader 版本记录 | 同设备前后对比，避免跨 GPU 泛化 |
| 启动窗口 Binder 或 I/O 明显增加 | Macrobenchmark StartupTimingMetric、应用侧阶段埋点、Perfetto SQL 门禁 | 采集冷启动 / 温启动分开统计 |

离线 profiler 的价值是解释机制，线上指标的价值是证明范围。把两者分开，性能治理才不会停在“本机看起来变快了”。

## 小结

APA 把 Perfetto Trace、GPU counter、SurfaceFlinger 事件、截图导航、项目化对比和 AI 辅助 SQL 放到同一个性能工作台里。它适合从复杂现场里找证据起点：哪一帧异常、CPU 和 GPU 哪边先变慢、系统合成有没有参与、前后版本差异是否集中在同一时间窗口。

可复核的使用方式很简单：记录采集条件，保留 Trace，SQL 回查关键指标，再把稳定信号迁移到 Macrobenchmark、APM、statsd 或 CI 门禁。APA 负责把问题讲清楚；发布判断仍要交给可重复的实验和线上数据。

## 参考资料

### Android Performance Analyzer 深度调研
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android Performance Analyzer/2026-05-20-Android Performance Analyzer-深度调研.md
- 类型：DeepResearch 调研结果
- 摘要：基于 Google I/O 2026 发布材料和本地官方 skills 文件，系统梳理 APA 与 Perfetto 的架构边界（APA 消费 Perfetto trace、补上 GPU 分析/截图导航/AI Agent Skills 产品层能力）、26x 提速的真实含义（对比 AGI 的 trace 渲染速度）、四家 GPU vendor counter 覆盖范围、AI Agent Skills（perfetto-trace-analysis / perfetto-sql）的真实边界，含完整事实核验表。
- 注入时间：2026-05-23
- 价值：对 APA 营销话术做了逐一事实核验，厘清 APA 与 Perfetto 的精确分层关系，避免读者误读 26x 等数字

- Android Performance Analyzer 官方页：https://developer.android.com/android-performance-analyzer
- Record a system trace：https://developer.android.com/android-performance-analyzer/run
- Use AI-powered analysis features：https://developer.android.com/android-performance-analyzer/analyze/ai
- Introducing Android Performance Analyzer：https://android-developers.googleblog.com/2026/05/introducing-android-performance-analyzer.html
- Android Developer Tools I/O 2026：https://android-developers.googleblog.com/2026/05/whats-new-android-developer-tools.html
- Perfetto TraceConfig docs：https://perfetto.dev/docs/concepts/config



### Android Performance Analyzer 深度调研
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android Performance Analyzer/2026-05-20-Android Performance Analyzer-深度调研.md
- 类型：DeepResearch 调研结果
- 摘要：Google I/O 2026 发布 APA open beta，重新包装 Android 性能工具栈：Perfetto 负责系统级 trace 能力，APA 提供面向应用和游戏的采集、GPU 分析、SQL 分析和 AI Agent Skills 入口。事实核验 26x 渲染提速的限定条件，厘清 APA 与 Perfetto 的架构边界和组合使用策略。
- 注入时间：2026-05-21
- 价值：源码级深度调研，包含 AOSP 路径、调用链和版本矩阵，可作为章节扩展参考或正文补充素材
