---
title: Activity Manager Service 与性能分析
chapter: '1.8'
section: '1.8'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android Developers + Perfetto
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/Constants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/Task.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/InputManagerCallback.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/AnrController.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Instrumentation.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationStartInfo.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentResolver.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/InputConstants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/res/res/values/attrs_manifest.xml @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp @ android-17.0.0_r1"
  - type: official
    path: "https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/timeout"
  - type: official
    path: "https://developer.android.com/about/versions/14/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/bg-audio"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationStartInfo#getStartComponent()"
  - type: official
    path: "https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention"
tags:
- ams
- activity-manager
- process-lifecycle
- anr
- service-management
- broadcast
- content-provider
related_chapters:
- '1.3'
- '1.4'
- '1.10'
- '1.25'
- '1.33'
- '1.34'
- '1.47'
- '4.4'
- '5.8'
- '8.1'
- '8.2'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch01-architecture/1.68-android17-activitymanager-architecture-performance.md"
---

# 1.8 Activity Manager Service 与性能分析

活动管理服务（ActivityManagerService，AMS）负责在系统侧协调应用组件与进程生命周期。它不渲染界面，也不直接执行应用代码；它记录“哪个进程承载哪些组件、当前有多重要、某次组件调用是否按时完成”，并协调相应模块创建进程、调度组件和记录异常。

分析冷启动、进程被终止、Service 卡住或广播导致的应用无响应（ANR）时，AMS 的记录常用于对应系统事件与应用调用栈。排查时应先确认：

1. 谁发起了操作；
2. 系统把操作投递给了哪个进程和线程；
3. 计时从哪里开始、由什么回调结束；
4. 超时后发生的是 ANR、异常、进程清理，还是普通的等待失败。

当前源码基线为 Android 开源项目（AOSP）`android-17.0.0_r1`。Android 10～16 只用于解释版本演进。

---

## AMS、ATMS 与 WMS 的分工

这三个服务都运行在承载核心系统服务的 `system_server` 进程中，但职责不同：

| 服务 | 主要职责 | 分析时常见入口 |
|---|---|---|
| AMS | 进程、Service、广播、ContentProvider、ANR、崩溃、进程重要性 | `ActivityManagerService`、`ProcessList`、`ActiveServices`、`BroadcastQueueImpl` |
| Activity 任务管理服务（ATMS） | Activity 启动、任务（Task）选择、前后台切换、启动模式 | `ActivityTaskManagerService`、`ActivityStarter`、`ActivityRecord` |
| 窗口管理服务（WMS） | 窗口容器、焦点、可见性、输入窗口状态 | `RootWindowContainer`、`DisplayContent`、`AnrController` |

`Instrumentation.execStartActivity()` 直接调用 `ActivityTaskManager.getService().startActivity()`。“启动 Activity 都由 AMS 完成”是旧版实现的说法。现代 Android 中，ATMS 先决定 Activity 应放进哪个任务；只有目标进程不存在时，才请求 AMS/`ProcessList` 创建进程。

AMS 通过 `IActivityManager` Binder 接口接受跨进程请求。请求通常先由 `Binder:system_server_*` 线程接收，再在持锁区域、`Handler` 或其他系统线程中继续处理。不要把名为 `ActivityManager` 的线程理解成唯一的 AMS 主线程，也不要把 Binder 线程池数量写成固定值：线程池上限和实际线程数都可能随系统构建及运行状态变化。

### Perfetto 中先看什么

使用系统性能跟踪工具 Perfetto 分析 AMS 时，证据主要来自三类数据：

- `system_server` 与目标应用的线程时间片段；
- Binder 事务、线程状态和 Java 监视器锁竞争（monitor contention）；
- 系统事件日志（EventLog），例如 `am_proc_start`、`am_proc_bound`、`am_anr`、`am_crash`、`am_kill`。

EventLog 不是普通时间片段。只有跟踪配置启用了 Android 日志数据源并包含事件缓冲区（events buffer），`android_logs` 表中才会有这些记录。下面的查询同时保留消息内容，便于读取进程 ID（PID）、进程名和原因：

