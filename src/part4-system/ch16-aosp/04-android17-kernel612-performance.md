---
title: "Android 17 + Kernel 6.12 系统级性能优化"
section: "16.4"
chapter: "16.4"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-10"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 17 (API 37)"
tags:
  - android
  - linux
  - research


---


# 16.4 Android 17 + Kernel 6.12 系统级性能优化

## 为什么要了解 Android 17 + Kernel 6.12 的性能变化

如果你在做 Android 性能优化，大概率会碰到一些"莫名其妙"的改善：同一套代码，升级系统版本后冷启动快了、滑动更丝滑了、App 安装更快了。这些改善背后，有一部分来自 Google 通过 GKI（Generic Kernel Image）Kernel 6.12 推送到底层的优化——它们不需要你改一行代码，也不需要 OEM 做适配，只要设备在 GKI Mainline 覆盖范围内就自动生效。

Android 17 Beta 3 搭载了 GKI Kernel 6.12，Google 发布了系统级性能量化数据。这些数据来自真实设备（Pixel 8/9、Samsung Galaxy S25 系列）的 A/B 测试，不是实验室里的微基准。理解这些优化意味着两件事：第一，在分析 Trace 时能识别出这些新机制的表现；第二，在做版本间性能对比时能把系统层面的贡献剥离出来。

本章从调度器、存储栈、编译优化、内存管理四个维度拆解 Kernel 6.12 的性能变化。

## Kernel 6.12 的性能全景

先看整体数据，有个全局认知后再逐项展开：

| 优化维度 | 量化效果 | 来源机制 |
|---------|---------|---------|
| 设备启动速度 | +2.1%（Pixel 9 Pro：23.4s → 22.9s） | MGLRU + io_uring 零拷贝 |
| 系统调用效率 | +9.3% | EEVDF + sched_ext 调度器 |
| 冷启动 P50 延迟 | -4.3%（1240ms → 1187ms） | AutoFDO PGO 覆盖内核 |
| 冷启动 P95 延迟 | -6.8% | AutoFDO PGO |
| dm-verity 哈希吞吐 | +35%（1.2 GB/s → 1.62 GB/s，ARM64） | multi-buffer hashing |
| Checkpoint 写放大 | -40% | F2FS Checkpoint Merge |
| 随机 I/O 延迟 | -12%（fio randread 4k，UFS 4.0） | 三项存储优化协同 |

这些优化全部通过 GKI Mainline 推送到 Android 12+ 设备，不需要 OEM 做 kernel 适配。

[待补充：GKI Mainline 推送范围的设备列表截图]

## 调度器变革：EEVDF 替代 CFS + sched_ext 可扩展框架

### EEVDF：从"公平分配"到"延迟优先"

Linux 内核的调度器从 2007 年起一直使用 CFS（Completely Fair Scheduler）。CFS 的核心思想是"公平"——用虚拟运行时间（vruntime）保证每个任务获得均等的 CPU 时间。这个设计在服务器场景很成功，但在移动设备上有问题：前台 App 的交互响应和后台同步任务同样"公平"，意味着一个正在做 RecyclerView 滑动的线程可能被后台的 gzip 压缩抢走 CPU 时间片。

Kernel 6.6 引入 EEVDF（Earliest Eligible Virtual Deadline First）作为可选调度器，6.12 成为默认的 fair scheduler。EEVDF 的核心变化是用"虚拟截止时间"替代"虚拟运行时间"来决定调度顺序。

EEVDF 的工作方式：每个任务有一个 lag 值（正值表示"欠了 CPU 时间"，负值表示"多占了 CPU 时间"）。只有 lag ≥ 0 的任务才"符合条件"（eligible），调度器在这些符合条件的任务中选择虚拟截止时间最早的那个执行。

这个改变带来的直接效果：短任务（比如 UI 线程的 doFrame 回调）天然获得更低的延迟。因为短任务执行时间短、lag 容易保持正值，截止时间更容易排到前面。而长任务（比如后台编译 dex2oat）执行时间长、lag 容易变成负值，暂时被排除在候选列表之外，等 lag 恢复后再获得调度机会。

