---
title: 耗电与发热监控 (Battery & Thermal)
chapter: '19'
section: '19.25'
status: finalized
drafted_date: '2026-04-24'
drafted_by: gemini
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-04-25'
last_verified_against: AOSP PowerManager / PowerManagerService / BatteryStats references,
  Android Thermal API docs
confidence: high
tags:
- apm
- battery
- thermal
- wakelock
related_chapters:
- '19.0'
- '19.19'
pipeline_stage: ready-to-publish
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: '2026-04-28'
last_task6_audit: '2026-05-22'
task6_result: pass-light-edit
task9_state: reviewed
sources:
- https://developer.android.com/reference/android/os/PowerManager
- https://source.android.com/docs/core/power/thermal-mitigation
- https://developer.android.com/topic/performance/power/setup-battery-historian
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-13
last_task9_at: 2026-05-13T07:38:00+08:00
task9_review_notes: "2026-05-13 Task9 复审：无 P0/P1，前次 exact alarm P0 已修正；queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task9_review_log: logs/deep-review/2026-05-13-07-deep-review.md
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-26
---


# 耗电与发热监控 (Battery & Thermal)

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明电量与发热是影响用户卸载 App 的重要隐性因素，解析线上 APM 如何突破系统限制进行归因监控。
- 🔹 [Wakelock 泄漏监控] 解释 `PowerManager.WakeLock` 的申请与释放原理，介绍如何通过 ASM 字节码插桩或受控的服务代理/反射 Hook，找出忘记释放唤醒锁的代码堆栈。
- 🔹 [Alarm 唤醒风暴] 说明后台频繁 Alarm 唤醒对系统 Doze 模式的破坏，以及如何在端侧记录异常的高频定时任务。
- 🔹 [硬件资源耗电归因] 说明网络模块（基带唤醒）、GPS 定位、蓝牙扫描以及后台异常高 CPU 占用在端侧的统计方法。
- 🔹 [Thermal API 应用] 重点介绍 Android 10+ 引入的 `PowerManager.OnThermalStatusChangedListener`，如何感知设备的过热状态（如 `THERMAL_STATUS_SEVERE`）。
- 🔹 [端侧降级策略] 结合发热状态感知，给出 App 主动自保的降级策略：降低动画帧率、关闭后台预加载、停止大文件下载、降低视频分辨率。
- 🔹 [系统级耗电账单] 分析 Android Vitals 提供的“后台耗电”及“卡死导致的耗电”大盘数据与端侧监控的互补关系。

### 扩展（可选深入）

- 🔸 提供一段基于 Android 10 Thermal API 进行业务降级的架构伪代码。
- 🔸 画一张从“触发 CPU/网络高频活动”到“发热状态改变”再到“APM 端侧报警”的反馈路径图。
- 🔸 介绍 `BatteryManager` 获取电流/电压瞬时值的局限性及不同厂商 ROM 下的差异。

### 流水线加工要求

- 必须明确“耗电”是一个衍生指标，直接测电量下降往往不准，主要观测对象是“谁占用了高耗电硬件”。
- 必须指出后台任务 (WorkManager/JobScheduler) 也是耗电分析的重灾区。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->

耗电监控不能只盯电量百分比。电量下降是结果，端侧 APM 更适合记录“哪些代码占用了高耗电硬件”：WakeLock、Alarm、定位、蓝牙扫描、网络传输、CPU 长时间高负载，以及 WorkManager / JobScheduler 触发的后台任务。这样上报的数据才能回到具体页面、任务、线程和调用栈。

发热监控也按同一思路处理。Android 10 之后，应用能通过 Thermal API 得到系统聚合后的发热等级。APM 侧直接记录系统热状态、业务活动和降级动作，判断“哪类任务在设备升温时仍然继续消耗资源”。

## 1. 先记录资源占用，再推导耗电原因

线上直接用 `BatteryManager` 读电流、电压并不稳定。不同芯片和 ROM 暴露的电源节点不同，瞬时电流还会受屏幕亮度、基带状态、充电状态、温度和采样窗口影响。把几秒内的电流读数强行归因到某个方法，误差通常很大。

端侧 APM 更可靠的做法是记录高耗电资源的占用时间和触发条件：