```sql
SELECT
  l.ts,
  p.pid,
  p.name AS process_name,
  l.tag,
  l.msg
FROM android_logs AS l
LEFT JOIN thread AS t USING (utid)
LEFT JOIN process AS p USING (upid)
WHERE l.tag IN (
  'am_proc_start',
  'am_proc_bound',
  'am_anr',
  'am_crash',
  'am_kill',
  'am_proc_died'
)
ORDER BY l.ts;
```

这段查询用于建立时间坐标，不足以单独判断原因。没有采集到某个日志标签（tag），也不表示事件没有发生。

---

## 进程重要性：`procState` 与 `oom_score_adj`

Android 不只把进程分为“前台”和“后台”。AMS 会综合 Activity 可见性、正在执行的 Service、ContentProvider 依赖、BroadcastReceiver、Binder 绑定关系等信息，计算进程状态和内存回收优先级。

这两个概念需要分开：

- 进程状态 `procState` 描述进程当前负责的工作，供调度、后台限制和权限判断使用；
- 内存不足调整分数 `oom_score_adj` 供内存回收使用。值越大，通常越早成为回收候选。

两者相关，但不是固定的一一对应关系。同一个进程也可能同时承载 Activity、Service 和 ContentProvider，最终重要性取决于所有依赖关系中最强的保护条件。

### Android 17 的关键 `adj` 档位

`frameworks/base/services/core/java/com/android/server/am/psc/Constants.java` 在 `android-17.0.0_r1` 中定义了以下基准值：

| 常量 | 值 | 典型含义 |
|---|---:|---|
| `FOREGROUND_APP_ADJ` | 0 | 当前顶层交互进程 |
| `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ` | 50 | 刚从顶层应用（TOP）转为前台服务（FGS）的短暂宽限 |
| `VISIBLE_APP_ADJ` | 100 | Activity 可见但不在顶层 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 用户可感知的工作，例如常规的非 `shortService` 类型 FGS |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | 由重要系统绑定保护的中间档 |
| `PERCEPTIBLE_LOW_APP_ADJ` | 250 | 比普通 Service 更重要的低可感知工作 |
| `BACKUP_APP_ADJ` | 300 | 正在备份 |
| `SERVICE_ADJ` | 500 | 普通后台 Service |
| `HOME_APP_ADJ` | 600 | 桌面（Home/Launcher） |
| `PREVIOUS_APP_ADJ` | 700 | 上一个前台应用的基准档 |
| `SERVICE_B_ADJ` | 800 | 较低优先级的旧 Service |
| `CACHED_APP_MIN_ADJ`～`CACHED_APP_MAX_ADJ` | 900～999 | 缓存进程 |

表中数值是源码常量，不承诺每种组件永远落在某一行。Android 17 还可以通过功能开关（feature flag）对可见进程和上一个应用（previous app）分配更细的档位。`TOP_SLEEPING` 也是计算分支中的调整类型 `adjType`，不能把它当成独立常量档位。

前台 Service 的 `adj` 同样不是“永远 100”。在当前固定源码版本中，常规的非 `shortService` 类型 FGS 通常受 `PERCEPTIBLE_APP_ADJ = 200` 保护；刚从顶层应用进入 FGS 的进程可在宽限期内使用 50。它仍可能在极端内存压力、异常或用户停止服务时退出。

### AMS 如何把分数交给 `lmkd`

Android 17 的实际计算位于 `com.android.server.am.psc.OomAdjuster` 和 `OomAdjusterImpl`。计算完成后，`ProcessList.setOomAdj()` 通过套接字（socket）向低内存终止守护进程 `lmkd` 发送 `LMK_PROCPRIO` 消息，消息中包含进程 ID、用户 ID（UID）与 `adj`。`lmkd` 再结合资源压力停顿信息（PSI）、剩余内存阈值（内存水位）、回收压力及候选进程信息，决定是否终止进程以及选择哪个进程。

“`lmkd` 每次从 `/proc/<pid>/oom_score_adj` 扫描并按最大值终止进程”过度简化了现行实现。`oom_score_adj` 仍是内核可见的重要状态，但 AMS 与 `lmkd` 之间存在明确的控制消息。

Perfetto 的 Android 内存标准库可以把 `adj` 变化与内存数据放在一起查看：

