---
title: "Macrobenchmark 框架与自动化性能门禁"
chapter: "14.27"
status: ready-for-review
drafted_date: "2026-07-08"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "AndroidX Benchmark 1.4.1 stable + Android 17 (API 37) + android-17.0.0_r1 + android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "developer.android.com/topic/performance/baselineprofiles/overview"
  - type: aosp
    path: "frameworks/support/benchmark/benchmark-macro/src/main/java/androidx/benchmark/macro/"
tags: [macrobenchmark, benchmark, ci, performance-gate, baseline-profile, androidx]
related_chapters: ["8.7", "13.1", "16.1", "21.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "Official docs/AOSP structure"
android17_review_notes: "按 AndroidX Benchmark 1.4.1 稳定版与 Android 17 复核；修正 COLD page cache 语义、TraceMetric API、Gradle 任务和门禁统计独立性"
---

# 14.27 Macrobenchmark 框架与自动化性能门禁

> [!NOTE]
> 复核基线是 2026-07-30 的 AndroidX Benchmark 稳定版 `1.4.1`。AndroidX 独立于 Android 平台发布；测试 Android 17 时，平台锚点仍是 API 37 / `android-17.0.0_r1`。`1.5.0-beta01` 已发布，但预览版不作为门禁基线。

Macrobenchmark 适合测量跨进程的用户旅程，例如冷启动、页面滚动和动画。它能控制应用的启动与编译状态，并为每次测量保留结果和系统 trace。性能门禁还需要稳定设备、可重复数据、版本化结果解析和明确的统计政策，库本身不会把有噪声的 benchmark 自动变成可靠的 pass/fail。

## 1. Macrobenchmark 与 Microbenchmark

| 工具 | 测量对象 | 运行边界 | 典型问题 |
|---|---|---|---|
| Macrobenchmark | 启动、滚动、动画、完整用户旅程 | 测试 APK 从目标应用进程外驱动 | 一次冷启动多长、列表滚动是否退化 |
| Microbenchmark | 可直接调用的函数或代码块 | benchmark 进程内循环 | 某个解析器、布局或算法单次耗时 |

Macrobenchmark 测量最终旅程，Microbenchmark 适合定位已知热点的局部成本。前者不能替代 Perfetto 归因，后者也不能推导整条用户旅程体验。

## 2. 运行模型

Macrobenchmark 使用单独的 instrumentation test APK。测试进程通过 `MacrobenchmarkScope` 和 UI Automator 控制目标应用，目标应用使用接近发布配置的 APK。

一次 `measureRepeated()` 包含：

1. 按 `CompilationMode` 准备目标包的编译状态；
2. 每次迭代执行 `setupBlock`，建立测量前状态；
3. 按 `StartupMode` 处理进程或 Activity 状态；
4. 执行 `measureBlock`；
5. 输出 metric，并为测量迭代保存 trace。

传给 `iterations` 的测量迭代都会进入结果。库不会自动识别“前几次是预热”并从统计中删除。`CompilationMode.Partial(warmupIterations = n)` 的 warmup 发生在 profile 收集与编译准备阶段，语义与丢弃前 n 个测量样本不同。

## 3. 工程配置

### 3.1 依赖版本

[AndroidX Benchmark 发布页](https://developer.android.com/jetpack/androidx/releases/benchmark) 在 2026-07-30 列出的稳定版是 1.4.1；该版本发布于 2025-09-10。下面的依赖用于锁定可复现版本：

```kotlin
dependencies {
    androidTestImplementation(
        "androidx.benchmark:benchmark-macro-junit4:1.4.1"
    )
}
```

CI 不应使用 `1.+` 或 alpha 浮动版本。升级 Benchmark、AGP、UI Automator 或目标系统镜像时，要把它当成测量系统变更，保留一轮旧版/新版对照。

### 3.2 Target 与 benchmark APK

Benchmark 模块通常使用 `com.android.test`，并把 `targetProjectPath` 指向应用模块。目标 build 应满足：

- `debuggable=false`；
- 与发布版本相同的 R8、资源压缩、ABI 和 feature flags；
- 允许 shell profiling 的 `profileable` 配置；
- 固定签名和安装路径，记录 version code，并避免安装/升级数据迁移进入测量区间；
- 测试数据可重复，不依赖不可控线上接口。

抑制 `DEBUGGABLE`、`EMULATOR`、`LOW-BATTERY` 或 `NOT-PROFILEABLE` 警告会掩盖测量环境变化。只在明确的诊断实验中抑制，并把原因写入结果元数据。

## 4. 启动测量

下面的测试用于测量携带 Baseline Profile 的冷启动：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun coldStartup() = rule.measureRepeated(
        packageName = TARGET_PACKAGE,
        metrics = listOf(StartupTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD,
        compilationMode = CompilationMode.Partial(
            baselineProfileMode = BaselineProfileMode.Require
        ),
        setupBlock = {
            pressHome()
        }
    ) {
        startActivityAndWait()
    }
}
```

`BaselineProfileMode.Require` 会在 APK 没有可用 Baseline Profile 或 ProfileInstaller 时使准备阶段失败，适合 CI 验证配置。`UseIfAvailable` 适合兼容实验，却可能把“Profile 没有安装”悄悄变成另一种编译状态。

`StartupTimingMetric` 的公开输出包括：

- `timeToInitialDisplayMs`：系统收到 launch intent 到目标 Activity 首帧；
- `timeToFullDisplayMs`：到 `reportFullyDrawn()` 所覆盖或紧随其后的首帧。

应用没有在业务内容就绪点调用 `reportFullyDrawn()` 时，`timeToFullDisplayMs` 不具备业务含义。官方文档建议启动改进优先观察 median；不应把启动 metric 固定为 P90。

### 4.1 COLD、WARM、HOT

| 模式 | 测量前状态 | 适合场景 | 边界 |
|---|---|---|---|
| `COLD` | 目标进程不存活；默认配置还会清理 shader cache 并请求清理 kernel page cache | 用户从无进程、冷代码/资源缓存状态打开应用 | 不等于设备刚重启，也不会清除应用数据和所有外部缓存 |
| `WARM` | 进程保留，Activity 需要重建或重新启动 | 进程尚在的返回路径 | 进程内缓存和单例会影响结果 |
| `HOT` | 进程与 Activity 保留 | Activity 从 stopped 回到前台 | 接近 resume 路径，覆盖范围最窄 |

每种模式建立独立基线。把三者混成一个“启动 P90”会失去进程状态信息。

## 5. 帧性能测量

下面的测试用于只测量已打开列表的滚动区间：

```kotlin
@Test
fun scrollFeed() = rule.measureRepeated(
    packageName = TARGET_PACKAGE,
    metrics = listOf(FrameTimingMetric()),
    iterations = 10,
    startupMode = StartupMode.WARM,
    compilationMode = CompilationMode.Partial(
        baselineProfileMode = BaselineProfileMode.Require
    ),
    setupBlock = {
        startActivityAndWait()
        device.wait(Until.hasObject(By.res("feed_list")), 5_000)
    }
) {
    device.findObject(By.res("feed_list"))
        .setGestureMargin(device.displayWidth / 5)
        .fling(Direction.DOWN)
}
```

`setupBlock` 把页面启动放在测量区间外，`measureBlock` 只保留滚动动作。每次迭代都要恢复同一列表位置和同一数据集，否则后续样本会测到不同内容。

AndroidX Benchmark 1.4.1 的 `FrameTimingMetric` 主要输出：

- `frameDurationCpuMs`：UI thread 与 RenderThread 生产一帧的 CPU 时长；
- `frameOverrunMs`：相对该帧 deadline 的超时，正值表示错过 deadline，负值表示提前完成。

Frame metric 提供 p50、p90、p95、p99 分布。不能用“16 ms”作为 120 Hz 设备的统一门槛；刷新率、SurfaceFlinger timeline 和每帧 deadline 都会变化。优先使用 `frameOverrunMs` 与 trace 中的 FrameTimeline 归因。

## 6. 自定义 trace 指标

`TraceSectionMetric` 是 AndroidX Benchmark 1.4.1 的公开实验 API。下面的配置用于累加应用 trace section 的总时长：

```kotlin
@OptIn(ExperimentalMetricApi::class)
val bindMetric = TraceSectionMetric(
    sectionName = "Feed#bind",
    mode = TraceSectionMetric.Mode.Sum
)
```

应用必须使用 `Trace.beginSection()/endSection()` 或 AndroidX tracing 生成同名切片。`Mode.Sum` 每个迭代输出 `Feed#bindSumMs` 和 `Feed#bindCount`；求和实现假设切片不重入，嵌套或重叠 section 会重复计算时间。section 名要稳定、短小，并避免在高频细粒度代码中制造明显 trace 开销。

`TraceMetric("name") { "SELECT ..." }` 不是 1.4.1 支持的构造方式。1.4.1 提供了实验性的抽象类 `TraceMetric`：自定义 metric 可以重写 `getMeasurements()`，通过 `TraceProcessor.Session` 执行 SQL；也可以在 CI 中用独立 `trace_processor` 后处理导出的 trace。两条路径都要版本化查询、Perfetto 版本、schema 和单位。

完整的 trace 版本边界见 [13.1 Perfetto 简介与演进](../ch13-perfetto/01-perfetto-intro.md)。

## 7. PowerMetric 的边界

`PowerMetric` 仍是实验 API。官方文档给出的边界包括：

- 指标是整机消耗，无法直接归因到单个应用；
- 支持范围限于 Pixel 6 / Pixel 6 Pro 及后续支持设备；
- 输出是分类的 power `uW` 与 energy `uWs`；
- 可用分类包括 CPU、DISPLAY、GPU、GPS、MEMORY、MACHINE_LEARNING、NETWORK 和 UNCATEGORIZED。

它不承诺所有 Android 12—17 设备都有 CPU/GPU/display energy counter，也不以 mAh 作为统一 metric。AndroidX 1.4.1 没有定义“Android 17 新增 5G modem domain、秒级回调、指定 Qualcomm/MediaTek 型号”这些能力。

功耗用例需要足够长的稳定测量区间，并固定屏幕亮度、网络数据、温度、充电状态和后台账户。结果仍应注明是整机差值。

## 8. CompilationMode 选择

| 模式 | 准备行为 | 用途 | 风险 |
|---|---|---|---|
| `DEFAULT` | API 24+ 等价于可用时使用 Baseline Profile | 快速接近常见安装状态 | Profile 缺失只记录日志，CI 容易漏检 |
| `Partial(Require)` | 要求 APK 内 Profile 可安装并做部分 AOT | 发布基线、Profile 配置验证 | 需要 ProfileInstaller 与正确打包 |
| `Partial(warmupIterations=n)` | 先运行旅程收集 warmup profile，再编译 | 模拟使用后 profile-guided 状态 | 会增加测试时长，语义不同于嵌入 Profile |
| `None` | reset profile，不做预编译 | 观察 JIT/解释执行的较差状态、衡量 Profile 收益 | 不代表常见商店安装状态 |
| `Full` | 对 app methods 做 full AOT | 减少 JIT 噪声、建立特殊上界 | 现代用户设备通常不是该状态 |
| `Ignore` | 不 reset、不编译 | 自定义编译实验 | 调用方负责全部状态控制 |

编译模式必须成为 benchmark identity 的一部分。`coldStartup[Partial-Require]` 和 `coldStartup[None]` 是两个不同基线，不能覆盖到同一趋势序列。

## 9. Baseline Profile 生成与验证

Baseline Profile 生成是独立测试，不是 `measureRepeated()` 的附带步骤。下面的 generator 用于记录启动与关键用户旅程：

```kotlin
class BaselineProfileGenerator {
    @get:Rule
    val baselineProfileRule = BaselineProfileRule()

    @Test
    fun appJourneys() = baselineProfileRule.collect(
        packageName = TARGET_PACKAGE
    ) {
        pressHome()
        startActivityAndWait()
        device.findObject(By.res("nav_search")).click()
        device.wait(Until.hasObject(By.res("search_input")), 5_000)
    }
}
```

Baseline Profile Gradle plugin 把生成结果复制到 variant 对应的 `generated/baselineProfiles` 目录，再随 APK/AAB 打包。Startup Profile 用于 DEX layout，只有启动相关规则才应设置 `includeInStartupProfile=true`。

嵌入 Baseline Profile 与商店 Cloud Profile 可以并存。前者随发布物提供，能在新安装/更新时覆盖关键路径；后者依赖商店分发和用户样本。Android 17 没有“Cloud Profile 取代本地 Baseline Profile”的平台结论。

生成后要做两组 Macrobenchmark：

- `CompilationMode.Partial(BaselineProfileMode.Require)`；
- `CompilationMode.None()`。

两组使用同一 APK、设备、旅程和数据，差异才可用于评估 Profile 收益。完整实践见 [21.4 Baseline Profile 实践](../../part5-app/ch21-startup/04-baseline-profile-practice.md)。

## 10. CI 分层

### 10.1 PR 快检

PR 阶段适合验证 benchmark 可执行、元素能找到、输出可拉取。`androidx.benchmark.dryRunMode.enable=true` 只跑一轮，适合功能检查，不产生可用于性能门禁的统计量。

### 10.2 定时性能任务

稳定门禁放在专用物理设备或稳定的真实设备服务上，固定：

- 设备型号、系统 build、Android 17/API 37 镜像和安全补丁；
- Benchmark/AGP/UI Automator 版本；
- 目标 APK 构建参数、ABI、签名和数据；
- 电量区间、温度、亮度、刷新率、网络和后台工作；
- 每个设备同一时间只运行一个性能任务。

Android 17 trace 涉及内核 sched、frequency、idle 或 power rail 时，源码分析统一锚到 `android17-6.18-2026-06_r6`；设备仍可能包含 OEM 内核差异，报告需保存 `uname` 与 build fingerprint。

### 10.3 执行与产物

下面的命令按官方 `connectedCheck` 入口运行单个 benchmark，并把 JSON/trace 写到设备上的指定目录：

```bash
./gradlew :benchmark:connectedCheck \
  -Pandroid.testInstrumentationRunnerArguments.class=\
com.example.benchmark.StartupBenchmark#coldStartup \
  -Pandroid.testInstrumentationRunnerArguments.additionalTestOutputDir=\
/sdcard/Download/benchmark-output
```

某些项目还会生成 variant 专用的 connected task，使用前应从 `./gradlew :benchmark:tasks` 核对。Android Gradle Plugin 通常会把 additional test output 复制到主机构建目录；CI 仍要从测试输出读取实际文件路径，再上传 JSON、每次迭代 trace、APK 哈希、设备元数据和测试日志。

## 11. 门禁统计

### 11.1 指标政策

不同 metric 使用不同摘要：

- 启动：以 median 为主，同时保存每次迭代值；
- 帧：看 `frameOverrunMs` 的 p90/p95/p99，并保存慢帧 trace；
- trace section：按 count/sum/first 等 mode 明确语义；
- power：使用稳定窗口的整机 power/energy，对同机 A/B。

一次任务中的十个迭代不是十台设备。它们共享温度、缓存和后台状态，不能被当成独立用户样本。门禁应结合多轮独立任务和历史噪声。

### 11.2 归一化数据层

AndroidX JSON schema 会随库版本扩展。解析器应锁定 Benchmark 版本，并把原始结果转换成内部稳定结构。门禁脚本的输入应包含 metric、unit、与 metric 同单位的绝对预算、用小数表示的相对预算、最小配对数，以及 `pairs` 数组。每个 pair 保存同一设备、同一环境区组内 baseline 与 candidate 两次独立 benchmark invocation 的摘要值。

转换层要校验 benchmark name、metric name、unit、device ID、compilation mode、iteration 数、APK 哈希和区组 ID；字段缺失时中止比较，不能把缺失值当成 0。一次 invocation 内的十个 iteration 共同形成一个摘要，不能拆成十个独立 pair。

### 11.3 相对阈值、绝对阈值与置信区间

下面的 Python 片段用于对配对的独立任务摘要做 bootstrap。输入是上一节描述的归一化 JSON，预算和最小样本数由产品策略写入文件：

```python
import json
import random
import statistics
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    data = json.load(source)

pairs = [
    (float(row["baseline"]), float(row["candidate"]))
    for row in data["pairs"]
]
minimum_pairs = int(data["minimumPairs"])
if len(pairs) < minimum_pairs:
    raise SystemExit("insufficient independent benchmark pairs")

absolute_budget = float(data["absoluteBudget"])
relative_budget = float(data["relativeBudget"])
bootstrap_iterations = int(data.get("bootstrapIterations", 10_000))
random.seed(int(data.get("bootstrapSeed", 20260730)))

absolute_deltas = []
relative_deltas = []
for _ in range(bootstrap_iterations):
    sample = random.choices(pairs, k=len(pairs))
    baseline_median = statistics.median(row[0] for row in sample)
    candidate_median = statistics.median(row[1] for row in sample)
    if baseline_median <= 0:
        raise SystemExit("baseline median must be positive")
    delta = candidate_median - baseline_median
    absolute_deltas.append(delta)
    relative_deltas.append(delta / baseline_median)

def percentile(values, quantile):
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]

absolute_ci = [
    percentile(absolute_deltas, 0.025),
    percentile(absolute_deltas, 0.975),
]
relative_ci = [
    percentile(relative_deltas, 0.025),
    percentile(relative_deltas, 0.975),
]

if absolute_ci[0] > absolute_budget and relative_ci[0] > relative_budget:
    status = "fail"
elif absolute_ci[1] <= absolute_budget or relative_ci[1] <= relative_budget:
    status = "pass"
else:
    status = "inconclusive"

print(json.dumps({
    "metric": data["metric"],
    "unit": data["unit"],
    "absoluteDelta95Ci": absolute_ci,
    "relativeDelta95Ci": relative_ci,
    "status": status,
}, indent=2))

raise SystemExit({"pass": 0, "fail": 1, "inconclusive": 2}[status])
```

脚本采用配对设计，区组内的 baseline 与 candidate 应在同一设备上运行，并交替或随机安排先后顺序。失败条件要求绝对增量和相对增量的 95% 区间下界都越过各自预算；任一维度的区间上界仍在预算内时通过，其余情况标为 inconclusive。

预算来自产品 SLA 与同设备历史噪声。样本太少时脚本直接拒绝比较；区间跨越门槛时由流水线冷却设备并增加独立配对，不能把同一次 invocation 的 iteration 重复抽样来凑数量。

## 12. 降低噪声

### 12.1 设备与温度

官方 CI 指南建议使用物理设备。模拟器数字受宿主机调度影响，只适合功能验证。

同一任务内记录：

- battery level 与是否充电；
- thermal status、设备表面温度或可用热指标；
- CPU frequency/idle 与刷新率；
- 后台包和账户；
- 每轮开始/结束时间。

若后半段样本随温度单调变慢，增加迭代只会增加热降频样本。应停止任务、冷却设备并重跑，不能简单取“稳态 P90”掩盖漂移。

### 12.2 网络与测试数据

飞行模式会改变业务路径。更可控的做法是使用固定离线数据、测试服务器或录制响应，并把网络条件作为场景参数。列表条目、图片缓存、账号状态和 AB flag 都要固定。

### 12.3 Cache 边界

在 API 31—37 上，`StartupMode.COLD` 会在每次迭代中停止目标进程。默认的 `androidx.benchmark.dropShaders.enable=true` 还会清理目标 shader cache，随后通过 `perf.drop_caches=3` 请求系统清理 kernel page cache。Macrobenchmark 会等待属性恢复为 0；默认配置下，清理失败会中止测试。

这仍不是“设备重启后的所有缓存都为空”。DNS、GPU 驱动、系统服务、网络端和应用数据缓存各有生命周期。page cache 清理影响全系统，性能设备上不能并行运行其他任务；也不应再由外层脚本额外执行一次 `drop_caches`。

## 13. 从 metric 回到 trace

每个测量迭代都有 trace。发现退化时：

1. 找到 candidate 的异常迭代和同设备 baseline 对照；
2. 对齐 measured journey 起止；
3. 启动问题检查 process start、binder、class load、GC、I/O、first frame；
4. 帧问题检查 FrameTimeline、UI thread、RenderThread、GPU 与 SurfaceFlinger；
5. 使用 trace processor 对同一时间窗运行版本化 SQL；
6. 修复后在原设备、原编译模式、原旅程复测。

不要依赖未经公开承诺的固定 slice 名。应用自定义 section 应由团队维护命名契约，系统 slice 则跟 Perfetto/平台版本一起记录。

## 14. 检查清单

### 测试定义

- 旅程对应高频或高价值用户场景；
- 每次迭代恢复相同页面、数据和滚动位置；
- startup mode 与 compilation mode 写入测试名和结果；
- `reportFullyDrawn()` 对应业务内容就绪；
- target APK 为非 debuggable 的发布等价构建。

### 门禁

- 固定物理设备和系统 build；
- 保留原始 JSON、trace、APK 哈希与设备信息；
- 启动使用 median，帧使用 overrun 分位数；
- 同时应用相对与绝对预算；
- 样本不足或置信区间过宽时重跑；
- 每次测量系统升级先做旧版/新版对照。

### 归因

- 指标异常后查看对应迭代 trace；
- 自定义 SQL 与 Perfetto 版本一起维护；
- 线下结果定期与线上相同口径的启动/慢帧数据校准；
- 线上差异很大时补旅程与设备覆盖，不放宽门禁掩盖缺口。

## 参考资料

- [AndroidX Benchmark 1.4.1 发布页](https://developer.android.com/jetpack/androidx/releases/benchmark)
- [Macrobenchmark 指南](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Benchmark in CI](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Macrobenchmark instrumentation arguments](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-instrumentation-args)
- [CompilationMode API](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode)
- [TraceSectionMetric API](https://developer.android.com/reference/androidx/benchmark/macro/TraceSectionMetric)
- [Baseline Profile 生成](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [Baseline Profiles 概览](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Android 17 common kernel tag `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
