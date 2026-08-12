---
status: "finalized"
title: EAS 能量感知调度
chapter: '5.2'
section: '5.2'
applicable_versions: Android 9 (API 28) - Android 17 (API 37)
last_verified: '2026-07-09'
last_verified_against: Android 17 android-17.0.0_r1 platform source, Android common kernel android17-6.18, Linux 6.6/6.12 scheduler docs
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
task6_state: "reviewed"
task9_state: reviewed
pipeline_stage: "ready-to-publish"
task2b_state: fixed
---


# 5.2 EAS 能量感知调度

> [!info] 源码锚点
> 正文按 Android 17 / API 37 / `android-17.0.0_r1` 与 kernel `android17-6.18-2026-06_r6` 复核。Linux 5.x、6.6、6.12 和 Android 10—16 只用于说明演进，不代表当前实现。

## 为什么要了解 EAS

上一节介绍了 fair 调度器怎样通过 vruntime、lag 和 virtual deadline 分配 CPU 时间。移动设备还要处理另一个目标：在不明显损害吞吐和响应的前提下降低能耗。

现代手机 SoC（System on Chip，片上系统）普遍采用大小核架构，详见 5.3 节。一个四小核加四大核的八核处理器，在安排任务时要判断任务应放在小核还是大核。小核更省电，但性能可能不足；大核性能更高，功耗也更高。如果调度器只看当前空闲程度，轻任务就可能被放到大核上，抬高频率和电压，并在前台交互阶段产生更多功耗与热量。

EAS（Energy Aware Scheduling）在 Linux 5.0 合入主线。任务唤醒时，它先在每个 performance domain 中找出有代表性的候选 CPU，再借助 Energy Model 估算放置前后的 active energy 差值。最终的选择还要满足 affinity、cpuset、capacity 和 UClamp 等约束。

理解 EAS 的意义在于：打开一份 Perfetto Trace 时，看到主线程在低 capacity CPU 上运行，或者在不同 performance domain 之间迁移，可以继续追查 wake-up placement、负载均衡、UClamp 与 thermal 等决策依据。

## EAS 的核心思想

### 从"找最快的核"到"找最省电的核"

不使用 EAS 的 fair wake-up placement 主要依据负载、idle 状态与 cache locality 选择 CPU。在异构系统里，只比较空闲程度可能把轻任务送到高 capacity、高成本的性能域。

EAS 接管 fair task 的部分 wake-up balancing。kernel 6.18 的 `select_task_rq_fair()` 在 `WF_TTWU` 且 root domain 未被标记为 overutilized 时调用 `find_energy_efficient_cpu()`；fork/exec、同步唤醒 fast path、无可用 Energy Model 等情况还会走其他路径。Energy Model 用来在数个可接受候选之间比较能量影响，目标是尽量降低能耗，同时减少对吞吐的影响。

例如，一个 util 值为 120 的轻量级任务需要被唤醒，系统中有两种核心：

- 小核：capacity 200,当前空闲
- 大核：capacity 1024,当前空闲

若小核的候选 CPU 通过 `fits_capacity(120, 200)`，EAS 会继续比较它与大核候选、`prev_cpu` 的能量增量。小核往往更合适，但结果仍取决于该 performance domain 的其他 CPU 利用率、UClamp、thermal pressure 和 EM cost，不能只凭 120 与 200 两个数直接断言目标 CPU。


### EAS 的前提条件

EAS 并非在所有设备上都生效。它需要满足以下条件：

1. **异构 CPU 拓扑**：调度域需要具备 `SD_ASYM_CPUCAPACITY_FULL`。当前 EAS 不支持对称 CPU 拓扑。
2. **能量模型可用**：root domain 需要关联已注册的 performance domain 与 power cost table。
3. **可缩放的利用率信号**：平台要实现 frequency-invariant 和 CPU-invariant PELT 所需的架构回调。
4. **schedutil 调频策略**：EAS 假设 OPP 会跟随利用率变化。官方文档把 schedutil 视为与该假设一致的 governor；搭配其他 governor 不受推荐。

是否满足这些条件要以目标设备为准。Android common kernel 提供框架，SoC 的 capacity、EM、cpufreq 和调度域仍由设备内核与固件数据决定。

## 能量模型（Energy Model）