```sql
INCLUDE PERFETTO MODULE android.memory.process;

SELECT
  ts,
  dur,
  pid,
  process_name,
  score,
  bucket,
  oom_adj_reason,
  rss,
  swap
FROM memory_oom_score_with_rss_and_swap_per_process
WHERE process_name = 'com.example.app'
ORDER BY ts;
```

能否得到完整结果取决于跟踪配置。看到 `adj` 升高只能说明保护程度下降；判断进程为何终止，还要结合 `lmkd` 日志、`ApplicationExitInfo`、`am_proc_died` 和内存压力。`am_kill` 表示 AMS 记录了一次主动终止操作，不能仅凭这个日志标签断言“进程被 `lmkd` 回收”。

---

## 冷启动中的 AMS

### 从点击图标到应用主线程

冷启动的关键调用关系如下：

```text
Launcher
  → Instrumentation.execStartActivity()
    → ActivityTaskManager.getService().startActivity()
      → ActivityTaskManagerService / ActivityStarter
        → 选择 TaskDisplayArea 与 Task
        → 目标进程不存在
          → ActivityTaskManagerService.startProcessAsync()
            → ActivityManagerInternal.startProcess()
              → ProcessList.startProcessLocked()
                → Process.start() / ZygoteProcess.start()
                  → Zygote fork
                    → ActivityThread.main()
                      → ActivityThread.attach()
                        → AMS.attachApplication()
                          → AMS 安排 bindApplication 与待启动组件
```

这里有两个容易误判的事件：

- `am_proc_start` 记录 AMS/`ProcessList` 发起进程创建的时刻，不是用户点击时刻，也不能代表完整冷启动耗时；
- `am_proc_bound` 写在 `attachApplicationLocked()` 中，表示 AMS 已经接受新进程的 `IApplicationThread` 连接。它不表示 `Application.onCreate()` 已经结束，更不表示首帧已经显示。

### 一次可靠的启动分析

冷启动至少应对齐这些时刻：

1. 启动请求发出；
2. `am_proc_start`；
3. Zygote 创建进程与新进程出现；
4. `ActivityThread.main()`、`attachApplication`、`bindApplication`；
5. `Application.onCreate()`；
6. Activity 生命周期；
7. 首帧提交与显示。

只计算 `am_proc_start` 到 `am_proc_bound`，得到的是进程创建和应用线程连接（attach）的一部分，不能代表用户感知的启动时间。

Android 15（API 35）引入 `ApplicationStartInfo`，Android 16（API 36）又增加 `getStartComponent()`。后者可以区分进程由 Activity、Service、BroadcastReceiver、ContentProvider 或其他组件拉起：

```kotlin
val activityManager = getSystemService(ActivityManager::class.java)
val latest = activityManager
    .getHistoricalProcessStartReasons(1)
    .firstOrNull()

if (Build.VERSION.SDK_INT >= 36 && latest != null) {
    when (latest.startComponent) {
        ApplicationStartInfo.START_COMPONENT_ACTIVITY -> {
            // 由 Activity 启动进程
        }
        ApplicationStartInfo.START_COMPONENT_SERVICE -> {
            // 由 Service 启动进程
        }
        ApplicationStartInfo.START_COMPONENT_BROADCAST -> {
            // 由 BroadcastReceiver 启动进程
        }
        ApplicationStartInfo.START_COMPONENT_CONTENT_PROVIDER -> {
            // 由 ContentProvider 启动进程
        }
    }
}
```

这段代码适合用于启动诊断，并根据启动组件选择不同的初始化路径。`getReason()` 提供更细的启动原因，`getStartComponent()` 则直接区分四类应用组件。

---

## ANR：先找计时器，再看阻塞点

应用无响应（Application Not Responding，ANR）并不等于统一的“主线程卡 5 秒”。不同系统模块在投递工作时各自开始计时，结束计时所等待的回调也不同。

