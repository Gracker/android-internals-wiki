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
Android 14 以后，前台服务（Foreground Service，FGS）的约束不再只有“展示通知”。系统还要判断服务类型、类型权限、运行时前置条件、后台启动资格和时长额度。任何一项不满足，都可能让服务无法晋升、被限时结束，或使进程进入 ANR / Crash 路径。

本节以 Android 17 / API 37 / `android-17.0.0_r1` 为基线，说明这些检查在 `system_server` 中怎样衔接，以及它们对启动延迟、后台任务和功耗意味着什么。FGS 的选择原则见 5.8，JobScheduler / WorkManager 配额见 5.10，面向业务的迁移方案见 25.13。

## 先区分 FGS 的五道门

调用 `startForegroundService()` 只完成了服务启动请求。一次合法的 FGS 还要依次通过以下条件：

1. 当前状态允许启动 FGS，或命中后台启动豁免；
2. manifest 声明了服务类型；
3. manifest 声明了基础权限和对应的类型权限；
4. 调用时满足该类型的运行时前置条件；
5. 服务及时调用 `startForeground()`，并且没有耗尽该类型的时长额度。

这五道门对应不同异常和处理位置。排障时先判断失败发生在“请求启动”“晋升 FGS”还是“运行超时”，比从一长串 `RemoteServiceException` 文本猜原因更有效。

### Android 14：类型和权限进入强校验

对于 targetSdk 34 及以上的应用，Android 14 要求每个 FGS 在 manifest 中声明用途类型，并声明相应的 FGS 类型权限。例如，一个数据同步服务的最小声明如下：

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />

<application>
    <service
        android:name=".SyncService"
        android:exported="false"
        android:foregroundServiceType="dataSync" />
