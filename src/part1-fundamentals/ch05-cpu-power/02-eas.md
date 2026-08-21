---
status: "finalized"
title: EAS 能量感知调度
chapter: '5.2'
section: '5.2'
applicable_versions: Android 9 (API 28) - Android 17 (API 37)
last_verified: '2026-08-19'
last_verified_against: "Android 17 android-17.0.0_r1 platform source, Android common kernel android17-6.18-2026-06_r6 and android16-6.12-2026-06_r6 scheduler source, Linux scheduler/energy-model/UClamp docs, Perfetto stdlib docs"
confidence: high
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/5.28-android17-pelt-boost-revert-amu-pmu-microarch-frequency-limiting.md"
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
  path: https://docs.kernel.org/scheduler/sched-util-clamp.html
- type: official
  path: https://docs.kernel.org/admin-guide/pm/cpuidle.html
- type: official
  path: https://docs.kernel.org/power/opp.html
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: aosp
  path: https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_util_Process.cpp
- type: android-common-kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c
- type: android-common-kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android16-6.12-2026-06_r6/kernel/sched/fair.c
- type: android-common-kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/power/energy_model.c
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
task6_state: "reviewed"
task9_state: reviewed
pipeline_stage: "ready-to-publish"
task2b_state: fixed
last_idle_audit_at: "2026-08-19T18:35:41+08:00"
last_idle_audit_run_id: "20260819-183541-idle-audit-58ee0272"
---


# 5.2 EAS 能量感知调度

> [!info] 源码锚点
> 正文按 Android 17 / API 37 / `android-17.0.0_r1` 与 Linux 内核分支 `android17-6.18-2026-06_r6` 复核。Linux 5.x、6.6、6.12 和 Android 10—16 只用于说明演进，不代表当前实现。

## 为什么要了解 EAS

上一节介绍了公平调度器（fair scheduler）怎样通过虚拟运行时间（vruntime）、滞后量（lag）和虚拟截止时间（virtual deadline）分配 CPU 时间。移动设备还要处理另一个目标：在不明显损害吞吐和响应的前提下降低能耗。

现代手机 SoC（System on Chip，片上系统）普遍采用大小核架构，详见 5.3 节。一个四小核加四大核的八核处理器，在安排任务时要判断任务应放在小核还是大核。小核更省电，但性能可能不足；大核性能更高，功耗也更高。如果调度器只看当前空闲程度，轻任务就可能被放到大核上，抬高频率和电压，并在前台交互阶段产生更多功耗与热量。

EAS（Energy Aware Scheduling，能量感知调度）在 Linux 5.0 合入主线。任务唤醒时，它先在每个性能域（performance domain）中找出有代表性的候选 CPU，再借助能量模型（Energy Model，EM）估算放置前后的活跃态能量差值。最终选择还要满足 CPU 亲和性（affinity）、cpuset、调度容量（capacity）和利用率钳制（Utilization Clamping，UClamp）等约束。

理解 EAS 后，打开一份 Perfetto Trace（性能轨迹）时，如果看到主线程在低 capacity CPU 上运行，或者在不同性能域之间迁移，就可以继续追查唤醒选核（wake-up placement）、负载均衡、UClamp 与温控（thermal）等决策依据。

## EAS 如何选择 CPU

### 从“找最快的核”到“找更省电的核”

不使用 EAS 时，fair 类任务的唤醒选核主要依据负载、空闲（idle）状态与缓存局部性（cache locality）选择 CPU。在异构系统里，只比较空闲程度，可能会把轻任务送到 capacity 较高、功耗成本也较高的性能域。

EAS 接管 fair 类任务的部分唤醒负载均衡。Linux 6.18 的 `select_task_rq_fair()` 仅在带有普通任务唤醒标志 `WF_TTWU`、且根调度域（root domain）未标记为过载（overutilized）时调用 `find_energy_efficient_cpu()`；fork/exec、无可用 EM 等情况会走其他路径。同步唤醒仍会进入该函数，但满足快速路径条件时可在 EM 估算前直接返回当前 CPU。EM 用来比较数个可接受候选的能量影响，目标是在尽量降低能耗的同时，减少对吞吐的影响。

例如，一个利用率（util）为 120 的轻量级任务需要被唤醒，系统中有两种核心：

- 小核：capacity 为 200，当前空闲；
- 大核：capacity 为 1024，当前空闲。

