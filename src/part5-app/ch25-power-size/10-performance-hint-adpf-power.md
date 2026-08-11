---

drafted_date: "2026-05-24"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-08-08"
last_verified_against: "Android Developers API reference + AOSP android-17.0.0_r1（PowerStatsService/StatsPullAtomCallbackImpl/IPowerStats.aidl/Power HAL AIDL）"
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
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/Boost.aidl"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/SessionTag.aidl"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/SessionMode.aidl"
  - type: report
    path: "DeepResearch/2026-06-13-android17-powerstats-service-statsd-pull-atoms.md"
  - type: report
    path: "DeepResearch/2026-07-07-android17-power-stats-hal-impl-variations.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: structure
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [adpf, power-efficiency, powermonitor, power-rails, perfetto, power-optimization]
related_chapters: ["5.9", "11.2", "25.1", "25.16"]
consolidated_from:
  - "src/part5-app/ch25-power-size/11-adpf-coroutine-thread-migration.md"
  - "src/part5-app/ch25-power-size/21-performance-hint-manager-practice.md"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "素材驱动/官方文档/AOSP 结构"
title: "PerformanceHintManager 与 ADPF 能效验证"
chapter: "25.10"
section: "25.10"
status: finalized
drafted_by: "task2a-knowledge-gap"
pipeline_stage: finalized
task6_state: reviewed
task9_state: "reviewed"
task2b_result: "fixed"
task2b_rework_date: "2026-06-13"
last_task2b_at: "2026-06-13T14:50:00+08:00"
reviewed_by: hermes-aiw-review-finalize-apply
reviewed_date: 2026-08-02
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
finalized_date: "2026-08-02"
finalized_by: "hermes-aiw-review-finalize-apply"
last_idle_audit_at: "2026-08-08T10:35:09+08:00"
last_idle_audit_run_id: "20260808-103509-idle-audit-13a21d51"
last_idle_audit_result: "pass-no-body-change"
last_idle_audit_log: "logs/audit/2026-08-08-20260808-103509-idle-audit-13a21d51-idle-audit.md"
last_idle_audit_notes: "2026-08-08 idle-audit: finalized 章节抽检通过；未发现 Android 18/API38 越界结论、待验证残留、来源缺口或需降级问题。正文不改动，仅刷新 idle-audit / last_verified 元数据。"
previous_rework_at: "2026-07-31T17:35:08+08:00"
previous_rework_run_id: "20260731-173508-rework-13a21d51"
previous_rework_notes: "2026-07-31 rework: 当时曾尝试修正延伸阅读摘要中的 PowerStatsService 缓存阈值矛盾，但把 r1 普通路径误写为过大的缓存年龄；2026-08-04/08-06 idle-audit 已按 android-17.0.0_r1 一手源码统一更正为普通 20_000 ms / 高精度 250 ms。PowerMonitor/Perfetto 一致性实验问题已在 2026-08-02 rework/finalize 闭合。"
last_rework_verify_at: "2026-08-02T09:36:04+08:00"
last_rework_at: "2026-08-02T09:36:04+08:00"
last_rework_run_id: "20260802-093547-rework-13a21d51"
last_rework_result: "ready-for-review"
last_rework_notes: "2026-08-02 rework: 处理一致性实验标记与 source 覆盖不足；将 PowerMonitorReadings 与 Perfetto 一致性从未闭合结论改为设备同窗验证方案，补入 2026-07-07 PowerStats HAL OEM 差异报告为 source，并将章节状态退回 ready-for-review 供 Task6 复审。"
last_review_finalize_at: "2026-08-02T10:05:51+08:00"
last_review_finalize_run_id: "20260802-100551-c614c850"
last_review_finalize_notes: "Hermes AIW review-finalize: 复核 2026-08-02 rework 已闭合 PowerMonitor/Perfetto 一致性实验问题；将 AOSP 锚点从 main/android-16 表述收敛到 android-17.0.0_r1，并补正 Android 17 SessionMode 枚举；正文无 Android 18/API38 越界结论。"
---
# PerformanceHintManager 与 ADPF 能效验证

`PerformanceHintManager` 接收周期性工作的线程集合、目标时长和实际时长，不提供“加速开关”。Android 17 没有新增另一套公开 Java 接口；这一版的重点是把 Java、NDK、协程线程身份、能效模式和 PowerMonitor 验证放在同一个工作流中。

