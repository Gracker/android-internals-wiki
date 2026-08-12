---
title: "性能测试最佳实践"
chapter: "15.6"
section: "15.6"
status: "ready-for-review"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-08"
last_verified_against: "AOSP android-17.0.0_r1 ThermalManagerService, DisplayModeDirector and ART Service; AndroidX Benchmark 1.4.1 stable, current Macrobenchmark, Microbenchmark and CI documentation; current Firebase Performance Monitoring documentation | 2026-08-08 rework: replaced 4 vague 见参考资料 source markers with exact official/AOSP URLs and rephrased body 待验证 to 待证实 to clear recurring pending-verification-marker/thin-source-marking flags"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-instrumentation-args"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview"
  - type: official
    path: "https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/benchmark"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/custom-code-traces"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/troubleshooting"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtShellCommand.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/BackgroundDexoptJobService.java"
  - type: aosp
    path: "art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java"
  - type: source
    path: "androidx-main/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/CompilationMode.kt"
  - type: source
    path: "androidx-main/benchmark/benchmark-junit4/src/main/java/androidx/benchmark/junit4/SideEffectRunListener.kt"
tags:
  - android
  - benchmark
  - research
related_chapters:
  - "14.9"
  - "15.5"
  - "8.3"
  - "13.2"
  - "5.5"
pipeline_stage: "ready-for-review"
task6_state: pending-review
task9_state: "pending-review"
task2b_state: fixed
last_rework_at: "2026-08-08T13:35:35+08:00"
last_rework_run_id: "20260808-133535-rework-b52e6e4a"
last_review_finalize_at: "2026-08-04T22:07:14+08:00"
last_review_finalize_run_id: "20260804-220518-6f1a5c2e"
last_idle_audit_at: "2026-08-06T18:35:19+08:00"
last_idle_audit_run_id: "20260806-183519-idle-audit-b52e6e4a"
---

# 性能测试最佳实践

## 性能测试测量的是分布

功能测试常用确定的断言判定一次执行。性能测试面对调频、缓存、GC、调度、I/O、温度和网络引入的随机波动，单次结果只能说明那次执行。可比较的性能结论需要同时固定三部分：

- 工作负载：入口、数据、手势、终止条件和正确性断言；
- 设备状态：硬件、系统镜像、电量、温度、显示、网络和后台活动；
- 统计协议：预热、编译状态、迭代、排除规则、聚合与回归判定。

工具会降低测量成本，不会自动补齐测试合同。Macrobenchmark 生成的数字若缺少设备状态和工作负载断言，仍可能测到错误页面、空列表或已经失败的启动。

## 先写测试合同

每个 benchmark 在代码和报告中都应回答以下问题：

| 项目 | 要写清的内容 |
|---|---|
| 目标 | 要保护的用户路径或代码单元 |
| 指标 | TTID、TTFD、`frameOverrunMs`、CPU time、allocation 等 |
| 方向 | 越小越好、越大越好或比率 |
| 范围 | 测量从哪里开始，到哪个可验证状态结束 |
| 状态 | app data、登录、缓存、编译、进程和 Activity 状态 |
| 环境 | 设备、系统 fingerprint、显示、温度、电量、网络 |
| 重复 | 预热方式、测量迭代、独立测试运行次数 |
| 判定 | 产品 SLO、允许回归、噪声下限和排除规则 |
| 证据 | 原始 JSON、每轮 trace、日志和构建产物摘要 |

测试块末尾应断言目标状态已经出现，例如列表加载完成、目标控件可见、视频开始播放。否则，应用崩溃后快速返回错误页也可能得到一组“更快”的结果。

## 测试环境标准化

### 设备：固定参考机与用户分层

CI 回归闸门需要专用物理设备。Android 官方不建议用模拟器做性能判定，因为结果受 host OS、虚拟化、GPU 和存储影响。模拟器与 Gradle Managed Devices 适合检查 benchmark 能否安装、启动和产出文件。

参考设备应固定：

