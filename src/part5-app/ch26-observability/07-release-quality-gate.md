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
related_chapters: ["26.6", "26.3", "15.10"]
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

# 发版质量门禁

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 发版前性能 Checklist
- 🔹 自动化性能测试集成
- 🔹 灰度发布与性能监控联动
- 🔹 版本回滚决策流程

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解发版质量门禁

发版质量门禁解决的是版本能不能继续往外放的问题。26.3 节负责把性能指标采上来，26.6 节负责实验设计和回归检测，本节把这些结果放进发布动作：发版前检查、候选包测试、灰度放量、暂停和回滚。

移动应用交付可以拆成开发、编译 CI、测试、灰度和发布几个阶段；数据验证平台应该放在灰度决策旁边，而不是等事故出现后再查。本节沿用这个结构，把判断对象收束到 Android 性能与稳定性。

## 发版前性能 Checklist

发版前 checklist 要写成可执行项，不要写成“关注启动、流畅性、稳定性”这种口号。每一项都要能回答三件事：检查哪个包、看哪个指标、失败后谁处理。

| 检查项 | 推荐口径 | 不通过动作 | 关联章节 |
| --- | --- | --- | --- |
| 启动 | 冷启动 TTID / TTFD P90、启动类型、入口来源、低端机分群 | 阻断 release candidate，回到 21.8 和 26.3 排查 | 21.8、26.3 |
| 渲染 | 核心页面慢帧率、冻帧率、`FrameTimingMetric` 结果、线上页面分群 | 降到小流量灰度或阻断发版 | 22.8、26.3 |
| 内存 | 前台 PSS P90、Java / Native Heap、OOM / LMKD 退出、图片缓存水位 | 限制放量范围，补采样现场 | 23.7、26.2 |
| 稳定性 | user-perceived crash rate、user-perceived ANR rate、Native crash、启动失败 | 阻断或回滚评估 | 20.6、26.2、26.4 |
| 上报质量 | 上传成功率、采样配置版本、事件丢弃数、延迟窗口 | 数据无效时暂停判断，不继续放量 | 26.3 |
| 包体与配置 | APK / AAB 体积、动态配置差异、实验参数快照 | 风险配置回退或降级灰度 | 25.6、26.6 |

Android Vitals 可以作为外部质量信号。官方文档说明 Play 会按日检查关键性能指标，并使用 28 天平均值评估 warning；core vitals 包括 user-perceived crash rate、user-perceived ANR rate、excessive partial wake locks 等。门禁报告要同时保留自建 APM 口径和 Vitals 口径，不能把内部 session 统计和 Play 的活跃用户口径混用。[已验证: 官方文档, developer.android.com/topic/performance/vitals]

checklist 的阈值要按版本阶段分层。release candidate 阶段可以用实验室基线拦确定性退化；1% / 5% 灰度阶段看真实用户分布和 crash / ANR；50% 之后更关注长尾分群和外部质量信号。阈值固定在平台配置里，人工豁免只能带过期时间和责任人。

## 自动化性能测试集成

自动化测试不负责覆盖所有真实设备，它负责让候选包带着证据进入灰度。候选包没有线下性能报告，就不应该直接进入生产灰度。

官方 benchmark CI 文档说明，benchmark 库会输出测量 JSON，并在设备目录里生成 profiling trace；Macrobenchmark 会按测量迭代输出 Perfetto trace。CI 要把这些产物按 commit、build id、设备、场景和测试名归档，后端才有条件做趋势对比。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]

Macrobenchmark 指标适合做候选包卡点：`StartupTimingMetric` 观察 TTID / TTFD，`FrameTimingMetric` 观察帧耗时和 overrun，`TraceSectionMetric` 观察业务自定义阶段，`PowerMetric` 在支持设备上观察能耗。TTFD 依赖 `reportFullyDrawn()`，在 Android 10（API 29）及以下可能不可用；`frameOverrunMs` 仅 Android 12（API 31）+ 可用，Android 10/11 门禁要为启动和帧指标准备替代口径。26.6 节已经展开回归检测，这里关注这些指标进入发版流程后的门禁位置。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]

这段配置只演示发布门禁的表达方式：每条规则都绑定场景、设备组、基线和动作。

