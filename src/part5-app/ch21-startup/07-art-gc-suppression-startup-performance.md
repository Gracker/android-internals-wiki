---
title: ART GC 抑制与启动性能优化
chapter: '21.7'
section: '21.7'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags:
- gc-suppression
- startup
- art-runtime
- heap-task-daemon
- native-hook
- concurrent-gc
related_chapters:
- '1.5'
- '4.6'
- '21.1'
- '21.2'
- '23.4'
- '4.5'
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 heap.cc, TaskProcessor, StartupCompletedTask, VMRuntime/Daemons/ActivityThread; current Android Developers memory and allocation-recording docs; current Perfetto tracing docs
confidence: high
sources:
- type: aosp
  path: art/runtime/gc/task_processor.cc, task_processor.h, heap.cc, heap-inl.h
- type: aosp
  path: art/runtime/startup_completed_task.cc
- type: aosp
  path: art/runtime/native/dalvik_system_VMRuntime.cc
- type: aosp
  path: libcore/libart/src/main/java/dalvik/system/VMRuntime.java, java/lang/Daemons.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: official
  path: developer.android.com/topic/performance/memory-overview
- type: official
  path: developer.android.com/studio/profile/record-java-kotlin-allocations
- type: official
  path: perfetto.dev/docs/getting-started/system-tracing, data-sources/cpu-scheduling
- type: research
  path: DeepResearch/2026-05-24-android17-art-gc-compose-pause.md
---

# ART GC 抑制与启动性能优化

Android Runtime（ART）负责执行 Android 字节码和管理 Java heap（存放 Java/Kotlin 对象的堆内存）。GC（Garbage Collection，垃圾回收）会查找已经不可达的对象并回收它们占用的空间。第三方 App 没有受支持的“暂停 ART GC”接口；本文所说的 GC 抑制，指降低启动阶段的对象分配速率和存活对象规模，让 ART 更少达到 GC 触发条件。

Android 17 会从 Zygote（预先加载公共 framework 代码的系统进程）fork 出 App 进程，并在 fork 后暂时放宽 Java heap 的启动期阈值。首帧前仍可能因为分配接近 growth limit（该进程 Java heap 允许增长的上限）、显式 GC 请求、已登记到 ART 的 native allocation（原生内存分配）压力或进程状态变化而回收。排查时应找到具体的分配点和 GC cause（触发原因），阻塞 `HeapTaskDaemon` 只会破坏运行时调度。

以下内部行为以 `android-17.0.0_r1` 为准。对象分配与 GC 治理见 [23.4 Java Heap、GC 与 Compose 内存分配](../ch23-memory-practice/04-java-heap-gc-compose-allocation.md)，启动任务治理见 [21.2 启动任务编排、延迟初始化与并发调度](02-startup-task-lazy-concurrency.md) 和 [21.2 启动任务编排、延迟初始化与并发调度](02-startup-task-lazy-concurrency.md)。

## GC 对启动性能的影响路径

现代 ART 的回收大部分可以与 mutator 并发执行。mutator 是运行 App 代码并分配、读取或修改对象的线程；并发 GC 仍会给启动带来三类成本：

1. **短暂停顿。** 并发收集器仍有需要挂起 mutator 的阶段。暂停若落在主线程关键路径上，会直接增加 TTID（首次显示时间）或 TTFD（主要内容完整可用时间）。
2. **分配线程等待。** 分配失败，或分配线程必须等待正在运行的 GC 完成时，主线程可能阻塞；`heap.cc` 用 `kGcCauseForAlloc` 标记这类“为完成分配而触发的 GC”。
3. **共享资源竞争。** `HeapTaskDaemon` 执行标记、扫描、复制或整理时，会消耗 CPU、内存带宽和 CPU cache（处理器缓存）。主线程即使没有被挂起，也可能因资源竞争得到更少的运行时间。

`HeapTaskDaemon` 是 ART 执行堆任务的后台守护线程，它还处理 collector transition（前后台状态变化时切换回收策略）、heap trim（尝试把空闲页归还系统）和启动完成清理。Perfetto 中的 Running 只表示该线程当时正在 CPU 上执行；要判断 GC 是否拖慢启动，还需对齐具体 ART slice（时间线上的一段事件）、主线程状态和对象分配记录。

## Android 17 的 HeapTaskDaemon 调度链

下面的调用链用于定位 Java daemon（常驻后台线程）与 ART native（C++ 运行时）任务队列之间的边界。

