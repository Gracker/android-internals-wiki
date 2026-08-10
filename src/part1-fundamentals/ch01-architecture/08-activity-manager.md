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
- '4.4'
- '8.1'
- '8.2'
- '5.8'
last_task2b_lite_at: '2026-06-26T09:35:00+08:00'
drafted_date: '2026-04-05'
created_by: task2a-knowledge-gap
created_date: '2026-04-04'
gap_source: AOSP结构+官方文档+研究素材+读者需求
rework_date: '2026-04-05'
rework_by: task2a
reviewed_by: openclaw-task6
reviewed_date: '2026-07-01'
task6_result: pass-light-edit
pipeline_stage: ready-to-publish
task6_state: reviewed
last_task6_audit: '2026-07-01'
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
last_task9_at: '2026-07-01T00:39:52+08:00'
task9_reviewed_date: '2026-07-01'
task9_reviewed_by: openclaw-task9
review_round: '9'
last_task9_audit: '2026-07-01'
task6_reviewed_by: openclaw-task6
task6_reviewed_at: '2026-05-18T20:16:50+08:00'
last_task6_at: '2026-07-01T09:07:00+08:00'
last_task6_review_log: logs/review/2026-06-09-09-review.md
last_task2b_at: '2026-05-27T22:50:00+08:00'
last_task2b_log: 'frontmatter backlog fallback: logs/deep-review/2026-05-18-19-deep-review.md'
task2b_notes: 修复 Task9 P95：top-sleeping oom_adj、Service ANR ProcessAnrTimer、ANR dump
  文件路径、Broadcast delivery timeout 起点与 Android 14/15/16 广播队列类名。
last_task9_review_log: logs/deep-review/2026-07-01-00-audit.md
last_task9_autofix_at: '2026-07-01'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: '2026-07-01'
task6_l1_l2_fixes: '5'
task6_l3_l4_issues: '0'
last_task9_audit_log: logs/deep-review/2026-07-01-00-audit.md
task6_review_notes: '2026-07-01 Task6 revisiting re-review (idle-audit auto-fix 后):
  pass-light-edit。L1 小修 7 处（禁用词"链路"×7 → 流程/调用链/计算路径/路径）；无 L2/L3/L4 新增问题。Task9 idle-audit
  source version anchoring 后写作复审通过。自动晋升 finalized。'
task9_review_notes: '2026-07-01 Task9 idle-audit: auto-fixed Android 17 source baseline;
  OomAdjuster moved to com.android.server.am.psc; updated OOM constants/source anchors
  and android-17.0.0_r1 verification markers; P0 1 / P1 0 / P2 0; returned to Task6
  review. | 2026-06-09 Task9 deep-review: pass-tech-review。复核 Task9 idle-audit auto-fix
  与 Task6 回流；AOSP android-16.0.0_r1 源码锚点、Android 17 官方行为边界、queue pending 状态均通过；P0
  0 / P1 0 / P2 0；自动晋升 finalized。 | 2026-06-09 Task9 idle-audit: auto-fixed P0 source
  anchors: ProcessAnrTimer is an inner class of ActiveServices, not a standalone source
  file; activity cold-start process launch uses ATMS.startProcessAsync() -> ActivityManagerInternal.startProcess(),
  not AMS.startProcessAsync(); P0 2 / P1 0 / P2 0; returned to Task6 review. | 2026-05-28
  Task9 00:33：AUTO-FIX Perfetto monitor contention SQL 表名/列名；回到 Task6 复审。 | 2026-05-28
  Task9 deep-review: pass-tech-review。复核 Task6 回流后的技术口径；P0 0 / P1 0 / P2 0；queue 无
  pending，自动晋升 finalized。'
---

# 1.8 Activity Manager Service 与性能分析

AMS（`ActivityManagerService`）是应用组件与进程生命周期的系统侧协调者。它不负责渲染界面，也不直接执行应用代码；它负责记录“哪个进程承载哪些组件、当前有多重要、某次组件调用是否按时完成”，并把创建进程、调度组件、记录异常等工作交给相应模块。

