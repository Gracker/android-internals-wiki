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

用户不知道应用内部正在做数据库迁移、Binder 调用还是图片解码。他只知道触摸后没有反馈、页面停住了，或刚打开的界面迟迟不能接收按键。Android 必须在有限时间内结束这种失控状态，同时留下足够证据供开发者追查。

ANR（Application Not Responding）因此负责三项工作：

1. 给输入、广播、服务等关键工作设定响应期限。
2. 期限耗尽时，从系统进程侧记录原因并采集现场。
3. 依据进程重要性、可见性和系统策略，终止进程或安排无响应界面。

这里有两个容易混淆的边界。

- ANR 约束的是系统正在等待的工作。应用中一次耗时操作若没有拖过任何受监控期限，系统不会仅凭“耗时很长”生成 ANR。
- 主线程阻塞是高频原因，但检测对象不只是一条主线程。广播可以交给指定 `Handler`，服务问题可能牵涉 Binder 线程、锁持有者或远端进程；系统判定依据是对应工作没有按期完成。

所以，分析 ANR 时应问“哪个系统期限耗尽、系统在等什么完成信号”，再问“哪条线程阻断了完成条件”。直接从主线程栈猜业务根因，容易把采样时刻的现场当成完整过程。

## Android 17 的整体分层

以 `android-17.0.0_r1` 为锚点，应用 ANR 可拆成四层。

| 层次 | 代表代码 | 职责 |
|---|---|---|
| 检测层 | `InputDispatcher`、`BroadcastQueueImpl`、`ActiveServices`、`ContentProviderHelper` | 建立期限，接收完成信号，发现超时 |
| 语义层 | `TimeoutRecord` | 保存超时类型、原因、触发时刻和延迟采集状态 |
| 编排层 | `AnrHelper` | 去重、尽早抓目标进程栈、排队处理 |
| 记录与处置层 | `ProcessErrorStateRecord` | 写日志和统计、生成 trace、提交 DropBox，并进入杀进程或界面策略 |

这种分层解决了两个系统级问题。检测器最接近业务协议，能写出“广播未完成”或“输入窗口未响应”这类具体原因；重型采集放在统一路径，避免每种组件各自实现一套堆栈、CPU 和 DropBox 逻辑。

### 检测器关注完成协议

不同检测器等待的完成信号不同：

| 场景 | 系统开始等待 | 系统认定完成 |
|---|---|---|
| 输入派发 | 事件进入目标连接并等待确认，或系统等待焦点窗口出现 | 目标连接确认已处理事件，或焦点条件满足 |
| 广播接收 | 有序或受跟踪的 receiver 开始交付 | receiver 返回，或 `goAsync()` 得到的 `PendingResult` 调用 `finish()` |
| Service 执行 | 受监控的 Service 回调开始 | 应用通过框架协议报告对应执行完成 |
| 前台服务启动 | `startForegroundService()` 建立前台化期限 | 服务按要求调用 `startForeground()` |
| ContentProvider | 系统侧的 provider 调用监控被触发 | provider 调用返回 |

输入派发的 AOSP 默认超时是 5 秒，设备实现可受 `ro.hw_timeout_multiplier` 和窗口级配置影响。广播、Service 等期限还会随前后台状态、目标 SDK 与组件类型变化，具体数值见 [9.2 ANR 类型与触发条件](02-anr-types.md)。把所有 ANR 统一记成“主线程超过 5 秒”会掩盖检测器差异。

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

`mEndUptimeMillis` 记录检测器发现超时的系统运行时间，`mEndTakenBeforeLocks` 标明这个时间点是否在获取昂贵锁之前采集。后续 ANR 处理即使排队，这两个字段仍能把“超时发生时间”和“报告处理时间”分开。Android 17 还会把内部类型映射为公开的 `AnrTypes`，用于更精细的退出记录和预警信息。

## 四阶段流程：注册、执行、超时、处置

“注册超时 → 应用处理 → 超时触发 → 弹窗或杀进程”可以概括主流程，但源码层面需要给每个箭头补上条件。

### 阶段一：注册超时

检测器在工作开始时设置期限。Android 17 的 `BroadcastQueueImpl`、`ActiveServices` 已使用 `AnrTimer`；输入路径由 native `InputDispatcher` 维护连接等待队列和 ANR 跟踪器。计时器与待处理对象绑定，完成时应取消或丢弃相应计时。

注册动作通常包含以下信息：

