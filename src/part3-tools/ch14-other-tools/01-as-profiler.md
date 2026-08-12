---
title: "Android Studio Profiler"
chapter: "14.1"
section: "14.1"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
task9_state: reviewed
last_verified: "2026-05-28"
last_verified_against: "Android Studio Profiler docs + Power Profiler docs + Android 17 tracing boundary"
confidence: high
sources:
- type: reference
  path: androidperformance.com (高爷博客)
- type: official
  path: https://ui.perfetto.dev/
- type: official
  path: https://developer.android.com/studio/profile
- type: official
  path: https://developer.android.com/topic/performance/tracing
- type: official
  path: https://developer.android.com/studio/profile/inspect-traces
- type: official
  path: https://developer.android.com/studio/profile/cpu-profiler
- type: official
  path: https://developer.android.com/studio/profile/sample-callstack
- type: official
  path: https://developer.android.com/studio/profile/record-java-kotlin-methods
- type: official
  path: https://developer.android.com/studio/profile/record-java-kotlin-allocations
- type: official
  path: https://developer.android.com/studio/profile/capture-heap-dump
- type: official
  path: https://developer.android.com/studio/profile/record-native-allocations
- type: official
  path: https://developer.android.com/studio/profile/power-profiler
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
tags: 
related_chapters: ["5.4", "13.3", "13.5", "13.7", "14.2", "14.8"]
task2b_state: fixed
pipeline_stage: ready-to-publish
task6_state: reviewed
---

# 14.1 Android Studio Profiler

## Profiler 解决什么问题

设备端语义固定到 Android 17 / API 37 / `android-17.0.0_r1`，Android Studio 的任务名称和操作入口则按 2026 年 7 月 29 日可用的官方文档核对。IDE 与平台分别演进：升级 Android Studio 不会改变旧 trace 已采集的数据，升级设备系统也不保证 IDE 自动支持新增数据源。

滑动卡顿、启动慢、内存增长和耗电异常只是现象。诊断时要回答更具体的问题：线程在运行还是等待，CPU 时间花在哪条调用路径，对象为何仍被引用，功耗峰值与哪段设备活动同时发生。Android Studio Profiler 把这些采集任务放进 IDE，并把时间轴、调用栈和源码跳转放在同一套交互里。

Profiler 不是单一采集后端。System Trace 使用平台 tracing 数据；调用栈采样会覆盖 Java/Kotlin、JNI、虚拟机和内核栈帧，原生代码采样使用 Simpleperf；Java/Kotlin 方法记录依赖运行时插桩；内存任务还会使用堆转储、分配事件或原生内存分配采样。分析结论要服从所选任务的数据语义，不能把一种任务的读数套到另一种任务上。

Profiler 的 IDE 视图围绕所选 App 展开。System Trace 本身仍含系统调度、CPU 核心、部分系统进程、渲染和 power rail 数据。需要跨进程浏览、Trace Processor SQL、复杂时间关联或自定义数据源时，可把支持导出的 system trace 交给 Perfetto UI。两套界面读取相同的 trace 记录，展示范围和查询能力有所差异。

## 当前界面与任务入口

从 `View > Tool Windows > Profiler` 打开面板，在 Home 页选择进程，再从 Tasks 区域启动任务。录制可从进程启动阶段开始，也可附加到正在运行的进程。任务结束后，记录会保留在当前 Android Studio 会话的 Past Recordings 中；需要长期保存时应显式导出，且并非所有记录类型都支持导出。

常用入口与问题类型如下：

| 入口 | 适合回答的问题 | 主要限制 |
|---|---|---|
| System Trace | 调度、线程状态、帧渲染、系统竞争、设备功耗活动 | 方法内部只呈现已有 tracepoint，不能自动展开每次方法调用 |
| Find CPU Hotspots（Callstack Sample） | 哪些调用路径持续消耗 CPU | 统计采样可能遗漏短调用，百分比不等同于单次调用耗时 |
| Record Java/Kotlin Methods | 某次执行出现了哪些方法调用及其层级 | 运行时插桩会改变被测程序的时序 |
| Track Memory Consumption | 哪些调用栈产生 Java/Kotlin 或 Native 分配 | Full 记录和较小 Native sample size 会提高采集开销 |
| Analyze Memory Usage（Heap Dump） | 哪些 Java 对象存活、由哪条 GC Root 链持有 | 需要 debuggable App，抓取过程会扰动被测进程 |
| Power Profiler / System Trace Power Rails | 某段设备活动与哪些 power rail 同时升高 | ODPM 是设备级数据，不能直接归因给当前 App |

