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
related_chapters: ["7.7", "22.2", "22.3", "18.2", "14.18"]
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

<!-- outline-start -->
## 要点

### 🔹 Compose First 改变新增 UI 能力入口
说明 Google 2026 年将 Android UI 指南、工具、API 和示例转向 Compose 的背景，并把它转成工程判断：新增功能优先 Compose，老页面按触碰频率和性能风险分批迁移。

### 🔹 View 维护模式与存量页面边界
区分 android.widget、Fragment、RecyclerView、ViewPager 等 View-based 组件的维护状态、继续可用范围和不再承接新特性的影响，避免把“维护模式”误读成“立即废弃”。

### 🔹 View/Compose interop 的性能成本
梳理 `ComposeView`、`AndroidView`、Fragment 容器、RecyclerView item 中嵌入 Compose 的常见成本：生命周期桥接、measure/layout 重复、状态同步、slot table 与 View tree 双重管理。

### 🔹 迁移顺序与风险分层
给出页面迁移排序：新页面、低频设置页、长列表 item、动画密集页、大屏/窗口化页面分别采用不同验证门槛，性能敏感路径先做 Macrobenchmark 和线上指标基线。

### 🔹 Lazy 列表、Pausable Composition 与版本边界
结合 Compose Foundation 1.9/1.10 的 LazyLayoutCacheWindow、Pausable Composition、runtime tracing，说明长列表迁移时要看具体 Compose 版本和默认开关，不把 alpha 能力写成稳定默认能力。

### 🔹 观测工具与验收指标
说明 Compose Profiler、Perfetto、Android Performance Analyzer、Macrobenchmark、Baseline Profile 的分工，建立启动耗时、帧耗时、重组次数、跳过次数、GC 暂停和内存峰值的验收表。

## 扩展

### 🔸 XML to Compose migration skill 的适用范围
记录官方迁移 skill 适合做布局草案转换，最终仍需人工确认状态提升、语义、可访问性和性能数据。

### 🔸 Compose Multiplatform 与 Android App 迁移的差异
区分跨平台 UI 选型和 Android 原生页面迁移，避免把 Compose Multiplatform 的限制直接套到 Android App 页面上。

### 🔸 Compose 1.10+ 发布说明跟踪
后续补充 Pausable Composition、Lazy prefetch、Modifier 优化和 runtime tracing 的稳定版本边界。

<!-- outline-end -->

Google 在 2026 年将 Android UI 指南、示例、工具和新增 API 的重心全面转向 Compose，官方把这个方向称为 Compose First。对团队来说，这条产品路线要转成可执行的工程规则：新增 UI 默认选 Compose；存量 View 页面按触碰频率、性能敏感度和维护成本分批处理——不要一上来就计划全量重写。[已验证: Android Developers Blog, 2026-05-21][已验证: 官方文档, developer.android.com/develop/ui/compose/first]

这类迁移不能只看“能不能改成 Compose”。View 管线、RecyclerView 实战和 Compose 性能细节在 22.2、22.3 和 18.2 节已经展开过。本节只聚焦混合迁移阶段的取舍：什么时候插入 `ComposeView`，什么时候用 `AndroidView` 保留遗留组件，什么时候必须先补性能基线——这些判断比“能不能改”更影响上线质量。

## Compose First 改变新增 UI 能力入口

Compose First 的工程含义是“新增能力优先从 Compose 入口接入”。Google 公告给出的范围包括 API、库、工具、指南、文档、codelab 和示例；Android Studio 后续新增 UI 工具也会面向 Compose。对业务团队来说，新增页面、重做页面和新形态适配应该先评估 Compose 方案，再回看是否存在必须保留 View 的技术债。[已验证: Android Developers Blog, 2026-05-21]

新增页面优先 Compose 的收益主要来自三个方面：

- **开发入口统一**：UI 状态、预览、Material 组件和自适应布局都从 Compose 文档开始，团队不再为新页面同时维护 XML、Binding 和 Compose 三套写法。
- **工具投入集中**：Compose Profiler、Layout Inspector 重组计数、compiler metrics、runtime tracing、Baseline Profile 指南都围绕 Compose 补齐，性能问题更容易形成统一排查模板。
- **跨形态成本更低**：大屏、折叠屏、窗口化和多尺寸布局在 Compose 指南中被放到更前的位置，新增页面能较早暴露尺寸适配问题。