### OPP：频率-电压对的集合

EAS 的能耗预测依赖 OPP（Operating Performance Points）提供的数据。

CPU 可以在多个频率、电压工作点之间切换，每个有效组合就是一个 OPP。下面的数字只用于展示表的形态，不对应任何量产 SoC：

| OPP | 频率 (MHz) | 电压 (mV) | 功耗 (mW) |
|-----|-----------|-----------|-----------|
| 0   | 300       | 600       | 15        |
| 1   | 600       | 650       | 30        |
| 2   | 900       | 720       | 60        |
| 3   | 1200      | 820       | 120       |
| 4   | 1500      | 950       | 200       |
| 5   | 1800      | 1100      | 380       |

表中的 active power cost 随频率上升得很快。动态功耗常用 `P_dynamic ∝ C × V² × f` 解释，但整颗 CPU 的功耗还包含漏电、互连和平台相关成本，不能据此称为“指数增长”。EAS 使用注册到 Energy Model 的 cost table，不会在调度热路径里自行套用这条物理公式。

OPP 可以来自 Device Tree 的 `operating-points-v2`，也可以由平台驱动提供。Energy Model 的 performance domain 通常对应共享性能状态的 CPU 集合；它与“外观上的 CPU 簇”经常重合，但最终边界应以 cpufreq policy 和已注册 EM 为准。

### 能量模型框架

Linux 内核的 Energy Model（EM）是一个独立于调度器的子系统。它给每个 performance domain 维护一张 active power cost table，表项对应不同的 performance state / OPP，调度器通过 `em_cpu_energy()` 接口估算“把任务放进这个簇后，活跃运行态大概要花多少能量”。调用链是 `kernel/sched/fair.c::compute_energy()` → `em_cpu_energy()` → EM performance state / power table。

EM 只描述活跃运行态的功耗成本，不负责 CPU idle state。C-State 进入多深、停留多久，属于 CPUIdle governor 和 driver 的职责，观测时要看 `cpu_idle` 轨、平台 idle 统计或内核 idle 数据。把 EM 和 CPUIdle 写成一张表，会把"频率点功耗"和"空闲驻留功耗"混成同一层概念。

EM 之所以重要，是因为 EAS、thermal IPA、powercap 这类子系统都能复用同一套 active power 基线。EAS 负责把任务放到合适的簇，CPUIdle 负责在空闲时选 C-State,两个方向都会影响整机功耗，但读取的不是同一组接口。

### 能耗计算的核心公式

EAS 的能耗预测并不复杂。对每个候选 CPU,它计算的是一个能量增量（energy delta):

```text
energy_delta = 放置任务后的系统总能耗 - 当前的系统总能耗
```

选择 energy_delta 最小的那个候选 CPU。

具体来说，它会：

1. 计算目标 CPU 在放置任务后的预期 utilization
2. 根据 utilization 查询 EM，确定需要运行的 OPP（频率）
3. 用该 OPP 的功耗值，结合该 CPU 上其他任务的 utilization,计算总能耗
4. 对每个候选 CPU 重复上述计算，选出总能耗最低的

这个计算是近似的：它假设频率请求会跟随 utilization 选择相应 OPP。`schedutil` 与这项假设最一致，因此官方文档只推荐 EAS 搭配 schedutil；固定频率或采用不同输入信号的 governor 会降低预测可信度。

## PELT:追踪每个任务的"繁忙程度"

### 为什么需要"利用率"信号

EAS 的决策依赖任务利用率，这个信号由 PELT（Per-Entity Load Tracking）提供。

在 PELT 出现之前，内核通过 per-CPU runqueue 的负载来估算任务的繁忙程度，但这种方式有一个缺陷：它只反映了 CPU 的整体负载，无法区分"一个 CPU 上跑了三个轻任务"和"一个 CPU 上跑了一个重任务"。EAS 需要知道**每个任务**需要多少计算能力，才能做出合理的选核决策。

PELT 从 Linux 3.8 开始引入，它为每个调度实体（单个任务、任务组、CPU runqueue）维护独立的 utilization 信号 `util_avg`。

### PELT 的计算方式

PELT 使用指数衰减累计 utilization，常说的 32 ms 指半衰期；该信号没有到点清空的固定窗口。持续满载任务的信号会逐步逼近上限，停止运行后也会逐步衰减。具体表现为：

