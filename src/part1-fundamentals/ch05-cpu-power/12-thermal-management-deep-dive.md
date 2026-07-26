---
last_task9_at: "2026-06-05T07:20:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-05"
title: "Thermal 管控深度：从内核子系统到 ADPF 主动降频"
chapter: "5.12"
section: "5.12"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-12"
last_verified_against: "AOSP android-16.0.0_r1, Linux kernel android16-6.12"
confidence: medium
sources: 
path: "drivers/thermal/thermal_core.c"
path: "drivers/thermal/cpufreq_cooling.c"
path: "drivers/thermal/gov_step_wise.c"
path: "drivers/thermal/gov_power_allocator.c"
path: "drivers/thermal/devfreq_cooling.c"
path: "drivers/devfreq/devfreq.c"
path: "hardware/interfaces/thermal/aidl/android/hardware/thermal/"
path: "developer.android.com/games/optimize/thermal"
path: "developer.android.com/games/optimize/adpf"
path: "source.android.com/docs/core/power/thermal-mitigation"
path: "https://perfetto.dev/docs/analysis/trace-analysis-with-sql"
path: "mediatek.com - MAGT ADPF integration case studies"
tags: "[thermal, throttling, ADPF, Thermal HAL, sustained performance, 游戏性能, 功耗, devfreq, power_allocator]"
related_chapters: "[\"5.5\", \"5.9\", \"4.7\", \"8.9\", \"11.1\", \"16.4\"]"
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "官方文档+研究素材+AOSP结构+读者需求"
gap_score: "18/20"
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_date: 2026-06-04
last_task6_audit: "2026-06-08"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
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
last_task6_at: "2026-06-15T04:09:51+08:00"
task6_reviewed_date: 2026-06-15
task6_reviewed_by: openclaw-task6
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
task6_review_notes: "2026-06-04 Task6 revisiting review: pass-light-edit。L1 小修 2 处（形容词+冒号起手式 1、「很关键」填充 1）。无新增 L3/L4 回炉项。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
last_task9_autofix_at: "2026-06-15"
last_task6_review_log: logs/review/2026-06-15-04-review.md
finalized_date: 2026-06-15
finalized_by: openclaw-task6
auto_promoted_date: 2026-06-15
auto_promoted_by: openclaw-task6
---

# 5.12 Thermal 管控深度：从内核子系统到应用主动降载

本章是 [5.5 Thermal 管控](05-thermal.md) 的深入篇。5.5 建立从传感器到应用的整体视图；这里继续回答几个更具体的问题：

- Linux thermal governor 根据什么决定 cooling state；
- `power_allocator` 的功耗预算与 PID 参数如何工作；
- Thermal HAL 的 severity、Framework status 和内核 trip 有什么区别；
- 应用怎样正确解释 thermal headroom、CPU/GPU headroom；
- Perfetto 中哪些信号能证明降频来自温控。

平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核以 `android17-6.18-2026-06_r6` 为准。版本演进段会保留旧接口，但不会把旧分支的函数签名套到 6.18 上。

## 先看清温控系统的分层

Android 设备的温控路径通常包含五层：

```text
温度传感器与电源监控
  → Linux thermal zone / vendor driver / thermal daemon
  → cooling device、DVFS、充电与其他缓解动作
  → Thermal HAL：Temperature + ThrottlingSeverity
  → ThermalManagerService / PowerManager
  → App：状态监听、headroom、主动降低 workload
```

这张图表达职责关系，不表示每台手机都由内核 thermal governor 独自完成决策。厂商可以在 HAL、用户空间 daemon、vendor kernel 模块和芯片固件中加入策略。Framework 接收到的是厂商整理后的温度与 severity，无法从一个 status 值反推出全部底层动作。

需要分清三套术语：

| 层 | 主要概念 | 它回答的问题 |
|---|---|---|
| Linux thermal | zone、trip、governor、cooling device | 哪个热区越过阈值，执行多强的缓解动作 |
| Thermal HAL | `Temperature`、`ThrottlingSeverity`、threshold | 厂商向 Framework 报告哪个传感器处于哪一级 |
| App API | thermal status、thermal headroom、CPU/GPU headroom | 应用何时应降低负载，哪个资源可能接近容量上限 |

内核的 `THERMAL_TRIP_CRITICAL` 与 Framework 的 `THERMAL_STATUS_CRITICAL` 名称相近，但它们没有固定的一一映射。前者属于某个 thermal zone 的保护阈值；后者是 HAL 上报的 severity。

## Linux 6.18 thermal 子系统

内核通用 thermal 框架位于 `drivers/thermal/`。它把温度采样、阈值、控制策略和执行器组织成几个对象。

### Thermal zone、trip、cooling device 与 instance

