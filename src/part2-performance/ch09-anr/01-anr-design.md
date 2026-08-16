---
title: "ANR 设计思想"
chapter: "9.1"
section: "9.1"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-20"
last_verified_against: "AOSP android-11.0.0_r1 / android-14.0.0_r1 / android-15.0.0_r1 / android-17.0.0_r1, packages/modules/Profiling android-16.0.0_r1 / android-17.0.0_r1, Android Vitals ANR docs"
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
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
tags: [anr, watchdog, traces, dropbox, activitymanagerservice, input-dispatcher, anrhelper, sigquit]
related_chapters: ["9.2", "9.3", "1.5", "7.1", "8.1", "15.3", "15.5"]
status: "finalized"
pipeline_stage: "ready-to-publish"
task9_state: "reviewed"
task2b_state: "fixed"
task6_state: "reviewed"
---
# 9.1 ANR 设计思想

## 从“用户等了多久”理解 ANR

用户不了解应用内部正在做数据库迁移、Binder 调用还是图片解码。他能感受到的只是触摸后没有反馈、页面停住，或刚打开的界面迟迟不能接收按键。Android 需要为这类关键响应设置期限，并在超时后留下足够证据供开发者追查。

ANR（Application Not Responding，应用无响应）机制因此负责三项工作：

1. 给输入、广播、服务等关键工作设定响应期限。
2. 期限耗尽时，从系统进程侧记录原因并采集现场。
3. 依据进程重要性、可见性和系统策略，终止进程或安排系统无响应界面。

这里有两个容易混淆的边界。

- ANR 约束的是系统正在等待完成的工作。应用中的某项操作即使耗时很长，只要没有超过任何受监控期限，系统就不会仅凭时长生成 ANR。
- 主线程阻塞是常见原因，但检测对象不局限于主线程。广播可以交给指定 `Handler`，服务问题可能牵涉 Binder 线程、锁持有者或远端进程；系统判定依据是对应工作没有按协议按时完成。

分析 ANR 时，应先问“哪个系统期限耗尽，系统在等什么完成信号”，再问“哪条线程阻断了完成条件”。若直接从主线程栈猜业务根因，很容易把采样瞬间的现场误当成此前几秒的完整过程。

## Android 17 的整体分层

以 `android-17.0.0_r1` 为锚点，应用 ANR 可拆成四层。

| 层次 | 代表代码 | 职责 |
|---|---|---|
| 检测层 | `InputDispatcher`、`BroadcastQueueImpl`、`ActiveServices`、`ContentProviderHelper` | 建立期限，接收完成信号，发现超时 |
| 语义层 | `TimeoutRecord` | 用统一对象保存超时类型、原因、触发时刻和采集延迟状态 |
| 编排层 | `AnrHelper` | 去重、尽早抓取目标进程栈，再将完整报告排队处理 |
| 记录与处置层 | `ProcessErrorStateRecord` | 写日志和统计、生成 trace、提交 DropBox（系统诊断条目仓库），再进入杀进程或界面策略 |

这种分层解决了两个系统级问题。检测器最了解自己等待的协议，因此能写出“广播未完成”或“输入窗口未响应”等具体原因；耗时较高的堆栈、CPU 和 DropBox 采集则放在统一路径，避免每种组件重复实现。

### 检测器关注完成协议

不同检测器等待的完成信号不同：

| 场景 | 系统开始等待 | 系统认定完成 |
|---|---|---|
| 输入派发 | 事件进入目标连接并等待确认，或系统等待焦点窗口出现 | 目标连接确认事件已处理，或焦点条件满足 |
| 广播接收 | 有序或受跟踪的 receiver 开始交付 | receiver 返回，或 `goAsync()` 得到的 `PendingResult` 调用 `finish()` |
| Service 执行 | 受监控的 Service 回调开始 | 应用通过 Framework 协议报告对应执行完成 |
| 前台服务启动 | `startForegroundService()` 建立前台化期限 | 服务按要求调用 `startForeground()` |
| ContentProvider | 系统侧的 provider 调用监控被触发 | provider 调用返回 |

