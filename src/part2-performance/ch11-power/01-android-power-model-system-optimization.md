---
title: Android 功耗模型与系统级优化
chapter: '11.1'
section: '11.1'
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
tags:
- power
- battery
- power_profile
- BatteryStats
- ODPM
- Coulomb Counter
- Fuel Gauge
- IPowerStats
- 功耗归属
- doze
- standby
- battery-saver
- background-restriction
- oem-power
- adaptive-battery
- foreground-service
confidence: medium
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1 / Android common kernel android17-6.18-2026-06_r6 / PowerAttributor and PowerStatsProcessor pipeline
note: Android 17+ 屏幕功耗归因处理器
sources:
- type: aosp
  path: frameworks/base/core/res/res/xml/power_profile.xml
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/PowerAttributor.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/stats/processor/ScreenPowerStatsProcessor.java
- type: aosp
  path: hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl
- type: kernel
  path: include/linux/power_supply.h
- type: kernel
  path: drivers/power/supply/power_supply_core.c
- type: official
  path: https://source.android.com/docs/core/power
- type: official
  path: https://source.android.com/docs/core/power/values
- type: official
  path: https://developer.android.com/studio/profile/power-profiler
- type: official
  path: https://developer.android.com/reference/android/os/health/SystemHealthManager
- type: official
  path: https://perfetto.dev/docs/reference/traced_probes
- type: official
  path: https://developer.android.com/training/monitoring-device-state/doze-standby
- type: official
  path: https://developer.android.com/topic/performance/appstandby
- type: official
  path: https://developer.android.com/topic/performance/power/power-details
- type: official
  path: https://developer.android.com/topic/performance/power/test-power
- type: official
  path: https://developer.android.com/guide/components/activities/secure-bal
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- type: official
  path: https://developer.android.com/develop/sensors-and-location/location/background
- type: official
  path: https://source.android.com/docs/core/power/mgmt
- type: official
  path: https://source.android.com/docs/core/power/platform_mgmt
- type: official
  path: https://source.android.com/docs/core/power/trackers
- type: official
  path: https://source.android.com/docs/core/power/routine-battery-saver
- type: official
  path: https://developer.android.com/reference/android/os/PowerManager
- type: official
  path: https://developer.android.com/reference/android/app/job/JobScheduler
- type: official
  path: https://developer.android.com/reference/android/app/AlarmManager
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java
- type: aosp
  path: frameworks/base/services/usage/java/com/android/server/usage/UsageStatsService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/LowPowerStandbyController.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverController.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverPolicy.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityOptions.java
- type: aosp
  path: frameworks/base/core/java/android/os/PowerManager.java
- type: kernel
  path: kernel/power/suspend.c
- type: kernel
  path: kernel/sched/idle.c
- type: kernel
  path: drivers/base/power/wakeup.c
- type: community
  path: https://dontkillmyapp.com/
- type: official
  path: https://developer.android.com/topic/performance/app-hibernation
- type: official
  path: https://developer.android.com/about/versions/15/features#app-archiving
- type: official
  path: https://developer.android.com/reference/android/content/pm/PackageInstaller#requestArchive(java.lang.String,android.content.IntentSender)
- type: official
  path: https://developer.android.com/about/versions/oreo/background
- type: official
  path: https://developer.android.com/topic/performance/power
- type: official
  path: https://developer.android.com/about/versions
related_chapters:
- '5.2'
- '11.2'
- '14.1'
- '1.1'
- '4.3'
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch11-power/01-power-model.md
- src/part2-performance/ch11-power/03-system-power-optimization.md
---

# Android 功耗模型与系统级优化

“某应用耗了多少电”看似只有一个数字，平台内部却要完成三件不同的工作：

1. 记录 CPU、屏幕、网络、传感器、WakeLock 等资源活动；
2. 把活动时间或硬件能量读数换算成组件耗电；
3. 把共享组件的成本分配给 UID（Linux 用户标识，Android 用它归集应用资源），再生成 Settings 和 bugreport 使用的结果。

这三层使用的数据源、单位和误差不同。BatteryStats 里的活动时长、PowerStats HAL（硬件抽象层）的能量读数、ODPM rail（设备级电源轨计量）和设置页里的应用百分比不能直接横向比较。

Framework 行为按 Android 17 / API 37 / `android-17.0.0_r1` 核对。内核接口按 `android17-6.18-2026-06_r6` 核对；具体 Fuel Gauge（电量计）、PMIC（电源管理芯片）和 rail（电源轨）名称由设备厂商实现。

功耗由 CPU、GPU、屏幕、网络、定位和传感器等组件在时间窗口内的活动共同产生。系统优化通过调度、休眠、批处理和硬件状态控制缩短高功率驻留时间。

## 组件功率、驻留时间与归因口径

### 1. Android 17 功耗统计全景

| 层次 | 典型对象 | 记录内容 | 常用单位 |
|---|---|---|---|
| 电池侧 | Fuel Gauge、Coulomb Counter（库仑计） | 电池剩余电量、电流、电压、温度 | µAh、µA、mV、百分比 |
| 模块计量 | PowerStats HAL、ODPM | energy consumer（逻辑耗能组件）或 rail 的累计能量 | µWs |
| 活动记账 | `BatteryStatsImpl` | UID 和组件的时间、计数、状态、能量桶 | ms、次数、字节、µC 等 |
| 归因计算 | `PowerAttributor`、`*PowerStatsProcessor` | 设备组件和 UID 的估算耗电 | mAh |
| 对外结果 | `BatteryUsageStats`、`UidBatteryConsumer` | 查询窗口内的组件与 UID 归因 | mAh、百分比 |
| 诊断工具 | bugreport、Battery Historian、Perfetto、Power Profiler | 时间线、统计结果、rail 变化 | 取决于数据源 |

`µWs` 表示能量，`µAh` 和 `mAh` 表示电荷量，百分比表示电池剩余容量比例。能量与电荷量之间的换算还需要电压，不能忽略单位直接比较。

数据从硬件进入 Framework 后，并不保证每层都完整。设备没有对应 energy consumer 时，Framework 会使用 controller activity（控制器活动统计）或 `power_profile.xml`；共享 rail 无法给出 UID 归属时，Framework 还要按活动时间分配。

### 2. `power_profile.xml`：软件估算的设备参数

`frameworks/base/core/res/res/xml/power_profile.xml` 描述组件在不同状态下、折算到电池侧的平均电流。官方要求单位为 mA，并按标称电压测量。Framework 将电流与活动时长相乘，得到电荷量：

`charge(mAh) = current(mA) × duration(ms) / 3_600_000`

该文件用于估算电池消耗，不是 PMIC rail 的原始电流表。rail 位于不同电压域时，不能直接把 rail 电流填进 profile，因为相同电流在不同电压下对应的功率不同。

#### 2.1 AOSP 文件为何不能当设备参数

Android 17 AOSP 默认文件明确声明数值是故意设置的错误值，OEM 出货前必须用目标设备测量值覆盖。下面摘录的 `0.1` 来自 `android-17.0.0_r1`，用于展示字段形态。

```xml
<device name="Android">
    <item name="screen.on.display0">0.1</item>
    <item name="screen.full.display0">0.1</item>

    <item name="wifi.on">0.1</item>
    <item name="wifi.active">0.1</item>
    <item name="wifi.scan">0.1</item>

    <array name="cpu.active">
        <value>0.1</value>
    </array>
    <array name="cpu.clusters.cores">
        <value>1</value>
    </array>
    <array name="cpu.speeds.cluster0">
        <value>400000</value>
    </array>
    <array name="cpu.active.cluster0">
        <value>0.1</value>
    </array>
</device>
```

这段 XML 只能说明 display、Wi-Fi 和 CPU cluster 的键如何组织。任何性能报告若使用这些默认电流计算真实设备耗电，结果都没有设备测量意义。

#### 2.2 CPU 参数按 scaling policy 与频点组织

