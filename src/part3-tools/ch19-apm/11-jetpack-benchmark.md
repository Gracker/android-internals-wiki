---
title: Jetpack Benchmark（Microbenchmark + Macrobenchmark）
chapter: '19'
section: '19.11'
applicable_versions: Benchmark 1.4.1 Microbenchmark：Android 5.0+（API 21+）；Macrobenchmark：Android 6.0+（API 23+）；Benchmark 1.5.0-rc01：API 24+；Baseline Profile 生成需 API 33+ 或 rooted API 28+；收益验证需 API 24+
last_verified: '2026-08-14'
last_verified_against: AndroidX Benchmark 1.4.1 stable and 1.5.0-rc01 artifacts + BlackHole / BenchmarkState / BaselineProfileRule / CompilationMode / Metric sources + Android Developers Benchmark docs
confidence: medium
tags:
- apm
related_chapters:
- '19.0'
sources:
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/benchmark/BlackHole
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/benchmark/macro/junit4/BaselineProfileRule
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/benchmark
- type: official
  path: https://dl.google.com/android/maven2/androidx/benchmark/benchmark-common/maven-metadata.xml
- type: official
  path: https://dl.google.com/android/maven2/androidx/benchmark/benchmark-common/1.5.0-rc01/benchmark-common-1.5.0-rc01.aar
- type: official
  path: https://dl.google.com/android/maven2/androidx/benchmark/benchmark-common/1.5.0-rc01/benchmark-common-1.5.0-rc01-sources.jar
- type: official
  path: https://dl.google.com/android/maven2/androidx/profileinstaller/profileinstaller/maven-metadata.xml
status: "finalized"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
---
# Jetpack Benchmark（Microbenchmark + Macrobenchmark）

## Benchmark 给优化结论提供可重复实验

Jetpack Benchmark 用于回答一个受约束的问题：同一场景、同一设备和同一编译状态下，candidate（待评估版本）相对 baseline（基准版本）变快了还是变慢了。它会管理测量循环、采集指标并保存结果；它不采集真实用户分布，也不替代线上 APM（Application Performance Monitoring，应用性能监控）、Android Vitals、JankStats 或故障样本。

这两类证据可以互相接续：

1. 线上数据定位到受影响的机型、页面和业务阶段。
2. 团队把该阶段压缩成可重复的本地数据与交互脚本。
3. Benchmark 对基线提交和候选提交执行同一实验。
4. 数字发生变化时，打开随迭代生成的 Perfetto trace（系统执行时间线）解释原因。
5. 修复上线后，再由线上指标确认真实用户分布是否改善。

线上 P95 与实验室 median（中位数）的样本来源、设备分布和负载都不同，不能直接相减。P95 表示 95% 的观测值不超过该数值。可以比较两者指向的阶段以及变化方向，数值门槛必须各自维护。

## 2026 年版本与平台锚点

截至 2026-08-14，AndroidX Benchmark 的稳定版是 `1.4.1`，预发布版是 `1.5.0-rc01`。示例继续使用 stable 1.4.1，并以 Android 17 / API 37 / `android-17.0.0_r1` 为最高平台锚点。

| 能力 | stable 1.4.1 的运行下限 | 使用边界 |
|---|---:|---|
| Microbenchmark | API 21 | 进程内、可重复调用的局部代码 |
| Macrobenchmark | API 23 | 独立测试进程驱动目标应用 |
| `CompilationMode.None` / `Partial` | API 24 | API 23 仅支持 `Full` |
| `BaselineProfileRule` 生成 | 非 root API 33+；rooted API 28+ | 生成环境与收益验证环境分开 |
| Baseline Profile 收益验证 | API 24+ | `Partial(BaselineProfileMode.Require)` 与 `None()` 对照 |
| `FrameTimingMetric.frameOverrunMs` | API 31+ | Android 17 可直接使用 |
| `PowerMetric` | API 29+ | 还要检查设备是否支持所选 power rail |

旧资料中常见的“Microbenchmark 支持 API 14”不适用于当前 stable artifact（Maven 仓库中的发布组件）：`benchmark-common:1.4.1` 与 `benchmark-junit4:1.4.1` 的 AAR manifest 都声明 `minSdkVersion=21`。Macrobenchmark 两个 Android AAR 则声明 `minSdkVersion=23`。

Benchmark 1.5.0-rc01 的四个 Android AAR 都把 `minSdkVersion` 提到 24；该预发布线还采用 UiAutomator 2.4，稳定化 `BlackHole`，并支持采集和合并 AndroidX Tracing 2.0 的进程内 trace。stable 1.4.1 的 `BlackHole` 仍标注为 experimental，代码需要显式 opt-in（主动接受实验 API），不能用预发布版状态描述稳定版 API。

