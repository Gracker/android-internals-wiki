---
title: "行业案例"
chapter: "17.3"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-04-21"
last_verified_against: "Android Developers Game Mode/ADPF 文档, Samsung Support Game Booster, Samsung Developer SceneSDK, Android Developers Blog TikTok case study"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/fps-throttling"
  - type: official
    path: "https://developer.android.com/topic/performance/adpf"
  - type: official
    path: "https://www.samsung.com/levant/support/apps-services/know-more-about-the-game-booster-app/"
  - type: official
    path: "https://developer.samsung.com/galaxy-gamedev/blog/en/2022/04/26/accelerate-game-performance-based-on-scenesdk"
  - type: official
    path: "https://android-developers.googleblog.com/2022/08/precise-improvements-how-tiktok-enhanced-its-social-experience-on-android.html"
  - type: blog
    path: "Cubox/抖音 Android 性能优化系列：启动优化实践 - 掘金-2024-01-15.md"
  - type: blog
    path: "Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea-2022-01-13.md"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/window"
tags: ['case-study', 'game-mode', 'adpf', 'startup', 'foldable', 'oem', 'industry']
related_chapters: ["5.6", "7.4", "7.5", "8.2", "8.3", "11.1", "16.1", "17.1", "17.2"]
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
task6_state: "reviewed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-28"
task6_result: "pass-light-edit"
last_task6_audit: "2026-06-22"
last_task6_audit_log: "logs/review/2026-06-22-16-audit.md"
last_task6_audit_notes: "idle audit: L1 禁用词 拆解→分析 1 处小修；高频词均在阈值内；frontmatter 完整；outline 锚点内容需优化。"
section: "17.3"
status: finalized
pipeline_stage: ready-to-publish
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-04"
last_task9_at: "2026-05-04T10:37:13+08:00"
last_task2b_at: "2026-04-27T14:50:00+08:00"
last_task9_audit: "2026-06-17"
last_task9_audit_log: "logs/deep-review/2026-06-17-07-audit.md"
last_task9_audit_notes: "idle audit: no P0/P1; AOSP android-16.0.0_r1 source paths and official Game Mode/ADPF API version guards rechecked; existing P2 guards remain for FileProvider attachInfo, Thermal thresholds, Game State API."
review_notes: "2026-04-28 task9 deep-review: pass-tech-review；无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 2 写入 suggestions。；2026-05-04 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 3。核心 API 与案例链路可通过；仅有 Thermal thresholds API 版本守卫、FileProvider 插桩细节、折叠屏多窗口数据支撑三处 P2。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
---

# 行业案例

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 手机厂商公开分享的性能优化案例（引用公开演讲/博客）
- 🔹 游戏性能优化的行业实践：Game Mode、帧率稳定、温控策略
- 🔹 系统级启动速度优化案例
- 🔹 大型 App 与厂商协作的性能优化案例

### 扩展（可选深入）

- 🔸 汽车/IoT/TV 等 Android 变体的性能优化
- 🔸 折叠屏设备的性能挑战与优化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要看行业案例

前十六章我们一直在分析 Android 系统的内部机制和优化方法——VSync 怎么工作、Binder 怎么调度、SurfaceFlinger 怎么合成。这些是"兵器谱"，告诉你每件兵器的原理和用法。但落到具体性能问题时，怎么选兵器、怎么组合、怎么根据现场条件调整策略，光看原理是不够的。

行业案例的价值在于：**它们是真实战场的复盘报告。** 每一个案例背后都是某个团队在数亿用户、复杂设备和苛刻时间约束下做出的技术决策。看这些案例的目的是学习他们的**分析思路、决策逻辑和权衡取舍**。

我们在前面各章节提到的技术手段——ADPF、Baseline Profiles、Game Mode API、Perfetto 分析——在本节都能看到它们在真实项目中的应用方式。这一节是前面章节技术的综合运用。

## 手机厂商的性能优化体系

手机厂商处于 Android 生态中一个独特位置：它们既控制着硬件（SoC、屏幕、散热结构），又深度定制着系统软件（Framework 层的调度策略、内核的 CPU governor、GPU 驱动参数）。这种"软硬一体"的控制力，使得厂商能够实现应用层无法触及的优化。

### Samsung：Game Booster 是用户入口，SceneSDK 才是私有调度接口

