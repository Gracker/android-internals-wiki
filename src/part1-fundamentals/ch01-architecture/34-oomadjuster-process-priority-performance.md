---
title: "Android 17 ProcessStateController、OomAdjuster 与进程优先级"
chapter: "1.34"
section: "1.34"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [oom, oom_score_adj, process_state_controller, process_priority, lmkd, freezer, AMS]
related_chapters: ["4.4", "1.3", "1.8", "5.8", "4.11", "1.18"]
last_verified: "2026-08-17"
last_verified_against: "AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6"
confidence: high
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
last_deep_review_at: "2026-08-16"
last_deep_review_run_id: "20260816-163551-deep-review-0e71bb6d"
last_review_finalize_at: "2026-08-17T16:12:41+08:00"
last_review_finalize_run_id: "20260817-160535-73cfe799"
sources:
  - type: official
    path: "developer.android.com/guide/components/activities/process-lifecycle"
  - type: official
    path: "source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "source.android.com/docs/core/perf/cached-apps-freezer"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/ProcessStateController.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/OomAdjusterImpl.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/Constants.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/psc/ProcStateController.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerfettoCategories.java (android-17.0.0_r1)"
  - type: aosp
    path: "system/memory/lmkd/include/lmkd.h (android-17.0.0_r1)"
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp (android-17.0.0_r1)"
  - type: kernel
    path: "include/trace/events/oom.h (android17-6.18-2026-06_r6)"
---

# 1.34 Android 17 ProcessStateController、OomAdjuster 与进程优先级

Android 不允许应用直接决定自己的进程寿命。`system_server` 根据进程承载的 Activity、Service、BroadcastReceiver、ContentProvider 以及跨进程依赖，持续计算进程重要性；低内存终止守护进程（lmkd）在内存压力出现时，使用这份结果选择回收目标。

API 37 的实现已经迁入 `com.android.server.am.psc` 包。继续以 `com.android.server.am.OomAdjuster.java` 为源码入口，会遗漏 Android 17 的 `ProcessStateController`、批处理会话、能力传播和新的跟踪字段。

以下结论限定于 `android-17.0.0_r1` Android framework / lmkd 和 `android17-6.18-2026-06_r6` 内核跟踪点。ProcessStateController（下文简称 PSC）、应用冻结机制（freezer）、LMKD socket（套接字）和 Perfetto 行为均以该基线为准，不外推到后续主线或厂商私有实现。

## 一、进程优先级不是一个数字

OomAdjuster 每轮计算会同时产生多组结果：

| 结果 | 主要消费者 | 回答的问题 |
|---|---|---|
| `adj` / `oom_score_adj` | lmkd、内核 OOM | 内存压力下，这个进程相对有多容易被终止 |
| `procState` | AMS、网络策略、统计、应用线程 | 进程当前属于 `top`、FGS、service、cached 等哪类状态 |
| `schedGroup` | libprocessgroup / cgroup（控制组） | 进程和子进程应进入 `background`、`default`、`top-app` 等 CPU 组 |
| capability（能力位） | 后台启动、网络、CPU / freezer 等策略 | 进程当前被允许做哪些事 |

四者相关，但不是一一映射。同为 `adj=0` 的顶部 Activity、正在执行广播接收者和服务回调，可以拥有不同的 `procState` 与调度组；同为前台服务（FGS）进程状态，普通 FGS 和 short FGS（短时前台服务）也使用不同的 adj。

`oom_score_adj` 越小，进程越受保护。Android 为受 AMS 管理的进程使用的大部分有效范围是 `-1000..999`；`UNKNOWN_ADJ=1001` 是计算中的未定值，不会作为正常结果写给 lmkd。

## 二、Android 17 的 PSC 代码结构

### 2.1 `ProcessStateController` 是 AMS 的统一入口

`ActivityManagerService` 创建 `ProcessStateController`，组件生命周期代码通过它提交状态变化和触发计算。主要入口包括：

