---
title: "Android 存储架构"
chapter: "6.1"
section: "6.1"
status: ready-for-review
applicable_versions: "Android 9 - Android 16"
last_verified: "2026-04-14"
last_verified_against: "Android 16, AOSP dynamic partitions / metadata encryption / system-as-root docs, Android 11 shared storage docs, SQLite compile & WAL docs"
confidence: medium
polish_count: 1
polish_date: "2026-04-06"
polish_by: task2b-polish
sources:
  - "手机Android存储性能优化架构分析（Linux阅码场）"
  - "手机主流存储器件的分析与发展（OPPO内核工匠）"
  - "Android分区挂载原理介绍（OPPO内核工匠）"
  - "Android Storage | Android Open Source Project"
  - "Scoped Storage | Android Developers"
  - "Access media files from shared storage | Android Developers"
  - "File-based encryption | Android Open Source Project"
  - "Metadata encryption | Android Open Source Project"
  - "System-as-root | Android Open Source Project"
  - "Implement dynamic partitions | Android Open Source Project"
  - "SQLite Compile-time Options / WAL | sqlite.org"
  - "JEDEC UFS 4.0 Standard (JESD220E)"
tags: ['storage', 'ufs', 'emmc', 'partition', 'scoped-storage', 'mediastore', 'fuse', 'fbe', 'dynamic-partition', 'virtual-ab', 'f2fs']
related_chapters: ['6.2', '6.3', '4.1', '7.1']
created: 2026-04-01
drafted_date: 2026-04-01
drafted_by: openclaw-task2a
reviewed_date: 2026-06-15
task6_reviewed_date: "2026-06-15"
last_task6_audit: 2026-06-09
reviewed_by: openclaw-task6
task6_result: pass-light-edit
reviewers: []
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task9_result: pending-review
task2b_result: fixed
task2b_state: fixed
task9_reviewed_date: "2026-06-03"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-03T02:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-03-02-deep-review.md"
last_task9_audit: "2026-06-15"
last_task9_audit_at: "2026-06-15T16:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-15-16-audit.md"
task9_review_notes: "2026-06-15 Task9 闲时抽检：发现 P1 版本差异，Virtual A/B / VABC 小节仍按 dm-snapshot + super COW 统一模型描述，未区分 Android 11 / 12 / 13+ snapshot 与 snapuserd 边界；已写入 queue，回到 Task2B。"

last_task2b_at: "2026-06-15T16:52:36+08:00"
last_task9_autofix_at: "2026-06-02"
last_task6_at: "2026-06-15T17:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-15-17-review.md"
task6_review_notes: "2026-06-15 17:10 Task6 revisiting-review（Task2B 修复后）：Virtual A/B 版本拆分（Android 11/12+/13+）写作质量良好，逻辑清晰；L1 小修 1 处（第一人称「我更建议」→「建议」）；outline 7/7 覆盖；无新增 L3/L4 回炉项。Task2B 已修复 Task9 P1（版本差异），送 Task9 复核。"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_new_rework: false
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-03
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

我们在 Perfetto 里追踪主线程卡顿的时候，经常会看到一类很典型的场景：用户点击冷启动某个 App，主线程在 `bindApplication` 阶段花了几百毫秒甚至超过一秒。把 Trace 展开一看，发现大量时间消耗在 SQLite 的 `fsync` 调用上——那是 SharedPreferences 在做磁盘同步写入。类似的情况还出现在 Activity 切换时读取资源文件、图片解码时从存储加载 bitmap、甚至系统服务在 `data` 分区写日志的瞬间。

这些问题的根源并不在 CPU，而在存储子系统。Android 设备的 I/O 路径从底层存储芯片一直到应用层的文件 API，中间经过了物理层协议、块设备层、I/O 调度器、文件系统、加密层、权限隔离层等多个环节。任何一个环节的瓶颈，最终都会以卡顿的形式暴露到用户体验上。理解这条完整的路径，是做 Android 性能优化的基础——尤其是存储相关的性能问题，往往不会直接在 CPU 火焰图上体现，需要我们具备从 Trace 中识别 I/O 等待的能力。

本章沿着数据从闪存芯片到应用程序的完整路径，自底向上梳理 Android 的存储架构。

## 存储栈全景：从闪存芯片到应用 API

Android 的存储栈可以大致分成四层。最底层是物理存储器件，也就是焊在手机主板上的 eMMC 或 UFS 芯片。往上一层是 Linux 内核的块设备层（Block Layer），包括 I/O 调度器和设备映射器（device-mapper）。再往上是文件系统，Android 目前主要使用 ext4 和 f2fs。最顶层则是 Android 框架提供的存储抽象——Scoped Storage、MediaStore、以及各种存储相关的权限和 API。

用一张简化的数据流图来表示：