- 设备序列号和硬件 revision；
- Android 版本、build fingerprint 和安全补丁；
- bootloader、vendor image 与 ART Mainline 模块版本；
- 电池健康、存储介质状态和实验室散热方式；
- 测试账号、区域、语言、字体缩放和无障碍设置。

用户设备分层从线上机型、SoC、RAM 和 Android 版本分布中选择，用于周期性兼容验证。PR 级细微回归尽量在同一台参考设备上比较基线与候选版本；不同设备的结果不直接做百分比差值。

系统镜像使用 user 或经过验证的 userdebug 构建。eng 构建、debuggable 目标包、代码覆盖率和 method tracing 都会改变执行路径。Macrobenchmark 目标应用应接近 release：`debuggable=false`、`profileable`、与发布一致的 R8/资源压缩配置，并包含满足当前 Benchmark 要求的 ProfileInstaller。

### 存储与数据状态

存储剩余空间会影响文件系统回收、数据库、安装和 dexopt。Android 没有适用于所有设备的固定“至少空闲百分比”。测试池应通过试运行确定拒测边界，报告同时保存可用字节、总容量和是否出现明显后台 I/O。

以下状态需要分别定义，不能用一句“清缓存”代替：

- app data 是否清除；
- HTTP、图片、数据库和业务缓存是冷还是热；
- APK 是否重装；
- ART 编译与 profile 状态；
- 进程、Activity 与 task 是否存在；
- 测试数据是否固定并完成准备。

`StartupMode.COLD` 会为冷启动终止应用进程，但不会自动清除 app data、业务缓存或模拟全新安装。`CompilationMode.None()` 重置编译状态，也不能改名为 fresh install。

### 温度：用状态门控，不套统一摄氏度

不同设备暴露的 thermal zone、传感器位置和厂商策略不同。`/sys/class/thermal/thermal_zone*/temp` 在量产设备上还可能不可读。一个固定摄氏度阈值无法跨机型表示同一种性能状态。

参考机应建立自己的冷机基线：

1. 记录室温、设备位置和散热配置；
2. 从 `dumpsys thermalservice`、厂商可读传感器和 Perfetto 记录热状态；
3. 运行试验确定进入降频前的状态范围；
4. 超出门控条件时暂停并冷却，样本标记为环境无效；
5. 保存每次运行的起止热状态与冷却时间。

Android 17 的 `cmd thermalservice override-status` 只覆盖 `ThermalManagerService` 向 framework 暴露的 thermal status。它不会关闭 Thermal HAL、kernel cpufreq/GPU 降频或厂商 thermal engine。该命令适合测试应用的 thermal callback，不能用来制造“未降频”基准。

### 峰值路径与热稳定态分开

启动、短滑动等短路径通常关心冷机或受控初始状态。游戏、直播、相机和持续列表交互还要测热稳定态。两者的前置条件和报告字段不同：

| 类型 | 前置条件 | 测量开始 | 报告重点 |
|---|---|---|---|
| 短路径回归 | 冷却到参考状态，缓存与编译状态固定 | 环境门控通过后 | 每轮时长、分布、起止热状态 |
| 持续负载 | 运行目标 workload 直到温度与性能进入稳定区间 | 预热区间结束后 | 稳态时长、帧/功耗分布、频率与热状态曲线 |

持续负载的“稳定”应由预先定义的滑动窗口条件判定，不能观察曲线后临时选择一段较平的区间。预热数据要保留，但不混入稳态统计。

### 电量与供电

Benchmark 会把低电量设备标为 `LOW-BATTERY` 错误。CI 闸门不应抑制该错误。即使接通电源，低电量策略仍可能限制大核；充电又会增加发热。

测试池需要固定供电协议，例如在规定电量范围内断电运行一组测试，或使用具备充电控制能力的设备架。协议选择可以不同，但基线与候选版本必须一致，并保存：

- 测试前后电量；
- 是否充电、充电功率状态；
- Battery Saver 与厂商省电模式；
- 运行中是否发生充电状态切换。

不要把“充满后一直插电”等同于所有设备上的恒定供电状态。厂商充电策略、电池温度和旁路供电能力并不一致。

