---
title: Battery Historian 与功耗分析工具
chapter: '14.11'
section: '14.11'
status: finalized
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: "2026-07-07"
last_verified_against: "AOSP android-17.0.0_r1 PowerMonitorReadings.java / PowerStatsService.java / PerformanceHintManager.java / frameworks/native/include/android/performance_hint.h"
confidence: medium
sources:
- path: https://source.android.com/docs/core/power/power-stats-hal
  type: official
tags:
- Battery Historian
- bugreport
- 功耗分析
- Wakelock
- 电池
- Power Profiler
- ODPM
- Energy Profiler
related_chapters:
- '11.1'
- '11.2'
- '11.5'
- '14.1'
- '15.5'
created_by: task2a-knowledge-gap
created_date: '2026-04-09'
gap_source: 官方文档+读者需求
gap_score: 15/20
drafted_by: openclaw-task2a
drafted_date: '2026-04-10'
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-07-07
last_task6_at: 2026-07-07T15:10:00+08:00
last_task6_review_log: logs/review/2026-07-07-04-review.md
task6_reviewed_date: '2026-07-07'
review_notes: '2026-05-08 task6 revisit: pass-light-edit。完成写作层复审；修正虚假引导语/填充词和格式空行；无新增 B 类回炉项；转入 Task9 复审。 | 2026-05-08 Task9 17:38：needs-rework。P0 2 / P1 0 / P2 1；14.11 PowerMonitor 常量值与 PowerStatsService 源码路径/版本错误，需回炉修正。 | 2026-05-08 Task6 18:20：复审 Task2B P0 修复后的文稿，完成代码围栏语言标注与第一/二人称痕迹小修；无新增 B 类回炉项；转入 Task9 复审。 | 2026-06-19 Task9 audit 18:25：auto-fixed。闲时抽检发现 4 处源码/版本锚点小问题：Android 35 误写为 Android 15、PowerMonitorReadings.getConsumedEnergy 方法归属、NDK performance_hint.h AOSP 根路径、Android 16/17 PowerStatsAggregator 迁移路径；已局部修正并退回 Task6 复审。 | 2026-06-24 Task6 复审：pass-light-edit。Task9 auto-fix 后文稿写作层无新增问题；L1/L2 全部通过。转 Task9 确认。 | 2026-07-06 Task6 复审：pass-light-edit。Task2B lite 修复后文稿复审；L1 修正 3 处禁用词「链路」→「路径」（均在补充段）；无新增 B 类回炉项；转 Task9 复审。 | 2026-07-06 Task6 revisit：pass-light-edit。完成写作层再次复审；小幅优化表达清晰度，无新增 B 类回炉项；转入 Task9 复审。 | 2026-07-07 Task6 复审：pass-light-edit。L1 修正 4 处禁用词（3×链路→路径/衔接缺口, 1×闭环→回路）；修正 frontmatter 孤立字段 last_task2b_main_at 归位；无新增 B 类回炉项；转 Task9 复审。 | 2026-07-07 Task2B Verifier: frontmatter 重建（commit 80759fd88 破坏了 YAML frontmatter，已从 git 历史恢复） | 2026-07-07 Task6 复审：pass-light-edit。修复全文重复（1856→925行）；L1 修正禁用词「对齐」→「同步」（参考链接描述）；无新增 B 类回炉项；转 Task9 复审。'
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task2b_rerun_at: '2026-07-07T02:53:56+08:00'
last_task2b_lite_at: 2026-07-07
last_task2b_at: '2026-07-07T02:53:56+08:00'
task9_result: auto-fixed
last_task9_at: "2026-07-07T12:33:06+08:00"
last_task9_audit: 2026-07-07
last_task9_autofix_at: "2026-07-07"
task9_reviewed_by: openclaw-task9
task9_review_notes: "2026-07-07 Task9 AUTO-FIX：修正 PowerMonitorReadings Android 17 API 签名（需传入 PowerMonitor / OutcomeReceiver.onResult）、μW·s/ms→mW 公式、PerformanceHintManager.createHintSession 示例、performance_hint.h AOSP 路径；回到 Task6 复审。"
task9_reviewed_date: '2026-07-07'
last_task9_review_log: "logs/deep-review/2026-07-07-12-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-07
last_task6_audit: '2026-07-09'
---
# 14.11 Battery Historian 与功耗分析工具

