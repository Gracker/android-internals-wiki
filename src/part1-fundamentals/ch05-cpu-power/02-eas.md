---
status: "finalized"
last_task2b_at: '2026-05-09T12:43:00+08:00'
title: EAS 能量感知调度
chapter: '5.2'
section: '5.2'
applicable_versions: Android 9 (API 28) - Android 17 (API 37)
last_verified: '2026-04-29'
last_verified_against: Linux kernel 6.6, Documentation/scheduler/sched-energy.rst
confidence: high
sources:
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md
- type: blog
  path: Personal-Knowlodge/source/Android-Systrace-CPU.md
- type: official
  path: https://docs.kernel.org/scheduler/sched-energy.html
- type: official
  path: https://docs.kernel.org/power/energy-model.html
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
tags:
- EAS
- energy-aware-scheduling
- PELT
- energy-model
- OPP
- task-placement
- uclamp
- schedutil
related_chapters:
- '5.1'
- '5.3'
- '5.4'
- '2.5'
drafted_date: '2026-03-31'
reviewed_date: "2026-05-28"
last_task6_audit: '2026-05-21'
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: revisiting
task9_state: "reviewed"
pipeline_stage: "task6_pending"
review2_date: '2026-04-06'
review2_by: openclaw-task6
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
task2b_state: fixed
task2b_result: fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-28"
last_task9_at: "2026-06-18T10:29:11+08:00"
task9_result: "auto-fixed"
review_notes: '2026-05-24 task9 idle-audit: needs-rework。P0：android16-6.12 overutilized 仍在 select_task_rq_fair callsite 跳过 find_energy_efficient_cpu，正文写成仍会尝试能量估算。'
last_task9_audit: "2026-06-18"
last_task2b_verifier_at: "2026-05-27T23:28:16+08:00"
task2b_verifier_note: "queue 无 pending 且正文充分，回流 Task6 复审；仅修正状态闭环。"
last_task6_at: '2026-05-28T01:05:00+08:00'
last_task6_review_log: "logs/review/2026-05-28-01-review.md"
task6_review_notes: "2026-05-28 Task6 review: pass-light-edit。L1/L2 小修 2 处；既有 Task9 needs-rework 技术项不由 Task6 裁决，继续流转 task9_pending。"
last_task9_review_log: "logs/deep-review/2026-06-18-10-audit.md"
task9_review_notes: "2026-05-24 task9 idle-audit: needs-rework。P0：android16-6.12 overutilized 仍在 select_task_rq_fair callsite 跳过 find_energy_efficient_cpu，正文写成仍会尝试能量估算。 | 2026-05-28 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-18 Task9 idle-audit: auto-fixed。P0 1：EAS 示例未体现 fits_capacity 约 20% margin；P1 1：运行时负载均衡误写为 EAS 参与，已改为 CFS load_balance/misfit 路径并由 overutilized 分界。回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-18
last_task9_audit_at: "2026-06-18T10:29:11+08:00"
last_task9_autofix_at: "2026-06-18"
last_task9_audit_log: "logs/deep-review/2026-06-18-10-audit.md"
last_task9_audit_result: "auto-fixed"
---


# EAS 能量感知调度

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 EAS（Energy Aware Scheduling）的核心思想：在满足性能需求的同时最小化能耗
- 🔹 能量模型（Energy Model）：OPP（Operating Performance Points）与功耗曲线
- 🔹 Task Placement 策略:将轻任务放小核、重任务放大核
- 🔹 Util（utilization）信号与 PELT（Per-Entity Load Tracking）
- 🔹 EAS 在 Perfetto 中的观察:cpu_frequency、sched_switch、uclamp

### 扩展(可选深入)

- 🔸 各 SoC 厂商对 EAS 的定制化(高通 / 联发科 / 三星)
- 🔸 Pixel 设备上的调度策略特点

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 EAS

在上一节中,我们讲了 CFS 的基本原理:它通过 vruntime 保证所有进程公平地获得 CPU 时间。但公平只是调度器的一个目标——在手机这样的移动设备上，还有一个同样重要的目标：**省电**。

现代手机 SoC（System on Chip，片上系统）普遍采用大小核架构(我们会在 5.3 节详细展开),一个四小核加四大核的八核处理器,在安排任务时面临一个核心问题:**一个任务应该放在小核还是大核?** 放小核省电但可能不够快,放大核够快但功耗高。如果调度器只看当前空闲程度,轻任务就可能被放到大核上,频率和电压都会被抬高,系统会多花电,也更容易把热量堆在前台交互阶段。

EAS（Energy Aware Scheduling）就是为了解决这个问题而生的。它在 Linux 5.0 中被合入主线内核,是 Android 设备上最重要的调度增强之一。EAS 的核心能力是:**在任务唤醒时,预测把任务放在不同 CPU 核心上分别需要消耗多少能量,然后选择一个既满足性能需求又最省电的核**。

