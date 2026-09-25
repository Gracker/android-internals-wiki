---
title: Battery Historian 与功耗指标集成
chapter: '26.11'
section: '26.11'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
tags:
- Battery Historian
- 性能监控
- 电池
- 指标集成
related_chapters:
- '26.1'
- '26.8'
- '26.5'
last_verified: '2026-08-15'
last_source_verified_at: '2026-08-15'
last_verified_against: Android Developers Battery Historian docs updated 2026-05-19; PowerMonitorReadings and BatteryManager API references updated 2026-08-03; current Power Profiler, Macrobenchmark PowerMetric, WakeLock, and Android vitals docs; AOSP android-17.0.0_r1 power and battery sources; android17-6.18 kernel refs, retrieved 2026-08-15
confidence: high
sources:
- type: legacy-reference-preserved
  path: frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java
- type: legacy-reference-preserved
  path: frameworks/base/services/core/java/com/android/server/powerstats/
- type: official
  path: https://developer.android.com/topic/performance/power/battery-historian
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/TimerTrigger.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/BatteryTrigger.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsLogger.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/PowerAttributor.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java
- type: official
  path: https://developer.android.com/topic/performance/power/setup-battery-historian
- type: official
  path: https://developer.android.com/studio/profile/power-profiler
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics#power-metric
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java
- type: official
  path: https://developer.android.com/reference/android/os/PowerMonitorReadings
- type: official
  path: https://developer.android.com/reference/android/os/health/UidHealthStats
- type: official
  path: https://developer.android.com/reference/android/os/BatteryManager
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/BatteryStatsManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/BatteryUsageStatsQuery.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/AndroidManifest.xml
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/awake/wakelock
- type: official
  path: https://developer.android.com/topic/performance/vitals/excessive-wakelock
- type: aosp
  path: https://android.googlesource.com/kernel/common/+/refs/heads/android17-6.18
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: '2026-08-15T22:11:00+08:00'
last_draft_polish_run_id: 20260815-221100-gracker-writing-478
last_review_finalize_at: '2026-08-15T22:11:00+08:00'
last_review_finalize_run_id: 20260815-221100-gracker-writing-478
last_rework_at: '2026-08-15T22:11:00+08:00'
last_rework_run_id: 20260815-221100-gracker-writing-478
---

# Battery Historian 与功耗指标集成

Battery Historian 是把 bugreport（Android 系统诊断包）中的 Batterystats 等电源记录转换成可交互时间线的离线工具，适合分析一次受控实验。它能帮助回答“电量下降时，屏幕、CPU、Job（系统调度任务）、网络、定位和 WakeLock（请求系统暂时保持硬件工作的唤醒锁）处于什么状态”，却不能直接证明某个事件消耗了多少能量。