输入派发的 AOSP 默认超时是 5 秒，设备还可能通过 `ro.hw_timeout_multiplier`（硬件超时倍数）和窗口级配置调整。广播、Service 等期限也会随前后台状态、目标 SDK 和组件类型变化，具体数值见 [9.2 ANR 类型与触发条件](02-anr-types.md)。若把所有 ANR 都概括为“主线程超过 5 秒”，就会掩盖不同检测器的触发条件。

### `TimeoutRecord` 统一表达超时

Android 17 的检测器会创建相应的 `TimeoutRecord`。下面的源码节选用于说明语义对象包含什么，省略了无关工厂方法：

```java
private TimeoutRecord(int kind, String reason, long endUptimeMillis,
        boolean endTakenBeforeLocks) {
    mKind = kind;
    mReason = reason;
    mEndUptimeMillis = endUptimeMillis;
    mEndTakenBeforeLocks = endTakenBeforeLocks;
    mLatencyTracker = new AnrLatencyTracker(kind, endUptimeMillis);
}

public static TimeoutRecord forInputDispatchWindowUnresponsive(String reason) {
    return endingNow(TimeoutKind.INPUT_DISPATCH_WINDOW_UNRESPONSIVE, reason);
}

public static TimeoutRecord forContentProvider(String reason) {
    return endingApproximatelyNow(TimeoutKind.CONTENT_PROVIDER, reason);
}
```

`mEndUptimeMillis` 记录检测器发现超时的系统运行时间；`mEndTakenBeforeLocks` 标明这个时间点是否在等待可能耗时的锁之前取得。即使后续 ANR 处理需要排队，这两个字段仍能区分“超时发生时间”和“报告开始处理时间”。Android 17 还会把内部类型映射为公开的 `AnrTypes`，供结构化退出记录和预警信息使用。

## 四阶段流程：注册、执行、超时、处置

“注册超时 → 应用处理 → 超时触发 → 弹窗或杀进程”可以概括主流程，但每一步都存在取消、重新核实或策略分支。

### 阶段一：注册超时

检测器在工作开始时设置期限。Android 17 的 `BroadcastQueueImpl`、`ActiveServices` 已使用 `AnrTimer`；输入路径由 native `InputDispatcher` 维护连接等待队列和 ANR 跟踪器。计时器会与待处理对象绑定，工作完成后，相应计时会被取消或丢弃。

注册动作通常包含以下信息：

- 负责完成工作的进程或窗口；
- 组件、Intent 或输入目标；
- 期限开始时间和时长；
- 到期时可写入报告的原因文本。

这也解释了应用自建的“主线程卡顿监控”为何不能替代系统 ANR 统计。应用监控可以观察 Looper 消息延迟，却不知道 `system_server` 正在等待哪一项协议完成，也无法复现系统对窗口、进程和用户可见性的归因策略。

### 阶段二：应用执行并报告完成

大部分 Android 组件回调在应用主线程运行，因此主线程 I/O、长计算、同步 Binder、锁竞争和死锁很容易拖过期限。这个阶段仍要检查参与完成条件的其他线程：

- 主线程可能正在等待工作线程释放锁；
- 同步 Binder 的耗时由服务端线程和调度状态决定；
- `BroadcastReceiver.goAsync()` 会让广播在回调返回后继续保持未完成状态，直到 `PendingResult.finish()` 被调用；
- 使用自定义 `Handler` 的 receiver 可能在另一条 Looper 线程执行；
- 系统负载或 CPU 调度饥饿会让处于 Runnable 状态的线程长时间得不到 CPU。

“回调方法已经返回”不一定表示系统协议已经完成。`goAsync()` 是典型例子；前台服务还要在期限内调用 `startForeground()`。排查时必须找到相应检测器真正等待的完成信号。

### 阶段三：期限耗尽

计时器到期后，检测器会再次核实目标是否仍处于等待状态。若工作已经完成、进程已经退出或对象已经被替换，旧超时就会被丢弃。确认仍然超时后，检测器创建 `TimeoutRecord`，再把目标进程交给 AMS（ActivityManagerService）。

