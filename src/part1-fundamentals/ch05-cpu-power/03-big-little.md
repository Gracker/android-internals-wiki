---
title: "大小核架构"
chapter: "5.3"
section: "5.3"
status: ready-for-review
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-29"
last_verified_against: "ARM official documentation, Linux kernel 6.12, Snapdragon 8 Elite specs"
confidence: high  # 架构原理和 schedutil 机制描述经过 AOSP 源码和 ARM 官方文档双重验证
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
    path: "https://docs.kernel.org/scheduler/sched-energy.html"
tags: ['big.LITTLE', 'DynamIQ', 'schedutil', 'cpufreq', 'capacity', 'cluster', 'DVFS', 'PELT', 'RTG', 'core-migration', 'EAS', 'HMP']
related_chapters: ["5.1", "5.2", "5.4", "5.5", "5.6", "2.5"]
drafted_date: "2026-03-31"
reviewed_date: "2026-05-05"
reviewed_by: openclaw-task6
task6_result: needs-rework
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
task2b_result: fixed
last_task2b_at: "2026-05-18T15:23:37+08:00"
task2b_state: fixed
task6_state: revisiting
task9_state: pending
pipeline_stage: task6_pending
task9_result: needs-rework
task9_reviewed_date: "2026-05-15"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-15T12:31:59+08:00"
review_notes: "2026-05-05 task6 review: L1/L2 小修完成；GPU/NPU 协同调度扩展仍为空壳，已写入 queue/suggestions 回炉。"
task6_reviewed_date: "2026-05-05"
last_task6_at: "2026-05-05T10:05:00+08:00"
last_task9_review_log: "logs/deep-review/2026-05-15-12-deep-review.md"
task9_review_notes: "2026-05-15 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 0；新增问题已写入 queue，等待 Task2B 回炉。"
---

# 大小核架构


## 为什么要了解大小核架构

打开 Perfetto 的 CPU 视图，我们会看到 8 个（或更多）CPU 核心，编号从 0 开始。点击某个线程的 Running 切片，详情面板里有一个 `cpu` 字段，告诉你这个线程此刻跑在几号核心上。仔细观察会发现，同一线程在不同时间段跑在不同的核心上——有时候在 CPU 0，有时候在 CPU 7，而且在这两个核心上的执行速度差异巨大。

现代手机 SoC 普遍采用大小核（big.LITTLE）异构多核架构，不同类型的核心在性能和功耗之间存在巨大的设计权衡。理解这种架构，是读懂 CPU Scheduling 轨道、判断调度器行为是否合理的基础。一个计算密集型任务如果长时间运行在小核上，它的耗时可能比在大核上慢 2-3 倍；反过来，一个后台同步任务如果被错误地调度到大核上，会白白浪费电量。

这一节的任务是讲清大小核架构的设计方式、核心迁移的触发机制，以及 cpufreq governor（尤其是 schedutil）如何根据负载动态调频。读懂这些，后面分析 CPU Scheduling 轨道时才知道线程为什么跑在某个核心上。

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## ARM big.LITTLE 与 DynamIQ 架构原理

### 从问题说起：性能与功耗的矛盾

移动设备的电池容量是有限的，但用户对性能的期望却不断增长。如果一个 8 核处理器所有核心都是高性能设计，那么在处理后台同步、推送消息这类轻负载任务时，大部分算力被浪费了，而功耗却居高不下。反过来，如果所有核心都是低功耗设计，用户打开应用、滑动列表时又会有明显的卡顿。

ARM 在 2011 年提出的 big.LITTLE 架构就是为了解决这个矛盾：在同一个 SoC 上集成两种（后来发展为多种）不同微架构的 CPU 核心——**大核（big cores）**追求单线程性能，**小核（LITTLE cores）**追求能效比。调度器根据任务负载的特征，把任务分配到最合适的核心上。

### 早期 big.LITTLE：集群迁移模式

最初的大核小核实现采用**独立的两个集群（cluster）**，一个集群全是小核，另一个集群全是大核。两个集群通过 Cache Coherent Interconnect（CCI）互联。

这种架构下有三种软件调度模型：

1. **集群迁移（Cluster Migration）**：同一时刻只有一个集群在线。负载低时用小核集群，负载高时整个系统切换到大核集群。切换过程需要把缓存数据从 L2 搬到另一个集群的 L2，会产生一次"不可忽略"的中断。如果系统里只有一个高负载任务，但其他核心都在空闲，也会被迫把整个集群切到大核，浪费功耗。

2. **CPU 迁移（In-Kernel Switcher, IKS）**：每个大核和一个小核组成虚拟对，调度器在配对的核心之间迁移任务。迁移延迟大约 30 微秒，比 DVFS 变频还快，用户基本感知不到。但限制是大核和小核数量必须 1:1 配对，且同一时刻只有一半核心在线。

