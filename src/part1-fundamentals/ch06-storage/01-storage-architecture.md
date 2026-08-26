---
title: Android 存储架构
chapter: '6.1'
section: '6.1'
status: finalized
applicable_versions: Android 9 - Android 17 (API 37)
last_verified: '2026-08-26'
last_verified_against: Android 17 (android-17.0.0_r1), AOSP cgroups/task_profiles/init/vold/MediaProvider source, Android Common Kernel android17-6.18 UFS/blk-crypto config, dynamic partitions / metadata encryption / system-as-root / scoped storage / FUSE passthrough / Virtual A/B docs, SQLite compile & WAL docs
confidence: medium
sources:
- type: reference
  path: 手机Android存储性能优化架构分析（Linux阅码场）
- type: reference
  path: 手机主流存储器件的分析与发展（OPPO内核工匠）
- type: reference
  path: Android分区挂载原理介绍（OPPO内核工匠）
- type: reference
  path: Android Storage | Android Open Source Project
- type: reference
  path: Scoped Storage | Android Developers
- type: reference
  path: Access media files from shared storage | Android Developers
- type: reference
  path: File-based encryption | Android Open Source Project
- type: reference
  path: Metadata encryption | Android Open Source Project
- type: reference
  path: System-as-root | Android Open Source Project
- type: reference
  path: Implement dynamic partitions | Android Open Source Project
- type: reference
  path: SQLite Compile-time Options / WAL | sqlite.org
- type: reference
  path: JEDEC UFS 4.0 Standard (JESD220E)
tags:
- storage
- ufs
- emmc
- partition
- scoped-storage
- mediastore
- fuse
- fbe
- dynamic-partition
- virtual-ab
- f2fs
related_chapters:
- '6.2'
- '4.1'
- '7.2'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_idle_audit_at: '2026-08-26T22:49:33+08:00'
last_idle_audit_run_id: 20260826-224308-idle-audit-1f93810e
---

# Android 存储架构

一次应用 I/O 会跨越 API、文件系统、页缓存、块层和存储器件，任何一层都可能把短请求放大成长尾。阅读这条链路的目的，是把“磁盘慢”拆成可观测的缓存命中、回写、排队、同步和介质延迟。

## 从一个卡顿现象说起

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核锚点是 Android Common Kernel `android17-6.18-2026-06_r6`。设备厂商可以定制分区表、文件系统、UFS 控制器和 vendor kernel（厂商内核），因此涉及具体机型的性能结论仍要以运行时信息为准。

在 Perfetto 中追踪主线程卡顿时，常会遇到这样的片段：线程调用 SQLite、SharedPreferences 或普通文件 API 后进入睡眠，直到数据回写、日志提交或设备请求完成才重新运行。SQLite 事务和 SharedPreferences 写盘是两条独立的实现路径，不能看到 `fsync()` 就把前者解释成后者；还要结合调用栈、文件名、文件系统事件和 block trace（块 I/O 跟踪记录）判断。

这类问题有时伴随大量 CPU 工作，有时则主要耗在 I/O wait（等待输入/输出完成）。Android 文件访问可能依次经过 VFS（统一文件系统接口）、具体文件系统、fscrypt（文件级加密框架）、device-mapper（块设备映射层）、块层、主机控制器和闪存；共享存储还可能经过 MediaProvider/FUSE。只有把等待时间对应到具体层级，才能判断延迟来自同步点设计、文件系统回写、设备排队、加密准备，还是共享存储的权限检查路径。

以下沿数据从应用 API 到存储器件的路径梳理 Android 存储架构。

## 存储栈全景：从闪存芯片到应用 API

Android 存储栈可以按职责分为应用与 framework、VFS 与文件系统、块设备映射与调度、主机控制器和闪存器件几层。ext4、f2fs、FUSE、fscrypt 和 device-mapper 位于不同层级，分析时不能把它们统称为“文件系统开销”。

下面的简图用于标出常见读写路径；括号中的层只在相应场景出现。

```text
Application / native library
    ↓  Java File API、SQLite、MediaStore 或 POSIX I/O
Android framework / ContentProvider（按 API 路径）
    ↓
MediaProvider + FUSE（共享外部存储路径）
    ↓
VFS → ext4 / f2fs → fscrypt
    ↓
device-mapper（dm-linear、dm-verity、dm-default-key、snapshot，按卷配置）
    ↓
Block multi-queue / I/O scheduler
    ↓
UFS 或 eMMC host controller → storage device
```

同一次访问不会经过图中的每一项。例如，应用内部文件不经过 MediaProvider/FUSE；只读动态分区通常经过 dm-linear 与 dm-verity；`/data` 则可能叠加 dm-default-key 和 fscrypt。该图用于帮助定位层级边界，不代表所有设备都采用同一张映射表。

先看最底层的物理存储器件。

## 物理存储器件：UFS 与 eMMC 的差异

### 总线、并发和软件栈

eMMC（embedded MultiMediaCard）和 UFS（Universal Flash Storage）都是管理型闪存器件，封装中包含 NAND 闪存、控制器和 FTL（Flash Translation Layer，闪存转换层）。FTL 负责把主机看到的逻辑块地址映射到 NAND 物理位置。两类器件都向 Linux 暴露块设备，但主机接口和并发能力有明显差异。

eMMC 使用并行总线，数据传输为半双工。旧式 eMMC 请求模型的并发能力有限，但 eMMC 5.1 已经定义 Command Queuing（命令排队），不能再用“控制器同一时刻只能处理一个命令”概括所有 eMMC 5.1 设备。主机驱动、器件是否支持 CQE（Command Queue Engine）、队列深度和固件质量都会影响结果。

