---
title: "大小核架构"
chapter: "5.3"
section: "5.3"
status: finalized
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
reviewed_date: "2026-06-05"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
task2b_result: fixed
last_task2b_at: "2026-06-03T21:33:00+08:00"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
task9_result: pass-tech-review
task9_reviewed_date: "2026-06-05"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-05T06:20:00+08:00"
last_task9_audit: "2026-07-11"
review_notes: "2026-05-05 task6 review: L1/L2 小修完成；GPU/NPU 协同调度扩展仍为空壳，已写入 queue/suggestions 回炉。；2026-05-18 task6 revisiting: L1/L2 小修完成；GPU + NPU 扩展仍为占位，已合并写入 queue/suggestions，等待 Task2B 补素材或裁剪。"
task6_reviewed_date: "2026-05-18"
last_task6_at: "2026-06-05T05:12:00+08:00"
last_task6_review_log: "logs/review/2026-05-18-16-review.md"
task6_review_notes: "2026-05-18 Task6：修正口语化迁移描述和结构性过渡语；GPU + NPU 协同调度扩展仍缺素材，已投递 Task2B 回炉。"
last_task9_review_log: "logs/deep-review/2026-06-05-06-deep-review.md"
task9_review_notes: "2026-05-15 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 0；新增问题已写入 queue，等待 Task2B 回炉。；2026-05-18 task9 deep-review: P0 1 / P1 0 / P2 1；android16-6.12 sugov_get_util() 代码块与实际源码不一致，需 Task2B 修正；骁龙 8 Elite capacity 数值需补一手锚点。；2026-06-05 task9 deep-review: pass-tech-review。P0/P1 0；schedutil android16-6.12 源码与正文一致；GPU+NPU 扩展占位作为 P2 建议记录。"
last_task6_audit: "2026-06-05"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-05
last_task9_audit_at: "2026-07-11T21:27:05+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-11-21-audit.md"
last_task9_audit_result: "pass-idle-audit"
last_task9_audit_notes: "idle audit: 维度1（源码引用准确性）和维度3（版本差异覆盖）复核通过；android16-6.12 与 android17-6.18 的 schedutil `sugov_get_util()`/`scx_cpuperf_target()` 路径一致；未发现超出 Android 17/API 37 的源码结论。"
---

# 5.3 大小核架构

> [!info] 源码锚点
> 正文按 Android 17 / API 37 / `android-17.0.0_r1` 与 kernel `android17-6.18-2026-06_r6` 复核。具体 SoC 的核心名称、编号、capacity 与 cpufreq policy 属于设备实现；未从目标设备内核或 sysfs 读取的数据不当作平台保证。

## 先区分四个容易混用的概念

Perfetto 会显示 CPU 编号、线程运行切片和频率计数器。要解释这些数据，先把四个概念分开：

| 概念 | 回答的问题 | 可靠来源 |
| --- | --- | --- |
| CPU microarchitecture | 同频下每周期大约能完成多少工作 | SoC/Arm 技术资料、目标设备测试 |
| scheduler capacity | 内核认为 CPU 的最大相对算力与当前可用能力是多少 | `arch_scale_cpu_capacity()`、scheduler topology、thermal/IRQ pressure |
| cpufreq policy | 哪些 CPU 共享一套频率控制，以及可选频点是什么 | `/sys/devices/system/cpu/cpufreq/policy*` |
| Energy Model performance domain | 哪组 CPU 共享 active power cost table | 目标内核注册的 EM、scheduler debug 信息 |

这四者经常重合，却没有一一对应的保证。两个 CPU 可以共享 cpufreq policy，但 capacity 不同；宣传材料中的“中核”也不一定对应独立 performance domain。

CPU 编号更没有跨设备语义。CPU 7 可能是最高 capacity CPU，也可能只是某个同构簇成员。分析前先识别拓扑，再谈“大核”“小核”。

## 从 big.LITTLE 到多档异构 CPU

### 早期 big.LITTLE 的软件模型

Arm big.LITTLE 把侧重单线程性能的 CPU 与侧重能效的 CPU 放进同一 SoC。早期实现经历过几种软件模型：

