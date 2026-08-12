---
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
chapter: 14.9
confidence: medium
last_verified: 2026-07-30
last_verified_against: "AndroidX Benchmark 1.4.1 stable + Android test docs + Android 17 / API 37 + android-17.0.0_r1"
related_chapters: ["8.7", "13.9", "15.3", "15.6"]
section: 14.9
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
status: "finalized"
tags:
  - android
  - benchmark
  - macrobenchmark
  - microbenchmark
  - ci-cd
  - performance-testing
task2b_state: fixed
task6_state: "reviewed"
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
title: 自动化性能测试与回归门禁
---

# 14.9 自动化性能测试与回归门禁

## 为什么要用自动化工具做性能测试

Perfetto、Android Studio Profiler 适合回答“时间花在哪里”，自动化基准测试负责回答“从哪次改动开始变慢”。一次手工 Trace 可以定位问题，却很难在每次提交后按相同条件重放启动、滚动或热点函数。

Jetpack Benchmark 把场景、编译状态、重复次数和产物格式写进测试代码。持续集成系统因此可以保存每次运行的 JSON 与 Perfetto Trace，并把本次数据与同一设备上的历史数据比较。自动执行只解决了重复性；构建类型、设备温度、系统版本、编译模式和操作边界仍要固定，否则得到的是设备噪声。

## Macrobenchmark 与 Microbenchmark：两种层次，两种用途

两套库的区别集中在进程边界和测量对象：

| 维度 | Macrobenchmark | Microbenchmark |
|---|---|---|
| 测量范围 | 启动、滚动、动画等完整用户场景 | 可直接调用的函数、算法或一小段 UI 代码 |
| 运行位置 | 测试 APK 在目标应用进程之外驱动场景 | 被测代码在基准测试进程内循环执行 |
| 编译控制 | 可选择 `DEFAULT`、`Full`、`Partial`、`None`、`Ignore` | AndroidX Benchmark Gradle 插件可对基准测试 APK 做全量 AOT |
| 主要产物 | 指标 JSON；每个测量迭代一份系统 Trace | 指标 JSON；每个 `measureRepeated` 默认一份方法/系统 Trace |
| 适合回答 | 一次交互整体是否回归，慢在哪个系统阶段 | 某个热点实现是否更快，分配是否减少 |

### Macrobenchmark：端到端的用户体验测量

Macrobenchmark 从目标应用外部启动 Activity、注入手势并采集系统 Trace，适合测量启动、滚动和动画等完整交互。测试代码必须放在独立的 `com.android.test` 模块中；目标 APK 应使用接近 release 的非 debuggable、可混淆构建，并通过 `<profileable>` 允许低干扰 Trace 采集。

入口是 `MacrobenchmarkRule.measureRepeated()`。`setupBlock` 把应用放到一致的初始状态，`measureBlock` 定义计入测量的操作。一次 `measureRepeated()` 会执行多个迭代，并为每个测量迭代保存一份系统 Trace。`StartupTimingMetric` 的汇总值是 min、median、max；`FrameTimingMetric` 输出 P50、P90、P95、P99。不能把它们概括成“重复 N 次取平均值”。

常用指标及其边界如下：

| 指标 | 版本边界 | 读法 |
|---|---|---|
| `StartupTimingMetric` | Macrobenchmark 支持 API 23+；`timeToFullDisplayMs` 在 API 29 及以下可能不可用 | TTID 对应首帧；TTFD 依赖应用在主要内容就绪后调用 `reportFullyDrawn()` |
| `FrameTimingMetric` | `frameOverrunMs` 仅 API 31+ | 正值表示越过该帧 deadline；`frameDurationCpuMs` 表示 UI 线程与 RenderThread 生成一帧所用的 CPU 时间 |
| `TraceSectionMetric` | 实验 API；依赖 Trace 中存在同名 section | 默认只查目标包，并选取测量区间内首次匹配；适合测量明确标记的初始化或绑定阶段 |
| `PowerMetric` | 实验 API，最低 API 29 | 高精度 power/energy 数据是系统总量，依赖设备 power rails；官方文档限定 Pixel 6、Pixel 6 Pro 及更新机型 |

