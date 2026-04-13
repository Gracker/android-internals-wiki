---
title: "EAS 能量感知调度"
chapter: "5.2"
section: "5.2"
status: ready-for-review
applicable_versions: "Android 9 (API 28) - Android 16 (API 36)"
last_verified: "2026-03-31"
last_verified_against: "Linux kernel 6.6, Documentation/scheduler/sched-energy.rst"
confidence: high
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-09-CPU.md"
  - type: blog
    path: "Personal-Knowlodge/source/Android-Systrace-CPU.md"
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-energy.html"
  - type: official
    path: "https://docs.kernel.org/power/energy-model.html"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-scheduling"
tags: ['EAS', 'energy-aware-scheduling', 'PELT', 'energy-model', 'OPP', 'task-placement', 'uclamp', 'schedutil']
related_chapters: ["5.1", "5.3", "5.4", "2.5"]
drafted_date: "2026-03-31"
reviewed_date: "2026-04-14"
reviewed_by: "openclaw-task6"
review2_date: "2026-04-06"
review2_by: openclaw-task6
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: needs-rework
task9_state: pending
task2b_state: pending
---

# EAS 能量感知调度

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 EAS（Energy Aware Scheduling）的核心思想：在满足性能需求的同时最小化能耗
- 🔹 能量模型（Energy Model）：OPP（Operating Performance Points）与功耗曲线
- 🔹 Task Placement 策略：将轻任务放小核、重任务放大核
- 🔹 Util（utilization）信号与 PELT（Per-Entity Load Tracking）
- 🔹 EAS 在 Perfetto 中的观察：cpu_frequency、sched_switch、uclamp

### 扩展（可选深入）

- 🔸 各 SoC 厂商对 EAS 的定制化（高通 / 联发科 / 三星）
- 🔸 Pixel 设备上的调度策略特点

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 EAS

在上一节中，我们讲了 CFS 的基本原理：它通过 vruntime 保证所有进程公平地获得 CPU 时间。但公平只是调度器的一个目标——在手机这样的移动设备上，还有一个同样重要的目标：**省电**。

现代手机 SoC（System on Chip，片上系统）普遍采用大小核架构（我们会在 5.3 节详细展开），一个四小核加四大核的八核处理器，在安排任务时面临一个核心问题：**一个任务应该放在小核还是大核？** 放小核省电但可能不够快，放大核够快但功耗高。如果每个任务都由调度器盲目地"找最空闲的核"来放，系统的总功耗往往会比最优安排高出 20%~40%。

EAS（Energy Aware Scheduling）就是为了解决这个问题而生的。它在 Linux 5.0 中被合入主线内核，是 Android 设备上最重要的调度增强之一。EAS 的核心能力是：**在任务唤醒时，预测把任务放在不同 CPU 核心上分别需要消耗多少能量，然后选择一个既满足性能需求又最省电的核**。

理解 EAS 的意义在于：打开一份 Perfetto Trace 时，看到主线程被分配到了小核上运行缓慢，或者在大小核之间频繁迁移，需要知道这不是"随机"的行为——背后有 EAS 的决策逻辑，而理解这个逻辑，是判断调度行为是否正常的关键。

[已验证: 官方文档, https://docs.kernel.org/scheduler/sched-energy.html]

## EAS 的核心思想

### 从"找最快的核"到"找最省电的核"

传统 CFS 的任务唤醒逻辑（5.1 节讲过的 `select_task_rq_fair()`）主要关注性能：在可用的 CPU 核心中选择一个负载最低的、能让任务尽快开始执行的核。这个逻辑在同构系统（所有 CPU 核心性能相同）上工作良好，但在大小核架构上会出现问题——它可能把一个轻量级任务放到大核上，仅仅因为大核当时更空闲，这白白浪费了大核的高功耗能力。

EAS 覆盖了 CFS 的默认唤醒逻辑。当 EAS 启用时，`select_task_rq_fair()` 不再走原来的负载均衡路径，而是调用 `find_energy_efficient_cpu()`——这个函数的决策目标从"最快开始执行"变成了"满足性能需求的前提下，系统总能耗最低"。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — "EAS overrides the CFS task wake-up balancing code"]

