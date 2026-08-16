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
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
related_chapters:
  - "5.1"
  - "5.2"
  - "5.4"
---

# 5.6 Android 功耗管理

> [!NOTE] 源码锚点
> 平台实现以 Android 开源项目（AOSP）`android-17.0.0_r1`（Android 17 / API 37）为准，Linux 内核休眠与唤醒机制以 `android17-6.18-2026-06_r6` 为准。Doze 时序、应用待机分桶（App Standby Buckets）、功率模型与厂商电源硬件抽象层（Power HAL）策略都允许由设备配置，因此不使用固定分钟数或固定频率描述通用行为。

## 功耗排障先回答三个问题

一次“耗电高”可能来自完全不同的机制。开始分析前先分开：

1. **谁在消耗能量**：CPU、GPU、显示、蜂窝、Wi-Fi、全球卫星导航系统（GNSS）、相机或充电电路；
2. **系统为什么没有休眠**：应用唤醒锁（WakeLock）、内核唤醒源（wakeup source）、定时器、中断或系统恢复流程；
3. **工作为什么在这个时间发生**：前台业务、定时任务（Alarm）、作业调度器（JobScheduler）、持久化任务库 WorkManager、推送、Doze 维护窗口或后台限制豁免。

WakeLock 主要回答第二个问题。它不能解释 CPU 为什么繁忙，也不能覆盖显示或无线射频的全部能量。可靠的判断通常需要把系统状态、组件活动和能量数据放到同一时间轴。

## 从 PowerManagerService 到系统挂起

### 四个不同层次

Android 17 的功耗主路径可以分为四层：

| 层次 | 主要对象 | 职责 |
| --- | --- | --- |
| 应用/Framework API | `PowerManager.WakeLock`、屏幕标志（screen flags）、Job/Alarm API | 表达“暂时保持某种运行条件” |
| `system_server` | `PowerManagerService`（PMS） | 汇总 WakeLock、显示、唤醒状态（wakefulness）和用户活动，维护挂起阻止器（suspend blocker） |
| 原生层/系统服务 | PMS 的 JNI、`ISystemSuspend`、挂起控制服务 | 开关自动挂起（autosuspend），获取或释放原生 suspend blocker |
| Linux 内核/平台 | wakeup source、系统挂起（system suspend）、设备驱动、固件 | 冻结用户空间、挂起设备、进入平台支持的睡眠状态并处理唤醒 |

应用 WakeLock 与内核 wakeup source 有关联，却不是同一个对象。PMS 会把满足条件的 Framework WakeLock 汇总到名为 `PowerManagerService.WakeLocks` 的 suspend blocker；硬件驱动也可以独立注册 wakeup source。

### Android 17 的准确调用边界

`PowerManagerService.java` 中可以定位到：

- `mWakeLockSuspendBlocker`、`mDisplaySuspendBlocker` 和启动阶段 blocker（boot blocker）；
- `nativeAcquireSuspendBlocker()` / `nativeReleaseSuspendBlocker()`；
- `nativeSetAutoSuspend()`；
- `nativeSetPowerMode()`。

JNI（Java Native Interface，Java 原生接口）文件 `com_android_server_power_PowerManagerService.cpp` 连接 `ISystemSuspend` 与挂起控制服务（suspend control service）。启用 autosuspend 后，只要没有有效的 blocker，内核和平台就可以尝试进入 system suspend。

PMS 还会用 `Mode.INTERACTIVE` 向 AIDL（Android Interface Definition Language，Android 接口定义语言）Power HAL 通知交互状态。这个模式由厂商映射到自己的电源策略；一次普通的 WakeLock 获取（acquire）没有“AOSP 固定调用 `Boost.INTERACTION` 若干毫秒”的通用链路，也不会直接命令 schedutil 升到某个频点。

### CPU 空闲与系统挂起

这两个状态必须分开：