- 突发负载的 `util_avg` 不会在第一个周期内立即达到真实需求；
- 任务停止运行后，历史贡献仍会保留一段时间；
- `util_est` 与 UClamp 可以分别补充短期需求预测和用户空间性能提示。


PELT 的 `util_avg` 被归一化到 0~1024 的范围。其中 1024 代表"一个最大 capacity 的 CPU 满负荷运行"。这个归一化的作用是让 `util_avg` 可以直接与 CPU 的 `capacity` 比较：如果任务的 `util_avg` 是 300,而小核的 `capacity` 是 400,EAS 就知道这个任务放在小核上"装得下"。

### 频率不变性与 CPU 不变性

PELT 的 util 信号要能在大小核之间准确比较，需要满足两个"不变性":

1. **频率不变性（Frequency Invariance）**：同一工作负载不应因为当前频率较低、占用墙上时间更长就被永久误判为更重。架构通过 `arch_scale_freq_capacity()` 提供当前频率相对能力。

2. **CPU 不变性（CPU Invariance）**：同一工作负载迁到不同 capacity 的 CPU 后，利用率信号仍应表达可比较的计算需求。`arch_scale_cpu_capacity()` 提供各 CPU 相对系统最强 CPU 的 capacity。

这两个缩放量参与 PELT 更新和 capacity 比较。缺失或不准确时，同一个 workload 在不同频率、不同 CPU 上形成的信号不可比，EAS 的能量预测也会失去基础。

### WALT 与设备差异

Linux mainline 的 EAS 文档建立在 PELT 及其 frequency / CPU invariance 之上，并没有把 WALT 当成前提。WALT（Window Assisted Load Tracking）是部分 Android common kernel 或厂商内核使用过的负载跟踪扩展，常见于追求更快突发响应的设备内核。它会改变 util 信号的形成方式，但不会改变 EAS 依据 util、capacity、EM 做选核这一核心逻辑。

分析具体设备时，按三层拆开看更清楚。主线内核这条线是 PELT → EAS → uclamp；AOSP 用户态是 task profile、cgroup 和 Power HAL 怎样把提示送进调度器；厂商设备才是 WALT、boost hook、额外迁核策略。把三条线压成"Android 12 统一回归 PELT"，容易把 mainline、AOSP 和 vendor 内核混成一件事。排查时按内核版本和厂商树确认具体负载跟踪实现。

## Task Placement：EAS 的选核策略

### find_energy_efficient_cpu 的决策流程

当一个 fair task 通过 `WF_TTWU` 被唤醒，且 root domain 未被标记为 overutilized 时，`select_task_rq_fair()` 才会尝试 `find_energy_efficient_cpu()`。该函数只负责 **wake-up placement**；fork/exec placement、周期负载均衡、newidle balance 和 misfit migration 各有入口，不在这里做 EM 估算。kernel 6.18 的核心流程如下：

**第一步：处理 fast path。** 同步唤醒时，如果当前 CPU 只有当前任务运行、目标线程允许在该 CPU 运行，且 `task_fits_cpu()` 成立，函数可直接返回当前 CPU。任务的 `task_util_est()` 为 0 且 `uclamp.min` 也为 0 时，则保留 `prev_cpu`，不做无依据的能量预测。

**第二步：筛选候选。** 对每个 performance domain，代码过滤 offline CPU、调度域外 CPU、`p->cpus_ptr` 不允许的 CPU，以及 `util_fits_cpu()` 返回 0 的 CPU。返回负值表示实际 util 能放下、但 CPU 无法满足 `uclamp.min`；这类 CPU 会保留到后续 capacity 比较。每个 domain 最终留下 fit 等级更好、spare capacity 更大的候选，并把可用的 `prev_cpu` 纳入比较。

**第三步：计算 energy delta。** `compute_energy()` 先算不含被唤醒任务的 `base_energy`，再模拟把任务放到 `prev_cpu` 或候选 CPU。计算会使用该 performance domain 的 busy time、最大有效利用率、UClamp 和实际 capacity，经 `em_cpu_energy()` 得到 active energy cost。

