---
title: Measure
chapter: '19'
section: '19.09'
status: "ready-for-review"
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-04-24'
last_verified_against: measure-sh docs/README.md + sdk-integration-guide + feature-network-monitoring + configuration-options + feature-bug-report-android + docs/api/dashboard/README.md retention endpoint
confidence: medium
tags:
- apm
related_chapters:
- '19.0'
sources:
- type: official
  path: https://github.com/measure-sh/measure
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/README.md
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/sdk-integration-guide.md
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/features/feature-network-monitoring.md
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/features/feature-identify-users.md
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/features/feature-bug-report-android.md
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/features/configuration-options.md
- type: official
  path: https://github.com/measure-sh/measure/blob/main/docs/api/dashboard/README.md
- type: official
  path: https://raw.githubusercontent.com/measure-sh/measure/main/docs/hosting/README.md
pipeline_stage: task2b_pending
reviewed_by: openclaw-task6
reviewed_date: "2026-05-20"
task6_result: needs-rework
task6_state: reviewed
task9_state: reviewed
task2b_state: pending
task2b_result: pending
task2b_reopened_at: "2026-05-20T20:08:00+08:00"
task2b_fixed_at: '2026-04-24T14:55:00+08:00'
last_task2b_at: '2026-04-24T14:55:00+08:00'
task9_result: needs-rework
task9_reviewed_date: "2026-05-20"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-20T20:22:00+08:00"
task6_reviewed_date: "2026-05-20"
last_task6_at: "2026-05-20T20:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-20-20-review.md"
last_task9_audit: "2026-05-20"
last_task9_audit_log: "logs/deep-review/2026-05-20-15-audit.md"
task9_review_notes: "2026-05-20 Task9 deep review: P1 Crash/ANR/native crash 能力边界缺失，已写入 queue/research-gaps；另有 P2 版本接入边界、App size 数据模型、traceparent 锚点建议。"
last_task9_review_log: "logs/deep-review/2026-05-20-20-deep-review.md"
---
# Measure

<!-- outline-start -->

## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 Measure 是开源移动监控平台，包含 SDK、后端和看板；和只提供端侧采集的 Matrix / KOOM 分开讲。
- 🔹 [会话时间线] 展开 session、screen、event、trace、error、resource 的关系；补一个用户操作到 ANR 的时间线例子。
- 🔹 [能力范围] 按 Crash、ANR、HTTP、启动、App size、CPU、内存、点击、页面导航列数据来源、字段和适用判断。
- 🔹 [接入成本] 写 SDK 接入之外的工作：部署、存储、查询、符号化、权限、告警、采样、数据删除。
- 🔹 [自定义 trace] 规定 trace 命名、属性、单位、动态值禁用规则；补登录、首屏、支付、图片解码示例。
- 🔹 [自托管] 拆存储成本、索引设计、附件保留、mapping / native symbol 关联、备份和升级风险。
- 🔹 [OpenTelemetry] 说明移动 session 与服务端 trace 的模型差异；设计 trace id / request id 关联方式。
- 🔹 [平台对比] 和 Firebase、Sentry 做表格对比，维度包括开源/托管、错误监控、性能 trace、会话上下文、部署成本。
- 🔹 [隐私策略] 覆盖 URL pattern、用户标识、日志、请求体、截图/附件、地区合规和删除请求。
- 🔹 [试点评估] 给 2-4 周试点清单，验证崩溃定位、ANR 上下文、会话检索、告警噪声和团队使用成本。

### 扩展（可选深入）

- 🔸 增加 Measure 平台数据流图，标出端侧事件、批量上传、后端入库、查询和告警。
- 🔸 补一份 session JSON 示例，要求字段能支持页面、网络、错误和性能 trace 关联。
- 🔸 加一张自托管成本表，区分小团队试点、中型团队、私有化环境。
- 🔸 对 measure-sh/measure README、部署文档、license、维护状态做核对。
- 🔸 增加“什么时候选 Firebase / Sentry / Measure”的决策表。

### 流水线加工要求

- 平台能力必须和运维成本一起写，不能只列 SDK API。
- 每个数据对象都要给字段例子，后续服务端章节可以直接复用。
- 涉及 OpenTelemetry 时只写可验证的关联方式，不扩展成服务端 APM 教程。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## Measure 是开源移动监控平台

Measure 是一个开源移动监控方案，目标是把崩溃、ANR、启动、错误率、App 大小、用户点击、页面导航、HTTP 调用、CPU、内存等信息组织成可回查的会话时间线。它和 Matrix、KOOM 这类“客户端采集组件”不同，更接近“SDK + 后端 + 看板”的平台方案。

如果团队不想从零搭服务端，又希望数据可自托管，Measure 值得评估。它的边界也要先定清：平台能帮团队收集很多监控数据，但专项性能诊断仍然要回到 Perfetto、Profiler、heap dump 和业务日志。

[已验证: 官方文档, GitHub README；docs/README.md；docs/sdk-integration-guide.md]