网络请求已经放到 `App Inspection > Network Inspector`，不再与 CPU、Memory 共用 Profiler 的旧式总时间轴。它适合检查受支持网络库的请求、响应和调用位置；TLS 解密、任意协议和系统范围抓包仍需专门的网络工具。

## CPU Profiler：三种分析模式的深度对比

CPU 问题至少包含三类证据：线程何时得到 CPU、哪些调用路径反复出现在样本中、一次调用经过了哪些子方法。System Trace、Callstack Sample 和 Record Java/Kotlin Methods 分别覆盖这三类问题。它们的时间含义不同。

### System Trace（系统追踪）

Android 10（API 29）及以上的系统追踪文件采用 Perfetto 格式；更早的设备使用旧版 Systrace 格式。Perfetto 可接收多种数据源：内核调度等事件来自 ftrace，Framework 和 App 标记可经 atrace 或 TrackEvent 写入，设备支持时还能携带 FrameTimeline、进程内存和 power rail 数据。把 System Trace 概括成“只通过 atrace 抓点”会漏掉大部分调度证据。

System Trace 通常比全量方法插桩轻，但不存在适用于所有设备和配置的“每个事件固定耗时”。启用的数据源、事件频率、缓冲区大小、App 自定义标记密度和设备实现都会改变开销。高频循环内写入成千上万个 tracepoint，同样可能扰动调度和缓存。可采用相同设备、相同构建、相同脚本分别跑基线和录制版本，检查关键指标是否发生系统性偏移。

它擅长回答线程状态和系统上下文：主线程正在 Running、Runnable、Sleeping 还是不可中断睡眠；任务跑在哪个 CPU 核；是否被更高优先级线程抢占；一帧在 App、RenderThread、GPU 完成和 SurfaceFlinger 各阶段花了多久。没有 tracepoint 的普通 Java/Kotlin 方法不会自动展开，此时要结合调用栈采样或为较小的代码范围添加自定义标记。

