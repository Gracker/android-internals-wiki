---
title: "Thermal 管控"
section: "5.5"
chapter: "5.5"
status: ready-for-review
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-01"
last_verified_against: "AOSP android-14.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java"
  - type: aosp
    path: "hardware/interfaces/thermal/2.0/IThermal.hal"
  - type: aosp
    path: "hardware/interfaces/thermal/2.0/types.hal"
  - type: aosp
    path: "hardware/interfaces/thermal/aidl/android/hardware/thermal/"
  - type: official
    path: "developer.android.com/reference/android/os/PowerManager#THERMAL_STATUS_NONE"
  - type: official
    path: "source.android.com/docs/core/thermal"
  - type: official
    path: "developer.android.com/games/optimize/thermal"
  - type: official
    path: "developer.android.com/games/optimize/adpf"
related_chapters: ["5.1", "5.2", "5.3", "5.4", "5.6", "7.3"]
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2"
polish_count: 2
polish_date: "2026-04-08"
polish_by: "task2b-polish"
tags:
  - android
  - power
  - research
  - thermal
  - throttling
  - dvfs
  - cpu-frequency
reviewed_date: "2026-04-15"
reviewed_by: "openclaw-task6"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_date: "2026-04-17"
task9_reviewed_by: "openclaw-task9"
pipeline_stage: task2b_pending
---


# Thermal 管控

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Thermal 管控链路：温度传感器 → Thermal HAL → thermal engine → 限频/限核
- 🔹 Android Thermal API（PowerManager.THERMAL_STATUS_*）
- 🔹 温度墙（Thermal Throttling）对性能的影响：持续高负载场景的帧率下降
- 🔹 Thermal Mitigation 策略：限频、限核、降亮度、关闭功能
- 🔹 如何在性能测试中排除温控干扰

### 扩展（可选深入）

- 🔸 各厂商 Thermal 策略差异（激进 vs 保守）
- 🔸 Sustained Performance Mode API
- 🔸 散热方案（石墨烯、VC 均热板）对性能稳定性的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要了解 Thermal 管控

做过持续性能测试的工程师大概率遇到过这种情况——比如跑一个 30 分钟的游戏场景或者反复滑动列表：前 5 分钟帧率稳稳的 120fps，第 10 分钟开始偶尔掉帧，到了第 20 分钟帧率直接腰斩，CPU 频率也莫名其妙地降了下来。第一反应往往是“代码有 bug”，但换一台冷启动的设备，表现完全正常。

这不是代码的问题，而是设备的温控系统开始介入了。

在 Perfetto 中，这种场景的 Trace 非常有辨识度：CPU Frequency 轨迹线一开始在高频区间，随后逐步下探，像一只慢慢放气的气球。与此同时，帧渲染时间（Frame Timeline）从稳定的 8.33ms 一路飘升到 16ms、20ms 甚至更高。这就是 Thermal Throttling——温度墙——对性能最直接的影响。

了解温控系统的运作方式，对性能优化工程师来说是刚需。不是因为我们要去"关闭温控"——那是危险且不负责任的做法——而是因为：

1. **我们需要区分温控导致的性能下降和代码缺陷导致的性能下降**。搞混了这两者，优化方向完全跑偏。
2. **在性能测试中，温控是最大的干扰变量**。不知道温控什么时候介入，benchmark 数据就没有可比性。
3. **App 层面的主动配合**。Android 提供了 Thermal API 让应用感知温度状态，在高负载场景（游戏、视频编码、AR）中主动降级，比被系统强制降频体验好得多。

## Thermal 管控链路：从传感器到限频

Android 的温控是一个分层架构，从底层硬件传感器一直到上层 Framework 服务，形成一条完整的管控链路。我们先从全局看这条链路长什么样，然后逐层拆解。

[图：Thermal 管控链路全景——温度传感器 → Kernel Thermal Core → Thermal HAL → ThermalManagerService → App/系统组件]

### 温度传感器：数据的源头

手机内部布满了温度传感器，它们分布在 SoC 的各个关键位置。常见的传感器位置包括：

