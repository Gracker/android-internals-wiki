---
title: "Activity Manager Service 与性能分析"
chapter: "1.8"
status: ready-for-review
drafted_date: "2026-04-05"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers behavior changes 14/17"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java"
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
    path: "https://developer.android.com/about/versions/12/behavior-changes-12"
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
reviewed_date: "2026-04-10"
task6_result: needs-rework
pipeline_stage: task2b_pending
task6_state: revisiting
task9_result: needs-rework
task9_state: reviewed
task2b_result: pending
task2b_state: pending
---

# 1.8 Activity Manager Service 与性能分析

## 为什么要了解 AMS

如果你做过 Android 性能优化，几乎不可能绕开 AMS。应用冷启动时，是 AMS 向 Zygote 发出 fork 请求来创建你的进程；用户按 Home 键时，是 AMS 调整你进程的 oom_adj，决定你在内存紧张时是第一个被杀还是最后一个；当你遇到 ANR，超时检测的"埋雷-爆雷"逻辑就住在 AMS 内部。

更直白地说：**你用 Perfetto 分析启动耗时、进程被杀、ANR、前台服务超时这些问题时，Trace 里看到的 `am_proc_start`、`am_anr`、`am_crash` 这些事件，全部来自 AMS。** 不了解 AMS 的工作方式，这些事件就是 Trace 里的"黑盒"——你看到它发生了，但不知道为什么、怎么追。

读完本节，我们将能够在 Perfetto 中识别 AMS 的关键 Track 和事件，理解进程优先级的动态调整逻辑，以及各类 ANR 的触发路径。这不是为了让你成为 AMS 的开发者，而是让你在分析性能问题时知道"该往哪里看"。

> 阅读本节之前，建议先了解 §1.3 进程模型和 §1.4 Binder IPC，因为 AMS 的几乎所有操作都涉及跨进程调用和进程生命周期管理。

---

## AMS 在 Android 架构中的角色

AMS 运行在 `system_server` 进程中，是 Android 最核心的系统服务之一。它负责进程的创建、优先级调整和回收，负责 Service、BroadcastReceiver、ContentProvider 的系统侧调度，也承接 ANR、Crash、前后台状态变化这些全局管理逻辑。对于 Activity，现代 Android 已经把大部分任务与窗口容器管理拆到了 `ActivityTaskManagerService`（ATMS）和 `WindowManagerService`（WMS）一侧，所以我们分析启动和任务切换时，不能只盯着 AMS。

从架构上看，AMS 和几个关键服务之间有紧密的协作关系：

- **PackageManagerService（PMS）**：AMS 在启动 Activity/Service 时，需要通过 PMS 解析目标组件的信息（权限、声明、进程名等）。
- **ActivityTaskManagerService（ATMS） / WindowManagerService（WMS）**：Activity 需要窗口才能显示，现代 AOSP 里任务与窗口容器管理主要落在 ATMS / WMS。AMS 更多负责进程、Service、Broadcast 和 ANR 管线；ATMS 负责 Activity / Task 的调度；WMS 负责窗口、焦点和输入相关状态。Input ANR 的检测也要看 WMS 侧的 `InputDispatcher`。
- **SurfaceFlinger**：虽然不直接交互，但 AMS 决定了哪个 Activity 可见 → WMS 据此决定 Surface 的层级 → SurfaceFlinger 合成显示。
- **ProcessList**：AMS 内部维护的进程列表，和 lmkd（Low Memory Killer Daemon）协作完成内存回收。我们在 §4.4 会专门讲这个机制。

应用进程通过 `ActivityManager`（客户端代理类）与 AMS 通信。这层通信走的是 Binder IPC，`IActivityManager.aidl` 定义接口，`ActivityManagerService` 实现接口。需要区分的是，`startActivity()` 这类 Activity / Task 相关调用虽然入口还在 AMS 对外接口上，但会继续委托给 `ActivityTaskManagerService`。所以你在 Perfetto 中看到的 `Binder:system` 线程调用，往往只是系统服务链路的起点，不是全部。

```
[图：AMS 在系统架构中的位置，展示 system_server 内 AMS 与 PMS/WMS 的关系，以及 App 进程通过 Binder 与 AMS 通信的路径]
[待高爷补充：系统架构图]
```

### 在 Perfetto 中定位 AMS

在 Perfetto 中分析 AMS 相关行为时，我们主要关注 `system_server` 进程中的以下线程和事件：

**关键线程：**
- `ActivityManager` 线程：处理大部分 AMS 主逻辑（组件调度、进程管理）。
- `Binder:system_server` 线程池（通常 16 个线程）：接收来自 App 进程的 Binder 调用。
- `android.fg` / `android.display` 线程：处理前台和显示相关的后台任务。