- **thermal zone**：一个可监控的热区，例如 SoC、CPU cluster、电池或某个虚拟 skin 模型；
- **trip**：该热区的温度阈值、类型与 hysteresis；
- **cooling device**：可以降低发热或移走热量的执行器，例如 cpufreq、devfreq 或风扇；
- **thermal instance**：某个 trip 与某个 cooling device 的绑定，包含可用 state 的上下界和权重；
- **governor**：根据温度、趋势和 trip 状态，计算各 instance 的目标。

在设备树中，这些关系通常由 `trips` 与 `cooling-maps` 描述。下面只展示结构，温度、传感器和 state 范围均由具体产品标定：

```dts
thermal-zones {
    soc_thermal: soc-thermal {
        polling-delay = <1000>;
        polling-delay-passive = <100>;
        thermal-sensors = <&sensor 0>;

        trips {
            soc_passive: trip-passive {
                temperature = <55000>;
                hysteresis = <2000>;
                type = "passive";
            };
            soc_critical: trip-critical {
                temperature = <85000>;
                hysteresis = <0>;
                type = "critical";
            };
        };

        cooling-maps {
            map0 {
                trip = <&soc_passive>;
                cooling-device = <&cpu0 1 4>;
            };
        };
    };
};
```

这个示例说明：超过 passive trip 后，governor 可以在 state 1 到 4 之间控制绑定的 cooling device；温度下降到带 hysteresis 的释放阈值后，再减轻限制。Hysteresis 可以减少阈值附近的频繁切换。

### 用 sysfs 确认本机对象

在 userdebug、eng 或具有相应权限的设备上，可以先枚举 thermal 对象：

```bash
adb shell 'for z in /sys/class/thermal/thermal_zone*; do
  echo "$z type=$(cat "$z/type" 2>/dev/null) temp=$(cat "$z/temp" 2>/dev/null)"
done'

adb shell 'for c in /sys/class/thermal/cooling_device*; do
  echo "$c type=$(cat "$c/type" 2>/dev/null) state=$(cat "$c/cur_state" 2>/dev/null)"
done'
```

标准 thermal sysfs 的温度通常使用毫摄氏度，例如 `52000` 表示 52°C。量产机可能因 SELinux、内核配置或厂商实现而隐藏部分节点；脚本还应读取 `type`，不要把 `thermal_zone0` 固定解释为 CPU。

### 四种 trip 类型

**Passive** 通常用于限制设备活动度，例如压低 CPU/GPU 允许的最高频率。它描述控制用途，不指定具体 cooling device。

**Active** 面向风扇、泵等主动散热执行器。无风扇手机较少使用，平板、车载、Chromebook 或带外接散热设备的产品可能使用。

**Hot** 表示高温事件。Linux 6.18 的 `handle_critical_trips()` 在 HOT 分支调用可选的 `tz->ops.hot()`；没有通用的自动关机承诺。

**Critical** 进入硬件保护路径。`android17-6.18-2026-06_r6` 的调用关系是：

```text
handle_critical_trips()
  → tz->ops.critical(tz)
  → 默认 thermal_zone_device_critical()
  → thermal_zone_device_halt(..., HWPROT_ACT_DEFAULT)
  → __hw_protection_trigger(...)
```

同一分支还提供 `thermal_zone_device_critical_shutdown()` 和 `thermal_zone_device_critical_reboot()`，分别传入明确的 shutdown/reboot 动作。默认动作由 `HWPROT_ACT_DEFAULT` 解析，内核默认是 shutdown，也可由平台硬件保护配置选择 reboot。应用和普通系统调优不应修改 critical 阈值或保护动作。

### `step_wise`：按趋势调整 state

`step_wise` 的核心入口是 `step_wise_manage()`，单个 trip-instance 的目标由：

```c
get_target_state(struct thermal_instance *instance,
                 enum thermal_trend trend,
                 bool throttle)
```

计算。Linux 6.18 的行为比“温度升就加一级、温度降就减一级”多几条边界：

- `throttle` 由当前温度是否达到该 trip 的动态 threshold 决定；
- instance 首次初始化且需要 throttle 时，从 cooling device 当前 state 加一级，并限制在 `lower..upper`；
- 已经越过 trip 且趋势继续上升时，加一级；
- 已经越过 trip 但趋势下降时，可减一级，但仍至少保持在该 instance 的有效下限附近；
- 已低于 trip 且趋势下降时，回到 `lower`；达到释放条件后可返回 `THERMAL_NO_TARGET`；
- HOT 与 CRITICAL trip 不交给 `step_wise` 管理。

因此，同一个 cooling device 被多个 trip 绑定时，最终 state 还要综合多个 thermal instance。只看单个 trip 的温度不足以推断最终频率上限。

`step_wise` 易于理解，代价是动作按离散 state 变化。采样周期、hysteresis、state 数量和温升速度会共同影响过冲与振荡。

