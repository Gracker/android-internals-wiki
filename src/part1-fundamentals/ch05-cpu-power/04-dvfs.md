---
title: DVFS 与功耗管理
chapter: '5.4'
section: '5.4'
status: finalized
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: '2026-06-29'
last_verified_against: AOSP android-17.0.0_r1 (frameworks/base, hardware/interfaces/power), Linux kernel 6.6 (android15-6.6), Linux kernel 6.12 (android16-6.12)
confidence: medium
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/5.21-android17-battery-optimization-soc-architecture.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.28-android17-pelt-boost-revert-amu-pmu-microarch-frequency-limiting.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.29-android17-gpu-dvfs-headroom-power-advisor.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.32-linux-610-bpf-dvfs-schedutil-loop.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.35-pms-cpuidle-schedutil.md"
sources:
- type: material
  path: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md
- type: aosp
  path: AOSP android-17.0.0_r1 (frameworks/base, hardware/interfaces/power)
- type: kernel
  path: kernel/sched/cpufreq_schedutil.c
tags:
  - dvfs
  - cpu-frequency
  - power-management
  - schedutil
  - opp
  - perfetto
related_chapters: 
task2b_state: fixed
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
---



# 5.4 DVFS 与功耗管理

> [!NOTE] 源码锚点
> 平台源码以 Android 开源项目（AOSP）`android-17.0.0_r1`（Android 17 / API 37）为准，Linux 内核调频路径以 `android17-6.18-2026-06_r6` 为准。厂商仍可替换 Linux CPU 调频框架 CPUFreq 的驱动、固件和电源硬件抽象层（Power HAL）策略，因此需要区分通用机制、Android 接口与设备实现。

## 先分清两个问题：完成得多快，以及消耗多少能量

调度器决定任务何时运行、运行在哪个 CPU 上；DVFS（Dynamic Voltage and Frequency Scaling，动态电压与频率调节）决定一个共享电压和频率的硬件域采用哪个性能档位。两者互相影响：

- 同一段 CPU 指令在高频下通常更早完成，但瞬时功率往往更高。
- 任务更早完成后，CPU 可能更早进入空闲态，整段工作的能量未必更高。
- 多个 CPU 共享一个频率策略时，一个繁忙 CPU 的需求可能抬高整个策略域的频率。
- 温控、电池电流限制或固件约束可以压低可用上限，即使调度器希望继续升频。

因此，看到掉帧附近出现低频，只能先提出“低频可能影响帧耗时”的假设。还要继续确认任务是否在运行、是否等待锁或 I/O、是否被迁移，以及设备报告的是软件请求档位还是硬件实测频率。

## DVFS 的物理基础

### 动态功耗、漏电功耗与能量

CMOS（Complementary Metal-Oxide-Semiconductor，互补金属氧化物半导体）电路的动态功耗常用下面的近似式说明：

**P_dynamic ≈ α × C × V² × f**

其中：

- `α` 是电路的翻转活动因子；
- `C` 是等效开关电容；
- `V` 是供电电压；
- `f` 是时钟频率。

这个式子说明，在其他条件近似不变时，电压对动态功耗呈平方关系，频率呈一次关系。它适合解释趋势，却不能直接预测整颗片上系统（System on Chip，SoC）或整机功耗。芯片还存在漏电功耗，漏电会随工艺、电压和温度变化；图形处理器（GPU）、内存、显示与电源转换损耗也没有包含在这个式子中。

讨论续航时还要从功率走到能量：

**E = ∫ P(t) dt**

低频会降低单位时间内的动态功率，也会延长任务执行时间。对短任务而言，先用高性能档位快速完成、随后进入更深空闲态，可能比长时间低速运行更省能，这种策略常称为“抢先完成后转入空闲”（race to idle）。结论要以同一工作量下的能量与完成时间为准，不能只看某个瞬时频点。

### 为什么频率与电压通常一起变化

更高时钟频率缩短了组合逻辑完成一次传播的时间。为了在目标温度和芯片个体差异下保留足够的时序裕量，也就是确保信号能在时钟边沿前稳定，较高频率通常需要较高电压。SoC 厂商会对芯片进行表征，为一个性能域提供经过验证的频率—电压组合。

