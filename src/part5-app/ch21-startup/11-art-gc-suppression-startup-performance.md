---
title: "ART GC 抑制与启动性能优化"
chapter: "21.11"
section: "21.11"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [gc-suppression, startup, art-runtime, heap-task-daemon, native-hook, concurrent-gc]
related_chapters: ["1.7", "4.8", "21.1", "21.6", "23.5", "20.13"]
last_verified: "2026-06-05"
last_verified_against: "AOSP android-17.0.0_r1, art/runtime/gc/ + libcore/libart/src/main/java/java/lang/Daemons.java"
confidence: medium
sources:
  - type: aosp
    path: "art/runtime/gc/task_processor.cc, task_processor.h, heap.cc, heap-inl.h"
  - type: aosp
    path: "libcore/libart/src/main/java/java/lang/Daemons.java"
  - type: official
    path: "developer.android.com/topic/performance/memory"
  - type: research
    path: "DeepResearch/2026-05-24-android17-art-gc-compose-pause.md"
---

# ART GC 抑制与启动性能优化

三方 App 没有受支持的“暂停 ART GC”接口，也不应修改 `libart.so` 的任务函数或 vtable。所谓 GC 抑制，是**降低启动阶段的分配速率和存活对象规模，让 ART 更少达到 GC 触发条件**。

Android 17 已在 Zygote fork 后主动放宽 Java heap 的启动期阈值。App 若仍在首帧前触发 GC，通常说明启动分配接近 heap growth limit、显式请求了 GC、native allocation 反馈造成压力，或进程状态变化触发了回收。排查目标应是找到这些分配和触发原因，而非阻塞 `HeapTaskDaemon`。

以下行为以 `android-17.0.0_r1` 为准。ART GC 的收集器和分代机制见 4.8，启动任务治理见 21.2 和 21.6。

## GC 对启动性能的影响路径

现代 ART 的回收大部分可以与 mutator 并发执行，但“并发”不表示对启动没有成本。需要区分三条影响路径：

1. **短暂停顿。** 并发收集器仍有需要挂起 mutator 的阶段。暂停若落在主线程关键路径上，会直接增加 TTID/TTFD。
2. **分配线程等待。** 分配失败或必须等待正在运行的 GC 完成时，主线程可能阻塞；`heap.cc` 把 `kGcCauseForAlloc` 视为需要关注的暂停来源。
3. **共享资源竞争。** `HeapTaskDaemon` 执行标记、扫描、复制或整理时，会消耗 CPU、内存带宽和缓存。主线程即使没有被挂起，也可能得到更少的 CPU 时间。

`HeapTaskDaemon` 不只执行 GC。它还处理 collector transition、heap trim、启动完成清理等 heap task。因此，看到该线程 Running 只能证明它在工作，不能直接得出“GC 导致启动慢”的结论。还需要对齐 ART slice、主线程状态和分配记录。

## Android 17 的 HeapTaskDaemon 调度链

下面的调用链用于定位 Java daemon 与 ART native 任务队列之间的边界。

```text
Daemons.HeapTaskDaemon.runInternal()
  ├─ VMRuntime.startHeapTaskProcessor()
  └─ VMRuntime.runHeapTasks()
       └─ TaskProcessor::RunAllTasks()
            └─ GetTask() → HeapTask::Run()
```

`TaskProcessor` 用按 `target_run_time` 排序的 `multiset` 保存任务。队列为空时，daemon 等待条件变量；队首任务尚未到时，它执行定时等待。`AddTask()` 插入新任务后会发送 signal，因此一个 target time 更早的新任务可以唤醒 daemon 并成为新队首。

Android 17 的常见任务包括：

| 任务 | 源码职责 | 与启动分析的关系 |
|---|---|---|
| `ConcurrentGCTask` | 调用 `Heap::ConcurrentGC()` | 需要结合 GC cause、暂停与 Running 时间分析 |
| `CollectorTransitionTask` | 处理前后台 collector 状态变化 | 进程状态变化附近可能出现，不等同于分配触发 GC |
| `HeapTrimTask` | 尝试归还空闲页并整理相关内存 | 关注 trim slice，不能算作 GC CPU |
| `ReduceTargetFootprintTask` | 延后降低 post-fork heap 目标 | Android 17 启动期阈值调整的一部分 |
| `TriggerPostForkCCGcTask` | 长时间没有发生 GC 时请求一次后台 GC | 用于回收启动垃圾，不是在 fork 后 2 秒立即执行 |
| `StartupCompletedTask` | 通知 runtime 启动结束、释放 startup dex cache/linear alloc 等资源 | 由 framework/runtime 管理，不是 App 的 GC 开关 |

