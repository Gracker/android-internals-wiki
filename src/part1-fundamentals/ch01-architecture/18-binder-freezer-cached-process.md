---
title: Binder Freezer 与缓存进程冻结
chapter: '1.18'
section: '1.18'
status: finalized
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6 + Android 17 API 37 official documentation
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/cached-apps-freezer"
  - type: official
    path: "https://source.android.com/docs/core/architecture/ipc/binder-freezer"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/os/IBinder"
  - type: official
    path: "https://developer.android.com/reference/android/os/RemoteCallbackList"
  - type: official
    path: "https://docs.kernel.org/admin-guide/cgroup-v2.html"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/IBinder.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/RemoteCallbackList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java @ android-17.0.0_r1"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/android/binder.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/cgroup/freezer.c"
tags:
  - android
  - binder
  - cached-app
  - freezer
  - cgroup-v2
  - oom-adjuster
  - performance
related_chapters:
  - '1.3'
  - '1.4'
  - '1.17'
  - '5.8'
  - '26.8'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 1.18 Binder Freezer 与缓存进程冻结

Android 会把退到后台、当前没有重要工作的进程标为缓存进程（cached process），并暂时保留在内存中，以减少下次打开时的冷启动成本。但进程存活不代表它仍应执行工作：如果缓存进程继续运行轮询线程、定时器或回调，它仍会消耗 CPU，甚至唤醒设备。

缓存应用冻结器（Cached Apps Freezer）在“继续运行”和“杀掉回收”之间增加了一种状态：

```text
进程仍存在、地址空间仍存在
            +
进程中的线程暂时不能获得 CPU
```

冻结后，进程和地址空间仍在，但其中的线程暂停执行。它节省的是缓存进程的 CPU 与唤醒成本。内存压力到来时，低内存终止守护进程 `lmkd` 仍可杀掉它；进程重新进入前台或接到生命周期工作时，系统也可以先解冻再继续执行。

Binder 路径需要单独处理。被冻结的线程无法处理进程间通信：同步调用不能无限等待，`oneway` 异步事务也不能无限堆积。以下结合 Android 17 框架与 Android 通用内核（Android Common Kernel，ACK）6.18 源码说明这条链路。

## 1. 先区分冻结器、Doze 和 LMK

| 机制 | 主要对象 | 直接动作 | 进程内存 | 恢复方式 |
| --- | --- | --- | --- | --- |
| Cached Apps Freezer | 已进入缓存状态的应用进程 | 暂停线程执行 | 通常仍保留 | 系统解冻后继续执行 |
| Doze / App Standby | 设备或应用的后台活动 | 延后或限制 Job、Alarm、网络等能力 | 不要求进程冻结 | 满足窗口、配额或状态条件 |
| 后台启动 / 前台服务（FGS）限制 | 组件启动与长期后台执行 | 拒绝、限时或约束组件行为 | 不直接决定是否保留 | 依组件和用户可见状态变化 |
| `lmkd` | 内存压力下的低优先级进程 | 杀进程并回收内存 | 释放 | 下次需要时重新启动 |

因此，下列推断都不成立：

- “进程被冻结，所以按比例分摊的物理内存（PSS）已经释放。”
- “应用处于 Doze，所以进程一定没有 CPU 时间。”
- “进程处于缓存状态，所以它一定已经被冻结。”
- “进程已被冻结但仍在内存，所以不会被杀。”

是否启用 Cached Apps Freezer 还受设备配置影响。AOSP 提供 `activity_manager_native_boot/use_freezer` 和开发者选项，但量产设备是否启用、控制组（cgroup）如何布局、厂商是否增加自己的后台策略，都需要在实机上确认。

## 2. Android 17 的决策链：先把进程重要性转换成 CPU 执行资格

`oom_adj` 是进程在内存压力下的终止优先级分值，通常数值越低，进程越重要；进程状态（proc state）则描述它当前处于前台、服务、缓存等哪一类状态。理解当前实现时，不能只背一句“`oom_adj >= CACHED_APP_MIN_ADJ` 就冻结”。Android 17 会把这些状态转换为 CPU 执行资格（capability），再决定能否冻结：