异构 CPU 需要描述 cluster（核簇）的核数、频点和对应活动电流。Android 17 的 `CpuPowerStatsProcessor` 从 `CpuScalingPolicies` 取得 scaling policy（共享调频策略的一组 CPU）与频点，并从 `PowerProfile` 读取三类参数：

- CPU 整体 active 的基础电流；
- scaling policy 活跃的附加电流；
- scaling step，也就是某个具体频点的附加电流。

没有 CPU energy consumer 时，处理器按 uptime（设备处于运行状态的时间）、policy 运行时间和频点时间形成 profile 估算。有 hardware energy（硬件能量读数）时，处理器仍会利用 profile 的 power bracket（合并了相近功耗档位的分组）和 UID 时间，把 energy consumer 的总量按活动比例分配。

因此，相同 CPU time 不保证相同耗电。任务运行在哪个 policy、哪些频点，以及设备是否提供 measured energy，都会改变结果。

#### 2.3 modem、Wi-Fi 与 Bluetooth 还有 controller 数据

现代 profile 同时保留 legacy（兼容旧实现）项和 controller 项。Wi-Fi 可提供 idle、rx、不同 tx level（发射功率档位）及工作电压；modem 配置可区分 RAT（无线接入技术）、NR（5G New Radio）频段和发射等级；Bluetooth controller 也可提供 idle、rx、tx 统计。

使用哪组数据取决于芯片、HAL 和 Framework collector（统计采集器）的能力。不能把所有设备简化成“开启时间 × 一个固定 mA”。同一网络制式的发射功率、驻留状态和 tail（传输结束后保持高功耗状态的一段时间）行为也由基带、运营商与设备策略决定。

### 3. 组件功耗如何进入归因

#### 3.1 CPU

Android 17 不再使用顶层 `CpuPowerCalculator`。入口变为：

`BatteryUsageStatsProvider → PowerAttributor → MultiStatePowerAttributor → CpuPowerStatsProcessor`

`CpuPowerStatsProcessor` 会按设备状态、屏幕状态和 UID 进程状态聚合 CPU 统计。缺少 measured energy（实测能量）时使用 profile；存在 CPU cluster energy consumer 时，以硬件能量校正各 power bracket，再按 UID 在 bracket 中的活动比例分配。

这里的“硬件能量优先”不表示 HAL 能直接识别每条应用线程。HAL 提供组件或 cluster 总量，UID 归属仍依赖 CPU 活动统计。

#### 3.2 Display

`ScreenPowerStatsProcessor` 先计算设备级屏幕耗电：

- 有 screen energy consumer 时，使用累计能量；
- 没有时，使用 screen-on、doze（低功耗显示状态）、亮度档位时长与 profile。

UID 分配阶段按 top activity duration（应用处于最前台的 Activity 时长）占比分配亮屏耗电。Android 17 处理器在总 top activity duration 为 0 时跳过 UID 分配，不再保留 Android 16 `ScreenPowerCalculator` 中 10 分钟的 smear（按时长摊分）门槛。

硬件 screen energy consumer 仍然是设备级输入。它提高屏幕总量的测量质量，不能自动得到每个应用的屏幕电量；UID 结果依旧来自前台活动时长比例。

#### 3.3 GPU

Android 17 的标准 `BatteryConsumer.POWER_COMPONENT_*` 集合没有 GPU，`EnergyConsumerType.aidl` 也没有 GPU 专用枚举。GPU rail 可通过下列入口观察：

- Pixel 6 及后续 Pixel 的 ODPM / Power Profiler；
- 厂商 PowerMonitor measurement 或 consumer；
- Perfetto 中设备提供的 GPU rail；
- GPU frequency、busy 和调度 trace，用作负载代理指标；它们描述活跃程度，不直接等于能量。

`PowerMonitor` consumer 名称可以出现 GPU，但名称和组合方式允许 OEM 自定义。它与 `BatteryConsumer` 是否有标准 GPU 组件是两个 API 层面。

#### 3.4 Cellular、Wi-Fi 与 Bluetooth

通信组件可能组合使用：

- controller activity：idle、rx、tx 及发射等级时长；
- network bytes、packets、scan 和连接状态；
- PowerStats energy consumer；
- `power_profile.xml` 回退参数。

共享 controller 或共享 rail 需要二次分配。网络字节多不一定代表 radio（无线通信模块）耗电高，短而分散的传输还可能增加唤醒和高功耗状态驻留时间。诊断时应同时观察传输窗口、网络状态、controller activity 与 rail。

#### 3.5 GNSS、Camera、Audio、Video 与 Sensor

这些组件也存在多种路径：

| 组件 | 活动证据 | 能量输入 | UID 归属注意点 |
|---|---|---|---|
| GNSS | 请求者、signal quality（信号质量）、活跃时间 | energy consumer 或 profile | 多个请求者可能共享一次定位 |
| Camera | Camera 使用状态与时长 | CAMERA energy consumer 或 `camera.avg` | rail 可能包含 ISP（图像信号处理器）、传感器或共享域 |
| Audio / Video | 播放、编码、解码时间 | profile、DSP（数字信号处理器）/controller/vendor monitor | offload（交给专用硬件处理）与非 offload 路径不同 |
| Bluetooth | scan、controller rx/tx/idle | controller activity、energy consumer、profile | BLE、经典连接和音频链路不能混为一类 |
| Sensor | 注册 UID 与活跃时间 | sensor power 参数或 vendor 数据 | batching（批量上报）会改变唤醒成本 |

profile 数字反映特定设备测量条件。Camera、GPS 或 Bluetooth 没有跨设备通用电流值。

### 4. BatteryStats：活动记账层

`BatteryStatsService` 运行在 `system_server`，主要状态由 `BatteryStatsImpl` 维护。它负责记录活动与归属线索，并不会持续读取整机电流。

#### 4.1 Push 与 Pull

控制组件状态的系统服务会在状态变化时推送事件，例如屏幕、Wi-Fi、定位和 WakeLock（阻止设备进入部分休眠状态的锁）。CPU 等累计统计则在状态切换或采样点拉取快照。Android 官方将两者称为 push（推送）和 pull（拉取）。

一次 UID 归因可能依赖多种线索：

- CPU active、policy、频点和 UID 时间；
- 前台、后台、top（最前台）等进程状态；
- WakeLock、Job、Sync、FGS（前台服务）与传感器时长；
- 网络字节、controller activity 和 radio 状态；
- EnergyConsumer 累计值；
- BatteryStats history 中的状态变化。

`BatteryStatsImpl` 记录的是 UID 级统计，UID 不总是单个进程。共享 UID、多进程应用、系统 UID 和 SDK sandbox（SDK 沙箱进程）等场景都要先确认身份边界。

#### 4.2 时间窗口与持久化

BatteryStats 会持久化统计，跨重启保留需要的历史信息。`/data/system/batterystats.bin` 是当前实现中的存储文件，不属于应用可依赖的公开接口。

拔掉充电器不会无条件重置所有统计。Android 17 的 `shouldResetOnUnplugLocked()` 根据满电、高电量、一次明显充电和 session（统计会话）时长等条件决定是否 reset；高电量阈值由 `BatteryStatsConfig.getHighBatteryLevelAfterCharge()` 提供，默认值为 90，OEM 可以配置。

实验前执行 `dumpsys batterystats --reset` 是人为建立采集窗口，和系统自动 reset 的策略不同。重置会影响整机统计，不应在用户设备或多人共享测试环境随意执行。

#### 4.3 `dumpsys batterystats` 能回答什么

在专用测试机上，可以用下面的命令建立一个明确窗口并导出结果。

```bash
adb shell dumpsys batterystats --reset

# 运行受控测试场景后导出
adb shell dumpsys batterystats > batterystats.txt
adb bugreport bugreport.zip
```

`dumpsys` 适合核对 UID 活动、WakeLock、网络、Job 和组件统计；bugreport 可交给 Battery Historian（将 BatteryStats 历史数据可视化的工具）。命令结果是统计与归因证据，不是外接功耗仪的瞬时电流曲线。

### 5. Coulomb Counter、Fuel Gauge 与 Framework 归因