</application>
```

这段声明只让服务具备申请该类型的静态资格。应用仍要在允许的时机启动服务，并在服务中调用 `ServiceCompat.startForeground()`。涉及 camera、microphone、location 等类型时，还必须在调用时满足相应的运行时权限和 while-in-use 条件。

`ActiveServices.validateForegroundServiceType()` 通过 `ForegroundServiceTypePolicy` 执行类型检查。Android 17 源码中的失败类型需要分别理解：

- manifest 没有类型：`MissingForegroundServiceTypeException`；
- 类型被策略禁止：`InvalidForegroundServiceTypeException`；
- 缺少类型权限或运行时前置条件：`SecurityException`；
- 把 manifest 未声明的类型传给 `startForeground()`：公开 API 文档规定为 `IllegalArgumentException`；
- 后台启动资格不足：`ForegroundServiceStartNotAllowedException`。

类型或权限错误不能统一归为 `ForegroundServiceStartNotAllowedException`。它们的修复位置不同：有的要改 manifest，有的要改运行时权限流程，有的要把启动动作移到用户可见状态。

### Android 15：两种长时类型开始共享额度

targetSdk 35 及以上时，`dataSync` 与 `mediaProcessing` 在应用处于后台期间受到时长限制。`mediaProcessing` 类型也是 Android 15 新增的。默认规则是：

- 每个类型在 24 小时窗口内共有 6 小时；
- `dataSync` 与 `mediaProcessing` 分开计量；
- 同一 UID 下多个同类型服务共享额度；
- 应用进入 TOP 状态后，用户交互会让该类型重新获得可用时间；
- 额度耗尽后再次启动同类型服务会抛 `ForegroundServiceStartNotAllowedException`。

Android 15 还增加了 `Service.onTimeout(int startId, int fgsType)`，用于通知 `dataSync` / `mediaProcessing` 停止。收到回调后应立即保存可恢复状态并停止服务。

### Android 16：FGS 不再替 Job 规避 quota

Android 16 起，与 FGS 并发执行的普通 Job 和 expedited Job 仍受 JobScheduler runtime quota 约束。这个变化同时影响 JobScheduler、WorkManager 和 DownloadManager。

因此，“FGS 活着”不能推出 Worker 正在执行。遇到 FGS 通知仍在、后台任务却没有进度时，应读取 `WorkInfo.getStopReason()` 或 `JobParameters.getStopReason()`，并用 `JobScheduler.getPendingJobReasonsHistory()` 和 `dumpsys jobscheduler` 核对原因。

用户发起的数据传输应评估 User-Initiated Data Transfer Job。它与普通 Job 的适用条件和配额不同，不能只把原有 Worker 套进 FGS 来获得长期运行时间。

### Android 17：后台音频增加生命周期条件

Android 17 的后台音频加固适用于音频播放、audio focus 请求和音量修改：

- 对所有运行在 Android 17 上的应用，后台音频交互要求有可见 Activity，或运行一个类型不为 `shortService` 的 FGS；
- targetSdk 37 的应用若在后台，还要求该 FGS 具备 while-in-use（WIU）能力；
- 从可见界面或明确的用户动作启动的 FGS 通常具备 WIU 能力；
- exact alarm 权限与 `USAGE_ALARM` 音频用途同时成立时，WIU 要求可豁免。

这项变化约束音频 API 的使用条件，没有把 WIU 变成新的 FGS 类型，也没有要求所有 FGS 都额外声明“WIU 权限”。不满足条件时，播放与音量 API 可能静默失败，audio focus 请求返回 `AUDIOFOCUS_REQUEST_FAILED`。排查时查看 `dumpsys audio` 和带有 `AudioHardening` 前缀的 logcat；只盯着 FGS 启动日志会漏掉失败点。

对播放器，推荐由用户操作启动 `mediaPlayback` FGS，并让 Media3 `MediaSessionService` 管理播放生命周期。由 `BOOT_COMPLETED` 拉起一个 FGS 后直接播放音频，不具备同样的用户意图条件。

## FGS 类型决定用途，不承诺算力

进入 FGS 状态会提高进程在内存回收与后台执行模型中的重要性，并向用户展示持续工作的状态。它不会为业务线程保留 CPU 核心、固定频率或网络带宽，也不会取消 Thermal、Job quota、Doze 和厂商功耗策略。

对性能工程而言，FGS 有三层影响：

| 层级 | 系统提供什么 | 系统没有承诺什么 |
|---|---|---|
| 生命周期 | 在合法用途下允许用户可感知的持续任务 | 任意后台任务都可长期运行 |
| 进程优先级 | FGS 进程通常获得较高的进程重要性 | 不会永不被杀，也不等于实时调度 |
| 用户可见性 | 通知或任务管理界面暴露持续工作 | 通知权限不能替代 FGS 类型与权限 |

`POST_NOTIFICATIONS` 被拒绝时，应用仍可启动合法 FGS。通知不会按常规方式出现在通知抽屉中，但系统仍会在 Task Manager 等系统界面提供可见性。不要把通知运行时权限当作 `startForeground()` 的开关。

## `shortService` 的三段式超时

`shortService` 用于很快完成且不能推迟的关键工作，默认时限约 3 分钟。它不要求类型专用权限，但仍要求基础 `FOREGROUND_SERVICE` 权限。

Android 17 的 `ServiceRecord.ShortFgsInfo` 记录以下时间：

```text
timeout = shortFgsStartUptime + short_fgs_timeout_duration
demote  = timeout + short_fgs_proc_state_extra_wait_duration
ANR     = shortFgsStartUptime + short_fgs_timeout_duration
          + short_fgs_anr_extra_wait_duration
