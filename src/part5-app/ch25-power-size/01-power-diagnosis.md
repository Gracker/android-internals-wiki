---
title: "功耗诊断与分析方法"
chapter: "25.1"
section: "25.1"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-22"
last_verified_against: "AOSP android-17.0.0_r1 (primary) + android-16.0.0_r1 + android-15.0.0_r1 (version diff) + Android Developers power docs + Clippings structure references"
confidence: medium-high
consolidated_from:
  - "src/part2-performance/ch07-smoothness/16-power-thermal-jank-playbook.md"
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
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-22T04:51:20+08:00"
last_task2b_lite_at: "2026-06-03"
task2b_rework_log: "logs/task2b/2026-06-22-04-task2b-main-25.1.md"
last_task6_review_log: "logs/review/2026-06-03-07-review.md"
task6_review_notes: "2026-06-22 Task6 revisiting 复审通过（第二轮）；Task9 auto-fix 后内容完整，L1/L2 无新增问题；4 锚点全覆盖；9 处已验证 0 待验证；无 B 类回炉项；task9_result=auto-fixed 视同技术复审完成，自动晋升 finalized。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-22"
last_task9_at: "2026-06-22T05:28:30+08:00"
last_task9_review_log: logs/deep-review/2026-06-22-05-deep-review.md
task9_review_notes: "2026-06-22 Task9 深度复审：auto-fix 了 PowerStatsStore 存储路径/格式、Android 16 调用行号、WakeupReason/WakeLockStats 行号及 master 锚点边界；返回 Task6 revisiting。"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-22"
last_task6_at: "2026-06-22T06:08:57+08:00"
review_type: task6-writing-quality-review
task6_reviewed_date: "2026-06-03"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
last_task9_audit: "2026-06-22"
last_task9_autofix_at: "2026-06-22"
---

# 功耗诊断与分析方法

## 从问题描述到可归因证据

“App 掉电快”不是可以直接修复的问题描述。它缺少设备、系统版本、前后台状态、网络、温度、测试区间和业务动作。缺少这些条件时，电量百分比下降、某条电源轨峰值、某个 UID 的 CPU 时间都不能单独证明责任归属。

功耗诊断要完成三次转换：

1. 把用户感受转换成可重复执行的场景。
2. 把设备级能量变化转换成同一时间窗内的 CPU、网络、GNSS、WakeLock 等证据。
3. 把系统证据定位到线程、请求、定位订阅或唤醒锁标签，再验证修改前后的差异。

功耗模型、硬件电流计与 BatteryStats 的计算原则见 §11.1；后台任务、Alarm、网络与定位策略见 §11.2；Battery Historian 的部署见 §14.11。这里专注于采集、解读和归因。

## 先分清三类证据

功耗工具观察的是不同层次。把它们的输出混为一谈，常会得到“时间上相关，所以由 App 引起”的错误结论。

| 证据层次 | 常用工具 | 能回答什么 | 不能单独证明什么 |
|---|---|---|---|
| 设备能量 | 外部电源分析仪、ODPM、电池电荷计 | 整机或电源轨在测试区间内消耗了多少能量 | 某个 App 应归属多少 |
| 系统归因 | `dumpsys batterystats`、`BatteryUsageStats`、Android Vitals | 系统把 CPU、网络、WakeLock、传感器等活动记给了哪个 UID | 每项统计与物理能量完全相等 |
| 执行行为 | Perfetto、应用日志、方法追踪 | 哪个线程、请求或回调在某个时刻运行 | 单次尖峰必然造成可感知续航问题 |

外部电源分析仪更接近整机能量基准；ODPM 和电池计数器仍是设备级读数；BatteryStats 按系统可见的活动和模型做 UID 归因；Perfetto 负责解释时间线上发生了什么。可靠结论通常需要其中两层以上互相印证。

## 设计可比较的测试

基线包与候选包必须在同一台设备、同一系统构建、相近电量和温度下测试。屏幕亮度、刷新率、音量、网络类型、信号条件、账号同步和其他前台 App 也要保持一致。若业务依赖服务器响应，还要记录服务端版本和返回数据规模。