**关键 Trace 事件（在 ftrace 或 atrace 中搜索 `am_` 前缀）：**
- `am_proc_start`：AMS 通知 Zygote fork 新进程。
- `am_proc_bound`：新进程启动完成，与 AMS 建立 Binder 连接。
- `am_anr`：检测到 ANR，开始收集 trace。
- `am_crash`：应用崩溃。
- `am_activity_launch`：Activity 启动。
- `am_kill` / `am_pss`：进程被杀或内存统计。

> [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java — EventLogTags 定义]

在 Perfetto 的 SQL 视图中，这些事件可以通过 `SELECT * FROM slice WHERE name LIKE 'am_%'` 来查询。

---

## AMS 的进程管理机制

### 进程优先级（oom_adj）的动态调整

Android 不是"前台就活着、后台就杀掉"这么简单。系统维护了一套精细的进程优先级体系，AMS 会根据进程中运行的组件状态动态调整每个进程的 `oom_adj`（Out-of-Memory Adjustment Score）。当内存紧张时，lmkd 根据这个分数决定先杀谁。

核心的优先级层级（从高到低）：

| 优先级 | oom_adj | 含义 | 典型场景 |
|--------|---------|------|----------|
| FOREGROUND | 0 | 前台进程 | 当前可见的 Activity 所在进程 |
| FOREGROUND_SERVICE | 100 | 前台服务 | 正在执行前台 Service 的进程 |
| TOP_SLEEPING | 200 | 顶层休眠 | 屏幕关闭但之前是前台 |
| VISIBLE | 100 | 可见进程 | Activity 可见但不在前台（如被透明 Activity 遮挡） |
| PERCEPTIBLE | 200 | 可感知 | 正在播放音乐等用户可感知的后台操作 |
| PERCEPTIBLE_LOW | 250 | 低可感知 | 后台有轻量级操作 |
| BACKUP | 300 | 备份 | 正在执行备份操作 |
| HEAVY_WEIGHT | 400 | 重量级 | 后台 heavyweight 应用 |
| SERVICE | 500 | 服务 | 后台运行着 Service |
| HOME | 600 | 主页 | Launcher 进程 |
| PREVIOUS | 700 | 上一个 | 上一个后台 Activity |
| SERVICE_B | 800 | B 类服务 | 较老的后台 Service |
| CACHED / CACHED_EMPTY | 900+ | 缓存 | 纯缓存的后台进程 |

> [待验证：上表具体数值在 Android 16/17 中可能有微调，不同厂商可能自定义层级]

AMS 调整 oom_adj 的核心方法是 `ActivityManagerService.updateOomAdjLocked()`。这个方法会遍历所有进程，根据每个进程中运行的组件（Activity、Service、Provider、广播接收器）的状态重新计算优先级。

值得关注的细节是：一个进程可能同时持有多种组件。比如一个 App 进程可能既有前台 Activity，又有后台 Service 在跑。AMS 会取所有组件中最高的优先级作为进程的最终优先级——这个策略确保了"只要进程中有任何重要组件，就不会被轻易杀掉"。

### 进程启动流程

当用户点击一个 App 图标时，Launcher 通过 Binder 调用 AMS 的 `startActivity()`。如果目标 App 的进程还不存在，AMS 会走一个完整的进程创建链路：

```
Launcher.startActivity()
  → AMS.startActivity()          // Binder 调用到 system_server
    → AMS.startProcessAsync()    // 异步发起进程创建
      → ZygoteProcess.start()    // 通过 Socket 通知 Zygote
        → Zygote fork 新进程
          → new 进程执行 RuntimeInit.applicationInit()
            → ActivityThread.main()   // App 主线程启动
              → ActivityThread.attachApplication()  // 通知 AMS 进程已就绪
                → AMS.attachApplicationLocked()     // 绑定 Application
                  → 回调 Application.onCreate()
                  → 调度第一个 Activity 的创建
```

在 Perfetto 中，这个过程表现为：
1. `system_server` 的 `ActivityManager` 线程中出现 `am_proc_start` 切片
2. `zygote64`（或 `zygote`）中出现 fork 操作
3. 新进程出现，主线程开始执行
4. `am_proc_bound` 标记进程与 AMS 的连接建立
5. `am_activity_launch` 标记 Activity 开始加载

> [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java — startProcessLocked → ZygoteProcess.start]

### 进程回收策略

AMS 与 lmkd 的协作在 §4.4 中有详细讲解，这里简要提一下：当系统内存低于阈值时，lmkd 通过 `/proc/<pid>/oom_score_adj` 读取每个进程的优先级分数，从分数最高的缓存进程开始杀。AMS 的角色是维护好这个分数——每次组件状态变化时，`updateOomAdjLocked()` 都会被触发。