| 资源 | 端侧记录项 | 归因方式 | 常见问题 |
| --- | --- | --- | --- |
| WakeLock | tag、acquire/release 时间、调用栈、`mToken` 标识 | 同一个 token 的持有时长与页面/任务绑定 | 忘记 release、引用计数不匹配、超时时间过长 |
| Alarm | type、triggerAt、interval、allowWhileIdle、调用栈 | 高频唤醒与后台任务名绑定 | Doze 下反复唤醒、定时任务退避失效 |
| 定位/GNSS | provider、请求精度、回调间隔、前后台状态 | 按会话或任务统计定位占用窗口 | 后台持续定位、精度要求过高 |
| 蓝牙/Wi-Fi 扫描 | 扫描开始/停止、间隔、结果数 | 按扫描任务统计硬件活跃时间 | 轮询过密、页面退出后未停止 |
| 网络 | 请求量、字节数、重试次数、前后台状态 | 结合 TrafficStats 与网络 APM 样本 | 后台大文件、弱网重试放大耗电 |
| CPU | 线程采样、任务名、前后台状态 | 高 CPU 线程与业务任务绑定 | 死循环、忙等、解码/压缩任务未限速 |

系统侧的 `BatteryStats` 也是按计时器和计数器建模：硬件进入某个状态后开始计时，退出后停止计时，再按功耗模型折算到 UID 或系统组件。线下可用 `dumpsys batterystats --history` 和 Battery Historian 观察唤醒、网络、定位、Job 的时间分布；线上应用通常拿不到完整系统账本，只能记录自身触发的资源事件，再和 Android Vitals 的后台耗电大盘互补。

## 2. WakeLock 泄漏：看 `acquire()` 和 `release()` 是否配对

`PowerManager.WakeLock` 的申请会跨进程进入 SystemServer。应用调用 `WakeLock.acquire()` 后，`PowerManager.WakeLock` 会把内部的 `mToken` 通过 `IPowerManager` 传给 SystemServer；`PowerManagerService` 按这个 Binder token 记录一条唤醒锁。释放时，`release()` 也会带着同一个 token 回到 SystemServer。APM 端用 token、tag、调用栈和线程信息组合成一条本地记录，就能识别哪一次申请没有按时释放。

WakeLock 监控有两种常见接入方式：

- ASM 插桩：在字节码层面包住 `PowerManager.WakeLock.acquire()`、`acquire(long timeout)` 和 `release()`，记录调用栈、tag、线程、页面、前后台状态和超时时间。它不依赖系统私有字段，版本风险低，适合线上。
- 服务代理 / 反射 Hook：尝试替换 `PowerManager` 持有的 `IPowerManager` 或已有 `WakeLock` 实例中的服务对象。`PowerManager` 通常在构造阶段从 `ServiceManager` 获取并缓存服务引用，简单代理 `Context.getSystemService()` 很难覆盖已创建对象；反射路径还会受隐藏 API、字段名和厂商改动影响，适合内部诊断，不适合大规模线上默认开启。

泄漏判断要同时看 release 调用、引用计数和持有时长。WakeLock 默认带引用计数，同一个对象连续 acquire 多次，需要对应次数的 release；业务也可能调用 `setReferenceCounted(false)` 改变配对规则。端侧记录应包含引用计数模式、timeout、持有时长、页面生命周期和进程前后台状态。超过阈值时，上报最近一次 acquire 栈和持有窗口，避免等用户电量明显下降后再回捞日志。

这段伪代码展示端侧记录的最小字段，重点是用 token/tag/调用栈定位泄漏来源，不直接计算 mAh。

```kotlin
// Pseudocode: inserted around PowerManager.WakeLock.acquire/release by ASM.
data class WakeLockSample(
    val tokenHash: String,
    val tag: String?,
    val op: String,
    val elapsedRealtimeMs: Long,
    val timeoutMs: Long?,
    val referenceCounted: Boolean,
    val foreground: Boolean,
    val stack: List<String>
)

fun onWakeLockAcquire(lock: PowerManager.WakeLock, timeoutMs: Long?) {
    BatteryApm.record(
        WakeLockSample(
            tokenHash = reflectTokenHashIfAvailable(lock),
            tag = reflectTagIfAvailable(lock),
            op = "acquire",
            elapsedRealtimeMs = SystemClock.elapsedRealtime(),
            timeoutMs = timeoutMs,
            referenceCounted = reflectReferenceModeIfAvailable(lock),
            foreground = ProcessState.isForeground(),
            stack = StackSampler.compactCurrentStack()
        )
    )
}
```

这类代码只能作为端侧 APM 的采样入口。真正的泄漏判定要在本地状态表中完成：同一 token 的 acquire 进入持有表，release 移出持有表，超过阈值仍未释放才生成告警样本。

## 3. Alarm 与后台任务：记录高频唤醒来源

