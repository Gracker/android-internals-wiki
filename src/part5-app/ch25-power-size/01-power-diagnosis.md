---
title: "功耗诊断与分析方法"
chapter: "25.1"
section: "25.1"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-22"
last_verified_against: "AOSP android-17.0.0_r1 (primary) + android-16.0.0_r1 + android-15.0.0_r1 (version diff) + Android Developers power docs + Clippings structure references"
confidence: medium-high
drafted_date: "2026-05-10"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/power/setup-battery-historian"
  - type: official
    path: "https://developer.android.com/topic/performance/power/battery-historian"
  - type: official
    path: "https://developer.android.com/studio/profile/power-profiler"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/stuck-wakelock"
  - type: official
    path: "https://source.android.com/docs/core/power/power-stats-hal"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/PowerStatsScheduler.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/stats/PowerStatsStore.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/WakeLockStats.java"
  - type: blog
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: blog
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
tags: [power-diagnosis, battery-historian, power-profiler, batterystats]
related_chapters: ["25.2", "11.1", "11.2", "14.11"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-22T04:51:20+08:00"
last_task2b_lite_at: "2026-06-03"
task2b_rework_log: "logs/task2b/2026-06-22-04-task2b-main-25.1.md"
last_task6_review_log: "logs/review/2026-06-03-07-review.md"
task6_review_notes: "2026-06-22 Task6 revisiting 复审通过；L1/L2 无新增问题（修复 1 处笔误'异常常'→'异常通常'）；Task2B 已修复 P0 源码链路问题；无 B 类回炉项，转入 Task9 pending 待技术复审。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-22"
last_task9_at: "2026-06-22T05:28:30+08:00"
last_task9_review_log: logs/deep-review/2026-06-22-05-deep-review.md
task9_review_notes: "2026-06-22 Task9 深度复审：auto-fix 了 PowerStatsStore 存储路径/格式、Android 16 调用行号、WakeupReason/WakeLockStats 行号及 master 锚点边界；返回 Task6 revisiting。"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
last_task6_at: "2026-06-22T05:06:00+08:00"
review_type: task6-writing-quality-review
task6_reviewed_date: "2026-06-03"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
last_task9_audit: "2026-06-22"
last_task9_autofix_at: "2026-06-22"
---

# 功耗诊断与分析方法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Battery Historian 与 Power Profiler 实战
- 🔹 dumpsys batterystats 解读
- 🔹 功耗归因：CPU / 网络 / GPS / WakeLock
- 🔹 功耗异常检测与定位

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解功耗诊断与分析方法

App 侧功耗诊断不用重复 Android 功耗模型的计算细节。模型、硬件电流表和 BatteryStats 归属算法见 §11.1；后台任务、定位、网络、Alarm 的省电策略见 §11.2；Battery Historian 的部署细节见 §14.11。

App 实战里要解决的是另一件事：用户说耗电之后，怎么把“掉电快”拆成可复现的场景、可对比的数据和可修改的代码入口。功耗诊断的目标是把 CPU、网络、GNSS、WakeLock 这些信号放到同一个时间窗口里判断，而不是追一个万能指标。

Part 5 更关注怎么抓数据、怎么读数据、怎么把异常归到业务动作上，不重新解释系统为什么这样计电。

## Battery Historian 与 Power Profiler 实战

功耗工具按粒度分三类：离线回放、实时观测、自动化回归。Battery Historian 属于离线回放，`dumpsys batterystats` 提供原始统计，Android Studio Power Profiler 负责把功耗轨道和 System Trace 放在同一条时间轴上。旧资料里常见的 Energy Profiler，在当前 Android Studio 文档中已经被 Power Profiler 取代。

[已验证: 官方文档, developer.android.com/topic/performance/power/setup-battery-historian]
[已验证: 官方文档, developer.android.com/studio/profile/power-profiler]

| 工具 | 适合回答的问题 | 典型输入 | 输出重点 |
|------|----------------|----------|----------|
| Battery Historian | 一段测试结束后，系统在什么时间段持续耗电 | `bugreport.zip` | `cpu_running`、`wake_lock`、`network`、`gps`、Job / Sync 记录 |
| `dumpsys batterystats` | 某个 UID 的 CPU、网络、WakeLock、传感器统计是多少 | 设备上的 BatteryStats 快照 | UID 级统计、历史事件、checkin 数据 |
| Power Profiler | 哪段代码执行时拉高了某条 power rail | Android Studio profiling session | CPU / display / modem / camera 等 power rails 与 trace 事件 |
| Perfetto | 线程调度、CPU 频点、网络包、power rails 如何在时间上重叠 | System Trace | 调度切片、counter、power rails、线程名 |
| Macrobenchmark `PowerMetric` | 优化前后功耗是否回退 | 可重复测试脚本 | energy / power 指标，适合 CI 阶段守门 |

Android Developers 在 2026 年更新的 Battery Historian 文档里已经明确提示：Battery Historian 不再活跃维护；能用 System Trace、Macrobenchmark power metric 或 Power Profiler 的场景，应优先使用这些工具。Battery Historian 仍有价值，位置更偏向长时间离线回顾和历史兼容。 [已验证: 官方文档, developer.android.com/topic/performance/power/setup-battery-historian]

一次可复现的功耗采集至少包含四个步骤：清理历史统计、断开 USB、执行固定场景、导出数据。下面这组命令只负责采集，不负责判断；判断要回到时间线和 UID 统计里做。

```bash
# 清理旧统计，给本轮测试一个干净起点
adb shell dumpsys batterystats --reset

# 短时场景可打开完整 WakeLock 历史；长时间测试慎用，历史缓冲区会更快写满
adb shell dumpsys batterystats --enable full-wake-history

# 断开 USB 后执行测试场景，例如：冷启动、后台播放 30 分钟、息屏定位 20 分钟
# 场景结束后重新连接设备，导出 bugreport
adb bugreport bugreport-power.zip

# 同时保存文本统计，方便后续 diff
adb shell dumpsys batterystats --charged > batterystats-charged.txt
adb shell dumpsys batterystats --checkin > batterystats-checkin.csv
```

`--reset` 后再采集，能减少历史噪声；断开 USB 是为了避免充电状态改变系统行为；`--charged` 适合查看自上次充满电以来的统计，`--checkin` 适合脚本化处理。短场景建议记录场景开始和结束的墙钟时间，后面在 Battery Historian 或 Perfetto 里按这段时间框选。

Power Profiler 的用法更贴近日常开发：让测试场景在 Android Studio profiler session 中跑一遍，然后把 power rails 的峰值和线程、方法调用、网络活动对齐。这个工具依赖设备的 On Device Power Rails Monitor 能力；不支持 ODPM 的设备仍能看部分系统 trace 信息，但无法给出完整 power rail 读数。 [已验证: 官方文档, source.android.com/docs/core/power/power-stats-hal]

## `dumpsys batterystats` 解读

`dumpsys batterystats` 是 Battery Historian 背后的原始数据入口。它的价值不在于可视化，而在于能按 UID 追到具体统计项。系统侧服务入口在 `BatteryStatsService`，持久统计与事件记录由 `BatteryStatsImpl` 管理，App 级电量汇总再进入 `BatteryUsageStatsProvider` 和各类 `PowerCalculator`。 [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java]

读文本输出时，先找目标包名对应的 UID，再看四组数据：CPU 时间、WakeLock、网络流量、传感器和定位。不要只看总耗电百分比；百分比会受设备电池容量、采样窗口、屏幕亮度和其他 App 行为影响。

下面是实战里常用的检索方式，用途是把一个很长的 `batterystats` 文件切成 UID 视角。

```bash
# 查包名对应 UID
adb shell cmd package list packages -U | grep com.example.app

# 导出完整统计
adb shell dumpsys batterystats --charged > batterystats.txt

# 在本地按 UID / 包名检索
rg "com.example.app|u0a123|Wake lock|Uid u0a123|Network|Sensor" batterystats.txt
```

命中结果要按时间窗口解释。CPU 时间高，代表进程在采样窗口内消耗了较多用户态或内核态时间；它不等同于电量，因为 CPU 处于小核低频和大核高频时，单位时间的电流差异很大。网络字节数高，也不等同于 modem 耗电；多次短连接可能比一次批量传输更糟。WakeLock 持有时间更接近直接异常信号，尤其是息屏后台场景。

`batterystats` 的另一层用途是做版本对比。固定同一台设备、同一电量区间、同一网络和亮度条件，分别跑基线版本和候选版本，再对比以下指标：

- `uid cpu time`：目标 UID 的用户态、内核态时间是否上升。
- `wake lock`：Partial WakeLock 的累计持有时间和仍在持有的 tag。
- `network`：Wi-Fi / mobile 的收发字节数、radio active 时间和唤醒次数。
- `sensor` / `gps`：传感器与 GNSS 是否在后台持续活跃。
- `job` / `sync` / `alarm`：后台调度是否比基线更频繁。

## 功耗归因：CPU / 网络 / GPS / WakeLock

功耗归因要按硬件入口拆，不要把“耗电”当成单一问题处理。一个 App 可能 CPU 时间不高，却因为频繁网络唤醒拖住 modem；也可能网络不多，但一个后台 WakeLock 让设备无法进入深度休眠。

### CPU：看运行时间，也看频点和线程

CPU 异常通常表现为目标 UID CPU time 上升、Perfetto 里目标进程线程密集运行、CPU frequency counter 长时间停在高频。诊断顺序是：用 `batterystats` 确认 UID CPU 时间，再用 Perfetto 找线程，再回到代码看这段线程在做计算、轮询、锁等待还是 IO 等待。

CPU 功耗不能只看线程是否 busy。大核高频、持续唤醒、频繁跨核迁移都会改变成本。调度和 DVFS 的机制见 §5.1、§5.4；实战判断看这个差异：同样 30 秒 CPU time，如果一个版本让大核长时间拉高频，另一个版本把任务压到短时批处理，两者的电量结果可能不同。

### 网络：看传输量，也看唤醒形态

网络功耗异常通常来自碎片流量。十几 KB 的请求如果每分钟唤醒一次，modem 和 Wi-Fi 都要反复从低功耗状态切到活跃状态。`batterystats` 里看 UID 收发字节数和 radio active；Battery Historian 里看 `network` 行是否出现密集短脉冲；Perfetto 里进一步查 socket tag、线程和请求发起点。

网络优化策略详见 §24.4、§24.5。诊断结论要落到“是哪类请求在唤醒网络、频率是多少、是否能批量化”。

### GPS 与传感器：看后台持续时间

GNSS、相机、麦克风、运动传感器都属于高风险功耗入口。GPS 异常在 Battery Historian 的 `gps` 行通常很直观：屏幕灭掉后仍有连续活跃区间，或者定位请求间隔远小于业务需要。`batterystats` 的 sensor / gps 项能把使用时间归到 UID。

定位治理见 §25.5。诊断阶段只做三件事：确认是否后台使用、确认请求间隔和精度等级、确认是否能用 geofence / passive location / batched location 代替持续高精度定位。

### WakeLock：把“让 CPU 不睡”的责任找出来

Partial WakeLock 是功耗异常里最容易直接归责的一类。Android Vitals 把 24 小时内后台或前台服务中的非豁免 Partial WakeLock 累计 2 小时及以上定义为 excessive wake lock；如果 24 小时内至少出现一次后台持有 1 小时及以上，会进入 stuck wake lock 视角。Vitals 口径会排除 audio、location、JobScheduler user-initiated 等明确用户收益场景；超过 5% app sessions / 28 天的 excessive wake lock 才进入 Play 质量门槛，本地诊断仍要排查所有 tag 和时间窗口。 [已验证: 官方文档, developer.android.com/topic/performance/vitals/excessive-wakelock] [已验证: 官方文档, developer.android.com/topic/performance/vitals/stuck-wakelock]

实战里要同时看三件事：tag 是否能指到业务模块、持有时间是否跨过场景结束点、bugreport 生成时是否仍处于 held 状态。如果 tag 写成 `wakelock`、`service` 这类无信息名称，定位会被迫转向线程栈、日志和埋点；这类命名问题应在代码规范里修掉。

## 功耗异常检测与定位

功耗异常检测要从“单次观察”升级成“对比实验”。最低可用方案是同一设备、同一系统版本、同一网络条件、同一亮度和音量，分别跑基线包和候选包。每个场景至少保留三类输出：`bugreport.zip`、`batterystats.txt`、Perfetto 或 Power Profiler trace。

| 场景 | 建议时长 | 主要指标 | 判定方式 |
|------|----------|----------|----------|
| 前台冷启动 + 首页停留 | 3-5 分钟 | CPU time、power rail 峰值、网络请求次数 | 候选版本不应新增持续高频 CPU 或碎片网络 |
| 息屏后台保活 | 20-60 分钟 | Partial WakeLock、Alarm、Job、CPU running | 息屏后应快速进入低活跃状态 |
| 导航 / 运动 / 录音类长任务 | 30-120 分钟 | GNSS / sensor active、WakeLock、温度 | 持续硬件使用必须和用户可感知任务匹配 |
| 弱网重试 | 10-30 分钟 | mobile radio active、重试次数、失败队列 | 重试应退避，不能固定间隔唤醒 |

定位流程可以压成一张决策表：

| 观察到的异常 | 下一步检查 | 常见代码入口 |
|--------------|------------|--------------|
| 息屏后 `cpu_running` 连续活跃 | 查 WakeLock、Alarm、Job、前台服务 | `PowerManager.WakeLock`、`AlarmManager`、`WorkManager`、FGS |
| modem rail 或 `network` 短脉冲密集 | 查请求频率、失败重试、socket tag | 轮询、日志上报、IM 长连接保活、HTTPDNS 刷新 |
| GPS 长时间活跃 | 查定位请求间隔、精度、后台调用栈 | `FusedLocationProviderClient`、地图 SDK、运动轨迹模块 |
| CPU time 上升但网络和 GPS 正常 | 查热点线程、锁等待、序列化、加解密 | 线程池、协程 dispatcher、JSON / protobuf、数据库扫描 |
| 候选版本总耗电上升但单项不突出 | 查采样窗口、屏幕亮度、温度、其他 UID | 测试环境波动、热降频、系统服务背景任务 |

Power Profiler 与 Perfetto 最适合做“时间同步”。当 power rail 出现尖峰时，不要直接下结论；先在同一时间点查线程、网络包、frame、日志 marker。只有功耗轨道和业务事件在时间上重合，才值得进入代码级修复。

## 源码级实现细节（AIW-源码调研-2026-06-16）

> 关联报告：`DeepResearch/2026-06-16-android15-battery-historian-perf-metrics-integration.md`
> 锚点版本：AOSP `android-17.0.0_r1` 为主锚点，`android-16.0.0_r1` / `android-15.0.0_r1` 用于版本差异，最高边界 Android 17 / API 37
> 一手资料：`BatteryStatsService.java`、`PowerStatsService.java`、`PowerStatsScheduler.java`、`BatteryUsageStatsProvider.java`、`WakeLockStats.java`

### ⚠️ 重要勘误：daily-topics.json topic #1 的 source_refs 不存在

> `frameworks/base/services/core/java/com/android/server/battery/BatteryHistorian.java` 在 AOSP 任何分支中**均不存在**。`server/battery/` 目录从未存在；Battery Historian 本身是独立 Go 工具（`github.com/google/battery-historian`），不在平台树内。
>
> Battery Historian 在 AOSP 端的真实数据生产者是 `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`，配合 `PowerStatsService`（HAL 数据采集）+ `PowerStatsScheduler`（周期聚合）+ `BatteryUsageStatsProvider`（统一归因入口）共同完成。

### 功耗归因路径：Android 15 → 16 → 17 版本演进

`BatteryStatsService.systemServicesReady()` 在三个 Android 版本中逐步重构了功耗归因链路。下面的分析以 `android-17.0.0_r1` 为最终锚点，Android 15/16 差异单独标注。

#### ① Android 15（`android-15.0.0_r1`）：三层 aconfig flag 控制 collector / exporter

`BatteryStatsService.systemServicesReady()`（L619-L631）集中配置哪些 power component 走实测 HAL 路径： [已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java]

| Flag | 覆盖组件 | 关闭时行为 |
|------|----------|-------------|
| `Flags.streamlinedBatteryStats()` | `POWER_COMPONENT_CPU` | `CpuPowerCalculator` 用 PowerProfile 估算 |
| `Flags.streamlinedMiscBatteryStats()` | `WAKE_LOCK` / `SCREEN` / `AUDIO` / `VIDEO` / `GNSS` / `SENSORS` / `CAMERA` / `MEMORY` / `ANY` | 各类 `*PowerCalculator` 用 PowerProfile 估算 |
| `Flags.streamlinedConnectivityBatteryStats()` | `MOBILE_RADIO` / `PHONE` / `WIFI` / `BLUETOOTH` | `MobileRadioPowerCalculator` 等估算 |

Android 15 中，这些 flag 的作用是决定各 `PowerCalculator` 走实测（`PowerStatsService` 采集的 HAL 数据）还是建模（`PowerProfile` 估算）。此版本**不存在** `processor/MultiStatePowerAttributor.java`——旗舰归因逻辑没有独立 processor。`PowerStatsScheduler.start(Flags.streamlinedBatteryStats())` 在 L707-L710 调用，带 boolean 参数控制是否启动周期聚合。

**实战判定方式**：
```bash
adb shell dumpsys batterystats --usage --proto
# 看输出中 component 是 "modeled" 还是 "measured"
```

#### ② Android 16（`android-16.0.0_r1`）：`MultiStatePowerAttributor` 引入

Android 16 新增 `processor/MultiStatePowerAttributor`，归因路径变为： [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java]

```
BatteryUsageStatsProvider.getBatteryUsageStats()
  → MultiStatePowerAttributor.estimatePowerConsumption()
    → PowerStatsExporter.exportAggregatedPowerStats()
      → BatteryUsageStats.Builder.aggregate()
```

`PowerStatsInternal.getStateResidencyAsync()` — 位于 `BatteryStatsService` 的低功耗状态查询/打印路径（`android-17.0.0_r1` L294-L297），**不是** `BatteryUsageStatsProvider` 的主归因链。`PowerStatsScheduler.start(boolean enablePeriodicPowerStatsCollection)`（L92-L97）保持带参形式。

#### ③ Android 17（`android-17.0.0_r1`）：flag 移除 + `start()` 无参化

Android 17 中 `BatteryStatsService` 已移除 `Flags.streamlinedBatteryStats()` 判断，`PowerStatsScheduler.start()` 变为无参方法（L91-L94）。归因链与 Android 16 一致，但不再由 aconfig flag 开关控制： [已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java] [已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/PowerStatsScheduler.java]

```
BatteryUsageStatsProvider.getBatteryUsageStats()（L286-L287）
  → mPowerAttributor.estimatePowerConsumption()
```

### PowerStatsScheduler：周期聚合主调度器

`frameworks/base/services/core/java/com/android/server/power/stats/PowerStatsScheduler.java`

| Android 版本 | `start()` 签名 | 调用位置 |
|-------------|---------------|---------|
| 15（`android-15.0.0_r1`） | `start(Flags.streamlinedBatteryStats())` | `BatteryStatsService.java` L707-L710 |
| 16（`android-16.0.0_r1`） | `start(boolean enablePeriodicPowerStatsCollection)` | `BatteryStatsService.java` L629-L631 |
| 17（`android-17.0.0_r1`） | `start()`（无参） | `BatteryStatsService.java` L573-L576 |

三个版本的共同行为：
- 通过 `AlarmManager` 注册 **inexact non-wakeup alarm** 触发聚合
- 聚合动作在 `mHandler` 线程执行，**不会阻塞 system_server main looper**
- 落盘到 `PowerStatsStore`（在 `/data/system/power-stats/`，span 文件后缀为 `.pss`）

### WakeupReason × Perfetto POWER track —— 「业务耗时 × 系统功耗」对齐点

`BatteryStatsService.java` L2928（`WakeupReasonThread.run()` 内）：

```java
Trace.instantForTrack(Trace.TRACE_TAG_POWER, "wakeup_reason",
        SystemClock.elapsedRealtime() + " " + reason);
```

**一次 wakeup 同时写入 3 个数据源**：
1. Perfetto ftrace `power` track 的 instant 事件（`TRACE_TRACK_WAKEUP_REASON = "wakeup_reason"`）
2. `mCpuWakeupStats` 内存聚合
3. `BatteryStatsImpl` 的 history buffer

这是「业务耗时 × 系统功耗」二维分析在 Android 平台层的**唯一明确实现点**。APM 端可借此把 systrace 调度切片（`sched_wakeup`）与 power 事件做时间对齐。

### 标准化 WakeLockStats API（@hide）

`core/java/android/os/WakeLockStats.java`（244 行）

```java
public final class WakeLockStats implements Parcelable {
    public final List<WakeLock> wakeLocks;          // 每锁明细
    public final List<WakeLock> aggregatedWakeLocks; // 聚合视图

    public static class WakeLock {
        public final int uid;
        public final String name;
        public final boolean isAggregated;
        public final WakeLockData totalWakeLockData;
        public final WakeLockData backgroundWakeLockData;  // 对应 stuck partial wake lock 判定
    }

    public static class WakeLockData {
        public final int timesAcquired;
        public final long totalTimeHeldMs;
        public final long timeHeldMs;  // 0 = 未持锁
    }
}
```

服务端入口：`BatteryStatsService.getWakeLockStats()`（L3534-L3540，权限 `BATTERY_STATS`）。

**对 Battery Historian 的意义**：旧版只能从 dumpsys 文本 `grep "Wake lock"`，新版 APM 可直接走 `IBatteryStats.getWakeLockStats()` 拿 `Parcelable` 快照。`backgroundWakeLockData` 字段对应 Android Vitals 的 stuck partial wake lock 判定（>1h 后台持有）。

### 与 §26.3 的衔接

§26.3 已覆盖 `BatteryUsageStats` 数据通道、statsd 45KB atom pull 降级、History 持久化。本节补充：
- Streamlined battery stats 三层 flag → 决定 device 走「实测」还是「估算」路径
- PowerStatsScheduler 周期聚合 → 与 statsd 异步解耦的**第二条**功耗数据通路
- `WakeLockStats` 新 API → 把 wake lock 从 dumpsys 文本格式升级为 System API
- Perfetto POWER track wakeup_reason instant → 业务事件与功耗事件的**统一时间锚**

### 反哺要点（建议 Battery Historian 替代方案选型时复用）

1. **判断 device 走哪条归因路径**：`dumpsys batterystats --usage --proto` 输出中的 `power_model` 字段，值为 `POWER_MODEL_POWER_PROFILE` vs `POWER_MODEL_MEASURED_ENERGY`
2. **新增 wakeup 监控**应同时检查 `Trace.TRACE_TAG_POWER` track 与 BatteryStats history 两条线 —— 二者在 `BatteryStatsService.WakeupReasonThread` 内已统一落点
3. **`WakeLockStats.getWakeLockStats()`** 在 Android 15 引入，但 `@hide`，端侧 APM 需通过系统权限或反射调用
4. **PowerStatsStore** 位于 `/data/system/power-stats/`，span 文件名是 19 位 ID + `.pss`，内容由 `PowerStatsSpan.writeXml(out, Xml.newBinarySerializer())` 写成二进制 XML；不要按 `/data/system/powerstats/log.powerstats.meter.0` 或 Proto 文件处理。

## 本节小结

功耗诊断的工作顺序很固定：先把场景做成可复现测试，再用 `batterystats` 找 UID 级异常，接着用 Battery Historian / Power Profiler / Perfetto 把异常放回时间线，并按 CPU、网络、GPS、WakeLock 四类入口归责。

功耗诊断的输出不应该是一句“App 很耗电”，而应该是“在息屏后台 30 分钟场景中，目标 UID 持有 `upload_worker` Partial WakeLock 24 分钟，同时每 60 秒触发一次 mobile radio active；疑似日志上传重试未退避”。只有到这个粒度，后面的 §25.2、§25.3、§25.5 才能进入具体治理。
