# 第 4 章：内存管理

Android 内存问题不只表现为 OOM。GC pause、page fault、direct reclaim、zram I/O、进程冻结与解冻、图形 buffer 占用、内存压力下的进程回收，都可能转化为启动变慢、交互卡顿、后台重建或整机抖动。

复核锚点如下：

- platform：Android 17 / API 37 / `android-17.0.0_r1`；
- kernel：`android17-6.18-2026-06_r6`；
- 历史演进允许保留旧版本行为，当前类名、配置和调用关系按固定 tag 核对；
- 设备厂商可能修改 allocator、GPU/display 驱动、zram、LMKD 参数和冻结策略，设备级结论需要运行时证据。

## 1. 内存域

同一个进程的“内存”由多个来源组成：

| 内存域 | 常见来源 | 管理者 | 主要观测 |
|---|---|---|---|
| ART managed heap | Java/Kotlin object、class metadata 的一部分 | ART allocator 与 GC | heap size、allocated bytes、GC cause/pause、object graph |
| Native heap | malloc/new、JNI、native library | Scudo/malloc、应用或库 | native heap profile、allocation callsite、RSS/PSS |
| Anonymous mapping | mmap、thread stack、JIT/运行时区域 | 进程与 kernel mm | smaps、RSS/PSS、page fault、swap |
| File-backed mapping/page cache | dex/oat/so、资源、文件 I/O | kernel page cache | file RSS/PSS、major/minor fault、reclaim |
| Graphic/shared buffer | GraphicBuffer、AHardwareBuffer、Camera/codec buffer | Gralloc、dma-buf、各 Producer/Consumer | dma-buf、gralloc、GPU/vendor counter、layer/buffer |
| Kernel memory | slab、page table、driver allocation | kernel 与驱动 | slabinfo、vmstat、meminfo、vendor trace |
| Compressed swap | zram 中的匿名页 | kernel reclaim、swap 与 zram | SwapTotal/SwapFree、zram mm_stat、swapin/swapout |

Java heap dump 看不到 native、graphics、page cache 和 kernel allocation。进程 RSS 也会把共享页面完整计入每个进程。选择指标前，要先说明调查的是 object retention、进程 footprint、系统 pressure，还是跨进程共享 buffer。

## 2. 压力处理不是固定流水线

内存压力下可能同时出现以下动作：

- ART 根据分配与堆策略发起 GC；
- 应用主动淘汰 cache，framework 也可能通过 trim 回调通知进程；
- kernel `kswapd` 做后台 reclaim，分配线程也可能进入 direct reclaim；
- compaction 为高阶连续页迁移可移动页面；
- 匿名页可以换出到 zram；
- cached app freezer 改变后台进程的可运行状态；
- lmkd 依据 PSI、meminfo、zone/watermark、`oom_score_adj` 和设备配置选择进程。

它们没有一条对所有设备都成立的先后顺序。GC 只管理目标进程的 ART heap；reclaim/compaction 在 kernel 中处理页面；lmkd 是 userspace daemon，负责选择和终止进程。应用无法直接控制 kswapd 或 lmkd，但可以减少持有、响应当前仍会到达的 trim level，并通过生命周期保存可恢复状态。

`/proc/meminfo` 的 `SwapTotal` 是配置容量，`SwapFree` 是未使用容量，`SwapCached` 是已换回内存但仍保留 swap entry 的页。三者不能相加当作“zram 使用量”。zram 还要结合 `/sys/block/zram*/mm_stat`、swap I/O 和压缩率。

## 3. PSS、RSS、USS 与 swap

| 指标 | 含义 | 适合回答的问题 | 局限 |
|---|---|---|---|
| RSS | 当前 resident page 总量，共享页在每个进程内完整计数 | 进程当前驻留规模、fault/reclaim 变化 | 多进程相加会重复计算共享页 |
| PSS | 共享页按 map count 比例分摊 | 多进程 footprint 归因、Android 常用进程比较 | 是分摊值，不能表示某进程独占 |
| USS/Private | 只归入该进程的 private pages | 杀掉进程后较可能直接释放多少用户页 | 不覆盖共享对象的系统总成本 |
| SwapPss | swap 中共享页的比例分摊 | 进程换出贡献 | 受 kernel、smaps 与设备实现影响 |

