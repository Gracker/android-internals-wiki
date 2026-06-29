---
title: DVFS 与功耗管理
chapter: '5.4'
section: '5.4'
status: ready-for-review
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: '2026-06-29'
last_verified_against: AOSP android-17.0.0_r1 (frameworks/base, hardware/interfaces/power), Linux kernel 6.6 (android15-6.6), Linux kernel 6.12 (android16-6.12)
confidence: medium
sources:
- type: aosp
  path: frameworks/base @ android-17.0.0_r1
- type: aosp
  path: hardware/interfaces/power @ android-17.0.0_r1
- type: aosp
  path: kernel/sched/cpufreq_schedutil.c @ android15-6.6, android16-6.12
- type: aosp
  path: drivers/opp/ @ android15-6.6, android16-6.12
- type: official
  path: developer.android.com/games/optimize/adpf/performance-hint-api
- type: blog
  path: kernel.org/doc/Documentation/cpu-freq/governors.txt
- type: blog
  path: 'source: obsidian/Personal-Knowlodge/source/2026-03-05_wechat_谷歌官方性能文档2_Android_动态性能框架优化Performance_Hint_API.md'
- type: blog
  path: 'source: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md'
tags:
- dvfs
- cpufreq
- schedutil
- opp
- power
- frequency-scaling
- adpf
related_chapters:
- '5.1'
- '5.2'
- '5.3'
- '5.5'
- '5.6'
- '7.3'
drafted_date: '2026-04-01'
drafted_by: openclaw-task2
polish_count: 1
polish_date: '2026-04-07'
polish_by: task2b-polish
task9_result: auto-fixed
task9_reviewed_date: '2026-06-07'
task2b_state: fixed
task2b_result: fixed
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-06-29T19:26:54+08:00'
last_task9_autofix_at: '2026-06-29'
status: ready-for-review
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
task9_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: '2026-06-07'
task6_reviewed_date: '2026-06-07'
last_task6_at: '2026-06-07T19:14:17+08:00'
last_task6_audit: '2026-05-24'
P26-06-07 Task6 18:10：Task9 auto-fix 后写作复审；L1/L2 全面扫描零命中，无需修复；送 Task9 复核 auto-fix 结果。2026-05-01 task9 deep-review: needs-rework。P0 2，P1 1，P2 1。 | 2026-05-06
  Task6 01:05：Task2B 修复后写作复审，清理 L1/L2 表达与格式；无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-06
  Task9 01:28：needs-rework。schedutil android15/16 源码节选仍与 kernel/common 不符，SCMI Performance
  Protocol msg_id 错误；已写入 queue P95，交 Task2B 回炉。 | 2026-05-06T01:45:17+08:00 Task2B：P0
  schedutil 源码改为简化伪代码并标注省略项；P0 SCMI PERF_LEVEL_SET/GET msg_id 修正为 0x7/0x8，补 fastchannel
  事件说明。 | 2026-05-06 Task6 02:06：Task2B 修复后写作复审；清理 L1 填充词 3 处，无新增 L3/L4 回炉项，送 Task9
  复审。 | 2026-05-06 16:24 Task6：Task2B 修复后写作复审；修复 schedutil 伪代码块 Markdown 围栏，无新增 L3/L4
  回炉项，送 Task9 复审。 | 2026-05-06 18:18 Task6：Task2B 修复后写作复审；修复 schedutil 伪代码块 Markdown
  断行、统一数值单位空格和少量 L2 表达；无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-06 18:45 Task9：needs-rework。P0
  0 / P1 1 / P2 0。L275 RT/Deadline 任务并非在 Android 15/16 schedutil 中无条件拉到最高频；需按 effective_cpu_util()、uclamp
  与 DL bandwidth 重新表述。'
last_task2b_at: '2026-06-07T16:50:00+08:00'
last_task6_review_log: logs/review/2026-05-06-18-review.md
task6_review_notes: 2026-06-07 Task6 19:14：Task9 auto-fix 后写作复审（revisiting）；L1/L2 全面扫描零命中，无需修复；送 Task9 做最终 pass 确认。 |  2026-05-06T16:04 Task2B 修复后待 Task6 复审。 | 2026-05-06 Task6 13:13：Task2B
  修复后写作复审；清理 frontmatter 重复键并统一流水线状态；L1/L2 通过，无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-06
  16:24 Task6：Task2B 修复后写作复审；修复 schedutil 伪代码块 Markdown 围栏，无新增 L3/L4 回炉项，送 Task9 复审。
  | 2026-05-06 18:18 Task6：Task2B 修复后写作复审；修复 schedutil 伪代码块 Markdown 断行、统一数值单位空格和少量
  L2 表达；无新增 L3/L4 回炉项，送 Task9 复审。
