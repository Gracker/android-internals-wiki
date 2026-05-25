---
title: "ANR 设计思想"
chapter: "9.1"
section: "9.1"
drafted_date: "2026-04-02"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-26"
last_verified_against: "AOSP android-11.0.0_r1 / android-13.0.0_r1 / android-14.0.0_r1, Android Vitals ANR docs"
reviewed_date: 2026-05-04
reviewed_by: openclaw-task6
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/Watchdog.java"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
tags: [anr, watchdog, traces, dropbox, activitymanagerservice, input-dispatcher, anrhelper, sigquit]
related_chapters: ["9.2", "9.3", "1.5", "7.1", "8.1", "15.3", "15.5"]
review_notes: "2026-05-01 task6 re-review (revisiting→reviewed): pass-light-edit. L1/L2 clean. No banned words, no AI fillers, format consistent. 2 pending queue entries block auto-promotion."

last_task2b_at: "2026-04-26T15:45:22+08:00"
task2b_fixed_at: "2026-04-26T15:45:22+08:00"
rework_by: openclaw-task2b
rework_type: "review回炉修复（Task9 问题单）"
repaired_date: "2026-04-26"
repaired_by: "openclaw-task2b"
auto_finalized_by: openclaw-task6
auto_finalized_date: "2026-05-02"
status: "ready-for-review"
pipeline_stage: "task2b_pending"
task9_result: "needs-rework"
task9_state: "reviewed"
task2b_state: "pending"
task2b_result: "pending"
task9_reviewed_date: 2026-05-06
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-06T10:38:04+08:00"
task9_review_notes: "2026-05-04 task9 deep-review: needs-rework。P0 2 / P1 0 / P2 0；详见 logs/deep-review/2026-05-04-16-deep-review.md。；2026-05-06 Task9 10:24：pass-tech-review。P0/P1 0；P2 2 写入 suggestions（ANR 2.3 版本口径、Watchdog 60s/30s 半程检查）；Task6 已通过且 queue 无 pending，自动晋升 finalized。；2026-05-25 Task9 闲时抽检：needs-rework。P0 1（Dropbox tag 进程类别边界）；P2 1（Watchdog 60s/30s 半程检查口径）；详见 logs/deep-review/2026-05-25-12-audit.md。"
task6_state: reviewed
task6_result: pass-light-edit
last_task6_audit: "2026-05-23"
last_task9_audit: 2026-05-25
last_task9_audit_at: "2026-05-25T12:27:10+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-25-12-audit.md"
---

# ANR 设计思想

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ANR 的设计初衷：保护用户体验，防止 App 无响应
- 🔹 ANR 机制的核心流程：注册超时 → 主线程处理 → 超时触发 → 弹窗/杀进程
- 🔹 AMS 中 ANR 的核心代码路径：AnrHelper / ProcessErrorStateRecord
- 🔹 ANR 与 Watchdog 的区别
- 🔹 ANR 信息的产出：traces.txt、event log、dropbox

### 扩展（可选深入）

- 🔸 各版本 ANR 机制的微调与改进
- 🔸 ANR 在 Google Play Console 中的统计与影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 ANR 的设计思想

当用户点击屏幕后等了几秒钟，屏幕没有任何反应——没有动画，没有反馈，就像手机死了一样。这种体验会让用户焦虑，进而愤怒，最后卸载你的 App。Android 的设计者很早就意识到，一个无响应的应用会严重损害用户对整个系统的信任，而不仅仅是对单个 App 的不满。

ANR（Application Not Responding）机制就是 Android 对这个问题的系统性回答。它不是事后诊断工具，而是一道运行时的防线：在应用失去响应能力的瞬间介入，给用户选择权——继续等待，或者杀掉它。

如果把全书的主线连起来看，ANR 并不是“完全不同的一类问题”，而是广义流畅性里最极端的一层：`7.1` 讲的是用户把“卡顿、响应慢、ANR”统称为卡；`8.1` 讲的是系统还能在多大程度上及时反馈；到了 ANR，这条反馈链已经断到系统必须介入。所以 ANR 设计思想也是一篇“体验保护机制”章节，而不只是异常处理机制。

