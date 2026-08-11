---
title: "Google Android Bench：AI 编码能力评测方法论"
chapter: "15.10"
section: "15.10"
status: ready-for-review
drafted_date: "2026-07-17"
applicable_versions: "Android 工程任务（平台结论最高 Android 17 / API 37；评测框架版本单独固定）"
last_verified: "2026-07-30"
last_verified_against: "Android Bench 官方 methodology（Harbor + mini-swe-agent v2）；归档仓库 commit 65a86bf41e45dde517a65d6e65a6dc7cdd2063ea"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/bench/methodology"
  - type: official
    path: "https://android-developers.googleblog.com/2026/03/elevating-ai-assisted-androi.html"
  - type: source
    path: "https://github.com/android-bench/android-bench/tree/65a86bf41e45dde517a65d6e65a6dc7cdd2063ea"
  - type: source
    path: "https://github.com/android-bench/android-bench/blob/65a86bf41e45dde517a65d6e65a6dc7cdd2063ea/docs/tech_report.md"
  - type: source
    path: "https://github.com/android-bench/android-bench/blob/65a86bf41e45dde517a65d6e65a6dc7cdd2063ea/docs/guide.md"
  - type: dataset
    path: "https://hub.harborframework.com/datasets/android-bench/android-bench/latest"
tags: ["android-bench", "ai-evaluation", "coding-agent", "methodology"]
related_chapters: ["15.6", "15.9"]
---

# Google Android Bench：AI 编码能力评测方法论

## Android Bench 测量什么

Android Developers 在 2026-03-05 发布首版 Android Bench。每个任务提供真实 Android 工程上下文与问题描述，agent 在仓库中生成代码修改，verifier 再通过构建和测试判断 patch 是否解决问题。

它比通用代码问答多出几类 Android 约束：

- Kotlin/Java 与 Android API、Jetpack API 的版本关系；
- Gradle、AGP、多模块和依赖配置；
- Compose、View、Coroutines/Flow、Room、Hilt 与 Navigation；
- 配置变化、折叠屏、runtime permission、camera、media、wearable 等平台场景；
- 部分任务需要理解截图等多模态输入。

测量对象仍然有限：给定 issue、已有仓库和自动化验收条件下的 patch 成功率。它不覆盖从空目录创建完整产品、长期维护、发布运营、无测试需求的架构取舍，也不自动评价代码可读性、安全性、功耗或性能质量。

## 数据集从哪里来

当前官方 methodology 页写明：100 个任务从 38,989 个 pull request 的候选池及人工补充流程中形成。仓库需要包含 Android app 或 library 代码，并至少有 500 GitHub stars；候选 PR 需要已经合并、修复 issue、带有 unit 或 instrumentation test，且变更位于最近三年。

自动筛选后还有两轮人工复核：

1. QA 检查 base 与目标 patch 的构建/测试行为、问题描述是否提供足够上下文、变更是否超出描述，并估计人工完成难度。
2. Android 专家检查任务是否具有足够复杂度和 Android 相关性。

某些 Android 领域在 GitHub 样本中不足，维护者会为合适 PR 补测试、补 issue，或重写过于简略的问题描述。这样的任务仍需经过专家复核。数据因此不等于“从公开 PR 原样随机抽 100 个”，带有明确的策展与补充策略。

### 当前官方组成

| 维度 | 当前 methodology 页公布的数据 |
|---|---:|
| Kotlin | 71% |
| Java | 25% |
| Compose UI 任务 | 41% |
| View UI 任务 | 59% |
| benchmark 中 library 项目 | 58% |
| 小于 27 行的变更 | 46% |
| 27—136 行的变更 | 33% |
| 大于 136 行的变更 | 21% |
| patch 中位数 | 32 行 |
| 最大 patch | 435 行 |

这些比例不是 Android 开发生态的自然分布。官方同时指出，采集到的 GitHub Android 仓库以 app 为主（63%），benchmark 则更偏 library；这项选择增加了模块化与 API 约束，也改变了外推范围。

## 一个任务怎样执行

Android Bench 将 inference 与 evaluation 分开：

1. inference agent 读取 issue、base commit 和仓库内容；
2. agent 使用工具检查、编辑和测试，输出 patch；
3. verifier 在固定任务环境应用 patch；
4. verifier 构建工程并运行任务的 acceptance tests；
5. 每个任务输出通过/失败以及诊断状态。

归档仓库的 user guide 要求有效任务满足：

- 问题描述清楚；
- base commit 与容器环境可复现；
- 验收测试在 base 上失败，在 canonical/oracle patch 上通过；
- 测试不依赖未同步的 UI timing 等易抖动条件。

