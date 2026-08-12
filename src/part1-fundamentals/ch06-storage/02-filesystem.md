---

title: 文件系统
chapter: '6.2'
section: '6.2'
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-04-23'
last_verified_against: AOSP EROFS docs + source.android 16KB page size docs + kernel/common android15-6.6 ext4 journal / f2fs segment,gc,uapi/linux/f2fs.h,include/linux/f2fs_fs.h + developer.android.com
confidence: medium
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
status: finalized
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
---

# 6.2 文件系统

## 先把 `fsync` 卡顿放回完整 I/O 路径

Perfetto 中偶尔会看到主线程进入不可中断睡眠，调用栈停在 `fsync()`、`fdatasync()` 或文件关闭附近。这个现象只能说明线程在等待持久化路径完成，不能只凭一个 syscall 就认定文件系统存在缺陷。

一次同步写可能经过这些层次：

1. App 或数据库提交修改。
2. VFS 把脏页交给 ext4 或 F2FS。
3. 文件系统写数据、必要的元数据和恢复信息。
4. 块层处理请求合并、调度、加密与 device-mapper 映射。
5. UFS 控制器和设备内部 FTL 完成写入与缓存刷新。

`fsync()` 的返回语义还受挂载参数、写屏障以及存储设备对 flush/FUA 的实现影响。文件系统会改变其中一部分成本，却无法消除器件尾延迟、温度降频、磨损控制或队列拥塞。

SQLite 也不等于“每执行一条 SQL 就调用一次 `fsync()`”。同步次数取决于事务边界、journal 模式、`PRAGMA synchronous`、是否发生 cache spill，以及文件系统是否提供 SQLite 能识别的原子批写能力。SharedPreferences 的 `apply()` 会先更新内存并把磁盘写入排到后台；它减少调用线程的直接等待，但排队的写入仍可能在组件生命周期切换时参与 ANR。

> 源码锚点：Android 17 / API 37 / `android-17.0.0_r1`，Android Common Kernel `android17-6.18-2026-06_r6`。

## VFS 与 Page Cache：统一接口不代表相同行为

VFS 用 `super_block`、`inode`、`dentry` 和 `file` 等对象向上提供统一接口。App 调用相同的 `open()`、`read()`、`write()` 和 `fsync()`，VFS 再分发到具体文件系统的 `file_operations`、`address_space_operations` 等实现。

普通缓冲 I/O 的 `write()` 通常先修改 Page Cache，页面随后被标记为 dirty。内核回写线程可以异步提交这些页面；`fsync()` 则要求指定文件在相应范围内达到持久化语义，所以调用者可能需要等待：

- 文件数据写回；
- 影响文件可读性的元数据更新；
- journal、F2FS node 或 checkpoint 等恢复信息；
- 块设备 cache flush。

Page Cache 命中会掩盖很多读取差异。分析随机读时，应先区分缓存命中、缺页读取和存储设备读取，避免把内存速度记到文件系统名下。

## ext4：成熟的通用读写文件系统

### ext4 解决了哪些问题

ext4 在 Android 17 的 arm64 GKI 中仍为内建能力：`CONFIG_EXT4_FS=y`。它并未退出 Android，也不应被概括为“不适合手机”。设备可以根据分区职责、升级方案、故障恢复经验和性能目标选择 ext4。

几个重要机制如下：

- **extent**：用连续区间描述物理块，降低大文件块映射的元数据量。
- **delayed allocation**：缓冲写入阶段可以暂缓物理块分配，给多块分配器更多机会形成连续布局。
- **multiblock allocator**：批量选择连续空闲块。
- **jbd2 journal**：记录一致性所需的文件系统修改。常见 `data=ordered` 模式主要记录元数据，并要求相关数据先于元数据提交完成。
- **fast commit**：条件允许时只记录较小的增量；遇到不支持的操作会回退到完整 journal commit。

