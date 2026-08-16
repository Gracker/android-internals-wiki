---
title: "onTrimMemory 回调与 ART Heap Trim"
chapter: "4.14"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-29"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java (TRIM_MEMORY 等级定义, line 99-161)"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java (scheduleTrimMemory + handleTrimMemory, line 2289-2304/7868-7894)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (冻结前下发整理回调, line 1409-1420)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java (setProcessMemoryTrimLevel, line 3748-3772)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java (整理级别状态跟踪, line 4392/4895)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java (MemoryLimiter 全链路)"
  - type: aosp
    path: "frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp (JNI 层 cgroup 写入)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java (oom_adj 与内存整理协同)"
  - type: research
    path: "DeepResearch/2026-06-25-fair-memory-trim-android17-source.md"
  - type: research
    path: "DeepResearch/2026-06-28-android17-memorylimiter-procstate-polling-statsd.md"
tags: [memory, onTrimMemory, memory-management, android17, aosp, ComponentCallbacks2, CachedAppOptimizer, MemoryLimiter, cgroup]
related_chapters: ["4.3", "4.4", "4.11", "4.13", "10.4", "23.9"]
pipeline_stage: ready-for-review
task6_state: pending-verification
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch04-memory/4.49-android17-trim-memory-api-evolution.md"
---

# 4.14 onTrimMemory 回调与 ART Heap Trim

## 先看范围与结论

- Android 17 常规向应用发送的内存整理级别（level）只剩 `UI_HIDDEN(20)` 与 `BACKGROUND(40)`。这里的 trim 是请求应用缩减可重建资源，不代表系统已经完成垃圾回收或归还物理页。
- `UI_HIDDEN` 由 `system_server` 的 `AppProfiler` 发送；`BACKGROUND` 由 `CachedAppOptimizer` 在安排缓存进程冻结前发送。
- 低内存终止守护进程 lmkd、MemoryLimiter 与内核页面回收都不直接调用应用的 `onTrimMemory()`。
- `IApplicationThread` 是单向异步（oneway）Binder 接口，发送方不等待应用处理完成；应用回调最终在主线程执行。
- “公平内存”不是 AOSP 功能名。工程目标应是：单个应用主动缩减可重建资源，同时不把启动、卡顿和后台重建成本转移给用户。

## 1. Android 14～17 的回调级别边界

Android 17 的 `ComponentCallbacks2.java` 仍定义七个级别。源码注释说明，应用从 API 34 起不再收到以下五个级别：

- `TRIM_MEMORY_RUNNING_MODERATE`（5）
- `TRIM_MEMORY_RUNNING_LOW`（10）
- `TRIM_MEMORY_RUNNING_CRITICAL`（15）
- `TRIM_MEMORY_MODERATE`（60）
- `TRIM_MEMORY_COMPLETE`（80）

这些常量在 Android 17 源码中带有 `@Deprecated`，但常量和 `onTrimMemory(int)` 方法仍然存在。AOSP 的常规发送路径集中在：

- `TRIM_MEMORY_UI_HIDDEN`（20）：进程此前显示过 UI，随后进入后台；
- `TRIM_MEMORY_BACKGROUND`（40）：缓存进程进入可以冻结或终止的范围。

级别数值允许未来插入中间状态，应用应按 `>=` 比较。旧系统、厂商代码或命令行测试仍可能传入其他数值，兼容分支可以保留，但 Android 17 的资源管理不能依赖旧级别一定会到达。

## 2. `UI_HIDDEN` 的真实发送路径

`UI_HIDDEN` 并非由 `ActivityThread.handleStopActivity()` 在应用进程内同步发出。Android 17 的发送者位于 `system_server`，调用路径如下：

```text
AppProfiler.updateLowMemStateLSP()
  → 遍历 LRU 进程
  → 检查 proc state 与 pendingUiClean
  → IApplicationThread.scheduleTrimMemory(TRIM_MEMORY_UI_HIDDEN)
```

这里的 LRU 是 ActivityManager 按近期活跃程度维护的进程顺序。`AppProfiler` 只对已经进入后台、并带有“UI 等待清理”标记 `pendingUiClean` 的进程发送一次提示，随后清除该标记。这解释了两个现象：

1. 某个 Activity 执行 `onStop()`，不表示同一调用栈会立即收到整理回调；
2. 在多 Activity、画中画、前台 Service 等复杂状态下，回调时机取决于 ActivityManager 的进程状态（proc state）与 `pendingUiClean`，不能只用单个 Activity 的生命周期推导。

应用可以把级别 20 当作“可见界面资源可以缩减”的信号。适合释放的对象包括全尺寸预览、只服务于当前页面的预加载结果、不可见动画资源和可以快速重建的界面缓存。正在播放的音频、下载任务或用户可感知的后台工作，不能仅因界面隐藏就中止。