#### 5.1 Coulomb Counter

Coulomb Counter 对电池充放电电流做时间积分，得到 charge（电荷量）变化。Android 设备常通过 Fuel Gauge 和 Health HAL 暴露剩余 charge、current、capacity 等属性。`BatteryManager` 中常见单位包括：

- `BATTERY_PROPERTY_CHARGE_COUNTER`：µAh；
- `BATTERY_PROPERTY_CURRENT_NOW`：µA；
- `BATTERY_PROPERTY_CAPACITY`：百分比；
- `BATTERY_PROPERTY_ENERGY_COUNTER`：nWh，设备支持情况不同。

属性缺失、符号方向和采样行为由设备实现决定。任何精度结论都要依据目标 Fuel Gauge 数据手册和整机验证，不能给 Coulomb Counter 设一个通用误差范围。

#### 5.2 Fuel Gauge

Fuel Gauge 通常结合 Coulomb counting（库仑计量）、电压、温度、电池模型和校准状态估计 State of Charge（SOC，剩余电量比例）。部分实现还提供 State of Health（SOH，电池健康状态）。它面对的是整块电池，不能识别某次电流由哪个 UID 引起。

`android17-6.18-2026-06_r6` 中，`include/linux/power_supply.h` 和 `drivers/power/supply/power_supply_core.c` 定义了通用 power_supply 框架。具体 Gauge 驱动、属性集合和校准算法位于厂商实现；Android common kernel 只能作为接口锚点。

#### 5.3 两类结果不能互相替代

| 问题 | 合适数据 |
|---|---|
| 电池在测试窗口少了多少 charge（电荷量） | Fuel Gauge / 外接功耗仪 |
| 某个 rail 在窗口内增加了多少 energy（能量） | ODPM / PowerMonitor measurement |
| 哪个组件最活跃 | BatteryStats、Perfetto 状态和 controller 数据 |
| 哪个 UID 被归因了多少 mAh | BatteryUsageStats / UidBatteryConsumer |
| 某代码改动是否降低整机平均功率 | 外接仪表或稳定 rail delta，加受控 A/B |

Framework 不会简单地把 Coulomb Counter 总差值按应用比例切分。BatteryUsageStats 的组件算法可能使用 measured energy、controller 数据或 profile，再依据 UID 活动分配。电池总差值还包含系统、屏幕、基带、供电转换损耗和未归因部分。

### 6. Android 17 归因管线

#### 6.1 从 history 到 `BatteryUsageStats`

Android 17 的主路径为：

| 阶段 | 对象 | 作用 |
|---|---|---|
| 记录 | `BatteryStatsImpl` / `BatteryStatsHistory` | 保存状态变化、计数和能量输入 |
| 配置 | `AggregatedPowerStatsConfig` | 定义设备、屏幕、进程等聚合维度 |
| 聚合 | `MultiStatePowerAttributor` | 读取 history（状态变化历史），按时间与状态组织组件统计 |
| 计算 | `processor/*PowerStatsProcessor` | 计算设备组件和 UID 的 mAh |
| 输出 | `BatteryUsageStats.Builder` | 生成设备与 UID consumer |

`PowerAttributor` 是接口，Android 17 默认实现使用 `MultiStatePowerAttributor`。不同 processor 的算法各自决定 measured energy、profile 和活动时长的组合方式，因此不能写出一条覆盖所有组件的统一分摊公式。

#### 6.2 Android 16 到 17 的边界

Android 16 是迁移阶段：`BatteryUsageStatsProvider` 对已支持的组件调用 `PowerAttributor`，其余组件保留 `*PowerCalculator`。`android-17.0.0_r1` 的 provider 已移除这组顶层 calculator 回退，委托 `PowerAttributor` 生成组件结果。

阅读 Android 17 源码时，应从 `PowerAttributor`、`MultiStatePowerAttributor` 和 `processor/` 目录进入。使用 Android 16 或更早 tag 讨论历史行为时，仍需查看 `CpuPowerCalculator`、`ScreenPowerCalculator` 等旧实现。

#### 6.3 设置页百分比的边界

Settings 使用的是 Framework 归因结果，不是 HAL 原始 rail 表。应用百分比受以下因素影响：

- 查询窗口与 BatteryStats reset 边界；
- measured energy 是否可用；
- profile 与 controller 参数质量；
- UID 前后台状态；
- 共享资源分配；
- 系统组件、未归因量和 reattribution（重新归因）；
- Settings 自身的分组和展示策略。

这个百分比适合排序和寻找异常组件。它不具备实验室仪表的绝对精度，所有 UID 百分比相加也不一定覆盖电池端观测到的全部消耗。

### 7. PowerStats HAL、ODPM 与 PowerMonitor

#### 7.1 HIDL 与 AIDL 版本边界

Android 10、Android 11 的历史实现使用 HIDL（旧一代 HAL 接口定义语言）`android.hardware.power.stats@1.0::IPowerStats`：

- `getRailInfo()` 返回 rail 描述；
- `getEnergyData()` 返回累计能量；
- `EnergyData.energy` 使用 µWs。

Android 12 起的 AIDL（Android 接口定义语言）`android.hardware.power.stats.IPowerStats` 分为两组：

- `getEnergyConsumerInfo()` / `getEnergyConsumed()` 返回逻辑 consumer 与 `EnergyConsumerResult.energyUWs`；
- `getEnergyMeterInfo()` / `readEnergyMeter()` 返回 Channel 与 `EnergyMeasurement.energyUWs`。

AIDL consumer 可以附带 UID attribution（UID 归因），但供应商是否提供、如何划分均由硬件与 HAL 决定。Channel 更接近物理或逻辑 meter（计量通道），名称不具备跨设备稳定性。

#### 7.2 ODPM 与 Pixel

Android Studio 官方 Power Profiler 文档说明，ODPM（On-Device Power Monitor，设备内功耗监测）rail 目前面向 Pixel 6 及后续 Pixel 设备。可见 rail 随设备变化，常见类别包括 CPU cluster、GPU、memory、display、camera、cellular、WLAN 和 UFS。

ODPM 测量设备级 rail。测试期间其他应用、系统服务、亮度和网络活动都会进入读数。rail 的名称、边界与采样行为也由设备实现决定，因此报告必须同时记录机型、构建号和 rail 名。

不支持 ODPM 的设备仍可提供 battery gauge、Coulomb counter、BatteryStats 和其他代理指标。缺少 rail 不表示设备没有该模块的耗电。

#### 7.3 API 35 `PowerMonitor`

Android 15 / API 35 增加 `PowerMonitor`、`PowerMonitorReadings` 和 `SystemHealthManager` 的异步读取 API。monitor 分为：

- `POWER_MONITOR_TYPE_MEASUREMENT`：直接测量的 device-specific rail（设备专用电源轨）；
- `POWER_MONITOR_TYPE_CONSUMER`：子系统 consumer，可能直接对应 rail，也可能经过模型计算或组合。

下面的读取函数保留 monitor 名称、类型、累计能量和各自时间戳，并处理设备不支持与能量不可用。

```kotlin
data class PowerReading(
    val name: String,
    val type: Int,
    val energyUWs: Long,
    val timestampMillis: Long
)

@RequiresApi(35)
fun readSupportedPowerMonitors(
    context: Context,
    executor: Executor,
    onSuccess: (List<PowerReading>) -> Unit,
    onFailure: (RuntimeException) -> Unit
) {
    val manager =
        context.getSystemService(SystemHealthManager::class.java)
            ?: return onSuccess(emptyList())

    manager.getSupportedPowerMonitors(executor) { monitors ->
        if (monitors.isEmpty()) {
            onSuccess(emptyList())
            return@getSupportedPowerMonitors
        }

        manager.getPowerMonitorReadings(
            monitors,
            executor,
            object : OutcomeReceiver<PowerMonitorReadings, RuntimeException> {
                override fun onResult(readings: PowerMonitorReadings) {
                    val result = monitors.mapNotNull { monitor ->
                        val energy = readings.getConsumedEnergy(monitor)
                        if (energy == PowerMonitorReadings.ENERGY_UNAVAILABLE.toLong()) {
                            null
                        } else {
                            PowerReading(
                                name = monitor.name,
                                type = monitor.type,
                                energyUWs = energy,
                                timestampMillis =
                                    readings.getTimestampMillis(monitor)
                            )
                        }
                    }
                    onSuccess(result)
                }

                override fun onError(error: RuntimeException) {
                    onFailure(error)
                }
            }
        )
    }
}
```

