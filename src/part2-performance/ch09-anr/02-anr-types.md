---
title: "ANR 类型与触发条件"
section: "9.2"
chapter: "9.2"
status: ready-for-review
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-14.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/BroadcastQueue.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: blog
    path: "intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md"
tags: [anr, input-dispatching, broadcast, service, contentprovider, timeout]
related_chapters: ["9.1", "9.3", "9.4", "1.4", "1.5", "1.10"]
reviewed_date: "2026-04-16"
review_v2_date: "2026-04-09"
review_v2_by: "openclaw-task6"
review_type: "post-polish-quality-gate"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_review_date: "2026-04-16"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: idle
---

# ANR 类型与触发条件

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Input Dispatching Timeout：5s，触摸/按键事件无响应
- 🔹 BroadcastReceiver Timeout：前台 10s / 后台 60s
- 🔹 Service Timeout：前台 20s / 后台 200s
- 🔹 ContentProvider Timeout：10s（publish timeout）
- 🔹 各类型 ANR 在 Logcat 中的标识特征

### 扩展（可选深入）

- 🔸 执行 Service startForeground 的 ANR（FGS 超时）
- 🔸 JobService 超时机制与 ANR 的关系

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 ANR 的类型分类

在上一节中，我们了解了 ANR 机制的设计思想——系统通过超时计时器在应用失去响应能力时介入。但"超时"不是一个统一的概念，不同类型的 ANR 有不同的触发条件、超时阈值和检测机制。如果拿到一份 ANR trace，第一步就是判断它属于哪种类型——因为不同类型的 ANR，分析方法完全不同。

举例来说，一个 Input ANR 意味着主线程在用户点击后 5 秒内没有处理完输入事件，问题通常出在主线程被阻塞。而一个 Broadcast ANR 可能在后台静默发生，超时时间长达 60 秒，根因可能完全不在主线程——而是 `goAsync()` 的后台任务没有及时调用 `finish()`。

了解每种 ANR 类型的触发条件，是精准分析 ANR 的前提。

## Input Dispatching Timeout（输入分发超时）

### 超时阈值：5 秒

这是开发者最常遇到的 ANR 类型，也是用户最直接能感知到的。当用户触摸屏幕或按下按键时，系统通过 InputDispatcher 将事件分发给对应窗口所在的 App 进程。如果 App 的主线程在 5 秒内没有处理完这个事件（更精确地说，没有"消费"或"丢弃"该事件），InputDispatcher 就会触发 ANR。

