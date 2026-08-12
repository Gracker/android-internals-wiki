---
title: "性能反馈回路与治理工程化"
chapter: "15.9"
section: "15.9"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1；AndroidX Benchmark 1.4.1 sources；Baseline Profiles、Android Vitals 与 Perfetto 官方文档"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: source
    path: "https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro/1.4.1/benchmark-macro-1.4.1-sources.jar"
  - type: source
    path: "https://dl.google.com/dl/android/maven2/androidx/benchmark/benchmark-macro-junit4/1.4.1/benchmark-macro-junit4-1.4.1-sources.jar"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles"
  - type: official
    path: "https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/track-events"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6"
tags: [governance, observability, benchmark, ci, budget, release]
related_chapters: ["7.1", "8.1", "8.3", "9.1", "14.9", "14.10", "15.3", "15.5", "15.6"]
consolidated_from:
  - "15.9 从采集到治理的反馈回路"
  - "15.10 性能治理工程化"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 性能反馈回路与治理工程化

## 从个人能力转为团队机制

会读 Perfetto、会分析 heap、熟悉 ART 或 SurfaceFlinger 的工程师仍然很重要。团队风险来自这些能力只存在于少数人手中：版本回归依靠临时救火，分析方法无法复用，修复完成后也没有稳定验收。

工程化治理要固定五类决策：

- 哪些用户旅程属于 Critical User Journey（CUJ）；
- 每条旅程采用什么指标、预算和设备；
- 什么变化需要评审、阻断、灰度或回滚；
- 异常由谁调查，证据如何交接；
- 修复通过什么线下测试和线上指标验收。

机制的目标是可重复决策。不同工程师面对同一份数据，应得到相近的发布结论；对结论有异议时，也能查到预算、基线、例外和证据。

## 从信号到验收的反馈回路

监控平台持续收到数据，不等于问题正在被治理。一条异常只有完成“发现 → 归因 → 修复 → 验收”，才会改变后续版本。回路中需要同时保留四类对象：

| 对象 | 回答的问题 | 不能单独回答 |
|---|---|---|
| 指标与分布 | 影响范围、趋势和异常分群 | 单个样本为何变慢 |
| 事件与会话 | 某次操作经历了哪些业务阶段 | 调度、锁和跨进程根因 |
| trace、profile、heap、ANR trace | 现场执行和资源关系 | 对全部用户的影响 |
| 工单与发布记录 | 谁处理、何时交付、怎样验收 | 运行时技术事实 |

一条可执行的流程包含八个阶段：

1. **采集**：按 §15.3 的指标合同和 §15.5 的平台边界记录信号。
2. **采样**：把概率已知的基线样本与异常触发的诊断样本分开。
3. **聚合**：展示分母、样本量、缺失率、schema 和采样配置。
4. **归因**：从异常分群进入正常/异常样本，用 trace、源码和对照实验验证假设。
5. **告警**：同时检查绝对预算、相对回归、最小样本和数据健康。
6. **流转**：为问题指定当前 owner、状态、时限和下一项动作。
7. **修复**：记录改动机制、风险、开关、回滚条件和守护指标。
8. **验收**：在线下同协议复测，并在线上同分群确认用户结果。

若工单缺少指标合同、可回查样本、当前 owner、修复版本或验收条件，流程就停在了中间。告警关闭也不能自动解释为修复成功；采样切换、上报中断或用户构成变化同样会让曲线下降。

## 五个支点

### 1. 预算：先固定测量契约

性能预算不能只写“启动 2 秒以内”。至少包含：

| 字段 | 示例含义 |
|---|---|
| CUJ | 冷启动到首页 TTID、warm start 到 TTFD、Feed 连续滑动 |
| 指标 | `timeToInitialDisplayMs`、frame overrun、峰值 RSS、包体积 |
| 人群/设备 | 低内存设备、主力 SoC、API 26、API 37 |
| 构建与编译状态 | benchmark/release 变体、R8 状态、Baseline Profile 模式 |
| 统计口径 | median、P90、失败率、样本数、窗口 |
| 预算 | 绝对上限、相对回归上限或两者组合 |
| 动作 | 提醒、阻断合入、停止灰度、回滚 |
| owner | 指标 owner、CUJ owner、批准例外的角色 |

预算可以分为三层：

- **用户体验 SLO**：线上启动、帧、ANR、crash、OOM、耗电等用户结果；
- **实验室回归预算**：固定设备与场景下的 Macrobenchmark、内存和 CPU 结果；
- **资源预算**：下载大小、安装大小、DEX/资源增长、启动初始化和后台资源。

