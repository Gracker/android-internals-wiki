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
  - '26.9'
drafted_date: "2026-05-15"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构/官方文档"
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: "2026-06-14"
reviewed_by: openclaw-task6
reviewed_date: 2026-06-21
last_task6_at: "2026-06-21T01:06:00+08:00"
last_task6_review_log: "logs/review/2026-06-13-18-review.md"
task6_review_notes: "2026-06-21 Task6 round 4 re-review (post-task9-autofix): pass-light-edit. Task9 auto-fixed kernel source anchors (Linux main to Android common kernel android17-6.18-2026-04_r1). Re-verified writing quality after Task9 changes: L1 clean (no banned words, no high-freq issues, no translation tone). L2 clean (good narrative flow, proper structure, clear tables, good CJK-ASCII spacing). L3/L4: strong technical depth, good human feel, precise source references. All 6 anchors covered. No B-class issues. Auto-promoted to finalized: task6 pass-light-edit + task9 auto-fixed + no pending queue items."
task9_state: reviewed
last_task9_review_log: "logs/deep-review/2026-06-14-00-deep-review.md"
last_task9_at: "2026-06-14T00:24:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-14"
task9_result: auto-fixed
task2b_result: fixed
task2b_state: fixed
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
task9_review_notes: "2026-06-14 Task9 deep review：AUTO-FIX Binder/cgroup freezer 内核源码锚点，从 Linux main/master 切到 Android common kernel android17-6.18-2026-04_r1；framework android-17 tag 仍不可取，回到 Task6 复审。"
p0: 0
p1: 0
p2: 0
last_task9_audit: "2026-06-13"
last_task9_autofix_at: "2026-06-14"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
last_task6_audit: 2026-06-21
last_task2b_at: 2026-06-21T00:52:15+08:00
last_task2b_by: task2b-main
---

# 1.18 Binder Freezer 与缓存进程冻结

Android 把退到后台的进程保留在内存里，是为了下次打开时少付一次冷启动成本。但进程存活不代表它仍应执行工作：如果缓存进程继续跑轮询线程、定时器或回调，它仍会消耗 CPU，甚至唤醒设备。

Cached apps freezer 在“继续运行”和“杀掉回收”之间增加了一种状态：

```text
进程仍存在、地址空间仍存在
            +
进程中的线程暂时不能获得 CPU
```

它节省的是 cached 进程的 CPU 与唤醒成本。内存压力到来时，`lmkd` 仍可杀掉这个进程；重新进入前台或接到生命周期工作时，系统也可以先解冻再继续执行。

Binder 路径需要单独处理。被冻结的线程无法处理 IPC：synchronous call 不能无限等待，`oneway` transaction 也不能无限堆积。以下从 Android 17 framework 与 ACK 6.18 源码拆解这条链路。

## 1. 先区分冻结器、Doze 和 LMK

| 机制 | 主要对象 | 直接动作 | 进程内存 | 恢复方式 |
| --- | --- | --- | --- | --- |
| Cached apps freezer | 已进入 cached 状态的 App 进程 | 暂停线程执行 | 通常仍保留 | 系统解冻后继续执行 |
| Doze / App Standby | 设备或应用的后台活动 | 延后或限制 Job、Alarm、网络等能力 | 不要求进程冻结 | 满足窗口、配额或状态条件 |
| 后台启动 / FGS 限制 | 组件启动与长期后台执行 | 拒绝、限时或约束组件行为 | 不直接决定是否保留 | 依组件和用户可见状态变化 |
| `lmkd` | 内存压力下的低优先级进程 | 杀进程并回收内存 | 释放 | 下次需要时重新启动 |

因此，下列推断都不成立：

- “进程被 freeze，所以 PSS 已经释放。”
- “应用处于 Doze，所以进程一定没有 CPU 时间。”
- “进程处于缓存状态，所以它一定已经 frozen。”
- “进程 frozen 但仍在内存，所以不会被杀。”

是否启用 cached apps freezer 还受设备配置影响。AOSP 提供 `activity_manager_native_boot/use_freezer` 和开发者选项，但量产设备是否启用、cgroup 如何布局、厂商是否叠加自己的后台策略，都需要在实机上确认。

