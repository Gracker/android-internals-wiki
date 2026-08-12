---
title: "ANR 类型与触发条件"
section: "9.2"
chapter: "9.2"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-09"
last_verified_against: "AOSP android-17.0.0_r1, Android Developers ANR vitals / JobService / foreground service docs"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
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
---
# 9.2 ANR 类型与触发条件

## 先认超时契约，再看线程栈

ANR 报告中的 `Reason` 描述了系统等待哪一个完成信号。Input 等输入连接确认，Broadcast 等 receiver 完成，execute-service 等服务生命周期调用结束。它们可能留下相似的主线程栈，触发它们的计时器和责任边界却不同。

拿到报告后可以依次回答三个问题：

1. 系统等待什么完成信号？
2. 计时从哪个动作开始，冷启动是否占用同一段预算？
3. 到期后走 `appNotResponding()`、移除进程，还是抛出远程服务异常？

这三个问题比“主线程卡在哪里”更早。类型判错后，即使栈读对了，也可能把结果回调、进程启动或远端 Provider 的责任归到错误位置。

Android 17 的常用类型可以先按下表定位。表中的数值是 AOSP 默认值；`Build.HW_TIMEOUT_MULTIPLIER`、DeviceConfig、广播 CPU 饥饿补偿和 OEM 配置都可能改变设备上的等待时长。

| 触发器 | Android 17 默认等待 | 系统等待的完成信号 | 常见 `Reason` 片段 |
|---|---:|---|---|
| Input connection | 5 秒 | 已分发事件得到完成确认 | `Input dispatching timed out`、`is not responding. Waited ... for ...` |
| No focused window | 5 秒 | 已聚焦应用出现可接收输入的窗口 | `does not have a focused window` |
| Broadcast | 10 秒或 60 秒；CPU 饥饿时最多再延长一段同等时长 | `onReceive()` 返回，或 `PendingResult.finish()` | `Broadcast of Intent` |
| Execute service | 20 秒或 200 秒 | `onCreate()`、`onBind()`、`onStartCommand()` 等调度执行结束 | `executing service ... waited ...ms` |
| FGS 晋升 | 源码默认 30 秒，另有 10 秒 ANR 延迟 | `startForegroundService()` 启动的服务调用 `startForeground()` | `did not then call Service.startForeground()` |
| `shortService` | 约 3 分钟，回调后源码默认再等 10 秒 | `onTimeout(int, int)` 后停止服务 | `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop` |
| Provider 远程调用 | 客户端配置 | 远程 Provider 调用返回 | `ContentProvider not responding` |
| `JobService` 回调 | 8 秒 | `onStartJob()` 或 `onStopJob()` 返回 | `No response to onStartJob` / `onStopJob` |

`10 秒 Provider publish timeout` 没有列成 Provider ANR，因为 Android 17 对该超时的处理是以初始化失败原因移除进程。后文会给出对应源码。

## Input ANR：输入连接和焦点窗口是两条路径

### 默认 5 秒从哪里来

`InputDispatcher` 位于 native inputflinger。事件写入应用的 InputChannel 后，待确认的 `DispatchEntry` 留在 connection 的 `waitQueue` 中。应用完成输入处理时，`InputEventReceiver.finishInputEvent()` 方向的确认使条目离开等待队列。普通 View 层事件通常由主线程处理，所以主线程阻塞是高频根因；检测对象仍是输入连接的响应状态。

下面的源码用于确认 Android 17 的默认值、硬件超时倍率和窗口级覆盖能力：

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

`IInputConstants.UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS` 为 5000。默认 5 秒适用于没有其他设置的窗口和 input monitor；窗口可以提供自己的 dispatching timeout，因此报告中的等待值应结合目标设备和窗口状态解读。

### Connection ANR

`processAnrsLocked()` 从 `mAnrTracker` 取得到期 connection。进入 `onAnrLocked(connection)` 后，源码选取 `waitQueue.front()` 作为诊断用的 oldest entry，并用 `now() - deliveryTime` 生成等待时长。