理解 ANR 的设计思想之所以重要，不仅因为它是 Android 性能优化的核心课题之一，更因为它直接决定了我们分析 ANR 问题时的思路。如果不了解系统"为什么这样设计"，拿到一份 traces.txt 时很容易陷入"看堆栈猜原因"的盲人摸象——ANR trace 的堆栈经常是"替罪羊"，真正导致超时的代码可能早已执行完毕。

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

ANR 机制可以拆成四个阶段：注册超时、主线程处理、超时触发、弹窗或杀进程。

### 第一阶段：注册超时

当某个需要应用响应的操作开始时，system_server 会在后台线程上设置延迟消息。以 BroadcastReceiver 为例，Android 13 及以下常用排查口径是前台广播 10 秒、后台广播 60 秒；Android 14+ 的 Modern Broadcast Queue 把广播超时拆成 soft timeout 和 hard timeout，官方诊断窗口扩展为前台 10-20 秒、后台 60-120 秒。

```java
// 概念流程（简化）
// frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java
// frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java
// @ AOSP android-14.0.0_r1

// Android 13 及以下的典型口径：分发广播时设置固定 timeout
scheduleBroadcastsDispatchAndCheckTimeout(r, BROADCAST_FG_TIMEOUT);

// Android 14+ Modern Broadcast Queue：先触发 soft timeout
// dispatchReceivers() 记录 lastCpuDelayTime 并发送 MSG_DELIVERY_TIMEOUT_SOFT
// deliveryTimeoutSoftLocked() 再按 app.getCpuDelayTime() 计算 hard timeout
```

广播发送出去的同时，计时器开始倒计时。如果应用在窗口内完成 `onReceive()` 并通过 `finishReceiver()` 通知 AMS，计时器会被取消。Android 14+ 追加 hard timeout 的目的，是把 CPU starvation 和冷启动阶段的等待纳入窗口，避免系统忙或进程刚拉起时过早判定 Broadcast ANR。

### 第二阶段：主线程处理

此时应用的主线程正在执行 `onReceive()`（或其他超时类型的对应方法）。如果主线程当前没有被其他任务阻塞，`onReceive()` 正常执行完毕，AMS 收到完成通知，取消超时消息，流程结束。

但如果主线程正在忙于其他事情——比如前面有一个耗时 3 秒的数据库写入操作正在执行——那么 `onReceive()` 就得排队等待。如果等待时间超过了超时阈值，计时器就会到期。

不同组件向 system_server 报告"操作已完成"的机制各不相同：

- **BroadcastReceiver**：`onReceive()` 执行完毕后，`ActivityThread.handleReceiver()` 在主线程上直接调用 `IActivityManager.finishReceiver()` 通知 AMS——这是主线程上的同步 Binder 调用，不是异步 Binder 线程调用
- **Service**：`onStartCommand()` 或 `onCreate()` 执行完毕后，`ActivityThread.handleServiceArgs()` 在主线程上通过 Binder 回调通知 AMS
- **Input 事件**：应用通过 `InputConsumer.finishInputEvent()` 告知 InputDispatcher 事件已消费
- **ContentProvider**：发布完成后通过 `IActivityManager.publishContentProviders()` 回调 AMS

BroadcastReceiver 和 Service 的完成通知都在主线程上发起，与组件的执行同属一个线程。主线程不需要额外等待 AMS 确认——AMS 的超时计时器在 system_server 的后台线程独立运行，Binder 调用发出即视为完成。

超时检测和应用执行是异步关系。超时计时器运行在 system_server 的后台线程上，它不会检查应用主线程"在做什么"，只检查"结果有没有回来"。如果超时检测同步调用应用，应用自身的问题可能连检测机制一起拖死。

### 第三阶段：超时触发

当延迟消息到期时，system_server 进入 ANR 处理流程。Android 11 起，这个入口由 `AnrHelper.appNotResponding()` 承接；更早版本会散在 `ActivityManagerService`、`BroadcastQueue` 或对应组件管理类中处理。Android 14 仍沿用 `AnrHelper`，并通过内部 `AnrRecord` 与 `AnrConsumerThread` 排队执行。

