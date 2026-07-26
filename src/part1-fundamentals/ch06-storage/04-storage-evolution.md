---
status: "finalized"
title: 存储相关的版本演进
chapter: '6.4'
section: '6.4'
applicable_versions: Android 4.4 (API 19) - Android 17 (API 37)
last_verified: '2026-04-14'
last_verified_against: Android storage docs / Photo Picker docs / Android 14 partial
  photo access docs / UFS 4.0 spec
confidence: medium
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
sources:
- type: official
  path: https://source.android.com/docs/core/storage
- type: blog
  path: https://developer.android.com/about/versions/11/privacy/storage
- type: blog
  path: https://developer.android.com/training/data-storage/shared/media
- type: official
  path: https://developer.android.com/training/data-storage/shared/photopicker
- type: official
  path: https://developer.android.com/about/versions/14/changes/partial-photo-video-access
- type: aosp
  path: fs/f2fs/ in kernel
- type: blog
  path: 'OPPO内核工匠: 手机主流存储器件的分析与发展'
- type: blog
  path: 'Linux阅码场: 手机Android存储性能优化架构分析'
tags:
- storage
- FUSE
- SDCardFS
- Scoped-Storage
- EROFS
- UFS
- f2fs
- MediaStore
related_chapters:
- '6.1'
- '6.2'
- '6.3'
- '1.6'
drafted_date: '2026-04-01'
drafted_by: openclaw-task2a
reviewed_date: "2026-06-05"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: reviewed
task9_result: auto-fixed
task2b_result: fixed
last_task2b_at: '2026-06-04T22:53:28+08:00'
task2b_state: fixed
task9_reviewed_date: "2026-06-05"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-05T16:21:00+08:00"
task9_review_notes: "2026-06-05 Task9 auto-fix: 修正 eMMC 5.1 Command Queuing、EROFS Android 13 口径，并将 Android 16 SDM 云端编译段降级为待验证边界。"
last_task6_audit: 2026-06-04
last_task6_at: "2026-06-05T17:22:30"
last_task9_autofix_at: 2026-06-05

finalized_date: "2026-06-05"
finalized_by: "openclaw-task6-auto-promote"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-06
---



# 存储相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 7 及更早的 FUSE → 8.0-10 SDCardFS → 11 回归 FUSE 的演进
- 🔹 Scoped Storage 的引入（Android 10+）与 MediaStore API
- 🔹 EROFS 在 Android 12+ system 分区的启用
- 🔹 UFS 规格演进对 Android 存储性能的影响

### 扩展（可选深入）

- 🔸 各版本对 App 外部存储访问权限的收紧
- 🔸 Incremental FS 用于大型应用的按需下载

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 先确定基线，再谈“某个版本变快或变慢”

存储问题很容易被一句“升级系统后变慢了”带偏。相同的 Android 版本，可能运行在不同内核、文件系统和闪存上；相同的 App，在不同 `targetSdkVersion` 下又可能采用不同的共享存储规则。设备是随新版本出厂，还是从旧版本升级上来，也会影响 SDCardFS、FUSE passthrough 等能力是否可用。

因此，分析存储演进时至少要分清五个维度：

1. **平台版本与 App 的 target SDK**：两者共同决定 Scoped Storage 和媒体权限的行为。
2. **新机出厂还是存量设备升级**：内核冻结规则会影响 FUSE passthrough 等功能。
3. **分区及其文件系统**：`/data` 可能是 ext4 或 F2FS，只读动态分区可能是 ext4 或 EROFS。
4. **内核和模块版本**：GKI 配置、MediaProvider Mainline 模块都可能改变实现细节。
5. **存储硬件与主控制器**：UFS 设备规格、UFSHCI 控制器版本、厂商固件和 NAND 状态不能混为一个指标。