`ConcurrentGCTask` 请求时使用 `NanoTime()` 作为 target time，也就是尽快运行。延时队列中已有 `ReduceTargetFootprintTask` 或 post-fork GC，不会阻止这个立即任务排到前面。

## Android 17 的 post-fork 启动期策略

`Heap::PostForkChildAction()` 是理解启动期策略的关键源码锚点。Android 17 做了四件事：

1. 增加 GC sequence number，使 Zygote 或 fork 极早期已经排队的旧 GC 请求失效，避免子进程刚 fork 就执行旧请求。
2. 把 `target_footprint_` 临时提高到 `growth_limit_`，再重新计算 `concurrent_start_bytes_`，源码注释直接写明目的是避免 App launch 期间 GC。
3. 在 2 秒后尝试把目标降低到 `max(growth_limit / 4, initial_heap_size)`；如果仍高于初始值，再过 8 秒限制到 `initial_heap_size`。若期间已经发生 GC，这些降低目标任务会成为无操作。
4. 更晚再安排 `TriggerPostForkCCGcTask`。它只在自 fork 以来仍未发生 GC 时请求后台回收，用于避免长期保留启动垃圾；时间还加入了按 UID 生成的 0—19,999 ms 抖动。

所以，“系统固定屏蔽 GC 两秒”的说法并不准确。2 秒是第一次 footprint 降低的延迟，不是 TaskProcessor 的全局冻结窗口。启动分配若触及 growth limit、发生 allocation failure、收到其他 GC 请求或遇到进程状态变化，GC 仍可能发生。

这套策略只适用于新 fork 的进程。温启动、热启动复用已有进程，不会重新执行 `PostForkChildAction()`；多进程 App 的每个新进程则有自己的 heap 和 post-fork 状态。

## 用 Perfetto 建立因果证据

采集配置至少要包含 `sched`、CPU frequency/idle 和 ART/dalvik trace。分析时先标出进程启动、`bindApplication`、首帧和 fully drawn 边界，再看 GC 是否与关键路径重叠。

推荐按下面的顺序判断：

1. 在 App 进程中找到 `HeapTaskDaemon`，确认它在启动窗口内是否 Running。
2. 查看同一窗口的 ART/GC slice，区分 concurrent GC、blocking GC、trim 与其他 task。
3. 检查主线程在重叠区间是 Running、Runnable、Sleeping 还是阻塞；Runnable 但长期拿不到 CPU 更支持“资源竞争”，明确的 suspend/wait slice 更支持“GC 等待”。
4. 对照 TTID/TTFD，确认 GC 位于关键路径，而非首帧之后。
5. 再用分配记录定位哪段代码制造了短命对象或保留了大量对象。

下面的 Perfetto SQL 统计一个已知启动窗口内 `HeapTaskDaemon` 的 scheduler Running 时间。请先把 `VALUES` 中的两个数字替换为 trace 内的纳秒时间戳。

```sql
WITH bounds(start_ns, end_ns) AS (
  VALUES (123000000000, 126000000000)
)
SELECT
  p.name AS process_name,
  SUM(
    MAX(
      0,
      MIN(ts.ts + ts.dur, b.end_ns) - MAX(ts.ts, b.start_ns)
    )
  ) / 1e6 AS running_ms
FROM thread_state ts
JOIN thread t USING (utid)
JOIN process p USING (upid)
CROSS JOIN bounds b
WHERE p.name = 'com.example.app'
  AND t.name = 'HeapTaskDaemon'
  AND ts.state = 'Running'
  AND ts.ts < b.end_ns
  AND ts.ts + ts.dur > b.start_ns
GROUP BY p.name;
```

这条查询只计算 CPU Running 时间，不区分是哪一种 heap task。没有适用于所有应用的“10% 就需要抑制”阈值；要用同一设备、同一构建、同一启动入口的 A/B 结果判断。

Logcat 中的 ART GC 行可补充 cause、freed bytes、heap 大小、pause 和 total duration，但 Android 17 `Heap::LogGC()` 不保证打印每一次普通 GC。没有日志不能证明启动期间没有 GC。

## 从 GC 事件追到分配调用栈

Perfetto 适合确认时序和关键路径，Java/Kotlin Allocation Recording 适合找到对象类型与调用栈。分配记录会引入明显开销，尤其是 Full tracking，因此只能用于归因，不应拿它的启动耗时作为性能结论。

建议做两轮采集：

