---
title: "Android 功耗管理"
chapter: "5.6"
section: "5.6"
status: finalized
applicable_versions: "Android 6.0 (API 23) - Android 17 (API 37)"
last_verified: "2026-06-21"
last_verified_against: "AOSP android-17.0.0_r1 (frameworks/base, frameworks/native, hardware/interfaces); android-14.0.0_r1 historical TARE check; Android 16/17 official docs"
confidence: medium
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/5.21-android17-battery-optimization-soc-architecture.md"
  - "src/part1-fundamentals/ch05-cpu-power/25-low-power-standby-background-performance.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.35-pms-cpuidle-schedutil.md"
sources:
  - type: official
    path: android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java
    note: PowerManagerService 核心实现
  - type: official
    path: developer.android.com/training/monitoring-device-state/doze-standby
    note: Doze 模式与 App Standby 官方文档
  - type: official
    path: developer.android.com/topic/performance/appstandby
    note: App Standby Buckets 官方文档
  - type: official
    path: developer.android.com/topic/libraries/architecture/workmanager
    note: WorkManager 官方文档
  - type: blog
    path: obsidian/Cubox/BatteryHistorian Android手机耗电分析神器-2022-04-15.md
    note: Battery Historian 使用实践
  - type: blog
    path: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_抖音功耗优化实践.md
    note: 抖音功耗优化实践
tags:
  - power
  - wakelock
  - doze
  - battery
  - battery-historian
  - jobscheduler
  - power-management
drafted_date: "2026-04-01"
drafted_by: openclaw-task2a
reviewed_date: "2026-06-02"
task6_reviewed_date: "2026-06-02"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-21"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-21T15:27:38+08:00"
last_task9_audit: "2026-06-21"
last_task9_autofix_at: "2026-06-21"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-02T08:50:00+08:00"
pipeline_stage: ready-to-publish
reviewed_by: openclaw-task6
review_round: 8
related_chapters:
  - "5.1"
  - "5.2"
  - "5.4"
last_task9_review_log: "logs/deep-review/2026-06-21-15-audit.md"
task9_review_notes: "2026-06-21 Task9 闲时抽检：auto-fixed。已将源码锚点升级到 android-17.0.0_r1；修正 TARE tag 状态、Notifier/BatteryStatsImpl 路径、JobScheduler 10 分钟时限版本边界，并把不存在的 JobDebugInfo 改为 PendingJobReasonsInfo/getPendingJobReasonStats 口径；回到 Task6 复审。"
reviewed_at: "2026-06-02T01:05:00+08:00"
last_task6_at: "2026-06-22T01:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-22-01-review.md"
task6_review_notes: "2026-06-22 01 Task6 revisiting-review (Task9 autofix 后复审): pass-light-edit。L1 修复 1 处形容词+冒号起手式（'趋势很明确:'→直接陈述）。L2 开头/节奏/结构/读者视角均通过。无 B 类问题。自动晋升 finalized。"
p0: 0
p1: 0
p2: 0
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_new_rework: false
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
---

# 5.6 Android 功耗管理

> [!NOTE] 源码锚点
> 平台实现以 AOSP `android-17.0.0_r1`（Android 17 / API 37）为准，内核休眠与唤醒机制以 `android17-6.18-2026-06_r6` 为准。Doze 时序、App Standby 分桶、功率模型与 vendor Power HAL 策略允许由设备配置，因此不使用固定分钟数或固定频率描述通用行为。

## 功耗排障先回答三个问题

一次“耗电高”可能来自完全不同的机制。开始分析前先分开：

1. **谁在做功**：CPU、GPU、显示、蜂窝、Wi-Fi、GNSS、相机或充电电路。
2. **系统为什么没有休眠**：应用 WakeLock、内核 wakeup source、定时器、中断或系统恢复流程。
3. **工作为什么在这个时间发生**：前台业务、Alarm、JobScheduler、WorkManager、推送、Doze 维护窗口或后台限制豁免。

WakeLock 主要回答第二个问题。它不能解释 CPU 为什么繁忙，也不能覆盖显示或射频的全部能量。可靠结论通常需要把系统状态、组件活动和能量数据放到同一时间轴。

## PowerManagerService 到 system suspend