三层不能互相代替。线下启动稳定不代表全部厂商设备稳定；线上曲线稳定也可能由灰度量小或采样延迟造成。发布决策要说明使用了哪一层证据。

### 2. 基线：记录比较条件

预算描述目标，基线描述某组条件下已经测得的水平。更新基线时至少保留：

- git commit、version code、依赖锁文件与构建变体；
- benchmark/library/AGP/JDK 版本；
- 设备型号、serial 或实验室资产 ID、Android build fingerprint；
- 电量、温度、刷新率、网络与测试数据；
- compilation mode、startup mode、迭代数；
- JSON 结果、每轮 trace 和失败日志。

基线必须与候选版本使用同一设备和同一配置。把 Pixel 的结果与另一品牌设备比较，把 `CompilationMode.None` 与 `Partial` 比较，或把 debug 与 benchmark 变体比较，所得差值都包含测试条件变化。

基线也不是目标。某个历史版本已经超出 SLO 时，不能因为它“当前如此”就继续接受同等表现。预算变更与基线更新应由不同操作完成，并留下评审记录。

### 3. 回归门禁：按证据确定强度

门禁可以分三类：

| 类型 | 适合内容 | 失败动作 |
|---|---|---|
| 确定性门禁 | CUJ 脚本可运行、APK/AAB 含 profile、包体积、禁用 API、缺少 mapping/symbol | 直接阻断 |
| 测量门禁 | 启动、帧、内存、CPU benchmark | 达到样本与噪声规则后阻断；其余标记需复测 |
| 线上门禁 | 灰度 ANR/crash、启动 tail、慢帧、OOM、退出原因 | 暂停扩量、关闭开关或回滚 |

Benchmark 是带噪测量。Android 官方 CI 文档明确提醒，它不像普通测试那样天然只有 pass/fail。可靠门禁要先测量设备自身的历史噪声，再规定：

- 候选与基线的最小重复次数；
- 可以比较的设备池；
- 允许的绝对差和相对差；
- 测量失败、thermal throttle、低电量和设备离线如何处理；
- 何时自动复测，复测几次后转人工判断；
- 哪些 trace 和 JSON 必须归档。

PR 可以运行 dry run，验证脚本、安装和导航是否正常。性能数值适合在稳定真机池的 nightly、合入队列或发布流水线评估。官方强烈不建议用模拟器结果代表用户性能；模拟器可用于 CUJ 脚本冒烟和部分 profile 生成。

不要在 CI 中全局压制 Macrobenchmark 的配置错误。target app 为 debuggable、未设为 profileable、设备为 emulator 或低电量时，库会报告可能损害测量的错误。单项抑制需要记录原因和到期时间。

### 4. 灰度观测：验证设备分布

灰度需要覆盖：

- TTID、TTFD 和关键页面 tail；
- frame overrun、慢帧/冻帧与交互失败；
- user-perceived ANR、crash、OOM 与 `ApplicationExitInfo`；
- 内存、后台 CPU、WakeLock 与网络异常；
- 设备型号、SoC/GPU、SDK、渠道、地域和实验分群。

灰度组与对照组要处于相同时间窗，并控制版本、设备和远程配置。服务端延迟、活动流量、网络变化和实验开关都可能改变客户端结果。只看全局平均值会隐藏少数高流量机型或低内存设备。

Google Play 的 Android Vitals 提供发布质量信号，自建指标提供更细场景与更快回查。两者分母、延迟和覆盖范围不同，门禁页面要标明数据源。Play 的阈值可作为外部红线，内部预算通常要更早发现趋势。

灰度规则应预先写明扩量、暂停和回滚条件。临时调整条件要进入发布记录，避免数据出现后再选择更宽松的口径。

### 5. 发布验收：把结论写回版本

发布验收记录至少包含：

- CUJ 线下结果与预算结论；
- profile、mapping、native symbols 等构建产物检查；
- 灰度指标、样本量、观察窗口和重点设备；
- 未解决问题、已批准例外和到期日；
- 发布/暂停/回滚决定及批准人；
- 上线后复查时间和 owner。

验收结果关联 commit、build、benchmark JSON、trace、dashboard 和工单。后续发现回归时，可以区分“当时没有信号”“规则没有触发”“例外放行”和“发布后环境变化”。

## Benchmark 与 Profile 在治理中的位置