源码注释补充了一个限制：oldest entry 最适合帮助排查，却未必是造成计时器到期的那一个事件。窗口超时在事件等待期间发生变化时，较新的事件可能更早达到自己的期限。报告里的事件描述要当作高价值线索，不能当作唯一因果证据。

Android 17 生成的 native reason 形如：

`<input-channel> is not responding. Waited <N>ms for <event-description>`

随后 `processConnectionUnresponsiveLocked()` 将事件、持续时间和 connection token 交给 policy 层，WMS/AMS 再构造 ANR 记录。`cancelEventsForAnrLocked()` 会取消该 connection 上的后续事件，避免继续向已判定无响应的连接送入工作。

排查 connection ANR 时要覆盖这些可能性：

- 主线程执行长任务、锁等待、Binder 同步调用或文件 I/O；
- 主线程 Runnable 排队过深，输入消息迟迟得不到调度；
- native input receiver 或自建 InputChannel 没有按协议完成事件；
- 进程长时间处于 Runnable，但缺少 CPU 时间；
- 系统端或跨进程依赖拖住主线程，触发点仍落在应用的输入窗口。

### No focused window ANR

InputDispatcher 已知 focused application、却找不到 focused window 时，会启动另一只计时器。到期 reason 是：

`<application> does not have a focused window`

这条记录指向窗口建立或焦点交接。常见检查项包括 Activity 启动是否卡在 `bindApplication` / `Application.onCreate()`、首个窗口是否迟迟没有加入 WMS、窗口切换期间 token 是否失配，以及显示切换或多窗口状态是否异常。看到 no-focused-window 后直接按“点击事件处理超过 5 秒”分析，通常会错过启动链。

## Broadcast ANR：判断依据是广播标志和完成回执

### 10/60 秒与 10–20/60–120 秒

Android 17 的基础常量仍是：

- 带 `Intent.FLAG_RECEIVER_FOREGROUND` 的广播使用 10 秒软超时；
- 其余受跟踪广播使用 60 秒软超时。

这里的“前台广播”描述广播标志，不等同于接收进程当时位于前台。Android 14 起，系统会按进程在软超时窗口内 Runnable 却拿不到 CPU 的时间延长等待，延长量限制在原软超时以内。因此官方诊断范围写作 10–20 秒和 60–120 秒。

以下 Android 17 片段用于展示何时启动计时器，以及超时时如何进入 ANR：

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

系统尚未完成启动、`timeoutExempt` 广播和 `assumeDelivered` 的交付不会启动这只计时器。动态注册的无序 receiver 可能走 assumed-delivered 路径，所以“每个 BroadcastReceiver 都有 10/60 秒 ANR 计时器”不成立。

### `goAsync()` 没有增加一段预算

同步 receiver 的结束信号是 `onReceive()` 返回。调用 `goAsync()` 后，结束信号改为 `PendingResult.finish()`，原广播 deadline 仍在运行。后台线程池拥塞、网络等待、锁竞争或漏调 `finish()` 都可能让 deadline 到期。

冷启动也要计入分析。广播需要拉起进程时，进程创建、`bindApplication`、`Application` 和静态 Provider 初始化会先占用交付时间。ANR 栈只记录超时附近的瞬间，启动早期已完成的慢步骤可能不再出现在栈顶。

常见 `Reason` 以 `Broadcast of Intent` 开头，并携带 action、component 或 receiver 包名。诊断时同时记录：

- 是否设置 `FLAG_RECEIVER_FOREGROUND`；
- receiver 是 manifest 注册还是运行时注册，是否为 ordered；
- 是否调用 `goAsync()`，每条分支是否都能执行 `finish()`；
- 进程在接收前是否存在，CPU starvation 是否明显；
- `onReceive()` 之前是否经历长时间应用初始化。

## Execute-service ANR：20/200 秒描述执行优先级

### “前台 20 秒”不等于“前台服务 20 秒”

AMS 为进程调度 service lifecycle transaction 后，会把该服务加入 executing set。`ActiveServices.scheduleServiceTimeoutLocked()` 根据 `ProcessServiceRecord.isExecServicesFg()` 选择 20 秒或 200 秒。这是 execute-service 的调度优先级，不能用前台服务类型直接替换。

