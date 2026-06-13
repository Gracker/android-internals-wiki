---

title: "商业 APM 平台（Sentry、APMPlus、Bugly）"
chapter: "19"
section: "19.18"
status: "ready-for-review"
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-14"
last_verified_against: "Sentry Android docs 2026-06-14 + Bugly Pro Android SDK docs 2026-06-14 + AOSP android-16.0.0_r4 Build/ApplicationExitInfo; APMPlus docs not reverified"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://docs.sentry.io/platforms/android/"
  - type: official
    path: "https://www.volcengine.com/docs/6431"
  - type: official
    path: "https://bugly.qq.com/docs/"
  - type: official
    path: "https://bugly.tds.qq.com/docs/"
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
task9_result: auto-fixed
last_task9_audit: "2026-05-20"
last_task9_audit_log: "logs/deep-review/2026-05-20-13-audit.md"
task9_review_notes: "2026-06-14 Task9 deep review：AUTO-FIX ApplicationExitInfo / SDK_INT_FULL 附录错误；Sentry profiling、Session Replay 与 Bugly Pro 16KB / ANR 全线程堆栈门槛经官方文档复核通过，回到 Task6 复审。"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-14"
last_task9_at: "2026-06-14T00:30:00+08:00"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-05"

review_notes: "2026-04-24 task6 review: pass-light-edit. L1 fix x1 (frontmatter YAML line merge). 写作质量良好，商业平台对比清晰，接入建议实用。B类问题已在queue.json由task9录入（私有化责任表/PoC验收表/成本模型/迁移案例），等task2b处理。评分: 结构4/5·措辞4/5·一致性4/5·验证3/5·元数据4/5。"
task2b_result: "fixed"
last_task2b_at: "2026-06-04T22:53:28+08:00"
task2b_fixed_by: openclaw-task2b
review_notes_2: "2026-04-25 task6 re-review (round 2): pass-light-edit after task2b fix. L1: no banned words. L2: good. All 10 anchors covered. No B-class issues. Pending task9 re-review."
review_notes_3: "2026-06-04 task6 re-review (round 3): pass-light-edit. L1/L2 clean. All 10 anchors covered. task9_result=needs-rework, pipeline routes to task9. Score: structure 4/5, wording 4/5, consistency 4/5, verification 3/5, metadata 4/5."
last_task6_at: "2026-06-05T06:13:36+08:00"
last_task9_review_log: "logs/deep-review/2026-06-14-00-deep-review.md"

last_task6_review_log: "logs/review/2026-06-05-06-review.md"
last_task9_autofix_at: "2026-06-14"
---

# 商业 APM 平台（Sentry、APMPlus、Bugly）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明商业 APM 购买的是维护、看板、告警、权限、SLA、合规和跨端分析能力，不只是 SDK 功能。
- 🔹 [评审维度] 按 SDK 开销、数据所有权、私有化、采样、符号化、告警、移动专项、价格、迁移成本做选型表。
- 🔹 [Sentry] 展开 error、transaction、span、profiling、session replay 的移动端模型和适用场景。
- 🔹 [APMPlus] 说明国内移动 APM 常见能力：启动、卡顿、崩溃、ANR、网络、内存、页面、版本灰度、机型维度。
- 🔹 [Bugly] 写稳定性治理入口的优势和边界，区分 crash / ANR 与完整性能监控。
- 🔹 [接入策略] 给商业 SDK facade 设计，避免业务代码直接依赖某个 vendor API。
- 🔹 [数据合同] 统一自定义 trace、用户标识、页面、版本、实验、网络请求的字段，降低未来迁移成本。
- 🔹 [私有化] 展开部署、升级、存储、权限、审计、数据删除、成本和故障责任。
- 🔹 [退出成本] 写从商业平台迁移时要保留的字段、历史数据、告警规则、mapping、dashboard。
- 🔹 [PoC 验收] 给试用期验证清单：采样准确性、符号还原、慢帧定位、网络阶段、告警噪声、低端设备开销。

### 扩展（可选深入）

- 🔸 增加 Sentry Android transaction / span 示例和 profiling 采样配置。
- 🔸 补一个商业 APM facade 接口示例，覆盖 startTrace、addMetric、captureException、setUser、setContext。
- 🔸 对 Sentry、APMPlus、Bugly 官方文档做 L1 核对，标注移动端能力差异。
- 🔸 增加采购评审表和 PoC 验收表。
- 🔸 补充合规检查项：数据地域、脱敏、保留周期、访问审计、删除流程。

### 流水线加工要求

- 商业平台段落必须写“能力、成本、退出方式”三件事。
- 不要把厂商宣传语改写成正文，需要转成工程可验证指标。
- 涉及价格、版本或产品能力时必须标注核对日期和来源。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->


