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
task6_state: revisiting
task9_state: pending
task9_result: needs-rework
last_task9_at: "2026-04-27T11:27:00+08:00"
task9_reviewed_date: "2026-04-27"
task9_reviewed_by: "openclaw-task9"
task2b_state: fixed
task2b_result: fixed
pipeline_stage: task6_pending
task2b_fixed_at: "2026-04-27T11:41:00+08:00"
last_task2b_at: "2026-04-27T11:41:00+08:00"
applicable_versions: "Android 17 (API 37)"
tags:
  - android
  - linux
  - research
review_notes: "2026-04-27 Task2B：修正 EEVDF 版本分界，拆开 Android 17/API37 与 android16-6.12 GKI branch，补 DeliQueue 源码锚点并降级 io_uring 用户态采用结论。"
---

# 16.4 Android 17 + Kernel 6.12 系统级性能优化

## 为什么要了解 Android 17 + Kernel 6.12 的性能变化

升级系统版本后出现的冷启动、滑动和安装速度改善，常常来自内核与运行时的共同演进。GKI（Generic Kernel Image）的价值，是把通用内核与 SoC / 板级代码分开：核心内核由 Google 提供 release build，厂商特定能力放进 vendor modules，并通过 stable KMI 约束接口。同一条 LTS / Android 分支内的内核更新更容易独立交付，但某台设备能否收到更新，仍取决于它是否采用兼容的 GKI release build，以及 vendor modules 是否满足对应 KMI 边界。

本章把两类事实分开写。第一类是 ACK / GKI 源码分支事实，例如 `android15-6.6`、`android16-6.12` 中 `kernel/sched/fair.c`、`fs/f2fs/`、`drivers/md/dm-verity-target.c` 的实现变化。第二类是 Android 17 / API 37 平台行为，例如 targetSdk 37 应用启用新的 lock-free `MessageQueue`。`android16-6.12` 是 GKI release branch 名称，不能直接等同于所有 Android 17 设备的内核状态。

本章从调度器、存储栈、编译优化、内存管理四个维度拆解 Kernel 6.12 相关变化。凡是缺少官方公开数据或源码采用证据的性能数字，只保留为待验证线索，不写成确定收益。

## Kernel 6.12 的性能全景

公开资料里的性能数字来自不同来源，不能混成一张“Android 17 必然收益”表。这里按可核验程度拆开。

| 类别 | 可核验来源 | 本章采用口径 |
|------|------------|--------------|
| AutoFDO for GKI | Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel；`android15-6.6` 与 `android16-6.12` 的 GKI AFDO 目录 | 保留官方公开的 cold start 与 Binder microbenchmark 数据，限定在对应 GKI profile / build。 |
| DeliQueue | Android Developers Blog: Under the hood: Android 17’s lock-free MessageQueue；Android 17 MessageQueue behavior change | 保留内测设备上的 lock contention、missed frames 与 first frame P95 数据，限定在 targetSdk 37+ 新 `MessageQueue`。 |
| dm-verity multi-buffer hashing | `android16-6.12/drivers/md/dm-verity-target.c` 与 multi-buffer hashing patch discussion | 写成 ARM64 cold-cache read / hash throughput 改善，不推导到所有安装、启动或 OTA 场景。 |
| F2FS / io_uring / MGLRU | `fs/f2fs/`、`io_uring/`、MGLRU patch discussion | 以机制和可观测指标为主；未能逐项溯源的全局百分比删除。 |

对某台设备做验证时，至少要同时记录平台版本、GKI branch、kernel release、设备型号、benchmark 名称和样本口径。缺一项时，数据只能用于排查线索，不能当作跨设备结论。

[待补充：GKI Mainline 推送范围的设备列表截图]

## 调度器变革：EEVDF fair scheduler + sched_ext 可扩展框架

### EEVDF：fair scheduler 的 lag / deadline 模型

Linux fair scheduler 的 6.6 系列已经能看到 EEVDF 代码路径。复核 AOSP `kernel/common` 的 `android15-6.6/kernel/sched/fair.c`，`pick_eevdf()`、`entity_eligible()` 和 `place_entity()` 已存在；`android16-6.12/kernel/sched/fair.c` 继续保留这些路径。因此本章不能把 `android16-6.12` 写成 EEVDF 从“可选”走向“默认”的分界。

