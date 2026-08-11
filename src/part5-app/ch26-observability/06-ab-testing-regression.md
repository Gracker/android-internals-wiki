---

title: "A/B Test 与性能回归防护"
chapter: "26.6"
section: "26.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
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
  - type: official
    path: "https://firebase.google.com/docs/ab-testing/ab-concepts"
  - type: paper
    path: "https://www.kdd.org/kdd2019/accepted-papers/view/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments-a-taxonomy-and-rules-of-thumb-for-practitioners"
  - type: paper
    path: "https://arxiv.org/abs/1512.04922"
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
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
---

# 26.6 A/B Test 与性能回归防护

## 发布阶段需要回答的问题

性能治理进入发布阶段后，团队需要回答一组风险问题：新版本能否继续扩大灰度，某个配置是否适合放量，启动优化有没有伤到资源受限设备，页面改版是否提高了慢帧率。A/B Test 用随机对照估计方案的因果影响，回归防护则在代码合入、候选包和线上灰度阶段发现劣化。二者相关，但证据等级不同。

26.3 节已经讲过性能指标采集与上报，这里只处理实验设计、回归检测、CI/CD 门禁和劣化归因。重点是怎样把线下 benchmark、线上分流实验、灰度监控和发布决策放到同一套判断流程里。

平台结论上界为 Android 17 / API 37 / `android-17.0.0_r1`。实验统计与 CI 策略属于应用和数据平台设计；Android 版本主要影响 Macrobenchmark 指标是否可用，以及 `ApplicationExitInfo` 能提供哪些退出证据。相关判断不依赖内核专有实现，因此不附加 Android 17 kernel tag。

## 性能 A/B Test 的设计与统计方法

性能 A/B Test 不能只比较“新方案平均耗时”。启动、渲染、内存和功耗往往带有长尾，同一方案也可能对不同设备群产生相反影响。实验开始前要预先写清估计对象（estimand）、随机化单元、主指标、护栏指标、关键分群、最小可检测效应、样本量方法和停止规则。

| 设计项 | 推荐做法 | 风险 |
| --- | --- | --- |
| 随机化单元 | 按账号、安装或设备选择与产品语义一致的稳定单元；分析时保留分桶版本 | 按请求随机会让同一用户反复切换；更换 hash 或 salt 会造成重分桶 |
| 暴露定义 | 分别记录 assignment、配置 fetch、activate 和功能实际使用 | 只分析成功激活者会引入处理后选择偏差 |
| 主指标 | 每个决策指定一个主指标，并写清是每用户均值、事件分位值还是用户违约率 | 同名指标的聚合单元不同，估计的问题也不同 |
| 护栏指标 | 同时观察 Crash、ANR、内存、功耗、数据上报健康度和关键业务路径 | 性能收益可能伴随稳定性或业务损伤 |
| 分群维度 | 预先指定设备档位、Android 版本、刷新率、网络与入口等少量关键分群 | 事后遍历大量分群容易挑出偶然差异 |
| 停止规则 | 固定观察终点，或使用预注册的有效序贯方法 | 反复查看普通 p-value 并随时停止会抬高假阳性率 |

随机化单元和统计单元必须对齐。按用户分桶时，同一用户的多次启动、帧或会话是相关观测，不能当作互相独立的样本。常见处理是先在用户级聚合，再比较两组；如果必须保留事件级模型，就使用按随机化单元聚类的标准误或按该单元重采样的 bootstrap。否则，活跃用户贡献更多事件会让置信区间过窄。

Firebase A/B Testing 的 Remote Config 实验可以配置目标人群、基线与变体、权重和指标。官方文档有两个容易忽略的边界：只有触发 activation event 的目标用户会进入实验结果；实验开始后不能修改 variant 权重。自建平台应把“被分配”“成功获取”“成功激活”“使用功能”“成功上报”拆成漏斗。主分析优先遵循预先指定的 assignment 口径；按激活者补充分析时，要明确它可能受网络、启动成功率和变体自身崩溃影响。

指标类型决定估计方法：

