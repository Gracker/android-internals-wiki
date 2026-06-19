---
title: "稳定性度量与指标体系"
chapter: "20.6"
section: "20.6"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-11"
last_verified_against: "AOSP android-16.0.0_r1, developer.android.com, Google Play Console"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 1
sources:
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844486"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java"
tags: [metrics, crash-rate, anr-rate, play-vitals, slo, dashboard]
related_chapters: ["20.1", "26.1", "15.3"]
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task9_state: "pending"
task2b_state: "fixed"
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
task6_result: pass-light-edit
task9_reviewed_date: "2026-05-28"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-19T13:27:06+08:00"
last_task9_review_log: "logs/deep-review/2026-06-19-13-audit.md"
task9_result: "auto-fixed"
task9_review_notes: "2026-05-17 Task9 11: needs-rework。P1 3：Crash-Free 示例计算仍错；ANR 超时表仍把系统阈值/内部目标/Android 14+ soft-hard timeout 混在一起；Vitals/Firebase/行业阈值来源仍不闭合。P2 1：官方 URL 需修正。 已写入 logs/deep-review/2026-05-17-11-deep-review.md。 | 2026-05-28 Task9 deep-review: auto-fixed。P0 0 / P1 0 / P2 1；Android Vitals 官方 URL 从 answer/9844476 修正为 answer/9844486，回到 Task6 复审。 | 2026-05-28 10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 1；Google Play Vitals 阈值和 User-Perceived ANR 仅计 input dispatching timed out 的边界与官方文档一致；无 P0/P1。 自动晋升 finalized。 | 2026-06-19 13 Task9 idle audit: auto-fixed。P1 1（已修复）/ P0 0 / P2 0；FGS 超时版本边界修正：Android 14 仅 shortService ANR，Android 15+ dataSync/mediaProcessing 为 6h/24h 后台运行限额且超时通常 RemoteServiceException，不再写成 Android 14+ 一组 ANR 阈值。"
rework_notes: "Task 2B 回炉修复: P0 User-Perceived ANR Rate 定义修正(Vitals 只计 Input dispatching timed out), P1 行业对标值改为匿名经验区间, P1 示例计算补 Session 分母, P1 ANR 阈值表补 Android 14+ soft/hard 超时, P2 Native Crash 采集描述修正, P2 26.1 引用改指向 15.3"
last_task2b_at: "2026-05-23T11:17:28+08:00"
p0: 0
p1: 0
p2: 0
last_task6_at: "2026-05-28T02:11:48+08:00"
task6_review_notes: "2026-05-28 Task6：Task9 auto-fix 后写作复审通过；修复 frontmatter 禁用词和结尾否定-纠正式表达 2 处；无 L3/L4 回炉项，送 Task9 复核。"
last_task2b_verifier_at: "2026-05-27T23:28:16+08:00"
task2b_verifier_note: "queue 无 pending 且正文充分，回流 Task6 复审；仅修正状态流转。"
last_task9_autofix_at: "2026-06-19"
last_task6_review_log: "logs/review/2026-05-28-02-review.md"
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
finalized_by: openclaw-task9-auto-promote
finalized_date: "2026-05-28"
last_task9_audit: "2026-06-19"
---

# 稳定性度量与指标体系

20.1 节建立了 Crash / ANR / OOM 的分类框架，也给出了 Google Play Vitals 的底线阈值。本节处理三件事：**团队内部的稳定性数据怎么算、怎么看、怎么管**——从计算口径到看板搭建，再到 SLO 执行。

崩溃率是一组针对性指标。不同计算口径回答不同问题，选错口径会得出错误判断。后文分别说明这些指标的计算方法和适用场景。

## 崩溃率指标定义：四种口径，四种用途

### UV 崩溃率（User Crash Rate）

$$\text{UV 崩溃率} = \frac{\text{当日发生过崩溃的去重用户数}}{\text{当日活跃用户数（DAU）}}$$

UV 崩溃率衡量：**崩溃影响了多少比例的用户**。分子是"发生过至少一次崩溃的独立用户"，不去重意味着一个用户崩溃 10 次和崩溃 1 次在 UV 崩溃率里等价。

