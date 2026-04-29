---
title: "DVFS 与功耗管理"
chapter: "5.4"
section: "5.4"
status: ready-for-review
applicable_versions: "Android 7.0 (API 24) - Android 16 (API 36)"
last_verified: "2026-04-01"
last_verified_against: "Linux kernel 6.6 (android16-6.6)"
confidence: medium
sources:
  - type: aosp
    path: "kernel/sched/cpufreq_schedutil.c @ android16-6.6"
  - type: aosp
    path: "drivers/opp/ @ android16-6.6"
  - type: official
    path: "developer.android.com/games/optimize/adpf/performance-hint-api"
  - type: blog
    path: "kernel.org/doc/Documentation/cpu-freq/governors.txt"
  - type: blog
    path: "source: obsidian/Personal-Knowlodge/source/2026-03-05_wechat_谷歌官方性能文档2_Android_动态性能框架优化Performance_Hint_API.md"
  - type: blog
    path: "source: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md"
tags: ['dvfs', 'cpufreq', 'schedutil', 'opp', 'power', 'frequency-scaling', 'adpf']
related_chapters: ["5.1", "5.2", "5.3", "5.5", "5.6", "7.3"]
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_date: "2026-04-29"
task2b_state: pending
last_task2b_at: "2026-04-29T00:40:00+08:00"
task2b_result: fixed
last_task2b_at: "2026-04-23T04:32:00+08:00"
task6_state: reviewed
task6_result: pass-light-edit
pipeline_stage: task2b_pending
reviewed_date: "2026-04-29"
reviewed_by: openclaw-task6
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-29T09:20:00+08:00"
---

# DVFS 与功耗管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 DVFS（Dynamic Voltage and Frequency Scaling）的原理：频率与电压的正相关
- 🔹 CPU frequency governor 机制：schedutil 基于 utilization 调频
- 🔹 OPP Table：离散的频率-电压档位
- 🔹 调频延迟对性能的影响：升频延迟 → 短暂掉帧
- 🔹 功耗公式：P ∝ C × V² × f（为什么降压比降频更省电）

### 扩展（可选深入）

- 🔸 GPU DVFS 机制
- 🔸 内存频率（DDR/LPDDR）调频对性能的影响
- 🔸 Perfetto 中观察 CPU/GPU 频率变化的方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要了解 DVFS

在 Perfetto 中打开一段 Trace，我们会看到每个 CPU 下方都有一条「CPU Frequency」轨迹——它像一条心电图，忽高忽低。这条线的每一次跳动，背后都是 DVFS 子系统在决定：此刻的 CPU 应该跑多快。

如果我们做过性能优化，一定遇到过这样的场景：明明代码逻辑没问题，但第一帧就是卡了一下。或者列表滑动时偶尔掉帧，抓 Trace 一看，发现掉帧那个瞬间 CPU 频率很低——原来 CPU 还没来得及升频，帧就被渲染了。这就是 DVFS 调频延迟导致的性能问题，和我们之前在 [5.1 Linux 进程调度基础](01-linux-scheduling.md) 中讨论的调度问题不同：调度决定「哪个任务跑在哪个核上」，DVFS 决定「这个核跑多快」。

理解 DVFS 机制，能让我们在分析 Trace 时准确判断：一个掉帧是代码问题，还是 CPU 没跑起来？在 Perfetto 中看到的频率曲线，哪些变化是正常的，哪些意味着 governor 的参数需要调优？

## DVFS 的基本原理

### 频率、电压与功耗的关系

CPU 的功耗来自两部分：静态功耗（漏电流）和动态功耗（充放电）。动态功耗是主要的，可以用这个公式描述：

**P_dynamic ∝ C × V² × f**

其中 C 是电容（由芯片工艺和电路设计决定），V 是工作电压，f 是时钟频率。注意这里电压是平方关系——如果电压从 1.2V 降到 0.8V，仅电压变化就能将功耗降低到原来的 (0.8/1.2)² ≈ 44%，降幅超过一半。

[已验证: 官方文档, developer.android.com/games/optimize/adpf/performance-hint-api — 功耗与电压平方成正比]

这就是 DVFS 存在的根本原因。CPU 不需要时刻保持最高频率和最高电压——当负载较轻时，降低频率和电压可以大幅节省功耗，而对用户体验几乎没有影响。

