---
title: 进程模型与生命周期管理
chapter: '1.3'
section: '1.3'
status: ready-for-review
reviewed_date: '2026-05-05'
reviewed_by: openclaw-task6
review_type: task6-writing-quality-review
task6_result: pass-light-edit
drafted_date: '2026-03-31'
applicable_versions: Android 10 (API 29) - Android 16 (API 36)
last_verified: '2026-04-09'
last_verified_against: AOSP android-16.0.0_r1
confidence: high
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
sources:
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessList.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessStateRecord.java
- type: aosp
  path: frameworks/base/core/java/android/os/Binder.java
- type: aosp
  path: frameworks/base/core/java/android/os/Process.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/PhantomProcessList.java
- type: aosp
  path: frameworks/base/core/java/android/util/FeatureFlagUtils.java
- type: aosp
  path: system/memory/lmkd/lmkd.cpp
- type: aosp
  path: system/core/libprocessgroup/profiles/task_profiles.json
- type: aosp
  path: system/core/libprocessgroup/processgroup.cpp
- type: aosp
  path: system/core/libcutils/include/private/android_filesystem_config.h
- type: official
  path: developer.android.com/guide/components/processes-and-threads
- type: official
  path: developer.android.com/guide/topics/manifest/application-element
- type: official
  path: developer.android.com/guide/topics/manifest/service-element
- type: official
  path: source.android.com/docs/core/perf/lmkd
tags:
- process
- ams
- oom_adj
- lmkd
- zygote
- process-lifecycle
- binder
related_chapters:
- '1.1'
- '1.2'
- '1.4'
- '1.5'
- '4.4'
- '5.1'
- '5.8'
task6_state: reviewed
review_notes: '2026-04-29 task6 re-review (revisiting): pass-light-edit, 3 L1 fixes.
  | 2026-05-05 task6 re-confirm: fixed L1/L2 wording and punctuation; task9_result=needs-rework,
  pipeline kept task2b_pending.'
task2b_result: fixed
pipeline_stage: task9_pending
task9_state: pending
task9_result: ''
task6_reviewed_date: '2026-05-05'
task2b_state: pending
task9_reviewed_date: '2026-05-01'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-05-01T05:32:43+08:00'
---


# 进程模型与生命周期管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Zygote 如何通过 `fork()` 派生 App 进程，以及 Copy-on-Write 对启动速度的意义
- 🔹 Android 进程优先级模型：Foreground / Visible / Perceptible / Service / Cached / Empty 与 `oom_adj` / `oom_score_adj` 的对应关系
- 🔹 `lmkd` 的回收决策：`oom_score_adj`、`minfree` / PSI，以及 AMS 的动态调级
- 🔹 四大组件、多进程配置与 Binder / LocalSocket / 共享内存等 IPC 方式
- 🔹 进程模型在 Perfetto 中的表现：进程消失、优先级变化、常见误区与排查入口

### 扩展（可选深入）

- 🔸 Phantom Process Killer、App Standby Buckets 与后台限制
- 🔸 Isolated Process、SDK Sandbox 对安全与资源隔离的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 的进程模型

打开 Perfetto，会看到密密麻麻的进程列表——system_server、surfaceflinger、当前调试的 App、以及一大堆名字看着眼熟但说不出所以然的系统进程。这些进程不是随便跑在那里的，每一个进程的存在、消失、优先级高低，都有一套明确的规则在背后操控。

在做性能优化——尤其是 ANR 分析、启动速度优化、后台任务调度——我们必须理解这套规则。因为 Android 的进程模型直接决定了：

- App 进程什么时候会被系统回收，什么时候会安全地留在后台
- 为什么有时候后台 Service 被杀了，有时候前台 Activity 也会被杀
- 在 Perfetto 中看到某个进程消失，背后可能是哪类原因、该怎么追查
- 不同 Android 版本上进程管理策略的差异，导致同一个 App 在不同设备上表现不同

不理解进程模型，分析很多问题时就像在黑箱操作——现象看到了，但不知道背后的机制。

## Zygote：所有 App 进程的"母体"

在讲进程优先级之前，我们先搞清楚一个前置问题：Android 的 App 进程是怎么来的？

答案指向一个特殊的进程——Zygote。Zygote 在系统启动时由 init 进程创建（具体过程见 1.2 系统启动全流程），它在启动时会预加载大量的 Java 类和资源。之后，每当需要启动一个新的 App，系统不会从零开始创建进程，而是让 Zygote 调用 `fork()` 系统调用，复制自身来产生子进程。

这个设计有一个关键优势：**共享已加载的类和资源**。由于 Linux 的 fork 机制采用写时复制（Copy-on-Write），Zygote 预加载的所有 Java 类和 Framework 资源在 fork 之后被子进程共享（只要子进程不去修改它们）。因此每个 App 进程不需要重新加载几十 MB 的 Framework 代码，这也是 Android 冷启动通常能控制在几百毫秒级的重要原因之一。

[已验证: 官方文档, source.android.com/docs/core/memory]

在 AOSP 中，Zygote 的启动和 fork 流程涉及三个关键类的协作：

**`ZygoteInit.main()`** 负责初始化——预加载类和资源，然后创建 `ZygoteServer` 实例并进入等待循环：

