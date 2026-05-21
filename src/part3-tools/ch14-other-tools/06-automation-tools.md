---
title: 自动化测试工具
chapter: '14.6'
repaired_by: openclaw-task2b
repaired_date: "2026-04-26"
last_task2b_at: "2026-05-22T07:21:00+08:00"
task2b_result: fixed
section: '14.6'
status: ready-for-review
drafted_date: '2026-04-04'
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: "2026-04-26"
last_verified_against: "AndroidX docs + AndroidX Benchmark PowerMetric @RequiresApi(Q) + Android test docs + external review"
confidence: medium
sources:
- type: official
  path: developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: developer.android.com/topic/performance/benchmarking/microbenchmark-overview
- type: official
  path: developer.android.com/topic/performance/benchmarking/benchmarking-in-ci
- type: official
  path: developer.android.com/studio/test/other-testing-tools/monkey
- type: blog
  path: github.com/alipay/SoloPi
- type: official
  path: appium.io/docs/en/latest/
tags:
- macrobenchmark
- microbenchmark
- espresso
- uiautomator
- ci/cd
- baseline-profiles
related_chapters:
- '13.1'
- '13.2'
- '14.1'
- '8.3'
- '8.7'
pipeline_stage: task2b_pending
task6_state: revisiting
review_round: 3
task9_state: reviewed
task2b_state: pending
reviewed_by: openclaw-task6
reviewed_date: "2026-04-26"
task6_result: pass-light-edit
task9_result: needs-rework
task9_reviewed_date: "2026-05-22"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-22T07:43:01+08:00"
last_task6_audit: "2026-05-21"
updated_by: openclaw-task2b
updated_date: "2026-04-26"
last_task9_audit: "2026-05-22"
last_task9_review_log: logs/deep-review/2026-05-22-07-deep-review.md
task9_review_notes: "2026-05-22 Task9 07: needs-rework。P0 1：AndroidX Benchmark am instrument 参数裸写 iterations 且包含未验证 androidLogResults，需按 androidx.benchmark.* 参数重写。已写入 logs/deep-review/2026-05-22-07-deep-review.md。"
---

# 自动化测试工具

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Macrobenchmark / Microbenchmark 的使用方法与区别
- 🔹 使用 Macrobenchmark 测量启动时间、滑动帧率
- 🔹 adb shell am instrument 与性能测试集成
- 🔹 UI Automator / Espresso 在性能测试中的角色
- 🔹 性能自动化测试的 CI/CD 集成方案

### 扩展（可选深入）

- 🔸 使用 Firebase Test Lab 进行大规模性能测试
- 🔸 自建性能 Benchmark 平台的实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要用自动化工具做性能测试

我们在前面章节中介绍了 Perfetto、Android Studio Profiler 等手动分析工具——它们帮助我们在发现性能问题后深入定位根因。但手动测试有一个根本性的局限：**无法持续**。你不可能在每次代码提交后都手动跑一遍启动速度测试，也不可能让人盯着每一帧的渲染时间。性能回归往往是在不知不觉中发生的——某次合并引入了一个多余的布局层级，某次依赖升级拖慢了冷启动——等到用户反馈"变卡了"的时候，问题可能已经累积了好几个版本。

自动化性能测试解决的就是这个问题。它让性能指标变成一个**可量化、可追踪、可回归**的工程信号，而不是依赖主观感受。Google 从 2020 年开始陆续推出 Jetpack Benchmark 库（Macrobenchmark 和 Microbenchmark），就是要把性能测试从"高级工程师的直觉"变成"CI 管线里的一行命令"。

在本章中，我们会把自动化性能测试工具分成几个层次来介绍：先从 Google 官方的基准测试库入手，理解 Macrobenchmark 和 Microbenchmark 各自的定位和用法；然后看看 UI Automator 和 Espresso 在性能测试中扮演什么角色；最后讨论如何把这一切接入 CI/CD 管线，实现真正的性能守护。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking]

## Macrobenchmark 与 Microbenchmark：两种层次，两种用途

Google 为 Android 提供了两个互补的基准测试库。它们不是互相替代的关系，而是分别针对不同粒度的性能问题。

### Macrobenchmark：端到端的用户体验测量

