---
title: "进程模型与生命周期管理"
chapter: "1.3"
section: "1.3"
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
task6_state: "reviewed"
status: "finalized"
pipeline_stage: "ready-to-publish"
task9_state: reviewed
---

# 1.3 进程模型与生命周期管理

Android 应用可以创建线程，却不能自行决定进程能活多久。系统根据进程中正在运行的组件、组件与其他进程的依赖关系、用户能否感知这些工作以及整机内存压力，持续计算进程重要性。内存紧张时，重要性较低的进程先成为回收候选。

这个模型解释了三类常见问题：

- 进程不存在时，启动组件要先由 Zygote（预加载 Android 运行环境、用于派生应用进程的模板进程）创建进程，再经过应用绑定和组件调度，冷启动路径因此更长。
- 缓存进程能缩短应用切回时间，但会占用内存；系统必须在切回速度与前台可用内存之间取舍。
- 一个线程即使还在运行，如果所属进程中没有系统认可的活跃组件，进程仍可能进入缓存态（cached）并被终止。

分析这类问题时，要把“应用代码是否还有工作”“ActivityManagerService（AMS）认为进程是什么状态”“内核是否允许它获得 CPU”“低内存策略是否把它列为候选”分开看。

## 应用进程从哪里来

默认情况下，每个应用使用自己的 Linux 用户 ID（UID）和进程，Activity、Service、BroadcastReceiver、ContentProvider 等组件运行在默认进程中。进程刚启动时只有主线程；组件生命周期回调通常由主线程分发，但这不表示组件的所有方法都只会在主线程执行。例如，远程 Binder 方法和来自其他进程的 ContentProvider 调用可以落在 Binder 线程池，相关实现仍要满足线程安全要求。

`AndroidManifest.xml` 可以改变进程边界：

- `<application android:process="...">` 为应用组件指定默认进程。
- `<activity>`、`<service>`、`<receiver>`、`<provider>` 可以覆盖该值。
- 以冒号开头的名字，例如 `:player`，表示应用私有进程，实际名字会带上包名前缀。
- 不以冒号开头的全局进程名只在共享 Linux UID 且签名匹配时才可能跨应用共用。`android:sharedUserId` 从 API 29 起已经废弃，新应用不应依赖这种设计。

在 Android 17 中，`android.os.Process.start()` 仍把用户 ID（UID）、组 ID（GID）、应用二进制接口（ABI）、目标 SDK 版本（targetSdk）、数据目录和运行时参数交给 `ZygoteProcess.start()`。进程创建（fork）发生在 Zygote 一侧；`Process.start()` 是应用框架的请求入口，不会直接调用 Linux `fork()`。应用进程创建后再经 Binder 向 `system_server` 回连，AMS 才能继续 `bindApplication` 和组件调度。

多进程会带来额外的隔离成本。一个 `android:process=":remote"` 至少增加一套进程地址空间、ART 运行时状态、Java 与原生堆、线程栈、主线程消息循环和 `Application` 初始化；原来的进程内调用也可能变成 Binder 进程间通信（IPC）。

适合拆进程的场景通常有明确的故障或内存边界，例如：

- 不可信插件或需要隔离访问权限的服务；
- 崩溃后不应导致主界面进程一同崩溃的独立模块；
- 生命周期清楚、结束后希望通过终止整个进程释放大块原生或图形内存的模块；
- 系统明确提供隔离进程模型的组件。

如果两个模块高频同步调用、共享大量可变状态，拆进程往往只会增加序列化、Binder 线程池、锁和状态同步成本。

## 组件状态决定进程重要性

开发者文档把应用进程概括为前台（foreground）、可见（visible）、服务（service）和缓存（cached）四类。AOSP 的执行策略还使用更细的 `adj` 回收优先级分数，数值越小，进程在低内存时越不容易成为终止候选。Android 17 的常量已经从旧版 `ProcessList` 移到 `com.android.server.am.psc.Constants`：

| 典型状态 | Android 17 基准 `adj` | 含义 |
| --- | ---: | --- |
| 顶层/前台（top/foreground） | `FOREGROUND_APP_ADJ = 0` | 用户正在交互，或进程正在执行广播接收器、服务回调等受保护工作 |
| 可见（visible） | `VISIBLE_APP_ADJ = 100` 起 | 内容仍可见；部分策略可以在可见区间内进一步分层 |
| 可感知（perceptible） | `PERCEPTIBLE_APP_ADJ = 200` 起 | 用户能感知中断，例如受认可的媒体播放或前台服务场景 |
| 服务（service） | `SERVICE_ADJ = 500` | 持有已启动服务（started service），但没有更重要组件 |
| 桌面（home） | `HOME_APP_ADJ = 600` | 当前桌面进程 |
| 上一个应用（previous） | `PREVIOUS_APP_ADJ = 700` 起 | 最近离开的应用；Android 17 可按开关对该区间分层 |
| B 类服务（service B） | `SERVICE_B_ADJ = 800` | 重要性进一步降低的老化服务 |
| 缓存（cached） | `CACHED_APP_MIN_ADJ = 900` 到 `CACHED_APP_MAX_ADJ = 999` | 当前没有用户可感知工作，可按系统需要回收 |