Samsung 公开一手资料能确认两条线。用户侧有 Game Booster，Samsung 支持页把它定义为在游戏运行时自动介入的功能，目标是在 battery usage、performance 和 temperature 之间做平衡。开发者协作侧有 SceneSDK，Samsung Galaxy GameDev 的文章明确写到，游戏可以把场景信息发给 SceneSDK，设备侧再按场景调整 CPU/GPU frequency，并在发生降频时回传通知。

这两条线要分开看。Game Booster 里的 Max Boost、Performance Priority 是用户可见的模式入口，公开资料没有展开 governor 参数、线程调度优先级、热阈值这些内部实现。SceneSDK 是 Samsung 私有的厂商协作接口，不是 Android 标准 API，不同 Galaxy 机型给不同游戏开放的策略也不一样。

把 Samsung 案例落到实战，比较稳的写法有三点：

- **用户侧可观察事实**：Game Booster 会在游戏启动后自动工作，用户可以在面板里切换更偏性能或更偏续航的模式
- **厂商私有能力**：SceneSDK 支持按 scene 调整 CPU/GPU 资源，并在系统发生 frequency reduction 时通知游戏
- **验证方法**：如果要判断某台 Galaxy 设备是否真的抬高了频率或缩短了频率响应，仍要看 Perfetto、频率 counter、热状态和帧时间，不能把 UI 上的“Max Boost”直接翻译成固定的底层机制

### Xiaomi：Game Turbo 更适合写成设备侧模式入口

Xiaomi 的 Game Turbo 是 HyperOS 里的游戏模式入口。公开能稳定确认的是用户侧能力：均衡模式、性能模式，以及免打扰、亮度锁定、手势限制这类配套开关。至于“主线程固定绑大核”“GPU governor 一定更激进”这类底层行为，仍会随着机型、SoC 和系统版本变化，不能直接写成跨设备结论。

因此，这一类案例保留两层信息就够了：

- **用户可见模式**：均衡模式偏续航和温控，性能模式偏帧率和响应
- **设备侧验证**：判断 HyperOS 某个版本是否真的改变了 CPU 迁移、频率投票，回到 Perfetto、频率 counter、migration 事件和帧时间分布

这样写既保留了 OEM 游戏模式的实用价值，也不会把设备观察误写成 Android 通用机制。

### OPPO/vivo：ADPF 的价值在于更早给系统负载信号

OPPO、vivo 这类案例更适合说明 ADPF 与厂商 thermal / power 栈的协作边界。公开标准 API 只有 `PerformanceHintManager`、Thermal Headroom 和 Game Mode。应用把 workload 信号提前交给系统后，具体怎么转换为 cluster placement、frequency vote 或 thermal policy，仍要经过厂商的 power HAL、perfservice 或调度栈。

因此，这里保留定性判断，不再写成通用时延数字。ADPF 的价值是让游戏把目标帧时间和实际工作时长更早交给系统，减少纯靠历史负载猜测的滞后。具体能快多少，取决于 SoC、governor、power HAL、thermal policy 和游戏引擎接入方式。

在设备上验证这件事，建议看四组信号：

- **FrameTimeline / 帧时间**：用户态工作负载变化后，帧时间是否更快收敛
- **CPU/GPU 频率 counter**：频率变化是提前发生，还是等掉帧之后才追上来
- **thermal status / thermal headroom**：系统是在主动留余量，还是已经进入被动降频
- **hint session 相关轨道或日志**：应用是否真的按帧上报了 target / actual duration

## 游戏性能优化：ADPF 与 Game Mode 的实战

游戏是 Android 设备上对性能要求最高的场景——持续高负载、对帧率极其敏感、发热与性能之间需要精细平衡。Google 从 Android 12 开始推出了整套游戏优化框架，包括 Game Mode API、Game State API 和 ADPF，本节我们通过具体的使用场景来看这些 API 怎么用。

### Game Mode API：让用户选择优化方向

Game Mode API 的作用是把“用户更想要性能还是续航”这件事传给游戏。公开游戏适配文档仍要求游戏至少处理 Standard、Performance、Battery Saver 三类选择。Android 14+ 平台 API 还存在 `GAME_MODE_CUSTOM`，用于 OEM 或系统提供自定义模式；面向 Android 13 及以下 targetSdk 的应用，平台可能把 custom mode 兼容返回为 standard。读取 `GameManager#getGameMode()` 时不要只写三个分支，默认分支要记录原始值，并回退到安全画质或帧率策略。