若小核的候选 CPU 通过 `fits_capacity(120, 200)`，EAS 会继续比较它与大核候选、任务上次运行的 CPU（`prev_cpu`）的能量增量。小核往往更合适，但结果仍取决于该性能域内其他 CPU 的利用率、UClamp、温控压力（thermal pressure）和 EM 成本，不能只凭 120 与 200 两个数断言目标 CPU。

### EAS 的前提条件

EAS 并非在所有设备上都生效。它需要满足以下条件：

1. **异构 CPU 拓扑**：调度域需要具备 `SD_ASYM_CPUCAPACITY_FULL`。当前 EAS 不支持对称 CPU 拓扑。
2. **能量模型可用**：root domain 需要关联已注册的性能域与功耗成本表（power cost table）。
3. **可缩放的利用率信号**：平台要实现 PELT 具备频率不变性（frequency invariance）和 CPU 不变性（CPU invariance）所需的架构回调。
4. **schedutil 调频策略**：EAS 假设 OPP 会跟随利用率变化。官方文档把 schedutil 视为符合这一假设的调频策略（governor）；不推荐搭配其他 governor。

是否满足这些条件要以目标设备为准。Android 公共内核（Android common kernel）提供框架，SoC 的 capacity、EM、CPU 调频框架 cpufreq 和调度域仍由设备内核与固件数据决定。

## 能量模型（Energy Model）

### OPP：频率-电压对的集合

EAS 的能耗预测依赖工作性能点（Operating Performance Point，OPP）提供的数据。

CPU 可以在多个频率、电压工作点之间切换，每个有效组合就是一个 OPP。下面的数字只用于展示表的形态，不对应任何量产 SoC：

| OPP | 频率 (MHz) | 电压 (mV) | 功耗 (mW) |
|-----|-----------|-----------|-----------|
| 0   | 300       | 600       | 15        |
| 1   | 600       | 650       | 30        |
| 2   | 900       | 720       | 60        |
| 3   | 1200      | 820       | 120       |
| 4   | 1500      | 950       | 200       |
| 5   | 1800      | 1100      | 380       |

表中的活跃态功耗成本（active power cost）随频率上升得很快。动态功耗常用 `P_dynamic ∝ C × V² × f` 解释，但整颗 CPU 的功耗还包含漏电、互连和平台相关成本，不能据此称为“指数增长”。EAS 使用注册到 EM 的成本表（cost table），不会在调度热路径里自行套用这条物理公式。

OPP 可以来自设备树（Device Tree）的 `operating-points-v2`，也可以由平台驱动提供。EM 的性能域通常对应共享性能状态的 CPU 集合；它与“外观上的 CPU 簇”经常重合，但最终边界应以 cpufreq 策略域（policy）和已注册的 EM 为准。

### 能量模型框架

Linux 内核的 EM 是一个独立于调度器的子系统。它给每个性能域维护一张活跃态功耗成本表，表项对应不同的性能状态（performance state）或 OPP。调度器通过 `em_cpu_energy()` 接口估算“把任务放进这个簇后，活跃运行态大概要消耗多少能量”。调用链为 `kernel/sched/fair.c::compute_energy()` → `em_cpu_energy()` → EM 性能状态与功耗表。

EM 只描述活跃运行态的功耗成本，不负责 CPU 空闲状态（idle state）。进入多深的 C-State（CPU 空闲低功耗状态）、停留多久，属于 CPUIdle governor（状态选择策略）和驱动的职责；观测时要看 `cpu_idle` 轨道、平台空闲态统计或内核空闲态数据。把 EM 和 CPUIdle 写成一张表，会把“频率点功耗”和“空闲驻留功耗”混成同一层概念。

EAS、温控 IPA（Intelligent Power Allocation，智能功率分配）和功耗上限控制子系统 powercap，都能复用 EM 提供的活跃态功耗基线。EAS 负责把任务放到合适的簇，CPUIdle 负责在空闲时选择 C-State；两者都会影响整机功耗，但读取的不是同一组接口。

### 能耗计算的主要关系

EAS 会为每个候选 CPU 计算能量增量（energy delta）：

```text
energy_delta = 放置任务后的系统总能耗 - 当前的系统总能耗
```

计算结果用于选择 `energy_delta` 最小的候选 CPU。

具体来说，它会：

1. 计算目标 CPU 放置任务后的预期利用率（utilization）；
2. 根据利用率查询 EM，确定需要运行的 OPP（频率）；
3. 用该 OPP 的功耗值，结合该 CPU 上其他任务的利用率，计算总能耗；
4. 对每个候选 CPU 重复上述计算，选出总能耗最低的候选。