- **连续指标**：例如用户级平均启动耗时。样本量需要历史方差、最小可检测效应、显著性水平、统计功效与分配比例；不能只填写基线均值。
- **二元指标**：例如“用户当天是否遇到 Crash”或“是否越过体验阈值”。使用用户级比例及其置信区间，不要把一次用户的多次事件当成多个独立用户。
- **比率指标**：例如慢帧数 / 总帧数。应明确采用 ratio of sums 还是 mean of user ratios，并使用与定义相符的 delta method、bootstrap 或聚类模型。
- **P90/P99**：分位值是非线性秩统计量，不能套用均值公式。可以按随机化单元 bootstrap 分位差，也可以把产品 SLO 转成用户级或会话级违约率；两种结果回答的问题不同。

最小可检测效应来自产品决策，而不是“统计上能测到的最小数字”。关键分群需要单独检查统计功效；样本不足时报告“方向与不确定区间”，不把短期波动写成收益。设备群过细时，可先用实验室 benchmark 排除确定性风险，再积累线上证据。

A/A Test 用于检查分桶、曝光、上报和统计任务是否校准。它不能证明平台永远无偏，也不要求每次指标差异都恰好为零；团队应观察长期假阳性率、置信区间覆盖率和 Sample Ratio Mismatch（SRM）。SRM 检查要覆盖全量与预注册关键分群，并沿 assignment → fetch → activation → metric → upload 逐层定位丢失。多主张、多分群或多次查看结果时，应预先选择多重比较或序贯控制方法，不能对每次查看都套用一次固定终点检验。

### 长尾指标的判定协议

P90/P99 的主效应应直接定义为 `Qτ(variant) - Qτ(baseline)`，并对差值构造区间；分别查看两组 quantile 区间是否重叠，不能替代差值区间。按用户或安装分桶时，cluster bootstrap 必须以随机化单元重采样，并让被抽中的单元携带其全部合格事件。直接按帧、启动或请求重采样会破坏单元内相关性，也会让高活跃用户获得额外权重。

尾部报告不只给一个 P99。还要预先登记体验阈值 `L`，报告 `P(X > L)` 的违约率、阈值以上的 excess duration、独立实验单元数和每单元事件分布。若区间同时包含可接受改善和不可接受退化，结论就是 inconclusive，不能用单点方向替代不确定性。

分群 quantile 也不能线性相加。总体分布是 `F(x) = Σg wgFg(x)`，总体 quantile 是混合 CDF 的逆函数，并不等于各群 quantile 的加权和。归因时要分别回答人群构成是否变化，以及相同分群内部的分布是否变化；需要标准化时，把两组重加权到同一参考构成后重新计算经验分布，而不是计算“样本量 × P90 delta”。

### 查看频率、多重比较与异常值

每天查看一次普通固定终点 p-value，并在第一次越线时停止，会抬高假阳性率。平台应在实验登记时选择 fixed horizon、带 alpha spending 的有限次 group sequential，或经过校准的 anytime-valid inference。Crash、ANR、数据损坏和严重性能伤害可以触发安全停止，但安全停止只说明需要止损，不自动证明方案有效。

多个确认性主张要控制 family-wise error；大量设备、场景和时间分群只能标为 exploratory，发现后进入复现实验。数据清洗也要在揭盲前登记：负耗时、时钟混用、重复事件和错误 join 可以判无效；低端机、热限频、冷缓存与弱网造成的真实慢样本属于用户体验，不能因为数值极端而删除。winsorization 或 trimmed mean 可以作为敏感性分析，不能替代原始分位值与违约率。

### 实验登记与决策结果

一份可审计的实验登记至少保存 treatment 与作用路径、eligibility、assignment unit、exposure、主 estimand、护栏、聚类单位、MDE、业务可行动差异、伤害线、CI 方法、分配比例、成熟窗口、SRM 与缺失数据规则、预注册分群、停止规则和数据 schema。最终结果只落到四类之一：`adopt`、`reject/harm`、`inconclusive`、`invalid-data`。“未显著”不等于没有差异，数据漏斗或 SRM 已损坏时也不能继续比较收益。

## 性能回归自动检测

性能回归检测分成两条线：实验室基线和线上分布。实验室基线负责在代码合入、候选包、发版前发现确定性退化；线上分布负责发现真实用户环境里的长尾问题。两条线不能互相替代。