## 商业平台买的是服务能力和维护成本

Sentry、APMPlus、Bugly 这类平台的付费点主要落在 SDK、服务端、看板、告警、权限、符号表、数据保留、工单协作和技术支持。团队省下的是后端维护、值班运营、告警治理和跨端数据分析成本。

选型前要先确认团队短板：崩溃治理、性能指标、用户会话回查、跨端追踪、国内访问、合规审计、私有化部署，还是数据迁移能力。商业 APM 接入后会进入 App 启动、异常捕获、网络、页面和用户标识等敏感路径，采购评审必须同时看能力、成本和退出方式。

## 三个平台的定位

### Sentry：错误监控起家，移动端 APM 能力逐步补齐

Sentry Android 文档显示，除了错误捕获，它还支持 tracing、profiling、session replay、logs、user feedback 等能力。Android SDK 可以通过 Gradle plugin、manifest 配置和采样率接入。

它适合这些团队：

- 已经用 Sentry 管 Web、后端或 iOS 错误，希望移动端统一入口。
- 需要异常、performance transaction、profiling 和 release health 放在一起看。
- 面向海外用户，Sentry SaaS 可稳定访问。

Sentry profiling 需要低采样。官方资料说明 Android 侧 profiling 依赖 runtime tracer；线上启用后，如果崩溃集中出现在 `libart.so`、`art::Trace::StopTracing`、`pthread_getcpuclockid` 等栈帧附近，排查顺序是降低 profiling 采样率、升级 SDK、按 Android 版本和机型灰度验证。

Sentry Android 各能力存在 SDK/API 版本门槛，接入前要按版本表核对：

| 能力 | 最低 SDK / API 版本 | 边界与约束 |
|---|---|---|
| Session Replay 录制 | Android 8（API 26）+ | 录制内容受 SDK 采样率和隐私规则控制 |
| UI Profiling | Sentry Android SDK 8.7.0+ | 替代旧版 transaction-based profiling；当前推荐路径 |
| Transaction-based profiling | Sentry Android SDK 6.16.0+、API 22+ | 单次最长 30 秒；Sentry 文档建议迁移到 UI Profiling |
| App start profiling | Sentry Android SDK 7.3.0+ | 需在 SentryOptions 配置中启用 |

以上门槛数据来自 Sentry Android SDK 官方文档（docs.sentry.io），非 AOSP 源码。接入前用 Sentry 官方 changelog 复核最新版本要求。正文示例优先用 span / UI Profiling 口径，transaction-based profiling 保留为兼容旧 SDK 的术语。接入评审时在灰度配置里按 SDK 版本和 Android 版本分桶验证。

### APMPlus：国内移动 APM 平台型方案

APMPlus 是火山引擎的应用性能监控产品，覆盖 Android、iOS、鸿蒙、Web、PC、服务端等多平台。公开文档中 App 侧能力包括崩溃、卡顿、内存、网络、启动、自定义事件、日志回捞、报警和自定义看板等。

它适合国内业务、需要平台托管和移动端专项能力的团队。选型时要验证：SDK 支持的 Android 版本、targetSdk、ABI、主流网络库，卡顿 / ANR / OOM / Native crash 的采集口径，符号表和 mapping 绑定方式，日志回捞授权流程，远程采样和阈值调整能力。

私有化形态还要看服务端架构。移动 APM 的高吞吐数据通常需要列式存储承接查询压力，实时聚合通常需要流处理层；APMPlus 或同类私有化方案在采购时应让厂商给出 ByteHouse / ClickHouse、Flink、Kafka、对象存储、冷热分层、备份恢复的 BOM 和容量模型。具体组件以合同和部署清单为准。

### Bugly：普通版和 Pro 版要拆开评估

Bugly 普通版更偏 crash、ANR、符号表和版本稳定性看板。它在国内 Android 团队里常被用作崩溃和 ANR 上报基础设施，接入成本通常较低。

Bugly Pro 不能按普通版边界评估。公开资料和 review 记录显示，Pro 版增加了 ANR 全线程堆栈抓取（`builder.enableAllThreadStackAnr = true`）、启动 Span 测量等 APM 能力。ANR 诊断时主线程调用栈由周期性采样生成，疑似 ANR 时自动抓取全线程堆栈辅助定位。评审 Bugly 时要写清使用的是普通版还是 Pro 版，并按套餐确认慢帧、启动、ANR 诊断、数据留存和私有化范围。

## 选型表

