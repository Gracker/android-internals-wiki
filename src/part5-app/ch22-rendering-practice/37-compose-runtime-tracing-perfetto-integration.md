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
last_verified: "2026-07-27"
confidence: medium
task2b_state: fixed
task6_state: fixed
task9_state: rework-fixed
pipeline_stage: ready-for-review
last_body_apply_at: "2026-07-25T07:15:14+08:00"
last_body_apply_run_id: "20260725-071514-c8dfcc93"
last_body_apply_source: "source-index:100 / 2026-07-25-76336249-Android-App-最强APM来袭.md"
reviewed_date: "2026-07-27"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-27T08:23:36+08:00"
last_review_finalize_run_id: "20260727-082309-5af88f00"
last_rework_at: "2026-07-27T09:35:33+08:00"
last_rework_run_id: "20260727-093533-rework-2ce7e666"
last_verified_against: "AndroidX Compose Runtime Tracing 官方文档、AndroidX tracing release 文档、AndroidX compose-runtime release 文档；结论边界止于 Android 17/API 37"
rework_summary: "删除原始大纲占位与未实证事件名/字段承诺；把章节收敛为 Android 13-17 范围内可审查的 Compose Runtime Tracing + Perfetto + APM 工程策略；明确 runtime-tracing 依赖、Flamingo/Compose UI 1.3.0+/Compiler 1.3.0+/API 30+ 前提、track_event/ENABLE_TRACING 手动采集边界、tracing-perfetto-binary 生产包隔离要求。"
sources:
  - "developer.android.com/develop/ui/compose/tooling/tracing"
  - "developer.android.com/jetpack/androidx/releases/tracing"
  - "developer.android.com/jetpack/androidx/releases/compose-runtime"
  - "技术文章/source/juejin-android/2026-07-25-76336249-Android-App-最强APM来袭.md"
---

# 22.37 Compose Runtime Tracing — runtime-tracing 与 Perfetto 组合阶段追踪

## 1. 本章定位：只把已核实边界写成工程策略

Compose Runtime Tracing 的价值不只是“在 Perfetto 里多看几条 Slice”，而是把组合、重组、子组合等 UI 运行时开销纳入可回放、可关联、可门禁的性能观测链路。官方文档给出的入口是 `androidx.compose.runtime:runtime-tracing`，不是 `androidx.tracing.compose` 之类的模块名；官方 setup 同时要求 Android Studio Flamingo+、Compose UI 1.3.0+、Compose Compiler 1.3.0+，并在 API 30+ 设备或模拟器上查看 system trace。本章的适用范围是 Android 13（API 33）到 Android 17（API 37），均高于该设备 API 前提。[来源: developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/compose-runtime]

本章不把 Compose Runtime 内部钩子、Slice 名称、重组原因字段或 Release 采集矩阵写成稳定 API。当前可安全落地的结论是：应用可以通过官方 runtime-tracing 依赖让 Compose 相关工作出现在 system trace / Perfetto 中；生产化时需要把采集动作放进受控开关、采样、限流和构建产物隔离之下。[来源: developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/tracing]

材料中的 Android APM 框架把性能监控拆成按需注册的模块，并通过 `Apm.init(application, ApmConfig(...))` 加模块注册完成低侵入接入；这说明 Compose Tracing 在工程里也应作为“渲染/帧率观测的可选子能力”纳入模块化开关，而不是强制全量开启。同一材料还把令牌桶限流、灰度发布、动态配置列为生产可用性的核心设计，因此 Compose Trace 的线上部署也应具备采样率、触发条件、上传配额和降级策略。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 2. 依赖与采集边界

### 2.1 Android Studio / Benchmark 优先路径

开发期和 Benchmark 场景优先使用 Android Studio 与 Macrobenchmark 触发采集：