last_task9_review_log: logs/deep-review/2026-06-29-19-audit.md
task9_review_notes: "2026-06-29 19:26 Task9 闲时抽检 auto-fixed：P1 1；Android 17 tag 已公开，Framework/Power HAL 源码锚点从 android-16.0.0_r1 升到 android-17.0.0_r1；回到 Task6 复审。 | 2026-06-07 19:20 Task9 pass-tech-review：P0 0 / P1 0 / P2 0；复核今日 auto-fix 结果通过，queue 无 pending，自动晋升 finalized。 | 2026-06-07 18:20 Task9 auto-fixed：P2 3；收紧 Perfetto/SCMI 频率口径、修正 7.3 相对链接、修正 scaling_cur_freq 与 thermal trip point 设备边界。回到 Task6 复审。 | 2026-06-07 17:20 Task9 auto-fixed：P0 2；修正 GameManagerService loading power mode 入口为 setGameState/notifyGraphicsEnvironmentSetup，并将 Power HAL Mode 枚举 CAMERA 修为 CAMERA_STREAMING_*。回到 Task6 复审。 | 2026-06-07 17:05 Task6 revisiting pass-light-edit. L1 禁用词「落地」→「实现于」1处. 送Task9复审. | 2026-06-07 Task9 闲时抽检：needs-rework。P0 2 / P1 1；Android 17 源码锚点未公开且补充块把 GameManagerService/PowerManager powerHint 链路写错，已写入 queue P95。"
last_task9_audit: '2026-06-29'
review_type: task9-idle-audit
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-29
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

在 Perfetto 中打开一段 Trace，我们会看到每个 CPU 下方都有一条「CPU Frequency」轨迹，频率会随着负载和策略上下跳变。每一次跳变，背后都是 DVFS 子系统在决定：此刻的 CPU 应该跑多快。

如果我们做过性能优化，一定遇到过这样的场景：明明代码逻辑没问题，但第一帧就是卡了一下。或者列表滑动时偶尔掉帧，抓 Trace 一看，发现掉帧那个瞬间 CPU 频率很低——原来 CPU 还没来得及升频，帧就被渲染了。这就是 DVFS 调频延迟导致的性能问题，和我们之前在 [5.1 Linux 进程调度基础](01-linux-scheduling.md) 中讨论的调度问题不同：调度决定「哪个任务跑在哪个核上」，DVFS 决定「这个核跑多快」。

理解 DVFS 机制，能让我们在分析 Trace 时准确判断：一个掉帧是代码问题，还是 CPU 没跑起来？在 Perfetto 中看到的频率曲线，哪些变化是正常的，哪些意味着 governor 的参数需要调优？

## DVFS 的基本原理

### 频率、电压与功耗的关系

CPU 的功耗来自两部分：静态功耗（漏电流）和动态功耗（充放电）。动态功耗是主要的，可以用这个公式描述：

**P_dynamic ∝ C × V² × f**

其中 C 是电容（由芯片工艺和电路设计决定），V 是工作电压，f 是时钟频率。这里电压是平方关系——如果电压从 1.2 V 降到 0.8 V，仅电压变化就能将功耗降低到原来的 (0.8/1.2)² ≈ 44%，降幅超过一半。

[已验证: 官方文档, developer.android.com/games/optimize/adpf/performance-hint-api — 功耗与电压平方成正比]

这就是 DVFS 存在的主要原因。CPU 不需要时刻保持最高频率和最高电压——当负载较轻时，降低频率和电压可以大幅节省功耗，而对用户体验几乎没有影响。

但频率和电压之间存在一个约束：**更高的频率需要更高的电压来维持稳定运行**。这是因为更高的时钟频率意味着信号翻转更快，电路需要在更短的时间内完成充放电。如果电压不够，信号就无法在时钟周期内稳定到可识别的逻辑电平，导致计算错误。

DVFS 的任务是：根据当前负载，从预先定义好的频率-电压对中选择合适档位，同时调整时钟频率和供电电压。

### 为什么降压比降频更省电

回到功耗公式 P ∝ C × V² × f。假设我们将频率从最高频率 f_max 降到 f_max/2，电压可能从 V_max 降到约 0.8 × V_max（具体取决于工艺），那么：

- 功耗变为原来的 0.8² × 0.5 = 0.32 倍（约降 68%）
- 如果只降频不降压（某些简单实现），功耗变为原来的 1 × 0.5 = 0.5 倍（只降 50%）

因此，DVFS 必须同时调整电压和频率——单纯降频的效果远不如同时降压。功耗中电压项的二次方贡献，使得降压成为最有效的节能手段。

[已验证: 官方文档, developer.android.com — P ∝ C × V² × f 为 CMOS 动态功耗的标准公式]

### 4 GHz 时代的能效红线

