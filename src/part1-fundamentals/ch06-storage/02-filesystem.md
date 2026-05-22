---
title: 文件系统
chapter: '6.2'
section: '6.2'
applicable_versions: Android 10+
last_verified: '2026-04-23'
last_verified_against: AOSP EROFS docs + source.android 16KB page size docs + kernel/common android15-6.6 ext4 journal / f2fs segment,gc,uapi/linux/f2fs.h,include/linux/f2fs_fs.h + developer.android.com
confidence: medium
drafted_date: '2026-04-01'
drafted_by: openclaw-task2a
polish_count: 1
polish_date: '2026-04-07'
polish_by: task2b-polish
reviewed_date: '2026-04-23'
reviewed_by: openclaw-task6
review_type: scheduled-review
review_round: 4
sources:
- type: blog
  path: Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_深入代码细节看f2fs在磁盘上的组织方式.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md
- type: official
  path: source.android.com/docs/core/storage
- type: official
  path: developer.android.com/training/data-storage
tags:
- linux
- android
- research
task6_result: pass-light-edit
task2b_result: fixed
last_task2b_at: "2026-05-22T15:21:00+08:00"
status: ready-for-review
pipeline_stage: "task6_pending"
task6_state: revisiting
task9_state: pending
task9_result: "needs-rework"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-22"
last_task9_at: "2026-05-22T14:20:00+08:00"
last_task6_audit: "2026-05-19"
task2b_state: fixed
p0: 1
p1: 1
p2: 0
updated_by: "openclaw-task9"
updated_date: "2026-05-22"
review_notes: "2026-05-22 task9 idle audit: needs-rework。P0 1 / P1 1 / P2 0。f2fs 前台 GC 源码片段过期，EROFS ZSTD 需补 Android 16/6.12+ 版本边界。"
auto_promoted: false
last_task9_audit: "2026-05-22"
---

<!-- outline-start -->


## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ext4 的核心特性与在 Android 上的使用
- 🔹 F2FS（Flash-Friendly File System）的设计思想与在 Android 上的优势
- 🔹 EROFS（Enhanced Read-Only File System）用于 system 分区
- 🔹 文件系统对随机读写性能的影响
- 🔹 fsync / fdatasync 对写性能的影响与优化

### 扩展（可选深入）

- 🔸 各厂商对文件系统的选型差异
- 🔸 文件系统碎片化对长期使用后性能退化的影响
<!-- outline-end -->

## 从一个真实的 fsync 卡顿说起

在 Perfetto 中分析 App 卡顿时，有一类问题几乎每个 Android 工程师都会遇到——主线程在 `fsync` 上阻塞了几十甚至几百毫秒。Trace 中主线程时间条上出现一大段橘红色的 "Uninterruptible Sleep"（D 状态），放大后 syscall 是 `fsync`，对应的是一个 SQLite 数据库或 SharedPreferences 的 XML 文件。

这个现象在 Android 上比在其他 Linux 系统上更为突出，原因是 Android 系统中 SQLite 的使用密度远高于服务器或桌面 Linux——几乎所有 App 的配置、缓存、状态信息都存在 SQLite 数据库里，而 SQLite 每次事务提交都需要调用 `fsync` 确保数据落盘。再加上 SharedPreferences 在早期 Android 版本中也是通过 `fsync` 同步写入 XML 文件，一个 App 在启动阶段可能触发数十次 `fsync`。

这个问题的根因，往往不在 App 代码本身，而在 App 之下那一层——文件系统。不同的文件系统对 `fsync` 的实现策略差异巨大，直接影响着 App 的 I/O 延迟。Android 设备上的文件系统选择，经历了从 ext4 到 f2fs、再到 EROFS 的演进，每一次切换都是为了解决前一代在手机场景下暴露出的特定问题。

理解这三个文件系统的设计思想和性能特性，是我们诊断存储相关卡顿的基础。

## VFS：文件系统的统一抽象

在深入各个具体的文件系统之前，我们先理解一个关键的中间层——VFS（Virtual File System，虚拟文件系统）。

Linux 内核在用户进程和具体文件系统之间引入了 VFS 抽象层。VFS 定义了一组所有文件系统都必须支持的标准接口和数据结构：`superblock`（超级块）、`inode`（索引节点）、`dentry`（目录项）、`file`（打开文件）。上层代码无论是操作 ext4 还是 f2fs，调用的都是同一套 POSIX 接口——`open()`、`read()`、`write()`、`fsync()`，VFS 负责把请求分发到对应文件系统的实现。

[已验证: 官方文档, kernel.org/doc/html/latest/filesystems/vfs.html]

从 App 开发者的角度看，不需要关心底层用的是哪种文件系统；但从性能分析的角度，同一个 `fsync()` 调用在 ext4 和 f2fs 上的行为完全不同。这也是为什么我们在 Perfetto 中看到 I/O 延迟异常时，需要先确认文件系统类型。

VFS 层管理的另一个关键组件是 Page Cache（页缓存）。通过 `read()` 读取文件时，内核先检查 Page Cache 中是否已有对应数据——如果有，直接从内存返回，不触发磁盘 I/O；如果没有，才向文件系统发起实际的读请求。`write()` 也是类似，数据先写入 Page Cache，标记为"脏页"（dirty page），由内核的 `flush` 线程在后台异步写回磁盘。这种机制对读性能有巨大的提升——被频繁访问的文件数据几乎全部缓存在内存中，这也是为什么手机在内存充足时读操作通常很快，而写操作（尤其是同步写）更容易成为瓶颈。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md]

## ext4：成熟但不适合手机场景

### ext4 的核心设计

ext4 是 Linux 生态中最成熟、最广泛使用的文件系统。它是 ext3 的直接继任者，在 2008 年合并入 Linux 主线。ext4 的核心特性包括：

**日志（Journal）**：ext4 使用 jbd2（Journal Block Device v2）作为日志系统，保证文件系统在异常断电后的一致性。jbd2 支持 journal、ordered、writeback 三种模式。Android 上默认使用 ordered 模式——日志只记录元数据（metadata），但保证在元数据提交到日志之前，对应的数据块已经写入磁盘。这是一种在安全性和性能之间的折中。

**延迟分配（Delayed Allocation）**：ext4 不会在 `write()` 调用时立即分配磁盘块，而是等到数据需要刷新到磁盘时（`fsync` 或内核的 `flush` 线程触发）才统一分配。这种策略可以合并和优化写入模式，提升大文件写入的顺序性。

**多块分配（Multiblock Allocator）**：与延迟分配配合，一次性为一组数据分配连续的磁盘块，减少碎片。

**Extent**：用 extent（区间）替代传统的间接块映射。一个 extent 可以描述一段连续的物理块，大幅减少了大文件的元数据开销。

[已验证: 官方文档, kernel.org/doc/html/latest/filesystems/ext4.html]