功耗分析面对的是几种不同证据：系统事件有没有发生、某个 UID 被归因了多少电量、某条硬件电源轨累计了多少能量，以及整机从电源端取走了多少能量。它们的单位、时间范围和归因模型不同，不能放进同一列直接比较。

平台基线是 Android 17 / API 37 / `android-17.0.0_r1`。Battery Historian 仍能读取 bugreport，但 Google 已说明该工具不再积极维护；新问题应优先考虑 System Trace、Perfetto `android.power`、Android Studio Power Profiler 或 Macrobenchmark `PowerMetric`。Historian 的价值主要在于回看较长时间内的 Wakelock、JobScheduler、同步、定位、网络和电池历史。

## 按问题选择证据

| 要回答的问题 | 优先工具 | 数据含义 | 不能直接证明什么 |
|---|---|---|---|
| 灭屏后有哪些任务、锁和无线活动 | Battery Historian、`dumpsys batterystats` | BatteryStats 历史事件与 UID 统计 | 某一行变色消耗了多少焦耳 |
| 某次操作期间哪条 rail 的能量增加 | Perfetto `android.power`、Power Profiler | ODPM/Power Stats HAL 的系统级累计能量 | 增量全部属于目标应用 |
| 同一场景改动前后是否有功耗回归 | Macrobenchmark `PowerMetric` | 测量窗口内的系统级 power/energy/battery 指标 | 一次运行就能代表总体分布 |
| 应用代码读取设备支持的 power monitor | API 35+ `SystemHealthManager` | 自启动以来的累计 `uWs`，设备相关 | 瞬时功率或逐应用能耗 |
| 平台按 UID、组件和进程状态归因 | `BatteryUsageStats`、statsd、bugreport | BatteryStats 与功耗模型的归因结果 | 未实现硬件计量时的绝对精度 |
| 整机供电端的高精度功耗 | 外部电源分析仪 | 测量边界处的电压、电流和能量 | 不加额外埋点时的线程归因 |

一份有用的报告应写明使用了哪种证据。例如，“WLAN rail 在 20 秒窗口增加 4.2 J”与“目标 UID 被 BatteryStats 归因 4.2 J”是两种结论，即使数值恰好接近。

## Battery Historian 还适合做什么

Battery Historian 把 bugreport 中的 BatteryStats 历史渲染成时间线，并提供系统和应用统计表。时间线中的色块表示事件或状态处于活动期，不表示该组件在这段时间消耗了多少电量。

它适合回答这些问题：

- 屏幕关闭后，CPU running、userspace wakelock、JobScheduler 或 sync 是否仍然活跃；
- 一个 Wakelock tag 的累计次数和持有时间是否符合业务预期；
- 后台定位、wakeup alarm 或网络活动是否集中在合理窗口；
- 两份 bugreport 的统计差异落在哪些 UID 和事件类型。

它不适合短时函数级测量，也不能从一条时间线直接计算某段代码的毫瓦数。

### 采集一份可比较的 bugreport

下面的命令用于清空当前 BatteryStats、打开完整 userspace wakelock 历史，并在测试结束后生成 bugreport。

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history

# 断开 USB，在电池供电状态下执行固定测试场景。
# 完成后重新连接设备，再抓取报告。
adb bugreport bugreport.zip

