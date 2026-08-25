# 第 4 章：内存管理

Android 内存问题不只表现为内存不足（Out of Memory，OOM）。垃圾回收（GC）暂停、缺页异常（page fault）、分配线程直接回收内存（direct reclaim）、zram 压缩交换 I/O、进程冻结与解冻、图形缓冲区占用，以及内存压力下的进程回收，都可能造成启动变慢、交互卡顿、后台重建或整机抖动。

复核锚点如下：

- 平台版本：Android 17 / API 37 / `android-17.0.0_r1`；
- 内核版本：`android17-6.18-2026-06_r6`；
- 历史演进可以保留旧版本行为，当前类名、配置和调用关系按固定源码标签（tag）核对；
- 设备厂商可能修改内存分配器、GPU/显示驱动、zram、低内存终止守护进程（lmkd）参数和冻结策略，设备级结论需要运行时证据。

## 1. 内存域

同一个进程的“内存”由多个来源组成：

| 内存域 | 常见来源 | 管理者 | 主要观测 |
|---|---|---|---|
| ART 托管堆 | Java/Kotlin 对象、部分类元数据 | ART 分配器与 GC | 堆大小、已分配字节数、GC 原因与暂停时间、对象图 |
| 原生堆（Native heap） | `malloc/new`、JNI、原生库 | Scudo/`malloc`、应用或库 | 原生堆分析、分配调用点、RSS/PSS |
| 匿名映射 | `mmap`、线程栈、JIT/运行时区域 | 进程与内核内存管理模块 | `smaps`、RSS/PSS、缺页异常、交换空间 |
| 文件映射/页缓存 | dex/oat/so、资源、文件 I/O | 内核页缓存 | 文件 RSS/PSS、主要/次要缺页、页面回收 |
| 图形/共享缓冲区 | `GraphicBuffer`、`AHardwareBuffer`、相机/编解码器缓冲区 | Gralloc、dma-buf、各生产者/消费者 | dma-buf、Gralloc、GPU/厂商计数器、图层与缓冲区 |
| 内核内存 | slab、页表、驱动分配 | 内核与驱动 | `slabinfo`、`vmstat`、`meminfo`、厂商跟踪数据 |
| 压缩交换空间 | zram 中的匿名页 | 内核页面回收、交换机制与 zram | `SwapTotal/SwapFree`、zram `mm_stat`、换入/换出量 |

Java 堆转储（heap dump）看不到原生内存、图形内存、页缓存和内核分配。进程 RSS 也会把共享页面完整计入每个进程。选择指标前，要先说明调查的是对象滞留、进程内存规模（footprint）、系统内存压力，还是跨进程共享缓冲区。

## 2. 内存压力没有固定处理顺序

内存压力下可能同时出现以下动作：

- ART 根据分配与堆策略发起 GC；
- 应用主动淘汰缓存，Android Framework 也可能通过内存裁剪（trim）回调通知进程；
- 内核线程 `kswapd` 在后台回收页面，分配线程也可能进入直接回收；
- 内存规整（compaction）会迁移可移动页面，为需要连续物理内存的高阶分配腾出空间；
- 匿名页可以换出到 zram；
- 缓存应用冻结器（cached app freezer）改变后台进程的可运行状态；
- lmkd 依据压力停顿信息（Pressure Stall Information，PSI）、`meminfo`、内存区域及其水位线（zone/watermark）、`oom_score_adj` 和设备配置选择待终止进程。

这些动作在不同设备上没有统一的先后顺序。GC 只管理目标进程的 ART 堆；页面回收和内存规整在内核中处理页面；lmkd 是用户空间守护进程，负责选择并终止进程。应用无法直接控制 `kswapd` 或 lmkd，但可以减少不必要的持有、响应当前版本仍会送达的内存裁剪级别（trim level），并通过生命周期保存可恢复状态。

`/proc/meminfo` 的 `SwapTotal` 是配置容量，`SwapFree` 是未使用容量，`SwapCached` 是已经换回内存、但仍保留交换条目的页面。三者不能相加当作“zram 使用量”。分析 zram 还要结合 `/sys/block/zram*/mm_stat`、交换 I/O 和压缩率。

## 3. PSS、RSS、USS 与 swap

RSS（Resident Set Size，驻留集大小）统计驻留页面；PSS（Proportional Set Size，比例分摊集大小）会按共享映射数分摊共享页面；USS（Unique Set Size，独占集大小）只统计进程独占页面；`SwapPss` 则把换出后的共享页面按比例分摊。下表说明它们各自适合回答什么问题：