这些数值适合解释 AOSP 的相对顺序，不能当成所有设备不变的“保活等级”。Android 17 中的可见、上一个应用和缓存区间都存在更细的排序策略与功能开关；厂商还可以调整进程上限、冻结阈值和 `lmkd` 参数。

分类遵循三条规则。

第一，进程按其中最重要的活跃组件定级。一个进程同时拥有可见 Activity 和已启动服务时，不会因为服务的重要性较低就降到服务级别。

第二，重要性会沿依赖关系传播。高优先级进程绑定另一个进程的 Service，或正在使用另一个进程的 ContentProvider 时，被依赖进程需要获得足以完成请求的保护。绑定标志（flag）、依赖类型和能力传播规则都会影响最终结果，不能只看服务端自身组件。

第三，组件回调结束就可能撤销保护。`BroadcastReceiver.onReceive()` 返回后，广播接收器不再被视为活跃；此时让普通线程继续工作，不能保证进程还会存活。需要可靠完成的任务应交给 JobScheduler、WorkManager 或其他与系统调度约束相匹配的接口。

从 Android 13 开始，缓存进程在重新进入活跃生命周期状态前，可能只得到有限的执行时间，甚至得不到执行时间。应用必须把缓存态视为“可以立即停止”的状态，不能当作低优先级后台运行模式。

## Android 17 如何计算进程状态

Android 17 的实现不再适合用“AMS 调用一个旧版 `OomAdjuster.java`”一句话概括。进程状态相关实现已经进入 `com.android.server.am.psc`：

1. Activity、Service、Broadcast 等管理模块把组件和依赖变化交给 `ProcessStateController`。
2. `ProcessStateController` 提交待处理事件，并触发局部或全量内存不足（Out of Memory，OOM）优先级调整（adjustment）。
3. `OomAdjusterImpl.computeOomAdjLSP()` 从最重要条件开始计算 `adj`、`procState`、`schedGroup` 和能力标志（capability）。
4. 依赖遍历继续修正服务端、Provider 端及其他可达进程的结果。
5. 计算值提交后，回调更新调度组、缓存进程冻结器（freezer）、统计信息，并把 OOM 优先级同步给 `lmkd`。

下面的 Android 17 源码片段显示，顶层应用（top app）、正在接收广播和正在执行 Service 回调会得到不同的 `procState` 与调度组；这些是初始规则，后续还会处理 Activity、前台服务和进程依赖。

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
- 能力标志描述进程当前可以继承或使用的特定能力。Android 17 的冻结策略会直接检查 CPU 时间能力标志。

所以，“`oom_score_adj` 较低”不能推出“它一定在 top-app CPU 集合（cpuset）”，“有前台服务”也不能推出“它等同于顶层 Activity”。排查时必须同时记录这几组值。

## `lmkd` 决定何时杀、杀谁

Android 使用用户态低内存终止守护进程（`lmkd`）监控内存压力。Android 10 及以上支持 PSI（Pressure Stall Information，资源压力停顿信息）模式：内核统计任务因 CPU、内存或 I/O 资源争用而停顿的时间，`lmkd` 订阅内存压力阈值。当前官方配置仍以 `ro.lmk.use_psi=true` 为默认值，但前提是设备内核启用 PSI。

Android 17 的固定平台与内核源码版本可以核对这条路径：

- `ProcessList.setOomAdj()` 向 `lmkd` 发送 `LMK_PROCPRIO`，包含进程 ID（pid）、用户 ID（uid）、`adj`、进程类型等字段。
- `system/memory/lmkd/lmkd.cpp` 保存进程的 `oomadj`，读取 PSI、交换空间（swap）、页面缓存抖动（thrashing）、工作集页面淘汰后又被访问（workingset refault）等信号后选择合格目标。
- ACK `android17-6.18-2026-06_r6` 的 `kernel/sched/psi.c` 实现 PSI 触发器（trigger）的创建与轮询。

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

`lmkd` 也不是简单地找常驻内存集（RSS）最大的进程。选择结果至少受以下信息共同影响：