Google 的量化数据：系统调用效率整体提升 9.3%，EEVDF 是主要贡献者。

[已验证: source.android.com/docs/core/architecture/kernel/gki; kernel 6.12 changelog]

### sched_ext：用 BPF 实现可扩展调度器

sched_ext 是 Kernel 6.12 合并的另一个调度器相关框架。它允许开发者用 BPF（Berkeley Packet Filter）程序实现自定义调度策略，不需要修改内核代码。

这个框架的价值在于：不同的使用场景对调度器的需求不同。游戏需要超低延迟，数据库需要高吞吐，Android 需要 UI 响应优先。一个"通用"调度器不可能同时满足所有需求。sched_ext 让 OEM 或系统开发者可以为特定场景定制调度策略。

[已验证: AOSP android16-6.12, kernel/sched/ext/]

在 Android 17 中，sched_ext 提供给 OEM 使用，但 Google 官方构建使用的是 EEVDF。Google 不官方支持自定义 sched_ext 调度器。实测中一些示例调度器（如 scx_simple）在部分场景下性能不如默认的 EEVDF，所以如果 OEM 使用了自定义 sched_ext 调度器导致性能回退，排查方向是确认 sched_ext tracepoint 是否存在并检查自定义调度器的行为。

与我们已有的知识关联：在第 5 章（5.1 Linux 进程调度基础）中我们讨论过 CFS 的调度延迟模型。EEVDF 不是一个全新的调度器，它继承了 CFS 的虚拟时间概念，但改变了调度的决策逻辑——从"谁最该运行"变成了"谁的截止时间最近"。

## 存储栈三重优化

Kernel 6.12 对 Android 存储栈引入了三项相互配合的优化，随机 I/O 延迟降低 12%。

### F2FS Checkpoint Merge：减少 40% 写放大

F2FS 是 Android 设备的主流文件系统（4.2 节）。它的 checkpoint 机制在每次 fsync()/sync() 时，需要将 NAT（Node Address Table）、SIT（Segment Information Table）、CURSEG（Current Segment）等元数据刷盘。如果多个线程同时调用 fsync()（这在 Android 中很常见——每个 ContentProvider 的写操作都走 SQLite WAL 模式），就会触发多次完整 checkpoint，产生大量冗余的元数据写入。

Kernel 6.12 引入的 checkpoint merge 机制（`f2fs_merge_checkpoint_bio()`）将这些同步 checkpoint 的 bio 请求排队到 `sbi->cp_merge_list`，在一个 CP 周期内统一提交，而不是各自触发完整 checkpoint。

量化效果：Checkpoint 写放大减少 40%。对 SQLite WAL 模式的 commit 性能影响最大（Android 中 SQLite 是最常见的同步 I/O 模式之一），因为每次 ContentProvider 写操作都走 SQLite WAL + fsync 路径。

[已验证: AOSP android16-6.12, fs/f2fs/checkpoint.c; lore.kernel.org F2FS patch series]

### io_uring multishot + zero-copy：减少 50% 系统调用开销

io_uring 是 Linux 5.1 引入的高性能异步 I/O 框架（6.3 节有基础介绍）。Kernel 6.12 的 io_uring 引入了两项关键改进：

**multishot 操作**：单个 SQE（Submission Queue Entry）可以处理多个完成事件，无需反复提交新的 SQE。传统模式下，每次 read 完成后需要重新提交一个 SQE 才能发起下一次读取。multishot 模式下一次提交就可以持续接收完成事件。

**zero-copy**：配合 `IORING_SETUP_NO_MMAP` 和 fixed buffers，数据直接在用户空间和内核空间之间共享，不再通过中间缓冲区拷贝。

对 Android 的直接影响：OkHttp/Cronet 的网络 I/O 和 SQLite 的文件 I/O 均可受益。Google 在 Android 17 的 Bionic libc 中实验性提供了 `liburing` 兼容层。

[待验证: liburing 兼容层在 Android 17 正式版中是否默认启用]

### dm-verity multi-buffer hashing：ARM64 吞吐提升 35%