输入路径还多一层责任归属判断。`InputDispatcher` 识别“没有焦点窗口”或“目标连接未确认事件”后，经 `InputManagerCallback` 进入 WMS（WindowManagerService）的 `AnrController`。`AnrController` 会根据 input token（输入连接标识）、窗口、Activity 和 PID 找到责任进程；若焦点请求来自其他窗口，也可能将超时归给对应窗口进程。确认目标后，系统调用 AMS 的 `inputDispatchingTimedOut()`，再进入 `AnrHelper`。

这段路由说明，日志中的责任进程由窗口和输入状态共同决定，不一定是用户当时看到的前台 Activity 所在进程。

### 阶段四：采集并执行策略

进入 AMS 后，系统会先采集容易随时间变化的诊断现场，再决定怎样处置。Android 17 的常见结果包括：

- 后台且不具备用户相关性的 silent ANR（不显示对话框的后台 ANR）：采集后直接杀进程；
- 可感知进程：记录 `NOT_RESPONDING` 状态并向系统 UI Handler 投递无响应界面；
- Window/Activity 控制器提前处理或要求终止；
- 调试、Instrumentation（测试框架控制）、关机或进程已死等状态下，跳过报告或改变处置。

因此，超时后不一定弹窗，也不一定立即杀进程。对话框只是处置分支之一；厂商系统、调试状态、后台 ANR 设置和当前用户状态都会影响用户看到什么。没有对话框，也不能证明没有发生 ANR。

## AMS 主路径：`AnrHelper`

`AnrHelper` 让多个检测器快速交接：先尽早保存最容易变化的目标进程堆栈，再排队生成成本较高的完整报告。

### 先去重

Android 17 会拒绝以下无效或重复请求：

- PID 为 0；
- 同一 PID 正在处理；
- 同一 PID 正在做早期临时 dump；
- 同一 PID 已在 ANR 队列中。

这一层避免同一进程同时生成多份高成本报告。因此，日志里“业务层连续检测到多次卡顿”和“系统完整处理了多次 ANR”是两种不同的计数口径。

### 尽早保存目标进程栈

完整 ANR 报告可能还要抓取 `system_server`、持久进程、原生守护进程和 CPU 状态。若等这些步骤完成后才抓目标应用，主线程现场可能早已变化。`AnrHelper` 因此先把目标 PID 的临时 dump（线程堆栈转储）提交给独立线程池，再将 ANR 记录放入报告队列。

下面的 Android 17 源码节选展示“先提交 early dump，再把记录入队”的顺序：

```java
Future<File> firstPidDumpPromise = mEarlyDumpExecutor.submit(() -> {
    File tracesFile = StackTracesDumpHelper.dumpStackTracesTempFile(
            incomingPid, timeoutRecord.mLatencyTracker);
    mTempDumpedPids.remove(incomingPid);
    return tracesFile;
});

mAnrRecords.add(new AnrRecord(
        anrProcess, activityShortComponentName, aInfo,
        parentShortComponentName, parentProcess, aboveSystem,
        timeoutRecord, isContinuousAnr, firstPidDumpPromise));
```

`Future<File>` 代表仍在执行或已经完成的异步文件任务，它会随 `AnrRecord` 进入消费线程。生成正式 trace 时，`StackTracesDumpHelper` 优先复制这份 early dump；若早期采集失败，再对目标 PID 重新采集。

### 队列拥塞时缩小采集范围

`AnrConsumer` 会逐条处理队列中的记录。Android 17 中，若报告排队已超过 10 秒，或系统启动还不足 10 分钟，`onlyDumpSelf` 会设为 `true`，系统只抓取被归因进程。这样可以避免大量并发 ANR 报告继续占用 CPU 和 I/O，进一步拖慢设备。

两次 ANR 若间隔不足 2 分钟，`AnrHelper` 会安排 Binder heavy-hitter（高频 Binder 调用方）自动采样，为报告补充调用热点线索。这个 2 分钟常量只控制采样调度；系统不会因此把两次 ANR 合成一条，也不会忽略后一次 ANR。

Android 17 在单条 ANR 处理结束后还可以发送 `ProfilingTrigger.TRIGGER_TYPE_ANR`。应用若事先注册了系统触发式 profiling（性能剖析），可能获得覆盖一段时间的额外产物；注册方式与数据边界见 [14.11 ProfilingManager](../../part3-tools/ch14-other-tools/11-profiling-manager.md)。这类产物是补充证据，不能替代 ANR trace。

