---



title: "Cached App Freezer 与 GC 触发边界"
chapter: "4.11"
section: "4.11"
status: finalized
finalized_by: openclaw-task2b-verifier
drafted_date: "2026-05-19"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37); 16KB Page Size 从 Android 15 起覆盖设备侧兼容"
last_verified: "2026-05-19"
last_verified_against: "AOSP android-16.0.0_r1 frameworks/base CachedAppOptimizer/OomAdjuster/ProcessList/ActivityManagerConstants + ART heap.cc; Android Source/Developers docs 2026-05; Android 17 tag 未公开"
confidence: medium
pipeline_stage: ready-to-publish
tags: [cached-app-freezer, gc, lmkd, oom-adj, binder-freezer, memory]
related_chapters: ["1.18", "4.2", "4.3", "4.4", "4.7", "5.8", "20.5", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "每日信息/DeepResearch/AOSP结构/官方文档"
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/cached-apps-freezer"
  - type: official
    path: "https://source.android.com/docs/core/architecture/ipc/binder-freezer"
  - type: official
    path: "https://developer.android.com/guide/components/activities/process-lifecycle"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://developer.android.com/reference/android/os/IBinder"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: aosp
    path: "art/runtime/gc/heap.cc"
  - type: research
    path: "DeepResearch/2026-05-19-android-cached-app-freezer-gc-trigger.md"
task6_state: reviewed
task9_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-07
last_task6_at: 2026-06-07T16:07:00+08:00
task9_result: auto-fixed
task2b_state: fixed
last_task9_autofix_at: "2026-06-05"
last_task9_at: "2026-06-05T05:28:04+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-07
task2b_result: fixed
---

# 4.11 Cached App Freezer 与 GC 触发边界

<!-- outline-start -->
## 要点

### 🔹 Freezer 解决的是 cached 进程继续消耗 CPU 的问题
梳理 Cached App Freezer 的定位：它把符合条件的 cached 进程迁移到 frozen cgroup，停止线程调度，减少后台 CPU 和电量消耗；同时说明冻结本身不释放 Java Heap、Native Heap 或匿名页内存。

### 🔹 OOM Adj 是入口条件，不是 LMK 决策复用
围绕 `ProcessList.CACHED_APP_MIN_ADJ`、`FREEZER_CUTOFF_ADJ`、`CACHED_APP_LMK_FIRST_ADJ` 拆清边界：freezer 与 LMKD 都会看进程重要性，但一个暂停执行，一个杀进程释放内存，排障时不能把两者合并成“低内存处理”。

### 🔹 CachedAppOptimizer 的冻结/解冻链路
以 `OomAdjuster.applyOomAdjLocked()`、`CachedAppOptimizer.freezeProcess()`、framework/native JNI 与 cgroup 写入为主线，给出冻结触发、异步处理线程、`mFrozenProcesses` 状态记录和进程移除清理路径。

### 🔹 Binder Freezer 与解冻延迟
说明 `IBinder.addFrozenStateChangeCallback` 与 binder freezer 文档的协作方式；重点放在同步 binder call、服务绑定、UI 可见性恢复等解冻入口，以及解冻延迟对调用方卡顿/ANR 的排查价值。

### 🔹 GC 触发与 Freezer 没有直接因果关系
把 ART GC 的触发路径放回 `art/runtime/gc/heap.cc`：对象分配、堆占用阈值、后台 GC 与 low-memory 信号会影响 GC；freezer 只是停止调度，不会主动触发 GC，也不会替代 `onTrimMemory()` 或 LMKD。

### 🔹 16KB Page Size 影响内存粒度，不改写 freezer 语义
解释 16KB 页对分配粒度、页对齐、native/anonymous memory 观测口径的影响；同时标注待验证点：Android 16/17 分支中是否存在 freezer 专属 16KB 适配代码，不能从页大小变化推导出 GC/freezer 策略变化。

### 🔹 线上归因：区分冻结、GC、LMK 与用户感知重启
建立排障口径：Perfetto/trace 中看线程调度停顿，dumpsys activity/process 看 adj 和 frozen 状态，ApplicationExitInfo 看退出原因，GC log/heap profile 看堆事件，避免把“回前台慢”“像冷启动”“内存突然下降”混成同一类问题。

## 扩展

### 🔸 Android 11 QPR3 到 Android 16 的版本演进
整理 cached app freezer、binder freezer callback、DeviceConfig throttle、16KB Page Size 支持之间的时间线。

### 🔸 厂商 freezer 策略差异
补充 Pixel、国内 ROM、低内存设备上的 freezer 开关、阈值、白名单和后台保活策略差异；需要实机 trace 或厂商源码验证。

### 🔸 与 1.18 Binder Freezer 的边界
本节聚焦内存、GC 与 LMK 视角；Binder 协议与 frozen process 通信细节详见 1.18。

<!-- outline-end -->

## 冻结处理 CPU 空转，保留进程内存

Cached App Freezer 要解决的问题很明确：cached 进程退到后台后，虽然没有可见界面也没有前台服务这类活跃组件，却可能因为定时器、线程池、回调分发或遗留 Binder 引用继续消耗 CPU。系统如果直接杀掉它，可以释放内存；如果只把它留在 LRU 列表里，它仍可能消耗调度时间。

Freezer 给 Android 增加了一个中间态：进程还在 RAM 里，Java Heap、Native Heap、mmap 区域、文件描述符和运行时状态仍保留，但线程被迁移到 frozen cgroup 后不再获得 CPU 时间。AOSP 文档把这个动作描述为“将 cached 进程迁移到 frozen cgroup”，目标是减少 active cached apps 带来的 active/idle CPU 消耗。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

这个定位划出了几条排障边界：

| 现象 | Freezer 的作用 | 不该推导出的结论 |
| --- | --- | --- |
| cached 进程后台空转 | 暂停线程调度，降低 CPU 和电量消耗 | 冻结会释放 Java Heap 或 Native Heap |
| 回前台时恢复变慢 | 解冻、广播投递、Binder 回调恢复可能带来延迟 | 看到慢恢复就等同于冷启动 |
| 低内存后进程消失 | 可能由 LMK/lmkd 杀进程 | freezer 会主动杀低优先级进程 |
| GC 日志出现在退后台附近 | 可能来自系统请求 runtime 做冻结前准备，也可能来自 ART 自身阈值 | frozen cgroup 会直接触发 GC |

Android Developers 的进程生命周期文档也给了同一层语义：cached process 不再被用户直接需要，系统可以在资源不足时杀掉它；从 Android 13 起，cached 进程可能获得有限甚至没有执行时间，直到重新进入活跃生命周期状态。[已验证: 官方文档, developer.android.com/guide/components/activities/process-lifecycle]

## OOM Adj 只是入口条件

决定“冻谁”之前，先要搞清楚“怎么判断谁该冻”。Freezer 和 LMK 都会参考进程重要性，但两者的动作不同。Freezer 暂停执行，LMK/lmkd 杀进程释放内存。把这两条路径合成“低内存处理”会让线上归因跑偏。

`ProcessList.java` 与 `ActivityManagerConstants.java` 里与本节相关的值很少：

| 常量 | AOSP android-16.0.0_r1 值 | 用途 |
| --- | ---: | --- |
| `CACHED_APP_MIN_ADJ` | `900` | cached 进程区间起点 |
| `CACHED_APP_MAX_ADJ` | `999` | cached 进程区间末端 |
| `CACHED_APP_LMK_FIRST_ADJ` | `950` | LMK 候选中更早被回收的 cached 进程起点 |
| `FREEZER_CUTOFF_ADJ` | 默认 `CACHED_APP_MIN_ADJ`；`prototypeAggressiveFreezing` 打开时为 `HOME_APP_ADJ` | freezer 判断可冻结进程的 adj 阈值 |

[已验证: AOSP android-16.0.0_r1, `ProcessList.java` / `ActivityManagerConstants.java`]

`OomAdjuster.getFreezePolicy()` 才是冻结资格判断所在位置。它先排除带有 CPU capability、`shouldNotFreeze()` 或 `isFreezeExempt()` 的进程；通过这些排除项后，`curAdj >= FREEZER_CUTOFF_ADJ` 的进程才会进入冻结候选。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

这段设计有两个排障含义：

- `oom_score_adj` 高不等于一定被冻结。前台服务、绑定关系、CPU capability、文件锁、厂商白名单都会让 cached 进程停留在可运行状态。
- 被冻结不等于即将被 LMK 杀掉。冻结后的进程仍占内存；只有内存压力进入 kswapd / LMK 路径，系统才会回收页或杀进程。Android 内存管理文档把低内存路径拆成 kswapd 回收、`onTrimMemory()` 通知、LMK 杀进程几类动作，freezer 不在这条释放内存路径里。[已验证: 官方文档, developer.android.com/topic/performance/memory-management]

## 冻结路径：OomAdjuster 判断，CachedAppOptimizer 执行

冻结动作由 `CachedAppOptimizer` 在 system_server 内异步处理。`OomAdjuster.applyOomAdjLSP()` 完成本轮 adj、proc state、sched group 等状态更新后，会调用 `updateAppFreezeStateLSP()`；后者根据 `getFreezePolicy()` 的结果选择冻结或解冻。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

源码路径可以压缩成下面这条：

```text
OomAdjuster.applyOomAdjLSP(app)
  -> updateAppFreezeStateLSP(app, reason, immediate, oldOomAdj)
     -> getFreezePolicy(app)
        -> curAdj >= FREEZER_CUTOFF_ADJ && !isFreezeExempt()
     -> CachedAppOptimizer.freezeAppAsyncLSP(app)
        -> FreezeHandler: SET_FROZEN_PROCESS_MSG
           -> freezeProcess(proc)
              -> mFreezer.freezeBinder(pid, true, timeout)
              -> mFreezer.setProcessFrozen(pid, uid, true)
              -> opt.setFrozen(true)
              -> mFrozenProcesses.put(pid, proc)
```

`freezeAppAsyncLSP()` 在投递冻结消息前会调用 `scheduleTrimMemory(TRIM_MEMORY_BACKGROUND)`，并把进程标记为 pending freeze。执行冻结的是 `FreezeHandler` 线程中的 `freezeProcess()`。它先冻结 Binder 接口，再通过 `mFreezer.setProcessFrozen(pid, uid, true)` 设置进程冻结状态，然后记录 `mFrozenProcesses`。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

这套顺序解释了几个线上现象：

- 退后台到冻结之间存在 debounce。AOSP 文档说 Android 14 及以上会在进程进入 cached 状态 10 秒后冻结；源码中也有 `mFreezerDebounceTimeout` 这类延迟控制。设备厂商可以通过 DeviceConfig 或 framework 配置调整这个窗口。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]
- Binder 在进程冻结前先被处理。`freezeProcess()` 调用 `freezeBinder()` 后才设置进程 frozen，避免未完成事务在冻结点留下不一致状态。
- 进程清理时必须删除 frozen 状态。`onCleanupApplicationRecordLocked()` 会移除 pending freeze 消息并从 `mFrozenProcesses` 删除 pid，防止 system_server 继续把已经退出的进程当成 frozen 目标。