本节的当前源码基线为：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`
- Android common kernel：`android17-6.18-2026-06_r6`

版本迭代用于解释旧设备行为；涉及当前实现的结论，以这两个锚点为准。

## 一张时间表看清各层变化

| 时期 | 共享存储模拟与访问 | 分区文件系统与安装 | 硬件与内核侧提示 |
| --- | --- | --- | --- |
| Android 4.4—7 | emulated storage 主要使用用户态 FUSE；4.4 开始强化读写权限边界 | `/data` 以 ext4 为主，部分产品逐步采用 F2FS | eMMC 仍常见，UFS 开始进入高端设备 |
| Android 8—9 | AOSP 产品路径转向内核态 SDCardFS | F2FS 的量产采用增加 | UFS 2.x 普及 |
| Android 10 | SDCardFS 仍在使用；Scoped Storage 首次引入且提供过渡开关 | MediaStore 增加 `RELATIVE_PATH`、`IS_PENDING` 等面向 Scoped Storage 的能力 | UFS 3.0 开始量产 |
| Android 11 | 新发布设备回到 MediaProvider 承载的 FUSE；面向 API 30+ 的 App 强制使用 Scoped Storage | 引入 IncFS，支持流式安装场景 | 新发布且使用 5.4+ 内核的设备不再采用 SDCardFS |
| Android 12 | 符合内核与出厂条件的设备可启用 FUSE passthrough | IncFS v2；EROFS 开始进入更多 Android 产品配置 | UFS 3.1 常见 |
| Android 13 | FUSE 与 MediaProvider 路径继续演进；媒体权限拆分，系统 Photo Picker 上线 | EROFS 完整支持 Virtual A/B | GKI 只支持其内置文件系统作为 Android 用户空间所需文件系统 |
| Android 14—16 | Selected Photos Access、Photo Picker 和局部媒体授权继续细化 | Android 15 起支持 16KB page size；Android 16 加强预编译 ELF 对齐检查 | UFS 4.0/4.1 进入产品和标准演进阶段 |
| Android 17 | 共享存储仍以 Scoped Storage、MediaStore、Photo Picker 和 MediaProvider FUSE 为主线 | 继续兼容 4KB/16KB 页设备，具体分区格式仍由产品配置决定 | 当前内核含 FUSE、FUSE BPF、IncFS、EROFS 和 UFS MCQ 支持代码 |

这张表描述的是 AOSP 能力与常见产品路径，不代表每台设备都会在对应版本切换。OEM 可以保留旧内核和旧分区布局，硬件规格也不由 Android 版本号直接决定。

## 外部存储模拟：FUSE → SDCardFS → 新 FUSE

### `/storage/emulated/0` 是受控视图

现代 Android 中的“内部共享存储”通常以 `/data/media/<userId>` 为底层数据，在 `/storage/emulated/<userId>` 暴露给 App。后者不是对底层目录的简单 bind mount。系统需要根据调用方 UID、包归属、媒体权限和用户选择，给不同 App 呈现不同的可访问视图。

Android 7 及更早版本主要使用用户态 FUSE 完成这层模拟。典型请求路径是：

`App → VFS → FUSE 内核驱动 → 用户态守护进程 → VFS → 底层文件系统`

这条路径会增加调度、上下文切换和请求转发成本，但不能笼统理解成“所有数据都缓存两份”或“FUSE 只能单线程工作”。缓存策略、并发模型和内核实现均随版本变化，具体开销还取决于操作类型：目录遍历、频繁 `stat()` 和小块随机 I/O，通常比已打开文件上的长顺序读写更容易暴露额外成本。

### Android 8—10：SDCardFS 把模拟放入内核

Android 8.0 的 AOSP 产品路径开始使用 SDCardFS。它是内核中的可堆叠文件系统，可以在底层 ext4/F2FS 之上处理派生权限和共享存储语义，省去用户态 FUSE 守护进程参与每个请求的成本。

SDCardFS 改善了许多元数据密集型场景，但不宜引用脱离设备、内核和负载的固定提升百分比。Android 8—10 也不是“任意设备必定使用 SDCardFS”的充分条件。厂商配置与升级历史仍需通过实际挂载信息确认。

### Android 11：弃用 SDCardFS，但不能只归因于 Scoped Storage

Android 11 将 FUSE 设为存储模拟的默认实现，并弃用 SDCardFS。FUSE 的用户态裁决能力适合承载 Scoped Storage：MediaProvider 可以在打开文件时检查归属、媒体权限、位置元数据脱敏和转码条件。

不过，官方文档明确区分了两件事：SDCardFS 的弃用并非由 Android 11 的 FUSE 支持单独导致；FUSE 同时承担了替代存储模拟实现和执行隐私策略的任务。把这次切换简化成“为了 Scoped Storage，只能回到 FUSE”，会遗漏内核维护、升级兼容与安全边界。

设备条件同样重要：

- 使用 Android 11 出厂、内核为 5.4 或更高版本的设备不能继续使用 SDCardFS。
- 从旧版本升级的设备可能保留已有内核路径；不能只看 `ro.build.version.release` 推断底层文件系统。
- Android 13 起，Android 用户空间依赖的文件系统需要内置于 GKI；SDCardFS 只在 4.14 及更早内核的兼容范围内保留。

### Android 12+：passthrough 缩短已获准的数据路径

FUSE passthrough 不会绕过首次 `open()` 的权限判断。文件完成打开与访问条件检查后，内核才可能让后续 `read()`/`write()` 直接访问底层文件，减少用户态守护进程搬运数据的成本。

这项能力也有出厂边界：Android 12 新发布设备可在符合官方内核条件时支持 passthrough；从 Android 11 升级到 Android 12 的设备受冻结内核约束，不能据系统版本假定已经获得这项能力。

下面两行用于说明 Android 17 MediaProvider 如何决定某个打开文件能否进入 passthrough：

```cpp
bool passthrough = !redaction_needed && transforms_complete;
bool direct_io = open_info_direct_io && !passthrough;
```

这段代码来自 `packages/providers/MediaProvider/jni/FuseDaemon.cpp` 的 `android-17.0.0_r1`。如果文件仍需位置元数据脱敏，或者按需转码尚未完成，就不能把后续数据请求直接交给底层文件系统。由此可见，passthrough 是逐文件、逐次打开决策，不是设备级的永久直通开关。

同一份 Android 17 源码还包含 FUSE BPF 路径，并注明当前范围限于 `Android/data` 与 `Android/obb`。BPF 可以把部分文件系统请求转发到底层文件系统而绕过守护进程，但“内核编译了 `CONFIG_FUSE_BPF`”只代表具备基础能力，产品是否启用、目标路径是否符合规则仍需现场确认。

## Scoped Storage：版本号之外还要看 target SDK

### 从全盘权限转向按用途授权

旧版共享存储权限允许 App 在获得广义读写权限后查看大量不属于自己的文件。Scoped Storage 把访问方式按用途拆开：

- App 自己的外部专属目录使用 `getExternalFilesDir()` 等 API，通常无需存储权限，卸载时由系统清理。
- 共享图片、视频和音频通过 MediaStore 管理；App 访问自己创建的媒体与访问其他 App 创建的媒体，权限条件不同。
- 用户挑选少量照片或视频时，优先使用 Photo Picker，由系统返回选中项目的 URI。
- 文档及用户选择的目录使用 Storage Access Framework（SAF）。
- `MANAGE_EXTERNAL_STORAGE` 只适用于符合政策与功能条件的文件管理、备份等少数类别，不能当作普通兼容方案。

Scoped Storage 也不是 Android 对共享文件访问的第一次调整。Android 4.4（API 19）带来了两个重要前奏：App 访问自己的外部专属目录不再需要存储权限，Storage Access Framework 开始让用户通过系统选择器授权具体文档。Android 6.0（API 23）又把存储这类危险权限纳入运行时授权。前者按文件用途缩小授权范围，后者把授权时机从安装阶段移到运行阶段，两者共同改变了 App 组织文件和处理失败的方式。

### Android 10—17 的关键节点

| 平台版本 | 关键变化 | 容易忽略的条件 |
| --- | --- | --- |
| Android 10 / API 29 | 引入 Scoped Storage；MediaStore 增加面向新模型的写入方式 | App 可用 `requestLegacyExternalStorage` 暂时保留旧模型 |
| Android 11 / API 30 | 面向 API 30+ 的 App 必须使用 Scoped Storage；增加 all-files 特殊访问；允许在权限范围内用直接文件路径访问共享媒体 | `requestLegacyExternalStorage` 对面向 API 30+ 的 App 失效；SAF 不能再授予存储根目录、可靠 SD 卡根目录、`Download` 根目录以及 `Android/data`、`Android/obb` 的 tree 访问 |
| Android 13 / API 33 | `READ_EXTERNAL_STORAGE` 拆为图片、视频、音频权限；系统 Photo Picker 上线 | Photo Picker 只授予用户选择的项目，不等同于媒体库读取权限；部分旧系统可通过模块获得回推实现 |
| Android 14 / API 34 | 增加 `READ_MEDIA_VISUAL_USER_SELECTED`，支持用户仅授权所选照片和视频 | 自定义相册界面需要正确处理授权集合变化；使用系统 Photo Picker 时通常不需要媒体读取权限 |
| Android 15 / API 35 | App 可查询最近一次用户选择的媒体集合 | 仍需处理用户随后修改或撤销授权 |
| Android 16 / API 36 | 限制媒体访问时，App 自己创建的照片会预选，用户仍可取消；增加可嵌入式 Photo Picker 能力 | 嵌入式选择器依赖对应系统版本或扩展版本，不能只按 API 调用是否存在判断 |
| Android 17 / API 37 | 沿用 Scoped Storage、MediaStore 与 Photo Picker 的主模型 | Android 17 官方版本说明没有引入一套替代上述模型的平台级共享存储机制；仍要检查 MediaProvider 模块和厂商实现 |

这张表中的“强制”通常与 target SDK 绑定。例如，设备升级到 Android 11 并不自动让所有旧 App 按同一时刻改用面向 API 30 的行为。排查时应同时记录系统 API、App target SDK 和实际权限授予状态。

### MediaStore、直接路径、SAF 与 Photo Picker 各管一类问题

**MediaStore** 是共享媒体的索引与访问入口。写入新媒体时，`DISPLAY_NAME`、`MIME_TYPE`、`RELATIVE_PATH` 和 `IS_PENDING` 比依赖已废弃的 `DATA` 列更稳定。App 对自己创建的媒体通常拥有更直接的管理能力；读取其他 App 创建的媒体则受媒体权限、用户选择和平台版本约束。

**直接文件路径** 在 Android 11 起对符合条件的共享媒体重新可用，但它没有恢复 Android 9 时代的全盘访问。打开路径时仍会受到 FUSE/MediaProvider 的可见性和权限裁决。

**SAF** 通过 `DocumentsProvider` 处理用户选定的文档或目录。它不等于 MediaStore，也不能据此推断会使用媒体 FUSE passthrough。Provider 进程、Binder 调用、云端文档和远端文件系统都可能改变延迟。

**Photo Picker** 适合“让用户选择几张照片或视频”。App 获得的是有限 URI 授权，无需为了这个需求申请整类媒体读取权限。若任务需要长期访问，应按 API 约定持久化授权，并为项目被删除、移动或撤权做好失败处理。

因此，“Scoped Storage 比直接路径慢多少”没有统一答案。先确认调用经过哪一种 API、打开的是哪一类文件，再区分 Provider 查询、权限裁决、文件打开和持续数据传输的耗时。

## EROFS：只读分区的可选格式，不是 Android 版本开关

EROFS 是面向只读数据、支持压缩的 Linux 文件系统，进入主线内核的起点是 Linux 4.19。Android 产品可以把 `system`、`vendor`、`product` 等只读分区构建为 EROFS，也可以继续采用只读 ext4。Android 版本本身不能证明设备使用了哪一种格式。

AOSP EROFS 文档给出的当前要点包括：

- Android 构建默认使用 `lz4hc` 压缩器。
- 典型镜像平均可缩小约 25%，高压缩配置下最高可到约 45%；这是构建镜像统计，不是任意文件集的承诺值。
- Android 13 起，EROFS 完整支持 Virtual A/B。
- 是否启用由产品构建与分区配置决定，不能写成 Android 12 或 13 对全部设备的强制要求。

压缩会减少从闪存读取的字节数，同时带来解压 CPU 成本。冷启动是否改善，取决于数据可压缩性、闪存性能、CPU、预读和 page cache 命中率。EROFS 的只读属性也不能单独承担系统完整性保证；Android 的信任链还包括 AVB、dm-verity、SELinux 和分区签名。

下面的命令用于确认设备当前挂载了哪些文件系统，而不是根据机型或 Android 版本猜测：

```bash
adb shell 'cat /proc/mounts | grep -E " (ext4|f2fs|erofs|fuse)( |\\.)"'
```

输出应按挂载点逐项阅读：`/data` 的格式决定用户数据写入路径，只读动态分区的格式影响系统文件读取，`/storage/emulated` 的 FUSE 挂载则属于共享存储模拟层。三者处在不同层，不能用其中一个结果替代整条存储栈。

## UFS 演进：区分设备规范、主控制器和量产性能

### eMMC 与 UFS 的差异没有一张跑分表那么简单

eMMC 使用并行、半双工接口；eMMC 5.1 提供 Command Queuing，但是否启用以及主控制器如何实现仍有产品差异。UFS 使用 M-PHY/UniPro 串行链路，发送与接收方向各有信号通道，并从协议设计中提供任务管理和队列能力。

“全双工”描述的是链路方向，不保证 NAND 阵列能在任意负载下同时以峰值完成读写。控制器固件、SLC 缓存、垃圾回收、热降频、容量余量和文件系统同步语义，都会让应用实测远低于接口上限。

UFS 对 Android 的主要价值也不限于顺序带宽。多请求并发、较低命令延迟、HPB、WriteBooster 和更完善的电源状态，都可能改善安装、资源解包、相机写入和多任务 I/O。SQLite 的事务提交仍需要穿过文件系统、块层以及设备缓存刷新路径，换成更快的 UFS 不能消除 `fsync()` 的一致性成本。

### 规范演进不等于 Android 版本映射

| 标准 | 链路代际 | 规范层面的重点 | 阅读边界 |
| --- | --- | --- | --- |
| UFS 2.0/2.1 | M-PHY 3.x，最高约 5.8Gb/s/通道/方向 | UFS 在旗舰设备上逐步替代 eMMC | 具体顺序读写由存储器件决定，不能把某款产品跑分当作规范值 |
| UFS 3.0 | M-PHY 4.x，最高约 11.6Gb/s/通道/方向 | 链路速率提升 | Android 版本不会自动启用某一代 UFS |
| UFS 3.1 | 保持 UFS 3.0 链路代际 | 引入 WriteBooster、HPB、DeepSleep 等能力 | 每项能力都需要设备、主机和软件配合 |
| UFS 4.0 | M-PHY 5.x，最高约 23.2Gb/s/通道/方向 | 链路继续提升；配套 UFSHCI 4.0 定义 MCQ | UFS 设备规范与 UFS 主控制器规范应分开核对 |
| UFS 4.1 | 与 UFS 4.0 保持硬件兼容 | 2024 年发布的增量规范更新 | 不能据版本名推导固定 IOPS 或功耗比例 |
| UFS 5.0 | M-PHY 6.0 / UniPro 3.0，最高 46.6Gb/s/通道/方向 | 2026 年发布，双通道有效带宽目标约 10.8GB/s | 规范发布不代表 Android 17 量产设备已经采用 |

表中的链路速率是接口能力，不是 App 可获得的吞吐量。厂商常见的“4.2GB/s 顺序读取”“功效提升 46%”等数字来自特定器件和测试条件，不应写成所有 UFS 4.0 产品的共同属性。

### MCQ 属于 UFSHCI 主控制器能力

UFSHCI 4.0 引入 Multi-Circular Queue（MCQ），让主控制器提供多组硬件提交/完成队列。它与 Linux 块层的多队列模型配合，可减少单队列竞争并改善多核并发提交。

下面的内核片段用于确认 Android 17 锚点下 MCQ 的启用条件：

```c
/* UFSHC 4.0 compliant HC support this mode. */
static bool use_mcq_mode = true;