### 四个不同层次

Android 17 的功耗主路径可以分为四层：

| 层次 | 主要对象 | 职责 |
| --- | --- | --- |
| App/Framework API | `PowerManager.WakeLock`、screen flags、Job/Alarm API | 表达“暂时保持某种运行条件” |
| system_server | `PowerManagerService`（PMS） | 汇总 WakeLock、显示、wakefulness 和用户活动，维护 suspend blocker |
| Native/system service | PMS JNI、`ISystemSuspend`、suspend control | 开关 autosuspend，获取或释放 native suspend blocker |
| Kernel/platform | wakeup source、system suspend、设备驱动、固件 | 冻结用户空间、挂起设备、进入平台支持的睡眠状态并处理唤醒 |

App WakeLock 与内核 wakeup source 相关，却不能简单视为同一个对象。PMS 会把满足条件的 framework WakeLock 汇总到名为 `PowerManagerService.WakeLocks` 的 suspend blocker；硬件驱动也可以独立注册 wakeup source。

### Android 17 的准确调用边界

`PowerManagerService.java` 中可以定位到：

- `mWakeLockSuspendBlocker`、`mDisplaySuspendBlocker` 和 boot blocker；
- `nativeAcquireSuspendBlocker()` / `nativeReleaseSuspendBlocker()`；
- `nativeSetAutoSuspend()`；
- `nativeSetPowerMode()`。

JNI 文件 `com_android_server_power_PowerManagerService.cpp` 连接 `ISystemSuspend` 与 suspend control service。启用 autosuspend 后，只要没有有效 blocker，内核和平台就可以尝试进入 system suspend。

PMS 还会用 `Mode.INTERACTIVE` 通知 AIDL Power HAL 交互状态。这个 mode 由 vendor 映射到自己的电源策略；一次普通 WakeLock acquire 没有“AOSP 固定调用 `Boost.INTERACTION` 若干毫秒”的通用链路，也不会直接命令 schedutil 升到某个频点。

### CPU idle 与 system suspend

这两个状态必须分开：

- **CPU idle**：某个 CPU 暂时没有可运行任务，进入一个 cpuidle state；其他 CPU 和用户空间仍可能继续工作。
- **system suspend**：全系统低功耗转换，用户空间被冻结，设备进入低功耗状态，CPU 由平台 suspend 流程处理。
- **suspend-to-idle（s2idle）**：一种较轻的 system suspend；CPU 可停留在深 idle，但它仍经过冻结用户空间和挂起设备的系统流程。
- **suspend-to-RAM**：平台支持时可进入更深状态，内存自刷新，更多设备与总线断电或低功耗。

所以，“CPU idle 比例接近 100%”不能证明系统已经 suspend；Trace 中没有调度 slice 也可能只是采集缺失。应使用 `power/suspend_resume` 等事件确认 system suspend 边界。

### CPUIdle 与 schedutil 在 runnable 边界两侧工作

cpuidle governor 只在 CPU 已没有 runnable task、准备进入 idle 时选择空闲状态；schedutil 则在 CPU 执行或负载变化时把利用率需求映射成 CPUFreq 请求。PMS 可以通过 interactive 状态、suspend blocker 与 Power HAL mode 改变外部条件，但不会替内核逐 CPU 选择 idle state 或频率。一次唤醒中常同时出现 idle exit、任务 runnable、升频和 framework 交互提示，时间相邻不代表存在一条固定的 PMS → cpuidle → schedutil 调用链。

## WakeLock：类型、语义与责任

### 公共应用最常用的是 PARTIAL_WAKE_LOCK

Android 17 `PowerManager` 定义的主要 level 包括：

| Level | 语义 | 公共应用建议 |
| --- | --- | --- |
| `PARTIAL_WAKE_LOCK` | 保持 CPU 执行，屏幕可以关闭 | 仅在没有更合适 API 时短时使用 |
| `SCREEN_DIM_WAKE_LOCK` | 保持屏幕点亮，可变暗 | 已废弃，使用 `FLAG_KEEP_SCREEN_ON` |
| `SCREEN_BRIGHT_WAKE_LOCK` | 保持屏幕高亮 | 已废弃 |
| `FULL_WAKE_LOCK` | 保持屏幕和键盘背光 | 已废弃 |
| `PROXIMITY_SCREEN_OFF_WAKE_LOCK` | 由接近传感器控制屏幕 | 先检查设备支持，典型用于通话 |
| `DOZE_WAKE_LOCK` / `DRAW_WAKE_LOCK` | 系统内部用途 | 普通应用不可按公共能力依赖 |