```text
Activity / Service / Broadcast / binding 等状态
                     │
                     ▼
OomAdjuster 计算 proc state、oom_adj 与 capability
                     │
                     ├─ PROCESS_CAPABILITY_CPU_TIME
                     └─ PROCESS_CAPABILITY_IMPLICIT_CPU_TIME
                                      │
                                      ▼
getFreezePolicy()
  ├─ 持有任一 CPU_TIME capability → 不冻结
  └─ 两者都没有                  → 可冻结
                                      │
                                      ▼
ActivityManagerService
  ├─ freezeAppAsyncLSP()
  └─ unfreezeAppLSP()
                                      │
                                      ▼
CachedAppOptimizer 执行 Binder freeze 与 cgroup freeze
```

流程图中的两个 `CPU_TIME` 标志都表示进程仍应获得 CPU 时间：一个来自当前明确工作，另一个保留旧 `oom_adj` 阈值所表达的兼容行为。

### 2.1 显式 CPU_TIME：当前确实有工作要执行

`android-17.0.0_r1` 的 `psc/OomAdjuster.java` 会为下列典型状态授予 `PROCESS_CAPABILITY_CPU_TIME`：

- UID 位于电源管理允许名单。
- 进程处于顶部（top）状态，或持有用户可感知的前台 Activity。
- 正在启动或停止 Service。
- 承载前台服务。
- 正在接收广播。
- 正在运行 instrumentation 测试。
- CPU 执行资格通过重要客户端的绑定关系传递而来。

这比“缓存 / 非缓存”二分更能表达真实意图：一个进程当前是否仍有必须执行的工作。

### 2.2 隐式 CPU_TIME：保留 oom_adj 阈值的兼容行为

Android 17 并没有丢掉 oom_adj。`getImplicitCpuCapability()` 在下面任一条件成立时授予 `PROCESS_CAPABILITY_IMPLICIT_CPU_TIME`：

```java
adj < mFreezerCutoffAdj
        ||
maxAdj < mFreezerCutoffAdj
```

默认阈值来自 `ActivityManagerConstants.DEFAULT_FREEZER_CUTOFF_ADJ`：

```java
Flags.prototypeAggressiveFreezing()
        ? HOME_APP_ADJ
        : CACHED_APP_MIN_ADJ
```

设备还可通过 `activity_manager/freezer_cutoff_adj` 修改它。由此形成三条边界：

- 常规配置仍以缓存进程边界为基准。
- 激进冻结（aggressive freezing）实验可把资格范围提前到 `HOME_APP_ADJ`。
- 即使当前 adj 较低，`maxAdj` 约束也可能让进程继续获得隐式 CPU 时间。

排查“为什么没有冻结”时，要同时查看 adj、CPU 执行资格、功能开关和可在线调整系统参数的 DeviceConfig，不能只看 `curAdj`。

### 2.3 旧实现里的两个判断已经不能代表 Android 17

较早版本的分析常引用：

```text
ProcessCachedOptimizerRecord.shouldNotFreeze()
ProcessCachedOptimizerRecord.isFreezeExempt()
```

Android 17 当前主路径的 `getFreezePolicy()` 不再靠这两个状态决定资格；`ActivityManagerService` 的兼容轨迹甚至把对应占位值固定为 `false`。描述 Android 17 时，应使用 `CPU_TIME` / `IMPLICIT_CPU_TIME` 模型。

这不表示所有豁免都消失了。官方文档仍列出两类实现级保护：

- 缓存进程持有文件锁并阻塞非缓存进程时，系统会避免继续冻结锁持有者。
- `BIND_WAIVE_PRIORITY` 连接可能让服务进程进入缓存状态，但在相关客户端全部进入缓存状态前仍保持可运行。

它们是冻结执行链上的保护条件，不应重新包装成旧版 `shouldNotFreeze()` 结论。

## 3. 进入缓存状态后为什么还要等 10 秒

Android 17 的默认值来自：

```xml
<integer name="config_defaultFreezerDebounceTimeout">10000</integer>
```