```text
Daemons.HeapTaskDaemon.runInternal()
  ├─ VMRuntime.startHeapTaskProcessor()
  └─ VMRuntime.runHeapTasks()
       └─ TaskProcessor::RunAllTasks()
            └─ GetTask() → HeapTask::Run()
```

`TaskProcessor` 用 `multiset` 保存任务；这是允许相同排序键的有序容器，排序键 `target_run_time` 表示基于 `NanoTime()` 单调时钟的目标执行时间。队列为空时，daemon 等待 condition variable（条件变量）；队首任务尚未到期时，它定时等待到目标时间。`AddTask()` 每次插入都会发送 signal（唤醒信号），所以目标时间更早的新任务可以让 daemon 重新检查队首。

Android 17 的常见任务包括：

| 任务 | 源码职责 | 与启动分析的关系 |
|---|---|---|
| `ConcurrentGCTask` | 调用 `Heap::ConcurrentGC()` | 要结合 GC cause、暂停与 Running 时间分析 |
| `CollectorTransitionTask` | 处理前后台进程状态对应的 collector 切换 | 可能出现在进程状态变化附近，不能算作分配触发的 GC |
| `HeapTrimTask` | 尝试把不用的 heap 页归还系统 | 应识别为 trim slice，不能计入 GC 的 CPU 时间 |
| `ReduceTargetFootprintTask` | 延后降低 post-fork 的 target footprint；该值是 ART 当前期望的 heap 规模，不等于硬上限 `growth_limit_` | 属于 Android 17 的启动期阈值调整 |
| `TriggerPostForkCCGcTask` | 长时间没有发生 GC 时，以 `kGcCauseBackground` 请求一次并发 GC | 用于回收启动阶段留下的无用对象；类名中的 `CC` 不能单独证明设备当前使用哪一种 collector |
| `StartupCompletedTask` | 首次执行时通知 runtime 启动结束，清理 startup dex cache（启动期类/方法查找缓存）和 linear alloc（ART 启动期元数据分配区），满足条件时还会尝试写 runtime app image | 由 framework/runtime 触发，不是第三方 App 的 GC 开关 |

`ConcurrentGCTask` 入队时使用当前 `NanoTime()` 作为目标时间，也就是让任务尽快具备执行资格。队列里已有延时的 `ReduceTargetFootprintTask` 或 post-fork GC 请求，不会阻止它排到更早的位置；何时拿到 CPU 仍取决于线程调度。

## Android 17 的 post-fork 启动期策略

`Heap::PostForkChildAction()` 是理解启动期策略的关键源码入口。Android 17 的处理可分为四步：

1. 把 `gcs_completed_` 计数加一，让 Zygote 或 fork 极早期按旧 GC 编号排队的请求失效。这里增加的是用来判定请求是否过期的 GC 编号，并没有执行一次回收。
2. 把 `target_footprint_` 暂时提高到 `growth_limit_`，再重算 `concurrent_start_bytes_`（并发 GC 的启动阈值）。源码注释给出的目的就是减少 App launch 期间的 GC。
3. 若 `initial_heap_size_ < growth_limit_`，2 秒后尝试把 target footprint 降到 `max(growth_limit / 4, initial_heap_size)`；若该值仍高于初始 heap，再过 8 秒降到 `initial_heap_size`，即第二次目标时间约为 fork 后 10 秒。只要期间已完成 GC，或任务执行时已有 collector 在运行，降低任务就不再改这个目标。
4. 随后安排 `TriggerPostForkCCGcTask`。根据前面安排了零、一个还是两个降低任务，其目标时间分别约为 fork 后 8—28 秒、10—30 秒或 18—38 秒；区间来自固定的 8 秒延迟和按 UID（系统分配给 App 的用户标识）生成的 0—19,999 ms jitter（确定性的错峰伪随机量）。任务执行时若 GC 编号仍与 fork 后相同，才请求一次后台并发 GC。

这两秒内 collector 并未关闭。源码只是在这段时间放宽 target footprint，并让 fork 前后的旧请求失效；`TaskProcessor` 没有全局冻结。启动分配触及阈值、发生 allocation failure（对象分配失败）、收到其他 GC 请求或遇到进程状态变化时，GC 仍可能发生。

这套策略只适用于新 fork 的进程。温启动和热启动会复用已有进程，不会重新执行 `PostForkChildAction()`；多进程 App 的每个新进程都有独立的 heap 与 post-fork 状态。冷、温、热启动的判定见 [21.1 App 启动路径、监控与度量](01-app-startup-path-monitoring.md)。