### ext4 在 Android 上的性能问题

ext4 面向服务器和桌面场景设计，它的优化策略在 HDD 时代是合理的。但 Android 设备的 I/O 特征与服务器截然不同，导致 ext4 暴露了明显的性能问题。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

**问题一：fsync 的放大效应**

这是 ext4 在 Android 上最严重的问题。SQLite 使用 WAL（Write-Ahead Log）模式或 rollback journal 模式，每次事务提交都需要调用 `fsync`。在 ext4 + jbd2（ordered 模式）+ 延迟分配的组合下，一次 `fsync` 会触发一系列连锁反应：

1. 延迟分配意味着脏页还没有分配物理块。`fsync` 时必须先为所有相关的脏页分配物理块——如果其他进程也积累了大量脏页（内核的 `flush` 线程每 30 秒触发一次），`fsync` 需要等待这些脏页的块分配完成。

2. ordered 模式要求在提交元数据日志之前，先把对应的数据块写入磁盘。jbd2 的 commit 线程需要等待所有脏数据刷盘，然后才能提交日志。

3. I/O 优先级倒置——`flush` 线程的异步 I/O 可能占据了存储设备队列，导致 `fsync` 的同步 I/O 被阻塞在队列后面等待。

最终的结果是：一次本应只需几毫秒的 `fsync`，在极端情况下可能需要几百毫秒甚至超过一秒。这就是用户感知到的"App 卡死"的直接原因。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

**问题二：原地更新与写放大**

ext4 采用就地更新（in-place update）策略——修改文件时，直接覆盖原有的磁盘块。对于 HDD 来说，这不是问题，因为 HDD 的扇区可以无限次覆盖写入。但 NAND 闪存完全不同——它不能就地覆盖写，必须先擦除整个 block（通常 128KB-256KB），然后再写入。修改一个 4KB 的页面，实际需要：读取整个 block → 在内存中修改 → 擦除 block → 写回整个 block。4KB 的写入被放大成了 128KB+，这就是写放大（Write Amplification）。

就地更新策略使得 ext4 无法有效利用闪存内部的并发能力，加速了存储芯片的磨损，也增加了垃圾回收（GC）的压力。

**问题三：缺乏闪存感知**

ext4 的块分配策略没有考虑 NAND 闪存的物理特性——它不知道哪些块在闪存内部是相邻的，也不知道哪些块已经在被 GC 搬运。这导致文件系统的分配模式和闪存内部的管理策略可能产生冲突，进一步加剧写放大和延迟。

### ext4 在 Android 上的现状

尽管 f2fs 已经成为 `data` 分区的首选，ext4 在 Android 上并没有完全消失。部分厂商的 `data` 分区仍在使用 ext4（通常配合厂商自定义的优化补丁），而 `metadata` 等小分区仍然普遍使用 ext4。此外，ext4 的成熟度和稳定性在业界是公认的——经过二十多年的打磨和大量线上验证，它的可靠性是新兴文件系统短期内难以匹敌的。[待验证: 具体哪些厂商的哪款机型仍在 data 分区使用 ext4]

## f2fs：为闪存而生的文件系统

### 设计背景与核心思想

f2fs（Flash-Friendly File System）由 Samsung 的 Jaegeuk Kim 于 2012 年开发，2013 年合并入 Linux 主线。它的设计目标很明确：针对 NAND 闪存的物理特性优化文件系统行为，解决 ext4 在移动设备上的性能瓶颈。[已验证: 官方文档, kernel.org/doc/html/latest/filesystems/f2fs.html]

f2fs 的核心设计思想可以概括为：**把随机写转换为顺序写**。NAND 闪存最擅长的就是顺序写入——因为它可以直接往空闲区域追加数据，不需要先擦除。f2fs 通过 Copy-on-Write（CoW）和日志结构（Log-Structured）的设计，尽可能让所有写入操作都变成追加写。

### 磁盘布局：六个区域

f2fs 把整个分区划分为六个区域，每个区域有明确的职责：

```
┌──────────────┐
│  Superblock  │  文件系统元信息（魔数、版本、块大小等）
├──────────────┤
│  Checkpoint  │  文件系统的一致性检查点（两组，交替使用）
├──────────────┤
│     SIT      │  Segment Information Table：记录每个 segment 的有效块数和位图
├──────────────┤
│     NAT      │  Node Address Table：inode/node 编号到物理块地址的映射
├──────────────┤
│     SSA      │  Segment Summary Area：记录每个 block 属于哪个 node 的哪个 offset
├──────────────┤
│   Main Area  │  主存储区，存放实际的 node（元数据）和 data（文件内容）
└──────────────┘
```

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_深入代码细节看f2fs在磁盘上的组织方式.md]

这里有几个关键的设计要点值得展开：

**NAT（Node Address Table）**：f2fs 不像 ext4 那样把物理块地址直接存在 inode 里，而是引入了一层间接映射——inode 中存储的是 node ID（nid），NAT 负责 nid 到物理块地址（physical block address）的翻译。这层间接映射是 f2fs 实现 CoW 的基础——修改数据时，新数据写到新的物理位置，只需要更新 NAT 中的映射，不需要修改 inode 本身。

**SIT（Segment Information Table）**：记录每个 segment 的使用状态——有多少有效块、哪些块是空闲的。f2fs 的垃圾回收器依赖 SIT 来决定哪些 segment 可以回收。

**冷热数据分离**：f2fs 把 Main Area 中的 segment 分为六种类型：hot/warm/cold × data/node。频繁更新的"热"数据（如 SQLite 日志）和很少修改的"冷"数据（如照片、APK 文件）被分配到不同的 segment。这样热数据的频繁修改不会影响冷数据所在的 block，垃圾回收时只需要处理热数据区域，大幅减少了 GC 的开销和写放大。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_深入代码细节看f2fs在磁盘上的组织方式.md]

### SQLite 原子写：f2fs 的杀手级优化

这是 f2fs 对 Android 性能贡献最大的一个特性。

SQLite 在写入数据库时，传统流程是这样的（以 rollback journal 模式为例）：先创建 journal 文件记录原始数据 → 修改数据库文件 → 调用 `fsync` 确保 journal 写入 → 调用 `fsync` 确保数据库文件写入 → 删除 journal 文件。每次事务至少两次 `fsync`，每次 `fsync` 都要等数据真正落盘。

f2fs 在 `kernel/common/include/uapi/linux/f2fs.h` 里定义了 `F2FS_IOC_START_ATOMIC_WRITE`、`F2FS_IOC_COMMIT_ATOMIC_WRITE` 和 `F2FS_IOC_ABORT_ATOMIC_WRITE` 这组 ioctl，允许数据库把一批页修改包成一次原子提交。工作流程可以概括成：