`PowerManager.newWakeLock()` 只创建客户端对象；`acquire()` 才经 Binder 把请求送到 PMS。`ACQUIRE_CAUSES_WAKEUP` 也已废弃，唤醒 Activity 应使用 `setTurnScreenOn()` 或清单属性等面向窗口的 API。

### 安全的持锁写法

下面的示例只用于屏幕关闭后仍有必要完成的一小段进程内工作：

```kotlin
val powerManager = getSystemService(PowerManager::class.java)
val wakeLock = powerManager.newWakeLock(
    PowerManager.PARTIAL_WAKE_LOCK,
    "$packageName:UploadFinalize"
)

wakeLock.acquire(30_000L)
try {
    finishLocalCommit()
} finally {
    if (wakeLock.isHeld) {
        wakeLock.release()
    }
}
```

超时是兜底，`finally` 负责正常释放。应用仍需声明 `android.permission.WAKE_LOCK`。如果工作可以交给 WorkManager、JobScheduler、媒体播放、位置或下载框架，应让对应 API 管理 WakeLock 和系统约束，减少手工持锁。

还要注意引用计数：WakeLock 默认按 acquire/release 次数配对。调用 `setReferenceCounted(false)` 后，一次 release 可以结束多次 acquire 的效果；混用两种计数规则很容易造成提前释放或泄漏。

### WorkSource 负责归因

系统服务代表其他 UID 工作时，可以用 `WorkSource` 把 WakeLock 成本归因给实际请求者。普通应用不能用它把自身功耗随意归到别处；权限和来源链由系统校验。排障时同时记录 tag、owner UID 与 WorkSource，避免只按持锁进程判断责任。

### 缓存进程的 WakeLock 可能被禁用

Android 17 PMS 有 `no_cached_wake_locks` 等配置与 cached-process 判断，可以把某些 WakeLock 标记为 disabled。具体条件还涉及 UID 状态、豁免、锁类型和设备配置。

因此，应用不能把 PARTIAL_WAKE_LOCK 当作后台永久运行承诺。系统也不会因为对象仍在应用内显示 `isHeld` 就保证所有后台能力、网络或 Job 调度都不受限制。

## WakeLock 怎样进入 Batterystats

Android 17 的记账路径可以从源码追到：

```text
PowerManager.WakeLock.acquire()
  → IPowerManager.acquireWakeLock()
  → PowerManagerService.acquireWakeLockInternal()
  → notifyWakeLockAcquiredLocked()
  → Notifier.onWakeLockAcquired()
  → IBatteryStats.noteStartWakelock*()
  → BatteryStatsService / BatteryStatsImpl
```

释放路径使用 `noteStopWakelock*()`。`WorkSource`、history tag、UID/PID 和 lock flags 会影响归因。

Batterystats 适合回答“某 UID 在多长时间内持有哪些锁、触发哪些 Job/Alarm/网络活动”。它不是物理电表：统计时长和模型估算不能自动转换成精确焦耳，尤其无法单靠 WakeLock 时长推导屏幕、射频或 GPU 能量。

## Doze、App Standby 与其他省电状态

### 不要把几个名字合并成一个“后台限制”

| 机制 | 作用范围 | 主要触发依据 | 典型影响 |
| --- | --- | --- | --- |
| Battery Saver | 全设备 | 用户或系统省电策略 | 系统可能降低性能、限制网络访问、减少动画并延后后台任务 |
| Doze | 全设备空闲状态 | 灭屏、未充电、静止/空闲等设备条件 | 网络、Job、Sync、普通 Alarm 延后，WakeLock 被忽略 |
| App Standby | 单个应用 | 用户近期是否使用该应用 | 后台网络、Job 和 Alarm 受限 |
| App Standby Buckets | 单个应用 | 使用频率、预测与系统策略 | 不同 bucket 获得不同预算 |
| Background restricted | 单个应用的用户/系统限制 | 用户设置或系统提示后的选择 | 后台执行可被更强地阻止 |
| Low Power Standby | 设备非交互后的更深策略 | 平台支持、配置与 exemptions | 网络和 WakeLock 等能力进一步受限 |

