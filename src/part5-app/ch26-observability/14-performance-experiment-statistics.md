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

<!-- outline-start -->
## 要点

### 🔹 性能实验和灰度发布的边界
说明灰度发布回答“是否可以继续放量”，性能实验回答“某个方案是否造成可复核差异”。覆盖同质人群、同一时间窗、activation event 和 A/A 空转测试。

### 🔹 样本量不能只靠 baseline 与 MDE
整理 baseline、minimum detectable effect、alpha、power、历史方差、完整分布、allocation ratio 对样本量的影响，区分均值、比例和分位值三类检验对象。

### 🔹 P90/P99 的置信区间与尾部违约率
建立分位值实验的判定口径：bootstrap confidence interval、quantile confidence interval、tail violation rate、阈值超标率，避免把单个 P90 delta 当作稳定结论。

### 🔹 分群归因不能线性相加 P90
按设备档位、Android 版本、刷新率、启动类型、网络状态拆分分布；归因时看尾部样本来源、超阈值样本占比和分群权重，不用“样本量 × P90 delta”做结论。

### 🔹 SRM、采样和上报完整性
覆盖 Sample Ratio Mismatch、采样率切换、数据到达率、延迟上报、variant 崩溃导致的样本缺失，以及上报组件自监控字段。

### 🔹 CI 门禁与线上实验的证据对齐
把 Macrobenchmark 的 `FrameTimingMetric`、启动指标、固定设备基线和线上 P90/P99 / 慢帧率 / Crash / ANR 护栏指标放到同一张判定表里。

## 扩展

### 🔸 Sequential testing 与频繁看数风险
记录中途多次看数、提前停止、alpha spending、FDR 对发布决策的影响。

### 🔸 长尾分布的异常值处理
整理 winsorization、trimmed mean、分桶重算和异常样本回查的适用边界。

<!-- outline-end -->

## 为什么要单独拆出性能实验统计

26.6 节已经说明 A/B Test 和回归防护如何进入发布流程。26.14 只处理一个更窄的问题：当指标是启动耗时、帧耗时、慢帧率、功耗、内存水位这类性能数据时，实验结论怎样从“看起来涨了 / 降了”变成可复核判断。

性能数据和常规转化率不同。转化率通常是比例问题，启动和渲染指标却带有长尾分布；一批低端机的尾部样本，足够把 P90 / P99 推上去。实验报告只写“P90 上升 3%”不够，还要交代样本量、分桶、置信区间、尾部违约率和数据完整性。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]
[来源: intake/research-gaps.md#2026-05-15-26.6]

## 性能实验和灰度发布的边界

灰度发布回答“这个版本能不能继续放量”。性能实验回答“某个方案是否造成可复核差异”。两者都依赖分流和上报，但判断对象不同。

| 判断对象 | 典型问题 | 数据要求 | 决策动作 |
| --- | --- | --- | --- |
| 灰度发布 | 新版本 Crash、ANR、启动、卡顿、业务指标是否越过风险线 | 覆盖真实用户、监控实时、异常可回滚 | 暂停、回滚、继续放量 |
| 性能实验 | 新方案相对对照组是否改变某个性能指标 | 同质人群、同一时间窗、稳定分桶、明确主指标 | 采用、拒绝、延长实验 |
| CI 门禁 | 代码或候选包是否造成确定性退化 | 固定设备、固定场景、多轮采样、可重跑 trace | 阻断合入或阻断发版 |

Clippings 的发布章节把灰度和 A/B Test 分开：灰度用户常带选择偏差，适合验证版本风险，不适合直接裁定方案收益；A/B Test 要控制人群和时间窗，让差异尽量只来自实验变量。放到性能实验里，还要控制设备档位、Android 版本、刷新率、启动入口和网络状态。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]

Firebase A/B Testing 的 Remote Config 实验提供了可参照的约束：用户按 experiment ID 和 Firebase installation ID 进入 variant，进入后保持稳定分配；activation event 只影响结果计量，不影响客户端是否拿到实验参数；activation event 应发生在配置生效之后、配置影响行为之前。这个边界适合直接迁移到自建性能实验平台。[已验证: 官方文档, firebase.google.com/docs/ab-testing/ab-concepts；firebase.google.com/docs/ab-testing/abtest-config]