Macrobenchmark 的设计目标是测量**用户能感知到的性能**——启动时间、页面滚动流畅度、动画帧率。它不是在代码内部插桩测量某个函数的执行时间，而是从外部操控应用，模拟用户的真实操作，然后测量整个操作流程的耗时。

Macrobenchmark 运行在一个独立的测试模块（`com.android.test`）中，与被测应用完全分离。这种外部测量的方式意味着测试结果反映的是用户实际体验到的性能，而不是某个优化过的代码路径的理想表现。

它的核心 API 是 `MacrobenchmarkRule.measureRepeated()`。这个方法做的事情可以概括为：启动你的应用 → 按照你定义的步骤执行操作（比如点击按钮、滑动列表）→ 收集系统 Trace → 重复 N 次取平均值。每次迭代的 Trace 都会被保存下来，我们可以在 Android Studio 或 Perfetto 中打开分析。

Macrobenchmark 常用指标如下：

| 指标 | 版本边界 | 读法 |
|---|---|---|
| `StartupTimingMetric` | Macrobenchmark 最低 API 23；TTFD 依赖应用调用 `reportFullyDrawn()`，API 30+ 统计更稳定 | TTID 看首帧显示，TTFD 看主要内容加载完成 |
| `FrameTimingMetric` | 基础帧时间可用；`frameOverrunMs` 等 deadline / overrun 指标仅 API 31+ | API 31+ 优先看 overrun，API 30 及以下看帧时间分位数 |
| `TraceSectionMetric` | 随 Macrobenchmark 运行环境；依赖应用里存在同名 Trace Section | 用于度量某段业务路径或初始化阶段 |
| `PowerMetric` | API 29+（AndroidX 源码标注 `@RequiresApi(Build.VERSION_CODES.Q)`）；设备需暴露 power rails / ODPM，实测优先使用 Pixel 6 或更新的受支持机型 | 用于功耗与能耗分类观察；CI 中要对设备白名单、指标缺失和温度状态做显式处理 |

此外，Macrobenchmark 还支持 **CompilationMode** 参数，可以控制应用在测试前的编译状态——是完全 AOT 编译、部分编译（模拟 Baseline Profile 安装后的状态），还是完全未编译。这让我们可以量化 Baseline Profile 带来的启动速度提升。

### Microbenchmark：代码级热点分析

Microbenchmark 关注的是**代码片段的执行效率**。当我们用 Macrobenchmark 或 Profiler 定位到一个性能热点后（比如一个耗时的 JSON 解析方法、一个频繁调用的布局 inflate），就可以用 Microbenchmark 精确测量这段代码在不同实现方案下的性能差异。

Microbenchmark 直接运行在应用进程内部，通过循环执行被测代码来获取稳定的测量结果。它的 API 同样基于 JUnit4 规则：

```kotlin
// 仅展示关键用法
@RunWith(AndroidJUnit4::class)
class MyBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    @Test
    fun measureJsonParsing() = benchmarkRule.measureRepeated {
        // 被测量的代码
        val result = parseJson(largeJsonInput)
    }
}
```

Microbenchmark 会自动处理预热（warmup）——先运行若干次让 JIT 编译生效、缓存预热，然后再开始正式测量。它还会输出内存分配次数（allocations），因为频繁的对象分配往往意味着 GC 压力，这在 Perfetto 中表现为内存抖动（Memory Churn）。

### 什么时候用哪个？

一个简单的判断标准：**如果我们关心的是用户能不能感知到差异，用 Macrobenchmark；如果我们关心的是代码层面的优化效果，用 Microbenchmark。**

典型的协作流程是这样的：先用 Macrobenchmark 发现"启动时间从 800ms 涨到了 1200ms"，然后通过 Trace 分析定位到"JSON 解析占了 400ms"，接着用 Microbenchmark 量化不同 JSON 库的性能差异，最后再用 Macrobenchmark 验证优化后整体启动时间是否回到了 800ms 以下。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-overview 和 microbenchmark-overview]

[适用版本: Macrobenchmark 最低 API 23；Microbenchmark 当前主流稳定版按 API 21+ 规划；`frameOverrunMs` 属 API 31+ 指标；`PowerMetric` 的 API floor 是 29，返回数据取决于设备 power rails / ODPM 能力]