这些机制可以叠加。一次 Job 延迟可能同时受到 Doze、standby bucket、后台限制、quota、网络约束和 thermal 状态影响。

Low Power Standby 开启后，设备处于非交互状态且不在 device-idle 维护窗口时，应用的网络访问会被禁用，持有的 WakeLock 会被忽略；运行 foreground service 的应用也在限制范围内。Android 14 / API 34 增加了 `isExemptFromLowPowerStandby()` 与 `isAllowedInLowPowerStandby()`，用于查询当前策略下的豁免和允许能力。该查询只描述 Low Power Standby，不能代替 Doze allowlist、standby bucket 或用户后台限制检查。

### Doze 的行为

设备满足平台定义的空闲条件后进入 Doze。Android 不给应用承诺“灭屏 30 分钟后进入”等固定时间；Light/Deep 状态机的延迟、维护窗口和运动检测都可以由系统配置。

Doze 期间，普通应用通常会遇到：

- 网络访问暂停；
- 未获豁免应用的 partial WakeLock 被忽略；
- JobScheduler、WorkManager 和 Sync 延后；
- 普通 Alarm 延后到维护窗口；
- Wi-Fi 扫描等高成本操作受限。

`setAndAllowWhileIdle()`、`setExactAndAllowWhileIdle()` 和 alarm clock 有特定例外，但频率与权限仍受限制。FCM 高优先级消息适合会产生用户可见通知的时效消息；用它维持静默心跳可能被降级，也会增加功耗。

Doze 会周期性进入维护窗口，批量执行部分待处理工作。窗口间隔会随空闲延长而变化，应用不能依赖具体分钟数。

### 电池优化豁免是部分豁免

在豁免名单中的应用可以在 Doze/App Standby 中使用网络并持有 partial WakeLock，但这不等于解除所有 Alarm、Job、Sync、后台启动与平台政策。Google Play 对直接申请豁免也有适用场景限制。

应用可以用 `PowerManager.isIgnoringBatteryOptimizations()` 查询自身状态。大多数业务应先采用 FCM、JobScheduler、WorkManager、前台服务或专用系统 API；只有核心功能在 Doze 下无法工作且符合政策时，再引导用户查看豁免设置。

### App Standby Buckets

Android 17 仍使用以下主要 bucket：

- `ACTIVE`
- `WORKING_SET`
- `FREQUENT`
- `RARE`
- `RESTRICTED`
- 另有从未运行等特殊状态

bucket 会影响 Job、Alarm 和后台网络预算。系统可以依据近期使用，也可以由预装预测组件利用机器学习判断未来使用概率；OEM 可调整非 active 应用的分配标准。应用不应尝试操纵 bucket，只需在每个 bucket 下保持功能可恢复。

`UsageStatsManager.getAppStandbyBucket()` 可以查询当前 bucket。测试设备可用下面的命令改变和读取状态：

```bash
adb shell am set-standby-bucket com.example.app rare
adb shell am get-standby-bucket com.example.app
```

测试结束后应恢复原 bucket。bucket 只是一个变量，Doze、charging、后台限制和 Job 约束仍要分别记录。

### RESTRICTED bucket 与“后台受限”设置

当前官方文档对 RESTRICTED bucket 给出严格预算：通常把 Job 集中到每天一次、最长约 10 分钟的批处理会话，Alarm 也大幅受限；充电时仍可能保留限制，只在特定充电/idle/非计量网络组合下放宽。

这些是 Android 当前的高层行为，设备厂商仍可决定分桶条件和部分限制细节。Device owner、profile owner、VPN、dialer、persistent app、用户设为 unrestricted 的应用等可能获得豁免；“正在运行任意前台服务”不是通用的 RESTRICTED bucket 豁免证明。

系统设置里的“Restricted/后台受限”侧重用户明确禁止后台活动，与预测得到的 standby bucket 不是同一个查询维度。两者都可能令 Job、Alarm、网络和前台服务启动受限，排障时要分别读取。

