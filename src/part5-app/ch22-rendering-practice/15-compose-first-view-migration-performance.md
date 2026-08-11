---
title: "Compose First 与 View/Compose 混合迁移性能边界"
chapter: "22.15"
status: finalized
drafted_date: "2026-05-21"
applicable_versions: "Jetpack Compose 1.9 - 1.10 / Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-21"
last_verified_against: "Android Developers Compose First docs/blog, Compose performance docs, Compose Foundation 1.9/1.10 发布说明, local DeepResearch 2026-05-15/18"
confidence: medium
tags: [compose, view-interop, rendering, migration, performance]
related_chapters: ["7.7", "22.2", "22.3", "18.2", "14.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "每日信息/官方文档/研究素材"
gap_score: 18
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-21"
task6_result: pass-light-edit
task9_state: reviewed
last_task6_at: "2026-05-21T19:07:00+08:00"
last_task6_review_log: "logs/review/2026-05-21-19-review.md"
task6_l1_l2_fixes: 12
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-21 Task6：四层质检通过；L1/L2 轻量修复 12 处；无 L3/L4 回炉项，送 Task9 技术复审。"
sources:
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/android-ui-development-is-compose-first.html"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/first"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/migrate/interoperability-apis"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/baseline-profiles"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/compose-foundation"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-15-compose-pausable-composition-lazy-layout-cache-window.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-18-android-17-compose-pausable-composition-tooling-verification.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
task9_reviewed_date: 2026-05-21
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-21T19:35:29+08:00"
last_task9_review_log: "logs/deep-review/2026-05-21-19-deep-review.md"
task9_result: pass-tech-review
task9_review_notes: "2026-05-21 task9 deep-review: 无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: 2026-06-29
last_task6_audit: 2026-06-15
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
---

# 22.15 Compose First 与 View/Compose 混合迁移性能边界

Google 在 2026 年明确采用 Compose First：新的 Android UI 库、示例、文档、培训和工具以 Compose 为设计起点。这是一项增量策略，存量 View 代码仍受支持。团队可以据此制定两条规则：新 UI 默认评估 Compose；存量页面在功能改造、视觉重做或状态模型调整时评估迁移，不安排缺少业务收益的全量重写。[Android Developers：Compose First](https://developer.android.com/develop/ui/compose/first)｜[Android Developers Blog](https://developer.android.com/blog/posts/android-ui-development-is-compose-first)

版本线分为平台、Jetpack 和内核三层：

| 层级 | 锚点 | 能回答的问题 |
|---|---|---|
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | `Choreographer`、`ViewRootImpl`、HWUI、BLAST、SurfaceFlinger 如何调度和显示宿主窗口 |
| Jetpack Compose | BOM `2026.06.01`，Runtime/UI/Foundation `1.11.4`；`1.12.0-beta02` 只作预览观察 | Composition、Layout、Draw、Lazy 预取、runtime tracing 和互操作 API 的当前行为 |
| Android common kernel | `android17-6.18-2026-06_r6` | 线程调度、CPU 频率以及 dma-fence 等系统现象 |

Compose 独立于 Android 平台发布。`android-17.0.0_r1` 不能证明某个 Compose Runtime 或 Foundation 特性已经启用；BOM 也不能证明设备上的 SurfaceFlinger 或内核实现。RecyclerView 复用、Compose 应用优化和显示管线的详细背景分别见 [22.2 RecyclerView 性能优化实战](02-recyclerview-practice.md)、[22.3 Jetpack Compose 性能优化](03-compose-performance.md)、[18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md) 与 [18.2 Android View 标准管线](../../part2-performance/ch18-rendering-pipelines/02-android-view-standard.md)。

## Compose First 改变新增 UI 能力入口

Compose First 把新增 UI 能力的主入口移到 Compose。Google 公告覆盖 API、库、工具、指南、codelab 和示例；新的 Android Studio UI 工具也以 Compose 为目标。它没有取消 View API，也没有要求稳定页面立刻迁移。[Android Developers：Compose First](https://developer.android.com/develop/ui/compose/first)

新增页面优先 Compose 的收益主要来自三个方面：

- **入口一致**：状态、预览、Material 组件和自适应布局从同一套 Compose 文档与 API 出发，新增页面无需同时维护 XML 与 Compose 两套实现。
- **工具持续更新**：Layout Inspector、compiler reports、composition tracing 和 Compose 测试 API 仍在扩展，新增诊断能力会优先覆盖 Compose。
- **新形态适配较早进入设计**：大屏、折叠屏、桌面窗口化与多尺寸布局直接进入新页面的布局决策。

存量页面需要按收益与风险排序。官方建议在页面被业务需求触及时迁移。页面发生大改、视觉重做、状态模型重构或适配新形态时，可把 Compose 迁移纳入同一轮测试；产品形态稳定、线上性能达标、又依赖复杂 View SDK 的页面保留 View 往往更稳妥。

“新页面默认 Compose”仍允许例外。相机预览、地图、广告、WebView、视频播放器以及厂商 SDK 可能只提供 View 或 Surface 接口。团队应记录例外依赖、替换条件和测试门槛，避免把临时互操作层长期留成无人负责的架构边界。

## View 维护模式与存量页面边界

Compose First 不等于 View 已废弃。官方将 `android.widget` View toolkit 标为 maintenance mode，只接收高优先级修复；`android.view` 继续负责窗口、输入与绘制等基础职责。Fragment、RecyclerView、ViewPager2、ConstraintLayout 和 Data Binding 等 View-based Jetpack 库被列为 complete 或 maintenance mode，存量项目仍可使用，新特性投入会集中到 Compose。[Android Developers：View 与 View-based 库的支持边界](https://developer.android.com/develop/ui/compose/first)

这个边界会影响技术规划：

| 对象 | 官方状态 | 工程判断 |
|---|---|---|
| `android.view` | 继续作为 UI toolkit 底层支撑 | 不能按废弃处理，输入、窗口、绘制和生命周期仍绕不开它 |
| `android.widget` | maintenance mode | 新页面少用，遗留页面可继续维护，重大改版时评估 Compose |
| Fragment / RecyclerView / ViewPager 等 View-based libraries | complete / maintenance mode | 存量可用；新能力、适配和工具增量不要押在这些库上 |
| Compose interop APIs | 持续支持 | 用作渐进迁移桥梁；长期保留时要指定生命周期、状态归属和性能负责人 |

维护模式不会让现有页面突然失效。它改变的是未来投入方向：新的组件能力、示例和 UI 诊断工具不会优先覆盖 View。保留 View 页面时，评审记录应写明遗留依赖、迁移收益、测试覆盖和现有性能数据。只写“以后再迁”无法支撑后续决策。

## View/Compose interop 的性能成本

`ComposeView` 把 Compose 子树放进 View 层级，`AndroidView` 把 View 放进 Compose 层级。两种 API 都受官方支持，成本集中在生命周期、测量、状态和资源所有权边界。[Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)｜[Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)

常见成本可以按四类看：

- **生命周期桥接**：`ViewCompositionStrategy.Default` 当前对应 `DisposeOnDetachedFromWindowOrReleasedFromPool`。普通容器在 detach 时释放 Composition；RecyclerView 等 pooling container 会等到容器 detach，或 item 被丢弃、复用池已满时释放。Fragment 的 View 应使用 `DisposeOnViewTreeLifecycleDestroyed`，让 Composition 跟随 Fragment view lifecycle，而非 Fragment 实例生命周期。
- **测量与布局边界**：View 的 `measure/layout/draw` 与 Compose 的 Composition/Layout/Draw 不是同一个阶段模型。一个 `ComposeView` 进入复杂 ViewGroup 后，尺寸约束、重新测量和 invalidation 传播要跨边界转换；`AndroidView` 包装旧 View 时也会把 View 的测量规则带进 Compose。
- **状态同步**：ViewModel、SavedState、Fragment arguments、View binding、Compose state 和 snapshot 需要收敛到一个数据源。双向同步越多，重复更新和无效重组越难排查。
- **两套树结构**：混合页面同时存在 View tree、Semantics tree、slot table 和旧组件内部状态。滚动、动画、焦点、输入法与无障碍问题可能跨越多套结构。

同一个布局中存在多个 `ComposeView` 时，每个实例都要有唯一 ID，SavedState 才能区分对应状态。Fragment 场景还要在 `onDestroyView()` 清理 View binding 和 View 引用，避免把 Composition 的正确释放误当成整条引用链都已释放。

`AndroidView` 适合包裹尚无 Compose 替代的 SDK 组件，或迁移周期内必须保留的自定义 View。在 Lazy 列表里，需要选择带 `onReset` 的重载并传入非空回调，才会启用兼容项之间的 View 复用；`onRelease` 负责最终释放不再复用的资源。`onReset` 应清除前一项留下的监听、选中状态、动画与临时数据，不能只清空文本。[Views in Compose：Lazy list reuse](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)

Fragment 也应视为迁移桥梁。官方当前建议 Compose-only 应用采用单 Activity 与最新 Compose navigation 方案；已有 Fragment 架构无需为遵守口号而重写导航。迁移顺序宜先收敛页面状态，再替换内容区域，待导航与生命周期测试齐备后评估是否移除 Fragment。

### 互操作不会自动增加 Surface

普通 `ComposeView` 不会自动创建独立 Surface。Compose 在应用侧执行 Composition、Layout 和 Drawing，绘制结果由宿主 `ViewRootImpl` 与 HWUI 进入同一个 App Window buffer。普通 `AndroidView` 也留在该宿主窗口的 HWUI 路径中。两者的框架入口不同，宿主窗口以下仍沿 RenderThread → BLAST / BufferQueue → SurfaceFlinger → HWC / RenderEngine → present 前进。

输出拓扑由被包装组件的 producer 与 Surface 类型决定：

| 互操作对象 | 常见输出拓扑 | 排查重点 |
|---|---|---|
| 普通 TextView、自定义 Canvas View | 与 Compose 共用 App Window | 主线程 composition/layout、View measure/layout、RenderThread |
| `SurfaceView`、相机预览、部分播放器或地图 SDK | 宿主窗口之外增加独立 SurfaceFlinger layer | 独立 BufferQueue、transaction、acquire fence、layer latch 与 present |
| `TextureView` | 外部 producer 写入 SurfaceTexture，再由宿主 HWUI 采样进 App Window | producer queue、纹理更新、宿主窗口 draw 与 GPU 采样 |
| `WebView` 或厂商复杂 SDK | 依实现可能包含额外 Surface、进程或 GPU producer | 先查 layer 树和 producer，再选分析模型 |

因此，“页面用了 Compose”不能直接说明 layer 数量、buffer 数量或合成类型。含相机、视频、地图和 WebView 的页面应先用 SurfaceFlinger layer、Perfetto 和 producer 线程确认拓扑，之后再判断卡顿位于 Compose、旧 View、独立 buffer producer 还是系统合成。混合管线的证据方法见 [18.4 Android View 混合渲染](../../part2-performance/ch18-rendering-pipelines/04-android-view-mixed.md)、[18.6 SurfaceView](../../part2-performance/ch18-rendering-pipelines/06-surfaceview.md) 与 [18.7 TextureView](../../part2-performance/ch18-rendering-pipelines/07-textureview.md)。

## 迁移顺序与风险分层

迁移顺序由改动收益和性能风险共同决定。每个候选页面先保存可重复的基线，再选择替换整页、替换局部区域或暂缓迁移。

| 页面类型 | 建议策略 | 验证门槛 |
|---|---|---|
| 新页面 / 新弹窗 / 新设置项 | 直接使用 Compose | 常规单元测试、截图测试、基本帧耗时检查 |
| 低频设置页 / 个人资料页 | 小批量迁移，优先清理 XML 和 Binding 技术债 | 冷启动不劣化；页面首帧和内存峰值不劣化 |
| 高频信息流 / 长列表 item | 先选一类 item 迁移，保留稳定 key 和复用策略 | Macrobenchmark 滚动测试、FrameTimeline、重组次数、GC 暂停 |
| 动画密集页 / 手势强交互页 | 先做端到端原型，控制 `ComposeView` / `AndroidView` 边界数量 | 目标刷新率下的帧 deadline、输入延迟、动画 jank |
| 大屏 / 折叠屏 / 多窗口页面 | 新布局优先 Compose，旧组件逐步剥离 | 多尺寸截图、窗口 resize trace、状态恢复 |
| 依赖 WebView、Map、Ad、播放器的页面 | 用 `AndroidView` 包装缺口组件，外围状态和布局先 Compose 化 | 生命周期释放、可见性切换、内存回收、后台恢复 |

性能敏感路径迁移前至少保存三组基线：用户路径耗时、帧 deadline 结果、内存与 GC 数据。测试应固定设备、系统 build、thermal 状态、刷新率、账号数据和滚动输入。缺少这些条件时，“体感更顺”无法转成可复核结论，回退也难以区分 Compose、互操作、状态模型和业务分配。

建议把迁移拆成可回退的几个小批次：

1. 固定业务状态与数据源，记录旧页面 benchmark、trace 和截图。
2. 迁移一个边界清楚的区域，保持导航、数据请求和业务规则不变。
3. 检查生命周期、SavedState、焦点、输入法、无障碍和返回行为。
4. 在同一测试条件下比较 FrameTimeline、启动或跳转耗时、分配与内存。
5. 指标通过后再扩大范围，并删除已失去用途的桥接状态与监听器。

每批改动只改变一类变量。若同时重写状态层、导航、列表和动画，即使指标变化也很难定位原因。

## Lazy 列表、Pausable Composition 与版本边界

长列表的风险集中在 item composition、measure、状态读取、对象分配和预取。RecyclerView 与 LazyColumn 的缓存模型不同，迁移验收不能只比较同屏 item 数量，也不能用“新版已经修复列表性能”替代实测。

截至 2026-07-29，Compose Foundation 当前稳定版为 `1.11.4`，`1.12.0-beta02` 属于预览版。下表只记录发布说明能直接支持的边界：[Compose Foundation release notes](https://developer.android.com/jetpack/androidx/releases/compose-foundation)

| 能力 | 版本边界 | 迁移判断 |
|---|---|---|
| `LazyLayoutCacheWindow` | Foundation 1.9.0 增加 `LazyGridState` 与对应 `remember` 重载；1.9.1 修复相关崩溃 | 它提供缓存窗口配置入口，不保证某一组数值适合所有 item；按滚动方向、item 复杂度、内存与命中率测试 |
| lazy prefetch 中的 Pausable Composition | 1.10.0-alpha05 曾默认开启；1.10.6 因稳定性问题把 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` 设为默认关闭 | 1.11.4 的发布说明没有给出可据此宣称“已重新默认开启”的条目；使用前核对精确 artifact、源码 flag 与运行时配置 |

Pausable Composition 允许预取组合工作在调度点暂停，把剩余工作留给后续时机。它不负责消除重复状态读取、错误 key、频繁分配或昂贵 measure。列表仍要检查稳定 key、content type、状态读取范围、派生状态、图片请求和 item 内 `AndroidView` 的复用。

Strong Skipping 从 Kotlin `2.0.20` 起默认启用。restartable composable 可被标记为 skippable；不稳定参数使用实例相等性判断，稳定参数使用对象相等性判断，composable 内的 lambda 也会自动记忆。`@NonSkippableComposable` 用于明确退出跳过，`@DontMemoize` 用于明确退出 lambda 自动记忆。它提高跳过机会，但不会替开发者修复可变对象内部变化未被 snapshot 观察的问题。[Strong Skipping 官方说明](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)

## 观测工具与验收指标

迁移验收分成开发期定位与发布前门禁。重组计数适合发现异常，不能单独判定页面是否流畅；发布门禁需要可重复的 benchmark 与系统 trace。

| 工具 | 主要用途 | 适合回答的问题 |
|---|---|---|
| Layout Inspector | 查看 Composable 重组次数、跳过次数和树结构 | 哪个组件重复重组；计数是否与预期状态变化相符 |
| Compose compiler reports | 静态输出 skippable、restartable 和稳定性推断 | 哪些函数或参数影响跳过；它不提供运行时耗时 |
| Macrobenchmark | 重复执行启动、滚动、页面跳转路径 | 迁移前后冷启动、首帧、滚动帧耗时是否回退 |
| Baseline Profile | 让 ART 提前编译关键路径 | Compose runtime 之外，业务热点路径是否被覆盖 |
| Android Studio Profiler / System Trace | 采集 Perfetto 系统轨道；配合 composition tracing 展开 composable | 超期发生在 composition、layout、draw、GC、RenderThread 或系统等待 |
| Perfetto / FrameTimeline | 对齐 App SurfaceFrame、SF DisplayFrame、目标 layer 与 present | 应用是否按 expected deadline 交帧，目标 buffer 是否按期显示 |
| Android Performance Analyzer | 在 open beta 工具中联合查看 CPU、GPU、内存、功耗和 SurfaceFlinger | 适合作为跨子系统调查入口；不宜作为唯一 CI 门禁，详见 [14.17](../../part3-tools/ch14-other-tools/17-android-performance-analyzer.md) |

[Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing) 需要引入 `runtime-tracing`；自定义 Perfetto 配置还要启用 `track_event` data source。采集应使用 profileable、non-debuggable build，因为 debug 构建的解释、检查与调试开销会污染耗时。生产包是否保留 tracing strings 需要按 APK 体积与现场诊断需求决定。

Baseline Profile 文档给出的“约 30%”是对被 profile 覆盖代码路径的概括性收益，不是页面 SLA。Compose 随库提供的 profile 只覆盖 Compose 库代码；业务导航、数据绑定、图片和自定义组件仍需用 Macrobenchmark 生成并验证应用 profile。[Baseline Profiles for Compose](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)

一张可执行的验收表至少包含这些字段：

| 指标 | 建议采集方式 | 判定方式 |
|---|---|---|
| 冷启动 / 热启动耗时 | Macrobenchmark `StartupTimingMetric` | P50 / P90 / P95 不劣化；收益要给出设备和迭代次数 |
| 页面首帧 | Macrobenchmark + FrameTimeline | 目标页面首帧不晚于迁移前基线 |
| 滚动帧表现 | Macrobenchmark scroll + FrameTimingMetric + Perfetto | 按 FrameTimeline expected deadline 和刷新率分桶，比较超期帧分布，不把 16.6 ms 当作所有设备的固定预算 |
| 重组次数 / 跳过次数 | Layout Inspector + compiler reports | 高频组件重组次数有对应状态事件；跳过变化能追到参数稳定性 |
| GC 暂停和分配 | Android Studio Profiler / Perfetto / ART counters | 滑动阶段无持续分配尖峰；GC pause 不集中压到交互窗口 |
| 内存峰值 | Profiler / dumpsys meminfo / Perfetto | 混合层不会长期持有 Fragment view、Context 或旧 View 缓存 |
| 线上帧指标 | APM / FrameMetrics / statsd | 灰度期间与老页面分桶对比，按设备档位拆开看 |

FrameTimeline 的 App `SurfaceFrame` 和 SurfaceFlinger `DisplayFrame` 回答不同问题。App actual 超过 expected deadline 说明应用侧交帧未按预算完成；它不能独立证明目标 layer 已错过 present。涉及独立 `SurfaceView` 或视频 layer 时，还要核对该 layer 的 latch、fence 与 display timeline。[Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)

截至 2026-07-29，[Android Performance Analyzer](https://developer.android.com/android-performance-analyzer) 仍为 open beta。它可以辅助关联 CPU、GPU、内存、功耗和 SurfaceFlinger 信息，GPU counters 也可能因设备能力而缺失。稳定验收仍应保存 Macrobenchmark 输出、Perfetto trace、构建版本和测试条件。[Android Studio jank detection](https://developer.android.com/studio/profile/jank-detection)

## XML to Compose migration skill 的适用范围

Google 维护的 [Android agent skills 仓库](https://github.com/android/skills) 提供 [Migrate XML Views to Jetpack Compose](https://github.com/android/skills/blob/main/jetpack-compose/migration/migrate-xml-views-to-jetpack-compose/SKILL.md)。该 skill 的范围是一份旧 XML layout 到 Compose UI 的迁移，流程覆盖基线截图、依赖与 compiler 配置、主题、布局替换、验证和清理。

它只处理 UI 迁移流程，不能证明业务状态、导航、生命周期和性能已经正确。生成结果仍需人工核对：

- state owner 与事件方向是否唯一；
- semantics、无障碍、焦点和输入法行为是否保留；
- 自定义 attribute、theme、dimension 与 RTL 是否等价；
- View 或 Surface 资源是否在正确生命周期释放；
- screenshot/UI test、Macrobenchmark 和 trace 是否覆盖目标路径。

XML 结构转换成功只说明页面进入可验证阶段，不能直接视为发布完成。

## Compose Multiplatform 与 Android App 迁移的差异

Compose First 面向 Android UI 开发路线；Compose Multiplatform 是跨平台 UI 选型。Android 应用内部迁移关注 Android 上的启动、渲染、输入、内存、无障碍和工具链。跨平台项目还要评估 iOS、桌面或 Web target 的 API 缺口、组件差异、二进制体积、平台集成与发布流程。

两类决策应使用不同的验收表。Android Compose 页面运行良好，无法推出同一 UI 在其他 target 具有相同的文本、输入、滚动和性能表现；某个跨平台 target 的限制也不应阻止 Android 页面采用成熟的原生 Compose API。

## Compose 1.10+ 发布说明跟踪

Compose 的版本更新快于 Android 平台。引用“默认启用”“性能相当”或“卡顿率下降”时，应同时记录：

- Compose BOM、Runtime、UI、Foundation 和 Kotlin 版本；
- AGP、Android Studio 与 benchmark library 版本；
- 设备、Android build、刷新率、thermal 状态和数据规模；
- 测试路径、迭代次数、percentile 与回归阈值；
- feature flag 的编译期和运行时值。

2026-07-29 核对到 Foundation `1.11.4` 稳定版与 `1.12.0-beta02` 预览版。后续若发布说明明确更改 Pausable Composition 的默认状态，需要同时更新 [22.3 Compose 性能](03-compose-performance.md)、[22.33 PausableComposition](33-compose-pausable-composition-performance.md) 与这里的版本边界，不能根据预览版或一次本地结果推断稳定版行为。

## Android 17 源码核对入口

下列文件用于核对宿主窗口以下的公共显示路径。Compose 的 Composition 和 Lazy 实现应回到对应 AndroidX artifact 源码与发布说明，不能从这些 AOSP 文件推导。

- [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java) 与 [`ThreadedRenderer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ThreadedRenderer.java)：应用 traversal、HWUI 绘制入口和宿主 App Window。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)：RenderThread 帧任务与同步边界。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)：窗口 buffer transaction、回调与 FrameTimeline 信息传递。
- [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)：App SurfaceFrame、SF DisplayFrame 与 jank 分类。
- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c) 与 [`drivers/dma-buf/dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)：线程未获运行时间与 fence 等待的内核观察边界。

完成一批迁移后，评审结论至少要回答四个问题：状态所有权是否清楚，互操作资源是否按生命周期释放，目标用户路径是否通过同条件 benchmark，FrameTimeline 与 layer 证据是否支持归因。四项都能复核，迁移才适合扩大范围。