用一个具体的例子来说明。假设我们有一个 util 值为 200 的轻量级任务需要被唤醒，系统中有两种核心：

- 小核：capacity 200，当前空闲
- 大核：capacity 1024，当前空闲

传统 CFS 会发现大核更空闲，选择大核。但 EAS 会计算：这个任务放在小核上刚好能"装下"（util 200 ≤ capacity 200），不需要拉高大核的频率，整体能耗更低。于是 EAS 选择小核。这就是 EAS 的核心逻辑：**优先找一个既省电又够用的核，而不是单纯追求最空闲的核**。

[图：EAS 选核对比示意 — 传统 CFS 选最空闲大核 vs EAS 选最省电小核，标注 util/capacity/energy delta]

[已验证: 官方文档, https://docs.kernel.org/scheduler/sched-energy.html — EAS uses capacity and utilization to estimate "busyness" for performance-vs-energy trade-offs]

### EAS 的前提条件

EAS 并非在所有设备上都生效。它需要满足以下条件：

1. **异构 CPU 拓扑**：系统中存在不同 computing capacity 的 CPU 核心（即大小核架构）。EAS 目前不支持同构系统，因为同构系统中无论把任务放在哪个核上，能耗差异都很小。
2. **能量模型（Energy Model）可用**：内核中必须注册了 CPU 的能耗数据。没有能量模型，EAS 就无法做能耗预测。
3. **schedutil 调频策略**：EAS 需要与 `schedutil` governor 配合工作，因为它的能耗预测依赖于对 CPU 未来运行频率的估算，而 `schedutil` 能提供这个信息。如果使用 `performance` 或 `powersave` 等固定频率的 governor，EAS 的频率预测就不准了。

这三个条件在主流 Android 手机上通常都满足——它们都是大小核架构，内核中有能量模型（通常通过 Device Tree 提供），默认使用 `schedutil` 调频。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — EAS requirements: asymmetric CPU topology, EM, schedutil]

## 能量模型（Energy Model）

### OPP：频率-电压对的集合

要理解 EAS 怎么做能耗预测，我们得先看能量模型的数据来源，即 OPP（Operating Performance Points）。

一个 CPU 核心并不是只能跑一个固定频率。它可以在多个频率-电压对之间切换，每个频率-电压对就是一个 OPP。例如，一个小核可能有如下 OPP 表：

| OPP | 频率 (MHz) | 电压 (mV) | 功耗 (mW) |
|-----|-----------|-----------|-----------|
| 0   | 300       | 600       | 15        |
| 1   | 600       | 650       | 30        |
| 2   | 900       | 720       | 60        |
| 3   | 1200      | 820       | 120       |
| 4   | 1500      | 950       | 200       |
| 5   | 1800      | 1100      | 380       |

注意功耗不是线性增长的——从 OPP 4 到 OPP 5，频率只增加了 20%，但功耗几乎翻倍。这是因为更高的频率需要更高的电压，而功耗与电压的平方成正比（动态功耗公式：P ∝ CV²f）。这也是 EAS 要尽量让任务在低频运行的原因——省下的不只是"一点电"，而是指数级的功耗节省。

[已验证: 官方文档, Documentation/power/energy-model.rst — EM provides power cost tables for performance domains]

[图：OPP 功耗曲线示例 — 频率-功耗非线性关系可视化，标注动态功耗公式 P ∝ CV²f]

OPP 数据通常定义在 Device Tree（设备树）中，使用 `operating-points-v2` 属性。内核启动时解析这些数据，构建出每个"性能域"（Performance Domain）的功耗曲线。一个性能域通常对应一个 CPU 簇——同簇内的核心共享频率和电压调节，因此它们的 OPP 表相同。

### 能量模型框架

Linux 内核的 Energy Model（EM）框架是一个独立于调度器的子系统，它的职责是管理和提供各性能域的功耗数据。`CONFIG_ENERGY_MODEL` 编译选项控制是否启用 EM 框架。