存量页面的规则要更保守。公告建议在“触碰到页面时再迁移”（when you touch them），这句话适合转成版本计划：页面发生大改、视觉重做、状态模型重构或性能专项时，把 Compose 迁移纳入同一批验证；没有产品变化、线上指标稳定、依赖复杂 View 组件的页面继续保留 View。[已验证: 官方文档, developer.android.com/develop/ui/compose/first]

## View 维护模式与存量页面边界

Compose First 不等于 View 立刻废弃。官方明确 `android.widget` 这类 View toolkit 进入 maintenance mode，仍会获得高优先级修复；`android.view` 仍是 Compose 和其他 UI toolkit 的底层支撑。Fragment、RecyclerView、ViewPager、ConstraintLayout、Databinding 等 View-based Jetpack libraries 也进入维护状态，后续不再承接显著新能力。[已验证: 官方文档, developer.android.com/develop/ui/compose/first]

这个边界会影响技术规划：

| 对象 | 官方状态 | 工程判断 |
|---|---|---|
| `android.view` | 继续作为 UI toolkit 底层支撑 | 不能按废弃处理，输入、窗口、绘制和生命周期仍绕不开它 |
| `android.widget` | maintenance mode | 新页面少用，遗留页面可继续维护，重大改版时评估 Compose |
| Fragment / RecyclerView / ViewPager 等 View-based libraries | complete / maintenance mode | 存量可用；新能力、适配和工具增量不要押在这些库上 |
| Compose interop APIs | 官方继续支持 | 作为渐进迁移桥梁使用，不能把混合层长期当成最终架构 |

维护模式的风险不是“明天不能用”，而是“新工具、新示例、新 API 入口不会优先服务 View”。当团队把一个页面继续留在 View 上，需要记录这个选择对应的原因：遗留组件依赖、短期稳定性、迁移成本、测试覆盖不足，或现有性能数据已经满足目标。

## View/Compose interop 的性能成本

混合迁移阶段最容易低估 interop 成本。`ComposeView` 把 Compose 子树嵌进 View 层级，`AndroidView` 把 View 放进 Compose 树；两者都能工作，但都会多出一层生命周期、测量和状态同步边界。[已验证: 官方文档, developer.android.com/develop/ui/compose/migrate/interoperability-apis]

常见成本可以按四类看：

- **生命周期桥接**：`ComposeView` 需要明确 Composition 释放时机。官方文档说明 `ViewCompositionStrategy.Default` 会在底层 `ComposeView` detach 时释放 Composition，但在 RecyclerView 这类可复用容器（pooling container）中有特殊处理；Fragment 的 View 中更适合使用与 `ViewTreeLifecycleOwner` 绑定的策略，避免 Fragment view 销毁后 Composition 仍持有状态。[已验证: 官方文档, developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views]
- **测量与布局边界**：View 的 `measure/layout/draw` 与 Compose 的 Composition/Layout/Draw 不是同一个阶段模型。一个 `ComposeView` 进入复杂 ViewGroup 后，尺寸约束、重新测量和 invalidation 传播要跨边界转换；`AndroidView` 包装旧 View 时也会把 View 的测量规则带进 Compose。
- **状态同步**：ViewModel、SavedState、Fragment arguments、View binding、Compose state 和 snapshot 需要收敛到一个数据源。双向同步越多，重复更新和无效重组越难排查。
- **双重树管理**：混合页面同时存在 View tree、Semantics tree、slot table 和旧组件内部状态。问题发生在滚动、动画、焦点、输入法和无障碍场景时，定位成本会明显上升。

`AndroidView` 只适合包住仍缺 Compose 替代的 SDK 组件或短期无法重写的自定义 View。官方文档建议自定义 View 尽量迁移到 Compose；在 Lazy list 中使用 `AndroidView` 时，应使用带 `onReset` 的重载以启用 View 复用，并在 `onRelease` 中释放不再复用的资源。[已验证: 官方文档, developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose]

这条规则和 RecyclerView 复用思想一致，详见 22.2 节：长列表里每个 item 都新建 View 或 Compose 子树，会把绑定成本、布局成本和 GC 压力叠加到滑动阶段。混合列表要把复用、稳定 key、状态提升和对象分配一起验证。

## 迁移顺序与风险分层