`getConsumedEnergy()` 返回自开机以来的累计 µWs，并包含插电期间的能量；重启后不保留。比较场景应使用同一 monitor 的前后差值和对应 timestamp（时间戳），不能拿累计值直接当“本次操作耗电”。设备不支持 ODPM 时，supported monitor 列表可能为空。

### 8. Perfetto、Power Profiler 与 Battery Historian

#### 8.1 Perfetto `android.power`

Perfetto 的数据源名为 `android.power`。下面的配置同时采集 charge、capacity 和设备支持的 power rails。

```protobuf
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 1000
      battery_counters: BATTERY_COUNTER_CHARGE
      battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
      collect_power_rails: true
    }
  }
}

duration_ms: 60000
```

`collect_power_rails` 只会输出设备提供的 rail。`battery_poll_ms` 是 trace 采样配置，不代表 Fuel Gauge 硬件更新频率。长窗口需要评估 trace buffer（轨迹缓冲区）、文件大小与设备扰动，生产设备采集还要遵守权限和隐私约束。

#### 8.2 工具回答的问题不同

| 工具 | 强项 | 边界 |
|---|---|---|
| Battery Historian | bugreport 中的 BatteryStats 时间线 | 依赖采集窗口和 BatteryStats 数据 |
| `dumpsys batterystats` | UID、WakeLock、Job、网络和组件统计 | 不提供高频电流波形 |
| Perfetto | rail、battery counter、调度、频率和应用 trace 的时间关联 | rail 设备相关；trace 本身有采集成本 |
| Power Profiler | Android Studio 中对比应用操作与 rail | ODPM 设备范围与 rail 可用性有限 |
| 外接功耗仪 | 受控场景的整机电流和能量 | 无法自动分配到 UID 或组件 |
| PowerMonitor API | 应用内读取累计 monitor 能量 | 设备支持、名称、范围与更新节奏不同 |

工具选择取决于问题。整机 A/B 更适合外接仪表；模块变化适合 rail；UID 耗电归属适合 BatteryUsageStats；代码和电源事件的时间关系适合 Perfetto。

### 9. 如何做可信的功耗实验

#### 9.1 先确定测量对象

实验开始前写清楚目标：

- 整机电池 charge；
- 某条 rail 的 energy；
- 某个组件的 BatteryUsageStats mAh；
- 某 UID 的归因结果；
- 用户任务完成所需的总能量。

测量对象不同，结论不能互换。降低 UID 归因值未必降低整机能量，rail 降低也可能被其他 rail 抵消。

#### 9.2 控制实验条件

- 固定设备、系统构建、应用版本和数据集；
- 记录亮度、刷新率、网络、信号、音量、温度和充电状态；
- 让对比组从一致的 thermal（温控）、缓存、登录和电池状态开始；
- 采用多轮、交错顺序，报告离散程度；
- 用时间戳对齐应用 trace、服务端日志、rail 和 battery counter；
- 对 idle baseline（空闲基线）单独采样，避免把系统后台活动归给应用；
- 记录失败、重试、未完成任务和输出质量。

短测试中，电池百分比粒度通常过粗。可以使用 charge counter、rail delta 或外接仪表，但仍要验证读数的更新周期和噪声。

#### 9.3 校准的正确含义

校准用于检查 profile 或工具与受控参考测量之间的偏差。一个场景得到的校准系数不能直接用于所有组件、温度和设备。

OEM 制作 `power_profile.xml` 时，应按官方 Power Values 指导在目标硬件上测量组件增量电流。应用团队做回归时，更适合保持工具、设备和条件一致，比较同一指标的差值；不要用一个整机系数修正所有 UID 归因。

### 10. 与内核调度和 ADPF 的边界

Linux EAS（Energy-Aware Scheduling，能耗感知调度）使用 Energy Model 评估任务放在哪个 CPU 上。BatteryStats 使用 `power_profile.xml`、energy consumer 和活动统计计算查询窗口内的耗电。两者都涉及能量模型，但数据结构、时间尺度和用途不同。

在 `android17-6.18-2026-06_r6` 中，EAS 调度路径使用内核 Energy Model 与调度利用率；Android 17 AOSP 没有标准调用链把 ODPM rail 实时写回 EAS cost table（调度成本表）。PowerStats 与 PowerMonitor 用于观测能量，ADPF（Android Dynamic Performance Framework）`PerformanceHintManager` 则由应用提供工作负载提示。

厂商可以在 Power HAL、调度器和固件中实现额外联动。缺少 vendor（厂商）源码和设备 trace 时，只能把这些联动标记为设备特性，不能推广为 Android 17 平台通用机制。

### 11. Android 17 源码阅读入口

| 主题 | 源码入口 |
|---|---|
| profile 默认结构 | `frameworks/base/core/res/res/xml/power_profile.xml` |
| 活动与 history | `frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java` |
| 查询入口 | `frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java` |
| 归因接口 | `frameworks/base/services/core/java/com/android/server/power/stats/PowerAttributor.java` |
| 默认多状态归因 | `frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java` |
| CPU 归因 | `frameworks/base/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java` |
| Screen 归因 | `frameworks/base/services/core/java/com/android/server/power/stats/processor/ScreenPowerStatsProcessor.java` |
| 公共 monitor API | `frameworks/base/core/java/android/os/PowerMonitor.java`、`PowerMonitorReadings.java` |
| PowerStats AIDL | `hardware/interfaces/power/stats/aidl/android/hardware/power/stats/` |
| kernel power_supply | `include/linux/power_supply.h`、`drivers/power/supply/power_supply_core.c`，tag `android17-6.18-2026-06_r6` |

### 12. 复核检查表

- [ ] 区分活动时间、charge、energy、power 和百分比。
- [ ] 确认 `power_profile.xml` 来自目标设备，未使用 AOSP 默认值。
- [ ] Android 17 归因从 `PowerAttributor` 与 processor 目录阅读。
- [ ] Screen measured energy 与 UID top-activity 分配没有混写。
- [ ] GPU rail、PowerMonitor consumer 与 BatteryConsumer 标准组件没有混写。
- [ ] BatteryStats reset、查询窗口和插电状态已经记录。
- [ ] PowerMonitor 使用前后差值，并处理不支持该功能与 `ENERGY_UNAVAILABLE` 两种情况。
- [ ] ODPM 报告包含设备、构建、rail 名和并行系统负载。
- [ ] A/B 测试固定亮度、刷新率、网络、温度与数据集。
- [ ] 结论范围与测量工具一致，没有从设备 rail 直接推导 UID 电量。

### 版本与实现边界

| 版本 | 可验证变化 |
|---|---|
| Android 5.0 / API 21 | BatteryStats 与 Battery Historian 成为系统功耗诊断的重要入口 |
| Android 7.0 / API 24 | Wi-Fi、Bluetooth 和 modem controller activity 在设备支持时提供更细的状态数据 |
| Android 10 / API 29 | HIDL PowerStats HAL 提供 rail 信息与累计能量 |
| Android 12 / API 31 | AIDL PowerStats HAL 将 energy consumer 与 energy meter/channel 分开 |
| Android 15 / API 35 | 公开 `PowerMonitor`、`PowerMonitorReadings` 与 `SystemHealthManager` 读取 API |
| Android 16 / API 36 | `BatteryUsageStatsProvider` 处于 calculator 与 `PowerAttributor` 并存的迁移阶段 |
| Android 17 / API 37 | provider 委托 `PowerAttributor`；`MultiStatePowerAttributor` 配置组件 processor；screen UID 分配移除旧 10 分钟 smear 门槛；unplug reset 高电量阈值改为 `BatteryStatsConfig` 配置 |