## API 版本与调用路径

| API level | Java | NDK |
| ---: | --- | --- |
| 31 | 创建 Session、更新 target、上报单值 actual、关闭 | — |
| 33 | 延续基础能力 | 基础 manager/session API |
| 34 | `setThreads()` | `APerformanceHint_setThreads()` |
| 35 | `setPreferPowerEfficiency()`、`WorkDuration` | 能效模式与分项时长 |
| 36 | 无对应新增 Java Session 方法 | creation config、feature probing、graphics pipeline、Java Session 借用 |
| 37 | 延续现有公开能力 | `android-17.0.0_r1` 未新增 API 37 函数 |

Java 调用经过 framework JNI、native client、`HintManagerService` 和 Power HAL。高频 target/actual 更新在设备支持时可走 FMQ，失败或未建立 channel 时回退 Binder，因此不能笼统写成“每帧必定一次 Binder”。系统还会根据 UID 进程状态暂停/恢复 Session；应用调用成功不代表 HAL 一定采用每条数据。

## 适用场景：什么时候该把线程标成节能优先

Power Efficiency Mode 的前提是工作有稳定周期，并且业务结果不要求最短延迟。线程在 target duration 之前完成即可，系统有空间把它安排到更省电的执行形态。

| 场景 | 是否适合 | 判断依据 |
| --- | --- | --- |
| 后台批量压缩、日志归档、离线索引 | 适合 | 任务持续时间和吞吐较稳定，目标耗时留有余量 |
| 本地模型批处理、照片批量转码、媒体库扫描 | 适合灰度 | 有固定 batch，可用单位任务能耗和 P90 耗时同时验收 |
| 游戏主循环、相机预览滤镜、低延迟音频 | 谨慎 | 有周期性，但 deadline 紧；默认应优先稳定帧耗时和低延迟 |
| 输入响应、点击后首屏展示、滚动帧提交 | 不适合 | 用户感知延迟优先级高，节能 hint 容易带来 P95 / P99 退化 |
| 一次性网络请求、偶发 JSON 解析 | 不适合 | 缺少稳定周期，无法持续提供有意义的目标耗时与实际耗时 |

判断顺序很简单：先问这段工作是否能定义周期，再问周期是否有余量，随后确认线程是否稳定。三项有一项不成立，Power Efficiency Mode 通常不是第一选择。

## ADPF Session 的线程集合与生命周期

`PerformanceHintManager.Session` 表示一组共同完成同一类工作的 Linux 线程。session 中的线程应是 long-lived，不适合动态创建、销毁；创建 session 时传入初始 target duration，每个周期用 `reportActualWorkDuration()` 上报实际耗时。

这几个 API 的分工要分开：

- `createHintSession(int[] tids, long initialTargetWorkDurationNanos)`: 创建 session，`tids` 必须属于当前进程，目标耗时必须为正；设备不支持时可能返回 `null`。
- `setThreads(int[] tids)`: 替换 session 的线程列表，不是在原列表上追加；AOSP 注释还说明它不是 oneway 调用，不应放到热路径高频执行。
- `updateTargetWorkDuration(long)`: 只在目标周期改变时调用，例如刷新率、batch 大小或业务 deadline 变化。
- `reportActualWorkDuration(long)` / `reportActualWorkDuration(WorkDuration)`: 周期结束后上报实际耗时，时间基准按 `SystemClock.uptimeNanos()` 理解。
- `close()`: 释放 session；不要把 close 当暂停开关，下一轮长期工作重新创建 session。

Power Efficiency Mode 对应的公开方法是 `setPreferPowerEfficiency(boolean)`，API reference 标注 Added in API level 35。AOSP `android-17.0.0_r1` 中同名方法调用 native 层 `nativeSetPreferPowerEfficiency()`，注释说明它表达“这些线程可以安全地偏向能效而不是性能”。

下面的代码展示固定工作线程的组织方式，重点是在线程自身采集 tid、串行访问 session，并在周期结束后上报实际耗时。

