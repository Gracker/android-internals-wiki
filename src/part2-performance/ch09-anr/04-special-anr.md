---
title: "特殊与跨边界 ANR"
chapter: "9.4"
section: "9.4"
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-27"
last_verified_against: "AOSP android-15.0.0_r1 ART heap/gc_cause anchors, SQLite WAL docs, Android 14-17 FGS timeout research"
confidence: medium
sources:
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: aosp
  path: frameworks/base/core/java/android/app/SharedPreferencesImpl.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
- type: aosp
  path: frameworks/base/core/java/android/app/IActivityManager.aidl
- type: web
  note: 高爷原创 ANR 分析系列
  path: https://androidperformance.com/
tags: ['anr', 'sharedpreferences', 'contentprovider', 'binder', 'broadcast', 'io-blocking', 'system-load']
related_chapters: ['9.1', '9.2', '9.3', '1.4', '4.3', '4.4', '6.3']
task6_state: "reviewed"
task6_result: pass-light-edit
task2b_result: fixed
last_task2b_at: "2026-05-22T19:18:14+08:00"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-15"
rework_date: "2026-04-16"
rework_by: "task2b-rework"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
status: "finalized"
pipeline_stage: "ready-to-publish"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-15"
last_task9_at: "2026-06-15T09:27:19+08:00"
auto_promoted_by: "openclaw-task6"
auto_promoted_date: "2026-06-15"
task2b_state: fixed
p0: 0
p1: 0
p2: 0
updated_by: "openclaw-task9"
updated_date: "2026-06-15"
review_notes: "2026-05-22 task2b rework: P0×2 IActivityManager.aidl路径+ModernBroadcastQueue线程模型；P1×2 Freezer广播口径收窄+16KB SQLite条件化。2026-05-22 Task6 re-review: pass-light-edit。L1/L2 小修 2 处（ContentProvider 顺序句式、占位提示改为 Trace 观察点）。既有 Task9 16KB SQLite P1 queue pending，保持 task2b_pending。 2026-05-22 16:06 Task6 re-review: pass-light-edit。L1/L2 小修 1 处；修复版本演进里的物理动词式表达；既有 Task9 P0（16KB SQLite 页大小排查路径）queue 保留，保持 task2b_pending。 2026-05-22 19:26 Task9 re-review: pass-tech-review，P0/P1=0；P2 低内存/LMK 因果链精度已写 suggestions；queue 无 pending，自动晋升 finalized。 2026-06-15 Task2B Verifier: status 修正 finalized→ready-for-review（Task9 auto-fixed 后未改 status，阻塞 Task6 回流）。 2026-06-15 Task6 re-review (revisiting→reviewed): pass-light-edit。L1 applicable_versions 补 Android 17；L2 无问题；L3/L4 无回炉项。Task9 idle audit P0/P1=0，queue 无 pending，自动晋升 finalized。"
rework_round_2: "2026-05-04"
last_task9_audit: "2026-06-15"
task9_audit_notes: "2026-05-22 idle audit: P0×2 / P1×2; see logs/deep-review/2026-05-22-08-audit.md. 2026-06-15 idle audit auto-fix: ART GC cause 常量修正，见 logs/deep-review/2026-06-15-09-audit.md。"
last_task6_audit: "2026-06-15"
task6_audit_notes: "2026-05-22 idle audit: L1 wording fixes; status changed from finalized to ready-for-review because Task9 queue has pending P0/P1 issues."
auto_promotion_revoked_by: "openclaw-task6"
auto_promotion_revoked_date: "2026-05-22"
auto_promotion_revoked_reason: "Task9 audit queue pending; finalized status was inconsistent."
last_task9_review_log: "logs/deep-review/2026-06-15-09-audit.md"
task9_review_notes: "2026-06-15 Task9 idle audit auto-fix: 修正 ART GC cause 常量 kGcCauseNativeAlloc -> kGcCauseForNativeAlloc；证据：AOSP art/runtime/gc/gc_cause.h android-14.0.0_r1/15.0.0_r1/16.0.0_r1。未发现需写 queue 的 P0/P1。"
last_task6_at: "2026-06-15T12:05:00+08:00"
last_task6_review_log: "logs/review/2026-06-15-12-review.md"
finalized_date: "2026-06-15"
finalized_by: "openclaw-task9-auto-promote"
auto_promoted: true
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
last_task9_autofix_at: "2026-06-15"
---
# 9.4 特殊与跨边界 ANR