### Adaptive Battery 的准确边界

Adaptive Battery 可以借助预测结果影响 standby bucket 和后台资源分配。AOSP/官方 API 没有“Adaptive Battery 2.0”这一公共技术名称，也没有跨设备固定的 ML 模型、输入特征或省电百分比。

可靠表述应停在可观察边界：应用所在 bucket 会动态变化，OEM 可以提供预测组件；应用应使用系统调度 API并对延迟、停止和重试负责。

### Low Power Standby 在非交互期间限制网络与 WakeLock 效力

Low Power Standby（LPS）与 Doze、App Standby 和 App Hibernation 是不同状态机。Android 13 起它可以在设备非交互、超过配置超时后启用；Android 17 的 framework 主要把策略交给两个消费者：网络策略限制部分后台 UID 的联网能力，PowerManagerService 让不在允许范围内的 WakeLock 不再阻止低功耗状态。

LPS 不会删除 WakeLock，也不会取消 Job。交互恢复或应用命中 package、feature、allowed reason 等豁免后，限制可以解除。验证时读取 `dumpsys power` 的 Low Power Standby 状态与 policy，并同时观察网络访问、WakeLock/suspend blocker 和 `power/suspend_resume`；只看到一次请求超时，无法区分 LPS、Doze、待机桶或网络故障。

## JobScheduler 与 WorkManager

### 为什么它们通常比手工 WakeLock 合适

JobScheduler 能把多个应用的可延期工作按充电、网络、idle、storage、quota 等条件批量执行，从而减少频繁唤醒和无线电重复建链。WorkManager 在现代 Android 上通常借助 JobScheduler，并提供持久化、依赖链和跨版本适配。

它们不承诺精确执行时间，也不取消 Doze、App Standby、thermal 或 quota。Android 17 的详细 JobScheduler 机制见 [5.8 JobScheduler/WorkManager](08-jobscheduler-workmanager-performance.md)。

### 选择 API

| 需求 | 首选方向 |
| --- | --- |
| 可延期且需要可靠完成 | WorkManager |
| 平台/系统组件的条件式后台 Job | JobScheduler |
| 用户刚发起且可见的大文件传输 | User-initiated data transfer job |
| 用户可感知、需要持续运行的工作 | 符合类型与权限要求的 foreground service |
| 精确的用户提醒 | AlarmManager，按 exact alarm 政策使用 |
| 进程存活期内的短异步工作 | coroutine/executor，不需要持久 scheduler |

不要为了“早点运行”同时叠加 WakeLock、exact alarm、foreground service 和 expedited work。每个机制都有独立成本与政策，应按业务语义选择最小集合。

## 检测 WakeLock 与 suspend 问题

### 第一步：看当前状态

`dumpsys power` 能显示 PMS 当前 wakefulness、suspend blocker 和 WakeLock。下面的命令是只读检查：

```bash
adb shell dumpsys power
adb shell cat /sys/kernel/debug/wakeup_sources
```

第二个节点需要相应内核配置、权限和 SELinux 许可，量产机上可能不可读。输出中的 active count、event count、active time 和 wakeup count 语义由内核 wakeup-source 统计决定。

### 第二步：抓 system trace

内核 6.18 的 `include/trace/events/power.h` 定义了：

- `power/suspend_resume`
- `power/wakeup_source_activate`
- `power/wakeup_source_deactivate`
- `power/cpu_idle`

下面的 Perfetto 配置用于观察 suspend、wakeup source、CPU idle 和调度活动：

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "sched/sched_switch"
      atrace_categories: "power"
    }
  }
}
```

Android 17 PMS 还会在 `SuspendBlockers` track 发出 async trace。分析顺序是：

1. 标记屏幕/interactive 状态变化。
2. 查 `PowerManagerService.WakeLocks` 与 Display blocker 何时释放。
3. 查 wakeup source 是否持续 active。
4. 用 `suspend_resume` 确认是否进入/退出系统睡眠流程。
5. 恢复后查看第一批 IRQ、wakeup reason、线程和硬件活动。
6. 把周期性唤醒与 Alarm、Job、网络、GNSS 或 vendor 驱动关联。

“某 App 有 WakeLock”与“该锁阻止了本次 suspend”仍需时间重叠证据。系统服务可能代表 App 持锁，硬件 wakeup source 也可能没有直接 App tag。

### 第三步：看长时间统计

Batterystats 用于跨数小时或一天观察 UID 归因：

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history
# 复现场景后
adb bugreport /path/to/output/bugreport.zip
```