Android 官方已经标注 Battery Historian [不再积极维护](https://developer.android.com/topic/performance/power/battery-historian)，并建议优先考虑 system trace（按时间记录系统调度和设备事件的跟踪文件）、Macrobenchmark `PowerMetric`（在实体设备上重复执行用户场景的功耗基准指标）或 Android Studio Power Profiler。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。历史报告仍可继续用 Battery Historian 解读；新的自动化测量应使用可重复实验、公开 API 与平台原始证据。

## 先分清四种数据

功耗分析常见误判来自把“状态”“资源用量”“归因估算”和“硬件能量”当成同一类数据。

UID 是 Android 用来归属应用进程和资源用量的用户标识，同一个 UID 可能由多个共享 UID 的包共同使用。

ODPM（On-Device Power Rails Monitor）是部分设备提供的板载电源轨监视器；电源轨（rail）指面向 CPU、显示或蜂窝网络等硬件子系统的设备级计量通道。

归因指系统按活动记录和功耗模型，把估算能耗分配到 UID 或硬件组件。`BatteryUsageStats` 是承载这类系统归因结果的查询对象，数值仍受设备模型与测量能力限制。

| 数据 | 典型来源 | 能回答什么 | 不能直接回答什么 |
|---|---|---|---|
| 状态与事件时间线 | Batterystats 历史、system trace、应用 Trace | 某段时间发生了什么，哪些行为重叠 | 每个行为消耗了多少能量 |
| 本 UID 资源计数 | `SystemHealthManager.takeMyUidSnapshot()`、应用埋点 | CPU 时间、网络字节、WakeLock 与 Job 时长怎样变化 | 精确的整机或单功能能耗 |
| 系统归因估算 | `BatteryUsageStats`、设置页、bugreport | 系统怎样把组件能耗估算到 UID | 物理仪器级精度与跨设备可比性 |
| 设备级能量 | ODPM 电源轨、设备用能组件、外置功耗仪 | 实验窗口内整机或子系统能量差 | 普通场景下某个 App 的独占能量 |

能量与功率也要分开。能量描述一个窗口内累计消耗，功率描述消耗速率，平均功率等于能量增量除以时间增量。电池百分比经过量化和系统估算，短窗口内没有下降不能推导为“零消耗”。

## Android 17 的平台结构

### BatteryStatsService 与 PowerStatsService 各自负责什么

Android 17 仍由两个分工不同的系统服务处理电池统计与硬件功耗数据，这种分工早于 Android 15。

- [`BatteryStatsService`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java) 维护 `BatteryStatsImpl`，接收系统组件上报的状态与活动数据，触发外部统计同步，并通过 `BatteryUsageStatsProvider` 生成 UID 和功耗组件归因。
- [`PowerStatsService`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java) 访问 `android.hardware.power.stats` HAL。HAL 是系统与厂商硬件实现之间的标准接口；这里可读取 `energy consumer`（HAL 归类的用能组件）、`energy meter`（计量通道）和 `state residency`（硬件处于各功耗状态的累计时长），再把内部接口 `PowerStatsInternal` 发布给系统服务进程 `system_server`，供系统服务之间调用。
- 两者通过 `PowerStatsInternal` 协作。BatteryStats 还能使用控制器活动、内核时间、网络统计和设备 `power_profile.xml`；该 XML 保存设备厂商提供的功耗估算系数。设备缺少 HAL 电源轨时，系统仍可能给出模型估算。

“Streamlined Battery Stats”的 CPU、misc、connectivity 等 `flag` 只是平台迁移期间的实现开关，公开 API 没有与之对应的“三层架构”承诺。设备构建、季度版本和 OEM（设备厂商）可以采用不同开关状态。监控协议应依赖公开输出语义，不能假设某个内部开关始终开启。

### 从采集到 BatteryUsageStats

Android 17 的 `com.android.server.power.stats` 按 `collector`（采集器）、`history`（历史记录）、`processor`（归因计算器）、`store`（达到容量后覆盖旧记录的轮转存储）和 `provider`（查询结果组装器）分工：

1. `PowerStatsCollector` 的组件实现采集 CPU、Wi-Fi、移动网络、蓝牙、GNSS（卫星定位）、屏幕、传感器、WakeLock 等活动或能量样本。
2. `BatteryStatsHistory` 保存带单调时间的状态变化和 `PowerStats` 样本。历史有容量上限，旧数据会被清理，不能当作永久时序库。
3. `PowerAttributor` 根据设备状态、UID 状态和各组件的 `processor` 计算归因。Android 17 的 [`PowerAttributor`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/PowerAttributor.java) 把估算结果写入 `BatteryUsageStats.Builder`。
4. [`BatteryUsageStatsProvider`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java) 根据查询窗口组装当前会话、历史会话或累计统计。

CPU 可以说明测量值怎样参与归因。[`CpuPowerStatsProcessor`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java) 先按 `scaling policy`（共享调频策略的一组 CPU）与 `power bracket`（合并相近功耗档位的分组）估算各档活动成本；设备提供 CPU `energy consumer` 时，再用测得的总能量校准或分配估算。

Wi-Fi 与移动网络也会结合控制器活动、网络字节、进程状态和可用的用能组件。最终数值仍是系统模型下的归因结果，不能写成电源轨到 UID 的无误差测量。

### PowerStatsLogger 的周期不等于 Historian 采样率

Android 17 的 `com.android.server.powerstats.TimerTrigger` 保留高频与低频触发器，默认周期还可由资源配置覆盖；`BatteryTrigger` 在观察到电池整数电量下降时记录状态驻留时间。数据由 `PowerStatsLogger` 分别写入计量、模型与状态驻留三类轮转文件；轮转存储达到容量限制后会覆盖旧记录，供系统诊断或 incident 报告（系统故障事件包）使用。

这些触发器属于 `PowerStatsService` 的内部日志策略。Battery Historian 展示的是 bugreport 中可解析的 Batterystats 与系统材料，不能据此宣称 Historian 固定按某个周期“实时采集”。内部周期、保留量与文件格式也不应成为 App 监控协议。

## 正确采集 Battery Historian 证据

Battery Historian 的输入优先使用完整 bugreport。官方 [采集流程](https://developer.android.com/topic/performance/power/setup-battery-historian) 要求在 USB 调试设备上重置统计、断开供电、执行目标场景，再生成 bugreport。`dumpsys batterystats --proto` 只输出 Protocol Buffers 二进制格式的当前聚合统计且不带历史记录，无法替代完整的 Historian 时间线。

下面的命令用于一台专门的测试设备。`--reset` 会清除该设备当前的 Batterystats 数据；`full-history` 会额外记录 WakeLock、Alarm 和进程事件，官方最小采集流程无需此开关。该开关也会增加报告体积，因此不要在仍需保留现场的设备上运行。

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-history

# 断开 USB 供电后执行待测场景；完成后重新连接设备。
adb bugreport power-test.zip

# 额外保存文本摘要，便于版本控制和自动提取。
adb shell dumpsys batterystats --charged > batterystats-charged.txt

adb shell dumpsys batterystats --disable full-history
```

这组命令与 Android 17 `BatteryStatsService.dumpHelp()` 的参数一致。`android-17.0.0_r1` 的 `dumpsys batterystats` 没有 `--csv`、`--watch` 和 `--stats` 参数。需要 proto 形式的使用量摘要时，可用 `dumpsys batterystats --usage --proto`，但它仍不代替 bugreport 时间线。

分析前还要保存以下实验元数据：

- build fingerprint（系统构建的唯一标识字符串）、App 版本、ABI（应用二进制接口）、设备型号与开机时长；
- 充电状态、起止电量、温度、是否进入省电模式和热状态；
- 屏幕亮度、刷新率、音量、网络制式、信号条件与外设状态；
- 编译状态、账号同步、系统更新和其他后台活动；
- 场景开始与结束的单调时间，以及 App 自定义 Trace 标记；单调时间只随设备运行推进，不受手动改时钟影响。

bugreport 可能包含账号、网络、日志和设备标识等敏感信息。它适合实验室与用户明确参与的诊断会话，不适合由普通 App 静默采集并上传。

## 如何把性能指标与能量证据关联

### 用同一实验窗口对齐

功耗优化需要同时观察“完成了多少工作”和“付出了多少能量”。只降低功率可能让任务执行更久，总能量反而增加；只缩短耗时也可能提高峰值功率和温度。

建议每次实验至少保留：

- 场景产出：完成的请求、帧、音视频时长、处理的数据量或用户任务数；
- 性能：场景耗时、帧时间、CPU 时间、I/O、网络字节和内存压力；
- 能量：整机或所选 `PowerMonitor` 的能量增量；`PowerMonitor` 代表一个可读取的硬件计量通道或模型用能组件；
- 环境：温度、亮度、网络、充电状态、设备与系统版本；
- 正确性：失败率、画质、音质、数据完整性与功能结果。

报告同时给出每任务能量、耗时分布和失败率。这里的 A/B 实验是在等价条件下交替运行基准实现与候选实现；两组使用同一设备、同一场景与相近初始状态，并保留空闲基线，也就是不执行待测场景时的对照测量。跨设备汇总时按机型与系统版本分层。

### Power Profiler 与 Macrobenchmark

[Android Studio Power Profiler](https://developer.android.com/studio/profile/power-profiler) 可把 system trace 与 ODPM 电源轨放在同一时间轴上。官方当前将 ODPM 支持范围写为 Android 10 及以上的 Pixel 6 和更新机型，具体电源轨仍依设备而变。数据覆盖整台设备，前后台其他进程都会形成测量噪声。

[Macrobenchmark `PowerMetric`](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics#power-metric) 是实验性指标，适合把固定用户场景放入可重复测试。它报告系统范围的功率与能量变化，官方当前限定在 Pixel 6、Pixel 6 Pro 和更新的实体设备。CI 发布门禁是持续集成中用阈值阻止性能回退版本通过的检查；阈值应按固定测试设备建立，不能把一台设备的绝对值推广到所有 Android 设备。

## 普通 App 在 Android 17 能读取什么

### API 35：PowerMonitor

`SystemHealthManager.getSupportedPowerMonitors()` 与 `getPowerMonitorReadings()` 从 API 35 起公开。Android 17 的 [`SystemHealthManager` 源码](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java) 通过 `IPowerStatsService` 异步返回电源轨或 `modeled consumer`（用功耗模型估算的用能组件）。

使用时要遵守以下语义：

- 支持列表可能为空，电源监视器的名称与含义依设备而变；即使名称相同，也不能假设不同 OEM 的计量范围等价。
- [`PowerMonitorReadings`](https://developer.android.com/reference/android/os/PowerMonitorReadings) 返回自开机以来的累计能量，单位是微瓦秒，包含电池供电与插电阶段；重启后不连续。
- 单次累计值没有场景意义。使用同一组 `PowerMonitor` 在场景前后读取，按各自 `timestamp` 计算非负增量；该时间戳来自 `SystemClock.elapsedRealtime()`。跨重启、计数回退或 `ENERGY_UNAVAILABLE` 的样本应丢弃。
- 普通 App 读数可能被缓存并加入与调用 UID 相关的随机噪声。连续高频读取不能获得实验室仪器精度，也不应尝试反推去噪。
- 电源轨是设备级数据。App 只能在受控实验中用 Trace 时间窗做相关分析，不能把电源轨增量直接记为当前 App 的能耗。

`PowerMonitor` 适合在内部测试版中输出结构化实验记录：类型、原始名称、起止累计值、起止 `timestamp`、增量、设备与 build fingerprint。硬件通道名称可能暴露机型或硬件组合，生产上报应先评估这种设备指纹风险，并对采样频率和保留期设限。

### API 24：本 UID HealthStats

`SystemHealthManager.takeMyUidSnapshot()` 返回本 UID 的 `HealthStats`，即一组按键查询的累计计数器和计时器。[`UidHealthStats`](https://developer.android.com/reference/android/os/health/UidHealthStats) 提供用户态/内核态 CPU 时间、Wi-Fi 与移动网络字节、部分控制器活动、WakeLock、Job、Sync、传感器和前后台状态等键。

这些值适合作为资源代理指标，也就是用资源活动量提示可能的能耗变化，而不直接充当能量测量。读取端必须先用对应的 `has…()` 方法检查键是否存在，因为设备与版本可以缺少部分数据。共享 UID 会把多个包的统计记到同一身份下；系统代持的 WakeLock 和库内部调度也会影响解释。

### BatteryManager：电池状态与燃料计

[`BatteryManager`](https://developer.android.com/reference/android/os/BatteryManager) 公开电量、充电状态、瞬时/平均电流、`charge counter`（剩余电荷，单位微安时）和 `energy counter`（剩余能量，单位纳瓦时）等属性。设备可以不支持某个属性：`getIntProperty()` 对 `targetSdkVersion` 为 Android 9 及以上的应用返回 `Integer.MIN_VALUE`，更旧目标返回 0；`getLongProperty()` 返回 `Long.MIN_VALUE`；API 35 新增的 `getStringProperty()` 返回 `null`。

这些属性描述整块电池或燃料计状态。燃料计是根据电压、电流、温度等信号估算剩余电量的硬件与算法组合。瞬时电流噪声较大，平均电流的时间窗由硬件决定，剩余能量还会受充电状态、温度和估算法影响。它们适合记录实验环境或长窗口变化，不提供 App 归因。

Android 14 / API 34 的 `EXTRA_CYCLE_COUNT` 可提供充电循环计数，`EXTRA_HEALTH` 给出类别状态。普通 App 仍无法依靠这些字段得到一致的设计容量、实时内阻或精确衰减曲线；缺失值与 OEM 差异必须保留。

### 隐藏接口不能进入业务代码

Android 17 源码中的下列路径带 `@hide`，表示它们不属于第三方应用 SDK：

- [`BatteryStatsManager#getBatteryUsageStats()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/BatteryStatsManager.java)；
- [`BatteryUsageStatsQuery`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/BatteryUsageStatsQuery.java)；
- 按 UID 获取 `BatteryConsumer` 的路径。

这些路径还受 `BATTERY_STATS` 权限保护。Android 17 清单把它声明为 `signature|privileged|development`，普通第三方应用无法获得；平台签名应用、特权系统应用或开发调试环境要按各自授权条件判断。

`SystemHealthManager` 也没有 `getBatteryUsageStats()`、`registerBatteryStateCallback()` 或 `getCurrentPowerStats()`。

因此，普通 App 不能复制系统设置（Settings）或 `system_server` 的调用代码来获取全设备 `BatteryUsageStats`。这类信息应通过 adb、bugreport、平台测试组件或 OEM 授权的系统应用获取。

## WakeLock：从时间线定位持有者

WakeLock（唤醒锁）用于请求系统暂时保持某类硬件工作。应用排查重点通常是 `PARTIAL_WAKE_LOCK`：屏幕关闭后它仍可让 CPU 保持运行。旧的 `FULL_WAKE_LOCK` 等屏幕级别早已废弃，窗口保持亮屏应使用 `FLAG_KEEP_SCREEN_ON`；“Alarm Wakelock”更多表示系统因 Alarm 代持或归因的唤醒活动，不对应一种可由业务统一管理的 WakeLock 级别。

分析一段可疑窗口时按以下顺序检查：

1. 在 Historian 或 system trace 中定位屏幕关闭、CPU running（CPU 活动）与 userspace WakeLock（用户空间持有的唤醒锁）的重叠区间。
2. 按 UID 与 tag（调用方设置的识别标签）查看持有次数和总时长，再回到代码、库或系统 API 的调用来源。
3. 对照 Job、Alarm、FCM（Firebase Cloud Messaging）推送、位置、音频、传感器和网络活动，确认是谁请求工作、谁代持 WakeLock。
4. 检查 `acquire()`/`release()` 是否成对、异常路径是否释放、是否设置合理的 `timeout`（超时），以及重复任务是否并发。
5. 修改后复跑同一场景，并同时比较任务结果、WakeLock 时长、CPU 时间和能量增量。

多个 WakeLock 的时长不能简单相加为 CPU awake 时间，因为持有区间可能重叠。平台或库代持的锁也可能归因给应用；Android 官方的 [WakeLock 来源指南](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls) 列出了 AlarmManager、JobScheduler、WorkManager、FCM、位置与媒体等常见 tag 和修复方向。

常见修复是减少不必要的唤醒、合并可延期工作、缩短回调、让 JobScheduler/WorkManager/媒体 API 管理其需要的唤醒状态。手动 WakeLock 只覆盖无法由合适 API 处理的短临界区，参见 [WakeLock 使用建议](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock)。

线上还应结合 Play Console 的 [Android vitals 的 excessive partial WakeLock 指标](https://developer.android.com/topic/performance/vitals/excessive-wakelock) 观察真实用户影响，不把单台实验设备的结果直接外推到全量用户。

若证据涉及内核 wakeup source（可阻止系统挂起的内核唤醒源）、驱动中断或 suspend（系统挂起）失败，用户态 WakeLock tag 与内核 wakeup source 不能按名称一一对应。Android 17 通用内核源码以持续滚动的 `android17-6.18` 分支为基线，具体设备还要核对其内核构建号、驱动配置和厂商改动；分析时结合 Perfetto/ftrace 跟踪，Battery Historian 只提供时间关联线索。

## 网络活动的电池成本

“Wi-Fi 低、4G 中、5G 高、蓝牙极低”这种固定排序并不成立。信号质量、频段、基带状态机、扫描、连接建立、传输时长、数据量、硬件代际与共享芯片都会改变结果。5G 也不能统一解释为更高功耗，Wi-Fi 在弱信号或频繁扫描时同样可能很昂贵。

网络证据至少包含：

- 逻辑请求数、重试数、成功率、上下行字节与活跃时长；
- `transport`（Wi-Fi、蜂窝网络等承载类型）、`metered`（是否按计量网络处理）、`validated`（系统是否验证可访问互联网）、漫游、VPN 和信号强度分桶；
- DNS 解析、连接、TLS 握手、首字节和传输耗时；
- Wi-Fi/移动网络 `PowerMonitor` 是否可用及设备型号；
- 场景期间的后台流量与 radio 活动；radio 活动指蜂窝基带处于发送、接收或高功耗保持状态的时间。

优化假设需要逐项验证：

- 合并可延期的小请求可减少调度和 radio 活跃次数，但会增加等待时间与单次失败影响。
- 连接复用可减少 DNS/TCP/TLS 成本；主动频繁断开可能增加握手与 radio 状态切换。
- 预取可能降低用户等待，也可能下载用户永远不会使用的数据。
- WorkManager 的网络约束适合可延期任务；交互请求仍按用户时效执行，不能为了省电任意等待 Wi-Fi。

`TrafficStats` 或 `HealthStats` 的字节数只能表示活动量，能量还取决于传输时间和无线状态。移动网络与 Wi-Fi 的系统归因处理器还会使用控制器活动和设备模型，所以“每 MB 固定耗电”不能跨网络和设备复用。

## 应用级实战：验证一个后台同步假设

假设线上指标显示后台同步频繁，排查可以这样组织：

1. 从 Android vitals、APM（Application Performance Monitoring，应用性能监控）与任务日志确认问题集中在哪些版本、设备、网络和后台状态。
2. 在测试设备构造旧实现与候选实现，固定账号数据、同步结果和网络条件。
3. 用自定义 Trace 标记每次调度、实际执行、请求尝试与结束原因。
4. 同时采集 bugreport、Macrobenchmark/Power Profiler、PowerMonitor 增量和本 UID HealthStats。
5. 检查 Alarm/Job/WakeLock、radio 活跃、CPU 时间、字节、失败与重试是否在同一窗口变化。
6. 以每次成功同步的能量与耗时比较两组，并验证同步后的数据仍满足时效要求。

若候选实现减少唤醒却导致同步大量超时，结论不能写成“更省电”。同样，某次 Historian 时间线看起来更安静，也需要多轮实验和能量增量支持。优化收益只能填写测量得到的分布、样本条件和不确定性，不能预先写入固定百分比或“续航增加几小时”。

## 设备级实战：解释电源轨峰值

Power Profiler 或 PowerMonitor 显示 `CPU`、`display`、`cellular` 等电源轨增量时，先确认它是系统范围数据：

- 用 App Trace 标记目标操作，检查峰值是否与窗口重叠；
- 查看同一窗口是否有系统更新、媒体播放、其他 App、屏幕或温控变化；
- 对照空闲基线和不启动目标 App 的对照组；
- 将设备温度与 `thermal status`（系统热状态等级）纳入报告，避免把降频后的低功率误判为效率提升；
- 分别报告总能量、任务数、耗时和失败，不按假设把电源轨强制分配到进程。

内核调度、驱动、显示与基带（modem）可能共同影响电源轨。需要精确到硬件组件时，优先使用设备厂商的电源轨定义、外置功耗仪和受控 system trace。Battery Historian 的柱状状态只能协助缩小时间窗。

## 集成 APM：保存可解释指标，不上传 Historian

APM 汇集线上场景、性能和结果指标。Battery Historian 只提供离线分析界面，无法作为嵌入 App 的实时采集 SDK。

APM 应保存各层数据原本的含义：

| 层级 | 可采指标 | 使用方式 |
|---|---|---|
| 生产 App | 场景、耗时、请求、字节、任务结果、WakeLock 自埋点、电池/热状态 | 发现集中在特定版本或设备群的性能回退 |
| 本 UID 系统快照 | CPU 时间、网络、Job、Sync、WakeLock 与传感器计数 | 低频采样前后差值，验证资源代理 |
| 支持设备的 PowerMonitor | monitor 名称、类型、累计能量与 timestamp | 内测或严格采样的设备级窗口差分 |
| 实验室 | Macrobenchmark、Power Profiler、bugreport、外置功耗仪 | 复现、归因和发布门禁 |
| Play Console | excessive partial WakeLock 等 Android vitals | 观察真实用户分布与受影响会话 |

平台记录 `source`、`unit`、`scope`、`timebase`、`supported`、`model/device` 和 `collection_version`。其中 `scope` 表明数值覆盖整机、子系统还是本 UID，`timebase` 表明时间戳使用单调时钟还是可被校时的日历时间。`power_monitor_energy_uws`、`battery_energy_remaining_nwh`、`uid_cpu_time_ms` 等字段不能合并到一个含义模糊的 `battery_cost`。

告警使用同设备族、同 App 版本和相近场景的基线，并同时检查覆盖率。只有支持 PowerMonitor 的设备会产生电源轨指标，只有仍活跃并能上报的 App 会进入 APM。由样本进入条件造成的系统性差异叫选择偏差，这两类偏差都要在看板中展示。

## 低功耗模式、电池健康与设备差异

### App 应响应系统策略

普通 App 不应自行调 CPU 频率或全局屏幕亮度。可执行的策略包括：

- 通过 `PowerManager.isPowerSaveMode()`、充电状态与 WorkManager 约束调整可延期工作；
- 在后台减少非必要刷新、扫描和预取，保留用户明确发起的任务；
- 游戏或媒体应用在可接受范围内调整帧率、分辨率、码率或效果，并监控质量与延迟；
- 使用系统提供的调度、媒体、位置和传输 API，减少手动 WakeLock。

策略必须记录触发条件与结果。省电模式用户本来就可能处于低电量或重负载状态，直接比较开启和关闭人群会混入明显的选择偏差。

### 电池老化只作为分层变量

循环次数、温度与健康类别可以帮助解释同型号设备的差异，但不能由 Battery Historian 建立可靠的容量衰减或内阻模型；内阻是电池内部对电流表现出的等效电阻。设备使用史、充电策略、环境温度、燃料计算法与换电池记录通常不可得。

如果业务需要研究老化对性能的影响：

- 明确使用公开字段还是受控实验室测量，并保留 `unsupported`（设备不支持）状态；
- 在同型号、同系统、同温度区间内比较；
- 将热节流、剩余电量、充电状态和电源模式作为混杂变量；混杂变量是同时影响分组和结果、可能制造虚假关联的条件；
- 只输出统计关联，不把单次卡顿或耗电归因给电池老化。

### 跨设备比较以任务为单位

SoC（片上系统）的制程、核心数量、DVFS、显示面板、radio、散热、固件和电池容量共同决定结果。DVFS 是按负载动态调整处理器电压与频率的机制。不能根据“制程更小”“OLED”或“电池更大”直接推导效率。

跨设备报告以每个成功任务的能量、性能和质量为主，并保留绝对能量。电源轨名称与组件集合按设备维护映射；无法确认语义的电源轨归入设备专有项，不按名称猜测为 CPU、GPU 或内存。

## Android 17 验收清单

- Battery Historian 只用于离线受控分析，并在文档中注明维护状态。
- `dumpsys batterystats` 命令与 Android 17 `dumpHelp()` 对齐，不使用不存在的参数。
- 平台说明区分 `BatteryStatsService`、`PowerStatsService`、HAL 能量和 UID 模型归因。
- 不把内部功能开关、采集周期或文件保留量当成公开兼容性承诺。
- 普通 App 不调用隐藏的 `BatteryStatsManager`、`BatteryUsageStatsQuery` 或受限权限接口。
- PowerMonitor 处理 `unsupported`、累计值、时间戳、重启、回退、噪声和设备级 `scope`。
- HealthStats 读取前检查键是否存在，并把共享 UID 与系统代持计入解释。
- BatteryManager 属性处理 `unsupported`，电流、剩余能量与电量百分比不用于单 App 精确归因。
- WakeLock 分析区分直接持有、系统或库代持、重叠时长与任务结果。
- 网络优化保留 `transport`、信号、重试、字节、时延与 radio 证据，不采用固定网络功耗排名。
- A/B 实验控制设备、温度、亮度、网络、编译状态、后台负载与功能输出。
- APM 字段保留来源、单位、`scope`、`timebase`、支持状态和采集版本。
- bugreport、电源轨名称与设备健康数据经过隐私评估、访问控制和保留期管理。

## 全文小结

这套集成把线上信号、可重复实验和 Android 17 平台证据放进同一套证据体系。Battery Historian 仍可解释历史时间线；新的功耗结论应由受控场景、公开 API、system trace 和设备级能量测量共同支持。