`PowerMetric` 还提供电池电量差值类型，精度低于 power rail。无论选择哪一种，功耗结果都不能直接归因于单个应用。测试进程、系统服务、屏幕和网络活动都会进入系统总量。[AndroidX 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-main/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/Metric.kt) 对 `PowerMetric` 标注了 `@RequiresApi(29)`，并提供 `deviceSupportsHighPrecisionTracking()` 检查设备能力。

### Microbenchmark：代码级热点分析

Microbenchmark 直接循环调用被测代码，适合 JSON 解析、数据转换、布局 inflate、`RecyclerView` item 绑定等高频 CPU 路径。循环会形成预热缓存和稳定代码路径，因此结果接近热点代码的最佳情况；磁盘首次读取、只运行一次的初始化、跨进程交互通常不适合用它单独判断。

下面的测试演示如何测量解析函数，并用 `BlackHole.consume()` 防止 Kotlin 编译器或 R8 删除未使用的计算结果：

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

`measureRepeated` 负责预热、循环次数和计时，报告执行时间与分配次数。Benchmark 1.3.0-beta01+ 配合 AGP 8.4.0+ 时，`androidx.benchmark` 插件默认对 Microbenchmark APK 做全量 AOT；需要观察 JIT 行为时，可在 `gradle.properties` 中设置 `androidx.benchmark.forceaotcompilation=false`。准备输入数据或重置容器时，应把不计时的部分放进 `runWithTimingDisabled {}`。

### 什么时候用哪个？

完整交互选 Macrobenchmark，能独立调用的热点选 Microbenchmark。两者常按这条证据路径配合：

1. Macrobenchmark 记录启动或滚动回归，并保留对应 Trace。
2. Perfetto 把耗时定位到一个可隔离的函数或阶段。
3. Microbenchmark 比较候选实现，确认局部变化。
4. Macrobenchmark 回到原场景，确认端到端指标与 Trace 都得到改善。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`；Macrobenchmark 最低支持 API 23，`frameOverrunMs` 属于 API 31+ 指标，`PowerMetric` 最低支持 API 29。

## 使用 Macrobenchmark 测量启动时间和滑动帧率

### 测量启动时间

这段测试测量 Baseline Profile 可用时的冷启动，代码主体省略了 import：

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

`StartupMode.COLD` 会在 `setupBlock` 与 `measureBlock` 之间终止目标进程，测试无需自行执行 `force-stop`。`pressHome()` 固定启动前的可见界面，`startActivityAndWait()` 发出启动 Intent 并等待 Activity 首帧。`iterations = 10` 只是该场景的采样配置；应根据本机噪声和 CI 时长调整，不能把 10 次当成通用门槛。

`StartupTimingMetric` 输出 `timeToInitialDisplayMs` 和 `timeToFullDisplayMs`。前者从系统收到启动 Intent 计到目标 Activity 首帧；后者计到应用调用 `reportFullyDrawn()` 后的首个完整帧。应用未调用该 API 时没有可解释的 TTFD，API 29 及以下还可能无法提供该字段。报告比较以 median 为主，同时保留 min、max 和单次 Trace。

`StartupMode` 提供 `COLD`、`WARM`、`HOT`。三种模式改变启动前的进程和 Activity 状态，不能混在一条趋势曲线中。测试名称、JSON 基线和告警规则都应带上启动模式。

### 测量滑动帧率

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

`FrameTimingMetric` 报告 P50、P90、P95、P99。API 31+ 的 `frameOverrunMs` 使用系统为每一帧计算的 deadline，适用于 60 Hz、高刷新率和可变刷新率设备；正值表示超期，负值表示仍有余量。`frameDurationCpuMs` 只描述 UI 线程与 RenderThread 生成帧的 CPU 时间，GPU 等待和合成问题仍要回到 FrameTimeline 与系统 Trace 判断。

### CompilationMode：量化编译优化效果

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

`DEFAULT` 在 API 24+ 尝试安装 APK 中的 Baseline Profile；API 23 按系统默认行为做全量编译。`Partial()` 用于观察 profile 覆盖后的状态，`None()` 用于观察无预编译的状态，`Full()` 适合研究全量 AOT 上限。`Ignore()` 不修改已有状态，适合由外部脚本精确控制 ART 编译的场景；当前 API 带有 `ExperimentalMacrobenchmarkApi` 标记，调用处需要按所用 Benchmark 版本处理 opt-in。

Android 14（API 34）起，Macrobenchmark 可以在重置编译状态时保留应用数据；更低版本常需要重装 APK。测试必须保留登录态或预置数据时，优先使用 API 34—37 的固定设备；旧设备可由外部脚本管理编译，再选 `CompilationMode.Ignore()`。

Baseline Profile 收益应由同一 APK、同一设备、同一启动模式下的 `None()` 与 `Partial()` 实测得出。跨项目引用“提升约 30%”无法替代本应用数据。

## adb shell am instrument：性能测试的命令行入口

Gradle、Android Studio 和云设备平台最终都要启动 instrumentation。ADB 下最直接的入口是 `am instrument`，基本语法如下：

```bash
adb shell am instrument -w <test_package>/<runner_class>
```

`<test_package>/<runner_class>` 是测试 APK Manifest 中注册的 instrumentation 组件；`-w` 让客户端等待测试结束并打印状态。Macrobenchmark 使用常规 `AndroidJUnitRunner`，下面只执行一个测试方法：

```bash
adb shell am instrument -w \
  -e class com.example.macrobenchmark.StartupBenchmark#coldStartup \
  com.example.macrobenchmark/androidx.test.runner.AndroidJUnitRunner