## 使用 Macrobenchmark 测量启动时间和滑动帧率

### 测量启动时间

启动时间是最常见的 Macrobenchmark 场景。下面是一个测量冷启动的完整示例：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartup() = benchmarkRule.measureRepeated(
        packageName = "com.example.myapp",
        metrics = listOf(StartupTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD,
        setupBlock = {
            // 每次测量前按 Home 键，确保应用不在前台
            pressHome()
        }
    ) {
        // 启动默认 Activity 并等待首帧渲染完成
        startActivityAndWait()
    }
}
```

这段代码的逻辑很直白：先按 Home 键回到桌面（确保每次测试的起始状态一致），然后启动应用的默认 Activity，等待它完成首帧渲染。`measureRepeated` 会把这一过程重复 10 次，每次都杀掉进程重新冷启动，最终输出平均的 TTID 和 TTFD。

TTFD 不会自动等到所有异步内容完成。应用必须在首屏主要内容加载完后调用 `Activity.reportFullyDrawn()`；否则结果里只能稳定拿到 TTID，TTFD 会缺失，或只代表首帧之后很短的一段等待。Android 11（API 30）及以上对 fully-drawn 信号的统计更稳定，也会把该信号反馈给系统启动优化和后续 profile 处理。测试脚本要让 `reportFullyDrawn()` 的调用点对应“首页主要内容出现”这一时刻。

`StartupMode` 有三种选择：`COLD`（杀进程重新创建）、`WARM`（只重建 Activity，保留进程）、`HOT`（只恢复 Activity）。三种模式分别对应我们在第 8 章讨论的三种启动类型。在 Perfetto 中，这些 Trace 会被自动捕获，我们可以在 Android Studio 中直接打开查看主线程的 doFrame 时序。

### 测量滑动帧率

滑动流畅度是另一个关键场景。下面的示例测量一个列表的滚动帧率：

```kotlin
@Test
fun scrollList() = benchmarkRule.measureRepeated(
    packageName = "com.example.myapp",
    metrics = listOf(FrameTimingMetric()),
    iterations = 5,
    setupBlock = {
        startActivityAndWait()
        device.wait(Until.hasObject(By.res("recycler_list")), 5000)
    }
) {
    val list = device.findObject(By.res("recycler_list"))
    list?.setGestureMargin(device.displayWidth / 5)
    list?.swipe(Direction.UP, 0.8f)
}
```

`FrameTimingMetric` 会收集每一帧的渲染时间。Macrobenchmark 会统计帧时间分布——P50、P90、P95 和 P99 分位数。P50 代表典型帧的渲染时间，P95/P99 用来观察尾部掉帧。API 31+ 还会输出 `frameOverrunMs`，它按每帧完成时间与系统 deadline 的差值判断是否越界，比固定套 16.67ms 或 8.33ms 更适合高刷新率、可变刷新率设备。API 30 及以下主要看帧时间分布和 Trace 中的 `Choreographer#doFrame`。

这里的滑动操作使用了 `UiObject2.swipe()`，这是 UI Automator 的 API。`swipe(Direction.UP, 0.8f)` 表示向上滑动屏幕 80% 的距离，适合模拟列表滚动。`UiObject2` 也提供 `drag(Point dest)` 方法——起点固定取 `getVisibleCenter()`，传入目标点即可——但列表滚动场景用 `swipe()` 更简洁。Macrobenchmark 在底层依赖 UI Automator 来驱动 UI 操作——后面会详细讨论。

### CompilationMode：量化编译优化效果

在测量启动时间时，CompilationMode 是一个关键参数。它控制测试前应用的编译状态，让我们能够对比不同编译优化级别的效果：

```kotlin
// 测量无 Baseline Profile 时的启动速度（仅 JIT）
CompilationMode.None()

// 测量安装 Baseline Profile 后的启动速度
CompilationMode.Partial()

// 如果测试必须要求 Baseline Profile 存在，可以显式指定
CompilationMode.Partial(
    baselineProfileMode = BaselineProfileMode.Require
)

// 完全 AOT 编译
CompilationMode.Full()
```

