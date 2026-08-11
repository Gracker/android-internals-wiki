---

title: "SmartPerfetto 与可复用 Trace 分析平台"
chapter: "13.17"
section: "13.17"
status: "finalized"
drafted_date: "2026-05-18"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)；Perfetto trace schema / stdlib 能力按工具版本降级"
last_verified: "2026-06-19"
last_verified_against: "SmartPerfetto main c4884fa73f98c71224e105304dc1c1ff98051de1; README; backend/src/types/multiTraceComparison.ts; backend/src/services/standardMetricBackfillService.ts; backend/src/services/enterpriseMigration.ts; backend/src/services/traceMetadataStore.ts; AIW 13.3/13.9/13.15/13.16/26.3/26.12/26.14"
confidence: medium
task6_review_notes: "2026-06-19 17 Task6 复审（Task9 auto-fix 后）：L1 修复 1 处 AI 模板结尾；L2 通过；L3 标注 🔧 企业版排查段风格不一致（bullet-only，缺叙述），不影响本轮通过；送 Task9 最终确认。"
tags: [perfetto, smartperfetto, trace-analysis, ai-assistant, sql-guardrail, observability]
related_chapters: ["13.3", "13.9", "13.13", "13.15", "13.16", "26.3", "26.12", "26.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "每日信息/素材驱动/章节深挖"
gap_score: 17
material_count: 4
pipeline_stage: "ready-to-publish"
task6_state: reviewed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-19"
task6_result: pass-light-edit
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: fixed
task2b_result: fixed
task9_reviewed_date: "2026-07-10"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-10T13:30:33+08:00"
last_task9_review_log: "logs/deep-review/2026-07-10-13-deep-review.md"
task9_review_notes: "2026-07-10 Task9 idle-audit: needs-rework。P0 0 / P1 1 / P2 0；复核 SmartPerfetto main 1508f99788bfcf18cc861e4bf4f8b472e84240c3，cutover 阶段 readAuthority=db，readTraceMetadataForContext() 在企业模式下按 trace_assets scope 读取且无 filesystem fallback；正文 L273-L290 把“DB 失败后回退文件系统”写成长期修复和监控目标，与当前企业迁移/权限边界冲突，已写入 queue.json。详见 logs/deep-review/2026-07-10-09-audit.md。 | 2026-05-28 11 Task9 auto-fix: 协调 SmartPerfetto main 标准对比指标列表与回填能力边界；回到 Task6 复审。 | 2026-05-28 12 Task9 复审：pass-tech-review。P0 0 / P1 0 / P2 0；自动晋升 finalized。 | 2026-06-19 15 Task9 闲时抽检：发现 SmartPerfetto main 运行时边界已从双运行时扩展为四类 runtime/provider 路径，写入 P1 回炉。 | 2026-06-19 16 Task9 deep-review: auto-fixed。P0 0 / P1 1（已修复）/ P2 0；标准回填能力按 SmartPerfetto main c4884fa73f98 明确为 startup.total_ms、scrolling.avg_fps、scrolling.frame_count、scrolling.jank_count、scrolling.jank_rate_pct，回到 Task6 复审。 | 2026-06-19 17 Task9 final review: pass-tech-review。P0 0 / P1 0 / P2 0；复核 16 点 SmartPerfetto 运行时/provider 边界与标准回填键 auto-fix、Task6 复审结果；queue 无 pending，自动晋升 finalized。 | 2026-07-10 Task9 回流复审: pass-tech-review。P0 0 / P1 0 / P2 0；复核 SmartPerfetto main 609ac843c268f53a6e93c2061d3c1dde29ce3e91 的 runtime/provider、标准指标回填与企业 cutover 读路径，正文已一致；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task2b_at: 2026-07-10T10:50:00+08:00
task2b_fixed_by: openclaw-task2b
last_task2b_lite_at: 2026-06-19
last_task6_at: "2026-07-10T12:20:00+08:00"
last_task6_review_log: "logs/review/2026-06-19-17-review.md"
last_task9_audit: "2026-07-10"
last_task6_audit: "2026-07-01"
last_task9_audit_log: "logs/deep-review/2026-07-10-09-audit.md"
sources:
  - type: blog
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/技术文章/RSS/rss-tech/2026-05-18_RSS_886623bf54.md"
  - type: github
    path: "https://github.com/Gracker/SmartPerfetto"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/09-perfetto-sql-cookbook.md"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/15-agent-perfetto-analysis-protocol.md"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/16-perfetto-sdk-in-app-tracing.md"
  - type: internal
    path: "src/part5-app/ch26-observability/03-performance-collection.md"
  - type: internal
    path: "src/part5-app/ch26-observability/14-performance-experiment-statistics.md"
last_task9_autofix_at: "2026-07-10"
updated_date: 2026-07-10
updated_by: openclaw-task2b
p0: 0
p1: 0
p2: 0
finalized_by: "openclaw-task9-auto-promote"
finalized_date: "2026-07-10"
---

# 13.17 SmartPerfetto 与可复用 Trace 分析平台


一条 Perfetto trace 可以回答很多问题，但同一问题换个人、换一周、换一个工具版本，查询口径常会发生偏移。SmartPerfetto 处理的正是这段工程成本：把 Perfetto UI、`trace_processor_shell`、YAML Skill、场景策略、模型运行时、证据合约和报告存储放到同一套分析流程中，让 SQL 可以重跑，结论可以回查，多次分析可以按统一指标比较。

平台机制以 Android 17 / API 37 / `android-17.0.0_r1` 为上界，涉及内核事件时以 `android17-6.18-2026-06_r6` 为基线。工具部分核对 SmartPerfetto v1.3.0、提交 `24eba544cebf231524294aa50def33ee0e267c9e`；该版本固定使用 Perfetto v57.2 的 host 侧 `trace_processor_shell`。这两个版本轴需要分开理解：Android 版本决定设备能采到哪些数据源，host 侧 Perfetto 版本决定 trace 解析器、SQL schema 和 stdlib 能力。用 v57.2 分析 Android 10～17 的 trace，并不表示设备端已经运行 v57.2。

## 从单次 Trace 问答到可复用分析结果

手工分析常停在一次会话中：工程师打开 Perfetto UI，运行几段 SQL，再把截图贴到 issue。截图保留了画面，却很难回答“查询条件是什么”“数值来自哪一行”“换一条 trace 后怎样按同一口径复测”。SmartPerfetto 将一次分析产生的内容分为四类：

| 产物 | 主要用途 | 复核能力 |
| --- | --- | --- |
| 聊天答案 | 当前会话内解释现象、安排下一步查询 | 依赖会话中的工具结果 |
| SQL / Skill 表格 | 保存确定性取数结果 | 可检查查询、参数、列与行 |
| HTML 报告 | 分享一次完整调查 | 保留结论、限制和证据入口 |
| analysis result snapshot | 跨窗口、跨人员、跨版本比较 | 保存标准化指标、证据引用和报告身份 |

四类产物的保存周期不同。聊天答案可以随会话结束，snapshot 和报告则要携带指标来源、证据引用、运行模式、provider/runtime 身份以及部分失败原因。团队回归分析应优先保存 snapshot 或报告。只有一句模型结论时，后来的人无法确认它来自 trace 数据、外部知识，还是模型推断。

SmartPerfetto 也不能代替线上性能平台。线上 P90 / P99、慢帧率和启动耗时用于判断影响范围与趋势；少量代表性 trace 用于解释阶段耗时、线程状态和资源竞争怎样变化。两类证据的采样方式不同，宜在复盘中并列呈现，不能用一条 trace 推导全量用户分布。

## Perfetto AI Assistant 的最小工作流

一次最小分析包含五个动作：加载 `.pftrace` 或 `.perfetto-trace`，说明包名与问题，限定场景或时间窗，选择分析模式，检查报告中的证据。如果 Perfetto UI 已选中 area 或 track event，前端可以把选区作为有界上下文提交给后端。选区只缩小调查范围，不会自动证明该区间就是根因。

`fast`、`full`、`auto` 控制的是 Agent 分析预算和工具范围：

| 模式 | 当前行为 | 适合场景 |
| --- | --- | --- |
| `fast` | 轻量提示词、核心证据工具子集、较小的 runtime 预算 | 已知问题的快速检查 |
| `full` | 完整工具、计划门禁、notes、artifact 与质量门禁 | 因果链较长或需要逐层排除的问题 |
| `auto` | 由硬规则和轻量分类器决定；无法可靠分类时走 `full` | 日常入口 |

引用 reference trace、注册源码或私有知识源时，后端会把 `fast` / `auto` 解析为 `full`，避免轻量路径遗漏必需工具。Smart Profile 是另一层场景编排：preview 阶段还原可分析场景，用户选中启动、滑动、点击、导航、设备状态或 ANR 后，系统才创建对应的深度分析 run。不要把 Smart Profile 的场景选择和 `fast` / `full` 的运行预算混成一个开关。

模型不会直接读取整份 trace 字节。后端通过 `trace_processor_shell`、SQL 和 Skill 取数，再把结构化结果、有界表格投影、选区上下文及允许的报告片段交给 runtime。该设计控制上下文体积，也迫使诊断经过查询接口。它没有消除数据外发风险：工具结果仍可能包含进程名、线程名、slice 文本或业务标识，使用外部 provider 前仍要评估脱敏与合规要求。

复核时应记录 Result ID、`evidenceRefId`、表格行列、查询限制和运行时身份。只反馈“回答不对”不足以定位缺陷；这些字段可以帮助维护者区分 SQL 口径错误、Skill 兼容问题、trace 数据源缺失、模型推断过度和报告投影错误。

## YAML Skill 与场景策略的分层设计

SmartPerfetto 将可复用分析拆成 Skill、strategy 和 template。当前仓库中的 Skill 是 YAML 领域描述，不等同于一段提示词。它可以声明参数、SQL、Skill 引用、迭代、并行、条件分支、诊断输出和展示 schema。Skill 目录按 atomic、composite、comparison、deep、pipelines、modules 与 vendor 扩展组织；文件数量会随版本变化，不宜写死。

| 层级 | 主要职责 | 失败时的症状 | 复核方式 |
| --- | --- | --- | --- |
| Skill | 查询、参数、输出列、执行状态与证据来源 | 空表、错列、错时间窗、单位不一致 | 独立执行并检查 DataEnvelope |
| strategy | 场景路由、执行顺序、质量要求与误诊规则 | 选错调查路径、缺关键分支、过早收敛 | 对照场景和中间证据 |
| template | 报告结构与证据呈现 | 数字可见却无来源，限制项被遗漏 | 检查报告合约与证据引用 |

这组分层减少了临场生成 SQL 的比例。高频取数固化到 Skill，场景决策由 strategy 约束，报告格式交给 template。模型仍可解释数据、提出下一步查询和排列假设，但查询条件、单位换算与空结果语义应留在可测试的执行层。

Skill 输出经兼容桥转换为 `DataEnvelope`。`meta` 保存 schema 版本、来源、时间、Skill/step、执行状态和证据身份；`data` 保存表格、图表、文本或诊断 payload；`display` 保存层级、列定义与格式。`observed`、`empty`、`optional_error` 三种执行状态不能合并解释。空结果表示查询成功且没有匹配行，可选查询失败则表示这一项没有得到有效观测。

## SQL guardrail、stdlib docs 与证据来源索引

Perfetto SQL 的高频错误包括 schema 漂移、漏写 stdlib module、忽略 `dur = -1`、混用 `utid/upid` 与 `tid/pid`、缺少时间窗，以及在大表上进行无界 join。SmartPerfetto 对 raw SQL 和 Skill SQL 使用不同的 include 构建路径。raw SQL 会根据生成的 stdlib symbol index 分析依赖，按确定顺序补入 `INCLUDE PERFETTO MODULE ...;`；Skill 执行器按 Skill 声明构造 include。自动补全只覆盖已知符号，symbol index 为空或语句无法识别时，查询仍需显式 include。

执行后的 SQL 会生成 `QueryReviewV1`，记录实际读取表、过滤条件、输出列、guardrail 告警、stdlib 注入、执行时长、行数与截断状态。复杂 CTE、嵌套查询、JOIN 或窗口函数只能得到部分静态解析时，review 必须标为 `partial`。`QueryReviewV1` 的允许用途固定为 `review_metadata_only`：它帮助人理解查询做过什么，却不能单独支持诊断结论。

完整 Query Review 会随 DataEnvelope 或 Artifact 进入报告；给模型的 compact projection 不含可执行 SQL。这个边界兼顾复核和上下文控制，也修正了一个容易误解的说法：报告侧可以保留可执行 SQL，不能据此推断模型每轮都看到了完整 SQL 文本。

诊断证据由独立的 Evidence Contract 表达。一个数值锚点可以记录 `traceId`、current/reference 一侧、producer kind、Skill 与 step、`queryHash`、`queryReviewId`、artifact、计划阶段，以及具体的 row selector、column、actual value、单位和时间范围。claim 的支持等级分为 `verified`、`partial`、`inference`、`unsupported`。例如报告写“主线程 Runnable 120 ms”，至少要能定位到相应证据行和列；若再写“CPU 争用导致这 120 ms”，还需调度关系或其他证据支持因果判断。

guardrail 只能发现已编码的风险模式，无法证明任意 PerfettoSQL 都正确。缺少 FrameTimeline、Binder、sched、GPU counter 或关键应用标记时，报告应列出缺失数据、降低支持等级，并给出补采配置。`empty` 也不能被写成“系统没有问题”。

## 多 Trace 对比与性能回归判断

SmartPerfetto 支持两类对比。raw reference trace 对比要求当前会话同时能够访问 current 与 reference 两条 trace，适合围绕同一问题继续查询原始数据。analysis result snapshot 对比读取已经完成的分析产物，适合版本回归、A/B、多候选结果和跨窗口复盘；此时比较的是保存下来的标准化指标与证据引用。

标准指标键覆盖这些类别：

- 启动：总耗时、首帧、`bindApplication`、Activity start、主线程 blocked；
- 滑动：平均 FPS、帧数、Jank 数与比例、帧时长 P50/P95/P99；
- CPU：主线程 Running/Runnable、大核占比、平均频率；
- 环境：trace 时长、设备型号、Android 版本和抓取配置摘要。

标准回填的范围更窄，只包含 `startup.total_ms`、`scrolling.avg_fps`、`scrolling.frame_count`、`scrolling.jank_count` 和 `scrolling.jank_rate_pct`。TTFD、PSS、Java/Native Heap、dmabuf、bitmap、RSS/swap 等指标可以由 Skill、SQL 或报告模板提供，不属于当前内置回填集合。缺字段要作为 missing metric 呈现，不能按零值参与比较。

当前显著变化判定同时使用相对阈值和单位阈值。通用相对阈值为 5%；`ms` 为 5 ms，`fps` 为 1 fps，百分比为 1 个百分点，计数为 1，字节为 1 MiB，纳秒为 5,000,000 ns。时间、FPS、字节等指标通常要同时达到绝对阈值与相对阈值；百分比和计数满足其中一个即可。无单位且只有相对变化时采用 5%。这些是产品高亮规则，不是统计显著性检验，也不能代替 26.14 节中的置信区间、样本量和实验设计。

实务上可以在启动 P90 上升后抽取 baseline 与 candidate trace，分别生成 snapshot，再比较启动阶段、主线程状态、Binder、I/O 和首帧提交证据。若设备、温控、编译状态或抓取配置不一致，应先标注环境差异，避免把不可比样本的变化解释为代码回归。

## Provider Manager 与运行时/provider 边界

模型配置包含 Connection、Provider profile 和 runtime。Connection 保存前端要访问的 SmartPerfetto 后端地址与可选后端 token。Provider profile 保存模型端点、模型凭证、模型 ID、协议及 runtime 选择。runtime 决定由哪套 SDK 或 server adapter 编排 SmartPerfetto 工具。

| 配置项 | 作用 | 常见误解 |
| --- | --- | --- |
| Connection | 前端连接 SmartPerfetto 后端 | 把后端 token 当成模型 key |
| Provider profile | 配模型服务、模型 ID、协议类型 | 保存 profile 后忘记设为 active |
| active provider | 当前会话优先使用的 provider | 以为改 `.env` 会覆盖 active profile |
| env fallback | 脚本和服务端部署的默认凭证 | 只查 `.env`，不看 Provider Manager |
| runtime | 选择 Agent SDK / server adapter | provider 能对话就认定工具调用也可用 |

v1.3.0 注册了五条 production runtime：

| runtime | 适配层 | 配置边界 |
| --- | --- | --- |
| `claude-agent-sdk` | Claude Agent SDK | 默认 runtime；支持 Anthropic、Bedrock、Vertex、DeepSeek 与兼容网关 |
| `openai-agents-sdk` | OpenAI Agents SDK | OpenAI、Ollama 与 OpenAI-compatible endpoint |
| `pi-agent-core` | Pi Agent Core | 仅 custom provider；禁用项目发现和 shell/file tools |
| `opencode` | 隔离的 OpenCode server / SDK | 仅 custom provider；不读取用户本机 OpenCode 项目状态 |
| `qoder-agent-sdk` | Qoder Agent SDK / `qodercli` | custom provider 或显式 env；SDK 为可选依赖 |

Qoder SDK 不随默认 Docker、portable 或 npm 安装提供，启用前需要审阅其独立条款并显式安装 optional peer。Pi、OpenCode、Qoder 在 SmartPerfetto 中都只获得按请求生成的分析工具，不应按通用 coding agent 的文件、shell 或网络权限理解。

新建 session 时，runtime 选择依次检查请求指定的 `providerId`、Provider Manager 当前 active provider、`SMARTPERFETTO_AGENT_RUNTIME`，再回到默认的 `claude-agent-sdk`。请求明确指定的 provider 不存在时会 fail-fast。恢复历史 session 走保存下来的 provider/runtime 分支：已保存的 provider 仍优先，env/default session 的 `runtimeOverride` 位于当前环境变量之前，恢复过程不会重新采用后来切换的 active provider。已绑定的 provider 被删除时同样会 fail-fast，不会静默改用另一个 provider。

v1.3.0 还有一个需要单独标注的快照缺口。常规 runtime 选择器已经接受 `qoder-agent-sdk`，但 `providerSnapshot.ts` 的纯 env runtime 解析只列出了 Claude、OpenAI、Pi 和 OpenCode。只靠 `SMARTPERFETTO_AGENT_RUNTIME=qoder-agent-sdk` 启动时，本次运行可以进入 Qoder，env/default 会话快照却不能据此证明 Qoder 身份已经被正确固定。这个限制不影响显式 provider 的存在性检查；恢复该类 Qoder session 前仍应在修复版本上做回归，或重新创建 session。

排障要读取带鉴权的 `GET /api/runtime-health`，检查 runtime、模型和 credential source。公开 `GET /health` 只表示服务存活，不返回凭证来源。这个区别可以防止“连接测试成功”被误判成“分析 runtime 已按预期切换”。

## 运行分发、权限和隐私边界

运行方式应按维护责任选择。Docker 适合服务端部署；三平台 portable 包自带 Node.js 24、后端、预构建前端和固定的 trace processor；源码运行适合维护 Skill、strategy 与后端；npm CLI 提供 `smp` / `smartperfetto`，复用同一套 runtime、MCP 工具、报告和 session snapshot，但不启动 Web UI。批处理、CI 或内部服务可以使用 CLI / API / MCP。

部署者设置 `SMARTPERFETTO_API_KEY` 后，受保护 API 需要携带相应凭证；企业用户还可以使用带角色与 scope 的持久 API key。这里的后端 API key 保护 SmartPerfetto 服务入口，provider key 则授权模型服务，二者不能互换。把服务暴露到非可信网络时，还要限制上传大小、代理超时、报告下载与管理接口。

trace 可能含有进程名、线程名、业务路径、URL 片段、用户操作节奏、设备信息与 slice 参数。上传、provider 投影、Result ID、HTML 报告、日志、workspace 分享和留存清理都应按敏感数据管理。私有源码与外部知识源只有在本次请求显式选择、scope 与授权校验通过后才进入 runtime；它们不会自动暴露给普通 trace 会话。使用 `provider_send` 时还需要注册级许可和本次运行许可。

SmartPerfetto 只能分析调用方有权提供的 trace。Perfetto SDK 或 AndroidX Tracing 可以增加应用内事件，但不会赋予应用读取整机 ftrace、其他进程或系统服务内部数据的权限。系统级采集仍受 `profileable` / `debuggable`、adb、ProfilingManager、系统签名权限和设备策略约束，参见 13.16 与 26.12 节。

## 和原生 Perfetto / Perfetto SDK / APM 平台的组合关系

每个工具负责不同责任。Perfetto UI 提供时间轴观察和人工验证，`trace_processor_shell` 执行确定性查询，Perfetto SDK 把应用事件写入 trace，ProfilingManager 提供受平台控制的 profiling 请求，APM 平台统计长期趋势。SmartPerfetto 位于解析器和团队调查流程之间，负责调用查询、组织证据、生成报告与比较结果。

| 工具 | 更适合的问题 | 产物 |
| --- | --- | --- |
| Perfetto UI | 手工观察时间轴、验证某段事件关系 | 截图、选区、手动 SQL |
| `trace_processor_shell` | 批量查询、可重复 SQL、CI 检查 | CSV / SQL 输出 |
| SmartPerfetto | 开放式 trace 调查、证据报告、多 trace 对比 | Result ID、报告、Skill 表格 |
| Perfetto SDK / AndroidX Tracing | 把应用内部阶段写进 trace | 自定义 slice、counter、data source |
| ProfilingManager | Android 15（API 35）起的受控 profiling 请求 | 系统返回的 profiling 结果 |
| APM 平台 | 长期线上趋势、分位值、告警 | 指标、事件、抽样现场 |

开发期可以分析单条 trace，专项排障可以积累 Skill 与模板，灰度回归可以把异常样本与 baseline snapshot 比较。任何 Agent 生成的因果结论仍需回到 Perfetto UI 或 SQL 结果复核。涉及渲染链时，还要按 App、BufferQueue、SurfaceFlinger、HWC、显示五段责任边界组织证据，避免用一个长 slice 覆盖整条链。

## Skill 质量评估与回归测试

Skill 进入团队流程后，应按可执行代码维护。最小测试集包含固定 trace、固定参数、SQL smoke test、输出列校验、空结果与可选错误分支、证据引用校验和 golden report。Perfetto schema、stdlib、设备数据源与厂商实现都会变化，单看 YAML 能否解析远远不够。

测试可以分为四层：

1. SQL 在固定 trace 上能够执行；
2. DataEnvelope 的列、单位、layer、level 与执行状态符合 contract；
3. 关键指标与 golden 值处于允许误差内；
4. 报告中的 evidence anchor 能返回表格行列，claim support 没有把 `partial` 升级成 `verified`。

启动、滑动、ANR、Binder、I/O、内存和功耗场景都需要成功样本与缺字段样本。缺字段样本用于验证降级路径，例如缺少 FrameTimeline 时，帧级结论必须标为不完整。SmartPerfetto 固定 trace processor 版本后仍需运行 canonical trace 回归；升级 v57.2 之后的版本时，还要重新核对 schema、stdlib symbol index、标准指标和 golden 输出。

13.9 的 SQL 口径、13.13 的 Jank/CUJ 查询、13.15 的调查协议以及 26.14 的回归判定可以转为 Skill contract。contract 应声明输入、输出、单位、证据解释、适用版本、缺失数据分支和人工复核入口。

## 企业内部 Trace 分析平台接入清单

企业接入前要确定 trace 存储、留存周期、报告可见范围、provider 凭证归属、模型请求出网策略、脱敏规则和审计范围。表中的项目应落实到部署配置、权限测试和删除演练，不能只停在文档约定。

| 维度 | 建议检查项 |
| --- | --- |
| 多租户 | tenant / workspace 边界、跨组报告分享审批 |
| Provider 隔离 | 每个租户单独 profile、独立 token、独立用量审计 |
| Trace 留存 | 上传大小限制、过期清理、敏感样本删除流程 |
| 报告权限 | Result ID 可见性、HTML report 分享范围、导出水印 |
| 审计 | 上传、分析、查看、分享、删除、provider 修改记录 |
| 脱敏 | 包名、URL、账号、地理位置、业务参数、截图附件 |
| 回归 | 固定 trace 集合、Skill golden、发布前 smoke test |

权限测试要覆盖同租户不同 workspace、不同 tenant、资源 owner、过期数据和被删除 provider。报告可见不等于原始 trace 可见，二者应有各自的授权检查与审计记录。

## SmartPerfetto 与技术知识库联动

技术知识库保存机制解释、源码锚点和调查顺序，SmartPerfetto 在具体 trace 上执行查询并保存证据。适合转换为 Skill 的内容是稳定口径，例如输入参数、SQL、输出列、单位和失败分支；依赖机型、版本或上下文判断的内容更适合放在 strategy 或机制说明中。

一条实用的维护路径是：从章节选定一个可观察问题，编写 Skill，在固定 trace 上运行，检查报告证据，再把缺字段、厂商差异和误诊条件补回章节。章节修订后还要判断 Skill contract 是否同步变化。这样可以保持“机制说明—可执行查询—真实样本”三者一致。

## 企业版迁移与 404 排查

SmartPerfetto 的企业迁移阶段决定 trace 元数据从文件系统或数据库读取。v1.3.0 的状态如下：

| 阶段 | 读权威 | 写文件系统 | 写数据库 | 回滚语义 |
| --- | --- | --- | --- | --- |
| `legacy` | filesystem | 是 | 否 | 关闭企业模式 |
| `dual-write` | filesystem | 是 | 是 | 删除数据库副本，文件系统仍为权威 |
| `cutover` | DB | 否 | 是 | 恢复切换前已验证的文件系统与 DB 快照 |
| `retired` | DB | 否 | 是 | 恢复退役前快照；不承诺反向转换 |

企业功能启用且未配置 `SMARTPERFETTO_ENTERPRISE_MIGRATION_PHASE` 时，默认阶段是 `dual-write`。进入 `cutover` 还要求 `SMARTPERFETTO_ENTERPRISE_CUTOVER_CONFIRMED=true`；缺少该确认时，服务会在解析迁移计划时拒绝启动。这个门禁要求运维人员已经完成文件系统到 DB 的 reconciliation 和快照验证。

诊断环境阶段时，可用下面的命令只打印两个迁移开关，不要把数据库口令或 provider key 写入工单：

```bash
printf 'phase=%s\n' "${SMARTPERFETTO_ENTERPRISE_MIGRATION_PHASE:-<unset>}"
printf 'cutover_confirmed=%s\n' "${SMARTPERFETTO_ENTERPRISE_CUTOVER_CONFIRMED:-<unset>}"
```

第一行未设置且企业功能已开启时，应按 `dual-write` 解释。第二行只有在准备进入 `cutover` 时才应为 `true`。

`cutover` 阶段的 `readTraceMetadataForContext()` 只按当前 RequestContext 的 tenant/workspace/owner scope 查询 `trace_assets`，查不到就返回 `null`，不会回退到旧文件系统。透明回退会绕过 DB 权威与 RBAC scope，还会掩盖迁移缺口，因此不能作为 404 修复手段。

遇到切换后的 404，可按以下顺序排查：

1. 确认生效阶段、enterprise feature flag 与 cutover confirmation；
2. 按请求的 tenant、workspace、owner 检查 `trace_assets` 是否存在记录；
3. 检查记录中的 `local_path`、文件搬运结果和服务进程访问权限；
4. 检查 SSO 映射、API key scope 与 RBAC，区分“记录缺失”和“当前用户不可见”；
5. 对照切换前 dry-run fingerprint、snapshot manifest 与数据库表计数；
6. 若切换数据不完整，停止写入并按官方 snapshot restore 路径恢复文件系统和 SQLite 快照，再修复 reconciliation。

不能只把环境变量改回 `dual-write` 并假设 DB 数据会自动反向写回文件系统。源码明确说明 dual-write 不是 reverse importer。快照恢复会覆盖目标文件或目录，必须在维护窗口内由部署负责人执行，并在恢复前保留现场副本。

404 率、trace 访问成功率和数据库延迟的阈值应由团队按 SLO 与流量设定，SmartPerfetto 源码没有规定 99.5% 或 0.5% 这类通用目标。迁移监控还应包含 reconciliation 失败数、snapshot 完整性、按 scope 查询的 miss 分类和恢复演练结果。

## 复核准则

使用 SmartPerfetto 时，可以用四个问题约束分析质量：

1. 报告中的关键数值能否回到证据行列和 trace 身份？
2. 因果结论的支持等级是否与调度、时间关系或跨层证据相符？
3. 多 trace 指标是否同口径、同单位、同采集环境，并明确缺失字段？
4. provider、runtime、私有上下文与企业存储是否遵守当前部署的权限边界？

四项中任何一项无法回答，都应把结论留在待验证状态。SmartPerfetto 可以减少重复查询和报告整理，却不会替代 Android 机制判断、Perfetto UI 人工核验或可重复的实验设计。

## 参考源码与文档

- [SmartPerfetto v1.3.0 核对提交](https://github.com/Gracker/SmartPerfetto/tree/24eba544cebf231524294aa50def33ee0e267c9e)
- [Perfetto v57.2 host 工具固定配置](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/scripts/trace-processor-pin.env)
- [Agent runtime 架构](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/docs/architecture/agent-runtime.md)
- [runtime 选择与 snapshot override 顺序](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/agentRuntime/runtimeSelection.ts)
- [v1.3.0 provider/runtime 快照解析](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/providerManager/providerSnapshot.ts)
- [私有分析上下文边界](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/docs/architecture/private-analysis-context.md)
- [DataEnvelope、Query Review 与 Analysis Receipt](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/docs/DATA_CONTRACT_DESIGN.md)
- [raw SQL stdlib include 注入](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/agentv3/sqlIncludeInjector.ts)
- [证据合约类型](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/types/evidenceContract.ts)
- [标准对比指标](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/types/multiTraceComparison.ts)
- [标准指标回填范围](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/standardMetricBackfillService.ts)
- [显著变化阈值](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/comparisonSignificance.ts)
- [企业迁移状态机与快照恢复](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/enterpriseMigration.ts)
- [企业 trace metadata 的 scoped 读取](https://github.com/Gracker/SmartPerfetto/blob/24eba544cebf231524294aa50def33ee0e267c9e/backend/src/services/traceMetadataStore.ts)