## 3. `BACKGROUND` 与进程冻结器的关系

`CachedAppOptimizer.freezeAppAsyncInternalLSP()` 确认目标进程已经处于缓存进程的优先级档位（cached adj）后，会执行：

```text
IApplicationThread.scheduleTrimMemory(TRIM_MEMORY_BACKGROUND)
mFreezeHandler.sendMessageDelayed(SET_FROZEN_PROCESS_MSG, delayMillis)
```

代码先发送整理回调，再安排冻结消息，但二者之间没有完成确认。目标应用接收 Binder 事务、主线程执行 `Runnable` 任务，以及系统冻结处理器（freeze handler）处理消息，分属不同的调度上下文。因此，只能得出以下结论：

- 系统会尽量在冻结前给应用一次缩减缓存的机会；
- 发送方不会等待 `onTrimMemory()` 返回；
- 主线程拥塞时，回调可能很晚才运行；
- 进程被冻结后，尚未执行的任务只能等到解冻后继续；
- 应用拿不到稳定的“剩余处理时间”。

lmkd 不在这条路径中。它根据全局压力停顿信息（PSI）、内存水位（watermark）、交换空间、反复换入换出（thrashing）和进程优先级分值 `oom_score_adj` 选择目标并终止进程，不会先调用 `scheduleTrimMemory()`。因此，应用也可能在没有收到新整理回调的情况下被终止。

## 4. Binder 到主线程的分发

`IApplicationThread.aidl` 把整个接口声明为 `oneway`。`system_server` 调用 `scheduleTrimMemory(level)` 时不等待应用处理完成；`oneway` 只表示单向异步调用，不代表 Binder 事务队列容量无限，也不保证消息能在进程冻结前执行。

应用进程收到事务后，`ActivityThread.ApplicationThread.scheduleTrimMemory()` 会构造一个用后归还对象池的 `Runnable`，优先投递到主线程 Choreographer 的 `CALLBACK_COMMIT` 阶段；这是单帧提交接近结束时的回调阶段：

```java
public void scheduleTrimMemory(int level) {
    final Runnable r = PooledLambda.obtainRunnable(
            ActivityThread::handleTrimMemory, ActivityThread.this, level)
            .recycleOnUse();
    Choreographer choreographer = Choreographer.getMainThreadInstance();
    if (choreographer != null) {
        choreographer.postCallback(Choreographer.CALLBACK_COMMIT, r, null);
    } else {
        mH.post(r);
    }
}
```

这段代码降低了清理工作打断当前帧绘制关键阶段的概率。它没有把工作移到后台线程；回调中的同步 I/O、锁等待、大量对象遍历和压缩操作仍会阻塞主线程。

## 5. `handleTrimMemory()` 的准确行为

Android 17 的处理顺序是：

1. 创建名为 `trimMemory: <level>` 的跟踪时间片（trace slice）。
2. 若功能开关 `skip_bg_mem_trim_on_fg_app` 已启用、当前进程仍是重要前台进程，并且级别至少为 40，则直接返回。
3. 收集当前进程中的组件回调。
4. 调用每个组件的 `onTrimMemory(level)`。
5. 正常路径最终调用 `WindowManagerGlobal.trimMemory(level)`。

第 2 步的提前返回也会跳过 `WindowManagerGlobal.trimMemory()`，但 `finally` 仍会结束跟踪。因此，仅看到 `trimMemory: 40` 时间片，不足以证明应用组件确实收到了回调。

`collectComponentCallbacks(true)` 的源码顺序是：

1. `Application`
2. 尚未结束的 `Activity`
3. `Service`
4. 本地 `ContentProvider`

Activity 会按 `mActivities` 的逆序收集，具体页面之间不应依赖稳定次序。`ContextWrapper` 不会在这里被单独收集为回调对象。

`WindowManagerGlobal.trimMemory()` 会直接调用 `ThreadedRenderer.trimMemory(level)`，用于缩减应用进程图形栈的缓存。它不表示系统会直接清理 SurfaceFlinger 中 BufferQueue（图形缓冲区队列）的空闲缓冲区。

## 6. 应用回调怎样写

以下实现先判断数值较大的级别，并把清理成本控制在较低范围：

```kotlin
override fun onTrimMemory(level: Int) {
    super.onTrimMemory(level)

    when {
        level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> {
            decodedPageCache.clear()
            imageCache.trimToFraction(0.25f)
        }
        level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> {
            screenPreloader.cancel()
            fullResolutionPreviewCache.clear()
        }
    }
}
```

这个示例只释放当前进程拥有且可以重建的资源。项目实现还要遵守以下规则：