PSS 与 CPU cache locality 属于不同层级。cache line 描述 CPU cache 传输/一致性粒度，page 描述虚拟内存映射与记账粒度，ART card table 用于 GC remembered set。三者数值或现象接近时也不能互相替代。

## 4. 内容索引

### 4.1 基础模型

- [4.1 Android 内存模型全景](01-memory-overview.md)：进程地址空间、ART/native、共享页、graphics 与系统压力。
- [4.2 Linux 内核内存管理](02-linux-memory.md)：page、zone、LRU、reclaim、swap、compaction 与 OOM。
- [4.3 ART 虚拟机内存管理](03-art-memory.md)：ART heap、space、allocator、GC 与 native accounting。
- [4.4 Low Memory Killer](04-lmk.md)：lmkd、`oom_score_adj`、pressure signal 与 kill decision。
- [4.5 App 内存优化](05-app-memory-optimization.md)：用 profile 和生命周期证据减少 retention、峰值与抖动。
- [4.6 内存版本演进](06-memory-evolution.md)：按具体机制与 tag 对照版本变化。

### 4.2 ART 分配、GC 与后台任务

- [4.8 ART 分代 GC](08-art-generational-gc.md)：young/old collection、pause 与吞吐权衡。
- [4.9 FinalizerDaemon 与 ReferenceQueue](09-finalizer-referencequeue.md)：finalization、reference processing 与队列积压。
- [4.14 ART Region 碎片与 compaction](14-art-gc-region-fragmentation-compaction.md)：对象碎片、region space 与移动 GC。
- [4.16 ART TLAB 与对象分配](16-art-tlab-object-allocation-performance.md)：thread-local allocation、refill 与 slow path。
- [4.21 ART HeapTask 调度](21-art-heaptask-scheduling-pipeline.md)：HeapTask、TaskProcessor、GC/trim 任务与并发边界。
- [4.21 ART HeapTask 补充](4.21-art-heaptask-scheduling-pipeline.md)：同主题的补充说明，阅读时以固定 tag 的类和子类为准。

### 4.3 Kernel reclaim、compaction、zram 与 freezer

- [4.10 内存规整与 direct reclaim](10-memory-compaction-direct-reclaim.md)：高阶分配、reclaim stall、compaction 与 latency。
- [4.11 Cached App Freezer 与 GC](11-cached-app-freezer-gc-boundary.md)：冻结进程、GC 请求和解冻的责任边界。
- [4.12 ZRAM 与应用重启延迟](12-zram-compressed-swap-relaunch.md)：压缩、swap I/O、fault 与 relaunch 成本。
- [4.13 ANON_VMA_LAZY 事实核查](13-anon-vma-lazy-memory-optimization.md)：说明 Android 17/kernel 固定 tag 中没有该功能，避免把提案或错误材料当成现状。
- [4.20 Compaction 与 Freezer 对监控的影响](04.20-android17-memory-compaction-freezer-performance-impact.md)：区分 kernel compaction、ART compaction 与 cached-app freezer。

### 4.4 PSI、lmkd、trim 与 MemoryLimiter

- [4.15 PSI/LowMemDetector 与 lmkd](15-psi-lowmemdetector-lmkd-architecture.md)：区分 legacy detector、PSI monitor 与当前 lmkd 逻辑。
- [4.17 MemoryLimiter 与监控](17-android17-MemoryLimiter-与内存监控影响.md)：先确认设备是否启用对应 cgroup/BPF 路径，再解释统计影响。
- [4.18 MemoryLimiter 深入](4.18-android-17-memorylimiter-深度解析.md)：cgroup memory、BPF map、memcg 与 PSS 口径的边界。
- [4.18 onTrimMemory 与公平适配](04.18-android17-ontrimmemory-source-fair-adaptation.md)：framework trim dispatch、API 演进与应用 cache 策略。
- [4.36 lmkd 批量优先级命令与 thrashing](4.36-android17-lmkd-procs-prio-batch.md)：控制 socket、批处理命令和 thrashing 衰减的源码入口。
- [4.49 trimMemory API 演进](4.49-android17-trim-memory-api-evolution.md)：ComponentCallbacks2、ActivityThread 与 ART heap trim。
- [4.50 lmkd v2/PSI 分层治理事实核查](4.50-lmkd-v2-psi-tiered-pressure-governance.md)：把 AOSP 已存在机制与材料中的版本化命名分开。