```kotlin
@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
class PowerEfficientBatchWorker(
    context: Context,
    private val targetDurationNanos: Long,
) {
    private val appContext = context.applicationContext
    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "pe-batch-worker")
    }
    private val dispatcher = executor.asCoroutineDispatcher()
    private var session: PerformanceHintManager.Session? = null

    init {
        require(targetDurationNanos > 0L)
    }

    suspend fun start(): Boolean = withContext(dispatcher) {
        check(session == null) { "Session has already started" }
        val manager = appContext.getSystemService(PerformanceHintManager::class.java)
        val tid = Process.myTid()
        session = manager?.createHintSession(intArrayOf(tid), targetDurationNanos)
        session?.setPreferPowerEfficiency(true)
        session != null
    }

    suspend fun runCycle(block: suspend () -> Unit) = withContext(dispatcher) {
        checkNotNull(session) { "Call start() before runCycle()" }
        val start = SystemClock.uptimeNanos()
        try {
            block()
        } finally {
            val actual = SystemClock.uptimeNanos() - start
            session?.reportActualWorkDuration(actual)
        }
    }

    suspend fun close() {
        withContext(dispatcher) {
            session?.close()
            session = null
        }
        dispatcher.close()
        executor.shutdown()
    }
}
```

`PerformanceHintManager.Session` 不是线程安全对象，因此示例把创建、上报与关闭都放在同一个调度器中。`finally` 保证失败周期也会上报已经消耗的时间；业务仍需单独记录异常结果。多线程 batch 可以登记多个 tid，但要在线程身份稳定后再创建或更新 session。`Dispatchers.IO` 这类弹性线程池会在不同 tid 之间迁移协程，不适合作为固定线程集合直接登记；相关边界在下一节继续说明。

### 协程迁移与 TID 所有权

Session 绑定 Linux TID，即 `Process.myTid()`，不是 `Thread.currentThread().id`。`Dispatchers.Default`、`Dispatchers.IO` 和 `limitedParallelism()` 都不承诺同一协程挂起恢复后仍在同一个 TID 上。常见错误是在某个 `suspend` 函数开头登记当前线程，恢复后却由另一工作线程执行；系统收到的线程集合与真实负载随即分离。

适合 ADPF 的协程负载应由单线程或小规模固定 `Executor` 承载，在线程启动后采集 TID；一个周期的业务块不要在中途切换 dispatcher。Session 创建、`setThreads()`、target 更新、actual 上报和 `close()` 由同一 owner 串行执行。线程池重建时，API 31—33 关闭旧 Session 并重建；API 34+ 可在生命周期边界完整替换线程数组，但不能每周期更新。

API 36 的 `APerformanceHint_borrowSessionFromJava()` 可以让 JNI 代码借用 Java Session，避免重复创建。native 侧不能关闭借用指针，Java 对象关闭后也不能继续使用。没有稳定周期、稳定线程和可信 actual 测量时，应先处理并发、任务队列与生命周期，不应强行套 ADPF。

## Power Efficiency Mode 的系统语义

`setPreferPowerEfficiency(true)` 表达的是调度偏好，不承诺具体 CPU 频点、大小核选择、GPU 频率或能耗下降比例。基本模型是：App 提供工作目标和实际耗时，系统结合 SoC 与热设计决定如何使用这些 hint。

发布时要把三层边界写清楚：

- API 边界：`PerformanceHintManager` 从 API 31 开始可用，`setThreads()` API reference 标注 API 34，`setPreferPowerEfficiency()` 标注 API 35。编译期、运行期和灰度数据都要检查，不能只按系统版本推断收益。
- 系统边界：hint 会进入系统的性能提示路径，后续行为受 Power HAL、调度器、CPUfreq、thermal throttling 和 OEM 策略影响。
- 业务边界：节能 hint 可能拉长尾部耗时。验收时要同时看 P50 / P90 / P99 耗时、单位任务能耗和热状态。

因此，Power Efficiency Mode 更像“把 deadline 余量交给系统使用”。如果业务没有余量，把线程标成节能优先只会让问题从平均耗时转移到尾部耗时。

## PowerMonitor 与 SystemHealthManager 读数模型

Android 15（API 35）新增的 `PowerMonitor` / `PowerMonitorReadings` 让 App 能按设备提供的 monitor 读取累计能耗。两个入口都是异步方法：`getSupportedPowerMonitors(executor, callback)` 返回支持列表，`getPowerMonitorReadings(monitors, executor, outcomeReceiver)` 返回指定 monitor 的读数。回调执行器可以传 `null`，但此时回调线程由实现选择，应用代码通常应提供自己的执行器。