这里把 CFS 当作 fair scheduler 子系统的历史名称使用；EEVDF 改的是 fair class 内部选择下一个 runnable entity 的策略。`update_curr()` 继续推进当前 entity 的 vruntime，`entity_lag()` / `entity_eligible()` 用实际服务时间与权重期望服务时间的差值判断 lag，`pick_eevdf()` 再从 eligible entity 中选择虚拟 deadline 最早的对象。正 lag 表示 entity 获得的 CPU 时间少于应得份额，负 lag 表示已经多拿了服务时间。

这个模型对移动设备的价值在于延迟控制。短任务（例如 UI 线程的 `doFrame` 回调）运行时间短，lag 更容易回到 eligible 区间，deadline 也更容易排到前面；后台长任务执行时间更长，lag 变负后会暂时退出候选集合，等 lag 恢复后再参与选择。

[已验证: AOSP `kernel/common` `android15-6.6/kernel/sched/fair.c` 和 `android16-6.12/kernel/sched/fair.c` 均包含 `pick_eevdf()` / `entity_eligible()`；Kernel 6.12 changelog]

### sched_ext：用 BPF 实现可扩展调度器

sched_ext 是 Kernel 6.12 合并的另一个调度器相关框架。它允许开发者用 BPF（Berkeley Packet Filter）程序实现自定义调度策略，不需要修改内核代码。

这个框架的价值在于：不同的使用场景对调度器的需求不同。游戏需要超低延迟，数据库需要高吞吐，Android 需要 UI 响应优先。一个"通用"调度器不可能同时满足所有需求。sched_ext 让 OEM 或系统开发者可以为特定场景定制调度策略。

[已验证: AOSP android16-6.12, kernel/sched/ext/]

在 Android 17 的讨论里，sched_ext 的边界要单独写清。`android16-6.12/kernel/sched/ext/` 是可核验的源码锚点；这项能力提供给 OEM 和系统开发者做实验或定制，Google 官方构建仍以 fair scheduler / EEVDF 为主。若某个 ROM 启用了自定义 sched_ext 调度器并出现性能回退，排查方向是确认 sched_ext tracepoint 是否存在，再检查对应 BPF 调度器的行为。

与第 5 章（5.1 Linux 进程调度基础）的关系可以压缩成一句：EEVDF 继续使用虚拟时间体系，但调度决策从“vruntime 最小”转向“eligible entity 中 virtual deadline 最早”。

## 存储栈三重优化

Kernel 6.12 对 Android 存储栈引入了三项相互配合的优化：减少重复 checkpoint、提高完整性校验吞吐、扩展异步 I/O 能力。

### F2FS Checkpoint Merge：减少重复 checkpoint 写入

F2FS 是 Android 设备的主流文件系统（4.2 节）。它的 checkpoint 机制在每次 fsync()/sync() 时，需要将 NAT（Node Address Table）、SIT（Segment Information Table）、CURSEG（Current Segment）等元数据刷盘。如果多个线程同时调用 fsync()（这在 Android 中很常见——每个 ContentProvider 的写操作都走 SQLite WAL 模式），就会触发多次完整 checkpoint，产生大量冗余的元数据写入。

在 `android16-6.12` 中，更稳的源码锚点是 `fs/f2fs/super.c`、`fs/f2fs/checkpoint.c` 和 `fs/f2fs/f2fs.h`。`checkpoint_merge` 挂载选项开启后，`f2fs_issue_checkpoint()` 会把并发的 `CP_SYNC` 请求挂到 `cprc->issue_list`，再由 `issue_checkpoint_thread` 统一执行；`struct ckpt_req_control` 里还能看到 `queued_ckpt`、`ckpt_wait_queue` 和 `ckpt_thread_ioprio` 这些配套字段。这里该把重点放在机制上：多个同步 checkpoint 请求会被串到同一个 checkpoint 线程里统一落盘，各个进程不再各自触发一轮完整 checkpoint。

对 SQLite WAL 模式的 commit 性能影响最大（Android 中 SQLite 是最常见的同步 I/O 模式之一），因为每次 ContentProvider 写操作都走 SQLite WAL + fsync 路径。具体写放大下降比例需要补齐设备、内核分支、挂载参数和写入模型后再写入正文。

[已验证: AOSP android16-6.12, fs/f2fs/super.c + fs/f2fs/checkpoint.c + fs/f2fs/f2fs.h; Linux F2FS checkpoint_merge mount option]

### io_uring multishot 与 zero-copy：内核能力不等于框架默认采用

io_uring 是 Linux 5.1 引入的高性能异步 I/O 框架（6.3 节有基础介绍）。在 `android16-6.12/io_uring/` 中，可以核验 multishot、registered buffer、ring setup 等内核能力；`IORING_SETUP_NO_MMAP` 也能在 `io_uring/io_uring.c` 中找到。但这些能力要分三层看。