`MemoryLimiter`、批量 lmkd command 或厂商 pressure policy 不应由 “Android 17” 四个字推导为全设备默认。文章中的 feature flag、build target、BPF program 与运行时状态必须逐项确认。

### 4.5 Page size、MTE、cache locality 与观测

- [4.7 16KB Page Size](07-16kb-page-size.md)：ABI、ELF alignment、mapping 与兼容性，不把 page size 当作固定性能增益。
- [4.9 Android 17 ARM MTE](4.9-android17-memory-tagging-extension-mte.md)：tagging mode、同步/异步 fault、进程启用条件与开销。
- [4.35 CPU cache locality 与 PSS](4.35-android17-cpu-cache-locality-pss-accounting.md)：区分 cache line、page、ART card 与 smaps 记账。
- [4.36 高级内存诊断](4.36-android17-advanced-memory-optimization.md)：按 Java/native/graphics/kernel/pressure 选择观测工具。

### 4.6 AppFlow 与 AI Agent 的能力边界

这组内容涉及产品、厂商方案或尚无 Android 17 公共 AOSP 实现的命名，只能用于兼容性设计和能力边界分析，不能写成平台内置能力。

- [4.04 AppFlow 与 Android 17 LMKD 兼容性](4.04-AppFlow与Android-17-LMKD兼容性方案.md)
- [4.5 AppFlow 与 lmkd 兼容性复核](4.5-appflow-lmkd-compatibility.md)
- [4.22 AI Agent 进程隔离与数据复用边界](4.22-android17-ai-agent-memory-sandboxed-data-reuse.md)

跨应用共享数据要使用有权限和生命周期约束的 IPC、provider、service、shared memory 或持久化机制。Android 17 没有一个名为“AI Agent Memory Sandbox”的通用内存子系统。

## 5. 按现象选择阅读顺序

| 现象 | 阅读顺序 | 优先证据 |
|---|---|---|
| Java heap 持续增长 | 4.1 → 4.3 → 4.5 → 4.8/4.9 | allocation profile、heap dump、GC、reference/finalizer queue |
| Native/PSS 增长 | 4.1 → 4.2 → 4.35 → 4.36 | smaps、native heap、mmap、shared mapping、callsite |
| 分配时偶发长卡顿 | 4.8 → 4.10 → 4.14 → 4.16 | GC pause、direct reclaim、compaction、TLAB refill |
| 后台恢复慢 | 4.11 → 4.12 → 4.15 → 4.4 | freezer、swapin fault、PSI、lmkd kill 与 process start |
| 低内存设备频繁杀进程 | 4.4 → 4.15 → 4.36 lmkd → 4.50 | PSI、vmstat、lmkd decision、oom_score_adj、kill reason |
| 图形内存偏高 | 4.1 → 第 2 章 DMA-BUF/Gralloc | dma-buf、gralloc、buffer 数、Producer/Consumer、GPU/vendor counter |
| 16KB 兼容或 MTE fault | 4.7 / 4.9 MTE | ELF alignment、mapping、tagging mode、fault address 与 stack |

内存问题采集时应记录 build、进程状态、前后台、总内存、swap/zram、PSI、刷新率/温度及复现场景。单张 `dumpsys meminfo` 快照只能说明采样时刻，趋势和因果关系要靠时间序列、allocation callsite 与系统 trace。

## 6. 固定源码入口

- [ART `gc/heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)：heap accounting、GC/trim 与 collector 入口；
- [lmkd `lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/lmkd.cpp)：pressure monitor、控制命令、进程选择与 kill；
- [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)、[`ComponentCallbacks2.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)：trim dispatch 与公开 callback；
- [`libmeminfo`](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/)：smaps、PSS 与系统内存读取；
- [bionic `heap_tagging.cpp`](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/libc/bionic/heap_tagging.cpp)：heap pointer tagging/MTE mode；
- [kernel `mm/vmscan.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)：LRU reclaim 与 direct/background reclaim；
- [kernel `mm/compaction.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/compaction.c)：page compaction；
- [kernel `zram_drv.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/block/zram/zram_drv.c)：zram block device 与统计；
- [kernel `psi.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c)：pressure stall accounting。

这些源码固定公共机制。内存性能结论还要结合目标设备的 kernel config、sysprop、lmkd 配置、zram 参数、cgroup 层级、GPU/allocator 实现与运行时采样。
