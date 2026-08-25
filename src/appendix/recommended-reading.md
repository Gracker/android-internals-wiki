# 附录 F：推荐阅读与资源

> 表格中的文章来自 [Gracker（高爷）博客](https://www.androidperformance.com/)，按对应章节主题分组。

本页收录博客中已有的对应文章；某章没有列出条目，只表示暂时没有匹配的博客文章。链接文章保留写作时使用的 Android 版本、工具界面和术语，阅读时应把长期有效的系统机制与当时的操作步骤分开理解。

---

## 怎么使用这份索引

Trace（性能追踪数据）按时间记录线程调度、系统事件和应用埋点。较早的文章使用 Systrace（早期 Android 系统追踪工具链），较新的文章使用 Perfetto（统一采集和分析多类追踪数据的平台）；它们都用于时间线分析，但采集配置、界面和可查询的数据并不相同。

先从知识库正文了解组件职责和诊断边界，再按症状选择案例文章。复现文章步骤时，以待测设备的 Android 版本、内核和厂商实现为准。表中保留原题里的线程名、API 名和 Trace 轨道名，方便在源码、日志与 Perfetto 中搜索。

## Ch01 Android 系统架构

`SystemServer` 是启动系统 Java 服务的入口类，运行在 `system_server` 进程中；`Binder` 是 Android 进程间调用的主要机制，具体调用模型可查 [AOSP Binder 概览](https://source.android.com/docs/core/architecture/ipc/binder-overview)。建议先读 [1.1 Android 分层架构、进程模型与线程协作](../part1-fundamentals/ch01-architecture/01-android-architecture-process-threading.md) 和 [1.9 Android IPC 全景与 Binder 性能](../part1-fundamentals/ch01-architecture/09-ipc-binder-performance.md)，再用这里的 Trace 案例观察服务启动、跨进程调用和线程等待。

| 系列 | 文章 | 链接 |
|------|------|------|
| Systrace 系列 | Systrace 系列——SystemServer | [链接](https://www.androidperformance.com/2019/06/29/Android-Systrace-SystemServer/) |
| Systrace 系列 | Systrace 系列——Binder | [链接](https://www.androidperformance.com/2019/12/06/Android-Systrace-Binder/) |

阅读 Binder 案例时，要把调用方等待、服务端执行和 Binder 线程池活动放在同一时间段核对；只看调用方的一段阻塞，无法判断耗时发生在哪个进程。

## Ch02 图形与渲染系统

`VSync` 提供显示节拍，`Choreographer` 据此安排应用帧回调，`MainThread` 与 `RenderThread` 分担 UI 和渲染工作，`SurfaceFlinger` 负责图层合成。Hardware Layer（硬件加速图层）讨论 View 内容的缓存方式，Triple Buffer（三缓冲）讨论生产者与消费者之间的缓冲区周转；二者解决的问题不同。

| 系列 | 文章 | 链接 |
|------|------|------|
| Systrace 系列 | Systrace 系列——Vsync | [链接](https://www.androidperformance.com/2019/12/01/Android-Systrace-Vsync/) |
| 独立文章 | Android Choreographer | [链接](https://www.androidperformance.com/2019/10/22/Android-Choreographer/) |
| Systrace 系列 | Systrace 系列——MainThread 与 RenderThread | [链接](https://www.androidperformance.com/2019/11/06/Android-Systrace-MainThread-And-RenderThread/) |
| Systrace 系列 | Systrace 系列——SurfaceFlinger | [链接](https://www.androidperformance.com/2020/02/14/Android-Systrace-SurfaceFlinger/) |
| 独立文章 | Android 硬件层（Hardware Layer） | [链接](https://www.androidperformance.com/2019/07/27/Android-Hardware-Layer/) |
| Systrace 系列 | Systrace 系列——Triple Buffer | [链接](https://www.androidperformance.com/2019/12/15/Android-Systrace-Triple-Buffer/) |

推荐按 VSync、Choreographer、MainThread/RenderThread、SurfaceFlinger 的顺序阅读，再根据问题补充 Hardware Layer 或 Triple Buffer。知识库的 [2.1 Android 渲染架构与版本演进](../part1-fundamentals/ch02-rendering/01-rendering-architecture-evolution.md) 说明组件关系；`BufferQueue` 是图形生产者与消费者交接缓冲区的队列，[2.8 BufferQueue](../part1-fundamentals/ch02-rendering/08-bufferqueue-gralloc-sync-fence.md) 解释它为什么会等待、排队或回退到较少的可用槽位。

## Ch03 输入系统

Input 在这里指从触摸或按键产生，到目标窗口收到并处理事件的整条分发路径。Trace 中的长延迟既可能来自系统分发，也可能来自应用主线程没有及时处理；[3.1 Input 分发、拦截与安全边界](../part1-fundamentals/ch03-input/01-input-dispatch-interception-security.md) 给出了区分两类问题所需的队列与时间点。

| 系列 | 文章 | 链接 |
|------|------|------|
| Systrace 系列 | Systrace 系列——Input | [链接](https://www.androidperformance.com/2019/11/04/Android-Systrace-Input/) |

读案例时记录事件进入系统、投递到窗口和应用开始处理的时间，避免把“触摸后画面晚更新”全部归因于 InputDispatcher。

## Ch04 内存管理

`onTrimMemory` 是系统向应用发送内存压力或进程状态提示的回调，回调到达并不等同于系统已经释放了应用内存。“后台应用被杀”通常指应用进程被系统终止；`lmkd` 是 Android 的低内存终止守护进程，会根据内存压力和进程优先级参与目标选择。应用侧的处理建议可查 [Android 内存管理文档](https://developer.android.com/topic/performance/memory)。

| 系列 | 文章 | 链接 |
|------|------|------|
| Memory 系列 | Android 性能优化——内存篇之 Google 内存优化 | [链接](https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-Google/) |
| Memory 系列 | Android 性能优化——内存篇之 Java 内存 | [链接](https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-Java/) |
| Memory 系列 | Android 性能优化——内存篇之 onTrimMemory | [链接](https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-onTrimMemory/) |
| 独立文章 | Android 后台应用被杀 Debug | [链接](https://www.androidperformance.com/2019/09/17/Android-Kill-Background-App-Debug/) |
| Memory 系列 | Android 性能优化——内存篇之 Android 资源 | [链接](https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-AndroidResource/) |

这些 Memory 系列文章发表于 2015 年，适合了解问题类型与排查思路；具体阈值、回调行为和系统回收策略要结合目标版本验证。可先读 [4.1 Android 与 Linux 内存管理全景](../part1-fundamentals/ch04-memory/01-android-linux-memory-overview.md)，涉及后台进程终止时再读 [4.3 lmkd、Cached App Freezer 与内存压力治理](../part1-fundamentals/ch04-memory/03-lmkd-freezer-memory-pressure.md)。

## Ch05 CPU 与调度

在 Trace 的调度时间线上，`Running` 表示线程正在某个 CPU 上执行，`Runnable` 表示线程已经具备运行条件、正在就绪队列等待，`Sleep` 表示线程在等待条件或定时器。这里的 `Sleep` 是线程状态，不等于整机进入低功耗休眠。

| 系列 | 文章 | 链接 |
|------|------|------|
| Systrace 系列 | Systrace 系列——CPU | [链接](https://www.androidperformance.com/2019/12/21/Android-Systrace-CPU/) |
| CPU 状态系列 | Systrace CPU 状态——Runnable | [链接](https://www.androidperformance.com/2022/01/21/android-systrace-cpu-state-runnable/) |
| CPU 状态系列 | Systrace CPU 状态——Running | [链接](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-running/) |
| CPU 状态系列 | Systrace CPU 状态——Sleep | [链接](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/) |

先用 [5.1 Linux 调度、EAS 与大小核架构](../part1-fundamentals/ch05-cpu-power/01-linux-eas-big-little-scheduling.md) 理解就绪队列、抢占和调度延迟，再读三个状态专题。线程长时间 `Runnable` 往往需要检查 CPU 竞争与优先级；长时间 `Sleep` 则要继续找它等待的锁、Binder 回复、I/O 或定时器。

## Ch07 卡顿（Jank）

Jank 指帧节奏异常带来的可见卡顿，常见表现包括帧超时、间隔突变或动画不连贯。“App 导致”与“System 导致”描述耗时来源，不能只凭卡顿发生在哪个应用界面来划分。

| 系列 | 文章 | 链接 |
|------|------|------|
| 独立文章 | Android Jank——App 导致的卡顿 | [链接](https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-App/) |
| 独立文章 | Android Jank——System 导致的卡顿 | [链接](https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-System/) |
| 独立文章 | Android Jank 调试 | [链接](https://www.androidperformance.com/2019/09/05/Android-Jank-Debug/) |
| 独立文章 | Android 后台动画优化 | [链接](https://www.androidperformance.com/2019/10/24/Android-Background-Animation/) |

从 [7.1 卡顿定义、分类与原因体系](../part2-performance/ch07-smoothness/01-jank-definition-causes.md) 建立帧时间标准，再按 [7.2 卡顿分析步骤](../part2-performance/ch07-smoothness/02-jank-methodology-scenarios-cases.md) 收集证据。两篇归因案例适合对照阅读：同一种掉帧现象，可能分别由应用工作量和系统资源竞争造成。

## Ch08 应用启动

“链式唤醒”指一个应用的行为继续触发其他应用或组件启动；Activity 启动模式控制实例与任务栈的复用规则，和启动速度优化是两个问题。先读 [8.2 App 冷启动链路与 Binder Trace 分析](../part2-performance/ch08-responsiveness/02-app-cold-start-binder-trace.md)，再读 [8.3 启动优化策略](../part2-performance/ch08-responsiveness/03-launch-optimization.md)。

| 系列 | 文章 | 链接 |
|------|------|------|
| 独立文章 | Android 应用链式唤醒 | [链接](https://www.androidperformance.com/2020/05/07/Android-App-Chain-Wakeup/) |
| 独立文章 | Android Activity 启动模式 | [链接](https://www.androidperformance.com/2019/09/01/Android-Activity-Lunch-Mode/) |
| 独立文章 | Android 应用启动优化 | [链接](https://www.androidperformance.com/2019/11/18/Android-App-Lunch-Optimize/) |

这组文章写于 2019—2020 年。后台启动限制、进程缓存和预编译策略会随 Android 版本变化，适合复用其中的观测思路，不宜直接照搬旧版本的策略或阈值。

## Ch09 ANR

ANR 是 Application Not Responding 的缩写，表示系统判定应用在特定交互或组件场景中未能及时响应，并开始记录诊断信息。不同 ANR 类型有各自的触发条件，不应统一套用“主线程超过 5 秒”这一条判断；版本与厂商差异可对照 [Android ANR 诊断文档](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)。

| 系列 | 文章 | 链接 |
|------|------|------|
| ANR 系列 | Android ANR 01——ANR 的设计 | [链接](https://www.androidperformance.com/2025/02/08/Android-ANR-01-ANR-Design/) |
| ANR 系列 | Android ANR 02——如何分析 ANR | [链接](https://www.androidperformance.com/2025/02/08/Android-ANR-02-How-to-analysis-ANR/) |
| ANR 系列 | Android ANR 03——ANR 案例分享 | [链接](https://www.androidperformance.com/2025/02/08/Android-ANR-03-ANR-Case-Share/) |

按设计、分析、案例的顺序阅读。知识库的 [9.1 ANR 机制、类型与触发条件](../part2-performance/ch09-anr/01-anr-mechanism-types-triggers.md) 说明触发与记录过程，[9.2 ANR 分析](../part2-performance/ch09-anr/02-anr-kernel-trace-diagnosis.md) 说明如何把 ANR 线程堆栈、系统日志和 Trace 证据对齐。

## Ch10 稳定性

低内存既可能直接触发进程回收，也可能通过页回收、交换、GC（垃圾回收）或重新启动增加延迟。看到低可用内存与卡顿同时发生，只能说明二者相关；还要用时间线确认卡顿窗口内发生了哪种内存活动。

| 系列 | 文章 | 链接 |
|------|------|------|
| 独立文章 | Android 低内存导致的卡顿 | [链接](https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/) |

可配合 [10.1 App 内存分析与案例](../part2-performance/ch10-memory-perf/01-app-memory-analysis-cases.md) 检查进程指标，并回到 [4.3 lmkd、Cached App Freezer 与内存压力治理](../part1-fundamentals/ch04-memory/03-lmkd-freezer-memory-pressure.md) 区分回收、压缩交换与进程终止。

## Ch13 Perfetto

Perfetto 是 Android 当前使用的系统追踪与分析平台，可把内核调度、系统服务、应用埋点等数据记录到同一个 Trace，再通过时间线或 SQL 查询，采集方式可查 [Perfetto 系统追踪文档](https://perfetto.dev/docs/getting-started/system-tracing)。Systrace 文章保留了早期工具的分析视角；实际采集可参照 [14.1 Trace 抓取](../part3-tools/ch14-perfetto/01-perfetto-intro-capture-reliability.md)，界面阅读可参照 [14.2 Perfetto View 解读](../part3-tools/ch14-perfetto/02-perfetto-ui-state-tracks.md)。

| 系列 | 文章 | 链接 |
|------|------|------|
| Systrace 系列 | Systrace 系列——开篇 | [链接](https://www.androidperformance.com/2019/05/28/Android-Systrace-About/) |
| Systrace 系列 | Systrace 系列——基础 | [链接](https://www.androidperformance.com/2019/07/23/Android-Systrace-Pre/) |
| Perfetto 系列 | Android Perfetto 101 | [链接](https://www.androidperformance.com/2024/03/27/Android-Perfetto-101/) |
| Perfetto 系列 | Perfetto 基础——什么是 Perfetto | [链接](https://www.androidperformance.com/2024/05/21/Android-Perfetto-01-What-is-perfetto/) |
| Perfetto 系列 | Perfetto 基础——如何获取 Trace | [链接](https://www.androidperformance.com/2024/05/21/Android-Perfetto-02-how-to-get-perfetto/) |
| Perfetto 系列 | Perfetto 基础——如何分析 Trace | [链接](https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/) |
| Perfetto 系列 | Perfetto 进阶——命令行打开大 Trace | [链接](https://www.androidperformance.com/2025/02/08/Android-Perfetto-04-Open-Big-Trace-With-Command-Line/) |
| Perfetto 系列 | Perfetto 专题——Choreographer | [链接](https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/) |
| Perfetto 系列 | Perfetto 专题——为什么是 120Hz | [链接](https://www.androidperformance.com/2025/04/26/Android-Perfetto-06-Why-120Hz/) |
| Perfetto 系列 | Perfetto 专题——MainThread 与 RenderThread | [链接](https://www.androidperformance.com/2025/08/02/Android-Perfetto-07-MainThread-And-RenderThread/) |
| Perfetto 系列 | Perfetto 专题——Vsync | [链接](https://www.androidperformance.com/2025/08/05/Android-Perfetto-08-Vsync/) |
| Perfetto 系列 | Perfetto 专题——Binder | [链接](https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/) |
| Perfetto 系列 | Perfetto 专题——CPU | [链接](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/) |

入门时先读“Android Perfetto 101”和三篇基础文章，再按数据规模决定是否阅读“大 Trace”。专题文章可按等待链选择：CPU 用于确认线程有没有获得执行时间，Binder 用于追踪跨进程调用，MainThread/RenderThread、Choreographer 和 Vsync 用于定位一帧在应用与显示管线中的延迟。

如果采集后缺少预期轨道，先检查数据源、缓冲区和设备能力。`TraceConfig` 是声明 Perfetto 数据源、缓冲区和采集时长的配置，参照 [14.1 Perfetto 入门、Trace 抓取与可靠性](../part3-tools/ch14-perfetto/01-perfetto-intro-capture-reliability.md) 与 [附录 C：TraceConfig 模板](perfetto-templates.md) 排查。遇到旧文章的菜单、轨道名或系统行为与设备不一致时，可查 [附录 A：Android 版本性能变更](version-changelog.md)。