```yaml
release_quality_gates:
  - id: startup_low_end
    stage: release_candidate
    metric: home_cold_start_tffd_p90_ms
    device_group: low_end_android_12_14
    baseline: last_green_release
    fail_if_relative_regression: 0.08
    fail_if_absolute_over_ms: 5000
    artifacts: [benchmark_json, perfetto_trace]
    action: block_release_candidate
  - id: rollout_jank_guard
    stage: staged_rollout_5_percent
    metric: feed_slow_frame_rate
    segment: low_end_or_90hz_devices
    min_samples: 500
    fail_if_relative_regression: 0.15
    action: pause_rollout
```

配置里的 `baseline` 不要只指向上一次构建。上一版可能已经退化，连续小幅退化会被逐次放过。发布门禁至少保留 `last_green_release`、`main_branch_7d_median` 和 `manual_pinned_baseline` 三类基线；报告里显示命中哪条基线。

自动化测试失败后，CI 不只给红绿结果。失败报告至少带上新包值、基线值、相对变化、绝对变化、设备温度、测试轮数、trace 文件路径和最近可疑 commit。这样 release owner 能判断是测试环境波动、真实退化，还是基线需要更新。

## 灰度发布与性能监控联动

灰度发布的价值在于把候选包放回真实用户分布里验证。灰度效率可以拆成测试效率和数据验证效率，这个拆法适合性能门禁：线下测试决定能不能开始灰度，线上数据决定能不能扩大灰度。

Google Play staged rollout 支持把更新先发布给一部分用户，然后逐步提高比例；该能力只适用于应用更新，不适用于首次发布。Play Console 文档也说明 staged rollout 可以按百分比放量，开发者可以在发现问题时停止扩大影响面。[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/6346149]

灰度监控要按批次组织，而不是只按 app version 聚合。同一个 version 可能经历 1%、5%、20%、50%、100% 多个阶段，每个阶段的用户结构都不同。门禁系统至少记录这些字段：

- `rollout_id`: 灰度批次，用来区分同一版本的不同放量阶段。
- `rollout_fraction`: 当前用户比例，和 Play / 自建渠道配置对账。
- `build_id`: 构建产物 ID，用来连接 CI 报告和线上指标。
- `experiment_snapshot`: Remote Config、A/B Test、服务端开关的参数快照。
- `metric_window`: 判断窗口，例如放量后 30 分钟、1 小时、24 小时。
- `segment`: 设备档位、Android 版本、国家 / 地区、渠道、刷新率。

灰度放量建议采用“证据齐了再升档”的状态机：

| 阶段 | 观察窗口 | 放量条件 | 失败动作 |
| --- | --- | --- | --- |
| internal / dogfood | 半天到 1 天 | 安装成功、启动路径无阻断、基础上报正常 | 修包，不进生产灰度 |
| 1% | 30-60 分钟看快速指标，24 小时看慢指标 | crash / ANR 无异常，启动和慢帧分群无明显退化 | 暂停灰度，拉证据包 |
| 5%-20% | 1-2 个核心流量周期 | 低端机、老系统、弱网分群通过 | 限制渠道或设备范围 |
| 50%-100% | 至少覆盖高峰时段 | Vitals / APM / 客服反馈没有同源异常 | halt rollout 或发修复包 |

灰度决策要区分 fast signals 和 slow signals。APM 上报、Crash/ANR 实时统计、启动/帧率分群是 fast signals——分钟到小时级可用，适合 1%-5% 灰度阶段判断。Android Vitals 使用 28 天滚动窗口计算 quality warning，属于 slow signals——它在 50%-100% 放量及全量后提供长期质量校验，但不适合在 1% 灰度 30 分钟内做决策。灰度门禁的策略：fast signals 决定能否升档（暂停/继续灰度），slow signals 用来检验"持续好几个月"的质量趋势、触发 Play warning 排查和商店可见性评估。门禁报告里把两类信号分开列出，不混在一个判断条件里。

APM 数据要和发布平台双向对账。发布平台告诉 APM 当前 version、rollout fraction、渠道和实验参数；APM 把核心指标、异常分群和上报质量回写到发布单。缺少这一步，release owner 会在几个看板之间人工对数，决策会变慢。

灰度指标还要保护数据质量。上报组件章节把采样、存储、上报、容灾拆成四块；发布门禁里要把上传成功率、事件丢弃数、配置命中率、采样版本纳入护栏。数据管道异常时，正确动作是暂停判断，而不是继续放量。

## 版本回滚决策流程