### `power_allocator`：把温度误差换成功耗预算

`power_allocator` 使用反馈控制计算下一周期允许分配的总功耗，再按 cooling device 的请求、能力和权重分配给各 power actor。Cooling device 需要实现 `get_requested_power`、`state2power` 和 `power2state` 才能作为 power actor 参与。

Linux 6.18 的控制器签名为：

```c
pid_controller(struct thermal_zone_device *tz,
               int control_temp,
               u32 max_allocatable_power)
```

核心关系可以写成：

```text
error = control_temp - current_temperature
budget = sustainable_power
       + k_p(error) × error
       + k_i × accumulated_error
       + k_d × error_change / sample_interval
```

当温度高于目标时，`error` 为负，比例项使用 `k_po`；低于目标时使用 `k_pu`。实现还会限制积分项，避免累计值越过最大可分配功耗。`sustainable_power` 是热平衡附近的前馈基线；P/I/D 项在其上修正。

参数的工程含义如下：

| 参数 | 增大后的主要影响 | 风险 |
|---|---|---|
| `sustainable_power` | 提高目标温度附近的基础预算 | 高估会持续偏热，低估会过早限制 |
| `k_pu` | 低于目标温度时更快放开功耗 | 容易冲过目标温度 |
| `k_po` | 高于目标温度时更强地收紧预算 | 可能造成性能突降或振荡 |
| `k_i` | 更积极修正长期偏差 | 积分累积可能让恢复变慢 |
| `k_d` | 根据温度误差变化速度提前修正 | 对噪声敏感；内核文档建议通常保留默认 0 |
| `integral_cutoff` | 决定哪些误差进入积分 | 配置不当会积累无用历史误差 |

调参需要同时观察 `thermal_power_allocator`、`thermal_power_actor` 与 `thermal_power_allocator_pid` tracepoint。仅看温度曲线，无法知道预算收紧来自比例项、积分项还是 actor 的功耗请求。

### 其他 governor

- `fair_share` 按 thermal instance 权重分配 cooling state；
- `user_space` 把策略事件交给用户空间；
- `bang_bang` 适合开/关式执行器，例如风扇。

Android 产品常有厂商自定义路径。发现 sysfs 中的 governor 是 `user_space`，或标准 tracepoint 没有记录到预期动作时，应继续检查 vendor thermal daemon、芯片固件和厂商 trace。

## Cooling device 如何限制 CPU 与 GPU

### cpufreq cooling

`drivers/thermal/cpufreq_cooling.c` 把 cooling state 映射到 CPU policy 的允许频率，并通过 `freq_qos` 更新上限。state 0 通常表示最少限制；state 越高，可用的最高频率越低。state 与 MHz 不保证线性关系，取决于频率表和 OPP。

当使用 `power_allocator` 时，cpufreq cooling 还可以通过能量模型实现 `state2power`、`power2state` 与请求功耗估算。此时 governor 分配的是功耗预算，最终仍要转换成 cooling state 和频率限制。

可以用下面的只读信息交叉确认 CPU 限制：

```bash
adb shell 'cat /sys/class/thermal/cooling_device*/type'
adb shell 'cat /sys/class/thermal/cooling_device*/cur_state'
adb shell 'cat /sys/devices/system/cpu/cpufreq/policy*/scaling_max_freq'
adb shell 'cat /sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq'
```

`scaling_cur_freq` 是采样值，`scaling_max_freq` 也可能同时受用户策略、Power HAL、battery、scheduler 或其他 QoS request 影响。观察到上限下降后，还需用 thermal state、tracepoint 或 HAL severity 证明温控因果关系。

### devfreq cooling

`drivers/thermal/devfreq_cooling.c` 把 thermal 框架连接到 devfreq 设备。GPU、NPU、DSP 或内存互连只有在对应驱动注册为 devfreq cooling device 后，才会受这条通用路径控制。

Linux 6.18 的 devfreq cooling 同样支持普通 state 控制和可选 power actor 操作。设备节点、频率单位和 `available_frequencies` 是否公开均由驱动决定。看到 `/sys/class/devfreq/` 目录，并不能据此断言该设备已绑定 thermal cooling。

### CPU hotplug 的边界

CPU hotplug 曾被一些设备用于高温保护，近年的手机更常见 cpufreq/devfreq 限制、core control、厂商 daemon 和固件策略。Framework severity 没有“升一级就下线几个核心”的标准映射。

若 trace 中出现 CPU offline，应继续查 `cpu_hotplug` 事件、vendor driver 和 daemon 日志。不要仅凭 `THERMAL_STATUS_SEVERE` 推断是 Framework 主动 hotplug。

## Thermal HAL：把厂商状态交给 Framework