分析冷启动、进程被杀、Service 卡住或 Broadcast ANR 时，AMS 往往是把系统侧现象与应用侧调用栈接起来的那一层。排查时应先确认：

1. 谁发起了操作；
2. 系统把操作投递给了哪个进程和线程；
3. 计时从哪里开始、由什么回调结束；
4. 超时后是 ANR、异常、进程清理，还是一次普通的等待失败。

当前源码基线为 AOSP `android-17.0.0_r1`。Android 10～16 只用于解释版本演进。

---

## AMS、ATMS 与 WMS 的分工

这三个服务都运行在 `system_server` 中，但职责不同：

| 服务 | 主要职责 | 分析时常见入口 |
|---|---|---|
| AMS | 进程、Service、Broadcast、Provider、ANR、Crash、进程重要性 | `ActivityManagerService`、`ProcessList`、`ActiveServices`、`BroadcastQueueImpl` |
| ATMS | Activity 启动、Task 选择、前后台切换、启动模式 | `ActivityTaskManagerService`、`ActivityStarter`、`ActivityRecord` |
| WMS | Window 容器、焦点、可见性、输入窗口状态 | `RootWindowContainer`、`DisplayContent`、`AnrController` |

`Instrumentation.execStartActivity()` 直接调用的是 `ActivityTaskManager.getService().startActivity()`。因此，“启动 Activity 都由 AMS 完成”是旧口径。现代 Android 中，ATMS 先决定 Activity 应放进哪个 Task；只有目标进程不存在时，才请求 AMS/`ProcessList` 创建进程。

AMS 对外暴露 `IActivityManager` Binder 接口。请求通常先落在 `Binder:system_server_*` 线程上，再在持锁区域、Handler 或其他系统线程中继续处理。不要把 `ActivityManager` 线程理解成唯一的 AMS 主线程，也不要把 Binder 线程池数量写成固定值：线程池上限和实际线程数都可能随构建及运行状态变化。

### Perfetto 中先看什么

AMS 相关证据主要来自三类数据：

- `system_server` 与目标应用的线程切片；
- Binder transaction、线程状态和 Java monitor contention；
- EventLog，例如 `am_proc_start`、`am_proc_bound`、`am_anr`、`am_crash`、`am_kill`。

EventLog 不是普通切片。只有跟踪启用了 Android logs 数据源并包含 events buffer，`android_logs` 表中才会有这些记录。下面的查询同时保留消息内容，便于读取 PID、进程名和原因：

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

这段查询用于建立时间坐标，不足以单独判断根因。没有采集到某个 tag，也不等于事件没有发生。

---

## 进程重要性：`procState` 与 `oom_score_adj`

Android 不以“前台/后台”二分进程。AMS 会综合 Activity 可见性、正在执行的 Service、Provider 依赖、Receiver、Binder 绑定关系等信息，计算进程状态和回收优先级。

这两个概念需要分开：

- `procState` 描述进程当前负责的工作，供调度、后台限制和权限判断使用；
- `oom_score_adj` 是给内存回收使用的分数。值越大，通常越早成为回收候选。

两者相关，但不是一张固定的一一映射表。同一个进程也可能同时承载 Activity、Service 和 Provider，最终重要性取决于所有依赖关系中最强的保护条件。

### Android 17 的关键 adj 档位

`frameworks/base/services/core/java/com/android/server/am/psc/Constants.java` 在 `android-17.0.0_r1` 中定义了以下基准值：

| 常量 | 值 | 典型含义 |
|---|---:|---|
| `FOREGROUND_APP_ADJ` | 0 | 当前顶层交互进程 |
| `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ` | 50 | 刚从 TOP 转为 FGS 的短暂宽限 |
| `VISIBLE_APP_ADJ` | 100 | Activity 可见但不在顶层 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 用户可感知的工作，例如常规非 short FGS |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | 由重要系统绑定保护的中间档 |
| `PERCEPTIBLE_LOW_APP_ADJ` | 250 | 比普通 Service 更重要的低可感知工作 |
| `BACKUP_APP_ADJ` | 300 | 正在备份 |
| `SERVICE_ADJ` | 500 | 普通后台 Service |
| `HOME_APP_ADJ` | 600 | Home/Launcher |
| `PREVIOUS_APP_ADJ` | 700 | 上一个前台应用的基准档 |
| `SERVICE_B_ADJ` | 800 | 较低优先级的旧 Service |
| `CACHED_APP_MIN_ADJ`～`CACHED_APP_MAX_ADJ` | 900～999 | 缓存进程 |