3. **全局任务调度（Global Task Scheduling / HMP）**：调度器同时感知所有大核和小核，可以独立地把单个任务分配到任意核心上。所有核心可以同时在线，也支持不对称配置（比如 4 小核 + 2 大核）。这是 big.LITTLE 最成熟的软件模型，也是 Android 设备实际采用的方案。

[已验证: ARM 官方文档, developer.arm.com/documentation]

### DynamIQ：从双集群到统一集群

2017 年 ARM 推出了 DynamIQ 技术，这是 big.LITTLE 的重大演进。核心变化在于：**大核和小核可以放在同一个集群（cluster）里**，由一个 DynamIQ Shared Unit（DSU）统一管理。

DSU 提供了集群内的共享 L3 缓存（最高可达 32MB）和一致性的缓存管理。大核和小核之间的任务迁移不再需要跨集群搬运缓存数据——它们共享同一个 L3，迁移的开销大幅降低。

DynamIQ 带来了几个关键优势：

- **更灵活的核心配置**：不再受限于对称的集群配置，可以在一个集群内自由组合大核、中核、小核。比如 1 个超大核 + 3 个大核 + 4 个小核，这种 1+3+4 的配置在旗舰 SoC 上非常常见。
- **独立的核心控制**：DynamIQ 架构支持每个核心独立的频率和休眠控制。传统 big.LITTLE 中同一集群内的核心共享同一个电压/频率域，必须同步变频；DynamIQ 在架构层面提供了 per-core DVFS 的能力。但需要注意，**架构能力不等于设备实现**——实际 SoC 出于功耗域设计和成本考量，仍可能把同类型核心归入同一个 cpufreq policy 组，在 Perfetto 中表现为同簇核心频率联动。区分"架构能力"和"实装策略"的方式是看 `/sys/devices/system/cpu/cpu<N>/cpufreq/related_cpus`，如果多个核心出现在同一列表中，说明它们共享一个 DVFS 域。
- **更低迁移延迟**：由于大核和小核共享 L3 缓存，任务在核心间迁移时不再需要通过 CCI 互联搬运缓存行，迁移延迟从"跨集群级别"降低到"集群内级别"。
- **更大的 L3 缓存**：DSU-120（配合 Armv9 世代的核心）支持最高 32MB L3 缓存，显著减少了核心访问主存的次数，对内存密集型任务的性能提升尤为明显。
- **16KB 页与互联层的潜在收益**：理论上，更大的页粒度可能降低 DSU 内部 snoop filter 的探测频率——每个页表条目覆盖更大的物理地址范围，跨核缓存一致性事务的粒度也随之放大。但这一机制取决于 SoC 厂商对 DSU-120 的具体实装方式，公开 ARM TRM 目前未明确记载"16KB 页模式"作为 DSU 的可配置选项。16KB 页在 CPU 侧的确定性收益主要来自 TLB Reach 提升（§4.7 有展开），互联层的收益可作为性能分析的观察方向，但不应作为已验证事实引用。

[待验证: ARM DSU-120 TRM 中与页粒度相关的寄存器配置；如有确切证据再补实]

### 在 Perfetto 中识别核心类型

在 Perfetto 的 CPU 视图中，核心从 0 开始编号。不同设备的编号规则不同，但通常有一个规律：**小核编号靠前，大核编号靠后**。

不过不能完全依赖编号来判断核心类型——最可靠的方式是查看每个核心的 `cpuinfo_max_freq`。在 Perfetto 中，我们可以通过 SQL 查询获取：

```sql
-- 查看每个 CPU 在 trace 期间观测到的最高运行频率
INCLUDE PERFETTO MODULE linux.cpu.frequency;

SELECT cpu, max(freq) / 1000.0 AS observed_max_freq_mhz
FROM cpu_frequency_counters
GROUP BY cpu
ORDER BY cpu;
```

> 注意：`cpu_frequency_counters` 返回的是 trace 期间实际观测到的频率，不等同于 sysfs 的 `cpuinfo_max_freq`。如果某个核心在 trace 期间没有跑到最高频，查询结果会偏低。需要完整频率上限时，仍应读取 `/sys/devices/system/cpu/cpu<N>/cpufreq/cpuinfo_max_freq`。

或者在设备上直接读取 sysfs 节点：

```bash
$ cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq
1804800
$ cat /sys/devices/system/cpu/cpu7/cpufreq/cpuinfo_max_freq
2841600
```

通过最大频率，可以把核心分组。比如一个 8 核处理器中，`cpuinfo_max_freq` 为 1804800 的 4 个核心是小核，2419200 的 3 个核心是大核，2841600 的 1 个核心是超大核。

