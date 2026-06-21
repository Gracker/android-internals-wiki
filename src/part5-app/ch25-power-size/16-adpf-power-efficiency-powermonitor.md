---

drafted_date: "2026-05-24"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-06-13"
last_verified_against: "Android Developers API reference + AOSP main 分支（PowerStatsService/StatsPullAtomCallbackImpl/IPowerStats.aidl）"
confidence: medium-high
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager.Session"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf"
  - type: official
    path: "https://source.android.com/docs/core/perf/performance-hint-api"
  - type: official
    path: "https://developer.android.com/reference/android/os/health/SystemHealthManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerMonitor"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerMonitorReadings"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/battery-counters"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerformanceHintManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/health/SystemHealthManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerMonitor.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerMonitorReadings.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsLogger.java"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/Channel.aidl"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl"
  - type: aosp
    path: "frameworks/base/core/java/android/os/IPowerStatsService.aidl"
  - type: report
    path: "DeepResearch/2026-06-13-android17-powerstats-service-statsd-pull-atoms.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [adpf, power-efficiency, powermonitor, power-rails, perfetto, power-optimization]
related_chapters: ["5.9", "11.2", "25.1", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "素材驱动/官方文档/AOSP 结构"
title: "ADPF Power Efficiency Mode 与 PowerMonitor 能耗验证"
chapter: "25.16"
section: "25.16"
status: finalized
drafted_by: "task2a-knowledge-gap"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_result: "fixed"
task2b_rework_date: "2026-06-13"
last_task2b_at: "2026-06-13T14:50:00+08:00"
reviewed_by: openclaw-task6
reviewed_date: 2026-06-13
task6_result: pass-light-edit
last_task6_at: 2026-06-13T16:18:11+08:00
last_task6_review_log: "logs/review/2026-06-13-16-review.md"
task6_review_notes: "2026-06-13 Task6 回炉复审(revisiting→reviewed): pass-light-edit。L1 修复见 review 日志；L2/L3/L4 无新增问题；Task9 已 auto-fixed；queue 无 pending；自动晋升 finalized。"

task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-13"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-13T15:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-13-15-deep-review.md"
task9_review_notes: "2026-06-13 Task9 深度技术复审: auto-fixed。P0 1 / P1 1 / P2 1；已修复 SessionMode 枚举、headroom 版本与返回值边界、FMQ/版本演进表，回到 Task6 复审。"
last_task9_autofix_at: "2026-06-13"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
task2b_state: "fixed"
last_task9_audit: 2026-06-13
finalized_date: "2026-06-13"
finalized_by: "openclaw-task6-auto-promote"
---
# 25.16 ADPF Power Efficiency Mode 与 PowerMonitor 能耗验证

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 适用场景：Power Efficiency Mode 适合长期周期任务，不适合低延迟路径
- 🔹 ADPF Session：线程集合、生命周期、target duration 与实际耗时上报
- 🔹 系统语义：节能偏好不是收益承诺，需要同时看尾部耗时与能耗
- 🔹 PowerMonitor / SystemHealthManager：累计能耗读数、monitor 类型与读数差值
- 🔹 Perfetto power rails：用 trace 交叉验证能耗窗口、CPU 频率与线程状态
- 🔹 实验设计与线上灰度：A/B 对照、单位任务能耗、热状态和设备分桶
- 🔹 OEM 差异、Thermal API 联合治理与降级策略

### 扩展（可选深入）

- 🔸 游戏帧循环与后台计算的策略差异
- 🔸 PowerMonitor 与 Android Studio Power Profiler 数据口径
- 🔸 PowerMonitorReadings 与 Perfetto power rails 一致性待验证

## 适用场景：什么时候该把线程标成节能优先

Power Efficiency Mode 的前提是工作有稳定周期，并且业务结果不要求最短延迟。线程在 target duration 之前完成即可，系统有空间把它安排到更省电的执行形态。

| 场景 | 是否适合 | 判断依据 |
| --- | --- | --- |
| 后台批量压缩、日志归档、离线索引 | 适合 | 任务时间较长，吞吐稳定，允许几十毫秒到秒级弹性 |
| 本地模型批处理、照片批量转码、媒体库扫描 | 适合灰度 | 有固定 batch，可用单位任务能耗和 P90 耗时同时验收 |
| 游戏主循环、相机预览滤镜、低延迟音频 | 谨慎 | 有周期性，但 deadline 紧；默认应优先稳定帧耗时和低延迟 |
| 输入响应、点击后首屏展示、滚动帧提交 | 不适合 | 用户感知延迟优先级高，节能 hint 容易带来 P95 / P99 退化 |
| 一次性网络请求、偶发 JSON 解析 | 不适合 | 缺少稳定周期，创建 session 和上报成本会污染收益 |

判断顺序很简单：先问这段工作是否能定义周期，再问周期是否有余量，随后确认线程是否稳定。三项有一项不成立，Power Efficiency Mode 通常不是第一选择。

## ADPF Session 的线程集合与生命周期

`PerformanceHintManager.Session` 表示一组共同完成同一类工作的 Linux 线程。session 中的线程应是 long-lived，不适合动态创建、销毁；创建 session 时传入初始 target duration，每个周期用 `reportActualWorkDuration()` 上报实际耗时。

这几个 API 的分工要分开：

- `createHintSession(int[] tids, long initialTargetWorkDurationNanos)`: 创建 session，`tids` 必须属于当前进程，目标耗时必须为正；设备不支持时可能返回 `null`。
- `setThreads(int[] tids)`: 替换 session 的线程列表，不是在原列表上追加；AOSP 注释还说明它不是 oneway 调用，不应放到热路径高频执行。
- `updateTargetWorkDuration(long)`: 只在目标周期改变时调用，例如刷新率、batch 大小或业务 deadline 变化。
- `reportActualWorkDuration(long)` / `reportActualWorkDuration(WorkDuration)`: 周期结束后上报实际耗时，时间基准按 `SystemClock.uptimeNanos()` 理解。
- `close()`: 释放 session；不要把 close 当暂停开关，下一轮长期工作重新创建 session。

Power Efficiency Mode 对应的公开方法是 `setPreferPowerEfficiency(boolean)`，API reference 标注 Added in API level 35。AOSP main 中同名方法调用 native 层 `nativeSetPreferPowerEfficiency()`，注释说明它表达“这些线程可以安全地偏向能效而不是性能”。

这段代码展示固定 worker 的组织方式。重点看 tid 采集、session 创建、节能偏好和周期上报的位置；生产代码还要补错误处理、埋点、灰度开关和 API 版本判断。

```kotlin
@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
class PowerEfficientBatchWorker(
    context: Context,
    private val targetDurationNanos: Long,
) : Closeable {
    private val appContext = context.applicationContext
    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "pe-batch-worker")
    }
    private val dispatcher = executor.asCoroutineDispatcher()
    private var session: PerformanceHintManager.Session? = null

    suspend fun start() = withContext(dispatcher) {
        val manager = appContext.getSystemService(PerformanceHintManager::class.java)
        val tid = Process.myTid()
        session = manager?.createHintSession(intArrayOf(tid), targetDurationNanos)
        session?.setPreferPowerEfficiency(true)
    }

    suspend fun runCycle(block: suspend () -> Unit) = withContext(dispatcher) {
        val start = SystemClock.uptimeNanos()
        block()
        val actual = SystemClock.uptimeNanos() - start
        session?.reportActualWorkDuration(actual)
    }

    override fun close() {
        session?.close()
        session = null
        dispatcher.close()
        executor.shutdown()
    }
}
```

这段封装只把一个固定 worker 放进 session。多线程 batch 也能做，但要把 worker 数量控制在小范围内，并在线程全部启动后一次性登记 tid。默认 `Dispatchers.IO` 这类弹性线程池不适合直接接入，原因是 tid 会随挂起恢复和阻塞扩容变化；相关边界见 25.11 节。

## Power Efficiency Mode 的系统语义

`setPreferPowerEfficiency(true)` 表达的是调度偏好，不承诺具体 CPU 频点、大小核选择、GPU 频率或能耗下降比例。基本模型是：App 提供工作目标和实际耗时，系统结合 SoC 与热设计决定如何使用这些 hint。

发布时要把三层边界写清楚：

- API 边界：`PerformanceHintManager` 从 API 31 开始可用，`setThreads()` API reference 标注 API 34，`setPreferPowerEfficiency()` 标注 API 35。编译期、运行期和灰度数据都要检查，不按系统版本硬断言收益。
- 系统边界：hint 会进入系统的性能提示路径，后续行为受 Power HAL、调度器、CPUfreq、thermal throttling 和 OEM 策略影响。
- 业务边界：节能 hint 可能拉长尾部耗时。验收时要同时看 P50 / P90 / P99 耗时、单位任务能耗和热状态。

因此，Power Efficiency Mode 更像“把 deadline 余量交给系统使用”。如果业务没有余量，把线程标成节能优先只会让问题从平均耗时转移到尾部耗时。

## PowerMonitor 与 SystemHealthManager 读数模型

Android 15（API 35）新增的 `PowerMonitor` / `PowerMonitorReadings` 让 App 能按设备提供的 monitor 读取累计能耗。入口在 `SystemHealthManager`：先调用 `getSupportedPowerMonitors()` 拿到列表，再把列表传给 `getPowerMonitorReadings()`，结果通过 `OutcomeReceiver<PowerMonitorReadings, RuntimeException>` 返回。

AOSP main 中 `SystemHealthManager.getSupportedPowerMonitors()` 的注释把 monitor 分成 raw ODPM rails 和 modeled energy consumers；如果设备不支持 ODPM，方法返回空列表。`getPowerMonitorReadings()` 通过 PowerStats service 取指定 monitor 的累计读数，失败时走 `onError()`。

`PowerMonitor` 有两类类型：

- `POWER_MONITOR_TYPE_CONSUMER`: 子系统或建模能耗消费者。它可能由多个 rail 组合而来，也可能代表共享 rail 的一部分，例如 Wi-Fi 与 Bluetooth 共用芯片供电时的模型拆分。
- `POWER_MONITOR_TYPE_MEASUREMENT`: 直接测量的电源轨。rail 名称和来源是设备特有的，不能跨设备用同名 rail 做绝对对比。

`PowerMonitorReadings.getConsumedEnergy(powerMonitor)` 返回自启动以来的累计能耗，单位是 microwatt-seconds（μWs），不跨重启保留，包含电池供电和插电状态下的总能耗。`getTimestampMillis(powerMonitor)` 返回快照时刻，时间基准是 `SystemClock.elapsedRealtime()`。找不到对应 monitor 时，AOSP main 返回 `ENERGY_UNAVAILABLE = -1`。

这段代码展示一次实验窗口的读数差值。重点是用两次累计值相减，不要把单次累计值当成场景能耗。

```kotlin
@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
fun measurePowerWindow(
    context: Context,
    monitors: List<PowerMonitor>,
    executor: Executor,
    onMeasured: (Map<String, Long>) -> Unit,
    block: () -> Unit,
) {
    val shm = context.getSystemService(SystemHealthManager::class.java)
        ?: return onMeasured(emptyMap())

    fun read(consumer: (PowerMonitorReadings) -> Unit) {
        shm.getPowerMonitorReadings(
            monitors,
            executor,
            object : OutcomeReceiver<PowerMonitorReadings, RuntimeException> {
                override fun onResult(result: PowerMonitorReadings) = consumer(result)
                override fun onError(error: RuntimeException) {
                    onMeasured(emptyMap())
                }
            },
        )
    }

    read { before ->
        block()
        read { after ->
            val delta = monitors.associate { monitor ->
                val start = before.getConsumedEnergy(monitor)
                val end = after.getConsumedEnergy(monitor)
                val value = if (start >= 0 && end >= start) end - start else -1L
                monitor.name to value
            }
            onMeasured(delta)
        }
    }
}
```

这段示意代码只适合说明读数关系。实测时还要把异步回调、任务执行和时间窗口做成串行状态机，避免 before / after 窗口覆盖到无关工作；线上路径不要高频读取所有 monitor。

## Perfetto power rails 作为交叉验证通道

Perfetto 的 power rails 与 `PowerMonitor` 底层都依赖设备提供的 power stats 能力。Perfetto 文档说明，power rail counter 的存在和分辨率取决于设备厂商；平台侧通过 Android `IPowerStats` HAL 轮询获取数据。

最小采集配置里，Perfetto 使用 `android.power` 数据源，并在 `android_power_config` 中打开 `collect_power_rails`。同时采 CPU frequency、sched 和自定义 trace marker，才能把节能 hint 窗口、线程运行、频率变化和 rail 能耗放到同一条时间线上。

```protobuf
buffers: {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources: {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 250
      collect_power_rails: true
    }
  }
}

data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "power/cpu_frequency"
      atrace_categories: "app"
      atrace_apps: "com.example.app"
    }
  }
}
```

这份配置只能保证请求采集，不能保证设备一定提供 rail 数据。拿到 trace 后，先确认 power rail 轨道是否存在，再把 `Trace.beginSection("pe_batch_cycle")` 标记的工作窗口与 CPU frequency、thread state、thermal status 对齐。只看电池百分比或单次电流值，很容易把充电状态、屏幕亮度、网络波动和后台任务混进结论。

## 实验设计：同时看耗时和单位任务能耗

Power Efficiency Mode 的验收对象不是“是否更省电”这一句泛化判断，而是同一个工作负载在同一设备、同一温度起点、同一数据量下的单位任务能耗。

建议把实验拆成 A / B 两组：

| 维度 | A 组 | B 组 |
| --- | --- | --- |
| ADPF session | 固定 worker + 周期上报 | 固定 worker + 周期上报 + `setPreferPowerEfficiency(true)` |
| 工作负载 | 同一批任务、同一输入数据、同一 batch size | 与 A 组一致 |
| 耗时指标 | P50 / P90 / P99 周期耗时、超 deadline 比例 | 与 A 组一致 |
| 能耗指标 | `ΔμWs / 完成任务数`，按 monitor 分列 | 与 A 组一致 |
| 温控指标 | 起始热状态、结束热状态、throttling 次数 | 与 A 组一致 |

判断规则建议写成门禁，而不是写成单一收益数：

- P90 / P99 周期耗时不能超过业务阈值，超 deadline 比例不能上升。
- 单位任务能耗要下降到超过测量噪声的幅度；rail 数据波动大时，延长测试窗口或增加重复次数。
- 热状态不能更早进入 throttling；长时任务至少跑到温机状态再判断。
- 结果按设备型号、SoC、系统版本、刷新率、充电状态和温度起点分桶，不把 Pixel 上的 rail 名称或收益外推到 OEM 设备。

如果只能拿到 `PowerMonitor` 空列表，实验仍可继续，但结论要降级：用 Perfetto power rails、Android Studio Power Profiler、BatteryStats、CPU time 和任务耗时做旁证，不写 API 读数收益。

## 线上灰度与指标设计

线上灰度不应把 `PowerMonitor` 当作高频采样接口。它是异步读数 API，返回的是累计能耗，设备支持度也不一致。线上更稳的做法是把节能 hint 当成实验变量，采集轻量业务指标，再用实验室 power rails 做解释。

灰度字段建议至少包含这些维度：

- hint 配置：是否开启 Power Efficiency Mode、target duration、session 线程数、任务类型。
- 工作结果：完成任务数、单任务耗时、P50 / P90 / P99、取消率、失败率。
- 设备环境：机型、SoC、系统版本、刷新率、充电状态、热状态、前后台状态。
- 资源旁证：CPU time、线程运行时间、任务排队时间、后台执行约束命中情况。
- 实验标签：灰度批次、开关版本、回滚原因、异常设备黑名单。

上线策略按“耗时不退化，再看能耗收益”执行。只要尾部耗时或失败率退化，先回滚节能 hint；不要为了平均能耗下降牺牲用户可感知路径。

## OEM 差异与降级策略

`PowerMonitor` 与 Perfetto power rails 都绕不开 OEM 实现差异。设备可能返回空 monitor 列表，也可能只提供少量 modeled consumer；同名 rail 在不同设备上也可能对应不同硬件范围。`PowerMonitor` 源码还说明 monitor index 不保证跨重启稳定，不应持久化 index。

降级策略按三档处理：

| 设备能力 | 可用验证方式 | 结论口径 |
| --- | --- | --- |
| `PowerMonitor` 列表完整，Perfetto 有 rail 轨道 | API 差值 + Perfetto 时间线交叉验证 | 可写单位任务能耗变化，但限定设备和场景 |
| `PowerMonitor` 为空，Perfetto 有部分 rail | Perfetto rail + CPU frequency + thermal + 任务耗时 | 写实验室旁证，不写 API 闭合验证 |
| API 与 Perfetto 都缺 rail | BatteryStats / Power Profiler / CPU time / 业务耗时 | 只写功耗趋势和风险，不能写 rail 级结论 |

Power Efficiency Mode 的开关也要做设备级降级。灰度中发现某些型号 P99 耗时退化、温控更早升档或任务失败率上升，应按型号关闭，而不是全局下线整套能力。

## 与 Thermal API 的联合治理

Power Efficiency Mode 和 Thermal API 处理的是同一类长期负载问题的两个阶段：前者在任务开始时表达能效偏好，后者在设备热状态变化时调整策略。`PowerManager.addThermalStatusListener()` 可监听热状态变化，`getCurrentThermalStatus()` 可读取当前状态；热管理机制详见 5.9 节与 11.2 节。

组合策略可以按热状态分层：

- 常温：按实验得到的 target duration 与 batch size 执行，开启 `setPreferPowerEfficiency(true)`。
- 轻度升温：增大 batch 间隔或降低并发线程数，保留任务吞吐。
- 中度升温：暂停非必要 batch，降低后台同步频率，避免继续推高热状态。
- 严重升温：关闭非关键长时任务，只保留用户可感知路径和系统要求任务。

上述策略要和业务 SLA 绑定。照片备份、日志压缩、离线索引可以主动让路；实时通话、导航、录制不能只按能耗目标降级。

## 常见误区

### 误区一：`setPreferPowerEfficiency(true)` 等于省电收益

它只表达调度偏好。没有 PowerMonitor、Perfetto、BatteryStats 或 Power Profiler 的数据，就不能写成收益。正确表述是“启用后在某设备、某场景、某测试窗口内单位任务能耗下降”。

### 误区二：把输入和渲染线程也标成节能优先

输入、主线程、RenderThread、音视频低延迟线程一般不适合默认节能优先。它们的尾部延迟更敏感，错误 hint 会把用户感知问题放大。图形、游戏和相机相关周期任务如果要接入，应先按 5.9 和 25.11 的 session 边界验证线程身份。

### 误区三：PowerMonitor 的 rail 名称能跨设备对比

`POWER_MONITOR_TYPE_MEASUREMENT` 的 rail 是设备特有的，同名不代表同一硬件范围。跨设备只能比同一业务指标和同类设备分桶结果，不要把 rail 绝对值拉到同一张排行榜。

### 误区四：插电测试不影响结论

Perfetto 文档说明，电池 counter 在 USB 插电时会反映充电电流，实验室功耗测试要隔离充电状态。Power rail counter 位于电池下游，受充电状态影响小一些，但测试仍要记录 USB、电量、屏幕亮度和温度起点。

## 扩展

### 游戏帧循环与后台计算的策略差异

游戏帧循环通常先保证帧 deadline，Power Efficiency Mode 只能用于确认有稳定余量的子线程，例如资源准备、后台 AI、低优先级物理预计算。后台计算的目标是吞吐和能耗平衡，更适合用较长 target duration、固定 batch 和节能 hint。

### PowerMonitor 与 Android Studio Power Profiler 数据口径

`PowerMonitorReadings` 返回 monitor 维度的累计 μWs；Perfetto power rails 提供 trace 时间线；Android Studio Power Profiler 更适合交互式分析 App 行为、系统事件和功耗趋势。三者可以互相佐证，但不要把采样频率、单位和归因范围混成同一个数字。

### Thermal 阈值需要设备实验

热状态进入高档位前主动降低 batch 并发，通常比等系统 throttling 后再恢复更可控。具体阈值要由设备实验给出，本节不写固定温度或固定收益。

### 待验证：PowerMonitorReadings 与 Perfetto power rails 一致性

[待验证] 当前缺少 Pixel 与至少一个 OEM 设备上的同窗对比数据。后续实验应在同一时间窗口内同时记录 `PowerMonitorReadings.getConsumedEnergy()` 差值、Perfetto power rails 差值、CPU frequency、thermal status 和任务计数，确认两类读数在同一设备上是否能互相解释。


## 扩展：系统层硬件协同设计架构

ADPF 的端到端效果不仅依赖应用侧代码，更依赖系统层的硬件感知能力。本节基于 AOSP android-16.0.0_r1 源码分析系统组件如何实现硬件协同。

> **版本限定**：本节源码锚点统一使用 `android-16.0.0_r1`。标注为"仅 main/master 可见"的内容已移出正文，不作为 AIW 结论。android-17.0.0_r1 中实现细节可能存在差异，但当前 AIW 最高只覆盖到 Android 17/API 37。

### Power HAL ML_ACC Boost：硬件加速器协同接口

**源码位置**: `hardware/interfaces/power/aidl/android/hardware/power/Boost.aidl` (android-16.0.0_r1)

`ML_ACC` boost 是 Power HAL 层为机器学习硬件加速器设计的协同接口。在 android-16.0.0_r1 的 `Boost.aidl` 中，`ML_ACC` 是枚举成员，位于 `INTERACTION`、`DISPLAY_UPDATE_IMMINENT` 之后，但 **没有显式数值**——实际值由 AIDL 编译器根据枚举位置自动分配：

```aidl
/** 
 * This boost indicates that the device is interacting 
 * with ML accelerator. 
 */
ML_ACC,
```

> ⚠️ 不要手写 `ML_ACC = 20` 或其他硬编码常量。实际数值由对应 tag 的 AIDL 生成代码决定，跨版本可能不同。适配时引用枚举名 `Boost.ML_ACC`，不依赖数值。

该 boost 在 Android 16 的 framework 中暂未主动发送，但为 OEM 提供了与 NPU/GPU 硬件协同的标准化接口。手机厂商可在此实现芯片级优化，例如 CPU 预处理阶段增加 boost、AI 推理阶段动态调整时钟频率、后处理阶段释放资源。

### HintManagerService：系统层会话调度中心

**源码位置**: `frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java` (android-16.0.0_r1)

系统通过 HintManagerService 统一管理所有 ADPF 会话。核心职责包括：

- **会话生命周期管理**：维护 uid → token → session 的映射，处理 session 的创建、更新和清理。
- **CPU/GPU headroom 查询**：Android 16 的 `SystemHealthManager` 通过 `IHintManager` 转发到 Power HAL `getCpuHeadroom()` / `getGpuHeadroom()`。Java API 返回 0-100 的 headroom 数值或 `Float.NaN`，HAL 的 `CpuHeadroomResult` / `GpuHeadroomResult` 也只暴露 `globalHeadroom`，不提供负载、温度或频率明细。
- **版本感知调度**：根据 Power HAL 版本调整可用的 hint 数量和调度策略。

HintManagerService 的内部实现细节（如具体状态映射结构、清理间隔）随版本演进，应以对应 tag 的源码为准。本章不粘贴 main branch 特有的内部代码。

**版本感知的调度策略**：
- Power HAL V4：基础 hint session 支持。
- Power HAL V5：`createHintSessionWithConfig()`、`SessionTag`、`SessionMode.POWER_EFFICIENCY` 与 `getSessionChannel()` 支持。
- Power HAL V6：CPU/GPU headroom 查询，以及 `GRAPHICS_PIPELINE`、`AUTO_CPU`、`AUTO_GPU` session mode 支持。

### SessionTag 与 SessionMode：两个不同的 HAL 内部枚举

AOSP 中 **SessionTag** 和 **SessionMode** 是两个独立的 AIDL 枚举，定义在不同文件中，服务于不同层次。

**SessionTag**（`hardware/interfaces/power/aidl/android/hardware/power/SessionTag.aidl`，android-16.0.0_r1）：
```aidl
@VintfStability
enum SessionTag {
    OTHER = 0,
    SURFACEFLINGER = 1,
    HWUI = 2,
    GAME = 3,
    APP = 4,
    SYSUI = 5,
}
```

**SessionMode**（`hardware/interfaces/power/aidl/android/hardware/power/SessionMode.aidl`，android-16.0.0_r1）：
```aidl
@VintfStability
@Backing(type="int")
enum SessionMode {
    POWER_EFFICIENCY,
    GRAPHICS_PIPELINE,
    AUTO_CPU,
    AUTO_GPU,
}
```

关键区分：
- `GRAPHICS_PIPELINE` 属于 **SessionMode**，不是 SessionTag。SessionTag 中不包含 `GRAPHICS_PIPELINE`。
- SessionTag 和 SessionMode 都是 **Power HAL 内部**枚举，供系统服务（SurfaceFlinger、HWUI 等）向 Power HAL 传达调度意图。
- **普通 App 不直接选择 tag 或 mode**。公开 `PerformanceHintManager.createHintSession(int[], long)` 不暴露 tag/mode 选择参数。App 通过 `setPreferPowerEfficiency(true)` 表达能效偏好，由系统层根据会话特征映射到对应的 HAL tag/mode——不要建议业务代码直接选择 `SessionTag` 或 `GRAPHICS_PIPELINE`。

### 电源状态跟踪与统计

系统通过 `FrameworkStatsLog` 跟踪全局 ADPF 使用状态，包括最大并发会话数、最大线程数、能效优先会话数和目标持续时间分布。这些统计用于系统健康监控和 OEM 调优，不直接暴露给 App。

### FMQ (Fast Message Queue) 优化

`android-16.0.0_r1` 的 `HintManagerService` 中可见系统组件接入 ADPF 的调试开关；这两个属性在 `android-15.0.0_r1` 已存在，不能当成 Android 16 新增公开 API：
- `debug.sf.enable_adpf_cpu_hint`：SurfaceFlinger CPU hint 开关
- `debug.hwui.use_hint_manager`：HWUI hint manager 开关

Android 15 起 Power HAL AIDL 已提供 `getSessionChannel()`，Android 16 的服务端增加 FMQ 支持状态统计。它们都属于系统级调试和 OEM 适配面，不直接暴露给 App。



### PowerStatsService 完整数据通路（系统服务 → IPowerStats HAL → statsd）

25.16 节「PowerMonitor 与 SystemHealthManager 读数模型」描述了 App 端如何通过 `SystemHealthManager.getPowerMonitorReadings()` 拿到 ODPM rails 与 EnergyConsumer 累计读数；本节补齐该链路在系统服务层的实现细节，作为 2026-06-13 端侧 AI 资源调度报告（覆盖 ADPF + Power HAL 应用层）到硬件层的下行补充。

**入口分发与缓存阈值**（`frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java` L540-606）：

`IPowerStatsService.Stub.getPowerMonitorReadings()` 只做参数校验后 `getHandler().post(...)`，HAL 调用不占用 Binder 线程。`getPowerMonitorReadingsImpl` 走 **30 秒缓存**：`MAX_POWER_MONITOR_AGE_MILLIS = 30_000`（同文件 L52）。如果 30 秒内已读过的 monitor（`mPowerMonitorStates[].timestampMs` 差值）则直接复用；超阈值时才调 `updateEnergyConsumers()` / `updateEnergyMeasurements()` 真正走 HAL。

**异步路径与噪声注入**（同文件 L608-678）：

`LocalService` 暴露 `getEnergyConsumedAsync` / `getStateResidencyAsync` / `readEnergyMeterAsync` 三个 `CompletableFuture` 入口。**关键设计**：`getEnergyConsumedAsync` 在 HAL 返回 `null` 或长度不匹配时，**走 `Slog.wtf` 级别告警但仍用部分数据 `future.complete(results)` 兜底**（L673-675），与 statsd pull 路径的 `PULL_SKIP` 语义不同——Binder 调用方拿到「数据可能不完整」是设计意图，避免 App 端 `getPowerMonitorReadings` 因 HAL 瞬时失败而 crash；statsd pull 路径则是「本次跳过，下次再来」。

能量计算注入 `IntervalRandomNoiseGenerator` Beta 分布噪声（`INTERVAL_RANDOM_NOISE_GENERATION_ALPHA = 50`、`MAX_RANDOM_NOISE_UWS = 10_000_000` 即 10 MJ，约 1W 设备 2.78 小时功耗上限），避免多 App 同步轮询撞峰时上报一致值（k-anonymity 隐私保护）。

**statsd pull atom 注册**（`frameworks/base/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java`）：

`StatsPullAtomCallbackImpl` 在 `StatsPullAtomCallbackImpl(Context, PowerStatsInternal)` 构造时（L150-175）一次性注册两个 atom：

- `FrameworkStatsLog.ON_DEVICE_POWER_MEASUREMENT` —— 对应 `IPowerStats.readEnergyMeter`（ODPM 实测 rail）
- `FrameworkStatsLog.SUBSYSTEM_SLEEP_STATE` —— 对应 `IPowerStats.getStateResidency`（State 驻留时间）

**`STATS_PULL_TIMEOUT_MILLIS = 2_000`**（L41）是 statsd 硬性窗口。`ConcurrentUtils.DIRECT_EXECUTOR`（L165）让 `onPullAtom` 在 statsd binder 线程同步执行，**避免排队时间被算进 2s 窗口**。`ON_DEVICE_POWER_MEASUREMENT` 关键过滤：`if (energyMeasurement.durationMs == energyMeasurement.timestampMs)` 才上报——HAL 在设备刚 boot 时把这两字段都置 0，等价于「累积能量为 0」的另一种表达。

**持久化层**（`PowerStatsLogger.java`）：

3 个 Handler 消息 `MSG_LOG_TO_DATA_STORAGE_BATTERY_DROP / LOW_FREQUENCY / HIGH_FREQUENCY` 写到 `/data/system/powerstats/` 下 6 个 `.pb` 文件（meter / meterCache / model / modelCache / residency / residencyCache）。`EnergyMeasurementUtils.adjustTimeSinceBootToEpoch(measurements, mStartWallTime)` 把 HAL 的 `CLOCK_BOOTTIME` 时间戳转换为 wall clock，便于跨重启对比；`*Cache.0` 后缀是 `AtomicFile` 临时文件，写入完成 rename 为正式文件，避免半写状态被读取。

**HAL 接口契约**（`hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl`）：

6 个方法（`@VintfStability` 稳定）：`getPowerEntityInfo` / `getStateResidency` / `getEnergyConsumerInfo` / `getEnergyConsumed` / `getEnergyMeterInfo` / `readEnergyMeter`。`Channel` parcelable 3 字段（`id` / `name` / `subsystem`），`EnergyMeasurement` 4 字段（`id` / `timestampMs` / `durationMs` / `energyUWs` μWs）。

**远程开关**：`KEY_POWER_MONITOR_API_ENABLED = "power_monitor_api_enabled"` device config 在 `mDeviceConfigListener` 监听下变化时调 `refreshFlags()`，可一键 disable 并清空 `mPowerMonitors` / `mPowerMonitorStates`（L624-635），给厂商回归测试提供不开销的 PowerMonitor API 关闭路径。

**反哺要点**：
1. App 不应假设 `getPowerMonitorReadings()` 实时调用 HAL；30s 阈值期间复用 `mPowerMonitorStates` 缓存
2. getEnergyConsumedAsync 偶发返回 null 是已知问题（见 PowerStatsService.java L515），线上要监控 `Slog.wtf` 频率而非直接报错
3. statsd pull atom 的 2s 超时是硬约束，HAL 异常时 `PULL_SKIP` 是正确行为；不能改用后台 executor 反而把 2s 用在排队上
4. PowerStats 数据是 `IPowerStats` AIDL `@VintfStability` 稳定接口，跨 Android 主版本兼容；vendor 端实现差异在 `Channel.name` 等设备特定字段上，跨设备对比前要先确认字段语义

> 本节源码锚点覆盖：`PowerStatsService.java`（L1-800+）、`StatsPullAtomCallbackImpl.java`（L1-175）、`PowerStatsLogger.java`（L1-120+）、`IPowerStatsService.aidl`、`PowerMonitor.java`、`IPowerStats.aidl`、`Channel.aidl`、`EnergyMeasurement.aidl`。深入分析见 `DeepResearch/2026-06-13-android17-powerstats-service-statsd-pull-atoms.md`。


### 版本演进总结

| Android 版本 | 系统层能力 | 硬件协同增强 |
|-------------|----------|-------------|
| Android 12 | ADPF v1 `PerformanceHintManager` / `createHintSession()` | CPU hint session 基础支持 |
| Android 14 | `setThreads()` 等 session 线程管理 API | 更完整的线程集合维护 |
| Android 15 | `setPreferPowerEfficiency()`、`PowerMonitor`、Power HAL `SessionTag` / `SessionConfig` 与 `getSessionChannel()` | 能效偏好和 monitor 读数进入公开验证链路 |
| Android 16 | `getCpuHeadroom()` / `getGpuHeadroom()`、`GRAPHICS_PIPELINE` / `AUTO_CPU` / `AUTO_GPU` SessionMode | CPU/GPU headroom 查询与图形管线自动计时模式 |

**硬件协同要点**：
1. SessionTag 和 SessionMode 是 HAL 内部概念，App 通过公开 ADPF API（`createHintSession`、`reportActualWorkDuration`、`setPreferPowerEfficiency`）表达意图，不直接选择 tag/mode。
2. `ML_ACC` boost 的数值由 AIDL 编译器生成，适配代码引用枚举名而非硬编码常量。
3. 利用 Perfetto 验证系统对 ADPF hint 的实际调度行为，而不是假设 hint 一定生效。
4. OEM 可基于 Boost、SessionTag 和 SessionMode 实现芯片级优化，但这些优化在不同设备上不可假设一致。

## 小结

ADPF Power Efficiency Mode 的价值在于把长期周期任务的 deadline 余量告诉系统。`setPreferPowerEfficiency(true)` 负责表达偏好，`PowerMonitorReadings` 和 Perfetto power rails 负责验证，线上灰度负责守住尾部耗时和失败率。没有稳定线程、稳定周期和能耗数据，这个能力就不该写成优化结论。
