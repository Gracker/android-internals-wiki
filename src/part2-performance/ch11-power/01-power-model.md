---
title: "Android 功耗模型"
chapter: "11.1"
section: "11.1"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [['power', 'battery', 'power_profile', 'BatteryStats', 'ODPM', 'Coulomb Counter', 'Fuel Gauge', 'IPowerStats', '功耗归属']]
confidence: medium
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1 / Android common kernel android17-6.18-2026-06_r6 / PowerAttributor and PowerStatsProcessor pipeline"
note: "Android 17+ 屏幕功耗归因处理器"
sources:
  - type: aosp
    path: "frameworks/base/core/res/res/xml/power_profile.xml"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/PowerAttributor.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/processor/ScreenPowerStatsProcessor.java"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
  - type: kernel
    path: "include/linux/power_supply.h"
  - type: kernel
    path: "drivers/power/supply/power_supply_core.c"
  - type: official
    path: "https://source.android.com/docs/core/power"
  - type: official
    path: "https://source.android.com/docs/core/power/values"
  - type: official
    path: "https://developer.android.com/studio/profile/power-profiler"
  - type: official
    path: "https://developer.android.com/reference/android/os/health/SystemHealthManager"
  - type: official
    path: "https://perfetto.dev/docs/reference/traced_probes"
related_chapters: "[\"5.4\", \"5.5\", \"5.6\", \"11.2\", \"11.3\", \"13.1\"]"
task2b_state: "fixed"
task6_state: "reviewed"
task9_state: "reviewed"
---

# 11.1 Android 功耗模型

“某应用耗了多少电”看似只有一个数字，平台内部却要完成三件不同的工作：

1. 记录 CPU、屏幕、网络、传感器、WakeLock 等资源活动；
2. 把活动时间或硬件能量读数换算成组件耗电；
3. 把共享组件的成本分配给 UID（Linux 用户标识，Android 用它归集应用资源），再生成 Settings 和 bugreport 使用的结果。

这三层使用的数据源、单位和误差不同。BatteryStats 里的活动时长、PowerStats HAL（硬件抽象层）的能量读数、ODPM rail（设备级电源轨计量）和设置页里的应用百分比不能直接横向比较。

Framework 行为按 Android 17 / API 37 / `android-17.0.0_r1` 核对。内核接口按 `android17-6.18-2026-06_r6` 核对；具体 Fuel Gauge（电量计）、PMIC（电源管理芯片）和 rail（电源轨）名称由设备厂商实现。

## 1. Android 17 功耗统计全景

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

## 2. `power_profile.xml`：软件估算的设备参数

`frameworks/base/core/res/res/xml/power_profile.xml` 描述组件在不同状态下、折算到电池侧的平均电流。官方要求单位为 mA，并按标称电压测量。Framework 将电流与活动时长相乘，得到电荷量：

`charge(mAh) = current(mA) × duration(ms) / 3_600_000`

该文件用于估算电池消耗，不是 PMIC rail 的原始电流表。rail 位于不同电压域时，不能直接把 rail 电流填进 profile，因为相同电流在不同电压下对应的功率不同。

### 2.1 AOSP 文件为何不能当设备参数

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

### 2.2 CPU 参数按 scaling policy 与频点组织

异构 CPU 需要描述 cluster（核簇）的核数、频点和对应活动电流。Android 17 的 `CpuPowerStatsProcessor` 从 `CpuScalingPolicies` 取得 scaling policy（共享调频策略的一组 CPU）与频点，并从 `PowerProfile` 读取三类参数：

- CPU 整体 active 的基础电流；
- scaling policy 活跃的附加电流；
- scaling step，也就是某个具体频点的附加电流。

没有 CPU energy consumer 时，处理器按 uptime（设备处于运行状态的时间）、policy 运行时间和频点时间形成 profile 估算。有 hardware energy（硬件能量读数）时，处理器仍会利用 profile 的 power bracket（合并了相近功耗档位的分组）和 UID 时间，把 energy consumer 的总量按活动比例分配。

因此，相同 CPU time 不保证相同耗电。任务运行在哪个 policy、哪些频点，以及设备是否提供 measured energy，都会改变结果。

### 2.3 modem、Wi-Fi 与 Bluetooth 还有 controller 数据

现代 profile 同时保留 legacy（兼容旧实现）项和 controller 项。Wi-Fi 可提供 idle、rx、不同 tx level（发射功率档位）及工作电压；modem 配置可区分 RAT（无线接入技术）、NR（5G New Radio）频段和发射等级；Bluetooth controller 也可提供 idle、rx、tx 统计。