迁移顺序应该从“改动收益”和“性能风险”一起排。参考《Android 性能优化》里按场景建立指标、再按 CPU、缓存、任务调度拆原因的组织方式，Compose 迁移也应该先建立页面基线，再决定改哪一类页面。| 页面类型 | 建议策略 | 验证门槛 |
|---|---|---|
| 新页面 / 新弹窗 / 新设置项 | 直接使用 Compose | 常规单元测试、截图测试、基本帧耗时检查 |
| 低频设置页 / 个人资料页 | 小批量迁移，优先清理 XML 和 Binding 技术债 | 冷启动不劣化；页面首帧和内存峰值不劣化 |
| 高频信息流 / 长列表 item | 先选一类 item 迁移，保留稳定 key 和复用策略 | Macrobenchmark 滚动测试、FrameTimeline、重组次数、GC 暂停 |
| 动画密集页 / 手势强交互页 | 不建议从局部 `ComposeView` 开始堆混合层 | 60/90/120 Hz 下帧耗时分布、输入延迟、动画 jank |
| 大屏 / 折叠屏 / 多窗口页面 | 新布局优先 Compose，旧组件逐步剥离 | 多尺寸截图、窗口 resize trace、状态恢复 |
| 依赖 WebView、Map、Ad、播放器的页面 | 用 `AndroidView` 包装缺口组件，外围状态和布局先 Compose 化 | 生命周期释放、可见性切换、内存回收、后台恢复 |

性能敏感路径迁移前要保存三组基线：用户路径耗时、帧耗时分布和内存/GC 数据。没有基线时，迁移后的“体感更顺”很难转成可复核结论；一旦出现回退，也很难判断是 Compose 本身、interop 边界、状态模型，还是业务代码分配造成的。

## Lazy 列表、Pausable Composition 与版本边界

长列表是 View/Compose 迁移里风险最高的区域。RecyclerView 的复用和预取模型在 22.2 节已经展开；Compose LazyColumn 的成本则集中在 item composition、measure、对象分配、状态读取和预取窗口配置。迁移时不能用“Compose 1.10 已经解决列表性能”这类笼统结论替代版本核对。

本地调研确认了两个版本边界：

| 能力 | 版本边界 | 迁移判断 |
|---|---|---|
| `LazyLayoutCacheWindow` | Compose Foundation 1.9.0 稳定化，支持 Dp 和 viewport fraction 两类窗口描述；具体参数类型要按所用版本发布说明核对 | 可以作为长列表预取调优入口，但要配合 item 复杂度和滚动基准测试 |
| Pausable Composition in lazy prefetch | 1.10.0-alpha05 曾默认启用；1.10.6 发布说明记录：因稳定性问题默认禁用 `ComposeFoundationFlags.isPausableCompositionInPrefetchEnabled` | 不能把 alpha 阶段默认行为写成稳定版默认能力；采用前必须核对 Foundation 版本和 flag 状态 |

[已验证: DeepResearch/2026-05-15-compose-pausable-composition-lazy-layout-cache-window.md][已验证: DeepResearch/2026-05-18-android-17-compose-pausable-composition-tooling-verification.md][已验证: 官方发布说明, developer.android.com/jetpack/androidx/releases/compose-foundation]

Pausable Composition 解决的是“单次组合工作阻塞当前帧”的问题，不会自动减少无效重组。无效重组仍要靠状态读取位置、稳定性、Strong Skipping、key 设计和派生状态控制。Strong Skipping 在 Kotlin 2.0.20 起默认启用，会让带 unstable 参数的 restartable Composable 也可跳过，并记住带 unstable captures 的 lambda；这能改变老项目里手写 `remember` lambda 的优先级。[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/stability/strongskipping]

## 观测工具与验收指标

迁移验收要拆成“开发期定位”和“发布前门禁”两层。Compose 页面只看单次 profiler 截图不够，必须让指标能重复跑。