- 负责完成工作的进程或窗口；
- 组件、Intent 或输入目标；
- 期限开始时间和时长；
- 到期时可写入报告的原因文本。

这也解释了为什么应用自建“主线程卡顿监控”不能替代系统 ANR 统计：应用监控能观察 Looper 延迟，却不知道 system_server 正在等待哪一项协议完成，也不能复刻窗口归因和进程策略。

### 阶段二：应用执行并报告完成

大部分 Android 组件回调在应用主线程运行，所以主线程 I/O、长计算、同步 Binder、锁竞争和死锁很容易拖过期限。这个阶段仍要关注非主线程参与者：

- 主线程可能正在等待工作线程释放锁；
- 同步 Binder 的耗时由服务端线程和调度状态决定；
- `BroadcastReceiver.goAsync()` 把完成点延后到 `PendingResult.finish()`；
- 使用自定义 `Handler` 的 receiver 可能在另一条 Looper 线程执行；
- 系统负载或 CPU 调度饥饿会让可运行线程长期拿不到 CPU。

“回调方法已经 return”也不总等于协议完成。`goAsync()` 是典型例子；前台服务还需完成 `startForeground()` 要求。排查时必须找到检测器对应的完成信号。

### 阶段三：期限耗尽

计时器到期后，检测器再次核实目标是否仍处于等待状态。工作已完成、进程已退出或对象已被替换时，旧超时可被丢弃。确认超时后，检测器创建 `TimeoutRecord`，再把目标进程交给 AMS。

输入路径还多一层归因。`InputDispatcher` 识别“没有焦点窗口”或“目标连接未确认事件”后，经 `InputManagerCallback` 进入 WMS 的 `AnrController`。`AnrController` 会解析 input token、窗口、Activity 与 PID；焦点请求来自其他窗口时，它也可能把责任归给对应窗口进程。确认目标后，调用 AMS 的 `inputDispatchingTimedOut()`，再进入 `AnrHelper`。

这段路由表明，日志中的被归因进程由窗口和输入状态共同决定，未必就是用户认为的“前台 Activity 进程”。

### 阶段四：采集并执行策略

进入 AMS 后，系统会先保护诊断现场，再考虑用户界面。Android 17 的常见结果包括：

- 后台且不具备用户相关性的 silent ANR：采集后直接杀进程；
- 可感知进程：记录 `NOT_RESPONDING` 状态并向系统 UI Handler 投递无响应界面；
- Window/Activity 控制器提前处理或要求终止；
- 调试、Instrumentation、关机、进程已死等状态下跳过或改变处置。

所以，“超时必定弹窗”和“超时必定立刻杀进程”都不成立。对话框是处置分支之一；厂商系统、调试状态、后台 ANR 设置和当前用户状态都会影响用户看到什么。无对话框也不能证明没有发生 ANR。

## AMS 主路径：`AnrHelper`

`AnrHelper` 的职责是让多个检测器快速交接，把堆栈新鲜度和重型报告成本隔开。

### 先去重

Android 17 会拒绝以下无效或重复请求：

- PID 为 0；
- 同一 PID 正在处理；
- 同一 PID 正在做早期临时 dump；
- 同一 PID 已在 ANR 队列中。

这一层避免同一进程同时生成多份昂贵报告。它也意味着日志里“业务层连续卡住多次”和“系统完整处理多次 ANR”不是同一个计数口径。

### 尽早保存目标进程栈

完整 ANR 报告可能还要抓 system_server、持久进程、原生守护进程和 CPU 状态。等待这些步骤完成后再抓目标进程，主线程现场可能已经变化。`AnrHelper` 因此把目标 PID 的临时 dump 提交给独立线程池，再把 ANR 记录放入队列。

下面的 Android 17 源码节选用于观察“先 dump、后排队”的顺序：

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

`Future<File>` 会随 `AnrRecord` 进入消费线程。生成正式 trace 时，`StackTracesDumpHelper` 优先复制这份早期结果；早期 dump 失败时，再对目标 PID 做回退采集。

### 队列拥塞时缩小采集范围

`AnrConsumer` 逐条处理记录。Android 17 中，报告排队超过 10 秒，或系统启动不足 10 分钟时，`onlyDumpSelf` 为 `true`，系统只抓被归因进程，减少诊断风暴对设备的二次冲击。

两次 ANR 若间隔不足 2 分钟，`AnrHelper` 会安排 Binder heavy-hitter 自动采样，用来补充高频 Binder 调用线索。这个 2 分钟常量服务于采样调度；它不表示系统把两次 ANR 合成一条，也不表示后一次 ANR 会被忽略。