return hba->mcq_sup && use_mcq_mode;
```

代码来自 `drivers/ufs/core/ufshcd.c` 的 `android17-6.18-2026-06_r6`。驱动默认允许 MCQ，但还会检查 `hba->mcq_sup`；初始化失败时也会回退到传统 SDB 模式。因此，存储芯片标称 UFS 4.x、内核含 MCQ 代码、设备运行时正在使用 MCQ，是三个需要分别验证的命题。

`drivers/ufs/core/ufs-mcq.c` 还分别定义了读写队列、只读队列和轮询队列数量。队列更多也不必然让单个同步 I/O 更快，它主要改善并发请求分配与完成路径。

### 不要用危险或不可复现的 `dd` 证明 UFS 代际

在 `/data/local/tmp` 创建测试文件只能测到“当前文件系统 + 加密 + 块层 + 设备 + 当时温度和缓存状态”的组合结果，无法仅凭速度反推出 UFS 版本。`iflag=direct` 是否受设备工具链、对齐与文件系统支持，也要先验证。

下面的命令只用于采集设备身份、挂载和 UFS 驱动线索，不会向原始块设备写数据：

```bash
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell uname -r
adb shell cat /proc/mounts
adb shell 'find /sys -path "*ufshc*" -o -path "*ufs*" 2>/dev/null | head -n 80'
```

sysfs 路径由 SoC 与内核驱动决定，命令没有输出并不等于设备不是 UFS。若要做性能基线，应在可恢复的实验机上固定文件大小、预热方式、缓存策略、空闲容量、电量和温度，并同时采集块层延迟与调度数据。不要对 live userdata 原始块设备执行写测试。

## `/data` 的 ext4 与 F2FS：产品选择，不是统一迁移

F2FS 针对 NAND 闪存的写入与回收特征设计，Android 很早就提供了相应支持，部分厂商和 Pixel 产品把它用于 userdata。与此同时，ext4 仍是 Android 支持的重要文件系统。不能把版本线写成“Android 6 起 `/data` 从 ext4 全面迁移到 F2FS”。

两种文件系统的差异需要结合设备实现判断：

- F2FS 具备 segment、冷热数据分离、checkpoint、SSR 和 GC 等机制，长期性能受空闲 segment、碎片与回收压力影响。
- ext4 使用 extent、日志和成熟的块分配路径，在具体 workload 与厂商调优下仍可能是合适选择。
- 文件级加密、元数据加密、配额、discard、压缩和 checkpoint 参数会影响结果，文件系统名称不能单独解释一次卡顿。

排查时先从 `/proc/mounts` 确认 `/data` 的格式，再观察 `fsync`、writeback、GC、块层完成延迟和任务调度。相关机制分别见 §6.1「存储架构」、§6.2「文件系统」和 §6.3「I/O 调度」。

## Incremental FS：为受控的流式安装提供按块读取

Android 11 引入 Incremental FS（IncFS），最初用于通过 ADB 流式传输 APK。文件可以在全部数据块到齐前被系统打开；读取尚未提供的块时，内核记录缺块请求，由用户空间数据加载器提供并验证对应内容。

它不是“任意 5GB 游戏点击后几秒必定可玩”的通用承诺，也不是所有下载渠道都能让现有 App 自动获得流式启动。完整路径还需要 PackageManager、安装服务、数据加载器、APK Signature Scheme v4，以及足够覆盖启动工作集的块调度。

版本边界如下：

- Android 11 允许以模块形式提供 IncFS，主要支持流式 APK 安装。
- Android 12 起要求相应内核配置内置，并引入 IncFS v2；游戏流式安装等产品能力可在此基础上实现。
- `android17-6.18-2026-06_r6` 的 GKI 配置包含 `CONFIG_INCREMENTAL_FS=y`，说明当前内核基线保留这一能力。

如果启动线程在 IncFS 文件读取上等待，表面现象会像普通 I/O stall。分析时还要检查数据加载器是否及时供应所需块，网络和校验耗时是否落在关键路径。

## 16KB page size：兼容性变化不能直接写成存储提速

Android 15 开始支持使用 16KB page size 的设备；这不代表 Android 15 之后的设备都运行在 16KB 模式。Android 16 又在构建阶段加强了对预编译 ELF 的 16KB 对齐检查。到了 Android 17，App 仍需同时面对 4KB 与 16KB 设备，含原生库的 APK/AAB 应保证 ELF segment、打包对齐和运行时代码都兼容目标页大小。

较大页可以减少某些工作负载的页表项和 TLB 压力，也会扩大最小分页与 `mmap()` 对齐粒度。它对文件 I/O 吞吐量没有无条件的直接增益：顺序读写还受 read-ahead、块大小、文件系统、压缩和存储设备限制；随机映射访问甚至可能读取更多无用数据。内存碎片、内部浪费和工作集形态也会改变收益。

下面的命令用于确认设备运行时页大小，并查看 App 是否包含原生库：

```bash
adb shell getconf PAGE_SIZE
unzip -l app-release.apk | grep 'lib/.*\.so$'
```

第一条应在目标设备上返回实际页大小，第二条只确认 APK 中是否有 `.so`。若存在原生库，还需用 Android 官方提供的 APK/ELF 对齐检查方法逐个验证；仅查看 `.bss`、`.data` section 不能替代 program header 的 `LOAD` segment 对齐检查。

## 一套可复用的版本排查顺序

遇到“升级后相册扫描慢了”“新机安装反而卡”等问题时，可以按下面的顺序缩小范围：

1. 记录 Android API、build fingerprint、内核版本、App target SDK，以及设备是新版本出厂还是升级而来。
2. 从 `/proc/mounts` 区分 `/data`、只读系统分区和 `/storage/emulated` 的文件系统。
3. 明确 App 使用直接路径、MediaStore、SAF、Photo Picker 还是专属目录。
4. 把操作拆成查询、权限裁决、`open()`、持续读写、`fsync()` 和关闭阶段，避免只比较总耗时。
5. 用 Perfetto 同时观察线程调度、Binder、文件系统和块 I/O；Provider 查询慢与块设备慢需要不同证据。
6. 若怀疑 UFS 或 F2FS 状态，再补充温度、空闲空间、writeback、GC 和请求完成延迟。

版本知识在这里用于提出更准确的假设，不用于代替 Trace、源码和设备现场数据。

## 常见误区

### “Android 11 回到 FUSE，所以所有外部存储操作都会变慢”

FUSE 增加了用户态裁决路径，但文件打开后的数据传输可能进入 passthrough，Android 17 还存在条件受限的 FUSE BPF 路径。目录操作、需脱敏媒体和长顺序读取的成本结构不同，应按操作类型测量。

### “Android 13 以后 system 分区一定是 EROFS”

Android 13 的里程碑是 EROFS 完整支持 Virtual A/B。产品是否采用 EROFS 由构建配置决定，查看实际挂载才有结论。

### “标称 UFS 4.0 就一定启用了 MCQ”

MCQ 属于 UFSHCI 主控制器能力。驱动还要看到控制器支持位并成功完成初始化；任何一步不满足都可能继续使用传统队列模式。

### “Photo Picker URI 是普通文件路径”

Photo Picker 返回带有限授权的 URI。它可能由本地或云端 Provider 提供，生命周期、可持久化条件和访问延迟都应按 ContentResolver 契约处理。

### “16KB 页会让文件读取提高四倍”

页大小从 4KB 变为 16KB 不等于闪存接口或文件系统块吞吐提高四倍。它改变的是内存管理粒度，并间接影响部分映射和 I/O 工作负载。

## 小结

Android 存储演进包含几条相互独立又彼此影响的线：

- 共享存储从旧 FUSE 转向 SDCardFS，再回到由 MediaProvider 参与裁决的新 FUSE；Android 12+ 可在条件满足时使用 passthrough。
- 权限模型从广义外部存储权限，演进到 Scoped Storage、细粒度媒体权限、Photo Picker 和用户选定媒体集合。
- EROFS 为只读分区提供压缩格式，ext4 与 F2FS 则继续服务于不同的产品和可写分区需求。
- UFS 规范提高链路与队列能力，但 App 性能仍取决于控制器、NAND、文件系统、内核和 workload。
- IncFS 与 16KB page size 各自解决流式安装和页大小兼容问题，都不能被概括成“新版本自动让存储更快”。

排查时先识别真实路径和版本条件，再用 Android 17 平台源码、`android17-6.18-2026-06_r6` 内核以及设备 Trace 验证。这样得到的结论才能跨设备复用。

## 参考资料

- [FUSE passthrough](https://source.android.com/docs/core/storage/fuse-passthrough)
- [Scoped Storage](https://source.android.com/docs/core/storage/scoped)
- [Android kernel file system support](https://source.android.com/docs/core/architecture/android-kernel-file-system-support)
- [Access media files from shared storage](https://developer.android.com/training/data-storage/shared/media)
- [Photo Picker](https://developer.android.com/training/data-storage/shared/photopicker)
- [Partial photo and video access](https://developer.android.com/about/versions/14/changes/partial-photo-video-access)
- [EROFS](https://source.android.com/docs/core/architecture/kernel/erofs)
- [Incremental File System](https://source.android.com/docs/core/architecture/kernel/incfs)
- [16KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb)
- [Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [JEDEC announces UFS 4.1 and UFSHCI 4.1](https://www.businesswire.com/news/home/20250108099318/en/JEDEC-Announces-Updates-to-Universal-Flash-Storage-UFS-and-Memory-Interface-Standards)
- [JEDEC announces UFS 5.0](https://www.businesswire.com/news/home/20260226710161/en/JEDEC-Announces-Updates-to-Universal-Flash-Storage-UFS-and-Memory-Interface-Standards)
- AOSP `packages/providers/MediaProvider/jni/FuseDaemon.cpp`（`android-17.0.0_r1`）
- Android common kernel `drivers/ufs/core/ufshcd.c`、`drivers/ufs/core/ufs-mcq.c`（`android17-6.18-2026-06_r6`）
