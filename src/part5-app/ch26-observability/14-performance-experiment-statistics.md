---
title: "性能实验统计与分位值回归判定"
chapter: "26.14"
section: "26.14"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [observability, ab-test, performance-metrics, release-quality, macrobenchmark]
related_chapters: ["15.3", "15.6", "26.3", "26.6", "26.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "章节深挖/素材驱动"
gap_score: 16
material_count: 5
source_refs:
  - "intake/research-gaps.md#2026-05-15-26.6"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - "https://firebase.google.com/docs/ab-testing/abtest-config"
  - "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
drafted_date: "2026-05-18"
drafted_by: "openclaw-task2a"
last_verified: "2026-05-18"
last_verified_against: "Firebase A/B Testing docs + Android Macrobenchmark docs + Clippings structure references + research-gaps 2026-05-15"
confidence: medium
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: official
    path: "https://firebase.google.com/docs/ab-testing/ab-concepts"
  - type: official
    path: "https://firebase.google.com/docs/ab-testing/abtest-config"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/codelabs/android-macrobenchmark-inspect"
  - type: research-gap
    path: "intake/research-gaps.md#2026-05-15-26.6"
---

# 26.14 性能实验统计与分位值回归判定

性能实验面对的是长尾、重复测量和设备异质性。报告里出现一个 P90 delta 或一个 p-value，并不足以说明方案可发布。可信结论至少要同时满足：随机分配有效、指标定义固定、实验单元正确、数据到达完整、区间估计达到预设精度、护栏没有越界。

26.6 负责实验流程和回归防护，26.7 负责发布门禁。性能指标的统计对象与证据标准在这里单独讨论。Android 能力以上限 Android 17 / API 37 为准；Macrobenchmark 指标按当前 AndroidX 官方文档核对。

## 灰度、随机实验与 CI 各自回答什么

| 机制 | 主要问题 | 能否直接解释因果 | 典型动作 |
|---|---|---|---|
| 灰度发布 | 新版本是否出现严重风险，能否继续扩大覆盖 | 灰度人群、时间和渠道常有选择偏差，通常不能 | 暂停、回滚、继续观察或放量 |
| 随机性能实验 | 方案相对对照是否改变预先登记的性能指标 | 随机化、稳定分配和数据完整性成立时可以 | 采用、拒绝、判定无效或继续收集 |
| CI / 实验室基准 | 固定设备和场景能否复现确定性退化 | 对该受控环境有效，不能代表线上设备分布 | 阻断合入、定位 trace、修复后重跑 |

灰度也可以使用随机对照设计。只要同一时间窗内保留稳定的随机 control，并维持一致的 eligibility、配置和观测协议，它就兼具风险控制与实验属性。按渠道、地区、设备或报名顺序逐步放量时，版本差异会与人群差异混在一起，只适合作为发布风险证据。

### 分配、激活与暴露

实验需要区分三个时刻：

- assignment：实验单元被稳定分配到 variant。
- activation：实验参数已可用，且样本满足进入分析的预先条件。
- exposure：用户或 session 经过受参数影响的代码路径。

以 Firebase Remote Config A/B Testing 为例，variant assignment 使用 experiment ID 与 Firebase installation ID 的 hash，并在实验期间保持分配。activation event 只限制哪些用户进入结果计量，不影响实验参数下发。官方要求 activation event 位于配置激活之后、配置改变行为之前。

这个顺序很关键。若 activation 本身会被 treatment 影响，按 activation 过滤会选择一批 treatment 之后才形成的人群，随机化保护会被削弱。平台应尽量在 treatment 生效前定义 eligibility 和 activation；无法做到时，主分析保留 intention-to-treat 口径，exposure 分析只作为补充。

### A/A 空转验证

A/A 使用相同配置验证分配、埋点、上报和统计任务。它应检查：

- assignment ratio 是否符合配置；
- 各 variant 的 eligibility、activation、exposure 和 delivery 漏斗是否一致；
- 指标分布与置信区间覆盖是否符合预期；
- 设备、版本、渠道和时间分布是否平衡；
- 重复事件、迟到数据和 join 丢失是否偏向某个 variant。

A/A 出现显著差异并不自动证明平台有 bug，因为固定显著性水平下仍会有偶然误报。持续、跨指标或跨批次复现的差异，才需要沿数据漏斗定位。A/A 的验收规则也要在运行前登记。

## 先定义 estimand

样本量计算之前，团队要写清楚希望估计什么。性能实验至少有四个容易混淆的单位：

| 单位 | 例子 | 风险 |
|---|---|---|
| 随机化单元 | 用户、安装 ID、设备 | 统计推断必须尊重这个独立单位 |
| 观测单元 | 启动、页面 session、帧、请求 | 同一用户内往往相关，不能全部当独立样本 |
| 指标单元 | 每用户中位启动耗时、所有 session 的 P90、慢帧占比 | 不同聚合方式回答不同问题 |
| 决策人群 | 全量用户、冷启动用户、低端机用户 | 实验结论只适用于登记的人群 |

如果按用户分配 variant，却把每一帧当成独立样本，高活跃用户会获得更大权重，标准误也会偏小。常见处理有两种：

- 先把同一用户的事件聚合成用户级指标，再比较用户分布。
- 保留事件级 estimand，但使用按用户聚类的方差估计或 cluster bootstrap。

两种方法的业务含义不同。前者更接近“典型用户是否改善”，后者更接近“所有实际事件的总体分布是否改善”。实验登记必须选定一个作为主 estimand。

ratio metric 也要保留分子、分母和聚类单位。慢帧率、失败率和每用户功耗等指标不能只上报最终比值；否则难以处理不同用户的暴露量和不确定性。

## 样本量为何不只由 baseline 和 MDE 决定

样本量规划要同时考虑：

- baseline 的完整历史分布，而非只保存均值或 P90；
- minimum detectable effect（MDE）和最小业务可行动差异；
- alpha、power 和单侧/双侧假设；
- allocation ratio；
- 实验单元内的重复测量相关性；
- eligibility、activation、采样和上报造成的有效样本折损；
- 目标分群和多重比较计划；
- 指标在不同日期、版本和设备上的方差。

MDE 是实验希望以给定 power 检出的效应，不等于业务接受线。一次很小的变化可能统计可检出，却没有工程价值；一次尾部风险即使尚未达到主指标显著性，也可能触发安全护栏。登记表应分别保存 `detectable_effect`、`practical_effect` 和 `harm_limit`。

### 三类指标的规划差异

| 指标 | 主要分布信息 | 推荐规划方式 |
|---|---|---|
| 均值或用户级平均 | 方差、偏度、聚类相关性 | 解析近似或基于历史用户簇的模拟 |
| 比例或阈值违约率 | baseline rate、暴露量、聚类相关性 | 二项近似只适用于独立单位；复杂场景用模拟 |
| P90/P99 | 目标分位附近的样本密度、完整尾部分布、用户内相关性 | 使用历史原始样本注入候选效应，按随机化单元模拟实验 |

分位值附近的分布越平坦，少量样本顺序变化越容易造成较大的 quantile 波动。P99 还依赖极少的尾部观测，区间通常更宽。计划阶段应通过模拟检查区间宽度和检出率，不能因为全量事件数很大就认定 P99 有足够 power。

bootstrap replicate 数量只影响重采样近似的 Monte Carlo 误差，不会增加原始样本的信息量。它不能作为样本量公式中的用户数替代项。

不均匀 allocation 会减少较小 variant 的有效信息。Firebase 官方文档也提示，不均匀 variant weight 可能延长数据收集时间，并且实验开始后不能修改权重。自建平台如果中途改变分配，应开启新的实验版本，旧数据与新数据分开分析。

## P90/P99 应怎样报告

对于目标分位点 τ，主效应应定义为：

`Δτ = Qτ(variant) - Qτ(baseline)`

报告既包含两组的分位值，也包含 `Δτ` 的置信区间。分别查看 baseline CI 和 variant CI 是否重叠，不能替代对差值本身构造 CI。

### Cluster bootstrap

当用户或安装 ID 是随机化单元时，推荐按该单元重采样：

1. 在每个 variant 内有放回抽取用户或安装 ID。
2. 被抽中的单元携带其全部合格 session 或 event。
3. 对每次重采样计算两组 quantile 与 `Δτ`。
4. 使用预先登记的 bootstrap CI 方法输出区间。

直接按 event 重采样会破坏用户内相关结构，并让事件多的用户影响更大。若实验按 session 随机化，才可把 session 作为独立重采样单位。

简单 percentile bootstrap 易实现，但 quantile 的有限样本覆盖并非在所有尾部分布上都理想。平台应通过历史回放和模拟校准覆盖率；对近似独立同分布样本，也可以使用二项分布与 order statistics 构造分布无关的 quantile 区间。方法一旦登记，不能在看到结果后挑选最有利的 CI。

### 尾部违约率

P90/P99 之外，再登记一个有明确产品语义的阈值 `L`：

`tail_violation_rate = P(X > L)`

`L` 可以来自 Android vitals、团队 SLO 或场景预算，但必须带指标、场景、设备、刷新率和版本。报告要给出 baseline/variant 违约率、差值及置信区间。对渲染还可以补充阈值以上的 excess duration，区分“刚越线”和“严重超时”。

一个稳健的尾部报告至少包含：

| 证据 | 用途 |
|---|---|
| P50、目标主 quantile、辅助高 quantile | 观察整体位置和尾部形状 |
| 主 quantile 差值 CI | 判断效应方向与精度 |
| tail violation rate 差值 CI | 判断越过体验线的用户或事件比例 |
| 原始样本量、独立实验单元数、每单元事件分布 | 判断信息量与聚类 |
| 关键分群与每日分布 | 发现人群或时间漂移 |

若区间仍同时包含可接受改善和不可接受退化，结论应标为 inconclusive。单点 P99 方向不能覆盖不确定性。

## 分群 P90 为什么不能线性相加

设 variant `v` 的总体分布由互斥分群组成：

`Fv(x) = Σg wv,g × Fv,g(x)`

总体 quantile 是混合 CDF 的逆函数：

`Qv(τ) = Fv⁻¹(τ)`

因此，`Qv(τ)` 通常不等于 `Σg wv,g × Qv,g(τ)`。`样本量 × P90 delta` 也没有可加的统计含义。

分群归因应分成两个问题：

- composition effect：variant 的设备、版本、刷新率、启动类型或网络权重是否发生变化；
- within-segment effect：在相同分群内部，性能分布是否变化。

工程上可以选定一组 reference weights，把 baseline 和 variant 都重加权到同一分群构成，再从加权经验 CDF 重算 P90/P99。重加权后的差异更接近 within-segment effect；原始分布与重加权分布的差异提示 composition shift。

分群维度必须预先定义为互斥 strata，或使用能处理多维协变量的标准化方法。按“低端机”“Android 版本”“弱网”逐个替换时，这些人群会重叠，各次变化不能相加成总贡献。

尾部来源分析仍有直接工程价值：在总体主 quantile 附近及以上的样本中，统计各 strata 的人数、事件数、违约率和超额耗时。它回答“尾部主要由哪些人群构成”，不宣称这些分群 quantile 可以线性求和。

## SRM 和数据漏斗

SRM（Sample Ratio Mismatch）表示观察到的 assignment 数量与预期分配比例不符。检查应从原始 assignment count 开始，使用适合多项计数的检验，而不是只肉眼比较百分比。

assignment SRM 是实验有效性的前置条件。常见原因包括 hash 或 seed 变化、ID 重置、互斥层冲突、分配日志重复、eligibility 在分配后变化、客户端版本未同步。发生 SRM 时，主效果报告暂停；不能通过删样本把比例修回预期。

性能实验还要按 variant 追踪完整漏斗：

| 阶段 | 关键字段 | 典型偏差 |
|---|---|---|
| assigned | experiment version、assignment unit、variant、bucket | 分配不均、ID 漂移 |
| eligible | eligibility rule version、时间 | treatment 后过滤 |
| config available | fetch/activate 状态、配置版本 | 弱网或缓存差异 |
| exposed | scene、首个受影响事件 | 不同 variant 改变触达概率 |
| sampled | sampling unit、rate、policy version | variant 采样率不同 |
| persisted | 本地写入结果、队列状态 | 崩溃前未落盘、磁盘失败 |
| delivered | 到达时间、重试次数、payload version | 弱网迟到、重复上传 |
| analyzed | join 结果、去重版本、排除原因 | join 丢失、窗口截断 |

variant 导致 Crash、ANR 或进程被杀时，慢样本可能来不及上报。只分析 delivered performance event 会把最差的用户排除掉。应把 Crash/ANR、`ApplicationExitInfo`、delivery rate 和 missingness 作为护栏，并在可行时使用 assignment population 的 intention-to-treat 结果。

迟到数据要采用成熟窗口或水位线。日报可以显示 provisional 状态，但发布结论只能使用预先登记的数据成熟规则。采样策略切换、客户端 schema 升级和服务端重算都要产生新的 policy/version 字段。

## Sequential testing 与多重比较

固定样本检验假设分析时间和样本量在看结果前确定。每天查看同一 p-value，并在第一次越过阈值时停止，会提高 type-I error。

实验平台可选择三种设计：

| 设计 | 规则 | 适用场景 |
|---|---|---|
| fixed horizon | 到登记的样本量或时间窗后做一次主分析 | 发布节奏可等待固定窗口 |
| group sequential | 预先设置有限 interim look 与 alpha spending | 需要少量中期决策 |
| anytime-valid inference | 使用可持续监控的 p-value 或 confidence sequence | 平台支持连续监控并完成过覆盖校准 |

Crash、ANR、数据损坏或严重性能退化可以触发安全停止。这个动作是风险控制，不等于证明 treatment 有收益。提前停止后，报告要保留停止原因、当时样本和设计对应的区间估计。

主指标和护栏指标应在实验前登记。多个 confirmatory 指标需要控制 family-wise error；大量分群与场景探索可使用 FDR 或明确标为 exploratory。探索性发现进入复现实验，不直接升级为发布收益。

## 长尾异常值处理

性能尾部包含两种来源：

- 真实用户慢样本：低端机、热限频、弱网、冷缓存、资源竞争。
- 无效数据：负耗时、时钟基准混用、重复事件、错误 join、测试流量或损坏 payload。

无效规则要在实验揭盲前定义，并对各 variant 一致执行。删除记录时保存 reason、数量和分群；原始不可变数据保留在受控存储中。

winsorization 和 trimmed mean 会改变 estimand。它们可以作为均值类指标的 sensitivity analysis，不能替代原始 P90/P99 与 tail violation guardrail。真实慢样本属于用户体验，不因数值极端而删除。

推荐同时输出：

- 按数据有效性规则过滤后的主结果；
- 未做尾部截断的分位值与违约率；
- winsorized/trimmed 结果作为敏感性对照；
- Top 慢样本对应的 trace、设备和业务状态索引。

若结论只在某一种事后异常值规则下成立，应判为不稳定，并回到采集或复现实验。

## CI 与线上实验怎样对齐

Android Macrobenchmark 的当前指标边界如下：

- `StartupTimingMetric` 输出 `timeToInitialDisplayMs` 与 `timeToFullDisplayMs`，并汇总多次 iteration 的 min、median、max；官方建议以 median 评估典型启动。
- `FrameTimingMetric` 输出 `frameDurationCpuMs`；Android 12 / API 31+ 还输出 `frameOverrunMs`。两者按 P50/P90/P95/P99 汇总。
- `TraceSectionMetric` 对匹配 section 输出 min、median、max 和次数，并默认选择一次 measurement 中的第一个匹配实例。
- `PowerMetric` 测量的是测试期间的系统级功耗/能耗，并非 App 独占；设备支持范围和环境干扰要单独核对。

CI 的少量 iteration 不应套用线上大样本实验的 P90/P99 显著性语言。它用于受控、可重跑的相对回归：固定设备型号、Android 版本、刷新率、温度、构建类型、compilation mode、网络和数据状态，保留每轮原始值与 trace。

| 场景 | CI 证据 | 线上证据 | 联合判定 |
|---|---|---|---|
| 启动 | StartupTimingMetric median、每轮值、trace | 按 cold/warm/hot 和入口分桶的 TTID/TTFD 分布 | CI 复现阶段，线上确认人群与尾部 |
| 滚动/动画 | FrameTimingMetric quantiles、trace | 慢帧率、冻帧率、FrameTimeline/JankStats 摘要 | 使用相同 scene 与刷新率分桶 |
| 业务阶段 | TraceSectionMetric 与 Perfetto SQL | 同名业务阶段耗时分布 | 名称和起止语义逐版本一致 |
| 稳定性 | benchmark crash、ANR、timeout | Crash、ANR、ApplicationExitInfo | 稳定性护栏优先 |
| 数据健康 | 测试产物完整性 | SRM、delivery、late arrival、missingness | 数据无效时暂停效果判断 |

Android 8–11 没有 `frameOverrunMs`，应使用可用的 `frameDurationCpuMs`、自定义 trace section 或对应版本的线上帧指标。Android 17 / API 37 作为上限时，也要保留 AndroidX Benchmark 版本、设备 build 和指标 availability，避免把库升级造成的字段变化解释成性能变化。

## 实验登记与决策

性能实验登记至少包含：

| 分类 | 必填内容 |
|---|---|
| 假设 | treatment、作用路径、预期方向、风险 |
| 人群 | eligibility、assignment unit、exposure、排除规则 |
| 指标 | primary estimand、guardrails、单位、聚类单位、阈值版本 |
| 统计 | alpha、power、MDE、practical effect、harm limit、CI 方法 |
| 计划 | allocation、fixed/sequential 设计、interim 规则、成熟窗口 |
| 数据 | event schema、sampling policy、去重、迟到、missingness、SRM |
| 分群 | 预先声明的设备、Android 版本、刷新率、启动类型、网络 strata |
| 处置 | adopt、reject、inconclusive、invalid-data、emergency-stop 的条件 |

最终报告给出四类结论之一：

- adopt：主效应达到统计与业务标准，护栏安全，数据健康。
- reject/harm：收益不足或达到预设伤害条件。
- inconclusive：方向或精度不足，需要按登记规则继续收集或重做设计。
- invalid data：SRM、埋点、采样、上报或 join 破坏了可解释性。

“未显著”不等于“没有差异”，“P90 下降”也不等于“值得发布”。结论需要同时写 effect size、区间、业务阈值、护栏和数据健康状态。

## 参考资料

- [Firebase A/B Testing concepts](https://firebase.google.com/docs/ab-testing/ab-concepts)
- [Firebase Remote Config experiment configuration](https://firebase.google.com/docs/ab-testing/abtest-config)
- [Android Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Android Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [KDD 2019：Diagnosing Sample Ratio Mismatch in Online Controlled Experiments](https://www.kdd.org/kdd2019/accepted-papers/view/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonom)
- [Always Valid Inference: Bringing Sequential Analysis to A/B Testing](https://arxiv.org/abs/1512.04922)
- [Efron 1979：Bootstrap Methods](https://projecteuclid.org/journals/annals-of-statistics/volume-7/issue-1/Bootstrap-Methods--Another-Look-at-the-Jackknife/10.1214/aos/1176344552.full)
- [Hall & Martin 1989：Bootstrap confidence intervals for a quantile](https://doi.org/10.1016/0167-7152%2889%2990121-1)
- [Firpo, Fortin & Lemieux：Unconditional Quantile Regressions](https://www.nber.org/papers/t0339)
