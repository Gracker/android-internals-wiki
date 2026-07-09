---
title: "ANR 类型与触发条件"
section: "9.2"
chapter: "9.2"
status: finalized
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
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
reviewed_date: "2026-05-06"
review_v2_date: "2026-04-09"
review_v2_by: "openclaw-task6"
review_type: "post-polish-quality-gate"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_review_v2_date: "2026-05-03"
task6_review_date: "2026-04-16"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-05-06T07:51:16+08:00"
task9_reviewed_date: "2026-07-09"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-07-09T21:30:58+08:00"
last_task9_autofix_at: "2026-07-09"
task2b_fixed_at: "2026-04-26T13:40:00+08:00"
rework_by: openclaw-task2b
rework_type: "Task9 Deep Tech Review 回炉修复（4项源码/版本/命令错误）"
task9_review_notes: "2026-05-24 07:40 Task9 deep-review: pass-tech-review。无 P0/P1；P2 2 项已写入 suggestions；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-09 Task9 闲时抽检：auto-fixed。修正 Android 17 源码锚点、Broadcast ANR 路径、Input ANR logcat 口径与源码映射行号，回到 Task6 复审。 | 2026-07-09 21:30 Task9 deep-review：pass-tech-review。复核 Android 17 InputDispatcher、BroadcastQueueImpl/BroadcastAnrTimer、ActiveServices、ContentResolver Provider timeout、JobServiceContext 等源码锚点，无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task6_at: 2026-07-09T21:10:00+08:00
last_task6_audit: 2026-07-09
auto_promoted: true
task6_review_notes: "2026-05-06 task6 revisiting review 08:15: pass-light-edit。清理重复 DeepResearch 注入块与引用元信息；Task9 复审已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-07-09"
last_task9_audit_log: "logs/deep-review/2026-07-09-06-audit.md"
last_task9_review_log: "logs/deep-review/2026-07-09-21-deep-review.md"
p0: 0
p1: 0
p2: 2
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-31
verifier_checked: 2026-07-09
task6_reviewed_date: 2026-07-09
auto_promoted_date: "2026-07-09"
updated_by: "openclaw-task9"
updated_date: "2026-07-09"
---
# ANR 类型与触发条件

## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Input Dispatching Timeout：5s，触摸/按键事件无响应
- 🔹 BroadcastReceiver Timeout：Android 13 及以下前台 10s / 后台 60s；Android 14+ 前台 10-20s / 后台 60-120s
- 🔹 Service Timeout：前台 20s / 后台 200s
- 🔹 ContentProvider Timeout：10s（publish timeout）
- 🔹 各类型 ANR 在 Logcat 中的标识特征

### 扩展（可选深入）

- 🔸 执行 Service startForeground 的 ANR（FGS 超时）
- 🔸 Android 14+ JobService callback ANR 与 job 超时边界

### OpenClaw 加工指引

## 为什么要了解 ANR 的类型分类

在上一节中，我们了解了 ANR 机制的设计思想——系统通过超时计时器在应用失去响应能力时介入。但"超时"不是一个统一的概念，不同类型的 ANR 有不同的触发条件、超时阈值和检测机制。如果拿到一份 ANR trace，第一步就是判断它属于哪种类型——因为不同类型的 ANR，分析方法完全不同。

举例来说，一个 Input ANR 意味着主线程在用户点击后 5 秒内没有处理完输入事件，问题通常出在主线程被阻塞。而一个 Broadcast ANR 可能在后台静默发生，超时时间长达 60 秒，根因可能完全不在主线程——而是 `goAsync()` 的后台任务没有及时调用 `finish()`。

了解每种 ANR 类型的触发条件，是精准分析 ANR 的前提。

## Input Dispatching Timeout（输入分发超时）

### 超时阈值：5 秒

这是开发者最常遇到的 ANR 类型，也是用户最直接能感知到的。当用户触摸屏幕或按下按键时，系统通过 InputDispatcher 将事件分发给对应窗口所在的 App 进程。如果 App 的主线程在 5 秒内没有处理完这个事件（即没有"消费"或"丢弃"该事件），InputDispatcher 就会触发 ANR。

### 检测机制：从 InputDispatcher 到 AMS