理解 EAS 的意义在于:打开一份 Perfetto Trace 时,看到主线程被分配到了小核上运行缓慢,或者在大小核之间频繁迁移,需要知道这不是“随机”的行为，背后有 EAS 的决策逻辑,而理解这个逻辑,是判断调度行为是否正常的关键。

[已验证: 官方文档, https://docs.kernel.org/scheduler/sched-energy.html]

## EAS 的核心思想

### 从"找最快的核"到"找最省电的核"

传统 CFS 的任务唤醒逻辑（5.1 节讲过的 `select_task_rq_fair()`）主要关注性能：在可用的 CPU 核心中选择一个负载最低的、能让任务尽快开始执行的核。这个逻辑在同构系统（所有 CPU 核心性能相同）上工作良好，但在大小核架构上会出现问题：它可能把一个轻量级任务放到大核上，仅仅因为大核当时更空闲，这白白浪费了大核的高功耗能力。

EAS 覆盖了 CFS 的默认唤醒逻辑。当 EAS 启用时，`select_task_rq_fair()` 不再走原来的负载均衡路径，而是调用 `find_energy_efficient_cpu()`，这个函数的决策目标从“最快开始执行”变成了“满足性能需求的前提下，系统总能耗最低”。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - "EAS overrides the CFS task wake-up balancing code"]

用一个具体的例子来说明。假设我们有一个 util 值为 120 的轻量级任务需要被唤醒,系统中有两种核心:

- 小核:capacity 200,当前空闲
- 大核:capacity 1024,当前空闲

传统 CFS 会发现大核更空闲,选择大核。但 EAS 会计算:这个任务放在小核上仍在安全余量内(`fits_capacity(120, 200)` 为真;内核默认预留约 20% margin),不需要拉高大核的频率,整体能耗更低。于是 EAS 选择小核。这就是 EAS 的核心逻辑:**优先找一个既省电又够用的核,而不是单纯追求最空闲的核**。


[已验证: 官方文档, https://docs.kernel.org/scheduler/sched-energy.html - EAS uses capacity and utilization to estimate "busyness" for performance-vs-energy trade-offs]

### EAS 的前提条件

EAS 并非在所有设备上都生效。它需要满足以下条件:

1. **异构 CPU 拓扑**:系统中存在不同 computing capacity 的 CPU 核心(即大小核架构)。EAS 目前不支持同构系统,因为同构系统中无论把任务放在哪个核上,能耗差异都很小。
2. **能量模型(Energy Model)可用**:内核中必须注册了 CPU 的能耗数据。没有能量模型,EAS 就无法做能耗预测。
3. **schedutil 调频策略**:EAS 需要与 `schedutil` governor 配合工作,因为它的能耗预测依赖于对 CPU 未来运行频率的估算,而 `schedutil` 能提供这个信息。如果使用 `performance` 或 `powersave` 等固定频率的 governor,EAS 的频率预测就不准了。

这三个条件在主流 Android 手机上通常都满足：它们都是大小核架构，内核中有能量模型（通常通过 Device Tree 提供），默认使用 `schedutil` 调频。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - EAS requirements: asymmetric CPU topology, EM, schedutil]

## 能量模型(Energy Model)

### OPP:频率-电压对的集合

要理解 EAS 怎么做能耗预测,我们得先看能量模型的数据来源,即 OPP（Operating Performance Points）。

一个 CPU 核心并不是只能跑一个固定频率。它可以在多个频率-电压对之间切换,每个频率-电压对就是一个 OPP。例如,一个小核可能有如下 OPP 表:

| OPP | 频率 (MHz) | 电压 (mV) | 功耗 (mW) |
|-----|-----------|-----------|-----------|
| 0   | 300       | 600       | 15        |
| 1   | 600       | 650       | 30        |
| 2   | 900       | 720       | 60        |
| 3   | 1200      | 820       | 120       |
| 4   | 1500      | 950       | 200       |
| 5   | 1800      | 1100      | 380       |

功耗不是线性增长的：从 OPP 4 到 OPP 5,频率只增加了 20%,但功耗几乎翻倍。这是因为更高的频率需要更高的电压,而功耗与电压的平方成正比(动态功耗公式：P ∝ C V² f)。这也是 EAS 要尽量让任务在低频运行的原因：省下的不只是“一点电”，而是指数级的功耗节省。

[已验证: 官方文档, Documentation/power/energy-model.rst - EM provides power cost tables for performance domains]


OPP 数据通常定义在 Device Tree（设备树）中,使用 `operating-points-v2` 属性。内核启动时解析这些数据,构建出每个“性能域”（Performance Domain）的功耗曲线。一个性能域通常对应一个 CPU 簇，同簇内的核心共享频率和电压调节,因此它们的 OPP 表相同。

### 能量模型框架