使用 `BaselineProfileMode.Require` 的文件要导入 `androidx.benchmark.macro.BaselineProfileMode`；只采用默认策略时，`CompilationMode.Partial()` 更不容易受旧 API 签名影响。

Baseline Profile 不是运行时开关。构建产物会携带启动路径和热点方法规则，安装或后台 dexopt 时，系统把这些规则合并到 ART profile，再由 `dex2oat` 按 `speed-profile` 口径把命中的类和方法编译进 `.odex` / `.oat` / `.vdex` 产物。`CompilationMode.Partial()` 用来模拟这条安装后编译路径，只编译 profile 覆盖的热路径；`CompilationMode.Full()` 更接近全量 AOT。

Google 官方的数据显示，Baseline Profile 可以将冷启动时间改善约 30%。通过对比 `CompilationMode.None()` 和 `CompilationMode.Partial()` 的测试结果，我们可以量化自己应用的 Baseline Profile 收益。保留量化数字时，要同时写清设备型号、系统版本、启动模式、迭代次数和 profile 安装方式。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics；Android Runtime profile-guided compilation 机制]

[待补充: Perfetto Trace 截图——Macrobenchmark 输出的 startup 和 frame timing Trace 在 Android Studio 中的具体表现]

## adb shell am instrument：性能测试的命令行入口

在深入了解 CI/CD 集成之前，我们需要理解一个基础但重要的命令行工具：`adb shell am instrument`。无论用的是 Macrobenchmark、Espresso 还是 UI Automator，最终都是通过这个命令在设备上执行测试的。

`am instrument` 是 Android 的 Activity Manager 提供的测试运行器接口。基本语法：

```bash
adb shell am instrument -w <test_package>/<runner_class>
```

对于 Macrobenchmark，实际执行的命令类似于：

```bash
adb shell am instrument -w \
  -e class com.example.macrobenchmark.StartupBenchmark#coldStartup \
  com.example.macrobenchmark/androidx.test.runner.AndroidJUnitRunner
```

`-w` 参数表示等待测试完成并输出结果。`-e class` 指定要运行的测试类和方法。在 Gradle 中，我们通常通过 `connectedCheck` 任务间接调用：

```bash
./gradlew :macrobenchmark:connectedBenchmarkAndroidTest \
  -P android.testInstrumentationRunnerArguments.class=\
com.example.macrobenchmark.StartupBenchmark#coldStartup
```

这个命令行接口在 CI/CD 管线中非常重要——我们不需要打开 Android Studio，直接在终端就能运行基准测试并获取结果。Macrobenchmark 的输出包括控制台的摘要信息和一个 JSON 文件（包含每次迭代的详细指标），以及每轮迭代的 Perfetto Trace 文件。

几个有用的 `am instrument` 参数：

- `-e iterations N`：覆盖测试的迭代次数
- `-e androidx.benchmark.suppressErrors ACTIVITY-MISSING`：抑制某些配置错误（调试用）
- `-e androidLogResults true`：在 logcat 中输出详细结果

[已验证: 官方文档, developer.android.com/training/testing/instrumented-tests]

## UI Automator 与 Espresso：在性能测试中的角色

UI Automator 和 Espresso 都是 Android 的 UI 测试框架，但它们在性能测试中扮演的角色截然不同。理解这个区别是正确使用 Macrobenchmark 的前提。

### UI Automator：Macrobenchmark 的底层驱动

UI Automator 是一个**黑盒测试框架**——它通过 Android 的无障碍服务（Accessibility Service）与 UI 交互，不需要知道应用的内部实现。它运行在独立进程中，可以跨应用操作（比如先打开设置修改配置，再回到被测应用）。

Macrobenchmark 在底层直接使用 UI Automator 的 API 来驱动应用。当我们调用 `startActivityAndWait()`、`pressHome()` 或 `device.findObject(By.res("..."))` 时，底层调用的都是 UI Automator 的 `UiDevice` 接口。Macrobenchmark 测试因此具备黑盒特性：它测量的是用户真实感知到的性能，而不是开发者注入的探针。

UI Automator 在性能测试中的优势是它不干扰被测应用：因为它运行在独立进程中，不会占用被测应用的 CPU 时间片或内存空间。但它也有代价——通过无障碍服务交互有 IPC 开销，操作速度比 Espresso 慢。不过对于性能测试来说，这个"慢"反而是优势——它更接近真实用户的操作节奏。