### 显示模式、亮度与主题

60 Hz、90 Hz、120 Hz 和动态刷新率使用不同 deadline。性能回归比较应固定同一显示策略，或至少记录每帧实际 deadline。`DisplayModeDirector` 会综合系统 setting、应用帧率投票、功耗和 thermal 条件选择 mode，写入 `peak_refresh_rate` 与 `min_refresh_rate` 不保证 OEM 一定采用指定模式。

设备准备需要保存并恢复原 setting，随后用 `dumpsys display` 和 Perfetto 的 expected FrameTimeline 验证生效。报告记录 requested mode 和 observed mode，失败时拒绝比较。

亮度、自动亮度、主题和显示内容也要保持一致。OLED 上切换深浅主题会改变显示功耗，同时也改变被测 UI；不能为了散热把生产场景改成另一套主题。测动画或转场时保留发布配置的 animation scale，关闭系统动画会改变 workload。

### 网络：本地路径与网络路径使用不同方案

本地 UI、布局和滚动 benchmark 应使用预置数据或受控 fake backend，避免公共网络波动进入结果。网络性能测试则要固定：

- 服务端版本、region 和测试账号；
- 网络类型、延迟、带宽、抖动、丢包和代理配置；
- DNS、TLS session、HTTP cache 与连接复用状态；
- 每轮请求数据大小及服务端处理时间。

飞行模式、关闭 Wi-Fi 或代理限速都会改变系统与应用路径，应作为测试合同的一部分。用真实生产接口做回归闸门通常无法区分客户端改动与服务端、CDN 或公网变化。

## 消除测试干扰

### 使用专用设备，减少全局设置改动

通用脚本不应无条件关闭定位、同步、动画和所有后台应用。这些设置可能改变待测路径，也容易污染后续测试。更稳妥的隔离方式包括：

- 使用无个人账号、无消息推送的专用用户或专用设备；
- 固定安装清单和系统更新窗口；
- 在每个用例中 `force-stop` 目标应用并准备明确状态；
- 串行运行性能任务，禁止同设备并行测试；
- 记录 `top`、I/O、thermal 和异常系统任务作为数据质量证据；
- 所有变更都有 tear-down，设备重启后重新验收状态。

`adb shell am kill-all` 只处理符合条件的后台进程，无法终止系统服务、前台服务和维护任务，不能作为“设备已经干净”的证明。

### AndroidX SideEffectRunListener

当前 Benchmark 文档提供可选 `SideEffectRunListener`，用于在 benchmark 运行期间减少无关后台工作。AndroidX 源码中的 listener 配置 `DisablePackages` 与 `DisableDexOpt`，并在测试结束时恢复 side effect。

CI 可通过 instrumentation argument 启用：

```bash
./gradlew :macrobenchmark:connectedBenchmarkAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.listener=androidx.benchmark.junit4.SideEffectRunListener
```

这条命令的用途是让 Benchmark listener 管理其支持的副作用。Gradle task 名随 module 和 variant 变化；CI 要保存完整命令、Benchmark 版本与 listener 日志，确认 setup 和 tear-down 均成功。

### Android 17 后台 dexopt 的手动边界

若实验室脚本需要独立控制后台 dexopt，Android 17 的公开 shell 入口为：

| 操作 | 命令 | 语义 |
|---|---|---|
| 取消当前任务 | `adb shell pm bg-dexopt-job --cancel` | 非阻塞地取消当前后台 dexopt |
| 暂停 JobScheduler 启动 | `adb shell pm bg-dexopt-job --disable` | 取消已由 scheduler 启动的任务并停止后续调度 |
| 恢复调度 | `adb shell pm bg-dexopt-job --enable` | 重新调度后台 dexopt |

`cancel-bg-dexopt-job` 在 Android 17 只是 `bg-dexopt-job --cancel` 的废弃别名。`--disable` 状态在 `system_server` 退出后会丢失，而且不阻止所有系统内部启动路径。测试脚本必须检查输出，并在 tear-down 执行 `--enable`。

