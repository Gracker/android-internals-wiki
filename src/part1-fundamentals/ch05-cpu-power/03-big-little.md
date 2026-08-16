---
title: "大小核架构"
chapter: "5.3"
section: "5.3"
status: ready-for-review
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-08-12"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1; Android common kernel android17-6.18-2026-06_r6 scheduler docs and source (sched-capacity, sched-energy, fair.c, cpufreq_schedutil.c); AOSP task_profiles UClamp/cpuset controls; Perfetto CPU scheduling and linux.cpu.frequency docs/source; Arm public docs retained as background source, not as device-specific Android 17 guarantee"
last_rework_at: "2026-08-12T17:35:54+08:00"
last_rework_run_id: "20260812-173533-rework-5b334e2d"
confidence: high
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-09-CPU.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md"
  - type: official
    path: "https://developer.arm.com/documentation"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-scheduling"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#linux-cpu-frequency"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/frequency.sql"
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-capacity.html"
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-energy.html"
  - type: official
    path: "https://docs.kernel.org/scheduler/schedutil.html"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-capacity.rst"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-energy.rst"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json"
tags: ['big.LITTLE', 'DynamIQ', 'schedutil', 'cpufreq', 'capacity', 'cluster', 'DVFS', 'PELT', 'RTG', 'core-migration', 'EAS', 'HMP']
related_chapters: ["5.1", "5.2", "5.4", "5.5", "5.6", "2.5"]
task2b_state: fixed
task6_state: pending-review
task9_state: pending-review
pipeline_stage: ready-for-review
---

# 5.3 大小核架构

> [!info] 源码锚点
> 正文按 Android 17 / API 37 / `android-17.0.0_r1` 与 Linux 内核分支 `android17-6.18-2026-06_r6` 复核。具体 SoC 的核心名称、编号、调度容量（capacity）与 cpufreq 策略域（policy）属于设备实现；未从目标设备内核或 sysfs 读取的数据不作为平台保证。

## 先区分四个容易混用的概念

Perfetto 会显示 CPU 编号、线程运行切片和频率计数器。要解释这些数据，先把四个概念分开：

| 概念 | 回答的问题 | 可靠来源 |
| --- | --- | --- |
| CPU 微架构（microarchitecture） | 同频下每周期大约能完成多少工作 | SoC/Arm 技术资料、目标设备测试 |
| 调度器 capacity | 内核认为 CPU 的最大相对算力与当前可用能力是多少 | `arch_scale_cpu_capacity()`、调度拓扑、温控或中断压力 |
| cpufreq policy | 哪些 CPU 共享一套频率控制，以及可选频点是什么 | `/sys/devices/system/cpu/cpufreq/policy*` |
| 能量模型性能域（Energy Model performance domain） | 哪组 CPU 共享活跃态功耗成本表 | 目标内核注册的 EM、调度器调试信息 |

这四者经常重合，却不保证一一对应。两个 CPU 可以共享 cpufreq policy，但 capacity 不同；宣传材料中的“中核”也不一定对应独立性能域。

CPU 编号更没有跨设备语义。CPU 7 可能是最高 capacity CPU，也可能只是某个同构簇成员。分析前先识别拓扑，再谈“大核”“小核”。

## 从 big.LITTLE 到多档异构 CPU

### 早期 big.LITTLE 的软件模型

Arm big.LITTLE 把侧重单线程性能的 CPU 与侧重能效的 CPU 放进同一 SoC。早期实现经历过几种软件模型：

1. **簇级迁移（Cluster migration）**：一个 CPU 簇（cluster）工作时，另一个对应簇关闭；切换粒度较粗。
2. **内核切换器（In-kernel switcher）**：把一颗高性能 CPU 与一颗高能效 CPU 配成逻辑对，任一时刻只启用其中一颗。
3. **全局任务调度（Global Task Scheduling）与 HMP**：所有 CPU 对内核可见，调度器按任务需求选择 CPU，并允许不同类型 CPU 采用不对称数量。HMP 是 Heterogeneous Multi-Processing，即异构多处理。

这些模型用于理解历史演进。Android 17 / Linux 6.18 的公共调度路径以 capacity 感知调度（按 CPU 相对算力选择和均衡任务）、能量感知调度（Energy Aware Scheduling，EAS）、cpuset（限制任务可用 CPU 集合）和利用率钳制（Utilization Clamping，UClamp）为主，不应继续套用早期“一次切换整个簇”的运行图。

