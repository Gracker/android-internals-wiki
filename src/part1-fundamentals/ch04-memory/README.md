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

本章按“模型 → 运行时 → 系统压力 → 产品边界”展开。每个主题只保留一个主入口，版本事实核查、观测方法和原先拆散的小节已经合并到对应主文。

| 编号 | 主题 | 解决的问题 |
|---|---|---|
| [4.1](01-memory-overview.md) | Android 内存模型全景 | 统一解释地址空间、RSS/PSS/USS、共享页、图形内存、zram 与系统压力。 |
| [4.2](02-linux-memory.md) | Linux 内核内存管理 | page、zone、Buddy、SLUB、reclaim、swap、compaction、DMA-BUF 与尚未合入的 `ANON_VMA_LAZY`。 |
| [4.3](03-art-memory.md) | ART 虚拟机内存管理 | heap space、allocator、TLAB、GC、native accounting、JIT 与 profile。 |
| [4.4](04-lmk.md) | 系统内存压力与 lmkd | PSI、`oom_score_adj`、控制协议、批量优先级、thrashing、kill reason 与 watchdog。 |
| [4.5](05-app-memory-optimization.md) | App 内存优化与诊断 | retention、Bitmap、native heap、PSS、cache locality、Perfetto 与线上分层诊断。 |
| [4.6](06-16kb-page-size.md) | 16 KB Page Size 与 Android 性能 | ELF/APK 对齐、linker 兼容、mmap 假设、迁移验证与性能测量。 |
| [4.7](07-art-generational-gc.md) | ART 分代 GC、Region 碎片与暂停分析 | young/full collection、Region 碎片、CC/CMC compaction 与暂停归因。 |
| [4.8](08-finalizer-referencequeue.md) | ART FinalizerDaemon、Cleaner 与 ReferenceQueue | 引用处理、串行终结、Cleaner 所有权与队列积压。 |
| [4.9](09-art-heaptask-scheduling-pipeline.md) | ART HeapTask 调度、启动维护与冻结边界 | GC、collector 切换、heap trim、启动维护任务与冻结状态下的调度。 |
| [4.10](10-memory-compaction-direct-reclaim.md) | 内存规整与直接回收性能边界 | 高阶分配、direct reclaim、compaction、PSI 与卡顿取证。 |
| [4.11](11-cached-app-freezer-gc-boundary.md) | Cached App Freezer、外部页回收与 GC 边界 | 进程冻结/解冻、app compaction、memcg reclaim、Binder 与 ART GC 的责任边界。 |
| [4.12](12-zram-compressed-swap-relaunch.md) | ZRAM 压缩交换与应用重启延迟 | 匿名页换出、MMD、writeback/prefetch、swapin fault 与恢复长尾。 |
| [4.13](13-android17-memorylimiter.md) | Android 17 MemoryLimiter | memcg 限制、`memory.high`、`memory.swap.max`、red-zone 轮询与超限诊断。 |
| [4.14](14-ontrimmemory-art-heap-trim.md) | onTrimMemory 回调与 ART Heap Trim | framework 回调分发、应用释放策略与 ART 异步裁剪之间的边界。 |
| [4.15](15-android17-memory-tagging-extension-mte.md) | Android 17 ARM MTE | tagging mode、同步/异步 fault、Scudo/Bionic 集成、启用条件与诊断。 |
| [4.16](16-cross-process-memory-ai-inference.md) | 跨进程内存共享与端侧推理预算 | SharedMemory/HardwareBuffer、PSS 记账、进程隔离与模型推理峰值。 |
| [4.17](17-product-prefetch-lmkd-boundary.md) | 产品侧内存预取与 lmkd 边界 | 外部预取模块的权限、预算、状态机、降级与 lmkd/MemoryLimiter 边界。 |

`MemoryLimiter`、批量 lmkd command 或厂商 pressure policy 不应由“Android 17”四个字推导为全设备默认。文章中的 feature flag、build target、BPF program 与运行时状态必须逐项确认。跨应用共享也必须使用有权限和生命周期约束的 IPC、provider、service、shared memory 或持久化机制；Android 17 没有名为“AI Agent Memory Sandbox”或“LMKD v2”的通用平台子系统。

## 5. 按现象选择阅读顺序

| 现象 | 阅读顺序 | 优先证据 |
|---|---|---|
| Java heap 持续增长 | 4.1 → 4.3 → 4.5 → 4.7/4.8 | allocation profile、heap dump、GC、reference/finalizer queue |
| Native/PSS 增长 | 4.1 → 4.2 → 4.5 → 4.15 | smaps、native heap、mmap、shared mapping、MTE fault |
| 分配时偶发长卡顿 | 4.3 → 4.7 → 4.9 → 4.10 | GC pause、HeapTask、direct reclaim、compaction、TLAB refill |
| 后台恢复慢 | 4.11 → 4.12 → 4.4 | freezer、swapin fault、PSI、lmkd kill 与 process start |
| 低内存设备频繁杀进程 | 4.4 → 4.10 → 4.12 → 4.13 | PSI、vmstat、lmkd decision、zram、memcg 与 kill reason |
| 图形内存偏高 | 4.1 → 第 2 章 DMA-BUF/Gralloc | dma-buf、gralloc、buffer 数、Producer/Consumer、GPU/vendor counter |
| 16 KB 兼容或 MTE fault | 4.6 / 4.15 | ELF alignment、mapping、tagging mode、fault address 与 stack |
| 多进程推理峰值或预取反噬 | 4.16 → 4.17 → 4.13 → 4.4 | PID/UID、PSS、fd、阶段峰值、memcg、lmkd decision |

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