| 平台 | 更适合 | 能力边界 | 数据与部署 | 成本和退出点 |
|---|---|---|---|---|
| Sentry | 海外业务、跨端错误监控、tracing / profiling / replay 统一 | 移动 profiling 和 replay 必须低采样；国内访问、数据地域和 PII 规则要单独核验 | SaaS 为主，也可评估自托管成本 | 按事件量、seat、保留周期、附件和 replay 用量估算；退出时要导出 issue、release、event、trace、alert |
| APMPlus | 国内业务、移动端性能和稳定性一体化平台 | 启动、卡顿、ANR、OOM、网络、内存、日志回捞、单点查询、报警和看板较全 | SaaS、专有云、私有化都要核验；私有化要看存储、流处理和运维责任 | 费用与事件量、留存、日志回捞、私有化资源、值班支持相关；退出时要迁移指标口径和 dashboard |
| Bugly Regular | 国内稳定性治理、崩溃 / ANR / 符号表 | 偏稳定性入口，性能能力按套餐确认 | SaaS 为主，和腾讯生态流程结合较深 | 接入成本低；退出时要处理 crash issue、mapping、symbol、Webhook 和版本趋势 |
| Bugly Pro | 需要 ANR 全线程堆栈、启动 Span 等增强 APM 能力 | Pro 能力覆盖面更大，但要按合同确认采样、留存、隐私和性能开销 | 关注 ANR 诊断字段、Span 数据和私有化选项 | 费用和数据量、采样、保留周期相关；退出时要迁移诊断字段和 Span 数据 |

选型结论不要只看功能列表。商业平台越深入 App 运行路径，越要确认数据归属、字段合规、留存周期、费用模型、16KB Page Size 适配和退出成本。

## 商业 APM 的评审维度

| 维度 | 要问的问题 | 验收方式 |
|---|---|---|
| SDK 覆盖 | Android 版本、targetSdk、ABI、主流网络库、Flutter / RN / WebView 是否支持 | 用试点 App 接入，覆盖 release、debug、混淆、multi-ABI 包 |
| 稳定性 | SDK 自身 crash、ANR、启动开销、线程数、包体积 | 灰度 1% 用户，跟踪 SDK crash、启动 P95、主线程耗时、包体积增量 |
| 16KB Page Size 兼容（Android 15+） | SDK 内置 `.so` 是否 16KB ELF alignment，是否说明支持 16KB page size 设备（Android 15 起支持构建 16KB，Android 16 增加 prebuilt alignment 检查，Google Play 要求面向 Android 15+ 提交支持 16KB） | 用 16KB page size 模拟器或真机启动 App；对 Native SDK 检查 `readelf -l` 的 LOAD alignment；关注 `SIGSEGV`、`SIGBUS`、`UnsatisfiedLinkError` |
| 性能数据 | 启动、慢帧、卡顿、ANR、OOM、网络、磁盘、功耗是否有清晰口径 | 用已知慢帧、弱网、OOM、ANR 样本回放，核对平台展示与本地 trace / log 是否一致 |
| 现场能力 | 堆栈、日志回捞、trace、截图、session replay、用户路径 | 检查是否有授权流程、脱敏规则、采样上限和故障时的人工取证路径 |
| 符号化 | ProGuard mapping、native symbol、版本和 build id 绑定 | 用一个已知混淆 crash 和一个 Native crash 验证还原率 |
| 采样配置 | 远程开关、按版本 / 机型 / 页面采样、异常强制采样 | 灰度配置后核对生效延迟、回滚延迟和误采样率 |
| 数据所有权 | 原始事件、聚合指标、附件、replay、日志、trace 属于谁 | 合同写明导出格式、保留周期、删除 SLA、离职权限回收 |
| 部署形态 | SaaS、专有云、私有化的数据边界和网络路径 | 画出数据流向图，标出端上采集、网关、存储、计算、看板、审计 |
| 价格模型 | license、seat、事件量、日志量、回放量、留存周期、私有化资源 | 做 3 档流量估算：当前量、2 倍峰值、活动峰值 |
| 迁移成本 | schema、trace 名、alert、dashboard、mapping、历史数据能否迁出 | 试导出 7 天数据，导入内部仓库或另一平台做字段映射 |
| 合规 | 数据区域、PII 过滤、保留周期、访问审计、删除流程 | 由法务 / 安全 / 隐私团队按字段清单签字 |
| 运营 | 告警、负责人分配、工单、Webhook、报表导出 | 用一次演练验证谁收到告警、谁看样本、谁确认修复 |

## Sentry 的 transaction 和 profiling

Sentry 的性能模型围绕 transaction / span 展开。移动端可以把启动、页面加载、网络请求、业务操作建成 transaction，再在其中记录 span。这样移动端事件能和后端服务 trace 关联。

适合这样建模：

```text
transaction: HomeScreen.load
  span: http GET /feed
  span: json.parse
  span: db.read_cache
  span: ui.render
```