- **CPU 各个 cluster**：大核 cluster 和小核 cluster 通常有独立的温度传感器，因为大小核的功耗和发热特性差异很大。
- **GPU**：GPU 在游戏等场景是发热大户，需要独立监控。
- **电池**：电池温度直接关系到安全，锂电池超过一定温度（通常 45°C-60°C）就需要强制保护。
- **皮肤（Skin）**：用户能感知到的设备表面温度。这个温度不是直接测量的，而是通过 SoC 温度、电池温度等通过热模型估算出来的。
- **USB/充电 IC**：快充时充电电路也是发热源。

在 Linux 内核中，这些传感器通过 `sysfs` 接口暴露，路径通常在 `/sys/class/thermal/` 下。每个 `thermal_zone` 对应一个传感器，其中 `temp` 文件保存当前温度值（单位通常是毫摄氏度）。

```
# 查看 SoC 上所有 thermal zone 的温度
$ cat /sys/class/thermal/thermal_zone*/temp
45000    # 45.0°C — CPU cluster 0
52000    # 52.0°C — CPU cluster 1
38000    # 38.0°C — GPU
41000    # 41.0°C — Battery
```

[已验证: AOSP thermal zone sysfs 接口, Linux kernel Documentation/thermal/sysfs-api.rst]

### 内核 Thermal Core：第一道防线

Linux 内核自带一套 thermal management 框架，位于 `drivers/thermal/`。它的核心概念是 **Thermal Zone**（温度监控区域）和 **Cooling Device**（降温设备）。

每个 Thermal Zone 定义了多个温度阈值（trip point），当温度跨越这些阈值时，内核会通知对应的 Cooling Device 采取行动。一个典型的 trip point 配置看起来是这样的：

| Trip Point | 温度阈值 | 动作 |
|-----------|---------|------|
| passive | 55°C | 开始被动降温（限制 CPU 频率） |
| hot | 65°C | 激进降频 |
| critical | 85°C | 触发硬件关机保护 |

Cooling Device 不一定是物理设备——更常见的"降温设备"就是 CPU 本身。内核通过限制 CPU 的最高运行频率来实现降温，这被称为 **cpufreq cooling**。在 `drivers/thermal/cpu_cooling.c` 中，cpufreq cooling 会动态调整 CPU 的最大允许频率：当温度升高时，逐步降低 `max_freq`；温度回落后，再逐步恢复。

这就是为什么我们在 Perfetto 中看到 CPU 频率下降时，往往伴随着温度的上升——与 governor（如 schedutil）基于 utilization 的主动调频不同，thermal cooling 是在强制压低频率上限。

[已验证: Linux kernel drivers/thermal/cpu_cooling.c, of-thermal.c]

### Thermal HAL：硬件抽象层

内核的 thermal core 够用了，但 Android 有自己的需求——Framework 需要统一管理温控策略，而不同厂商的硬件差异很大。Thermal HAL 就是这层抽象。

**Thermal HAL 1.0（Android 9 及更低版本）** 采用轮询（polling）方式获取温度，这是最早的标准化 Thermal HAL 版本。Framework 定期调用 HAL 的 `getTemperatures()` 方法来读取各传感器数据。这种方式简单但效率低，而且延迟大——两次轮询之间可能错过了温度的快速上升。

**Thermal HAL 2.0（Android 10+）** 引入了事件驱动的接口。当温度跨越阈值时，HAL 主动向 Framework 上报 `ThrottlingSeverity` 变化，而不是等 Framework 来问。从 Android 14 开始，HAL 接口从 HIDL 迁移到 AIDL（`android.hardware.thermal.IThermal`），但核心模型不变。

HAL 层定义的关键数据结构在 `hardware/interfaces/thermal/2.0/types.hal` 中：

```c
// HIDL types.hal — TemperatureType：传感器类型
enum TemperatureType : int32_t {
    UNKNOWN = -1,
    CPU = 0,
    GPU = 1,
    BATTERY = 2,
    SKIN = 3,
    USB_PORT = 4,
    POWER_AMPLIFIER = 5,
    ...
};

// ThrottlingSeverity：温控严重程度
enum ThrottlingSeverity : int32_t {
    NONE = 0,
    LIGHT = 1,
    MODERATE = 2,
    SEVERE = 3,
    CRITICAL = 4,
    EMERGENCY = 5,
    SHUTDOWN = 6,
};

// Temperature：一个传感器的完整温度状态
struct Temperature {
    TemperatureType type;
    string name;
    float value;                // 当前温度
    ThrottlingSeverity throttlingStatus;  // 当前温控状态
};
```