## 2. Android 17 的决策链：重要性先转换为 CPU capability

理解当前实现时，不能只背一句“`oom_adj >= CACHED_APP_MIN_ADJ` 就冻结”。Android 17 已把冻结资格收束到 CPU capability：

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

### 2.1 显式 CPU_TIME：当前需要执行

`android-17.0.0_r1` 的 `psc/OomAdjuster.java` 会为下列典型状态授予 `PROCESS_CAPABILITY_CPU_TIME`：

- UID 位于 power allowlist。
- 进程处于 top，或持有用户可感知的前台 Activity。
- 正在启动或停止 Service。
- 承载前台服务。
- 正在接收广播。
- 正在运行 instrumentation。
- CPU capability 通过重要 client 的 binding 关系传递而来。

这比“cached / non-cached”二分更能表达真实意图：一个进程当前是否仍有必须执行的工作。

### 2.2 隐式 CPU_TIME：保留 oom_adj 阈值的兼容语义

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

- 常规配置仍把 cached 边界作为基线。
- aggressive freezing 实验可把资格范围提前到 `HOME_APP_ADJ`。
- 即使当前 adj 较低，`maxAdj` 约束也可能让进程继续获得隐式 CPU 时间。

排查“为什么没冻”时要同时看 adj、capability、flag 和 DeviceConfig，不能只看 `curAdj`。

### 2.3 旧实现里的两个判断已经不能代表 Android 17

较早版本的分析常引用：

```text
ProcessCachedOptimizerRecord.shouldNotFreeze()
ProcessCachedOptimizerRecord.isFreezeExempt()
```

Android 17 当前主路径的 `getFreezePolicy()` 不再靠这两个状态决定资格；`ActivityManagerService` 的兼容 trace 甚至把对应占位值固定为 `false`。写 Android 17 时，应使用 `CPU_TIME` / `IMPLICIT_CPU_TIME` 模型。

这不表示所有豁免都消失了。官方文档仍列出两类实现级保护：

- cached 进程持有文件锁并阻塞 non-cached 进程时，系统会避免继续冻结锁持有者。
- `BIND_WAIVE_PRIORITY` 连接可能让服务进程进入 cached，但在相关 client 都 cached 之前保持可运行。

它们是冻结执行链上的保护条件，不应重新包装成旧版 `shouldNotFreeze()` 结论。

## 3. 进入缓存状态后为什么还要等 10 秒

Android 17 的默认值来自：

```xml
<integer name="config_defaultFreezerDebounceTimeout">10000</integer>
```

`CachedAppOptimizer` 允许用 `activity_manager_native_boot/freeze_debounce_timeout` 覆盖这个资源值。默认等待 10 秒有两个目的：

1. 避免 Activity 刚退后台、Service 刚结束时立刻冻结，打断仍在收尾的状态切换。
2. 避免短时间内反复 freeze/unfreeze，放大调度、Binder 和日志开销。

实现并非简单地“发一个 10 秒后的消息”。它会维护 `earliestFreezableTime`：临时解冻可能把最早可冻结时间继续向后推；立即冻结请求也要与这个时间以及 pending 状态协调。

因此，看到进程进入 cached 后仍运行几秒，并不自动说明 freezer 失效。要先确认：

- 当前 capability 是否允许冻结。
- `earliestFreezableTime` 是否还没到。
- 是否有未完成的 Binder 事务导致重试。
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

这两个动作不能交换。如果先停掉线程，再让 Binder 驱动继续接受同步事务，调用端就可能等待一个永远不会执行的 server。

ACK `android17-6.18-2026-06_r6` 的 `BINDER_FREEZE` 路径也说明了这一点：

1. 先设置目标 `binder_proc.is_frozen = true`，阻止新的同步 transaction。
2. 若传入 timeout，等待 `outstanding_txns` 归零。
3. 再检查仍在等待 reply 的 transaction stack。
4. 若检查失败，清回 `is_frozen` 并把失败交给 framework 处理。