```java
// frameworks/base/core/java/com/android/internal/os/ZygoteInit.java
// @ AOSP android-16.0.0_r1（简化流程，非逐行源码）
public static void main(String[] argv) {
    // 1. 预加载共享的 Java 类、资源和 native 库
    preload(bootTimingsTraceLog);
    // 2. 创建 ZygoteServer，打开 LocalSocket
    ZygoteServer zygoteServer = new ZygoteServer(isPrimaryZygote);
    // 3. 进入 selectLoop，等待 AMS 发来的 fork 请求
    caller = zygoteServer.runSelectLoop(abiList);
}
```

注意：这里展示的是简化后的主干流程，省略了异常处理和参数解析。实际的 socket accept 和 fork 操作不在 `main()` 中，而是在 `ZygoteServer.runSelectLoop()` 内部处理。当收到 AMS 的请求后，`ZygoteConnection.processCommand()` 负责解析参数并调用 `Zygote.forkAndSpecialize()` 创建子进程。

这里先看两个细节。第一，在同时支持 32 位和 64 位 ABI 的设备上，系统通常会准备两个 Zygote，并根据 App 的 ABI 选择对应的进程来 fork。第二，fork 之后子进程会调用 `ApplicationLoaders` 来加载 App 自己的 APK 代码，而 Framework 层的代码已经在 Zygote 阶段加载好了。

在 Perfetto 中，进程列表里会出现 `zygote64`（或 `zygote`）进程，它的启动时间很早，内存占用较大，但 CPU 使用率通常很低，因为它大部分时间都在等待 fork 请求。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/com/android/internal/os/ZygoteInit.java]

## Android 进程的常用优先级 buckets

Android 官方文档常把进程分成 foreground、visible、service、cached 这些大类。AOSP 用于回收决策的 bucket 会再细一层。排查内存回收时，最常用的是六类：**foreground → visible → perceptible → service → cached → empty**。

[图：Android 进程优先级 buckets 示意——从上到下依次为 foreground→visible→perceptible→service→cached→empty，旁边标出 android-16 中常见 `adj` 值区间]

AMS 会根据组件状态、绑定关系和前后台可见性计算进程的 `adj`。这些值随后写进 `/proc/<pid>/oom_score_adj`，供 `lmkd` 决定谁更适合被回收。

### Foreground Process

Foreground process 指用户此刻正在直接交互的进程。最典型的场景是进程里有一个 resumed Activity。处于前台广播回调、前台输入回调，或和 top activity 紧耦合的执行路径，也会把进程维持在这一档。`FOREGROUND_APP_ADJ` 在 android-16.0.0_r1 中是 **0**。

### Visible Process

Visible process 没有输入焦点，但界面仍在屏幕上。常见例子是被半透明窗口遮住、已经 `onPause()` 但仍可见的 Activity。AOSP 对应的常见值是 `VISIBLE_APP_ADJ = 100`。这一档离用户很近，系统通常不会优先回收。

### Perceptible Process

Perceptible process 代表用户能感知到它还在工作，但它未必占据可见界面。音频播放、输入法、壁纸，以及大量 foreground service 都落在这一层。foreground service 和 resumed Activity 所在的 foreground process 不是同一档。进程里没有 resumed Activity 时，`startForeground()` 提升出来的多数是 user-visible / perceptible bucket，常见值是 `PERCEPTIBLE_APP_ADJ = 200`，不是 `FOREGROUND_APP_ADJ = 0`。android-16 里还保留了 `PERCEPTIBLE_MEDIUM_APP_ADJ = 225` 和 `PERCEPTIBLE_LOW_APP_ADJ = 250` 这两个更细的档位。

### Service Process

Service process 指后台 `startService()` 挂着，但这项工作既不直接可见，也不在 perceptible bucket 里。它的常见值是 `SERVICE_ADJ = 500`。AOSP 还保留了更容易被回收的 `SERVICE_B_ADJ = 800`。早期资料里的 `SERVICE_A` / `SERVICE_B` 说法来自旧模型，android-16.0.0_r1 已经没有 `SERVICE_A` 这个常量名。

### Cached Process

Cached process 没有前台组件，只是保留在内存里加快下一次切回。android-16 把这段区间放在 `CACHED_APP_MIN_ADJ = 900` 到 `CACHED_APP_MAX_ADJ = 999`。`HOME_APP_ADJ = 600` 和 `PREVIOUS_APP_ADJ = 700` 也属于介于 service 与 cached 之间的保留档位，排查 Home 切换或最近任务回切时经常会碰到。

<!-- AIW-源码调研-2026-04-17 -->

## CachedAppOptimizer / Freezer 机制（Android 12+）

Android 12 引入了 `CachedAppOptimizer` 机制，通过 cgroup v2 freezer 技术冻结缓存的进程，这是比传统优先级调整更强的进程管理方式。

### 架构设计

**源码位置**：`frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`

**关键类/方法**：`CachedAppOptimizer` 类及其构造函数

**调用链**：
1. `ActivityManagerService` 实例化 `CachedAppOptimizer` →
2. `CachedAppOptimizer` 创建专用线程 `CachedAppOptimizerThread` →
3. 后台执行优化任务，包括进程冻结/解冻

```java
// 文件: frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java
public class CachedAppOptimizer {
    private final ActivityManagerService mAm;
    private final ServiceThread mCachedAppOptimizerThread;
    
    public CachedAppOptimizer(ActivityManagerService am) {
        mAm = am;
        mCachedAppOptimizerThread = new ServiceThread(
            "CachedAppOptimizerThread", Process.THREAD_GROUP_SYSTEM, /* allowBlocking= */ true);
        // 线程在 updateUseFreezer() 生效后通过 AMS handler 启动，构造函数只负责创建
    }
}
```