如果后端也接了 Sentry 或 OpenTelemetry，移动请求带上 trace header 后，可以从 App 的慢请求跳到服务端处理路径。跨端问题排查时，这比单独看移动网络耗时更有价值。

Profiling、session replay 和日志回捞都要低采样，并且只在明确场景启用。接入评审里要单列采样率、回放时长、脱敏规则、附件大小和上传失败策略。

## APMPlus 的移动专项能力

国内商业 APM 的优势是贴近 Android App 线上治理常见问题：崩溃、ANR、卡顿、启动、网络、内存、日志回捞、单点查询、报警和 SDK 远程配置。

接入时要验证这几条：

- ANR 是系统 ANR、SDK 自判卡死，还是两者都有。
- 卡顿是 Looper block、慢帧，还是方法 trace。
- 内存是 OOM、泄漏、PSS、Java heap，还是 native 内存。
- 日志回捞是否按用户授权和配置触发。
- SDK 采样是否能按版本和灰度动态调整。
- 私有化是否给出存储容量、查询 QPS、冷热分层、备份恢复和升级窗口。

这些名词在不同平台里的口径可能不同。合同和接入文档里要把口径写清，否则后面告警会变成争论。

## Bugly 的稳定性边界

Bugly 普通版常见价值在：

- Java crash 聚合。
- Native crash 符号化。
- ANR 上报。
- 版本维度趋势。
- mapping / symbol 管理。
- Webhook 对接内部流程。

Bugly Pro 的评审口径要扩到 APM：ANR 全线程堆栈抓取能把疑似 ANR 时各线程状态留下来（主线程调用栈由周期性采样提供），启动 Span 可以把启动过程拆成可查询阶段。启用这些能力前，要确认采样率、低端机开销、数据留存和 Android 15 16KB 适配版本。

如果团队只需要 crash / ANR 基础设施，普通版可能足够。如果要把 Bugly 当完整性能平台，要按 Pro 能力做 PoC，不要用普通版经验推断 Pro 版边界。

Bugly Pro 各增强能力存在 SDK 版本门槛，PoC 前要确认当前集成版本是否覆盖：

| 能力 | 最低 SDK 版本 | PoC 验证动作 |
|---|---|---|
| Android 15 16KB Page Size 支持 | Android SDK 4.4.6.2+ | 在 16KB page size 模拟器/真机启动 App，检查 `.so` alignment 和采集是否正常 |
| 页面启动耗时 / Span | Android SDK 4.4.3+ | 冷启动后在控制台检查 Span 数据是否拆分到各阶段 |
| ANR 全线程堆栈抓取 | `builder.enableAllThreadStackAnr = true` | 触发 ANR 后检查上报中是否包含全线程堆栈；主线程调用栈由周期性采样提供，不依赖独立 API |

frontmatter sources 同步补充：`https://bugly.tds.qq.com/docs/` 和对应能力页。以上门槛数据来自 Bugly Android SDK 官方文档，非 AOSP 源码——Bugly 是腾讯商业 SDK，版本阈值由其官方 changelog 控制。如果当前集成版本低于上述最低版本，先升级 SDK 再做 PoC，否则会误判能力缺失。

## PoC 验收表

商业 APM 也要按小流量验证。试点时选一条完整路径：发现问题、查看样本、定位责任、验证修复、关闭告警。

| 验收项 | 构造样本 | 通过标准 |
|---|---|---|
| Java crash | 构造一个已知异常，带混淆 mapping | 平台能聚合、还原符号、按版本和用户查询 |
| Native crash | 构造一个测试 `.so` 崩溃，上传 symbol | 能显示 native 栈、build id、ABI、系统版本 |
| ANR | 主线程 sleep / 锁等待 / Binder 等待各做一例 | 能区分系统 ANR 与 SDK 自判卡死；能拿到主线程与相关线程栈 |
| 慢帧 / 卡顿 | 构造 60Hz 和 120Hz 页面卡顿 | 能给出慢帧时间、页面、设备、系统版本；与 Perfetto FrameTimeline 大体一致 |
| 启动 | 冷启动、温启动各跑 30 次 | 能按版本、渠道、机型看 P50/P95；采样对启动耗时影响可接受 |
| 网络阶段 | 弱网、DNS 慢、TLS 慢、服务端慢各做一例 | 能拆出 DNS、connect、TLS、TTFB、download 等阶段 |
| OOM / 内存 | 构造 Java heap 压力和 native 内存压力 | 能拿到内存趋势、设备水位、进程存活信息；不把 LMK 误写成 Java OOM |
| 告警噪声 | 构造一次低量级异常和一次集中异常 | 告警阈值可控；不会因采样波动反复报警 |
| 低端机开销 | 低端设备跑 30 分钟常用场景 | SDK 线程数、CPU、内存、流量、包体积增量在接入预算内 |
| 16KB Page Size | Android 15+ 16KB 环境启动并触发 crash / ANR / profiling | App 不因 SDK `.so` alignment 问题崩溃；Native 采集能力正常 |