Alarm 对耗电的影响来自“把设备叫醒”。在 Doze 模式下，系统会限制后台唤醒频率，但 `setExactAndAllowWhileIdle()`、`setAlarmClock()` 等接口仍可能让应用在不合适的场景里频繁打断休眠。APM 端要记录同一业务在一段时间内设置了多少唤醒、间隔是否过短、是否发生在后台、是否伴随网络请求或 WakeLock。

工程上可把 `AlarmManager.set*()`、`PendingIntent` 标识、WorkManager 任务名、JobScheduler 的 jobId 放进同一个后台任务样本。这样能把“某个同步任务每 5 分钟唤醒一次、醒来后拉取网络并持有 WakeLock”的路径还原出来。不同 Android 版本和厂商 ROM 对 idle quota 的处理会变化，线上规则应看相对异常：同一用户、同一版本、同一任务名下的唤醒次数突然升高，就应进入采样上报。

### Android 12+ 精确闹钟权限对 APM 归因的影响

Android 12 引入 `SCHEDULE_EXACT_ALARM` 权限，Android 13/14 进一步收紧精确闹钟的行为。APM 记录 Alarm 样本时，要同时记录目标进程是否持有该权限、`canScheduleExactAlarms()` 的返回值、alarm type 和 `allowWhileIdle` 标记。这样在归因时才能区分"业务设置了精确闹钟但系统拒绝了"和"业务确实只用了非精确闹钟"。

| Android 版本 | 精确闹钟行为 | APM 样本应记录的字段 |
| --- | --- | --- |
| Android 11 及以下 | 无权限限制，`setExact()` / `setExactAndAllowWhileIdle()` 正常工作 | alarm type、triggerAt、interval |
| Android 12 | 新增 `SCHEDULE_EXACT_ALARM` 权限，新安装应用默认授予，预装应用视厂商策略 | 增加 permission 状态、`canScheduleExactAlarms()` 返回值 |
| Android 13 | 权限默认不授予（除非闹钟/日历类应用），用户需在设置中手动授权；新增 `USE_EXACT_ALARM` 供特定类别申请 | 增加 app-op 状态、是否命中 `USE_EXACT_ALARM` 豁免 |
| Android 14+ | 新安装且 target 33+ 的应用默认拒绝 `SCHEDULE_EXACT_ALARM`；未授权时调用 `setExact()` / `setExactAndAllowWhileIdle()` / `setAlarmClock()` 会抛 `SecurityException`，不会静默降级。需改用 `set()` / `setWindow()` / `setAndAllowWhileIdle()` 等非精确闹钟 API，或引导用户授权 | 调用精确闹钟 API 前必须检查 `canScheduleExactAlarms()`；未授权时记录回退路径（非精确闹钟 API 或权限请求），并在样本中区分"请求精确"与"实际精确" |

Android 14 起精确闹钟策略收紧：未持有 `SCHEDULE_EXACT_ALARM` 权限时，调用 `setExact()`、`setExactAndAllowWhileIdle()`、`setAlarmClock()` 会直接抛出 `SecurityException`，而非静默降级。APM 归因时需要区分两种场景：一是业务确实只用了非精确闹钟 API，触发时间本身就有偏移窗口；二是业务请求了精确闹钟 API 但因权限缺失导致崩溃或被迫回退。端侧应在调用前检查 `canScheduleExactAlarms()` 返回值，并在 APM 样本中分别记录"请求精确"与"实际精确"两种口径。

## 4. 硬件资源耗电归因：按占用窗口统计

GPS、蓝牙扫描、Wi-Fi 扫描、基带传输和 CPU 高负载都需要按占用窗口解释。APM 侧要记录“开始、停止、持续时间、触发任务、设备状态”。

- 定位：记录请求精度、最小间隔、provider、页面/服务名和停止时间。前后台切换后仍持续高精度定位，是最常见的异常形态。
- 蓝牙与 Wi-Fi 扫描：记录扫描频率、扫描窗口、结果数量和调用栈。扫描任务如果跟页面生命周期脱钩，页面退出后仍会持续唤醒硬件。
- 网络：用网络 APM 样本补充请求数、字节数、重试次数和弱网状态。基带被频繁唤醒时，小包高频比单次大包更容易拖长活跃窗口。
- CPU：记录进程 CPU 占比、线程采样栈、任务名和前后台状态。图片解码、压缩、加密、轮询和忙等都应落到具体线程。

Android Vitals 的“excessive wakeups”“stuck wake locks”“background battery usage”等指标适合看版本级趋势。端侧 APM 适合解释趋势背后的业务来源。两边数据口径不同，不能把 Vitals 的百分比直接套回单个用户会话。

## 5. Thermal API：从发热等级映射到降级动作