```java
// 概念流程（简化）
// frameworks/base/services/core/java/com/android/server/am/AnrHelper.java
// @ AOSP android-14.0.0_r1

void appNotResponding(ProcessRecord anrProcess, TimeoutRecord timeoutRecord) {
    // 1. 把一次 ANR 请求封装成 AnrRecord
    synchronized (mAnrRecords) {
        mAnrRecords.add(new AnrRecord(anrProcess, activityShortComponentName, aInfo,
                parentShortComponentName, parentProcess, aboveSystem, timeoutRecord,
                isContinuousAnr, firstPidDumpPromise));
    }
    // 2. 由独立的 AnrConsumerThread 顺序处理，避免阻塞 AMS 主线程
    startAnrConsumerIfNeeded();
}

private final class AnrRecord {
    void appNotResponding(boolean onlyDumpSelf) {
        // 真实的 dump、event log、dropbox、弹窗/杀进程决策在这里继续展开
        mApp.mErrorState.appNotResponding(mActivityShortComponentName, mAppInfo,
                mParentShortComponentName, mParentProcess, mAboveSystem,
                mTimeoutRecord, mAuxiliaryTaskExecutor, onlyDumpSelf,
                mIsContinuousAnr, mFirstPidFilePromise);
    }
}
```

[已验证: AOSP android-11.0.0_r1 / android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java, ProcessErrorStateRecord.java]

注意 `startAnrConsumerIfNeeded()`——ANR 处理被放到了单独的 `AnrConsumerThread` 中执行，目标是避免 ANR 处理逻辑阻塞 AMS 主线程。系统处理一个应用无响应事件时，AMS 仍要继续服务其他进程，ANR dump 不能把调度线程拖住。

**连续 ANR 抑制。** 当同一个 App 短时间内反复触发 ANR 时，系统不会对每一次都执行完整的 dump + 弹窗流程。`AnrHelper` 内部通过 `isContinuousAnr` 标记和 `firstPidDumpPromise` 机制，对连续 ANR 做合并处理：第一次 ANR 正常 dump 全量堆栈，后续连续 ANR 可能只 dump 自身进程（`onlyDumpSelf=true`）或跳过 dump 直接走杀进程逻辑。这个设计有两个目的：避免频繁 SIGQUIT 导致系统 I/O 飙升（dump 一个进程的堆栈可能耗时数百毫秒），以及防止 ANR 处理本身成为系统瓶颈。排查时要注意：如果 traces.txt 中只看到一个 ANR 记录但 event log 显示多次 `am_anr`，可能就是连续 ANR 被合并了。

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

**ContentProvider ANR**：由 `ContentProviderHelper`（Android 14+）检测。ContentProvider 发布超时为 10 秒，常量是 `ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`（`frameworks/base/core/java/android/content/ContentResolver.java`），值为 `10 * 1000 * Build.HW_TIMEOUT_MULTIPLIER`；AMS 侧通过 `ActivityManagerService.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG` 消息编号触发超时回调。与 Service/Activity ANR 一样是系统级强制约束。`getProviderMimeType()` 调用有独立的 1 秒超时（API 31+，可通过 `getProviderMimeTypeAsync()` 异步处理），但这个 1 秒超时仅适用于 MIME 类型查询，不是通用的 ContentProvider ANR 阈值。

[已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/content/ContentResolver.java, CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS = 10 * 1000 * Build.HW_TIMEOUT_MULTIPLIER; frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java, CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG]


**startForeground() 宽限期**：这条规则约束的是 `Context.startForegroundService()` 之后多久必须调用 `Service.startForeground()`。版本边界要分开记：Android 8.0 是 5 秒；Android 9-12 是 10 秒；Android 13/14/15 的默认值迁到 `ActivityManagerConstants.DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS = 30 * 1000`，运行时字段是 `mServiceStartForegroundTimeoutMs`，设备也可通过 DeviceConfig 覆盖。Android 12 的主要变化是超时后常见 `ForegroundServiceDidNotStartInTimeException`；5 秒只对应 Android 8.0 的初始宽限期。

[已验证: AOSP android-8.0.0_r1 / android-9.0.0_r1 / android-12.0.0_r1 / android-13.0.0_r1 / android-14.0.0_r1, ActiveServices.java 与 ActivityManagerConstants.java]