| 场景 | Android 17 AOSP 基础值 | 计时结束条件 |
|---|---:|---|
| 输入分发（Input dispatch） | 通常 5 秒 | 目标窗口及时处理输入，或焦点问题解除 |
| 前台优先级广播 | 10 秒基础值 | 同步 `onReceive()` 返回，或异步 `PendingResult.finish()` 被调用 |
| 后台优先级广播 | 60 秒基础值 | 同上 |
| 前台进程中的 Service 回调 | 20 秒基础值 | 对应 Service 执行回调完成 |
| 后台进程中的 Service 回调 | 200 秒基础值 | 对应 Service 执行回调完成 |

这些值不是跨设备保证不变的 API 约定。AOSP 会乘以 `Build.HW_TIMEOUT_MULTIPLIER`，设备厂商也可能调整。Android 14 及以上版本的广播计时还会为长时间得不到 CPU 的进程延长窗口：官方诊断文档给出的范围是前台优先级 10～20 秒、后台优先级 60～120 秒。

### 输入 ANR

输入 ANR 从原生层的 `InputDispatcher` 开始。典型路径是：

```text
InputDispatcher.processAnrsLocked()
  → notifyWindowUnresponsive()
    或 notifyNoFocusedWindowAnr()
      → InputManagerCallback
        → AnrController
          → ActivityRecord.inputDispatchingTimedOut()
            → AnrHelper.appNotResponding()
```

两类输入超时需要分开：

- **窗口无响应（Window unresponsive）**：已有目标窗口，但输入事件在分发队列中等待过久；
- **没有焦点窗口（No focused window）**：按键等需要焦点的事件到达时，没有可接收它的焦点窗口。

第二种情况不一定是某个 `onTouchEvent()` 太慢。首帧迟迟没有建立窗口、窗口带有“不接受焦点”标志 `FLAG_NOT_FOCUSABLE`，或焦点切换长时间停留在 WMS 中，都可能触发它。

排查时先看应用主线程状态：

- 长时间运行（Running）：检查长任务与热点代码；
- 长时间可运行（Runnable）却得不到 CPU：检查 CPU 争用和系统负载；
- 睡眠（Sleeping）且在等待 Binder：沿 Binder 响应找到服务端；
- 睡眠且在等待锁：找到持锁线程；
- 主线程已经空闲：堆栈可能采集得太晚，需要查看 ANR 发生前的跟踪数据。

### 广播 ANR

Android 17 中，AMS 创建前台与后台两套 `BroadcastConstants`。`ActivityManagerService` 给它们设置 10 秒和 60 秒基础超时，`BroadcastQueueImpl.dispatchReceivers()` 在向目标进程调度广播接收器时启动 `BroadcastAnrTimer`。

计时边界如下：

- 广播进入系统队列的时刻，不等于 ANR 计时开始；
- 创建冷进程所花的时间会占用接收器的执行时间；
- 同步接收器在 `onReceive()` 返回时完成；
- 调用 `goAsync()` 后，必须由 `PendingResult.finish()` 结束本次投递。

`FLAG_RECEIVER_FOREGROUND` 决定这里的“前台优先级广播”。它不表示接收进程中一定有前台 Activity。

### Service 执行 ANR

Service 的 20/200 秒描述的是执行回调超时，不是 Service 允许存活多久。Android 17 在 `ActiveServices` 中使用进程 ANR 计时器 `ProcessAnrTimer`，基础值来自 `ActivityManagerConstants.SERVICE_TIMEOUT` 和 `SERVICE_BACKGROUND_TIMEOUT`。

创建 Service 时的核心关系可以简化为：

```text
ActiveServices.realStartServiceLocked()
  → bumpServiceExecutingLocked()
    → 启动 ProcessAnrTimer
  → IApplicationThread.scheduleCreateService()   // oneway Binder

ActivityThread.handleCreateService()
  → Service.onCreate()
  → AMS.serviceDoneExecuting()
    → 没有其他执行中 Service 时取消计时
```

`onStartCommand()`、`onBind()` 等回调也会纳入相应的 Service 执行管理。应用进程若为承载 Service 而冷启动，冷启动本身也会占用超时时间。

#### `startForegroundService()` 的前台提升使用另一套计时器

调用 `startForegroundService()` 后没有及时调用 `Service.startForeground()`，会触发“未及时提升为前台服务”的超时路径。`android-17.0.0_r1` 中：