Oracle Agent 的作用是验证任务与 verifier，不能证明测试覆盖了需求的全部语义。模型仍可能找到测试盲区；维护者通过成功轨迹人工审计来发现 reward hacking 或描述不足。

## 方法版本不能混用

Android Bench 发布后已经换过执行框架：

| 版本 | agent 与执行接口 | 资料状态 |
|---|---|---|
| 2026 年 3 月首版 | mini-swe-agent v1；模型以 Markdown code block 输出 shell command，由正则提取执行 | 归档技术报告与首版排行榜 |
| 当前 methodology | Harbor；mini-swe-agent v2；provider API 的 native tool calling；Android-specific system steering | 当前官方口径 |

mini-swe-agent v2 只执行通过工具 API 提交的 bash 调用。若沿用 v1 prompt，让模型把命令写成 Markdown 文本，命令不会执行。官方因此更新了 system instruction 与 Pydantic tool schema。

旧 `android-bench/android-bench` 仓库已在 2026-07-08 归档，当前数据集迁移到 Harbor Hub。复现实验时要同时记录：

- dataset 名称、版本或 digest；
- Harbor/旧 harness commit；
- mini-swe-agent 版本、system prompt 与 tool schema；
- model provider、完整 model ID、endpoint 与运行日期；
- temperature/seed（provider 支持时）、turn/time/cost budget；
- Docker image digest、JDK、Android SDK、AGP、Gradle 与 KVM 环境。

只写“使用 Gemini/Claude/GPT”无法复现。模型 backend、agent shell、prompt、工具调用和预算都会改变得分。

## verifier 到底判定什么

归档实现把任务结果记录为二元 score：

- `1.0 / PASSED`：patch 成功应用，工程构建完成，要求的测试通过；
- `AGENT_FAILED_BUILD`：模型 patch 导致构建失败；
- `AGENT_FAILED_TEST`：构建通过，验收测试失败；
- `NO_PATCH_GENERATED`：agent 没有生成可识别 patch；
- `EVAL_ERROR`：容器或 verifier 等评测基础设施失败；
- `SKIPPED`：任务按运行参数被跳过。

前三类与未生成 patch 可以归到 agent 未解决；`EVAL_ERROR` 要单独修复或重跑，不能静默算成模型能力失败。报告还要公开 attempted、evaluable、passed、infra error 和 excluded 的数量，防止不同分母产生不可比 pass rate。

测试通过说明 patch 满足当前 acceptance tests。它没有证明 patch 是 canonical 实现，也没有证明没有性能、安全、可维护性或兼容性问题。对高风险任务可以在 verifier 后增加静态检查、benchmark、人工 review 或隐藏测试，但这些附加层必须写进评测协议。

## pass@1 与重复运行

单个任务的一次运行只有通过或失败。一次完整运行的 pass@1 可写成：

\[
\text{pass@1}=\frac{\text{通过的可评任务数}}{\text{可评任务总数}}
\]

重复运行时，任务 \(i\) 有 \(n_i\) 次有效运行，其中 \(c_i\) 次通过；整体估计量是各任务 \(c_i/n_i\) 的平均值。模型输出具有随机性，一次 100-task run 不能描述稳定能力。`EVAL_ERROR` 的重跑和分母规则必须预先规定，model timeout、build failure 和 test failure 则属于模型/agent 配置的结果。

首版技术报告对模型重复运行，并用任务与运行的分层 bootstrap 计算 95% confidence interval。报告明确指出，多组模型区间重叠；该规模当时只能检测约 10 个百分点的绝对 pass-rate 差异。

当前官方页计算 cost、token 和 latency 时，以一次完整 100-task suite 的总量为单位，再对同一模型的 10 次 run 取算术平均。复现实验要保存每任务原始结果，不能只保留排行榜平均值。

### 成本、token 与时延的偏差

- **Cost** 使用运行时 provider 定价，跨日期会受价格调整影响；
- **Token** 依赖 inference engine/provider 返回值，缓存与共享 prompt 可能没有统一计量；
- **Latency** 包含 API 网络传输，受运行地域和 endpoint 负载影响；
- 失败较早的模型消耗更少，低成本和低时延可能来自没有完成任务。

因此，资源指标只适合在 pass rate 接近的配置间比较。团队还可以补充 cost per solved task、成功任务 latency 与失败任务 latency；passed 为 0 时，cost per solved task 没有定义。

## 数据污染与测试投机

真实 GitHub PR 让任务贴近工程现场，也带来训练数据污染风险。当前项目采取两项主要措施：

- 在任务文件中加入 BIG-BENCH canary string，劝阻训练语料收录；
- 人工审计成功 trajectory，检查 patch 是否来自有效修复。