性能实验上线前要跑 A/A 或 A/A/B 空转。A/A 的两个组拿同一份配置，分桶比例、activation rate、上报成功率、主指标分布都应该接近；如果空转阶段已经出现稳定差异，正式实验的收益结论没有可信度。A/A 不只检查统计任务，也检查客户端分流、采样、埋点、延迟上报和服务端 join 逻辑。

## 样本量不能只靠 baseline 与 MDE

实验样本量不是 `baseline + MDE + alpha + power` 四个字段就能算完。性能指标要先确认检验对象：均值、比例、阈值违约率、P90 / P99 分位值，对应的数据需求不同。

| 检验对象 | 例子 | 样本量还依赖什么 | 不满足时的处理 |
| --- | --- | --- | --- |
| 均值 | 平均启动耗时、平均功耗、平均内存水位 | 历史方差或标准差、同用户多次测量相关性、分组比例 | 补历史分布或改用分桶 bootstrap |
| 比例 | 慢帧率、Crash-free users、阈值超标率 | baseline rate、目标变化幅度、事件发生率、用户 / session 去重口径 | 延长时间窗或合并低频分群 |
| 分位值 | TTFD P90、frameOverrunMs P99、RSS P95 | 完整样本分布、目标分位点附近样本密度、bootstrap 次数、关键分群最小样本 | 输出置信区间，不把单点 delta 写成结论 |

`minimum_detectable_effect` 也要按业务动作定义。P90 降低 1% 可能统计显著，但不一定值得承担发版风险；P99 上升 8% 可能样本少，却已经越过低端机护栏。样本量计算服务要同时保存“统计能检出多小变化”和“发布团队愿意为多大变化行动”两个值。

allocation ratio 会改变每个组的有效样本。50 / 50 分流在统计上效率高；10 / 90 更安全，但实验组样本少，得到同等置信度要更久。Firebase 文档也说明，不均匀 variant weight 会增加数据收集时间，且权重在实验开始后不能修改。[已验证: 官方文档, firebase.google.com/docs/ab-testing/abtest-config]

分群后的样本量要重新计算。全量样本 100 万不代表“低端机 + Android 11 + 60 Hz + 冷启动”也够用。性能实验报告至少列出主分群的有效用户数、有效 session 数、样本天数、采样率、上报到达率。低于阈值的分群只给趋势，不给采用或回滚建议。

推荐把实验登记表写成下面这组字段。它不是代码模板，而是避免漏字段的检查表。

```yaml
experiment_design:
  unit: firebase_installation_id_or_user_id
  primary_metric: home_cold_start_ttf_d_p90_ms
  guardrail_metrics:
    - crash_rate
    - anr_rate
    - slow_frame_rate
    - report_delivery_rate
  detectable_effect:
    type: relative
    value: 0.05
  alpha: 0.05
  power: 0.8
  allocation_ratio:
    baseline: 0.5
    variant: 0.5
  historical_distribution:
    source: last_14_days_same_scene
    fields: [p50, p90, p95, p99, stddev, sample_count]
  required_segments:
    - low_end_android_10_12
    - mid_end_90hz
    - high_end_android_15_plus
```

这张表把统计参数、历史分布和分群放在一起。缺少 `historical_distribution` 时，只能估算实验周期，不能承诺上线后几天一定能得出结论。

## P90/P99 的置信区间与尾部违约率

P90 / P99 是顺序统计量，不是可以线性相加的普通均值。一个 variant 的 P90 比 baseline 高 30 ms，只说明样本排序后第 90% 位置发生了变化；它没有说明尾部有多少用户变慢，也没有说明这个变化在重采样后是否稳定。

分位值实验至少给三类结果：

| 结果 | 计算方式 | 能回答的问题 |
| --- | --- | --- |
| 分位值单点 | 对每个 variant 的原始样本排序后取 P90 / P99 | 本次观测值是多少 |
| bootstrap CI | 对用户或 session 重采样，重复计算 P90 / P99，取 2.5% 和 97.5% 分位 | 如果重新抽一批样本，结论是否稳定 |
| tail violation rate | 统计超过业务阈值的样本占比，例如 TTFD > 5 s、frameOverrunMs > 0 ms | 有多少样本越过体验或门禁阈值 |

