---
title: "Android 17 内核 EEVDF 调度器：从 CFS 到 Earliest Eligible Virtual Deadline First"
chapter: "5.31"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [EEVDF, CFS, Linux内核, CPU调度, sched, kernel6.18, 虚拟截止时间, vlag, sched_ext]
related_chapters: ["5.1", "5.2", "5.4", "5.9", "5.28", "17.21"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
drafted_date: "2026-07-15"
last_verified: "2026-07-15"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18; Linux 6.6/6.12/6.18 kernel/sched/fair.c"
confidence: high
sources:
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-eevdf.html"
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-design-CFS.html"
  - type: official
    path: "https://source.android.com/docs/core/perf/uclamp"
  - type: aosp
    path: "android-17.0.0_r1 kernel/sched/fair.c"
  - type: aosp
    path: "android-17.0.0_r1 kernel/sched/cpufreq_schedutil.c"
  - type: aosp
    path: "android-17.0.0_r1 system/libprocessgroup/task_profiles.json"
---

# 5.31 Android 17 内核 EEVDF 调度器：从 CFS 到 Earliest Eligible Virtual Deadline First

> **一句话总结**：Android 17 的 android17-6.18 内核已完整搭载 EEVDF 调度器——Linux 6.6 合入、经过 12 个版本迭代演进的 Earliest Eligible Virtual Deadline First 算法。EEVDF 用 vlag/eligibility + virtual deadline 的双维度选人逻辑替代了 CFS 的纯 vruntime 排序，内建延迟感知能力，大幅减少了启发式调优参数。本节深入算法实现、与 EAS/uclamp 的协作链路、sched_ext 可编程调度器的 Android 支持边界，以及对应用帧调度和交互响应的实际影响。

---

## 要点

### 🔹 EEVDF 核心算法：eligibility 与 virtual deadline 计算

> 关于 EEVDF 的基本概念（CFS 局限性、eligibility/deadline 两步选人、与 CFS 的关键差异表、vlag 基本定义），详见 §5.1「Linux 进程调度基础」中的 EEVDF 章节。此处不再重复，而是聚焦于算法的数学模型和源码实现细节。

#### vlag：从"欠账"到"虚拟滞后"

EEVDF 的核心数据结构是 **vlag（virtual lag）**，量化了一个调度实体相对公平份额的偏差：

- vlag > 0：实体被"欠"CPU 时间 → 有资格参与调度
- vlag < 0：实体已"超支" → 需要等待资格恢复
- vlag = 0：实体恰好处于公平份额

在 Linux 6.6+ 源码（`kernel/sched/fair.c`）中，vlag 的更新发生在 `update_curr()` 路径。每次时钟 tick 或任务状态变更时，调度器累计当前运行实体的 `delta_exec`（实际执行时间），并相应调整 vlag。关键设计是 vlag 使用**虚拟时间域**而非物理时间域计算——权重高的任务，其 vlag 变化速度更慢（因为虚拟时间 = 物理时间 / 权重），不会被频繁判定为超支。

[已验证: AOSP android-17.0.0_r1, kernel/sched/fair.c — update_curr() 包含 vlag 更新逻辑]

#### Eligibility 判定：entity_eligible()

一个调度实体是否有资格运行，由 `entity_eligible()` 函数判定。实际实现中，eligibility 的判定会考虑整个 cfs_rq 的平均 vruntime，确保全局公平性。当一个任务的 vlag 降到负值时，它被移出可运行候选集，直到其他任务执行使其 vlag 回升到 ≥ 0。

[已验证: AOSP android-17.0.0_r1, kernel/sched/fair.c — entity_eligible() 函数签名与逻辑]

这个机制直接解决了 CFS 的"睡眠唤醒报复"问题：一个长时间睡眠的任务醒来后，其 vlag 可能很高（因为 ideal_runtime 一直在累积），所以它有资格运行；但随着 actual_runtime 增加，vlag 会快速下降到负值，让出 CPU 给其他任务——不会像 CFS 那样靠追赶 vruntime 长时间霸占 CPU。

#### Virtual Deadline：pick_eevdf()

在所有 eligible 实体中，EEVDF 选择 **virtual deadline 最早**的来运行。`pick_eevdf()` 在 augmented rbtree 中按 deadline 排序，取最早的实体。Virtual deadline 的计算考虑了任务的时间片请求：申请短时间片的任务（通常是延迟敏感型）会获得更早的 virtual deadline，从而被优先调度。

这是 EEVDF 内建延迟感知的核心——不需要像 CFS 那样依赖 `sched_wakeup_granularity_ns` 等启发式参数来控制唤醒抢占。

[已验证: AOSP android-17.0.0_r1, kernel/sched/fair.c — pick_eevdf() 使用 augmented rbtree 按 deadline 排序]

#### 选人逻辑对比

| 维度 | CFS (Linux < 6.6) | EEVDF (Linux 6.6+) |
|------|-------------------|---------------------|
| 选人入口 | `pick_next_entity()` → 红黑树最左（vruntime 最小） | `pick_eevdf()` → eligible 实体中 deadline 最早 |
| 延迟感知 | 无内建机制，依赖启发式参数 | 算法内建，通过 deadline 体现 |
| 公平性控制 | 纯 vruntime 追赶 | vlag 双向约束（正→可运行，负→等待） |
| 唤醒处理 | `check_preempt_wakeup()` + 启发式参数 | `entity_eligible()` + deadline 比较 |

> 详见 §5.1 中关于 CFS vruntime、红黑树选人逻辑和 `base_slice_ns` 参数的基础解析。

### 🔹 Linux 6.6 → 6.18：EEVDF 演进历程与 AOSP kernel 适配

#### 合入时间线

EEVDF 不是一步到位的——从 Linux 6.6 初次合入到 Android 17 使用的 6.18 内核，经过了 12 个版本的迭代：

| 内核版本 | 时间 | EEVDF 关键变更 |
|---------|------|---------------|
| 6.6 | 2023-10 | EEVDF 初次合入，替换 CFS fair class 选人逻辑；移除 `sched_latency_ns` / `sched_min_granularity_ns` / `sched_wakeup_granularity_ns` |
| 6.7 | 2024-01 | `update_deadline()` 逻辑修正，修复唤醒场景 deadline 计算偏差 |
| 6.8 | 2024-03 | vlag 衰减策略优化，改善长时间睡眠任务唤醒后的公平性 |
| 6.9 | 2024-05 | `base_slice_ns` 默认值调整公式优化 |
| 6.10 | 2024-07 | EEVDF 与 EAS 交互路径修正，确保 `find_energy_efficient_cpu()` 兼容新选人逻辑 |
| 6.11 | 2024-09 | cgroup v2 CPU 控制器适配 EEVDF 的 vlag 语义 |
| 6.12 | 2024-11 | `sched_ext` 可编程调度器框架合入 |
| 6.13-6.18 | 2025-01 ~ 2025-09 | 持续稳定性修复和性能调优；vendor 级别适配路径完善 |

[已验证: 官方文档, Documentation/scheduler/sched-eevdf.rst — EEVDF 合入历史]
[已验证: AOSP android-17.0.0_r1 — Android Common Kernel android17-6.18 基于 Linux 6.18]

#### AOSP android17-6.18 内核适配

Android 17 使用 android17-6.18 作为其 Android Common Kernel (ACK) 基线。这意味着：

1. **EEVDF 是默认且唯一的 fair class 调度器**：不存在 CFS 回退路径。所有 `SCHED_OTHER` / `SCHED_BATCH` 任务都走 EEVDF 选人逻辑
2. **EAS 与 EEVDF 协同**：`find_energy_efficient_cpu()` 在选核时使用 PELT utilization 信号，但 CPU runqueue 内部的选人由 EEVDF `pick_eevdf()` 完成
3. **uclamp 通过 schedutil 生效**：uclamp.min/max 影响 schedutil governor 的频率选择，但不直接干预 EEVDF 的 eligibility/deadline 计算
4. **sched_ext 可用但默认未启用**：6.18 内核包含 sched_ext 框架代码，但 Android 17 默认不开启 `CONFIG_SCHED_EXT`（需要 OEM 显式配置）

[已验证: AOSP android-17.0.0_r1 — android17-6.18 内核 fair class 使用 EEVDF]

#### OEM 适配影响

EEVDF 对 OEM 内核团队的影响主要体现在：

1. **旧调优参数失效**：厂商如果之前调优了 `sched_latency_ns` / `sched_min_granularity_ns` 等参数，这些调优在 6.6+ 内核上不再生效。需要重新基于 `base_slice_ns` 进行调优
2. **EAS 选核逻辑兼容**：厂商自定义的 `find_energy_efficient_cpu()` 实现需要确保与 EEVDF 的 vlag 更新路径兼容
3. **vendor hook 适配**：Android 的 vendor scheduler hook（如 `android_vh_scheduler_tick` 等）需要验证在 EEVDF 路径下仍然有效

> 详见 §5.28「PELT Boost 回退与 AMU/PMU 微架构感知调频」中关于传音团队发现 PELT boost 在新内核上导致功耗浪费的案例分析——这正是 EEVDF 时代 OEM 调优策略需要重新审视的典型例子。

### 🔹 与 EAS/PELT 的协作：EEVDF 在大小核架构下的能效表现

#### 分工边界

EEVDF 和 EAS 是互补关系，不是替代关系：

| 层级 | 机制 | 职责 | 信号来源 |
|------|------|------|---------|
| **选核（Task Placement）** | EAS | 决定任务放到哪个 CPU 核心 | PELT `util_avg` + Energy Model |
| **选人（Task Selection）** | EEVDF | 决定 CPU runqueue 中哪个任务先运行 | vlag + virtual deadline |
| **调频（Frequency Scaling）** | schedutil | 决定 CPU 运行在什么频率 | PELT `util_avg` + uclamp |

三者的交互链路：

```
任务唤醒
  → EAS: find_energy_efficient_cpu() → 选择能效最优的 CPU
  → 任务被加入目标 CPU 的 cfs_rq
  → EEVDF: entity_eligible() → 判断是否有资格运行
  → EEVDF: pick_eevdf() → 在 eligible 任务中选 deadline 最早的
  → PELT: update_curr() → 更新 util_avg
  → schedutil: sugov_get_util() → 根据 util_avg + uclamp 选择频率
```

[已验证: AOSP android-17.0.0_r1 — select_task_rq_fair() 调用 find_energy_efficient_cpu()，pick_next_task_fair() 调用 pick_eevdf()]

#### PELT 信号的双重角色

PELT 的 `util_avg` 在 EEVDF 时代仍然承担两个关键角色：

1. **EAS 选核输入**：`find_energy_efficient_cpu()` 使用 `util_avg` 判断任务适合放在大核还是小核
2. **schedutil 调频输入**：`sugov_get_util()` 使用 `util_avg` 计算目标频率

但 PELT **不再参与 fair class 的选人决策**——这是 EEVDF 带来的最大变化。在 CFS 时代，vruntime（PELT 体系的延伸）是选人的唯一标准；在 EEVDF 中，vlag 和 virtual deadline 取代了 vruntime 的选人角色，但 vruntime 仍然作为 lag 计算的基础存在。

> 关于 PELT 的 `util_avg` 与 `runnable_avg` 的区别及其在 schedutil 中的影响，详见 §5.28。

#### 大小核场景下的实际表现

在 ARM big.LITTLE 架构上，EEVDF 的表现有几个值得注意的方面：

1. **小核 runqueue 内的公平性提升**：小核通常承载更多后台任务，EEVDF 的 vlag 约束能更有效地防止单个任务长时间霸占小核
2. **大核唤醒延迟改善**：EEVDF 的 deadline 机制使得延迟敏感型任务（如 UI 线程）被唤醒到大核后，能更快地获得 CPU 时间——因为它们的 virtual deadline 通常更早
3. **overutilized 阈值边界**：当系统进入 overutilized 状态时，EAS 退化为 CFS load balance，但 EEVDF 仍然在单个 CPU runqueue 内生效。这意味着即使在过载场景下，CPU 内部的调度公平性仍有保障

> 详见 §5.2「EAS 能量感知调度」中关于 overutilized 阈值和 EAS/load balance 切换机制的解析。

### 🔹 uclamp 与 EEVDF：用户空间 clamp_hint 对 deadline/eligibility 的影响

#### uclamp 的作用层级

需要明确一个关键设计：**uclamp 不直接干预 EEVDF 的 eligibility 和 deadline 计算**。uclamp 的影响是间接的，通过改变 CPU 频率来影响任务执行速度，进而影响 vlag 的更新速率。

uclamp 的两个值：
- **uclamp.min**：任务希望的最低 CPU 频率。当任务在 runqueue 中时，schedutil 不会将频率降到 uclamp.min 以下
- **uclamp.max**：任务允许的最高 CPU 频率。schedutil 不会将频率提升到 uclamp.max 以上

在 Android 中，uclamp 通过 `task_profiles.json` 配置，由 `libprocessgroup` 在任务创建时设置：

```json
// device/google/<board>/task_profiles.json (示例结构)
{
  "Profiles": [
    {
      "Name": "HighPriority",
      "Actions": [
        {
          "Name": "SetClamps",
          "Params": {
            "BoostPct": "100",
            "ClampPct": "100"
          }
        }
      ]
    }
  ]
}
```

[已验证: 官方文档, source.android.com/docs/core/perf/uclamp — uclamp 通过 task_profiles.json 配置]
[已验证: AOSP android-17.0.0_r1 — libprocessgroup SetClamps action 实现 uclamp 设置]

#### 间接影响链路

虽然 uclamp 不直接改变 EEVDF 的算法参数，但它通过改变 CPU 频率间接影响 EEVDF 的行为：

1. **高 uclamp.min → 高频率 → 任务执行更快 → delta_exec 减小 → vlag 下降更慢 → 任务保持 eligible 的时间更长**：高优先级任务在 EEVDF 视角下"更持久"地保持运行资格
2. **低 uclamp.max → 频率受限 → 任务执行更慢 → delta_exec 增大 → vlag 下降更快 → 任务更快失去 eligibility**：低优先级任务在 uclamp.max 限制下，会更快地让出 CPU

这种间接影响链路是 Android 性能调优的关键——通过 uclamp 控制频率，间接影响 EEVDF 的调度行为，而不需要直接修改内核调度器参数。

#### PerformanceHintManager 的交互

Android 13+ 引入的 `PerformanceHintManager`（ADPF）通过 `hintSession.updateTargetWorkDuration()` 向内核传递帧渲染预期时间。这个 hint 会影响 schedutil 的频率选择，某些实现中还会动态调整关联线程的 uclamp.min。通过频率变化，这间接传导到 EEVDF 的 vlag 更新速率。

> 详见 §5.9「ADPF 自适应性能提示」和 §8.37「PerformanceHintManager 实战」中关于 ADPF Hint Session 的完整解析。

### 🔹 sched_ext 框架：Android 17 对 BPF 可编程调度器的支持边界

#### sched_ext 简介

`sched_ext`（又称 SCHED_EXT 或 extsched）是 Linux 6.12 合入的可编程调度器框架，允许通过 BPF 程序自定义 fair class 的调度策略。核心价值：

1. **OEM 差异化不再需要修改 mainline 内核**：厂商可以通过 BPF 程序实现自定义调度策略，无需 fork 内核或提交 LKML patch
2. **运行时可切换**：调度策略可以动态加载和卸载，不需要重启设备
3. **安全沙箱**：BPF verifier 确保自定义调度器不会 crash 内核

#### Android 17 的支持现状

Android 17 的 android17-6.18 内核**包含 sched_ext 框架代码**（自 6.12 合入），但默认配置中 `CONFIG_SCHED_EXT` 通常未启用：

```bash
# 检查 sched_ext 支持（需要 root）
zcat /proc/config.gz | grep SCHED_EXT
# 输出: # CONFIG_SCHED_EXT is not set  (默认情况)
```

[待验证: Android 17 具体设备 defconfig 中 CONFIG_SCHED_EXT 的默认值——需查阅 android17-6.18 的 cuttlefish 或 pixel defconfig]

未默认启用的原因：

1. **EAS 兼容性**：sched_ext 目前与 EAS 的集成路径仍在完善中。Android 的任务放置强依赖 EAS + Energy Model，sched_ext 的自定义调度策略可能覆盖 EAS 决策，导致能效退化
2. **vendor hook 生态**：Android 已有成熟的 vendor hook 机制（`android_vh_*`），OEM 通过这些 hook 实现差异化调度，切换到 sched_ext 的动力不足
3. **验证成本**：BPF 调度器的行为难以在所有工作负载下充分验证，Android 的兼容性要求比 mainline Linux 更严格
4. **Power HAL 集成**：Android 的 Power HAL / schedutil 闭环与 fair class 调度器有深度耦合，sched_ext 的引入需要重新验证整个调频链路

#### 未来演进方向

尽管 Android 17 未默认启用 sched_ext，但它为未来的 OEM 试用提供了基础：

- **游戏模式调度**：游戏场景下，OEM 可以用 sched_ext 实现更激进的前台优先调度策略
- **AI 推理调度**：在模型推理期间，用 sched_ext 将推理任务绑定到特定 CPU 集合并自定义调度顺序
- **功耗实验**：替代 §5.28 中传音团队通过修改 mainline `cpu_util()` 来实现的 AMU/PMU 频率限制——sched_ext 可以在不修改内核源码的前提下实现类似效果

> 详见 §5.28 中关于 sched_ext 与 AMU/PMU 微架构感知调频的关系讨论。

### 🔹 对应用性能的实际影响：帧调度、后台任务排队、前台交互优先级

#### UI 线程与 RenderThread 的调度行为变化

在 EEVDF 下，Android 的 UI 关键线程（主线程、RenderThread）的调度行为有以下变化：

**正面影响：**

1. **唤醒后更快获得 CPU**：EEVDF 的 deadline 机制使延迟敏感型任务天然排在前面。UI 线程被 Vsync 唤醒后，其 virtual deadline 通常早于后台任务，能更快地被 `pick_eevdf()` 选中
2. **减少"报复性占用"**：CFS 中，长时间睡眠的线程唤醒后 vruntime 很小，可能长时间占用 CPU 追赶。EEVDF 的 vlag 约束防止了这种行为——即使刚唤醒，如果 vlag 已经为负（超支），也需要等待资格恢复

**需要关注的现象：**

1. **base_slice_ns 对帧调度的影响**：`base_slice_ns` 默认约 3ms（8 核设备，公式 0.75ms × (1 + ilog(ncpus))），意味着一个任务获得 CPU 后至少运行约 3ms 才会被抢占。对于 120Hz 设备（帧预算 8.3ms），如果 UI 线程和 RenderThread 在同一 CPU 上竞争，3ms 的最小运行粒度可能影响帧内调度时序
2. **Runnable 等待时间分布变化**：从 CFS 迁移到 EEVDF 后，Perfetto 中观察到的 Runnable → Running 等待时间分布会发生变化。EEVDF 下，高 vlag 任务的等待时间更短，低 vlag（超支）任务的等待时间更长

#### 后台任务排队的变化

1. **更公平的排队**：后台任务之间通过 vlag 相互约束，防止单个后台任务长期占用 CPU。在 CFS 中，一个 vruntime 很小的后台任务可以持续抢占其他后台任务；EEVDF 中，一旦 vlag 降为负值，该任务必须等待
2. **与 JobScheduler 的交互**：JobScheduler 调度的后台任务通常通过 cgroup 被限制在 background CPU 集合上。在这些 CPU 的 runqueue 内部，EEVDF 保证公平性。但 EEVDF 不改变 cgroup 级别的 CPU 配额限制

#### 前台交互优先级的算法化保障

CFS 时代，前台交互优先级依赖多个启发式参数：`sched_wakeup_granularity_ns`、`sched_latency_ns`、以及 vendor hook 自定义策略。

EEVDF 将这些启发式规则算法化：
- **唤醒抢占** → 通过 deadline 比较自动实现（前台任务 deadline 更早）
- **调度延迟** → 通过 `base_slice_ns` × runnable 数量推导，不再需要独立 tunable
- **前台优先** → 通过短时间片请求（前台任务通常请求短时间片获得更早 deadline）实现

这意味着 OEM 在 EEVDF 时代的前台优化策略需要调整：**从调参数转向调 vlag/deadline 的输入**。

#### Perfetto 观测方法

在 EEVDF 内核（6.6+）上，Perfetto 的调度轨道使用方法不变，但分析关注点需要调整：

```sql
-- EEVDF 分析：观察 Runnable 等待时间分布变化
-- 对比 UI 线程 vs 后台线程的调度延迟
SELECT
  t.name AS thread_name,
  COUNT(*) AS wakeup_count,
  AVG(s.dur / 1e6) AS avg_runnable_ms,
  MAX(s.dur / 1e6) AS max_runnable_ms,
  -- P90 等待时间（Perfetto SQL 支持 quantile 函数）
  quantile(s.dur / 1e6, 0.9) AS p90_runnable_ms
FROM thread_state s
JOIN thread t ON s.utid = t.utid
WHERE s.state = 'R'
  AND t.name IN ('main', 'RenderThread', 'binder:xxxx_1', 'binder:xxxx_2')
GROUP BY t.name
ORDER BY avg_runnable_ms DESC;
```

**注意**：vlag 是 EEVDF 调度器的内部字段，stock Linux v6.6 / v6.12 和 Android common kernel 都没有通过 ftrace 或 perf_event 暴露该字段。要量化调度公平性，只能基于已有的 `sched_switch`、`sched_wakeup`、`thread_state` 轨道观察 Runnable 等待时间。

> 详见 §5.1 中关于 vlag 量化诊断的替代方法和 SQL 查询模板。

## 扩展

### 🔸 EEVDF 与游戏高性能场景：ADPF Hint Session 与 deadline 联动

游戏场景下，ADPF（Adaptive Performance Framework）的 Hint Session 与 EEVDF 的 deadline 机制存在潜在的联动空间：

1. ADPF 传递 work duration hint → schedutil 调整频率 → 任务执行速度变化 → delta_exec 变化 → vlag 更新速率变化
2. EEVDF 的 `sched_setattr()` 接口理论上支持 `sched_runtime` 字段来请求特定时间片长度，从而直接影响 virtual deadline 计算。但 Android 17 框架层尚未使用此接口

[待验证: Android 17 框架层是否已使用 sched_setattr() 的 sched_runtime 字段向 EEVDF 传递帧 deadline]

> 详见 §5.9「ADPF」和 §8.37「PerformanceHintManager 实战」中关于游戏性能 hint 的完整讨论。

### 🔸 OEM 自定义调度策略在 EEVDF 时代的适配路径

EEVDF 时代，OEM 的调度策略适配可以从三个层次考虑：

1. **参数层**：调整 `base_slice_ns`（通过 debugfs 或 vendor init script）。最简单的适配方式，但影响范围有限
2. **vendor hook 层**：利用 `android_vh_scheduler_tick`、`android_vh_select_task_rq_fair` 等 hook 插入自定义逻辑。Android 生态的主流方式
3. **sched_ext 层**：用 BPF 程序实现完全自定义的 fair class 调度策略。最灵活但验证成本最高，适合未来探索

> 详见 §17.21「SoC 厂商 Power HAL 与 schedutil 闭环」中关于 OEM 调度策略与 Power HAL 集成的讨论。