使用哪组数据取决于芯片、HAL 和 Framework collector（统计采集器）的能力。不能把所有设备简化成“开启时间 × 一个固定 mA”。同一网络制式的发射功率、驻留状态和 tail（传输结束后保持高功耗状态的一段时间）行为也由基带、运营商与设备策略决定。

## 3. 组件功耗如何进入归因

### 3.1 CPU

Android 17 不再使用顶层 `CpuPowerCalculator`。入口变为：

`BatteryUsageStatsProvider → PowerAttributor → MultiStatePowerAttributor → CpuPowerStatsProcessor`

`CpuPowerStatsProcessor` 会按设备状态、屏幕状态和 UID 进程状态聚合 CPU 统计。缺少 measured energy（实测能量）时使用 profile；存在 CPU cluster energy consumer 时，以硬件能量校正各 power bracket，再按 UID 在 bracket 中的活动比例分配。

这里的“硬件能量优先”不表示 HAL 能直接识别每条应用线程。HAL 提供组件或 cluster 总量，UID 归属仍依赖 CPU 活动统计。

### 3.2 Display

`ScreenPowerStatsProcessor` 先计算设备级屏幕耗电：

- 有 screen energy consumer 时，使用累计能量；
- 没有时，使用 screen-on、doze（低功耗显示状态）、亮度档位时长与 profile。

UID 分配阶段按 top activity duration（应用处于最前台的 Activity 时长）占比分配亮屏耗电。Android 17 处理器在总 top activity duration 为 0 时跳过 UID 分配，不再保留 Android 16 `ScreenPowerCalculator` 中 10 分钟的 smear（按时长摊分）门槛。

硬件 screen energy consumer 仍然是设备级输入。它提高屏幕总量的测量质量，不能自动得到每个应用的屏幕电量；UID 结果依旧来自前台活动时长比例。

### 3.3 GPU

Android 17 的标准 `BatteryConsumer.POWER_COMPONENT_*` 集合没有 GPU，`EnergyConsumerType.aidl` 也没有 GPU 专用枚举。GPU rail 可通过下列入口观察：

- Pixel 6 及后续 Pixel 的 ODPM / Power Profiler；
- 厂商 PowerMonitor measurement 或 consumer；
- Perfetto 中设备提供的 GPU rail；
- GPU frequency、busy 和调度 trace，用作负载代理指标；它们描述活跃程度，不直接等于能量。

`PowerMonitor` consumer 名称可以出现 GPU，但名称和组合方式允许 OEM 自定义。它与 `BatteryConsumer` 是否有标准 GPU 组件是两个 API 层面。

### 3.4 Cellular、Wi-Fi 与 Bluetooth

通信组件可能组合使用：

- controller activity：idle、rx、tx 及发射等级时长；
- network bytes、packets、scan 和连接状态；
- PowerStats energy consumer；
- `power_profile.xml` 回退参数。

共享 controller 或共享 rail 需要二次分配。网络字节多不一定代表 radio（无线通信模块）耗电高，短而分散的传输还可能增加唤醒和高功耗状态驻留时间。诊断时应同时观察传输窗口、网络状态、controller activity 与 rail。

### 3.5 GNSS、Camera、Audio、Video 与 Sensor

这些组件也存在多种路径：

| 组件 | 活动证据 | 能量输入 | UID 归属注意点 |
|---|---|---|---|
| GNSS | 请求者、signal quality（信号质量）、活跃时间 | energy consumer 或 profile | 多个请求者可能共享一次定位 |
| Camera | Camera 使用状态与时长 | CAMERA energy consumer 或 `camera.avg` | rail 可能包含 ISP（图像信号处理器）、传感器或共享域 |
| Audio / Video | 播放、编码、解码时间 | profile、DSP（数字信号处理器）/controller/vendor monitor | offload（交给专用硬件处理）与非 offload 路径不同 |
| Bluetooth | scan、controller rx/tx/idle | controller activity、energy consumer、profile | BLE、经典连接和音频链路不能混为一类 |
| Sensor | 注册 UID 与活跃时间 | sensor power 参数或 vendor 数据 | batching（批量上报）会改变唤醒成本 |

profile 数字反映特定设备测量条件。Camera、GPS 或 Bluetooth 没有跨设备通用电流值。

## 4. BatteryStats：活动记账层

`BatteryStatsService` 运行在 `system_server`，主要状态由 `BatteryStatsImpl` 维护。它负责记录活动与归属线索，并不会持续读取整机电流。