- `DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS` 为 30 秒；
- 超时后 `DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS` 再给 10 秒延迟；
- `ActiveServices.serviceForegroundTimeout()` 创建超时记录，随后进入 ANR 处理。

这组数值是 Android 17 固定源码版本中的默认实现，不能反推为所有 Android 版本和所有设备都保证 30+10 秒。开发应用时，仍应在 `onCreate()` 中立即建立通知并调用 `startForeground()`，不要把任何超时值当作可用工作时间。

它也不同于 Android 15 起按前台服务类型计算的总运行时长限制。后者到期会调用 `Service.onTimeout(int, int)`，未及时停止时产生 `RemoteServiceException`；这不属于 Service 执行 ANR。

### ContentProvider：三种等待对应三种结果

“ContentProvider ANR 是 10 秒”会把三种机制混在一起。Android 17 的 `ContentResolver` 定义了：

| 等待点 | 默认值 | 超时后的主要含义 |
|---|---:|---|
| ContentProvider 发布（publish） | 10 秒 | 进程连接 AMS 后没有发布 ContentProvider，AMS 按初始化失败清理进程 |
| ContentProvider 就绪（ready） | 20 秒 | 调用方等待 ContentProvider 可用时超时，获取失败 |
| 已连接远端 ContentProvider 的部分异步调用 | 3 秒 | 等待特定 API 的远端结果；可通过 `appNotRespondingViaProvider()` 报告宿主无响应 |

`ContentProviderHelper.processContentProviderPublishTimedOutLocked()` 会以“发布 ContentProvider 超时”为原因移除进程；外部调用者等待 ContentProvider 就绪超时后可能只得到 `null`。真正进入 ContentProvider ANR 流程时，`ContentProviderHelper.appNotRespondingViaProvider()` 会创建 `TimeoutRecord.forContentProvider()` 并交给 `AnrHelper`。

排查 ContentProvider 卡顿时，先确认它发生在：

1. 应用启动和 `installContentProviders()`；
2. 获取 ContentProvider；
3. 已建立 Binder 连接后的具体 ContentProvider 方法。

ContentProvider 通常在应用主线程初始化。即使最终报告的是输入、广播或 Service ANR，原因也可能是某个 ContentProvider 在进程启动阶段执行了数据库迁移或同步 I/O。

### ANR 数据是怎样保存的

各入口最终可调用 `AnrHelper.appNotResponding()`。Android 17 会尽早为主要目标进程生成临时堆栈，正式处理时再由 `StackTracesDumpHelper` 收集相关 Java/原生调用栈与 CPU 信息。正式文件位于 `/data/anr/`，文件名以 `anr_` 开头，不再使用早期版本常见的固定文件名 `traces.txt`。

如果 ANR 排队超过 10 秒，`AnrHelper` 会把报告视为过期，只导出目标进程的堆栈，避免在系统已经很慢时继续增加负载。因此，ANR 文件里缺少其他进程的堆栈不一定是采集故障。

定位 EventLog 可以使用：

```sql
SELECT ts, tag, msg
FROM android_logs
WHERE tag = 'am_anr'
ORDER BY ts;
```

确定时间点后，应查看超时前的线程状态、Binder 依赖和锁依赖。ANR 发生后线程可能已经恢复，只看最后采集的一份堆栈容易错过真正的阻塞区间。

---

## Activity 与任务的现行容器模型

现代 Android 的任务容器更接近下面的层级：

```text
RootWindowContainer
  └─ DisplayContent
      └─ TaskDisplayArea
          └─ Task
              └─ ActivityRecord
```

其中：

- `RootWindowContainer` 是所有显示与窗口容器的根节点；
- 一个显示内容容器 `DisplayContent` 可以包含多个任务显示区域 `TaskDisplayArea`；
- `TaskDisplayArea` 可以容纳任务，也可以嵌套；
- `Task` 既可能对应最近任务界面（Recents）中的一张任务卡，也可能是嵌套任务容器；
- `ActivityRecord` 是单个 Activity 的系统侧记录。

`ActivityStarter` 计算目标显示区域、启动模式与可复用任务，ATMS/WMS 再把 `ActivityRecord` 放入合适容器。旧文章中的 `TaskStack` 可以用于解释历史实现，不应再作为 Android 17 的主模型。