```text
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

这么多层的存在，不是架构上的过度设计。每一层处理一个独立的工程问题：物理层解决"怎么在硅片上可靠地存储和读取数据"；块设备层解决"怎么高效调度并发 I/O 请求"；文件系统解决"怎么把数据组织成文件和目录的语义"；Android 框架层解决"怎么在多应用环境下安全地隔离和管理存储访问"。只有理解每一层的职责，才能在遇到性能问题时精准定位瓶颈所在。

先看最底层的物理存储器件。

## 物理存储器件：UFS 与 eMMC 的根本差异

### 两种架构的本质区别

eMMC（embedded Multi Media Card）和 UFS（Universal Flash Storage）是 Android 设备上最主流的两种嵌入式存储方案。从外观上看它们都是一颗焊在 PCB 上的 BGA 封装芯片，但内部架构和接口协议完全不同。

eMMC 的本质是一颗并行总线设备。它使用 8 位并行数据线与 SoC 通信，时钟频率最高 200MHz（eMMC 5.1），总线宽度在 DDR 模式下等效于每个时钟周期传输两个数据字。但 eMMC 的工作模式是**半双工**的——读和写不能同时进行，控制器同一时刻只能处理一个命令。这就像一条单车道的桥，虽然路面够宽，但一次只能走一个方向的车。

UFS 则完全不同。它采用差分串行传输，物理层基于 MIPI M-PHY 协议，链路层使用 UniPro，传输层使用 UTP（UFS Transport Protocol），命令集基于 SCSI 的子集 UCS（UFS Command Set）。最关键的是，UFS 是**全双工**的——它有独立的读写通道，可以同时发送和接收数据。而且 UFS 支持命令队列（Command Queue），控制器可以在内部并行处理多个 I/O 命令，对随机 I/O 场景特别有利。[已验证: 来源见 手机主流存储器件的分析与发展（OPPO内核工匠）]

从协议栈的角度看，UFS 的层次结构可以表示为：

```text
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

来看实际数据。以下基于 JEDEC 标准和 Samsung 半导体公开的测试数据：

| 指标 | eMMC 5.1 | UFS 3.1 | UFS 4.0 |
|------|----------|---------|---------|
| 顺序读 | ~330 MB/s | ~2100 MB/s | ~4300 MB/s |
| 顺序写 | ~200 MB/s | ~1200 MB/s | ~2800 MB/s |
| 随机读 (IOPS) | ~12K | ~50K | ~100K+ |
| 随机写 (IOPS) | ~8K | ~50K | ~100K+ |

[已验证: JEDEC 标准，Samsung 半导体公开数据]

UFS 4.0 的顺序读取速度是 eMMC 5.1 的 13 倍，随机 IOPS 是 8 倍以上。这种差距会直接体现在 App 安装速度、冷启动时间、大文件拷贝和相机连拍写入速度上。

UFS 4.0 还引入了 **MCQ（Multi-Circular Queue，多命令队列）**。在 UFS 3.x 中，虽然支持命令队列，但只有一个硬件队列，所有 I/O 请求排队等待。MCQ 允许 Host 端同时维护多个命令队列，不同优先级或不同类型的 I/O 可以走不同的队列，这与 NVMe 的多队列设计思路一致，在高并发 I/O 场景下可以降低尾部延迟。[已验证: 来源见 手机主流存储器件的分析与发展（OPPO内核工匠）]

### 怎么用这个知识？

在做性能分析时，如果我们发现 I/O 延迟异常高，先要确认设备使用的是什么存储器件。不同档位的手机使用不同规格的存储芯片，旗舰机常见 UFS 4.0，中端机可能是 UFS 3.1，入门机还可能停留在 eMMC 5.1。同一份代码在这些器件上的 I/O 基线差异很大，所以判断 Trace 之前先要知道设备档位。在 Perfetto 里，可以把 `block` 相关 slice 和设备规格一起看。UFS 4.0 的随机读基线通常会明显短于 eMMC 5.1；如果高端设备上已经接近毫秒级延迟，问题往往不只在芯片本身，还要继续往调度器、文件系统和后台写入看。[图：不同存储器件上的 I/O 延迟基线对比。至少放一组 UFS 4.0 与 eMMC 5.1 的 `block` slice，对比同样 4 KB 随机读请求的完成时间。]

## 块设备层：I/O 调度与设备映射

数据从文件系统出来后，以 `bio`（block I/O）的结构提交给内核的块设备层。这一层主要做两件事：I/O 调度和设备映射。

### I/O 调度器

I/O 调度器负责把文件系统提交的 bio 请求按照一定策略排序和合并，然后发给底层存储设备。Android 设备上通常使用 `mq-deadline` 或 `bfq` 调度器。`mq-deadline` 的核心思路是为每个 I/O 请求设置一个截止时间，在截止时间之前尽量合并和排序请求以提高吞吐量，超过截止时间则强制发出，避免饿死。`bfq` 则更注重公平性，会按照进程（cgroup）分配 I/O 带宽，防止后台进程抢占前台 App 的 I/O 资源。