## Microbenchmark：只测可重复的局部工作

Microbenchmark 在测试进程内反复执行同一段代码，适合纯 CPU 或内存分配路径，例如：

- JSON、Protocol Buffers（Proto）、图片元数据等解析和编码。
- diff（新旧数据的差量计算）、排序、查找、正则与格式转换。
- 小块图像处理、向量或数值运算。
- 缓存命中路径、对象池与数据结构操作。

以下对象不适合放进 Microbenchmark：

- 冷启动、页面切换和列表滚动。
- 一次执行就改变全局状态、难以恢复的操作。
- 强依赖网络、磁盘冷缓存、Binder 或系统调度的端到端路径。
- 低频且每次行为明显不同的初始化工作。

### Warmup、JIT 与 AOT 要写进实验说明

`BenchmarkRule` 会自己执行 warmup（预热，先重复运行以稳定运行时状态）和测量阶段，不要在 `measureRepeated` 里再套手工次数循环。JIT 是运行时把热点代码编译为机器码，AOT 是运行前预先编译；实验采用哪种编译状态取决于工程配置：

- 使用 Benchmark `1.3.0-beta01+`、Android Gradle Plugin（AGP）`8.4.0+` 并应用 `androidx.benchmark` Gradle 插件时，Microbenchmark APK 默认 full AOT，目标是减少 JIT 稳定时间和结果波动。
- 设置 `androidx.benchmark.forceaotcompilation=false` 会退出这一默认行为，结果更接近 warmup 后的 JIT 状态。
- 两组结果只在编译配置一致时才可比较。报告要记录 Benchmark、AGP、Kotlin、R8 代码优化/压缩工具和该开关。

full AOT 让实验更稳定，却不保证结果代表用户设备的常态编译状态。局部优化若依赖 JIT 行为，应再增加一组关闭强制 AOT 的实验，并清楚标记口径。

### 循环里只保留被测工作

下面的例子测量固定 100 条数据的 JSON 解析。fixture 是可重复使用的固定测试数据，seed 是生成它的固定随机种子。fixture 在 `@Before` 中准备；循环内只有解析和防止消除的消费操作；结果校验放到循环外。

```kotlin
import androidx.benchmark.BlackHole
import androidx.benchmark.ExperimentalBlackHoleApi
import androidx.benchmark.junit4.BenchmarkRule
import androidx.benchmark.junit4.measureRepeated
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@OptIn(ExperimentalBlackHoleApi::class)
@RunWith(AndroidJUnit4::class)
class FeedParserBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    private lateinit var parser: FeedParser
    private lateinit var payload: String

    @Before
    fun setUp() {
        parser = FeedParser()
        payload = Fixtures.feedJson(itemCount = 100, seed = 42)
        check(parser.parse(payload).size == 100)
    }

    @Test
    fun parse100Items() = benchmarkRule.measureRepeated {
        val result = parser.parse(payload)
        BlackHole.consume(result)
    }
}
```

被测对象是 `parser.parse(payload)`；准备数据固定为 seed 42；循环由 Benchmark 管理；指标是执行时间与库采集的分配信息；准备阶段会校验条目数，解析异常则直接让测试失败。`BlackHole.consume()` 防止编译器或 R8 把未使用的结果连同计算一起删除。该结果只能说明这一固定输入下的局部解析成本。

可变状态要在每轮恢复，但恢复成本不应混进算法时间。下面的片段演示对原数组做副本，再只测排序。

```kotlin
benchmarkRule.measureRepeated {
    val working = runWithMeasurementDisabled {
        fixture.copyOf()
    }
    sorter.sort(working)
    BlackHole.consume(working[0])
}
```

stable 1.4.1 推荐使用 `runWithMeasurementDisabled()`；旧名 `runWithTimingDisabled()` 已弃用，因为暂停的是所有 measurement（测量指标），不只计时。暂停区也会反复执行，所以其中仍应保持轻量和确定性。

### 常见测错方式