[来源: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]
[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## 典型 SoC 核心配置

不同 SoC 厂商和型号的核心配置差异很大，但近几年的旗舰芯片呈现出一个明显的趋势：**核心类型越来越多样化，配置从简单的 4+4 演变为三档甚至全大核设计**。

### 经典配置类型

**4+4（四小核 + 四大核）**

这是最早期的 big.LITTLE 配置，现在主要出现在中低端芯片上。比如早期的 Exynos 5 Octa 就是 4 个 Cortex-A7 小核 + 4 个 Cortex-A15 大核。这种配置在今天看来比较粗糙——大核和小核的性能差距大，中间没有过渡。

**1+3+4（一个超大核 + 三个大核 + 四个小核）**

这是 2023-2025 年旗舰 SoC 的主流配置。一个典型的例子是联发科天玑 9400：

- 1 个 Cortex-X925 超大核（3.62GHz+）——负责最苛刻的单线程场景（应用启动、JS 执行）
- 3 个 Cortex-X4 大核（约 3.0GHz）——负责多线程重负载（游戏渲染、后台编译）
- 4 个 Cortex-A720 中/小核（约 2.3GHz）——负责日常轻负载（后台同步、消息推送）

高通骁龙 8 Gen 3 也采用类似的 1+5+2 配置（1 个 Cortex-X4 + 5 个 Cortex-A720 + 2 个 Cortex-A520），思路相同：三层核心各自对应不同的性能区间。

**2+6（两个大核 + 六个性能核）**

高通骁龙 8 Elite（2024 年底发布）采用了一种更激进的配置：2 个 Oryon Prime 核心（4.32GHz）+ 6 个 Oryon Performance 核心（3.53GHz）。它完全去掉了传统意义上的"小核"，所有核心都有较强的性能输出，但 Prime 核心在频率和微架构上仍然更激进。从 capacity 归一化标定看，Performance 核的算力约为 837（以 Prime 核 1024 为基准），级差只有约 18%。这使得 EAS 的迁核逻辑更倾向于负载均衡而非节能压制——核心之间的能效差异本身就小了，“跑错了核”的惩罚远低于传统大小核架构。这种设计反映了厂商对"全大核"趋势的探索——随着工艺进步和功耗控制的改善，低性能小核的价值在下降。

**全大核设计**

联发科天玑 9400 也被称为"All Big Core"设计——它的"最小"核心是 Cortex-A720，这在几年前已经算是大核级别了。这说明 ARM 的核心设计也在不断提升：每一代小核的性能都在逼近上一代大核的水平。

[已验证: ARM 官方文档, MediaTek 官方发布, Qualcomm Snapdragon 8 Elite 技术规格]
[适用版本: Android 13 - Android 16]

### 配置趋势对性能分析的影响

核心配置的多样化意味着性能分析时不能简单地套用一个通用的"大核 = CPU 7"规则。分析时需要注意：

1. **先搞清楚目标设备的核心布局**。不同设备的核心编号、频率、capacity 值都不同。在 Perfetto 中可以通过 CPU Frequency 轨道和 CPU Scheduling 轨道来推断。
2. **关注线程在核心间的迁移模式**。一个线程如果频繁在小核和大核之间反复横跳，可能意味着调度器的 upmigrate/downmigrate 阈值设置不合理，或者线程本身的负载波动很大。
3. **理解不同 SoC 厂商的客制化策略差异很大**。OEM 厂商通常会对调度器做大量定制（比如 OPPO 的蜂鸟引擎、小米的 MIUI 调度策略），导致同样的负载在不同手机上的调度行为完全不同。

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## 核心迁移的触发条件与性能影响

在 [5.1 Linux 进程调度基础] 中我们讨论了 CFS 调度器的基本原理，在 [5.2 EAS 能量感知调度] 中了解了 EAS 如何利用能量模型进行选核决策。这里我们聚焦在核心迁移的实际触发机制和性能影响上。

### 核心迁移的触发条件

任务从一个小核迁移到大核（或反向），主要有以下几种触发条件：

**1. 唤醒时选核（Wake-up Placement）**

当线程从 Sleep 状态被唤醒时，调度器需要为它选择一个目标 CPU。EAS 调度器会：

- 评估线程的 `util`（利用率），反映它需要多少计算资源。这个值是通过 PELT（Per-Entity Load Tracking）机制持续追踪的——PELT 使用指数衰减移动平均来计算每个调度实体（线程、cgroup、CPU rq）的最近负载，时间常数约 32ms（一个 PELT 窗口的 1024us × 32），确保近期活跃的权重远大于历史活跃。
- 遍历所有可用的 CPU 核心，比较线程的 `util` 和每个核心的 `capacity`（容量）。capacity 是内核在启动时根据每个核心的最高频率和微架构 IPC 差异计算出的归一化算力值（以同 SoC 中最强核心为 1024 基准），可以通过 `/sys/devices/system/cpu/cpu<N>/cpu_capacity` 读取。大核的 capacity 远高于小核。
- 在所有满足 `capacity > util` 的核心中，利用内核中预置的**能量模型（Energy Model）**选择一个让系统总功耗最低的核心。

唤醒时选核是最常见的迁移时机，因为它天然就是一个"需要做决策"的时刻。

**2. 负载均衡（Load Balancing）**

调度器会周期性地检查系统的负载分布。如果发现某个核心（比如一个小核）上的任务过多导致利用率饱和，而另一个核心（比如一个大核）很空闲，调度器会将一个高负载任务从小核"拉"到大核上，以恢复负载平衡。

负载均衡的检查周期和迁移阈值是可调的，Android 设备上通常会针对前台应用的交互场景做激进的优化——在触摸屏幕或启动应用时，关键线程会更积极地被迁移到大核上。

**3. RTG（Related Thread Group）驱动的集群偏好**

[来源: Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md]

部分 Android 厂商内核（以 Qualcomm vendor 分支为代表）中有一个客制化机制叫 **RTG（Related Thread Group）**。它的核心思想是：把一组有关联的线程（比如同一个 App 的主线程、RenderThread、Binder 线程）放在同一个 CPU 集群上，以利用集群内的共享缓存，减少缓存未命中。

RTG 维护了一个 `preferred_cluster`（偏好集群）字段，根据组内所有线程的累计负载来决定应该优先使用哪个集群。当组内某个线程被设置了 `SCHED_BOOST_ON_BIG` 属性时，整个组都会被"boost"到大核集群上。

RTG 还有一个重要功能是**负载聚合（Colocation Boost）**：当 RTG 组内的高负载线程被调度到大核上时，schedutil governor 在计算大核的频率时，会把 RTG 组的累计负载也纳入考虑，而不仅仅是当前核心上的单个任务负载。大核频率会被适当拉高，以更好地服务整组线程。

> **注意：** RTG 并非 AOSP/GKI 主线机制，在 android16-6.12 common kernel 的 `kernel/sched/` 中未找到对应符号。它主要存在于 Qualcomm 等厂商的 vendor kernel 分支中。GKI 主线上实现类似效果的机制包括 task_profiles、cpuset、uclamp 和 Power HAL 提示链（§5.2、§5.4）。

[来源: Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md — 可能基于 vendor kernel 分析]

### 迁移的性能影响

核心迁移不是免费的。它带来的性能影响主要有两方面：

**缓存效应**

当任务从一个核心迁移到另一个核心时，它的 L1/L2 缓存数据不会跟着走。新核心的 L1/L2 缓存是冷的，需要从 L3（如果是 DynamIQ 集群）或主存重新加载数据。在 DynamIQ 架构下，由于所有核心共享 L3 缓存，迁移后的缓存恢复速度比传统 big.LITTLE 快得多。但如果在 Trace 中看到线程在大核和小核之间频繁来回迁移（"乒乓效应"），那么每次迁移都要付出缓存冷启动的代价，实际性能可能还不如一直待在一个核心上。

**DVFS 延迟**

同一集群内的核心通常共享电压/频率域。当任务从小核迁移到大核时，大核可能处于低频状态，需要 DVFS 把频率提上来。DVFS 的响应时间通常在几百微秒到几毫秒之间，取决于硬件和驱动实现。任务迁移到大核后，需要一小段时间才能达到全速运行。这也是为什么 Android 厂商在应用启动等场景会通过 Power HAL 预先把大核频率拉高——减少迁移后的"爬坡时间"。

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

### 在 Perfetto 中观察核心迁移

在 Perfetto 中，可以通过以下方式观察线程的核心迁移行为：

1. **线程的 CPU 轨道**：选中一个线程，在 thread_state 轨道中查看每个 Running 切片的 `cpu` 字段。如果频繁在不同的 CPU 之间跳转，说明迁移频繁。
2. **CPU Frequency 轨道**：结合频率变化看——线程迁移到一个核心后，那个核心的频率是否及时拉高了？如果频率迟迟上不去，说明 DVFS 响应慢或者有温控限制。
3. **SQL 查询**：

```sql
-- 查看某线程在各 CPU 上的调度片段数和累计运行时间
SELECT s.cpu, COUNT(*) AS slices, SUM(s.dur) / 1e6 AS total_running_ms
FROM sched s
JOIN thread t USING (utid)
WHERE t.tid = <target_tid>
GROUP BY s.cpu
ORDER BY s.cpu;
```

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## cpufreq governor：schedutil 的工作原理

了解了核心迁移的机制后，自然要问：选定核心之后，这个核心应该跑多快？CPU 频率直接影响代码执行速度，也与功耗正相关。在 Perfetto 中，CPU Frequency 轨道显示了每个核心在不同时间的运行频率。但频率不是随便变化的——它由 **cpufreq governor** 决定。

### 从性能 governor 到 schedutil

早期的 Android 使用 `interactive` 或 `ondemand` governor，它们的调频逻辑比较简单：看 CPU 空闲时间的比例。空闲多了就降频，空闲少了就升频。这种方式有一个明显的问题：**它只能看到"当前 CPU 繁不忙"，看不到"是谁在忙"**。

`schedutil`（scheduler utilization governor）从 Linux 4.7 开始引入，Android 从 Android 9（Pie）开始大规模采用。它的核心改进是直接**与调度器集成**，利用 PELT（Per-Entity Load Tracking）数据来做调频决策。

### schedutil 的工作流程

schedutil 的调频决策可以简化为以下步骤：

1. **获取 CPU 利用率**：调度器在每次调度事件（唤醒、迁移、负载均衡等）时，会计算目标 CPU 的总利用率——即该 CPU 上所有 runnable 线程的 `util` 之和。
2. **线性映射到频率**：schedutil 使用一个近似线性映射把利用率换算成目标频率：`next_freq ≈ 1.25 × max_freq × util / capacity`（这里的 1.25 是 `map_util_perf()` 加的性能裕量 / headroom）。实际频率还要经过 `sugov_effective_cpu_perf()` 综合 uclamp 约束、deadline 带宽下限（`bw_min`）、`rate_limit_us` 和 cpufreq driver 约束后才能确定，不能把上面的近似公式当作最终输出。
3. **应用 rate_limit**：为了避免频率抖动（短时间内频繁升降频），schedutil 有一个 `rate_limit_us` 参数（通常为 1-2ms），限制两次调频之间的最小间隔。
4. **特殊处理**：
   - **实时任务（RT/DL）**：现代内核（v6.6/android16-6.12）中，schedutil 已不再对 RT/DL 任务直接置顶频率。实际路径是 `effective_cpu_util()` 将 RT/DL 带宽需求纳入 `bw_min` 计算，`sugov_update_single_freq()` / `sugov_update_shared()` 在检测到 `bw_min > 0` 时把频率下限锁定到满足带宽的最低值。当 RT/DL 带宽占满 CPU 时，频率自然会映射到最高，但这走的是带宽约束路径，不是“直接置顶”。
   - **I/O Boost**：当线程在进行 I/O 操作时（比如从磁盘读取数据），schedutil 会临时抬升其利用率估计，让频率更快地提上去。这是因为 I/O 操作通常与用户体验直接相关（比如加载页面、读取文件），需要更快的响应。

schedutil 的核心调频函数是 `sugov_get_util()`，它负责汇总目标 CPU 上所有调度类的利用率。以下展示 android16-6.12 GKI 内核中的实际实现（简化展示关键逻辑）：

```c
// android16-6.12（GKI）kernel/sched/cpufreq_schedutil.c
// 简化展示核心路径，省略部分变量声明和边界处理
static void sugov_get_util(struct sugov_cpu *sg_cpu, unsigned long boost)
{
    unsigned long min, max;
    unsigned long util = cpu_util_cfs_boost(sg_cpu->cpu) + boost;

    max = arch_scale_cpu_capacity(sg_cpu->cpu);
    // effective_cpu_util 合并 CFS + RT + DL 利用率，
    // 并根据 FREQUENCY_UTIL 类型应用 uclamp 约束
    // 返回值即为用于频率选择的最终 util
    util = effective_cpu_util(sg_cpu->cpu, util, &min, &max);

    // bw_min: deadline 带宽的最低频率保障
    sg_cpu->bw_min = min;
    // sugov_effective_cpu_perf: 综合 util、max、boost，
    // 计算最终的目标性能值
    sg_cpu->util = sugov_effective_cpu_perf(sg_cpu->cpu, util, min, max);
}
```

这段代码的要点：`effective_cpu_util()` 是核心汇总函数，把 CFS、RT、deadline 三类调度实体的利用率合并，并根据 uclamp 约束裁剪出最终的 `util` 和 `min/max` 范围。android16-6.12 与 Linux v6.6 mainline 的差异在于：mainline 的 `sugov_get_util` 接受单个 `struct sugov_cpu *` 参数，内部使用 `FREQUENCY_UTIL` / `ENERGY_UTIL` 枚举区分调频与选核；android16-6.12 增加了 `unsigned long boost` 参数，改为直接通过 `effective_cpu_util` + `sugov_effective_cpu_perf` 两步完成，引入 `bw_min` 作为 deadline 带宽的下限保障，并预留了 `scx_cpuperf_target()` 接口用于 sched_ext 可编程调度。RT/DL 任务的频率映射在 `sugov_update_single_freq()` / `sugov_update_shared()` 中处理：`bw_min > 0` 时频率下限被锁定到带宽约束对应的最低频率，如果带宽需求接近 CPU 满载，最终频率自然会接近最高值。

[已验证: android16-6.12 kernel/sched/cpufreq_schedutil.c; Linux v6.6 mainline 同文件对比]

### schedutil 与 EAS 的配合

在上一节 [5.2 EAS 能量感知调度] 中我们讲到，EAS 负责决定任务放在哪个核心上。schedutil 负责决定核心跑多快。两者通过 PELT 共享的利用率数据来协调：

- EAS 选核时用的是任务的 `util` 值。如果一个小核的 capacity 足够装下任务（`capacity > util`），EAS 会倾向选小核以节省功耗。
- 但如果任务持续运行在小核上、且 util 接近小核的 capacity 上限，schedutil 会把小核频率拉到最高。这时候可能出现在 Perfetto 中的现象是：**小核频率很高，但任务仍然很慢**——因为小核的绝对性能上限低，即使跑在最高频率也比大核的中频慢。

这就是为什么在 Perfetto 中看到"高频 + 小核 + 仍慢"时，不应该简单地认为"频率不够"，而应该优先考虑**选核问题**——任务是否应该被迁移到大核上。

### uclamp：约束调度器和 governor 的利用率先验

在 cpufreq / schedutil 这条线上，uclamp 可以直接理解成对 util 信号加上下限和上限。`effective_cpu_util()` 汇总 CFS、RT、DL 负载之后，还会把 `UCLAMP_MIN` / `UCLAMP_MAX` 一起算进去，所以 schedutil 看到的是 clamp 之后的有效 util，不再等同于原始 PELT util。

这会直接改变调频结果。前台关键线程带着较高的 `uclamp_min` 被唤醒时，即使 PELT 还没爬起来，schedutil 也会按更高的 util 计算目标频率，大核频率因此更早拉起；后台任务如果被写了较低的 `uclamp_max`，瞬时 util 冲高时也更难把频率和选核一路推到顶。Android 用户态怎样通过 task profile、libprocessgroup 和 cgroup 把 clamp 值送进内核，§5.2 已完整展开，这里只保留与频率选择直接相关的部分。

排查这类场景时，把 `/proc/<tid>/sched` 里的 clamp 字段、CPU Frequency 轨和线程迁移一起看，通常就能解释“util 看起来不高，频率却先上来了”的现象。

### 影响频率的其他因素

schedutil 的决策并不是最终频率，还有几个约束会叠加在 schedutil 的选择之上：

1. **Power HAL 的场景策略**：Android Framework 通过 Power HAL 向内核传递当前的系统"场景"信息。比如在应用启动（LAUNCH）、触摸交互（INTERACTION）、游戏等场景，Power HAL 会抬高 CPU 的**地板频（floor frequency）**——即 `scaling_min_freq`。这保证了在关键场景下 CPU 不会因为利用率低而降频到很低的水平。

2. **温控（Thermal Throttling）**：当设备温度超过预设阈值时，温控系统会强制降低 `scaling_max_freq`（天花板频）。此时即使 schedutil 想要更高的频率、Power HAL 也申请了更高的性能，CPU 频率也上不去。这是分析游戏掉帧、持续负载性能下降时优先要排查的因素。

3. **省电模式**：低电量或手动开启省电模式时，系统同样会压低天花板频。

在 Perfetto 中，CPU Frequency 轨道上能直接看到频率的上下限变化。如果频率被压在某个较低值不变，且不受负载变化影响，大概率是温控或省电模式在起作用。

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]
[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-scheduling]