**InputConnection / IME 输入相关无响应**：不要把它写成 `InputMethodManagerService#onInputEvent` 的 5 秒 timeout。AOSP android-14.0.0_r1 的 `InputMethodManagerService` 中没有这个判定点。IME 和 `InputConnection` 是输入法交互路径的一部分；如果表现为输入事件长期没有完成，最终仍要回到 `InputDispatcher` 的 dispatching timeout、waitQueue 和 `AnrTracker` 机制，由 `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` 处理。排查这类问题时，把 IME Binder 调用、目标应用主线程和 InputDispatcher 超时放在同一条时间线上看。

[已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp；InputMethodManagerService.java 未见 `onInputEvent` timeout 判定点]

### 核心：AnrHelper 与 ProcessErrorStateRecord

Android 11 起，`AnrHelper` 成为应用 ANR 请求的排队入口。它把一次 ANR 封装成内部 `AnrRecord`，再交给 `AnrConsumerThread` 串行处理。负责收集 trace、写 event log / dropbox、决定弹窗或杀进程的路径，在 `ProcessErrorStateRecord.appNotResponding()` 里继续展开。

```java
// frameworks/base/services/core/java/com/android/server/am/AnrHelper.java
// @ AOSP android-14.0.0_r1
// 节选后保留核心路径

class AnrHelper {
    private final ArrayList<AnrRecord> mAnrRecords = new ArrayList<>();

    void appNotResponding(ProcessRecord anrProcess, TimeoutRecord timeoutRecord) {
        synchronized (mAnrRecords) {
            mAnrRecords.add(new AnrRecord(anrProcess, activityShortComponentName, aInfo,
                    parentShortComponentName, parentProcess, aboveSystem, timeoutRecord,
                    isContinuousAnr, firstPidDumpPromise));
        }
        startAnrConsumerIfNeeded();
    }

    private final class AnrConsumerThread extends Thread {
        public void run() {
            AnrRecord r;
            while ((r = next()) != null) {
                r.appNotResponding(onlyDumpSelf);
            }
        }
    }

    private final class AnrRecord {
        void appNotResponding(boolean onlyDumpSelf) {
            mApp.mErrorState.appNotResponding(mActivityShortComponentName, mAppInfo,
                    mParentShortComponentName, mParentProcess, mAboveSystem,
                    mTimeoutRecord, mAuxiliaryTaskExecutor, onlyDumpSelf,
                    mIsContinuousAnr, mFirstPidFilePromise);
        }
    }
}
```

`mApp.mErrorState` 对应 `ProcessErrorStateRecord`。这条调用会进入 trace 收集、CPU 信息采样、event log、dropbox 和 UI 决策。文章里讨论“ANR 处理核心”时，应把 `AnrHelper` 理解成排队和线程隔离层，把 `ProcessErrorStateRecord` 理解成一次 ANR 的实际处理层。

[已验证: AOSP android-14.0.0_r1, `AnrHelper.java`, `ProcessErrorStateRecord.java`]

这段代码揭示了几个关键细节：

**堆栈收集使用 SIGQUIT 信号。** system_server 向目标进程发送 Signal 3（SIGQUIT），触发虚拟机的堆栈 dump。这也是为什么 ANR traces 文件中会包含所有线程的堆栈——因为 SIGQUIT 的处理函数会遍历虚拟机中的所有线程。

**traces 的堆栈有滞后性。** 钉钉团队在 ANR 治理实践中将这个问题形象地描述为"刻舟求剑"：从超时检测到发送 SIGQUIT 再到堆栈 dump 完成，中间经历了一系列异步操作。等到堆栈被捕获时，主线程上导致超时的长耗时任务可能已经执行完毕，当前正在执行的是另一个完全无关的任务。我们在 9.3 节（ANR 分析方法）中会详细讨论如何应对这个挑战。

**System Server 会向多个进程发送 SIGQUIT。** 不仅仅是对发生 ANR 的进程，系统可能会同时请求关联进程的堆栈信息。这意味着一个 App 收到 SIGQUIT 并不代表自己发生了 ANR，也可能是另一个 App 触发的。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md]

## ANR 与 Watchdog 的区别

不少开发者容易混淆 ANR 和 Watchdog 这两个机制，因为它们都涉及"超时检测"。但它们的设计目标、作用范围和处理方式完全不同，理解这个区别对性能分析非常重要。