这是一种近似计算：它假设频率请求会跟随利用率选择相应 OPP。`schedutil` 与这项假设最一致，因此官方文档只推荐 EAS 搭配 schedutil；固定频率或采用不同输入信号的 governor 会降低预测可信度。

## PELT：跟踪每个任务的“繁忙程度”

### 为什么需要利用率信号

EAS 的决策依赖任务利用率，这个信号由 PELT（Per-Entity Load Tracking，每个调度实体的负载跟踪）提供。这里的“调度实体”既可以是单个任务，也可以是任务组或 CPU 运行队列。

在 PELT 出现之前，内核通过每 CPU 运行队列（per-CPU runqueue）的负载来估算繁忙程度，但这种方式只反映 CPU 的整体负载，无法区分“一个 CPU 上跑了三个轻任务”和“一个 CPU 上跑了一个重任务”。EAS 需要知道**每个任务**需要多少计算能力，才能合理选核。

PELT 从 Linux 3.8 开始引入，它为每个调度实体（单个任务、任务组、CPU runqueue）维护独立的 utilization 信号 `util_avg`。

### PELT 的计算方式

PELT 使用指数衰减累计利用率，常说的 32 ms 指半衰期；该信号没有到点清空的固定窗口。持续满载任务的信号会逐步逼近上限，停止运行后也会逐步衰减。具体表现为：

- 突发负载的 `util_avg` 不会在第一个周期内立即达到真实需求；
- 任务停止运行后，历史贡献仍会保留一段时间；
- `util_est` 与 UClamp 分别补充短期需求预测和用户空间性能提示。

PELT 的 `util_avg` 被归一化到 0～1024。其中 1024 代表“一个最大 capacity 的 CPU 满负荷运行”。经过归一化，`util_avg` 可以直接与 CPU 的 `capacity` 比较：如果任务的 `util_avg` 是 300，而小核的 `capacity` 是 400，EAS 就知道这个任务放在小核上“装得下”。

### 频率不变性与 CPU 不变性

PELT 的利用率信号要能在大小核之间准确比较，需要满足两种“不变性”：

1. **频率不变性（Frequency Invariance）**：同一工作负载不应因为当前频率较低、占用实际经过时间（wall time）更长，就被永久误判为更重。架构通过 `arch_scale_freq_capacity()` 提供当前频率的相对能力。

2. **CPU 不变性（CPU Invariance）**：同一工作负载迁到不同 capacity 的 CPU 后，利用率信号仍应表达可比较的计算需求。`arch_scale_cpu_capacity()` 提供各 CPU 相对于系统最强 CPU 的 capacity。

这两个缩放量参与 PELT 更新和 capacity 比较。它们缺失或不准确时，同一工作负载在不同频率、不同 CPU 上形成的信号将不可比，EAS 的能量预测也会失去基础。

### WALT 与设备差异

Linux 主线的 EAS 文档建立在 PELT 及其频率不变性和 CPU 不变性之上，并没有把 WALT 当成前提。WALT（Window Assisted Load Tracking，窗口辅助负载跟踪）是部分 Android 公共内核或厂商内核使用过的负载跟踪扩展，常见于追求更快突发响应的设备内核。它会改变利用率信号的形成方式，但不会改变 EAS 依据利用率、capacity 和 EM 选核的基本逻辑。

分析具体设备时，可以分三层来看。Linux 主线内核这一层是 PELT → EAS → UClamp；Android 开源项目（AOSP）用户空间这一层是任务配置（task profile）、控制组（cgroup）和电源硬件抽象层（Power HAL）怎样把提示送进调度器；厂商设备层才涉及 WALT、性能增强钩子（boost hook）和额外迁核策略。把三层概括成“Android 12 统一回归 PELT”，容易混淆 Linux 主线、AOSP 和厂商内核。排查时应根据内核版本和厂商代码树确认实际使用的负载跟踪方式。

## 任务放置（Task Placement）：EAS 的选核策略

### `find_energy_efficient_cpu()` 的决策流程

当一个 fair 类任务通过 `WF_TTWU` 被唤醒，且 root domain 未标记为 overutilized 时，`select_task_rq_fair()` 才会尝试调用 `find_energy_efficient_cpu()`。该函数只负责**唤醒选核**；fork/exec 时的任务放置、周期负载均衡、CPU 即将空闲时的 `newidle balance`，以及任务与 CPU capacity 不匹配时的迁移（misfit migration），各有自己的入口，不会在这里进行 EM 估算。Linux 6.18 的主要流程如下：

