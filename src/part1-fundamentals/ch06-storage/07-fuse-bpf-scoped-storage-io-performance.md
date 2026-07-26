---
title: "Linux 6.12 FUSE Passthrough 内核机制与 Android Scoped Storage I/O"
chapter: "6.7"
status: ready-for-review
drafted_date: "2026-06-05"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-05"
last_verified_against: "Linux v6.12 fs/fuse/passthrough.c, fs/fuse/iomode.c; AOSP android-16.0.0_r1 packages/providers/MediaProvider/jni/FuseDaemon.cpp"
confidence: medium
sources:
  - type: aosp
    path: "Linux v6.12 fs/fuse/passthrough.c"
  - type: aosp
    path: "Linux v6.12 fs/fuse/iomode.c"
  - type: aosp
    path: "packages/providers/MediaProvider/jni/FuseDaemon.cpp"
  - type: official
    path: "https://source.android.com/docs/core/storage/fuse-passthrough"
tags: [storage, fuse, passthrough, scoped-storage, kernel, linux-6.12, android17]
related_chapters: ["6.1", "6.6", "24.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "AOSP源码验证"
rewrite_note: "原 FUSE-BPF 前提经源码验证不存在，已基于 Linux 6.12 实际 FUSE passthrough 重写"
---

# 6.7 Android 17 FUSE Passthrough、FUSE BPF 与 Scoped Storage I/O

> 本章的平台源码基线是 Android 17 / API 37 / `android-17.0.0_r1`，内核源码基线是 `android17-6.18-2026-06_r6`。这里的 6.18 是知识库统一采用的内核源码锚点，不代表每台 Android 17 设备都运行 6.18 内核。分析量产设备时，仍要以该设备的 `uname -r`、最终内核配置、产品属性和 MediaProvider 日志为准。

6.6 节解释了应用经过 `/storage/emulated/<user>/` 访问共享存储时的路径。本章继续回答三个容易混淆的问题：

1. `FOPEN_DIRECT_IO`、FUSE passthrough 和 FUSE BPF 分别省掉了什么；
2. Android 17 的 MediaProvider 在什么条件下允许某次文件打开使用 passthrough；
3. 外部存储 I/O 偏慢时，怎样用可复现的证据判断瓶颈所在。

先给出结论：Android 17 的 6.18 内核源码同时包含 FUSE passthrough 和 FUSE BPF。passthrough 以“已经打开的文件”为单位，把后续数据 I/O 交给 backing file；FUSE BPF 可以在 FUSE 操作前后执行 BPF 程序，并把受支持的操作交给 backing filesystem。它们可以共存，但用途、接入方式和覆盖路径不同。

## 1. 先区分四条 I/O 路径

理解本章时，不能把“绕过页缓存”“绕过 FUSE daemon”和“访问 lower filesystem”当成同一件事。

| 路径 | FUSE 页缓存 | read/write 是否需要 daemon 处理 | lower filesystem 的访问方式 | Android 17 中的典型用途 |
|---|---|---|---|---|
| 缓存 FUSE | 使用 | 缓存未命中、回写等情况需要 | daemon 再访问 lower fs | 普通共享存储文件访问 |
| `FOPEN_DIRECT_IO` | 对该 open 绕过 | 仍然需要 | daemon 处理 FUSE 请求 | redaction、缓存一致性或产品策略要求 direct I/O 的文件 |
| FUSE passthrough | 不使用 FUSE 文件页缓存的数据路径 | open 需要；获准后的数据 I/O 通常不需要 | 内核通过 backing file 转发 | 无须 redaction、transform 已完成的普通文件数据 I/O |
| FUSE BPF + backing | 取决于具体操作和实现 | BPF/backing 已处理的操作可以不交给 daemon | FUSE inode/dentry 关联 backing path | 当前 MediaProvider 对主存储 `Android/data`、`Android/obb` 的加速与访问控制 |

`direct_io` 最容易被误读。它只说明这次 open 不使用 FUSE 页缓存，并没有让 read/write 自动进入 lower fs。没有 passthrough 或 BPF backing 时，请求仍会经 `/dev/fuse` 到达 MediaProvider。

passthrough 也不等于绕过 Scoped Storage。权限判断、redaction 和转码决策发生在 open 阶段；只有策略允许的文件，daemon 才会把后续数据面交给 backing file。

## 2. Android 17 内核中两种机制都存在

下面的配置片段用于确认 `android17-6.18-2026-06_r6` 同时编译支持两套代码路径，其内容来自 `fs/fuse/Kconfig` 和 `fs/fuse/Makefile`：

```text
config FUSE_PASSTHROUGH
    bool "FUSE passthrough operations support"
    default y
    depends on FUSE_FS

config FUSE_BPF
    bool "Adds BPF to fuse"
    depends on FUSE_FS
    depends on BPF

fuse-$(CONFIG_FUSE_PASSTHROUGH) += passthrough.o backing.o
fuse-$(CONFIG_FUSE_BPF) += fuse_bpf_backing.o
```

这段配置只能证明源码具备相应实现。`FUSE_PASSTHROUGH` 在 Kconfig 中默认选中，Android 17 arm64 GKI defconfig 也显式设置了 `CONFIG_FUSE_BPF=y`；OEM 仍可通过产品内核配置、模块组合或运行时开关改变最终结果。因此，排查设备时应读取最终 `.config` 或 `/proc/config.gz`，不能仅凭 Android 大版本推断功能已启用。

### 2.1 Passthrough：一次 open 对应一个 backing file

上游 FUSE 协议 7.40 增加了 `FUSE_PASSTHROUGH` 初始化能力、`FOPEN_PASSTHROUGH` open 标志，以及 `fuse_open_out.backing_id`。其建立过程可以分成四步：

1. FUSE daemon 收到 open/create 请求，完成权限和内容策略检查；
2. daemon 打开 lower fs 文件，并向当前 FUSE connection 注册这个文件，得到 `backing_id`；
3. open 回复携带 `FOPEN_PASSTHROUGH` 与 `backing_id`；
4. 内核为这次 FUSE open 创建独立 backing file，后续 read/write、mmap 和可用的 splice 操作通过该 file 执行。

这里的优化单位是“这次打开的文件”，不是整个挂载点。文件关闭后，对应 open 的 passthrough 关系也结束。

### 2.2 FUSE BPF：对操作做 prefilter、backing 和 postfilter

Android 17 内核的 `include/uapi/linux/android_fuse.h` 定义了三段处理标志：

- `FUSE_BPF_USER_FILTER`：仍需用户态过滤；
- `FUSE_BPF_BACKING`：执行 backing filesystem 操作；
- `FUSE_BPF_POST_FILTER`：backing 操作之后再执行过滤。

同一头文件还定义了 `FUSE_ACTION_KEEP`、`FUSE_ACTION_REMOVE` 和 `FUSE_ACTION_REPLACE`。MediaProvider 在 lookup 回复中使用这些动作，为目录项安装或移除 backing fd 与 BPF 程序。内核侧 `fuse_bpf_backing.c` 覆盖 open、create、flush、lseek、read/write、splice、mmap、属性和目录等多类操作，范围比“某个普通文件 open 后的数据转发”更广。

这并不表示 Android 17 把全部共享存储访问交给了 BPF。`FuseDaemon.cpp` 当前只在主存储路径中安装相关 entry，并把 BPF backing 根限定在 `Android/data` 与 `Android/obb`。遇到包所属路径时，代码还会按规则移除继承的 BPF 程序。具体访问是否进入 backing 路径，要结合目录项状态、BPF 返回值和该操作的内核实现判断。

## 3. Passthrough 的内核数据路径

### 3.1 注册 backing file

`fs/fuse/backing.c` 的 `fuse_backing_open()` 接收 daemon 提供的 lower-fs fd，并做以下检查：

- fd 必须有效；
- 目标必须是普通文件，目录不能按普通文件 passthrough 注册；
- backing filesystem 的 stack depth 不能超过当前 FUSE connection 允许的上限；
- backing file、注册时凭据与生成的 ID 一起保存在 connection 的 IDR 中。

Android 17 common kernel 在这一函数和 close 路径中用 `#if 0` 关闭了上游的 `CAP_SYS_ADMIN` 检查。源码注释说明 Android 已在别处限制访问，不希望仅为 daemon 增加额外 capability。

这个补丁的含义应控制在权限边界内：Android common kernel 不要求调用者仅凭 `CAP_SYS_ADMIN` 注册 backing file。它没有消除 FUSE connection 归属、fd 获取、普通文件检查、stack depth、MediaProvider 权限判断和 SELinux 约束，也不能据此推导出可测量的 I/O 性能提升。capability 检查只发生在注册或关闭 backing 映射时，不在每次 read/write 热路径中。

### 3.2 read/write 如何到达 lower fs

下面的精简代码用于说明 passthrough read 的调用方向，结构与 Android 17 的 `fs/fuse/passthrough.c` 一致：

```c
ssize_t fuse_passthrough_read_iter(struct kiocb *iocb,
                                   struct iov_iter *iter)
{
    struct file *file = iocb->ki_filp;
    struct fuse_file *ff = file->private_data;
    struct file *backing_file = fuse_file_passthrough(ff);
    struct backing_file_ctx ctx = {
        .cred = ff->cred,
        .accessed = fuse_file_accessed,
    };

    write_inode_now(file_inode(file), 1);
    return backing_file_read_iter(backing_file, iter, iocb,
                                  iocb->ki_flags, &ctx);
}
```

执行前，内核会先提交 FUSE inode 上可能存在的脏缓存页；随后 `backing_file_read_iter()` 使用保存的凭据读取 lower file。这里省掉的是一次 FUSE read 请求往返，并没有省掉 VFS、lower filesystem、文件加密、页缓存、块层和设备访问的成本。

写路径使用 `backing_file_write_iter()`，并在 Android 17 基线中对 FUSE inode 获取独占 `inode_lock()`。写完后，内核更新 FUSE inode 的属性，并使相应范围的 FUSE 页缓存失效。由此可以得到两个排查结论：

- passthrough 不保证多个 writer 可以无锁并行写同一 inode；
- 如果延迟来自 f2fs/ext4、fscrypt、回写、块队列或闪存，passthrough 不会把这部分时间抹掉。

### 3.3 mmap 与 splice 的边界

`passthrough.c` 实现了 mmap、splice read 和 splice write 的 backing-file 路径。不过，Android 17 MediaProvider 在协商任一种 passthrough 能力时会清除 `FUSE_CAP_SPLICE_WRITE`。源码注释给出的原因是规避 redacted FUSE cache 与 passthrough cache 之间的内容污染问题。

所以，“内核实现了 passthrough splice”与“当前 MediaProvider 连接允许 FUSE daemon 使用 splice write”是两个层次。视频播放或文件复制是否受益，还取决于应用使用的 API、文件是否获准 passthrough、读写方向、缓存状态和底层文件系统。不能把所有视频或所有复制任务概括为零拷贝。

## 4. `iomode.c` 解决的是缓存一致性

Android 17 的 `fuse_file` 有四个 I/O mode 值：

| 枚举 | 含义 |
|---|---|
| `IOM_NONE` | 当前 file 没有持有 cached、uncached 或 passthrough inode mode 引用 |
| `IOM_CACHED` | 使用 FUSE inode 页缓存，并增加 `iocachectr` |
| `IOM_UNCACHED` | 并行 direct write 期间临时进入严格 uncached 状态 |
| `IOM_PASSTHROUGH` | 当前 open 持有 passthrough backing 引用，并增加 `iopassctr` |

原理上要保护两组状态：

- cached I/O 不能与会破坏缓存一致性的 direct write 随意并发；
- 同一个 FUSE inode 不能同时绑定互相冲突的 backing file。

`FOPEN_DIRECT_IO` 且没有 `FOPEN_PASSTHROUGH` 时，`fuse_file_io_open()` 不会立即把 file 设为 `IOM_UNCACHED`。并行 direct write 开始时，`file.c` 才调用 `fuse_inode_uncached_io_start()`；如果已有 cached open，代码会改用独占 inode lock，避免并行 direct write 与页缓存访问冲突。

Android common kernel 还关闭了 `fuse_file_cached_io_open()` 中一条“发现 inode 已有 backing 就返回 `-ETXTBSY`”的上游检查，注释写明 Android 需要同时打开 passthrough 与非 passthrough 文件。这条改动允许 Android 的特定组合继续执行，但仍有多重约束：

- 不同 backing file 绑定同一 FUSE inode 会返回 `-EBUSY`；
- 某些已有 backing、非 passthrough open 与 writeback-cache 组合仍会在 `fuse_file_io_open()` 中失败；
- passthrough 写仍获取 inode lock；
- daemon 必须为同一 inode 返回彼此兼容的 open flags，否则用户会看到 `EIO`。

因此，不能把这条 Android 补丁解释为“同一文件可由任意多进程、任意模式无代价并发访问”。它只移除了一个不适合 Android 用例的拒绝分支，缓存与 backing 一致性规则依旧有效。

还有一个少见但重要的协议细节：内核允许 `FOPEN_PASSTHROUGH` 与 `FOPEN_DIRECT_IO` 同时出现。`iomode.c` 的注释规定，这个组合下 read/write 仍发给 FUSE server，mmap 才使用 backing file。看到 passthrough 标志时，不应脱离 open flags 判断所有数据操作的去向。

## 5. Android 17 MediaProvider 怎样选择 passthrough

### 5.1 挂载级能力协商

`android-17.0.0_r1` 的 `FuseDaemon.cpp` 支持两套接口：

| MediaProvider 看到的能力 | daemon 的处理 | 内核关联方式 |
|---|---|---|
| `FUSE_CAP_PASSTHROUGH` | 使用 Android 早期 passthrough 接口 | `fuse_passthrough_enable()` 返回 `passthrough_fh` |
| `FUSE_CAP_PASSTHROUGH_UPSTREAM` | 还要检查 `/sys/fs/fuse/features/fuse_passthrough` | `fuse_passthrough_open()` 注册 backing fd，open 回复填写 `backing_id` |

源码把后一种标记为 upstream passthrough。两条路径的协议形式不同，但目标相同：open 仍由 MediaProvider 审核，获准后的数据请求可在内核中访问 lower file。

sysfs 节点只用于确认 upstream passthrough 的内核能力，不能证明产品属性已开启、MediaProvider 已选择该能力，更不能证明某个文件的 open 已获准。

### 5.2 每次 open 的资格判断

下面的代码用于展示 MediaProvider 最核心的逐文件选择条件，摘自 `create_handle_for_node()` 的等价逻辑：

```cpp
if (fuse->passthrough && allow_passthrough) {
    bool passthrough = !redaction_needed && transforms_complete;
    bool direct_io = open_info_direct_io && !passthrough;

    handle = new handle(fd, std::move(redaction_info),
                        !direct_io /* cached */,
                        passthrough,
                        uid, transforms_uid);
}
```

从这段代码可以读出三条明确边界：

1. 需要隐藏 EXIF 等内容时，MediaProvider 必须看到 read，不能交给 passthrough；
2. 转码等 transform 尚未完成时，第一次 read 可能触发处理，也不能提前交给 passthrough；
3. Java 层返回的 fd 可能再次指向 FUSE 文件，`pf_open()` 会禁止这类 fd 使用 passthrough，防止递归或错误 backing。

`ShouldOpenWithFuse()` 不是这里的 passthrough 开关。它参与 provider fd 与路径访问的一致性决策；把它简化成“返回 false 就使用 passthrough”会误判当前源码。最终是否调用 `do_passthrough_enable()`，取决于 `handle->passthrough`。

open、create、权限检查、路径解析和 backing 注册依旧会唤醒 MediaProvider。passthrough 主要减少 open 之后的文件内容读写往返；lookup、readdir、rename 和需要用户态内容处理的操作应分别分析。

## 6. Android 17 中 FUSE BPF 的具体位置

MediaProvider 定义的 BPF 程序路径是 `/sys/fs/bpf/prog_fuseMedia_fuse_media`。在主存储 lookup 返回 entry 时，`fuse_bpf_install()` 检查路径：

- 到达 `Android/data` 或 `Android/obb` 的 backing 根时，返回 `FUSE_ACTION_REPLACE`，安装 backing fd 与 BPF fd；
- 进入包所属路径时，可以返回移除 BPF 的动作；
- `readdirplus` 暂时不能直接携带 backing fd 与 BPF program，代码会让相关项随后再触发单独 lookup。

vold 的 `EmulatedVolume::doMount()` 提供了另一半证据：`IsFuseBpfEnabled()` 为 false 时，vold 才把 lower fs 上的 `Android/data` 和 `Android/obb` bind mount 到用户可见 FUSE 树；BPF 启用时跳过这组 bind mount，由 FUSE BPF/backing 路径承担相应工作。

这套机制主要解决受保护目录的访问控制与 lower-fs 转发，不是普通 `DCIM`、`Pictures` 或 `Download` 文件的通用加速开关。分析媒体大文件读写时，先看 passthrough；分析 `Android/data`、`Android/obb` 的目录和文件操作时，再检查 FUSE BPF 与 vold 的选择。

### Passthrough 与 FUSE BPF 对照

| 维度 | FUSE passthrough | FUSE BPF |
|---|---|---|
| 关联对象 | 一次普通文件 open 的 backing file | FUSE inode/dentry 的 BPF program 与 backing path |
| 决策入口 | daemon 处理 open/create | lookup 安装 entry，操作执行前后由 BPF 决定 |
| 主要覆盖 | read/write、mmap、splice | open、read/write、目录、属性等多类已实现操作 |
| Android 17 当前用途 | 符合条件的共享媒体文件数据 I/O | 主存储 `Android/data`、`Android/obb` |
| 能否完全跳过 daemon | open 不能；获准的数据操作通常可以 | 取决于 BPF 返回值、backing 实现与具体 opcode |
| 关键风险 | redaction、transform、页缓存一致性 | BPF 程序、backing entry、用户态回退之间的一致性 |

## 7. 性能收益该怎样表述

passthrough 的直接收益是减少 FUSE read/write 请求的用户态调度、数据搬运和 daemon 工作。收益大小没有跨设备固定比例，至少受以下因素影响：

- 请求是顺序还是随机、块大小多大；
- 文件页是否已经命中缓存；
- I/O 是否需要 redaction、转码或其他 transform；
- lower fs 是 f2fs 还是 ext4，是否经过 fscrypt 或 inline encryption；
- 回写、`fsync()`、闪存延迟和系统内存压力；
- 文件是通过 `/storage/emulated/...` 路径打开，还是由 MediaProvider 返回 lower-fs fd；
- OEM 是否启用了对应能力，当前 open 是否符合资格。

AOSP 的 scoped-storage 文档给过特定 Pixel 2 测试结果：调优后的 FUSE 顺序读写接近 SDCardFS，顺序写略慢，随机读写最差可接近两倍开销。这个结果描述的是指定设备和工作负载，不能直接换算成 Android 17 passthrough 的承诺值。

应用层可以据此选择优化方向：

- 大文件内容读写先确认该 open 是否获准 passthrough，再判断 lower fs 或块设备是否成为主耗时；
- 相册枚举、批量 stat 和目录遍历主要看 MediaStore 查询、lookup/readdir 与数据库，不要指望文件数据 passthrough 改善全部耗时；
- 图像编辑包含大量小块随机读写、临时文件和频繁同步时，复制到应用私有目录可能更稳定，但要把复制时间、空间占用和失败恢复一起计入；
- 通过 `ContentResolver.openFileDescriptor()` 得到的 fd 可能直接指向 lower fs，也可能受 provider 处理约束，测试报告必须写清 API 和 fd 来源。

## 8. 设备上怎样验证

单个信号只能回答一个问题。推荐把“内核能力”“挂载级启用”“逐文件路径”和“最终耗时”分开取证。

### 8.1 记录内核与产品环境

下面的命令用于记录测试设备的版本、页大小和最终可见内核配置：

```bash
adb shell uname -r
adb shell getconf PAGESIZE
adb shell getprop ro.build.version.sdk
adb shell getprop ro.build.version.release
adb shell 'zcat /proc/config.gz 2>/dev/null | grep -E "CONFIG_FUSE_(FS|PASSTHROUGH|BPF)="'
```

部分 user build 不提供 `/proc/config.gz`，此时需要从对应 boot/GKI 构建产物取得 `.config`。`ro.build.version.sdk=37` 不能替代内核配置证据，`uname -r` 也不能证明 MediaProvider 运行时已经使用某项能力。

### 8.2 检查 upstream passthrough 能力与 daemon 日志

下面的命令分别检查内核 sysfs 能力和 MediaProvider 启动日志：

```bash
adb shell cat /sys/fs/fuse/features/fuse_passthrough
adb logcat -d -s FuseDaemon:V '*:S'
```

sysfs 输出 `supported` 只表示 upstream 接口可用。AOSP 官方文档给出的 `Using FUSE passthrough` 日志可以证明 MediaProvider 挂载选择了 passthrough，但它仍是连接级证据；具体文件若需要 redaction、transform 未完成或 backing 注册失败，仍可能回到 FUSE 数据路径。

### 8.3 先枚举 tracepoint，再启用

不同产品内核可能裁剪 tracepoint 或挂载到不同 tracefs 路径。下面的命令用于先确认事件名称，再跟踪 FUSE 用户态请求：

```bash
adb shell su 0 sh -c '
TRACE=/sys/kernel/tracing
[ -d "$TRACE/events" ] || TRACE=/sys/kernel/debug/tracing
grep "^fuse:" "$TRACE/available_events"
echo 1 > "$TRACE/events/fuse/fuse_request_send/enable"
echo 1 > "$TRACE/events/fuse/fuse_request_end/enable"
echo > "$TRACE/trace"
'
```

Android 17 基线的 `fs/fuse/fuse_trace.h` 定义了 `fuse_request_send` 和 `fuse_request_end`，send 事件会打印 opcode。量产内核未必保留同样配置，因此先读 `available_events` 比直接写一个假定事件名更可靠。

完成一次受控 I/O 后，下面的命令用于读取并筛选 open/read/write 请求：

```bash
adb shell su 0 sh -c '
TRACE=/sys/kernel/tracing
[ -f "$TRACE/trace" ] || TRACE=/sys/kernel/debug/tracing
grep -E "FUSE_(OPEN|READ|WRITE)" "$TRACE/trace"
'
```

有 `FUSE_READ` 或 `FUSE_WRITE` send 事件，说明相应请求进入了 daemon。只有 `FUSE_OPEN` 而没有 read/write，与 passthrough 或 BPF backing 相符，但也可能是页缓存命中、测试没有产生预期 syscall、读提前失败或采集窗口不完整。这个现象必须和文件来源、冷暖缓存、MediaProvider 日志、应用 syscall 以及块层事件一起解释。

### 8.4 用 Perfetto 回答“时间花在哪里”

Perfetto 采集至少应包含：

- 应用线程调度、阻塞状态和 syscall；
- MediaProvider 进程的调度活动；
- FUSE request tracepoint；
- f2fs/ext4 与 block I/O 事件；
- 测试区间的自定义 trace marker。

没有一个通用的“MediaProvider CPU 低于 5% 就算 passthrough”阈值。进程 CPU 会受文件大小、请求并发、缓存、后台扫描和设备性能影响。更可靠的判断是：在标记清楚的测试窗口内，应用发出的 read/write 是否对应 FUSE daemon 请求，线程等待落在 daemon、lower fs、回写还是块设备。

## 9. 建立可复现的对比实验

一次 `cat` 或一次文件复制不足以得出结论。建议至少拆成四组负载：

1. 大块顺序读，观察吞吐、应用阻塞和 FUSE read 数量；
2. 固定块大小的随机读，分别测冷缓存与暖缓存；
3. 顺序写加独立的 `fsync()` 测试，区分写入速度和持久化延迟；
4. lookup/readdir/stat 密集测试，单独评估元数据路径。

每组测试都记录：

- 文件大小、块大小、队列深度、线程数和运行轮数；
- 文件创建方式、所属目录、调用 API 和 fd 来源；
- 设备温度、电源模式、剩余空间、文件系统类型；
- 首轮与后续轮次，避免混合冷暖缓存结果；
- Android build、MediaProvider 模块版本、kernel release 与配置；
- passthrough、FUSE BPF、redaction 和 transform 是否适用。

应用私有目录可以作为 lower-fs 参考，但它与共享存储可能使用不同挂载选项、加密策略和数据布局。两者差值包含多项因素，不能全部记在 FUSE 名下。

## 10. 常见误判

### “Android 17 设备一定是 6.18 内核”

错误。`android17-6.18-2026-06_r6` 是本章的内核源码锚点。设备可以采用 Android 17 允许的其他产品内核，升级设备还受出厂内核冻结和厂商维护策略影响。

### “`direct_io` 就是直接访问 lower fs”

错误。它绕过 FUSE 页缓存；没有 passthrough 或 BPF backing 时，read/write 仍由 FUSE daemon 处理。

### “发现 sysfs 节点就说明所有文件都走 passthrough”

错误。sysfs 表示 upstream 内核能力，MediaProvider 还要完成挂载协商和逐文件判断。

### “passthrough 会跳过权限检查”

错误。open 阶段仍由 MediaProvider 执行 Scoped Storage 策略。redaction 或未完成 transform 的文件不会得到 passthrough 数据路径。

### “FUSE BPF 在 Android 17 不存在”

错误。Android 17 的 6.18 基线包含 `CONFIG_FUSE_BPF`、`fuse_bpf_backing.c`、`android_fuse.h` 和 MediaProvider 的 BPF 安装代码。当前 Android 用法集中在主存储 `Android/data` 与 `Android/obb`，不应外推到全部共享媒体目录。

### “允许 mixed mode 后，多进程访问就没有锁竞争”

错误。Android 补丁只关闭了一条 `-ETXTBSY` 分支。conflicting backing 检查、open flag 一致性、direct-write 锁和 passthrough write 的 inode lock 都还在。

### “没有 FUSE_READ trace 就已证明 passthrough 生效”

证据不足。页缓存命中、测试窗口和 syscall 行为都可能造成相同现象。需要与挂载日志、文件资格、应用调用和 lower-fs/block 事件联合判断。

## 11. 版本边界

| Android 版本 | 需要记住的边界 |
|---|---|
| Android 11 | 重新以 MediaProvider FUSE 支持 direct-path Scoped Storage；官方 passthrough 从 Android 12 开始 |
| Android 12 | 首次支持 FUSE passthrough；官方文档明确支持取决于设备内核，Android 11 升级设备因内核冻结不能获得该功能 |
| Android 13—16 | MediaProvider、内核接口和产品实现持续演进；不能只看 Android 版本判断运行时路径 |
| Android 17 / API 37 | 本章以 `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6` 验证；内核源码同时包含 upstream passthrough 与 FUSE BPF，设备结果仍以产品配置和运行时证据为准 |

Android 12 官方文档还说明，launch 设备只有在使用包含相应改动的官方内核并配置产品属性时才可以启用 passthrough。后续版本不应被简化成“launch 设备默认全部开启”；OEM 配置、内核能力和 MediaProvider 模块缺一不可。

## 12. 小结

Android 17 共享存储的快速路径有两套不同机制：

- FUSE passthrough 在 open 审核通过后，把该文件的后续数据 I/O 关联到 backing file；
- FUSE BPF 在操作前后运行程序，并可调用 backing filesystem，当前 Android 代码主要把它用于主存储 `Android/data` 和 `Android/obb`。

`FOPEN_DIRECT_IO` 只绕过 FUSE 页缓存，不能代替 passthrough。passthrough 省掉的是数据请求经 daemon 往返的成本，open 策略、redaction、transform、缓存一致性、lower fs、加密和块设备成本仍需分别分析。

排查时按四层收集证据：最终内核能力、MediaProvider 挂载选择、该文件的逐次 open 资格、Perfetto/ftrace 中的请求与等待位置。做到这一点，才能判断优化对象是 FUSE 用户态往返、媒体策略、元数据访问、文件系统，还是存储设备。

## 参考源码与文档

- AOSP `android-17.0.0_r1`：`packages/providers/MediaProvider/jni/FuseDaemon.cpp`
- AOSP `android-17.0.0_r1`：`system/vold/model/EmulatedVolume.cpp`
- Android common kernel `android17-6.18-2026-06_r6`：`fs/fuse/Kconfig`
- Android common kernel `android17-6.18-2026-06_r6`：`fs/fuse/Makefile`
- Android common kernel `android17-6.18-2026-06_r6`：`fs/fuse/backing.c`
- Android common kernel `android17-6.18-2026-06_r6`：`fs/fuse/passthrough.c`
- Android common kernel `android17-6.18-2026-06_r6`：`fs/fuse/iomode.c`
- Android common kernel `android17-6.18-2026-06_r6`：`fs/fuse/fuse_bpf_backing.c`
- Android common kernel `android17-6.18-2026-06_r6`：`include/uapi/linux/fuse.h`
- Android common kernel `android17-6.18-2026-06_r6`：`include/uapi/linux/android_fuse.h`
- [AOSP：FUSE passthrough](https://source.android.com/docs/core/storage/fuse-passthrough)
- [AOSP：Scoped storage](https://source.android.com/docs/core/storage/scoped)
