---
title: ActivityManager 组件调度、进程优先级与锁模型
chapter: '1.12'
section: '1.12'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-17'
last_verified_against: AOSP android-17.0.0_r1 + Android Developers + Perfetto
confidence: high
sources:
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/Constants.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActiveServices.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/AnrHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/Task.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/InputManagerCallback.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/AnrController.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/Instrumentation.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ApplicationStartInfo.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/ContentResolver.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/InputConstants.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/res/res/values/attrs_manifest.xml @ android-17.0.0_r1
- type: aosp
  path: frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp @ android-17.0.0_r1
- type: official
  path: https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/timeout
- type: official
  path: https://developer.android.com/about/versions/14/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/release-notes
- type: official
  path: https://developer.android.com/about/versions/17/changes/bg-audio
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationStartInfo#getStartComponent()
- type: official
  path: https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention
- type: research
  path: DeepResearch/2026-06-10-lru-lock-optimization.md
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java (android-12.0.0_r1, android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/ActivityManagerProcLock.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/ActivityManagerGlobalLock.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/ProcessList.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/ThreadPriorityBooster.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/core/java/android/os/PerfettoCategories.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/core/java/android/app/LoadedApk.java (android-17.0.0_r1)
- type: aosp
  path: platform/frameworks/base/core/java/android/app/IApplicationThread.aidl (android-17.0.0_r1)
- type: official-docs
  path: https://perfetto.dev/docs/analysis/stdlib-docs#android-monitor_contention
- type: official
  path: developer.android.com/guide/components/activities/process-lifecycle
- type: official
  path: source.android.com/docs/core/perf/lmkd
- type: official
  path: source.android.com/docs/core/perf/cached-apps-freezer
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/ProcessStateController.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/Constants.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/psc/ProcStateController.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessList.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityManager.java (android-17.0.0_r1)
- type: aosp
  path: frameworks/base/core/java/android/os/PerfettoCategories.java (android-17.0.0_r1)
- type: aosp
  path: system/memory/lmkd/include/lmkd.h (android-17.0.0_r1)
- type: aosp
  path: system/memory/lmkd/lmkd.cpp (android-17.0.0_r1)
- type: kernel
  path: include/trace/events/oom.h (android17-6.18-2026-06_r6)
tags:
- ams
- activity-manager
- process-lifecycle
- anr
- service-management
- broadcast
- content-provider
- lock-contention
- system-server
- process-record
- dual-lock
- LOSP
- LSP
- OomAdjuster
- performance
- oom
- oom_score_adj
- process_state_controller
- process_priority
- lmkd
- freezer
- AMS
related_chapters:
- '1.1'
- '1.9'
- '1.15'
- '1.14'
- '1.19'
- '4.3'
- '5.3'
- '8.1'
- '8.2'
- '1.8'
- '1.10'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/1.68-android17-activitymanager-architecture-performance.md
- src/part1-fundamentals/ch01-architecture/08-activity-manager.md
- src/part1-fundamentals/ch01-architecture/25-ams-dual-lock-system-server-contention.md
- src/part1-fundamentals/ch01-architecture/34-oomadjuster-process-priority-performance.md
---

# ActivityManager 组件调度、进程优先级与锁模型

活动管理服务（ActivityManagerService，AMS）负责在系统侧协调应用组件与进程生命周期。它不渲染界面，也不直接执行应用代码；它记录“哪个进程承载哪些组件、当前有多重要、某次组件调用是否按时完成”，并协调相应模块创建进程、调度组件和记录异常。

分析冷启动、进程被终止、Service 卡住或广播导致的应用无响应（ANR）时，AMS 的记录常用来把系统事件与应用调用栈对应起来。排查时应先确认：

1. 谁发起了操作；
2. 系统把操作投递给了哪个进程和线程；
3. 计时从哪里开始、由什么回调结束；
4. 超时后发生的是 ANR、异常、进程清理，还是普通的等待失败。

当前源码基线为 Android 开源项目（AOSP）`android-17.0.0_r1`。Android 10～16 只用于解释版本演进。

---

AMS 既维护组件和进程状态，也参与启动、回收、ANR 与调度组更新。分析 system_server 延迟时，需要把业务状态变化、锁等待和 OomAdjuster 计算放在同一条因果线上。

## 进程管理的主路径

### AMS、ATMS 与 WMS 的分工

这三个服务都运行在承载核心系统服务的 `system_server` 进程中，但职责不同：

| 服务 | 主要职责 | 分析时常见入口 |
|---|---|---|
| AMS | 进程、Service、广播、ContentProvider、ANR、崩溃、进程重要性 | `ActivityManagerService`、`ProcessList`、`ActiveServices`、`BroadcastQueueImpl` |
| Activity 任务管理服务（ATMS） | Activity 启动、任务（Task）选择、前后台切换、启动模式 | `ActivityTaskManagerService`、`ActivityStarter`、`ActivityRecord` |
| 窗口管理服务（WMS） | 窗口容器、焦点、可见性、输入窗口状态 | `RootWindowContainer`、`DisplayContent`、`AnrController` |

`Instrumentation.execStartActivity()` 直接调用 `ActivityTaskManager.getService().startActivity()`。“启动 Activity 都由 AMS 完成”是旧版实现的说法。现代 Android 中，ATMS 先决定 Activity 应放进哪个任务；只有目标进程不存在时，才请求 AMS/`ProcessList` 创建进程。

AMS 通过 `IActivityManager` Binder 接口接受跨进程请求。请求通常先由 `Binder:system_server_*` 线程接收，随后在持锁代码段内、`Handler` 上或其他系统线程中继续处理。不要把名为 `ActivityManager` 的线程理解成唯一的 AMS 主线程，也不要把 Binder 线程池数量写成固定值：线程池上限和实际线程数都可能随系统构建及运行状态变化。

#### Perfetto 中先看什么

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

### 进程重要性：`procState` 与 `oom_score_adj`

Android 不只把进程分为“前台”和“后台”。AMS 会综合 Activity 可见性、正在执行的 Service、ContentProvider 依赖、BroadcastReceiver、Binder 绑定关系等信息，计算进程状态和内存回收优先级。

这两个概念需要分开：

- 进程状态 `procState` 描述进程当前负责的工作，供调度、后台限制和权限判断使用；
- 内存不足调整分数 `oom_score_adj` 供内存回收使用。值越大，通常越早成为回收候选。

两者相关，但不是固定的一一对应关系。同一个进程也可能同时承载 Activity、Service 和 ContentProvider，最终重要性取决于所有依赖关系中最强的保护条件。

#### Android 17 的关键 `adj` 档位

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

表中数值是源码常量，但每种组件不一定永远落在同一行。Android 17 还可以通过功能开关（feature flag）对可见进程和上一个应用（previous app）分配更细的档位。`TOP_SLEEPING` 也是计算分支中的调整类型 `adjType`，不能把它当成独立常量档位。

前台 Service 的 `adj` 同样不是“永远 100”。在当前固定源码版本中，常规的非 `shortService` 类型 FGS 通常受 `PERCEPTIBLE_APP_ADJ = 200` 保护；刚从顶层应用进入 FGS 的进程可在宽限期内使用 50。它仍可能在极端内存压力、异常或用户停止服务时退出。

#### AMS 如何把分数交给 `lmkd`

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

### 冷启动中的 AMS

#### 从点击图标到应用主线程

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

#### 一次可靠的启动分析

冷启动至少应对齐这些时刻：

1. 启动请求发出；
2. `am_proc_start`；
3. Zygote 创建进程与新进程出现；
4. `ActivityThread.main()`、`attachApplication`、`bindApplication`；
5. `Application.onCreate()`；
6. Activity 生命周期；
7. 首帧提交与显示。

只计算 `am_proc_start` 到 `am_proc_bound`，得到的是进程创建和应用线程连接（attach）耗时的一部分，不能代表用户感知的启动时间。

Android 15（API 35）引入 `ApplicationStartInfo`，Android 16（API 36）又增加 `getStartComponent()`。后者可以区分进程由 Activity、Service、BroadcastReceiver、ContentProvider 还是其他组件拉起：

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

这段代码可用于启动诊断，并按启动组件走不同的初始化路径。`getReason()` 提供更细的启动原因，`getStartComponent()` 则直接区分四类应用组件。

---

### ANR：先找计时器，再看阻塞点

应用无响应（Application Not Responding，ANR）并不等于统一的“主线程卡 5 秒”。不同系统模块在投递工作时各自开始计时，结束计时所等待的回调也不同。

| 场景 | Android 17 AOSP 基础值 | 计时结束条件 |
|---|---:|---|
| 输入分发（Input dispatch） | 通常 5 秒 | 目标窗口及时处理输入，或焦点问题解除 |
| 前台优先级广播 | 10 秒基础值 | 同步 `onReceive()` 返回，或异步 `PendingResult.finish()` 被调用 |
| 后台优先级广播 | 60 秒基础值 | 同上 |
| 前台进程中的 Service 回调 | 20 秒基础值 | 对应 Service 执行回调完成 |
| 后台进程中的 Service 回调 | 200 秒基础值 | 对应 Service 执行回调完成 |

这些值不是 API 约定，不保证跨设备一致。AOSP 会乘以 `Build.HW_TIMEOUT_MULTIPLIER`，设备厂商也可能调整。Android 14 及以上版本的广播计时还会为长时间得不到 CPU 的进程延长窗口：官方诊断文档给出的范围是前台优先级 10～20 秒、后台优先级 60～120 秒。

#### 输入 ANR

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

第二种情况不一定是某个 `onTouchEvent()` 太慢。首帧迟迟没有建立窗口、窗口带有“不接受焦点”标志 `FLAG_NOT_FOCUSABLE`，或焦点切换在 WMS 中长时间未完成，都可能触发它。

排查时先看应用主线程状态：

- 长时间运行（Running）：检查长任务与热点代码；
- 长时间可运行（Runnable）却得不到 CPU：检查 CPU 争用和系统负载；
- 睡眠（Sleeping）且在等待 Binder：沿 Binder 响应找到服务端；
- 睡眠且在等待锁：找到持锁线程；
- 主线程已经空闲：堆栈可能采集得太晚，需要查看 ANR 发生前的跟踪数据。

#### 广播 ANR

Android 17 中，AMS 创建前台与后台两套 `BroadcastConstants`。`ActivityManagerService` 给它们设置 10 秒和 60 秒基础超时，`BroadcastQueueImpl.dispatchReceivers()` 在向目标进程调度广播接收器时启动 `BroadcastAnrTimer`。

计时边界如下：

- 广播进入系统队列的时刻，不等于 ANR 计时开始；
- 创建冷进程所花的时间会占用接收器的执行时间；
- 同步接收器在 `onReceive()` 返回时完成；
- 调用 `goAsync()` 后，必须由 `PendingResult.finish()` 结束本次投递。

`FLAG_RECEIVER_FOREGROUND` 决定这里的“前台优先级广播”。它不表示接收进程中一定有前台 Activity。

#### Service 执行 ANR

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

##### `startForegroundService()` 的前台提升使用另一套计时器

调用 `startForegroundService()` 后没有及时调用 `Service.startForeground()`，会触发“未及时提升为前台服务”的超时路径。`android-17.0.0_r1` 中：

- `DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS` 为 30 秒；
- 超时后 `DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS` 再给 10 秒延迟；
- `ActiveServices.serviceForegroundTimeout()` 创建超时记录，随后进入 ANR 处理。

这组数值是 Android 17 固定源码版本中的默认实现，不能反推为所有 Android 版本和所有设备都保证 30+10 秒。开发应用时，仍应在 `onCreate()` 中立即建立通知并调用 `startForeground()`，不要把任何超时值当作可用工作时间。

它也不同于 Android 15 起按前台服务类型计算的总运行时长限制。后者到期会调用 `Service.onTimeout(int, int)`，未及时停止时产生 `RemoteServiceException`；这不属于 Service 执行 ANR。

#### ContentProvider：三种等待对应三种结果

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

#### ANR 数据是怎样保存的

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

### Activity 与任务的现行容器模型

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

#### Android 17 减少了部分配置变化触发的重建

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

### Service 与前台服务的版本边界

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

可延迟、可重试的工作优先考虑 `JobScheduler` 或 `WorkManager`；用户发起的数据传输可评估 user-initiated data transfer job（用户发起的数据传输任务）；持续媒体播放更适合使用 Media3 的 `MediaSessionService`。选择依据是任务含义和约束，不能把所有 FGS 一律替换成 WorkManager。

#### AMS 全局锁竞争

`ActivityManagerService.startService()` 在 Android 17 中没有给整个 Java 方法加 `synchronized`。它完成调用者检查后才进入以下同步代码块：

```java
synchronized (mGlobalLock) {
    res = mServices.startServiceLocked(...);
}
```

`ActiveServices` 方法名中的 `...Locked()` 表示调用者应持有 AMS 全局锁，不代表存在一个独立的“`mServices` 锁”。

`realStartServiceLocked()` 还会在这段受锁保护的代码中向应用发送 `IApplicationThread.scheduleCreateService()`；这是单向异步（oneway）Binder 调用，但 Binder 驱动排队、系统负载和执行时间较长的持锁代码段（临界区）仍可能增加其他线程的锁等待时间。

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

### Android 17 的广播调度

这里仅说明广播怎样进入 AMS 的组件调度与进程状态链。队列选择、冷启动槽位、优先级传播、超时与可观测性的完整模型见 [1.14 BroadcastQueue 进程级调度与广播性能边界](14-broadcastqueue-scheduling-performance.md)。

#### 按进程组织的队列

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

#### 清单注册与运行时注册的接收器

- 清单注册的接收器（Manifest Receiver）可以在规则允许时创建尚未运行的应用进程，因此可能把冷启动时间计入广播执行时间；
- 运行时注册的接收器（context-registered Receiver）只在注册对象有效时接收，不会为了已经失效的注册关系单独创建进程；
- 从 Android 8 开始，清单中的隐式广播受到广泛限制，并非任意静态接收器都能被系统事件唤醒；
- 目标版本为 Android 14 及以上的应用注册并非仅接收系统广播的接收器时，要显式使用 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`。

#### Android 14 及以上版本的缓存态广播

Android 14 起，应用处于缓存态（cached state）时，系统可以暂存发给运行时注册接收器的广播，等应用离开缓存态后再投递；某些重复广播还可能被合并。发给清单注册接收器的广播不使用这套排队方式，系统可先让应用离开缓存态再投递。

这会改变系统跟踪数据的解释：

- “广播发送后很久才进入 `onReceive()`”可能是系统按设计暂存了缓存态广播，不一定是 AMS 卡住；
- 清单注册的接收器仍可能触发进程启动。判断大量进程集中启动的原因时，要结合隐式广播限制和具体广播动作（`action`）；
- 接收器 ANR 的计时从 `BroadcastQueueImpl` 调度目标接收器时开始，不从广播发送时开始。

---

### 三个常用排查模板

#### 冷启动慢

1. 用启动请求或 `ApplicationStartInfo.START_TIMESTAMP_LAUNCH` 确定起点；
2. 查看 `am_proc_start` 到创建进程（fork）的时间，判断 `system_server`/Zygote 阶段；
3. 查看新进程出现到 `bindApplication` 的时间，判断运行时初始化与进程连接 AMS 的阶段；
4. 查看 `Application.onCreate()`、ContentProvider 安装和 Activity 生命周期；
5. 查看渲染线程 `RenderThread`、首帧提交和系统合成服务 SurfaceFlinger 的显示时刻；
6. 用 `getStartComponent()` 确认是哪个组件拉起了进程。

#### ANR

1. 从 ANR 主题（subject）或 `am_anr.msg` 确认类型；
2. 按类型找到计时器的开始点与结束回调；
3. 查看超时前的过程，不能只看导出堆栈的时刻；
4. 判断目标线程是在运行、等待 CPU、等待 Binder，还是等待锁；
5. Binder 等待继续看服务端，锁等待继续看持锁者；
6. 检查系统级 CPU、I/O、内存压力，避免把线程长时间得不到 CPU 误判成应用长任务。

#### 进程消失

1. 查看 `ApplicationExitInfo` 的原因（`reason`）、子原因（`subreason`）与说明（`description`）；
2. 对齐 `am_kill`、`am_proc_died`、`lmkd` 日志和进程 ID 的生命周期；
3. 查看终止前的 `adj`、`procState`、常驻内存集（RSS）、交换空间（swap）与系统内存压力；
4. 区分 AMS 主动清理、`lmkd`、崩溃、ANR 后退出、用户停止和 Android 17 的内存限制器（MemoryLimiter）；
5. 不要把“最后一次记录的 `adj` 是 900+”当作终止原因，它只表示进程当时受到的保护较弱。

---

### 源码阅读入口

#### 进程与优先级

- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/Constants.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java`
- `frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java`

#### Activity 与启动

- `frameworks/base/core/java/android/app/Instrumentation.java`
- `frameworks/base/core/java/android/app/ActivityThread.java`
- `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java`
- `frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java`
- `frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java`
- `frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java`
- `frameworks/base/services/core/java/com/android/server/wm/Task.java`
- `frameworks/base/core/java/android/app/ApplicationStartInfo.java`

#### ANR、Service、Broadcast 与 ContentProvider

- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java`
- `frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java`
- `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java`
- `frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java`
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`
- `frameworks/base/services/core/java/com/android/server/wm/AnrController.java`

以上路径均以 `android-17.0.0_r1` 为准。

### 官方资料

- [Diagnose and fix ANRs](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Foreground service timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android 14 behavior changes: all apps](https://developer.android.com/about/versions/14/behavior-changes-all)
- [Android 16 behavior changes: all apps](https://developer.android.com/about/versions/16/behavior-changes-all)
- [Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [Android 17 background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [`ApplicationStartInfo.getStartComponent()`](https://developer.android.com/reference/android/app/ApplicationStartInfo#getStartComponent())
- [`android:recreateOnConfigChanges`](https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges)
- [Perfetto SQL standard library: monitor contention](https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention)


## system_server 锁模型与竞争

AMS 的状态变化会触发多组共享结构更新。调用落到 system_server 后，应先确认持锁范围、锁顺序和 Binder 回调是否把局部操作放大为全局等待。

`ActivityManagerService`（AMS）处在 Android 进程管理的中心。进程启动和退出、组件状态、LRU（最近最少使用）次序、OOM adj（进程回收优先级分值）、应用冻结等操作，都可能在 `system_server` 内并发发生。只用一把大锁保护这些状态，代码容易保持一致，却会让互不修改同一组数据的线程排在同一个等待队列中。

Android 12 引入 `mProcLock`，并保留原有的 `mGlobalLock`。Android 17 仍采用这套双锁设计。双锁扩大了部分进程状态读取和独立操作的并发空间，但没有把 AMS 的所有进程管理操作改成只持 `mProcLock`。OOM adj 全量计算、LRU 写入等关键路径仍会同时持有两把锁。

### 1. 从单锁到双锁

Android 11 的 AMS 尚未定义 `ENABLE_PROC_LOCK`、`mProcLock` 和 `ActivityManagerProcLock`。当时进程管理代码广泛依赖 AMS 对象自身的 Java monitor，也就是 `synchronized` 使用的对象锁；这把锁后来称为 `mGlobalLock`。

Android 12 的 `ActivityManagerService` 首次给出完整的双锁骨架：

```java
final ActivityManagerGlobalLock mGlobalLock = ActivityManagerService.this;

private static final boolean ENABLE_PROC_LOCK = true;

final ActivityManagerGlobalLock mProcLock = ENABLE_PROC_LOCK
        ? new ActivityManagerProcLock() : mGlobalLock;
```

这段代码说明了两件事：

1. `mGlobalLock` 仍然是 `ActivityManagerService.this`，旧代码中的 `synchronized (mService)`、`synchronized (this)` 与围绕全局锁建立的约束不会凭空消失。
2. `ENABLE_PROC_LOCK` 为 `false` 时，`mProcLock` 会指回 `mGlobalLock`。这种写法让迁移过程可以维持相同的接口和方法命名；Android 12 与 Android 17 的发布源码中该开关均为 `true`。

双锁要解决的是锁保护范围过宽，并不保证每条路径都更快。一次操作若要同时读取组件关系并修改进程状态，仍然需要两把锁；持锁期间若执行耗时的 Binder 调用、文件 I/O 或大量计算，也仍会造成竞争。

### 2. 两把锁分别保护什么

Android 17 在 `ActivityManagerService` 的注释中给出了边界：Service、Provider、Broadcast 等核心组件状态仍主要由 `mGlobalLock` 保护；进程管理状态逐步迁移到 `mProcLock`。源码中的锁要求如下。

| 锁要求 | 典型数据或操作 | 说明 |
|---|---|---|
| 只持 `mGlobalLock` | Service、Provider、Broadcast 的大量核心状态 | 方法常使用 `Locked` 后缀；已经持有 `mProcLock` 时不能反向获取 |
| 只持 `mProcLock` | 部分进程状态读取、应用冻结/压缩队列、向运行进程分发某些通知 | 这类路径不需要访问由全局锁单独保护的组件关系 |
| 两把锁都持有 | LRU 列表写入、OOM adj 计算及提交、跨组件关系更新进程状态 | 获取顺序固定为 `mGlobalLock` → `mProcLock` |
| 任一把锁均可读取 | 使用 `@CompositeRWLock` 保护的数据，例如 `mLruProcesses` | “任一把锁可读”不表示任一把锁都可写 |

这里的“进程状态”也不能简单理解成 `ProcessRecord` 的全部字段。`ProcessRecord` 聚合了 Activity、Service、Provider、错误状态、优化状态等多个子记录，各字段的锁注解并不相同。判断某段代码能否只持 `mProcLock`，应查看字段与方法上的 `@GuardedBy`、`@CompositeRWLock` 注解，不能只看对象类型。

### 3. `@CompositeRWLock`：任一锁读、两把锁写

`ProcessList` 中的 LRU 列表是双锁语义最清楚的例子：

```java
@CompositeRWLock({"mService", "mProcLock"})
private final ArrayList<ProcessRecord> mLruProcesses = new ArrayList<>();

@CompositeRWLock({"mService", "mProcLock"})
private int mLruProcessActivityStart = 0;

@CompositeRWLock({"mService", "mProcLock"})
private int mLruProcessServiceStart = 0;
```

`@CompositeRWLock` 表达一套组合读写规则：

- 读取时，持有 `mService`（即 AMS 全局锁）或 `mProcLock` 中的任意一把即可。
- 写入时，两把锁都要持有。

因此，下面的遍历方法可以由只持 `mProcLock` 的调用方使用：

```java
@GuardedBy(anyOf = {"mService", "mProcLock"})
void forEachLruProcessesLOSP(boolean iterateForward,
        @NonNull Consumer<ProcessRecord> callback) {
    if (iterateForward) {
        for (int i = 0, size = mLruProcesses.size(); i < size; i++) {
            callback.accept(mLruProcesses.get(i));
        }
    } else {
        for (int i = mLruProcesses.size() - 1; i >= 0; i--) {
            callback.accept(mLruProcesses.get(i));
        }
    }
}
```

这段方法只遍历列表，没有改变元素和分区索引。调用方仍要持有两把锁中的一把，传入的回调也不能修改受组合写锁保护的数据。

LRU 写路径的要求更严格。Android 17 的 `updateLruProcessLocked()` 已由 `@GuardedBy("mService")` 约束，随后在内部获取 `mProcLock`，再调用 `updateLruProcessLSP()`：

```java
@GuardedBy("mService")
public void updateLruProcessLocked(ProcessRecordInternal appInternal,
        boolean activityChange, ProcessRecordInternal clientInternal) {
    // 省略无需写入时的快速返回
    synchronized (mProcLock) {
        updateLruProcessLSP(app, client, hasActivity, hasService);
    }
}

@GuardedBy({"mService", "mProcLock"})
private void updateLruProcessLSP(...) {
    // 修改 mLruProcesses 和分区索引
}
```

双锁允许 LRU 读取避开全局锁，但 LRU 排序、插入和删除仍要同时保护列表结构与关联状态。

### 4. 方法后缀是锁契约的速记

AMS 进程管理代码用方法名后缀提示调用方需要持有什么锁。

| 后缀 | 源码中的含义 | 调用要求 |
|---|---|---|
| `LOSP` | Locked with any Of global am Service or Process lock | 持有 `mGlobalLock` 或 `mProcLock` 中任意一把 |
| `LSP` | Locked with both global am Service and Process lock | 同时持有两把锁 |
| `Locked` | Locked with global AM service lock alone | 通常要求持有 `mGlobalLock`；仍需结合注解确认 |
| `LPr` | Locked with Process lock alone | 持有 `mProcLock` |

后缀是维护约定，字段访问器等方法不一定都带后缀。代码审查时应按“注解优先、后缀辅助、调用点复核”的顺序判断。

例如，`updateOomAdjLocked()` 的名称只提示入口已经持有全局锁。它进入方法后还会获取 `mProcLock`，再调用 `updateOomAdjLSP()`。仅凭 `Locked` 后缀推断整个调用过程只使用一把锁，会漏掉内部的嵌套锁。

### 5. 锁顺序：先全局锁，再进程锁

Android 17 在 `mProcLock` 的字段注释中明确要求：需要两把锁时，先获取 `mGlobalLock`，再获取 `mProcLock`。Service、Provider、Broadcast 等代码仍可能只由全局锁保护，因此持有进程锁后再请求全局锁会形成 AB-BA 死锁条件：一个线程按 A→B 取锁，另一个线程按 B→A 取锁，两者可能互相等待。

符合顺序的写法如下：

```java
synchronized (mGlobalLock) {
    // 读取或修改全局组件状态
    synchronized (mProcLock) {
        // 修改需要组合写锁保护的进程状态
    }
}
```

退出嵌套块时按相反顺序释放锁。这是 Java `synchronized` 的自然行为。

下面的顺序不允许出现在可达路径中：

```java
synchronized (mProcLock) {
    synchronized (mGlobalLock) { // 锁顺序反转
        // ...
    }
}
```

只持 `mProcLock` 的方法若发现还需要全局状态，通常应退出当前临界区，再从满足全局锁契约的入口重新组织操作。不能为了少改代码而在原地反向加锁。

### 6. 三条代表性路径

#### 6.1 OOM adj：Android 17 仍同时持有两把锁

Android 17 已将 OOM 调整实现移到 `com.android.server.am.psc.OomAdjuster`。全量更新入口的锁关系如下：

```java
@GuardedBy("mServiceLock")
void updateOomAdjLocked(@OomAdjReason int oomAdjReason) {
    synchronized (mProcLock) {
        updateOomAdjLSP(oomAdjReason);
    }
}

@GuardedBy({"mServiceLock", "mProcLock"})
private void updateOomAdjLSP(@OomAdjReason int oomAdjReason) {
    performUpdateOomAdjLSP(oomAdjReason);
}
```

`performUpdateOomAdjLSP()`、`updateAndTrimProcessLSP()` 等后续方法也标注为同时受两把锁保护。双锁没有让一次完整的 OOM adj 更新与所有 AMS 全局操作并行。它提供的收益之一，是让只需读取或修改独立进程状态的其他路径可以绕开全局锁等待。

分析性能时必须保留这项边界。若系统轨迹显示 OOM adj 期间 `mGlobalLock` 长时间被持有，不能因为双锁已经启用就排除 OOM adj；仍需查看持锁线程在计算、Binder 调用、内核调度和 I/O 上分别花了多少时间。

#### 6.2 时区更新：只用进程锁遍历 LRU

时区变化需要通知正在运行的应用进程。Android 17 的 AMS `Handler`（消息队列处理器）只获取 `mProcLock`，然后通过 `forEachLruProcessesLOSP()` 读取 LRU 列表：

```java
case UPDATE_TIME_ZONE: {
    synchronized (mProcLock) {
        mProcessList.forEachLruProcessesLOSP(false, app -> {
            final IApplicationThread thread = app.getThread();
            if (thread != null) {
                try {
                    thread.updateTimeZone();
                } catch (RemoteException ignored) {
                }
            }
        });
    }
} break;
```

该路径展示了 `LOSP` 的作用：读取 LRU 不必占用 `mGlobalLock`。风险在于，代码会在 `mProcLock` 内向多个应用进程发起 Binder 调用。即使这些调用通常只发送请求、不等待应用返回结果，也要通过系统轨迹判断临界区是否因调度、Binder 驱动拥塞或目标进程状态而延长。

#### 6.3 CachedAppOptimizer：进程锁保护冻结与压缩队列

Android 17 的 `CachedAppOptimizer` 使用 `mProcLock` 保护 `mPendingCompactionProcesses`、`mFrozenProcesses` 和冻结器相关状态。这里的压缩是回收或整理缓存进程内存的 compaction 操作。典型代码会在锁内复制 PID 或移出一个待压缩进程，再在锁外执行较慢的工作。

这种写法体现了缩短临界区的常用方法：锁内完成一致性检查和最小状态变更，耗时操作使用局部副本在锁外继续。能否这样处理取决于对象生命周期与并发修改规则，不能机械地把现有代码移出锁外。

### 7. `ActivityManagerProcLock` 与线程优先级提升

`ActivityManagerProcLock` 是一个没有字段和方法的标记类：

```java
final class ActivityManagerProcLock implements ActivityManagerGlobalLock {
}
```

源码注释说明，这个独立类型可让线程优先级提升器识别临界区。Android 17 中可以直接验证的实现是 `ThreadPriorityBooster`：AMS 分别为全局锁和进程锁创建一个提升器，目标优先级都是 `THREAD_PRIORITY_FOREGROUND`。

`ThreadPriorityBooster.boost()` 会读取当前线程的 Linux nice 值；nice 是普通调度策略下的线程优先级参数。若当前优先级低于目标值，它会通过 `setThreadPriority()` 提升当前线程。嵌套临界区由线程局部计数器记录，退出最外层临界区时恢复原优先级。

这段源码支持的结论有三点：

- 提升对象是当前持锁线程，不是整个 `system_server` 进程中的所有线程。
- 调整的是 Linux nice 优先级，目标为前台线程优先级。
- 退出最外层临界区后恢复先前优先级。

它不能证明系统会为该锁直接提高 CPU 频率，也不能证明持锁线程会切换到 `SCHED_FIFO` 先进先出实时调度策略。AMS 中的 `mUseFifoUiScheduling` 面向界面线程和渲染线程（RenderThread），属于另一套调度策略，不应与 `mProcLock` 的优先级提升混为一谈。

优先级提升只能降低持锁线程因普通优先级竞争而延迟的概率。临界区内若有耗时的 Binder 调用、缺页、I/O 或过量计算，`ThreadPriorityBooster` 不会消除这些等待。

### 8. 用 Perfetto 区分等待时间与持锁时间

锁问题至少涉及等待线程和持锁线程。`futex` 是 Linux 用户态同步原语在内核中的等待机制；只看到 Binder 线程处于 `futex` 等待，无法确定是哪把锁造成延迟，也无法判断持锁线程为何没有及时释放。

Android 17 的 `ActivityManagerService` 定义了 `big_locks` 类别下的四组事件：

| 锁 | 尝试获取 | 已获取并持有 |
|---|---|---|
| `mGlobalLock` | `ams_lock_acquire` | `ams_lock_held` |
| `mProcLock` | `proc_lock_acquire` | `proc_lock_held` |

这些事件受 `android.os.Flags.perfettoSdkTracingV3()` 控制。分析某台设备前，应确认系统构建是否启用相应特性、系统轨迹配置是否采集 `big_locks` 类别，以及结果中是否出现这些区间。源码定义了事件，不代表每份系统轨迹都包含它们。

如果事件存在，可以先用下面的查询列出 `system_server` 中的持锁区间。它的用途是找到长持锁段，并定位到具体线程：

```sql
SELECT
  s.ts,
  s.dur / 1e6 AS dur_ms,
  s.name,
  t.tid,
  t.name AS thread_name
FROM slice s
JOIN thread_track tt ON tt.id = s.track_id
JOIN thread t USING (utid)
JOIN process p USING (upid)
WHERE p.name = 'system_server'
  AND s.category = 'big_locks'
  AND s.name IN ('ams_lock_held', 'proc_lock_held')
ORDER BY s.dur DESC;
```

`*_lock_acquire` 是尝试获取锁时发出的瞬时事件，`*_lock_held` 是成功获取后开始的持锁区间。二者位于同一线程轨道时，可以在界面中直接观察等待与持锁的先后关系。查询结果为空时，再使用 ART 的 Java monitor 竞争数据作为通用证据。

Perfetto 当前标准库的模块名为 `android.monitor_contention`，表名为 `android_monitor_contention`。monitor contention 指多个线程争用同一个 Java 对象锁。下面的查询使用现有列名列出 `system_server` 中的这类竞争：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  dur / 1e6 AS blocked_ms,
  blocked_thread_name,
  blocking_thread_name,
  lock_name,
  short_blocked_method,
  short_blocking_method,
  blocked_src,
  blocking_src,
  waiter_count
FROM android_monitor_contention
WHERE process_name = 'system_server'
  AND (
    lock_name GLOB '*ActivityManager*'
    OR short_blocked_method GLOB '*ActivityManager*'
    OR short_blocked_method GLOB '*OomAdjuster*'
    OR short_blocking_method GLOB '*ActivityManager*'
    OR short_blocking_method GLOB '*OomAdjuster*'
    OR short_blocking_method GLOB '*ProcessList*'
  )
ORDER BY dur DESC
LIMIT 50;
```

`dur` 是等待线程被 Java monitor 阻塞的墙钟时间，也就是从等待开始到重新获得执行机会所经过的实际时间。`blocking_thread_name` 与 `short_blocking_method` 指向持锁方，`blocked_thread_name` 与 `short_blocked_method` 指向等待方。

`lock_name` 可用时，优先用它区分 `ActivityManagerService` 对象和 `ActivityManagerProcLock` 对象；类名缺失时，再结合源码位置与 `big_locks` 事件判断。仅凭方法属于 `OomAdjuster` 或 `ProcessList` 来猜测锁类型并不可靠，因为这些类中存在同时持有两把锁的路径。

### 9. 一次可复用的诊断顺序

遇到 Activity 启动、Service 调用或进程状态更新偶发变慢时，可以按以下顺序分析：

1. 在问题时间窗内找到等待线程，确认延迟来自 Java monitor 竞争，而非等待 Binder 回复、CPU 可运行态排队、I/O 或其他原因。
2. 查看 `big_locks` 事件或 `android_monitor_contention.lock_name`，区分全局锁与进程锁。
3. 找到持锁线程及其持锁方法。等待方的调用栈只能说明谁受影响，持锁方才说明临界区为何变长。
4. 把持锁区间与线程状态、Binder 事务、调度和 I/O 区间对齐。持锁线程可能正在运行，也可能在持锁期间等待另一个资源。
5. 检查同一时段的 `waiter_count`（等待者数量）和其他等待线程。一次长等待与许多中等等待造成的总影响不同。
6. 回到对应 Android 版本的源码，确认锁注解、获取顺序和版本差异，再决定修改位置。

`adb shell dumpsys activity processes` 可以查看当时的进程、adj 与进程状态（proc state），但它只是一份状态快照，不能证明某个 adj 变化导致了锁竞争。复现性能问题时，应把 `dumpsys` 用作背景信息，并通过系统轨迹判断时间关系与因果链。

### 10. 应用侧能做什么

普通应用不能直接选择 AMS 使用哪把锁，也无法从一次系统 API 调用推断服务端当时的持锁情况。应用侧能控制调用时机、频率和结果时效要求。

- 不要在每帧、滚动回调或高频定时器中同步查询系统进程与内存状态。一次调用可能很快，密集的跨进程调用（IPC）仍会增加客户端和 `system_server` 的调度负担。
- 缓存前要确认数据允许短时间过期。进程列表、内存压力和组件状态的时效要求不同，不能统一设置一个缓存时间。
- 将与绘制无关的系统查询移出主线程或关键交互时段。异步执行只能减少应用主线程阻塞，服务端成本仍然存在，因此还要控制调用次数。
- `ActivityManager.getRunningAppProcesses()` 是进程可见性查询，不会因为“读取列表”就刷新 LRU。`UsageStatsManager` 提供应用使用记录，语义不同，不能当作进程列表的通用替代品。
- `ServiceConnection.onServiceConnected()` 等回调在应用进程中按 `ServiceDispatcher` 配置的执行器或 `Handler` 分发。回调里发起新的系统调用可能形成新的同步 IPC，但不能据此声称 `system_server` 仍持有原来的 AMS 锁。

平台代码的优化需要遵守更严格的条件：缩短锁内工作、避免持锁进行不可控的跨进程调用、在安全时复制所需状态后释放锁，并用相同负载的系统轨迹验证等待时间和持锁时间。任何把代码移到锁外的修改，都要先证明对象生命周期与组合写锁规则仍然成立。


## 进程状态、OomAdjuster 与优先级

锁竞争解释了状态更新为什么变慢，ProcessStateController 和 OomAdjuster 则决定更新结果如何作用到 oom_adj、proc state、调度组与回收顺序。

Android 不允许应用直接决定自己的进程寿命。`system_server` 根据进程承载的 Activity、Service、BroadcastReceiver、ContentProvider 以及跨进程依赖，持续计算进程重要性；低内存终止守护进程（lmkd）在内存压力出现时，使用这份结果选择回收目标。

API 37 的实现已经迁入 `com.android.server.am.psc` 包。继续以 `com.android.server.am.OomAdjuster.java` 为源码入口，会遗漏 Android 17 的 `ProcessStateController`、批处理会话、能力传播和新的跟踪字段。

以下结论限定于 `android-17.0.0_r1` Android framework / lmkd 和 `android17-6.18-2026-06_r6` 内核跟踪点。ProcessStateController（下文简称 PSC）、应用冻结机制（freezer）、LMKD socket（套接字）和 Perfetto 行为均以该基线为准，不外推到后续主线或厂商私有实现。

### 一、进程优先级不是一个数字

OomAdjuster 每轮计算会同时产生多组结果：

| 结果 | 主要消费者 | 回答的问题 |
|---|---|---|
| `adj` / `oom_score_adj` | lmkd、内核 OOM | 内存压力下，这个进程相对有多容易被终止 |
| `procState` | AMS、网络策略、统计、应用线程 | 进程当前属于 `top`、FGS、service、cached 等哪类状态 |
| `schedGroup` | libprocessgroup / cgroup（控制组） | 进程和子进程应进入 `background`、`default`、`top-app` 等 CPU 组 |
| capability（能力位） | 后台启动、网络、CPU / freezer 等策略 | 进程当前被允许做哪些事 |

四者相关，但不是一一映射。同为 `adj=0` 的顶部 Activity、正在执行广播接收者和服务回调，可以拥有不同的 `procState` 与调度组；同为前台服务（FGS）进程状态，普通 FGS 和 short FGS（短时前台服务）也使用不同的 adj。

`oom_score_adj` 越小，进程越受保护。Android 给 AMS 管理的进程分配的 `oom_score_adj` 有效范围大部分是 `-1000..999`；`UNKNOWN_ADJ=1001` 是计算中的未定值，不会作为正常结果写给 lmkd。

### 二、Android 17 的 PSC 代码结构

#### 2.1 `ProcessStateController` 是 AMS 的统一入口

`ActivityManagerService` 创建 `ProcessStateController`，组件生命周期代码通过它提交状态变化和触发计算。主要入口包括：

- `runUpdate(proc, reason)`：更新指定进程及受影响的可达进程；
- `enqueueUpdateTarget(proc)` + `runPendingUpdate(reason)`：合并多个目标后更新；
- `runFullUpdate(reason)`：全量更新；
- `runFollowUpUpdate()`：处理有时效状态的到期；
- `startBatchSession(reason)`：在一组服务等状态变更结束后统一计算。

Controller 在每次计算前调用 `commitStagedEvents()`，把异步暂存的 Activity 等状态同步到计算视图。若批处理会话仍然开启，新请求只记录目标；会话关闭后才执行待处理更新或全量更新。

#### 2.2 `OomAdjuster` 与 `OomAdjusterImpl` 的分工

`psc/OomAdjuster.java` 是公共计算与结果应用框架，负责：

- 全量、局部、待处理、后续更新的编排；
- 防止更新过程递归进入；
- 应用 `adj`、`procState`、`schedGroup` 和能力位；
- 与 lmkd、进程组、freezer、UID 观察者和 Perfetto 交互。

`psc/OomAdjusterImpl.java` 承载 API 37 的具体策略：计算进程本地状态、遍历服务 / Provider 连接、分配 LRU 梯度和处理循环依赖。

#### 2.3 新的 `ProcStateController` 仍处于受功能开关控制的演进阶段

API 37 源码还包含基于进程图和 bucket priority queue（按优先级分桶的队列）的 `ProcStateController`。全量更新中，`OomAdjusterImpl` 只有在 `enableProcstateControllerComputation()` 开启时才调用它。

该类的 `partialUpdate()`、`evaluateProcState(ProcessEdge)`、服务 / Provider 边计算仍留有 TODO；代码注释也说明 CapabilityController 尚未完全切换到它的 `procState` 结果。因此，它代表仍在推进的新算法，不能写成 Android 17 已经完全用基于优先级队列的图遍历替换 OomAdjuster。

#### 2.4 不要为 `LSP` 臆造英文全称

API 37 用注解给出锁要求：`computeOomAdjLSP()`、`applyResultsLSP()` 等方法由 `@GuardedBy({"mServiceLock", "mProcLock"})` 保护。`updateOomAdjLocked()` 在持有 service lock 时再获取 proc lock，然后进入 LSP 方法。

源码没有把 `LSP` 定义为 “Locked Synchronized Pinned”。排障和改代码时应看 `@GuardedBy`，不要根据后缀臆造锁语义。

### 三、API 37 的 adj 分级

常量已从旧的 `ProcessList` 迁到 `psc/Constants.java`：

| 常量 | 值 | API 37 中的典型含义 |
|---|---:|---|
| `NATIVE_ADJ` | -1000 | 不由 AMS 分配 adj 的原生进程边界 |
| `SYSTEM_ADJ` | -900 | `system_server` |
| `PERSISTENT_PROC_ADJ` | -800 | 常驻系统应用 |
| `PERSISTENT_SERVICE_ADJ` | -700 | 被系统/持久进程按重要方式绑定的服务 |
| `FOREGROUND_APP_ADJ` | 0 | 顶部应用、正在执行接收者 / 服务回调等 |
| `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ` | 50 | 最近处于顶部的进程转入 FGS 后的宽限档 |
| `VISIBLE_APP_ADJ` | 100 | 可见 Activity 的起始档 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 普通 FGS、悬浮层 UI 等可感知工作 |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | 中等可感知绑定档；short FGS 使用 `225 + 1` |
| `PERCEPTIBLE_LOW_APP_ADJ` | 250 | 高于普通 service、低于可感知组件的绑定档 |
| `BACKUP_APP_ADJ` | 300 | 当前备份目标 |
| `HEAVY_WEIGHT_APP_ADJ` | 400 | 不能保存状态的重量级应用 |
| `SERVICE_ADJ` | 500 | 已启动服务的 A 档 |
| `HOME_APP_ADJ` | 600 | Home 进程 |
| `PREVIOUS_APP_ADJ` | 700 | 上一个应用的起始档 |
| `SERVICE_B_ADJ` | 800 | 较旧或高内存服务的 B 档 |
| `CACHED_APP_MIN_ADJ` | 900 | cached 区间起点 |
| `CACHED_APP_MAX_ADJ` | 999 | cached 区间终点 |

可见进程和上一个应用进程可以在功能开关开启时使用 100～199、700～799 的梯度。cached 进程则在 900～999 间按最近最少使用顺序（LRU）、有 Activity / 空进程分组和连接组重要性分配。

`CACHED_APP_LMK_FIRST_ADJ=950` 是 `ProcessList` 提交给 lmkd 的六档目标配置中的末档；源码注释称它为允许优先终止的 adj 等级。它不表示 lmkd 永远先终止所有 `adj>=950` 的进程。lmkd 还会结合当前压力级别、内存占用、swap、内存反复换入换出的抖动（thrashing）、进程类型和设备参数选择目标。

### 四、一轮 OOM adjustment（内存回收优先级调整）怎样计算

#### 4.1 计算进程自身承载的组件

全量更新会遍历 LRU 进程，并调用下面这个 API 37 方法：

```java
private void computeOomAdjLSP(
        ProcessRecordInternal app,
        ProcessRecordInternal topApp,
        boolean doingAll,
        long now)
```

它不再接收旧实现里的 `cachedAdj`、`cycleReEval` 或 `computeClients` 参数。方法先根据进程自身状态计算初值，常见分支如下：

| 进程当前工作 | 初始 adj | procState | 调度组要点 |
|---|---:|---|---|
| 顶部 Activity | 0 | `TOP` | 通常 `TOP_APP` |
| 运行远程动画（remote animation） | 100 | 当前 top 状态 | `TOP_APP` |
| 测试插桩（instrumentation） | 0 | `FOREGROUND_SERVICE` | `DEFAULT` |
| 正在执行广播接收者 | 0 | `RECEIVER` | 由广播类型决定 |
| 正在执行服务回调 | 0 | `SERVICE` | 由回调的前后台属性决定 |
| 位于顶部但设备休眠 | 0 | 当前 top / sleeping 状态 | `BACKGROUND` |
| 暂无重要组件 | `UNKNOWN_ADJ` | `CACHED_EMPTY` | `BACKGROUND` |

随后再检查非顶部 Activity、FGS、悬浮层 UI、备份、Home、上一个应用、已启动服务、近期使用的 Provider 等本地状态。

#### 4.2 可见 Activity 使用 visible 档，不等于前台 adj 0

非顶部但仍可见的 Activity，例如多窗口中的可见窗口，进入 visible 档。基础值为 `VISIBLE_APP_ADJ=100`，还可按 WindowManager 返回的窗口层级在 visible 范围内细分。

`procState` 反映 `TOP`（顶部）、`BOUND_TOP`（绑定到顶部应用）、`IMPORTANT_FOREGROUND`（重要前台）等进程状态语义；adj 反映内存回收保护程度。把“可见 Activity = adj 0”写死，会高估它相对顶部进程的保护等级。

#### 4.3 FGS 还要区分普通、short（短时）与 recently-top（近期顶部）

API 37 的本地策略是：

- 普通 non-short FGS：`adj=200`、`procState=FOREGROUND_SERVICE`，并获得 BFSL（从后台启动前台服务）等相应能力；
- short FGS 在 `procState` 宽限未超时时：`adj=226`，即 `PERCEPTIBLE_MEDIUM_APP_ADJ + 1`，不获得 BFSL；
- 最近处于顶部的进程转入普通 FGS：宽限期内可提升到 `adj=50`；
- 最近处于顶部的进程转入 short FGS：宽限期内使用 `adj=51`；
- 最近处于顶部且运行符合条件的加急作业（expedited job）：相关豁免使用 `adj=52`。

Short FGS 超时后会触发带 `OOM_ADJ_REASON_SHORT_FGS_TIMEOUT` 的重算。结果取决于进程是否还有 Activity、其他 FGS、已启动服务或绑定，不能概括为“立即固定回落到 500”。

#### 4.4 Service 和 Provider 依赖通过连接传播

每个进程完成本地初值后，`OomAdjusterImpl` 使用两套有序节点队列传播连接影响：

1. 按 `procState` 重要性处理服务 / Provider 连接；
2. 再按 adj 档位处理可能继续降低承载进程 adj 的连接；
3. 承载进程状态改善时重新进入对应队列，直到没有连接能继续改变结果。

这里的“承载进程”（源码语境中的 host）指运行该 Service 或 Provider 的进程。

这套做法支持多跳依赖与循环关系，不再停留在“从每个进程递归 computeClients”的简单伪代码层面。

绑定服务的传播结果受多个标志共同影响，例如：

- `BIND_WAIVE_PRIORITY`：连接不按常规方式提升承载进程；
- `BIND_NOT_FOREGROUND`：限制调度组和前台 `procState` 传播；
- `BIND_IMPORTANT`、`BIND_ABOVE_CLIENT`：加强承载进程的重要性；
- `BIND_NOT_PERCEPTIBLE`、`BIND_ALMOST_PERCEPTIBLE`：限制到特定可感知档；
- `BIND_ALLOW_OOM_MANAGEMENT`：允许承载进程更接近自身组件状态管理；
- `BIND_ALLOW_FREEZE`：阻止 CPU_TIME 能力沿该绑定自动传播。

因此，“Service 至少是 500”并不成立。被顶部或常驻客户端以相应标志绑定时，服务承载进程可以达到 bound-top、persistent-service 等更高保护档；已启动服务在后台又可能落入 500 / 800。

Provider 连接也能传播客户端重要性。持有外部进程句柄（external process handle）的 Provider 承载进程可提升到 `adj=0`；连接释放后的短时间内，近期使用的 Provider 还可能保留 `PREVIOUS_APP_ADJ`，到期后由后续更新重算。

#### 4.5 最终分配 LRU 梯度并应用结果

连接传播结束后，`applyLruAdjust()` 为仍处于未知 / 缓存状态的进程分配 cached adj，并在相应功能开关下处理可见 / 上一个应用的梯度。`postUpdateOomAdjInnerLSP()` 再执行：

- 写入变化的 OOM 分数；
- 切换调度组和主线程 / RenderThread 优先级；
- 更新 freezer 资格；
- 把 `procState` 报告给应用线程、UID 观察者、网络策略和进程统计；
- 发送 `process_state_changed` Perfetto 事件；
- 必要时主动清理超额 cached 进程。

### 五、`procState`、`schedGroup` 与 capability（能力位）

#### 5.1 `procState` 的数字顺序表示重要性顺序

`ActivityManager.java` 定义的主要状态从高到低依次包括：

```text
PERSISTENT → PERSISTENT_UI → TOP → BOUND_TOP
→ FOREGROUND_SERVICE → BOUND_FOREGROUND_SERVICE
→ IMPORTANT_FOREGROUND → IMPORTANT_BACKGROUND
→ TRANSIENT_BACKGROUND → BACKUP → SERVICE → RECEIVER
→ TOP_SLEEPING → HEAVY_WEIGHT → HOME → LAST_ACTIVITY
→ CACHED_ACTIVITY → CACHED_ACTIVITY_CLIENT
→ CACHED_RECENT → CACHED_EMPTY → NONEXISTENT
```

Android 17 已没有单独的 `PROCESS_STATE_FOREGROUND_SERVICE_LOCATION`。位置、相机、麦克风等 FGS 能力通过 capability 表达，不应向 `procState` 表中插入一个不存在的枚举值。

#### 5.2 `schedGroup` 映射到线程组，不代表固定 CPU 份额

API 37 的 AMS 调度组常量是：

| AMS schedGroup | 值 | `applyResultsLSP()` 映射 |
|---|---:|---|
| `SCHED_GROUP_BACKGROUND` | 0 | `THREAD_GROUP_BACKGROUND` |
| `SCHED_GROUP_RESTRICTED` | 1 | `THREAD_GROUP_RESTRICTED` |
| `SCHED_GROUP_DEFAULT` | 2 | `THREAD_GROUP_DEFAULT` |
| `SCHED_GROUP_TOP_APP` | 3 | `THREAD_GROUP_TOP_APP` |
| `SCHED_GROUP_TOP_APP_BOUND` | 4 | `THREAD_GROUP_TOP_APP` |
| `SCHED_GROUP_FOREGROUND_WINDOW` | 5 | `THREAD_GROUP_FOREGROUND_WINDOW` |

具体使用哪些 cgroup 控制器、uclamp（调度器利用率上下界）和 cpuset（可运行的 CPU 集合），由设备的任务配置（task profile）和 libprocessgroup 配置决定。不能把 `schedGroup` 直接解释为固定 CPU 百分比，也不能假定 API 37 仍通过某个 `/dev/cpuctl` 路径写值。

进入 `top-app` 时，OomAdjuster 还会更新 UI / RenderThread 优先级；启用 FIFO UI 调度的产品使用先进先出调度回调，否则使用 `THREAD_PRIORITY_TOP_APP_BOOST`。离开 `top-app` 时再恢复。

#### 5.3 Android 17 的 freezer 资格由 CPU 能力决定

API 37 的 `getFreezePolicy()` 逻辑很短：只要进程拥有 `PROCESS_CAPABILITY_CPU_TIME` 或 `PROCESS_CAPABILITY_IMPLICIT_CPU_TIME`，就不能冻结；两者都没有时，策略允许冻结。

- 顶部、可见工作、FGS、执行服务回调、接收广播等状态可赋予 CPU_TIME；
- adj 低于 `mFreezerCutoffAdj` 的进程获得 IMPLICIT_CPU_TIME；
- 服务 / Provider 绑定可以传播 CPU_TIME；
- `BIND_ALLOW_FREEZE` 用于阻止不必要的 CPU 时间传播，让服务承载进程在合适状态下可冻结。

OomAdjuster 只计算资格并回调 `onProcessFreezabilityChanged()`。`CachedAppOptimizer` 负责去抖延迟（debounce，即等待状态稳定）、Binder 冻结、cgroup 冻结、解冻和失败处理。冻结前遇到未排空 Binder 事务时可能重试；持续制造 Binder 流量逃避冻结的进程还可能被终止。

“adj 达到 900 就一定冻结”“没有待处理定时器才冻结”“冻结后不再重算 adj”都不符合 API 37 的规则。详细 Binder 行为见 §1.10。

### 六、OomAdjuster 与 lmkd 的边界

#### 6.1 `system_server` 计算分数，lmkd 监测压力并选择目标

OomAdjuster 把 `curAdj` 应用到 `ProcessList.setOomAdj()`。该方法通过 lmkd 控制套接字发送 `LMK_PROCPRIO`；lmkd 校验进程 ID（PID）、用户 ID（UID）和值域，更新内部进程表，并在 `for_lmkd_only` 为 `false` 时写入内核的 `/proc/<pid>/oom_score_adj`。`for_lmkd_only` 表示只更新 lmkd 内部信息，不同步写这个内核分数文件。

lmkd 使用内存 PSI 事件、swap、thrashing 和设备属性判断何时需要回收。

PSI 框架本身可衡量任务因 CPU、内存或 I/O 资源不足而停顿的时间；在 lmkd 的回收触发路径中，内存压力事件由 lmkd 直接订阅，通常不会先回调 AMS，再要求 OomAdjuster“加快 cached 进程老化”。API 37 的 OomAdjuster 中也没有通过 `PSI_SOME` / `PSI_FULL` 分支修改 cached adj。

这两个环节要分开理解：

```text
组件/依赖变化
  → ProcessStateController / OomAdjusterImpl
  → adj、procState、schedGroup、capability
  → LMK_PROCPRIO / LMK_PROCS_PRIO
  → lmkd 保存最新进程优先级

kernel PSI / swap / thrashing
  → lmkd 判断内存压力与候选范围
  → 结合 oom_score_adj 和内存数据选择进程
  → pidfd/kill + kill event
```

其中，pidfd 是引用目标进程的文件描述符，可避免仅凭可能复用的 PID 操作进程。

#### 6.2 `LMK_PROCS_PRIO` 是小批量套接字消息

当 `mEnableBatchingOomAdj` 开启且属于批量应用结果时，变化进程先放入 `mProcsToOomAdj`，计算末尾调用 `ProcessList.batchSetOomAdj()`。

API 37 每个 `LMK_PROCS_PRIO` 包最多携带 3 个进程，每个进程有 5 个字段：PID、UID、oomadj、进程类型、`for_lmkd_only`。列表超过 3 个时会拆成多条控制套接字消息；批处理路径当前把进程类型固定为应用，并把 `for_lmkd_only` 写为 0（单进程 `LMK_PROCPRIO` 才有 zram 回写场景下的 `for_lmkd_only` 例外）。

它不是 Binder IPC，也不会把任意数量进程放进一次调用。LMKD 批量命令编号、数据包长度和 thrashing 决策边界，可与 [4.3 lmkd、Cached App Freezer 与内存压力治理](../ch04-memory/03-lmkd-freezer-memory-pressure.md) 交叉核对。

### 七、何时触发重算

更新主要由状态变化驱动，`OomAdjReason` 包括：

- Activity / UI 及 UI 可见性变化；
- 开始 / 结束执行接收者；
- 绑定、解绑、启动、停止或执行服务；
- 获取 / 移除 Provider；
- 进程开始 / 结束；
- 允许列表、UID 空闲、限制变化；
- short FGS 超时、备份、移除任务；
- 服务 Binder 调用、批量更新请求。

API 37 没有“每 1 秒无条件全量重算”的 `OOM_ADJ_UPDATE_INTERVAL`。有时效的状态会记录 `followupUpdateUptimeMs`，例如最近处于顶部的 FGS、上一个应用的 Provider；到期处理器先把进程加入待处理集合，再做局部更新。调度下一次后续更新时，还会用 `mFollowUpOomadjUpdateWaitDuration` 合并过近的超时点，所以不要把状态到期时刻理解为必然立刻单独重算。

若更新过程中又产生更新请求，`mOomAdjUpdateOngoing` 阻止递归进入，新目标进入 `mPendingProcessSet`。当前轮结束后统一处理待处理目标；若期间要求全量更新，则下一轮直接全量计算。

### 八、计算开销与锁边界

全量更新的计算和结果应用需要同时持有服务锁与进程锁，进程数和连接图复杂度会直接影响 `system_server` 临界区时长。API 37 使用了以下几类控制：

- 局部更新只收集目标及其可达进程；
- procState / adj 两套按重要性排序的节点队列减少无效反复扫描；
- 批处理会话合并一组组件状态变更；
- 待处理集合合并更新期间重复到达的目标；
- 后续更新设置最小间隔，合并接近的超时点；
- LMKD adj 更新可按 3 条记录一包发送；
- 进程组更新回调放到独立处理器线程，避免在线程很多时长期占用锁。

源码没有“超过 20 ms 就算 OomAdjuster 瓶颈”的平台阈值。应对照一帧预算、输入 / 启动关键路径、同一时段 AMS Binder 阻塞和设备进程规模评估。

### 九、Android 17 的诊断方法

#### 9.1 从 dumpsys 和 procfs 核对结果

procfs 是以 `/proc` 路径暴露进程和内核状态的虚拟文件系统。先保存 AMS 视角下的分数，再与内核接收的分数对照：

```bash
adb shell dumpsys activity oom
adb shell dumpsys activity processes

adb shell pidof com.example.app
adb shell cat /proc/<pid>/oom_score_adj
```

在 `dumpsys activity oom` 和 `dumpsys activity processes` 中，重点看 `curAdj/setAdj`、`curRawAdj/setRawAdj`、`curProcState/setProcState`、调度组、能力位、`adjType`、`adjSource` 和 `adjTarget`。含义如下：

- `cur*`：本轮刚计算出的值；
- `set*`：最近一次已应用 / 已报告的值；
- `rawAdj`：尚未经过 `maxAdj` / LRU 等最终修正的中间 adj；
- `adjType/source/target`：哪类组件或哪条依赖把进程提升到当前档。

若 `/proc/<pid>/oom_score_adj` 与 `setAdj` 短时不同，应确认进程是否刚重启、是否处于 zram 回写的 `for_lmkd_only` 特殊路径，以及 lmkd 套接字是否重连。

#### 9.2 Perfetto 的准确入口

API 37 在 Activity Manager atrace（Android 系统跟踪标记）中使用 `updateOomAdj_<reason>` 命名全量 / 局部更新时间片，例如 `updateOomAdj_activityChange`、`updateOomAdj_bindService`。下面的查询可查找耗时较长的计算：

```sql
SELECT ts, dur, name
FROM slice
WHERE name GLOB 'updateOomAdj_*'
ORDER BY dur DESC;
```

启用 Perfetto SDK 的 `proc_state` 分类后，adj、`procState` 或能力位改变会产生 `process_state_changed` 瞬时事件，字段包括：

- UID、PID、序列 ID 和更新原因；
- 更新前 / 后的 `procState`；
- 更新前 / 后的 OOM 分数；
- 更新前 / 后的能力位；
- CPU_TIME 与 IMPLICIT_CPU_TIME 的来源。

`proc_state_counter` 分类还会按 procstats（进程状态统计）状态输出全局进程数计数器，包括冻结进程数量。查看单个瞬时事件的结构化参数可使用：

```sql
SELECT s.ts, s.name, a.key, a.display_value
FROM slice AS s
JOIN args AS a USING (arg_set_id)
WHERE s.name = 'process_state_changed'
ORDER BY s.ts, a.key;
```

内核 `oom/oom_score_adj_update` ftrace（内核跟踪框架）事件用于核对分数写入时间；lmkd 终止事件和 PSI 轨道用于核对何时发生压力、为何选择该目标。不能仅凭“adj 升到 900 后出现 `am_kill`”断言进程一定由 lmkd 终止，还需检查终止原因、PID、压力事件和进程是否由 AMS 主动清理。

#### 9.3 一次有效的优先级实验

1. 记录系统构建指纹（build fingerprint）、AOSP / 厂商版本和 lmkd / freezer DeviceConfig；
2. 分别触发顶部、可见、FGS、short FGS、接收者、已启动服务和 cached 状态；
3. 对每次变化记录 `adjType/source/target`，不要只记最终数字；
4. 对绑定场景逐个改变绑定标志，确认承载进程的 adj、`procState` 与能力位；
5. 同时采集 `updateOomAdj_*`、`process_state_changed`、`sched` 调度事件、Binder 和 `oom_score_adj_update`；
6. 将计算耗时按全量 / 局部更新、进程数、连接数和触发原因分组。

### 十、版本边界与源码锚点

在 Android 13 到 Android 17 的范围内，cached 进程可能获得很少或零 CPU 时间；Android 14 到 Android 17 的范围内，cached-app freezer 与延迟动态广播等策略进一步减少无效解冻。Android 17 的源码变化包括 PSC 包迁移、ProcessStateController 入口、基于能力位的 freezer 决策和结构化进程状态跟踪。这里没有使用后续主线实现反推 Android 17 行为。

源码定位：

- 入口与批处理：`services/core/java/com/android/server/am/psc/ProcessStateController.java`
- 计算 / 应用框架：`.../psc/OomAdjuster.java`
- API 37 主策略：`.../psc/OomAdjusterImpl.java`
- adj / `schedGroup` 常量：`.../psc/Constants.java`
- 新图算法演进：`.../psc/ProcStateController.java` 与 Graph / Edge 类
- LMKD 协议：`services/core/java/com/android/server/am/ProcessList.java`、`system/memory/lmkd/include/lmkd.h`
- Freezer 执行：`services/core/java/com/android/server/am/CachedAppOptimizer.java`
- 内核跟踪：`include/trace/events/oom.h`（`android17-6.18-2026-06_r6`）
- 官方说明：
  - [Processes and app lifecycle](https://developer.android.com/guide/components/activities/process-lifecycle)
  - [Low memory killer daemon](https://source.android.com/docs/core/perf/lmkd)
  - [Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)

排查进程为何被终止时，应保持这条边界：组件和依赖决定重要性，OomAdjuster 计算并应用重要性，lmkd 监测内存压力并选择目标，内核落实分数与进程控制。混用这四层术语，会把正常的 cached 回收误判成 OomAdjuster 计算错误，或把错误的绑定关系误判成 lmkd 过于激进。


## 版本与实现边界

| 版本 | 双锁状态 | 阅读源码时的重点 |
|---|---|---|
| Android 11 及更早 | 没有当前这套 `mProcLock` 双锁骨架 | 不要把 Android 12 之后的 LOSP/LSP 契约套用到旧分支 |
| Android 12 / API 31 | 引入并启用 `mProcLock`，确立组合读写锁和锁顺序 | 迁移初期仍有大量全局锁路径 |
| Android 13—16 | 进程状态、OOM 调整、冻结与统计代码持续采用相关约定 | 具体字段和方法位置随版本变化 |
| Android 17 / API 37 | 双锁继续启用；OOM 调整位于 `am.psc`；定义 `big_locks` Perfetto 事件 | 以 `android-17.0.0_r1` 的注解、调用点和系统轨迹特性为准 |


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


## 结论

ActivityManager 的主线不是某一个数值或某一把锁。它是“组件事件改变进程责任，进程责任触发优先级计算，共享状态更新又受到 system_server 锁契约约束”这条因果链。Activity、Service、Broadcast 和 ContentProvider 的调度入口不同，但都要回到目标进程、计时边界、`procState`、`oom_score_adj` 与 `schedGroup` 解释结果。

Android 17 的双锁模型没有消除大临界区。OOM adj 和 LRU 写入仍会同时持有全局锁与进程锁，冻结与部分通知路径才可能只使用 `mProcLock`。诊断时应把组件调用链、OomAdjuster 结果、锁等待和持锁者工作连成同一条时间线，不能只凭一次 `futex` 等待或一个 adj 数值下结论。


## 参考资料

- [Android 12 `ActivityManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-12.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [Android 17 `ActivityManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [Android 17 `ActivityManagerProcLock.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerProcLock.java)
- [Android 17 `ActivityManagerGlobalLock.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerGlobalLock.java)
- [Android 17 `ProcessList.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [Android 17 `OomAdjuster.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/psc/OomAdjuster.java)
- [Android 17 `CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [Android 17 `ThreadPriorityBooster.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/ThreadPriorityBooster.java)
- [Android 17 `PerfettoCategories.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerfettoCategories.java)
- [Android 17 `LoadedApk.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/LoadedApk.java)
- [Perfetto SQL 标准库：`android.monitor_contention`](https://perfetto.dev/docs/analysis/stdlib-docs#android-monitor_contention)
- [Perfetto Android trace 分析示例](https://perfetto.dev/docs/analysis/common-queries)
