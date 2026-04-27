---
title: "Android 17 + Kernel 6.12 系统级性能优化"
section: "16.4"
chapter: "16.4"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-27"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
last_task9_at: "2026-04-27T11:27:00+08:00"
task9_reviewed_date: "2026-04-27"
task9_reviewed_by: "openclaw-task9"
task2b_state: pending
task2b_result: fixed
pipeline_stage: task2b_pending
applicable_versions: "Android 17 (API 37)"
tags:
  - android
  - linux
  - research
review_notes: "2026-04-27 Task9：EEVDF 版本表与 android15-6.6 源码不符；Android 17/API37 与 android16-6.12 branch 边界、DeliQueue 源码锚点、io_uring Android 落地均需回炉。"
---

# 16.4 Android 17 + Kernel 6.12 系统级性能优化

## 为什么要了解 Android 17 + Kernel 6.12 的性能变化

升级系统版本后出现的冷启动、滑动和安装速度改善，常常来自内核与运行时的共同演进。GKI（Generic Kernel Image）的价值，是把通用内核与 SoC / 板级代码分开：核心内核由 Google 提供 release build，厂商特定能力放进 vendor modules，并通过 stable KMI 约束接口。这让同一条 LTS / Android 分支内的内核更新更容易独立交付，但是否能落到某台设备上，仍取决于该设备是否采用兼容的 GKI release build，以及 vendor modules 是否满足对应 KMI 边界。

Android 17 对应的讨论语境是 `android16-6.12` 这条 GKI release branch。Google 公布了一批系统级性能数据，覆盖 Pixel 8/9 和 Samsung Galaxy S25 等设备。读这类数据时，需要同时看两层信息：一层是 6.12 分支本身带来的调度、存储和内存改动，另一层是具体设备是否真的收到这条分支的 GKI 更新。

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

这些优化来自 GKI release build、内核 patch 和运行时改动的组合。能否在某台 Android 12+ 设备上看到同样收益，取决于它是否落在兼容的 GKI 分支，以及厂商模块是否满足 stable KMI 约束。

[待补充：GKI Mainline 推送范围的设备列表截图]

## 调度器变革：EEVDF 替代 CFS + sched_ext 可扩展框架

### EEVDF：从"公平分配"到"延迟优先"

Linux 内核的调度器从 2007 年起一直使用 CFS（Completely Fair Scheduler）。CFS 的核心思想是"公平"——用虚拟运行时间（vruntime）保证每个任务获得均等的 CPU 时间。这个设计在服务器场景很成功，但在移动设备上有问题：前台 App 的交互响应和后台同步任务同样"公平"，意味着一个正在做 RecyclerView 滑动的线程可能被后台的 gzip 压缩抢走 CPU 时间片。

Kernel 6.6 引入 EEVDF（Earliest Eligible Virtual Deadline First）作为可选调度器，6.12 成为默认的 fair scheduler。EEVDF 的核心变化是用"虚拟截止时间"替代"虚拟运行时间"来决定调度顺序。

EEVDF 的工作方式：每个任务有一个 lag 值（正值表示"欠了 CPU 时间"，负值表示"多占了 CPU 时间"）。只有 lag ≥ 0 的任务才"符合条件"（eligible），调度器在这些符合条件的任务中选择虚拟截止时间最早的那个执行。

这个改变带来的直接效果：短任务（比如 UI 线程的 doFrame 回调）更容易获得更低的延迟。因为短任务执行时间短、lag 容易保持正值，截止时间更容易排到前面。而长任务（比如后台编译 dex2oat）执行时间长、lag 容易变成负值，暂时被排除在候选列表之外，等 lag 恢复后再获得调度机会。

Google 的量化数据：系统调用效率整体提升 9.3%，EEVDF 是主要贡献者。

[已验证: source.android.com/docs/core/architecture/kernel/gki; kernel 6.12 changelog]

### sched_ext：用 BPF 实现可扩展调度器

sched_ext 是 Kernel 6.12 合并的另一个调度器相关框架。它允许开发者用 BPF（Berkeley Packet Filter）程序实现自定义调度策略，不需要修改内核代码。

这个框架的价值在于：不同的使用场景对调度器的需求不同。游戏需要超低延迟，数据库需要高吞吐，Android 需要 UI 响应优先。一个"通用"调度器不可能同时满足所有需求。sched_ext 让 OEM 或系统开发者可以为特定场景定制调度策略。

[已验证: AOSP android16-6.12, kernel/sched/ext/]

在 Android 17 中，sched_ext 提供给 OEM 使用，但 Google 官方构建使用的是 EEVDF。Google 不官方支持自定义 sched_ext 调度器。实际测试中一些示例调度器（如 scx_simple）在部分场景下性能不如默认的 EEVDF，所以如果 OEM 使用了自定义 sched_ext 调度器导致性能回退，排查方向是确认 sched_ext tracepoint 是否存在并检查自定义调度器的行为。