分位值置信区间也可用 order statistics 思路：样本排序后，用二项分布找到目标分位点的下界和上界秩。这个方法不假设分布形状，适合解释“P90 的可信区间落在哪两个排序样本之间”。工程上更常用 bootstrap，因为它容易按用户、设备分群和天级批次重采样。[引用: online.stat.psu.edu/stat415/book/export/html/835；library.virginia.edu/data/articles/distribution-free-confidence-intervals-percentiles]

bootstrap 要按实验单元重采样。实验单元是用户时，就按用户抽样，再带出该用户的 session；实验单元是安装 ID 时，就按安装 ID 抽样。直接按 event 抽样会让高活跃用户权重变大，分布会偏向重度用户。

下面的 SQL 只做口径示意：先算每组分位值和阈值违约率，bootstrap 建议在离线任务里按用户重采样。

```sql
WITH base AS (
  SELECT
    experiment_id,
    variant_id,
    user_id,
    device_tier,
    android_version,
    ttf_d_ms
  FROM perf_experiment_events
  WHERE scene_id = 'home_cold_start'
    AND event_date BETWEEN '2026-05-01' AND '2026-05-14'
    AND report_status = 'delivered'
)
SELECT
  experiment_id,
  variant_id,
  APPROX_QUANTILES(ttf_d_ms, 100)[OFFSET(90)] AS p90_ms,
  APPROX_QUANTILES(ttf_d_ms, 100)[OFFSET(99)] AS p99_ms,
  AVG(CASE WHEN ttf_d_ms > 5000 THEN 1 ELSE 0 END) AS tail_violation_rate,
  COUNT(DISTINCT user_id) AS users,
  COUNT(*) AS samples
FROM base
GROUP BY experiment_id, variant_id;
```

这段查询只能输出观测分布。发布报告还要附 bootstrap CI、关键分群、上报完整性和护栏指标，否则 P90 单点会被短期流量和采样波动放大。

## 分群归因不能线性相加 P90

均值和比例可以做贡献度拆分，分位值不能直接做 `样本量 × P90 delta`。P90 的位置由全量分布排序决定，分群 P90 的加权和无法还原全量 P90；某个小分群的 P90 大幅上升，也可能没有改变全量 P90 所在的样本位置。

归因算法要按指标类型分开：

| 指标类型 | 可用贡献口径 | 禁用口径 |
| --- | --- | --- |
| 均值 | `segment_users × mean_delta`、总耗时增量、总能耗增量 | 把均值贡献套到 P90 |
| 比例 | `segment_users × rate_delta`、新增违约样本数 | 忽略分群权重只看 rate delta |
| 分位值 | 原始样本重算 counterfactual 分布、尾部违约样本数、阈值以上超额均值、bootstrap 后分群移除对 P90 的影响 | `segment_users × p90_delta` |

性能实验里更可执行的做法是计算尾部来源：取全量 P90 / P99 阈值附近及以上的样本，按设备档位、Android 版本、刷新率、启动类型、网络状态统计占比。这样能回答“哪些分群构成了尾部”，而不是把不可加的分位值硬拆成贡献分。

counterfactual 分布适合做发布复盘。做法是保留 baseline 原始样本，把某个分群替换成 variant 样本，再重算全量 P90 / P99；或者反过来，保留 variant 样本，把某个异常分群替换回 baseline。每次只替换一个分群，就能估计该分群对全量分位值位置的影响。

这套归因还要回连 26.3 的采集字段。没有 `device_tier`、`android_version`、`refresh_rate`、`startup_type`、`network_type`、`scene_id`，后端只能对混合分布做猜测，无法把尾部样本派给具体工程团队。

## SRM、采样和上报完整性