下面的常量用于确认 Android 17 的默认执行时限：

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
private static final long DEFAULT_SERVICE_TIMEOUT =
        20 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long DEFAULT_SERVICE_BACKGROUND_TIMEOUT =
        DEFAULT_SERVICE_TIMEOUT * 10;

long SERVICE_TIMEOUT = DEFAULT_SERVICE_TIMEOUT;
long SERVICE_BACKGROUND_TIMEOUT = DEFAULT_SERVICE_BACKGROUND_TIMEOUT;
```

源码把默认值放入运行时字段；设备配置和硬件倍率可能改变数值。报告中的 `waited ...ms` 比记忆中的固定秒数更可靠。

计时覆盖 `onCreate()`、`onBind()`、`onStartCommand()` 等执行阶段，也可能包含服务进程冷启动所消耗的时间。`TimeoutRecord.forServiceExec()` 生成的 reason 形如：

`executing service <short-instance-name>, waited <N>ms`

同一进程可以同时执行多个 Service。计时器归责到进程，trace 中的主线程栈需要结合 executing service 列表、transaction 记录和业务日志，定位究竟是哪次生命周期调用未完成。

## 前台服务附近有三种不同的超时结果

前台服务相关报错经常被统称为“FGS ANR”，这样会把修复点混在一起。Android 17 至少要分开以下三条路径。

### `startForegroundService()` 后没有及时晋升

`startForegroundService()` 建立 `fgRequired` 约束，服务需要尽早调用 `startForeground()` 并发布合规通知。官方 ANR 概览给出的应用侧时限是 5 秒，FGS 排障页表述为“几秒内”；AOSP Android 17 的内部实现默认使用：

- `DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS = 30 * 1000`；
- `DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS = 10 * 1000`。

这两个值可由 DeviceConfig 改写，不应写进应用业务计时逻辑，也不能拿 30 秒替代公开契约。`serviceForegroundTimeout()` 生成：

`Context.startForegroundService() did not then call Service.startForeground(): <ServiceRecord>`

该方法会停止服务，并在源码默认 10 秒后投递 `SERVICE_FOREGROUND_TIMEOUT_ANR_MSG`。另一条服务拆除路径会投递 `SERVICE_FOREGROUND_CRASH_MSG`，由 `serviceForegroundCrash()` 创建 `ForegroundServiceDidNotStartInTimeException`。设备日志可能呈现 ANR 或该远程服务异常，排查入口都是 `startForeground()` 晋升契约。

应用侧应在 `onCreate()` 或 `onStartCommand()` 的早段准备最小可用通知并调用 `startForeground()`。数据库迁移、网络请求、账号刷新和大文件扫描应放到晋升之后；把晋升放进异步结果回调会增加超时概率。

### `shortService` 超时后未停止：ANR

Android 14 引入 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE`。Android 17 默认时限为 3 分钟。到期后系统调用 `Service.onTimeout(int startId, int fgsType)`，同时为兼容 API 34 保留单参数 `onTimeout(int startId)` 语义；面向 Android 15+ 的实现只需覆盖双参数回调。系统还会启动 short-FGS ANR timer，源码默认再等待 10 秒。服务仍未停止时，`onShortFgsAnrTimeout()` 构造以下 reason 并调用 `appNotResponding()`：

`A foreground service of FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop within a timeout: <component>`

`onTimeout(int, int)` 应只做有界清理并尽快调用 `stopSelf()` 或 `stopService()`。在回调中继续等待原任务完成，会把清理窗口也耗尽。

### `dataSync` / `mediaProcessing` 超时后未停止：崩溃

对 targetSdk 35+，Android 15 开始限制这两类前台服务在应用处于后台时的累计运行时间。Android 17 的默认值分别为 6 小时，统计按 UID 和 FGS 类型维护；两个类型各有自己的 `TimeLimitedFgsInfo`，没有共享一份 6 小时额度。24 小时窗口到期会重置统计，用户把应用带到前台也会刷新可用时间的计算起点。