## 不同核心对单线程性能和多线程吞吐量的差异

前面讨论了核心迁移和调频机制，接下来我们看一个更基础的问题：不同类型的核心在同样频率下，性能差距到底有多大？

### "同频不同效"——频率不是衡量性能的唯一标准

在 Perfetto 中我们会看到不同核心的频率值，但**大核 2.0GHz 和小核 2.0GHz 的实际性能完全不同**。这背后的原因有几个层次：

**微架构差异导致 IPC 不同**

大核通常有更宽的乱序执行窗口、更多的执行端口、更大的 L1/L2 缓存、更激进的分支预测和预取。在同样的时钟周期内，大核能完成更多的指令（IPC 更高）。同频下，大核完成同样工作所需的时间更短，消耗的能量也更少。

**缓存层次差异**

大核通常有更大的 L2 缓存（比如 1-2MB vs 小核的 256-512KB），对访存密集型任务的性能影响显著。如果工作集（working set）超过小核的 L2 容量但不超过大核的 L2 容量，性能差距可能达到 2-3 倍——这在 Perfetto 中会直接体现为同一段代码在小核上的 wall duration 是大核的 2-3 倍。

**能效曲线非线性**

小核在接近最高频时，电压会急剧升高，导致边际能耗飙升——频率只提升了一点点，功耗却翻倍了。而大核在中等频点的"每瓦性能"可能反而更好。这就是为什么在性能分析中，不能简单地用频率来比较不同核心的"能效"。