| 写法 | 测到的内容 | 修正 |
|---|---|---|
| 循环内生成随机数据 | 随机数和分配成本 | 固定 seed，在 `@Before` 准备 fixture |
| 循环内打印日志 | I/O、锁和 Logcat 成本 | 移除日志 |
| 循环内做断言 | 断言与异常消息准备 | 只校验末次结果 |
| 返回值无人使用 | 计算可能被编译器或 R8 删除 | 1.4.1 用 opt-in 后的 `BlackHole.consume()` |
| 原地排序同一个数组 | 首轮后输入已排序 | 每轮在 measurement 外复制 |
| 手工执行一万次 | 多套循环与 Benchmark 的 warmup 混在一起 | 每个 `measureRepeated` block 表示一次操作 |
| 在主线程调用普通 `measureRepeated` | 长测量可能触发 ANR（应用无响应） | UI microbenchmark 使用 `measureRepeatedOnMainThread()` |
| 只测缓存命中却声称代表冷路径 | 结论对象错位 | 明确 cache state（缓存是否已有数据），必要时改用 Macrobenchmark |

Java 仍可通过 `BenchmarkRule.getState()` 和 `while (state.keepRunning())` 驱动旧式循环；Kotlin 代码应使用 `measureRepeated {}`，减少忘记结束状态机或错误暂停计量的风险。

## Macrobenchmark：从外部进程测完整用户路径

Macrobenchmark 使用单独安装的 test APK（只包含测试与控制代码的应用包）控制目标应用，适合启动、滚动、转场、动画和关键用户旅程。它的控制流可概括为：

```text
重置目标应用的编译状态
  -> 按 CompilationMode 编译或安装 profile
  -> repeat(iterations) {
       setupBlock：把应用放到统一起点，不计入 metrics
       开始 Perfetto 采集
       measureBlock：执行被测交互
       停止采集并提取 metrics
     }
```

`setupBlock` 不计入指标，但它决定每轮起点是否一致。`measureBlock` 里任何等待都会进入 trace 的测量窗口；某项 metric 是否计入这段等待，则由该 metric 的定义决定。

### `StartupMode` 只描述进程和 Activity 起点

| 模式 | 开始时的状态 | 不能推出的结论 |
|---|---|---|
| `COLD` | 目标进程不存在，需要进程创建和 Activity 创建 | 不等于首次安装，也不自动清应用数据 |
| `WARM` | 进程存活，需要新建并显示 Activity | 不等于页面数据已缓存 |
| `HOT` | 进程与 Activity 存活，把现有 Activity 带回前台 | 不等于零工作量 |

冷启动实验要另外记录登录态、数据库、磁盘缓存、shader cache（图形着色器编译缓存）和编译状态。只写 `StartupMode.COLD` 还不足以复现实验。

### `CompilationMode` 决定代码处于什么编译状态

这里的 profile 是运行时或构建阶段记录的热点代码清单，Android Runtime（ART）可据此决定优先编译哪些方法。

| 模式 | API 24-37 行为 | 用途 |
|---|---|---|
| `DEFAULT` | `Partial(BaselineProfileMode.UseIfAvailable)` | 模拟安装后可用 profile 的默认体验；profile 缺失时不失败 |
| `None()` | 清除预编译，运行时可发生 JIT | 看 fresh install（刚安装且尚无 profile）无 Baseline Profile 的较差口径 |
| `Partial(Require)` | 安装 APK 内 Baseline Profile，并以 `speed-profile` 编译清单命中的方法 | 验证 profile 能否安装和使用 |
| `Partial(Disable, warmupIterations=N)` | 用 N 次 warmup 生成运行时 profile 后部分编译 | 模拟使用一段时间后的 profile-guided 状态 |
| `Full()` | 以 `speed` 全量 AOT 编译方法 | 稳定性或上限对照；不代表现代用户设备常态 |
| `Ignore()` | 不重置、不改变外部准备的编译状态 | 由脚本管理编译时使用 |

API 23 只有 `Full()`。`Full()` 也不保证一定更快：更大的已编译代码可能增加磁盘读取与 instruction cache（CPU 存放近期执行指令的缓存）压力。验证 Baseline Profile 应使用 `Partial(BaselineProfileMode.Require)` 与 `None()` 成对比较，不能用 `DEFAULT` 代替严格验证。

Android 14 / API 34 之前，Macrobenchmark 为重置编译状态可能重装目标 APK，从而丢失应用数据。依赖预置账号或数据库的场景需要在每次重装后重新准备，或者由外部脚本控制编译并使用 `CompilationMode.Ignore()`。Android 14 及以上才适合在这一步保留应用状态。

## 工程结构：把测量代码与目标应用隔开

推荐结构如下：

```text
:app                 目标应用，提供接近 release 的 benchmark build type
:benchmarkable       可选；暴露给 Microbenchmark 的纯逻辑
:microbenchmark      com.android.library，进程内测局部代码
:macrobenchmark      com.android.test，从外部驱动 :app
```

