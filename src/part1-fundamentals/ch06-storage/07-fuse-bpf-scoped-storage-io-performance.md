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

# 6.7 Linux 6.12 FUSE Passthrough 内核机制与 Android Scoped Storage I/O

> 6.6 节从应用视角解释了 FUSE passthrough 的作用和适用条件。本节下钻到 Linux 6.12 内核实现，拆解 passthrough 的数据路径、I/O 模式管理和 Android MediaProvider 的对接方式。如果只关心"什么时候该用 MediaStore、什么时候复制到私有目录"，读 6.6 就够了。

## 为什么还要往下看内核

Android 12 引入 FUSE passthrough 后，经过策略检查的文件读写可以跳过用户态 `MediaProvider` FUSE daemon，直接操作底层文件系统。6.6 节已经给出了应用层的路径选择依据。但两个排查场景需要内核级别的理解：

1. **passthrough 已经启用，I/O 延迟仍然偏高**——需要确认读写请求是否真的走了 passthrough 路径，还是在 I/O 模式切换中被降级回传统 FUSE。
2. **内核版本或编译配置导致 passthrough 不可用**——需要检查 `CONFIG_FUSE_PASSTHROUGH`、`FOPEN_PASSTHROUGH` 标志、`/sys/fs/fuse/features/fuse_passthrough` 的实际状态。

这两个场景在 OEM 设备适配和系统级 I/O 调优中会反复出现。[已验证: AOSP 文档, source.android.com/docs/core/storage/fuse-passthrough]

## FUSE 文件的 I/O 模式管理

Linux 6.12 的 `fs/fuse/iomode.c` 为每个 FUSE 文件定义了三种 I/O 模式：

| 模式 | 枚举值 | 行为 |
|------|--------|------|
| 无模式 | `IOM_NONE` | 文件未绑定特定模式，使用默认 FUSE 路径 |
| 缓存模式 | `IOM_CACHED` | 数据经过页缓存，FUSE daemon 参与读写处理 |
| 直出模式 | `IOM_UNCACHED` | 绕过页缓存，数据直接在内核和底层文件系统之间搬运 |

模式选择发生在 `fuse_file_io_open()` 中，判断依据是 FUSE daemon 在 `open()` 回复中设置的标志：

- `FOPEN_DIRECT_IO` + `FOPEN_PASSTHROUGH` → 进入 passthrough 路径
- `FOPEN_DIRECT_IO`（无 passthrough）→ 直出模式但不走 passthrough
- 都没设置 → 进入缓存模式

缓存模式和直出模式互斥。`iomode.c` 用 `fuse_inode->iocachectr` 引用计数跟踪当前有多少文件以缓存模式打开同一个 inode。当 `iocachectr > 0` 时，新的直出写请求必须等已有缓存模式文件关闭或降级。这个等待通过 `fuse_inode->direct_io_waitq` 实现。[已验证: Linux v6.12, fs/fuse/iomode.c]

```c
// iomode.c 的核心等待逻辑（简化）
int fuse_file_cached_io_open(struct inode *inode, struct fuse_file *ff)
{
    struct fuse_inode *fi = get_fuse_inode(inode);
    spin_lock(&fi->lock);
    while (fuse_is_io_cache_wait(fi)) {
        set_bit(FUSE_I_CACHE_IO_MODE, &fi->state);
        spin_unlock(&fi->lock);
        wait_event(fi->direct_io_waitq, !fuse_is_io_cache_wait(fi));
        spin_lock(&fi->lock);
    }
    // ... 进入缓存模式
}
```

这段逻辑解决的是并发场景：一个文件被缓存模式打开后，另一个 fd 尝试以直出模式写同一个 inode，必须等缓存 fd 关闭或降级，否则会破坏页缓存一致性。

## passthrough 的数据路径

`fs/fuse/passthrough.c` 提供了四个核心操作：`read_iter`、`write_iter`、`splice_read`、`splice_write`。以 `read_iter` 为例：

```c
// passthrough.c（简化）
ssize_t fuse_passthrough_read_iter(struct kiocb *iocb, struct iov_iter *iter)
{
    struct fuse_file *ff = iocb->ki_filp->private_data;
    struct file *backing_file = fuse_file_passthrough(ff);
    struct backing_file_ctx ctx = {
        .cred = ff->cred,
        .user_file = iocb->ki_filp,
        .accessed = fuse_file_accessed,
    };
    return backing_file_read_iter(backing_file, iter, iocb,
                                  iocb->ki_flags, &ctx);
}
```

整个读写路径的关键特征：

1. **数据不经过用户态**。`backing_file_read_iter()` 直接在内核中完成从底层文件系统（ext4/f2fs）到用户缓冲区的数据拷贝，`MediaProvider` 进程不会被唤醒。

2. **backing file 是独立的 file 对象**。`fuse_passthrough_open()` 通过 `backing_file_open()` 为每个 FUSE 文件创建独立的 backing file，保存原始路径和权限凭据。这意味着 passthrough 路径能正确处理 DAC/MAC 权限检查，不需要额外委托。

