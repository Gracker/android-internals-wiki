---
title: "Android 17 Power Stats HAL 的 OEM 实现差异"
chapter: "17.9"
section: "17.9"
status: finalized
applicable_versions: "Android 17 (API 37)"
tags: [Android17, PowerStats, HAL, 功耗, OEM]
related_chapters: ["5.4", "11.1", "14.8", "17.8"]
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_draft_polish_at: "2026-08-05T11:35:04+08:00"
last_draft_polish_run_id: "20260805-113504-draft-polish-f93bb337"
last_review_finalize_at: "2026-08-05T12:08:38+08:00"
last_review_finalize_run_id: "20260805-120725-a2b4bf2b"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1: frozen PowerStats AIDL v2, HIDL 1.0 fallback, default fake HAL, PowerStatsService/Logger/Trigger/StatsD paths, public Power Monitor API and fine-monitor permission"
confidence: medium-high
sources:
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
    url: "https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/default/"
    url: "https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/default/main.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/"
  - type: research-note
    path: "DeepResearch/2026-07-08-android17-powerstats-hal-oem-implementation.md"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/Android.bp (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/Android.bp"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsHALWrapper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsLogger.java (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsLogger.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/TimerTrigger.java (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/TimerTrigger.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/BatteryTrigger.java (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/BatteryTrigger.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java"
  - type: aosp
    path: "frameworks/base/core/res/AndroidManifest.xml ACCESS_FINE_POWER_MONITORS (android-17.0.0_r1)"
    url: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/res/AndroidManifest.xml"
  - type: official-doc
    path: "SystemHealthManager API"
    url: "https://developer.android.com/reference/android/os/health/SystemHealthManager"
  - type: official-doc
    path: "AOSP Power stats HAL"
    url: "https://source.android.com/docs/core/power/power-stats-hal"
---

# Android 17 Power Stats HAL 的 OEM 实现差异

Android 17 的 PowerStats 链路用三类对象描述设备数据。`PowerEntity` 是子系统、外设或电源域，报告各状态的累计驻留时间；`EnergyConsumer` 报告组件累计能量，并可选择附带按 UID（应用身份）分摊的结果；`Channel` 是能量计量通道，常对应一条电源 rail（供电支路）。OEM 指设备厂商。

AOSP 定义稳定的 HAL（Hardware Abstraction Layer，硬件抽象层）接口、Framework 系统服务和数据使用路径。设备能提供多少 rail、是否包含 UID 分摊、计数器是否可靠，仍取决于厂商实现。本文按 `android-17.0.0_r1` 核对；Pixel、高通、MediaTek、三星等闭源或受限仓库的细节不作源码级断言。

## 标准架构与厂商差异

### PowerStats HAL 标准架构

Android 17 冻结的 `android.hardware.power.stats` AIDL 是 v2。AIDL（Android Interface Definition Language）描述进程间接口；`IPowerStats.aidl` 定义以下 6 个方法：

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

能量字段的单位是微瓦秒（µW·s，数值上等于微焦耳），AIDL 时间戳使用从开机起计时且包含休眠时间的 `CLOCK_BOOTTIME`。ID 数组为空时表示请求全部可用对象；某个对象暂时没有结果时，HAL 可以不返回该项。接口只约定对象和数据格式，不保证设备覆盖某个组件，也不保证提供 UID 分摊。

### AOSP 默认实现不是真实设备基线

AOSP 默认实现位于 `hardware/interfaces/power/stats/aidl/default/`。`main.cpp` 注册 3 条虚构 rail、2 个虚构状态提供者和 2 个虚构 EnergyConsumer，供接口联调与 VINTF（Vendor Interface，系统和厂商组件之间的兼容契约）验证。这类 fake 数据只用于测试，不能当作真实设备基线。

这也是 OEM 差异的根源：

- 厂商只接入少量 rail 时，系统服务诊断命令 `dumpsys powerstats` 仍会列出对象，但覆盖范围有限。
- 厂商没有提供 `EnergyConsumerAttribution[]` 时，PowerStats 数据不能给出该组件的 UID 分摊。
- 计数器复位、时间戳错误或单位换算错误，会让上层工具读到格式正确但无法比较的数据。

### Framework 有三条数据使用路径

`PowerStatsHALWrapper` 优先连接稳定 AIDL v2；连接不到时会尝试旧版 HIDL 1.0。HIDL（HAL Interface Definition Language）1.0 能提供 rail 与状态驻留，Framework 的兼容封装会把 EnergyConsumer 信息和结果返回为空数组。设备有 PowerStats 服务，不代表三组数据都可用。

下面列出主要类名，便于在源码中定位。箭头表示组件关系；含有存储、PowerMonitor 和 `dumpsys` 的那一行列出不同使用入口，它们不会按文字顺序互相调用。

```text
vendor PowerStats HAL
  → PowerStatsHALWrapper
  → PowerStatsService
  → PowerStatsLogger
  → PowerStatsDataStorage / PowerMonitor / dumpsys
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

### 用四个维度判断设备能力

评估一台 Android 17 设备时，“服务存在”只说明接口可以连接，还要检查以下四项：

| 维度 | 需要确认的问题 | 对工具结果的影响 |
|---|---|---|
| 对象覆盖 | Channel、EnergyConsumer、PowerEntity 是否覆盖 CPU、显示、蜂窝网络、Wi-Fi、GNSS 等关键组件 | 决定能分析哪些子系统，缺失对象不能靠上层补出 |
| 采集方式 | 数据来自片上电源监视器、PMIC（电源管理芯片）、内核计数器或软件模型 | 决定数值是直接测量、状态统计还是估算 |
| UID 分摊 | 是否提供 `EnergyConsumerAttribution[]`，分摊总和与 UID 映射是否有效 | 决定能否在对应组件内分析应用归因 |
| 计数器与时钟 | 累计值是否单调、重启后是否复位，`timestampMs` 与 `durationMs` 是否符合字段定义 | 决定窗口差值是否可用，以及多路数据能否对齐 |

同一厂商的不同 SoC、内核、PMIC 和整机配置可能提供不同对象。报告设备能力时，应记录这四项证据，不能只写厂商品牌。

### Power Monitor 的缓存、权限与随机扰动

公开 Power Monitor API 从 API 35 开始提供。`getSupportedPowerMonitors()` 异步返回两类对象：直接测得的 `POWER_MONITOR_TYPE_MEASUREMENT` 与直接测量或模型计算的 `POWER_MONITOR_TYPE_CONSUMER`。空列表是合法结果。PowerMonitor 的 index 在重启后不保证稳定，应用只能使用本次查询返回的对象，不能把 index 持久化。

`ACCESS_FINE_POWER_MONITORS` 是 `signature|privileged|development` 级别权限，普通第三方应用通常无法获得。Android 17 的服务为两类调用方维护独立缓存：

- 无该权限时，缓存最长复用 20 秒，结果标为 `GRANULARITY_UNSPECIFIED`；
- 有该权限时，缓存最长复用 250 毫秒，结果标为 `GRANULARITY_FINE`。

这两个阈值决定服务何时重新请求 HAL，不代表硬件传感器按同样周期采样。服务还会在前后两次累计值之间加入按调用 UID 保持一段时间的随机扰动，两类权限路径都会经过该处理。公开结果以 µW·s 报告自开机以来的累计能量，包含电池供电与外接电源期间的能量，重启后不会延续。该 API 不返回 `EnergyConsumerAttribution[]`。

这里的 granularity 指结果新鲜度等级。排查 Power Monitor 读数时，应同时确认设备功能开关、对象列表、结果时间戳、累计值是否增长、调用方权限和返回的 granularity。20 秒或 250 毫秒的缓存规则不能替代 HAL 计数器本身的采样说明。

## 能力分级与部署

### 按能力描述 OEM 实现

闭源实现无法从 AOSP 主线核对时，可以按观测到的能力给设备分级。L0–L4 是本文使用的验收约定，不是 Android 官方等级：

| 能力等级 | 典型表现 | 适合的分析场景 |
|---|---|---|
| L0：没有可用数据 | HAL 未初始化、对象为空，或设备部署了默认 fake 数据 | 只能验证接口或故障处理 |
| L1：计量通道可用 | 能读取部分 `Channel` / `EnergyMeasurement` | 可观察同一设备上的供电支路趋势，覆盖范围有限 |
| L2：组件能量可用 | 多个 `EnergyConsumer` 覆盖关键硬件 | 可分析设备定义的 CPU、显示、蜂窝网络等组件 |
| L3：UID 分摊可用 | 部分 EnergyConsumer 稳定返回合法的 `EnergyConsumerAttribution[]` | 可在对应组件和采样窗口内分析 UID 分摊 |
| L4：测量链已验证 | 累计值、时间戳、单位和覆盖范围经过外部仪器与重复实验核对 | 可支持目标机型上的定量实验，报告仍需写明测量边界 |

能力等级描述的是一台设备上的一版软件，不能自动推广到同品牌的其他机型或 OTA 版本。

### 跨厂商比较先统一口径

跨厂商比较前，要统一对象映射、计算方式和时间窗口：

1. **保存对象清单**：记录 `getPowerEntityInfo()`、`getEnergyConsumerInfo()` 和 `getEnergyMeterInfo()` 的完整返回值。设备自定义名称对 Framework 是不透明字符串，同名对象也未必测量同一范围。
2. **使用累计值差分**：一次任务的能量取结束累计值减去开始累计值。若计数器下降，要先排除重启、HAL 复位、回绕或对象映射变化，不能把负差值当成耗能结果。
3. **区分两种时间戳**：原始 HAL 结果使用 `CLOCK_BOOTTIME`；Logger 的落盘数据转换为 Unix 时间。混合两条路径时要先转换到同一时间轴。
4. **对齐实验窗口**：保持工作负载、屏幕状态、电量区间、温度和网络条件一致。平均功率可用能量差除以同一窗口的时长计算。
5. **单独标注 UID 分摊**：组件总能量与 UID 分摊的证据强度不同。分摊缺失，只能说明 HAL 没有返回这项数据，不能推出某个应用没有耗电。
6. **用外部仪器校验**：片上 rail 可能漏掉屏幕、射频或 PMIC 转换损耗。跨设备总能量结论应同时给出外部功耗仪或电池侧测量的校验结果。
7. **记录来源**：报告中写明机型、软件构建指纹、内核版本、HAL 路径、对象清单、采样时长、权限与 Power Monitor granularity。

不同设备的对象无法一一对应时，可以比较各自覆盖范围内的趋势，但不应拼成一个统一的绝对总量。

### 企业设备与实验室设备池

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
- 明确 Framework 连接的是 AIDL v2 还是 HIDL 1.0，后者不会提供 EnergyConsumer；
- 在亮屏、灭屏、视频、网络和定位等场景中，比较前后两次 meter/model 累计值是否合理增长；
- `EnergyConsumerResult` 是否带 UID 分摊，分摊总和是否不超过组件总能量；
- 重启或 OTA 后重新采集对象 ID、名称与类型，不能沿用旧映射；
- 导出的 protobuf 是否能由与当前 schema（字段结构定义）匹配的内部工具解析；
- 外部功耗仪与片上计数器的能量差是否在预先设定的误差范围内。

监控平台应把设备能力等级、HAL 路径、对象清单版本和测量边界保存为元数据。混合 L1 与 L3 设备生成同一张应用耗电榜，会把“没有 UID 数据”误当成“应用耗电较低”。

## 实战排查：为什么不同手机的功耗榜差异很大？

同一个 APK 在两台 Android 17 设备上出现不同耗电归因时，可以按以下顺序排查：

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

模板中的 `model/build/kernel` 分别指机型、软件构建指纹和内核版本。`legacy` 只是原模板对“没有细粒度权限”的简称，不是 Framework 的正式路径名；正式报告宜写 `GRANULARITY_UNSPECIFIED` 或 `GRANULARITY_FINE`。

## 版本边界

- 本文固定在 `android-17.0.0_r1` / Android 17（API 37）。该标签冻结 PowerStats AIDL v2，同时保留 HIDL 1.0 回退。
- Pixel、高通、MediaTek、三星等厂商 HAL 的闭源细节没有纳入确定性结论。
- `StatsPullAtomCallbackImpl` 已核对：它向 StatsD 注册片上功耗测量与子系统休眠状态两类拉取项。
- AOSP 官方文档把 StatsD、Perfetto 与 Batterystats 列为 PowerStats 客户端，但这不等于 Battery Historian 会直接解析 `dumpsys powerstats --proto` 的三类文件。内部工具需要单独验证输入 schema 与消费路径。
- 公开 Power Monitor 从 API 35 开始提供，只公开 Channel/EnergyConsumer 累计值，不公开 PowerEntity 状态驻留或 EnergyConsumer 的 UID 分摊数组。

## 参考资料

### Android 17 / AOSP 源码

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

### 官方文档

- [`SystemHealthManager` API](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [AOSP：Power stats HAL](https://source.android.com/docs/core/power/power-stats-hal)