Linux 内核的 Energy Model（EM）是一个独立于调度器的子系统。它给每个 performance domain 维护一张 active power cost table，表项对应不同的 performance state / OPP，调度器通过 `em_cpu_energy()` 接口估算“把任务放进这个簇后，活跃运行态大概要花多少能量”。调用链是 `kernel/sched/fair.c::compute_energy()` → `em_cpu_energy()` → EM performance state / power table。

这个边界要拆开。EM 只描述活跃运行态的功耗成本,不负责 CPU idle state。C-State 进入多深、停留多久,属于 CPUIdle governor 和 driver 的职责,观测时要看 `cpu_idle` 轨、平台 idle 统计或内核 idle 数据。把 EM 和 CPUIdle 写成一张表,会把"频率点功耗"和"空闲驻留功耗"混成同一层概念。

EM 之所以重要,是因为 EAS、thermal IPA、powercap 这类子系统都能复用同一套 active power 基线。EAS 负责把任务放到合适的簇,CPUIdle 负责在空闲时选 C-State,两个方向都会影响整机功耗,但读取的不是同一组接口。

[已验证: 官方文档, https://docs.kernel.org/power/energy-model.html;https://docs.kernel.org/admin-guide/pm/cpuidle.html]

### 能耗计算的核心公式

EAS 的能耗预测并不复杂。对每个候选 CPU,它计算的是一个能量增量(energy delta):

```text
energy_delta = 放置任务后的系统总能耗 - 当前的系统总能耗
```

选择 energy_delta 最小的那个候选 CPU。

具体来说,它会:

1. 计算目标 CPU 在放置任务后的预期 utilization
2. 根据 utilization 查询 EM，确定需要运行的 OPP（频率）
3. 用该 OPP 的功耗值,结合该 CPU 上其他任务的 utilization,计算总能耗
4. 对每个候选 CPU 重复上述计算,选出总能耗最低的

这个计算是近似的：它假设 schedutil 会把频率调到恰好满足当前 utilization 的最低 OPP,这是 `schedutil` governor 的核心行为。也正是这个原因,EAS 必须配合 `schedutil` 使用:如果 governor 不是按 utilization 调频的,EAS 的预测就会出错。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - EAS predicts energy impact and relies on schedutil for frequency predictions]

## PELT:追踪每个任务的"繁忙程度"

### 为什么需要"利用率"信号

EAS 的决策依赖一个关键输入:**任务有多"忙"**。这个信息由 PELT（Per-Entity Load Tracking）提供。

在 PELT 出现之前,内核通过 per-CPU runqueue 的负载来估算任务的繁忙程度,但这种方式有一个缺陷：它只反映了 CPU 的整体负载,无法区分"一个 CPU 上跑了三个轻任务"和"一个 CPU 上跑了一个重任务"。EAS 需要知道**每个任务**需要多少计算能力,才能做出合理的选核决策。

PELT 从 Linux 3.8 开始引入，它为每个调度实体（单个任务、任务组、CPU runqueue）维护独立的 utilization 信号 `util_avg`。

[已验证: 官方文档, kernel/sched/fair.c - PELT tracks utilization per sched_entity]

### PELT 的计算方式

PELT 使用指数加权移动平均(EWMA)来平滑 utilization 信号。它的窗口大约为 32ms,最近 32ms 的实际运行时间贡献了信号总权重的一半,更早的历史贡献另一半。具体表现为:

- 如果一个任务突然变忙,它的 `util_avg` 会在约 32ms 内快速上升
- 如果一个任务突然空闲,它的 `util_avg` 会在约 32ms 内缓慢下降
- 这个设计让调度器既能快速响应负载变化,又不会被瞬时波动干扰


PELT 的 `util_avg` 被归一化到 0~1024 的范围。其中 1024 代表"一个最大 capacity 的 CPU 满负荷运行"。这个归一化的作用是让 `util_avg` 可以直接与 CPU 的 `capacity` 比较:如果任务的 `util_avg` 是 300,而小核的 `capacity` 是 400,EAS 就知道这个任务放在小核上"装得下"。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - PELT signals normalized to 1024, comparable with CPU capacity]

### 频率不变性与 CPU 不变性

PELT 的 util 信号要能在大小核之间准确比较,需要满足两个"不变性":

1. **频率不变性（Frequency Invariance）**：同一个任务在大核 1GHz 上跑 10ms 和大核 2GHz 上跑 5ms，utilization 信号应该相同。PELT 通过 `arch_scale_freq_capacity()` 回调实现频率归一化：将实际运行时间按当前频率与最大频率的比值进行缩放。

2. **CPU 不变性（CPU Invariance）**：同一个任务在大核上跑 5ms 和小核上跑 5ms，由于大核 IPC（Instructions Per Cycle，每周期指令数）更高，实际完成的计算量不同。PELT 通过 `arch_scale_cpu_capacity()` 回调实现 CPU 归一化：将 utilization 信号按目标 CPU 的 capacity 进行缩放。