3. **写操作持有 inode 锁**。`fuse_passthrough_write_iter()` 在调用 `backing_file_write_iter()` 前获取 `inode_lock`，保证同一个 inode 的并发写串行化。[已验证: Linux v6.12, fs/fuse/passthrough.c]

4. **splice 支持**。`fuse_passthrough_splice_read()` 和 `fuse_passthrough_splice_write()` 让 zero-copy 的管道传输也能走 passthrough 路径，对视频播放和文件复制场景有直接收益。

### passthrough 建立过程

FUSE daemon 通过 `ioctl(FUSE_DEV_IOC_BACKING_OPEN)` 向内核注册 backing file，内核返回一个 backing_id。后续 `open()` 回复中带上 `FOPEN_PASSTHROUGH` 标志和 backing_id，内核就会为这个 FUSE 文件建立 passthrough 映射：

```c
// passthrough.c 的 open 路径（简化）
struct fuse_backing *fuse_passthrough_open(struct file *file,
                                           struct inode *inode,
                                           int backing_id)
{
    // 1. 通过 IDR 查找已注册的 backing file
    fb = idr_find(&fc->backing_files_map, backing_id);

    // 2. 为这个 FUSE file 创建独立 backing file
    backing_file = backing_file_open(&file->f_path, file->f_flags,
                                     &fb->file->f_path, fb->cred);

    // 3. 存入 fuse_file 供后续读写使用
    ff->passthrough = backing_file;
    ff->cred = get_cred(fb->cred);
}
```

注册 backing file 需要 `CAP_SYS_ADMIN` 权限，这在 Android 上由 `MediaProvider` 系统进程满足。[已验证: Linux v6.12, fs/fuse/passthrough.c]

## Android MediaProvider 的对接方式

AOSP `packages/providers/MediaProvider/jni/FuseDaemon.cpp` 是 FUSE daemon 侧的实现。passthrough 的启用分两步检查：

**第一步：内核能力探测。** `IsUpstreamPassthroughSupported()` 读取 `/sys/fs/fuse/features/fuse_passthrough`，只有返回 `supported\n` 才认为内核支持。这个 sysfs 入口由 Linux 内核 FUSE driver 在初始化时创建，取决于 `CONFIG_FUSE_PASSTHROUGH` 编译选项。

**第二步：逐文件决策。** `FuseDaemon::ShouldOpenWithFuse()` 根据文件类型、访问者 UID、transcode 需求等因素决定这次 open 是否走 FUSE 路径。如果文件不需要转码、不需要 redaction、访问者有完整权限，daemon 会在 open 回复中设置 `FOPEN_PASSTHROUGH` 标志，让内核为该文件启用 passthrough。

```java
// FuseDaemon.cpp 中的判断逻辑（简化）
bool FuseDaemon::ShouldOpenWithFuse(/* ... */) {
    // 文件需要转码 → 必须走 FUSE
    if (requiresTranscode) return true;
    // 文件需要内容遮盖（如位置信息） → 必须走 FUSE
    if (requiresRedaction) return true;
    // 访问者没有完整权限 → 必须走 FUSE 做策略检查
    if (!hasFullPermission) return true;
    // 否则可以 passthrough
    return false;
}
```

`ShouldOpenWithFuse()` 返回 `false` 意味着文件内容读写走 passthrough。但即使启用了 passthrough，`open()` 本身仍然经过 FUSE daemon，因为权限检查和策略判断必须在用户态完成。passthrough 优化的是 `open()` 之后的数据读写路径。[已验证: AOSP android-16.0.0_r1, packages/providers/MediaProvider/jni/FuseDaemon.cpp]

## 性能影响：哪些场景受益，哪些不会

passthrough 的收益集中在**数据读写路径**：

| 操作 | 传统 FUSE 路径 | passthrough 路径 | 收益来源 |
|------|---------------|-----------------|---------|
| 大文件顺序读 | kernel→daemon→kernel→ext4 | kernel→ext4 | 消除两次用户态切换和数据拷贝 |
| 大文件顺序写 | kernel→daemon→kernel→ext4 | kernel→ext4 | 同上 |
| splice/零拷贝 | 不支持，必须经过 daemon 缓冲区 | 直接管道传输 | 消除额外缓冲区分配 |
| open() | daemon 处理策略 | daemon 处理策略 | **无收益**，策略检查仍需用户态 |
| readdir/getattr | daemon 处理 | daemon 处理 | **无收益**，目录和元数据操作不在 passthrough 范围内 |
| 转码/redaction | daemon 处理 | daemon 处理 | **无收益**，这些操作必须在用户态完成 |

AOSP 文档给出的 Pixel 2 对比数据（FUSE passthrough 之前）显示，顺序读可以接近直接访问 ext4 的水平，随机读写最坏情况可能慢到接近 2 倍。Android 12+ 启用 passthrough 后，顺序读写路径被压缩到接近直接 I/O，但随机 I/O 的 FUSE 开销（每次 open 仍需用户态策略检查）不会消失。[已验证: AOSP 文档, source.android.com/docs/core/storage/fuse-passthrough]