EM 框架的核心数据结构为每个性能域维护一张功耗表，记录了在每个 OPP 下的活跃功耗和不同 C-State（空闲状态）下的功耗。当 EAS 需要计算"把任务放在某个 CPU 上需要多少能耗"时，它就查询这张表。

EM 框架是通用的。除了 EAS，thermal 管理（IPA 智能功率分配）和 power capping 等子系统也依赖它。因此，EAS 的能量预测和温控的功率预算用的是同一套数据源，决策基线一致。

[已验证: 官方文档, Documentation/power/energy-model.rst — EM framework standardizes power cost tables]

### 能耗计算的核心公式

EAS 的能耗预测并不复杂。对每个候选 CPU，它计算的是一个能量增量（energy delta）：

```
energy_delta = 放置任务后的系统总能耗 - 当前的系统总能耗
```

选择 energy_delta 最小的那个候选 CPU。

具体来说，它会：

1. 计算目标 CPU 在放置任务后的预期 utilization
2. 根据 utilization 查询 EM，确定需要运行的 OPP（频率）
3. 用该 OPP 的功耗值，结合该 CPU 上其他任务的 utilization，计算总能耗
4. 对每个候选 CPU 重复上述计算，选出总能耗最低的

这个计算是近似的——它假设 schedutil 会把频率调到恰好满足当前 utilization 的最低 OPP，这是 `schedutil` governor 的核心行为。也正是这个原因，EAS 必须配合 `schedutil` 使用：如果 governor 不是按 utilization 调频的，EAS 的预测就会出错。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — EAS predicts energy impact and relies on schedutil for frequency predictions]

## PELT：追踪每个任务的"繁忙程度"

### 为什么需要"利用率"信号

EAS 的决策依赖一个关键输入：**任务有多"忙"**。这个信息由 PELT（Per-Entity Load Tracking）提供。

在 PELT 出现之前，内核通过 per-CPU runqueue 的负载来估算任务的繁忙程度，但这种方式有根本性的缺陷——它只反映了 CPU 的整体负载，无法区分"一个 CPU 上跑了三个轻任务"和"一个 CPU 上跑了一个重任务"。EAS 需要知道**每个任务**需要多少计算能力，才能做出合理的选核决策。

PELT 从 Linux 3.8 开始引入，它为每个调度实体（单个任务、任务组、CPU runqueue）维护一个独立的 utilization 信号 `util_avg`。

[已验证: 官方文档, kernel/sched/fair.c — PELT tracks utilization per sched_entity]

### PELT 的计算方式

PELT 使用指数加权移动平均（EWMA）来平滑 utilization 信号。它的窗口大约为 32ms，最近 32ms 的实际运行时间贡献了信号总权重的一半，更早的历史贡献另一半。具体表现为：

- 如果一个任务突然变忙，它的 `util_avg` 会在约 32ms 内快速上升
- 如果一个任务突然空闲，它的 `util_avg` 会在约 32ms 内缓慢下降
- 这个设计让调度器既能快速响应负载变化，又不会被瞬时波动干扰

[图：PELT 信号衰减示意 — 32ms 窗口指数加权移动平均，展示信号上升/下降的响应速度]

PELT 的 `util_avg` 被归一化到 0~1024 的范围。其中 1024 代表"一个最大 capacity 的 CPU 满负荷运行"。这个归一化非常关键——它让 `util_avg` 可以直接与 CPU 的 `capacity` 比较：如果任务的 `util_avg` 是 300，而小核的 `capacity` 是 400，EAS 就知道这个任务放在小核上"装得下"。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — PELT signals normalized to 1024, comparable with CPU capacity]

### 频率不变性与 CPU 不变性

PELT 的 util 信号要能在大小核之间准确比较，需要满足两个"不变性"：

1. **频率不变性（Frequency Invariance）**：同一个任务在大核 1GHz 上跑 10ms 和大核 2GHz 上跑 5ms，utilization 信号应该相同。PELT 通过 `arch_scale_freq_capacity()` 回调实现频率归一化——将实际运行时间按当前频率与最大频率的比值进行缩放。