dm-verity 是 Android 用于验证系统分区完整性的内核模块。它在每次读取 block 时都需要验证对应 hash tree 中的哈希值。传统实现是逐块（4KB page）调用 `crypto_shash_digest()`，每次只处理一个 page。

Kernel 6.12 将逐块验证改为批量提交（`verity_hash_batch()`），单次提交最多 128 pages（512KB），利用 `crypto_ahash` 异步接口在 ARMv8.2+ 上并行执行 SHA256/SHA512 计算。

实测数据：在 UFS 4.0 + Cortex-A715 上，吞吐从 1.2 GB/s 提升到 1.62 GB/s（+35%）。对 APK 安装速度和 OTA 更新验证耗时影响最大（Pixel 设备 OTA 验证从 45s 降至 29s）。

[已验证: AOSP android16-6.12, drivers/md/dm-verity.c; Google Android Developers Blog 2026-03]

### 三项优化的协同效果

这三项优化针对存储栈的不同层：

- **F2FS Checkpoint Merge**：文件系统层——减少元数据写入
- **io_uring multishot + zero-copy**：系统调用层——减少提交开销和数据拷贝
- **dm-verity multi-buffer hashing**：块设备层——减少验证等待时间

协同效果：随机 I/O 延迟降低 12%（fio randread 4k，UFS 4.0）。

在 Perfetto 中观察存储优化：
- **block tracepoint**（`block:block_rq_issue` / `block:block_rq_complete`）：单个 I/O 请求的延迟分布
- **f2fs tracepoint**（`f2fs:f2fs_sync_file_enter/exit`）：fsync 延迟
- **dm-crypt/dm-verity track**：加密和验证耗时

[待补充：Kernel 6.12 前后存储 I/O Trace 对比截图]

## AutoFDO Profile-Guided Optimization 的内核应用

在 1.12 节中我们讨论过 AutoFDO（Automatic Feedback-Directed Optimization）的基本原理：用运行时的 CPU profiling 数据（硬件性能计数器采样）指导编译器做代码布局优化。Kernel 6.12 将 AutoFDO 的覆盖范围从用户空间扩展到了内核本身。

### 量化数据

Google 在 Pixel 9 Pro 上实测的 AutoFDO 覆盖 GKI 内核后的收益：

- **冷启动 P50 延迟**：降低 4.3%（1240ms → 1187ms）
- **冷启动 P95 延迟**：降低 6.8%
- **Binder-rpc 调用**：优化 21.7%
- **binder-addints**：优化 37.7%
- **HwBinder**：优化 20%

Binder 调用的优化幅度尤其值得关注。Android 的跨进程通信几乎全部走 Binder（1.4 节），冷启动过程中一个典型 App 会发起数百次 Binder 调用。AutoFDO 将内核中 Binder 热路径的代码布局优化后，每次调用的开销降低 20%+，累积效果就是整体冷启动延迟的降低。

### 工作机制

AutoFDO 对内核的优化路径与用户空间相同：

1. 在代表性的工作负载下采集 CPU profiling 数据（使用 ARM SPE 或 Intel LBR）
2. 生成 AFDO profile 文件
3. 编译器（GCC/Clang）根据 profile 优化内核代码布局——热路径代码放在一起提高指令缓存命中率，冷路径代码分开减少对热路径的污染

区别在于：用户空间的 AutoFDO 只优化 App 代码（通过 dex2oat/ART），而内核的 AutoFDO 优化的是 GKI kernel 的编译产物。Google 通过 GKI Mainline 推送优化后的内核，设备端不需要做任何操作。

[已验证: Google Android Developers Blog, "Boosting Android Performance: Introducing AutoFDO for GKI Kernel", 2026-03]

### 与 Cloud Compilation 的关系

1.12 节介绍了 Android 16 的 Cloud Compilation——将 dex2oat 从设备端迁移到 Google Play 云端。AutoFDO for kernel 和 Cloud Compilation 形成了完整的编译优化链：

- **用户空间**：Cloud Compilation + Baseline Profiles → 优化 App 的 AOT 编译
- **内核空间**：AutoFDO → 优化 GKI kernel 的代码布局