这是最常用的对外汇报指标，也是 Google Play Vitals 的核心指标。但 UV 崩溃率有一个陷阱：它和应用的使用时长强相关。用户在 App 里待 60 分钟，遇到崩溃的概率远高于待 5 分钟的用户。一个日活 1 亿、人均使用 120 分钟的社交 App，和一个日活 500 万、人均使用 10 分钟的工具 App，UV 崩溃率不能直接横向比较。

### PV 崩溃率（Session Crash Rate）

$$\text{PV 崩溃率} = \frac{\text{崩溃次数}}{\text{总会话数（Session 数）}}$$

PV 崩溃率也叫 Session 崩溃率（本节中 PV 和 Session 等价使用，指一次完整的使用会话），用来衡量：**平均多少次会话会出现一次崩溃**。它消除了用户使用时长带来的偏差，适合做跨应用、跨版本的横向对比。

Firebase Crashlytics 报告中的 "Crash-Free Sessions" 就是基于这个口径的变形：

$$\text{Crash-Free Session Rate} = 1 - \text{PV 崩溃率}$$

行业基线：Crash-Free Session Rate ≥ 99.5% 是发版门禁的常见标准。低于 99% 意味着平均每 100 次使用就有一次崩溃，用户体验已经很差了。

[已验证: Firebase Crashlytics 文档, firebase.google.com/docs/crashlytics]

### 启动崩溃率

$$\text{启动崩溃率} = \frac{\text{启动阶段崩溃次数}}{\text{总启动次数}}$$

启动阶段的定义因团队而异，常见做法是取 `Application.onCreate()` 到第一个 Activity `onResume()` 的时间窗口。这个指标要单独看，原因有两个：

1. 启动崩溃对用户伤害最大——App 打不开，热修复也无法自救
2. 启动阶段代码路径集中（初始化、配置下发、资源加载），崩溃的归因相对明确

启动崩溃率的目标通常比整体崩溃率严格一个数量级。大型团队常见内部红线：≤ 0.01%。超过这个值，灰度立即暂停。

### 重复崩溃率

$$\text{重复崩溃率} = \frac{\text{同一用户连续发生相同堆栈崩溃的次数}}{\text{总崩溃次数}}$$

这个指标衡量的是崩溃后的恢复能力。如果同一个用户反复在同一个地方崩溃，说明恢复逻辑有问题（比如状态没有清理干净，重启后又走到同样的错误路径）。

重复崩溃率 > 30% 意味着相当一部分崩溃是"可复现但未修复"的，应该优先处理。这与崩溃堆栈的去重聚合（crash clustering）配合使用——先看 Top 10 堆栈簇的影响用户数，再看每个簇的重复崩溃率，决定修复优先级。

### 口径选择指南

| 场景 | 推荐指标 | 原因 |
|------|----------|------|
| 对外汇报（老板 / Play Store） | UV 崩溃率 | 与用户体感最接近 |
| 跨版本对比 | PV 崩溃率（Crash-Free Session） | 消除使用时长偏差 |
| 发版门禁 | Crash-Free Session + 启动崩溃率 | 兼顾整体质量和关键路径 |
| 崩溃治理优先级排序 | 堆栈簇影响用户数 + 重复崩溃率 | 定位影响面和恢复能力 |

## ANR 率与 Google Play Vitals 标准

### Google Play Vitals 的定义

Google Play 通过 Android Vitals 对所有上架应用做持续性监控。两个核心指标：

**User-Perceived Crash Rate（用户感知崩溃率）**

$$\text{User-Perceived Crash Rate} = \frac{\text{在前台经历过至少一次崩溃的用户数}}{\text{每日活跃用户数}}$$

**User-Perceived ANR Rate（用户感知 ANR 率）**

$$\text{User-Perceived ANR Rate} = \frac{\text{在前台经历过至少一次用户可感知 ANR 的用户数}}{\text{每日活跃用户数}}$$

两个指标都限定"前台"——后台崩溃或后台 ANR 不计入分子。这是因为用户只感知到前台异常。

> **Android Vitals 的"用户感知 ANR"口径**：Google Play Vitals 只把 `Input dispatching timed out` 类型的 ANR 计入 User-Perceived ANR Rate，Service ANR、Broadcast ANR 等类型即使发生在前台也不计入。团队内部度量通常会统计所有前台 ANR，口径比 Vitals 更宽，做内外数据对比时要注意这个差异。

[已验证: Android Vitals 文档, support.google.com/googleplay/android-developer/answer/9844486]

