---
title: "进程模型与生命周期管理"
chapter: "1.3"
section: "1.3"
drafted_date: "2026-05-13"
drafted_by: openclaw-task2a
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; ACK android17-6.18-2026-06_r6; Android Developers; source.android.com"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/guide/components/activities/process-lifecycle"
  - type: official
    path: "https://developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/application-element"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/manifest-element"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "https://source.android.com/docs/core/perf/mmd"
  - type: official
    path: "https://source.android.com/docs/core/perf/cached-apps-freezer"
  - type: official
    path: "https://source.android.com/docs/core/architecture/ipc/binder-freezer"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Process.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/Constants.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/ProcessStateController.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/memory/ZramMaintenance.java @ android-17.0.0_r1"
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "system/memory/mmd/src/service.rs @ android-17.0.0_r1"
  - type: aosp
    path: "system/core/libprocessgroup/profiles/task_profiles.json @ android-17.0.0_r1"
  - type: kernel
    path: "kernel/cgroup/freezer.c @ android17-6.18-2026-06_r6"
  - type: kernel
    path: "kernel/sched/psi.c @ android17-6.18-2026-06_r6"
tags:
  - process
  - ams
  - oom_adj
  - lmkd
  - mmd
  - zygote
  - process-lifecycle
  - binder
  - cgroup
related_chapters:
  - "1.1"
  - "1.2"
  - "1.4"
  - "1.5"
  - "4.4"
  - "5.1"
  - "5.8"
task2b_state: fixed
task2b_result: fixed
task6_state: "reviewed"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-13"
task6_result: "pass-light-edit"
task6_reviewed_date: "2026-06-07"
review_round: 2
task6_review_notes: "2026-05-13 task6 review: L1/L2 通过；本轮仅补齐 review 元数据，无新增 L3/L4 回炉项。 | 2026-06-07 task6 revisiting review: L1/L2 通过（代码块标签、禁用词、高频词均合规）；无 B 类大问题；自动晋升 finalized（task9 pass + queue 无 pending）。"
status: "finalized"
pipeline_stage: "ready-to-publish"
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-07"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-07T08:20:00+08:00"
last_task9_autofix_at: "2026-06-07"
last_task9_audit: "2026-06-07"
last_task6_audit: "2026-07-08"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-07
task6_reviewed_by: "openclaw-task6"
last_task6_at: "2026-06-07T12:12:00+08:00"
---

# 进程模型与生命周期管理

Android 应用可以创建线程，却不能自行决定进程能活多久。系统根据进程中正在运行的组件、组件与其他进程的依赖关系、用户能否感知这些工作以及整机内存压力，持续计算进程重要性。内存紧张时，重要性较低的进程先成为回收候选。

这个模型解释了三类常见问题：

- 进程不存在时，启动组件要先经过 Zygote 创建进程、应用绑定和组件调度，冷启动路径因此更长。
- 缓存进程能缩短应用切回时间，但会占用内存；系统必须在切回速度与前台可用内存之间取舍。
- 一个线程即使还在运行，只要没有受系统认可的活跃组件承载，所在进程仍可能降为 cached 并被终止。

分析这类问题时，要把“应用代码是否还有工作”“AMS 认为进程是什么状态”“内核是否允许它获得 CPU”“低内存策略是否把它列为候选”分开看。

## 应用进程从哪里来

默认情况下，每个应用使用自己的 Linux UID 和进程，Activity、Service、BroadcastReceiver、ContentProvider 等组件运行在默认进程中。进程刚启动时只有主线程；组件生命周期回调通常由主线程分发，但这不表示组件的所有方法都只会在主线程执行。例如，远程 Binder 方法和来自其他进程的 ContentProvider 调用可以落在 Binder 线程池，相关实现仍要满足线程安全要求。

Manifest 可以改变进程边界：

- `<application android:process="...">` 为应用组件指定默认进程。
- `<activity>`、`<service>`、`<receiver>`、`<provider>` 可以覆盖该值。
- 以冒号开头的名字，例如 `:player`，表示应用私有进程，实际名字会带上包名前缀。
- 不以冒号开头的全局进程名只在共享 Linux UID 且签名匹配时才可能跨应用共用。`android:sharedUserId` 从 API 29 起已经废弃，新应用不应依赖这种设计。