在 Perfetto 中，我们可以通过 `Process Stats` Track 观察 `oom_score_adj` 的变化：当一个 App 从前台切到后台，你会看到它的 oom_score_adj 从 0 逐步升到 900+。如果随后出现 `am_kill` 事件，说明该进程被 lmkd 回收了。

```
[图：Perfetto 中 oom_score_adj 变化时序图，展示 App 从前台→后台→被杀的完整过程]
[待高爷补充：Trace 截图]
```

---

## AMS 与 ANR 检测

ANR（Application Not Responding）是 Android 稳定性的核心防线。AMS 不直接导致 ANR——它是"裁判"，负责检测 App 是否在规定时间内完成了应完成的操作。

ANR 检测的核心模式可以用三个字概括：**埋雷、拆雷、爆雷**。

1. **埋雷**：AMS 在发起一个操作时（如启动 Service、分发广播），同时在主线程 Handler 上 post 一个延时消息。
2. **拆雷**：目标操作完成时，App 通过 Binder 通知 AMS，AMS 移除那个延时消息。
3. **爆雷**：如果延时消息到期时还没有被移除，说明 App 没有按时完成操作，触发 ANR 流程。

> [来源: 掘金《Android ANR的设计原理》]

这个"埋雷-拆雷-爆雷"模式贯穿了所有 ANR 类型。下面我们逐一拆解。

### Input ANR

**超时阈值：5 秒**

Input ANR 是用户感知最强烈的——App 在前台，点了没反应。检测入口不在 AMS 本身，而是在 Input 系统的 `InputDispatcher` 中。当 InputDispatcher 通过 socket 将输入事件发送给 App 的 `InputConsumer` 后，开始计时。如果 App 在 5 秒内没有消费（consume）这个事件，InputDispatcher 会通过 `InputManagerCallback` 通知 AMS 发起 ANR。

关键路径：
```
InputDispatcher.dispatchEvent()
  → 设置 connection 的 waitQueue（等待消费）
  → 定期检查：如果 waitQueue 中有事件超时 5s
    → InputDispatcher.notifyANR()
      → InputManagerCallback.notifyNotResponding()
        → AMS.inputDispatchingTimedOut()
          → AnrHelper.appNotResponding()
```

> [已验证: AOSP, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp — processAnrsLocked()]

在 Perfetto 中，Input ANR 表现为：主线程在某个 Message 上执行时间过长（或被阻塞），导致 Input 事件堆积在 `waitQueue` 中。

### Broadcast ANR

**超时阈值：前台广播 10 秒 / 后台广播 60 秒**

AMS 通过 `BroadcastQueue` 管理广播的分发。当一个广播被派发给一个 BroadcastReceiver 时，AMS 在主线程 Handler 上 post 一个延时消息。如果 Receiver 在超时时间内没有调用 `finishReceiver()`（对于 `goAsync()` 场景是 `PendingResult.finish()`），ANR 触发。

关键代码在 `BroadcastQueue.processNextBroadcastLocked()` 中：

```java
// frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java
// @ AOSP android-16.0.0_r1
// 前台广播超时
static final int BROADCAST_FG_TIMEOUT = 10 * 1000;  // 10 秒
// 后台广播超时
static final int BROADCAST_BG_TIMEOUT = 60 * 1000;  // 60 秒
```

> [待验证：Android 14+ 引入了基于 CPU 饥饿检测的动态超时调整，前台广播可能在 CPU 紧张时延长到 20 秒]

### Service ANR

**超时阈值：前台 Service 20 秒 / 后台 Service 200 秒 / startForeground() 调用 5 秒**

Service ANR 的"埋雷"发生在 `ActiveServices.realStartServiceLocked()` 中。当 AMS 通过 Binder 通知 App 端的 `ActivityThread` 创建 Service 时，同时在 `mAm.mHandler`（AMS 主线程 Handler）上 post 一个延时消息 `SERVICE_TIMEOUT_MSG`：

```java
// frameworks/base/services/core/java/com/android/server/am/ActiveServices.java
// @ AOSP android-16.0.0_r1
private final void realStartServiceLocked(ServiceRecord r, ProcessRecord app, 
        boolean execInFg) throws RemoteException {
    // 埋雷：开始 ANR 检测
    bumpServiceExecutingLocked(r, execInFg, "create");
    // 启动服务（拆雷的操作在这里面）
    app.thread.scheduleCreateService(r, ...);
}

void scheduleServiceTimeoutLocked(ProcessRecord proc) {
    // ...
    Message msg = mAm.mHandler.obtainMessage(
        ActivityManagerService.SERVICE_TIMEOUT_MSG);
    msg.obj = proc;
    // 前台 20s，后台 200s
    mAm.mHandler.sendMessageDelayed(msg, 
        proc.execServicesFg ? SERVICE_TIMEOUT : SERVICE_BACKGROUND_TIMEOUT);
}
```