UFS 使用 MIPI M-PHY 差分串行链路和 UniPro 协议，UTP（UFS Transport Protocol）负责承载 UFS Command Set。链路支持全双工，协议和主机控制器也支持同时处理多个 outstanding request（尚未完成的请求）。更高的链路速率、队列并发度和控制器并行度可以改善吞吐与尾延迟，但应用实际感受到的性能仍受 NAND 类型、SLC cache（用单层单元模式提供的高速缓存）、温度、容量占用和固件影响。

下面的图用于区分 UFS 协议层次。

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

应用调用 `read()` 时不会直接生成 UFS Command Set 命令。文件系统与块层会先把文件偏移转换、合并或拆分为块请求，再由 UFS host driver（主机驱动）把请求映射为 UTP transfer request。

### 性能差距不能只看版本号

JEDEC 版本规定的是接口能力，不承诺某颗量产器件一定达到某组 MB/s 或 IOPS（每秒输入/输出操作次数）。把厂商样品数据写成协议标准，会让设备基线失真。比较时应区分以下维度：

| 维度 | eMMC 5.1 | UFS 3.x / 4.x |
|---|---|---|
| 主机链路 | 并行、半双工 | M-PHY 串行、全双工 |
| 多请求能力 | 可有 CQE，设备实现差异大 | 原生支持多个 transfer request |
| Linux 驱动栈 | MMC block / CQHCI（命令队列主机控制器接口，按设备能力） | SCSI/UFSHCD（UFS 主机控制器驱动） |
| 多硬件队列 | 取决于主控和 CQE | 支持 MCQ 的 UFSHCI 主控可建立多组 submission/completion queue（提交/完成队列） |
| 常见性能特征 | 链路与并发上限较低 | 更高带宽与并发潜力，尾延迟仍由器件和负载决定 |

**MCQ（Multi-Circular Queue，多循环队列）是 UFS Host Controller Interface 的能力**，不能只把它理解为“UFS 4.0 闪存特性”。`android17-6.18-2026-06_r6` 的 `drivers/ufs/core/ufs-mcq.c` 会根据主控能力配置读写队列、专用读队列和 polling queue（轮询队列）；默认读写队列数还会参考 CPU 数量。要确认设备是否启用了 MCQ，还需检查 host controller capability（主机控制器能力）、驱动日志和 `/sys` 队列信息。

### 验证器件差异

发现 I/O 延迟异常时，应先记录器件型号、UFS/eMMC 版本、文件系统、可用空间、温度与当前后台负载，再为这台设备建立冷启动、随机读写和 `fsync()` 基线。Perfetto 的 block request 延迟可以说明请求在块设备路径上等待了多久，但不能仅凭“UFS 4.0”标签设定固定的毫秒阈值。

## 块设备层：I/O 调度与设备映射

文件系统会把一段或多段内存页组织成 `bio`（描述一组块 I/O 的内核结构）并提交给块层。device-mapper 可以先改写目标设备和扇区；块层再合并或拆分 `bio`，形成 request，并交给 blk-mq（多队列块层）与设备驱动。映射和调度的先后关系还取决于具体的 device-mapper 叠加方式，不能把整个过程理解成一个固定函数。

### I/O 调度器

I/O 调度器负责块 request 的排序、合并与派发。Android 设备可能选择 `mq-deadline`、BFQ（Budget Fair Queueing）或 `none`，UFS MCQ 与设备厂商配置都会影响最终选择。`mq-deadline` 同时维护排序队列和 FIFO（先进先出）到期约束；BFQ 根据预算和权重分配设备服务时间，启用相应 cgroup（控制组）支持时可以体现组级权重。调度器名称本身并不保证前台请求一定优先。

手机上经常出现前台随机读与后台顺序写竞争。AOSP `android-17.0.0_r1` 的 `libprocessgroup/profiles/cgroups.json` 仍把 v1 `blkio`（块 I/O 控制组）挂载到 `/dev/blkio`；在 `task_profiles.json` 中，`LowIoPriority` 进入 `blkio/background`，`SCHED_SP_FOREGROUND` 与 `SCHED_SP_TOP_APP` 分别组合 `HighIoPriority`、`MaxIoPriority`。这些 profile 只表达用户空间的分组意图，能否转化为实际的设备服务差异，取决于 active scheduler（当前启用的调度器）、内核 cgroup 支持和厂商的 blkio 属性。可结合 `/sys/block/<dev>/queue/scheduler`、`/proc/cgroups`、`/dev/blkio` 与设备配置进行核对。

### device-mapper：虚拟块设备映射层

device-mapper（简称 dm）是 Linux 内核提供的通用块设备映射框架。它可以把一个或多个底层块设备映射成新的虚拟块设备。Android 使用 device-mapper 实现分区管理、完整性校验和加密等功能。

device-mapper 的工作涉及三个基本概念：

1. **映射设备（Mapped Device）**：对上层可见的虚拟块设备，例如 `/dev/block/dm-0`；
2. **映射表（Mapping Table）**：定义虚拟设备的每段扇区范围对应哪个底层设备的哪些扇区；
3. **目标设备（Target Device）**：映射表指向的底层块设备。

Android 常用的 dm target（映射目标类型）包括：

