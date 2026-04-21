---
title: "性能治理工程化"
chapter: "15.10"
section: "15.10"
status: finalized
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-22"
last_verified_against: "Android Developers docs"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
tags: [governance, benchmark, ci, budget, release]
related_chapters: ["7.1", "8.1", "8.3", "9.1", "14.12", "15.3", "15.5", "15.6", "15.9"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: "2026-04-21"
reviewed_by: openclaw-task6
task9_state: reviewed
repaired_date: "2026-04-22"
repaired_by: "codex"
task9_result: pass-tech-review
task9_reviewed_date: "2026-04-22"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-22T07:35:00+08:00"
---

# 性能治理工程化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 性能治理要从“高手经验”升级成“团队机制”
- 🔹 预算、基线、回归门禁、灰度观测、发布验收缺一不可
- 🔹 Macrobenchmark / Baseline Profiles / CI 是工程化实践的关键支撑
- 🔹 性能问题需要 owner、优先级、SLO 和验收标准
- 🔹 治理体系不该只覆盖 crash / ANR，也要覆盖流畅性和启动

### 扩展（可选深入）

- 🔸 把性能 review 纳入代码评审流程
- 🔸 跨端团队 / 系统团队的协作分工模型
<!-- outline-end -->

## 为什么“大家都很重视性能”通常没用

性能治理最常见的失败方式，不是没人懂，而是人人都懂一点、但没有机制。结果就是：

- 某位同学擅长看 Perfetto，于是性能问题总靠他救火。
- 每次出大问题都紧急优化，但平时没有门禁。
- 线上指标一直看着“还行”，直到某次版本或活动把问题放大。

真正长期有效的性能治理，必须把个人能力转化成团队制度。

这也是为什么“治理工程化”和“有几个高手懂性能”不是一回事。  
前者追求的是版本质量可预测，后者往往只会在出事时表现出价值。

如果顺着全书主线往下看，本节其实是最后一层：`7/8/9` 说明用户体验为什么会坏，`15.3` 和 `15.5` 说明怎样把坏体验量化并在线上感知，`15.9` 说明如何闭环，而本节则回答“团队怎样长期把这件事做对”。

## 工程化治理最少要有五个维度

### 1. 性能预算

预算的意思是明确：

- 首页 TTFD 预算
- 核心场景 Janky Frame Rate 预算
- 冷启动预算
- ANR / OOM / crash 红线

预算最好分层写，而不是只写一个全局数字：

- **核心路径预算**：启动、首页、支付、详情等
- **平台预算**：APK 体积、Baseline Profile 命中率、关键 trace 阶段
- **稳定性预算**：ANR / crash / OOM

### 2. 基线

预算是目标，基线是现实。基线至少要分三种：

- 线下 Macrobenchmark 基线
- 线上版本基线
- 重点机型 / 重点页面基线

### 3. 回归门禁

门禁是把性能问题挡在发布前，而不是等用户投诉后再看。

常见门禁包括：

- PR / nightly 跑 Macrobenchmark
- Baseline Profile 生成与验证
- APK 大小、主线程风险扫描、启动任务检查
- 关键场景的帧时间回归阈值

不是所有指标都适合做硬门禁，但核心路径至少要有几条硬规则。  
否则“重视性能”最后还是会在赶版本时被让位给功能。

### 4. 灰度观测

线下过了，不代表线上就没问题。灰度阶段至少要看：

- 启动
- 帧率 / 慢帧
- ANR / exit
- 内存异常
- 分机型 / 分渠道差异

### 5. 发布验收

发布验收不是“功能测完了顺手看一眼性能”，而应有固定项：

- 是否满足预算
- 是否有重点机型异常
- 是否有 tail latency 抬升
- 是否有历史回归项复发

发布验收做得越固定，团队越不会在节奏紧时把它跳过。

## 推荐的组织方式

### 日常

- 用 CI 跑关键场景 Macrobenchmark
- 用静态规则和 code review 拦明显风险
- 用基础线上指标看趋势

如果团队有条件，再把“性能 review”固定成代码评审的一个问题：

- 有没有新增主线程风险？
- 有没有引入新的启动初始化？
- 有没有加大页面首屏依赖？

### 版本前

- 重点页面 / 场景做专项检查
- 核对 Baseline Profile / 启动任务 / 大版本依赖变更
- 看灰度关键指标

### 事故时

- 平台快速聚合范围
- 工程拿 trace / 栈 / case 现场
- 修复后回到基线和预算重新验收

事故处理最忌讳两件事：

- 只修表象，不改门禁
- 只做一次复盘，不把规则固化回日常机制

## 角色分工也要工程化

### App 团队

- 负责主线程、渲染、启动、内存使用、埋点质量

### 基础架构 / 平台团队

- 负责 APM 能力、采样、聚合、门禁、统一 dashboard

### 系统 / ROM / 设备协作方

- 负责调度、thermal、GPU / 驱动、系统服务行为等跨应用问题

如果角色分工不清晰，性能问题最后会退化成“谁都说有道理，但没人真正负责收口”。

## 把性能问题写成“可交付物”

一次有效的性能治理项，至少要有：

- 现象描述
- 影响范围
- 指标变化
- 初步归因
- owner
- 修复计划
- 验收标准

这里最关键的不是模板本身，而是让性能问题退出“口头经验区”，进入“可以排期、可以追踪、可以复盘”的交付区。

## 一个现实可行的成熟路径

### 阶段 1：有感知

- 上线基础指标
- 能看到版本 / 机型趋势

### 阶段 2：能回归

- 核心场景进入 Macrobenchmark / CI
- 有预算和基线

### 阶段 3：能治理

- 有固定门禁
- 有 backlog 和 owner
- 有灰度和发布验收

### 阶段 4：能持续优化

- 问题不会总靠少数专家救火
- 性能成为版本质量的一部分

## 一个现实可执行的最小组合

如果团队现在还没有完整治理体系，可以先用这个组合起步：

1. **线下**：Macrobenchmark + Baseline Profile + 基本 code review 规则
2. **线上**：启动、jank、ANR、exit 这几类基础指标
3. **流程**：固定灰度观测 + 发布验收
4. **管理**：所有性能问题都要有 owner 和验收标准

这四件事先跑起来，再逐步往更复杂的平台和自动化演进。