Android 17 的 AOSP 同时保留旧 HIDL 兼容路径和 AIDL Thermal HAL。AIDL 接口位于：

```text
hardware/interfaces/thermal/aidl/android/hardware/thermal/
```

`android-17.0.0_r1` 中冻结了三个 AIDL 版本：

| AIDL HAL 版本 | 主要能力 | 对应平台演进 |
|---|---|---|
| v1 | 温度、cooling device、threshold、thermal changed callback | Android 14 |
| v2 | cooling device changed callback | Android 15 |
| v3 | `forecastSkinTemperature(int)`、threshold changed callback | Android 16 |

Android 17 锚点没有新增 v4。版本号描述 HAL 契约，具体设备可以因旧 vendor image 或兼容要求继续使用 HIDL Thermal HAL 2.0/1.1/1.0；`ThermalManagerService` 会按 AIDL、HIDL 2.0、1.1、1.0 的顺序尝试连接。

### AIDL 中的三类数据

`IThermal` 提供：

- `getTemperatures*()`：当前温度与 `ThrottlingSeverity`；
- `getCoolingDevices*()`：cooling device 当前值；
- `getTemperatureThresholds*()`：各 severity 的 hot/cold 静态阈值；
- `registerThermalChangedCallback*()`：温度 severity 变化；
- `registerCoolingDeviceChangedCallbackWithType()`：v2 的 cooling device 回调；
- `forecastSkinTemperature()`：v3 的 skin 温度预测；
- `IThermalChangedCallback.notifyThresholdChanged()`：v3 的低频 threshold 更新。

`TemperatureThreshold.hotThrottlingThresholds[]` 和 `coldThrottlingThresholds[]` 以 severity 为索引。它们是厂商策略的阈值基线；v3 允许设备在硬件状态或 workload 改变时谨慎、低频地通知 threshold 更新。HAL 文档同时提醒：threshold 不一定完整描述厂商缓解算法；准确的当前 throttling 状态应读取 `Temperature` 或监听 callback。

### Severity 与内核 trip 的区别

HAL severity 包括：

```text
NONE → LIGHT → MODERATE → SEVERE → CRITICAL → EMERGENCY → SHUTDOWN
```

厂商可以融合 skin、SoC、电池、充电和其他模型生成 severity。内核 trip 则属于某个 thermal zone。两者可能参考相同传感器，也可能经过完全不同的策略。调试时应分别记录内核对象和 HAL 输出。

## Android 17 Framework 的聚合规则

Framework 服务位于：

```text
frameworks/base/services/core/java/com/android/server/power/thermal/
    ThermalManagerService.java
```

### 全局 status 取 skin severity 的最高值

`ThermalManagerService.onTemperatureMapChangedLocked()` 遍历当前温度，只考虑 `Temperature.TYPE_SKIN`，把最高 status 作为 `PowerManager.getCurrentThermalStatus()` 的全局结果。这个规则解释了两个常见现象：

- CPU 传感器很热，但 skin 模型还未升档时，全局 status 可能保持较低；
- 多个 skin 传感器同时存在时，Framework 取 severity 更高的一路。

收到任意 CPU、GPU、NPU、SKIN 传感器的 `THROTTLING_SHUTDOWN` 时，服务会请求 thermal-state shutdown；电池 SHUTDOWN 使用 battery-thermal 原因。全局 status 的 skin 聚合与最终关机保护是两条不同逻辑。

### 应用可用的三类信号

| API | 数值方向 | 适合用途 |
|---|---|---|
| `getCurrentThermalStatus()` / status listener | 等级越高越热 | 当前已发生的 throttling 档位 |
| `getThermalHeadroom(forecastSeconds)` | 0 较冷；1 表示到达或预测到达 SEVERE；可大于 1 | skin 热包络的当前值与短期预测 |
| `SystemHealthManager.getCpuHeadroom()` / `getGpuHeadroom()` | 0 表示没有更多容量，100 表示余量更大 | CPU/GPU 最近一段时间的容量余量 |

Thermal headroom 与 CPU/GPU headroom 的数值方向相反，也没有换算公式。CPU/GPU headroom 更接近历史使用情况与剩余容量，存在 TOCTOU；thermal headroom 是慢变 skin 热趋势。应用可以组合使用，不能互相替代。

### Thermal headroom 的归一化

`PowerManager.getThermalHeadroom()` 从 API 30 提供，参数范围是 0 到 60 秒。Framework 把 SEVERE 的 skin threshold 归一化为 1.0；Android 17 的本地实现把 0.0 放在 SEVERE threshold 以下 30°C 的位置，并对中间温度做线性归一化。

这里要记住三点：

1. headroom 越接近 1，越接近 SEVERE；大于 1 表示已经越过这条线或预测将越过；
2. 1 以上没有固定映射到 CRITICAL、EMERGENCY 或 SHUTDOWN；
3. 设备不支持、阈值缺失或调用过快时可能返回 `NaN`。

