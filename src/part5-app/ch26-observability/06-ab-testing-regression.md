---

title: "A/B Test 与性能回归防护"
chapter: "26.6"
section: "26.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-06-04"
last_verified_against: "Android Developers Macrobenchmark docs 2026-05-19 + Firebase docs + Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 0
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/training/testing/instrumented-tests/performance"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://firebase.google.com/docs/ab-testing/abtest-config"
tags: [ab-testing, regression, ci-cd, performance-gate]
related_chapters: ["26.7", "26.3", "15.6"]
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-04
task6_result: pass-light-edit
last_task6_at: "2026-06-04T06:08:46+08:00"
task6_review_notes: "2026-05-15 Task6 05:15：needs-rework。完成 L1/L2 小修 4 处；L3 技术/证据边界已标注并合并 queue，交 Task2B。"
task9_state: reviewed
task2b_state: fixed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-04"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-04T03:20:00+08:00"
task9_review_notes: "2026-06-04 Task9 auto-fix：补充 StartupTimingMetric.timeToFullDisplayMs 在 Android 10/API 29 及以下可能不可用的版本边界；回到 Task6 复审。"
task2b_result: fixed
last_task2b_at: 2026-06-04T00:55:43+08:00
task2b_fixed_by: openclaw-task2b-main
task2b_fix_round: 2026-06-04-00
last_task9_autofix_at: "2026-06-04"
last_task9_review_log: "logs/deep-review/2026-06-04-03-deep-review.md"
---

# A/B Test 与性能回归防护

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 性能 A/B Test 的设计与统计方法
- 🔹 性能回归自动检测
- 🔹 CI/CD 集成性能卡点
- 🔹 性能劣化的自动归因

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 A/B Test 与性能回归防护

性能治理走到发布阶段后，判断对象会从单次优化结果变成一组风险问题：新版本能不能继续扩大灰度，某个配置能不能放量，某次启动优化有没有伤到低端机，某个页面改版是不是让慢帧率上升。A/B Test 和回归防护处理的正是这些问题。

26.3 节已经讲过性能指标采集与上报，本节不重复指标采集方法，只处理实验设计、回归检测、CI/CD 门禁和劣化归因。Part 5 的侧重点是实战动作：怎样把线下 benchmark、线上分流实验、灰度监控和发布决策放到同一套判断流程里。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]

## 性能 A/B Test 的设计与统计方法

性能 A/B Test 不能只看“新方案平均耗时更低”。启动、渲染、内存、功耗都带有明显长尾，同一个方案在高端机上变快，在低端机上变慢也很常见。实验开始前要把主指标、护栏指标、分群维度和停止条件写清楚。

| 设计项 | 推荐做法 | 风险 |
| --- | --- | --- |
| 实验单元 | 按用户 ID 或安装 ID 稳定分桶，同一用户在实验期间保持同一方案 | 按请求随机会让同一用户反复切换，指标会被污染 |
| 主指标 | 每个实验只选一个主判断指标，例如首页冷启动 TTFD P90、Feed 滚动慢帧率、图片解码 P90 | 主指标过多会让团队挑对自己有利的数字 |
| 护栏指标 | 同时观察 Crash、ANR、内存水位、功耗、上报成功率和业务转化 | 只看性能收益可能放过稳定性或业务损伤 |
| 分群维度 | 至少拆设备档位、Android 版本、国家 / 地区、网络类型、启动入口 | 全量指标正常时，单一低端机分群可能已经劣化 |
| 停止条件 | 样本量、运行天数、最小可接受收益和回滚阈值提前确定 | 边看边停会抬高误判概率 |

Clippings 的发布章节把 A/B Test 的难点放在人群和时间窗上：实验组和对照组要在同一时间运行，人群分布要足够接近，差异才有资格归到方案本身。性能实验还要多一层设备分布约束：低端机、老系统、弱网用户不能被平均值掩盖。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]

