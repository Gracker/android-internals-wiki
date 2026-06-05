---
title: "Thermal 管控"
chapter: "5.5"
section: "5.5"
status: ready-for-review
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
applicable_versions_note: "已验证范围 Android 7-14；Android 15-17 为待验证"
last_verified: "2026-06-06"
last_verified_against: "PowerManager#getThermalHeadroom + #getThermalHeadroomThresholds docs + SystemHealthManager headroom docs + source.android.com thermal mitigation docs"
confidence: medium
sources:
  - type: "official"
    path: "developer.android.com/games/optimize/adpf"
  - type: "official"
    path: "source.android.com/docs/core/thermal"
  - type: "official"
    path: "developer.android.com/reference/android/os/PowerManager"
tags: ["thermal", "power", "adpf", "perfetto", "cpu"]
related_chapters: ["5.1", "5.2", "5.3", "5.4", "5.6", "5.9", "5.12", "7.3"]
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2"
polish_count: 2
polish_date: "2026-04-08"
polish_by: "task2b-polish"
reviewed_date: "2026-05-08"
reviewed_by: "openclaw-task6"
task6_state: revisiting
task6_result: "pass-light-edit"
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-05-08T06:05:00+08:00"
last_task6_audit: "2026-05-26"
last_task6_audit_log: "logs/review/2026-05-26-06-audit.md"
last_task6_review_log: "logs/review/2026-05-08-06-review.md"
task9_state: reviewed
task9_result: "auto-fixed"
task9_reviewed_date: "2026-05-08"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-08T06:28:09+08:00"
last_task9_review_log: "logs/deep-review/2026-05-08-06-deep-review.md"
task2b_state: fixed
task2b_result: fixed
pipeline_stage: task6_pending
repaired_date: "2026-04-24"
repaired_by: "openclaw-task2b"
last_task2b_at: '2026-05-08T05:42:56+08:00'
review_notes: "2026-05-02 task9 deep-review: needs-rework。本轮 P0 1，P1 1，P2 1；问题已写入 queue/suggestions/research-gaps。；2026-05-04 task6 re-review (revisiting→reviewed): pass-light-edit。无新增L1/L2问题。 | 2026-05-05 Task9 21:00：needs-rework。复核旧 P1：16KB/MMU 功耗→延迟 thermal throttling 仍缺设备/SoC/trace 数据证据；getThermalHeadroom >1.0 边界已有 suggestions，不新增 queue。 | 2026-05-08 Task6 05:05：发现 AIW 16KB thermal 残留确定性断言与已降级研究假设口径冲突，已标注并写入 Task2B queue；同步完成 L1/L2 小修。 | 2026-05-08 Task9 05:27：needs-rework。P0 1 / P1 1；AIW 16KB thermal 残留段仍包含不存在的 `thermal_monitor_notify()` / `update_libcache_stats()` 与无证据 Android 16/17 thermal 预测断言，已合并 queue。 | 2026-05-08 Task6 06:05：回炉复审通过。L1/L2 无新增问题，16KB thermal 段已保持研究假设口径；切回 Task9 复审。 | 2026-05-08 Task9 06:20：pass-tech-review。P0/P1 0，P2 1，P3 1；自动晋升 finalized。 | 2026-05-26 Task6 06:09：闲时抽检。L1 小修 2 处：删去冗余强调词，改写否定纠正式句式；frontmatter 完整，锚点覆盖完整。 | 2026-06-06 Task9 闲时抽检：auto-fixed。P1 1；补齐 Android 15/API 35 `PowerManager#getThermalHeadroomThresholds()` 版本差异，更新 Thermal API 与版本演进表，回到 Task6 复审。"
task9_review_notes: "2026-05-08 Task9 05:27：needs-rework。P0 1 / P1 1；AIW 16KB thermal 残留段仍包含不存在的 `thermal_monitor_notify()` / `update_libcache_stats()` 与无证据 Android 16/17 thermal 预测断言，已合并 queue。 | 2026-05-08 Task9 06:20：pass-tech-review。P0/P1 0，P2 1，P3 1；自动晋升 finalized。 | 2026-06-06 Task9 闲时抽检：auto-fixed。P1 1；补齐 Android 15/API 35 `PowerManager#getThermalHeadroomThresholds()` 版本差异，更新 Thermal API 与版本演进表，回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-05
last_task9_autofix_at: "2026-06-06"
last_task9_audit: "2026-06-06"
last_task9_audit_log: "logs/deep-review/2026-06-06-07-audit.md"
---
# Thermal 管控

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Thermal 管控路径：温度传感器 → Thermal HAL → thermal engine → 限频/限核
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

