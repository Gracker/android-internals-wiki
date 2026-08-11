---

title: "发版质量门禁"
chapter: "26.7"
section: "26.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-04"
last_verified_against: "Android Developers Macrobenchmark docs 2026-05-19 + Google Play rollout docs 2025-12/2026 Help + Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 1
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 29.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: clipping
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
tags: [quality-gate, release, canary, rollback]
related_chapters: ["26.6", "26.3", "15.9"]
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-04
task6_result: pass-light-edit
last_task6_at: "2026-06-04T06:08:46+08:00"
last_task6_review_log: "logs/review/2026-05-15-07-review.md"
task6_review_notes: "2026-05-15 Task6 07: needs-rework。完成 L1/L2 小修 2 处；沿用 Task9 风险信号标注 3 处并合并 queue，交 Task2B。"
task9_state: reviewed
task2b_state: fixed
task9_reviewed_date: "2026-06-04"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-04T03:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-04-03-deep-review.md"
task9_result: auto-fixed
task9_review_notes: "2026-06-04 Task9 auto-fix：补齐 Macrobenchmark TTFD/API 边界，并修正 Google Play 100% 全量 release 可 halt 的当前能力与限制；回到 Task6 复审。"
task2b_result: fixed
last_task2b_at: 2026-06-04T00:55:43+08:00
task2b_fixed_by: openclaw-task2b-main
task2b_fix_round: 2026-06-04-00
last_task9_autofix_at: "2026-06-04"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-28
---

# 26.7 发版质量门禁

## 门禁如何衔接发布阶段

发版质量门禁解决的是版本能否进入下一发布阶段。26.3 节负责采集性能指标，26.6 节负责实验设计和回归检测，这里把这些证据映射为发版前检查、候选包测试、灰度扩量、暂停和恢复动作。

平台上界为 Android 17 / API 37，源码标签为 `android-17.0.0_r1`。发布门禁属于应用和交付平台设计，相关结论不依赖 Linux 内核专有实现，因此不附加 kernel tag。AOSP 标签用于核对平台实现；实际发布还要覆盖目标 OEM、系统 build fingerprint 和季度更新，因为源码标签不能代替真实设备验证。

## 发版前性能 Checklist

发版前 checklist 要能直接执行。每项至少说明被测产物、场景与设备、指标定义、比较基线、判定方法、失败动作和负责人。缺少任一项，门禁失败后就容易陷入“数字变了，但不知道是否该停”的争论。

发布单应先冻结产物身份：`versionCode`、Git commit、AAB/APK 摘要、签名证书摘要、`compileSdk`、`targetSdk`、构建变体、R8 mapping、Native symbols、Baseline Profile 版本、动态特性模块版本和远程配置快照。测试报告与线上事件都引用同一个 build ID，才能确认线下和线上观察的是同一份代码与配置。

| 检查域 | 证据与口径 | 不通过动作 | 关联章节 |
| --- | --- | --- | --- |
| 启动 | 按启动类型、入口和设备群比较 TTID；仅在正确调用 `reportFullyDrawn()` 的场景使用 TTFD | 阻断候选包，带 Trace 回到启动链路排查 | 21.8、26.3 |
| 渲染 | 核心交互的 `FrameTimingMetric` 分布、线上慢帧或冻帧指标，并保留刷新率与页面分群 | 阻断或缩小发布范围 | 22.8、26.3 |
| 内存 | Java/Native Heap、PSS/RSS、OOM 与低内存退出；同时记录前后台状态和设备内存档位 | 阻断高风险设备群，补充 heap/Perfetto/退出证据 | 23.7、26.2 |
| 稳定性 | Crash、ANR、Native crash、启动失败和 `ApplicationExitInfo` 退出原因，按用户口径与事件口径分别呈现 | 停止升档，进入回滚评估 | 20.6、26.2、26.4、26.8 |
| 功耗 | 固定场景的实验室能耗与线上异常唤醒、后台任务证据；声明测量是否为系统级 | 对耗电路径限流或关闭配置 | 24.x、26.3 |
| 数据健康度 | assignment、采样配置、事件生成、落盘、上传和查询延迟 | 将业务指标标为不可判定，暂停升档 | 26.3、26.6 |
| 包体与配置 | AAB/APK 与动态特性大小、资源变化、远程参数和实验快照 | 回退配置或重新生成候选包 | 25.6、26.6 |

### Android 17 要做两轮兼容性验证

Android 官方迁移指南把升级验证分成两条路径：