`:app` 不应为了 benchmark 关闭 R8、保留 debug 日志或改变业务实现。build type 是同一应用的构建配置变体；`benchmark` build type 应继承 release 的压缩和优化，仅用本地签名方便安装。

下面是目标应用需要关注的核心配置。

```kotlin
// :app/build.gradle.kts
android {
    compileSdk = 37

    defaultConfig {
        targetSdk = 37
    }

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
            isDebuggable = false
            signingConfig = signingConfigs.getByName("debug")
            matchingFallbacks += listOf("release")
        }
    }
}

dependencies {
    implementation("androidx.profileinstaller:profileinstaller:1.4.1")
}
```

`matchingFallbacks` 让没有 `benchmark` build type 的依赖模块选择 `release`。ProfileInstaller 负责把 Baseline Profile 交给系统，也提供 Macrobenchmark 清 shader cache、采集和重置 profile 所需的命令通道；1.3+ 满足要求，这里固定到当前稳定版 1.4.1 便于复现。

目标应用 manifest 还要允许 shell profiling，即允许 adb shell 启动的受控工具采集性能数据。下面的元素位于 `<application>` 内，target app 必须保持 non-debuggable（不可附加普通调试器）。

```xml
<profileable
    android:enabled="true"
    android:shell="true" />
```

这允许测试与 profiling 工具读取详细 trace，不会把目标应用变成 debuggable。Android Studio 的 Benchmark module 模板会自动添加相应配置，手工工程要检查最终合并 manifest。

Macrobenchmark module 使用 `com.android.test`，核心配置如下。

```kotlin
// :macrobenchmark/build.gradle.kts
plugins {
    id("com.android.test")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.example.macrobenchmark"
    compileSdk = 37

    defaultConfig {
        minSdk = 23
        targetSdk = 37
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        create("benchmark") {
            isDebuggable = true
            signingConfig = getByName("debug").signingConfig
            matchingFallbacks += listOf("release")
        }
    }

    targetProjectPath = ":app"
    experimentalProperties["android.experimental.self-instrumenting"] = true
}

dependencies {
    implementation("androidx.benchmark:benchmark-macro-junit4:1.4.1")
    implementation("androidx.test.ext:junit:1.3.0")
}

androidComponents {
    beforeVariants(selector().all()) {
        it.enable = it.buildType == "benchmark"
    }
}
```

测试代码放在这个 test-only module 的 `src/main`。test APK 的 `benchmark` variant 可以 debuggable，受测的 `:app` benchmark APK 必须保持 non-debuggable；两者不要混淆。`self-instrumenting` 让测试 APK 与目标应用分进程运行。`benchmark-macro-junit4:1.4.1` 已依赖 UI 自动化库 UiAutomator 2.3.0；若项目显式覆盖 UiAutomator 版本，需要重新验证选择器与手势行为。

Microbenchmark module 应应用与依赖同版本的 Gradle 插件。

```kotlin
// 根 build.gradle.kts
plugins {
    id("androidx.benchmark") version "1.4.1" apply false
}

// :microbenchmark/build.gradle.kts
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("androidx.benchmark")
}

android {
    compileSdk = 37
    defaultConfig {
        minSdk = 21
        testInstrumentationRunner =
            "androidx.benchmark.junit4.AndroidBenchmarkRunner"
    }

    testBuildType = "release"
}

dependencies {
    androidTestImplementation(project(":benchmarkable"))
    androidTestImplementation("androidx.benchmark:benchmark-junit4:1.4.1")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
}
```

插件会配置 benchmark 输出复制、AOT 默认行为和 rooted 设备的 `lockClocks` task；`lockClocks` 用来固定 CPU 时钟，减少频率变化带来的噪声。被测代码宜放到 `:benchmarkable`，避免为调用应用内部实现而把整个 debug app 拉进测试。

## 示例一：可判定失败的 cold startup

下面的例子测量目标应用的冷启动。测试数据由目标应用的 benchmark variant 提供固定本地 fixture；`home_ready` 是测试可以观察的 ready sentinel（就绪标记），只有在首屏数据和可交互状态准备完成后才出现；应用在同一时点调用 `reportFullyDrawn()`。