重置会清除旧统计，只应在受控测试开始前执行。测试时断开 USB 或固定供电条件，记录亮度、网络、信号、电量、温度和场景时间。

Battery Historian 可以读取 bugreport 并显示 Userspace Wakelock、JobScheduler、SyncManager、进程状态等长时间线。但官方已注明它不再积极维护；能用 system tracing、Macrobenchmark power metric 或 Android Studio Power Profiler 时，应优先采用这些工具。Historian 适合查看历史关联，不适合作为精确能量仪表。

### 第四步：验证能量

要判断优化是否省电，应保持工作量和环境一致，比较：

- 完成时间与成功率；
- suspend residency 与唤醒次数；
- CPU/GPU/网络/GNSS 活动；
- 设备提供的 power rail/ODPM 数据；
- 电池电流/电量统计；
- 条件允许时的外部电源仪表。

Perfetto energy consumer、Power Profiler 或 rail 数据是否存在取决于设备 HAL 和硬件。AOSP 不保证通过 RAPL 或静态 Energy Model 就能得到每进程真实能耗。

## WakeLock 滥用模式

### 忘记释放或异常路径泄漏

典型表现是 tag 在业务结束后仍持续 active。修复方式是缩小持锁作用域，使用 `try/finally` 和超时，并为错误、取消和进程生命周期分别测试。

### 锁粒度过大

把整个网络请求、重试等待和解析流程包在同一 WakeLock 中，会把不可控等待也算入持锁区间。可由系统 scheduler 管理的工作应移交给对应 API；必须手工持锁时，只覆盖无法安全 suspend 的临界阶段。

### 高频短锁导致反复唤醒

单次锁很短也可能有问题：频繁 Alarm、轮询或推送重试会反复唤醒 SoC 和无线电。按 tag 汇总总时长之外，还要统计 acquire 次数、间隔和与硬件活动的关系。

### 隐式 WakeLock

音频、位置、下载、JobScheduler 等系统 API 可能代表应用持锁。看到陌生 tag 时先查 WorkSource、UID 与发起 API，不要只在代码库搜索 `newWakeLock`。

### Android vitals 口径

截至 2026 年 Android vitals 文档，非豁免 partial WakeLock 在 24 小时内累计达到 2 小时会被报告为 excessive；这里仅统计应用处于后台或运行 foreground service 时持有的时长。若 28 天窗口内受影响会话超过 5%，从 2026 年 3 月 1 日起可能影响 Play 可见性。音频、位置和 JobScheduler user-initiated API 等用户收益明确的场景有统计豁免。

这是 Play 质量政策指标，可能更新，也不等同于系统强制释放阈值。应用内部应采用更严格、与业务时限匹配的预算。

## 一套可复现的排障方法

### 先做时间线归因

1. 记录用户操作、屏幕状态和问题区间。
2. 确认系统是否进入 suspend；若没有，找持续 blocker/wakeup source。
3. 若系统反复醒来，按唤醒间隔和 wakeup reason 聚类。
4. 对齐 App Alarm、Job、网络、GNSS、音频和推送。
5. 找到造成无效工作或阻止休眠的最小代码路径。

### 再做 A/B

- 保持设备、构建、环境温度、亮度、信号和电量区间一致。
- 让测试包含足够长的灭屏或后台阶段。
- 交错执行基线与候选版本，避免热机/冷机偏差。
- 同时比较功能正确性；省电不能靠漏同步或丢通知换取。
- 报告中区分 modeled energy、rail measurement、battery delta 与外部仪表。

### 最终选择修复层