- **运行兼容性**：把当前线上版本安装到 Android 17 设备，保持原有 `targetSdk`，验证所有应用都会受到的行为变化。这里发现的问题会影响已经发布的包，优先级通常高于 target 升级。
- **target 兼容性**：用 API 37 SDK 构建并把 `targetSdk` 升到 37，验证只对 target 37+ 生效的变化。Android 17 的兼容性开关可以在 debuggable 包上逐项启用 target 变化，便于定位；最终结论仍要来自按目标 SDK 构建的 release-like 包。

测试清单从官方“影响所有应用”和“target Android 17+”两份行为变化文档生成，不应手抄一份长期不更新的列表。Android 17 中，target 37+ 的 `MessageQueue` 实现变化、反射或 JNI 修改 `static final` 字段的限制、Certificate Transparency 默认启用、Native 动态代码加载文件只读要求、后台音频约束和大屏方向/可调整大小规则，都可能影响启动、崩溃、网络、媒体或布局门禁。应用只选择与自身代码路径相关的条目，但每个排除项也要留下理由。

兼容性开关适合做单变量定位，不代表用户设备会只启用一个变化。正式候选包还要在 Android 17 的完整行为组合上运行主流程、后台流程、升级安装、数据迁移、权限拒绝、进程重建和大屏场景，并检查非 SDK 接口告警及第三方 SDK。

### 阈值必须来自本项目数据

门禁阈值应绑定指标版本、设备群、场景和发布阶段。相对退化阈值来自历史噪声与业务最小可接受变化，绝对阈值来自体验 SLO 或稳定性预算，最小样本量来自历史方差和期望检测能力。不要把别的项目的百分比、毫秒数或样本量直接复制进配置。

Android vitals 是外部质量信号。Play 使用最近 28 天数据评估应用质量，并按日检查 28 天平均值；Core vitals 包括 user-perceived crash rate、user-perceived ANR rate、excessive battery usage 和 excessive partial wake locks。发布报告要保存自建 APM 与 vitals 各自的分子、分母、窗口和设备范围，不能混用内部 session 与 Play 用户口径。

## 自动化性能测试集成

自动化测试无法覆盖全部真实设备，它的职责是让候选包带着可复现证据进入灰度。风险较高的候选包如果没有线下性能报告，应停在发布候选阶段。

Android 官方建议在物理设备上运行 Benchmark；模拟器结果受宿主机和虚拟化环境影响，不适合代表用户体验。目标 APK 应接近线上构建：不可调试、允许 profiling、使用一致的 R8、资源压缩、签名后处理和 Baseline Profile。测试 APK 与目标 APK 分开构建，避免把 benchmark 配置带进生产包。

Macrobenchmark 指标进入门禁前，要核对 API 可用范围和测量语义：

- `StartupTimingMetric.timeToInitialDisplayMs` 测首帧。`timeToFullDisplayMs` 依赖 `reportFullyDrawn()`，在 Android 10 / API 29 及更早版本可能不可用；没有业务完整绘制点的场景不能拿 TTFD 做卡点。
- `FrameTimingMetric.frameDurationCpuMs` 是 UI Thread 与 RenderThread 生产一帧的 CPU 时间；`frameOverrunMs` 只在 Android 12 / API 31 及以上可用，还包含相对帧 deadline 的语义。两项指标不能共享阈值。
- `TraceSectionMetric` 是 experimental API，默认只观察目标包，并选择一次测量中匹配到的第一个 section。业务阶段可能重复出现时，要先验证选择模式。
- `PowerMetric` 是 experimental API，测量系统级功率或能量，不是单应用归因；官方支持 Pixel 6、Pixel 6 Pro 及后续设备，测试机还需限制其他进程干扰。

门禁配置不需要嵌入一组看似精确的示例数字。下面这些字段才是可移植的约束：

| 字段 | 要回答的问题 |
| --- | --- |
| `artifact_id` / `commit` | 测的是哪一份目标包与测试包 |
| `scenario_id` / `setup_version` | 用户路径、账号和测试数据是否一致 |
| `metric_name` / `metric_version` | 指标怎样计算，当前 API 是否可用 |
| `device_id` / `build_fingerprint` | 设备、系统镜像和刷新率是否可比较 |
| `compilation_mode` / `profile_version` | 编译状态和 Baseline Profile 是否一致 |
| `baseline_id` | 比较对象是固定 green release、滚动趋势还是人工固定基线 |
| `sample_count` / `effect_interval` | 测量次数、效应值和不确定区间是什么 |
| `decision` / `owner` / `waiver_expiry` | 失败后做什么，由谁处理，豁免何时失效 |