"拆雷"发生在 App 端 Service 的 `onCreate()` 被调用之前：`ActivityThread.handleCreateService()` 中，在调用 `service.onCreate()` 之前，会通过 `ActivityManager.getService().serviceDoneExecuting()` 通知 AMS 移除超时消息。

> [已验证: AOSP android-16.0.0_r1, ActiveServices.java — scheduleServiceTimeoutLocked / serviceDoneExecutingLocked]

注意 `startForeground()` 的 5 秒超时是另一条独立的检测路径——如果 App 调用了 `Context.startForegroundService()` 但在 5 秒内没有调用 `startForeground()`，AMS 会直接抛出 ANR（早期版本是 crash，Android 12+ 改为 ANR）。

### ContentProvider ANR

**超时阈值：10 秒**

当 App 请求一个 ContentProvider 的数据时，如果目标进程尚未启动，AMS 需要先启动目标进程并等待 ContentProvider 发布（publish）。`ContentProvider` 的 ANR 检测在 `ActivityManagerService.getContentProviderImpl()` 中，超时为 10 秒。

### AMS 的 ANR 数据采集

当任何类型的 ANR 触发后，AMS 会通过 `AnrHelper.appNotResponding()` 进入统一的处理管线：

1. **pre-dump**：如果检测到 AMS 或 WMS 的锁被长时间持有（> 500ms），先 dump 锁持有者的堆栈。
2. **dump stack traces**：向目标进程发送 `SIGNAL_ANR`（或通过 `Debug.dumpJavaBacktraces()`），获取主线程和所有线程的调用栈。结果写入 `/data/anr/traces.txt`。
3. **CPU 使用率采集**：记录 ANR 发生前后各进程的 CPU 使用率，帮助判断是否因 CPU 争抢导致。
4. **弹出 ANR 对话框**：由 `AppNotRespondingDialog` 展示给用户（系统设置可关闭）。

`ProcessErrorStateRecord` 是管理单个进程错误状态（ANR/Crash）的核心类，在现代 Android 版本中接管了原来直接在 AMS 中处理的部分逻辑。

> [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AnrHelper.java]

在 Perfetto 中，ANR 事件通过 `am_anr` 标记可以精确定位。SQL 查询：

```sql
SELECT track.name, slice.name, slice.ts, slice.dur
FROM slice
JOIN track ON slice.track_id = track.id
WHERE slice.name LIKE 'am_anr%'
ORDER BY slice.ts DESC
LIMIT 10;
```

---

## AMS 的 Activity 管理

### Activity 栈与 Task 管理

如果你看的还是早期 Android 文章，很容易把这部分记成 `TaskStack` + `Task`。这个说法放在历史版本里不算错，但放到 Android 10 之后就会把旧模型和现行实现混在一起。当前 AOSP 里，Activity 与 Task 的容器管理已经从 AMS 主类拆到 `ActivityTaskManagerService`（ATMS）和 `WindowManager` 侧。`ActivityManagerService.startActivity()` 现在只是把请求转给 `mActivityTaskManager.startActivity()`，真正决定“这个 Activity 落到哪个任务、哪个显示区域、是否复用已有任务”的，是 `ActivityStarter`、`RootWindowContainer`、`TaskDisplayArea` 和 `Task` 这一套容器。

从容器层级看，现代实现更接近下面这个结构：

```text
RootWindowContainer
  └─ DisplayContent
      └─ TaskDisplayArea
          └─ Task（root task / leaf task）
              └─ ActivityRecord
```

`RootWindowContainer` 是整台设备的顶层窗口容器；每个 `DisplayContent` 下面可以有一个或多个 `TaskDisplayArea`；`TaskDisplayArea` 的孩子既可以是 `Task`，也可以是嵌套的 `TaskDisplayArea`；`Task` 本身既可能是用户在 Recents 里看到的一张任务卡片，也可能继续包含子 `Task`。所以我们今天谈“Activity 落在哪个栈里”时，更准确的说法不是“AMS 把它塞进某个 TaskStack”，而是“ATMS / WindowManager 在目标 `TaskDisplayArea` 中选择或创建合适的 `Task`，再把 `ActivityRecord` 挂进去”。

落实到启动链路，`ActivityStarter.startActivityInner()` 会先计算 `mPreferredTaskDisplayArea`，再通过 `TaskDisplayArea.getOrCreateRootTask()` 找到或创建目标 root task，最后把新的 `ActivityRecord` 放进目标 `Task`。这对性能分析有一个直接影响：我们在 Perfetto 里看到 `am_activity_launch`，只能说明 `system_server` 侧已经发起了启动流程；真正影响启动手感的“复用旧任务还是新建任务、是否切到别的 display area、是否走多窗口 / PiP 路径”，要结合 `ActivityStarter` 的决策和后续 `ActivityThread.handleLaunchActivity()` 一起看。AMS 负责把进程和全局状态管起来，ATMS 负责把 Activity 放到正确的容器里，这两条线要放在一起看，启动链路才完整。