- `runUpdate(proc, reason)`：更新指定进程及受影响的可达进程；
- `enqueueUpdateTarget(proc)` + `runPendingUpdate(reason)`：合并多个目标后更新；
- `runFullUpdate(reason)`：全量更新；
- `runFollowUpUpdate()`：处理有时效状态的到期；
- `startBatchSession(reason)`：在一组服务等状态变更结束后统一计算。

Controller 在每次计算前调用 `commitStagedEvents()`，把异步暂存的 Activity 等状态同步到计算视图。若批处理会话仍然开启，新请求只记录目标；会话关闭后才执行待处理更新或全量更新。

### 2.2 `OomAdjuster` 与 `OomAdjusterImpl` 的分工

`psc/OomAdjuster.java` 是公共计算与结果应用框架，负责：

- 全量、局部、待处理、后续更新的编排；
- 防止更新过程递归进入；
- 应用 `adj`、`procState`、`schedGroup` 和能力位；
- 与 lmkd、进程组、freezer、UID 观察者和 Perfetto 交互。

`psc/OomAdjusterImpl.java` 承载 API 37 的具体策略：计算进程本地状态、遍历服务 / Provider 连接、分配 LRU 梯度和处理循环依赖。

### 2.3 新的 `ProcStateController` 仍处于受功能开关控制的演进阶段

API 37 源码还包含基于进程图和 bucket priority queue（按优先级分桶的队列）的 `ProcStateController`。全量更新中，`OomAdjusterImpl` 只有在 `enableProcstateControllerComputation()` 开启时才调用它。

该标签的 `partialUpdate()`、`evaluateProcState(ProcessEdge)`、服务 / Provider 边计算仍留有 TODO；代码注释也说明 CapabilityController 尚未完全切换到它的 `procState` 结果。因此，它代表仍在推进的新算法，不能写成 Android 17 已经完全用基于优先级队列的图遍历替换 OomAdjuster。

### 2.4 `LSP` 不应自行展开成一句英文

API 37 用注解给出锁要求：`computeOomAdjLSP()`、`applyResultsLSP()` 等方法由 `@GuardedBy({"mServiceLock", "mProcLock"})` 保护。`updateOomAdjLocked()` 在持有 service lock 时再获取 proc lock，然后进入 LSP 方法。

源码没有把 `LSP` 定义为 “Locked Synchronized Pinned”。排障和改代码时应看 `@GuardedBy`，不要根据后缀臆造锁语义。

## 三、API 37 的 adj 分级

常量已从旧的 `ProcessList` 迁到 `psc/Constants.java`：

| 常量 | 值 | API 37 中的典型含义 |
|---|---:|---|
| `NATIVE_ADJ` | -1000 | 不由 AMS 分配 adj 的原生进程边界 |
| `SYSTEM_ADJ` | -900 | `system_server` |
| `PERSISTENT_PROC_ADJ` | -800 | 常驻系统应用 |
| `PERSISTENT_SERVICE_ADJ` | -700 | 被系统/持久进程按重要方式绑定的服务 |
| `FOREGROUND_APP_ADJ` | 0 | 顶部应用、正在执行接收者 / 服务回调等 |
| `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ` | 50 | 最近处于顶部的进程转入 FGS 后的宽限档 |
| `VISIBLE_APP_ADJ` | 100 | 可见 Activity 的起始档 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 普通 FGS、悬浮层 UI 等可感知工作 |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | 中等可感知绑定档；short FGS 使用 `225 + 1` |
| `PERCEPTIBLE_LOW_APP_ADJ` | 250 | 高于普通 service、低于可感知组件的绑定档 |
| `BACKUP_APP_ADJ` | 300 | 当前备份目标 |
| `HEAVY_WEIGHT_APP_ADJ` | 400 | 不能保存状态的重量级应用 |
| `SERVICE_ADJ` | 500 | 已启动服务的 A 档 |
| `HOME_APP_ADJ` | 600 | Home 进程 |
| `PREVIOUS_APP_ADJ` | 700 | 上一个应用的起始档 |
| `SERVICE_B_ADJ` | 800 | 较旧或高内存服务的 B 档 |
| `CACHED_APP_MIN_ADJ` | 900 | cached 区间起点 |
| `CACHED_APP_MAX_ADJ` | 999 | cached 区间终点 |