- 用户编辑、数据库事务和任务进度应按业务时机持久化，不等待整理回调；
- 不主动调用 `System.gc()`；
- 不在回调中同步写盘或等待网络；
- 不直接回收（recycle）仍可能被 View、渲染器或其他线程使用的 Bitmap；
- 缓存在常态运行时就要有容量上限；
- 清理后记录条目数和估算字节，方便验证收益。

`onTrimMemory()` 只是通知应用断开不再需要的引用并缩减业务缓存。它不会直接触发 ART 垃圾回收（GC）、堆规整（heap compaction）、内核直接回收（direct reclaim）或后台回收线程 `kswapd`。ART 会根据分配压力、堆目标大小（heap footprint）与进程状态独立安排 GC；GC 完成后，还可以另行安排 `HeapTrimTask` 归还堆页面。

### ART Heap Trim（堆页归还）是另一条异步链

`ActivityThread.handleTrimMemory()` 没有调用 `VMRuntime.requestConcurrentGC()`、`requestHeapTrim()` 或 `trimHeap()`。应用在回调中断开强引用后，对象只是变为可以回收；GC 何时发生，仍由 ART 的分配压力、堆目标大小、垃圾收集器（collector）和进程状态决定。

ART 的堆页归还通常在 GC 完成后发起，调用链如下：

```text
Heap::CollectGarbageInternal()
  → Heap::RequestTrim()
  → HeapTrimTask（Android 17 默认等待 5 秒）
  → Heap::Trim()
  → TrimIndirectReferenceTables()
  → TrimSpaces()
  → ArenaPool::TrimMaps()
```

`RequestTrim()` 会合并重复请求；`Heap::Trim()` 负责把分配器中可以归还的页面、JNI 引用表和部分运行时内存区（runtime arena）交还给内核，或标记为内核可回收。它不等同于“完整 GC（Major GC）加堆规整”，也不会按整理回调级别选择新生代或老年代（young/old generation）。

进程前后台变化还会沿 `ActivityThread.updateProcessState()` → `VMRuntime.updateProcessState()` 影响 ART 垃圾收集器切换与堆目标大小。它可能与 `onTrimMemory(20/40)` 在相近时间发生，但二者不是同一次调用。另一个严重低内存入口 `handleLowMemory()` 会处理 `onLowMemory()` 并请求 GC，其行为也不能套用到 `handleTrimMemory()`。

## 7. lmkd、进程冻结器与 MemoryLimiter 要分开看

| 子系统 | 主要输入 | 主要动作 | 向应用发送整理回调 |
| --- | --- | --- | --- |
| `AppProfiler` | 进程状态、`pendingUiClean` | 发送 `UI_HIDDEN` | 是 |
| `CachedAppOptimizer` | 缓存/冻结状态 | 发送 `BACKGROUND`、安排冻结 | 是 |
| lmkd | 全局 PSI、内存水位、交换空间、反复换入换出、进程优先级 | 选择并终止进程 | 否 |
| MemoryLimiter | 进程状态、cgroup 用量与事件、配置值 | 写入限制、检查越界、诊断并终止进程 | 否 |
| 内核页面回收 | 内存水位、内存分配与 cgroup 压力 | 回收、换出和节流 | 否 |

MemoryLimiter 的 Android 17 执行代码配置 `memory.high` 与 `memory.swap.max`，没有配置 `memory.swap.high`。阈值来自平台配置，不存在适用于所有设备和进程的固定 2 GB/4 GB 配额。

首次 `memory.high` 事件、红区检查和后续进程终止属于 MemoryLimiter 自己的状态机。它没有为目标应用派发专用的 `onTrimMemory()`；30 秒的性能剖析与终止延迟也不是应用可以依赖的自救窗口。源码与监控方法见 [4.13 Android 17 MemoryLimiter：memcg 限制与超限诊断](13-android17-memorylimiter.md)。

“公平运行内存”可以作为产品目标，不能写成 Android 17 的公共 API。评估公平性时，应同时考察目标应用的内存释放量与恢复成本、其他应用的留存情况、系统终止进程的记录和交互响应，不能只看当前进程的 PSS。

## 8. 多进程与后台组件

每个 Android 进程拥有独立的 `ActivityThread` 和组件集合：

- 主进程收到级别 20，不会自动转发到 `:remote` 进程；
- 远程 Service 进程没有界面时，通常也没有 `pendingUiClean`，不能假设它会收到级别 20；
- Service 进程只有满足缓存和冻结条件后，才可能沿进程冻结器路径收到级别 40；
- 隔离进程（isolated process）也不能依赖宿主进程替它清理资源。

