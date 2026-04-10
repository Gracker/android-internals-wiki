---
title: "Android 存储架构"
chapter: "6.1"
section: "6.1"
status: ready-for-review
applicable_versions: "Android 10+"
last_verified: "2026-04-01"
last_verified_against: "Android 15, JEDEC UFS 4.0 Spec, AOSP source.android.com"
confidence: medium
polish_count: 1
polish_date: "2026-04-06"
polish_by: task2b-polish
sources:
  - "手机Android存储性能优化架构分析（Linux阅码场）"
  - "手机主流存储器件的分析与发展（OPPO内核工匠）"
  - "Android分区挂载原理介绍（OPPO内核工匠）"
tags: ['storage', 'ufs', 'emmc', 'partition', 'scoped-storage', 'fbe', 'f2fs']
related_chapters: ['6.2', '6.3', '4.1', '7.1']
created: 2026-04-01
drafted_date: 2026-04-01
drafted_by: openclaw-task2a
reviewed_date: 2026-04-06
reviewed_by: openclaw-task6
reviewers: []
---

<!-- outline-start -->
- 🔹 Android 存储架构：UFS/eMMC → Block Layer → 文件系统 → Scoped Storage / MediaStore
- 🔹 UFS 3.x/4.0 vs eMMC 的性能差异
- 🔹 分区布局：system、vendor、data、metadata 等分区的作用
- 🔹 Scoped Storage（Android 10+）对 App I/O 行为的影响
- 🔹 FBE（File-Based Encryption）对 I/O 性能的影响
- 🔸 Dynamic Partition 与 Virtual A/B 的存储布局
- 🔸 存储寿命与写入放大（Write Amplification）对性能的长期影响
<!-- outline-end -->

## 从一个卡顿现象说起

我们在 Perfetto 里追踪主线程卡顿的时候，经常会看到一类很典型的场景：用户点击冷启动某个 App，主线程在 `bindApplication` 阶段花了几百毫秒甚至超过一秒。把 trace 展开一看，发现大量时间消耗在 sqlite 的 `fsync` 调用上——那是 SharedPreferences 在做磁盘同步写入。类似的情况还出现在 Activity 切换时读取资源文件、图片解码时从存储加载 bitmap、甚至系统服务在 `data` 分区写日志的瞬间。

这些问题的根源并不在 CPU，而在存储子系统。Android 设备的 I/O 路径从底层存储芯片一直到应用层的文件 API，中间经过了物理层协议、块设备层、I/O 调度器、文件系统、加密层、权限隔离层等多个环节。任何一个环节的瓶颈，最终都会以卡顿的形式暴露到用户体验上。理解这条完整的路径，是做 Android 性能优化的基础——尤其是存储相关的性能问题，往往不会直接在 CPU 火焰图上体现，需要我们具备从 trace 中识别 I/O 等待的能力。

本章我们就沿着数据从闪存芯片到应用程序的完整路径，自底向上拆解 Android 的存储架构。

## 存储栈全景：从闪存芯片到应用 API

Android 的存储栈可以大致分成四层。最底层是物理存储器件，也就是焊在手机主板上的 eMMC 或 UFS 芯片。往上一层是 Linux 内核的块设备层（Block Layer），包括 I/O 调度器和设备映射器（device-mapper）。再往上是文件系统，Android 目前主要使用 ext4 和 f2fs。最顶层则是 Android 框架提供的存储抽象——Scoped Storage、MediaStore、以及各种存储相关的权限和 API。

用一张简化的数据流图来表示：

```
Application (Java/Kotlin)
    ↓  Scoped Storage / MediaStore API
Android Framework (StorageManager, ContentProvider)
    ↓  POSIX file I/O (open/read/write/fsync)
File System (ext4 / f2fs)
    ↓  bio 提交
Block Layer (I/O Scheduler + device-mapper)
    ↓  SCSI / UFS Command
Storage Device (UFS / eMMC)
```