Android 官方性能测试文档把 runtime performance 分成 local testing 和 field testing。field testing 观察真实用户环境，local testing 使用 benchmark 库在可控设备上复现用户流程。CI 应保存设备、系统镜像、构建配置、编译模式、测试数据与测量产物，缺少这些上下文时，趋势变化可能来自环境漂移。

回归检测适合采用三类规则组合：

| 规则 | 判定依据 | 适合发现的问题 | 处理动作 |
| --- | --- | --- | --- |
| 相对变化 | 相对固定 green baseline 的效应与不确定区间 | 稳定、可复现的中等幅度退化 | 重跑确认后阻断候选包或暂停灰度 |
| 产品阈值 | 由用户体验 SLO、历史分布和业务风险共同定义 | 已越过可接受体验范围的问题 | 进入发布风险评审 |
| 分群异常 | 预注册关键分群相对自身基线的变化 | 全量指标掩盖的设备或版本问题 | 限制受影响分群并派发诊断 |

Macrobenchmark 适合用于实验室基线，但基准设备应是物理设备，目标包应接近 release：不可调试、`profileable`、尽量开启与线上一致的优化。固定设备并不等于环境恒定，仍要记录电量、温控等待、后台干扰、系统 build fingerprint、CompilationMode 和 App 数据准备方式。官方明确不建议用模拟器数值代表用户设备。

指标还存在版本和语义边界：

- `StartupTimingMetric.timeToInitialDisplayMs` 测到首帧；`timeToFullDisplayMs` 依赖 App 调用 `reportFullyDrawn()`，在 Android 10 / API 29 及更早版本可能不可用。未正确上报 fully drawn 时，TTFD 门禁本身就没有业务意义。
- `FrameTimingMetric.frameDurationCpuMs` 表示 UI Thread 与 RenderThread 生产一帧的 CPU 时间；`frameOverrunMs` 还考虑帧 deadline，但只在 Android 12 / API 31 及以上可用。两者不能用同一阈值互换。
- `TraceSectionMetric` 仍是 experimental API，默认只读目标包的 section，并选择一次测量中匹配到的第一个实例。需要聚合多次业务阶段时，要先验证选择模式是否符合测试场景。
- `PowerMetric` 也是 experimental，测量系统级功率或能量，而非单 App 归因；官方支持范围是 Pixel 6、Pixel 6 Pro 及后续设备，测试时还要压低其他进程干扰。

门禁 schema 应保存 `metric_name`、`metric_available_api`、设备与系统指纹、场景、编译模式、基线来源、样本数、效应区间和处理动作。Benchmark 库会输出 JSON，并为每个 Macrobenchmark 测量迭代保存 Perfetto trace；CI 必须归档两类产物，聚合异常后仍能回到单次 Trace 查原因。

线上回归检测要沿用 26.3 节的分位值和采样字段。检测任务至少按 `metric_name`、`scene_id`、`app_version`、`experiment_id`、`variant_id`、`device_tier`、`android_version` 分桶。没有分桶的 P90 只代表混合分布，不能支持版本决策。

线上告警要同时处理不确定性和数据新鲜度。样本量不足时只记录风险；服务端故障、活动流量、配置切换和采样策略更新要标成外部事件。连续窗口并不天然独立，不能用“连续命中次数”冒充统计置信度。更稳的做法是固定观察窗口，报告效应区间与数据延迟，并把重复告警合并到同一事件。

Android vitals 可以作为外部校验源，但它和自建 APM 的安装来源、设备集合、聚合窗口、用户定义与数据延迟不同。发布报告应保留每个指标的分子、分母、窗口和过滤条件；不能把 Play 的每日活跃用户口径与内部 session 口径直接相减，也不能把尚未更新的 vitals 当成实时放量信号。

## CI/CD 集成性能卡点

CI/CD 里的性能卡点要分层，不能把所有 benchmark 都塞进每个 PR。每次提交都跑完整启动、滚动、功耗和弱网测试，队列会很快排满；完全不在 CI 里跑，回归又会拖到灰度阶段才暴露。

可以把门禁拆成三档：