Firebase A/B Testing 的 Remote Config 实验提供了一个可参照的产品形态：配置目标用户、目标用户百分比、基线版本和实验版本，并选择主指标与附加指标；目标用户可以按版本、语言、国家 / 地区、Analytics audience、user property 等条件筛选。官方文档也要求 activation event 发生在配置值生效之后，否则实验数据会把未使用新配置的用户算进去。[已验证: 官方文档, firebase.google.com/docs/ab-testing/abtest-config]

性能实验的统计口径需要区分指标类型，不同指标对应的检验对象和样本量估计方式不一样：

**均值/比例类指标**（TTFD 均值、慢帧率、crash rate）：
- `baseline_value`：对照组当前值，例如首页冷启动 TTFD 均值 1200 ms，或慢帧率 3.2%。
- `minimum_detectable_effect`：业务上值得采用的最小变化，例如 TTFD 均值降低 80 ms 或慢帧率降低 0.5 个百分点。
- `baseline_variance` / `baseline_rate`：均值类需要历史标准差（SD）或方差；比例类需要 baseline rate，用来确定所需样本量。没有方差估计的样本量计算只是把四个数字放进公式，结论不可靠。
- `alpha`：显著性水平，常见取值 0.05，限制误判"有差异"的概率。
- `power`：统计功效，常见取值 0.8 或 0.9，限制漏判"有差异"的概率。
- `allocation_ratio`：实验组与对照组的流量分配比例，影响所需总样本量。

**P90/P99 分位值指标**（TTFD P90、帧耗时 P99）：
- 分位值是秩统计量，不能套用均值类样本量公式。需要根据 baseline 分布、检测目标和对 tail 的敏感度来估计。
- 工程上可以用两种方式替代精确的 quantile CI：
  - **阈值违约率**：设定"TTFD P90 超过 2500 ms"的样本比例作为检验对象，用比例类公式计算样本量。
  - **bootstrap 估计**：对已有数据做 bootstrap 重采样，检查在给定样本量下 95% CI 宽度是否小于 MDE。
- 分设备档位/Android 版本后，每个关键分群都要重新计算最小样本量。低端机分群本身就小，分位值 CI 会更宽；此时应优先参考阈值违约率。

样本量不足时，实验报告只输出"数据不足"结论，不把短时间波动写成性能收益。灰度用户少、指标发生率低、分群过细都会让实验周期变长；这时适合先用实验室 benchmark 或内部体验包排除大风险，再用线上实验验证真实用户分布。

A/A Test 是性能实验平台的验收手段。两个组拿到同一份配置时，主指标应该没有系统性差异；如果 A/A 就出现明显差异，分桶、采样、上报、数据计算至少有一处存在偏差。正式性能实验前保留一段 A/A 或 A/A/B 空转，能提前暴露埋点缺失、分流不均和统计任务延迟。

A/A Test 还要检查多重比较风险。日常看板频繁窥探、多分群（设备档位 × 系统版本）和多护栏指标（Crash + ANR + 内存 + 功耗）同时检查时，假阳性会被放大。建议在 A/A 阶段验证以下控制手段：
- **SRM（Sample Ratio Mismatch）**：每个关键分群内检查配置比例与实际样本比例是否一致。
- **假阳性率验证**：按实际看板频率模拟检查，确认 α=0.05 设定下实际误判率不超预期。
- **多重比较校正**：多护栏指标或多分群同时检查时，使用 Bonferroni 校正或 FDR（Benjamini-Hochberg）控制整体错误率。
- **sequential testing / alpha spending**：针对中途看数需求，预注册检查窗口并使用 alpha spending function（如 Lan-DeMets O'Brien-Fleming），避免每次按 α=0.05 直接判断、等效于多轮重复测试。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]

## 性能回归自动检测

性能回归检测分成两条线：实验室基线和线上分布。实验室基线负责在代码合入、候选包、发版前发现确定性退化；线上分布负责发现真实用户环境里的长尾问题。两条线不能互相替代。