**第四步：比较 fit 与 energy delta。** 候选能满足性能提示时，优先选 energy delta 更低者；若候选都无法满足 `uclamp.min`，代码还会比较可用 capacity。没有更优候选时保留 `prev_cpu`。kernel 6.18 的判断没有“能量差低于固定百分比就强制上大核”这类通用阈值。

### 轻任务 vs 重任务的策略差异

EAS 对轻任务和重任务有不同的处理方式：

**轻任务（util 较低）**：若低 capacity domain 能容纳任务，且其 energy delta 更低，EAS 常会选这个 domain。后台任务、心跳检测和短 UI 回调是否属于“轻任务”，仍要看目标设备上的 PELT/util_est 与 clamp，不能只按线程名分类。

**重任务（util 接近或超过低 capacity CPU 的能力）**：低 capacity 候选可能无法通过 `util_fits_cpu()`，更高 capacity domain 因而成为候选。视频编解码、游戏渲染和应用启动主线程也可能包含等待型阶段，不能把整个线程生命周期固定标成重任务。

### 全大核架构的调度边界

部分新 SoC 不再采用传统“四小核 + 四大核”命名，但只要调度拓扑仍存在不同 capacity，且注册了对应 EM，EAS 的判断框架就没有变化。某个 CPU 的 capacity 数字来自具体 kernel tree、频率上限与架构缩放，不能从产品宣传中的核心名称推算。

capacity 差距变小不等于 power cost 差距也变小。分析这类设备时，应读取调度器 capacity、cpufreq policy、Energy Model 和 thermal pressure，再解释选核、频率与迁移。仅凭“全大核”标签推导能效空间或迁移代价，证据不足。

### 负载均衡与任务迁移

运行中的任务迁移仍由周期负载均衡、newidle balance、active balance 和 misfit 等路径处理。这些路径依据调度域、负载、capacity 与 affinity 做判断，不会为每次迁移调用 `compute_energy()`。

EAS 与基于负载的平衡以 root domain 的 **overutilized 标志** 为分界。`fits_capacity(util, capacity)` 预留约 20% margin；root domain 中有 CPU 越过该 tipping point 后，EAS 被关闭，load balancer 重新参与。这里的利用率还会计入 RT、deadline、IRQ 等占用造成的 capacity 损失。

overutilized 对 EAS 的影响随内核版本有差异：

- **Linux 6.6 及更早**：`find_energy_efficient_cpu()` 入口处检查 `rd->overutilized`，如果系统已 overutilized，直接跳过能量估算，回到传统选核路径。
- **android16-6.12 公共内核分支**：overutilized 的短路检查从 `find_energy_efficient_cpu()` 函数入口移到了调用点 `select_task_rq_fair()`。效果不变：系统 overutilized 时唤醒路径跳过能量估算，重新使用基于负载的选择与平衡。
- **Android 17 / `android17-6.18-2026-06_r6`**：调用点仍通过 `is_rd_overutilized(this_rq()->rd)` 保护 `find_energy_efficient_cpu()`；该函数还接收 `sync` 参数，并包含同步唤醒 fast path。

因此，无论 6.6、android16-6.12 还是 kernel 6.18，root domain overutilized 时都不会执行 EAS 能量估算。此时不能再用“EM 选择了这个 CPU”解释 Trace。

## UClamp：用户空间的性能提示

### uclamp 的作用

EAS 以 PELT、util_est、capacity 和 Energy Model 为基础。用户空间还可以用 UClamp 描述任务期望的最低或最高性能点。

用户空间掌握业务 deadline 和进程状态，能够补充纯历史利用率无法及时表达的信息。例如突发帧任务的 PELT 尚未升高，系统已经知道它需要较快响应。

这就是 uclamp（Utilization Clamping）的作用：它允许用户空间为每个任务设置 utilization 的上下限：

- **UCLAMP_MIN**：设置有效 utilization 的下限。`UCLAMP_MIN=512` 会让选核与 schedutil 至少考虑这一性能提示，但目标 CPU 和实际频率仍受 capacity、其他任务、cpufreq、thermal 与厂商策略影响。

- **UCLAMP_MAX**：设置有效 utilization 的上限，可限制调频与 capacity-aware placement 采用的性能提示。它不是 CPU 时间配额，不会阻止任务继续运行，也不保证线程永远不去高 capacity CPU。