## 用 Perfetto 建立因果证据

Perfetto 是 Android 的系统级时间线追踪工具。采集配置至少要包含 scheduler 事件（`sched_switch`、`sched_wakeup`）、CPU frequency/idle（频率与空闲状态），以及 `am`、`view`、`dalvik` 等 atrace 类别；还应为目标包启用 App trace。类别是否可用与系统版本有关，采集前可用 Perfetto UI 或命令行列出的设备能力确认。配置方法见 [Recording system traces](https://perfetto.dev/docs/getting-started/system-tracing) 和 [CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)。

分析时先标出进程创建、`bindApplication`（framework 把 App 绑定到新进程并开始初始化的阶段）、首帧和 fully drawn（App 报告主要内容已完整可用）边界，再看 GC 是否与启动关键路径重叠。

推荐按下面的顺序判断：

1. 在 App 进程中找到 `HeapTaskDaemon`，确认它在启动窗口内是否 Running（正在 CPU 上执行）。
2. 查看同一窗口的 ART/GC slice，区分 concurrent GC（并发回收）、blocking GC（让调用线程等待的回收）、trim 与其他 heap task。
3. 检查主线程在重叠区间是 Running、Runnable（已具备运行条件但在等 CPU）、Sleeping，还是卡在 suspend/wait slice。长时间 Runnable 更支持 CPU 竞争；明确的 GC wait slice 才能证明线程在等回收完成。
4. 对照 TTID/TTFD，确认事件落在关键路径上；首帧之后的 GC 不能解释 TTID 变慢。
5. 再用对象分配记录定位制造短命对象或保留大量对象的代码。

下面的 Perfetto SQL 统计一个已知启动窗口内 `HeapTaskDaemon` 的 scheduler Running 时间。`thread_state` 记录线程调度状态，`utid`/`upid` 是 trace 内部的线程/进程标识。运行前要把 `VALUES` 中的两个数字替换为该次 trace 的纳秒时间戳，并把包名改成目标进程名。

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

这条查询求的是时间窗口与 Running 区间的交集，只能回答该 daemon 用了多少 CPU 时间，无法区分具体 heap task。若目标是 `:remote` 等子进程，还要改成对应进程名。没有适用于所有 App 的“超过启动窗口 10% 就要抑制”阈值；应比较同一设备、同一构建和同一启动入口的 A/B（只改变一个条件的对照实验）结果。

Logcat 中的 ART GC 行可补充 cause、freed bytes（回收字节数）、heap 大小、pause 和 total duration。Android 17 的 `Heap::LogGC()` 默认只保证记录符合条件的显式或慢 GC，快速的普通 GC 可能不打印；没有日志不能证明启动期间没有发生 GC。

## 从 GC 事件追到分配调用栈

Perfetto 适合确认时序和关键路径，Java/Kotlin Allocation Recording（对象分配记录）适合查对象类型与分配调用栈。当前 Android Studio 要求使用 debuggable 构建；Full 模式记录每次分配，分配密集时会明显拖慢 App，Sampled 模式则按间隔采样。两种模式都用于归因，采集期间的启动耗时不能作为发布性能结论。详细限制见 [Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)。

建议做两轮采集：

- **release/profileable system trace**：用发布构建或允许性能分析的 release-like 构建复现 TTID/TTFD，确认 GC、主线程与 CPU 调度关系；
- **debuggable allocation recording**：只截取 `ContentProvider`、`Application.onCreate()`、首个 Activity 和首屏构建窗口，按 allocated bytes（分配字节数）、allocation count（分配次数）和 Remaining Size 排序。

Android Studio 的 Remaining Size 是所选时间段内“分配大小减去已释放大小”，适合寻找采集结束时仍未释放的对象；它不计算一棵对象引用图的完整 retained size（移除某个对象后可一起释放的总大小）。要判断泄漏或完整保留关系，还需结合 heap dump（堆快照）和引用链。

排查时把对象分成三类：

| 类型 | 典型信号 | 处理方向 |
|---|---|---|
| 大量短命对象 | allocation count 高，GC 后 Remaining Size 低 | 去掉临时集合、字符串和包装对象，减少重复解析 |
| 大量启动后仍存活对象 | Remaining Size 高 | 检查全局缓存、SDK、DI graph（依赖注入创建的对象关系）、图片和首屏模型 |
| 单个或少量大对象 | byte[]、Bitmap、大数组占比高 | 延后加载、降低尺寸、流式处理或按需映射 |

把工作移到后台线程不会自动降低 GC 压力。Java heap 由进程内线程共享，后台线程仍在同一个 heap 分配；迁移线程可以减少主线程 CPU 工作，却不会消除并发 GC 或内存带宽竞争。

## 可发布应用的治理顺序

### 1. 移出首帧前不需要的对象图

对每个启动任务记录“首帧前是否必须完成”和“会保留多少对象”。分析、推送、广告、搜索索引、二级页面模型等任务若与初始显示无关，应延迟到首帧后、首次使用时或后台调度。延迟初始化的生命周期与线程安全策略见 [21.2 启动任务编排、延迟初始化与并发调度](02-startup-task-lazy-concurrency.md)。

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

短命对象影响分配速率，长命对象会抬高 live set（一次 GC 时仍能从引用链访问到的对象集合）。live set 越大，GC 需要扫描的对象通常越多，后续 heap 可用空间也越少。

启动期 cache（缓存）应有容量、逐出和生命周期边界。对象池只适合已经测出高频构造且重置成本可控的对象；随意池化会扩大 live set、增加状态错误，并可能让 GC 更慢。

### 4. 同时检查 native 与 graphics memory

ART 只能把已经通过 native allocation accounting（原生分配记账）登记的部分原生内存纳入 GC 压力判断；Android 17 的 `RegisterNativeAllocation()` 会在累计到一定次数或遇到大额登记时检查是否需要 GC。Bitmap、字体或解码器等 framework 组件可能走这条路径，数据库 page cache（文件页缓存）、graphics buffer（图形缓冲区）和任意 native SDK 占用则不能仅凭“位于 native 内存”就认定会触发 ART GC。

Java heap 看起来不大时，仍要查看进程 PSS（按共享比例折算的驻留内存）、native heap、graphics 分类和对应调用栈。这些数据能说明进程总内存压力，不等同于 ART heap 的触发阈值。`Runtime.totalMemory() - freeMemory()` 只给出 Java heap 的一个瞬时近似值，不能代表进程总内存，也不适合设置跨设备统一百分比告警。

### 5. 保持编译状态与实验条件一致

Baseline Profile 会改变启动 CPU 时间和分配时序，Startup Profile 会改变 DEX 文件中的代码排列和读取局部性。比较 GC 优化前后时，要固定 APK、compiler filter（ART 实际采用的编译强度）、安装来源、设备温度、账号数据和启动类型，避免把编译差异解释成 GC 收益。Profile 与编译状态的核查方法见 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md) 和 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md)。

