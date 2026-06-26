---
title: "Activity Manager Service 与性能分析"
chapter: "1.8"
section: "1.8"
status: "finalized"
last_task2b_lite_at: "2026-06-26T09:35:00+08:00"
task2b_result: "fixed-lite"
task2b_state: "fixed"
task6_state: "revisiting"
task9_state: "pending"
pipeline_stage: "task6_pending"
drafted_date: "2026-04-05"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-26"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers behavior changes 11/12/13/14/17 (2026-06-26 audit)"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ContentResolver.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/InputManagerCallback.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/AnrController.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Instrumentation.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/Task.java"
  - type: aosp
    path: "frameworks/base/core/res/res/values/attrs_manifest.xml"
  - type: blog
    path: "https://juejin.cn/post/7083438148843225102"
  - type: blog
    path: "https://juejin.cn/post/7136008620658917407"
  - type: official
    path: "https://developer.android.com/about/versions/11/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/12/behavior-changes-12"
  - type: official
    path: "https://developer.android.com/about/versions/13/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/14/behavior-changes-14"
  - type: official
    path: "https://developer.android.com/about/versions/14/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges"
tags: [ams, activity-manager, process-lifecycle, anr, service-management, broadcast, content-provider]
related_chapters: ["1.3", "1.4", "4.4", "8.1", "8.2", "5.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+研究素材+读者需求"
rework_date: "2026-04-05"
rework_by: "task2a"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-09"
task6_result: pass-light-edit
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
last_task6_audit: "2026-06-08"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
task2b_result: "fixed"
last_task9_at: "2026-06-09T09:20:00+08:00"
task9_reviewed_date: "2026-06-09"
task9_reviewed_by: "openclaw-task9"
review_round: "8"
last_task9_audit: "2026-06-09"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_at: "2026-05-18T20:16:50+08:00"
last_task6_at: "2026-06-09T09:09:00+08:00"
last_task6_review_log: "logs/review/2026-06-09-09-review.md"
task6_review_notes: "2026-06-09 Task6 revisiting review：Task9 idle-audit auto-fix 后写作复审通过；L1/L2 无新增问题；0 回炉项。送 Task9 确认 auto-fix。"
last_task2b_at: "2026-05-27T22:50:00+08:00"
last_task2b_log: "frontmatter backlog fallback: logs/deep-review/2026-05-18-19-deep-review.md"
task2b_notes: "修复 Task9 P95：top-sleeping oom_adj、Service ANR ProcessAnrTimer、ANR dump 文件路径、Broadcast delivery timeout 起点与 Android 14/15/16 广播队列类名。"
last_task9_review_log: "logs/deep-review/2026-06-09-09-deep-review.md"
last_task9_autofix_at: "2026-06-09"
task9_review_notes: "2026-06-09 Task9 deep-review: pass-tech-review。复核 Task9 idle-audit auto-fix 与 Task6 回流；AOSP android-16.0.0_r1 源码锚点、Android 17 官方行为边界、queue pending 状态均通过；P0 0 / P1 0 / P2 0；自动晋升 finalized。 | 2026-06-09 Task9 idle-audit: auto-fixed P0 source anchors: ProcessAnrTimer is an inner class of ActiveServices, not a standalone source file; activity cold-start process launch uses ATMS.startProcessAsync() -> ActivityManagerInternal.startProcess(), not AMS.startProcessAsync(); P0 2 / P1 0 / P2 0; returned to Task6 review. | 2026-05-28 Task9 00:33：AUTO-FIX Perfetto monitor contention SQL 表名/列名；回到 Task6 复审。 | 2026-05-28 Task9 deep-review: pass-tech-review。复核 Task6 回流后的技术口径；P0 0 / P1 0 / P2 0；queue 无 pending，自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
task6_l1_l2_fixes: 5
task6_l3_l4_issues: 0
last_task9_audit_log: "logs/deep-review/2026-06-09-08-audit.md"
---


# 1.8 Activity Manager Service 与性能分析

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 **AMS / ATMS 分工与 Perfetto 入口**:[已验证: AOSP android-16.0.0_r1]
  AMS 负责进程管理、ANR、Service / Broadcast / Provider 调度;Activity / Task 容器管理在 ATMS / WindowManager。Perfetto 入口看 `system_server` 的 `ActivityManager` 线程和 `am_*` 事件。

- 🔹 **进程优先级、启动与回收链路**:[已验证: AOSP android-16.0.0_r1]
  关注 `oom_adj`、`am_proc_start`、`am_proc_bound`、lmkd 协作与冷启动关键时间点。

- 🔹 **ANR 类型与超时差异**:[已验证: AOSP + 官方文档]
  Input / Broadcast / Service / ContentProvider 有不同超时和埋雷位置,不能用"ANR = 5 秒"一把梭。

- 🔹 **现代 Activity 任务容器模型**:[已验证: AOSP android-16.0.0_r1]
  现代层级是 `RootWindowContainer → DisplayContent → TaskDisplayArea → Task → ActivityRecord`,不能再把 `TaskStack` 当成当前主术语。

- 🔹 **Android 14+ 广播与配置变更差异**:[已验证: developer.android.com + AOSP]
  Android 14 对 cached state 下的 context-registered broadcast 引入排队,并要求动态注册 Receiver 显式声明导出属性;`recreateOnConfigChanges` 的公开可验证语义是 Android O+ 下 `mcc/mnc` 场景的显式重建。

### 扩展(可选深入)

- 🔸 **system_server 侧瓶颈排查**:Binder 线程池饱和、AMS 全局锁竞争、Task 切换与窗口动画联动
- 🔸 **Trace 实战脚本化**:用 SQL 把 `am_*` 事件与主线程首帧、Binder 调用链、Process Stats 串起来
<!-- outline-end -->


## 为什么要了解 AMS

如果你做过 Android 性能优化,几乎不可能绕开 AMS。应用冷启动时,是 AMS 向 Zygote 发出 fork 请求来创建你的进程;用户按 Home 键时,是 AMS 调整你进程的 oom_adj,决定你在内存紧张时是第一个被杀还是最后一个;当你遇到 ANR,超时检测的"埋雷-爆雷"逻辑就住在 AMS 内部。

**用 Perfetto 分析启动耗时、进程被杀、ANR、前台服务超时这些问题时,Trace 里看到的 `am_proc_start`、`am_anr`、`am_crash` 这些事件,全部来自 AMS。** 不了解 AMS 的工作方式,这些事件就是 Trace 里的“黑盒”：你看到它发生了，但不知道为什么、怎么追。

读完本节,可以在 Perfetto 中识别 AMS 的关键 Track 和事件,理解进程优先级的动态调整逻辑,以及各类 ANR 的触发路径。目标是让性能分析时知道"该往哪里看",不是把读者变成 AMS 的开发者。

> 阅读本节之前,建议先了解 §1.3 进程模型和 §1.4 Binder IPC,因为 AMS 的几乎所有操作都涉及跨进程调用和进程生命周期管理。

下文涉及 Broadcast、Service、ContentProvider 的超时实现和 Input ANR 归因时,源码口径以 AOSP `android-16.0.0_r1` 为主;跨版本差异放在对应小节和文末版本演进表里。

---

## AMS 在 Android 架构中的角色

AMS 运行在 `system_server` 进程中,是 Android 最核心的系统服务之一。它负责进程的创建、优先级调整和回收,负责 Service、BroadcastReceiver、ContentProvider 的系统侧调度,也承接 ANR、Crash、前后台状态变化这些全局管理逻辑。对于 Activity,现代 Android 已经把大部分任务与窗口容器管理拆到了 `ActivityTaskManagerService`(ATMS)和 `WindowManagerService`(WMS)一侧,所以我们分析启动和任务切换时,不能只盯着 AMS。

AMS 与几个关键服务之间存在紧密的协作关系：

- **PackageManagerService(PMS)**:AMS 在启动 Activity/Service 时,需要通过 PMS 解析目标组件的信息(权限、声明、进程名等)。
- **ActivityTaskManagerService(ATMS) / WindowManagerService(WMS)**:Activity 需要窗口才能显示,现代 AOSP 里任务与窗口容器管理主要落在 ATMS / WMS。AMS 更多负责进程、Service、Broadcast 和 ANR 管线;ATMS 负责 Activity / Task 的调度;WMS 负责窗口、焦点和输入相关状态。Input ANR 的检测也要看 WMS 侧的 `InputDispatcher`。
- **SurfaceFlinger**:虽然不直接交互,但 AMS 决定了哪个 Activity 可见 → WMS 据此决定 Surface 的层级 → SurfaceFlinger 合成显示。
- **ProcessList**:AMS 内部维护的进程列表,和 lmkd(Low Memory Killer Daemon)协作完成内存回收。我们在 §4.4 会专门讲这个机制。

应用进程通过 `ActivityManager`(客户端代理类)与 AMS 通信。这层通信走的是 Binder IPC,`IActivityManager.aidl` 定义接口,`ActivityManagerService` 实现接口。需要区分的是,`startActivity()` 这类 Activity / Task 相关调用虽然入口还在 AMS 对外接口上,但会继续委托给 `ActivityTaskManagerService`。所以你在 Perfetto 中看到的 `Binder:system` 线程调用,往往只是系统服务链路的起点,不是全部。

```text
[图：AMS 在系统架构中的位置，展示 system_server 内 AMS 与 PMS / WMS 的关系，以及 App 进程通过 Binder 与 AMS 通信的路径]
```

### 在 Perfetto 中定位 AMS

在 Perfetto 中分析 AMS 相关行为时,我们主要关注 `system_server` 进程中的以下线程和事件:

**关键线程:**
- `ActivityManager` 线程:处理大部分 AMS 主逻辑(组件调度、进程管理)。
- `Binder:system_server` 线程池(通常 16 个线程):接收来自 App 进程的 Binder 调用。
- `android.fg` / `android.display` 线程:处理前台和显示相关的后台任务。

**关键 EventLog / Android logs 事件:**
- `am_proc_start`:AMS 决定创建新进程,并把启动请求交给 Zygote。
- `am_proc_bound`:新进程与 `system_server` 建立连接,应用线程已经 attach 完成。
- `am_anr`:系统记录一次 ANR。
- `am_crash`:应用崩溃。
- `am_kill` / `am_pss`:进程被杀或进行内存统计。
- `am_create_service` / `am_destroy_service`:Service 的创建与销毁。

这里要把 EventLog 和 slice 分开看。`am_proc_start`、`am_anr` 这些是 EventLog tag,在 Perfetto 里应当从 `android_logs` 这类日志数据源读取;Activity 启动本身没有 `am_activity_launch` 这个 EventLog tag,启动耗时更适合结合 `ActivityTaskManager` / `WindowManager` 的系统侧 slice、应用主线程的 `bindApplication` / Activity 生命周期,以及首帧 `doFrame` 一起看。

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags` 中存在 `am_proc_start` / `am_proc_bound` / `am_anr` / `am_kill`,不存在 `am_activity_launch`]

如果 trace 打开了 Android logs 数据源,可以先用下面的 SQL 看 AMS 侧 EventLog:

```sql
SELECT ts, tag
FROM android_logs
WHERE tag IN ('am_proc_start', 'am_proc_bound', 'am_anr', 'am_crash', 'am_kill')
ORDER BY ts DESC
LIMIT 20;
```

---

## AMS 的进程管理机制

### 进程优先级(oom_adj)的动态调整

Android 不是"前台就活着、后台就杀掉"这么简单。系统维护了一套精细的进程优先级体系,AMS 会根据进程中运行的组件状态动态调整每个进程的 `oom_adj`(Out-of-Memory Adjustment Score)。当内存紧张时,lmkd 根据这个分数决定先杀谁。

核心的优先级层级（从高到低）：

| 优先级 | oom_adj | 含义 | 典型场景 |
|--------|---------|------|----------|
| FOREGROUND | 0 | 前台进程 | 当前可见且正在交互的 Activity 所在进程 |
| PERCEPTIBLE_RECENT_FOREGROUND | 50 | 最近从 TOP 切到 FGS 的短期宽限 | 刚从前台退到后台,但还在执行 non-short FGS |
| VISIBLE | 100 | 可见进程 | Activity 可见但不在前台(如被透明 Activity 遮挡) |
| TOP_SLEEPING(`adjType`) | 0 | 顶层休眠分支 | 屏幕关闭前的 top app;`OomAdjuster` 标记 `adjType=top-sleeping`,但 `adj` 仍是 `FOREGROUND_APP_ADJ` |
| PERCEPTIBLE | 200 | 可感知 | 音乐播放、导航、常规 non-short 前台 Service |
| PERCEPTIBLE_MEDIUM | 225 | 中可感知 | 介于可感知与低可感知之间的缓冲档(android-16.0.0_r1 已存在) |
| PERCEPTIBLE_LOW | 250 | 低可感知 | 后台有轻量级操作 |
| BACKUP | 300 | 备份 | 正在执行备份操作 |
| HEAVY_WEIGHT | 400 | 重量级 | 后台 heavyweight 应用 |
| SERVICE | 500 | 服务 | 后台运行着普通 Service |
| HOME | 600 | 主页 | Launcher 进程 |
| PREVIOUS | 700 | 上一个 | 上一个后台 Activity |
| SERVICE_B | 800 | B 类服务 | 较老的后台 Service |
| CACHED / CACHED_EMPTY | 900+ | 缓存 | 纯缓存的后台进程 |
| CACHED_APP_LMK_FIRST | 950 | LMK 优先回收缓存 | lmkd 在回收时优先从此档开始杀(android-16.0.0_r1 已存在) |

这里要避免把前台 Service 写成固定的 100 档位。AOSP android-16.0.0_r1 的 `OomAdjuster` 里,常规 non-short FGS 会被抬到 `PERCEPTIBLE_APP_ADJ = 200`;只有最近刚从 TOP Activity 切到 FGS 的短期宽限窗口,才会临时抬到 `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ = 50`。

> 上表中 `PERCEPTIBLE_MEDIUM_APP_ADJ = 225` 和 `CACHED_APP_LMK_FIRST_ADJ = 950` 在 AOSP android-16.0.0_r1 的 `ProcessList.java` 中已存在,非 Android 17 新增。`TOP_SLEEPING` 在 `OomAdjuster.java` 中是 `adjType` 分支,不是 `PERCEPTIBLE_APP_ADJ = 200` 的独立表项。其余细分档位在厂商 ROM 中可能继续调整;FGS 的 50 / 200 档位已按 AOSP android-16.0.0_r1 的 `ProcessList.java` 与 `OomAdjuster.java` 核对。

AMS 调整 oom_adj 的核心方法是 `ActivityManagerService.updateOomAdjLocked()`。这个方法会遍历所有进程,根据每个进程中运行的组件(Activity、Service、Provider、广播接收器)的状态重新计算优先级。

一个进程可能同时持有多种组件。比如一个 App 进程可能既有前台 Activity,又有后台 Service 在跑。AMS 会取所有组件中最高的优先级作为进程的最终优先级。这个策略确保了"只要进程中有任何重要组件,就不会被轻易杀掉"。

### 进程启动流程

当用户点击一个 App 图标时,客户端入口是 Launcher 进程里的 `Instrumentation.execStartActivity()`。它通过 `ActivityTaskManager.getService().startActivity()` 进入 `system_server`,先由 ATMS / `ActivityStarter` 做任务容器和启动模式决策;只有在发现目标进程还不存在时,才会继续落到 AMS 的进程启动链路。`ActivityManagerService.startActivity()` 在现代版本里更多是兼容旧接口的转发层。

```text
Launcher / Instrumentation.execStartActivity()
  → ActivityTaskManager.getService().startActivity()   // Binder 到 system_server
    → ATMS.startActivity() / ActivityStarter.execute() // 先决定 Task / DisplayArea / 启动模式
      → 若目标进程不存在,ATMS.startProcessAsync()
        → ActivityManagerInternal.startProcess() / ProcessList.startProcessLocked()
          → ZygoteProcess.start()
            → Zygote fork 新进程
              → ActivityThread.main()
                → ActivityThread.attach()
                  → AMS.attachApplicationLocked()
                    → Application.onCreate()
                    → ATMS 继续调度 ActivityRecord 启动与可见化
```

在 Perfetto 中,这个过程通常表现为:
1. `android_logs` 里出现 `am_proc_start`
2. `zygote64`(或 `zygote`)中出现 fork 操作
3. 新进程出现,主线程开始执行 `bindApplication`
4. `android_logs` 里出现 `am_proc_bound`
5. `system_server` 侧出现 ATMS / WindowManager 的启动 slice,应用主线程进入 `Activity` 生命周期并准备首帧

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/core/java/android/app/Instrumentation.java` 的 `execStartActivity()` 调用 `ActivityTaskManager.getService().startActivity()`;`frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` 中 `startActivity()` 委托到 `mActivityTaskManager.startActivity()`;`frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java` 的 `startProcessAsync()` 通过 `ActivityManagerInternal::startProcess` 进入 AMS 进程启动路径]