AOSP `android-17.0.0_r1` 中 `SystemHealthManager.getSupportedPowerMonitors()` 的注释把 monitor 分成 raw ODPM rails 和 modeled energy consumers；如果设备不支持 ODPM，公开 API 允许返回空列表。`getPowerMonitorReadings()` 通过 PowerStats service 取指定 monitor 的累计读数，不支持的 monitor 会通过 `onError()` 返回 `IllegalArgumentException`。

`PowerMonitor` 有两类类型：

- `POWER_MONITOR_TYPE_CONSUMER`: 子系统或建模能耗消费者。它可能由多个 rail 组合而来，也可能代表共享 rail 的一部分，例如 Wi-Fi 与 Bluetooth 共用芯片供电时的模型拆分。
- `POWER_MONITOR_TYPE_MEASUREMENT`: 直接测量的电源轨。rail 名称和来源是设备特有的，不能跨设备用同名 rail 做绝对对比。

`PowerMonitorReadings.getConsumedEnergy(powerMonitor)` 返回自启动以来的累计能耗，单位是 microwatt-seconds（μWs），不跨重启保留，包含电池供电和插电状态下的总能耗。`getTimestampMillis(powerMonitor)` 返回快照时刻，时间基准是 `SystemClock.elapsedRealtime()`。找不到对应 monitor 时，AOSP `android-17.0.0_r1` 返回 `ENERGY_UNAVAILABLE = -1`。

Android 17 r1 还规定了读数新鲜度和精度边界。普通调用方使用 `MAX_POWER_MONITOR_AGE_MILLIS = 20_000` 的缓存；持有隐藏的系统权限 `ACCESS_FINE_POWER_MONITORS` 时使用另一组状态缓存，最大年龄为 `250 ms`。该权限的保护级别是 `signature|privileged|development`，普通三方应用不能把它当作可申请的公开能力。

普通与高精度路径返回累计值前都会经过 `IntervalRandomNoiseGenerator`。在 r1 中，返回值位于“上一次原始读数”和“当前原始读数向下最多 `10_000_000 μWs`”共同确定的下界与当前读数之间；`10_000_000 μWs` 等于 `10 J`。同一 UID 在下一次底层刷新前得到稳定的扰动样本。这个实现意味着公开读数适合较长实验窗口和重复对照，不适合把一次短任务的前后差值当作精密能量计结果。

下面的纯函数用于检查两次异步快照是否来自不同采样时刻，再计算累计值差。它不会把同一缓存快照或回退读数伪装成有效结果。

```kotlin
data class PowerWindowDelta(
    val monitorName: String,
    val energyUws: Long?,
    val startTimestampMillis: Long,
    val endTimestampMillis: Long,
)

@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
fun calculatePowerWindowDeltas(
    monitors: List<PowerMonitor>,
    before: PowerMonitorReadings,
    after: PowerMonitorReadings,
): List<PowerWindowDelta> =
    monitors.map { monitor ->
        val startEnergy = before.getConsumedEnergy(monitor)
        val endEnergy = after.getConsumedEnergy(monitor)
        val startTime = before.getTimestampMillis(monitor)
        val endTime = after.getTimestampMillis(monitor)

        val delta = if (
            startEnergy != PowerMonitorReadings.ENERGY_UNAVAILABLE.toLong() &&
            endEnergy >= startEnergy &&
            endTime > startTime
        ) {
            endEnergy - startEnergy
        } else {
            null
        }

        PowerWindowDelta(
            monitorName = monitor.name,
            energyUws = delta,
            startTimestampMillis = startTime,
            endTimestampMillis = endTime,
        )
    }
```

调用方先通过 `getPowerMonitorReadings()` 获取 `before`，执行固定工作负载，再异步获取 `after`。`energyUws == null` 表示读数不可用、累计值回退，或两次调用命中了同一采样时刻。不要用高频轮询等待时间戳变化；实验窗口应覆盖缓存与扰动带来的误差，并把 `startTimestampMillis`、`endTimestampMillis` 一起保存。需要分析短任务时，优先使用可用的 Perfetto power rails、设备功耗轨道或外部功耗仪。

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