[§9.2 ANR 类型与触发条件](02-anr-types.md) 和 [§9.3 ANR 分析方法](03-anr-analysis.md) 说明了 Android 17 detector、时间点和证据等级，下面沿用这些定义。

## “特殊”指的是证据跨了边界

ANR 仍由 Input、Broadcast、Service、ContentProvider、Job 等 detector 按各自期限判定。这里讨论的场景有一个共同点：触发超时的进程与消耗时间的资源拥有者可能分属不同线程、进程，甚至不同内核子系统。

常见跨边界关系包括：

- 主线程已 Runnable，CPU 时间被同 cpuset 的其他线程消耗；
- 调用方主线程等待 Binder reply，慢路径位于服务端或更深的嵌套调用；
- `SharedPreferences.apply()` 已返回，组件完成信号仍被尚未写完的数据拖住；
- Provider 初始化发生在应用冷启动早段，超时却表现为输入、广播或调用方 ANR；
- GC、reclaim、page fault 和低频 CPU 同时挤压主线程预算；
- SQLite 调用卡在连接池、事务、checkpoint 或文件系统中的某一层。

分析时不要用“系统问题”或“应用问题”提前结束调查。每个结论都应写清 detector、等待者、资源拥有者、时间区间和能够实施的修复点。

源码锚点为 AOSP `android-17.0.0_r1`，内核语义锚点为 `android17-6.18-2026-06_r6`。

## CPU 饥饿、I/O 等待与 freezer

### 主线程 Runnable 才是 CPU 饥饿的直接入口

主线程长时间处于 Runnable、Running 占比很低，说明它已具备运行条件却没有及时获得 CPU。整机 CPU 利用率高、Load 高或某个进程占比高只能说明环境，不能替代目标线程的调度证据。

Perfetto 中要按唤醒事件拆分：

1. 主线程何时从睡眠或等待变为 Runnable；
2. wakeup-to-run 延迟多长；
3. 延迟期间同 CPU、同 cpuset 上运行了哪些线程；
4. 目标线程的 nice、调度组、uclamp 与 CPU affinity 是否符合预期；
5. CPU frequency、idle 和 thermal 是否降低了可用算力。

多核总利用率没有达到 100% 时也可能发生局部饥饿。空闲核可能不在目标 cpuset、频率很低，或者任务受 affinity 限制。反过来，所有核很忙也不保证主线程必然饿死；更高优先级和调度组仍可能让它及时运行。

### `D` 状态需要 kernel callstack

6.18 内核中的 `TASK_UNINTERRUPTIBLE` 会在常见工具里显示为 `D`。它表示任务正处于不可中断等待，状态字母没有指出磁盘、驱动、futex、内存回收或 freezer 中的哪一种原因。

把 `D` 归到 I/O 至少需要一组相互支持的信号：

- 目标线程的 kernel callstack 落在文件系统、块设备或具体驱动等待路径；
- 同一时间段存在 block I/O、`fsync()`、major fault 或 I/O PSI 增量；
- 请求提交、设备服务和线程唤醒在时间线上能够对齐。

`loadavg` 把 Runnable 与不可中断等待任务都计入。8 核设备 Load 为 16 不能直接翻译为“CPU 使用 200%”，也不能判断其中有多少任务在等 I/O。

### freezer 要用冻结状态确认

`D` 和 `__refrigerator` 都不应当作 Cached Apps Freezer 的单点证明。6.18 内核有独立的 `TASK_FROZEN` 状态；cgroup v2 在 `cgroup.freeze` 完成后把 `cgroup.events` 的 `frozen` 置为 `1`。Android 系统侧还会记录 freeze/unfreeze reason。

Android 17 的 Broadcast 路径对 freezer 有明确处理：