Google Play 的不良行为阈值（Bad Behavior Threshold）：

| 指标 | 全机型阈值 | 单机型阈值 |
|------|-----------|-----------|
| User-Perceived Crash Rate | ≥ 1.09% | ≥ 8% |
| User-Perceived ANR Rate | ≥ 0.47% | ≥ 8% |

超过全机型阈值，Play Store 在应用详情页展示警告标签，搜索排名和推荐权重下降。超过单机型阈值但未超全机型，只在特定设备上触发警告。

[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/9844486]

### 团队内部的 ANR 率度量

Google Play 的阈值是面向所有开发者的底线。团队内部度量 ANR，通常要细分：

**按触发原因拆分**：

**系统 ANR 触发阈值（AOSP / 官方文档）**

| ANR 类型 | 系统超时阈值 | 版本差异 |
|----------|-------------|----------|
| Input dispatching | 5 秒 | 全版本一致 [AOSP `InputDispatcher.cpp`] |
| 前台 Service / FGS | `startForegroundService()` 后必须在短时间内调用 `startForeground()`；普通 Service 执行超时默认约 20 秒；shortService FGS 约 3 分钟后触发 ANR | Android 14 引入 shortService 超时；Android 15+ 对 dataSync / mediaProcessing FGS 增加 6 小时 / 24 小时后台运行限额（mediaProcessing 类型 Android 15 加入），超时未停止通常是 `RemoteServiceException` 崩溃，不计作 ANR 触发阈值 [developer.android.com FGS troubleshooting/timeout; AOSP `ActivityManagerConstants.java`] |
| 前台 Broadcast | fg ~10 秒 / bg ~60 秒 | Android 14+ 引入 soft/hard 两级超时: soft timeout 更短，超过后广播排队等待; hard timeout 到达才触发 ANR [AOSP `BroadcastQueue.java`] |
| ContentProvider | 10 秒 | 全版本一致 [AOSP `ActivityManagerService.java`] |

**团队内部监控目标（示例）**

| ANR 类型 | 内部 P90 目标 | 说明 |
|----------|-------------|------|
| Input dispatching | < 2 秒 | 用户可感知的主线程卡顿，要求最严 |
| 前台 Service | < 10 秒 | 启动和执行分别统计 |
| Broadcast | < 5 秒 | 团队内部阈值，严于系统触发线 |
| ContentProvider | < 5 秒 | 重点关注冷启动阶段 |

单独看总 ANR 率会掩盖结构性问题。比如总 ANR 率 0.3% 看起来不错，但其中 80% 是 Input ANR——主线程卡了 5 秒以上用户才会触发 ANR 对话框，实际卡顿问题远比数字显示的严重。

**按版本 / 渠道 / 机型拆分**：

- 按版本：灰度阶段的核心观测维度。新版本 ANR 率较上个版本上升 > 10%，灰度暂停
- 按渠道：国内各厂商 ROM 对前台 Service 超时处理不同，部分厂商修改了超时阈值
- 按机型：低端机（≤ 4GB RAM）的 ANR 率通常是高端机的 3-5 倍，需要单独建立基线

### ANR 采集方式对比

| 方式 | 能力 | 局限 |
|------|------|------|
| Google Play Console | 零接入，自动采集前台 ANR | 延迟约 24h，无法附加自定义上下文 |
| `FileObserver` 监听 `/data/anr/` | 可获取完整 traces 文件 | Android 10+ 大部分设备无读取权限 |
| `Handler` 超时检测 | 可在 App 内检测主线程卡顿 | 无法确认是否触发系统 ANR 对话框，属于卡顿监控 |
| 自建 APM SDK + `ActivityManager.getHistoricalProcessExitReasons()` | API 30+ 可获取退出原因和 ANR trace | 仅 API 30+，需与 Firebase / Crashlytics 互补 |

推荐组合：Google Play Console（海外）+ 自建 SDK `ApplicationExitInfo` 采集（API 30+）+ 主线程卡顿监控。详见 15.3 节 `ApplicationExitInfo` 的使用方式。

## 无崩溃用户占比（Crash-Free Users）

### 定义与计算

$$\text{Crash-Free Users} = 1 - \text{UV 崩溃率} = \frac{\text{当日未发生崩溃的 DAU}}{\text{当日 DAU}}$$