> [已验证: AOSP android-16.0.0_r1，`frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` 中 `startActivity()` 委托给 `mActivityTaskManager.startActivity()`；`frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java`、`TaskDisplayArea.java`、`Task.java` 定义了当前任务容器层级]

### Activity 启动耗时在 Perfetto 中的定位

分析 Activity 启动耗时，我们通常关注以下几个时间节点：

1. `am_proc_start`（如果是冷启动）：进程创建开始
2. `am_proc_bound`：进程就绪
3. Binder: `attachApplication`：Application 绑定
4. `Application.onCreate()`：App 初始化
5. `Activity.onCreate()` → `onResume()`：Activity 生命周期
6. 第一帧 `doFrame`：首帧渲染完成

冷启动的场景下，`am_proc_start` 到首帧 `doFrame` 之间的时间就是用户感知的"冷启动耗时"。

```
[图：Perfetto 中冷启动的完整 Trace 片段，标注上述 6 个关键时间节点]
[待高爷补充：Trace 截图]
```

### manifest 中的 `recreateOnConfigChanges`

这一项不能写成“Android 17 新引入”。当前公开 AOSP 在 `frameworks/base/core/res/res/values/attrs_manifest.xml` 里已经定义了 `recreateOnConfigChanges`，而且注释写得很直白：从 Android O 开始，`mcc` 和 `mnc` 这两类配置变化默认不会再触发 Activity 重建；如果应用确实希望在这两种变化发生时重走一次 Activity 重建流程，需要在 manifest 里显式声明 `recreateOnConfigChanges`。

这意味着我们分析配置变更带来的重启问题时，不能把 `recreateOnConfigChanges` 当成一个“通用的 Activity 重启开关”。就公开源码可验证的语义来看，它主要针对 `mcc` / `mnc` 这类运营商和区域配置变化。屏幕旋转、夜间模式、窗口尺寸变化这类更常见的场景，仍然应该先看 `android:configChanges`、`onConfigurationChanged()` 和实际生命周期回调，而不是先假设系统会因为 `recreateOnConfigChanges` 把 Activity 杀掉重建。

从性能角度，这个属性影响的不是高频日常交互，而是少见但难查的区域 / 运营商切换场景。假如你在跨境 SIM、eSIM 切换或运营商配置更新后看到 Activity 没有按预期重建，先查 manifest 是否声明了 `mcc|mnc` 的 `recreateOnConfigChanges`，再决定是否继续沿着 AMS / ATMS 的重启链路追。至少就当前公开的 AOSP 与 Android Developers 文档，我们没有证据把它解释成 Android 17 的通用行为变更。

> [已验证: AOSP android-16.0.0_r1，`frameworks/base/core/res/res/values/attrs_manifest.xml`；Android Developers `android.R.attr#recreateOnConfigChanges`]

---

## AMS 的 Service 管理

### 前台服务（Foreground Service）的演进

前台服务是 Android 中一种重要的后台执行机制，允许 App 在用户不可见时继续执行关键任务（如音乐播放、导航、文件下载），代价是必须显示一个持续通知。

**Android 12（API 31）** 引入了一个重大变更：**禁止从后台启动前台服务**。如果 App 在后台时调用 `startForegroundService()`，系统会抛出 `ForegroundServiceStartNotAllowedException`。例外情况包括：从用户可见状态转换时、收到高优先级 FCM 消息时、以及特定的系统组件调用时。

同时，Android 12 引入了 **Phantom Process Killer**，监控 App 的子进程（通过 `Runtime.exec()` 或 JNI fork），限制系统级总数为 32 个，超出的会被杀掉。

**Android 14（API 34）** 进一步要求：
- 每个 FGS 必须在 Manifest 中声明 `foregroundServiceType`（如 `camera`、`connectedDevice`、`dataSync`、`health`）。
- 必须申请对应类型的权限（如 `FOREGROUND_SERVICE_CAMERA`），否则 `SecurityException`。
- 即使满足后台启动 FGS 的豁免条件，如果 FGS 需要"while-in-use"权限（如位置、相机、麦克风），在 App 处于后台时也不能访问这些资源。

**Android 15（API 35）** 对 `dataSync` 和新增的 `mediaProcessing` 类型的 FGS 加了运行时间上限（`dataSync` 最长 6 小时）。

**Android 16（API 36）** 要求后台 Job（包括通过 FGS 启动的）遵守各自的运行配额。