- `BroadcastQueueImpl` 发现目标是 warm process 时，会在投递前调用临时解冻；
- 进程进入 running broadcast queue 时，系统通过 process state controller 更新接收状态，旧开关路径也会显式解冻；
- `BroadcastAnrTimer` 使用 `AnrTimer.Args().extend(true)`，允许按软超时窗口内的 CPU delay 延长等待；
- 当前锚点没有在这个 timer 上配置 `freeze(true)`。

这些规则只约束 Broadcast。Input、execute-service、Provider 和应用自建 Binder 协议各有自己的冻结与进程状态路径。报告应同时给出目标 PID 的冻结区间、unfreeze reason、receiver 调度时间和 ANR timer 起点。

## 广播洪峰：排队延迟与 receiver ANR 要分开

### Android 17 按进程组织广播队列

`BroadcastQueueImpl` 为每个目标进程维护 `BroadcastProcessQueue`，再按优先级、可运行时间和全局并行度选择运行队列。默认普通并行进程队列数在低内存设备为 2、其他设备为 4，DeviceConfig 可以改写。系统还限制单个 running process queue 连续投递的 active broadcast 数量，以便其他进程获得调度机会。

这个模型没有取消以下约束：

- 同一进程默认仍由主线程顺序处理 receiver callback；
- ordered broadcast 和需要 result 的投递仍有完成依赖；
- `goAsync()` 之后，`PendingResult.finish()` 仍是本次交付的完成信号；
- 某些运行时注册的无序 receiver 可走 assumed-delivered，不启动 receiver ANR timer。

receiver ANR timer 在 `dispatchReceivers()` 准备向 warm process 调度回调时启动。广播在 system_server 队列里等待的时间不会自动继承到该 receiver 的 10/60 秒窗口；系统把 receiver 调度出去后，主线程排队、应用初始化、`onReceive()`、异步工作和延迟的完成回执才会消耗这只 timer。

### 洪峰为何仍会产生一组 ANR

大量广播可以同时制造三种压力：

- system_server 排队和进程启动增加，用户可见动作整体变晚；
- 多个接收进程同时执行初始化、Binder、数据库和文件写入，争用 CPU 与 I/O；
- receiver 自己的 worker pool、`QueuedWork` 或对端服务已被前一批工作占满。

因此，同一时间段出现多条 `Broadcast of Intent` 只说明存在聚集现象。要写成“广播洪峰导致连锁 ANR”，还要证明发送速率或 pending queue 上升、各 receiver 的 timer 区间重叠，以及它们共享同一项受压资源。

排查时保留以下时间点：

| 时间点 | 说明 |
|---|---|
| 入队 | 广播进入 system_server 队列 |
| 进程启动 | 冷进程开始拉起、attach 完成 |
| 调度 receiver | ANR timer 可能在此启动 |
| `onReceive()` 开始/返回 | 同步 receiver 的执行区间 |
| `goAsync()` / `finish()` | 异步 receiver 的生命周期 |
| `finishReceiver()` 到达 system_server | 平台收到完成回执 |

若主线程 trace 停在 `nativePollOnce`，应检查自定义 Handler、`goAsync()` worker 和 `QueuedWork`。广播工作可能从未在主线程执行，主线程空闲与 Broadcast ANR 可以同时成立。

### 修复方向

- 合并应用内部的高频事件，避免用全局广播传递可直接调用的进程内状态；
- receiver 只解析必要字段并快速安排有界工作；
- `goAsync()` 使用有容量规划的专用执行器，每条路径在 `finally` 中完成 `PendingResult`；
- 长任务交给 JobScheduler、WorkManager 或前台服务，并遵守对应的后台执行规则；
- 监控 sender UID、action、pending 数、冷启动数、receiver 执行和 finish 延迟。

扩大线程池可能让 CPU、Binder 或数据库竞争更严重。应先确认排队来自容量不足，还是任务本身在等待不可用资源。

## Provider 初始化：三个超时出口

### Provider 早于 `Application.onCreate()`