Firebase Crashlytics 默认展示这个指标。它的含义直白：每天有多少用户完全没有遇到过崩溃。

### 为什么 Crash-Free Users 比 PV 崩溃率更适合做发版门禁

Crash-Free Users 度量的是"有多少用户的体验完全不受影响"。PV 崩溃率度量的是"会话级别的崩溃频率"。两者的差异在长尾场景：

- App A：100 万 DAU，人均 2 次 Session（200 万总 Session），1 万用户各崩溃 1 次。Crash-Free Users = 99%，PV 崩溃率 = 1 万次 / 200 万 = 0.5%
- App B：100 万 DAU，人均 2 次 Session（200 万总 Session），2 万用户受影响：1 万用户各崩溃 1 次，另 1 万用户因特定 bug 反复崩溃（每人平均 5 次，共 5 万次崩溃）。Crash-Free Users = 98%（2 万去重用户受影响），PV 崩溃率 = (1 万 + 5 万) / 200 万 = 3%

Crash-Free Users 揭示了 App B 的崩溃影响面是 App A 的 2 倍（98% vs 99%）。但只看 Crash-Free Users 看不到 App B 存在严重的重复崩溃问题——PV 崩溃率 3% 远高于 App A 的 0.5%。这正是两个指标需要配合使用的原因：前者控制影响面，后者控制频率。

### 行业参考值

| 应用级别 | Crash-Free Users 目标 | 说明 |
|----------|----------------------|------|
| Play Store 不良行为线 | < 98.91%（即 User-Perceived Crash Rate > 1.09%） | 超过此值 Play Store 展示警告 [来源: Google Play Console Android Vitals] |
| 行业经验及格线 | ≥ 99.0% | 中大型 App 的常见最低标准 [匿名行业经验区间] |
| 发版门禁 | ≥ 99.5% | 常见内部发版标准 [匿名行业经验区间，各团队根据自身基线调整] |
| 头部 App 目标 | ≥ 99.8% | 超级 App 的内控标准 [匿名行业经验区间，各团队实际目标因应用类型和用户分布差异较大] |

实际操作中，Crash-Free Users 需要和 Crash-Free Session 配合使用。前者控制影响面，后者控制频率。两者同时满足才算达标。

## 稳定性看板搭建与趋势分析

### 看板的核心维度

稳定性看板不是一个图，是一组联动视图。最少需要以下四个维度：

**1. 时间趋势图**

X 轴：日期（按天或按小时）。Y 轴：Crash Rate / ANR Rate。叠加版本上线时间点和灰度比例，让版本变更和指标波动的关系一目了然。

建议双 Y 轴：左轴 Crash Rate，右轴 ANR Rate。两个指标趋势方向一致说明整体稳定；方向相反可能是新版本修了 Crash 但引入了卡顿（比如加锁过度）。

**2. 版本对比图**

按版本分组的 Crash Rate 柱状图。每个版本展示 UV 崩溃率 + PV 崩溃率 + 启动崩溃率三个指标。

关键观测点：新版本的三项指标是否同时优于上一版本。如果 UV 崩溃率下降了但启动崩溃率上升了，灰度需要暂停。

**3. Top 崩溃堆栈排名表**

按堆栈簇聚合的崩溃排名，字段至少包括：

- 堆栈摘要（首行 + 异常类型）
- 影响用户数
- 崩溃次数
- 首次出现时间
- 近 7 天趋势（↑↓→）
- 修复状态（未处理 / 修复中 / 已修复）

这个表是每天稳定性巡检的核心。Top 10 堆栈簇覆盖了 80% 以上的崩溃量——先看这张表，再决定今天修什么。

**4. 机型 / 系统版本分布**

Crash Rate 按 Android 版本和机型的热力图。用于发现特定设备上的集中问题。部分厂商 ROM 的兼容性 bug 会在热力图上呈现为局部高亮。

### 告警策略

看板是被动的，告警是主动的。最低限度的告警规则：

| 规则 | 阈值（示例） | 级别 |
|------|-------------|------|
| Crash Rate 较上一版本上升 | > 20% | P1：灰度暂停 |
| 新堆栈簇出现且影响用户数 | > 100 人 / 小时 | P1：立即排查 |
| Crash Rate 绝对值 | > 0.5%（单版本） | P2：24h 内响应 |
| ANR Rate 较上一版本上升 | > 30% | P2：版本 review |
| 单机型 Crash Rate | > 5% | P2：定向排查 |