`baseline_id` 不宜永久指向上一轮构建。上一轮可能已经退化，连续的小变化会被滚动比较忽略。固定 green release 适合判断累计漂移，近期稳定趋势适合识别设备环境变化，人工固定基线适合重大重构；报告必须显示实际使用的基线及其更新时间。

Benchmark 库输出测量 JSON 和 profiling trace；Macrobenchmark 会为每个测量迭代生成一份 Perfetto trace。CI 应按 build、设备、场景和测试名归档 JSON 与 Trace。失败报告除了红绿状态，还应包含新包值、基线值、效应区间、测试轮数、thermal throttling 等环境标记、失败迭代 Trace 和候选 commit。

PR 阶段适合运行编译校验和 dry run，确认测试可以执行；固定物理设备上的重复测量更适合主干定时任务和候选包门禁。一次噪声较大的 benchmark 不能自动判定业务回归：门禁要区分测试基础设施失败、环境漂移和可重复的应用退化，并为每类失败定义不同动作。

## 灰度发布与性能监控联动

灰度发布把候选包放到真实设备和使用环境中验证。线下测试决定能否开始灰度，线上数据决定能否扩大覆盖，数据健康度决定当前窗口是否有资格作出判断。

Google Play staged rollout 只适用于应用更新，不适用于首次发布。Play 会为每次新 release 随机选择符合条件的用户；暂停后恢复会继续影响同一组用户。暂停只会阻止新增用户取得该版本，已经安装的用户仍停留在问题版本。

staged rollout 不是严格的 A/B Test。Play 没有向开发者提供一个由实验协议定义、可稳定复现的旧版本对照组；版本覆盖还会受国家、设备资格、自动更新、安装时间和渠道影响。因此，版本间差异可以触发风险处置，却不能只凭“灰度用户比旧版用户差”就宣称代码变化是原因。因果判断仍需使用 26.6 节的实验或可复现回退证据。

灰度监控要按 release 与每次扩量决策组织，不能只按 `versionName` 聚合。门禁系统至少记录：

- `track`、release name、`versionCode` 与发布 edit ID。
- `rollout_id`、目标 `userFraction`、国家范围、开始/暂停/恢复/完成时间。
- build ID、产物摘要、签名和符号文件版本。
- Remote Config、实验、服务端开关和后端依赖版本快照。
- 指标窗口的事件时间、入库时间、完整性水位与查询时间。
- 设备、Android 版本、国家、渠道、刷新率、入口和新老用户等预注册分群。

`userFraction` 是“有资格接收该 staged release 的用户比例”，不是安装完成率，也不是实时在线用户占比。发布平台要同时观察 eligible、已更新、已启动、产生指标和上传成功的数量；只用目标比例作为样本量会高估有效暴露。

可以把发布状态写成以下门禁状态机；具体比例和观察时间由流量周期、事件发生率、审核时延与风险预算决定，不写成全项目通用常量。

| 状态 | 进入条件 | 继续条件 | 异常动作 |
| --- | --- | --- | --- |
| 内部验证 | 候选包与配置冻结，自动化门禁通过 | 安装、升级、主流程和诊断上报可用 | 重新构建，不进入生产 |
| 初始生产灰度 | 内部证据齐全，发布审批完成 | 快速稳定性指标与数据健康度可判断，未发现高风险分群 | 暂停 release，保存现场 |
| 扩量观察 | 上一阶段通过，样本覆盖预注册分群 | 指标区间在预算内，服务端与客户端依赖稳定 | 保持当前比例或限制国家/设备 |
| 完成发布 | 风险 owner 接受剩余不确定性 | 全量后继续观察版本队列、vitals 与反馈 | halt completed release、配置降级或发修复包 |

灰度决策要区分快速信号和慢速信号。自建 APM、Crash/ANR 流、启动与帧指标可以较早暴露风险，但前提是数据延迟和样本覆盖达标。Android vitals 使用最近 28 天数据评估质量，并按日更新 28 天平均值，适合观察长期质量与 Play warning，不适合作为小流量刚启动后的即时放量依据。

客服反馈和商店评论也是慢且有选择偏差的信号。它们可以帮助发现未知症状，不能用“暂时没有投诉”抵消已观测到的 Crash、ANR 或数据管道异常。

