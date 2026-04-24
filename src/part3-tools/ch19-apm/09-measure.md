---
title: "Measure"
chapter: "19"
section: "19.09"
status: draft
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "measure-sh/measure GitHub README"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: blog
    path: "https://github.com/measure-sh/measure"
pipeline_stage: drafted
---

# Measure

## Measure 是开源移动监控平台

Measure 是一个开源移动监控方案，目标是把崩溃、ANR、启动、错误率、App 大小、用户点击、页面导航、HTTP 调用、CPU、内存等信息组织成可回查的会话时间线。它和 Matrix、KOOM 这类“客户端采集组件”不同，更接近“SDK + 后端 + 看板”的平台方案。

如果团队不想从零搭服务端，又希望数据可自托管，Measure 值得评估。它的边界也要先定清：平台能帮你接住很多监控数据，但专项性能诊断仍然要回到 Perfetto、Profiler、heap dump 和业务日志。

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

如果只是想快速看到启动、网络、屏幕渲染和自定义 trace，Firebase 更轻。如果主要问题是崩溃、异常聚合和跨端错误追踪，Sentry 更成熟。如果希望把移动监控数据留在自有环境里，Measure 的开源形态更有吸引力。

## 使用建议

Measure 适合作为平台入口评估，而不是单个性能 SDK。试点时不要一上来接入所有事件，先围绕一条真实问题路径验证：崩溃能否聚合、会话能否回放、符号能否还原、告警能否进入团队处理流程。

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

这组事件不能直接给根因，但能把复现路径变清楚：进入详情页、推荐接口超时、内存上涨、返回时 ANR。接下来才值得抓 Perfetto、看主线程和网络回调。

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

## 和 OpenTelemetry 的关系

很多团队会问移动 APM 是否要直接接入 OpenTelemetry。答案取决于目标。服务端 trace 和移动 session 的数据模型并不完全一致。移动端多了页面、前后台、设备、系统版本、冷启动、慢帧、ANR、用户操作等概念。

更稳的做法是：

- 移动端内部用适合 App 的事件模型。
- 网络请求携带 trace id，与服务端 trace 关联。
- 服务端侧仍按 OpenTelemetry / APM trace 分析后端耗时。
- 平台查询时能从移动 session 跳到服务端 trace。

这样既保留移动端语义，也能让同一次请求从 App 查到服务端。

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
