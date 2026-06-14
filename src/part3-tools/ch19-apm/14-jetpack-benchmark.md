---
title: Jetpack Benchmark（Microbenchmark + Macrobenchmark）
chapter: '19'
section: '19.14'
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Microbenchmark：Android 4.0+（API 14+）；Macrobenchmark：Android 6.0+（API 23+）；Baseline Profile 生成需 API 33+ 或 rooted API 28+；Baseline Profile 验证需 API 24+；书中样例以 Android 8-17 为主
last_verified: '2026-04-27'
last_verified_against: AndroidX BlackHole / BenchmarkState / BaselineProfileRule / CompilationMode source and Android Developers Benchmark docs
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
last_task2b_at: '2026-04-27T06:57:48+08:00'
repaired_date: '2026-04-27'
repaired_by: openclaw-task2b
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-05-24"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-24T01:38:24+08:00"
last_task9_audit: "2026-06-15"
last_task9_audit_at: "2026-06-15T05:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-15-05-audit.md"
last_task9_review_log: "logs/deep-review/2026-05-24-01-deep-review.md"
task9_review_notes: "2026-05-24 Task9 deep review: pass-tech-review。P0 0 / P1 0 / P2 0；Baseline Profile API floor / CompilationMode / BlackHole 已复核；自动晋升 finalized；详见 logs/deep-review/2026-05-24-01-deep-review.md。"
status: "finalized"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: "fixed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-24"
task6_result: "pass-light-edit"
last_task6_at: "2026-05-24T01:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-24-01-review.md"
task6_review_notes: "2026-05-24 Task6 revisiting review: pass-light-edit。L1/L2 小修 1 处（清理 frontmatter duplicate task2b_result）。无新增 Task6 回炉；Baseline Profile API floor 已由 Task2B 修复，等待 Task9 复审。"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-26
last_task9_audit_result: "pass-source-version-audit"
---
# Jetpack Benchmark（Microbenchmark + Macrobenchmark）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 Jetpack Benchmark 用来证明代码改动效果，承担可重复实验，不承担线上监控。
- 🔹 [Microbenchmark] 展开适合测试的对象、JIT / warmup、measurement、BlackHole、state、避免测到日志或随机数。
- 🔹 [Macrobenchmark] 展开端到端场景、启动、滚动、页面切换、UiAutomator、CompilationMode、StartupMode。
- 🔹 [工程结构] 写 benchmark module、target app、instrumentation runner、Gradle 插件、依赖和构建变体。
- 🔹 [最小示例] 提供 cold startup 和列表滑动两个 Macrobenchmark 示例，标注关键行。
- 🔹 [指标解释] 说明 StartupTimingMetric、FrameTimingMetric、TraceSectionMetric、PowerMetric 等指标如何阅读。
- 🔹 [测试条件] 写设备温度、电量、后台进程、网络、数据准备、编译模式、系统动画、重复次数。
- 🔹 [CI 噪声] 给基线设备、阈值、历史趋势、重跑规则、失败判定和报告保存方式。
- 🔹 [线上关系] 说明线上 APM 发现问题后如何转成 Benchmark 场景；Benchmark 结果如何反证修复。
- 🔹 [Baseline Profiles] 写 Macrobenchmark 生成 / 验证 Baseline Profiles 的位置和注意事项。

### 扩展（可选深入）

- 🔸 增加 benchmark module 目录结构和 Gradle 配置示例。
- 🔸 补一个 Microbenchmark 错误写法案例，说明为什么测错对象。
- 🔸 补一份 CI 报告字段模板，包含设备、版本、metric、median、p95、variance。
- 🔸 对 Android Developers Benchmark 文档、Gradle 插件版本和 API 状态做核对。
- 🔸 增加与 Perfetto trace、JankStats、FrameMetrics 的结果互证方式。

### 流水线加工要求

- 每个 benchmark 示例都要写清被测对象、准备数据、循环方式、指标和失败条件。
- 任何性能结论都必须绑定测试条件。
- 不要把线上 P95 和实验室 median 混为同一种证据。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## Benchmark 用来证明改动效果

Jetpack Benchmark 不是线上 APM。它是本地、实验室和 CI 中用来稳定测量性能差异的工具。APM 告诉你线上哪个版本变差，Benchmark 用来验证某个修复是否真的让启动、滑动或函数耗时变好。