SRM（Sample Ratio Mismatch）要先于性能指标检查。如果配置是 50 / 50，实际有效样本是 56 / 44，性能结论要先暂停。Microsoft Research 关于 SRM 的材料也强调，不能只肉眼看比例差异，要用卡方检验判断观察分布是否偏离配置分布。[引用: microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing]

SRM 的常见来源分成四类：

| 来源 | 例子 | 检查字段 |
| --- | --- | --- |
| 分流 | hash seed 变更、安装 ID 重置、variant 权重配置错误 | assigned_variant、assignment_time、bucket_hash |
| 激活 | activation event 放在配置生效前、某个入口没有触发激活 | activation_event、activated_at、config_activated_at |
| 采样 | variant 使用不同采样率、采样率下发延迟、PV / UV 口径混用 | sampling_rate、sampling_unit、sampling_policy_version |
| 上报 | variant 崩溃导致样本丢失、弱网上报延迟、后台进程未及时上传 | delivery_rate、late_arrival_rate、client_crash_before_report |

Clippings 的上报组件章节把采样、存储、上报、容灾拆成四个模块，并强调数据自监控。性能实验要把这套思想迁移到实验平台：分流量、激活量、采样量、写入量、成功上报量、进入分析表的量，都要能按 variant 对齐。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

推荐保留一张实验健康度表：

| 健康度项 | 合格口径 | 不合格动作 |
| --- | --- | --- |
| assignment ratio | 与配置比例偏差通过 SRM 检验 | 暂停性能结论，排查分流 |
| activation rate | baseline 与 variant 差异在预设范围内 | 检查 activation event 位置 |
| report delivery rate | variant 之间接近，且高于历史基线 | 检查上报组件、弱网、崩溃前丢失 |
| late arrival rate | 延迟上报不改变前一日结论 | 延迟出报告或补跑离线任务 |
| crash before report | variant 无异常升高 | 先按稳定性事故处理 |
| sampling policy version | 各 variant 同步切换 | 切换窗口数据剔除或重算 |

这些检查不通过时，报告应该写“实验数据无效”或“等待补数”，不要写“未发现性能差异”。数据缺失会把坏方案伪装成没问题。

## CI 门禁与线上实验的证据对齐

CI 门禁和线上实验要用同一套指标字典。CI 负责固定设备上的可重跑证据，线上实验负责真实用户分布；两边指标名、场景名、分群名不同，发布报告就很难判断同一个退化是否在两个环境里都存在。

Android Macrobenchmark 的 `FrameTimingMetric` 能输出帧相关指标。官方指标页说明 `frameOverrunMs` 表示帧错过 deadline 的时间；Macrobenchmark codelab 说明 `frameDurationCpuMs` 会输出 P50 / P90 / P95 / P99，Android 12（API 31）及以上还会返回 `frameOverrunMs`。因此 Android 10 / 11 的门禁不能依赖 overrun 口径，应退回 `frameDurationCpuMs`、slow frame rate、frozen frame rate 或自定义 trace section。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics；developer.android.com/codelabs/android-macrobenchmark-inspect]

CI 与线上证据建议按这张表对齐：

| 场景 | CI 指标 | 线上指标 | 判定方式 |
| --- | --- | --- | --- |
| 冷启动 | `StartupTimingMetric` 的 TTID / TTFD，多轮 P90 | 冷启动 TTFD P90 / P99、启动失败率 | CI 阻断确定性退化，线上检查设备分布 |
| 滚动 | `FrameTimingMetric` 的 `frameDurationCpuMs`；API 31+ 加 `frameOverrunMs` | 慢帧率、冻帧率、JankStats / FrameTimeline 摘要 | 同一 `scene_id` 下比较 CI trace 和线上尾部 |
| 业务阶段 | `TraceSectionMetric` 的 min / median / max、次数 | 同名 trace section 的 P90 / P99 | trace 名称一致时直接归因到阶段 |
| 稳定性护栏 | 测试过程 crash / ANR / timeout | Crash rate、ANR rate、ApplicationExitInfo | 稳定性越线时性能收益不采纳 |
| 上报健康 | 测试包上报成功率、日志完整性 | delivery rate、late arrival rate、SRM | 健康度不合格时实验结论暂停 |