Android 17 中，`PackageManagerShellCommand` 只保留 ART Service 命令的兼容分发列表；处理代码在 `art/libartservice/.../ArtShellCommand.java`，调度与执行由 `BackgroundDexoptJob*` 和 `ArtManagerLocal` 完成。不要依赖旧版 `BackgroundDexOptService` 路径，也不要用无法确认权限和恢复行为的 `setprop` 代替这些命令。

### 锁频只适用于特定 Microbenchmark

Android 官方 CI 文档提供 Microbenchmark Gradle plugin 的 `lockClocks`/`unlockClocks`，要求 rooted 设备。官方也明确说明锁频仅在 Microbenchmark 场景需要。

Macrobenchmark 测量完整应用路径，DVFS、调度和 thermal 响应本来就是用户设备行为的一部分。直接写死 CPU0 的 sysfs governor 或频率既不跨 SoC，也可能改变线程迁移、GPU、内存和功耗行为。需要分析硬件上限时，应使用设备专用、可恢复的实验配置，并把结果标为实验室上限，不与用户代表性基线混用。

### Microbenchmark 与 Macrobenchmark 的自动稳定化不同

Microbenchmark 使用 `AndroidBenchmarkRunner`；其 runner 与 `IsolationActivity`、亮度控制和设备能力相关的稳定化逻辑属于 Microbenchmark 语境。Macrobenchmark 是独立进程驱动目标应用，官方 CI 文档要求使用常规 `AndroidJUnitRunner`。

因此，Macrobenchmark 不会仅因创建了 `MacrobenchmarkRule` 就完成温度、网络、目标数据和所有后台任务的标准化。SideEffectRunListener、专用设备、状态准备和数据质量检查仍需显式配置。

## 数据采样策略

### 迭代次数由噪声与最小可检测回归决定

官方 API 要求设置 `iterations`，示例会使用具体次数，但没有适用于所有 workload 的固定下限。短启动、长滚动、数据库迁移和持续视频的单轮成本与方差差异很大。

确定次数时可按以下流程：

1. 在参考设备上重复运行候选 workload；
2. 分离一次 instrumentation 内的迭代波动与多次 CI job 之间的波动；
3. 确定团队需要发现的最小回归幅度；
4. 选择能让置信区间窄于该幅度的迭代与独立 job 数；
5. 版本化这份采样协议。

样本少时，P90/P95 很接近极值，估计会很不稳定。十次启动的 P90 不能直接解释为线上 90% 用户体验。线上用户分位数来自不同设备和会话，实验室分位数来自同一设备上的重复运行，两者分母不同。

### Macrobenchmark 两类指标的聚合方式

当前 Macrobenchmark 官方文档给出两种常见输出语义：

| Metric | 数据层次 | 官方输出 |
|---|---|---|
| `StartupTimingMetric` | 每次启动一个值 | min、median、max，并在 JSON 保存 `runs` |
| `FrameTimingMetric` | 多轮中的帧样本池 | P50、P90、P95、P99 |

`StartupTimingMetric` 的 JSON 不会自动提供 P90 字段。需要启动尾部分位时，应从 `runs` 按版本化算法计算，并使用足够的独立启动样本。`FrameTimingMetric` 的 P90/P95/P99 是帧样本分布，不能写成“10 次滑动的 P90”而不说明合并方式。

API 31+ 优先看 `frameOverrunMs`：正值表示错过 deadline，负值表示剩余预算。`frameDurationCpuMs` 只描述 UI 线程与 RenderThread 的 CPU 生产时长，不能覆盖 GPU 与 SurfaceFlinger 的完整路径。

### 中位数、尾部与指标方向

中位数适合描述典型运行，对偶发长尾不敏感。尾部分位适合描述慢启动或长帧，但必须带样本量和估计方法。

指标方向也要保持一致：

- latency、duration、overrun、慢帧占比：数值越小越好，关注高分位；
- FPS、throughput：数值越大越好，关注低分位；
- rate：同时说明分子、分母和统计单元。

帧体验优先使用 `frameOverrunMs`、慢帧率或每轮帧时长分布。平均 FPS 会掩盖少量冻结帧，也容易受静止画面和帧率上限影响。

