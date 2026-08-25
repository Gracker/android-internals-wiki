---
applicable_versions: Android 6.0 (API 23) – Android 17 (API 37)
chapter: '14.6'
confidence: medium
last_verified: '2026-08-13'
last_verified_against: AndroidX Benchmark 1.4.1 stable + UI Automator 2.4.0 stable + Android test docs + Android 17 / API 37 + android-17.0.0_r1
related_chapters:
- '21.4'
- '13.7'
- '15.3'
- '15.5'
- '13.9'
- '14.1'
- '14.13'
- '22.7'
section: '14.6'
sources:
- type: official
  path: developer.android.com/topic/performance/benchmarking
- type: official
  path: developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: developer.android.com/topic/performance/benchmarking/microbenchmark-overview
- type: official
  path: developer.android.com/topic/performance/benchmarking/benchmarking-in-ci
- type: official
  path: developer.android.com/training/testing/ui-automator
- type: official
  path: developer.android.com/training/testing/ui-testing/espresso
- type: official
  path: https://developer.android.com/tools/agents/android-cli
- type: official
  path: https://developer.android.com/tools/agents/android-cli/journeys
- type: official
  path: https://developer.android.com/tools/agents/android-skills
- type: official
  path: https://developer.android.com/android-performance-analyzer
- type: official
  path: https://developer.android.com/studio/profile
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: https://developer.android.com/about/versions/17/setup-sdk
- type: official
  path: https://perfetto.dev/docs/
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h
- type: blog
  path: https://android-developers.googleblog.com/2026/05/android-cli-stable-1-0-agent-development.html
- type: blog
  path: https://android-developers.googleblog.com/2026/05/whats-new-android-developer-tools.html
- type: blog
  path: intake/daily-info/2026-05-21.md
status: finalized
tags:
- android
- benchmark
- macrobenchmark
- microbenchmark
- ci-cd
- performance-testing
- android-cli
- agent
- performance-tooling
- android-studio
- perfetto
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
title: 自动化性能测试与 CLI Agent 工作流
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part3-tools/ch14-other-tools/09-automation-tools.md
- src/part3-tools/ch14-other-tools/14-android-cli-agent-performance-workflow.md
---

# 自动化性能测试与 CLI Agent 工作流

自动化性能测试需要固定设备状态、场景、采集配置、统计口径和失败证据。CLI 与 Agent 可以编排这些步骤，但每个判断仍应返回命令、Trace、日志或测试结果。

## 场景、基线、重复测量与回归门禁

### 为什么要用自动化工具做性能测试

Perfetto、Android Studio Profiler 适合回答“时间花在哪里”，自动化基准测试负责回答“从哪次改动开始变慢”。Trace 是带时间戳的性能事件记录。一次手工 Trace 可以定位问题，却很难在每次提交后按相同条件重放启动、滚动或热点函数。

Jetpack Benchmark 把场景、编译状态、重复次数和产物格式写进测试代码。持续集成（CI）系统因此可以保存每次运行的 JSON 结构化结果与 Perfetto Trace，并把本次数据与同一设备上的历史数据比较。自动执行只解决了重复性；构建类型、设备温度、系统版本、编译模式和操作边界仍要固定，否则得到的主要是设备波动。

### Macrobenchmark 与 Microbenchmark：两种层次，两种用途

两套库的区别集中在进程边界和测量对象：

APK 是 Android 应用或测试程序的安装包。AOT（Ahead-of-Time）在运行前将字节码编译为机器码，JIT（Just-in-Time）则在运行期间编译热点代码。

| 维度 | Macrobenchmark | Microbenchmark |
|---|---|---|
| 测量范围 | 启动、滚动、动画等完整用户场景 | 可直接调用的函数、算法或一小段 UI 代码 |
| 运行位置 | 测试 APK 在目标应用进程之外驱动场景 | 被测代码在基准测试进程内循环执行 |
| 编译控制 | 可选择 `DEFAULT`、`Full`、`Partial`、`None`、`Ignore` | AndroidX Benchmark Gradle 插件可对基准测试 APK 做全量 AOT |
| 主要产物 | 指标 JSON；每个测量迭代一份系统 Trace | 指标 JSON 与最小系统 Trace；采集条件允许时默认再生成方法 Trace |
| 适合回答 | 一次交互整体是否回归，慢在哪个系统阶段 | 某个热点实现是否更快，分配是否减少 |

#### Macrobenchmark：端到端的用户体验测量

Macrobenchmark 从目标应用外部启动 Activity、注入手势并采集系统 Trace，适合测量启动、滚动和动画等完整交互。测试代码必须放在独立的 `com.android.test` 模块中。目标 APK 应使用接近 release 的非 debuggable 构建，并保留 R8 代码压缩和优化。Manifest 中的 `<profileable>` 让 shell 可以对非 debuggable 应用进行低干扰 Trace 采集。

入口是 `MacrobenchmarkRule.measureRepeated()`。`setupBlock` 把应用放到一致的初始状态，`measureBlock` 定义计入测量的操作。iteration 是同一次测试启动中的一次重复测量；一次 `measureRepeated()` 会执行多个 iteration，并为每个测量 iteration 保存一份系统 Trace。

`StartupTimingMetric` 的汇总值是 min、median、max；`FrameTimingMetric` 输出 P50、P90、P95、P99。P90 表示 90% 的样本不超过该值，其余分位数同理。不能把这些结果概括成“重复 N 次取平均值”。

常用指标及其边界如下：

| 指标 | 版本边界 | 读法 |
|---|---|---|
| `StartupTimingMetric` | Macrobenchmark 支持 API 23+；`timeToFullDisplayMs` 在 API 29 及以下可能不可用 | TTID（Time to Initial Display）对应首帧；TTFD（Time to Full Display）依赖应用在主要内容就绪后调用 `reportFullyDrawn()` |
| `FrameTimingMetric` | `frameOverrunMs` 仅 API 31+ | 正值表示超过该帧 deadline（应完成时间）；`frameDurationCpuMs` 表示 UI 线程与 RenderThread 生成一帧所用的 CPU 时间 |
| `TraceSectionMetric` | 实验 API；依赖 Trace 中存在同名 section | section 是应用写入 Trace 的命名时间片；默认只查目标包，并选取测量区间内首次匹配 |
| `PowerMetric` | 实验 API，最低 API 29 | 高精度 power/energy 是系统总量，依赖设备 power rail（硬件供电通路）；官方限定 Pixel 6、Pixel 6 Pro 及更新机型 |

`PowerMetric` 还提供电池电量差值类型，精度低于 power rail。无论选择哪一种，功耗结果都不能直接归因于单个应用。测试进程、系统服务、屏幕和网络活动都会进入系统总量。[AndroidX 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-main/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/Metric.kt) 对 `PowerMetric` 标注了 `@RequiresApi(29)`，并提供 `deviceSupportsHighPrecisionTracking()` 检查设备能力。

#### Microbenchmark：代码级热点分析

Microbenchmark 直接循环调用被测代码，适合 JSON 解析、数据转换、布局 inflate（从 XML 创建 View）、`RecyclerView` item 绑定等高频 CPU 路径。循环会形成预热缓存和稳定代码路径，因此结果接近热点代码的最佳情况。磁盘首次读取、只运行一次的初始化、跨进程交互通常不适合用它单独判断。

下面的测试演示如何测量解析函数，并用 `BlackHole.consume()` 防止死代码删除，即避免 Kotlin 编译器或 R8 把没有外部用途的计算整段删掉。

```kotlin
// 省略 import；类位于 microbenchmark 模块的 androidTest 源集。
@RunWith(AndroidJUnit4::class)
class JsonBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    @Test
    fun measureJsonParsing() = benchmarkRule.measureRepeated {
        val result = parseJson(largeJsonInput)
        BlackHole.consume(result)
    }
}
```

`measureRepeated` 负责预热、循环次数和计时，报告执行时间与分配次数。AGP 是 Android Gradle Plugin。Benchmark 1.3.0-beta01+ 配合 AGP 8.4.0+ 时，`androidx.benchmark` 插件默认对 Microbenchmark APK 做全量 AOT。需要观察 JIT 行为时，可在 `gradle.properties` 中设置 `androidx.benchmark.forceaotcompilation=false`。