做过持续性能测试的工程师大概率遇到过这种情况：跑一个 30 分钟的游戏场景，或者反复滑动列表——前 5 分钟帧率稳稳的 120fps，第 10 分钟开始偶尔掉帧，到了第 20 分钟帧率直接腰斩，CPU 频率也莫名其妙地降了下来。第一反应往往是“代码有 bug”，但换一台冷启动的设备，表现完全正常。

这是设备的温控系统开始介入了。

在 Perfetto 中，这种场景的 Trace 非常有辨识度：CPU Frequency 轨迹线一开始在高频区间，随后逐步下探，像一只慢慢放气的气球。与此同时，帧渲染时间（Frame Timeline）从稳定的 8.33ms 一路飘升到 16ms、20ms 甚至更高。这就是 Thermal Throttling——温度墙——对性能最直接的影响。

了解温控系统的运作方式，对性能优化工程师来说是必修课。关闭温控是危险且不负责任的做法；需要理解温控机制的原因有三：

1. **我们需要区分温控导致的性能下降和代码缺陷导致的性能下降**。搞混了这两者，优化方向完全跑偏。
2. **在性能测试中，温控是最大的干扰变量**。不知道温控什么时候介入，benchmark 数据就没有可比性。
3. **App 层面的主动配合**。Android 提供了 Thermal API 让应用感知温度状态，在高负载场景（游戏、视频编码、AR）中主动降级，比被系统强制降频体验好得多。

## Thermal 管控路径：从传感器到限频

Android 的温控是一个分层架构：从底层硬件传感器一直到上层 Framework 服务，组成了一条完整的管控路径。下面按层拆解。

[图：Thermal 管控路径全景——温度传感器 → Kernel Thermal Core → Thermal HAL → ThermalManagerService → App/系统组件]

### 温度传感器：数据的源头

手机内部布满了温度传感器，它们分布在 SoC 的各个关键位置。常见的传感器位置包括：

- **CPU 各个 cluster**：大核 cluster 和小核 cluster 通常有独立的温度传感器，因为大小核的功耗和发热特性差异很大。
- **GPU**：GPU 在游戏等场景是发热大户，需要独立监控。
- **电池**：电池温度直接关系到安全，锂电池超过一定温度（通常 45°C-60°C）就需要强制保护。
- **皮肤（Skin）**：用户能感知到的设备表面温度。这个温度通过 SoC 温度、电池温度等经热模型估算得出。
- **USB/充电 IC**：快充时充电电路也是发热源。

在 Linux 内核中，这些传感器通过 `sysfs` 接口暴露，路径通常在 `/sys/class/thermal/` 下。每个 `thermal_zone` 对应一个传感器，其中 `temp` 文件保存当前温度值（单位通常是毫摄氏度）。