### Warm-up 有三种不同含义

| 类型 | 目的 | 是否进入测量 |
|---|---|---|
| Microbenchmark warmup | 让 JIT、缓存和循环达到库的稳定判定 | 不进入正式统计 |
| `CompilationMode.Partial.warmupIterations` | 运行 workload、收集 ART profile，再以 `speed-profile` 编译 | 发生在测量前 |
| 持续负载预热 | 让温度、频率和 workload 进入定义好的稳态 | 单独保存，不并入稳态统计 |

这三种 warm-up 不能互换。尤其是 `warmupIterations`，它改变目标应用的编译状态，属于测试条件。

### AndroidX Benchmark 1.4.1 的 CompilationMode

AndroidX Benchmark 当前稳定版为 1.4.1。`CompilationMode` 的语义如下：

| 模式 | 语义 | 使用建议 |
|---|---|---|
| `DEFAULT` | API 24+ 等价于 `Partial(UseIfAvailable, 0)` | 接近安装器可使用 Baseline Profile 的默认状态，但 profile 缺失不会失败 |
| `Partial(Require, 0)` | 要求 APK 中的 Baseline Profile 成功安装并做 `speed-profile` 编译 | Baseline Profile 回归闸门 |
| `Partial(Disable, N)` | 运行 N 次收集 profile，再做 `speed-profile` 编译 | 模拟由 workload 形成的 profile-guided 状态 |
| `None()` | 清除 profile/编译状态并测无预编译路径 | 编译状态下限；不等于清数据或全新安装 |
| `Full()` | `speed` 模式做完整 AOT 方法编译 | 降低 JIT 干扰的实验上限 |
| `Ignore()` | 不重置也不编译 | 只用于外部已精确控制 ART 状态的测试 |

下面的测试用于验证 APK 中的 Baseline Profile 能被安装。代码中的迭代数只演示参数位置，项目应通过试运行确定实际值：

```kotlin
@get:Rule
val benchmarkRule = MacrobenchmarkRule()

@Test
fun coldStartupWithRequiredBaselineProfile() {
    benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.Partial(
            baselineProfileMode = BaselineProfileMode.Require,
            warmupIterations = 0,
        ),
        iterations = 10,
        startupMode = StartupMode.COLD,
        setupBlock = { pressHome() },
    ) {
        startActivityAndWait()
        device.wait(Until.hasObject(By.res("com.example.app", "home_ready")), 5_000)
        check(device.hasObject(By.res("com.example.app", "home_ready")))
    }
}
```

`home_ready` 是该示例的业务完成断言。项目应替换为稳定的 resource ID 或可访问性条件，并把超时视为用例失败，不能让错误页或空页面进入启动统计。

`Partial(Require, warmupIterations > 0)` 会先安装 Baseline Profile，再运行 warmup 并再次做 profile-guided 编译。若要单独量化 Baseline Profile 与运行时 profile 的作用，使用不同测试分别配置，避免把两种 profile 混在一个结果里。

### 启动模式只控制进程与 Activity 状态

Macrobenchmark 的 `StartupMode` 控制启动前的进程/Activity 状态：

- `COLD`：测量前终止目标进程；
- `WARM`：保留进程，重新创建或启动 Activity；
- `HOT`：保留进程和 Activity，恢复到前台。

测试仍需控制数据、账号、缓存和入口 Intent。`setupBlock` 在每轮测量前运行；冷启动模式会在 setup 与 measure 之间终止进程，因此不能把必须留在目标进程内存中的准备工作放到 setup 后依赖。

## 排除规则与异常值

排除样本的条件必须在运行前定义，例如：

- 热状态门控失败；
- 目标页面断言失败；
- 设备发生系统更新、重启或充电状态变化；
- trace 缺失、metric 无样本或脚本未完成目标动作；
- 已识别的设备池故障。

观察到一个慢值后再以“可能遇到 GC”为由删除，会系统性美化结果。有效但很慢的样本应保留，并通过 trace 判断它是否属于用户路径。所有排除都要保存原因、原始记录和排除前后的样本量。