### 进程回收策略

AMS 与 lmkd 的协作在 §4.4 中有详细讲解,这里简要提一下:当系统内存低于阈值时,lmkd 通过 `/proc/<pid>/oom_score_adj` 读取每个进程的优先级分数,从分数最高的缓存进程开始杀。AMS 的角色是维护这个分数；每次组件状态变化时,`updateOomAdjLocked()` 都会被触发。

在 Perfetto 中,我们可以通过 `Process Stats` Track 观察 `oom_score_adj` 的变化:当一个 App 从前台切到后台,你会看到它的 oom_score_adj 从 0 逐步升到 900+。如果随后出现 `am_kill` 事件,说明该进程被 lmkd 回收了。

```text
[图：Perfetto 中 oom_score_adj 变化时序图，展示 App 从前台到后台再到被杀的完整过程]
```

---

## AMS 与 ANR 检测

ANR(Application Not Responding)是 Android 稳定性的核心防线。AMS 不直接导致 ANR；它是“裁判”，负责检测 App 是否在规定时间内完成了应完成的操作。

ANR 检测可以先按三步理解:**开始计时、取消计时、超时上报**。

1. **开始计时**:AMS 在发起一个操作时(如启动 Service、分发广播),同时启动对应的超时计时器或延时消息。
2. **取消计时**:目标操作完成时,App 通过 Binder 通知 AMS,AMS 取消对应计时。
3. **超时上报**:如果计时到期时操作还没有完成,系统进入 ANR 处理流程。