[已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### 检测机制：从 InputDispatcher 到 AMS

Input ANR 的检测不在 Java 层，而是在 Native 层的 InputDispatcher 中完成。整个检测流程可以拆解为以下几步：

**第一步：事件入队。** InputReader 从 EventHub 读取原始输入事件后，交给 InputDispatcher。InputDispatcher 将事件放入 outboundQueue，准备分发给目标窗口。

**第二步：等待确认。** 事件通过 InputChannel（基于 Unix socketpair）发送给 App 进程的 InputConsumer。App 主线程的 Looper 被唤醒，将事件交给 InputEventReceiver 处理。处理完成后，App 通过同一个 InputChannel 发回"已消费"确认。

**第三步：超时检测。** InputDispatcher 将已发送但未确认的事件移入 waitQueue，并记录每个事件的发送时间。在每次处理循环中，InputDispatcher 检查 waitQueue 头部的事件——如果它已经等待超过 `DEFAULT_INPUT_DISPATCHING_TIMEOUT`（5 秒），就调用 `onAnrLocked()`。

这里有一个重要的细节：**超时检测是针对 waitQueue 头部的事件**，而不是最新的事件。所以如果队列中有多个未确认事件，超时计算的是最老的那个。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
// @ AOSP android-14.0.0_r1
const nsecs_t DEFAULT_INPUT_DISPATCHING_TIMEOUT = 5000 * 1000000LL; // 5 sec
```

**第四步：通知 AMS。** InputDispatcher 检测到超时后，通过 `InputManagerCallback` -> `WindowManagerService` -> `ActivityManagerService.inputDispatchingTimedOut()` 的调用链通知 AMS。

### 在 Logcat 中的特征

```
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: Input dispatching timed out (Waiting to send non-key event because the
        touched window has not finished processing certain input events that were
        delivered to it over 500.0ms ago. Wait queue length: 33. Wait queue head age: 6178.1ms.)
```

关键信息：**"Input dispatching timed out"** 明确标识这是 Input ANR；**"Wait queue length"** 说明主线程事件积压程度；**"Wait queue head age"** 说明头部事件已等待超过阈值。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

### 特殊情况：无焦点窗口的 Input ANR

有一种容易忽略的 Input ANR 变体："no focused window" ANR。它发生在 InputDispatcher 试图将事件分发给一个应该有焦点、但实际上没有对应窗口的 App。这种情况虽然也归类为 Input ANR，但根因可能不是主线程阻塞，而是窗口切换过程中的状态不一致。

## BroadcastReceiver Timeout（广播超时）

与 Input ANR 不同，Broadcast ANR 的触发并不依赖用户交互——它可能在一个完全没有用户操作的静默时段发生。理解它的超时机制，有助于排查那些“明明没有用户操作却发生了 ANR”的问题。

### 超时阈值：前台 10 秒 / 后台 60 秒

当系统通过 BroadcastQueue 将一个有序广播（ordered broadcast）分发给 BroadcastReceiver 时，会在分发的同时启动一个超时计时器。如果 Receiver 的 `onReceive()` 方法在超时时间内没有执行完毕（对于使用了 `goAsync()` 的情况，是 `PendingResult.finish()` 没有被调用），就会触发 ANR。

前台广播（FLAG_RECEIVER_FOREGROUND）的超时是 **10 秒**，后台广播的超时是 **60 秒**：

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
// @ AOSP android-14.0.0_r1
static final int BROADCAST_FG_TIMEOUT = 10 * 1000;  // 10 seconds
static final int BROADCAST_BG_TIMEOUT = 60 * 1000;  // 60 seconds
```

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java]

### 检测机制：BroadcastQueue 的超时 Handler

Broadcast ANR 的检测逻辑在 `BroadcastQueue.broadcastTimeoutLocked()` 方法中。**只有有序广播（ordered broadcast）才会触发超时检测。** 普通的无序广播是并行分发给所有 Receiver 的，不会等待单个 Receiver 完成，因此不会产生 ANR。

`goAsync()` 的引入让这个问题更复杂了。调用 `goAsync()` 将广播处理移到后台线程时，超时计时器并不会停止——仍然需要在原始超时时间内调用 `PendingResult.finish()`。如果后台线程执行时间超过 10 秒（前台广播）或 60 秒（后台广播），仍然会触发 ANR，即使主线程完全空闲。

### 在 Logcat 中的特征

```
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: Broadcast of Intent { act=android.intent.action.BOOT_COMPLETED
        cmp=com.example.app/.receiver.BootReceiver }
```

特征是 Reason 行以 **"Broadcast of Intent"** 开头，后面跟着具体的 Action 和 Component 名称。

### 常见触发场景

**系统广播处理过重。** 比如 `BOOT_COMPLETED`、`CONNECTIVITY_CHANGE` 等系统广播的 Receiver 中执行了数据库操作、网络请求或文件 I/O。

**`goAsync()` 忘记 finish。** 开发者使用 `goAsync()` 将处理移到后台线程，但忘记在完成后调用 `PendingResult.finish()`，或者后台任务执行时间超过了超时阈值。

**有序广播分发路径中的慢 Receiver。** 有序广播按优先级依次分发给各个 Receiver，一个 Receiver 的延迟会阻塞整个链路。

## Service Timeout（服务超时）

### 超时阈值：前台 20 秒 / 后台 200 秒

Service ANR 的超时阈值在所有类型中跨度最大：前台 Service 是 **20 秒**，后台 Service 是 **200 秒**。