## 性能基线与回归检测

### 基线是一份版本化合同

基线至少绑定：

- 目标 Git SHA、APK/AAB 摘要和构建工具版本；
- Benchmark、AGP、Kotlin、R8 与 ProfileInstaller 版本；
- 设备序列、build fingerprint 和 ART Mainline 版本；
- workload、测试数据、编译模式、启动模式和迭代协议；
- 环境状态与排除规则；
- 原始 JSON、trace 和统计脚本版本。

只保存一个 median 数字，无法判断后续变化来自应用、设备、Benchmark 升级还是统计脚本。

### 同机配对与交错运行

候选版本和基线版本在同一设备上运行，能减少设备间差异。设备温度或后台活动随时间漂移时，可按 A/B/B/A 或随机顺序交错运行，而非跑完全部基线再跑全部候选。

配对比较要保留每个 block 的顺序、环境状态和两侧结果。对多台设备分别计算变化，再按设备层次汇总；不要把不同机型的原始毫秒直接放进一个总体样本池。

### 阈值来自 SLO 与噪声下限

固定“P50 回归 10%、P90 回归 20%”无法跨 workload 使用。回归判定通常需要同时满足：

1. 数据质量检查通过；
2. 候选版本超过产品或平台 SLO；
3. 相对基线的效应量超过该测试的历史噪声；
4. 置信区间或重复 job 支持同一方向；
5. 变化达到团队预先定义的工程意义。

样本量不足时，结果可标为 inconclusive，并自动增加独立运行或转人工复核。p-value 不能代替效应量；统计显著但工程幅度极小的变化，不一定需要阻断发布。

### 趋势与单次闸门并用

PR 闸门保护明确回归，长期趋势发现多次小幅累积。趋势面板应展示：

- 每个 reference device 的原始 run 与 median；
- 控制限或历史噪声带；
- Benchmark、系统镜像和设备维护事件；
- 基线切换点及原因；
- 数据缺失、排除和设备健康。

基线更新需要审批和迁移记录。新功能改变工作量时，可以建立新场景或新 SLO；不能通过移动基线隐藏已经发生的退化。

## 测试报告的撰写规范

### 报告必须支持复现和决策

建议按以下结构撰写：

1. 决策摘要：通过、阻断或证据不足，指出受影响场景；
2. 测试合同：工作负载、状态、设备、版本和统计协议；
3. 数据质量：样本量、排除、thermal、显示、供电和脚本断言；
4. 结果：基线、候选、绝对差、相对差、区间和 SLO；
5. 证据：JSON、每轮 trace、日志、构建摘要和关联变更；
6. 归因状态：已验证原因、待证实假设与下一项实验；
7. 处理人和复测条件。

结果表可使用以下列：

| Metric | Baseline | Candidate | Absolute delta | Relative delta | Uncertainty | SLO | Decision |
|---|---:|---:|---:|---:|---:|---:|---|

表中每一行都链接到原始 artifact。对 `StartupTimingMetric` 标明 min/median/max 与 run count；对 `FrameTimingMetric` 标明 percentile、frame count、API 版本及是否使用 `frameOverrunMs`。

### 报告不能把相关性写成根因

“候选版本更慢”是测量结果。“某次慢样本同时出现 GC”是相关证据。只有通过 trace、源码改动、对照实验或回滚验证后，才能写成已验证原因。

根因段落应区分：

- observation：稳定复现的现象；
- evidence：trace、日志、源码或对照结果；
- hypothesis：尚需实验验证的解释；
- decision：下一项实验或修复。

截图只作为辅助。报告还要保存可查询 trace、时间范围、process/thread 和 SQL/metric 定义，方便另一位工程师复核。

## 扩展：Macrobenchmark 在 CI 中的集成

### runner 与构建产物

Microbenchmark 使用 `androidx.benchmark.junit4.AndroidBenchmarkRunner`。Macrobenchmark 使用常规 `AndroidJUnitRunner`，目标 APK 与 test APK 分开构建。目标 variant 接近 release，不能用 debuggable 构建替代。