1. SQLite 调用 `ioctl(F2FS_IOC_START_ATOMIC_WRITE)` 告知内核，后续写入进入原子上下文
2. 事务页写到新的物理位置，旧数据仍然保持可读
3. 成功路径调用 `ioctl(F2FS_IOC_COMMIT_ATOMIC_WRITE)`，让 NAT / node 映射一次性切到新版本
4. 失败或回滚路径调用 `ioctl(F2FS_IOC_ABORT_ATOMIC_WRITE)`，丢弃本轮改动

这条路径的收益，在于把 journal 文件和多次同步点压成一次提交边界。提交阶段通常只剩一轮主要的持久化边界，而不是 journal 文件和数据文件各做一轮同步。Android 8.1 之后，SQLite / AOSP 已经具备 batch atomic write 的接入点；但是否真正走到这条路径，还要看设备是否使用 f2fs，以及内核、挂载选项和 SQLite 构建配置是否同时满足条件。[已验证: sqlite.org/src/info/5c5e4f6f6d + kernel/common/include/uapi/linux/f2fs.h]

### f2fs 的 fsync 优化

除了 SQLite 原子写，f2fs 在 `fsync` 本身的实现上也比 ext4 更高效。

默认 ext4 并不是把“被修改的数据块完整内容”都写进 jbd2。`data=ordered` 只把 metadata 写入 journal，同时要求相关 data blocks 先落到主文件系统；只有 `data=journal` 才会把 file data 连同 metadata 一起 journal。Android 常见的 ext4 `fsync` 成本，更多来自 ordered 模式下的数据先落盘约束、延迟分配触发的块分配，以及 jbd2 commit 等待。新一些内核里的 fast commit 也只是把受影响 metadata 的最小 delta 写进 fast commit 区，用来降低 commit latency，不等于默认双写整块数据。

f2fs 的路径不同。它用日志结构的追加写配合 NAT / node 映射更新，把数据写入和元数据切换拆成“新块落盘 + 映射翻转”两步。`fsync` 仍然要把这次修改涉及的数据块和必要的 node / NAT 元数据刷稳，必要时再带上 checkpoint 相关元数据，但不需要再走一遍 `data=journal` 式的数据全文 journal。这也是它在随机写和高频同步写场景里更容易把延迟压低的原因。

### f2fs 的代价：垃圾回收

f2fs 的 CoW 设计带来了优秀的写入性能，但也有代价——垃圾回收（Garbage Collection，GC）。因为数据不断写到新位置，旧的 segment 中会产生大量"过时"的数据（被新版本替代），f2fs 需要定期清理这些 segment，把仍然有效的数据搬到新位置，然后释放整个 segment。

f2fs 的 GC 分为前台和后台两种。后台 GC 由内核线程在存储负载较低时自动触发，对前台 App 的影响较小。但如果存储空间紧张（可用 segment 少于阈值），f2fs 会强制触发前台 GC——在 App 的写入路径上同步执行 GC。前台 GC 可能导致写入延迟飙升到数百毫秒，是 f2fs 用户在存储空间不足时感知到卡顿的主要原因。

在 Perfetto 中，f2fs 的 GC 活动可以通过 `f2fs_gc_*` 相关的 trace event 观察到。如果我们看到 App 线程在写入时出现长时间的 D 状态等待，同时有 `f2fs_gc` 相关的活动，那大概率是前台 GC 在阻塞写入。[待补充：Trace截图展示f2fs前台GC期间的I/O延迟]

### f2fs 前台 GC 触发机制详解

f2fs 的前台 GC 触发决策由 `has_not_enough_free_secs()` 函数（`fs/f2fs/segment.h`）控制。android15-6.6 的实现使用了三段判定逻辑：

```c
// fs/f2fs/segment.h — android15-6.6
static inline bool has_not_enough_free_secs(struct f2fs_sb_info *sbi,
        int freed, int needed)
{
    unsigned int free_secs = free_sections(sbi) + freed;
    unsigned int lower_secs, upper_secs;
    block_t curseg_space;

    if (unlikely(is_sbi_flag_set(sbi, SBI_POR_DOING)))
        return false;

    __get_secs_required(sbi, &lower_secs, &upper_secs, &curseg_space);
    // 情况 1：空闲充裕，直接返回 false
    if (free_secs > upper_secs)
        return false;
    // 情况 2：空闲不足，需要前台 GC
    if (free_secs <= lower_secs)
        return true;
    // 情况 3：空闲处于中间地带，取决于 curseg 是否还有空间
    return !curseg_space;
}
```

**三段判定逻辑**：
- `__get_secs_required()` 同时返回三个值：`lower_secs`（最低需求）、`upper_secs`（充裕阈值）和 `curseg_space`（当前 curseg 剩余空间）
- `free_secs > upper_secs`：空闲充足，不需要 GC
- `free_secs <= lower_secs`：空闲不足，必须触发前台 GC
- 介于两者之间时：取决于 curseg 是否还有可用空间（`!curseg_space` 表示 curseg 已满，仍需 GC）
- `lower_secs` 和 `upper_secs` 的计算包含 node/dentry/imeta 三类 dirty sections 加上 reserved sections（over-provisioning，默认约 5%）

**VFS 入口**：`f2fs_balance_fs()`（`fs/f2fs/segment.c`）在每次 VFS 写请求时被调用。当空闲不足需要前台 GC 时，根据 `GC_MERGE` mount option 决定执行方式：`GC_MERGE`=true 时写线程等待 `fggc_wq`，后台 `gc_thread` 被唤醒执行前台 GC（`wake_up(&gc_wait_queue_head)`）；否则同步调用 `f2fs_gc()`。

**Victim 选择**：前台 GC（`FG_GC`）使用 `GC_GREEDY` 算法——选择有效块最少的 segment 进行清理，以最快速度释放空间。后台 GC 则使用 `GC_CB`（Cost Benefit）或 `GC_AT`（Age Threshold）算法，在不阻塞前台 I/O 的前提下平衡清理效率。

**性能特征**：前台 GC 触发时可能导致 50-500ms 的同步 I/O 阻塞。CVE-2024-53220 修复了 `has_not_enough_free_secs()` 判定逻辑相关的问题，影响的是 free section 判定和 GC 触发时机。

`[源码锚点: kernel/common fs/f2fs/segment.h — has_not_enough_free_secs() / __get_secs_required(); fs/f2fs/segment.c — f2fs_balance_fs()]`

### f2fs 的 LFS / SSR 切换机制

#### 默认路径：LFS
f2fs 默认按 log-structured 的方式把新写入追加到干净 segment。这对应资料里常说的 LFS / copy-and-compaction：先顺序写新数据，后续再靠 GC 回收旧 segment。对闪存来说，这条路径通常比原地更新更友好。