准备输入数据或重置容器时，应把不参与测量的部分放进 `runWithMeasurementDisabled {}`。旧名 `runWithTimingDisabled {}` 在 Benchmark 1.4.0 已弃用，因为该方法暂停的不只是计时。

#### 什么时候用哪个？

完整交互选 Macrobenchmark，能独立调用的热点选 Microbenchmark。两者常按这条证据路径配合：

1. Macrobenchmark 记录启动或滚动回归，并保留对应 Trace。
2. Perfetto 把耗时定位到一个可隔离的函数或阶段。
3. Microbenchmark 比较候选实现，确认局部变化。
4. Macrobenchmark 回到原场景，确认端到端指标与 Trace 都得到改善。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`；Macrobenchmark 最低支持 API 23，`frameOverrunMs` 属于 API 31+ 指标，`PowerMetric` 最低支持 API 29。

### 使用 Macrobenchmark 测量启动时间和滑动帧率

#### 测量启动时间

Baseline Profile 是应用交给 ART 的预编译方法与类列表。这段测试测量 Baseline Profile 可用时的冷启动，代码主体省略了 import：

```kotlin
// 省略 import；替换为被测应用的真实包名。
@LargeTest
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartup() = benchmarkRule.measureRepeated(
        packageName = "com.example.myapp",
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.Partial(),
        iterations = 10,
        startupMode = StartupMode.COLD,
        setupBlock = {
            pressHome()
        }
    ) {
        startActivityAndWait()
    }
}
```

`StartupMode.COLD` 会在 `setupBlock` 与 `measureBlock` 之间终止目标进程，测试无需自行执行 `force-stop`。`pressHome()` 固定启动前的可见界面，`startActivityAndWait()` 发出启动 Intent 并等待 Activity 首帧。`iterations = 10` 只是该场景的采样配置；应根据本机测量波动和 CI 时长调整，不能把 10 次当成通用门槛。

`StartupTimingMetric` 输出 `timeToInitialDisplayMs` 和 `timeToFullDisplayMs`。前者从系统收到启动 Intent 计到目标 Activity 首帧；后者计到应用调用 `reportFullyDrawn()` 后的首个完整帧。应用未调用该 API 时没有可解释的 TTFD，API 29 及以下还可能无法提供该字段。报告比较以 median（中位数）为主，同时保留 min、max 和单次 Trace。

`StartupMode` 提供 `COLD`、`WARM`、`HOT`。三种模式改变启动前的进程和 Activity 状态，不能混在一条趋势曲线中。测试名称、JSON 基线和告警规则都应带上启动模式。

#### 测量滑动帧率

滚动测试要把页面准备放进 `setupBlock`，把手势及其产生的帧留在 `measureBlock`。下面的主体代码使用 UI Automator 的稳定 API：

```kotlin
@Test
fun scrollList() = benchmarkRule.measureRepeated(
    packageName = "com.example.myapp",
    metrics = listOf(FrameTimingMetric()),
    compilationMode = CompilationMode.Partial(),
    iterations = 10,
    setupBlock = {
        killProcess()
        startActivityAndWait()
        check(
            device.wait(
                Until.hasObject(By.res("com.example.myapp", "recycler_list")),
                5_000
            )
        )
    }
) {
    val list = requireNotNull(
        device.findObject(By.res("com.example.myapp", "recycler_list"))
    )
    list.setGestureMargin(device.displayWidth / 5)
    list.fling(Direction.DOWN)
}
```

`killProcess()` 与重新启动发生在测量区间之外，用来让每次迭代都从列表初始位置开始。`check` 让页面未准备好时直接失败，避免“没有找到列表但测试仍通过”。`setGestureMargin()` 避开系统返回手势区域，`fling()` 产生可重复的滚动输入。若业务场景要求固定距离，可改用 `swipe()`，并把方向、速度、距离和列表初始位置写成稳定条件。

`FrameTimingMetric` 报告 P50、P90、P95、P99。API 31+ 的 `frameOverrunMs` 使用系统为每一帧计算的 deadline，适用于 60 Hz、高刷新率和可变刷新率设备；正值表示超期，负值表示仍有余量。`frameDurationCpuMs` 只描述 UI 线程与 RenderThread 生成帧的 CPU 时间。GPU 等待和合成问题仍要回到 FrameTimeline（系统记录的预期帧与实际帧时序）与系统 Trace 判断。

#### CompilationMode：量化编译优化效果

下面列出常用编译模式，重点看 `DEFAULT` 与 `Ignore` 的边界：

```kotlin
// 使用库的默认策略。
CompilationMode.DEFAULT

// 清除已编译代码和 profile，运行期间可继续产生 JIT 编译。
CompilationMode.None()

// 安装 Baseline Profile，并可按配置执行 warmup。
CompilationMode.Partial()

// 缺少 Baseline Profile 时让测试失败。
CompilationMode.Partial(
    baselineProfileMode = BaselineProfileMode.Require
)

// 对目标 APK 做全量 AOT。
CompilationMode.Full()

// 保留设备当前编译状态，不执行重置或编译。
CompilationMode.Ignore()
```

`DEFAULT` 在 API 24+ 尝试安装 APK 中的 Baseline Profile；API 23 按系统默认行为做全量编译。`Partial()` 用于观察 profile 覆盖后的状态，`None()` 用于观察无预编译的状态，`Full()` 适合研究全量 AOT 上限。

`Ignore()` 不修改已有状态，适合由外部脚本精确控制 ART 编译的场景。当前 `Ignore()` 带有 `ExperimentalMacrobenchmarkApi` 标记，调用处需用 opt-in 显式确认实验 API。

Android 14（API 34）起，Macrobenchmark 可以在重置编译状态时保留应用数据；更低版本常需要重装 APK。测试必须保留登录态或预置数据时，优先使用 API 34—37 的固定设备；旧设备可由外部脚本管理编译，再选 `CompilationMode.Ignore()`。

Baseline Profile 收益应由同一 APK、同一设备、同一启动模式下的 `None()` 与 `Partial()` 实测得出。跨项目引用“提升约 30%”无法替代本应用数据。

### adb shell am instrument：性能测试的命令行入口

Gradle、Android Studio 和云设备平台最终都要启动 instrumentation。instrumentation 是 Android 的系统测试机制：系统启动测试 APK 中的 runner，并为它建立测试连接。ADB（Android Debug Bridge）下最直接的入口是 `am instrument`，基本语法如下：

```bash
adb shell am instrument -w <test_package>/<runner_class>
```

`<test_package>/<runner_class>` 是测试 APK Manifest（应用组件声明文件）中注册的 instrumentation 组件。runner 是发现并执行测试的入口类，`-w` 让 ADB 客户端等待测试结束并打印状态。Macrobenchmark 使用常规 `AndroidJUnitRunner`，下面只执行一个测试方法：

```bash
adb shell am instrument -w \
  -e class com.example.macrobenchmark.StartupBenchmark#coldStartup \
  com.example.macrobenchmark/androidx.test.runner.AndroidJUnitRunner
```

`-e class` 会写入 instrumentation 的参数 `Bundle`，即一组键值对，由 `AndroidJUnitRunner` 解释为测试过滤条件。Microbenchmark 的组件 runner 则是 `androidx.benchmark.junit4.AndroidBenchmarkRunner`，两者不能照抄。

本地运行整个 Macrobenchmark 模块或单个方法，可让 Gradle 负责构建、安装、执行和拉取产物：

```bash
./gradlew :macrobenchmark:connectedCheck

./gradlew :macrobenchmark:connectedCheck \
  -Pandroid.testInstrumentationRunnerArguments.class=\