```

`ActivityManagerConstants` 在 `android-17.0.0_r1` 中的默认值分别为 3 分钟、额外 5 秒降级进程状态、额外 10 秒触发 ANR。这些是 AOSP 默认实现，可由 `DeviceConfig` 调整，应用不能把额外宽限期当作可用执行预算。

### 到期后的系统路径

超时后的步骤如下：

1. `ActiveServices.onShortFgsTimeout()` 调用应用侧的 `Service.onTimeout(int startId)`；
2. 系统安排进程状态降级；
3. 系统启动 `mShortFGSAnrTimer`；
4. 服务仍未停止时，`onShortFgsAnrTimeout()` 通过 `appNotResponding()` 进入标准 ANR 流程。

应用应覆盖单参数回调，并根据对应的 `startId` 停止服务：

```kotlin
override fun onTimeout(startId: Int) {
    persistCheckpoint()
    stopSelfResult(startId)
}
```

这里的 checkpoint 只能做轻量、可预测的收尾。若保存动作本身可能阻塞，应在正常执行过程中持续写入可恢复状态，不能等到回调才开始一轮大 I/O。

### 再次调用不一定续时

官方规则要求应用当前可见，或满足后台启动 FGS 的某项豁免，才能再次以 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` 调用 `startForeground()` 并获得新的约 3 分钟。

源码中的 `maybeUpdateShortFgsTrackingLocked()` 只有在 `extendTimeout` 为真或首次进入 short-service 状态时才重建计时。若后台启动资格不成立，再次调用可以更新通知或 start count，但旧计时继续运行。单独再次调用 `startService()` / `startForegroundService()` 也不会延长 short-service 时限。

把 `shortService` 与其他 FGS type 同时传入时，系统忽略 `shortService` bit，服务按其他类型处理。这个组合不能用来取得短服务的额外时间。

## `dataSync` 与 `mediaProcessing` 的共享时长

这两种类型使用 `ActiveServices.mTimeLimitedFgsInfo`，按 UID 和类型保存 `TimeLimitedFgsInfo`。数据结构包含：

- 第一次启动的 uptime 与 elapsed realtime；
- 最近一次启动的 uptime；
- 累计运行时长；
- 同类型并发服务数；
- 最近一次额度耗尽时间。

运行时长使用 `uptimeMillis` 累积，24 小时窗口判断使用 `elapsedRealtime`。这样可以把“CPU 可执行时间的累计”和“经过一个自然时间窗口”分开。

### 并发不会得到多份额度

同一应用同时运行两个 `dataSync` 服务，不会得到 12 小时。它们共享同一类型额度。源码用 `mNumParallelServices` 记录并发实例，但总预算仍属于 UID + type。

如果一个服务同时声明多个受限类型，`getTimeLimitedFgsType()` 会选择当前配置下时限更宽松的类型进行跟踪。由于 Android 17 默认的两类时限同为 6 小时，业务代码仍应让 type 精确匹配用途，不能依赖内部选择顺序延长执行。

### 用户进入前台怎样影响额度

官方行为可概括为：用户把应用带到前台后，该类型重新获得完整的 6 小时。

源码实现比一句“进入 TOP 就调用 `reset()`”更细：

- 超时消息触发时，`onFgsTimeout()` 检查进程的当前 TOP 状态和 `lastTopTime`；
- 若 FGS 启动后发生过有效的 TOP 交互，系统按该时间重新安排超时；
- 后续调用 `startForeground()` 时，若当前是 TOP、24 小时窗口已过，或额度耗尽后出现过 TOP，`TimeLimitedFgsInfo.reset()` 才会清空累计数据。

所以不能把进程状态采样中的一次短暂 TOP 直接解释为“后台已有对象当场清零”。对应用而言，可靠做法仍是从明确的用户操作发起长任务，并自行维护剩余工作和恢复点。

### 超时回调与 Crash

额度到期后，`ActiveServices.onFgsTimeout()` 调用应用的双参数回调：

```kotlin
override fun onTimeout(startId: Int, foregroundServiceType: Int) {
    persistCheckpoint()
    stopSelfResult(startId)
}
```

系统随后安排一小段清理宽限期。如果服务仍保留受限 FGS 类型，`onFgsCrashTimeout()` 通过 `ForegroundServiceDidNotStopInTimeException` 让应用进程崩溃。该路径与 short-service ANR 不同，通常不会生成 `/data/anr/` 报告。