`CachedAppOptimizer` 允许用 `activity_manager_native_boot/freeze_debounce_timeout` 覆盖这个资源值。默认等待 10 秒有两个目的：

1. 避免 Activity 刚退后台、Service 刚结束时立刻冻结，打断仍在收尾的状态切换。
2. 避免短时间内反复冻结和解冻，增加调度、Binder 与日志开销。

这段等待也叫防抖（debounce），用于让短暂状态变化稳定下来。实现并非简单地“发一个 10 秒后的消息”。它会维护 `earliestFreezableTime`：临时解冻可能继续推迟最早可冻结时间；立即冻结请求也要与这个时间以及待处理状态协调。

因此，看到进程进入缓存状态后仍运行几秒，并不能直接说明冻结器失效。要先确认：

- 当前 CPU 执行资格是否允许冻结。
- `earliestFreezableTime` 是否还没到。
- 是否有尚未完成的 Binder 事务导致重试。
- 是否刚发生生命周期事件或文件锁保护。

## 4. 冻结时，Binder 必须先于 cgroup

Android 17 的 `CachedAppOptimizer.freezeProcess()` 顺序很明确：

```text
1. freezeBinder(pid, true, timeout)
   ├─ 阻止新的同步事务进入
   └─ 等待 outstanding transaction 排空

2. setProcessFrozen(pid, uid, true)
   └─ 把进程置入 freezer cgroup

3. 标记 ProcessCachedOptimizerRecord.frozen = true
   └─ 写 AM_FREEZE、statsd 与 trace

4. getBinderFreezeInfo(pid)
   └─ 冻结后再次检查竞态窗口中的 pending transaction
```

竞态窗口指第一次检查结束到线程真正冻结之间，状态仍可能发生变化的短暂时间。流程先阻止新的同步 Binder 事务并等待旧事务结束，再通过 cgroup 暂停线程。两个动作不能交换：如果先停掉线程，却让 Binder 驱动继续接受同步事务，调用端就可能等待一个永远不会执行的服务端。

ACK `android17-6.18-2026-06_r6` 的 `BINDER_FREEZE` 路径也说明了这一点：

1. 先设置目标 `binder_proc.is_frozen = true`，阻止新的同步事务。
2. 若传入超时时间，等待 `outstanding_txns` 归零。
3. 再检查仍在等待回复的事务调用栈。
4. 若检查失败，清除 `is_frozen`，并把失败交给 Android 框架处理。

`CachedAppOptimizer` 遇到尚未完成的事务，或冻结后新出现的待处理事务，不会把本次操作记录为冻结成功。它会解冻、调整重试时间并重新安排冻结；反复出现时还会识别 Binder 事务洪泛，避免应用靠持续发送事务永久逃过冻结。

## 5. cgroup v2 freezer：请求冻结不等于已经冻结

控制组（cgroup）是 Linux 按进程组管理 CPU、内存等资源的机制。ACK 6.18 使用 cgroup v2 的冻结功能，用户空间通过 `cgroup.freeze` 请求冻结或解冻。下面两条命令展示写入值的含义：

```bash
echo 1 > cgroup.freeze   # 请求冻结本 cgroup 及其后代
echo 0 > cgroup.freeze   # 请求解冻
```

写入只发出请求，内核还需要区分两个状态：

| 状态 | 含义 |
| --- | --- |
| `CGRP_FREEZE` | 用户空间已经请求冻结 |
| `CGRP_FROZEN` | 本 cgroup 的任务以及需要计入的后代已经达到冻结条件 |

因此，写完 `1` 以后，应观察 `cgroup.events`：

```text
frozen 1
```

只有这个状态变为 `1`，才表示冻结转换完成。某个任务还没运行到可安全暂停的位置时，`CGRP_FREEZE` 可以已经置位，而 `CGRP_FROZEN` 尚未成立。

### 5.1 内核状态机

`android17-6.18-2026-06_r6/kernel/cgroup/freezer.c` 的关键路径是：