Macrobenchmark 的工程配置、迭代、编译模式和统计处理由 §14.9 与 §15.6 统一说明。本节只保留治理要求：CI 必须把目标 APK、测试 APK、设备与环境 manifest、原始 JSON、每轮 trace、失败日志和统计程序版本绑定到同一次运行；门禁程序先验证条件一致与数据质量，再比较绝对预算、相对回归和历史噪声。临界结果在同一设备复测，阻断结果附正常与异常 trace。

Baseline Profile 与 Startup Profile 也分成三项验收：规则是否覆盖稳定 CUJ、产物是否正确打包、真机上的目标场景是否获得收益。profile 文件存在不能证明目标代码已完成预期编译，更不能证明用户指标改善。生成规则、检查产物和测量收益是三个独立动作；具体工具操作继续由 §14.9 与启动专题维护。

设备系统更新、电池老化、存储状态变化、Benchmark 升级或测试脚本变更后，应重新评估噪声并建立有迁移记录的新基线，不能静默沿用旧结果。

## 代码评审中的性能检查

以下变化应触发性能影响说明：

- `Application`、ContentProvider、App Startup initializer 或首个 Activity 的初始化；
- 主线程文件/数据库/网络、同步 Binder、锁和反射；
- 图片、序列化、数据库 schema、缓存和大数据路径；
- View measure/layout/draw、Compose state/recomposition 与列表绑定；
- 新 SDK、动态特性、native 库、资源或包体积增长；
- 后台 Job、alarm、WakeLock、定位、传感器和轮询；
- Baseline/Startup Profile 的 CUJ 或构建配置变化。

PR 模板可以要求作者填写：

- 受影响 CUJ 与线程；
- 新增工作在调用链中的位置；
- 预期复杂度、数据规模和设备边界；
- 已运行的 benchmark/trace 或无需测量的理由；
- 线上观察指标和失败开关。

评审线索用于决定是否测量，不能只凭“看起来可能慢”要求重写。命中高风险路径时补 Macrobenchmark、Microbenchmark 或系统 trace；影响低且路径不频繁时，记录判断即可。

## 角色与交接

| 角色 | 主要责任 |
|---|---|
| Feature/CUJ owner | 场景脚本、代码修复、业务正确性、线上验收 |
| 性能平台团队 | 指标契约、真机池、benchmark 工具、采样与 dashboard |
| Release/值班角色 | 灰度节奏、门禁执行、暂停与回滚 |
| 系统/ROM 团队 | framework、system_server、调度、thermal、GPU/驱动问题 |
| 数据/服务端团队 | 服务延迟、实验分群、数据完整性与查询成本 |

每个问题只有一个当前 owner。跨团队协作可以有多名参与者，但调查状态、下一动作和时限由当前 owner 维护。转交给系统或厂商团队时，证据包至少包含：

- app build、复现步骤与发生率；
- 设备型号、Android build fingerprint、kernel build；
- 正常与异常对照；
- Perfetto/bugreport/tombstone 等现场；
- 已排除的 app 侧假设；
- 期望对方验证的具体问题。

“trace 里 system_server 很忙”不足以完成转交。需要沿 Binder flow、线程状态、锁、I/O 或调度证据指出可调查入口。涉及内核的判断固定到 `android17-6.18-2026-06_r6`；厂商设备按设备对应源码复核。

### 工单状态与验收责任

性能工单可以使用 `detected → triaged → investigating → fixing → validating → resolved`。`false-positive`、`duplicate`、`cannot-reproduce` 与 `accepted-risk` 应作为有理由、有操作者和时间戳的终态，不能全部写成“关闭”。

工单至少携带指标合同、异常窗口、基线与回归版本、受影响分群、样本量、采样配置、正常/异常证据、已确认事实、候选假设、当前 owner、计划版本和回滚条件。进入 `validating` 前，必须先写线上验收窗口、最小样本和成功条件，避免结果出现后再挑选口径。

## 证据连接与数据生命周期

聚合图、单次事件、诊断制品和发布记录需要稳定连接，但连接键不能进入高基数指标标签：

| 键 | 用途 |
|---|---|
| `event_id` | 客户端重试幂等与单事件去重 |
| `session_id` / `page_instance_id` | 关联一次会话或页面实例 |
| `process_instance_id` | 区分进程生命周期，避免只依赖会复用的 PID |
| `trace_id` / artifact ID | 从异常事件进入受控保存的 trace、heap 或 tombstone |
| `build_id` / `version_code` | 对齐二进制、mapping、symbols 和发布记录 |
| `event_schema_version` / `sampling_config_version` | 解释字段、算法与采样策略变化 |

