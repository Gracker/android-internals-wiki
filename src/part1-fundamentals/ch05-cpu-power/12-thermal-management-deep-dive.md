---



last_task9_at: "2026-06-05T07:20:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-05"
title: "Thermal 管控深度：从内核子系统到 ADPF 主动降频"
chapter: "5.12"
section: "5.12"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-12"
last_verified_against: "AOSP android-16.0.0_r1, Linux kernel android16-6.12"
confidence: medium
sources:
  - type: aosp
    path: "drivers/thermal/thermal_core.c"
  - type: aosp
    path: "drivers/thermal/cpufreq_cooling.c"
  - type: aosp
    path: "drivers/thermal/gov_step_wise.c"
  - type: aosp
    path: "drivers/thermal/gov_power_allocator.c"
  - type: aosp
    path: "drivers/thermal/devfreq_cooling.c"
  - type: aosp
    path: "drivers/devfreq/devfreq.c"
  - type: aosp
    path: "hardware/interfaces/thermal/aidl/android/hardware/thermal/"
  - type: official
    path: "developer.android.com/games/optimize/thermal"
  - type: official
    path: "developer.android.com/games/optimize/adpf"
  - type: official
    path: "source.android.com/docs/core/power/thermal-mitigation"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-analysis-with-sql"
  - type: blog
    path: "mediatek.com - MAGT ADPF integration case studies"