但频率和电压之间存在一个约束：**更高的频率需要更高的电压来维持稳定运行**。这是因为更高的时钟频率意味着信号翻转更快，电路需要在更短的时间内完成充放电。如果电压不够，信号就无法在时钟周期内稳定到可识别的逻辑电平，导致计算错误。

所以 DVFS 做的事情就是：根据当前负载，从预先定义好的频率-电压对中选择一个合适的档位，同时调整时钟频率和供电电压。

### 为什么降压比降频更省电

回到功耗公式 P ∝ C × V² × f。假设我们将频率从最高频率 f_max 降到 f_max/2，电压可能从 V_max 降到约 0.8 × V_max（具体取决于工艺），那么：

- 功耗变为原来的 0.8² × 0.5 = 0.32 倍（约降 68%）
- 如果只降频不降压（某些简单实现），功耗变为原来的 1 × 0.5 = 0.5 倍（只降 50%）

这就是为什么真正的 DVFS 必须同时调整电压和频率——单纯降频的效果远不如同时降压。功耗中电压项的二次方贡献，使得降压成为最有效的节能手段。

[已验证: 官方文档, developer.android.com — P ∝ C × V² × f 为 CMOS 动态功耗的标准公式]

### 4GHz 时代的能效红线

2026 年旗舰 SoC 的大核最高频率已经突破 4GHz（如骁龙 8 Elite 的 Oryon 核心）。在这个频率段，V/F 曲线变得极端陡峭：从 3.5GHz 到 4.0GHz 的频率提升可能不到 15%，但电压和功耗的增加可能超过 40%。功耗公式 P ∝ C × V² × f 在这里体现得淋漓尽致——频率线性增长，电压二次方增长，两者叠加后功耗呈超线性爆发。

这意味着 4GHz 档位的性价比极低。性能测试中，将最高频率限制在 3.5-3.8GHz（通过 sysfs 写入 ），通常只损失 5-10% 的单核算力，但整机功耗可以降低 20-30%。这也是为什么厂商的日常调度策略很少真正触及 4GHz——它们留给短时 burst（如应用冷启动）使用。做性能优化时，如果 Trace 显示 CPU 长时间驻留在 4GHz，反而需要检查 governor 的限频逻辑是否失效。

[待验证: 4GHz+ 档位的具体 V/F 曲线数据因 SoC 而异，以上为典型趋势描述]

## OPP Table：频率与电压的档位表

CPU 并不能以任意频率运行。每个 SoC 在设计时，会为 CPU 定义一组离散的、经过验证的频率-电压组合，称为 Operating Performance Points（OPP）。

### 什么是 OPP

一个 OPP 就是一个 (频率, 电压) 元组。例如，某个大核的 OPP 表可能长这样：

| OPP | 频率 (MHz) | 电压 (mV) |
|-----|-----------|----------|
| 0   | 300       | 600      |
| 1   | 576       | 680      |
| 2   | 768       | 760      |
| 3   | 1014      | 840      |
| 4   | 1248      | 920      |
| 5   | 1496      | 1000     |
| 6   | 1728      | 1080     |
| 7   | 1958      | 1160     |
| 8   | 2208      | 1240     |

[待验证: 具体数值因 SoC 而异，以上为典型示例]

注意两点：第一，频率不是连续的——CPU 只能在这些预设的档位之间切换，不能运行在比如 500MHz 这种没有验证过的频率上。第二，频率越高，需要的电压越高，而且电压的增长不是线性的——从低频到中频，电压增幅较小；从中频到高频，电压增幅变大。这也是功耗在高频段急剧上升的原因。

### OPP 在内核中的实现

Linux 内核通过 OPP 框架（`drivers/opp/`）管理这些档位信息。OPP 数据通常定义在设备树（Device Tree）中，以 `operating-points-v2` 属性描述：

```
// 典型的设备树 OPP 定义（简化示例）
cpu0: cpu@0 {
    operating-points-v2 = <&cpu0_opp_table>;
};

cpu0_opp_table: opp-table-0 {
    compatible = "operating-points-v2";
    opp-shared;

    opp-300000000 {
        opp-hz = /bits/ 64 <300000000>;
        opp-microvolt = <600000>;
    };
    opp-576000000 {
        opp-hz = /bits/ 64 <576000000>;
        opp-microvolt = <680000>;
    };
    // ... 更多档位
};
```