```text
cgroup_freeze(cgrp, true)
  └─ cgroup_do_freeze()
       ├─ set_bit(CGRP_FREEZE)
       ├─ 遍历 task
       │    └─ cgroup_freeze_task()
       │         ├─ JOBCTL_TRAP_FREEZE
       │         └─ signal_wake_up()
       └─ cgroup_update_frozen()
```

任务进入冻结点后，`cgroup_enter_frozen()` 会：

- 设置 `current->frozen = true`。
- 增加 cgroup 中已冻结任务的计数。
- 重新计算 `CGRP_FROZEN`。

解冻时则清除 `JOBCTL_TRAP_FREEZE`、唤醒任务，并在 `cgroup_leave_frozen()` 中更新计数。

### 5.2 性能含义

冻结不是忙等：任务不会占着 CPU 循环检查“能不能解冻”。因此，Java 线程、C/C++ 工作线程、Handler 和协程都不会继续执行。

冻结也不是回收：

- 虚拟地址空间仍在。
- Java 堆和 C/C++ 堆仍在。
- 文件描述符和 Binder 引用仍在。
- 驻留物理内存（RSS）和按比例分摊的物理内存（PSS）不会因为 `cgroup.freeze=1` 自动归零。

Android 14 以后，Android 框架可能在冻结前后触发垃圾回收（GC）、内存压缩、匿名页换入 ZRAM 等辅助动作。ZRAM 是用压缩内存充当交换空间的机制。这些动作可能降低物理内存压力，但要与“冻结器本身暂停 CPU”分开描述。

## 6. Binder Freezer 的两条事务路径

### 6.1 同步事务：驱动拒绝，系统终止被冻结的接收进程

目标 `binder_proc.is_frozen` 为 `true` 时，ACK r6 的 `binder_proc_transaction()` 对同步事务执行：

```text
proc->sync_recv = true
return BR_FROZEN_REPLY
```

平台对外的行为是：

- 同步事务不会排到冻结进程等待解冻。
- 调用端随后收到 `RemoteException`，已注册的 Binder 远端死亡监听也会被触发。
- 系统终止被冻结的接收进程，退出原因记录为冻结器。

Android 17 的 `CachedAppOptimizer` 同时保留两条发现路径：

- Binder 监控收到 `BR_FROZEN_REPLY` 报告后，直接按“冻结期间收到同步事务”处理目标 PID。
- 若即时报告能力未启用，解冻前的 `getBinderFreezeInfo()` 仍能发现 `SYNC_RECEIVED_WHILE_FROZEN` 并杀进程。

这项处理用于保护调用线程，与惩罚“服务端太慢”无关。最常见的应用错误是：

1. 客户端已经调用 `unbindService()`。
2. 服务端因失去重要绑定关系，退到缓存状态并被冻结。
3. 客户端仍保存旧的 `IBinder` 代理，继续发同步调用。

修复时要让 Binder 引用的生命周期与绑定关系一致：解绑后立即丢弃代理，不要把它当作永久可用的本地对象。

### 6.2 oneway 事务：允许入队，但队列并非无限

`oneway` 事务命中冻结目标时，Binder 驱动会：

```text
proc->async_recv = true
transaction 入 async queue
return BR_TRANSACTION_PENDING_FROZEN
```

目标解冻后才会消费这些事务。这个设计避免了同步等待，却带来两个问题：

- 事务继续占用目标进程的 Binder 缓冲区；空间耗尽时，系统会以 `SUBREASON_FREEZER_BINDER_ASYNC_FULL` 终止目标。
- 事件可能已经过期；解冻后一次性处理大量旧回调，还可能造成 CPU 使用突增和业务状态倒退。

“改成 `oneway`”只解决了等待方式，没有解决事件模型。更合适的策略通常是：

| 事件语义 | 冻结期间策略 |
| --- | --- |
| 瞬时采样、下一次可重新获取 | 丢弃 |
| 当前状态，以最新值为准 | 只保留最新一条 |
| 每条都是不可丢的业务记录 | 有上限地排队，并设计补偿、去重和持久化 |

如果“不可丢”意味着无限排队，这个协议仍然没有完成设计。