历史资料常给迁移标注固定的微秒数。迁移成本会随互连、缓存层级（cache hierarchy）、工作集、源 CPU 与目标 CPU 是否共享末级缓存（Last-Level Cache，LLC）、频率状态和内核路径变化，不能把某个平台测得的数值写成架构常量。

### DynamIQ 改变了 cluster 内组织方式

DynamIQ 允许不同 CPU 微架构在同一个 DynamIQ 簇中协作，并通过 DSU（DynamIQ Shared Unit）提供共享的系统级缓存与一致性支持。它降低了部分跨类型 CPU 共享数据的成本，也允许更灵活的核心组合。

分析时还要注意三点：

- 共享 LLC 不会复制源 CPU 私有的 L1/L2 内容，迁移后仍可能出现冷缓存未命中（cold miss）；
- DynamIQ 具备相关硬件能力，不代表每款 SoC 都实现每 CPU 动态电压与频率调节（Dynamic Voltage and Frequency Scaling，DVFS），实际频率控制范围要看 cpufreq policy；
- DSU 型号、缓存容量和互连拓扑由 SoC 决定，不能用某个 Arm IP 的能力上限描述所有 Android 设备。

16 KB 页大小主要改变地址转换缓存（Translation Lookaside Buffer，TLB）的覆盖范围（TLB reach）、页表层级行为和内存管理成本。公开的通用 DSU 接口没有把“16 KB 页会降低监听过滤器（snoop filter）探测频率”定义为平台保证，因此不能据此推导互连收益。

### 当代 SoC 不止“大”和“小”

常见布局可以抽象为：

- 两档：高能效 CPU + 高性能 CPU；
- 三档：高能效 CPU + 高性能 CPU（performance CPU）+ 最高性能 CPU（prime CPU）；
- 多颗 performance CPU + 少量 prime CPU；
- 市场上称为“全大核”的组合。

这些名称适合描述产品，不适合作为调度器输入。Linux 关心的是每颗 CPU 的 capacity、允许范围、当前压力、性能域和能量模型（Energy Model，EM）。即使两类 CPU 的 capacity 很接近，功耗成本仍可能不同；反过来也一样。

因此，不应从公开规格外推“某 CPU 的 `capacity=837`”这类数字。精确分析应读取目标设备的 capacity 数据或对应内核代码树。

## Linux 怎样表达 CPU capacity

### 原始 capacity 与当前可用 capacity

Linux 6.18 的 Capacity Aware Scheduling 文档把 CPU 的最大能力近似写成：

```text
capacity(cpu) = work_per_hz(cpu) × max_freq(cpu)
```

其中，`work_per_hz` 表示 CPU 每赫兹大约能完成的工作量，`max_freq` 表示最高频率。系统中最强 CPU 的原始 capacity（original capacity）被归一化为 `SCHED_CAPACITY_SCALE=1024`，其他 CPU 按相对能力缩放。`arch_scale_cpu_capacity(cpu)` 返回原始 capacity。

运行时可用 capacity 还会扣除部分压力，例如硬件中断（IRQ）、温控压力（thermal pressure）与调频压力（cpufreq pressure）。对 EAS、不匹配任务迁移（misfit migration）或 `util_fits_cpu()` 来说，静态的 1024 或某个较小值只是计算起点。

单个 capacity 标量也有局限。两种微架构在整数、浮点、向量、分支和内存访问上的相对性能不同，无法由一个数字完整表达。capacity 适合调度器快速估算，性能结论仍要以微基准与业务测试为依据。

### 利用率与 capacity 的比较带有余量

任务的 PELT（Per-Entity Load Tracking，每个调度实体的负载跟踪）利用率和短期利用率估计 `util_est` 经过频率不变性与 CPU 不变性处理后，可以与 capacity 比较。Linux 6.18 的 `fits_capacity(util, capacity)` 会预留约 20% 余量（margin）：

```text
util × 1280 < capacity × 1024
```

因此，`util=800` 不能算作“刚好装进 `capacity=800` 的 CPU”。这段余量用于避免任务在临界位置反复迁移，也给突发负载留出空间。