| 层级 | 可确认事实 | 写作边界 |
|------|------------|----------|
| 内核能力 | `android16-6.12/io_uring/` 包含 io_uring 实现，`IORING_SETUP_NO_MMAP` 是建环相关 flag | 它减少 ring 映射方式上的限制，不能直接等同于应用数据 zero-copy。 |
| 用户态库 | AOSP `platform/external/liburing/Android.bp` 提供 `cc_library_static { name: "liburing" }` | 这是外部 liburing 模块，Java / framework 默认路径不会自动获得该能力。 |
| Android 框架与常用库 | 需要逐项核验 Cronet、SQLite、OkHttp 是否在对应版本接入 io_uring | 没有源码采用证据时，只能写“具备潜在收益”，不能写成默认收益。 |

multishot 的稳定结论是减少重复提交 SQE 的开销；zero-copy 的稳定结论要落到具体操作类型、registered buffers、send / receive zero-copy 支持和设备内核配置。对 App 性能分析来说，先看 trace 里是否真的出现 io_uring 相关 syscall / tracepoint，再判断网络或文件 I/O 是否使用了这条路径。

[已验证: AOSP `kernel/common` `android16-6.12/io_uring/io_uring.c`; AOSP `platform/external/liburing/Android.bp`; Cronet / SQLite / OkHttp 默认采用状态待逐项核验]

### dm-verity multi-buffer hashing：ARM64 吞吐提升 35%

dm-verity 是 Android 用于验证系统分区完整性的内核模块。传统路径按块计算哈希，热点函数是 `verity_hash()`。在 `android16-6.12` 中，对应源码文件是 `drivers/md/dm-verity-target.c`，多块哈希路径落在 `verity_hash_mb()`，shash 分支会调用 `crypto_shash_finup_mb(desc, data, len, digests, num_blocks)`，ahash 分支则保留逐块 fallback。

公开 patch 讨论把这组改动的收益表述为 dm-verity / fsverity 的 cold-cache read 吞吐提升，ARM64 场景约在 35% 左右。这里更稳的结论是：6.12 把哈希热点从单块计算扩展到多块交错计算，对安装、首读和 OTA 校验这类需要连续完整性验证的路径更敏感。

[已验证: AOSP android16-6.12, drivers/md/dm-verity-target.c; dm-verity multi-buffer hashing patch discussion]

### 三项优化的协同观察

这三项优化针对存储栈的不同层：

- **F2FS Checkpoint Merge**：文件系统层，减少重复 checkpoint 带来的元数据写入。
- **io_uring multishot / registered buffer 相关能力**：系统调用层，减少重复提交和部分数据搬运成本，前提是用户态组件实际采用。
- **dm-verity multi-buffer hashing**：块设备验证层，减少连续读场景下的哈希等待。

随机 I/O 延迟这类全局百分比需要完整 benchmark 条件支撑。缺少设备、内核分支、fio 参数、UFS 型号和样本口径时，本章不保留固定百分比。

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

### DeliQueue lock-free MessageQueue

DeliQueue 属于 Android 17 / API 37 平台行为，不属于 `android16-6.12` 内核分支本身。官方博客给出的适用条件是：targetSdk 37 及以上应用会收到新的 lock-free `android.os.MessageQueue` 实现；依赖反射读取 `MessageQueue` 私有字段的代码需要专项验证。

可核验源码锚点在 AOSP `frameworks/base/core/java/android/os/`：历史实现可以看 `LockedMessageQueue/MessageQueue.java`，新实现可以看 `ConcurrentMessageQueue/MessageQueue.java`，`CombinedMessageQueue/MessageQueue.java` 负责兼容选择。博客描述的实现模型是生产者侧 lock-free Treiber stack + Looper 侧 min-heap：多个线程插入消息时不再抢同一把 monitor lock，Looper 仍由单线程维护到期消息的顺序。

官方博客给出的数据来自内部 beta traces，适合写成限定条件下的观测结果：

- App 主线程花在 `MessageQueue` lock contention 上的时间减少 15%。
- App missed frames 减少 4%。
- System UI / Launcher interactions missed frames 减少 7.7%。
- App startup 到 first frame drawn 的 P95 时间减少 9.1%。

这些数据不能直接外推到所有设备和所有 App。实际排查时，仍然要在 Perfetto 中搜索 `monitor contention with ...`，确认旧实现是否真的在 `MessageQueue` 上产生锁竞争。

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