`Game Mode Interventions` 要和游戏自己实现的模式处理分开看。Android Developers 当前公开的干预项，主线是 `WindowManager` backbuffer resize 和 FPS throttling，文档还给出了 `downscaleFactor`、`allowGameDownscaling`、`allowGameFpsOverride` 这些配置与 opt-out 方式。公开文档没有提供“按包名调整线程调度策略”的标准接口或配置项。

正文里的边界按两层写：

- **标准能力**：`game_mode_config.xml`、`GameManager#getGameMode()`、backbuffer downscale、FPS throttling/override，以及对 `GAME_MODE_CUSTOM` 的安全回退
- **厂商私有能力**：线程调度、频率策略、驱动参数、Game Booster / Game Turbo 的设备定制逻辑

如果 OEM 在系统侧做了线程调度或 governor 调整，应单列为厂商私有策略，不写进 Game Mode Interventions 的公开能力清单。

### ADPF Thermal API：主动温控避免降频

温控是移动设备上最容易被忽视的性能因素。游戏前几分钟能稳定跑满 60fps，温度升高后触发 thermal throttling，帧率可能骤降到 30fps。稳定的 45fps 比先满帧再突然半帧更容易接受。

ADPF Thermal API 用于在温度接近阈值前逐步降低负载，避免设备进入被动降频。主要 API 是 `PowerManager.getThermalHeadroom(int forecastSeconds)`。它返回非负浮点值，表示当前工作负载持续 `forecastSeconds` 秒后的预测热余量；`1.0` 对应 `THERMAL_STATUS_SEVERE` 的预测阈值，不是取值上限。返回值可能大于 `1.0`。设备不支持预测、传感器数据不足，或调用频率过高时可能返回 `NaN`。接入代码要先处理 `NaN`，并把采样频率控制在秒级，避免把无效值写进降级策略。

降级阈值不能直接写死成 `0.5 / 0.7 / 0.85`。更稳的做法是读取 `getThermalHeadroomThresholds()` 中当前设备给出的状态阈值，或用同机型实测数据建立映射。策略可以按三档设计：

- **无效值或不支持**：保持现有画质策略，只记录 `NaN`、机型、系统版本和采样间隔，不触发激进降级
- **接近设备阈值**：逐步降低阴影、后处理、粒子等可回退负载，并观察帧时间是否收敛
- **超过 `SEVERE` 预测阈值**：优先降低渲染分辨率或目标帧率，把设备拉回可持续区间

在 Perfetto 里验证 Thermal API，至少同时看四组信号：thermal status / thermal headroom、CPU/GPU 频率 counter、FrameTimeline / 帧时间，以及应用侧的降级日志。只有 API 返回值、负载降级动作和帧时间变化能对上，才说明主动温控策略真的生效。

### ADPF Performance Hint API：帧级性能信号

Performance Hint API 让应用把周期性 workload 的目标耗时和实际耗时交给系统。传统 DVFS 依赖过去一段时间的平均负载做决策，`PerformanceHintManager` 则让游戏按线程组创建 `HintSession`，把目标帧时间和每轮实际工作时长直接上报。

一帧渲染完成后调用 `reportActualWorkDuration()` 上报实际耗时，用 `updateTargetWorkDuration()` 更新目标耗时（例如 `16.6ms@60fps`）。系统对比实际耗时与目标：实际耗时长期低于目标时降低资源供给；实际耗时接近或超过目标时提前提高供给，减少下一帧超时概率。

这套机制需要游戏引擎配合。Unity 引擎通过 ADPF 插件可以在每一帧渲染完成后调用这些 API；Unreal Engine 可以把可伸缩性设置与 ADPF 信号结合，按负载动态调整画质级别。

验证 Performance Hint 是否生效时，不要只看 API 调用是否成功。抓 Perfetto trace 时同时保留应用自定义 Trace 标记、CPU/GPU 频率、线程调度状态、thermal status / headroom；如果系统版本或厂商镜像暴露 `HintSession`、target duration、actual duration 相关 track，再把它们和频率变化、帧时间变化放到同一时间窗里检查。一个可发布的结论至少要说明：目标耗时如何设置、实际耗时何时超标、系统资源供给是否跟随变化，以及帧时间是否回到目标区间。

## 系统级启动速度优化：抖音的实践