“就地更新”描述的是 ext4 的逻辑块分配倾向。NAND 的物理擦除、搬移和磨损均衡由 UFS/eMMC 内部 FTL 处理，文件系统看不到固定的 NAND erase block。把每次 ext4 小写都描述成一次固定大小的“读—改—擦—写”并不准确。

### Android 17 内核中的 ext4 `fsync`

下面的源码片段用于说明 ext4 同步文件时等待了哪些对象，摘自 `fs/ext4/fsync.c`：

```c
ret = file_write_and_wait_range(file, start, end);
if (ret)
        goto out;

ret = ext4_fsync_journal(inode, datasync, &needs_barrier);

if (needs_barrier)
        err = blkdev_issue_flush(inode->i_sb->s_bdev);
```

这条路径先提交并等待目标文件范围的数据，再等待对应 journal 事务；需要写屏障时还会发出块设备 flush。`ext4_fsync_journal()` 对普通文件尝试 `ext4_fc_commit()`，能否使用 fast commit 由文件系统特性和本次修改类型共同决定。

因此，ext4 的一次 `fsync()` 可能等待同一 journal transaction 中的其他工作，但不能扩写成“等待所有进程的脏数据”或“每次都做完整 checkpoint”。诊断时应同时看 `ext4_sync_file_enter/exit`、jbd2 commit 和块层事件。

## F2FS：围绕闪存负载组织写入

### LFS 思路与 F2FS 的修正

F2FS 基于 log-structured file system 思路，目标是减少随机覆盖写，并控制经典 LFS 的 wandering tree 与清理成本。Android 17 的 arm64 GKI 启用了：

- `CONFIG_F2FS_FS=y`
- `CONFIG_F2FS_FS_COMPRESSION=y`
- `CONFIG_F2FS_FS_SECURITY=y`

F2FS 的关键磁盘结构可以这样理解：

- **NAT（Node Address Table）**：把 `nid` 映射到最新 node block 的物理地址。inode、direct node 和 indirect node 都属于 node。
- **SIT（Segment Information Table）**：记录 segment 中有效块数量、有效位图和类型信息，供分配与 GC 使用。
- **SSA（Segment Summary Area）**：保存 segment 内块的归属摘要，GC 可据此回查块是否仍有效。
- **Checkpoint**：保存一组可恢复的一致状态。双 checkpoint pack 让挂载恢复可以选择有效版本。
- **多路 active logs**：按 node/data、冷热等类别分配写入，尽量降低 GC 搬移有效块的成本。

NAT 只负责 `nid → node block address`。文件数据块地址位于 inode 或其他 node 的地址数组中。把 NAT 说成“文件逻辑块到数据块的直接映射”会漏掉 F2FS 解决 wandering tree 的关键层。

### F2FS 并非所有写入都永远顺序追加

默认 adaptive 模式会在 LFS 分配与 SSR（Selective Segment Reuse）之间选择。空间宽裕时，out-of-place update 更容易保持追加式写入；空间紧张时，SSR 可以复用已用 segment 中的空洞。挂载为 `mode=lfs` 时，主区域不使用随机覆盖分配，代价是需要更多连续空闲空间。

F2FS 还存在 IPU（in-place update）路径。例如 Android 17 内核的 `f2fs_do_sync_file()` 会在 `fdatasync()` 或脏页较少时设置 `FI_NEED_IPU`，随后执行范围写回。因此，“F2FS 的每一次数据修改都是 CoW”属于过度简化。

当前 `f2fs_need_SSR()` 的判断包含几条清晰边界：

- `mode=lfs` 直接禁用 SSR；
- `GC_URGENT_HIGH` 或 checkpoint disabled 状态需要 SSR；
- 常规模式比较 free sections 与 dirty node/dentry/inode metadata、`min_ssr_sections`、reserved sections 的需求。

这里的单位是 section，阈值来自运行时状态和格式参数，没有一个适用于所有设备的固定百分比。

### `fsync`、roll-forward 与 checkpoint

F2FS 的常见 `fsync` 路径先写回目标文件数据，再判断是否需要 checkpoint。普通可 roll-forward 的情况会写带 fsync 标记的 node 链并发出必要的 flush；以下情况可能转入完整 checkpoint，包括非普通文件、压缩文件、硬链接、超级块明确要求 checkpoint 等。