UClamp 会进一步影响 `util_fits_cpu()`。`uclamp.min` 可以表达较高的最低性能点，`uclamp.max` 可能让限制了性能上限的任务在较低 capacity CPU 上仍被视为适配（fit）。UClamp 不提供 CPU 时间配额，也不会单独决定目标 CPU。

### 温控压力会改变任务是否“装得下”

当温控或 cpufreq 限制使 CPU 无法达到原有最高性能时，内核会降低相应的可用 capacity。于是，同一个任务在冷机时可能适合当前 CPU，进入热稳态后却可能变成不匹配任务（misfit），并被负载均衡迁往其他可用 CPU。

这也是持续性能分析必须进入热稳态的原因。只比较冷机前几秒的核心分布，无法说明设备在长期功耗预算下的行为。

## 在设备和 Perfetto 中识别拓扑

### 先读 sysfs，再看 Trace

sysfs 是 Linux 向用户空间暴露设备和内核对象状态的虚拟文件系统。下面的命令只读取目标设备状态，用于建立 CPU、capacity 与 cpufreq policy 的对应关系，随后再与 Perfetto Trace（性能轨迹）对照：

```shell
adb shell 'for c in /sys/devices/system/cpu/cpu[0-9]*; do
  echo "$c"
  cat "$c/cpu_capacity" 2>/dev/null
  cat "$c/cpufreq/cpuinfo_max_freq" 2>/dev/null
  cat "$c/cpufreq/related_cpus" 2>/dev/null
done'

adb shell 'for p in /sys/devices/system/cpu/cpufreq/policy*; do
  echo "$p"
  cat "$p/related_cpus" 2>/dev/null
  cat "$p/scaling_available_frequencies" 2>/dev/null
  cat "$p/scaling_driver" 2>/dev/null
  cat "$p/scaling_governor" 2>/dev/null
done'
```

命令会逐个读取 CPU 的 capacity、最高频率与共享 policy，并列出各 policy 的可选频率、驱动和调频策略（governor）。有些量产设备会隐藏 `cpu_capacity`、可用频点或 governor 节点；读不到时，应转向设备内核配置、厂商源码或具备权限的调试接口，不能只用最高频率替代 capacity。

Perfetto 标准库（stdlib）可以汇总 Trace 期间观测到的频率。下面的查询用于查看各 CPU 的频率变化范围和采集覆盖时长：

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

SELECT
  cpu,
  MIN(freq) / 1000.0 AS observed_min_mhz,
  MAX(freq) / 1000.0 AS observed_max_mhz,
  ROUND(SUM(dur) / 1e9, 3) AS covered_s