- 当前内存压力及 PSI 记录的停顿时间；
- 进程是否达到本轮允许回收的最小 `oom_score_adj`；
- 交换空间剩余量、页面缓存抖动和工作集页面淘汰后的再次访问；
- 是否启用“杀最大合格进程”等策略；
- 低内存设备与高性能设备的不同配置；
- 厂商在产品属性与内存控制组（cgroup）上的调整。

官方文档列出的 `ro.lmk.medium=800`、`ro.lmk.critical=0` 是特定模式下的默认配置说明，不是跨设备、跨压力级别的固定杀进程公式。应用侧更不应依赖某个数值来承诺存活时间。

`ApplicationExitInfo.REASON_LOW_MEMORY` 可用于分析一部分低内存退出，但官方 API 也说明，设备未必能把所有低内存终止都准确归为这一原因；某些情况可能表现为 `REASON_SIGNALED` 和 `SIGKILL`。退出原因要和 `lmkd` 日志、系统跟踪数据、当时的 `oom_score_adj` 一起判断。

## 缓存进程冻结器（Freezer）：进程还在，不等于线程还能运行

缓存应用冻结器（Cached App Freezer）与 `lmkd` 执行两种不同操作：

- `lmkd` 终止进程，释放其资源。
- 冻结器通过 cgroup v2 控制组的 `cgroup.freeze` 暂停进程中的任务，进程和内存仍然存在。

Android 17 的 `CachedAppOptimizer.DEFAULT_USE_FREEZER` 为 `true`，但设备实际启用还要同时满足可动态调整系统参数的 DeviceConfig 配置、内核和进程资源管理库 `libprocessgroup` 对冻结功能的支持。`task_profiles.json` 中的 `Frozen`/`Unfrozen` 配置最终写入 `FreezerState`，Android 通用内核（Android Common Kernel，ACK）固定版本中的 `kernel/cgroup/freezer.c` 与 `kernel/cgroup/cgroup.c` 实现并暴露 `cgroup.freeze`。

“`adj >= 900` 就一定冻结”也不准确。默认冻结阈值是 `CACHED_APP_MIN_ADJ`，但 Android 17 允许通过 `freezer_cutoff_adj` 和实验开关调整。此外，`OomAdjuster.getFreezePolicy()` 还会检查进程是否持有显式或隐式 CPU 时间能力标志。AMS 只有在冻结功能已启用、进程达到阈值且策略认为可冻结时，才安排异步冻结；中间还存在用于避免频繁切换状态的延迟（debounce）、待处理消息、Binder 事务和解冻原因。

同步 Binder 调用不能简单概括为“自动解冻后一切正常”。Android 17 会冻结 Binder 接口并处理待处理事务；如果应用通过持续 Binder 事务规避冻结，或者冻结状态下异步 Binder 缓冲区耗尽，系统可以终止进程。`ApplicationExitInfo.REASON_FREEZER` 表示进程因为冻结相关错误被终止，例如 Binder `ioctl`、同步事务或异步缓冲区问题；它不表示一次普通冻结事件，也不是“解冻失败”的通用标签。

系统性能跟踪工具 Perfetto 中进程存在、线程长时间没有 `sched_switch` 记录，只能作为“可能被冻结”的线索。线程也可能只是睡眠、等待锁、等待 Binder 或没有任务。要确认冻结状态，应组合检查：

- `dumpsys activity processes` 中的已冻结/待冻结状态（frozen/pending freeze）、`adj`、`procState`；
- 目标进程实际 cgroup 的 `cgroup.freeze` / `cgroup.events`；
- ActivityManager 的冻结跟踪事件与调度轨迹；
- `dumpsys activity exit-info` 中的退出原因（reason）与子原因（subreason）；
- Binder 和 `lmkd` 日志。

同样，Perfetto 上的进程轨迹结束也不能单独证明是 `lmkd` 所为：崩溃、强制停止（force-stop）、用户停止、升级和其他信号都能结束进程。

## Android 17 的 `mmd` 不取代 `lmkd`

Android 17 新增内存管理守护进程（Memory Management Daemon，`mmd`），用来集中处理内存压缩块设备（ZRAM）的配置、参数和持续维护任务。它与 `lmkd` 的分工不同：

- `lmkd` 在内存压力下选择并终止较不重要的进程。
- `mmd` 处理 ZRAM 重压缩、写回、按进程写回和预取等维护任务。

系统启动完成后，`mmd_setup` 尝试配置 ZRAM，随后启动 `mmd` 服务。`system_server` 中的 `ZramMaintenance` 通过 JobScheduler 在设备空闲且电量不低时安排全局维护，并调用 `IMmd.doZramMaintenanceAsync()`。