1. 在 Compose 应用或基准测试工程中加入 `androidx.compose.runtime:runtime-tracing`，版本可由 Compose BOM 管理。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
2. 保持 Compose UI 1.3.0+ 与 Compose Compiler 1.3.0+，并在 API 30+ 设备或模拟器上采集。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
3. 用 Android Studio Profiler / system trace / Perfetto 观察 Compose 相关 Slice 与 FrameTimeline、Choreographer、主线程任务之间的时序关系。[来源: developer.android.com/develop/ui/compose/tooling/tracing]

这一路径适合做本地问题复现、Benchmark 基线、CI 门禁中的“是否新增组合阶段热点”对比。它不要求把 Perfetto 二进制依赖随普通生产包发布。

### 2.2 手动 Perfetto 采集路径

手动从 terminal 或外部 Perfetto 配置采集时，需要额外区分两个 AndroidX tracing 组件：

- `androidx.tracing:tracing-perfetto`：在应用侧提供 Perfetto tracing 集成能力。[来源: developer.android.com/jetpack/androidx/releases/tracing]
- `androidx.tracing:tracing-perfetto-binary`：提供 Perfetto SDK native binary；官方文档提示它会显著增加 APK 大小，不应随生产应用发布。[来源: developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/tracing]

手动采集时，Perfetto record config 至少要包含 `track_event` data source；启动采集前还需要向目标包名发送 `androidx.tracing.perfetto.action.ENABLE_TRACING` 广播，并指定 `androidx.tracing.perfetto.TracingReceiver`。Android Studio 自动采集会代做激活流程，手动采集不能简化成“只加依赖即可”。[来源: developer.android.com/develop/ui/compose/tooling/tracing]

## 3. APM 维度映射：Compose Trace 与 FPS/Render 模块的关系

材料列出的 FPS 模块使用 Choreographer VSync 与 FrameMetrics 观测掉帧、卡顿和冻结，Render 模块关注 View 树数量、层级深度和过度绘制预留项。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 在 Compose 页面中，FrameMetrics/FPS 能告诉我们“这一帧慢了”，Compose Runtime Tracing 的目标则是补足“慢帧附近是否存在组合/重组/子组合相关工作”。

推荐把数据分成两层：第一层是轻量指标，例如帧耗时、丢帧等级、页面名和设备分组；第二层是触发式 Trace，例如当某页面连续出现卡顿或冻结时，再采集短窗口 Perfetto Trace。这样做的依据是材料中的 APM 设计已经包含令牌桶限流、灰度发布和动态配置，可以为“只在异常会话采集 Trace”提供生产控制面。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 4. Perfetto 分析口径：看 Slice 时序，不伪造字段

在 Perfetto 侧，本章只承诺三类可审查分析口径：

1. **时序对齐**：把 Compose 相关 Slice 与慢帧窗口、FrameTimeline、主线程 Runnable 和 Choreographer 回调对齐，判断组合阶段是否挤占帧预算。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
2. **频次与时长趋势**：在同一版本、同一场景、同一采集配置下比较 Slice 的出现次数和耗时分布，用于识别回归趋势；不要在未固定 trace schema 前承诺“某 Composable 单帧重组次数”这样的后台字段。
3. **交叉排查**：如果 Compose 相关 Slice 正常，而同一时间 APM 慢方法、IO、SQLite、Binder IPC、线程或 GC 模块报告主线程阻塞，则应优先处理主线程阻塞，而不是盲目优化 Composable 结构。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

反过来，Trace 事件不应被写成可以直接给出 State 变化、强制重组、键值变化等“重组原因”。原因归因需要结合 Layout Inspector、Compose Compiler Metrics、业务状态订阅、代码审查和同版本 trace_processor 输出；本章只把 Perfetto 作为时序证据入口，而不是唯一归因引擎。

## 5. 生产启用策略：灰度、限流与构建产物隔离

生产环境不要把 Compose Trace 当成无条件常开能力；更稳妥的方式是把它绑定到 APM 配置中心，由动态配置决定页面白名单、采样比例、最大 Trace 时长和上传频率。材料中的 GrayReleaseController 支持按比例开启新模块，RateLimiter 支持保护上报通道，DynamicConfigProvider 支持运行时调整阈值，这三类能力正好对应 Compose Trace 的灰度、限流和阈值控制。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