告警不是越多越好。太多告警会导致团队麻木，太少会漏掉重要问题。P1 告警要求 5 分钟内响应，每天不超过 2 条；P2 告警要求当天响应，每天不超过 5 条。

### 看板的技术实现

稳定性看板的数据来源分两层：

**端侧采集**：
- Java Crash：`UncaughtExceptionHandler` 上报堆栈 + 设备信息 + 用户状态
- Native Crash：系统 debuggerd 生成 tombstone + `ApplicationExitInfo` 获取退出原因；App 侧也可自建 minidump 采集（需要符号表做堆栈还原，详见 20.3 节）
- ANR：`ApplicationExitInfo`（API 30+）读取 `REASON_ANR` 退出记录，配合 `getTraceInputStream()` 获取 ANR traces

**服务端聚合**：
- 堆栈聚类：按异常类型 + 堆栈前 N 帧的相似度做聚类，同一簇内的崩溃视为同一问题
- 去重逻辑：同一用户同一堆栈簇，在 5 分钟内只计一次
- 时序存储：指标数据按分钟粒度写入时序数据库，看板查询按小时或天聚合

## 扩展：稳定性 SLO 设定与行业对标

### SLO vs SLI vs SLA

三个概念的关系：

- **SLI**（Service Level Indicator）：具体指标，如 "Crash-Free Session Rate"
- **SLO**（Service Level Objective）：目标值，如 "Crash-Free Session Rate ≥ 99.8%"
- **SLA**（Service Level Agreement）：对外承诺 + 违约后果。大部分 Android 应用没有 SLA，SLO 是内部管理的核心工具

### SLO 设定的实践方法

**第一步：选 SLI**

稳定性领域推荐三个核心 SLI：

1. Crash-Free Users（度量影响面）
2. Crash-Free Session Rate（度量频率）
3. 启动崩溃率（度量关键路径）

**第二步：定目标**

目标分三档：

| 档位 | 含义 | 示例 |
|------|------|------|
| 目标值（Target） | 日常运营的及格线 | Crash-Free Users ≥ 99.5% |
| 警戒值（Alert） | 触发告警的阈值 | Crash-Free Users < 99.3% |
| 红线（Hard Limit） | 不可逾越的底线 | Crash-Free Users < 99.0% |

**第三步：建 Error Budget**

$$\text{Error Budget} = 1 - \text{SLO Target}$$

如果 SLO 是 Crash-Free Users ≥ 99.8%，那 30 天的 Error Budget = 30 × DAU × 0.2%。假设 DAU 100 万，30 天内允许崩溃的用户上限是 6 万人。超出 Error Budget 的版本，必须先修复稳定性问题再推进新需求。

### 行业对标参考

> 下表中的具体数字均为匿名行业经验区间，用于团队设定 SLO 时做横向参考。不同应用类型（社交/工具/游戏）、用户分布和采集 SDK 差异都会影响实际值，不要直接照搬。

| 应用级别 | Crash-Free Users | ANR Rate | 说明 |
|----------|-----------------|----------|------|
| Google Play 不良行为线 | < 98.91% | > 0.47% | 全机型阈值 [来源: Google Play Console Android Vitals] |
| 头部超级 App | ≥ 99.8% | < 0.1% | 内控标准 [匿名行业经验区间] |
| 大型团队发版门禁 | ≥ 99.5% | < 0.2% | 常见内部标准 [匿名行业经验区间] |
| 中型应用 | ≥ 99.0% | < 0.5% | 行业及格线 [匿名行业经验区间] |
| 长尾应用 | < 98% | > 1% | Play Store 会展示警告 |

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md]

[已验证: 结构参考文档与当前内容一致性]

对标的注意事项：

- 应用类型差异：社交 / 内容类应用使用时长长，UV 崩溃率天然偏高；工具类应用使用频次低，数值容易"好看"
- 设备分布差异：出海东南亚（大量低端机）和只做国内旗舰机型的崩溃率基准不同
- 采集 SDK 差异：用 try-catch 吞掉异常，或者不采集 Native Crash，数字会好看但问题没解决

稳定性 SLO 的价值是建立一套可量化、可追溯、可改进的治理机制，避免只追求表面数字。