- **dm-linear**：把一个连续扇区范围线性映射到另一个设备的连续扇区。它是 Dynamic Partition 的基础，`system`、`vendor` 等逻辑分区通过 dm-linear 从 `super` 物理分区中映射出来。
- **dm-verity**：通过预先计算的 hash tree（哈希树）校验只读分区（如 `system`）的完整性，检测数据是否被篡改。
- **dm-snapshot / dm-user**：用于 Virtual A/B 的快照路径，但具体职责要按 Android 版本区分。Android 11 使用 `dm-snapshot` 和 kernel COW；Android 12 compressed snapshots 引入 Android COW format 与 `snapuserd`，但仍需转换到 kernel COW / `dm-snapshot`；Android 13+ 的 userspace merge 才移除对 kernel COW 和 `dm-snapshot` 的依赖。
- **dm-default-key**：用于 metadata encryption，在 `data` 分区的块设备层执行加密。

这些 dm 目标可以叠加，形成 Android 的分区布局。各分区的职责、挂载方式和性能影响需要分别分析。

## 分区布局：system、vendor、data 与 metadata

### 传统分区与 Dynamic Partition

早期 Android 使用固定大小的分区。`system`、`vendor`、`cache` 等分区在出厂时就确定容量，写入分区表后不能动态调整。如果 `system` 空间不足而 `vendor` 仍有空余，这部分空间也无法直接调给 `system` 使用。

Android 10 引入 **Dynamic Partition（动态分区）**。设备可以把 `system`、`vendor`、`product`、`odm` 等适合动态化的只读分区放入 `super`，再通过 dm-linear 映射成逻辑分区。`boot`、`dtbo`、`vbmeta` 等 bootloader（引导加载程序）需要直接读取的分区通常仍是物理分区，因此不能说所有 A/B 分区都进入了 `super`。

下面的图用于说明 `super` 与逻辑分区的映射关系，不代表分区在介质上的固定排列。

```text
Physical Partition: super
┌──────────┬──────────┬──────────┬──────────┐
│  system  │  vendor  │ product  │   odm    │
│ (logical)│ (logical)│ (logical)│ (logical)│
└──────────┴──────────┴──────────┴──────────┘
         mapped via dm-linear
```

借助这种布局，OTA 升级可以动态调整各逻辑分区的大小，不再完全受固定分区表约束。

### 各分区的职责

**system 分区**：包含 Android framework、系统库和系统应用，在正常 Verified Boot（验证启动）流程中以只读方式使用。Android 9 首发设备采用当时的 system-as-root：rootfs（根文件系统）内容合入 `system.img`，由内核直接挂载为根。Android 10 仍采用 system-as-root 的分区布局，但启动方式已经变化：设备必须带 ramdisk，`first-stage init` 解析 `super` metadata、创建 dm-linear 逻辑设备，并挂载 `system`、`vendor`、`product` 等分区，不再沿用 Android 9 的 no-ramdisk、kernel-direct-mount 路径。受保护的只读分区继续由 AVB（Android Verified Boot）/ dm-verity 验证。

**vendor 分区**：包含 HAL（硬件抽象层）实现、固件和厂商定制配置。Project Treble 借助这一分区边界把 vendor 实现与 Android framework 分开，使 framework 升级不必与全部厂商实现同步更新。vendor 分区同样以只读方式使用，并受 dm-verity 保护。

**data 分区**：这是主要的大容量可写分区，承载安装包（`/data/app/`）、应用私有数据（`/data/user/<user_id>/`）、共享媒体的 backing storage（底层存储，`/data/media/`）以及系统数据库等。设备还可能有 `metadata`、`persist` 等小型可写分区，所以“唯一可写分区”并不严谨。应用日常持久化流量主要集中在 `/data`，这里也是 I/O 性能分析的重点。

**metadata 分区**：这是启动早期即可使用的独立小分区，AOSP metadata encryption 文档建议容量为 16 MB，通常挂载到 `/metadata`。它保存用于保护 metadata encryption key 的 KeyMint blobs（由 KeyMint 保护的密钥数据），也可能承载 `vold`、checkpoint、Virtual A/B 等功能在 `/data` 挂载前必须访问的少量状态。系统先挂载 `/metadata` 取得 key material（密钥材料），随后建立 `/data` 的 metadata-encrypted block device（元数据加密块设备）；不能把这个顺序表述成“先解密 metadata 分区”。

### 挂载流程：从 bootloader 到用户空间

Android 10+ 设备的常见启动链远比“bootloader 挂分区”复杂。bootloader 完成 Verified Boot 和硬件初始化后，把 boot image 中的 kernel 与 ramdisk 交给内核。内核启动后进入 ramdisk 中的 `first-stage init`；`first-stage init` 解析 `super` 分区 metadata，创建 `dm-linear` 逻辑设备，并挂载 `system`、`vendor`、`product` 等 `first_stage_mount` 分区。到 `early-fs` 阶段，系统先启动 `vold`，提前进行 metadata encryption 的准备工作；到 `late-fs` 阶段，`init` 先执行 `wait_for_keymaster`，再通过 `mount_all` 挂载 `/data`。`vold` 负责 `/data` 挂载前的密钥准备和设备映射，bootloader 本身不负责挂载 `super` 或 `/data`。

## 文件系统：ext4 与 f2fs

### ext4 的同步写成本

ext4 和 f2fs 都是 Android 17 GKI（Generic Kernel Image，通用内核镜像）支持的文件系统，量产设备可以选择其中之一作为 `userdata`。ext4 在 Android 上并非“过时方案”；其日志、一致性保证与同步写时机仍需结合应用事务模型分析。

应用的普通 buffered I/O（缓冲 I/O）会先进入 page cache（页缓存），持久化边界则常由 SQLite、SharedPreferences、文件下载器或系统服务调用 `fsync()` / `fdatasync()` 建立。手机还同时面对进程频繁启动、后台回写、突然掉电保护、热约束和共享闪存队列竞争，这些因素都可能放大一次同步写的尾延迟。