FROM cpu_frequency_counters
WHERE dur > 0
GROUP BY cpu
ORDER BY cpu;
```

查询结果中，`freq` 的单位是 kHz。`observed_max_mhz` 只是采集窗口内出现过的最高频率；设备若没有运行到最高工作性能点（Operating Performance Point，OPP），该值会低于 `cpuinfo_max_freq`。两个 CPU 的频率同时变化只能提示它们可能共享 policy，还应通过 `related_cpus` 确认。

### 不要用 CPU 编号或最高频率单独分类

最高频率较高的 CPU 往往 capacity 也较高，但每赫兹工作量（work-per-Hz）可能不同。仅看频率无法区分：

- 同频但微架构不同；
- 不同频但最大 capacity 相近；
- policy 被温控或省电模式临时限制；
- 硬件自治 DVFS 使软件频率计数器（counter）与瞬时执行频率存在差异。

可靠的判断需要结合 capacity、cpufreq policy、频率、线程运行时间（runtime）与业务截止时间（deadline）。

## 任务为什么会换 CPU

### 唤醒时放置

对于 fair 调度类任务，`select_task_rq_fair()` 处理唤醒，以及创建新进程的 fork、装载新程序的 exec 等场景下的任务放置（placement）。Android 17 内核 r6 在普通唤醒标志 `WF_TTWU` 路径中，如果根调度域（root domain）没有进入过载状态（overutilized），就会尝试调用 `find_energy_efficient_cpu()`。

EAS 不会遍历所有 CPU 后简单选择“最省电的一颗”。它从每个 EM 性能域选出有代表性的、仍有剩余 capacity（spare capacity）的候选，再与任务上次运行的 CPU（`prev_cpu`）比较适配程度和能量增量（energy delta）。同步唤醒满足条件时，还可能直接进入复用当前 CPU 的快速路径（fast path）。

root domain 进入 overutilized 状态后，这次唤醒会跳过 EAS 能量估算，转到基于负载和空闲同级 CPU（idle sibling）的选择路径。看到线程在某颗 CPU 上运行，不能默认归因于 EAS。

### 运行时负载均衡与不匹配任务迁移

任务开始运行后，周期负载均衡（load balance）、CPU 即将空闲时的 `newidle balance`、主动均衡（active balance）和 misfit migration 仍可继续迁移它。常见原因包括：

- 原 CPU 的运行队列（runqueue）过载；
- 低 capacity CPU 无法满足任务需求；
- 其他 CPU 进入空闲状态，可以拉取任务；
- 调度域（sched domain）的不均衡超过阈值；
- thermal pressure 改变了 CPU 的可用 capacity。

这些路径不会为每次迁移调用 EM。唤醒选核与运行时迁移属于不同问题，在 Perfetto 中要结合迁移前的线程状态判断。

### CPU 亲和性、cpuset、热插拔与隔离

线程最终可用的 CPU，是在线 CPU、CPU 亲和性掩码（affinity mask）与 cpuset 允许范围的交集。系统改变前后台任务配置（task profile）、将 CPU 下线、设置隔离 CPU 或应用厂商策略时，即使线程负载不变，也可能迫使线程迁移。

下面的命令用于确认某个线程 ID（tid）当时可以在哪些 CPU 上运行：

```shell
adb shell 'cat /proc/<pid>/task/<tid>/status | grep Cpus_allowed_list'
adb shell 'cat /proc/<pid>/task/<tid>/cgroup'
```

第一条命令显示 CPU 亲和性允许列表，第二条显示线程所属的控制组（cgroup）。CPU 亲和性只能缩小候选范围。把 Android 渲染线程（RenderThread）固定到某一颗高 capacity CPU，会让它无法避开该 CPU 的竞争或温控限制，因此只适合用于有对照组的实验。

### RTG 属于厂商实现

RTG（Related Thread Group，相关线程组）、同位增强（colocation boost）和首选 CPU 簇（preferred cluster）等机制常见于部分厂商内核。它们可以按相关线程组聚合需求、偏好某个簇或影响频率提示。

这些符号不属于 Android 17 公共内核的通用接口。不同厂商、不同代际的 RTG 数据结构和策略也可能变化。若 Trace 疑似受到 RTG 影响，应在目标内核代码树、厂商钩子（vendor hook）和电源硬件抽象层（Power HAL）中寻找证据，不能根据线程名推断。

## 迁移成本怎样判断

### 缓存局部性

迁移不会复制源 CPU 私有缓存中的 L1/L2 内容。目标 CPU 需要从共享 LLC、系统缓存或内存重新取得数据。实际成本取决于工作集、缓存共享边界、写共享、非一致内存访问（Non-Uniform Memory Access，NUMA）或其他内存拓扑，以及迁移间隔。

DynamIQ 的共享缓存能降低部分数据获取成本，但无法消除私有缓存冷未命中（private-cache cold miss）。固定的“迁移需要 30 μs”或“新架构只需几微秒”都不适合作为跨设备结论。

### 频率与 cpufreq policy 状态

任务迁入新的 cpufreq policy 后，该 policy 可能还处于低频。schedutil、I/O 等待增强（I/O-wait boost）、UClamp、Power HAL 和硬件 DVFS 会共同决定频率提升速度。若多个 CPU 共享 policy，另一个 CPU 的负载也可能已经使频率升高。

因此，“迁到大核后仍慢”至少要同时检查：

- 迁移前后的运行态（Running）和可运行等待态（Runnable）时间；
- 源 CPU 与目标 CPU 的 capacity 和频率；
- 是否跨 LLC 或 cpufreq policy；
- 温控或省电模式设置的上限；
- 工作集的缓存未命中次数是否增加。

### 用 Perfetto 统计分布与迁移

第一条查询统计目标线程在各 CPU 上的运行时长与运行切片数量：

```sql
SELECT
  s.cpu,
  COUNT(*) AS slice_count,
  ROUND(SUM(s.dur) / 1e6, 3) AS running_ms
FROM sched_slice AS s
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name = 'your.package.name'
  AND t.name = 'RenderThread'
  AND s.dur > 0