| 阶段 | 运行内容 | 失败动作 | 产物 |
| --- | --- | --- | --- |
| PR 快检 | benchmark 编译、dry run、关键场景可执行性 | 测试基础设施失败时阻断合入 | 测试日志、环境信息 |
| 主干定时任务 | 固定物理设备上的启动、滚动与稳定 trace section，多轮测量 | 创建回归事件，达到团队风险线时限制主干 | JSON、每次迭代 Trace、趋势 |
| Release 候选 | 代表性设备档位、目标系统版本和核心用户路径 | 阻断发包或缩小灰度 | 候选包、设备覆盖表、门禁结论 |

官方 CI 文档里，Macrobenchmark 需要分别构建目标 APK 和测试 APK，再通过 instrumentation 运行；使用 Gradle 时，JSON 与 Trace 会自动复制到 host 的 additional output 目录。CI 系统要按 commit、branch、设备、系统镜像、benchmark name 和迭代编号归档，后端才能做同环境趋势对比。

门禁配置需要把“测什么、和谁比、证据够不够、命中后做什么”写成可审计字段：

| 字段组 | 必备内容 |
|---|---|
| 测量身份 | 场景、metric、API 可用范围、设备组、系统与构建指纹 |
| 比较基线 | pinned green release、滚动稳定基线，以及基线更新时间 |
| 判断证据 | 产品阈值、最小可检测效应、样本数、估计值与不确定区间 |
| 环境有效性 | 温控、低电量、后台干扰、失败迭代与异常值处理规则 |
| 处置 | 阻断、重跑、缩小灰度、责任模块与豁免流程 |

`baseline` 不能总指向上一轮测试。上一轮本身可能已退化，逐次比较会放过累积变化。报告可同时展示 pinned green release 与滚动稳定基线，并明确哪一个用于门禁。更新 pinned baseline 是发布决策，不能由测试任务在结果变差后自动完成。

性能门禁可以允许人工豁免，但测试环境异常应先标记为无效运行，不应伪装成业务豁免。有效豁免需记录批准人、证据、适用构建、到期条件、用户影响和补偿计划；到期后恢复门禁，不能形成永久白名单。

## 性能劣化的自动归因

自动归因用于把排查范围缩小到可验证的候选，不能仅凭相关性裁定根因。性能告警应该携带版本、实验、场景、设备分群、变更记录、trace section 与原始样本索引，排查人据此提出并验证假设。

归因输入建议固定成五类字段：

| 字段组 | 典型字段 | 用途 |
| --- | --- | --- |
| 发布字段 | app version、build id、git commit、渠道、灰度批次 | 判断是否由包体或代码变化引入 |
| 实验字段 | experiment id、variant id、参数快照、命中时间 | 判断是否由配置或功能开关引入 |
| 场景字段 | scene id、入口、启动类型、页面、业务阶段 | 判断是否集中在某条用户路径 |
| 设备字段 | 机型、SoC、内存档位、Android 版本、刷新率、国家 / 地区 | 判断是否是兼容性或性能档位问题 |
| 证据字段 | trace section、慢帧样本、日志摘要、网络错误码、Crash / ANR 组 | 支持工程团队复现和定位 |

自动归因可以给候选排序，但算法必须和指标类型匹配：

- **均值或比例**：先把两组标准化到同一设备与入口分布，再分解“分群内部变化”和“人群构成变化”。只计算样本量乘分群 delta 会把流量结构变化混入代码效应。
- **比率**：分子、分母分别做贡献分解，并保留 denominator shift。慢帧率上升可能来自慢帧数增加，也可能来自总帧数或会话长度变化。
- **P90/P99**：各分群分位值不能线性加权。可按固定体验阈值比较 violation count 与 excess distribution，也可移除某分群后重算全量分位值，作为排查优先级；“移除后变化”仍是描述性敏感度分析，不是因果效应。
- **时间线证据**：版本、配置和服务端变更与指标拐点相邻只说明相关。需要对照组、回滚/再现、代码路径或 Trace 证据才能提升根因置信度。

TraceSectionMetric 和业务 trace 名称要提前统一。线下 benchmark 里 `home.bind_data` 变慢，线上同名摘要也变慢，归因系统就能把告警指到首页数据绑定阶段；如果线下叫 `HomeBind`，线上叫 `feed_first_render`，后端只能靠人工猜。26.3 节已经建议自定义 Trace 和线上摘要使用同名阶段，这里直接复用该规则。

