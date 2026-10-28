---
title: Power HAL、schedutil 与 Power Stats
chapter: '19.4'
section: '19.4'
status: finalized
applicable_versions: Android 14 (API 34) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 Power framework and frozen Power AIDL v7/PowerStats AIDL v2; Android public APIs current on 2026-08-14; android17-6.18-2026-06_r6 schedutil, sched_ext and vendor driver sources
confidence: medium
sources:
- type: research
  path: DeepResearch/2026-07-06-android17-soc-vendor-power-hal-schedutil-loop.md
- type: aosp
  path: hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/IPower.aidl
- type: aosp
  path: hardware/interfaces/power/aidl/android/hardware/power/Mode.aidl (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/Mode.aidl
- type: aosp
  path: hardware/interfaces/power/aidl/android/hardware/power/Boost.aidl (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/Boost.aidl
- type: aosp
  path: hardware/interfaces/power/stats/aidl/ (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/
- type: aosp
  path: kernel/sched/cpufreq_schedutil.c (linux 6.10 / Android common 6.12)
- type: aosp
  path: drivers/cpuidle/governors/menu.c (linux 6.10)
- type: blog
  path: obsidian/Cubox/高通Perflock - yooooooo - 博客园-2024-11-18.md
- type: note
  path: §19.2 SoC 平台差异 (finalized) — CPU/GPU 硬件架构对比
- type: research
  path: DeepResearch/2026-07-10-android17-soc-vendor-power-hal-stats-schedutil-closedloop.md
- type: research
  path: DeepResearch/2026-07-15-android17-sched-ext-6.18-vendor-hook-cpufreq-loop.md
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java
- type: aosp
  path: frameworks/native/services/powermanager/PowerHalController.cpp (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/powermanager/PowerHalController.cpp
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/hint/HintManagerService.java
- type: kernel
  path: kernel/sched/cpufreq_schedutil.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c
- type: kernel
  path: kernel/sched/ext.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c
- type: kernel
  path: include/trace/hooks/sched.h (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/hooks/sched.h
- type: kernel
  path: drivers/soc/qcom/rpmh.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/soc/qcom/rpmh.c
- type: kernel
  path: drivers/soc/qcom/rpmh-rsc.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/soc/qcom/rpmh-rsc.c
- type: kernel
  path: drivers/cpufreq/qcom-cpufreq-hw.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/qcom-cpufreq-hw.c
- type: kernel
  path: drivers/cpufreq/mediatek-cpufreq.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/mediatek-cpufreq.c
- type: kernel
  path: drivers/cpufreq/mediatek-cpufreq-hw.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/mediatek-cpufreq-hw.c
- type: kernel
  path: drivers/soc/samsung/exynos-asv.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/soc/samsung/exynos-asv.c
- type: kernel
  path: drivers/thermal/samsung/exynos_tmu.c (android17-6.18-2026-06_r6)
  url: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/thermal/samsung/exynos_tmu.c
- type: official-doc
  path: PerformanceHintManager API
  url: https://developer.android.com/reference/android/os/PerformanceHintManager
- type: official-doc
  path: PowerManager API
  url: https://developer.android.com/reference/android/os/PowerManager
- type: official-doc
  path: SystemHealthManager API
  url: https://developer.android.com/reference/android/os/health/SystemHealthManager
- type: official-doc
  path: Perfetto battery counters and power rails
  url: https://perfetto.dev/docs/data-sources/battery-counters
- type: official-doc
  path: AOSP Power statistics HAL
  url: https://source.android.com/docs/core/power/power-stats-hal
- type: aosp
  path: hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl
- type: aosp
  path: hardware/interfaces/power/stats/aidl/default/
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/default/main.cpp
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/
- type: research-note
  path: DeepResearch/2026-07-08-android17-powerstats-hal-oem-implementation.md
- type: aosp
  path: hardware/interfaces/power/stats/aidl/Android.bp (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/Android.bp
- type: aosp
  path: hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl
- type: aosp
  path: hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsLogger.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsLogger.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/TimerTrigger.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/TimerTrigger.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/BatteryTrigger.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/BatteryTrigger.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java
- type: aosp
  path: frameworks/base/core/res/AndroidManifest.xml ACCESS_FINE_POWER_MONITORS (android-17.0.0_r1)
  url: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/res/AndroidManifest.xml
- type: official-doc
  path: AOSP Power stats HAL
  url: https://source.android.com/docs/core/power/power-stats-hal
tags:
  - soc
  - power
  - qualcomm
  - mediatek
  - samsung
  - dcvs
  - schedutil
  - powerhal
related_chapters:
- '19.2'
- '19.3'
- '5.2'
- '5.4'
- '11.1'
- '15.5'
consolidated_from:
- 17.21-android17-soc-vendor-power-hal-schedutil-loop.md
- src/part4-system/ch19-oem/08-power-hal-schedutil-soc-power.md
- src/part4-system/ch19-oem/09-power-stats-hal-oem-implementation.md
last_consolidated_at: '2026-08-24'
---

# Power HAL（Hardware Abstraction Layer，硬件抽象层）、schedutil 与 Power Stats

同一款应用在三台旗舰机上可能出现不同的耗电、温升和持续性能，原因通常不止 CPU 核心数量。系统软件会把每帧可用的处理时间、交互、相机、音频等工作负载信息交给厂商实现，内核再结合调度负载、频率约束、温控上限和固件决策控制硬件。SoC 型号、整机散热、屏幕、基带、厂商参数及应用行为都会改变结果。我们把本文涉及的两条路径分开讲：Power HAL 把场景提示传给厂商电源策略，schedutil 根据利用率调节 CPU 频率，Power Stats HAL 汇报设备能量实体和状态驻留。控制与统计是两条相关但独立的路径。

> 源码基线：Android 17 / API 37 / AOSP `android-17.0.0_r1`；内核标签 `android17-6.18-2026-06_r6`；设备可能使用其他内核分支。厂商差异只讨论公开源码能证明的范围。

## Power Hint、schedutil 与 SoC 控制环

<!-- gracker-diagram: a202-01-control-statistics -->
![电源控制与能量统计的两条路径](../../assets/diagrams/ch19/a202-01-control-statistics.png)

图：Power HAL 传递场景策略，schedutil 形成 CPU 频率请求，Power Stats 报告结果；统计接口不直接参与 schedutil 的选频。

### 先分清四层职责

<!-- gracker-diagram: a202-02-four-layers -->
![从应用预算到硬件动作的职责](../../assets/diagrams/ch19/a202-02-four-layers.png)

图：四层接口与能力分别确认；Mode 或 Boost 枚举存在，仍需查询支持并观察设备响应。

功耗问题适合按四层排查：应用层、Framework / HAL 层、内核层、固件 / 硬件层。表格列出了每一层的典型接口和职责，我们先借助它把层次分清，再进入各层的细节。governor 是 CPU 调频策略，HAL 负责连接系统与厂商实现。把层次混在一起，很容易把提示、调度和硬件动作误写成一条固定调用链。

| 层次 | 典型接口或组件 | 谁能直接使用 | 可确认的职责 |
|---|---|---|---|
| 应用层 | `PerformanceHintManager`、`PowerManager`、`SystemHealthManager` | 普通应用，受 API 版本和设备能力约束 | 报告周期工作、读取省电与热状态、读取可选的资源余量和能耗监视器 |
| Framework / HAL 层 | `PowerManagerService`、HintManager、`android.hardware.power.IPower` | 系统进程与厂商服务 | 把系统状态、短时 `Boost` 和 Hint Session 交给厂商实现 |
| 内核层 | 调度器、`schedutil`、cpufreq/devfreq、cpuidle、thermal | 内核及特权调试工具 | 根据负载和约束选择任务位置、CPU/GPU 性能级别与空闲状态 |
| 固件 / 硬件层 | 电源控制器、DVFS 控制器、PMIC、片上热传感器 | 厂商固件与驱动 | 执行电压、时钟、电源域和过热保护动作 |

表里几个组件先交代一下：cpufreq、devfreq 和 cpuidle 分别管理 CPU 频率、其他设备频率与 CPU 空闲状态，thermal 是内核温控子系统，DVFS（Dynamic Voltage and Frequency Scaling） 配合负载调整电压和频率，PMIC（Power Management Integrated Circuit） 是电源管理芯片。这四层不是各干各的：每层都会改变下一层收到的输入或约束，再根据温度、性能和能耗结果继续调整。

可选能力要看设备实现：`IPower.aidl` 明确允许平台忽略某个 `Mode` 或 `Boost`，调用前先用 `isModeSupported()`、`isBoostSupported()` 查询支持情况。看到 AIDL（Android Interface Definition Language，Android 接口定义语言） 枚举，我们知道的只是接口契约存在；往下每一层都要重新确认。

### 冻结的 Power AIDL 契约

系统与厂商实现之间的跨进程接口契约由 AIDL 描述。`android-17.0.0_r1` 冻结的 `android.hardware.power` AIDL 是 v7：`Mode.aidl` 定义 19 个持续状态，包括 `LOW_POWER`、`SUSTAINED_PERFORMANCE`、`LAUNCH`、`GAME` 与多档相机流模式；`Boost.aidl` 定义 6 个短时提示，包括 `INTERACTION`、`DISPLAY_UPDATE_IMMINENT`、`ML_ACC`、音频和相机提示。

Hint Session 让一组线程持续报告目标时长和实际用时，`IPower` 还定义 FMQ（Fast Message Queue，快速消息队列）Session Channel、CPU/GPU headroom 和显示合成反馈等接口；headroom 是当前还能分配多少 CPU 或 GPU 资源的估计值。FMQ（Fast Message Queue） 基于共享内存，可减少高频 Binder 调用。

版本沿革要分清：CPU/GPU headroom、`SupportInfo`、`sendCompositionData()` 和 `sendCompositionUpdate()` 在冻结的 v6 接口里就有了，v7 契约继续保留这些能力。

`IPower.setMode()` 与 `setBoost()` 是 Framework 到厂商 HAL 的接口，普通应用 SDK 里没有这两个入口。应用侧能用的是 `PowerManager.isPowerSaveMode()` 读取省电模式，或动态注册 `ACTION_POWER_SAVE_MODE_CHANGED` 后调整自己的同步、动画和预取策略。`setPowerSaveModeEnabled()` 则是隐藏的 `@SystemApi`，还要求 `DEVICE_POWER` 或 `POWER_SAVER` 权限，留给系统组件使用。

厂商 Power HAL 收到提示后可以调整 CPU、GPU、内存总线或空闲策略，也可以按本机策略忽略它。要判断某次提示落在哪条硬件路径上，需要目标设备的 HAL 源码、厂商 trace marker 或寄存器级证据；“`LAUNCH` 一定调用 Qualcomm 的 RPMh 硬件资源请求通道”“`GAME` 一定锁定某档 GPU 频率”这类固定映射，要拿到证据才写得出来。

#### Mode/Boost 与 Hint Session 是两条入口

<!-- gracker-diagram: a202-03-entry-contracts -->
![Mode、Boost 与 Hint Session 的入口](../../assets/diagrams/ch19/a202-03-entry-contracts.png)

图：系统场景与应用会话是不同入口；框架校验和厂商支持之后，资源控制仍取决于设备实现。

`Mode` 和 `Boost` 由系统场景或特权调用触发，Hint Session 则由应用主动创建。我们先看系统侧这条：`PowerManagerService` 中的交互、亮灭屏、Device Idle 等事件进入 `setPowerModeInternal()` 或 `setPowerBoostInternal()`，Binder 对外暴露的相应方法要求 `DEVICE_POWER` 权限。省电策略禁用启动加速时，Framework 会过滤 `LAUNCH`：

```java
private boolean setPowerModeInternal(int mode, boolean enabled) {
    if (mode == Mode.LAUNCH && enabled && mBatterySaverStateMachine != null
            && mBatterySaverStateMachine.getBatterySaverController()
                    .isLaunchBoostDisabled()) {
        return false;
    }
    return mNativeWrapper.nativeSetPowerMode(mode, enabled);
}
```

调用从 `PowerManagerService` 经 JNI 进入 native C++ 层，再依次经过 `PowerHalController`、`PowerHalLoader` 和 `AidlHalWrapper`。这一路的 wrapper 会缓存 Mode/Boost 支持查询，连接失效后由后续调用尝试重连，并且仍保留 HIDL（旧版 HAL 接口）封装来兼容旧实现。所以在量产机上，进程间通信接口要以运行时读取为准，平台版本推不出来。

普通应用的另一条入口是 `PerformanceHintManager`，请求会进入 `HintManagerService`。系统端校验 UID（应用身份）、TGID（进程 ID）、TID（线程 ID）、进程状态和会话生命周期，再交给 `IPowerHintSession`。AIDL v7 支持 `createHintSessionWithConfig()`；v5 起还可通过可选 FMQ Channel 减少高频报告的 Binder 往返，FMQ 不可用时仍走 Binder 会话路径。

<details>
<summary>Mermaid 源码（保留供复查）</summary>

```mermaid
flowchart TD
    scene["系统场景或特权调用"] --> pms["PowerManagerService"]
    pms --> mode["IPower setMode / setBoost"]
    app["应用周期工作"] --> hint["PerformanceHintManager / HintManagerService"]
    hint --> session["IPower hint session / 可选 FMQ"]
    mode -.->|OEM 可选映射| control["uclamp / QoS / 固件资源请求"]
    session -.->|OEM 可选映射| control
    wake["调度、唤醒与约束"] --> cfs["fair-class utilization"]
    scx["SCX BPF scheduler"] --> target["SCX CPU performance target"]
    cfs --> sugov["schedutil"]
    target --> sugov
    control -.->|product-specific| sugov
    sugov --> driver["cpufreq driver / OPP"]
```

</details>

图中实线是可验证的标准接口，虚线是厂商可选映射；AOSP 没有定义 Power HAL 直接调用内核调度器辅助函数的通用路径。

### schedutil 的频率决策

<!-- gracker-diagram: a202-04-scx-input-modes -->
![SCX 状态改变 schedutil 的输入](../../assets/diagrams/ch19/a202-04-scx-input-modes.png)

图：SCX target 是归一化性能值，既不是 kHz 也不是 OPP 序号；full 与 partial 决定是否叠加 fair 利用率。

`schedutil` 是基于调度器负载的 CPU 调频策略。在内核标签 `android17-6.18-2026-06_r6` 中，它已通过 `sugov_get_util()` 接入 `sched_ext` 的 CPU 性能目标。`sched_ext` 简称 SCX，允许用 BPF 程序定义调度策略，这些 BPF 程序在受约束的内核执行环境中运行；CFS/fair class 是 Linux 普通任务使用的公平调度类。看频率决策时，我们要同时知道 CFS 与 SCX 各自给了多少利用率。

下面的节选展示 CFS 与 SCX 同时参与时的计算入口。

```c
unsigned long min, max, util = scx_cpuperf_target(sg_cpu->cpu);

if (!scx_switched_all())
    util += cpu_util_cfs_boost(sg_cpu->cpu);
```

SCX BPF 调度器通过 `scx_bpf_cpuperf_set(cpu, perf)` 写入相对于该 CPU 最大性能的线性目标，范围为 `[0, SCX_CPUPERF_ONE]`，并触发 `cpufreq_update_util()`。SCX 启用时先把每个 CPU 的 target 初始化为 `SCX_CPUPERF_ONE`，运行后再由 BPF 策略更新。这个目标是归一化性能值，单位既非 kHz，也非 OPP（Operating Performance Point，运行性能点）序号；OPP 指一组可用的频率与电压配置。再往下一层，CPU 怎么分组、每个 cpufreq policy（共用一次调频决策的 CPU 组）覆盖哪些核、驱动、频率上下限和温控约束，都会改变最终结果。

三种运行状态应分开解释：

| SCX 状态 | SCX target | fair-class 利用率 | `schedutil` 输入 |
| --- | ---: | ---: | --- |
| 未启用 | 0 | 加入 | 普通调度类利用率及后续约束 |
| partial switch（部分接管） | BPF 目标 | 加入 | SCX target 与普通调度类利用率之和，再应用约束 |
| full switch（全部接管） | BPF 目标 | 不加入 | SCX target，再应用 iowait、uclamp 等约束 |

iowait boost 会在任务等待 I/O 后唤醒时临时抬高利用率，uclamp（utilization clamp）则给任务或任务组设置利用率上下限。在 partial switch 下，fair-class 利用率仍会加入；fair class 是和 SCX 并存的调度路径，SCX 在场时它也在工作。

频率更新的节奏是设备相关的，没有跨设备统一的 10 ms 一类约定。`sugov_should_update_freq()` 会检查 policy 是否可以更新以及频率上下限是否变化，普通更新还受 `freq_update_delay_ns` 的速率限制，初值来自 `cpufreq_policy_transition_delay_us(policy)`。`get_next_freq()` 经 `map_util_freq()` 或厂商钩子给出原始频率，再由 `cpufreq_driver_resolve_freq()` 解析成驱动支持的档位；支持 fast switch（快速切换） 时直接更新，否则由工作线程延后执行。还有一点读源码时容易漏：共用一个 policy 的多个 CPU 会取处理后的最大利用率，所以给某个 CPU 写入 target，硬件改变的可能是一组 CPU 的频率。

<!-- gracker-diagram: a202-05-frequency-request -->
![从性能目标到频率执行](../../assets/diagrams/ch19/a202-05-frequency-request.png)

图：schedutil 先判断是否需要更新，再把利用率映射为驱动支持的频率；共享 policy、温控与硬件限制会影响最终执行。

以下几项都要在目标机上单独确认，SoC 品牌标签回答不了：

- `schedutil` 是否为量产配置中的调频策略；
- cpufreq policy 如何划分，是否支持每核独立 DVFS；
- cpuidle 使用 `menu`、`teo` 还是厂商策略；
- OPP 表、热限频和总功耗预算的取值；
- SCX 调度器是否启用，以及接管了哪些调度类。

排查目标机时，应读取调频策略、policy、频率表、空闲状态和温区的当前值，再结合内核配置与设备树解释 trace；产品配置要到这一步才能还原，通用内核源码只提供机制。

#### Android 厂商扩展钩子与异常恢复

<!-- gracker-diagram: a202-06-recovery-lifecycles -->
![SCX 回退与厂商状态清理](../../assets/diagrams/ch19/a202-06-recovery-lifecycles.png)

图：SCX 的内核回退、厂商额外资源状态清理、Power HAL 死亡后的重连，是三个分别设计的生命周期。

`android17-6.18-2026-06_r6/include/trace/hooks/sched.h` 中，名称含 `android_vh_scx_` 的钩子声明共 11 个，覆盖启用状态、异常退出、CPU 可运行性、迁移、入队、时间片和调度类切换修正。它们供 GKI（Generic Kernel Image，通用内核镜像）的厂商模块扩展调度行为，不是 Power HAL 到 SCX 的标准协议；数量和函数签名也只对应这个内核标签。

SCX 遇到 BPF 错误、可运行任务长时间得不到执行（runnable task stall）或 `SysRq-S` 时，会终止调度器并把任务交回 fair class；`SysRq-D` 只输出诊断 dump。退出后 `scx_cpuperf_target()` 返回 0，`scx_switched_all()` 为 false，下次 `schedutil` 更新会重新加入 fair-class 利用率。到这里要分清两条恢复路径：SCX 退出由内核自己完成，设备厂商在 SCX 之外保留的 Boost、uclamp 或固件状态仍需自行设计超时和清理；Power HAL 服务死亡后的封装层（wrapper）重连是另一条，两者互不替代。

### 三类厂商公开驱动能证明什么

<!-- gracker-diagram: a202-07-driver-boundaries -->
![公开驱动与量产实现的边界](../../assets/diagrams/ch19/a202-07-driver-boundaries.png)

图：公开驱动解释一类硬件接入方式；品牌、旧款驱动或节点名不足以还原新设备 Power HAL 与固件策略。

公开内核树提供了部分厂商硬件的基础驱动。这些代码能说明某类控制器怎样接入 Linux，也能限定本文可以确认的范围；量产手机的厂商模块、Power HAL 和固件往往还有额外实现。

#### Qualcomm：RPMh 与硬件 cpufreq

内核树中的 `drivers/soc/qcom/rpmh.c` 和 `drivers/soc/qcom/rpmh-rsc.c` 实现 RPMh/RSC 的内核消息通道。RPMh（Resource Power Manager hardware）负责接收资源状态请求，RSC（Resource State Coordinator）是向 RPMh 发送这些请求的控制器；`rpmh_write()`、`rpmh_write_async()` 与批量 API 把资源命令送入控制器。这些源码能证明的是“Linux 驱动可通过 RPMh 请求资源状态”；要断言“用户空间 Power HAL 直接调用某个内核函数”，还差目标机的证据。

`drivers/cpufreq/qcom-cpufreq-hw.c` 则展示一条硬件 cpufreq 路径：

- 驱动从最多 40 项的硬件 LUT（Lookup Table，查找表）构建频率表；
- 某些设备匹配数据支持 `per_core_dcvs`，即每核独立的动态时钟与电压调节；
- OPP 与 interconnect（片上互连）带宽路径可以协同更新；
- 驱动是否具备这些能力取决于设备匹配信息、设备树和硬件版本。

读厂商代码时要分清 `RPMh`、`DCVS` 和 `Perflock` 三个词：DCVS（Dynamic Clock and Voltage Scaling）指动态调整时钟与电压，RPMh 是资源请求基础设施，cpufreq-hw 是 CPU 频率驱动路径，Perflock 通常指厂商的性能锁服务及私有资源表，三者各有含义。某次频率上升可能来自调度负载、温控或 QoS（服务质量）约束变化、HAL 提示或厂商服务；trace 里没有对应标记时，把“多个核心同时升频”标成 Perflock 只是猜测。

#### MediaTek：软件调压与硬件 LUT 两条路径

公开内核树同时保留 `mediatek-cpufreq.c` 和 `mediatek-cpufreq-hw.c`，对应不同硬件代际或平台的实现方式，我们先看软件调压这条。

`mediatek-cpufreq.c` 会协调 CPU 核心电压 Vproc、可选的 SRAM 电压 Vsram、CPU 时钟与 PLL（Phase-Locked Loop，锁相环）。regulator 是内核中的稳压器接口；升频和降频阶段要按电压约束安排顺序，切换 PLL 时还会使用稳定的中间时钟。另一条路径 `mediatek-cpufreq-hw.c` 从最多 32 项的硬件 LUT 建表，并包含 Energy Model（内核能耗模型）注册和软硬件混合 DVFS 变体支持。

这些源码可以证明 MediaTek 平台存在多种 cpufreq 实现。再往前一步就要靠目标内核或跟踪证据：所有 Dimensity 产品是否使用同一个“硬件预测器”、Power HAL 是否固定经过 `mtlp`、`hw_flower` 这类用户空间或固件路径，都要逐台核实。CorePilot 是厂商品牌名，task packing（把可运行任务集中到较少 CPU 上）、核心选择和 Boost 策略也一样，具体实现从品牌名推不出来。

#### Samsung：ASV 和 TMU 的公开边界

公开内核中的 `drivers/soc/samsung/exynos-asv.c` 会读取 ASV（Adaptive Supply Voltage，自适应供电电压）信息，根据芯片体质分档（chip binning）调整 CPU OPP 电压，并在 OPP 更新后刷新 Energy Model。它当前的公开实现明确落在 Exynos 5422 的支持范围内：读它我们能理解 ASV 的一类 Linux 实现；要量化新款 Exynos 或 Xclipse GPU 设备之间的功耗差异，就得靠相应设备的资料。

`drivers/thermal/samsung/exynos_tmu.c` 是 Exynos TMU（Thermal Management Unit，热管理单元）驱动，负责温度读取、阈值、中断和校准等基础工作。量产设备采用哪套温控策略、ASV 是否会随温度持续修改 OPP 电压，还是要以目标机为准。

Xclipse GPU 的 DVFS、固件和产品策略要以相应设备的公开驱动、厂商源码或测量数据为准。`exynos_tmu.c` 加上旧款 ASV 支持，还推不出 SurfaceFlinger、Power HAL 与 GPU 驱动之间的完整产品调用关系。

#### 品牌标签与实验变量

同一厂商的两个 SoC 可能使用不同 CPU 微架构、GPU、制程、DVFS 控制器和调度配置；同一 SoC 放入两种机身后，也会受散热结构、屏幕与固件参数影响。所以跨设备实验里，用“Qualcomm 对 MediaTek”这样的品牌标签分组，信息量太少。我们记录实验时至少应包含：

- 手机型号、SoC、RAM 和软件构建指纹（build fingerprint）；
- Android 版本、内核版本及调频策略；
- 分辨率、刷新率和校准后的屏幕亮度；
- 环境温度、起始电池温度、起始电量与充电状态；
- 无线网络制式、信号条件、SIM 与后台账号状态；
- 工作负载版本、输入数据、持续时间和重复次数。

### 应用侧可用的标准能力

应用很少需要知道某个 Hint 在芯片内部怎样执行。可移植的做法是报告周期任务的目标用时与实际用时，读取系统压力，并在本进程内调整工作量。这三个入口分别是 Hint Session、温控状态与资源余量。

#### 用 `PerformanceHintManager` 描述周期工作

<!-- gracker-diagram: a202-08-hint-session-lifetime -->
![Hint Session 的周期工作闭环](../../assets/diagrams/ch19/a202-08-hint-session-lifetime.png)

图：会话把目标预算与实际用时交给系统；实际频率、核心和功耗由设备结合温控预算决定，应用仍需减少无效工作。

`PerformanceHintManager` 从 API 31 提供公开接口，适合渲染、音视频等具有周期预算的长寿命线程。下面的 Kotlin 片段展示最小会话生命周期。

```kotlin
val manager = getSystemService(PerformanceHintManager::class.java)
val targetNs = 6_000_000L
val session = manager?.createHintSession(
    intArrayOf(Process.myTid()),
    targetNs
)

try {
    repeat(frameCount) {
        val startNs = System.nanoTime()
        renderOneFrame()
        val actualNs = System.nanoTime() - startNs
        session?.reportActualWorkDuration(actualNs)
    }
} finally {
    session?.close()
}
```

`frameCount` 和 `renderOneFrame()` 代表业务自己的周期循环。`createHintSession()` 接收 Linux TID 数组和正数目标时长；设备不支持 Hint Session，或线程不属于当前进程时，可以返回 `null`。使用时要守住几条约定：参与线程长期存活且属于当前进程，每个周期都报告工作时长，目标预算变化时再调用 `updateTargetWorkDuration()`。目标时长应取该线程组在整条处理管线中的工作预算。示例两端都用 `System.nanoTime()` 测量单调时钟时差，兼容本文覆盖的 API 34；`SystemClock.uptimeNanos()` 与其同属不包含深度休眠的 uptime 时间基准，但该公开方法从 API 35 才提供。

> ⚠️ API 边界校勘：Hint Session 从 API 31 提供，不代表示例中的所有计时方法也都能在 API 31～34 使用。[来源：SystemClock API](https://developer.android.com/reference/android/os/SystemClock#uptimeNanos())

ADPF（Android Dynamic Performance Framework，Android 动态性能框架）提供反馈信号，频率、核心或功耗结果仍由厂商实现结合温控和整机预算决定。所以应用侧该做的优化一件不少：减少无效工作、控制并发和缩短持锁区间。

#### thermal headroom 的读数与阈值

<!-- gracker-diagram: a202-09-headroom-direction -->
![两类 headroom 的读数方向](../../assets/diagrams/ch19/a202-09-headroom-direction.png)

图：thermal headroom 和 CPU/GPU headroom 的读数方向不同；设备阈值、查询间隔和计算窗口均需单独读取。

`PowerManager.getThermalHeadroom(forecastSeconds)` 的 `forecastSeconds` 参数取 0 到 60 秒，返回值为非负的归一化热压力指标。这个 API 名字里带 headroom（热余量），读数方向却相反：返回值越高表示越接近严重温控阈值，`1.0` 表示到达 `THERMAL_STATUS_SEVERE` 阈值，返回值可以超过 `1.0`；`0.0` 不对应某个固定温度或温控状态，也没有摄氏度单位。

接口可能返回 `NaN`（Not a Number，表示当前没有有效数值），包括设备不支持、采样尚未稳定或调用过快等情况。AOSP 文档指出慢变化传感器约一秒更新一次，更高频轮询没有收益。我们把 headroom 与 `getCurrentThermalStatus()` 放在一起用，可以决定何时降低画质、减小批量任务或延后预取。

`getThermalHeadroomThresholds()` 从 API 35 开始提供，用于读取设备为各温控状态定义的 headroom 阈值。不同设备的传感器和阈值模型可能不同，跨机比较原始 headroom 数字时要保留这项限制。

#### CPU/GPU headroom 的含义

API 36 起，`SystemHealthManager` 提供可选的 `getCpuHeadroom()` 与 `getGpuHeadroom()`，用于估计 CPU 或 GPU 还剩多少可用能力。有效结果范围为 `[0, 100]`，其中 `0` 表示没有更多对应资源可分配；暂不可用时会返回 `Float.NaN`，设备不支持时会抛出 `UnsupportedOperationException`。

这两个调用至少包含一次同步 Binder 事务，可能超过 1 ms，初次或自定义参数调用还可能更慢。所以渲染、音频这类时限敏感线程应把查询放到关键路径之外。轮询间隔和计算窗口由设备报告，应用应查询：

- `getCpuHeadroomMinIntervalMillis()` / `getGpuHeadroomMinIntervalMillis()`；
- `getCpuHeadroomCalculationWindowRange()` / `getGpuHeadroomCalculationWindowRange()`。

CPU 参数可指定属于本进程的 TID，这些线程还必须具有相同的 CPU affinity（允许线程运行的 CPU 集合）。接口契约里没有固定的 100 ms 轮询间隔，具体数值以查询结果为准。

#### 应用与调度策略的分工

sysfs 是 Linux 通过虚拟文件暴露内核设备和状态的接口。应用侧可移植的做法只有一条：走公开 SDK。手工绑核、限制 GPU 最高频率、写旧式 `schedtune` 调度参数节点，或依赖写 sysfs、厂商私有性能服务和隐藏 Power API，这些做法都绑死在特定设备上，还可能破坏调度器和温控系统的联合决策。

若开发的是系统镜像、设备策略或游戏性能服务，绑核和 QoS 调整也应完成目标设备实验，明确撤销条件，并在 OTA（系统无线更新） 后重新验证。另外，`sched_ext` 与 `schedtune` 面向的对象、接口和部署方式各不相同，是两套独立的机制。

### 功耗测量：先明确物理量

<!-- gracker-diagram: a202-10-energy-measurements -->
![能量、电流与测量边界](../../assets/diagrams/ch19/a202-10-energy-measurements.png)

图：任务总能量需结合完成时间、温度和帧性能；电池电流与片上供电支路读数的测量范围不同。

“功耗”经常混用三类量：

- **功率**，单位 W，描述某个时刻或时间窗的能量消耗速率；
- **能量**，单位 J、Wh 或 µW·s，适合比较一次任务完成所需成本；
- **电池电流**，单位 A 或 mA，必须结合电压、方向约定、采样位置和充电状态解释。

只比较任务期间的平均电流，容易把电压变化、充电路径和任务完成时间漏掉。对“完成同一任务谁更省电”的问题，我们优先比较任务总能量，同时给出耗时、温度、帧性能和置信区间；置信区间用于表达重复采样下估计值可能落入的范围。

#### Perfetto 的 Android power 数据源

下面的配置用于采集电池计数器和设备可选的片上电源轨，字段名与 Perfetto 官方 Android power 数据源一致。

```textproto
data_sources {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 250
      battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
      battery_counters: BATTERY_COUNTER_CHARGE
      battery_counters: BATTERY_COUNTER_CURRENT
      battery_counters: BATTERY_COUNTER_VOLTAGE
      collect_power_rails: true
    }
  }
}
```

`android.power` 的电池计数器受充电状态影响；USB 数据连接还可能让设备保持额外的唤醒状态，所以精密实验要记录供电和调试连接方式。`collect_power_rails` 依赖设备实现：ODPM（片上功耗测量）rail 是硬件能够单独计量的一条供电支路，没有相应硬件的设备不会凭配置生成数据。

在 Linux/ChromeOS 文档里，通过 sysfs 读取功耗的 Perfetto 数据源名是 `linux.sysfs_power`；`linux.power.sysfs` 这个名字在当前官方配置说明里查不到，Android 功耗采集也用不上 `android.power.stats` 这个数据源名。

#### PowerStats HAL 与公开功耗监视器

PowerStats AIDL 仍是冻结的 v2。它可以报告电源轨能量，以及 power entity（可独立统计电源状态的子系统或电源域）的状态驻留时间——residency 指组件在某个电源状态中累计停留的时间。组件支持是可选的，rail 名称、覆盖范围和采样属性也由设备决定。系统统计服务 Statsd、Perfetto 与 Batterystats 可以使用这些数据。

API 35 起，普通应用可通过 `SystemHealthManager.getSupportedPowerMonitors()` 查询设备公开的功耗监视器，再异步调用 `getPowerMonitorReadings()`；支持列表为空是合法结果。监视器可能来自原始 ODPM rail，也可能来自 energy consumer（按硬件读数或模型归集的耗能组件），分析时要保留监视器类型与名称。

ODPM rail 在电池输出的下游测量子系统能量，充电状态对它的读数没有直接影响；覆盖范围由硬件决定，屏幕、射频或 PMIC 转换损耗可能都不在内。rail 名同样随设备各自定义，互比前要先核对覆盖说明。跨设备总功耗比较仍以校准过的外部功耗仪更稳妥，片上 rail 更适合分析同一台设备内各子系统的贡献。

### 按控制链路做运行态排查

排查前要固定产品配置：软件构建指纹、内核版本（kernel release）、`CONFIG_SCHED_CLASS_EXT`、调频策略、cpufreq policy 分组和当前温控状态。这里最容易想当然的是 SCX 的启用层级：内核包含 SCX 支持，不代表设备已经加载 BPF 调度器；加载调度器后，也未必进入 full switch。

sched_ext 的运行状态从两组 sysfs 节点读取：顶层节点描述全局启用情况，`root/` 描述当前活动的 BPF 调度器。

| 节点 | 含义 |
| --- | --- |
| `/sys/kernel/sched_ext/state` | `disabled`、`enabling`、`enabled` 或 `disabling` |
| `/sys/kernel/sched_ext/switch_all` | 当前是否接管全部符合条件的普通任务 |
| `/sys/kernel/sched_ext/nr_rejected` | 显式请求 `SCHED_EXT` 却被拒绝的累计数 |
| `/sys/kernel/sched_ext/enable_seq` | 本次开机中，调度器每次成功启用后递增的序号 |
| `/sys/kernel/sched_ext/root/ops` | 当前活动 BPF 调度器名称 |
| `/sys/kernel/sched_ext/root/events` | 当前内核标签定义的选核回退、任务派发和绕过调度器等计数 |

`root/` 只在活动调度器对象存在时创建，采集脚本要允许缺失。ABI 是外部工具依赖的接口约定；`events` 的字段集会随内核标签变化，跨版本复用前要重新核对。

配置固定后，我们按以下顺序缩小问题：

1. 确认 Mode、Boost 或 Hint Session 的发起方、权限、支持结果、持续时间与取消点。
2. 对齐普通调度类中的可运行任务、SCX 策略、`switch_all`、产品公开的 `cpuperf_target`、iowait 和 uclamp。
3. 检查调频更新是否受其他 CPU 发起的更新、速率限制或未变化的目标影响，再检查 policy 的最低/最高频率、温控约束与驱动频率表。
4. 把驱动请求、实际频率、任务完成时间、帧性能、温度和能量放到同一时间轴。

一次可复查的跟踪记录至少要覆盖 Framework 场景与业务标记、`sched_switch` / `sched_wakeup`、任务调度策略与所在 CPU、SCX 和产品自定义事件、cpufreq 频率上下限与当前频率、温控事件及 uclamp。`setMode()` 是 `oneway` AIDL 调用，调用方发送后不会同步等待 HAL 处理结果，所以没有 HAL 标记时，我们应做启用/取消对照并观察约束变化，只靠时间相邻是建立不起因果的。PowerStats 的 rail 或 residency 用来观察结果，不参与 `schedutil` 选频，具体能力差异见本篇后半部分。

### 一套可复现的实验流程

#### 1. 定义问题和指标

先写清要回答的问题，例如“固定 60 Hz 时一次列表冷启动消耗多少能量”，或“20 分钟游戏后的稳态帧率和每帧能量怎样变化”；指标至少包括任务能量、任务耗时、帧性能和热状态。

#### 2. 固定可控变量

屏幕亮度应按实测 nit 对齐；nit 是亮度单位，1 nit 等于 1 cd/m²。系统百分比刻度不可跨设备直接比较。分辨率、刷新率、色彩模式、网络、账号同步、定位、音量、工作负载数据、起始电量和起始温度都要记录。运行前等待温度回到预设范围。

主动风冷会改变真实用户场景的热稳态。若目标是分离芯片计算成本，可以增设恒温或主动冷却组；若目标是评估手持设备持续性能，应保留原机散热条件。两组数据要分开报告。

#### 3. 预热并随机化顺序

JIT（Just-In-Time，即时编译）、着色器缓存（shader cache）、文件缓存和网络缓存都会改变结果，冷启动与热启动应拆成不同实验。多设备轮测时我们随机化顺序，减少环境温度、服务器负载和电池状态随时间漂移带来的偏差。

#### 4. 重复采样并报告分布

单次基准测试（benchmark）撑不起厂商级结论。每个条件重复多轮，保留原始数据，报告中位数、离散程度和置信区间。发生充电、温控状态跨档、后台更新或网络异常的样本应按预先约定的规则处理。

#### 5. 用 trace 解释差异

Perfetto 至少同时观察：

- `sched_switch` / `sched_wakeup` 与线程运行位置；
- CPU 频率、空闲状态和 cpufreq policy；
- 温度计数器或温控状态；
- 应用自定义时间片（slice）、FrameTimeline 或业务阶段；
- 设备支持时的电池计数器与 power rail。

频率升高和功率尖峰是相关证据，要证明因果还需要更多东西。我们可以对齐唤醒、等待运行的任务队列（runnable backlog）、Hint 标记、频率、rail 能量和任务阶段，再用对照实验逐步缩小原因。没有厂商标记时，结论写成“观察到的系统响应”即可，不要给闭源模块强行命名。

### 面向不同角色的检查表

#### 应用工程师

- 使用公开 SDK 报告周期工作和读取系统压力；
- 对 `null`、`NaN`、不支持异常及设备差异做好兼容；
- 在应用内部减少工作量，避免依赖私有 Boost、绑核和频率节点；
- 以任务总能量、用户体验和温度一起评估改动。

#### 系统与设备厂商工程师

- 在调用 `setMode()` / `setBoost()` 前检查厂商实现是否支持；
- 为每个 Hint 定义启用、取消、超时和进程死亡后的清理行为；
- 验证 Hint Session 更新频率、FMQ 失败回退和温控限制；
- 用跟踪标记暴露可审计的策略阶段，避免闭源行为缺少可用的调试线索；
- 在 `android17-6.18-2026-06_r6` 内核上重新验证调频策略、SCX 和 cpufreq 驱动交互。

#### 性能分析工程师

- 记录完整设备和实验环境，而非只记录 SoC 品牌；
- 区分电池计数器、片上 rail 和外部功耗仪的测量边界；
- 对比功耗时同时对齐工作量和完成时间；
- 把源码可证事实、目标机观测和推断分栏记录。

### 结语

这一部分我们看到，平台为各厂商提供同一套 Power AIDL 契约，厂商仍可按硬件、固件和整机目标选择实现方式。公开源码能够确认接口、通用调度逻辑和部分硬件驱动，却无法替代目标设备验证。

应用侧较稳妥的路径是使用 `PerformanceHintManager`、温控状态、资源余量和功耗监视器等公开能力，并通过减少工作量改善能效。系统侧排查要分层观察 Framework 提示、内核调度与频率、温控约束和固件响应。控制变量、记录测量范围并保留跟踪证据，才能让跨 SoC 功耗结论经得起复查。

## Power Stats 能量实体、驻留与归因

控制环决定硬件状态，Power Stats 用来观察能量和驻留结果。我们拿到一台设备做功耗分析时，首先要弄清它的统计覆盖、单位和更新频率：这些都由 OEM（设备厂商）实现，设备之间差别可以很大。

PowerStats 链路用三类对象描述设备数据：`PowerEntity` 是子系统、外设或电源域，报告各状态的累计驻留时间；`EnergyConsumer` 报告组件累计能量，并可选择附带按 UID 分摊的结果；`Channel` 是能量计量通道，常对应一条电源 rail（供电支路）。我们沿着这三个对象往下看。

AOSP 定义稳定的 HAL 接口、Framework 系统服务和数据使用路径；设备能提供多少 rail、是否包含 UID 分摊、计数器是否可靠，仍取决于厂商实现。Pixel、高通、MediaTek、三星等闭源或受限仓库的细节，本文不作源码级断言。

### 标准架构与厂商差异

#### PowerStats HAL 标准架构

<!-- gracker-diagram: a202-11-stats-three-objects -->
![Power Stats 的三类对象](../../assets/diagrams/ch19/a202-11-stats-three-objects.png)

图：六个 HAL 方法配成三组对象与读数；ID、名称和覆盖由设备定义，服务存在不代表三组数据齐全。

冻结的 `android.hardware.power.stats` AIDL 是 v2，`IPowerStats.aidl` 定义以下 6 个方法：

```aidl
PowerEntity[]              getPowerEntityInfo();
StateResidencyResult[]     getStateResidency(in int[] powerEntityIds);
EnergyConsumer[]           getEnergyConsumerInfo();
EnergyConsumerResult[]     getEnergyConsumed(in int[] energyConsumerIds);
Channel[]                  getEnergyMeterInfo();
EnergyMeasurement[]        readEnergyMeter(in int[] channelIds);
```

这 6 个方法组成三组数据：

1. **状态驻留**：`PowerEntity` / `StateResidencyResult` 记录每种状态自开机以来的累计时长、进入次数和最近一次进入时间。实体名与状态名由设备定义，Framework 不解释其硬件含义。
2. **组件能量**：`EnergyConsumer` / `EnergyConsumerResult` 记录自开机以来的累计能量与采集时间，也可附带 `EnergyConsumerAttribution[]` 做 UID 分摊。分摊数组是可选项，其总和不得超过该组件的累计能量。
3. **计量通道**：`Channel` / `EnergyMeasurement` 记录采集时间 `timestampMs`、累计时长 `durationMs` 和累计能量。通道可能对应总线、采样电阻或电源 rail，名称与子系统字段由设备定义。

能量字段的单位是微瓦秒（µW·s，数值上等于微焦耳），AIDL 时间戳使用从开机起计时且包含休眠时间的 `CLOCK_BOOTTIME`。ID 数组为空时表示请求全部可用对象，某个对象暂时没有结果时 HAL 可以不返回该项。接口约定到这里为止：设备是否覆盖某个组件、是否提供 UID 分摊，要靠后文的能力核查确认。

#### AOSP 默认实现与真实设备

AOSP 默认实现位于 `hardware/interfaces/power/stats/aidl/default/`。`main.cpp` 注册 3 条虚构 rail、2 个虚构状态提供者和 2 个虚构 EnergyConsumer，供接口联调与 VINTF（Vendor Interface，系统和厂商组件之间的兼容契约）验证。这些 fake 数据只服务于测试，真实设备的数据基线要另行确认。

OEM 差异也从这里开始：

- 厂商只接入少量 rail 时，系统服务诊断命令 `dumpsys powerstats` 仍会列出对象，但覆盖范围有限。
- 厂商没有提供 `EnergyConsumerAttribution[]` 时，PowerStats 数据给不出该组件的 UID 分摊。
- 计数器复位、时间戳错误或单位换算错误，会让上层工具读到格式正确但无法比较的数据。

#### Framework 的三条数据使用路径

<!-- gracker-diagram: a202-12-stats-service-branches -->
![PowerStatsService 的三条使用路径](../../assets/diagrams/ch19/a202-12-stats-service-branches.png)

图：日志、公开 Power Monitor 和 StatsD 是从服务分开的使用路径；公开 Monitor 不经过 Logger 文件，HIDL 回退也不提供 EnergyConsumer。

`PowerStatsHALWrapper` 优先连接稳定 AIDL v2；连接不到时会尝试旧版 HIDL（旧版 HAL 接口定义） 1.0，后者能提供 rail 与状态驻留，Framework 的兼容封装会把 EnergyConsumer 信息和结果返回为空数组。所以设备有 PowerStats 服务，只说明接口连上了，三组数据是否齐全要分别确认。

下面列出主要类名，便于在源码中定位。服务连接 HAL 后分成日志、公开 Power Monitor 和 StatsD 三路；公开 Power Monitor 使用服务自己的缓存，不经过 Logger 或日志文件。

```text
vendor PowerStats HAL
  → PowerStatsHALWrapper
  → PowerStatsService
      ├─ PowerStatsLogger → PowerStatsDataStorage → dumpsys --proto
      ├─ Power Monitor API → 独立缓存 → SystemHealthManager
      └─ LocalService → StatsPullAtomCallbackImpl → StatsD
```

`PowerStatsService` 封装 HAL 后，数据分三路使用：

1. **持久化日志**：`PowerStatsLogger` 按收到的消息类型，把计量通道（meter）、组件能量（model）或状态驻留（residency）写入滚动存储；触发器与数据类型的对应关系见下文。
2. **公开 Power Monitor**：`SystemHealthManager` 通过 `PowerStatsService` 直接读取 Channel 或 EnergyConsumer，并在服务内使用独立缓存；它不读取 `PowerStatsLogger` 的文件。
3. **StatsD 拉取**：StatsD 是 Android 的系统统计守护进程。`StatsPullAtomCallbackImpl` 从本地服务读取 rail 和状态驻留，注册 `ON_DEVICE_POWER_MEASUREMENT` 与 `SUBSYSTEM_SLEEP_STATE` 两个统计项。

BatteryTrigger 在系统报告的电池百分比下降时记录状态驻留。TimerTrigger 默认每 2 分钟记录 rail 与不含 UID 分摊的组件能量，每 1 小时记录包含 UID 分摊的组件能量；启用相应平台开关后，产品资源配置可以改写这两个周期。

持久化目录是设备加密存储中的 `/data/system_de/0/powerstats/`，常见文件包括：

- `log.powerstats.meter.0`
- `log.powerstats.model.0`
- `log.powerstats.residency.0`

`PowerStatsLogger` 写文件前，会按本次开机的时钟偏移把 HAL 的开机时间戳转换为 Unix 时间。对象元数据在重启后发生变化时，Logger 会清理对应的旧日志。无参数的 `dumpsys powerstats` 列出当前对象与 Logger 状态；`--proto meter/model/residency` 导出各自的二进制 protobuf（Protocol Buffers，结构化序列化格式）日志。

#### 设备能力的四个维度

评估一台设备时，“服务存在”只说明接口可以连接，我们还要检查以下四项：

| 维度 | 需要确认的问题 | 对工具结果的影响 |
|---|---|---|
| 对象覆盖 | Channel、EnergyConsumer、PowerEntity 是否覆盖 CPU、显示、蜂窝网络、Wi-Fi、GNSS 等关键组件 | 决定能分析哪些子系统，缺失对象不能靠上层补出 |
| 采集方式 | 数据来自片上电源监视器、PMIC（电源管理芯片）、内核计数器或软件模型 | 决定数值是直接测量、状态统计还是估算 |
| UID 分摊 | 是否提供 `EnergyConsumerAttribution[]`，分摊总和与 UID 映射是否有效 | 决定能否在对应组件内分析应用归因 |
| 计数器与时钟 | 累计值是否单调、重启后是否复位，`timestampMs` 与 `durationMs` 是否符合字段定义 | 决定窗口差值是否可用，以及多路数据能否对齐 |

同一厂商的不同 SoC、内核、PMIC 和整机配置可能提供不同对象。报告设备能力时，我们把这四项写全，只写厂商品牌是撑不起结论的。

#### Power Monitor 的缓存、权限与随机扰动

<!-- gracker-diagram: a202-13-monitor-cache-noise -->
![Power Monitor 的缓存与读数](../../assets/diagrams/ch19/a202-13-monitor-cache-noise.png)

图：服务缓存新鲜度与硬件采样周期不同；两类权限路径都经过扰动处理，公开结果不包含 EnergyConsumer 的 UID 分摊数组。

公开 Power Monitor API 从 API 35 开始提供。`getSupportedPowerMonitors()` 异步返回两类对象：直接测得的 `POWER_MONITOR_TYPE_MEASUREMENT` 与直接测量或模型计算的 `POWER_MONITOR_TYPE_CONSUMER`；空列表是合法结果。有一个坑：PowerMonitor 的 index 在重启后不保证稳定，应用只能使用本次查询返回的对象，index 不要持久化。

`ACCESS_FINE_POWER_MONITORS` 是 `signature|privileged|development` 级别权限，普通第三方应用通常无法获得。服务为两类调用方维护独立缓存：

- 无该权限时，缓存最长复用 20 秒，结果标为 `GRANULARITY_UNSPECIFIED`；
- 有该权限时，缓存最长复用 250 毫秒，结果标为 `GRANULARITY_FINE`。

这两个阈值决定服务何时重新请求 HAL，硬件传感器本身的采样周期要另行确认。服务还会在前后两次累计值之间加入按调用 UID 保持一段时间的随机扰动，两类权限路径都会经过该处理。公开结果以 µW·s 报告自开机以来的累计能量，包含电池供电与外接电源期间的能量，重启后不会延续；该 API 不返回 `EnergyConsumerAttribution[]`。

这里的 granularity 指结果新鲜度等级。排查 Power Monitor 读数时，我们同时确认设备功能开关、对象列表、结果时间戳、累计值是否增长、调用方权限和返回的 granularity；20 秒或 250 毫秒的缓存规则与 HAL 计数器本身的采样说明是两回事。

### 能力分级与部署

#### 按能力描述 OEM 实现

闭源实现无法从 AOSP 主线核对时，我们可以按观测到的能力给设备分级。L0–L4 是本文使用的验收约定，不是 Android 官方等级：

| 能力等级 | 典型表现 | 适合的分析场景 |
|---|---|---|
| L0：没有可用数据 | HAL 未初始化、对象为空，或设备部署了默认 fake 数据 | 只能验证接口或故障处理 |
| L1：计量通道可用 | 能读取部分 `Channel` / `EnergyMeasurement` | 可观察同一设备上的供电支路趋势，覆盖范围有限 |
| L2：组件能量可用 | 多个 `EnergyConsumer` 覆盖关键硬件 | 可分析设备定义的 CPU、显示、蜂窝网络等组件 |
| L3：UID 分摊可用 | 部分 EnergyConsumer 稳定返回合法的 `EnergyConsumerAttribution[]` | 可在对应组件和采样窗口内分析 UID 分摊 |
| L4：测量链已验证 | 累计值、时间戳、单位和覆盖范围经过外部仪器与重复实验核对 | 可支持目标机型上的定量实验，报告仍需写明测量边界 |

能力等级描述的是一台设备上的一版软件；换机型或 OTA 版本后，要重新分级。

#### 跨厂商比较的统一口径

<!-- gracker-diagram: a202-14-energy-difference -->
![跨设备能量比较前的对齐](../../assets/diagrams/ch19/a202-14-energy-difference.png)

图：先对齐对象、时钟和实验窗口，再做累计值差分；未提供 UID 数据的设备不能被解释成应用耗电更低。

跨厂商比较前，我们先统一对象映射、计算方式和时间窗口：

1. **保存对象清单**：记录 `getPowerEntityInfo()`、`getEnergyConsumerInfo()` 和 `getEnergyMeterInfo()` 的完整返回值。设备自定义名称对 Framework 是不透明字符串，同名对象测量的范围要逐一核对。
2. **使用累计值差分**：一次任务的能量取结束累计值减去开始累计值。若计数器下降，先排查重启、HAL 复位、回绕或对象映射变化，负差值要在排查清楚后才能使用。
3. **区分两种时间戳**：原始 HAL 结果使用 `CLOCK_BOOTTIME`；Logger 的落盘数据转换为 Unix 时间。混合两条路径时要先转换到同一时间轴。
4. **对齐实验窗口**：保持工作负载、屏幕状态、电量区间、温度和网络条件一致。平均功率可用能量差除以同一窗口的时长计算。
5. **单独标注 UID 分摊**：组件总能量与 UID 分摊的证据强度不同。分摊缺失只说明 HAL 没有返回这项数据，据此说某个应用没有耗电就过头了。
6. **用外部仪器校验**：片上 rail 可能漏掉屏幕、射频或 PMIC 转换损耗。跨设备总能量结论应同时给出外部功耗仪或电池侧测量的校验结果。
7. **记录来源**：报告中写明机型、软件构建指纹、内核版本、HAL 路径、对象清单、采样时长、权限与 Power Monitor granularity。

不同设备的对象对不上时，我们就比较各自覆盖范围内的趋势，暂不拼统一的绝对总量。

#### 企业设备与实验室设备池

设备进入实验池前，先保存对象清单并验证计数器：

```bash
adb shell dumpsys powerstats
adb shell dumpsys powerstats --proto meter
adb shell dumpsys powerstats --proto model
adb shell dumpsys powerstats --proto residency
```

后三条命令输出二进制 protobuf。正式采集时应使用 `adb exec-out dumpsys powerstats --proto meter > powerstats-meter.pb` 这类重定向保存方式，避免终端或 shell 改写二进制内容；`model` 与 `residency` 同理。

验收清单：

- `dumpsys powerstats` 中是否能列出 PowerEntity、Channel、EnergyConsumer；
- 明确 Framework 连接的是 AIDL v2 还是 HIDL（HAL Interface Definition Language） 1.0，后者不会提供 EnergyConsumer；
- 在亮屏、灭屏、视频、网络和定位等场景中，比较前后两次 meter/model 累计值是否合理增长；
- `EnergyConsumerResult` 是否带 UID 分摊，分摊总和是否不超过组件总能量；
- 重启或 OTA 后重新采集对象 ID、名称与类型，旧映射作废；
- 导出的 protobuf 是否能由与当前 schema（字段结构定义）匹配的内部工具解析；
- 外部功耗仪与片上计数器的能量差是否在预先设定的误差范围内。

监控平台应把设备能力等级、HAL 路径、对象清单版本和测量范围保存为元数据。混合 L1 与 L3 设备生成同一张应用耗电榜，会把“没有 UID 数据”误当成“应用耗电较低”，所以这层把关要放在设备入池前。

### 实战排查：不同手机功耗榜的差异来源

<!-- gracker-diagram: a202-15-collection-cadence -->
![日志触发、公开缓存与设备采样](../../assets/diagrams/ch19/a202-15-collection-cadence.png)

图：四类节奏属于不同层；采集路径、权限、粒度、计数器与覆盖一致后，才能把功耗榜差异归因到业务行为。

同一个 APK 在两台设备上出现不同耗电归因时，我们按以下顺序排查：

1. **确认 HAL 路径**：区分 AIDL v2、HIDL 1.0 与未初始化状态，记录服务是否使用默认 fake 实现。
2. **检查对象清单**：对象数量、名称或类型不同，统计覆盖范围已经不同。
3. **核对累计值**：用同一对象的结束值减开始值，排除重启、复位、回绕和对象 ID 变化。
4. **检查 UID 分摊**：缺少 UID 分摊数据的设备无法仅靠 PowerStats 给出组件内的应用分摊。
5. **区分采集路径**：Logger 的默认 2 分钟/1 小时周期、BatteryTrigger、公开 Power Monitor 的缓存是三种不同节奏。
6. **确认权限和扰动**：记录 `PowerMonitorReadings.getGranularity()`；公开读数还包含按 UID 生成的随机扰动。
7. **比较业务代码**：测量范围和时间窗口一致后，再分析线程、网络、渲染或媒体行为。

报告中至少保留以下信息：

```text
设备：<model/build/kernel>
PowerStats 能力：L1/L2/L3/L4
对象数量：PowerEntity=<n>, Channel=<n>, EnergyConsumer=<n>
采样窗口：<start/end/duration>
权限路径：legacy / ACCESS_FINE_POWER_MONITORS
结论：仅在上述口径内成立
```

模板中的 `model/build/kernel` 分别指机型、软件构建指纹和内核版本。`legacy` 只是原模板对“没有细粒度权限”的简称，不是 Framework 的正式路径名，正式报告宜写 `GRANULARITY_UNSPECIFIED` 或 `GRANULARITY_FINE`。

### 版本与实现边界

- 本部分固定在 `android-17.0.0_r1` / Android 17（API 37）：该标签冻结 PowerStats AIDL v2，同时保留 HIDL 1.0 回退。
- Pixel、高通、MediaTek、三星等厂商 HAL 的闭源细节没有纳入确定性结论。
- `StatsPullAtomCallbackImpl` 已核对：它向 StatsD 注册片上功耗测量与子系统休眠状态两类拉取项。
- AOSP 官方文档把 StatsD、Perfetto 与 Batterystats 列为 PowerStats 客户端；Battery Historian 是否直接解析 `dumpsys powerstats --proto` 的三类文件，同样要单独验证，内部工具的输入 schema 与消费路径也是如此。
- 公开 Power Monitor 从 API 35 开始提供，只公开 Channel/EnergyConsumer 累计值，不公开 PowerEntity 状态驻留或 EnergyConsumer 的 UID 分摊数组。

## 小结

Power HAL 与 schedutil 把场景、利用率和约束转成设备侧控制，Power Stats 报告能量与状态驻留结果；统计数据不会反向参与选频。跨设备比较时，我们要分别核对控制入口、调度/频率响应、PowerStats 对象覆盖和外部仪器校验，同名 rail、SoC 品牌或服务存在都不是等价的测量依据。

## 参考资料

### Android 17 / AOSP

- [Power AIDL `IPower.aidl`（android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/IPower.aidl)
- [PowerManagerService（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java)
- [Power HAL controller（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/powermanager/PowerHalController.cpp)
- [HintManagerService（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/hint/HintManagerService.java)
- [`Mode.aidl`（19 个 Mode，android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/Mode.aidl)
- [`Boost.aidl`（6 个 Boost，android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/Boost.aidl)
- [PowerStats AIDL v2（android-17.0.0_r1）](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/)
- [Android 17 kernel `cpufreq_schedutil.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)
- [Android 17 `sched_ext` 核心实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c)
- [Android 17 scheduler vendor hooks](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/hooks/sched.h)
- [`drivers/soc/qcom/rpmh.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/soc/qcom/rpmh.c)
- [`drivers/soc/qcom/rpmh-rsc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/soc/qcom/rpmh-rsc.c)
- [`drivers/cpufreq/qcom-cpufreq-hw.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/qcom-cpufreq-hw.c)
- [`drivers/cpufreq/mediatek-cpufreq.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/mediatek-cpufreq.c)
- [`drivers/cpufreq/mediatek-cpufreq-hw.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/mediatek-cpufreq-hw.c)
- [`drivers/soc/samsung/exynos-asv.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/soc/samsung/exynos-asv.c)
- [`drivers/thermal/samsung/exynos_tmu.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/thermal/samsung/exynos_tmu.c)

#### 官方文档

- [PerformanceHintManager API](https://developer.android.com/reference/android/os/PerformanceHintManager)
- [PowerManager API](https://developer.android.com/reference/android/os/PowerManager)
- [SystemHealthManager API](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [Perfetto：Battery counters and power rails](https://perfetto.dev/docs/data-sources/battery-counters)
- [AOSP：Power statistics HAL](https://source.android.com/docs/core/power/power-stats-hal)

#### 交叉阅读

- §19.2 SoC 平台差异：CPU/GPU 硬件架构
- §19.3 sched_ext 与 OEM 调度实践
- 本篇后半部分：Android 17 Power Stats HAL 的 OEM 实现差异
- §5.2 DVFS 与功耗管理
- §5.2 Android 功耗管理
- §5.4 ADPF 自适应性能框架

#### Android 17 / AOSP 源码

- [PowerStats AIDL v2 构建与冻结版本](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/Android.bp)
- [`IPowerStats.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl)
- [`EnergyConsumerResult.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl)
- [`EnergyMeasurement.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl)
- [AOSP 默认 fake PowerStats 服务](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/default/main.cpp)
- [`PowerStatsHALWrapper`：AIDL v2 与 HIDL 1.0 回退](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java)
- [`PowerStatsService`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java)
- [`PowerStatsLogger`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsLogger.java)
- [`TimerTrigger`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/TimerTrigger.java)
- [`BatteryTrigger`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/BatteryTrigger.java)
- [`StatsPullAtomCallbackImpl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java)
- [`ACCESS_FINE_POWER_MONITORS` 权限声明](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/res/AndroidManifest.xml)


- [`SystemHealthManager` API](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [AOSP：Power stats HAL](https://source.android.com/docs/core/power/power-stats-hal)