Input ANR 的检测不在 Java 层，而是在 Native 层的 InputDispatcher 中完成。整个检测流程可以拆解为以下几步：

**第一步：事件入队。** InputReader 从 EventHub 读取原始输入事件后，交给 InputDispatcher。InputDispatcher 将事件放入 outboundQueue，准备分发给目标窗口。

**第二步：等待确认。** 事件通过 InputChannel（基于 Unix socketpair）发送给 App 进程的 InputConsumer。App 主线程的 Looper 被唤醒，将事件交给 InputEventReceiver 处理。处理完成后，App 通过同一个 InputChannel 发回"已消费"确认。

**第三步：超时检测。** InputDispatcher 将已发送但未确认的事件移入 waitQueue，并记录每个事件的发送时间。在每次处理循环中，InputDispatcher 检查 waitQueue 头部的事件——如果它已经等待超过 `DEFAULT_INPUT_DISPATCHING_TIMEOUT`（5 秒），就调用 `onAnrLocked()`。

**超时检测是针对 waitQueue 头部的事件**，不是最新的事件。队列中有多个未确认事件时，超时计算的是最老的那个。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
// @ AOSP android-17.0.0_r1
// 实际实现使用 std::chrono，并通过 HwTimeoutMultiplier 缩放
static constexpr std::chrono::nanoseconds DEFAULT_INPUT_DISPATCHING_TIMEOUT =
    std::chrono::milliseconds(
        IInputConstants::UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS
        * HwTimeoutMultiplier());
// 默认约 5s（UNMULTIPLIED_DEFAULT = 5000ms, HW multiplier 默认 1.0）
```

**第四步：通知 AMS。** InputDispatcher 检测到超时后，通过 `InputManagerCallback` -> `WindowManagerService` -> `ActivityManagerService.inputDispatchingTimedOut()` 的调用链通知 AMS。

### 在 Logcat 中的特征

```logcat
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: Input dispatching timed out: com.example.app/.MainActivity is not responding.
        Waited 6178ms for MotionEvent(action=ACTION_DOWN, ...)
```

关键信息：**"Input dispatching timed out"** 明确标识这是 Input ANR；**"Waited ...ms"** 对应 Android 17 `InputDispatcher::onAnrLocked()` 中 oldest entry 从 `deliveryTime` 到触发时的等待时间；事件描述用于判断卡住的是按键、触摸还是无焦点窗口路径。

### 特殊情况：无焦点窗口的 Input ANR

有一种容易忽略的 Input ANR 变体："no focused window" ANR。它发生在 InputDispatcher 试图将事件分发给一个应该有焦点、但没有对应窗口的 App。这种情况虽然也归类为 Input ANR，但根因可能不是主线程阻塞，而是窗口切换过程中的状态不一致。

## BroadcastReceiver Timeout（广播超时）

与 Input ANR 不同，Broadcast ANR 的触发并不依赖用户交互——它可能在一个完全没有用户操作的静默时段发生。理解它的超时机制，有助于排查那些“明明没有用户操作却发生了 ANR”的问题。

### 超时阈值：Android 13 及以下前台 10 秒 / 后台 60 秒；Android 14+ 前台 10-20 秒 / 后台 60-120 秒

Broadcast ANR 的判断要同时看前后台优先级、同步还是异步 receiver，以及应用启动时间有没有落进同一段窗口。Android 13 及以下按前台 **10 秒**、后台 **60 秒** 排查；Android 14+ 官方诊断口径改成前台 **10-20 秒**、后台 **60-120 秒**。进程处于 CPU-starved 状态时，系统会把窗口拉到上限；没有 CPU starvation 时，排查起点仍接近 10 秒 / 60 秒。

`goAsync()` 不会重置这段窗口。同步 receiver 要在 `onReceive()` 内返回；异步 receiver 要在同一窗口内调用 `PendingResult.finish()`。如果广播拉起了冷启动进程，进程启动和 `Application` 初始化时间也会算进这次超时。

### 检测机制：BroadcastQueueImpl 的超时计时器

Android 17 主线源码中，Broadcast ANR 不再以旧版 `BroadcastQueue.broadcastTimeoutLocked()` 或 `BroadcastQueueModernImpl` 作为锚点。当前路径是 `BroadcastQueueImpl.startDeliveryTimeoutLocked()` 通过 `BroadcastAnrTimer` 启动软超时；命中后进入 `deliveryTimeoutLocked()`，随后在 `finishReceiverActiveLocked()` 中构造 `TimeoutRecord.forBroadcastReceiver()` 并调用 `mService.appNotResponding()`。

做 App 侧排障时，判断边界比“ordered / parallel”更直接：

- **同步 receiver**：`onReceive()` 必须在当前广播窗口内返回。
- **异步 receiver**：调用 `goAsync()` 后，`PendingResult.finish()` 也必须在同一窗口内完成。
- **冷启动 receiver**：如果广播唤起了进程，进程启动、`Application` 初始化和 receiver 执行共享同一段超时预算。

`ordered / parallel` 仍然有价值，但它更适合解释分发路径和是否会拖住后续 receiver；单看这一条已经不够覆盖 Android 14+ 的超时诊断口径。

### 在 Logcat 中的特征

```logcat
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: Broadcast of Intent { act=android.intent.action.BOOT_COMPLETED
        cmp=com.example.app/.receiver.BootReceiver }