2026 年旗舰 SoC 的大核最高频率已经突破 4 GHz（如骁龙 8 Elite 的 Oryon 核心）。在这个频率段，V/F 曲线变得极端陡峭：从 3.5 GHz 到 4.0 GHz 的频率提升可能不到 15%，但电压和功耗的增加可能超过 40%。功耗公式 P ∝ C × V² × f 在这里体现得淋漓尽致——频率线性增长，电压二次方增长，两者叠加后功耗呈超线性爆发。

到 4 GHz 这个档位，性价比会迅速下降。性能测试中，将最高频率限制在 3.5-3.8 GHz（通过 sysfs 写入 `scaling_max_freq`），通常只损失 5-10% 的单核算力，但整机功耗可以降低 20-30%。厂商的日常调度策略通常很少触及 4 GHz——它们留给短时 burst（如应用冷启动）使用。做性能优化时，如果 Trace 显示 CPU 长时间驻留在 4 GHz，反而需要检查 governor 的限频逻辑是否失效。

[待验证: 4 GHz+ 档位的具体 V/F 曲线数据因 SoC 而异，以上为典型趋势描述]

**获取实际 V/F 数据的方法**：每个 CPU cluster 的频率档位可以通过 sysfs 读取。`/sys/devices/system/cpu/cpufreq/` 下的 policy 目录（如 `policy4` 对应大核 cluster）包含 `scaling_available_frequencies` 和 `cpuinfo_max_freq` 等文件。对应的电压信息通常不在 sysfs 直接暴露，但在部分设备上可以通过 debugfs 的 `regulator` 节点（`/sys/kernel/debug/regulator/`）观察实际供电电压。限频的实际影响可以直接测试：找到大核 cluster 的 policy 目录，向 `scaling_max_freq` 写入目标频率上限（如 `3800000` 表示 3.8 GHz），在同一 workload 下用 Perfetto 对比帧时间分布和功耗——这种设备上的 A/B 对比比引用任何第三方数字都可靠。

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

这里有两点：第一，频率不是连续的——CPU 只能在这些预设的档位之间切换，不能运行在比如 500 MHz 这种没有验证过的频率上。第二，频率越高，需要的电压越高，而且电压的增长不是线性的——从低频到中频，电压增幅较小；从中频到高频，电压增幅变大。这也是功耗在高频段急剧上升的原因。

### OPP 在内核中的实现

Linux 内核通过 OPP 框架（`drivers/opp/`）管理这些档位信息。OPP 数据通常定义在设备树（Device Tree）中，以 `operating-points-v2` 属性描述：