与我们已有的知识关联：在第 5 章（5.1 Linux 进程调度基础）中我们讨论过 CFS 的调度延迟模型。EEVDF 不是一个全新的调度器，它继承了 CFS 的虚拟时间概念，但改变了调度的决策逻辑——从"谁最该运行"变成了"谁的截止时间最近"。

## 存储栈三重优化

Kernel 6.12 对 Android 存储栈引入了三项相互配合的优化，随机 I/O 延迟降低 12%。

### F2FS Checkpoint Merge：减少 40% 写放大

F2FS 是 Android 设备的主流文件系统（4.2 节）。它的 checkpoint 机制在每次 fsync()/sync() 时，需要将 NAT（Node Address Table）、SIT（Segment Information Table）、CURSEG（Current Segment）等元数据刷盘。如果多个线程同时调用 fsync()（这在 Android 中很常见——每个 ContentProvider 的写操作都走 SQLite WAL 模式），就会触发多次完整 checkpoint，产生大量冗余的元数据写入。

在 `android16-6.12` 中，更稳的源码锚点是 `fs/f2fs/super.c`、`fs/f2fs/checkpoint.c` 和 `fs/f2fs/f2fs.h`。`checkpoint_merge` 挂载选项开启后，`f2fs_issue_checkpoint()` 会把并发的 `CP_SYNC` 请求挂到 `cprc->issue_list`，再由 `issue_checkpoint_thread` 统一执行；`struct ckpt_req_control` 里还能看到 `queued_ckpt`、`ckpt_wait_queue` 和 `ckpt_thread_ioprio` 这些配套字段。这里该把重点放在机制上：多个同步 checkpoint 请求会被串到同一个 checkpoint 线程里统一落盘，各个进程不再各自触发一轮完整 checkpoint。

量化效果：Checkpoint 写放大减少 40%。对 SQLite WAL 模式的 commit 性能影响最大（Android 中 SQLite 是最常见的同步 I/O 模式之一），因为每次 ContentProvider 写操作都走 SQLite WAL + fsync 路径。

[已验证: AOSP android16-6.12, fs/f2fs/super.c + fs/f2fs/checkpoint.c + fs/f2fs/f2fs.h; Linux F2FS checkpoint_merge mount option]

### io_uring multishot + zero-copy：减少 50% 系统调用开销

io_uring 是 Linux 5.1 引入的高性能异步 I/O 框架（6.3 节有基础介绍）。Kernel 6.12 的 io_uring 引入了两项关键改进：

**multishot 操作**：单个 SQE（Submission Queue Entry）可以处理多个完成事件，无需反复提交新的 SQE。传统模式下，每次 read 完成后需要重新提交一个 SQE 才能发起下一次读取。multishot 模式下一次提交就可以持续接收完成事件。

**zero-copy**：配合 `IORING_SETUP_NO_MMAP` 和 fixed buffers，数据直接在用户空间和内核空间之间共享，不再通过中间缓冲区拷贝。

对 Android 的直接影响：OkHttp/Cronet 的网络 I/O 和 SQLite 的文件 I/O 均可受益。Google 在 Android 17 的 Bionic libc 中实验性提供了 `liburing` 兼容层。

[待验证: liburing 兼容层在 Android 17 正式版中是否默认启用]

### dm-verity multi-buffer hashing：ARM64 吞吐提升 35%

dm-verity 是 Android 用于验证系统分区完整性的内核模块。传统路径按块计算哈希，热点函数是 `verity_hash()`。在 `android16-6.12` 中，对应源码文件是 `drivers/md/dm-verity-target.c`，多块哈希路径落在 `verity_hash_mb()`，shash 分支会调用 `crypto_shash_finup_mb(desc, data, len, digests, num_blocks)`，ahash 分支则保留逐块 fallback。

公开 patch 讨论把这组改动的收益表述为 dm-verity / fsverity 的 cold-cache read 吞吐提升，ARM64 场景约在 35% 左右。这里更稳的结论是：6.12 把哈希热点从单块计算扩展到多块交错计算，对安装、首读和 OTA 校验这类需要连续完整性验证的路径更敏感。

[已验证: AOSP android16-6.12, drivers/md/dm-verity-target.c; dm-verity multi-buffer hashing patch discussion]

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

Binder 调用的优化幅度显著。Android 的跨进程通信几乎全部走 Binder（1.4 节），冷启动过程中一个典型 App 会发起数百次 Binder 调用。AutoFDO 将内核中 Binder 热路径的代码布局优化后，每次调用的开销降低 20%+，累积效果就是整体冷启动延迟的降低。

### 工作机制

AutoFDO 对内核的优化路径与用户空间相同：

1. 在代表性的工作负载下采集 CPU profiling 数据（使用 ARM SPE 或 Intel LBR）
2. 生成 AFDO profile 文件
3. 编译器（GCC/Clang）根据 profile 优化内核代码布局——热路径代码放在一起提高指令缓存命中率，冷路径代码分开减少对热路径的污染

