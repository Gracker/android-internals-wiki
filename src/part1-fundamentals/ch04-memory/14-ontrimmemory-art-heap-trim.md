---
title: "onTrimMemory 回调与 ART Heap Trim"
chapter: "4.14"
status: ready-for-review
drafted_date: "2026-06-29"
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
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java (freeze 前下发 trim, line 1409-1420)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java (setProcessMemoryTrimLevel, line 3748-3772)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java (trim 状态追踪, line 4392/4895)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java (MemoryLimiter 全链路)"
  - type: aosp
    path: "frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp (JNI 层 cgroup 写入)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java (oom_adj 与 trim 协同)"
  - type: research
    path: "DeepResearch/2026-06-25-fair-memory-trim-android17-source.md"
  - type: research
    path: "DeepResearch/2026-06-28-android17-memorylimiter-procstate-polling-statsd.md"
tags: [memory, onTrimMemory, memory-management, android17, aosp, ComponentCallbacks2, CachedAppOptimizer, MemoryLimiter, cgroup]
related_chapters: ["4.3", "4.4", "4.11", "4.13", "10.4", "23.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-29"
gap_source: "素材驱动/AOSP结构"
pipeline_stage: ready-for-review
task6_state: pending-verification
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch04-memory/4.49-android17-trim-memory-api-evolution.md"
---

# 4.14 onTrimMemory 回调与 ART Heap Trim

## 先看范围与结论

- Android 17 常规向应用发送的 level 只剩 `UI_HIDDEN(20)` 与 `BACKGROUND(40)`。
- `UI_HIDDEN` 由 `system_server` 的 `AppProfiler` 发送；`BACKGROUND` 由 `CachedAppOptimizer` 在安排 cached app freeze 前发送。
- lmkd、MemoryLimiter 与 kernel reclaim 都不直接调用应用的 `onTrimMemory()`。
- `IApplicationThread` 是 oneway Binder 接口，发送方不等待应用完成；应用回调最终在主线程执行。
- “公平内存”不是 AOSP 功能名。工程目标应是：单个应用主动缩减可重建资源，同时不把启动、卡顿和后台重建成本转移给用户。

## 1. Android 14～17 的 level 边界

Android 17 的 `ComponentCallbacks2.java` 仍定义七个 level。源码注释说明，应用从 API 34 起不再收到以下五个 level：

- `TRIM_MEMORY_RUNNING_MODERATE`（5）
- `TRIM_MEMORY_RUNNING_LOW`（10）
- `TRIM_MEMORY_RUNNING_CRITICAL`（15）
- `TRIM_MEMORY_MODERATE`（60）
- `TRIM_MEMORY_COMPLETE`（80）

这些常量在 Android 17 源码中带有 `@Deprecated`，但常量和 `onTrimMemory(int)` 方法仍然存在。正常 AOSP 发送路径集中在：

- `TRIM_MEMORY_UI_HIDDEN`（20）：进程此前显示过 UI，随后进入后台；
- `TRIM_MEMORY_BACKGROUND`（40）：cached 进程进入可冻结、可终止范围。

级别数值允许未来插入中间状态，应用应按 `>=` 比较。旧系统、厂商代码或 shell 测试仍可能传入其他数值，兼容分支可以保留，但 Android 17 的资源治理不能依赖旧 level 到达。

## 2. `UI_HIDDEN` 的真实发送路径

`UI_HIDDEN` 不是 `ActivityThread.handleStopActivity()` 在应用进程内同步发出的。Android 17 的发送者位于 `system_server`：

```text
AppProfiler.updateLowMemStateLSP()
  → 遍历 LRU 进程
  → 检查 proc state 与 pendingUiClean
  → IApplicationThread.scheduleTrimMemory(TRIM_MEMORY_UI_HIDDEN)
```

`AppProfiler` 只对已经进入后台、此前又有 UI 待清理的进程发送一次提示，并清除 `pendingUiClean`。这解释了两个现象：

1. 某个 Activity 执行 `onStop()`，不等于同一调用栈内立即收到 trim；
2. 多 Activity、画中画、前台 Service 等复杂状态下，回调时机取决于进程状态与 `pendingUiClean`，不能用单个 Activity 生命周期机械推导。

应用可以把 level 20 当作“可见界面资源可以缩减”的信号。适合释放的对象包括全尺寸预览、只服务于当前页面的预加载结果、不可见动画资源和可快速重建的 UI cache。正在播放的音频、下载任务或用户可感知的后台工作不能仅因 UI 隐藏就中止。

## 3. `BACKGROUND` 与 freezer 的关系

`CachedAppOptimizer.freezeAppAsyncInternalLSP()` 检查目标进程已经处于 cached adj 后，执行：

```text
IApplicationThread.scheduleTrimMemory(TRIM_MEMORY_BACKGROUND)
mFreezeHandler.sendMessageDelayed(SET_FROZEN_PROCESS_MSG, delayMillis)
```

代码先发送 trim，再安排 freeze 消息，但二者之间没有完成确认。目标应用接收 Binder 事务、主线程处理 Runnable 和系统 freeze handler 分属不同调度上下文。以下结论更安全：

- 系统尽力在 freeze 前给应用一次缩减缓存的机会；
- 发送方不会等待 `onTrimMemory()` 返回；
- 主线程拥塞时，回调可能很晚才运行；
- 进程被冻结后，尚未执行的工作只能等解冻；
- 应用拿不到稳定的“剩余处理时间”。

lmkd 不在这条路径中。lmkd 根据全局 PSI、watermark、swap、thrashing 与 `oom_score_adj` 选择进程并发送 kill，不会先调用 `scheduleTrimMemory()`。应用也可能在没有新 trim 的情况下被终止。

## 4. Binder 到主线程的分发

`IApplicationThread.aidl` 把整个接口声明为 `oneway`。`system_server` 调用 `scheduleTrimMemory(level)` 时不等待应用处理完成；oneway 只表示异步调用，不代表事务队列容量无限或消息会在 freeze 前执行。

应用进程收到事务后，`ActivityThread.ApplicationThread.scheduleTrimMemory()` 构造一个可回收的 `Runnable`，优先投递到主线程 Choreographer 的 `CALLBACK_COMMIT` 阶段：

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

这段代码减少清理工作打断当前帧关键阶段的概率。它没有把工作移到后台线程；回调中的同步 I/O、锁等待、大量对象遍历和压缩仍会阻塞主线程。

## 5. `handleTrimMemory()` 的准确行为

Android 17 的处理顺序是：

1. 创建 `trimMemory: <level>` trace slice。
2. 若 `skip_bg_mem_trim_on_fg_app` 开启，当前进程仍为重要前台，且 level 至少为 40，直接返回。
3. 收集当前进程中的组件回调。
4. 调用每个组件的 `onTrimMemory(level)`。
5. 正常路径最终调用 `WindowManagerGlobal.trimMemory(level)`。

第 2 步的早退也会跳过 `WindowManagerGlobal.trimMemory()`，但 `finally` 仍会结束 trace。因此，看到 `trimMemory: 40` slice 不足以证明应用组件收到回调。

`collectComponentCallbacks(true)` 的源码顺序是：

1. `Application`
2. 尚未结束的 `Activity`
3. `Service`
4. 本地 `ContentProvider`

Activity 会按 `mActivities` 的逆序收集，具体页面之间不要依赖稳定次序。`ContextWrapper` 不是这里单独收集的回调对象。

`WindowManagerGlobal.trimMemory()` 直接调用 `ThreadedRenderer.trimMemory(level)`。它表示缩减应用进程图形栈的 cache trim，不能扩大成“直接清理 SurfaceFlinger 的 BufferQueue 空闲 buffer”。

## 6. 应用回调怎样写

以下实现先判断较高 level，并让清理动作保持低成本：

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

这个示例只释放当前进程拥有、并且可以重建的资源。项目实现还要遵守以下规则：

- 用户编辑、数据库事务和任务进度按业务时机持久化，不等待 trim；
- 不主动调用 `System.gc()`；
- 不在回调中同步写盘或等待网络；
- 不直接 recycle 仍可能被 View、renderer 或其他线程使用的 Bitmap；
- cache 在常态运行时就要有容量上限；
- 清理后记录条目数和估算字节，方便验证收益。

`onTrimMemory()` 释放的是引用与产品 cache。它不会直接触发 ART GC、heap compaction、kernel direct reclaim 或 kswapd。ART 会按分配压力、heap footprint 与进程状态独立安排 GC；GC 完成后可以另行安排 HeapTrimTask。

### ART Heap Trim 是另一条异步链

`ActivityThread.handleTrimMemory()` 没有调用 `VMRuntime.requestConcurrentGC()`、`requestHeapTrim()` 或 `trimHeap()`。应用在回调里断开强引用后，对象只是变成可回收；GC 何时发生仍由 ART 的分配压力、目标 footprint、collector 与进程状态决定。

ART 的 heap trim 通常从 GC 完成处发起：

```text
Heap::CollectGarbageInternal()
  → Heap::RequestTrim()
  → HeapTrimTask（Android 17 默认等待 5 秒）
  → Heap::Trim()
  → TrimIndirectReferenceTables()
  → TrimSpaces()
  → ArenaPool::TrimMaps()
```

`RequestTrim()` 会合并重复请求；`Heap::Trim()` 负责把分配器中可归还的页面、JNI 引用表和部分 runtime arena 交还或标记给内核。它不等于 “Major GC + compaction”，也不按 trim level 选择 young/old generation。

进程前后台变化还会沿 `ActivityThread.updateProcessState()` → `VMRuntime.updateProcessState()` 影响 ART collector transition 与 heap footprint。它可能和 `onTrimMemory(20/40)` 时间接近，但不是同一次调用。另一个严重低内存入口 `handleLowMemory()` 会处理 `onLowMemory()` 并请求 GC，也不能套用到 `handleTrimMemory()`。

## 7. lmkd、freezer 与 MemoryLimiter 要分开看

| 子系统 | 主要输入 | 主要动作 | 向 App 发送 trim |
| --- | --- | --- | --- |
| `AppProfiler` | proc state、`pendingUiClean` | 发送 `UI_HIDDEN` | 是 |
| `CachedAppOptimizer` | cached/freezer 状态 | 发送 `BACKGROUND`、安排 freeze | 是 |
| lmkd | 全局 PSI、watermark、swap、thrashing、adj | 选择进程并 kill | 否 |
| MemoryLimiter | proc state、cgroup usage/events、配置值 | 写限制、检查越界、诊断/kill | 否 |
| kernel reclaim | watermark、分配与 cgroup 压力 | 回收、换出、节流 | 否 |

MemoryLimiter 的 Android 17 执行代码配置 `memory.high` 与 `memory.swap.max`，没有配置 `memory.swap.high`。阈值来自平台配置，不存在适用于所有设备和进程的固定 2GB/4GB 配额。

首次 `memory.high` 事件、red-zone 检查和后续 kill 属于 MemoryLimiter 自己的状态机。它没有为目标应用派发专属 `onTrimMemory()`；30 秒的 profiling/kill 延迟也不是应用可依赖的自救窗口。源码与监控方法见 [4.13 Android 17 MemoryLimiter：memcg 限制与超限诊断](13-android17-memorylimiter.md)。

“公平运行内存”可以作为产品目标，不能写成 Android 17 的公共 API。公平性的证据应包括目标 App 释放量、恢复成本、其他 App 留存、系统 kill 与交互响应，不能只看本进程 PSS。

## 8. 多进程与后台组件

每个 Android 进程拥有独立的 `ActivityThread` 和组件集合：

- 主进程收到 level 20，不会自动转发到 `:remote` 进程；
- 远程 Service 进程没有 UI 时，通常没有 `pendingUiClean`，不能假设它会收到 level 20；
- Service 进程只有进入 cached/freezer 条件后，才可能沿 freezer 路径收到 level 40；
- isolated 进程也不能依赖宿主进程替它清理。

多进程 App 应为每个进程建立自己的内存预算。公共数据如果通过文件映射、共享内存或 DMA-BUF 使用，还要分别观察每个进程的 PSS/RSS 和资源所有权；“多个 cgroup 一定重复计费”需要结合具体 controller 与映射类型验证，不能一概而论。

## 9. 手动测试

### 9.1 注入回调

Android 17 shell 提供：

```bash
adb shell am send-trim-memory com.example.app HIDDEN
adb shell am send-trim-memory com.example.app BACKGROUND
```

目标进程必须处于允许发送该后台 level 的状态；`ActivityManagerService.setProcessMemoryTrimLevel()` 会拒绝向重要前台进程注入 level 20 及以上。

shell 还接受 legacy level 和原始整数。这只验证应用兼容分支，不能证明正常系统路径会再次发送旧 level。

### 9.2 Trace

查询 App 进程的 trim slice，可以使用：

```sql
SELECT ts, dur, name, track_id
FROM slice
WHERE name GLOB 'trimMemory: *'
ORDER BY ts;
```

系统 trace 只说明 `handleTrimMemory()` 开始和结束。为了确认组件代码执行，应用还应记录：

- 回调 level 与进程名；
- cache 清理前后的条目和字节；
- 自定义 trace slice；
- 清理耗时；
- 回到前台后的重建耗时。

不应统一规定“超过 16ms 就失败”或“每小时 3 次就告警”。不同资源的清理成本和设备帧率不同，阈值应由目标场景数据决定；主线程回调越短越好。

### 9.3 系统侧状态

`dumpsys activity processes` 可显示进程记录中的 `trimMemoryLevel`、proc state 与 adj。应用可用 `ActivityManager.getMyMemoryState()` 读取 `lastTrimLevel`。

PSS/RSS 测量应在同一设备状态下重复多轮，并按 Java、native、graphics、file-backed 与 swap 分类。一次 PSS 下降不等于 trim 已把物理页交还系统，也不能证明 MemoryLimiter 或 lmkd 触发。

## 10. 常见错误

| 错误说法 | Android 17 源码结论 |
| --- | --- |
| `Activity#onStop()` 同步调用 level 20 | `AppProfiler` 根据进程状态与 `pendingUiClean` 经 Binder 发送 |
| lmkd 在 kill 前发送 level 40 | level 40 来自 `CachedAppOptimizer` 的 freezer 路径 |
| oneway Binder 不占缓冲且保证到达 | 发送方不等待完成；队列、调度与 freeze 仍会影响执行时机 |
| 回调组件顺序是 Application→Provider→Activity→Service | 源码顺序是 Application→Activity→Service→Provider |
| trim 会触发 Major GC + compaction | `handleTrimMemory()` 没有调用 VMRuntime 或 GC |
| MemoryLimiter 使用 `memory.swap.high` | 执行代码使用 `memory.swap.max` |
| 游戏/播放器有统一 2GB 或 4GB 配额 | 阈值由平台配置与进程状态决定 |
| 缺少 trace slice表示消息丢失 | 还可能是未发送、进程状态不符、抓取配置不足或时间窗不匹配 |

## 11. 复核清单

- [ ] 只把 level 20/40 当作 Android 17 的常规应用通知；
- [ ] 把 `AppProfiler`、freezer、lmkd 与 MemoryLimiter 分开解释；
- [ ] 不依赖回调保存关键状态或预告进程死亡；
- [ ] 回调只做主线程可承受的可重建资源清理；
- [ ] 多进程分别设置预算与回调；
- [ ] 用 App 自定义证据确认回调执行，而非只看 framework trace；
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

平台源码以 `android-17.0.0_r1` 为锚点。涉及 cgroup 语义时，以 kernel `android17-6.18-2026-06_r6` 的 `Documentation/admin-guide/cgroup-v2.rst` 与 `mm/memcontrol.c` 为准。