Android 17 在单条 ANR 处理结束后还可发送 `ProfilingTrigger.TRIGGER_TYPE_ANR`。系统触发式 profiling 的注册与产物边界见 [14.11 ProfilingManager](../../part3-tools/ch14-other-tools/11-profiling-manager.md)；它是补充证据来源，不能替代 ANR trace。

## AMS 主路径：`ProcessErrorStateRecord`

`ProcessErrorStateRecord.appNotResponding()` 把一条已确认的超时转成可诊断、可统计、可处置的系统事件。

### 进入报告前的状态防护

AMS 在下列条件下跳过报告：系统正在关机、进程已有 ANR、进程正在崩溃、进程已被 ActivityManager 杀死、进程已经死亡。调试器附着时也不会按普通应用 ANR 路径处理。

通过检查后，系统在锁保护下把进程标记为 `notResponding`，阻止同一进程并发进入重复报告。随后写入 `am_anr` EventLog，并尽快记录 Perfetto/Stats 触发点。

### 收集可关联证据

Android 17 的报告路径会组合：

- 超时原因、组件和 PID；
- 目标进程及选定关联进程的 Java/native 线程栈；
- 当前 CPU 使用和负载；
- PSI 资源压力；
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

EventLog 提供索引，trace 保存线程现场，DropBox 汇总更完整的报告。代码里的 `"anr"` 是错误类型参数；AMS 会结合进程类别形成具体 DropBox tag，排查时不应假定所有设备都只有固定的 `data_app_anr`。

### 决定杀进程或展示界面

证据采集完成后，`WindowProcessController` 和系统控制器先获得处理机会。普通路径继续检查 `isSilentAnr()`：开发者选项没有开启“显示所有 ANR”，并且进程不属于用户相关进程时，系统按后台 ANR 杀死它。system_server、正在展示 Activity 的进程、SystemUI、具有 top UI 或 overlay UI 的进程会被视为更值得保留完整现场。

可展示路径会生成 `ProcessErrorStateInfo.NOT_RESPONDING`，并向 AMS UI Handler 发送 `SHOW_NOT_RESPONDING_UI_MSG`。界面到达用户之前仍可能受到当前用户、系统控制器、延迟策略和设备定制影响。

## 应用 ANR 与 `system_server` Watchdog

两者都处理“长时间没有进展”，对象和恢复方式差异很大。

| 维度 | 应用 ANR | `system_server` Watchdog |
|---|---|---|
| 保护对象 | 应用组件、输入窗口和应用进程 | `system_server` 的关键 Handler 与 Monitor |
| 检测者 | 输入、广播、服务、Provider 等子系统 | `Watchdog` 线程与 `HandlerChecker` |
| Android 17 默认期限 | 按场景配置；输入 AOSP 默认 5 秒 | 普通构建默认 60 秒，可由设置和硬件超时系数调整 |
| 中间信号 | Android 17 部分路径有 ANR warning/pre-ANR | 期限的 1/4 进入 pre-watchdog；默认约 15 秒 |
| 主报告路径 | `AnrHelper` → `ProcessErrorStateRecord` | `Watchdog.run()` → `collectThreadDumps()` |
| 常见处置 | 后台杀进程或安排 ANR UI | 采集后杀掉 `system_server`，由系统重启；调试器和禁重启策略可阻止 |

Watchdog 会把检查任务投递到 system_server 的关键 Looper，并执行注册的 Monitor。检查器迟迟不能完成时，它能区分等待、pre-watchdog 和 overdue。Android 17 的 `PRE_WATCHDOG_TIMEOUT_RATIO` 是 4，因此默认 60 秒期限下，pre-watchdog 起点约为 15 秒；pre-watchdog 采集受到一小时冷却限制，完整超时仍可能在约 60 秒触发。

Watchdog 报告会使用 `pre_watchdog` 或 `watchdog` DropBox tag，并生成 system_server 及关键原生进程堆栈。完整超时后，若没有调试器、允许重启且控制器没有要求继续等待，Watchdog 调用 `Process.killProcess(Process.myPid())` 并退出。

应用 ANR 也可能由 system_server 卡顿间接引起。例如应用主线程在同步 Binder 中等待 system_server，输入期限先耗尽，此时先记录的是应用 ANR；若 system_server 的受监控线程也持续不前进，Watchdog 才会独立触发。两个报告的时间线需要一起看，不能凭进程名把前者直接定性成应用缺陷。