回滚决策要先区分三种动作：停止放量、回退配置、发布修复包。不是所有问题都适合立刻发新版；配置错误适合关开关，灰度包问题适合 halt，已全量问题要结合商店能力、修复包审核时间和动态配置能力处理。

Google Play Developer API 的 track release 模型包含 `draft`、`inProgress`、`halted`、`completed` 等状态，也包含 staged rollout 的 user fraction 和国家定向字段；官方 tracks 文档说明，可以把 production track 上 `inProgress` 的 staged release 更新为 `halted`。这给自动化发布平台提供了可操作接口，但执行前仍要走人工审批。[已验证: 官方文档, developers.google.com/android-publisher/api-ref/rest/v3/edits.tracks；developers.google.com/android-publisher/tracks]

回滚判断建议按影响面和可逆性排序：

| 信号 | 判断 | 推荐动作 |
| --- | --- | --- |
| 配置导致启动拉接口、日志暴涨、图片预加载扩大 | 可通过服务端配置恢复 | 立即回退配置，保留版本灰度 |
| 1% 灰度出现 crash / ANR 分群异常 | 影响面小，包体风险高 | halt / pause rollout，拉取样本和 trace |
| 低端机启动或慢帧明显退化 | 可通过设备 / 渠道限制降低影响 | 暂停升档，只对安全分群继续观察 |
| 已 100% 发布后发现 P0 稳定性问题 | 新用户和更新用户会继续拿到问题版本，已安装用户不会自动降级 | 可以 halt 已 100% rolled-out release，但前提是该 track 上存在可 serving 的上一个 completed release，且 fallback release 没有阻塞性政策问题；同时准备修复包、服务端降级和功能开关 |
| 监控数据异常但客服和 Vitals 未同步异常 | 可能是采样或上报故障 | 先修数据管道，不用问题指标触发回滚 |

Play Developer API 的 Tracks 文档同时覆盖两类 halt：`inProgress` staged rollout 可设置为 `halted`；已 `completed` 的 release 也可以设置为 `halted`，随后由同一 track 上之前已发布且未被 halt 的 completed release 作为 serving fallback。Play Console 帮助文档也说明 100% rolled-out release 可以 halt，但不能 halt track 的首个 release，也不能 fallback 到存在阻塞性政策问题的旧版本。halt 不会让已经安装问题版本的用户自动降级；这些用户仍要通过修复包、服务端降级、功能开关或应用内更新策略恢复。

版本回滚要有证据包。证据包至少包含：版本、build id、rollout fraction、异常指标、基线值、当前值、样本量、影响用户数、Top 分群、Top crash / ANR 组、trace / 日志样本、配置快照、已执行动作和下一步 owner。

回滚后还要做两件事。第一，确认指标回到基线：配置回退后看分钟级指标，修复包发布后看灰度批次指标，商店全量问题还要看 Vitals 的 28 天趋势。第二，把事故规则写回门禁：如果这次是低端机慢帧退化，下个版本的 release candidate 就必须加入同场景 benchmark 或线上分群护栏。

## 发布单要保存完整证据

发布单不只是审批记录，它是事故复盘和下一轮门禁的输入。每个发布单至少保存四类附件：CI benchmark 报告、灰度监控快照、配置 / 实验快照、人工审批与豁免记录。豁免记录必须有过期时间，不能永久压过门禁。

数据平台章节强调统一埋点规范和数据验证流程；放到发布门禁里，对应的是统一发布单字段。没有统一字段，后续很难回答“哪个版本在哪个灰度阶段开始退化、当时哪些开关打开、谁批准继续放量”。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]

## 小结

发版质量门禁把性能治理从“版本前看一眼指标”改成固定流程：release candidate 用自动化 benchmark 拦确定性退化；灰度阶段用 APM、Vitals、客服反馈和配置快照判断真实用户风险；异常发生后先暂停放量，再按配置回退、halt rollout、修复包三类动作处理。

这套机制的价值不在于让每次发布零风险，而在于让风险有证据、有 owner、有停止条件，并且能回写到下一轮门禁。

## 参考资料

- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 29.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 31.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]
- [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/benchmarking-in-ci]
- [已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]
- [已验证: 官方文档, developer.android.com/topic/performance/vitals]
- [已验证: 官方文档, support.google.com/googleplay/android-developer/answer/6346149]
- [已验证: 官方文档, developers.google.com/android-publisher/api-ref/rest/v3/edits.tracks]
- [已验证: 官方文档, developers.google.com/android-publisher/tracks]