com.example.macrobenchmark.StartupBenchmark#coldStartup
```

`connectedCheck` 是 Gradle 的连机测试任务，会负责构建、安装和执行，再把 JSON 与 Trace 拉到主机。CI 拆分构建和设备执行时，才需要显式安装两个 APK 并调用 `am instrument`。

Benchmark 常用参数由测试库解释，不属于 `am` 内建选项：

- `-e class 包名.类名#方法名`：由 runner 过滤测试。
- `-e androidx.benchmark.dryRunMode.enable true`：把基准缩成一次循环，不预热、不保存测量或 Trace，只用于验证脚本和配置。
- `-e androidx.benchmark.iterations N`：覆盖 Microbenchmark 的 measurement 数，每次 measurement 内部仍可根据预热时长运行多个循环；Macrobenchmark 的 iteration 数由测试代码中的 `measureRepeated` 参数定义。
- `-e androidx.benchmark.suppressErrors 错误名`：把指定配置错误降为警告。带错误前缀的结果只适合诊断，不能进入基线。
- `-e additionalTestOutputDir 路径`：为直接 ADB 或云设备运行指定可写的产物目录。

Benchmark 1.1.0 之前需要用 `androidx.benchmark.output.enable=true` 手动开启 JSON；当前版本默认输出，无需继续携带这个历史参数。

Android 17 源码中，[`Instrument`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/cmds/am/src/com/android/commands/am/Instrument.java) 解析 `-w`、`-e`、用户、ABI 等参数。ABI（Application Binary Interface）指 APK 中 native 代码面向的 CPU 架构与二进制接口。解析后，`Instrument` 调用 Binder 接口 `IActivityManager.startInstrumentation()`。

[`ActivityManagerShellCommand`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java) 的帮助文本也明确区分了 `am instrument` 入口。平台这一层只负责启动和传递参数，指标含义由 AndroidX Benchmark 决定。

### UI Automator 与 Espresso：在性能测试中的角色

UI Automator 负责从应用进程外驱动完整场景；Espresso 负责在应用 instrumentation 环境中做功能断言。前者视角更接近用户，后者可访问目标应用内部的 View 和同步状态。它们的同步方式和测量边界不同。

#### UI Automator：Macrobenchmark 的底层驱动

UI Automator 可以检查用户应用和系统应用的 accessibility node（无障碍服务看到的 UI 结构节点）、注入输入并跨窗口操作。它不要求目标应用链接测试代码，因而可以驱动保留 release 优化的 APK，也能处理权限弹窗、桌面和系统设置。

Android 17 的 [`UiAutomation`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/UiAutomation.java) 被平台定义为一种特殊的 `AccessibilityService` 客户端；`am instrument` 创建 `UiAutomationConnection` 并把它交给 instrumentation。这里没有要求用户安装或常驻启用一个普通无障碍服务。UI Automator 在测试进程中通过这条系统连接读取节点和注入手势。

测试进程与目标应用进程分离，可以避免把驱动代码计入目标进程的堆和调用栈。它们仍共享 CPU、内存带宽、Binder 服务和内核调度资源。节点查询与输入注入也会产生 IPC（跨进程通信）开销。降低扰动的方法是把页面查找、登录和数据准备放入 `setupBlock`，在 `measureBlock` 中只保留固定输入和必要等待。

UI Automator 2.4.0 已于 2026 年 7 月 1 日稳定发布。它引入了 `uiAutomator {}`、`onElement {}`、`waitForAppToBeVisible()` 等 Kotlin DSL（针对测试场景设计的 Kotlin 调用语法），并加入内置等待、应用状态管理和截图能力。

已有 Macrobenchmark 使用 `UiDevice`、`By`、`Until` 的代码仍可维护，不必为了语法变化改写已经稳定的场景。

#### Espresso：用于白盒验证，不用于性能测量

Espresso 是白盒测试工具，即测试可以访问目标应用内部的 View 和同步状态。每次 `onView()` 操作前，它会等待需要处理的消息队列、`AsyncTask` 和已注册 `IdlingResource` 进入空闲状态。`IdlingResource` 是业务或组件向 Espresso 报告“已空闲”的同步接口。这个模型适合验证点击后的 View 状态，也适合确认性能优化没有破坏功能。

同步等待会改变输入时序，matcher（判定 View 是否符合条件的匹配器）与其他测试代码还会进入目标进程的 CPU、内存和调度数据。用 Espresso 包围一段操作再读取墙钟时间（真实经过时间），测到的会同时包含框架同步、断言和应用工作，不能替代 Macrobenchmark 指标。

工程上可把 Espresso 用例放在提交验证阶段，把 Macrobenchmark 放在固定设备阶段：前者验证页面可用，后者测量完整交互。失败证据也不同，Espresso 看断言与截图，Macrobenchmark 看 JSON 与 Trace。

#### 不能混用的地方

Macrobenchmark 的自 instrumentation 测试 APK 运行在目标应用进程之外，无法把 Espresso 的 `onView()` 当作目标应用内 matcher 使用。跨应用操作、权限弹窗和系统界面统一交给 UI Automator。目标应用内部必须暴露“主要内容已就绪”这类语义时，可调用 `reportFullyDrawn()` 或写自定义 Trace section，再由 Macrobenchmark 从 Trace 读取。Espresso 驱动不应放进 `measureBlock`。

### Monkey、SoloPi 与 Appium：自动化工具的另一类用途

基准测试负责回答“这次改动是否让指标变差”。稳定性和专项测试工具负责覆盖长时间运行、随机输入、跨端脚本这些场景。

#### Monkey：低成本压力测试

`Monkey` 在设备端生成伪随机点击、滑动、按键和系统事件，适合在夜间任务中发现崩溃与 ANR（Application Not Responding，应用无响应）。seed 是伪随机数生成器的初始值；固定 seed 可以重放相同事件序列，但页面数据、网络响应和系统弹窗仍可能让后续路径分叉。

这条命令把事件限制在单个包中，固定 seed，并监控 native crash：

```bash
adb shell monkey -p com.example.app \
  -s 20260730 \
  --pct-touch 60 --pct-motion 20 \
  --throttle 200 \
  --monitor-native-crashes \
  -v 10000
```

`10000` 是事件数，`--throttle 200` 在事件之间加入 200 ms 间隔。`--monitor-native-crashes` 额外监视 C/C++ 等 native 代码崩溃。复查现场时应保留命令、seed、应用与系统版本、logcat 日志、bugreport 诊断包与 tombstone（native 崩溃报告）。Monkey 没有固定业务边界，也不控制编译和设备状态，因此不能用于启动耗时或帧时间回归判定。

#### SoloPi：专项性能脚本和视觉拆帧

SoloPi 提供录制回放、CPU / 内存 / FPS（每秒帧数）性能面板和启动耗时辅助工具，适合线下走查与测试同学复现长流程。它的开源仓库构建说明仍以 Target API 29、Gradle 6.1.1 与 NDK 16 为基准。NDK 是 Android 的 C/C++ 开发工具集。接入 Android 17 设备前要单独验证权限、无线调试、无障碍节点和厂商系统兼容性。SoloPi 的面板数据可用于发现异常区间，发布门禁仍应使用可追溯的 Benchmark JSON 与 Trace。

#### Appium：跨端自动化，不负责指标可信度

Appium 3 是基于 W3C WebDriver 的模块化自动化框架。W3C WebDriver 定义查找元素、点击和创建会话等标准命令，driver 则把这些命令转换为 Android、iOS 等平台的操作。这套架构适合统一 Android、iOS、WebView 和桌面端的业务脚本。

WebDriver 服务、driver、设备自动化后端和显式/隐式等待都会影响输入时序。Appium 负责场景编排时，性能指标仍应由设备侧 Macrobenchmark、Perfetto 或明确的系统 counter（计数器读数）采集。

### 性能自动化测试的 CI/CD 集成方案

CI/CD 分别指持续集成与持续交付/部署。可靠的性能 CI 要同时保存代码版本、APK、测试 APK、设备指纹、Benchmark JSON 和 Trace。缺少其中任一项，回归曲线都很难复查。

#### 基本架构

一条可维护的流水线分为构建、设备准备、执行、产物收集和回归判定五个阶段。

**构建阶段**需要生成目标 APK 与测试 APK。build variant（构建变体）是 build type 与可选 product flavor 的一种组合。目标应用采用接近 release 的 `benchmark` 变体：关闭 debuggable，保留 R8 与资源压缩配置，只把签名换成 CI 可用的密钥。下面是应用模块的基础配置：