没有这两个不变性,EAS 的选核决策就会出错。例如,如果一个任务在小核上跑了很长时间积累了较高的 raw utilization,不做 CPU 不变性归一化的话,EAS 会误以为这个任务很重而不敢放在小核上。归一化后,它的 util 可能并不高。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - EAS requires frequency-invariant and CPU-invariant PELT signals]

### WALT 与设备差异

Linux mainline 的 EAS 文档建立在 PELT 及其 frequency / CPU invariance 之上,并没有把 WALT 当成前提。WALT（Window Assisted Load Tracking）是部分 Android common kernel 或厂商内核使用过的负载跟踪扩展，常见于追求更快突发响应的设备内核。它会改变 util 信号的形成方式，但不会改变 EAS 依据 util、capacity、EM 做选核这一核心逻辑。

分析具体设备时，按三层拆开看更清楚。主线内核这条线是 PELT → EAS → uclamp；AOSP 用户态是 task profile、cgroup 和 Power HAL 怎样把提示送进调度器；厂商设备才是 WALT、boost hook、额外迁核策略。把三条线压成"Android 12 统一回归 PELT"，容易把 mainline、AOSP 和 vendor 内核混成一件事。排查时按内核版本和厂商树确认具体负载跟踪实现。

[已验证: 官方文档, https://docs.kernel.org/scheduler/sched-energy.html - EAS 依赖 frequency-invariant / CPU-invariant utilization signals]

## Task Placement:EAS 的选核策略

### find_energy_efficient_cpu 的决策流程

当一个 CFS 任务被唤醒时，`select_task_rq_fair()` 会调用 `find_energy_efficient_cpu()` 为它选择目标 CPU。这个函数只负责 **wake-up placement**：负载均衡迁移、newidle balance、misfit migration 等路径有各自的入口（`load_balance()`、`detach_tasks()` 等），不走能量估算。这个函数的核心流程如下：

**第一步:寻找每个性能域中 spare capacity 最大的 CPU。** Spare capacity = CPU capacity - 当前 utilization。它表示这个 CPU 还有多少"余力"。在大小核系统中,也就是先在小核簇中找一个最空闲的小核,再在大核簇中找一个最空闲的大核。

**第二步：检查 prev_cpu（上一次运行的 CPU）的 spare capacity。** 如果 prev_cpu 当前有足够的空闲容量来容纳这个任务,倾向于保持不变，因为迁移本身有开销（cache miss、TLB flush 等）。

**第三步:如果 prev_cpu 容不下,计算将任务放到每个候选 CPU 上的系统总能耗。** 对每个候选,EAS 会:
- 预测目标 CPU 的 utilization 会变成多少
- 根据新的 utilization 查询 EM,确定目标 CPU 需要运行在哪个 OPP
- 计算整个系统的能耗变化(不仅仅是目标 CPU,还要考虑被迁出 CPU 的能耗下降)

**第四步:选择总能耗最低的候选 CPU。** 但有一个安全阀：如果“能耗最优”的候选与“性能最优”的候选之间的能耗差异很小(在一个阈值范围内),EAS 会倾向于选择性能更好的那个,避免为了省微不足道的电量而牺牲用户体验。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - find_energy_efficient_cpu identifies highest spare capacity and estimates energy]

### 轻任务 vs 重任务的策略差异

EAS 对轻任务和重任务有不同的处理方式:

**轻任务(util_avg 较低)**:EAS 会优先把这类任务放在小核上。因为小核的 capacity 足以"装下"它们,不需要动用高功耗的大核。大多数后台任务、周期性的心跳检测、轻量的 UI 更新都属于此类。

**重任务(util_avg 接近或超过小核 capacity)**:这类任务如果硬放在小核上,会导致小核频率飙升(进入能效陡降区),反而更费电。EAS 会将这类任务提升到大核上,利用大核更高的 IPC 在更短时间内完成工作,然后让大核更快回到低功耗状态。典型的重任务包括视频编解码、大型游戏渲染线程、应用启动时的主线程等。

### 全大核架构的调度边界

骁龙 8 Elite（2+6 Oryon）和天玑 9400（All Big Core）这类设计模糊了大小核的传统分界:所有核心都有较强的性能输出,级差大幅收窄。骁龙 8 Elite 的 Performance 核算力约为 837（以 Prime 核 1024 为基准）,Prime 与 Performance 之间的 capacity 差距只有约 18%,远小于传统 4+4 架构中小核与大核之间 3-5 倍的差距。

这种架构下，EAS 的能耗优化空间变小，因为核心之间的能效差异本身就小了。调度器更倾向于负载均衡而非节能压制,迁核决策的容错窗口也变宽。在 Perfetto 中表现为:线程在不同核心间的分布更均匀,迁移更频繁但每次迁移的性能波动更小。