**第一步：处理快速路径。** 同步唤醒时，如果当前 CPU 只有当前任务运行、目标线程允许在该 CPU 运行，且 `task_fits_cpu()` 成立，函数可直接返回当前 CPU。任务的 `task_util_est()` 为 0 且 `uclamp.min` 也为 0 时，则保留上次运行的 CPU（`prev_cpu`），不做缺少利用率依据的能量预测。

**第二步：筛选候选。** 对每个性能域，代码过滤离线 CPU、调度域外 CPU、任务 CPU 亲和性掩码 `p->cpus_ptr` 不允许的 CPU，以及 `util_fits_cpu()` 返回 0 的 CPU。返回负值表示实际利用率能放下，但 CPU 无法满足 `uclamp.min`；这类 CPU 会保留到后续 capacity 比较。每个性能域最终留下适配等级更好、剩余 capacity（spare capacity）更大的候选，并把可用的 `prev_cpu` 纳入比较。

**第三步：计算能量增量。** `compute_energy()` 先计算不含被唤醒任务的基准能量 `base_energy`，再模拟把任务放到 `prev_cpu` 或候选 CPU。计算会使用该性能域的繁忙时间（busy time）、最大有效利用率、UClamp 和实际 capacity，经 `em_cpu_energy()` 得到活跃态能量成本。

**第四步：比较适配程度与能量增量。** 候选能满足性能提示时，优先选择能量增量更低者；若候选都无法满足 `uclamp.min`，代码还会比较可用 capacity。没有更优候选时保留 `prev_cpu`。Linux 6.18 的判断没有“能量差低于固定百分比就强制上大核”这类通用阈值。

### 轻任务与重任务的策略差异

EAS 对轻任务和重任务有不同的处理方式：

**轻任务（利用率较低）**：若低 capacity 性能域能容纳任务，且其能量增量更低，EAS 常会选择该性能域。后台任务、心跳检测和短 UI 回调是否属于“轻任务”，仍要看目标设备上的 PELT、`util_est` 与 UClamp，不能只按线程名分类。

**重任务（利用率接近或超过低 capacity CPU 的能力）**：低 capacity 候选可能无法通过 `util_fits_cpu()`，capacity 更高的性能域因而成为候选。视频编解码、游戏渲染和应用启动主线程也可能包含等待阶段，不能把整个线程生命周期都标成重任务。

### 全大核架构的调度边界

部分新 SoC 不再采用传统“四小核 + 四大核”命名，市场上常把这类设计称为“全大核”。不过，只要调度拓扑仍存在不同 capacity，且注册了对应 EM，EAS 的判断框架就没有变化。某个 CPU 的 capacity 数字来自具体内核代码树、频率上限与架构缩放，不能从产品宣传中的核心名称推算。

capacity 差距变小，不代表功耗成本差距也变小。分析这类设备时，应读取调度器 capacity、cpufreq policy、EM 和 thermal pressure，再解释选核、频率与迁移。仅凭“全大核”标签推导能效空间或迁移代价，证据不足。

### 负载均衡与任务迁移

运行中的任务迁移仍由周期负载均衡、`newidle balance`、主动均衡（active balance）和 misfit 等路径处理。这些路径依据调度域、负载、capacity 与 CPU 亲和性作判断，不会为每次迁移调用 `compute_energy()`。

EAS 与基于负载的均衡以 root domain 的 **overutilized 标志** 为分界。`fits_capacity(util, capacity)` 预留约 20% 余量（margin）；root domain 中有 CPU 越过该临界点（tipping point）后，EAS 会被关闭，负载均衡器（load balancer）重新参与选核。这里的利用率还会计入实时调度类（RT）、截止时间调度类（deadline）和硬件中断（IRQ）等占用造成的 capacity 损失。

overutilized 对 EAS 的影响随内核版本有差异：

- **Linux 6.6 及更早版本**：`find_energy_efficient_cpu()` 在入口处检查 `rd->overutilized`。系统已过载时，它直接跳过能量估算，回到传统选核路径。
- **`android16-6.12` 公共内核分支**：overutilized 的短路检查从 `find_energy_efficient_cpu()` 函数入口移到调用点 `select_task_rq_fair()`。行为不变：系统过载时，唤醒路径跳过能量估算，重新使用基于负载的选择与均衡。该分支的 `find_energy_efficient_cpu()` 已接收 `sync` 参数，并在同步唤醒快速路径满足条件时直接返回当前 CPU。
- **Android 17 / `android17-6.18-2026-06_r6`**：调用点仍通过 `is_rd_overutilized(this_rq()->rd)` 保护 `find_energy_efficient_cpu()`；该函数沿用 `sync` 参数与同步唤醒快速路径。