#### 什么时候切到 SSR
Android 15-6.6 的决策入口在 `kernel/common/fs/f2fs/segment.c` 里的 `f2fs_need_SSR()`。它会同时看 dirty node sections、dirty dentry sections、dirty imeta sections、`min_ssr_sections`、`reserved_sections`，以及 `GC_URGENT_HIGH`、checkpoint disabled 这类强制条件；当前实现不是单一的固定 5% 阈值。源码里的核心判断可以概括成：

```c
free_sections <= node_secs + 2 * dent_secs + imeta_secs
                + min_ssr_sections + reserved_sections
```

命中后，分配策略会更积极地复用 dirty segment 里的 invalid blocks，也就是 SSR（selective segment reuse）。旧文里把它叫成 threaded logging，只能算历史描述的近似说法；放到当前源码语境里，直接写 LFS / SSR 更贴近实现。

#### SSR 与 GC 的关系
SSR 不是 GC 的替代品。它的作用，是在 free section 紧张时先让写入路径继续向前推进，少等一次“先清理出干净 segment再写”的过程。真正的空间回收仍然由 `kernel/common/fs/f2fs/gc.c` 里的前台 / 后台 GC 完成，victim 选择和回收节奏也都在那套回收逻辑里。SSR 负责缓冲写入压力，GC 负责把空间拿回来。

#### Perfetto 里怎么观察
Perfetto 通常不会给出一个名为“SSR”的直接 slice。排查时更可操作的线索是：
- block I/O 延迟是否在空间逼近上限时突然抬高；
- 有没有 `f2fs_gc_*` 相关 trace event 或内核日志同步出现；
- 主线程 / binder 线程是否在 `fsync`、`fdatasync`、`pwrite` 一类 syscall 上进入 D 状态。

如果这三类信号一起出现，更像是 free section 紧张后写路径开始复用旧 segment，并且 GC 跟不上了。

### 在 Perfetto 中的观察要点

对于 f2fs 分区上的 I/O 分析，在 Perfetto 中我们应该关注：

1. **block I/O slice 的延迟**：先看同一台设备、同一 workload 下的相对变化，不要把某个 UFS 代际的经验值当成通用门槛。延迟突然抬高时，再分辨是 GC、I/O 调度还是存储器件本身的问题。

2. **f2fs 相关的 trace event**：如果内核编译时启用了 f2fs 的 tracepoint，能看到 GC 活动、segment 分配等信息。

3. **主线程的 D 状态等待**：配合 syscall 信息，确认是否是 `fsync` / `fdatasync` / `pwrite` 之类的同步写导致阻塞。

## 现代 Android /data 分区还依赖三类文件系统能力

只讲 ext4 / f2fs / EROFS 还不够。日常性能分析里，经常直接撞到的还有配额、目录匹配和加密三组能力。

### Project Quota：把“存储统计”从全盘遍历变成计数读取

系统设置页、`StorageStatsManager` 和很多空间分析工具都要回答一个问题：某个用户、某个 UID、某个包到底占了多少空间。没有 quota 时，只能递归扫目录，耗时和 I/O 压力都很高。

Android 在 ext4 / f2fs 打开 project quota 后，可以把目录树映射到 project id，再由内核维护计数器。这样系统查询存储占用时，不需要每次都对 `/data` 做一轮 `du` 式遍历。对性能分析来说，“查看占用”本身通常不是一次重 I/O 扫描。

### Casefolding：让大小写无关匹配留在文件系统层

Android 需要兼顾 Linux 的大小写敏感语义和移动设备上常见的大小写无关文件名习惯。ext4 / f2fs 的 casefold 机制会在目录查找阶段做 Unicode case-insensitive 匹配，目录比较逻辑直接落在文件系统层。

这类能力常见于共享存储相关目录。它减少了把名字匹配逻辑放在用户态适配层的压力，也让目录查找路径更短。

### fscrypt 与 Inline Encryption：加密在 I/O 路径里的真实位置

Android 的文件级加密建立在 fscrypt 上，真正落到 ext4 / f2fs 的读写路径时，还会继续和块层的 inline encryption 能力配合。

设备具备 Inline Crypto Engine 时，文件系统可以把数据加解密工作交给存储硬件，CPU 主要负责密钥和请求编排。对 trace 分析来说，加密不再等同于“每次写入都多跑一段 CPU 密集计算”。

16KB page size 设备上，这里还会出现 data unit size 约束；块大小、页大小和 inline crypto 能力需要一起看，单看文件系统名字不够。

> [源码锚点: frameworks/base/services/usage/java/com/android/server/usage/StorageStatsService.java]
> [源码锚点: frameworks/base/core/java/android/app/usage/StorageStatsManager.java]
> [源码锚点: kernel/common/fs/f2fs/dir.c — `f2fs_match_name`]
> [源码锚点: kernel/common/fs/crypto/inline_crypt.c]

## EROFS：为只读分区设计的极致压缩

### 从 ext4 到 EROFS 的切换

在 6.1 节中我们讨论过，`system`、`vendor` 等分区是只读的，受 dm-verity 保护。既然只读，使用 ext4 这种读写文件系统就存在开销浪费——日志系统、块分配器、空闲空间管理等模块在只读场景下全部多余。

EROFS（Enhanced Read-Only File System）就是为解决这个问题而生的。它由华为工程师高翔（Xiang Gao）开发，2019 年合并入 Linux 5.4 主线。华为在 EMUI 9.0.1 中首次大规模部署 EROFS，随后 Samsung、OPPO、小米等厂商也陆续跟进。Android 13 之后，AOSP 已经给出完整的 EROFS BoardConfig / fstab 配置，Virtual A/B 也正式支持 EROFS。这里需要收窄表述：官方要求的是设备侧具备 EROFS 支持，GMS/VTS 生态把它推成了只读分区的主流方案；这不等于“所有只读分区都被 CDD 强制格式化成 EROFS”。[已验证: 官方文档, source.android.com/docs/core/architecture/kernel/erofs and kernel.org]

### EROFS 的核心优势

**压缩与去重**：EROFS 最大的价值在于它对存储空间的高效利用。Android 13-15 的常见只读分区以 LZ4 为主（默认压缩），内核可选启用 LZMA 或 DEFLATE。ZSTD 压缩需要 Android 16 / kernel 6.12+ 或厂商 backport 并启用 `CONFIG_EROFS_FS_ZIP_ZSTD`。EROFS 还具有字节粒度的去重（deduplication）能力。实测数据显示，EROFS 压缩后的 system 分区镜像比未压缩的 ext4 镜像小 30%-45%，相当于为 128GB 的设备节省了 800MB 到 2GB 的空间——这些空间可以分配给 `data` 分区供用户使用。

[已验证: 多来源交叉验证, esper.io, androidauthority.com, pocketnow.com]

**随机读性能提升**：EROFS 的压缩不仅节省空间，还能提升读性能——因为压缩后需要从存储读取的数据量更小。对于随机读场景（如 App 启动时加载大量小文件），EROFS 相比 ext4 有约 20% 的性能提升，某些场景下可达 300%。在 Pixel 设备上，EROFS 压缩带来了 10%-15% 的启动时间改善。