## 7. API 36+：使用系统提供的冻结回调队列

### 7.1 观察远端 Binder 的冻结状态

`IBinder.addFrozenStateChangeCallback()` 从 API 36 起成为公开 API。下面的示例注册回调，把远端是否冻结保存到 `remoteFrozen`：

```java
IBinder.FrozenStateChangeCallback callback = (who, state) -> {
    boolean frozen =
            state == IBinder.FrozenStateChangeCallback.STATE_FROZEN;
    remoteFrozen.set(frozen);
};

try {
    remoteBinder.addFrozenStateChangeCallback(executor, callback);
} catch (UnsupportedOperationException e) {
    // Kernel binder driver 不支持 frozen notification。
} catch (RemoteException e) {
    // 远端可能已死亡，按正常 Binder death 路径处理。
}
```

若注册成功，系统会通过给定的 `executor` 执行回调；异常分支分别处理内核不支持和远端已经死亡。

使用时要记住三个边界：

1. 只会观察远端 Binder；本地 Binder 与当前进程一起冻结或解冻。
2. 状态变化可能合并，只保证拿到最新状态，不能用回调次数统计冻结次数。
3. 内核不支持时会抛出 `UnsupportedOperationException`，必须有降级策略。

不再需要时可调用 `removeFrozenStateChangeCallback()`。所有 Binder 代理引用都释放后，注册也会自动移除，但显式解除通常更容易明确组件生命周期。

### 7.2 用 RemoteCallbackList 表达事件策略

API 36 的 `RemoteCallbackList` 支持三种“被调用方冻结时”的策略。下面的示例选择只保留最新回调：

```java
RemoteCallbackList<IMyCallback> callbacks =
        new RemoteCallbackList.Builder<IMyCallback>(
                RemoteCallbackList.FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT)
                .build();

callbacks.broadcast(callback -> {
    try {
        callback.onStateChanged(latestState);
    } catch (RemoteException ignored) {
        // RemoteCallbackList 会处理死亡的远端接口。
    }
});
```

当远端冻结时，旧状态会被新状态替换；解冻后只发送最后一次 `onStateChanged()`。

可选策略与适用场景：

| 策略 | 行为 | 适合 |
| --- | --- | --- |
| `FROZEN_CALLEE_POLICY_DROP` | 远端冻结时丢弃 | 高频瞬时事件 |
| `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT` | 只保留最新回调 | 音量、亮度、连接状态等状态同步 |
| `FROZEN_CALLEE_POLICY_ENQUEUE_ALL` | 按顺序排队 | 少量且每条都有意义的事件 |

`ENQUEUE_ALL` 也有队列上限。Android 17 默认最多 1000 条；达到上限后会丢掉最旧回调，构建器可用 `setMaxQueueSize()` 显式设置容量。选择这个策略时，仍要写出容量、溢出和恢复方案。

未设置策略的旧构造方式保留兼容行为：照常调用冻结的远端。SDK 36 及以上版本不推荐这种用法。

## 8. Freezer 对应用代码的几个隐蔽影响

### 8.1 固定频率任务可能在解冻后追赶

冻结期间，`Timer.scheduleAtFixedRate()` 或 `ScheduledThreadPoolExecutor.scheduleAtFixedRate()` 不会执行。解冻后，错过的固定频率任务可能快速连续运行。

如果业务需要“每次完成后再间隔一段时间”，应使用 `scheduleWithFixedDelay()`；如果任务允许由系统安排执行时机，优先考虑 WorkManager。不要在解冻后补跑几十次已经失去意义的轮询。

### 8.2 GC 与内存回收回调也无法执行

线程全部暂停意味着进程不能主动执行垃圾回收，也不能处理 `onTrimMemory()` 等内存回收提示回调。Android 14 起，Android 框架会调整通知和冻结前准备：

- 可见 Activity 退后台时尽早收到 `TRIM_MEMORY_UI_HIDDEN`。
- 进程进入缓存状态后，运行时可能先执行 GC。
- 其他内存回收提示级别不保证能在冻结进程中执行。