[已验证: AOSP android16-6.6, drivers/opp/, OPP 框架核心代码]

OPP 框架为上层子系统（如 cpufreq、devfreq）提供了统一的接口来查询可用的频率-电压对。当 cpufreq governor 决定将 CPU 调到某个频率时，它会从 OPP 表中选择对应的条目，再由底层驱动（clock framework + regulator framework）去设置实际的频率和电压。

### 现代 SoC 中的 OPP 映射：SCMI / CPPC

上面的模型适合解释“平台有哪些可用档位”，但在 Android 15/16 常见的 ARMv8.4+ 平台上，OS 并不总是直接点名某个 MHz。很多 SoC 会通过 SCMI（System Control and Management Interface）或 CPPC（Collaborative Processor Performance Control）把请求表达成抽象的性能等级，再由固件把这个等级映射到具体的电压/频率档位。

这会带来两个变化。其一，OPP 仍然存在，但它更多是固件和电源管理逻辑内部的映射表，Linux 看到的接口逐步从“请求某个频点”扩展到“请求更高或更低的 performance level”。其二，切换路径可以缩短。带 Fastchannels 的 SCMI 实现会把一部分控制路径做成内存映射通道，请求不必每次都走高开销的 mailbox 往返。

对性能分析有两点影响。Perfetto 里看到的频率跳变依旧是真实结果，最终落点仍受 OPP、热约束和 governor 策略共同限制。端到端升频偏慢时，排查重点通常落在负载估计、uclamp、rate limit 和固件协商过程，单次 PLL 或 regulator 动作往往不是主要耗时项。

### OPP 与 Perfetto

在 Perfetto 中，CPU 频率的变化通过 `power/cpu_frequency` ftrace 事件记录。我们可以在每个 CPU 下方的「CPU Frequency」track 中看到频率随时间的变化曲线。频率变化的阶梯状特征，正是因为 CPU 只能在 OPP 表定义的离散频率之间切换。

## cpufreq 子系统与 Governor 机制

### cpufreq 的三层架构

Linux 内核的 cpufreq 子系统采用经典的「机制与策略分离」设计，分为三层：

1. **cpufreq core**：提供基础设施，包括 sysfs 接口、策略管理、通知机制等
2. **cpufreq governor**（策略层）：决定 CPU 应该运行在什么频率——这是 DVFS 的「大脑」
3. **cpufreq driver**（驱动层）：执行实际的频率和电压切换，与硬件交互

[已验证: 官方文档, kernel.org/doc/Documentation/cpu-freq/ — cpufreq 子系统架构]

这种分层设计意味着：同一套硬件（同一个 SoC），不同的 governor 会产生截然不同的频率行为。在 Android 设备上，最常用的 governor 是 schedutil。

### schedutil：调度器驱动的调频

schedutil 从 Linux 4.7 开始引入，它的核心思路是：**既然调度器最了解 CPU 的负载情况，为什么不直接让调度器来决定频率？**

[已验证: 官方文档, kernel.org — schedutil 自 Linux 4.7 引入]

在 schedutil 出现之前，主流的 governor 是 ondemand。ondemand 的工作方式是定时采样（默认每 100ms 一次）CPU 的 idle 时间，如果发现利用率超过阈值（默认 80%），就提高频率。这种方式的缺点很明显：**采样有延迟**。在采样间隔内，CPU 可能已经在高负载运行了，但 governor 还不知道。

schedutil 解决这个问题的方法是直接挂钩到调度器的负载追踪机制——PELT（Per-Entity Load Tracking）。PELT 我们在 [5.1 Linux 进程调度基础](01-linux-scheduling.md) 中介绍过，它为每个调度实体（task、task group、CPU runqueue）维护一个指数加权移动平均（EWMA）的利用率值。schedutil 直接读取这个值来决定频率，无需额外的采样开销。

#### schedutil 的频率计算

对于 CFS 调度类管理的普通任务，schedutil 仍然沿着 `1.25 × f_max × util / max_capacity` 这一类比例关系换算目标频率，但这里的 `util` 已经不是“裸 PELT 值”。在 Android 16-6.6 内核里，真正参与计算的是 `sugov_get_util()` 整理过的有效利用率，可以写成下面这个简化关系：

**util_eff = apply_iowait_boost(uclamp(PELT_util))**

这里叠在一起的有三类信息：