Android 官方性能测试文档把 runtime performance 分成 local testing 和 field testing。field testing 观察真实用户环境，local testing 使用 benchmark 库在可控设备上复现用户流程；官方也建议频繁运行性能测试，并把结果保存下来做时间序列对比。[已验证: 官方文档, developer.android.com/training/testing/instrumented-tests/performance]

回归检测适合采用三类规则组合：

| 规则 | 示例 | 适合拦截的问题 | 处理动作 |
| --- | --- | --- | --- |
| 相对变化 | 新包首页 TTFD P90 比基线高 8% | 中等幅度、稳定复现的性能退化 | 候选包阻断或灰度暂停 |
| 绝对阈值 | 冷启动 P90 超过 5 s，冻帧率超过 0.1% | 已经接近用户可感知的问题 | 进入 P0/P1 风险评估 |
| 分群异常 | Android 13 + 4 GB 内存设备慢帧率翻倍 | 全量指标被平均值盖住的设备问题 | 限制放量范围，派发给相关模块 |

Macrobenchmark 适合承担实验室基线。`StartupTimingMetric` 输出 `timeToInitialDisplayMs` 和 `timeToFullDisplayMs`；其中 `timeToFullDisplayMs` 依赖应用通过 `reportFullyDrawn()` 报告完全绘制，官方文档说明该测量在 Android 10（API 29）及以下可能不可用。`FrameTimingMetric` 的基础输出 `frameDurationCpuMs` 在所有受支持版本上可用；`frameOverrunMs` 仅在 Android 12（API 31）+ 上可用，它反映帧实际耗时超出预期帧间隔的部分。Android 10/11（API 29/30）设备上的 CI 门禁不能依赖 TTFD 或 overrun 作为唯一口径，应改用 `timeToInitialDisplayMs`、`frameDurationCpuMs`、慢帧率（slow frame rate）或冻结帧率（frozen frame rate）作为替代口径。`TraceSectionMetric` 按自定义 trace section 统计次数和耗时；`PowerMetric` 在支持的 Pixel 设备上记录测试期间的能耗变化。门禁配置中需补 `metric_available_api` 字段，避免跨版本混算同一阈值。官方文档要求 benchmark 输出 JSON 和 Perfetto trace，产物应进入 CI 存档，不留在本地控制台。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics；developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]

线上回归检测要沿用 26.3 节的分位值和采样字段。检测任务至少按 `metric_name`、`scene_id`、`app_version`、`experiment_id`、`variant_id`、`device_tier`、`android_version` 分桶。没有分桶的 P90 只代表混合分布，不能支持版本决策。

告警去噪比阈值本身更影响体验。样本量不足时只记录风险，连续多个时间窗异常再升级；服务端故障、活动流量、配置切换和采样策略更新要能标记为外部事件。性能告警一旦变成噪音，发布团队会绕过它。

Android Vitals 可以作为外部校验源。官方文档列出了 user-perceived crash rate、user-perceived ANR rate、excessive partial wake locks 等 core vitals，也包含启动时间、慢渲染、Slow Sessions 等质量信号；Play 会使用最近 28 天数据评估质量，并对 bad behavior threshold 给出警告。自建 APM 和 Vitals 的统计口径不同，发布报告要保留两套数字的定义，避免把 Vitals 的每日活跃用户口径和内部 session 口径混用。[已验证: 官方文档, developer.android.com/topic/performance/vitals]

## CI/CD 集成性能卡点

CI/CD 里的性能卡点要分层，不能把所有 benchmark 都塞进每个 PR。每次提交都跑完整启动、滚动、功耗和弱网测试，队列会很快排满；完全不在 CI 里跑，回归又会拖到灰度阶段才暴露。

推荐把卡点拆成三档：