开发阶段还应执行 `adb shell dumpsys performance_hint`，核对 Session 的 PID/UID、TID、target、`AllowedByProcState`、`ForcePaused`、`PowerEfficient` 和设备能力。Perfetto 中的 `ADPF Session <id> target duration`、`actual duration`、TID 与 mode counter 用来确认提示数据确实进入客户端路径，再与 sched、频率、deadline miss 和 thermal 对齐。statsd 的 ADPF atom 属于系统遥测，不是普通应用的实时查询接口。

## 实验设计：同时看耗时和单位任务能耗

Power Efficiency Mode 应按单位任务验收：固定设备、温度起点、输入数据和工作负载，再比较耗时与能耗。

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

输入、主线程、RenderThread、音视频低延迟线程一般不适合默认节能优先。它们的尾部延迟更敏感，错误 hint 会把用户感知问题放大。图形、游戏和相机相关周期任务如果要接入，应先按 5.9 和本节的 Session 边界验证线程身份。

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

热状态进入高档位前主动降低 batch 并发，通常比等系统 throttling 后再恢复更可控。具体阈值要由设备实验给出，这里不写固定温度或固定收益。

### PowerMonitorReadings 与 Perfetto power rails 的同窗验证方法

`PowerMonitorReadings` 和 Perfetto power rails 可以放在同一实验窗口内互相解释，但不应被写成跨设备等价数据源。应在同一设备、同一工作负载、同一温度起点下，同时记录两次 `PowerMonitorReadings` 的时间戳与差值、Perfetto power rails 差值、CPU frequency、thermal status 和任务计数。普通应用还要把 r1 的 20 秒缓存和随机扰动计入误差。若两类曲线只在趋势上同向，结论应写成“同窗旁证一致”，不要写成 rail 级校准。Pixel 或单一 OEM 设备上的结论也只绑定该设备分桶。


## 扩展：系统与电源 HAL 的协同

ADPF 的端到端效果同时取决于应用上报、系统服务和电源 HAL。以下以 AOSP `android-17.0.0_r1` 为准，说明公开 API 进入系统后的关键边界。

> **版本限定**：源码锚点统一使用 `android-17.0.0_r1`。main/master 或 Android 18/API 38 及以上的内容不在讨论范围内；公开 API 口径只覆盖到 Android 17/API 37。

### Power HAL `ML_ACC` Boost

**源码位置**: `hardware/interfaces/power/aidl/android/hardware/power/Boost.aidl` (`android-17.0.0_r1`)

`ML_ACC` 是 Power HAL 为机器学习加速器预留的 boost 类型。`android-17.0.0_r1` 的注释把它和后续几种 boost 一起标记为“Android framework 当前不发送，OEM 可以选择实现”。下面摘录用于确认枚举名与这一版本边界：

```aidl
/** 
 * This boost indicates that the device is interacting 
 * with ML accelerator. 
 */
ML_ACC,
```

源文件没有给 `ML_ACC` 写显式整数。HAL 与系统代码应引用生成的 `Boost.ML_ACC`，不能从排列位置推导数值。应用公开 API 也不直接发送这个 boost，不能把它写成通用的 App 侧 NPU 加速开关。

厂商可以在自己的受控路径中决定是否实现该类型以及如何映射到芯片策略，但 AOSP 枚举本身不承诺 CPU、GPU、NPU 频率或持续时间。

### HintManagerService：系统层会话调度中心

**源码位置**: `frameworks/base/services/core/java/com/android/server/power/hint/HintManagerService.java` (`android-17.0.0_r1`)

系统通过 HintManagerService 统一管理所有 ADPF 会话。核心职责包括：

- **会话生命周期管理**：维护 uid → token → session 的映射，处理 session 的创建、更新和清理。
- **CPU/GPU headroom 查询**：Android 17 的 `SystemHealthManager` 通过 `IHintManager` 转发到 Power HAL `getCpuHeadroom()` / `getGpuHeadroom()`。Java API 返回 0-100 的 headroom 数值或 `Float.NaN`，HAL 的 `CpuHeadroomResult` / `GpuHeadroomResult` 也只暴露 `globalHeadroom`，不提供负载、温度或频率明细。
- **版本感知调度**：根据 Power HAL 版本调整可用的 hint 数量和调度策略。

HintManagerService 的内部实现细节（如具体状态映射结构、清理间隔）随版本演进，应以对应 tag 的源码为准。以下不引用 main branch 特有的内部代码。