版本迭代解释历史报告时很有用。分析 Android 17 时应优先使用 `processor/*PowerStatsProcessor`，避免把 Android 16 calculator 的实现细节当作当前源码。

## 调度、休眠与硬件状态控制

功耗模型指出能量花在哪里，系统策略决定工作何时执行、能否批处理以及设备能否进入低功耗状态。

### 系统为什么要限制后台工作

单个 App 只知道自己的任务是否紧急，系统还要综合考虑电量、充电状态、屏幕、移动状态、温度、内存压力、网络和其他 App。Android 因此把后台资源分配分为多组可叠加的策略：

| 决策维度 | 主要机制 | 影响对象 |
| --- | --- | --- |
| 设备是否空闲 | Doze、Light Doze、Low Power Standby | 网络、WakeLock、Job、Alarm、Sync |
| 用户多久使用一次 App | App Standby Buckets、Restricted bucket | Job 时长、Alarm 频率、后台网络 |
| 用户是否主动限制 App | Battery settings、background restriction | Job、Alarm、网络与后台执行 |
| 全局是否节电 | Battery Saver、OEM low-power policy | 位置、后台任务、显示、性能与厂商功能 |
| App 当前是否可见 | 进程重要性、FGS、BAL、while-in-use 权限 | 资源配额、界面拉起、位置与敏感资源 |
| ROM 的附加策略 | OEM 冻结、自启动和应用启动管理 | 进程调度、广播、推送与后台存活 |

下文沿用 Android 文档中的常用名称：FGS 是 Foreground Service（前台服务），BAL 是 Background Activity Launch（后台 Activity 启动），quota 表示系统分配的资源配额，OEM 指设备厂商，ROM 指设备搭载的系统。它们分别约束不同环节，不能用其中一个机制的状态推断其他机制。

同一个 Job 可能同时等待充电约束、Doze 维护窗口、standby quota（待机配额）和 OEM 调度条件。定位“为什么没运行”时，需要逐项核对证据，不能只看 WorkManager 状态。

### Doze：按设备状态集中后台活动

Android 6.0（API 23）引入 Doze（设备空闲省电模式）。设备长时间未使用时，系统暂停普通后台网络，忽略 App WakeLock，并延后 Job、Sync 与普通 Alarm；设备会周期性进入维护窗口，批量处理积压工作。

#### Light Doze 与 Deep Doze

Android 7.0（API 24）加入限制较轻的 Light Doze。Light Doze 与 Deep Doze 是两条独立的状态机，触发条件和限制强度不同：

| 模式 | 进入条件 | 主要目的 |
| --- | --- | --- |
| Light Doze（轻度 Doze） | 屏幕关闭、未充电；不要求设备静止 | 较早限制后台网络和调度，移动中的设备也能节电 |
| Deep Doze（深度 Doze） | 屏幕关闭、未充电、持续静止；完整实现依赖 significant motion detector（显著运动检测器） | 延长 suspend（系统挂起）驻留时间，限制更严格 |

设备移动、点亮屏幕或接入充电器会让 Deep Doze 退出。Light Doze 与 Deep Doze 在 `DeviceIdleController` 中有各自状态，`dumpsys deviceidle` 输出的 `mLightState`、`mState` 也要分开读。

#### 维护窗口不是定时器

维护窗口会短暂恢复网络，并分发积压的 Sync、Job 和 Alarm。设备持续空闲时，维护窗口之间的休眠间隔会逐步增长。具体时长由平台版本、资源 overlay（资源覆盖配置）、DeviceConfig（系统动态配置）与设备实现决定，App 不能把某款手机的窗口间隔当作调度 SLA（服务时限承诺）。

窗口到来只表示限制暂时放宽，仍不保证某个任务马上执行。Job 还要满足自身约束、standby bucket（待机分组）、quota 和并发调度条件。

#### Doze 中哪些能力会被限制

- 普通网络访问暂停。
- App 持有的 WakeLock 被忽略。
- `set()`、`setWindow()`、`setExact()` 等普通 Alarm 延后到维护窗口。
- JobScheduler、WorkManager 和 SyncAdapter 延后。
- 后台 Wi‑Fi 扫描停止。
- FGS 可以提高进程重要性，但不能获得设备级 Doze 豁免。

高优先级 FCM 只适合时间敏感、会产生用户可见通知的消息。系统会给接收方短暂使用网络和 partial WakeLock（只保持 CPU 运行的唤醒锁）的机会，处理完成后设备继续空闲。普通数据刷新使用 normal priority（普通优先级），并接受维护窗口延迟。

`setAndAllowWhileIdle()`、`setExactAndAllowWhileIdle()` 和 `setAlarmClock()` 能在空闲期间交付。前两者受每个 App 约九分钟一次的频率边界，系统还可以延长间隔。它们适合用户感知的关键事件，不能用于高频轮询。

#### Android 17 的 listener 型 allow-while-idle Alarm

API 37 新增 `setExactAndAllowWhileIdle(int, long, String, Executor, OnAlarmListener)`。这是 listener（监听器）形式的 allow-while-idle Alarm，可在设备空闲时交付。回调直接在指定 `Executor` 上执行，仍有组件存活的 App 因而无需为等待精确回调而持续持有 WakeLock。

`OnAlarmListener` 形式的 Alarm 依赖调用进程继续有组件运行。进程没有 Activity、Service 或 ContentProvider 时，系统可以取消它。需要在进程退出后仍能收到事件，应使用 `PendingIntent` 形式并遵守精确闹钟权限。新 API 没有改变 allow-while-idle 只能低频使用的原则。

#### Doze 豁免是部分豁免

用户可以在系统设置中把 App 加入电池优化豁免列表。豁免 App 在 Doze 中可以访问网络并持有 `PARTIAL_WAKE_LOCK`，普通 Alarm 等限制仍可能存在。App 可用 `PowerManager.isIgnoringBatteryOptimizations()` 检查状态。

`ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` 只适用于官方列出的少数核心场景，Google Play 也限制直接请求豁免。一般应用应打开电池优化设置页，由用户决定；不要在首次启动时把“无限制”当作必选权限。

#### 从 Framework 到 kernel suspend

`DeviceIdleController` 决定何时限制 App 资源，`PowerManagerService` 与 SystemSuspend 协调系统休眠。内核 `android17-6.18-2026-06_r6` 的 `kernel/power/suspend.c` 执行 suspend 主流程，`drivers/base/power/wakeup.c` 管理 wakeup source（唤醒源），`kernel/sched/idle.c` 处理 CPU idle（CPU 空闲状态）。

Doze 状态不能证明设备已经进入 suspend。驱动 wakeup source、内核 timer（定时器）、IRQ（中断请求）或 `system_server` 中的工作仍可能阻止休眠。Framework 层的状态只能证明策略已进入 idle（空闲）阶段；还要结合 `power/suspend_resume`、wakeup source 与 CPU idle 证据确认硬件状态。

#### 强制进入 Doze 的测试方法

下面的命令用于专用测试设备，主动驱动 DeviceIdle 状态并保存快照。

```bash
adb shell dumpsys battery unplug
adb shell dumpsys deviceidle force-idle
adb shell dumpsys deviceidle
adb shell dumpsys jobscheduler com.example.app
adb shell dumpsys alarm

# 测试结束后恢复设备状态
adb shell dumpsys deviceidle unforce
adb shell dumpsys battery reset
```

`force-idle` 会绕过正常等待时间，适合验证功能恢复和任务延迟，不适合测量自然进入 Doze 的时延。性能与续航测试还要覆盖屏幕关闭、设备静止的自然路径。

### App Standby Buckets：按使用关系分配配额

App Standby（应用待机）不要求整台设备空闲。Android 9（API 28）开始，系统根据使用模式把 App 动态放入不同的 standby bucket：Active（活跃）、Working set（常用）、Frequent（频繁使用）、Rare（很少使用）或 Restricted（受限）；安装后从未运行的 App 还有 `Never` 状态。