排查这类设备时,重点关注的是频率和热约束,而不是选核。因为所有核心性能接近,"跑错了核"的惩罚比传统大小核架构轻得多。

### 负载均衡与任务迁移

除了唤醒时的选核,运行时负载均衡仍走 CFS 的 `load_balance()`、misfit migration 等路径,不做 EAS 能量估算。当调度器发现某个 CPU 过载(utilization 接近或超过 capacity),会触发负载均衡,将部分任务迁移到其他 CPU。

在 EAS 的场景下,这个分界由 **overutilized 标志** 决定。当系统中任何一个 CPU 的 utilization 超过其 capacity 的 80%(默认阈值),系统会被标记为 "overutilized"。

overutilized 对 EAS 的影响随内核版本有差异:

- **Linux 6.6 及更早**：`find_energy_efficient_cpu()` 入口处检查 `rd->overutilized`，如果系统已 overutilized，直接跳过能量估算，回到传统选核路径。
- **Linux 6.12 / GKI 6.12（Android 16）**：overutilized 的短路检查从 `find_energy_efficient_cpu()` 函数入口移到了调用点 `select_task_rq_fair()`。效果不变——系统 overutilized 时唤醒路径仍然跳过能量估算、回到传统选核；只是检查位置从被调函数内部挪到了调用方。overutilized 标志同时影响负载均衡判断（`load_balance()`、misfit migration 等路径），在高负载下触发更激进的性能优先迁移。

因此无论 6.6 还是 6.12，overutilized 时唤醒路径都会跳过能量估算。区别只是短路位置不同：6.6 在 `find_energy_efficient_cpu()` 内部检查，6.12 在 `select_task_rq_fair()` 调用点检查。排查时要按内核版本区分，不要把 6.6 的行为外推到 6.12。

[已验证: 官方文档, Documentation/scheduler/sched-energy.rst - overutilized flag disables EAS energy-awareness]

## UClamp:用户空间的性能提示

### uclamp 的作用

到目前为止,EAS 的选核决策完全依赖 PELT 提供的 utilization 信号,调度器据此预测未来需求。

但有时候,用户空间比调度器更清楚一个任务的重要程度:主线程需要低延迟响应,而后台同步任务可以慢慢跑。PELT 提供了任务的实际 utilization 信号,用户空间还需要一种机制告诉调度器:"这个任务虽然 util 不高,但它很重要,请给它更多资源"或者"这个后台任务不重要,不要让它浪费太多电"。

这就是 uclamp（Utilization Clamping）的作用：它允许用户空间为每个任务设置 utilization 的上下限：

- **UCLAMP_MIN**:设置 utilization 的下限。即使任务的实际 util 很低,调度器也会按这个下限来对待它。效果类似"保底性能"。例如,设 UCLAMP_MIN=512 意味着即使这个任务当前 util 只有 100,EAS 也会按 512 来选核和调频，它会被分配到 capacity 更高的 CPU,频率也会被拉高。

- **UCLAMP_MAX**:设置 utilization 的上限。限制任务最多能获得多少 CPU 资源。用于约束后台任务,防止它们占用大核或拉高频率。

[已验证: 官方文档, Linux kernel v5.3+ uclamp feature, Documentation/scheduler/sched-util-clamp.rst]

### Android 中的 uclamp 使用

在 Android 里，调度提示不是应用自己去写 cgroup 文件。AMS / OomAdjuster 先根据进程状态给进程或线程分配 sched group，随后 `android.os.Process.setThreadGroup()`、`setThreadGroupAndCpuset()`、`setProcessGroup()` 进 JNI，JNI 再调用 `SetTaskProfiles()` / `SetProcessProfiles()`。libprocessgroup 读取 `system/core/libprocessgroup/profiles/task_profiles.json`，把 profile 展开成“加入哪个 cgroup”和“往哪个属性文件写值”两类动作。

### UClamp 聚合方式的演进

主线内核（Linux 5.3 至 6.12）的 UClamp 聚合始终采用 max/bucket 策略：`kernel/sched/core.c` 的 clamp bucket 逻辑追踪每个 rq 上请求的最大 clamp 值。三个 UCLAMP_MIN=200 的后台任务跑在同一个 CPU 上时，调度器只按 200 来调频和选核。多任务并发时,如果各任务的真实负载之和远大于单任务的 clamp 值,频率预测会系统性偏低。

社区和部分厂商分支曾探索将聚合方式从 max 改为 sum，理论上能更准确反映多任务总负载。但截至 android16-6.12（GKI 6.12），公开源码中 `uclamp_rq_util_with()` 仍走 max 路径，sum 聚合尚未合入主线。如果某个厂商内核切换到了 sum 聚合，排查时要结合具体 kernel tree 和 commit 确认。

