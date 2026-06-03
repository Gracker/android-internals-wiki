---


status: ready-for-review
task9_reviewed_date: "2026-05-21"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-21T11:31:10+08:00"
title: Linux 内核内存管理
chapter: '4.2'
section: '4.2'
drafted_date: '2026-03-30'
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-03-31'
reviewed_date: 2026-06-04
reviewed_by: openclaw-task6
task6_result: pass-light-edit
last_verified_against: Linux kernel 6.6 (android14-6.6-lts)
confidence: medium
sources:
- type: blog
  path: Cubox/五万字 - 深入理解Linux内存管理-2022-08-05.md
- type: blog
  path: Cubox/为什么 Linux 需要虚拟内存 - 面向信仰编程-2024-06-25.md
- type: blog
  path: Cubox/OPPO内存反碎片优化原理-2022-10-26.md
- type: blog
  path: Cubox/Android 系统 内存不足时，kswapd 导致的性能问题之冷热文件回收方案-2025-05-31.md
- type: paper
  path: Cubox/Silk-安卓GC与内核内存管理的进一步融合-2025-10-20.md (TACO '25)
- type: blog
  path: Cubox/荣耀在MGLRU内存回收上的发力或恰到好处-2026-02-25.md
- type: official
  path: developer.android.com - 16KB page size
- type: blog
  path: Cubox/LPC2025-Android MC主题-2026-01-10.md
tags:
- kernel
- memory
- buddy
- slab
- kswapd
- page-reclaim
- compaction
- ION
- DMA-BUF
- LRU
- MGLRU
- 16K-page
related_chapters:
- '4.1'
- '4.3'
- '4.4'
- '2.6'
pipeline_stage: task9_pending
task6_state: reviewed
task6_reviewed_date: "2026-05-21"
task9_state: pending
task9_result: needs-rework
task2b_state: fixed
task2b_result: reworked
last_task2b_rework_at: "2026-05-21T11:13:00+08:00"
review_notes: "2026-05-21 task9 deep-review: needs-rework。P1 1，Android 17 ART→MADV_COLD 实现链缺少 AOSP 源码锚点，已写入 queue/research-gaps。"
last_task9_review_log: "logs/deep-review/2026-05-21-11-deep-review.md"
last_task6_at: '2026-06-04T07:05:00+08:00'
last_task6_review_log: "logs/review/2026-05-21-12-review.md"
task6_review_notes: '2026-06-04 task6 revisiting-review: pass-light-edit。L1/L2 全部通过(禁用词0/AI套话0/高频词全0/元叙述0)。无B类大问题。task9 needs-rework + task2b 已 fixed,返回 task9 待复审。'
task9_review_notes: "2026-05-21 Task9 deep review: P1 Android 17 ART→MADV_COLD 仍以确定语气描述，源码锚点与内核语义未完成校验，写入 queue 条目 task9-20260521-4.2-art-madv-cold-still-assertive。"
last_task2b_at: "2026-06-04T04:55:01"
---


# Linux 内核内存管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 虚拟内存与物理内存映射：页表、TLB、Page Fault
- 🔹 Buddy 分配器与 Slab 分配器的基本原理
- 🔹 页面回收（Page Reclaim）：LRU、kswapd、direct reclaim
- 🔹 内存压缩（Memory Compaction）与碎片化
- 🔹 ION / DMA-BUF 在 Android 图形内存中的角色

### 扩展（可选深入）

- 🔸 16K Page Size（Android 15+ 支持）对内存和性能的影响
- 🔸 KASAN / MTE 等内存安全机制对性能的开销
- 🔸 Huge Pages 在 Android 上的实验

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Linux 内核内存管理

我们在 Perfetto 中分析 Android 性能问题时，经常会遇到一些"看不见的瓶颈"：应用卡顿但主线程没有耗时操作，启动变慢但 CPU 利用率并不高，滑动掉帧但渲染管线一切正常。这类问题的根因，往往藏在 Linux 内核的内存管理子系统里。

内核内存管理平时不显眼，但一旦出问题，整条性能链都会被拖慢。当系统内存紧张时，kswapd 线程开始工作，大量 CPU 时间花在页面回收上；当物理内存碎片化严重时，大块连续内存分配变慢，相机启动、游戏加载这类需要大块图形内存的操作就会被拖慢。在 Perfetto 中，我们更可能看到的是 kswapd 线程占用了异常的 CPU 时间，或者某个进程在缺页处理、内存分配相关路径上阻塞。

理解内核内存管理的机制，我们就能从 Perfetto 中读出更多信号：为什么 kswapd 突然活跃了？为什么 direct reclaim 导致了卡顿？为什么图形缓冲区分配失败？这些都是做 Android 性能分析时绕不开的问题。

[来源: Cubox/五万字 - 深入理解Linux内存管理-2022-08-05.md]
[来源: Cubox/Android 系统 内存不足时，kswapd 导致的性能问题之冷热文件回收方案-2025-05-31.md]

## 虚拟内存与物理内存映射

### 从虚拟地址到物理地址

现代操作系统都采用虚拟内存管理。CPU 访问的每一个内存地址都是虚拟地址，它需要经过 MMU（Memory Management Unit，内存管理单元）翻译成物理地址后，才能访问 DRAM 中的数据。

这个翻译过程依赖页表（Page Table）。页表是内核维护的一种数据结构，记录了虚拟页（Virtual Page）到物理页（Physical Page，也叫 Page Frame）的映射关系。在 64 位 Linux 系统上，为了高效管理巨大的地址空间，内核使用多级页表结构。ARM64 在 Linux 中默认使用四级页表（PGD → PUD → PMD → PTE），Linux 4.11 引入了五级页表支持。每一级页表就像一层目录索引，逐级缩小查找范围，最终定位到具体的物理页。

[已验证: 官方文档, kernel.org doc/vm — Linux 使用多级页表结构管理 64 位地址空间]

### TLB：页表的缓存

页表的查找是一个多级遍历过程，如果每次内存访问都要查 4-5 级页表，性能开销是无法接受的。所以 CPU 内部有一个专门的缓存叫做 TLB（Translation Lookaside Buffer），用来缓存最近使用过的虚拟地址到物理地址的映射。

TLB 的命中率直接影响程序的执行效率。当 TLB miss 发生时，CPU 需要遍历多级页表（即 Page Table Walk），这个过程可能需要几十到上百个时钟周期。这也是为什么内核和硬件都倾向于使用更大的页面（如 16KB 或 2MB Huge Page）——更大的页面意味着同等虚拟地址空间需要更少的页表项，TLB 能覆盖更大的地址范围。

[已验证: 官方文档, ARM Architecture Reference Manual — TLB 作为页表缓存减少地址翻译延迟]

### Page Fault：缺页异常

当 CPU 访问一个虚拟地址，但在页表中找不到对应的映射（页表项为空或无效）时，就会触发 Page Fault（缺页异常）。Page Fault 并不总是坏事——它是 Linux 实现按需分配（Demand Paging）和内存超卖的核心机制。

Page Fault 在 Android 上有几类典型场景：

- **首次访问新分配的内存**：进程调用 `mmap()` 或 `malloc()` 时，内核只记录了虚拟地址的分配，还没有分配物理页。等到进程第一次读写这块内存时，触发 Page Fault，内核此时才分配物理页并建立映射。这就是为什么我们在 Perfetto 中看到应用启动初期会有密集的 page fault。
- **页面被回收后再次访问**：当内存紧张时，内核可能回收了一些页面的物理内存。进程再次访问这些页面时，会触发 Page Fault——如果是文件页（File-backed Page），内核会从磁盘重新读入；如果是匿名页（Anonymous Page），且之前被写入了 swap/zRAM，则从压缩存储中解压恢复。
- **写时复制（Copy-on-Write）**：`fork()` 创建子进程时，内核只复制父进程的页表，两个进程指向相同的物理页。当其中一方尝试写入时，触发 Page Fault，内核此时才复制那个页面。Android 的 Zygote 进程正是利用这个机制——所有从 Zygote fork 出来的应用进程共享同一份物理内存页，直到它们需要修改时才各自持有副本。

[已验证: 官方文档, kernel.org — Demand Paging 和 Copy-on-Write 机制]
[来源: Cubox/为什么 Linux 需要虚拟内存 - 面向信仰编程-2024-06-25.md]

### 在 Perfetto 中的表现

在 Perfetto Trace 中，与虚拟内存相关的信号主要体现在：

- **Page Fault 计数**：通过 `ftrace` 的 `exceptions/page_fault_user` 和 `exceptions/page_fault_kernel` tracepoint，能分别观察用户态与内核态的缺页异常。抓 trace 时要在 `exceptions` 类下启用这两个事件，不要写成 `mm_page_fault`。如果要统计总 fault 数，还要区分 ftrace tracepoint 与 perf software counter 的口径。
- **kswapd 线程活动**：在 Perfetto 的进程列表中能看到 `kswapd0`（每个 NUMA 节点一个），它的 CPU 使用率直接反映了系统的内存压力。
- **Direct Reclaim 延迟**：当进程在内存分配路径上被迫同步回收页面时，在 Trace 中表现为该进程的长时间不可中断睡眠（`D` 状态）。

[待补充: Perfetto 中 page fault 和 kswapd 活动的 Trace 截图]

## Buddy 分配器与 Slab 分配器

Linux 内核管理物理内存采用三级分配体系：Buddy System → Slab Allocator → kmalloc/vmalloc。这三层各有分工，从大块连续内存到小块频繁分配，层层细化。

### Buddy System：大块内存的分配基石

Buddy 分配器是 Linux 物理内存管理的基础。它以页（通常 4KB）为最小单位，管理所有物理内存页。

Buddy 的核心思想很直接：将空闲内存按 2 的幂次方组织成不同的阶（order）。order-n 对应 2^n 个连续物理页，字节数 = 2^n × PAGE_SIZE。

以常见的两种页大小为例：

| order | 连续页数 | 4KB 页 | 16KB 页 |
|-------|---------|--------|---------|
| 0 | 1 | 4 KB | 16 KB |
| 1 | 2 | 8 KB | 32 KB |
| 2 | 4 | 16 KB | 64 KB |
| ... | ... | ... | ... |
| 10 | 1024 | 4 MB | 16 MB |

最高 order 受 `CONFIG_ARCH_FORCE_MAX_ORDER`（或 `MAX_PAGE_ORDER`）控制，不同内核配置和架构下可能不同，不能把 4KB 页下的 order-10=4MB 写成全版本通用结论。

分配时，如果请求的大小对应的 order 没有空闲块，就从更大的 order 拆分。比如请求 8KB（order-1），但 order-1 空闲列表为空，就从 order-2（16KB）拆成两个 8KB 的"伙伴"（buddy），分配一个，另一个放入 order-1 空闲列表。释放时反过来——如果被释放的块和它的"伙伴"都空闲，就合并成更大的块。这就是"伙伴"这个名字的由来：每一对相邻且大小相同的空闲块都是伙伴，它们可以合并。

Buddy 分配器的优势是能快速分配和释放连续的物理页，且能有效减少外部碎片。但它有一个固有的限制：只能分配 2 的幂次方大小的块。如果我们只需要 3KB，它也得给我们 4KB（一整个页），造成内部碎片。

为了进一步减少碎片，现代 Linux 内核还把页面按迁移类型（Migration Type）分组：不可移动页（Unmovable，如内核使用的页）、可回收页（Reclaimable，如文件缓存）、可移动页（Movable，如用户进程的匿名页）。把相同类型的页放在一起，使得在需要大块连续内存时，可以通过移动可移动页来腾出空间。

[已验证: L1 Linux kernel, mm/page_alloc.c — Buddy allocator 实现，支持 migration type 分组]

### Slab 分配器：内核对象的高效复用

Buddy 分配器以页为单位分配，但内核内部有大量远小于一页的数据结构需要频繁分配和释放——比如 `task_struct`（进程描述符）、`inode`（文件索引节点）、`dentry`（目录项）等。如果每次都通过 Buddy 分配整页然后自己切分，既浪费又低效。

Slab 分配器就是在 Buddy 之上构建的一层"批发-零售"机制。它从 Buddy 分配器获取连续的物理页，然后把这些页切成固定大小的对象（object），缓存起来。当内核需要某种类型的对象时，直接从 Slab 缓存中取一个已初始化好的实例，用完后不立即销毁，而是放回缓存中，下次直接复用。这样就避免了反复分配-初始化-销毁的开销。

Linux 内核历史上出现过三种 Slab 实现：

- **SLAB**：最早的实现，设计精巧但复杂度高，在大型系统上锁竞争严重。
- **SLOB**：面向嵌入式系统的极简实现，内存开销小但性能一般，适用于内存极度受限的场景。
- **SLUB**：当前 Linux 内核的默认实现（Android 的 GKI 内核也使用 SLUB）。它简化了 SLAB 的设计，减少了元数据开销，在多核系统上扩展性更好。

在实际的 Android 性能分析中，我们不太会直接观察 Slab 分配器的行为，但需要知道它的存在——当我们看到内核内存使用量异常增长时，可能需要检查 Slab 缓存的大小（通过 `/proc/meminfo` 中的 `Slab` 字段）。

[已验证: 官方文档, kernel.org — SLUB 为现代 Linux 内核默认 slab 实现]

### kmalloc 与 vmalloc

在 Slab 分配器之上，内核还提供了两个常用接口：

- **kmalloc**：分配物理连续的内存，适用于 DMA 等需要物理连续的场景。大小通常不超过几页，底层走 Slab 分配器。这是内核中最常用的分配接口。
- **vmalloc**：分配虚拟连续但物理不一定连续的内存。它把多段不连续的物理页映射到连续的虚拟地址空间。适用于需要大块内存但不要求物理连续的场景（如内核模块加载、大型缓冲区）。vmalloc 的开销比 kmalloc 大，因为需要修改页表，且访问时 TLB miss 更多。

在 Android 的性能分析中，如果发现 `vmalloc` 占用异常增大，可能是某些内核模块（如 GPU 驱动、相机驱动）在大量分配虚拟连续内存。

[来源: Cubox/五万字 - 深入理解Linux内存管理-2022-08-05.md]

## 页面回收（Page Reclaim）

当系统的空闲内存低于一定阈值时，内核需要回收一些已经被使用但"价值较低"的页面，腾出空间给更需要内存的进程。这个回收过程是 Linux 内存管理中最复杂也最影响性能的部分之一。

### LRU 链表：决定回收谁的标尺

Linux 内核使用 LRU（Least Recently Used）链表来跟踪页面的"热度"。内核为每个内存区域（zone）维护两组 LRU 链表：

- **Active List（活跃链表）**：存放最近被频繁访问的页面。
- **Inactive List（非活跃链表）**：存放有一段时间没被访问的页面，是回收的首选目标。

页面在两个链表之间移动遵循一个简单的"第二次机会"算法：页面首次被访问时进入 Inactive List，如果在 Inactive List 期间被再次访问，就提升到 Active List。长期不被访问的 Active 页面会逐渐降级回 Inactive List。回收时，优先从 Inactive List 尾部取页面。

页面还分为两大类，回收策略不同：

- **文件页（File-backed Page）**：对应磁盘上的文件内容。如果页面是干净的（没有被修改过），可以直接丢弃——下次需要时从文件重新读取即可。如果页面是脏的（被修改过但还没写回磁盘），需要先写回磁盘再回收。
- **匿名页（Anonymous Page）**：没有对应磁盘文件的页面，如堆内存、栈内存。回收匿名页需要将其内容压缩后存入 zRAM（Android 没有 swap 分区，使用 zRAM 替代）。

Android 上通常没有传统意义上的 swap 分区，所以匿名页的回收依赖 zRAM 压缩。因此，回收匿名页的 CPU 开销通常比回收干净文件页更高。

[已验证: 官方文档, kernel.org — LRU 双链表机制，active/inactive 页面分类]

### kswapd：后台回收守护线程

kswapd 是内核为每个 NUMA 节点创建的后台线程。它的工作方式可以用三个水位线来描述：

1. **High Watermark（高水位线）**：空闲内存充足，kswapd 不需要工作。
2. **Low Watermark（低水位线）**：空闲内存下降到此线以下，唤醒 kswapd 开始回收。
3. **Min Watermark（最低水位线）**：空闲内存极度紧张，触发 direct reclaim。

kswapd 被唤醒后，会持续回收页面，直到空闲内存恢复到 High Watermark 以上。这个过程的 CPU 开销和耗时直接影响了前台应用的性能——kswapd 虽然在后台运行，但它需要扫描 LRU 链表、处理页面、可能触发 I/O，这些都会占用 CPU 和 I/O 带宽。

在 Android 上，kswapd 过度活跃是一个常见的性能问题。Nubia 曾分享过一个案例：三方应用唯品会在内存不足时滑动严重掉帧，Perfetto 中能看到 kswapd 线程大量占用 CPU，同时把前台应用的 Page Cache 也回收了，导致前台应用读写文件时产生更多 page fault，形成恶性循环。

针对这类问题，一些 OEM 厂商采用了"冷热文件分离"策略：区分前台应用的热文件和后台应用的冷文件，优先回收后台冷文件的页面，保护前台应用的 Page Cache。

另一种思路是常态化少量回收——每分钟定时少量回收页面，避免内存不足时 kswapd 的突发性高开销。这种做法用可预测的低开销替代不可预测的高开销，与渲染优化中"分帧加载"的思路类似。

[已验证: L4 交叉验证, Nubia案例 + OPPO内存反碎片优化 + 荣耀MGLRU实践经验]
[来源: Cubox/Android 系统 内存不足时，kswapd 导致的性能问题之冷热文件回收方案-2025-05-31.md]

### Direct Reclaim：同步回收的代价

当内存分配请求发现空闲内存已经低于 Min Watermark 时，分配请求的进程会被迫自己执行页面回收——这就是 Direct Reclaim。与 kswapd 的异步回收不同，Direct Reclaim 是同步的：发出内存分配请求的进程必须等待回收完成才能继续执行。

如果前台应用在渲染帧的过程中触发 Direct Reclaim，这一帧的渲染时间就会被拉长，掉帧风险也会随之上升。在 Perfetto 中，Direct Reclaim 通常表现为进程长时间处于不可中断睡眠状态（`D` 状态），调用栈中通常会出现 `__alloc_pages_direct_reclaim` 相关函数。

[已验证: 官方文档, kernel.org — Direct reclaim 在内存分配路径中同步执行]

### MGLRU：下一代页面回收算法

传统的双链表 LRU 在 Android 场景下有一些固有缺陷：

- **粒度太粗**：只有 active 和 inactive 两个层级，难以精确区分页面的热度。
- **GC 干扰**：ART 虚拟机的 GC 线程在遍历对象时会访问大量页面，导致内核把这些页面判断为"热的"（pseudo-hot），即使 GC 访问后这些页面可能很长时间不会再被访问。
- **前台保护不足**：传统 LRU 不区分前台和后台进程的页面，可能错误地回收前台应用的热页面。

Google 为 Linux 内核开发了 MGLRU（Multi-Generational LRU），用多代（generation）模型替代了传统的双链表。页面按访问时间被分配到不同的 generation 中，越年轻的 generation 表示越近被访问过。回收时优先从最老的 generation 开始。

MGLRU 在 Android 上的实测效果显著：kswapd CPU 使用率明显下降，低内存杀进程（LMK）频率降低，应用启动速度提升。

但 MGLRU 在 Android 上也面临一些挑战。荣耀在 2026 年 LSF/MM 峰会上提出了几个实际问题：

1. **匿名页和文件页分布不均衡**：匿名页集中在最年轻的 2 个 generation，而文件页分散在多个 generation 且被过度回收，导致 16GB 设备上 MGLRU 可用内存比传统 LRU 少约 1GB。
2. **回收量难以精确控制**：memcg 回收时容易超出预期回收量。
3. **低端设备回收延迟**：在内存较少的设备上，单次回收可能耗时过长。

#### Android 版本与 MGLRU 启用状态

MGLRU 在 Linux 6.1 合入主线，但 Android 设备的实际启用状态取决于内核分支和 OEM 配置：

| Android 版本 | 内核分支 | CONFIG_LRU_GEN | 默认状态 | 验证命令 |
|-------------|---------|----------------|---------|---------|
| Android 10-12 | common 4.14-4.19 | 未合入主线 | 不可用 | — |
| Android 13 | common 5.10/5.15 | 可选 | OEM 自行决定是否开启 | `zcat /proc/config.gz \| grep CONFIG_LRU_GEN` |
| Android 14 | common 5.15/6.1 | 编译可用 | 多数旗舰 Pixel/高通平台已启用 | `zcat /proc/config.gz \| grep CONFIG_LRU_GEN` |
| Android 15 | GKI 6.1/6.6 | 编译可用 | 主流旗舰默认启用 | `zcat /proc/config.gz \| grep CONFIG_LRU_GEN` |
| Android 16 | GKI 6.12 | GKI 基线可用 | 6.12 common kernel 包含 MGLRU；是否启用取决于 CONFIG_LRU_GEN/CONFIG_LRU_GEN_ENABLED 和 `/sys/kernel/mm/lru_gen/enabled` | `cat /sys/kernel/mm/lru_gen/enabled` |

Android 16 (GKI 6.12) 的 common kernel 包含 MGLRU 基础设施。是否作为平台强制基线，需要 CDD/VTS 或 GKI config 引用确认——当前可验证的判断方式是检查 `CONFIG_LRU_GEN`、`CONFIG_LRU_GEN_ENABLED` 和 `/sys/kernel/mm/lru_gen/enabled`。对于非 GKI 设备（部分低端机型使用旧内核），MGLRU 的可用性仍取决于 OEM 的内核配置。

[待验证: Android 16/17 非 GKI 低端设备的 MGLRU 覆盖率]

[已验证: 官方文档, kernel.org — MGLRU 自 Linux 6.1 合入主线]
[来源: Cubox/荣耀在MGLRU内存回收上的发力或恰到好处-2026-02-25.md]
[来源: Cubox/Silk-安卓GC与内核内存管理的进一步融合-2025-10-20.md]

#### 源码分析：MGLRU vs 传统双级 LRU 锁竞争

传统双级 LRU 的核心问题是 **per-node 全局 `lru_lock` 的竞争**。`struct lruvec` 持有单一 `spinlock_t lru_lock`，所有 CPU 上的页面引用事件（`folio_mark_accessed()` / `activate_page()`）和页面回收路径（`shrink_inactive_list()` / `shrink_active_list()`）都在这把锁下操作。在 8+ 核的手机 SoC 上，多核并发访问导致这把锁成为瓶颈。

MGLRU 通过三个机制削减锁竞争（以下源码以 Linux 6.12 / Android common kernel 为参考）：

**1. 减少 per-lruvec 锁内的操作量**

传统 LRU 和 MGLRU 都围绕 `lruvec`（每个 node+memcg 组合）组织 LRU 链表。MGLRU 的优势不在于引入 per-lruvec——传统 LRU 也有 `struct lruvec`——而在于减少了锁内的操作量和持有时间。

```c
// 伪代码，基于 include/linux/mmzone.h / mm/vmscan.c
// lruvec 通过 mem_cgroup_lruvec() 获取
struct lruvec *mem_cgroup_lruvec(struct mem_cgroup *memcg, struct pglist_data *pgdat);
// 不同 App（不同 memcg）的内存回收操作各自的 lruvec
```

**2. `folio_update_gen()` 无锁化**

传统 LRU 每次页面引用都做 `list_move()`（持锁）。MGLRU 用 generation 编号替代：页面引用时只更新 `folio->flags` 中的 `LRU_GEN_MASK` 位（不需要锁），由 `lru_gen_look_around()` 做批量 PTE accessed bit 清除：

```c
// 伪代码，基于 mm/vmscan.c lru_gen_look_around()
void lru_gen_look_around(struct page_vma_mapped_walk *pvmw)
{
    for (i = 0, addr = start; addr != end; i++, addr += PAGE_SIZE) {
        pte_t ptent = ptep_get(pte + i);
        if (!pte_young(ptent))
            continue;
        ptep_test_and_clear_young(vma, addr, pte + i);  // 批量清除 accessed bit
        old_gen = folio_update_gen(folio, new_gen);  // 只更新 flags，无锁
    }
}
```

**3. `evict_folios()` 锁持有时间从 O(n) 降到 O(1)**

传统 `shrink_inactive_list()` 在整个扫描期间（可能数千次 `list_move()`）持有 `lru_lock`。MGLRU 的 `evict_folios()` 持锁后只做一代链表的批量 `isolate_folios()`，然后立即释放锁：

```c
// 伪代码，基于 mm/vmscan.c evict_folios()
static int evict_folios(struct lruvec *lruvec, ...)
{
    spin_lock_irq(&lruvec->lru_lock);
    scanned = isolate_folios(lruvec, sc, swappiness, &type, &list);
    // try_to_inc_min_seq() 也在这里执行
    spin_unlock_irq(&lruvec->lru_lock);  // 立即释放！

    // shrink 在锁外执行
    reclaimed = shrink_folio_list(&list, pgdat, sc, &stat, false);
}
```

**sysfs 监控接口**：`/sys/kernel/mm/lru_gen/enabled`（bitmask 主开关）+ `/sys/kernel/mm/lru_gen/lru_gen`（各代页面数量直方图）。

[来源: Cubox/Silk-安卓GC与内核内存管理的进一步融合-2025-10-20.md]

### [自动发现] Silk：GC 与内核页面回收的协同优化

华中科技大学在 TACO '25 上发表的 Silk 论文提出了一个更深层的观察：ART 虚拟机的 GC 行为会严重干扰内核的 LRU 判断。论文发现了"Object Hotness Inversion"（对象热度倒置）问题：

1. **应用线程维度**：热页中有 80% 的对象对应用来说是冷的（pseudo-hot），导致内核错误地保留了大量不必要的页面。
2. **GC 线程维度**：GC 遍历对象时不区分冷热，访问冷页时触发不必要的内存换入；同时 GC 最近访问过的冷页被误判为热页。

Silk 的解决方案是在对象级别跟踪热度信息，并将其传递给内核的页面回收机制。实测效果：应用线程换入减少 18.6%-48.4%，GC 线程换入减少 15.2%-51.2%，JankFrame 降低 55.3%-60.7%。

这个工作展示了 Android 内存优化的一个前沿方向：让虚拟机层和内核层协同工作，而不是各自为政。

[来源: Cubox/Silk-安卓GC与内核内存管理的进一步融合-2025-10-20.md (TACO '25)]

#### 待验证方向：madvise(MADV_COLD) 作为 GC-内核协同路径

[状态: 截至 Android 17（API 37）公开 AOSP 源码，ART runtime/gc 中未找到对 `MADV_COLD` 的直接调用；以下描述基于 Silk 论文方向和社区提案，不是已进入 AOSP 公开树的 Android 17 实现。]

Silk（TACO '25）论文提出了一种 GC-内核协同思路：ART 虚拟机在 GC 标记阶段识别出对象冷热信息后，由 GC 向内核传达哪些页面近期不会再被访问，从而帮助内核更准确地回收冷页。

这条路径的具体工作方式是：GC 对识别为冷对象所在的匿名页调用 `madvise(MADV_COLD)`。内核处理 `MADV_COLD` 的实际路径取决于内核版本和 LRU 实现：

- **`mm/madvise.c` 中的 MADV_COLD 处理**：对目标 `vma` 范围内的页面调用 `folio_deactivate()`，清掉 `referenced` flag 并将 folio 移到 inactive LRU 链表的尾部。在 MGLRU（Multi-Gen LRU，Linux 5.18+）中，等效操作是清除 generation 计数的 `PG_referenced` 标记，使页面在下一次老化（aging）扫描时更容易被降代。
- **实际效果**：这些页面不再因为 GC 扫描时的访问而被错误标记为"活跃"（前面提到的 pseudo-hot 问题），从而在内存压力下优先被回收，减少不必要的 swap-in。

**版本边界**：AOSP `platform/art`（截至 android-16.0.0_r1）与主线（main）均未发现 ART runtime/gc 中对 `MADV_COLD` 的显式调用点。ART GC 触发 `MADV_COLD` 的精确调用点、触发条件、频率和指标口径目前仍是待研究项（已在 `research-gaps.md` 中记录）。在没有 AOSP commit、release note 或独立 benchmark 支撑之前，本节不将 MADV_COLD 路径作为正文结论。

[来源: external-review 2026-04-28-ch04-02-linux-memory 与 Silk 论文（TACO '25）概念参考]

## 内存压缩（Memory Compaction）与碎片化

### 物理内存碎片化的本质

物理内存碎片化是嵌入式和移动设备上特别棘手的问题。随着系统运行时间增长，内存页被分配、释放、再分配，空闲页面逐渐散落在不同的物理地址区域，导致虽然总空闲内存够用，但无法找到足够大的连续物理内存块。

在 Android 上，这个问题尤其突出：

- **图形内存**：GPU、相机、视频编解码器等硬件模块通常需要物理连续的大块内存（GPU buffer、camera buffer）。碎片化严重时，这些硬件模块的内存分配会变慢甚至失败。
- **大页面支持**：Transparent Huge Pages（THP）需要 2MB 连续物理内存（512 个连续的 4KB 页），碎片化使得 THP 难以生效。

OPPO 曾经详细分析过这个问题，并提出了两种反碎片化机制：

- **Multi-Freearea（MF）**：将空闲物理页面集中在某段物理页帧号（pfn）范围内，增大空闲页面合并成大块物理页面的概率。
- **Centralize-Small-VirtualMem（CSVM）**：将小段虚拟内存分配集中在特定的虚拟地址范围，减少虚拟地址空间被"污染"。

[来源: Cubox/OPPO内存反碎片优化原理-2022-10-26.md]

### kcompactd 和 Direct Compaction

内核有两种内存压缩机制：

- **kcompactd**：类似 kswapd 的后台守护线程，在后台异步执行内存压缩。它会把可移动的页面迁移到一起，腾出连续的空闲区域。kswapd 在回收页面后可能会唤醒 kcompactd 进行后续的碎片整理。
- **Direct Compaction**：同步压缩，在分配大块连续内存失败时触发。进程必须等待压缩完成才能继续执行，类似于 Direct Reclaim 对性能的影响。

在 Perfetto 中，如果我们看到应用进程出现长时间 D 状态睡眠，且调用栈中出现 `__alloc_pages_direct_compact`，说明该进程在等待内存压缩完成。这通常意味着系统碎片化严重或者可用内存不足。

[已验证: 官方文档, kernel.org — Memory compaction 在页面分配路径中作为 reclaim 的补充]

### CMA（Contiguous Memory Allocator）

CMA 是 Linux 内核为解决大块连续内存分配问题而引入的一种机制。它在系统启动时预留一块连续的物理内存区域，平时可以给可移动页使用，当需要大块连续内存时，把这块区域内的页面迁移走即可。

Android 的很多硬件模块（如相机、多媒体编解码器）依赖 CMA 来保证大块连续内存的供应。我们可以在 `/proc/meminfo` 中看到 `CmaTotal` 和 `CmaFree` 字段，反映 CMA 区域的使用情况。

[已验证: 官方文档, kernel.org — CMA 机制说明]

## ION / DMA-BUF 在 Android 图形内存中的角色

### 从 ION 到 DMA-BUF Heaps 的演进

Android 的图形内存管理经历了一次重要的架构迁移：从 ION 分配器迁移到 DMA-BUF Heaps。

ION 是 Android 4.0（Ice Cream Sandwich）引入的内存分配器，目的是统一不同硬件模块（GPU、相机、视频编解码器等）的内存分配接口。ION 通过一个 `/dev/ion` 设备节点提供分配接口，不同的 heap（如 system heap、carved-out heap）通过 flags 和 heap mask 来区分。

但 ION 有几个严重问题：

- **安全性差**：所有分配都通过一个 `/dev/ion` 节点，权限控制粒度太粗。
- **ABI 不稳定**：ION 的 IOCTL 接口不在主线 Linux 内核中维护，不同厂商的实现各不相同，与 GKI（Generic Kernel Image）的 ABI 稳定性目标冲突。
- **实现碎片化**：不同 SoC 厂商自定义了各种 heap 类型和 flags，导致碎片化严重。

从 Android 12 和 GKI 2.0（Linux 5.10+）开始，Google 用 DMA-BUF Heaps 框架替代了 ION。DMA-BUF Heaps 的核心改进：

- **每个 heap 是独立的设备节点**：如 `/dev/dma_heap/system`、`/dev/dma_heap/system_uncached`，可以通过 sepolicy 精确控制每个 heap 的访问权限。
- **ABI 稳定**：DMA-BUF Heaps 的接口在主线 Linux 内核中维护，属于稳定的 UAPI。
- **标准化**：统一了 heap 的命名和语义，减少了厂商间的差异。

[已验证: 官方文档, source.android.com — ION to DMA-BUF Heaps 迁移, Android 12+]

### DMA-BUF 的工作机制

DMA-BUF 是 Linux 内核中用于跨设备、跨进程共享大块内存的框架。在 Android 图形系统里，Gralloc 分配出的图形缓冲区通常会以 dma-buf fd 或 handle 的形式在 App、SurfaceFlinger、GPU 和 HWC 之间传递。

1. **Gralloc（Graphics Allocator）**：Gralloc 底层从 DMA-BUF Heaps 申请 buffer，并拿到一个 dma-buf fd。这里不能把所有 heap 都写成“物理连续”。`/dev/dma_heap/system` 提供的是虚拟连续 buffer，只有 CMA 类型 heap（例如 `default_cma_region`）才保证物理连续。设备是否需要物理连续，还取决于 IOMMU 和具体硬件能力。
2. **BufferQueue 传递**：App 通过 BufferQueue 传递的是 dma-buf fd 或其封装句柄，不是像素数据本身。SurfaceFlinger 导入同一个 dma-buf 对象。CPU 侧调试或软件访问可以通过 `mmap()` 建立映射，但合成阶段更常见的是驱动侧导入，而不是所有参与方都去访问同一段 CPU 虚拟地址。
3. **GPU / HWC 导入**：SurfaceFlinger、GPU 和 HWC 会按各自驱动模型导入 dma-buf。支持 IOMMU 的设备可以导入非物理连续 buffer，缺少这类映射能力的硬件才更依赖 CMA 这类物理连续分配。

这个 fd 传递机制减少了数据副本。各组件共享的是同一个 dma-buf 对象，但 CPU 访问方式、GPU/HWC 的导入方式、是否要求物理连续，取决于 heap 类型和硬件内存映射能力，不能压成“始终共享同一块物理连续内存”。

在 `/proc/meminfo` 中，`DMA-BUF` 相关的字段（如 `DmaBufTotal`、`DmaBufMapped`、`DmaBufUnmapped`）反映了图形缓冲区的内存使用情况。在 Perfetto 的内存分析视图中，DMA-BUF 通常占据了设备总内存的相当大比例（在高端设备上可能达到数百 MB 甚至超过 1GB）。

[已验证: 官方文档, source.android.com — Graphics buffer 管理与 DMA-BUF 框架]

### 在 Perfetto 中的表现

图形内存相关的性能问题在 Perfetto 中通常表现为：

- **DMA-BUF 分配延迟**：当系统碎片化严重或内存紧张时，Gralloc 的 DMA-BUF 分配可能变慢，在 Trace 中表现为 RenderThread 或 SurfaceFlinger 的长时间阻塞。
- **GPU 内存压力**：GPU 驱动的内存使用（部分通过 DMA-BUF 管理）会影响整体系统内存可用量。
- **Buffer 被回收导致重新分配**：Android 14 引入了强制清除 buffer 缓存的机制，在内存紧张时会回收空闲的图形 buffer，后续需要时重新分配。

Google 在 LPC 2025 上介绍了使用 eBPF 替代 sysfs 来统计 DMA-BUF 使用量的工作，目标是提供更精确、更低开销的图形内存监控能力。

[来源: Cubox/LPC2025-Android MC主题-2026-01-10.md]
[待补充: Perfetto 中 DMA-BUF 相关 Track 和事件的 Trace 截图]

了解了图形内存的底层机制后，我们再来看一个影响整个内存管理架构的系统性变更：16KB 页面大小。前面讨论的 Buddy 分配器、TLB、Page Fault 等机制，在页面大小从 4KB 增大到 16KB 后，行为都会发生变化。

## 16K Page Size 对内存和性能的影响

Android 15 开始支持 16KB 页面大小（之前一直是 4KB），这是一个对整个 Android 生态影响深远的变更。

### 为什么要增大页面大小

增大页面大小的主要动机来自硬件和性能两个方面：

- **减少 TLB miss**：更大的页面意味着同等地址空间需要更少的页表项，TLB 的覆盖范围更大。对于内存密集型应用，TLB miss 率会下降。
- **减少页表内存开销**：每个页表项本身也占内存。页面越大，相同内存量需要的页表项越少，页表占用的内存也越少。
- **减少 Page Fault 次数**：每次 Page Fault 可以映射更大的地址范围，减少总的 Page Fault 次数。实测中，16KB 页面使 `page_fault_user` 频率骤降约 75%，显著缩短了 IO 密集型路径的内核等待时间。

Google 的实测数据（来自 developer.android.com）：

| 指标 | 改善幅度 |
|------|---------|
| 应用启动时间 | 平均降低 3.16%，部分应用最高 30% |
| 功耗（启动时） | 平均降低 4.56% |
| 相机热启动 | 平均快 4.48% |
| 相机冷启动 | 平均快 6.60% |
| 系统启动时间 | 约改善 8%（约 950ms） |

[已验证: 官方文档, developer.android.com — 16KB page size 性能数据]

### 对应用开发的影响

16KB 页面大小主要影响使用原生代码（NDK）的应用。涉及的关键变更：

- **ELF 对齐要求**：native library（.so 文件）的 ELF LOAD 段必须对齐到 16KB。4KB 对齐的 .so 文件在 16KB 页面设备上可能导致功能异常或无法加载。
- **内存使用增加**：更大的页面意味着更多的内部碎片——如果一个对象只用了 1KB，也要占用整个 16KB 页面。平均内存使用会有小幅增加。
- **mprotect 粒度**：`mprotect()` 的最小粒度从 4KB 变为 16KB，可能影响一些内存保护策略。

Google 在 LPC 2025 上分享了为 16KB 页面适配旧 ELF 库的技术探索，包括"Simple Shift"方案和"memfd 双映射"方案。其中最棘手的挑战来自亚洲市场的应用——重度混淆的 ELF 和自定义 loader 使得自动化适配非常困难。

从 2025 年 11 月 1 日起，Google Play 要求所有新应用和更新必须支持 16KB 页面大小。

[来源: Cubox/LPC2025-Android MC主题-2026-01-10.md]
[已验证: 官方文档, developer.android.com — 16KB page size 要求]

### 在 Perfetto 中的表现

16KB 页面大小对 Perfetto 分析的影响：

- Page Fault 频率下降，但单次 Page Fault 映射的内存量增大。
- kswapd 的回收效率变化——每回收一个页面释放 16KB 而非 4KB，但页面移动的开销也相应增大。
- Slab 分配器行为变化——对象在 16KB 页面中的布局不同，可能影响 Slab 的利用率。

[待验证: 16KB 页面在 Android 16 GKI 内核中的实际 Perfetto 表现]

## 扩展方向：内存安全与大页面

本节先覆盖 Linux 内核内存管理的主干机制。后面还有两个与性能直接相关的扩展方向：

**内存安全机制**：KASAN（Kernel Address SANitizer）通过 shadow memory 检测内核空间的越界访问，但会带来约 2-3 倍的内存开销和可感知的性能下降，通常只在调试版本启用。MTE（Memory Tagging Extension）是 ARMv8.5+ 引入的硬件级内存标签机制，开销远低于 KASAN——快手在 2023 年分享了 MTE 在 Android 上的探索，标签检查的额外延迟约 1-2%。GWP-ASan 采用采样策略，在生产环境中以极低概率（约千分之一）分配带毒标记的内存块，能在几乎零开销的前提下捕获部分内存安全漏洞。

**Huge Pages**：Transparent Huge Pages（THP）在服务器场景中已被广泛采用，但在 Android 上仍处于实验阶段。THP 需要 2MB 连续物理内存（512 个 4KB 页），碎片化严重的移动设备很难满足。Android 15 的 pKVM（Protected Kernel Virtual Machine）对 THP 的支持也在探索中。大页面的核心权衡是：TLB miss 率降低带来的性能收益 vs. 内存浪费（内部碎片增加）vs. 碎片化加剧的风险。对于移动场景，16KB page size 可能是比 THP 更务实的折中方案。

[来源: Cubox/Andriod Native - 采样型内存调试工具GWP-ASan - 掘金-2022-01-14.md]
[来源: Cubox/内存检测工具KASAN：精准定位内存越界的"幽灵"-2025-05-29.md]
[来源: Cubox/Android内存安全革命性改变：快手MTE探索与实践-2023-05-23.md]

## 与其他机制的关系

Linux 内核内存管理不是孤立的，它与 Android 系统的其他层面有密切关联：

- **与 ART 虚拟机（4.3 节）**：ART 的 GC 和内核的页面回收相互影响。Silk 论文展示了 GC 行为对内核 LRU 判断的干扰，说明两个层面需要协同优化。
- **与 Low Memory Killer（4.4 节）**：LMK 是页面回收失败后的兜底机制——当 kswapd 和 direct reclaim 都无法满足需求时，LMK 会杀掉后台进程释放内存。
- **与 SurfaceFlinger（2.6 节）**：SurfaceFlinger 的图形缓冲区通过 DMA-BUF 管理，是系统内存的大户。
- **与 CPU 调度（5.1 节）**：kswapd 和 kcompactd 都是内核线程，它们的 CPU 使用会影响前台应用的调度。
- **与存储 I/O（6.3 节）**：页面回收中的脏页回写会产生 I/O 压力，影响前台应用的文件读写性能。

## 常见问题与误区

### "物理内存够用就不会有性能问题"

这是最常见的误解。即使物理内存总量充足，碎片化问题也会导致大块连续内存分配变慢。手机长期运行（不重启）后，相机或游戏的启动速度下降，很大程度上就是因为碎片化。

### "kswapd 是后台线程，不影响前台"

kswapd 虽然在后台运行，但它占用 CPU 和 I/O 带宽，会直接影响前台应用的性能。更严重的是，kswapd 可能回收前台应用的 Page Cache，导致前台应用的文件读写变慢，形成恶性循环。

### "Android 没有 swap，所以不用担心内存回收延迟"

Android 使用 zRAM 替代 swap。回收匿名页时，内核需要将其压缩后存入 zRAM，这个压缩过程消耗 CPU。在内存压力大时，频繁的 zRAM 压缩/解压缩本身就是性能瓶颈。

### "DMA-BUF 内存不算应用的内存"

通过 DMA-BUF 分配的图形缓冲区在 `/proc/<pid>/smaps` 中是可以追踪的。一个 App 的 Gralloc 内存（主要是图片、Surface buffer）可能占其总内存的 30% 以上。在分析 App 内存问题时，不能忽略图形内存部分。

## 参考资料

### MTE ASYMM 模式与 android:memtagMode 源码级验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-13-android-mte-memtag-async-asymm-analysis.md
- 摘要：源码级验证 Android MTE 实现多层机制：应用层 android:memtagMode 仅支持 off/sync/async（ASYMM 非 Java API 选项）；Zygote 始终以 ASYNC MTE 运行（因 MTE 只能在进程初始化后禁用）；decideTaggingLevel()→SpecializeCommon→mallopt 完整调用链；Linux Kernel per-CPU mte_tcf_preferred 覆盖机制。
- Linux kernel / Android common kernel 路径：
  - `mm/page_alloc.c` — Buddy 分配器实现
  - `mm/slub.c` — SLUB 分配器实现
  - `mm/vmscan.c` — 页面回收主流程（kswapd / direct reclaim / MGLRU 相关入口）
  - `mm/compaction.c` — 内存压缩
  - `drivers/dma-buf/` — DMA-BUF 框架
  - `drivers/dma-buf/heaps/` — DMA-BUF Heaps 实现
- 官方文档：
  - developer.android.com — 16KB page size 支持
  - source.android.com — Graphics buffer 管理与 DMA-BUF
  - kernel.org — Linux Memory Management Documentation
- 高质量参考：
  - 程磊《五万字深入理解Linux内存管理》
  - draveness.me《为什么Linux需要虚拟内存》
  - OPPO《内存反碎片优化原理》
  - Silk (TACO '25) — GC 与内核页面回收的协同优化
  - LPC 2025 — HW/SW Design Recommendations for 16KB Devices

### MGLRU vs 传统双级 LRU 锁竞争差异
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-09-mglru-vs-traditional-lru-lock-contention.md
- 摘要：Linux 6.12 / Android common kernel MGLRU 与传统双级 LRU 的锁竞争对比。传统 LRU 每次页面引用做 `list_move()`（持 `lruvec->lru_lock`），多核时成为瓶颈；MGLRU 用 generation 编号替代 `list_move()`（`folio_update_gen()` 无锁），`lru_gen_look_around()` 批量 PTE 扫描，`evict_folios()` 持锁时间从 O(n) 降到 O(1)。含关键数据结构与调用链。