## 从启动请求到 `startForeground()` 的窗口

`Context.startForegroundService()` 会先创建或启动普通 Service，并把 `ServiceRecord.fgRequired` 设为真。服务必须尽快调用 `startForeground()` 完成晋升。

开发文档把这个要求表述为“几秒内”。Android 工程中常说的“5 秒规则”不能继续当作 Android 17 的固定常量：`android-17.0.0_r1` 的 `ActivityManagerConstants.DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS` 为 30 秒，另有默认 10 秒的 ANR 延迟；`mServiceFGAnrTimer` 还允许在系统重载时扩展。这些值属于内部实现，也可受设备配置影响。

工程代码仍应在 `onCreate()` 或 `onStartCommand()` 开头完成通知构建和 `startForeground()`，不要主动消耗内部宽限时间。宽限期增长的目的不是允许更多初始化工作。

### 常见启动阻塞

- `Application.onCreate()` 或 ContentProvider 做同步 I/O；
- Service 主线程等待数据库迁移、网络或 Binder；
- 首次创建 NotificationChannel 时发生额外工作；
- 通知对象无效、channel 不存在或权限前置条件失败；
- 业务先初始化 SDK，最后才调用 `startForeground()`。

更稳的顺序是：预先创建稳定的通知渠道；Service 启动后立即发布最小可用通知；随后把业务工作交给有明确取消和恢复语义的执行单元。通知内容可在获得进度后更新。

### Android 17 源码中的两条失败分支

`ActiveServices.serviceForegroundTimeout()` 在转前台计时到期后停止服务，并安排后续 ANR 检查。服务在仍处于 `fgRequired` 状态时被销毁，`bringDownService` 分支还会安排 `ForegroundServiceDidNotStartInTimeException`。因此，不能把所有版本、所有竞态下的结果简化成“只 Crash”或“只 ANR”。

面向应用的稳定结论是：

- `startForegroundService()` 后必须马上晋升；
- `ForegroundServiceDidNotStartInTimeException` 属于系统向进程投递的内部致命异常，不能依靠普通业务 `try/catch` 恢复；
- 日志中出现 `Context.startForegroundService() did not then call Service.startForeground()` 时，应回查冷启动和 Service 主线程；
- 不要把它和调用点同步抛出的后台启动异常混为一类。

## 后台启动资格与 WIU 权限要分开

targetSdk 31 及以上的应用通常不能从后台启动 FGS，除非命中官方豁免。常见豁免包括用户可见状态刚结束、通知或 widget 交互、高优先级 FCM、用户请求的 exact alarm、特定系统角色和 Companion Device Manager。

豁免只解决“能否从后台发起 FGS”。涉及 camera、microphone、location 或部分 health 能力时，还要通过 while-in-use 权限检查。Android 14 及以上会在创建相应 FGS 时检查当前可用权限；即使静态 `checkSelfPermission()` 返回 `PERMISSION_GRANTED`，后台状态也可能没有当下的 while-in-use 能力，并抛出 `SecurityException`。

因此，下面两句话含义不同：

- 应用命中后台 FGS 启动豁免；
- 这个 FGS 具备访问 while-in-use 资源的能力。

Android 17 的后台音频规则又复用了 WIU 能力作为音频交互门槛。排查时要同时记录 FGS 启动原因、服务类型、`allow-start-foreground` 判定和音频侧 `AudioHardening` 结果。

### 高优先级 FCM 与 exact alarm 的边界

高优先级 FCM 可能被服务端或系统降级。尝试启动 FGS 前应检查收到消息的实际优先级；降级后继续启动会得到 `ForegroundServiceStartNotAllowedException`。

exact alarm 豁免要求闹钟对应用户请求的操作。它既不是通用后台执行许可，也不会自动提供 camera / microphone 等 WIU 权限。Android 17 后台音频中的 exact-alarm 例外还要求音频用途为 `USAGE_ALARM`。

## 异常表：先看触发阶段