解冻走同一套状态表。`unfreezeAppInternalLSP()` 会先检查 frozen 期间是否收到同步 Binder 事务；命中后用 `ApplicationExitInfo.REASON_FREEZER` 杀掉服务端进程。通过检查后，它再调用 `freezeBinder(pid, false, ...)` 和 `setProcessFrozen(pid, uid, false)`，清理 `mFrozenProcesses` 并分发 unfrozen 事件。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

## 冻结期间不能把 GC 当成正在运行的后台任务

AOSP freezer 文档明确写到：进程被冻结后，所有线程都暂停，直到解冻前不能执行 CPU work；结果是应用不能执行 GC，也不能响应内存 trim 事件。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

同一页还补了一条 Android 14 之后的行为：进程进入 cached 状态后不久，系统可能请求 app runtime 执行一次 GC，为后续冻结做准备；冻结后还可能发生额外的内存规整，比如把 dirty pages 写回 backing storage、把 anonymous pages swap 到 zRAM。这里的时间顺序容易被误读：

```text
进入 cached 状态
  -> framework 可能发送 TRIM_MEMORY_BACKGROUND
  -> runtime 可能收到一次后台 GC 请求
  -> 达到冻结条件后进入 frozen cgroup
  -> frozen 期间线程不运行，ART 不能继续执行 GC
  -> 内核/系统仍可能围绕页回收、zRAM、compaction 改变物理内存分布
```