CI 至少归档：

- `*-benchmarkData.json`；
- 每个 Macrobenchmark measured iteration 的 `.perfetto-trace`；
- instrumentation stdout/stderr 与 logcat；
- 目标 APK、test APK 和摘要；
- 设备与环境 manifest；
- 统计与报告程序版本。

Gradle 会把额外测试输出复制到 `build/outputs/connected_android_test_additional_output/...`。目录层次随 module、variant 和工具版本变化，CI 应从任务输出或 artifact glob 定位，避免写死旧路径。

### 真机负责数值，模拟器负责流程

| 环境 | 适用任务 |
|---|---|
| 专用本地真机 | PR 闸门和高灵敏度趋势 |
| Firebase Test Lab 真机 | 设备覆盖、周期性趋势；先量化共享环境噪声 |
| 模拟器 / GMD | 安装、导航、断言、JSON/trace 产出 smoke test |

`androidx.benchmark.dryRunMode.enable=true` 可快速检查用例流程。dry run 和模拟器结果不能进入性能基线。

### 不要压掉关键错误

Macrobenchmark instrumentation arguments 支持 `androidx.benchmark.suppressErrors`，其中包括 `DEBUGGABLE`、`LOW-BATTERY`、`EMULATOR`、`NOT-PROFILEABLE` 和 `METHOD-TRACING-ENABLED`。这些条件都会改变可信度，正式闸门应修复环境，而非把错误降级为 warning。

CI 还要限制同一设备并发，定期运行固定 calibration workload，并在设备更换、电池老化、系统更新或 Benchmark 升级后重新建立噪声模型。

### JSON 的正确使用

Benchmark JSON 的 single metric 记录通常包含 `minimum`、`maximum`、`median` 与 `runs`；sampled metric 会保存从样本池计算的 percentiles。解析器应：

- 校验 schema 和 Benchmark 版本；
- 保留 `runs`，不只保存 median；
- 区分 single metric 与 sampled metric；
- 拒绝缺失或非有限值；
- 保存 `repeatIterations`、`warmupIterations` 与 context；
- 关联同一次测试生成的 trace 文件。

CI 自行计算 P90 或置信区间时，要固定插值方法和 bootstrap 参数，并给统计脚本单独做回归测试。

## 扩展：Firebase Performance Monitoring 的边界

Firebase Performance Monitoring（FPM）提供线上启动、网络和自定义 code trace。它适合观察真实用户版本趋势，无法替代受控设备上的合入前 benchmark。

### 当前 custom code trace 限制

当前官方文档给出的约束包括：

- trace name 最长 100 个字符，不能以下划线开头；
- metric name 最长 100 个字符；
- 每条 custom code trace 最多 32 个 metrics，包含默认 Duration；
- attribute name 最长 32 个字符，只允许规定字符；
- 每条 trace 最多 5 个 custom attributes；
- attribute 不得包含可识别个人的信息；
- 高频创建 trace 会增加资源开销，不应逐帧创建。

FPM 的服务端采样和聚合不由客户端按 benchmark 实验协议精确控制。它能按版本、设备、国家等维度分析，也提供 session 时间线，但 session 数据仍不等同于 Perfetto system trace。

### 延迟与报警

当前 FPM 文档把兼容 SDK 的处理描述为 near real-time，数据通常在采集后数分钟显示。SDK 首次检测、批量上传、离线设备和平台故障仍会造成额外延迟。发布报警要监控数据新鲜度与覆盖率，不能假设每条事件同步到达。

### 与其他数据源的分工

| 数据源 | 适合回答的问题 |
|---|---|
| Macrobenchmark / Microbenchmark | 候选改动在固定实验条件下是否回归 |
| Android Vitals | Play 用户的启动、渲染、ANR 等版本趋势 |
| FPM | 启动、网络与自定义 trace 的线上分群 |
| 自建遥测 | 自定义业务终点、采样与低延迟诊断 |
| Perfetto / ProfilingManager | 单个异常样本的系统级或进程级证据 |