可执行规则如下：

1. Debug/Benchmark 构建中优先完整采集 Compose Trace，用于开发期回归和 Macrobenchmark 对比。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
2. Release 构建中默认关闭全量 Trace，只保留 FPS/FrameMetrics 等轻量观测；命中动态配置、目标页面、设备档位或慢帧阈值时，才采集短窗口 Trace。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
3. `tracing-perfetto-binary` 不进入常规生产包；如必须验证手动 Perfetto 集成，应使用独立 benchmark/debug/internal 构建变体隔离二进制依赖。[来源: developer.android.com/develop/ui/compose/tooling/tracing；developer.android.com/jetpack/androidx/releases/tracing]
4. 上传链路沿用 APM 的本地存储、批量重试和压缩上传策略，避免在弱网或高频异常场景中放大性能问题。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
5. Trace 产物只作为问题归因证据进入后台，不作为普通埋点高频上报；完整 Perfetto 文件只在命中采样、用户授权和服务端配额时保留。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 6. 与字节码插桩和慢方法监控的边界

材料中的慢方法模块同时使用 Looper Hook 与 ASM 字节码插桩，并通过 AGP instrumentation API 提供方法耗时采集能力。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md] 这类方法级监控适合回答“哪个函数慢”，而 Compose Runtime Tracing 更适合回答“组合阶段何时发生、与帧时序如何重叠”。

两者可以互补，但不应互相替代：如果某个 Composable 的业务计算函数被 ASM 标记为慢方法，再结合 Compose Trace 中同一时间窗口的组合/重组 Slice 分布，就能判断问题更像是单次计算过重，还是状态订阅导致重复进入组合路径。对 CI/CD 门禁而言，可以用 Macrobenchmark 固定场景采集 Trace，再用慢方法统计验证是否有新增热点方法；材料中明确包含“构建 + 测试”和基于 AGP instrumentation API 的插桩能力，可作为自动化门禁的工程基础。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 7. 事件模型建议

为了让 Compose Trace 进入 APM 后台，事件至少应包含以下字段：页面/路由、设备分组、帧时间窗口、Trace 文件索引、采样策略版本、触发原因和关联轻量指标。材料中的 apm-model 使用 ApmEvent 与 Line Protocol 序列化，apm-storage 使用 EventStore 与 FileEventStore，apm-uploader 提供 HttpApmUploader、LogcatApmUploader 和 RetryingApmUploader；这些模块说明 Trace 摘要与上传引用可以复用统一事件管线。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

不要把完整 Perfetto 文件当成普通指标无限制上传；更合理的方式是上传摘要指标与受控文件引用，完整 Trace 只在命中采样、用户授权和服务端配额时保留。这与材料强调的本地存储、重试上传、Gzip 压缩和令牌桶限流一致，也能降低线上观测系统反向制造卡顿的风险。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]

## 8. 检查清单

- 适用范围是否只覆盖 Android 13（API 33）到 Android 17（API 37），且结论边界止于 Android 17/API 37。
- 依赖是否写成 `androidx.compose.runtime:runtime-tracing`，并保留 Android Studio Flamingo+、Compose UI 1.3.0+、Compose Compiler 1.3.0+、API 30+ 的官方前提。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
- 手动 Perfetto 采集是否包含 `track_event` data source 与 `ENABLE_TRACING` / `TracingReceiver` 激活流程。[来源: developer.android.com/develop/ui/compose/tooling/tracing]
- Release 策略是否默认关闭全量 Trace，并通过灰度发布、动态配置和令牌桶限流控制短窗口采集范围。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
- `tracing-perfetto-binary` 是否被隔离在 benchmark/debug/internal 构建变体中，而不是随常规生产包发布。[来源: developer.android.com/jetpack/androidx/releases/tracing]
- Trace 摘要是否接入统一事件模型、本地存储和重试上传链路，而不是无限制上传完整 Perfetto 文件。[来源: 2026-07-25-76336249-Android-App-最强APM来袭.md]