因此，无论 Linux 6.6、`android16-6.12` 还是 Linux 6.18，root domain 过载时都不会执行 EAS 能量估算。此时不能再用“EM 选择了这个 CPU”解释 Trace。

## UClamp：用户空间性能提示

### UClamp 的作用

EAS 以 PELT、`util_est`、capacity 和 EM 为基础。用户空间还可以用 UClamp 描述任务期望的最低或最高性能点。

用户空间掌握业务截止时间（deadline）和进程状态，能够补充历史利用率暂时无法表达的信息。例如，突发帧任务的 PELT 尚未升高时，系统可能已经知道它需要较快响应。

UClamp 允许用户空间为每个任务设置有效利用率的上下限：

- **UCLAMP_MIN**：设置有效利用率的下限。`UCLAMP_MIN=512` 会让选核与 schedutil 至少考虑这一性能提示，但目标 CPU 和实际频率仍受 capacity、其他任务、cpufreq、温控与厂商策略影响。

- **UCLAMP_MAX**：设置有效利用率的上限，可限制调频与按 capacity 选核时采用的性能提示。它不是 CPU 时间配额，不会阻止任务继续运行，也不保证线程永远不去高 capacity CPU。

### Android 中的 UClamp 使用

Android 平台通常由 Framework 和进程组管理库 `libprocessgroup` 应用调度提示，普通应用无须直接写 cgroup 文件。AMS（ActivityManagerService）中的 `OomAdjuster` 先根据进程状态给进程或线程分配调度组（sched group），随后由 `android.os.Process.setThreadGroup()`、`setThreadGroupAndCpuset()` 或 `setProcessGroup()` 进入 JNI。Android 17 的 `android_util_Process.cpp` 中，线程分组路径调用 `SetTaskProfiles()`，进程分组路径调用 `SetProcessProfilesCached()`；冻结、解冻等进程配置（profile）路径会直接调用 `SetProcessProfiles()`。`libprocessgroup` 读取 `system/core/libprocessgroup/profiles/task_profiles.json`，把任务配置展开为加入 cgroup 和设置属性两类动作。

### UClamp 聚合方式的演进

Linux 主线内核以及 Android 17 `android17-6.18-2026-06_r6` 的 UClamp 请求采用最大值与分桶（max/bucket）聚合策略。运行队列分别维护 `UCLAMP_MIN` 与 `UCLAMP_MAX` 的 bucket，并取已入队任务中最高的有效请求。这里聚合的是 UClamp 边界，不会取代 PELT 对运行队列实际利用率的求和。

例如，三个任务的 `uclamp.min` 都是 200，而 PELT 总利用率已达 300，调度器会结合实际利用率 300 与运行队列的 UClamp 边界 200 得出有效值，不会把 300 降到 200。最大值聚合的局限主要体现在多个 UClamp 请求怎样合并，尤其会影响 `UCLAMP_MAX` 的节能语义；不能把它解释成“多任务真实负载只取最大单任务值”。厂商若改变聚合方式，应以对应内核代码树为准。

在 Android 10、11、12 各版本中，排查路径应分层检查：

- **Android 10**：任务配置已经能操作 `cpu.util.min` / `cpu.util.max`，但默认性能档位仍大量依赖 `/dev/stune/{background,foreground,top-app}` 和 `schedtune.boost` / `schedtune.prefer_idle`；cpuset 单独决定线程允许在哪组 CPU 上运行。
- **Android 11**：AOSP 把 CPU 控制器的接口名改为 `cpu.uclamp.min` / `cpu.uclamp.max`，默认配置仍保留 `schedtune` 分组。此时 UClamp 文件名已经就位，但默认性能档位还没有完全离开 SchedTune。
- **Android 12 及以后**：AOSP 默认的 `HighEnergySaving` / `HighPerformance` / `MaxPerformance` 直接加入 `cpu/{background,foreground,top-app}`，`cpuset` 继续负责 CPU 集合约束，冻结控制器（freezer）迁到 cgroup v2。至此，top-app、foreground 和 background 三档把 UClamp 提示纳入默认用户空间路径。

排查具体设备时，至少检查三处：

