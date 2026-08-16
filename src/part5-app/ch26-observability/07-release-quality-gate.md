---

title: "发版质量门禁"
chapter: "26.7"
section: "26.7"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "Current Android 17 migration/behavior-change docs, Android vitals and Macrobenchmark docs, and Google Play staged/full-rollout and Publisher API docs retrieved 2026-08-15"
confidence: high
sources:
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 29.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: legacy-reference-preserved
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/6346149"
  - type: official
    path: "https://developers.google.com/android-publisher/api-ref/rest/v3/edits.tracks"
  - type: official
    path: "https://developer.android.com/about/versions/17/migration"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/guide/app-compatibility"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/reference/kotlin/androidx/benchmark/macro/TraceSectionMetric"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/index.html"
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/16285429"
tags: [quality-gate, release, canary, rollback]
related_chapters: ["26.6", "26.3", "15.9"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_draft_polish_at: "2026-08-15T19:49:16+08:00"
last_draft_polish_run_id: "20260815-194916-gracker-writing-468"
last_review_finalize_at: "2026-08-15T19:49:16+08:00"
last_review_finalize_run_id: "20260815-194916-gracker-writing-468"
last_rework_at: "2026-08-15T19:49:16+08:00"
last_rework_run_id: "20260815-194916-gracker-writing-468"
---

# 26.7 发版质量门禁

## 门禁如何衔接发布阶段

发版质量门禁用一组可验证条件决定版本能否进入下一发布阶段。26.3 节负责采集性能指标，26.6 节负责实验设计和回归检测，本节把这些证据对应到发版前检查、候选包测试、灰度扩量、暂停和恢复动作。

本文覆盖 Android 10 到 Android 17（API 29–37），Android 17 源码标签为 `android-17.0.0_r1`。这里讨论的是应用和交付平台设计，不涉及某个 Linux 内核版本特有的实现，所以无需记录内核标签（kernel tag）。AOSP 标签用于核对平台实现；实际发布还要覆盖目标设备厂商（OEM）、系统构建指纹（build fingerprint，用于唯一标识设备上的系统构建）和季度更新。源码标签只能说明所核对的代码版本，不能代替真实设备验证。

## 发版前性能检查清单

发版前检查清单要能直接执行。每项至少说明被测产物、场景与设备、指标定义、比较基线、判定方法、失败动作和负责人。缺少任一项，数字变化便无法转换成明确的发布决定。

发布单应先冻结产物身份：`versionCode`（Android 用来判断版本新旧的整数）、Git 提交、AAB/APK 文件摘要、签名证书摘要、`compileSdk`、`targetSdk`、构建变体、R8（Android 的代码压缩、优化与混淆工具）映射文件、原生代码符号文件、Baseline Profile（预先提供给 ART 的热点代码配置）版本、动态特性模块版本和远程配置快照。测试报告与生产事件都引用同一个构建 ID，才能确认实验室和生产环境观察的是同一份代码与配置。

| 检查域 | 证据与口径 | 不通过动作 | 关联章节 |
| --- | --- | --- | --- |
| 启动 | 按启动类型、入口和设备群比较首次显示时间（TTID）；仅在正确调用 `reportFullyDrawn()` 的场景使用完全显示时间（TTFD） | 阻断候选包，结合 Perfetto Trace（系统跟踪文件）检查启动路径 | 21.8、26.3 |
| 渲染 | 核心交互的 `FrameTimingMetric` 分布、生产环境慢帧或冻帧指标，并按刷新率和页面分组（分群） | 阻断或缩小发布范围 | 22.8、26.3 |
| 内存 | Java 堆、原生堆、PSS（按比例分摊共享页后的物理内存）、RSS（包含共享页的驻留物理内存）、内存不足（OOM）与低内存退出；同时记录进程状态和设备内存档位 | 阻断高风险设备群，补充堆转储、Perfetto 或退出记录 | 23.7、26.2 |
| 稳定性 | 崩溃、应用无响应（ANR）、原生崩溃、启动失败和 `ApplicationExitInfo` 退出原因，按受影响用户数与事件数分别呈现 | 停止扩量，进入回滚评估 | 20.6、26.2、26.4、26.8 |
| 功耗 | 固定场景的实验室能耗与生产环境异常唤醒、后台任务证据；声明测量是否覆盖整台设备 | 对耗电路径限流或关闭配置 | 24.x、26.3 |
| 数据健康度 | 实验分组（assignment）、采样配置、事件生成、落盘、上传和查询延迟 | 将业务指标标为不可判定，暂停扩量 | 26.3、26.6 |
| 包体与配置 | AAB/APK 与动态特性大小、资源变化、远程参数和实验快照 | 回退配置或重新生成候选包 | 25.6、26.6 |

每个检查域都要在发布单中留下证据链接和判定结果；任一项失败时，直接执行表中动作并记录审批人。

### Android 17 要做两轮兼容性验证

Android 官方迁移指南把升级验证分成两条可以并行推进的路径：

- **运行兼容性**：把当前生产版本安装到 Android 17 设备，保持原有 `targetSdk`，验证所有应用都会受到的行为变化。这里发现的问题也会影响已经发布的包，通常应优先处理。
- **目标版本兼容性**：用 API 37 SDK 构建并把 `targetSdk` 升到 37，验证只对目标 API 37 及以上生效的变化。Android 17 的兼容性开关允许在可调试包上单独启用某项变化，便于隔离原因；发布结论仍要来自按目标 SDK 构建、配置接近生产版本的候选包。

测试清单应从官方“影响所有应用”和“以 Android 17 为目标版本”两份行为变化文档生成，并在每轮验证时更新。对目标 API 37 及以上的应用，新的无锁 `MessageQueue` 实现可能破坏依赖其私有字段或方法的反射代码；通过反射修改 `static final` 字段会抛出 `IllegalAccessException`，通过 JNI 修改会导致崩溃。证书透明度（Certificate Transparency，公开记录并校验网站证书签发情况的机制）默认启用；通过 `System.load()` 动态加载的原生库文件必须为只读。后台音频限制和大屏方向、宽高比及可调整大小规则也可能影响媒体或布局。应用可以只选择与自身代码路径相关的条目，但每个排除项都要留下理由。

兼容性开关适合逐项定位问题；用户设备运行的是多项行为变化同时生效的系统。正式候选包还要在 Android 17 的完整行为组合下运行主流程、后台流程、升级安装、数据迁移、权限拒绝、进程重建和大屏场景，并检查受限非 SDK 接口告警及第三方 SDK 的兼容性。

### 阈值必须来自本项目数据

门禁阈值应绑定指标版本、设备群、场景和发布阶段。相对退化阈值来自历史噪声与业务可接受的最小变化，绝对阈值来自体验服务等级目标（SLO）或稳定性预算，最小样本量取决于历史方差和希望识别出的变化幅度。其他项目的百分比、毫秒数或样本量没有这些前提，不能直接复制进配置。

Android vitals 是 Google Play 汇总的外部质量信号。Play 每天用最近 28 天的平均值检查关键指标。当前面向所有应用的 Core vitals（会影响应用在 Google Play 中曝光度的核心指标）包括用户感知崩溃率、用户感知 ANR 率和过度持有局部唤醒锁；过度耗电只作为表盘应用的 Core vital。发布报告要分别保存自建应用性能监控（APM）与 vitals 的分子、分母、统计窗口和设备范围。内部会话数与 Play 的用户或会话口径不同，不能放在同一个分母中计算。

## 自动化性能测试集成

自动化测试无法覆盖全部真实设备，它的职责是让候选包带着可复现证据进入灰度。风险较高的候选包如果没有实验室性能报告，应停在发布候选阶段。

Android 官方建议在物理设备上运行 Benchmark；模拟器结果会受宿主机和虚拟化环境影响，不宜代表用户体验。目标 APK 应接近生产构建：不可调试、允许性能剖析（profiling）、使用一致的 R8、资源压缩、签名后处理和 Baseline Profile。测试 APK 与目标 APK 分开构建，避免把 Benchmark 专用配置带进生产包。

Macrobenchmark 指标进入门禁前，要核对 API 可用范围和测量语义：

- `StartupTimingMetric.timeToInitialDisplayMs` 测量首帧出现所需时间。`timeToFullDisplayMs` 依赖 `reportFullyDrawn()`，在 Android 10 / API 29 及更早版本可能不可用；没有明确完整绘制点的场景不能用 TTFD 卡门禁。
- `FrameTimingMetric.frameDurationCpuMs` 是界面线程（UI Thread）与渲染线程（RenderThread）生成一帧所用的 CPU 时间；`frameOverrunMs` 只在 Android 12 / API 31 及以上可用，表示相对于帧截止时间的提前或超时量。两项指标不能共享阈值。
- `TraceSectionMetric` 仍标记为实验性 API，用来统计 Trace 中带名称的代码区段（section）。AndroidX Benchmark 1.3.0 及以上默认只统计目标包（`targetPackageOnly = true`），并以 `Mode.Sum` 汇总一次测量中所有同名 section 的耗时；若要看第一次或最长一次，必须显式选择 `Mode.First` 或 `Mode.Max`。业务阶段可能重复出现时，应先确定所需的聚合方式。
- `PowerMetric` 仍标记为实验性 API，测量的是系统级功率或能量，无法直接归因到单个应用；官方支持 Pixel 6、Pixel 6 Pro 及后续设备，测试时还需减少其他进程的干扰。

门禁配置无需嵌入一组脱离项目数据的示例数字。可移植的是这些字段及其约束：

| 字段 | 要回答的问题 |
| --- | --- |
| `artifact_id` / `commit` | 测的是哪一份目标包与测试包 |
| `scenario_id` / `setup_version` | 用户路径、账号和测试数据是否一致 |
| `metric_name` / `metric_version` | 指标怎样计算，当前 API 是否可用 |
| `device_id` / `build_fingerprint` | 设备、系统镜像和刷新率是否可比较 |
| `compilation_mode` / `profile_version` | 编译状态和 Baseline Profile 是否一致 |
| `baseline_id` | 比较对象是已知质量合格的固定版本、近期滚动趋势，还是人工固定基线 |
| `sample_count` / `effect_interval` | 测量次数、效应值和不确定区间分别是什么 |
| `decision` / `owner` / `waiver_expiry` | 失败后做什么，由谁处理，豁免何时失效 |

`baseline_id` 不宜永久指向前一轮构建。该构建可能已经退化，连续的小变化也可能被滚动比较忽略。已知质量合格的固定版本适合判断累计漂移，近期稳定趋势适合识别设备环境变化，人工固定基线适合重大重构；报告必须显示实际使用的基线及其更新时间。

Benchmark 库输出测量 JSON 和性能剖析 Trace；Macrobenchmark 会为每次测量迭代生成一份 Perfetto Trace。持续集成（CI）系统应按构建、设备、场景和测试名归档 JSON 与 Trace。失败报告除通过或不通过状态外，还应包含新包值、基线值、效应区间、测试轮数、热降频（设备过热后主动降速）等环境标记、失败迭代的 Trace 和候选提交。

拉取请求（PR）阶段适合运行编译校验和试运行（dry run），确认测试可以执行；固定物理设备上的重复测量更适合主干定时任务和候选包门禁。单次噪声较大的 Benchmark 不足以自动判定业务回归。门禁要区分测试基础设施失败、环境漂移和可重复的应用退化，并为每类失败定义不同动作。

## 灰度发布与性能监控联动

灰度发布（staged rollout）先把候选包提供给一部分符合条件的用户，再分阶段提高比例。实验室测试决定能否开始灰度，生产数据决定能否扩大覆盖，数据健康度决定当前窗口能否支持发布判断。

Google Play staged rollout 只适用于应用更新，首次发布不能使用。Play 会为每个新版本随机选择符合条件的用户；暂停后恢复仍影响同一组用户。暂停会阻止更多用户取得该版本，已经安装的用户仍停留在该版本。

staged rollout 不满足严格 A/B Test 的设计条件。Play 不向开发者提供由实验协议定义、可以稳定复现的旧版本对照组；版本覆盖还会受国家、设备资格、自动更新、安装时间和渠道影响。因此，版本间差异可以触发风险处置，但仅凭“灰度用户比旧版用户差”无法证明代码变化就是原因。因果判断仍需使用 26.6 节的受控实验或可复现回退证据。

灰度监控要按版本对象（release）和每次扩量批次记录，不能只按 `versionName` 聚合。门禁系统至少记录：

- `track`（生产、开放测试等发布轨道）、版本名称（release name）、`versionCode` 与发布事务的 edit ID。
- `rollout_id`、目标 `userFraction`、国家范围，以及开始、暂停、恢复和完成时间。
- build ID、产物摘要、签名和符号文件版本。
- Remote Config（远程配置）、实验、服务端开关和后端依赖版本快照。
- 指标窗口的事件时间、入库时间、数据已完整到达的最晚事件时间，以及查询时间。
- 发布前登记的设备、Android 版本、国家、渠道、刷新率、入口和新老用户类别。

`userFraction` 表示有资格接收该 staged release 的用户比例。它既不表示安装完成率，也不表示实时在线用户占比。发布平台要同时观察符合资格、已更新、已启动、产生指标和上传成功的数量；只用目标比例估算样本量会高估有效暴露。

发布门禁可以采用以下状态机；具体比例和观察时间由流量周期、事件发生率、审核时延与风险预算决定，不写成全项目通用常量。

| 状态 | 进入条件 | 继续条件 | 异常动作 |
| --- | --- | --- | --- |
| 内部验证 | 候选包与配置冻结，自动化门禁通过 | 安装、升级、主流程和诊断上报可用 | 重新构建，不进入生产 |
| 初始生产灰度 | 内部证据齐全，发布审批完成 | 快速稳定性指标与数据健康度可以判断，未发现高风险分群 | 暂停版本，保存诊断证据 |
| 扩量观察 | 前一阶段通过，样本覆盖预先登记的分群 | 指标区间在预算内，服务端与客户端依赖稳定 | 保持当前比例或限制国家、设备 |
| 完成发布 | 风险负责人接受剩余不确定性 | 全量后继续观察版本队列、vitals 与反馈 | 暂停已全量版本、降低配置风险或发布修复包 |

灰度决策要区分快速信号和慢速信号。自建 APM、崩溃与 ANR 事件流、启动与帧指标可以较早暴露风险，前提是数据延迟和样本覆盖达标。Android vitals 每天更新最近 28 天的平均值，适合观察长期质量与 Play 警告，无法为刚开始的小流量灰度提供即时扩量依据。

客服反馈和商店评论到达较慢，也存在选择偏差。它们可以帮助发现未知症状；“暂时没有投诉”不能抵消已经观测到的崩溃、ANR 或数据管道异常。

APM 与发布平台需要双向核对。发布平台向监控侧提供版本、目标比例、国家、配置和实验快照；监控侧把指标区间、异常分群、数据完整性和证据链接写回发布单。若上报成功率、事件丢弃、配置命中率或上报延迟异常，当前结论应标为“不可判定”，维持或暂停当前比例。缺失数据不能解释为质量正常。

## 版本回滚决策流程

Android 应用所说的“回滚”至少包含三种操作：暂停发布、回退服务端配置，以及发布更高 `versionCode` 的修复包。配置错误可以通过关闭开关处理；未完成的 staged rollout 可以暂停；已经安装到设备上的问题版本无法由 Play 自动降级，需要借助配置降级、服务端兼容或修复包恢复功能。

Google Play Developer API 的版本状态包括 `draft`（草稿）、`inProgress`（分阶段发布中）、`halted`（已暂停）和 `completed`（发布完成）。`userFraction` 只允许用于 `inProgress` 或 `halted`，取值必须严格大于 0 且小于 1。暂停进行中的版本时，把状态更新为 `halted` 并提交 edit（一次待提交的发布事务）；该版本随后不再提供给更多用户，已安装用户不受影响。

Google Play 也允许暂停已全量发布的版本，但内部测试轨道除外。当前版本不能是该轨道的首个版本，并且前一个已全量发布版本不能存在阻止重新提供的政策违规。暂停成功后，前一个版本会重新提供给新用户和其他符合条件、尚未安装问题版本的用户；已经安装问题版本的用户仍不会自动降级。发布平台执行前应读取轨道当前状态，显示将恢复提供的版本号；执行后再次读取状态确认结果。

按可逆性和剩余影响面选择动作：

| 信号 | 判断 | 推荐动作 |
| --- | --- | --- |
| 配置导致启动请求增加、日志量激增、图片预加载范围扩大 | 可通过服务端配置恢复 | 立即回退配置，保留版本灰度 |
| 初始灰度出现崩溃、ANR 或启动失败异常 | 影响范围仍受控，包体风险高 | 暂停 staged rollout，冻结证据并复现 |
| 特定设备群出现稳定退化 | 可通过发布资格或功能开关缩小范围 | 保持当前比例，限制受影响范围并准备修复 |
| 已全量版本出现严重稳定性问题 | 仍有用户可能更新到问题版本 | 核对可恢复提供的旧版本后暂停，同时降低配置风险并提交修复包 |
| 已安装用户持续受影响 | 暂停发布无法降级现有安装 | 保持服务端兼容、关闭高风险功能、提供应用内提示，并发布更高 `versionCode` |
| 数据完整性失败 | 当前质量结论不可用 | 暂停扩量，修复监控数据通路；已有明确安全信号仍按该信号处理 |

自动化可以生成建议、检查权限和准备 Play edit，但暂停、恢复和完成发布等动作会改变用户能够取得的版本，应保留明确审批、操作者、请求内容和 Play 返回结果。重试前先读取当前轨道，避免网络超时后重复修改未知状态。

回滚证据包至少包含：轨道、版本、`versionCode`、构建 ID、目标覆盖率与有效覆盖率、异常指标定义、基线与效应区间、数据完整性、受影响分群、按堆栈指纹归组的崩溃或 ANR 问题、Trace 或日志样本、配置快照、可恢复提供的旧版本、已执行动作和负责人。对于动态配置，还要保存旧值、新值、作用条件、配置版本和客户端生效时机。

处置后要验证恢复是否与动作时间一致。配置回退要检查配置拉取、激活与功能实际使用的转化步骤；修复包要检查新 `versionCode` 的有效覆盖和关键指标；Play 侧长期质量继续观察 vitals 的滚动窗口。恢复可以证明处置有效，根因仍要由代码、Trace 或受控实验确认。事故中发现的设备群、场景或数据缺口应加入下一版门禁。

## 发布单要保存完整证据

发布单既是审批记录，也是事故复盘和下一轮门禁的输入。每个发布单至少保存四类附件：CI Benchmark 报告、灰度监控快照、配置或实验快照、人工审批与豁免记录。豁免要写明规则、原因、证据、责任人、适用版本和失效时间；新版本不得自动继承。

发布单还应保存每次状态转换，不能只保留当前状态：谁在什么时间依据哪一版数据把版本从候选包转为灰度、扩大到哪个比例，以及何时暂停、恢复或完成。不可变的事件记录可以帮助团队复原退化出现的时间窗口、当时生效的开关和继续发布的依据。

## 小结

发版质量门禁把候选包、测试环境、指标定义、发布状态和处置动作绑定到同一份证据记录。候选包阶段使用接近生产配置的构建与物理设备识别可重复退化；Android 17 兼容性按“保留原 `targetSdk` 运行”和“目标 API 37”两轮验证；灰度阶段同时观察质量指标和数据健康度；异常发生后根据适用范围选择配置回退、暂停版本或发布修复包。

门禁不能消除发布风险。它应让剩余风险、数据不确定性、审批责任和停止条件可复核，并把本次事故暴露的场景与设备群加入下一次发布验证。

## 参考资料

- [AOSP Android 17：`android-17.0.0_r1` source manifest](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml)
- [迁移应用到 Android 17](https://developer.android.com/about/versions/17/migration)
- [Android 17：影响所有应用的行为变化](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android 17：target API 37+ 的行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 应用兼容性框架](https://developer.android.com/guide/app-compatibility)
- [在 CI 中运行 Android Benchmark](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Android vitals](https://developer.android.com/topic/performance/vitals)
- [Google Play staged rollout](https://support.google.com/googleplay/android-developer/answer/6346149)
- [Google Play Developer API：APKs 与 Tracks](https://developers.google.com/android-publisher/tracks)
- [Google Play Developer API：`edits.tracks`](https://developers.google.com/android-publisher/api-ref/rest/v3/edits.tracks)
- [Google Play：暂停已全量发布的版本](https://support.google.com/googleplay/android-developer/answer/16285429)
- [AndroidX `TraceSectionMetric` API 参考](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/TraceSectionMetric)