1. **Cluster migration**：一个 cluster 工作时，另一个对应 cluster 关闭；切换粒度较粗。
2. **In-kernel switcher**：把一颗高性能 CPU 与一颗高能效 CPU 配成逻辑对，任一时刻只启用其中一颗。
3. **Global task scheduling / HMP**：所有 CPU 对内核可见，调度器按任务需求选择 CPU，并允许不对称数量配置。

这些模型用于理解历史演进。Android 17 / kernel 6.18 的公共调度路径以 capacity-aware scheduling、EAS、cpuset、UClamp 和负载均衡为主，不应继续套用早期“一次切换整个 cluster”的运行图。

历史资料常给迁移标注固定微秒数。迁移成本会随互连、cache hierarchy、工作集、源/目标 CPU 是否共享 LLC、频率状态和内核路径变化，不能把某个平台测得的数值写成架构常量。

### DynamIQ 改变了 cluster 内组织方式

DynamIQ 允许不同 CPU microarchitecture 在同一 DynamIQ cluster 中协作，并通过 DSU 提供共享的系统级 cache 与一致性支持。它降低了部分跨类型 CPU 共享数据的成本，也允许更灵活的核心组合。

仍要保留三个边界：

- 共享 LLC 不会搬走源 CPU 私有的 L1/L2 内容，迁移后仍可能发生 cold miss；
- DynamIQ 提供的能力不等于每款 SoC 都实现 per-CPU DVFS，实际频率控制看 cpufreq policy；
- DSU 型号、cache 容量和互连拓扑由 SoC 决定，不能用一个 Arm IP 上限描述所有 Android 设备。

16 KB page size 主要改变 TLB reach、页表层级行为和内存管理成本。公开的通用 DSU 接口没有把“16 KB 页会降低 snoop filter 探测频率”定义为平台保证，因此不能据此推导互连收益。

### 当代 SoC 不止“大”和“小”

常见布局可以抽象为：

- 两档：高能效 CPU + 高性能 CPU；
- 三档：高能效 CPU + performance CPU + prime CPU；
- 多颗 performance CPU + 少量 prime CPU；
- 市场上称为“全大核”的组合。

这些名称适合描述产品，不适合作为调度器输入。Linux 关心的是每颗 CPU 的 capacity、允许范围、当前压力、performance domain 和 Energy Model。即使两类 CPU 的 capacity 很接近，power cost 仍可能不同；反过来也一样。

因此，不从公开规格外推诸如“某 CPU capacity=837”这样的数字。精确分析应读取目标设备的 capacity 数据或对应 kernel tree。

## Linux 怎样表达 CPU capacity

### original capacity 与当前 capacity

kernel 6.18 的 Capacity Aware Scheduling 文档把最大能力近似写成：

```text
capacity(cpu) = work_per_hz(cpu) × max_freq(cpu)
```

系统中最强 CPU 的 original capacity 归一化为 `SCHED_CAPACITY_SCALE=1024`，其他 CPU 按相对能力缩放。`arch_scale_cpu_capacity(cpu)` 返回 original capacity。

运行时可用 capacity 还会扣除部分压力，例如 IRQ、thermal pressure 与 cpufreq pressure。对 EAS、misfit migration 或 `util_fits_cpu()` 来说，静态的 1024/某个较小值只是起点。

单个 capacity 标量也有局限。两种 microarchitecture 在整数、浮点、向量、分支和内存访问上的相对性能不同，无法由一个数字完整表达。capacity 适合调度器做快速近似，微基准与业务测试仍是性能结论的依据。

### util 与 capacity 的比较带有余量

任务的 PELT/util_est 经 frequency invariance 与 CPU invariance 处理后，可以与 capacity 比较。kernel 6.18 的 `fits_capacity(util, capacity)` 采用约 20% margin：

```text
util × 1280 < capacity × 1024
```

所以 `util=800` 并不能算作“刚好装进 capacity=800 的 CPU”。这段余量用于避免任务在临界位置反复迁移，也给突发负载留出空间。

UClamp 会进一步影响 `util_fits_cpu()`。`uclamp.min` 可能表达更高性能点，`uclamp.max` 可能让被封顶任务在较低 capacity CPU 上仍被视为 fit。UClamp 没有提供 CPU 时间配额，也不会单独决定目标 CPU。