```

特征是 Reason 行以 **"Broadcast of Intent"** 开头，后面跟着具体的 Action 和 Component 名称。

### 常见触发场景

**冷启动流程过长。** 广播拉起进程后，Zygote fork、`Application` 初始化、`ContentProvider` 初始化和 receiver 业务代码都在同一窗口里，启动阶段慢会先把预算吃掉。

**`goAsync()` 后台线程没有及时 finish。** `goAsync()` 只把工作移出 `onReceive()`，没有获得新的超时预算。后台线程被共享线程池、网络等待或 Binder 阻塞拖住时，仍会触发 ANR。

**慢 Receiver 拖住广播分发。** 有序广播里，一个 Receiver 的延迟会顺着队列传递给后续 Receiver；并行分发场景里，单个进程仍可能因为自己的处理超时而报 ANR。

## Service Timeout（服务超时）

### 超时阈值：前台 20 秒 / 后台 200 秒

Service ANR 的超时阈值在所有类型中跨度最大：前台 Service 是 **20 秒**，后台 Service 是 **200 秒**。

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
// @ AOSP android-17.0.0_r1
private static final long DEFAULT_SERVICE_TIMEOUT =
        20 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long DEFAULT_SERVICE_BACKGROUND_TIMEOUT =
        DEFAULT_SERVICE_TIMEOUT * 10;
```

### 检测机制：ActiveServices 的超时 Handler

超时检测的目标是 Service 的生命周期方法：`onCreate()`、`onStartCommand()` 或 `onBind()`。Android 14 的 `ActiveServices` 不再自己声明固定的 20 秒 / 200 秒常量，而是在调度超时时读取 `mAm.mConstants.SERVICE_TIMEOUT` 和 `mAm.mConstants.SERVICE_BACKGROUND_TIMEOUT`。默认值仍对应前台 20 秒、后台 200 秒，但会乘 `Build.HW_TIMEOUT_MULTIPLIER`，运行时也可能被系统配置覆盖。

另一个细节是，超时计算从 Service 被调度到进程执行开始，不是从业务代码第一行开始。如果进程本身还在启动，进程启动时间也计算在内。

### 在 Logcat 中的特征

```logcat
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: executing service com.example.app/com.example.app.MyService
```

特征是 Reason 行以 **"executing service"** 开头。

### startForegroundService 到 startForeground 的宽限期

这条超时链和普通 Service 的 20 秒 / 200 秒执行超时不是一回事。它约束的是 `Context.startForegroundService()` 之后，Service 多久必须调用 `startForeground()` 完成前台晋升。

- **Android 8.0：** AOSP `ActiveServices.SERVICE_START_FOREGROUND_TIMEOUT = 5 * 1000`，宽限期 5 秒
- **Android 9-12：** AOSP 把这条宽限期提升到 10 秒
- **Android 13-17：** 默认值迁到 `ActivityManagerConstants.DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS`，默认 30 秒，对应运行时字段 `mServiceStartForegroundTimeoutMs`

超时后的后果取决于哪条超时链被触发，这里要把两条路径分开看。