官方 API 文档说明，没有必要高于约 1 Hz 调用。更远的 forecast 更容易受负载变化影响。

### HAL forecast 与 Framework fallback

Android 17 启动时只在“恰好一个 skin threshold”并且 feature flag 开启时探测 HAL `forecastSkinTemperature()`。若 HAL 支持，Framework 将 HAL 返回的绝对温度按该 sensor 的 SEVERE threshold 归一化。

其余情况使用 `TemperatureWatcher`：

- 每秒读取 skin 温度；
- 每个 sensor 保留最多 30 个样本；
- 至少三个样本后用线性回归计算温升斜率；
- 预测 `current + slope × forecastSeconds`；
- 多 sensor 时取归一化结果最大的值；
- 十秒无人调用后停止采样并清理缓存。

所以，headroom forecast 可能来自 HAL 模型，也可能来自 Framework 线性外推。应用无需依赖内部来源，应把它当短期趋势信号。

### API 35 thresholds 与 API 36 listener

API 35 的 `getThermalHeadroomThresholds()` 返回 `Map<ThermalStatus, Float>`。SEVERE 保证是 1.0；其他 status 只有在 OEM 提供对应 threshold 时才存在。

API 36 的 `addThermalHeadroomListener()` 在 callback 中提供：

- 当前 headroom；
- 默认十秒的 forecast headroom；
- `forecastSeconds`；
- 最新 threshold map。

服务端有两类触发源：skin temperature/severity 事件与 threshold 变化。相似数据在五秒窗口内会被抑制；headroom 或 forecast 差值达到 0.03、threshold 差值达到 0.01 时会被视为显著变化。注册成功后会立即投递一次当前快照。

这个 listener 不会只因时间推移而周期性发送 forecast。官方注释明确建议：需要提前监控预测时，仍可按合理间隔调用 `getThermalHeadroom()`。

单参数重载使用 main executor；性能敏感应用更适合传入自己的 executor。生命周期结束时必须调用 `removeThermalHeadroomListener()`，因为 `PowerManager` 在应用进程中保存业务 listener 到 Binder stub 的映射。

NDK 在 API 36 提供 `AThermal_registerThermalHeadroomListener()`。callback 运行在 system Binder 线程池；其中 threshold 指针仅在 callback 生命周期内有效，需要长期保存时应立即复制。API 35 的 polling thresholds 接口由调用方按文档释放返回数组，不能与 callback 指针生命周期混用。

### Android 17 的虚拟设备边界

Android 17 的 `PowerManager` 会识别采用自定义 thermal policy 的虚拟设备 context：

- `getCurrentThermalStatus()` 和 status listener 路由到对应 deviceId；
- thermal headroom、threshold 和 headroom listener 对这类 context 不开放。

普通物理设备应用仍使用默认设备 status。多设备或虚拟显示框架不能假设所有 context 共享同一个 thermal policy。

## 应用侧如何设计降载策略

### 使用 OEM threshold，避免反向理解 headroom

下面的判断函数展示 API 35+ 的基本思路：当前 status 是硬信号，forecast 与 OEM threshold 用于提前一级调整。

```kotlin
private enum class ThermalLoadLevel { NORMAL, REDUCED, MINIMUM }

private fun chooseThermalLoad(
    currentStatus: Int,
    forecastHeadroom: Float,
    thresholds: Map<Int, Float>
): ThermalLoadLevel {
    val forecastValid = !forecastHeadroom.isNaN()
    val moderate = thresholds[PowerManager.THERMAL_STATUS_MODERATE]
    val severe = thresholds[PowerManager.THERMAL_STATUS_SEVERE] ?: 1.0f

    return when {
        currentStatus >= PowerManager.THERMAL_STATUS_SEVERE ||
            (forecastValid && forecastHeadroom >= severe) ->
            ThermalLoadLevel.MINIMUM

        currentStatus >= PowerManager.THERMAL_STATUS_MODERATE ||
            (forecastValid && moderate != null && forecastHeadroom >= moderate) ->
            ThermalLoadLevel.REDUCED

        else -> ThermalLoadLevel.NORMAL
    }
}
```

这里没有把 `0.4`、`0.7` 写成通用阈值。不同设备的 threshold 不同；headroom 数字越大，热压力越高。产品还应加入进入/退出 hysteresis 和最短驻留时间，避免画质、帧率在边界附近反复切换。

API 30—34 没有 threshold map，可组合 current status、headroom 趋势和设备实测建立策略。若 `NaN`，应退回 status listener 与保守默认值。

### 降载动作按成本分级

应用无法通过 Thermal API 直接指定 CPU/GPU 频率。可控的是 workload：