在 Android 17 中，`android.os.Process.start()` 仍把 UID、GID、ABI、targetSdk、数据目录和运行时参数交给 `ZygoteProcess.start()`。实际的 fork 发生在 Zygote 一侧；`Process.start()` 是 framework 的请求入口，不是直接调用 Linux `fork()` 的位置。应用进程创建后再经 Binder 向 `system_server` 回连，AMS 才能继续 `bindApplication` 和组件调度。

多进程因此不是免费的线程隔离。一个 `android:process=":remote"` 至少增加一套进程地址空间、ART 运行时状态、Java 与 native 堆、线程栈、主线程消息循环和 `Application` 初始化；原来的进程内调用也可能变成 Binder IPC。

适合拆进程的场景通常有明确的故障或内存边界，例如：

- 不可信插件或需要隔离权限面的服务；
- 崩溃后不应带倒主界面的独立模块；
- 生命周期清楚、结束后希望整进程释放大块 native 或图形内存的模块；
- 系统明确提供隔离进程模型的组件。

如果两个模块高频同步调用、共享大量可变状态，拆进程往往只会增加序列化、Binder 线程池、锁和状态同步成本。

## 组件状态决定进程重要性

开发者文档把应用进程概括为 foreground、visible、service、cached 四类。AOSP 为执行策略使用更细的数值区间。Android 17 的常量已经从旧版 `ProcessList` 拆到 `com.android.server.am.psc.Constants`：

| 典型状态 | Android 17 基准 `adj` | 含义 |
| --- | ---: | --- |
| top / foreground | `FOREGROUND_APP_ADJ = 0` | 用户正在交互，或进程正在执行 receiver、service 回调等受保护工作 |
| visible | `VISIBLE_APP_ADJ = 100` 起 | 内容仍可见；部分策略可以在可见区间内进一步分层 |
| perceptible | `PERCEPTIBLE_APP_ADJ = 200` 起 | 用户能感知中断，例如受认可的媒体播放或前台服务场景 |
| service | `SERVICE_ADJ = 500` | 持有 started service，但没有更重要组件 |
| home | `HOME_APP_ADJ = 600` | 当前桌面进程 |
| previous | `PREVIOUS_APP_ADJ = 700` 起 | 最近离开的应用；Android 17 可按开关对该区间分层 |
| service B | `SERVICE_B_ADJ = 800` | 重要性进一步降低的老化服务 |
| cached | `CACHED_APP_MIN_ADJ = 900` 到 `CACHED_APP_MAX_ADJ = 999` | 当前没有用户可感知工作，可按系统需要回收 |

这些数值适合解释 AOSP 的相对顺序，不能当成所有设备不变的“保活等级”。Android 17 中可见、previous 和 cached 区间都存在更细的排序策略与 feature flag；厂商还可以调整进程上限、freezer cutoff 和 `lmkd` 参数。

分类有三条关键规则。

第一，进程按其中最重要的活跃组件定级。一个进程同时拥有 visible Activity 和 started service 时，不会因为 service 较弱就降到 service 级别。

第二，重要性会沿依赖关系传播。高优先级进程绑定另一个进程的 Service，或正在使用另一个进程的 ContentProvider 时，被依赖进程需要获得足以完成请求的保护。绑定 flag、依赖类型和能力传播规则都会影响最终结果，不能只看服务端自身组件。

第三，组件回调结束就可能撤销保护。`BroadcastReceiver.onReceive()` 返回后，receiver 不再被视为活跃；此时让裸线程继续工作，不能保证进程还会存活。需要可靠完成的任务应交给 JobScheduler、WorkManager 或其他与系统调度约束相匹配的接口。

从 Android 13 开始，cached 进程在重新进入活跃生命周期状态前，可能只得到有限的执行时间，甚至得不到执行时间。应用必须把 cached 当作“可以立即停止”的状态，而不是低优先级后台运行模式。

## Android 17 如何计算进程状态

Android 17 的实现不再适合用“AMS 调用一个旧版 `OomAdjuster.java`”一句话概括。进程状态相关实现已经进入 `com.android.server.am.psc`：

1. Activity、Service、Broadcast 等管理模块把组件和依赖变化交给 `ProcessStateController`。
2. `ProcessStateController` 提交待处理事件，并触发局部或全量 OOM adjustment 更新。
3. `OomAdjusterImpl.computeOomAdjLSP()` 从最重要条件开始计算 `adj`、`procState`、`schedGroup` 和 capability。
4. 依赖遍历继续修正服务端、Provider 端及其他可达进程的结果。
5. 计算值提交后，回调更新调度组、freezer、统计信息，并把 OOM 优先级同步给 `lmkd`。