**路径一：startForeground 未调用（DidNotStartInTime）。** `Context.startForegroundService()` 之后，Service 在宽限期内没有调用 `startForeground()`。AOSP 路径是 `ActiveServices.serviceForegroundTimeout()` → `stopServiceLocked()` → 延迟 `SERVICE_FOREGROUND_TIMEOUT_ANR_MSG` → `appNotResponding()`。Android 12+ 对此抛出 `ForegroundServiceDidNotStartInTimeException`——这条路径没有 `Service.onTimeout()` 回调自救，超时就直接进入 ANR/异常流程。

**路径二：FGS 运行超时（shortService / dataSync / mediaProcessing）。** Service 已经成功调用了 `startForeground()`，但运行时间超过该 FGS 类型的限额。以 Android 14+ 的 `shortService`（约 3 分钟）为例：**第一阶段**是回调自救——系统通过 `Service.onTimeout()` 给应用一个窗口执行清理并调用 `stopSelf()`；**第二阶段**是硬性惩罚——如果应用在宽限期内没有主动停止，系统抛出 `ForegroundServiceDidNotStopInTimeException` 或直接杀进程。Android 15 的 `dataSync`（6 小时）和 `mediaProcessing`（6 小时）走同样的两段式语义，各自类型在后台 24 小时窗口内累计运行不超过 6 小时（AOSP `ActivityManagerConstants.DEFAULT_MEDIA_PROCESSING_FGS_TIMEOUT_DURATION = 6 * 60 * 60_000`，`DEFAULT_DATA_SYNC_FGS_TIMEOUT_DURATION` 同理）。

这两条路径的入口、触发条件和后果都不同，排查时要先确认是"没有调 startForeground"还是"FGS 运行超时"。

常见触发场景：

1. `onStartCommand()` 中有阻塞操作，阻塞了 `startForeground()` 的调用
2. 等待异步结果（如网络请求）后再调用 `startForeground()`，但异步操作超过当前版本的宽限期
3. 从后台启动，被系统调度延迟

**正确做法：** 先调用 `startForeground()` 展示通知，再执行其他逻辑。

## ContentProvider Timeout（内容提供者超时）

前三种 ANR 类型都围绕主线程的“执行超时”，ContentProvider ANR 的触发逻辑有所不同——它的超时发生在“发布”阶段，也就是 App 还没来得及执行任何业务代码的时候。

### 超时阈值：10 秒（publish timeout）

系统在两种场景下检测 ContentProvider 的超时：

**场景一：Provider 发布超时。** 当 App 进程启动时，系统等待该进程 publish 其声明的 ContentProvider。如果进程在 **10 秒**内没有完成 `ContentProvider.onCreate()` 并返回 provider 对象，就会触发 ANR。这个超时尤其危险，因为它发生在应用启动的早期阶段——Provider 不 publish，Activity 就无法启动。

**场景二：Provider 客户端超时。** 当一个 App 通过 `ContentResolver.query()` 访问另一个 App 的 ContentProvider 时，如果 Provider 端响应过慢，客户端的 Binder 线程会被阻塞。虽然没有独立的超时计时器，但阻塞时间过长可能导致客户端进程因 Binder 线程耗尽而触发 ANR。

### 在 Logcat 中的特征

```logcat
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: ContentProvider com.example.app/.provider.MyProvider not responding
```

特征是 Reason 行包含 **"ContentProvider"** 和 **"not responding"**。

## 各类型 ANR 速查对照表