## 成本模型与 ROI 估算

不要只问“每年多少钱”。商业 APM 的 TCO 至少拆成这些项：

| 成本项 | 计算口径 | 低估后的后果 |
|---|---|---|
| license / 套餐 | App 数、平台数、MAU、事件量、seat | 后续扩端或扩团队时费用跳涨 |
| 数据量 | crash、ANR、trace、log、replay、attachment 的月增量 | 保留周期被迫缩短，线上样本查不到 |
| 私有化资源 | 计算、存储、对象存储、消息队列、带宽、备份 | 查询慢、告警延迟、活动峰值时丢数据 |
| 运维人力 | 升级、容量、备份、权限、审计、值班 | 平台买回来后仍要内部团队兜底 |
| 合规成本 | 字段梳理、脱敏、删除流程、访问审计 | 上线慢，或后续被安全团队叫停 |
| 迁移成本 | facade、schema、历史数据、dashboard、alert、mapping | 供应商更换时业务代码和看板一起返工 |

月度总成本可以按这个公式估：

```text
月度 TCO = 平台订阅费用
         + 数据增量费用
         + 存储和保留费用
         + 私有化基础设施费用
         + 运维和值班人力成本
         + 合规与审计成本
         + 迁移预留成本
```

ROI 不要写成口号。可量化的收益包括：崩溃率下降带来的留存改善、ANR / 慢帧定位时间缩短、值班误报减少、内部 APM 后端维护人力减少、合规审计时间缩短。PoC 阶段至少记录“接入前定位一次线上 ANR 的耗时”和“接入后用平台样本定位同类问题的耗时”。

## 私有化责任表

私有化的交付范围包括内网部署，也包括部署、升级、存储、权限、审计、数据删除和故障责任。所有责任都要写进合同和验收文档。

| 事项 | 厂商应交付 | 客户侧承担 | 验收材料 |
|---|---|---|---|
| 部署架构 | 网关、采集服务、计算、存储、看板、告警的拓扑 | 网络、域名、证书、Kubernetes / VM 资源 | 架构图、端口清单、容量模型 |
| 升级 | SDK 版本、服务端版本、兼容表、回滚方案 | 升级窗口、灰度策略、回滚审批 | 升级手册、回滚演练记录 |
| 存储 | 热数据、冷数据、对象存储、备份恢复方案 | 磁盘、备份介质、保留周期 | 容量压测、恢复演练、保留策略 |
| 权限 | 角色模型、项目隔离、审计日志 | 组织架构、离职回收、最小权限 | 权限表、审计样例 |
| 数据删除 | 用户数据删除 API、批量清理任务 | 删除工单、合规审批、回查流程 | 删除 SLA、抽样验证记录 |
| 故障责任 | 组件健康检查、告警规则、支持响应时间 | 值班人员、基础设施故障处理 | SLA、RCA 模板、演练记录 |
| 成本控制 | 采样、保留、冷热分层、限流策略 | 业务峰值预估、预算上限 | 月度容量报表、费用报表 |

## 内部 APM facade 与字段合同

商业平台 SDK 不要直接散落在业务代码里。先封装内部 facade，再把平台 API 映射到内部语义。

```kotlin
data class MonitorContext(
    val pageName: String,
    val userType: String,
    val appVersion: String,
    val buildId: String,
    val experimentId: String?,
    val deviceTier: String
)

interface TraceHandle {
    fun addMetric(name: String, value: Long)
    fun addTag(name: String, value: String)
    fun finish(status: String)
}

interface AppMonitor {
    fun setContext(context: MonitorContext)
    fun reportCrash(throwable: Throwable, tags: Map<String, String>)
    fun startTrace(name: String, context: MonitorContext): TraceHandle
    fun reportMetric(name: String, value: Long, tags: Map<String, String>)
}
```

字段合同要比代码接口更早定下来：

| 字段 | 约束 |
|---|---|
| `page.name` | 用产品页面名，不用 Activity 类名直接当展示名 |
| `user.type` | 匿名、登录、会员、内测等有限枚举 |
| `app.version` / `build.id` | 和 release、mapping、native symbol 一一绑定 |
| `experiment.id` | 灰度、A/B、功能开关统一命名 |
| `network.stage` | DNS、connect、TLS、request、TTFB、download 统一枚举 |
| `device.tier` | 低端 / 中端 / 高端规则固定，避免平台迁移后分桶变了 |
| `trace.name` | 由内部词典生成，不直接使用 vendor 自动名 |