```bash
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

Cooling Device 不一定是物理设备——更常见的"降温设备"就是 CPU 本身。内核通过限制 CPU 的最高运行频率来实现降温，这被称为 **cpufreq cooling**。在 `drivers/thermal/cpufreq_cooling.c` 中，cpufreq cooling 会动态调整 CPU 的最大允许频率：当温度升高时，逐步降低 `max_freq`；温度回落后，再逐步恢复。

### Thermal Governor：从 trip crossing 到 cooling state

Trip point 被触发后，内核不会立刻把频率拉到最低——频率的变化幅度由 **thermal governor** 决定。Linux 内核提供了多种 governor 算法（`step_wise`、`fair_share`、`bang_bang`），Android 设备默认使用 **step_wise**。

step_wise 的工作方式：每次温度采样周期，检查当前温度是否跨越了某个 trip point。如果温度上升并越过了 trip point，对应的 cooling device 的 cooling state 增加 1 级（每级对应一个频率档位）；如果温度下降并离开了 trip point，cooling state 减少 1 级。频率会按台阶式变化：温度每上升一个采样周期，频率下降一档，不会直接跳到极值。

这个"渐进式降频"的设计是有意为之的。温度变化本身是连续的，如果温度刚过阈值就直接拉到最低频率，用户体验会出现断崖式下跌（帧率从 120fps 直接掉到 30fps）。step_wise 的单步调整让降频过程相对平滑，给用户一个"逐渐变慢"而非"突然卡死"的感知。

在 Perfetto 中，这种阶梯式降频表现为 CPU frequency 曲线的"台阶"形态——每次下降一个固定的频率档位，而不是直线跌落。这与 DVFS governor（如 schedutil）基于 utilization 的连续调频形成对比。

[已验证: Linux kernel drivers/thermal/step_wise.c, Documentation/thermal/sysfs-api.rst]

这就是为什么我们在 Perfetto 中看到 CPU 频率下降时，往往伴随着温度的上升——与 governor（如 schedutil）基于 utilization 的主动调频不同，thermal cooling 是在强制压低频率上限。

[已验证: Linux kernel drivers/thermal/cpufreq_cooling.c, thermal_of.c (Linux 5.13+)]

### Thermal HAL：硬件抽象层

内核的 thermal core 够用了，但 Android 有自己的需求——Framework 需要统一管理温控策略，而不同厂商的硬件差异很大。Thermal HAL 就是这层抽象。

**Thermal HAL 1.0（Android 8 引入）** 采用轮询（polling）方式获取温度，这是最早的标准化 Thermal HAL 版本。Framework 定期调用 HAL 的 `getTemperatures()` 方法来读取各传感器数据。这种方式简单但效率低，而且延迟大——两次轮询之间可能错过了温度的快速上升。

**Thermal HAL 2.0（Android 10+）** 引入了事件驱动的接口。当温度跨越阈值时，HAL 主动向 Framework 上报 `ThrottlingSeverity` 变化，而不是等 Framework 来问。从 Android 14 开始，HAL 接口从 HIDL 迁移到 AIDL（`android.hardware.thermal.IThermal`），但核心模型不变。

### 厂商 Thermal 中间层：温控策略的实际执行者

AOSP 定义的 Thermal HAL 是一套标准接口，但不同厂商的设备在同样的 SoC、同样的负载下，温控行为可能截然不同。差异来自 HAL 层下方各厂商实现的 vendor-specific thermal engine。

**Qualcomm** 平台上，`thermal-engine` 是一个用户态守护进程（`/vendor/bin/thermal-engine`），它读取内核 thermal zone 的温度数据，运行 PID 控制算法，然后通过 sysfs 和 Thermal HAL 配置来调节频率上限、CPU 核心数、充电电流等参数。OEM 可以通过 `/vendor/etc/thermal-engine.conf` 配置文件定义自己的温控策略——温度阈值、降频步进、每个 severity 级别对应的频率限制等。同一款 Snapdragon 8 Gen 3，在不同厂商的手机上，thermal-engine 的配置也可能完全不同。

**MediaTek** 平台有类似的组件（thermal manager / thermal daemon），同样负责将温度传感器数据映射为具体的限频/限核动作。MTK 的温控配置通常在 `/vendor/etc/thermal.conf` 中定义。

这些厂商 thermal engine 的存在解释了一个现象：即使 Framework 层的 `ThermalManagerService` 报告的 severity 是 `LIGHT`，实际的限频幅度可能因为 thermal engine 的 PID 控制策略而比 AOSP 默认行为更激进或更保守。性能工程师在做跨设备对比时，需要意识到这个"隐藏层"的存在。

[待验证：thermal-engine 配置参数属于厂商私有信息，具体阈值和算法因 OEM 而异]

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
3. **执行关机流程**。当 severity 达到 `SHUTDOWN` 时，ThermalManagerService 触发 Framework 层关机。

温控路径实际运行在两条并行平面上：

**Mitigation 平面（降温执行）**：传感器感知温度 → 内核 thermal core 做第一道硬件级保护（cpufreq cooling、CPU hotplug） → 厂商 thermal engine 在 HAL 层下方并行执行 PID 控制策略（限频、限核、降充电电流） → cooling device 按 governor 算法逐级响应。这条平面上的限频/限核动作通常不经过 ThermalManagerService，而是由内核 thermal core 和 vendor thermal-engine 直接执行。

**Reporting / API 平面（状态上报）**：Thermal HAL 将温度状态抽象为 severity 级别 → ThermalManagerService 接收 HAL 上报并广播给系统组件和 App → 各组件根据 severity 独立响应（如 JobScheduler 限制后台频率、DisplayManagerService 降低亮度上限） → App 通过 PowerManager API 感知并自适应。当 severity 达到 SHUTDOWN 时，ThermalManagerService 触发关机。

两个平面通过 severity / thermal zone 状态关联：内核 thermal core 和 vendor engine 在 mitigation 平面上执行降温，同时通过 HAL 将状态同步到 reporting 平面，让 Framework 和 App 能感知并配合。

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

Android 11（API 30）引入了 `getThermalHeadroom(int forecastSeconds)`。它返回的是一个非负浮点值，用来表示距离 `THERMAL_STATUS_SEVERE` 还有多少热余量：`1.0` 对应 `SEVERE` 阈值，数值也可能大于 `1.0`，表示设备已经超过这个阈值并处在更重的限频状态。

```java
// 查询当前的热余量
float headroom = pm.getThermalHeadroom(0);  // 当前状态
float headroom5s = pm.getThermalHeadroom(5); // 预测5秒后的状态
```

这个 API 的使用场景主要是游戏或其他持续高负载场景：引擎可以周期性读取 thermal headroom，在靠近阈值时主动降低渲染分辨率、帧率目标或特效等级，把负载降下来。

需要注意几点：

- 这个 API 主要跟踪的是慢变化传感器（如皮肤温度），而不是 CPU 瞬时温度，所以它更适合做趋势判断。
- 不要频繁调用。官方明确说大约每秒调用一次已经够用，调用过密可能返回 `NaN`。
- `NaN` 主要表示设备不支持，或者采样过密；不要把“首次调用返回 `NaN`”当成固定行为。
- 预测值需要系统先积累多个温度样本。在最初几秒里，即使 `forecastSeconds` 大于 0，返回的通常仍是当前 headroom，而不是未来预测值。

Android 15（API 35）增加了配套 API：`getThermalHeadroomThresholds()`。它返回 `THERMAL_STATUS_*` 到 headroom 阈值的映射，只有厂商为某个状态定义了阈值时才会出现在结果里。这个映射适合把 `getThermalHeadroom(10)` 这类预测值转换为“可能进入 LIGHT / MODERATE / SEVERE”的预警，但它不保证当前 `getThermalHeadroom(0)` 超过某个阈值时，`getCurrentThermalStatus()` 已经同步切到对应状态。

[已验证: 官方文档 developer.android.com/reference/android/os/PowerManager#getThermalHeadroom(int), #getThermalHeadroomThresholds()]

### Android 16：CPU/GPU 算力余量（SystemHealthManager）

`getThermalHeadroom()` 只反映距 SEVERE 阈值的热余量，不区分 CPU 和 GPU 各自的负载压力。Android 16 引入了 `SystemHealthManager`（`android.os.health.SystemHealthManager`），提供更细粒度的算力余量查询：

- `getCpuHeadroom(CpuHeadroomParams)` — 估算近期 CPU 可用算力百分比，返回值范围 `[0, 100]`
- `getGpuHeadroom(GpuHeadroomParams)` — 估算近期 GPU 可用算力百分比，返回值范围 `[0, 100]`

这两个 API 与 `getThermalHeadroom()` 互补：thermal headroom 看的是整体接近 SEVERE 的程度，CPU/GPU headroom 看的是各计算单元本身的资源余量。在高负载场景下，可能出现 thermal headroom 还充裕但 GPU headroom 已经很低的情况——此时应该降的是 GPU 负载（分辨率、特效）而非 CPU。

边界条件：
- 设备不支持时抛 `UnsupportedOperationException`
- 参数无效时抛 `IllegalArgumentException`
- 暂时无法获取结果时返回 `Float.NaN`（如采样过密或数据尚未就绪）
- 不要在主线程或关键渲染路径上同步调用，查询本身有 IPC 开销
- 最小轮询间隔应通过 `getCpuHeadroomMinIntervalMillis()` / `getGpuHeadroomMinIntervalMillis()` 查询，并非固定值

```java
// import android.os.health.SystemHealthManager;
SystemHealthManager shm = getSystemService(SystemHealthManager.class);
float cpuHeadroom = shm.getCpuHeadroom(new CpuHeadroomParams.Builder().build());
float gpuHeadroom = shm.getGpuHeadroom(new GpuHeadroomParams.Builder().build());
// 两者都是 [0, 100]，越低表示该计算单元余量越小
```

[已验证: AOSP android16-qpr2 SystemHealthManager.java / CpuHeadroomParams.java / GpuHeadroomParams.java]

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

`thermal_zone_trip` 事件会告诉我们哪个 thermal zone 跨越了哪个 trip point，这是确认温控介入的直接证据。

[已验证: Perfetto 官方文档 ui.perfetto.dev, data source 配置参考]

### Android 16：ProfilingManager 与热场景 Trace

Android 16 的 `ProfilingManager` 支持通过 `ProfilingTrigger` 注册 profiling 请求，可用触发器包括 `TRIGGER_TYPE_APP_FULLY_DRAWN`、`TRIGGER_TYPE_ANR` 等（定义在 `packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`）。截至 android16-qpr2，AOSP Profiling 模块中未提供 thermal 类型的触发器——热场景的 Trace 捕获仍需手动配置。

对于热性能分析，推荐的手动采集方式：

```python
# Perfetto trace_config 示例：热场景专用
thermal_trace = {
  'buffers': [{'size_kb': 16384}],
  'data_sources': [
    {'config': {'name': 'linux.ftrace', 'ftrace_events': [
      'thermal/thermal_temperature', 'thermal/thermal_zone_trip',
      'power/cpu_frequency', 'sched/sched_switch'
    ]}},
  ]
}
```

在过热复现场景中，提前启动上述配置的 Trace，就能捕获降频瞬间的 CPU 频率、thermal zone 温度变化和线程调度，定位触发降频的 thermal zone 和受影响最大的线程。

[已验证: AOSP android16-qpr2 ProfilingTrigger.java — thermal trigger 不在 AOSP 定义的触发器列表中]

### DVFS 降频 vs Thermal 降频：怎么区分？

我们在 [5.4 DVFS 与功耗管理](04-dvfs.md) 中讨论过，schedutil governor 会根据 CPU utilization 主动调节频率。高负载时升频，低负载时降频——这是正常的 DVFS 行为，不涉及温控。

Thermal 降频是另一种机制：它是 **强制性的频率上限约束**。即使 CPU utilization 很高，thermal cooling 也会把频率限制在某个上限以下。

在 Perfetto 中区分两者的方法：

- **DVFS 降频**：CPU utilization 低 → 频率降低。这是正常的，频率和负载同步变化。
- **Thermal 降频**：CPU utilization 高 → 频率反而降低。频率和负载"反着来"，这就是温度墙在起作用。

如果我们看到高负载期间频率反而比空闲时低，基本可以确认是 thermal throttling。

### 16KB Page Size 与热平衡：研究假设

前面讨论的温控触发条件都与“负载产生了多少热量”直接相关。换个角度想：如果硬件本身因为某些原因做了更少的无用功，热量积累就会变慢。16KB 大页内存对温控可能存在间接贡献，但当前缺乏同设备 4KB/16KB A/B 对照数据（thermal zone 温度曲线、CPU 频率上限变化、time-to-throttle、功耗 rail 读数），以下为研究假设而非已验证结论。

大页使页表条目数量减少约 75%，TLB miss 率理论上下降，页表遍历功耗也会减少。社区估算 MMU 功耗可降低约 4.5%，但该数值因 SoC 和工作负载而异，尚无公开的系统性 benchmark 支撑。

如果 MMU 功耗下降，理论上热积累斜率变缓，设备在相同工作负载下维持最高频率的时间窗可能延长。但这条因果链（16KB → TLB miss 降低 → MMU 功耗下降 → 热积累变缓 → thermal throttling 推迟）的每一环都需要实测数据验证。在缺乏同设备 A/B trace 之前，不应把 16KB 当作推迟温控降频的确定因素。

[待验证: 需要同设备 4KB/16KB kernel 页大小配置下的 thermal zone trace、CPU freq 上限曲线、time-to-throttle 与 power rail 对照数据]

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

具体实现是 `DisplayManagerService` 订阅 thermal status 变化后自行降低亮度上限，具体的降亮曲线因厂商而异。

### 关闭非必要功能

在更高的 severity 级别，系统各组件根据订阅到的 thermal status 独立执行各自的降温策略：

- **SEVERE**：`JobScheduler` 限制后台任务执行频率（由 `JobSchedulerService` 根据 thermal status 自行调整）
- **CRITICAL**：降低扫描频率（如 Wi-Fi 扫描、BLE 扫描），减少非必要唤醒
- **EMERGENCY**：关闭调制解调器（radio）、停止充电、关闭 NFC 等外设

这些动作通常由各系统组件订阅 thermal status 后自行响应。ThermalManagerService 负责广播状态，具体执行落在各组件或厂商 thermal engine 上；后者可能在 HAL 层执行更激进的策略（如直接限频/限核），绕过 Framework 层。

### 限制充电电流

充电本身会产生热量。当电池温度过高时，系统会降低充电电流甚至暂停充电。这个逻辑通常在充电 IC 的固件中实现，但也受 Thermal HAL 的控制。

[已验证: AOSP ThermalManagerService.java @ android16-qpr2, 官方文档 source.android.com/docs/core/thermal]

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

Android 7.0（API 24）引入的 Sustained Performance Mode，会从一开始就把最高频率限制在一个更容易持续维持的区间，避免先跑满再降频。它适合长时间 benchmark：峰值成绩可能低一些，但 30 分钟窗口里的波动更小。

前提条件是设备厂商必须在 Power HAL 中实现 `POWER_HINT_SUSTAINED_PERFORMANCE`，并通过 `PowerManager.isSustainedPerformanceModeSupported()` 声明支持。很多中低端设备并不支持。具体 API 用法和 CTS 要求见下文 [Sustained Performance Mode API](#sustained-performance-mode-api) 小节。

### 策略 3：使用 Fixed Performance Mode（Benchmark 专用）

Fixed Performance Mode 是面向基准测试和实验室复现的调试开关，通常通过 `adb shell cmd power set-fixed-performance-mode-enabled true` 启用，不是普通应用通过 `PerformanceHintManager` 直接调用的公开 API。

它的作用是把设备放到更稳定的性能区间，减少 DVFS 抖动，让 A/B 对比更容易复现；但它不会关闭 thermal，设备仍然可能过热，也不保证 CPU / GPU 频率永远固定在同一个值。

```bash
adb shell cmd power set-fixed-performance-mode-enabled true
# 跑完基准测试后记得关闭
adb shell cmd power set-fixed-performance-mode-enabled false
```

这个模式适合横向对比不同设备或不同版本的性能差异，但测试前仍要等待设备回到可持续温度区间，并记录 thermal status 作为元数据。

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

前面讨论的都是 Android 通用架构。但在实际工作中我们会发现，同样 SoC 的两台手机，性能表现可能天差地别——差异往往来自厂商各自的温控策略调校。温控策略是厂商差异化最明显的领域之一。同样是 Snapdragon 8 Gen 3，不同手机厂商的 thermal 配置可能截然不同：激进者允许更高的温度上限换取持续高性能，保守者在较低温度就开始降频，以平衡用户体验和硬件安全。

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

这方面的差异不是软件层面能改变的，但性能工程师需要知道：**在评估"性能下降"问题时，先排除散热条件差异**。比如用户反馈"更新后游戏变卡了"，可能只是这次测试时环境温度比上次高，或者测试前设备没有充分冷却。

[待验证：石墨烯和 VC 均热板的具体散热参数因厂商规格而异，此处为通用描述]

## 版本演进速览

Thermal 管控在 Android 各版本中有几项关键变化，这里做一个梳理：

| Android 版本 | 变化 | 影响 |
|-------------|------|------|
| 7.0 (API 24) | 引入 Sustained Performance Mode | 首次提供可预测持续性能的 API |
| 8 (API 26) | Thermal HAL 1.0（轮询模式） | 首个标准化温度读取接口 |
| 10 (API 29) | Thermal HAL 2.0（事件驱动）+ PowerManager Thermal API | App 可感知温控状态 |
| 11 (API 30) | `getThermalHeadroom()` API | 支持前瞻性热余量预测 |
| 14 (API 34) | Thermal HAL 从 HIDL 迁移至 AIDL | 接口现代化，无功能变化 |
| 15 (API 35) | `PowerManager#getThermalHeadroomThresholds()` | App 可读取各 thermal status 对应的 headroom 阈值，更早做降载预警 |
| 16 (API 36) | ADPF Game Mode API 扩展，与温控协同增强 [待验证] | 更多性能-温控协调能力 |