### Freezer 实现机制

**源码位置**：`task_profiles.json` + cgroup v2 freezer 控制器

**关键函数/类**：`enableFreezer()`, `setProcessFrozen()`, `FreezerState`

**调用链**：
1. `ActivityManagerService.enableFreezer()` →
2. `CachedAppOptimizer.handleMessage()` 处理冻结消息 →
3. 通过 cgroup freezer 控制器执行实际冻结操作

```java
// 文件: frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java
private static final int SET_FROZEN_PROCESS_MSG = 1;
private static final int REPORT_UNFREEZE_MSG = 2;
private static final int UID_FROZEN_STATE_CHANGED_MSG = 3;
private static final int DEADLOCK_WATCHDOG_MSG = 4;
private static final int BINDER_ERROR_MSG = 5;

// 内部类 FreezeHandler 处理冻结/解冻消息
private class FreezeHandler extends Handler {
    @Override
    public void handleMessage(Message msg) {
        switch (msg.what) {
            case SET_FROZEN_PROCESS_MSG:
                handleFreezeProcess(msg);
                break;
            case REPORT_UNFREEZE_MSG:
                handleReportUnfreeze(msg);
                break;
            case UID_FROZEN_STATE_CHANGED_MSG:
                handleUidFrozenStateChanged(msg);
                break;
            case DEADLOCK_WATCHDOG_MSG:
                handleFreezerDeadlock();
                break;
            case BINDER_ERROR_MSG:
                handleBinderError(msg);
                break;
        }
    }
}

// 冻结操作通过 Freezer.setProcessFrozen() 执行（非 native 方法直接调用）
// Freezer.setProcessFrozen() 内部写入 task profile Frozen/Unfrozen
```

**cgroup 配置**：

```json
// 文件: system/core/libprocessgroup/profiles/task_profiles.json
// Attributes 定义冻结状态属性
"Attributes": [
  { "Name": "FreezerState", "Controller": "freezer", "File": "cgroup.freeze" }
],
// Profiles 使用 SetAttribute 写入冻结/解冻值
"Profiles": {
  "Frozen": [{ "Name": "SetAttribute", "Params": { "Name": "FreezerState", "Value": "1" } }],
  "Unfrozen": [{ "Name": "SetAttribute", "Params": { "Name": "FreezerState", "Value": "0" } }]
}
```

### 在 Perfetto 中的表现

被冻结进程的线程 slice 会长时间不再出现，与被 LMK 杀死的进程表现完全不同：
- **被杀进程**：进程直接消失，所有线程停止
- **被冻结进程**：进程仍然存在，但线程 slice 消失，CPU 占用率为 0

**诊断方法**：
- 使用 `adb shell dumpsys activity | grep "Apps frozen:"` 查看冻结进程
- 通过 `adb logcat | grep -i "\(freezing\|froze\)"` 监控冻结事件
- 在 Perfetto v49+ 中，`android.freezer` 模块提供 `android_freezer_events` 表

```sql
-- Perfetto 查询冻结进程事件
SELECT
  ts,
  pid,
  uid,
  duration,
  reason
FROM android_freezer_events
ORDER BY ts DESC
LIMIT 20;
```

### 性能影响

- **CPU 消耗**：被冻结进程完全停止执行，CPU 占用率降为 0
- **内存使用**：保持内存占用但避免频繁页面交换，减少内存碎片
- **启动延迟**：解冻过程需要时间，可能影响应用恢复速度
- **Binder 交互**：同步 Binder 调用会被终止，需要异步处理机制
- **通知延迟**：后台服务冻结可能导致推送通知延迟

### 版本演进

- **Android 11 QPR3**: 引入 CachedAppOptimizer 概念，但 cgroup v1 实现
- **Android 12**: 全面迁移到 cgroup v2 freezer
- **Android 13**: 重构 `enableFreezer()` API，从 `Process` 类迁移到 `ActivityManagerService`
- **Android 14**: 引入 "Frozen-callee callback policy" for Binder
- **Perfetto v49**: 新增 `frozen` 布尔字段和 `android.freezer` 事件表
- **Android 16（Seamless App Updates）**: 应用更新时的冻结窗口从秒级降至毫秒级。Android 16 将 dexopt 尽量前移到应用安装/更新流程中，冻结窗口只覆盖最终文件切换阶段。此前应用更新需要先杀掉旧进程、替换 APK、再重新启动，整个冻结窗口可能持续数秒。

<!-- AIW-源码调研-2026-04-17 -->

### Empty Process

Empty process 连缓存 Activity 都没有，只剩一个已经建好的 Linux 进程和 ART 虚拟机外壳。它仍然可能留在 999 档，方便下一次快速启动，但内存一紧张就会优先被回收。