表中数值是源码常量，不是承诺每种组件永远落在某一行。Android 17 还可以通过 feature flag 对可见进程和 previous app 做阶梯化分配。`TOP_SLEEPING` 也是计算分支中的 `adjType`，不能把它当成独立常量档位。

前台 Service 同样不是“永远 100”。在当前基线中，常规非 short FGS 通常受 `PERCEPTIBLE_APP_ADJ = 200` 保护；刚从 TOP 进入 FGS 的进程可在宽限期内使用 50。它仍可能在极端内存压力、异常或用户停止服务时退出。

### AMS 如何把分数交给 lmkd

Android 17 的实际计算位于 `com.android.server.am.psc.OomAdjuster` 和 `OomAdjusterImpl`。计算完成后，`ProcessList.setOomAdj()` 通过 lmkd socket 发送 `LMK_PROCPRIO` 消息，消息中包含 PID、UID 与 adj。lmkd 再结合 PSI、内存水位、回收压力及候选进程信息做杀进程决策。

因此，“lmkd 每次从 `/proc/<pid>/oom_score_adj` 扫描并按最大值杀进程”过度简化了现行实现。`oom_score_adj` 仍是内核可见的重要状态，但 AMS 与 lmkd 之间存在明确的控制消息。

Perfetto 的 Android memory 标准库可以把 adj 变化与内存放在一起看：

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

能否得到完整结果取决于跟踪配置。看到 adj 升高只能说明保护程度下降；判断死亡原因还要结合 lmkd 日志、`ApplicationExitInfo`、`am_proc_died` 和内存压力。`am_kill` 表示 AMS 记录了一次主动终止，不能仅凭这个标签断言“进程被 lmkd 回收”。

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

- `am_proc_start` 记录 AMS/`ProcessList` 发起进程创建，不是用户点击时刻，也不是完整冷启动耗时；
- `am_proc_bound` 写在 `attachApplicationLocked()` 中，表示新进程的 `IApplicationThread` 已被 AMS 接受。它不表示 `Application.onCreate()` 已经结束，更不表示首帧完成。

### 一次可靠的启动分析

冷启动至少应对齐这些时刻：

1. 启动请求发出；
2. `am_proc_start`；
3. Zygote fork 与新进程出现；
4. `ActivityThread.main()`、`attachApplication`、`bindApplication`；
5. `Application.onCreate()`；
6. Activity 生命周期；
7. 首帧提交与显示。

只计算 `am_proc_start` 到 `am_proc_bound`，得到的是进程创建和 attach 的一部分，不是用户感知启动时间。

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

这段代码适合在启动诊断和初始化分流中使用。`getReason()` 提供更细的启动原因，`getStartComponent()` 才是区分四大组件的直接 API。

---

## ANR：先找计时器，再看阻塞点

ANR 不是统一的“主线程卡 5 秒”。不同系统模块在投递不同工作时启动计时，完成回调也不同。

| 场景 | Android 17 AOSP 基础值 | 计时结束条件 |
|---|---:|---|
| Input dispatch | 通常 5 秒 | 目标窗口及时处理输入或焦点问题解除 |
| 前台优先级 Broadcast | 10 秒基础值 | 同步 `onReceive()` 返回，或异步 `PendingResult.finish()` |
| 后台优先级 Broadcast | 60 秒基础值 | 同上 |
| 前台执行 Service | 20 秒基础值 | 对应 Service 执行回调完成 |
| 后台执行 Service | 200 秒基础值 | 对应 Service 执行回调完成 |

这些值不是跨设备 API 契约。AOSP 会乘以 `Build.HW_TIMEOUT_MULTIPLIER`，设备厂商也可能调整。Android 14+ 的广播计时还会为 CPU 饥饿进程扩展窗口：官方诊断文档给出的范围是前台优先级 10～20 秒、后台优先级 60～120 秒。