# 不再需要完整 wakelock 历史时关闭它。
adb shell dumpsys batterystats --disable full-wake-history
```

`--reset` 会清除当前统计和历史，应在确认不需要保留现场后执行。完整 Wakelock 历史会占用更多历史缓冲区，只应覆盖目标测试窗口。测试阶段断开 USB，是为了让 BatteryStats 进入 on-battery 统计口径；抓取 bugreport 时重新连接不会抹掉前面的历史。

Android 7.0 及更高版本使用 zip bugreport。报告可能含账号、网络、应用、日志和设备状态等敏感信息，不应上传到不受信任的在线 Historian 服务。

### 部署边界

Google 的 `battery-historian` 仓库已在 2022 年归档。官方 Android 文档仍给出 `stable:3.1` 容器命令，但旧镜像和旧前端依赖可能在新主机上出现拉取或架构兼容问题。

下面的命令来自官方安装说明，用于尝试在本机启动归档版本。

```bash
docker run -p 9999:9999 \
  gcr.io/android-battery-historian/stable:3.1 \
  --port 9999
```

页面启动后访问 `http://localhost:9999`，上传刚生成的 bugreport。若镜像已经无法使用，应转用 `dumpsys batterystats` 文本、Perfetto 或 Power Profiler，不要为了复活旧依赖而把生产 bugreport 交给第三方站点。

## 怎样读 Historian 时间线

| 行或区域 | 表示什么 | 合理的下一步 |
|---|---|---|
| Battery level | 电池计量芯片报告的剩余百分比变化 | 长窗口观察趋势；短窗口不要依赖百分比差值 |
| CPU running | 系统至少有 CPU 处于运行状态 | 与 Wakelock、alarm、job 和 Perfetto sched 数据交叉检查 |
| Userspace wakelock | 记录到历史中的应用 Wakelock 活动 | 按 UID 与 tag 查累计次数、时长和调用代码 |
| Top app | 当时处于前台的应用 | 只用来提供场景上下文，不能当成功耗排名 |
| JobScheduler / SyncManager | job 或同步活动窗口 | 核对周期、约束、停止原因和业务触发条件 |
| Mobile radio / Wi-Fi | 无线网络相关状态与活动 | 联合请求日志、信号强度和网络类型判断 |
| GPS / sensor | 定位或传感器活动 | 核对请求方、精度、批处理与停止时机 |
| App Stats | 目标 UID 的累计统计 | 检查 CPU、网络、Wakelock、job、sensor 等分项 |

时间重叠只能建立相关性。例如，WLAN 活动与一次图片下载重叠，说明该操作值得进一步测量；它不能排除同一时刻其他进程使用 WLAN，也不能给目标应用分配该 rail 的全部能量。

### Wakelock 的判断边界

bugreport 生成时仍被持有的锁值得检查，但这不自动等于泄漏。录音、导航、媒体播放等任务可能合法持锁，判断依据是持锁原因、生命周期和时长是否与用户可见任务一致。

Android vitals 把 24 小时内合计达到 2 小时的后台或前台服务 Partial Wakelock 视为过度使用，并排除音频、定位和 JobScheduler user-initiated API 等部分场景。这个阈值用于线上质量统计，不能替代本地场景的需求判断。

### `top_app` 与电池下降曲线

`top_app` 表示前台状态，不表示“耗电最多的应用”。电池百分比又经过 fuel gauge 估算和取整，短测试里可能长时间不变，也可能一次跳变。短时优化应比较 rail 能量、外部仪表或可重复的系统级指标；长时待机测试再把百分比斜率作为辅助证据。

## 直接使用 `dumpsys batterystats`

Historian 页面打不开时，BatteryStats 文本仍然可用。Android 17 的 `BatteryStatsService.dumpHelp()` 区分了 human-readable、history、proto 和 checkin 等输出。

下面的命令用于保留不同粒度的原始证据。

```bash
# 人类可读的当前统计
adb shell dumpsys batterystats > batterystats.txt

# 当前历史
adb shell dumpsys batterystats --history > battery-history.txt

# 当前统计的 checkin 格式；-c 不采用 --checkin 的旧记录清理语义
adb shell dumpsys batterystats -c > batterystats-current-checkin.csv

# 仅查看目标包相关统计
adb shell dumpsys batterystats com.example.app > app-batterystats.txt
```