自动归因可以按固定流程输出候选：

1. 比对实验组和对照组，确认退化是否只出现在某个 variant。
2. 比对新版本和 pinned green release，确认退化是否随包体发布出现。
3. 按设备档位和 Android 版本排序贡献度，确认是否只影响特定设备群。
4. 拉取 Top 慢样本的 trace section、启动入口、网络错误和日志摘要。
5. 如果 Trace 指向业务阶段，派给业务模块；如果指向系统阶段，关联到 13.2、15.6、21.x、22.x、23.x 对应章节做线下复现。

这套流程不会消除人工分析，但能避免每次告警都从群里问“最近谁改了”。工程团队拿到的是可复核的候选清单，而不是单个结论。

## 样本比例失衡与实验污染

性能 A/B Test 要监控 SRM（Sample Ratio Mismatch，样本比例失衡）。将实际 assignment 数量与预设权重比较时，如果差异超出随机波动能够解释的范围，实验数据应暂停决策。常见原因包括分桶 hash 或 salt 变更、安装 ID 重置、目标条件实现不一致、埋点丢失，以及某个 variant 在 activation 或上报之前崩溃。

SRM 检查应先于性能指标判断。大样本且期望频数足够时可以使用卡方检验，小样本或稀疏分群则选择精确方法；检验阈值和查看频率也要预注册。实验平台应输出 assignment、fetch、activation、指标产生和上传成功率。assignment 已均衡而 activation 后失衡，说明问题发生在处理之后，此时只过滤“成功用户”会隐藏 Crash、ANR 或启动失败造成的损伤。

## 实验平台自身也要设护栏

实验平台、Remote Config、灰度平台都可能制造性能事故。一个错误配置可能让启动阶段多拉接口、打开高频日志、扩大图片预加载、调整线程池参数。平台自身要支持配置审计、灰度放量、紧急关闭和指标回看。

Firebase Remote Config 实验会在 variant 中修改参数；官方文档说明实验开始后不能修改变体权重，非均匀权重也会延长数据收集。自建平台同样要记录不可变的 experiment/version、参数 schema、权重、分桶 salt 与发布时间。紧急关闭应生成新的配置版本并保留旧快照，不能在数据库里覆盖历史值。

## 系统进程死亡证据：ApplicationExitInfo

Android 11 / API 30 起，App 可以用 `ActivityManager.getHistoricalProcessExitReasons()` 查询自己的近期进程退出记录。它补充了 App 可能来不及上报的 Crash、ANR、低内存和其他系统终止证据，但仍是一条有容量限制、可能缺字段的历史记录，不是完整审计日志。

三个查询参数要按公开 API 语义使用：

- `packageName == null` 匹配调用者 UID 下的包；跨 UID 查询需要 `DUMP`，普通第三方 App 不能依赖这条路径。
- `pid == 0` 表示不按 PID 过滤。PID 会复用，不应成为跨启动事件的唯一 ID。
- `maxNum == 0` 表示返回系统当前仍保存的全部匹配记录，不表示无限历史。结果按时间从新到旧排序。

`ApplicationExitInfo` 中适合进入实验报表的字段包括 processName、reason、status、importance、timestamp、description，以及可用时的 PSS、RSS、process state summary、ANR 信息和 trace。边界如下：

- PSS/RSS 是系统最近一次采样值，可能为 0，也不是进程死亡瞬间的精确内存。
- `description` 只供人阅读，格式不保证跨设备和版本稳定；聚合必须使用 reason、status 和结构化字段。
- `getTraceInputStream()` 可能返回 `null`。ANR 恢复后进程因其他原因退出，ANR trace 也可能附在后一次记录上；API 31 起 Native crash 会返回 protobuf tombstone。trace 位于独立的系统级环形缓冲区，可能被包括其他应用在内的新记录覆盖。
- `ActivityManager.setProcessStateSummary()` 最多接收 128 字节，系统还可能对高频调用限流。这里适合保存无敏感信息的 experiment ID、variant ID、配置版本和场景码，不适合塞入完整参数或用于恢复 UI。