| 阶段 | 可选动作 | 需要验证的副作用 |
|---|---|---|
| 轻度预警 | 延后预取、减少后台推理、降低非关键采样率 | 功能时效 |
| 中度 | 降低渲染分辨率、阴影、粒子、相机分析帧率 | 画质与识别质量 |
| 重度 | 降低目标 FPS、模型档位、编码规格或并发度 | 交互连续性 |
| 恢复 | 分阶段恢复，并设置冷却驻留时间 | 防止热振荡 |

实时管线还应丢弃过期输入，避免低频后队列继续增长。温控降载若只降低设备频率而不减少待完成工作，端到端延迟可能更差。

### 与 Performance Hint Session 保持一致

ADPF 的 Performance Hint Session 让应用报告目标 work duration 与实际 duration，系统据此调整调度策略。它不是应用侧的“降频 API”。

当应用从 120 FPS 改成 60 FPS 时，每帧目标从约 8.33 ms 变成 16.67 ms，应同步调用 `updateTargetWorkDuration()`。继续报告旧目标会让系统收到与产品策略不一致的性能需求。

Hint session、thermal status 与 headroom 分工如下：

- hint session：描述当前 workload 的目标和实际耗时；
- status/headroom：说明整机热状态与趋势；
- 应用质量策略：决定减少多少工作。

### CPU/GPU capacity headroom 的使用

API 36 的 `SystemHealthManager.getCpuHeadroom()` 与 `getGpuHeadroom()` 返回 0—100 的容量余量。调用可能发生同步 Binder transaction，首次或自定义参数时可能更慢，不要放在渲染关键线程。

设备可以不支持这两个 API；调用方应处理 `UnsupportedOperationException` 和 `NaN`，并遵守 `getCpuHeadroomMinIntervalMillis()`、`getGpuHeadroomMinIntervalMillis()`。判断瓶颈时：

- GPU headroom 长期接近 0、CPU 较高：先减少像素与 GPU pass；
- CPU headroom 长期接近 0、GPU 较高：先减少脚本、物理、分词或后处理；
- 两者都低且 thermal headroom 上升：同时降低目标 FPS 与内容复杂度；
- 单次值突变：先看一段时间窗口，避免把 TOCTOU 当成稳定结论。

### Sustained Performance Mode

API 24 的 Sustained Performance Mode 只在设备声明支持时可用。它为长时间负载选择更可预测的性能区间，通常会牺牲峰值。它不替代应用降载，也不保证固定频率或固定 FPS。测试应分别比较普通模式与 sustained mode 的首次峰值、稳定阶段和温度。

## Framework 对后台任务的 thermal 限制

Android 17 的 `JobScheduler` 使用 `ThermalStatusRestriction`。TOP_APP bias 的 job 不受该 restriction 限制；其他 job 大致按三档处理：

- LIGHT：限制 MIN；LOW 若尚未运行或已经 overtime 也受限；
- MODERATE：放行 user-initiated job；expedited 和 HIGH 还要满足运行状态、重试与 overtime 条件；
- SEVERE 及以上：限制全部非 TOP_APP job。

这是 Framework 的后台调度策略，不等于应用进程在 SEVERE 时必然停止。调试 job 延迟时，可以结合 pending/stop reason 判断是否属于 thermal device state。

## 用 Perfetto 建立温控证据

### 录制时需要哪些数据

建议同时打开：

- `sched/sched_switch`、`sched/sched_wakeup`；
- `power/cpu_frequency`、`power/cpu_idle`；
- FrameTimeline 或目标应用的渲染打点；
- `thermal/thermal_temperature`；
- `thermal/thermal_zone_trip`；
- `thermal/cdev_update`；
- `thermal/thermal_power_cpu_limit`；
- `thermal/thermal_power_devfreq_limit`；
- 使用 `power_allocator` 时再开 `thermal_power_allocator/*`；
- 厂商提供的 GPU、NPU、thermal daemon trace。

这些 thermal tracepoint 是否存在取决于内核配置和设备权限。标准事件缺失时，不要把空轨道当成“没有温控”；继续查看 HAL status、cooling state、频率上限和 vendor 证据。

### Framework status counter

Android 17 的 `ThermalManagerService.setStatusLocked()` 写入名为 `ThermalManagerService.status` 的 trace counter。可以先用这条 SQL 查看全局 skin status：

```sql
SELECT
  c.ts / 1e9 AS time_s,
  CAST(c.value AS INT) AS thermal_status
FROM counter c
JOIN counter_track t ON c.track_id = t.id
WHERE t.name = 'ThermalManagerService.status'
ORDER BY c.ts;
```

数值 0—6 对应 NONE、LIGHT、MODERATE、SEVERE、CRITICAL、EMERGENCY、SHUTDOWN。若查询为空，先确认录制配置包含 power atrace 类别，再执行 `SELECT DISTINCT name FROM counter_track` 查找设备上的实际轨道。

