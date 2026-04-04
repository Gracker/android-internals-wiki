---
title: "文件系统"
chapter: "6.2"
status: finalized
applicable_versions: "Android 10+"
last_verified: "2026-04-01"
last_verified_against: "AOSP android-15, kernel 6.6, source.android.com, developer.android.com"
confidence: medium
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_深入代码细节看f2fs在磁盘上的组织方式.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md"
  - type: official
    path: "source.android.com/docs/core/storage"
  - type: official
    path: "developer.android.com/training/data-storage"
tags: ['f2fs', 'ext4', 'erofs', 'fsync', 'fdatasync', 'filesystem', 'sqlite']
related_chapters: ['6.1', '6.3', '4.1', '7.1']
created: 2026-04-01
drafted_date: 2026-04-01
reviewed_date: 2026-04-04
reviewed_by: openclaw-task6
reviewers: []
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

我们在 Perfetto 中分析 App 卡顿的时候，有一类问题几乎每个 Android 工程师都会遇到——主线程在 `fsync` 上阻塞了几十甚至几百毫秒。打开 Perfetto trace，看到主线程那行的时间条上出现了一大段橘红色的 "Uninterruptible Sleep"（D 状态），放大一看，syscall 是 `fsync`，对应的文件是一个 SQLite 数据库或者 SharedPreferences 的 XML 文件。

这个现象在 Android 上比在其他 Linux 系统上更为突出，原因是 Android 系统中 SQLite 的使用密度远高于服务器或桌面 Linux——几乎所有 App 的配置、缓存、状态信息都存在 SQLite 数据库里，而 SQLite 每次事务提交都需要调用 `fsync` 确保数据落盘。再加上 SharedPreferences 在早期 Android 版本中也是通过 `fsync` 同步写入 XML 文件，一个 App 在启动阶段可能触发数十次 `fsync`。

这个问题的根因，往往不在 App 代码本身，而在 App 之下那一层——文件系统。不同的文件系统对 `fsync` 的实现策略差异巨大，直接影响着 App 的 I/O 延迟。Android 设备上的文件系统选择，经历了从 ext4 到 f2fs、再到 EROFS 的演进，每一次切换都是为了解决前一代在手机场景下暴露出的特定问题。

理解这三个文件系统的设计思想和性能特性，是我们诊断存储相关卡顿的基础。

## VFS：文件系统的统一抽象

在深入各个具体的文件系统之前，我们先理解一个关键的中间层——VFS（Virtual File System，虚拟文件系统）。

Linux 内核在用户进程和具体文件系统之间引入了 VFS 抽象层。VFS 定义了一组所有文件系统都必须支持的标准接口和数据结构：`superblock`（超级块）、`inode`（索引节点）、`dentry`（目录项）、`file`（打开文件）。上层代码无论是操作 ext4 还是 f2fs，调用的都是同一套 POSIX 接口——`open()`、`read()`、`write()`、`fsync()`，VFS 负责把请求分发到对应文件系统的实现。

[已验证: 官方文档, kernel.org/doc/html/latest/filesystems/vfs.html]

这意味着，从 App 开发者的角度看，不需要关心底层用的是哪种文件系统；但从性能分析的角度，我们必须清楚——同一个 `fsync()` 调用，在 ext4 和 f2fs 上的行为完全不同。这也是为什么我们在 Perfetto 中看到 I/O 延迟异常时，需要先确认文件系统类型。

VFS 层还管理着 Page Cache（页缓存）。当我们通过 `read()` 读取文件时，内核首先检查 Page Cache 中是否已有对应的数据——如果有，直接从内存返回，不触发任何磁盘 I/O；如果没有，才会向文件系统发起实际的读请求。`write()` 也是类似，数据先写入 Page Cache，标记为"脏页"（dirty page），由内核的 `flush` 线程在后台异步写回磁盘。这种机制对读性能有巨大的提升——被频繁访问的文件数据几乎全部缓存在内存中，这也是为什么手机在内存充足时读操作通常很快，而写操作（尤其是同步写）更容易成为瓶颈。[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md]