Android 官方把 Benchmark 分成 Microbenchmark 和 Macrobenchmark。名字相近，但测的对象完全不同。

## 版本兼容表

官方 Benchmark 对比页给出了库级 API floor：Macrobenchmark 支持 API 23 及以上，Microbenchmark 支持 API 14 及以上。书里讨论 Android 8-17，是因为当前项目的发布设备段主要落在这一段，不是因为库从 API 26 才能使用。

| 能力 | 官方 API floor | 书中主验证设备段 | 边界 |
|---|---|---|---|
| Microbenchmark | API 14+ | Android 8-17 | 适合进程内热点代码；结果更接近局部 CPU / 内存分配，不代表页面端到端体验 |
| Macrobenchmark | API 23+ | Android 8-17 | 适合启动、滚动、转场；依赖外部测试进程驱动 App |
| Baseline Profile 安装收益 | 目标设备 API 24+（API 24-27 依赖 ProfileInstaller；API 28+ 支持安装期/云端 profile） | Android 8-17 | API 24-27 通过 `ProfileInstaller` 在 App 首次启动后安装 profile；API 28+ ART 支持安装期编译，可利用 Baseline Profile 和云端 profile。API 21-23 不能获得 Baseline Profile AOT 收益 |
| Baseline Profile 生成（BaselineProfileRule） | API 33+，或 rooted API 28+ | Android 8-17 | `BaselineProfileRule.collect()` 生成环境需要 API 33+ 或 rooted 设备；生成结果与具体设备/版本绑定，需在目标发布设备段验证 |
| Baseline Profile 验证（CompilationMode） | API 24+（`Partial(BaselineProfileMode.Require)`） | Android 8-17 | 验证需被测 APK 包含 ProfileInstaller 且由 AGP 7.0+ 打包 profile；API 23 只有 `Full()` 编译模式 |

决定能不能测的，除了 API floor，还包括 metric 是否被当前设备支持、被测 App 是否使用接近 Release 的 build variant，以及 profileable / instrumentation 配置是否齐全。

## Microbenchmark 测小代码段

Microbenchmark 在进程内循环执行一段可直接调用的代码，适合测算法、序列化、正则、数据结构、图片处理等局部 CPU 工作。

旧版经验常把 Microbenchmark 理解成热身后的 JIT 和缓存命中口径。这个判断只适用于没有额外 AOT 预编译的配置。Android Developers 现在明确写明：Benchmark 1.3.0-beta01+ 配合 AGP 8.4.0+ 时，`androidx.benchmark` plugin 会默认把 microbenchmark APK 做全量编译，口径更接近稳定的 AOT 结果；如果要回到旧的预热后的 JIT 口径，需要在 `gradle.properties` 里设置 `androidx.benchmark.forceaotcompilation=false`。

| Microbenchmark 运行形态 | 典型版本 | 结果口径 |
|---|---|---|
| 旧配置或手动关闭 AOT | Benchmark < 1.3.0-beta01，或 AGP < 8.4，或显式设置 `androidx.benchmark.forceaotcompilation=false` | 更接近热身后的 JIT 与缓存命中结果 |
| 新版默认配置 | Benchmark 1.3.0-beta01+ 且 AGP 8.4.0+ | 默认 full AOT，波动更小，适合做稳定回归 |

读数据时要先写清编译模式。两条 benchmark 曲线如果编译模式不同，不能放在一张图里直接横比。

Microbenchmark 还要防止 Dead Code Elimination。Kotlin 编译器和 R8 可能移除“计算了但结果没被使用”的代码，尤其是纯函数、解析器、编码器这类返回值路径。AndroidX 提供的类名是 `androidx.benchmark.BlackHole`，用法是把被测结果传给 `BlackHole.consume(result)`，让编译器保留这段计算。

适合 Microbenchmark 的问题：

- 一个 JSON 解析器是否比另一个快。
- 某个 diff 算法在 1000 条数据下耗时多少。
- 图片缩放函数改写后是否更快。
- 缓存命中路径是否有额外分配。

不适合的问题：

- 冷启动真实耗时。
- 页面滑动是否流畅。
- Binder、I/O、系统调度参与的端到端场景。