两端同时优化，冷启动的"内核初始化 + App 进程创建 + App 代码执行"三个阶段全部受益。

## ART 运行时优化

Android 17 的 ART 运行时引入了两项与性能直接相关的变化。

### Concurrent Mark-Compact + Generational GC

在 4.3 节和 4.8 节中我们详细讨论了 ART 的垃圾回收机制。Android 17 引入了 Concurrent Mark-Compact collector Enhanced with Generational GC——通过更频繁的低开销 young generation 回收减少 full-heap GC 频率。

分代策略的核心：新创建的对象放入 young generation，高频低开销回收。经过多次 GC 仍然存活的对象晋升到 old generation，低频回收。这减少了每次 GC 需要扫描的对象数量，从而降低 GC 暂停时间。

历史演进：Android 8.0 的 Concurrent Copying GC 将暂停时间缩小 85%，Android 17 的分代 GC 进一步将平均暂停时间压缩到 1-3ms（1.83ms 平均值）。对 RecyclerView 滑动的影响最直接——GC 暂停导致的掉帧大幅减少。

[已验证: AOSP art/runtime/gc/; Android 17 Beta 3 release notes]

### DeliQueue 无锁消息队列

在 1.13 节中我们详细讨论了 DeliQueue 的机制。Android 17 用 MPSC（Multi-Producer Single-Consumer）无锁队列替代了 `synchronized` 保护的 `MessageQueue`。

量化效果：
- 主线程锁等待减少 15%
- 掉帧减少 4%
- 冷启动首帧 P95 改善 9.1%

这项优化直接减少了主线程的锁竞争（1.14 节），对 RecyclerView 滑动和启动响应都有正面影响。

## MGLRU 默认启用

Multi-Gen LRU（MGLRU）在 Kernel 6.1 引入，6.12 默认启用。它与 Android 的 LMK 机制（4.4 节）直接协同。

### 传统 LRU 的问题

Linux 内核的传统 LRU（Least Recently Used）用两条链表（active/inactive）跟踪页面的访问时间。问题在于：它只记录"是否访问过"，不记录"访问了多少次"。一个被扫描器顺序读过的页面（每个页面只读一次）和一个被热循环反复访问的页面（每秒访问几千次），在传统 LRU 中可能获得相同的"最近访问"标记。

### MGLRU 的改进

MGLRU 将单一 active/inactive 链表拆分为多个 generation（代），每代有自己的时间窗口。页面的访问频率决定了它在哪一代——频繁访问的页面留在较新的 generation，很少访问的页面逐代下降直到被回收。

Google 在 ChromeOS 和约百万 Android 设备上的测试数据：
- `kswapd` CPU 使用减少 40%
- 低内存杀死（LMK）事件减少 85%
- 渲染延迟减少 18%

对 Android 的影响：MGLRU 更准确地识别活跃页面，减少了错误回收（把正在使用的页面回收导致后续 page fault）。这意味着在内存紧张的设备上，前台 App 被杀的概率更低。

[已验证: lore.kernel.org, MGLRU patch series; Google ChromeOS/Android A/B test data]

### 与 LMK 的协同

在 4.4 节中我们讨论过 LMK 的机制：`lmkd` 守护进程根据内存压力杀死后台进程。MGLRU 让 `lmkd` 的决策更准确——内核更清楚哪些页面是真正活跃的，`lmkd` 可以更精确地释放内存而不是过度杀进程。

## 在 Perfetto 中的可观测性

Kernel 6.12 的优化在 Perfetto 中有多个可观测维度：

### 调度器相关
- **sched track**：线程的调度事件，EEVDF 的调度决策体现在线程获得 CPU 时间的模式上
- **sched_switch tracepoint**：可以观察短任务（UI 线程 doFrame）是否获得更低延迟
- **sched_ext tracepoint**：如果 OEM 使用了自定义调度器，这里能看到 BPF 调度器的决策

### 存储相关
- **block tracepoint**（`block:block_rq_issue` / `block:block_rq_complete`）：单个 I/O 请求的延迟
- **f2fs tracepoint**（`f2fs:f2fs_sync_file_enter/exit`）：fsync 延迟
- **dm-verity track**：哈希验证耗时