### Input ANR

Input ANR 从原生 `InputDispatcher` 开始。典型路径是：

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

- **Window unresponsive**：已有目标窗口，但输入事件在分发队列中等待过久；
- **No focused window**：按键等需要焦点的事件到达时，没有可接收它的焦点窗口。

第二种情况不一定是某个 `onTouchEvent()` 太慢。首帧迟迟没有建立窗口、窗口带有 `FLAG_NOT_FOCUSABLE`、焦点切换卡在 WMS 中，都可能触发它。

排查时先看应用主线程状态：

- `Running` 很久：查长任务与热点代码；
- `Runnable` 很久：查 CPU 饥饿和系统负载；
- `Sleeping` 且在 Binder：沿 Binder reply 找服务端；
- `Sleeping` 且在锁等待：找持锁线程；
- 主线程已经空闲：堆栈可能采得太晚，需回看 ANR 前的跟踪。

### Broadcast ANR

Android 17 中，AMS 创建前台与后台两套 `BroadcastConstants`。`ActivityManagerService` 给它们设置 10 秒和 60 秒基础超时，`BroadcastQueueImpl.dispatchReceivers()` 在向目标进程调度 Receiver 时启动 `BroadcastAnrTimer`。

计时边界如下：

- 广播进入系统队列的时刻，不等于 ANR 计时开始；
- 拉起冷进程所花的时间会进入 Receiver 的执行预算；
- 同步 Receiver 在 `onReceive()` 返回时完成；
- 调用 `goAsync()` 后，必须由 `PendingResult.finish()` 结束本次投递。

`FLAG_RECEIVER_FOREGROUND` 决定这里的“前台优先级广播”。它不等于“接收进程有前台 Activity”。

### Service execution ANR

Service 的 20/200 秒描述的是执行回调超时，不是 Service 允许存活多久。Android 17 在 `ActiveServices` 中使用 `ProcessAnrTimer`，基础值来自 `ActivityManagerConstants.SERVICE_TIMEOUT` 和 `SERVICE_BACKGROUND_TIMEOUT`。

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

`onStartCommand()`、`onBind()` 等执行也会纳入相应的 Service 执行管理。应用进程若为承载 Service 而冷启动，冷启动本身也会消耗预算。

#### `startForegroundService()` 的前台提升不是同一个计时器

调用 `startForegroundService()` 后没有及时调用 `Service.startForeground()`，走的是前台提升超时。`android-17.0.0_r1` 中：

- `DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS` 为 30 秒；
- 超时后 `DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS` 再给 10 秒延迟；
- `ActiveServices.serviceForegroundTimeout()` 创建超时记录，随后进入 ANR 处理。

这组数值是 Android 17 固定源码标签下的默认实现，不应反推为所有 Android 版本和所有设备都承诺 30+10 秒。面向应用开发时，仍应在 `onCreate()` 中立即建立通知并调用 `startForeground()`，不要把任何超时值当作可用工作时间。

它也不同于 Android 15 起的 FGS 类型运行总时长限制。后者到期会调用 `Service.onTimeout(int, int)`，未及时停止时产生 `RemoteServiceException`；这不是 execute-service ANR。

### ContentProvider：三种等待，三种结果

“Provider ANR 是 10 秒”会把三个机制混在一起。Android 17 的 `ContentResolver` 定义了：

| 等待点 | 默认值 | 超时后的主要含义 |
|---|---:|---|
| Provider publish | 10 秒 | 进程 attach 后没有发布 Provider，AMS 按初始化失败清理进程 |
| Provider ready | 20 秒 | 调用方等待 Provider 可用超时，获取失败 |
| 已连接远端 Provider 的部分异步调用 | 3 秒 | 特定 API 的远端结果等待；可通过 `appNotRespondingViaProvider()` 报告宿主无响应 |