- **CPU 空闲（CPU idle）**：某个 CPU 暂时没有可运行任务，进入一个 cpuidle 状态；其他 CPU 和用户空间仍可能继续工作。
- **系统挂起（system suspend）**：全系统进入低功耗状态，用户空间被冻结，设备被挂起，CPU 由平台的 suspend 流程处理。
- **挂起到空闲（suspend-to-idle，s2idle）**：一种较轻的 system suspend；CPU 可以停留在深度空闲状态，但仍要经过冻结用户空间和挂起设备的系统流程。
- **挂起到内存（suspend-to-RAM）**：平台支持时可以进入更深状态，内存自刷新，更多设备与总线断电或进入低功耗状态。

因此，“CPU idle 比例接近 100%”不能证明系统已经挂起；Trace 中没有调度切片（slice）也可能只是采集缺失。应使用 `power/suspend_resume` 等事件确认 system suspend 的边界。

### CPUIdle 与 schedutil 分别处理空闲和运行需求

cpuidle governor（空闲状态选择策略）只在 CPU 已经没有可运行等待态（runnable）的任务、准备进入 idle 时选择空闲状态；schedutil 则在 CPU 执行或负载变化时，把利用率需求映射成 Linux CPU 调频框架 CPUFreq 的请求。PMS 可以通过交互状态、suspend blocker 与 Power HAL mode 改变外部条件，但不会替内核逐 CPU 选择 idle state 或频率。一次唤醒中常会同时出现退出 idle、任务进入 runnable、升频和 Framework 交互提示；这些事件时间相邻，不代表存在一条固定的 PMS → cpuidle → schedutil 调用链。

## WakeLock：类型、语义与责任

### 普通应用最常用的是 PARTIAL_WAKE_LOCK

Android 17 `PowerManager` 定义的主要 WakeLock 等级（level）包括：

| 等级 | 语义 | 普通应用建议 |
| --- | --- | --- |
| `PARTIAL_WAKE_LOCK` | 保持 CPU 执行，屏幕可以关闭 | 仅在没有更合适 API 时短时使用 |
| `SCREEN_DIM_WAKE_LOCK` | 保持屏幕点亮，可变暗 | 已废弃，使用 `FLAG_KEEP_SCREEN_ON` |
| `SCREEN_BRIGHT_WAKE_LOCK` | 保持屏幕高亮 | 已废弃 |
| `FULL_WAKE_LOCK` | 保持屏幕和键盘背光 | 已废弃 |
| `PROXIMITY_SCREEN_OFF_WAKE_LOCK` | 由接近传感器控制屏幕 | 先检查设备支持，典型用于通话 |
| `DOZE_WAKE_LOCK` / `DRAW_WAKE_LOCK` | 系统内部用途 | 普通应用不可按公共能力依赖 |

`PowerManager.newWakeLock()` 只创建客户端对象；调用 `acquire()` 后，请求才会经 Android 跨进程调用机制 Binder 送到 PMS。`ACQUIRE_CAUSES_WAKEUP` 也已废弃；需要点亮屏幕的 Activity 应使用 `setTurnScreenOn()` 或清单属性等面向窗口的 API。

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

代码把持锁时间限制为 30 秒：超时用于防止异常路径长期持锁，`finally` 负责在正常或异常结束时释放。应用仍需声明 `android.permission.WAKE_LOCK`。如果工作可以交给 WorkManager、JobScheduler、媒体播放、位置或下载框架，应让对应 API 管理 WakeLock 和系统约束，减少手工持锁。

还要注意引用计数：WakeLock 默认按获取（acquire）和释放（release）次数配对。调用 `setReferenceCounted(false)` 后，一次 release 可以结束多次 acquire 的效果；混用两种计数规则很容易导致提前释放或锁泄漏。

### WorkSource 负责归因

系统服务代表其他用户 ID（UID）工作时，可以用 `WorkSource` 把 WakeLock 成本归因给实际请求者。普通应用不能用它把自身功耗随意归到别处；权限和来源链由系统校验。排障时应同时记录标签（tag）、持有者 UID 与 WorkSource，避免只按持锁进程判断责任。

### 缓存进程的 WakeLock 可能被禁用