### thermal pressure 会改变“装得下吗”

当 thermal 或 cpufreq 限制使 CPU 无法达到原有最高性能时，内核会降低相应可用 capacity。于是同一个任务在冷机时可能 fit，热稳态下可能变成 misfit，并被负载均衡迁往其他可用 CPU。

这也是持续性能分析必须进入热稳态的原因。只比较冷机前几秒的核心分布，无法说明设备在长期功耗预算下的行为。

## 在设备和 Perfetto 中识别拓扑

### 先读 sysfs，再看 Trace

下面的命令只读取目标设备状态，可用于建立 CPU、capacity 与 cpufreq policy 的对应关系：

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

有些量产设备会隐藏 `cpu_capacity`、可用频点或 governor 节点。读不到时，应转向设备内核配置、vendor 源码或具备权限的 debug 接口，不能只用最大频率替代 capacity。

Perfetto 的 stdlib 可以汇总 Trace 期间观测到的频率。下面的查询用于发现共享变化模式和观测上限：

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

`freq` 的单位是 kHz。`observed_max_mhz` 只是采集窗口内出现过的最高频率；设备若未跑到最高 OPP，它会低于 `cpuinfo_max_freq`。同样，两个 CPU 的频率同时变化只能提示共享 policy，还应由 `related_cpus` 确认。

### 不要用 CPU 编号或最高频率单独分类

最高频率较高的 CPU 往往 capacity 也较高，但 work-per-Hz 可能不同。仅看频率无法区分：

- 同频但 microarchitecture 不同；
- 不同频但最大 capacity 相近；
- policy 被 thermal 或省电模式临时封顶；
- 硬件自治 DVFS 让软件 counter 与瞬时执行频率存在差异。

可靠做法是把 capacity、cpufreq policy、频率、线程 runtime 与业务 deadline 放在一起看。

## 任务为什么会换 CPU

### 唤醒时放置

对 fair task，`select_task_rq_fair()` 处理唤醒、fork 和 exec 等 placement。Android 17 kernel r6 在普通 `WF_TTWU` 路径中，root domain 未 overutilized 时会尝试 `find_energy_efficient_cpu()`。

EAS 不会遍历所有 CPU 后简单选“最省电的一颗”。它从每个 Energy Model performance domain 选出有代表性的 spare-capacity 候选，与 `prev_cpu` 比较 fit 和 energy delta。同步唤醒满足条件时，还可能直接使用当前 CPU fast path。

root domain overutilized 后，这次唤醒会跳过 EAS 能量估算，转到基于负载和 idle sibling 的选择路径。看到线程跑在某颗 CPU 上，不能默认归因于 EAS。

### 运行时负载均衡与 misfit migration

任务开始运行后，周期 load balance、newidle balance、active balance 和 misfit migration 可以继续迁移它。常见原因包括：

- 原 CPU runqueue 过载；
- 低 capacity CPU 无法满足任务需求；
- 其他 CPU 进入 idle，允许拉取任务；
- sched domain 的不均衡超过阈值；
- thermal pressure 改变 CPU 的可用 capacity。

这些路径不会为每次迁移调用 Energy Model。wake-up placement 与运行时 migration 属于不同问题，Perfetto 里要结合迁移前的线程状态判断。

### affinity、cpuset、hotplug 与隔离

线程最终可用 CPU 是 online CPU、affinity mask 与 cpuset 允许范围的交集。系统改变前后台 task profile、CPU offline、isolated CPU 或 vendor policy 时，即使线程负载没变，也可能被迫迁移。

下面的命令用于确认某个 tid 当时可去哪些 CPU：

```shell
adb shell 'cat /proc/<pid>/task/<tid>/status | grep Cpus_allowed_list'
adb shell 'cat /proc/<pid>/task/<tid>/cgroup'
```

affinity 只能缩小候选范围。把 RenderThread 固定到某一颗高 capacity CPU 会让它无法避开该 CPU 的竞争或 thermal 限制，应只作为有对照组的实验。

### RTG 属于厂商实现