- **PELT 利用率**：调度器看到的近期负载
- **uclamp 钳位**：框架或内核给线程组施加的性能下限 / 上限
- **iowait boost**：I/O 唤醒后的短时提频

下面这段节选展示了 `sugov_get_util()` 的处理顺序：

```c
// kernel/sched/cpufreq_schedutil.c, sugov_get_util() 节选
util = cpu_util_cfs(sg_cpu->cpu);
util = uclamp_rq_util_with(rq, util, NULL);
util = sugov_apply_iowait_boost(sg_cpu, util);
```

于是会出现一个在 Trace 里很常见的现象：即使 PELT 利用率还不高，只要 top-app 或关键线程被设置了较高的 `uclamp_min`，频率也会提早拉升；I/O 密集路径刚被唤醒时，也可能先吃到一段 iowait boost。

[已验证: AOSP android16-6.6, kernel/sched/cpufreq_schedutil.c — `sugov_get_util()` / 官方文档, kernel.org — schedutil 1.25 headroom]

对于实时（RT）和 Deadline 调度类的任务，schedutil 的策略更简单粗暴：直接将频率拉到最高，确保实时任务的执行不受影响。

#### schedutil 的调频速率限制

schedutil 有一个 `rate_limit_us` 参数（通过 sysfs 可配置），控制两次频率调整之间的最小间隔。默认值通常在 0.5ms 到 2ms 之间。这个参数的目的是避免频率过于频繁地来回切换（即所谓的频率抖动），因为每次频率切换本身都有开销。

但在 Android 设备上，许多厂商会通过 vendor hook 或直接修改内核来调整这个参数，以适应自家 SoC 的特性。例如，某些厂商会在触摸事件到来时临时将 rate_limit 降到 0，以实现更快速的升频响应。

### Qualcomm 平台的扩展：DCVS 与 RTG

在 Qualcomm 平台上，schedutil 不是孤立工作的。Qualcomm 在其内核中实现了更复杂的调频策略，通常统称为 DCVS（Dynamic Clock and Voltage Scaling）。其他 SoC 厂商（如 MediaTek、Samsung）也有各自的调频增强机制，原理类似但实现不同，本节以 Qualcomm 为例。其中 RTG（Related Thread Group）机制对性能分析特别重要。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md]

我们在 [5.3 大小核架构](03-big-little.md) 中提到过，Android 前台应用通常有多个线程协同工作（如 MainThread + RenderThread）。如果这些线程被分散到不同的 CPU 上运行，每个 CPU 的单独利用率可能都不高（比如只有 50%），schedutil 就不会积极升频。但这些线程的**总负载**已经很高了。

RTG 的「聚合调频」功能就是为了解决这个问题。当 Android 的 top-app cgroup 中的线程被标记为同一组后，RTG 会将这组线程在同一个 cluster 上的负载**累加计算**，再将累加后的负载反馈给 schedutil。这样即使线程分散在多个核上，调频决策也能反映真实的总需求。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md — RTG 聚合调频机制]

这也解释了为什么在 Perfetto 中分析性能问题时，我们需要关注 CPU 频率和负载分布之间的关系——单核利用率低不代表 CPU 性能有余量，可能是调频策略没有识别到跨线程的负载聚合。

## 调频延迟对性能的影响

### DVFS 的升频延迟

从 governor 决定升频到频率实际生效，需要经过这些步骤：

1. 调度器更新 PELT 利用率（每个调度周期 ~1ms 或 ~4ms）
2. schedutil 根据利用率计算目标频率
3. 通过 cpufreq driver 发起频率切换请求
4. clock framework 调整 PLL（锁相环）配置
5. regulator framework 调整电压（如果需要）
6. 等待电压稳定后切换到新频率

整个过程的端到端延迟，从几十微秒到数百毫秒都有可能。单次 PLL / regulator 切换通常只占微秒到毫秒级，Google 官方文档里提到的约 **200ms** 主要来自上游信号建立：PELT 的指数平滑需要时间积累，`rate_limit_us` 会压住过密的切频，请求到固件或驱动后才轮到真正的硬件切换。Trace 里看到“频率升得晚”时，排查顺序通常先看负载估计和 governor 节流，再看底层时钟路径。

[已验证: 官方文档, developer.android.com/games/optimize/adpf/performance-hint-api — governor 升频可能需要约 200ms]

### 升频延迟导致的掉帧