## Macrobenchmark 测端到端交互

Macrobenchmark 在应用进程外启动和控制 App，适合测冷启动、热启动、列表滚动、页面跳转、复杂 UI 操作等端到端路径。它可以输出启动耗时、帧指标，并生成 trace 供分析。

| 维度 | Microbenchmark | Macrobenchmark |
|---|---|---|
| 测量对象 | 可直接调用的小代码段 | App 入口和用户交互 |
| 运行位置 | App 进程内 | 测试进程控制被测 App |
| 适合指标 | CPU 时间、分配、局部方法耗时 | 启动、帧、滚动、页面切换 |
| 典型耗时 | 较快 | 较慢，常超过 1 分钟 |
| trace | 可选 profiling | 结果通常带 trace |

两者不能互相替代。启动慢不能靠 Microbenchmark 证明，算法优化也不该用 Macrobenchmark 绕一大圈测。

## 最小 Macrobenchmark 示例

下面这段代码展示冷启动 benchmark 的基本结构，重点看 `measureRepeated()` 包住的启动流程，以及显式写出的 `compilationMode`。

```kotlin
import androidx.benchmark.macro.CompilationMode
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.StartupTimingMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartup() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.DEFAULT,
        startupMode = StartupMode.COLD,
        iterations = 10
    ) {
        pressHome()
        startActivityAndWait()
    }
}
```

`compilationMode` 要显式写出。Benchmark 结果经常因为这一项不同而失去可比性。默认值虽然存在，文稿和团队基线都不该省略它。

## CompilationMode 的口径表

Android Developers 和 AndroidX `CompilationMode` 源码把默认行为分成两段：

| 模式 | API 24+ | API 23 | 适合场景 |
|---|---|---|---|
| `CompilationMode.DEFAULT` | 等同 `Partial(BaselineProfileMode.UseIfAvailable)`；有 Baseline Profile 时优先安装 | 系统默认就是 full compile | 接近 fresh install 的默认体验 |
| `CompilationMode.None()` | 不做 AOT 预编译，允许运行期 JIT | 这一档不可用，API 23 只有 full compile | 看无 Baseline Profile 时的最差启动或交互口径 |
| `CompilationMode.Partial()` | 走 Baseline Profile 或 warmup 的部分预编译 | 这一档不可用，API 23 只有 full compile | 看接近真实用户设备的常态表现 |
| `CompilationMode.Full()` | 全量 AOT，结果更稳，但不代表现代用户设备的常态 | 系统默认行为 | 做上限对照，或减少编译噪声 |
| `CompilationMode.Ignore()` | 跳过库内编译步骤，保留外部已经准备好的编译状态 | 只能保留系统默认 full compile | 编译状态由外部脚本控制时使用 |

如果目标是验证 Baseline Profile 是否生效，`CompilationMode.DEFAULT` 还不够直接，优先显式写 `CompilationMode.Partial(BaselineProfileMode.Require)`。这个模式要求被测 APK 由 AGP 7.0+ 打包 baseline profile，并包含 `androidx.profileinstaller:profileinstaller`。如果目标是看最差冷启动，才改成 `None()`。如果目标是消掉 JIT 噪声做上限对照，再用 `Full()`。

这个测试只适合放在 benchmark module 或独立测试配置里。CI 上还要固定设备、系统版本、充电状态、温度和后台进程，否则数据波动会吞掉优化效果。

## 测试条件优先于代码

Benchmark 最常见的失败点是测试条件不稳定。要让结果能被团队信任，至少控制这些变量：

- 设备型号和系统版本固定。
- 关闭省电模式，保持充电和温度稳定。
- 每次测试前清理或固定数据集。
- 区分 debug、profile、release 构建。
- 保留 trace 和原始结果，避免只看单个数字。

冷启动测试还要区分首次安装、清数据后启动、普通冷启动、预编译状态。Baseline Profiles 生效前后，启动结果会明显不同。

## 它解决不了哪些问题

Benchmark 适合回答“这次改动在固定条件下是否更快”。不适合直接解决这些场景：