实验室与线上数据出现差异时，先比较设备分布、入口、缓存、编译和指标定义。两个系统可能都正确，只是观测对象不同。

## 在 Perfetto 中复核 benchmark

Macrobenchmark 为每个 measured iteration 生成独立 Perfetto trace。它可用于检查：

- 启动：launch intent、进程创建、bindApplication、首帧与 `reportFullyDrawn()`；
- 帧：expected/actual FrameTimeline、主线程、RenderThread、GPU 与 SurfaceFlinger；
- 调度：线程运行、睡眠、抢占、CPU 迁移和频率；
- I/O 与 ART：dex2oat、JIT、GC、文件系统和 Binder；
- 测试动作：目标控件是否出现、滚动区间是否一致。

TTID 与 TTFD 必须分开。`StartupTimingMetric.timeToFullDisplayMs` 依赖应用调用 `reportFullyDrawn()`，Android 10（API 29）及以下还可能不可用。

帧回归不要用 `DrawFrame > 16 ms` 做统一判定。动态刷新率和流水线 deadline 会变化；API 31+ 用 `frameOverrunMs` 与 FrameTimeline 判断 miss，再定位 App、GPU 或合成阶段。`DrawFrame` 只是流水线中的切片。

trace 与结果不一致时，依次检查 metric 语义、测量范围、应用断言、编译/启动模式和环境。后台 I/O 只是可能原因之一，需要 trace 证据后再写入结论。

## 常见误区

- 只测一次，把偶然结果写成基线。
- 用模拟器数值阻断真机性能回归。
- 将 `StartupMode.COLD` 解释为清数据或全新安装。
- 将 `CompilationMode.None()` 解释为冷缓存用户状态。
- 把 `Partial.warmupIterations` 当成普通测量预热。
- 用十次启动的 P90 代表线上用户 P90。
- 把 `FrameTimingMetric` 的帧 percentile 与启动 run percentile 混为一谈。
- 关闭动画、网络或定位后，却声称测量生产 workload。
- 用 thermal status override 隐藏真实降频。
- 对 Macrobenchmark 写死 CPU0 sysfs 频率。
- 启用 `--disable` 后忘记恢复后台 dexopt。
- 观察慢样本后删除“异常值”。
- 用固定百分比阈值覆盖所有指标。
- 只保存 median，不保存 runs 与 trace。
- 用相关事件直接下根因结论。

## 与其他章节的关系

- §5.5 解释 Thermal HAL、framework 状态与设备降频。
- §8.3 定义冷、温、热启动及优化路径。
- §13.2 介绍 Perfetto 抓取与实验配置。
- §14.9 介绍 Android 自动化性能工具与 Macrobenchmark 回归门禁。
- §15.3 定义指标合同、SLO 和统计方向。
- §15.5 说明线上采样、聚合与报警。

## 参考资料

### Android 官方

- [Benchmark your app](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [Benchmark in Continuous Integration](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Capture Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Macrobenchmark instrumentation arguments](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-instrumentation-args)
- [Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview)
- [CompilationMode](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode)
- [AndroidX Benchmark releases](https://developer.android.com/jetpack/androidx/releases/benchmark)

### Firebase 官方

- [Custom code traces](https://firebase.google.com/docs/perf-mon/custom-code-traces)
- [Performance Monitoring troubleshooting](https://firebase.google.com/docs/perf-mon/troubleshooting)

### AOSP android-17.0.0_r1

- `frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java`
- `frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java`
- `frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java`
- `art/libartservice/service/java/com/android/server/art/ArtShellCommand.java`
- `art/libartservice/service/java/com/android/server/art/BackgroundDexoptJob.java`
- `art/libartservice/service/java/com/android/server/art/BackgroundDexoptJobService.java`
- `art/libartservice/service/java/com/android/server/art/ArtManagerLocal.java`

### AndroidX 源码

- `androidx-main/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/CompilationMode.kt`
- `androidx-main/benchmark/benchmark-junit4/src/main/java/androidx/benchmark/junit4/SideEffectRunListener.kt`