[已验证: 官方文档, developer.android.com/guide/components/processes-and-threads]
[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

## `adj` / `oom_score_adj` 机制：系统按什么顺序回收进程

历史文章经常把这套分数统称为 `oom_adj`。排查现代 Android 时，最好把两套刻度分开看：

- 早期 in-kernel LMK 文档常说的 `oom_adj` 是旧刻度，范围大致在 `-17..15`
- AOSP 现在在 Framework 层维护的是 `adj` 常量，最终写进 `/proc/<pid>/oom_score_adj`，范围是 `-1000..1000`

本章后文提到的 `0 / 100 / 200 / 500 / 800 / 900-999` 都是 android-16.0.0_r1 的现代 `adj` / `oom_score_adj` 值，不该和 `-12 / -11` 这类 legacy `oom_adj` 混着看。

### android-16.0.0_r1 常见 `adj` 值

| bucket / 常量 | `adj` / `oom_score_adj` | 典型含义 |
|---|---:|---|
| `PERSISTENT_PROC_ADJ` | -800 | 持久化系统进程 |
| `PERSISTENT_SERVICE_ADJ` | -700 | 持久化系统服务 |
| `FOREGROUND_APP_ADJ` | 0 | 当前 top / foreground 进程 |
| `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ` | 50 | 从 TOP 退到 FGS 的应用缓冲档，防止短暂切换场景下误杀。该常量自 Android 11 已存在于 ProcessList，后续版本逐步强化了 FGS 缓冲保护逻辑 |
| `VISIBLE_APP_ADJ` | 100 | 可见进程 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 用户可感知进程，foreground service 常落在这一档 |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | 中间过渡档 |
| `PERCEPTIBLE_LOW_APP_ADJ` | 250 | 较低优先级的 perceptible 进程 |
| `BACKUP_APP_ADJ` | 300 | 备份相关进程 |
| `HEAVY_WEIGHT_APP_ADJ` | 400 | 重量级进程 |
| `SERVICE_ADJ` | 500 | 普通后台 service |
| `HOME_APP_ADJ` | 600 | Home 进程 |
| `PREVIOUS_APP_ADJ` | 700 | 最近前台的上一个进程 |
| `SERVICE_B_ADJ` | 800 | 更容易被杀的 service bucket |
| `CACHED_APP_MIN_ADJ` | 900 | cached 起点 |
| `CACHED_APP_MAX_ADJ` | 999 | cached / empty 末端 |

`SERVICE_A` 这一类旧名字没有继续保留在 android-16.0.0_r1 的 `ProcessList.java` 常量里。把它写回现代表格，会把 service bucket 的杀伤顺序讲反。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

### `lmkd` 解决两个问题：何时杀，杀谁

`lmkd` 是 userspace low memory killer daemon。它做两件独立的事：

- **谁可杀**：看每个进程当前的 `oom_score_adj`
- **何时杀**：看系统此刻的内存压力信号

`oom_score_adj` 只负责排序，不负责告诉系统“现在已经该杀了”。决定回收时机的是 `vmpressure`、PSI、watermark、file cache 和 thrashing 这些信号。

### userspace `lmkd` 的时间线

Android 9 把 userspace `lmkd` 引入主线，但它的启用条件仍然带着 fallback 色彩：只有没检测到 in-kernel LMK driver 时，userspace `lmkd` 才接管回收。Android 10 开始，`lmkd` 增加 PSI monitors 模式，用 stall time 直接衡量内存压力。Android 11 又在 PSI 基础上引入新的 killing strategy，把 thrashing、file cache 和 watermark 一起纳入判断，低 RAM 设备和高性能设备也能共用同一套主线策略。

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd]

### legacy `minfree` 路径和现代 PSI 路径要分开写

很多老资料把 `ro.lmk.low`、`ro.lmk.medium`、`ro.lmk.critical` 当成通用默认配置。现代 Android 里，这样写会把两条路径揉在一起。

- `ro.lmk.use_minfree_levels=true` 时，`lmkd` 会回到更接近旧内核 LMK 的策略，按 free memory / file cache threshold 做决定
- `ro.lmk.use_psi=true` 时，`lmkd` 优先使用 PSI monitors；内核不支持 PSI 时才会退回 `vmpressure`
- `ro.lmk.lowmem_min_oom_score` 用来限制低内存路径里最低能杀到哪一档进程

所以，`ro.lmk.low / medium / critical`、minfree 阈值、vmpressure level 这些词，更适合放在 legacy 模式或兼容路径里解释。Android 10+ / 11+ 的主线写法应该把重点放在 PSI、thrashing、file cache 和 watermark。

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd]
[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/lmkd.cpp]

### AMS 入口和计算路径不在同一层

组件状态一变化，AMS 就会触发一轮优先级重算。android-16.0.0_r1 里，`ActivityManagerService.updateOomAdjLocked()` 更像入口包装，后面会委托给 `mProcessStateController.runUpdate(...)`，再进入 `OomAdjuster.updateOomAdjLSP()` / `computeOomAdjLSP()` 完成最终的 `adj`、`procstate` 和调度组计算。

进程的绑定关系、前后台可见性、Provider 依赖、service connection，都会在这条路径上抬高或压低分数。排查“后台进程为什么没被杀”时，只看 AMS 入口还不够，还得顺到 `OomAdjuster` 才能看到最终决策。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java; frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

## 四大组件与进程的对应关系

Android 的进程模型是**组件驱动**的——进程的存在是因为里面有组件在运行。

### 默认情况：单进程

如果开发者不在 AndroidManifest.xml 中做任何特殊配置，一个 App 的所有组件（Activity、Service、Receiver、Provider）默认都运行在同一个进程中。进程名就是 App 的包名。

### 多进程：android:process

开发者可以通过 `android:process` 属性将组件指定到不同的进程中：

```xml
<!-- 这个 Service 运行在名为 ":remote" 的私有进程中 -->
<service android:name=".RemoteService" android:process=":remote" />

<!-- 这个 Service 运行在名为 "com.example.shared" 的全局进程中 -->
<service android:name=".SharedService" android:process="com.example.shared" />
```