> [来源: 掘金《Android ANR 的设计原理》]

这个模式贯穿所有 ANR 类型,后面按类型说明。

### Input ANR

**默认超时:5 秒**

Input ANR 的起点在 `InputDispatcher`,判责要继续看 WMS。AOSP android-16.0.0_r1 的主路径是:`InputDispatcher` 发现目标连接在 `waitQueue` 中超时后,调用 `notifyWindowUnresponsive()` 或 `notifyNoFocusedWindowAnr()`;`system_server` 里的 `InputManagerCallback` 把事件交给 `AnrController`,再由 `ActivityRecord.inputDispatchingTimedOut()` / AMS 决定是否进入应用级 ANR 流程。

关键路径:
```text
InputDispatcher.processAnrsLocked()
  → notifyWindowUnresponsive() / notifyNoFocusedWindowAnr()
    → InputManagerCallback
      → AnrController
        → ActivityRecord.inputDispatchingTimedOut() / AMS
          → AnrHelper.appNotResponding()
```

`notifyWindowUnresponsive()` 对应"窗口已经接到焦点,但事件长时间消费不掉";`notifyNoFocusedWindowAnr()` 对应"焦点事件来了,但系统还没有拿到可接收输入的焦点窗口"。排查 no-focused-window 场景时,还要看 WMS 里是否存在 pending focus request。焦点切换未完成,和应用主线程卡死,判责位置不同。

> [已验证: AOSP android-16.0.0_r1,`frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`、`frameworks/base/services/core/java/com/android/server/wm/InputManagerCallback.java`、`frameworks/base/services/core/java/com/android/server/wm/AnrController.java`]