为什么需要这么多层？因为每一层都在解决一个不同的工程问题。物理层解决的是"怎么在硅片上可靠地存储和读取数据"；块设备层解决的是"怎么高效调度并发 I/O 请求"；文件系统解决的是"怎么把数据组织成文件和目录的语义"；而 Android 框架层解决的是"怎么在多应用环境下安全地隔离和管理存储访问"。理解每一层的职责，我们才能在遇到性能问题时精准定位瓶颈所在的层级。

接下来，我们从最底层开始，逐层拆解。

## 物理存储器件：UFS 与 eMMC 的根本差异

### 两种架构的本质区别

eMMC（embedded Multi Media Card）和 UFS（Universal Flash Storage）是 Android 设备上最主流的两种嵌入式存储方案。从外观上看它们都是一颗焊在 PCB 上的 BGA 封装芯片，但内部架构和接口协议完全不同。

eMMC 的本质是一颗并行总线设备。它使用 8 位并行数据线与 SoC 通信，时钟频率最高 200MHz（eMMC 5.1），总线宽度在 DDR 模式下等效于每个时钟周期传输两个数据字。但 eMMC 的工作模式是**半双工**的——读和写不能同时进行，控制器同一时刻只能处理一个命令。这就像一条单车道的桥，虽然路面够宽，但一次只能走一个方向的车。

UFS 则完全不同。它采用差分串行传输，物理层基于 MIPI M-PHY 协议，链路层使用 UniPro，传输层使用 UTP（UFS Transport Protocol），命令集基于 SCSI 的子集 UCS（UFS Command Set）。最关键的是，UFS 是**全双工**的——它有独立的读写通道，可以同时发送和接收数据。而且 UFS 支持命令队列（Command Queue），控制器可以在内部并行处理多个 I/O 命令，对随机 I/O 场景特别有利。[已验证: 来源见 手机主流存储器件的分析与发展（OPPO内核工匠）]

从协议栈的角度看，UFS 的层次结构可以表示为：

```
┌─────────────────────────┐
│     Application Layer    │  ← SCSI Command Set (UCS)
├─────────────────────────┤
│     Transport Layer      │  ← UTP (UFS Transport Protocol)
├─────────────────────────┤
│     Data Link Layer      │  ← UniPro
├─────────────────────────┤
│     Physical Layer       │  ← M-PHY (差分串行)
└─────────────────────────┘
```

### 性能差距有多大？

数字最能说明问题。根据 JEDEC 标准和 Samsung 半导体公开的测试数据：

| 指标 | eMMC 5.1 | UFS 3.1 | UFS 4.0 |
|------|----------|---------|---------|
| 顺序读 | ~330 MB/s | ~2100 MB/s | ~4300 MB/s |
| 顺序写 | ~200 MB/s | ~1200 MB/s | ~2800 MB/s |
| 随机读 (IOPS) | ~12K | ~50K | ~100K+ |
| 随机写 (IOPS) | ~8K | ~50K | ~100K+ |

[已验证: JEDEC标准, Samsung半导体公开数据]

UFS 4.0 的顺序读取速度是 eMMC 5.1 的 13 倍，随机 IOPS 是 8 倍以上。这种差距在实际使用中的体感非常明显——App 安装速度、冷启动时间、大文件拷贝、相机连拍写入速度，都直接受存储器件性能影响。

UFS 4.0 还引入了一个重要的新特性：**MCQ（Multi-Circular Queue，多命令队列）**。在 UFS 3.x 中，虽然支持命令队列，但只有一个硬件队列，所有 I/O 请求排队等待。MCQ 允许 Host 端同时维护多个命令队列，不同优先级或不同类型的 I/O 可以走不同的队列，这与 NVMe 的多队列设计思路一致，在高并发 I/O 场景下能显著降低尾部延迟。[已验证: 来源见 手机主流存储器件的分析与发展（OPPO内核工匠）]

### 怎么用这个知识？

在做性能分析时，如果我们发现 I/O 延迟异常高，首先需要确认设备使用的是什么存储器件。不同档位的手机使用不同规格的存储芯片——旗舰机用 UFS 4.0，中端机可能用 UFS 3.1，入门机可能还在用 eMMC 5.1。同一份代码在不同存储器件上的 I/O 表现可以天差地别。在 Perfetto trace 中，我们可以通过观察 `block` 类别的 slice 来判断 I/O 延迟是否合理——在 UFS 4.0 设备上，4KB 随机读的延迟应该在 0.1ms 以下；如果看到 1ms 以上的延迟，那问题可能不在芯片本身，而在上层的调度或文件系统。[待补充：Trace截图对比不同存储器件上的I/O延迟]