`ContentProviderHelper.processContentProviderPublishTimedOutLocked()` 会以“timeout publishing content providers”为原因移除进程；外部调用者在 ready 等待超时后可能只得到 `null`。实际的 Provider ANR 由 `ContentProviderHelper.appNotRespondingViaProvider()` 创建 `TimeoutRecord.forContentProvider()` 并交给 `AnrHelper`。

所以排查 Provider 卡顿时，先确认它发生在：

1. 应用启动和 `installContentProviders()`；
2. 获取 Provider；
3. 已建立 Binder 连接后的具体 Provider 方法。

Provider 通常在应用主线程初始化。即使最终报告的是 Input、Broadcast 或 Service ANR，根因也可能是某个 Provider 在进程启动阶段做了数据库迁移或同步 I/O。

### ANR 数据是怎样保存的

各入口最终可调用 `AnrHelper.appNotResponding()`。Android 17 会尽早为主要目标进程生成临时堆栈，正式处理时再由 `StackTracesDumpHelper` 收集相关 Java/native 栈与 CPU 信息。正式文件位于 `/data/anr/`，文件名以 `anr_` 开头，而不是早期版本常见的固定 `traces.txt`。

如果 ANR 排队超过 10 秒，`AnrHelper` 会把报告视为过期，只 dump 目标进程，避免在系统已经很慢时继续扩大负载。因此，ANR 文件里缺少其他进程的栈不一定是采集故障。

定位 EventLog 可以使用：

```sql
SELECT ts, tag, msg
FROM android_logs
WHERE tag = 'am_anr'
ORDER BY ts;
```

拿到时刻后，回看超时前的线程状态和 Binder/锁依赖。ANR 发生后的堆栈可能已经恢复，只看最末张堆栈容易错过实际的阻塞段。

---

## Activity 与 Task 的现行容器模型

现代 Android 的任务容器更接近下面的层级：

```text
RootWindowContainer
  └─ DisplayContent
      └─ TaskDisplayArea
          └─ Task
              └─ ActivityRecord
```

其中：

- `RootWindowContainer` 是所有显示与窗口容器的根；
- 一个 `DisplayContent` 可以包含多个 `TaskDisplayArea`；
- `TaskDisplayArea` 可以容纳 Task，也可以嵌套；
- `Task` 既可能对应 Recents 中的一张任务卡，也可能是嵌套任务容器；
- `ActivityRecord` 是单个 Activity 的系统侧记录。

`ActivityStarter` 计算目标显示区域、启动模式与可复用 Task，ATMS/WMS 再把 `ActivityRecord` 放入合适容器。旧文章中的 `TaskStack` 可以用于解释历史实现，不应再作为 Android 17 的主模型。

### Android 17 的优化配置变更

`android:recreateOnConfigChanges` 不是 Android 17 才出现的属性。Android O 已使用它处理 `mcc`/`mnc` 的显式重建。Android 17 扩大了“不默认重建”的配置范围：

- `keyboard`、`keyboardHidden`；
- `navigation`；
- `touchscreen`；
- `colorMode`；
- `uiMode`，仅限进入或离开 `UI_MODE_TYPE_DESK`。

如果应用依赖 Activity 重建来重新加载这些资源，需要在 Manifest 中显式选择：

```xml
<activity
    android:name=".MainActivity"
    android:recreateOnConfigChanges="keyboard|keyboardHidden|navigation|touchscreen|colorMode|uiMode" />
```

这段配置用于恢复“发生这些变化时重建”的行为。它不是任意配置变化的总开关。

还要注意与 `android:configChanges` 的关系：同一 flag 若同时出现在两个属性中，Activity 不会因该变化重建。前者要求重建，后者表示应用自行处理；二者同时写时，自行处理一侧占上风。`uiMode` 的 Android 17 桌面模式边界还需结合应用实际目标版本与设备行为测试。

---

## Service 与前台服务的版本边界

前台服务用于用户明确知情、需要持续运行的任务。它提升进程重要性并要求持续通知，但不是绕过后台限制的通行证。