GROUP BY s.cpu
ORDER BY s.cpu;
```

这张表只能说明运行分布。要统计相邻运行切片（Running slice）之间的 CPU 变化，可以使用窗口函数：

```sql
WITH target_slices AS (
  SELECT
    s.ts,
    s.cpu,
    LAG(s.cpu) OVER (ORDER BY s.ts) AS previous_cpu
  FROM sched_slice AS s
  JOIN thread AS t USING (utid)
  JOIN process AS p USING (upid)
  WHERE p.name = 'your.package.name'
    AND t.name = 'RenderThread'
    AND s.dur > 0
)
SELECT
  previous_cpu,
  cpu,
  COUNT(*) AS transitions
FROM target_slices
WHERE previous_cpu IS NOT NULL
  AND previous_cpu != cpu
GROUP BY previous_cpu, cpu
ORDER BY transitions DESC;
```

相邻切片跨 CPU 表示两次运行之间目标 CPU 发生变化，但中间可能经历睡眠、唤醒和排队。这项结果不能单独证明缓存迁移是延迟根因，还要与业务切片、频率、缓存和性能监控单元（Performance Monitoring Unit，PMU）数据对齐。

## Android 17 schedutil 怎样选频

### 当前源码路径

schedutil 使用调度器的利用率信号决定 cpufreq policy 的目标性能点。`android17-6.18-2026-06_r6` 中 `sugov_get_util()` 的处理过程可概括为：

```text
util = sched_ext CPU perf target
if CPU 没有完全交给 sched_ext:
    util += boosted CFS util