SQLite 可以使用 rollback journal（回滚日志）或 WAL（Write-Ahead Logging，预写日志）。一次提交会发出哪些同步操作，还取决于 journal mode、`synchronous` 级别、checkpoint（检查点）状态和 Android SQLite 配置。WAL 模式通常把事务记录追加到 `-wal` 文件，再由 checkpoint 回写主库，不能把所有事务简化成“每次都同步整个数据库”。在 ext4 常见的 `data=ordered` 配置下，`fsync()` 需要协调目标文件的脏数据、必要的 jbd2 metadata transaction（文件系统日志事务）和设备 flush。延迟分配可能把块分配工作推到回写或同步阶段，后台写入也可能占据设备队列，因此要通过具体 trace 判断耗时落在哪一步。

### f2fs：为闪存优化的文件系统

f2fs（Flash-Friendly File System）是 Android 设备可选的 `userdata` 文件系统。它采用 log-structured（日志结构）设计，把主机侧更新写入新的逻辑块，并通过 segment（分段）、checkpoint 和 GC（垃圾回收）管理空间。Android 没有要求所有设备把 `/data` 从 ext4 统一迁移到 f2fs。

f2fs 的关键设计包括：

**Out-of-place update（异地更新）**：f2fs 通常把修改后的数据写入新逻辑块，再更新元数据。它可以把主机侧的随机更新整理到 segment 中，降低文件系统层的覆盖写与碎片压力。NAND 的物理擦除、有效页搬移和写入放大仍由器件 FTL 参与，f2fs 无法保证一次 4 KiB 更新在闪存内部只产生 4 KiB 写入。

**冷热数据分离**：f2fs 会根据更新模式给数据与 node（索引节点）标记不同温度，尽量把更新频率相近的数据放入相应 segment。这样可以降低 GC 搬移仍然有效的冷数据的概率，但这种分类属于启发式策略，不能保证热写入永远不影响冷数据。