Android 17 的 `CachedAppOptimizer` 还可以在缓存进程压缩后，经进程文件描述符（pidfd）请求 `mmd.asyncWritebackProcessZramMemory()`；用户重新启动已写回的缓存进程时，可以调用 `asyncPrefetchProcessZramMemory()`，减少从后备存储恢复页面造成的主要缺页（major fault，即需要存储 I/O 才能补回页面）。是否启用、是否有后备块设备以及具体参数都属于产品配置，不能假设每台 Android 17 设备都会发生按进程写回。

这条新路径改变的是缓存进程的内存驻留和再次启动代价，并没有取消 OOM 优先级调整、冻结器或 `lmkd`。

## 调度组与任务配置（task profile）

进程重要性还会影响 CPU 和 I/O 资源。`OomAdjusterImpl` 计算 `schedGroup` 后，libprocessgroup 把抽象组映射为任务配置。Android 17 的 `task_profiles.json` 仍包含这些典型映射：

- `SCHED_SP_BACKGROUND` 组合节能、低 I/O 优先级和更大的定时器容许延迟（timer slack）；
- `SCHED_SP_FOREGROUND` 组合较高性能、较高 I/O 优先级和正常的定时器容许延迟；
- `SCHED_SP_TOP_APP` 组合最大性能、最大进程容量和最大 I/O 优先级。

任务配置只是平台默认策略的名字，应用时可能涉及 CPU 集合（cpuset）、CPU 利用率上下限（uclamp）、I/O 优先级或其他控制器。实际 cgroup 层级和文件路径由内核版本、init 配置与厂商产品配置共同决定。不要把某台设备的 `/dev/cpuset/...` 路径复制成所有 Android 17 设备的固定结构。

## 最小诊断方法

先记录同一时刻的进程 ID（pid）、用户 ID（uid）和进程名，再把 AMS、`/proc`、cgroup、退出记录和系统跟踪数据按时间对应起来。

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
2. 调度组和冻结状态是否随后改变；
3. PSI、交换空间与页面淘汰后的再次访问（refault）是否显示持续内存压力；
4. 进程是被冻结、被 `lmkd` 终止，还是因其他原因退出；
5. 下次返回应用时，是原进程解冻、ZRAM 页面预取，还是创建了新进程。

只保存最终一张 `dumpsys` 快照，通常无法还原这条时序。

## 常见误判

### “进程还在，后台任务就可靠”

缓存进程可以被冻结或终止。普通线程、线程池、协程不会自行提升进程重要性；需要可靠完成的任务必须使用系统能识别和调度的组件。

### “前台服务就是前台应用”

前台服务能让用户感知持续工作，也能提高进程重要性，但顶层 Activity、可见 Activity、前台服务在 `adj`、`procState`、调度组和后台能力上仍是不同状态。

### “`oom_score_adj` 就是全部优先级”

它主要服务于内存回收。CPU 资源要看 `schedGroup` 与任务配置，后台权限和能力还要看 `procState`、能力标志、应用待机分组（App Standby Bucket）及相应子系统策略。

### “线程轨迹空白就是进程被冻结”

睡眠、锁等待、Binder 等待和没有任务都可能导致线程没有 CPU 时间片。必须读取冻结状态或 ActivityManager 冻结事件来确认。

### “低内存退出只看 RSS 最大者”

常驻内存集（RSS）只是候选选择的一部分。进程重要性、PSI、交换空间、页面缓存抖动、页面再次访问和产品配置都会影响 `lmkd` 决策。

### “多进程总能提高稳定性”

多进程可以隔离一部分崩溃与内存峰值，但会增加启动、常驻内存、Binder 和一致性成本。只有边界稳定、通信较少且失败可以隔离时，这笔成本才合理。

## 版本边界

- Android 10：`lmkd` 支持 PSI 模式，默认配置为 `ro.lmk.use_psi=true`，内核需启用 `CONFIG_PSI=y`。
- Android 11：AOSP 引入缓存应用冻结器代码路径，并改进基于 PSI、交换空间和页面缓存抖动的 `lmkd` 策略。
- Android 12：AOSP 冻结器的默认值改为启用，但设备仍需满足配置和内核能力。
- Android 13：缓存进程可能只有有限或没有执行时间；`ApplicationExitInfo` 增加冻结相关退出原因。
- Android 17：进程状态计算代码位于 `com.android.server.am.psc`，常量与实现不应再引用 Android 16 的旧路径；平台新增 `mmd`，负责 ZRAM 与交换空间维护，但保留 `lmkd` 作为低内存终止决策者。

平台结论以 `android-17.0.0_r1` 为准；PSI 与 cgroup 冻结器的内核实现以 `android17-6.18-2026-06_r6` 为准。具体设备的功能开关、DeviceConfig、产品属性、cgroup 挂载和厂商内存策略仍需在目标构建上实测。