启动速度是 Android 性能优化中讨论最多的主题之一，也是 App 开发者能直接控制的核心体验指标。字节跳动（抖音/TikTok）公开的启动优化实践覆盖了从任务治理到工具自研的完整链路，对大型 App 有参考价值。

### 从 300+ 启动任务到架构重构

抖音在启动优化的深水区面临的难点是：启动阶段有超过 300 个任务需要执行，传统的"任务调度 + 并行化"已经无法带来显著的提升。根本原因在于，300 个任务中大量是 SDK 初始化（配置任务）和预加载（预加载任务），它们的依赖关系错综复杂，简单增加并行度反而会因为锁竞争和 I/O 争用导致整体变慢。

抖音团队的解决思路是**三步走**：

第一步，**任务分类**。将 300+ 任务分为配置任务（SDK 初始化）、预加载任务（功能预热）和功能任务三类。这个分类本身就是一个工程决策——它强迫团队审视每个任务的必要性。

第二步，**配置任务原子化**。原来的模式是"初始化时主动调用 SDK 的 init 方法，传入 Context 和回调"。抖音将这个模式改为了 SPI（服务发现）模式——SDK 的初始化不再是启动时的显式调用，而是在第一次使用 SDK 功能时按需触发。对于无法修改源码的第三方 SDK，则通过中间层封装，在中间层接口被调用时才执行 SDK 初始化。

第三步，**预加载任务评估**。对每个预加载任务进行 A/B 实验，评估它的命中率和收益。结果是大量预加载任务被移除或延迟——因为统计发现很多预加载的内容在启动后的前 30 秒根本没有被用到。

这套方法论关注的是：**启动优化要先减少启动阶段需要执行的任务。** 这和我们在 8.3 节（启动优化）中讨论的"延迟初始化"原则完全一致，但抖音的工程规模让这个原则的应用变得极具挑战。

### ContentProvider 优化：字节码插桩的妙用

抖音在启动优化中发现过一个典型现象，ContentProvider 会发生隐式初始化。Android 在 App 启动时会自动实例化并调用所有注册的 ContentProvider 的 `onCreate()`，即使 App 在启动阶段不使用某个 ContentProvider，它的初始化开销也会被计入启动时间。

Google 自己的 Lifecycle 组件（`ProcessLifecycleOwnerInitializer`）和 FileProvider 就是典型的例子。单个 ContentProvider 的耗时可能只有几毫秒，但大型 App 可能注册了几十个 ContentProvider，累积起来就是几十毫秒甚至上百毫秒的开销。

抖音的做法是在编译期通过字节码插桩分析 FileProvider 的行为：具体来说，他们在 `FileProvider.attachInfo()` 中插桩，临时将 `grantUriPermissions` 设为 `false`，让 `getPathStrategy()` 的解析逻辑被跳过（因为 FileProvider 会检查这个标志并在为 false 时抛异常），然后在异常捕获后恢复原始值。这样 FileProvider 在启动阶段只执行了最轻量的初始化，真正的 XML 解析被延迟到第一次实际使用文件操作时才进行。

这种做法不修改业务代码，在构建流水线中自动完成，对开发者透明。对于 WorkManager 等其他有类似问题的库，也可以用同样的方式处理。

### 自研工具 Rhea：方法论价值高于产品细节

字节公开资料能确认的是一套方法论：通过自动化插桩把函数耗时、锁等待、I/O 和 Binder 信息放到统一分析面里，再做启动与页面场景的差异分析。对外资料没有完整公开 Rhea 的全部产品形态和内部插件边界，所以这类工具更适合写成“方法论案例”，不适合写成“已有完整开源平台”。

对外团队能带走的有三点：

- **自动插桩**：减少人工到处加 trace marker 的维护成本
- **统一事件面**：把函数、锁、I/O、Binder 放到同一条时间线里看
- **差异分析**：关注“这一次为什么比基线慢了多少、慢在哪个阶段”，而不只是导出一份 trace

如果只保留这些可验证结论，本章的案例链就成立了。至于 Rhea 的完整实现细节、线上采集开销和开源边界，应以字节后续公开材料为准。

## 大型 App 与厂商的协作优化

### TikTok × Google：完整证据链的示范

Google 在 2022 年发布了 TikTok Android 性能案例，三组结果是：启动时间下降 **45%**、UI smoothness 改善 **49%**、视频首帧速度提升 **41%**。同一篇文章还提到 active days per user 提升 **1%**。这些数字来自 Google 和 TikTok 联合发布的案例，适合当成单一应用、单一优化周期的公开结果，不能直接当作行业基线。