## AMS 主路径：`ProcessErrorStateRecord`

`ProcessErrorStateRecord.appNotResponding()` 将已经确认的超时转成可诊断、可统计、可处置的系统事件。

### 进入报告前的状态防护

AMS 在下列条件下跳过普通报告：系统正在关机、进程已有 ANR、进程正在崩溃、进程已被 ActivityManager 杀死，或进程已经死亡。调试器附着时，也不会完全按照普通应用 ANR 路径处理。

通过检查后，系统在锁保护下把进程标记为 `notResponding`，阻止同一进程并发生成重复报告。随后写入 `am_anr` EventLog，并尽快记录 Perfetto/Stats 触发点，方便将不同诊断数据按时间关联。

### 收集可关联证据

Android 17 的报告路径会组合：

- 超时原因、组件和 PID；
- 目标进程及选定关联进程的 Java/native 线程栈；
- 当前 CPU 使用和负载；
- PSI（Pressure Stall Information，资源压力停顿信息）；
- 目标进程内存摘要与 fs-verity 信息；
- CriticalEventLog、EventLog、statsd 和 Perfetto 标记；
- DropBox 报告与 `ApplicationExitInfo` 可回捞的 trace 片段。

下面的源码节选用于确认三类产物都来自同一处理函数：

```java
EventLog.writeEvent(EventLogTags.AM_ANR, mApp.userId, pid,
        mApp.processName, mApp.info.flags, annotation);

File tracesFile = StackTracesDumpHelper.dumpStackTraces(
        firstPids, processCpuTracker, lastPids, nativePidsFuture,
        tracesFileException, firstPidEndOffset, annotation,
        criticalEventLog, extraHeaders, auxiliaryTaskExecutor,
        firstPidFilePromise, latencyTracker, timeoutRecord);

mService.addErrorToDropBox("anr", mApp, mApp.processName,
        activityShortComponentName, parentShortComponentName,
        parentPr, null, report.toString(), tracesFile, null,
        new Float(loadingProgress), incrementalMetrics, errorId,
        volatileDropboxEntriyStates);
```

EventLog 提供事件索引，trace 保存线程现场，DropBox 汇总更完整的上下文。代码里的 `"anr"` 是错误类型参数；AMS 会结合进程类别生成具体 DropBox tag（条目分类名），因此排查时不能假定所有设备都只使用固定的 `data_app_anr`。

### 决定杀进程或展示界面

证据采集完成后，`WindowProcessController` 和系统控制器先获得处理机会。普通路径继续检查 `isSilentAnr()`：若开发者选项没有开启“显示所有 ANR”，且进程与当前用户界面无关，系统会按后台 ANR 杀死它。`system_server`、正在展示 Activity 的进程、SystemUI，以及具有 top UI（顶层界面）或 overlay UI（覆盖层界面）的进程，会被视为用户相关进程并保留更完整的现场。

可展示路径会生成 `ProcessErrorStateInfo.NOT_RESPONDING`，并向 AMS UI Handler 发送 `SHOW_NOT_RESPONDING_UI_MSG`。在界面真正显示前，当前用户、系统控制器、延迟策略和设备定制仍可能改变结果。

## 应用 ANR 与 `system_server` Watchdog

应用 ANR 和 `system_server` Watchdog 都处理“长时间没有进展”，但保护对象和恢复方式差异很大。

| 维度 | 应用 ANR | `system_server` Watchdog |
|---|---|---|
| 保护对象 | 应用组件、输入窗口和应用进程 | `system_server` 的关键 Handler 与 Monitor |
| 检测者 | 输入、广播、服务、Provider 等子系统 | `Watchdog` 线程与 `HandlerChecker` |
| Android 17 默认期限 | 按场景配置；输入 AOSP 默认 5 秒 | 普通构建默认 60 秒，可由设置和硬件超时系数调整 |
| 中间信号 | Android 17 部分路径有 ANR warning/pre-ANR（正式超时前预警） | 期限的 1/4 进入 pre-watchdog；默认约 15 秒 |
| 主报告路径 | `AnrHelper` → `ProcessErrorStateRecord` | `Watchdog.run()` → `collectThreadDumps()` |
| 常见处置 | 后台杀进程或安排 ANR UI | 采集后杀掉 `system_server`，由系统重启；调试器和禁重启策略可阻止 |