| 指标 | 含义 | 适合回答的问题 | 局限 |
|---|---|---|---|
| RSS | 当前驻留物理页总量，共享页在每个进程内完整计数 | 进程当前驻留规模、缺页/回收变化 | 多进程相加会重复计算共享页 |
| PSS | 共享页按映射数量比例分摊 | 多进程内存规模归因、Android 常用进程比较 | 是分摊值，不能表示某进程独占 |
| USS/Private | 只归入该进程的私有页面 | 终止进程后较可能直接释放多少用户空间页面 | 不覆盖共享对象的系统总成本 |
| SwapPss | 交换空间中共享页的比例分摊 | 进程对换出量的贡献 | 受内核、`smaps` 与设备实现影响 |

PSS 与 CPU 缓存局部性属于不同层级。缓存行（cache line）是 CPU 缓存传输和一致性维护的单位；内存页（page）是虚拟内存映射与记账的单位；ART 卡表（card table）则帮助 GC 记录跨区域引用，形成后续扫描使用的记忆集（remembered set）。三者即使数值或现象接近，也不能互相替代。

## 4. 内容索引


- [4.1 Android 与 Linux 内存管理全景](01-android-linux-memory-overview.md)
- [4.2 ART Heap、GC 与后台维护调度](02-art-heap-gc-maintenance.md)
- [4.3 lmkd、Cached App Freezer 与内存压力治理](03-lmkd-freezer-memory-pressure.md)
- [4.4 App 内存优化与诊断](04-app-memory-optimization.md)
- [4.5 16 KB Page Size 与 Android 性能](05-16kb-page-size.md)
- [4.6 ART FinalizerDaemon、Cleaner 与 ReferenceQueue](06-finalizer-referencequeue.md)
- [4.7 内存规整与直接回收性能边界](07-memory-compaction-direct-reclaim.md)
- [4.8 ZRAM 压缩交换与应用重启延迟](08-zram-compressed-swap-relaunch.md)
- [4.9 Android 17 ARM MTE 内存标签扩展实战](09-android17-memory-tagging-extension-mte.md)
- [4.10 跨进程内存共享与端侧推理预算](10-cross-process-memory-ai-inference.md)

## 5. 按现象选择阅读顺序

| 现象 | 阅读顺序 | 优先证据 |
|---|---|---|
| Java 堆持续增长 | 4.1 → 4.4 → 4.2/4.6 | 分配分析、堆转储、GC、引用/终结队列 |
| 原生内存或 PSS 增长 | 4.1 → 4.4 → 4.9 | `smaps`、原生堆、`mmap`、共享映射、MTE 故障 |
| 分配时偶发长卡顿 | 4.2 → 4.7 | GC 暂停、HeapTask、直接回收、内存规整、TLAB 补充 |
| 后台恢复慢 | 4.3 → 4.8 | 进程冻结器、换入缺页、PSI、lmkd 终止记录与进程启动 |
| 低内存设备频繁终止进程 | 4.3 → 4.7 → 4.8 | PSI、`vmstat`、lmkd 决策、zram、memcg 与终止原因 |
| 图形内存偏高 | 4.1 → 第 2 章 DMA-BUF/Gralloc | dma-buf、Gralloc、缓冲区数量、生产者/消费者、GPU/厂商计数器 |
| 16 KB 兼容或 MTE 故障 | 4.5 / 4.9 | ELF 对齐、内存映射、标签模式、故障地址与调用栈 |
| 多进程推理峰值或预取反噬 | 4.10 → 4.3 | 进程/用户 ID（PID/UID）、PSS、文件描述符（fd）、阶段峰值、memcg、lmkd 决策 |

采集内存问题时，应记录构建版本、进程状态、前后台状态、总内存、swap/zram、PSI、刷新率、温度和复现场景。单张 `dumpsys meminfo` 快照只能说明采样时刻；趋势和因果关系要靠时间序列、分配调用点与系统跟踪。

## 6. 固定源码入口

- [ART `gc/heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)：堆内存记账、GC/裁剪与收集器入口；
- [lmkd `lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/lmkd.cpp)：压力监控、控制命令、进程选择与终止；
- [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)、[`ComponentCallbacks2.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)：内存裁剪回调的分发与公开接口；
- [`libmeminfo`](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/)：`smaps`、PSS 与系统内存读取；
- [bionic `heap_tagging.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/heap_tagging.cpp)：堆指针标签与 MTE 模式；
- [kernel `mm/vmscan.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)：最近最少使用（LRU）页面回收，以及直接/后台回收；
- [kernel `mm/compaction.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/compaction.c)：页面规整；
- [kernel `zram_drv.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/block/zram/zram_drv.c)：zram 块设备与统计；
- [kernel `psi.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c)：压力停顿时间记账。

这些源码用于固定公共机制。内存性能结论还要结合目标设备的内核配置、系统属性（sysprop）、lmkd 配置、zram 参数、控制组（cgroup）层级、GPU/内存分配器实现与运行时采样。