场景时长由业务周期和仪器分辨率决定，不存在适用于所有 App 的“标准分钟数”。短场景需要重复执行，直到信号能够从测量噪声中辨认；后台场景则要覆盖一次完整调度、重试或定位周期。预热、正式采集和冷却阶段要分开，避免把安装、编译、缓存填充或热节流混进业务耗电。

建议为每轮测试保存以下信息：

- 设备型号、Android 构建指纹和电池健康状态。
- App 版本、提交号、安装方式及是否清除数据。
- 场景开始与结束时间、屏幕和充电状态。
- 网络类型、信号强度、亮度、刷新率、音量和环境温度。
- `bugreport.zip`、`batterystats` 文本、Perfetto trace，以及应用侧场景标记。
- 每次重复的原始结果，不只保留均值。

## Battery Historian 与 Power Profiler 实战

### 工具怎么选

| 工具 | 适合的问题 | 关键边界 |
|---|---|---|
| Battery Historian | 回看一段较长区间内的系统事件、UID 统计、Job、Sync 和 WakeLock | 已停止活跃维护；图中的活动条不等于该组件消耗的能量 |
| `dumpsys batterystats` | 获取 BatteryStats 的文本或 checkin 数据，按 UID 比较 CPU、网络、WakeLock 和传感器统计 | 功耗值可能来自模型估算，也可能由硬件能量校准；它不是直接测得的 App 能量 |
| Power Profiler | 把 ODPM 电源轨与 System Trace 放在一条时间轴上 | ODPM 是设备级数据，设备和电源轨支持情况不同 |
| Perfetto | 对齐线程调度、CPU 频点、应用 trace、唤醒原因和功耗计数器 | 数据源、采样分辨率和轨道名称依设备而异 |
| Macrobenchmark `PowerMetric` | 对可重复场景做自动化功耗对比 | 仍为实验 API；指标是系统级，并受支持设备范围限制 |

