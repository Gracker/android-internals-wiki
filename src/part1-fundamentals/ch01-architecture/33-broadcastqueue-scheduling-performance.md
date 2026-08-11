---
title: "Android 17 BroadcastQueue 进程级调度与广播性能边界"
chapter: "1.33"
status: ready-for-review
drafted_date: "2026-06-27"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
consolidated_from:
  - "src/part2-performance/ch08-responsiveness/21-broadcast-performance-cross-process-overhead.md"
sources:
  - type: official
    path: "developer.android.com/develop/background-work/background-tasks/broadcasts"
  - type: official
    path: "developer.android.com/about/versions/14/behavior-changes-all"
  - type: official
    path: "developer.android.com/reference/android/app/BroadcastOptions"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerShellCommand.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ContextImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/BroadcastOptions.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/Intent.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerfettoCategories.java"
tags: [broadcast, broadcastqueue, scheduler, AMS, ANR, broadcast-process-queue]
related_chapters: ["1.8", "9.2", "5.8", "1.34", "5.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/章节深挖"
---

# 1.33 Android 17 BroadcastQueue 进程级调度与广播性能边界

Android 广播是一种受系统策略调度的事件分发机制。调用 `sendBroadcast()` 只表示系统接受了发送请求，不表示接收方会立刻执行。目标进程是否存活、是否处于 cached 状态、接收者类型、广播是否有序以及调度槽是否空闲，都会改变投递时间。

Android 17 的实现与早期 Android 常见的“前台一条队列、后台一条队列”示意图已有明显差异。广播性能由 `BroadcastRecord`、`BroadcastProcessQueue` 和进程调度槽三个层次共同决定。

## 一、Android 17 只有一个 BroadcastQueue 实例

### 1.1 前台和后台是两套超时参数，不是两条队列

API 37 的 `ActivityManagerService` 只持有一个 `mBroadcastQueue`。`ActivityManagerService.Injector.getBroadcastQueue()` 创建两个 `BroadcastConstants`：

- `foreConstants.TIMEOUT = BROADCAST_FG_TIMEOUT`；
- `backConstants.TIMEOUT = BROADCAST_BG_TIMEOUT`；
- 两者共同传给一个 `BroadcastQueueImpl`。

因此，Android 17 不能再画成 `mFgBroadcastQueue` 和 `mBgBroadcastQueue` 两个独立对象。`Intent.FLAG_RECEIVER_FOREGROUND` 仍然有效，但它影响的是紧急程度、接收进程调度组和超时参数，不是把记录放入另一套全局队列。

源码中的基准超时为：

| 类型 | API 37 基准值 | 选择条件 |
|---|---:|---|
| foreground broadcast | `10 s × Build.HW_TIMEOUT_MULTIPLIER` | 带 `FLAG_RECEIVER_FOREGROUND` |
| background broadcast | `60 s × Build.HW_TIMEOUT_MULTIPLIER` | 未带上述标志 |

这两个值还能通过 `Settings.Global.BROADCAST_FG_CONSTANTS` 和 `BROADCAST_BG_CONSTANTS` 中的 `bcast_timeout` 覆盖。因此，10 秒/60 秒是源码基准值，不是所有构建和设备都无法更改的常量。

### 1.2 API 37 的实现类名就是 `BroadcastQueueImpl`

Android 17 标签中不存在 `BroadcastQueueModernImpl.java`。当前的 `BroadcastQueueImpl` 类注释直接说明：广播按目标进程分发，每个进程由一个 `BroadcastProcessQueue` 表示。

内部类名在开发分支和历史版本中发生过变化，应用可依赖的是公开广播语义，不能根据某个旧类名判断设备一定运行 Legacy 或 Modern 模式。以下实现细节均以 `android-17.0.0_r1` 为准。

## 二、三层数据结构分别解决什么问题

### 2.1 `BroadcastRecord`：一次发送及其全部接收者

`BroadcastController.broadcastIntentLockedTraced()` 查询 manifest receiver 和运行时注册接收者，把结果合成一份接收者列表，再构造 `BroadcastRecord`。

一个 `BroadcastRecord` 保存发送者、Intent、广播选项、接收者列表，以及每个接收者自己的状态数组。API 37 的投递状态为：

| 状态 | 含义 | 是否终态 |
|---|---|---|
| `DELIVERY_PENDING` | 尚未调度 | 否 |
| `DELIVERY_SCHEDULED` | 已提交给目标进程，等待完成 | 否 |
| `DELIVERY_DEFERRED` | 因 cached/deferral 策略而推迟 | 否 |
| `DELIVERY_DELIVERED` | 已完成或系统按规则视为完成 | 是 |
| `DELIVERY_SKIPPED` | 被权限、进程状态或其他策略跳过 | 是 |
| `DELIVERY_TIMEOUT` | 接收者执行超时 | 是 |
| `DELIVERY_FAILURE` | 调度到进程失败 | 是 |

`APP_RECEIVE`、`CALL_IN_RECEIVE`、`CALL_DONE_RECEIVE` 属于 `BroadcastRecord.state` 的整条记录执行状态，不能拿来替代上述逐接收者 `delivery[]` 状态。

### 2.2 `BroadcastProcessQueue`：同一目标进程的待投递项

`BroadcastQueueImpl.enqueueBroadcastLocked()` 不会把整个 `BroadcastRecord` 只放进一条全局 FIFO。它遍历接收者，以 `processName + uid` 找到目标 `BroadcastProcessQueue`，将“记录 + 接收者下标”入队。

每个进程队列内部有三条待处理队列：

| 队列 | 进入条件 | 调度关系 |
|---|---|---|
| `mPendingUrgent` | `BroadcastRecord.isUrgent()` | 优先于 normal/offload，但有防饥饿限制 |
| `mPending` | 普通广播 | 位于 urgent 之后、offload 之前 |
| `mPendingOffload` | 隐藏标志 `FLAG_RECEIVER_OFFLOAD` | 系统内部使用，优先级最低 |

`FLAG_RECEIVER_OFFLOAD` 不是“允许系统延迟合并”的公开性能开关。`Intent.java` 将它标记为 `@hide`，其语义是进入 offload 调度类。

### 2.3 `runnable` 与 `running`：控制跨进程并行度

有待处理项的进程队列会计算 `runnableAt`，再按时间排序进入 `runnable` 链表。`updateRunningListLocked()` 从链表中选取队列，放进固定大小的 `running` 数组并开始投递。

Android 17 的默认值为：

- 普通设备最多同时运行 4 个普通进程队列；
- low-RAM 设备最多同时运行 2 个；
- urgent 广播可额外使用 1 个槽；
- 同一时刻只允许发起 1 个广播冷启动。

这些值来自 `BroadcastConstants`，并可由 `activity_manager_native_boot` DeviceConfig 调整。额外 urgent 槽用于在普通槽已占满时保证紧急广播继续推进，不会把所有广播的并行度永久提高到 5。

## 三、从发送到 `onReceive()` 的调用路径

下面的调用链用于区分“解析接收者”“排队”“拉起进程”和“执行回调”四段时间：

```text
ContextImpl.sendBroadcast()
  → IActivityManager.broadcastIntentWithFeature()
  → BroadcastController.broadcastIntentLockedTraced()
      ├─ PackageManagerInternal.queryIntentReceivers()  // manifest receiver
      ├─ ReceiverResolver.queryIntent()                 // context-registered receiver
      └─ new BroadcastRecord(...)
  → BroadcastQueueImpl.enqueueBroadcastLocked()
      └─ 每个 receiver 入对应 BroadcastProcessQueue
  → updateRunnableList() → updateRunningListLocked()
      ├─ cold: scheduleReceiverColdLocked()
      │       → startProcessLocked()
      │       → onApplicationAttachedLocked()
      └─ warm: scheduleReceiverWarmLocked()
              ├─ IApplicationThread.scheduleRegisteredReceiver()
              └─ IApplicationThread.scheduleReceiver()
  → 应用进程 ActivityThread / ReceiverDispatcher
  → BroadcastReceiver.onReceive()
  → finishReceiver()（系统需要等待完成的投递）
```

这条链说明，广播总延迟至少包含接收者解析、进程队列等待、必要时的进程冷启动、Binder 调度、应用主线程排队和 `onReceive()` 执行。只测 `onReceive()` 方法体，无法代表发送到接收的端到端延迟。

### 3.1 冷启动不会把多条广播合并为一次 ApplicationThread IPC

目标进程不存在时，`scheduleReceiverColdLocked()` 请求拉起进程；进程 attach 后再转入 `scheduleReceiverWarmLocked()`。同一进程的多条广播共用一个进程队列，可以在一个 `running` 时段连续排空若干项，减少调度槽反复切换。

但源码仍对每个 receiver 分别调用 `scheduleRegisteredReceiver()` 或 `scheduleReceiver()`，不会把多条广播序列化进一次 Binder 调用。“同进程多个广播自动合并为一次 IPC”没有源码依据。

冷启动耗时也没有 300～800 ms 的平台保证。Zygote 分支、存储冷热、`bindApplication`、应用初始化和设备负载都会改变结果，应使用进程启动 trace 与广播 trace 在目标设备上测量。

### 3.2 运行时 receiver 与 manifest receiver 的完成语义不同

对于无序且没有 completion callback 的 context-registered receiver，`BroadcastRecord.isAssumedDelivered()` 返回 `true`。`system_server` 成功发出 `scheduleRegisteredReceiver()` 后立即把该项标记为 delivered，不等待应用回报，也不会为它启动广播 ANR 定时器。

以下投递会等待 `finishReceiver()`，并受广播超时跟踪：

- manifest receiver；
- 有序广播接收者；
- 带 completion callback、不能按 assumed-delivered 处理的投递。

这不表示无序动态 receiver 可以长期占用主线程。它仍会阻塞该应用自己的 UI 和后续消息，可能触发输入、前台服务等其他类型 ANR；BroadcastQueue 只是不等待这次无序动态投递的完成回执。

## 四、优先级、顺序与防饥饿

### 4.1 `urgent` 不是 `Intent` 的“priority string”

Android 没有 `PRIORITY_URGENT_APP`、`PRIORITY_NORMAL_APP` 这组广播字符串。API 37 的 `BroadcastRecord.calculateUrgent()` 在以下条件返回 true：

- Intent 带 `FLAG_RECEIVER_FOREGROUND`；
- `BroadcastOptions` 将其标记为 interactive；
- `BroadcastOptions` 将其标记为 alarm broadcast。

后两项主要供系统组件使用。普通应用不应为了抢占调度而滥用 foreground receiver flag；它会让接收者以更高调度优先级运行，并把广播超时基准缩短到 10 秒。

### 4.2 receiver priority 是整数，但 Android 16 起不再提供跨进程全序

`IntentFilter` 的 priority 仍是整数。Android 16 起，公开行为增加了两项限制：优先级只保证在同一应用进程内生效，不保证不同进程之间的接收顺序；应用可设置的值也会被限制在系统保留上下界之间。

因此，即使两个应用为同一个广播设置不同 priority，也不能把它设计成跨应用协议顺序。需要请求/响应、确认或全序处理时，应使用 Binder 服务、明确的任务队列或持久化协调机制。

### 4.3 ordered 仍会建立接收者依赖

有序广播的第 N 个接收者，要等第 N-1 个接收者到达终态或 deferred 状态后才能继续。无序广播的接收者没有这条依赖，可以分散到多个进程队列并行推进。

“无序广播并行”也不等于所有 receiver 同时执行。并行度仍受 `running` 槽、单冷启动槽、目标进程主线程和 cached 策略限制。

进程队列内部按 `urgent` → `normal` → `offload` 选择下一项，同时用两个上限避免低优先级长期饥饿：默认连续 3 个 `urgent` 后会考虑更早入队的低优先级项，连续 10 个 `normal` 后也会考虑 `offload` 项；若低优先级项仍被 ordered 依赖阻塞，则不能越过依赖强行执行。

## 五、cached app 的延迟没有统一规则

### 5.1 Android 14 起的公开行为

从 Android 14 开始，应用处于 cached 状态时，系统可以延后 context-registered receiver 的广播。应用回到 active 状态后，系统再投递积压项；某些广播的多个实例可能被合并。

Manifest receiver 不走同样的无限延迟路径。重要的 manifest broadcast 可以让应用离开 cached 状态并启动接收进程。“cached app 的所有广播都要等待其他原因拉起进程”并不是统一规则。

### 5.2 API 37 如何计算 `runnableAt`

`BroadcastProcessQueue.updateRunnableAt()` 按队列内容和进程状态选原因。默认调度偏移包括：

| 条件 | 默认偏移 | 含义 |
|---|---:|---|
| urgent / foreground / instrumented | `-120 s` | 排序时强烈前移，不代表提前执行 |
| ordered / alarm / prioritized / manifest | `0` | 不加普通防抖延迟 |
| 普通广播 | `+500 ms` | 给快速变化事件留出调度余量 |
| cached 且不能无限 defer | `+120 s` | 延后处理 |
| cached 且全部记录 `deferUntilActive` | `Long.MAX_VALUE` | 等进程变为 active 或条件变化 |

这些是 DeviceConfig 默认值，不是 API 时延承诺。队列积压达到 `MAX_PENDING_BROADCASTS`（普通设备默认 256、low-RAM 默认 128）时，代码会绕过已施加的延迟以帮助排空。

### 5.3 deferral 和 delivery group 是两个维度

API 34 加入的 `BroadcastOptions` 提供两组不同能力：

- `setDeferralPolicy(DEFERRAL_POLICY_UNTIL_ACTIVE)`：允许把符合条件的运行时 receiver 延后到进程 active；它不适用于 ordered、alarm、interactive 和 manifest broadcast；
- `setDeliveryGroupPolicy(DELIVERY_GROUP_POLICY_MOST_RECENT)`：同一 delivery group 只保留最近一条，旧的待投递项被跳过。

Deferral 解决何时投递，delivery group 解决积压项是否都要投递。没有显式 delivery group 策略时，系统不会因为接收者在同一进程就自动合并任意广播。

`FLAG_RECEIVER_REPLACE_PENDING` 也只替换满足发送 UID、user、Intent 匹配、receiver 和其他条件的 pending 项。它不会对整个 action 或整个进程执行无条件去重。

### 5.4 freezer 与广播队列互相通知，但冻结时不会一律挂起

广播队列会观察进程是否可冻结，并在状态变化时重新计算 runnable/deferred 状态。若接收进程已进入 `running` 投递，系统还会更新 OOM adj 和冻结状态，保证回调能够执行。

API 37 另有受 feature flag 控制的 outgoing broadcast 延迟：freezable 发送进程产生的广播可以暂存在它自己的进程队列，进程恢复后再进入正式队列。发送方延迟与接收方处于 cached 状态时的延迟投递不是同一条路径。

## 六、广播 ANR 的计时边界

### 6.1 定时器从提交给接收进程前开始

`dispatchReceivers()` 在调用 `scheduleRegisteredReceiver()` 或 `scheduleReceiver()` 之前启动 `AnrTimer`，完成后由 `finishReceiverLocked()` 取消。超时会把该接收者标为 `DELIVERY_TIMEOUT`，随后调用 `appNotResponding()`。

队列等待和广播触发的冷启动发生在启动此定时器之前。因此，一条广播端到端等待很久，不等于 receiver 已经执行超时；排障必须区分调度延迟与完成延迟。

### 6.2 `goAsync()` 延长的是回调完成方式，不是无限时间

需要异步完成的 receiver 可以调用 `goAsync()` 取得 `PendingResult`，在短任务结束后调用 `finish()`。对于需要 `system_server` 等待完成的投递，ANR 定时器不会因为 `goAsync()` 自动取消。

长时间网络、磁盘扫描、数据库迁移等工作不应留在广播完成窗口内。receiver 更适合做参数校验、去重和任务入队，再交给 `JobScheduler`、WorkManager 或具备明确生命周期的服务。

### 6.3 从 ANR 文件看哪一段卡住

广播 ANR 的 `TimeoutRecord` 描述包含 Intent、接收包名和类名。分析时至少核对：

1. 当前 receiver 是 manifest、ordered 还是带 completion callback 的动态 receiver；
2. 主线程在执行 Java/Kotlin 代码、等待锁、Binder 调用还是文件 I/O；
3. 是否调用 `goAsync()` 后遗漏 `finish()`；
4. 广播是否带 `FLAG_RECEIVER_FOREGROUND`，从而使用 10 秒基准；
5. trace 中的长时间出现在调度前排队，还是 schedule 后执行。

## 七、应用侧常见误区

### 7.1 不要默认认为清单接收者更省性能

Manifest receiver 的 IntentFilter 在安装阶段解析，但投递时仍要查询并执行权限/可见性检查，而且它能拉起尚未运行的进程。Android 8 起，多数隐式广播不能由面向 API 26+ 的应用随意静态注册。

动态 receiver 适合只在页面、服务或进程存活期间关注的事件；manifest receiver 适合需要在进程不存在时接收、且平台允许静态注册的事件。应根据生命周期与后台启动语义选择，不能用“静态注册一定更快”代替测量。

### 7.2 `RECEIVER_NOT_EXPORTED` 是安全边界，不是本地广播优化开关

面向 Android 14 的应用注册非纯系统广播 receiver 时，需要显式选择 `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`。`RECEIVER_NOT_EXPORTED` 限制可向该 receiver 发送广播的外部身份，但它仍在 `system_server` 中注册并通过广播分发路径执行。

它不会把广播自动变成进程内函数调用，也不能据此声称省去了 PackageManager 查询或 Binder IPC。若事件只在一个进程内使用，直接回调、`Flow` 或应用自己的事件模型更简单。

### 7.3 低延迟 IPC 不要依赖广播

官方文档明确不保证广播投递时延。需要同步响应、背压、调用结果或稳定低延迟的跨进程接口，应使用 bound service/AIDL。广播适合一次发送、多个可能接收者的事件通知。

发送方还应尽量缩小接收范围：

- 私有 `action` 使用应用包名前缀；
- 已知目标时使用 explicit component 或 `Intent.setPackage()`；
- 对跨应用广播设置发送/接收权限；
- 高频状态变化只发送必要字段，或通知接收方读取权威状态源；
- 需要去重时明确使用 delivery group，不能期待系统猜测业务语义。

### 7.4 `goAsync()` 要有提交点和失败语义

`goAsync()` 只把完成回执从 `onReceive()` 返回点延后到 `PendingResult.finish()`，不会暂停广播 ANR 计时，也不会让进程获得持久任务保证。实现时要先定义清楚的提交点：幂等任务已持久化入队、ordered result 已写完，或短任务确实完成；随后在 `finally` 中调用 `finish()`。只启动一条裸线程再立刻结束 receiver，进程可能在工作完成前被回收。

短异步任务仍应使用应用级 scope、独立 dispatcher 和短于系统窗口的内部 deadline。下载、上传、数据库迁移、大目录扫描以及要求进程死亡后重试的任务，应由 receiver 快速校验和去重，再交给 WorkManager、JobScheduler 或有明确生命周期的服务。

### 7.5 sticky、系统事件与业务状态要分开

sticky broadcast 保存的是最近一次 Intent，后注册 receiver 可立即取得它；它不是带版本、一致性和事务语义的状态仓库。平台仍保留少量系统 sticky 事件，普通应用不应为业务状态新增 sticky 协议。需要当前值时优先读取权威存储，再把广播当作“状态可能变化”的通知。

`BOOT_COMPLETED` 和 `PACKAGE_*` 事件尤其容易形成启动风暴。receiver 内只做 action/用户/包名校验、幂等去重和任务入队；包扫描、索引重建与网络同步交给受约束任务，并把同一启动周期内的重复事件合并。发送端调用很快返回只说明 AMS 接受了请求，不表示下游完成，端到端指标必须包含系统排队、必要的进程启动和应用执行。

## 八、Android 17 的可观测性

### 8.1 查看队列快照与当前常量

下面的命令用于确认设备当前队列、历史记录和可调参数，避免只按 AOSP 默认值推断：

```bash
adb shell dumpsys activity broadcasts
adb shell dumpsys activity broadcast-stats

adb shell cmd activity get-broadcast-constant bcast_max_running_process_queues
adb shell cmd activity get-broadcast-constant bcast_delay_normal_millis
adb shell cmd activity get-broadcast-constant bcast_delay_cached_millis
adb shell cmd activity get-broadcast-constant bcast_timeout
```

`dumpsys activity broadcasts` 会打印每个 `BroadcastProcessQueue` 的 pending/active 状态、`runnableAt` 原因、history，以及 foreground/background 常量。`get-broadcast-constant` 返回 BroadcastQueue 当前读取到的配置；`bcast_timeout` 的结果取自前台常量实例，后台超时仍应在完整 dump 中核对。

### 8.2 Perfetto 的 Android 17 锚点

API 37 定义了 `broadcasts` Perfetto SDK category。启用相关 tracing v3 feature 后，每个接收者完成时可产生名为 `broadcast_delivered` 的 instant event，并附带结构化字段：

- sender/receiver uid、PID 和进程状态；
- `action`、receiver type；
- cold/warm process start type；
- `dispatch_delay_ms`、`receive_delay_ms`、`finish_delay_ms`；
- Intent flags、receiver priority、delivery group policy。

当前进程级实现把 `receive_delay_ms` 记为 0，因为“被进程队列选中”和“提交给应用”之间没有旧实现中的独立阶段。分析时重点检查以下两个值：

- `dispatch_delay_ms = scheduledTime - enqueueTime`：包含队列等待及冷启动影响；
- `finish_delay_ms = terminalTime - scheduledTime`：包含应用侧执行与完成回执。

不要复制依赖不存在字段或别名的 SQL。应先在目标 trace 中确认是否有 `broadcast_delivered`，再通过 `slice`/`args` 表查看该版本导出的参数名。没有启用 SDK category 时，仍可结合 `am_proc_start`、应用主线程 slice、sched 和 Binder 轨道还原延迟。

### 8.3 一次可靠的广播性能实验

1. 记录 `action`、发送 UID、接收者类型、ordered/foreground/deferral/delivery-group 配置；
2. 分别测 warm process、cached process 和 cold process；
3. 同时记录发送时刻、`onReceive()` 开始、异步 `finish()` 和业务完成时刻；
4. 用 host trace 对齐进程启动、`system_server` 队列、Binder 和应用主线程；
5. 报告 P50/P90/P99，并记录设备温度、CPU 负载和构建类型；
6. 用 `dumpsys` 保存实验时的 BroadcastConstants，避免配置漂移。

## 九、版本边界

- Android 8 / API 26：面向 API 26+ 的应用受到 manifest implicit broadcast 限制；
- Android 14 / API 34：cached app 的 context-registered broadcast 可以延后，公开 `BroadcastOptions` deferral API；
- Android 16 / API 36：跨进程 receiver priority 顺序不再保证，priority 只在同一应用进程内有效；
- Android 17 / API 37：源码结构以 `BroadcastQueueImpl`、`BroadcastProcessQueue` 和逐接收者 `delivery[]` 为准。

## 十、源码锚点

- 发送与接收者解析：
  - `frameworks/base/core/java/android/app/ContextImpl.java`
  - `frameworks/base/services/core/java/com/android/server/am/BroadcastController.java`
- 队列与调度：
  - `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java`
  - `frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java`
  - `frameworks/base/services/core/java/com/android/server/am/BroadcastRecord.java`
  - `frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java`
- 标志与公开选项：
  - `frameworks/base/core/java/android/content/Intent.java`
  - `frameworks/base/core/java/android/app/BroadcastOptions.java`
- tracing：
  - `frameworks/base/core/java/android/os/PerfettoCategories.java`
  - `BroadcastQueueImpl.logBroadcastDeliveryEventReported()`
- 官方行为说明：
  - [Broadcasts overview](https://developer.android.com/develop/background-work/background-tasks/broadcasts)
  - [Android 14 behavior changes](https://developer.android.com/about/versions/14/behavior-changes-all#cached-broadcasts)
  - [BroadcastOptions API](https://developer.android.com/reference/android/app/BroadcastOptions)

Android 17 会在及时性、进程启动成本、cached 状态和系统健康之间调度广播，不保证每一条事件都立即唤醒每一个进程。分析时应判断接收者为何在当前时 runnable，再区分排队、冷启动、Binder 提交和应用执行，进而决定是优化接收者、调整发送策略，还是改用更合适的 IPC/任务机制。