所以退后台附近出现 GC 日志，不足以证明 freezer 触发了 GC。更稳的判断方式是把事件放到时间轴上：GC slice 在 freeze slice 前，可能是冻结前准备；GC slice 在 unfreeze 后，可能是恢复执行后补跑的 heap 任务；如果进程处在 frozen 区间内，ART 自身的 mutator 和 GC 线程都拿不到 CPU。

ART 的触发条件仍在 `art/runtime/gc/heap.cc`。源码里能看到三类常见入口：

- 对象分配失败或分配压力变高时，`CollectGarbageInternal(..., kGcCauseForAlloc, ...)` 会作为阻塞式 GC 路径出现。
- 并发 GC 由 `RequestConcurrentGC()` 投递，触发原因可以是 `kGcCauseBackground` 或 native allocation 压力。
- `target_footprint_` 和 `concurrent_start_bytes_` 决定下一次 GC 的启动水位，`GrowForUtilization()` 会在 GC 后重新计算这些阈值。

[已验证: AOSP android-16.0.0_r1, art/runtime/gc/heap.cc]

这和 §4.3「ART 虚拟机内存管理」的解释一致：GC 是 runtime 根据堆占用、分配速度、collector 策略和进程状态做出的内存管理动作。Freezer 只改变线程能不能运行，不改写 ART heap 的阈值公式。