由此可以得到更严谨的表述：

- 降低频率常常允许同时降低电压，因此节能幅度可能大于单独降低频率。
- 电压由平台认可的工作档位约束。随意降低到额定值以下（欠压）可能破坏时序稳定性，通用 Android 接口也不承诺支持欠压。
- 高频端的能效通常会变差，但拐点、幅度和可持续时间都依赖具体芯片、温度与封装，不能用一个固定 GHz 数字概括。

## OPP：离散的工作档位

OPP（Operating Performance Point，工作性能点）描述一个设备域可采用的性能状态，典型内容是频率和电压，也可以附带电流、功耗或硬件版本等约束。下面的表只用于说明离散档位，不对应任何量产 SoC：

| 示例档位 | 频率 | 电压 | 含义 |
| --- | ---: | ---: | --- |
| OPP 0 | 500 MHz | 650 mV | 低负载档 |
| OPP 1 | 1.2 GHz | 780 mV | 中间档 |
| OPP 2 | 2.0 GHz | 950 mV | 高性能档 |

Linux OPP 库位于 `drivers/opp/`。OPP 可以来自设备树（Device Tree），也可以由驱动或固件在运行时提供；平台还能根据芯片分档、温控状态等条件启用或禁用某些档位。因此：

1. 调频策略（governor）计算出的通常是性能需求或目标频率；
2. CPUFreq 驱动把目标解析到策略域（policy）允许且硬件支持的档位；
3. 固件、电源控制器和热管理还可能进一步约束最终状态；
4. 用户空间未必能看到完整的电压表，也不能假定 `scaling_available_frequencies` 在每台设备上存在。

在使用系统控制与管理接口（System Control and Management Interface，SCMI）、高级配置与电源接口（Advanced Configuration and Power Interface，ACPI）的协作式处理器性能控制（Collaborative Processor Performance Control，CPPC），或厂商固件的系统上，Linux 可能提交抽象性能等级（performance level）。这个等级如何映射到时钟、电压与电源域，由平台定义；查询一次等级也不等于独立测量了物理时钟。

## CPUFreq：核心层、governor 与驱动

Linux CPUFreq 可以分成三层理解：

| 层次 | 主要职责 |
| --- | --- |
| CPUFreq 核心层（core） | 维护 policy、频率上下限和 governor/driver 的公共接口 |
| 调频策略（governor） | 根据负载或用户策略计算性能需求 |
| 调频驱动（scaling driver） | 将需求提交给硬件寄存器、固件或性能状态接口 |

### policy 不等于单个 CPU

`/sys/devices/system/cpu/cpufreq/policyN/` 位于 sysfs，也就是 Linux 向用户空间暴露设备和内核对象状态的虚拟文件系统。这个目录表示一个 CPUFreq 策略域（policy），其中可以包含多个共享性能状态接口的 CPU。分析前可读取：

- `related_cpus`：属于该 policy 的 CPU；
- `scaling_driver`：当前驱动；
- `scaling_governor`：当前 governor；
- `scaling_min_freq` / `scaling_max_freq`：策略允许范围；
- `cpuinfo_min_freq` / `cpuinfo_max_freq`：驱动报告的硬件范围；
- `cpuinfo_transition_latency`：驱动能够提供时才有意义；
- `scaling_cur_freq`：通常是最近请求的性能状态（P-state）对应频率，不保证是物理时钟读数；
- `cpuinfo_cur_freq` 或 `cpuinfo_avg_freq`：驱动和硬件支持反馈时，才可能提供当前值或平均值。

这些节点的存在和权限由驱动、内核配置及设备策略决定。写入频率上下限会改变系统行为，需要超级用户（root）或调试权限，也可能破坏温控与性能策略。通用排障应先做只读采集；限频 A/B 对照实验应限定在可恢复的工程设备上，并记录温度、电量和工作负载。

## Android 17 内核中的 schedutil