### 作用范围不同

ANR 监控的是**应用进程**中的组件——Activity、Service、BroadcastReceiver、ContentProvider。它关心的是"某个 App 是否及时响应了系统请求"。

Watchdog 监控的是 **system_server 自身**中的核心系统服务——ActivityManagerService、WindowManagerService、PackageManagerService 等。它关心的是"系统服务是否正常运行"。

简单来说：ANR 是系统在"监视"应用，Watchdog 是系统在"监视"自己。

### 检测机制不同

ANR 采用"注册超时 → 完成取消"的模式：发起一个操作的同时设置超时计时器，操作完成后取消计时器。

Watchdog 采用"定期巡检"模式：它运行在 system_server 中的一个独立线程上，每隔一定时间（默认 60 秒）向所有注册的系统服务线程发送一个心跳检查。如果某个服务线程在规定时间内没有响应心跳，Watchdog 就认为它出了问题。

```java
// frameworks/base/services/core/java/com/android/server/Watchdog.java
// @ AOSP android-14.0.0_r1
// 概念级简化

public class Watchdog {
    // 每个 HandlerChecker 监控一个 Looper 线程
    final ArrayList<HandlerChecker> mHandlerCheckers = new ArrayList<>();
    
    void run() {
        while (true) {
            // 向所有注册的线程发送心跳
            for (HandlerChecker hc : mHandlerCheckers) {
                hc.scheduleCheckLocked();
            }
            // 等待所有线程完成检查
            wait(WAIT_INTERVAL);
            
            // 检查是否有超时的
            blockedCheckers = getBlockedCheckersLocked();
            if (blockedCheckers.size() > 0) {
                // 系统挂了！dump 堆栈 + 杀 system_server
                dumpStackTraces();
                killSystemServer();
            }
        }
    }
}
```

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/Watchdog.java]

### 后果不同

ANR 触发后，用户看到的是一个对话框——可以选择"等待"或"关闭"。App 进程可能被杀，但 system_server 不受影响，其他应用正常运行。

Watchdog 触发后，意味着 system_server 本身出了问题（通常是死锁）。此时整个设备基本上已经无法正常使用了——系统会杀掉 system_server 进程，init 进程会重新启动它，效果等同于一次"软重启"。所有正在运行的应用都会被杀掉。

### 在 Perfetto 中的表现不同

在 Perfetto Trace 中，ANR 事件通常表现为：
- 应用主线程上出现一段长时间的非空闲执行块（RUNNABLE 或 BLOCKED）
- system_server 进程中会出现 `AnrHelper` 相关的活动
- Input ANR 可以在 InputDispatcher 的 track 中看到 "Application Not Responding" 标记

Watchdog 触发时，在 Perfetto 中会表现为：
- system_server 进程中的某个系统服务线程长时间处于 BLOCKED 或 WAITING 状态
- 如果抓到了 Watchdog 超时事件，通常意味着设备即将重启

[待补充：Trace 截图 — ANR 与 Watchdog 在 Perfetto 中的对比]

## ANR 信息的产出

ANR 触发后，系统会产出多种诊断信息，这些是我们分析 ANR 问题的核心素材。

### traces.txt（或 /data/anr/ 目录下的文件）

这是最核心的 ANR 诊断文件。系统通过 SIGQUIT 信号触发虚拟机 dump 出所有线程的堆栈。文件内容包括：

- **所有线程的完整堆栈**：包括线程名、优先级、状态（RUNNABLE / BLOCKED / WAITING 等）、tid
- **线程持有的锁信息**：如 `- locked <0x12345678>`，标明哪个线程持有哪些锁
- **CPU 使用统计**：ANR 发生前一段时间的 CPU 负载信息

在 Android 10 及以上版本中，ANR trace 文件不再统一写入 `/data/anr/traces.txt`，而是以 `anr_*` 命名存放在 `/data/anr/` 目录下。Android 14 起访问 `/data/anr/` 需要 root 权限，开发者获取原始 trace 的标准路径有两条：执行 **`adb bugreport`** 从完整报告里提取，或在应用内通过 **`ActivityManager.getHistoricalProcessExitReasons()`** 获取 `ApplicationExitInfo` 列表，再调用 **`ApplicationExitInfo.getTraceInputStream()`**（API 30+，随 `ApplicationExitInfo` 在 Android 11 引入）程序化读取 ANR 堆栈。Android 14 起 `/data/anr/` 目录需要 root 权限，非 root 设备只能通过 `ApplicationExitInfo` 或 `adb bugreport` 获取。