```

`-e class` 进入 instrumentation 的参数 `Bundle`，由 `AndroidJUnitRunner` 解释为测试过滤条件。Microbenchmark 的组件 runner 则是 `androidx.benchmark.junit4.AndroidBenchmarkRunner`，两者不能照抄。

本地运行整个 Macrobenchmark 模块或单个方法，可让 Gradle 负责构建、安装、执行和拉取产物：

```bash
./gradlew :macrobenchmark:connectedCheck

./gradlew :macrobenchmark:connectedCheck \
  -Pandroid.testInstrumentationRunnerArguments.class=\
com.example.macrobenchmark.StartupBenchmark#coldStartup
```

`connectedCheck` 会自动把 JSON 与 Trace 拉到主机。CI 拆分构建和设备执行时，才需要显式安装两个 APK 并调用 `am instrument`。

Benchmark 常用参数由测试库解释，不属于 `am` 内建选项：

- `-e class 包名.类名#方法名`：由 runner 过滤测试。
- `-e androidx.benchmark.dryRunMode.enable true`：把基准缩成一次循环，用于验证脚本和配置，结果不能进入性能趋势。
- `-e androidx.benchmark.iterations N`：覆盖 Microbenchmark 的迭代数；Macrobenchmark 的迭代数由测试代码中的 `measureRepeated` 参数定义。
- `-e androidx.benchmark.suppressErrors 错误名`：把指定配置错误降为警告。带错误前缀的结果只适合诊断，不能进入基线。
- `-e additionalTestOutputDir 路径`：为直接 ADB 或云设备运行指定可写的产物目录。

Benchmark 1.1.0 之前需要用 `androidx.benchmark.output.enable=true` 手动开启 JSON；当前版本默认输出，无需继续携带这个历史参数。