把 Android 10、11、12 的路径拆开看,更稳:

- **Android 10**:task profile 已经能操作 `cpu.util.min` / `cpu.util.max`,但默认的性能档位还是大量依赖 `/dev/stune/{background,foreground,top-app}` 和 `schedtune.boost` / `schedtune.prefer_idle`;cpuset 这条线单独决定线程允许跑在哪组 CPU 上。
- **Android 11**:AOSP 把 cpu controller 的接口名切到 `cpu.uclamp.min` / `cpu.uclamp.max`,默认 profile 仍保留 `schedtune` 分组,属于"uclamp 文件名到位了,默认性能档位还没完全离开 schedtune"的阶段。
- **Android 12 及以后**:AOSP 默认的 `HighEnergySaving` / `HighPerformance` / `MaxPerformance` 直接加入 `cpu/{background,foreground,top-app}`,`cpuset` 继续负责 CPU 集约束,freezer 迁到 cgroup v2。到这时,top-app / foreground / background 这三档才把 uclamp 提示纳入默认用户态路径。

落到设备上排查时,我们至少看三处:

1. `/proc/<tid>/cgroup`,确认线程落在哪个 `cpu` / `cpuset` / `schedtune` 分组。
2. 对应 cgroup 目录里的 `cpu.uclamp.min`、`cpu.uclamp.max`,旧设备再补看 `cpu.util.min` / `cpu.util.max` 和 `/dev/stune/*/schedtune.boost`。
3. `/proc/<tid>/sched`,核对该线程最终暴露给调度器的 util / clamp 相关字段;字段名会随内核版本变化,通常要连同 `schedutil`、频率轨和 CPU 迁移一起看。

把这条控制链看完整,就能解释同一条 RenderThread 为什么在 top-app 状态被推到大核,而切回后台后又被压回小核。

[已验证: AOSP, `platform/system/core/libprocessgroup/profiles/task_profiles.json` @ android10-release/android11-release/android12-release;`frameworks/base/core/jni/android_util_Process.cpp` @ android12-release]

## EAS 在 Perfetto 中的观察

### 三条关键 Track


在 Perfetto 中观察 EAS 的行为,主要关注以下三条 Track:

**1. CPU Frequency Track**

在 Perfetto 界面最上方,每个 CPU 核心都有对应的频率条。鼠标悬停在频率区域上,能直接读到当前的运行频率(MHz)。频率曲线随负载上下波动时,对应的就是 schedutil 根据 PELT utilization 信号做出的 DVFS 决策。

重点关注:
- 频率是否有突然的上限限制（scaling_max_freq 被压低），通常表示温控介入了(详见 5.5 节)
- 同簇 CPU 的频率是否同步变化，移动 SoC 通常以簇为单位调频
- 任务运行期间频率是否合理，如果一个高负载任务运行时频率被限制在低位,性能瓶颈可能不在代码而在系统策略

**2. CPU Scheduling Track（sched_switch）**

CPU Scheduling Track 显示每个时刻哪个线程在哪个 CPU 核心上运行。这是观察 EAS 选核和迁移行为的直接窗口。

重点观察:
- **关键线程是否在合适的核心上**:主线程和 RenderThread 是否被分配到了大核?如果被长时间限制在小核上,可能是 EAS 误判了任务的 util,或者系统处于 overutilized 状态
- **迁移频率**:一个线程在大小核之间"反复横跳"(ping-pong)通常不是好现象，每次迁移都会带来 cache miss 开销
- **唤醒关系**:通过点击一个 sched slice,能追到是谁唤醒了这个线程(wakeup from),以及它被唤醒后的目标 CPU

**3. CPU Idle States Track**

这条 Track 显示 CPU 的 C-State 变化。EAS 的一个重要优化目标就是让空闲的 CPU 尽快进入深睡眠状态(C3/C4),因为 CPU 在空闲状态下的功耗远低于最低频运行状态。

如果 EAS 工作正常,小核在无负载时会快速进入深度 idle,大核在不需要时大部分时间处于 deep idle。如果大核频繁在浅 idle 和运行之间切换,说明有后台任务不恰当地唤醒了大核。

### 使用 SQL 分析 EAS 行为

Perfetto 更适合拿来回答三个问题:线程到底跑在哪些 CPU 上、这些 CPU 当时跑到什么频率、空闲驻留有没有被打碎。SQL 最好同时带进程名和线程名,避免多进程 Trace 里只按 thread name 取到错误 `utid`。

**统计目标线程在各 CPU 上的运行时间**:

```sql
WITH target_thread AS (
  SELECT t.utid, t.tid
  FROM thread t
  JOIN process p USING (upid)
  WHERE p.name = 'com.example.app'
    AND t.name = 'RenderThread'
  LIMIT 1
)
SELECT
  cpu,
  round(sum(dur) / 1e6, 2) AS running_ms
FROM sched
WHERE utid = (SELECT utid FROM target_thread)
GROUP BY cpu
ORDER BY cpu;
```