**traces.txt 中的主线程堆栈不一定是 ANR 的根因**。正如前面提到的"刻舟求剑"问题，堆栈捕获时导致超时的代码可能已经执行完毕。如果主线程堆栈显示 `Native (nativePollOnce)`，那说明 ANR 发生时主线程处于空闲状态——问题出在更早的消息处理中。

### Event Log

ANR 发生时，系统会在 event log 中写入一条记录，包含进程名、PID、ANR 原因（如 `Input dispatching timed out`）等信息：

```
// event log 示例
04-02 10:30:15.123  1000  1234  5678 I am_anr: [0,com.example.app,12345,ActivityManager,Input dispatching timed out (Waiting to send non-key event because the touched window has not finished processing certain input events that were delivered to it over 500.0ms ago)]
```

通过 `adb logcat -b events | grep am_anr` 可以过滤 ANR 事件。这条日志能快速确认是哪个进程、因为什么原因触发了 ANR。

### Dropbox

Dropbox 是 Android 系统的持久化日志存储机制，用于保存系统级错误信息。ANR 信息会被写入 Dropbox 中的 `system_app_anr` 标签。与 traces.txt 不同，Dropbox 中的信息是持久化的，即使设备重启也不会丢失。

通过 `adb shell dumpsys dropbox --print` 可以查看所有 Dropbox 条目，包括历史 ANR 记录。这在分析偶发性 ANR 时特别有用——用户可能无法实时提供 traces.txt，但 Dropbox 中可能保留了之前 ANR 的记录。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]
[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java]

### 三种信息的互补关系

这三种信息在 ANR 分析中各有侧重：

- **traces.txt**：告诉我们 ANR 时刻所有线程"在哪里"（堆栈快照）
- **event log**：告诉我们"为什么触发 ANR"（超时类型和具体原因）
- **dropbox**：告诉我们"历史上有多少次 ANR"（持久化统计）

在 9.3 节（ANR 分析方法）中，我们会详细讨论如何综合使用这三种信息来定位 ANR 根因。

## 各版本 ANR 机制的微调与改进 [扩展]

ANR 机制自 Android 2.3 引入以来，基本框架没有大的变化，但几乎每个大版本都在细节上有所调整。我们梳理其中影响较大的几次变化。

Android 8.0 引入了后台执行限制。后台 Service 的超时阈值一直是前台超时的 10 倍（`DEFAULT_SERVICE_BACKGROUND_TIMEOUT = DEFAULT_SERVICE_TIMEOUT * 10`），对应前台 20 秒、后台 200 秒——这不是 Android 8.0 才引入的值，早期 AOSP 的 `ActivityManagerConstants` 里就已经这样定义。Android 8.0 的主要变化是后台执行限制本身：系统更倾向于直接杀掉后台应用而不是等它触发 ANR。200 秒的后台超时更多是一个保底兜底值，绝大多数后台 Service 会在远早于 200 秒时被后台限制策略回收。

Android 10 解决了一个长期困扰开发者的诊断难题：ANR trace 文件从单一的 `traces.txt` 改为按时间和进程分别存储在 `/data/anr/` 目录下。在此之前，如果一个 App 连续触发多次 ANR，后面的 traces 会覆盖前面的，导致丢失重要的诊断信息。按进程和时间分开存储后，每次 ANR 都有独立的 trace 文件，历史信息不再被覆盖。

Android 12 收紧了前台服务启动失败后的异常表现。`startForegroundService()` 后没有及时调用 `startForeground()` 时，常见结果是 `ForegroundServiceDidNotStartInTimeException`；AOSP 对应宽限期仍是 10 秒。Android 13 起，这个默认值迁到 `ActivityManagerConstants.DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS = 30 * 1000`。