### Espresso：白盒验证，不是性能测量工具

Espresso 是一个**白盒测试框架**，运行在被测应用的同一个进程中。它的设计重点是“自动同步”：当测试执行 `onView(...).perform(click())` 时，Espresso 会等待 UI 线程空闲、`IdlingResource` 归零以及已注册异步任务完成后再执行下一步。这让功能测试更稳定。

这套同步机制不适合直接做性能测量。它和应用在同一个进程中，测试代码本身会影响被测量的 CPU、内存和调度数据；`IdlingResource` 等等待机制还会改变用户输入到 UI 响应之间的时间关系，掩盖主线程竞争、后台任务排队和首帧等待。

Espresso 在性能测试中的主要价值是**验证**：可以用 Espresso 快速确认某个性能优化是否改变了功能行为。比如优化了布局层级后，想确认 UI 仍然正确渲染，这时候用 Espresso 写一个快速的功能回归测试是合适的。

### 不能混用的地方

一个常见的误区是尝试在 Macrobenchmark 中使用 Espresso。这行不通，因为 Macrobenchmark 测试运行在独立进程中，而 Espresso 必须和应用在同一个进程。如果在 Macrobenchmark 的 `measureBlock` 中尝试调用 Espresso API，会直接抛出异常。

如果测试需要跨应用操作（比如授权弹窗），正确的做法是在 Macrobenchmark 的 `setupBlock` 中使用 UI Automator 处理系统弹窗，然后在 `measureBlock` 中继续用 UI Automator 驱动被测应用。

[已验证: 官方文档, developer.android.com/training/testing/ui-automator 和 developer.android.com/training/testing/ui-testing/espresso]

## Monkey、SoloPi 与 Appium：自动化工具的另一类用途

基准测试负责回答“这次改动是否让指标变差”。稳定性和专项测试工具负责覆盖长时间运行、随机输入、跨端脚本这些场景。

### Monkey：低成本压力测试

`Monkey` 通过随机事件持续触发点击、滑动、按键和 Activity 切换，适合在夜间构建或专项回归中暴露 ANR、崩溃、OOM 和资源泄漏。它不提供可信的性能指标，价值在于制造足够多的状态组合，然后把异常现场交给 logcat、bugreport、Perfetto 或 LeakCanary 复核。

这条命令把随机事件限制在单个包内，并通过 `--throttle` 控制事件间隔：

```bash
adb shell monkey -p com.example.app \
  --pct-touch 60 --pct-motion 20 \
  --throttle 200 -v 10000
```

读结果时看三类证据：崩溃 / ANR 日志、测试前后 RSS / Java heap 变化、是否能导出 Hprof 或 tombstone。Monkey 本身不适合做启动耗时、滑动帧率这类精确度量。

### SoloPi：专项性能脚本和视觉拆帧

`SoloPi` 偏向线下专项测试。它可以录制操作脚本、采集 FPS / CPU / 内存等指标，并通过录屏帧变化估计页面加载完成时间。这个结果更贴近测试同学观察到的“页面是否已经可用”，但它依赖录屏、无障碍和设备状态，复现性低于 Macrobenchmark。适合做竞品对比、快速走查和人工测试补充。

### Appium：跨端自动化，不负责指标可信度

`Appium` 的优势是脚本生态和跨平台能力。用它可以覆盖长流程业务场景，但驱动层经过 WebDriver、无障碍和多次 IPC，输入延迟和同步等待会影响耗时。性能测试中，Appium 适合做场景编排；指标采集仍应交给 Macrobenchmark、Perfetto、dumpsys 或设备侧专项工具。

[已验证: Android Monkey 文档、SoloPi GitHub、Appium 文档]

## 性能自动化测试的 CI/CD 集成方案

把基准测试集成到 CI/CD 管线中，是性能工程从"偶尔测测"到"持续守护"的关键一步。

### 基本架构

一个完整的 CI/CD 性能测试管线通常包含四个环节：