Android 10 及以上设备的 System Trace 使用 Perfetto 格式，导出的记录可在 [Perfetto UI](https://ui.perfetto.dev/) 打开。Android Studio 也能导入它支持的既有记录。导出和导入都不会增加数据源；缺少的事件只能修改采集配置后重新录制。

Android 17 的平台 tracing 实现在 `android-17.0.0_r1` 的 `external/perfetto`；App 的同步 trace 标记入口见 `frameworks/base/core/java/android/os/Trace.java`。前者负责采集基础设施与数据源，后者只是 App/Framework 写入 trace 标记的一个入口。

### Java Method Trace（方法追踪）

Java/Kotlin 方法记录通过运行时插桩，在方法进入和退出处写入时间信息。它能呈现完整的调用事件和层级，适合回答“这次调用依次进入了哪些方法”“递归或重复调用发生了多少次”。

插桩逻辑会增加每次方法调用的工作量，并可能改变线程调度、缓存行为和运行时优化状态。方法越短、调用越密集，扰动占原始工作量的比例越高。Android 官方文档明确提示 trace 中的时间读数会偏离生产环境，并建议把录制控制在 5 秒以内。

因此，方法记录中的绝对耗时只适合在同一录制条件下辅助排序。若要判断优化是否缩短了用户可见时延，应回到无插桩的基准测试或低扰动 System Trace。社区案例里的固定倍数依赖设备、代码形态和录制配置，不能当成工具契约。

录制前把操作缩成一个可复现片段，并限制录制窗口。Android 7.1 及以下设备达到配置的文件大小上限后，Android Studio 会停止收集新数据，但界面仍可能显示正在录制；Android 8.0 及以上会忽略该上限。后者仍不适合无限延长录制，因为大文件会显著增加传输和解析时间。

### Callstack Sample（调用栈采样）

调用栈采样要求设备至少为 Android 8.0（API 26）。它周期性获取线程栈，再按调用路径聚合。一个栈帧在样本中占比高，说明它或其子调用在采样窗口内经常处于被观测状态。它提供统计证据，没有给出每次调用的完整事件流。

采样省去了每个方法入口和出口的插桩，开销通常低于方法记录。短于采样间隔的调用可能完全缺席；大量短调用若累计占用 CPU，则可能通过调用方或部分命中的栈表现出来。采样间隔越短，样本更密，文件增长和采集开销也更高。

Callstack Sample 适合找 CPU 热点。若主线程大部分时间在等待 Binder、锁或 I/O，CPU 样本较少不能证明路径很快；System Trace 的线程状态和唤醒链更适合解释等待时间。分析 Java/Kotlin 程序时，栈中还会出现 JNI、ART、`/apex/`、`/system/` 和 `[kernel.kallsyms]` 帧。隐藏这些帧只改变展示，不改变采集结果。

Android Studio 对 App 的原生代码采样使用 Simpleperf。因而表格里可把 Simpleperf 写成原生栈采样后端，不能据此断言所有 Java/Kotlin 栈帧都由同一条原生代码专用路径生成。

### 三种模式怎么选

一个稳妥的选择顺序如下：

1. 用 System Trace 判断问题属于执行、等待、调度、渲染还是系统竞争，并圈定线程和时间窗。
2. 时间主要消耗在 Running 状态且缺少方法级标记时，用 Callstack Sample 找高占比调用路径。
3. 只有调用顺序仍不清楚时，缩短场景后录制 Java/Kotlin Methods；耗时结论再由低扰动 trace 或基准测试复核。

| 模式 | 采集机制 | 结果含义 | 主要风险 |
|---|---|---|---|
| System Trace | Perfetto/Systrace 格式及平台数据源 | 带时间戳的系统事件、线程状态和 trace slice | 未启用或未埋点的数据不会出现；高频数据源也会有成本 |
| Callstack Sample | 周期性栈采样；Native 代码由 Simpleperf 支持 | 样本分布和调用路径 | 短调用遗漏、采样偏差、等待时间解释不足 |
| Java/Kotlin Methods | ART 运行时插桩 | 方法进入/退出事件与调用层级 | 时序扰动、文件快速增长 |

## Memory Profiler：从实时曲线到堆快照

Memory Profiler 将 Java、Native、Graphics、Stack、Code 和无法细分的内存放在时间轴上，并提供 Java/Kotlin allocation、heap dump 与 Native allocation 等任务。顶部分类统计以系统报告的 App 私有已提交页面为基础，不等同于完整 RSS/PSS；Graphics 包含图形缓冲区队列、GL surface 和 GL texture 等 CPU/GPU 共享内存，并非独立 GPU 显存。曲线用于发现异常时段，引用链和分配调用栈用于解释原因。

### 实时内存曲线

一次跳升表示该时间段内进程持有的内存增加，下降常与 GC、对象释放或分配器行为有关。曲线持续抬高是调查线索，还不能单独证明泄漏。缓存扩容、延迟 GC、原生分配器保留空闲页、Bitmap/图形缓冲区生命周期和测试路径没有回到同一状态，都可能产生相似形状。

排查时应固定设备和构建，重复同一段用户路径，并在每轮回到等价界面状态。关注对象数、分类内存、GC 事件和多轮操作后的稳定区间。若 Java 对象数或某类实例在多轮 GC 后仍单调增长，再抓 heap dump 检查引用链。进程 RSS 没有立即下降，也不等价于 Java 对象仍存活；堆内空闲空间可能保留给后续分配。

Java/Kotlin allocation 任务默认记录全部分配，也可改成 Sampled。Android 7.1 及以下的旧路径最多保留 65,535 条分配记录；Android 8.0 及以上没有该项实践限制。这个版本差异与 LeakCanary 无关。LeakCanary 的 Android Studio 专用任务从 Android Studio Panda 开始提供，不能写成 Android 8.0 平台新增能力。

### Heap Dump（堆快照）

`Analyze Memory Usage (Heap Dump)` 记录抓取时仍存活的 Java 对象。类表中的 Shallow Size 是该类全部实例的 Java 内存总量，Retained Size 是这些实例共同支配的内存总量；实例面板中的 Shallow Size 才是单个对象自身的 Java 内存，Retained Size 则来自支配树（dominator tree）。两者都要结合实例和引用图解释。抓取发生在 App 进程内，会临时增加 Java 内存并扰动执行，因此不要用同一时段评价性能时延。

检查顺序可从“本应结束生命周期的对象”开始：退出页面后仍保留的 Activity、Fragment、View 树、Coroutine 作用域、监听器或大型业务对象。多个 Activity 实例也可能来自配置变化、返回栈或多窗口，不能只凭数量定性。选中实例后沿 References 查到 GC Root，确认持有者是否符合生命周期设计。

Profiler 的 `Show activity/fragment leaks` 过滤器会列出可疑实例。它缩小候选集合，仍需核对引用链和复现步骤。Android Studio Panda 的 LeakCanary 集成则把 LeakCanary 生成的证据带到 Profiler 专用任务中；项目要先按 LeakCanary 的接入要求运行检测。

Android Studio 中的 Heap Dump 和 Java/Kotlin allocation 任务要求 debuggable App。若问题只在接近发布的构建中出现，可先用 profileable 构建采 System Trace、Callstack Sample 或 Native allocations，再制作最小化的 debuggable 变体复现 Java 堆问题。Android 15 起的 `ProfilingManager` 可以在真实用户设备上申请 Java heap dump，那是另一套受限流和隐私处理约束的生产采集接口。

### Allocation Tracking（分配追踪）

分配追踪回答“哪些调用栈在创建对象”。锯齿状曲线和密集 GC 常提示短生命周期对象很多，但还要检查分配速率、对象类型和用户可见时延是否同窗出现。

`Track Memory Consumption (Java/Kotlin Allocations)` 可显示对象类型、分配大小、线程、调用栈和释放时间。Full 模式记录全部分配，分配密集时可能让 App 明显变慢；Sampled 按间隔收集，开销较低，结果是估计值。

可先用 Sampled 观察高频模式，再对缩短后的场景使用 Full 确认对象与调用位置。采样仍可能漏掉某一类分配，不能承诺“高频就一定不会漏”。修复后应比较同一操作次数下的分配量、GC 次数和帧时延。

`Track Memory Consumption (Native Allocations)` 追踪 `malloc()`/`new` 与对应释放。该任务采用按字节累计的采样阈值，当前默认采样大小为 2,048 字节；阈值更小会提供更密的快照，同时增加资源消耗。Native Remaining Size 是选定窗口内分配大小减释放大小，不能自动证明窗口外仍有泄漏。

## 各 Profiler 模式的性能开销与适用场景

任何采集都会改变被测系统，只是程度不同。应记录设备型号、系统版本、Android Studio 版本、构建类型、采集配置和复现脚本。涉及回归判断时，保留未录制基线；涉及方法级时延时，用 Macrobenchmark 或其他受控基准测试给出最终数字。

Android 10（API 29）加入 manifest `<profileable>`。当前 Android Studio 推荐从 release variant 构建 profileable App，以减少 debug 构建自身的性能成本。官方 Profiler 总览给出的推荐环境是 API 29 及以上、带 Google Play 的测试设备，并使用 Android Gradle Plugin 7.3 及以上；旧设备与旧 Studio 的能力应按相应版本文档判断。

两种构建类型的能力边界：

| 能力 | `profileable` release | `debuggable` |
|---|:---:|:---:|
| System Trace | 支持 | 支持 |
| Callstack Sample | 支持 | 支持 |
| Java/Kotlin methods | 支持，任务可用性仍受设备与 Studio 版本约束 | 支持 |
| Java/Kotlin allocations | 不支持 | 支持 |
| Heap dump | 不支持 | 支持 |
| Interaction timeline | 不支持 | API 26+ 支持 |

Native allocation 和 power rail 的可用性还受设备、系统及硬件数据源约束，不应只依据 `profileable` 或 `debuggable` 推断。Android Studio 菜单中的 `Profile 'app' with low overhead` 对应 profileable 路径，`Profile 'app' with complete data` 对应 debuggable 路径。

## Profiler 与 Perfetto 的互补关系

Android Studio 的优势是任务入口、App 筛选、源码跳转和较低的操作成本。Perfetto UI 的优势是系统范围浏览、Track 分组、自定义 SQL、Trace Processor 指标和更灵活的数据关联。Profiler 的 System Trace 也能展示系统活动，不能笼统写成“完全看不到系统”；差别主要落在展示范围和分析能力。

可按问题逐步升级：

1. 在 Android Studio 录制 System Trace，用 Threads、CPU Cores、Display、Process Memory 和 Power Rails 圈定时间窗。
2. App 在 Running 状态持续占用 CPU 时，补 Callstack Sample；Java 堆对象异常时，切换 Memory 任务。
3. 需要跨进程解释 Binder、SurfaceFlinger、调度或 GPU 完成事件，或需要 SQL 计算分位数和关键路径时，把 trace 导入 Perfetto UI。
4. 若现有 trace 缺少所需数据源，修改 Perfetto 配置并重新录制。界面切换无法恢复未采集的事件。

版本演进可作为理解旧 trace 的背景：Android 9 开始带入 Perfetto 服务基础设施，Android 10 把 Perfetto 作为平台级 tracing 工具并提供 heapprofd，Android 12 加入 FrameTimeline。当前平台结论固定到 Android 17 / API 37 / `android-17.0.0_r1`。

## Power Profiler（Android Studio Hedgehog+）

Android Studio Hedgehog 开始提供 Power Profiler。System Trace 负责记录并显示功耗数据，Power Profiler 用于浏览设备的 On-Device Power Rails Monitor（ODPM）结果。它和旧 Energy Profiler 的数据语义不同，迁移时不要把历史估算曲线与 power rail 测量值直接横向比较。

ODPM 把设备级功耗分成若干 rail，可能包括 CPU Big/Mid/Little、GPU、Display、Camera、Cellular、WLAN、GPS、UFS 和 Memory。具体 rail 由设备实现决定。数据表示整个设备子系统的功耗，前台 App、后台进程、系统服务和硬件自身活动都可能贡献读数。

例如，App 启动窗口内 Cellular rail 升高只建立了时间相关性。应再对照 Network Inspector、线程活动、系统网络事件和无操作基线，排除后台同步与信号环境后，才能把请求策略列为候选原因。

官方当前说明中，Power Profiler 的 ODPM 数据要求 Pixel 6 或更新的 Pixel 设备，并运行 Android 10（API 29）及以上。没有 ODPM 的设备仍可能通过库仑计和电池计量器提供容量、剩余电荷与瞬时电流；可用字段要以连接设备的结果为准。

## 生产设备中的受限采集入口

Android Studio Profiler 主要服务于连接设备上的交互式分析。若问题只能在真实用户设备或接近发布的构建中出现，应改用 `ProfilingManager` 请求或注册系统触发式采集；它有独立的版本、限流、脱敏、产物交付和隐私边界，不能按 IDE 任务的行为推断。

完整的 API 35—37 演进、`requestProfiling()`、后台 trace、触发器矩阵、结果文件管理与降级策略统一见 [14.11 ProfilingManager](11-profiling-manager.md)。本节只保留工具选择边界，避免两处维护同一套 API 细节。

## 常见问题与误区

**把 Java/Kotlin Methods 的时长当成生产时长。** 插桩已经改变执行过程。它适合看调用事件；发布性能数字要由低扰动 trace 或基准测试支撑。

**把样本百分比当成某次调用耗时。** Callstack Sample 结果描述选定窗口内的统计分布。一次短调用可能缺席，同一个方法的多次调用也已经聚合。

**看到内存曲线上升就宣布泄漏。** 曲线只提供候选时段。泄漏结论要有可重复路径、生命周期预期、GC 后对象存活和 GC Root 引用链。

**把 power rail 峰值归到前台 App。** ODPM 是设备级测量。需要用对照实验和同窗 trace 逐步排除其他进程与硬件状态。

**认为 profileable 什么都不能采。** 它覆盖多数低扰动任务；Java/Kotlin allocations、heap dump 和 Interaction timeline 要切换到 debuggable。

**认为 Android Studio System Trace 没有系统视角。** 它能展示调度、系统进程和渲染轨道，但 IDE 分析围绕所选 App，SQL 与跨进程深入分析更适合 Perfetto UI。

## 参考资料

- [Android Studio Profiler 总览](https://developer.android.com/studio/profile)
- [Android 系统追踪总览](https://developer.android.com/topic/performance/tracing)
- [Inspect traces](https://developer.android.com/studio/profile/inspect-traces)
- [Record a system trace](https://developer.android.com/studio/profile/cpu-profiler)
- [Sample the callstack](https://developer.android.com/studio/profile/sample-callstack)
- [Record Java/Kotlin methods](https://developer.android.com/studio/profile/record-java-kotlin-methods)
- [Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [Capture a heap dump](https://developer.android.com/studio/profile/capture-heap-dump)
- [Record Native allocations](https://developer.android.com/studio/profile/record-native-allocations)
- [Power Profiler](https://developer.android.com/studio/profile/power-profiler)
- [ProfilingManager API reference](https://developer.android.com/reference/android/os/ProfilingManager)
- [Android 17 `Trace.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)
- [Android 17 Perfetto source tree](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/)