Android 13 对 ANR trace 的存储做了改进：trace 文件改为按进程独立存储，并且增加了 trace 采集的可靠性。此前，在多个进程同时触发 ANR 时，trace 文件的写入可能互相干扰导致内容丢失。Android 13 还改进了后台执行限制策略，进一步收紧了后台 Service 的行为约束，间接减少了后台 Service ANR 的场景。

Android 14 的 ANR 变化主要落在触发条件和诊断口径上：BroadcastReceiver 的官方诊断窗口更新为前台 10-20 秒、后台 60-120 秒，并引入 `BroadcastQueueModernImpl` 这条现代广播分发实现；targetSdk 34+ 的 `JobService.onStartJob()` / `onStopJob()` 主线程超时也会显式上报 ANR。`AnrHelper` 从 Android 11 起已经承担排队和线程隔离职责。

Android 16 引入的系统触发式 ProfilingManager 追踪可能是迄今最有价值的 ANR 诊断改进。当 ANR 发生时，系统可以自动捕获 ANR 时刻的 Perfetto trace，提供比传统 traces.txt 远为丰富的信息。这个改进有望解决 traces.txt "刻舟求剑"的问题——系统触发式 trace 可以捕获 ANR 发生前一段时间的主线程完整行为，而不仅仅是一个堆栈快照。

[已验证: AOSP android-11.0.0_r1 / android-14.0.0_r1, AnrHelper.java；AOSP android-14.0.0_r1, BroadcastQueueModernImpl.java, ActiveServices.java]
[已验证: Android 16 ProfilingManager ANR 触发, intake/research-feeds/2026-04-01-12-android16-17-profilingmanager-system-triggered.md]
[待验证: Android 8.0 后台 Service 200 秒超时的具体 commit]

**Android 15**（[待验证]）：ANR 行为可能存在以下变更——更严格的 `startForeground()` 执行约束、前台 Service 类型声明的强制化。这些变更影响的是 ANR 的触发条件，而非 ANR 机制本身的架构。如有变更，将在后续 review 中更新。

**Android 17**（[待验证]）：基于 Android 16 ProfilingManager 系统触发式追踪的进一步完善，可能引入更多 ANR 诊断信息的自动采集能力。ANR 机制的核心架构（超时检测 → SIGQUIT dump → 弹窗/杀进程）预计不会有根本性变化。具体变更将在 AOSP android-17 正式发布后验证。

[待验证: Android 15/17 ANR 机制的具体变更，需在 AOSP 正式版发布后对照确认]

## ANR 在 Google Play Console 中的统计与影响 [扩展]

Google Play Console 将 ANR 率作为应用核心性能指标（Android Vitals）的一部分进行监控。当用户的设备上发生 ANR 时，Play Services 会匿名上报 ANR 信息到 Play Console。

当前 Android Vitals 的核心 ANR 指标采用“用户感知 ANR 率”（user-perceived ANR rate）口径。全局坏行为阈值是 **0.47%**：如果应用跨设备总体超过这条线，可能影响 Google Play 的曝光；Play Console 还会按设备型号检查局部高发问题。

按 10000 个日活用户估算，0.47% 对应每天约 47 个用户遇到用户感知 ANR。这个数字只是官方质量红线，不适合作为内部目标；线上治理通常要把内部告警线设得更低，并按设备、系统版本和场景拆开看。

Play Console 提供的 ANR 信息包括：
- 按设备和 Android 版本分组的 ANR 分布
- ANR 触发时的堆栈信息（来自 traces.txt）
- ANR 趋势图（按日/周/月）

这些统计数据可以帮助开发者快速定位 ANR 在哪些设备或系统版本上高发，但根因分析仍然需要获取完整的 traces.txt 和 event log。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

## [自动发现] ANR trace 堆栈的"替罪羊"现象

我们在前面分析 `AnrHelper` 与 `ProcessErrorStateRecord` 时已经提到过堆栈捕获的滞后性。这里把这个问题的完整机制展开，因为它直接决定了我们后续分析 ANR 的方法论。

**ANR trace 中主线程的堆栈，往往不是导致 ANR 的直接原因。** 根源在于 ANR 机制的时序设计：超时检测发生在 system_server 中，而堆栈 dump 发生在超时检测之后。从"导致超时的代码开始执行"到"堆栈被 dump 下来"，中间经历了至少三个阶段：