`ThrottlingSeverity` 从 `NONE` 到 `SHUTDOWN` 共 7 个级别，每个级别对应不同的系统行为。HAL 层把温度传感器的原始数据映射为这套标准化的 severity 分级，上游的 ThermalManagerService 就基于这套分级来协调系统响应。

[已验证: AOSP hardware/interfaces/thermal/2.0/types.hal @ android-14.0.0_r1]

### ThermalManagerService：Framework 的温控中枢

在 Framework 层，`ThermalManagerService`（`frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java`）是温控系统的中枢。它做三件事：

1. **接收 HAL 上报的温控事件**。ThermalManagerService 通过 `IThermalEventListener` 回调接口接收 Thermal HAL 推送的 severity 变化。
2. **将 severity 广播给系统组件和 App**。内部组件通过 `IThermalEventListener` 接收；App 通过 `IThermalStatusListener`（封装为 `PowerManager.OnThermalStatusChangedListener`）接收。
3. **执行系统级降温动作**。当 severity 升高到一定程度时，ThermalManagerService 会触发一系列系统级行为，比如限制 JobScheduler 的执行、降低屏幕亮度、甚至触发 Framework 层的关机流程。

整条链路可以概括为：**传感器感知温度 → 内核 thermal core 做第一道硬件级保护 → Thermal HAL 将温度状态抽象为 severity 级别 → ThermalManagerService 协调系统响应 → App 通过 API 感知并自适应。**

## Android Thermal API：应用如何感知温度

Android 从 API 29（Android 10）开始正式向应用层暴露温控状态。这些 API 都挂在 `PowerManager` 类上。

### 获取当前温控状态

```java
// 获取当前 thermal status（轮询方式）
PowerManager pm = getSystemService(PowerManager.class);
int status = pm.getCurrentThermalStatus();
```

`getCurrentThermalStatus()` 返回一个整数，对应 `PowerManager` 中的常量：

| 常量 | 值 | 含义 | 对用户体验的影响 |
|------|---|------|----------------|
| `THERMAL_STATUS_NONE` | 0 | 没有温控 | 无 |
| `THERMAL_STATUS_LIGHT` | 1 | 轻度限制 | 基本无感知 |
| `THERMAL_STATUS_MODERATE` | 2 | 中度限制 | 轻微影响 |
| `THERMAL_STATUS_SEVERE` | 3 | 严重限制 | 显著影响（掉帧、卡顿） |
| `THERMAL_STATUS_CRITICAL` | 4 | 极限限制 | 所有省电措施已启用 |
| `THERMAL_STATUS_EMERGENCY` | 5 | 紧急状态 | 关键组件开始关闭（如调制解调器） |
| `THERMAL_STATUS_SHUTDOWN` | 6 | 即将关机 | 设备即将关机 |

[已验证: 官方文档 developer.android.com/reference/android/os/PowerManager]

### 注册温控状态变化监听

轮询方式不推荐——温控状态变化是一个低频事件，每秒查询一次纯属浪费。推荐使用回调方式：

```java
PowerManager pm = getSystemService(PowerManager.class);
Executor executor = ContextCompat.getMainExecutor(this);

pm.addThermalStatusListener(executor, status -> {
    switch (status) {
        case PowerManager.THERMAL_STATUS_NONE:
            // 恢复正常，可以使用全性能
            break;
        case PowerManager.THERMAL_STATUS_LIGHT:
            // 开始注意，可以减少一些非必要的后台工作
            break;
        case PowerManager.THERMAL_STATUS_MODERATE:
            // 主动降低画质、减少帧率目标
            break;
        case PowerManager.THERMAL_STATUS_SEVERE:
            // 大幅降低负载，优先保基本可用
            break;
        case PowerManager.THERMAL_STATUS_CRITICAL:
        case PowerManager.THERMAL_STATUS_EMERGENCY:
            // 停止一切非必要操作，准备关机
            break;
    }
});
```