这些版本节点的共同趋势是：从被动响应走向主动感知，从系统独占走向应用参与。Android 希望应用能主动配合降载，成为温控的合作方。

## 常见问题与误区

### 误区 1："手机发烫是 App 的 bug"

手机发烫是 SoC 在高负载下的物理必然。App 能做的是减少不必要的计算，但只要用户在玩游戏、看高码率视频、用 AR 应用，SoC 就会发热。需要排查的 bug 是后台偷偷跑着高负载（如死循环、频繁 GC、持续定位），这些可以通过 Trace 分析定位。

### 误区 2："Root 后关掉温控就能一直满血"

这是极其危险的做法。温控是硬件保护机制，关闭温控可能导致 SoC 温度超过安全阈值（通常 85-95°C），轻则硬件加速老化，重则直接烧毁。短期测试可以放宽温控阈值，但绝对不能在生产环境中关闭。

### 误区 3："Thermal API 只对游戏有用"

虽然游戏是 Thermal API 最主要的使用者，但任何长时间高负载的应用都应该关注温控状态。比如视频编辑应用（长时间编码）、导航应用（GPS + 屏幕 + 语音同时工作）、AR 应用（摄像头 + GPU + 传感器全开）。当 thermal status 升高时，这些应用也应该主动降低负载。