下面的 Android 17 源码片段显示，top app、正在接收广播和正在执行 Service 回调会得到不同的 `procState` 与调度组；它们只是初始规则，后续还会处理 Activity、前台服务和进程依赖。

```java
// frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java
// @ android-17.0.0_r1
if (app == topApp && PROCESS_STATE_CUR_TOP == PROCESS_STATE_TOP) {
    adj = FOREGROUND_APP_ADJ;
    schedGroup = useTopSchedGroupForTopProcess()
            ? SCHED_GROUP_TOP_APP : SCHED_GROUP_DEFAULT;
    procState = PROCESS_STATE_TOP;
} else if (isReceivingBroadcast(app)) {
    adj = FOREGROUND_APP_ADJ;
    schedGroup = app.getReceivers().getBroadcastReceiverSchedGroup();
    procState = ActivityManager.PROCESS_STATE_RECEIVER;
} else if (psr.hasExecutingServices()) {
    adj = FOREGROUND_APP_ADJ;
    schedGroup = psr.isExecServicesFg()
            ? SCHED_GROUP_DEFAULT : SCHED_GROUP_BACKGROUND;
    procState = PROCESS_STATE_SERVICE;
}
```

四组结果负责不同职责：

- `adj` 是 Android 的进程回收优先级，提交后与 `/proc/<pid>/oom_score_adj`、`lmkd` 进程表相关。
- `procState` 描述更细的运行状态，供后台限制、统计、内存采样和其他策略使用。
- `schedGroup` 决定进程应进入哪类 CPU 调度资源组。
- capability 描述进程当前可以继承或使用的特定能力。Android 17 的 freezer 策略会直接检查 CPU time capability。

所以，“`oom_score_adj` 较低”不能推出“它一定在 top-app cpuset”，“有前台服务”也不能推出“它等同于顶层 Activity”。排查时必须同时记录这几组值。

## `lmkd` 决定何时杀、杀谁

Android 使用 userspace `lmkd` 监控内存压力。Android 10 及以上支持 PSI（Pressure Stall Information）模式：内核统计任务因 CPU、内存或 I/O 资源争用而停顿的时间，`lmkd` 订阅内存压力阈值。当前官方配置仍以 `ro.lmk.use_psi=true` 为默认值，但前提是设备内核启用 PSI。

Android 17 的 platform 与 kernel 锚点能对上这条链：

- `ProcessList.setOomAdj()` 向 `lmkd` 发送 `LMK_PROCPRIO`，包含 pid、uid、adj、进程类型等字段。
- `system/memory/lmkd/lmkd.cpp` 保存进程的 `oomadj`，读取 PSI、swap、thrashing、workingset refault 等信号后选择合格目标。
- ACK `android17-6.18-2026-06_r6` 的 `kernel/sched/psi.c` 实现 PSI trigger 的创建与轮询。

下面这段代码只是在同步优先级，不表示进程会立即被杀：

```java
// frameworks/base/services/core/java/com/android/server/am/ProcessList.java
// @ android-17.0.0_r1
ByteBuffer buf = ByteBuffer.allocate(4 * 6);
buf.putInt(LMK_PROCPRIO);
buf.putInt(pid);
buf.putInt(uid);
buf.putInt(amt);
buf.putInt(0); // PROC_TYPE_APP
buf.putInt(forLmkdOnly ? 1 : 0);
writeLmkd(buf, null);
```

`lmkd` 也不是简单地找 RSS 最大的进程。选择结果至少受以下信息共同影响：

- 当前内存压力及 PSI stall；
- 进程是否达到本轮允许回收的最小 `oom_score_adj`；
- swap 剩余量、page cache thrashing 和 workingset refault；
- 是否启用“杀最大合格进程”等策略；
- 低内存设备与高性能设备的不同配置；
- 厂商在产品属性与内存 cgroup 上的调整。

官方文档列出的 `ro.lmk.medium=800`、`ro.lmk.critical=0` 是特定模式下的默认配置说明，不是跨设备、跨压力级别的固定杀进程公式。应用侧更不应依赖某个数值来承诺存活时间。

`ApplicationExitInfo.REASON_LOW_MEMORY` 可用于分析一部分低内存退出，但官方 API 也说明，设备未必能把所有低内存终止都准确归为这个 reason；某些情况可能表现为 `REASON_SIGNALED` 和 `SIGKILL`。退出原因要和 `lmkd` 日志、系统 trace、当时的 `oom_score_adj` 一起判断。

