---
title: "Android 17 FGS 类型声明与后台执行性能边界"
chapter: "5.17"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [fgs, foreground-service, background-execution, android17, battery, scheduling, anr]
related_chapters: ["5.8", "5.10", "9.2", "25.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
drafted_date: "2026-06-05"
last_verified: "2026-06-05"
last_verified_against: "AOSP android-17.0.0_r1 (ActiveServices.java, ServiceRecord.java, AnrTimer.java); developer.android.com foreground service docs"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ServiceRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Service.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ForegroundServiceTypePolicy.java"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/service-types"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/timeout"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: research
    path: "DeepResearch/Android 14 → Android 17 Foreground Service Timeout : ANR 机制深度解析(AOSP 源码视角).md"
---

# 5.17 Android 17 FGS 类型声明与后台执行性能边界

Android 14 把前台服务从"声明一个就能跑"变成"声明类型 + 补齐权限 + 接受时长预算"。到 Android 17，这套约束已经演进出三类时间边界——`shortService` 的 3 分钟硬超时、`dataSync`/`mediaProcessing` 的 6 小时滚动窗口、以及后台启动 FGS 的 5 秒通知挂出窗口——每类边界背后都有独立的系统惩罚路径。

本节聚焦这些边界在 `system_server` 内部的实现机制和性能影响：超时判定怎么触发、ANR 和 Crash 走哪些不同的代码路径、冻结进程和超时计时器怎么交互、以及 Android 17 在 While-In-Use（WIU）能力判定上的变化。后台执行模型的演进脉络和各 FGS 类型的使用场景，详见 5.8 节；应用层的超时治理和 WorkManager 迁移策略，详见 25.13 节。

## FGS 类型声明机制与版本演进

### 从无类型到强制类型

Android 13 及以前，前台服务不需要声明类型。`startForeground(notificationId, notification)` 一个调用就够了。Android 14（API 34）要求 `foregroundServiceType` 必须声明，同时要求对应权限。Android 15（API 35）把 `dataSync` 和 `mediaProcessing` 纳入 6 小时预算管理，并新增 `onTimeout(int startId, int fgsType)` 双参数回调。Android 16（API 36）没新增超时类型，但让与 FGS 并发的 Job 回到 runtime quota 约束下。Android 17（API 37）在 timeout 框架本身没有新增类型，但强化了两类边界条件：

1. **WIU（While-In-Use）能力判定**：Android 17 对后台音频场景的 FGS 要求非 `SHORT_SERVICE` 类型且具备 WIU 能力，或同时持有 exact alarm 权限并使用 `USAGE_ALARM` 用途。这意味着后台启动 FGS 的合法性检查多了一层"能力"维度，不再只看类型和权限。[已验证: developer.android.com/about/versions/17/behavior-changes-17]
2. **AnrTimer 冻结感知扩大**：`mActiveServiceAnrTimer` 在 Android 17 上使用 `AnrTimer.Args().freeze(true)` 构造，当目标进程被 `CachedAppOptimizer` 冻结时计时暂停、解冻后恢复。但 `mShortFGSAnrTimer`（`shortService` 专用）未设置 freeze flag——这意味着 `shortService` 超时不受进程冻结影响，即使进程已被降级并冻结，3 分钟计时仍在继续。 [已验证: AOSP ActiveServices.java, AnrTimer.java]

### 类型校验发生在哪个环节

`Service.startForeground()` 的 Binder 调用进入 `ActiveServices.setServiceForegroundInnerLocked()`，在这里系统做三件事：

1. 校验 `foregroundServiceType` 与 manifest 声明是否一致（`ForegroundServiceTypePolicy`）
2. 检查对应的运行时权限是否存在
3. 对有时间预算的类型（`shortService`、`dataSync`、`mediaProcessing`），启动或更新对应的计时器

校验不通过时，Android 14+ 直接抛 `ForegroundServiceStartNotAllowedException`（非 `RemoteServiceException` 子类，在 Binder 调用栈上同步抛回 caller，可以被 `try-catch` 捕获）。这和后文讨论的异步超时异常是两条不同的投递路径。[已验证: AOSP ActiveServices.java, ForegroundServiceTypePolicy.java]

## 各 FGS 类型的性能预算差异

三组时间边界覆盖了当前所有受约束的 FGS 类型：

| 类型 | 时间边界 | 计时粒度 | 超时惩罚 | 超出后能否重新启动同类型 |
|:---|:---|:---|:---|:---|
| `shortService` | 单次 ~3 分钟 | 单次 `startForeground()` 到 now | ANR（走 `AnrHelper`） | 可以（新一次 `startForeground` 开启新计时周期） |
| `dataSync` | 24 小时滚动窗口内累计 ~6 小时 | per-uid per-type 聚合 | `ForegroundServiceDidNotStopInTimeException`（进程 Crash，非 ANR） | 额度耗尽后再启动直接抛 `ForegroundServiceStartNotAllowedException` |
| `mediaProcessing` | 24 小时滚动窗口内累计 ~6 小时 | per-uid per-type 聚合 | 同 `dataSync` | 同 `dataSync` |
| `location`、`connectedDevice`、`health`、`mediaPlayback` 等 | 无硬性时长上限 | — | — | — |

### shortService 的三段时间线

`shortService` 在 `ServiceRecord.ShortFgsInfo` 中维护三个时间点 [已验证: AOSP ServiceRecord.java]：

```
getTimeoutTime()         = mStartTime + SHORT_FGS_TIMEOUT_DURATION        // ~3 min: onTimeout 回调
getProcStateDemoteTime() = mStartTime + SHORT_FGS_TIMEOUT_DURATION
                           + SHORT_FGS_PROCSTATE_EXTRA_WAIT_DURATION       // 进程降级为 cached
getAnrTime()             = mStartTime + SHORT_FGS_TIMEOUT_DURATION
                           + SHORT_FGS_ANR_EXTRA_WAIT_DURATION             // 触发 ANR
```

三个时间点的间隔由 `ActivityManagerConstants` 控制，可通过 `DeviceConfig` 覆盖。进程降级后，`OomAdjuster` 以 `OOM_ADJ_REASON_SHORT_FGS_TIMEOUT` 为原因码更新 adj 值——这意味着超时后的进程按 cached app 对待，可被 LMK 杀掉或被 `CachedAppOptimizer` 冻结。[已验证: AOSP OomAdjuster.java]

`mStartForegroundCount` 是单调递增的计数器。每次 `startForeground()` 调用都会递增它，`ShortFgsInfo.isCurrent()` 通过比较计数决定当前 info 是否对应最新一次前台周期——旧的 info 对应的 timeout 自动作废。这个设计允许同一个 `shortService` 实例多次进出前台状态，每次重新开始计时。

### dataSync / mediaProcessing 的滚动窗口

与 `shortService` 的 per-record 模型不同，`dataSync` 和 `mediaProcessing` 采用 per-uid per-type 的聚合对象 `ActiveServices.mTimeLimitedFgsInfo`（`SparseArray<SparseArray<TimeLimitedFgsInfo>>`）。同一个 app 下多个 `dataSync` service 共享同一个 6 小时额度。 [已验证: AOSP ActiveServices.java, ServiceRecord.java]

`TimeLimitedFgsInfo` 用 `mFirstFgsStartRealtime`（`elapsedRealtime`，非 `uptimeMillis`）标记窗口起点。24 小时后自动 `reset()`——用 `elapsedRealtime` 而非 `uptime` 的原因是把设备深度睡眠时间也算进 24 小时。当 app 被用户带入前台（`PROCESS_STATE_TOP`），AMS 也会对该 uid 的 `TimeLimitedFgsInfo` 执行 `reset()`。这解释了官方文档"以用户交互为起点启动同步服务"的源码依据。

## FGS 启动延迟与启动链路性能

### startForegroundService → startForeground 的 5 秒窗口

Android 8.0 引入的 `startForegroundService()` 要求应用在约 5 秒内调用 `startForeground()` 把通知挂出来。这个窗口由 `mServiceFGAnrTimer`（`ServiceAnrTimer` 类型）计时。超时后系统调用 `serviceForegroundCrash()`，向应用投递 `ForegroundServiceDidNotStartInTimeException`——这是 Crash 不是 ANR，不经过 `AnrHelper`，不产生 `/data/anr` trace 文件。[已验证: AOSP ActiveServices.java]

5 秒窗口内最常见的阻塞来源：

- 冷启动路径上的静态初始化（ContentProvider、`Application.onCreate`）过长
- `Service.onCreate()` 内做了同步 I/O
- Notification channel 未预先创建，`startForeground()` 内部抛异常

### Android 17 通知权限对 FGS 启动的影响

Android 13 引入的 `POST_NOTIFICATIONS` 运行时权限影响 FGS 通知显示。如果应用没有通知权限，`startForeground()` 仍然会成功（系统保证 FGS 生命周期不受通知权限影响），但通知不会展示给用户。Android 17 对此没有改变核心行为，但后台音频硬化引入了新的约束：后台音频场景下，FGS 不仅需要合法类型，还需要 WIU 能力。WIU 能力的判定涉及进程当前的前台状态和 FGS 启动入口——如果 FGS 是由后台触发器（如 `BOOT_COMPLETED`）拉起的，即使类型正确，WIU 能力也可能不满足。详见 25.17 节。[已验证: developer.android.com/about/versions/17/behavior-changes-17]

### 后台启动 FGS 的豁免路径

Android 12 起后台启动 FGS 受限，`ForegroundServiceStartNotAllowedException` 是 Binder 调用栈上同步抛回的 `RuntimeException`（非 `RemoteServiceException`），可以被调用方 `try-catch`。豁免路径包括：

- 高优先级 FCM 消息（但 FCM 被系统降级后仍会失败）
- 用户可见交互（Activity 前台、Notification action）
- `exact alarm` 触发
- `FgsTempAllowList` 临时豁免

豁免列表的具体条件随版本收紧。排查"为什么后台起不了 FGS"时，`dumpsys activity services <pkg>` 输出中的 `allow-start-foreground` 字段记录了系统判定结果。详见 5.8 节。[已验证: AOSP FgsTempAllowList.java]

## FGS 类型不匹配的系统惩罚链路

### SHORT_SERVICE：从 onTimeout 到 ANR 的完整路径

`shortService` 的超时惩罚分三步走 [已验证: AOSP ActiveServices.java, ServiceRecord.java]：

**第一步（~3 分钟）**：`AnrTimer` 触发 → `ActiveServices.onShortFgsTimeout()` → `ActivityThread.scheduleTimeoutService()` → 应用主线程 `H.handleMessage(SCHEDULE_TIMEOUT_SERVICE)` → `Service.onTimeout(startId, fgsType)`。应用应在回调内立即 `stopSelf(startId)`。

**第二步（procstate demote）**：进程被 `OomAdjuster` 降级为 cached app（`OOM_ADJ_REASON_SHORT_FGS_TIMEOUT`）。此时进程可被 LMK 杀掉或被 `CachedAppOptimizer` 冻结。

**第三步（ANR）**：若进程仍未退出，`mShortFGSAnrTimer` 在 `getAnrTime()` 触发 → `ActiveServices.onShortFgsAnr()` → `AMS.appNotResponding()` → `AnrHelper` 入队 → 标准 ANR dump 流程（`/data/anr/anr_*` 文件生成）。同时通过 `throwRemoteServiceException` 投递 `ForegroundServiceDidNotStopInTimeException` 到应用主线程。

堆栈特征始终经过 `ActivityThread$H.handleMessage`，看不到业务代码是哪一段阻塞了——这也是 `shortService` 超时问题在现场 debug 时定位困难的原因。必须结合 `dumpsys activity services` 的超时记录和 logcat 中 `ActivityManager` 的 `onShortFgsAnr` 日志反推。[已验证: developer.android.com/develop/background-work/services/fgs/troubleshooting]

### dataSync / mediaProcessing：Crash 而非 ANR

`dataSync` 和 `mediaProcessing` 的超时惩罚不经过 `AnrHelper`。超时后系统直接调用 `throwRemoteServiceException`，投递 `ForegroundServiceDidNotStopInTimeException` 到应用主线程。进程收到的是 Fatal Exception，不是 ANR——不产生 `/data/anr` trace 文件。 [已验证: AOSP ActiveServices.java]

两类惩罚的关键区别：

| 维度 | SHORT_SERVICE | dataSync / mediaProcessing |
|:---|:---|:---|
| 惩罚性质 | ANR + Exception | Exception only |
| ANR trace | 有（`/data/anr/`） | 无 |
| 投递路径 | `AnrHelper` + `throwRemoteServiceException` | 仅 `throwRemoteServiceException` |
| 对 App Standby Bucket 的影响 | procstate demote 后影响 bucket | 额度耗尽后直接失败 |

### startForeground 5 秒窗口超时

这条路径也不经过 ANR。`mServiceFGAnrTimer` 超时后调用 `serviceForegroundCrash()`，直接投递 `ForegroundServiceDidNotStartInTimeException`（也是 Crash）。堆栈同样经过 `ActivityThread` 的异常重建路径。[已验证: AOSP ActiveServices.java]

### 四类异常的辨析

| 异常 | 触发条件 | 同步/异步 | 可 catch | 有 ANR trace |
|:---|:---|:---|:---|:---|
| `ForegroundServiceStartNotAllowedException` | 后台启动 FGS 不满足豁免 / 类型校验失败 / 额度耗尽 | 同步（Binder 栈上） | 可以 | 无 |
| `ForegroundServiceDidNotStartInTimeException` | `startForegroundService()` 后 ~5 秒未调 `startForeground()` | 异步 | 不可以（Fatal） | 无 |
| `ForegroundServiceDidNotStopInTimeException`（SHORT_SERVICE） | `shortService` ~3 分钟未退出 | 异步 | 不可以（Fatal） | 有 |
| `ForegroundServiceDidNotStopInTimeException`（dataSync/mediaProcessing） | 24h 窗口内累计 ~6h 未退出 | 异步 | 不可以（Fatal） | 无 |

[已验证: AOSP ActiveServices.java, RemoteServiceException.java, developer.android.com/develop/background-work/services/fgs/troubleshooting]

## Data Sync 替代方案与 WorkManager 协调性能

Android 15 给 `dataSync` 加了 6 小时预算后，长时间下载/同步任务不再能无限制地依赖 FGS。迁移方向和 WorkManager 接入方案详见 25.13 节。这里只讲机制层面的性能边界。

### FGS + Job 并发的 quota 合流

Android 16 起，与 FGS 并发执行的 Job 受 App Standby Bucket 的 runtime quota 约束。即使 FGS 在 6 小时预算内，其内部跑的 `OneTimeWorkRequest` 仍可能因 bucket（例如 `RESTRICTED`）被挂起。外在表现是"FGS 存活但 Worker 不执行"。排查时用 `dumpsys jobscheduler <pkg>` 核对 effective quota 和 pending reason。[已验证: developer.android.com/about/versions/16/behavior-changes-all; 详见 5.10 节]

### 用户前台 reset 的架构意义

`TimeLimitedFgsInfo` 在 app 进入 `PROCESS_STATE_TOP` 时 `reset()`。这意味着以用户交互为起点的同步服务会获得完整的 6 小时额度。反过来，纯后台触发的同步任务（如定时 WorkManager 触发）额度可能已经被之前的后台同步消耗。这是"用户主动触发优于系统自动触发"的架构依据。[已验证: AOSP ServiceRecord.java TimeLimitedFgsInfo]

## Perfetto 观测与调试方法

### dumpsys activity services 输出解读

```bash
# 查看当前 FGS 状态、类型和超时记录
adb shell dumpsys activity services <package_name>
```

关键字段：
- `foregroundServiceType`：当前 FGS 类型
- `isForeground`：是否在前台服务状态
- `allow-start-foreground`：后台启动 FGS 的豁免判定结果和原因
- `short-fgs-info`：`shortService` 的计时起点和各阶段时间点

### FGS 启动延迟的 Perfetto 追踪

FGS 启动链路在 Perfetto 中的关键 slice：

1. `am_proc_start`：系统决定启动进程（冷启动场景）
2. `ActivityThread.handleBindApplication`：Application 初始化
3. `Service.onCreate`：Service 创建
4. `Service.onStartCommand`：接收启动命令
5. `Service.startForeground`：通知挂出、FGS 类型校验

从 `startForegroundService()` 到 `startForeground()` 超过 5 秒的案例，在 trace 上表现为 `Service.onStartCommand` 到 `Service.startForeground` 之间的 gap 过长。

### FGS 超时的系统日志关联

`shortService` 超时在 logcat 中的时序特征：

```
# onTimeout 回调
ActivityManager: Short FGS timeout for <component>

# procstate demote
ActivityManager: OOM_ADJ_REASON_SHORT_FGS_TIMEOUT

# ANR（若应用未退出）
ActivityManager: ANR in <package>, reason=A foreground service of type FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop within its timeout
```

`dataSync`/`mediaProcessing` 超时的日志特征不同——不会有 ANR 行，只有 `AndroidRuntime` 的 Fatal Exception 和堆栈。

### App Standby Bucket 对 FGS 行为的影响

```bash
# 查看当前 bucket
adb shell deviceidle whitelist +<package_name>  # 临时豁免
adb shell am get-standby-bucket <package_name>
```

`RESTRICTED` bucket 下，FGS 的 Job quota 受限更严重。Battery Historian 中可以查看 FGS 活跃时段与功耗的关联。Perfetto 的 `android.app_standby` counter track 显示 bucket 变化时点。

## 实战迁移建议与性能测试策略

### 类型迁移 checklist

| 旧做法 | Android 17 推荐方案 | 迁移要点 |
|:---|:---|:---|
| 无类型 FGS | 声明 `foregroundServiceType` + 对应权限 | 最低 targetSdk 34 |
| `dataSync` 长时间同步 | `WorkManager` foreground worker + `User Initiated Data Transfer` API | 控制单次时长在 6 小时内 |
| 后台静默下载 | `DownloadManager` 或 `WorkManager` + 进度持久化 | FGS 不再是绕过后台限制的通道 |
| 后台音乐播放 | `mediaPlayback` FGS + WIU 能力 | Android 17 后台音频硬化要求 |
| BLE 后台连接 | `connectedDevice` FGS | 无硬性时长上限 |

### 性能回归测试矩阵

FGS 相关的性能测试应覆盖：

1. **FGS 启动延迟**：`startForegroundService()` → `startForeground()` 间隔。冷启动和热启动分别测量。
2. **超时回调延迟**：`onTimeout()` 回调到达的抖动。Android 17 的 DeliQueue 改善了主线程消息分发延迟，`onTimeout` 回调的抖动应比 Android 16 小（从数百毫秒级缩小到数十毫秒级）。[待验证: 需实际 Android 17 设备 trace 对比]
3. **后台任务完成率**：各 bucket 下的 FGS + Job 组合完成率。`RESTRICTED` bucket 下需要单独测试。
4. **电池影响**：Battery Historian 中 FGS 活跃时段的功耗归因。
5. **兼容性**：Android 14-17 各版本的 FGS 行为差异。`onTimeout(int, int)` 双参数回调在 Android 14 不存在。

## Android 17 WIU 能力与后台执行边界 [自动发现]

Android 17 把 WIU（While-In-Use）能力引入 FGS 启动判定。WIU 能力不是一个新的 FGS 类型，而是对现有类型的附加约束：后台启动 FGS 时，系统不仅检查类型和权限，还检查这次启动是否具备"用户正在使用"的语义。

具体影响：

- 后台音频播放的 FGS 必须是非 `SHORT_SERVICE` 类型且具备 WIU 能力
- 同时持有 exact alarm 权限并使用 `USAGE_ALARM` 用途可以满足 WIU 要求
- 由 `BOOT_COMPLETED`、`MY_PACKAGE_REPLACED` 等系统广播触发的 FGS 可能不满足 WIU 要求，即使类型正确

这对音乐播放器和语音通话类 App 影响最大。适配方案详见 25.17 节。[已验证: developer.android.com/about/versions/17/behavior-changes-17]

## FGS 进程冻结与超时计时的交互 [自动发现]

`CachedAppOptimizer` 对 FGS 进程（procstate ≥ `PROCESS_STATE_FOREGROUND_SERVICE`）不冻结。但在 `shortService` 的 procstate demote 之后，进程可以被冻结。

`mShortFGSAnrTimer` 未设置 `freeze(true)` flag，所以即使进程被冻结，ANR 计时仍在继续。边界场景：

1. `shortService` 超时 → procstate demote → 进程被冻结
2. ANR 计时继续 → 解冻后 ANR 立即触发

在 dumpsys 中通过 `*freezer*` 日志核对冻结时间点，与 ANR 触发时间交叉对比。[已验证: AOSP ActiveServices.java, CachedAppOptimizer.java, AnrTimer.java]

## 扩展

### 🔸 Android 17 用户发起的 FGS 豁免机制

`FgsTempAllowList` 管理后台启动 FGS 的临时豁免。豁免窗口和条件随版本收紧，Android 17 未新增豁免入口，但对已有豁免路径的 WIU 能力判定更严格。源码路径：`frameworks/base/services/core/java/com/android/server/am/FgsTempAllowList.java`。[待验证: 需 android-17.0.0_r1 源码确认 FgsTempAllowList 变更]

### 🔸 System Exempt FGS 与系统应用性能特权

`systemExempted` 类型的 FGS 不受时间预算约束。这个类型保留给系统应用（`privileged` app），普通应用无法使用。对性能工程师的意义：在系统日志中看到 `systemExempted` 类型的 FGS 长时间运行时，这不是异常行为，是设计特权。[待验证: 具体准入条件需核对 ForegroundServiceTypePolicy.java]

### 🔸 FGS 与 JobScheduler 配额的交互预算模型

Android 16 起 FGS + Job 并发的 quota 合流机制，使得 FGS 不再是绕过 Job 配额的通道。交互模型：FGS 负责用户可见生命周期和通知提示，Job/WorkManager 负责任务调度和进度管理，两侧共享同一份任务状态。完整的 quota 模型和排障方法详见 5.10 节和 25.13 节。[已验证: developer.android.com/about/versions/16/behavior-changes-all]