| 工具 | 主要用途 | 适合回答的问题 |
|---|---|---|
| Layout Inspector / Compose Profiler | 查看 Composable 重组次数、跳过次数和耗时 | 哪个组件在频繁重组，是否存在明显无法跳过的情况 |
| Compose compiler metrics | 输出 skippable、restartable、稳定性推断结果 | 数据模型是否破坏跳过；哪些参数导致函数不可跳过 |
| Macrobenchmark | 重复执行启动、滚动、页面跳转路径 | 迁移前后冷启动、首帧、滚动帧耗时是否回退 |
| Baseline Profile | 让 ART 提前编译关键路径 | Compose runtime 之外，业务热点路径是否被覆盖 |
| Perfetto / FrameTimeline | 复核主线程、RenderThread、GC、SurfaceFlinger 时序 | 掉帧发生在 composition、layout、draw、GC 还是同步等待 |
| Android Performance Analyzer | 同屏分析 CPU、GPU、内存、功耗和系统事件 | 图形重负载页面迁移后，是否出现系统级相关性问题，详见 14.18 节 |

官方 Baseline Profile 文档给出的口径是：Baseline Profiles 通过避免解释执行和 JIT 编译，让包含路径的代码从首次启动起获得约 30% 的执行速度提升；Compose 库自带 profile 只覆盖 Compose 库代码，业务关键路径仍要通过 Macrobenchmark 生成并验证自定义 profile。[已验证: 官方文档, developer.android.com/develop/ui/compose/performance/baseline-profiles]

一张可执行的验收表至少包含这些字段：

| 指标 | 建议采集方式 | 判定方式 |
|---|---|---|
| 冷启动 / 热启动耗时 | Macrobenchmark `StartupTimingMetric` | P50 / P90 / P95 不劣化；收益要给出设备和迭代次数 |
| 页面首帧 | Macrobenchmark + FrameTimeline | 目标页面首帧不晚于迁移前基线 |
| 滚动帧耗时 | Macrobenchmark scroll + Perfetto | 16.6/11.1/8.3 ms 档位按目标刷新率分别统计 |
| 重组次数 / 跳过次数 | Layout Inspector / Compose Profiler / compiler metrics | 高频组件重组次数有解释；跳过失败能追到参数稳定性 |
| GC 暂停和分配 | Android Studio Profiler / Perfetto / ART counters | 滑动阶段无持续分配尖峰；GC pause 不集中压到交互窗口 |
| 内存峰值 | Profiler / dumpsys meminfo / Perfetto | 混合层不会长期持有 Fragment view、Context 或旧 View 缓存 |
| 线上帧指标 | APM / FrameMetrics / statsd | 灰度期间与老页面分桶对比，按设备档位拆开看 |

## XML to Compose migration skill 的适用范围

Google 公告提到 XML to Compose migration skill，可用于把旧 XML 布局转换成 Compose 草案。[已验证: Android Developers Blog, 2026-05-21] 它适合做初始迁移加速，不适合直接生成可发布代码。

转换后要人工确认四件事：状态是否提升到正确层级；语义和无障碍信息是否保留；自定义属性、主题和尺寸资源是否被等价表达；性能路径是否经过 Macrobenchmark 或至少经过可重复的手工 trace。XML 结构被转成 Composable 函数，只说明 UI 形状接近，不说明状态模型和渲染成本已经达标。

## Compose Multiplatform 与 Android App 迁移的差异

Compose First 面向 Android UI 开发主路径；Compose Multiplatform 是跨平台 UI 技术选择。Android App 内部迁移时，判断对象是 Android 设备上的启动、渲染、输入、内存和工具链；跨平台方案还要加入桌面、iOS、共享业务层和团队技能边界。

因此，不能把 Compose Multiplatform 的限制直接套到 Android 页面迁移，也不能用 Android Compose 的成熟度推断跨平台项目的成本。Android 原生页面优先关心与 View 互操作、AndroidX 版本、ART profile、Perfetto 和线上指标；跨平台项目还要单独评估平台能力缺口、组件差异和发布流程。

## Compose 1.10+ 发布说明跟踪

Compose 1.10 之后，列表预取、Pausable Composition、Modifier 行为、runtime tracing 和 compiler metrics 仍在快速变化。进入稳定版本之前，任何“默认启用”“性能对等”“列表卡顿率显著下降”这类判断都要补齐四个条件：Compose BOM / Foundation / Compiler 版本、Android Studio 或 AGP 版本、设备与刷新率、测试场景与统计口径。

本节结论基于 2026-05-21 可验证的公开文档和本地调研。后续 Compose Foundation 如果重新默认启用 Pausable Composition，或 Compose Profiler 的入口和数据项发生变化，应先更新本节的版本边界，再同步回 22.3 节。