应用不能依赖“等 `onTrimMemory()` 再释放关键资源”来保证冻结前收尾。

### 8.3 不同广播采用不同的解冻方式

Android 14 起，为减少无意义的解冻：

- 通过代码动态注册的广播可在缓存期间排队，解冻后再投递。
- 在清单中声明的广播会先解冻进程，再投递。

因此，在系统轨迹中看到广播延迟时，不应先归因于 BroadcastQueue 卡死；还要检查目标是否处于缓存或冻结状态，以及接收器采用哪种注册方式。

### 8.4 TCP 套接字不能当作保活承诺

官方冻结器文档说明：当一个应用的所有进程都被冻结时，系统会终止该应用的活动 TCP 套接字，避免保活包（keepalive）唤醒基带。需要长期可靠传递的业务应使用 Firebase Cloud Messaging（FCM）、JobScheduler、WorkManager 或符合其语义的系统设施，不能依赖缓存进程维持套接字连接。

## 9. 退出归因：区分公开原因与内部子原因

`ApplicationExitInfo` 从 API 30 开始提供，`REASON_FREEZER` 从 API 33 起加入公开 SDK。下面的代码在应用下次启动时查询最近 20 条退出记录，并筛选冻结器导致的退出：

```java
ActivityManager am = context.getSystemService(ActivityManager.class);
List<ApplicationExitInfo> exits =
        am.getHistoricalProcessExitReasons(null, 0, 20);

for (ApplicationExitInfo info : exits) {
    if (Build.VERSION.SDK_INT >= 33
            && info.getReason() == ApplicationExitInfo.REASON_FREEZER) {
        Log.w(TAG, "Previous process was killed by freezer: "
                + info.getDescription());
    }
}
```

命中时，日志会记录系统提供的退出描述。Android 17 源码中的内部子原因包括：

| 子原因 | 含义 |
| --- | --- |
| `SUBREASON_FREEZER_BINDER_TRANSACTION` | 冻结期间收到同步 Binder 事务 |
| `SUBREASON_FREEZER_BINDER_IOCTL` | 冻结、解冻 Binder 或查询状态失败 |
| `SUBREASON_FREEZER_BINDER_ASYNC_FULL` | 冻结期间异步 Binder 缓冲区接近耗尽 |

这些子原因与 `getSubReason()` 都是隐藏 API，普通应用不能把它们当成公开诊断接口。平台或设备厂商调试可从 `dumpsys`、`system_server` 日志与源码获得更细的信息；应用侧应以公开原因、描述、自己的业务状态和时间线为准。

API 30～32 没有公开 `REASON_FREEZER` 常量。不要硬编码数值 `14` 跨版本猜测；这会混淆“当时平台是否记录这种原因”与“当前 SDK 中的常量值”。

## 10. 用四层证据诊断，避免根据缓存状态直接下结论

### 10.1 配置与 Android 框架状态

下面三条命令依次查看冻结器开关、CachedAppOptimizer 配置，以及进程重要性与冻结资格：

```bash
# 当前设备是否请求启用 cached apps freezer
adb shell device_config get activity_manager_native_boot use_freezer

# Android 17 的 CachedAppOptimizer 配置与统计
adb shell dumpsys activity cao

# 进程状态、adj、capability 与 LRU 信息
adb shell dumpsys activity processes
```

重点记录：

- `use_freezer`
- `freeze_debounce_timeout`
- `freezer_cutoff_adj`
- 进程状态与 `oom_adj`
- `CPU_TIME` 与 `IMPLICIT_CPU_TIME` 执行资格
- 待冻结状态与实际冻结状态

### 10.2 shell 控制实验

Android 17 的 ActivityManager shell 提供以下查询、冻结和解冻命令：

```bash
adb shell cmd activity isfrozen <PROCESS_OR_PID>
adb shell cmd activity freeze <PROCESS_OR_PID>
adb shell cmd activity unfreeze <PROCESS_OR_PID>
```

`--sticky` 会让强制状态保持到进程死亡，或下一次方向相反的 shell 操作为止，只应用于隔离的测试进程。实验结束必须解冻，不能拿线上关键进程做同步 Binder 探测。