| 版本 | 与 AMS/FGS 相关的主要变化 |
|---|---|
| Android 8（API 26） | 后台 Service 启动受限，引入 `startForegroundService()` 使用方式 |
| Android 11（API 30） | 后台拉起的 FGS 访问相机、麦克风、位置受到更严格限制 |
| Android 12（API 31） | 后台启动 FGS 默认禁止，仅保留明确豁免 |
| Android 13（API 33） | 用户可在 Active apps/FGS 管理界面查看并停止服务；通知权限与 FGS 通知展示分开处理 |
| Android 14（API 34） | 目标版本要求声明 FGS type 和对应权限；后台创建 FGS 时会同步检查 while-in-use 权限是否处于可用状态 |
| Android 15（API 35） | `dataSync` 与 `mediaProcessing` 各自共享每 24 小时 6 小时后台额度，并提供 `Service.onTimeout()` |
| Android 16（API 36） | 与 FGS 并发执行的 Job 也计入 JobScheduler runtime quota |
| Android 17（API 37） | 后台音频交互增加生命周期与 FGS/WIU 约束 |

Android 17 的后台音频规则分两层：

1. 所有运行在 Android 17 上的应用，要在可见 Activity 中交互音频，或运行一个非 `shortService` 类型的 FGS；
2. 目标 API 37 的后台应用还需要具有 while-in-use 能力的 FGS。具有精确闹钟权限且操作 `USAGE_ALARM` 音频流时存在例外。

播放和音量 API 在无效生命周期中通常静默失败，音频焦点请求返回 `AUDIOFOCUS_REQUEST_FAILED`。所以不能笼统写成“Android 17 所有后台 FGS 没有 WIU 就静默失败”，目标版本、Activity 可见性、FGS 类型和 alarm 例外都要一起判断。

可延迟、可重试的工作优先考虑 JobScheduler 或 WorkManager；用户发起的数据传输可评估 user-initiated data transfer job；持续媒体播放使用 Media3 的 `MediaSessionService` 更合适。选择依据是任务语义，不是把所有 FGS 机械替换成 WorkManager。

### AMS 全局锁竞争

`ActivityManagerService.startService()` 在 Android 17 中不是 Java 方法级 `synchronized`。它完成调用者检查后进入：

```java
synchronized (mGlobalLock) {
    res = mServices.startServiceLocked(...);
}
```

`ActiveServices` 的 `...Locked()` 命名表示调用者应持有 AMS 全局锁，不代表存在一个独立的“`mServices` 锁”。`realStartServiceLocked()` 还会在该保护区域内向应用发送 `IApplicationThread.scheduleCreateService()`；这是 oneway Binder 调用，但 Binder 驱动排队、系统负载和大临界区仍可能放大锁等待。

采集了 Java monitor contention 后，可以用 Perfetto 标准库定位：

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

`blocked_*` 是等待锁的一侧，`blocking_*` 是持锁一侧。`binder_reply_id` 非空时，标准库已经把 contention 与相关 Binder reply 建立了关联；不要只凭两个切片时间相邻就宣布因果关系。

---

## Android 17 的广播调度

### 按进程组织的队列

Android 17 的主要实现是 `BroadcastQueueImpl` 与 `BroadcastProcessQueue`。AMS 先解析 Receiver，再按目标进程组织等待和运行状态：

```text
Context.sendBroadcast()
  → ActivityManagerService.broadcastIntent()
    → 解析 manifest / context-registered Receiver
      → BroadcastQueueImpl 入队
        → BroadcastProcessQueue 选择可运行目标进程
          → IApplicationThread.scheduleReceiver()
            或 scheduleRegisteredReceiver()
```

同一进程的 Receiver 最终仍要在该进程的指定 Handler/线程上执行，主线程繁忙会形成进程内队头阻塞。不同进程的队列可以独立推进，避免一个慢进程阻塞所有广播。

“无序广播并行执行”也要加边界。无序广播没有全局结果传递顺序，系统可以调度多个目标进程；但同一进程中的 Receiver 不会因此自动获得并行线程。Receiver 运行在哪个线程，取决于注册时使用的调度器及系统投递方式。

### Manifest Receiver 与动态 Receiver