| 现象或异常 | 触发阶段 | 处理性质 | 首要修复方向 |
|---|---|---|---|
| `ForegroundServiceStartNotAllowedException` | 启动或晋升 | 调用点异常 | 检查后台资格、豁免、类型额度 |
| `MissingForegroundServiceTypeException` | `startForeground()` 类型检查 | 调用点异常 | 补 manifest type |
| `InvalidForegroundServiceTypeException` | `startForeground()` 类型策略 | 调用点异常 | 使用受支持且已声明的类型 |
| `IllegalArgumentException` | 传入 manifest 未声明的 type | 调用点异常 | 对齐动态 type 与 manifest |
| `SecurityException` | 类型权限 / 运行时前置条件 | 调用点异常 | 补权限并调整启动时机 |
| `ForegroundServiceDidNotStartInTimeException` | 未及时晋升 | 系统投递的致命异常 | 缩短冷启动和主线程路径 |
| short-service ANR | 约 3 分钟后仍未停止 | ANR | 正常路径提前结束，回调立即收尾 |
| `ForegroundServiceDidNotStopInTimeException` | `dataSync` / `mediaProcessing` 到期后仍未停 | 进程 Crash | 实现双参数回调和可恢复任务 |

“可在调用点捕获”也不等于应该把异常当作控制流长期依赖。应用应在调用前判断状态，捕获用于处理状态变化造成的竞态。

## 调试与观测

### 先收集系统状态

以下命令用于读取服务、进程和 Job 状态：

```bash
adb shell dumpsys activity services <package>
adb shell dumpsys activity processes <package>
adb shell dumpsys jobscheduler <package>
adb shell am get-standby-bucket <package>
adb shell dumpsys audio
```

`dumpsys activity services` 的具体字段会随版本变化。常见线索包括当前 FGS type、`isForeground`、`allow-start-foreground`、`fgRequired` 和 short-FGS 计时信息。不要让自动化脚本只依赖一段未经版本校验的文本字段。

### 再把应用阶段放进 Perfetto

应用至少为这些位置加 trace slice：

- 发起 `startForegroundService()`；
- `Application.onCreate()`；
- `Service.onCreate()`；
- `Service.onStartCommand()`；
- 调用 `startForeground()` 前后；
- 业务工作启动、checkpoint 和停止；
- `onTimeout()` 进入与返回。

同时采集 `am`、Binder、sched、CPU frequency 和进程线程轨道。这样可以区分：

- 进程尚未创建；
- 主线程被初始化占用；
- `startForeground()` 调用被 Binder 或通知处理阻塞；
- 服务已晋升，后续 Worker 又被 quota 停止；
- 超时回调已投递，但主线程迟迟无法处理。

Perfetto 中不保证出现名为 `Service.startForeground` 的平台 slice。依赖应用自定义标记和系统事件的时间关联会更稳。

### 使用测试开关时保存并恢复原值

官方提供 compat change 和 `DeviceConfig` 入口来缩短 `dataSync` / `mediaProcessing` 测试周期，例如：

```bash
adb shell am compat enable FGS_INTRODUCE_TIME_LIMITS <package>
adb shell device_config put activity_manager \
    data_sync_fgs_timeout_duration <milliseconds>
adb shell device_config put activity_manager \
    media_processing_fgs_timeout_duration <milliseconds>
```

这些命令改变测试设备行为。运行前先读取原值，测试后恢复；测试报告也要标记覆盖值。模拟结果只能证明应用的停止路径可工作，不能替代真实长时功耗和热稳定性测试。

Android 17 后台音频可用 `adb shell cmd audio set-enable-hardening` 测试。`throw` 模式会把部分静默失败改为响亮失败，便于定位，但它不代表默认用户设备的错误呈现方式。

## 架构与性能建议

### 把 FGS 当作用户可感知生命周期