1. 超时计时器到期 → system_server 检测到超时
2. system_server 的 AnrHelper 开始处理 → 创建 `AnrRecord` 并进入 `ProcessErrorStateRecord`
3. 向目标进程发送 SIGQUIT → 目标进程 dump 堆栈

在这整个过程中，应用的主线程并没有停止工作。导致超时的"长耗时消息"很可能已经执行完毕，主线程已经开始处理下一个消息，甚至进入了空闲状态（`nativePollOnce`）。

钉钉团队在分析一个 ANR 问题时发现：BugReport 中的 traces.txt 显示主线程在处理传感器事件，导致 ANR 的实际原因是硬件渲染阶段的锁等待（耗时 68 秒）。传感器事件处理只用了 12 毫秒，但因为发生在超时检测之后，成了 traces.txt 中的"替罪羊"。

这个认知直接决定了我们分析 ANR 的方式——不能简单地把 traces.txt 堆栈当作根因，而需要结合时间线和多种信息源交叉验证。这正是 9.3 节要讨论的核心主题。

[来源: Personal-Knowlodge/source/2026-03-07_wechat_钉钉_ANR_治理最佳实践_定位_ANR_不再雾里看花.md]
[自动发现]

## 常见问题与误区

### 误区一："主线程堆栈就是 ANR 的根因"

这是最常见的误区。拿到一份 traces.txt，看到主线程堆栈在某个方法上，就认定这个方法是 ANR 的罪魁祸首。但 traces.txt 中的堆栈是超时检测之后才 dump 的，导致超时的代码很可能已经执行完毕。我们在前面的"替罪羊"现象中已经详细解释了这个时序问题。正确的做法是：traces.txt 是线索之一，但必须结合 event log 中的时间戳、systrace/perfetto 中的主线程时间线来交叉验证。

### 误区二："ANR = CPU 高负载"

ANR 的触发条件是"主线程在超时时间内没有响应"，而不是"CPU 占用率高"。一个 CPU 占用率极低的线程，如果被锁阻塞（BLOCKED 状态），同样会触发 ANR。反过来，CPU 占用率高但及时返回了结果的代码，不会触发 ANR。ANR 的本质是"响应超时"，不是"资源消耗过大"。

### 误区三："后台 Service 超时 200 秒，所以不用担心"

200 秒的后台 Service 超时只是 ANR 触发的阈值，不意味着系统会给后台 Service 200 秒的执行时间。Android 8.0 之后，系统对后台 Service 有严格的限制策略，大多数后台 Service 会在远早于 200 秒时被系统回收。如果后台 Service 触发了 200 秒超时，说明它已经违反了后台执行限制，即使不触发 ANR 也会被系统杀掉。

### 误区四："ANR 率低就不需要关注"

Google Play Console 的核心 ANR 坏行为阈值（用户感知 ANR 率 0.47%）是全局统计值。对于一个日活 100 万的应用，0.47% 意味着每天约 4700 个用户遇到用户感知 ANR。而且，ANR 率是按会话计算的，一个用户可能在同一天遇到多次 ANR，但只计算一次。所以即使 ANR 率在"可接受"范围内，频繁 ANR 的用户很可能已经流失了。

## 参考资料

### Kotlin 协程 ANR 治理与 Dispatchers 性能开销
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-11-kotlin-coroutine-dispatchers-anr-analysis.md
- 类型：DeepResearch 调研结果
- 摘要：源码级分析 CoroutineScheduler 线程池架构：Dispatchers.IO 与 Default 共享同一 CoroutineScheduler 实例，withContext(Dispatchers.IO) 在 Default 线程上不发生线程切换只改变 TaskContext 标记；WorkQueue 半 FIFO 调度的饥饿风险；HandlerContext 关闭后任务降级到 Dispatchers.IO 的 ANR 传播链；协程 ANR 本质是 withContext(Dispatchers.Main) 仍在主线程执行。
- 注入时间：2026-05-12
- 价值：揭示了协程 ANR 的核心陷阱——Dispatchers.IO 不等于切换线程，以及 Handler 关闭后的降级传播链，对 ANR 治理实践有直接的避坑指导价值


- AOSP 源码路径：
  - `frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java`
  - `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java`（Android 11+）
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