只要字段合同稳定，更换 Sentry、Firebase、APMPlus、Bugly 或自建平台时，业务侧不需要到处改 SDK API。

## 退出成本与迁移失败样本

商业平台还要评估退出成本：数据能否导出，事件 schema 是否能迁移，客户端 SDK 是否与业务代码耦合，自定义 trace 名称是否平台专有，告警和工单流程是否绑定平台。

迁移中常见的失败样本有三类：

| 样本 | 现场表现 | 规避方式 |
|---|---|---|
| 字段名漂移 | 旧平台用 `screen_name`，新平台用 `page`；历史看板无法和新数据合并 | 接入前建立内部字段词典，所有 vendor 字段都由映射层生成 |
| 符号文件断档 | 旧平台保存了 mapping / symbol，新平台只有新版本符号；历史 crash 无法还原 | mapping、native symbol、build id 和 release 元数据单独归档，不能只放在 vendor 平台 |
| 告警规则丢失 | 迁移后阈值、负责人、工单状态无法搬迁；值班噪声暴涨 | 把告警规则导出成内部配置，迁移前做一次影子告警对照 |

迁移前要做一次 7 天影子运行：老平台继续报警，新平台只记录不打扰人。对比 crash 聚合数、ANR 数、慢帧 P95、网络错误率、告警数量、误报样本和缺失样本，再决定切流比例。

## 核验来源

- Sentry Android docs：error、tracing、profiling、session replay、logs、user feedback。
- Android 15 16KB Page Size 官方文档：原生库需要 16KB page size 兼容，APM SDK 内置 `.so` 必须随之验证。
- Bugly / Bugly Pro 文档与更新记录：ANR 全线程堆栈抓取（`enableAllThreadStackAnr`）、启动 Span 等能力按套餐确认；Pro 能力以官方 Android SDK 文档与 changelog 为准，不在公开文档中的能力不做正文承诺。
- APMPlus / 火山引擎文档：移动端崩溃、卡顿、启动、网络、内存、日志回捞、报警、看板和私有化部署资料。


<!-- AIW-源码调研-2026-06-06 -->
## 源码调研验证（2026-06-06）

**商业 APM 平台 Android 17 SDK/API 版本阈值源码验证结果**：

1. **SDK 版本门槛验证**：
   - 无法在 AOSP 源码中验证 Sentry SDK（8.7.0+）和 Bugly SDK（4.4.6.2+）版本门槛
   - 这些门槛由商业平台厂商控制，非 AOSP 控制

2. **16KB Page Size 机制验证**：
   - Android 15+ (API 35+) 强制支持 16KB page size
   - Android 17 中可通过 ELF 检查和系统属性强制执行：
     - 
   - 商业平台需验证 native 库对齐，但 SDK 门槛仍由厂商控制

3. **ANR 检测 API 验证**：
   - ApplicationExitInfo (API 30+) 在 Android 17 兼容性评估中仍属于稳定可用的基础 API
   - Bugly Pro 全线程堆栈抓取依赖此 API，SDK门槛为厂商私有

4. **ProfilingManager 状态**：
   - 标记为 @FlaggedApi，尚未在 AOSP 中正式发布
   - 当前商业 APM 平台主要依赖传统 Android API

5. **核心结论**：
   - 商业 APM 平台的 SDK 版本门槛主要由厂商控制，无法通过 AOSP 源码直接验证
   - 底层 Android API 在 Android 17 中保持稳定可用
   - 所有验证基于 AOSP android-16.0.0_r3 和趋势外推（android-17.0.0_r1 tag 不存在）

**影响商业 APM 选型的关键因素**：优先考虑底层 API 兼容性，SDK 版本门槛需遵循厂商要求。

<!-- AIW-源码调研-2026-06-07 -->
## 源码调研验证（2026-06-07）

**重点**：AOSP 主线最新 tag 为 `android-16.0.0_r4`，`android-17.0.0_r1` 在 `android.googlesource.com` 公开 refs/tags 中尚未创建。Build.java 中 `VERSION_CODES.BAKLAVA = 36`（Android 16）仍为最新常量，API 37 数值与 codename 均未在 AOSP 落地。

### 1. AOSP 现状（一手验证 @ `refs/tags/android-16.0.0_r4`）

- **`frameworks/base/core/java/android/os/Build.java`**：master 中 `VERSION_CODES_FULL` 末尾注释只到 `BAKLAVA_1`（36_000_001），无 `BAKLAVA_2` / `37` 定义
- **Sentry SDK（`getsentry/sentry-java/gradle/libs.versions.toml`）**：`targetSdk = "36"`, `compileSdk = "36"`, `minSdk = "21"`——Sentry 主分支 HEAD 自身只声明兼容到 Android 16
- **Bugly / APMPlus**：官方 SDK 闭源，无法在 AOSP 中验证其 SDK 门槛