对 Android 的影响：MGLRU 更准确地识别活跃页面，减少错误回收（把正在使用的页面回收导致后续 page fault）。在内存紧张的设备上，前台 App 被误杀的概率会随之下降。

[已验证: lore.kernel.org, MGLRU patch series; Google ChromeOS/Android A/B test data]

### 与 LMK 的协同

在 4.4 节中我们讨论过 LMK 的机制：`lmkd` 守护进程根据内存压力杀死后台进程。MGLRU 让 `lmkd` 的决策更准确：内核更清楚哪些页面仍在活跃使用，`lmkd` 可以减少过度杀进程。

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

## 版本演进：把平台版本和 GKI 分支分开

| 维度 | 可核验锚点 | 本章结论 |
|------|------------|----------|
| Android 15 相关 GKI | `kernel/common` `android15-6.6/kernel/sched/fair.c` | 已存在 `pick_eevdf()`、`entity_eligible()`、`place_entity()`，不能写成“6.6 仍是纯 CFS 默认”。 |
| Android 16 / 17 讨论中的 GKI | `kernel/common` `android16-6.12/kernel/sched/fair.c`、`kernel/sched/ext/` | fair scheduler 继续使用 EEVDF 路径；6.12 的明确新增点是 sched_ext 等能力。 |
| Android 17 / API 37 平台行为 | Android 17 release notes / behavior changes；`frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java` | DeliQueue / lock-free `MessageQueue` 按 targetSdk 37 等条件生效，属于平台行为层，需和 GKI branch 分开记录。 |

存储栈优化仍然是累积性的：F2FS folio 化、checkpoint merge、dm-verity multi-buffer hashing、io_uring 新能力分别处在文件系统、块设备验证和系统调用层。某台设备是否具备这些变化，要回到它实际使用的 kernel release、GKI build 和厂商配置。

## 常见问题与误区

**误区 1："Kernel 6.12 的优化只影响新设备"**

不准确。6.12 的优化先落在对应的 GKI release branch 上，再由兼容这条 branch 的设备去接收。能否看到收益，取决于设备是否采用对应的 GKI 内核、vendor modules 是否满足 stable KMI 约束，以及 OEM 是否真的把这条 release build 交付到量产版本。把“GKI 支持独立更新”理解成“所有 Android 12+ 设备都会自动收到同一条 6.12 更新”，会把边界讲错。

**误区 2："EEVDF 进入 fair scheduler 是因为 CFS 有 bug"**

CFS 的旧模型没有根本性缺陷，EEVDF 是 fair scheduler 在移动交互延迟上的一次策略调整。旧模型更强调按 vruntime 拉平 CPU 时间，EEVDF 更强调 eligible entity 与 virtual deadline。移动设备上的 UI 回调、输入响应和前台短任务更依赖低延迟调度。

**误区 3："sched_ext 意味着 Android 可以用任意调度器"**

sched_ext 是一个框架，Google 官方构建仍以 fair scheduler / EEVDF 为主。OEM 可以通过 sched_ext 自定义调度策略，但 Google 不提供官方支持。如果第三方 ROM 启用了自定义 sched_ext 调度器导致性能问题，排查方向是确认 sched_ext tracepoint 是否存在并检查自定义调度器的行为。

**误区 4："MGLRU 可以解决所有内存问题"**

MGLRU 优化页面回收策略，让内核更准确地决定回收哪些页面。它不会增加物理内存，也不会减少 App 自身的内存占用。如果一个 App 有内存泄漏导致持续增长，MGLRU 只能让 LMK 更精准地处理目标进程，无法阻止泄漏继续发生。

## 参考资料

- [Google Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel](https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html)
- [GKI Kernel 架构文档](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)
- [AOSP GKI Kernel android15-6.6 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android15-6.6)
- [AOSP GKI Kernel android16-6.12 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12)
- [Android Developers Blog: Under the hood - Android 17 lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [AOSP external/liburing](https://android.googlesource.com/platform/external/liburing/+/refs/heads/main)
- [Lore.kernel.org: F2FS Checkpoint Merge 补丁系列](https://lore.kernel.org/all/)
- [Lore.kernel.org: MGLRU 补丁系列](https://lore.kernel.org/all/)
- [Kernel 6.12 Changelog](https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12)
- 交叉引用：§1.4 Binder IPC、§1.6 版本演进、§1.12 AutoFDO、§1.13 DeliQueue、§4.4 LMK、§4.8 ART GC、§5.1 调度基础、§5.7 CPU 版本演进、§6.2 文件系统、§6.3 I/O 调度、§8.2 应用启动、§16.1 Google 官方优化思路