- Manifest Receiver 可以在规则允许时拉起尚未运行的应用进程，因此可能把冷启动时间计入广播预算；
- context-registered Receiver 只在注册对象有效时接收，不会为了一个已经消失的动态注册关系单独创建进程；
- 从 Android 8 开始，Manifest 中的隐式广播受到广泛限制，并非任意静态 Receiver 都能被系统事件唤醒；
- 目标 Android 14+ 的应用注册非纯系统广播 Receiver 时，要显式使用 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`。

### Android 14+ 缓存状态下的广播

Android 14 起，应用处于 cached state 时，系统可以暂存发给运行时注册 Receiver 的广播，等应用离开 cached state 后再投递；某些重复广播还可能被合并。Manifest-declared broadcast Manifest Receiver 的广播不使用这套排队方式，系统可先让应用离开缓存状态再投递。

这会改变跟踪的解释：

- “广播发送后很久才进入 `onReceive()`”可能是设计内的缓存排队，不一定是 AMS 卡住；
- Manifest Receiver 仍可能触发进程启动，启动风暴要结合隐式广播限制和具体 `action` 判断；
- 实际的 Receiver ANR 计时从 `BroadcastQueueImpl` 调度目标 Receiver 时开始，不从广播发送时开始。

---

## 三个常用排查模板

### 冷启动慢

1. 用启动请求或 `ApplicationStartInfo.START_TIMESTAMP_LAUNCH` 建立起点；
2. 看 `am_proc_start` 到 fork，判断 system_server/Zygote 阶段；
3. 看 fork 到 `bindApplication`，判断运行时与进程 attach；
4. 看 `Application.onCreate()`、Provider 安装和 Activity 生命周期；
5. 看 RenderThread、首帧提交和 SurfaceFlinger 显示；
6. 用 `getStartComponent()` 确认是哪个组件拉起了进程。

### ANR

1. 从 ANR subject 或 `am_anr.msg` 确认类型；
2. 按类型找到计时器的开始点与结束回调；
3. 回看超时前，而不是只看 dump 时刻；
4. 判断目标线程是 Running、Runnable、Binder wait 还是 lock wait；
5. Binder 等待继续看服务端，锁等待继续看持锁者；
6. 检查系统级 CPU、I/O、内存压力，避免把调度饥饿误判成应用长任务。

### 进程消失

1. 查 `ApplicationExitInfo` 的 `reason`、`subreason` 与 `description`；
2. 对齐 `am_kill`、`am_proc_died`、lmkd 日志和 PID 生命周期；
3. 查看死亡前 adj、procState、RSS、swap 与系统内存压力；
4. 区分 AMS 主动清理、lmkd、Crash、ANR 后退出、用户停止和 Android 17 MemoryLimiter；
5. 不要把“末次 adj 是 900+”当作死亡原因，它只表示当时保护较弱。

---

## 常见误区

### “ANR 就是主线程卡 5 秒”

5 秒是 Input dispatch 的常见默认值。Broadcast、Service、JobScheduler、short FGS 和 Provider 各有自己的触发条件，部分场景甚至不是 ANR。

### “看到 `am_proc_bound` 就说明应用启动完成”

它只表示 AMS 接受了新进程的应用线程连接。`bindApplication`、`Application.onCreate()`、Activity 创建和首帧都可能还没发生。

### “看到 `am_kill` 就是 lmkd 杀进程”

`am_kill` 是 AMS 主动 kill 的 EventLog。lmkd 回收要结合 lmkd 证据、进程死亡事件与退出信息判断。

### “前台 Service 不会被杀”

FGS 提高进程重要性，不提供绝对存活保证。它还受启动权限、服务类型、运行额度、用户停止、ANR、Crash 和内存压力约束。

### “静态广播一定会拉起应用”

只有广播 action、Manifest 声明、导出/权限、后台执行限制和系统策略都允许时才可能拉起。Android 8 之后的隐式广播限制是判断前提。

### “`recreateOnConfigChanges` 是通用重启开关”

它只对列出的配置 flag 生效。Android 17 扩大了适用 flag，但与 `configChanges` 同时声明同一项时不会重建。

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

### ANR、Service、Broadcast 与 Provider

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