可见进程和上一个应用进程可以在功能开关开启时使用 100～199、700～799 的梯度。cached 进程则在 900～999 间按最近最少使用顺序（LRU）、有 Activity / 空进程分组和连接组重要性分配。

`CACHED_APP_LMK_FIRST_ADJ=950` 是 `ProcessList` 提交给 lmkd 的六档目标配置中的末档；源码注释称它为允许优先终止的 adj 等级。它不表示 lmkd 永远先终止所有 `adj>=950` 的进程。lmkd 还会结合当前压力级别、内存占用、swap、内存反复换入换出的抖动（thrashing）、进程类型和设备参数选择目标。

## 四、一轮 OOM adjustment（内存回收优先级调整）怎样计算

### 4.1 计算进程自身承载的组件

全量更新会遍历 LRU 进程，并调用下面这个 API 37 方法：

```java
private void computeOomAdjLSP(
        ProcessRecordInternal app,
        ProcessRecordInternal topApp,
        boolean doingAll,
        long now)
```

它不再接收旧实现里的 `cachedAdj`、`cycleReEval` 或 `computeClients` 参数。方法先根据进程自身状态计算初值，常见分支如下：

| 进程当前工作 | 初始 adj | procState | 调度组要点 |
|---|---:|---|---|
| 顶部 Activity | 0 | `TOP` | 通常 `TOP_APP` |
| 运行远程动画（remote animation） | 100 | 当前 top 状态 | `TOP_APP` |
| 测试插桩（instrumentation） | 0 | `FOREGROUND_SERVICE` | `DEFAULT` |
| 正在执行广播接收者 | 0 | `RECEIVER` | 由广播类型决定 |
| 正在执行服务回调 | 0 | `SERVICE` | 由回调的前后台属性决定 |
| 位于顶部但设备休眠 | 0 | 当前 top / sleeping 状态 | `BACKGROUND` |
| 暂无重要组件 | `UNKNOWN_ADJ` | `CACHED_EMPTY` | `BACKGROUND` |

随后再检查非顶部 Activity、FGS、悬浮层 UI、备份、Home、上一个应用、已启动服务、近期使用的 Provider 等本地状态。

### 4.2 可见 Activity 使用 visible 档，不等于前台 adj 0

非顶部但仍可见的 Activity，例如多窗口中的可见窗口，进入 visible 档。基础值为 `VISIBLE_APP_ADJ=100`，还可按 WindowManager 返回的窗口层级在 visible 范围内细分。

`procState` 反映 `TOP`（顶部）、`BOUND_TOP`（绑定到顶部应用）、`IMPORTANT_FOREGROUND`（重要前台）等进程状态语义；adj 反映内存回收保护程度。把“可见 Activity = adj 0”写死，会高估它相对顶部进程的保护等级。

### 4.3 FGS 还要区分普通、short（短时）与 recently-top（近期顶部）

API 37 的本地策略是：

- 普通 non-short FGS：`adj=200`、`procState=FOREGROUND_SERVICE`，并获得 BFSL（从后台启动前台服务）等相应能力；
- short FGS 在 `procState` 宽限未超时时：`adj=226`，即 `PERCEPTIBLE_MEDIUM_APP_ADJ + 1`，不获得 BFSL；
- 最近处于顶部的进程转入普通 FGS：宽限期内可提升到 `adj=50`；
- 最近处于顶部的进程转入 short FGS：宽限期内使用 `adj=51`；
- 最近处于顶部且运行符合条件的加急作业（expedited job）：相关豁免使用 `adj=52`。

Short FGS 超时后会触发带 `OOM_ADJ_REASON_SHORT_FGS_TIMEOUT` 的重算。结果取决于进程是否还有 Activity、其他 FGS、已启动服务或绑定，不能概括为“立即固定回落到 500”。

### 4.4 Service 和 Provider 依赖通过连接传播

每个进程完成本地初值后，`OomAdjusterImpl` 使用两套有序节点队列传播连接影响：