util, min, max = effective_cpu_util(CFS + RT + DL + IRQ, UClamp)
util = max(util, I/O-wait boost)
target_perf = sugov_effective_cpu_perf(util, min, max)
```

其中，`perf target` 是 sched_ext 提供的性能目标，`boosted CFS util` 是调整后的 fair 类利用率。CFS（Completely Fair Scheduler，完全公平调度器）表示 fair 调度类任务，RT 表示实时调度类，DL 表示截止时间调度类，IRQ 表示硬件中断；sched_ext 是 Linux 的可扩展调度器框架。`sugov_effective_cpu_perf()` 先用 `map_util_perf()` 增加约 25% 的 DVFS 余量（headroom），再应用最低与最高性能约束。这种线性映射只是一种估算，并不等同于硬件的实际性能曲线。

如果一个 cpufreq policy 覆盖多个 CPU，`sugov_next_freq_shared()` 会遍历该 policy 中的 CPU，并采用其中最高的目标性能需求来选频。因此，Perfetto 中同一 policy 内 CPU 的频率联动符合源码预期。

### 调频速率限制没有跨设备固定值

`rate_limit_us` 限制调频请求的更新频率。Linux 6.18 初始化时采用 `cpufreq_policy_transition_delay_us(policy)`，之后可以由 governor 的可调参数（tunable）改写。该值取决于驱动与 policy，不应写成 Android 固定采用 1 ms 或 2 ms。

### I/O-wait boost 的适用范围

Linux 6.18 针对带有 `SCHED_CPUFREQ_IOWAIT` 标志的唤醒维护 I/O-wait boost。连续、频繁的 I/O 完成唤醒（completion wakeup）会逐步提高这一增强值；超过一个调度时钟周期（tick）没有新请求时，增强值会重置或衰减。该机制用于缩短 I/O 后续处理延迟，不能据此推断所有文件读取都会直接升到最高频率。

### RT、DL、UClamp 与 sched_ext

`effective_cpu_util()` 合并 CFS、RT、DL 与 IRQ 的影响，并向 schedutil 返回性能上下界。RT 或 DL 任务并非“只要出现就永久锁定最高频率”；截止时间带宽（deadline bandwidth）、默认 RT UClamp 和设备配置都会影响结果。

Android 17 公共内核的 schedutil 还接受 `scx_cpuperf_target()`。只有 sched_ext 实际管理 CPU 或提供性能目标（perf target）时，这项输入才有意义；源码中存在该接口，不代表量产设备默认启用了 sched_ext 调度器。

### Power HAL 和省电/温控是外部约束

Power HAL 可以应用任务配置、UClamp、cpuset、设备调频框架 devfreq 或厂商节点，也可能调整 cpufreq 的最低与最高限制（floor/ceiling）。Android 平台没有保证每个 `LAUNCH` / `INTERACTION` 性能提示（hint）都通过 `scaling_min_freq` 实现。

温控和省电模式可以限制最高 OPP，硬件 DVFS 也可能在软件请求之外自行选择。Perfetto 显示的是最终可观测频率，解释时应同时检查：

- `scaling_driver` 与 `scaling_governor`；
- policy 的最低值、最高值与温控上限；
- UClamp 与任务配置；
- Power HAL 或 Android 动态性能框架会话（Android Dynamic Performance Framework session，ADPF session）；
- 硬件计数器是否提供频率不变性所需的信息。

## 如何理解不同 CPU 的性能

### 同频不等性能

capacity 文档把最大能力拆成每赫兹工作量与最高频率。高性能微架构往往有更宽的前端和后端、更大的乱序执行窗口，以及更多缓存和分支预测资源；相同频率下，它可能完成更多工作。

差距会随工作负载（workload）变化：

- 计算与分支密集代码更受执行宽度、预测和前端影响；
- 数据主要驻留在缓存中的负载（cache-resident workload）更受 L1/L2 容量与延迟影响；
- 受内存限制的负载（memory-bound workload）可能主要受 LLC、动态随机存取存储器（DRAM）和带宽争用限制；
- 向量或加密代码还取决于具体执行单元。

因此，“大核一定快 2～3 倍”或“同频大核耗能更少”都需要目标工作负载的实测支撑。

### 单线程延迟

应用启动、UI 主线程和部分脚本执行包含单线程关键路径，高 capacity CPU 可能缩短受 CPU 计算限制的阶段（CPU-bound 段）。但线程若主要等待 Android 跨进程调用机制 Binder、锁、I/O 或 GPU，迁到 prime CPU 也不会消除等待。

判断是否需要更高 capacity CPU，应先比较实际经过时间（wall time）、CPU 执行时间（CPU time）、可运行态等待时间（Runnable wait）和截止时间。主线程没有运行在编号最大的 CPU，本身不构成问题。

### 多线程吞吐与热稳态

图片处理、编译和软件编解码等吞吐任务可以利用多颗 CPU，但并行度还受任务划分、锁、内存带宽和散热预算（thermal budget）限制。短时间跑满全部 CPU，不代表能够长期维持最高频率。

进入热稳态后，系统可能降低多个 policy 的频率、调整任务放置，甚至下线部分 CPU。有效指标应覆盖每秒完成量、每项任务的能量、温度和尾延迟，不能只统计高频 CPU 的数量。

## 一套可复现的分析顺序

1. **标出业务截止时间**：定位启动、帧、音频或推理区间。
2. **确认线程状态**：区分运行态（Running）、可运行态标记 `R/R+`，以及锁、Binder、I/O 等等待。
3. **建立设备拓扑**：记录 capacity、cpufreq policy、在线 CPU、CPU 亲和性与 cpuset。
4. **对齐运行结果**：统计各 CPU 的运行时间、迁移、频率和空闲状态。
5. **检查外部约束**：温控、省电模式（battery saver）、Power HAL、UClamp、ADPF 和 vendor hook。
6. **提出单一假设**：例如“低 capacity CPU 无法在截止时间内完成 CPU-bound 段”。
7. **做 A/B 验证**：比较延迟分位数、功耗与热稳态，不只看一次 Trace。

### 正常现象

- 短任务留在低 capacity CPU 且按时完成；
- 唤醒后保留 `prev_cpu`，减少不必要迁移；
- 高利用率任务在温控允许时进入更高 capacity 性能域；
- 同一 cpufreq policy 的 CPU 共享频率变化；
- 任务发生运行时迁移，但没有对应的截止时间违约或缓存指标下降。

### 需要继续排查的现象

- CPU-bound 关键阶段持续超时，同时只能在低 capacity CPU 上运行；
- 存在空闲且允许使用的高 capacity CPU，目标线程却长时间处于 Runnable 状态；
- 迁移点与缓存未命中、wall time 尖峰稳定相关；
- policy 频率长期受限，且与温控或省电状态一致；
- 前后台状态变化后，cpuset、UClamp 或任务配置没有按预期更新。

这些现象是调查入口，不是单凭一条就能定责的规则。

## 常见误区

### “CPU 编号越大，性能越高”

编号由固件和设备拓扑决定。用 capacity、policy 与实测识别 CPU 类型。

### “降低 nice 值会让线程自动去大核”

nice 值主要改变 fair 类任务获得 CPU 时间的相对权重。选核还要看利用率、capacity、EAS、UClamp、cpuset 和当前负载；更高权重不等于强制选择高 capacity CPU。

### “最高频率越高，CPU 就越快”

最高频率没有反映每赫兹工作量、缓存、内存与温控信息，只能描述 CPU 性能的一个维度。

### “迁移次数多，调度一定有问题”

迁移是负载均衡和异构调度的正常手段。只有迁移与截止时间违约、缓存指标恶化或能耗增加稳定相关时，才有优化依据。

### “绑核可以修复所有选核问题”

CPU 亲和性会缩小调度器的选择范围，也可能把线程留在拥塞或降频的 CPU 上。应先验证根因，再用可回滚的实验评估绑核效果。

### “全大核 SoC 不需要 EAS”

产品名称无法替代内核拓扑。只要 CPU capacity 或 EM 成本存在差异，能量感知的任务放置仍有分析价值。

## GPU、NPU 与 CPU 调度的边界

EAS、最早合格虚拟截止时间优先算法（Earliest Eligible Virtual Deadline First，EEVDF）和 schedutil 分别参与 CPU 任务放置、CPU 运行队列调度与 CPU 频率选择。图形处理器（GPU）和神经网络处理器（NPU）有各自的队列、驱动、devfreq 或固件调度与功耗域，不能称为由 CPU EAS “协同调度”。

任务卸载仍会在 CPU 上产生准备、Binder 或 HAL 调用、命令提交（command submission）、同步栅栏（fence）和结果处理。分析异构计算时，可以按下面的执行依赖检查：

```text
CPU 准备与提交
    → GPU/NPU 队列等待与执行
    → fence / callback 唤醒 CPU
    → CPU 后处理