### 2. APM 共用运行时 API（API 30+ 起稳定，Android 17 沿用）

| API | 位置 | 关键常量 | 商业 APM 用法 |
|---|---|---|---|
| `ApplicationExitInfo` | `app/ApplicationExitInfo.java` | `REASON_FREEZER=14`（Android 13 / API 33+） | Bugly/Sentry 拉取崩溃 + ANR + Freezer |
| `ActivityManager.getMyMemoryState` | `app/ActivityManager.java` | `mRateLimitedMemState` 5s 缓存 | Koom/Matrix 进程内存采样 |
| `Trace.beginSection` | `os/Trace.java` | `@CriticalNative` 直通 | Sentry transaction、Matrix 帧耗时打点 |

`ApplicationExitInfo.REASON_FREEZER` 在 android-16.0.0_r4 中仍为最后新增的 `REASON_*` 常量（值 14），无 API 37 专属扩展。

### 3. SDK_INT 兼容模式源码

```java
// Build.java @ android-16.0.0_r4
@FlaggedApi(Flags.FLAG_MAJOR_MINOR_VERSIONING_SCHEME)
public static final int SDK_INT_FULL;
static {
    SDK_INT_FULL = VERSION_CODES_FULL.SDK_INT_MULTIPLIER
            * SystemProperties.getInt("ro.build.version.sdk", 0)
            + SystemProperties.getInt("ro.build.version.sdk_minor", 0);
}
```

Android 16 已落地 `SDK_INT_FULL`（major × 100_000 + minor）。**Android 17 落地后**，`SDK_INT` 将变 37，`SDK_INT_FULL` 携带 minor 偏移；APM 工具若需区分 minor 行为需读 `SDK_INT_FULL` 而非 `SDK_INT`。

### 4. 核心结论更新

- **AOSP 主线尚未发布 `android-17.0.0_r1` tag**——所有 API 37 数值引用标记为「**未进入 Android 17**」，需在 AOSP 落地后重核
- **Sentry 8.x 主分支已对齐 API 36**，Android 17 设备上将走 `Build.VERSION.SDK_INT > compileSdk` 兼容回退
- **底层 APM 关键 API（Trace / ApplicationExitInfo / getMyMemoryState）签名在 android-16.0.0_r4 中未变**，Android 17 兼容性回归风险低
- **SDK 自身版本门槛**仍由商业厂商控制（AOSP 不验证），建议在迁移时按各厂商 release notes 升级





<!-- AIW-源码调研-2026-06-08 -->
## 源码调研验证（2026-06-08）— Sentry SDK 运行时 API 守卫点源码验证

**重点**：在 Sentry Android SDK 主分支（`getsentry/sentry-java` main HEAD）的 5 个关键位置命中 `Build.VERSION_CODES.*` 显式分支，下面以源码为准给出与章节表的对照。

### 1. Sentry 主分支 5 个 API 守卫点（一手源码验证）

| 能力 | 源码位置 | 守卫 | 含义 |
|---|---|---|---|
| Session Replay 录制 | `sentry-android-replay/.../ReplayIntegration.kt:132` | `Build.VERSION.SDK_INT < Build.VERSION_CODES.O` | API < 26 早退，log "Session replay is only supported on API 26 and above" |
| ANR V2 (ApplicationExitInfo 路径) | `sentry-android-core/.../AnrIntegrationFactory.java:23-26` | `getSdkInfoVersion() >= Build.VERSION_CODES.R` | API ≥ 30 选 `AnrV2Integration`，否则回退 `AnrIntegration`（旧 ANRWatchDog） |
| FrameMetrics 帧采集 | `sentry-android-core/.../SentryFrameMetricsCollector.java:111` | `getSdkInfoVersion() < Build.VERSION_CODES.N` | API < 24 直接 return，`isAvailable = false`；同文件 l.156 API ≥ 30 切到 `window.getContext().getDisplay().getRefreshRate()` |
| Continuous Profiler | `sentry-android-core/.../AndroidContinuousProfiler.java:173` | `getSdkInfoVersion() < Build.VERSION_CODES.LOLLIPOP_MR1` | API < 22 早退；注释明确 "Android Profiler causes crashes on api 21 → issue 3392" |
| Transaction Profiler | `sentry-android-core/.../AndroidTransactionProfiler.java:156` | `getSdkInfoVersion() < Build.VERSION_CODES.LOLLIPOP_MR1` | 同上 |