- 只在少数线上机型、地区、账号或真实流量下出现的问题；这类问题先靠 APM、日志或灰度数据缩小范围。
- 依赖服务端抖动、弱网、推送时序、真实账号数据的路径；实验室脚本很难稳定复现。
- ANR、native crash、系统服务争用、Binder 跨进程阻塞这类现场；它们更适合 Perfetto、ANR 样本、Crash 堆栈。
- 需要秒级看板或长期线上趋势的问题；Benchmark 只产出实验结果，不产出持续监控面板。

所以 Benchmark 更像“实验室回归工具”。线上先发现异常，再把异常压缩成可重复脚本，再用 Benchmark 验证修复。

## 和线上 APM 的连接方式

线上 APM 发现某个页面 P95 慢帧率升高后，可以用 Macrobenchmark 写一条可重复滑动场景；修复后在 CI 里持续跑。这样线上问题会变成可回归测试。

Microbenchmark 则适合把局部优化变成护栏。比如一个图片解码缓存优化，修完后写 benchmark 防止后续改动又把耗时拉回去。

Benchmark 的作用是把“线上变差”转化成“本地可重复、CI 可防守”的性能测试。

## Benchmark module 的工程形态

书稿级项目里，Benchmark 不应该散落在普通 instrumentation test 中。推荐单独建立：

- `:benchmark`：Macrobenchmark module，控制被测 App。
- `:microbenchmark`：Microbenchmark module，测试可直接调用的热点代码。
- `:app`：被测应用，提供 `benchmark` build type 或 `profile` build variant。

Macrobenchmark 通常要求被测包接近 Release 配置。Debug 包有调试开销、无优化、日志更多，测出来的数据不适合做发布判断。被测 build variant 还要满足 benchmark runner 和 profileable 等前置条件，否则脚本连目标进程都不稳定。

如果要验证 Baseline Profile 或使用 `CompilationMode.Partial(BaselineProfileMode.Require)`，被测 App 侧还要加入 ProfileInstaller 依赖，并确认使用 AGP 7.0+ 打包 baseline profile：

```kotlin
// :app/build.gradle.kts
dependencies {
    implementation("androidx.profileinstaller:profileinstaller:<latest>")
}
```

这条依赖属于 target app，不能放错到 benchmark module。缺少它时，Macrobenchmark 可能无法把 profile 写入目标应用并触发对应编译，`Partial(Require)` 也会失去验证价值。

## Microbenchmark 写法要避免测错对象

Microbenchmark 容易写成“测了测试代码”。比如在 benchmark 循环里构造大量输入数据，会把数据构造成本算进去。

推荐结构：

```kotlin
import androidx.benchmark.BlackHole

@RunWith(AndroidJUnit4::class)
class JsonParserBenchmark {
    private lateinit var payload: String
    private lateinit var parser: FeedParser

    @Before
    fun setUp() {
        payload = loadFixture("feed_100_items.json")
        parser = FeedParser()
    }

    @Test
    fun parseFeed() = benchmarkRule.measureRepeated {
        val result = parser.parse(payload)
        BlackHole.consume(result)
    }
}
```

`setUp()` 准备稳定输入，`measureRepeated` 里只放被测代码；`BlackHole.consume(result)` 防止返回值未使用时被 DCE 移除。Java 或手动循环写法可以使用 `BenchmarkRule.getState()` 拿到 `BenchmarkState`，再用 `while (state.keepRunning()) { ... }` 控制测量循环。

## Macrobenchmark 场景要有业务脚本

Macrobenchmark 的价值来自稳定复现用户路径。启动测试最简单，滚动、搜索、详情页、支付这类路径需要明确脚本。

示例：

```kotlin
@Test
fun homeFeedScroll() = benchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(FrameTimingMetric()),
    iterations = 8,
    startupMode = StartupMode.WARM
) {
    startActivityAndWait()
    device.findObject(By.res("feed_list")).fling(Direction.DOWN)
    device.waitForIdle()
}
```

真实项目要给关键控件稳定 resource id。没有稳定 id，测试脚本容易因为 UI 改动失效。

多进程 App 还要确认被测 UI、渲染 surface 和主要 CPU 工作是否在 `targetPackage` 的主进程内。如果页面主要跑在 `:remote` 或其他进程，`FrameTimingMetric` 可能只反映被匹配到的窗口帧，无法解释远端进程里的 CPU、Binder 或 I/O 耗时。处理这类场景时，把 Macrobenchmark 结果和 Perfetto 进程轨道、`TraceSectionMetric` 或应用内 trace 名称一起核对。