## Freezer：进程还在，不等于线程还能运行

Cached App Freezer 与 `lmkd` 是两种不同动作：

- `lmkd` 终止进程，释放其资源。
- freezer 通过 cgroup v2 的 `cgroup.freeze` 暂停进程中的任务，进程和内存仍然存在。

Android 17 的 `CachedAppOptimizer.DEFAULT_USE_FREEZER` 为 `true`，但设备实际启用还要同时满足 DeviceConfig、内核和 libprocessgroup 对 freezer 的支持。`task_profiles.json` 中的 `Frozen` / `Unfrozen` profile 最终写入 `FreezerState`，ACK 基线中的 `kernel/cgroup/freezer.c` 与 `kernel/cgroup/cgroup.c` 实现并暴露 `cgroup.freeze`。

“`adj >= 900` 就一定冻结”也不准确。默认 freezer cutoff 是 `CACHED_APP_MIN_ADJ`，但 Android 17 允许通过 `freezer_cutoff_adj` 和实验开关调整。此外，`OomAdjuster.getFreezePolicy()` 还会检查进程是否持有显式或隐式 CPU time capability。AMS 只有在 freezer 已启用、进程满足 cutoff 且策略认为可冻结时，才安排异步冻结；中间还存在 debounce、待处理消息、Binder 事务和解冻原因。

同步 Binder 调用不会被简单概括为“自动解冻后一切正常”。Android 17 会冻结 Binder 接口并处理待处理事务；如果应用通过持续 Binder 事务规避冻结，或者冻结状态下异步 Binder 缓冲区耗尽，系统可以终止进程。`ApplicationExitInfo.REASON_FREEZER` 表示进程因为 freezer 相关错误被杀，例如 Binder ioctl、同步事务或异步缓冲区问题；它不表示一次普通冻结事件，也不是“解冻失败”的通用标签。

Perfetto 中进程存在、线程长时间没有 `sched_switch` 记录，只能作为“可能被冻结”的线索。线程也可能只是睡眠、等待锁、等待 Binder 或没有任务。要确认 freezer，应组合检查：

- `dumpsys activity processes` 中的 frozen / pending freeze、adj、procState；
- 目标进程实际 cgroup 的 `cgroup.freeze` / `cgroup.events`；
- ActivityManager 的 freezer trace 事件与调度轨迹；
- `dumpsys activity exit-info` 中的退出 reason 与 subreason；
- Binder 和 `lmkd` 日志。

同样，Perfetto 上的进程轨迹结束也不能单独证明是 LMKD：崩溃、force-stop、用户停止、升级和其他信号都能结束进程。

## Android 17 的 `mmd` 不取代 `lmkd`

Android 17 新增 Memory Management Daemon（`mmd`），用来集中处理 ZRAM 配置、参数和持续维护任务。它与 `lmkd` 的分工不同：

- `lmkd` 在内存压力下选择并终止较不重要的进程。
- `mmd` 处理 ZRAM 重压缩、写回、按进程写回和预取等维护任务。

系统启动完成后，`mmd_setup` 尝试配置 ZRAM，随后启动 `mmd` 服务。`system_server` 中的 `ZramMaintenance` 通过 JobScheduler 在设备空闲且电量不低时安排全局维护，并调用 `IMmd.doZramMaintenanceAsync()`。

Android 17 的 `CachedAppOptimizer` 还可以在 cached 进程压缩后，经 pidfd 请求 `mmd.asyncWritebackProcessZramMemory()`；用户重新启动已写回的缓存进程时，可以调用 `asyncPrefetchProcessZramMemory()`，减少从后备存储恢复页面造成的 major fault。是否启用、是否有后备块设备以及具体参数都属于产品配置，不能假设每台 Android 17 设备都会发生按进程写回。

这条新路径改变的是 cached 进程的内存驻留和再次启动代价，并没有取消 OOM adjustment、freezer 或 `lmkd`。

## 调度组与 task profile

进程重要性还会影响 CPU 和 I/O 资源。`OomAdjusterImpl` 计算 `schedGroup` 后，libprocessgroup 把抽象组映射为 task profile。Android 17 的 `task_profiles.json` 仍包含这些典型映射：

- `SCHED_SP_BACKGROUND` 组合节能、低 I/O 优先级和更大的 timer slack；
- `SCHED_SP_FOREGROUND` 组合较高性能、较高 I/O 优先级和正常 timer slack；
- `SCHED_SP_TOP_APP` 组合最大性能、最大进程容量和最大 I/O 优先级。