### 单线程性能：超大核的价值

对于 UI 响应、应用启动这类**单线程延迟敏感**的场景，超大核（Cortex-X 系列）的价值就体现出来了。以 Cortex-X925（2024 年发布）为例：

- 相比上一代 Cortex-X4，单核性能提升约 36%（Geekbench 6 测试），得益于更高的时钟频率（最高 3.6GHz vs 3.4GHz）和 15% 的 IPC 提升。
- 微架构改进包括：4 条加载流水线、双周期 ALU、向量单元数量增加 50%、指令缓存和数据缓存带宽翻倍。
- 代价是更大的芯片面积和更高的峰值功耗，所以通常只配置 1 个超大核。

在 Perfetto 中，如果在 Trace 中观察到前台 UI 线程始终没有运行在超大核上，而应用又有明显的启动或响应延迟，这可能是调度策略需要优化的信号。

### 多线程吞吐量：核心数量的权衡

对于视频编码、图片处理、后台编译这类**多线程吞吐量敏感**的场景，所有核心的总算力更关键。一个 1+3+4 的配置意味着：

- 短时间的突发负载：4 个小核 + 3 个大核 + 1 个超大核全部出动，总并发能力是 8 线程。
- 持续负载：受限于热设计功耗（TDP），通常不可能所有核心都以最高频率同时运行。调度器会根据温度和功耗预算动态调整每个核心的频率上限。