| 阶段 | 运行内容 | 失败动作 | 产物 |
| --- | --- | --- | --- |
| PR 快检 | benchmark 编译、dry run、少量 smoke 场景 | 阻断合入，修复测试或脚本 | 测试日志、失败栈 |
| 主干夜间 | 固定设备上的启动、滚动、TraceSection benchmark，多轮采样 | 生成回归任务，必要时冻结主干 | JSON、Perfetto trace、趋势图 |
| Release 候选 | 覆盖低 / 中 / 高端设备、目标系统版本、主业务路径 | 阻断发包或降级为小流量灰度 | 签名包、报告、门禁结论 |

官方 CI 文档里，Macrobenchmark 需要分别构建目标 APK 和测试 APK，再通过 `adb shell am instrument` 运行；benchmark 结果包含测量 JSON 和 trace 文件。CI 系统要把这些产物按 commit、branch、device、benchmark name 归档，后端才能做趋势对比。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]

这段配置示例只说明门禁表达方式：阈值要带场景、设备和处理动作，不要写成一个全项目共享的数字。

```yaml
performance_gates:
  - name: home_cold_start
    metric: time_to_full_display_ms_p90
    device_group: low_end_android_12_14
    baseline: last_green_release
    fail_if_relative_regression: 0.08
    fail_if_absolute_over_ms: 5000
    min_samples: 300
    action: block_release_candidate
  - name: feed_scroll_jank
    metric: slow_frame_rate
    device_group: mid_end_90hz
    baseline: last_green_release
    fail_if_relative_regression: 0.15
    min_samples: 500
    action: pause_rollout
```

配置里的 `baseline` 不能总指向上一轮测试。上一轮测试本身可能已经退化，连续小退化会被逐次放过。更稳的做法是同时保留 `last_green_release`、`main_branch_7d_median` 和 `manual_pinned_baseline` 三种基线，报告里展示命中了哪一种。

性能卡点还要允许人工豁免，但豁免必须可追踪。常见豁免理由包括：新功能主动增加首屏内容、测试设备温度异常、外部服务波动、实验包只影响内部灰度。豁免单至少记录责任人、过期时间、指标变化和补偿计划；过期后自动恢复门禁。

## 性能劣化的自动归因

自动归因的目标是把排查范围缩小到可验证的候选，不负责一次性裁定“谁写坏了”。性能告警应该带着证据进入排查：哪个版本、哪个实验、哪个场景、哪个设备分群、哪条 trace section 变慢、样本列表在哪里。

归因输入建议固定成五类字段：

| 字段组 | 典型字段 | 用途 |
| --- | --- | --- |
| 发布字段 | app version、build id、git commit、渠道、灰度批次 | 判断是否由包体或代码变化引入 |
| 实验字段 | experiment id、variant id、参数快照、命中时间 | 判断是否由配置或功能开关引入 |
| 场景字段 | scene id、入口、启动类型、页面、业务阶段 | 判断是否集中在某条用户路径 |
| 设备字段 | 机型、SoC、内存档位、Android 版本、刷新率、国家 / 地区 | 判断是否是兼容性或性能档位问题 |
| 证据字段 | trace section、慢帧样本、日志摘要、网络错误码、Crash / ANR 组 | 支持工程团队复现和定位 |

自动归因可以按贡献度排序，但算法必须和指标类型匹配：

**均值/比例类指标**使用线性贡献：分群样本量 × 分群均值变化量 ≈ 对全量均值变化的贡献。一个 2% 用户分群的 TTFD 均值上升 200 ms，和 40% 分群上升 10 ms，贡献度能帮团队决定先排查哪个分群。

**P90/P99 分位值**不能直接用"样本量 × P90 delta"归因。P90 是非线性秩统计量，各分群 P90 的加权变化之和不等于全量 P90 的变化。尾部退化要用以下方式定位：
- **tail violation count**：统计每个分群中超过告警阈值（例如 TTFD > 2500 ms）的样本数，按分群排序，找对尾部长尾贡献最大的分群。
- **counterfactual 重算**：把某个分群的样本从全量中移除后重算 P90，对比前后差异，得到该分群对全量 P90 的边际影响。
- **mean excess over threshold**：对超过阈值的样本计算超出量的均值，按分群比较超出幅度。