schedutil 是按调度器利用率选择性能需求的 CPUFreq governor。`android17-6.18-2026-06_r6` 的主要实现位于 `kernel/sched/cpufreq_schedutil.c`。

### 利用率信号来自哪里

CFS（Completely Fair Scheduler，完全公平调度器）任务的利用率主要由 PELT（Per-Entity Load Tracking，每个调度实体的负载跟踪）维护。PELT 以 1024 微秒为周期衰减，半衰期约 32 毫秒；它不是“每隔固定毫秒统计一次”的滑动窗口。内核还会结合或约束多类信号：

- CFS 利用率与短期利用率估计 `util_est`；
- 运行队列（runqueue）上的利用率钳制（Utilization Clamping，UClamp）最小值和最大值；
- I/O 等待增强（I/O wait boost）；
- 实时调度类（RT）、截止时间调度类（DL）和硬件中断（IRQ）对可用 CPU 调度容量（capacity，即内核估算的相对算力）的占用；
- 温控压力（thermal pressure）等 capacity 修正；
- 可扩展调度器框架 sched_ext 启用时提供的 CPU 性能目标（performance target）。

Android 17 这一内核分支的 `sugov_get_util()` 会读取 `scx_cpuperf_target()`；没有把全部任务切换到 sched_ext 时，还会加入 `CFS boost`，即对 fair 类利用率的增强值，再经 `effective_cpu_util()` 和 DVFS 余量（headroom）处理。因此，使用“CPU 百分比 × 最高频率”描述当前实现，会漏掉多个输入。

### 从利用率映射到支持的频率

省略锁、缓存与边界处理后，主要计算关系可写为以下伪代码：

```text
util, uclamp_min, uclamp_max = collect_effective_cpu_util()
util = apply_iowait_or_other_boost(util)
perf = clamp(add_dvfs_headroom(util), uclamp_min, uclamp_max)

raw_frequency = reference_frequency * perf / capacity
next_frequency = resolve_to_driver_supported_frequency(raw_frequency)
```

伪代码中的 `perf` 是经过 UClamp 约束后的性能需求，`capacity` 是当前 CPU 的相对算力尺度。源码会根据频率不变性能力和架构反馈选择参考频率；常规频率映射还带有约 1.25 倍的余量。最终频点由 CPUFreq 驱动在 policy 限制内解析，通常选择不低于目标的受支持频点。这里的 headroom 是调频算法的一部分，不代表应用会获得固定比例的性能提升。

若一个 policy 覆盖多个 CPU，共享策略路径会遍历 `policy->cpus`，使用能够代表最高性能需求的利用率与 capacity 组合。看到某个 CPU 负载不高时，也要检查同一 policy 中的其他 CPU。

### 提交目标有三条主要路径

Android 17 的 schedutil 不能概括成“每次都排队给内核线程（kthread）”：

1. policy 开启快速切换（fast switch）时，频率路径可调用 `cpufreq_driver_fast_switch()`；
2. 驱动支持性能参数调整（adjust-perf）且满足频率不变性条件时，可调用 `cpufreq_driver_adjust_perf()` 传递性能参数；
3. 不能快速切换时，schedutil 通过中断工作机制 `irq_work` 和内核线程工作（kthread work）延后执行，最终进入 `__cpufreq_driver_target()`。

具体设备采用哪条路径，由 CPUFreq 驱动能力与 policy 配置决定。Perfetto 的频率事件本身不能证明调用经过了 fast switch、固件消息通道（mailbox），还是延后执行的内核线程。

### 更新速率限制与 I/O wait boost

schedutil 的更新速率限制 `rate_limit_us` 初值来自 `cpufreq_policy_transition_delay_us(policy)`，不是 Android 统一规定的固定毫秒值。它限制连续调频更新的节奏，设备和驱动可能提供不同的转换延迟。

I/O wait boost 用来响应刚从 I/O 等待中唤醒的任务。在这一内核版本中，增强值从 capacity 的八分之一开始，连续的 I/O 唤醒可以使其逐步增大；超过一个调度时钟周期（tick）没有更新时会重置，没有新的增强请求时还会衰减。它改善突发响应的同时也可能增加能量消耗，分析时应结合唤醒来源与持续时间。