1. 查看 `/proc/<tid>/cgroup`，确认线程位于哪个 `cpu`、`cpuset` 或 `schedtune` 分组；
2. 查看相应 cgroup 目录中的 `cpu.uclamp.min` 和 `cpu.uclamp.max`，旧设备还要检查 `cpu.util.min` / `cpu.util.max` 与 `/dev/stune/*/schedtune.boost`；
3. 查看 `/proc/<tid>/sched`，核对该线程最终暴露给调度器的利用率和 UClamp 相关字段。字段名会随内核版本变化，通常要连同 `schedutil`、频率轨道和 CPU 迁移一起分析。

这条控制链可以解释同一个 Android 渲染线程（RenderThread）为什么在 top-app 状态更容易被选到大核，而切到后台后又回到小核。

## EAS 在 Perfetto 中的观察

### 三条关键轨道

Perfetto 不会直接标明“这次由 `find_energy_efficient_cpu()` 选核”。它提供调度、频率和空闲态结果，分析时还要结合 overutilized、UClamp、thermal 与设备内核。主要关注以下三条轨道（Track）：

**1. CPU 频率轨道（CPU Frequency Track）**

CPU 频率轨道记录 cpufreq 变化。频率请求可能来自 schedutil 对 PELT 和 UClamp 的计算，也可能受 cpufreq policy 的共享范围、Power HAL、温控上限（thermal cap）和硬件自治调频影响，不能把每次变化只归因于 EAS。

重点关注：

- 频率上限是否突然降低，例如 `scaling_max_freq` 被调低；这通常表示温控已经介入，详见 5.5 节；
- 同簇 CPU 的频率是否同步变化；移动 SoC 通常以簇为单位调频；
- 任务运行期间的频率是否合理。如果高负载任务运行时频率被限制在低位，性能瓶颈可能来自系统策略，而非任务代码。

**2. CPU 调度轨道（CPU Scheduling Track，`sched_switch`）**

CPU 调度轨道显示每个时刻哪个线程在哪个 CPU 上运行，是观察 EAS 选核和迁移结果的直接窗口。

重点观察：

- **目标 CPU 是否满足截止时间**：主线程和 RenderThread 无须默认常驻大核；能否满足帧预算，取决于运行时 capacity、频率和排队时间；
- **迁移是否与性能下降相关**：迁移会影响缓存局部性，但负载均衡和温控迁移也属于正常行为。要把迁移点与可运行态等待时间（runnable wait）、CPU 周期数（CPU cycles）、缓存未命中（cache miss）和实际经过时间（wall time）对齐；
- **唤醒关系是否完整**：采集 `sched_waking` 后，才能从唤醒关系解释目标 CPU；只看 `sched_switch` 无法还原全部唤醒选核过程。

**3. CPU 空闲状态轨道（CPU Idle States Track）**

这条轨道显示 CPU 的空闲状态变化。Linux 6.18 的 EAS 能量模型只描述活跃态功耗，不计算空闲状态成本；`find_energy_efficient_cpu()` 的注释也明确说明，它无法仅凭当前 EM 判断“把小任务集中到一个 CPU、让另一个 CPU 深度休眠”是否更省电。

空闲态驻留仍是分析整机功耗的重要证据，但它反映的是 EAS、CPUIdle governor、定时器、IRQ、后台唤醒和设备驱动的共同结果。大核频繁退出深度空闲态（deep idle）只能说明需要继续查找唤醒源，不能单独证明 EAS 配置错误。

### 使用 SQL 分析 EAS 行为

Perfetto 适合用来回答三个问题：线程到底在哪些 CPU 上运行、这些 CPU 当时运行在什么频率，以及连续的空闲态驻留是否被频繁唤醒打断。SQL 最好同时带上进程名和线程名，避免在多进程 Trace 中只按线程名查询而取得错误的唯一线程 ID（`utid`）。