在 Perfetto 中,Input ANR 通常表现为:输入事件长期停留在 `waitQueue`,同时目标窗口的主线程 Message、Binder 回调,或焦点切换路径没有按时完成。

### Broadcast ANR

**常见默认超时:前台广播 10 秒 / 普通广播 60 秒**

把现代广播模型直接写成 `BroadcastQueue.java` 里的两个固定队列,会把源码入口看错。AOSP android-16.0.0_r1 的做法是由 `ActivityManagerService` 组装广播参数,注入 `BroadcastConstants`,再由 `BroadcastQueueImpl` 执行分发、超时检查和 ANR 上报。

对性能分析,10 秒 / 60 秒仍可作为工作记忆;但"前台队列 = `mFgBroadcastQueue`、后台队列 = `mBgBroadcastQueue`"更接近早期实现。放到现代版本,入口应该看 `ActivityManagerService.java`、`BroadcastConstants.java` 和 `BroadcastQueueImpl.java`。

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`、`BroadcastConstants.java`、`BroadcastQueueImpl.java`]

### Service ANR

**超时阈值:前台 Service 20 秒 / 后台 Service 200 秒;`startForegroundService()` 的前台提升窗口需要单独看**

Service ANR 的计时发生在 `ActiveServices.realStartServiceLocked()` 调起 Service 的过程中。旧文章里常见的 `mAm.mHandler.sendMessageDelayed(SERVICE_TIMEOUT_MSG)` 口径不适用于 AOSP android-16.0.0_r1;当前实现通过 `ProcessAnrTimer` 管理执行中 Service 的超时。

```java
// 伪代码,基于 AOSP android-16.0.0_r1 ActiveServices.java 逻辑
// realStartServiceLocked 签名已简化,保留核心流程
void realStartServiceLocked(ServiceRecord r, ProcessRecord app,
        boolean execInFg) throws RemoteException {
    // 开始 Service 执行计时
    bumpServiceExecutingLocked(r, execInFg, "create");
    // 启动服务;完成回调由 App 端 serviceDoneExecuting 触发
    app.thread.scheduleCreateService(r, app.info, ...);
}

// scheduleServiceTimeoutLocked 在 bumpServiceExecutingLocked 中被调用
// 前台 20s,后台 200s
void scheduleServiceTimeoutLocked(ProcessRecord proc) {
    if (proc.mServices.numberOfExecutingServices() == 0
            || proc.getThread() == null) {
        return;
    }
    long delay = proc.mServices.shouldExecServicesFg()
            ? SERVICE_TIMEOUT : SERVICE_BACKGROUND_TIMEOUT;
    mActiveServiceAnrTimer.start(proc, delay);
    proc.mServices.noteScheduleServiceTimeoutPending(false);
}
```

完成回调不发生在 `service.onCreate()` 之前。AOSP android-16.0.0_r1 的 `ActivityThread.handleCreateService()` 先执行 `service.onCreate()`,完成 Service 创建,然后才通过 `ActivityManager.getService().serviceDoneExecuting()` 通知 AMS 本次执行结束。`ActiveServices.serviceDoneExecutingLocked()` 在进程没有执行中的 Service 后调用 `mActiveServiceAnrTimer.cancel(r.app)`;如果计时先到期,`ActiveServices.serviceTimeout()` 会生成 `TimeoutRecord` 并交给 `mAnrHelper.appNotResponding()`。

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/core/java/android/app/ActivityThread.java` 的 `handleCreateService()`、`frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` 的 `scheduleServiceTimeoutLocked()` / `serviceDoneExecutingLocked()` / `serviceTimeout()` 与内部 `ProcessAnrTimer`、`frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java`]

在 `startForegroundService()` 这段超时判责里,现代版本不能直接写成"固定 5 秒未调用 `startForeground()` 就 ANR"。AOSP android-16.0.0_r1 把这段窗口拆成了两段:`ActivityManagerConstants.DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS = 30000`,`DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS = 10000`。系统先给 Service 30 秒完成前台提升,超时后再进入额外 10 秒的 ANR 判责缓冲,对应 `ActiveServices.serviceForegroundTimeout()` 这条处理路径。更早版本里常见的 5 秒说法,只能带着版本前提使用。

### ContentProvider ANR

**相关超时不能压成一个固定的 10 秒**

现代 AOSP 的入口在 `ContentProviderHelper.getContentProviderImpl()`,排查时至少分三段看:

- provider publish:provider 进程 attach 后等待 publish,`ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`,默认 10 秒
- provider ready:调用方等待 provider ready,`ContentResolver.CONTENT_PROVIDER_READY_TIMEOUT_MILLIS`,默认 20 秒
- remote provider:已连到远端 provider 后的单次等待,`ContentResolver.CONTENT_PROVIDER_TIMEOUT_MILLIS`,默认 3 秒;组合等待窗口可看 `REMOTE_CONTENT_PROVIDER_TIMEOUT_MILLIS`

Provider 卡死时,需要分清卡在 publish、ready 还是 remote-provider 调用,再决定去看 AMS、provider 进程主线程,还是 Binder 调用栈。把这三类场景压成"AMS 里统一 10 秒超时",很容易把等待点和责任进程混在一起。

### AMS 的 ANR 数据采集

当任何类型的 ANR 触发后,AMS 会通过 `AnrHelper.appNotResponding()` 进入统一的处理管线:

1. **pre-dump**:如果检测到 AMS 或 WMS 的锁被长时间持有(> 500ms),先 dump 锁持有者的堆栈。
2. **dump stack traces**:向目标进程发送 `SIGNAL_ANR`(或通过 `Debug.dumpJavaBacktraces()`),获取主线程和相关线程的调用栈。android-16.0.0_r1 的 `StackTracesDumpHelper` 在 `/data/anr` 下创建 `anr_yyyy-MM-dd-HH-mm-ss-SSS` 形式的文件,不再是固定 `/data/anr/traces.txt`。
3. **CPU 使用率采集**:记录 ANR 发生前后各进程的 CPU 使用率,帮助判断是否因 CPU 争抢导致。
4. **弹出 ANR 对话框**:由 `AppNotRespondingDialog` 展示给用户(系统设置可关闭)。