```kotlin
import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.StartupTimingMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@LargeTest
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartup() = benchmarkRule.measureRepeated(
        packageName = PACKAGE_NAME,
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.DEFAULT,
        startupMode = StartupMode.COLD,
        iterations = 10,
        setupBlock = {
            pressHome()
        }
    ) {
        startActivityAndWait()
        check(
            device.wait(
                Until.hasObject(By.res(PACKAGE_NAME, "home_ready")),
                5_000
            )
        ) {
            "Home did not become ready within 5 seconds"
        }
    }

    private companion object {
        const val PACKAGE_NAME = "com.example.app"
    }
}
```

被测对象是从 launch intent（启动 Activity 的意图）到首帧和 `reportFullyDrawn()` 的启动过程；每轮由 `StartupMode.COLD` 杀进程，应用数据不自动清除；指标是 TTID（Time to Initial Display，首帧显示时间）与可用时的 TTFD（Time to Full Display，完整内容显示时间）；找不到 ready sentinel、没有启动事件或超时都会让测试失败。10 次适合观察 median 和逐次 trace，不足以稳定估计 P95，若 CI 要使用 P95，需要增加样本并从 JSON 的 `runs` 计算。

`startActivityAndWait()` 只保证启动 Activity 并等待平台可观察的启动完成。额外的 `home_ready` 检查用于防止下一轮在异步数据仍加载时开始；TTFD 是否正确仍取决于应用报告 fully drawn 的时机。

## 示例二：只把列表滚动放进测量窗口

滚动实验不应把启动、登录和网络等待混入 `FrameTimingMetric`。下面的 benchmark deep link（直接打开指定页面的应用内链接）载入固定 1000 条本地数据并回到列表顶部，准备动作放在 `setupBlock`；测量窗口只包含一次向下 fling（带惯性的快速滚动）。

```kotlin
import android.content.Intent
import android.net.Uri
import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.FrameTimingMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Direction
import androidx.test.uiautomator.Until
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@LargeTest
@RunWith(AndroidJUnit4::class)
class FeedScrollBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun flingDown() = benchmarkRule.measureRepeated(
        packageName = PACKAGE_NAME,
        metrics = listOf(FrameTimingMetric()),
        compilationMode = CompilationMode.DEFAULT,
        startupMode = null,
        iterations = 10,
        setupBlock = {
            pressHome()
            startActivityAndWait(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse("example://benchmark/feed?count=1000&seed=42")
                )
            )
            check(
                device.wait(
                    Until.hasObject(By.res(PACKAGE_NAME, "feed_ready")),
                    5_000
                )
            )
        }
    ) {
        val list = checkNotNull(
            device.findObject(By.res(PACKAGE_NAME, "feed_list"))
        )
        list.setGestureMargin(device.displayWidth / 5)
        check(list.fling(Direction.DOWN)) {
            "Feed list could not fling down"
        }
        device.waitForIdle()
    }

    private companion object {
        const val PACKAGE_NAME = "com.example.app"
    }
}
```

被测对象是确定数据集上的一次 fling；每轮准备同一 deep link 和列表起点；指标是 frame duration、API 31+ 的 frame overrun 以及 frame count；页面未就绪、列表不存在或手势失败会中止测试。`device.waitForIdle()` 位于测量窗口，因此列表滚动到静止的全过程都会被 trace 覆盖。

网络不能成为这个回归测试的随机变量。需要覆盖网络解析时，应使用本地 mock server（按预设响应请求的测试服务器）、固定响应、固定延迟策略，并把“网络实验”和“渲染实验”分成不同场景。

## 指标要按定义阅读

### `StartupTimingMetric`

它输出：

- `timeToInitialDisplayMs`：系统收到 launch intent 到目标 Activity 第一帧完成。
- `timeToFullDisplayMs`：到应用 `reportFullyDrawn()` 所在或之后第一帧完成；API 29 前可能不可用。

TTID 低只说明用户较快看到第一帧。若首屏仍是骨架屏或不可交互，业务目标要看 TTFD，并审计 `reportFullyDrawn()` 是否过早、过晚或从未调用。

### `FrameTimingMetric`

它输出每帧样本并在多次迭代后形成分位数：

- `frameDurationCpuMs`：UI thread 与负责提交绘制命令的 RenderThread 产出一帧的 CPU duration；API 31 前无法计入 `Choreographer#doFrame` 开始前的时间。
- `frameOverrunMs`：API 31+ 相对帧 deadline（系统给这一帧分配的时间预算）的超期或余量；正值表示超过 deadline，负值表示仍有余量。
- `frameCount`：测量窗口内产出的帧数，用来解释“删掉无效帧后分位数上升”之类的样本变化。