```kotlin
// app/build.gradle.kts
buildTypes {
    getByName("release") {
        isMinifyEnabled = true
        isShrinkResources = true
        proguardFiles(
            getDefaultProguardFile("proguard-android-optimize.txt"),
            "proguard-rules.pro"
        )
    }

    create("benchmark") {
        initWith(getByName("release"))
        signingConfig = signingConfigs.getByName("debug")
        matchingFallbacks += listOf("release")
    }
}
```

`matchingFallbacks` 在依赖模块没有同名 `benchmark` 变体时，允许 Gradle 回退选择 `release`；单模块项目不一定需要。目标 APK 还要包含 `<profileable>`，并按当前 Macrobenchmark 文档接入 ProfileInstaller 1.3 或更新版本。ProfileInstaller 可帮助测试环境把 APK 携带的 Baseline Profile 安装到设备上。

**设备准备阶段**固定型号、Android build fingerprint（唯一标识系统构建的字符串）、电量区间、充电方式、网络、屏幕亮度、刷新率、账号与后台应用。AndroidX Benchmark 会检查低电量、模拟器、debuggable 等配置错误，也会在 Microbenchmark 中检测热降频并暂停等待冷却。已获取 root 管理员权限的 Microbenchmark 设备可用 `lockClocks` 锁定 CPU 频率；面向用户体验的 Macrobenchmark 不使用这项方案。

**执行阶段**按用途分层：

- PR 冒烟：PR 是 Pull Request，冒烟测试是用最小成本确认主流程能运行。使用 `dryRunMode` 或只运行少量场景，目标是发现构建、安装、权限和元素定位错误。
- 夜间趋势：固定少量物理设备，运行完整迭代并保存全部产物。
- 发布候选：在固定趋势设备之外增加一组机型，用于发现厂商系统或屏幕配置相关问题。

模拟器适合 PR 阶段验证脚本能否执行。Benchmark 会把模拟器判为配置错误；即使通过 `suppressErrors` 继续运行，产物也只能用于诊断，不能写入物理设备的性能基线。

**产物收集阶段**保存 JSON 与 `.perfetto-trace`，并把 Git commit、目标 APK 哈希、测试 APK 哈希和设备指纹写入同一次运行记录。哈希是由文件内容计算的固定长度摘要，用来确认实际测量的 APK。Macrobenchmark 每个测量 iteration 一份系统 Trace。Microbenchmark 默认生成最小系统 Trace；是否额外生成方法 Trace，还取决于 profiling 配置，以及当前系统能否在不影响后续测量的情况下采集。

**回归判定阶段**比较同名测试、同名指标、同一启动/编译模式和同类设备。启动看 median，帧指标看 P50 与尾部分位，功耗看设备是否支持对应数据源。阈值应从该设备的历史方差（数据波动幅度）与业务预算推导，不能给所有项目套一个固定百分比。

#### Firebase Test Lab 与 GitHub Actions

Firebase Test Lab（FTL）是 Google Cloud 的设备测试服务，可以运行 instrumentation APK，并把指定目录收集到 Cloud Storage 对象存储。可用设备与系统组合会变化，提交测试前先查当前目录：

```bash
gcloud firebase test android models list
gcloud firebase test android models describe <MODEL_ID>
gcloud firebase test android versions list
```

命令输出会标明型号、可用 OS、ABI 以及物理/虚拟类型。性能趋势应固定物理型号和 OS。云端每次可能分配同型号的不同设备实例，因此要保留设备上下文，并用多次运行估计波动。

下面的 GitHub Actions 片段省略了项目专属的权限与路径过滤，只展示构建和 FTL 提交方式：

```yaml
name: Performance Benchmark

on:
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Build APKs
        run: ./gradlew :app:assembleBenchmark :macrobenchmark:assembleBenchmark

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Run Macrobenchmarks on FTL
        env:
          APP_APK: app/build/outputs/apk/benchmark/app-benchmark.apk
          TEST_APK: macrobenchmark/build/outputs/apk/benchmark/macrobenchmark-benchmark.apk
        run: |
          gcloud firebase test android run \
            --type instrumentation \
            --app "$APP_APK" \
            --test "$TEST_APK" \
            --device model="${{ vars.FTL_MODEL }}",version="${{ vars.FTL_VERSION }}",locale=en,orientation=portrait \
            --directories-to-pull /sdcard/Download \
            --results-bucket "gs://${{ secrets.BENCHMARK_BUCKET }}" \
            --environment-variables clearPackageData=true,additionalTestOutputDir=/sdcard/Download,no-isolated-storage=true,androidx.benchmark.enabledRules=Macrobenchmark \
            --timeout 30m
```

APK 文件名会随 product flavor、AGP 和项目配置变化，`APP_APK`、`TEST_APK` 必须按构建产物调整。`additionalTestOutputDir` 把产物写到 `/sdcard/Download`，`--directories-to-pull` 再让 FTL 把该目录收集到结果 bucket（Cloud Storage 存储桶）。

`androidx.benchmark.enabledRules=Macrobenchmark` 只启用 Macrobenchmark 规则，避免同一模块中的 Baseline Profile 规则混入本轮。`no-isolated-storage=true` 临时让 instrumentation 测试跳出 Android 10+ 的默认存储沙箱，以便写入全局目录。

该参数会改变整场测试的存储行为，所以这次运行不能同时用来验证 scoped storage 兼容性。

