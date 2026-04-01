---
title: "ANR 设计思想"
chapter: "9.1"
status: ready-for-review
drafted_date: "2026-04-02"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-14.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AppNotResponding.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
tags: [anr, watchdog, traces, dropbox, activitymanagerservice]
related_chapters: ["9.2", "9.3", "1.5", "8.1"]
---

# ANR 设计思想

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ANR 的设计初衷：保护用户体验，防止 App 无响应
- 🔹 ANR 机制的核心流程：注册超时 → 主线程处理 → 超时触发 → 弹窗/杀进程
- 🔹 AMS 中 ANR 的核心代码路径：AppNotResponding 类
- 🔹 ANR 与 Watchdog 的区别
- 🔹 ANR 信息的产出：traces.txt、event log、dropbox

### 扩展（可选深入）

- 🔸 各版本 ANR 机制的微调与改进
- 🔸 ANR 在 Google Play Console 中的统计与影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->

## 为什么要了解 ANR 的设计思想

当用户点击屏幕后等了几秒钟，屏幕没有任何反应——没有动画，没有反馈，就像手机死了一样。这种体验会让用户焦虑，进而愤怒，最后卸载你的 App。Android 的设计者很早就意识到，一个无响应的应用会严重损害用户对整个系统的信任，而不仅仅是对单个 App 的不满。

ANR（Application Not Responding）机制就是 Android 对这个问题的系统性回答。它不是事后诊断工具，而是一道运行时的防线：在应用失去响应能力的瞬间介入，给用户选择权——继续等待，或者杀掉它。

理解 ANR 的设计思想之所以重要，不仅因为它是 Android 性能优化的核心课题之一，更因为它直接决定了我们分析 ANR 问题时的思路。如果你不了解系统"为什么这样设计"，拿到一份 traces.txt 时很容易陷入"看堆栈猜原因"的盲人摸象——而事实上，ANR trace 的堆栈经常是"替罪羊"，真正导致超时的代码可能早已执行完毕。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md]

## ANR 的设计初衷：站在用户和系统之间

Android 设计 ANR 机制的出发点可以用一句话概括：**用户不应该被一个失控的 App 扣为人质。**

当应用的主线程被阻塞时，它无法处理任何用户输入——触摸事件、按键事件都被丢弃在消息队列中等待。如果系统不介入，用户面对的就是一块冻结的屏幕，只能强制重启手机来摆脱。

ANR 机制在这个场景中介入的方式是：设置一个超时计时器，如果在规定时间内应用没有完成某个关键操作，系统就会认为它"失去了响应能力"，然后弹出对话框让用户决定下一步。这个设计哲学有几个关键特点：

**第一，ANR 是系统对应用的强制约束，不是应用自愿配合的机制。** 超时检测在 system_server 中运行，与应用自身的代码完全隔离。即使应用的主线程已经死锁，system_server 仍然能检测到超时并介入。这种设计保证了即使应用开发者完全不考虑响应性，系统也有兜底方案。

**第二，ANR 保护的是"用户可感知的响应性"，不是"代码执行正确性"。** 系统不关心你的业务逻辑是否正确，它关心的是用户能否在合理时间内得到反馈。这就解释了为什么 ANR 超时阈值按组件类型区分：Activity 的输入事件要求 5 秒内响应（因为用户在等屏幕反馈），而后台 Service 给了 200 秒（因为用户根本看不到它在做什么）。

**第三，ANR 机制本身是一个"紧急刹车"，不应该成为常规流程的一部分。** Google 明确将 ANR 率作为应用质量的核心指标之一，ANR 过高的应用会在 Google Play 中被降权。这意味着好的应用应该"永远不会触发 ANR"，而不是"触发了 ANR 之后能优雅处理"。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

## ANR 机制的核心流程

了解了设计初衷之后，我们来看 ANR 机制具体是怎么工作的。整个流程可以抽象为四个阶段。

### 第一阶段：注册超时

当某个需要应用响应的操作开始时，system_server 会在一个后台线程上设置一个延迟消息。以 BroadcastReceiver 为例：当 AMS 将一个广播分发给目标应用时，它会同时通过 Handler 发送一个延迟消息，延迟时间就是该类型广播的超时阈值（前台广播 10 秒，后台广播 60 秒）。

这个设计的核心思路是"发令枪 + 计时器"：广播发送出去的同时，计时器开始倒计时。如果应用在规定时间内完成了 `onReceive()` 的执行并通知了 AMS，这个计时器就会被取消——一切正常，用户毫无感知。