短路径可以减少恢复信息和等待范围，但仍需满足掉电恢复语义。设备 cache flush、node writeback、checkpoint 以及 GC 都可能成为尾延迟来源，所以“F2FS 上的 `fsync` 没有成本”是错误结论。

### 原子文件写与 Android SQLite

Android 17 内核在 `include/uapi/linux/f2fs.h` 中定义了：

- `F2FS_IOC_START_ATOMIC_WRITE`
- `F2FS_IOC_COMMIT_ATOMIC_WRITE`
- `F2FS_IOC_ABORT_ATOMIC_WRITE`
- `F2FS_IOC_START_ATOMIC_REPLACE`

`f2fs_ioc_start_atomic_write()` 会为普通文件准备 COW inode；commit 路径调用 `f2fs_commit_atomic_write()`，随后以 atomic 语义同步文件，失败或结束后再清理原子写状态。这里的“原子”指一批文件页修改在崩溃恢复时全有或全无，并不表示写入没有 I/O 等待。

Android 17 的 AOSP SQLite 在 `external/sqlite/dist/Android.bp` 中启用了 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE`。Unix VFS 只有在 `F2FS_IOC_START_ATOMIC_WRITE` 探测成功后才报告 `SQLITE_IOCAP_BATCH_ATOMIC`，SQLite pager 还会检查数据库状态和事务条件。编译期开关提供了使用机会，不能据此推断每个 SQLite 事务都走 F2FS 原子写。

### GC：空间紧张时为什么会抬高尾延迟

out-of-place update 会留下无效块。F2FS 需要选择 victim segment，核对其中仍有效的数据与 node，然后搬移有效块以释放 segment。后台 GC 可利用空闲窗口；当写入路径发现可用 section 不足时，请求线程可能参与或等待空间回收。

Android 17 的判定已经不同于旧版 kernel 6.6 的 lower/upper 阈值写法。下面的摘录用于固定当前 6.18 源码中的比较对象，来自 `fs/f2fs/segment.h`：

```c
free_secs = free_sections(sbi) + freed;
required_secs = needed + reserved_sections(sbi) +
                __get_secs_required(sbi);