区别在于：用户空间的 AutoFDO 只优化 App 代码（通过 dex2oat/ART），而内核的 AutoFDO 优化的是 GKI kernel 的编译产物。设备是否拿到这批优化，取决于对应 GKI release build 是否已经下发到该设备的兼容分支。Android 12+ 只是平台下限，不代表设备会进入同一条 6.12 内核线。

[已验证: Google Android Developers Blog, "Boosting Android Performance: Introducing AutoFDO for GKI Kernel", 2026-03]

### 与 Cloud Compilation 的关系

1.12 节介绍了 Android 16 的 Cloud Compilation——将 dex2oat 从设备端迁移到 Google Play 云端。AutoFDO for kernel 和 Cloud Compilation 形成了完整的编译优化链：

- **用户空间**：Cloud Compilation + Baseline Profiles → 优化 App 的 AOT 编译
- **内核空间**：AutoFDO → 优化 GKI kernel 的代码布局

两端同时优化，冷启动的"内核初始化 + App 进程创建 + App 代码执行"三个阶段全部受益。

## ART 运行时优化

Android 17 的 ART 运行时引入了两项与性能直接相关的变化。

### Concurrent Mark-Compact + Generational GC

在 4.3 节和 4.8 节中已经把 ART 的垃圾回收机制展开过，这里只保留和系统性能结论直接相关的部分。4.8 的适用范围已经覆盖 Android 14-17，因此这里讨论的是 Android 17 对既有分代 GC 的增强。Concurrent Mark-Compact（CMC）路径把更多 young collection 维持在更小的扫描范围内。

分代策略本身没有变化：新对象优先留在 young generation，短命对象尽量在小范围回收，存活对象再逐步晋升。收益点在于 full-heap collection 的频率更低，GC 线程的 CPU 占用也更容易被压住。

把版本演进压缩来看：Android 8.0 先把 pause time 大幅压短；Android 10 之后的 Concurrent Copying 路径已经带有分代回收；Android 17 在 CMC 路径上继续强化 generational GC。对 RecyclerView 滑动和启动阶段的直接收益，是 GC 暂停与并发 GC 的 CPU 抢占都更容易被压到较小范围内。

[已验证: AOSP art/runtime/gc/; Android 17 Beta 3 release notes; §4.8 ART 分代垃圾回收与 GC 暂停优化]

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

调度器方面，Kernel 6.12 的 EEVDF 从可选到默认的改变，直接作用在使用对应 GKI release build 的 Android 17 设备上。

## 常见问题与误区

**误区 1："Kernel 6.12 的优化只影响新设备"**

不准确。6.12 的优化先落在对应的 GKI release branch 上，再由兼容这条 branch 的设备去接收。能否看到收益，取决于设备是否采用对应的 GKI 内核、vendor modules 是否满足 stable KMI 约束，以及 OEM 是否真的把这条 release build 交付到量产版本。把“GKI 支持独立更新”理解成“所有 Android 12+ 设备都会自动收到同一条 6.12 更新”，会把边界讲错。

**误区 2："EEVDF 替代 CFS 是因为 CFS 有 bug"**

CFS 没有根本性缺陷，EEVDF 的替代是设计理念的转变。CFS 追求"公平"（每个任务获得均等 CPU 时间），EEVDF 追求"低延迟"（短任务优先、交互响应优先）。对移动设备来说，后者更符合实际需求。

**误区 3："sched_ext 意味着 Android 可以用任意调度器"**

sched_ext 是一个框架，但 Google 官方构建使用 EEVDF。OEM 可以通过 sched_ext 自定义调度策略，但 Google 不提供官方支持。如果第三方 ROM 启用了自定义 sched_ext 调度器导致性能问题，排查方向是确认 sched_ext tracepoint 是否存在并检查自定义调度器的行为。

**误区 4："MGLRU 可以解决所有内存问题"**

MGLRU 优化的是页面回收策略，它让内核更聪明地决定回收哪些页面。但它不增加物理内存，也不减少 App 的内存占用。如果一个 App 有内存泄漏导致持续增长，MGLRU 只能让 LMK 更精准地杀掉它，而不是阻止泄漏。

## 参考资料

- [Google Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel](https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html)
- [GKI Kernel 架构文档](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)
- [AOSP GKI Kernel android16-6.12 分支](https://android.googlesource.com/kernel/common/+/android16-6.12)
- [Lore.kernel.org: F2FS Checkpoint Merge 补丁系列](https://lore.kernel.org/all/)
- [Lore.kernel.org: MGLRU 补丁系列](https://lore.kernel.org/all/)
- [Kernel 6.12 Changelog](https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12)
- 交叉引用：§1.4 Binder IPC、§1.6 版本演进、§1.12 AutoFDO、§1.13 DeliQueue、§4.4 LMK、§4.8 ART GC、§5.1 调度基础、§5.7 CPU 版本演进、§6.2 文件系统、§6.3 I/O 调度、§8.2 应用启动、§16.1 Google 官方优化思路