`CachedAppOptimizer` 遇到 outstanding transaction 或冻结后的新 pending transaction，不会把它记录为冻结成功。它会解冻、调整重试时间并重新安排冻结；反复出现时可识别 Binder spam，避免应用靠持续发事务永久逃过 freezer。

## 5. cgroup v2 freezer：请求冻结不等于已经冻结

ACK 6.18 使用 cgroup v2 freezer。用户空间写入的是 `cgroup.freeze`：

```bash
echo 1 > cgroup.freeze   # 请求冻结本 cgroup 及其后代
echo 0 > cgroup.freeze   # 请求解冻
```

内核需要区分两个状态：

| 状态 | 含义 |
| --- | --- |
| `CGRP_FREEZE` | 用户空间已经请求冻结 |
| `CGRP_FROZEN` | 本 cgroup 的任务以及需要计入的后代已经达到 frozen 条件 |

因此，写完 `1` 以后，应观察 `cgroup.events`：

```text
frozen 1
```

只有这个状态变为 `1`，才表示冻结转换完成。一个 task 还没走到可冻结点时，`CGRP_FREEZE` 可以已经置位，而 `CGRP_FROZEN` 尚未成立。

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

task 进入冻结点后，`cgroup_enter_frozen()`：

- 设置 `current->frozen = true`。
- 增加 cgroup 的 frozen task 计数。
- 重新计算 `CGRP_FROZEN`。

解冻则清除 `JOBCTL_TRAP_FREEZE`、唤醒任务，并在 `cgroup_leave_frozen()` 更新计数。

### 5.2 性能含义

冻结不是 busy wait。task 不会在 CPU 上循环检查“能不能解冻”，所以 Java 线程、native worker、Handler 和协程都不会继续执行。

冻结也不是回收：

- 虚拟地址空间仍在。
- Java / native heap 仍在。
- fd 和 Binder 引用仍在。
- RSS/PSS 不会因为 `cgroup.freeze=1` 自动归零。

Android 14 以后，framework 可能在冻结前后触发 GC、内存压缩、匿名页换入 ZRAM 等辅助动作。这些动作可能降低物理内存压力，但要与“freezer 本身暂停 CPU”分开描述。

## 6. Binder Freezer 的两条事务路径

### 6.1 同步事务：driver 拒绝，系统终止被冻结的接收进程

目标 `binder_proc.is_frozen` 为 true 时，ACK r6 的 `binder_proc_transaction()` 对同步事务执行：

```text
proc->sync_recv = true
return BR_FROZEN_REPLY
```

平台对外的行为是：

- 同步事务不会排到 frozen 进程等待解冻。
- 调用端随后收到 `RemoteException`，已注册的 Binder death 监听也会被触发。
- 系统终止被冻结的接收进程，退出原因记录为 freezer。

Android 17 的 `CachedAppOptimizer` 同时保留两条发现路径：

- Binder 监控收到 `BR_FROZEN_REPLY` 报告后，直接按同步冻结事务处理目标 PID。
- 若即时报告能力未启用，解冻前的 `getBinderFreezeInfo()` 仍能发现 `SYNC_RECEIVED_WHILE_FROZEN` 并杀进程。

这项处理用于保护调用线程，与惩罚“服务端太慢”无关。最常见的应用错误是：

1. client 已经调用 `unbindService()`。
2. server 因失去重要 binding 退到 cached 并被冻结。
3. client 仍保存旧 `IBinder` proxy，继续发同步调用。

修复点是让 Binder 引用的生命周期与 binding 对齐：解绑后立即丢弃 proxy，不要把它当作永久可用的本地对象。

### 6.2 oneway 事务：允许入队，但不是无限队列

`oneway` transaction 命中 frozen 目标时，driver 会：

```text
proc->async_recv = true
transaction 入 async queue
return BR_TRANSACTION_PENDING_FROZEN
```

目标解冻后才会消费这些 transaction。这个设计避免同步等待，却带来两个问题：

- transaction 继续占用目标进程的 Binder buffer；空间耗尽时，系统会以 `SUBREASON_FREEZER_BINDER_ASYNC_FULL` 终止目标。
- 事件可能已经过期；解冻后一次性处理大量旧回调，还可能造成 CPU burst 和业务状态倒退。