**无日志开销**：作为只读文件系统，EROFS 不需要日志系统。没有 jbd2 的 commit 开销，没有 metadata 的同步写入，mount 速度也更快。这使得设备启动时 `system` 分区的挂载时间更短。

**安全增强**：只读属性本身就是一种安全机制——`system` 分区上的文件无法被运行时修改，配合 dm-verity 的完整性校验，构成了双重保护。


### dm-verity 与 EROFS 的协同工作机制

在第 6.1 节中我们提到 dm-verity，但未深入展开它与 EROFS 的协作机制。两者是**互补关系**，而非耦合关系：

**dm-verity 的职责**（完整性校验）：
- 在运行时**按需逐块**验证 system/vendor 分区的数据完整性（每个 4KB block 的 SHA256 hash）
- 信任锚点是 build 阶段由 OEM 私钥签名的 root hash，存储在 vbmeta 分区
- dm-verity 要求保护分区必须是**只读**的——EROFS 天生只读，两者的要求天然匹配

**EROFS 的职责**（高效只读存储）：
- 提供压缩的只读文件系统（LZ4 默认压缩，镜像减小 30-45%）
- 本身不提供完整性校验，需要 dm-verity 在下层叠加完整性保护
- 设计为与 dm-verity 协同工作（Android build system 中 EROFS 分区配置 `ro + verify` flag）

**Build 阶段协作**：
`avbtool add_hashtree_footer`（`external/avb/avbtool.py`）生成 EROFS 镜像的哈希树：
1. 对每个 4KB data block 计算 SHA256 hash（leaf）
2. 递归聚合形成 Merkle tree，最终得到 root hash
3. root hash + salt + hash tree offset 存入 vbmeta struct
4. vbmeta struct 由 OEM 私钥签名，嵌入 vbmeta partition

**Boot 阶段协作**：
1. Bootloader 读取 vbmeta partition，用内置 OEM 公钥验证签名
2. 从 vbmeta 提取 system 分区的 root hash，传递给 kernel
3. kernel dm-verity 模块挂载 EROFS 时重建 hash tree，逐块验证
4. 每读一块数据 → 计算 SHA256(data + salt) → 查 hash tree → 验证到 root
5. 验证通过 → 数据返回给 EROFS 文件系统层；验证失败 → I/O error

**dm-verity 保护下的 EROFS 挂载栈**（Dynamic Partition 场景）：
```
物理 super partition
  → dm-linear（映射 dynamic partition 边界）
    → dm-verity（哈希校验层）
      → EROFS 文件系统
        → /system 挂载点
```

**性能数据**（来源：android.com 官方文档）：
- 顺序读取：dm-verity 额外开销约 5-15%（SHA256 计算）
- 缓存读取：几乎无额外开销（hash 结果被内核页缓存）
- 内存开销：10GB 分区约需 81MB hash storage（约 0.8% overhead）
- EROFS 压缩带来 10-15% 启动时间改善（间接减少 dm-verity 校验的绝对数据量）

**为什么 EROFS 是 dm-verity 的「理想搭档」**：
1. EROFS 只读设计满足 dm-verity 对保护分区的只读要求，无需额外 flag 检查
2. EROFS 的 in-place decompression（LZ4 在同一 page 内解压）减少了 dm-verity 按需校验时的内存分配开销
3. EROFS 压缩使相同数据量的 dm-verity 校验绝对字节数减少 30-45%
4. Android 13 之后 EROFS 在 launch device 上快速普及，使 dm-verity 保护的系统分区更小、更快

**Perfetto 中的可观测性**：
dm-verity 的 block-level 验证目前没有独立的 Trace slice。在 Perfetto 中，它通常只会折叠进底层 storage I/O 延迟里。更可操作的观察路径，是先看 block layer 的 `block_rq_issue` / `block_rq_complete`，再按设备内核是否开放对应事件，补看 mmc / UFS host controller tracepoint；如果内核还打开了 dm 或 dm-verity 相关 ftrace 事件，再把映射层时延一起对照。公开默认配置里通常看不到一个单独名为 dm-verity 的轨道，因此很难把“读数据”和“验 hash”完全拆开。dm-verity hash prefetch 机制（`DM_VERITY_HASH_PREFETCH_MIN_SIZE`，默认 128 blocks）会进一步把一部分验证开销藏在预取里。

<!-- AIW-源码调研-2026-04-20 -->

### EROFS 与 OTA 升级

EROFS 完全支持 Android 13+ 的 Virtual A/B OTA 升级机制。OTA 包生成工具能够智能地解压 LZ4 流来生成增量包（delta），因此 EROFS 分区的 OTA 包大小与 ext4 分区相比几乎没有差异，切换到 EROFS 不会增加用户的 OTA 下载量和升级时间。[已验证: 官方文档, source.android.com/docs/core/ota]

### [图：ext4 vs EROFS system 分区布局对比]

EROFS 在 Android 上的布局通常是：
- `system` 分区：EROFS + LZ4 压缩
- `vendor` 分区：EROFS + LZ4 压缩（或 ext4，取决于厂商配置）
- `product` 分区：EROFS 或 ext4
- `data` 分区：f2fs（需要读写，不能用 EROFS）

## 文件系统对随机读写性能的影响

### 为什么随机写是瓶颈？

在分析存储性能时，我们通常关注顺序读写和随机读写两大类指标。对于 Android 设备来说，**随机写性能几乎总是最薄弱的环节**。

原因有两层。第一层在闪存硬件层面——NAND 闪存的写入粒度是 page（通常 4KB 或 8KB），但擦除粒度是 block（通常包含 128-512 个 page）。即使只修改一个 page，也需要读取整个 block → 在内存中修改 → 擦除 block → 写回整个 block。随机写入导致大量 block 被部分修改，产生大量的"读-改-写"操作。

第二层在文件系统层面。ext4 的就地更新策略使得每次随机写入都可能触发上述的"读-改-写"循环。f2fs 的 CoW 策略通过把修改写到新位置来避免这个问题，但代价是需要维护复杂的映射表和定期执行 GC。

### 不同文件系统的随机 I/O 特性

| 操作 | ext4 | f2fs | EROFS |
|------|------|------|-------|
| 顺序读 | 优秀（Page Cache 加速） | 优秀 | 优秀（压缩减小读取量） |
| 随机读 | 良好 | 良好 | 优秀（紧凑布局+压缩） |
| 顺序写 | 良好 | 优秀（追加写） | N/A（只读） |
| 随机写 | 较差（就地更新+写放大） | 良好（CoW转换为追加写） | N/A（只读） |
| fsync | 较差（日志+延迟分配连锁） | 良好（逻辑日志+无延迟分配） | N/A（只读） |

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