canary 无法证明模型从未见过公开 issue、PR 或代码。公开 dataset 也使发布后的模型可能针对 benchmark 优化。报告应区分任务发布日期、模型训练/知识 cutoff（provider 公布时）、公开任务与新建任务结果，并维护未公开的 shadow set。

验收测试同样可能存在盲区。创建任务时应反复验证 base 失败、oracle 通过、失败原因稳定，并检查 agent 是否能修改测试、构建脚本或 verifier 路径。任何防篡改措施都要通过实际文件权限和 patch allowlist 验证，不能只依赖 prompt 中的“不要修改测试”。

## 怎样读公开排行榜

### 排名是一个配置的结果

公开分数对应“model + endpoint + agent + prompt + tools + budget + dataset + verifier”。更换 Android Studio agent、Claude Code、Codex、Gemini CLI 或自研 context system 后，即使底层模型相同，结果也可能变化。

### 小分类不适合过度解读

100 个任务再按 Compose、library、bugfix 或许可类型分组后，置信区间会变宽。几分差距不能支持“模型 A 更懂 Compose”一类强结论，除非差异通过预先规定的统计检验，并在新任务上复现。

### Android 版本不是唯一变量

任务跨 Android、Jetpack、Gradle 与第三方库版本。一个 model 得分高，可能来自 Kotlin/Gradle/tool-use 能力，也可能来自 agent 更会搜索和运行测试。Android Bench 不是 Android 17 compatibility suite，更不验证 AOSP framework 或 kernel 实现。

### 首版结果只作为历史快照

首版博客写的是模型完成率约 16%—72%，Gemini 3.1 Pro 位于当时榜首。模型版本、执行框架和数据集已经变化；引用该结果必须标明 2026-03 首版，不能写成长期选型结论。

## 团队怎样建立私有评测

公共 benchmark 用于观察通用能力，采购或工具选型还应增加本团队 shadow set。

### 任务选择

- 从近期已修复 issue 中选择有明确 acceptance criteria 的任务；
- 覆盖团队的 Compose/View、Gradle、数据、网络、性能和兼容性工作；
- 保留低频高风险任务，不按 PR 数量机械抽样；
- 将测试、base commit、oracle patch 和环境镜像版本化；
- 让不参与 agent 运行的人维护隐藏验证。

### 对照实验

每轮只改变一个变量：

- 比较 model 时固定 agent、prompt、tools 和 budget；
- 比较 agent 时固定 model、endpoint 和 dataset；
- 比较成本预算时固定其余配置；
- 每个配置重复运行，并随机化任务顺序；
- 基础设施错误按预设规则重跑，重跑次数公开。

### 报告字段

| 维度 | 建议输出 |
|---|---|
| 正确性 | resolved/evaluable、95% CI、按任务类别分层 |
| 稳定性 | 同一任务多次运行的通过比例与分歧任务 |
| 失败类型 | build、test、no patch、timeout、infra error |
| 资源 | 总 cost、cost/solved、token、成功/失败 latency |
| 工程质量 | 人工 review、改动范围、测试增量、安全与性能风险 |
| 可复现性 | dataset、image、model、agent、prompt、budget 的精确版本 |

模型选型不能只按总分排序。团队还要考虑数据策略、代码许可、私有仓库访问、可审计性、IDE/CI 集成、速率限制和供应商稳定性。

## 与 Android 17 源码锚点的关系

这里讨论的是评测框架，不含平台或 kernel 机制结论。涉及 Android API 行为时，最高版本固定为 Android 17 / API 37 / `android-17.0.0_r1`；Android Bench 自身必须按 dataset 和 harness 版本固定，不能用 AOSP tag 替代。由于不涉及内核机制，也不引用 `android17-6.18-2026-06_r6`。

## 参考资料

- [Android Developers：Android Bench methodology](https://developer.android.com/bench/methodology)
- [Android Developers Blog：首版 Android Bench 发布说明（2026-03-05）](https://android-developers.googleblog.com/2026/03/elevating-ai-assisted-androi.html)
- [Android Bench 归档仓库，commit `65a86bf`](https://github.com/android-bench/android-bench/tree/65a86bf41e45dde517a65d6e65a6dc7cdd2063ea)
- [归档技术报告](https://github.com/android-bench/android-bench/blob/65a86bf41e45dde517a65d6e65a6dc7cdd2063ea/docs/tech_report.md)
- [归档 User Guide](https://github.com/android-bench/android-bench/blob/65a86bf41e45dde517a65d6e65a6dc7cdd2063ea/docs/guide.md)
- [Harbor Hub：Android Bench dataset](https://hub.harborframework.com/datasets/android-bench/android-bench/latest)