## 指标解释

Benchmark 输出的数字要和业务目标对应：

| 指标 | 适合判断 | 误用 |
|---|---|---|
| `StartupTimingMetric` | 冷/温/热启动耗时 | 用它解释首屏数据完成时间 |
| `FrameTimingMetric` | 滚动、转场、动画的帧表现 | 用平均值掩盖 P95 / P99 问题 |
| `TraceSectionMetric` | 自定义 trace 区间耗时 | trace 名称不稳定导致结果断档 |
| Allocation metrics | 局部代码分配压力 | 直接推断 OOM |

启动耗时还要区分 TTID 和 TTFD。系统看到首帧不等于用户可交互。如果业务关心内容可用，需要在 App 中正确调用 `reportFullyDrawn()` 或自定义 trace。像 `PowerMetric` 这类指标还依赖设备、电池状态和系统支持，开始前先确认 metric 本身的前置条件。

## CI 中的噪声控制

CI 跑性能测试比功能测试更脆弱。建议：

- 使用固定物理设备池，不用普通共享模拟器做最终性能门禁。
- 测试前清理后台任务，固定亮度、刷新率、性能模式。
- 保持散热条件稳定。Benchmark 库检测到 thermal throttling 时会丢弃受影响数据并等待设备降温；CI 仍要避免设备长期过热导致整轮测试被拉长。
- 不要为了跑通流水线滥用 `androidx.benchmark.suppressErrors`。被压成 warning 的低电量、debuggable、模拟器等错误都会降低结果可信度，只适合 smoke test，不适合做回归门禁。
- 每个场景至少多次 iteration，看中位数和 P95。
- 保存 trace 文件，失败时能回放分析。
- 阈值用相对回归，例如比 main 分支慢 8% 才报警。

绝对阈值适合发布标准，相对阈值适合 PR 回归。两者不要混在一起。

## 和 Baseline Profiles 的配合

Baseline Profiles 的生成和验证离不开 Macrobenchmark，但两类测试的 Rule 不同：

- `BaselineProfileRule.collect()`：执行关键路径，生成 baseline profile 规则。
- `MacrobenchmarkRule.measureRepeated()`：在 `CompilationMode.Partial(BaselineProfileMode.Require)`、`None()`、`Full()` 等模式下验证启动或滚动收益。
- `startupBenchmark` / `scrollBenchmark`：复用同一批用户路径，把 profile 收集结果转成可比较的性能数据。

生成 profile 的最小骨架如下，代码里只看 `BaselineProfileRule` 和 `collect()`：

```kotlin
import androidx.benchmark.macro.junit4.BaselineProfileRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val baselineProfileRule = BaselineProfileRule()

    @Test
    fun generate() = baselineProfileRule.collect(
        packageName = "com.example.app"
    ) {
        pressHome()
        startActivityAndWait()
        device.waitForIdle()
    }
}
```

每次改启动路径、首页依赖或大 SDK 初始化，都要重新跑 profile 生成和 benchmark。否则 profile 可能还存在，但已经覆盖不到新的热点路径。生成设备的 API、root 状态和库版本要记录进报告；收益验证仍然回到目标发布设备段。

`BaselineProfileRule.collect()` 的运行环境有版本门槛：Android 13 / API 33+ 完整支持，rooted 设备从 Android P / API 28+ 也可运行。低于这两个条件时，`collect()` 会降级或跳过。生成的 profile 规则与被测路径和设备版本绑定，跨版本迁移后需要重新生成。

验证 profile 是否生效优先用 `CompilationMode.Partial(BaselineProfileMode.Require)`，这一模式要求 API 24+ 且被测 APK 由 AGP 7.0+ 打包了 baseline profile 并包含 `androidx.profileinstaller:profileinstaller`。API 23 只有 `CompilationMode.Full()` 可用，`Partial` / `None` 在这一版本不可用。[已验证: AndroidX BaselineProfileRule.kt @RequiresApi(28) + 类注释 API 33+ / rooted API 28+; CompilationMode.kt API 23 only Full]