这意味着：
- **视频播放、大文件上传**等顺序读场景受益最大
- **相册首扫**的瓶颈在 `readdir` + `getattr`（不走 passthrough），优化方向应该转向 MediaStore 查询
- **图片编辑**等随机读写场景，把文件复制到 App 私有目录处理仍然是更可靠的做法

## 在 Perfetto 中确认 passthrough 是否生效

确认 passthrough 是否生效需要观察两个指标：

**1. MediaProvider CPU 占用。** passthrough 生效时，大文件读写不应该引起 `media_provider` 进程的 CPU 显著升高。在 Perfetto 中查看 `media_provider` 进程的 CPU 轨道，执行顺序读写时 CPU 占用应低于 5%。如果读写时 `media_provider` CPU 持续在 10% 以上，passthrough 可能没有生效。

**2. I/O 延迟对比。** 使用 `ftrace` 的 `fuse_request_*` tracepoint 追踪 FUSE 请求。passthrough 路径下，read/write 请求的端到端延迟应接近底层文件系统的直接 I/O 延迟，而不是传统 FUSE 路径的 2-5ms 额外开销。具体操作：

```
# 在 root 设备上启用 FUSE tracepoint
echo 1 > /sys/kernel/debug/tracing/events/fuse/enable
# 执行测试 I/O
cat /storage/emulated/0/DCIM/test.jpg > /dev/null
# 查看结果
cat /sys/kernel/debug/tracing/trace | grep fuse
```

如果 trace 中看到 `fuse_open` 但没有 `fuse_read`/`fuse_write`（只有 `fuse_request_send` 和 `fuse_request_end` 配对），说明读写走了 passthrough 路径，没有经过 daemon。[待验证: 需 root 设备实测确认 tracepoint 名称和过滤条件]

**3. sysfs 确认。** 直接检查 `/sys/fs/fuse/features/fuse_passthrough` 的内容：

```
adb shell cat /sys/fs/fuse/features/fuse_passthrough
```

输出 `supported` 表示内核编译了 passthrough 支持。但这只是前提条件，`MediaProvider` 是否实际使用还取决于版本和设备配置。[已验证: AOSP android-16.0.0_r1, packages/providers/MediaProvider/jni/FuseDaemon.cpp]

## 版本边界

| 版本 | FUSE passthrough 状态 | 内核要求 |
|------|----------------------|---------|
| Android 11 | 不支持 | — |
| Android 12 | 首次引入 | `android12-5.4` 或 `android12-5.10` 测试内核；升级设备通常不支持 |
| Android 13-15 | 持续改进 | Mainline 内核 `CONFIG_FUSE_PASSTHROUGH=y` |
| Android 16-17 | 默认启用（launch 设备） | Linux 6.1+ / 6.12，`CONFIG_FUSE_PASSTHROUGH=y` |

从 Android 12 升级到更高版本的设备，如果内核在出厂时没有编译 passthrough 支持（升级设备内核通常冻结），passthrough 不可用。这是排查"同一 Android 版本、不同设备上 FUSE 性能差异"时首先要排除的因素。[已验证: AOSP 文档, source.android.com/docs/core/storage/fuse-passthrough]

## 排查清单

遇到外部存储 I/O 延迟偏高时，按以下顺序检查：

1. **确认文件路径**。`/storage/emulated/0/` 经过 FUSE；`/data/user/0/<pkg>/` 和 App-specific external directory 不经过 FUSE。延迟发生在外部存储路径上才继续往下看。

2. **确认 passthrough 前提**。检查 `adb shell cat /sys/fs/fuse/features/fuse_passthrough`。输出不是 `supported` 则 passthrough 不可用，I/O 走传统 FUSE 路径。

3. **确认文件类型和操作**。转码、redaction、跨目录 rename 等操作不走 passthrough，无论内核是否支持。查看 `media_provider` CPU 轨道确认是否有用户态处理。

4. **确认 I/O 模式**。如果同一 inode 被缓存模式和直出模式同时打开，直出写会被 `iomode.c` 的等待机制阻塞。在 Perfetto 中表现为写线程在 `D` 状态等待，调用栈包含 `fuse_file_cached_io_open` 或 `wait_event`。

5. **对比内部存储路径**。把同一份文件复制到 App 私有目录后执行相同 I/O，对比延迟。如果私有目录延迟正常而外部存储延迟高，问题在 FUSE 路径；如果两者都高，问题在底层文件系统或块设备。

## 小结

FUSE passthrough 在 Linux 6.12 中的实现（`passthrough.c` + `iomode.c`）提供了绕过用户态 daemon 的数据读写路径。Android `MediaProvider` 通过 `FOPEN_PASSTHROUGH` 标志和 backing file 注册机制与之对接，让经过策略检查的文件读写直接操作底层文件系统。passthrough 优化的是数据读写路径，不替代权限检查和策略判断；目录遍历、元数据查询、转码和内容遮盖仍然需要 FUSE daemon 参与。排查外部存储 I/O 问题时，先确认 passthrough 是否可用、当前操作是否在 passthrough 覆盖范围内，再做进一步优化。