这个案例的参考价值在于它把“分析路径 → 工程动作 → 业务结果”接完整了：

- **启动路径**：按需加载组件、细化任务调度、把部分 View 初始化移到后台线程
- **界面流畅性**：精简首屏层级，只保留当前帧需要的内容，减少每帧任务量
- **视频首帧**：复用 player、做 preload / prerender，并联优化 codec 与 network path

这类官方案例最有用的地方，不在数字本身，而在证据链完整。能看到优化目标、主要动作和业务结果之间的对应关系。

### 厂商与应用的联合优化模式

在实际行业里，大型 App 和手机厂商的协作大体有三种形态：

- **模式一：标准 API 适配**。App 集成 ADPF、Game Mode 等公开接口。这条路通用性最好，跨设备成本最低。
- **模式二：设备侧定制配置**。厂商通过 game overlay、驱动白名单、per-app profile 或内部调度策略给头部应用做设备定制。这类能力通常不会完整公开，外部团队更适合把它当成设备差异来观察和验证。
- **模式三：联合调优**。厂商提供系统 trace、驱动或 thermal 观测能力，应用团队提供稳定复现场景和 workload 约束，双方一起缩小问题范围。

这三种形态可以同时存在。写案例时要把“公开 API”“设备配置”“合作调优”分层，不要把其中一层的能力外推成整条 Android 通用机制。

## 折叠屏与大屏设备的性能挑战

折叠屏设备在 2024-2025 年成为 Android 生态中增长最快的品类之一，Samsung Galaxy Z Fold 系列是其中的代表。折叠屏给性能优化带来两类独特挑战。

### 屏幕形态切换时的渲染开销

折叠屏设备的内屏和外屏通常有不同的分辨率、刷新率和宽高比。以 Galaxy Z Fold 7 为例，外屏是 21:9 比例，内屏是接近方形的宽屏比例。当用户展开或折叠设备时，系统需要处理配置变更（Configuration Change）、重建 Surface、重新分配 BufferQueue，并可能需要重新布局整个 UI。

这个过程在 Perfetto 中常会出现一串事件：Configuration Changed → Activity 重建 → Surface 分配 → 首帧渲染。如果 App 没有正确处理配置变更（比如在 `onConfigurationChanged()` 中做了大量同步工作），这个切换过程会导致明显的卡顿甚至黑屏。

Google 从 Android 12L 开始为大屏和折叠屏提供了一系列平台支持：改进的任务栏、增强的多窗口能力、可调整大小的应用窗口。开发者需要使用 Jetpack WindowManager 库来获取设备的折叠状态（通过 `FoldingFeature` API），并根据状态调整布局。

### 多窗口与分屏的性能压力

折叠屏的大屏天然适合多窗口模式——用户同时运行两个 App。但对系统来说，同时有两个 App 在竞争 CPU、GPU 和内存资源。特别是 GPU：两个 App 同时渲染意味着 SurfaceFlinger 需要合成的 Layer 数量翻倍，GPU 的工作负载也显著增加。

在高刷新率（120Hz）的大屏上同时运行两个 App，对系统性能的要求是普通场景的 2-3 倍。这要求厂商在调度策略上做更精细的分配——前台窗口获得更多的 GPU 时间片和更高的渲染优先级，后台窗口则降低帧率目标（从 120fps 降到 60fps 甚至更低）。

### 可变刷新率（VRR）对帧率的影响

Samsung 的折叠屏设备支持 LTPO 技术的 VRR，刷新率可以在 1Hz-120Hz 之间动态调整。这在 2.2 节（帧率与刷新率）中我们已经讨论过其原理。在折叠屏上的特殊之处在于：内外屏可能支持不同的刷新率范围——内屏支持 1-120Hz，外屏可能只支持 60Hz 或 10-120Hz。

App 在屏幕切换时需要重新适配帧率策略。如果 App 使用了 Choreographer 的帧回调来驱动动画，需要确保在配置变更后重新注册回调，否则可能出现动画卡顿。

## 常见问题与误区

**误区一：厂商优化可以替代 App 自身的优化。** 厂商的 Game Booster、Game Turbo 等功能能提升性能，但它们解决的是系统层面的调度和资源分配问题。如果 App 自身存在主线程 I/O、过度绘制、内存抖动等问题，厂商优化无法直接消除这些瓶颈。两者的关系是互补而非替代。

