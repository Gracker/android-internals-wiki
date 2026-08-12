---
title: "AMS 双锁架构与 system_server 锁竞争优化"
chapter: "1.25"
section: "1.25"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [lock-contention, system-server, ams, process-record, dual-lock, LOSP, LSP, OomAdjuster, performance]
related_chapters: ["1.14", "1.3", "1.8", "5.8"]
last_verified: "2026-08-12"
last_source_verified_at: "2026-08-12"
last_verified_against: "AOSP android-17.0.0_r1 frameworks/base ActivityManagerService/ActivityManagerProcLock/ActivityManagerGlobalLock/ProcessList/CachedAppOptimizer/OomAdjuster/ThreadPriorityBooster/PerfettoCategories/LoadedApk/IApplicationThread; Perfetto android.monitor_contention stdlib docs"
confidence: high
sources:
  - type: research
    path: "DeepResearch/2026-06-10-lru-lock-optimization.md"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java (android-12.0.0_r1, android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/am/ActivityManagerProcLock.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/am/ActivityManagerGlobalLock.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/am/ProcessList.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/am/psc/OomAdjuster.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/services/core/java/com/android/server/ThreadPriorityBooster.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/core/java/android/os/PerfettoCategories.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/core/java/android/app/LoadedApk.java (android-17.0.0_r1)"
  - type: aosp
    path: "platform/frameworks/base/core/java/android/app/IApplicationThread.aidl (android-17.0.0_r1)"
  - type: official-docs
    path: "https://perfetto.dev/docs/analysis/stdlib-docs#android-monitor_contention"
---

# 1.25 AMS 双锁架构与 system_server 锁竞争优化

`ActivityManagerService`（AMS）处在 Android 进程管理的中心。进程启动和退出、组件状态、LRU 次序、OOM adj、应用冻结等操作都可能在 `system_server` 内并发发生。只用一把大锁保护这些状态，代码容易保持一致，却会让互不修改同一组数据的线程排在同一个等待队列中。

Android 12 引入 `mProcLock`，并保留原有的 `mGlobalLock`。Android 17 仍采用这套双锁设计。它的边界很明确：双锁扩大了部分进程状态读取和独立操作的并发空间，但没有把 AMS 的所有进程管理操作改成只持 `mProcLock`。OOM adj 全量计算、LRU 写入等关键路径仍会同时持有两把锁。

## 1. 从单锁到双锁

Android 11 的 AMS 尚未定义 `ENABLE_PROC_LOCK`、`mProcLock` 和 `ActivityManagerProcLock`。当时进程管理代码广泛依赖 AMS 对象自身的 monitor，也就是后来的 `mGlobalLock`。

Android 12 的 `ActivityManagerService` 首次给出完整的双锁骨架：

```java
final ActivityManagerGlobalLock mGlobalLock = ActivityManagerService.this;

private static final boolean ENABLE_PROC_LOCK = true;

final ActivityManagerGlobalLock mProcLock = ENABLE_PROC_LOCK
        ? new ActivityManagerProcLock() : mGlobalLock;
```

这段代码说明了两件事：

1. `mGlobalLock` 仍然是 `ActivityManagerService.this`，旧代码中的 `synchronized (mService)`、`synchronized (this)` 与围绕全局锁建立的约束不会凭空消失。
2. `ENABLE_PROC_LOCK` 为 `false` 时，`mProcLock` 会指回 `mGlobalLock`。这种写法让迁移过程可以维持相同的接口和方法命名；Android 12 与 Android 17 的发布源码中该开关均为 `true`。

双锁要解决的是锁保护范围过宽，不保证每条路径都更快。一次操作若要同时读取组件关系并修改进程状态，仍然需要两把锁；持锁期间若执行慢 Binder 调用、文件 I/O 或大量计算，也仍会造成竞争。

## 2. 两把锁分别保护什么

Android 17 在 `ActivityManagerService` 的注释中给出了边界：Service、Provider、Broadcast 等核心组件仍主要由 `mGlobalLock` 保护；进程管理状态逐步迁移到 `mProcLock`。源码中的锁要求如下。

| 锁要求 | 典型数据或操作 | 说明 |
|---|---|---|
| 只持 `mGlobalLock` | Service、Provider、Broadcast 的大量核心状态 | 方法常使用 `Locked` 后缀，不能在已经持有 `mProcLock` 时反向获取 |
| 只持 `mProcLock` | 部分进程状态读取、应用冻结/压缩队列、向运行进程分发某些通知 | 这类路径不需要访问由全局锁单独保护的组件关系 |
| 两把锁都持有 | LRU 列表写入、OOM adj 计算及提交、跨组件关系更新进程状态 | 获取顺序固定为 `mGlobalLock` → `mProcLock` |
| 任一把锁均可读取 | 使用 `@CompositeRWLock` 保护的数据，例如 `mLruProcesses` | “任一把锁可读”不表示任一把锁都可写 |

这里的“进程状态”也不能简单理解成 `ProcessRecord` 的全部字段。`ProcessRecord` 聚合了 Activity、Service、Provider、错误状态、优化状态等多个子记录，各字段的锁注解并不相同。判断某段代码能否只持 `mProcLock`，应查看字段与方法上的 `@GuardedBy`、`@CompositeRWLock`，不能只看对象类型。

## 3. `@CompositeRWLock`：任一锁读、两把锁写

`ProcessList` 中的 LRU 列表是双锁语义最清楚的例子：

```java
@CompositeRWLock({"mService", "mProcLock"})
private final ArrayList<ProcessRecord> mLruProcesses = new ArrayList<>();

@CompositeRWLock({"mService", "mProcLock"})
private int mLruProcessActivityStart = 0;

@CompositeRWLock({"mService", "mProcLock"})
private int mLruProcessServiceStart = 0;
```

`@CompositeRWLock` 表达的是一套组合读写规则：

- 读取时，持有 `mService`（即 AMS 全局锁）或 `mProcLock` 中的任意一把即可。
- 写入时，两把锁都要持有。

因此，下面的遍历方法可以由只持 `mProcLock` 的调用方使用：

```java
@GuardedBy(anyOf = {"mService", "mProcLock"})
void forEachLruProcessesLOSP(boolean iterateForward,
        @NonNull Consumer<ProcessRecord> callback) {
    if (iterateForward) {
        for (int i = 0, size = mLruProcesses.size(); i < size; i++) {
            callback.accept(mLruProcesses.get(i));
        }
    } else {
        for (int i = mLruProcesses.size() - 1; i >= 0; i--) {
            callback.accept(mLruProcesses.get(i));
        }
    }
}
```

这段方法只遍历列表，没有改变元素和分区索引。调用方仍要持有两把锁中的一把，并且回调不能破坏该锁对应的约束。

LRU 写路径的要求更严格。Android 17 的 `updateLruProcessLocked()` 已由 `@GuardedBy("mService")` 约束，随后在内部获取 `mProcLock`，再调用 `updateLruProcessLSP()`：

```java
@GuardedBy("mService")
public void updateLruProcessLocked(ProcessRecordInternal appInternal,
        boolean activityChange, ProcessRecordInternal clientInternal) {
    // 省略无需写入时的快速返回
    synchronized (mProcLock) {
        updateLruProcessLSP(app, client, hasActivity, hasService);
    }
}

@GuardedBy({"mService", "mProcLock"})
private void updateLruProcessLSP(...) {
    // 修改 mLruProcesses 和分区索引
}
```

双锁允许 LRU 读取避开全局锁，但 LRU 排序、插入和删除仍要同时保护列表结构与关联状态。

## 4. 方法后缀是锁契约的速记

AMS 进程管理代码用方法名后缀提示调用方需要持有什么锁。

| 后缀 | 源码中的含义 | 调用要求 |
|---|---|---|
| `LOSP` | Locked with any Of global am Service or Process lock | `mGlobalLock` 或 `mProcLock` 任一把 |
| `LSP` | Locked with both global am Service and Process lock | 两把锁都要持有 |
| `Locked` | Locked with global AM service lock alone | 通常要求 `mGlobalLock`；仍需结合注解确认 |
| `LPr` | Locked with Process lock alone | 要求 `mProcLock` |

后缀是维护约定，字段访问器等方法不一定都带后缀。代码审查时应按“注解优先、后缀辅助、调用点复核”的顺序判断。

例如，`updateOomAdjLocked()` 的名称只提示入口已经持有全局锁。它进入方法后还会获取 `mProcLock`，再调用 `updateOomAdjLSP()`。仅凭 `Locked` 后缀推断整个调用过程只使用一把锁，会漏掉内部的嵌套锁。

## 5. 锁顺序：先全局锁，再进程锁

Android 17 在 `mProcLock` 的字段注释中明确要求：需要两把锁时，先获取 `mGlobalLock`，再获取 `mProcLock`。Service、Provider、Broadcast 等代码仍可能只由全局锁保护，因此持有进程锁后再请求全局锁会制造 AB-BA 死锁条件。

符合顺序的写法如下：

```java
synchronized (mGlobalLock) {
    // 读取或修改全局组件状态
    synchronized (mProcLock) {
        // 修改需要组合写锁保护的进程状态
    }
}
```

退出嵌套块时按相反顺序释放锁。这是 Java `synchronized` 的自然行为。

下面的顺序不允许出现在可达路径中：

```java
synchronized (mProcLock) {
    synchronized (mGlobalLock) { // 锁顺序反转
        // ...
    }
}
```

只持 `mProcLock` 的方法若发现还需要全局状态，通常应退出当前临界区，再从满足全局锁契约的入口重新组织操作。不能为了少改代码而在原地反向加锁。

## 6. 三条代表性路径

### 6.1 OOM adj：Android 17 仍同时持有两把锁

Android 17 已将 OOM 调整实现移到 `com.android.server.am.psc.OomAdjuster`。全量更新入口的锁关系如下：

```java
@GuardedBy("mServiceLock")
void updateOomAdjLocked(@OomAdjReason int oomAdjReason) {
    synchronized (mProcLock) {
        updateOomAdjLSP(oomAdjReason);
    }
}

@GuardedBy({"mServiceLock", "mProcLock"})
private void updateOomAdjLSP(@OomAdjReason int oomAdjReason) {
    performUpdateOomAdjLSP(oomAdjReason);
}
```

`performUpdateOomAdjLSP()`、`updateAndTrimProcessLSP()` 等后续方法也标注为同时受两把锁保护。双锁没有让一次完整的 OOM adj 更新与所有 AMS 全局操作并行。它提供的收益之一，是让只需读取或修改独立进程状态的其他路径可以绕开全局锁等待。

分析性能时必须保留这项边界。若 trace 显示 OOM adj 期间 `mGlobalLock` 长时间被持有，不能因双锁已经启用就排除 OOM adj；仍需查看持锁线程在计算、Binder 调用、内核调度和 I/O 上分别花了多少时间。

### 6.2 时区更新：只用进程锁遍历 LRU

时区变化需要通知正在运行的应用进程。Android 17 的 AMS Handler 只获取 `mProcLock`，然后通过 `forEachLruProcessesLOSP()` 读取 LRU 列表：

```java
case UPDATE_TIME_ZONE: {
    synchronized (mProcLock) {
        mProcessList.forEachLruProcessesLOSP(false, app -> {
            final IApplicationThread thread = app.getThread();
            if (thread != null) {
                try {
                    thread.updateTimeZone();
                } catch (RemoteException ignored) {
                }
            }
        });
    }
} break;
```

该路径展示了 `LOSP` 的作用：读取 LRU 不必占用 `mGlobalLock`。风险在于，代码会在 `mProcLock` 内向多个应用进程发起 Binder 调用。即使这些调用通常是单向分发，也要通过 trace 判断临界区是否因调度、Binder 驱动拥塞或目标进程状态而拉长。

### 6.3 CachedAppOptimizer：进程锁保护冻结与压缩队列

Android 17 的 `CachedAppOptimizer` 使用 `mProcLock` 保护 `mPendingCompactionProcesses`、`mFrozenProcesses` 和冻结器相关状态。典型代码会在锁内复制 PID 或移出一个待压缩进程，再在锁外执行较慢的工作。

这种写法体现了缩短临界区的常用方法：锁内完成一致性检查和最小状态变更，耗时操作使用局部快照在锁外继续。能否这样处理取决于对象生命周期与并发修改规则，不能机械地把现有代码移出锁外。

## 7. `ActivityManagerProcLock` 与线程优先级提升

`ActivityManagerProcLock` 是一个没有字段和方法的标记类：

```java
final class ActivityManagerProcLock implements ActivityManagerGlobalLock {
}
```

源码注释说明，这个独立类型可让 CPU booster 识别临界区。Android 17 中可以直接验证的实现是 `ThreadPriorityBooster`：AMS 分别为全局锁和进程锁创建一个 booster，目标优先级都是 `THREAD_PRIORITY_FOREGROUND`。

`ThreadPriorityBooster.boost()` 会读取当前线程的 Linux nice 值；若当前优先级低于目标值，便通过 `setThreadPriority()` 提升当前线程。嵌套临界区由线程局部计数器记录，最外层退出时恢复原优先级。

这段源码支持的结论有三点：

- 提升对象是当前持锁线程，不是整个 `system_server` 进程中的所有线程。
- 调整的是 Linux nice 优先级，目标为前台线程优先级。
- 退出最外层临界区后恢复先前优先级。

它不能证明系统会为该锁直接提高 CPU 频率，也不能证明持锁线程会切换到 `SCHED_FIFO`。AMS 中的 `mUseFifoUiScheduling` 面向 UI 线程和 RenderThread，是另一套调度策略，不应与 `mProcLock` 的 booster 混为一谈。

优先级提升只能降低持锁线程因普通优先级竞争而延迟的概率。临界区内若有慢 Binder、缺页、I/O 或过量计算，booster 不会消除这些等待。

## 8. 用 Perfetto 区分等待时间与持锁时间

锁问题至少涉及等待线程和持锁线程。只看到 Binder 线程处于 `futex` 等待，无法确定哪把锁造成延迟，也无法判断持锁线程为何没有及时释放。

Android 17 的 `ActivityManagerService` 定义了 `big_locks` 类别下的四组事件：

| 锁 | 尝试获取 | 已获取并持有 |
|---|---|---|
| `mGlobalLock` | `ams_lock_acquire` | `ams_lock_held` |
| `mProcLock` | `proc_lock_acquire` | `proc_lock_held` |

这些事件受 `android.os.Flags.perfettoSdkTracingV3()` 控制。分析某台设备前，应确认构建是否启用相应特性、trace 配置是否采集 `big_locks` 类别，以及结果中是否出现这些 slice。源码定义了事件，不代表每份 trace 都包含它们。

如果事件存在，可以先用下面的查询列出 `system_server` 中的持锁区间。它的用途是找到长持锁段，并定位到具体线程：

```sql
SELECT
  s.ts,
  s.dur / 1e6 AS dur_ms,
  s.name,
  t.tid,
  t.name AS thread_name
FROM slice s
JOIN thread_track tt ON tt.id = s.track_id
JOIN thread t USING (utid)
JOIN process p USING (upid)
WHERE p.name = 'system_server'
  AND s.category = 'big_locks'
  AND s.name IN ('ams_lock_held', 'proc_lock_held')
ORDER BY s.dur DESC;
```

`*_lock_acquire` 是尝试获取时发出的瞬时事件，`*_lock_held` 是成功获取后开始的区间。二者位于同一线程轨道时，可以在界面中直接观察等待与持锁的先后关系。查询结果为空时，再使用 ART monitor contention 数据作为通用证据。

Perfetto 当前标准库的模块名为 `android.monitor_contention`，表名为 `android_monitor_contention`。下面的查询使用现有列名列出 `system_server` 的 Java monitor 竞争：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  dur / 1e6 AS blocked_ms,
  blocked_thread_name,
  blocking_thread_name,
  lock_name,
  short_blocked_method,
  short_blocking_method,
  blocked_src,
  blocking_src,
  waiter_count
FROM android_monitor_contention
WHERE process_name = 'system_server'
  AND (
    lock_name GLOB '*ActivityManager*'
    OR short_blocked_method GLOB '*ActivityManager*'
    OR short_blocked_method GLOB '*OomAdjuster*'
    OR short_blocking_method GLOB '*ActivityManager*'
    OR short_blocking_method GLOB '*OomAdjuster*'
    OR short_blocking_method GLOB '*ProcessList*'
  )
ORDER BY dur DESC
LIMIT 50;
```

`dur` 是等待线程被 monitor 阻塞的墙钟时间。`blocking_thread_name` 与 `short_blocking_method` 指向持锁方，`blocked_thread_name` 与 `short_blocked_method` 指向等待方。`lock_name` 可用时，优先用它区分 `ActivityManagerService` 对象和 `ActivityManagerProcLock` 对象；类名缺失时，再结合源码位置与 `big_locks` 事件判断。仅凭方法属于 `OomAdjuster` 或 `ProcessList` 猜测锁类型并不可靠，因为这些类中存在同时持有两把锁的路径。

## 9. 一次可复用的诊断顺序

遇到 Activity 启动、Service 调用或进程状态更新偶发变慢时，可以按以下顺序分析：

1. 在问题时间窗内找到等待线程，确认延迟来自 monitor contention，而非 Binder reply、CPU runnable、I/O 或其他原因。
2. 查看 `big_locks` 事件或 `android_monitor_contention.lock_name`，区分全局锁与进程锁。
3. 找到持锁线程及其持锁方法。等待方的调用栈只能说明谁受影响，持锁方才说明临界区为何变长。
4. 把持锁区间与线程状态、Binder transaction、调度和 I/O slice 对齐。持锁线程可能在运行，也可能持锁等待另一个资源。
5. 检查同一时段的 `waiter_count` 和其他等待者。一次长等待与许多中等等待造成的总影响不同。
6. 回到对应 Android 版本的源码，确认锁注解、获取顺序和版本差异，再决定修改位置。

`adb shell dumpsys activity processes` 可以查看当时的进程、adj 与 proc state，但它是状态快照，不能证明某个 adj 变化导致了锁竞争。复现性能问题时，应把 dumpsys 用作背景信息，并通过 trace 判断时间关系与因果链。

## 10. 应用侧能做什么

普通应用不能直接选择 AMS 使用哪把锁，也无法从一次系统 API 调用推断服务端当时的持锁情况。应用侧能控制调用时机、频率和结果时效要求。

- 不要在每帧、滚动回调或高频定时器中同步查询系统进程与内存状态。一次调用可能很快，密集 IPC 仍会增加客户端和 `system_server` 的调度负担。
- 缓存前要确认数据允许短时间过期。进程列表、内存压力和组件状态的时效要求不同，不能统一设置一个缓存时间。
- 将与绘制无关的系统查询移出主线程或关键交互时段。异步执行只能减少应用主线程阻塞，服务端成本仍然存在，因此还要控制调用次数。
- `ActivityManager.getRunningAppProcesses()` 是进程可见性查询，不会因为“读取列表”就刷新 LRU。`UsageStatsManager` 提供应用使用记录，语义不同，不能当作进程列表的通用替代品。
- `ServiceConnection.onServiceConnected()` 等回调在应用进程中按 `ServiceDispatcher` 配置的执行器或 Handler 分发。回调里发起新的系统调用可能形成新的同步 IPC，但不能据此声称 system_server 仍持有原来的 AMS 锁。

平台代码的优化需要遵守更严格的条件：缩短锁内工作、避免持锁进行不可控的跨进程调用、在安全时复制快照后释放锁，并用相同负载的 trace 验证等待时间和持锁时间。任何移锁操作都要先证明对象生命周期与组合写锁规则仍成立。

## 11. 版本边界

| 版本 | 双锁状态 | 阅读源码时的重点 |
|---|---|---|
| Android 11 及更早 | 没有当前这套 `mProcLock` 双锁骨架 | 不要把 Android 12 之后的 LOSP/LSP 契约套用到旧分支 |
| Android 12 / API 31 | 引入并启用 `mProcLock`，确立组合读写锁和锁顺序 | 迁移初期仍有大量全局锁路径 |
| Android 13—16 | 进程状态、OOM 调整、冻结与统计代码持续采用相关约定 | 具体字段和方法位置随版本变化 |
| Android 17 / API 37 | 双锁继续启用；OOM 调整位于 `am.psc`；定义 `big_locks` Perfetto 事件 | 以 `android-17.0.0_r1` 的注解、调用点和 trace 特性为准 |

## 12. 小结

AMS 双锁的核心是明确状态所有权，并给读写操作建立可检查的锁契约：部分组合数据允许持任一把锁读取，写入必须同时持有两把锁；需要嵌套时固定按全局锁到进程锁的顺序获取。

它没有消除 AMS 大临界区。Android 17 的 OOM adj 和 LRU 写入仍会同时持有两把锁，冻结与部分通知路径才可能只使用 `mProcLock`。性能分析要分别测量等待时间和持锁时间，再检查持锁线程在做什么。这样才能把“看到 futex 等待”推进到可验证的源码结论。

## 参考资料

- [Android 12 `ActivityManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-12.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [Android 17 `ActivityManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [Android 17 `ActivityManagerProcLock.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerProcLock.java)
- [Android 17 `ActivityManagerGlobalLock.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerGlobalLock.java)
- [Android 17 `ProcessList.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [Android 17 `OomAdjuster.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/psc/OomAdjuster.java)
- [Android 17 `CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [Android 17 `ThreadPriorityBooster.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/ThreadPriorityBooster.java)
- [Android 17 `PerfettoCategories.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerfettoCategories.java)
- [Android 17 `LoadedApk.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/LoadedApk.java)
- [Perfetto SQL 标准库：`android.monitor_contention`](https://perfetto.dev/docs/analysis/stdlib-docs#android-monitor_contention)
- [Perfetto Android trace 分析示例](https://perfetto.dev/docs/analysis/common-queries)