`--checkin` 在 Android 17 的帮助文本中还带有“输出并清除上一次已完成旧统计”的语义。自动化脚本若只想读取当前数据，应先确认使用 `-c` 还是 `--checkin`，不能把两者当作完全等价。

文本字段会随平台演进。解析脚本应记录 build fingerprint 和 Android 版本，并对未知行保留原始内容；按固定列号硬切容易在升级后静默读错。

## 从异常时间线走到代码

### Wakelock 持有过长

1. 从 App Stats 记录 UID、tag、次数和累计时长。
2. 确认锁是在前台、后台还是前台服务期间持有。
3. 在代码和依赖库里搜索 tag，检查超时、取消、异常和进程退出路径。
4. 用 Perfetto 加应用 trace section，把 acquire/release 的业务上下文与线程调度放到同一时间轴。
5. 修复后用同一场景重新采集，不用一次结果代替重复测试。

`WakeLock.acquire(timeout)` 能给异常路径设置上限，但它不能修复错误的生命周期设计。WorkManager、媒体、定位等组件还可能间接持锁，未知 tag 应先查组件来源。

### Job、alarm 或同步过密

Historian 能显示运行窗口和累计次数。下一步应检查调度 API、约束、flex、退避、停止原因以及服务端推送能力。仅把周期调大可能延迟任务，却没有消除重复触发或失败重试。

对 WorkManager，可结合 `WorkInfo.getStopReason()`；对 JobScheduler，可结合 `JobParameters.getStopReason()` 和 `dumpsys jobscheduler`。需要线程级原因时，再录 Perfetto。

### CPU 活动持续

CPU running 只能说明设备没有完全休眠。定位 CPU 花在哪里，需要 System Trace 或 simpleperf：

- Perfetto 的 sched 数据回答哪些线程在运行、被谁唤醒、是否被抢占；
- CPU frequency 和 idle 数据回答频率与空闲状态；
- simpleperf 回答采样落在哪些函数；
- Thermal/ADPF 数据帮助区分工作量增加与热降频。

### 网络、定位和传感器

无线功耗受信号、网络制式、批处理和其他进程影响。Historian 用来圈定活动窗口，请求日志用来解释业务行为，Perfetto 或 power rail 用来观察系统级能量变化。定位和传感器还要核对精度、批处理延迟、前后台状态与停止时机。

## Perfetto：把 rail 与线程放进同一时间轴

Android 17 Perfetto 的 `android.power` 数据源可以轮询电池 counter，并在硬件与 HAL 支持时采集 power rail。下面的配置以 1 秒轮询开始，适合先确认设备是否有数据。

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
      battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
      battery_counters: BATTERY_COUNTER_CHARGE
      battery_counters: BATTERY_COUNTER_CURRENT
      collect_power_rails: true
    }
  }
}
duration_ms: 30000
```

降低 `battery_poll_ms` 会增加时间分辨率和采集负担。rail 通常是自启动以来的累计能量 counter，UI 或 SQL 通过相邻样本差分得到窗口能量和平均功率。设备没有 ODPM 时，trace 可能只有 battery capacity、charge、current 等 counter。

Android 17 的 Perfetto SQL 标准库已经提供 `android.power_rails` 模块。下面的查询用于读取每条 rail 的相邻样本区间。

```sql
INCLUDE PERFETTO MODULE android.power_rails;

SELECT
  power_rail_name,
  ts,
  dur,
  energy_delta,
  average_power