### Android 17 减少了部分配置变化触发的重建

`android:recreateOnConfigChanges` 不是 Android 17 才出现的属性。Android O 已使用它控制移动国家码 `mcc` 和移动网络码 `mnc` 变化时是否显式重建。Android 17 扩大了默认不重建 Activity 的配置范围：

- `keyboard`、`keyboardHidden`；
- `navigation`；
- `touchscreen`；
- `colorMode`；
- `uiMode`，仅限进入或离开 `UI_MODE_TYPE_DESK`。

如果应用依赖 Activity 重建来重新加载这些资源，需要在 `AndroidManifest.xml` 中显式选择：

```xml
<activity
    android:name=".MainActivity"
    android:recreateOnConfigChanges="keyboard|keyboardHidden|navigation|touchscreen|colorMode|uiMode" />
```

这段配置用于恢复“发生这些变化时重建 Activity”的行为。它不是控制所有配置变化的总开关。

还要注意它与 `android:configChanges` 的关系：同一配置标志若同时出现在两个属性中，Activity 不会因该变化重建。前者要求重建，后者表示应用自行处理；二者同时声明时，以应用自行处理为准。`uiMode` 在 Android 17 桌面模式下的边界，还需结合应用目标版本与设备行为测试。

---

## Service 与前台服务的版本边界

前台服务（Foreground Service，FGS）用于用户明确知情、需要持续运行的任务。它提升进程重要性并要求显示持续通知，但不能绕过后台限制。

| 版本 | 与 AMS/FGS 相关的主要变化 |
|---|---|
| Android 8（API 26） | 后台 Service 启动受限，引入 `startForegroundService()` 使用方式 |
| Android 11（API 30） | 后台启动的 FGS 访问相机、麦克风、位置受到更严格限制 |
| Android 12（API 31） | 后台启动 FGS 默认禁止，仅保留明确豁免 |
| Android 13（API 33） | 用户可在活跃应用（Active apps）/FGS 管理界面查看并停止服务；通知权限与 FGS 通知展示分开处理 |
| Android 14（API 34） | 目标版本要求声明 FGS 类型和对应权限；后台创建 FGS 时会同步检查仅在使用应用时有效的权限（while-in-use）是否可用 |
| Android 15（API 35） | `dataSync` 与 `mediaProcessing` 各自共享每 24 小时 6 小时后台额度，并提供 `Service.onTimeout()` |
| Android 16（API 36） | 与 FGS 并发执行的 Job 也计入 `JobScheduler` 运行时配额 |
| Android 17（API 37） | 后台音频交互增加生命周期、FGS 与 while-in-use（WIU）权限约束 |

Android 17 的后台音频规则分两层：

1. 所有运行在 Android 17 上的应用，要么在可见 Activity 中操作音频，要么运行一个类型不是 `shortService` 的 FGS；
2. 目标 API 37 的后台应用还需要运行一个具备 while-in-use 权限能力的 FGS。具有精确闹钟权限且操作 `USAGE_ALARM` 音频流时存在例外。

播放和音量 API 在不满足生命周期条件时通常不会生效，也不会抛出显眼错误；音频焦点请求会返回 `AUDIOFOCUS_REQUEST_FAILED`。因此，不能笼统写成“Android 17 所有后台 FGS 没有 WIU 就静默失败”，目标版本、Activity 可见性、FGS 类型和闹钟例外都要一起判断。

可延迟、可重试的工作优先考虑 `JobScheduler` 或 `WorkManager`；用户发起的数据传输可评估用户发起的数据传输任务（user-initiated data transfer job）；持续媒体播放更适合使用 Media3 的 `MediaSessionService`。选择依据是任务含义和约束，不能把所有 FGS 一律替换成 WorkManager。

### AMS 全局锁竞争

`ActivityManagerService.startService()` 在 Android 17 中没有给整个 Java 方法加 `synchronized`。它完成调用者检查后才进入以下同步代码块：

```java
synchronized (mGlobalLock) {
    res = mServices.startServiceLocked(...);
}
```