1. 按 `procState` 重要性处理服务 / Provider 连接；
2. 再按 adj 档位处理可能继续降低承载进程 adj 的连接；
3. 承载进程状态改善时重新进入对应队列，直到没有连接能继续改变结果。

这里的“承载进程”（源码语境中的 host）指运行该 Service 或 Provider 的进程。

这套做法支持多跳依赖与循环关系，不再是“从每个进程递归 computeClients”的简单伪代码。

绑定服务的传播结果受多个标志共同影响，例如：

- `BIND_WAIVE_PRIORITY`：连接不按常规方式提升承载进程；
- `BIND_NOT_FOREGROUND`：限制调度组和前台 `procState` 传播；
- `BIND_IMPORTANT`、`BIND_ABOVE_CLIENT`：加强承载进程的重要性；
- `BIND_NOT_PERCEPTIBLE`、`BIND_ALMOST_PERCEPTIBLE`：限制到特定可感知档；
- `BIND_ALLOW_OOM_MANAGEMENT`：允许承载进程更接近自身组件状态管理；
- `BIND_ALLOW_FREEZE`：阻止 CPU_TIME 能力沿该绑定自动传播。

因此，“Service 至少是 500”并不成立。被顶部或常驻客户端以相应标志绑定时，服务承载进程可以达到 bound-top、persistent-service 等更高保护档；已启动服务在后台又可能落入 500 / 800。

Provider 连接也能传播客户端重要性。持有外部进程句柄（external process handle）的 Provider 承载进程可提升到 `adj=0`；连接释放后的短时间内，近期使用的 Provider 还可能保留 `PREVIOUS_APP_ADJ`，到期后由后续更新重算。

### 4.5 最终分配 LRU 梯度并应用结果

连接传播结束后，`applyLruAdjust()` 为仍处于未知 / 缓存状态的进程分配 cached adj，并在相应功能开关下处理可见 / 上一个应用的梯度。`postUpdateOomAdjInnerLSP()` 再执行：

- 写入变化的 OOM 分数；
- 切换调度组和主线程 / RenderThread 优先级；
- 更新 freezer 资格；
- 把 `procState` 报告给应用线程、UID 观察者、网络策略和进程统计；
- 发送 `process_state_changed` Perfetto 事件；
- 必要时主动清理超额 cached 进程。

## 五、`procState`、`schedGroup` 与 capability（能力位）

### 5.1 `procState` 的数字顺序表示重要性顺序

`ActivityManager.java` 定义的主要状态从高到低依次包括：

```text
PERSISTENT → PERSISTENT_UI → TOP → BOUND_TOP
→ FOREGROUND_SERVICE → BOUND_FOREGROUND_SERVICE
→ IMPORTANT_FOREGROUND → IMPORTANT_BACKGROUND
→ TRANSIENT_BACKGROUND → BACKUP → SERVICE → RECEIVER
→ TOP_SLEEPING → HEAVY_WEIGHT → HOME → LAST_ACTIVITY
→ CACHED_ACTIVITY → CACHED_ACTIVITY_CLIENT
→ CACHED_RECENT → CACHED_EMPTY → NONEXISTENT
```

Android 17 已没有单独的 `PROCESS_STATE_FOREGROUND_SERVICE_LOCATION`。位置、相机、麦克风等 FGS 能力通过 capability 表达，不应向 `procState` 表中插入一个不存在的枚举值。

### 5.2 `schedGroup` 映射到线程组，不代表固定 CPU 份额

API 37 的 AMS 调度组常量是：

| AMS schedGroup | 值 | `applyResultsLSP()` 映射 |
|---|---:|---|
| `SCHED_GROUP_BACKGROUND` | 0 | `THREAD_GROUP_BACKGROUND` |
| `SCHED_GROUP_RESTRICTED` | 1 | `THREAD_GROUP_RESTRICTED` |
| `SCHED_GROUP_DEFAULT` | 2 | `THREAD_GROUP_DEFAULT` |
| `SCHED_GROUP_TOP_APP` | 3 | `THREAD_GROUP_TOP_APP` |
| `SCHED_GROUP_TOP_APP_BOUND` | 4 | `THREAD_GROUP_TOP_APP` |
| `SCHED_GROUP_FOREGROUND_WINDOW` | 5 | `THREAD_GROUP_FOREGROUND_WINDOW` |