### 4.1 Push 与 Pull

控制组件状态的系统服务会在状态变化时推送事件，例如屏幕、Wi-Fi、定位和 WakeLock（阻止设备进入部分休眠状态的锁）。CPU 等累计统计则在状态切换或采样点拉取快照。Android 官方将两者称为 push（推送）和 pull（拉取）。

一次 UID 归因可能依赖多种线索：

- CPU active、policy、频点和 UID 时间；
- 前台、后台、top（最前台）等进程状态；
- WakeLock、Job、Sync、FGS（前台服务）与传感器时长；
- 网络字节、controller activity 和 radio 状态；
- EnergyConsumer 累计值；
- BatteryStats history 中的状态变化。

`BatteryStatsImpl` 记录的是 UID 级统计，UID 不总是单个进程。共享 UID、多进程应用、系统 UID 和 SDK sandbox（SDK 沙箱进程）等场景都要先确认身份边界。

### 4.2 时间窗口与持久化

BatteryStats 会持久化统计，跨重启保留需要的历史信息。`/data/system/batterystats.bin` 是当前实现中的存储文件，不属于应用可依赖的公开接口。

拔掉充电器不会无条件重置所有统计。Android 17 的 `shouldResetOnUnplugLocked()` 根据满电、高电量、一次明显充电和 session（统计会话）时长等条件决定是否 reset；高电量阈值由 `BatteryStatsConfig.getHighBatteryLevelAfterCharge()` 提供，默认值为 90，OEM 可以配置。

实验前执行 `dumpsys batterystats --reset` 是人为建立采集窗口，和系统自动 reset 的策略不同。重置会影响整机统计，不应在用户设备或多人共享测试环境随意执行。

### 4.3 `dumpsys batterystats` 能回答什么

在专用测试机上，可以用下面的命令建立一个明确窗口并导出结果。

```bash
adb shell dumpsys batterystats --reset

# 运行受控测试场景后导出
adb shell dumpsys batterystats > batterystats.txt
adb bugreport bugreport.zip
```

`dumpsys` 适合核对 UID 活动、WakeLock、网络、Job 和组件统计；bugreport 可交给 Battery Historian（将 BatteryStats 历史数据可视化的工具）。命令结果是统计与归因证据，不是外接功耗仪的瞬时电流曲线。

## 5. Coulomb Counter、Fuel Gauge 与 Framework 归因

### 5.1 Coulomb Counter

Coulomb Counter 对电池充放电电流做时间积分，得到 charge（电荷量）变化。Android 设备常通过 Fuel Gauge 和 Health HAL 暴露剩余 charge、current、capacity 等属性。`BatteryManager` 中常见单位包括：

- `BATTERY_PROPERTY_CHARGE_COUNTER`：µAh；
- `BATTERY_PROPERTY_CURRENT_NOW`：µA；
- `BATTERY_PROPERTY_CAPACITY`：百分比；
- `BATTERY_PROPERTY_ENERGY_COUNTER`：nWh，设备支持情况不同。

属性缺失、符号方向和采样行为由设备实现决定。任何精度结论都要依据目标 Fuel Gauge 数据手册和整机验证，不能给 Coulomb Counter 设一个通用误差范围。

### 5.2 Fuel Gauge

Fuel Gauge 通常结合 Coulomb counting（库仑计量）、电压、温度、电池模型和校准状态估计 State of Charge（SOC，剩余电量比例）。部分实现还提供 State of Health（SOH，电池健康状态）。它面对的是整块电池，不能识别某次电流由哪个 UID 引起。

`android17-6.18-2026-06_r6` 中，`include/linux/power_supply.h` 和 `drivers/power/supply/power_supply_core.c` 定义了通用 power_supply 框架。具体 Gauge 驱动、属性集合和校准算法位于厂商实现；Android common kernel 只能作为接口锚点。

### 5.3 两类结果不能互相替代

| 问题 | 合适数据 |
|---|---|
| 电池在测试窗口少了多少 charge（电荷量） | Fuel Gauge / 外接功耗仪 |
| 某个 rail 在窗口内增加了多少 energy（能量） | ODPM / PowerMonitor measurement |
| 哪个组件最活跃 | BatteryStats、Perfetto 状态和 controller 数据 |
| 哪个 UID 被归因了多少 mAh | BatteryUsageStats / UidBatteryConsumer |
| 某代码改动是否降低整机平均功率 | 外接仪表或稳定 rail delta，加受控 A/B |