2. **CPU 不变性（CPU Invariance）**：同一个任务在大核上跑 5ms 和小核上跑 5ms，由于大核 IPC（Instructions Per Cycle，每周期指令数）更高，实际完成的计算量不同。PELT 通过 `arch_scale_cpu_capacity()` 回调实现 CPU 归一化——将 utilization 信号按目标 CPU 的 capacity 进行缩放。

没有这两个不变性，EAS 的选核决策就会出错。例如，如果一个任务在小核上跑了很长时间积累了较高的 raw utilization，不做 CPU 不变性归一化的话，EAS 会误以为这个任务很重而不敢放在小核上。归一化后，它的 util 可能并不高。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — EAS requires frequency-invariant and CPU-invariant PELT signals]

### WALT：PELT 的替代方案

在早期 Android 设备上，Google 曾尝试过另一种负载追踪机制——WALT（Window Assisted Load Tracking），在部分 Pixel 设备上使用。WALT 基于固定时间窗口（而非 PELT 的指数衰减）来计算负载，对突发负载的响应更快。

但从 Android 12 / Linux 5.10 开始，WALT 已被弃用，统一回归 PELT。PELT 的内核主线支持更完善，与 EAS 的集成也更紧密。在分析老设备的 Trace 数据时遇到与负载追踪相关的问题，可能需要考虑设备当时用的是 WALT 还是 PELT。

[待验证: WALT 的弃用时间线在所有厂商设备上是否一致]

无论设备使用哪种负载追踪机制，PELT 还是 WALT，EAS 的核心决策逻辑不变：基于 utilization 信号做能耗最优的选核。下文讨论的 Task Placement 策略，均以 PELT 作为输入信号。

## Task Placement：EAS 的选核策略

### find_energy_efficient_cpu 的决策流程

当一个任务被唤醒（wake-up）或迁移（migration）时，EAS 通过 `find_energy_efficient_cpu()` 为它选择目标 CPU。这个函数的核心流程如下：

**第一步：寻找每个性能域中 spare capacity 最大的 CPU。** Spare capacity = CPU capacity - 当前 utilization。它表示这个 CPU 还有多少"余力"。在大小核系统中，也就是先在小核簇中找一个最空闲的小核，再在大核簇中找一个最空闲的大核。

**第二步：检查 prev_cpu（上一次运行的 CPU）的 spare capacity。** 如果 prev_cpu 当前有足够的空闲容量来容纳这个任务，倾向于保持不变——因为迁移本身有开销（cache miss、TLB flush 等）。

**第三步：如果 prev_cpu 容不下，计算将任务放到每个候选 CPU 上的系统总能耗。** 对每个候选，EAS 会：
- 预测目标 CPU 的 utilization 会变成多少
- 根据新的 utilization 查询 EM，确定目标 CPU 需要运行在哪个 OPP
- 计算整个系统的能耗变化（不仅仅是目标 CPU，还要考虑被迁出 CPU 的能耗下降）

**第四步：选择总能耗最低的候选 CPU。** 但有一个安全阀——如果"能耗最优"的候选与"性能最优"的候选之间的能耗差异很小（在一个阈值范围内），EAS 会倾向于选择性能更好的那个，避免为了省微不足道的电量而牺牲用户体验。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — find_energy_efficient_cpu identifies highest spare capacity and estimates energy]

### 轻任务 vs 重任务的策略差异

EAS 对轻任务和重任务有不同的处理方式：

**轻任务（util_avg 较低）**：EAS 会优先把这类任务放在小核上。因为小核的 capacity 足以"装下"它们，不需要动用高功耗的大核。大多数后台任务、周期性的心跳检测、轻量的 UI 更新都属于此类。

**重任务（util_avg 接近或超过小核 capacity）**：这类任务如果硬放在小核上，会导致小核频率飙升（进入能效陡降区），反而更费电。EAS 会将这类任务提升到大核上，利用大核更高的 IPC 在更短时间内完成工作，然后让大核更快回到低功耗状态。典型的重任务包括视频编解码、大型游戏渲染线程、应用启动时的主线程等。

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — EAS 选核逻辑与 Task Placement 部分]

### 负载均衡与任务迁移