## 它的优势在会话上下文

很多线上问题难查，是因为单条崩溃或 ANR 日志太孤立。Measure 的一个强点是 event timeline：把错误会话中的点击、导航、HTTP 调用、CPU、内存等事件按时间排列。

这类时间线能回答几个常见问题：

- 用户进入哪个页面后出现错误。
- 错误前是否发生网络失败、长耗时请求或页面跳转。
- CPU / 内存是否在错误前异常升高。
- 同一类问题是否有相似操作路径。

这和只看堆栈是两种体验。堆栈告诉你崩在代码哪里，时间线告诉你用户和系统在崩溃前经历了什么。

## 核心能力

| 能力 | 适合的问题 |
|---|---|
| Crash / ANR 自动捕获 | 稳定性大盘、版本回归、错误聚合 |
| Launch time / error rate / app size | 发布质量和基础体验趋势 |
| Session timeline | 单个用户会话回查和复现路径判断 |
| HTTP / CPU / memory 事件 | 错误发生前后的资源和网络上下文 |
| Bug report | 用户主动反馈和设备侧现场补充 |
| Custom traces | 业务关键路径耗时观测 |

这些能力组合起来后，Measure 更像移动端“可观测性平台”。它不只收一个指标，而是把会话中的多个事件放在同一条时间线上。

## 接入成本不只在 SDK

开源平台型方案的成本常被低估。除了客户端 SDK，还要考虑：

- 后端服务部署、升级、备份和容量规划。
- 数据字段合规，尤其是 URL、请求内容、用户标识、设备标识。
- 符号表、mapping 文件、版本管理。
- 团队内部的项目、环境、权限和告警配置。
- 自定义事件命名规范，避免不同业务各写一套字段。

如果团队已经有日志平台、埋点平台和告警平台，Measure 还要和这些系统分工。重复建设会让开发者不知道该查哪一个入口。

## 和 Firebase、Sentry 的差别

Firebase Performance 更偏 Google 生态里的低门槛性能监控；Sentry 强在错误监控、tracing、profiling 和会话回放；Measure 的特点是开源、自托管和移动会话时间线。

选型时可以按三件事判断：

1. 数据是否必须自托管。
2. 团队是否有维护后端服务的能力。
3. 当前最缺的是崩溃治理、性能指标，还是会话级回查。

如果只是想快速看到启动、网络、屏幕渲染和自定义 trace，Firebase 更轻。如果主要处理崩溃、异常聚合和跨端错误追踪，Sentry 更成熟。如果希望把移动监控数据留在自有环境里，Measure 的开源形态更有吸引力。

## 使用建议

Measure 适合作为平台入口评估，而不是单个性能 SDK。试点时不要一次接入所有事件，先围绕一条真实问题路径验证：崩溃能否聚合、会话能否回放、符号能否还原、告警能否进入团队处理流程。

只有当这些环节都跑通，平台型 APM 才能给团队省时间。否则它只是多收了一批数据。

## 平台型 APM 的数据模型

Measure 这类平台主要看数据模型，单个 SDK API 反而不是评估重点。一个移动会话通常可以拆成：

- `session`：一次 App 前台使用周期，包含用户、设备、版本、启动时间。
- `screen`：页面进入、退出和停留时间。
- `event`：点击、导航、业务事件、生命周期事件。
- `trace`：一段自定义耗时，例如启动、登录、首屏、支付。
- `error`：Crash、ANR、非致命异常。
- `resource`：HTTP、CPU、内存、App size 等资源或环境数据。

平台的价值来自这些事件能放在同一条时间线上。只有 Crash，没有点击和页面；只有网络，没有页面和用户路径；只有 CPU，没有错误上下文，分析都会断。

## 会话时间线怎样帮助定位

假设用户反馈“打开详情页后卡死”，传统 crash 平台可能只给一条 ANR 主线程堆栈。会话时间线能补出更多上下文：

```text
00:00 App foreground
00:01 screen: Home
00:05 click: feed_item
00:05 screen: Detail
00:06 http: /item/detail 200 820ms
00:07 http: /recommend timeout 5000ms
00:07 memory: 420MB -> 680MB
00:08 click: back
00:10 anr: input dispatching timed out
```

这组事件不能直接给根因，但能把复现路径变清楚：进入详情页、推荐接口超时、内存上涨、返回时 ANR。之后再抓 Perfetto，看主线程和网络回调。

## 自定义 trace 的设计原则

平台型 APM 一定会提供自定义 trace。trace 名称和属性要稳定，否则后端无法聚合。

推荐命名：

- `startup.cold.first_draw`
- `home.first_feed`
- `detail.load_content`
- `checkout.submit_order`
- `image.decode.thumbnail`

不推荐命名：

- 带商品 id、用户 id、完整 URL 的动态名称。
- 每个函数都建 trace。
- 同一业务在不同模块里用不同名字。