如果 RenderThread 绝大多数时间都留在小核,我们再回去看当时的 `uclamp.min/max`、前台状态和 thermal 约束,判断这是正常节能放置,还是提示链断了。

**统计各 CPU 的频率驻留时间**:

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

SELECT
  cpu,
  freq / 1000.0 AS freq_mhz,
  round(sum(dur) / 1e9, 3) AS time_s
FROM cpu_frequency_counters
GROUP BY cpu, freq
ORDER BY cpu, freq;
```

`cpu_frequency_counters` 是 Perfetto stdlib 里的标准表,列名是 `freq`、`cpu`、`dur`。如果当前环境没有加载 stdlib,再退回原始 `counter` / `counter_track` 方案。

**统计 CPU idle 驻留**:

```sql
INCLUDE PERFETTO MODULE linux.cpu.idle;

SELECT
  cpu,
  idle,
  round(sum(dur) / 1e9, 3) AS time_s
FROM cpu_idle_counters
GROUP BY cpu, idle
ORDER BY cpu, idle;
```

`idle = -1` 表示 CPU 正在运行,数值越大通常代表越深的 idle state。大核长期停不进深 idle,通常说明前台线程、binder 回调或后台唤醒把它反复拉醒。

**怎么判断 overutilized**

官方文档里的 over-utilized 阈值是"CPU 使用量超过其 compute capacity 的 80%"。Perfetto 没有统一的 `sched_overutilized` 轨,所以 SQL 只能给排查线索,不能只凭"小核几乎没有 idle"就下结论。更稳妥的做法是把这几项一起看:小核 running ratio 是否持续偏高、同簇频率是否长期贴顶、关键线程是否被推向大核,再结合设备内核导出的 scheduler debug 信息确认。

[已验证: 官方文档, https://perfetto.dev/docs/analysis/stdlib-docs#linux-cpu-frequency;https://perfetto.dev/docs/analysis/stdlib-docs#linux-cpu-idle;https://docs.kernel.org/scheduler/sched-energy.html]

## 与其他机制的关系

### EAS 与 CFS（5.1 节）

EAS 建立在 CFS 之上。它不替换 CFS，而是接管了 CFS 的唤醒选核逻辑。overutilized 时唤醒路径始终跳过能量估算——Linux 6.6 在 `find_energy_efficient_cpu()` 入口短路，android16-6.12 把同一个检查移到 `select_task_rq_fair()` 调用点。overutilized 同时影响负载均衡和迁移策略（详见本文「负载均衡与任务迁移」小节）。

### EAS 与大小核架构（5.3 节）

EAS 的节能效果严重依赖于大小核架构的设计：小核提供能效，大核提供性能。5.3 节会详细讲解不同 SoC 的核心拓扑及其对 EAS 的影响。

### EAS 与 DVFS（5.4 节）

EAS 的能耗预测依赖于 schedutil governor 的 DVFS 行为。5.4 节会详细讲解 DVFS 机制,以及 Power HAL 的场景策略如何影响 CPU 频率，这些因素会直接影响 EAS 的预测准确性。

### EAS 与 Thermal 管理(5.5 节)

当设备过热时,温控系统会强制降低 CPU 频率上限（scaling_max_freq）。这不影响 EAS 的选核逻辑，但会改变 EAS 对 CPU capacity 的估算，因为实际可用的最高频率被降低了。5.5 节会详细讲解温控对调度的影响。

### EAS 与 UClamp/SchedTune

把 SchedTune 和 uclamp 写成"Linux 5.3 之后完全替换"会丢掉 Android 用户态这层历史。对 mainline 来说,uclamp 是 Linux 5.3 引入、5.4 提供 cgroup 接口的标准机制;对 AOSP 来说,Android 10/11 的默认性能 profile 仍大量依赖 `schedtune` 分组,Android 12 的默认 profile 才开始直接加入 `cpu/{background,foreground,top-app}`。厂商设备是否继续保留 WALT hook、boost path 或自定义 schedtune 行为,要按设备 kernel tree 和 task profile 再核实。

EAS 看的是"有效 util 信号 + capacity + EM"。SchedTune 或 uclamp 只是给这个 util 加提示,让 top-app 更容易上核,background 更容易被封顶。它们会改 EAS 的输入,但不会单独决定 EAS 的全部结果。

## 常见问题与误区

### "EAS 是为了让系统变慢来省电"

不是。EAS 的核心目标是“在满足性能需求的前提下省电”。对于轻任务，放在小核上既省电又不影响性能；对于重任务，EAS 仍然会分配到大核。无论 6.6 还是 6.12，overutilized 时唤醒路径都会跳过能量估算（只是短路位置不同），负载均衡路径会更激进地做性能优先迁移。正常情况下不会因为 EAS 而感受到明显的性能下降——但如果 EAS 被错误配置或禁用，可能会发现耗电明显增加。

### "任务应该尽量放在大核上以保证性能"

这是最常见的误区。大核的高功耗意味着频繁使用大核会显著缩短续航,而且大核在高频下的能效比(performance per watt)可能不如中频运行时。正确的做法是让 EAS 根据任务的实际 util 来决定：轻任务放小核、重任务放大核，各司其职。

### "看到任务在小核上就是 EAS 有问题"

不一定。如果任务的 util 很低(比如 <200),放在小核上是 EAS 的正确决策。只有当任务的 util 超过了小核 capacity、且没有触发 overutilized、但任务仍然长时间留在小核上时,才说明 EAS 可能有问题，通常是因为 EM 数据不准确或任务的 util 信号被错误地 clamp 了。

### "厂商的定制调度器比原版 EAS 好"

不一定好，也不一定差。厂商定制通常在原版 EAS 基础上增加更多场景感知（游戏模式、性能模式）和更精细的绑核策略。有些定制体验更好，也有定制引入了新问题（如过度激进的上核策略导致功耗飙升）。分析 Perfetto 时，先确认测试设备的厂商调度策略，才能准确判断行为是否异常。

## 版本演进

| 维度 | 时间节点 | 变化 | 读这一段时要抓住什么 |
|------|----------|------|----------------------|
| 主线内核 | Linux 3.8 | PELT 引入 | 给 EAS 提供 per-entity utilization 信号 |
| 主线内核 | Linux 5.0 | EAS 合入主线 | `find_energy_efficient_cpu()` 基于 EM 做唤醒放置 |
| 主线内核 | Linux 5.3 | uclamp 合入主线 | 任务可以声明最小 / 最大性能点 |
| 主线内核 | Linux 5.4 | uclamp cgroup 接口合入 | 用户态可以通过 cgroup 统一下发 clamp |
| AOSP 用户态 | Android 10 | task_profiles 成型,cpu controller 暴露 `cpu.util.min/max`,默认性能档位仍大量依赖 `schedtune` + `cpuset` | 看 `/dev/stune/*` 和 `/dev/cpuset/*` |
| AOSP 用户态 | Android 11 | `cpu.uclamp.min/max` 命名到位,默认 profile 仍保留 `schedtune` 分组 | 同时核对 `schedtune` 与 `cpu.uclamp.*` |
| AOSP 用户态 | Android 12+ | 默认 `HighEnergySaving` / `HighPerformance` / `MaxPerformance` 直接进入 `cpu/{background,foreground,top-app}`,cpuset 继续控制可运行 CPU 集 | top-app / foreground / background 的默认提示链更直观 |
| GKI 内核 | GKI 6.12 (Android 16) | overutilized 短路位置从 `find_energy_efficient_cpu()` 内部移到 `select_task_rq_fair()` 调用点；效果不变 | 排查时注意 6.6 和 6.12 的检查位置不同，但短路行为一致 |
| GKI 内核 | GKI 6.12 (Android 16) | UClamp 聚合仍为 max/bucket,sum 聚合为厂商分支/社区探索方向 | 排查时需按具体 kernel tree 确认聚合策略 |
| 设备实现 | 厂商分支 | WALT、Power HAL boost、额外迁核策略按 SoC / kernel tree 变化 | Trace 结论必须落回具体设备 |

## 参考资料

- Linux 内核文档:[Energy Aware Scheduling](https://docs.kernel.org/scheduler/sched-energy.html)
- Linux 内核文档:[Utilization Clamping](https://docs.kernel.org/scheduler/sched-util-clamp.html)
- Linux 内核文档:[Energy Model framework](https://docs.kernel.org/power/energy-model.html)
- Linux 内核文档:[CPU Idle Time Management](https://docs.kernel.org/admin-guide/pm/cpuidle.html)
- Linux 内核文档:[Operating Performance Points (OPP)](https://docs.kernel.org/power/opp.html)
- Perfetto 官方文档:[CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- Perfetto 官方文档:[Perfetto stdlib docs](https://perfetto.dev/docs/analysis/stdlib-docs)
- AOSP 源码：`platform/system/core/libprocessgroup/profiles/task_profiles.json`（android10/11/12-release）
- AOSP 源码：`frameworks/base/core/jni/android_util_Process.cpp`（`SetTaskProfiles()` / `SetProcessProfiles()` 调用链）
- AOSP 源码：`kernel/sched/fair.c`（`find_energy_efficient_cpu()`）
- AOSP 源码：`kernel/power/energy_model.c`（EM 框架）
- [高爷 - Android Perfetto 系列 9:CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)
- ARM 社区:[EAS 设计与实现](https://www.linuxplumbersconf.org/event/2/contributions/133/)