额度耗尽时，系统调用 `Service.onTimeout(int startId, int fgsType)`。源码默认给予 10 秒清理时间；服务没有停止时，`onFgsCrashTimeout()` 通过 `ForegroundServiceDidNotStopInTimeException` 使进程崩溃。这条路径不调用 `appNotResponding()`，因此不要把它计入 ANR 类型统计。

| FGS 场景 | 到期回调 | 未在宽限期内处理的 Android 17 结果 |
|---|---|---|
| 未完成 `startForeground()` 晋升 | 无 `Service.onTimeout()` | ANR 延迟路径或 `ForegroundServiceDidNotStartInTimeException` |
| `shortService` 约 3 分钟 | `Service.onTimeout(int, int)` | ANR |
| `dataSync` 累计 6 小时 | `Service.onTimeout(int, int)` | `ForegroundServiceDidNotStopInTimeException` 崩溃 |
| `mediaProcessing` 累计 6 小时 | `Service.onTimeout(int, int)` | `ForegroundServiceDidNotStopInTimeException` 崩溃 |

## ContentProvider：发布保护与调用 ANR 要分开

### 10 秒 publish timeout 是初始化失败保护

进程启动时，AMS 等待它发布清单中声明的 Provider。`ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` 在 Android 17 默认为 10 秒乘硬件倍率。Provider 的 `onCreate()`、`Application.onCreate()` 或更早的进程初始化拖住发布，都会耗掉这段时间。

下面两段源码用于核对超时值和超时后的系统动作：

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

处理函数没有创建 `TimeoutRecord`，也没有调用 `AnrHelper.appNotResponding()`。它清理 launching provider，并以 `REASON_INITIALIZATION_FAILURE` 移除进程。因此“Provider 10 秒未 publish 会触发 ContentProvider ANR”是错误映射。

这类问题仍会阻塞调用方或启动流程。排查时搜索 `timeout publishing content providers`，再检查 `Application`、Provider `onCreate()`、自动初始化 SDK 和类加载开销；ANR 报表未必会把它归入 Provider ANR。

### Provider 调用 ANR 需要显式探测

Android 17 的 Provider ANR 入口来自 `ContentProviderClient.setDetectNotResponding(timeoutMillis)`。该接口属于 `@SystemApi`，需要 `REMOVE_TASKS` 权限，普通三方应用不能把任意 `ContentResolver.query()` 配置成系统级 Provider ANR。

配置探测后，`ContentProviderClient.beforeRemote()` 会在调用前安排定时任务。远程调用到期未返回时，客户端经 `ContentResolver.appNotRespondingViaProvider()` 通知 AMS。`ContentProviderHelper.appNotRespondingViaProvider()` 创建：

`TimeoutRecord.forContentProvider("ContentProvider not responding")`

随后目标 Provider 进程进入 `AnrHelper`。超时值来自客户端配置，所以不存在适用于所有 Provider 调用的固定 10 秒 ANR 阈值。

普通应用在主线程执行慢 `query()` 仍可能触发 ANR，只是类型通常由外层契约决定。例如主线程等待 Provider 超过输入期限，报告会归为 Input ANR。Provider 端耗尽 Binder 线程也可能拖慢多个调用方；这是一种因果链，不能据此把所有慢 Provider 调用标成 Provider ANR。

Provider 的四条超时路径和案例分析见 [9.8 ContentProvider 超时与 ANR 四路径](08-contentprovider-timeout-anr.md)。

## JobService：8 秒回调限制和 job 运行时限无关

`JobService.onStartJob()` 与 `onStopJob()` 都在应用主线程执行。Android 17 的 `JobServiceContext` 位于 JobScheduler APEX：

`frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`

以下片段用于确认回调、绑定和通知三种等待值：

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

`@EnabledAfter(TIRAMISU)` 使 targetSdk 34+ 的应用在慢 `onStartJob()` / `onStopJob()` 上进入显式 ANR。`handleOpTimeoutLocked()` 对应生成 `No response to onStartJob` 或 `No response to onStopJob`，再通过 `ActivityManagerInternal.appNotResponding()` 上报。18 秒 bind timeout 走绑定失败和重调度处理，不能写成 JobService ANR 阈值。