Android 17 PMS 有 `no_cached_wake_locks` 等配置与缓存进程（cached process）判断，可以把某些 WakeLock 标记为禁用（disabled）。具体条件还涉及 UID 状态、豁免、锁类型和设备配置。

因此，应用不能把 `PARTIAL_WAKE_LOCK` 当作后台永久运行承诺。即使应用内的对象仍显示 `isHeld`，系统也不会因此保证所有后台能力、网络或 Job 调度都不受限制。

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

释放路径使用 `noteStopWakelock*()`。`WorkSource`、历史标签（history tag）、UID、进程 ID（PID）和锁标志（lock flags）都会影响归因。

Batterystats 是 Android 的功耗记账系统，适合回答“某 UID 在多长时间内持有哪些锁、触发哪些 Job、Alarm 或网络活动”。它不是物理电表：统计时长和模型估算不能自动转换成精确焦耳，尤其无法只靠 WakeLock 时长推导屏幕、射频或 GPU 能量。

## Doze、App Standby 与其他省电状态

### 不要把几个名字合并成一个“后台限制”

| 机制 | 作用范围 | 主要触发依据 | 典型影响 |
| --- | --- | --- | --- |
| 省电模式（Battery Saver） | 全设备 | 用户或系统省电策略 | 系统可能降低性能、限制网络访问、减少动画并延后后台任务 |
| 低电耗模式（Doze） | 全设备空闲状态 | 灭屏、未充电、静止或空闲等设备条件 | 网络、Job、同步（Sync）和普通 Alarm 延后，WakeLock 被忽略 |
| 应用待机（App Standby） | 单个应用 | 用户近期是否使用该应用 | 后台网络、Job 和 Alarm 受限 |
| 应用待机分桶（App Standby Buckets） | 单个应用 | 使用频率、预测与系统策略 | 不同待机桶（bucket）获得不同预算 |
| 后台受限（Background restricted） | 单个应用的用户或系统限制 | 用户设置或系统提示后的选择 | 后台执行可受到更强限制 |
| 低功耗待机（Low Power Standby） | 设备非交互后的更深策略 | 平台支持、配置与豁免（exemptions） | 网络和 WakeLock 等能力进一步受限 |

这些机制可以叠加。一次 Job 延迟可能同时受到 Doze、standby bucket、后台限制、配额（quota）、网络约束和温控状态影响。

Low Power Standby 开启后，当设备处于非交互状态且不在设备空闲（device-idle）维护窗口时，应用的网络访问会被禁用，持有的 WakeLock 会被忽略；运行前台服务（foreground service）的应用也在限制范围内。Android 14 / API 34 增加了 `isExemptFromLowPowerStandby()` 与 `isAllowedInLowPowerStandby()`，用于查询当前策略下的豁免和允许能力。这些查询只描述 Low Power Standby，不能代替 Doze 允许名单（allowlist）、standby bucket 或用户后台限制检查。

### Doze 的行为

设备满足平台定义的空闲条件后进入 Doze。Android 不向应用承诺“灭屏 30 分钟后进入”等固定时间；浅度和深度 Doze（Light/Deep）的状态机延迟、维护窗口与运动检测都可以由系统配置。

Doze 期间，普通应用通常会遇到：

- 网络访问暂停；
- 未获豁免应用的 `PARTIAL_WAKE_LOCK` 被忽略；
- JobScheduler、WorkManager 和 Sync 延后；
- 普通 Alarm 延后到维护窗口；
- Wi-Fi 扫描等高成本操作受限。

`setAndAllowWhileIdle()`、`setExactAndAllowWhileIdle()` 和闹钟提醒（alarm clock）有特定例外，但调用频率与权限仍受限制。Firebase Cloud Messaging（FCM）高优先级消息适合会产生用户可见通知的时效消息；用它维持静默心跳可能被降级，也会增加功耗。

Doze 会周期性进入维护窗口，批量执行部分待处理工作。窗口间隔会随空闲延长而变化，应用不能依赖具体分钟数。

### 电池优化豁免是部分豁免