这个对比清楚地解释了为什么 Android 的 `data` 分区从 ext4 切换到 f2fs——f2fs 在手机最敏感的两个维度（随机写和 fsync）上都有明显优势。

## fsync 与 fdatasync：同步写入的两种策略

### 两者的区别

`fsync()` 和 `fdatasync()` 是 POSIX 定义的两个同步写入接口，它们的行为有细微但重要的区别：

- `fsync(fd)`：确保 fd 对应文件的所有修改（包括数据和元数据）都写入磁盘。元数据包括文件大小、修改时间、权限等。
- `fdatasync(fd)`：只确保文件数据写入磁盘，不保证元数据（除非元数据的变化会影响后续的数据读取，比如文件大小变化）。

`fdatasync()` 比 `fsync()` 少了一次元数据的磁盘写入，理论上更快。但实际在 Android 上，绝大多数 I/O 库（包括 SQLite）使用的都是 `fsync()`，因为数据完整性是第一优先级——在手机可能随时异常掉电的场景下，保证数据的完全一致性比节省几毫秒更重要。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md]

### fsync 优化策略

在 App 层面，减少 `fsync` 的影响有几种策略：

**SharedPreferences 的 apply() vs commit()**：这是最简单也最常见的优化。`commit()` 同步写入并等待 `fsync` 完成，会阻塞调用线程；`apply()` 异步写入，立即返回，`fsync` 在后台线程执行。对于不需要立即确认写入结果的场景，应该始终使用 `apply()`。

**SQLite 事务批处理**：不要在循环中逐条执行 `INSERT`/`UPDATE` 并自动提交（每次提交都触发 `fsync`），而是用 `BEGIN TRANSACTION` ... `COMMIT` 把多条语句包在一个事务里——这样只在 `COMMIT` 时触发一次 `fsync`。

**WAL 模式**：SQLite 的 WAL（Write-Ahead Log）模式相比默认的 rollback journal 模式，在读写并发场景下性能更好。WAL 模式允许读操作和写操作并发进行（读操作访问旧的数据库内容，写操作追加到 WAL 文件），减少了锁竞争。

**Room 的增量写入**：如果使用 Jetpack Room，可以利用 `@Transaction` 注解和批量操作 API 来减少隐式 `fsync` 的调用次数。

在 Perfetto 中观察 `fsync` 行为时，可以通过 `ftrace` 事件跟踪 `ext4_sync_file_enter`/`ext4_sync_file_exit`、`f2fs_sync_file_enter`/`f2fs_sync_file_exit` 等 tracepoint，直接看到每次 `fsync` 的耗时。注意区分 `*_sync_file`（per-file fsync）和 `*_sync_fs`（superblock sync），前者才对应应用层调用的 `fsync()`。还可以结合 `block_rq_issue`/`block_rq_complete` 观察底层块设备 I/O 完成情况。如果发现主线程上频繁出现超过 10ms 的 `fsync`，就需要排查是否是不必要的同步写入或者文件系统层面的瓶颈。

## 扩展：各厂商的文件系统选型

Android 设备上的文件系统选型并非完全统一，各厂商有不同的策略：

**Google Pixel**：从 Pixel 3 开始，`data` 分区使用 f2fs。Google 在 AOSP 中积极推动 EROFS 的标准化，近几代 Pixel 机型的只读分区也广泛采用 EROFS。

**Samsung**：f2fs 的创始者，`data` 分区长期使用 f2fs。Samsung 也是 EROFS 的早期采用者之一。

**OPPO/一加**：OPPO 内核团队对 f2fs 有深度的优化经验，发表过多篇 f2fs 相关的技术文章。`data` 分区使用 f2fs，`system` 分区在较新机型上切换到 EROFS。

**小米**：跟进 Google 的 AOSP 标准，新机型上 `system` 使用 EROFS，`data` 使用 f2fs。

[待验证: 以上信息主要基于公开的技术分享和 AOSP 配置，具体到某款机型的文件系统选型需要查看 /proc/mounts 输出]

开发者可以通过 `adb shell mount` 或 `adb shell cat /proc/mounts` 命令查看设备上各分区实际使用的文件系统类型。在 Perfetto trace 中，如果 I/O 延迟异常，首先确认 `data` 分区的文件系统类型——如果是 ext4，很多 fsync 相关的性能问题在 f2fs 上可能不存在。

## 扩展：文件系统碎片化与长期性能退化

我们在 6.1 节中讨论过写入放大，现在从文件系统层面再深入看一下碎片化导致的性能退化。

ext4 的碎片化问题尤为突出。随着使用时间增长，频繁的创建-删除-修改操作使得 ext4 的空闲空间变得越来越零散。新写入的文件不得不分散在不连续的物理块中，导致读取时需要多次寻道——虽然对 SSD 来说没有物理寻道的开销，但分散的块意味着更多的 I/O 请求和更低的预读效率。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

f2fs 的碎片化问题表现形式不同。f2fs 的 CoW 机制本身不会产生传统意义上的文件碎片（因为写入总是追加到新位置），但 CoW 会产生大量的"无效 segment"——被旧版本数据占据但已经不再被引用的 segment。当无效 segment 积累到一定程度，f2fs 必须执行 GC 来回收空间。GC 的效率取决于冷热分离的效果——如果冷热数据混合在一起，GC 需要搬运大量仍然有效的冷数据，增加了写放大。

性能退化的直接表现，通常是同一台设备在存储空间充足时随机写延迟较低，空间逼近上限、GC 和磨损控制变重之后，尾延迟会明显拉长。这里不要把 0.1ms、1ms、5ms 这类数字当成通用基线；它们强依赖 UFS 代际、容量、挂载参数、温度和 workload。更稳的做法，是对比同机型、同测试条件下的基线与尾延迟分布。

缓解碎片化的方法包括：保持足够的可用空间（至少 10%-15%）、避免频繁的小文件创建删除、使用 f2fs 的 `f2fs_io` 工具定期触发碎片整理（需要 root 权限）、以及在 App 层面做好数据缓存策略，减少不必要的磁盘写入。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

## 版本演进：三个文件系统在 Android 中的变迁

我们在前面分别讲了 ext4、f2fs 和 EROFS 的设计思想和性能特征，现在把它们放到 Android 的版本时间线上，看看 Google 和厂商是如何一步步推动文件系统演进的。理解这条时间线，有助于我们在分析 Trace 时快速判断"这台设备用的是哪个时代的文件系统配置"，从而缩小问题排查的范围。

### ext4：从起点到逐步退守

Android 自诞生以来就使用 ext4 作为所有分区的默认文件系统。在 Android 4.x 到 7.x 的时代，`system`、`data`、`cache` 等分区清一色都是 ext4。这个选择不难理解——ext4 是 Linux 生态中最成熟稳定的文件系统，社区支持完善，出问题的概率最低。

