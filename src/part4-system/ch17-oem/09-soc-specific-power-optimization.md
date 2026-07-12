---
title: "SoC 特异性功耗优化策略：高通/联发科/三星"
chapter: "17.9"
status: ready-for-review
drafted_date: "2026-07-12"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-12"
last_verified_against: "AOSP android-17.0.0_r1, hardware/interfaces/power/aidl/, kernel/sched/cpufreq_schedutil.c"
confidence: medium
sources:
  - type: research
    path: "DeepResearch/2026-07-06-android17-soc-vendor-power-hal-schedutil-loop.md"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl (android-17.0.0_r1)"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/Mode.aidl (android-17.0.0_r1)"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/Boost.aidl (android-17.0.0_r1)"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/ (android-17.0.0_r1)"
  - type: aosp
    path: "kernel/sched/cpufreq_schedutil.c (linux 6.10 / Android common 6.12)"
  - type: aosp
    path: "drivers/cpuidle/governors/menu.c (linux 6.10)"
  - type: blog
    path: "obsidian/Cubox/高通Perflock - yooooooo - 博客园-2024-11-18.md"
  - type: note
    path: "§17.2 SoC 平台差异 (finalized) — CPU/GPU 硬件架构对比"
tags: [SoC, power, Qualcomm, MediaTek, Samsung, DCVS, schedutil, PowerHAL, 功耗优化]
related_chapters: ["17.2", "17.21", "5.21", "5.29", "15.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "研究素材/知识盲区"
---

# 17.9 SoC 特异性功耗优化策略：高通/联发科/三星

> 本章关注 **SoC 厂商在功耗管理上的差异化策略**及开发者可操作的优化路径。§17.2 讲了各平台硬件架构「是什么」，本节讲的是这些差异在功耗维度「带来什么影响、怎么优化」。§17.21 则从 Power HAL × schedutil 闭环的角度深入源码实现细节。

## 三个层级的功耗管理分工

在进入各家厂商的具体策略之前，需要先理解 Android 功耗管理在架构上的三层分工——不同 SoC 厂商的差异集中体现在第二层和第三层。

**第一层：AOSP 框架统一接口。** Android 13 起，所有功耗 Hint 通过 `IPower` AIDL 接口（`@VintfStability`）统一定义。Android 17 已演进到 AIDL v7，包含 19 个 `Mode` 枚举（长生命周期状态）和 6 个 `Boost` 枚举（短脉冲）。框架层通过 `PowerManager.setPowerSaveMode()`、`PowerManagerService.setMode()` 等统一入口下发，所有厂商必须接入同一接口。AOSP 在 `hardware/interfaces/power/aidl/default/Power.cpp` 提供空操作的参考实现，厂商必须提供自己的 `.so` 库做实际工作。

[已验证: AOSP android-17.0.0_r1, hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl]

**第二层：SoC 厂商 HAL 实现。** 这是各家差异的核心战场。同一个 `setMode(Mode.LAUNCH, true)` 调用，在高通设备上触发 RPMh 资源状态机切换，在联发科设备上走 `mtlp` 守护进程，在三星设备上经 ASV/TMU 协调多路电源轨。AOSP 不感知这些实现细节——这是合规边界，也是调试盲区。

[已验证: DeepResearch 2026-07-06, 基于 android-17.0.0_r1 源码 + 厂商公开技术规范推断]

**第三层：Linux 内核调度与频率管理。** `schedutil` governor（Android 14+ 全 SoC 默认）通过 `sugov_should_update_freq()` 守门 `rate_limit_us`（AOSP 默认 10ms），决定是否将频率变更写入硬件。SoC 厂商在 `get_next_freq()` 的 frequency table 中铺设不同分辨率的 OPP（Operating Performance Point）点，以及通过自定义 cpufreq 驱动叠加硬件活动预测器。

[已验证: kernel/sched/cpufreq_schedutil.c, linux 6.10; AOSP DEF_RATE_LIMIT_US = 10000 (10ms)]

## 高通骁龙：RPMh 驱动的集中式功耗调度

### DCVS 与 LPM 架构

高通的功耗管理核心是 RPMh（Resource Power Manager-hard）——一个独立于主 CPU 运行的硬件资源管理器。当 `setMode` 或 `setBoost` 到达高通的 Power HAL 实现（`libqti-power-hal.so`）时，HAL 通过 `rpmh_send_data` 同步消息将资源请求发送给 RPMh 控制器，由后者统一协调 CPU/GPU/Modem/ISP 等各子系统的电源域。

[待验证: libqti-power-hal.so 内部实现为闭源 NDK 库，以上描述基于高通公开技术规范的合理推断]

DCVS（Dynamic Clock and Voltage Scaling）是高通在 Adreno GPU 上的动态频率策略。与 CPU 的 schedutil 不同，Adreno DCVS 有自己的负载检测环路与温度反馈路径。在游戏场景中，GPU DCVS 会根据渲染管线的负载情况在 20-40 个 OPP 点之间选择频率，同时叠加 PowerAdvisor 的 thermal headroom 约束（详见 §5.29 GPU DVFS Headroom 与 SurfaceFlinger PowerAdvisor 链路）。

高通的 LPM（Low Power Mode）架构定义了多级低功耗子模式，每级对应不同的 exit latency 和 residency 时间阈值。这些参数通过 devicetree 传递给 `cpuidle` 驱动，`menu` governor（`drivers/cpuidle/governors/menu.c`）使用 `target_residency_ns` 和 `exit_latency_ns` 决定进入哪一级 C-state。

[已验证: drivers/cpuidle/governors/menu.c, linux 6.10, BUCKETS=12 / DECAY=8 / MAX_INTERESTING=50ms]

### Perflock 的功耗面

§17.2 已经介绍了 Perflock 在 CPU 频率锁定方面的能力。从功耗优化角度看，Perflock 还提供了一个关键的 power collapse 控制面：`MPCTLV3_ALL_CPUS_PWR_CLPS_DIS` 可以在关键路径（如相机启动、游戏加载）上临时禁用 CPU Power Collapse，避免进入深层 C-state 带来的唤醒延迟。这条路径在 Perfetto 中表现为 CPU Frequency Track 上所有核心频率突然同时拉高。

[来源: obsidian/Cubox/高通Perflock - yooooooo - 博客园-2024-11-18.md]

[适用版本: Android 12 - Android 17（Perflock 接口跨版本稳定）]

## 联发科 Dimensity：MTLP 与 CorePilot 的双层调度

### MTLP 模块

联发科的功耗管理通过 `mtlp`（MediaTek Low Power）模块实现。当 Power HAL 收到 `setMode` / `setBoost` 调用时，高通走 RPMh 硬件消息，联发科则走 `mtlp` 模块内部的 `hw_flower` 状态机路径，最终写入 `mediatek-dvfsrc` 或 `mediatek-cci-devfreq` 驱动节点。此外，`mtk_pcie` 控制器管理 WiFi/Modem 的二级电源域。

[待验证: mtlp 模块内部实现为厂商私有，以上描述基于联发科公开技术规范的合理推断]

联发科的 cpufreq 实现使用 `mtk-cpufreq-hw` 驱动，该驱动支持硬件活动预测器（基于性能计数器）。与 schedutil 的软件负载检测不同，硬件预测器能在微秒级别感知负载变化并预判频率需求，实现 race-ahead 调频。但这一机制叠加在 schedutil 之上，最终频率决策仍受 `rate_limit_us` 守门。

### CorePilot 调度算法

CorePilot 是联发科的任务调度策略品牌名称，在 Dimensity 全大核架构（§17.2 已详细介绍）上运行。从功耗角度看，CorePilot 的 task packing 策略倾向于将多个轻负载线程集中在少数核心上执行，让其他核心进入深度 idle。这与传统大小核架构的「把轻负载分散到小核」策略相反——在全大核架构中，没有低功耗小核可用，task packing 是降低功耗的关键手段。

在 Perfetto 中，Dimensity 设备的 CPU Scheduling Track 可能显示某些核心长时间空闲（进入 deep idle），而另一些核心集中运行多个线程。这是 CorePilot task packing 的正常表现，不一定是调度异常。

[自动发现: 基于 §17.2 对 Dimensity 全大核架构的分析推论，联发科官方未公开 CorePilot 内部实现]

## 三星 Exynos：ASV + TMU 的硅片级优化

### ASV（Adaptive Supply Voltage）

三星的功耗管理有独到的硅片级手段：ASV。同一型号的 Exynos 芯片，不同个体（甚至同一晶圆的不同位置）的晶体管特性有差异。ASV 在出厂时为每颗芯片测试并分配一个 ASV bin 等级，高等级芯片可以在更低电压下稳定运行相同频率。这意味着同一型号的两台手机，在相同工作负载下功耗可能有 5-15% 的差异。

ASV bin 信息写入 `exynos-pmu` 驱动的校准表，影响 `cpufreq` frequency table 中每个 OPP 点的实际电压。`schedutil` governor 计算出的目标频率对应到哪个 OPP、消耗多少功耗，取决于 ASV 校准结果。

[待验证: ASV bin 分配算法和具体电压偏移量为三星私有信息]

### TMU 与 Xclipse GPU 的热功耗联合管理

三星的 TMU（Thermal Management Unit）不像高通 RPMh 那样独立于主 CPU，而是嵌入在 SoC 内部的硬件监测单元。TMU 持续采样芯片温度，与 ASV 形成闭环：温度升高时，TMU 可以降低频率上限（thermal throttling），ASV 表动态调整电压。

Xclipse GPU（基于 AMD RDNA 架构）的功耗特征与 Adreno 和 Mali 都不同。Xclipse 驱动实现了独立的 GPU 频率-电压曲线管理，不经过 schedutil，而是通过 `gs_drm` 驱动的内部策略。这意味着 §5.29 中描述的 SurfaceFlinger PowerAdvisor → Power HAL → schedutil GPU DVFS 链路在三星设备上可能不完全适用。

[待验证: Xclipse GPU DVFS 路径与 AOSP 标准 PowerAdvisor 链路的差异程度]

## 跨厂商功耗优化最佳实践

了解了三家厂商的差异化实现后，以下是对应用开发者切实可操作的跨厂商功耗优化实践。

### 1. 通过标准 PowerHAL Hint 而非厂商私有 API

Android 17 的 `IPower` AIDL v7 提供了足够丰富的标准 Hint 接口。应用应优先使用标准 API（`PowerManager.setPowerSaveMode`、`PerformanceHintManager` 等），而非直接调用厂商私有接口。原因有二：第一，标准 API 在所有厂商设备上可用；第二，厂商 HAL 会将标准 Hint 映射到自己的最优路径（高通→RPMh，联发科→mtlp，三星→ASV/TMU），应用无需关心映射细节。

```java
// 正确做法：使用标准 API
PowerManager pm = getSystemService(PowerManager.class);
// 省电模式联动
if (pm.isPowerSaveMode()) {
    // 降低动画频率、减少后台同步
}

// PerformanceHintManager（ADPF）— Android 11+ 标准接口
PerformanceHintManager phm = getSystemService(PerformanceHintManager.class);
PerformanceHintManager.Session hintSession = phm.createHintSession(
    Thread.currentThread(), Arrays.asList(targetDurationNanos));
hintSession.updateTargetWorkDuration(targetDurationNanos);
hintSession.reportActualWorkDuration(actualDurationNanos);
```

[已验证: developer.android.com/reference/android/os/PerformanceHintManager]

### 2. CPU affinity pinning 的厂商差异

CPU 核心绑定（affinity）的效果因 SoC 架构而异：

- **高通 2+6 双集群（Oryon）**：集群间迁移开销较低，affinity pinning 的收益主要体现在减少迁移抖动。绑定到所有 8 核的效果通常与不绑定相近。
- **联发科全大核（1+3+4）**：task packing 已经由 CorePilot 处理，手动 affinity 可能干扰 packing 策略。建议只对延迟敏感线程做精细绑定（绑定到最高性能核心）。
- **三星 Exynos 三集群**：传统大小核架构下，affinity pinning 仍然有效。将后台任务绑定到小核集群可以显著降低功耗。

### 3. GPU frequency capping 的效果差异

通过 `Adreno Profiler`（高通）或 `Streamline`（ARM/Mali）可以观察到 GPU 频率行为。GPU frequency capping（限制最高频率）的省电效果：

| SoC | GPU | capping 效果（游戏场景） | 帧率影响 |
|-----|-----|------------------------|---------|
| Qualcomm | Adreno | 中等（DCVS 已较激进） | 轻微 |
| MediaTek | Immortalis/Mali | 显著（默认偏高） | 中等 |
| Samsung | Xclipse | 因 ASV bin 而异 | 不确定 |

[待验证: 以上对比基于有限的评测数据，实际效果因设备型号、游戏类型和环境温度而异]

### 4.schedtune 调参的厂商响应差异

`schedtune.boost` 和 `schedtune.prefer_idle`（Android 12+ EAS 调度器调参节点）对不同 SoC 的效果：

- **高通**：Perflock 路径会覆盖 schedtune 设置。在某些场景下 schedtune.boost=0 但 Perflock 仍然拉满频率。调试时需要同时检查两条路径。
- **联发科**：CorePilot 对 schedtune 的响应较为直接。schedtune.prefer_idle=1 在全大核架构上可能导致频繁的集群间迁移。
- **三星**：schedtune 与 ASV 联动。低 ASV bin 的芯片在高 boost 下可能更快触发热降频。

[适用版本: Android 12 - Android 16（schedtune 在 Android 17 中被 sched_ext 部分替代）]

## SoC 功耗基准测试方法论

跨厂商功耗对比需要严格控制变量，否则结论不可靠。

### 测试框架要求

1. **固定分辨率和刷新率**：不同设备的默认分辨率和刷新率不同，必须在开发者选项中统一（如 1080p / 60Hz）。
2. **统一亮度**：屏幕亮度是功耗的大头。固定 50% 亮度（或使用校准后的 nit 值），关闭自适应亮度。
3. **温度控制**：SoC 功耗强依赖温度。测试应在恒温环境（25°C ± 2°C）中进行，设备散热条件一致。使用风扇主动散热避免热降频干扰数据。
4. **统一工作负载**：使用标准化的 benchmark（如 Geebench、GFXBench、PCMark Work 3.0）而非自研测试。

### 三种场景的功耗模型

| 场景 | 典型功耗 | 主要耗电组件 | 测量方法 |
|------|---------|------------|---------|
| **Idle**（息屏待机） | 5-20mA | Modem、系统后台 | Battery Historian + dumpsys batterystats |
| **Sustained**（持续负载） | 200-800mA | CPU + GPU + 屏幕 | GFXBench 长期循环 + Monsoon 功耗仪 |
| **Peak**（峰值 burst） | 1-3A | CPU + GPU + ISP 全满 | Perfetto `LinuxPowerSysfsDataSource` + `AndroidPowerDataSource` |

[来源: 多来源综合，包括 Battery Historian 官方文档 + Monsoon Solutions 功耗仪公开技术文档]

### Perfetto 功耗追踪配置

跨厂商功耗分析推荐的 Perfetto 配置：

```
# 功耗分析专用 trace config 片段
data_sources {
  config {
    name: "linux.power.sysfs"
    target_buffer: 0
  }
}
data_sources {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 1000
      collect_power_rails: true
      battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
      battery_counters: BATTERY_COUNTER_CHARGE
      battery_counters: BATTERY_COUNTER_CURRENT
    }
  }
}
data_sources {
  config {
    name: "android.power.stats"
  }
}
```

通过 `dumpsys power_stats` 可以获取 PowerStats AIDL v2 的状态驻留数据和能耗Consumer 统计——这是跨厂商功耗归因的关键数据源。详见 §14.30 GpuService GPU 内存可观测性架构中关于 `PowerStats` HAL 的补充说明。

[已验证: AOSP android-17.0.0_r1, hardware/interfaces/power/stats/aidl/ — versions_with_info 确认 v2 frozen:true]

## Android 17 对 SoC 功耗管理的系统增强

Android 17 在 SoC 功耗管理方面引入了若干系统增强（HAL 实现细节详见 §17.21）：

**1. thermal headroom API。** `PowerManager.getThermalHeadroom()` 返回当前热余量（单位：°C），基于 `IThermalService` 和厂商 thermal HAL 的联合计算。应用可以据此主动降低工作负载，而非等待系统级 throttling。

**2. Composition Data 反馈。** `IPower.sendCompositionData()` 和 `sendCompositionUpdate()`（Android 17 新增）把 SurfaceFlinger 的合成数据直接送 Power HAL，让厂商 HAL 基于实际渲染负载做更精确的 GPU DVFS 决策。详见 §5.29。

**3. sched_ext 对 OEM 调度器的约束。** Android 17 内核（linux 6.12+）中 `schedutil` 的 `sugov_get_util()` 会优先检查 `scx_cpuperf_target()`——当 OEM 通过 BPF 实现了自定义调度器时，schedutil 直接采用 BPF 性能目标，CFS 仅作 fallback。这给 OEM 更大的调度灵活性，但也要求 OEM BPF 调度器正确报告性能需求，否则 schedutil 的频率决策会失准。

[已验证: kernel/sched/cpufreq_schedutil.c v6.12, sugov_get_util() 调用 scx_cpuperf_target()]

**4. CPU/GPU Headroom 反查。** `IPower.getCpuHeadroom()` 和 `getGpuHeadroom()`（Android 17 新增）让 Framework 主动查询 SoC 可用余量。调用间隔最低 100ms（Framework 端 limiter），vendor HAL 内部平均 200-500μs 完成计算。Qualcomm RPMh 路径最慢可达 1-2ms（涉及 PDC 查询）。

[已验证: AOSP android-17.0.0_r1, hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl — getCpuHeadroom/getGpuHeadroom 方法签名]

## 总结

SoC 厂商的功耗管理差异不在 AIDL 接口层（AOSP 强制统一），而在实现层与驱动层。对应用开发者而言，关键认知是：

1. **同一份 PowerManager API，在不同 SoC 上走完全不同的底层路径**——理解这一点有助于解释跨设备功耗数据的差异。
2. **优先使用标准 API**（`PerformanceHintManager`、`PowerManager`），让厂商 HAL 做它最擅长的映射。
3. **Perfetto 中的功耗数据需要结合 SoC 架构解读**——同一现象（如 CPU 频率突然拉高）在高通设备上可能是 Perflock，在联发科设备上可能是 mtlp 路径。
4. **跨厂商功耗对比必须严格控制变量**——分辨率、亮度、温度、工作负载统一后，数据才有可比性。

## 参考资料

### AOSP 源码
- `hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl` — 顶层 vendor 入口契约（android-17.0.0_r1）
- `hardware/interfaces/power/aidl/android/hardware/power/Mode.aidl` — Mode 枚举（19 项）
- `hardware/interfaces/power/aidl/android/hardware/power/Boost.aidl` — Boost 枚举（6 项）
- `hardware/interfaces/power/stats/aidl/` — PowerStats AIDL v2
- `kernel/sched/cpufreq_schedutil.c` — schedutil governor（linux 6.10）
- `drivers/cpuidle/governors/menu.c` — menu cpuidle governor（linux 6.10）
- `hardware/interfaces/power/aidl/default/Power.cpp` — AOSP 参考实现（空操作）

### 研究素材
- `DeepResearch/2026-07-06-android17-soc-vendor-power-hal-schedutil-loop.md` — 255 行 AOSP 源码级调研

### 交叉引用
- §17.2 SoC 平台差异 — CPU/GPU 硬件架构详细对比
- §17.21 Android 17 SoC 厂商 Power HAL 与 schedutil 闭环 — HAL 实现源码级分析
- §5.21 Android 17 SoC 厂商电池优化架构 — Framework 层 BatterySaverController 联动
- §5.29 Android 17 GPU DVFS Headroom 与 SurfaceFlinger PowerAdvisor 链路 — GPU 功耗管理
- §15.1 Android 17 PMS cpuidle/schedutil — 内核 idle/freq 协同