Google 的 [performance-samples FTL workflow](https://github.com/android/performance-samples/blob/main/.github/workflows/firebase_test_lab.yml) 可作为完整参考。不要用 `bucket/latest/*.json` 猜测结果路径。应读取本次 gcloud 返回的 test matrix（这次测试的设备与配置组合）信息，或由 Cloud Storage 事件处理对应结果目录。

#### 结果持久化与趋势追踪

JSON 的 `context` 包含设备型号、build fingerprint 和 CPU 等运行上下文。写入趋势数据库时，要把这些上下文与测试名、参数、指标数组一起保存，不能只取一个 median 数字。设备重刷系统、Benchmark 库升级、编译模式变化或 Baseline Profile 更新时，应建立新基线，避免把环境迁移显示成代码回归。

告警可同时使用“相对近期稳定窗口”与“绝对体验预算”。前者比较近期多次稳定运行，用来发现小幅持续退化；后者是业务能接受的最大耗时或功耗，可防止历史基线本身已经过慢。命中告警后查看对应 iteration 的 Trace；只靠百分比无法区分应用回归、温度变化、系统任务和云设备实例差异。

Android 17 的平台分析锚点是 `android-17.0.0_r1`，通用内核源码可对照 [`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)。量产设备通常还包含厂商内核提交、调频策略和 thermal（温控）配置，所以同为 API 37 也不能直接合并结果。趋势库必须以设备 build fingerprint 分组。

#### 门禁统计与测量波动

不同指标使用不同摘要：启动以 median 为主并保留每次 iteration 值；帧指标查看 `frameOverrunMs` 的 p90/p95/p99 并保留慢帧 Trace；自定义 section 要明确取出现次数（count）、总时长（sum）还是首次匹配（first）；功耗只做同机、稳定窗口的系统级 A/B。

benchmark invocation 是一次完整的基准测试调用或进程启动。同一 invocation 内的多个 iteration 共享温度、缓存和后台状态，它们有相关性，不能当作多个独立设备样本。

AndroidX JSON schema（字段与类型约定）会随库版本扩展。门禁前先把原始结果转换为内部稳定结构，并校验 benchmark 名、metric 名、unit、device/build fingerprint、compilation mode、iteration 数、APK hash 和实验区组。实验区组是把同一设备、系统与环境条件下的运行归为一组。字段缺失时中止比较，不把缺失值当成 0。

稳定门禁可采用配对设计：在同一设备和环境区组内，分别运行 baseline（参考构建）与 candidate（候选构建），交替或随机安排顺序。每次 invocation 先形成一个摘要，再将环境接近的 baseline/candidate 摘要组成一对。

预算同时包含业务定义的绝对增量和相对增量。样本不足时拒绝比较；若置信区间（根据样本估计的效果可能范围）跨越门槛，则标为 inconclusive（证据不足），待设备冷却后补充独立配对。重复抽样同一 invocation 的 iteration 不会产生新的独立样本。

波动控制至少记录电量与充电状态、thermal、CPU frequency/idle（频率/空闲状态）、刷新率、后台账号与每轮时间。若后半段随温度单调变慢，应停止并冷却设备。网络使用固定离线数据、测试服务器或录制响应，账号、缓存、A/B flag（分组实验开关）和列表内容都要固定。

`StartupMode.COLD` 会停止目标进程，默认配置还可能清理 shader cache（GPU 着色器编译缓存），并请求系统清理 page cache（内核的文件页缓存）。这不代表设备重启后的所有缓存状态。DNS 域名解析、GPU 驱动、系统服务和业务数据缓存各有生命周期。page cache 清理影响整机，同一性能设备上不要并行运行其他任务，也不要在外层脚本重复清理。

指标退化后，找到 candidate 的异常 iteration 及同设备 baseline，按相同 journey（完整用户操作路径）边界比较 Trace。启动检查 process start、Binder、class load（类加载）、GC（垃圾回收）、I/O（输入/输出）和首帧。帧问题检查 FrameTimeline、UI thread、RenderThread、GPU 与 SurfaceFlinger（系统显示合成服务）。

最后用版本固定的 Trace Processor SQL 查询量化同一时间窗。门禁负责发现回归，Trace 负责解释原因。

### 在 Perfetto 中的表现

Gradle 执行成功后，JSON 与 Trace 会被拉到模块构建目录。下面是当前官方文档给出的主机路径：

```text
project_root/module/build/outputs/connected_android_test_additional_output/debugAndroidTest/connected/device_id/
```

`module` 是 Macrobenchmark 或 Microbenchmark 模块名，`device_id` 由 Gradle 按设备生成。Macrobenchmark 目录中每个测量 iteration 各有一份 `.perfetto-trace`，文件名包含测试、参数与 iteration 编号。

启动 Trace 的阅读顺序可以固定为：

1. 在 App Startups 或启动相关 slice（Trace 中带起止时间的事件片段）中确认 launch、TTID、TTFD 边界。
2. 沿目标进程主线程查看 `ActivityThread`、`bindApplication`、`Activity` 生命周期和首帧 `Choreographer#doFrame`。
3. 查看 RenderThread、GPU queue（提交给 GPU 的工作队列）与 FrameTimeline，区分 UI 线程、RenderThread、GPU 和 SurfaceFlinger 侧等待。
4. 用 Binder、线程调度和 CPU frequency 轨道解释空洞或抢占，避免把所有墙钟时间都归给应用函数。

滚动 Trace 应以 FrameTimeline 的 expected/actual slice 为主，它们分别表示系统预期的帧时序与实际执行时序。jank 标记表示帧未按预期时序完成。然后再回到主线程 `doFrame`、RenderThread 与 GPU 轨道定位原因。单看 `doFrame` 是否超过固定 16.67 ms 会误判高刷新率、可变刷新率以及 GPU / 合成侧超期。


## CLI 编排、Agent 任务与证据回传

测试协议稳定后，CLI 和 Agent 用于执行重复步骤、收集产物和生成候选结论。无法回到原始证据的自动结论不能进入门禁。

Android CLI 1.0 把 Android 项目的环境准备、设备管理、应用运行、UI 状态读取和 IDE 语义查询放进同一个 `android` 命令入口。本文所说的 agent，是能规划步骤并调用命令或其他工具的 AI 执行程序；CLI 是 command-line interface，即命令行界面；IDE 是 integrated development environment，即集成开发环境。agent 可以用 CLI 准备实验并重放操作路径，再由 Profiler、Perfetto、APA（Android Performance Analyzer）或 Macrobenchmark 采集和计算性能数据。

### Android CLI 在性能工具链里的位置

Android CLI 负责把项目、SDK、设备、APK、UI 状态和 IDE 查询接到同一套命令流程中。它不生成帧级测量数据，也不能代替系统追踪分析。

| 工具 | 主要回答的问题 | 性能工作里的输出 | 边界 |
|---|---|---|---|
| Android CLI | agent 如何读取项目、SDK、设备、APK、UI 状态和 IDE 符号信息 | JSON 项目描述、SDK/设备状态、截图、UI 布局树、IDE 查询结果 | 不计算性能指标，不替代 trace / profiler |
| Android Studio Profiler | App 进程内 CPU、内存、网络、功耗如何变化 | CPU / Memory / Power / System Trace 数据，详见 14.1 节 | IDE 交互强，批量回归和跨 trace 对比能力有限 |
| Android Performance Analyzer | CPU、GPU、内存、功耗、SurfaceFlinger 事件如何同时变化 | Perfetto Trace 项目、GPU counter、截图时间线，详见 14.13 节 | 侧重 trace 浏览与对比；复现条件仍需单独控制 |
| Perfetto UI / Trace Processor | Trace 里的线程、slice、counter、帧时间如何定量分析 | `.perfetto-trace`、SQL 查询、表格结果，详见 13.7 和 13.9 节 | 采集、场景复现和项目管理需要另行组织 |
| Macrobenchmark / Jetpack Benchmark | 同一场景在多次运行里的指标是否稳定 | 启动耗时、帧时间、Baseline Profile 验证结果 | 需要设计可重复场景和设备基线，详见 19.6 节 |

这里的 trace 是按时间记录系统与 App 事件的文件；slice 是带时间戳和持续时间的一段事件，counter 是随时间变化的数值轨道；Baseline Profile 则是帮助系统提前编译常用代码路径的规则。一次排查可以先用 CLI 固定复现状态，再用 Trace 或 Profiler 采集数据，随后通过 SQL、APA 或 Benchmark 得出可复查的结果。

### Android 17 源码基线与证据边界

Android CLI 是独立发布、运行在开发机或 CI 机器上的主机工具。它不属于 `android-17.0.0_r1` framework，也没有名为“Android CLI”的 API 37 SDK 接口。一次实验需要同时记录三组版本信息：

- Android CLI 版本：决定命令、参数、默认模板和 skill 安装行为；
- 设备 build fingerprint（构建的唯一标识字符串）与 Android 17 / API 37 平台版本：决定 framework、ART（Android Runtime）、SurfaceFlinger 合成器和 Perfetto 事件；
- 设备实际 kernel 与 vendor driver（厂商驱动）版本：决定 scheduler tracepoint（调度器事件记录点）、CPU/GPU 能力和设备特有数据。`android17-6.18-2026-06_r6` 只能作为 Android common kernel 的源码参照，真机可能包含厂商修改。

例如，APA 或 Perfetto 读取的录制配置，对应 Android 17 源码中的 `external/perfetto/protos/perfetto/config/trace_config.proto`。调度分析会使用 `include/trace/events/sched.h` 中的 `sched_switch`、`sched_wakeup` 等事件；分析真机 trace 时，还要以该设备内核实际提供的事件为准。CLI 可以启动 App、保存画面或触发测试，但不会改变这些事件的含义。

截图、布局树和 Journey 结果只能证明“agent 看到了什么、执行了什么”。帧耗时、CPU 调度、GPU 执行和功耗结论还要依据 trace、benchmark metric（基准测试指标）或硬件测量。官方 Macrobenchmark 文档不建议用模拟器产出的性能数字代表终端用户体验，并会把模拟器测量视为配置错误；模拟器更适合验证安装、页面路径和断言，发布级性能结论应在受控的物理设备上采集。

### 项目描述、SDK 与设备基线

性能复现实验应先固定环境。`android --version`、`describe`、`info`、`sdk` 和 `emulator` 命令适合在 agent 操作前生成基线记录。`android update` 更新 Android CLI 本身，`android sdk update` 更新 SDK package（SDK 软件包），两条命令用途不同。

| 命令 | 适合记录的基线 | 在性能流程里的用法 |
|---|---|---|
| `android --version` / `android update` | CLI 版本 | 保存实际运行版本；升级后先重读帮助并执行最小可运行检查 |
| `android init` | `android-cli` skill 安装状态 | 为已识别的 agent 安装基础 skill；不配置 SDK 或设备 |
| `android describe [--project_dir=...]` | 项目结构、build target、构建输出的 JSON 路径、APK 位置 | 让 agent 从结构化结果里找到 APK，无需猜测 Gradle 输出目录 |
| `android info` | 当前默认 Android SDK 路径 | 记录本轮测试使用的 SDK，避免多 SDK 环境使用不同版本 |
| `android --sdk=<path> ...` | 单次命令使用的 SDK | 在 CI 或多项目机器上显式绑定 SDK |
| `android sdk list/install/update` | 平台包、build-tools、system image 版本 | 建立 Android 平台、工具链和模拟器镜像版本基线 |
| `android emulator create/list/start/stop` | 虚拟设备 profile、设备名、serial | 先创建 AVD，再启动列表中的设备；Windows 侧 `android emulator` 命令当前被官方禁用 |
| `android docs search/fetch` | Android Knowledge Base（官方知识库）查询及返回内容 | 为 agent 提供官方文档上下文；不能替代项目源码与设备 trace |

`android describe` 会输出一个 JSON（结构化文本格式）文件路径，该文件描述项目结构、build target（构建目标）和 artifact（构建输出）位置。命令本身不执行 Gradle 构建；调用前仍要明确 build variant（构建变体，如 `debug`、`benchmark` 或 `release`），并确认 APK 的时间戳、校验值和代码提交。agent 因而无需从 `app/build/outputs/` 猜文件，也无需把临时路径写死在提示词里。

SDK 和设备基线至少要记录 Android SDK 路径、`platforms/android-37` package revision（软件包修订号）、build-tools / platform-tools 版本，以及设备 serial 或 emulator profile。serial 是 adb 用来区分设备的标识，emulator profile 是虚拟设备配置。涉及帧率、启动耗时、功耗和 GPU counter 的测试，还要保存设备型号、build fingerprint、刷新率、电池与温度状态及 GPU driver；这些内容需要测试脚本或人工补齐。

`android emulator create --profile=medium_phone` 用于创建 AVD（Android Virtual Device，Android 虚拟设备），`android emulator start medium_phone` 只能启动已经存在且名称匹配的设备。旧 CI 模板直接调用 `start`，在全新 runner（执行 CI 任务的机器）上会失败。AVD provisioning，即虚拟设备的预先创建与配置，应在任务开始前完成；也可以先用 `emulator list` 检查，再按需创建。缺少 API 37 platform 或目标 system image（系统镜像）时，先通过 `sdk list/install` 安装。

`.androidrc` 可以把常用全局参数保存在用户目录，例如默认 `--sdk=<path-to-sdk>`。这种配置适合个人机器；团队 CI 的必要配置应直接写入任务脚本。显式传入 `--sdk` 后，构建日志也能显示本次使用的环境。

### `run`、`layout`、`screen` 在复现流程中的边界

`android run` 只负责把给定 APK 安装到设备并启动组件。官方文档明确说明，该命令不执行构建步骤，调用方必须传入 APK 路径；多 APK 安装可以通过逗号分隔的 `--apks` 完成。构建与运行分别记录后，测试报告才能说明本次使用的是哪一个 APK。

下面的命令演示安装单 APK、指定设备和显式启动 Activity；它们都假设 APK 已经构建完成。

```bash
# 安装并启动默认设备上的 APK；APK 路径通常来自 android describe 或 CI 产物
android run --apks=app/build/outputs/apk/debug/app-debug.apk

# 多设备并行测试时显式指定设备 serial
android run --apks=app-debug.apk --device=emulator-5554

# 明确指定要启动的 Activity
android run --apks=app-debug.apk --type=ACTIVITY --activity=.MainActivity
```

前三条命令分别覆盖默认设备、指定 serial 和指定 Activity 三种启动方式。发布级性能测试应使用接近 `release` 优化配置、同时满足 non-debuggable（不可调试）与 profileable（允许 shell 进行低开销性能采样）的构建。`--debug` 适合断点和诊断，相关结果不应与发布构建的基线数字放在同一组。官方页面当前还有一处矛盾：示例使用 `--type=SERVICE`，支持类型列表却没有列出 `SERVICE`。涉及后台组件时，应以所用 CLI 版本的 `android run --help` 和实机试运行为准，不把这个示例视为稳定接口。

`android layout` 返回当前活动 App 的 UI 布局树 JSON，也就是按层级组织的界面节点数据。`--diff` 只输出相对命令内部上一次快照发生变化的节点。它适合确认 agent 是否进入了正确页面、某个按钮是否出现，以及操作前后哪些节点改变。布局树不能解释帧耗时，也不具备 Layout Inspector 的完整交互能力；分析 measure / layout / draw 成本仍需使用 Perfetto、Profiler 或相关章节介绍的 View 绘制流程。

`android screen capture` 负责截屏，`--annotate` 会给识别到的 UI 元素绘制编号框。`android screen resolve --screenshot=ui.png --string="input tap #5"` 会把截图上的编号替换为实际坐标；命令只返回替换后的字符串，调用方还要执行相应的输入命令。这组能力可以留存当时的屏幕状态，并说明点击坐标如何得到。它无法解释某一帧卡顿的原因，也不能替代 FrameTimeline（逐帧预期与实际时间轨道）、SurfaceFlinger 合成记录或 GPU counter（随时间采样的 GPU 数值）。

当前 `layout` 与 `screen capture` 文档没有列出 `--device` 参数。多设备 CI runner 应隔离 adb（Android Debug Bridge）server，或保证任务期间只向 CLI 暴露目标设备，并在截图、布局树和 trace 文件名中记录 serial。仅在 `android run` 中指定 `--device`，无法确认后续 UI 命令仍指向同一台设备。

在性能复现中，可以依次安装目标 APK、进入目标页面、截屏确认状态、导出布局树并执行交互，最后把 trace 或 benchmark 输出放进同一份报告。这样会得到一组可复查的输入与结果：APK、设备、页面状态、操作坐标、trace 文件和指标数据。

### Journeys 与关键用户路径回归

Journeys 用自然语言描述用户在 App 中要完成的路径。agent 会把指令转换为界面交互，再依据设备画面判断断言是否成立。断言是对预期结果的可检查描述，例如“详情页标题已经出现”。官方页面在 2026 年 7 月 17 日更新后，仍由 agent 和 CLI 附带的 skills 创建、运行 Journey，并明确提到可接入 CI/CD（持续集成与持续交付）。

性能场景里的 Journey 不应只写“打开首页并滑动列表”。一条可复现的用户路径至少要补齐这些条件：

- 入口状态：冷启动、温启动、后台恢复、登录态、缓存是否清空。
- 页面路径：启动页、首页、列表页、详情页、返回路径，每一步都要有可观察 UI 标记。
- 交互动作：点击、输入、滚动、等待网络、横竖屏切换、返回键。
- 断言条件：目标页面出现、错误提示不出现、列表加载完成、关键按钮可点击。
- 性能采集窗口：明确从哪个动作前开始 trace、在哪个 UI 标记出现后停止，也就是界定纳入统计的时间范围。
- 失败处理：页面未出现、登录失效、网络超时、权限弹窗干扰时如何退出并保存截图。

Journey 适合准备登录态、导航到目标页面、确认异常是否出现，并记录失败画面。自然语言理解、视觉识别、坐标选择和 agent 模型都会带来执行差异，因此不适合控制 benchmark 的计时区间。测量窗口内的启动、滚动和动画应交给 Macrobenchmark 与 UI Automator；UI Automator 是 Android 的跨 App 界面自动化框架。指标应来自 Macrobenchmark、Perfetto Trace、APA 或线上 APM（Application Performance Monitoring，应用性能监控）。冷启动耗时、帧时间分布、CPU 调度、GPU counter、GC（garbage collection，垃圾回收）暂停和 Binder（Android 进程间通信机制）等待时间，都不能从 Journey 的成功或失败直接推导。

官方 Journey 页面没有发布固定的 `android journey ...` 子命令格式，因此本文不编造这类命令。文件格式、运行步骤和 CI 接入方式应以当前 Android CLI、Journeys skill 及项目实际生成的文件为准。报告还要记录 CLI、agent、模型、skill 版本或内容快照，避免直接比较不同执行环境得出的结果。

### Android Studio 语义命令与性能排查协作

`android studio` 命令仍处于 Preview（预览）状态，接口可能调整。官方文档给出的前提是：项目已在 Android Studio Quail 2 Canary 1 或更高版本中打开，并且 Gemini in Android Studio 已启用、已登录。Canary 是更新快、稳定性低于 Beta 和 Stable 的预览渠道。满足条件后，agent 可以通过 CLI 连接正在运行的 Android Studio 实例，执行理解代码符号与项目结构的查询；这类查询比纯文本搜索多了声明、引用和类型信息。

| 命令 | 输出 | 性能排查里的用法 |
|---|---|---|
| `android studio check` | Android Studio PID、版本、打开的项目状态 | 多 IDE 实例时选择目标项目，确认 CLI 与 IDE 已连接；PID 是进程编号 |
| `android studio analyze-file <path>` | Kotlin / Java 文件里的错误、警告、lint | 修改性能相关代码后执行 IDE 静态检查；lint 是一组静态规则检查 |
| `android studio find-declaration <symbol>` | 符号声明位置，可用 `--context-file` 消歧 | 从 trace 里的类名、方法名跳到源码定义 |
| `android studio find-usages <symbol>` | 符号引用位置 | 判断某个性能入口是否还有其他调用方 |
| `android studio open-file <path>` | 在 Android Studio 当前编辑器打开文件 | 把 agent 找到的源码、trace、报告交给人工复核 |
| `android studio render-compose-preview <path> <composable>` | Compose Preview PNG，可选语义树 JSON | 改 Compose UI 后确认画面和供无障碍、测试使用的语义节点 |
| `android studio version-lookup <artifacts...>` | Maven、AGP（Android Gradle Plugin）、Gradle、NDK（Native Development Kit）、SDK、Compose、Kotlin 等版本信息 | 核对工具链和依赖版本，减少手工查版本带来的误差 |

这组命令适合源码定位和人工复核。例如，trace 显示某段 Compose 页面在滑动时发生大量重组，即 Compose 多次重新执行相关 UI 代码。agent 可以先用 `find-declaration` 找到相关函数，再用 `analyze-file` 检查修改后的文件，并通过 `render-compose-preview --print-semantics` 为目标预览函数生成预览图和语义树。这里的预览函数必须带 `@Preview`，通常也会带 `@Composable`。若 release trace 中的符号已混淆或只剩地址，还需要 mapping（混淆前后名称映射）、native symbol（本地代码地址与函数名的映射）或对应的源码版本协助定位。帧时间是否改善仍要由 trace 或 benchmark 验证。

`version-lookup` 返回仓库或工具渠道中的可用新版本，但不会判断版本是否适合当前项目，也不会替团队选择 Stable、Beta 或 Canary。三者大致对应稳定发布、较成熟预览和早期预览；升级时仍要检查版本目录、依赖锁、AGP/Gradle 兼容表和回归测试。

### Android skills 与性能专项能力

Android skills 是供 AI 工具和 agent 使用的指令包。每个 skill 通常以 `SKILL.md` 说明适用任务和执行步骤，还可以附带脚本、模板与参考资料。官方文档列出的能力包括 XML 到 Compose 迁移、AGP 9 升级、Navigation 3、edge-to-edge UI（内容延伸到系统栏区域）和 R8 配置检查。R8 是 Android 构建中的代码压缩与优化工具。skill 为 agent 提供特定 Android 任务的操作方法，其输出仍需验证。

`android init` 是最短的初始化入口，用来安装基础 `android-cli` skill。Android CLI 还提供 `skills list/find/add/remove` 管理能力：

- `android skills list --long`：列出可用 skill、描述和已安装到哪些 agent。
- `android skills find 'performance'`：按描述搜索与性能相关的 skill。
- `android skills add --skill=<skill-name>`：安装或更新单个 skill；省略 `--skill` 和 `--all` 时默认安装 `android-cli` skill。官方仓库示例还用 `--project=.` 指定当前项目根目录。
- `android skills add --all`：一次安装或更新全部 Android skills。
- `android skills remove --skill=<skill-name>`：从一个或多个 agent 目录移除 skill。

更新规则要写进团队规范。官方文档提醒，如果修改了已安装的 skill，应换一个名称保存，否则后续执行 `skills add` 时可能被最新版覆盖。项目自定义 skill 放在仓库根目录的 `.skills/` 或 `.agent/skills/` 下，每个 skill 目录都要包含大小写固定的 `SKILL.md`。团队把 Perfetto SQL 模板、R8 检查流程或启动回归脚本写入自定义 skill 时，应使用内部名称，并记录来源和版本。

当前官方仓库中，与性能工作较相关的目录包括四个：`profilers/perfetto-sql` 把自然语言问题转换成有效的 Perfetto SQL，并对本地 trace 执行；`profilers/perfetto-trace-analysis` 调查延迟、内存或卡顿的原因；`testing/testing-setup` 分析并建立原生 Android 测试策略与测试基础设施；`performance/r8-analyzer` 检查构建文件和 R8 keep rules（指定哪些类或成员必须保留的规则），找出重复或范围过大的规则。这些名称是仓库目录和 skill 名称，不是 `android` 子命令。

安装或升级后，应先检查 `SKILL.md`、附带脚本和资源，再允许 agent 执行。当前 CLI 文档只描述“更新到最新版”，没有提供固定 skill 版本的参数。需要重复同一实验时，应在记录中保存已审核内容对应的提交或归档。skill 得出的结论还要复核 trace 表结构、字段单位、编译模式和设备条件。

### 与 APA / Perfetto / Macrobenchmark 的分工

把 Android CLI 加入现有工具后，可以按“环境 → 复现 → 采集 → 分析 → 回归”的顺序组织材料：

| 阶段 | Android CLI 做什么 | 其他工具做什么 | 输出 |
|---|---|---|---|
| 环境 | `android info`、`android sdk list`、`android emulator list/start` 记录 SDK 和设备 | CI 记录构建号、git commit、设备温度、电量、刷新率 | 环境基线 |
| 复现 | `android run` 安装 APK，Journey 或 screen/layout 驱动页面 | 人工确认测试账号、弱网、权限弹窗等条件 | 页面状态、截图、布局树 |
| 采集 | CLI 触发前置动作和结束动作 | Profiler / Perfetto / APA / Macrobenchmark 采集 trace 或指标 | trace、profile、benchmark JSON |
| 分析 | `android studio find-declaration/find-usages/open-file` 关联源码 | Perfetto SQL、APA、Profiler 做证据分析 | SQL、截图、源码定位 |
| 回归 | agent 准备同一入口状态；计时窗口外可用 Journey | Macrobenchmark 或 CI 阈值检查对比指标 | 趋势表、阈值判断、失败截图 |

Android CLI 负责准备环境、运行 App 和定位源码。14.13 节的 APA 在同一时间窗口分析 CPU、GPU、内存、功耗与 SurfaceFlinger；13.7 节的 Perfetto SQL 从 trace 表中计算定量结果；19.6 节的 Macrobenchmark 重复执行受控场景并输出指标。设备基线、APK、操作脚本、trace 和查询共同标识一次实验，让各工具的结果可以相互核对。

### CI 与本地 agent 工作流模板

一条最小可复现流程包含六类材料：环境记录、项目描述、设备状态、Journey 或操作脚本、trace / benchmark 输出和分析报告。下面的脚本骨架补上了 AVD 预先创建与启动完成检查。脚本中的 `release-like/profileable` 指接近 release 优化配置、同时允许低开销 profiling 的测量构建。由于 `layout` 和 `screen capture` 没有公开 `--device` 参数，示例还假设任务期间只有目标设备对 Android CLI 可见。真实性能数字仍应在固定的物理设备上采集。

```bash
set -euo pipefail

PROJECT_ROOT="$PWD"
PERF_OUT_DIR="$PROJECT_ROOT/out/perf-run-$(date +%Y%m%d-%H%M%S)"
TEST_DEVICE_NAME="${TEST_DEVICE_NAME:?set TEST_DEVICE_NAME to an existing AVD name}"
TEST_DEVICE_SERIAL="${TEST_DEVICE_SERIAL:?set TEST_DEVICE_SERIAL after device allocation}"
mkdir -p "$PERF_OUT_DIR"

# 1. 记录 CLI、SDK 和项目结构
android --version > "$PERF_OUT_DIR/android-version.txt"
android info > "$PERF_OUT_DIR/android-info.txt"
android sdk list 'platforms/android-37|build-tools|platform-tools|emulator' \
  > "$PERF_OUT_DIR/android-sdk-list.txt"
android describe --project_dir="$PROJECT_ROOT" \
  > "$PERF_OUT_DIR/android-describe.txt"

# 2. AVD 只在 provisioning 阶段创建：
# android emulator create --profile=medium_phone
android emulator list > "$PERF_OUT_DIR/emulator-list.txt"
android emulator start "$TEST_DEVICE_NAME" \
  > "$PERF_OUT_DIR/emulator.log" 2>&1 &
adb -s "$TEST_DEVICE_SERIAL" wait-for-device
until [[ "$(adb -s "$TEST_DEVICE_SERIAL" shell getprop sys.boot_completed \
  | tr -d '\r')" == "1" ]]; do
  sleep 2
done

# 3. 保存设备平台身份
adb -s "$TEST_DEVICE_SERIAL" shell getprop ro.build.fingerprint \
  > "$PERF_OUT_DIR/build-fingerprint.txt"
adb -s "$TEST_DEVICE_SERIAL" shell getprop ro.build.version.sdk \
  > "$PERF_OUT_DIR/api-level.txt"

# 4. 安装并启动已构建的 release-like/profileable APK
android run \
  --apks="$PROJECT_ROOT/app/build/outputs/apk/benchmark/app-benchmark.apk" \
  --device="$TEST_DEVICE_SERIAL"

# 5. 保存测量前的页面状态
android screen capture --output="$PERF_OUT_DIR/before.png" --annotate
android layout --pretty --output="$PERF_OUT_DIR/layout-before.json"

# 6. 计时区间由 Macrobenchmark / UI Automator 驱动；
# Journey 可用于区间外的前置导航和失败诊断。

# 7. 保存测量后的 UI 状态；trace / benchmark 由相应工具输出
android screen capture --output="$PERF_OUT_DIR/after.png" --annotate
android layout --pretty --output="$PERF_OUT_DIR/layout-after.json"
```

`emulator start` 在后台运行，所以脚本会等待 adb 连接和 `sys.boot_completed=1`。这个属性只说明系统完成启动，无法说明温度、编译状态、网络和后台任务已经满足测量条件。启动回归可以使用 Macrobenchmark；卡顿排查可以使用 Perfetto 或 APA；功耗分析还要采集电源、温度和电池数据；Compose UI 变更可以通过 `android studio render-compose-preview` 检查预览结果。

### 隐私与 Telemetry（遥测）边界

Telemetry 是工具为了解使用情况和故障而发送的数据。Android CLI 官方文档写明会收集 `android` 命令与子命令、选项名称、固定枚举型系统选项值，以及经过匿名化处理的堆栈和异常消息。文档同时说明，它不收集命令响应，也不收集用户创建的位置参数或外部标识符的值，例如 Maven 坐标（依赖的 group、artifact 与 version 标识）、文件路径和自定义项目名。

企业内网使用时，报告里应单独记录三类内容：

- 命令日志：是否包含本地路径、包名、账号、设备 serial、截图或布局树里的业务数据。
- agent 上下文：是否把 trace、截图、布局树或源码片段交给外部模型。
- skill 来源：官方 skill、团队内部 skill、第三方 skill 分开管理，更新记录要可追溯。

`screen capture` 和 `layout` 会直接读取设备画面与 UI 树，因而比 `android info` 或 `sdk list` 更容易包含业务数据。Perfetto SQL skill 还可能读取本地 trace，Journey agent 会接收自然语言步骤和设备画面。涉及用户数据、测试账号、订单页、聊天页或健康数据时，应使用隔离测试环境，并在报告发布前删除或遮盖可识别个人与业务的信息。


## 常见误区

**模拟器能不能运行基准测试？** 可以用来验证构建、安装和脚本路径，但 AndroidX Benchmark 会报告模拟器配置错误。抑制错误后产生的数据不能和物理设备比较，也不能作为发布门禁。

**Microbenchmark 数字更稳定，能否替代 Macrobenchmark？** 不能。Microbenchmark 适合循环热点，缓存与 AOT 状态接近最佳情况；启动、进程创建、系统服务和完整渲染仍要由 Macrobenchmark 与系统 Trace 判断。

**Macrobenchmark 能否放进应用模块？** 不能。它要求独立的 `com.android.test` 模块，从目标应用进程外启动和停止应用。Microbenchmark 可放在专用 benchmark 模块中，并依赖包含被测代码的模块。

**迭代次数是否固定为 10？** 没有统一数字。短而稳定的热点可能需要更多样本，长启动场景受 CI 时长限制。先在固定设备上观察分布与热状态，再选择能稳定区分目标回归幅度的迭代数；报告保留 median、尾部分位和原始样本。

**设备温度与调度波动能否全部消除？** 不能。固定设备状态、等待冷却、减少账号和后台任务可以压低波动，仍会受到 DVFS（动态电压频率调整）、thermal 和内核调度影响。测试记录应绑定 Android build fingerprint；分析 Android 17 通用内核行为时再对照 `android17-6.18-2026-06_r6`，不能用通用内核标签替代量产机证据。

**Espresso 能否驱动 Macrobenchmark？** Macrobenchmark 使用外部测试 APK，Espresso 的 View matcher 与同步机制面向目标应用 instrumentation 环境。完整性能场景使用 UI Automator；Espresso 保留在功能回归测试中。


## 结论

Android CLI 为 agent 提供项目描述、SDK 与设备管理、UI 状态读取和 IDE 符号查询入口。它能补全复现输入，但截图、布局树和 Journey 成功都不能单独支持性能结论。Android 17 上的结果应绑定 CLI 版本、设备 build fingerprint、实际 kernel 与 vendor driver；`android-17.0.0_r1` 和 `android17-6.18-2026-06_r6` 可作为对应源码的参照。最后还要由 Profiler、Perfetto、APA、Macrobenchmark 或线上指标验证。


## 参考资料

- [Android Benchmark 总览](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [Macrobenchmark 官方文档](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Microbenchmark 官方文档](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview)
- [编写 Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-write)
- [CI/CD 中的基准测试](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Baseline Profiles 指南](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [UI Automator 文档](https://developer.android.com/training/testing/other-components/ui-automator)
- [Espresso 文档](https://developer.android.com/training/testing/espresso)
- [Monkey 文档](https://developer.android.com/studio/test/other-testing-tools/monkey)
- [Firebase Test Lab 文档](https://firebase.google.com/docs/test-lab)
- [GitHub 官方示例: performance-samples](https://github.com/android/performance-samples)
- [Android 17 `am instrument` 实现](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/cmds/am/src/com/android/commands/am/Instrument.java)
- [Android 17 `UiAutomation` 实现](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/UiAutomation.java)
- [Android 17 common kernel 锚点](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)

- [Android CLI](https://developer.android.com/tools/agents/android-cli)
- [Android CLI support for Journeys](https://developer.android.com/tools/agents/android-cli/journeys)
- [Android skills](https://developer.android.com/tools/agents/android-skills)
- [Android CLI 1.0 announcement](https://android-developers.googleblog.com/2026/05/android-cli-stable-1-0-agent-development.html)
- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
- [Android Studio performance profilers](https://developer.android.com/studio/profile)
- [Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Set up the Android 17 SDK](https://developer.android.com/about/versions/17/setup-sdk)
- [Perfetto documentation](https://perfetto.dev/docs/)
- [Android 17 Perfetto `TraceConfig`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto)
- [Android 17 common kernel scheduler tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