- 以 `:` 开头表示私有进程，只在当前应用内部创建和使用
- 不以 `:` 开头表示全局进程名。只有共享同一 UID 且使用同一证书签名的应用，才可能把组件放进同一个全局进程；组件能否被其他 App 调起，仍由 `exported` / `permission` 决定

多进程的常见用途包括：
- 将耗内存的操作（如 WebView）放到独立进程，避免影响主进程
- 将推送服务放到独立进程，提高稳定性
- 将后台同步放到独立进程，避免被杀时影响用户当前操作

但要注意：每个进程都有独立的 ART 虚拟机实例，因此单例对象、静态变量在不同进程之间并不共享，跨进程通信必须通过 Binder 等机制。

[已验证: 官方文档, developer.android.com/guide/topics/manifest/service-element]

## 进程间通信方式总览

Android 提供了多种进程间通信（IPC）机制，适用于不同场景：

### Binder IPC（主力通道）

Binder 是 Android IPC 的主力机制。ActivityManagerService、PackageManagerService 这类系统服务调用，默认都通过 Binder 在客户端进程和 `system_server` 之间传递。它提供同步事务语义，一次调用对应一次事务，客户端发起调用后通常会阻塞到服务端返回结果。

关于 Binder 的详细机制，我们会在 1.4 Binder IPC 机制与性能影响 中深入展开。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Binder.java]

### LocalSocket / Network Socket

LocalSocket 基于 Linux 的 Unix Domain Socket，用于同设备上的进程间通信。相比于 Binder，Socket 更适合流式数据传输场景。例如 Zygote 接收 fork 请求时用的是 LocalSocket。

输入系统也选择了 Socket（SocketPair）而非 Binder 来完成 InputDispatcher 与应用进程之间的通信。这个选择不是随意的：Socket 可以实现异步通知，且只需要两端各一个线程参与。假设系统有 N 个应用进程，输入相关的线程数是 N+1（1 是 InputDispatcher 线程）。但如果用 Binder 实现异步接收，每个应用需要两个线程（一个 Binder 线程、一个处理线程），发送端也需要两个线程（一个发送、一个接收完成通知），N 个应用就需要 2(N+1) 个线程。Socket 在这个场景下明显更高效。

### 共享内存（ashmem / memfd）

Android 早期大量使用 ashmem（Anonymous Shared Memory）做跨进程的大块匿名共享内存。Android 10 之后，系统逐步转向 Linux 标准的 `memfd_create()`。如果只是讲通用 IPC，这里的典型例子更适合写成 `ASharedMemory` 这类匿名共享内存对象。

图形缓冲区是另一条实现路线。现代 `GraphicBuffer` / `HardwareBuffer` 更接近 gralloc / dma-buf heaps 路径，应该放到 `BufferQueue`、`Gralloc`、`DMA-BUF` 那几节单独讲，不宜直接并进 ashmem / memfd 的例子里。

共享内存的优势很直接：不用序列化大块 payload，适合零拷贝或低拷贝传输。

### 管道（Pipe）和信号（Signal）

管道和信号主要用于父子进程间的简单通信。比如 lmkd 向进程发送 SIGKILL 来回收进程，Zygote 使用管道来监听子进程的退出事件。

[已验证: AOSP android-16.0.0_r1, 多处源码交叉验证]
[已验证: 来源见 obsidian/Cubox/Android帝国之进程杀手：lmkd-2023-12-27.md]

## 进程死亡回调：DeathRecipient

了解了进程间通信的方式之后，来看一个实际场景：通信对端的进程突然死亡时，如何感知并处理。

当 App 绑定了另一个进程的 Service（或者获取了另一个进程的 Binder 代理），如果那个进程突然死了（被 LMK 杀掉或崩溃），如何感知到这个变化？

答案是通过 `DeathRecipient`。这是 Binder 框架提供的回调接口：

```java
// 注册死亡监听
IBinder binder = service.asBinder();
binder.linkToDeath(new IBinder.DeathRecipient() {
    @Override
    public void binderDied() {
        // 目标进程已死，需要清理资源或重连
        Log.w(TAG, "Service process died, reconnecting...");
        bindService(intent, connection, Context.BIND_AUTO_CREATE);
    }
}, 0);
```

当目标进程死亡时，Binder 驱动会通知所有持有其代理的客户端进程，触发 `binderDied()` 回调。系统服务里也大量依赖这个机制，在对端消失后清理代理对象并重新建立连接。

`binderDied()` 本身不是系统自动写入 Trace 的固定事件。要在 Perfetto 里稳定定位它，抓取时至少打开 `android.log`，并在客户端的 `binderDied()` 回调里补一条 log 或 `Trace.beginSection("binderDied")`。复现后先查系统侧的 `am_kill` / `am_proc_died`，再看客户端是否在同一时间窗里进入 `binderDied()`。这样能把对端进程死亡和普通的 Binder 调用超时区分开。

```sql
SELECT ts, tag
FROM android_logs
WHERE tag IN ('am_kill', 'am_proc_died')
ORDER BY ts DESC
LIMIT 20;
```

[图：Perfetto 中客户端 `binderDied` 自定义日志，与 `am_proc_died` 出现在同一时间窗]

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/IBinder.java]

## 进程保活：系统视角

掌握了进程优先级和回收机制，自然会问一个问题：有没有办法让 App 进程不被杀？国内 Android 生态中，"进程保活"是一个经常被讨论的话题。从系统设计的角度来看，Android 并不希望 App 尽可能多地留在后台——后台进程越多，前台 App 能用的内存越少，用户体验就越差。