`ActiveServices` 方法名中的 `...Locked()` 表示调用者应持有 AMS 全局锁，不代表存在一个独立的“`mServices` 锁”。`realStartServiceLocked()` 还会在这段受锁保护的代码中向应用发送 `IApplicationThread.scheduleCreateService()`；这是单向异步（oneway）Binder 调用，但 Binder 驱动排队、系统负载和执行时间较长的持锁代码段（临界区）仍可能增加其他线程的锁等待时间。

采集 Java 监视器锁竞争数据后，可以用 Perfetto 标准库定位：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  ts,
  dur / 1e6 AS duration_ms,
  blocked_thread_name,
  blocking_thread_name,
  short_blocked_method,
  short_blocking_method,
  waiter_count,
  binder_reply_id,
  lock_name
FROM android_monitor_contention
WHERE process_name = 'system_server'
  AND (
    blocked_method GLOB '*ActivityManagerService*'
    OR blocking_method GLOB '*ActivityManagerService*'
    OR blocked_method GLOB '*ActiveServices*'
    OR blocking_method GLOB '*ActiveServices*'
  )
ORDER BY dur DESC
LIMIT 20;
```

`blocked_*` 表示等待锁的一侧，`blocking_*` 表示持锁的一侧。`binder_reply_id` 非空时，标准库已经把锁竞争与相关 Binder 响应建立关联；不能只凭两个时间片段相邻就判断它们存在因果关系。

---

## Android 17 的广播调度

### 按进程组织的队列

Android 17 主要通过 `BroadcastQueueImpl` 与 `BroadcastProcessQueue` 调度广播。AMS 先解析接收器，再按目标进程组织等待和运行状态：

```text
Context.sendBroadcast()
  → ActivityManagerService.broadcastIntent()
    → 解析 manifest / context-registered Receiver
      → BroadcastQueueImpl 入队
        → BroadcastProcessQueue 选择可运行目标进程
          → IApplicationThread.scheduleReceiver()
            或 scheduleRegisteredReceiver()
```

同一进程的接收器最终仍要在该进程指定的 `Handler` 或线程上执行。主线程繁忙时，排在队首的广播会阻止后续广播执行。不同进程的队列可以独立推进，避免一个慢进程阻塞所有广播。

“无序广播并行执行”也有边界。无序广播没有全局结果传递顺序，系统可以调度多个目标进程；但同一进程中的接收器不会因此自动获得并行线程。接收器运行在哪个线程，取决于注册时使用的调度器及系统投递方式。

### 清单注册与运行时注册的接收器

- 清单注册的接收器（Manifest Receiver）可以在规则允许时创建尚未运行的应用进程，因此可能把冷启动时间计入广播执行时间；
- 运行时注册的接收器（context-registered Receiver）只在注册对象有效时接收，不会为了已经失效的注册关系单独创建进程；
- 从 Android 8 开始，清单中的隐式广播受到广泛限制，并非任意静态接收器都能被系统事件唤醒；
- 目标版本为 Android 14 及以上的应用注册并非仅接收系统广播的接收器时，要显式使用 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`。

### Android 14 及以上版本的缓存态广播

Android 14 起，应用处于缓存态（cached state）时，系统可以暂存发给运行时注册接收器的广播，等应用离开缓存态后再投递；某些重复广播还可能被合并。发给清单注册接收器的广播不使用这套排队方式，系统可先让应用离开缓存态再投递。

这会改变系统跟踪数据的解释：

- “广播发送后很久才进入 `onReceive()`”可能是系统按设计暂存了缓存态广播，不一定是 AMS 卡住；
- 清单注册的接收器仍可能触发进程启动。判断大量进程集中启动的原因时，要结合隐式广播限制和具体广播动作（`action`）；
- 接收器 ANR 的计时从 `BroadcastQueueImpl` 调度目标接收器时开始，不从广播发送时开始。

---

## 三个常用排查模板

### 冷启动慢