自定义 trace 的 metric 也要定义单位。比如 `duration_ms`、`payload_kb`、`item_count`、`cache_hit`，不要让客户端随意上报字符串值。

## 自托管平台的成本清单

Measure 的开源形态意味着团队可以自托管，也意味着平台工作要自己承担：

| 成本 | 具体内容 |
|---|---|
| 存储 | 原始事件、聚合结果、附件、trace、日志保留周期 |
| 查询 | 按版本、机型、页面、用户、session 查询 |
| 符号化 | mapping、native symbol、构建产物关联 |
| 告警 | 阈值、环比、版本灰度、噪声抑制 |
| 权限 | 项目隔离、用户数据访问、审计 |
| 数据治理 | 字段命名、隐私脱敏、采样、删除策略 |

这些成本没有处理好，开源平台也会变成难维护的内部系统。试点时要从最小可用范围开始：Crash / ANR + 会话时间线 + 版本维度，跑通后再加性能 trace。

服务端保留期在 Dashboard 中可配，范围是 30-365 天，默认 30 天（通过 `GET/PATCH /apps/:id/retention` 管理）。这个值会直接影响存储成本、附件保留时间和删除策略。[已验证: Dashboard API docs/api/dashboard/README.md retention endpoint]

## 和 OpenTelemetry 的关系

很多团队会问移动 APM 是否要直接接入 OpenTelemetry。答案取决于目标。服务端 trace 和移动 session 的数据模型并不完全一致。移动端多了页面、前后台、设备、系统版本、冷启动、慢帧、ANR、用户操作等概念。

更稳的做法是：

- 移动端内部用适合 App 的事件模型。
- 网络请求携带 trace id，与服务端 trace 关联。
- 服务端侧仍按 OpenTelemetry / APM trace 分析后端耗时。
- 平台查询时能从移动 session 跳到服务端 trace。

这样既保留移动端语义，也能让同一次请求从 App 查到服务端。

## 隐私策略要在接入前定清

[已验证: 官方文档, docs/features/feature-network-monitoring.md；docs/features/feature-identify-users.md；docs/features/feature-bug-report-android.md；docs/features/configuration-options.md；docs/api/dashboard/README.md retention endpoint]

Measure 已经提供了 URL pattern、HTTP body / header、用户标识、截图遮罩、数据保留期这些控制点，但默认策略仍要由接入团队自己定。试点阶段如果没有把规则写清，后面补救成本会很高。

| 风险点 | 文档里的控制点 | 接入建议 |
|---|---|---|
| URL pattern | Dashboard 会把高流量 URL 归并成 endpoint pattern；HTTP 事件支持按 URL 精确匹配或 `*` 通配符启停 | 只保留排障必需的路径；登录、支付、上传、回调 URL 单独列 allowlist / denylist |
| 用户标识 | `Measure.setUserId()` 会跨启动持久化；官方明确建议不要放 email、手机号这类 PII | 使用内部匿名 user id 或 hash；登出时调用 `Measure.clearUserId()` |
| 请求体 / 响应体 | 默认不采集 body 和 header；只能对指定 URL 打开 | body 采集只给白名单接口，优先灰度环境；敏感字段先在业务层脱敏 |
| 日志 / 诊断文件 | `enableDiagnosticMode` 只写 Measure SDK 自己的日志文件 | 只在 debug 或线下复现时打开，不把业务日志混进附件 |
| 截图 / 附件 | bug report 默认可带截图，支持 screenshot mask level，单条 bug report 最多 5 个附件 | 默认开启文字或敏感输入遮罩；支付、实名认证、聊天页按场景禁用截图，必要时改成 layout snapshot |
| 地区合规 | 自托管可以把数据留在自有区域；服务端 retention 可配 30-365 天（默认 30 天） | EU、境内、海外环境分开部署，部署前确认存储区域、备份流程和访问审计 |
| 删除请求 | SDK 提供 `clearUserId()` 处理后续会话标识；公开文档里明确的服务端控制项是 retention | 试点前就定义“按 user id 检索、导出、删除历史 session”的后台流程；没有这条流程时，不要把可识别用户数据放进自定义属性、请求体或附件 |

执行隐私策略时，SDK 初始化参数、dashboard 远端配置、自托管存储策略要放在同一张表里审一次。这样排查事故时，团队才能知道哪些字段能看、哪些字段不能留。

## Measure 试点评估表

试点 Measure 时建议按问题验证，而不是按功能勾选：

| 验证问题 | 通过标准 |
|---|---|
| Crash 能否定位 | 混淆堆栈能还原，能按版本聚合 |
| ANR 能否定位 | 能拿到线程信息，能关联页面和会话 |
| 会话是否有用 | 错误前点击、页面、网络、内存事件能串起来 |
| 自定义 trace 是否稳定 | 同一业务路径在不同版本名称一致 |
| 平台是否可运营 | 有告警、权限、采样和数据保留策略 |

通过这些验证后，再决定是否扩大到更多业务线。