### 10.3 cgroup 与事件日志

下面的命令用于定位进程所属的 cgroup、查找冻结状态文件、读取冻结事件和历史退出原因：

```bash
# 先找 PID 属于哪个 cgroup
adb shell cat /proc/<PID>/cgroup

# 设备路径可能不同；user build 也可能限制读取
adb shell find /sys/fs/cgroup \
  \( -name cgroup.freeze -o -name cgroup.events \)

# framework 冻结与解冻事件
adb logcat -b events -v threadtime | grep -E 'am_freeze|am_unfreeze'

# 历史退出原因
adb shell dumpsys activity exit-info <PACKAGE>
```

只看到 `cgroup.freeze=1` 还不够；还要确认对应 `cgroup.events` 的 `frozen=1`，并核对该 cgroup 确实包含目标 PID。

### 10.4 Perfetto 时间线

Android 17 的 `CachedAppOptimizer` 会在 ActivityManager 系统轨迹中写入一条名为 `Freezer` 的轨道：

```text
Freeze <process>:<pid> -1
Unfreeze <process>:<pid> <reason>
Reschedule freeze <process>:<pid> timeout=<...>, reason=<...>
```

分析顺序：

1. 用 `am_freeze` 或 `Freezer` 瞬时事件定位冻结窗口。
2. 检查目标线程在该窗口内是否还有运行中的轨迹区段。
3. 若出现 `Reschedule freeze`，核对尚未完成或新出现的待处理 Binder 事务。
4. 若进程消失，核对 `exit-info`、Binder 调用端和 `am_kill`。
5. 若解冻后 CPU 使用突增，检查积压的 `oneway` 事务、广播和固定频率任务。

Perfetto 没有采集 ActivityManager 或线程调度数据时，“没看到事件”不能证明冻结器没有运行。

## 11. 一个可复现的 Binder Freezer 实验

准备两个独立进程：

- 进程 A 提供一个同步方法和一个 `oneway` 方法。
- 进程 B 绑定 A，拿到 Binder 代理。

实验分三轮。

### 第一轮：正常绑定

保持绑定关系并调用同步方法。A 的重要性会被 B 的绑定提升，通常不应进入缓存进程冻结状态。应先证明基础 IPC 正常，再分析冻结行为。

### 第二轮：解绑后误用旧代理

1. B 调用 `unbindService()`，但故意保留旧代理。
2. 等 A 进入缓存状态，或在测试环境中使用 `cmd activity freeze`。
3. B 再发同步调用。

预期验证点包括：

- Binder 驱动返回冻结回复。
- B 收到 `RemoteException` 或 Binder 远端死亡通知。
- A 的退出记录为 `REASON_FREEZER`。

### 第三轮：oneway 积压

向冻结的 A 发送有限数量、带序号的 `oneway` 事件，然后解冻：

- 确认事件是否在解冻后按同一 Binder 对象内的 `oneway` 顺序到达。
- 观察事件是否已经过期。
- 观察解冻后的 CPU 使用是否突增。

不要用无限循环耗尽 Binder 缓冲区作为默认验证手段。需要验证溢出时，应在隔离设备上设置明确上限，并保存系统轨迹、事件日志和退出信息。

## 12. 版本边界

| 版本 | 已确认变化 | 工程含义 |
| --- | --- | --- |
| Android 11（API 30） | AOSP 支持 Cached Apps Freezer；`ApplicationExitInfo` 公开 | 设备是否启用仍取决于内核与配置 |
| Android 13（API 33） | 公开 `ApplicationExitInfo.REASON_FREEZER` | 应用可把冻结器终止与 LMK、ANR 分开统计 |
| Android 14（API 34） | 进入缓存状态后默认等待 10 秒再冻结；生命周期事件立即解冻；动态注册广播可排队；冻结前后配合 GC、压缩等操作 | 冻结器从单个开关扩展为更完整的缓存进程策略 |
| Android 16（API 36） | 公开 `IBinder` 冻结状态回调；`RemoteCallbackList` 增加远端冻结策略 | 回调服务可以按“丢弃、只留最新、全部排队”表达积压处理方式 |
| Android 17（API 37） | 当前 `OomAdjuster` 以显式、隐式 `CPU_TIME` 执行资格统一决定能否冻结；Binder 监控与冻结重试继续完善 | 框架源码以 `android-17.0.0_r1` 为准，内核源码以 `android17-6.18-2026-06_r6` 为准 |