```java
// frameworks/base/services/core/java/com/android/server/am/ActiveServices.java
// @ AOSP android-14.0.0_r1
static final int SERVICE_FOREGROUND_TIMEOUT = 20 * 1000;  // 20 seconds
static final int SERVICE_BACKGROUND_TIMEOUT = 200 * 1000; // 200 seconds
```

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActiveServices.java]

### 检测机制：ActiveServices 的超时 Handler

超时检测的目标是 Service 的生命周期方法：`onCreate()`、`onStartCommand()` 或 `onBind()`。重要细节：**超时计算是从 Service 被调度到进程执行开始的，不是从代码开始执行开始的。** 如果进程本身还在启动（冷启动场景），进程启动时间也计算在内。

### 在 Logcat 中的特征

```
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: executing service com.example.app/com.example.app.MyService
```

特征是 Reason 行以 **"executing service"** 开头。

### startForeground 的 5 秒超时

从 Android 8.0 开始，系统引入了 `Context.startForegroundService()` 方法。严格要求：**Service 必须在启动后 5 秒内调用 `startForeground()`**。超时后果按版本不同：

- **Android 8-11：** 触发 ANR 对话框
- **Android 12+：** 直接抛出 `ForegroundServiceDidNotStartInTimeException`，导致 App 崩溃

常见触发场景：

1. `onStartCommand()` 中有阻塞操作，阻塞了 `startForeground()` 的调用
2. 等待异步结果（如网络请求）后再调用 `startForeground()`，但异步操作超过 5 秒
3. 从后台启动，被系统调度延迟

**正确做法：** 先调用 `startForeground()` 展示通知，再执行其他逻辑。

[已验证: 官方文档, developer.android.com/guide/components/fg-services]

## ContentProvider Timeout（内容提供者超时）

前三种 ANR 类型都围绕主线程的“执行超时”，ContentProvider ANR 的触发逻辑有所不同——它的超时发生在“发布”阶段，也就是 App 还没来得及执行任何业务代码的时候。

### 超时阈值：10 秒（publish timeout）

系统在两种场景下检测 ContentProvider 的超时：

**场景一：Provider 发布超时。** 当 App 进程启动时，系统等待该进程 publish 其声明的 ContentProvider。如果进程在 **10 秒**内没有完成 `ContentProvider.onCreate()` 并返回 provider 对象，就会触发 ANR。这个超时尤其危险，因为它发生在应用启动的早期阶段——Provider 不 publish，Activity 就无法启动。

**场景二：Provider 客户端超时。** 当一个 App 通过 `ContentResolver.query()` 访问另一个 App 的 ContentProvider 时，如果 Provider 端响应过慢，客户端的 Binder 线程会被阻塞。虽然没有独立的超时计时器，但阻塞时间过长可能导致客户端进程因 Binder 线程耗尽而触发 ANR。

### 在 Logcat 中的特征

```
E/ActivityManager: ANR in com.example.app (PID: 12345)
Reason: ContentProvider com.example.app/.provider.MyProvider not responding
```

特征是 Reason 行包含 **"ContentProvider"** 和 **"not responding"**。

## 各类型 ANR 速查对照表

| 类型 | 超时阈值 | 检测位置 | 触发条件 | 用户感知 |
|------|---------|---------|---------|---------|
| Input Dispatching | 5s | InputDispatcher (Native) | 主线程未消费输入事件 | 直接感知，界面冻结 |
| Broadcast (前台) | 10s | BroadcastQueue (AMS) | Receiver.onReceive() 未完成 | 可能无感知 |
| Broadcast (后台) | 60s | BroadcastQueue (AMS) | Receiver.onReceive() 或 goAsync 未完成 | 无感知 |
| Service (前台) | 20s | ActiveServices (AMS) | onCreate/onStartCommand/onBind 未完成 | 可能无感知 |
| Service (后台) | 200s | ActiveServices (AMS) | onCreate/onStartCommand/onBind 未完成 | 无感知 |
| ContentProvider | 10s | AMS | Provider 未在时间内 publish | 间接感知（阻塞启动） |
| startForeground | 5s | AMS | startForeground() 未在时间内调用 | Android 12+ 直接崩溃 |