## 不应采用的“GC 抑制”方案

### Hook `ConcurrentGCTask::Run`

`libart.so` 是 ART 的 native 运行时库。替换其中的 vtable（C++ 虚函数分发表）条目或做 inline hook（改写函数入口，让调用跳到自定义代码）会直接改变系统运行时实现，Android 不提供兼容或正确性保证。具体风险包括：

- `ConcurrentGCTask`、vtable 布局、符号可见性和调用约定都属于 ART 内部 ABI（二进制调用约定），系统升级可以改变它们；
- C++ 非静态成员函数调用包含隐含的 `this` 对象指针，误按普通 `void(Thread*)` 函数调用会让寄存器或参数错位；
- vtable 所在页可能受只读映射、RELRO（重定位后只读保护）、CFI（控制流完整性检查）和其他平台加固机制保护；
- 在 `Run()` 中 sleep 会占住 `HeapTaskDaemon`，连 trim、transition、startup cleanup 等任务也被延迟；
- heap 达到分配上限时，mutator 仍可能执行 blocking GC，回收后仍无法分配则会遇到 OOM（OutOfMemoryError，内存不足错误）；
- ART 可通过 Mainline 独立于整机系统版本更新，同一 Android API 级别也不能保证内部符号和布局一致。

这种 Hook 不应进入生产 App，也不适合作为“失败就降级”的优化开关。它会影响内存安全和 runtime 正确性，失败后果可能是随机崩溃、heap corruption（堆元数据或对象关系被破坏）或 OOM。

### 反射调用 `VMRuntime`

`VMRuntime.registerSensitiveThread()` 在 Android 17 的 native 实现中调用 `Thread::SetJitSensitiveThread()`，给当前线程设置 JIT（Just-In-Time，运行时即时编译）sensitive 标记；`ActivityThread.handleBindApplication()` 已为 UI 线程调用它。这个标记没有“优先分配”“提高 heap 配额”或“减少 GC 阻塞”的语义。