Framework 不会简单地把 Coulomb Counter 总差值按应用比例切分。BatteryUsageStats 的组件算法可能使用 measured energy、controller 数据或 profile，再依据 UID 活动分配。电池总差值还包含系统、屏幕、基带、供电转换损耗和未归因部分。

## 6. Android 17 归因管线

### 6.1 从 history 到 `BatteryUsageStats`

Android 17 的主路径为：

| 阶段 | 对象 | 作用 |
|---|---|---|
| 记录 | `BatteryStatsImpl` / `BatteryStatsHistory` | 保存状态变化、计数和能量输入 |
| 配置 | `AggregatedPowerStatsConfig` | 定义设备、屏幕、进程等聚合维度 |
| 聚合 | `MultiStatePowerAttributor` | 读取 history（状态变化历史），按时间与状态组织组件统计 |
| 计算 | `processor/*PowerStatsProcessor` | 计算设备组件和 UID 的 mAh |
| 输出 | `BatteryUsageStats.Builder` | 生成设备与 UID consumer |

`PowerAttributor` 是接口，Android 17 默认实现使用 `MultiStatePowerAttributor`。不同 processor 的算法各自决定 measured energy、profile 和活动时长的组合方式，因此不能写出一条覆盖所有组件的统一分摊公式。

### 6.2 Android 16 到 17 的边界

Android 16 是迁移阶段：`BatteryUsageStatsProvider` 对已支持的组件调用 `PowerAttributor`，其余组件保留 `*PowerCalculator`。`android-17.0.0_r1` 的 provider 已移除这组顶层 calculator 回退，委托 `PowerAttributor` 生成组件结果。

阅读 Android 17 源码时，应从 `PowerAttributor`、`MultiStatePowerAttributor` 和 `processor/` 目录进入。使用 Android 16 或更早 tag 讨论历史行为时，仍需查看 `CpuPowerCalculator`、`ScreenPowerCalculator` 等旧实现。

### 6.3 设置页百分比的边界

Settings 使用的是 Framework 归因结果，不是 HAL 原始 rail 表。应用百分比受以下因素影响：

- 查询窗口与 BatteryStats reset 边界；
- measured energy 是否可用；
- profile 与 controller 参数质量；
- UID 前后台状态；
- 共享资源分配；
- 系统组件、未归因量和 reattribution（重新归因）；
- Settings 自身的分组和展示策略。

这个百分比适合排序和寻找异常组件。它不具备实验室仪表的绝对精度，所有 UID 百分比相加也不一定覆盖电池端观测到的全部消耗。

## 7. PowerStats HAL、ODPM 与 PowerMonitor

### 7.1 HIDL 与 AIDL 版本边界

Android 10、Android 11 的历史实现使用 HIDL（旧一代 HAL 接口定义语言）`android.hardware.power.stats@1.0::IPowerStats`：

- `getRailInfo()` 返回 rail 描述；
- `getEnergyData()` 返回累计能量；
- `EnergyData.energy` 使用 µWs。

Android 12 起的 AIDL（Android 接口定义语言）`android.hardware.power.stats.IPowerStats` 分为两组：

- `getEnergyConsumerInfo()` / `getEnergyConsumed()` 返回逻辑 consumer 与 `EnergyConsumerResult.energyUWs`；
- `getEnergyMeterInfo()` / `readEnergyMeter()` 返回 Channel 与 `EnergyMeasurement.energyUWs`。

AIDL consumer 可以附带 UID attribution（UID 归因），但供应商是否提供、如何划分均由硬件与 HAL 决定。Channel 更接近物理或逻辑 meter（计量通道），名称不具备跨设备稳定性。

### 7.2 ODPM 与 Pixel

Android Studio 官方 Power Profiler 文档说明，ODPM（On-Device Power Monitor，设备内功耗监测）rail 目前面向 Pixel 6 及后续 Pixel 设备。可见 rail 随设备变化，常见类别包括 CPU cluster、GPU、memory、display、camera、cellular、WLAN 和 UFS。

ODPM 测量设备级 rail。测试期间其他应用、系统服务、亮度和网络活动都会进入读数。rail 的名称、边界与采样行为也由设备实现决定，因此报告必须同时记录机型、构建号和 rail 名。

不支持 ODPM 的设备仍可提供 battery gauge、Coulomb counter、BatteryStats 和其他代理指标。缺少 rail 不表示设备没有该模块的耗电。

### 7.3 API 35 `PowerMonitor`

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