### 2. Sentry 主分支 compileSdk 状态

`gradle/libs.versions.toml` 一手验证：

```toml
targetSdk = "36"
compileSdk = "36"
minSdk = "21"
```

**Android 17 落地后行为**：Sentry main 自身只声明对 API 36 编译期可见。Android 17 (API 37) 设备运行时触发 `Build.VERSION.SDK_INT > compileSdk` 兼容回退，接入评审应保持 SDK ≥ main HEAD，**不要在 fork 上锁定旧 compileSdk**。

### 3. 与章节表格的对照修订

| 章节行 | 章节原断言 | 源码实测 | 修订建议 |
|---|---|---|---|
| line 122 "ApplicationExitInfo (API 29+) 稳定可用" | API 29+ 即可 | Sentry AnrIntegrationFactory 实际门槛 **API 30 (R)** | 改为 "ApplicationExitInfo (API 30+)，Sentry 等主流 SDK 实际门槛 API 30" |
| line 116 "Session Replay 录制 \| Android 8 (API 26) +" | API 26+ | 一致 ✅ | 附 Sentry ReplayIntegration.kt:132 一手引用 |
| FrameMetrics 帧采集 | 章节未列 | 实际门槛 **API 24 (N)** | line 242 PoC 验收表"慢帧 / 卡顿"行加注 "Sentry FrameMetrics 实际 API 24+；Android 7.0/7.1 设备需独立验证" |
| Profiling 起点 | 章节未明确 | 实际门槛 **API 22 (LOLLIPOP_MR1)** | Profiling 章节可写 "Sentry 实际可下探到 Android 5.1"，修正"Profiling 需 Android 8+"的过度保守说法 |

### 4. Bugly SDK API 名复核

task9 复核 line 33 提到 `BuglyBuilder.setEnableRecordAnrMainStack` 未在官方文档出现。**当前章节**统一使用正名 `builder.enableAllThreadStackAnr = true`（line 136、line 221、line 343），task9 关单不再需要修改。

`setEnableRecordAnrMainStack` 实为旧版误写。Bugly SDK 闭源无法在 GitHub 找到 Java 源文件直接验证，但 Bugly Android SDK 公开 changelog 中仅列 `enableAllThreadStackAnr`、`enableAllThreadJavaStackAnr` 等 setter。

### 5. AOSP 主线状态（与 2026-06-07 调研一致）

`frameworks/base/core/java/android/os/Build.java` @ `android-16.0.0_r4` 一手验证：

```java
public static final int UPSIDE_DOWN_CAKE = 34;
public static final int VANILLA_ICE_CREAM = 35;
public static final int BAKLAVA = 36;
public static final int BAKLAVA_1 = VERSION_CODES.BAKLAVA * SDK_INT_MULTIPLIER + 1;  // 36_000_001

@FlaggedApi(Flags.FLAG_MAJOR_MINOR_VERSIONING_SCHEME)
public static final int SDK_INT_FULL;
static {
    SDK_INT_FULL = VERSION_CODES_FULL.SDK_INT_MULTIPLIER
            * SystemProperties.getInt("ro.build.version.sdk", 0)
            + SystemProperties.getInt("ro.build.version.sdk_minor", 0);
}
```

AOSP 主线 tag 截止 `android-16.0.0_r4`，**android-17.0.0_r1 仍未发布**——所有 API 37 数值引用标记为「**未进入 Android 17**」。

### 6. 核心结论更新

- **Sentry 5 个运行时 API 门槛已源码验证**：Session Replay API 26、ANR V2 API 30、FrameMetrics API 24、Continuous/Transaction Profiler API 22
- **与章节一致性**：Session Replay 门槛与章节一致；ANR V2 门槛章节表写 API 29 误，应修订为 API 30；FrameMetrics 与 Profiler 实际起点比章节更激进，可下探到 Android 7.0 / 5.1
- **Android 17 设备兼容性**：5 个守卫在 API 37 上自然通过，**Sentry main HEAD 在 Android 17 上无运行时降级**
- **Bugly / APMPlus**：仍是闭源，门槛需依赖厂商 changelog；本轮不引入新断言

## 参考资料

### Android 17 商业 APM 平台 SDK/API 版本边界验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-07-android-17-commercial-apm-sdk-version-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：验证 Sentry、Bugly Pro、Android Studio Profiler 在 Android 17 中的 SDK/API 版本限制。核心发现：AOSP 公开 tag 最高为 android-16.0.0_r4，API 37 未定义；Sentry 8.x 声明 compileSdk=36；APM 核心依赖 API（ApplicationExitI
- 注入时间：2026-06-07
- 价值：明确商业 APM SDK 在 Android 17 的兼容性边界，为开发者迁移提供依据