变刷新率设备上优先使用 `frameOverrunMs` 判断 deadline 表现。它仍需与 FrameTimeline（记录每帧生命周期的系统时间线）、主线程、RenderThread 和 GPU 轨道一起读，不能仅凭一个分位数定位根因。

### `TraceSectionMetric`

stable 1.4.1 中它仍标注为 `ExperimentalMetricApi`。默认 `mode` 是 `Mode.Sum`，会输出匹配 slice 的总时长和次数；还可以选择 `First`、`Min`、`Max`、`Count`、`Average`。默认只匹配目标包，未闭合且 `dur = -1` 的 slice 会被忽略。

使用时必须明确 mode。`First` 只取第一条；`Sum` 遇到递归或重入 section 时可能把重叠时间重复相加。业务 trace 名称要稳定，且要打开每轮 Perfetto trace 确认选中了预期 section。

### `PowerMetric`、`MemoryUsageMetric` 与 `ArtMetric`

- `PowerMetric` 从 API 29 可用，仍是 experimental。高精度 energy/power 依赖设备 power rail（硬件提供的分项能耗计数）；使用前检查 `deviceSupportsHighPrecisionTracking()` 与最低电量。
- `MemoryUsageMetric` 可查询 heap、RSS（进程驻留在物理内存中的大小）、GPU 等子指标，适合固定操作窗口；它不能代替线上 OOM（内存不足）和 LMKD（系统低内存终止进程）证据。
- `ArtMetric` 从 API 24 可用，可观察 Android Runtime（ART）的 JIT compilation、类加载和校验情况，适合验证 Baseline Profile 是否减少启动期运行时工作。

功耗实验需要固定设备、亮度、网络、温度、电池电量和操作时长。短场景的功耗差异常被采样噪声掩盖，需延长稳定阶段并用相同物理设备比较。

## 测试条件就是结果的一部分

每份报告至少记录以下信息：

| 类别 | 必填字段 |
|---|---|
| 代码 | baseline SHA、candidate SHA（两次提交的内容哈希）、applicationId、version、variant、R8 配置 |
| 工具 | Benchmark、AGP、Kotlin、JDK、ProfileInstaller 版本 |
| 设备 | model、device codename、系统构建 fingerprint、API、kernel tag、是否 root |
| 运行 | `CompilationMode`、`StartupMode`、iterations、fixture seed、账号和缓存状态 |
| 环境 | 电量、充电状态、thermal sleep（因设备过热而等待降温的时间）、刷新率、动画设置、网络模式 |
| 结果 | metric、方向、runs、median、适用时的 p90/p95/p99、基线差值 |
| 证据 | benchmark JSON、每轮 Perfetto trace、测试日志 |

Android 17 设备的报告应记录 `android-17.0.0_r1` 对应系统构建信息。若结论涉及 Perfetto 中的 CPU 调度或唤醒事件，kernel 源码核验统一使用 `android17-6.18-2026-06_r6`；Benchmark 库行为仍以 AndroidX 1.4.1 源码为准。

还要固定这些实验条件：

- 使用物理设备作为性能门禁。模拟器可跑 smoke test（只验证流程可运行的快速检查），但数字受宿主机影响。
- 同一对比只使用相同型号、系统 fingerprint 和刷新率。
- 关闭省电模式，避免后台同步与系统更新，控制设备散热。
- Microbenchmark 可在 rooted 设备使用 `lockClocks`；官方 CI 指南明确说明该措施只用于 Microbenchmark。
- Macrobenchmark 让库处理 thermal throttling（温控降频）等待；报告保留 `thermalThrottleSleepSeconds`。
- UI 场景使用稳定 resource id 或 Compose `testTagAsResourceId`，不要依赖文本和屏幕坐标。
- 每轮数据、登录态、页面起点与网络响应一致。

系统动画是否关闭取决于测试目标。若要测应用转场动画，关闭动画会改变被测对象；若只想测布局与列表工作，可关闭系统级无关动画。报告必须写明选择。

## CI：先量化噪声，再定义门禁

这里的门禁是 CI 根据性能预算自动放行或阻止代码变更的规则。

Benchmark 结果是连续数值，不能像普通单元测试那样仅看一次 pass/fail。建议按以下方式建设门禁：

1. 固定一小组物理设备，建立每台设备自己的历史序列。
2. 对 main 分支定时运行，估计每个 metric 的自然波动带。
3. PR 在同型号、同 fingerprint 设备上运行 baseline 与 candidate。
4. 只有差值同时超过业务容忍值和历史噪声带时，才判为回归。
5. 首次越界自动在同一设备重跑；两轮方向一致再阻断。
6. 保留 raw JSON 与 trace，人工复核测试起点、样本数和异常系统负载。