具体使用哪些 cgroup 控制器、uclamp（调度器利用率上下界）和 cpuset（可运行的 CPU 集合），由设备的任务配置（task profile）和 libprocessgroup 配置决定。不能把 `schedGroup` 直接解释为固定 CPU 百分比，也不能假定 API 37 仍通过某个 `/dev/cpuctl` 路径写值。

进入 `top-app` 时，OomAdjuster 还会更新 UI / RenderThread 优先级；启用 FIFO UI 调度的产品使用先进先出调度回调，否则使用 `THREAD_PRIORITY_TOP_APP_BOOST`。离开 `top-app` 时再恢复。

### 5.3 Android 17 的 freezer 资格由 CPU 能力决定

API 37 的 `getFreezePolicy()` 逻辑很短：只要进程拥有 `PROCESS_CAPABILITY_CPU_TIME` 或 `PROCESS_CAPABILITY_IMPLICIT_CPU_TIME`，就不能冻结；两者都没有时，策略允许冻结。

- 顶部、可见工作、FGS、执行服务回调、接收广播等状态可赋予 CPU_TIME；
- adj 低于 `mFreezerCutoffAdj` 的进程获得 IMPLICIT_CPU_TIME；
- 服务 / Provider 绑定可以传播 CPU_TIME；
- `BIND_ALLOW_FREEZE` 用于阻止不必要的 CPU 时间传播，让服务承载进程在合适状态下可冻结。

OomAdjuster 只计算资格并回调 `onProcessFreezabilityChanged()`。`CachedAppOptimizer` 负责去抖延迟（debounce，即等待状态稳定）、Binder 冻结、cgroup 冻结、解冻和失败处理。冻结前遇到未排空 Binder 事务时可能重试；持续制造 Binder 流量逃避冻结的进程还可能被终止。

“adj 达到 900 就一定冻结”“没有待处理定时器才冻结”“冻结后不再重算 adj”都不符合 API 37 的规则。详细 Binder 行为见 §1.18。

## 六、OomAdjuster 与 lmkd 的边界

### 6.1 `system_server` 计算分数，lmkd 监测压力并选择目标

OomAdjuster 把 `curAdj` 应用到 `ProcessList.setOomAdj()`。该方法通过 lmkd 控制套接字发送 `LMK_PROCPRIO`；lmkd 校验进程 ID（PID）、用户 ID（UID）和值域，更新内部进程表，并在 `for_lmkd_only` 为 `false` 时写入内核的 `/proc/<pid>/oom_score_adj`。`for_lmkd_only` 表示只更新 lmkd 内部信息，不同步写这个内核分数文件。

lmkd 使用内存 PSI 事件、swap、thrashing 和设备属性判断何时需要回收。PSI 框架本身可衡量任务因 CPU、内存或 I/O 资源不足而停顿的时间；在 lmkd 的回收触发路径中，内存压力事件由 lmkd 直接订阅，通常不会先回调 AMS，再要求 OomAdjuster“加快 cached 进程老化”。API 37 的 OomAdjuster 中也没有通过 `PSI_SOME` / `PSI_FULL` 分支修改 cached adj。

这两个环节要分开理解：

```text
组件/依赖变化
  → ProcessStateController / OomAdjusterImpl
  → adj、procState、schedGroup、capability
  → LMK_PROCPRIO / LMK_PROCS_PRIO
  → lmkd 保存最新进程优先级

kernel PSI / swap / thrashing
  → lmkd 判断内存压力与候选范围
  → 结合 oom_score_adj 和内存数据选择进程
  → pidfd/kill + kill event
```

其中，pidfd 是引用目标进程的文件描述符，可避免仅凭可能复用的 PID 操作进程。

### 6.2 `LMK_PROCS_PRIO` 是小批量套接字消息

当 `mEnableBatchingOomAdj` 开启且属于批量应用结果时，变化进程先放入 `mProcsToOomAdj`，计算末尾调用 `ProcessList.batchSetOomAdj()`。