这个回调是在 `ThermalManagerService` 收到 HAL 的 severity 变化通知后触发的，延迟通常在几百毫秒以内。

### 预测温控余量（getThermalHeadroom）

Android 12（API 31）引入了一个更前瞻性的 API：`getThermalHeadroom(int forecastSeconds)`。它返回一个 0.0 到 1.0 的浮点数，表示距离达到 `SEVERE` 状态还有多少余量——1.0 意味着已经处于 SEVERE 状态。

```java
// 查询当前的热余量
float headroom = pm.getThermalHeadroom(0);  // 当前状态
float headroom5s = pm.getThermalHeadroom(5); // 预测5秒后的状态
```

这个 API 的使用场景主要是游戏：游戏引擎可以在每帧的更新循环中查询 thermal headroom，当余量低于某个阈值时，主动降低渲染分辨率或帧率目标——与其等到系统强制降频导致突然卡顿，不如自己平滑地降低负载。

需要注意几点：

- 这个 API 主要跟踪的是慢变化传感器（如皮肤温度），而不是 CPU 瞬时温度。所以它反映的是一种"趋势"而非"瞬时状态"。
- 不要频繁调用——官方建议每秒最多调用一次。调用过于频繁，API 会返回 `NaN`。
- 首次调用返回 `NaN` 表示设备不支持此 API。