**构建阶段**：编译应用的 benchmark 变体和基准测试 APK。Macrobenchmark 要求应用使用接近 release 的构建配置——开启混淆、关闭调试标志。通常的做法是创建一个 `benchmark` 构建类型，继承自 release 但使用调试签名：

```kotlin
// app/build.gradle.kts
buildTypes {
    create("benchmark") {
        initWith(getByName("release"))
        signingConfig = signingConfigs.getByName("debug")
        matchingFallbacks += listOf("release")
    }
}
```

**执行阶段**：在真实设备上运行基准测试。不要在模拟器上运行基准测试，模拟器的 CPU 调度、内存带宽、GPU 渲染路径都和真实设备完全不同，测出来的数据没有参考价值。

CI 里要把设备状态当成测试输入固定下来：同一型号和系统版本、充电状态一致、测试前冷却到稳定温度、关闭省电模式和后台同步，并记录电量与温度。AndroidX Benchmark 会检测 thermal throttling，触发后应让本轮结果失败或延后重跑。如果启用 `PowerMetric`，设备池要做白名单：API 29+ 只是入口条件，设备还要暴露 power rails / ODPM；Pixel 6+ 这类支持 power rail 计量的机型更适合作为固定测试池。拿不到 energy / power 字段时，本轮功耗指标应标为缺失，不能用 0 或空值参加对比。`androidx.benchmark.enabledRules` 只负责区分 `Macrobenchmark` 与 `BaselineProfile` 这类任务，不负责锁频；只有 rooted 设备上的 Microbenchmark 才适合用 `lockClocks` 降低频率波动。

对于没有自建设备农场的小团队，Firebase Test Lab（FTL）是一个实用的选择。FTL 提供了大量真实 Android 设备，通过 gcloud 命令行提交测试：

```bash
gcloud firebase test android run \
  --type instrumentation \
  --app app/build/outputs/apk/benchmark/app-benchmark.apk \
  --test macrobenchmark/build/outputs/apk/benchmark/macrobenchmark-benchmark.apk \
  --device model=redfin,version=30 \
  --results-bucket=gs://my-benchmark-results \
  --results-dir=run-$(date +%Y%m%d-%H%M%S)
```

**结果收集阶段**：Macrobenchmark 会输出两种结果——JSON 指标文件和 Perfetto Trace 文件。JSON 文件包含了每次迭代的量化指标（TTID、TTFD、帧时间等），Trace 文件则可以用于深入分析。

**回归检测阶段**：将本次测试的指标与历史基线对比。如果关键指标（如冷启动时间）超出阈值，就标记构建为失败。这需要自己写一个简单的比较脚本，或者使用开源工具。

### GitHub Actions 集成示例

以下是一个简化的 GitHub Actions workflow，展示如何将 Macrobenchmark 集成到 CI 中：

```yaml
name: Performance Benchmark
on:
  pull_request:
    branches: [ main ]
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
        run: |
          ./gradlew :app:assembleBenchmark
          ./gradlew :macrobenchmark:assembleBenchmark

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Run Benchmarks on FTL
        run: |
          gcloud firebase test android run \
            --type instrumentation \
            --app app/build/outputs/apk/benchmark/app-benchmark.apk \
            --test macrobenchmark/build/outputs/apk/benchmark/macrobenchmark-benchmark.apk \
            --device model=redfin,version=30 \
            --results-bucket=gs://${{ secrets.BENCHMARK_BUCKET }}

      - name: Download and Compare Results
        run: |
          gsutil cp gs://${{ secrets.BENCHMARK_BUCKET }}/latest/*.json ./results/
          python3 scripts/compare_benchmarks.py \
            --baseline ./baseline/benchmark_baseline.json \
            --current ./results/benchmark_result.json \
            --threshold 10
```

这个 workflow 在每个 PR 时自动运行基准测试，如果关键指标回归超过 10% 就会失败。这样开发者在合入代码之前就能知道自己的修改是否引入了性能问题。

### 结果持久化与趋势追踪

单次基准测试的绝对数值意义有限——设备温度、后台进程、电池状态等因素都会引入噪声。真正有价值的是**趋势**——性能指标随代码变更的变化曲线。

常见的做法是：将每次 CI 运行的 JSON 结果写入时序数据库（如 InfluxDB 或 BigQuery），用 Grafana 或 Data Studio 建立可视化看板，设置告警——当连续 3 次运行的 P95 启动时间超过基线 15% 时自动通知。