## 在 Perfetto 中的表现

**Input ANR** 最容易识别。目标 App 主线程 Track 中出现一段很长的 Running/Runnable 状态，InputDispatcher Track 中出现 ANR 标记，SurfaceFlinger 中 App 没有提交新 Frame。

**Service/Broadcast ANR** 更隐蔽。主线程可能在等待 Binder 返回（`binder_thread_read` sleep 状态），也可能在执行耗时操作。关键线索是检查 ANR 时间点前后的系统事件 Track。

**ContentProvider ANR** 表现为目标进程启动阶段过长。进程已创建但 `ContentProvider.onCreate()` 长时间未返回，调用方进程在等待 Binder 响应。

[待补充：Trace 截图展示各类型 ANR 在 Perfetto 中的具体 Track 和时间线特征]

## 版本演进中的变化

> 本节追踪 Android 8.0 到 Android 17 中与 ANR 触发条件和超时阈值相关的关键变更。未提及的版本意味着对应版本没有重大变化。

**Android 8.0（API 26）：** 引入 `startForegroundService()` / `startForeground()` 的 5 秒超时要求。

**Android 12（API 31）：** `startForeground()` 超时不再触发 ANR 对话框，而是直接抛出 `ForegroundServiceDidNotStartInTimeException` 导致崩溃。

**Android 14（API 34）：** 对前台 Service 限制进一步收紧，引入更多前台 Service 类型和对应的超时策略。

**Android 15（API 35）：** 新增 `dataSync` 和 `mediaProcessing` 前台 Service 的累计运行时间限制（后台 24 小时内 6 小时），以及 `shortService` 类型约 3 分钟的超时直接触发机制 [待验证: shortService 具体超时阈值因 OEM 实现可能不同]。

[来源: intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md]

## JobService 超时机制与 ANR 的关系 [扩展]

JobService 本身不直接触发 ANR，它有自己的超时机制。当 JobScheduler 调度一个 Job 后，如果 `JobService.onStartJob()` 返回 `true`，系统会等待 `jobFinished()` 被调用。如果等待时间过长（通常是几分钟级别），系统会强制停止该 Job 并调用 `onStopJob()`。

虽然不是传统 ANR，但从行为上看它与 Service ANR 类似——都是系统对"任务执行时间过长"的干预机制。区别在于 ANR 是面向用户体验的紧急干预（超时短，用户直接感知），而 JobScheduler 超时是面向资源管理的调度干预（超时长，用户不感知）。

[来源: intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md]
[待验证: JobService onStopJob 的具体超时阈值在不同 Android 版本中的变化]

## 各类型 ANR 在 Logcat 中的标识特征汇总

| ANR 类型 | Logcat Reason 关键词 |
|----------|---------------------|
| Input | `Input dispatching timed out` |
| Broadcast | `Broadcast of Intent` |
| Service | `executing service` |
| ContentProvider | `ContentProvider` + `not responding` |
| startForeground (12+) | `startForegroundService() did not then call Service.startForeground()` |

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

**误区三："所有广播都可能导致 ANR。"** 只有有序广播（ordered broadcast）和动态注册的 Receiver 才会触发超时检测。普通无序广播不会。

**误区四："Service ANR 只发生在前台 Service。"** 后台 Service 超时是 200 秒，长时间操作仍可能触发。

**误区五："ContentProvider ANR 不常见。"** 在使用多个 ContentProvider 做初始化的架构中（很多第三方 SDK 通过 ContentProvider 做自动初始化），任何一个超时都会阻塞整个 App 启动。

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — Input ANR 超时检测
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — ANR 常量定义
  - `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` — Service 超时检测
  - `frameworks/base/services/core/java/com/android/server/BroadcastQueue.java` — Broadcast 超时检测
- 官方文档：
  - https://developer.android.com/topic/performance/vitals/anr
  - https://developer.android.com/guide/components/fg-services
- 研究素材：
  - intake/research-feeds/2026-04-01-07-ch09-binder-anr-android15-16-17.md