Android 官方推荐的"保活"方式只有一种：**做用户需要的事情**。如果 Service 在做用户能感知到的工作（比如播放音乐、导航），就调用 `startForeground()` 把它变成前台 Service。如果不是，就让系统在需要时回收它。

以下是 Android 逐步强化后台限制的历程：

- **Android 8.0（Oreo）**：限制后台 Service 的创建，引入 `Context.startForegroundService()`
- **Android 9.0（Pie）**：进一步限制后台 App 访问传感器、麦克风、摄像头
- **Android 12**：引入 Phantom Process Killer，限制后台进程组
- **Android 12L / 13**：引入更严格的前台 Service 通知要求
- **Android 14**：前台 Service 类型必须明确声明

[已验证: 官方文档, developer.android.com/about/versions]
[已验证: 来源见 obsidian/Cubox/Android 运存越来越大，为什么后台 App 还是会被「杀」？-2023-06-17.md]

## Phantom Process Killer（Android 12+）

Android 12 引入了一个新的限制机制：Phantom Process Killer。这里的“Phantom Process”指的是 App 进程通过 `Runtime.exec()` 或 `ProcessBuilder` 创建的子进程。

为什么需要这个机制？因为有些 App 会利用子进程绕开后台限制，主进程退到后台后，子进程仍然继续占用 CPU 和内存。Phantom Process Killer 用来监控这类子进程，并在系统认为数量过多或资源占用不合适时进行裁剪。

在 AOSP 中，这个上限由 `ActivityManagerConstants.DEFAULT_MAX_PHANTOM_PROCESSES` 定义，默认值是 32。`PhantomProcessList.trimPhantomProcessesIfNecessary()` 比较的是系统当前追踪到的 `mPhantomProcesses.size()` 与 `MAX_PHANTOM_PROCESSES`，所以这里的 32 指的是系统级的 phantom process 总数，不是单个 App 固定拥有 32 个子进程。超过上限后，系统会按父进程的 `oom_adj` 顺序裁剪多出来的 phantom process。

监控逻辑还受 `FeatureFlagUtils.SETTINGS_ENABLE_MONITOR_PHANTOM_PROCS` 控制，AOSP 默认值是 `true`。同时，`MAX_PHANTOM_PROCESSES` 可以通过 `DeviceConfig.NAMESPACE_ACTIVITY_MANAGER` 下的 `max_phantom_processes` 覆盖，所以不同设备上的实际门槛可能不同。正文里不宜把某条 adb 命令写成所有版本、所有 ROM 都成立的统一开关。

Android 16 引入了 AVF (Android Virtualization Framework) Terminal，允许在受保护的虚拟机 (pVM) 中运行终端环境。pVM 内部的进程不受宿主 Phantom Process Killer 32 个名额的限制。对于需要运行大量子进程的场景（如构建工具链、测试框架），AVF Terminal 提供了一种隔离化方案。但需要注意几个边界：

1. **pVM 并非普通 App 子进程保活方案**：pVM 启动开销远大于 fork，资源隔离粒度也不同，只适合需要强隔离的场景。
2. **第三方 App 可用性有限**：AVF Terminal 的产品边界和 API 开放程度仍在演进中，普通 App 能否直接创建 pVM 取决于系统权限和策略。
3. **与 PhantomProcessList 的关系**：pVM 内部的进程对宿主 AMS 的 `PhantomProcessList` 不可见，因此不受其计数裁剪。但宿主进程自身的 oom_adj 仍会影响系统对整个 pVM 资源的回收决策。

[待验证：AVF Terminal 在第三方 App 中的可用性边界和 API 37 的正式限制条件]

[图：Perfetto 进程列表中，同一 UID 下出现父 App 进程和多个 phantom process，系统裁剪后多余子进程消失]

[已验证: AOSP main, frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java; frameworks/base/services/core/java/com/android/server/am/PhantomProcessList.java; frameworks/base/core/java/android/util/FeatureFlagUtils.java]

## App Standby Buckets 对进程调度的影响

Android 9 引入了 App Standby Buckets 机制，将 App 分为五个桶：

1. **Active**：用户正在使用的 App，无任何限制
2. **Working Set**：经常使用但当前不在前台的 App，轻度限制
3. **Frequent**：每天使用但不频繁的 App，中度限制
4. **Rare**：很少使用的 App，严格限制后台作业、闹钟、网络
5. **Restricted**（Android 12 新增）：极低优先级，最高限制等级

Standby Bucket 影响的是 **JobScheduler 的执行频率、Firebase Cloud Messaging 的传递优先级、闹钟的精确度**等后台能力，而不是进程优先级（oom_adj）。也就是说，它影响的是后台任务的执行时机，而不是进程本身的存亡。

通过 `UsageStatsManager.getAppStandbyBucket()` 可以查询当前 Bucket，通过 `adb shell am set-standby-bucket <package> <bucket>` 可以手动测试不同 Bucket 下的行为。

[已验证: 官方文档, developer.android.com/topic/performance/appstandby]

## `procstate`、sched group、task profile 与 Perfetto 的连接点

很多性能问题在进程被杀之前就已经出现了。进程从 top-app 退到 background / cached 时，先变化的通常是 `procstate`、调度组和 cgroup 归属，进程本身还活着。