“改成 oneway”只解决了等待语义，没有解决事件模型。更合适的策略通常是：

| 事件语义 | frozen 期间策略 |
| --- | --- |
| 瞬时采样、下一次可重新获取 | 丢弃 |
| 当前状态，以最新值为准 | 只保留最新一条 |
| 每条都是不可丢的业务记录 | 有上限地排队，并设计补偿、去重和持久化 |

如果“不可丢”意味着无限排队，这个协议仍然没有完成设计。

## 7. API 36+：使用系统提供的冻结回调队列

### 7.1 观察远端 Binder 的 frozen 状态

`IBinder.addFrozenStateChangeCallback()` 从 API 36 成为公开 API。Android 17 的回调签名是：

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

使用时要记住三个边界：

1. 只会观察 remote Binder；local Binder 与当前进程同生共冻。
2. 状态变化可能合并，只保证拿到最新状态，不能用回调次数统计 freeze 次数。
3. kernel 不支持时会抛出 `UnsupportedOperationException`，必须有降级策略。

不再需要时可调用 `removeFrozenStateChangeCallback()`。所有 Binder proxy 引用都释放后，注册也会自动移除，但显式解除通常更容易让组件生命周期清楚。

### 7.2 用 RemoteCallbackList 表达事件策略

API 36 的 `RemoteCallbackList` 支持三种 frozen callee policy：

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

可选策略与适用场景：

| policy | 行为 | 适合 |
| --- | --- | --- |
| `FROZEN_CALLEE_POLICY_DROP` | frozen 时丢弃 | 高频瞬时事件 |
| `FROZEN_CALLEE_POLICY_ENQUEUE_MOST_RECENT` | 只保留最新 callback | 音量、亮度、连接状态等状态同步 |
| `FROZEN_CALLEE_POLICY_ENQUEUE_ALL` | 按顺序排队 | 少量且每条都有意义的事件 |

`ENQUEUE_ALL` 也有队列上限。Android 17 默认最大 1000 条；达到上限后丢掉最旧 callback，Builder 可用 `setMaxQueueSize()` 显式设置。选择这个策略时，仍要写出容量、溢出和恢复方案。

没有设置策略的旧构造方式保留兼容行为：照常调用 frozen 远端。SDK 36+ 不推荐这种用法。

## 8. Freezer 对应用代码的几个隐蔽影响

### 8.1 固定频率任务可能在解冻后追赶

冻结期间，`Timer.scheduleAtFixedRate()` 或 `ScheduledThreadPoolExecutor.scheduleAtFixedRate()` 不会执行。解冻后，错过的固定频率任务可能快速连续运行。

如果业务要的是“每次完成后再隔一段时间”，使用 `scheduleWithFixedDelay()`；如果任务允许由系统调度，优先考虑 WorkManager。不要在解冻后补跑几十次已经失去意义的轮询。

### 8.2 GC 与 trim callback 也无法执行

线程全部暂停意味着进程不能主动 GC，也不能处理内存 trim callback。Android 14 起，framework 会调整通知和冻结前准备：

- 可见 Activity 退后台时尽早收到 `TRIM_MEMORY_UI_HIDDEN`。
- 进程进入 cached 后，runtime 可能先执行 GC。
- 其他整理级别不保证在冻结进程中执行。

应用不能依赖“等 `onTrimMemory()` 再释放关键资源”来保证冻结前收尾。

### 8.3 不同广播采用不同的解冻方式

Android 14 起，为减少无意义的解冻：

- context-registered broadcast 可在 cached 期间排队，解冻后再投递。
- manifest-declared broadcast 会先解冻进程再投递。

因此，trace 里看到广播延迟，不应先归因于 BroadcastQueue 卡死；要同时检查目标是否 cached/frozen 以及 receiver 的注册方式。

### 8.4 TCP socket 不能当作保活承诺