return free_secs < required_secs;
```

`__get_secs_required()` 会把 dirty node、dentry、inode metadata，以及特定模式下的 dirty data 换算为所需 section。`f2fs_balance_fs()` 在空间足够时直接返回；空间不足时，它可以唤醒启用 `gc_merge` 的 GC 线程并等待，也可以调用 `f2fs_gc()` 释放 section。普通后台 victim 策略可使用 cost-benefit 或 age-threshold，前台 GC 使用 greedy 选择逻辑。

这也解释了“剩余容量尚未显示为 0，写入已经变慢”的现象：文件系统要保留可完成写回、checkpoint 和 GC 搬移的工作空间；UFS 自身也需要预留块进行 FTL 回收。两层空间压力可能同时出现。

### 4 KB 与 16 KB 页大小

Android 15 开始支持 16 KB page size，Android 17 继续支持 4 KB 与 16 KB 设备。ELF 的 16 KB 对齐兼容性和 F2FS 磁盘格式是两件事：

- AOSP 用户空间可以构建为 page-size agnostic，ELF 以 16 KB 对齐后可在 4 KB/16 KB kernel 上运行。
- `android17-6.18-2026-06_r6` 的 `include/linux/f2fs_fs.h` 明确规定 `F2FS_BLKSIZE == PAGE_SIZE`。
- 同一源码中的默认 segment 仍含 512 个 block，因此 4 KB 页时默认 segment 为 2 MB，16 KB 页时为 8 MB。

16 KB kernel 使用的 F2FS 格式参数需要按 16 KB block 生成。设备升级是否能够保留 `/data`，取决于 OEM 的分区、迁移和升级方案，不能仅从 App 的 ELF 兼容结论推导出“旧 4 KB `/data` 可原样挂载”。App 工程师需要修复 native library 对页大小的硬编码；格式化与用户数据迁移由设备实现负责。

### quota、casefold 与 fscrypt

F2FS 和 ext4 都可以承载 Android 所需的配额、大小写无关目录与文件加密能力，但可用性取决于内核配置、文件系统 feature、格式化参数和挂载参数：

- project quota 可帮助系统按目录项目统计或限制空间；看到 `CONFIG_QUOTA=y` 不代表目标分区已经启用 `prjquota`。
- casefold 使用 Unicode 规则进行大小写无关查找；只有带相应 feature 且目录被设置为 casefold 时才生效。
- fscrypt 提供文件级加密策略，Android 的 FBE 在其上组织 DE/CE 密钥域。
- inline encryption 可以把数据加解密交给存储控制器，但文件系统仍负责密钥上下文与 bio 标记。

检查设备行为时，应读取实际 superblock feature、mount options 和内核配置，不能只看文件系统类型。

## EROFS：面向不可变镜像的只读文件系统

### 适用边界

EROFS 没有运行时写入、journal 和空闲块分配路径，适合 `system`、`vendor`、`product`、`system_ext` 等构建期生成、启动后只读的镜像。`/data` 需要创建和修改文件，不能使用 EROFS。

AOSP 的 EROFS 文档给出了 BoardConfig、fstab、压缩和 Virtual A/B 配置。文档中的示例允许为 `/system` 同时保留 EROFS 与只读 ext4 fstab 条目，以便测试 ext4 GSI。这说明 Android 提供了完整支持，具体分区采用哪一种格式仍由产品配置决定。

EROFS 的核心能力包括：

- compact/extended inode 布局与 tail packing；
- 可选透明压缩；
- in-place decompression，减少额外解压缓冲与 Page Cache 抖动；
- chunk-based 与 rolling-hash 压缩数据去重；
- 面向随机访问的索引设计。

AOSP 当前构建文档的默认 compressor 是 `lz4hc`，也允许禁用压缩和调整 PCluster 大小。官方给出的镜像体积数据是平均约缩小 25%，高压缩配置可到约 45%；这组数据只适合说明文档测试范围，不能换算为任意设备的启动耗时。

Android 17 的 6.18 arm64 GKI 已启用 `CONFIG_EROFS_FS=y`、`CONFIG_EROFS_FS_ZIP_ZSTD=y` 和 `CONFIG_EROFS_FS_PCPU_KTHREAD=y`。所以 ZSTD 在这个源码锚点中具备内核解压支持；镜像是否使用 ZSTD 仍由产品构建配置决定，且 6.18 Kconfig 仍把该能力标为 experimental。LZ4HC 依然是 AOSP EROFS 构建文档中的默认选择。

### EROFS、dm-verity 与 Virtual A/B

EROFS 负责解释只读文件和压缩数据，dm-verity 负责校验块完整性，AVB/vbmeta 提供受信任的根摘要与签名信息。正常挂载时，常见的简化层次是：

1. `super` 物理分区；
2. `dm-linear` 映射出的动态逻辑分区；
3. `dm-verity` 校验设备；
4. EROFS 或只读 ext4；
5. `/system` 等挂载点。

dm-verity 按需读取哈希树并验证数据，不会在每次挂载时重算整棵树。哈希算法、数据块大小和错误策略来自 AVB descriptor 与设备配置，不能固定写成“所有设备每块都用 4 KB SHA-256”。

Virtual A/B OTA 合并期间还可能插入 `dm-user`/`snapuserd` snapshot 层。AOSP 从 Android 13 起完整支持 EROFS 与 Virtual A/B，并能在生成增量 OTA 时理解 LZ4 数据流。EROFS 镜像压缩和 Virtual A/B snapshot 压缩属于不同层次：前者缩小只读文件系统镜像，后者缩小更新时暂存的 COW 数据。

## 文件系统如何影响随机 I/O

下表比较的是机制与风险点，不是脱离设备和负载的性能排名：

| 场景 | ext4 | F2FS | EROFS |
|---|---|---|---|
| 缓冲随机读 | Page Cache + extent 映射 | Page Cache + node/NAT 映射 | Page Cache + 压缩索引与解压 |
| 随机写 | delayed allocation、extent 分配、journal | OPU/IPU、LFS/SSR、node 更新 | 不支持 |
| 同步提交 | 数据写回 + journal/fast commit + 必要 flush | 数据写回 + roll-forward node 或 checkpoint + 必要 flush | 不支持写入 |
| 空间回收 | 空闲 extent 管理、discard | segment GC、SSR、discard | 构建期生成镜像 |
| 主要尾延迟来源 | journal 竞争、块分配、flush、器件延迟 | GC/checkpoint、flush、器件延迟 | cache miss、压缩块读取与解压、verity、器件延迟 |

随机写成本来自多个层次。文件系统决定逻辑块如何分配，块层决定请求如何提交，FTL 决定 NAND 页如何搬移与回收。F2FS 尝试向 FTL 提供更有规律的写入并分离冷热数据，但双层日志式管理也可能叠加写放大。哪种文件系统更快，需要在同机型、同镜像、同挂载参数和同工作集下测量 P50/P95/P99 延迟。

## `fsync()` 与 `fdatasync()`：差别在持久化范围

POSIX 语义可以简化为：

- `fsync(fd)`：同步文件数据，以及恢复该文件状态所需的元数据。
- `fdatasync(fd)`：可以跳过不影响后续数据读取的元数据，例如仅修改时间戳；文件大小变化仍需持久化。

`fdatasync()` 不保证“固定少一次元数据写”，两者最终走到哪些写回和 flush，取决于文件修改类型与文件系统实现。Android 17 的 F2FS 甚至会在 `fdatasync()` 路径设置 `FI_NEED_IPU`，所以 syscall 名称不足以估算成本。

SQLite 在 rollback journal、WAL 和不同 `synchronous` 配置下会安排不同的同步操作。要求断电恢复的安全配置需要保留相应同步保证；修改 pragma 换性能前，需要先定义允许丢失多少数据、是否允许数据库损坏。业务层最稳妥的优化通常是减少事务数量和主线程等待，而非关闭同步保证。

### App 侧能做的事

1. **批量提交数据库修改**：把同一业务动作的多条写入放在一个明确事务中，避免循环内反复提交。Room 可以用 `@Transaction` 或批量 DAO 方法表达边界。
2. **谨慎选择 WAL**：WAL 通常改善读写并发，但仍有 WAL sync、checkpoint 和文件增长成本。用目标 workload 验证，别把它当作免同步开关。
3. **避免主线程等待持久化**：文件写、数据库事务和 `SharedPreferences.commit()` 不应占用 UI 关键路径。
4. **理解 `SharedPreferences.apply()` 的限制**：它会立即更新进程内视图并异步写磁盘；连续 `apply()` 仍产生磁盘工作，生命周期切换可能等待排队任务。
5. **合并小文件更新**：频繁创建、rename、删除小文件会增加目录与 inode 元数据修改。可在保持崩溃一致性的前提下合并更新频率。

### 如何定位

下面的命令用于确认目标挂载点的文件系统与关键挂载参数：

```bash
adb shell cat /proc/mounts
adb shell stat -f -c '%T %s' /data
adb shell getconf PAGE_SIZE
```

第一条显示实际 mount options，第二条显示 `/data` 的文件系统类型和基本块大小，第三条确认运行内核的页大小。`stat` 的基本块大小不能代替对 F2FS on-disk feature 的完整检查。

Perfetto/ftrace 中可以按设备开放情况观察：

- `ext4_sync_file_enter` / `ext4_sync_file_exit`
- `f2fs_sync_file_enter` / `f2fs_sync_file_exit`
- F2FS GC 与 checkpoint 事件
- `block_rq_issue` / `block_rq_complete`
- UFS host controller、device-mapper 和 writeback 事件

先用 sync_file 的 enter/exit 确认文件系统层等待，再看时间是否消耗在 writeback、journal/checkpoint、GC、块队列或设备完成阶段。不要用统一的 10 ms 阈值判定所有设备；应与同机型正常场景的分位数比较。

## 厂商选型：以设备事实为准

Android 没有规定所有厂商的 `/data` 必须使用 F2FS，也没有规定所有只读动态分区必须使用 EROFS。AOSP 和 GKI 提供能力，产品还要结合：

- launch/upgrade 路径与 Virtual A/B 方案；
- UFS 特性、容量与 FTL 行为；
- 4 KB/16 KB kernel 选择；
- FBE、metadata encryption、quota 和 casefold 需求；
- 故障恢复、量产工具和售后升级成本；
- 厂商内核回移植与测试覆盖。

同一品牌的不同 SoC、地区版本和代际也可能不同。文章或发布会信息只能当作线索，现场问题应以 `/proc/mounts`、fstab、superblock 与 build config 为准。

## 碎片化与长期性能变化

ext4 和 F2FS 都会出现布局不连续，只是形成方式和维护机制不同。

ext4 的空闲空间可能随着文件创建、扩展、截断和删除而分散。extent 与 delayed allocation 能缓解碎片，但无法保证长期使用后所有文件仍连续。闪存没有机械寻道，碎片仍可能增加 bio 数量、削弱 readahead 和请求合并。

F2FS 的更新会产生旧无效块，GC 再搬移 victim 中的有效块。冷热数据混放、空闲 section 少或后台 GC 缺少运行窗口时，需要搬移的有效数据增多，前台分配更容易等待。F2FS 也可能出现文件逻辑块映射到分散物理地址的情况，因此“F2FS 没有文件碎片”不成立。

保持空闲空间通常有利于文件系统和 FTL 回收，但不存在跨设备统一适用的“至少 10%”安全线。系统开发者应结合 `/sys/fs/f2fs/<dev>/` 统计、GC trace、块层延迟和产品容量策略建立阈值；普通 App 不应依赖 root 工具定期对用户设备强制 defrag。

恢复出厂设置会重建或清空用户数据，短期内改变空间与布局状态。它无法修复持续制造高频小写、无边界缓存或过多事务提交的业务模式。

## 版本脉络：保留能力边界，不推导统一选型

| 版本阶段 | 可确认的变化 |
|---|---|
| 早期 Android | 设备曾使用 YAFFS2、ext4 等多种格式；“Android 从诞生起所有分区都用 ext4”不成立。 |
| Android 8–12 | F2FS 原子写 ioctl 与 SQLite 适配进入 Android 设备软件栈；是否使用仍需运行时探测与事务条件满足。 |
| Android 10–12 | F2FS、ext4 继续用于可写分区；动态分区与 Virtual A/B 改变系统镜像的映射和更新方式。 |
| Android 13 | AOSP 文档明确 EROFS 完整支持 Virtual A/B，EROFS 成为只读分区的产品选项。 |
| Android 15 | AOSP 支持 16 KB page size；文件系统格式、kernel page size 与 native ELF 对齐需要分别检查。 |
| Android 16 | AOSP 增加预编译 ELF 最大页大小检查等迁移工具，16 KB 兼容要求继续变严。 |
| Android 17 | 平台锚点为 API 37 / `android-17.0.0_r1`；6.18 arm64 GKI 同时启用 ext4、F2FS、EROFS，并启用 EROFS ZSTD 解压能力。 |

这条时间线描述 AOSP 能力，不代表每台上市设备在相同版本都采用相同格式。版本分析还要结合设备是 launch 还是 upgrade，以及 vendor kernel 和产品配置。

## 常见误区

### “F2FS 一定比 ext4 快”

F2FS 对闪存随机更新做了有针对性的设计，空间紧张时又可能付出 GC 和 checkpoint 成本。ext4 的 journal 可能抬高同步提交延迟，fast commit、工作集和设备 flush 行为也会改变结果。文件系统名只能帮助建立假设，结论来自同条件测量。

### “EROFS 自带 dm-verity”

EROFS 提供只读文件系统语义和压缩访问；dm-verity 是独立的 device-mapper 完整性层。Android 常把两者叠加使用，EROFS 镜像也可以在没有 dm-verity 的其他 Linux 场景挂载。

### “`apply()` 已经消除了 SharedPreferences I/O”

`apply()` 把磁盘阶段移出当前调用点，写入仍会发生。Android API 文档明确提醒，排队写入可能在组件生命周期切换时引发 ANR。高频配置更新应先合并和限频。

### “`fsync()` 慢就换文件系统”

App 无法在运行时把 `/data` 从 ext4 切换为 F2FS；这需要设备级格式化、升级和数据迁移设计。发现慢同步后，应先确认调用者、事务边界、文件系统内部等待和设备 I/O，再决定 App、framework、kernel 或产品分区层的修改。

## 参考资料与源码锚点

### Android 17 / kernel 6.18 源码

- `kernel/common/fs/ext4/fsync.c`：`ext4_sync_file()`、fast commit 与 flush。
- `kernel/common/fs/f2fs/file.c`：`f2fs_do_sync_file()`、atomic write ioctls。
- `kernel/common/fs/f2fs/segment.h`：`__get_secs_required()`、`has_not_enough_free_secs()`。
- `kernel/common/fs/f2fs/segment.c`：`f2fs_need_SSR()`、`f2fs_balance_fs()`。
- `kernel/common/fs/f2fs/gc.c`：BG/FG GC 与 victim policy。
- `kernel/common/include/linux/f2fs_fs.h`：F2FS block/page、NAT、SIT 磁盘结构。
- `kernel/common/include/uapi/linux/f2fs.h`：F2FS ioctl ABI。
- `kernel/common/fs/erofs/`、`kernel/common/fs/erofs/Kconfig`：EROFS 与压缩算法支持。
- `kernel/common/arch/arm64/configs/gki_defconfig`：Android 17 arm64 GKI 文件系统配置。
- `external/sqlite/dist/Android.bp` 与 `dist/sqlite-autoconf-*/sqlite3.c`：SQLite batch atomic write 编译选项与 F2FS 探测。

### 官方文档

- [AOSP EROFS](https://source.android.com/docs/core/architecture/kernel/erofs)
- [AOSP 16 KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)
- [AOSP Virtual A/B](https://source.android.com/docs/core/ota/virtual_ab)
- [Android SharedPreferences.Editor](https://developer.android.com/reference/android/content/SharedPreferences.Editor)
- [Linux F2FS documentation](https://www.kernel.org/doc/html/latest/filesystems/f2fs.html)
- [Linux ext4 documentation](https://www.kernel.org/doc/html/latest/filesystems/ext4/index.html)
- [Linux EROFS documentation](https://www.kernel.org/doc/html/latest/filesystems/erofs.html)
- [Linux VFS documentation](https://www.kernel.org/doc/html/latest/filesystems/vfs.html)
- [SQLite Atomic Commit](https://www.sqlite.org/atomiccommit.html)

## 小结

遇到同步写卡顿时，可以按四个问题推进：

1. 谁发起了同步，事务或配置更新是否过于频繁？
2. `/data` 使用 ext4 还是 F2FS，页大小和挂载参数是什么？
3. 时间消耗在数据回写、journal/fast commit、F2FS node/checkpoint/GC，还是块设备 flush？
4. 问题属于 App 调用方式、系统服务、文件系统策略，还是 UFS/FTL 尾延迟？

ext4 是成熟的通用读写文件系统；F2FS 用 segment、NAT/SIT、冷热日志和 GC 适配闪存更新负载；EROFS 服务于构建期生成的只读镜像。它们的职责与代价不同。Android 17 同时保留三者的内核能力，产品配置和现场证据决定该分析哪一条路径。

下一节（6.3）会继续向下进入块层 I/O 调度，解释文件系统生成的 bio 如何变成设备请求。