Watchdog 会把检查任务投递到 `system_server` 的关键 Looper，并执行注册的 Monitor（关键锁或组件健康检查）。若检查任务迟迟不能完成，它会区分仍在等待、pre-watchdog 和 overdue（已经超过最终期限）状态。Android 17 的 `PRE_WATCHDOG_TIMEOUT_RATIO` 是 4，因此默认 60 秒期限下，pre-watchdog 约在 15 秒触发；pre-watchdog 采集有一小时冷却限制，但完整超时仍可能在约 60 秒触发。

Watchdog 报告会使用 `pre_watchdog` 或 `watchdog` DropBox tag，并生成 `system_server` 及关键原生进程的堆栈。完整超时后，若没有调试器、系统允许重启，且控制器没有要求继续等待，Watchdog 会调用 `Process.killProcess(Process.myPid())` 终止 `system_server`，随后由系统完成重启恢复。

应用 ANR 也可能由 `system_server` 卡顿间接引起。例如，应用主线程在同步 Binder 中等待 `system_server`，输入期限先耗尽，此时会先记录应用 ANR；若 `system_server` 的受监控线程也持续没有进展，Watchdog 才会独立触发。两个报告要按时间线一起分析，不能只因前一份报告归在应用进程名下，就认定是应用自身缺陷。

## 三类基础产物怎么配合

### EventLog：回答“何时、谁、因为什么”

Android 17 的 `am_anr` EventLog tag 编号为 30008，字段顺序是 user、PID、进程名、应用 flags 和 reason。reason 来自检测器构造的 `TimeoutRecord`，通常是判断 ANR 类型与等待对象最稳定的入口。

下面的两条命令分别从设备的 events 日志缓冲区和已导出的 bugreport 中查找 `am_anr` 索引：

```bash
adb shell logcat -b events -d -v threadtime | grep 'am_anr'
grep 'am_anr' bugreport.txt
```

events 缓冲区会循环覆盖旧记录，因此线上问题应尽早保存带时间戳的完整 bugreport 或平台侧记录。

### ANR trace：回答“采样时线程在做什么”

Android 17 的 `StackTracesDumpHelper` 会在 `/data/anr/` 创建名为 `anr_yyyy-MM-dd-HH-mm-ss-SSS` 的文件，权限 `0600` 表示只有文件所有者可读写。历史 bugreport 中仍会出现 `traces.txt` 这个名字，以下用“ANR trace”统称两种形式。

普通第三方应用不能直接遍历 `/data/anr`。开发阶段可以从 bugreport 获取系统收集的 ANR 段；Android 11（API 30）起，应用还能通过 `ActivityManager.getHistoricalProcessExitReasons()` 查询自己的历史退出记录，并用 `ApplicationExitInfo.getTraceInputStream()` 读取系统保留的 trace。由于 trace 存放在容量有限的全局循环缓冲区中，可能已被后续记录覆盖，因此该输入流允许返回 `null`。

下面的 Kotlin 片段查找当前应用最近一次带有 trace 的 ANR 退出记录，并读取文本内容：

```kotlin
val activityManager = getSystemService(ActivityManager::class.java)
val exits = activityManager.getHistoricalProcessExitReasons(
    packageName,
    0,
    20,
)

val latestAnr = exits.firstOrNull {
    it.reason == ApplicationExitInfo.REASON_ANR
}

latestAnr?.traceInputStream?.bufferedReader()?.use { reader ->
    val traceText = reader.readText()
    uploadAfterRedaction(traceText)
}
```

这个 API 只返回本应用有权访问的历史信息，内容范围小于完整 bugreport。生产环境上传前要限制大小、进行隐私审查并脱敏；trace 为 `null` 是允许出现的结果，不能当成采集逻辑异常。

Android 17（API 37）还为 `ApplicationExitInfo` 增加了 `getAnrInfo()`。返回的 `AnrInfo` 包含 ANR ID、`AnrTypes` 类型、系统等待时长和用户可感知标志。它只可能出现在 `REASON_ANR` 记录中；输入派发等没有 `AnrTimer.ExpiredTimer` 的路径仍可能拿不到该对象，因此兼容代码要同时判断系统版本和空值。