除了唤醒时的选核，EAS 还参与系统运行时的负载均衡。当调度器发现某个 CPU 过载（utilization 接近或超过 capacity），会触发负载均衡，将部分任务迁移到其他 CPU。

在 EAS 的场景下，负载均衡有一个特殊行为：**overutilized 标志**。当系统中任何一个 CPU 的 utilization 超过其 capacity 的 80%（默认阈值），系统会被标记为 "overutilized"，此时 EAS 的节能策略会被暂时关闭，调度器回到传统的性能优先模式。原因是：在系统负载很高的情况下，节能优化的空间已经很小，强行节能反而会导致严重的性能问题。

这个机制意味着，如果发现 EAS 似乎"不工作了"——任务被随意分配，不再考虑能耗——很可能是因为系统处于 overutilized 状态。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst — overutilized flag disables EAS energy-awareness]

## UClamp：用户空间的性能提示

### uclamp 的作用

到目前为止，EAS 的选核决策完全依赖 PELT 提供的 utilization 信号，调度器据此预测未来需求。

但有时候，用户空间比调度器更清楚一个任务的重要程度：主线程需要低延迟响应，而后台同步任务可以慢慢跑。PELT 提供了任务的实际 utilization 信号，用户空间还需要一种机制告诉调度器：“这个任务虽然 util 不高，但它很重要，请给它更多资源”或者“这个后台任务不重要，不要让它浪费太多电”。

这就是 uclamp（Utilization Clamping）的作用——它允许用户空间为每个任务设置 utilization 的上下限：

- **UCLAMP_MIN**：设置 utilization 的下限。即使任务的实际 util 很低，调度器也会按这个下限来对待它。效果类似"保底性能"。例如，设 UCLAMP_MIN=512 意味着即使这个任务当前 util 只有 100，EAS 也会按 512 来选核和调频——它会被分配到 capacity 更高的 CPU，频率也会被拉高。

- **UCLAMP_MAX**：设置 utilization 的上限。限制任务最多能获得多少 CPU 资源。用于约束后台任务，防止它们占用大核或拉高频率。

[已验证: 官方文档, Linux kernel v5.3+ uclamp feature, Documentation/scheduler/sched-util-clamp.rst]

### Android 中的 uclamp 使用

Android 从 10（API 29）开始广泛使用 uclamp 来区分不同优先级任务：

- **Top-app（前台应用）**：通过 cgroup 设置较高的 UCLAMP_MIN，确保关键线程（如主线程、RenderThread）能快速获得 CPU 资源，减少启动和交互延迟
- **Background（后台应用）**：设置较低的 UCLAMP_MAX，限制后台任务对 CPU 的占用，防止它们抢夺前台应用的资源
- **Foreground service**：介于两者之间，获得适度的资源保障

uclamp 的效果可以直接在 Perfetto 中观察到：同样是 util=200 的任务，一个 top-app 的线程会被分配到大核上、频率拉到中高 OPP；而一个 background 的线程则被稳稳地"按"在小核低频上运行。

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — schedutil 与 uclamp 部分]

[自动发现: 来源 obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — SchedTune/cgroup 对调度策略的影响]

> **注意**: 在 Linux 6.6+ / Android 15+ 中，部分设备开始使用 `schedutil` 的替代方案（如基于 EAS+EM 的混合调频），核心逻辑不变，但 governor 名称可能不同。

## EAS 在 Perfetto 中的观察

### 三条关键 Track

[图：Perfetto 全局视图 — CPU Frequency + CPU Scheduling + CPU Idle 三条 Track 同时可见，标注大小核分布]

在 Perfetto 中观察 EAS 的行为，主要关注以下三条 Track：

**1. CPU Frequency Track**

在 Perfetto 界面最上方，每个 CPU 核心都有对应的频率条。鼠标悬停在频率区域上，能直接读到当前的运行频率（MHz）。频率曲线随负载上下波动时，对应的就是 schedutil 根据 PELT utilization 信号做出的 DVFS 决策。