版本演进可以保留，但描述当前行为时，不能继续用 Android 15/16 的旧文件路径代替 Android 17。特别是 `shouldNotFreeze()`、冻结阈值和 Binder 错误上报，已经出现足以影响结论的结构变化。

## 13. 常见误区

### “缓存进程一定被冻结”

不成立。设备可能没有启用冻结器，进程可能仍持有 CPU 执行资格，也可能处于防抖等待、Binder 重试或实现级保护中。

### “被冻结就等于释放内存”

不成立。冻结器的直接作用是停止 CPU 执行；进程仍占用地址空间和物理内存。GC、内存压缩、ZRAM 回写与 LMK 是另外的动作。

### “同步调用只会等到对方解冻”

不成立。Android 会拒绝发往冻结远端的同步 Binder 事务，并终止被冻结的接收进程，避免调用线程无限等待。

### “oneway 对冻结进程绝对安全”

不成立。它会积压并占用 Binder 缓冲区，解冻后还可能集中处理过期事件；缓冲区压力过高时，目标进程会被终止。

### “观察冻结回调就能统计冻结次数”

不成立。状态事件允许合并，API 只承诺最新状态。

### “厂商的‘冻结’都等于 AOSP Cached Apps Freezer”

不成立。必须用 ActivityManager 事件、cgroup 状态、Binder 冻结退出原因和厂商实现证据进行区分。

## 14. 复核清单

1. 确认设备的 `use_freezer`、内核支持和 cgroup v2 布局。
2. 同时记录进程状态、`oom_adj`、`CPU_TIME` 执行资格与冻结阈值。
3. 区分等待冻结、已经请求冻结和 `cgroup.events frozen=1`。
4. 检查 Binder 冻结是否先于 cgroup 冻结。
5. 同步调用命中冻结目标时，找到调用端、旧代理生命周期和退出原因。
6. 为 `oneway` 回调写清丢弃、只留最新、全量排队策略及容量上限。
7. API 36 及以上版本优先使用 `IBinder` 冻结回调或 `RemoteCallbackList` 策略。
8. 检查固定频率任务、广播与 `oneway` 是否在解冻后造成 CPU 使用突增。
9. 不把冻结本身写成内存回收；单独验证 GC、内存压缩、ZRAM 和 LMK。
10. 用 Perfetto、事件日志、cgroup 和退出信息四条时间线交叉证明结论。
11. 区分公开的 `REASON_FREEZER` 与隐藏的内部子原因。
12. 当前源码统一引用 `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6`。

## 参考资料

- [AOSP：Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [AOSP：Handle cached and frozen apps](https://source.android.com/docs/core/architecture/ipc/binder-freezer)
- [Android API：ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android API diff：API 33 新增 REASON_FREEZER](https://developer.android.com/sdk/api_diff/33/changes/android.app.ApplicationExitInfo)
- [Android API：IBinder](https://developer.android.com/reference/android/os/IBinder)
- [Android API：RemoteCallbackList](https://developer.android.com/reference/android/os/RemoteCallbackList)
- [Linux Kernel：Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [AOSP：OomAdjuster.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/psc/OomAdjuster.java)
- [AOSP：ActivityManagerConstants.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java)
- [AOSP：ActivityManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP：CachedAppOptimizer.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP：config_defaultFreezerDebounceTimeout（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)
- [AOSP：IBinder.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/IBinder.java)
- [AOSP：RemoteCallbackList.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/RemoteCallbackList.java)
- [AOSP：ApplicationExitInfo.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [ACK：Binder driver（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder.c)
- [ACK：Binder UAPI（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/uapi/linux/android/binder.h)
- [ACK：cgroup freezer（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/cgroup/freezer.c)