| 类型 | 超时阈值 | 检测位置 | 触发条件 | 用户感知 |
|------|---------|---------|---------|---------|
| Input Dispatching | 5s | InputDispatcher (Native) | 主线程未消费输入事件 | 直接感知，界面冻结 |
| Broadcast (前台) | Android 13 及以下 10s；Android 14+ 10-20s | BroadcastQueueImpl / BroadcastAnrTimer (AMS) | `onReceive()` 未返回，或 `goAsync()` 后未 `finish()` | 可能无感知 |
| Broadcast (后台) | Android 13 及以下 60s；Android 14+ 60-120s | BroadcastQueueImpl / BroadcastAnrTimer (AMS) | 同上；冷启动时间也可能计入窗口 | 无感知 |
| Service (前台) | 20s | ActiveServices (AMS) | `onCreate()` / `onStartCommand()` / `onBind()` 未完成 | 可能无感知 |
| Service (后台) | 200s | ActiveServices (AMS) | `onCreate()` / `onStartCommand()` / `onBind()` 未完成 | 无感知 |
| ContentProvider | 10s | AMS | Provider 未在时间内 publish | 间接感知（阻塞启动） |
| startForeground | Android 8.0 5s / 9-12 10s / 13-14+ 默认 30s | AMS | `startForeground()` 未在宽限期内调用 | Android 12+ 常见直接崩溃 |
| JobService callback (14+) | 8s（`OP_TIMEOUT_MILLIS` × HW_TIMEOUT_MULTIPLIER） | JobScheduler / AMS | `onStartJob()` 或 `onStopJob()` 主线程未及时返回 | 多为后台无感知 |

## 在 Perfetto 中的表现

**Input ANR** 最容易识别。目标 App 主线程 Track 中出现一段很长的 Running/Runnable 状态，InputDispatcher Track 中出现 ANR 标记，SurfaceFlinger 中 App 没有提交新 Frame。

**Service/Broadcast ANR** 更隐蔽。主线程可能在等待 Binder 返回（`binder_thread_read` sleep 状态），也可能在执行耗时操作。关键线索是检查 ANR 时间点前后的系统事件 Track。

**ContentProvider ANR** 表现为目标进程启动阶段过长。进程已创建但 `ContentProvider.onCreate()` 长时间未返回，调用方进程在等待 Binder 响应。

## 版本演进中的变化

> 本节追踪 Android 8.0 到 Android 17 中与 ANR 触发条件和超时阈值相关的关键变更。未提及的版本意味着对应版本没有重大变化。

**Android 8.0（API 26）：** 引入 `startForegroundService()` / `startForeground()` 的 5 秒宽限期。

**Android 9-12（API 28-32）：** AOSP 把 `startForegroundService()` 到 `startForeground()` 的宽限期提升到 10 秒；Android 12 同时把超时结果收紧为 `ForegroundServiceDidNotStartInTimeException`。

**Android 13（API 33）：** `startForegroundService()` 到 `startForeground()` 的默认宽限期仍是 30 秒；Broadcast 超时排障口径通常仍按前台 10 秒、后台 60 秒。

**Android 14（API 34）：** BroadcastReceiver 的官方诊断口径更新为前台 10-20 秒、后台 60-120 秒，并把 CPU starvation 与 app startup 纳入超时窗口解释。引入 `shortService` 前台 Service 类型，约 3 分钟运行超时，超时后走 `Service.onTimeout()` 回调自救 → 硬杀的两段式语义。targetSdk 34+ 的 `JobService.onStartJob()` / `onStopJob()` 超时也会以显式 ANR 上报。`AnrTimer` 已在 AOSP `android-15.0.0_r1` 中存在（`com.android.server.utils.AnrTimer`），`ActiveServices` 中已使用 `ServiceAnrTimer`；Android 16 在此基础上继续完善。

**Android 15（API 35）：** 新增 `dataSync` 和 `mediaProcessing` 前台 Service 类型，各自类型在后台 24 小时窗口内累计运行时间限制为 6 小时（`dataSync` 与 `mediaProcessing` 同类型服务共享配额，AOSP `ActivityManagerConstants` 中两者超时常量一致）。`dataSync` 和 `mediaProcessing` 的累计限制是跨生命周期的——重启进程或杀掉 App 不能重置计时器，必须真实结束任务或等待 24 小时窗口滚动。开发者不能通过"拆分多个短任务 + 重启 Service"来绕过配额。

**Android 16（API 36）：** `AnrTimer` 在 Android 15 已引入的基础上进一步扩展覆盖范围。传统 Handler 计时受 AMS 主线程负载影响：如果 AMS 主线程在处理其他事务（比如同时处理多个应用的 ANR dump），超时消息可能延迟投递，导致 ANR 检测不准时。`AnrTimer` 在独立线程中运行，不受 Java 层调度抖动影响，计时精度更高。调试时可在 `adb shell dumpsys activity` 的完整输出中查找 `AnrTimer` dump 段（AOSP `AnrTimer.dump(pw, false)` 会输出当前活跃的 ANR 计时器状态），具体过滤命令需以目标版本的 `dumpsys activity` 输出格式为准。