Android 17 / API 37 增加 `ApplicationExitInfo.getAnrInfo()`：当 reason 为 `REASON_ANR` 时，`AnrInfo` 可以提供 ANR ID、ANR type、系统等待的 timeout 和 `isUserPerceptible()`。它能减少从不稳定 description 文本猜 ANR 类型的做法。

公开 API 只承诺近期记录保存在 ring buffer。AOSP `android-17.0.0_r1` 的 `config_app_exit_info_history_list_size` 默认值为每包 16 条，但它是可覆盖的 framework resource，不是 SDK 合约。Android 17 的 `AppExitInfoContainer` 使用 `ArrayList<ApplicationExitInfo>` 并按时间淘汰最旧记录，同一 PID 可以保留多条历史；旧文中“`SparseArray` 以 PID 为 key、同 PID 必然覆盖”的结论不再适用。framework 会持久化退出历史并在 system ready 后加载，但应用仍不能把跨重启保留和固定条数当作产品保证。

Android 17 的 `AppExitInfoTracker.preventExitInfoUpdate()` 会保护已有的 ANR、Java crash 和 Native crash 记录，后续显式 kill 信息不会覆盖这些记录，而是新增记录。这能减少同一进程相邻终止动作互相改写的情况，但应用仍应保留 actual reason，不要根据“某版本以后”把 `REASON_USER_REQUESTED` 自动改写成 Crash。

接入 A/B 平台时，建议按以下方式处理：

- 进程启动后在后台读取最近记录，用 processName、timestamp、reason、status、state summary 和 trace 摘要生成去重键；PID 只作为辅助字段。
- 保存已消费的稳定游标或摘要，避免每次启动重复上报。由于系统保留窗口有限，不能依赖低频轮询找回全部退出事件。
- reason、ANR type 和 variant 分桶聚合；description 只进入受控明细。PSS/RSS 为 0 时标记 unavailable，不做插值。
- 发现 trace 后立即在字节上限内复制到应用私有目录并关闭流。`REASON_CRASH_NATIVE` 在 API 31 及以上对应 protobuf tombstone；其他 reason 也可能附带较早的 ANR trace。保留实际 reason 与 trace 类型两个字段，不能把所有非空流统一当成文本或统一标为 ANR。
- `setProcessStateSummary()` 只在 variant 或关键场景变化时更新，并捕获限流异常。服务端 assignment 日志仍是实验归属的主记录，state summary 是进程死亡时的补充证据。
- Android 17 的 `AnrInfo` 可进入结构化维度；Android 11-16 继续使用 reason、trace 和业务现场，不能从 description 反解析出等价字段。

`ApplicationExitInfo` 能补足 App 上报中断后的部分进程退出信息，却不能证明某个 variant 导致退出。有效归因仍需检查 assignment 是否随机、各组退出记录的缺失机制是否一致，并结合对照组、代码变更、复现或 Trace。系统证据提高的是事件分类质量，不会自动把相关性变成因果结论。

## 小结

性能 A/B Test 要从随机化单元、暴露漏斗和估计对象开始设计。重复会话不能冒充独立样本，分位值不能按分群线性相加，SRM 与缺失数据要先于收益判断。CI 使用接近 release 的目标包和物理设备建立可复现基线，线上实验再覆盖真实设备与长尾分布。告警系统输出的是带证据强度的候选，因果结论仍需对照、复现或回滚验证。

26.7 会继续处理发版质量门禁，把回归检测结果放进发布前 checklist、灰度放量和回滚决策。

## 参考资料

- [在 CI 中运行 Android Benchmark](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [`FrameTimingMetric` API](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric)
- [Firebase Remote Config A/B Testing](https://firebase.google.com/docs/ab-testing/abtest-config)
- [Android vitals](https://developer.android.com/topic/performance/vitals)
- [`ActivityManager.getHistoricalProcessExitReasons()` 与 `setProcessStateSummary()`](https://developer.android.com/reference/android/app/ActivityManager)
- [`ApplicationExitInfo` API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ApplicationExitInfo.AnrInfo` API 37](https://developer.android.com/reference/android/app/ApplicationExitInfo.AnrInfo)
- [AOSP Android 17：`AppExitInfoTracker`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java)
- [AOSP Android 17：退出历史容量配置](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)