#### 当前官方指导额度

下表是 Android 官方在 2026 年提供的近似资源边界。这些数字不承诺任务一定执行；设备状态、进程可见性、充电、用户限制、bucket 变化和未来系统更新都可能改变结果。

| Bucket（待机分组） | Regular jobs（普通任务） | Expedited jobs（加急任务） | Alarms（闹钟） | 后台网络 |
| --- | --- | --- | --- | --- |
| Active | Android 16+：滚动 60 分钟内最多约 20 分钟 | 滚动 24 小时内最多约 30 分钟 | 无 bucket 频率限制 | 不限制 |
| Working set | 滚动 4 小时内最多约 10 分钟 | 滚动 24 小时内最多约 15 分钟 | 每小时最多约 10 次 | 不限制 |
| Frequent | 滚动 12 小时内最多约 10 分钟 | 滚动 24 小时内最多约 10 分钟 | 每小时最多约 2 次 | 不限制 |
| Rare | 滚动 24 小时内最多约 10 分钟 | 滚动 24 小时内最多约 10 分钟 | 每小时最多约 1 次 | 禁用 |
| Restricted | 每天一次、批量会话最多约 10 分钟 | 滚动 24 小时内最多约 5 分钟 | 每天一次 exact 或 inexact alarm（精确或非精确闹钟） | 禁用 |

充电时多数 bucket 限制会放宽，Restricted 仍有专门规则。可见或前台进程通常不受 bucket 执行限制；运行 FGS 的进程仍要遵守 bucket 对 Job 和 Alarm 的限制。Android 16 之前，Active bucket 与 FGS 并发 Job 的 runtime quota（运行时长配额）更宽松，迁移测试要注意版本差异。

`QuotaController` 负责 JobScheduler 的配额判断，`AppStandbyController` 评估 bucket，`JobSchedulerService` 汇总约束并分发任务。表里的数字来自当前默认策略说明，不应硬编码进业务重试逻辑。

#### Restricted bucket 的触发与例外

Android 12/12L 的无互动阈值为 45 天；Android 13+ 缩短为 8 天，关机时间不计入。Android 13+ 还可能因为 24 小时内广播或 binding（服务绑定）次数过多，把 App 放入 Restricted。设备厂商能调整非 Active App 的分类标准。

Companion Device（配套设备应用）、device/profile owner（设备或工作资料所有者）、persistent（常驻系统应用）、VPN、默认拨号、活动 widget（桌面小组件），以及具备部分官方列出权限或被用户设为“无限制”的 App，可能获得 Restricted 豁免。豁免条件应以运行设备和当前官方文档为准。

#### Adaptive Battery 的可确认边界

Adaptive Battery（自适应电量管理）的公开契约只保证 bucket 会动态变化。设备可能预装使用机器学习预测近期使用情况的系统 App，也可以在没有该组件时按最近使用时间排序；厂商还能实现自己的分类标准。

AOSP 和公开文档没有规定统一的模型框架、网络结构、特征集合或训练方式。App 可以依赖 `UsageStatsManager.getAppStandbyBucket()` 的返回结果；预测器内部结构不属于公开契约。

#### 检查 bucket、quota 与 pending reason

pending reason（待处理原因）指 Job 仍在等待的原因。下面的命令把测试 App 设为不同 bucket，并对照 UsageStats 与 JobScheduler。

```bash
adb shell dumpsys battery unplug
adb shell am set-standby-bucket com.example.app rare
adb shell am get-standby-bucket com.example.app
adb shell dumpsys usagestats appstandby
adb shell dumpsys jobscheduler com.example.app

# 测试结束后恢复电池模拟状态
adb shell dumpsys battery reset
```

手工分桶只覆盖 bucket 维度。测试报告还要记录屏幕、充电、Doze、Battery Saver、网络和 App 进程状态，否则无法解释同一 bucket 下的不同结果。

API 34 提供单个 pending reason，API 36 增加 `getPendingJobReasons()` 与 `getPendingJobReasonsHistory()`。API 37 的 `JobScheduler.getPendingJobReasonStats(jobId)` 返回 `PENDING_JOB_REASON_*` 到累计 `Duration`（持续时间）的映射；多个原因可同时存在，所以各项时长之和可能大于任务总等待时间。统计不会跨重启保留，任务成功或取消后也会清除。

诊断时应区分：

- `PENDING_JOB_REASON_APP_STANDBY`：bucket 阻止执行。
- `PENDING_JOB_REASON_QUOTA`：当前 Job quota 已用完。
- `PENDING_JOB_REASON_DEVICE_STATE`：Doze、Battery Saver、内存或温度等设备状态。
- `PENDING_JOB_REASON_JOB_SCHEDULER_OPTIMIZATION`：JobScheduler 选择更合适的时间。
- 显式 constraint reason（约束原因）：充电、网络、存储、minimum latency（最短等待时间）等业务约束未满足。

### 系统级后台限制

Doze 与 bucket 主要决定任务何时运行、可以运行多久。后台执行、后台界面和 while-in-use（仅使用期间授权）权限规则还会判断当前操作能否开始。

#### Background Activity Launch

Android 10（API 29）开始限制 Background Activity Launch（后台 Activity 启动，BAL）。通知、full-screen intent（全屏通知意图）、系统角色和用户交互各有专门规则，FGS 通知本身不提供通用 BAL 豁免。

PendingIntent 与 IntentSender 的授权逐步改为 opt-in（显式选择启用）：

| 版本 | 变化 |
| --- | --- |
| target 34+ | PendingIntent 发送方不再默认授予自己的 BAL 能力；通过 `setPendingIntentBackgroundActivityStartMode()` 选择模式 |
| target 35+ | PendingIntent 创建方不再默认把自己的 BAL 能力交给接收方；通过 `setPendingIntentCreatorBackgroundActivityStartMode()` 授权 |
| API 36+ | 发送方优先使用 `MODE_BACKGROUND_ACTIVITY_START_ALLOW_IF_VISIBLE`；只有确有后台拉起需求时评估更宽模式 |
| target 37+ | `IntentSender.sendIntent()` 也要求发送方按 BAL 规则显式 opt-in |

授权链还必须包含一个原本就有后台启动资格的参与者。设置 mode（授权模式）不会额外产生启动资格。可见 App 绑定服务并希望被绑定方拉起 Activity 时，Android 14+ 还要核对 `BIND_ALLOW_ACTIVITY_STARTS`。

#### 后台位置

- Android 8.0+：后台 App 通常每小时只能收到少量位置更新，此限制与 targetSdk 无关。
- Android 10+：持续后台定位需要 `ACCESS_BACKGROUND_LOCATION`，仅有 `coarse`/`fine`（粗略/精确位置）权限只覆盖 while-in-use。
- Android 11+：从可见界面启动的 `location` FGS 属于 foreground location（前台定位），界面退到后台后仍可继续；App 已在后台才启动 FGS 时，没有 `ACCESS_BACKGROUND_LOCATION` 就不能获得位置。
- Android 14、target 34+：创建 `location` FGS 时立即校验类型权限与 while-in-use 条件。App 已在后台且不满足例外时，可能抛 `SecurityException` 或 FGS 启动异常。

地理围栏和 batched location（批量定位）可以减少 App 主动轮询，但不会绕过权限和系统交付边界。

#### 后台 Service 与 FGS

Android 8.0+ 对后台 Service 的创建和存活施加限制。可延迟任务交给 JobScheduler 或 WorkManager；用户知情的持续任务使用匹配类型的 FGS，并接受后台启动限制、类型权限和时长规则。

FGS 不能提升 bucket 等级、绕过 Doze、跳过 Job quota 或获得 while-in-use 权限。Android 16 起，与 FGS 并发的 Job 明确受 runtime quota 约束。

### Hibernation 与 Archiving

Hibernation（应用休眠）与 Archiving（应用归档）都会让长期未用的 App 停止后台活动，但两者对存储占用和恢复流程的影响不同：