### DropBox：回答“系统汇总了哪些上下文”

`ProcessErrorStateRecord` 会把 ANR 摘要、资源压力、trace 文件和关联信息交给 `ActivityManagerService.addErrorToDropBox()`。最终 tag 与进程类别有关，常见形式包括 `data_app_anr`、`system_app_anr` 等；AOSP 与厂商构建可能存在差异。

下面的命令用于在具备相应调试权限的设备上先列出 DropBox 条目，再读取指定 tag 的内容：

```bash
adb shell dumpsys dropbox --file
adb shell dumpsys dropbox --print data_app_anr
```

先确认设备实际存在的条目和 tag，再读取目标内容，可以避免把示例中的 `data_app_anr` 当成所有 ANR 的固定名称。

### 三者按时间关联

一份可靠的基础证据包至少要对齐以下三类信息：

1. EventLog 的时间、PID、进程名和 reason；
2. trace 文件头中的 PID、时间与 subject；
3. DropBox 条目的 tag、时间和资源信息。

PID 会被后续进程复用，应用进程也可能在 ANR 后重启。若只按包名合并多份报告，就会把不同进程生命周期混在一起；关联时应同时使用时间、PID、进程名和错误 ID。

## trace 是快照，根因常在快照之前

系统已经尽量早地抓取目标进程栈，但采样仍发生在检测器确认超时之后。线程状态可能在超时与采样之间变化，常见情形有两类：

- 主线程在期限耗尽前执行了长任务，dump 时任务刚刚结束，堆栈已经回到 `nativePollOnce()` 等待下一条消息；
- 主线程 dump 时等待某把锁，持锁线程稍后释放，后续采样只留下普通业务帧。

因此，主线程栈停在 `nativePollOnce()`，不能反向证明主线程此前一直空闲；主线程停在某个普通方法中，也不能单独证明该方法消耗了整个超时时间。官方 ANR 诊断文档也将“采样过晚而显示 idle 的主线程聚类”列为难以直接行动的线索。

排查时可按下面的证据顺序推进：

1. 用 EventLog reason 确认检测类型和等待对象。
2. 用 trace 找阻塞关系、Binder 调用、锁持有者和线程状态。
3. 用 CPU、PSI 判断 CPU 是否饱和、线程是否长期得不到调度，以及是否存在内存或 I/O 压力。
4. 用 Perfetto 还原超时前几秒的调度、Binder、锁和主线程任务。
5. 结合版本、机型、进程生命周期和同一时段的系统日志，排除错误归因。

更完整的 trace 逐段阅读方法见 [9.3 ANR 分析方法](03-anr-analysis.md)，系统与内核联合诊断见 [9.7 ANR 与 Kernel Trace 联合诊断](07-anr-kernel-trace-joint-diagnosis.md)。

## Android 8 到 Android 17 的演进重点

这里只保留会影响诊断方式的变化；源码内部重构不一定改变对应用可见的行为。

- **Android 8（API 26）**：后台执行限制改变了后台组件的运行条件。分析旧应用时，要把“组件能否在后台启动”和“组件启动后是否超时”分开。
- **Android 11（API 30）**：公开 `ApplicationExitInfo` 与 `getHistoricalProcessExitReasons()`，应用可以在下次启动后读取自身历史退出原因和仍可用的 ANR trace。`AnrHelper` 也已进入 AMS 的统一处理路径。
- **Android 14（API 34）**：面向目标 SDK 34 及以上的部分 `JobService` 回调超时会按明确 ANR 报告；广播派发进入现代队列实现，超时可依据进程状态调整。
- **Android 15（API 35）**：公开 `ProfilingManager` 的主动采集能力；AOSP Watchdog 已能在最终期限的 1/4 处执行 pre-watchdog 采集。
- **Android 16（API 36）**：公开 `ProfilingTrigger.TRIGGER_TYPE_ANR` 和系统触发式 profiling 注册能力，为 ANR 增加一份时间段证据。
- **Android 17（API 37）**：`TimeoutRecord` 可映射公开 `AnrTypes`；`ApplicationExitInfo.getAnrInfo()` 提供结构化 ANR 元数据；`ActivityManager.registerAnrWarningListener()` 允许应用按尽力而为原则接收临近 ANR 期限的预警。详情见 [9.9 Android 17 ANR 预警回调](09-android17-anr-warning-callback.md)。