Android 10 引入 `PowerManager.OnThermalStatusChangedListener`，应用能收到系统聚合后的热状态。它给的是等级，应用无需读取摄氏度。业务侧应把等级映射为一组明确动作，避免每个模块各自判断。

| Thermal 状态 | 建议动作 | APM 记录项 |
| --- | --- | --- |
| `THERMAL_STATUS_NONE` / `LIGHT` | 正常运行，只记录状态变化 | 状态、前后台、页面、设备信息 |
| `THERMAL_STATUS_MODERATE` | 降低后台预取频率，延后非必要上传，控制动画和图片解码并发 | 被降级的任务名、降级前后参数 |
| `THERMAL_STATUS_SEVERE` | 降低动画帧率或刷新频率，暂停预加载，停止大文件下载，降低视频清晰度 | 降级动作、用户可感知页面、持续时间 |
| `THERMAL_STATUS_CRITICAL` | 停止非必要后台活动，关闭高功耗特效，限制定位和扫描 | 被停止的任务、恢复条件 |
| `THERMAL_STATUS_EMERGENCY` | 保存必要状态，停止所有可推迟任务，避免继续触发硬件资源 | 最近一次活动、保护动作是否执行 |
| `THERMAL_STATUS_SHUTDOWN` | 设备接近关机，应用不应依赖收到回调 | 若收到，记录并立即停止非必要工作 |

这段 Kotlin 示例用于说明监听注册和统一降级入口，重点看 `applyThermalPolicy(status)` 的集中处理。

```kotlin
class ThermalGuard(private val context: Context) {
    private val powerManager = context.getSystemService(PowerManager::class.java)

    private val listener = PowerManager.OnThermalStatusChangedListener { status ->
        BatteryApm.recordThermalStatus(
            status = status,
            elapsedRealtimeMs = SystemClock.elapsedRealtime(),
            foreground = ProcessState.isForeground()
        )
        applyThermalPolicy(status)
    }

    fun start() {
        powerManager.addThermalStatusListener(context.mainExecutor, listener)
        // 注册后立即读取当前热状态，避免应用启动时设备已处于 SEVERE/CRITICAL 但监听器要等下一次状态变化才回调
        val currentStatus = powerManager.currentThermalStatus
        if (currentStatus != PowerManager.THERMAL_STATUS_NONE) {
            BatteryApm.recordThermalStatus(
                status = currentStatus,
                elapsedRealtimeMs = SystemClock.elapsedRealtime(),
                foreground = ProcessState.isForeground(),
                source = "initial_snapshot"
            )
            applyThermalPolicy(currentStatus)
        }
    }

    fun stop() {
        powerManager.removeThermalStatusListener(listener)
    }

    private fun applyThermalPolicy(status: Int) {
        when (status) {
            PowerManager.THERMAL_STATUS_MODERATE -> BackgroundPrefetch.reduceRate()
            PowerManager.THERMAL_STATUS_SEVERE -> {
                AnimationBudget.useLowRefreshMode()
                DownloadManager.pauseLargeFiles()
                VideoPlayer.reduceResolution()
            }
            PowerManager.THERMAL_STATUS_CRITICAL,
            PowerManager.THERMAL_STATUS_EMERGENCY,
            PowerManager.THERMAL_STATUS_SHUTDOWN -> {
                BackgroundPrefetch.stopAll()
                LocationCollector.useLowPowerMode()
                BluetoothScanner.stopOptionalScan()
            }
        }
    }
}
```

监听本身只提供状态变化。APM 要把热状态与同一时间窗口内的 WakeLock、Alarm、网络、定位、CPU 样本放在一起分析，才能判断是业务活动推高了热状态，还是系统已经降频导致页面变慢。

## 6. 端侧告警与上报边界

耗电与发热样本容易变大，默认策略应做本地聚合。普通用户只上报分钟级摘要：各资源占用时长、后台任务次数、热状态分布、异常 top 调用栈。命中阈值的用户再上报少量明细样本，包含调用栈和任务名。定位、蓝牙、网络请求等数据要做脱敏，不能上传精确位置、设备附近蓝牙名称、完整 URL query 或请求体。

端侧结论也要保留边界。应用无法完整读取系统功耗模型，无法证明某个方法消耗了多少 mAh；它能证明的是：某段时间内，某个任务持有了 WakeLock、触发了高频 Alarm、占用了定位或网络硬件，并且这些事件与 Android Vitals 或用户投诉中的耗电现象同向变化。

## 参考资料

- Android `PowerManager` API reference：`OnThermalStatusChangedListener`、Thermal status 常量、WakeLock API。
- Android Thermal Mitigation 文档：系统热状态与应用降级建议。
- Android Battery Historian / batterystats：线下耗电账本分析工具。