选择 FGS 的首要问题是：用户是否明确知道任务正在持续运行，并需要随时停止或查看进度。若任务可以延迟、合并、重试，JobScheduler / WorkManager 往往更符合系统调度模型。若任务是用户刚刚发起的大文件传输，评估 User-Initiated Data Transfer Job。

FGS 类型要匹配用途。`specialUse` 需要声明具体 subtype，并接受应用商店审核；`systemExempted` 也不是普通系统应用的通用特权。Android 官方列出的资格包括设备所有者、特定系统角色、VPN、exact alarm 等受控场景。Android 17 的 `SystemExemptedFgsTypePermission` 会核对权限和系统豁免原因，不满足条件时按类型权限校验失败处理。

### 所有长任务都要可恢复

进程重要性提高仍不能保证任务完成。可靠任务至少需要：

- 幂等的工作单元；
- 持久化 checkpoint；
- 明确的取消信号；
- 进程重建后的恢复策略；
- type timeout 和 Job stop reason 的统一记录；
- 用户主动结束时清理通知、session 和临时文件。

收到 timeout 后才持久化全部状态，风险较高。按工作单元持续写 checkpoint，回调只负责关闭入口和提交最后一个已完成位置。

### 测试范围要覆盖启动、额度和用户状态

FGS 回归测试至少包含：

| 维度 | 必测场景 |
|---|---|
| 启动状态 | 前台、刚离开前台、后台无豁免、通知 / widget 交互 |
| 进程状态 | 热进程、冷启动、低内存重建 |
| 类型 | 单一类型、动态增加 type、short-service 转换 |
| 权限 | 已授予、拒绝、while-in-use 在后台失效 |
| 时长 | 正常完成、收到 timeout 后停止、故意不停止 |
| Job | FGS 与 Worker 并发、不同 standby bucket、quota 停止 |
| Android 17 音频 | 可见 Activity、具备 WIU 的 FGS、后台无 WIU、alarm 例外 |

除了成功率，还要记录 FGS 晋升延迟、主线程阻塞、任务吞吐、能量、温度、停止响应时间和用户可见错误。FGS 让任务可见，并没有让功耗变得合理。

## 源码核对索引

本节的 Android 17 判断对应以下源码位置：

- `services/core/java/com/android/server/am/ActiveServices.java`
  - `setServiceForegroundInnerLocked()`；
  - `validateForegroundServiceType()`；
  - `maybeUpdateShortFgsTrackingLocked()`；
  - `onShortFgsTimeout()` / `onShortFgsAnrTimeout()`；
  - `onFgsTimeout()` / `onFgsCrashTimeout()`；
  - `serviceForegroundTimeout()`。
- `services/core/java/com/android/server/am/ServiceRecord.java`
  - `ShortFgsInfo` 与 `TimeLimitedFgsInfo`。
- `services/core/java/com/android/server/am/ActivityManagerConstants.java`
  - short-service、time-limited FGS 与晋升超时默认值。
- `core/java/android/app/ForegroundServiceTypePolicy.java`
  - 各 FGS type 的权限策略。
- `core/java/android/app/Service.java`
  - 两个 `onTimeout()` 回调的契约。
- `core/java/android/app/RemoteServiceException.java`
  - FGS 未及时启动和未及时停止的内部异常。

## References

- [Android FGS changes by version](https://developer.android.com/develop/background-work/services/fgs/changes)
- [Declare foreground services and permissions](https://developer.android.com/develop/background-work/services/fgs/declare)
- [Launch a foreground service](https://developer.android.com/develop/background-work/services/fgs/launch)
- [Foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Background FGS start restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Troubleshoot foreground services](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [Android 17 background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Android 16 JobScheduler quota changes](https://developer.android.com/about/versions/16/behavior-changes-all)
- [AOSP Android 17 `ActiveServices`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)
- [AOSP Android 17 `ServiceRecord`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ServiceRecord.java)
- [AOSP Android 17 `ForegroundServiceTypePolicy`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ForegroundServiceTypePolicy.java)
- [AOSP Android 17 `Service`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/Service.java)