## Binder Freezer 影响的是调用边界，不是内存释放

Binder Freezer 是 cached app freezer 最容易在业务侧显形的部分。应用退后台后，如果还有服务端 Binder 被其他进程持有，就可能遇到三类结果：

| Binder 形态 | frozen 目标进程上的处理 | 风险 |
| --- | --- | --- |
| 同步 Binder transaction | 系统终止 frozen 服务端，避免调用方无限等待 | 调用方收到 `RemoteException`，服务端 `ApplicationExitInfo` 记录 `REASON_FREEZER` |
| `oneway` 异步 transaction | 事务先进入 per-process buffer，目标解冻后再处理 | buffer 溢出会导致服务端被终止；解冻后可能集中处理过期事件 |
| 持续 callback | 调用方应按 cached/frozen 状态暂停、丢弃或合并事件 | 后台无效 work、解冻瞬间事件洪峰、ANR 归因困难 |

[已验证: 官方文档, source.android.com/docs/core/architecture/ipc/binder-freezer]

`IBinder.addFrozenStateChangeCallback()` 可以让持有远端 Binder 的进程收到 frozen/unfrozen 状态变化通知。Android API reference 标注该方法 Added in API level 36，文档同时提醒：事件可能合并，只能拿来判断最新状态，不能拿来统计状态变化次数；本地 Binder 不会触发这类通知，因为本地 Binder 所在进程与监听者同进程。[已验证: 官方文档, developer.android.com/reference/android/os/IBinder]