### Android 中的 uclamp 使用

Android 平台通常由 framework 和 libprocessgroup 应用调度提示，普通应用无须直接写 cgroup 文件。AMS / OomAdjuster 先根据进程状态给进程或线程分配 sched group，随后 `android.os.Process.setThreadGroup()`、`setThreadGroupAndCpuset()`、`setProcessGroup()` 进入 JNI。Android 17 的 `android_util_Process.cpp` 中，线程分组路径调用 `SetTaskProfiles()`，进程分组路径调用 `SetProcessProfilesCached()`；冻结、解冻等进程 profile 路径会直接调用 `SetProcessProfiles()`。libprocessgroup 读取 `system/core/libprocessgroup/profiles/task_profiles.json`，把 profile 展开成加入 cgroup 和设置属性两类动作。

### UClamp 聚合方式的演进

主线内核以及 Android 17 `android17-6.18-2026-06_r6` 的 UClamp request 聚合采用 max/bucket 策略。runqueue 分别维护 `UCLAMP_MIN` 与 `UCLAMP_MAX` bucket，并取已入队任务中最高的有效 request。它聚合的是 clamp 边界，不会替代 PELT 对 runqueue 实际利用率的求和。

例如三个任务的 `uclamp.min` 都是 200，而 PELT 总 util 已达 300，调度器会在实际 util 300 与 rq clamp 边界 200 之间取有效结果，不会把 300 压回 200。max aggregation 的局限主要体现在多个 clamp request 怎样合并，尤其是 `UCLAMP_MAX` 的节能语义；不能把它解释成多任务真实负载只取最大单任务值。厂商若改变聚合方式，应以对应 kernel tree 为准。

在 Android 10、11、12 各版本中，排查路径应分层检查：

- **Android 10**:task profile 已经能操作 `cpu.util.min` / `cpu.util.max`,但默认的性能档位还是大量依赖 `/dev/stune/{background,foreground,top-app}` 和 `schedtune.boost` / `schedtune.prefer_idle`;cpuset 这条线单独决定线程允许跑在哪组 CPU 上。
- **Android 11**:AOSP 把 cpu controller 的接口名切到 `cpu.uclamp.min` / `cpu.uclamp.max`,默认 profile 仍保留 `schedtune` 分组，属于"uclamp 文件名到位了，默认性能档位还没完全离开 schedtune"的阶段。
- **Android 12 及以后**:AOSP 默认的 `HighEnergySaving` / `HighPerformance` / `MaxPerformance` 直接加入 `cpu/{background,foreground,top-app}`,`cpuset` 继续负责 CPU 集约束，freezer 迁到 cgroup v2。到这时，top-app / foreground / background 这三档才把 uclamp 提示纳入默认用户态路径。

排查具体设备时，至少检查三处：

1. `/proc/<tid>/cgroup`,确认线程落在哪个 `cpu` / `cpuset` / `schedtune` 分组。
2. 对应 cgroup 目录里的 `cpu.uclamp.min`、`cpu.uclamp.max`,旧设备再补看 `cpu.util.min` / `cpu.util.max` 和 `/dev/stune/*/schedtune.boost`。
3. `/proc/<tid>/sched`,核对该线程最终暴露给调度器的 util / clamp 相关字段；字段名会随内核版本变化，通常要连同 `schedutil`、频率轨和 CPU 迁移一起看。

这条控制链可以解释同一条 RenderThread 为什么在 top-app 状态被推到大核，而切回后台后又被压回小核。

## EAS 在 Perfetto 中的观察

### 三条关键 Track


Perfetto 不会直接标明“这次由 `find_energy_efficient_cpu()` 选核”。它提供调度、频率和 idle 结果，分析时还要结合 overutilized、UClamp、thermal 与设备内核。主要关注以下三条 Track：

**1. CPU Frequency Track**

CPU Frequency Track 记录 cpufreq 变化。频率请求可能来自 schedutil 对 PELT/UClamp 的计算，也可能受 policy 共享范围、Power HAL、thermal cap 和硬件自治调频影响，不能把每次变化只归因于 EAS。