Related Thread Group、colocation boost、preferred cluster 等机制常见于部分 vendor kernel。它们可以按相关线程组聚合需求、偏好 cluster 或影响频率提示。

这些符号不属于 Android 17 common kernel 的通用接口。不同厂商、不同代际的 RTG 数据结构和策略也可能变化。若 Trace 疑似受到 RTG 影响，应在目标 kernel tree、vendor hook 和 Power HAL 中寻找证据，不能根据线程名推断。

## 迁移成本怎样判断

### cache locality

迁移不会复制源 CPU 的私有 L1/L2 内容。目标 CPU 需要从共享 LLC、系统 cache 或内存重新取得数据。实际成本取决于工作集、cache 共享边界、写共享、NUMA/内存拓扑和迁移间隔。

DynamIQ 的共享 cache 能降低部分数据获取成本，但无法消除 private-cache cold miss。固定的“迁移需要 30 μs”或“新架构只需几微秒”都不适合作为跨设备结论。

### 频率与 policy 状态

任务迁入新 cpufreq policy 后，该 policy 可能还在低频。schedutil、I/O-wait boost、UClamp、Power HAL 和硬件 DVFS 会共同决定爬升速度。若多个 CPU 共享 policy，另一个 CPU 的负载也可能已经把频率拉高。

因此，“迁到大核后仍慢”至少要同时检查：

- 迁移前后的 Running 和 Runnable 时间；
- 源/目标 CPU 的 capacity 与 frequency；
- 是否跨 LLC 或 cpufreq policy；
- thermal/省电上限；
- 工作集是否发生 cache miss 增长。

### 用 Perfetto 统计分布与迁移

下面的第一条查询统计目标线程在各 CPU 上的运行时长：

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

这张表只能说明分布。要数相邻 Running slice 之间的 CPU 变化，可以用窗口函数：

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

相邻 slice 跨 CPU 表示两次运行之间目标 CPU 发生变化，但中间可能经历睡眠、唤醒和排队。它不能单独证明 cache migration 是延迟根因，还要与业务 slice、频率和 cache/PMU 数据对齐。

## Android 17 schedutil 怎样选频

### 当前源码路径

schedutil 使用调度器的利用率信号决定 cpufreq policy 的目标性能点。`android17-6.18-2026-06_r6` 的 `sugov_get_util()` 可概括为：

```text
util = sched_ext CPU perf target
if CPU 没有完全交给 sched_ext:
    util += boosted CFS util

util, min, max = effective_cpu_util(CFS + RT + DL + IRQ, UClamp)
util = max(util, I/O-wait boost)
target_perf = sugov_effective_cpu_perf(util, min, max)
```

`sugov_effective_cpu_perf()` 先用 `map_util_perf()` 添加约 25% DVFS headroom，再应用 minimum/maximum performance 约束。这个线性映射是假设，不等于硬件的实际性能曲线。

如果一个 cpufreq policy 覆盖多个 CPU，`sugov_next_freq_shared()` 会遍历 policy CPU，并采用其中最高的目标性能需求来选频。所以 Perfetto 中同 policy CPU 的频率联动符合源码预期。

### rate limit 没有跨设备固定值

`rate_limit_us` 限制调频请求频率。kernel 6.18 初始化时采用 `cpufreq_policy_transition_delay_us(policy)`，之后可以由 governor tunable 改写。它取决于 driver 与 policy，不应写成 Android 固定 1 ms 或 2 ms。

### I/O-wait boost 的适用范围

kernel 6.18 在 `SCHED_CPUFREQ_IOWAIT` 唤醒上维护 I/O-wait boost。连续、频繁的 I/O completion wakeup 会逐步提高 boost；超过一个 tick 没有新请求时会重置或衰减。它用于缩短 I/O 后续处理延迟，无法据此推断所有文件读取都会直接升到最高频。

### RT、DL、UClamp 与 sched_ext

`effective_cpu_util()` 合并 CFS、RT、deadline 与 IRQ 影响，并给 schedutil 返回性能上下界。RT/DL 并非简单地“出现就永久锁最高频”；deadline bandwidth、默认 RT UClamp 和设备配置会影响结果。