这部分的协议细节放在 §1.18「Binder Freezer 与缓存进程冻结性能」。本节只保留内存视角的判断：Binder Freezer 不释放内存，它只改变 frozen 进程接收 IPC 时的行为。线上看到 `REASON_FREEZER`，优先查 stale Binder 引用、unbind 后继续调用、异步 callback 过量和解冻事件堆积。

## 16KB Page Size 改变页粒度，不改变 freezer 语义

Binder Freezer 解决的是 frozen 进程的 IPC 行为问题；还有一个话题在内存分析中经常被和 freezer 并列提起：16KB Page Size。两者容易被放到一起讨论，因为二者都会影响内存观测口径。官方 16KB 文档说明，从 Android 15 开始 AOSP 支持 16KB page size 设备；Google Play 从 2025-11-01 起要求 target Android 15+ 的 64 位新应用和更新支持 16KB page sizes。文档也给出方向性测试结果：16KB 设备平均使用稍多内存，但在启动耗时、启动功耗、相机启动和系统启动方面有收益。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

这类变化影响的是页表、TLB 覆盖范围、ELF segment 对齐、native allocation 对齐和 page fault 计数。它会改变 `dumpsys meminfo`、RSS/PSS、匿名页、zRAM 回收这类指标的观察粒度，但不会把 freezer 变成 GC 触发器。

截至本轮核对，AOSP android-16.0.0_r1 的 `CachedAppOptimizer.java`、`OomAdjuster.java`、`ProcessList.java`、`ActivityManagerConstants.java` 中没有看到“16KB page size 专门改变冻结策略”的判断分支。ART `heap.cc` 中能看到堆水位、native allocation 水位、后台 GC 请求等逻辑，但没有证据表明 frozen cgroup 状态会重写这些阈值。[待验证: Android 17 release tag 公开后复核是否存在设备侧或 vendor 侧 freezer 专属 16KB 调整]

工程上可以这样拆：

- 16KB 页让一次页映射覆盖更大内存，可能减少 page fault 和 TLB miss；详见 §4.7。
- Freezer 让 cached 进程停止执行，减少 CPU 消耗；它不回收进程地址空间。
- GC 由 ART heap 状态触发；冻结前 runtime 可能被请求做一次准备性 GC，但 frozen 期间 GC 线程不能运行。
- LMK/lmkd 才负责在低内存场景下杀进程；详见 §4.4。

## 线上归因要把四类事件拆开

“回前台慢”“像冷启动”“内存突然下降”“GC 变多”经常出现在同一段用户反馈里。排障时要把它们拆成不同信号，而不是按单一因果链解释。

| 要判断的问题 | 观察入口 | 指向的机制 |
| --- | --- | --- |
| 进程是否被冻结 | Perfetto `system_server` / `Freezer` track、`dumpsys activity` 的 frozen 列表、logcat `freezing/froze` | Cached App Freezer |
| 进程是否被杀 | `ApplicationExitInfo.getReason()`、tombstone、crash/ANR 平台日志 | LMK、freezer kill、crash、ANR、自杀退出 |
| 内存是否被系统回收 | zRAM、kswapd、PSI、lmkd 日志、`dumpsys meminfo` 前后对比 | kswapd / lmkd / compaction |
| GC 是否参与 | ART GC log、Perfetto ART heap/GC slice、allocation stall、heap profile | ART heap 管理 |
| 回前台慢来自哪里 | Activity launch slice、Binder latency、unfreeze slice、class loading、资源加载 | 解冻延迟或普通启动路径 |

AOSP 文档给出的调试入口可以直接作为排查基线。下面这组命令用于确认 freezer 是否可用、某个进程是否被冻结，以及退出原因是否来自 freezer。

```bash
adb shell dumpsys activity | grep -A 20 "Apps frozen:"
adb shell am freeze <process>
adb shell am unfreeze <process>
adb logcat | grep -i "\(freezing\|froze\)"
```