`OomAdjuster.computeOomAdjLSP()` 计算出 `curProcState` 之后，会同步更新 `currentSchedulingGroup`。调度组发生变化时，系统会走到 `android.os.Process.setProcessGroup(pid, group)`。这一步再往下落到 libprocessgroup 的 task profile / cgroup 配置，常见结果是进程从 top-app / default 档切到 background / restricted，对应的 cpuset、CPU 可用核和调度资源也跟着变。

[图：`procstate` → `OomAdjuster` → `setProcessGroup()` → task profile / cgroup → Perfetto `sched` / `process stats` 的映射图]

Perfetto 里最先冒出来的信号，通常是主线程和 RenderThread 在大核上的连续 runnable slice 变少，CPU frequency track 不再跟着交互抬升，或者 cached app 进入 freezer 之后线程 slice 长时间消失。读到这一步，再去看 §4.4《Low Memory Killer》、§5.1《Linux 进程调度基础》、§5.8《后台执行限制与优化》，上下文会更完整。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java; frameworks/base/services/core/java/com/android/server/am/ProcessStateRecord.java; frameworks/base/core/java/android/os/Process.java; system/core/libprocessgroup/profiles/task_profiles.json; system/core/libprocessgroup/processgroup.cpp]

## Isolated Process 与 SDK Sandbox

### Isolated Process

Android 允许把 Service 放进隔离进程，通过 `android:isolatedProcess="true"` 打开。这个进程运行在独立的 isolated UID 区间里。AOSP 在 `android_filesystem_config.h` 里专门预留了 `AID_ISOLATED_START..END` 给这类 sandboxed process。它没有应用声明权限，只能通过 Service API 和外界交互。

典型使用场景是浏览器渲染进程或承载不可信代码的隔离服务。把 UID 和 permission 混成一个概念，后面分析 SELinux、数据目录和跨进程身份时很容易出错。

[已验证: 官方文档, developer.android.com/guide/topics/manifest/service-element]
[已验证: AOSP android-16.0.0_r1, system/core/libcutils/include/private/android_filesystem_config.h]

### SDK Sandbox（Android 13+）

Android 13 引入了 SDK Sandbox，允许广告 SDK 运行在一个独立的沙箱进程中。这个沙箱进程有独立的 UID（以 `_sdk_sandbox` 结尾），与 App 主进程完全隔离。

这对性能分析的影响是：在 Perfetto 中会看到 App 包名后面跟着 `_sdk_sandbox` 后缀的进程，它们是广告 SDK 的沙箱进程。这些进程的内存和 CPU 使用不计入 App 主进程，但会占用系统总资源。

[已验证: 官方文档, developer.android.com/design-for-safety/privacy/sandbox]
[待验证: SDK Sandbox 在 Android 16 中的实际采用率]

## 在 Perfetto 中的表现

进程问题在 Perfetto 里至少有三种结局：**被 `lmkd` 回收、自己崩溃、只是从 top-app 降到 background / cached**。三种情况的抓取面不一样，读图顺序也不一样。仅凭“进程名字不见了”下结论，很容易把 kill、crash 和纯调级混成一类。

要把证据放在同一个时间窗里，抓取时至少带上这几组数据源：

- `android.log`：看 `am_kill`、`am_proc_died`、`am_crash`
- `linux.process_stats`：看进程 RSS、`oom_score_adj`、生命周期变化
- `linux.sys_stats`：看 `MemAvailable`、vmstat 一类系统内存信号
- `linux.ftrace`：至少补 `oom/oom_score_adj_update`；如果要看资源档位变化，再加 `sched/sched_switch`、`sched/sched_wakeup`

### 1. 先区分 kill、crash 和单纯降级

`android.log` 里的 `am_kill`、`am_proc_died`、`am_crash` 是最稳的时间锚点。`am_crash` 说明进程自己挂了；`am_kill` 更接近 AMS / LMK 的终止动作；只有进程从 top-app 降到 cached、日志里没有 kill / crash 记录，那才更像“活着，但资源档位已经掉下去”。

```sql
SELECT ts, tag
FROM android_logs
WHERE tag IN ('am_proc_start', 'am_kill', 'am_proc_died', 'am_crash')
ORDER BY ts DESC
LIMIT 40;
```

[图：同一时间窗里 `am_crash`、`am_kill`、`am_proc_died` 的三类样例对比，标注“崩溃 / 回收 / 仅降级”三种读法]

### 2. 再看它有没有先从 top-app 掉到 background

单纯降级通常先体现在 `Process Stats` 和 `sched` 轨道上。进程还在，主线程和 RenderThread 的 runnable slice 已经变碎，CPU 频率响应也弱了。如果 `oom_score_adj` 从 0 / 100 / 200 一路抬到 900+，同时 `MemAvailable` 持续走低，才更像系统在把它推向可杀区。

```sql
SELECT
  ts,
  (value / 1024) AS rss_kb
FROM counter
JOIN process_counter_track ON counter.track_id = process_counter_track.id
JOIN process USING (upid)
WHERE process.name = '<App包名>'
  AND process_counter_track.name = 'rssanon'
ORDER BY ts;
```

这个查询只给 RSS。判断“只是降级”还是“马上会被杀”，还要把它和同一时间窗里的 `oom_score_adj` 变化、`MemAvailable`、`sched` 轨道一起看。

[图：目标 App 的 `oom_score_adj` 逐步抬高，但进程仍在列表中；下方 `sched` 轨道显示线程切到 background 资源档位]

### 3. 需要核对 LMK 路径时，再补 `oom_score_adj_update`