**Android 17（API 37）** 进一步收紧了后台音频行为——没有"while-in-use"能力的 FGS 在后台调用音频 API 会静默失败。

> [已验证: 官方文档, developer.android.com — Behavior changes for Android 12/14/15/16/17]

### 后台启动服务的限制链

从 Android 8.0 开始，Google 就在逐步收紧后台启动 Service 的能力。整个演进路线：

- **Android 8.0**：限制后台 App 调用 `startService()`，必须使用 `startForegroundService()`。
- **Android 12**：限制后台启动 FGS（`ForegroundServiceStartNotAllowedException`）。
- **Android 14**：FGS 类型声明强制化 + while-in-use 权限限制。
- **Android 15**：`dataSync` FGS 运行时间上限。
- **Android 16**：后台 Job 配额执行。
- **Android 17**：后台音频 API 强制限制。

Google 的推荐替代方案是使用 `WorkManager` 来调度可延迟的后台任务，只在真正需要用户可感知的长时间运行时才使用 FGS。

---

## AMS 的广播管理

### 广播分发机制

AMS 通过 `BroadcastQueue` 管理所有广播的分发。系统维护两个队列：

- **前台广播队列**（`mFgBroadcastQueue`）：处理带 `FLAG_RECEIVER_FOREGROUND` 标志的广播，超时 10 秒。
- **后台广播队列**（`mBgBroadcastQueue`）：处理普通广播，超时 60 秒。

分发流程：

1. 发送方通过 `Context.sendBroadcast()` → Binder 调用到 AMS。
2. AMS 根据 Intent 匹配已注册的 Receiver（包括静态和动态），生成目标列表。
3. 对于有序广播，按 priority 排序后依次分发；对于无序广播，并行分发。
4. 每个 Receiver 执行 `onReceive()` 时，AMS 开始计时。如果超时未完成，触发 ANR。

### 静态广播 vs 动态广播的性能差异

静态广播（在 Manifest 中声明）和动态广播（代码中 `registerReceiver()`）的主要区别在于：

- **静态广播**：即使 App 进程不在，系统也会通过 AMS 启动 App 进程来接收广播。这意味着一次静态广播的触发可能导致进程冷启动，性能开销大。
- **动态广播**：只在进程存活时有效，不需要冷启动，性能开销小。

从系统性能的角度，大量注册静态广播的 App 会在系统事件（如 `BOOT_COMPLETED`、`CONNECTIVITY_CHANGE`）触发时引发"进程创建风暴"——AMS 需要同时启动大量进程。这也是 Android 逐步限制静态广播的原因之一。

### Android 14+ 的广播限制

Android 14 对广播做的变化，重点不在 Extra 大小，而在**投递时机**和**动态注册边界**。

第一层变化发生在进程处于 cached state 时。官方行为变更文档明确写到，`context-registered broadcasts` 可以在应用进入 cached state 后被放进队列，等应用回到前台或离开 cached state 再投递。Manifest 中声明的广播不走这套排队逻辑，系统甚至会把应用从 cached state 拉出来立即投递。这会直接改变我们在 Perfetto 里理解“广播什么时候真正执行”的方式：发送时刻和 `onReceive()` 真正跑起来的时刻，Android 14 之后不一定重合。