`requestConcurrentGC()`、`setTargetHeapUtilization()` 和 `notifyStartupCompleted()` 都是 hidden 或 module-only API，只供系统平台或 ART 模块代码使用，不属于第三方 SDK；反射调用还会受到 non-SDK interface（非 SDK 接口）限制。`notifyStartupCompleted()` 只是把立即执行的 `StartupCompletedTask` 放入 heap 任务队列。任务首次生效时会释放 startup dex cache/linear alloc，并且只在非 debuggable、没有 AOT（Ahead-Of-Time，提前编译）机器码且没有可用 App Image 等条件同时满足时尝试写 runtime app image（运行时类元数据快照）；它不是供 App 自选时机的 GC 控制器。

### 在首帧后主动调用 `System.gc()`

`System.gc()` 向 runtime 发出显式回收请求，ART 可以忽略或调整；被执行的请求可能引入暂停以及 CPU/内存带宽竞争。只有 trace 和对照实验都证明某个无交互窗口的请求能改善后续关键路径，才有继续评估的依据；常规 App 不应在首帧后、页面切换或滑动开始前调用它。

RecyclerView 滑动、Activity 转场或 Compose 重组期间也应从每帧分配量入手，不能把“GC suppression”理解成暂停 collector（回收器）。

## 实验设计与发布判断

一项 GC 启动优化至少要回答四个问题：

1. 启动窗口是否发生了 GC，cause 和 collector（实际执行的回收器类型）是什么？
2. GC 与 TTID/TTFD 关键路径重叠了多少？
3. 哪些调用栈贡献了分配量与 live set？
4. 修复后是 GC 减少了，还是业务工作量、编译状态或缓存条件变了？

建议保留下面的实验对照表：

| 组别 | 变量 | 观察 |
|---|---|---|
| 原始组 | 当前 release（发布构建） | GC 次数/重叠、HeapTaskDaemon Running、TTID/TTFD、峰值内存 |
| 分配修复组 | 只改目标分配点 | 同一编译状态下 GC 和分位值是否改善 |
| 延迟任务组 | 只移动非首帧任务 | TTID 改善后，首交互和首帧后是否出现反弹 |
| 低内存设备组 | 同一构建、受控内存压力 | blocking GC、OOM、进程退出和长尾是否恶化 |

线上没有通用的 GC CPU、heap 使用率或 pause 告警阈值。阈值应来自应用自身按设备档位建立的基线。至少联合观察：

- TTID、TTFD 与 P50/P90/P99（分别有 50%、90%、99% 样本不超过的耗时）；
- 启动阶段 Java allocated bytes、Allocation Recording 的 Remaining Size，以及 heap dump 的 retained/live bytes 实验室基线；
- GC 与关键路径重叠时长；
- 启动后首个交互的慢帧；
- 低内存/OOM 相关退出、崩溃和 ANR（应用无响应）；
- 新进程冷启动与复用进程启动的分布。

## Android 8—17 的版本边界

Android Studio 官方文档说明：Android 7.1 及更低版本最多保留 65,535 条分配记录，Android 8 及更高版本没有这一实际限制。这只描述记录数量，debuggable 要求和采集开销仍然存在。ART 内部 heap 策略会随系统版本与 Mainline 模块演进，不能把 Android 8 的某个实现细节直接外推到 Android 17。

以下 Android 17 结论以 `android-17.0.0_r1` 为准：

- post-fork 阶段先放宽 heap 阈值，再分阶段降低；
- 2 秒不是 GC 全局冻结窗口；
- `ConcurrentGCTask` 可以作为立即任务插入队列；
- UI 线程已由 framework 登记为 JIT sensitive thread；
- 普通 App 没有受支持的 ART GC 暂停 API。

OEM（设备厂商）和 ART Mainline 更新可以调整 collector、flags（运行时开关）和 heap 参数。应用侧稳定可用的策略是控制分配量、缩小 live set、减少首帧前任务，并用 trace 验证效果。

## 排查清单

1. 分开采集新进程冷启动与复用进程启动。
2. 在 Perfetto 中对齐启动边界、GC slice、HeapTaskDaemon 和主线程状态。
3. 不把 HeapTaskDaemon 的所有 Running 时间都记为 GC。
4. 用 Allocation Recording 找对象类型和调用栈，不用采集期间的耗时做 benchmark（性能基准）。
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
- [Recording system traces with Perfetto](https://perfetto.dev/docs/getting-started/system-tracing)
- [Perfetto CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [`dalvik_system_VMRuntime.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/dalvik_system_VMRuntime.cc)