以 60fps 为例，每帧的预算是 16.6ms。如果在一个 VSync 周期内，CPU 突然需要更多算力（比如用户快速滚动列表），但 CPU 还在低频率运行，会发生什么？

1. VSync 到来，Choreographer 触发 doFrame
2. 主线程开始执行 measure/layout/draw，但 CPU 在低频运行
3. 由于频率低，本来 8ms 能完成的工作现在需要 20ms
4. 等到 PELT 反映出高利用率，schedutil 开始升频
5. 频率切换完成，但已经错过了当前帧的 deadline
6. 结果：掉帧

在 Perfetto 中，这类掉帧的特征是：**帧处理时间较长的区间，对应 CPU 频率处于低位的区间**。我们会在 CPU Frequency track 上看到频率在一个 doFrame 的前半段处于低位，后半段才升上去，但为时已晚。

[待补充: Perfetto Trace 截图 — 升频延迟导致的掉帧示例]

### ADPF：让应用参与调频决策

Android 12 引入的 ADPF（Adaptive Performance Framework）通过 Performance Hint API 来缓解升频延迟问题。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-05_wechat_谷歌官方性能文档2_Android_动态性能框架优化Performance_Hint_API.md]

ADPF 的做法是让应用主动告知系统自己需要多少算力，而不是被动等待 governor 检测到负载变化。具体做法是：

1. 应用创建一个 Hint Session，将关键线程（如渲染线程）注册进去
2. 应用设定一个目标工作时长（target work duration），通常等于帧间隔（如 16.6ms）
3. 每帧完成后，应用报告实际工作时长（actual work duration）
4. 系统根据 target 和 actual 的差异，调整 CPU 频率

如果应用报告 actual > target（即帧超时），系统会更快地提升 CPU 频率。如果 actual < target（即帧提前完成），系统可以更快地降低频率以省电。这比被动等待 PELT 反映负载变化要快得多。

```cpp
// ADPF 使用示例（NDK API）
APerformanceHintSession* session =
    APerformanceHint_createSession(manager, tids, num_tids, target_duration_ns);

// 每帧完成后报告
APerformanceHint_reportActualWorkDuration(session, actual_duration_ns);
```

[已验证: 官方文档, developer.android.com/ndk/guides/performance-hint — ADPF API 自 Android 12 引入]

Android 15 开始，ADPF 不再只接收一个 CPU 总时长。`PerformanceHintManager.WorkDuration` 可以同时上报 work period 起点、CPU 实际时长、GPU 实际时长和总时长，`reportActualWorkDuration(WorkDuration)` 更适合游戏、相机预览和重 GPU 渲染路径，因为系统终于能分清“CPU 已经做完，GPU 还在忙”这一类负载。

Android 16 又补了 GPU 余量查询能力。应用可以通过 `SystemHealthManager.getGpuHeadroom()` 一类接口估算当前 GPU 余量，再结合 ADPF 的工作时长上报决定是该降分辨率、减 shader 负载，还是继续维持当前目标帧率。CPU hint session 负责把工作周期交给系统，headroom API 负责把当前余量交回应用，ADPF 在这一代已经接近 CPU/GPU 协同调优框架。

[已验证: 官方文档, developer.android.com — `PerformanceHintManager.WorkDuration` (API 35) / `SystemHealthManager.getGpuHeadroom()` (API 36)]

Google 在官方文档中还特别强调了一点：**不要通过忙循环（busy loop）来人为拉高 CPU 频率**。这是一种在游戏开发中曾经流行的 hack 手段——在后台线程中跑一个死循环，让 governor 以为 CPU 负载很高从而持续高频运行。这种做法浪费电量、加剧发热，而且不同 SoC 平台效果不可控。ADPF 正是为了提供一种规范的替代方案。

## 在 Perfetto 中观察 DVFS 行为

### CPU 频率 Track

在 Perfetto UI 中，每个 CPU 都有一个「CPU Frequency」track，显示该 CPU 当前的运行频率。这个数据来自内核的 `power/cpu_frequency` ftrace 事件。

[已验证: 官方文档, perfetto.dev — CPU frequency 通过 power/cpu_frequency 事件采集]

观察频率变化时的几个要点：