多进程应用应为每个进程建立自己的内存预算。公共数据如果通过文件映射、共享内存或 DMA-BUF 共享缓冲区使用，还要分别观察每个进程的 PSS（按比例分摊共享页后的占用）、RSS（驻留物理内存）和资源所有权。“多个 cgroup 一定重复计费”这一判断，需要结合具体内存控制器与映射类型验证，不能一概而论。

## 9. 手动验证

### 9.1 注入回调

Android 17 的 `adb shell` 提供以下命令，可向目标进程注入整理回调：

```bash
adb shell am send-trim-memory com.example.app HIDDEN
adb shell am send-trim-memory com.example.app BACKGROUND
```

目标进程必须处于允许发送相应后台级别的状态；`ActivityManagerService.setProcessMemoryTrimLevel()` 会拒绝向重要前台进程注入级别 20 及以上的回调。

命令行还接受旧版级别和原始整数。这只能验证应用的兼容分支，不能证明常规系统路径仍会发送旧级别。

### 9.2 性能跟踪

可以用下面的 Perfetto SQL 查询应用进程中的整理回调时间片：

```sql
SELECT ts, dur, name, track_id
FROM slice
WHERE name GLOB 'trimMemory: *'
ORDER BY ts;
```

系统跟踪只能说明 `handleTrimMemory()` 何时开始和结束。为了确认组件代码确实执行，应用还应记录：

- 回调级别与进程名；
- 缓存清理前后的条目数和字节数；
- 自定义跟踪时间片；
- 清理耗时；
- 回到前台后的重建耗时。

不应统一规定“超过 16 ms 就失败”或“每小时 3 次就告警”。不同资源的清理成本和设备帧率不同，阈值应由目标场景数据决定；主线程回调仍应尽可能短。

### 9.3 系统侧状态

`dumpsys activity processes` 可显示进程记录中的 `trimMemoryLevel`、进程状态与优先级分值 `adj`。应用可以通过 `ActivityManager.getMyMemoryState()` 读取 `lastTrimLevel`。

PSS/RSS 测量应在相同设备状态下重复多轮，并按 Java 堆、原生内存、图形内存、文件映射与交换空间分类。一次 PSS 下降不表示整理回调已经把物理页交还系统，也不能证明 MemoryLimiter 或 lmkd 曾经触发。

## 10. 常见错误

| 错误说法 | Android 17 源码结论 |
| --- | --- |
| `Activity#onStop()` 同步调用级别 20 | `AppProfiler` 根据进程状态与 `pendingUiClean` 经 Binder 发送 |
| lmkd 在终止进程前发送级别 40 | 级别 40 来自 `CachedAppOptimizer` 的进程冻结器路径 |
| 单向 Binder 不占缓冲区且保证到达 | 发送方只是不等待完成；队列、调度与进程冻结仍会影响执行时机 |
| 回调组件顺序是 Application→Provider→Activity→Service | 源码顺序是 Application→Activity→Service→Provider |
| 整理回调会触发完整 GC 与堆规整 | `handleTrimMemory()` 没有调用 VMRuntime 或 GC |
| MemoryLimiter 使用 `memory.swap.high` | 执行代码使用 `memory.swap.max` |
| 游戏或播放器有统一的 2 GB/4 GB 配额 | 阈值由平台配置与进程状态决定 |
| 缺少跟踪时间片表示消息丢失 | 也可能是系统未发送、进程状态不符、采集配置不足或时间窗口不匹配 |

## 11. 复核清单

- [ ] 只把级别 20/40 当作 Android 17 的常规应用通知；
- [ ] 把 `AppProfiler`、进程冻结器、lmkd 与 MemoryLimiter 分开解释；
- [ ] 不依赖回调保存关键状态或预告进程死亡；
- [ ] 回调只做主线程可承受的可重建资源清理；
- [ ] 多进程分别设置预算与回调；
- [ ] 用应用自己的日志和跟踪确认回调执行，不能只看 framework 跟踪；
- [ ] 同时验证释放收益与回前台重建成本。

## 12. Android 17 源码索引

- `frameworks/base/core/java/android/content/ComponentCallbacks2.java`
- `frameworks/base/core/java/android/app/IApplicationThread.aidl`
- `frameworks/base/core/java/android/app/ActivityThread.java`
- `frameworks/base/core/java/android/view/WindowManagerGlobal.java`
- `frameworks/base/services/core/java/com/android/server/am/AppProfiler.java`
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`
- `frameworks/base/services/core/java/com/android/server/am/ProcessProfileRecord.java`
- `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`
- `frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp`

平台源码以 `android-17.0.0_r1` 为锚点。涉及 cgroup 语义时，以 Linux 内核 `android17-6.18-2026-06_r6` 中的 `Documentation/admin-guide/cgroup-v2.rst` 与 `mm/memcontrol.c` 为准。