**版本感知的调度策略**：
- Power HAL V4：基础 hint session 支持。
- Power HAL V5：`createHintSessionWithConfig()`、`SessionTag`、`SessionMode.POWER_EFFICIENCY` 与 `getSessionChannel()` 支持。
- Power HAL V6：CPU/GPU headroom 查询，以及 `GRAPHICS_PIPELINE`、`AUTO_CPU`、`AUTO_GPU` session mode 支持。
- Power HAL V7：加入 `AUDIO_PERFORMANCE` session mode；`android-17.0.0_r1` 的冻结 AIDL 已包含 V7。

### SessionTag 与 SessionMode：两个不同的 HAL 内部枚举

AOSP 中 **SessionTag** 和 **SessionMode** 是两个独立的 AIDL 枚举，定义在不同文件中，服务于不同层次。

下面的 `SessionTag` 摘录用于说明会话来源类别。r1 源文件没有显式整数赋值：

```aidl
@VintfStability
@Backing(type="int")
enum SessionTag {
    OTHER,
    SURFACEFLINGER,
    HWUI,
    GAME,
    APP,
    SYSUI,
}
```

`SessionTag` 描述谁创建或归属哪类会话，`HintManagerService` 还会把普通 App 会话按应用类别映射为 `APP` 或 `GAME`。

下面的 `SessionMode` 摘录用于说明会话要求；它与来源标签是两套不同的枚举：

```aidl
@VintfStability
@Backing(type="int")
enum SessionMode {
    POWER_EFFICIENCY,
    GRAPHICS_PIPELINE,
    AUTO_CPU,
    AUTO_GPU,
    AUDIO_PERFORMANCE,
}
```

`GRAPHICS_PIPELINE` 属于 `SessionMode`，不在 `SessionTag` 中。Java SDK 的 `PerformanceHintManager.createHintSession(int[], long)` 不接受 HAL tag 或 mode；`setPreferPowerEfficiency(true)` 由系统映射为能效模式。Android 16 起的 NDK `ASessionCreationConfig` 提供 `setGraphicsPipeline()`、`setUseAutoTiming()` 和 `setPreferPowerEfficiency()` 等高层开关，但 App 仍不应依赖 HAL 枚举整数，也不能通过公开 NDK 接口任意选择 `SessionTag` 或 `AUDIO_PERFORMANCE`。

### 电源状态跟踪与统计

`HintManagerService` 注册了 `ADPF_SYSTEM_COMPONENT_INFO`、`ADPF_SESSION_SNAPSHOT` 和 `ADPF_SUPPORT_INFO` 等 statsd pull atom。会话快照按 UID 与 `SessionTag` 记录最大并发会话数、最大线程数、能效会话数、目标耗时分布和图形管线会话数；支持信息还包含 Power HAL 版本与可用的 session hint、mode、FMQ、CPU/GPU headroom 能力。这些是系统统计接口，不是 App 的公开诊断 API。

### FMQ 与系统组件开关

`android-17.0.0_r1` 的 `HintManagerService` 会读取两个系统属性，并把状态写入 `ADPF_SYSTEM_COMPONENT_INFO`：

- `debug.sf.enable_adpf_cpu_hint`：SurfaceFlinger CPU hint 开关
- `debug.hwui.use_hint_manager`：HWUI hint manager 开关

Power HAL V5 开始提供 `getSessionChannel()`，服务端可以通过 FMQ 传递会话数据并记录是否使用。上述属性和 HAL channel 都属于系统组件与厂商适配面，不应作为普通 App 的运行时开关。

### PowerStatsService 完整数据通路（系统服务 → IPowerStats HAL → statsd）

`SystemHealthManager.getPowerMonitorReadings()` 最终进入 `IPowerStatsService.Stub`。Binder 入口复制调用 UID 后，把工作投递给 PowerStatsService 的 Handler，避免在 Binder 线程中直接访问 HAL。服务根据 monitor 类型分别调用：

- `IPowerStats.getEnergyConsumed()`：读取 modeled energy consumer；
- `IPowerStats.readEnergyMeter()`：读取直接测量的 ODPM channel。