但正如我们前面分析的，ext4 在闪存设备的随机写和 fsync 场景下暴露了越来越明显的性能问题。随着 App 功能越来越复杂、数据库操作越来越频繁，主线程因 fsync 阻塞导致的卡顿成了用户投诉的重灾区。Google 从 Android 8.0 开始，在 AOSP 推荐配置中将 `data` 分区转向 f2fs，ext4 逐步退守到 `metadata`、`cache` 等小分区以及部分厂商的定制场景。到 Android 13 之后，ext4 在主流设备上的可见范围已经很小了——`system` 让位给 EROFS，`data` 让位给 f2fs，ext4 主要留在一些对小分区可靠性要求极高的场景中。

### f2fs：从 Samsung 自研到行业标配

f2fs 的演进路径比较独特，项目起点来自 Samsung 的 Jaegeuk Kim：2012 年启动开发，2013 年合并入 Linux 3.8 主线。Samsung 自然是最早的采用者，在 Galaxy S 系列的 `data` 分区上率先部署 f2fs。

其他厂商的跟进速度不一。OPPO 在 2016 年前后开始在部分机型上使用 f2fs，并组建了专门的内核团队做深度优化。一加在较新机型上全面采用。小米的跟进稍晚，但在 2019 年后的机型上 `data` 分区基本都用了 f2fs。

Google 自己的 Pixel 系列从 Pixel 3（2018 年）开始在 `data` 分区使用 f2fs。从 Android 10 开始，AOSP 的推荐配置明确建议 `data` 分区使用 f2fs。一个关键的里程碑是 Android 8.1——这一版本引入了对 SQLite batch atomic write 的支持（编译选项 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE`）。当 SQLite 检测到文件系统和内核能力都满足条件时，可以用原子写接口替代传统的 journal + 多次同步流程；收益主要体现在减少额外写放大和同步等待，具体幅度要看 workload。

Android 15 把 16KB 页面大小（Page Size）带进正式适配范围，f2fs 的边界也随之收紧。内核头文件 `include/linux/f2fs_fs.h` 直接把 `F2FS_BLKSIZE` 定义为 `PAGE_SIZE`，也就是块大小必须和页大小一致。结果是：4KB 时代创建的 4KB f2fs 镜像，不能直接搬到 16KB kernel 上继续挂载为 `/data`；设备切到 16KB 方案时，通常要重建文件系统并完成数据迁移。这一项是格式兼容约束，不是普通的 GC 调优。

### EROFS：从华为自研到事实标准

EROFS 的演进是 Android 文件系统历史上推进最快的案例之一。

华为工程师高翔在 2018 年开始开发 EROFS，2019 年合并入 Linux 5.4 主线。同年华为在 EMUI 9.0.1（基于 Android 9）中首次大规模部署——当时华为的 P30 系列是首批使用 EROFS 的消费级设备。实测数据显示，EROFS 压缩后的 system 镜像比 ext4 小约 30%，随机读性能提升约 20%，App 启动速度改善 10%-15%。

Samsung、OPPO、小米等厂商在 2020-2021 年间陆续跟进，在各自的高端机型上启用 EROFS。但由于缺乏统一标准，各厂商的实现细节（压缩算法选择、分区布局）存在差异。

转折点在 Android 13。AOSP 的 EROFS 文档已经补齐 BoardConfig、fstab 和 Virtual A/B OTA 支持，GMS 设备也在这一代开始大规模把只读分区迁移到 EROFS。这里更稳的说法是：Android 13 以后，EROFS 成为只读分区的事实标准；是否所有只读分区都一刀切使用 EROFS，仍取决于设备分区方案和内核支持。

到 Android 16（2025 年），EROFS 在 Android 生态中的渗透率已经非常高。新增加的改进包括对更大压缩单元的支持和去重能力的增强，进一步提升了存储空间利用率。

### 时间线速览

| Android 版本 | 年份 | ext4 | f2fs | EROFS |
|---|---|---|---|---|
| 4.0–7.x | 2011–2016 | 全分区默认 | 仅 Samsung 部分机型 | 未使用 |
| 8.0 | 2017 | 全分区默认 | Samsung/OPPO 部分机型 | 未使用 |
| 8.1 | 2017 | data 仍为 ext4 | 引入 SQLite batch atomic write | 未使用 |
| 9 | 2018 | data 仍为 ext4 | Pixel 3 开始使用 f2fs | 华为 EMUI 9.0.1 首次部署 |
| 10 | 2019 | 退守小分区 | AOSP 推荐配置 | 多厂商跟进 |
| 11–12 | 2020–2021 | 小分区 | 主流设备普及 | 高端机型采用 |
| 13 | 2022 | 小分区 | data 分区标配 | 只读分区大规模转向 EROFS |
| 14 | 2023 | 小分区 | data 分区标配 | 全面普及 |
| 15 | 2024 | 小分区 | 适配 16KB Page Size，4KB `/data` 不能原样迁移 | 全面普及 |
| 16 | 2025 | 小分区 | 持续优化 | 持续优化 |

[已验证: 时间线基于 AOSP 官方文档、CDD 要求、kernel.org changelog 和厂商公开技术分享综合整理]

## 常见问题与误区

在分析存储相关的性能问题时，我们经常会遇到一些根深蒂固的误解。这些误解不仅会浪费排查时间，还可能导致错误的优化方向。我们梳理了几个最常见的误区。

### "f2fs 一定比 ext4 快"

这是最常见也最危险的误解之一。f2fs 在随机写和 fsync 场景下确实比 ext4 有明显优势，但这不意味着它在所有场景下都更快。

顺序读写方面，在 Page Cache 命中率高的情况下，ext4 和 f2fs 的性能几乎没有差异——因为数据根本不经过文件系统的写入路径。f2fs 的 GC 机制在存储空间紧张时会引入不可预测的延迟峰值，这种峰值在 ext4 上不会出现。在存储接近满的情况下，f2fs 的前台 GC 可能导致比 ext4 更严重的卡顿。此外，f2fs 的成熟度和边缘情况处理（如异常断电后的恢复）虽然经过多年改进已经非常可靠，但与经过二十多年打磨的 ext4 相比，在极端场景下仍然可能存在风险。

所以正确的理解是：f2fs 在 Android 手机的典型 I/O 负载下（随机写密集、fsync 频繁）整体优于 ext4，但不是"全面碾压"。在分析 Trace 时，不应该因为看到 f2fs 就假设存储性能一定没问题。

### "EROFS 可以用于 data 分区"

EROFS 是只读文件系统——这个限制是设计层面决定的，不是通过配置可以绕过的。EROFS 没有 journal、没有块分配器、没有空闲空间管理，因为它根本不需要处理运行时的写入操作。试图把 data 分区格式化为 EROFS 是不可行的，即使强行挂载，任何写入操作都会直接失败。

有些开发者会把 EROFS 的压缩能力和 App 的资源压缩混淆——EROFS 的压缩发生在构建时（系统镜像打包），运行时是解压读取。App 的资源压缩（如 WebP、compressed XML）是另一层优化，两者互不冲突，但解决的问题完全不同。

### "fsync 在 f2fs 上完全没有开销"

f2fs 通过逻辑日志和 CoW 机制大幅降低了 fsync 的开销，但"大幅降低"不等于"没有"。在正常情况下，f2fs 上的 fsync 确实比 ext4 快得多——通常只需更新少量的元数据映射。但当 f2fs 正在执行 GC（尤其是前台 GC）时，fsync 仍然可能被阻塞数十甚至数百毫秒。存储器件本身的健康状况（磨损程度、预留空间是否充足）也会影响 fsync 的实际延迟。

在 Perfetto 中看到 f2fs 分区上的 fsync 延迟异常时，不要因为"用了 f2fs 就不应该有问题"而跳过存储层面的排查。正确的做法是检查 GC 活动、存储空间使用率和器件健康状态。

### "手机卡一定是存储变慢了"

这是从用户角度最容易产生的直觉判断，但实际情况远比这复杂。手机使用一段时间后变卡，可能的原因包括：存储碎片化和 GC 压力增大（这确实是存储层面的）、后台进程数量增加导致内存和 CPU 竞争、App 缓存和数据膨胀导致数据库查询变慢、系统更新引入了新的性能回退等。

在 Trace 中排查"手机变卡"问题时，应该先确认瓶颈在哪里——是主线程在 I/O 上阻塞（存储问题），还是在 CPU 上跑满了计算（算法或渲染问题），还是因为内存不足导致频繁的低内存回收（内存问题）。只有当 Trace 明确显示主线程在 D 状态等待 I/O 时，才需要深入到文件系统层面分析。

### "恢复出厂设置能彻底解决文件系统碎片化"

恢复出厂设置确实会清除 data 分区的所有数据并重新格式化，短期内能消除碎片化和 GC 压力。但这只是"重置"，不是"解决"——恢复后随着使用，碎片化问题会再次累积。如果根本原因是不良的 I/O 使用模式（某个 App 频繁创建和删除大量小文件），恢复出厂设置后问题会再次出现。

更有针对性的做法是：识别产生大量随机 I/O 的 App（通过 Perfetto 的 block I/O 视图），优化其数据存储策略，保持足够的可用存储空间（至少 10%-15%），以及在系统层面确保 f2fs 的后台 GC 有足够的执行窗口。

## 参考资料

### AOSP 源码路径

- f2fs 核心实现：`kernel/common/fs/f2fs/`（内核源码树）
- f2fs SSR / 分段分配：`kernel/common/fs/f2fs/segment.c`
- f2fs GC：`kernel/common/fs/f2fs/gc.c`
- f2fs ioctl 接口定义：`kernel/common/include/uapi/linux/f2fs.h`（`F2FS_IOC_START_ATOMIC_WRITE` / `COMMIT` / `ABORT`）
- f2fs 块大小与磁盘布局结构：`kernel/common/include/linux/f2fs_fs.h`（`F2FS_BLKSIZE == PAGE_SIZE` 以及 Superblock / Checkpoint 等定义）
- f2fs 目录匹配：`kernel/common/fs/f2fs/dir.c`（`f2fs_match_name` / casefold 路径）
- ext4 / jbd2 实现：`kernel/common/fs/ext4/`、`kernel/common/fs/jbd2/`
- EROFS 实现：`kernel/common/fs/erofs/`
- fscrypt / inline encryption：`kernel/common/fs/crypto/`
- Storage Stats 服务：`frameworks/base/services/usage/java/com/android/server/usage/StorageStatsService.java`
- SQLite batch atomic write 适配：AOSP SQLite dist sources（搜索 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE`）
- VFS 层：`kernel/common/fs/`、`kernel/common/include/linux/fs.h`

