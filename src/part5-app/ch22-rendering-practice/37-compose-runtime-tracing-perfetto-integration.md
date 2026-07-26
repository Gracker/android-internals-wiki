---
title: "Compose Runtime Tracing — runtime-tracing 与 Perfetto 组合阶段追踪"
chapter: "22.37"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Compose, Tracing, Perfetto, Observability, Recomposition]
related_chapters: ["22.28", "22.3", "13.21", "26.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构/官方文档"
last_verified: "2026-07-26"
confidence: medium-low
sources:
  - "developer.android.com/develop/ui/compose/tooling/tracing"
  - "developer.android.com/jetpack/androidx/releases/tracing"
  - "developer.android.com/jetpack/androidx/releases/compose-runtime"
  - "技术文章/source/juejin-android/2026-07-25-76336249-Android-App-最强APM来袭.md"
last_body_apply_at: "2026-07-25T07:15:14+08:00"
last_body_apply_run_id: "20260725-071514-c8dfcc93"
last_body_apply_source: "source-index:100 / 2026-07-25-76336249-Android-App-最强APM来袭.md"
task2b_state: fixed
task6_state: needs-rework
task9_state: needs-rework
pipeline_stage: needs-rework
reviewed_date: "2026-07-26"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-26T12:17:49+08:00"
last_review_finalize_run_id: "20260726-121635-46911438"
rework_reason: "本轮补核官方 Compose tracing 文档：已确认 runtime-tracing 依赖、Android Studio Flamingo/Compose UI 1.3.0/Compiler 1.3.0/API 30+ 前提，以及手动 Perfetto 采集需要 tracing-perfetto 与 tracing-perfetto-binary 且 binary 不应随生产包发布；但可见 Slice 命名清单、重组原因字段与线上 Release 短窗口采集矩阵仍需同版本 trace_processor/实测样本后才能 finalized。"
---

# 22.37 Compose Runtime Tracing — runtime-tracing 与 Perfetto 组合阶段追踪

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Compose Runtime Tracing 架构与启用方式
- `androidx.compose.runtime:runtime-tracing` 是官方 Compose Runtime Tracing 依赖；官方 setup 明确要求 Android Studio Flamingo+、Compose UI 1.3.0+、Compose Compiler 1.3.0+、API 30+ 设备/模拟器，并可通过 Compose BOM 管理版本。不要误写为不存在的 `androidx.tracing.compose` 模块。[来源: developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/compose-runtime]
- CompositionTracer 接口：组合阶段追踪的钩子设计 [结构参考: 本章原始大纲]
- 启用方式：开发期、Benchmark 和 Android Studio/Perfetto 场景优先验证；Release 线上使用需要由采样、限流和开关保护，具体 API/版本矩阵需补官方示例后再定稿。[结构参考: developer.android.com/jetpack/androidx/releases/compose-runtime]
- 手动 Perfetto 采集路径需要额外加入 `androidx.tracing:tracing-perfetto` 与 `androidx.tracing:tracing-perfetto-binary`；官方同时警告不要把 `tracing-perfetto-binary` 随生产应用发布，因为它会显著增加包体积。因此本章的 Release 策略只能写成“动态开关 + 受控采样 + 构建产物隔离”，不能写成无条件常驻依赖。[来源: developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/tracing]

### 🔹 锚点 2：Compose 组合阶段的 Trace 事件
- 可见事件应以实际 Perfetto Slice 名称为准；本轮材料不能支撑固定写死 `recompose:start/end`、`compose:start/end`、`subcompose:start/end` 这类事件名，因此正文只保留“组合/重组/子组合相关 Slice”的能力边界。[待验证: 本轮 review]
- 若后续定稿需要事件名表，应从同一 Compose/AndroidX 版本下的 Perfetto trace 与 `trace_processor` 查询结果抽取，而不是沿用大纲占位名称；官方文档只承诺 system trace 可看到 composable function slices，并未在本轮核对中给出固定事件名表。[来源: developer.android.com/develop/ui/compose/tooling/tracing；待验证: trace_processor 实测]
- Trace 事件通常能帮助定位组合/重组相关 Slice，但“每个事件都携带重组原因”未在本轮来源中得到充分证明，定稿前应以官方 Runtime Tracing 示例或实测 trace_processor 输出校验。[待验证: 本轮 review]
- Trace 事件与 FrameTimeline 的时序对齐 [结构参考: 本章原始大纲]

### 🔹 锚点 3：Perfetto 中分析 Compose 组合开销
- 在 Perfetto UI 中识别 Compose 重组 Track [结构参考: 本章原始大纲]
- 重组频率热点定位：某 Composable 单帧重组次数 [结构参考: 本章原始大纲]
- 子组合嵌套深度的 Perfetto 可视化 [结构参考: 本章原始大纲]
- 重组与布局/绘制阶段的耗时占比分析 [结构参考: 本章原始大纲]
- 使用 Perfetto SQL 查询重组统计（与 13.22 Perfetto SQL Cookbook 联动）[结构参考: 本章原始大纲]

### 🔹 锚点 4：生产环境 Compose Tracing 部署
- tracing-perfetto/runtime-tracing 在 Release 构建中的开销、启用条件与二进制依赖边界需补官方或实测证据后再写成版本矩阵。[结构参考: developer.android.com/jetpack/androidx/releases/tracing]
- 采样策略：基于用户的灰度采样 vs 基于会话的触发式采样 [来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
- Trace 数据的线上收集与聚合 [来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
- 与现有 APM 框架（Firebase Performance / 自研 APM）的集成路径 [来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

### 🔹 锚点 5：重组归因与性能反模式识别
- 不要直接宣称 Trace 事件能给出 State 变化、强制重组、键值变化等“重组原因”；本章现有来源只足以支撑用 Slice 观察组合/重组时序，原因归因需结合 Layout Inspector、Compose Compiler Metrics、业务状态订阅和实测 trace_processor 结果。[待验证: 本轮 review]
- 高频重组 Composable 的自动识别规则 [结构参考: 本章原始大纲]
- 无效重组（unnecessary recomposition）的 Trace 特征 [结构参考: 本章原始大纲]
- 与 Compose Compiler Metrics（22.28）交叉验证重组问题 [结构参考: 本章原始大纲]

### 🔹 锚点 6：与 Layout Inspector / Recompose Highlighter 的工具链协同
- Layout Inspector 的实时重组高亮 vs Perfetto 的离线深度分析 [结构参考: 本章原始大纲]
- 开发期调试工具与线上监控工具的能力边界 [结构参考: 本章原始大纲]
- 从开发期发现到线上验证的完整 Compose 性能工作流 [结构参考: 本章原始大纲]

## 扩展

### 🔸 扩展点 1：自定义 Trace Section 与 Composable 关联
- 使用 Trace.beginSection() 在自定义 Composable 中添加细粒度追踪 [结构参考: developer.android.com/jetpack/androidx/releases/tracing]
- Modifier.Node 架构下的自定义追踪粒度控制 [结构参考: 本章原始大纲]
- 追踪命名规范与 Perfetto Slice 聚合 [结构参考: 本章原始大纲]

### 🔸 扩展点 2：Compose Tracing 与 Macrobenchmark 集成
- 在 Macrobenchmark 测试中自动收集 Compose Trace [结构参考: 本章原始大纲]
- 基线对比：重组次数回归检测 [结构参考: 本章原始大纲]
- CI/CD 中的 Compose 性能门禁自动化 [来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

<!-- outline-end -->

## 1. 本章定位：把 Compose Trace 放进 APM 闭环

> Review 状态：本章当前适合作为“Compose Trace 如何接入 APM 闭环”的工程策略草稿；依赖名已修正为 `androidx.compose.runtime:runtime-tracing`，本轮补核了官方 Compose tracing setup 前提（Android Studio Flamingo+、Compose UI/Compiler 1.3.0+、API 30+）与 `tracing-perfetto-binary` 不应随生产包发布的边界，但可见 Slice 命名、重组原因字段和线上 Release 短窗口采集矩阵仍缺少同版本 Perfetto/trace_processor 实测证据，因此暂不 finalized。

Compose Runtime Tracing 的价值不只是“在 Perfetto 里多看几条 Slice”，而是把组合、重组、子组合等 UI 运行时开销纳入可回放、可归因、可门禁的性能观测链路。[结构参考: 本章原始大纲] 对应用侧来说，它应当和启动、FPS、慢方法、网络、IO 等信号一起进入 APM 事件模型，而不是停留在一次性的本地调试截图。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

材料中的 Android APM 框架把性能监控拆成按需注册的模块，并通过 `Apm.init(application, ApmConfig(...))` 加模块注册完成低侵入接入；这说明 Compose Tracing 在工程里也应作为“渲染/帧率观测的可选子能力”纳入模块化开关，而不是强制全量开启。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 同一材料还把令牌桶限流、灰度发布、动态配置列为生产可用性的核心设计，因此 Compose Trace 的线上部署也应具备采样率、触发条件、上传配额和降级策略。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 2. APM 维度映射：Compose Trace 与 FPS/Render 模块的关系

材料列出的 FPS 模块使用 Choreographer VSync 与 FrameMetrics 观测掉帧、卡顿和冻结，Render 模块关注 View 树数量、层级深度和过度绘制预留项。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 在 Compose 页面中，FrameMetrics/FPS 能告诉我们“这一帧慢了”，而 Compose Runtime Tracing 的目标是补足“慢帧前后是否发生了高频重组、子组合嵌套或组合阶段膨胀”。[结构参考: 本章原始大纲]

因此推荐把数据分成两层：第一层是轻量指标，例如帧耗时、丢帧等级、页面名和设备分组；第二层是触发式 Trace，例如当某页面连续出现卡顿或冻结时再采集 Perfetto Trace 片段。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 这样做的依据是材料中的 APM 设计已经包含令牌桶限流、灰度发布和动态配置，可以为“只在异常会话采集 Trace”提供生产控制面。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 3. 生产启用策略：灰度、限流与动态配置

生产环境不要把 Compose Trace 当成无条件常开能力；更稳妥的方式是把它绑定到 APM 配置中心，由动态配置决定页面白名单、采样比例、最大 Trace 时长和上传频率。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 材料中的 GrayReleaseController 支持按比例开启新模块，RateLimiter 支持保护上报通道，DynamicConfigProvider 支持运行时调整阈值，这三类能力正好对应 Compose Trace 的灰度、限流和阈值控制。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

一个可执行的落地规则如下：

1. Debug/Benchmark 构建中优先完整采集 Compose Trace，用于开发期回归和 Macrobenchmark 对比；官方 composition tracing 文档给出的最低前提是 Android Studio Flamingo+、Compose UI/Compiler 1.3.0+、API 30+，本章适用版本 Android 13—17 均高于该设备 API 前提。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
2. Release 构建中默认关闭全量 Trace，只保留 FPS/FrameMetrics 等轻量观测；当动态配置命中目标页面、设备档位或慢帧阈值时，再按已验证的 AndroidX tracing/runtime-tracing 接入方式采集短窗口 Trace，并确保 `tracing-perfetto-binary` 不进入常规生产包，避免在缺少版本矩阵证据时宣称某个统一的显式开启 API。[来源: developer.android.com/develop/ui/compose/tooling/tracing；2026-07-25-76336249-Android-App-最强APM来袭.md；待验证: trace_processor 实测]
3. 上传链路沿用 APM 的本地存储、批量重试和压缩上传策略，避免在弱网或高频异常场景中放大性能问题。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
4. Trace 产物只作为问题归因证据进入后台，不作为普通埋点高频上报；这与材料中“令牌桶限流 + 灰度发布 + 动态配置，生产环境可用”的思路一致。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 4. 归因流程：从慢帧到 Compose 重组证据

一次完整排查可以按“先轻后重”的顺序执行：先由 FPS 模块发现卡顿帧，再检查页面、设备、启动阶段、网络和 IO 是否有同步异常，最后调取 Perfetto 中的 Compose Trace Slice 做组合阶段归因。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 材料中的 APM 能力覆盖启动、网络、FPS、慢方法、IO、SQLite、Binder IPC、线程和 GC 等维度，因此 Compose Trace 不应孤立解释所有慢帧，而应和这些维度一起做交叉排查。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

在 Perfetto 侧，重点看三类现象：同一帧内是否出现过多重组 Slice、子组合 Slice 是否嵌套过深、组合阶段耗时是否挤占了布局/绘制预算。[结构参考: 本章原始大纲] 如果 Trace 显示组合阶段正常，而同一时间 APM 慢方法或 IO 模块报告主线程阻塞，则应优先处理主线程阻塞而不是盲目优化 Composable 结构。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 5. 与字节码插桩和慢方法监控的边界

材料中的慢方法模块同时使用 Looper Hook 与 ASM 字节码插桩，并通过 AGP instrumentation API 提供方法耗时采集能力。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 这类方法级监控适合回答“哪个函数慢”，而 Compose Runtime Tracing 更适合回答“组合阶段何时发生、与帧时序如何重叠”。[结构参考: 本章原始大纲]

两者可以互补，但不应互相替代：如果某个 Composable 的业务计算函数被 ASM 标记为慢方法，再结合 Compose Trace 中的重组次数，就能判断问题是单次计算过重，还是状态订阅导致重复计算过多。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 对 CI/CD 门禁而言，可以用 Macrobenchmark 固定场景采集 Trace，再用慢方法统计验证是否有新增热点方法；材料中明确包含“构建 + 测试”和基于 AGP instrumentation API 的插桩能力，可作为自动化门禁的工程基础。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 6. 事件模型建议

为了让 Compose Trace 进入 APM 后台，事件至少应包含以下字段：页面/路由、设备分组、帧时间窗口、Trace 文件索引、采样策略版本、触发原因和关联轻量指标。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 材料中的 apm-model 使用 ApmEvent 与 Line Protocol 序列化，apm-storage 使用 EventStore 与 FileEventStore，apm-uploader 提供 HttpApmUploader、LogcatApmUploader 和 RetryingApmUploader；这些模块说明 Trace 摘要与上传引用可以复用统一事件管线。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

注意不要把完整 Perfetto 文件当成普通指标无限制上传；更合理的方式是上传摘要指标与受控文件引用，完整 Trace 只在命中采样、用户授权和服务端配额时保留。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 这与材料强调的本地存储、重试上传、Gzip 压缩和令牌桶限流一致，也能降低线上观测系统反向制造卡顿的风险。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 7. 检查清单

- 是否只在 Android 13（API 33）到 Android 17（API 37）范围内描述本章行为，避免引入 Android 18/API 38+ 结论。[适用版本: 本章 frontmatter]
- 是否把 Compose Trace 和 FPS/FrameMetrics 指标关联，而不是只保存孤立 Trace 文件。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
- 是否通过灰度发布、动态配置和令牌桶限流控制 Release 采集范围。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
- 是否把 Trace 摘要接入统一事件模型、本地存储和重试上传链路。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
- 是否在 Perfetto 中把重组/组合/子组合 Slice 与慢帧窗口对齐分析。[结构参考: 本章原始大纲]

[结构参考: 官方文档 developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/tracing]
[适用版本: Android 13 (API 33) - Android 17 (API 37)；composition tracing 的官方复现前提为 Android Studio Flamingo+、Compose UI/Compiler 1.3.0+、API 30+、加入 `androidx.compose.runtime:runtime-tracing`]