Android 17 源码中，[`Instrument`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/cmds/am/src/com/android/commands/am/Instrument.java) 解析 `-w`、`-e`、用户、ABI 等参数，随后调用 `IActivityManager.startInstrumentation()`；[`ActivityManagerShellCommand`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java) 的帮助文本也明确区分了 `am instrument` 入口。这一层只负责启动和传递参数，指标含义由 AndroidX Benchmark 决定。

## UI Automator 与 Espresso：在性能测试中的角色

UI Automator 负责从应用进程外驱动完整场景；Espresso 负责在应用 instrumentation 环境中做稳定的功能断言。两者的同步方式和测量边界不同。

### UI Automator：Macrobenchmark 的底层驱动

UI Automator 可以检查用户应用和系统应用的可访问性节点、注入输入并跨窗口操作。它不要求目标应用链接测试代码，因而可以驱动混淆后的 release-like APK，也能处理权限弹窗、桌面和系统设置。

Android 17 的 [`UiAutomation`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/UiAutomation.java) 被平台定义为一种特殊的 `AccessibilityService` 客户端；`am instrument` 创建 `UiAutomationConnection` 并把它交给 instrumentation。这里没有要求用户安装或常驻启用一个普通无障碍服务。UI Automator 在测试进程中通过这条系统连接读取节点和注入手势。

测试进程与目标应用进程分离，可以避免把驱动代码计入目标进程的堆和调用栈。它们仍共享 CPU、内存带宽、Binder 服务和内核调度资源，节点查询与输入注入也有 IPC 成本。降低扰动的方法是把页面查找、登录和数据准备放入 `setupBlock`，在 `measureBlock` 中只保留固定输入和必要等待。

UI Automator 2.4 引入了 `uiAutomator {}`、`onElement {}`、`waitForAppToBeVisible()` 等 Kotlin DSL。官方文档把 2.4 API 标为仍在开发，同时推荐新测试采用它；已有 Macrobenchmark 使用 `UiDevice`、`By`、`Until` 的代码仍可维护，不必为了语法变化改写已经稳定的场景。

### Espresso：白盒验证，不是性能测量工具

Espresso 与目标应用的 instrumentation 紧密配合。每次 `onView()` 操作前，它会等待需要处理的消息队列、`AsyncTask` 和已注册 `IdlingResource` 进入空闲状态。这个同步模型适合验证点击后的 View 状态，也适合确认性能优化没有破坏功能。

同步等待会改变输入时序，测试代码及 matcher 还可能进入目标进程的 CPU、内存和调度数据。用 Espresso 包围一段操作再读取墙钟时间，测到的会同时包含框架同步、断言和应用工作，不能替代 Macrobenchmark 指标。

工程上可把 Espresso 用例放在提交验证阶段，把 Macrobenchmark 放在固定设备阶段：前者验证页面可用，后者测量完整交互。失败证据也不同，Espresso 看断言与截图，Macrobenchmark 看 JSON 与 Trace。

### 不能混用的地方

Macrobenchmark 模块的 instrumentation 目标是测试 APK，无法把 Espresso 的 `onView()` 当作目标应用内 matcher 使用。跨应用操作、权限弹窗和系统界面统一交给 UI Automator。目标应用内部必须暴露“主要内容已就绪”这类语义时，可调用 `reportFullyDrawn()` 或写自定义 Trace section，再由 Macrobenchmark 从 Trace 读取；不要把 Espresso 驱动塞进 `measureBlock`。

## Monkey、SoloPi 与 Appium：自动化工具的另一类用途

基准测试负责回答“这次改动是否让指标变差”。稳定性和专项测试工具负责覆盖长时间运行、随机输入、跨端脚本这些场景。

### Monkey：低成本压力测试

`Monkey` 在设备端生成伪随机点击、滑动、按键和系统事件，适合在夜间任务中发现崩溃与 ANR。它能用固定 seed 重放相同事件序列，但页面数据、网络响应和系统弹窗仍可能让后续路径分叉。