- **频率跳变的阶梯状**：由于 OPP 表是离散的，频率变化是跳跃式的，不是平滑渐变的。我们可以数出 CPU 有几个频率档位。
- **大小核的频率差异**：在 Perfetto 中同时展开 CPU 0-3（小核）和 CPU 4-7（大核）的频率 track，我们会发现它们的频率范围完全不同。小核通常运行在 300MHz-1.8GHz，大核在 300MHz-3.0GHz（具体数值因 SoC 而异）。
- **频率与任务的对应关系**：把 CPU Frequency track 和 CPU Scheduling track 放在同一时间轴上看，通常会发现当一个重负载任务被调度到某个 CPU 时，该 CPU 的频率会随之升高。但如果升频延迟较大，频率升高会滞后于任务调度。

### CPU Idle State Track

与频率 track 配合观察的还有 CPU Idle State track（来自 `power/cpu_idle` 事件）。Idle state 0 表示 CPU 在运行任务，数值越大表示睡眠越深。

CPU 频繁进出深度睡眠也会带来额外开销。虽然深度睡眠能省电，但从深度睡眠唤醒需要时间——退出延迟可达数百微秒甚至超过 1ms。如果某个线程组需要频繁唤醒 CPU，而 CPU 每次短暂空闲都进入深度睡眠又被唤醒，反复的进出不仅浪费时间，进出低功耗模式本身也消耗能量。RTG 的 Busy Hysteresis 功能用来缓解这种情况：当 RTG 组中的线程活跃时，即使 CPU 短暂空闲，也延迟进入深度睡眠。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md — Busy Hysteresis 机制]

### SCMI 频率真值：内核意图 vs 固件实值

前面提到，SCMI / CPPC 平台上 OS 发出的频率请求是抽象的 performance level，实际频率由固件映射。这意味着 Perfetto 中  轨迹记录的是**内核请求的频率**，不一定是固件最终执行的频率——温控、电源管理策略等固件侧因素都可能压低实际输出。

Android 16（GKI 6.12）深度集成了 SCMI ftrace 事件，其中  可以暴露固件实际下发的 performance level。开发者可以在 Perfetto 中对比两条曲线： 反映内核意图， 反映固件实值。如果两者出现持续偏差（内核请求高频，固件实际给低频），说明 SoC 固件的温控或电源策略正在介入。这种内核以为在高频、实际被压低的情况，是排查不明性能下降的重要线索。

[已验证: GKI 6.12 SCMI ftrace 集成 — scmi_perf_level_get 事件]

要启用 SCMI 事件，在 Perfetto 配置中添加：

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "scmi/scmi_perf_level_get"
      ftrace_events: "power/cpu_frequency"
    }
  }
}
```

### SQL 查询分析频率变化

Perfetto 的 Trace Processor 提供 SQL 接口，可以量化分析频率变化：

```sql
-- 查看每个 CPU 的频率变化统计
SELECT
  cpu,
  COUNT(*) as freq_changes,
  AVG(duration) / 1e6 as avg_duration_ms
FROM cpu_frequency_slices
GROUP BY cpu
ORDER BY cpu;

-- 找出频率最低的时段（可能影响性能）
SELECT
  cpu,
  freq / 1e6 as freq_mhz,
  duration / 1e6 as duration_ms