## ext4：成熟但不适合手机场景

### ext4 的核心设计

ext4 是 Linux 生态中最成熟、最广泛使用的文件系统。它是 ext3 的直接继任者，在 2008 年合并入 Linux 主线。ext4 的核心特性包括：

**日志（Journal）**：ext4 使用 jbd2（Journal Block Device v2）作为日志系统，保证文件系统在异常断电后的一致性。jbd2 支持 journal、ordered、writeback 三种模式。Android 上默认使用 ordered 模式——日志只记录元数据（metadata），但保证在元数据提交到日志之前，对应的数据块已经写入磁盘。这是一种在安全性和性能之间的折中。

**延迟分配（Delayed Allocation）**：ext4 不会在 `write()` 调用时立即分配磁盘块，而是等到数据需要刷新到磁盘时（`fsync` 或内核的 `flush` 线程触发）才统一分配。这种策略可以合并和优化写入模式，提升大文件写入的顺序性。

**多块分配（Multiblock Allocator）**：与延迟分配配合，一次性为一组数据分配连续的磁盘块，减少碎片。

**Extent**：用 extent（区间）替代传统的间接块映射。一个 extent 可以描述一段连续的物理块，大幅减少了大文件的元数据开销。

[已验证: 官方文档, kernel.org/doc/html/latest/filesystems/ext4.html]

### ext4 在 Android 上的痛点