### 官方文档

- Android Storage 文档：<https://source.android.com/docs/core/storage>
- AOSP EROFS 文档：<https://source.android.com/docs/core/architecture/kernel/erofs>
- 16 KB page size 概览：<https://source.android.com/docs/core/architecture/16kb-page-size/16kb>
- Android Data Storage 指南：<https://developer.android.com/training/data-storage>
- f2fs 内核文档：<https://www.kernel.org/doc/html/latest/filesystems/f2fs.html>
- ext4 内核文档：<https://www.kernel.org/doc/html/latest/filesystems/ext4.html>
- EROFS 内核文档：<https://www.kernel.org/doc/html/latest/filesystems/erofs.html>
- VFS 内核文档：<https://www.kernel.org/doc/html/latest/filesystems/vfs.html>
- SQLite 官方文档（fsync 与事务）：<https://www.sqlite.org/atomiccommit.html>
- SQLite atomic write 特性说明：<https://www.sqlite.org/src/info/5c5e4f6f6d>

### 深入阅读

- LWN: f2fs 介绍与设计理念（2012）：<https://lwn.net/Articles/518988/>
- LWN: EROFS 合并入主线（2019）：<https://lwn.net/Articles/799717/>
- Samsung f2fs 技术分享： Jaegeuk Kim 在 Linux Storage Filesystem & Memory Management Summit 的历次演讲
- 华为 EROFS 技术分享：高翔在 Linux Plumbers Conference 的演讲
- Android 13 CDD 存储相关要求：<https://source.android.com/docs/compatibility/13/android-13-cdd>
- esper.io Android 文件系统分析系列

## 小结：文件系统选择对性能的影响

回到我们开头提到的 `fsync` 卡顿问题。当我们看到主线程在 `fsync` 上阻塞时，分析路径应该是：

1. **确认文件系统类型**：通过 `/proc/mounts` 或 Perfetto trace 信息查看 `data` 分区用的是 ext4 还是 f2fs。如果是 ext4，fsync 的放大效应是已知问题。

2. **检查是否是 SQLite/SharedPreferences**：确认阻塞是否由数据库操作或配置写入引起。如果是，检查是否使用了事务批处理、是否使用了 `apply()` 替代 `commit()`。

3. **观察 f2fs GC 活动**（如果使用 f2fs）：检查是否有前台 GC 阻塞了写入。如果是，可能需要清理存储空间。

4. **评估文件系统切换的可行性**：对于仍然使用 ext4 的 `data` 分区，切换到 f2fs 可能带来显著的 fsync 性能提升——尤其是在 SQLite 密集使用的场景下。

Android 文件系统的演进路线清晰：ext4 负责通用场景，f2fs 负责闪存设备的随机写密集场景，EROFS 负责只读分区。没有万能的文件系统，理解它们各自的设计取舍，是存储性能优化的基础。

下一节（6.3）我们将深入 I/O 调度层，看看在文件系统之下、存储器件之上，Linux 内核是如何管理和调度 I/O 请求的。