豁免名单中的应用可以在 Doze 或 App Standby 中使用网络并持有 `PARTIAL_WAKE_LOCK`，但这不等于解除所有 Alarm、Job、Sync、后台启动与平台政策。Google Play 对直接申请豁免也有适用场景限制。

应用可以用 `PowerManager.isIgnoringBatteryOptimizations()` 查询自身状态。大多数业务应先采用 FCM、JobScheduler、WorkManager、前台服务或专用系统 API；只有核心功能在 Doze 下无法工作且符合政策时，再引导用户查看豁免设置。

### App Standby Buckets

Android 17 仍使用以下主要待机桶：

- `ACTIVE`
- `WORKING_SET`
- `FREQUENT`
- `RARE`
- `RESTRICTED`
- 另有从未运行等特殊状态。

待机桶会影响 Job、Alarm 和后台网络预算。系统可以依据近期使用情况分配，也可以由预装预测组件利用机器学习判断未来使用概率；原始设备制造商（OEM）可以调整非 `ACTIVE` 应用的分配标准。应用不应尝试操纵待机桶，只需保证在各个桶中功能都可以恢复。

`UsageStatsManager.getAppStandbyBucket()` 可以查询当前 bucket。测试设备可用下面的命令改变和读取状态：

```bash
adb shell am set-standby-bucket com.example.app rare
adb shell am get-standby-bucket com.example.app
```

测试结束后应恢复原待机桶。待机桶只是一个变量，Doze、充电状态、后台限制和 Job 约束仍要分别记录。

### RESTRICTED bucket 与“后台受限”设置

当前官方文档对 `RESTRICTED` bucket 给出严格预算：通常把 Job 集中到每天一次、最长约 10 分钟的批处理会话，Alarm 也大幅受限；充电时仍可能保留限制，只在特定的充电、空闲和非计量网络条件组合下放宽。

这些是 Android 当前的高层行为，设备厂商仍可决定分桶条件和部分限制细节。设备所有者（device owner）、资料所有者（profile owner）、虚拟专用网络（VPN）、默认拨号应用（dialer）、持久系统应用（persistent app）和用户设为“不受限制”（unrestricted）的应用等，可能获得豁免；“正在运行任意前台服务”不是通用的 `RESTRICTED` bucket 豁免条件。

系统设置中的“Restricted/后台受限”表示用户明确禁止后台活动，与预测得到的 standby bucket 不是同一个状态。两者都可能使 Job、Alarm、网络和前台服务启动受限，排障时要分别读取。

### Adaptive Battery 的准确边界

自适应电池（Adaptive Battery）可以借助预测结果影响 standby bucket 和后台资源分配。AOSP 和官方 API 没有“Adaptive Battery 2.0”这一公共技术名称，也没有跨设备固定的机器学习（ML）模型、输入特征或省电百分比。

可以确认的边界是：应用所在的 bucket 会动态变化，OEM 可以提供预测组件；应用应使用系统调度 API，并正确处理延迟、停止和重试。

### Low Power Standby 在非交互期间限制网络与 WakeLock 效力

Low Power Standby（LPS）与 Doze、App Standby 和应用休眠（App Hibernation）是不同的状态机。Android 13 起，LPS 可以在设备进入非交互状态并超过配置的超时时间后启用；Android 17 的 Framework 主要把策略交给两个使用方：网络策略限制部分后台 UID 的联网能力，PowerManagerService 则让不在允许范围内的 WakeLock 不再阻止低功耗状态。

LPS 不会删除 WakeLock，也不会取消 Job。设备恢复交互，或应用符合软件包（package）、功能（feature）、允许原因（allowed reason）等豁免条件后，限制可以解除。验证时应读取 `dumpsys power` 中的 Low Power Standby 状态与 policy，并同时观察网络访问、WakeLock、suspend blocker 和 `power/suspend_resume`；只看到一次请求超时，无法区分 LPS、Doze、待机桶或网络故障。

## JobScheduler 与 WorkManager

### 为什么它们通常比手工 WakeLock 合适

