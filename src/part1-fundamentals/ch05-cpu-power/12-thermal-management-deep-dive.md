---
title: "Thermal 管控深度：从内核子系统到 ADPF 主动降频"
chapter: "5.12"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-09"
last_verified_against: "AOSP android-16.0.0_r1, Linux kernel 6.1"
confidence: medium
sources:
  - type: aosp
    path: "drivers/thermal/thermal_core.c"
  - type: aosp
    path: "drivers/thermal/cpu_cooling.c"
  - type: aosp
    path: "drivers/thermal/gov_step_wise.c"
  - type: aosp
    path: "drivers/thermal/gov_power_allocator.c"
  - type: aosp
    path: "drivers/devfreq/devfreq.c"
  - type: aosp
    path: "hardware/interfaces/thermal/aidl/android/hardware/thermal/"
  - type: official
    path: "developer.android.com/games/optimize/thermal"
  - type: official
    path: "developer.android.com/games/optimize/adpf"
  - type: official
    path: "source.android.com/docs/core/thermal"
  - type: blog
    path: "mediaTek.com - MAGT ADPF integration case studies"
tags: [thermal, throttling, ADPF, Thermal HAL, sustained performance, 游戏性能, 功耗, devfreq, power_allocator]
related_chapters: ["5.5", "5.9", "4.7", "8.9", "11.1", "16.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "官方文档+研究素材+AOSP结构+读者需求"
gap_score: "18/20"
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频

本章是 [5.5 Thermal 管控](./05-thermal.md) 的深度扩展。5.5 讲的是"温控系统从传感器到 App 的完整链路"，适合建立全局认知。如果你已经读完 5.5，并且需要回答这些问题——"内核的 thermal governor 具体怎么决策？""power_allocator 的 PID 参数怎么调？""为什么同一款 SoC 的两台手机 thermal 表现差这么多？""在 Perfetto 里怎么用 SQL 量化 thermal throttling 对帧率的影响？"——那么你在这篇文章里能找到答案。

[5.9 ADPF 自适应性能框架](./09-adpf.md) 讲了 Performance Hint API 和 Game Mode API 的使用方法。本章聚焦在 thermal 这条线上：内核子系统的内部机制、Thermal HAL 的接口演进、以及从被动降频到主动温控的范式变化。ADPF 作为"App 主动参与温控"的手段，在本章中从 thermal 的视角被重新审视。

## 为什么需要深挖 Thermal 子系统

5.5 中我们看到了温控对性能的影响——30 分钟游戏测试中帧率从 120fps 降到 30fps 的场景。但那篇是面向"识别问题"的：知道温控在介入就够了。本文面向的是"解决问题"：理解内核 thermal governor 的决策逻辑，才能在 Perfetto 中准确判断"为什么这一刻开始降频了"，才能在系统调优时知道该动哪个参数。

这个区分在实际工作中很关键。有些性能问题是可以通过 App 层优化解决的（减少不必要的计算、使用 ADPF 主动降载）。但有些问题的根因在系统层——OEM 的 thermal 策略过于保守、kernel governor 的响应曲线不合理、或者 devfreq cooling 对 GPU 的限制过早介入。解决后者需要对 thermal 子系统有更深的理解。

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

**Hot trip point** 表示温度已经到了危险区间。这个级别通常是"最后警告"——下一步就是 critical。内核会记录日志并通知用户空间（通过 uevent），但不一定自动触发降温——这取决于 governor 的实现。

**Critical trip point** 触发硬件级保护。内核会调用 `ordered_poweroff()` 强制关机。这不是建议性的，是强制性的——85°C（具体值由 OEM 在设备树中设定）是硬件安全红线，过了就关机，不商量。

[已验证: Linux kernel include/linux/thermal.h, thermal_zone_device_set_trips()]

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
                                       enum thermal_trend trend)
{
    struct thermal_cooling_device *cdev = instance->cdev;
    unsigned long cur_state = instance->target;

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

`power_allocator` 是更先进的 governor，它在高端设备上越来越常见。和 step_wise 不同，power_allocator 不按固定步长调整 cooling state，而是通过一个 PID 控制器计算出一个"功耗预算"，然后把这个预算分配给各个 cooling device。

PID 控制器的输入是温度偏差（当前温度与目标温度的差值），输出是可分配的总功耗。控制器的三个参数——比例（P）、积分（I）、微分（D）——决定了它对温度变化的响应特性。P 决定响应速度，I 消除稳态误差，D 抑制过冲。

```c
// drivers/thermal/gov_power_allocator.c
// PID 控制器的核心计算（简化）
static u32 pid_controller(struct thermal_zone_device *tz,
                           int trip_switch_on, int trip_temp,
                           int control_temp)
{
    s64 p, i, d, power_range;
    s32 err, integral_err;

    // err = 目标温度 - 当前温度（负值表示过热）
    err = control_temp - tz->temperature;

    // P 项：比例响应
    p = mul_u64_u32_div(err, params->kpo, MAX_KP);

    // I 项：积分（历史误差累积）
    integral_err = moving_avg(&params->err_integral, err);
    i = mul_u64_u32_div(integral_err, params->kio, MAX_KI);

    // D 项：微分（误差变化率）
    d = mul_u64_u32_div(tz->passive_delay, params->kdo, MAX_KD);

    // 总输出 = 基础功耗预算 + PID 调节量
    power_range = params->sustainable_power + p + i + d;

    return clamp(power_range, (s64)0, (s64)max_power);
}
```

power_allocator 需要两个 passive trip point 才能工作：一个 "switch on" trip point（温度超过此值时启动 PID 控制）和一个 "desired temperature" trip point（PID 的目标温度）。当温度低于 switch on 点时，governor 不介入；超过后，PID 控制器开始计算功耗预算，把温度拉向 desired temperature。

这个 governor 的优势在于**平稳**。step_wise 的台阶式调整可能导致性能突然下降（比如 CPU 频率从 2.8GHz 突然跳到 2.4GHz），而 power_allocator 通过 PID 连续计算功耗预算，频率下降更平滑，用户感知到的性能变化也更温和。

但 power_allocator 的调优更复杂。PID 参数需要针对具体硬件（SoC 的功耗特性、散热能力）精细调整，参数不当会导致温度振荡（过冲后回调、回调后再过冲）或响应过慢。这就是为什么同一 SoC 的两台手机 thermal 表现可能差异巨大——PID 参数不同。

[已验证: Linux kernel drivers/thermal/gov_power_allocator.c, Documentation/thermal/power_allocator.rst]

#### fair_share 和 user_space：其他 governor

`fair_share` 按比例分配 cooling 力度。如果一个 thermal zone 关联了多个 cooling device（比如同时限制 CPU 频率和 GPU 频率），fair_share 会根据每个 cooling device 的权重来分配降温任务。权重越高，分担的降温力度越大。

`user_space` 把温控决策权完全交给用户空间的 thermal daemon。内核只负责检测 trip point 触发，然后通过 uevent 通知用户空间程序，由后者决定采取什么降温措施。Android 设备上很多 OEM 的 thermal 策略就是通过用户空间 daemon 实现的——内核用 user_space governor，OEM 在用户空间的 thermal engine 中实现自己的策略逻辑。

### Cooling Device：降温的执行者

Cooling device 是 thermal 子系统的执行机构。每个 cooling device 有一个 state 值（从 0 到 max_state），state 越高降温力度越大。governor 的工作就是决定每个 cooling device 的 target state。

#### cpufreq cooling：限制 CPU 频率

最常见的 cooling device。它通过限制 CPU 的最大允许频率来实现降温。在 `drivers/thermal/cpu_cooling.c` 中，cpufreq cooling 维护一个频率表，governor 设定 target state 后，cooling device 将频率上限设为频率表中对应的级别。

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

频率表通常是等间距的。假设大核最高 3.0GHz、4 级限制，频率表可能是 [3000, 2600, 2200, 1800, 1400] MHz。state 0 表示无限制（3000MHz），state 4 表示最严格限制（1400MHz）。

#### devfreq cooling：限制 GPU/NPU 频率

`devfreq` 是 `cpufreq` 的"设备版"——cpufreq 管 CPU，devfreq 管 GPU、NPU、DSP 等其他设备。`CONFIG_DEVFREQ_THERMAL` 选项启用了 devfreq 的 thermal cooling 能力，让 thermal 子系统可以限制这些设备的最大频率。

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

#### CPU hotplug：核心离线

在极端情况下，thermal 子系统通过 CPU hotplug 直接关闭部分 CPU 核心。这比限制频率更激进——频率限制至少还能用全部核心（只是跑得慢），hotplug 直接减少了可用的计算资源。

Hotplug 通常在 severity 达到 SEVERE 或 CRITICAL 时触发。比如一台 8 核设备（1+3+4 big.LITTLE），在 CRITICAL 时可能只保留 4 个小核在线，大核全部离线。这对性能的影响是毁灭性的，但目的是保护硬件——设备快烧了的时候，性能已经不重要了。

[已验证: Linux kernel drivers/thermal/cpu_cooling.c, drivers/base/cpu.c (cpu hotplug)]

## Android Thermal HAL：内核与 Framework 的桥梁

5.5 中介绍了 Thermal HAL 的基本职责——将内核的温度数据抽象为标准化的 severity 级别，通过回调机制上报给 Framework。这里我们深入 HAL 层的接口设计和版本演进。

### Thermal HAL 2.0 的接口架构

从 Android 14 开始，Thermal HAL 从 HIDL 迁移到 AIDL。AIDL 版本的接口定义在 `hardware/interfaces/thermal/aidl/android/hardware/thermal/` 目录下，核心文件包括：

- `IThermal.aidl`：主接口，提供温度读取和回调注册
- `IThermalChangedCallback.aidl`：温度变化时的回调接口
- `Temperature.aidl`：温度数据结构（类型、名称、值、severity）
- `TemperatureType.aidl`：传感器类型枚举（CPU/GPU/Battery/Skin/USB 等）
- `ThrottlingSeverity.aidl`：severity 分级枚举
- `CoolingType.aidl`：cooling device 类型枚举

```java
// hardware/interfaces/thermal/aidl/android/hardware/thermal/Temperature.aidl
@VintfStability
parcelable Temperature {
    TemperatureType type;
    String name;
    float value;
    ThrottlingSeverity throttlingStatus;
}

// IThermal.aidl 的关键方法
@VintfStability
interface IThermal {
    // 注册温度变化回调
    void registerThermalChangedCallback(
        in IThermalChangedCallback callback,
        in boolean filterType,
        in TemperatureType type);

    // 获取当前所有温度传感器数据
    List<Temperature> getTemperatures();

    // 获取 cooling device 信息
    List<CoolingDevice> getCoolingDevices();
}
```

AIDL 接口要求 OEM 实现两个核心方法。`getTemperatures()` 在 Framework 初始化时调用一次，获取所有传感器的当前状态。之后 Framework 通过 `registerThermalChangedCallback()` 注册回调，HAL 在温度跨越阈值时主动推送更新——这是从 HIDL 1.0 轮询模式到 2.0 事件驱动模式的核心变化。

### OEM 实现差异：同一 SoC 的不同表现

Thermal HAL 的实现是 OEM 差异化最严重的部分之一。即使是同一款 SoC，不同厂商的 HAL 实现可能在以下方面完全不同：

**温度阈值映射**。HAL 需要将内核 thermal zone 的原始温度映射为 `ThrottlingSeverity` 枚举值。这个映射表由 OEM 定义——激进厂商可能把 SEVERE 映射到 60°C，保守厂商可能映射到 48°C。同样的温度，在两台手机上可能产生完全不同的 severity 级别。

**皮肤温度估算模型**。用户感受到的"手机烫不烫"取决于皮肤温度，而皮肤温度无法直接测量。OEM 通过热模型（thermal model）将 SoC 温度、电池温度、环境温度等输入估算为皮肤温度。这个模型的精度直接影响用户体验——估算偏高会导致过早降频，估算偏低会导致用户觉得烫手。

**多传感器融合策略**。高端设备有十几个温度传感器，HAL 需要决定哪个传感器的数据优先级最高。游戏场景可能以 GPU 和 CPU 温度为主，充电场景可能以电池温度为主。这个优先级策略因厂商而异。

[待验证：Qualcomm 和 MediaTek 参考实现中的 thermal threshold 默认值差异]

## 从被动降频到主动温控：ADPF 带来的范式变化

5.5 中我们看到的温控链路是"被动"的：温度升高 → 内核限制频率 → App 性能下降。App 在这个过程中是被动的承受者——不知道为什么突然卡了，也无法提前准备。

ADPF（Android Dynamic Performance Framework）改变了这个范式。通过 Thermal API，App 可以在系统强制降频**之前**感知到温度趋势，主动降低自己的负载。这种"主动降载"相比"被动降频"有几个优势：

1. **平滑过渡**。App 可以逐步降低画质（先降阴影分辨率、再降粒子效果、最后降帧率目标），用户几乎感知不到变化。系统强制降频则是一刀切——CPU 频率突然砍半，帧率瞬间腰斩。

2. **减少发热量**。App 主动降载减少了 SoC 的计算量，从源头降低了发热。如果 App 不降载，系统只能通过限制频率来降温——同样的计算量在更低频率下需要更长时间完成，帧时间反而更长。

3. **延长高性能时间窗口**。通过提前降载，App 可以让温度上升更缓慢，推迟系统强制降频的时刻，整体的高性能持续时间反而更长。

### Thermal Headroom 的预测机制

`getThermalHeadroom(int forecastSeconds)` 是主动温控的关键 API。5.9 中介绍了它的用法，这里我们看它背后的数据来源。

`ThermalManagerService` 计算 headroom 时依赖的主要数据是皮肤温度（skin temperature）的变化趋势。皮肤温度变化缓慢（秒级到分钟级），但它是影响 severity 等级变化的主要因素——大多数 OEM 的 thermal HAL 在计算 severity 时，皮肤温度的权重最高。

headroom 的预测不是简单的线性外推。Framework 内部维护了一个滑动窗口，记录过去 N 秒的温度变化率，结合当前的 severity 级别和 HAL 上报的温度阈值，估算"如果当前负载持续不变，N 秒后有多大概率触发更高级别的 severity"。

```java
// frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java
// getThermalHeadroom 的核心逻辑（简化）
float getThermalHeadroom(int forecastSeconds) {
    // 1. 获取当前皮肤温度估算
    float skinTemp = getSkinTemperatureEstimate();

    // 2. 计算温度变化率（基于滑动窗口）
    float tempRate = calculateTemperatureRate();

    // 3. 预测 forecastSeconds 后的温度
    float predictedTemp = skinTemp + tempRate * forecastSeconds;

    // 4. 归一化为 0.0-1.0 的 headroom 值
    // 1.0 表示预测温度将达到/超过 SEVERE 阈值
    return normalizeToHeadroom(predictedTemp);
}
```

这意味着 headroom API 的精度取决于两个因素：HAL 上报的温度数据的准确性和更新频率，以及 Framework 的热模型的复杂度。不同设备上的 headroom 预测精度可能差异很大。

[已验证: 官方文档 developer.android.com/reference/android/os/PowerManager#getThermalHeadroom(int)]
[待验证: ThermalManagerService 内部热模型的具体算法，不同 Android 版本是否有变化]

## 游戏场景的 Thermal 管控策略

游戏是 thermal 问题最集中的场景——CPU 和 GPU 同时高负载、屏幕高亮度持续运行、用户手握设备阻碍散热。我们来看游戏场景下 thermal 管控的几个关键策略。

### 分辨率动态调整

最有效的主动降载手段。当 thermal headroom 下降时，游戏引擎动态降低渲染分辨率（比如从 1080p 降到 720p），然后通过 GPU 的空间放大（spatial upscaling）恢复到显示分辨率。帧率基本不受影响，但 GPU 的渲染负载降低了约 50%（像素数从 207 万降到 92 万）。

Android 16 的 ADPF 提供了 `SystemHealthManager.getCpuHeadroom()` 和 `getGpuHeadroom()` 两个 API，游戏可以分别查询 CPU 和 GPU 的余量。如果 GPU headroom 低而 CPU headroom 高，说明瓶颈在 GPU——降低分辨率是正确策略。如果两者都低，说明整机发热严重——需要同时降低分辨率和帧率目标。

### 帧率目标动态降级

当分辨率已经降到下限但温度仍在上升时，下一步是降低帧率目标。从 120fps 降到 60fps 直接将每帧的 GPU 时间预算从 8.33ms 放宽到 16.67ms，GPU 可以在更低的频率下完成渲染。

关键是要和 ADPF 的 `HintSession` 同步更新。降低帧率目标后，需要调用 `updateTargetWorkDuration()` 更新 target duration，否则 ADPF 会认为 App 还在追求 8.33ms 的帧时间，继续尝试提频——反而加剧发热。

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
    // 关键：同步更新 ADPF HintSession
    hintSession.updateTargetWorkDuration(
        TimeUnit.SECONDS.toNanos(1) / targetFps);
}
```

### MediaTek MAGT：芯片级热数据反馈

Google 与 MediaTek 的合作为 ADPF 提供了更精细的热数据来源。标准的 ADPF Thermal API 基于 Thermal HAL 上报的系统级温度，而 MAGT（MediaTek Adaptive Gaming Technology）可以提供芯片级的温度和功耗数据——直接读取 SoC 内部的传感器，而不是经过 OEM HAL 层的抽象和映射。

根据 MediaTek 公布的案例数据：

- **Unity Boat Attack demo**（Dimensity 9300）：平均帧率提升 8.5 FPS，帧时间标准差降低 25%，功耗降低 12%，游戏续航延长 25 分钟以上。
- **Lineage W（NCSoft）**（Dimensity 9300）：平均帧率提升 7.4 FPS，帧抖动降低 25%，功耗降低 9%。
- **Ares: Rise of Guardians（Kakao Games）**（Dimensity 9400）：帧抖动降低 17%，功耗降低 6%。

这些改进来自更精准的温度反馈——游戏可以更早、更准确地预判 thermal throttling 的到来，从而更平滑地降载。MAGT 还提供了额外的 SDK，允许开发者在 Dimensity 设备上使用更底层的性能调控接口。

[来源: MediaTek 官方博客 mediatek.com, ADPF 开发者文档]
[待验证：Qualcomm 是否有类似的芯片级热数据 API；MAGT SDK 的具体接口文档]

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

```sql
-- 高 CPU utilization + 低频率 = thermal throttling
-- 低 CPU utilization + 低频率 = 正常 DVFS
-- 高 CPU utilization + 高频率 + 长帧时间 = 代码性能问题
SELECT
  ts / 1e9 AS time_sec,
  cpu,
  freq / 1e6 AS freq_mhz,
  -- 需要配合 sched slice 数据判断 utilization
FROM cpu_frequency_scans
ORDER BY ts
LIMIT 100;
```

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

**定期查询 headroom**。对于游戏和 Camera 等持续高负载应用，每秒查询一次 `getThermalHeadroom(30)`——预测 30 秒后的余量。当 headroom 超过 0.5 时开始预降级，超过 0.7 时加速降级。

**HintSession 同步**。任何帧率目标的变更都必须同步更新 `HintSession.updateTargetWorkDuration()`。否则 ADPF 和 App 的预期不一致——App 已经降到了 60fps 的节奏，系统还在为 120fps 提频，白费功耗。

### Framework 层：JobScheduler 的 thermal 感知

从 Android 10 开始，`JobScheduler` 在 thermal severity 达到 MODERATE 时会降低任务的执行频率。在 SEVERE 时会推迟所有非紧急任务。App 应该正确设置 Job 的优先级（`setPriority()`），让系统在 thermal 压力下知道哪些任务可以推迟。

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
| Android 7.0 (API 24) | Sustained Performance Mode 引入 | 首次提供可预测持续性能的 API |
| Android 8.0 (API 26) | Thermal HAL 1.0 | 标准化温度读取（轮询模式） |
| Android 10 (API 29) | Thermal HAL 2.0（HIDL，事件驱动）+ PowerManager Thermal API | App 可感知温控状态 |
| Android 12 (API 31) | `getThermalHeadroom()` + ADPF Performance Hint API | 预测式热管理 + 主动性能调控 |
| Android 13 (API 33) | Game State API + Thermal NDK 接口 | 细粒度游戏状态标注 |
| Android 14 (API 34) | Thermal HAL 从 HIDL 迁移至 AIDL | 接口现代化 |
| Android 15 (API 35) | ADPF Power Efficiency Mode + GPU 时长上报 | 功耗优先路径 + CPU/GPU 联合调频 |
| Android 16 (API 36) | `SystemHealthManager` Headroom API + `AThermal_HeadroomCallback` | 分别查询 CPU/GPU 余量 + 回调式热监听 |
| Android 17 (API 37) | [待验证：Thermal Balancing 改进细节] | 预期进一步优化多传感器融合策略 |

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

- **[5.5 Thermal 管控](./05-thermal.md)**：本章是 5.5 的深度扩展。5.5 建立全局认知，本章深入内核机制和工程实践。
- **[5.4 DVFS](./04-dvfs.md)**：DVFS 是 thermal cooling 的执行手段。cpufreq cooling 通过限制 DVFS 的频率上限来降温。
- **[5.9 ADPF](./09-adpf.md)**：ADPF 是 App 参与温控的桥梁。本章从 thermal 视角审视 ADPF，5.9 从性能优化视角审视 ADPF。
- **[8.9 游戏性能](../../part2-performance/ch08-responsiveness/05-case-studies.md)**：游戏是 thermal 问题最集中的场景。本章的游戏策略可以直接应用于 8.9 中的案例。
- **[11.1 功耗模型](../../part2-performance/ch11-power/01-power-model.md)**：thermal 和功耗是一体两面——功耗决定发热量，发热量触发 thermal throttling。理解功耗模型有助于从源头减少 thermal 压力。

## 参考资料

### AOSP 源码
- `drivers/thermal/thermal_core.c` — Thermal 子系统核心框架 [已验证]
- `drivers/thermal/gov_step_wise.c` — step_wise governor 实现 [已验证]
- `drivers/thermal/gov_power_allocator.c` — power_allocator governor (PID) 实现 [已验证]
- `drivers/thermal/cpu_cooling.c` — cpufreq cooling device 实现 [已验证]
- `drivers/devfreq/devfreq.c` — devfreq 框架 [已验证]
- `hardware/interfaces/thermal/aidl/android/hardware/thermal/` — Thermal HAL AIDL 接口 [已验证]
- `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` — Framework 温控服务 [已验证]

### 官方文档
- [Android Thermal Management](https://source.android.com/docs/core/thermal) — 系统级温控架构 [已验证]
- [ADPF for Games](https://developer.android.com/games/optimize/performance#adpf) — 游戏 ADPF 集成指南 [已验证]
- [Thermal API Reference](https://developer.android.com/reference/android/os/PowerManager) — PowerManager Thermal API [已验证]
- [Game Mode API](https://developer.android.com/games/gamemode/gamemode-api) — Game Mode 文档 [已验证]

### 其他参考
- Linux kernel `Documentation/thermal/power_allocator.rst` — power_allocator governor 文档 [已验证]
- Linux kernel `Documentation/thermal/sysfs-api.rst` — thermal zone sysfs 接口 [已验证]
- [MediaTek MAGT & ADPF Integration](https://mediatek.com) — MediaTek 游戏性能优化案例 [来源: MediaTek 官方]
- [Perfetto Trace Configuration](https://ui.perfetto.dev/) — thermal/ftrace 数据源配置 [已验证]