### 第二阶段：主线程处理

此时应用的主线程正在执行 `onReceive()`（或其他超时类型的对应方法）。如果主线程当前没有被其他任务阻塞，`onReceive()` 正常执行完毕，AMS 收到完成通知，取消超时消息，流程结束。

但如果主线程正在忙于其他事情——比如前面有一个耗时 3 秒的数据库写入操作正在执行——那么 `onReceive()` 就得排队等待。如果等待时间超过了超时阈值，计时器就会到期。

这里有一个重要的细节：**超时检测和应用执行是完全异步的。** 超时计时器运行在 system_server 的后台线程上，它不会去检查应用主线程"在做什么"，它只关心"结果有没有回来"。这种设计是故意的——如果超时检测需要同步调用应用，那应用自身的问题可能连检测机制一起拖死。

### 第三阶段：超时触发

当延迟消息到期时，system_server 进入 ANR 处理流程。在 Android 14 中，这个入口是 `AnrHelper.appNotResponding()`（早期版本直接在 ActivityManagerService 或 BroadcastQueue 中处理）。

```java
// frameworks/base/services/core/java/com/android/server/am/AnrHelper.java
// @ AOSP android-14.0.0_r1
// 概念级简化
void appNotResponding(ProcessRecord app, String activityShortComponentName,
        String annotation, ProcessRecord parentProcess) {
    AppNotResponding anr = new AppNotResponding(...);
    mAnrRecords.add(anr);
    startAnrTaskIfNeeded(); // 提交到专门线程，避免阻塞 AMS 主线程
}
```

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java]

注意 `startAnrTaskIfNeeded()`——ANR 处理被放到了单独的线程中执行，目的是避免 ANR 处理逻辑阻塞 AMS 的主线程。这个设计考虑很重要：如果系统在处理一个 ANR 时又导致自身卡住，那就本末倒置了。

### 第四阶段：弹窗或杀进程

ANR 触发后，系统的处理分为两种情况：

**前台 ANR（用户可见的应用）**：系统会向用户弹出"应用无响应"对话框，用户可以选择"等待"或"关闭应用"。在对话框出现之前，系统会先收集各种诊断信息。

**后台 ANR（用户看不到的应用）**：系统直接杀掉进程，不弹对话框。用户完全无感知，只是下次打开这个 App 时可能发现它已经被系统回收了。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

## AMS 中 ANR 的核心代码路径

上一节讲了概念流程，这一节我们深入源码，看看 Android 是怎么一步步实现这个机制的。ANR 的代码路径虽然分散在多个文件中，但有一条清晰的主线。

### 入口：不同组件的 ANR 触发点

ANR 的触发点因组件类型而异，但最终都会汇聚到同一个处理流程：

**Input ANR**（Activity 触摸/按键无响应）：由 `InputDispatcher` 检测。当 InputDispatcher 发现一个输入事件在 5 秒内没有被目标窗口消费时，它会通过 `WindowManagerService` 向 AMS 报告输入超时。路径大致是 `InputDispatcher → InputManagerService(JNI) → WindowManagerService → ActivityManagerService`。

**Service ANR**：由 `ActiveServices` 检测。当 Service 启动或绑定的超时到期时，`ActiveServices.serviceTimeout()` 或 `ActiveServices.serviceForegroundTimeout()` 被调用。

**Broadcast ANR**：由 `BroadcastQueue` 检测。`BroadcastQueue.broadcastTimeoutLocked()` 在超时到期时被触发。

**ContentProvider ANR**：由 `ContentProviderHelper`（Android 14+）检测，超时阈值为 1000ms。

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/]

### 核心：AppNotResponding 类

在 Android 14 中，ANR 的核心处理逻辑被重构到了 `AppNotResponding` 类中。这个类封装了一次 ANR 事件的完整处理流程。它的核心工作包括：收集进程状态，dump 关联进程的堆栈，收集系统状态信息（CPU 负载等），通过 SIGQUIT 信号生成 traces.txt，写入 event log 和 dropbox，最后决策是弹对话框还是直接杀进程。