`ProcessErrorStateRecord` 是管理单个进程错误状态(ANR/Crash)的核心类,在现代 Android 版本中接管了原来直接在 AMS 中处理的部分逻辑。

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/services/core/java/com/android/server/am/AnrHelper.java`、`frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java`]

在 Perfetto 中,ANR 事件可以通过 `android_logs` 里的 `am_anr` 精确定位。SQL 查询:

```sql
SELECT ts, tag
FROM android_logs
WHERE tag = 'am_anr'
ORDER BY ts DESC
LIMIT 10;
```

---

## AMS 的 Activity 管理

### Activity 栈与 Task 管理

如果你看的还是早期 Android 文章,很容易把这部分记成 `TaskStack` + `Task`。这个说法放在历史版本里不算错,但放到 Android 10 之后就会把旧模型和现行实现混在一起。当前 AOSP 里,Activity 与 Task 的容器管理已经从 AMS 主类拆到 `ActivityTaskManagerService`(ATMS)和 `WindowManager` 侧。`ActivityManagerService.startActivity()` 现在只是把请求转给 `mActivityTaskManager.startActivity()`;"这个 Activity 落到哪个任务、哪个显示区域、是否复用已有任务",由 `ActivityStarter`、`RootWindowContainer`、`TaskDisplayArea` 和 `Task` 这一套容器决定。

从容器层级看,现代实现更接近下面这个结构:

```text
RootWindowContainer
  └─ DisplayContent
      └─ TaskDisplayArea
          └─ Task(root task / leaf task)
              └─ ActivityRecord
```

`RootWindowContainer` 是整台设备的顶层窗口容器;每个 `DisplayContent` 下面可以有一个或多个 `TaskDisplayArea`;`TaskDisplayArea` 的孩子既可以是 `Task`,也可以是嵌套的 `TaskDisplayArea`;`Task` 本身既可能是用户在 Recents 里看到的一张任务卡片,也可能继续包含子 `Task`。所以今天谈"Activity 落在哪个栈里"时,更准确的表述是:ATMS / WindowManager 在目标 `TaskDisplayArea` 中选择或创建合适的 `Task`,再把 `ActivityRecord` 挂进去。

落实到启动链路,`ActivityStarter.startActivityInner()` 会先计算 `mPreferredTaskDisplayArea`,再通过 `TaskDisplayArea.getOrCreateRootTask()` 找到或创建目标 root task,最后把新的 `ActivityRecord` 放进目标 `Task`。这对性能分析有一个直接影响:我们不能再假设 Perfetto 里存在一个统一的 `am_activity_launch` EventLog 作为启动锚点。应该把 `android_logs` 里的 `am_proc_start` / `am_proc_bound`、`system_server` 侧的 ATMS / WindowManager slice,以及应用主线程的 `bindApplication`、Activity 生命周期和首帧 `doFrame` 串起来看。AMS 负责把进程和全局状态管起来,ATMS 负责把 Activity 放到正确的容器里,这两条线要放在一起看,启动链路才完整。

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` 中 `startActivity()` 委托给 `mActivityTaskManager.startActivity()`;`frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java`、`TaskDisplayArea.java`、`Task.java` 定义了当前任务容器层级]

### Activity 启动耗时在 Perfetto 中的定位

分析 Activity 启动耗时,我们通常关注以下几个时间节点:

1. 用户点击 Launcher 图标(或系统发起启动 Intent)
2. `am_proc_start`(如果是冷启动):AMS 开始创建进程
3. `am_proc_bound`:新进程与 `system_server` 建立连接
4. Binder `attachApplication` / 主线程 `bindApplication`
5. `Application.onCreate()` 与 `Activity.onCreate()` → `onResume()`
6. 第一帧 `doFrame`:首帧渲染完成

冷启动场景下,要衡量的是"启动请求发出"到首帧 `doFrame` 之间的总时间;`am_proc_start` 只是其中的进程创建起点,不等于完整启动耗时。

### 冷启动归因:ApplicationStartInfo

Android 16 (API 36)引入了 `ApplicationStartInfo.getStartComponent()` API,可以精确区分当前冷启动是由哪种组件触发的:Activity、Service、Receiver 还是 ContentProvider。获取入口是 `ActivityManager.getHistoricalProcessStartReasons(int maxNum)`,返回 `ApplicationStartInfo` 列表。在没有这个 API 之前,分析启动耗时只能从 Trace 上按时间顺序推断"看起来是哪个组件先被调用",不够准确。

实际操作中,在 Perfetto 里可以通过以下方式辅助归因:

- 如果 `am_proc_start` 之后紧接着 `bindApplication` → `Activity.onCreate()`,大概率是 Activity 启动
- 如果 `bindApplication` 之后先走 `onCreate` → `onStartCommand()`,是 Service 启动
- 如果进程启动后直接进入 `onReceive()`,是静态广播触发

Android 16+ 上,用 `ApplicationStartInfo.getStartComponent()` 直接获取组件类型,不再需要从 Trace 时序推断。这对区分"用户点击触发的冷启动"和"后台组件触发的冷启动"尤其有用：前者应该优先优化,后者可能只需要做延迟初始化。

> [已验证: Android 16 / API 36,`android.app.ApplicationStartInfo#getStartComponent()`;获取入口为 `ActivityManager#getHistoricalProcessStartReasons(int)`]

```text
[图：Perfetto 中冷启动的完整 Trace 片段，标注上述 6 个关键时间节点]
```

### manifest 中的 `recreateOnConfigChanges`

这一项不能写成"Android 17 新引入"。当前公开 AOSP 在 `frameworks/base/core/res/res/values/attrs_manifest.xml` 里已经定义了 `recreateOnConfigChanges`,而且注释写得很直白:从 Android O 开始,`mcc` 和 `mnc` 这两类配置变化默认不会再触发 Activity 重建;如果应用确实希望在这两种变化发生时重走一次 Activity 重建流程,需要在 manifest 里显式声明 `recreateOnConfigChanges`。

因此我们分析配置变更带来的重启问题时,不能把 `recreateOnConfigChanges` 当成一个"通用的 Activity 重启开关"。就公开源码可验证的语义来看,它主要针对 `mcc` / `mnc` 这类运营商和区域配置变化。屏幕旋转、夜间模式、窗口尺寸变化这类更常见的场景,仍然应该先看 `android:configChanges`、`onConfigurationChanged()` 和实际生命周期回调,而不是先假设系统会因为 `recreateOnConfigChanges` 把 Activity 杀掉重建。

从性能角度,这个属性主要影响少见但难查的区域 / 运营商切换场景,不是高频日常交互。假如你在跨境 SIM、eSIM 切换或运营商配置更新后看到 Activity 没有按预期重建,先查 manifest 是否声明了 `mcc|mnc` 的 `recreateOnConfigChanges`,再决定是否继续沿着 AMS / ATMS 的重启链路追。至少就当前公开的 AOSP 与 Android Developers 文档,我们没有证据把它解释成 Android 17 的通用行为变更。

> [已验证: AOSP android-16.0.0_r1,`frameworks/base/core/res/res/values/attrs_manifest.xml`;Android Developers `android.R.attr#recreateOnConfigChanges`]

---

## AMS 的 Service 管理

### 前台服务(Foreground Service)的演进

前台服务是 Android 中一种重要的后台执行机制,允许 App 在用户不可见时继续执行关键任务(如音乐播放、导航、文件下载),代价是必须显示一个持续通知。