这条命令把事件限制在单个包中，固定 seed，并监控 native crash：

```bash
adb shell monkey -p com.example.app \
  -s 20260730 \
  --pct-touch 60 --pct-motion 20 \
  --throttle 200 \
  --monitor-native-crashes \
  -v 10000
```

`10000` 是事件数，`--throttle 200` 在事件之间加入 200 ms 间隔。保留命令、seed、应用版本、系统版本、logcat、bugreport 与 tombstone，才能复查故障现场。Monkey 没有固定业务边界，也不控制编译和设备状态，因此不能用于启动耗时或帧时间回归判定。

### SoloPi：专项性能脚本和视觉拆帧

SoloPi 提供录制回放、CPU / 内存 / FPS 等性能面板和启动耗时辅助工具，适合线下走查与测试同学复现长流程。它的开源仓库构建说明仍以 Target API 29、较旧 Gradle 与 NDK 为基准；接入 Android 17 设备前要单独验证权限、无线调试、无障碍节点和厂商系统兼容性。SoloPi 的面板数据可用于发现异常区间，发布门禁仍应使用可追溯的 Benchmark JSON 与 Trace。

### Appium：跨端自动化，不负责指标可信度

Appium 3 是基于 W3C WebDriver 的模块化自动化框架，Android 能力由独立 driver 提供。它适合统一 Android、iOS、WebView 和桌面端的业务脚本。WebDriver 服务、driver、设备自动化后端和显式/隐式等待都会影响输入时序，所以 Appium 负责场景编排时，性能指标仍应由设备侧 Macrobenchmark、Perfetto 或明确的系统 counter 采集。

## 性能自动化测试的 CI/CD 集成方案

可靠的性能 CI 要同时保存代码版本、APK、测试 APK、设备指纹、Benchmark JSON 和 Trace。缺少其中任一项，回归曲线都很难复查。

### 基本架构

一条可维护的流水线分为构建、设备准备、执行、产物收集和回归判定五个阶段。

**构建阶段**需要生成目标 APK 与测试 APK。目标应用采用 release-like 的 `benchmark` 变体：关闭 debuggable，保留 R8/资源压缩配置，只把签名换成 CI 可用的密钥。下面是应用模块的基础配置：

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

`matchingFallbacks` 主要解决多模块工程的变体匹配；单模块项目不一定需要。目标 APK 还要包含 `<profileable>`，并按当前 Macrobenchmark 文档接入 ProfileInstaller 1.3 或更新版本。

**设备准备阶段**固定型号、Android build fingerprint、电量区间、充电方式、网络、屏幕亮度、刷新率、账号与后台应用。AndroidX Benchmark 会检查低电量、模拟器、debuggable 等错误，也会在 Microbenchmark 中检测热降频并暂停等待冷却。rooted Microbenchmark 设备可用 `lockClocks`；Macrobenchmark 不使用这项锁频方案。

**执行阶段**按用途分层：

- PR 冒烟：`dryRunMode` 或只运行少量场景，目标是发现构建、安装、权限和元素定位错误。
- 夜间趋势：固定少量物理设备，运行完整迭代并保存全部产物。
- 发布候选：在固定趋势设备之外增加一组机型，用于发现厂商系统或屏幕配置相关问题。

模拟器适合 PR 阶段验证脚本能否执行。Benchmark 会把模拟器判为配置错误；即使通过 `suppressErrors` 继续运行，产物也只能用于诊断，不能写入物理设备的性能基线。

**产物收集阶段**保存 JSON 与 `.perfetto-trace`，并把 Git commit、目标 APK 哈希、测试 APK 哈希和设备指纹写入同一次运行记录。Macrobenchmark 每个测量迭代一份 Trace；Microbenchmark 每个 `measureRepeated` 一份 Trace。