Android 17 r1 为普通读数和高精度读数维护两组 `PowerMonitorState`。普通调用方的最大缓存年龄是 `20_000 ms`；持有隐藏系统权限 `ACCESS_FINE_POWER_MONITORS` 的调用方使用 `250 ms`。当所选 monitor 中最早的时间戳为 0，或其年龄超过对应阈值，服务才更新 energy consumer 与 energy measurement。调用频率高于阈值只会反复拿到缓存，并不会提高底层采样频率。

读数更新后，服务在上一次原始累计值与当前原始累计值之间生成按 UID 稳定的随机返回值。下界不会低于 `current - 10_000_000 μWs`，也不会低于 `prevEnergyUws`；上界是当前原始值。因为 `1 μWs = 1 μJ`，该常量对应 `10 J`，不是 `10 MJ`。这段逻辑降低了公开读数的时间与数值精度，也解释了相邻窗口为何可能出现零差值或波动。

`LocalService` 另有 `getEnergyConsumedAsync()`、`getStateResidencyAsync()` 和 `readEnergyMeterAsync()` 三个系统内部入口，返回 `CompletableFuture`。`getEnergyConsumedAsync()` 发现 HAL 返回的 consumer 数量少于请求时会记录 `Slog.wtf`，随后仍以已有数组完成 future。这个内部路径不能直接用来推断 App 的 `getPowerMonitorReadings()` 错误语义；App 路径由 `IPowerStatsService` 的结果码和 `OutcomeReceiver` 约定决定。

`StatsPullAtomCallbackImpl` 根据 HAL 提供的信息注册两个 pull atom：

- `ON_DEVICE_POWER_MEASUREMENT` 对应 `IPowerStats.readEnergyMeter()`；
- `SUBSYSTEM_SLEEP_STATE` 对应 `IPowerStats.getStateResidency()`。

回调通过 `ConcurrentUtils.DIRECT_EXECUTOR` 执行，再等待 Handler 侧 future，超时上限为 `2_000 ms`。异常、超时或空结果返回 `PULL_SKIP`。`ON_DEVICE_POWER_MEASUREMENT` 只接收 `durationMs == timestampMs` 的样本，含义是能量累计区间从开机开始；不能把这个判断缩写成“两个字段为 0”。

`PowerStatsLogger` 使用三个 Handler 消息采集 meter、model 和 residency 数据，并存入 `/data/system/powerstats/`。日志前缀分别是 `log.powerstats.meter.0`、`log.powerstats.model.0` 与 `log.powerstats.residency.0`。`PowerStatsDataStorage` 通过 `FileRotator` 每 4 小时轮转并保留 48 小时，而不是固定写成六个 `.pb` 文件。`meterCache`、`modelCache`、`residencyCache` 保存 HAL 元信息指纹；元信息改变时，对应的旧日志会被删除。它们由 `AtomicFile` 更新，不能把临时文件名当作稳定存储格式。

写入前，`adjustTimeSinceBootToEpoch()` 使用服务启动时计算的墙钟基线，把 HAL 的开机时间戳放到墙钟时间线上，便于事件报告排序。这不表示累计能量可以跨重启直接相减；HAL 的 energy 与 residency 仍以本次开机为起点。

`IPowerStats.aidl` 是 `@VintfStability` 接口，定义六个方法：`getPowerEntityInfo()`、`getStateResidency()`、`getEnergyConsumerInfo()`、`getEnergyConsumed()`、`getEnergyMeterInfo()` 与 `readEnergyMeter()`。`Channel` 包含 `id`、`name`、`subsystem`；后两个字段对 framework 是厂商不透明字符串。`EnergyMeasurement` 包含 `id`、`timestampMs`、`durationMs`、`energyUWs`，其中时间使用 `CLOCK_BOOTTIME`，能量单位是 μWs。

DeviceConfig 的 `battery_stats/power_monitor_api_enabled` 由监听器动态刷新。值变化时，服务清空 monitor 列表和两组状态缓存；关闭后返回空列表。它是系统侧控制项，不是 App 的公开灰度接口。

对 App 和实验平台有四个直接影响：

- 不要假设每次 `getPowerMonitorReadings()` 都访问 HAL；普通应用在 r1 中可能复用 20 秒内的读数。
- 必须保存每个 monitor 的返回时间戳。两次时间戳相同，差值就不代表业务窗口。
- μWs 与 μJ 数值相等，但 μWh 是另一种单位；换算报告时要保留原始单位。
- `@VintfStability` 约束接口兼容性，不统一厂商 rail 的覆盖范围、名称和测量质量。跨设备实验仍需先核对 monitor 语义。