这些版本变化呈现出一条主线：各检测器继续保留自己的协议语义，AMS 统一组织报告；诊断材料则从单次线程快照扩展到结构化退出信息、早期预警和可选的时间段 profiling。传统 trace 仍是基础证据，但需要与时间线和结构化信息一起解释。

## Google Play Console 的统计边界

截至 2026 年 7 月，Android vitals 同时提供：

- **ANR rate**：每日活跃用户中经历任意 ANR 的比例；
- **user-perceived ANR rate**：每日活跃用户中经历至少一次用户可感知 ANR 的比例；当前只计入 `Input dispatching timed out`；
- **multiple ANR rate**：每日经历至少两次 ANR 的用户比例。

用户可感知 ANR 率属于 Google Play core vital（核心质量指标）。官方当前的不良行为阈值如下：

| 统计范围 | 阈值 |
|---|---:|
| 全部设备型号的每日活跃用户 | 0.47% |
| 单一手机型号的每日活跃用户 | 8% |

超过全局阈值可能影响应用在所有设备上的可发现性；若只在部分机型超过单机型阈值，也可能影响对应设备上的曝光并触发商店警告。阈值属于可能调整的平台运营规则，因此发布准入检查应读取 Play Console 和最新官方文档，不能把表中数值永久写死在监控代码中。

还要留意统计分母不同：本地 APM（应用性能监控）常按会话、事件数或进程启动次数计算，Android vitals 则按每日活跃用户计算，并受到来源设备、用户共享设置和隐私门槛影响。两边数值不同，不代表其中一方采集错误；比较前应先统一分母、时间窗口和“用户可感知”的定义。

## 工程检查表

设计监控或阅读一条 ANR 报告时，依次回答这些问题：

- 哪个检测器报的超时，reason 原文是什么？
- 系统等待的完成信号是什么，期限从哪个时刻开始？
- 被归因的 PID、进程名、窗口或组件是否一致？
- trace 与 EventLog 的时间差是多少，主线程状态是否可能已经变化？
- 主线程在运行、可运行、睡眠、Binder 等待还是锁等待？
- 若有等待关系，远端 Binder 线程或锁持有者在做什么？
- CPU、PSI、I/O 和系统服务是否显示设备级压力？
- 进程属于前台可感知 ANR、后台 silent ANR，还是 `system_server` Watchdog？
- 相同错误是否集中在特定 Android 版本、设备型号或目标 SDK？
- 修复是否真正缩短了检测器等待的那项工作，而不只是让采样时的栈顶换了位置？

## 参考资料

- Android 17 AOSP：
  - [`TimeoutRecord.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/TimeoutRecord.java)
  - [`AnrHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java)
  - [`ProcessErrorStateRecord.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessErrorStateRecord.java)
  - [`StackTracesDumpHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/StackTracesDumpHelper.java)
  - [`BroadcastQueueImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastQueueImpl.java)
  - [`ActiveServices.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)
  - [`AnrController.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/AnrController.java)
  - [`Watchdog.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/Watchdog.java)
  - [`InputDispatcher.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
  - [`IInputConstants.aidl`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/android/os/IInputConstants.aidl)
- Android Developers：
  - [ANRs 与 Android vitals](https://developer.android.com/topic/performance/vitals/anr)
  - [Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
  - [`ActivityManager.registerAnrWarningListener()`](https://developer.android.com/reference/android/app/ActivityManager#registerAnrWarningListener(java.util.concurrent.Executor,java.util.function.Consumer%3Candroid.app.AnrWarningResult%3E))
  - [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
  - [`ActivityManager.getHistoricalProcessExitReasons()`](https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,int,int))
- AOSP 调试文档：
  - [Read bug reports：ANRs and deadlocks](https://source.android.com/docs/core/tests/debug/read-bug-reports#anrs_and_deadlocks)