1. 用启动请求或 `ApplicationStartInfo.START_TIMESTAMP_LAUNCH` 确定起点；
2. 查看 `am_proc_start` 到创建进程（fork）的时间，判断 `system_server`/Zygote 阶段；
3. 查看新进程出现到 `bindApplication` 的时间，判断运行时初始化与进程连接 AMS 的阶段；
4. 查看 `Application.onCreate()`、ContentProvider 安装和 Activity 生命周期；
5. 查看渲染线程 `RenderThread`、首帧提交和系统合成服务 SurfaceFlinger 的显示时刻；
6. 用 `getStartComponent()` 确认是哪个组件拉起了进程。

### ANR

1. 从 ANR 主题（subject）或 `am_anr.msg` 确认类型；
2. 按类型找到计时器的开始点与结束回调；
3. 查看超时前的过程，不能只看导出堆栈的时刻；
4. 判断目标线程是在运行、等待 CPU、等待 Binder，还是等待锁；
5. Binder 等待继续看服务端，锁等待继续看持锁者；
6. 检查系统级 CPU、I/O、内存压力，避免把线程长时间得不到 CPU 误判成应用长任务。

### 进程消失

1. 查看 `ApplicationExitInfo` 的原因（`reason`）、子原因（`subreason`）与说明（`description`）；
2. 对齐 `am_kill`、`am_proc_died`、`lmkd` 日志和进程 ID 的生命周期；
3. 查看终止前的 `adj`、`procState`、常驻内存集（RSS）、交换空间（swap）与系统内存压力；
4. 区分 AMS 主动清理、`lmkd`、崩溃、ANR 后退出、用户停止和 Android 17 的内存限制器（MemoryLimiter）；
5. 不要把“最后一次记录的 `adj` 是 900+”当作终止原因，它只表示进程当时受到的保护较弱。

---

## 常见误区

### “ANR 就是主线程卡 5 秒”

5 秒是输入分发的常见默认值。广播、Service、`JobScheduler`、`shortService` 类型 FGS 和 ContentProvider 各有自己的触发条件，部分场景甚至不会产生 ANR。

### “看到 `am_proc_bound` 就说明应用启动完成”

它只表示 AMS 接受了新进程的应用线程连接。`bindApplication`、`Application.onCreate()`、Activity 创建和首帧都可能还没发生。

### “看到 `am_kill` 就说明进程由 `lmkd` 终止”

`am_kill` 是 AMS 主动终止进程时写入的 EventLog。判断是否由 `lmkd` 回收，需要结合 `lmkd` 证据、进程死亡事件与退出信息。

### “前台 Service 不会被终止”

FGS 提高进程重要性，但不提供绝对存活保证。它还受启动权限、服务类型、运行额度、用户停止、ANR、崩溃和内存压力约束。

### “静态广播一定会启动应用进程”

只有广播动作、`AndroidManifest.xml` 声明、导出与权限设置、后台执行限制和系统策略都允许时，广播才可能创建应用进程。Android 8 之后的隐式广播限制是判断前提。

### “`recreateOnConfigChanges` 是通用重启开关”

它只对列出的配置标志生效。Android 17 扩大了适用范围，但与 `configChanges` 同时声明同一项时不会重建。

---

## 源码阅读入口

### 进程与优先级

- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/Constants.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java`

### Activity 与启动

- `frameworks/base/core/java/android/app/Instrumentation.java`
- `frameworks/base/core/java/android/app/ActivityThread.java`
- `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java`
- `frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java`
- `frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java`
- `frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java`
- `frameworks/base/services/core/java/com/android/server/wm/Task.java`
- `frameworks/base/core/java/android/app/ApplicationStartInfo.java`

### ANR、Service、Broadcast 与 ContentProvider

- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java`
- `frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java`
- `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java`
- `frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java`
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
- `frameworks/base/services/core/java/com/android/server/wm/AnrController.java`

以上路径均以 `android-17.0.0_r1` 为准。

## 官方资料

- [Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android 14 behavior changes: all apps](https://developer.android.com/about/versions/14/behavior-changes-all)
- [Android 16 behavior changes: all apps](https://developer.android.com/about/versions/16/behavior-changes-all)
- [Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [Android 17 background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [`ApplicationStartInfo.getStartComponent()`](https://developer.android.com/reference/android/app/ApplicationStartInfo#getStartComponent())
- [`android:recreateOnConfigChanges`](https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges)
- [Perfetto SQL standard library: monitor contention](https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention)