```java
// frameworks/base/services/core/java/com/android/server/am/AppNotResponding.java
// @ AOSP android-14.0.0_r1
// 概念级简化，展示核心步骤

// 向目标进程发送 Signal 3 (SIGQUIT) 触发堆栈 dump
Process.sendSignal(app.pid, Process.SIGNAL_QUIT);

// 写入 event log 和 dropbox
EventLog.writeEvent(EventLogTags.AM_ANR, ...);
mService.addErrorToDropBox("anr", app, ...);

// 决策：前台弹对话框，后台直接杀
if (app.isInterestingToUser()) {
    mService.showAnrDialog(app);  // 前台 ANR
} else {
    mService.killAppAtUsersRequest(app);  // 后台 ANR
}
```

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AppNotResponding.java]

这段代码揭示了几个关键细节：

**堆栈收集使用 SIGQUIT 信号。** system_server 向目标进程发送 Signal 3（SIGQUIT），触发虚拟机的堆栈 dump。这也是为什么 ANR traces 文件中会包含所有线程的堆栈——因为 SIGQUIT 的处理函数会遍历虚拟机中的所有线程。

**traces 的堆栈有滞后性。** 钉钉团队将这个问题形象地描述为"刻舟求剑"：从超时检测到发送 SIGQUIT 再到堆栈 dump 完成，中间经历了一系列异步操作。等到堆栈真正被捕获时，主线程上真正导致超时的长耗时任务可能已经执行完毕，当前正在执行的是另一个完全无关的任务。我们在 9.3 节（ANR 分析方法）中会详细讨论如何应对这个挑战。

**System Server 会向多个进程发送 SIGQUIT。** 不仅仅是对发生 ANR 的进程，系统可能会同时请求关联进程的堆栈信息。这意味着一个 App 收到 SIGQUIT 并不代表自己发生了 ANR，也可能是另一个 App 触发的。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md]

## ANR 与 Watchdog 的区别

很多开发者容易混淆 ANR 和 Watchdog 这两个机制，因为它们都涉及"超时检测"。但它们的设计目标、作用范围和处理方式完全不同，理解这个区别对性能分析非常重要。

### 作用范围不同

ANR 监控的是**应用进程**中的组件——Activity、Service、BroadcastReceiver、ContentProvider。它关心的是"某个 App 是否及时响应了系统请求"。

Watchdog 监控的是 **system_server 自身**中的核心系统服务——ActivityManagerService、WindowManagerService、PackageManagerService 等。它关心的是"系统服务是否正常运行"。

简单来说：ANR 是系统在"监视"应用，Watchdog 是系统在"监视"自己。

### 检测机制不同

ANR 采用"注册超时 → 完成取消"的模式：发起一个操作的同时设置超时计时器，操作完成后取消计时器。

Watchdog 采用"定期巡检"模式：它运行在 system_server 中的一个独立线程上，每隔一定时间（默认 60 秒）向所有注册的系统服务线程发送一个心跳检查。每个 `HandlerChecker` 监控一个 Looper 线程。如果某个服务线程在规定时间内没有响应心跳，Watchdog 就认为它出了问题。

```java
// frameworks/base/services/core/java/com/android/server/Watchdog.java
// @ AOSP android-14.0.0_r1
// 概念级简化

// 每个 HandlerChecker 监控一个 Looper 线程
final ArrayList<HandlerChecker> mHandlerCheckers = new ArrayList<>();

// 定期向所有注册的线程发送心跳
for (HandlerChecker hc : mHandlerCheckers) {
    hc.scheduleCheckLocked();
}
// 等待所有线程完成检查，如果有超时的 → dump 堆栈 + 杀 system_server
```

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/Watchdog.java]

### 后果不同

ANR 触发后，用户看到的是一个对话框——可以选择"等待"或"关闭"。App 进程可能被杀，但 system_server 不受影响，其他应用正常运行。

Watchdog 触发后，意味着 system_server 本身出了问题（通常是死锁）。此时整个设备基本上已经无法正常使用了——系统会杀掉 system_server 进程，init 进程会重新启动它，效果等同于一次"软重启"。所有正在运行的应用都会被杀掉。

### 在 Perfetto 中的表现不同

在 Perfetto Trace 中，ANR 事件通常表现为：应用主线程上出现一段长时间的非空闲执行块（RUNNABLE 或 BLOCKED），在 system_server 进程中可以看到 AnrHelper 相关的活动，Input ANR 可以在 InputDispatcher 的 track 中看到 "Application Not Responding" 标记。

Watchdog 触发时，在 Perfetto 中会表现为 system_server 进程中的某个系统服务线程长时间处于 BLOCKED 或 WAITING 状态。如果抓到了 Watchdog 超时事件，通常意味着设备即将重启。

