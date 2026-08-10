---
title: "Compose Runtime Tracing — runtime-tracing 与 Perfetto 组合阶段追踪"
chapter: "22.37"
status: finalized
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Compose, Tracing, Perfetto, Observability, Recomposition]
related_chapters: ["22.28", "22.3", "13.21", "26.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构/官方文档"
last_verified: "2026-07-27"
confidence: medium
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_body_apply_at: "2026-07-25T07:15:14+08:00"
last_body_apply_run_id: "20260725-071514-c8dfcc93"
last_body_apply_source: "source-index:100 / 2026-07-25-76336249-Android-App-最强APM来袭.md"
reviewed_date: "2026-07-27"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-27T14:05:40+08:00"
last_review_finalize_run_id: "20260727-140540-bf9d2ac9"
last_rework_at: "2026-07-27T09:35:33+08:00"
last_rework_run_id: "20260727-093533-rework-2ce7e666"
last_verified_against: "AndroidX Compose Runtime Tracing 官方文档、AndroidX tracing release 文档、AndroidX compose-runtime release 文档；结论边界止于 Android 17/API 37"
rework_summary: "删除原始大纲占位与未实证事件名/字段承诺；把章节收敛为 Android 13-17 范围内可审查的 Compose Runtime Tracing + Perfetto + APM 工程策略；明确 runtime-tracing 依赖、Flamingo/Compose UI 1.3.0+/Compiler 1.3.0+/API 30+ 前提、track_event/ENABLE_TRACING 手动采集边界、tracing-perfetto-binary 生产包隔离要求。"
sources:
- type: official
  path: developer.android.com/develop/ui/compose/tooling/tracing
- type: official
  path: developer.android.com/jetpack/androidx/releases/tracing
- type: official
  path: developer.android.com/jetpack/androidx/releases/compose-runtime
- type: reference
  path: 技术文章/source/juejin-android/2026-07-25-76336249-Android-App-最强APM来袭.md
---

# 22.37 Compose Runtime Tracing — runtime-tracing 与 Perfetto 组合阶段追踪

## 1. 先分开平台版本与 Compose 版本

平台源码基线是 Android 17 / API 37 / `android-17.0.0_r1`，内核基线是 `android17-6.18-2026-06_r6`。这两个 tag 决定 Choreographer、FrameTimeline、进程调度和系统录制能力的解释口径，不决定 Compose Runtime 的实现。

Jetpack Compose 随 AndroidX 发布。这里使用 Compose Runtime 1.11.4 的发布版本与源码快照 `854220f44ea8ea80fee824a6c5a045f39bede289`。分析工程时还要记录 Kotlin、Compose compiler plugin、Compose UI、Runtime、BOM 和 R8 配置。相同的 API 37 设备可以运行完全不同的 Compose 版本。

官方 Composition Tracing 文档保留以下最低条件：

- Android Studio Flamingo 或更新版本；
- Compose UI 1.3.0 或更新版本；
- Compose Compiler 1.3.0 或更新版本；
- API 30 或更新版本的设备或模拟器；
- 应用包含 `androidx.compose.runtime:runtime-tracing`。

讨论范围为 Android 13（API 33）至 Android 17（API 37），设备版本都满足 API 30 前提。这个前提来自 `tracing-perfetto` 当前 `enable()` 的 `@RequiresApi(Build.VERSION_CODES.R)`，不能改写成“Composition Tracing 从 Android 13 才可用”。

## 2. 一条 Composable slice 是怎样生成的

看到 Perfetto 中的函数名之前，代码经历四层协作。

| 层次 | 当前职责 | 不负责什么 |
| --- | --- | --- |
| Compose Compiler | 在生成代码中插入 `isTraceInProgress()`、`traceEventStart()`、`traceEventEnd()`，并保存可读的函数与源码位置信息 | 不启动 Perfetto 录制 |
| `runtime-tracing` | 用 AndroidX Startup 安装 `CompositionTracer` | 不提供应用侧录制文件 API |
| `tracing-perfetto` | 加载、注册 Perfetto SDK data source，提供同步 section begin/end | 不自动创建 system trace session |
| Studio、Macrobenchmark 或 Perfetto | 激活 SDK data source，配置 `track_event`，开始和停止录制 | 不推断 State 失效原因 |

### 2.1 Compiler marker 是入口

Compose Compiler 从 1.3.0 起会在生成代码中注入 tracing 调用和未混淆的显示字符串。默认 system trace 没有这些应用源码信息，因此只能看到较粗的 framework 或线程工作；加入 `runtime-tracing` 后，工具才有机会显示具体 Composable 及文件、行号。

字符串与 marker 会增加 APK 体积。官方给出了让 R8 把 tracing 函数视为无副作用并删除 marker 的规则，但同时提醒这些函数可能变化。项目要明确选择：

- 生产包保留 marker，benchmark 与用户运行的代码更接近，代价是 APK 体积增加；
- 生产包删除 marker，减小体积，benchmark 产物需要另行说明与生产包的差异。

不要只在性能报告里写“release”。还要记录 marker 是否被 R8 删除，否则两次测量可能比较的是不同代码。

### 2.2 `runtime-tracing` 安装全局 tracer

1.11.4 的 `ComposeTracingInitializer` 由 AndroidX Startup 自动创建，并调用内部 API `Composer.setTracer()`。它安装的 tracer 做三件事：

- `traceEventStart(..., info)` 调用 `PerfettoSdkTrace.beginSection(info)`；
- `traceEventEnd()` 调用 `PerfettoSdkTrace.endSection()`；
- `isTraceInProgress()` 返回 `PerfettoSdkTrace.isEnabled`。

这里有一个容易忽略的源码事实：`CompositionTracer` 接口收到 `key`、`dirty1`、`dirty2` 和 `info`，当前 initializer 只转发 `info`。所以 Perfetto 中的 slice 不能读取 dirty bit，也不能据此回答“参数 3 改变导致重组”。

### 2.3 激活和录制是两件事

`PerfettoSdkTrace.enable()` 会加载 native library、检查 Java/native 版本、向 Perfetto 注册 data source，然后把 `isEnabled` 设为 `true`。当前源码明确依赖该值不再回到 `false`。

激活之后，Compose 可以向 Perfetto SDK 发 section；是否有数据进入文件，还取决于当前 Perfetto session 是否订阅 `track_event`。因此：

- 发送 `ENABLE_TRACING` 不等于已经开始录制；
- 停止一轮 Perfetto session 不等于把 `PerfettoSdkTrace` 还原为未激活；
- 普通动态配置开关不能模拟这套工具协议。

## 3. 依赖与构建产物

### 3.1 目标应用依赖

下面的配置把 Compose Runtime Tracing 版本固定到 1.11.4。

```kotlin
dependencies {
    implementation("androidx.compose.runtime:runtime-tracing:1.11.4")
}
```

这段配置会引入 `runtime-tracing` 的 Startup initializer；该版本源码内部依赖 `tracing-perfetto:1.0.1`，不包含 `tracing-perfetto-binary`。如果项目使用 Compose BOM，可以省略 artifact 版本，但性能报告必须记录 Gradle 最终解析出的版本。

`runtime-tracing`、Compose Runtime、UI 与 compiler plugin 应按同一 BOM 或官方兼容关系管理。各 artifact 的最低依赖和发布节奏可能不同，不能只看版本号是否相同。不要把官方文档示例中的旧版本直接复制到已经使用 1.11.4 的工程，也不要单独升级 tracing artifact 后省略依赖解析结果。

### 3.2 binary 只放在诊断产物

官方文档警告 `tracing-perfetto-binary` 会明显增加应用体积，不应随普通生产应用发布。1.0.1 是当前稳定版本，并增加了 16 KB page size 支持。

下面的配置假定工程已经有名为 `benchmark` 的 release-like build type，只让该产物携带 Perfetto SDK binary。

```kotlin
dependencies {
    add("benchmarkImplementation", "androidx.tracing:tracing-perfetto:1.0.1")
    add(
        "benchmarkImplementation",
        "androidx.tracing:tracing-perfetto-binary:1.0.1",
    )
}
```

这段配置服务于 terminal 或内部设备诊断。若 binary 放在 Macrobenchmark test module，则由测试工具完成握手和加载；两种接法不要混为常规线上依赖。

### 3.3 测量构建要 profileable 且 non-debuggable

Debug 构建包含调试器支持、不同的优化结果和额外检查，不适合给出发布性能结论。官方要求准确计时时使用 `profileable`、`non-debuggable` 应用。常见做法是从 release 初始化一个 benchmark build type，使用测试签名并保留与 release 相同的 shrink、资源和 Baseline Profile 策略。

如果诊断产物加入了 binary，而生产包没有，报告应列出 APK 差异。若目标是验证用户产物本身，则优先由 Studio 或 Macrobenchmark 侧提供工具能力，避免修改目标 APK。

## 4. Android Studio 采集

Android Studio 的 System Trace 路径适合交互式定位：

1. 启动 profileable、non-debuggable 的目标应用；
2. 打开 CPU Profiler，选择 System Trace；
3. 进入目标页面后开始录制；
4. 执行会引发组合或重组的固定操作；
5. 停止录制，在线程轨道和 Flame Chart 中检查 Composable。

Studio 会处理 SDK 激活等工具步骤。双击 Composable slice 可以跳到源码；Flame Chart 可以显示函数、文件和行号。没有具体函数时，依次检查：

- 目标 APK 是否包含 `runtime-tracing`；
- Compose Compiler 是否满足版本要求；
- R8 是否删除了 trace marker；
- 设备是否至少为 API 30；
- 录制类型是否为 System Trace；
- 当前操作是否执行了目标 Composable，而不是被跳过或只触发 Layout/Drawing。

Studio 视图适合阅读单份 trace，不适合凭肉眼给出稳定的回归结论。回归比较要固定操作和构建，交给 Macrobenchmark 保存每轮结果。

## 5. Macrobenchmark 采集

Macrobenchmark 让目标应用运行在独立进程和 release-like 构建中，每轮 measurement 都能附带 system trace。目标应用仍需包含 `runtime-tracing`；额外的 `tracing-perfetto` 与 binary 按官方说明放在 Macrobenchmark test module。

下面的 runner 参数用于让 Macrobenchmark 启用包括 Composition Tracing 在内的 AndroidX Perfetto tracepoints。

```kotlin
android {
    defaultConfig {
        testInstrumentationRunnerArguments[
            "androidx.benchmark.fullTracing.enable"
        ] = "true"
    }
}
```

该参数类型为 boolean，默认值是 `false`，旧名称是 `perfettoSdkTracing`。启用参数只解决 AndroidX Perfetto tracepoint 采集；测试仍需定义稳定的启动模式、预热、用户操作、数据量和 metric。

Composition Tracing 很适合回答“这轮回归中多执行了哪些 Composable”，但不应直接作为 CI 数值门槛。slice 名称属于 Compose 工具输出，版本升级可能改变格式。CI 的主门槛使用 `FrameTimingMetric`、启动 metric 等稳定指标；trace 用于解释失败样本。

## 6. Terminal Perfetto 采集

手动采集适合验证自定义 Perfetto config，或检查 Studio 没有启用的系统 data source。目标应用或工具侧必须能提供匹配版本的 Perfetto SDK binary。

### 6.1 配置 `track_event`

下面的片段用于把 AndroidX Perfetto SDK 事件加入已有的 system trace 配置。

```protobuf
data_sources: {
  config {
    name: "track_event"
  }
}
```

这段配置只订阅 Perfetto SDK track events。要分析完整渲染链，还要在同一份 config 中加入 FrameTimeline、`linux.ftrace`、调度、gfx 和目标应用等需要的 data source；不要把仅含 `track_event` 的文件称为完整 Android system trace。

### 6.2 激活目标进程

下面的命令用于由 adb shell 显式激活目标包中的 `TracingReceiver`。

```bash
adb shell am broadcast \
  -a androidx.tracing.perfetto.action.ENABLE_TRACING \
  com.example.app/androidx.tracing.perfetto.TracingReceiver
```

这条命令中的包名要替换为设备上正在运行的 application ID。receiver 要求发送方持有 `android.permission.DUMP`，shell 可以调用，普通应用代码不具备该权限。命令结果中的 binary missing、checksum、版本不匹配或其他错误必须处理，不能只看 broadcast 已送达。

官方手动流程是先启动应用并进入待测位置，发送激活广播，再启动带 `track_event` 的录制命令。冷启动 trace 使用另一套握手动作和持久配置，不应拿 warm/hot 流程推断。

## 7. Composition slice 能证明什么

当前实现生成的是同线程、成对嵌套的同步 section。slice 名来自 compiler 传入的 `info` 字符串，通常含 Composable 名与源码位置。它提供三类可靠信息：

- 目标 Composable 在这个时间窗口执行过；
- begin/end 之间经过了多长墙钟时间；
- 嵌套关系反映这次执行调用了哪些带 marker 的 Composable。

它没有直接提供以下结论：

- 哪个 `State` 写入触发 invalidation；
- 某个参数的新旧值或 dirty bit；
- 函数为何未被 skip；
- 该函数在 Layout 或 Drawing 阶段消耗多少时间；
- GPU 绘制该 Composable 的时长；
- 独立、稳定的“重组原因”字段。

“执行过”也不等于“由慢帧触发”。Composable 可能在帧外准备 composition，也可能在正常帧中执行；应以 trace 上的实际线程、时间和 FrameTimeline 关联为准。

### 7.1 墙钟时长不等于 CPU 执行时间

同步 slice 的 `dur` 包含线程运行、等待锁、被调度器换出以及内部调用。若 slice 很长，需要同时看 thread state：

- 大部分时间是 Running：检查函数体计算、分配和内部调用；
- 大部分时间是 Runnable：检查 CPU 竞争、优先级和调度；
- 大部分时间处于 Sleeping 或 blocked：检查锁、Binder、I/O 或等待条件。

内核基线与这里的联系是：`android17-6.18-2026-06_r6` 决定标准调度机制的阅读基线，但具体设备还有 vendor kernel、cpuset、uclamp、频率和热策略。单个 Compose slice 不能证明内核调度异常。

### 7.2 inclusive duration 不能直接相加

父 Composable 的 slice 包含子 Composable。把所有 slice 的 `dur` 求和会重复计算嵌套时间。比较热点时要区分：

- inclusive time：函数及所有带 marker 子调用的总墙钟时间；
- self time：扣除直接子 slice 后的时间；
- occurrence count：匹配 slice 在采样场景中出现的次数。

Perfetto UI 的 Flame Chart 更适合观察调用层级。SQL 聚合适合批量筛选候选，但不能用 inclusive 总和代替线程 CPU 时间。

## 8. 从慢帧回到 Compose 代码

Composition Tracing 是标准 App Window 渲染证据的一段。Compose 内容通常经宿主 ViewRootImpl 与 HWUI 进入同一个 App Window buffer，后续仍经过 RenderThread、BLASTBufferQueue、SurfaceFlinger 和 HWC。

推荐按以下顺序阅读同一份 trace。

### 8.1 定位目标帧

用 FrameTimeline 找到目标应用的 deadline miss，确认 expected/actual timeline、present type 和 jank type。不要只凭一段 `Choreographer#doFrame` 很长就认定屏幕上已经掉帧。

### 8.2 检查 UI Thread 与 Composable

在目标帧附近查看：

- `Choreographer#doFrame` 及 callback；
- snapshot apply、Recomposer 或 composition 相关工作；
- 具体 Composable slice；
- measure、layout、draw 和 `syncAndDrawFrame()`；
- GC、Binder、锁、I/O 与线程状态。

Composition slice 与慢帧重叠只能说明它占用了同一时间窗口。若该线程长时间 Runnable，问题可能来自 CPU 竞争；若函数内部等待 Binder，优化状态稳定性不会消除等待。

### 8.3 继续检查 RenderThread 和显示后段

UI Thread 按时完成时，继续检查 RenderThread `DrawFrame`、dequeue/queue buffer、GPU completion、SurfaceFlinger actual timeline 和 present。Composition Tracing 没有显示 Composable 热点时，不能停在 Compose 层反复改代码。

Compose、View 和系统显示使用同一条后半段证据链。若瓶颈在 GPU overdraw、大图纹理、RenderThread 或 SurfaceFlinger，Composition slice 正常是很有价值的排除证据。

## 9. 用 PerfettoSQL 做可重复筛选

分析前先在 UI 中确认当前版本的实际 slice 命名。Compose 的内部 slice 和 `info` 格式不是稳定 API，SQL 不要长期绑定未经验证的固定前缀。

下面的查询用于统计一个已确认名称模式的出现次数、inclusive 总时长和最大时长。

```sql
SELECT
  name,
  COUNT(*) AS occurrences,
  ROUND(SUM(dur) / 1e6, 3) AS inclusive_ms,
  ROUND(MAX(dur) / 1e6, 3) AS max_ms
FROM slice
WHERE dur > 0
  AND name GLOB '*MyComposable*'
GROUP BY name
ORDER BY inclusive_ms DESC;
```

这段查询中的 `MyComposable` 要替换为本次 trace 中确认过的函数或源码标识；`dur` 的单位是纳秒。结果含嵌套重复，适合筛选候选，不代表应用总 CPU 时间，也不能单独证明帧回归。

做版本比较时至少固定：

- 设备、系统 build、刷新率和分辨率；
- 应用 commit、build type、R8 与 Baseline Profile；
- Kotlin、Compose compiler plugin、BOM、Runtime 和 UI；
- 页面数据、图片缓存状态、输入脚本和预热；
- Perfetto config 与 Macrobenchmark 参数；
- 电量、温度和后台负载。

## 10. 与其他 Compose 工具怎样配合

不同工具观察不同层次，互相替换会产生错误归因。

| 工具 | 能回答的问题 | 主要限制 |
| --- | --- | --- |
| Composition Tracing | 运行时何时执行了哪些 Composable | 不提供 State 来源与 dirty 值 |
| Compose Compiler reports/metrics | 编译期的 restartable、skippable、稳定性判断 | 不提供运行次数和耗时 |
| Layout Inspector | 交互场景中的 composition tree、重组与 skip 计数 | Inspector 会改变被测环境，不用于正式计时 |
| Macrobenchmark | 固定场景的帧、启动等端到端 metric 与 trace | 不解释任意线上会话 |
| JankStats / FrameMetrics | 哪些用户帧发生卡顿及轻量上下文 | 不显示每个 Composable |
| 自定义业务 trace marker | 业务操作、数据加载与 UI 工作的时间关系 | marker 粒度由工程维护 |

当 trace 显示某 Composable 频繁执行时，按这条路径继续：

1. 用 compiler report 检查它是否 skippable，以及参数稳定性判断；
2. 用 Layout Inspector 或小范围计数确认交互是否重复触发；
3. 检查 State 读取发生在 Composition、Layout 还是 Drawing；
4. 检查参数对象是否每次创建新实例；
5. 修改后用相同 Macrobenchmark 场景复测帧 metric 和 trace。

不要为了获得“更多证据”给每个 Composable 再加 `Trace.beginSection()` 或 ASM 方法插桩。Compose Compiler 已经提供 marker，大规模重复插桩会增加方法体、字符串、运行开销和 trace 数据量。

## 11. 接入 APM 时的边界

线上轻量监控适合记录页面、用户操作、帧结果、设备状态和业务阶段。它能帮助选择复现场景，也能把问题按版本、设备和页面分组。它不能自然地获得 shell 权限，也不能把 `ENABLE_TRACING` receiver 变成远程开关。

当前 `runtime-tracing` 源码没有“达到慢帧阈值后由普通应用开始短窗口 system trace”的公开接口。原有 APM 设计中的采样、限流、存储和上传可以管理轻量事件或合法获得的 profile 文件，但不能作为 Compose Perfetto SDK 激活能力的证据。

### 11.1 API 33—34

Android 13 和 Android 14 没有平台 `ProfilingManager`。普通生产应用应保留轻量帧监控和业务 marker，在实验室用相同页面、数据与设备复现后录制 Composition Trace。

### 11.2 API 35—37

Android 15 起，平台 `ProfilingManager` 支持应用请求 system trace；请求受系统限流，不保证执行，结果会经过隐私删减。Android 16/17 又增加了系统 trigger 相关能力。

这条平台能力适合生产 profile 文件管理，但不能自动替代 `runtime-tracing` 的 Perfetto SDK 激活协议。`ProfilingManager` 录制能看到应用和 framework 的平台 trace annotation；是否包含逐个 Composable，必须在目标 API、目标 Compose 版本和最终发布产物上验证。仅加入 `runtime-tracing` 后宣称所有线上 profile 都会含 Composable，证据不足。

### 11.3 文件、隐私和配额

Perfetto 文件可能含方法名、线程名、应用状态、调度信息和用户操作时序。生产系统至少要定义：

- 用户告知或授权条件；
- 本地文件保留时间；
- 单设备和服务端配额；
- 网络、电量和温度条件；
- 上传失败后的删除与重试规则；
- 服务端访问控制和审计；
- Android 版本、应用版本、trace config 与删减状态。

完整 trace 不应作为普通高频埋点上传。后台摘要也要保留来源：来自 JankStats、Macrobenchmark、manual Perfetto，还是 `ProfilingManager`，这些数据的可见范围不同。

## 12. 与慢方法和业务 marker 的关系

Looper 监控、采样 profiler、选择性方法 trace 与 Composition Tracing 可以关联使用：

- Composition slice 长，内部业务函数也长：检查业务计算、序列化、图片处理或同步调用；
- Composition slice 频繁但每次很短：检查 State 订阅范围、参数实例和跳过条件；
- Composition slice 正常，主线程有其他长任务：修复长任务所在模块；
- UI Thread 正常，RenderThread 或 GPU 超时：转到绘制与图形资源分析。

ASM 插桩得到的方法时长与 Perfetto slice 未必使用同一时间基准。若要自动关联，事件应记录 monotonic timestamp、进程、线程、页面实例、应用版本和场景 ID，并验证时钟换算。只按墙上时间相近合并两个系统的数据，容易把相邻任务配错。

来源材料中的模块化 APM、限流、持久化和重试设计可用于组织这些轻量数据；Compose API 名称、激活流程与可见字段仍以 AndroidX 文档和源码为准。

## 13. 常见误判

| 说法 | 问题 | 正确处理 |
| --- | --- | --- |
| 加了 `runtime-tracing` 就会一直录制 | 依赖只安装 tracer；还需要激活和 `track_event` session | 分别检查 marker、initializer、SDK 激活和录制 config |
| API 37 自带 Compose 1.11.4 | Compose 与 platform 独立发布 | 单独记录 Android、Kotlin 与 Compose 版本 |
| `dirty1`、`dirty2` 能在 Perfetto 里查到 | 1.11.4 initializer 没有转发它们 | 用 compiler report、Inspector 和代码审查分析失效原因 |
| 某 Composable slice 很长，所以它一直占用 CPU | `dur` 包含 runnable 与阻塞时间 | 同看 thread state、sched 和内部调用 |
| 所有 slice 时长相加就是组合总耗时 | 父子 section 会重复计算 | 区分 inclusive、self 与线程 CPU 时间 |
| Composition 很慢说明 GPU 很慢 | Composition 在应用代码侧生成或更新 UI tree | 另查 Drawing、RenderThread、GPU 与 FrameTimeline |
| 慢帧发生后再录几秒就能看到原因 | 触发前的工作可能已经离开缓冲区 | 使用可重复场景、预先启动录制或系统支持的 trigger |
| 远程配置可以发送 `ENABLE_TRACING` | receiver 受 `DUMP` 权限保护 | 由 Studio、adb 或测试工具完成激活 |
| Debug trace 可以代表发布性能 | Debug 与 release-like 构建优化不同 | 使用 profileable、non-debuggable 目标 |
| Compiler metric 能给出线上重组次数 | 它是编译期报告 | 运行次数用运行时工具测量 |

## 14. Android 17 评审清单

- 平台是否固定为 Android 17 / API 37 / `android-17.0.0_r1`，并把 Compose 版本单独记录；
- Compose Runtime Tracing 是否解析到 1.11.4，Runtime、UI、compiler plugin 和 Kotlin 是否按 BOM 或兼容关系管理；
- 设备是否至少为 API 30；
- 目标应用是否包含 `runtime-tracing`，R8 是否保留 marker；
- 目标构建是否 non-debuggable、profileable；
- `tracing-perfetto-binary` 是否只存在于 benchmark/internal 或测试工具；
- 手动录制是否显式包含 `track_event`；
- 激活广播是否指向正确 application ID 和 `TracingReceiver`，返回码是否成功；
- 是否误把 SDK 激活当作 Perfetto session 开始；
- Macrobenchmark 是否设置 `androidx.benchmark.fullTracing.enable=true`；
- 是否在当前 trace 中确认 slice 名后再写 SQL；
- 是否把 nested inclusive duration 错算成总 CPU 时间；
- 是否结合 FrameTimeline、UI Thread、RenderThread、GPU 和 sched；
- 是否把 Composable 执行记录误写成 State/参数失效原因；
- 是否把 Composition、Layout 和 Drawing 混成同一阶段；
- 线上方案是否区分轻量帧事件、manual trace 与 `ProfilingManager` 的删减 trace；
- profile 文件是否有权限、配额、保留和删除规则；
- 内核结论是否止于 `android17-6.18-2026-06_r6` 可证明的标准机制，没有把设备策略写成 AOSP 固定行为。

## 15. 结论

Compose Runtime Tracing 的核心价值是把 compiler 生成的 Composable 执行信息放进与系统帧、线程和调度共享时间轴的 Perfetto trace。它擅长回答“慢帧附近执行了哪些 Composable、嵌套关系和墙钟时长是什么”。

它不提供重组原因数据库。1.11.4 的 tracer 只转发显示字符串，dirty metadata 没有进入 trace；激活 receiver 又受 `DUMP` 权限保护。因此，工程上可靠的用法是以 Studio、Macrobenchmark 和受控 terminal 采集为主，用 compiler report、Layout Inspector、业务 marker 与完整渲染链证据补充归因。

Android 17 提供更完善的平台 profiling 能力，但平台版本不会改变 Compose artifact 的独立发布事实，也不会让 `runtime-tracing` 自动成为线上录制 API。每次性能结论都要同时写清 platform build、Compose/Kotlin 版本、构建方式和 trace config。

## 参考资料

- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)：最低版本、依赖、APK 体积、准确计时、terminal 与 Macrobenchmark 流程。
- [Compose Runtime release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime)：1.11.4 当前稳定版本与发布记录。
- [`ComposeTracingInitializer.kt`（Compose Runtime 1.11.4 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime-tracing/src/main/java/androidx/compose/runtime/tracing/ComposeTracingInitializer.kt)：Startup 初始化、`CompositionTracer` 与 `PerfettoSdkTrace` 转发。
- [`Composer.kt`（Compose Runtime 1.11.4 源码快照）](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composer.kt)：`CompositionTracer`、dirty metadata 与 tracer 安装接口。
- [`runtime-tracing/build.gradle`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime-tracing/build.gradle)：1.11.4 源码中的 `tracing-perfetto:1.0.1` 与 Startup 依赖。
- [AndroidX Tracing release notes](https://developer.android.com/jetpack/androidx/releases/tracing)：`tracing-perfetto` 1.0.1、16 KB page size 支持与版本记录。
- [`PerfettoSdkTrace.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/tracing/tracing-perfetto/src/main/java/androidx/tracing/perfetto/PerfettoSdkTrace.kt)：native library 加载、data source 注册、`isEnabled` 与同步 section。
- [`TracingReceiver.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/tracing/tracing-perfetto/src/main/java/androidx/tracing/perfetto/TracingReceiver.kt) 与 [manifest](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/tracing/tracing-perfetto/src/main/AndroidManifest.xml)：激活动作、API 30 检查与 `android.permission.DUMP` 保护。
- [Macrobenchmark instrumentation arguments](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-instrumentation-args)：`androidx.benchmark.fullTracing.enable` 的含义与默认值。
- [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager) 与 [profiling method comparison](https://developer.android.com/topic/performance/tracing/choose-right-method)：API 35—37 的生产 profile、限流、隐私删减和 manual trace 边界。
- [`Choreographer.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)：Android 17 应用帧与 FrameTimeline 平台入口。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线；Compose Runtime Tracing 不依赖专属内核 API。