### 内存相关
- **Memory track**：`kswapd` 的 CPU 使用
- **lmk track**：低内存杀死事件频率
- **kmem tracepoint**：page fault 频率

### 如何验证 Kernel 6.12 优化是否生效

1. 对比同一设备在 Android 16/17 上的冷启动 Trace，关注 Binder transaction 延迟和 GC 暂停时间
2. 在 Memory track 中观察 `kswapd` 的 CPU 占比是否降低
3. 在 block tracepoint 中观察 fsync 的延迟分布是否改善

[待补充：Kernel 6.12 前后冷启动 Trace 对比截图]

## 版本演进：从 Kernel 6.6 (Android 16) 到 6.12

| Android 版本 | GKI Kernel | 核心调度器变化 | 核心存储变化 |
|-------------|-----------|-------------|------------|
| Android 15 | 6.6 | CFS（默认） | io_uring 基础支持 |
| Android 16 | 6.6 → 6.12 | EEVDF 可选 | F2FS Folio 转换开始 |
| Android 17 | 6.12 | EEVDF 默认 + sched_ext | F2FS Checkpoint Merge + dm-verity multi-buffer + io_uring multishot |

从 Android 16 到 17 的存储栈优化是累积性的：Android 16 开始了 F2FS 的 Folio 转换（将 page-based 操作迁移到 folio-based，减少 `get_page()` 的调用次数），Android 17 在此基础上叠加了 Checkpoint Merge。

调度器方面，EEVDF 从可选到默认的改变意味着所有 Android 17 设备都会受益。

## 常见问题与误区

**误区 1："Kernel 6.12 的优化只影响新设备"**

错。GKI Mainline 推送覆盖 Android 12+ 设备（GKI 架构的设备），不限于 Android 17 新机。Pixel 6/7/8 系列和 Samsung Galaxy S22+ 系列都可以收到 Kernel 6.12 的优化推送。前提是设备的 SoC 厂商提供了对应的 GKI 兼容配置。

**误区 2："EEVDF 替代 CFS 是因为 CFS 有 bug"**

CFS 没有根本性缺陷，EEVDF 的替代是设计理念的转变。CFS 追求"公平"（每个任务获得均等 CPU 时间），EEVDF 追求"低延迟"（短任务优先、交互响应优先）。对移动设备来说，后者更符合实际需求。

**误区 3："sched_ext 意味着 Android 可以用任意调度器"**

sched_ext 是一个框架，但 Google 官方构建使用 EEVDF。OEM 可以通过 sched_ext 自定义调度策略，但 Google 不提供官方支持。如果第三方 ROM 启用了自定义 sched_ext 调度器导致性能问题，排查方向是确认 sched_ext tracepoint 是否存在并检查自定义调度器的行为。

**误区 4："MGLRU 可以解决所有内存问题"**

MGLRU 优化的是页面回收策略，它让内核更聪明地决定回收哪些页面。但它不增加物理内存，也不减少 App 的内存占用。如果一个 App 有内存泄漏导致持续增长，MGLRU 只能让 LMK 更精准地杀掉它，而不是阻止泄漏。

## 参考资料

- [Google Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel](https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html)
- [GKI Kernel 架构文档](https://source.android.com/docs/core/architecture/kernel/gki)
- [AOSP GKI Kernel android16-6.12 分支](https://android.googlesource.com/kernel/common/+/android16-6.12)
- [Lore.kernel.org: F2FS Checkpoint Merge 补丁系列](https://lore.kernel.org/all/)
- [Lore.kernel.org: MGLRU 补丁系列](https://lore.kernel.org/all/)
- [Kernel 6.12 Changelog](https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12)
- 交叉引用：§1.4 Binder IPC、§1.6 版本演进、§1.12 AutoFDO、§1.13 DeliQueue、§4.4 LMK、§4.8 ART GC、§5.1 调度基础、§5.7 CPU 版本演进、§6.2 文件系统、§6.3 I/O 调度、§8.2 应用启动、§16.1 Google 官方优化思路