`oom/oom_score_adj_update` 只在 `linux.ftrace` 里显式打开后才会出现。它适合核对 AMS / OomAdjuster 的结果是否真的写进了内核的 `/proc/<pid>/oom_score_adj`。如果这组事件缺失，就不要把“日志里有 `am_kill`”直接扩写成“LMK 细节已经确认”。

`binderDied()` 这类客户端回调也一样。Perfetto 不会自动替我们打点。排查对端进程死亡时，做法是把 `am_kill` / `am_proc_died` 当主锚点，再在客户端的 `binderDied()` 里补 log 或 `Trace.beginSection()`，把两边放到同一时间窗里比较。

[图：`am_kill`、`oom_score_adj_update` 和客户端 `binderDied` 自定义打点落在同一时间窗，说明对端先被回收，Binder 回调随后到达]

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags；Perfetto 抓取配置见 §13.5 `oom/oom_score_adj_update` 示例]

## 常见问题与误区

### 误区 1：App 在前台就不会被回收

**错误**。前台进程是最不容易被回收的一类，但在极端内存压力下（比如设备物理内存很小又运行了大型游戏），LMK 仍然可能杀掉前台进程。此外，这里的“前台”指的是“有前台 Activity 或前台 Service”，不是单纯指“屏幕上能看到这个 App”。如果一个 App 的 Activity 在前台但进程意外被杀，系统会重建 Activity（如果有 savedInstanceState）。

### 误区 2：多进程方案能解决所有内存问题

**不完整**。多进程可以把大内存操作隔离出去，但每个进程都要消耗额外的内存（ART 虚拟机、资源副本），而且进程间通信有额外开销。在低端设备上，多进程反而可能导致更频繁的 LMK 回收。

### 误区 3：后台 Service 设置为前台 Service 就万事大吉

**不完全正确**。前台 Service 能把进程从 `SERVICE_ADJ`（500）甚至 `SERVICE_B_ADJ`（800）提上来，但实际 adj 值取决于 `OomAdjuster` 的综合判定。多数情况下，`startForeground()` 会把进程提升到 `PERCEPTIBLE_APP_ADJ = 200`（用户可感知档）；刚从 TOP 退下还带着 FGS 的应用，可能短暂落在 `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ = 50` 这一缓冲档。但不能一概写成“提升到 0~100”——前台进程（`FOREGROUND_APP_ADJ = 0`）要求有 resumed Activity 或其他 top 条件，仅靠 FGS 本身通常达不到。此外，Android 14 要求前台 Service 必须声明类型（如 `camera`, `location`, `mediaPlayback`），并且系统会检查这些类型是否与 App 实际行为匹配。滥用前台 Service 不仅违反 Play Store 政策，也会被系统检测并降级。

### 误区 4：进程被杀一定是因为内存不足

**错误**。进程被杀的原因有很多：LMK 回收、App 自身崩溃（RuntimeException、Native Crash）、ANR 超时被系统杀掉、用户手动在设置中强制停止、厂商的后台管理机制等。分析时要先确认是什么原因导致进程消失。

[已验证: 来源见 obsidian/Cubox/App处于前台，Activity就不会被回收了？ - 掘金-2022-02-10.md]

## 与其他章节的关系

- **1.1 Android 分层架构**：进程模型是 Framework 层资源管理的入口
- **1.2 系统启动全流程**：Zygote 的启动、fork 和 SystemServer 关系在那一节展开
- **1.4 Binder IPC 机制与性能影响**：Binder、DeathRecipient、system_server 调用路径在那一节细讲
- **1.5 线程模型**：进程内线程和主线程调度问题要和这里配合看
- **4.4 Low Memory Killer**：`lmkd`、PSI、thrashing、watermark 的现代策略在那一节展开
- **5.1 Linux 进程调度基础**：sched group、cgroup、top-app / background 资源档位要回到那一节
- **5.8 后台执行限制与优化**：App Standby Buckets、后台限制、freezer 相关影响在那一节继续展开
- **9.1 ANR 设计思想**：ANR 触发后 AMS 和进程状态的处理行为在那一节补齐

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` — `adj` 常量定义
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — 进程管理入口
  - `frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java` — `adj` / `procstate` / sched group 计算
  - `frameworks/base/services/core/java/com/android/server/am/ProcessStateRecord.java` — 进程状态记录
  - `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java` — Zygote 启动与 fork
  - `frameworks/base/core/java/android/os/Process.java` — `setProcessGroup()` Java 入口
  - `frameworks/base/core/java/android/os/IBinder.java` — `DeathRecipient` 接口定义
  - `system/memory/lmkd/lmkd.cpp` — `lmkd` 守护进程实现
  - `system/core/libprocessgroup/profiles/task_profiles.json` — task profile 与 cgroup 配置
  - `system/core/libprocessgroup/processgroup.cpp` — 进程组切换实现
  - `system/core/libcutils/include/private/android_filesystem_config.h` — isolated UID 范围定义
- 官方文档：
  - [Processes and Threads | Android Developers](https://developer.android.com/guide/components/processes-and-threads)
  - [<application> | Android Developers](https://developer.android.com/guide/topics/manifest/application-element)
  - [<service> | Android Developers](https://developer.android.com/guide/topics/manifest/service-element)
  - [App Standby Buckets | Android Developers](https://developer.android.com/topic/performance/appstandby)
  - [SDK Sandbox | Android Developers](https://developer.android.com/design-for-safety/privacy/sandbox)
  - [Low Memory Killer Daemon | Android Source](https://source.android.com/docs/core/perf/lmkd)