**SQLite batch atomic write（批量原子写）**：`android-17.0.0_r1` 的 `external/sqlite/dist/Android.bp` 明确定义了 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE`。只有当 VFS 与文件系统报告相应能力、事务满足限制且采用 rollback-journal 相关路径时，SQLite 才可能通过 batch atomic write 减少 journal 工作。WAL 有自己的追加与 checkpoint 语义，不能把这项优化写成 WAL 的通用加速。设备文件系统和运行时 journal mode 都需要单独确认。

在 Perfetto 中观察到 `data` partition 上大量 `fsync()` 延迟时，应先确认 filesystem type（文件系统类型）。分析 ext4 时要关注 `jbd2`（ext4 日志线程）和 `ext4_sync_file_*` 等同步写路径；分析 f2fs 时，则要检查 writeback（脏页回写）、checkpoint 或 GC 是否与 foreground I/O 争用 device queue（设备队列）。f2fs 的 GC 多数时间在后台完成，但可用空间紧张时也会拖慢前台读写。

## Scoped Storage：权限模型与 I/O 路径变化

### 为什么需要 Scoped Storage

Android 10 之前，App 获得 `READ_EXTERNAL_STORAGE` 或 `WRITE_EXTERNAL_STORAGE` 后，可以访问共享存储（`/sdcard`）中的大部分内容。用户照片、文档和下载内容缺少按媒体集合与创建者划分的细粒度隔离，这种权限模型暴露了过多用户数据。

Android 10 引入 Scoped Storage（分区存储）。Android 10 允许应用通过兼容机制暂缓迁移；从 Android 11 开始，target API（应用声明的目标 API 级别）为 30 及以上的应用必须遵循 scoped storage。主要变化包括：

1. App 可以直接访问自己的专属目录（`Android/data/<package_name>/` 和 `Android/media/<package_name>/`），不需要申请存储权限；
2. 要访问其他 App 创建的媒体文件，通常需要通过 MediaStore，并根据 Android 版本取得媒体权限或用户选择授权；
3. 要访问 PDF、文档等非媒体文件，需要通过 Storage Access Framework（SAF，存储访问框架）让用户选择；
4. App 不能再直接写入 `/sdcard` 根目录。

### FUSE 层的性能开销

Android 11 重新引入 FUSE，作为共享外部存储执行权限策略的路径。MediaProvider 充当 userspace FUSE handler（用户态 FUSE 处理程序），可以允许、拒绝或按策略对文件访问结果进行脱敏。首发搭载 Android 11 且使用 5.4 以上内核的设备不能再使用 SDCardFS；从旧版本升级的设备则可能在 SDCardFS 上叠加 FUSE。应用内部目录 `/data/user/<user_id>/<package>/` 不在这条 FUSE 挂载路径中。

Android 11 新增了 shared media 的 direct file paths（直接文件路径）访问方式。取得相应权限后，App 可以继续使用 `File` API 或 `fopen()` 访问媒体文件，从而兼容大量第三方媒体库。这一能力解决的是 API 兼容问题，不等于天然绕过 FUSE。官方文档指出，顺序读取时 direct file path 与 MediaStore 的性能接近；随机读写时，direct file path 反而可能慢到接近 2 倍，此类场景更适合继续使用 MediaStore。

Android 12 增加了 FUSE passthrough（直通路径）。设备需要匹配的 official kernel、MediaProvider 实现与产品属性。文件通过权限与 redaction（内容脱敏）检查后，FUSE driver 可以在 `open()` 之后把后续读写直接转发到 lower file system（底层文件系统）。`android-17.0.0_r1` 的 `MediaProvider/jni/FuseDaemon.cpp` 仍会检查 `persist.sys.fuse.passthrough.enable`、内核 capability（能力支持）以及文件是否需要 redaction/transform，再决定能否启用 passthrough；源码还包含 FUSE BPF（通过内核 BPF 程序处理部分 FUSE 操作）路径。MediaStore API、Android 11 direct file path、FUSE passthrough 和 FUSE BPF 分属四个不同层次。

### 对 App I/O 行为的实际影响

Scoped Storage 会从以下几方面影响 App 开发和性能分析。

**访问共享媒体时，先按访问模式选择接口**：目录扫描、批量查询和随机读写等场景，优先使用 MediaStore 完成索引与权限判定；需要兼容旧库或 native 媒体栈时，再考虑 Android 11 的 direct file paths。

**不要把应用私有数据混入共享存储**：只在 App 内部使用的数据，放在内部存储 `/data/user/0/<package>/` 最直接。如果必须放入 external app-specific directory（外部存储中的应用专属目录），分析时也要把它与共享媒体访问分开，不能把两条 I/O 路径混成同一个模型。

**看版本边界再下结论**：同样是“共享媒体访问慢”，Android 10 要区分 MediaProvider API 与当时的 SDCardFS/设备存储模拟路径；Android 11 才由 MediaProvider FUSE 支持 direct file path；Android 12+ 设备还可能启用 passthrough。分析时先确认首发版本、MediaProvider 模块、设备内核和产品属性。

在 Perfetto trace 中，未使用 passthrough 的 FUSE 请求可能表现为 App 线程等待，并与 MediaProvider 的 FUSE worker（工作线程）活动对齐；采用 passthrough 后，后续数据读写可能不再唤醒 userspace handler。仅凭 App 的 I/O wait 无法判断请求是否经过 FUSE，还要结合 MediaProvider 日志、产品属性、内核 capability 和调用路径。

### 版本断点速查

| Android 版本 | system / 挂载模型 | shared storage 入口 | FUSE 行为 | App 侧建议 |
| --- | --- | --- | --- | --- |
| Android 9 | `system-as-root` 成为首发设备基线，rootfs 合入 `system.img` | 传统 external storage 模型 | 设备存储模拟常用 SDCardFS，也存在升级和厂商差异 | 旧项目以路径访问为主，但要为后续访问权限减少做准备 |
| Android 10 | dynamic partitions + `first-stage init` 成为新设备主路径 | Scoped Storage 引入，可通过兼容机制暂缓 | MediaProvider 执行 scoped policy；设备存储模拟仍常见 SDCardFS，direct file path 受限 | 新代码优先 MediaStore / SAF，少依赖裸路径 |
| Android 11 | `/data` 挂载流程继续沿用 Android 10 | shared media 支持 direct file paths、`File` API、`fopen()` | MediaProvider 成为 FUSE handler；升级设备可叠加 SDCardFS | 媒体库兼容可以用 direct file paths，重度随机访问优先比较 MediaStore |
| Android 12 | 挂载模型基本稳定 | API 入口与 Android 11 接近 | 首发设备配合 official kernel 可启用 FUSE passthrough | 先确认设备是否支持 passthrough，再判断瓶颈位置 |
| Android 15-17 | 挂载与共享存储主要模型延续 Android 12+ | MediaStore / direct file path 共存 | FUSE passthrough 仍取决于内核与 MediaProvider 模块版本 | 大量枚举和跨媒体库访问仍优先使用 MediaStore，模块侧优化按设备实测确认 |

## FBE：文件级加密的存储影响

### 从全盘加密到文件级加密

Android 的存储加密经历了从全盘加密（Full-Disk Encryption，FDE）到文件级加密（File-Based Encryption，FBE）的演进。FDE 在块设备层使用一套 volume key（卷密钥）保护 `userdata`，早期密码启动流程会把整卷解锁与用户凭据绑定。FBE 通过 fscrypt policy（文件系统加密策略）把不同目录树归入可以独立解锁的加密类，由此形成 DE（Device Encrypted，设备加密）与 CE（Credential Encrypted，凭据加密）存储。内容密钥是否按文件派生，还取决于 policy 版本和 inlinecrypt 优化模式。

**DE 存储**：其 class key（加密类密钥）不依赖用户凭据解锁，但仍受 KeyMint、Verified Boot 与硬件信任根保护。系统完成 Direct Boot（用户解锁前启动）所需准备后，direct-boot-aware 组件就可以访问 DE 数据。

**CE 存储**：其 class key 受用户解锁凭据和 Android 密钥保护机制约束，只有在用户解锁后才能安装。应用默认存储、用户媒体和大部分隐私数据都属于 CE。

所有首发 Android 10 及以上版本的设备都必须使用 FBE。

### metadata encryption、FBE 与 `/metadata` 的分工

“存储加密”包含三个容易混淆的层级。`/metadata` 是独立小分区，用于保存保护 metadata encryption key 的 KeyMint blobs；metadata encryption 工作在 userdata block device 层，保护目录项、inode（索引节点）、文件长度等文件系统 metadata，现代设备常见实现是 `dm-default-key` 配合 inline crypto / blk-crypto；FBE 则建立在文件系统之上，由 `vold` 在 `/data` 可以挂载后安装 DE/CE key，再由 `fscrypt` 把策略应用到不同目录。

按启动顺序观察会更清楚：系统先挂载 `/metadata`，让 `vold` 取得保护 metadata encryption key 的 key material；随后 `wait_for_keymaster` 与 `mount_all` 协作，使 `/data` 进入可挂载状态；文件系统可用后，`vold` 才继续安装 System DE、User DE 和 User CE key。`dm-default-key` 负责 `/data` block device 的 metadata 保护，不是 FBE 的别名。

### 加密的 I/O 性能影响

加密路径会增加密钥准备、crypto mapping（加密映射）和数据加解密工作，成本取决于设备是否具备 CPU crypto acceleration（加密指令加速）、inline crypto、hardware-wrapped key（硬件封装密钥）以及匹配的驱动。

inline encryption hardware（内联加密硬件）通常由 UFS 或 eMMC host controller 实现，在数据往返存储器件的路径上执行块加解密。`android17-6.18-2026-06_r6` 的 arm64 GKI 打开了 `CONFIG_BLK_INLINE_ENCRYPTION`、`CONFIG_FS_ENCRYPTION_INLINE_CRYPT`、`CONFIG_DM_DEFAULT_KEY`、`CONFIG_SCSI_UFS_CRYPTO`，也打开了 `CONFIG_BLK_INLINE_ENCRYPTION_FALLBACK`。这些配置表示内核同时具备硬件接口与软件 fallback（回退实现），但设备驱动和 fstab 仍决定运行时采用哪条路径。

Android 17 还把当前版 hardware-wrapped keys 命名为 `wrappedkey`，与旧版 `wrappedkey_v0` 区分。前者使用 android17 内核的 blk-crypto key generate/import/prepare 接口，并与 mainline Linux 方向兼容。是否启用，可从 userdata 的 fstab（文件系统挂载配置）`fileencryption=` 选项、内核日志和加密测试确认。

性能分析时不能预先忽略加密。软件 fallback 可能增加 CPU 时间；inline crypto 也会受 keyslot（硬件密钥槽）编程、host reset、队列和内存带宽影响。最小验证应包含 fstab、`dmctl table userdata`、内核配置和 `vts_kernel_encryption_test`，再把 CPU 活动与 block trace 对齐。

### FBE 的密钥层次

FBE 的密钥管理由 `vold`（Volume Daemon，存储卷守护进程）负责。密钥层次如下：

1. **System DE Key**：系统级 DE key 在启动早期安装，保护 `/data/app`、`/data/misc`、`/data/system`、`/data/vendor` 等不属于某个用户 DE/CE 类的顶层数据。
2. **User DE Key**：每个用户各有 User DE class key，用于 Direct Boot 数据，对应 `/data/misc_de/<user_id>/`、`/data/system_de/<user_id>/`、`/data/user_de/<user_id>/`、`/data/vendor_de/<user_id>/` 等。
3. **User CE Key**：每个用户的 CE class key 在用户解锁认证成功后解封并安装，用于绝大多数 App 数据，对应 `/data/user/<user_id>/`，也包括 `/data/misc_ce/`、`/data/system_ce/`、`/data/vendor_ce/` 等。

AOSP `android-17.0.0_r1` 中的关键实现路径如下：

- `system/vold/FsCrypt.cpp`：`fscrypt_prepare_user_storage()` 准备 DE/CE 目录并应用 fscrypt policy；
- `system/vold/Utils.cpp`：`BuildDataSystemDePath()`、`BuildDataMiscDePath()`、`BuildDataUserDePath()` 生成 `/data/system_de/<user>`、`/data/misc_de/<user>`、`/data/user_de/<user>` 等路径。

fscrypt policy 设置在加密目录上，并保存在文件系统 metadata 中。新建的子文件或子目录会继承父目录的加密上下文，内核再从已经安装的 master key（主密钥）派生或选择相应的内容密钥与文件名密钥。应用看到的仍是普通文件 API，解锁边界由 DE/CE class key 是否可用决定。

## Dynamic Partition 与 Virtual A/B 的存储布局

Dynamic Partition 通过 `super` 物理分区和 `dm-linear` 在运行时映射出逻辑分区。它解决的是“逻辑分区如何划分”；另一部分是 **Virtual A/B（VABC）**，负责 OTA 升级期间如何安全更新这些逻辑分区、差异数据存在哪里，以及由谁合并。

传统 A/B 会为需要无缝升级的分区保留 A/B slot（槽位）。Virtual A/B 仍会复制 bootloader 必须直接读取的物理分区，但动态分区不再常驻一套完整副本；OTA 期间只为变更部分创建 snapshot（快照），成功启动后再执行 merge（合并）。snapshot 的格式、存放位置和 merge 执行者都要按 Android 版本区分。

### Android 11：kernel COW

Android 11 引入了 Virtual A/B 的早期形态。更新差异使用 kernel COW（Copy-on-Write，写时复制）format，并由 `dm-snapshot` 提供 base partition（基础分区）与 COW 数据的组合视图。COW 数据会占用 OTA 期间的临时空间；AOSP 的空间模型把 Virtual A/B 的额外用量计入 `/data`，`super` 只需容纳动态分区本体，不再常驻一套完整 B 槽。确认新 slot 后再把变化合并进 base device。请求是否产生额外读写取决于具体操作和 merge 阶段，不能统一概括成“一次写入变成两次 I/O”。

### Android 12：compressed snapshots 与 dm-snapshot 过渡期

从 Android 12 开始，Virtual A/B 可以启用 **compressed snapshots（压缩快照）**。这一版本引入 Android COW format 和 `snapuserd`，COW 空间主要位于 `/data`，`dm-user` 让用户态组件可以处理块设备读写。但 Android 12 还不是纯 userspace merge：Android COW 仍需转换为 kernel COW format，snapshot merge 仍会用到 `dm-snapshot`。分析 Android 12 设备时，要同时观察 `snapuserd`、`dm-user` 和 `dm-snapshot`。

### Android 13+：userspace merge

Android 13 把 compressed snapshot 的 mount（挂载）与 merge 移入用户态的 `snapuserd`，移除了对 kernel COW format 和 `dm-snapshot` 的依赖。首发搭载 Android 13 及以上版本的设备默认启用 userspace merge；从旧版本升级的设备则需要显式启用。Android 17 延续这套模型：成功启动后，`snapuserd` 把 COW 操作合并进 base device；如果新 slot 未通过启动确认，系统仍保留回退能力。

下面的简图用于对比三个关键版本的 COW 与 merge 路径。

```text
Virtual A/B 存储模型演进:

Android 11(kernel COW):
  snapshot delta → dm-snapshot COW → super 内分配

Android 12(compressed snapshots 过渡期):
  snapshot delta → /data(compressed Android COW)→ dm-user + snapuserd → kernel COW / dm-snapshot merge

Android 13+(userspace merge):
  snapshot mount / merge 由 dm-user + snapuserd 执行,移除 kernel COW / dm-snapshot 依赖
```

图中 Android 12 是格式转换的过渡期，不能按 Android 13+ 的 userspace merge 解释。compressed snapshots 会使用 `/data` 的临时空间，升级完成并合并后可以回收；安装阶段的 COW 写入以及 merge 期间的底层设备流量都可能与前台 I/O 竞争。

在 Perfetto trace 中，OTA 升级期间的 Virtual A/B 活动主要集中在三组进程：

| 进程 | 角色 | Trace 特征 |
| --- | --- | --- |
| `update_engine` | 下载包、写 COW、触发 merge | 对 `/data` 中的 COW 空间产生写入流量；升级完成后停止 |
| `snapuserd` | Android 12 compressed snapshots 的 COW 读写；Android 13+ 的 userspace merge | 作为用户态 dm-user worker，持续占用 CPU 和 `/data` I/O；Android 13+ 的 merge 阶段仍然活跃 |
| 前台 App | 受影响方 | 主线程 `fsync()` / `read()` 延迟明显增加，时间与 `snapuserd` / `update_engine` 活动对齐 |

Android 13+ 的 userspace merge 大多在后台完成；Android 12 设备还要单独分析 `dm-snapshot` merge 路径。存储空间紧张或后台写入密集时，`snapuserd` 和前台 App 会争用 `/data` 的 IOPS，明显拉长前台 App 的 I/O 等待。

## 存储寿命与写入放大

NAND 闪存单元只能承受有限次数的 program/erase cycle（编程/擦除循环）。SLC、MLC、TLC、QLC 每个单元存储的位数不同，耐久度趋势也不同；同一类型还会因工艺、纠错、预留空间和厂商分级产生很大差异。手机存储器件也常使用动态 SLC cache、磨损均衡和 over-provisioning（预留空间），不能用一组固定擦写次数估算所有设备的寿命。

**写入放大（Write Amplification Factor，WAF）**通常指 NAND 实际写入量与 host write（主机写入量）之比。应用写入 4 KiB，不代表 NAND 只会 program 4 KiB：文件系统更新、数据库日志、F2FS GC、FTL 垃圾回收和磨损均衡都可能搬移额外数据。具体 WAF 需要器件计数器或厂商遥测支持，不能根据一次文件写入和固定 erase block（擦除块）大小直接计算。

写入放大的常见来源包括：

- **垃圾回收（GC）**：闪存不能就地覆盖写入，必须先擦除再写。当空闲 block 不足时，控制器需要把仍然有效的数据从一个 block 搬到另一个 block，再擦除旧 block。这些数据搬移会产生额外写入。
- **磨损均衡（Wear Leveling）**：控制器会尽量让各个 block 的擦写次数均匀分布，避免部分 block 过早失效；这一过程也可能搬移数据。
- **文件系统与应用写入模式**：小事务、频繁 checkpoint、临时文件重写和文件系统 GC 会改变 host request 形态，FTL 再把逻辑地址映射到物理 NAND。

可用空间下降时，文件系统和 FTL 可选择的空闲区域减少，GC 更容易进入前台路径，尾延迟和 WAF 都可能上升。设备使用时间只是相关变量；应用数据增长、温度、后台任务、OTA merge、器件固件和电池策略也会改变性能，不能把“用久变慢”直接归因于闪存老化。

应用侧可以合并状态更新、避免无变化重写、控制日志与缓存规模，并把持久化移出关键交互路径。`SharedPreferences.apply()` 只是把调用方等待改成异步写回，最终仍会写入 XML；它不能减少写入量，进程生命周期结束时还可能等待未完成的 queued work（排队写入）。若目标是降低 WAF，应先减少写入次数和字节量，再讨论使用同步还是异步 API。

## 常见问题与误区

**“手机变慢是因为闪存老化了吗？”**

单凭使用年限无法判断。应同时查看可用空间、器件寿命指标、后台写入、温度、文件系统 GC、I/O 错误与同机型基线。闪存磨损可能参与性能下降，也可能只是应用数据和并发负载增加。

**“f2fs 一定比 ext4 快吗？”**

没有跨设备的固定答案。f2fs 的 out-of-place update、冷热分离和 segment 管理适合部分闪存工作负载，ext4 的成熟日志与分配策略也可能在另一些负载上更稳定。两者都受 mount option（挂载选项）、内核版本、可用空间、GC、checkpoint、设备 cache 与 flush 语义影响。结论应来自目标机型的 p50/p95/p99（第 50/95/99 百分位）延迟、吞吐、CPU 和写入量，而非“低于 80%”一类没有源码依据的阈值。

**“FBE 加密会拖慢存储性能吗？”**

在支持 inline encryption 的设备上，FBE 额外带来的 CPU 成本通常不大；如果设备缺少这类硬件能力，软件加密会让 CPU 承担一部分加解密工作。排查时不能只问“FBE 会不会慢”，还要检查 `dm-default-key` 是否启用、`vold` / kernel 日志中是否出现解锁重试，以及块层等待是否与加密阶段重合。

## 存储问题观测地图

I/O 诊断至少需要覆盖以下五层，避免停在“看起来像 I/O 慢”的直觉判断。

| 关注面 | 推荐抓取点 | 重点看什么 | 异常形态 |
| --- | --- | --- | --- |
| Block layer | Perfetto 的 `ftrace`（内核跟踪）事件 `block_rq_issue`、`block_rq_complete` | 单次请求从 issue 到 complete 的时延、队列是否堆积 | 前台线程卡在 `fsync()` / `read()`，同时块请求完成时延持续增加 |
| ext4 / f2fs | `ext4_sync_file_*`、`f2fs_sync_file_*`、内核回写线程 | 同步写是否集中出现在事务提交或 checkpoint 前后 | `fsync()` 时间长，并伴随 `jbd2`、f2fs checkpoint 或 GC 活动 |
| Shared storage / FUSE | App 线程、`MediaProvider`、`fuse` 相关进程或线程 | App I/O wait 是否与用户态转发、权限检查同时发生 | 目录扫描或批量访问媒体时，App 与 `MediaProvider` 的 CPU 和 I/O 等待同时增加 |
| Mount / encryption | 开机阶段的 `init`、`vold`、`wait_for_keymaster` 日志与 trace slice（事件区间） | `/metadata` 是否已挂载、`vold` 是否提前启动、`mount_all` 是否卡住 | 开机早期反复重试 KeyMint，`/data` 长时间无法挂载，后续 I/O 全部受到影响 |
| OTA merge | `update_engine`、`snapuserd`、Virtual A/B merge 相关后台写入 | OTA 后台 merge 是否仍在持续、前台 I/O 是否受到挤压 | 重启后长时间存在稳定写入流量，前台 App 随机 I/O 延迟异常 |

除 Perfetto 外，还应结合 `logcat`、`dmesg`、`mount`、`getprop` 交叉验证。存储问题经常横跨内核、init、`vold`、MediaProvider 和 App 线程，单看一层容易偏离根因。

## 从存储架构定位性能问题

主线程在 `fsync()` 上等待时，可以按以下顺序分析：

1. **调用层**：确认谁调用了 `fsync()`、同步的是哪个文件，以及这一同步点是否必须位于主线程。
2. **文件系统层**：确认 ext4/f2fs、mount option，并检查 jbd2、checkpoint、writeback 或 GC 是否与等待区间重合。
3. **块设备层**：检查 active I/O scheduler、request issue-to-complete（请求下发到完成）延迟、队列堆积和后台写入。
4. **映射与加密层**：读取 device-mapper table 与 fstab，确认 dm-default-key、snapshot、inline crypto 或软件 fallback。
5. **共享存储层**：涉及 `/storage/emulated` 时，核对 MediaProvider/FUSE、passthrough、权限检查与 redaction。
6. **器件层**：记录 UFS/eMMC 型号、MCQ、可用空间、温度和设备健康信息，用同机型基线解释数据。

按这套顺序，Perfetto 中的“I/O wait”才能继续收敛到同步点、文件系统、块队列、共享存储或器件层面的可验证原因。

第 6.2 节继续分析文件系统选择、I/O 调度和调优；存储与内存压力共同放大卡顿的案例见第 7.2 节。

## 参考资料

- **手机 Android 存储性能优化架构分析** - Linux 阅码场，系统梳理了 Android 存储 I/O 路径和 ext4/f2fs 的性能差异
- **手机主流存储器件的分析与发展** - OPPO 内核工匠，介绍 eMMC/UFS 架构对比与 UFS 4.0 MCQ 特性
- **Android 分区挂载原理介绍** - OPPO 内核工匠，介绍 Dynamic Partition、dm-linear 与 FBE 密钥层次
- **[Partition layout | AOSP](https://source.android.com/docs/core/architecture/partitions/system-as-root)** - Android 9/10 system-as-root 语义与 first-stage init 边界
- **[Scoped storage | AOSP](https://source.android.com/docs/core/storage/scoped)** - Android 11 MediaProvider/FUSE、direct file path 与性能边界
- **[FUSE passthrough | AOSP](https://source.android.com/docs/core/storage/fuse-passthrough)** - Android 12+ passthrough 的内核、产品属性和验证方式
- **JEDEC UFS 4.0 Standard (JESD220E)** - UFS 设备接口与协议能力；MCQ 还需结合 UFS Host Controller Interface 规范和主控实现
- **Android Common Kernel `android17-6.18-2026-06_r6`** - `drivers/ufs/core/ufs-mcq.c`、arm64 GKI defconfig、ext4/f2fs、blk-crypto 与 dm-default-key 实现
- **AOSP `android-17.0.0_r1`** - `system/core/libprocessgroup/profiles/`、`system/vold/FsCrypt.cpp`、`packages/providers/MediaProvider/jni/FuseDaemon.cpp`、`external/sqlite/dist/Android.bp`
- **[Virtual A/B overview | AOSP](https://source.android.com/docs/core/ota/virtual_ab)** - Android 11 kernel COW、Android 12 格式转换、Android 13+ userspace merge 的官方版本边界
- **[File-based encryption | AOSP](https://source.android.com/docs/security/features/encryption/file-based)** / **[Metadata encryption | AOSP](https://source.android.com/docs/security/features/encryption/metadata)** - DE/CE、KeyMint、`dm-default-key`、inline encryption 与 `/metadata` 启动依赖