对于开源项目，GitHub Actions 的 `benchmark-action/github-action-benchmark` 可以直接在 PR 中评论性能对比结果，非常方便。

[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]

[待验证: Firebase Test Lab 的最新计费模型和设备可用性]

## 在 Perfetto 中的表现

Macrobenchmark 的每次迭代都会自动捕获一份 Perfetto Trace。这些 Trace 文件默认保存在设备上，运行完成后被自动拷贝到主机的构建输出目录：

```
project_root/macrobenchmark/build/outputs/
connected_android_test_additional_output/
```

在 Perfetto（ui.perfetto.dev）中打开这些 Trace，就能看到完整的启动或滑动过程。对于启动基准测试，关注的主线程 Track 通常会显示：

- `Choreographer#doFrame` 的执行时间——反映首帧渲染耗时
- `ActivityThread.handleBindApplication` 到 `Activity.onCreate` 的间隔——反映 Application 初始化耗时
- `RenderThread` 的 `DrawFrame` 以及 GPU completion / `queueBuffer` 附近片段——反映渲染命令提交和等待完成的时间

对于帧率基准测试，Perfetto 会显示每一帧的 doFrame 调用及其耗时。掉帧的帧在 Trace 中表现为超过 VSync 间隔的 doFrame，在 Perfetto 的帧时间线视图中会以红色或橙色标记。

[图：Macrobenchmark 输出的 Perfetto Trace 在 Android Studio CPU Profiler 中的展示——显示冷启动各阶段的时间分布]

[图：FrameTimingMetric 在 Perfetto 中的帧时间分布——正常帧（绿色）vs 掉帧帧（红色）]

## 常见问题与误区

**"基准测试可以在模拟器上运行"**——这是最常见的错误。模拟器的 CPU 特性、GPU 渲染路径、内存架构与真机完全不同。在模拟器上测出的启动时间可能比真机快 2 倍也可能慢 3 倍，完全不可靠。Macrobenchmark 库在检测到模拟器环境时会主动报错。

**"Microbenchmark 比 Macrobenchmark 更精确所以更好"**——这是混淆了精度和价值。Microbenchmark 测量的是代码片段的理想执行时间，但用户感知不到一个函数快了 2 微秒。Macrobenchmark 虽然单次测量噪声更大，但它测量的是真正的端到端用户体验，这才是性能优化的终极目标。

**"把基准测试放在应用模块里就行"**——Macrobenchmark 必须放在独立的 `com.android.test` 模块中。因为它需要从外部控制应用的启动和停止，如果和应用在同一个模块，就无法保证测试环境的独立性。Microbenchmark 则可以放在 library 模块中。

**"基准测试结果应该完全稳定"**——即使控制了编译模式、设备温度、后台进程等变量，基准测试仍然会有 5-15% 的波动。这是正常的——ARM 处理器的动态调频、thermal throttling、内核调度决策都引入不确定性。解决方案是通过多次迭代（至少 10 次）取中位数，加上长期趋势追踪来过滤噪声，而不是追求单次数值的精确。

**"Espresso 可以用于 Macrobenchmark"**——如前所述，Macrobenchmark 测试运行在独立进程中，而 Espresso 必须和应用在同一个进程。两者在架构上不兼容。

## 参考资料

- [Macrobenchmark 官方文档](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) [已验证: 官方文档]
- [Microbenchmark 官方文档](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) [已验证: 官方文档]
- [CI/CD 中的基准测试](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci) [已验证: 官方文档]
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics) [已验证: 官方文档]
- [Baseline Profiles 指南](https://developer.android.com/topic/performance/baselineprofiles/overview) [已验证: 官方文档]
- [UI Automator 文档](https://developer.android.com/training/testing/ui-automator) [已验证: 官方文档]
- [Espresso 文档](https://developer.android.com/training/testing/ui-testing/espresso) [已验证: 官方文档]
- [Firebase Test Lab 文档](https://firebase.google.com/docs/test-lab) [已验证: 官方文档]
- [GitHub 官方示例: performance-samples](https://github.com/android/performance-samples) [已验证: 官方文档]
