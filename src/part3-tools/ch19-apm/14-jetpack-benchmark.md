---
title: "Jetpack Benchmark（Microbenchmark + Macrobenchmark）"
chapter: "19"
section: "19.14"
status: ready-for-review
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "Android Developers Benchmark docs"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-overview"
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: pending
---

# Jetpack Benchmark（Microbenchmark + Macrobenchmark）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 Jetpack Benchmark 用来证明代码改动效果，承担可重复实验，不承担线上监控。
- 🔹 [Microbenchmark] 展开适合测试的对象、JIT / warmup、measurement、Blackhole、state、避免测到日志或随机数。
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

## Microbenchmark 测小代码段

Microbenchmark 在进程内循环执行一段可直接调用的代码，适合测算法、序列化、正则、数据结构、图片处理等局部 CPU 工作。官方文档也说明，它更接近 warmed up JIT 和缓存命中的 best-case 情况。

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

下面这段代码展示冷启动 benchmark 的基本结构，重点看 `measureRepeated()` 包住的启动流程。

```kotlin
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartup() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD
    ) {
        pressHome()
        startActivityAndWait()
    }
}
```

这个测试只适合放在 benchmark module 或独立测试配置里。CI 上还要固定设备、系统版本、充电状态、温度和后台进程，否则数据波动会吞掉优化效果。

## 测试条件优先于代码

Benchmark 最常见的问题是测试条件不稳定。要让结果能被团队信任，至少控制这些变量：

- 设备型号和系统版本固定。
- 关闭省电模式，保持充电和温度稳定。
- 每次测试前清理或固定数据集。
- 区分 debug、profile、release 构建。
- 保留 trace 和原始结果，避免只看单个数字。

冷启动测试还要区分首次安装、清数据后启动、普通冷启动、预编译状态。Baseline Profiles 生效前后，启动结果会明显不同。

## 和线上 APM 的连接方式

线上 APM 发现某个页面 P95 慢帧率升高后，可以用 Macrobenchmark 写一条可重复滑动场景；修复后在 CI 里持续跑。这样线上问题会变成可回归测试。

Microbenchmark 则适合把局部优化变成护栏。比如一个图片解码缓存优化，修完后写 benchmark 防止后续改动又把耗时拉回去。

Benchmark 的作用是把“线上变差”转化成“本地可重复、CI 可防守”的性能测试。

## Benchmark module 的工程形态

书稿级项目里，Benchmark 不应该散落在普通 instrumentation test 中。推荐单独建立：

- `:benchmark`：Macrobenchmark module，控制被测 App。
- `:microbenchmark`：Microbenchmark module，测试可直接调用的热点代码。
- `:app`：被测应用，提供 `benchmark` build type 或 `profile` build variant。

Macrobenchmark 通常要求被测包接近 Release 配置。Debug 包有调试开销、无优化、日志更多，测出来的数据不适合做发布判断。

## Microbenchmark 写法要避免测错对象

Microbenchmark 容易写成“测了测试代码”。比如在 benchmark 循环里构造大量输入数据，会把数据构造成本算进去。

推荐结构：

```kotlin
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
        parser.parse(payload)
    }
}
```

`setUp()` 准备稳定输入，`measureRepeated` 里只放被测代码。否则数据生成、文件读取、对象初始化都会污染结果。

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

## 指标解释

Benchmark 输出的数字要和业务目标对应：

| 指标 | 适合判断 | 误用 |
|---|---|---|
| `StartupTimingMetric` | 冷/温/热启动耗时 | 用它解释首屏数据完成时间 |
| `FrameTimingMetric` | 滚动、转场、动画的帧表现 | 用平均值掩盖 P95 / P99 问题 |
| `TraceSectionMetric` | 自定义 trace 区间耗时 | trace 名称不稳定导致结果断档 |
| Allocation metrics | 局部代码分配压力 | 直接推断 OOM |

启动耗时还要区分 TTID 和 TTFD。系统看到首帧不等于用户可交互。如果业务关心内容可用，需要在 App 中正确调用 `reportFullyDrawn()` 或自定义 trace。

## CI 中的噪声控制

CI 跑性能测试比功能测试更脆弱。建议：

- 使用固定物理设备池，不用普通共享模拟器做最终性能门禁。
- 测试前清理后台任务，固定亮度、刷新率、性能模式。
- 设备温度过高时跳过或降权本轮结果。
- 每个场景至少多次 iteration，看中位数和 P95。
- 保存 trace 文件，失败时能回放分析。
- 阈值用相对回归，例如比 main 分支慢 8% 才报警。

绝对阈值适合发布标准，相对阈值适合 PR 回归。两者不要混在一起。

## 和 Baseline Profiles 的配合

Baseline Profiles 的生成和验证离不开 Macrobenchmark。推荐把这两类测试放在同一套场景里：

- `generateBaselineProfile`：执行关键路径，生成 profile。
- `startupBenchmark`：验证 profile 对启动的影响。
- `scrollBenchmark`：验证 profile 对高频交互的影响。

每次改启动路径、首页依赖或大 SDK 初始化，都要重新跑 profile 生成和 benchmark。否则 profile 可能还存在，但已经覆盖不到新的热点路径。