对“越小越好”的耗时指标，可以使用如下门槛：

`candidateMedian - baselineMedian > max(业务绝对预算, 历史噪声上界)`

历史噪声可用稳定窗口的 MAD（Median Absolute Deviation，中位数绝对偏差）、置信区间或团队已有统计模型估算。不要在没有历史数据时随意写“慢 8% 就失败”；不同场景的信噪比，即真实变化相对随机波动的强弱，差异很大。

样本数也影响统计口径：

- 启动做 10 次时，适合看 median 和逐次 trace，P95 接近极值。
- 帧指标一轮就有许多帧样本，可以看 p90/p95/p99，但要同时看 frame count。
- 功耗与稀疏事件需要更长测量窗口，而不只是增加启动次数。

官方 Gradle 运行会把 JSON 和 trace 复制到 `build/outputs/connected_android_test_additional_output/...`。Macrobenchmark 每个 measured iteration（计入指标的一轮）生成一份 Perfetto trace；Microbenchmark 每个测试通常生成一份覆盖全部迭代的 trace。CI 应按 commit、设备和场景归档原始 JSON 与 trace，不能只保留控制台摘要。

`androidx.benchmark.suppressErrors` 会把 debuggable、模拟器、低电量等配置错误降为警告。它可用于只检查脚本能否跑通的 smoke job（快速验证任务），不应出现在性能门禁。

## 从线上问题构造 Benchmark

线上异常转成实验场景时，按四个问题收敛：

| 问题 | 需要固定的内容 |
|---|---|
| 哪类设备受影响 | SoC（System on Chip，片上系统）、API、刷新率、内存档位 |
| 哪个业务阶段受影响 | 页面、操作、稳定 trace 名称 |
| 哪种输入触发 | 数据规模、缓存状态、账号形态、网络响应 |
| 什么结果算修复 | 指标方向、绝对预算、相对基线与噪声带 |

例如，线上 JankStats 显示 `screen=Home, phase=feed_submit` 的慢帧率上升，可以构造固定 1000 条 feed 的 Macrobenchmark，并让应用保留 `Home#submitFeed` trace。`FrameTimingMetric` 证明帧 deadline 是否改善，`TraceSectionMetric` 检查提交阶段，Perfetto 再确认主线程、RenderThread 或调度证据。

若 Perfetto 把耗时缩小到纯解析函数，再增加 Microbenchmark。这样端到端测试保护用户路径，局部测试保护算法成本，两者共同指向同一业务阶段。

## Baseline Profiles：生成与验证是两项任务

Baseline Profile 是随 APK 发布的热点方法和类清单，ART 可据此提前编译常用路径。producer（生成方）通常复用 `:macrobenchmark`，或使用独立 `:baselineprofile` 的 `com.android.test` module；consumer（消费方）是把 profile 打进 APK 的目标 `:app`。AGP 8.2+ 可直接使用 Android Studio 的 Baseline Profile Generator 模板，减少 variant 与文件复制配置。

生成启动 profile 的最小测试如下。`includeInStartupProfile = true` 会把启动入口到 fully drawn（应用报告完整内容已显示）的路径纳入启动 profile；普通滚动或二级页面旅程应另建 `collect()` 并保持为 `false`。

```kotlin
import androidx.benchmark.macro.junit4.BaselineProfileRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val baselineProfileRule = BaselineProfileRule()

    @Test
    fun startup() = baselineProfileRule.collect(
        packageName = PACKAGE_NAME,
        includeInStartupProfile = true,
        strictStability = true
    ) {
        pressHome()
        startActivityAndWait()
        check(
            device.wait(
                Until.hasObject(By.res(PACKAGE_NAME, "home_ready")),
                5_000
            )
        )
    }

    private companion object {
        const val PACKAGE_NAME = "com.example.app"
    }
}
```

生成环境要求非 root API 33+，或 rooted（已获得系统 root 权限）API 28+；这只是 profile 收集门槛。收益验证要回到实际发布设备段，并至少成对运行：

- `CompilationMode.None()`：无预编译对照。
- `CompilationMode.Partial(BaselineProfileMode.Require)`：要求 APK 内 profile 可安装，否则直接失败。

两组测试使用相同目标 APK、fixture、设备和 iteration。`Partial(Require)` 需要 API 24+、APK 由 AGP 7.0+ 打包 profile，并包含 ProfileInstaller；当前工程宜使用 AGP 8.2+ 模板与 ProfileInstaller 1.4.1。API 23 只能运行 `Full()`，无法完成这组收益对照。