进程内阶段耗时使用明确的 monotonic clock，跨设备和发布窗口使用 UTC wall time；两类时间戳不能直接相减。schema 改变单位、分母或含义时升版本，生产者、消费者、看板和告警在同一变更记录中写明兼容窗口。

存储按用途分层：近期聚合和可检索事件服务告警，降采样趋势用于长期比较，trace、heap、tombstone 等高敏附件单独加密、缩短保留期并记录访问审计。每个数据源都要有 owner、日量、保留期、删除机制和停采条件。

多业务线共享平台时，`tenant_id` 必须来自受信任的服务端身份或发布配置。查询、缓存、附件、导出、告警和审计全程执行 tenant + role 校验；在 ID 前加租户前缀只能避免碰撞，不能构成访问隔离。

## 例外机制

业务可以在明确条件下接受性能回归。例外记录必须包含：

- 指标、设备/CUJ、回归量和用户影响；
- 放行原因、补偿措施与风险；
- owner、批准人和到期日期；
- 计划修复版本或重新评估条件；
- 灰度观察与回滚规则。

例外到期后自动恢复原门禁。若团队决定永久调整预算，应提交预算变更评审，展示用户影响、历史趋势和替代指标。不能通过更新基线隐藏回归，也不能无限延长同一例外。

## 日常、版本和事故

### 日常

- PR dry run 验证 CUJ，风险变更补充性能影响说明；
- nightly 在固定真机跑关键 Macrobenchmark；
- 趋势任务检查设备噪声、结果缺失和 profile 产物；
- 线上 dashboard 按版本和设备分群审计。

### 发布前与灰度

- 冻结 benchmark、metric schema 和 sampling config 版本；
- 生成并检查 Baseline/Startup Profile；
- 运行 release candidate 的完整 CUJ 集；
- 检查未关闭工单、例外和回滚开关；
- 灰度阶段按预设规则扩量或暂停。

### 事故

- 保留异常窗口、配置和证据；
- 通过暂停扩量、开关、降级或回滚限制影响；
- 比较正常/异常分群并验证归因；
- 修复后同时复测线下 CUJ 与线上指标；
- 只把稳定、可重复的检测方法加入日常门禁。

事故复盘的产物可能是新 CUJ、指标、告警、lint、profile journey 或操作手册。若问题依赖偶发外部条件，强行加入不稳定硬门禁会制造噪声；此时更适合线上预警或人工专项。

## 从小规模开始

一个可运行的最小版本包括：

1. 选择启动、首页和一个高频交互作为 CUJ。
2. 为每条 CUJ 写指标契约、预算和固定真机。
3. PR 跑脚本 dry run，nightly 跑完整 Macrobenchmark。
4. 生成 Baseline/Startup Profile 并检查发布产物。
5. 灰度观察启动、帧、ANR、crash、OOM 和退出原因。
6. 所有回归进入带 owner、验收和到期时间的工单。

稳定运行后再增加设备、场景和硬门禁。门禁数量不是成熟度指标；可靠覆盖高价值 CUJ、能够解释失败并持续验收，才说明机制有效。

## 与其他章节的关系

- §7、§8、§9 解释流畅性、启动和 ANR 的平台机制。
- §14.9 说明 Macrobenchmark 的用法与回归门禁边界。
- §15.3 定义性能指标契约。
- §15.5 讨论线上监控和保护开关。
- §15.6 讨论测试设计与统计可靠性。
- 本节把这些能力连接到采集、归因、工单、发布和验收流程，不再重复各工具的 API 教程。

平台源码锚点固定为 Android 17 / API 37 / `android-17.0.0_r1`。Benchmark、Baseline Profile 与 ProfileInstaller 属于 AndroidX/构建工具，版本应在项目依赖和基线记录中单独固定。涉及 CPU 调度、Binder driver、cgroup 或 thermal 的内核证据，使用 `android17-6.18-2026-06_r6`。

## 参考资料

- [Android 官方：Benchmark overview](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [Android 官方：Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Android 官方：Benchmark in CI](https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci)
- [Android 官方：Android Vitals](https://developer.android.com/topic/performance/vitals)
- [Android 官方：Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Android 官方：Create Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile)
- [Android 官方：Debug Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/debug-baseline-profiles)
- [Android 官方：Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