JobScheduler 能根据充电、网络、空闲、存储和配额等条件，批量执行多个应用的可延期工作，从而减少频繁唤醒和无线电重复建立连接。WorkManager 在现代 Android 上通常借助 JobScheduler 执行任务，并提供持久化、任务依赖关系和跨版本适配。

它们不承诺精确执行时间，也不会取消 Doze、App Standby、温控或配额限制。Android 17 的详细 JobScheduler 机制见 [5.8 JobScheduler/WorkManager](08-jobscheduler-workmanager-performance.md)。

### 选择 API

| 需求 | 首选方向 |
| --- | --- |
| 可延期且需要可靠完成 | WorkManager |
| 平台或系统组件按条件运行的后台任务 | JobScheduler |
| 用户刚发起且可见的大文件传输 | 用户发起的数据传输作业（User-initiated data transfer job） |
| 用户可感知、需要持续运行的工作 | 符合类型与权限要求的前台服务（foreground service） |
| 精确的用户提醒 | AlarmManager，按精确闹钟（exact alarm）政策使用 |
| 进程存活期内的短异步工作 | 协程或执行器（coroutine/executor），不需要持久化调度器 |

不要为了“早点运行”同时叠加 WakeLock、exact alarm、foreground service 和加急工作（expedited work）。每种机制都有独立成本与政策，应按业务语义选择足够完成任务的最小集合。

## 检测 WakeLock 与 suspend 问题

### 第一步：看当前状态

`dumpsys power` 能显示 PMS 当前的 wakefulness、suspend blocker 和 WakeLock。下面的命令只读取状态：

```bash
adb shell dumpsys power
adb shell cat /sys/kernel/debug/wakeup_sources
```

第二个节点需要相应的内核配置、权限和安全增强型 Linux（Security-Enhanced Linux，SELinux）许可，量产设备上可能无法读取。输出中的活跃次数（active count）、事件次数（event count）、活跃时长（active time）和唤醒次数（wakeup count），其具体语义由内核 wakeup-source 统计决定。

### 第二步：抓取系统 Trace

Linux 6.18 的 `include/trace/events/power.h` 定义了以下 ftrace 内核跟踪事件：

- `power/suspend_resume`
- `power/wakeup_source_activate`
- `power/wakeup_source_deactivate`
- `power/cpu_idle`

下面的 Perfetto 配置用于观察系统挂起、wakeup source、CPU idle 和调度活动：

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

Android 17 PMS 还会在 `SuspendBlockers` 轨道（track）中写入异步 Trace（async trace）。可以按以下顺序分析：

1. 标记屏幕和交互（interactive）状态变化；
2. 检查 `PowerManagerService.WakeLocks` 与显示挂起阻止器（Display blocker）何时释放；
3. 检查 wakeup source 是否持续处于活跃状态；
4. 用 `suspend_resume` 确认是否进入或退出系统睡眠流程；
5. 恢复后查看第一批硬件中断（IRQ）、唤醒原因（wakeup reason）、线程和硬件活动；
6. 把周期性唤醒与 Alarm、Job、网络、GNSS 或厂商驱动关联。

“某应用有 WakeLock”与“该锁阻止了本次 system suspend”之间，仍需要时间重叠证据。系统服务可能代表应用持锁，硬件 wakeup source 也可能没有直接对应的应用标签。

### 第三步：看长时间统计