tags: [thermal, throttling, ADPF, Thermal HAL, sustained performance, 游戏性能, 功耗, devfreq, power_allocator]
related_chapters: ["5.5", "5.9", "4.7", "8.9", "11.1", "16.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "官方文档+研究素材+AOSP结构+读者需求"
gap_score: "18/20"
pipeline_stage: "task6_pending"
task6_state: "revisiting"
reviewed_date: 2026-06-04
last_task6_audit: "2026-06-08"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: fixed
task9_result: "auto-fixed"
last_task9_audit: "2026-06-15"
last_task9_audit_at: "2026-06-15T01:26:52+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-15-01-audit.md"
last_task9_review_log: logs/deep-review/2026-06-05-07-deep-review.md
task9_review_notes: "2026-06-15 Task9 idle audit: auto-fixed。收紧 android16-6.12/android-16.0.0_r1 源码锚点；修正 critical trip 保护路径、headroom listener 去抖逻辑、PowerManager listener 清理描述；回到 Task6 复审。"
last_task2b_by: openclaw-task2b-main
task2b_fix_summary: "2026-06-04 Task2B main: P1 Linux thermal kernel source branch disambiguated from generic 6.1 to android16-6.12; critical trip handler symbols corrected for branch consistency; step_wise get_target_state() added bool throttle parameter; Thermal HAL version table split into AIDL basics (14), cooling callback (15), forecastSkinTemperature + Framework fallback (16)."
last_task2b_at: "2026-06-04T14:54:52+08:00"
last_task6_at: "2026-06-04T15:21:59.742576+08:00"
task6_reviewed_date: 2026-06-04
task6_reviewed_by: "openclaw-task6"
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
task6_review_notes: "2026-06-04 Task6 revisiting review: pass-light-edit。L1 小修 2 处（形容词+冒号起手式 1、「很关键」填充 1）。无新增 L3/L4 回炉项。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-10
last_task9_autofix_at: "2026-06-15"
---

# Thermal 管控深度：从内核子系统到 ADPF 主动降频

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Thermal Zone、trip point、cooling device 三者的关系
- 🔹 `step_wise` 与 `power_allocator` 的决策逻辑和调参差异
- 🔹 Thermal HAL 的接口结构、severity 映射与 OEM 差异
- 🔹 ADPF / thermal headroom 如何把被动降频变成主动控温
- 🔹 游戏场景里的分辨率、帧率和厂商扩展策略
- 🔹 Perfetto + SQL 分析 thermal throttling 的定位流程

### 扩展（可选深入）

- 🔸 `power_allocator` 的 PID 参数与 `sustainable_power`
- 🔸 MediaTek MAGT 与多传感器融合策略
- 🔸 Thermal 能力从 Android 7 到 Android 16 的版本演进

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

本章是 [5.5 Thermal 管控](05-thermal.md) 的深度扩展。5.5 讲的是"温控系统从传感器到 App 的完整流程"，适合建立全局认知。如果你已经读完 5.5，并且需要回答这些问题——"内核的 thermal governor 具体怎么决策？""power_allocator 的 PID 参数怎么调？""为什么同一款 SoC 的两台手机 thermal 表现差这么多？""在 Perfetto 里怎么用 SQL 量化 thermal throttling 对帧率的影响？"——那么你在这篇文章里能找到答案。

[5.9 ADPF 自适应性能框架](09-adpf.md) 讲了 Performance Hint API 和 Game Mode API 的使用方法。本章聚焦在 thermal 这一侧：内核子系统的内部机制、Thermal HAL 的接口演进、以及从被动降频到主动温控的范式变化。ADPF 作为"App 主动参与温控"的手段，在本章中从 thermal 的视角被重新审视。

## 为什么需要深挖 Thermal 子系统

5.5 中我们看到了温控对性能的影响——30 分钟游戏测试中帧率从 120fps 降到 30fps 的场景。但那篇是面向"识别问题"的：知道温控在介入就够了。本文面向的是"解决问题"：理解内核 thermal governor 的决策逻辑，才能在 Perfetto 中准确判断"为什么这一刻开始降频了"，才能在系统调优时知道该动哪个参数。

这个区分决定了后续排查方向。有些性能问题是可以通过 App 层优化解决的（减少不必要的计算、使用 ADPF 主动降载）。但有些问题的根因在系统层——OEM 的 thermal 策略过于保守、kernel governor 的响应曲线不合理、或者 devfreq cooling 对 GPU 的限制过早介入。解决后者需要对 thermal 子系统有更深的理解。

[图：Thermal 问题分析的三个层次——App 层（ADPF Thermal API）→ Framework 层（ThermalManagerService）→ Kernel 层（thermal governor + cooling device），标注每层能做什么、不能做什么]

## Linux 内核 Thermal 子系统：内核的温控引擎

内核 thermal 子系统位于 `drivers/thermal/`，是所有温控行为的底层执行者。不管是 Android 的 ThermalManagerService 还是 OEM 的 thermal daemon，最终都是通过操作内核的 thermal zone 和 cooling device 来实现温控。

### Thermal Zone：温度监控的抽象

一个 thermal zone 就是一个温度监控区域。它绑定了三个东西：一个温度传感器（或者虚拟温度源）、一组 trip point（温度阈值）、和一组关联的 cooling device。

```bash
# 查看系统上所有 thermal zone
$ ls /sys/class/thermal/
thermal_zone0  thermal_zone1  thermal_zone2  cooling_device0  cooling_device1

# 查看某个 thermal zone 的类型和温度
$ cat /sys/class/thermal/thermal_zone0/type
cpu-0-0-0
$ cat /sys/class/thermal/thermal_zone0/temp
52000    # 52.0°C

# 查看这个 zone 的 trip points
$ cat /sys/class/thermal/thermal_zone0/trip_point_*_temp
55000   # trip_point_0: 55°C (passive)
65000   # trip_point_1: 65°C (hot)
85000   # trip_point_2: 85°C (critical)
$ cat /sys/class/thermal/thermal_zone0/trip_point_*_type
passive
hot
critical
```

在 Android 设备上，典型的 thermal zone 配置包括 CPU 各个 cluster（通常每个 cluster 一个 zone）、GPU、电池、皮肤温度估算（skin thermal zone，通过多个传感器的加权模型计算）、以及 USB/充电 IC。这些配置通常定义在设备树（Device Tree）中：

```dts
// arch/arm64/boot/dts/vendor/thermal.dtsi（简化示例）
cpu_thermal: cpu-thermal {
    polling-delay-passive = <100>;   // 被动降温时每 100ms 轮询
    polling-delay = <1000>;          // 正常时每 1s 轮询
    thermal-sensors = <&tsens 0>;    // 绑定温度传感器

    trips {
        cpu_alert0: trip-point-0 {
            temperature = <55000>;   // 55°C
            hysteresis = <2000>;      // 2°C 回差
            type = "passive";
        };
        cpu_crit: trip-point-2 {
            temperature = <85000>;   // 85°C
            hysteresis = <0>;
            type = "critical";       // 触发关机
        };
    };

    cooling-maps {
        map0 {
            trip = <&cpu_alert0>;
            cooling-device = <&cpu0 1 4>;  // cooling state 范围 1-4
        };
    };
};
```

这里有几个值得注意的设计细节。`polling-delay-passive` 设为 100ms 而 `polling-delay` 设为 1000ms——当温度在安全范围内时，内核每秒检查一次就够了；一旦温度超过 passive trip point 进入被动降温模式，检查频率提高到每 100ms 一次，因为需要更快地响应温度变化。`hysteresis`（回差）的设计是为了防止温度在阈值附近震荡时频繁切换 cooling state——温度需要下降 2°C 低于阈值后才会退出 passive 模式。

[已验证: Linux kernel Documentation/thermal/sysfs-api.rst, drivers/thermal/of-thermal.c]

### Trip Point 的四种类型

内核定义了四种 trip point 类型，每种对应不同的系统行为：

**Passive trip point** 是最常用的。触发后，内核通知关联的 cooling device 开始被动降温（通常是限制频率）。之所以叫"被动"，是因为降温通过降低设备的"活跃度"来实现——把 CPU 频率压低，它自然就少发热了。

**Active trip point** 触发主动降温措施——比如开启风扇。在手机上基本不用（手机没有风扇），但在平板、Chromebook、嵌入式设备上会用到。部分游戏手机（如 ROG Phone）的外接散热风扇就通过这个机制控制。

**Hot trip point** 表示温度已经进入危险区间，但它还不是“立刻关机”的同义词。`thermal_core.c` 在温度向上跨过 `THERMAL_TRIP_HOT` 或 `THERMAL_TRIP_CRITICAL` 时，都会先走 `handle_critical_trips()`。如果 trip 类型是 `THERMAL_TRIP_HOT`，并且该 thermal zone 实现了 `tz->ops.hot()`，内核只会调用 hot 回调，让平台记录告警或触发更激进的缓解动作；是否继续限频、通知用户空间，要看 zone 的实现。

**Critical trip point** 才是硬件保护真正开始执行的那一层。`android16-6.12` 的 `handle_critical_trips()` 在 `THERMAL_TRIP_CRITICAL` 分支调用 `tz->ops.critical(tz)`。如果平台注册 thermal zone 时没有提供 `critical` 回调，thermal core 会默认填成 `thermal_zone_device_critical()`；这个函数再调用 `thermal_zone_device_halt(tz, true)`，最终走 `hw_protection_shutdown(...)`。同文件还导出了 `thermal_zone_device_critical_reboot()`，它走 `thermal_zone_device_halt(tz, false)`，用于 reboot 保护路径；Android 16 这条主路径里没有 `thermal_zone_device_critical_shutdown()` 这个符号。

不同 linux-stable 分支的热保护代码形态存在差异——`android14-6.1` / `android15-6.6` 的 `handle_critical_trips()` 仍接收 `trip`、`trip_temp`、`trip_type` 分散参数，并通过 `tz->ops->critical(tz)` 访问回调；`android16-6.12` 改成 `const struct thermal_trip *trip`，并通过复制到 `tz->ops` 的结构体成员调用 `tz->ops.critical(tz)`。本章源码锚点以 `android16-6.12` 为主，跨分支对比前要先确认对应分支。

[已验证: Linux kernel drivers/thermal/thermal_core.c (handle_critical_trips(), thermal_zone_device_critical(), thermal_zone_device_critical_reboot()), include/linux/thermal.h]

### Thermal Governor：温控策略的大脑

Thermal zone 定义了"什么时候该降温"，governor 决定"降多少、怎么降"。内核提供了几种 governor，它们的核心区别在于冷却策略的激进程度。

#### step_wise：逐步升温，逐步冷却

`step_wise` 是最简单的 governor，也是很多设备的默认选择。它的逻辑可以用三句话概括：

1. 温度超过 trip point 且仍在上升 → 增加 cooling state（降温力度更大）
2. 温度超过 trip point 但趋势平稳 → 保持当前 cooling state
3. 温度低于 trip point 且在下降 → 降低 cooling state（降温力度减小）

"Step"的意思是每次只调整一个级别。假设 CPU 的 cooling device 有 5 个 state（0-4，0 表示无限制，4 表示最大限制），从 state 0 开始：

- 第一个采样周期：温度超过 passive trip → state 变为 1（轻微限制）
- 第二个采样周期：温度继续上升 → state 变为 2（中度限制）
- 第三个采样周期：温度还在上升 → state 变为 3（较重限制）
- 温度开始回落 → state 保持 3（趋势平稳）
- 温度继续下降低于 trip point → state 变为 2

这种"一步一个台阶"的策略简单可靠，但有一个缺点：响应慢。如果温度急剧上升（比如游戏场景切换到高负载），step_wise 需要多个周期才能把 cooling state 拉到位，期间温度可能已经冲到很高。

```c
// drivers/thermal/gov_step_wise.c（简化）
// step_wise 的核心逻辑
static unsigned long get_target_state(struct thermal_instance *instance,
                                       enum thermal_trend trend,
                                       bool throttle)
{
    struct thermal_cooling_device *cdev = instance->cdev;
    unsigned long cur_state = instance->target;

    // android16-6.12: throttle 控制是否允许增加 cooling state
    if (!throttle && trend == THERMAL_TREND_RAISING)
        return cur_state;

    switch (trend) {
    case THERMAL_TREND_RAISING:
        if (cur_state < instance->upper)
            return cur_state + 1;   // 温度在升 → 加一级
        break;
    case THERMAL_TREND_DROPPING:
        if (cur_state > instance->lower)
            return cur_state - 1;   // 温度在降 → 减一级
        break;
    case THERMAL_TREND_STABLE:
        return cur_state;           // 温度平稳 → 不动
    }
    return cur_state;
}
```

[已验证: Linux kernel drivers/thermal/gov_step_wise.c]

#### power_allocator：基于功耗预算的 PID 控制

`power_allocator` 更像一个按功耗预算工作的反馈控制器。它先估算 thermal zone 在下一轮能承受多少功耗，再把这个预算分给 CPU、GPU、NPU 等 power actor，而不是像 `step_wise` 那样一次只升降一个 state。

`android16-6.12` 的 `pid_controller()` 签名是 `pid_controller(struct thermal_zone_device *tz, int control_temp, u32 max_allocatable_power)`。它不再接收文中原来那组 `trip_switch_on`、`trip_temp` 或 `MAX_K*` 风格的参数，P/I/D 三项都直接围绕当前 zone 的目标温度、历史误差和最大可分配功耗展开。

```c
// drivers/thermal/gov_power_allocator.c
static u32 pid_controller(struct thermal_zone_device *tz,
                          int control_temp,
                          u32 max_allocatable_power)
{
    struct power_allocator_params *params = tz->governor_data;
    s64 p, i, d, power_range;
    s32 err, max_power_frac;
    u32 sustainable_power;

    max_power_frac = int_to_frac(max_allocatable_power);
    sustainable_power = get_sustainable_power(tz, params, control_temp);

    err = int_to_frac(control_temp - tz->temperature);

    p = mul_frac(err < 0 ? tz->tzp->k_po : tz->tzp->k_pu, err);
    i = mul_frac(tz->tzp->k_i, params->err_integral);
    if (err < int_to_frac(tz->tzp->integral_cutoff)) {
        s64 i_next = i + mul_frac(tz->tzp->k_i, err);
        if (abs(i_next) < max_power_frac) {
            i = i_next;
            params->err_integral += err;
        }
    }
    d = mul_frac(tz->tzp->k_d, err - params->prev_err);
    d = div_frac(d, jiffies_to_msecs(tz->passive_delay_jiffies));
    params->prev_err = err;

    power_range = sustainable_power + frac_to_int(p + i + d);
    return clamp(power_range, (s64)0, (s64)max_allocatable_power);
}
```

这段实现里，`k_po` 和 `k_pu` 分别处理 overshoot 和 undershoot。温度已经高于 `control_temp` 时，`err` 为负，控制器走 `k_po`；温度低于目标时，走 `k_pu`。积分项只有在误差低于 `integral_cutoff`，并且下一步积分值没有超过最大功耗预算时才继续累积，避免系统在轻载状态下把历史误差越攒越大。微分项直接用 `(err - prev_err)`，再按 `passive_delay_jiffies` 折算到时间尺度。`sustainable_power` 是 feed-forward 基线，P/I/D 只负责在这个基线上做修正。

从调参角度看，`power_allocator` 关注的不是“下一档 state 是多少”，而是“下一轮总功耗预算是多少”。这也是它比 `step_wise` 更平滑的原因。

[已验证: Linux kernel drivers/thermal/gov_power_allocator.c, Documentation/thermal/power_allocator.rst]

#### fair_share 和 user_space：其他 governor

`fair_share` 按比例分配 cooling 力度。如果一个 thermal zone 关联了多个 cooling device（比如同时限制 CPU 频率和 GPU 频率），fair_share 会根据每个 cooling device 的权重来分配降温任务。权重越高，分担的降温力度越大。

`user_space` 把温控决策权完全交给用户空间的 thermal daemon。内核只负责检测 trip point 触发，然后通过 uevent 通知用户空间程序，由后者决定采取什么降温措施。Android 设备上很多 OEM 的 thermal 策略就是通过用户空间 daemon 实现的——内核用 user_space governor，OEM 在用户空间的 thermal engine 中实现自己的策略逻辑。

### Cooling Device：降温的执行者

Cooling device 是 thermal 子系统的执行机构。每个 cooling device 有一个 state 值（从 0 到 max_state），state 越高降温力度越大。governor 的工作就是决定每个 cooling device 的 target state。

#### cpufreq cooling：限制 CPU 频率

最常见的 cooling device。它通过限制 CPU 的最大允许频率来实现降温。在 `android16-6.12` 中，这部分实现位于 `drivers/thermal/cpufreq_cooling.c`。thermal governor 设定 target state 后，cpufreq cooling 会把该 state 映射到受限频点或受限功耗区间，再通过 cpufreq QoS 和频率表收紧 CPU 的最高频率。

```bash
# 查看 CPU cooling device 的当前 state
$ cat /sys/class/thermal/cooling_device0/type
cpufreq
$ cat /sys/class/thermal/cooling_device0/cur_state
0        # 0 = 无限制
$ cat /sys/class/thermal/cooling_device0/max_state
4        # 最高 4 级限制

# 当 thermal governor 提高限制时
$ cat /sys/class/thermal/cooling_device0/cur_state
2        # 第 2 级限制，CPU 最大频率被压低
```

state 和实际频点之间没有统一的线性关系。cpufreq cooling 更常见的做法，是按 SoC 的 OPP 表、功耗模型或 freq_qos 约束，把 target state 映射成一个最高频率上限。下面这组数字只是假想示例，用来说明“state 越高，允许的最高频率越低”，不能当成通用频点表。

假设某颗大核集群的 OPP 表是 [3000, 2840, 2490, 2010, 1490] MHz，厂商把 state 0-4 分别映射到“无限制 / ≤2840 / ≤2490 / ≤2010 / ≤1490”。另一颗 SoC 完全可能有不同的频点数、不同的 state 数，甚至同一个 state 还会同时绑定功耗预算，而不只是单一频点。

#### devfreq cooling：限制 GPU/NPU 频率

`devfreq` 是 `cpufreq` 的“设备版”，管 GPU、NPU、DSP 等非 CPU 设备。真正把 thermal governor 接到这些设备上的代码在 `drivers/thermal/devfreq_cooling.c`；`drivers/devfreq/devfreq.c` 只提供通用 devfreq 框架和 OPP/QoS 管理，不是 thermal cooling device 本体。`CONFIG_DEVFREQ_THERMAL` 打开后，thermal 子系统才能通过 devfreq cooling 收紧这些设备的最高频率。

在 Android 设备上，GPU 的 devfreq cooling 是游戏场景 thermal throttling 的主要机制之一。当 GPU 温度升高时，thermal governor 同时提高 CPU cpufreq cooling state 和 GPU devfreq cooling state，两面夹击降低发热量。

```bash
# 查看 GPU 的 devfreq 信息
$ cat /sys/class/devfreq/gpu.0/cur_freq
500000000    # 500MHz
$ cat /sys/class/devfreq/gpu.0/max_freq
800000000    # 正常最高 800MHz

# thermal cooling 介入后
$ cat /sys/class/devfreq/gpu.0/max_freq
400000000    # 被限制到 400MHz
```

[待验证：不同 SoC 的 devfreq cooling 实现差异，Qualcomm Adreno vs MediaTek Mali 的具体行为]

#### CPU hotplug：历史方案与极端保护路径

Android 手机上更常见的 thermal 动作，还是 cpufreq/devfreq 限频、vendor thermal daemon、core control，或者 cpuset / cgroup 一类负载约束。CPU hotplug 更像历史方案或厂商的极端保护手段，不该写成 Framework / HAL severity 升高后的常规结果。

这里要把三层概念拆开。kernel thermal trip 和 governor 决定 thermal zone 到 cooling device 的本地动作；Thermal HAL 再把传感器状态折算成 `ThrottlingSeverity`；Framework 的 `THERMAL_STATUS_*` 则把这个 severity 暴露给系统服务和 App。这三层之间没有“severity 升一级，内核就 hotplug 一批核心”的直接映射。

如果某台设备真的出现核心离线，更稳妥的解释是：厂商在用户空间 thermal daemon、vendor kernel 模块或 core control 策略里额外加了激进保护。正文把 hotplug 降格为“可能存在的设备策略”，更符合近几代 Android 手机的主流实现。

[已验证: Linux kernel drivers/thermal/cpufreq_cooling.c, drivers/thermal/devfreq_cooling.c; source.android.com/docs/core/power/thermal-mitigation]

## Android Thermal HAL：内核与 Framework 的桥梁

5.5 中介绍了 Thermal HAL 的基本职责——将内核的温度数据抽象为标准化的 severity 级别，通过回调机制上报给 Framework。这里我们深入 HAL 层的接口设计和版本演进。

### AIDL 版 Thermal HAL 的接口结构

Android 10 到 Android 13 的 Thermal HAL 2.0 仍然是 HIDL。到了 Android 14，`IThermal` 才迁到 AIDL，接口定义在 `hardware/interfaces/thermal/aidl/android/hardware/thermal/`。当前契约把数据分成三组：当前温度与 cooling device、静态 threshold、事件回调和预测。

```java
// hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl
@VintfStability
interface IThermal {
    CoolingDevice[] getCoolingDevices();
    CoolingDevice[] getCoolingDevicesWithType(in CoolingType type);

    Temperature[] getTemperatures();
    Temperature[] getTemperaturesWithType(in TemperatureType type);

    TemperatureThreshold[] getTemperatureThresholds();
    TemperatureThreshold[] getTemperatureThresholdsWithType(
            in TemperatureType type);

    void registerThermalChangedCallback(in IThermalChangedCallback callback);
    void registerThermalChangedCallbackWithType(
            in IThermalChangedCallback callback,
            in TemperatureType type);

    float forecastSkinTemperature(in int forecastSeconds);
}
```

这里有两个容易混淆的点。第一，AIDL 返回的是 `Temperature[]`、`CoolingDevice[]`、`TemperatureThreshold[]` 数组，不是 `List<>`。第二，按类型过滤的注册接口是 `registerThermalChangedCallbackWithType()`，没有 `boolean filterType` 这种签名。

`TemperatureThreshold` 也不是一个单值阈值。它按 `ThrottlingSeverity` 提供 `hotThrottlingThresholds[]` 和 `coldThrottlingThresholds[]` 两组数组，Framework 可以据此知道同一个 skin、battery、cpu 传感器在 LIGHT、MODERATE、SEVERE 直到 SHUTDOWN 各档对应的静态温度线。`forecastSkinTemperature()` 则是 HAL 直接给出的 skin 温度预测值，单位仍是摄氏度。

对 Framework 来说，这一层做四件事：`getTemperatures*()` 读当前状态，`registerThermalChangedCallback*()` 订阅 severity 变化，`getTemperatureThresholds*()` 提供静态阈值基线，`forecastSkinTemperature()` 提供 HAL 侧预测能力。真正的 throttling status 还是要看 HAL 当前上报的 severity，不能只拿 threshold 数组硬推。

[已验证: hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl, TemperatureThreshold.aidl, source.android.com/docs/core/power/thermal-mitigation]

### OEM 实现差异：同一 SoC 的不同表现

Thermal HAL 的实现是 OEM 差异化最严重的部分之一。即使是同一款 SoC，不同厂商的 HAL 实现可能在以下方面完全不同：

**温度阈值映射**。HAL 需要将内核 thermal zone 的原始温度映射为 `ThrottlingSeverity` 枚举值。这个映射表由 OEM 定义——激进厂商可能把 SEVERE 映射到 60°C，保守厂商可能映射到 48°C。同样的温度，在两台手机上可能产生完全不同的 severity 级别。

**皮肤温度估算模型**。用户感受到的"手机烫不烫"取决于皮肤温度，而皮肤温度无法直接测量。OEM 通过热模型（thermal model）将 SoC 温度、电池温度、环境温度等输入估算为皮肤温度。这个模型的精度直接影响用户体验——估算偏高会导致过早降频，估算偏低会导致用户觉得烫手。

**多传感器融合策略**。高端设备有十几个温度传感器，HAL 需要决定哪个传感器的数据优先级最高。游戏场景可能以 GPU 和 CPU 温度为主，充电场景可能以电池温度为主。这个优先级策略因厂商而异。

[待验证：Qualcomm 和 MediaTek 参考实现中的 thermal threshold 默认值差异]

## 从被动降频到主动温控：ADPF 带来的范式变化

5.5 中我们看到的温控过程是"被动"的：温度升高 → 内核限制频率 → App 性能下降。App 在这个过程中是被动的承受者——不知道为什么突然卡了，也无法提前准备。

ADPF（Android Dynamic Performance Framework）改变了这个范式。通过 Thermal API，App 可以在系统强制降频**之前**感知到温度趋势，主动降低自己的负载。这种"主动降载"相比"被动降频"有几个优势：

1. **平滑过渡**。App 可以逐步降低画质（先降阴影分辨率、再降粒子效果、最后降帧率目标），用户几乎感知不到变化。系统强制降频则是一刀切——CPU 频率突然砍半，帧率瞬间腰斩。

2. **减少发热量**。App 主动降载减少了 SoC 的计算量，从源头降低了发热。如果 App 不降载，系统只能通过限制频率来降温——同样的计算量在更低频率下需要更长时间完成，帧时间反而更长。

3. **延长高性能时间窗口**。通过提前降载，App 可以让温度上升更缓慢，推迟系统强制降频的时刻，整体的高性能持续时间反而更长。

### HAL threshold → ThermalManagerService → headroom API

`PowerManager.getThermalHeadroom(int)` 从 API 30 就有了，但它不是把 HAL 的 severity 枚举原样转给 App。Framework 这一侧的输入是 skin sensor 的当前温度样本和对应阈值，核心实现在 `ThermalManagerService.TemperatureWatcher`。AIDL 里的 `forecastSkinTemperature()` 说明 HAL 也能给绝对温度预测，不过当前 Framework 暴露给 App 的 headroom 主要还是靠 `TemperatureWatcher` 自己采样和回归。

`TemperatureWatcher` 启动时先通过 `mHalWrapper.getTemperatureThresholds(true, Temperature.TYPE_SKIN)` 读取 skin 传感器的 `TemperatureThreshold`。它把每个传感器的 `SEVERE` 温度线记到 `mSevereThresholds`，再把 LIGHT 到 SHUTDOWN 的阈值归一化成 headroom threshold。多传感器设备会取更保守的一侧，也就是同一 severity 下更小的 normalized threshold。

```java
// frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java
List<TemperatureThreshold> thresholds =
        mHalWrapper.getTemperatureThresholds(true, Temperature.TYPE_SKIN);
float severeThreshold =
        threshold.hotThrottlingThresholds[ThrottlingSeverity.SEVERE];
mHeadroomThresholds[ThrottlingSeverity.SEVERE] = 1.0f;

float slope = forecastSeconds > 0 ? getSlopeOf(samples) : 0.0f;
float normalized = normalizeTemperature(
        currentTemperature + slope * forecastSeconds * 1000,
        severeThreshold);
```

真正做预测时，Framework 维护每个 skin sensor 最近一段时间的 ring buffer 样本。`getSlopeOf(samples)` 用线性回归算温升斜率，然后用 `currentTemperature + slope * forecastSeconds * 1000` 预测未来温度，再按 severe threshold 归一化。多个 skin sensor 同时存在时，`getForecast()` 会取 normalized 值最大的那个，把最坏的一路当成当前 headroom。

API 35 新增 `PowerManager.getThermalHeadroomThresholds()`，把这些 normalized threshold 直接开放给 App。官方文档也写得很清楚，`getThermalHeadroom()` 跟踪的是 skin 这类慢变传感器，没有必要高于约 1Hz 轮询，调用太频繁可能返回 `NaN`。如果设备还没有积累出足够样本，Framework 会先返回当前 headroom，而不是给一个激进的远期预测。

[已验证: frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java (TemperatureWatcher), developer.android.com/reference/android/os/PowerManager#getThermalHeadroom(int), developer.android.com/reference/android/os/PowerManager#getThermalHeadroomThresholds()]

## 游戏场景的 Thermal 管控策略

游戏是 thermal 问题最集中的场景——CPU 和 GPU 同时高负载、屏幕高亮度持续运行、用户手握设备阻碍散热。我们来看游戏场景下 thermal 管控的几个关键策略。

### 分辨率动态调整

最有效的主动降载手段。当 thermal headroom 下降时，游戏引擎动态降低渲染分辨率（比如从 1080p 降到 720p），然后通过 GPU 的空间放大（spatial upscaling）恢复到显示分辨率。帧率基本不受影响，但 GPU 的渲染负载降低了约 50%（像素数从 207 万降到 92 万）。

从 Android 16 / API 36 开始，`SystemHealthManager.getCpuHeadroom()` 和 `getGpuHeadroom()` 可以补一层 capacity signal。它们告诉我们 CPU 和 GPU 还剩多少可用算力，不直接等同于 thermal headroom。如果 GPU capacity headroom 已经很低，而 thermal headroom 还没有逼近 severe，通常先降分辨率更合适；如果 CPU、GPU 和 thermal headroom 一起收紧，再考虑同时降分辨率和帧率目标。

### 帧率目标动态降级

当分辨率已经降到下限但温度仍在上升时，下一步是降低帧率目标。从 120fps 降到 60fps 直接将每帧的 GPU 时间预算从 8.33ms 放宽到 16.67ms，GPU 可以在更低的频率下完成渲染。

`HintSession` 要和 ADPF 同步更新。降低帧率目标后，需要调用 `updateTargetWorkDuration()` 更新 target duration，否则 ADPF 会认为 App 还在追求 8.33ms 的帧时间，继续尝试提频——反而加剧发热。

```java
// 游戏场景的动态帧率调整
void adjustForThermal(float headroom) {
    if (headroom > 0.7f) {
        // 余量充足，保持高性能
        targetFps = 120;
        renderer.setResolutionScale(1.0f);
    } else if (headroom > 0.4f) {
        // 余量紧张，降低分辨率
        targetFps = 120;
        renderer.setResolutionScale(0.7f);
    } else {
        // 余量很低，同时降帧率和分辨率
        targetFps = 60;
        renderer.setResolutionScale(0.5f);
    }
    // 同步更新 ADPF HintSession
    hintSession.updateTargetWorkDuration(
        TimeUnit.SECONDS.toNanos(1) / targetFps);
}
```

### MediaTek MAGT：vendor case study

Google 和 MediaTek 的公开材料，把 MAGT（MediaTek Adaptive Gaming Technology）放在 ADPF 协同优化的案例里。正文更稳妥的读法，是把它当成 vendor case study：同样是“更早感知热余量，再更早降载”，Dimensity 平台在 Unity Boat Attack、Lineage W、Ares: Rise of Guardians 这些 workload 上展示了帧率稳定性和功耗改善的方向。

这一组材料能证明的重点，是厂商确实在做芯片级热数据和游戏负载控制的联动；它还不能直接推出“所有 SoC 都能拿到同样的 FPS、功耗、续航收益”。原始页面没有同时给出完整的环境温度、测试时长、分辨率 / 帧率档位和 baseline 配置，正文不再把 8.5 FPS、12% 功耗、25 分钟续航这类数字写成通用结论。

如果要把这类案例转成项目内的决策依据，至少要补四类测试元数据：workload 场景、环境温度、单次测试时长、对照组的分辨率 / 帧率 / 画质档位。条件没补齐之前，MAGT 更适合作为“厂商做过这类协同优化”的参考，不适合直接拷贝阈值或收益百分比。

[来源: Google ADPF / MediaTek MAGT 公开案例页面]

## 在 Perfetto 中分析 Thermal 问题

5.5 介绍了如何通过 CPU Frequency Track 和 thermal 数据源观察温控介入。这里我们进一步，用 Perfetto SQL 做更精确的量化分析。

### 查询 Thermal 状态变化时间线

```sql
-- 查询所有 thermal 相关事件
SELECT
  ts,
  name,
  CAST(dur / 1e6 AS FLOAT) AS duration_ms,
  track_id
FROM slice
WHERE name GLOB '*thermal*' OR name GLOB '*Thermal*'
ORDER BY ts
LIMIT 100;
```

### 关联 Thermal 状态与帧时间

这是最实用的查询——找出"thermal throttling 开始影响帧率"的精确时刻：

```sql
-- 找到 thermal severity 升高的时刻
-- 然后查看后续帧时间的变化
WITH thermal_events AS (
  SELECT
    ts,
    name,
    CAST(dur / 1e6 AS FLOAT) AS duration_ms
  FROM slice
  WHERE name GLOB '*thermal*throttling*'
    OR name GLOB '*ThermalThrottling*'
  ORDER BY ts
),
frame_times AS (
  SELECT
    ts,
    CAST(dur / 1e6 AS FLOAT) AS frame_time_ms,
    track_id
  FROM slice
  WHERE name = 'Choreographer#doFrame'
)
SELECT
  f.ts AS frame_ts,
  f.frame_time_ms,
  MIN(ABS(f.ts - t.ts)) AS closest_thermal_event_delta_ns
FROM frame_times f
CROSS JOIN thermal_events t
GROUP BY f.ts
HAVING f.frame_time_ms > 16.67  -- 只看掉帧
ORDER BY f.ts;
```

### 区分 Thermal 降频和调度延迟

这条查询的前提，是抓 trace 时已经打开 `power/cpu_frequency` ftrace 事件，或者 `linux.sys_stats` 里的 `cpufreq_period_ms`。CPU 频率本身来自 counter 轨道，标准表是 `counter` + `cpu_counter_track`，不是 `cpu_frequency_scans`。

```sql
-- 先看每个 CPU 的频率 counter
SELECT
  c.ts / 1e9 AS time_sec,
  t.cpu,
  c.value AS freq_khz
FROM counter c
JOIN cpu_counter_track t
  ON c.track_id = t.id
WHERE t.name GLOB '*cpufreq*'
ORDER BY c.ts, t.cpu
LIMIT 100;
```

如果这条查询没有结果，先执行 `SELECT DISTINCT name FROM cpu_counter_track;`，确认设备把 CPU 频率轨道命名成了什么。拿到频率曲线之后，再和 `sched` / `thread_state` 一起看：高 CPU 利用率 + 持续低频，更像 thermal throttling；低利用率 + 低频，很多时候只是 DVFS 正常回落。

[已验证: Perfetto SQL 文档, https://perfetto.dev/docs/analysis/trace-analysis-with-sql]

这三组查询覆盖了 thermal 分析的核心需求：确认 thermal 事件发生了、量化它对帧率的影响、排除其他原因（调度延迟或代码性能问题）。

[图：Perfetto 中 thermal 分析的完整工作流——CPU Frequency Track（频率变化）+ Thermal Status Track（severity 变化）+ Frame Timeline（帧时间）三图叠加分析]

### Thermal 问题分析的决策树

当我们看到帧率下降时，按以下决策树排查：

1. **CPU 频率有没有突然下降？**
   - 没有 → 不是 thermal，检查代码（锁竞争、GC、I/O 阻塞等）
   - 有 → 继续

2. **下降时 CPU utilization 是高还是低？**
   - 低 → 可能是 DVFS 正常调频，检查是否有 idle 后的提频延迟
   - 高 → 继续

3. **Thermal status 有没有变化？**
   - 没有 → 可能是 OEM 的用户空间 thermal daemon 直接操作了频率（不经过内核 thermal framework），检查 uevent 日志
   - 有（severity 升高） → 确认是 thermal throttling

4. **thermal 事件前 30-60 秒的帧时间趋势？**
   - 稳定 → thermal 是唯一原因
   - 逐步上升 → 可能叠加了负载增加（游戏场景切换）和 thermal，需要拆分

## Thermal 优化的工程实践

### App 层：ADPF 集成策略

**梯度降载**。不要等到 SEVERE 才开始降级。正确的做法是在 LIGHT 就做轻微调整（减少非关键的后台任务），在 MODERATE 降低渲染复杂度（阴影、粒子），在 SEVERE 降低帧率目标。每个级别都应该有预定义的降级策略。

**API 30-34：趋势式 fallback**。这几个版本只有 `PowerManager.getThermalHeadroom(int)`。更稳妥的用法是把它当作 skin 温度的慢变趋势信号，再结合 `getCurrentThermalStatus()` 做本机标定，不要把 `0.5`、`0.7` 这种经验值写成通用阈值。官方文档明确说了，没有必要高于约 1Hz 轮询，调用太频繁可能直接返回 `NaN`。

**API 35+：thresholds-aware**。从 `PowerManager.getThermalHeadroomThresholds()` 读取设备返回的 LIGHT、MODERATE、SEVERE 对应阈值，再决定何时降分辨率、何时降帧率，才符合 OEM 自己的 skin sensor threshold。NDK 侧对应的是 `AThermal_getThermalHeadroomThresholds()` 和 thermal headroom listener。

**HintSession 同步**。任何帧率目标的变更都必须同步更新 `HintSession.updateTargetWorkDuration()`。否则 ADPF 和 App 的预期不一致，App 已经按 60fps 的节奏在跑，系统却还在按 120fps 目标提频。

### Framework 层：JobScheduler 的 thermal 感知

`ThermalStatusRestriction` 把热限制分成三档。`THERMAL_STATUS_LIGHT` 开始限制 `PRIORITY_MIN`，并限制尚未运行或已经进入 overtime 的 `PRIORITY_LOW`。`THERMAL_STATUS_MODERATE` 进一步只放行 user-initiated job、部分 expedited job，以及仍在运行且没有 overtime 的 `PRIORITY_HIGH`。到了 `THERMAL_STATUS_SEVERE`，框架会直接限制全部 job。这里的 `JobInfo.Builder#setPriority()` 是 API 33 才引入的；更早版本不能把它当成 Android 10 就有的接口。

### Kernel 层：governor 参数调优

如果设备使用 `power_allocator` governor，PID 参数的调优是 thermal 性能调优的核心。调优需要实机测试——在典型负载（游戏、Camera、充电时使用）下抓取 thermal zone 温度曲线和 cooling state 变化，然后调整 PID 参数使温度曲线更平稳（减少振荡和过冲）。

关键参数和它们的效果：

| 参数 | 增大效果 | 减小效果 |
|------|---------|---------|
| `k_po`（比例系数，过热时） | 响应更快，可能过冲 | 响应更慢，温度可能超调 |
| `k_i`（积分系数） | 消除稳态误差更积极 | 允许温度偏离目标更久 |
| `sustainable_power`（可持续功耗） | 基线功耗预算更高 | 基线功耗预算更低，更保守 |

[待验证：Qualcomm 和 MediaTek 参考实现中的 power_allocator 默认 PID 参数]

### OEM 层：散热设计与软件协同

散热设计的物理极限决定了软件策略的天花板。VC 均热板（Vapor Chamber）面积越大，SoC 的热量扩散越快，thermal throttling 触发越晚。软件调优无法突破物理限制——如果 SoC 在全速运行时发热量超过散热能力的上限，无论 governor 参数怎么调，降频都是必然的。

OEM 在散热设计和软件策略之间需要找到平衡：
- 散热堆料不足 → 软件被迫过早降频 → 性能受限
- 散热过度 → 成本和重量增加 → 影响产品定位
- 软件策略过于激进（允许高温运行）→ 用户体验差（烫手）→ 差评

### 测试方法：如何复现和量化 Thermal Throttling

**环境控制**。测试时控制环境温度（建议 25°C ± 2°C），每次测试前让设备冷却到环境温度。环境温度每升高 5°C，thermal throttling 触发时间大约提前 20-30%。

**标准化负载**。使用可重复的负载场景（如 Unity Boat Attack demo、GFXBench 长期稳定性测试）进行测试，确保每次测试的负载模式一致。

**数据记录**。记录以下数据作为测试元数据：
- 测试前各 thermal zone 的初始温度
- 测试过程中的 thermal status 变化时间线
- 测试结束时的最终温度
- 环境温度和设备散热条件（是否有风冷、是否放在桌面上）

## 版本演进

| 版本 | 变化 | 影响 |
|------|------|------|
| Android 7.0 (API 24) | Sustained Performance Mode 引入 | 首次提供可预测持续性能档位 |
| Android 8.0 (API 26) | Thermal HAL 1.0 | Framework 能轮询温度与阈值 |
| Android 10 (API 29) | Thermal HAL 2.0（HIDL）+ thermal status callback | Framework 开始常驻监控 severity，App 可监听 thermal status |
| Android 11 (API 30) | `PowerManager.getThermalHeadroom(int)` | App 可以做预测式预降载 |
| Android 12 (API 31) | ADPF Performance Hint API | App 可以把 workload 目标时长告诉系统 |
| Android 14 (API 34) | `IThermal` 从 HIDL 迁到 AIDL，基础 AIDL 接口包含 `getTemperatures()`、`getCoolingDevices()`、`getTemperatureThresholds()`、`registerThermalChangedCallback()` | HAL 契约统一到 AIDL，Framework 通过 AIDL 获取温度、cooling device 和 threshold 数组 |
| Android 15 (API 35) | AIDL Thermal HAL 增加 cooling device changed callback；`PowerManager.getThermalHeadroomThresholds()` 开放给 App | HAL 侧可感知 cooling device 的动态变化；App 可以读取 OEM 返回的 headroom threshold，不必硬编码阈值 |
| Android 16 (API 36) | AIDL Thermal HAL 新增 `forecastSkinTemperature(int forecastSeconds)`；Framework `TemperatureWatcher#getForecast()` 在 HAL 支持 skin forecast 且仅有一路 skin threshold 时优先走 HAL 预测，否则回落到本地 ring buffer + 线性回归；`SystemHealthManager.getCpuHeadroom()` / `getGpuHeadroom()`，NDK thermal headroom listener | HAL 侧可返回未来 skin 温度预测值，Framework 不再只依赖本地采样回归；App 可区分 CPU/GPU capacity 余量，并在 native 层订阅 headroom 变化 |



## Android 16+ Thermal Headroom Listener：事件驱动的 headroom 监控

上一节的版本演进表里，Android 16 多了 `SystemHealthManager.getCpuHeadroom()` / `getGpuHeadroom()` 和 NDK thermal headroom listener。其中 headroom listener 改变了 App 获取温控信息的方式——从轮询变成事件驱动。下面展开这条新路径。

[已验证: `frameworks/base/core/java/android/os/PowerManager.java` (android-16.0.0_r1 l.1247-3011), `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` (android-16.0.0_r1 l.85-705, l.1830-1870, l.2197-2208), `frameworks/base/core/java/android/os/IThermalHeadroomListener.aidl`, `frameworks/native/include/android/thermal.h`, developer.android.com PowerManager#addThermalHeadroomListener]

API 35 的 `getThermalHeadroomThresholds()` 让 App 能读到 OEM 返回的 headroom 阈值。Android 16 (BAKLAVA / API 36) 在此基础上补了事件驱动机制——`addThermalHeadroomListener(...)`，让 App 不需要轮询就能收到 headroom 变化。本节展开这个新机制。

### 公共 API 形态

| 入口 | API Level | 形式 | 说明 |
| --- | --- | --- | --- |
| `PowerManager.addThermalHeadroomListener(OnThermalHeadroomChangedListener)` | 36 | 单参重载 | 默认走 `mContext.getMainExecutor()`，callback 在主线程 |
| `PowerManager.addThermalHeadroomListener(Executor, OnThermalHeadroomChangedListener)` | 36 | 多参重载 | 接收任意 `@CallbackExecutor` |
| `PowerManager.removeThermalHeadroomListener(OnThermalHeadroomChangedListener)` | 36 | 显式清理 | **必须**显式调用；`PowerManager` 端仍保存 listener → Stub 映射，生命周期结束后要释放本地引用 |
| `AThermal_registerThermalHeadroomListener(...)` | 36 (NDK r28+) | C API | NDK 端等价物，callback 在 system binder 线程池 |
| `AThermal_unregisterThermalHeadroomListener(...)` | 36 (NDK r28+) | C API | NDK 端清理 |

listener 接口（`OnThermalHeadroomChangedListener`）由 `@FlaggedApi(Flags.FLAG_ALLOW_THERMAL_THRESHOLDS_CALLBACK)` 标记，隐藏的 `@hide` AIDL `IThermalHeadroomListener` 是 binder 桥接，framework 内部用 `IThermalHeadroomListener.Stub` 把跨进程回调 marshal 到 App 端 Executor。

```java
// 源码锚点：PowerManager.java (android-16.0.0_r1) l.2822-2852
@FlaggedApi(Flags.FLAG_ALLOW_THERMAL_THRESHOLDS_CALLBACK)
public interface OnThermalHeadroomChangedListener {
    void onThermalHeadroomChanged(float headroom,
            float forecastHeadroom, int forecastSeconds,
            @NonNull Map<@ThermalStatus Integer, Float> thresholds);
}
```

回调只在以下两种条件满足其一才会触发（官方文档 + `ThermalManagerService.HeadroomCallbackData.isSignificantDifferentFrom` 双重确认）：

1. **thermal throttling 事件** —— skin 温度跨过任意 threshold，且短时间内没有发送过相似值的 callback；
2. **headroom / forecastHeadroom 变化 ≥ 0.03**（约 0.9°C），或 thresholds 数组变化 ≥ 0.01（约 0.3°C）；

仅当 absolute °C threshold 变化但 headroom 与 thresholds 都没显著变化时**不回调**，避免 App 收到无意义事件。

### 服务端节流与时序

`ThermalManagerService` 用 `RemoteCallbackList<IThermalHeadroomListener>` 维护监听者，关键常量：

```java
// 源码锚点：ThermalManagerService.java (android-16.0.0_r1) l.101-110
public static final int DEFAULT_FORECAST_SECONDS = 10;
public static final int HEADROOM_CALLBACK_MIN_INTERVAL_MILLIS = 5000;
public static final float HEADROOM_CALLBACK_MIN_DIFFERENCE = 0.03f;
public static final float HEADROOM_THRESHOLD_CALLBACK_MIN_DIFFERENCE = 0.01f;
```

`checkAndNotifyHeadroomListenersLocked`（l.329-348）只有一个合并去抖条件：如果 `!data.isSignificantDifferentFrom(mLastHeadroomCallbackData)`，并且 `System.currentTimeMillis() < mLastHeadroomCallbackTimeMillis + 5000ms`，这一轮相似数据会被跳过。只要 headroom / forecastHeadroom / thresholds 差异达到阈值，或者 5s 窗口已经过去，就会更新 `mLastHeadroomCallbackTimeMillis` 和 `mLastHeadroomCallbackData`，再通过 `mThermalHeadroomListeners.beginBroadcast()` 投递到每个 listener。`postHeadroomListenerLocked`（l.306-326）进一步把 callback 通过 `FgThread.getHandler().post(...)` 调度到 FgThread（前台线程），**避免阻塞 system_server 的 binder 线程池**。

注册成功后（`registerThermalHeadroomListener`，l.668-705）会**立即触发一次** callback（`postHeadroomListenerLocked(listener, data)`），App 端不必等下一次显著变化就能拿到当前 headroom 快照。

### 与 `getThermalHeadroomThresholds()` 的关系

`getThermalHeadroomThresholds()` 在 Android 16 (BAKLAVA) 文档注释（`PowerManager.java` l.3098-3102）明确说明：

> Starting at `Build.VERSION_CODES.BAKLAVA` the returned map of thresholds can change between calls to this function, one could use the new `addThermalHeadroomListener(...)` API to register a listener and get callback for changes to thresholds.

即 **API 36 起 `getThermalHeadroomThresholds()` 不再 cache**，每次调用都可能返回不同结果。推荐用法：

- **轮询 → 事件驱动**：用 `addThermalHeadroomListener(Executor, ...)` 订阅变化，仍保留 1Hz 以下的 `getThermalHeadroom(forecastSeconds)` 作为预测 sanity check。listener 不是预测轮询器，不会单独为了 forecast 温度变化启动周期回调；但一旦进入回调判断，`HeadroomCallbackData.isSignificantDifferentFrom()` 会把 `forecastHeadroom` 差异也纳入 0.03 的去抖阈值。
- **Main thread 还是 worker？** 单参重载默认 main thread，会进入 UI 消息队列；如果同时在做相机预览 / 游戏渲染，建议重载用单线程 `Executor`，把降分辨率、降帧率动作派发到渲染线程。
- **清理时机**：在 `Activity.onDestroy()` / `Surface` 释放 / `View.onDetachedFromWindow` 显式 `removeThermalHeadroomListener`；否则 `PowerManager` 端本地 map 会一直保留业务 listener → Stub 映射。

### 与 API 35 getThermalHeadroomThresholds 的版本差异

| 维度 | API 35 (Android 15) | API 36 (Android 16) |
| --- | --- | --- |
| thresholds 获取 | `getThermalHeadroomThresholds()` 首次查询后 cache，**调用间不变** | 不再 cache，**调用间可能变化** |
| 变化发现方式 | 主动轮询；Cache 失效后阈值变化要重启 App 才能感知 | listener 主动回调（thresholds 维度差异 ≥ 0.01 触发） |
| 预测 headroom 字段 | 需轮询 `getThermalHeadroom(forecastSeconds)` | listener 回调附带 `forecastHeadroom` + `forecastSeconds` 字段（默认 10s） |
| NDK 端等价 | `AThermal_getThermalHeadroomThresholds()` 返回常量数组 | `AThermal_registerThermalHeadroomListener` + `AThermal_HeadroomCallback` |
| callback 线程 | N/A | Java 端由 `Executor` 控制；NDK 端在 binder 线程池，App 需自己切线程 |
| binder 死亡清理 | N/A | App 端 listener map 不会自动清理，必须显式 `removeThermalHeadroomListener` |

### 跨进程调用链

```
App 进程                                          system_server
  │                                                  │
  │ addThermalHeadroomListener(Executor, listener)   │
  ├─────────────────────────────────────────────────►│ PowerManager
  │                                                  │ .addThermalHeadroomListener
  │                                                  │ → IThermalHeadroomListener.Stub
  │                                                  │ → mThermalService
  │                                                  │   .registerThermalHeadroomListener
  │                                                  │ → ThermalManagerService
  │                                                  │   .registerThermalHeadroomListener
  │                                                  │ → mThermalHeadroomListeners.register
  │                                                  │ → getHeadroomCallbackDataLocked
  │                                                  │ → postHeadroomListenerLocked
  │                                                  │ → FgThread.post(...)
  │                                                  │
  │ （温度变化触发）                                   │ onTemperatureChanged
  │                                                  │ → TemperatureWatcher
  │                                                  │   .onTemperatureChanged
  │                                                  │ → mHeadroomThresholds 更新
  │                                                  │ → checkAndNotifyHeadroomListenersLocked
  │                                                  │   （节流：5s 窗 + 0.03/0.01 阈值）
  │                                                  │
  │ ◄─────────────────────────────────────────────────┤ oneway binder
  │ listener.onHeadroomChange(headroom, forecastHeadroom,      │ IThermalHeadroomListener
  │     forecastSeconds, thresholds[])                  │ (oneway)
  │ → Executor.execute(() -> App.onThermalHeadroomChanged(...))
```

### 工程实践要点

- **零分配 vs GC**：Java 端 `OnThermalHeadroomChangedListener` 的 `thresholds` 参数是 `Map<@ThermalStatus Integer, Float>`，由 `convertThresholdsToMap` 每次新建 `ArrayMap`；高频回调（如 OTA 后台跑温度测试）会触发频繁 GC。NDK 端返回的是常量指针 `AThermalHeadroomThreshold*`（NDK 文档明确说明「`thresholds` pointer will be a constant shared across all callbacks registered from the same process」），NDK 客户端零分配。
- **binder 死亡 vs listener 清理**：`ThermalManagerService` 内 `mThermalHeadroomListeners` 用 `RemoteCallbackList` 维护跨进程回调；App 进程里的 `PowerManager.addThermalHeadroomListener` 还会把业务 listener 和内部 `IThermalHeadroomListener.Stub` 存到 `mThermalHeadroomListenerMap`，这个本地映射只在 `removeThermalHeadroomListener` 成功后删除。**显式 `removeThermalHeadroomListener` 是必须项**。
- **与其他 thermal API 的关系**：listener 是 `getThermalHeadroom(int)` + `getThermalHeadroomThresholds()` 的事件驱动版本；`OnThermalStatusChangedListener` 仍然只通知 `getCurrentThermalStatus()` 跨级事件（status 变化）。两者并存，listener 粒度更细，status listener 粒度更粗。
- **OEM 差异**：`TemperatureWatcher.getHeadroomCallbackDataLocked` 内部使用 `getForecast(0)` + `getForecast(DEFAULT_FORECAST_SECONDS=10)`；OEM 如果改 `mForecastSeconds`，listener 回调的 `forecastSeconds` 字段会同步变化（`isSignificantDifferentFrom` 把 `mForecastSeconds` 不一致视为显著差异强制回调）。`android-16.0.0_r1` 源码注释说 `currently this is always the same as DEFAULT_FORECAST_SECONDS`，未启用动态 forecast。

### 常见误区

- **「headroom listener 会代替 status listener」** ❌：两个 listener 走不同的判定路径，status listener 只在 thermal status 跨级时通知，headroom listener 还会通知 headroom/threshold 数值变化。两者并存。
- **「listener 触发频率高时应在 App 端去抖」** ✅：server 端有 5s 窗 + 0.03/0.01 阈值去抖，但 App 端的 Executor 可能让多个 listener 串行；建议 App 内部维护一个 `headroomCache` + 上次处理时间，仅在跨过自身业务阈值时降画质。

### 引用

- `frameworks/base/core/java/android/os/PowerManager.java`（android-16.0.0_r1 l.1247-3011, l.3098-3126）
- `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java`（android-16.0.0_r1 l.85-705, l.1830-1870, l.2197-2208）
- `frameworks/base/core/java/android/os/IThermalHeadroomListener.aidl`
- `frameworks/native/include/android/thermal.h`（NDK r28+）
- developer.android.com PowerManager#addThermalHeadroomListener


## 常见问题与误区

### 「Thermal throttling 只影响游戏」

在 5.5 中我们已经澄清了这个误区，但从工程实践角度补充：Camera 录制（尤其是 4K60fps）、视频通话（编码器 + 屏幕 + 网络同时工作）、GPS 导航（持续定位 + 屏幕 + 语音）、甚至长时间的大文件下载（Modem 持续高负载 + 充电发热）都可能触发 thermal throttling。任何持续时间超过 3 分钟的高负载场景都需要考虑 thermal。

### 「降低 CPU 频率就能降温」

不完全正确。功耗和频率的关系是非线性的——在频率较高时，每次提频带来的功耗增加远大于频率增加的比例（因为电压也需要同步提高）。反过来，在频率已经较高时降频，功耗下降的幅度比频率下降的幅度更大。所以从最高频率降 20% 可能带来 40% 的功耗下降。但在中低频率段，这种非线性效应减弱，降频的"性价比"降低。

thermal governor（尤其是 power_allocator）利用了这个非线性特性——在高频段优先降频（功耗收益大），在低频段更谨慎（性能损失大但功耗收益小）。

### 「Thermal 问题纯靠硬件解决」

软件策略的重要性经常被低估。同样的硬件条件下，好的 thermal 策略可以带来显著的用户体验差异。具体来说：

- **调度策略**：将高负载线程集中到大核运行（单核高频）vs 分散到多核运行（多核中频），功耗差异可达 30%。前者利用了功耗的非线性特性——一个核跑高频的功耗通常低于多个核跑中频的总功耗。
- **预判式降载**：通过 thermal headroom API 提前 30 秒开始降载，可以将持续性能窗口延长 40-60%。
- **场景感知**：充电时更积极地降频（用户不太感知性能）、游戏时更保守地降频（用户极度敏感），可以在不增加散热成本的前提下改善体验。

## 与其他机制的关系

- **[5.5 Thermal 管控](05-thermal.md)**：本章是 5.5 的深度扩展。5.5 建立全局认知，本章深入内核机制和工程实践。
- **[5.4 DVFS](04-dvfs.md)**：DVFS 是 thermal cooling 的执行手段。cpufreq cooling 通过限制 DVFS 的频率上限来降温。
- **[5.9 ADPF](09-adpf.md)**：ADPF 是 App 参与温控的桥梁。本章从 thermal 视角审视 ADPF，5.9 从性能优化视角审视 ADPF。
- **[8.9 游戏性能](09-game-performance.md)**：游戏是 thermal 问题最集中的场景。本章的游戏策略可以直接应用于 8.9 中的案例。
- **[11.1 功耗模型](01-power-model.md)**：thermal 和功耗是一体两面——功耗决定发热量，发热量触发 thermal throttling。理解功耗模型有助于从源头减少 thermal 压力。

## 参考资料

### AOSP 源码
- `drivers/thermal/thermal_core.c` — Thermal 子系统核心框架 [已验证]
- `drivers/thermal/gov_step_wise.c` — step_wise governor 实现 [已验证]
- `drivers/thermal/gov_power_allocator.c` — power_allocator governor (PID) 实现 [已验证]
- `drivers/thermal/cpufreq_cooling.c` — cpufreq cooling device 实现 [已验证]
- `drivers/thermal/devfreq_cooling.c` — devfreq cooling device 实现 [已验证]
- `drivers/devfreq/devfreq.c` — devfreq 框架本体，不直接承担 thermal cooling decision [已验证]
- `hardware/interfaces/thermal/aidl/android/hardware/thermal/` — Thermal HAL AIDL 接口 [已验证]
- `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` — Framework 温控服务 [已验证]

### 官方文档
- [Android Thermal Management](https://source.android.com/docs/core/power/thermal-mitigation) — 系统级温控架构 [已验证]
- [Perfetto SQL getting started](https://perfetto.dev/docs/analysis/trace-analysis-with-sql) — Trace Processor 与标准表查询 [已验证]
- [ADPF for Games](https://developer.android.com/games/optimize/performance#adpf) — 游戏 ADPF 集成指南 [已验证]
- [Thermal API Reference](https://developer.android.com/reference/android/os/PowerManager) — PowerManager Thermal API [已验证]
- [Game Mode API](https://developer.android.com/games/gamemode/gamemode-api) — Game Mode 文档 [已验证]

### 其他参考
- Linux kernel `Documentation/thermal/power_allocator.rst` — power_allocator governor 文档 [已验证]
- Linux kernel `Documentation/thermal/sysfs-api.rst` — thermal zone sysfs 接口 [已验证]
- [MediaTek MAGT & ADPF Integration](https://mediatek.com) — MediaTek 游戏性能优化案例 [来源: MediaTek 官方]
- [Perfetto Trace Configuration](https://ui.perfetto.dev/) — thermal/ftrace 数据源配置 [已验证]