**Android 17（API 37）：** Broadcast ANR 的源码锚点收敛在 `BroadcastQueueImpl`、`BroadcastAnrTimer` 与 `AnrTimer`；`BroadcastQueueModernImpl.java` 不在 `android-17.0.0_r1` 源码树中，不能作为 Android 17 主线结论的引用路径。

## JobService callback ANR 与 job 超时的边界 [扩展]

Android 14 起，JobScheduler 不再只是长任务调度器。对 targetSdk 34+ 的应用，`JobService.onStartJob()` 和 `JobService.onStopJob()` 都运行在主线程；如果这两个 callback 在 8 秒内不返回（AOSP `JobServiceContext.OP_TIMEOUT_MILLIS = 8 * 1000 * Build.HW_TIMEOUT_MULTIPLIER`，`handleOpTimeoutLocked()` 生成 `No response to onStartJob/onStopJob` 并调用 `ActivityManagerInternal.appNotResponding()`），系统会直接报 ANR。Android 13 及以下这类 ANR 多为 silent ANR，不会显式回传给应用。

这里要把三条超时链分开看：

- **JobService callback ANR**：`onStartJob()` / `onStopJob()` 主线程卡住，超过 `OP_TIMEOUT_MILLIS`（默认 8 秒 × `HW_TIMEOUT_MULTIPLIER`）不返回，`handleOpTimeoutLocked()` 调用 `appNotResponding()` 触发 ANR。
- **Job 运行超时**：`onStartJob()` 已返回且返回 `true`，系统开始等待 `jobFinished()`。这条线通常是分钟级调度超时，超时后系统会停止 job 并回调 `onStopJob()`；它不等同于 ANR。
- **普通 Service ANR**：`JobService` 作为 `Service` 子类，仍受 Service 生命周期与前台服务规则影响；但这条线针对的是 `onCreate()` / `onStartCommand()` / `onBind()` 或 `startForeground()` 宽限期，不等于 JobScheduler callback ANR。

另一条独立规则是 user-initiated job：`onStartJob()` 返回后，应用还要在几秒内调用 `JobService.setNotification()`；这条要求超时也会落进 JobScheduler 的 ANR 诊断。

## 各类型 ANR 在 Logcat 中的标识特征汇总

| ANR 类型 | Logcat Reason 关键词 |
|----------|---------------------|
| Input | `Input dispatching timed out` |
| Broadcast | `Broadcast of Intent` |
| Service | `executing service` |
| ContentProvider | `ContentProvider` + `not responding` |
| startForeground (12+) | `startForegroundService() did not then call Service.startForeground()` |
| JobService callback (14+) | `No response to onStartJob` / `No response to onStopJob` |

掌握这些模式后，我们可以在拿到 ANR 报告的几秒钟内判断类型，进而选择正确的分析路径。

快速提取 ANR 类型的命令行方式：

```bash
# 从 logcat 中提取最近一条 ANR 的类型
adb logcat -d -s ActivityManager:E | grep "ANR in" | tail -1

# 从 ANR trace 文件中查看详细信息（Android 11+ 路径）
adb shell cat /data/anr/anr_* | tail -200
```

第一条命令可以直接看到 Reason 行，从而判断 ANR 类型。第二条命令可以获取完整的 ANR trace，包含当时所有线程的调用栈。

## 常见问题与误区

**误区一："ANR 超时时间都是 5 秒。"** 5 秒只适用于 Input ANR。Service 后台超时是 200 秒，Broadcast 后台超时是 60 秒。

**误区二："只有主线程阻塞才会导致 ANR。"** Broadcast ANR 可能发生在 `goAsync()` 的后台线程中；ContentProvider publish 超时发生在进程启动阶段。

**误区三："Broadcast ANR 只要看 ordered / 动态注册 就够了。"** App 侧排查还要同时看前后台优先级、同步还是 `goAsync()`、以及广播是否把冷启动时间带进同一窗口。`ordered / parallel` 更适合用来解释 AOSP 分发路径。