重点关注：
- 频率是否有突然的上限限制（scaling_max_freq 被压低），通常表示温控介入了（详见 5.5 节）
- 同簇 CPU 的频率是否同步变化，移动 SoC 通常以簇为单位调频
- 任务运行期间频率是否合理，如果一个高负载任务运行时频率被限制在低位，性能瓶颈可能不在代码而在系统策略

**2. CPU Scheduling Track（sched_switch）**

CPU Scheduling Track 显示每个时刻哪个线程在哪个 CPU 核心上运行。这是观察 EAS 选核和迁移行为的直接窗口。

重点观察：
- **目标 CPU 是否满足 deadline**：主线程和 RenderThread 无须默认常驻大核；是否满足帧预算取决于运行 capacity、频率和排队时间。
- **迁移是否与退化相关**：迁移会影响 cache locality，但负载均衡和 thermal 迁移也属正常行为。要把迁移点与 runnable wait、CPU cycles、cache miss 和 wall time 对齐。
- **唤醒关系是否完整**：采集 `sched_waking` 后，才能从 wakeup 关系解释目标 CPU；只看 `sched_switch` 无法还原全部 wake-up placement。

**3. CPU Idle States Track**

这条 Track 显示 CPU 的 idle state 变化。kernel 6.18 的 EAS Energy Model 只描述 active power，不计算 idle state cost；`find_energy_efficient_cpu()` 的注释也明确说明，它无法仅凭当前 EM 判断“把小任务挤到一个 CPU、让另一个 CPU 深睡”是否更省电。

idle 驻留仍是整机功耗的重要证据，但它反映 EAS、CPUIdle governor、定时器、IRQ、后台唤醒和设备驱动的共同结果。大核频繁退出 deep idle 只能说明需要继续查唤醒源，不能单独判定 EAS 配置错误。

### 使用 SQL 分析 EAS 行为