如果一个 2% 的低端机分群 P90 上升 2000 ms，排查优先级确实高于 40% 分群的 P90 上升 40 ms——但这个判断要用 violation count 或 counterfactual 重算来验证，而不是用线性公式。

TraceSectionMetric 和业务 trace 名称要提前统一。线下 benchmark 里 `home.bind_data` 变慢，线上同名摘要也变慢，归因系统就能把告警指到首页数据绑定阶段；如果线下叫 `HomeBind`，线上叫 `feed_first_render`，后端只能靠人工猜。26.3 节已经建议自定义 Trace 和线上摘要使用同名阶段，这里直接复用该规则。

自动归因的排查顺序可以写成固定流程：

1. 比对实验组和对照组，确认退化是否只出现在某个 variant。
2. 比对新版本和上一 green release，确认退化是否随包体发布出现。
3. 按设备档位和 Android 版本排序贡献度，确认是否只影响特定设备群。
4. 拉取 Top 慢样本的 trace section、启动入口、网络错误和日志摘要。
5. 如果 trace 指向业务阶段，派给业务模块；如果指向系统阶段，关联到 13.2、15.6、21.x、22.x、23.x 对应章节做线下复现。

这套流程不会消除人工分析，但能避免每次告警都从群里问“最近谁改了”。工程团队拿到的是可复核的候选清单，而不是单个结论。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]

## [自动发现] 样本比例失衡与实验污染

性能 A/B Test 要监控 SRM（Sample Ratio Mismatch，样本比例失衡）。如果平台配置是 50% / 50%，实际样本却变成 60% / 40%，实验结果就不能直接使用。常见原因包括分桶 hash 变更、安装 ID 重置、版本过滤条件写错、某个 variant 启动崩溃导致样本上报减少。

SRM 检查应该先于性能指标判断。实验平台每天输出分桶比例、配置命中率、activation event 触发率、上报成功率；这些基础检查不通过时，性能收益或退化都只能标成无效数据。Clippings 的数据评估章节强调上报组件和数据平台的准确性，放到性能实验里，SRM 就是最早暴露数据问题的信号之一。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

## [自动发现] 实验平台自身也要设护栏

实验平台、Remote Config、灰度平台都可能制造性能事故。一个错误配置可能让启动阶段多拉接口、打开高频日志、扩大图片预加载、调整线程池参数。平台自身要支持配置审计、灰度放量、紧急关闭和指标回看。

Firebase Remote Config 实验会在 variant 中修改参数；官方文档也提醒变体权重开始后不能修改，不均匀权重会增加数据收集时间。自建平台同样要记录参数快照和权重变化，否则归因时无法确认用户拿到的究竟是哪一版配置。[已验证: 官方文档, firebase.google.com/docs/ab-testing/abtest-config]

## 小结

性能 A/B Test 的价值在于把发布判断从“看起来变快”变成可复核的实验结论。实验开始前定义主指标、护栏指标、样本量和停止条件；CI 里用 Macrobenchmark 和固定设备拦住确定性回归；灰度阶段用线上分位值和分群指标判断真实用户风险；告警发生后，把版本、实验、场景、设备和 trace 证据一起交给排查人。

26.7 会继续处理发版质量门禁，把本节的回归检测结果放进发布前 checklist、灰度放量和回滚决策。

## 参考资料

- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]
- [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]
- [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]
- [已验证: 官方文档, developer.android.com/training/testing/instrumented-tests/performance]
- [已验证: 官方文档, developer.android.com/topic/performance/vitals]
- [已验证: 官方文档, firebase.google.com/docs/ab-testing/abtest-config]