| 机制 | 平台起点 | 系统动作 | 恢复时要处理 |
| --- | --- | --- | --- |
| App hibernation | Android 11 权限自动重置；Android 12 扩展完整休眠 | 重置运行时权限、停止后台 Job/Alarm/Push、清理 cache（缓存） | 用户重新交互后退出休眠；权限不会自动恢复，旧 Job/Alarm 也不会自动重新调度 |
| App archiving | Android 15 提供 OS 级 archive/unarchive（归档/恢复） | 安装器移除 APK 与 cache，保留用户数据；Launcher（桌面启动器）可展示归档状态 | 用户点击后由负责的 installer（安装器）恢复包，再按安装/恢复路径初始化 |

Android 15 提供 `PackageInstaller.requestArchive()`，调用者需要 `REQUEST_DELETE_PACKAGES`。是否自动选择长期未用 App、由哪个商店恢复、图标如何显示，取决于安装器和设备体验。不能把 Google Play 的 auto-archive（自动归档）策略写成所有 Android 15 设备的统一行为。

Hibernation 恢复后，App 应检查权限并重建必要任务。WorkManager 能帮助恢复一部分持久工作，业务仍要验证依赖的 Alarm、通知和服务是否重新注册。

### Battery Saver 与 Low Power Standby

#### Battery Saver 是全局策略输入

Battery Saver 是系统级省电模式。`PowerManagerService` 发布 low-power（低功耗）状态，`BatterySaverController` 与 `BatterySaverPolicy` 计算各服务的策略。设备可以调整具体限制，所以 App 应读取公开状态并降低自身工作量：

- `PowerManager.isPowerSaveMode()` 判断 Battery Saver 是否开启。
- `ACTION_POWER_SAVE_MODE_CHANGED` 监听状态变化。
- `getLocationPowerSaveMode()` 返回当前定位节电策略，可能是屏幕关闭后停用 GNSS、停用全部 provider（位置提供方）、只给前台 App、降低请求频率或不改变。

Battery Saver 不会简单地把所有 App 改成 Rare bucket。Job、Alarm、位置、网络、显示与性能策略会分别根据 low-power 状态调整，OEM 还能加入刷新率、性能上限或传感器策略。某项功能是否改变，应在目标 build（系统构建版本）上读取状态并测量。

#### Low Power Standby 的限制更直接

Android 13（API 33）公开 Low Power Standby（低功耗待机）状态。启用后，设备处于非交互状态且不在 maintenance window（维护窗口）时，App 的网络访问会被禁用，持有的 WakeLock 会被忽略；运行 FGS 的 App 也在范围内。系统角色、ongoing call（进行中的通话）、临时 allowlist（允许列表）或设备 policy（策略）可以获得例外。

App 可用 `isLowPowerStandbyEnabled()` 检查功能是否开启，并监听 `ACTION_LOW_POWER_STANDBY_ENABLED_CHANGED`。排查“FGS 明明活着却断网”时，要把 Low Power Standby 与 Doze、Data Saver 分开确认。

#### Adaptive Battery 与 Routine Battery Saver

- Adaptive Battery（自适应电量管理）影响单个 App 的 bucket 分类，分类器可以使用预测或最近使用排序。
- Routine Battery Saver（按日常规律触发的省电模式）是 Android 10 的可选 OEM 集成。OEM 通过 `config_batterySaverScheduleProvider` 指定特权 provider（策略提供方），provider 用受 `POWER_SAVER` 保护的 API 提供启用提示。
- Adaptive Charging（自适应充电）属于电池健康与充电管理，设备实现可能根据日程、温度和电池状态控制充电。它不等于 App Standby 或 Battery Saver，也不能从 Android 版本推导每台设备的充电曲线。

三项功能可能同时存在，证据入口分别是 bucket、low-power 状态，以及充电与 battery health（电池健康）服务。

#### Battery Saver 测试

下面的官方测试命令模拟设备断开电源，并打开 `low_power` 系统设置项；测试结束后恢复 BatteryService 状态。

```bash
adb shell dumpsys battery unplug
adb shell settings put global low_power 1
adb shell dumpsys power
adb shell dumpsys jobscheduler com.example.app

# 测试结束后恢复
adb shell dumpsys battery reset
```

性能基准要记录 Battery Saver、Low Power Standby、温度、充电和屏幕状态。CPU 频率下降或帧率变化属于设备结果，不能仅凭 `low_power=1` 预设固定幅度。

### OEM 功耗策略：按具体设备验证行为

AOSP 允许厂商调整 bucket 分类和低功耗策略。ROM 还可能提供自启动、关联启动、后台活动、睡眠待机、冻结和用户白名单等设置。这些名称、默认值和行为会随品牌、机型、地区与系统版本改变。

社区站点 Don't Kill My App 适合发现兼容性线索，不属于稳定的 API 契约。文档中出现“十分钟后冻结”“某品牌默认禁止全部自启动”或固定排行时，必须给出机型、build、地区、设置状态和复现证据；缺少这些条件就应删除数字。

#### 区分几种容易混淆的现象

| 现象 | 进程与包状态 | 证据 |
| --- | --- | --- |
| Job 等待系统条件 | 进程可能不存在，包可正常启动 | Job pending reason、bucket、Doze、quota |
| OEM/内核冻结 | 进程可能仍在，但线程长时间不获调度 | vendor（厂商）日志、cgroup/freezer（控制组冻结）状态、sched trace（调度跟踪）；接口随设备变化 |
| 低内存回收 | 进程消失，系统有内存压力 | `ApplicationExitInfo`、lmkd/LMKD（低内存终止守护进程）日志、PSI（Pressure Stall Information，压力停顿信息）与内存 trace |
| force-stop（强制停止）/用户停止 | 包进入 stopped（已停止）状态，后台触发被阻断 | package/activity 状态、用户操作时间、重新点击图标后的恢复 |
| Hibernation | 长期未用，权限和后台任务被重置 | unused-app（未使用应用）设置、权限、Job/Alarm 与 push 状态 |
| Archiving | APK 被移除，用户数据保留 | Launcher/PackageInstaller 的 archive metadata（归档元数据）与 installer 状态 |

只凭 Perfetto 里“线程没有 runnable slice（处于可运行状态的时间段）”无法证明 OEM 冻结。线程可能正在 epoll（I/O 事件等待机制）中等待，Job 也可能尚未分发。判断冻结需要 ROM 侧状态或 vendor 日志支撑。

#### 兼容性测试方法

- 为每个目标机型记录 `ro.build.fingerprint`（系统构建标识）、地区、系统更新版本和电池设置。
- 同一 App 包与账号分别测试屏幕关闭、重启、充电、低电量、网络切换和多日不互动。
- 保存 `dumpsys jobscheduler`、`deviceidle`、`alarm`、`activity processes`、bucket、AppOps（应用操作与权限状态）与设置页截图。
- 读取 `ApplicationExitInfo`，区分 low memory（低内存）、crash（崩溃）、ANR（应用无响应）、user requested（用户请求）和其他退出原因。
- 推送测试记录服务端发送时间、设备到达时间、通知展示与用户交互，不能只记录“收到/未收到”。
- 只有核心功能确受限制时才向用户解释设置入口；设置页面名称按设备动态展示，避免写成跨 ROM 固定路径。

删除系统包、禁用电源管理服务或要求所有用户打开“无限制”都不适合作为产品修复。前两项会改变系统安全与兼容性，后一项会增加用户电量成本。

### 统一诊断：按控制器收集证据

| 需要回答的问题 | Framework 入口 | 调试入口 |
| --- | --- | --- |
| 设备是否在 Light/Deep Doze | `DeviceIdleController` | `dumpsys deviceidle` |
| App 属于哪个 bucket | `AppStandbyController`、`UsageStatsService` | `am get-standby-bucket`、`dumpsys usagestats appstandby` |
| Job 为什么等待 | `JobSchedulerService`、controllers（各约束控制器） | `dumpsys jobscheduler`、pending reason APIs |
| Battery Saver 是否生效 | `PowerManagerService`、`BatterySaverController` | `dumpsys power`、`settings get global low_power` |
| Low Power Standby 是否限制网络/WakeLock | `LowPowerStandbyController` | `dumpsys power`、PowerManager API |
| 后台界面为何被拒绝 | ActivityTaskManager BAL controller、`ActivityOptions` | ActivityTaskManager 日志、调用链与 opt-in mode |
| 是否进入 kernel suspend | SystemSuspend、kernel PM（内核电源管理） | Perfetto/ftrace `power/suspend_resume`、wakeup sources、CPU idle |