API 37 每个 `LMK_PROCS_PRIO` 包最多携带 3 个进程，每个进程有 5 个字段：PID、UID、oomadj、进程类型、`for_lmkd_only`。列表超过 3 个时会拆成多条控制套接字消息；批处理路径当前把进程类型固定为应用，并把 `for_lmkd_only` 写为 0（单进程 `LMK_PROCPRIO` 才有 zram 回写场景下的 `for_lmkd_only` 例外）。它不是 Binder IPC，也不会把任意数量进程放进一次调用。LMKD 批量命令编号、数据包长度和 thrashing 决策边界，可与 [4.4 系统内存压力与 lmkd](../ch04-memory/04-lmk.md) 交叉核对。

## 七、何时触发重算

更新主要由状态变化驱动，`OomAdjReason` 包括：

- Activity / UI 及 UI 可见性变化；
- 开始 / 结束执行接收者；
- 绑定、解绑、启动、停止或执行服务；
- 获取 / 移除 Provider；
- 进程开始 / 结束；
- 允许列表、UID 空闲、限制变化；
- short FGS 超时、备份、移除任务；
- 服务 Binder 调用、批量更新请求。

API 37 没有“每 1 秒无条件全量重算”的 `OOM_ADJ_UPDATE_INTERVAL`。有时效的状态会记录 `followupUpdateUptimeMs`，例如最近处于顶部的 FGS、上一个应用的 Provider；到期处理器先把进程加入待处理集合，再做局部更新。调度下一次后续更新时，还会用 `mFollowUpOomadjUpdateWaitDuration` 合并过近的超时点，所以不要把状态到期时刻理解为必然立刻单独重算。

若更新过程中又产生更新请求，`mOomAdjUpdateOngoing` 阻止递归进入，新目标进入 `mPendingProcessSet`。当前轮结束后统一处理待处理目标；若期间要求全量更新，则下一轮直接全量计算。

## 八、计算开销与锁边界

全量更新的计算和结果应用需要同时持有服务锁与进程锁，进程数和连接图复杂度会直接影响 `system_server` 临界区时长。API 37 使用了以下几类控制：

- 局部更新只收集目标及其可达进程；
- procState / adj 两套按重要性排序的节点队列减少无效反复扫描；
- 批处理会话合并一组组件状态变更；
- 待处理集合合并更新期间重复到达的目标；
- 后续更新设置最小间隔，合并接近的超时点；
- LMKD adj 更新可按 3 条记录一包发送；
- 进程组更新回调放到独立处理器线程，避免在线程很多时长期占用锁。

源码没有“超过 20 ms 就算 OomAdjuster 瓶颈”的平台阈值。应对照一帧预算、输入 / 启动关键路径、同一时段 AMS Binder 阻塞和设备进程规模评估。

## 九、Android 17 的诊断方法

### 9.1 从 dumpsys 和 procfs 核对结果

procfs 是以 `/proc` 路径暴露进程和内核状态的虚拟文件系统。保存 AMS 视角后，再与内核接收的分数对照：

```bash
adb shell dumpsys activity oom
adb shell dumpsys activity processes

adb shell pidof com.example.app
adb shell cat /proc/<pid>/oom_score_adj
```

在 `dumpsys activity oom` 和 `dumpsys activity processes` 中，重点看 `curAdj/setAdj`、`curRawAdj/setRawAdj`、`curProcState/setProcState`、调度组、能力位、`adjType`、`adjSource` 和 `adjTarget`。含义如下：

- `cur*`：本轮刚计算出的值；
- `set*`：最近一次已应用 / 已报告的值；
- `rawAdj`：尚未经过 `maxAdj` / LRU 等最终修正的中间 adj；
- `adjType/source/target`：哪类组件或哪条依赖把进程提升到当前档。

若 `/proc/<pid>/oom_score_adj` 与 `setAdj` 短时不同，应确认进程是否刚重启、是否处于 zram 回写的 `for_lmkd_only` 特殊路径，以及 lmkd 套接字是否重连。

### 9.2 Perfetto 的准确入口