## 8. Perfetto、Power Profiler 与 Battery Historian

### 8.1 Perfetto `android.power`

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

### 8.2 工具回答的问题不同

| 工具 | 强项 | 边界 |
|---|---|---|
| Battery Historian | bugreport 中的 BatteryStats 时间线 | 依赖采集窗口和 BatteryStats 数据 |
| `dumpsys batterystats` | UID、WakeLock、Job、网络和组件统计 | 不提供高频电流波形 |
| Perfetto | rail、battery counter、调度、频率和应用 trace 的时间关联 | rail 设备相关；trace 本身有采集成本 |
| Power Profiler | Android Studio 中对比应用操作与 rail | ODPM 设备范围与 rail 可用性有限 |
| 外接功耗仪 | 受控场景的整机电流和能量 | 无法自动分配到 UID 或组件 |
| PowerMonitor API | 应用内读取累计 monitor 能量 | 设备支持、名称、范围与更新节奏不同 |

工具选择取决于问题。整机 A/B 更适合外接仪表；模块变化适合 rail；UID 耗电归属适合 BatteryUsageStats；代码和电源事件的时间关系适合 Perfetto。

## 9. 如何做可信的功耗实验

### 9.1 先确定测量对象

实验开始前写清楚目标：

- 整机电池 charge；
- 某条 rail 的 energy；
- 某个组件的 BatteryUsageStats mAh；
- 某 UID 的归因结果；
- 用户任务完成所需的总能量。

测量对象不同，结论不能互换。降低 UID 归因值未必降低整机能量，rail 降低也可能被其他 rail 抵消。

### 9.2 控制实验条件

- 固定设备、系统构建、应用版本和数据集；
- 记录亮度、刷新率、网络、信号、音量、温度和充电状态；
- 让对比组从一致的 thermal（温控）、缓存、登录和电池状态开始；
- 采用多轮、交错顺序，报告离散程度；
- 用时间戳对齐应用 trace、服务端日志、rail 和 battery counter；
- 对 idle baseline（空闲基线）单独采样，避免把系统后台活动归给应用；
- 记录失败、重试、未完成任务和输出质量。

短测试中，电池百分比粒度通常过粗。可以使用 charge counter、rail delta 或外接仪表，但仍要验证读数的更新周期和噪声。

### 9.3 校准的正确含义

校准用于检查 profile 或工具与受控参考测量之间的偏差。一个场景得到的校准系数不能直接用于所有组件、温度和设备。

OEM 制作 `power_profile.xml` 时，应按官方 Power Values 指导在目标硬件上测量组件增量电流。应用团队做回归时，更适合保持工具、设备和条件一致，比较同一指标的差值；不要用一个整机系数修正所有 UID 归因。

## 10. 与内核调度和 ADPF 的边界

Linux EAS（Energy-Aware Scheduling，能耗感知调度）使用 Energy Model 评估任务放在哪个 CPU 上。BatteryStats 使用 `power_profile.xml`、energy consumer 和活动统计计算查询窗口内的耗电。两者都涉及能量模型，但数据结构、时间尺度和用途不同。

在 `android17-6.18-2026-06_r6` 中，EAS 调度路径使用内核 Energy Model 与调度利用率；Android 17 AOSP 没有标准调用链把 ODPM rail 实时写回 EAS cost table（调度成本表）。PowerStats 与 PowerMonitor 用于观测能量，ADPF（Android Dynamic Performance Framework）`PerformanceHintManager` 则由应用提供工作负载提示。

厂商可以在 Power HAL、调度器和固件中实现额外联动。缺少 vendor（厂商）源码和设备 trace 时，只能把这些联动标记为设备特性，不能推广为 Android 17 平台通用机制。

## 11. 版本演进

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

## 12. 常见误判

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

## 13. Android 17 源码阅读入口

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

## 14. 复核检查表

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

## 参考资料

- [AOSP Power Profiles](https://source.android.com/docs/core/power)
- [AOSP Power Values](https://source.android.com/docs/core/power/values)
- [Android Studio Power Profiler 与 ODPM](https://developer.android.com/studio/profile/power-profiler)
- [SystemHealthManager](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [PowerMonitor](https://developer.android.com/reference/android/os/PowerMonitor)
- [PowerMonitorReadings](https://developer.android.com/reference/android/os/PowerMonitorReadings)
- [Perfetto traced_probes：android.power](https://perfetto.dev/docs/reference/traced_probes)
- [Battery Historian](https://github.com/google/battery-historian)