**误区四："Service ANR 只发生在前台 Service。"** 后台 Service 超时是 200 秒，长时间操作仍可能触发。

**误区五："ContentProvider ANR 不常见。"** 在使用多个 ContentProvider 做初始化的架构中（很多第三方 SDK 通过 ContentProvider 做自动初始化），任何一个超时都会阻塞整个 App 启动。

## 参考资料

- Android 14→17 Foreground Service Timeout / ANR 机制（DeepResearch，2026-04-29）：AOSP 源码视角梳理 ShortService 3 分钟超时、TimeLimitedFgs 6h / 24h 滚动窗口、AnrTimer 演进，以及 ActiveServices / ServiceRecord 中的超时判定路径。

- 官方文档：
  - https://developer.android.com/topic/performance/vitals/anr
  - https://developer.android.com/develop/background-work/services/fgs/troubleshooting
  - https://developer.android.com/guide/components/fg-services
- 研究素材：
  - intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md

<!-- AIW-源码调研-2026-06-15 -->
## 源码映射：ANR 类型与 InputDispatcher/AMS 路径

> 关联 DeepResearch：`2026-06-15-anr-detection-inputdispatcher-ams-anrhelper-source.md`

| ANR 类型 | 触发源 | 关键源码 | 阈值 |
|---------|--------|---------|------|
| **Input 派发超时** | `InputDispatcher::onAnrLocked(connection)` @ `InputDispatcher.cpp:6792` | mAnrTracker.firstTimeout() 命中 | `UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS = 5000` × HwTimeoutMultiplier |
| **无焦点窗口** | `InputDispatcher::onAnrLocked(application)` @ `InputDispatcher.cpp:6835` | mNoFocusedWindowTimeoutTime 到期 | 同上 |
| **Watchdog (system_server hang)** | `Watchdog.java:getCompletionStateLocked()` @ line 336 | 60s default / 15s pre-watchdog | `PRE_WATCHDOG_TIMEOUT_RATIO = 4` |
| **Provider 超时** | `AMS.appNotRespondingViaProvider` @ `ActivityManagerService.java:7939` | `mCpHelper.appNotRespondingViaProvider(connection)` | 沿用 AnrHelper 流程 |
| **Broadcast / Service 超时** | `ActiveServices.scheduleServiceTimeoutLocked` / `BroadcastQueueImpl.startDeliveryTimeoutLocked`、`deliveryTimeoutLocked` | Service 侧经 `ServiceAnrTimer`，Broadcast 侧经 `BroadcastAnrTimer` 后进入 `appNotResponding` | 详见各模块 |

**Input 派发超时细分**：

- **Connection ANR**（App 进程无响应）：waitQueue 头元素 `deliveryTime` 超 threshold → `connection->responsive = false` → `cancelEventsForAnrLocked` 清空后续事件。
- **No Focused Window ANR**（启动期无窗口）：focusedApplicationHandle 存在但 focusedWindowHandle 为空 → 启动超时 → 等待焦点窗口出现；若超时则归咎 application 而非窗口。

**关键 ANR 路径在 `AnrHelper` 内有 4 类 skip**（`AnrHelper.java:117-180`）：

1. zero pid（zygote 等极端）
2. mProcessingPid 命中（同一 pid 重复处理）
3. mTempDumpedPids 已 add（已被 earlyDump 处理）
4. mAnrRecords 队列里已有同 pid（已排队，避免并发 dump）

**`isContinuousAnr=true` 触发条件**：CONSECUTIVE_ANR_TIME_MS = 2min 内同一应用再次 ANR，AppNotRespondingDialog 文案会带 "持续无响应" 提示。

**Dropbox tag 命名规则**（`AMS.addErrorToDropBox` @ `ActivityManagerService.java:10537-10681`）：

- `dropboxTag = processClass(process) + "_" + eventType`
- `processClass(process)` 返回值：`system_server`（PID=system_server）/ `system_app`（system UID）/ `data_app`（其他）
- ANR tag 示例：`system_server_anr`、`system_app_anr`、`data_app_anr`
- 受 `Settings.Global.MAX_ERROR_BYTES_PREFIX + dropboxTag` 控制单条最大字节数

---