FROM android_power_rails_counters
WHERE dur > 0
ORDER BY ts, power_rail_name;
```

`energy_delta` 的单位是 `uWs`，数值上等于微焦耳；`average_power` 的单位是 mW。模块会跳过没有形成有效相邻区间的尾部样本。分析时还应同时查询目标进程、线程调度和应用 trace section，避免把系统后台噪声算给目标应用。

## Android Studio Power Profiler

Android Studio Hedgehog 起，Power Profiler 在 System Trace 中展示 ODPM 数据。官方文档给出的高精度 rail 支持范围是 Pixel 6 及后续 Pixel 设备；平台的 Power Stats HAL 允许其他厂商实现类似能力，但不能据此保证 Studio 会在任意 Android 10+ 设备上提供同样的 rail、名称或分辨率。

ODPM 测量的是电池下游一个硬件子系统或若干硬件单元的累计能量。它不受设备当时充电或放电方向的直接影响，但仍是系统级数据。CPU、GPU、Display、WLAN、Camera 等 rail 是否存在，由设备决定。

使用时应检查：

- 目标设备是否出现 Power Rails，而非只有 battery capacity/current；
- rail 名称和子系统映射是否有设备文档支持；
- 测试窗口内是否有系统更新、同步、温控或其他应用干扰；
- 改动前后是否使用同一设备、系统版本、亮度、网络和温度条件。

“硬件计量”也不等于“逐应用计量”。Power Profiler 适合把一次业务动作与设备 rail 变化建立时间相关性，应用归因仍需 BatteryStats、线程活动和受控 A/B 实验。

## Macrobenchmark `PowerMetric`

`PowerMetric` 在 AndroidX Benchmark 1.2.0 加入，最低测量平台是 API 29，并且仍标记为实验 API。高精度 Power/Energy 指标的官方支持范围是 Pixel 6、Pixel 6 Pro 及后续设备，结果表示整个系统在测试窗口中的消耗。

下面的基准在运行前检查高精度能力，再采集 CPU、Display 与 Network 能量。

```kotlin
@OptIn(ExperimentalMetricApi::class)
@RunWith(AndroidJUnit4::class)
class PowerBenchmark {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun startupEnergy() {
        assumeTrue(PowerMetric.deviceSupportsHighPrecisionTracking())

        rule.measureRepeated(
            packageName = "com.example.app",
            metrics = listOf(
                PowerMetric(
                    PowerMetric.Type.Energy(
                        mapOf(
                            PowerCategory.CPU to PowerCategoryDisplayLevel.TOTAL,
                            PowerCategory.DISPLAY to PowerCategoryDisplayLevel.TOTAL,
                            PowerCategory.NETWORK to PowerCategoryDisplayLevel.TOTAL,
                        )
                    )
                )
            ),
            iterations = 10,
            startupMode = StartupMode.COLD,
        ) {
            startActivityAndWait()
        }
    }
}
```

基准输出会包含选定 category、各 component、total、unselected 和 uncategorized 等指标。`Type.Battery` 可作为没有高精度 rail 时的较粗替代，并可用 `deviceBatteryHasMinimumCharge()` 预检。两种模式的统计口径不同，不能混在同一回归序列里。

CI 设备还需要固定系统镜像、充电控制、热状态和后台账号。功耗基准对环境比启动时间更敏感，单次结果不应直接触发发布阻断。

## API 35+ `PowerMonitor`

`SystemHealthManager.getSupportedPowerMonitors()` 返回设备公开的 monitor。没有 ODPM 支持时，公开文档规定回调可能得到空列表。`PowerMonitor` 分两类：

- `POWER_MONITOR_TYPE_MEASUREMENT`：直接测量的 rail，名称与含义由设备定义；
- `POWER_MONITOR_TYPE_CONSUMER`：某个子系统的能量消费者，可能直接来自 rail，也可能组合、拆分或建模。

monitor 的 index 在重启后不保证稳定。应用应在当前进程中按返回对象读取，不能把 index 持久化成设备协议。

下面的代码展示一次完整枚举和异步读取。它读取累计能量，不在回调里假设 monitor 名称。

```kotlin
val health = context.getSystemService(SystemHealthManager::class.java)