Android Developers 已在 [Battery Historian 使用说明](https://developer.android.com/topic/performance/power/setup-battery-historian)中提示该项目不再活跃维护，并建议优先考虑系统追踪、Macrobenchmark `PowerMetric` 或 Power Profiler。Battery Historian 仍适合读取现有 bugreport、观察长时间系统事件及兼容旧分析流程，不宜再作为唯一依据。

### 一轮可复现的 BatteryStats 采集

下面的命令用于测试设备。它会重置 BatteryStats 统计，不应在保留现场的用户设备上执行。

```bash
# 记录设备和系统身份，避免把不同构建的结果混在一起
adb shell getprop ro.build.fingerprint
adb shell dumpsys battery

# 清除旧的 BatteryStats 区间
adb shell dumpsys batterystats --reset

# 仅在需要逐个查看用户态 Partial WakeLock 时启用
adb shell dumpsys batterystats --enable full-wake-history

# 断开 USB，执行预先定义的测试场景；场景结束后再连接设备
adb bugreport bugreport-power.zip
adb shell dumpsys batterystats --charged > batterystats-charged.txt
adb shell dumpsys batterystats --checkin > batterystats-checkin.csv

# 采集完成后恢复默认的 WakeLock history 粒度
adb shell dumpsys batterystats --disable full-wake-history
```

`--reset` 让本轮数据有清楚的起点；`--charged` 表示输出自上次充满电以来的数据，并不表示设备当前正在充电；`--checkin` 输出便于程序解析的 CSV。完整 WakeLock history 会占用更多历史记录空间，只在需要时开启。官方采集步骤要求测试期间断开 USB，因为充电会改变电池电流方向和系统电源状态；USB 数据链路在不少设备上还会阻止完整休眠。

### Battery Historian 应该怎么看

Battery Historian 的系统视图先用于检查实验条件：屏幕、充电、信号、温度、Doze 和其他 UID 是否在目标区间内发生变化。确认环境没有明显干扰后，再看目标 App 的 `Userspace Wakelock`、`JobScheduler`、`SyncManager`、网络和进程状态。

图上的一段 `cpu_running`、`gps` 或网络活动只说明该资源在这段时间活跃。官方文档也说明，时间线中的彩色区间不显示组件消耗了多少电。正确用法是从异常区间出发，查看同一时间是否有目标 UID 的 WakeLock、Job、网络或前台状态，再回到文本统计和 trace 查责任来源。

### Power Profiler 和 Perfetto 应该怎么看

[Power Profiler](https://developer.android.com/studio/profile/power-profiler) 从 Android Studio Hedgehog 起展示 ODPM 电源轨。官方支持范围是 Android 10 及以上的 Pixel 6 和后续 Pixel 设备；可见的具体电源轨仍由设备决定。不支持 ODPM 的设备可能只提供电池容量、电荷和电流数据。

ODPM 衡量的是设备或硬件子系统，不是 App。若 WLAN 电源轨在某个请求期间升高，只能说明两者在时间上重合。要进一步归因，还要排除其他进程的网络活动，并查看目标 UID 的流量、socket tag、线程和业务标记。

下面的 Perfetto 数据源片段用于在支持的设备上采集电池计数器和 ODPM 电源轨。`250 ms` 来自 Perfetto 官方示例，只表示一个示例采样周期；完整配置应按设备分辨率、场景时长和追踪文件体积评估。

```textproto
data_sources: {
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

设备不支持某个计数器或电源轨时，配置不会凭空产生数据。[Perfetto 功耗数据源文档](https://perfetto.dev/docs/data-sources/battery-counters)说明：电池计数器来自 IHealth HAL，反映整机流入或流出电池的电荷；ODPM 由 IPowerStats HAL 提供，测量点在电池下游，不受充放电方向直接影响。二者的存在与分辨率都由设备实现决定。

### Macrobenchmark 适合做回归，不适合宣称“App 单独耗电”

Macrobenchmark `PowerMetric` 可以把固定操作脚本纳入回归测试，输出 CPU、显示、GPU、GPS、内存、机器学习和网络等类别的功率或能量变化。当前官方文档把它标为实验 API，且数据是系统级，仅支持 Pixel 6、Pixel 6 Pro 及后续设备。

在使用前先调用 `PowerMetric.deviceSupportsHighPrecisionTracking()` 做能力检查，并尽量减少测试设备上的其他应用与账号活动。回归阈值应来自同型号设备的重复测试分布，不能直接复用另一款设备的绝对数值。

## `dumpsys batterystats` 解读

### 从包名定位 UID

Android 以 UID 作为很多资源统计的归属单位。共享 UID、多用户和隔离进程都可能让“一个包名等于一个 UID”的假设失效。阅读报告前，应先记录当前安装实例的 UID。

下面的命令用于导出目标包统计，并从 checkin 数据中定位常见记录类型。

```bash
adb shell cmd package list packages -U | grep 'com.example.app'
adb shell dumpsys batterystats --charged com.example.app > app-batterystats.txt
adb shell dumpsys batterystats --checkin > batterystats-checkin.csv

rg ',(uid|wl|kwl|wr|nt|sr|jb|sy|apk),' batterystats-checkin.csv
```

文本输出适合人工阅读，checkin 输出适合稳定解析。官方 `dumpsys` 文档列出的常见段标识符包括：`wl` 表示 WakeLock，`kwl` 表示内核 WakeLock，`wr` 表示唤醒原因，`nt` 表示网络，`sr` 表示传感器，`jb` 表示 Job，`sy` 表示 Sync。解析器必须同时识别 checkin 版本；不要用固定列号跨 Android 版本直接读取。

### 先确认统计区间

任何数值都要连同区间一起记录。常见区间包括自充满电、自重置或当前放电会话。`--charged` 不会把统计自动裁成刚执行的业务场景；如果测试开始前没有重置，输出仍可能包含早先活动。

还要区分三种时间：

- 墙钟时间用于对应日志和人工操作。
- `elapsedRealtime` 包含深度睡眠，适合描述开机后的经过时间。
- `uptimeMillis` 不包含深度睡眠，适合辨认设备是否有较长休眠。

比较基线与候选包时，使用同一种统计区间，并保存场景起止标记。只比较两个报告里的累计值，区间不同会直接破坏结论。

### 读数表示什么

| 读数 | 可以说明 | 还要补什么证据 |
|---|---|---|
| UID 的 user/system CPU 时间 | 目标 UID 消耗了多少处理器时间 | 调度切片、频点、核簇、热点线程 |
| 网络字节和包数 | UID 传输量及分组数量 | 请求时间、网络类型、信号、radio active、重试 |
| mobile radio active | 蜂窝无线电活跃时间及次数 | 其他 UID 干扰、RAT、信号、请求批次 |
| Partial WakeLock 时间 | CPU 被目标 UID 的锁请求保持唤醒多久 | 锁标签、持有区间、业务是否仍需要 |
| GNSS / sensor 时间 | 定位或传感器在 UID 下的活跃情况 | 精度、频率、批处理、前后台状态 |
| estimated power | 系统基于模型和可用硬件数据给出的归因结果 | 设备级测量和同条件对照实验 |

CPU 时间不是能量。相同 CPU 时间可能分布在不同核簇和频点上，也可能伴随不同温度。网络字节数也不是无线电能量：批量传输和反复短请求可产生不同的无线电状态切换。BatteryStats 的功耗汇总适合比较和排查，不应被写成实验室电源分析仪的等价物。

Android 17 的 `dumpsys batterystats --usage` 仍支持 `--model power-profile`，用于强制采用 `PowerProfile` 功耗模型。不要再依赖旧文档中的 `BatteryConsumer.getPowerModel()` 判断每项是“实测”还是“模型”；Android 17 源码已将该接口标为弃用，并返回未定义值。设备是否提供能量数据，应结合 PowerStats HAL 能力、追踪数据中的电源轨以及目标设备实现判断。

## 功耗归因：CPU / 网络 / GPS / WakeLock

### CPU：从 UID 时间追到运行线程

CPU 异常常表现为目标 UID 的 user/system CPU 时间上升、Perfetto 中线程持续运行，或 CPU 频率轨道长时间处于较高档位。排查顺序如下：

1. 用 BatteryStats 判断 CPU 时间是否只在候选包上升。
2. 在 Perfetto 中按目标进程筛选 `sched` 切片，找出运行时间增加的线程。
3. 对齐 CPU 频率、idle 和 thermal 轨道，确认设备是否因高频、少休眠或温度发生变化。
4. 回到线程栈和业务标记，区分计算、轮询、序列化、锁竞争与 I/O 等待。

“线程存在”不等于“线程消耗 CPU”。等待锁或等待 I/O 的线程可能长时间存活却很少运行；密集唤醒的短任务也可能让设备难以进入低功耗状态。调度和 DVFS 原理见 §5.1、§5.4。

### 网络：传输量与唤醒形态要一起看

网络功耗通常同时受传输量、请求批次、无线电接入技术和信号影响。排查时把以下证据放在同一时间窗：

- BatteryStats 的移动网络与 Wi‑Fi 收发字节、包数和 radio active。
- Perfetto 或 Network Inspector 中的请求开始、结束、失败和重试。
- 信号强度、网络切换和是否使用蜂窝网络。
- 应用侧的请求类型、批次、退避和 socket tag。

若候选包多出密集短请求，结论应写明请求来源和触发条件。若只看到 modem 或 WLAN 电源轨上升，暂时只能确定硬件活动增加；还不能把全部差值记给目标 App。网络治理见 §24.4、§24.5。

### GNSS 与传感器：确认订阅是否越过业务边界

定位异常常见于页面离开后没有取消更新、后台仍保留高精度请求、多个 SDK 重复订阅，或请求参数远高于业务需求。BatteryStats 可以显示 UID 下的 GNSS 和传感器活动，Battery Historian 可以显示它们与屏幕、进程状态的关系。

定位报告至少写清以下内容：

- 请求由哪个模块或 SDK 发起。
- 前台、前台服务或后台中的哪种状态在使用。
- 精度、最小更新间隔、最小距离和批处理参数。
- 页面、任务或订阅结束后是否及时取消。
- 能否采用 geofence、被动定位或批量定位。

同一个 UID 中的多个库会合并计数，BatteryStats 不能代替应用侧订阅日志。定位策略见 §25.5。

### WakeLock：区分应用锁、内核唤醒源和唤醒原因

这三个名词经常被混用：

- 应用 Partial WakeLock 由 `PowerManager.WakeLock` 请求，目标是让 CPU 在屏幕关闭后继续运行。
- 内核唤醒源（wakeup source）是 Linux 电源管理对象，记录设备驱动阻止 suspend 或触发唤醒的活动。
- 唤醒原因（wakeup reason）描述最近一次 suspend 恢复或 suspend 中止的原因。

它们可以相关，但不存在通用的一对一映射。一个应用 WakeLock 可能经由系统服务反映为不同的内核对象；一次硬件中断唤醒也未必由某个 App 直接触发。

[Android Vitals 的 excessive partial wake lock 口径](https://developer.android.com/topic/performance/vitals/excessive-wakelock)是：24 小时内，App 处于后台或运行前台服务时，所有非豁免 Partial WakeLock 累计达到 2 小时。音频、定位和 JobScheduler 的 user-initiated API 当前有豁免。若该问题在 28 天内影响超过 5% 的 App 会话，可能影响 Play 可见性。

[Stuck partial wake lock 口径](https://developer.android.com/topic/performance/vitals/stuck-wakelock)是：24 小时内至少出现一次在后台连续持有满 1 小时的 Partial WakeLock。它与“多把锁累计 2 小时”的 excessive 指标不是同一个条件。

本地诊断不应等到达到 Vitals 门槛才处理。只要锁持续到业务结束之后，或标签无法识别责任模块，就应检查。下面的封装展示两个安全要求：使用可定位的标签，并同时设置超时与 `finally` 释放。

```kotlin
suspend fun <T> PowerManager.withPartialWakeLock(
    operationName: String,
    timeoutMs: Long,
    block: suspend () -> T,
): T {
    require(timeoutMs > 0)

    val wakeLock = newWakeLock(
        PowerManager.PARTIAL_WAKE_LOCK,
        "${BuildConfig.APPLICATION_ID}:$operationName",
    )
    wakeLock.acquire(timeoutMs)

    return try {
        block()
    } finally {
        if (wakeLock.isHeld) {
            wakeLock.release()
        }
    }
}
```

`timeoutMs` 应来自该操作的业务时限，而非随意复制的常量。超时只是额外保护；正常路径和异常路径仍要在 `finally` 中释放。若 WorkManager、媒体、定位或其他库间接持锁，还要按 Vitals 显示的标签查对应 API。

## 功耗异常检测与定位

### 用场景定义取代固定时长模板

| 场景 | 场景结束条件 | 主要观察项 | 常见干扰 |
|---|---|---|---|
| 冷启动并完成首屏 | 首屏内容与异步初始化完成 | CPU、存储、网络、显示电源轨 | 安装后编译、首次缓存、服务端冷请求 |
| 息屏后台等待 | 覆盖至少一个预期调度周期 | Partial WakeLock、Job、Alarm、CPU idle | USB、系统同步、消息推送 |
| 导航、录音或播放 | 用户可见任务完成 | GNSS、音频、传感器、WakeLock、温度 | 信号、音量、路线与媒体内容 |
| 弱网重试 | 请求成功或达到产品重试上限 | radio active、失败次数、退避间隔 | 网络模拟方式、DNS、服务端限流 |
| 周期同步 | 覆盖完整同步与静默阶段 | 网络批次、Job、Sync、后台 CPU | 账号数据量、系统维护窗口 |

同一场景至少要有基线包和候选包。重复次数由结果波动决定：如果组内波动与版本差值相当，就要增加重复、改善实验控制或更换测量方式，不能直接宣布回退。

### 从现象走到代码入口

| 现象 | 下一步证据 | 常见入口 |
|---|---|---|
| 息屏后 CPU 仍持续运行 | Partial WakeLock、Job、Alarm、前台服务和线程调度 | `PowerManager.WakeLock`、`WorkManager`、`AlarmManager`、FGS |
| WLAN 或 modem 轨道出现密集脉冲 | UID 网络统计、请求日志、重试与 socket tag | 轮询、遥测上报、长连接心跳、DNS 更新 |
| GNSS 在业务结束后仍活跃 | 定位订阅日志、页面与服务生命周期 | 地图 SDK、轨迹模块、`FusedLocationProviderClient` |
| CPU 时间上升而网络、GNSS 无明显变化 | 热点线程、频点、锁等待、序列化和数据库扫描 | 线程池、协程调度器、JSON / protobuf、数据库 |
| 整机能量上升但 UID 指标无明显变化 | 屏幕、温度、其他 UID、系统服务和设备状态 | 测试环境或设备级组件 |

时间重合是定位线索，不是因果证明。更可靠的验证是做受控消融：关闭一个可疑模块、延后某类请求或替换实现，再观察异常轨道和设备能量是否随之变化。

### 诊断结论怎么写

一份可执行的结论应包含：

- 设备、系统、App 版本和测试场景。
- 基线与候选包的重复结果及波动。
- 异常发生的时间窗。
- BatteryStats、trace 和应用日志中的相互印证。
- 能定位到的 UID、线程、请求、订阅或 WakeLock tag。
- 仍未排除的干扰和下一步验证。

例如，可以写成：“在 Pixel 测试机的息屏上传场景中，候选包在业务结束后仍保留 `com.example.app:upload` Partial WakeLock；同一时间窗内上传线程按固定间隔唤醒并发起失败重试。禁用该重试模块后，WakeLock 区间和移动网络活动一同消失。”其中的设备、区间、间隔和差值都应由本轮原始记录填写，不能套用示例数字。

## Android 17 源码中的功耗归因链

以下分析以 `android-17.0.0_r1` 为平台锚点。Battery Historian 是独立项目，不存在于 `frameworks/base`；AOSP 平台负责产生 BatteryStats、PowerStats 和 bugreport 数据。

下面的图用于区分“记录活动”“聚合功耗”和“展示结果”三条职责。

```mermaid
flowchart LR
    A["应用与系统服务事件"] --> B["BatteryStatsImpl history / UID 统计"]
    C["内核、控制器与 PowerStats HAL"] --> D["PowerStats collectors"]
    D --> B
    B --> E["PowerStatsScheduler"]
    E --> F["MultiStatePowerAttributor"]
    F --> G["PowerStatsStore"]
    B --> H["BatteryUsageStatsProvider"]
    G --> H
    H --> I["BatteryUsageStats / dumpsys"]
    B --> J["bugreport"]
    J --> K["Battery Historian"]
```

[`BatteryStatsImpl`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java) 保存事件历史和 UID 统计；采集器把 CPU、无线控制器或能量消费者等数据写入功耗统计；`PowerStatsScheduler` 周期聚合；`MultiStatePowerAttributor` 按设备状态与 UID 状态计算；`BatteryUsageStatsProvider` 生成查询结果；Battery Historian 只读取 bugreport 中已经存在的数据。

### Android 17 的主路径

在 [`BatteryStatsService.systemServicesReady()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java) 中，CPU、WakeLock、屏幕、移动网络、Wi‑Fi、蓝牙、音视频、GNSS、传感器、相机及自定义能量消费者等组件被统一启用。这里的“启用”表示框架允许采集和归因，不表示所有设备都具有对应的硬件能量计。

[`BatteryUsageStatsProvider`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java) 在构建 `BatteryUsageStats` 时调用 `PowerAttributor.estimatePowerConsumption()`。Android 17 使用的 [`MultiStatePowerAttributor`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java) 配置各功耗组件的处理器，并通过 `PowerStatsExporter` 把聚合结果写入构建器。

各处理器会根据组件采用不同输入。例如 [`CpuPowerStatsProcessor`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java) 读取 CPU 活跃时间、核簇和频点对应的 `PowerProfile` 参数；若采集结果带有 EnergyConsumer 数据，再用硬件能量调整各功耗分组（power bracket）的估算。移动网络处理器也会根据可用信息在 `PowerProfile` 与硬件能量之间校准。因而 Android 17 的归因不是简单的“全实测”或“全模型”二选一。

### Android 15 到 Android 17 的变化

| 版本 | 归因开关与调度器 | 需要记住的边界 |
|---|---|---|
| Android 15 | `streamlinedBatteryStats`、`streamlinedConnectivityBatteryStats`、`streamlinedMiscBatteryStats` 控制采集器和导出器；`PowerStatsScheduler.start(boolean)` | 新旧归因路径处于切换期 |
| Android 16 | 引入 `MultiStatePowerAttributor`，各组件仍受上述 flag 控制；调度器仍接收 boolean | 多状态功耗处理器已进入主要归因路径 |
| Android 17 | `BatteryStatsService` 对相关组件统一传入 `true`；`PowerStatsScheduler.start()` 改为无参 | 平台主锚点不再需要按这些 flag 判断是否启用 |

对应源码可在 [`android-15.0.0_r1 BatteryStatsService`](https://android.googlesource.com/platform/frameworks/base/+/android-15.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java)、[`android-16.0.0_r1 BatteryStatsService`](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java)和 [`android-17.0.0_r1 PowerStatsScheduler`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/stats/PowerStatsScheduler.java)中核对。这里保留 Android 15、16 只为解释迭代；当前结论以 Android 17 为准。

### PowerStatsScheduler 与 PowerStatsStore

Android 17 的 `PowerStatsScheduler.start()` 会安排功耗聚合，并注册下一次调度。它使用 `AlarmManager.ELAPSED_REALTIME` 的非唤醒闹钟，由后台 `Handler` 执行聚合；该闹钟本身不会为了统计而唤醒已经休眠的设备。

[`PowerStatsStore`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/stats/PowerStatsStore.java) 接收构造参数 `systemDir`，再创建 `power-stats` 子目录，所以典型路径是 `/data/system/power-stats/`。span 文件名是 19 位补零 ID 加 `.pss`，通过 `Xml.newBinarySerializer()` 写成二进制 XML，并由 `AtomicFile` 更新。它既不是普通文本 XML，也不是旧资料中所写的 Proto 日志路径。该目录属于系统内部实现，普通 App 不应直接读取。

### Wakeup reason 如何进入 Perfetto 和 BatteryStats

Android 17 的 `BatteryStatsService.WakeupReasonThread` 等待原生层返回唤醒原因。原生实现位于 [`com_android_server_am_BatteryStatsService.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_BatteryStatsService.cpp)，通过 `ISuspendControlService` 注册唤醒回调。收到原因后，Java 层会：

- 在 `TRACE_TAG_POWER` 的 `wakeup_reason` 轨道写入瞬时事件。
- 把原因交给 `CpuWakeupStats` 做统计与归因。
- 写入 `BatteryStatsImpl` history。

这条路径为 Perfetto、CPU wakeup 统计与 BatteryStats history 提供了共同时间点，但它不是应用行为与物理功耗之间的因果证明，也不是平台中仅有的功耗追踪入口。分析时仍要结合同一时刻的 IRQ、线程、Alarm、Job 和应用事件。

### `WakeLockStats` 为什么不能给普通 App 反射调用

Android 17 的 [`WakeLockStats`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/WakeLockStats.java) 是 `@hide` 的 `Parcelable`，包含逐锁和聚合列表。每条记录有 UID、名称、总持有数据和后台持有数据。`BatteryStatsImpl.getWakeLockStats()` 用主计时器生成总数据，用子计时器生成后台数据。

[`BatteryStatsService.getWakeLockStats()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java) 受 `BATTERY_STATS` 权限保护；Android 17 的 [`AndroidManifest.xml`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/res/AndroidManifest.xml) 将该权限声明为 `signature|privileged|development`。普通三方 App 既不能把它当作 SDK API，也不能靠反射绕过 Binder 权限校验。可行方案如下：

- 普通 App：使用 Play Console 的 Android Vitals、测试设备上的 `adb dumpsys`、bugreport、Perfetto 和应用侧 WakeLock 记录。
- OEM、系统 App 或测试工具：在拥有相应系统权限并维护版本兼容的前提下使用隐藏接口。
- 开发版设备：把隐藏接口调用限制在内部诊断组件，不随生产 APK 发布。

`backgroundWakeLockData` 只是后台计时器的快照字段。Android Vitals 的 excessive 和 stuck 判定还包含 24 小时窗口、前后台或前台服务状态、豁免项和会话聚合，不能把一个字段直接等同于 Play 指标。

## SoC 与设备差异：先查能力，再谈精度

Android 17 提供统一接口，不会保证每款 SoC 有相同数量的电源域、相同采样率或相同精度。按 ARM、Qualcomm、MediaTek 或 Samsung 给出固定误差、固定电源轨数量和固定节电比例，缺少具体设备、硬件设计、固件与实验条件，无法作为工程结论。

### 四类常见数据能力

| 能力 | 平台入口 | 数据含义 | 设备差异 |
|---|---|---|---|
| 电池容量、电荷、电流、电压 | IHealth HAL / `/sys/class/power_supply` | 整机电池侧计数器 | 字段是否存在、更新周期和分辨率不同 |
| ODPM 电源轨 | IPowerStats HAL 能量计 | 某条硬件电源轨累计能量 | 电源轨名称、组合方式和数量不同 |
| EnergyConsumer | IPowerStats HAL | CPU、显示、移动网络等消费者的累计能量 | 可用消费者和 UID 归因能力不同 |
| StateResidency | IPowerStats HAL | 电源实体在各状态停留的时间和进入次数 | 实体及状态由设备定义 |

Android 17 的 [`IPowerStats.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl) 通过 `getEnergyConsumerInfo()`、`getEnergyMeterInfo()` 和 `getPowerEntityInfo()` 暴露设备能力，再通过对应查询接口返回数据。客户端应先枚举能力，不应按厂商名猜测。

### 内核锚点告诉了我们什么

在 `android17-6.18-2026-06_r6` 中，[`power_supply_sysfs.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/power/supply/power_supply_sysfs.c) 定义了 `voltage_now`、`current_now`、`current_avg`、`charge_counter`、`energy_now` 等通用属性。具体驱动只会暴露它支持的属性，因此“内核定义了字段”不等于每台设备都能读取，也不代表刷新速度相同。

同一内核锚点下，[`drivers/base/power/wakeup.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c) 维护 `wakeup_source` 的 `active_count`、`event_count`、`total_time` 等统计；[`kernel/power/wakeup_reason.c`](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/kernel/power/wakeup_reason.c) 记录 suspend 恢复的 IRQ 或中止原因。这些是设备与驱动层证据，不能直接替代 UID 级 BatteryStats。

### 跨设备比较方法

- 在每台设备上保存 Power Profiler 或 Perfetto 实际列出的电源轨和计数器。
- 同一设备内比较基线与候选包；跨设备更适合比较趋势，不宜直接比较绝对电流。
- 记录系统构建和固件，因为相同硬件的计数器映射也可能随版本变化。
- 用设备级能量验证“整机是否改善”，用 UID 与 trace 解释“哪段行为改变”。
- 需要发布绝对精度或节电比例时，说明测量仪器、接线方式、样本量、置信区间和误差来源。

## 小结

功耗诊断从可重复场景开始，而不是从一张电量截图开始。BatteryStats 负责提供 UID 统计，Battery Historian 适合离线回看系统事件，Power Profiler 和 Perfetto 用于对齐电源轨、计数器与执行行为，Macrobenchmark `PowerMetric` 可用于受支持设备上的自动化回归。

归因时始终保留层次边界：CPU 时间、网络流量、GNSS 活跃和 WakeLock 是活动证据；ODPM 与电池计数器是设备级能量证据；Android 17 的 `MultiStatePowerAttributor` 会按可用输入结合模型与硬件能量。结论只有定位到明确场景、时间窗、UID 和代码入口，并通过基线对照或消融实验复核，才足以指导修改。
