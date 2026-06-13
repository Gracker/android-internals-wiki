---
title: "Binder Freezer 与缓存进程冻结性能"
chapter: "1.18"
section: "1.18"
status: ready-for-review
drafted_date: "2026-05-15"
applicable_versions: "Android 11 QPR3 - Android 17 (API 37)"
last_verified: "2026-06-14"
last_verified_against: "AOSP android-15.0.0_r1 / android-16.0.0_r1 frameworks/base + Android common kernel android17-6.18-2026-04_r1 Binder/freezer + Linux cgroup docs + AOSP docs 2026-04; platform android-17 tag not public"
confidence: medium
tags: [binder, process-freezer, cached-apps, cgroup, performance]
related_chapters: ["1.3", "1.4", "5.8", "11.2", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构/官方文档"
pipeline_stage: "task9_pending"
task6_state: "reviewed"
task6_result: pass-light-edit
task6_reviewed_date: "2026-06-14"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-27"
last_task6_at: "2026-06-14T01:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-13-18-review.md"
task6_review_notes: "2026-06-14 Task6 round 3 re-review: pass-light-edit. Task9 auto-fixed kernel source anchors (Linux main→Android common kernel android17-6.18-2026-04_r1). L1: clean (no banned words). L2: clean (good narrative, proper structure, clear tables). All 6 anchors covered. No B-class issues. Writing quality high. Score: structure 5/5, wording 5/5, consistency 5/5, verification 4/5, metadata 5/5."
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
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/cached-apps-freezer"
  - type: official
    path: "https://source.android.com/docs/core/architecture/ipc/binder-freezer"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://docs.kernel.org/admin-guide/cgroup-v2.html"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: aosp
    path: "core/java/android/app/ApplicationExitInfo.java"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-04_r1/drivers/android/binder.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-04_r1/include/uapi/linux/android/binder.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-04_r1/kernel/cgroup/freezer.c"
  - type: obsidian
    path: "../DeepResearch/2026-05-08-binder-freezer-driver-cgroup-v2-coordination-mechanism.md"
task9_review_notes: "2026-06-14 Task9 deep review：AUTO-FIX Binder/cgroup freezer 内核源码锚点，从 Linux main/master 切到 Android common kernel android17-6.18-2026-04_r1；framework android-17 tag 仍不可取，回到 Task6 复审。"
p0: 0
p1: 0
p2: 0
last_task9_audit: "2026-06-13"
last_task9_autofix_at: "2026-06-14"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
---

# 1.18 Binder Freezer 与缓存进程冻结性能

<!-- outline-start -->
## 要点

### 🔹 缓存进程冻结解决的问题
说明 Android 为什么在 LMK 之外引入 cached app freezer：降低 cached 进程空转 CPU、减少后台异常唤醒，并保持比杀进程更低的恢复成本。

### 🔹 CachedAppOptimizer 的冻结入口
梳理 `OomAdjuster`、`FREEZER_CUTOFF_ADJ` 与 `CachedAppOptimizer` 的协作边界，区分 oom_adj 计算、冻结资格判断和实际冻结执行。

### 🔹 cgroup v2 freezer 状态机
解释 `cgroup.freeze`、`CGRP_FREEZE`、`CGRP_FROZEN`、`JOBCTL_TRAP_FREEZE` 与任务调度状态之间的关系，说明冻结态线程为什么不消耗 CPU。

### 🔹 Binder Freezer 的跨进程调用边界
整理 Binder 驱动如何感知 frozen 目标进程、同步/异步事务在冻结态下的差异，以及哪些调用会形成等待、失败或延迟投递。

### 🔹 Perfetto 与线上指标中的可观测特征
总结冻结进程在 Perfetto sched 轨道、CPU 频率、Binder latency、ANR 归因和 ApplicationExitInfo 中的可观测信号。

### 🔹 版本演进与调试入口
按 Android 12-17 梳理 cached app freezer、cgroup v2 freezer、Binder freezer API 与退出原因枚举的版本边界，给出 `dumpsys activity processes`、`cmd activity`、`/sys/fs/cgroup` 的排查入口。

## 扩展

### 🔸 前台服务、广播与 JobScheduler 的冻结豁免边界
后续可补齐不同组件状态对冻结资格的影响，避免把后台限制、cached freezer 和 Doze 混成一类机制。

### 🔸 厂商后台管控与 AOSP freezer 的差异
后续可收集 OEM 实机 trace，对比标准 AOSP freezer 与厂商自研冻结/墓碑/保活策略的差异。

### 🔸 冻结态 Binder 等待与 ANR 风险案例
后续可补一个最小复现实验：调用 cached 目标进程 Binder 服务，观察等待时间、解冻时机和 trace 证据。

<!-- outline-end -->

## 冻结保留进程状态，降低恢复成本

Cached app freezer 处理的是一类很具体的浪费：进程已经退到 cached 状态，对用户不可见，却还通过定时器、线程循环、异步回调或 Binder 事务消耗 CPU。LMK 可以回收内存，但杀进程会丢掉运行时状态；下次回到前台时，应用要重新启动、重新建对象、重新加载缓存。

冻结给系统增加了一个中间态：进程地址空间和 Java/Native 堆仍在，线程暂停调度，不再拿 CPU 时间。AOSP 文档把它描述为“将 cached 进程迁移到 frozen cgroup”，目标是降低 active cached apps 带来的 active/idle CPU 消耗。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

这个机制不能等同于后台限制、Doze 或 LMK。

| 机制 | 触发对象 | 系统动作 | 保留内容 | 性能收益 | 风险 |
| --- | --- | --- | --- | --- | --- |
| Cached app freezer | cached 进程 | 暂停进程线程调度 | 进程、堆、文件描述符、Binder 状态 | 减少 cached 进程 CPU 空转 | 冻结期间 Binder 回调堆积或同步调用触发 kill |
| LMK/lmkd | 低内存场景下的低优先级进程 | 杀进程释放内存 | 无 | 释放 RSS/PSS 压力 | 下次启动成本高 |
| Doze / App Standby | 设备空闲或应用待机 | 限制网络、Job、Alarm 等后台能力 | 进程不一定暂停 | 降低后台唤醒和网络成本 | 任务延迟执行 |
| 前台服务限制 | FGS / 后台启动场景 | 限制组件能力或超时 | 依组件状态变化 | 控制长期后台执行 | 误用会触发异常或 ANR |

1.3 节已经解释进程优先级和 cached 状态，1.4 节负责 Binder IPC 的基本语义。这里关心的是两者交叉后出现的新边界：一个 cached 进程被冻结后，系统如何避免它继续消耗 CPU，以及 Binder 事务在冻结状态下如何处理。

## 冻结入口：OomAdjuster 决定资格，CachedAppOptimizer 执行动作

AOSP 把冻结资格放在 oom_adj 计算结果之后处理。Android 15 的 `ProcessList.FREEZER_CUTOFF_ADJ` 等于 `CACHED_APP_MIN_ADJ`；Android 16 改为 `ActivityManagerConstants.FREEZER_CUTOFF_ADJ`，默认值仍以 `CACHED_APP_MIN_ADJ` 为基线，但 `prototypeAggressiveFreezing` 和 DeviceConfig `freezer_cutoff_adj` 可以改变阈值。进程的 `curAdj` 达到当前阈值，并且没有被标记为 freezer exempt，`OomAdjuster` 才会把它交给 `CachedAppOptimizer`。[已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java][已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java][已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

关键路径可以概括为三段：

```text
OomAdjuster.getFreezePolicy(app)
  ├─ app 有 PROCESS_CAPABILITY_CPU_TIME 或 opt.shouldNotFreeze() → 不冻结
  ├─ app.mOptRecord.isFreezeExempt() → 不冻结
  └─ app.mState.getCurAdj() >= FREEZER_CUTOFF_ADJ → 可冻结

OomAdjuster.updateAppFreezeStateLSP(app)
  ├─ getFreezePolicy(app) = true  → CachedAppOptimizer.freezeAppAsyncLSP(app)
  └─ getFreezePolicy(app) = false → CachedAppOptimizer.unfreezeAppLSP(app, reason)

CachedAppOptimizer.freezeProcess(proc)
  ├─ mFreezer.freezeBinder(pid, true, timeout)
  ├─ mFreezer.setProcessFrozen(pid, uid, true)
  ├─ opt.setFrozen(true)
  └─ EventLogTags.AM_FREEZE / statsd APP_FREEZE_CHANGED
```

这段顺序有三个工程含义。

- oom_adj 仍是入口条件。Freezer 不重新定义进程重要性，它沿用 ActivityManager 计算出的 cached 边界；前台、可见、perceptible、service 等状态变化会先改变 adj，再影响冻结资格。
- capability 和 `shouldNotFreeze()` 是 adj 之外的保护链。前台服务、绑定重要进程、正在执行关键交互或其他仍应获得 CPU 时间的进程，可能先通过 `PROCESS_CAPABILITY_CPU_TIME` 或 `ProcessCachedOptimizerRecord.shouldNotFreeze()` 被排除，不必等到 adj 变化后才避免冻结。
- Binder 先于进程冻结。`CachedAppOptimizer.freezeProcess()` 在 `setProcessFrozen()` 前调用 `freezeBinder(pid, true, ...)`，目的是先处理 Binder 接口和未完成事务，再让线程进入冻结态。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

`CachedAppOptimizer` 还给冻结安排了 debounce。进程刚进入 cached 状态时，系统不会立刻冻结；默认配置会延迟一段时间，避免 Activity 刚退后台、Service 刚结束、Binder 事务还在收尾时反复 freeze/unfreeze。Android 16 源码里的 `DEFAULT_FREEZER_DEBOUNCE_TIMEOUT = 10_000L` 是默认值，设备侧仍可能通过 DeviceConfig 或厂商配置调整。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

## cgroup v2 freezer：线程停止调度，进程仍然存在

Linux cgroup v2 的 freezer 接口是 `cgroup.freeze`。对非 root cgroup 写入 `1` 会冻结该 cgroup 及其子 cgroup，写入 `0` 会解冻；冻结完成后，`cgroup.events` 里的 `frozen` 字段变为 `1`。内核文档明确说，frozen cgroup 中的进程会停止运行，直到显式解冻。[已验证: 官方文档, docs.kernel.org/admin-guide/cgroup-v2.html]

内核状态机由几个标志和计数组成：

```text
write cgroup.freeze = 1
  └─ cgroup_freeze(cgrp, true)
       ├─ set_bit(CGRP_FREEZE, cgrp->flags)
       ├─ cgroup_do_freeze() 遍历 task
       │    └─ cgroup_freeze_task(task, true)
       │         └─ task->jobctl |= JOBCTL_TRAP_FREEZE
       └─ cgroup_update_frozen()
            └─ 所有任务进入 frozen 计数后设置 CGRP_FROZEN
```

`JOBCTL_TRAP_FREEZE` 是任务进入冻结检查点的信号。任务进入 `cgroup_enter_frozen()` 后，内核设置 `current->frozen = true`，并增加 cgroup 的 frozen task 计数；解冻走 `cgroup_leave_frozen()`，清计数并唤醒任务。[已验证: Android common kernel android17-6.18-2026-04_r1, kernel/cgroup/freezer.c]

性能判断要抓住两点：

- 冻结态不是 busy wait。线程不在 CPU 上轮询，也不会继续执行 Java/Kotlin 协程、Handler 消息或 native worker 循环。
- 冻结态不释放内存。进程的 RSS/PSS 还在，文件描述符和 Binder 引用也还在；内存压力上来时，LMK 仍可能选择这些 cached 进程回收。

到这里，freezer 的收益范围就很清楚了：它主要节省 CPU 和唤醒成本，不是内存优化工具。内存章节讨论 PSS/RSS 时，不能把“冻结后 CPU 降低”误写成“冻结后内存回收”。

## Binder Freezer：同步事务拒绝，异步事务缓存

Binder 是冻结机制里最容易出错的边界。一个进程被冻结后，线程不能处理事务；如果其他进程继续向它发 Binder 调用，系统必须决定调用端等不等、目标端杀不杀、异步消息存不存。

AOSP 文档给出了平台口径：

- 同步 Binder 事务发给 frozen 远端进程时，系统会杀掉远端进程，避免调用线程无限等待，进而引发调用端线程饥饿或死锁。
- 异步 `oneway` 事务发给 frozen 远端进程时，事务会缓存到远端解冻后再处理；如果异步缓冲区溢出，接收进程可能被杀；缓存事务也可能在解冻时变成过期事件。[已验证: 官方文档, source.android.com/docs/core/architecture/ipc/binder-freezer]

内核 Binder 协议也能对上这两个分支。`include/uapi/linux/android/binder.h` 中定义了：

- `BR_FROZEN_REPLY`：上一次同步事务的目标进程或线程处于 frozen 状态。
- `BR_TRANSACTION_PENDING_FROZEN`：上一次异步事务的目标进程处于 frozen 状态，事务已经排队。

`binder_proc_transaction()` 的处理逻辑是：发现 `proc->is_frozen` 后记录 `sync_recv` / `async_recv`；同步事务直接返回 `BR_FROZEN_REPLY`；异步事务可以进入队列，并返回 `BR_TRANSACTION_PENDING_FROZEN`。[已验证: Android common kernel android17-6.18-2026-04_r1, include/uapi/linux/android/binder.h][已验证: Android common kernel android17-6.18-2026-04_r1, drivers/android/binder.c]

```text
目标进程 frozen
  ├─ 同步事务：记录 sync_recv → 返回 BR_FROZEN_REPLY → framework 侧按 freezer 原因杀掉目标进程
  └─ oneway 事务：记录 async_recv → 事务进入 async 队列 → 解冻后处理；缓冲区不足时 kill 目标进程
```

这条规则对应用架构有直接约束：不要把“通知 cached 进程一声”写成同步 Binder 调用。对回调、监听器、跨进程缓存刷新这类场景，优先使用可暂停的异步分发，并在远端 frozen 时停止发送或合并事件。Android 16 的 flagged API 可用时，可以用 `IBinder.addFrozenStateChangeCallback` 跟踪远端 frozen/unfrozen 状态；实现上要捕获 `UnsupportedOperationException`，低版本或 flag 不可用时退回生命周期状态、注册/退订策略、事件合并和 Binder death 等降级方案。[已验证: 官方文档, source.android.com/docs/core/architecture/ipc/binder-freezer][已验证: AOSP android-16.0.0_r1, core/java/android/os/IBinder.java]

## 失败归因：ApplicationExitInfo 能看到 freezer kill

从线上稳定性看，freezer kill 不应该被混进普通 OOM、ANR 或用户强杀。`ApplicationExitInfo.REASON_FREEZER = 14` 的公开说明是“Application process was killed by App Freezer”，示例场景是 frozen 状态下收到同步 Binder 事务；但这个字段不是 Android 11/12 的通用口径，线上归因要先按 API 版本分段。[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationExitInfo][已验证: AOSP android-16.0.0_r1, core/java/android/app/ApplicationExitInfo.java]

Android 16 源码还定义了几个内部 subreason，应用侧可见性受 API、权限和系统实现影响：

| reason / subreason | 场景 | 排查方向 |
| --- | --- | --- |
| API 30-32 | 无公开 `REASON_FREEZER` | 退回 `REASON_OTHER`、description、system_server 日志或内部 subreason 线索 |
| API 33+ `REASON_FREEZER` | 进程被 App Freezer 杀掉 | 先查是否 frozen 状态下收到 Binder 事务，避免误归因为低内存 |
| API 34+ `REASON_PACKAGE_STATE_CHANGE` / `REASON_PACKAGE_UPDATED` | 包状态变化或更新导致退出 | 不和 freezer kill 混写，按包管理事件单独归因 |
| `SUBREASON_FREEZER_BINDER_TRANSACTION` | frozen 期间收到同步 Binder 事务 | 查调用端、接口类型、是否可改成 oneway 或延后分发 |
| `SUBREASON_FREEZER_BINDER_IOCTL` | freeze/unfreeze Binder 或查询 frozen info 失败 | 查内核 Binder 状态、pid 生命周期、AMS 日志 |
| API 35+ `SUBREASON_FREEZER_BINDER_ASYNC_FULL` | frozen 期间异步 Binder 缓冲区接近耗尽 | 查 callback 风暴、监听器未退订、事件是否可合并 |

`CachedAppOptimizer` 里能看到这些归因的使用：解冻前查询 `getBinderFreezeInfo(pid)`，如果发现 `SYNC_RECEIVED_WHILE_FROZEN`，会用 `REASON_FREEZER` + `SUBREASON_FREEZER_BINDER_TRANSACTION` 杀进程；异步缓冲区不足时，走 `SUBREASON_FREEZER_BINDER_ASYNC_FULL`。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

26.9 节负责 `ApplicationExitInfo` 的完整归因模型。这里保留 freezer 相关的最小判断：看到 `REASON_FREEZER` 时，不要按“系统随机杀后台”处理；它通常指向 frozen 状态下仍有跨进程交互。

## Perfetto、日志和命令里的观察点

冻结态在 trace 里有三个层次的信号。

| 层次 | 观察点 | 正常 frozen 形态 | 异常信号 |
| --- | --- | --- | --- |
| ActivityManager | `Freezer` track / `am_freeze` / `am_unfreeze` | cached 进程出现 Freeze / Unfreeze instant event | 短时间反复 freeze/unfreeze，或因为 Binder 事务重排 freeze |
| sched | 目标进程线程轨道 | frozen 窗口内线程没有 Running 切片 | frozen 后仍有频繁 Running，说明未进入 freezer 或被频繁解冻 |
| Binder | 调用端线程、binder transaction latency | oneway 事务可能排队到解冻后处理 | 同步调用命中 frozen 目标，目标进程出现 freezer kill |

`CachedAppOptimizer.traceAppFreeze()` 会在 `Trace.TRACE_TAG_ACTIVITY_MANAGER` 下写入 `Freezer` track，事件名模板是 `Freeze <processName>:<pid> <reason>` 或 `Unfreeze <processName>:<pid> <reason>`；重排冻结时还会出现 `Reschedule freeze <processName>:<pid> timeout=..., reason=...`。这个 reschedule 事件常见于 Binder outstanding transaction 或新 pending transaction 让冻结延后，排查 freeze/unfreeze 抖动时要和 Binder 事务时间线一起看。成功冻结后还会写 `EventLogTags.AM_FREEZE`，解冻时写 `AM_UNFREEZE`。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

排查时可以按这个顺序拿证据：

```bash
# 查看进程状态、adj、cached/freezer 相关信息
adb shell dumpsys activity processes

# 查看 cgroup v2 freezer 状态；不同设备路径会有差异
adb shell find /sys/fs/cgroup -name cgroup.freeze -o -name cgroup.events

# 观察 ActivityManager freezer 事件
adb logcat -b events | grep -E 'am_freeze|am_unfreeze'

# 查看最近进程退出归因，重点找 REASON_FREEZER
adb shell dumpsys activity exit-info <package-name>
```

这组命令不保证所有量产设备都有同样输出。`/sys/fs/cgroup` 层级取决于设备 cgroup 配置，`dumpsys activity exit-info` 的可读字段也随 Android 版本变化。更稳的做法是同时保存 Perfetto trace、events log、`dumpsys activity processes` 和应用侧 `ApplicationExitInfo` 采样，四者时间戳对齐后再下结论。

## 版本边界：Android 11 QPR3 起有 cached app freezer，后续重点在 Binder 交互

AOSP 文档写明 Android 11 QPR3 或更高版本支持 cached apps freezer；设备还需要兼容内核，可通过系统配置或开发者选项启用。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

| 版本 | 可确认变化 | 写作边界 |
| --- | --- | --- |
| Android 11 QPR3 | 支持 cached apps freezer，框架通过 frozen cgroup 暂停 cached 进程 | 设备是否启用取决于 kernel / DeviceConfig / 开发者选项 |
| Android 12 | freezer 进入更多设备实现，Binder frozen 状态开始影响跨进程调用设计 | 无公开 `REASON_FREEZER` 时，要保留日志、description 和内部 subreason 证据 |
| Android 13 | `ApplicationExitInfo.REASON_FREEZER` 可用于线上归因 | 不把所有厂商后台冻结都归为 AOSP freezer |
| Android 14/15 | 包状态 / 更新原因与 freezer subreason 继续补齐 | `SUBREASON_FREEZER_BINDER_ASYNC_FULL` 属于 Android 15+ 边界；subreason 多为 hidden/internal，应用侧能拿到的字段受 API 和权限限制 |
| Android 16 | `FREEZER_CUTOFF_ADJ` 由 `ActivityManagerConstants` / DeviceConfig 管理，默认仍以 cached 边界为基线；`CachedAppOptimizer`、Binder freezer、cgroup v2 freezer 主路径与本节一致 | 以 `android-16.0.0_r1` 为源码锚点；不要把 AOSP main 直接当作 Android 17 结论 |
| Android 17 | framework `android-17.0.0_r1` tag 本轮仍未取到；Binder/cgroup 内核锚点已核到 Android common kernel `android17-6.18-2026-04_r1` | framework 结论只使用 Android 16 及以下可验证源码；内核侧只引用 Android common kernel tag，不使用 Linux main/master 作为 Android 17 结论 |

本节没有把 freezer 写成万能后台治理方案。它解决 cached 进程 CPU 空转，但会暴露跨进程协议设计问题：冻结期间还在同步调用远端，就会把后台节能问题变成稳定性问题；冻结期间不断发 oneway 回调，就会把 CPU 问题变成异步缓冲区压力和过期事件问题。

## 扩展：组件豁免、厂商差异和复现实验

### 前台服务、广播与 JobScheduler 的冻结豁免边界

AOSP 冻结资格从 oom_adj 进入，组件状态会通过 adj、capability 和 `shouldNotFreeze()` 间接影响 freezer。前台 Service、可见 Activity、perceptible 进程、正在执行的关键系统交互通常不会进入 cached 冻结窗口。排查时按这张表拆开看：

| 来源状态 | 进入 freezer 判断前的影响 | 排查边界 |
| --- | --- | --- |
| 前台 / 可见 / perceptible 组件 | 影响 `curAdj`，多数情况下不会达到 `FREEZER_CUTOFF_ADJ` | 先查 oom_adj 计算，不要直接查 cgroup |
| 仍需 CPU 时间的关键交互 | 可能带 `PROCESS_CAPABILITY_CPU_TIME` | 即使 adj 接近 cached，也可能被 capability 保护 |
| 进程优化记录保护 | `ProcessCachedOptimizerRecord.shouldNotFreeze()` 返回 true | 查 pending freeze、执行中事务、短时间状态切换 |
| freezer exempt | `isFreezeExempt()` 返回 true | 查系统组件、设备配置或特殊豁免 |

### 厂商后台管控与 AOSP freezer 的差异

很多 OEM 也有“冻结”“墓碑”“智能后台”策略，但它们不一定走 AOSP cached app freezer。判断时不要只看现象：进程不跑 CPU，可能来自 cgroup freezer，也可能来自厂商守护进程、调度器策略或权限管控。可验证证据应包含 `am_freeze` / `AM_FREEZE`、cgroup.freeze 状态、Binder freezer reason 和厂商日志。[待补充]

### 冻结态 Binder 等待与 ANR 风险案例

最小复现实验可以设计成两个进程：进程 A 提供 Binder 服务，退后台进入 cached；进程 B 分别发同步调用和 oneway 回调。观察 A 是否进入 frozen、B 的调用耗时、A 的 `ApplicationExitInfo`、Perfetto 中 `Freezer` track 和 Binder 事务。没有实机 trace 前，本节不写固定耗时或稳定复现结论。[待补充]

## 参考资料

- [官方文档: Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [官方文档: Handle cached and frozen apps](https://source.android.com/docs/core/architecture/ipc/binder-freezer)
- [官方 API: ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Linux Kernel Documentation: Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [AOSP android-16.0.0_r1: CachedAppOptimizer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP android-16.0.0_r1: OomAdjuster.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/java/com/android/server/am/OomAdjuster.java)
- [AOSP android-16.0.0_r1: ActivityManagerConstants.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java)
- [AOSP android-15.0.0_r1: ProcessList.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [Android common kernel android17-6.18-2026-04_r1: Binder driver](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-04_r1/drivers/android/binder.c)
- [Android common kernel android17-6.18-2026-04_r1: Binder UAPI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-04_r1/include/uapi/linux/android/binder.h)
- [Android common kernel android17-6.18-2026-04_r1: cgroup freezer](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-04_r1/kernel/cgroup/freezer.c)
- [DeepResearch: Cached App Freezer 机制与 GC 触发路径] — 厘清 Freezer/LMK/GC 三机制独立决策关系，补充冻结解冻触发链与 Binder 协作细节