三条时间线应分别阅读：

- **回调 ANR**：`onStartJob()` 或 `onStopJob()` 超过默认 8 秒没有返回；
- **job 运行超时**：`onStartJob()` 已返回 `true`，JobScheduler 之后因配额或执行时限停止 job 并调用 `onStopJob()`；停止动作本身不构成 ANR；
- **通知超时**：公开 API 要求 `JobParameters.isUserInitiatedJob()` 为 `true` 且继续运行的 job 在 10 秒内调用 `setNotification()`；Android 17 内部以 `JobStatus.isUserVisibleJob()` 设置 `mAwaitingNotification`。超时 reason 为 `required notification not provided`，并触发 ANR。

耗时工作应在 `onStartJob()` 中快速交给受控执行器并返回 `true`。任务完成时调用 `jobFinished()`；收到 `onStopJob()` 后快速取消或标记工作并返回重调度决策。回调里等待 Future、线程 join 或同步 Binder，会直接占用 8 秒窗口。

## Android 17 的 `AnrTypes`

Android 17 在 `frameworks/base/core/java/android/app/AnrTypes.java` 中给出公开分类常量。这个类型受 feature flag 约束，OEM 也可能保留额外的私有 detector；它适合统一平台分类，不能替代 `Reason` 和 `TimeoutRecord`。

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

枚举名里的 `JOB_SERVICE_START` 比底层 reason 粗。Android 17 的 `TimeoutRecord.forJobService()` 也可承载 `onStopJob` 或通知超时 reason，所以分析工具应保留原始 reason，避免只存一个整数后丢失细节。

## 如何从设备证据识别类型

### Logcat 和 bugreport

`ActivityManager` 文本日志可能经过裁剪，events buffer 的 `am_anr` 和 bugreport 更适合作为取证入口。下面的命令用于收集两类设备证据：

```bash
# 普通 user、userdebug、eng 构建均可尝试
adb shell logcat -b events -d -v threadtime | grep am_anr
adb bugreport bugreport.zip

# 仅 userdebug / eng 且 adbd 允许 root 时读取原始 /data/anr
adb root
adb shell ls -lt /data/anr
adb pull /data/anr ./anr-traces
```

普通量产 user 构建通常不能 `adb root`，也不能直接读取 `/data/anr`。此时使用 bugreport、Play Console、OEM 平台或 `ApplicationExitInfo` 提供的退出记录。收集后先保存发生时间、进程、`Reason`、目标 component 和等待时长，再进入线程栈。

### `Reason` 到检查方向

| `Reason` 线索 | 优先检查 |
|---|---|
| `Input dispatching timed out` | main Looper、输入 connection、焦点窗口、CPU 调度 |
| `does not have a focused window` | Activity 启动、首窗添加、焦点 token、显示切换 |
| `Broadcast of Intent` | action、广播 flags、冷启动、`goAsync()` 与 `finish()` |
| `executing service` | executing service 列表、生命周期方法、冷启动 |
| `did not then call Service.startForeground()` | 晋升调用位置、通知构建、启动链阻塞 |
| `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE did not stop` | `onTimeout()`、停止调用、清理耗时 |
| `ContentProvider not responding` | detector 配置、authority、Provider 进程 Binder 和主线程 |
| `No response to onStartJob/onStopJob` | JobService 主线程回调 |
| `required notification not provided` | user-initiated job 的公开通知契约、内部 user-visible 状态 |

Logcat 文案可能被 AMS 再包装，不要要求整行和表格逐字相同。`TimeoutRecord` kind、`ApplicationExitInfo` 子原因和原始 reason 的组合更稳妥。

## Perfetto 中能确认什么

Perfetto 用来回答“超时窗口内线程和 CPU 在做什么”，不能单靠一张 trace 自动确定 ANR 类型。类型仍由系统 detector 和 `Reason` 决定。