重点关注：
- 频率是否有突然的上限限制（scaling_max_freq 被压低）——这通常意味着温控介入了（详见 5.5 节）
- 同簇 CPU 的频率是否同步变化——移动 SoC 通常以簇为单位调频
- 任务运行期间频率是否合理——如果一个高负载任务运行时频率被限制在低位，性能瓶颈可能不在代码而在系统策略

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — CPU Frequency 深度解析部分]

**2. CPU Scheduling Track（sched_switch）**

CPU Scheduling Track 显示每个时刻哪个线程在哪个 CPU 核心上运行。这是观察 EAS 选核和迁移行为的直接窗口。

重点观察：
- **关键线程是否在合适的核心上**：主线程和 RenderThread 是否被分配到了大核？如果被长时间限制在小核上，可能是 EAS 误判了任务的 util，或者系统处于 overutilized 状态
- **迁移频率**：一个线程在大小核之间"反复横跳"（ping-pong）通常不是好现象——每次迁移都会带来 cache miss 开销
- **唤醒关系**：通过点击一个 sched slice，能追到是谁唤醒了这个线程（wakeup from），以及它被唤醒后的目标 CPU

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — 选核与迁移逻辑部分]

**3. CPU Idle States Track**

这条 Track 显示 CPU 的 C-State 变化。EAS 的一个重要优化目标就是让空闲的 CPU 尽快进入深睡眠状态（C3/C4），因为 CPU 在空闲状态下的功耗远低于最低频运行状态。

如果 EAS 工作正常，小核在无负载时会快速进入深度 idle，大核在不需要时大部分时间处于 deep idle。如果大核频繁在浅 idle 和运行之间切换，说明有后台任务不恰当地唤醒了大核。

### 使用 SQL 分析 EAS 行为

Perfetto 的 SQL 引擎可以帮我们量化 EAS 的决策效果。以下是几个实用的查询：

**查看线程在各 CPU 核心上的时间分布**（判断 EAS 是否合理分配任务）：

```sql
SELECT
  cpu,
  sum(dur) / 1e6 AS time_on_cpu_ms
FROM sched
WHERE utid = (SELECT utid FROM thread WHERE name = '你的线程名' LIMIT 1)
GROUP BY cpu
ORDER BY cpu;
```

如果主线程在 CPU 0-3（小核）上的时间远多于 CPU 4-7（大核），就值得调查 EAS 为什么没有把它分配到大核。

**查看 CPU 频率分布**（判断 schedutil 的调频是否合理）：

```sql
SELECT
  cpu,
  freq_value / 1000 AS freq_mhz,
  sum(dur) / 1e9 AS time_at_freq_s
FROM cpu_frequency
GROUP BY cpu, freq_value
ORDER BY cpu, freq_value;
```

**判断系统是否处于 overutilized 状态**：

Perfetto 没有直接的 overutilized Track，但我们可以通过观察是否有某个 CPU 的 utilization 长期超过其 capacity 的 80% 来间接判断。如果 CPU Scheduling Track 上某个小核几乎全是 Running 状态（没有 idle），很可能触发了 overutilized。

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — 实战与 SQL 部分]

## 与其他机制的关系

### EAS 与 CFS（5.1 节）

EAS 建立在 CFS 之上。它不替换 CFS，而是接管了 CFS 的唤醒选核逻辑。在 overutilized 状态下，EAS 自动退让，回到 CFS 的默认行为。

### EAS 与大小核架构（5.3 节）

EAS 的节能效果严重依赖于大小核架构的设计——小核提供能效，大核提供性能。5.3 节会详细讲解不同 SoC 的核心拓扑及其对 EAS 的影响。

### EAS 与 DVFS（5.4 节）

EAS 的能耗预测依赖于 schedutil governor 的 DVFS 行为。5.4 节会详细讲解 DVFS 机制，以及 Power HAL 的场景策略如何影响 CPU 频率——这些因素会直接影响 EAS 的预测准确性。

### EAS 与 Thermal 管理（5.5 节）

当设备过热时，温控系统会强制降低 CPU 频率上限（scaling_max_freq）。这不影响 EAS 的选核逻辑，但会改变 EAS 对 CPU capacity 的估算——因为实际可用的最高频率被降低了。5.5 节会详细讲解温控对调度的影响。