```

如果 CPU 长时间睡眠并等待 fence，调整 CPU 亲和性无法缩短加速器执行时间；如果提交线程长时间处于 Runnable 状态或受 CPU 计算限制，则需要回到 CPU 调度证据链。GPU/NPU 的频率、队列和利用率应使用各自的数据源分析。

## 版本演进与当前边界

| 时期 | 变化 | 分析用途 |
| --- | --- | --- |
| 2011 起 | Arm big.LITTLE 与早期簇级迁移或切换器模型 | 解释异构 CPU 的由来 |
| Linux 4.7 起 | schedutil 进入主线 | 解释调度器利用率驱动 DVFS |
| Linux 5.0 起 | EAS 进入主线 | 解释异构 CPU 的唤醒选核 |
| Android 9 起 | Android 设备广泛采用 EAS 和 schedutil，但厂商实现各异 | 只作历史范围，不假定所有设备一致 |
| Android 17 / API 37 | Android 开源项目（AOSP）`android-17.0.0_r1` | 任务配置、UClamp、Power HAL 和 ADPF 控制面 |
| Android 17 内核 | `android17-6.18-2026-06_r6` | capacity 感知调度、EAS、schedutil、thermal pressure 与 sched_ext 接口 |

## 源码索引与参考资料

相关公共源码结论可从以下入口复核：

- Linux 内核 `Documentation/scheduler/sched-capacity.rst`；
- Linux 内核 `Documentation/scheduler/sched-energy.rst`；
- Linux 内核 `Documentation/scheduler/schedutil.rst`；
- Linux 内核 `kernel/sched/fair.c`：`util_fits_cpu()`、`find_energy_efficient_cpu()`、misfit 与负载均衡路径；
- Linux 内核 `kernel/sched/cpufreq_schedutil.c`：`sugov_get_util()`、`sugov_effective_cpu_perf()`、I/O-wait boost；
- Android `system/core/libprocessgroup/profiles/task_profiles.json`；
- Perfetto `linux.cpu.frequency`、`sched_slice` 与 `thread_state`。

参考链接：

- [Linux Capacity Aware Scheduling](https://docs.kernel.org/scheduler/sched-capacity.html)
- [Linux Energy Aware Scheduling](https://docs.kernel.org/scheduler/sched-energy.html)
- [Linux schedutil](https://docs.kernel.org/scheduler/schedutil.html)
- [Arm big.LITTLE](https://developer.arm.com/Architectures/big.LITTLE)
- [Perfetto CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Android UClamp](https://source.android.com/docs/core/perf/uclamp)