## 为什么“升频晚了”会影响一帧

一帧的关键 CPU 工作可能经历以下路径：

1. 线程被唤醒并进入可运行等待态（runnable）；
2. 调度器选择 CPU，任务开始消耗执行时间；
3. PELT、`util_est`、UClamp 或提示会形成新的性能需求；
4. schedutil 通过更新速率限制和 policy 共享逻辑计算目标；
5. 驱动或固件接受请求，时钟和电源域完成转换；
6. 温控与电源预算决定该档位是否可用、能维持多久。

其中任何一步都可能受设备实现影响，无法给出适用于所有手机的固定“升频耗时”。PELT 的 32 毫秒半衰期也不能直接当作升频延迟：`util_est`、UClamp、I/O wait boost 和平台提示都可能让需求更早抬升。

### 判断低频是否导致掉帧

建议把下列证据放在同一时间窗口：

- 应用主线程、Android 渲染线程（RenderThread）或工作线程何时进入 runnable、何时真正运行（running）；
- 运行 CPU 与该 CPU 所属 policy；
- CPU 频率事件、CPU 空闲（idle）状态和调度切片；
- 帧截止时间（deadline）、关键切片（slice）和锁或 I/O 等待；
- UClamp、温控降频（thermal throttling）、CPU capacity 或厂商电源轨迹（若设备提供）；
- 同一场景多次复现时，低频与超时是否稳定共现。

如果关键线程大部分时间在睡眠或等待锁，升频通常不能消除瓶颈。如果线程持续运行、指令工作量相近，低频区间与错过截止时间（deadline miss）的现象反复对齐，才有较强理由继续调查 governor、UClamp、驱动响应或温控限制。

## Android 怎样向性能策略表达需求

应用和 Android Framework 通常只表达工作特征或时限，由系统及厂商策略决定怎样分配 CPU、GPU 和内存资源。这些接口不会向应用承诺某个具体频率。

### 任务配置（Task Profiles）与 UClamp

Android 可以借助任务配置（task profile）、限制线程可运行 CPU 集合的 cpuset，以及 UClamp 调整线程的放置范围与性能提示。UClamp min 给 schedutil 一个利用率下界，适合短时提高响应能力；UClamp max 可限制性能需求。它们仍受 policy 上限、CPU capacity、thermal pressure 和厂商实现约束。

长时间把 UClamp min 设得很高会增加功耗和温度，也可能减少其他任务可获得的性能资源。应围绕关键线程和关键阶段使用，并通过帧时间与能量数据验证。

### ADPF 性能提示会话（Performance Hint Session）

Android 动态性能框架（Android Dynamic Performance Framework，ADPF）的 `PerformanceHintManager` 允许应用创建性能提示会话（hint session）：

- 设置目标工作时长；
- 报告每轮工作的实际时长；
- 更新参与该会话的线程；
- 在受支持的 Android 17 API 中报告 `WorkDuration`，其中可以包含工作周期起点、总时长、CPU 时长和 GPU 时长。

这些反馈让平台知道“工作是否赶上目标”，厂商的电源硬件抽象层（Power HAL）再据此调整资源。会话受到前台状态、线程所有权和 HAL 支持等条件约束。它不会保证 CPU 进入某个 OPP，也不能代替对锁等待、算法复杂度和 GPU 瓶颈的分析。

### Power HAL 的 Mode、Boost 与提示会话

Android 17 的 AIDL（Android Interface Definition Language，Android 接口定义语言）接口 `android.hardware.power.IPower` 提供三类相关能力：

- `setMode()`：表达持续或阶段性模式，例如 `INTERACTIVE`、`GAME`、`GAME_LOADING`；
- `setBoost()`：表达短时 boost，例如 `INTERACTION`、`DISPLAY_UPDATE_IMMINENT`；
- 性能提示会话（performance hint session）：根据目标与实际工作时长持续反馈。