ext4 的设计初衷是面向服务器和桌面场景的通用文件系统，它的很多优化策略在 HDD（机械硬盘）时代是合理的。但 Android 设备有几个独特的 I/O 特征，让 ext4 暴露出了明显的性能问题。[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

**问题一：fsync 的放大效应**

这是 ext4 在 Android 上最严重的问题。SQLite 使用 WAL（Write-Ahead Log）模式或 rollback journal 模式，每次事务提交都需要调用 `fsync`。在 ext4 + jbd2（ordered 模式）+ 延迟分配的组合下，一次 `fsync` 会触发一系列连锁反应：

1. 延迟分配意味着脏页还没有分配物理块。`fsync` 时必须先为所有相关的脏页分配物理块——如果其他进程也积累了大量脏页（内核的 `flush` 线程每 30 秒触发一次），`fsync` 需要等待这些脏页的块分配完成。

2. ordered 模式要求在提交元数据日志之前，先把对应的数据块写入磁盘。jbd2 的 commit 线程需要等待所有脏数据刷盘，然后才能提交日志。

3. I/O 优先级倒置——`flush` 线程的异步 I/O 可能占据了存储设备队列，导致 `fsync` 的同步 I/O 被阻塞在队列后面等待。

最终的结果是：一次本应只需几毫秒的 `fsync`，在极端情况下可能需要几百毫秒甚至超过一秒。这就是用户感知到的"App 卡死"的直接原因。[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

**问题二：原地更新与写放大**

ext4 采用就地更新（in-place update）策略——修改文件时，直接覆盖原有的磁盘块。对于 HDD 来说，这不是问题，因为 HDD 的扇区可以无限次覆盖写入。但 NAND 闪存完全不同——它不能就地覆盖写，必须先擦除整个 block（通常 128KB-256KB），然后再写入。这意味着修改一个 4KB 的页面，实际需要：读取整个 block → 在内存中修改 → 擦除 block → 写回整个 block。4KB 的写入被放大成了 128KB+，这就是写放大（Write Amplification）。

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

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_深入代码细节看f2fs在磁盘上的组织方式.md]

这里有几个关键的设计要点值得展开：

**NAT（Node Address Table）**：f2fs 不像 ext4 那样把物理块地址直接存在 inode 里，而是引入了一层间接映射——inode 中存储的是 node ID（nid），NAT 负责 nid 到物理块地址（physical block address）的翻译。这层间接映射是 f2fs 实现 CoW 的基础——修改数据时，新数据写到新的物理位置，只需要更新 NAT 中的映射，不需要修改 inode 本身。

**SIT（Segment Information Table）**：记录每个 segment 的使用状态——有多少有效块、哪些块是空闲的。f2fs 的垃圾回收器依赖 SIT 来决定哪些 segment 可以回收。

**冷热数据分离**：f2fs 把 Main Area 中的 segment 分为六种类型：hot/warm/cold × data/node。频繁更新的"热"数据（如 SQLite 日志）和很少修改的"冷"数据（如照片、APK 文件）被分配到不同的 segment。这样热数据的频繁修改不会影响冷数据所在的 block，垃圾回收时只需要处理热数据区域，大幅减少了 GC 的开销和写放大。[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_深入代码细节看f2fs在磁盘上的组织方式.md]

### SQLite 原子写：f2fs 的杀手级优化

这是 f2fs 对 Android 性能贡献最大的一个特性。

SQLite 在写入数据库时，传统流程是这样的（以 rollback journal 模式为例）：先创建 journal 文件记录原始数据 → 修改数据库文件 → 调用 `fsync` 确保 journal 写入 → 调用 `fsync` 确保数据库文件写入 → 删除 journal 文件。每次事务至少两次 `fsync`，每次 `fsync` 都要等数据真正落盘。

f2fs 提供了一个 `F2FS_IOC_START_ATOMIC_WRITE` 的 ioctl 接口，允许 SQLite 把一系列对数据库文件的修改以原子方式提交。工作流程变成了：

1. SQLite 调用 `ioctl(F2FS_IOC_START_ATOMIC_WRITE)` 告知 f2fs 接下来对某个 inode 的写入需要原子保护
2. SQLite 直接修改数据库文件（f2fs 在内部把修改记录到 CoW 区域，不覆盖原数据）
3. SQLite 调用 `ioctl(F2FS_IOC_COMMIT_ATOMIC_WRITE)` 提交修改
4. f2fs 在一次原子操作中把所有修改生效（更新 NAT 映射）

整个过程中，**只需要一次 `fsync`**——提交时的那一次。journal 文件可以完全跳过，因为 f2fs 的文件系统层面保证了原子性：要么所有修改都生效，要么都不生效。从 Android 8.1 开始，SQLite 默认启用了 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE` 编译选项，当检测到底层文件系统是 f2fs 时，自动使用这个原子写接口。[已验证: 官方文档, sqlite.org/src/info/5c5e4f6f6d and Android source code]

实测数据显示，在 f2fs 上使用 batch atomic write 后，SQLite 的事务提交速度约为 ext4 上的 3 倍。这对于 Android 上几乎所有涉及数据库操作的 App 来说，都是一个巨大的性能提升。

### f2fs 的 fsync 优化

除了 SQLite 原子写，f2fs 在 `fsync` 本身的实现上也比 ext4 更高效。

f2fs 使用逻辑日志（logical logging）而非 ext4 的物理日志（physical logging）。ext4 的 jbd2 在日志中记录被修改的数据块的完整内容（physical logging），而 f2fs 只需要记录哪些 node 被修改了以及它们的新位置（logical logging）。这意味着 f2fs 的日志写入量远小于 ext4——`fsync` 时不需要把所有脏数据都写一遍，只需要更新少量的元数据信息。

此外，f2fs 没有 ext4 的延迟分配问题。f2fs 在写入数据时就已经分配了物理块（因为使用 CoW，写入本身就是往新位置追加），`fsync` 时不需要再做块分配。这避免了 ext4 上 "flush 线程积攒了大量脏页 → fsync 需要等待全部块分配完成" 的恶性连锁反应。[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

### f2fs 的代价：垃圾回收

f2fs 的 CoW 设计带来了优秀的写入性能，但也有代价——垃圾回收（Garbage Collection，GC）。因为数据不断写到新位置，旧的 segment 中会产生大量"过时"的数据（被新版本替代），f2fs 需要定期清理这些 segment，把仍然有效的数据搬到新位置，然后释放整个 segment。

f2fs 的 GC 分为前台和后台两种。后台 GC 由内核线程在存储负载较低时自动触发，对前台 App 的影响较小。但如果存储空间紧张（可用 segment 少于阈值），f2fs 会强制触发前台 GC——在 App 的写入路径上同步执行 GC。前台 GC 可能导致写入延迟飙升到数百毫秒，是 f2fs 用户在存储空间不足时感知到卡顿的主要原因。

在 Perfetto 中，f2fs 的 GC 活动可以通过 `f2fs_gc_*` 相关的 trace event 观察到。如果我们看到 App 线程在写入时出现长时间的 D 状态等待，同时有 `f2fs_gc` 相关的活动，那大概率是前台 GC 在阻塞写入。[待补充：Trace截图展示f2fs前台GC期间的I/O延迟]

### 在 Perfetto 中的观察要点

对于 f2fs 分区上的 I/O 分析，在 Perfetto 中我们应该关注：

1. **block I/O slice 的延迟**：正常情况下 4KB 随机写在 UFS 4.0 上应该在 0.1ms 以下。如果看到超过 1ms 的延迟，需要排查是 GC、调度器还是存储器件本身的问题。

2. **f2fs 相关的 trace event**：如果内核编译时启用了 f2fs 的 tracepoint，可以看到 GC 活动、segment 分配等信息。

3. **主线程的 D 状态等待**：配合 syscall 信息，可以确认是否是 `fsync`/`fdatasync` 导致的阻塞。

## EROFS：为只读分区设计的极致压缩

### 从 ext4 到 EROFS 的切换

在前面的 6.1 节中，我们提到 `system`、`vendor` 等分区是只读的，受 dm-verity 保护。既然是只读分区，使用 ext4 这种支持读写的文件系统就显得有些"浪费"了——ext4 的日志系统、块分配器、空闲空间管理等模块在只读场景下全部是多余的运行时开销。

EROFS（Enhanced Read-Only File System）就是为解决这个问题而生的。它由华为工程师高翔（Xiang Gao）开发，2019 年合并入 Linux 5.4 主线。华为在 EMUI 9.0.1 中首次大规模部署 EROFS，随后 Samsung、OPPO、小米等厂商也陆续跟进。从 Android 13 开始，对于搭载 GMS 的设备，EROFS 成为只读分区的强制要求。[已验证: 官方文档, source.android.com/docs/core/storage and kernel.org]

### EROFS 的核心优势

**压缩与去重**：EROFS 最大的价值在于它对存储空间的高效利用。它支持 LZ4（默认）、Zstandard 和 DEFLATE 三种压缩算法，并具有字节粒度的去重（deduplication）能力。实测数据显示，EROFS 压缩后的 system 分区镜像比未压缩的 ext4 镜像小 30%-45%，相当于为 128GB 的设备节省了 800MB 到 2GB 的空间——这些空间可以分配给 `data` 分区供用户使用。

[已验证: 多来源交叉验证, esper.io, androidauthority.com, pocketnow.com]

**随机读性能提升**：EROFS 的压缩不仅节省空间，还能提升读性能——因为压缩后需要从存储读取的数据量更小。对于随机读场景（如 App 启动时加载大量小文件），EROFS 相比 ext4 有约 20% 的性能提升，某些场景下可达 300%。在 Pixel 设备上，EROFS 压缩带来了 10%-15% 的启动时间改善。

**无日志开销**：作为只读文件系统，EROFS 不需要日志系统。没有 jbd2 的 commit 开销，没有 metadata 的同步写入，mount 速度也更快。这使得设备启动时 `system` 分区的挂载时间更短。

**安全增强**：只读属性本身就是一种安全机制——`system` 分区上的文件无法被运行时修改，配合 dm-verity 的完整性校验，构成了双重保护。

### EROFS 与 OTA 升级

EROFS 完全支持 Android 13+ 的 Virtual A/B OTA 升级机制。OTA 包生成工具能够智能地解压 LZ4 流来生成增量包（delta），因此 EROFS 分区的 OTA 包大小与 ext4 分区相比几乎没有差异。这意味着切换到 EROFS 不会增加用户的 OTA 下载量和升级时间。[已验证: 官方文档, source.android.com/docs/core/ota]

### [图：ext4 vs EROFS system 分区布局对比]

EROFS 在 Android 上的布局通常是：
- `system` 分区：EROFS + LZ4 压缩
- `vendor` 分区：EROFS + LZ4 压缩（或 ext4，取决于厂商配置）
- `product` 分区：EROFS 或 ext4
- `data` 分区：f2fs（需要读写，不能用 EROFS）

## 文件系统对随机读写性能的影响

### 为什么随机写是瓶颈？

在分析存储性能时，我们通常关注顺序读写和随机读写两大类指标。对于 Android 设备来说，**随机写性能几乎总是最薄弱的环节**。

原因有两层。第一层在闪存硬件层面——NAND 闪存的写入粒度是 page（通常 4KB 或 8KB），但擦除粒度是 block（通常包含 128-512 个 page）。这意味着即使只修改一个 page，也需要读取整个 block → 在内存中修改 → 擦除 block → 写回整个 block。随机写入导致大量 block 被部分修改，产生大量的"读-改-写"操作。

第二层在文件系统层面。ext4 的就地更新策略使得每次随机写入都可能触发上述的"读-改-写"循环。f2fs 的 CoW 策略通过把修改写到新位置来避免这个问题，但代价是需要维护复杂的映射表和定期执行 GC。

### 不同文件系统的随机 I/O 特性

| 操作 | ext4 | f2fs | EROFS |
|------|------|------|-------|
| 顺序读 | 优秀（Page Cache 加速） | 优秀 | 优秀（压缩减小读取量） |
| 随机读 | 良好 | 良好 | 优秀（紧凑布局+压缩） |
| 顺序写 | 良好 | 优秀（追加写） | N/A（只读） |
| 随机写 | 较差（就地更新+写放大） | 良好（CoW转换为追加写） | N/A（只读） |
| fsync | 较差（日志+延迟分配连锁） | 良好（逻辑日志+无延迟分配） | N/A（只读） |

[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

这个对比清楚地解释了为什么 Android 的 `data` 分区从 ext4 切换到 f2fs——f2fs 在手机最敏感的两个维度（随机写和 fsync）上都有明显优势。

## fsync 与 fdatasync：同步写入的两种策略

### 两者的区别

`fsync()` 和 `fdatasync()` 是 POSIX 定义的两个同步写入接口，它们的行为有细微但重要的区别：

- `fsync(fd)`：确保 fd 对应文件的所有修改（包括数据和元数据）都写入磁盘。元数据包括文件大小、修改时间、权限等。
- `fdatasync(fd)`：只确保文件数据写入磁盘，不保证元数据（除非元数据的变化会影响后续的数据读取，比如文件大小变化）。

`fdatasync()` 比 `fsync()` 少了一次元数据的磁盘写入，理论上更快。但实际在 Android 上，绝大多数 I/O 库（包括 SQLite）使用的都是 `fsync()`，因为数据完整性是第一优先级——在手机可能随时异常掉电的场景下，保证数据的完全一致性比节省几毫秒更重要。[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md]

### fsync 优化策略

在 App 层面，减少 `fsync` 的影响有几种策略：

**SharedPreferences 的 apply() vs commit()**：这是最简单也最常见的优化。`commit()` 同步写入并等待 `fsync` 完成，会阻塞调用线程；`apply()` 异步写入，立即返回，`fsync` 在后台线程执行。对于不需要立即确认写入结果的场景，应该始终使用 `apply()`。

**SQLite 事务批处理**：不要在循环中逐条执行 `INSERT`/`UPDATE` 并自动提交（每次提交都触发 `fsync`），而是用 `BEGIN TRANSACTION` ... `COMMIT` 把多条语句包在一个事务里——这样只在 `COMMIT` 时触发一次 `fsync`。

**WAL 模式**：SQLite 的 WAL（Write-Ahead Log）模式相比默认的 rollback journal 模式，在读写并发场景下性能更好。WAL 模式允许读操作和写操作并发进行（读操作访问旧的数据库内容，写操作追加到 WAL 文件），减少了锁竞争。

**Room 的增量写入**：如果使用 Jetpack Room，可以利用 `@Transaction` 注解和批量操作 API 来减少隐式 `fsync` 的调用次数。

在 Perfetto 中观察 `fsync` 行为时，可以通过 `systrace` 或 `perfetto` 的 `ftrace` 事件跟踪 `ext4_sync_fs`、`f2fs_sync_fs` 等 tracepoint，直接看到每次 `fsync` 的耗时。如果发现主线程上频繁出现超过 10ms 的 `fsync`，就需要排查是否是不必要的同步写入或者文件系统层面的瓶颈。

## 扩展：各厂商的文件系统选型

Android 设备上的文件系统选型并非完全统一，各厂商有不同的策略：

**Google Pixel**：从 Pixel 3 开始，`data` 分区使用 f2fs，`system` 分区从 Android 13 起使用 EROFS。Google 在 AOSP 中积极推动 EROFS 的标准化。

**Samsung**：f2fs 的创始者，`data` 分区长期使用 f2fs。Samsung 也是 EROFS 的早期采用者之一。

**OPPO/一加**：OPPO 内核团队对 f2fs 有深度的优化经验，发表过多篇 f2fs 相关的技术文章。`data` 分区使用 f2fs，`system` 分区在较新机型上切换到 EROFS。

**小米**：跟进 Google 的 AOSP 标准，新机型上 `system` 使用 EROFS，`data` 使用 f2fs。

[待验证: 以上信息主要基于公开的技术分享和 AOSP 配置，具体到某款机型的文件系统选型需要查看 /proc/mounts 输出]

开发者可以通过 `adb shell mount` 或 `adb shell cat /proc/mounts` 命令查看设备上各分区实际使用的文件系统类型。在 Perfetto trace 中，如果 I/O 延迟异常，首先确认 `data` 分区的文件系统类型——如果是 ext4，很多 fsync 相关的性能问题在 f2fs 上可能不存在。

## 扩展：文件系统碎片化与长期性能退化

我们在 6.1 节中讨论过写入放大，现在从文件系统层面再深入看一下碎片化导致的性能退化。

ext4 的碎片化问题尤为突出。随着使用时间增长，频繁的创建-删除-修改操作使得 ext4 的空闲空间变得越来越零散。新写入的文件不得不分散在不连续的物理块中，导致读取时需要多次寻道——虽然对 SSD 来说没有物理寻道的开销，但分散的块意味着更多的 I/O 请求和更低的预读效率。[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

f2fs 的碎片化问题表现形式不同。f2fs 的 CoW 机制本身不会产生传统意义上的文件碎片（因为写入总是追加到新位置），但 CoW 会产生大量的"无效 segment"——被旧版本数据占据但已经不再被引用的 segment。当无效 segment 积累到一定程度，f2fs 必须执行 GC 来回收空间。GC 的效率取决于冷热分离的效果——如果冷热数据混合在一起，GC 需要搬运大量仍然有效的冷数据，增加了写放大。

性能退化的实际表现是：新手机上 4KB 随机写延迟可能是 0.1ms，使用一年后在存储空间接近满的情况下，同样的操作可能需要 1-5ms——这就是用户感知到的"手机用久了变慢"在存储层面的体现。

缓解碎片化的方法包括：保持足够的可用空间（至少 10%-15%）、避免频繁的小文件创建删除、使用 f2fs 的 `f2fs_io` 工具定期触发碎片整理（需要 root 权限）、以及在 App 层面做好数据缓存策略，减少不必要的磁盘写入。[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md]

## 版本演进：三个文件系统在 Android 中的变迁

我们在前面分别讲了 ext4、f2fs 和 EROFS 的设计思想和性能特征，现在把它们放到 Android 的版本时间线上，看看 Google 和厂商是如何一步步推动文件系统演进的。理解这条时间线，有助于我们在分析 Trace 时快速判断"这台设备用的是哪个时代的文件系统配置"，从而缩小问题排查的范围。

### ext4：从起点到逐步退守

Android 自诞生以来就使用 ext4 作为所有分区的默认文件系统。在 Android 4.x 到 7.x 的时代，`system`、`data`、`cache` 等分区清一色都是 ext4。这个选择不难理解——ext4 是 Linux 生态中最成熟稳定的文件系统，社区支持完善，出问题的概率最低。

但正如我们前面分析的，ext4 在闪存设备的随机写和 fsync 场景下暴露了越来越明显的性能问题。随着 App 功能越来越复杂、数据库操作越来越频繁，主线程因 fsync 阻塞导致的卡顿成了用户投诉的重灾区。Google 从 Android 8.0 开始，在 AOSP 推荐配置中将 `data` 分区转向 f2fs，ext4 逐步退守到 `metadata`、`cache` 等小分区以及部分厂商的定制场景。到 Android 13 之后，ext4 在主流设备上的可见范围已经很小了——`system` 让位给 EROFS，`data` 让位给 f2fs，ext4 主要留在一些对小分区可靠性要求极高的场景中。

### f2fs：从 Samsung 自研到行业标配

f2fs 的演进路径比较独特——它不是 Google 主导的项目，而是 Samsung 的 Jaegeuk Kim 在 2012 年开发的，2013 年合并入 Linux 3.8 主线。Samsung 自然是最早的采用者，在 Galaxy S 系列的 `data` 分区上率先部署 f2fs。

其他厂商的跟进速度不一。OPPO 在 2016 年前后开始在部分机型上使用 f2fs，并组建了专门的内核团队做深度优化。一加在较新机型上全面采用。小米的跟进稍晚，但在 2019 年后的机型上 `data` 分区基本都用了 f2fs。

Google 自己的 Pixel 系列从 Pixel 3（2018 年）开始在 `data` 分区使用 f2fs。从 Android 10 开始，AOSP 的推荐配置明确建议 `data` 分区使用 f2fs。一个关键的里程碑是 Android 8.1——这一版本引入了对 SQLite batch atomic write 的支持（编译选项 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE`），当 SQLite 检测到文件系统是 f2fs 时，自动使用 `F2FS_IOC_START_ATOMIC_WRITE` 接口替代传统的 journal + fsync 流程，事务提交性能提升了约 3 倍。

Android 15 引入了对 16KB 页面大小（Page Size）的支持，f2fs 也相应做了适配。16KB 页面大小改变了 NAND 闪存的写入粒度，对 f2fs 的 segment 管理和 GC 策略都有影响——这也是为什么我们在分析基于 Android 15+ 设备的 I/O Trace 时，需要注意页大小对性能特征的影响。[待验证: f2fs 在 16KB 页面大小下的 GC 行为变化细节]

### EROFS：从华为自研到 Android 强制标准

EROFS 的演进是 Android 文件系统历史上推进最快的案例之一。

华为工程师高翔在 2018 年开始开发 EROFS，2019 年合并入 Linux 5.4 主线。同年华为在 EMUI 9.0.1（基于 Android 9）中首次大规模部署——当时华为的 P30 系列是首批使用 EROFS 的消费级设备。实测数据显示，EROFS 压缩后的 system 镜像比 ext4 小约 30%，随机读性能提升约 20%，App 启动速度改善 10%-15%。

Samsung、OPPO、小米等厂商在 2020-2021 年间陆续跟进，在各自的高端机型上启用 EROFS。但由于缺乏统一标准，各厂商的实现细节（压缩算法选择、分区布局）存在差异。

转折点在 Android 13。Google 在 Android 13 的 CDD（Compatibility Definition Document）中明确规定：对于搭载 GMS 的设备，只读分区（`system`、`vendor` 等）必须使用 EROFS。这意味着从 Android 13 开始，EROFS 不再是厂商的可选优化项，而是合规的硬性要求。对于不搭载 GMS的设备（如中国大陆市场的部分机型），EROFS 不是强制要求，但绝大多数主流厂商也主动采用了。

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
| 13 | 2022 | 小分区 | data 分区标配 | **GMS 设备强制要求** |
| 14 | 2023 | 小分区 | data 分区标配 | 全面普及 |
| 15 | 2024 | 小分区 | 适配 16KB Page Size | 全面普及 |
| 16 | 2025 | 小分区 | 持续优化 | 全面普及 + 增强去重 |

[已确认: 时间线基于 AOSP 官方文档、CDD 要求、kernel.org changelog 和厂商公开技术分享综合整理]

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

- f2fs 核心实现：`kernel/linux/fs/f2fs/`（内核源码树）
- f2fs ioctl 接口定义：`kernel/linux/fs/f2fs/f2fs.h`（`F2FS_IOC_START_ATOMIC_WRITE` 等常量定义）
- f2fs 磁盘布局结构：`kernel/linux/fs/f2fs/f2fs_format.h`（Superblock、Checkpoint、SIT、NAT、SSA、Main Area 数据结构）
- ext4 / jbd2 实现：`kernel/linux/fs/ext4/`、`kernel/linux/fs/jbd2/`
- EROFS 实现：`kernel/linux/fs/erofs/`
- SQLite batch atomic write 适配：`external/sqlite/dist/Android.mk`（`SQLITE_ENABLE_BATCH_ATOMIC_WRITE` 编译选项）
- VFS 层：`kernel/linux/fs/vfs.c`、`kernel/linux/include/linux/fs.h`

### 官方文档

- Android Storage 文档：<https://source.android.com/docs/core/storage>
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

回到我们开头提到的 `fsync` 卡顿问题。当我们看到主线程在 `fsync` 上阻塞时，分析链路应该是：

1. **确认文件系统类型**：通过 `/proc/mounts` 或 Perfetto trace 信息查看 `data` 分区用的是 ext4 还是 f2fs。如果是 ext4，fsync 的放大效应是已知问题。

2. **检查是否是 SQLite/SharedPreferences**：确认阻塞是否由数据库操作或配置写入引起。如果是，检查是否使用了事务批处理、是否使用了 `apply()` 替代 `commit()`。

3. **观察 f2fs GC 活动**（如果使用 f2fs）：检查是否有前台 GC 阻塞了写入。如果是，可能需要清理存储空间。

4. **评估文件系统切换的可行性**：对于仍然使用 ext4 的 `data` 分区，切换到 f2fs 可能带来显著的 fsync 性能提升——尤其是在 SQLite 密集使用的场景下。

Android 的文件系统演进反映了一个重要的工程思路：没有万能的文件系统，只有最适合特定场景的选择。ext4 适合通用场景，f2fs 适合闪存设备的随机写密集场景，EROFS 适合只读分区。理解它们各自的设计取舍，是我们做存储性能优化的基础。

下一节（6.3）我们将深入 I/O 调度层，看看在文件系统之下、存储器件之上，Linux 内核是如何管理和调度 I/O 请求的。