门禁阈值要带版本和设备边界。`frameOverrunMs` 的 Android 12+ 口径、60 Hz / 90 Hz / 120 Hz 的帧预算、低端机和高端机的启动基线，都不能混成一个全项目数字。26.7 的发布门禁可以引用这张表，不再重复统计方法。

## [自动发现] Sequential testing 与频繁看数风险

性能实验常被发布节奏推着频繁看数：第一天看一次、第二天看一次、发现 p-value 低于 0.05 就提前结束。普通固定样本检验不允许这样用；每多看一次，都在增加误报概率。

处理方式有三种：

| 方式 | 适用场景 | 代价 |
| --- | --- | --- |
| 固定窗口 | 发版节奏稳定，能等到预设样本量 | 发现明显坏方案不够快 |
| sequential testing / alpha spending | 需要中途看数，但希望控制误报 | 统计实现更复杂，报告要展示已消耗 alpha |
| 护栏优先停止 | Crash、ANR、启动严重退化等安全问题 | 只用于止损，不把提前停止样本当收益证明 |

Spotify Engineering 关于 sequential testing 的文章提到，如果能预先限制中途分析次数，可用 Bonferroni 等多重比较修正控制假阳性；更灵活的做法是使用 alpha spending。这个方向适合实验平台实现，不适合临时手工改 p-value。[引用: engineering.atspotify.com/2023/03/choosing-sequential-testing-framework-comparisons-and-discussions]

多指标也会增加误报。一个实验同时看启动、滑动、内存、功耗、Crash、ANR、转化率，必然会有指标看起来“显著”。发布报告要区分主指标和护栏指标；多场景、多分群探索结果应标为探索性发现，进入下一轮实验或线下复现，不直接作为采用证据。

## [自动发现] 长尾分布的异常值处理

性能长尾里有两类样本：一种是产品和系统要面对的真实慢样本，例如低端机冷启动、弱网首屏、热限频后的滚动；另一种是数据错误或外部污染，例如时间戳错乱、重复上报、服务端 join 错误、压测用户混入。异常值处理先分类，再决定是否剔除。

| 方法 | 适用对象 | 风险 |
| --- | --- | --- |
| winsorization | 极少数采集错误已经确认，且要保留样本量 | 会压低真实尾部，不能用于用户体验护栏 |
| trimmed mean | 均值类指标被极端错误值污染 | 对 P90 / P99 结论帮助有限 |
| 分桶重算 | 异常集中在某设备、入口、网络或版本 | 分桶过细会造成样本不足 |
| 异常样本回查 | Top 慢样本要进入工程排查 | 成本高，但最能发现真实问题 |

P90 / P99 实验默认不剔除真实慢样本。除非能证明样本是采集错误或实验外污染，否则尾部就是用户体验的一部分。剔除规则要在实验开始前写入登记表，不能在看到结果后再决定删哪些样本。

## 小结

性能实验的判断单位不是单个 P90 delta，而是一组证据：分流是否健康、样本量是否足够、分位值置信区间是否稳定、尾部违约率是否越线、异常分群是否可解释、CI 和线上是否指向同一类退化。均值和比例可以做线性贡献拆分；P90 / P99 要回到原始样本、尾部样本和 counterfactual 分布。

26.6 可以继续讲 A/B Test 和回归防护流程；26.7 可以引用这里的判定表做发布门禁。统计口径集中在 26.14，后续修订时只维护一个地方。

## 参考资料

- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]
- [来源: intake/research-gaps.md#2026-05-15-26.6]
- [已验证: 官方文档, firebase.google.com/docs/ab-testing/ab-concepts]
- [已验证: 官方文档, firebase.google.com/docs/ab-testing/abtest-config]
- [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]
- [已验证: 官方文档, developer.android.com/codelabs/android-macrobenchmark-inspect]
- [引用: microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing]
- [引用: online.stat.psu.edu/stat415/book/export/html/835]
- [引用: library.virginia.edu/data/articles/distribution-free-confidence-intervals-percentiles]
- [引用: engineering.atspotify.com/2023/03/choosing-sequential-testing-framework-comparisons-and-discussions]