health.getSupportedPowerMonitors(executor) { monitors ->
    if (monitors.isEmpty()) {
        Log.i("PowerSample", "No power monitors on this device")
        return@getSupportedPowerMonitors
    }

    health.getPowerMonitorReadings(
        monitors,
        executor,
        object : OutcomeReceiver<PowerMonitorReadings, RuntimeException> {
            override fun onResult(result: PowerMonitorReadings) {
                monitors.forEach { monitor ->
                    val energyUws = result.getConsumedEnergy(monitor)
                    val timestampMs = result.getTimestampMillis(monitor)
                    Log.i(
                        "PowerSample",
                        "${monitor.name}: $energyUws uWs at $timestampMs ms"
                    )
                }
            }

            override fun onError(error: RuntimeException) {
                Log.e("PowerSample", "Power monitor read failed", error)
            }
        }
    )
}
```

`getConsumedEnergy()` 返回自启动以来的累计 `uWs`，重启后清零，并且同时包含插电与电池供电期间的能量。返回 `ENERGY_UNAVAILABLE` 时不能参与差分。时间戳使用 elapsed realtime 毫秒。

两次读数的窗口平均功率按下面的单位关系计算：

```text
averagePower_mW =
    (energy2_uWs - energy1_uWs) /
    (timestamp2_ms - timestamp1_ms)
```

因为 `1 uWs / 1 ms = 1 mW`，公式不需要额外的 1000 倍换算。两次读数必须来自同一 `PowerMonitor` 对象和同一次开机，时间差还要大于服务端缓存与设备采样周期。

### Android 17 的新鲜度与随机化

`PowerStatsService` 在 API 37 使用两组缓存：

- 普通调用方的最大缓存年龄是 20,000 ms；
- 持有 `ACCESS_FINE_POWER_MONITORS` 的调用方使用 fine 缓存，最大年龄是 250 ms。

`ACCESS_FINE_POWER_MONITORS` 是 `signature|privileged|development` 权限，并受 feature flag 控制。这里的 20 秒和 250 ms 是服务端允许的缓存年龄，不是硬件固定采样率。

读取返回前，服务还会调用 `IntervalRandomNoiseGenerator.addNoise()`。Android 17 的上下界是：

```text
low  = max(previousEnergyUws, currentEnergyUws - 10_000_000)
high = currentEnergyUws
```

`10_000_000 uWs` 等于 10 J。Beta 分布参数 `alpha=50`，样本偏向 high，并按调用 UID 在一次 refresh 周期内复用。这个算法既不是对称的 ±10%，也不能描述成固定 10 mWs 误差。源码在选择普通或 fine 缓存后都会经过该随机化步骤；fine 权限提高的是读数新鲜度，不能写成“完全无噪声”。

这项设计意味着应用不应拿 PowerMonitor 做毫秒级控制器。它适合受控窗口的累计能量对比；频繁轮询、相邻差分和跨设备固定阈值都容易放大缓存、随机化和硬件差异。

## `BatteryUsageStats` 是平台归因接口

`BatteryStatsManager.getBatteryUsageStats()` 返回按子系统和 UID 归因的结果，但该接口需要 `BATTERY_STATS`，权限级别是 `signature|privileged|development`。普通应用不能把它当作线上自助功耗 API。

Android 17 的服务端流程是：

```text
BatteryStatsManager
    -> IBatteryStats.getBatteryUsageStats()
    -> BatteryStatsService
    -> 必要时同步外部统计并 collectPowerStatsSamples()
    -> BatteryUsageStatsProvider
    -> BatteryUsageStats