生成后的 profile 需要随关键用户旅程、R8 映射（压缩后名称与原始名称的对应关系）、启动依赖和大版本调整重新生成。文件存在只说明产物被创建，`Partial(Require)`、`ArtMetric` 与启动/滚动指标才能证明它在当前 APK 和设备上发挥作用。

## 源码核验记录

以下内容对 stable 1.4.1 的已发布 AAR 和 sources 做了交叉核对，并用 1.5.0-rc01 发布物确认预发布线边界：

- `benchmark-common` / `benchmark-junit4` manifest：`minSdkVersion=21`。
- `benchmark-macro` / `benchmark-macro-junit4` manifest：`minSdkVersion=23`。
- `CompilationMode.kt`：API 23 仅 `Full`，API 24+ 才有 `None` / `Partial`，`DEFAULT` 使用 `UseIfAvailable`。
- `Metric.kt`：Frame、Startup、TraceSection、Power、Memory 与 Art 指标的字段和 API 限制。
- `BaselineProfileRule.kt`：非 root API 33+ 或 rooted API 28+，以及 stability 参数。
- `BlackHole.kt`：stable 1.4.1 仍带 `ExperimentalBlackHoleApi`。
- `benchmark-*:1.5.0-rc01` Android AAR manifest：Microbenchmark 与 Macrobenchmark 下限统一为 API 24。
- `benchmark-common:1.5.0-rc01` sources：`BlackHole` 已取消 `ExperimentalBlackHoleApi` 注解。
- AndroidX Benchmark 发布说明：1.4.1 stable、1.5.0-rc01，以及 1.5 预发布线的 UiAutomator 2.4 与进程内 trace 合并能力。

stable 1.4.1 下载件的 SHA-256 如下：

| 文件 | SHA-256 |
|---|---|
| `benchmark-common-1.4.1.aar` | `54fad42120f3c4a9319c9b11ad37733a22a0dca92977ce4bfa33be6e6313c2b9` |
| `benchmark-junit4-1.4.1.aar` | `035c2393aa416b98ed8979d751119518a03da0a00f4a5529eb21a3eeed6b0183` |
| `benchmark-macro-1.4.1.aar` | `d99732de5d713fea47fe7caa3b18438fe615bbb1225e3c6cf0fac48ec350943c` |
| `benchmark-macro-junit4-1.4.1.aar` | `41595999e2dad5a3e61b9ad74c18d73700c21060b7845df05f28a8fbc9a08b15` |
| `benchmark-common-1.4.1-sources.jar` | `55d075a7fede74c60c4ca8a9c9a86cfd067e7e55ee4e33e3f5c7e285a298e930` |
| `benchmark-macro-1.4.1-sources.jar` | `7eee75b0a5982329906d2ae074c5cc05e4d25500a35d580a3401bb97dbfce2c4` |

## 参考资料

- [AndroidX Benchmark release notes](https://developer.android.com/jetpack/androidx/releases/benchmark)
- [Google Maven：Benchmark metadata](https://dl.google.com/android/maven2/androidx/benchmark/benchmark-common/maven-metadata.xml)
- [`benchmark-common:1.5.0-rc01` AAR（预发布边界）](https://dl.google.com/android/maven2/androidx/benchmark/benchmark-common/1.5.0-rc01/benchmark-common-1.5.0-rc01.aar)
- [`benchmark-common:1.5.0-rc01` sources（预发布边界）](https://dl.google.com/android/maven2/androidx/benchmark/benchmark-common/1.5.0-rc01/benchmark-common-1.5.0-rc01-sources.jar)
- [Google Maven：ProfileInstaller metadata](https://dl.google.com/android/maven2/androidx/profileinstaller/profileinstaller/maven-metadata.xml)
- [Microbenchmark overview](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview)
- [Write a Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-write)
- [Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Capture Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Benchmark in CI](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Create Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [Measure Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/measure-baselineprofile)
- [`benchmark-common:1.4.1` AAR](https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-common/1.4.1/benchmark-common-1.4.1.aar)
- [`benchmark-common:1.4.1` sources](https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-common/1.4.1/benchmark-common-1.4.1-sources.jar)
- [`benchmark-macro:1.4.1` AAR](https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro/1.4.1/benchmark-macro-1.4.1.aar)
- [`benchmark-macro:1.4.1` sources](https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro/1.4.1/benchmark-macro-1.4.1-sources.jar)
- [`android17-6.18-2026-06_r6` kernel source](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