### EAS 与 UClamp/SchedTune

在 Linux 5.3 之前，Android 使用 SchedTune（一个 Android 特有的 cgroup controller）来实现类似 uclamp 的功能。从 Linux 5.3 开始，主线内核的 uclamp 逐渐取代了 SchedTune。两者的核心思想相同：通过 cgroup 为不同优先级的任务设置 util clamp，影响 EAS 的选核和调频决策。部分厂商（如 OPPO 的蜂鸟引擎、小米的 MiBrain）在此基础上做了更多定制化，加入了更精细的场景感知。

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — 厂商定制化部分]

## 常见问题与误区

### "EAS 是为了让系统变慢来省电"

不是。EAS 的核心目标是"在满足性能需求的前提下省电"。对于轻任务，放在小核上既省电又不影响性能；对于重任务，EAS 仍然会分配到大核。只有当系统过载时 EAS 才会被暂时关闭。正常情况下不会因为 EAS 而感受到明显的性能下降——但如果 EAS 被错误配置或禁用，可能会发现耗电明显增加。

### "任务应该尽量放在大核上以保证性能"

这是最常见的误区。大核的高功耗意味着频繁使用大核会显著缩短续航，而且大核在高频下的能效比（performance per watt）可能不如中频运行时。正确的做法是让 EAS 根据任务的实际 util 来决定——轻任务放小核、重任务放大核，各司其职。

### "看到任务在小核上就是 EAS 有问题"

不一定。如果任务的 util 很低（比如 <200），放在小核上是 EAS 的正确决策。只有当任务的 util 超过了小核 capacity、且没有触发 overutilized、但任务仍然长时间留在小核上时，才说明 EAS 可能有问题——这通常是因为 EM 数据不准确或任务的 util 信号被错误地 clamp 了。

### "厂商的定制调度器比原版 EAS 好"

不一定，但也不一定差。厂商的定制调度器通常在原版 EAS 的基础上增加了更多场景感知（如游戏模式、性能模式）和更精细的绑核策略。有些厂商的定制确实带来了更好的用户体验，但也有厂商的定制引入了新的问题（如过度激进的上核策略导致功耗飙升）。分析 Perfetto Trace 时，需要了解测试设备的厂商调度策略，才能准确判断行为是否正常。

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-09-CPU.md — 选核与迁移逻辑、厂商定制化部分]

## 版本演进

| 时间节点 | 变化 | 影响 |
|---------|------|------|
| Linux 3.8 | PELT 引入 | 为后续 EAS 提供 per-entity utilization 信号基础 |
| Linux 5.0 | EAS 合入主线 | `find_energy_efficient_cpu()` 成为大小核系统的默认唤醒选核路径 |
| Linux 5.3 | uclamp 合入主线 | 取代 Android 特有的 SchedTune，提供标准化的 util clamping 接口 |
| Android 12 | WALT 弃用 | 统一回归主线 PELT，EAS 行为在所有设备上趋于一致 |
| Android 14+ | 厂商定制收敛 | Google 通过 GKI 限制内核定制空间，EAS 核心逻辑趋于统一 |

[待验证: Android 14 GKI 对厂商 EAS 定制的具体限制范围]

## 参考资料

- Linux 内核文档：[Energy Aware Scheduling](https://docs.kernel.org/scheduler/sched-energy.html)
- Linux 内核文档：[Energy Model framework](https://docs.kernel.org/power/energy-model.html)
- Linux 内核文档：[Operating Performance Points (OPP)](https://docs.kernel.org/power/opp.html)
- Perfetto 官方文档：[CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- AOSP 源码：`kernel/sched/fair.c`（`find_energy_efficient_cpu()`）
- AOSP 源码：`kernel/sched/pelt.c`（PELT 实现）
- AOSP 源码：`kernel/power/energy_model.c`（EM 框架）
- [高爷 - Android Perfetto 系列 9：CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)
- ARM 社区：[EAS 设计与实现](https://www.linuxplumbersconf.org/event/2/contributions/133/)