```

这条流程中的 `BatteryStatsService` 会等待待办统计完成，检查数据是否过旧，必要时同步外部状态并采集 PowerStats 样本，再由 provider 生成结果。它和 Historian 共用 BatteryStats 数据源，但 Historian 解析的是 bugreport，不是对这项 Binder API 的简单转发。

### API 37 查询项的变化

旧资料常把 `BatteryUsageStatsQuery` 写成“五个 flag”，其中包括 `INCLUDE_POWER_MODELS`。Android 17 源码已经不符合这种说法：

- `includePowerModels()` 标记为 deprecated，方法体直接返回 builder，不再设置 flag；
- `powerProfileModeledOnly()` 也已 deprecated；
- builder 仍支持 battery history、process state、virtual UID、screen state、power state、累计统计和组件过滤；
- `accumulated()` 会组合 process、screen 和 power state 维度；
- `PowerStatsAggregator` 位于 `services/core/java/com/android/server/power/stats/processor/`，通过回放 BatteryStats history 聚合样本。

`BatteryConsumer.POWER_MODEL_POWER_PROFILE` 与 `POWER_MODEL_ENERGY_CONSUMPTION` 常量仍在类中，不能由此反推 `includePowerModels()` 仍会返回双列模型数据。阅读 API 演进时应同时检查 builder 实现和消费方。

## 归因模型的边界

Android 功耗统计通常混合两类输入：

- Power Profile：活动时间乘设备配置中的平均功率；
- Energy consumer / rail：由 Power Stats HAL 报告的累计能量，再按 UID 活动或硬件 attribution 分配。

`IPowerStats` AIDL 对 EnergyConsumer、EnergyMeter Channel 和 PowerEntity 做了区分：

| HAL 数据 | 语义 | 典型用途 |
|---|---|---|
| EnergyConsumer | 子系统自启动以来的累计能量，可带 UID attribution | framework 组件与 UID 归因 |
| EnergyMeter Channel | bus、sense resistor 或 rail 的累计能量 | ODPM、Perfetto、PowerMonitor measurement |
| PowerEntity state residency | 子系统各状态驻留时间、次数和最近进入时间 | 功耗模型与状态诊断 |

HAL 的能量单位是 `uWs`，时间戳基于启动时钟。Channel 名称和 subsystem 字符串对 framework 是 opaque，跨设备比较前必须建立设备自己的映射。

没有硬件数据时，估算模型仍可用于同设备、同版本的趋势比较。它的误差来自 `power_profile.xml`、活动时间统计和归因规则，报告里应明确写“estimated”。有 rail 数据时也不能把系统级能量无条件分给前台应用。

## A/B 功耗实验怎么做

### 固定测量边界

先定义起止事件，例如“首页首帧完成后开始，连续滚动 60 秒后停止”。两组实验都用相同的 trace section 或测试脚本标记边界。不要用手工观察电池百分比替代测量窗口。

### 控制环境

- 同一台设备、同一系统镜像和同一应用编译类型；
- 固定亮度、刷新率、音量、网络类型和信号条件；
- 记录电池温度、SoC 温度、充电状态与 Thermal throttling；
- 关闭自动更新、云同步和不相关账号，或在报告里保留它们的活动证据；
- 让两组测试使用相同的预热、缓存、登录和数据集状态。

### 处理顺序效应

连续运行十次 A 再运行十次 B，后半段更可能受到热状态和电量变化影响。更稳妥的方式是交错 A/B 顺序，运行间恢复到相近温度，并保留每次原始 trace 与结果。

### 同时保留三层证据

1. Macrobenchmark 或外部仪表给出窗口能量分布；
2. Perfetto 解释 CPU、GPU、WLAN 等 rail 和线程活动；
3. Batterystats/Historian 检查较长窗口里的 Wakelock、job、alarm 和后台归因。

若三层证据不一致，先查时间边界、系统噪声、缓存与单位，不要挑选最符合预期的一组数字。

## 版本演进

| 版本或时间点 | 变化 | 使用方式 |
|---|---|---|
| Android 5.0 / API 21 | Battery Historian 支持 Lollipop 及后续 bugreport | 用于历史事件与统计回看 |
| Android 10 / API 29 | Perfetto `android.power` 与 Power Stats HAL/ODPM 能力进入平台 | rail 是否有数据由设备硬件和 HAL 决定 |
| 2022 年 | Google Battery Historian 仓库归档 | 不再把它作为新项目的默认入口 |
| Android Studio Hedgehog | Power Profiler 展示 ODPM Power Rails | 官方高精度支持以 Pixel 6+ 为准 |
| AndroidX Benchmark 1.2.0 / 1.3.0 | `PowerMetric` 加入；随后增加设备能力检查 | API 29+，高精度结果仍是系统级 |
| Android 15 / API 35 | 公开 `PowerMonitor` 枚举与读取 API | 读取自启动累计能量 |
| Android 17 / API 37 | fine monitor 权限、新鲜度分级和查询实现可从正式 tag 验证；BatteryUsageStats 查询项继续演进 | 结论锚定 `android-17.0.0_r1` |

## 常见误读

### “Historian 某一行持续变色，所以它就是耗电来源”

色块表示活动或状态。能量结论还要结合归因统计、rail、线程或外部测量。

### “ODPM 是硬件计量，所以数值属于目标应用”

ODPM 量的是设备 rail。应用归因要借助受控场景、线程活动和 BatteryStats。

### “PowerMonitor 返回的是瞬时功率”

返回值是自启动累计 `uWs`。平均功率来自两个样本的能量差和时间差。

### “250 ms 表示 Android 17 每 250 ms 采一次硬件”

250 ms 是 fine 缓存的最大年龄。HAL 与硬件的内部采样方式由设备实现。

### “fine 权限会返回完全原始、无随机化的数值”

Android 17 的返回循环对两种缓存都调用有界随机化函数。fine 权限改变缓存选择和新鲜度。

### “Power Profiler 在不支持 ODPM 的设备上会自动给出等价估算”

设备可能只提供 battery capacity、charge 或 current；缺少 rail 时没有等价的高精度子系统能量。界面是否展示旧估算项还取决于 Studio 与设备版本，测试程序应显式检查能力。

## 源码与官方文档

- [Battery Historian 使用说明与维护状态](https://developer.android.com/topic/performance/power/battery-historian)
- [Batterystats 与 Battery Historian 采集步骤](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [Google Battery Historian 归档仓库](https://github.com/google/battery-historian)
- [Android Studio Power Profiler](https://developer.android.com/studio/profile/power-profiler)
- [Macrobenchmark PowerMetric API](https://developer.android.com/reference/androidx/benchmark/macro/PowerMetric)
- [Macrobenchmark 指标说明](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Android vitals 过度 Partial Wakelock 口径](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [Perfetto power 数据源](https://perfetto.dev/docs/data-sources/battery-counters)
- [Android 17 Perfetto PowerConfig](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/power/android_power_config.proto)
- [Android 17 Perfetto power rails SQL 模块](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/power_rails.sql)
- [Android 17 SystemHealthManager PowerMonitor 入口](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/health/SystemHealthManager.java)
- [Android 17 PowerMonitor 类型与设备边界](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerMonitor.java)
- [Android 17 PowerMonitorReadings 单位与时间戳](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerMonitorReadings.java)
- [Android 17 PowerStatsService 缓存与随机化](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java)
- [Android 17 IntervalRandomNoiseGenerator](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/IntervalRandomNoiseGenerator.java)
- [Android 17 BatteryStatsService](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java)
- [Android 17 BatteryUsageStatsQuery](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/BatteryUsageStatsQuery.java)
- [Android 17 PowerStatsAggregator](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/stats/processor/PowerStatsAggregator.java)
- [Android 17 Power Stats HAL AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl)
- [Power Stats HAL 官方说明](https://source.android.com/docs/core/power/power-stats-hal)

---

**延伸阅读**：[11.1 Android 功耗模型](../../part2-performance/ch11-power/01-power-model.md) · [11.2 App 耗电优化](../../part2-performance/ch11-power/02-app-power-optimization.md) · [11.5 WakeLock 机制与功耗分析](../../part2-performance/ch11-power/05-wakelock.md) · [14.1 Android Studio Profiler](01-as-profiler.md) · [15.5 线上性能监控](../ch15-methodology/05-online-monitoring.md)