```dts
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

[已验证: AOSP android15-6.6 & android16-6.12, drivers/opp/, OPP 框架核心代码]

OPP 框架为上层子系统（如 cpufreq、devfreq）提供了统一的接口来查询可用的频率-电压对。当 cpufreq governor 决定将 CPU 调到某个频率时，它会从 OPP 表中选择对应的条目，再由底层驱动（clock framework + regulator framework）去设置实际的频率和电压。

### 现代 SoC 中的 OPP 映射：SCMI / CPPC

上面的模型适合解释“平台有哪些可用档位”，但在 Android 15/16 常见的 ARMv8.4+ 平台上，OS 并不总是直接点名某个 MHz。很多 SoC 会通过 SCMI（System Control and Management Interface）或 CPPC（Collaborative Processor Performance Control）把请求表达成抽象的性能等级，再由固件把这个等级映射到具体的电压/频率档位。

这会带来两个变化。其一，OPP 仍然存在，但它更多是固件和电源管理逻辑内部的映射表，Linux 看到的接口逐步从“请求某个频点”扩展到“请求更高或更低的 performance level”。其二，切换路径可以缩短。带 Fastchannels 的 SCMI 实现会把一部分控制路径做成内存映射通道，请求不必每次都走高开销的 mailbox 往返。

具体映射过程是：OS 通过 `PERF_LEVEL_SET` 发出一个整数的 performance level（比如 level 7），固件端的 SCP（System Control Processor）收到后，在内部的 OPP 映射表中查找该 level 对应的 (frequency, voltage) 组合，再通过硬件驱动分别设置 PLL 和供电电压。映射在固件侧完成，Linux 内核不直接看到从 level 到 MHz 的对应关系——这就是为什么 Perfetto 中的 `power/cpu_frequency` 轨迹记录的是内核请求的频率，而固件实际下发的频率可能不同。Fastchannels 把控制路径从"mailbox 中断 → SCP 处理 → 中断返回"缩短为共享内存写入，省掉了 mailbox 往返开销。没有 Fastchannel 的平台，每次调频请求都要经过完整的 mailbox 交互，延迟更高。下文的"SCMI 频率真值"一节会展开如何用 Perfetto 追踪这个协商过程。

对性能分析有两点影响。Perfetto 里的频率跳变是 cpufreq / 驱动层记录到的状态变化，最终落点仍受 OPP、热约束和 governor 策略共同限制；如果怀疑固件压频，需要结合 SCMI 事件或平台映射表复核。端到端升频偏慢时，排查重点通常落在负载估计、uclamp、rate limit 和固件协商过程，单次 PLL 或 regulator 动作往往不是主要耗时项。

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

在 schedutil 出现之前，主流的 governor 是 ondemand。ondemand 的工作方式是定时采样（默认每 100 ms 一次）CPU 的 idle 时间，如果发现利用率超过阈值（默认 80%），就提高频率。这种方式的缺点是：**采样有延迟**。在采样间隔内，CPU 可能已经在高负载运行了，但 governor 还不知道。

schedutil 解决这个问题的方法是直接挂钩到调度器的负载追踪机制——PELT（Per-Entity Load Tracking）。PELT 我们在 [5.1 Linux 进程调度基础](01-linux-scheduling.md) 中介绍过，它为每个调度实体（task、task group、CPU runqueue）维护一个指数加权移动平均（EWMA）的利用率值。schedutil 直接读取这个值来决定频率，无需额外的采样开销。

#### schedutil 的频率计算

对于 CFS 调度类管理的普通任务，schedutil 仍然沿着 `1.25 × f_max × util / max_capacity` 这一类比例关系换算目标频率，但这里的 `util` 已经不是“裸 PELT 值”。在 android15-6.6 内核里，参与计算的是 `sugov_get_util()` 整理过的有效利用率，可以写成下面这个简化关系：

**util_eff = apply_iowait_boost(uclamp(PELT_util))**

这里叠在一起的有三类信息：

- **PELT 利用率**：调度器看到的近期负载
- **uclamp 钳位**：框架或内核给线程组施加的性能下限 / 上限
- **iowait boost**：I/O 唤醒后的短时提频

schedutil 的调频入口是 `sugov_update_single_freq()` / `sugov_update_single_perf()`（单 policy CPU 的两种模式）和 `sugov_update_shared()`（共享 policy CPU），公共逻辑由 `sugov_update_single_common()` 承载。这几个函数由调度器通过 cpufreq callback 触发，内部调用 `sugov_get_util()` 获取有效利用率，再经 `sugov_iowait_apply()` 处理 I/O 提频，最终换算目标频率。

android15-6.6 和 android16-6.12 的 `sugov_get_util()` 签名和调用链有明确差异：

```c
// kernel/sched/cpufreq_schedutil.c（简化伪代码，省略部分字段和分支）
// android16-6.12: sched_ext 性能目标 + 统一频率计算
static void sugov_get_util(struct sugov_cpu *sg_cpu, unsigned long boost) {
    unsigned long min = 0, max = 0;
    unsigned long util;
    // 始终从 sched_ext 性能目标起算
    util = scx_cpuperf_target(cpu);
    // 非 scx 独占模式时，叠加 CFS 负载
    if (!scx_switched_all())
        util += cpu_util_cfs_boost(cpu);
    // effective_cpu_util 返回钳位后的有效利用率，同时输出 min/max 约束
    util = effective_cpu_util(cpu, util, &min, &max);
    // boost（来自 iowait）与 util 取大值
    util = max(util, boost);
    // bw_min 保存带宽约束下限
    sg_cpu->bw_min = min;
    // 统一计算最终频率目标，返回值赋给 sg_cpu->util
    sg_cpu->util = sugov_effective_cpu_perf(cpu, util, min, max);
    // 省略：uclamp 钳位、bw_dl 计算、其他 sg_cpu 字段赋值等细节
}
```

```c
// kernel/sched/cpufreq_schedutil.c（简化伪代码，省略部分字段和分支）
// android15-6.6: 纯 CFS 负载，无 sched_ext，boost 由调用方处理
static void sugov_get_util(struct sugov_cpu *sg_cpu) {
    unsigned long util = cpu_util_cfs_boost(sg_cpu->cpu);
    sg_cpu->bw_dl = cpu_bw_dl(cpu_rq(sg_cpu->cpu));
    // effective_cpu_util 以 FREQUENCY_UTIL 模式计算有效利用率，无 min/max 输出
    sg_cpu->util = effective_cpu_util(sg_cpu->cpu, util, FREQUENCY_UTIL, NULL);
    // 省略：uclamp 钳位、其他 sg_cpu 字段赋值等细节
}
```

两个版本的核心区别：android15-6.6 的 `sugov_get_util()` 只收集有效利用率（`cpu_util_cfs_boost()` → `effective_cpu_util(..., FREQUENCY_UTIL, NULL)`），iowait boost 由调用方 `sugov_iowait_apply()` 单独叠加；android16-6.12 将 boost 作为参数传入 `sugov_get_util()`，始终从 `scx_cpuperf_target(cpu)` 起算（非 scx 独占时叠加 `cpu_util_cfs_boost()`），`effective_cpu_util()` 返回值赋给 util 并输出 min/max 约束，最终由 `sugov_effective_cpu_perf(cpu, util, min, max)` 计算频率目标并赋给 `sg_cpu->util`，`sg_cpu->bw_min = min` 保存带宽下限。上方代码块为简化伪代码，展示了核心调用链和关键差异点，省略了部分字段赋值和边界分支。

[已验证: AOSP android15-6.6 & android16-6.12, kernel/sched/cpufreq_schedutil.c — sugov_update_single / sugov_get_util / sugov_iowait_apply / sugov_effective_cpu_perf（代码块为简化伪代码，非逐行源码复刻）]

于是会出现一个在 Trace 里很常见的现象：即使 PELT 利用率还不高，只要 top-app 或关键线程被设置了较高的 `uclamp_min`，频率也会提早拉升；I/O 密集路径刚被唤醒时，也可能先吃到一段 iowait boost。

[已验证: AOSP android15-6.6 & android16-6.12, kernel/sched/cpufreq_schedutil.c — `sugov_get_util()` / 官方文档, kernel.org — schedutil 1.25 headroom]

对于实时（RT）和 Deadline 调度类的任务，schedutil 的策略取决于 uclamp 是否启用。Android 设备上 uclamp 通常已开启（top-app `uclamp_min` 由 ActivityManager 设置），此时 RT 任务受 `uclamp_min` / `uclamp_max` 约束，不会无条件拉到最高频率。只有 `uclamp` 未启用时，schedutil 才会在 RT runnable 的 CPU 上直接返回 `max`。Deadline 调度类通过 `cpu_bw_dl` 提供带宽下限和饱和判断，影响目标频率——饱和时到 `max`，未饱和时按带宽比例贡献。`effective_cpu_util()` 会汇总 CFS、RT、DL、IRQ 各部分的利用率，最终由 `uclamp` / `schedutil` 计算频率目标，不存在 RT/DL 无条件 `fmax` 的单一策略。

[已验证: android15-6.6 kernel/sched/core.c:7605-7679 effective_cpu_util()；android16-6.12 kernel/sched/fair.c:8380-8414]

#### schedutil 的调频速率限制

schedutil 有一个 `rate_limit_us` 参数（通过 sysfs 可配置），控制两次频率调整之间的最小间隔。默认值通常在 0.5 ms 到 2 ms 之间。这个参数的目的是避免频率过于频繁地来回切换（即所谓的频率抖动），因为每次频率切换本身都有开销。

但在 Android 设备上，许多厂商会通过 vendor hook 或直接修改内核来调整这个参数，以适应自家 SoC 的特性。例如，某些厂商会在触摸事件到来时临时将 rate_limit 降到 0，以实现更快速的升频响应。

### Qualcomm 平台的扩展：DCVS 与 RTG

在 Qualcomm 平台上，schedutil 不是孤立工作的。Qualcomm 在其内核中实现了更复杂的调频策略，通常统称为 DCVS（Dynamic Clock and Voltage Scaling）。其他 SoC 厂商（如 MediaTek、Samsung）也有各自的调频增强机制，原理类似但实现不同，本节以 Qualcomm 为例。其中 RTG（Related Thread Group）机制对性能分析特别重要。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md]

我们在 [5.3 大小核架构](03-big-little.md) 中提到过，Android 前台应用通常有多个线程协同工作（如 MainThread + RenderThread）。如果这些线程被分散到不同的 CPU 上运行，每个 CPU 的单独利用率可能都不高（比如只有 50%），schedutil 就不会积极升频。但这些线程的**总负载**已经很高了。

RTG 的「聚合调频」功能就是为了解决这个问题。当 Android 的 top-app cgroup 中的线程被标记为同一组后，RTG 会将这组线程在同一个 cluster 上的负载**累加计算**，再将累加后的负载反馈给 schedutil。这样即使线程分散在多个核上，调频决策也能反映真实的总需求。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md — RTG 聚合调频机制]

因此在 Perfetto 中分析性能问题时，我们需要关注 CPU 频率和负载分布之间的关系——单核利用率低不代表 CPU 性能有余量，可能是调频策略没有识别到跨线程的负载聚合。

## 调频延迟对性能的影响

### DVFS 的升频延迟

从 governor 决定升频到频率实际生效，需要经过这些步骤：

1. 调度器更新 PELT 利用率（每个调度周期 ~1 ms 或 ~4 ms）
2. schedutil 根据利用率计算目标频率
3. 通过 cpufreq driver 发起频率切换请求
4. clock framework 调整 PLL（锁相环）配置
5. regulator framework 调整电压（如果需要）
6. 等待电压稳定后切换到新频率

整个过程的端到端延迟，从几十微秒到数百毫秒都有可能。单次 PLL / regulator 切换通常只占微秒到毫秒级，Google 官方文档里提到的约 **200 ms** 主要来自上游信号建立：PELT 的指数平滑需要时间积累，`rate_limit_us` 会压住过密的切频，请求到固件或驱动后才轮到硬件切换。Trace 里看到“频率升得晚”时，排查顺序通常先看负载估计和 governor 节流，再看底层时钟路径。

[已验证: 官方文档, developer.android.com/games/optimize/adpf/performance-hint-api — governor 升频可能需要约 200 ms]

### 升频延迟导致的掉帧

以 60 fps 为例，每帧的预算是 16.6 ms。如果在一个 VSync 周期内，CPU 突然需要更多算力（比如用户快速滚动列表），但 CPU 还在低频率运行，会发生什么？

1. VSync 到来，Choreographer 触发 doFrame
2. 主线程开始执行 measure/layout/draw，但 CPU 在低频运行
3. 由于频率低，本来 8 ms 能完成的工作现在需要 20 ms
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
2. 应用设定一个目标工作时长（target work duration），通常等于帧间隔（如 16.6 ms）
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
- **大小核的频率差异**：在 Perfetto 中同时展开 CPU 0-3（小核）和 CPU 4-7（大核）的频率 track，我们会发现它们的频率范围完全不同。小核通常运行在 300 MHz-1.8 GHz，大核在 300 MHz-3.0 GHz（具体数值因 SoC 而异）。
- **频率与任务的对应关系**：把 CPU Frequency track 和 CPU Scheduling track 放在同一时间轴上看，通常会发现当一个重负载任务被调度到某个 CPU 时，该 CPU 的频率会随之升高。但如果升频延迟较大，频率升高会滞后于任务调度。

### CPU Idle State Track

与频率 track 配合观察的还有 CPU Idle State track（来自 `power/cpu_idle` 事件）。Idle state 0 表示 CPU 在运行任务，数值越大表示睡眠越深。

CPU 频繁进出深度睡眠也会带来额外开销。虽然深度睡眠能省电，但从深度睡眠唤醒需要时间——退出延迟可达数百微秒甚至超过 1 ms。如果某个线程组需要频繁唤醒 CPU，而 CPU 每次短暂空闲都进入深度睡眠又被唤醒，反复的进出不仅浪费时间，进出低功耗模式本身也消耗能量。RTG 的 Busy Hysteresis 功能用来缓解这种情况：当 RTG 组中的线程活跃时，即使 CPU 短暂空闲，也延迟进入深度睡眠。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_调度器分支之RTG.md — Busy Hysteresis 机制]

### SCMI 频率真值：内核意图 vs 固件实值

前面提到，SCMI / CPPC 平台上 OS 发出的频率请求是抽象的 performance level，实际频率由固件映射。因此，Perfetto 中的 CPU Frequency 轨迹记录的是**内核请求的频率**，不一定是固件最终执行的频率——温控、电源管理策略等固件侧因素都可能压低实际输出。

Android 16（GKI 6.12）的 SCMI 框架提供了多个 ftrace 事件，可用于观察固件侧的频率协商过程。android16-6.12 的 `include/trace/events/scmi.h` 中定义的事件包括 `scmi_fc_call`、`scmi_xfer_begin`、`scmi_xfer_response_wait`、`scmi_xfer_end` 等。其中 `scmi_fc_call`（Fastchannel call）是直接观察 performance level 请求的关键事件——通过 `protocol_id`（0x13）和 `msg_id` 过滤 `PERF_LEVEL_GET` 类消息，可以追踪固件实际返回的 performance level，再与 `power/cpu_frequency` 轨迹中的内核请求频率对比。注意：`scmi_fc_call` 只在平台实现了 Fastchannel 地址时才会出现；没有 fastchannel 的平台需观察 `scmi_xfer_begin` / `scmi_xfer_end` 事件来追踪请求与响应。

如果两者出现持续偏差（内核请求高频，固件实际给低频），说明 SoC 固件的温控或电源策略正在介入。这种内核以为在高频、实际被压低的情况，是排查不明性能下降的重要线索。

SCMI Performance Protocol 的完整协商链涉及多个环节：OS 通过 `PERF_LEVEL_SET` (msg_id 0x7) 请求目标 performance level，固件将其映射到具体的 OPP 条目（frequency + voltage），再由 `PERF_LEVEL_GET` (msg_id 0x8) 查询固件实际下发的 level。每个 CPU domain 由 `res_id` 标识（通常与 CPU cluster 对应），`protocol_id` 为 0x13（SCMI_PROTOCOL_PERF，定义在 include/linux/scmi_protocol.h；注意 0x10 是 Base Protocol，不要混淆）。`scmi_fc_call` 事件中的 `protocol_id` 和 `msg_id` 可用来过滤不同类型的消息。这里要分清：performance level 到实际频率的映射是平台私有的——同一段 SCMI level 值在不同 SoC 上可能对应不同的 MHz。分析时必须结合设备的 OPP 表或 vendor dtbo 才能完成 level→freq 的换算。在没有平台映射表时，SCMI 事件只能定位"固件协商是否异常"，不能直接等同于实际频率真值。

[已验证: AOSP android16-6.12, include/trace/events/scmi.h — scmi_fc_call / scmi_xfer_* 事件族 / SCMI spec: Performance Protocol msg_id 0x7(PERF_LEVEL_SET)/0x8(PERF_LEVEL_GET), protocol_id 0x13]

要启用 SCMI 事件，在 Perfetto 配置中添加：

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "scmi/scmi_fc_call"
      ftrace_events: "scmi/scmi_xfer_begin"
      ftrace_events: "scmi/scmi_xfer_end"
      ftrace_events: "power/cpu_frequency"
    }
  }
}
```