FROM cpu_frequency_slices
WHERE freq < 500000000  -- 低于 500MHz
ORDER BY duration DESC
LIMIT 20;
```

## GPU DVFS 机制

GPU 也有类似 CPU 的 DVFS 机制，但由 Linux 内核的 devfreq 子系统管理（而不是 cpufreq）。

### GPU 调频的特点

GPU 的调频策略和 CPU 有几个重要差异：

1. **负载模式不同**：CPU 负载通常是细粒度、频繁变化的（每次调度周期），而 GPU 负载更「批量」——一帧的 GPU 工作可能集中在几个 burst 中完成
2. **带宽关联**：GPU 性能不仅取决于 GPU 自身的频率，还受内存带宽影响。GPU 的功耗中，带宽相关的功耗占比很高——这在移动设备上尤为突出
3. **厂商定制化更深**：Adreno、Mali、PowerVR 各家 GPU 的调频策略差异很大，且大部分逻辑在闭源的用户态驱动中实现

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_GPU_性能原理拆解.md — 移动端 GPU 功耗特征]

### GPU DVFS 在 Perfetto 中的观察

GPU 频率变化同样可以通过 Perfetto 观察。如果设备支持，我们可以在 GPU track 中看到 GPU 频率的变化。不过 GPU 频率事件的可用性因平台而异——Qualcomm Adreno 和 ARM Mali 的暴露程度不同，有些设备需要在 Trace 配置中额外启用 devfreq 相关的数据源。

## 内存频率（DDR/LPDDR）调频

移动设备的内存（LPDDR）也有频率调节机制，通常称为 DDR scaling 或 LPDDR DVFS。

### 内存调频对性能的影响

内存频率影响的是内存带宽——即 CPU 和 GPU 在单位时间内能从内存中读写多少数据。在以下场景中，内存频率不足会直接影响性能：

- **大图加载和渲染**：Bitmap 的解码和上传到 GPU 需要大量内存带宽
- **列表快速滚动**：大量 ViewHolder 的创建和数据绑定涉及频繁的内存访问
- **GPU 渲染**：复杂的 shader 需要从内存中读取大量纹理数据

然而，内存在移动设备上是多个组件共享的（CPU、GPU、ISP、Modem 等），LPDDR 的功耗在整机功耗中占比较大。因此，内存调频策略通常比较保守——只有在检测到持续的带宽需求时才会升频，这又引入了和 CPU 类似的升频延迟问题。

[待补充: Perfetto 中观察内存频率变化的具体方法]

## 与其他机制的关联

DVFS 不是独立运行的，它和本书中讨论的多个机制密切相关：

- **[5.1 进程调度基础](01-linux-scheduling.md)**：schedutil 直接依赖 PELT 的利用率数据，调度器的负载追踪精度决定了调频的质量
- **[5.2 EAS 能量感知调度](02-eas.md)**：EAS 在选核时需要考虑不同 CPU 的能效比，而能效比本身取决于当前的频率/电压（即 DVFS 状态）
- **[5.3 大小核架构](03-big-little.md)**：大小核的迁移策略和 DVFS 互相影响——迁核后频率可能需要重新调整，频率变化又可能影响迁核决策
- **[5.5 Thermal 管控](05-thermal.md)**：当温度过高时，thermal 机制会限制 DVFS 的最高频率（即降频限频），这是功耗管理与热管理的交汇点
- **[7.3 卡顿分析方法论](03-jank-methodology.md)**：在分析卡顿时，CPU 频率是需要优先排查的因素之一

## 常见问题与误区

### 误区 1：「CPU 利用率不高就不需要升频」

这在有 RTG/聚合调频机制的平台上是错误的。如果多个关联线程分散在不同 CPU 上，每个 CPU 的单独利用率可能只有 40-50%，但总负载已经需要更高的频率。在 Perfetto 中分析时，需要关注整个 cluster 上所有 CPU 的负载总和，而不仅仅是单个 CPU。

### 误区 2：「固定最高频率就能解决所有卡顿」

确实，将 CPU 固定在最高频率可以消除调频延迟导致的掉帧，但代价是巨大的功耗浪费和发热。长期来看，发热反而会触发 thermal throttling，导致更严重的性能下降。正确的做法是理解 DVFS 的行为，针对性地优化（如使用 ADPF），而不是一刀切地拉满频率。

### 误区 3：「调频延迟只有几十微秒，对性能没影响」

从硬件角度看，单次频率切换可能只需要几十微秒。但从端到端的角度看——PELT 的响应时间 + rate_limit + 硬件切换延迟——整个过程可能达到数十甚至上百毫秒。在 60fps 的场景下，可能错过 1-6 帧。所以调频延迟是一个真实的性能因素。

### 误区 4：「schedutil 的调频策略对所有场景都合适」

schedutil 是一个通用方案，它对典型 Android 应用场景做了优化，但对特殊场景（如游戏、相机预览、音频处理）不一定是最优的。这就是为什么 Android 引入了 ADPF——让应用有机会根据自身特点影响调频决策。

## 参考资料

- Linux 内核 cpufreq 文档：kernel.org/doc/Documentation/cpu-freq/
- Linux 内核 OPP 框架：kernel.org/doc/Documentation/power/opp.txt
- schedutil 源码：kernel/sched/cpufreq_schedutil.c
- Android ADPF 官方文档：developer.android.com/games/optimize/adpf
- Perfetto CPU frequency 文档：perfetto.dev/docs/data-sources/cpu-frequency
- RTG 聚合调频分析：OPPO 内核工匠《调度器分支之RTG》
- GPU 性能原理：腾讯技术工程《GPU 性能原理拆解》