**误区二：ADPF 只适用于游戏。** ADPF 的 Thermal API 和 Performance Hint API 虽然最初为游戏场景设计，但它们对任何性能密集型应用都有效——视频编辑、图片处理、AR/VR 应用等。Google 官方文档也明确指出这些 API "可用于其他性能密集型应用"。

**误区三：行业案例可以直接照搬。** 每个案例背后都有特定的条件：App 的规模、用户群、技术栈、团队能力。抖音的 300+ 启动任务重构方案适用于大型 App，但对于一个只有 30 个启动任务的中型 App 来说，投入产出比完全不同。学习案例的重点是**方法论和思路**，而不是具体的实现方案。

**误区四：折叠屏优化只是 UI 适配。** 折叠屏的性能优化不只是让布局在大屏上好看——它涉及 Surface 管理、GPU 资源分配、多窗口调度、VRR 适配等一系列底层问题。如果只做 UI 适配而忽视这些底层因素，用户体验仍然会出问题。

**误区五：性能优化的回报只在技术层面。** TikTok 案例表明性能优化直接关联用户活跃度和留存率——1% 的活跃天数提升在数亿用户规模下意味着可观的商业价值。把优化投入转化为业务语言（留存、DAU、ARPU），有助于技术团队争取资源。

## 与其他章节的关系

本节案例涉及全书多个章节的技术内容：

- **5.4 DVFS / 5.6 Android 功耗管理**：OEM 游戏模式经常围绕 CPU/GPU 频率、功耗预算和热策略做差异化实现
- **5.3 big.LITTLE**：关键线程是否迁移、迁到哪一组核心，常常决定游戏场景的帧时间波动
- **2.2 帧率与刷新率**：折叠屏的 VRR 技术和多窗口帧率适配
- **2.10 GPU 渲染深入**：Game Mode Interventions 中 GPU 负载降低的具体实现
- **7.4 典型场景分析 / 7.5 优化策略**：抖音的启动优化案例是这些章节方法论的大规模实践
- **8.2 应用启动 / 8.3 启动优化**：TikTok 和抖音的启动优化直接应用了这些章节讨论的技术
- **11.1 功耗模型**：ADPF Thermal API 的温控策略是功耗与性能权衡的典型体现

## 参考资料

### 官方文档与官方案例

- Android Game Mode API and interventions: https://developer.android.com/games/optimize/adpf/gamemode/about-API-and-interventions
- Game Mode interventions: https://developer.android.com/games/optimize/adpf/gamemode/gamemode-interventions
- FPS throttling: https://developer.android.com/games/optimize/adpf/gamemode/fps-throttling
- ADPF 官方指南: https://developer.android.com/topic/performance/adpf
- Samsung Support, Know more about the Game Booster app: https://www.samsung.com/levant/support/apps-services/know-more-about-the-game-booster-app/
- Samsung Developer, Accelerate game performance based on SceneSDK: https://developer.samsung.com/galaxy-gamedev/blog/en/2022/04/26/accelerate-game-performance-based-on-scenesdk
- Android Developers Blog, Precise improvements, how TikTok enhanced its social experience on Android: https://android-developers.googleblog.com/2022/08/precise-improvements-how-tiktok-enhanced-its-social-experience-on-android.html
- Jetpack WindowManager: https://developer.android.com/jetpack/androidx/releases/window

### 归档材料与技术分享

- 字节跳动技术团队：抖音 Android 性能优化系列（启动优化实践）: `Cubox/抖音 Android 性能优化系列：启动优化实践 - 掘金-2024-01-15.md`
- 字节跳动技术团队：抖音 Android 性能优化系列（Rhea 性能分析工具）: `Cubox/抖音 Android 性能优化系列：新一代全能型性能分析工具 Rhea-2022-01-13.md`

### AOSP 源码路径

- GameManagerService: `frameworks/base/services/core/java/com/android/server/app/GameManagerService.java`
- GameManager: `frameworks/base/core/java/android/app/GameManager.java`
- PerformanceHintManager: `frameworks/base/core/java/android/os/PerformanceHintManager.java`
- PowerManager (Thermal API): `frameworks/base/core/java/android/os/PowerManager.java`

### 开源项目

- ByteDance BoostMultiDex: https://github.com/bytedance/BoostMultiDex