> 源码锚点覆盖 `PowerStatsService.java`、`IntervalRandomNoiseGenerator.java`、`StatsPullAtomCallbackImpl.java`、`PowerStatsLogger.java`、`PowerStatsDataStorage.java`、`IPowerStatsService.aidl`、`PowerMonitor.java`、`PowerMonitorReadings.java`、`IPowerStats.aidl`、`Channel.aidl` 与 `EnergyMeasurement.aidl`，均以 `android-17.0.0_r1` 为准。


### 版本演进总结

| Android 版本 | 系统层能力 | 硬件协同增强 |
|-------------|----------|-------------|
| Android 12 | ADPF v1 `PerformanceHintManager` / `createHintSession()` | CPU hint session 基础支持 |
| Android 14 | `setThreads()` 等 session 线程管理 API | 更完整的线程集合维护 |
| Android 15 | `setPreferPowerEfficiency()`、`PowerMonitor`、Power HAL `SessionTag` / `SessionConfig` 与 `getSessionChannel()` | 能效偏好和 monitor 读数进入公开验证链路 |
| Android 16 | `getCpuHeadroom()` / `getGpuHeadroom()`、`GRAPHICS_PIPELINE` / `AUTO_CPU` / `AUTO_GPU` SessionMode | CPU/GPU headroom 查询与图形管线自动计时模式 |
| Android 17 | `AUDIO_PERFORMANCE` SessionMode 在 `android-17.0.0_r1` Power HAL AIDL 中可见 | 低延迟音频流水线可表达性能地板需求；仍属于系统/HAL 面，不是普通 App 直接选择的公开枚举 |

**硬件协同要点**：
1. SessionTag 和 SessionMode 是 HAL 内部概念，App 通过公开 ADPF API（`createHintSession`、`reportActualWorkDuration`、`setPreferPowerEfficiency`）表达意图，不直接选择 tag/mode。
2. `ML_ACC` boost 的数值由 AIDL 编译器生成，适配代码引用枚举名而非硬编码常量。
3. 利用 Perfetto 验证系统对 ADPF hint 的实际调度行为，而不是假设 hint 一定生效。
4. OEM 可基于 Boost、SessionTag 和 SessionMode 实现芯片级优化，但这些优化在不同设备上不可假设一致。

## 小结

ADPF Power Efficiency Mode 的价值在于把长期周期任务的 deadline 余量告诉系统。`setPreferPowerEfficiency(true)` 负责表达偏好，`PowerMonitorReadings` 和 Perfetto power rails 负责验证，线上灰度负责守住尾部耗时和失败率。没有稳定线程、稳定周期和能耗数据，这个能力就不该写成优化结论。

## 参考资料

- [Android Developers: PerformanceHintManager.Session](https://developer.android.com/reference/android/os/PerformanceHintManager.Session)
- [Android Developers: ADPF overview](https://developer.android.com/games/optimize/adpf)
- [Android Developers: SystemHealthManager](https://developer.android.com/reference/android/os/health/SystemHealthManager)
- [Android Developers: PowerMonitor](https://developer.android.com/reference/android/os/PowerMonitor)
- [Android Developers: PowerMonitorReadings](https://developer.android.com/reference/android/os/PowerMonitorReadings)
- [Android NDK: Performance Hint Manager](https://developer.android.com/ndk/reference/group/a-performance-hint)
- [Perfetto: Power data sources](https://perfetto.dev/docs/data-sources/battery-counters)
- [AOSP Android 17 r1: PerformanceHintManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [AOSP Android 17 r1: HintManagerService.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/hint/HintManagerService.java)
- [AOSP Android 17 r1: PowerStatsService.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsService.java)
- [AOSP Android 17 r1: IntervalRandomNoiseGenerator.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/IntervalRandomNoiseGenerator.java)
- [AOSP Android 17 r1: PowerStatsDataStorage.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/powerstats/PowerStatsDataStorage.java)
- [AOSP Android 17 r1: IPowerStats.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl)
- [AOSP Android 17 r1: SessionMode.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/aidl/android/hardware/power/SessionMode.aidl)