手机场景下，I/O 调度的挑战在于：前台 App（比如用户正在滑动的列表）需要低延迟的随机读，而后台任务（比如系统更新、媒体扫描）在进行大量顺序写。如果调度器不给力，后台的顺序写就会把前台的随机读挤到队列后面，造成卡顿。这也是为什么 Android 通过 task profiles 抽象调度组来实现前后台 I/O 隔离。AOSP android-15/16 的 `cgroups.json` 默认仍挂载 `blkio` 控制器在 `/dev/blkio`；`task_profiles.json` 中 `LowIoPriority` 加入 `blkio/background`，`SCHED_SP_FOREGROUND` / `SCHED_SP_TOP_APP` 聚合 `HighIoPriority` / `MaxIoPriority`。前后台 I/O 隔离效果取决于 kernel、active scheduler、blkio/BFQ 支持和 OEM 配置。cgroup v2 io controller 目前只能作为厂商/内核可选实现，可用 `/proc/cgroups`、`/sys/fs/cgroup`、`/dev/blkio` 确认设备实际配置。[已验证: AOSP android-16.0.0_r1, system/core/libprocessgroup/profiles/cgroups.json / task_profiles.json; 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

### device-mapper：虚拟块设备映射层

device-mapper（dm）是 Linux 内核提供的一个通用框架，它可以把一个或多个物理块设备"映射"成一个新的虚拟块设备。Android 大量使用了 device-mapper 来实现分区管理、完整性校验和加密等功能。

device-mapper 的工作基于三个概念：

1. **映射设备（Mapped Device）**：对上层可见的虚拟块设备，比如 `/dev/block/dm-0`
2. **映射表（Mapping Table）**：定义虚拟设备的每个扇区范围对应哪个底层设备的哪些扇区
3. **目标设备（Target Device）**：映射表指向的底层设备

[已验证: 来源见 Android分区挂载原理介绍（OPPO内核工匠）]

在 Android 中，几个关键的 dm 目标类型包括：

- **dm-linear**：线性映射，把一个连续的扇区范围映射到另一个设备的连续扇区。这是 Dynamic Partition 的基础——`system`、`vendor` 等分区是通过 dm-linear 从一个名为 `super` 的大物理分区中"切"出来的逻辑分区。
- **dm-verity**：完整性校验，通过预先计算的哈希树（hash tree）验证只读分区（如 `system`）的数据没有被篡改。
- **dm-snapshot**：快照设备，用于 Virtual A/B 升级，在升级过程中通过 Copy-on-Write（COW）设备记录变更。
- **dm-default-key**：元数据加密，对 `data` 分区进行块级加密。

这些 dm 目标层层叠加，最终形成了 Android 的分区布局。后面要说明的，就是这些分区各自负责什么、怎么挂载、对性能有什么影响。

## 分区布局：system、vendor、data 与 metadata

### 传统分区 vs Dynamic Partition

早期的 Android 使用固定大小的分区。`system`、`vendor`、`cache` 等分区在出厂时就确定了大小，写入分区表后不再改变。这种方式的问题在于灵活性差——如果 `system` 分区用完了而 `vendor` 还有空余，无法动态调整。

从 Android 10 开始，Google 引入了 **Dynamic Partition（动态分区）**。所有只读的 A/B 分区（`system`、`vendor`、`product`、`odm` 等）被合并到一个名为 `super` 的大物理分区中，然后通过 dm-linear 在运行时动态划分出逻辑分区。[已验证: 官方文档, source.android.com/docs/core/storage]

```text
Physical Partition: super
┌──────────┬──────────┬──────────┬──────────┐
│  system  │  vendor  │ product  │   odm    │
│ (logical)│ (logical)│ (logical)│ (logical)│
└──────────┴──────────┴──────────┴──────────┘
         mapped via dm-linear
```

这样一来，OTA 升级时可以动态调整各逻辑分区的大小，不再受制于固定分区表的约束。

### 各分区的职责

**system 分区**：包含 Android 框架、系统库和系统应用。它一直是只读分区，但挂载模型要按版本拆开。Android 9 的 system-as-root 会把 rootfs 合进 `system.img`，由内核把 `system.img` 挂成根文件系统。到了 Android 10，带 dynamic partitions 的设备改成由 ramdisk 里的 `first-stage init` 解析 `super` 分区 metadata，创建 `dm-linear` 逻辑块设备，再挂载 `system`、`vendor`、`product` 等逻辑分区。AOSP 对 launching with Android 10 且使用 dynamic partitions 的设备写得很清楚，这类设备不再使用 system-as-root。`system`、`vendor` 等只读分区仍受 AVB / dm-verity 保护。[已验证: 官方文档, source.android.com/docs/core/architecture/partitions/system-as-root; source.android.com/docs/core/ota/dynamic_partitions/implement]

**vendor 分区**：包含硬件抽象层（HAL）驱动、固件和厂商定制配置。这个分区的存在是 Project Treble 架构的核心——把 vendor 实现和 Android 框架解耦，使得框架可以独立升级而不需要等厂商适配。vendor 分区同样是只读的，受 dm-verity 保护。

**data 分区**：这是唯一的大容量可写分区，承载了几乎所有用户数据——安装的 App（`/data/app/`）、App 私有数据（`/data/data/`）、媒体文件（`/data/media/`）、系统数据库（如 `settings.db`）等。data 分区使用文件级加密（FBE），是性能优化的重点关注对象，因为几乎所有涉及持久化的 I/O 操作都发生在这里。

**metadata 分区**：一个独立的小分区，AOSP 建议大小为 16MB，通常挂载到 `/metadata`。它保存保护 metadata encryption key 的 KeyMint blobs，以及 `vold` 需要的少量状态。这里要分清顺序，系统在启动早期先挂载 `/metadata`，目的是拿到 key material；后面要解锁的是 `/data` 这侧的 metadata encryption key，不是“先把 metadata 分区解密”。[已验证: 官方文档, source.android.com/docs/security/features/encryption/metadata]

### 挂载流程：从 bootloader 到用户空间

Android 10+ 设备的常见启动链要比“bootloader 挂分区”细得多。bootloader 完成 Verified Boot 和硬件初始化后，把 boot image 里的 kernel 与 ramdisk 交给内核；内核启动后进入 ramdisk 里的 `first-stage init`；`first-stage init` 解析 `super` 分区 metadata，创建 `dm-linear` 逻辑设备，并挂载 `system`、`vendor`、`product` 等 `first_stage_mount` 分区。到了 `early-fs` 阶段，系统先启动 `vold`，让 metadata encryption 相关准备工作提前进行；到了 `late-fs` 阶段，`init` 会先执行 `wait_for_keymaster`，再通过 `mount_all` 挂载 `/data`。`vold` 参与的是 `/data` 挂载前的密钥准备和设备映射，bootloader 本身不负责挂载 `super` 或 `/data`。[已验证: 官方文档, source.android.com/docs/core/ota/dynamic_partitions/implement; source.android.com/docs/security/features/encryption/metadata]

## 文件系统：从 ext4 到 f2fs 的演进

### ext4 在 Android 上的问题

Android 早期使用 ext4 作为主要文件系统，这在服务器和桌面 Linux 上是成熟可靠的选择，但在手机场景下暴露出了一些问题。

手机存储的 I/O 特性与服务器完全不同。根据 Linux 阅码场的分析，手机存储 I/O 有几个典型特征：以 buffer I/O 为主（数据先写入 page cache，由内核回写），SQLite 频繁进行小量同步随机写（通过 `fsync`），存储芯片速度相对较低，设备会频繁异常掉电（手机没电直接关机），以及存储碎片化严重。

其中 SQLite 的 `fsync` 是 ext4 在 Android 上最常见的性能瓶颈之一。SQLite 使用 WAL（Write-Ahead Log）模式，每次事务提交都需要调用 `fsync` 确保日志写入磁盘。在 ext4 上，`fsync` 的实现涉及 jbd2（ext4 的日志系统）的 order 模式——为了保证数据一致性，`fsync` 不仅需要刷新日志，还要把所有相关的脏页都写到磁盘。更糟糕的是，ext4 的延迟分配（delayed allocation）机制会推迟分配物理块，等到 `fsync` 时才统一分配，这进一步拉长了 `fsync` 的耗时。再加上 I/O 优先级倒置的问题——低优先级的后台 I/O 可能占据了存储设备的队列，导致高优先级的 `fsync` 被阻塞——最终用户感知到的就是卡顿。[已验证: 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

### f2fs：为闪存优化的文件系统

为了解决这些问题，Android 逐步将 `data` 分区切换到 f2fs（Flash-Friendly File System）。f2fs 由 Samsung 开发，专门针对 NAND 闪存的特性设计，它的核心思路是把随机写转换为顺序写。

f2fs 的关键优化包括：

**Copy-on-Write（CoW）**：f2fs 不会就地覆盖数据，而是把修改后的数据写到新的位置，然后更新指向它的指针。这避免了闪存的"擦除-重写"开销，因为闪存的最小擦除单位（通常是 128KB 或 256KB 的 block）远大于最小写入单位（4KB 的 page）。就地覆盖意味着即使只修改 4KB 数据，也需要先擦除整个 block 再重写，而 CoW 只需要把新数据写到空闲空间。

**冷热数据分离**：f2fs 会根据数据的更新频率把它们分成"热"、"温"、"冷"三类。频繁更新的数据（如 SQLite 日志）放在一起，很少修改的数据（如照片）放在另一块区域。这样热数据的频繁更新不会影响冷数据所在的 block，减少了垃圾回收（GC）的开销和写入放大。

**SQLite 原子写优化**：这是一个针对 SQLite 提交路径的文件系统级优化，但适用范围比“所有 journal 模式都受益”窄得多。SQLite 官方的 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE` 文档写明，这个能力会在底层文件系统支持 batch atomic write 时启用；截至 SQLite 3.21.0，公开支持的文件系统只有 F2FS。启用后，SQLite 避免写入的是 rollback journal。WAL 是另一条提交路径，事务先追加到 WAL 文件，再由 checkpoint 回写主库，因此这里不能把 f2fs atomic write 写成对 WAL 和 rollback journal 都等价生效。Android 设备是否走到这条优化路径，还要继续核对 `external/sqlite` 的编译选项和机型配置。[已验证: 官方文档, sqlite.org/compile.html; sqlite.org/wal.html]

在 Perfetto 中，如果我们在 `data` 分区上观察到大量的 `fsync` 延迟，可以先确认文件系统类型。如果是 ext4，关注 `jbd2` 和 `ext4_sync_file_*` 这类同步写路径；如果已经是 f2fs，再看是否有回写、checkpoint 或 GC 在和前台 I/O 抢设备队列。f2fs 的 GC 多数时间在后台完成，但存储空间紧张时，前台读写也会被它拖慢。[图：f2fs GC 与前台 I/O 竞争的 Trace。主线程 slice 停在 `fsync` 或 `read`，后台出现 f2fs 回写或 GC 相关 worker，`block_rq_issue` 到 `block_rq_complete` 的间隔被拉长。]

## Scoped Storage：权限模型与 I/O 路径变化

### 为什么需要 Scoped Storage

Android 10 之前，App 只要获得了 `READ_EXTERNAL_STORAGE` 或 `WRITE_EXTERNAL_STORAGE` 权限，就可以读写共享存储（`/sdcard`）上的所有文件。这样一来，一个手电筒 App 理论上就可以读取用户的照片、文档和下载内容。这种粗粒度的权限模型在隐私安全上存在明显隐患。

从 Android 10 开始引入的 Scoped Storage（分区存储），改变了 App 访问共享存储的方式。Android 11 起强制执行。核心变化包括：

1. App 只能直接访问自己的专属目录（`Android/data/<package_name>/` 和 `Android/media/<package_name>/`），不需要任何权限
2. 要访问其他 App 创建的媒体文件，需要通过 MediaStore API 并获得相应权限
3. 要访问非媒体文件（如 PDF、文档），需要通过 Storage Access Framework（SAF）让用户手动选择
4. `/sdcard` 根目录不再对 App 直接可写

[已验证: 官方文档, developer.android.com/about/versions/11/privacy/storage]

### FUSE 层的性能开销

Scoped Storage 的实现仍然依赖共享存储上的权限检查和路径抽象。当 App 通过传统路径（如 `/sdcard/DCIM/`）访问共享媒体时，请求通常会经过 FUSE 这一层，由内核和用户态守护进程一起完成权限判定与转发。这里多出来的上下文切换、权限检查和数据转发，会让共享存储访问比应用内部的 `/data/user/0/<package>/` 更重。

Android 11 新增的是 shared media 的 direct file paths。拿到相应权限后，App 可以继续使用 `File` API 或 `fopen()` 访问媒体文件，兼容大量第三方媒体库。这一层解决的是 API 兼容问题，不等于天然绕过 FUSE。官方文档给出的结论更克制一些，顺序读时 direct file path 和 MediaStore 的性能接近，随机读写时 direct file path 反而可能慢到接近 2 倍，这种场景更适合继续走 MediaStore。[已验证: 官方文档, developer.android.com/about/versions/11/privacy/storage; developer.android.com/training/data-storage/shared/media]

Android 12 之后又多了一层变化。设备如果 launching with Android 12 且使用 official kernel，MediaProvider 可以配合 FUSE driver 打开 FUSE passthrough。当 App 对文件拥有完整访问权限时，后续读写请求可以直接转发到 lower file system，少走一轮用户态转发。这里要把三个概念拆开看：MediaStore API 是上层访问接口，direct file paths 是 Android 11 的兼容入口，FUSE passthrough 则是 Android 12+ 的内核与 MediaProvider 联合优化。[已验证: 官方文档, source.android.com/docs/core/storage/fuse-passthrough]

### 对 App I/O 行为的实际影响

Scoped Storage 对 App 开发和性能优化有几个直接影响。

**访问共享媒体时，先按访问模式选接口**：目录扫描、批量查询、随机读写这类场景，优先让 MediaStore 帮我们做索引和权限判定；兼容旧库或 native 媒体栈时，再考虑 Android 11 的 direct file paths。

**应用私有数据别混到共享存储**：只在 App 内部使用的数据，放内部存储 `/data/user/0/<package>/` 路径最省事；如果必须放 external app-specific directory，也要把它和共享媒体访问分开看，别把两条 I/O 路径混成一个模型。

**看版本边界再下结论**：同样是“共享媒体访问慢”，Android 10 常见的是纯 FUSE 转发开销，Android 11 多了 direct file paths，Android 12+ 还可能吃到 FUSE passthrough。分析时先确认系统版本、MediaProvider 模块和设备内核。

在 Perfetto Trace 中，FUSE 相关开销通常表现为 App 线程的文件 I/O 等待，与 `MediaProvider`、`fuse` 或同类用户态存储进程的 CPU 活动同一时间出现。[图：Scoped Storage 访问路径对比。左侧是 MediaStore URI 打开文件，右侧是 Android 11 direct file path 与 Android 12+ FUSE passthrough 的后续转发路径，标出 App 线程、MediaProvider、FUSE driver、lower file system 的先后关系。]

### 版本断点速查

| Android 版本 | system / 挂载模型 | shared storage 入口 | FUSE 行为 | App 侧建议 |
| --- | --- | --- | --- | --- |
| Android 9 | `system-as-root` 成为 launching device 基线，rootfs 合入 `system.img` | 传统 external storage 模型 | FUSE 仍用于 emulated storage，Scoped Storage 还没强制上线 | 旧项目以路径访问为主，但开始留意后续权限收紧 |
| Android 10 | dynamic partitions + `first-stage init` 成为新设备主路径 | Scoped Storage 引入，允许一部分兼容开关 | 共享存储访问普遍经过 FUSE | 新代码优先 MediaStore / SAF，少依赖裸路径 |
| Android 11 | `/data` 挂载流程继续沿用 Android 10 | shared media 支持 direct file paths、`File` API、`fopen()` | 仍有 FUSE，但 API 入口多了一条兼容路径 | 媒体库兼容可以用 direct file paths，随机读写仍优先 MediaStore |
| Android 12 | 挂载模型基本稳定 | API 入口与 Android 11 接近 | launching device + official kernel 可启用 FUSE passthrough | 先确认设备是否支持 passthrough，再判断瓶颈位置 |
| Android 15 | 挂载与共享存储主模型延续 Android 12+ | MediaStore / direct file path 共存 | FUSE passthrough 仍取决于内核与模块版本 | 大量枚举和跨媒体库访问仍优先 MediaStore，模块侧优化按设备实测确认 |

## FBE：文件级加密的存储影响

### 从全盘加密到文件级加密

Android 的存储加密经历了从全盘加密（Full-Disk Encryption，FDE）到文件级加密（File-Based Encryption，FBE）的演进。FDE 对整个 `data` 分区使用同一个密钥加密，用户解锁手机后才解密整个分区。FBE 则不同，它为每个文件独立加密，并引入了 DE（Device Encrypted）和 CE（Credential Encrypted）两种密钥。

**DE 密钥**（Device Encrypted Key）：绑定到硬件，不依赖用户凭据（PIN/密码/图案）。设备启动后即可使用 DE 密钥解密对应的文件。这使得闹钟、通知、电话等功能在用户解锁手机之前就能正常工作——这就是 Direct Boot 特性。

**CE 密钥**（Credential Encrypted Key）：绑定到用户凭据，只有用户解锁手机后才能获取。绝大多数用户数据（App 数据、照片等）使用 CE 密钥加密。

从 Android 10 开始，FBE 对所有新设备是强制要求的。[已验证: 官方文档, source.android.com/docs/security/features/encryption/file-based]

### metadata encryption、FBE 与 `/metadata` 的分工

把“存储加密”写成一条线，很容易把三个不同层级揉在一起。`/metadata` 是独立小分区，作用是保存保护 metadata encryption key 的 KeyMint blobs；metadata encryption 工作在 userdata block device 这一层，保护目录项、inode、文件长度这类文件系统 metadata，现代设备常见实现是 `dm-default-key` 配合 inline crypto / blk-crypto；FBE 则建立在文件系统之上，由 `vold` 在 `/data` 可挂载之后安装 DE/CE key，再由 `fscrypt` 把策略应用到不同目录。

换成启动顺序看会更清楚。系统先挂载 `/metadata`，让 `vold` 能取到保护 metadata encryption key 的 key material；随后 `wait_for_keymaster` 与 `mount_all` 协作，让 `/data` 进入可挂载状态；等文件系统已经可用，`vold` 才继续安装 System DE、User DE、User CE key。`dm-default-key` 管的是 `/data` block device 的 metadata 保护，不是 FBE 的别名。[已验证: 官方文档, source.android.com/docs/security/features/encryption/metadata; source.android.com/docs/security/features/encryption/file-based]

[图：`/data` 挂载前的三层关系图。左侧是 `/metadata` 分区，标注 KeyMint blobs；中间是 metadata encryption / `dm-default-key`，标注目录项、inode、文件长度等文件系统 metadata；右侧是 FBE / `fscrypt`，标注 System DE、User DE、User CE key 与 `/data/system_de`、`/data/user_de/<id>`、`/data/user/<id>` 的对应关系。]

### 加密的 I/O 性能影响

加密操作不可避免地会引入额外的计算开销，但现代 Android 设备上这个开销已经很小了。关键在于**硬件加速**。

主流 SoC 都集成了专用的加密引擎（inline encryption hardware），它位于存储控制器和闪存芯片之间。数据在写入闪存之前由硬件加密引擎自动加密，读取时自动解密。整个过程对 CPU 透明——CPU 写入的是明文数据，从存储读取到的也是明文数据，加密解密在 DMA 传输过程中完成。这种 inline encryption 方式通常不会成为主要瓶颈。[已验证: 官方文档, source.android.com/docs/security/features/encryption/file-based]

在 Perfetto Trace 中，我们通常不需要单独关注 FBE 的性能开销。但如果在低端设备上观察到加密相关的 CPU 活动，可以检查 SoC 是否支持 inline encryption——如果不支持，FBE 会回退到软件加密实现，这时 CPU 开销会比较明显。

### FBE 的密钥层次

FBE 的密钥管理由 `vold`（Volume Daemon）负责。整个密钥层次如下：

1. **System DE Key**：系统级 DE 密钥，由 `vold` 在启动早期读取或创建并安装到 fscrypt。对应 `/data/system_de/`、`/data/misc_de/` 目录。
2. **User DE Key**：每个用户的 DE 密钥，由 `vold` 管理，用于该用户的 Direct Boot 相关数据（如闹钟设置），对应 `/data/user_de/<user_id>/`。
3. **User CE Key**：每个用户的 CE 密钥，用户解锁后由凭据派生，用于绝大多数 App 数据，对应 `/data/user/<user_id>/`（CE 也包括 `/data/system_ce/<user_id>/`）。

AOSP 中的关键实现路径：
- `system/vold/FsCrypt.cpp`：`fs_prepare_user_storage()` 函数准备 DE/CE 目录并应用 fscrypt policy
- `system/vold/Utils.cpp`：`BuildDataSystemDePath()`、`BuildDataMiscDePath()`、`BuildDataUserDePath()` 生成 `/data/system_de/<user>`、`/data/misc_de/<user>`、`/data/user_de/<user>` 等路径

[已验证: AOSP android-16.0.0_r1, system/vold/FsCrypt.cpp / Utils.cpp; 来源见 Android分区挂载原理介绍（OPPO内核工匠）]

每个目录的加密策略由扩展属性（xattr）记录在文件系统的 inode 中。当创建新文件时，文件系统会继承父目录的加密策略，自动使用对应的密钥加密。

## Dynamic Partition 与 Virtual A/B 的存储布局

Dynamic Partition 通过 `super` 物理分区和 `dm-linear` 在运行时切出逻辑分区，这一层已经介绍过了。但分区布局的灵活调整只解决了"逻辑分区怎么划"的问题——另一半是 **Virtual A/B（VABC）**，解决的是 OTA 升级时如何安全更新这些逻辑分区、差异数据存在哪里、由谁合并。

传统 A/B 分区方案为每个分区维护两套完整副本（slot A 和 slot B），占用双倍存储空间。Virtual A/B 不再为只读分区保留完整副本，而是只记录升级中的差异。但"怎么记录差异、差异写到哪、合并由谁执行"这三个问题，在不同 Android 版本里答案完全不同，不能用一个统一的 `dm-snapshot` 模型概括。

### Android 11：kernel COW

Android 11 引入 Virtual A/B 的早期形态，差异记录在 `dm-snapshot` COW 设备上。COW 空间从 `super` 分区中分配，内核 snapshot 模块负责 redirect write——写入新数据前先把旧数据复制到 COW 设备，再将新数据写到目标位置，一次写入变成两次 I/O。

### Android 12+：Android COW Format + snapuserd

Android 12 起，Virtual A/B 转用 **Android COW format**（Android 自己的 COW 格式），不再依赖内核 `dm-snapshot`。COW 空间从 `super` 内分配改为主要落在 `/data`，由 `dm-user`（用户态 device mapper 接口）配合 `snapuserd` 守护进程处理压缩快照（compressed snapshots）。`snapuserd` 负责读取 COW 数据并以用户态响应读取——当系统需要读取旧版本数据时，`snapuserd` 判断该数据是否已被 COW 覆盖，未覆盖则直接读 base 分区。

### Android 13+：userspace merge

Android 13 将 snapshot merge 完全移入 `snapuserd` 用户态，移除了对内核 `dm-snapshot` 和 kernel COW 的依赖。升级成功后，`snapuserd` 执行 userspace merge 将 COW 数据写回正式分区；升级失败时，丢弃 COW 区回退到旧版本，不需要额外还原操作。[已验证: AOSP 官方 Virtual A/B 文档, source.android.com/docs/core/ota/virtual_ab]

```text
Virtual A/B 存储模型演进：

Android 11（kernel COW）：
  snapshot delta → dm-snapshot COW → super 内分配

Android 12+（Android COW format）：
  snapshot delta → /data（compressed）→ dm-user + snapuserd

Android 13+（userspace merge）：
  merge 由 snapuserd 用户态执行，移除 kernel COW 依赖
```

这次演进的实质是把 COW 空间从 `super` 分区解放出来，放到容量更充裕的 `/data` 分区。Android 12+ 的 COW 空间属于临时的 transient space——升级完成后可以被回收。升级期间，`/data` 上的 COW 写入会和用户 I/O 竞争；如果 `/data` 已经接近满载，性能影响会更明显。

在 Perfetto Trace 中，OTA 升级期间的 Virtual A/B 活动有几个可观测信号，集中在三组进程：

| 进程 | 角色 | Trace 特征 |
| --- | --- | --- |
| `update_engine` | 下载包、写 COW、触发 merge | 持有 `/data` COW 空间的写入流量；升级完成后停止 |
| `snapuserd` | Android 12+ 的 COW 读写与 merge 执行 | 用户态 dm-user worker，持续占用 CPU 和 `/data` I/O；升级成功后 merge 阶段仍活跃 |
| 前台 App | 受影响方 | 主线程 `fsync`/`read` 延迟明显拉长，时间与 `snapuserd`/`update_engine` 活动对齐 |

[图：Virtual A/B 后台 I/O 竞争的 Trace。标出 `update_engine`、`snapuserd` dm-user worker、以及前台 App 主线程被拉长的 `fsync`/`read`，同时展示 `/data` 上的稳定写入流量。]

合并大多在后台完成，但存储空间紧张或后台写入密集时，`snapuserd` 和前台 App 争抢 `/data` 的 IOPS，会明显拉长前台 App 的 I/O 等待。

## 存储寿命与写入放大

NAND 闪存有一个物理限制：每个存储单元的擦写次数是有限的。SLC（单层单元）可以承受约 10 万次擦写，MLC（多层单元）约 3000-10000 次，TLC（三层单元）约 1000-3000 次，而现代高密度 QLC（四层单元）只有几百次。手机上使用的主要是 TLC 或混合 SLC/TLC 方案。

这个物理限制催生了一个重要的性能概念：**写入放大（Write Amplification Factor，WAF）**。写入放大的含义是，实际写入闪存的数据量大于主机请求写入的数据量。例如，App 只想写 4KB 的数据，但闪存控制器可能需要先读取一个 128KB 的 block，修改其中的 4KB，擦除整个 block，再写回 128KB——这样 4KB 的写入变成了 128KB 的实际写入，WAF = 32。

写入放大的来源有几个：

- **垃圾回收（GC）**：闪存不能就地覆盖写，必须先擦除再写。当空闲 block 不足时，控制器需要把仍有效的数据从一个 block 搬到另一个 block，然后擦除旧 block。这些"搬家"操作产生了额外的写入。
- **磨损均衡（Wear Leveling）**：控制器会尽量让所有 block 的擦写次数均匀分布，避免某些 block 过早失效。这可能导致数据被频繁搬运。
- **文件系统层面的碎片**：即使 App 顺序写数据，经过文件系统的分配策略和闪存内部的地址映射，实际写入模式可能变得更随机。

写入放大是一个长期累积效应。新手机上存储空间充裕，GC 压力小，WAF 接近 1。但随着使用时间增长，存储碎片化加剧，可用空间减少，GC 频率上升，WAF 逐渐增大。这就是为什么很多用户感觉"手机用了一年之后变慢了"——存储性能的退化是真实存在的，不是心理作用。

从性能优化的角度，减少写入放大最有效的方法是**减少不必要的写入**。这包括：避免频繁的小量同步写入（如 SharedPreferences 的 `apply()` 替代 `commit()`）、使用 f2fs 的 CoW 机制减少就地更新、以及在 App 层面做好数据缓存策略，避免每次操作都触发磁盘写入。[已验证: 来源见 手机Android存储性能优化架构分析（Linux阅码场）]

## 常见问题与误区

**「手机变慢是因为闪存老化了吗？」**

不完全是。闪存有擦写寿命，但正常使用条件下（每天写入 10-20GB），TLC 闪存的寿命在 3-5 年内不太可能耗尽。手机长期使用后变慢，更主要的原因是存储碎片化导致的 GC 频率上升、App 数据量增长导致的 I/O 增多、以及系统更新后新版本对存储性能的更高要求。存储器件本身的性能退化只贡献了一小部分。

**「f2fs 一定比 ext4 快吗？」**

不一定。f2fs 在随机写密集的场景（如大量 SQLite 操作）下有明显优势，但在大文件顺序读写的场景下，两者的差距不大。而且 f2fs 的 GC 机制在存储空间紧张时可能引入不可预测的延迟抖动。如果设备存储空间长期保持在 80% 以下，f2fs 的优势比较稳定；但如果经常接近满载，f2fs 的性能退化反而可能比 ext4 更剧烈。

**「FBE 加密会拖慢存储性能吗？」**

在支持 inline encryption 的设备上，FBE 额外带来的 CPU 成本通常不大；如果设备缺少这类硬件能力，软件加密会把一部分开销重新搬回 CPU。排查时别只盯着“FBE 会不会慢”，还要一起看 `dm-default-key` 是否启用、`vold` / kernel 日志里有没有解锁重试，以及 block 层等待是否与加密阶段重合。

## 存储问题观测地图

这一章反复提 Perfetto 和 I/O 诊断，如果没有一个最小观测地图，读者很容易停在“看起来像 I/O 慢”的直觉层。实战中建议按以下五层抓取。

[图：存储问题观测地图。纵轴是 block layer、ext4/f2fs、FUSE/MediaProvider、init/vold、update_engine/snapuserd；横轴是抓取入口、关键进程、常见异常形态。]

| 关注面 | 推荐抓取点 | 重点看什么 | 异常形态 |
| --- | --- | --- | --- |
| Block layer | Perfetto `ftrace` 里的 `block_rq_issue`、`block_rq_complete` | 单次请求从 issue 到 complete 的时延、队列是否堆积 | 前台线程卡在 `fsync` / `read`，同时 block 完成时延持续拉长 |
| ext4 / f2fs | `ext4_sync_file_*`、`f2fs_sync_file_*`、内核回写线程 | 同步写是否集中出现在事务提交或 checkpoint 之前后 | `fsync` 时间长，伴随 `jbd2`、f2fs checkpoint 或 GC 活动 |
| Shared storage / FUSE | App 线程、`MediaProvider`、`fuse` 相关进程或线程 | App I/O wait 是否和用户态转发、权限检查同时发生 | 目录扫描或媒体批量访问时，App 与 `MediaProvider` 一起放大 CPU 与 I/O 等待 |
| Mount / encryption | 开机阶段的 `init`、`vold`、`wait_for_keymaster` 日志与 slice | `/metadata` 是否已挂载、`vold` 是否提前启动、`mount_all` 是否卡住 | 开机早期反复重试 KeyMint、`/data` 长时间挂不上，后续所有 I/O 都会被拖住 |
| OTA merge | `update_engine`、`snapuserd`、Virtual A/B merge 相关后台写入 | OTA 后台 merge 是否还在持续，前台 I/O 是否被挤压 | 重启后长时间存在稳定写入流量，前台 App 随机 I/O 延迟异常 |

除了 Perfetto，本章这些问题还值得和 `logcat`、`dmesg`、`mount`、`getprop` 一起交叉看。存储问题经常横跨内核、init、`vold`、MediaProvider 和 App 线程，单看一层很容易把根因看偏。

## 小结：从存储架构到性能分析

回到开头的那个卡顿场景。当我们看到主线程在 `fsync` 上等待时，完整的分析流程应该是：

1. **物理层**：确认设备使用的是 UFS 还是 eMMC——这决定了 I/O 延迟的基线
2. **块设备层**：检查 I/O 调度器配置和 cgroup I/O 优先级——是否有后台任务抢占了前台的 I/O 带宽
3. **文件系统层**：确认使用的是 ext4 还是 f2fs——ext4 的 `fsync` 在 Android 场景下有已知的性能问题
4. **加密层**：确认 FBE 是否使用硬件加速——软件加密在低端设备上可能成为瓶颈
5. **权限层**：如果涉及共享存储访问，检查是否走了 FUSE 路径——FUSE 的上下文切换开销可能增加 I/O 延迟

理解了存储栈的每一层，我们就能从 Perfetto Trace 中的 I/O 等待信号，逐层追踪到根因，而不是停留在"主线程被 I/O 阻塞了"这个表面结论上。

存储架构的知识还将在后续章节中持续用到——第 6.2 节我们会深入文件系统的选择与调优，第 6.3 节会讨论 I/O 调度的具体策略，而存储性能的长期退化问题则与第 7 章流畅性优化中的"老设备卡顿"现象直接相关。

## 参考资料

- **手机 Android 存储性能优化架构分析** — Linux 阅码场，系统梳理了 Android 存储 I/O 路径和 ext4/f2fs 的性能差异
- **手机主流存储器件的分析与发展** — OPPO 内核工匠，eMMC/UFS 架构对比与 UFS 4.0 MCQ 特性详解
- **Android 分区挂载原理介绍** — OPPO 内核工匠，Dynamic Partition、dm-linear、FBE 密钥层次
- **Android Storage | Android Open Source Project** — source.android.com/docs/core/storage，官方分区与加密文档
- **Scoped Storage | Android Developers** — developer.android.com/about/versions/11/privacy/storage，分区存储 API 与权限模型
- **JEDEC UFS 4.0 Standard (JESD220E)** — UFS 4.0 规范，MCQ 多命令队列定义