APM 与发布平台需要双向对账。发布平台向监控侧提供 release、目标比例、国家、配置和实验快照；监控侧把指标区间、异常分群、数据完整性和证据链接写回发布单。若上报成功率、事件丢弃、配置命中或延迟水位异常，当前结论应标为“不可判定”，维持或暂停当前比例，不能把缺失数据解释为质量正常。

## 版本回滚决策流程

Android 应用的“回滚”不是单一操作，至少要区分暂停发布、回退服务端配置和发布更高 `versionCode` 的修复包。配置错误可以关闭开关；未完成的 staged rollout 可以 halt；已经安装到设备上的问题版本不能由 Play 自动降级，需要配置降级、服务端兼容或修复包恢复用户。

Google Play Developer API 的 release 状态包括 `draft`、`inProgress`、`halted` 和 `completed`。`userFraction` 只允许用于 `inProgress` 或 `halted`，取值必须严格大于 0 且小于 1。暂停进行中的 release 时，把状态更新为 `halted` 并提交 edit；该 release 随后不再提供给新用户，已安装用户不受影响。

已完成发布也可以 halt，但存在前提：同一 track 上必须有一个更早、已发布且未 halt 的 `completed` release 作为 serving fallback；如果 fallback 存在阻塞性政策问题，也不能执行。halt completed release 后，旧版本重新提供给尚未更新的用户，问题版本的现有用户仍不会自动降级。这个动作要在发布平台执行前读取 track 当前状态并显示 fallback versionCode，执行后再次读取状态确认结果。

按可逆性和剩余影响面选择动作：

| 信号 | 判断 | 推荐动作 |
| --- | --- | --- |
| 配置导致启动拉接口、日志暴涨、图片预加载扩大 | 可通过服务端配置恢复 | 立即回退配置，保留版本灰度 |
| 初始灰度出现 Crash / ANR 或启动失败异常 | 影响面仍受控，包体风险高 | halt staged rollout，冻结证据并复现 |
| 特定设备群出现稳定退化 | 可通过发布资格或功能开关缩小范围 | 保持当前比例，限制受影响范围并准备修复 |
| completed release 出现严重稳定性问题 | 仍有用户可能更新到问题版本 | 核对 serving fallback 后 halt，同时执行配置降级并提交修复包 |
| 已安装用户持续受影响 | halt 无法降级现有安装 | 服务端兼容、关闭高风险功能、应用内提示，并发布更高 versionCode |
| 数据完整性失败 | 当前质量结论不可用 | 暂停扩量，修复监控链路；已有明确安全信号仍按安全信号处理 |

自动化可以生成建议、检查权限和准备 Play edit，但 halt、恢复和 completed 等动作会改变外部用户的版本供给，应保留明确审批、操作者、请求内容和 Play 返回结果。重试前先读取当前 track，避免网络超时后重复修改未知状态。

回滚证据包至少包含：track、release、versionCode、build ID、目标与有效覆盖、异常指标定义、基线与效应区间、数据完整性、受影响分群、Crash/ANR 组、Trace 或日志样本、配置快照、serving fallback、已执行动作和 owner。对于动态配置，还要保存旧值、新值、作用条件、配置版本和客户端生效时机。

处置后要验证恢复是否与动作时间一致。配置回退看配置拉取、激活与功能实际使用漏斗；修复包看新 versionCode 的有效覆盖和关键指标；Play 侧长期质量继续观察 vitals 的滚动窗口。恢复只说明处置有效，根因还要由代码、Trace 或可控实验确认。事故中发现的设备群、场景或数据缺口应加入下一版门禁。

## 发布单要保存完整证据

发布单既是审批记录，也是事故复盘和下一轮门禁的输入。每个发布单至少保存四类附件：CI Benchmark 报告、灰度监控快照、配置或实验快照、人工审批与豁免记录。豁免要写明规则、原因、证据、责任人、适用版本和失效时间；新版本不得自动继承。

发布单还应保存每次状态转换，而非只保留当前状态：谁在什么时间依据哪一版数据把 release 从候选包变为灰度、从当前比例扩大、暂停、恢复或完成。保留不可变事件记录后，团队才能复原“退化从哪个窗口出现、当时哪些开关生效、为什么继续发布”。

## 小结

发版质量门禁把候选包、测试环境、指标定义、发布状态和处置动作绑定到同一份证据记录。候选包阶段使用 release-like 构建与物理设备识别可重复退化；Android 17 兼容性按“旧 target 运行”和“target API 37”两轮验证；灰度阶段同时观察质量指标和数据健康度；异常发生后按配置回退、halt release 和修复包的适用范围处置。

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