[待补充：Trace 截图 — ANR 与 Watchdog 在 Perfetto 中的对比]

## ANR 信息的产出

ANR 触发后，系统会产出多种诊断信息，这些是我们分析 ANR 问题的核心素材。

### traces.txt（或 /data/anr/ 目录下的文件）

这是最核心的 ANR 诊断文件。系统通过 SIGQUIT 信号触发虚拟机 dump 出所有线程的堆栈。文件内容包括所有线程的完整堆栈（线程名、优先级、状态 RUNNABLE/BLOCKED/WAITING 等、tid）、线程持有的锁信息（如 `- locked <0x12345678>`）、CPU 使用统计。

在 Android 10 及以上版本中，ANR trace 文件不再统一写入 `/data/anr/traces.txt`，而是以 `anr_*` 命名存放在 `/data/anr/` 目录下。可以通过 `adb pull /data/anr/` 获取。

需要注意的是，**traces.txt 中的主线程堆栈不一定是 ANR 的根因**。正如前面提到的"刻舟求剑"问题，堆栈捕获时真正导致超时的代码可能已经执行完毕了。如果主线程堆栈显示 `Native (nativePollOnce)`，那说明 ANR 发生时主线程实际上处于空闲状态——真正的问题在更早的消息处理中。

### Event Log

ANR 发生时，系统会在 event log 中写入一条 `am_anr` 记录，包含进程名、PID、ANR 原因（如 `Input dispatching timed out`）等信息：

```
04-02 10:30:15.123  1000  1234  5678 I am_anr: [0,com.example.app,12345,
ActivityManager,Input dispatching timed out (Waiting to send non-key event
because the touched window has not finished processing certain input events
that were delivered to it over 500.0ms ago)]
```

通过 `adb logcat -b events | grep am_anr` 可以过滤 ANR 事件。这条日志能快速确认是哪个进程、因为什么原因触发了 ANR。

### Dropbox

Dropbox 是 Android 系统的持久化日志存储机制，用于保存系统级错误信息。ANR 信息会被写入 Dropbox 中的 `system_app_anr` 标签。与 traces.txt 不同，Dropbox 中的信息是持久化的，即使设备重启也不会丢失。

通过 `adb shell dumpsys dropbox --print` 可以查看所有 Dropbox 条目，包括历史 ANR 记录。这在分析偶发性 ANR 时特别有用——用户可能无法实时提供 traces.txt，但 Dropbox 中可能保留了之前 ANR 的记录。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]
[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AppNotResponding.java]

### 三种信息的互补关系

这三种信息在 ANR 分析中各有侧重：

- **traces.txt**：告诉我们 ANR 时刻所有线程"在哪里"（堆栈快照）
- **event log**：告诉我们"为什么触发 ANR"（超时类型和具体原因）
- **dropbox**：告诉我们"历史上有多少次 ANR"（持久化统计）

在 9.3 节（ANR 分析方法）中，我们会详细讨论如何综合使用这三种信息来定位 ANR 根因。

## 各版本 ANR 机制的微调与改进 [扩展]

ANR 机制自 Android 2.3 引入以来，基本框架没有大的变化，但每个版本都在细节上有所调整。

**Android 8.0（Oreo）**：引入了后台执行限制，后台 Service 的超时阈值从 20 秒调整为 200 秒。这个变化看似放松了限制，实际上是配合后台 Service 限制策略的一部分——系统更倾向于直接杀掉后台应用而不是弹 ANR 对话框。

**Android 10**：ANR trace 文件从单一的 `traces.txt` 改为按时间和进程分别存储在 `/data/anr/` 目录下。这个改进解决了多个 ANR 相互覆盖的问题——之前如果一个 App 连续触发多次 ANR，后面的 traces 会覆盖前面的，导致丢失重要的诊断信息。

**Android 12**：引入了 ANR 延迟报告机制。当后台 ANR 导致应用被杀时，系统会在应用下次启动时通知它，让开发者有机会收集崩溃报告。

**Android 14**：将 ANR 处理逻辑从 AMS 中解耦到独立的 `AnrHelper` 和 `AppNotResponding` 类中。这个重构的主要目的是提高 ANR 处理的可靠性——之前 ANR 处理代码散布在 AMS 的各个角落，容易与正常的 AMS 业务逻辑相互干扰。