第二层变化是动态注册 Receiver 的导出属性。面向 Android 14+ 的应用在调用 `Context.registerReceiver()` 时，需要显式指定 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`，除非它只接收 system broadcast。这个改动是安全收口，不是性能优化本身，但它会影响旧代码能不能顺利走到广播分发路径。

对性能分析来说，我们至少要记住两件事。第一，cached 进程里的动态广播可能被延后，因此不能再用“发送广播后主线程没立刻响应”直接推断 AMS 分发慢。第二，Manifest 广播依旧可能把进程拉起，所以 `BOOT_COMPLETED`、网络变化、电量状态切换这类广播仍然可能造成进程批量唤醒，低端设备上尤其容易放大冷启动风暴和后台抖动。

> [已验证: Android Developers `Behavior changes: all apps`（Android 14，cached state 下的 context-registered broadcast 排队）与 `Behavior changes: Android 14`（runtime-registered receiver 必须显式声明 `RECEIVER_EXPORTED` / `RECEIVER_NOT_EXPORTED`）]

---

## AMS 在 Perfetto 中的具体表现

前文我们已经分散地提到了各种 Trace 事件，这里做一个集中梳理。

### system_server 中的关键线程

在 Perfetto 中打开 `system_server` 进程，你会看到很多线程。和 AMS 最相关的几个：

| 线程名 | 作用 |
|--------|------|
| `ActivityManager` | AMS 主逻辑线程，处理组件调度、进程管理 |
| `Binder:system_server_X` | Binder 线程池（通常 16 个），接收来自 App 的跨进程调用 |
| `android.fg` | 前台 Handler 线程，处理一些后台任务（如 ANR dump） |
| `android.display` | Display 相关后台任务 |
| `TaskPersister` | 持久化 Task 状态到磁盘 |

### 典型场景的 Trace 特征

**冷启动场景：**
1. `ActivityManager` 线程出现 `am_proc_start`
2. `zygote64` 出现 fork（一个极短的 CPU burst）
3. 新进程出现，`main` 线程开始执行
4. `Binder:system_server_X` 上出现 `attachApplication` 调用
5. 新进程 `main` 线程执行 `Application.onCreate()`
6. `am_activity_launch` 出现在 `ActivityManager` 线程
7. 新进程渲染第一帧

**ANR 场景：**
1. 主线程上某个 Message 执行时间过长（或被阻塞）
2. `ActivityManager` 线程出现 `am_anr` 切片
3. `system_server` 的 Binder 线程上出现 `dumpStackTraces` 调用
4. 目标进程收到 signal，各线程堆栈被 dump
5. 如果启用了 ANR 对话框，`system_server` 中出现 `AppNotRespondingDialog` 相关活动

**进程被杀场景：**
1. `Process Stats` Track 中看到目标进程的 `oom_score_adj` 逐步升高
2. 系统内存水位上升
3. `ActivityManager` 线程出现 `am_kill`
4. 目标进程的所有线程消失

```
[图：三种典型场景的 Perfetto Trace 对比截图]
[待高爷补充：Trace 截图]
```

---

## 与其他机制的关系

- **§1.3 进程模型**：AMS 是进程创建和管理的执行者。理解进程模型是理解 AMS 行为的前提。
- **§1.4 Binder IPC**：AMS 几乎所有对外交互都走 Binder。`Binder:system_server` 线程池的饱和直接影响 AMS 的响应能力。
- **§2.4 Choreographer**：Activity 启动完成后，首帧渲染由 Choreographer 驱动。AMS 负责的是"Activity 启动"这个阶段。
- **§4.4 LMK**：AMS 维护 oom_adj，lmkd 执行杀进程。两者配合完成内存回收。
- **§8.2 App 启动分析**：冷启动的完整分析需要将 AMS 行为（进程创建）和 App 行为（Application/Activity 初始化）结合来看。

---

## 版本演进

| Android 版本 | 关键变更 | 影响 |
|-------------|---------|------|
| Android 8.0 (API 26) | 后台启动 Service 限制 | 后台 App 必须使用 `startForegroundService()` |
| Android 9.0 (API 28) | App Standby Buckets | AMS 根据使用频率限制后台执行 |
| Android 10 (API 29) | 后台 Activity 启动限制 | 后台 App 不能随意弹出 Activity |
| Android 12 (API 31) | 后台 FGS 启动限制 + Phantom Process Killer | `ForegroundServiceStartNotAllowedException` |
| Android 14 (API 34) | FGS 类型声明强制化 + while-in-use 限制 | 必须声明 `foregroundServiceType` |
| Android 15 (API 35) | dataSync FGS 运行时间上限（6h） | 长时间后台数据同步需换方案 |
| Android 16 (API 36) | 后台 Job 配额 + ProfilingManager | 后台任务受配额限制 |
| Android 17 (API 37) | 后台音频 API 限制 | 后台调用音频播放 / 焦点 / 音量 API 可能失败或静默无效 |

> [已验证: 官方文档, developer.android.com — 各版本 Behavior changes]

---

## 常见问题与误区

**误区 1："ANR 超时是 5 秒"**
不准确。5 秒只是 Input ANR 的超时。Service ANR 前台是 20 秒、后台是 200 秒；广播前台是 10 秒、后台是 60 秒。不同类型的 ANR 有不同的超时阈值。

**误区 2："进程被杀一定是因为内存不足"**
不一定。除了 lmkd 的内存回收，进程还可能因为 ANR（用户选择"关闭"）、Crash、或者 AMS 主动杀（如 App 后台行为违规）而被终止。需要看 `am_kill` 事件的具体原因字段。

**误区 3："前台 Service 不会被杀"**
前台 Service 的 oom_adj 确实比较低（100），不容易被 lmkd 杀。但如果系统极端缺内存，或者 Service 本身出现 ANR/Crash，仍然会被杀。而且 Android 12+ 对后台启动 FGS 有严格限制，不是想用就能用的。

**误区 4："`am_proc_start` 时间就是冷启动耗时"**
`am_proc_start` 只标记了 AMS 向 Zygote 发起 fork 请求的时刻。真正的冷启动耗时应该从用户点击（或 `am_activity_launch`）开始，到首帧 `doFrame` 结束。中间还包括 Zygote fork、Application 初始化、Activity 生命周期执行、首帧渲染等多个阶段。

**误区 5："后台 App 的广播不影响前台性能"**
影响。如果大量后台 App 注册了静态广播，系统事件触发时 AMS 会尝试启动多个进程，这会抢占 CPU 和 I/O 资源，间接影响前台 App 的性能。在低端设备上尤其明显。

---

## 参考资料

### AOSP 源码路径
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — AMS 主类
- `frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java` — Activity / Task 管理入口
- `frameworks/base/services/core/java/com/android/server/wm/RootWindowContainer.java` — 顶层任务 / 显示容器
- `frameworks/base/services/core/java/com/android/server/wm/TaskDisplayArea.java` — Display 下的任务容器
- `frameworks/base/services/core/java/com/android/server/wm/Task.java` — Task 定义与 Recents 语义
- `frameworks/base/core/res/res/values/attrs_manifest.xml` — `recreateOnConfigChanges` 定义
- `frameworks/base/services/core/java/com/android/server/am/ActiveServices.java` — Service 管理与 ANR 检测
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java` — 广播分发与超时
- `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java` — ANR 统一处理管线
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` — 进程列表与 lmkd 交互
- `frameworks/base/core/java/android/app/ActivityThread.java` — App 端主线程入口
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — Input 事件分发与 ANR 检测
- `frameworks/base/core/java/android/app/IActivityManager.aidl` — AMS 的 Binder 接口定义

### 官方文档
- [Behavior changes: Android 12](https://developer.android.com/about/versions/12/behavior-changes-12) — FGS 后台启动限制
- [Behavior changes: Android 14](https://developer.android.com/about/versions/14/behavior-changes-14) — 动态注册 Receiver 导出属性与 FGS 相关约束
- [Behavior changes: all apps on Android 14](https://developer.android.com/about/versions/14/behavior-changes-all) — cached state 下的 context-registered broadcast 排队
- [Behavior changes: all apps on Android 17](https://developer.android.com/about/versions/17/behavior-changes-all) — 后台音频 API 限制
- [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services) — FGS 官方指南
- [Background execution limits](https://developer.android.com/about/versions/oreo/background) — Android 8.0 后台限制
- [android.R.attr#recreateOnConfigChanges](https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges) — `recreateOnConfigChanges` 属性说明

### 深入阅读
- 《Android ANR 的设计原理》— 掘金，ANR 埋雷-拆雷-爆雷机制的源码级分析
- 《Android 卡顿与 ANR 的分析实践》— 掘金/Shopee 技术团队，Looper+MessageQueue 模型与 ANR 关系
- 《从 ApplicationExitInfo 看 Android 应用的退出类型》— 进程退出原因分类

---

> [自动发现] AMS 内部的锁竞争（`mService` 全局锁）和 `system_server` Binder 线程池饱和问题，是分析 system_server 侧性能瓶颈时的重要切入点。这部分内容计划在扩展章节中详细展开。


<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **AMS / ATMS 分工与 Perfetto 入口**：[已验证: AOSP android-16.0.0_r1]
  AMS 负责进程管理、ANR、Service / Broadcast / Provider 调度；Activity / Task 容器管理在 ATMS / WindowManager。Perfetto 入口看 `system_server` 的 `ActivityManager` 线程和 `am_*` 事件。

- 🔹 **进程优先级、启动与回收链路**：[已验证: AOSP android-16.0.0_r1]
  关注 `oom_adj`、`am_proc_start`、`am_proc_bound`、lmkd 协作与冷启动关键时间点。

- 🔹 **ANR 类型与超时差异**：[已验证: AOSP + 官方文档]
  Input / Broadcast / Service / ContentProvider 有不同超时和埋雷位置，不能用“ANR = 5 秒”一把梭。

- 🔹 **现代 Activity 任务容器模型**：[已验证: AOSP android-16.0.0_r1]
  现代层级是 `RootWindowContainer → DisplayContent → TaskDisplayArea → Task → ActivityRecord`，不能再把 `TaskStack` 当成当前主术语。

- 🔹 **Android 14+ 广播与配置变更差异**：[已验证: developer.android.com + AOSP]
  Android 14 对 cached state 下的 context-registered broadcast 引入排队，并要求动态注册 Receiver 显式声明导出属性；`recreateOnConfigChanges` 的公开可验证语义是 Android O+ 下 `mcc/mnc` 场景的显式重建。

### 扩展（可选深入）

- 🔸 **system_server 侧瓶颈排查**：Binder 线程池饱和、AMS 全局锁竞争、Task 切换与窗口动画联动
- 🔸 **Trace 实战脚本化**：用 SQL 把 `am_*` 事件与主线程首帧、Binder 调用链、Process Stats 串起来
<!-- outline-end -->