profile 只是平台默认策略的名字，最终可能涉及 cpuset、uclamp、I/O priority 或其他 controller。实际 cgroup 层级和文件路径由内核版本、init 配置与厂商产品配置共同决定。不要把某台设备的 `/dev/cpuset/...` 路径复制成所有 Android 17 设备的固定结构。

## 最小诊断方法

先固定同一时刻的 pid、uid 和进程名，再把 AMS、`/proc`、cgroup、退出记录和 trace 对齐。

```bash
# 找到精确进程；同一包可能有多个 processName
adb shell ps -A -o PID,UID,NAME | grep '<package-or-process>'

# AMS 视角：adj、procState、schedGroup、组件和冻结状态
adb shell dumpsys activity processes

# 内核 / lmkd 使用的当前优先级
adb shell cat /proc/<pid>/oom_score_adj

# 先找进程实际所属 cgroup，再读取相应 controller 文件
adb shell cat /proc/<pid>/cgroup

# 历史退出原因；需要结合日志和 trace 解释
adb shell dumpsys activity exit-info <package>

# 低内存和进程事件。不同产品的日志 tag、可见级别会有差异
adb logcat -b events -b system | grep -Ei 'lmkd|lowmemory|freez'
```

抓 Perfetto 时，应至少覆盖问题发生前后的调度、进程生命周期、ActivityManager 事件、内存计数器和 PSI。按以下顺序分析：

1. 进程的重要组件何时消失，`procState` 与 `adj` 何时改变；
2. 调度组和 freezer 状态是否随后改变；
3. PSI、swap 与 refault 是否显示持续内存压力；
4. 进程是被冻结、被 `lmkd` 终止，还是因其他原因退出；
5. 下次返回应用时，是原进程解冻、ZRAM 页面预取，还是创建了新进程。

只保存最终一张 `dumpsys` 快照，通常无法还原这条时序。

## 常见误判

### “进程还在，后台任务就可靠”

cached 进程可以被冻结或终止。裸线程、线程池、协程不会自行提升进程重要性；需要可靠完成的任务必须使用系统能识别和调度的组件。

### “前台服务就是前台应用”

前台服务能让用户感知持续工作，也能提高进程重要性，但 top Activity、visible Activity、前台服务在 `adj`、`procState`、调度组和后台能力上仍是不同状态。

### “`oom_score_adj` 就是全部优先级”

它主要服务于内存回收。CPU 资源看 `schedGroup` 与 task profile，后台权限和能力还要看 `procState`、capability、待机桶及相应子系统策略。

### “线程轨迹空白就是 freezer”

睡眠、锁等待、Binder 等待和无任务运行都可能没有 CPU slice。必须读取 freezer 状态或 ActivityManager freezer 事件来确认。

### “低内存退出只看 RSS 最大者”

RSS 只是候选选择的一部分。进程重要性、PSI、swap、thrashing、refault 和产品配置都会影响 `lmkd` 决策。

### “多进程总能提高稳定性”

多进程可以隔离一部分崩溃与内存峰值，但会增加启动、常驻内存、Binder 和一致性成本。只有边界稳定、通信较少且失败可以隔离时，这笔成本才合理。

## 版本边界

- Android 10：`lmkd` 支持 PSI 模式，默认配置为 `ro.lmk.use_psi=true`，内核需启用 `CONFIG_PSI=y`。
- Android 11：AOSP 引入 Cached App Freezer 代码路径，并改进基于 PSI、swap 和 thrashing 的 `lmkd` 策略。
- Android 12：AOSP freezer 默认值改为启用，但设备仍需满足配置和内核能力。
- Android 13：cached 进程可能只有有限或没有执行时间；`ApplicationExitInfo` 增加 freezer 退出原因。
- Android 17：进程状态计算代码位于 `com.android.server.am.psc`，常量与实现不应再引用 Android 16 的旧路径；平台新增 `mmd`，负责 ZRAM 与 swap 维护，但保留 `lmkd` 作为低内存终止决策者。

平台结论以 `android-17.0.0_r1` 为准；PSI 与 cgroup freezer 的内核实现以 `android17-6.18-2026-06_r6` 为准。具体设备的 feature flag、DeviceConfig、产品属性、cgroup 挂载和厂商内存策略仍需在目标构建上实测。