Android 17 的 `ActivityThread.handleBindApplication()` 先创建 `Application` 对象，再调用 `installContentProviders()`，之后才执行 `Instrumentation.callApplicationOnCreate()`。Provider 的 `attachInfo()` 会进入其 `onCreate()`，所以静态 Provider 的初始化位于应用冷启动主线程早段。

这段时间可能从三个出口表现出来：

1. **No-focused-window 或 Input ANR**：Activity 的首窗因 Provider 初始化迟迟没有建立，或主线程无法处理输入。
2. **Broadcast/execute-service ANR**：系统已把 receiver 或 Service transaction 排在 `bindApplication` 之后，应用初始化占用其完成期限。
3. **调用方派生 ANR**：另一个应用在主线程同步获取或调用该 Provider，等待目标进程发布和回复，调用方自己的输入期限到期。

Android 17 的 10 秒 Provider publish guard 属于进程初始化保护。超时后系统以 `REASON_INITIALIZATION_FAILURE` 移除 Provider 进程，它不是 Provider ANR。显式远程调用监视要由调用方配置 `ContentResolver.setDetectNotResponding()`，到期后才进入 `ContentProvider not responding` ANR。三条路径的 reason 和被归责进程不同，详见 [§9.2 的 Provider 边界](02-anr-types.md#contentprovider发布保护与调用-anr-要分开)。

### 诊断 Provider 冷启动

时间线上至少对齐：

- 目标进程 fork、attach 与 `bindApplication`；
- 各 Provider 的 `attachInfo()` / `onCreate()`；
- `Application.onCreate()`；
- Provider publish；
- 调用方的 acquire、query/call 与 Binder reply；
- 首窗或 receiver/Service 的 deadline。

若目标进程在 Provider publish guard 到期前被移除，调用方可能收到 provider acquisition failure，而非目标进程 ANR。若调用方主线程仍在等待或重试，它仍可能随后发生自己的 Input ANR。

### App Startup 能解决哪部分

Jetpack App Startup 让多个组件共享一个 `InitializationProvider`，并用 `Initializer.dependencies()` 声明顺序。通过 manifest 注册的 initializer 仍在 Provider 初始化阶段执行；只把多个 Provider 合成一个，不会自动缩短所有初始化工作。

收益来自两点：

- 去掉多个独立 Provider 的实例化和重复发现成本；
- 对启动不必需的组件关闭自动初始化，在业务需要时用 `AppInitializer` 懒加载。

第三方 SDK 自带 Provider 时，要通过 manifest merge 检查并按 SDK 文档关闭自动初始化。直接删除 Provider 可能破坏 SDK 契约。

## `SharedPreferences.apply()`：返回快，完成信号仍会等待

### Android 17 的写入链

`apply()` 先通过 `commitToMemory()` 更新内存状态，再把 `writeToDiskRunnable` 放入 `QueuedWork`。它还注册一个等待 `writtenToDiskLatch` 的 finisher。下面的 Android 17 摘要片段用于说明这三个对象的关系：

```java
final MemoryCommitResult mcr = commitToMemory();
final Runnable awaitCommit = () -> {
    try {
        mcr.writtenToDiskLatch.await();
    } catch (InterruptedException ignored) {
    }
};

QueuedWork.addFinisher(awaitCommit);

Runnable postWriteRunnable = () -> {
    awaitCommit.run();
    QueuedWork.removeFinisher(awaitCommit);
};

enqueueDiskWrite(mcr, postWriteRunnable);
```

`apply()` 返回时内存值已经可见，磁盘写入可能仍未结束。`enqueueDiskWrite()` 串行执行 XML 写入、`FileUtils.sync()` 与结果通知；存储拥塞、文件过大或短时间多次修改都会拉长队尾。

### 不同组件边界有两种等待方式

Android 17 的调用点需要逐条区分：

- **Activity stop**：现代应用在 `handleStopActivity()` 的主线程调用 `QueuedWork.waitToFinish()`；pre-Honeycomb 兼容路径在 pause。
- **Service start/stop**：`handleServiceArgs()` 与 `handleStopService()` 在向 AMS 报告执行完成前调用 `waitToFinish()`。
- **Manifest receiver**：`PendingResult.finish()` 发现有 pending work 时，把 `sendFinished()` 排到 QueuedWork 队尾，避免阻塞当前线程；Broadcast ANR timer 会继续等完成回执。

`QueuedWork.waitToFinish()` 会在调用线程执行 `processPendingWork()`，随后逐个运行 finisher。因此 Activity/Service 主线程既可能亲自执行尚未开始的写盘 runnable，也可能等另一个线程已开始的写盘完成。Broadcast 路径则可能出现主线程已经回到 `nativePollOnce`，完成回执仍排在慢写盘后面的现象。

### 如何确认

需要把以下证据放到同一时间窗：

- ANR reason 是 Broadcast、execute-service 还是 Input；
- `apply()` 的调用次数、文件名和待写 generation；
- `QueuedWork.waitToFinish()`、`PendingResult.finish()`、`awaitCommit` 的栈或 slice；
- queued-work-looper 的 `writeToFile()`、`fsync()` 与调度状态；
- I/O latency、I/O PSI、reclaim 和存储错误。

只看到 `apply()` 调用不够，已经合并掉的中间 generation 可能没有写盘。只看到 `waitToFinish()` 也不够，QueuedWork 还可能承载其他框架工作。

### 修复

- 把一次业务状态的多个键合并到同一个 Editor；
- 避免把大集合、JSON 或高频计数写进 XML；
- 让非关键状态延后到交互期限之外；
- 用 DataStore 承载适合异步、事务化更新的偏好数据，并设计迁移与读取时机；
- 结构化、大体量或需要查询的数据使用 Room 等数据库；
- 在 userdebug/测试构建启用 StrictMode，并为 `apply` 到写盘完成建立耗时指标。

把 `apply()` 换成 `commit()` 会把同步写盘直接暴露给调用线程，通常会加重主线程风险。

## Binder 循环等待与线程池耗尽

### 用资源等待图描述死锁

“A 调 B，B 回调 A”还不足以构成死锁。Binder 支持嵌套同步事务和一定程度的重入，回调也可能由 Binder 线程池处理。死锁需要形成闭合的资源等待环，例如：

1. A 的线程持有锁 L，发起同步事务到 B；
2. B 的处理线程调用回 A；
3. A 的回调处理需要锁 L，或必须同步切到正等待 B 的主线程；
4. A 等 B，B 等 A 的回调，回调又等 L 或主线程。

另一个常见环来自线程池：A 的 Binder workers 全在等待 B，B 回调 A 时没有可服务线程；B 的 workers 又逐步被这些调用占满。此时没有 Java monitor 环，资源环落在“线程槽位”上。

### “默认 15”不是进程线程总数

Android 17 的 libbinder `ProcessState.cpp` 把 `DEFAULT_MAX_BINDER_THREADS` 设为 15，并通过 `BINDER_SET_MAX_THREADS` 告诉驱动可请求的线程上限。进程还可能显式加入 thread pool、修改上限或采用系统进程专用配置；总参与线程数不能靠数 15 条栈机械判断。

诊断时记录：

- 每个同步 transaction 的 from/to PID、TID 与 code；
- Binder worker 的 Running、Runnable、锁等待和嵌套事务；
- 驱动是否请求新线程、进程是否已启动 pool；
- one-way 队列是否拥塞；
- 调用前持有哪些应用锁，回调需要哪些执行器或主线程状态。

### 设计约束

- 不在持有跨模块锁时调用不受控的同步 IPC；
- Binder 服务实现不在持锁区调用客户回调；
- 回调需要主线程时采用有界异步协议，处理生命周期与取消；
- `oneway` 只移除调用方等待 reply，事务仍会排队并占用 buffer，不能当作无限容量通道；
- 为服务端耗时、并发数和队列长度设置观测与过载降级。

扩大 Binder thread pool 可能延后饱和，也可能增加锁、CPU 和内存竞争。先消除循环等待和无界扇出。

## GC、reclaim 与 LMKD 的叠加

### GC 要拆成暂停、分配等待和 CPU 竞争

Android 8 起 ART 默认采用 Concurrent Copying；Android 10 起该计划支持分代收集。并发收集仍包含短暂停顿，线程到达 suspend point 的延迟也计入暂停。一次 ANR 时间窗内还可能出现：

- 主线程等待正在进行的 GC；
- 分配慢路径触发 `kGcCauseForAlloc`；
- native allocation 压力触发 `kGcCauseForNativeAlloc`；
- GC 并发线程消耗 CPU，主线程 Runnable 等待变长；
- 分配速度高，GC 间隔缩短但每轮回收收益低；
- 大对象、fragmentation 或 collector transition 改变收集成本。

Android 17 的 `Heap::GrowForUtilization()` 会依据回收后存活字节、target utilization、growth limit 等信息更新 `target_footprint_` 与 `concurrent_start_bytes_`。不存在跨设备通用的“堆到 50% 就 GC”规则，也没有固定的 GC 次数或毫秒数可直接定义“GC 风暴”。

应读取该进程自己的 GC performance dump 和 Perfetto：

- 各 collector 的 pause histogram、time to suspend、总 GC 时间与吞吐；
- GC cause、young/full 类型、回收前后字节数；
- 主线程每次暂停及暂停之间的 Running/Runnable；
- HeapTaskDaemon/GC 线程的 CPU 消耗；
- 分配热点和对象存活率。

官方文档中的 1.83 ms 是特定示例设备的一组 Young CC 数据，不是 Android 平台阈值。

### 系统内存压力是另一条链

低可用内存可能触发 kswapd、direct reclaim、compaction、zram/swap I/O 和 major fault。这些活动会增加 CPU 与 I/O 压力，使 GC 和应用分配更慢。LMKD 根据压力与进程优先级选择牺牲进程，杀掉后台进程通常用于缓解压力；不要把“LMKD 杀进程”写成存活进程随后磁盘缺页的固定原因。

归因需要同时观察：

- memory/io PSI 在 ANR 窗口内的增量；
- direct reclaim、compaction、kswapd 与 swap/zram；
- major fault、存储读取和目标页来源；
- lmkd kill 的时间、被杀进程和目标应用 adj；
- 应用 Java/native heap、分配速率与 GC pause。

如果主线程主要卡在自身高频分配和 GC，修复点在对象生命周期与分配热点。若多个进程同时受 reclaim 和调度影响，应把系统内存压力列为主因或放大因素，并保留应用侧可移除的主线程工作。

## 前台服务附近的四条结果

FGS 日志经常与 ANR 同时出现，但四条规则的结果不同。Android 17 的边界如下：

| 场景 | Android 17 计时或入口 | 结果 |
|---|---|---|
| `startForegroundService()` 后未及时 `startForeground()` | 公开契约要求几秒内完成，ANR 概览给出 5 秒；源码默认内部 timeout 为 30 秒，另有 10 秒 ANR delay，均可配置 | ANR 延迟路径或 `ForegroundServiceDidNotStartInTimeException` |
| 后台不满足豁免却启动 FGS | 启动入口检查 | `ForegroundServiceStartNotAllowedException`，不是 ANR |
| `shortService` 到期未停止 | 默认约 3 分钟，`onTimeout(int, int)` 后源码默认再等 10 秒 | ANR |
| targetSdk 35+ 的 `dataSync` / `mediaProcessing` 用尽后台额度仍未停止 | 每个类型各自默认累计 6 小时，`onTimeout(int, int)` 后源码默认清理期 10 秒 | `ForegroundServiceDidNotStopInTimeException` 崩溃 |

内部 30 秒不能替代应用面向 SDK 文档遵守的 5 秒约束。DeviceConfig、HW timeout multiplier、targetSdk 和 compat change 可能改变设备行为，报告应记录原始 reason 与观测到的时长。

特殊场景常发生在服务 transaction 已排到主线程，而 `bindApplication`、Provider、数据库迁移或同步 I/O 仍未完成。修复时先构造最小合规通知并及时调用 `startForeground()`，再启动耗时工作；收到 `onTimeout()` 后只做有界清理并尽快停止服务。

完整 detector 和源码路径见 [§9.2 的 FGS 分类](02-anr-types.md#前台服务附近有三种不同的超时结果)。

## SQLite：连接池、WAL、checkpoint 与 I/O

### 先确认 journal mode

Rollback journal 的 `UNLOCKED/SHARED/RESERVED/PENDING/EXCLUSIVE` 五态不能直接套到 WAL。WAL 用共享内存中的 read mark 和写入、checkpoint、recovery 等锁协调：

- 多个 reader 可以按各自 end mark 读取一致快照；
- 同一 WAL 同时只有一个 writer；
- checkpoint 可以与 reader 并行，但不能越过仍被 reader 使用的 end mark；
- 长 reader 会让 checkpoint 无法推进到末尾，WAL 可能继续增长。

Android framework 还管理 `SQLiteConnectionPool`。主线程可能等连接、等 writer、等应用 Java 锁，也可能进入 `fsync()`、checkpoint 或文件系统等待。把所有栈归成“文件锁”会漏掉修复点。

### 多进程场景

多进程直接打开同一数据库时，writer、reader 和 checkpoint 分布在不同进程。一个后台进程持有长事务，主进程可能经历：

- 连接池没有可用连接；
- 新 writer 等当前 writer；
- 长 reader 阻止 checkpoint 前进；
- WAL 变大增加读取和恢复成本；
- commit/checkpoint 的同步写入遇到存储压力。

ContentProvider 可以把跨进程数据库访问集中到一个所有者进程，但调用方若在主线程同步查询，慢 Provider 仍会转化为 Binder 等待。Room 默认禁止主线程数据库访问；不要用 `allowMainThreadQueries()` 绕过这个保护。

### 16 KB 内核页不是 SQLite 页

Android 15 起 AOSP 支持 16 KB 内存页设备，Android 17 继续支持。内核 page size、文件系统 block size、SQLite `PRAGMA page_size` 和 WAL frame size属于不同层级。16 KB 内核页不会自动把既有数据库的 SQLite page 改成 16 KB，也没有“checkpoint 固定放大四倍”的平台规律。

下面的命令用于记录设备与数据库的现场配置：

```bash
adb shell getconf PAGE_SIZE
adb shell grep -m 1 KernelPageSize /proc/<pid>/smaps

sqlite3 app.db 'PRAGMA page_size;'
sqlite3 app.db 'PRAGMA journal_mode;'
sqlite3 app.db 'PRAGMA wal_autocheckpoint;'
sqlite3 app.db 'PRAGMA synchronous;'
```

设备命令确认进程运行时内存页，PRAGMA 确认数据库层设置。还要测 WAL 大小、checkpoint 返回值与耗时、connection wait、busy/locked 次数和块设备延迟。没有这些数据时，不应把 16 KB 兼容性直接写成 ANR 根因。

### 修复顺序

1. 移除主线程上的数据库访问；
2. 缩短事务，避免在事务内执行网络、Binder 或大对象转换；
3. 核对 WAL 是否启用、是否存在 attached database 等并发限制；
4. 找出长 reader、唯一 writer 和 checkpoint 的时间关系；
5. 仅在工作负载测量支持时调整 autocheckpoint 或同步策略；
6. 多进程数据库建立单一所有者或明确的进程间访问协议。

`beginTransactionNonExclusive()` 在 WAL 下可提高读写并发，但它不能让两个 writer 同时提交，也不能修复长事务和 I/O 拥塞。

## 快速判断表

| 采样现象 | 容易误写的结论 | 下一份证据 |
|---|---|---|
| 主线程 `nativePollOnce` | 应用无责任 | detector、采样延迟、worker、QueuedWork |
| 主线程 Runnable 很长 | CPU 已经 100% | wakeup-to-run、cpuset、频率、竞争线程 |
| 主线程 `D` | 磁盘慢或进程冻结 | kernel callstack、block I/O、cgroup frozen |
| `BinderProxy.transact` | 对端服务有 bug | transaction flow、对端线程、嵌套调用 |
| 15 个 Binder worker | 线程池一定满 | 驱动请求、显式 join、进程配置、等待图 |
| `QueuedWork.waitToFinish` | `apply()` 一定写盘慢 | pending work 类型、writeToFile、fsync |
| Provider `onCreate()` 慢 | Provider ANR | 原始 reason、publish guard、调用方 deadline |
| GC slice 密集 | GC 是唯一根因 | pause、time to suspend、分配与 sched |
| Load 很高 | 所有 CPU 核已满 | sched、CPU idle/frequency、`D` 任务 |
| WAL 文件很大 | writer 挡住所有 reader | reader end mark、checkpoint、connection pool |

## 版本演进

- **Android 8 / API 26**：加入 `startForegroundService()`；ART 默认 GC 计划切换到 Concurrent Copying。
- **Android 10 / API 29**：Concurrent Copying 支持分代收集。
- **Android 12 / API 31**：后台启动 FGS 的入口限制趋严，使用 `ForegroundServiceStartNotAllowedException` 表达拒绝。
- **Android 14 / API 34**：Broadcast timeout 可按 CPU starvation 延长；加入 `shortService` 与超时回调。
- **Android 15 / API 35**：AOSP 支持 16 KB page-size 设备；targetSdk 35+ 的 `dataSync`、`mediaProcessing` 进入限时 FGS 规则。
- **Android 17 / API 37**：结论锚点为 `BroadcastQueueImpl`、`BroadcastAnrTimer`、Android 17 ActivityThread/QueuedWork、ART heap 和 6.18 内核状态。

历史变化可以帮助解释旧设备日志，现场结论仍要按 build fingerprint、targetSdk、DeviceConfig 和原始 reason 校准。

## 与其他章节的关系

- [§1.4 Binder IPC](../../part1-fundamentals/ch01-architecture/04-binder.md)：同步事务、重入与线程池。
- [§1.10 ContentProvider](../../part1-fundamentals/ch01-architecture/10-content-provider.md)：安装、发布和跨进程调用。
- [§4.3 ART 内存](../../part1-fundamentals/ch04-memory/03-art-memory.md)：GC、堆增长与分配路径。
- [§4.4 LMK](../../part1-fundamentals/ch04-memory/04-lmk.md)：内存压力与进程牺牲策略。
- [§6.3 I/O 调度](../../part1-fundamentals/ch06-storage/03-io-scheduling.md)：block I/O 与存储延迟。
- [§9.5 ANR 案例集](05-case-studies.md)：跨层证据在完整案例中的使用。

## 参考资料

Android 17 平台源码：

- [ActivityThread：Provider、组件边界与 QueuedWork](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [SharedPreferencesImpl：apply 与写盘](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/SharedPreferencesImpl.java)
- [QueuedWork：pending work 与 finisher](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/QueuedWork.java)
- [BroadcastReceiver：PendingResult.finish](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/BroadcastReceiver.java)
- [BroadcastQueueImpl](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastQueueImpl.java)
- [BroadcastProcessQueue](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastProcessQueue.java)
- [ActiveServices：execute-service 与 FGS timeout](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)
- [ProcessState：Binder thread-pool 配置](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [ART Heap](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [ART GC causes](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/gc_cause.h)
- [SQLiteDatabase](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabase.java)
- [SQLiteConnectionPool](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java)

内核与公开文档：

- [Android Common Kernel 6.18：task state](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h)
- [Android Common Kernel 6.18：PSI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/accounting/psi.rst)
- [Android Common Kernel 6.18：cgroup v2 freezer](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)
- [Android Developers：诊断和修复 ANR](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android Developers：App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Android Developers：DataStore](https://developer.android.com/topic/libraries/architecture/datastore)
- [Android Developers：FGS timeout](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Android Developers：排查 FGS](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [Android Developers：支持 16 KB page size](https://developer.android.com/guide/practices/page-sizes)
- [AOSP：ART GC 调试](https://source.android.com/docs/core/runtime/gc-debug)
- [SQLite：WAL](https://www.sqlite.org/wal.html)
- [SQLite：rollback journal locking](https://www.sqlite.org/lockingv3.html)
- [高爷：Android App ANR 分析系列](https://www.androidperformance.com/2025/02/08/Android-ANR-02-How-to-analysis-ANR/)