`isModeSupported()` 和 `isBoostSupported()` 用于查询支持情况；即使接口存在，厂商也可以不支持或忽略某个提示。HAL 内部怎样映射到 UClamp、CPUFreq、设备调频框架 devfreq、内存带宽或固件参数，不属于 AOSP 的统一保证。

Android 17 的游戏管理服务 `GameManagerService` 在游戏前台状态变化时控制 `Mode.GAME`；`setGameState()` 和 `notifyGraphicsEnvironmentSetup()` 可触发 `Mode.GAME_LOADING`，源码还为加载模式设置了最长 5 秒的限制。`setGameMode()` 主要改变用户选择与配置，不能简单等同于一次固定时长的升频。

唤醒锁（WakeLock）的职责是约束系统挂起或相关电源状态。AOSP 没有“每次获取（acquire）WakeLock 都调用 `Boost.INTERACTION` 200 毫秒”的通用链路，排障时不要把两者混为一谈。

### 从 Framework 提示到频率请求没有固定直连

Power HAL 是场景提示与厂商策略的接口边界，schedutil 是 Linux 内核的 CPUFreq governor。`setMode()`、`setBoost()` 与提示会话进入厂商 HAL 后，可以被实现为 UClamp、cpuset、devfreq、固件投票（向固件提交性能需求）或其他私有策略；AOSP 不规定它们必须写入某个 schedutil 参数。`IPowerStats` 负责观测能量消费者、计量值（meter）和状态驻留时间（residency）等数据，不会反向决定 governor 行为。

Android 公共内核 6.18 还允许 `sched_ext` 用 `scx_bpf_cpuperf_set()` 提交 CPU 性能目标。该入口与 CFS/PELT 路径会在 schedutil 中汇合，随后仍受 policy 上下限、驱动、固件与 thermal pressure 约束。BPF 是 Linux 内核中可验证、可加载的程序机制，BPF kfunc 则是内核向这类程序开放的函数接口；不能因为内核已有这一接口，就写成“Android 17 使用 BPF 直接控频”。需要在目标设备上确认 `sched_ext` 状态、已加载的 BPF 程序与 CPUFreq 路径。

架构活动监控单元（Activity Monitors Unit，AMU）、性能监控单元（Performance Monitoring Unit，PMU）和厂商计数器（counter）可以帮助解释同频不同效：AMU 反映架构活动周期与参考周期，PMU 可以提供指令数、周期数、缓存未命中（cache miss）和停顿（stall）等事件。它们是反馈或诊断来源，不是 AOSP 统一的升频仲裁器。比较“提频是否有收益”时，应在相同工作负载（workload）下同时报告完成时间、指令数与周期数、内存停顿、温度和能量，避免仅凭利用率或频率轨迹下结论。

## 用 Perfetto 观察 CPU DVFS

### 频率轨迹表示什么

Perfetto 标准库（stdlib）模块 `linux.cpu.frequency` 提供 `cpu_frequency_counters`，包含：

- `ts`：频率状态开始时间；
- `dur`：持续时长；
- `cpu`：逻辑 CPU 编号；
- `freq`：kHz。

这类轨迹来自 Linux 内核的 cpufreq 事件，适合观察内核报告的频率状态与驻留时间。它通常接近 CPUFreq 的请求或状态通知，并不自动等同于片上计数器测得的瞬时物理时钟。若需要硬件反馈，应寻找设备支持的 `cpuinfo_cur_freq`、`cpuinfo_avg_freq`、固件计数器或厂商遥测，并说明数据语义与采样周期。

### 先算频率驻留，再与调度切片关联

下面的 SQL 用于汇总每个 CPU 在各频点的驻留时长：

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

SELECT
  cpu,
  freq,
  ROUND(SUM(dur) / 1e6, 3) AS residency_ms