**Android 16**：引入了系统触发式 ProfilingManager 追踪。当 ANR 发生时，系统可以自动捕获 ANR 时刻的 Perfetto trace，提供比传统 traces.txt 更丰富的信息。这个改进有望解决 traces.txt "刻舟求剑"的问题——系统触发式 trace 可以捕获 ANR 发生前一段时间的主线程行为。

[已验证: AOSP android-14.0.0_r1, AnrHelper/AppNotResponding 类在 Android 14 引入]
[已验证: Android 16 ProfilingManager ANR 触发, intake/research-feeds/2026-04-01-12-android16-17-profilingmanager-system-triggered.md]
[待验证: Android 8.0 后台 Service 200 秒超时的具体 commit]

## ANR 在 Google Play Console 中的统计与影响 [扩展]

Google Play Console 将 ANR 率作为应用核心性能指标（Android Vitals）的一部分进行监控。当用户的设备上发生 ANR 时，Play Services 会匿名上报 ANR 信息到 Play Console。

Google 对 ANR 率的阈值定义是：

- **ANR 率 > 0.38%**：应用的表现被标记为"差"（Bad），会在 Play Store 的应用详情页中被标注
- **ANR 率 > 0.10%**：应用的表现被标记为"需要改进"（Needs improvement）

这意味着如果你的应用每天有 10000 个活跃用户，只要每天有超过 38 个用户遇到 ANR，Google 就会认为你的应用质量有问题。在 Google Play 的搜索和推荐算法中，ANR 率高的应用会被降权，直接影响应用的曝光和下载量。

Play Console 中可以看到的 ANR 信息包括：按设备和 Android 版本分组的 ANR 分布、ANR 触发时的堆栈信息（来自 traces.txt）、ANR 趋势图（按日/周/月）。

这些统计数据可以帮助开发者快速定位 ANR 在哪些设备或系统版本上高发，但根因分析仍然需要获取完整的 traces.txt 和 event log。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

## [自动发现] ANR trace 堆栈的"替罪羊"现象

这个知识点虽然在 9.3（ANR 分析方法）中会更深入讨论，但在理解 ANR 设计思想时就值得建立正确的认知：**ANR trace 中主线程的堆栈，往往不是导致 ANR 的真正原因。**

这个现象的根本原因在于 ANR 机制的时序设计：超时检测发生在 system_server 中，而堆栈 dump 发生在超时检测之后。从"真正导致超时的代码开始执行"到"堆栈被 dump 下来"，中间经历了至少三个阶段：

1. 超时计时器到期 → system_server 检测到超时
2. system_server 的 AnrHelper 开始处理 → 创建 AppNotResponding 对象
3. 向目标进程发送 SIGQUIT → 目标进程 dump 堆栈

在这整个过程中，应用的主线程并没有停止工作。真正导致超时的"长耗时消息"很可能已经执行完毕，主线程已经开始处理下一个消息，甚至进入了空闲状态（`nativePollOnce`）。

钉钉团队在分析一个 ANR 问题时发现：BugReport 中的 traces.txt 显示主线程在处理传感器事件，而实际上真正导致 ANR 的是硬件渲染阶段的锁等待（耗时 68 秒）。传感器事件处理只用了 12 毫秒，但因为发生在超时检测之后，成了 traces.txt 中的"替罪羊"。

这个认知对于 ANR 分析方法的影响是深远的——它意味着我们不能简单地"看 traces.txt 堆栈就能定位 ANR"，而需要更系统的方法论。这正是 9.3 节要讨论的核心主题。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md]
[自动发现]

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/services/core/java/com/android/server/am/AppNotResponding.java`（Android 14+）
  - `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java`（Android 14+）
  - `frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java`
  - `frameworks/base/services/core/java/com/android/server/Watchdog.java`
  - `frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java`
  - `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- 官方文档：
  - [Android Vitals — ANR](https://developer.android.com/topic/performance/vitals/anr)
  - [Keep your app responsive](https://developer.android.com/training/articles/perf-anr)
- 素材来源：
  - [钉钉 ANR 治理最佳实践 | 定位 ANR 不再雾里看花](https://mp.weixin.qq.com/s?__biz=Mzg4MjE5OTI4Mw==&mid=2247498818)
  - Android 16/17 ProfilingManager 系统触发式追踪（intake/research-feeds/2026-04-01-12-android16-17-profilingmanager-system-triggered.md）