**统计目标线程在各 CPU 上的运行时间：**

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
FROM sched_slice
WHERE utid = (SELECT utid FROM target_thread)
GROUP BY cpu
ORDER BY cpu;
```

如果 RenderThread 大部分时间位于低 capacity CPU，应把运行时长与帧截止时间对齐，再检查当时的 UClamp、进程组、overutilized 和 thermal pressure。CPU 类型要由设备的 capacity 与拓扑确认，不能只看 CPU 编号。

**统计各 CPU 的频率驻留时间：**

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

`cpu_frequency_counters` 是 Perfetto 标准库（stdlib）中的表，列名为 `freq`、`cpu` 和 `dur`。如果当前环境没有加载 stdlib，再使用原始的 `counter` / `counter_track` 查询方案。

**统计 CPU 空闲态驻留时间：**

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

`idle = -1` 表示 CPU 处于活跃状态；非负编号如何对应具体 C-State，要对照目标设备的 cpuidle 状态表。较大编号通常表示更深的空闲状态，但这些编号在不同设备上并不对应统一的状态名称。

**怎样判断系统是否 overutilized**

官方文档把 overutilized 的临界条件描述为 CPU 利用率超过其计算能力（compute capacity）的 80%。Perfetto 没有统一的 `sched_overutilized` 轨道，因此 SQL 只能提供排查线索，不能只凭“小核几乎没有空闲时间”下结论。应结合观察小核的运行时间占比（running ratio）是否持续偏高、同簇频率是否长期接近上限、关键线程是否转移到大核，再用设备内核导出的调度器调试信息确认。

## 与其他机制的关系

### EAS 与 fair 调度器（5.1 节）

EAS 只处理 fair 类任务的部分唤醒选核；Linux 6.18 仍由 EEVDF（Earliest Eligible Virtual Deadline First，最早合格虚拟截止时间优先）决定 CPU 运行队列中接下来执行哪个任务。root domain 处于 overutilized 状态时，`select_task_rq_fair()` 会跳过能量估算；同步唤醒还可能进入 `find_energy_efficient_cpu()` 内部的快速路径。一份 Trace 中可以同时看到 EAS 唤醒选核、EEVDF 运行队列竞争和后续负载均衡的结果。

### EAS 与大小核架构（5.3 节）

EAS 的收益取决于 capacity 的不对称程度和各性能域的 EM 成本。传统的小核、大核命名便于理解，但源码仍根据调度拓扑与 EM 作判断。

### EAS 与 DVFS（5.4 节）

EAS 的能耗预测依赖 schedutil governor 的 DVFS（Dynamic Voltage and Frequency Scaling，动态电压与频率调节）行为。5.4 节会详细介绍 DVFS 机制，以及 Power HAL 的场景策略如何影响 CPU 频率；这些因素会直接影响 EAS 的预测准确性。

### EAS 与温控管理（5.5 节）

温控可以通过 cpufreq cooling（以限制 CPU 频率进行散热）等机制降低频率上限，并以 thermal pressure 扣减可用 capacity。Linux 6.18 的 EAS 候选筛选与能量环境会读取实际 capacity，因此温控既可能改变频率，也可能改变任务是否适合某个 CPU 以及最终放置位置。

### EAS 与 UClamp/SchedTune

如果把 SchedTune 与 UClamp 的关系概括成“Linux 5.3 之后完全替换”，就会忽略 Android 用户空间的演进。Linux 主线在 5.3 引入 UClamp，并在 5.4 提供 cgroup 接口；AOSP 在 Android 10 和 11 的默认性能配置中仍大量使用 `schedtune` 分组，Android 12 的默认配置才开始直接加入 `cpu/{background,foreground,top-app}`。厂商设备是否继续保留 WALT 钩子、性能增强路径（boost path）或自定义 SchedTune 行为，需要根据设备内核代码树和任务配置核实。

EAS 使用有效利用率、capacity 与 EM。SchedTune 或 UClamp 会改变部分输入，让 top-app 组更容易获得较高性能点，并约束 background 组的性能提示；最终结果还受 CPU 亲和性、cpuset、负载、overutilized 和温控影响。

## 常见问题与误区

### “EAS 是为了让系统变慢来省电”

EAS 的目标是降低完成单位工作所需的能量（energy per work），并把吞吐影响控制在较小范围。低利用率任务可能进入低成本性能域；高利用率任务或 `uclamp.min` 较高的任务可能需要高 capacity 性能域。root domain 进入 overutilized 状态后，唤醒路径会跳过能量估算，转回基于负载的策略。

### “任务应该尽量放在大核上以保证性能”

高 capacity CPU 能缩短部分计算时间，也可能提高该性能域的活跃态功耗。选核应综合考虑截止时间、利用率、capacity 与 EM 成本；“固定在大核”会绕过 EAS 的候选范围，还可能增加排队时间和热压力。

### “看到任务在小核上就是 EAS 有问题”

先确认该 CPU 的实际 capacity，以及任务当时的利用率、`util_est`、UClamp 与截止时间。低 capacity CPU 若能按时完成工作，这次放置就可能合理；若任务已经错过截止时间，再继续排查 cpuset、thermal pressure、overutilized、EM、利用率信号和厂商钩子（vendor hook）。

### “厂商的定制调度器比原版 EAS 好”

厂商定制可能加入 WALT、游戏或启动性能提示（hint）、vendor hook 和额外迁移策略。效果必须通过目标设备的延迟、能耗与热稳态数据判断。分析 Perfetto 前，应先确认内核代码树、Power HAL 和任务配置，避免把公共内核行为直接套用到厂商分支。

## 版本演进

| 维度 | 时间节点 | 变化 | 排查要点 |
|------|----------|------|----------|
| Linux 主线内核 | Linux 3.8 | 引入 PELT | 为 EAS 提供每个调度实体的利用率信号 |
| Linux 主线内核 | Linux 5.0 | EAS 合入主线 | `find_energy_efficient_cpu()` 基于 EM 进行唤醒选核 |
| Linux 主线内核 | Linux 5.3 | UClamp 合入主线 | 任务可以声明最低和最高性能点 |
| Linux 主线内核 | Linux 5.4 | UClamp cgroup 接口合入 | 用户空间可以通过 cgroup 统一设置 UClamp |
| AOSP 用户空间 | Android 10 | `task_profiles` 机制成型；CPU 控制器暴露 `cpu.util.min/max`，默认性能档位仍大量依赖 `schedtune` 与 `cpuset` | 检查 `/dev/stune/*` 和 `/dev/cpuset/*` |
| AOSP 用户空间 | Android 11 | 使用 `cpu.uclamp.min/max` 命名，默认配置仍保留 `schedtune` 分组 | 同时核对 `schedtune` 与 `cpu.uclamp.*` |
| AOSP 用户空间 | Android 12+ | 默认的 `HighEnergySaving` / `HighPerformance` / `MaxPerformance` 直接进入 `cpu/{background,foreground,top-app}`，cpuset 继续控制可运行 CPU 集合 | 检查 top-app、foreground 和 background 的默认提示路径 |
| Android 公共内核 | `android16-6.12` 分支 | overutilized 短路位置从 `find_energy_efficient_cpu()` 内部移到 `select_task_rq_fair()` 调用点；行为不变 | Linux 6.6 和 6.12 的检查位置不同，短路行为一致 |
| Android 公共内核 | Android 17 / `android17-6.18-2026-06_r6` | `find_energy_efficient_cpu()` 沿用 `sync` 参数；同步唤醒且当前 CPU 只有当前任务运行、任务 CPU 掩码允许并通过 `task_fits_cpu()` 时，可直接返回当前 CPU | 排查 Android 16/17 公共内核的唤醒选核时，还要检查同步唤醒快速路径 |
| Android 公共内核 | Android 17 / `android17-6.18-2026-06_r6` | UClamp 请求仍按 max/bucket 聚合，PELT 运行队列利用率仍按任务贡献累计 | 不要把 UClamp 最大值聚合误写成“CPU 总利用率取最大单任务值” |
| 设备实现 | 厂商分支 | WALT、Power HAL 性能增强和额外迁核策略随 SoC 与内核代码树变化 | Trace 结论必须结合具体设备 |

## 参考资料

- Linux 内核文档：[Energy Aware Scheduling](https://docs.kernel.org/scheduler/sched-energy.html)
- Linux 内核文档：[Utilization Clamping](https://docs.kernel.org/scheduler/sched-util-clamp.html)
- Linux 内核文档：[Energy Model framework](https://docs.kernel.org/power/energy-model.html)
- Linux 内核文档：[CPU Idle Time Management](https://docs.kernel.org/admin-guide/pm/cpuidle.html)
- Linux 内核文档：[Operating Performance Points (OPP)](https://docs.kernel.org/power/opp.html)
- Perfetto 官方文档：[CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- Perfetto 官方文档：[Perfetto stdlib docs](https://perfetto.dev/docs/analysis/stdlib-docs)
- AOSP 源码：`platform/system/core/libprocessgroup/profiles/task_profiles.json`（`android-17.0.0_r1`；历史对比：android10/11/12-release）
- AOSP 源码：`frameworks/base/core/jni/android_util_Process.cpp`（`android-17.0.0_r1`，`SetTaskProfiles()` / `SetProcessProfilesCached()` 调用链）
- Android common kernel：`kernel/sched/fair.c`（`android16-6.12-2026-06_r6` 与 `android17-6.18-2026-06_r6`，`find_energy_efficient_cpu()` / overutilized / 同步唤醒快速路径）
- Android common kernel：`kernel/power/energy_model.c`（`android17-6.18-2026-06_r6`，EM 框架）
- [高爷 - Android Perfetto 系列 9:CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)
- ARM 社区：[EAS 设计与实现](https://www.linuxplumbersconf.org/event/2/contributions/133/)