官方 freezer 文档说明：当一个应用的所有进程都 frozen 时，系统会终止该应用的活动 TCP socket，避免 keepalive 唤醒 modem。需要长期可靠传递的业务应使用 FCM、JobScheduler、WorkManager 或适合其语义的系统设施，不能依赖 cached 进程维持 socket。

## 9. 退出归因：区分公开原因与内部子原因

`ApplicationExitInfo` 从 API 30 提供，`REASON_FREEZER` 从 API 33 加入公开 SDK。普通应用可在下一次启动时查询历史退出记录：

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

Android 17 源码中的内部 subreason 包括：

| subreason | 含义 |
| --- | --- |
| `SUBREASON_FREEZER_BINDER_TRANSACTION` | frozen 期间收到同步 Binder transaction |
| `SUBREASON_FREEZER_BINDER_IOCTL` | freeze/unfreeze Binder 或查询状态失败 |
| `SUBREASON_FREEZER_BINDER_ASYNC_FULL` | frozen 期间异步 Binder buffer 接近耗尽 |

这些 subreason 与 `getSubReason()` 是隐藏 API，普通应用不能把它们当成公开诊断接口。平台或 OEM 调试可从 `dumpsys`、`system_server` 日志与源码获得更细的信息；应用侧以公开原因、description、自己的业务状态和时间线为准。

API 30–32 没有公开 `REASON_FREEZER` 常量。不要硬编码数值 `14` 跨版本猜测；这会混淆“当时平台是否记录该原因”与“当前 SDK 里的常量值”。

## 10. 用四层证据诊断，避免根据缓存状态直接下结论

### 10.1 配置与 framework 状态

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
- process state / oom_adj
- CPU_TIME 与隐式 implicit CPU_TIME capability
- pending freeze / frozen

### 10.2 shell 控制实验

Android 17 的 ActivityManager shell 提供：

```bash
adb shell cmd activity isfrozen <PROCESS_OR_PID>
adb shell cmd activity freeze <PROCESS_OR_PID>
adb shell cmd activity unfreeze <PROCESS_OR_PID>
```

`--sticky` 会让强制状态保持到进程死亡或下一次相反的 shell 操作，只应用于隔离的测试进程。实验结束必须解冻，不能拿线上关键进程做同步 Binder 探测。

### 10.3 cgroup 与 events log

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

只看到 `cgroup.freeze=1` 不够；还要确认对应 `cgroup.events` 的 `frozen=1`，并把 cgroup 路径与目标 PID 对上。

### 10.4 Perfetto 时间线

Android 17 的 `CachedAppOptimizer` 会在 ActivityManager 跟踪下写入 `Freezer` track：

```text
Freeze <process>:<pid> -1
Unfreeze <process>:<pid> <reason>
Reschedule freeze <process>:<pid> timeout=<...>, reason=<...>
```

分析顺序：

1. 用 `am_freeze` 或 `Freezer` instant event 定位冻结窗口。
2. 检查目标线程在该窗口是否还有 Running slice。
3. 若出现 `Reschedule freeze`，对齐未完成/新增待处理 outstanding/new pending Binder transaction。
4. 若进程消失，对齐 `exit-info`、Binder 调用端和 `am_kill`。
5. 若解冻后 CPU 突增，检查积压 oneway、广播和固定频率任务。

Perfetto 未采集 ActivityManager 或 sched 数据时，“没看到事件”不能证明 freezer 未运行。

## 11. 一个可复现的 Binder Freezer 实验

准备两个独立进程：

- 进程 A 提供一个同步方法和一个`oneway`方法。
- 进程 B 绑定 A，拿到 Binder proxy。

实验分三轮。

### 第一轮：正常绑定

保持 binding，调用同步方法。A 的重要性会被 B 的绑定提升，通常不应进入 cached freezer。应先证明基础 IPC 正常，再分析冻结行为。

### 第二轮：解绑后误用旧 proxy

1. B 调用 `unbindService()`，但故意保留旧 proxy。
2. 等 A 进入 cached，或在测试环境用 `cmd activity freeze`。
3. B 再发同步调用。

预期验证点包括：

- driver 返回 frozen reply。
- B 收到 `RemoteException` / Binder death。
- A 的退出记录为 `REASON_FREEZER`。