**回归判定阶段**比较同名测试、同名指标、同一启动/编译模式和同类设备。启动看 median，帧指标看 P50 与尾部分位，功耗看设备是否支持对应数据源。阈值应从该设备的历史方差与业务预算推导，不能给所有项目套一个固定百分比。

### Firebase Test Lab 与 GitHub Actions

Firebase Test Lab 可以运行 instrumentation APK，并把指定目录拉到 Cloud Storage。设备目录会变化，提交测试前先查当前型号与系统组合：

```bash
gcloud firebase test android models list
gcloud firebase test android models describe <MODEL_ID>
gcloud firebase test android versions list
```

命令输出会标明型号、可用 OS、ABI 以及物理/虚拟类型。性能趋势应固定物理型号和 OS；云端每次可能分配不同设备实例，因此要保留设备上下文，并用多次运行估计噪声。

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

APK 文件名会随 flavor、AGP 和项目配置变化，`APP_APK`、`TEST_APK` 必须按构建产物调整。`additionalTestOutputDir` 配合 `--directories-to-pull` 让 FTL 把 JSON 与 Trace 放入结果 bucket；`androidx.benchmark.enabledRules=Macrobenchmark` 避免同一模块中的 Baseline Profile 规则混入本轮。

Google 的 [performance-samples FTL workflow](https://github.com/android/performance-samples/blob/main/.github/workflows/firebase_test_lab.yml) 可作为完整参考。不要用 `bucket/latest/*.json` 猜测结果路径；应读取本次 gcloud 返回的 matrix 信息，或由 Cloud Storage 事件处理本次结果目录。

### 结果持久化与趋势追踪

JSON 的 `context` 包含设备型号、build fingerprint 和 CPU 等信息。入库时把上下文与测试名、参数、指标数组一起保存，不能只取一个 median 数字。设备重刷系统、Benchmark 库升级、编译模式变化或基线 profile 更新时，应建立新基线，避免把环境迁移显示成代码回归。

告警可采用“相对近期稳定窗口 + 绝对体验预算”双条件。相对窗口发现小幅持续退化，绝对预算防止历史基线本身已经过慢。命中告警后查看对应迭代 Trace；只靠百分比无法区分应用回归、温度变化、系统任务和云设备实例差异。

Android 17 的平台分析锚点是 `android-17.0.0_r1`，内核侧是 [`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)。量产设备通常还包含厂商内核提交、调频策略和 thermal 配置，所以同为 API 37 也不能直接合并结果。趋势库必须以设备 build fingerprint 分组。

### 门禁统计与噪声处理

不同指标使用不同摘要：启动以 median 为主并保留每次迭代值；帧指标查看 `frameOverrunMs` 的 p90/p95/p99 并保存慢帧 trace；自定义 section 明确 count、sum 或 first；功耗只做同机、稳定窗口的系统级 A/B。一次 benchmark invocation 内的多个 iteration 共享温度、缓存和后台状态，不能当作多个独立设备样本。

AndroidX JSON schema 会随库版本扩展。门禁前先把原始结果转换为内部稳定结构，并校验 benchmark、metric、unit、device/build fingerprint、compilation mode、iteration 数、APK hash 和实验区组。字段缺失时中止比较，不把缺失值当成 0。

稳定门禁采用配对设计：同一设备和环境区组内分别运行 baseline 与 candidate，交替或随机安排顺序，每次 invocation 先形成一个摘要，再把多轮独立摘要组成 pairs。预算同时包含业务定义的绝对增量和相对增量；样本不足直接拒绝比较，置信区间跨越门槛时标为 inconclusive，待设备冷却后补充独立配对。不能重复抽样同一次 invocation 的 iteration 来凑独立样本。

噪声控制至少记录电量与充电状态、thermal、CPU frequency/idle、刷新率、后台账号与每轮时间。若后半段随温度单调变慢，应停止并冷却设备。网络使用固定离线数据、测试服务器或录制响应，账号、缓存、AB flag 和列表内容都要固定。

`StartupMode.COLD` 会停止目标进程，默认配置还可能清理 shader cache 并请求系统清理 page cache；这不等于设备重启后的所有缓存都为空。DNS、GPU 驱动、系统服务和业务数据缓存各有生命周期。page cache 清理影响整机，同一性能设备上不要并行运行其它任务，也不要在外层脚本重复清理。

指标退化后，找到 candidate 的异常迭代及同设备 baseline，按相同 journey 边界比较 trace：启动检查 process start、Binder、class load、GC、I/O 和首帧；帧问题检查 FrameTimeline、UI thread、RenderThread、GPU 与 SurfaceFlinger；最后用版本化 Trace Processor SQL 量化同一时间窗。门禁负责发现回归，trace 负责解释原因。

## 在 Perfetto 中的表现

Gradle 执行成功后，JSON 与 Trace 会被拉到模块构建目录。下面是当前官方文档给出的主机路径：

```text
project_root/module/build/outputs/connected_android_test_additional_output/debugAndroidTest/connected/device_id/
```

`module` 是 Macrobenchmark 或 Microbenchmark 模块名，`device_id` 由 Gradle 按设备生成。Macrobenchmark 目录中每个测量迭代各有一份 `.perfetto-trace`，文件名包含测试、参数与迭代编号。

启动 Trace 的阅读顺序可以固定为：

1. 在 App Startups 或启动相关 slice 中确认 launch、TTID、TTFD 边界。
2. 沿目标进程主线程查看 `ActivityThread`、`bindApplication`、`Activity` 生命周期和首帧 `Choreographer#doFrame`。
3. 查看 RenderThread、GPU queue 与 FrameTimeline，区分 UI 线程、RenderThread、GPU 和 SurfaceFlinger 侧等待。
4. 用 Binder、线程调度和 CPU frequency 轨道解释空洞或抢占，避免把所有墙钟时间都归给应用函数。

滚动 Trace 应以 FrameTimeline 的 expected/actual slice 和 jank 标记为主，再回到主线程 `doFrame`、RenderThread 与 GPU 轨道。单看 `doFrame` 是否超过固定 16.67 ms 会误判高刷新率、可变刷新率以及 GPU / 合成侧超期。

## 常见问题与误区

**模拟器能不能运行基准测试？** 可以用来验证构建、安装和脚本路径，但 AndroidX Benchmark 会报告模拟器配置错误。抑制错误后产生的数据不能和物理设备比较，也不能作为发布门禁。

**Microbenchmark 数字更稳定，能否替代 Macrobenchmark？** 不能。Microbenchmark 适合循环热点，缓存与 AOT 状态接近最佳情况；启动、进程创建、系统服务和完整渲染仍要由 Macrobenchmark 与系统 Trace 判断。

**Macrobenchmark 能否放进应用模块？** 不能。它要求独立的 `com.android.test` 模块，从目标应用进程外启动和停止应用。Microbenchmark 可放在专用 benchmark 模块中，并依赖包含被测代码的模块。

**迭代次数是否固定为 10？** 没有统一数字。短而稳定的热点可能需要更多样本，长启动场景受 CI 时长限制。先在固定设备上观察分布与热状态，再选择能稳定区分目标回归幅度的迭代数；报告保留 median、尾部分位和原始样本。

**设备温度与调度噪声能否全部消除？** 不能。固定设备状态、等待冷却、减少账号和后台任务可以压低噪声，仍会受到 DVFS、thermal 和内核调度影响。测试记录应绑定 Android build fingerprint；分析 Android 17 通用内核行为时再对照 `android17-6.18-2026-06_r6`，不能用通用内核标签替代量产机证据。

**Espresso 能否驱动 Macrobenchmark？** Macrobenchmark 使用外部测试 APK，Espresso 的 View matcher 与同步机制面向目标应用 instrumentation 环境。完整性能场景使用 UI Automator；Espresso 保留在功能回归测试中。

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