这也解释了为什么在持续重负载场景（如长时间游戏），即使有 8 个核心，我们可能也只能看到 3-4 个核心在高频运行，其余核心被降频甚至离线。

[已验证: ARM 官方文档 — Cortex-X925 技术规格, developer.arm.com]
[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## 在 Perfetto/工具中的表现

### 识别核心类型

在 Perfetto 中，最直接的方式是看 CPU Frequency 轨道上的频率上限差异。同簇核心的频率会同步变化，不同簇核心的频率独立变化。通过观察频率变化模式，可以推断出核心的分组。

也可以使用以下 SQL 查询来辅助判断：

```sql
-- 按 CPU 分组，查看全局调度片段的时长分布
SELECT
  s.cpu,
  COUNT(*) AS num_slices,
  SUM(s.dur) / 1e6 AS total_running_ms
FROM sched s
GROUP BY s.cpu
ORDER BY s.cpu;
```

通常，大核上会有更多前台关键线程（如主线程、RenderThread）的运行时间，而小核上更多是后台进程。

### 正常与异常的核心分配模式

**正常模式**：
- 应用启动时，主线程迅速迁移到超大核或大核上，大核频率被拉高。
- 滑动/交互时，UI 线程和 RenderThread 在大核上运行。
- 后台同步、推送等轻量任务在小核上运行。

**异常模式**：
- 主线程长时间运行在小核上（CPU 0-3），导致启动慢、卡顿多。可能的原因：调度器 upmigrate 阈值过高，或者 RTG 没有正确地将关键线程聚合到大核。
- 线程在大核和小核之间频繁来回迁移（乒乓效应），导致缓存命中率低。在 Perfetto 中会看到同一时段内，线程的 Running 切片分布在不同 CPU 上。
- 大核频率被限制在较低水平（温控或省电模式），即使有高负载任务也无法提速。在 CPU Frequency 轨道上会看到频率上限被压低。

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]
[来源: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]