### CPU 频率轨道

CPU frequency 通常位于 `counter` 与 `cpu_counter_track`。下面的查询用于确认轨道名和频率变化：

```sql
SELECT
  c.ts / 1e9 AS time_s,
  t.cpu,
  t.name,
  c.value AS frequency_khz
FROM counter c
JOIN cpu_counter_track t ON c.track_id = t.id
WHERE t.name GLOB '*cpufreq*'
ORDER BY c.ts, t.cpu;
```

某些设备的轨道名不同，应先枚举 `cpu_counter_track`。频率降低还可能来自 idle、普通 DVFS、battery saver、Power HAL 或其他 QoS request；需要和 status、trip、`cdev_update`、CPU runnable 状态一起判断。

### 证据链的阅读顺序

当持续负载的帧时间恶化时，按下面顺序对齐时间：

1. workload 是否先变重：场景、分辨率、输入规模、线程数量；
2. skin/SoC 温度与 HAL severity 是否上升；
3. thermal trip 或 cooling state 是否变化；
4. CPU/GPU 频率上限是否随之降低；
5. runnable 线程是否在低频下持续占用 CPU，GPU work 是否延长；
6. FrameTimeline、应用 slice 或吞吐从哪个点开始恶化。

只有频率下降且 CPU 利用率高，还不能单独确认 thermal。只有 status 升级，也不能证明某个 cluster 已被限频。两侧信号在时间上对应，结论才足够稳固。

### `dumpsys` 与快照

测试前后可以保存：

```bash
adb shell dumpsys thermalservice
adb shell dumpsys power
adb shell cat /sys/class/thermal/thermal_zone0/temp
adb shell cat /sys/class/thermal/cooling_device0/cur_state
```

zone/cooling device 编号不稳定，正式脚本应先按 `type` 建立映射。`dumpsys thermalservice` 可以看到 Framework 当前温度、status、HAL 连接与 headroom 相关状态；厂商字段和权限随 build 变化。

## 系统与 OEM 调优

### 先确认控制权在哪一层

调内核参数前，先回答：

- thermal zone 使用哪个 governor；
- cooling device 是否真的绑定到该 zone；
- vendor daemon 是否同时写 QoS、频率或充电限制；
- HAL severity 来自原始温度、虚拟 skin 模型还是固件；
- 芯片固件是否还有不可见的硬件保护。

多层同时控制同一资源时，修改一处参数可能没有效果，也可能引起两个控制器互相追逐。

### 调整 `power_allocator`

建议按以下顺序：

1. 固定环境、屏幕、充电与 workload；
2. 记录温度、PID 各项、总请求/授予功耗和 actor state；
3. 先校准 `sustainable_power`；
4. 再调整 `k_pu` 与 `k_po` 的升温/过热响应；
5. 最后评估积分项，`k_d` 保持文档建议的默认值，除非有充分数据；
6. 重复冷热机、不同环境温度和制造偏差测试。

调参目标应同时包含安全温度、温度过冲、性能振荡、稳定吞吐与功耗。追求更晚触发 throttling 可能把代价转移到机身温度、电池寿命或保护关机。

### HAL 与 skin 模型

同 SoC 的不同设备可以有不同散热结构、传感器位置和握持温度限制。HAL 的 skin 模型与 severity threshold 需要按整机校准，不能复制另一台设备的绝对温度表。

验证模型时应覆盖：

- 横屏/竖屏、手持/支架、保护壳；
- 充电、蜂窝、Wi-Fi、相机与高亮度；
- 冷环境、常温、高环境温度；
- CPU、GPU、NPU、ISP、modem 等不同热源；
- 快速升温和长时间稳态。

## 可复现的测试方法

每次测试至少记录：

- 设备型号、build、kernel、vendor image；
- 环境温度、气流、保护壳、摆放与握持方式；
- 电池电量、是否充电、充电功率；
- 屏幕亮度、刷新率、网络和音量；
- workload 版本、场景、分辨率、FPS 目标和输入；
- 测试前各关键 sensor 温度；
- time-to-LIGHT/MODERATE/SEVERE；
- cooling state、频率上限、thermal status dwell time；
- 稳态 P50/P95 帧时间或吞吐；
- 功耗、温度峰值和恢复时间。

每轮开始前回到相同初始温度。环境温度变化会显著改变可持续功耗，但“升高 5°C 就提前固定百分比”没有跨设备通用公式，应报告本机实测曲线。

至少比较三种状态：

1. 冷机短测，确认峰值能力；
2. 长时间稳态，确认持续性能；
3. thermal-aware 降载，确认帧稳定性、画质与功耗的综合结果。

## 常见误判

### “status 没变，所以没有温控”