[已验证: 官方文档 developer.android.com/reference/android/os/PowerManager#getThermalHeadroom(int)]

## 温度墙对性能的影响：从 Trace 中看 Thermal Throttling

了解完 API 层面，我们回到性能工程师的视角——在 Perfetto 中，温控介入是什么样子？

### 典型的 Thermal Throttling Trace

设想一个场景：我们用 Perfetto 抓了一段 5 分钟的游戏运行 Trace。设备从冷启动开始（环境温度 25°C），游戏设定 60fps 目标帧率。

在前 2 分钟，一切正常：
- CPU 频率稳定在大核 2.8GHz、小核 1.8GHz
- 帧渲染时间稳定在 12-14ms（有裕量）
- 各 thermal zone 温度逐步上升

第 3 分钟开始，Trace 出现变化：
- CPU 频率先从 2.8GHz 降到 2.4GHz，然后逐步降到 1.8GHz
- 帧渲染时间从 14ms 开始上升，部分帧超过 16.67ms（掉帧出现）
- `thermal_zone` 的温度曲线接近阈值线

第 4-5 分钟，情况加剧：
- CPU 频率被压到 1.2GHz 甚至更低
- 帧渲染时间飘到 20-30ms，帧率从 60fps 降到 30-40fps
- SurfaceFlinger 的 VSYNC-app 和 VSYNC-sf 的间距变大（因为帧处理变慢）

[图：典型的 Thermal Throttling Trace 示意——前段稳定 → 中段频率逐步下降 → 后段帧率显著下降]

### 如何在 Perfetto 中确认 Thermal Throttling

如果我们怀疑一次掉帧是温控导致的，可以在 Perfetto 中用以下方法验证：

**1. 查看 CPU Frequency Track**

这是最直观的证据。在 Perfetto 中展开 CPU 区域，每个核心下方都有一条「CPU Frequency」轨迹。如果这条线在高负载期间反而向下走——区别于正常的 DVFS 波动，这种持续性的频率下探——大概率是 thermal throttling。

**2. 启用 thermal 数据源**

在抓取 Trace 时，在 Perfetto 配置中启用 `linux.sys_stats` 数据源的 `thermal_period_ms` 选项：

```protobuf
data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      thermal_period_ms: 1000  // 每秒采样一次 thermal zone 温度
      cpufreq_period_ms: 1000
    }
  }
}
```

这样 Perfetto 会记录每个 thermal zone 的温度变化，我们可以在 Trace 中直接看到温度曲线，和 CPU 频率曲线叠加对比。

**3. 通过 ftrace 事件追踪**

内核的 thermal 子系统会产生 ftrace 事件。在 Perfetto 配置中添加：

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "thermal/thermal_temperature"
      ftrace_events: "thermal/thermal_zone_trip"
      ftrace_events: "power/cpu_frequency"
    }
  }
}
```

`thermal_zone_trip` 事件会告诉我们哪个 thermal zone 跨越了哪个 trip point——这是确认温控介入的"实锤"。

[已验证: Perfetto 官方文档 ui.perfetto.dev, data source 配置参考]

### DVFS 降频 vs Thermal 降频：怎么区分？

这里有一个容易混淆的点。我们在 [5.4 DVFS 与功耗管理](./04-dvfs.md) 中讨论过，schedutil governor 会根据 CPU utilization 主动调节频率。高负载时升频，低负载时降频——这是正常的 DVFS 行为，不涉及温控。

Thermal 降频是另一种机制：它是 **强制性的频率上限约束**。即使 CPU utilization 很高，thermal cooling 也会把频率限制在某个上限以下。

在 Perfetto 中区分两者的方法：

- **DVFS 降频**：CPU utilization 低 → 频率降低。这是正常的，频率和负载同步变化。
- **Thermal 降频**：CPU utilization 高 → 频率反而降低。频率和负载"反着来"，这就是温度墙在起作用。

如果我们看到高负载期间频率反而比空闲时低，基本可以确认是 thermal throttling。

## Thermal Mitigation 策略：系统如何降温

当温度升高到触发阈值时，系统不是一刀切地"把 CPU 降到最低"。实际的 mitigation 策略是分级的、渐进的，而且涉及多个子系统。

### 限频（CPU Frequency Capping）

这是最核心的手段。内核的 cpufreq cooling 会设置一个动态的频率上限。当 severity 从 LIGHT 升到 MODERATE 再到 SEVERE，频率上限逐步降低。

以一个典型的高端 SoC 为例（大核最高频率 3.0GHz）：

| Severity | 大核频率上限 | 小核频率上限 | 效果 |
|----------|------------|------------|------|
| NONE | 3.0 GHz | 2.0 GHz | 无限制 |
| LIGHT | 2.6 GHz | 1.8 GHz | 轻微影响 |
| MODERATE | 2.0 GHz | 1.5 GHz | 明显影响 |
| SEVERE | 1.4 GHz | 1.0 GHz | 严重影响 |

### 限核（CPU Isolation / Hotplug）

在更极端的情况下，系统会直接关闭某些 CPU 核心。这比限频更激进——频率可以慢慢恢复，但核心的上下线涉及更重的调度切换成本。

内核通过 CPU hotplug 机制实现核心隔离。在 Android 上，这通常在 severity 达到 SEVERE 或 CRITICAL 时触发。比如一台 8 核设备（1+3+4），可能在 CRITICAL 时只保留 4 个小核在线。

### 降低屏幕亮度

屏幕是手机最大的发热源之一（尤其在高端 OLED 屏幕上）。当温度升高时，系统会降低屏幕亮度上限。我们可能遇到过这种情况：在大太阳底下用手机，突然屏幕变暗了而且拉不上去——这就是 thermal mitigation 在限制亮度。

这个行为由 `DisplayManagerService` 配合 `ThermalManagerService` 实现。具体的亮度降低曲线因厂商而异。

### 关闭非必要功能

在更高的 severity 级别，系统开始关闭非核心功能：

- **SEVERE**：限制后台 JobScheduler 任务执行频率
- **CRITICAL**：降低扫描频率（如 Wi-Fi 扫描、BLE 扫描），减少非必要唤醒
- **EMERGENCY**：关闭调制解调器（radio）、停止充电、关闭 NFC 等外设

### 限制充电电流

充电本身会产生热量。当电池温度过高时，系统会降低充电电流甚至暂停充电。这个逻辑通常在充电 IC 的固件中实现，但也受 Thermal HAL 的控制。

[已验证: AOSP ThermalManagerService.java @ android-14.0.0_r1, 官方文档 source.android.com/docs/core/thermal]

## 如何在性能测试中排除温控干扰

这是性能工程师最关心的实操问题。温控是性能测试中最大的不可控变量——同一台设备，冷机第一次跑和热机第三次跑，结果可能差 30%。以下是在测试中控制温控影响的几种策略。

### 策略 1：每次测试前充分冷却

最简单直接的方法。每次测试前让设备静置冷却，直到所有 thermal zone 的温度回到接近环境温度。通常需要 5-10 分钟（取决于设备散热能力和前一次测试的负载强度）。

可以用 adb 命令监控温度：

```bash
# 持续监控 CPU 温度
watch -n 1 "cat /sys/class/thermal/thermal_zone*/temp"
```

当温度稳定在环境温度 ±2°C 范围内时，开始下一次测试。

### 策略 2：使用 Sustained Performance Mode

Android 7.0（API 24）引入的 Sustained Performance Mode，从一开始就把最高频率限制在一个"能持续 30 分钟不掉"的水平，避免先跑满再降频的断崖式下跌。设计理念是"稳定的平庸好过短暂的卓越"——benchmark 测试的 30 分钟数据不会因为温控介入而出现大的波动。

前提条件是设备厂商必须在 Power HAL 中实现 `POWER_HINT_SUSTAINED_PERFORMANCE`，并通过 `PowerManager.isSustainedPerformanceModeSupported()` 声明支持。很多中低端设备并不支持。具体 API 用法和 CTS 要求见下文 [Sustained Performance Mode API](#sustained-performance-mode-api) 小节。

### 策略 3：使用 Fixed Performance Mode（Benchmark 专用）

Android Dynamic Performance Framework (ADPF) 提供了 Fixed Performance Mode，专门用于 benchmark。启用后，CPU 和 GPU 频率固定在一个预设值，不会因为 DVFS 或 thermal 而变化。

```java
// ADPF 的 Performance Hint Manager 可用于固定性能模式
// 具体接口参考 developer.android.com/games/optimize/adpf
```

这个模式适合横向对比不同设备或不同版本的性能差异——消除了 DVFS 和 thermal 的影响后，纯粹比较代码执行效率。

### 策略 4：记录温控状态作为测试元数据

如果我们无法完全消除温控影响（比如在真实用户场景测试中），至少要把温控状态记录下来。在测试开始和结束时分别读取 thermal status：

```java
PowerManager pm = getSystemService(PowerManager.class);
int statusBefore = pm.getCurrentThermalStatus();
// ... 运行测试 ...
int statusAfter = pm.getCurrentThermalStatus();
// 记录到测试报告中
```

如果测试过程中 thermal status 从 NONE 变到了 MODERATE 甚至 SEVERE，那么这次测试的数据应该打上标记，和其他"全程 NONE"的测试数据区分处理。

### 策略 5：物理辅助散热

在实验室环境下，可以用散热背夹、风扇直吹、或者把设备放在空调出风口等物理手段辅助散热。这不是"作弊"——只要每次测试的条件一致，数据就有可比性。

但要注意：不同的散热条件会影响 SoC 内部的温度分布。强制风冷可能让表面温度很低，但 SoC 内部某些热点并没有被有效冷却。所以物理散热只是减少温控触发的概率，并不能完全消除。

## 各厂商 Thermal 策略差异

前面讨论的都是 Android 通用架构。但在实际工作中我们会发现，同样 SoC 的两台手机，性能表现可能天差地别——差异往往来自厂商各自的温控策略调校。温控策略是厂商差异化最严重的领域之一。同样是 Snapdragon 8 Gen 3，不同手机厂商的 thermal 配置可能截然不同——激进者允许更高的温度上限以换取持续高性能，保守者在较低温度就开始降频以保护用户体验和硬件安全。

### 策略风格的光谱

**激进型**（常见于游戏手机和性能旗舰）：
- 温度阈值设置较高（如 SEVERE 阈值设在 55°C 以上）
- 频率上限放宽，允许更长的高性能时间窗口
- 可能配备更好的散热材料（VC 均热板、石墨烯）作为硬件补偿
- 代表机型：ROG Phone 系列、红魔系列

**保守型**（常见于注重日常体验的品牌）：
- 温度阈值较低（如 SEVERE 阈值可能设在 45-48°C）
- 早期介入、缓慢降频，避免用户感知到突然的性能下降
- 更注重皮肤温度（用户手感）而非 SoC 温度
- 代表机型：部分 Samsung 和 Apple 机型

**均衡型**（大多数主流机型）：
- 根据使用场景动态调整策略（游戏时允许更高温度，日常使用更保守）
- 通过 Performance Hint API 接收 App 的性能需求信号

[待验证：具体机型的温度阈值参数因厂商私有配置，难以从公开资料中精确验证]

这种差异对性能工程师意味着：**同一份 benchmark 数据在不同厂商的设备上可能反映的未必是代码性能差异，更可能是温控策略差异**。做跨设备对比时，务必关注 thermal status 的变化。

## Sustained Performance Mode API

上文测试策略中提到 Sustained Performance Mode 可以排除温控干扰，这里从 API 设计和实现层面展开它的工作机制。

Sustained Performance Mode 从 Android 7.0 开始引入，核心设计目标只有一个：让设备能够在一个固定的性能水平上持续运行至少 30 分钟。CTS 测试要求是：开启此模式后，30 分钟内帧率变化不超过 5%，且帧率不能低于未开启模式时的水平。

它的工作原理是在 Power HAL 层面限制最高频率——从测试一开始就设定一个"可持续频率"，然后在整个运行期间保持不变。这样做的代价是初始性能低于最大频率，但换来了长时间的性能稳定。

```java
// 检查设备是否支持
PowerManager pm = getSystemService(PowerManager.class);
boolean supported = pm.isSustainedPerformanceModeSupported();