Android 17 common kernel 的 schedutil 还接受 `scx_cpuperf_target()`。只有 sched_ext 实际接管 CPU 或提供 perf target 时，这条输入才有意义；源码存在不代表量产设备默认启用 sched_ext 调度器。

### Power HAL 和省电/温控是外部约束

Power HAL 的实现可以应用 task profile、UClamp、cpuset、devfreq 或厂商节点，也可能调整 cpufreq floor/ceiling。Android 平台没有保证每个 LAUNCH/INTERACTION hint 都通过 `scaling_min_freq` 实现。

thermal 和省电模式可以限制最大 OPP，hardware DVFS 也可能在软件请求之外做选择。Perfetto 看到的频率是最终可观测结果，解释时应同时检查：

- `scaling_driver` 与 `scaling_governor`；
- policy min/max 与 thermal cap；
- UClamp/task profile；
- Power HAL 或 ADPF session；
- 硬件计数器是否提供 frequency invariance。

## 如何理解不同 CPU 的性能

### 同频不等性能

capacity 文档把最大能力拆成 work-per-Hz 与 max frequency。高性能 microarchitecture 往往有更宽的前后端、更大的乱序窗口、cache 和分支预测资源；相同频率下，它可能完成更多工作。

差距依 workload 而变：

- 计算与分支密集代码更受执行宽度、预测和前端影响；
- cache-resident workload 受 L1/L2 容量与延迟影响；
- memory-bound workload 可能主要受 LLC、DRAM 和带宽争用限制；
- 向量或加密代码还取决于具体执行单元。

因此，“大核一定快 2—3 倍”“同频大核耗能更少”都需要目标 workload 的实测支撑。

### 单线程延迟

应用启动、UI 主线程和部分脚本执行包含单线程关键路径，高 capacity CPU 可能缩短 CPU-bound 段。但线程若主要等待 Binder、锁、I/O 或 GPU，迁到 prime CPU 也不会消除等待。

判断是否需要更高 capacity CPU，应先比较 wall time、CPU time、Runnable wait 和 deadline。主线程没有运行在编号最大的 CPU，本身不构成问题。

### 多线程吞吐与热稳态

图片处理、编译和软件编解码等吞吐任务可以利用多颗 CPU，但并行度还受任务划分、锁、内存带宽和 thermal budget 限制。短时跑满全部 CPU 与长期维持最高频是两回事。

热稳态下，系统可能降低多个 policy 的频率、调整 task placement，甚至 offline 部分 CPU。有效指标应覆盖完成量/秒、能量/任务、温度和尾延迟，不能只数高频 CPU 数量。

## 一套可复现的分析顺序

1. **标出业务 deadline**：定位启动、帧、音频或推理区间。
2. **确认线程状态**：区分 Running、`R/R+`、锁/Binder/I/O 等等待。
3. **建立设备拓扑**：记录 capacity、cpufreq policy、online CPU、affinity 与 cpuset。
4. **对齐运行结果**：统计各 CPU runtime、迁移、频率和 idle。
5. **检查外部约束**：thermal、battery saver、Power HAL、UClamp、ADPF 和 vendor hook。
6. **提出单一假设**：例如“低 capacity CPU 无法在 deadline 内完成 CPU-bound 段”。
7. **做 A/B 验证**：比较延迟分位数、功耗与热稳态，不只看一次 Trace。

### 正常现象

- 短任务留在低 capacity CPU 且按时完成；
- 唤醒后保留 `prev_cpu`，减少不必要迁移；
- 高 util 任务在 thermal 允许时进入更高 capacity domain；
- 同一 cpufreq policy 的 CPU 共享频率变化；
- 运行迁移发生，但没有对应的 deadline 或 cache 指标退化。

### 需要继续排查的现象

- CPU-bound 关键段持续超时，同时仅能在低 capacity CPU 运行；
- 有空闲且允许的高 capacity CPU，目标线程却长时间 Runnable；
- 迁移点与 cache miss、wall time 尖峰稳定相关；
- policy 频率长期受限，且与 thermal 或省电状态一致；
- 前后台状态变化后，cpuset/UClamp/profile 没有按预期更新。

这些现象是调查入口，不是单凭一条就能定责的规则。