## 与其他机制的关系

大小核架构不是孤立运作的，它与多个系统机制紧密关联：

- **EAS 能量感知调度**（[5.2]）：EAS 利用了大小核架构的异构特性，通过能量模型在选核时优先考虑功耗效率。
- **DVFS 与功耗管理**（[5.4]）：DVFS 决定了每个核心簇的运行频率，与大小核的核心选择策略共同决定系统的性能-功耗平衡。
- **Thermal 管控**（[5.5]）：温控系统会限制大核的最高频率，甚至直接把大核离线（offline），这会改变大小核架构的可用核心组合。
- **Android 功耗管理**（[5.6]）：Power HAL 通过场景策略影响 CPU 频率的地板频和天花板频，间接影响大小核的实际性能表现。
- **MainThread 与 RenderThread 协作**（[2.5]）：这两个线程是 Android 渲染管线的关键，它们的 CPU 核心分配直接影响帧渲染时间。

## 常见问题与误区

### 误区 1："大核频率高，所以大核总是更快"

不完全对。大核的优势来自微架构（更宽的流水线、更大的缓存、更好的分支预测），不仅仅是频率。即使大核和小核运行在相同频率下，大核的 IPC 仍然更高。反之，大核被温控降频到低频时，性能可能还不如高频小核——但这种情况在实际中不太常见，因为大核的微架构优势通常足以弥补频率差距。

### 误区 2："小核没用，应该全部用大核"

从纯性能角度看，全大核有优势（骁龙 8 Elite 就在尝试）。但从能效角度看，小核在处理大量低负载后台任务时比大核更省电。关键在于调度器能否正确地识别任务特征，把轻量任务留在小核上。如果调度策略合理，小核可以显著延长续航。

### 误区 3："频率越高越好"

在异构 CPU 上，频率必须结合核心类型理解。小核 2.0GHz 和大核 2.0GHz 的实际性能完全不同。而且小核在接近最高频时能效会急剧恶化——频率只提升了一点点，功耗却可能翻倍。所以"拉高小核频率"不是一个好的优化策略。

### 误区 4："线程在哪个核心上是调度器的事，我管不了"