### 第三轮：oneway 积压

向 frozen 的 A 发送有限数量、带序号的`oneway`事件，然后解冻：

- 确认事件是否在解冻后按 Binder 对象内的 oneway 顺序到达。
- 观察事件是否已经过期。
- 观察解冻后的 CPU burst。

不要用无限循环耗尽 Binder 缓冲区作为默认验证手段。需要验证溢出时，应在隔离设备上设置明确上限，并保存 trace、events log 和 exit-info。

## 12. 版本边界

| 版本 | 已确认变化 | 工程含义 |
| --- | --- | --- |
| Android 11（API 30） | AOSP 支持 cached apps freezer；`ApplicationExitInfo` 公开 | 设备是否启用仍依赖 kernel 与配置 |
| Android 13（API 33） | 公开 `ApplicationExitInfo.REASON_FREEZER` | 应用可把 freezer kill 与 LMK、ANR 分开统计 |
| Android 14（API 34） | cached 后默认 10 秒冻结；生命周期事件立即解冻；动态注册广播可排队；冻结前后增加 GC/压缩等配合 | freezer 从单点开关扩展为更完整的 cached 进程策略 |
| Android 16（API 36） | 公开 `IBinder` frozen state callback；`RemoteCallbackList` 增加 frozen callee policy | callback 服务可以按“丢弃/最新/全部”表达积压语义 |
| Android 17（API 37） | 当前 `OomAdjuster` 以显式/隐式 CPU_TIME capability 统一冻结资格；Binder 监控与 freezer 重试链继续完善 | 源码判断锚定 `android-17.0.0_r1`，内核锚定 `android17-6.18-2026-06_r6` |

版本演进可以保留，但当前行为不能继续引用 Android 15/16 的旧文件路径代替 Android 17。特别是 `shouldNotFreeze()`、freezer cutoff 和 Binder 错误上报，已经出现足以影响结论的结构变化。

## 13. 常见误区

### “cached 进程一定 frozen”

不成立。设备可能没启用 freezer，进程可能仍持有 CPU capability，也可能处于 debounce、Binder 重试或实现级保护中。

### “frozen 就等于释放内存”

不成立。freezer 的直接作用是停止 CPU 执行；进程仍占地址空间和物理内存。GC、compaction、ZRAM writeback 与 LMK 是另外的动作。

### “同步调用只会等到对方解冻”

不成立。Android 会拒绝发往冻结远端的同步 Binder transaction，并终止被冻结的接收进程，避免调用线程无限等待。

### “oneway 对 frozen 进程绝对安全”

不成立。它会积压、占用 Binder buffer，解冻后还可能集中处理过期事件；buffer 压力过高时目标进程会被终止。

### “观察 frozen callback 就能统计冻结次数”

不成立。状态事件允许合并，API 只承诺最新状态。

### “OEM 的‘冻结’都等于 AOSP cached apps freezer”

不成立。必须用 ActivityManager 事件、cgroup 状态、Binder freezer reason 和厂商实现证据区分。

## 14. 复核清单

1. 确认设备的 `use_freezer`、kernel 支持和 cgroup v2 布局。
2. 同时记录 proc state、oom_adj、CPU_TIME capability 与 freezer cutoff。
3. 区分 pending freeze、请求冻结和 `cgroup.events frozen=1`。
4. 检查 Binder freeze 是否先于 cgroup freeze。
5. 同步调用命中 frozen 目标时，找到调用端、旧 proxy 生命周期和退出原因。
6. oneway 回调写清丢弃、只留最新、全量排队及容量上限。
7. API 36+ 优先使用 `IBinder` frozen callback 或 `RemoteCallbackList` policy。
8. 检查固定频率任务、广播与 oneway 是否在解冻后形成 burst。
9. 不把冻结本身写成内存回收；单独验证 GC、compaction、ZRAM 和 LMK。
10. 用 Perfetto、events log、cgroup、exit-info 四条时间线交叉证明结论。
11. 区分公开 `REASON_FREEZER` 与 hidden subreason。
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