## 常见误区

### “CPU 编号越大，性能越高”

编号由固件和设备拓扑决定。用 capacity、policy 与实测识别 CPU 类型。

### “降低 nice 值会让线程自动去大核”

nice 主要改变 fair CPU 份额。选核还要看 util、capacity、EAS、UClamp、cpuset 和当前负载；更高权重不等于强制选择高 capacity CPU。

### “最高频率越高，CPU 就越快”

最高频率缺少 work-per-Hz、cache、内存与 thermal 信息。它只能描述一个维度。

### “迁移次数多，调度一定有问题”

迁移是负载均衡和异构调度的正常手段。只有迁移与 deadline、cache 或能耗退化稳定相关时，才有优化依据。

### “绑核可以修复所有选核问题”

affinity 会减少调度器选择，也可能把线程留在拥塞或降频 CPU。先验证根因，再以可回滚的实验评估。

### “全大核 SoC 不需要 EAS”

产品名称无法替代 kernel topology。只要 CPU capacity 或 Energy Model cost 存在差异，energy-aware placement 仍有分析价值。

## GPU、NPU 与 CPU 调度的边界

EAS、EEVDF 和 schedutil 处理 CPU task placement、CPU runqueue 与 CPU frequency。GPU 和 NPU 有各自的队列、driver、devfreq/固件调度与功耗域，不能称为由 CPU EAS “协同调度”。

任务卸载仍会在 CPU 上产生准备、Binder/HAL 调用、command submission、同步 fence 和结果处理。分析异构计算时可按下面的依赖检查：

```text
CPU 准备与提交
    → GPU/NPU 队列等待与执行
    → fence / callback 唤醒 CPU
    → CPU 后处理
```

若 CPU 长时间睡眠等待 fence，调整 CPU affinity 无法缩短 accelerator execution；若提交线程长时间 Runnable 或 CPU-bound，则回到 CPU 调度证据链。GPU/NPU 的频率、队列和利用率应使用对应数据源分析。

## 版本演进与当前边界

| 时期 | 变化 | 分析用途 |
| --- | --- | --- |
| 2011 起 | Arm big.LITTLE 与早期 cluster/switcher 模型 | 解释异构 CPU 的由来 |
| Linux 4.7 起 | schedutil 进入主线 | 解释调度器利用率驱动 DVFS |
| Linux 5.0 起 | EAS 进入主线 | 解释异构 CPU 的 wake-up placement |
| Android 9 起 | Android 设备广泛采用 EAS/schedutil，但 vendor 实现各异 | 只作历史范围，不假定所有设备一致 |
| Android 17 / API 37 | AOSP `android-17.0.0_r1` | task profile、UClamp、Power HAL/ADPF 控制面 |
| Android 17 kernel | `android17-6.18-2026-06_r6` | capacity-aware scheduling、EAS、schedutil、thermal pressure 与 sched_ext 接口 |

## 源码索引与参考资料

相关公共源码结论可从以下入口复核：

- kernel `Documentation/scheduler/sched-capacity.rst`；
- kernel `Documentation/scheduler/sched-energy.rst`；
- kernel `Documentation/scheduler/schedutil.rst`；
- kernel `kernel/sched/fair.c`：`util_fits_cpu()`、`find_energy_efficient_cpu()`、misfit/load-balance 路径；
- kernel `kernel/sched/cpufreq_schedutil.c`：`sugov_get_util()`、`sugov_effective_cpu_perf()`、I/O-wait boost；
- Android `system/core/libprocessgroup/profiles/task_profiles.json`；
- Perfetto `linux.cpu.frequency`、`sched_slice` 与 `thread_state`。

参考链接：

- [Linux Capacity Aware Scheduling](https://docs.kernel.org/scheduler/sched-capacity.html)
- [Linux Energy Aware Scheduling](https://docs.kernel.org/scheduler/sched-energy.html)
- [Linux schedutil](https://docs.kernel.org/scheduler/schedutil.html)
- [Arm big.LITTLE](https://developer.arm.com/Architectures/big.LITTLE)
- [Perfetto CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Android UClamp](https://source.android.com/docs/core/perf/uclamp)
