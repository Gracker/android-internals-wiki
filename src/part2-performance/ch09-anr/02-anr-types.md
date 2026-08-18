---
title: "ANR 类型与触发条件"
section: "9.2"
chapter: "9.2"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-17"
last_verified_against: "AOSP android-17.0.0_r1, Android Developers ANR diagnose / JobService / foreground service docs"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/libs/input/android/os/IInputConstants.aidl"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/AnrTypes.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentResolver.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentProviderClient.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/TimeoutRecord.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/timeout"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobService"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/troubleshooting"
  - type: blog
    path: "intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md"
tags: [anr, input-dispatching, broadcast, service, contentprovider, timeout]
related_chapters: ["9.1", "9.3", "9.4", "1.4", "1.5", "1.10"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: "2026-08-17T22:39:27+08:00"
last_idle_audit_run_id: "20260817-223927-idle-audit-b22f4aa7"
---
# 9.2 ANR 类型与触发条件

## 先认超时契约，再看线程栈

ANR 报告中的 `Reason` 描述系统正在等待哪一个完成信号。Input 等待应用确认输入事件已处理，Broadcast 等待 receiver 完成，execute-service 等待服务生命周期调用结束。不同类型可能留下相似的主线程栈，但计时起点、完成条件和责任进程并不相同。

拿到报告后可以依次回答三个问题：

1. 系统等待什么完成信号？
2. 计时从哪个动作开始，进程冷启动是否也占用这段时间？
3. 到期后，系统会调用 `appNotResponding()` 生成 ANR、直接移除进程，还是抛出远程服务异常？

这三个问题应在“主线程卡在哪里”之前回答。若类型判断错误，即使线程栈读对了，也可能把回调、进程启动或远端 Provider 的责任归到错误位置。

Android 17 的常用类型可以先按下表定位。表中数值是 AOSP 源码默认值；`Build.HW_TIMEOUT_MULTIPLIER`、DeviceConfig、广播 CPU 饥饿补偿和 OEM 配置都可能改变具体设备上的等待时长。

| 触发器 | Android 17 默认等待 | 系统等待的完成信号 | 常见 `Reason` 片段 |
|---|---:|---|---|
| Input connection | 5 秒 | 已分发事件得到完成确认 | `Input dispatching timed out`、`is not responding. Waited ... for ...` |
| No focused window | 5 秒 | 已聚焦应用出现可接收输入的窗口 | `does not have a focused window` |
| Broadcast | 10 秒或 60 秒；线程长期得不到 CPU 时，最多再延长一段同等时长 | `onReceive()` 返回，或 `PendingResult.finish()` | `Broadcast of Intent` |
| Execute service | 20 秒或 200 秒 | `onCreate()`、`onBind()`、`onStartCommand()` 等调度执行结束 | `executing service ... waited ...ms` |
| FGS 晋升 | 源码内部默认 30 秒，另有 10 秒 ANR 延迟；应用仍应遵循公开的数秒契约 | `startForegroundService()` 启动的服务调用 `startForeground()` | `did not then call Service.startForeground()` |
| `shortService` | 约 3 分钟，回调后源码默认再等 10 秒 | `onTimeout(int, int)` 后停止服务 | `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop` |
| Provider 远程调用 | 客户端配置 | 远程 Provider 调用返回 | `ContentProvider not responding` |
| `JobService` 回调 | 8 秒 | `onStartJob()` 或 `onStopJob()` 返回 | `No response to onStartJob` / `onStopJob` |

“Provider 在 10 秒内完成 publish”没有列成 Provider ANR，因为 Android 17 会把这类超时记为初始化失败并移除进程，不走 ANR 报告路径。后文会给出对应源码。

## Input ANR：输入连接和焦点窗口是两条路径

### 默认 5 秒从哪里来

`InputDispatcher` 位于 native inputflinger（原生输入系统服务）。事件写入应用的 InputChannel（输入通道）后，待确认的 `DispatchEntry` 会留在 connection 的 `waitQueue` 中。应用完成输入处理并通过 `InputEventReceiver.finishInputEvent()` 方向回执后，该条目才离开等待队列。普通 View 事件通常由主线程处理，因此主线程阻塞是常见根因；不过，检测器直接监控的是输入连接有没有按时确认事件。

下面的源码用于确认 Android 17 怎样从 5 秒基础值、硬件超时倍率和窗口级配置计算实际超时：

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
const std::chrono::duration DEFAULT_INPUT_DISPATCHING_TIMEOUT = std::chrono::milliseconds(
        android::os::IInputConstants::UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS *
        HwTimeoutMultiplier());

std::chrono::nanoseconds InputDispatcher::getDispatchingTimeoutLocked(
        const std::shared_ptr<Connection>& connection) {
    if (connection->isFocusMonitor) {
        return mMonitorDispatchingTimeout;
    }
    const sp<WindowInfoHandle> window = mWindowInfos.findWindowHandle(connection->getToken());
    if (window != nullptr) {
        return window->getDispatchingTimeout(DEFAULT_INPUT_DISPATCHING_TIMEOUT);
    }
    return DEFAULT_INPUT_DISPATCHING_TIMEOUT;
}
```

`IInputConstants.UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS` 为 5000。默认 5 秒适用于没有单独配置的窗口和 input monitor（输入监视连接）；窗口可以提供自己的 dispatching timeout，因此应以报告中的实际等待值为准，并结合目标设备与窗口状态解读。

### Connection ANR

`processAnrsLocked()` 从 `mAnrTracker` 取得已经到期的 connection。进入 `onAnrLocked(connection)` 后，源码选取 `waitQueue.front()`，也就是队首最早的待确认事件，作为诊断线索，并用 `now() - deliveryTime` 计算它已经等待多久。

源码注释还说明一个限制：oldest entry 最适合帮助排查，却不一定是触发计时器到期的那一个事件。若窗口超时配置在等待期间发生变化，较新的事件反而可能更早达到自己的期限。因此，报告中的事件描述是重要线索，但不能单独作为因果结论。

Android 17 生成的 native reason 形如：

`<input-channel> is not responding. Waited <N>ms for <event-description>`

随后，`processConnectionUnresponsiveLocked()` 将事件、持续时间和 connection token（输入连接标识）交给 policy 层，WMS/AMS 再构造 ANR 记录。`cancelEventsForAnrLocked()` 会取消该 connection 上的后续事件，避免继续向已判定无响应的连接投递输入。

排查 connection ANR 时要覆盖这些可能性：

- 主线程执行长任务、锁等待、Binder 同步调用或文件 I/O；
- 主线程消息队列积压，输入消息迟迟得不到处理；
- native input receiver 或自建 InputChannel 没有按协议完成事件；
- 线程长时间处于 Runnable（可运行但等待 CPU）状态；
- 系统端或跨进程依赖拖住主线程，触发点仍落在应用的输入窗口。

### No focused window ANR

InputDispatcher 已知 focused application（当前应获得焦点的应用），却找不到 focused window（实际接收输入的焦点窗口）时，会启动另一只计时器。到期 reason 是：

`<application> does not have a focused window`

这条记录指向窗口建立或焦点交接。常见检查项包括 Activity 启动是否卡在 `bindApplication` / `Application.onCreate()`、首个窗口是否迟迟没有加入 WMS、窗口切换期间 token 是否对应错误，以及显示切换或多窗口状态是否异常。no-focused-window 表示系统还没有合适窗口接收输入，若直接按“点击事件处理超过 5 秒”分析，通常会漏掉启动链问题。

## Broadcast ANR：判断依据是广播标志和完成回执

### 10/60 秒与 10–20/60–120 秒

Android 17 的基础常量仍是：

- 带 `Intent.FLAG_RECEIVER_FOREGROUND` 的广播使用 10 秒软超时；
- 其余受跟踪广播使用 60 秒软超时。

这里的“前台广播”指 Intent 带有前台接收标志，不代表接收进程当时位于前台。Android 14 起，若进程在软超时窗口内长时间处于 Runnable 却得不到 CPU，系统会补偿相应等待时间，补偿上限等于原软超时。因此，官方诊断范围写作 10–20 秒和 60–120 秒。

以下 Android 17 源码片段展示哪些广播会启动计时器，以及确认超时后怎样进入 ANR：

```java
// frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java
final boolean assumeDelivered = r.isAssumedDelivered(index);
if (mService.mProcessesReady && !r.timeoutExempt && !assumeDelivered) {
    queue.setTimeoutScheduled(true);
    final int softTimeoutMillis = (int) (r.isForeground() ? mFgConstants.TIMEOUT
            : mBgConstants.TIMEOUT);
    startDeliveryTimeoutLocked(queue, softTimeoutMillis);
}

// deliveryState == BroadcastRecord.DELIVERY_TIMEOUT
TimeoutRecord tr = TimeoutRecord.forBroadcastReceiver(
        r.intent, packageName, className);
mAnrTimer.accept(queue, tr);
mService.appNotResponding(queue.app, tr);
```

系统尚未完成启动时，以及广播标记为 `timeoutExempt`（豁免超时）或 `assumeDelivered`（系统无需等待明确回执）时，不会启动这只计时器。动态注册的无序 receiver 可能走 assumed-delivered 路径，因此并非每个 BroadcastReceiver 都有 10/60 秒 ANR 计时器。

### `goAsync()` 不会增加一段预算

同步 receiver 以 `onReceive()` 返回作为完成信号。调用 `goAsync()` 后，完成信号改为 `PendingResult.finish()`，原有广播 deadline（截止时间）仍然继续计时。后台线程池拥塞、网络等待、锁竞争或漏调 `finish()`，都可能让同一个 deadline 到期。

进程冷启动也要计入分析。广播需要拉起进程时，创建进程、执行 `bindApplication`、`Application` 和静态 Provider 初始化，都会先消耗广播交付时间。ANR 栈只记录超时附近的瞬间，启动早期已经结束的慢步骤可能不再出现在栈顶。

常见 `Reason` 以 `Broadcast of Intent` 开头，并携带 action、component 或 receiver 包名。诊断时同时记录：

- 是否设置 `FLAG_RECEIVER_FOREGROUND`；
- receiver 是在 manifest 中声明还是运行时注册，广播是否为 ordered（有序广播）；
- 是否调用 `goAsync()`，每条分支是否都能执行 `finish()`；
- 进程在接收前是否已经存在，CPU starvation（线程长期得不到 CPU）是否明显；
- `onReceive()` 之前是否经历长时间应用初始化。

## Execute-service ANR：20/200 秒取决于执行优先级

### “前台 20 秒”不等于“前台服务 20 秒”

AMS 向进程调度 service lifecycle transaction（服务生命周期事务）后，会把该服务加入 executing set（正在执行的服务集合）。`ActiveServices.scheduleServiceTimeoutLocked()` 根据 `ProcessServiceRecord.isExecServicesFg()` 选择 20 秒或 200 秒。这里的“前台”表示这次服务执行采用较高优先级，并不等同于服务已经成为 Foreground Service，也不能从 FGS 类型直接推导。

下面的常量给出 Android 17 的默认执行时限及两者的 10 倍关系：

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
private static final long DEFAULT_SERVICE_TIMEOUT =
        20 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long DEFAULT_SERVICE_BACKGROUND_TIMEOUT =
        DEFAULT_SERVICE_TIMEOUT * 10;

long SERVICE_TIMEOUT = DEFAULT_SERVICE_TIMEOUT;
long SERVICE_BACKGROUND_TIMEOUT = DEFAULT_SERVICE_BACKGROUND_TIMEOUT;
```

源码会把默认值写入运行时字段，设备配置和硬件倍率仍可能改变实际数值。因此，报告中的 `waited ...ms` 比记忆中的固定秒数更可靠。

计时覆盖 `onCreate()`、`onBind()`、`onStartCommand()` 等执行阶段，也可能包含服务进程冷启动消耗的时间。`TimeoutRecord.forServiceExec()` 生成的 reason 形如：

`executing service <short-instance-name>, waited <N>ms`

同一进程可以同时执行多个 Service。计时器将责任归到进程，因此要结合 executing service 列表、transaction 记录、业务日志和 trace 中的主线程栈，确认究竟是哪次生命周期调用没有完成。

## 前台服务附近有三种不同的超时结果

前台服务相关报错经常被统称为“FGS ANR”，但不同路径有不同的计时起点和最终结果。Android 17 至少要区分以下三种情况。

### `startForegroundService()` 后没有及时晋升

调用 `startForegroundService()` 后，系统会为该服务设置 `fgRequired`，要求它尽快调用 `startForeground()` 并发布合规通知。官方 ANR 概览给出的应用侧时限是 5 秒，FGS 排障页表述为“几秒内”；AOSP Android 17 的内部实现默认使用以下两个值：

- `DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS = 30 * 1000`；
- `DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS = 10 * 1000`。

这两个内部值可以由 DeviceConfig 改写，因此不应写进应用业务计时逻辑，也不能用 30 秒替代公开的数秒契约。`serviceForegroundTimeout()` 生成：

`Context.startForegroundService() did not then call Service.startForeground(): <ServiceRecord>`

该方法会先停止服务，并在源码默认 10 秒后投递 `SERVICE_FOREGROUND_TIMEOUT_ANR_MSG`。另一条服务拆除路径会投递 `SERVICE_FOREGROUND_CRASH_MSG`，再由 `serviceForegroundCrash()` 创建 `ForegroundServiceDidNotStartInTimeException`。设备日志可能呈现 ANR，也可能呈现这项远程服务异常，但两者都应回到 `startForeground()` 晋升契约排查。

应用应在 `onCreate()` 或 `onStartCommand()` 的早期准备最小可用通知并调用 `startForeground()`。数据库迁移、网络请求、账号刷新和大文件扫描应放到晋升之后；若等异步结果返回后才晋升，服务更容易超过期限。

### `shortService` 超时后未停止：ANR

Android 14 引入 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE`，用于约三分钟内能够结束的短任务。Android 17 默认时限为 3 分钟。到期后，系统调用 `Service.onTimeout(int startId, int fgsType)`；同时为兼容 API 34 保留单参数 `onTimeout(int startId)` 语义，面向 Android 15+ 的实现只需覆盖双参数回调。系统还会启动 short-FGS ANR timer，源码默认再等待 10 秒。若服务仍未停止，`onShortFgsAnrTimeout()` 会构造以下 reason 并调用 `appNotResponding()`：

`A foreground service of FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop within a timeout: <component>`

`onTimeout(int, int)` 应只执行能够在明确时间内完成的清理，并尽快调用 `stopSelf()` 或 `stopService()`。若在回调中继续等待原任务完成，额外的清理窗口也会被耗尽。

### `dataSync` / `mediaProcessing` 超时后未停止：崩溃

对 targetSdk 35+，Android 15 开始限制这两类前台服务在应用处于后台时的累计运行时间。Android 17 的默认值各为 6 小时，统计按 UID 和 FGS 类型分别维护；两个类型各有自己的 `TimeLimitedFgsInfo`，不会共享同一份 6 小时额度。24 小时统计窗口到期会重置用量，用户把应用带到前台也会刷新可用时间的计算起点。

额度耗尽时，系统调用 `Service.onTimeout(int startId, int fgsType)`。源码默认再给 10 秒清理时间；若服务仍未停止，`onFgsCrashTimeout()` 会通过 `ForegroundServiceDidNotStopInTimeException` 使进程崩溃。这条路径不调用 `appNotResponding()`，因此不能计入 ANR 类型统计。

| FGS 场景 | 到期回调 | 未在宽限期内处理的 Android 17 结果 |
|---|---|---|
| 未完成 `startForeground()` 晋升 | 无 `Service.onTimeout()` | ANR 延迟路径或 `ForegroundServiceDidNotStartInTimeException` |
| `shortService` 约 3 分钟 | `Service.onTimeout(int, int)` | ANR |
| `dataSync` 累计 6 小时 | `Service.onTimeout(int, int)` | `ForegroundServiceDidNotStopInTimeException` 崩溃 |
| `mediaProcessing` 累计 6 小时 | `Service.onTimeout(int, int)` | `ForegroundServiceDidNotStopInTimeException` 崩溃 |

## ContentProvider：发布保护与调用 ANR 要分开

### 10 秒 publish timeout 属于初始化失败保护

进程启动时，AMS 会等待应用发布清单中声明的 Provider。`ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` 在 Android 17 默认为 10 秒再乘硬件超时倍率。Provider 的 `onCreate()`、`Application.onCreate()` 或更早的进程初始化只要拖住发布，都会占用这段时间。

下面两段源码分别给出默认超时值，以及超时后以初始化失败原因移除进程的动作：

```java
// frameworks/base/core/java/android/content/ContentResolver.java
public static final int CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS =
        10 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;

// frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java
void processContentProviderPublishTimedOutLocked(ProcessRecord app) {
    cleanupAppInLaunchingProvidersLocked(app, true);
    mService.mProcessList.removeProcessLocked(app, false, true,
            ApplicationExitInfo.REASON_INITIALIZATION_FAILURE,
            ApplicationExitInfo.SUBREASON_UNKNOWN,
            "timeout publishing content providers");
}
```

处理函数没有创建 `TimeoutRecord`，也没有调用 `AnrHelper.appNotResponding()`。它会清理 launching provider（仍在等待发布的 Provider），并以 `REASON_INITIALIZATION_FAILURE` 移除进程。因此，Provider 在 10 秒内没有 publish 属于初始化失败，不属于 ContentProvider ANR。

这类问题仍可能阻塞调用方或启动流程。排查时可以搜索 `timeout publishing content providers`，再检查 `Application`、Provider `onCreate()`、自动初始化 SDK 和类加载开销；ANR 报表通常不会将其归入 Provider ANR。

### Provider 调用 ANR 需要显式探测

Android 17 的 Provider ANR 入口来自 `ContentProviderClient.setDetectNotResponding(timeoutMillis)`。这个接口属于 `@SystemApi`，并要求 `REMOVE_TASKS` 权限，普通第三方应用无法为任意 `ContentResolver.query()` 配置系统级 Provider ANR 探测。

配置探测后，`ContentProviderClient.beforeRemote()` 会在远程调用前安排定时任务。若调用到期仍未返回，客户端会经 `ContentResolver.appNotRespondingViaProvider()` 通知 AMS。随后，`ContentProviderHelper.appNotRespondingViaProvider()` 创建：

`TimeoutRecord.forContentProvider("ContentProvider not responding")`

随后，目标 Provider 进程进入 `AnrHelper`。这条路径的超时值来自客户端配置，不存在适用于所有 Provider 调用的固定 10 秒 ANR 阈值。

普通应用在主线程执行很慢的 `query()` 仍可能触发 ANR，但类型通常由外层契约决定。例如，主线程等待 Provider 超过输入期限时，报告会归为 Input ANR。Provider 端 Binder 线程池耗尽也可能拖慢多个调用方；这是导致其他 ANR 的因果链，不能据此把所有慢 Provider 调用都标成 Provider ANR。

Provider 的四条超时路径和案例分析见 [9.8 ContentProvider 超时与 ANR 四路径](08-contentprovider-timeout-anr.md)。

## JobService：8 秒回调限制与 job 运行时限分开计算

`JobService.onStartJob()` 和 `onStopJob()` 都在应用主线程执行。Android 17 的 `JobServiceContext` 位于 JobScheduler APEX（可独立更新的系统模块）：

`frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`

以下源码片段给出回调、服务绑定和通知三种不同的等待值：

```java
private static final long OP_BIND_TIMEOUT_MILLIS =
        18 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long OP_TIMEOUT_MILLIS =
        8 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long NOTIFICATION_TIMEOUT_MILLIS =
        10_000L * Build.HW_TIMEOUT_MULTIPLIER;

@ChangeId
@EnabledAfter(targetSdkVersion = Build.VERSION_CODES.TIRAMISU)
static final long ANR_PRE_UDC_APIS_ON_SLOW_RESPONSES = 258236856L;
```

`@EnabledAfter(TIRAMISU)` 表示这项兼容性变更对 targetSdk 34+ 的应用启用，慢 `onStartJob()` / `onStopJob()` 会进入显式 ANR。`handleOpTimeoutLocked()` 生成 `No response to onStartJob` 或 `No response to onStopJob`，再通过 `ActivityManagerInternal.appNotResponding()` 上报。18 秒 bind timeout 走服务绑定失败和重新调度处理，不能当作 JobService ANR 阈值。

三条时间线应分别阅读：

- **回调 ANR**：`onStartJob()` 或 `onStopJob()` 超过默认 8 秒仍未返回；
- **job 运行超时**：`onStartJob()` 已返回 `true`，JobScheduler 之后因配额或执行时限停止 job 并调用 `onStopJob()`；停止 job 本身不构成 ANR，但 `onStopJob()` 仍要在回调期限内返回；
- **通知超时**：公开 API 要求 `JobParameters.isUserInitiatedJob()` 为 `true` 且继续运行的 job 在 10 秒内调用 `setNotification()`；Android 17 内部以 `JobStatus.isUserVisibleJob()` 设置 `mAwaitingNotification`。超时 reason 为 `required notification not provided`，并触发 ANR。

耗时工作应在 `onStartJob()` 中迅速交给有并发上限的执行器，并返回 `true`。任务完成时调用 `jobFinished()`；收到 `onStopJob()` 后，应快速取消或标记后台工作，再返回是否需要重新调度。若在回调中等待 Future、执行线程 `join` 或同步 Binder，就会直接消耗 8 秒窗口。

## Android 17 的 `AnrTypes`

Android 17 在 `frameworks/base/core/java/android/app/AnrTypes.java` 中给出公开分类常量。这项能力受 feature flag（功能开关）控制，OEM 也可能保留额外的私有 detector（检测器）。`AnrTypes` 适合统一平台分类，但信息比原始 `Reason` 和 `TimeoutRecord` 更粗，不能替代两者。

| 值 | 常量 | 含义 |
|---:|---|---|
| 0 | `ANR_TYPE_OTHER` | 其他或无法归类 |
| 1 | `ANR_TYPE_INPUT_DISPATCH_NO_FOCUSED_WINDOW` | 输入期间没有焦点窗口 |
| 2 | `ANR_TYPE_INPUT_DISPATCH` | 输入连接无响应 |
| 3 | `ANR_TYPE_BROADCAST_OF_INTENT` | 广播处理超时 |
| 4 | `ANR_TYPE_START_FOREGROUND_SERVICE` | 前台服务晋升超时 |
| 5 | `ANR_TYPE_EXECUTE_SERVICE` | Service 执行超时 |
| 6 | `ANR_TYPE_CONTENT_PROVIDER_NOT_RESPONDING` | Provider 远程调用无响应 |
| 7 | `ANR_TYPE_APP_TRIGGERED` | 应用主动触发 |
| 8 | `ANR_TYPE_FOREGROUND_SHORT_SERVICE_TIMEOUT` | `shortService` 超时 |
| 9 | `ANR_TYPE_JOB_SERVICE_START` | JobService 启动回调超时 |
| 10 | `ANR_TYPE_APPLICATION_START` | 应用启动超时 |

枚举名中的 `JOB_SERVICE_START` 比底层 reason 更粗。Android 17 的 `TimeoutRecord.forJobService()` 也可以承载 `onStopJob` 或通知超时 reason，因此分析工具要保留原始 reason；若只保存一个整数枚举，后续就无法区分这些情况。

## 如何从设备证据识别类型

### Logcat 和 bugreport

`ActivityManager` 文本日志可能经过裁剪，events buffer 中的 `am_anr` 和 bugreport 更适合作为取证入口。下面的命令先收集普通设备可获得的日志与 bugreport，再列出仅调试构建可直接读取的 `/data/anr` 路径：

```bash
# 普通 user、userdebug、eng 构建均可尝试
adb shell logcat -b events -d -v threadtime | grep am_anr
adb bugreport bugreport.zip

# 仅 userdebug / eng 且 adbd 允许 root 时读取原始 /data/anr
adb root
adb shell ls -lt /data/anr
adb pull /data/anr ./anr-traces
```

普通量产 user 构建通常不允许 `adb root`，也不能直接读取 `/data/anr`。此时应使用 bugreport、Play Console、OEM 平台或 `ApplicationExitInfo` 提供的退出记录。收集后先保存发生时间、进程、`Reason`、目标 component（组件）和等待时长，再分析线程栈。

### `Reason` 到检查方向

| `Reason` 线索 | 优先检查 |
|---|---|
| `Input dispatching timed out` | main Looper、输入 connection、焦点窗口、CPU 调度 |
| `does not have a focused window` | Activity 启动、首窗添加、焦点 token、显示切换 |
| `Broadcast of Intent` | action、广播 flags、进程冷启动、`goAsync()` 与 `finish()` |
| `executing service` | executing service 列表、生命周期方法、冷启动 |
| `did not then call Service.startForeground()` | 晋升调用位置、通知构建、启动链阻塞 |
| `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop` | `onTimeout()`、停止调用、清理耗时 |
| `ContentProvider not responding` | detector 配置、authority（Provider 标识）、Provider 进程 Binder 和主线程 |
| `No response to onStartJob/onStopJob` | JobService 主线程回调 |
| `required notification not provided` | user-initiated job 的公开通知契约、内部 user-visible 状态 |

Logcat 文案可能被 AMS 再次包装，因此不能要求整行文字与表格逐字相同。联合使用 `TimeoutRecord` kind、`ApplicationExitInfo` 子原因和原始 reason，分类会更可靠。

## Perfetto 中能确认什么

Perfetto 用来回答“超时窗口内线程和 CPU 在做什么”，单靠一张 trace 无法自动确定 ANR 类型。类型仍由系统 detector 和 `Reason` 决定。

对 Input ANR，要检查主线程从事件 delivery（投递）到 timeout 之间处于 Running、Runnable、Sleeping，还是 Binder 等待，再关联 input、sched、binder 和 frame timeline。主线程长时间 Runnable 表示有工作可运行却得不到 CPU；长时间 Sleeping 则要继续检查 futex（用户空间锁的内核等待点）、Binder 或 I/O 的唤醒来源。

对 Broadcast、Service 和 JobService，要围绕系统调度 transaction 与应用回调开始点对齐时间。冷启动样本应把 process start、`bindApplication`、Provider 初始化和回调执行放在同一条时间线上。若只看 ANR 时刻的栈，容易漏掉此前已经结束的启动耗时。

对 Provider 远程调用，要关联 caller（调用方）的 Binder transaction、Provider 进程的 binder thread 和主线程。caller 等待时，Provider 可能正在主线程工作、Binder 线程池排队、等待锁，或发起下游 Binder 调用；单一线程状态无法代替完整调用链。

## 版本演进：只保留会影响判断的变化

- **Android 8.0 / API 26**：引入 `startForegroundService()` 与及时调用 `startForeground()` 的契约。
- **Android 12 / API 31**：后台启动前台服务受到更严格限制，晋升超时的 `ForegroundServiceDidNotStartInTimeException` 成为常见诊断信号。
- **Android 14 / API 34**：广播诊断文档加入 CPU starvation 补偿窗口；引入 `shortService` 及其超时回调；targetSdk 34+ 的慢 `JobService` 回调进入显式 ANR。
- **Android 15 / API 35**：targetSdk 35+ 的 `dataSync`、`mediaProcessing` 采用后台累计 6 小时限制，并通过 `Service.onTimeout(int, int)` 给出停止机会；未停止的结果是远程服务异常崩溃。
- **Android 17 / API 37**：源码基线为 `android-17.0.0_r1`。Broadcast 使用 `BroadcastQueueImpl`、`BroadcastAnrTimer` 和通用 `AnrTimer`；平台给出 `AnrTypes` 分类，并可为部分 ANR timer 接入预警回调。各 detector 的完成信号仍需逐类判断。

版本号只说明平台能力。DeviceConfig、compat change（兼容性变更开关）、targetSdk、广播 flags 和厂商修改都会影响具体设备行为，因此分析报告还要记录 build fingerprint（系统构建指纹）、API level、targetSdk 和原始超时值。

## 排查清单

- 从 `Reason` 确定 detector，并保留完整原文。
- 记录计时开始点、到期点和系统等待的完成信号。
- 查明冷启动是否占用了 Broadcast、Service 或 Provider 的等待时间。
- Broadcast 记录 `FLAG_RECEIVER_FOREGROUND`、注册方式、ordered 状态和 `goAsync()` 完成路径。
- Service 区分 execute-service、FGS 晋升、`shortService` 和限时 FGS。
- Provider 区分 publish 初始化失败、显式 Provider detector 和调用方派生的 Input ANR。
- JobService 区分 8 秒回调、job 运行时限、18 秒 bind timeout 和通知要求。
- 线程栈解释采样时刻，Perfetto 补充一段时间范围；还要用日志、调度事件和 Binder 链补齐时间线。
- 报告阈值时写明“源码默认值”或“设备观测值”，不要把可配置常量当成 SDK 保证。

## 源码与官方资料

源码锚点均为 AOSP `android-17.0.0_r1`：

- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
- `frameworks/native/libs/input/android/os/IInputConstants.aidl`
- `frameworks/base/core/java/android/app/AnrTypes.java`
- `frameworks/base/core/java/android/content/ContentResolver.java`
- `frameworks/base/core/java/android/content/ContentProviderClient.java`
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java`
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java`
- `frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`
- `frameworks/base/core/java/com/android/internal/os/TimeoutRecord.java`

官方资料：

- [Keep your app responsive：ANR 类型与基础诊断](https://developer.android.com/topic/performance/vitals/anr)
- [Diagnose and fix ANRs：广播、输入、execute-service 与 Provider 诊断](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Foreground service timeout behavior](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Troubleshoot foreground services](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [`JobService` API reference](https://developer.android.com/reference/android/app/job/JobService)