对 Input ANR，检查主线程从事件 delivery 到 timeout 之间是 Running、Runnable、Sleeping，还是 Binder 等待；再关联 input、sched、binder 和 frame timeline。主线程长时间 Runnable 表示有工作可运行却缺少 CPU，长时间 Sleeping 要继续看 futex、Binder 或 I/O 唤醒来源。

对 Broadcast、Service 和 JobService，围绕系统调度 transaction 与应用回调开始点对齐时间。冷启动样本要把 process start、bindApplication、Provider 初始化和回调执行放在一条时间线上。只看 ANR 时刻的栈，容易漏掉已经结束的启动耗时。

对 Provider 远程调用，关联 caller 的 Binder transaction、provider 进程 binder thread 和 provider 主线程。caller 等待时 provider 可能在主线程工作、binder pool 排队、锁等待或下游 Binder 调用，不能用单一线程状态替代完整调用链。

## 版本演进：保留变化，结论落到 Android 17

- **Android 8.0 / API 26**：引入 `startForegroundService()` 与及时调用 `startForeground()` 的契约。
- **Android 12 / API 31**：后台启动前台服务受到更严格限制，晋升超时的 `ForegroundServiceDidNotStartInTimeException` 成为常见诊断信号。
- **Android 14 / API 34**：广播诊断文档加入 CPU starvation 延长窗口；引入 `shortService` 及其超时回调；targetSdk 34+ 的慢 `JobService` 回调进入显式 ANR。
- **Android 15 / API 35**：targetSdk 35+ 的 `dataSync`、`mediaProcessing` 采用后台累计 6 小时限制，并通过 `Service.onTimeout(int, int)` 给出停止机会；未停止的结果是远程服务异常崩溃。
- **Android 17 / API 37**：源码基线为 `android-17.0.0_r1`。Broadcast 使用 `BroadcastQueueImpl`、`BroadcastAnrTimer` 和通用 `AnrTimer`；平台给出 `AnrTypes` 分类，并可为部分 ANR timer 接入预警回调。各 detector 的完成信号仍需逐类判断。

版本号只说明平台能力。DeviceConfig、compat change、targetSdk、广播 flags 和厂商修改都会影响某台设备的行为，分析报告应同时记录 build fingerprint、API level、targetSdk 和原始超时值。

## 排查清单

- 从 `Reason` 确定 detector，保留完整原文。
- 记录计时开始点、到期点和系统等待的完成信号。
- 查明冷启动是否占用了 Broadcast、Service 或 Provider 的等待时间。
- Broadcast 记录 `FLAG_RECEIVER_FOREGROUND`、注册方式、ordered 状态和 `goAsync()` 完成路径。
- Service 区分 execute-service、FGS 晋升、`shortService` 和限时 FGS。
- Provider 区分 publish 初始化失败、显式 Provider detector 和调用方派生的 Input ANR。
- JobService 区分 8 秒回调、job 运行时限、18 秒 bind timeout 和通知要求。
- 线程栈与 Perfetto 只解释采样时刻；用日志、调度事件和 Binder 链补齐时间线。
- 报告阈值时写明“源码默认值”或“设备观测值”，不要把可配置常量当成 SDK 保证。

## 源码与官方资料

源码锚点均为 AOSP `android-17.0.0_r1`：

- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
- `frameworks/base/core/java/android/os/IInputConstants.aidl`
- `frameworks/base/core/java/android/app/AnrTypes.java`
- `frameworks/base/core/java/android/content/ContentResolver.java`
- `frameworks/base/core/java/android/content/ContentProviderClient.java`
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java`
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java`
- `frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java`
- `frameworks/base/services/core/java/com/android/server/am/TimeoutRecord.java`

官方资料：

- [Keep your app responsive：ANR 类型与基础诊断](https://developer.android.com/topic/performance/vitals/anr)
- [Diagnose and fix ANRs：广播、输入、execute-service 与 Provider 诊断](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Foreground service timeout behavior](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Troubleshoot foreground services](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [`JobService` API reference](https://developer.android.com/reference/android/app/job/JobService)