Batterystats 可用于跨数小时或一天观察 UID 归因。下面的命令先清空旧统计并启用完整 WakeLock 历史，然后在复现场景后生成 bugreport：

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history
# 复现场景后
adb bugreport /path/to/output/bugreport.zip
```

重置会清除旧统计，只应在受控测试开始前执行。测试时应断开 USB 或固定供电条件，并记录亮度、网络、信号、电量、温度和场景时间。

Battery Historian 可以读取 bugreport，并显示用户空间 WakeLock（Userspace Wakelock）、JobScheduler、同步管理器（SyncManager）和进程状态等长时间线。但官方已注明该工具不再积极维护；能够使用系统跟踪（system tracing）、Macrobenchmark 功耗指标（power metric）或 Android Studio Power Profiler 时，应优先采用这些工具。Historian 适合查看历史关联，不适合作为精确能量仪表。

### 第四步：验证能量

要判断优化是否省电，应保持工作量和环境一致，比较：

- 完成时间与成功率；
- system suspend 驻留时间（residency）与唤醒次数；
- CPU/GPU/网络/GNSS 活动；
- 设备提供的电源轨（power rail）或片上功耗监测（On-Device Power Monitor，ODPM）数据；
- 电池电流/电量统计；
- 条件允许时的外部电源仪表。

Perfetto 能量消费者（energy consumer）、Power Profiler 或电源轨数据是否存在，取决于设备 HAL 和硬件。AOSP 不保证通过运行平均功率限制（Running Average Power Limit，RAPL）或静态能量模型（Energy Model）就能得到每个进程的真实能耗。

## WakeLock 滥用模式

### 忘记释放或异常路径泄漏

典型表现是业务结束后，WakeLock 标签仍长时间处于活跃状态。修复时应缩小持锁作用域，使用 `try/finally` 和超时，并分别测试错误、取消与进程生命周期路径。

### 锁粒度过大

把整个网络请求、重试等待和解析流程包在同一个 WakeLock 中，会把不可控等待也纳入持锁区间。能够由系统调度器管理的工作应移交给相应 API；必须手工持锁时，只覆盖不能安全进入 system suspend 的必要阶段。

### 高频短锁导致反复唤醒

单次持锁很短也可能有问题：频繁的 Alarm、轮询或推送重试会反复唤醒片上系统（System on Chip，SoC）和无线电。除了按标签汇总总时长，还要统计 acquire 次数、间隔及其与硬件活动的关系。

### 隐式 WakeLock

音频、位置、下载和 JobScheduler 等系统 API 可能代表应用持锁。看到陌生标签时，应先检查 WorkSource、UID 与发起 API，不要只在代码库中搜索 `newWakeLock`。

### Android vitals 口径

截至 2026 年的 Android vitals 文档，非豁免的 partial WakeLock 在 24 小时内累计达到 2 小时，会被报告为过度使用（excessive）；这里只统计应用处于后台或运行前台服务时的持锁时长。如果 28 天窗口内受影响的会话超过 5%，从 2026 年 3 月 1 日起可能影响应用在 Google Play 中的可见性。音频、位置和 JobScheduler 用户发起（user-initiated）API 等用户收益明确的场景有统计豁免。

这是 Google Play 的质量政策指标，可能更新，也不等同于系统强制释放 WakeLock 的阈值。应用内部应采用更严格、与业务时限匹配的预算。

## 一套可复现的排障方法

### 先做时间线归因

1. 记录用户操作、屏幕状态和问题区间；
2. 确认系统是否进入 system suspend；如果没有，查找持续存在的 suspend blocker 或 wakeup source；
3. 如果系统反复唤醒，按唤醒间隔和 wakeup reason 分组；
4. 对齐应用 Alarm、Job、网络、GNSS、音频和推送；
5. 找到造成无效工作或阻止休眠的最小代码路径。

### 再做 A/B 对照

- 保持设备、系统构建、环境温度、亮度、信号和电量区间一致；
- 让测试包含足够长的灭屏或后台阶段；
- 交错执行基线与候选版本，避免热机和冷机偏差；
- 同时比较功能正确性；不能通过漏同步或丢通知来换取省电；
- 在报告中区分模型估算能量（modeled energy）、电源轨测量（rail measurement）、电池电量变化（battery delta）与外部仪表结果。

### 最终选择修复层

| 证据 | 优先修复 |
| --- | --- |
| 手工 WakeLock 覆盖过大 | 缩小作用域或交给系统调度器 |
| 周期性 Alarm 唤醒 | 合并、延后或改用 Job/WorkManager |
| 网络建链过于频繁 | 批量传输、推送触发、退避 |
| GNSS/传感器持续活跃 | 调整请求频率、批处理（batching）和生命周期 |
| Job 在不合适的条件下运行 | 补充真实约束（constraints），拆分可中断批次 |
| 内核 wakeup source 异常 | 在驱动或固件侧调查，不要归因给应用 WakeLock |
| 屏幕/刷新持续高功率 | 到显示与渲染章节分析亮度、刷新和合成 |

## 常见误区

### “代码没调用 newWakeLock，就不会阻止休眠”

系统 API 可以代表应用持锁；Alarm、网络、音频、GNSS 和驱动 wakeup source 也能让设备保持活跃或反复唤醒。要根据 UID、WorkSource 和时间线追查到发起 API。

### “持有 PARTIAL_WAKE_LOCK 就能绕过 Doze”

Doze 会忽略普通应用的 WakeLock，并限制网络、Job、Sync 和 Alarm。部分豁免也不会取消全部后台政策。

### “WorkManager 保证指定时刻执行”

WorkManager 提供持久化和按约束调度的能力；执行时间仍受系统状态影响。精确的用户提醒应使用符合政策的 Alarm API。

### “CPU idle 等于 system suspend”

cpuidle 是单 CPU 的运行时空闲，system suspend 是全系统状态转换。用 `suspend_resume`、blocker 和 wakeup source 判断系统休眠。

### “Batterystats 的耗电百分比就是实测能量”

Batterystats 包含记账和模型估算。硬件电源轨、采样周期和归因能力因设备而异；给出精确能量结论时，需要说明测量来源。

## 版本边界

| Android 版本 | 主要变化 | 说明 |
| --- | --- | --- |
| Android 5 / API 21 | JobScheduler | 把可延期后台工作交给系统批处理 |
| Android 6 / API 23 | Doze、App Standby | 设备级与应用级后台限制 |
| Android 7 / API 24 | Light Doze、后台广播优化 | 灭屏后更早限制更多活动 |
| Android 8 / API 26 | 后台执行与前台服务限制 | 长期后台服务受到更强约束 |
| Android 9 / API 28 | App Standby Buckets、Adaptive Battery | bucket 可由使用历史或预测影响 |
| Android 12 / API 31 | RESTRICTED bucket | 增加更严格的应用级资源限制 |
| Android 13 / API 33 | Low Power Standby、`RESTRICTED` bucket 规则更新 | 非交互阶段可进一步限制网络和 WakeLock；受限行为仍需按设备核对 |
| Android 14 / API 34 | Low Power Standby policy 查询 | 增加豁免、allowed reason 与 allowed feature 查询 |
| Android 16 / API 36 | `ACTIVE` bucket 的 Job 运行时配额等规则调整 | WorkManager/DownloadManager 也受平台 Job 配额影响 |
| Android 17 / API 37 | 以 `android-17.0.0_r1` PMS、SystemSuspend、JobScheduler APEX 模块为准 | 不假设新的固定 Doze 时序或厂商策略 |

## Android 17 / Linux 6.18 源码索引

| 主题 | 精确路径 |
| --- | --- |
| PMS | `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` |
| WakeLock API | `frameworks/base/core/java/android/os/PowerManager.java` |
| PMS JNI | `frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp` |
| 统计转发 | `frameworks/base/services/core/java/com/android/server/power/Notifier.java` |
| Batterystats | `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`、`services/core/java/com/android/server/power/stats/BatteryStatsImpl.java` |
| Power HAL | `hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl` |
| JobScheduler | `frameworks/base/apex/jobscheduler/` |
| Linux 内核休眠 | `Documentation/admin-guide/pm/sleep-states.rst`、`include/trace/events/power.h` |

## 参考资料

- AOSP `android-17.0.0_r1`：上述 Framework、SystemSuspend 与 Power HAL 源码
- Linux 内核 `android17-6.18-2026-06_r6`：系统休眠文档与 power 跟踪点（tracepoints）
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Background optimization](https://developer.android.com/topic/performance/background-optimization)
- [PowerManager：Low Power Standby](https://developer.android.com/reference/android/os/PowerManager#isLowPowerStandbyEnabled())
- [Batterystats and Battery Historian setup](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [Excessive partial WakeLocks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [WorkManager task scheduling](https://developer.android.com/develop/background-work/background-tasks/persistent)