## 三类基础产物怎么配合

### EventLog：回答“何时、谁、因为什么”

Android 17 的 `am_anr` tag 为 30008，字段顺序是 user、PID、进程名、应用 flags、reason。reason 来自检测器构造的 `TimeoutRecord`，往往是分类入口中最稳定的线索。

下面的命令用于在调试设备或 bugreport 文本中定位 ANR 索引：

```bash
adb shell logcat -b events -d -v threadtime | grep 'am_anr'
grep 'am_anr' bugreport.txt
```

第一条读取设备当前 events 缓冲区，第二条搜索已导出的报告。缓冲区会滚动，线上问题应优先保存带时间戳的完整 bugreport 或平台侧记录。

### ANR trace：回答“采样时线程在做什么”

Android 17 的 `StackTracesDumpHelper` 在 `/data/anr/` 创建 `anr_yyyy-MM-dd-HH-mm-ss-SSS` 文件，权限为 `0600`。历史 bugreport 中仍会出现 `traces.txt` 这个名字，以下用“ANR trace”统称两种形式。

普通第三方应用不能直接遍历 `/data/anr`。开发阶段可从 bugreport 获取系统收集的 ANR 段；Android 11（API 30）起，应用还能通过 `ActivityManager.getHistoricalProcessExitReasons()` 查询自己的历史退出记录，并用 `ApplicationExitInfo.getTraceInputStream()` 读取系统保留的 trace。该流可能为 `null`，因为 trace 使用容量有限的全局循环缓冲区，也可能被后续记录覆盖。

下面的 Kotlin 片段用于回捞当前应用最近一次带 trace 的 ANR 退出记录：

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

这个 API 返回本应用可访问的历史信息，不是一份包含系统全貌的 bugreport。生产环境上传前应做大小限制、隐私审查和脱敏，并把 `null` 当作正常结果处理。

Android 17（API 37）还给 `ApplicationExitInfo` 增加 `getAnrInfo()`。返回的 `AnrInfo` 包含 ANR ID、`AnrTypes` 类型、系统等待时长和用户可感知标志。它只在 `REASON_ANR` 记录中可能存在；输入派发等缺少 `AnrTimer.ExpiredTimer` 的路径仍可能拿不到对象，兼容代码要做版本和空值判断。

### DropBox：回答“系统汇总了哪些上下文”

`ProcessErrorStateRecord` 会把 ANR 摘要、资源压力、trace 文件和关联信息交给 `ActivityManagerService.addErrorToDropBox()`。最终 tag 与进程类别相关，常见形式包含 `data_app_anr`、`system_app_anr` 等；AOSP 与厂商构建可能存在差异。

下面的命令用于在具备相应调试权限的设备上查看 DropBox 索引和内容：

```bash
adb shell dumpsys dropbox --file
adb shell dumpsys dropbox --print data_app_anr
```

第一条先列出设备上已有条目及 tag，确认名称后再用第二类命令读取目标 tag，避免把某个示例 tag 当成所有 ANR 的固定名称。

### 三者按时间关联

一份可靠的基础证据包至少要对齐：

1. EventLog 的时间、PID、进程名和 reason；
2. trace 文件头中的 PID、时间与 subject；
3. DropBox 条目的 tag、时间和资源信息。

PID 会复用，进程也可能在 ANR 后重启。只按包名合并多份报告，会把不同进程生命周期混在一起；时间、PID、进程名和错误 ID 应共同参与关联。

## trace 是快照，根因常在快照之前

系统已经尽量早抓目标进程栈，但采样仍发生在检测器确认超时之后。两类时间漂移很常见：

- 主线程在期限耗尽前执行了长任务，dump 时任务刚结束，堆栈已回到 `nativePollOnce()`；
- 主线程 dump 时等待某把锁，持锁线程稍后释放，后续采样只留下普通业务帧。

因此，主线程栈处于 `nativePollOnce()` 不能反向证明主线程一直空闲；主线程处于某个普通方法也不能单独证明该方法消耗了整个超时时间。官方 ANR 诊断文档也把“采样过晚的 idle 主线程聚类”列为低可操作性线索。

排查时可按下面的证据顺序推进：

1. 用 EventLog reason 确认检测类型和等待对象。
2. 用 trace 找阻塞关系、Binder 调用、锁持有者和线程状态。
3. 用 CPU、PSI 判断计算饱和、调度饥饿或内存/I/O 压力。
4. 用 Perfetto 还原超时前几秒的调度、Binder、锁和主线程任务。
5. 用版本、机型、进程生命周期与同时间段系统日志排除错误归因。