API 37 在 Activity Manager atrace（Android 系统跟踪标记）中使用 `updateOomAdj_<reason>` 命名全量 / 局部更新时间片，例如 `updateOomAdj_activityChange`、`updateOomAdj_bindService`。下面的查询可查找耗时较长的计算：

```sql
SELECT ts, dur, name
FROM slice
WHERE name GLOB 'updateOomAdj_*'
ORDER BY dur DESC;
```

启用 Perfetto SDK 的 `proc_state` 分类后，adj、`procState` 或能力位改变会产生 `process_state_changed` 瞬时事件，字段包括：

- UID、PID、序列 ID 和更新原因；
- 更新前 / 后的 `procState`；
- 更新前 / 后的 OOM 分数；
- 更新前 / 后的能力位；
- CPU_TIME 与 IMPLICIT_CPU_TIME 的来源。

`proc_state_counter` 分类还会按 procstats（进程状态统计）状态输出全局进程数计数器，包括冻结进程数量。查看单个瞬时事件的结构化参数可使用：

```sql
SELECT s.ts, s.name, a.key, a.display_value
FROM slice AS s
JOIN args AS a USING (arg_set_id)
WHERE s.name = 'process_state_changed'
ORDER BY s.ts, a.key;
```

内核 `oom/oom_score_adj_update` ftrace（内核跟踪框架）事件用于核对分数写入时间；lmkd 终止事件和 PSI 轨道用于核对何时发生压力、为何选择该目标。不能仅凭“adj 升到 900 后出现 `am_kill`”断言进程一定由 lmkd 终止，还需检查终止原因、PID、压力事件和进程是否由 AMS 主动清理。

### 9.3 一次有效的优先级实验

1. 记录系统构建指纹（build fingerprint）、AOSP / 厂商版本和 lmkd / freezer DeviceConfig；
2. 分别触发顶部、可见、FGS、short FGS、接收者、已启动服务和 cached 状态；
3. 对每次变化记录 `adjType/source/target`，不要只记最终数字；
4. 对绑定场景逐个改变绑定标志，确认承载进程的 adj、`procState` 与能力位；
5. 同时采集 `updateOomAdj_*`、`process_state_changed`、`sched` 调度事件、Binder 和 `oom_score_adj_update`；
6. 将计算耗时按全量 / 局部更新、进程数、连接数和触发原因分组。

## 十、版本边界与源码锚点

在 Android 13 到 Android 17 的范围内，cached 进程可能获得很少或零 CPU 时间；Android 14 到 Android 17 的范围内，cached-app freezer 与延迟动态广播等策略进一步减少无效解冻。Android 17 的源码变化包括 PSC 包迁移、ProcessStateController 入口、基于能力位的 freezer 决策和结构化进程状态跟踪。这里没有使用后续主线实现反推 Android 17 行为。

源码定位：

- 入口与批处理：`services/core/java/com/android/server/am/psc/ProcessStateController.java`
- 计算 / 应用框架：`.../psc/OomAdjuster.java`
- API 37 主策略：`.../psc/OomAdjusterImpl.java`
- adj / `schedGroup` 常量：`.../psc/Constants.java`
- 新图算法演进：`.../psc/ProcStateController.java` 与 Graph / Edge 类
- LMKD 协议：`services/core/java/com/android/server/am/ProcessList.java`、`system/memory/lmkd/include/lmkd.h`
- Freezer 执行：`services/core/java/com/android/server/am/CachedAppOptimizer.java`
- 内核跟踪：`include/trace/events/oom.h`（`android17-6.18-2026-06_r6`）
- 官方说明：
  - [Processes and app lifecycle](https://developer.android.com/guide/components/activities/process-lifecycle)
  - [Low memory killer daemon](https://source.android.com/docs/core/perf/lmkd)
  - [Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)

排查进程为何被终止时，应保持这条边界：组件和依赖决定重要性，OomAdjuster 计算并应用重要性，lmkd 监测内存压力并选择目标，内核落实分数与进程控制。混用这四层术语，会把正常的 cached 回收误判成 OomAdjuster 计算错误，或把错误的绑定关系误判成 lmkd 过于激进。