- **release/profileable trace**：复现 TTID/TTFD，确认 GC、主线程与 CPU 调度关系；
- **debuggable allocation recording**：只截取 `ContentProvider`、`Application.onCreate()`、首个 Activity 和首屏构建窗口，按 allocated bytes、allocation count 和 remaining size 排序。

排查时把对象分成三类：

| 类型 | 典型信号 | 处理方向 |
|---|---|---|
| 大量短命对象 | allocation count 高，GC 后 remaining size 低 | 去掉临时集合/字符串/包装对象，减少重复解析 |
| 大量启动后仍存活对象 | remaining size 高 | 检查全局缓存、SDK、DI graph、图片和首屏模型 |
| 单个或少量大对象 | byte[]、Bitmap、大数组占比高 | 延后加载、降低尺寸、流式处理或按需映射 |

“把工作移到后台线程”不会自动降低 GC 压力。Java heap 是进程共享的，后台线程仍在同一个 heap 分配；这只能减少主线程 CPU 工作，不能消除并发 GC 或内存带宽竞争。

## 可发布应用的治理顺序

### 1. 移出首帧前不需要的对象图

对每个启动任务记录“首帧前是否必须完成”和“会保留多少对象”。分析、推送、广告、搜索索引、二级页面模型等任务若与初始显示无关，应延迟到首帧后、首次使用时或后台调度。延迟初始化的生命周期与线程安全策略见 21.6。

延后任务也要错峰。把所有任务一起放到首帧后的同一个回调，只会把 GC 和卡顿从 TTID 移到首次交互。

### 2. 降低瞬时分配率

启动热区常见的可修复模式包括：

- 多次把同一 JSON/XML 解析成临时树；
- `map/filter/flatMap` 链在大集合上创建多层临时对象；
- 字符串拼接、正则、格式化和日志参数在 release 启动路径频繁执行；
- 未预估容量的 `ArrayList`、`HashMap` 和 buffer 反复扩容；
- 依赖注入或反射扫描一次性构造大量 provider/metadata；
- Compose/View 首屏重复创建等价 model、span、shape 或 listener。

优化时先按 allocated bytes 与调用次数排序。不要因为某个对象“小”就忽略它；高频小对象形成的总分配量同样会推动 GC。

### 3. 控制存活对象和 cache

短命对象影响分配速率，长命对象抬高 live set。live set 越大，GC 需要扫描的对象越多，后续 heap 可用空间也越少。

启动期 cache 应有容量、逐出和生命周期边界。对象池只适合已经证明确有高频构造且重置成本可控的对象；随意池化会扩大 live set、增加状态错误，并可能让 GC 更慢。

### 4. 同时检查 native 与 graphics memory

Bitmap、字体、解码器、数据库 page cache 和 native SDK 可能通过 native allocation 反馈影响 ART 的回收决策。Java heap 看起来不大时，仍要查看进程 PSS、native heap、graphics 和对应调用栈。`Runtime.totalMemory() - freeMemory()` 只表示 Java heap 中的一个快照，不能代表进程总内存，也不能据此设置统一百分比告警。

### 5. 保持编译状态与实验条件一致

Baseline Profile 会改变启动 CPU 时间和分配时序，Startup Profile 会改变 DEX 读取局部性。比较 GC 优化前后时，要固定 APK、compiler filter、安装来源、设备温度、账号数据和启动类型，避免把编译差异解释成 GC 收益。

## 不应采用的“GC 抑制”方案

### Hook `ConcurrentGCTask::Run`

修改 `libart.so` vtable 或 inline hook 属于未受支持的 runtime 篡改。它的问题不只是版本兼容：

- `ConcurrentGCTask`、vtable 布局、符号可见性和调用约定都是 ART 内部 ABI；
- C++ 非静态成员函数调用还包含隐含的 `this` 参数，按普通 `void(Thread*)` 调用会破坏寄存器/参数；
- vtable 所在页可能受只读映射、RELRO、CFI 和平台加固保护；
- 在 `Run()` 中 sleep 会占住 `HeapTaskDaemon`，连 trim、transition、startup cleanup 等任务也被延迟；
- heap 达到分配上限时，mutator 仍可能执行 blocking GC 或直接走向 OOM；
- ART 是可通过 Mainline 更新的模块，同一 Android API 级别也不能保证内部符号和布局一致。

因此，这种 Hook 不应进入生产 App，也不适合作为“失败就降级”的优化开关。它改变的是内存安全和 runtime 正确性，失败后果可能是随机崩溃、heap corruption 或 OOM。

### 反射调用 `VMRuntime`

`VMRuntime.registerSensitiveThread()` 在 Android 17 中把当前线程登记为 **JIT sensitive thread**；`ActivityThread.handleBindApplication()` 已为 UI 线程调用它。它没有“优先分配”或“减少 GC 阻塞”的语义。

