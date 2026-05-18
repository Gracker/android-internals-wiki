---
title: "SmartPerfetto 与可复用 Trace 分析平台"
chapter: "13.18"
section: "13.18"
status: ready-for-review
drafted_date: "2026-05-18"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)；Perfetto trace schema / stdlib 能力按工具版本降级"
last_verified: "2026-05-18"
last_verified_against: "SmartPerfetto README + SmartPerfetto 2026-05-17 更新文 + AIW 13.10/13.16/13.17/26.3/26.14"
confidence: medium
tags: [perfetto, smartperfetto, trace-analysis, ai-assistant, sql-guardrail, observability]
related_chapters: ["13.10", "13.14", "13.16", "13.17", "26.3", "26.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "每日信息/素材驱动/章节深挖"
gap_score: 17
material_count: 4
pipeline_stage: task2b_pending
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-18"
task6_result: pass-light-edit
task6_l1_l2_fixes: 6
task6_l3_l4_issues: 0
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
task2b_result: pending
task9_reviewed_date: "2026-05-18"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-18T22:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-05-18-22-deep-review.md"
task9_review_notes: "2026-05-18 22: Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0。Top: 多 Trace 对比标准指标/回填能力写得超出当前实现。"
last_task6_at: "2026-05-18T22:15:21+08:00"
last_task6_review_log: "logs/review/2026-05-18-22-review.md"
sources:
  - type: blog
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Personal-Knowlodge/source/rss-tech/2026-05-18_RSS_886623bf54.md"
  - type: github
    path: "https://github.com/Gracker/SmartPerfetto"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/10-perfetto-sql-cookbook.md"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/16-agent-perfetto-analysis-protocol.md"
  - type: internal
    path: "src/part3-tools/ch13-perfetto/17-perfetto-sdk-in-app-tracing.md"
  - type: internal
    path: "src/part5-app/ch26-observability/03-performance-collection.md"
  - type: internal
    path: "src/part5-app/ch26-observability/14-performance-experiment-statistics.md"
---

# 13.18 SmartPerfetto 与可复用 Trace 分析平台

<!-- outline-start -->
## 要点

### 🔹 从单次 Trace 问答到可复用分析结果
说明 SmartPerfetto 的问题定位：把 Perfetto UI、SQL、Skill、报告和多 Trace 对比放进同一个分析工作流；重点区分一次性问答、结果快照、HTML 报告和回归对比四类产物。

### 🔹 Perfetto AI Assistant 的最小工作流
覆盖 trace 上传、场景选择、选区上下文、`fast` / `full` / `auto` 分析模式、结果生成和人工复核入口，强调模型只接触工具返回的数据，不直接读取完整 trace。

### 🔹 YAML Skill 与场景策略的分层设计
解释 Skill、strategy、template 的职责边界：Skill 负责可执行 SQL 和表格输出，strategy 负责场景路由，template 负责报告组织；说明这套分层如何降低临场写 SQL 的不确定性。

### 🔹 SQL guardrail、stdlib docs 与证据来源索引
梳理最终可执行 SQL、stdlib include 补齐、Skill validator、`evidenceRefId`、`sourceToolCallId`、行列级引用等机制，帮助读者判断 AI 结论能否回到 trace 数据。

### 🔹 多 Trace 对比与性能回归判断
说明实时 reference trace 对比和 analysis result snapshot 对比的差异，覆盖 baseline / candidates、标准化指标、缺失指标回填、显著变化阈值和报告复核方式。

### 🔹 Provider Manager 与双运行时边界
说明 provider profile、active profile、env fallback、Claude Agent SDK、OpenAI Agents SDK 的职责划分；重点写清模型配置和 SmartPerfetto 后端连接不是同一个概念。

### 🔹 运行分发、权限和隐私边界
覆盖 Docker、本地源码、桌面免安装包、CLI/API/MCP 的适用场景，并说明 trace 文件、SQL 结果、报告分享、workspace 权限和企业部署中的数据治理边界。

### 🔹 和原生 Perfetto / Perfetto SDK / APM 平台的组合关系
对比 SmartPerfetto、Perfetto UI、`trace_processor_shell`、Perfetto SDK、ProfilingManager、APM 平台的分工，给出开发期、专项排障、灰度回归和团队知识库四种使用方式。

## 扩展

### 🔸 Skill 质量评估与回归测试
记录如何用固定 trace、固定 SQL 输出和 golden report 检查 Skill 是否因 Perfetto schema / stdlib 版本变化而失效。

### 🔸 企业内部 Trace 分析平台接入清单
补充多租户、provider isolation、报告权限、trace 留存周期、审计日志和脱敏策略。

### 🔸 SmartPerfetto 与 AIW 知识库联动
探索把 AIW 章节中的排障步骤转成 SmartPerfetto Skill / strategy，再把真实 trace 结果反哺到案例章节。

<!-- outline-end -->

SmartPerfetto 解决的是 trace 调查的工程化问题：SQL 能重跑，证据能定位，报告能分享，多次分析能比较。13.10 节已经讲 Perfetto SQL，13.16 节已经讲 Agent 调查协议，本节把 SmartPerfetto 放在工具系统的位置上看：它把 Perfetto UI、`trace_processor_shell`、YAML Skill、场景策略、模型运行时和报告存储放到同一个分析界面里。[来源: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Personal-Knowlodge/source/rss-tech/2026-05-18_RSS_886623bf54.md]

## 从单次 Trace 问答到可复用分析结果

传统 trace 分析容易停在一次对话里：打开 Perfetto UI，问一个问题，复制几段 SQL，截图给同事。SmartPerfetto 的变化在于把每轮分析拆成四类产物：聊天答案、SQL / Skill 表格、HTML 报告、analysis result snapshot。聊天答案适合快速读结论；SQL 和表格适合复核证据；HTML 报告适合贴到 issue 或复盘文档；snapshot 适合和另一条 trace 的分析结果比较。

这四类产物的生命周期不同。一次性问答只服务当前窗口，结果快照要保存关键指标、证据引用和报告入口，HTML 报告要能离开对话上下文阅读，多 Trace 对比要能把 baseline 与 candidates 放到同一张指标表里。对于团队性能治理，保存“分析结果”比保存“模型回答”更有价值，因为前者保留了指标、证据引用和报告入口，后者很难判断数据从哪里来。

在 AIW 体系里，SmartPerfetto 更接近 26.3 节的“性能证据采集与上报”工具，而不只是 13.3 节 Perfetto UI 的插件。它把线下 trace 证据和线上指标治理连起来：线下用 trace 定位原因，线上用 P90 / P99、慢帧率、启动耗时判断范围和趋势，回归时再把两边的证据放进同一份复盘材料。

## Perfetto AI Assistant 的最小工作流

一次最小分析从 trace 输入开始。用户加载 `.pftrace` 或 `.perfetto-trace` 后，在 AI Assistant 里给出问题、包名、场景和可选时间窗；如果已经在 Perfetto UI 中选中一段 area 或一个 track event，前端会把选区上下文传给后端。后端再按 `fast`、`full` 或 `auto` 模式选择分析深度：`fast` 偏快速巡检，`full` 偏完整调查，`auto` 按问题类型和中间结果调整。[来源: https://github.com/Gracker/SmartPerfetto]

这个路径里有一个边界要写清：模型不直接读取完整 trace 文件。SmartPerfetto 后端用 `trace_processor_shell`、SQL 和 Skill 取数，模型接触的是工具返回的结构化结果、表格摘要、选区上下文和已有报告片段。这样做可以降低两类风险：trace 文件体积过大导致上下文失控，模型绕过查询口径直接猜结论。

人工复核入口也在同一条路径上。报告里的数字、线程名、slice 名、Result ID、SQL 和 evidence id 都应能回到工具调用结果。分析结论不符合预期时，反馈不应只写“AI 判断错了”，而要贴出报告中的 `evidenceRefId`、SQL 表格行列或 Result ID。这样维护者才能判断问题来自 SQL、Skill、trace 数据缺失、模型归纳还是报告渲染。[来源: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Personal-Knowlodge/source/rss-tech/2026-05-18_RSS_886623bf54.md]

## YAML Skill 与场景策略的分层设计

SmartPerfetto 的分析单元可以按三层理解：Skill、strategy、template。Skill 负责可执行查询和表格输出，例如启动、滑动、ANR、锁等待、内存、功耗、BufferQueue、FrameTimeline 这类可复用取数动作；strategy 负责把用户问题路由到合适的 Skill 组合；template 负责把证据组织成报告段落。

| 层级 | 主要职责 | 失败时的症状 | 复核方式 |
| --- | --- | --- | --- |
| Skill | 固定 SQL、输入参数、输出列、空结果处理 | 表格为空、列解释错、时间窗不准 | 单独运行 Skill，检查 SQL 与输出列 |
| strategy | 场景识别、执行顺序、下一跳判断 | 启动问题跑成滑动问题，或过早停止 | 对照问题类型和中间证据 |
| template | 报告结构、证据表、边界说明 | 结论可读但缺证据，或把待验证项写成确定结论 | 检查报告是否引用证据 ID |

这层拆分的收益是减少临场写 SQL。13.16 节已经说明，开放式 trace 调查要先收输入、查 schema、记录 scratchpad、再输出报告。SmartPerfetto 把这套协议产品化：高频 SQL 固化在 Skill，场景判断写进 strategy，输出格式交给 template。模型仍负责解释和排序，但不应把查询口径藏在自然语言里。

## SQL guardrail、stdlib docs 与证据来源索引

Perfetto SQL 的常见错误集中在字段漂移、stdlib module 漏 include、`dur = -1` 未处理、`utid/upid` 和 `tid/pid` 混用、跨时间窗 join 过宽。13.10 节已经给出大 trace 查询约束，SmartPerfetto 在工具层增加 SQL guardrail：展示最终可执行 SQL，补齐可识别的 stdlib include，检查 Skill 声明的依赖与实际查询是否匹配，并把高风险写法暴露出来。[已验证: 13.10 Perfetto SQL 性能分析实战手册]

证据来源索引是另一条约束。一个模型结论如果写了“主线程 Runnable 等待 120 ms”，报告应能标出这 120 ms 来自哪次工具调用、哪张表、哪一列、哪一行。SmartPerfetto 的 DataEnvelope / report contract 会保留 `evidenceRefId`、`sourceToolCallId`、`traceSide`、`queryHash`、行列引用和可选的 plan phase。这样做的目标是让每个数字有回查路径，而不是让报告变复杂。

边界同样要保留。guardrail 不能证明所有 PerfettoSQL 语法都安全，stdlib docs 也不能覆盖每个未来版本的字段变化。合格报告应该把“已验证的数据”“降级后的结果”“缺失的数据源”和“待补采建议”分开写。缺少 FrameTimeline、Binder、sched 或 GPU counter 时，SmartPerfetto 应降低可信度，而不是给出无法复查的根因。

## 多 Trace 对比与性能回归判断

SmartPerfetto 有两类对比对象。实时 reference trace 对比要求当前分析能访问 current / reference 两条 raw trace，适合临时比较一台设备上的两次抓取。analysis result snapshot 对比比较的是已经完成的分析结果，适合回归、A/B、多人协作和跨窗口复盘；候选 trace 不必仍在另一个 Perfetto UI 窗口里打开。

回归判断要先标准化指标。启动类问题可以比较 TTID、TTFD、关键阶段耗时、主线程状态分布；滑动类问题可以比较总帧数、慢帧率、最大 frame overrun、JankStats 或 FrameTimeline 结果；内存问题可以比较 PSS、Native / Java Heap、dmabuf、bitmap、RSS / swap。缺指标时可以尝试回填，但报告必须写出回填失败的字段，避免把“缺数据”当成“没有变化”。

这类对比和 26.14 节的实验统计互相补位。线上实验负责判断分位值和阈值违约率是否变化，SmartPerfetto 负责在少量代表性 trace 上解释变化来源。一个版本的启动 P90 上升后，应该抽取 baseline / candidate trace，各自生成 result snapshot，再比较启动阶段、线程状态、Binder、I/O 和帧提交证据。这样可以把“线上变慢”继续追到“哪类 trace 证据变了”。

## Provider Manager 与双运行时边界

SmartPerfetto 的模型配置分成三层：Connection、Provider、运行时。Connection 配 SmartPerfetto 后端地址和可选后端访问 token；Provider profile 配模型服务的 Base URL、API key / token、模型 ID 和协议类型；运行时决定后端用 Claude Agent SDK 还是 OpenAI Agents SDK 编排工具调用。这三层混在一起时，排障很难判断问题出在后端连接、模型凭证还是工具编排。[来源: https://github.com/Gracker/SmartPerfetto]

| 配置项 | 作用 | 常见误解 |
| --- | --- | --- |
| Connection | 前端连接 SmartPerfetto 后端 | 把后端 token 当成模型 key |
| Provider profile | 配模型服务、模型 ID、协议类型 | 保存 profile 后忘记设为 active |
| active provider | 当前会话优先使用的 provider | 以为改 `.env` 会覆盖 active profile |
| env fallback | 脚本和服务端部署的默认凭证 | 只查 `.env`，不看 Provider Manager |
| 运行时 | 选择 Claude Agent SDK 或 OpenAI Agents SDK | provider 能聊天就认为能稳定 tool call |

已经创建的分析 session 通常应固定当时的 provider 来源。trace 分析里的多轮追问依赖前一轮工具结果、SDK 会话状态和报告上下文；中途切换模型可能让后续回答无法复用原来的证据。排障时应同时记录 `/health` 的 `aiEngine.runtime`、`credentialSource`、provider 名称、模型 ID、协议类型、分析模式和 session 日志。

## 运行分发、权限和隐私边界

运行方式按用户角色选择。Docker 适合快速试用和服务端部署；免安装包适合不想装 Node.js / Docker 的普通用户；本地源码适合改 Skill、strategy、后端和发布脚本；Dev 模式只适合修改 AI Assistant 插件 UI；CLI / API / MCP 适合批量分析、CI 接入和内部平台集成。[来源: https://github.com/Gracker/SmartPerfetto]

trace 文件默认包含业务路径、进程名、线程名、URL 片段、用户操作节奏、设备信息和可能的敏感参数。SmartPerfetto 报告分享、Result ID 可见性、workspace 权限、trace 留存周期、日志导出和 provider 数据发送都要按隐私数据处理。企业部署里还要记录谁上传了 trace、谁查看了报告、报告是否可跨 workspace 分享、provider 是否被隔离到租户内。

权限边界也要拆开。SmartPerfetto 可以分析用户提供的 trace，并可以用 Perfetto SDK / AndroidX Tracing 产生的应用事件增强证据；它不能替代系统权限。普通第三方应用不能因为接入 Perfetto SDK 就读取整机 ftrace、其他进程或系统服务内部数据。系统级 trace 的采集边界仍由 Android 权限、profileable / debuggable、adb、ProfilingManager 和企业设备策略决定，详见 13.17 与 26.12 节。

## 和原生 Perfetto / Perfetto SDK / APM 平台的组合关系

SmartPerfetto 不替代 Perfetto。Perfetto UI 仍是时间轴观察和手工验证入口，`trace_processor_shell` 仍是确定性查询引擎，Perfetto SDK 负责把应用内事件写进 trace，APM 平台负责长期采集线上指标和异常。SmartPerfetto 位于这些工具之间，负责把分析过程组织成可复用的证据产物。

| 工具 | 更适合的问题 | 产物 |
| --- | --- | --- |
| Perfetto UI | 手工观察时间轴、验证某段事件关系 | 截图、选区、手动 SQL |
| `trace_processor_shell` | 批量查询、可重复 SQL、CI 检查 | CSV / SQL 输出 |
| SmartPerfetto | 开放式 trace 调查、证据报告、多 trace 对比 | Result ID、报告、Skill 表格 |
| Perfetto SDK / AndroidX Tracing | 把应用内部阶段写进 trace | 自定义 slice、counter、data source |
| ProfilingManager | Android 15+ 受控 profiling 请求 | 系统返回的 profiling 结果 |
| APM 平台 | 长期线上趋势、分位值、告警 | 指标、事件、抽样现场 |

开发期可以用 SmartPerfetto 快速解释单条 trace；专项排障可以积累 Skill 和报告模板；灰度回归可以把线上异常样本抽成 trace，再和 baseline snapshot 比较；团队知识库可以把稳定的分析路径回写到 AIW 章节、Skill 和故障手册里。这种组合关系能减少口头经验流失，也能让新同事从报告反查到 SQL 和章节说明。

## Skill 质量评估与回归测试

Skill 一旦进入团队工作流，就要按代码质量管理。最小测试集应包含固定 trace、固定输入参数、SQL smoke test、字段存在检查、空结果检查和 golden report。Perfetto schema、stdlib module、Android 版本和厂商 ROM 都会变；没有回归测试的 Skill 很容易在下一次升级后输出空表或错列。

推荐把 Skill 测试分成四档：SQL 能执行；输出列符合 contract；关键指标和 golden 值在阈值内；报告里的 evidence id 能回到表格行列。启动、滑动、ANR、Binder、I/O、内存、功耗这些高频场景至少要有一条成功样本和一条缺字段样本。缺字段样本用来验证降级逻辑：报告应写“缺 FrameTimeline”，不能把帧分析写成确定结论。

AIW 可以提供一批通用测试口径。13.10 节的 SQL 模板、13.16 节的调查协议、13.14 节的 Jank CUJ 查询和 26.14 节的回归判定表，都可以转成 Skill contract。每个 contract 都应写清输入、输出列、证据解释、适用版本和失败分支。

## 企业内部 Trace 分析平台接入清单

企业内部接入 SmartPerfetto 时，技术问题通常不难，治理问题更容易拖慢推进。接入前至少回答这些问题：trace 上传到哪里，保留多久；报告默认 private 还是 workspace 可见；provider 凭证由个人配置还是租户统一管理；模型请求是否允许出公网；报告中的进程名、URL、用户操作和业务字段是否需要脱敏；审计日志保留哪些动作。

| 维度 | 建议检查项 |
| --- | --- |
| 多租户 | tenant / workspace 边界、跨组报告分享审批 |
| Provider 隔离 | 每个租户单独 profile、独立 token、独立用量审计 |
| Trace 留存 | 上传大小限制、过期清理、敏感样本删除流程 |
| 报告权限 | Result ID 可见性、HTML report 分享范围、导出水印 |
| 审计 | 上传、分析、查看、分享、删除、provider 修改记录 |
| 脱敏 | 包名、URL、账号、地理位置、业务参数、截图附件 |
| 回归 | 固定 trace 集合、Skill golden、发布前 smoke test |

这张清单用于避免 trace 平台变成新的敏感数据散点。性能团队要能复查证据，安全和业务团队也要能知道数据在哪里、谁访问过、何时删除。

## SmartPerfetto 与 AIW 知识库联动

AIW 适合提供稳定的机制解释和调查步骤，SmartPerfetto 适合把步骤执行到具体 trace 上。两者可以互相反哺：AIW 章节里的排障流程转成 Skill / strategy；SmartPerfetto 在真实 trace 中发现的新分支、缺字段场景、厂商差异和误判案例，再回写到对应章节的扩展或案例集。

可先从三类章节试点：13.10 的 SQL 模板、13.16 的 Agent 调查协议、Part 5 的启动 / 渲染 / 内存 / 功耗实战章节。每个试点只做一个小回路：选一类问题，写一个 Skill，跑固定 trace，生成报告，把报告里的证据和失败分支回写 AIW。这样 AIW 不会停在静态文章，SmartPerfetto 也不会变成只靠提示词维护的工具。

## 小结

SmartPerfetto 的价值在可复查：模型回答要能回到 SQL，报告数字要能回到证据行，多次分析要能形成对比，Skill 要能回归测试。把这几件事做好，它就是团队 trace 调查、回归复盘和知识归档的中间层。工程上仍要保留边界：数据来自 trace processor 和 Skill，结论需要人工复核，缺失的数据源要写进补采建议。