## 块设备层：I/O 调度与设备映射

数据从文件系统出来后，以 `bio`（block I/O）的结构提交给内核的块设备层。这一层主要做两件事：I/O 调度和设备映射。

### I/O 调度器

I/O 调度器负责把文件系统提交的 bio 请求按照一定策略排序和合并，然后发给底层存储设备。Android 设备上通常使用 `mq-deadline` 或 `bfq` 调度器。`mq-deadline` 的核心思路是为每个 I/O 请求设置一个截止时间，在截止时间之前尽量合并和排序请求以提高吞吐量，超过截止时间则强制发出，避免饿死。`bfq` 则更注重公平性，会按照进程（cgroup）分配 I/O 带宽，防止后台进程抢占前台 App 的 I/O 资源。

手机场景下，I/O 调度的挑战在于：前台 App（比如用户正在滑动的列表）需要低延迟的随机读，而后台任务（比如系统更新、媒体扫描）在进行大量顺序写。如果调度器不给力，后台的顺序写就会把前台的随机读挤到队列后面，造成卡顿。这也是为什么 Android 引入了 `cgroup` v2 的 I/O 控制器——前台 App 的 I/O 请求会被标记为更高的优先级。[已验证: 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

### device-mapper：虚拟块设备的瑞士军刀

device-mapper（dm）是 Linux 内核提供的一个通用框架，它可以把一个或多个物理块设备"映射"成一个新的虚拟块设备。Android 大量使用了 device-mapper 来实现分区管理、完整性校验和加密等功能。

device-mapper 的工作基于三个概念：

1. **映射设备（Mapped Device）**：对上层可见的虚拟块设备，比如 `/dev/block/dm-0`
2. **映射表（Mapping Table）**：定义虚拟设备的每个扇区范围对应哪个底层设备的哪些扇区
3. **目标设备（Target Device）**：映射表指向的底层设备

[已验证: 来源见 Android分区挂载原理介绍（OPPO内核工匠）]

在 Android 中，几个关键的 dm 目标类型包括：

- **dm-linear**：线性映射，把一个连续的扇区范围映射到另一个设备的连续扇区。这是 Dynamic Partition 的基础——`system`、`vendor` 等分区实际上是通过 dm-linear 从一个名为 `super` 的大物理分区中"切"出来的逻辑分区。
- **dm-verity**：完整性校验，通过预先计算的哈希树（hash tree）验证只读分区（如 `system`）的数据没有被篡改。
- **dm-snapshot**：快照设备，用于 Virtual A/B 升级，在升级过程中通过 Copy-on-Write（COW）设备记录变更。
- **dm-default-key**：元数据加密，对 `data` 分区进行块级加密。

这些 dm 目标层层叠加，最终形成了 Android 的分区布局——我们接下来要拆解的，就是这些分区各自承担什么职责、怎么挂载、对性能有什么影响。

## 分区布局：system、vendor、data 与 metadata

### 传统分区 vs Dynamic Partition

早期的 Android 使用固定大小的分区。`system`、`vendor`、`cache` 等分区在出厂时就确定了大小，写入分区表后不再改变。这种方式的问题在于灵活性差——如果 `system` 分区用完了而 `vendor` 还有空余，无法动态调整。

从 Android 10 开始，Google 引入了 **Dynamic Partition（动态分区）**。所有只读的 A/B 分区（`system`、`vendor`、`product`、`odm` 等）被合并到一个名为 `super` 的大物理分区中，然后通过 dm-linear 在运行时动态划分出逻辑分区。[已验证: 官方文档, source.android.com/docs/core/storage]

```
Physical Partition: super
┌──────────┬──────────┬──────────┬──────────┐
│  system  │  vendor  │ product  │   odm    │
│ (logical)│ (logical)│ (logical)│ (logical)│
└──────────┴──────────┴──────────┴──────────┘
         mapped via dm-linear
```

这意味着在 OTA 升级时，可以动态调整各逻辑分区的大小，不再受制于固定分区表的约束。

### 各分区的职责

**system 分区**：包含 Android 框架和系统应用的代码。从 Android 8.0 开始采用 system-as-root 模式，`system` 分区直接作为根文件系统挂载。它是只读的，通过 dm-verity 保证完整性。任何对 `system` 分区的修改都会导致 dm-verity 校验失败，设备启动时会拒绝启动或进入恢复模式。

**vendor 分区**：包含硬件抽象层（HAL）驱动、固件和厂商定制配置。这个分区的存在是 Project Treble 架构的核心——把 vendor 实现和 Android 框架解耦，使得框架可以独立升级而不需要等厂商适配。vendor 分区同样是只读的，受 dm-verity 保护。

**data 分区**：这是唯一的大容量可写分区，承载了几乎所有用户数据——安装的 App（`/data/app/`）、App 私有数据（`/data/data/`）、媒体文件（`/data/media/`）、系统数据库（如 `settings.db`）等。data 分区使用文件级加密（FBE），是性能优化的重点关注对象，因为几乎所有涉及持久化的 I/O 操作都发生在这里。

**metadata 分区**：一个很小的分区（通常 16MB 左右），专门用于存储元数据加密的密钥信息。它在启动早期就需要被解密和挂载，因为后续的 FBE 加密依赖它提供的信息。[已验证: 官方文档, source.android.com/docs/core/storage]

### 挂载流程：从 bootloader 到用户空间

Android 的分区挂载是一个分阶段的过程。Bootloader 完成硬件初始化后，首先挂载 `super` 物理分区，通过 dm-linear 激活 `system`、`vendor` 等逻辑分区。`system` 分区作为 rootfs 挂载后，init 进程启动，开始挂载 `vendor`、`product` 等其他分区。接着，`vold`（Volume Daemon）负责挂载 `data` 分区——这里涉及 FBE 解密、dm-default-key 配置等复杂流程。整个挂载流程中任何一环出错，都会导致设备无法正常启动。[已验证: 来源见 Android分区挂载原理介绍（OPPO内核工匠）]

## 文件系统：从 ext4 到 f2fs 的演进

### ext4 在 Android 上的问题

Android 早期使用 ext4 作为主要文件系统，这在服务器和桌面 Linux 上是成熟可靠的选择，但在手机场景下暴露出了一些问题。

手机存储的 I/O 特性与服务器完全不同。根据 Linux 阅码场的分析，手机存储 I/O 有几个典型特征：以 buffer I/O 为主（数据先写入 page cache，由内核回写），sqlite 频繁进行小量同步随机写（通过 `fsync`），存储芯片速度相对较低，设备会频繁异常掉电（手机没电直接关机），以及存储碎片化严重。

其中 sqlite 的 `fsync` 问题是 ext4 在 Android 上最棘手的问题。sqlite 使用 WAL（Write-Ahead Log）模式，每次事务提交都需要调用 `fsync` 确保日志写入磁盘。在 ext4 上，`fsync` 的实现涉及 jbd2（ext4 的日志系统）的 order 模式——为了保证数据一致性，`fsync` 不仅需要刷新日志，还要把所有相关的脏页都写到磁盘。更糟糕的是，ext4 的延迟分配（delayed allocation）机制会推迟分配物理块，等到 `fsync` 时才统一分配，这进一步拉长了 `fsync` 的耗时。再加上 I/O 优先级倒置的问题——低优先级的后台 I/O 可能占据了存储设备的队列，导致高优先级的 `fsync` 被阻塞——最终的结果就是用户感知到的卡顿。[已验证: 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

### f2fs：为闪存优化的文件系统

为了解决这些问题，Android 逐步将 `data` 分区切换到 f2fs（Flash-Friendly File System）。f2fs 由 Samsung 开发，专门针对 NAND 闪存的特性设计，它的核心思路是把随机写转换为顺序写。

f2fs 的关键优化包括：

**Copy-on-Write（CoW）**：f2fs 不会就地覆盖数据，而是把修改后的数据写到新的位置，然后更新指向它的指针。这避免了闪存的"擦除-重写"开销，因为闪存的最小擦除单位（通常是 128KB 或 256KB 的 block）远大于最小写入单位（4KB 的 page）。就地覆盖意味着即使只修改 4KB 数据，也需要先擦除整个 block 再重写，而 CoW 只需要把新数据写到空闲空间。

**冷热数据分离**：f2fs 会根据数据的更新频率把它们分成"热"、"温"、"冷"三类。频繁更新的数据（如 sqlite 日志）放在一起，很少修改的数据（如照片）放在另一块区域。这样热数据的频繁更新不会影响冷数据所在的 block，减少了垃圾回收（GC）的开销和写入放大。

**sqlite 原子写优化**：这是一个非常精巧的优化。sqlite 在写入数据库时，通常需要先写日志（WAL 或 rollback journal），再写数据库文件，每步都需要 `fsync`。f2fs 提供了一个 `atomic_write` 的 ioctl 接口，允许 sqlite 把对数据库文件的修改以原子方式提交——文件系统层面保证了要么所有修改都生效，要么都不生效。这样 sqlite 可以跳过写日志的步骤，直接修改数据库文件并原子提交，将两次 `fsync` 减少到一次。[已验证: 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

在 Perfetto 中，如果我们在 `data` 分区上观察到大量的 `fsync` 延迟，可以检查文件系统类型——如果是 ext4，可以考虑切换到 f2fs；如果已经是 f2fs，可能需要检查是否有大量碎片或者 GC 活动。f2fs 的 GC 通常在后台进行，但如果存储空间紧张，前台 I/O 可能被 GC 阻塞，表现为间歇性的 I/O 延迟飙升。[待补充：Trace截图展示f2fs GC期间I/O延迟的变化]

## Scoped Storage：存储权限的革命

### 为什么需要 Scoped Storage

Android 10 之前，App 只要获得了 `READ_EXTERNAL_STORAGE` 或 `WRITE_EXTERNAL_STORAGE` 权限，就可以读写共享存储（`/sdcard`）上的所有文件。这意味着一个手电筒 App 理论上可以读取用户的照片、文档、下载的所有内容。这种粗粒度的权限模型在隐私安全上存在明显隐患。

从 Android 10 开始引入的 Scoped Storage（分区存储），从根本上改变了 App 访问共享存储的方式。Android 11 起强制执行。核心变化包括：

1. App 只能直接访问自己的专属目录（`Android/data/<package_name>/` 和 `Android/media/<package_name>/`），不需要任何权限
2. 要访问其他 App 创建的媒体文件，需要通过 MediaStore API 并获得相应权限
3. 要访问非媒体文件（如 PDF、文档），需要通过 Storage Access Framework（SAF）让用户手动选择
4. `/sdcard` 根目录不再对 App 直接可写

[已验证: 官方文档, developer.android.com/about/versions/11/privacy/storage]

### FUSE 层的性能开销

Scoped Storage 的实现依赖 FUSE（Filesystem in Userspace）。当 App 通过传统文件路径（如 `/sdcard/DCIM/`）访问文件时，请求会经过一层 FUSE 代理——内核把文件操作转发给用户空间的 FUSE 守护进程处理，FUSE 守护进程再检查 App 的权限后执行实际的文件操作。

这个 FUSE 代理层引入了显著的性能开销。每一次文件操作都需要在内核空间和用户空间之间进行上下文切换，涉及多次数据拷贝。在 Android 10 的早期实现中，通过 FUSE 访问文件的延迟比直接访问高 2-5 倍。这对媒体密集型 App（如图片浏览器、音乐播放器）的影响尤为明显。

为了缓解这个问题，Android 提供了 MediaStore API 的直接访问模式。当 App 通过 MediaStore 的 `ContentResolver` 查询并打开媒体文件时，系统可以绕过 FUSE 层，直接通过底层的文件描述符访问文件。这种非 FUSE 路径的性能接近原生文件 I/O。Android 15 进一步优化了 MediaStore 的批量查询性能，减少了大量文件枚举时的开销。[已验证: 官方文档, developer.android.com/training/data-storage/shared/media]

### 对 App I/O 行为的实际影响

Scoped Storage 对 App 开发和性能优化有几个直接的影响：

**迁移到 MediaStore API**：如果 App 需要访问共享存储中的媒体文件，应该使用 MediaStore API 而不是直接文件路径。这不仅是权限要求，也是性能优化的要求——MediaStore 的非 FUSE 路径更快。

**批量操作的优化**：大量文件操作（如扫描整个目录）在 FUSE 层的开销会被放大。如果 App 有这种需求，应该考虑使用 MediaStore 的批量查询接口。

**应用专属目录的使用**：App 专属目录（`Android/data/<pkg>/`）不需要任何权限，也不经过 FUSE 层，性能最好。如果数据只在 App 内部使用，应该优先放在这里。

在 Perfetto trace 中，FUSE 相关的开销通常表现为 `fuse` 进程的 CPU 活动和额外的 I/O 等待。如果我们看到 App 线程在文件 I/O 上等待，同时 `fuse` 进程在占用 CPU，那很可能是 Scoped Storage 的 FUSE 开销。[待补充：Trace截图展示FUSE层引入的额外延迟]

## FBE：文件级加密的存储影响

### 从全盘加密到文件级加密

Android 的存储加密经历了从全盘加密（Full-Disk Encryption，FDE）到文件级加密（File-Based Encryption，FBE）的演进。FDE 对整个 `data` 分区使用同一个密钥加密，用户解锁手机后才解密整个分区。FBE 则不同，它为每个文件独立加密，并引入了 DE（Device Encrypted）和 CE（Credential Encrypted）两种密钥。

**DE 密钥**（Device Encrypted Key）：绑定到硬件，不依赖用户凭据（PIN/密码/图案）。设备启动后即可使用 DE 密钥解密对应的文件。这使得闹钟、通知、电话等功能在用户解锁手机之前就能正常工作——这就是 Direct Boot 特性。

**CE 密钥**（Credential Encrypted Key）：绑定到用户凭据，只有用户解锁手机后才能获取。绝大多数用户数据（App 数据、照片等）使用 CE 密钥加密。

从 Android 10 开始，FBE 对所有新设备是强制要求的。[已验证: 官方文档, source.android.com/docs/security/features/encryption/file-based]

### 加密的 I/O 性能影响

加密操作不可避免地会引入额外的计算开销，但现代 Android 设备上这个开销已经很小了。关键在于**硬件加速**。

主流 SoC 都集成了专用的加密引擎（inline encryption hardware），它位于存储控制器和闪存芯片之间。数据在写入闪存之前由硬件加密引擎自动加密，读取时自动解密。整个过程对 CPU 透明——CPU 写入的是明文数据，从存储读取到的也是明文数据，加密解密在 DMA 传输过程中完成。这种 inline encryption 的方式使得加密的性能开销几乎可以忽略不计。[已验证: 官方文档, source.android.com/docs/security/features/encryption/file-based]

在 Perfetto trace 中，我们通常不需要单独关注 FBE 的性能开销。但如果在低端设备上观察到加密相关的 CPU 活动，可以检查 SoC 是否支持 inline encryption——如果不支持，FBE 会回退到软件加密实现，这时 CPU 开销会比较明显。

### FBE 的密钥层次

FBE 的密钥管理由 `vold`（Volume Daemon）负责。整个密钥层次如下：

1. **System DE Key**：系统级 DE 密钥，在启动早期由硬件生成。用于 `/data/system/`、`/data/misc/` 等系统目录。
2. **User DE Key**：每个用户的 DE 密钥，用于该用户的 Direct Boot 相关数据（如闹钟设置）。
3. **User CE Key**：每个用户的 CE 密钥，用户解锁后由凭据派生。用于绝大多数 App 数据。

```cpp
// vold 中的密钥安装（简化示意）
// System DE Key
installKey("scrypt_key_system_de", "/data/system_de/");
// User DE Key (per user)
installKey("scrypt_key_user_de_0", "/data/user_de/0/");
// User CE Key (after unlock)
installKey("scrypt_key_user_ce_0", "/data/user/0/");
```

[已验证: 来源见 Android分区挂载原理介绍（OPPO内核工匠）]

每个目录的加密策略由扩展属性（xattr）记录在文件系统的 inode 中。当创建新文件时，文件系统会继承父目录的加密策略，自动使用对应的密钥加密。

## Dynamic Partition 与 Virtual A/B 的存储布局

前面提到 Dynamic Partition 通过 `super` 物理分区和 dm-linear 实现了灵活的逻辑分区布局。但 Dynamic Partition 只是存储布局演进的一半，另一半是 **Virtual A/B（VABC）**——它解决了 OTA 升级时如何安全地更新这些分区的问题。

传统的 A/B 分区方案为每个分区维护两套完整的副本（slot A 和 slot B），占用双倍的存储空间。Virtual A/B 在此基础上做了优化：它不再为每个只读分区维护完整副本，而是利用 dm-snapshot（COW 设备）只记录升级过程中的变更。具体来说，升级时系统会创建一个 COW 设备，在 `super` 分区中分配空间。新版本的分区数据写入 COW 区域，旧版本的数据保持不变。如果升级成功，COW 中的数据被合并为正式数据；如果升级失败，系统可以回退到旧版本——只需要丢弃 COW 设备即可。

```
Virtual A/B 升级流程：

super 分区布局（升级中）：
┌──────────────┬──────────┬────────────┐
│  当前 slot A  │  COW 区域 │  空闲空间   │
│(system/vendor)│(变更记录) │            │
└──────────────┴──────────┴────────────┘

升级成功 → COW 合并到正式分区
升级失败 → 丢弃 COW，继续用 slot A
```

这个设计的巧妙之处在于，COW 区域只需要存储新旧版本之间的差异，而不是完整的分区副本。这大幅减少了 OTA 升级所需的额外存储空间。但代价是升级期间的写入性能会受到影响——每次写入都需要先复制旧数据到 COW 设备，再写入新数据，实际上每次写入变成了两次 I/O。[已验证: 来源见 Android分区挂载原理介绍（OPPO内核工匠）]

在 Perfetto trace 中，如果设备正在进行或刚完成 OTA 升级，我们可能会观察到 `data` 分区或 `super` 分区上有异常的 I/O 活动——那就是 COW 合并过程。合并通常在后台进行，但如果设备存储空间紧张，合并过程可能持续较长时间并影响前台 App 的 I/O 性能。[待补充：Trace截图展示OTA合并期间的I/O特征]

## 存储寿命与写入放大

NAND 闪存有一个物理限制：每个存储单元的擦写次数是有限的。SLC（单层单元）可以承受约 10 万次擦写，MLC（多层单元）约 3000-10000 次，TLC（三层单元）约 1000-3000 次，而现代高密度 QLC（四层单元）只有几百次。手机上使用的主要是 TLC 或混合 SLC/TLC 方案。

这个物理限制催生了一个重要的性能概念：**写入放大（Write Amplification Factor，WAF）**。写入放大的含义是，实际写入闪存的数据量大于主机请求写入的数据量。例如，App 只想写 4KB 的数据，但闪存控制器可能需要先读取一个 128KB 的 block，修改其中的 4KB，擦除整个 block，再写回 128KB——这样 4KB 的写入变成了 128KB 的实际写入，WAF = 32。

写入放大的来源有几个：

- **垃圾回收（GC）**：闪存不能就地覆盖写，必须先擦除再写。当空闲 block 不足时，控制器需要把仍有效的数据从一个 block 搬到另一个 block，然后擦除旧 block。这些"搬家"操作产生了额外的写入。
- **磨损均衡（Wear Leveling）**：控制器会尽量让所有 block 的擦写次数均匀分布，避免某些 block 过早失效。这可能导致数据被频繁搬运。
- **文件系统层面的碎片**：即使 App 顺序写数据，经过文件系统的分配策略和闪存内部的地址映射，实际写入模式可能变得非常随机。

写入放大是一个长期累积效应。新手机上存储空间充裕，GC 压力小，WAF 接近 1。但随着使用时间增长，存储碎片化加剧，可用空间减少，GC 频率上升，WAF 逐渐增大。这就是为什么很多用户感觉"手机用了一年之后变慢了"——存储性能的退化是真实存在的，不是心理作用。

从性能优化的角度，减少写入放大最有效的方法是**减少不必要的写入**。这包括：避免频繁的小量同步写入（如 SharedPreferences 的 `apply()` 替代 `commit()`）、使用 f2fs 的 CoW 机制减少就地更新、以及在 App 层面做好数据缓存策略，避免每次操作都触发磁盘写入。[已验证: 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

## 常见问题与误区

**「手机变慢是因为闪存老化了吗？」**

不完全是。闪存确实有擦写寿命，但正常使用条件下（每天写入 10-20GB），TLC 闪存的寿命在 3-5 年内不太可能耗尽。手机长期使用后变慢，更主要的原因是存储碎片化导致的 GC 频率上升、App 数据量增长导致的 I/O 增多、以及系统更新后新版本对存储性能的更高要求。存储器件本身的性能退化只贡献了一小部分。

**「f2fs 一定比 ext4 快吗？」**

不一定。f2fs 在随机写密集的场景（如大量 sqlite 操作）下有明显优势，但在大文件顺序读写的场景下，两者的差距不大。而且 f2fs 的 GC 机制在存储空间紧张时可能引入不可预测的延迟抖动。如果设备存储空间长期保持在 80% 以下，f2fs 的优势比较稳定；但如果经常接近满载，f2fs 的性能退化反而可能比 ext4 更剧烈。

**「FBE 加密会拖慢存储性能吗？」**

在有 inline encryption 硬件支持的设备上（2018 年后的主流 SoC），FBE 的性能开销可以忽略。加密解密在 DMA 传输路径上由硬件完成，CPU 感知不到。但在没有硬件加密引擎的低端设备上，FBE 回退到软件实现，可能引入 5-15% 的 I/O 延迟增加。在做性能分析时，如果怀疑 FBE 是瓶颈，可以检查 `[待补充：sysfs 加密统计路径]` 下对应分区的加密统计信息。

## 小结：从存储架构到性能分析

让我们回到开头的那个卡顿场景。当我们看到主线程在 `fsync` 上等待时，完整的分析流程应该是：

1. **物理层**：确认设备使用的是 UFS 还是 eMMC——这决定了 I/O 延迟的基线
2. **块设备层**：检查 I/O 调度器配置和 cgroup I/O 优先级——是否有后台任务抢占了前台的 I/O 带宽
3. **文件系统层**：确认使用的是 ext4 还是 f2fs——ext4 的 `fsync` 在 Android 场景下有已知的性能问题
4. **加密层**：确认 FBE 是否使用硬件加速——软件加密在低端设备上可能成为瓶颈
5. **权限层**：如果涉及共享存储访问，检查是否走了 FUSE 路径——FUSE 的上下文切换开销可能显著增加 I/O 延迟

理解了存储栈的每一层，我们就能从 Perfetto trace 中的 I/O 等待信号，逐层追踪到根因，而不是停留在"主线程被 I/O 阻塞了"这个表面结论上。

存储架构的知识还将在后续章节中持续用到——第 6.2 节我们会深入文件系统的选择与调优，第 6.3 节会讨论 I/O 调度的具体策略，而存储性能的长期退化问题则与第 7 章流畅性优化中的"老设备卡顿"现象直接相关。

## 参考资料

- **手机 Android 存储性能优化架构分析** — Linux 阅码场，系统梳理了 Android 存储 I/O 路径和 ext4/f2fs 的性能差异
- **手机主流存储器件的分析与发展** — OPPO 内核工匠，eMMC/UFS 架构对比与 UFS 4.0 MCQ 特性详解
- **Android 分区挂载原理介绍** — OPPO 内核工匠，Dynamic Partition、dm-linear、FBE 密钥层次
- **Android Storage | Android Open Source Project** — source.android.com/docs/core/storage，官方分区与加密文档
- **Scoped Storage | Android Developers** — developer.android.com/about/versions/11/privacy/storage，分区存储 API 与权限模型
- **JEDEC UFS 4.0 Standard (JESD220E)** — UFS 4.0 规范，MCQ 多命令队列定义