### 误区 4："Sustained Performance Mode 会降低性能"

不完全准确。Sustained Performance Mode 降低的是**峰值性能**，但提升了**持续性能**。对于长时间运行的场景（30 分钟+），它提供了更稳定的体验。只有短时间 burst 场景（如应用启动）才会感觉到峰值性能的损失。

## 与其他章节的关联

- **[5.4 DVFS 与功耗管理](04-dvfs.md)**：DVFS 是温控的执行手段之一。Thermal cooling 通过限制 DVFS 的频率上限来降温。了解 DVFS 机制有助于区分"正常调频"和"thermal 降频"。
- **[5.3 大小核架构](03-big-little.md)**：Thermal mitigation 的"限核"操作直接影响大小核的在线核心数，进而影响 EAS 调度决策。
- **[5.6 Android 功耗管理](06-android-power.md)**：温控是功耗管理的子系统之一。WakeLock、Doze、App Standby 管的是"谁在用电"，温控管的是"电用多了怎么办"。
- **[7.3 卡顿分析方法论](03-jank-methodology.md)**：卡顿分析中，温控导致的掉帧需要和代码缺陷导致的掉帧区分开来。

## 参考资料

### AOSP 源码
- `frameworks/base/services/core/java/com/android/server/power/ThermalManagerService.java` — Framework 温控服务 [已验证]
- `hardware/interfaces/thermal/2.0/IThermal.hal` — Thermal HAL 2.0 接口定义 [已验证]
- `hardware/interfaces/thermal/2.0/types.hal` — TemperatureType, ThrottlingSeverity 等类型定义 [已验证]
- `hardware/interfaces/thermal/aidl/android/hardware/thermal/` — AIDL 版本的 Thermal HAL（Android 14+）[已验证]
- `drivers/thermal/cpufreq_cooling.c` — 内核 cpufreq cooling 实现（Linux 5.x+，旧名 cpu_cooling.c）[已验证]
- `drivers/thermal/thermal_of.c` — 内核 thermal zone 设备树支持（Linux 5.13+，旧名 of-thermal.c 已移除）[已验证]

### 官方文档
- [Android Thermal Management](https://source.android.com/docs/core/thermal) — 系统级温控架构文档 [已验证]
- [PowerManager Thermal API](https://developer.android.com/reference/android/os/PowerManager) — 应用层 API 参考 [已验证]
- [Android Dynamic Performance Framework (ADPF)](https://developer.android.com/games/optimize/adpf) — ADPF 文档 [已验证]
- [Game Thermal Guide](https://developer.android.com/games/optimize/thermal) — 游戏温控优化指南 [已验证]

### 其他参考
- [Perfetto Trace 配置](https://ui.perfetto.dev/) — thermal_period_ms 和 ftrace 事件配置 [已验证]
- Linux kernel `Documentation/thermal/sysfs-api.rst` — thermal zone sysfs 接口文档 [已验证]