虽然应用开发者通常不直接控制线程的 CPU 亲和性（affinity），但有一些间接方式可以影响调度决策：
- **线程优先级**：通过 `Process.setThreadPriority()` 设置更高的优先级（更低的 nice 值），调度器会更积极地把高优先级线程放到大核上。
- **线程亲和性**：通过 `sched_setaffinity` 系统调用直接指定线程可以运行在哪些核心上。这在系统级开发和 OEM 定制中很常见（比如绑定 RenderThread 到大核上，参见高爷的文章"Android性能优化之绑定RenderThread到大核CPU"）。
- **cgroup 和 cpuset**：Android 使用 cgroup 来划分前台/后台进程组，前台组的线程更容易被调度到大核上。

### 误区 5："绑核（affinity）是万能的优化手段"

绑核能解决"关键线程被调度到小核"的问题，但也有代价：一旦绑定了某个核心，即使那个核心被温控降频，线程也无法迁移到其他核心上。在实际优化中，绑核通常是"兜底手段"，更稳的做法是调整 RTG 策略或调度器 upmigrate 阈值，让调度器自己做出正确的选核决策。绑核适合用于经过充分验证的固定场景（比如已知 RenderThread 的负载特征稳定），但不适合负载波动大的场景。

[来源: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]
[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## 版本演进

| 时期 | 架构/技术 | 特点 |
|------|----------|------|
| 2011-2014 | big.LITTLE 第一代 | 双集群，集群迁移模式，4+4 配置 |
| 2014-2016 | HMP（异构多处理） | 所有核心同时在线，独立调度 |
| 2017-2019 | DynamIQ 发布 | 统一集群，共享 L3 缓存，独立核心控制 |
| 2019-2021 | Cortex-X 系列引入 | 超大核概念，1+3+4 配置成为主流 |
| 2022-2024 | 三层核心普及 | A710/A715/A720 + A510/A520 + X2/X3/X4，三层核心成为旗舰标配 |
| 2024-2025 | "全大核"趋势 | 天玑 9400（全 Cortex-A 系核心），骁龙 8 Elite（2+6 Oryon 核心），小核逐步退出旗舰 |

[已验证: ARM 官方发布时间线, MediaTek/Qualcomm 官方技术文档]

## 扩展：Cortex-X 系列超大核的定位与功耗特性

Cortex-X 系列是 ARM 从 2020 年开始推出的"超大核"产品线，定位是"超越标准 Cortex-A 大核的极致单线程性能"。它的设计目标是缩短与苹果 A 系列（以及后来的 M 系列）自研核心在单核性能上的差距。

Cortex-X 系列的核心特点：

- **更大的微架构**：相比同代 Cortex-A 大核，Cortex-X 有更宽的流水线、更多的执行单元、更大的缓存。以 Cortex-X925 为例，它有 4 条加载流水线和翻倍的缓存带宽，这些在标准 Cortex-A725 上是没有的。
- **更高的峰值性能，但峰值功耗也更高**：Cortex-X925 在 Geekbench 6 上的单核分数比 Cortex-X4 高 36%，但维持最高频率时的功耗也显著更高。所以在持续重负载场景（如长时间游戏），超大核通常不会持续跑在最高频率，而是在中高频区间波动。
- **通常只配置 1 个**：由于芯片面积和功耗预算的限制，旗舰 SoC 通常只配置 1 个 Cortex-X 核心，专门用于应用启动、页面加载等突发单线程场景。

从性能分析角度看，超大核的存在意味着"CPU 7 上的线程不一定比 CPU 4-6 上的线程快多少"这个判断不再成立——如果设备有 Cortex-X 超大核，CPU 7 上的单核性能可能比其他大核高 20-30%。在分析启动性能时，确认主线程是否被调度到了超大核上是一个重要的检查点。

[已验证: ARM 官方文档 — Cortex-X925, developer.arm.com/products/silicon-ip-cpu/cortex-x925]

## 扩展：GPU + NPU 的协同调度概念

[需补充素材: GPU + NPU 与大小核架构的交互关系仍缺少可靠素材，需要补充任务卸载（offloading）策略、GPU/NPU 在异构计算中的角色、以及这些任务对 CPU 调度的影响。]

## 参考资料

- ARM big.LITTLE 技术介绍：https://developer.arm.com/Architectures/big.LITTLE
- ARM DynamIQ 技术白皮书：https://developer.arm.com/documentation
- Cortex-X925 技术规格：https://developer.arm.com/products/silicon-ip-cpu/cortex-x925
- Linux kernel schedutil 源码：kernel/sched/cpufreq_schedutil.c
- Perfetto CPU Scheduling 文档：https://perfetto.dev/docs/data-sources/cpu-scheduling
- 高爷原创：Android性能优化之绑定RenderThread到大核CPU [来源: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]
- 高爷原创：Android Perfetto 系列 — CPU [来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]
- 调度器分支之 RTG [来源: Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md]