这些命令只能证明 freezer 状态变化，不能证明 GC 或 LMK 原因。要判断退出原因，需要结合 `ActivityManager.getHistoricalProcessExitReasons()` 读取 `ApplicationExitInfo`。官方 reference 把 `REASON_FREEZER` 描述为 App Freezer 导致的退出，例如 frozen 期间收到同步 Binder transaction；`REASON_LOW_MEMORY` 则表示系统 low memory killer 杀掉了进程。[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationExitInfo]

Perfetto 适合把冻结、解冻和 GC 放在同一条时间轴上。AOSP 文档说明 freezer 事件会出现在 `system_server` 下名为 `Freezer` 的 track，`Freeze` / `Unfreeze` slice 表示进程状态变化，`updateAppFreezeStateLSP` 表示 system_server 重新评估进程属性。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

这段 SQL 用来从 trace 中抽出 freezer 事件，随后再按 pid 和时间窗口关联 ART GC、lmkd、Activity launch：

```sql
INCLUDE PERFETTO MODULE slices.with_context;

SELECT
  ts,
  dur,
  process_name,
  track_name,
  name
FROM process_slice
WHERE process_name = 'system_server'
  AND track_name = 'Freezer'
  AND (name LIKE 'Freeze %' OR name LIKE 'Unfreeze %')
ORDER BY ts;
```

如果 `Freeze` 后没有进程退出记录，只有 CPU activity 消失，说明它更接近 freezer 行为；如果随后出现 `REASON_LOW_MEMORY`，问题转到 LMK；如果解冻后立刻出现大量 GC 或 allocation stall，要回到 §4.3 的 ART heap 路径看分配压力。

## 版本边界与厂商差异

AOSP 文档给出的公开版本边界如下：Android 11（API 30）及以上支持 cached apps freezer；Android 14（API 34）及以上增加更稳的行为，包括 cached 后约 10 秒冻结、生命周期事件立即解冻、context-registered broadcasts 在 cached 状态下排队，manifest-declared broadcasts 触发立即解冻。[已验证: 官方文档, source.android.com/docs/core/perf/cached-apps-freezer]

`IBinder.addFrozenStateChangeCallback()` 的公开 API reference 标为 API 36。写系统服务或 SDK 侧代码时，不能把这个 API 当作 Android 14 可用能力；Android 14 的 freezer 行为增强与 API 36 的 Binder frozen-state callback 是两条不同版本线。[已验证: 官方文档, developer.android.com/reference/android/os/IBinder]

厂商差异需要单独留口。AOSP 文档也把部分 exemption 称为 implementation details，例如阻塞非 cached 进程的文件锁、`BIND_WAIVE_PRIORITY` 绑定关系等。国内 ROM 还可能叠加自研后台管控、保活白名单、墓碑策略或电量策略。没有实机 trace 或厂商源码时，本节不把这些策略写成 Android 通用行为。[待验证: Pixel 与主流国内 ROM 的 freezer 开关、debounce、白名单和 frozen cgroup 统计差异]

## 小结

Cached App Freezer、ART GC、LMK/lmkd 和 16KB Page Size 分别管四件事：

- Freezer 管 CPU 调度：冻结 cached 进程的线程，降功耗。
- ART GC 管堆内存：根据水位和分配压力回收对象。
- LMK/lmkd 管进程生死：低内存时杀进程保前台。
- 16KB Page Size 管页粒度：影响页表、TLB 和 page fault 开销，但不改变 freezer 语义。

排障时把这四类事件放到同一条时间轴上：先确认 freeze/unfreeze，再看退出原因，再看 GC 和内存回收，最后判断用户感知的“回前台慢”来自解冻延迟、冷启动还是普通资源加载。这个顺序能避免把“退后台后出现 GC”“回前台像冷启动”“内存下降”混成一条没有证据的因果链。