| 证据 | 优先修复 |
| --- | --- |
| 手工 WakeLock 覆盖过大 | 缩小作用域或交给系统 scheduler |
| 周期性 Alarm 唤醒 | 合并、延后或改用 Job/WorkManager |
| 网络建链过于频繁 | 批量传输、推送触发、退避 |
| GNSS/传感器持续活跃 | 调整请求频率、batching、生命周期 |
| Job 在不合适条件运行 | 补充真实 constraints、拆分可中断批次 |
| kernel wakeup source 异常 | 驱动/firmware 侧调查，不归因给 App WakeLock |
| 屏幕/刷新持续高功率 | 到显示与渲染章节分析亮度、刷新和合成 |

## 常见误区

### “代码没调用 newWakeLock，就不会阻止休眠”

系统 API 可以代表应用持锁，Alarm、网络、音频、GNSS 和驱动 wakeup source 也能使设备保持活跃或反复唤醒。要从 UID/WorkSource 和时间线追到发起 API。

### “持有 PARTIAL_WAKE_LOCK 就能绕过 Doze”

Doze 会忽略普通应用 WakeLock，并限制网络、Job、Sync 和 Alarm。部分豁免也不取消全部后台政策。

### “WorkManager 保证指定时刻执行”

WorkManager 保证持久化和按约束调度的能力；执行时间仍受系统状态影响。精确用户提醒应使用符合政策的 Alarm API。

### “CPU idle 等于 system suspend”

cpuidle 是单 CPU 的运行时空闲，system suspend 是全系统状态转换。用 `suspend_resume`、blocker 和 wakeup source 判断系统休眠。

### “Batterystats 的耗电百分比就是实测能量”

Batterystats 包含记账和模型估算。硬件 rail、采样周期和归因能力因设备而异，精确能量结论需要说明测量来源。

## 版本边界

| Android 版本 | 主要变化 | 说明 |
| --- | --- | --- |
| Android 5 / API 21 | JobScheduler | 把可延期后台工作交给系统批处理 |
| Android 6 / API 23 | Doze、App Standby | 设备级与应用级后台限制 |
| Android 7 / API 24 | Light Doze、后台广播优化 | 灭屏后更早限制更多活动 |
| Android 8 / API 26 | 后台执行与前台服务限制 | 长期后台服务受到更强约束 |
| Android 9 / API 28 | App Standby Buckets、Adaptive Battery | bucket 可由使用历史或预测影响 |
| Android 12 / API 31 | RESTRICTED bucket | 增加更严格的应用级资源限制 |
| Android 13 / API 33 | Low Power Standby、RESTRICTED bucket 规则更新 | 非交互阶段可进一步限制网络和 WakeLock；restricted 行为仍需按设备核对 |
| Android 14 / API 34 | Low Power Standby policy 查询 | 增加豁免、allowed reason 与 allowed feature 查询 |
| Android 16 / API 36 | Active bucket Job runtime quota 等规则调整 | WorkManager/DownloadManager 也受平台 Job quota 影响 |
| Android 17 / API 37 | 以 `android-17.0.0_r1` PMS、SystemSuspend、JobScheduler APEX 为准 | 不假设新的固定 Doze 时序或 vendor 策略 |

## Android 17 / kernel 6.18 源码索引

| 主题 | 精确路径 |
| --- | --- |
| PMS | `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` |
| WakeLock API | `frameworks/base/core/java/android/os/PowerManager.java` |
| PMS JNI | `frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp` |
| 统计转发 | `frameworks/base/services/core/java/com/android/server/power/Notifier.java` |
| Batterystats | `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`、`services/core/java/com/android/server/power/stats/BatteryStatsImpl.java` |
| Power HAL | `hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl` |
| JobScheduler | `frameworks/base/apex/jobscheduler/` |
| Kernel sleep | `Documentation/admin-guide/pm/sleep-states.rst`、`include/trace/events/power.h` |

## 参考资料

- AOSP `android-17.0.0_r1`：上述 Framework、SystemSuspend 与 Power HAL 源码
- Linux kernel `android17-6.18-2026-06_r6`：system sleep 文档与 power tracepoints
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Background optimization](https://developer.android.com/topic/performance/background-optimization)
- [PowerManager：Low Power Standby](https://developer.android.com/reference/android/os/PowerManager#isLowPowerStandbyEnabled())
- [Batterystats and Battery Historian setup](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [Excessive partial WakeLocks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [WorkManager task scheduling](https://developer.android.com/develop/background-work/background-tasks/persistent)