Perfetto 配置至少考虑 `sched/*`、`power/suspend_resume`、`power/cpu_idle`、`power/cpu_frequency`，再按问题加入 Binder、network 和 Framework `power`/`am` category（类别）。轨道名称和可用数据受 build 与厂商影响，`dumpsys` 快照与 trace 必须对应同一测试窗口。

### 复核清单

- 是否把 Doze 状态与 kernel suspend 证据分开？
- 是否同时检查 Light Doze、Deep Doze 和维护窗口？
- FGS 是否被错误地当成 Doze、Job quota 或 Low Power Standby 豁免？
- bucket 配额是否注明“近似指导值”，并记录充电与进程状态？
- Android 16+ 是否验证 top-started（从最前台状态启动）与 FGS 并发 Job 的 quota？
- Android 17 是否使用 pending reason stats 解释等待时间？
- Adaptive Battery 描述是否停留在公开契约，没有猜测模型结构？
- BAL 调用链是否按 sender、creator、IntentSender 与 targetSdk 分别检查？
- 后台位置是否同时满足权限、可见性、FGS type 和启动条件？
- Hibernation 与 Archiving 是否按权限、APK、数据和恢复语义区分？
- Battery Saver、Low Power Standby、Data Saver 与 Doze 是否分别取证？
- OEM 结论是否附机型、build、地区、设置和 trace/log？
- 测试结束后是否恢复 battery、deviceidle 与 AppOps 状态？

### 与其他章节的关系

§5.1–§5.2 解释 cpuidle（CPU 空闲管理）、cpufreq（CPU 频率管理）、EAS（Energy Aware Scheduling，能量感知调度）与 suspend 的基础，§11.1 说明能量归因，§11.2 讨论 App 如何减少 WakeLock、Job、位置和网络开销。本节说明二者之间的关系：Framework 策略决定任务何时获得资源，内核与硬件决定设备能进入多深的低功耗状态。进程被回收时还要结合 §1.1，避免把 LMKD 与功耗限制混为一类。

### 版本与实现边界

| 版本 | 系统级功耗与后台行为变化 |
| --- | --- |
| Android 6.0 / API 23 | Doze、App Standby、battery optimization exemption |
| Android 7.0 / API 24 | Light Doze；屏幕关闭且移动时也能应用较轻限制 |
| Android 8.0 / API 26 | 后台 Service、后台位置与隐式广播限制 |
| Android 9 / API 28 | App Standby Buckets、Adaptive Battery；定位节电 mode API |
| Android 10 / API 29 | BAL 限制、`ACCESS_BACKGROUND_LOCATION`、可选 Routine Battery Saver |
| Android 11 / API 30 | 未使用 App 权限自动重置；后台位置改为通过系统设置授予 |
| Android 12 / API 31 | Restricted bucket、App hibernation 完整效果、精确闹钟 special access |
| Android 13 / API 33 | Restricted 无互动阈值改为 8 天；Low Power Standby 公开 API；高优先级 FCM quota 与 bucket 脱离 |
| Android 14 / API 34 | PendingIntent 发送方 BAL opt-in；FGS type 与权限校验；Job pending reason API |
| Android 15 / API 35 | PendingIntent 创建方 BAL opt-in；OS 级 App Archiving；部分 FGS type 时长限制 |
| Android 16 / API 36 | Active bucket、top-started 和 FGS 并发 Job 受 runtime quota；多原因与历史 pending API |
| Android 17 / API 37 | `getPendingJobReasonStats()`；listener 型 exact allow-while-idle Alarm；`IntentSender.sendIntent()` BAL opt-in |

## 常见误区

### “设置页百分比就是应用的精确电量”

设置页使用归因结果，包含 measured energy、profile、controller activity 和共享资源分配。它适合发现异常与比较排序，不适合作为实验室绝对测量。

### “Coulomb Counter 能测出每个应用”

Coulomb Counter 面向整块电池。UID 结果来自 Framework 归因；两者可以校对总趋势，不能互相替代。

### “CPU 使用率相同，耗电就相同”

CPU policy、频点、idle 进入、迁核、内存访问、WakeLock 和 thermal 状态都会改变能量。CPU time 只是归因输入之一。

### “GPU rail 就是某个游戏的 GPU 电量”

rail 是设备级计量点，可能包含共享电源域。应用 trace 可以帮助时间关联，但不能自动排除系统 compositor（画面合成器）、其他进程和共享模块。

### “PowerMonitor delta 就是电池掉电”

PowerMonitor 可能返回 rail measurement（直接测量值）或 modeled consumer（模型估算的逻辑组件），累计值还包含插电期间。电池 charge、rail energy 与 BatteryUsageStats mAh 的范围不同。

## 参考资料

- [AOSP Power Profiles](https://source.android.com/docs/core/power)
- [AOSP Power Values](https://source.android.com/docs/core/power/values)
- [Android Studio Power Profiler 与 ODPM](https://developer.android.com/studio/profile/power-profiler)
- [SystemHealthManager](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [PowerMonitor](https://developer.android.com/reference/android/os/PowerMonitor)
- [PowerMonitorReadings](https://developer.android.com/reference/android/os/PowerMonitorReadings)
- [Perfetto traced_probes：android.power](https://perfetto.dev/docs/reference/traced_probes)
- [Battery Historian](https://github.com/google/battery-historian)

### 官方与 API 文档

- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details)
- [Test power-related issues](https://developer.android.com/topic/performance/power/test-power)
- [AOSP：Platform power management with Doze](https://source.android.com/docs/core/power/platform_mgmt)
- [AOSP：Power management](https://source.android.com/docs/core/power/mgmt)
- [AOSP：App background behavior trackers](https://source.android.com/docs/core/power/trackers)
- [AOSP：Routine Battery Saver](https://source.android.com/docs/core/power/routine-battery-saver)
- [PowerManager API](https://developer.android.com/reference/android/os/PowerManager)
- [JobScheduler API](https://developer.android.com/reference/android/app/job/JobScheduler)
- [AlarmManager API](https://developer.android.com/reference/android/app/AlarmManager)
- [Android 17 features and APIs](https://developer.android.com/about/versions/17/features)
- [Secure background activity launches](https://developer.android.com/guide/components/activities/secure-bal)
- [Background FGS start restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Background location](https://developer.android.com/develop/sensors-and-location/location/background)
- [Background execution limits](https://developer.android.com/about/versions/oreo/background)
- [App hibernation](https://developer.android.com/topic/performance/app-hibernation)
- [Android 15 App archiving](https://developer.android.com/about/versions/15/features#app-archiving)

#### Android 17 源码锚点

- [DeviceIdleController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java)
- [AppStandbyController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java)
- [JobSchedulerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java)
- [QuotaController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java)
- [JobScheduler.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/apex/jobscheduler/framework/java/android/app/job/JobScheduler.java)
- [PowerManagerService.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java)
- [LowPowerStandbyController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/LowPowerStandbyController.java)
- [BatterySaverController.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverController.java)
- [BatterySaverPolicy.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/power/batterysaver/BatterySaverPolicy.java)
- [ActivityOptions.java](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/app/ActivityOptions.java)

#### Android 17 Kernel 锚点

- [kernel/power/suspend.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/kernel/power/suspend.c)
- [kernel/sched/idle.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/kernel/sched/idle.c)
- [drivers/base/power/wakeup.c](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c)

#### OEM 行为线索

- [Don't Kill My App](https://dontkillmyapp.com/)：社区维护的设备行为记录，只用于兼容性线索，结论需在目标 build 复测
