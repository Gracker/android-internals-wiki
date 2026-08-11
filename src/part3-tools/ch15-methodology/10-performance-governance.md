---
title: "性能治理工程化"
chapter: "15.10"
section: "15.10"
status: finalized
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1；AndroidX Benchmark 1.4.1 sources；Baseline Profiles 与 Android Vitals 官方文档"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: source
    path: "https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro/1.4.1/benchmark-macro-1.4.1-sources.jar"
  - type: source
    path: "https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro-junit4/1.4.1/benchmark-macro-junit4-1.4.1-sources.jar"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6"
tags: [governance, benchmark, ci, budget, release]
related_chapters: ["7.1", "8.1", "8.3", "9.1", "14.9", "15.3", "15.5", "15.6", "15.9"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: "2026-04-21"
reviewed_by: openclaw-task6
task9_state: reviewed
repaired_date: "2026-04-22"
repaired_by: "codex"
task9_result: fixed
task9_reviewed_date: "2026-05-19"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-19T21:04:13+08:00"
last_task6_audit: "2026-07-15"
task2b_result: fixed
task2b_state: fixed
last_task9_audit: "2026-05-19"
last_task9_review_log: "logs/deep-review/2026-05-19-20-audit.md"
task9_review_notes: "2026-05-19 20 Task9 闲时抽检 → Task2B fixed: frontmatter 官方来源 URL 已替换为 benchmarking-overview。"
---

# 性能治理工程化

## 从个人能力转为团队机制

会读 Perfetto、会分析 heap、熟悉 ART 或 SurfaceFlinger 的工程师仍然很重要。团队风险来自这些能力只存在于少数人手中：版本回归依靠临时救火，分析方法无法复用，修复完成后也没有稳定验收。

工程化治理要固定五类决策：

- 哪些用户旅程属于 Critical User Journey（CUJ）；
- 每条旅程采用什么指标、预算和设备；
- 什么变化需要评审、阻断、灰度或回滚；
- 异常由谁调查，证据如何交接；
- 修复通过什么线下测试和线上指标验收。

机制的目标是可重复决策。不同工程师面对同一份数据，应得到相近的发布结论；对结论有异议时，也能查到预算、基线、例外和证据。

## 五个支点

### 1. 预算：先固定测量契约

性能预算不能只写“启动 2 秒以内”。至少包含：

| 字段 | 示例含义 |
|---|---|
| CUJ | 冷启动到首页 TTID、warm start 到 TTFD、Feed 连续滑动 |
| 指标 | `timeToInitialDisplayMs`、frame overrun、峰值 RSS、包体积 |
| 人群/设备 | 低内存设备、主力 SoC、API 26、API 37 |
| 构建与编译状态 | benchmark/release 变体、R8 状态、Baseline Profile 模式 |
| 统计口径 | median、P90、失败率、样本数、窗口 |
| 预算 | 绝对上限、相对回归上限或两者组合 |
| 动作 | 提醒、阻断合入、停止灰度、回滚 |
| owner | 指标 owner、CUJ owner、批准例外的角色 |

预算可以分为三层：

- **用户体验 SLO**：线上启动、帧、ANR、crash、OOM、耗电等用户结果；
- **实验室回归预算**：固定设备与场景下的 Macrobenchmark、内存和 CPU 结果；
- **资源预算**：下载大小、安装大小、DEX/资源增长、启动初始化和后台资源。

三层不能互相代替。线下启动稳定不代表全部厂商设备稳定；线上曲线稳定也可能由灰度量小或采样延迟造成。发布决策要说明使用了哪一层证据。

### 2. 基线：记录比较条件

预算描述目标，基线描述某组条件下已经测得的水平。更新基线时至少保留：

- git commit、version code、依赖锁文件与构建变体；
- benchmark/library/AGP/JDK 版本；
- 设备型号、serial 或实验室资产 ID、Android build fingerprint；
- 电量、温度、刷新率、网络与测试数据；
- compilation mode、startup mode、迭代数；
- JSON 结果、每轮 trace 和失败日志。

基线必须与候选版本使用同一设备和同一配置。把 Pixel 的结果与另一品牌设备比较，把 `CompilationMode.None` 与 `Partial` 比较，或把 debug 与 benchmark 变体比较，所得差值都包含测试条件变化。

基线也不是目标。某个历史版本已经超出 SLO 时，不能因为它“当前如此”就继续接受同等表现。预算变更与基线更新应由不同操作完成，并留下评审记录。

### 3. 回归门禁：按证据确定强度

门禁可以分三类：

| 类型 | 适合内容 | 失败动作 |
|---|---|---|
| 确定性门禁 | CUJ 脚本可运行、APK/AAB 含 profile、包体积、禁用 API、缺少 mapping/symbol | 直接阻断 |
| 测量门禁 | 启动、帧、内存、CPU benchmark | 达到样本与噪声规则后阻断；其余标记需复测 |
| 线上门禁 | 灰度 ANR/crash、启动 tail、慢帧、OOM、退出原因 | 暂停扩量、关闭开关或回滚 |

Benchmark 是带噪测量。Android 官方 CI 文档明确提醒，它不像普通测试那样天然只有 pass/fail。可靠门禁要先测量设备自身的历史噪声，再规定：

- 候选与基线的最小重复次数；
- 可以比较的设备池；
- 允许的绝对差和相对差；
- 测量失败、thermal throttle、低电量和设备离线如何处理；
- 何时自动复测，复测几次后转人工判断；
- 哪些 trace 和 JSON 必须归档。

PR 可以运行 dry run，验证脚本、安装和导航是否正常。性能数值适合在稳定真机池的 nightly、合入队列或发布流水线评估。官方强烈不建议用模拟器结果代表用户性能；模拟器可用于 CUJ 脚本冒烟和部分 profile 生成。

不要在 CI 中全局压制 Macrobenchmark 的配置错误。target app 为 debuggable、未设为 profileable、设备为 emulator 或低电量时，库会报告可能损害测量的错误。单项抑制需要记录原因和到期时间。

### 4. 灰度观测：验证设备分布

灰度需要覆盖：

- TTID、TTFD 和关键页面 tail；
- frame overrun、慢帧/冻帧与交互失败；
- user-perceived ANR、crash、OOM 与 `ApplicationExitInfo`；
- 内存、后台 CPU、WakeLock 与网络异常；
- 设备型号、SoC/GPU、SDK、渠道、地域和实验分群。

灰度组与对照组要处于相同时间窗，并控制版本、设备和远程配置。服务端延迟、活动流量、网络变化和实验开关都可能改变客户端结果。只看全局平均值会隐藏少数高流量机型或低内存设备。

Google Play 的 Android Vitals 提供发布质量信号，自建指标提供更细场景与更快回查。两者分母、延迟和覆盖范围不同，门禁页面要标明数据源。Play 的阈值可作为外部红线，内部预算通常要更早发现趋势。

灰度规则应预先写明扩量、暂停和回滚条件。临时调整条件要进入发布记录，避免数据出现后再选择更宽松的口径。

### 5. 发布验收：把结论写回版本

发布验收记录至少包含：

- CUJ 线下结果与预算结论；
- profile、mapping、native symbols 等构建产物检查；
- 灰度指标、样本量、观察窗口和重点设备；
- 未解决问题、已批准例外和到期日；
- 发布/暂停/回滚决定及批准人；
- 上线后复查时间和 owner。

验收结果关联 commit、build、benchmark JSON、trace、dashboard 和工单。后续发现回归时，可以区分“当时没有信号”“规则没有触发”“例外放行”和“发布后环境变化”。

## Macrobenchmark 进入 CI 的正确方式

Macrobenchmark 在独立 `com.android.test` 模块中从应用外部驱动 CUJ。target app 应使用接近 release 的 benchmark 变体，保持 non-debuggable，并通过 `<profileable>` 允许读取详细 trace。CI 构建 target APK 与 test APK，再安装到固定真机执行。

下面的测试已按 AndroidX Benchmark 1.4.1 源码核对，用于测量带 Baseline Profile 的冷启动。它把编译模式写进用例，避免 CI 默认值变化后仍沿用旧基线。

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartupWithBaselineProfile() =
        benchmarkRule.measureRepeated(
            packageName = TARGET_PACKAGE,
            metrics = listOf(StartupTimingMetric()),
            compilationMode = CompilationMode.Partial(
                baselineProfileMode = BaselineProfileMode.Require,
                warmupIterations = 0,
            ),
            startupMode = StartupMode.COLD,
            iterations = 10,
            setupBlock = {
                pressHome()
            },
        ) {
            startActivityAndWait()
        }
}
```

`BaselineProfileMode.Require` 会要求 APK 内存在可安装的 Baseline Profile，适合验证 profile 场景。`StartupMode.COLD` 会在 setup 与 measure 之间终止 app 进程；它描述进程冷启动，不等于设备重启后的全系统冷缓存。每个 iteration 会生成相应的 system trace，CI 还应归档 benchmark JSON。

测试脚本要固定应用状态。若 CUJ 依赖不稳定网络，可使用受控测试后端或确定性数据；不要把公网波动当成 app 启动回归。需要测网络场景时，网络延迟本身也要成为实验变量和输出。

### 从结果到门禁

不要直接对单次 median 写一条 shell 比较。门禁程序应读取 JSON，并做以下检查：

1. 验证设备、build、metric、compilation/startup mode 与基线匹配。
2. 排除框架明确标记为错误的运行，保留排除原因。
3. 比较每次 iteration，检查候选差值是否大于历史噪声。
4. 同时应用绝对预算和相对回归预算。
5. 对临界结果自动在同一设备复测。
6. 阻断时附上最慢 iteration 的 trace 和基线 trace。

真机池也会漂移。设备系统更新、换电池、存储老化或环境温度变化后，应重新建立基线，不能静默继承旧数据。

## Baseline Profiles 与 Startup Profiles

Baseline Profile 指导 ART 对常用代码路径做 AOT 编译，覆盖启动和其他关键交互。Startup Profile 用于 DEX 布局，使启动相关类和方法更适合放入 primary DEX。两者用途不同，官方建议同时使用。

Android 8—17 范围内：

- Android 8 / API 26—27 使用 partial AOT；有 `ProfileInstaller` 时可在首轮运行后安装 Baseline Profile；
- Android 9 / API 28 及以上还可获得 Google Play 聚合的 Cloud Profiles；
- Cloud Profile 需要真实使用数据并有分发延迟，不能保护新版本最初一批用户；
- 非 Play 分发渠道的安装和编译行为需要单独验证。

Baseline Profile 工程检查分三层：

1. **生成**：`BaselineProfileRule` 覆盖启动与稳定 CUJ，profile 随重要代码变化更新。
2. **打包**：AAB 中检查 `/BUNDLE-METADATA/com.android.tools.build.profiles/baseline.prof`，APK 中检查 `/assets/dexopt/baseline.prof`。
3. **效果**：在真机上比较带自定义 profile 的 release 变体与只含 library profile 的对照变体。

profile 文件存在只是打包成功的初步证据。`ProfileVerifier` 可以查询 profile 安装/编译状态，但不提供“某个业务方法的 Baseline Profile 命中率”。评估时应分别检查打包状态、编译状态和 CUJ 性能收益。

生成 profile 与测量性能的设备要求也不同。官方允许为了便利在 emulator/GMD 上生成规则，因为生成过程不采集性能数值；收益测量使用物理设备。Firebase Test Lab 当前不支持 Baseline Profile 生成，这一点与“在 Test Lab 真机跑 Macrobenchmark”不能混为一谈。

每次发布不必无条件扩大 profile。规则过宽会增加编译、磁盘和安装成本，官方文档还给出打包后二进制 profile 小于 1.5 MB 的约束。CUJ owner 要审查新增 journey 是否稳定、常用，并验证对其他场景没有负面影响。

## 代码评审中的性能检查

以下变化应触发性能影响说明：

- `Application`、ContentProvider、App Startup initializer 或首个 Activity 的初始化；
- 主线程文件/数据库/网络、同步 Binder、锁和反射；
- 图片、序列化、数据库 schema、缓存和大数据路径；
- View measure/layout/draw、Compose state/recomposition 与列表绑定；
- 新 SDK、动态特性、native 库、资源或包体积增长；
- 后台 Job、alarm、WakeLock、定位、传感器和轮询；
- Baseline/Startup Profile 的 CUJ 或构建配置变化。

PR 模板可以要求作者填写：

- 受影响 CUJ 与线程；
- 新增工作在调用链中的位置；
- 预期复杂度、数据规模和设备边界；
- 已运行的 benchmark/trace 或无需测量的理由；
- 线上观察指标和失败开关。

评审线索用于决定是否测量，不能只凭“看起来可能慢”要求重写。命中高风险路径时补 Macrobenchmark、Microbenchmark 或系统 trace；影响低且路径不频繁时，记录判断即可。

## 角色与交接

| 角色 | 主要责任 |
|---|---|
| Feature/CUJ owner | 场景脚本、代码修复、业务正确性、线上验收 |
| 性能平台团队 | 指标契约、真机池、benchmark 工具、采样与 dashboard |
| Release/值班角色 | 灰度节奏、门禁执行、暂停与回滚 |
| 系统/ROM 团队 | framework、system_server、调度、thermal、GPU/驱动问题 |
| 数据/服务端团队 | 服务延迟、实验分群、数据完整性与查询成本 |

每个问题只有一个当前 owner。跨团队协作可以有多名参与者，但调查状态、下一动作和时限由当前 owner 维护。转交给系统或厂商团队时，证据包至少包含：

- app build、复现步骤与发生率；
- 设备型号、Android build fingerprint、kernel build；
- 正常与异常对照；
- Perfetto/bugreport/tombstone 等现场；
- 已排除的 app 侧假设；
- 期望对方验证的具体问题。

“trace 里 system_server 很忙”不足以完成转交。需要沿 Binder flow、线程状态、锁、I/O 或调度证据指出可调查入口。涉及内核的判断固定到 `android17-6.18-2026-06_r6`；厂商设备按设备对应源码复核。

## 例外机制

业务可以在明确条件下接受性能回归。例外记录必须包含：

- 指标、设备/CUJ、回归量和用户影响；
- 放行原因、补偿措施与风险；
- owner、批准人和到期日期；
- 计划修复版本或重新评估条件；
- 灰度观察与回滚规则。

例外到期后自动恢复原门禁。若团队决定永久调整预算，应提交预算变更评审，展示用户影响、历史趋势和替代指标。不能通过更新基线隐藏回归，也不能无限延长同一例外。

## 日常、版本和事故

### 日常

- PR dry run 验证 CUJ，风险变更补充性能影响说明；
- nightly 在固定真机跑关键 Macrobenchmark；
- 趋势任务检查设备噪声、结果缺失和 profile 产物；
- 线上 dashboard 按版本和设备分群审计。

### 发布前与灰度

- 冻结 benchmark、metric schema 和 sampling config 版本；
- 生成并检查 Baseline/Startup Profile；
- 运行 release candidate 的完整 CUJ 集；
- 检查未关闭工单、例外和回滚开关；
- 灰度阶段按预设规则扩量或暂停。

### 事故

- 保留异常窗口、配置和证据；
- 通过暂停扩量、开关、降级或回滚限制影响；
- 比较正常/异常分群并验证归因；
- 修复后同时复测线下 CUJ 与线上指标；
- 只把稳定、可重复的检测方法加入日常门禁。

事故复盘的产物可能是新 CUJ、指标、告警、lint、profile journey 或操作手册。若问题依赖偶发外部条件，强行加入不稳定硬门禁会制造噪声；此时更适合线上预警或人工专项。

## 从小规模开始

一个可运行的最小版本包括：

1. 选择启动、首页和一个高频交互作为 CUJ。
2. 为每条 CUJ 写指标契约、预算和固定真机。
3. PR 跑脚本 dry run，nightly 跑完整 Macrobenchmark。
4. 生成 Baseline/Startup Profile 并检查发布产物。
5. 灰度观察启动、帧、ANR、crash、OOM 和退出原因。
6. 所有回归进入带 owner、验收和到期时间的工单。

稳定运行后再增加设备、场景和硬门禁。门禁数量不是成熟度指标；可靠覆盖高价值 CUJ、能够解释失败并持续验收，才说明机制有效。

## 与其他章节的关系

- §7、§8、§9 解释流畅性、启动和 ANR 的平台机制。
- §14.9 说明 Macrobenchmark 的用法与回归门禁边界。
- §15.3 定义性能指标契约。
- §15.5 讨论线上监控和保护开关。
- §15.6 讨论测试设计与统计可靠性。
- §15.9 连接采集、归因、工单和验收。
- §15.10 定义团队怎样把这些能力放进开发和发布流程。

平台源码锚点固定为 Android 17 / API 37 / `android-17.0.0_r1`。Benchmark、Baseline Profile 与 ProfileInstaller 属于 AndroidX/构建工具，版本应在项目依赖和基线记录中单独固定。涉及 CPU 调度、Binder driver、cgroup 或 thermal 的内核证据，使用 `android17-6.18-2026-06_r6`。

## 参考资料

- [Android 官方：Benchmark overview](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [Android 官方：Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Android 官方：Benchmark in CI](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Android 官方：Android Vitals](https://developer.android.com/topic/performance/vitals)
- [Android 官方：Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Android 官方：Create Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [Android 官方：Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Android 官方：Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