**Android 11 (API 30)** 开始把后台启动 FGS 的敏感资源访问单独加上约束。后台拉起的 FGS 不能默认访问相机、麦克风、位置;Manifest 里也要补 `camera` / `microphone` 等对应的 FGS type。

**Android 12 (API 31)** 引入了一个重大变更:**禁止从后台启动前台服务**。如果 App 在后台时调用 `startForegroundService()`,系统会抛出 `ForegroundServiceStartNotAllowedException`。例外情况包括:从用户可见状态转换时、收到高优先级 FCM 消息时、以及特定的系统组件调用时。

同时,Android 12 引入了 **Phantom Process Killer**,监控 App 的子进程(通过 `Runtime.exec()` 或 JNI fork),限制系统级总数为 32 个,超出的会被杀掉。

**Android 13 (API 33)** 增加了 FGS Task Manager 和 `POST_NOTIFICATIONS` 运行时权限。即使通知权限被拒,用户仍然可以在 FGS Task Manager 里看到并停止正在运行的前台服务。

**Android 14 (API 34)** 进一步要求:
- 每个 FGS 必须在 Manifest 中声明 `foregroundServiceType`(如 `camera`、`connectedDevice`、`dataSync`、`health`)。
- 必须申请对应类型的权限(如 `FOREGROUND_SERVICE_CAMERA`),否则 `SecurityException`。
- 即使满足后台启动 FGS 的豁免条件,如果 FGS 需要"while-in-use"权限(如位置、相机、麦克风),在 App 处于后台时也不能访问这些资源。

**Android 15 (API 35)** 对 `dataSync` 和新增的 `mediaProcessing` 类型的 FGS 加了运行时间上限(`dataSync` 最长 6 小时)。

**Android 16 (API 36)** 要求后台 Job(包括通过 FGS 启动的)遵守各自的运行配额。

**Android 17 (API 37)** 进一步限制后台音频行为,没有"while-in-use"能力的 FGS 在后台调用音频 API 会静默失败。

> [已验证: 官方文档, developer.android.com - Behavior changes for Android 11/12/13/14/15/16/17]

### 后台启动服务的限制链

从 Android 8.0 开始,Google 就在逐步限制后台启动 Service 的能力。整个演进路线:

- **Android 8.0**:限制后台 App 调用 `startService()`,必须使用 `startForegroundService()`。
- **Android 11**:后台启动的 FGS 访问相机 / 麦克风 / 位置能力继续受限。
- **Android 12**:限制后台启动 FGS(`ForegroundServiceStartNotAllowedException`)。
- **Android 13**:FGS Task Manager + `POST_NOTIFICATIONS` 让长驻服务更容易被看见和停止。
- **Android 14**:FGS 类型声明强制化 + while-in-use 权限限制。
- **Android 15**:`dataSync` FGS 运行时间上限。
- **Android 16**:后台 Job 配额执行。
- **Android 17**:后台音频 API 强制限制。

Google 的推荐替代方案是使用 `WorkManager` 来调度可延迟的后台任务,只在需要用户可感知的长时间运行时才使用 FGS。

除了版本演进带来的行为变更，Service 管理还有一个容易在 Perfetto 中暴露的点：`mServices`（`ActiveServices` 实例）上的锁竞争。当多个 App 同时调起或绑定 Service 时，Binder 线程池的线程会在 AMS 的 synchronized 方法上排队，这是 `system_server` 响应的常见瓶颈。下面从结构位置和诊断路径展开。

### AMS mServices 锁竞争与 Perfetto 诊断

**结构位置**:`ActivityManagerService` 持有 `ActiveServices mServices` 引用,`ActiveServices` 构造时保存 `final ActivityManagerService mAm`:

```java
// ActivityManagerService.java (android14-release)
final ActiveServices mServices;

// ActiveServices.java (android14-release)
public final class ActiveServices {
    final ActivityManagerService mAm;
    final SparseArray<ServiceMap> mServiceMap = new SparseArray<>();
    final ArrayList<ServiceRecord> mPendingServices = new ArrayList<>();
    final ArrayList<ServiceRecord> mRestartingServices = new ArrayList<>();
    ...
}
```

**Service 启动的锁路径**:`Context.startService()` → `AMS.startService()` **\[synchronized AMS]**,在 AMS 锁内部调用 `mServices.startServiceLocked()` → `bringUpServiceLocked()` → `realStartServiceLocked()`。`realStartServiceLocked` 在持有 AMS 锁的同时通过 `app.thread.scheduleCreateService()` 向 App 进程发起跨进程调用。

**并发竞争场景**:多个 App 同时 `bindService`/`startService` 时,Binder 线程池中的线程在 AMS 的 `synchronized` 方法级锁上排队。Logcat 会出现 `Long monitor contention with owner Binder:1234 at com.android.server.am.ActivityManagerService$UiHandler`(Blocking time: 500ms+)。

**Perfetto 诊断路径**:

```sql
-- Perfetto SQL:在 system_server 中定位 AMS / ActiveServices monitor contention
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  blocked_thread_name,
  blocking_thread_name,
  short_blocked_method,
  short_blocking_method,
  dur / 1e6 AS duration_ms,
  waiter_count
FROM android_monitor_contention
WHERE process_name = 'system_server'
  AND (blocked_method LIKE '%ActivityManagerService%'
       OR blocking_method LIKE '%ActivityManagerService%'
       OR blocked_method LIKE '%ActiveServices%'
       OR blocking_method LIKE '%ActiveServices%')
ORDER BY dur DESC
LIMIT 20;
```

**因果链还原**:在 Perfetto UI 中,`binder_transaction` 结束时间点与紧接着的 `monitor_contention` 开始时间点重叠,说明是 Binder 线程在等待 AMS 锁。Thread State track 中 Binder 线程从 Running 切换到 Sleeping(`futex_wait`)的切片宽度即为锁等待时长。

> [来源: AOSP android14-release `ActiveServices.java` / `ActivityManagerService.java`;Perfetto monitor contention 文档]

---


## AMS 的广播管理

### 广播分发机制

AMS 仍然负责广播匹配、调度和 ANR 判责,但源码入口不能只盯着旧版 `BroadcastQueue.java`。AOSP android-16.0.0_r1 的实现由 AMS 组装 `BroadcastConstants`,再交给 `BroadcastQueueImpl` 执行分发。对性能分析,前台广播和普通广播仍然可以视为两组不同配置,但不宜把现代实现硬写成 `mFgBroadcastQueue` / `mBgBroadcastQueue` 这一对固定字段。

分发流程:

1. 发送方通过 `Context.sendBroadcast()` → Binder 调用到 AMS。
2. AMS 根据 Intent 匹配已注册的 Receiver(包括静态和动态),生成目标列表。
3. 对于有序广播,按 priority 排序后依次分发;对于无序广播,并行分发。
4. `BroadcastQueueImpl.dispatchReceivers()` 在调度 Receiver 前把投递状态切到 `DELIVERY_SCHEDULED`,并按前台 / 后台广播配置启动 delivery timeout;Receiver 完成后再取消计时。超时先到时,`finishReceiverActiveLocked(... DELIVERY_TIMEOUT ...)` 进入广播 ANR 路径。

**按进程广播队列架构（Android 14/15/16）**：Android 14/15 的源码类名是 `BroadcastQueueModernImpl`,Android 16 的类名是 `BroadcastQueueImpl`,两者都围绕 `BroadcastProcessQueue` 按进程组织广播投递。旧实现中,一个进程内多个 Receiver 的分发是串行的,如果前面的 Receiver 执行慢,后面同一进程内的 Receiver 也会被阻塞——这就是"队头阻塞"（head-of-line blocking）。按进程队列把分发粒度从"全局队列"改到"进程队列":同一个进程的 Receiver 仍然串行,不同进程之间可以并行分发,减少慢进程拖累全局广播。对性能分析的影响是,在 Perfetto 中看到广播 ANR 时,要把 `BroadcastQueueImpl` 的 delivery timeout、目标进程主线程 `onReceive()`、以及同进程前序 Receiver 放在一起判断。

> [已验证: AOSP android-14/15 `BroadcastQueueModernImpl.java`;AOSP android-16.0.0_r1 `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java` + `BroadcastProcessQueue.java`]

### 静态广播 vs 动态广播的性能差异

静态广播(在 Manifest 中声明)和动态广播(代码中 `registerReceiver()`)的主要区别在于:

- **静态广播**:即使 App 进程不在,系统也会通过 AMS 启动 App 进程来接收广播。因此一次静态广播触发可能导致进程冷启动,性能开销大。
- **动态广播**:只在进程存活时有效,不需要冷启动,性能开销小。

从系统性能的角度,大量注册静态广播的 App 会在系统事件(如 `BOOT_COMPLETED`、`CONNECTIVITY_CHANGE`)触发时引发"进程创建风暴"：AMS 需要同时启动大量进程。这也是 Android 逐步限制静态广播的原因之一。

### Android 14+ 的广播限制

Android 14 对广播做的变化,重点不在 Extra 大小,而在**投递时机**和**动态注册边界**。

第一层变化发生在进程处于 cached state 时。官方行为变更文档明确写到,`context-registered broadcasts` 可以在应用进入 cached state 后被放进队列,等应用回到前台或离开 cached state 再投递。Manifest 中声明的广播不走这套排队逻辑,系统甚至会把应用从 cached state 拉出来立即投递。这会直接改变 Perfetto 里理解广播执行时机的方式:发送时刻和 `onReceive()` 开始执行的时刻,Android 14 之后不一定重合。