Perfetto 更适合拿来回答三个问题：线程到底跑在哪些 CPU 上、这些 CPU 当时跑到什么频率、空闲驻留有没有被打碎。SQL 最好同时带进程名和线程名，避免多进程 Trace 里只按 thread name 取到错误 `utid`。

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
FROM sched_slice
WHERE utid = (SELECT utid FROM target_thread)
GROUP BY cpu
ORDER BY cpu;
```

如果 RenderThread 大部分时间位于低 capacity CPU，应把运行时长与帧 deadline 对齐，再检查当时的 clamp、进程组、overutilized 和 thermal pressure。核心类型要由设备 capacity/topology 确认，不能只看 CPU 编号。

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

`cpu_frequency_counters` 是 Perfetto stdlib 里的标准表，列名是 `freq`、`cpu`、`dur`。如果当前环境没有加载 stdlib,再退回原始 `counter` / `counter_track` 方案。

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

`idle = -1` 表示 CPU 处于 active 状态；非负编号如何对应具体 C-State，要对照目标设备的 cpuidle state 表。较大编号通常更深，但这不是跨设备的状态名称。

**怎么判断 overutilized**

官方文档里的 over-utilized 阈值是"CPU 使用量超过其 compute capacity 的 80%"。Perfetto 没有统一的 `sched_overutilized` 轨，所以 SQL 只能给排查线索，不能只凭"小核几乎没有 idle"就下结论。更稳妥的做法是把这几项一起看：小核 running ratio 是否持续偏高、同簇频率是否长期贴顶、关键线程是否被推向大核，再结合设备内核导出的 scheduler debug 信息确认。

## 与其他机制的关系

### EAS 与 fair 调度器（5.1 节）

EAS 只处理 fair task 的部分唤醒选核；kernel 6.18 的 CPU 内选人仍由 EEVDF 完成。root domain overutilized 时，`select_task_rq_fair()` 跳过能量估算；同步唤醒还可能命中 `find_energy_efficient_cpu()` 内部 fast path。一次 Trace 中可以同时看到 EAS wake-up placement、EEVDF runqueue 竞争和后续 load balance 的结果。

### EAS 与大小核架构（5.3 节）

EAS 的收益取决于 capacity 不对称程度和各 performance domain 的 EM cost。传统小核/大核命名方便理解，源码判断仍以调度拓扑与 Energy Model 为准。

### EAS 与 DVFS（5.4 节）

EAS 的能耗预测依赖于 schedutil governor 的 DVFS 行为。5.4 节会详细讲解 DVFS 机制，以及 Power HAL 的场景策略如何影响 CPU 频率，这些因素会直接影响 EAS 的预测准确性。

### EAS 与 Thermal 管理（5.5 节）

温控可以通过 cpufreq cooling 等机制降低频率上限，并以 thermal pressure 扣减可用 capacity。kernel 6.18 的 EAS 候选筛选和能量环境会读取实际 capacity，所以温控既可能改变频率，也可能改变任务是否 fit 以及最终放置。

### EAS 与 UClamp/SchedTune

把 SchedTune 和 uclamp 写成"Linux 5.3 之后完全替换"会丢掉 Android 用户态这层历史。对 mainline 来说，uclamp 是 Linux 5.3 引入、5.4 提供 cgroup 接口的标准机制；对 AOSP 来说，Android 10/11 的默认性能 profile 仍大量依赖 `schedtune` 分组，Android 12 的默认 profile 才开始直接加入 `cpu/{background,foreground,top-app}`。厂商设备是否继续保留 WALT hook、boost path 或自定义 schedtune 行为，要按设备 kernel tree 和 task profile 再核实。

EAS 使用有效 util、capacity 与 EM。SchedTune 或 UClamp 会改变部分输入，让 top-app 更容易获得较高性能点，让 background 的性能提示受到约束；最终结果还受 affinity、cpuset、负载、overutilized 和 thermal 影响。

## 常见问题与误区

### "EAS 是为了让系统变慢来省电"

EAS 的目标是降低 energy per work，并把吞吐影响控制在较小范围。低 util 任务可能进入低 cost domain；高 util 或较高 `uclamp.min` 任务可能需要高 capacity domain。root domain overutilized 后，唤醒路径会跳过能量估算并回到基于负载的策略。

### "任务应该尽量放在大核上以保证性能"

高 capacity CPU 能缩短部分计算时间，也可能提高该 performance domain 的 active power。选择应由 deadline、util、capacity 与 EM cost 共同决定；“固定在大核”会绕过 EAS 的候选空间，还可能增加排队和热压力。

### "看到任务在小核上就是 EAS 有问题"

先确认该 CPU 的实际 capacity、任务当时的 util/util_est、clamp 与 deadline。低 capacity CPU 若能按时完成工作，放置可能合理；若 deadline 已经违约，再继续排查 cpuset、thermal pressure、overutilized、EM、util 信号和 vendor hook。

### "厂商的定制调度器比原版 EAS 好"

厂商定制可能加入 WALT、游戏/启动 hint、vendor hook 和额外迁移策略。效果必须通过目标设备的延迟、能耗与热稳态数据判断。分析 Perfetto 前先确认 kernel tree、Power HAL 和 task profile，避免把公共内核行为套到厂商分支。

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
| Android common kernel | `android16-6.12` 分支 | overutilized 短路位置从 `find_energy_efficient_cpu()` 内部移到 `select_task_rq_fair()` 调用点；效果不变 | 6.6 和 6.12 的检查位置不同，短路行为一致 |
| Android common kernel | Android 17 / `android17-6.18-2026-06_r6` | `find_energy_efficient_cpu()` 增加 `sync` 参数；同步唤醒且当前 CPU 只有当前任务运行、任务 cpumask 允许并通过 `task_fits_cpu()` 时，可直接返回当前 CPU | Android 17 排查唤醒选核时，还要检查同步唤醒 fast path |
| Android common kernel | Android 17 / `android17-6.18-2026-06_r6` | UClamp request 仍用 max/bucket 聚合，PELT runqueue util 仍按任务贡献累计 | 不要把 clamp max aggregation 误写成 CPU 总 util 取最大单任务值 |
| 设备实现 | 厂商分支 | WALT、Power HAL boost、额外迁核策略按 SoC / kernel tree 变化 | Trace 结论必须落回具体设备 |

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
- Android common kernel：`kernel/sched/fair.c`（`android17-6.18-2026-06_r6`，`find_energy_efficient_cpu()` / overutilized）
- Android common kernel：`kernel/power/energy_model.c`（`android17-6.18-2026-06_r6`，EM 框架）
- [高爷 - Android Perfetto 系列 9:CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)
- ARM 社区：[EAS 设计与实现](https://www.linuxplumbersconf.org/event/2/contributions/133/)