FROM cpu_frequency_counters
WHERE dur > 0
GROUP BY cpu, freq
ORDER BY cpu, freq;
```

查询结果回答“内核报告在某频点停留多久”。下一步应把目标时间窗与 `sched_slice`、应用切片和帧时间相交，确认关键线程在低频区间内确实处于 running 状态。只统计整段 Trace 的平均频率，结果容易被空闲时间稀释。

### CPU idle 的值要按设备解释

Perfetto 标准库 `linux.cpu.idle` 中的 `cpu_idle_counters` 使用 `idle = -1` 表示 CPU 处于活跃状态（active）；非负值是平台报告的空闲状态 ID。较大的编号通常对应更深的状态，但状态名称、退出延迟和编号映射由设备决定，应结合 `/sys/devices/system/cpu/cpuN/cpuidle/state*/` 或平台文档核对。

“低频”与“深 idle”也要分开：

- 低频表示 CPU 在活跃执行时采用较低性能状态；
- idle 表示 CPU 当时没有执行普通任务，并进入空闲状态；
- 从深度空闲状态唤醒与随后升频可能同时出现在启动阶段，但二者有不同的控制路径和延迟来源。

## GPU DVFS 与内存调频

### GPU 是独立的性能域

图形处理器（GPU）通常有自己的时钟、电压域、利用率统计和 governor 或固件策略。Linux 平台可能通过 devfreq，也可能通过厂商驱动管理 GPU。CPU 的 schedutil 不直接决定 GPU 频率。

分析 GPU 卡顿时应同时看：

- GPU 队列（queue）、同步栅栏（fence）和完成时间；
- GPU 频率或性能等级轨迹（设备提供时）；
- 温控与功率限制；
- CPU 是否及时提交了 GPU 工作。

Android 17 的 ADPF `WorkDuration` 可以携带 CPU 和 GPU 的实际工作时长，用于给平台提供更完整的反馈；它不会把 CPUFreq governor 变成 GPU governor。Perfetto 是否显示 GPU 频率、轨迹叫什么，以及数值表示请求等级还是硬件反馈，都取决于 GPU 驱动和数据源。

Android 17 的 CPU/GPU headroom API 提供未来时间窗口内的性能余量估计，应用可以据此降低画质或并发量；它不是 GPU 利用率、频率或硬件忙碌时间。系统合成服务 SurfaceFlinger 的 `PowerAdvisor` 也会围绕显示合成工作向 Power HAL 建立提示会话，但这条系统侧反馈链与应用读取 GPU headroom 没有固定的直接调用关系。设备是否把两者映射到同一套 GPU/devfreq 策略，需要厂商 Trace、HAL 实现和 GPU 计数器共同证明。

### DDR/LPDDR 调频要关注带宽、延迟与竞争

双倍数据速率内存（Double Data Rate，DDR）及其低功耗版本（Low-Power Double Data Rate，LPDDR）的控制器与互连，也可能采用动态频率或带宽投票，也就是由各组件向平台申报带宽需求。CPU 和 GPU 同时访问内存时，瓶颈可能出现在：

- 可用带宽不足；
- 内存访问延迟上升；
- 多个发起内存访问的主设备（master）相互争用；
- 热或功率预算限制内存域；
- CPU 缓存未命中增多，使核心频率上升但吞吐没有同比增加。

DDR 频率高低不能单独证明内存存在瓶颈。应优先使用设备提供的内存带宽计数器、末级缓存（LLC）相关计数器、缓存未命中与停顿事件、GPU 计数器和互连轨迹，并核对采样单位。AOSP 不统一规定厂商的 DDR governor、节点名称或 Perfetto 轨道（track）。

## 一套可复现的 DVFS 排障顺序

### 第一步：界定超时工作

标出掉帧、启动或交互的截止时间，找到关键线程和耗时最长的切片。先区分运行态（running）、可运行等待态（runnable）、睡眠态（sleeping）与阻塞态（blocked）。

### 第二步：确定 CPU 与 policy

记录线程运行过的 CPU，再读取 policy 的 `related_cpus`、驱动、governor 和频率上下限。不要用“CPU 0～3 一定是小核”之类的固定编号推断拓扑。

### 第三步：对齐请求、执行和限制

把 schedutil 输入线索、频率事件、idle 状态、温控压力、capacity 与关键切片对齐。设备若提供硬件频率反馈，再把“内核请求”和“硬件反馈”分开比较。

### 第四步：建立对照

保持工作负载、温度、电量、屏幕刷新率和网络条件尽量一致，重复采集。工程设备上的 UClamp、提示会话或受控频率上限实验可以帮助验证因果，但每次只改变一个变量，并在实验后恢复策略。

### 第五步：选择对应修复

- 线程长期处于 running 状态且算力不足：先优化工作量，再评估性能提示、UClamp 和调频响应；
- 线程处于 runnable 状态却没有获得 CPU：处理调度竞争、优先级或 CPU 放置；
- 线程处于 sleeping 或 blocked 状态：处理锁、Android 跨进程调用机制 Binder、I/O 或生产者依赖；
- 频率请求很高但硬件反馈偏低：调查温控、电源预算、固件或驱动；
- GPU/内存受限：转到对应性能域，避免只调 CPU。

## 常见误区

### “CPU 利用率不高，就没有升频需求”

平均利用率会掩盖短时突发负载（burst），也会混合不同 CPU 和时间段的数据。schedutil 还会考虑 `util_est`、UClamp、I/O 等待、RT/DL/IRQ 和 capacity 约束。应观察关键 policy 在目标时间窗口内的需求。

### “固定最高频率可以解决卡顿”

锁等待、I/O、GPU fence 和调度竞争不会因为 CPU 固定在最高频率而消失。持续最高频还会提高温度，随后可能触发更强的温控降频。限频或定频适合作为受控实验，不是通用产品方案。

### “scaling_cur_freq 就是硬件实频”

Linux CPUFreq 文档明确区分了请求状态和硬件反馈。`scaling_cur_freq` 在多数驱动上代表最近请求的 P-state；`cpuinfo_cur_freq`、`cpuinfo_avg_freq` 也只有在驱动与硬件支持时才存在。报告数据时，要写清 sysfs 节点或内核跟踪点（tracepoint）的语义。

### “看到频率晚升，就能判定 governor 有问题”

任务可能刚从深度空闲状态唤醒，也可能正在等待依赖；温控或 policy 上限还会限制目标。只有当关键任务正在运行、性能需求已经提高，而目标仍长时间没有提交或兑现时，才应把排查重点移到 governor、驱动或固件。

## 版本边界与源码索引

| 主题 | Android 17 / 6.18 锚点 | 边界 |
| --- | --- | --- |
| schedutil | `kernel/sched/cpufreq_schedutil.c` | 精确到 `android17-6.18-2026-06_r6`；其他内核分支可能不同 |
| OPP | `drivers/opp/`、`Documentation/power/opp.rst` | OPP 来源和可见性由平台决定 |
| CPUFreq | `Documentation/admin-guide/pm/cpufreq.rst` | 驱动决定 fast switch、反馈节点和固件接口 |
| ADPF | `android.os.PerformanceHintManager` | API 可用性、会话权限和 HAL 支持需在运行时确认 |
| Power HAL | `hardware/interfaces/power/aidl/android/hardware/power/` | Mode/Boost 到资源策略的映射由厂商实现 |
| 游戏模式 | `GameManagerService` | `GAME`/`GAME_LOADING` 调用点应以当前版本标签（tag）的源码为准 |
| Perfetto | `linux.cpu.frequency`、`linux.cpu.idle` | GPU、DDR 和硬件实频轨迹不具备跨设备统一性 |

## 参考资料

- Linux 内核 `android17-6.18-2026-06_r6`：`kernel/sched/cpufreq_schedutil.c`
- Linux 内核：`Documentation/admin-guide/pm/cpufreq.rst`
- Linux 内核：`Documentation/scheduler/schedutil.rst`
- Linux 内核：`Documentation/power/opp.rst` 与 `drivers/opp/`
- AOSP `android-17.0.0_r1`：`frameworks/base/core/java/android/os/PerformanceHintManager.java`
- AOSP `android-17.0.0_r1`：`frameworks/base/services/core/java/com/android/server/app/GameManagerService.java`
- AOSP `android-17.0.0_r1`：`hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl`、`Mode.aidl`、`Boost.aidl`
- Perfetto SQL 标准库：`linux.cpu.frequency`、`linux.cpu.idle`