// 启用
if (supported) {
    getWindow().setSustainedPerformanceMode(true);
}
```

[已验证: 官方文档 developer.android.com, CTS 测试要求]

## 散热方案对性能稳定性的影响

温控策略解决的是“温度高了怎么办”，而散热方案决定的是“温度高到什么程度才需要管”。温控策略是软件层面的事，但决定温控介入频率的根本因素是硬件散热能力。近年来手机散热技术的进步，直接影响了性能工程师的工作方式。

### 石墨散热片

最基础的散热方案。利用石墨的高导热性，将 SoC 的热量快速分散到更大面积上。几乎所有手机都使用石墨片，但面积和层数不同。优点是轻薄、便宜；缺点是只能均热，不能主动把热量排出机身。

### VC 均热板（Vapor Chamber）

中高端手机的标配。VC 内部有工质（通常是水），通过相变（蒸发→冷凝）循环来高效传热。散热效率是纯铜的 10 倍以上。VC 面积越大，散热效果越好——这就是为什么同样 SoC 的手机，散热面积大的性能更持久。

### 石墨烯

近年来开始采用的先进散热材料。导热系数高于传统石墨片，可以做得更薄更轻。一些旗舰机型宣称使用"超大石墨烯散热膜"来提升散热面积。

### 散热对性能工程师的意义

散热方案影响的是"温控介入的时间点"。同样的 SoC、同样的负载：

- 散热好的设备：5 分钟后才开始 thermal throttling
- 散热差的设备：2 分钟就开始降频

这不是软件能改变的因素，但性能工程师需要知道：**在评估"性能下降"问题时，先排除散热条件差异**。比如用户反馈"更新后游戏变卡了"，可能只是这次测试时环境温度比上次高，或者测试前设备没有充分冷却。

[待验证：石墨烯和 VC 均热板的具体散热参数因厂商规格而异，此处为通用描述]

## 版本演进速览

Thermal 管控在 Android 各版本中有几项关键变化，这里做一个梳理：

| Android 版本 | 变化 | 影响 |
|-------------|------|------|
| 7.0 (API 24) | 引入 Sustained Performance Mode | 首次提供可预测持续性能的 API |
| 9 (API 28) | Thermal HAL 1.0（轮询模式） | 标准化温度读取接口 |
| 10 (API 29) | Thermal HAL 2.0（事件驱动）+ PowerManager Thermal API | App 可感知温控状态 |
| 12 (API 31) | `getThermalHeadroom()` API | 支持前瞻性热余量预测 |
| 14 (API 34) | Thermal HAL 从 HIDL 迁移至 AIDL | 接口现代化，无功能变化 |
| 15 (API 35) | ADPF thermal headroom hint 精度提升 [待验证] | 游戏场景热管理更精细 |
| 16 (API 36) | ADPF Game Mode API 扩展，与温控协同增强 [待验证] | 更多性能-温控协调能力 |

这些版本节点的共同趋势是：从被动响应走向主动感知，从系统独占走向应用参与。Android 希望应用不只是温控的“被动承受者”，而是能主动配合降载的“合作方”。

## 常见问题与误区

### 误区 1："手机发烫是 App 的 bug"

手机发烫是 SoC 在高负载下的物理必然。App 能做的是减少不必要的计算，但只要用户在玩游戏、看高码率视频、用 AR 应用，SoC 就会发热。真正的"bug"是后台偷偷跑高负载（如死循环、频繁 GC、持续定位），这些可以通过 Trace 分析定位。

### 误区 2："Root 后关掉温控就能一直满血"

这是极其危险的做法。温控是硬件保护机制，关闭温控可能导致 SoC 温度超过安全阈值（通常 85-95°C），轻则硬件加速老化，重则直接烧毁。短期测试可以放宽温控阈值，但绝对不能在生产环境中关闭。

### 误区 3："Thermal API 只对游戏有用"

虽然游戏是 Thermal API 最主要的使用者，但任何长时间高负载的应用都应该关注温控状态。比如视频编辑应用（长时间编码）、导航应用（GPS + 屏幕 + 语音同时工作）、AR 应用（摄像头 + GPU + 传感器全开）。当 thermal status 升高时，这些应用也应该主动降低负载。

### 误区 4："Sustained Performance Mode 会降低性能"

不完全准确。Sustained Performance Mode 降低的是**峰值性能**，但提升了**持续性能**。对于长时间运行的场景（30 分钟+），它提供了更稳定的体验。只有短时间 burst 场景（如应用启动）才会感觉到峰值性能的损失。

## 与其他章节的关联

- **[5.4 DVFS 与功耗管理](./04-dvfs.md)**：DVFS 是温控的执行手段之一。Thermal cooling 通过限制 DVFS 的频率上限来降温。了解 DVFS 机制有助于区分"正常调频"和"thermal 降频"。
- **[5.3 大小核架构](./03-big-little.md)**：Thermal mitigation 的"限核"操作直接影响大小核的在线核心数，进而影响 EAS 调度决策。
- **[5.6 Android 功耗管理](./06-android-power.md)**：温控是功耗管理的子系统之一。WakeLock、Doze、App Standby 管的是"谁在用电"，温控管的是"电用多了怎么办"。
- **[7.3 卡顿分析方法论](../../part2-performance/ch07-smoothness/03-jank-methodology.md)**：卡顿分析中，温控导致的掉帧需要和代码缺陷导致的掉帧区分开来。

## 参考资料

### AOSP 源码
- `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` — Framework 温控服务 [已验证]
- `hardware/interfaces/thermal/2.0/IThermal.hal` — Thermal HAL 2.0 接口定义 [已验证]
- `hardware/interfaces/thermal/2.0/types.hal` — TemperatureType, ThrottlingSeverity 等类型定义 [已验证]
- `hardware/interfaces/thermal/aidl/android/hardware/thermal/` — AIDL 版本的 Thermal HAL（Android 14+）[已验证]
- `drivers/thermal/cpu_cooling.c` — 内核 cpufreq cooling 实现 [已验证]
- `drivers/thermal/of-thermal.c` — 内核 thermal zone 设备树支持 [已验证]

### 官方文档
- [Android Thermal Management](https://source.android.com/docs/core/thermal) — 系统级温控架构文档 [已验证]
- [PowerManager Thermal API](https://developer.android.com/reference/android/os/PowerManager) — 应用层 API 参考 [已验证]
- [Android Dynamic Performance Framework (ADPF)](https://developer.android.com/games/optimize/adpf) — ADPF 文档 [已验证]
- [Game Thermal Guide](https://developer.android.com/games/optimize/thermal) — 游戏温控优化指南 [已验证]

### 其他参考
- [Perfetto Trace 配置](https://ui.perfetto.dev/) — thermal_period_ms 和 ftrace 事件配置 [已验证]
- Linux kernel `Documentation/thermal/sysfs-api.rst` — thermal zone sysfs 接口文档 [已验证]