Framework 全局 status 只聚合 skin severity。内核或厂商固件可能已经限制局部资源，而 skin status 尚未升档。继续检查 cooling state、频率上限和 vendor trace。

### “headroom 0.8 比 0.4 更安全”

Thermal headroom 越高越接近 SEVERE，0.8 的热压力高于 0.4。CPU/GPU capacity headroom 的方向相反，这两个 API 最容易在这里混淆。

### “降低 CPU 频率一定能解决热问题”

设备可能由 GPU、NPU、ISP、modem、显示或充电主导发热。CPU 限频还可能延长任务运行时间。先定位主热源和 cooling actor，再选择动作。

### “SEVERE 会自动下线 CPU”

Framework severity 没有标准 hotplug 映射。核心离线通常来自厂商内核或 daemon 的额外策略。

### “主动降载等于应用主动降频”

应用通过分辨率、FPS、并发、模型和任务节奏减少工作；频率与功耗限制由系统和硬件策略决定。ADPF hint 描述 workload 目标，也不授予应用直接控制频率的能力。

## 版本演进

| Android 版本 | 相关变化 |
|---|---|
| Android 7.0 / API 24 | Sustained Performance Mode |
| Android 8.0 / API 26 | Thermal HAL 1.0 |
| Android 10 / API 29 | HIDL Thermal HAL 2.0、thermal status 与 callback |
| Android 11 / API 30 | Java `PowerManager.getThermalHeadroom()` |
| Android 12 / API 31 | Performance Hint API；NDK thermal headroom 从 API 31 提供 |
| Android 14 / API 34 | AIDL Thermal HAL v1 |
| Android 15 / API 35 | AIDL HAL v2 cooling callback；Java/NDK headroom thresholds |
| Android 16 / API 36 | AIDL HAL v3 skin forecast 与 threshold callback；Java/NDK headroom listener；CPU/GPU capacity headroom |
| Android 17 / API 37 | Thermal HAL 仍为 AIDL v3；Framework 延续 headroom/forecast，并支持自定义 thermal policy 的虚拟设备 status 路由 |

## Android 17 / Kernel 6.18 源码索引

### Kernel `android17-6.18-2026-06_r6`

| 路径 | 关注点 |
|---|---|
| `drivers/thermal/thermal_core.c` | zone 更新、HOT/CRITICAL 与硬件保护 |
| `drivers/thermal/gov_step_wise.c` | `throttle`、trend 与 target state |
| `drivers/thermal/gov_power_allocator.c` | PID、功耗分配、power actor |
| `drivers/thermal/cpufreq_cooling.c` | cpufreq cooling 与 `freq_qos` |
| `drivers/thermal/devfreq_cooling.c` | devfreq cooling |
| `drivers/thermal/thermal_trace.h` | 通用 thermal tracepoint |
| `drivers/thermal/thermal_trace_ipa.h` | power allocator tracepoint |
| `Documentation/driver-api/thermal/power_allocator.rst` | governor 参数与 power actor 契约 |

### Android `android-17.0.0_r1`

| 路径 | 关注点 |
|---|---|
| `hardware/interfaces/thermal/aidl/android/hardware/thermal/` | AIDL HAL v1—v3 |
| `frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java` | HAL 连接、status 聚合、headroom |
| `frameworks/base/core/java/android/os/PowerManager.java` | App thermal API |
| `frameworks/base/core/java/android/os/health/SystemHealthManager.java` | CPU/GPU capacity headroom |
| `frameworks/native/include/android/thermal.h` | NDK thermal API |
| `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/restrictions/ThermalStatusRestriction.java` | JobScheduler thermal policy |

## 官方资料

- [Android thermal mitigation](https://source.android.com/docs/core/power/thermal-mitigation)
- [PowerManager thermal APIs](https://developer.android.com/reference/android/os/PowerManager)
- [Optimize games for thermal conditions](https://developer.android.com/games/optimize/thermal)
- [ADPF overview](https://developer.android.com/games/optimize/adpf)
- [Perfetto trace analysis with SQL](https://perfetto.dev/docs/analysis/trace-analysis-with-sql)
- [Linux power allocator documentation](https://docs.kernel.org/driver-api/thermal/power_allocator.html)

## 与其他章节的关系

- **[5.4 DVFS](04-dvfs.md)**：频率、电压和 QoS 如何决定执行点；
- **[5.5 Thermal 管控](05-thermal.md)**：从传感器到应用的入门视图；
- **[5.9 ADPF](09-adpf.md)**：Performance Hint、Game Mode 与 thermal API 的应用方法；
- **[8.9 游戏性能](../../part2-performance/ch08-rendering/09-game-performance.md)**：帧率、渲染负载与持续性能；
- **[11.1 功耗模型](../../part2-performance/ch11-power/01-power-model.md)**：功耗、能量与发热的关系。