第二层变化是动态注册 Receiver 的导出属性。面向 Android 14+ 的应用在调用 `Context.registerReceiver()` 时,需要显式指定 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`,除非它只接收 system broadcast。这个改动是安全约束,不是性能优化本身,但它会影响旧代码能不能顺利走到广播分发路径。

对性能分析来说,我们至少要记住两件事。第一,cached 进程里的动态广播可能被延后,因此不能再用"发送广播后主线程没立刻响应"直接推断 AMS 分发慢。第二,Manifest 广播依旧可能把进程拉起,所以 `BOOT_COMPLETED`、网络变化、电量状态切换这类广播仍然可能造成进程批量唤醒,低端设备上尤其容易放大冷启动风暴和后台抖动。

> [已验证: Android Developers `Behavior changes: all apps`(Android 14,cached state 下的 context-registered broadcast 排队)与 `Behavior changes: Android 14`(runtime-registered receiver 必须显式声明 `RECEIVER_EXPORTED` / `RECEIVER_NOT_EXPORTED`)]

---

## AMS 在 Perfetto 中的具体表现

前文我们已经分散地提到了各种 Trace 事件,这里做一个集中梳理。

### system_server 中的关键线程

在 Perfetto 中打开 `system_server` 进程,你会看到很多线程。和 AMS 最相关的几个:

| 线程名 | 作用 |
|--------|------|
| `ActivityManager` | AMS 主逻辑线程,处理组件调度、进程管理 |
| `Binder:system_server_X` | Binder 线程池(通常 16 个),接收来自 App 的跨进程调用 |
| `android.fg` | 前台 Handler 线程,处理一些后台任务(如 ANR dump) |
| `android.display` | Display 相关后台任务 |
| `TaskPersister` | 持久化 Task 状态到磁盘 |

### 典型场景的 Trace 特征

**冷启动场景:**
1. `android_logs` 里出现 `am_proc_start`
2. `zygote64` 出现 fork(一个极短的 CPU burst)
3. 新进程出现,`main` 线程开始执行 `bindApplication`
4. `Binder:system_server_X` 上出现 `attachApplication` 调用
5. 新进程 `main` 线程执行 `Application.onCreate()` 和 `Activity` 生命周期
6. `system_server` 侧出现 ATMS / WindowManager 的启动 slice
7. 新进程渲染第一帧

**ANR 场景:**
1. 主线程上某个 Message 执行时间过长(或被阻塞)
2. `android_logs` 里出现 `am_anr`
3. `system_server` 的 Binder 线程或 `ActivityManager` 相关线程开始 `dumpStackTraces`
4. 目标进程收到 signal,各线程堆栈被 dump
5. 如果启用了 ANR 对话框,`system_server` 中出现 `AppNotRespondingDialog` 相关活动

**进程被杀场景:**
1. `Process Stats` Track 中看到目标进程的 `oom_score_adj` 逐步升高
2. 系统内存水位上升
3. `android_logs` 里出现 `am_kill`
4. 目标进程的所有线程消失

```text
[图：冷启动、ANR、进程被杀三种典型场景的 Perfetto Trace 对比截图]
```

---

## 与其他机制的关系

- **§1.3 进程模型**:AMS 是进程创建和管理的执行者。理解进程模型是理解 AMS 行为的前提。
- **§1.4 Binder IPC**:AMS 几乎所有对外交互都走 Binder。`Binder:system_server` 线程池的饱和直接影响 AMS 的响应能力。
- **§2.4 Choreographer**:Activity 启动完成后,首帧渲染由 Choreographer 驱动。AMS 负责的是"Activity 启动"这个阶段。
- **§4.4 LMK**:AMS 维护 oom_adj,lmkd 执行杀进程。两者配合完成内存回收。
- **§8.2 App 启动分析**:冷启动的完整分析需要将 AMS 行为(进程创建)和 App 行为(Application/Activity 初始化)结合来看。

---

## 版本演进

| Android 版本 | 关键变更 | 影响 |
|-------------|---------|------|
| Android 8.0 (API 26) | 后台启动 Service 限制 | 后台 App 必须使用 `startForegroundService()` |
| Android 9.0 (API 28) | App Standby Buckets | AMS 根据使用频率限制后台执行 |
| Android 10 (API 29) | 后台 Activity 启动限制 | 后台 App 不能随意弹出 Activity |
| Android 11 (API 30) | 后台启动 FGS 访问敏感资源受限 | 后台拉起的 FGS 不能默认访问相机 / 麦克风 / 位置,Manifest 要补对应 FGS type |
| Android 12 (API 31) | 后台 FGS 启动限制 + Phantom Process Killer | `ForegroundServiceStartNotAllowedException` |
| Android 13 (API 33) | FGS Task Manager + `POST_NOTIFICATIONS` | 长驻前台服务更容易被用户感知、停止和审计 |
| Android 14 (API 34) | FGS 类型声明强制化 + while-in-use 限制 | 必须声明 `foregroundServiceType` |
| Android 15 (API 35) | dataSync FGS 运行时间上限(6h) | 长时间后台数据同步需换方案 |
| Android 16 (API 36) | 后台 Job 配额 + ProfilingManager | 后台任务受配额限制 |
| Android 17 (API 37) | 后台音频 API 限制 | 后台调用音频播放 / 焦点 / 音量 API 可能失败或静默无效 |

> [已验证: 官方文档, developer.android.com - 各版本 Behavior changes]

---

## 常见问题与误区

**误区 1:"ANR 超时是 5 秒"**
不准确。5 秒只是 Input ANR 的超时。Service ANR 前台是 20 秒、后台是 200 秒;广播前台是 10 秒、后台是 60 秒。不同类型的 ANR 有不同的超时阈值。

**误区 2:"进程被杀一定是因为内存不足"**
不一定。除了 lmkd 的内存回收,进程还可能因为 ANR(用户选择"关闭")、Crash、或者 AMS 主动杀(如 App 后台行为违规)而被终止。需要看 `am_kill` 事件的具体原因字段。

**误区 3:"前台 Service 不会被杀"**
前台 Service 不是固定的 `100` 档。常规 non-short FGS 在 AOSP android-16.0.0_r1 的 `OomAdjuster` 里通常落在 perceptible 档(`PERCEPTIBLE_APP_ADJ = 200`),只有 recent-top → FGS 的短期宽限窗口才会临时抬到 `50`。如果系统极端缺内存,或者 Service 本身出现 ANR / Crash,FGS 仍然会被杀;而且 Android 12+ 对后台启动 FGS 有严格限制,不是想用就能用的。

**误区 4:"`am_proc_start` 时间就是冷启动耗时"**
`am_proc_start` 只标记了 AMS 向 Zygote 发起 fork 请求的时刻。完整冷启动耗时应该从用户点击 Launcher 图标(或系统发起启动 Intent)开始,到首帧 `doFrame` 结束。中间还包括 Zygote fork、Application 初始化、Activity 生命周期执行、首帧渲染等多个阶段。

**误区 5:"后台 App 的广播不影响前台性能"**
影响。如果大量后台 App 注册了静态广播,系统事件触发时 AMS 会尝试启动多个进程,这会抢占 CPU 和 I/O 资源,间接影响前台 App 的性能。在低端设备上尤其明显。

---

## 参考资料

### AOSP 源码路径
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` - AMS 主类
- `frameworks/base/core/java/android/app/Instrumentation.java` - 客户端 `execStartActivity()` 入口
- `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java` - Activity / Task 管理入口
- `frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java` - Activity 记录与 input dispatch timeout 判责入口
- `frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java` - 顶层任务 / 显示容器
- `frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java` - Display 下的任务容器
- `frameworks/base/services/core/java/com/android/server/wm/Task.java` - Task 定义与 Recents 语义
- `frameworks/base/core/res/res/values/attrs_manifest.xml` - `recreateOnConfigChanges` 定义
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` - Service 管理与 create-service ANR
- `frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java` - ANR 计时器基类;`ActiveServices.java` 内部定义 `ProcessAnrTimer` / `ServiceAnrTimer`
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java` - startForegroundService 相关超时配置
- `frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java` - `oom_adj` / `procState` 动态计算
- `frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java` - 广播超时与调度参数
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java` - 广播分发与超时执行
- `frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java` - 按进程组织的广播投递队列
- `frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java` - Provider 获取与等待流程
- `frameworks/base/core/java/android/content/ContentResolver.java` - Provider publish / ready / remote-provider timeout 常量
- `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java` - ANR 统一处理管线
- `frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java` - ANR 堆栈 dump 文件创建与写入
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` - 进程列表与 lmkd 交互
- `frameworks/base/core/java/android/app/ActivityThread.java` - App 端主线程入口
- `frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags` - `am_*` EventLog 标签定义
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` - Input 事件分发与 waitQueue 检查
- `frameworks/base/services/core/java/com/android/server/wm/InputManagerCallback.java` - Input → WMS 回调桥接
- `frameworks/base/services/core/java/com/android/server/wm/AnrController.java` - WMS 侧输入 ANR 归因
- `frameworks/base/core/java/android/app/IActivityManager.aidl` - AMS 的 Binder 接口定义

### 官方文档
- [Behavior changes: all apps on Android 11](https://developer.android.com/about/versions/11/behavior-changes-all) - 后台启动 FGS 访问敏感资源的限制
- [Behavior changes: Android 12](https://developer.android.com/about/versions/12/behavior-changes-12) - FGS 后台启动限制
- [Behavior changes: all apps on Android 13](https://developer.android.com/about/versions/13/behavior-changes-all) - FGS Task Manager 与通知权限变化
- [Behavior changes: Android 14](https://developer.android.com/about/versions/14/behavior-changes-14) - 动态注册 Receiver 导出属性与 FGS 相关约束
- [Behavior changes: all apps on Android 14](https://developer.android.com/about/versions/14/behavior-changes-all) - cached state 下的 context-registered broadcast 排队
- [Behavior changes: all apps on Android 17](https://developer.android.com/about/versions/17/behavior-changes-all) - 后台音频 API 限制
- [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services) - FGS 官方指南
- [Background execution limits](https://developer.android.com/about/versions/oreo/background) - Android 8.0 后台限制
- [android.R.attr#recreateOnConfigChanges](https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges) - `recreateOnConfigChanges` 属性说明

### 深入阅读
- 《Android ANR 的设计原理》- 掘金,ANR 埋雷-拆雷-爆雷机制的源码级分析
- 《Android 卡顿与 ANR 的分析实践》- 掘金/Shopee 技术团队,Looper+MessageQueue 模型与 ANR 关系
- 《从 ApplicationExitInfo 看 Android 应用的退出类型》- 进程退出原因分类

---