`requestConcurrentGC()`、`setTargetHeapUtilization()`、`notifyStartupCompleted()` 等也是隐藏或 module-only API，不属于三方 SDK。`StartupCompletedTask` 会释放 startup dex cache/linear alloc，并可能生成 runtime app image；它不是供 App 自己选择时机的 GC 控制器。

### 在首帧后主动调用 `System.gc()`

`System.gc()` 只是请求，ART 可以忽略或调整；请求本身可能引入额外暂停和 CPU/内存带宽竞争。没有 trace 证明“某个非交互窗口主动 GC”能改善后续关键路径时，不要在首帧后、页面切换或滑动开始前调用它。

同理，不要把 GC suppression 扩展到 RecyclerView 滑动、Activity 转场或 Compose 重组。减少每帧分配是正确方向，暂停 collector 不是。

## 实验设计与发布判断

一项 GC 启动优化至少要回答四个问题：

1. 启动窗口是否发生了 GC，cause 和 collector 是什么？
2. GC 与 TTID/TTFD 关键路径重叠了多少？
3. 哪些调用栈贡献了分配量与 live set？
4. 修复后是 GC 减少了，还是业务工作量、编译状态或缓存条件变了？

建议保留下面的实验对照表：

| 组别 | 变量 | 观察 |
|---|---|---|
| 原始组 | 当前 release | GC 次数/重叠、HeapTaskDaemon Running、TTID/TTFD、峰值内存 |
| 分配修复组 | 只改目标分配点 | 同一编译状态下 GC 和分位值是否改善 |
| 延迟任务组 | 只移动非首帧任务 | TTID 改善后，首交互和首帧后是否出现反弹 |
| 低内存设备组 | 同一构建、受控内存压力 | blocking GC、OOM、进程退出和长尾是否恶化 |

线上没有通用的 GC CPU、heap 使用率或 pause 告警阈值。阈值应来自应用自身按设备档位建立的基线。至少联合观察：

- TTID、TTFD 与 P50/P90/P99；
- 启动阶段 Java allocated bytes 和 retained/live bytes 的实验室基线；
- GC 与关键路径重叠时长；
- 启动后首个交互的慢帧；
- 低内存/OOM 相关退出、崩溃和 ANR；
- 新进程冷启动与复用进程启动的分布。

## Android 8—17 的版本边界

Android 8 起可以使用不受 65,535 条记录限制的现代 Java/Kotlin allocation recording，但 ART 内部 heap 策略会随系统和 Mainline 模块演进。文章或方案不应把 Android 8 某个实现细节直接外推到 Android 17。

以下 Android 17 结论以 `android-17.0.0_r1` 为准：

- post-fork 阶段先放宽 heap 阈值，再分阶段降低；
- 2 秒不是 GC 全局冻结窗口；
- `ConcurrentGCTask` 可以作为立即任务插入队列；
- UI 线程已由 framework 登记为 JIT sensitive thread；
- 普通 App 没有受支持的 ART GC 暂停 API。

OEM 和 ART Mainline 更新可以调整 collector、flags 和 heap 参数。应用侧可依赖的长期策略仍是：控制分配量、缩小 live set、减少首帧前任务，并用 trace 验证。

## 排查清单

1. 分开采集新进程冷启动与复用进程启动。
2. 在 Perfetto 中对齐启动边界、GC slice、HeapTaskDaemon 和主线程状态。
3. 不把 HeapTaskDaemon 的所有 Running 时间都记为 GC。
4. 用 Allocation Recording 找对象类型和调用栈，不用它的耗时做 benchmark。
5. 区分短命分配、live set 与大对象。
6. 检查 Java、native、graphics 和 Bitmap，不只看 `Runtime` heap。
7. 固定 compiler filter、安装来源和设备条件做 A/B。
8. 禁止 libart Hook、隐藏 VMRuntime 调用和无证据的 `System.gc()`。
9. 回归首帧后首交互、低内存设备与多进程启动。

## 参考资料

- [`Heap::PostForkChildAction()` 与 heap tasks](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [`TaskProcessor`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/task_processor.cc)
- [`task_processor.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/task_processor.h)
- [`StartupCompletedTask`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/startup_completed_task.cc)
- [`VMRuntime.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/libart/src/main/java/dalvik/system/VMRuntime.java)
- [`Daemons.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/libart/src/main/java/java/lang/Daemons.java)
- [`ActivityThread.handleBindApplication()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [Overview of memory management](https://developer.android.com/topic/performance/memory-overview)
- [Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