更完整的 trace 逐段阅读方法见 [9.3 ANR 分析方法](03-anr-analysis.md)，系统与内核联合诊断见 [9.7 ANR 与 Kernel Trace 联合诊断](07-anr-kernel-trace-joint-diagnosis.md)。

## Android 8 到 Android 17 的演进重点

这里保留影响诊断模型的变化，不把每个内部重构都当成行为变化。

- **Android 8（API 26）**：后台执行限制改变了后台组件的运行条件。分析旧应用时，要把“组件能否在后台启动”和“组件启动后是否超时”分开。
- **Android 11（API 30）**：公开 `ApplicationExitInfo` 与 `getHistoricalProcessExitReasons()`，应用可以在下次启动后回捞自身历史退出原因和可用的 ANR trace。`AnrHelper` 也已进入 AMS 的统一编排路径。
- **Android 14（API 34）**：面向目标 SDK 34 及以上的部分 `JobService` 回调超时会按明确 ANR 报告；广播派发进入现代队列实现，超时可依据进程状态调整。
- **Android 15（API 35）**：公开 `ProfilingManager` 的主动采集能力；AOSP Watchdog 已具备 1/4 期限处的 pre-watchdog 采集。
- **Android 16（API 36）**：公开 `ProfilingTrigger.TRIGGER_TYPE_ANR` 和系统触发式 profiling 注册能力，为 ANR 增加一份时间段证据。
- **Android 17（API 37）**：`TimeoutRecord` 可映射公开 `AnrTypes`；`ApplicationExitInfo.getAnrInfo()` 提供结构化 ANR 元数据；`ActivityManager.registerAnrWarningListener()` 允许应用按尽力而为原则接收临近 ANR 期限的预警。详情见 [9.9 Android 17 ANR 预警回调](09-android17-anr-warning-callback.md)。

版本演进的方向很清楚：检测器保留各自的协议语义，AMS 加强统一编排；诊断材料从一次线程快照扩展到结构化退出信息、早期预警和可选的时间段 profiling。传统 trace 仍是基础证据，只是它不再负责全部解释任务。

## Google Play Console 的统计边界

截至 2026 年 7 月，Android vitals 同时提供：

- **ANR rate**：每日活跃用户中经历任意 ANR 的比例；
- **user-perceived ANR rate**：每日活跃用户中经历至少一次用户可感知 ANR 的比例；当前只计入 `Input dispatching timed out`；
- **multiple ANR rate**：每日经历至少两次 ANR 的用户比例。

用户可感知 ANR 率属于 Google Play core vital。官方当前的不良行为阈值是：

| 统计范围 | 阈值 |
|---|---:|
| 全部设备型号的每日活跃用户 | 0.47% |
| 单一手机型号的每日活跃用户 | 8% |

超过全局阈值可能影响应用在所有设备上的可发现性；只在部分机型超过单机型阈值，也可能影响对应设备上的曝光并触发商店警告。阈值属于平台运营规则，可能调整，做发布门禁时应读取 Play Console 和最新官方文档，不能把表中数值永久写死在监控代码里。

还有一个统计陷阱：本地 APM 常按会话、事件数或进程启动次数计算，Android vitals 按每日活跃用户计算，并受到来源设备、用户共享设置和隐私门槛影响。两边数值不同不等于任何一边采集错误；团队应先统一分母、时间窗口和“用户可感知”的定义。

## 工程检查表

设计监控或阅读一条 ANR 报告时，依次回答这些问题：

- 哪个检测器报的超时，reason 原文是什么？
- 系统等待的完成信号是什么，期限从哪个时刻开始？
- 被归因的 PID、进程名、窗口或组件是否一致？
- trace 与 EventLog 的时间差是多少，主线程现场是否可能已经漂移？
- 主线程在运行、可运行、睡眠、Binder 等待还是锁等待？
- 若有等待关系，远端 Binder 线程或锁持有者在做什么？
- CPU、PSI、I/O 和系统服务是否显示设备级压力？
- 进程是前台可感知、后台 silent ANR，还是 system_server Watchdog？
- 相同错误是否集中在特定 Android 版本、设备型号或目标 SDK？
- 修复是否缩短了检测器等待的那项工作，而不只是在 trace 顶部移动了栈帧？

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