### SQL 查询分析频率变化

Perfetto 的 Trace Processor 提供 SQL 接口，可以量化分析频率变化：

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

-- 查看每个 CPU 的频率驻留统计
SELECT
  cpu,
  freq / 1000.0 AS freq_mhz,
  round(sum(dur) / 1e9, 3) AS time_s,
  round(sum(dur) * 100.0 / sum(sum(dur)) over (partition by cpu), 1) AS pct
FROM cpu_frequency_counters
GROUP BY cpu, freq
ORDER BY cpu, freq;

-- 找出频率最低的时段（可能影响性能）
SELECT
  cpu,
  freq / 1000.0 AS freq_mhz,
  round(dur / 1e6, 2) AS duration_ms
FROM cpu_frequency_counters
WHERE freq < 500000  -- 低于 500 MHz（freq 单位为 kHz）
ORDER BY dur DESC
LIMIT 20;
```

`cpu_frequency_slices` 不是 Perfetto stdlib 标准表。频率分析应通过 `INCLUDE PERFETTO MODULE linux.cpu.frequency;` 引入 `cpu_frequency_counters` 模块后查询，列名是 `cpu`、`freq`、`dur`。如果环境未加载 stdlib，可退回原始 `counter` / `counter_track` 方案自行派生。

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

DVFS 和本书多个机制互相影响，理解这些关联对性能分析很重要：

- **[5.1 进程调度基础](01-linux-scheduling.md)**：schedutil 直接依赖 PELT 的利用率数据，调度器的负载追踪精度决定了调频的质量
- **[5.2 EAS 能量感知调度](02-eas.md)**：EAS 在选核时需要考虑不同 CPU 的能效比，而能效比本身取决于当前的频率/电压（即 DVFS 状态）
- **[5.3 大小核架构](03-big-little.md)**：大小核的迁移策略和 DVFS 互相影响——迁核后频率可能需要重新调整，频率变化又可能影响迁核决策
- **[5.5 Thermal 管控](05-thermal.md)**：当温度过高时，thermal 机制会限制 DVFS 的最高频率（即降频限频），这是功耗管理与热管理的交汇点
- **[7.3 卡顿分析方法论](../../part2-performance/ch07-smoothness/03-jank-methodology.md)**：在分析卡顿时，CPU 频率是需要优先排查的因素之一

## 常见问题与误区

### 误区 1：「CPU 利用率不高就不需要升频」

这在有 RTG/聚合调频机制的平台上是错误的。如果多个关联线程分散在不同 CPU 上，每个 CPU 的单独利用率可能只有 40-50%，但总负载已经需要更高的频率。在 Perfetto 中分析时，需要关注整个 cluster 上所有 CPU 的负载总和，而不仅仅是单个 CPU。

### 误区 2：「固定最高频率就能解决所有卡顿」

将 CPU 固定在最高频率可以消除调频延迟导致的掉帧，但代价是巨大的功耗浪费和发热。长期来看，发热反而会触发 thermal throttling，导致更严重的性能下降。正确的做法是理解 DVFS 的行为，针对性地优化（如使用 ADPF），而不是一刀切地拉满频率。

### 误区 3：「调频延迟只有几十微秒，对性能没影响」

从硬件角度看，单次频率切换可能只需要几十微秒。但从端到端的角度看——PELT 的响应时间 + rate_limit + 硬件切换延迟——整个过程可能达到数十甚至上百毫秒。在 60 fps 的场景下，可能错过 1-6 帧。所以调频延迟是一个真实的性能因素。

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

## 游戏调度框架与 Power HAL 协同


> **版本说明**：本节 Framework 与 Power HAL AIDL 锚点已复核到 `android-17.0.0_r1`；schedutil / SCMI 代码段保留 `android15-6.6` 和 `android16-6.12` 边界（kernel/common 尚无 android-17 tag），不写成 Android 17 新增行为。

### GameManagerService 游戏模式感知层

AOSP android-17.0.0_r1 中，`GameManagerService`（路径：`frameworks/base/services/core/java/com/android/server/app/GameManagerService.java`）负责检测和管理游戏状态。关键函数：

- `setGameMode(String packageName, @GameMode int gameMode, int userId)` — 切换游戏模式（标准/性能/省电），更新 game mode interventions
- `getGameMode()` — 查询当前游戏模式

游戏启动/加载阶段的性能提升路径不经过 `powerHint` / `POWER_HINT_*` 常量。可验证链路是：

```
GameManagerService → PowerManagerInternal.setPowerMode(Mode.GAME_LOADING, isLoading)
```

具体地，游戏进入 loading 状态有两条可验证入口：`setGameState(...)` 在应用上报 loading 状态时通过 handler 设置 `Mode.GAME_LOADING`；`notifyGraphicsEnvironmentSetup(...)` 在游戏启动的 graphics env 初始化后按配置开启 loading boost，并通过延迟消息关闭。`setGameMode(...)` 本身只更新模式与 interventions，不直接下发 loading power mode。`PowerManagerInternal` 是系统服务内部接口（`@hide`），不暴露给第三方应用。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/app/GameManagerService.java — `setGameState()` / `notifyGraphicsEnvironmentSetup()` / `PowerManagerInternal.setPowerMode(Mode.GAME_LOADING)`]

> **PowerManager.java / IPowerManager.aidl 复核**：android-17.0.0_r1 的 `PowerManager.java` 和 `IPowerManager.aidl` 未命中 `powerHint` 方法或 `POWER_HINT_*` 常量簇。旧版 Android（API 28 之前）曾存在 `powerHint()` / `POWER_HINT_INTERACTIVE` 等常量，已在后续版本移除，不是 Android 16/17 的公开 API。

### PowerManagerService 与 Power HAL AIDL

`PowerManagerService`（路径：`frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java`，android-17.0.0_r1）内部通过 `setPowerModeInternal()` 承载游戏/相机/VR 等场景的性能模式请求，JNI 入口为 `nativeSetPowerMode()`（路径：`frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp`），最终通过 Power HAL AIDL 接口 `IPower.setMode()` 下发到 HAL 层。

`hardware/interfaces/power/aidl/android/hardware/power/Mode.aidl` 中的 `Mode` 枚举（如 `GAME_LOADING`、`GAME`、`SUSTAINED_PERFORMANCE`、`CAMERA_STREAMING_HIGH` 等）取代了旧的 `powerHint` 整型常量机制。Android 15-17 的系统侧下发路径使用 AIDL Power HAL，具体模式到频率、调度或功耗策略的映射由 vendor 实现决定。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java + frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp + hardware/interfaces/power/aidl/android/hardware/power/Mode.aidl — `nativeSetPowerMode()` / `IPower.setMode()`]

### Power HAL 的 vendor 配置边界

Power HAL 如何把 `Mode.GAME_LOADING` 映射到具体的调频/调压动作，由 vendor 实现决定。常见的映射手段包括：

- 向 kernel cpufreq governor 注入 uclamp 下限或性能提示
- 调整 cpuset cgroup 的 CPU 亲和性（`/dev/cpuset/top-app/cpus`）
- 通过 SoC 私有接口（如 `/proc/cpufreq/sched_dcvs_perf`，属 vendor 路径）下发调频目标

这些映射逻辑不在 AOSP 主线范围内，不同 SoC 平台和 OEM 的配置差异很大，无法用一条通用调用链覆盖。在 Perfetto 中观察时，可以对比 `power/cpu_frequency` 轨迹与游戏加载区间的时间对齐关系，判断厂商的 GAME_LOADING → 提频映射是否生效，但映射表本身不暴露在 AOSP 的 public API 或 sysfs 标准接口中。

### Linux cpufreq + cpuset + thermal 协同

Android 的 CPU 调频栈最终由 Linux kernel 实现：

```
/sys/devices/system/cpu/cpu0/cpufreq/
├── scaling_governor      # schedutil（默认）/ ondemand / performance
├── scaling_max_freq      # 软件上限（可写入）
└── scaling_cur_freq      # cpufreq 驱动可见频率，常是上次请求的 P-state
```

cpuset cgroup 控制进程 CPU 亲和性：

```
/dev/cpuset/top-app/cpus   # 顶层应用（如游戏）
/dev/cpuset/foreground/cpus # 前台进程
```

thermal 降频路径：`/sys/class/thermal/thermal_zone*/`。具体 trip point 和降频动作由内核 thermal zone / vendor thermal engine 配置决定，不能按固定温度阈值概括；分析时读取 `trip_point_*`、Thermal HAL severity 或设备侧配置，再和 `power/cpu_frequency` 对齐。

### 荣耀 MUSCHED 说明

荣耀 MUSCHED 为厂商私有实现，AOSP 未见源码。已验证 AOSP 路径仅覆盖通用 Android 调度框架，厂商特异调度器（如 MUSCHED）属于 vendor 分支，不在 android-17.0.0_r1 主线范围内。Android 17 厂商扩展仍需设备厂商源码或 trace 复核。

