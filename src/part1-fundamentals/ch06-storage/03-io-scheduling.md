---


status: finalized
title: I/O 调度与性能
chapter: '6.3'
section: '6.3'
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-05-09'
last_verified_against: Linux 6.12 + Android 16 GKI + Android 17 Baklava preview
confidence: medium
sources:
- type: material
  path: Cubox/IO调度器详解-2024-03-08.md
- type: material
  path: Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md
- type: material
  path: Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md
tags:
- linux
- android
- research
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
---
# 6.3 I/O 调度与性能

## 从 D 状态开始，但不要停在 D 状态

主线程出现一段 `D`（uninterruptible sleep）时，I/O 是重要嫌疑，却还不能直接定案。`D` 表示线程睡在不可中断等待点，等待对象也可能是驱动、内存回收或其他内核资源。Perfetto 的 `thread_state.io_wait=1`、`sched_blocked_reason`、文件系统 tracepoint 和 block 事件能进一步缩小范围。

即便调用栈落在 `read()` 或 `fsync()`，延迟也可能来自不同位置：

1. Page Cache miss 或脏页回写。
2. ext4 journal、F2FS checkpoint/GC 等文件系统工作。
3. request 进入块层后等待 scheduler dispatch。
4. device-mapper、inline crypto、UFS host 与设备内部队列。
5. UFS 固件的 cache flush、FTL GC、磨损控制和温度策略。

I/O scheduler 只负责块层请求进入设备前的一段。它能影响请求顺序、带宽份额和队列深度，无法抢占已经发给设备的命令，也无法修复主线程上设计不当的同步写。

> 源码锚点：Android 17 / API 37 / `android-17.0.0_r1`，Android Common Kernel `android17-6.18-2026-06_r6`。

## blk-mq 与 I/O scheduler 的位置

现代 Linux 块层使用 blk-mq。软件提交队列把请求分发到一个或多个硬件队列，驱动再把命令交给控制器。可选的 elevator 位于 request queue 上，用来合并、排序或限流尚未 dispatch 的请求。

UFS 没有机械磁头，但 scheduler 仍可能有价值：

- 读与同步写对交互延迟敏感，后台顺序写更重视吞吐。
- 设备队列过深会增加排队时间；过浅又可能浪费并行度。
- 多个进程或 cgroup 需要隔离。
- 相邻请求合并可减少软件和设备命令开销。

“闪存随机访问很快”不等于“请求顺序不再重要”。UFS 的读写不对称、SLC cache、内部并行单元与 FTL 回收都会让尾延迟随队列形态变化。

## CFQ、BFQ、mq-deadline、Kyber 与 `none`

这几个名字不构成一条固定的 Android 版本替换表。CFQ 属于旧 single-queue 块层；BFQ、mq-deadline 和 Kyber 都可工作在 blk-mq 上；`none` 表示目标 request queue 不挂 elevator。Android 版本、GKI 能力、vendor kernel 配置与块设备最终选择要分开看。

### CFQ：历史背景

CFQ（Completely Fair Queuing）为每个 I/O context 管理队列，并通过时间片和优先级分配设备服务。它曾是通用 Linux 配置中的重要调度器，但没有进入当前 6.18 blk-mq scheduler 集合。

把 CFQ 简化成“所有进程完全相同”并不准确：CFQ 支持 I/O class 与 priority。它退出当前内核的主要背景是块层迁移到 blk-mq，不能归因于一个 Android 前后台场景。

### BFQ：按 budget 分配服务

BFQ（Budget Fair Queueing）按权重和 budget 为队列分配服务，目标是在吞吐、公平性和交互延迟之间取得平衡。启用 `CONFIG_BFQ_GROUP_IOSCHED` 后，它还能进行 cgroup 层级调度。

BFQ 的 per-request 处理和队列管理比 mq-deadline 复杂。在较慢设备、需要比例带宽或交互保障的负载上，这份成本可能值得；在高 IOPS 设备上，额外调度工作也可能限制吞吐。不能用“最低延迟一定是 mq-deadline 的数倍”概括所有设备。

Android 17 的 6.18 `Kconfig.iosched` 把 BFQ 保留为可选项，但 arm64 GKI defconfig 没有显式启用 `CONFIG_IOSCHED_BFQ`。vendor 可以改变配置，因此实机上是否出现 `bfq` 仍以 sysfs 为准。

### mq-deadline：位置队列、FIFO 与 I/O class

mq-deadline 为 RT、BE、IDLE 三种 I/O class 分别维护读写队列。每个请求同时进入按 sector 排序的红黑树和按到期时间排列的 FIFO；调度器通常沿 sector 顺序批量 dispatch，并在批次边界处理超期请求。

下面的源码常量用于说明 Android 17 内核的默认软期限，摘自 `block/mq-deadline.c`：

```c
static const int read_expire = HZ / 2;
static const int write_expire = 5 * HZ;
static const int prio_aging_expire = 10 * HZ;
static const int writes_starved = 2;
static const int fifo_batch = 16;
```

`read_expire=500ms` 和 `write_expire=5s` 是 scheduler 开始考虑 dispatch 的软期限，不能当作设备完成延迟上限。`writes_starved=2` 表示读优先达到一定次数后要照顾写队列，它也不是固定“读写 2:1”带宽比例。

6.18 实现会把 `IOPRIO_CLASS_NONE` 映射到 BE，并识别 RT/BE/IDLE class。优先级 class 可以影响 dispatch；class 内的 0–7 level 是否生效则依赖 scheduler，不能只看 `ionice` 命令返回成功。

### Kyber：用 token 控制队列深度

Kyber 把请求分成 READ、WRITE、DISCARD 和 OTHER 域，通过 token 限制各域在途深度，并根据延迟直方图调整。6.18 源码中的默认 target 是读 2 ms、写 10 ms、discard 5 s。这些值用于内部控制，不承诺每个请求在目标时间内完成。

Linux 的通用 I/O priority 文档把 BFQ 和 mq-deadline 列为支持者；因此需要 `ionice` 或 cgroup I/O class 时，不应假设 Kyber 会提供相同效果。

### `none`：不挂 elevator

`none` 会跳过可选 scheduler 的排序和 QoS 策略。blk-mq、plugging、request 构造、硬件 tag 与驱动队列仍然存在，部分合并也可能发生。把 `none` 说成“完全没有块层处理”会误导排查。

### Android 17 提供什么，设备选择什么

6.18 的 `Kconfig.iosched` 默认提供 mq-deadline 与 Kyber，BFQ 是可选配置。一个设备的动态分区可能显示为 `dm-*`，直接承载请求的 UFS LUN 又是另一个 request queue；应沿 device-mapper 找到叶子块设备，再读取其 scheduler。

下面的命令用于列出设备上所有可见 request queue 的当前与候选 scheduler：

```bash
adb shell 'for q in /sys/block/*/queue/scheduler; do
  printf "%s: " "$q"
  cat "$q"
done'
```

方括号包围的名字是当前选择。某个设备只显示 `[none]` 可能来自驱动能力、queue 类型或内核配置，不能推导成 Android 17 的统一默认。

## I/O priority：先问谁消费它

Linux 的 `ioprio_set()` 和 `ionice` 使用三种通用 class：

- **RT**：高于 BE/IDLE，持续高负载可能使低 class 饥饿。
- **BE**：普通 best-effort class，level 范围 0–7。
- **IDLE**：有其他工作时延后。

下面的示例只用于调试受控进程的 class，不建议把普通前台 App 任意设成 RT：

```bash
adb shell su 0 ionice -c 3 -p <pid>
adb shell su 0 ionice -c 2 -n 4 -p <pid>
```

第一条把进程设为 IDLE class，第二条设为 BE level 4。命令通常需要足够权限；scheduler 若不消费相应 class/level，设置成功也未必改变 dispatch。

Android init service 还支持 `ioprio <rt|be|idle> <0-7>`，最终通过 `SYS_ioprio_set` 设置服务进程。但 Android App 的前后台保障并非由 ActivityManager 给每个前台进程调用一次 `ionice RT`。

## Android 17 的 blkio task profile

### AOSP tag 中的基线

`android-17.0.0_r1` 的 `system/core/libprocessgroup/profiles/cgroups.json` 仍把 `blkio` 配置为 cgroup v1，挂载在 `/dev/blkio`。同一份文件的 cgroup v2 基线只列出 freezer，以及可选 memory controller；所以“Android 17 已把 I/O 全部迁到 cgroup v2”与这个 tag 不符。

`task_profiles.json` 的关键动作是：

- `LowIoPriority`：加入 `/dev/blkio/background`。
- `NormalIoPriority`、`HighIoPriority`、`MaxIoPriority`：加入 blkio 根组。
- `SCHED_SP_BACKGROUND`：包含 `LowIoPriority`。
- `SCHED_SP_FOREGROUND`：包含 `HighIoPriority`。
- `SCHED_SP_TOP_APP`：包含 `MaxIoPriority`。

这些名字容易引起误解。AOSP 的 `HighIoPriority` 和 `MaxIoPriority` 本身没有写 RT class，它们都把任务移回 blkio 根组；前台收益主要来自避开 background 组的降权和 class 限制。

下面的 init 配置摘录用于固定 Android 17 AOSP 对后台 blkio 组的初始设置，来自 `system/core/rootdir/init.rc`：

```rc
write /dev/blkio/blkio.weight 1000
write /dev/blkio/background/blkio.weight 200
write /dev/blkio/background/blkio.bfq.weight 10
write /dev/blkio/background/blkio.prio.class restrict-to-be
```

根组与后台组配置了不同权重；BFQ 专用权重只有内核和 queue 使用 BFQ 时才生效。`restrict-to-be` 来自 blk-cgroup I/O priority policy，它会限制后台请求的 class，并能作用于支持 cgroup writeback 的缓冲写。

### GKI 能力不等于产品已经启用

Android 17 arm64 GKI 开启了 `CONFIG_BLK_CGROUP`、`CONFIG_BLK_DEV_THROTTLING`、`CONFIG_BLK_CGROUP_IOCOST` 和 `CONFIG_BLK_CGROUP_IOPRIO`。这些选项说明内核具备控制器能力，产品还需要正确挂载 controller、创建层级、设置参数并选择能消费策略的 scheduler。

Android 允许 API-level 和 vendor 文件覆盖默认 `cgroups.json` / `task_profiles.json`。因此排查实机时要读取：

- `/proc/cgroups`、`/proc/<pid>/cgroup` 与 `/proc/mounts`；
- `/system/etc/task_profiles/` 和 `/vendor/etc/task_profiles.json`；
- `/dev/blkio/` 或 `/sys/fs/cgroup/` 下实际存在的控制文件；
- 叶子块设备的 `/sys/block/<dev>/queue/scheduler`。

不要同时套用 blkio v1 的 `blkio.*` 示例和 cgroup v2 的 `io.*` 示例。先确认层级版本，再解释 `blkio.weight`、`io.weight`、`io.max`、`io.prio.class` 或 `io.pressure`。

## Buffered I/O、Page Cache 与 cgroup writeback

### 读路径

普通 `read()` 先查询 Page Cache。命中时不访问存储，未命中时文件系统读取 folio，并可能触发 readahead。App 冷启动中的 dex、资源和数据库读取是否命中缓存，会显著改变耗时，所以“同一文件第二次读更快”不能用来衡量 UFS。

Page Cache 属于可回收 file-backed memory。内存压力下，内核会在活跃/非活跃 file LRU、匿名页与 swap 之间选择回收对象。后台大范围扫描可能污染缓存并增加前台 refault，但回收决策还受 memcg 保护、访问频率、working-set 检测和 swap 成本影响。

### 写路径

Buffered write 先把 folio 标为 dirty，writeback 随后把数据转成 bio/request。脏页控制横跨 memory 与 I/O：

- memory controller 决定脏内存在哪个 memory domain 统计和限速；
- I/O controller 决定 writeback bio 归到哪个 blkcg；
- 文件系统需要支持 cgroup writeback，ext4 与 F2FS 均支持；
- inode 的 writeback owner 会根据持续写入来源调整，不能把每个回写请求都归因于当时运行的 flush 线程。

缓冲写转交后台线程后，不会必然丢失原进程的 cgroup 信息。支持 cgroup writeback 的路径会把 bio 关联到 inode owner 的 blkcg。

### dirty sysctl 与 swappiness

`dirty_background_ratio`、`dirty_ratio`、对应的 `*_bytes`、`dirty_expire_centisecs` 和 `dirty_writeback_centisecs` 会影响回写触发与节奏。它们可以被产品 init 配置覆盖，也会和 backing device、memcg 阈值共同作用，不能把 Linux 常见默认值当作所有 Android 设备的现值。

Android 17 AOSP 只在 low-RAM 或 batteryless 等特定条件下写入部分参数，例如 low-RAM 分支把 `dirty_background_ratio` 设为 5。这不代表所有 Android 17 设备都使用 5。

`swappiness` 描述 swap I/O 与 filesystem paging 的相对成本，范围 0–200，100 表示两者成本相同。它影响匿名页与 file-backed page 的回收权衡，不是“Page Cache 最大占比”。Android 通常使用 zram，合适值仍要结合压缩成本、refault 和产品内存容量测量。

下面的命令用于采集现场内存与 I/O 控制参数：

```bash
adb shell 'for f in \
  dirty_background_bytes dirty_background_ratio \
  dirty_bytes dirty_ratio swappiness; do
  printf "%s=" "$f"
  cat "/proc/sys/vm/$f"
done'
adb shell cat /proc/pressure/io
```

第一组输出应和设备 init 配置一起解释；PSI 的 `some`/`full` 表示任务因 I/O 停顿的时间比例，比一个孤立的 CPU iowait 百分比更适合描述系统压力。

## Direct I/O 与 Buffered I/O

### Buffered I/O 适合多数 App

Page Cache 可以合并小写、提供 readahead，并让热点数据复用。数据库、配置、资源和代码文件普遍依赖这些能力。写入先返回到用户态不代表已经持久化，崩溃一致性仍由事务、`fsync()` 和文件系统语义保证。

### `O_DIRECT` 的边界

`O_DIRECT` 尝试让文件数据 I/O 绕过 Page Cache。它适合应用自带缓存、访问模式明确且能满足对齐约束的系统软件。Linux 6.18 可通过 `statx(..., STATX_DIOALIGN)` 查询文件系统报告的 direct-I/O 对齐要求。

几个限制需要记住：

- buffer 地址、长度和文件 offset 常有对齐要求；
- 绕过 Page Cache 会失去普通 readahead 和缓存复用；
- `O_DIRECT` 不提供持久化保证，必要时仍要 `fsync()`；
- 同一文件混用 buffered 与 direct I/O 会增加一致性和失效处理难度；
- inline encryption、device-mapper 或驱动可能增加 bounce、拆分等成本。

AOSP SQLite 的 Unix VFS 以普通缓冲文件 I/O 为基线，F2FS batch atomic write 也是另一套 ioctl 能力。没有源码证据时，不应声称 Android SQLite 的 WAL 默认使用 Direct I/O。

## Perfetto：从线程等待走到块设备

### 录制数据要够

要分析这条路径，trace 至少需要 scheduler 数据；进一步定位还要按设备开放情况加入：

- `sched_switch`、`sched_wakeup`、`sched_blocked_reason`；
- `block_rq_insert`、`block_rq_issue`、`block_rq_complete`；
- `writeback:*`；
- `ext4:*` 或 `f2fs:*` 中的 sync、writeback、checkpoint、GC 事件；
- UFS、device-mapper 与 PSI 数据。

`sched_blocked_reason` 在不同 build type 和内核配置上的可用性不同。没有它时，`thread_state.io_wait` 可能为 NULL，此时不能把所有 `D` 都标记成 I/O。

### 第一问：哪些线程在 I/O sleep

下面的 PerfettoSQL 用于聚合明确标记 `io_wait=1` 的 D 状态，兼容 Android 17 对应的 `thread_state` schema：

```sql
SELECT
  COALESCE(process.name, '[kernel]') AS process_name,
  thread.name AS thread_name,
  ROUND(SUM(thread_state.dur) / 1e6, 2) AS iowait_ms,
  ROUND(MAX(thread_state.dur) / 1e6, 2) AS max_wait_ms
FROM thread_state
JOIN thread USING (utid)
LEFT JOIN process USING (upid)
WHERE thread_state.state = 'D'
  AND thread_state.io_wait = 1
GROUP BY thread.utid, process.name, thread.name
ORDER BY iowait_ms DESC
LIMIT 20;
```

查询结果给出线程等待总量和单次最大值，没有说明等待的是哪个文件或块设备。下一步仍要回到对应时间窗，检查调用栈、文件系统 slice 和 block 请求。

### 第二问：块设备队列是否积压

下面的查询用于统计 trace 中各 block device 的最大和平均在队列/设备中的操作数：

```sql
INCLUDE PERFETTO MODULE linux.block_io;

SELECT
  dev,
  MAX(ops_in_queue_or_device) AS max_ops,
  ROUND(AVG(ops_in_queue_or_device), 2) AS avg_ops
FROM linux_active_block_io_operations_by_device
GROUP BY dev
ORDER BY max_ops DESC;
```

这个 stdlib view 基于 `track.type='block_io'` 的 slice。录制中没有 block issue/complete 数据时，查询不会凭空生成结果；device id 还要映射到实机的 major:minor 和 device-mapper 层。

### 第三问：等待发生在哪一层

把同一时间窗的证据对齐：

- `sync_file_enter/exit` 很长，block queue 不深：关注 journal/checkpoint、锁、writeback 或 flush。
- issue 到 complete 很长：关注设备排队、UFS、加密、dm 层和器件状态。
- `D` 很长但 `io_wait` 不明确，block 事件也安静：检查 blocked function、reclaim、binder/driver wait。
- 后台 `wbytes/wios` 上升且前台 refault/major fault 增多：同时检查 blkio、memcg 和 Page Cache 竞争。
- `io.pressure` 的 `full` 持续上升：系统有一段时间所有非 idle 任务都因 I/O 受阻，需要结合 CPU、内存和块层判断原因。

不要使用跨设备固定的“fsync 超过 5ms”“随机读超过 1ms”或“iowait 超过 5%”作为异常线。UFS 代际、容量、温度、文件系统、队列深度和 trace 开销都会改变分布。更可靠的基线来自同机型、同镜像、同电量温度和同 workload 的 P50/P95/P99。

### CPU iowait 的含义

CPU iowait 是 CPU idle 记账中的一个状态，无法精确归属到某个 App，也不会等于所有线程 I/O 等待时间之和。异步 writeback 可能让设备很忙而 CPU iowait 很低；一个线程等待 I/O 时，其他 runnable 线程也可能让 CPU 保持忙碌。

因此，CPU iowait 适合当系统线索；线程 `io_wait`、I/O PSI、block queue、文件系统事件和应用调用栈才构成定位证据。

## SQLite、Room 与 SharedPreferences：优先减少同步工作

调度策略可以减轻竞争，却不能让一次不必要的主线程事务变得合理。App 侧优先检查：

1. **事务边界**：把同一业务动作的多条数据库修改放在一个事务中，避免循环自动提交。
2. **线程边界**：Room 默认拒绝主线程数据库访问；使用 `suspend`、Flow、RxJava 或 executor 等异步 DAO，不要开启 `allowMainThreadQueries()` 规避限制。
3. **WAL 条件**：WAL 常能改善读写并发，但仍有 WAL sync、checkpoint、文件增长和多进程边界。按 workload 验证。
4. **SharedPreferences**：`apply()` 把磁盘写排到后台，连续调用仍制造 I/O，生命周期切换也可能等待排队任务。
5. **开发期检查**：StrictMode 可发现主线程磁盘访问；release 性能仍需 Perfetto、数据库统计和现场分位数。

Android 17 的 AOSP SQLite 编译了 F2FS batch atomic write 支持，运行时还要由 Unix VFS 探测文件系统 ioctl 并满足 pager 条件。它可以减少部分 journal 工作，但不保证每个事务绕开同步或块层竞争。

## `io_uring` 与 FUSE：存在能力不等于路径已使用

6.18 Kconfig 默认提供 `IO_URING`，Android 17 GKI 也启用 FUSE/FUSE BPF。由此只能确认内核能力。若要声称 Android 17 的某条 MediaProvider、外部存储或 OTA 路径使用 io_uring，需要找到对应 AOSP 调用点、进程权限、设备配置与 trace 事件。

“io_uring 让 FUSE 快 40%”或“dm-verity 并行哈希让冷读快 35%”都缺少可迁移到所有 Android 17 设备的前提，不能作为平台结论。

## 现场检查清单

| 问题 | 证据 |
|---|---|
| 请求落到哪个叶子块设备？ | `/proc/mounts`、`ls -l /sys/dev/block/<major>:<minor>`、dm 映射 |
| 当前 elevator 是什么？ | `/sys/block/<dev>/queue/scheduler` |
| 线程在哪个 I/O cgroup？ | `/proc/<tid>/cgroup` |
| v1 还是 v2，参数是否存在？ | `/proc/cgroups`、`/proc/mounts`、`/dev/blkio`、`/sys/fs/cgroup` |
| Page Cache 是否反复失效？ | major fault、`workingset_refault_file`、memcg `memory.stat` |
| 脏页是否在回写或限速？ | `file_dirty`、`file_writeback`、`writeback:*` |
| 系统是否普遍被 I/O 阻塞？ | `/proc/pressure/io` 或 cgroup `io.pressure` |
| 延迟在文件系统还是设备？ | `*_sync_file_*`、checkpoint/GC、`block_rq_*`、UFS trace |

## 参考资料与源码锚点

### Android 17 / kernel 6.18 源码

- `kernel/common/block/Kconfig.iosched`：mq-deadline、Kyber、BFQ 配置边界。
- `kernel/common/block/mq-deadline.c`：deadline 队列、软期限与 I/O class。
- `kernel/common/block/kyber-iosched.c`：调度域、token 与 latency target。
- `kernel/common/block/blk-ioprio.c`：cgroup I/O priority policy 与 `prio.class`。
- `kernel/common/Documentation/admin-guide/cgroup-v2.rst`：I/O controller 与 cgroup writeback。
- `kernel/common/arch/arm64/configs/gki_defconfig`：Android 17 arm64 GKI blk-cgroup 能力。
- `system/core/libprocessgroup/profiles/cgroups.json`：Android 17 controller 基线。
- `system/core/libprocessgroup/profiles/task_profiles.json`：前后台 I/O profiles。
- `system/core/rootdir/init.rc`：blkio 根组与 background 组参数。
- `system/core/init/service_parser.cpp`：init service 的 `ioprio` 解析。
- `external/perfetto/src/trace_processor/perfetto_sql/stdlib/linux/block_io.sql`：block I/O stdlib view。

### 官方文档

- [AOSP cgroup abstraction layer](https://source.android.com/docs/core/perf/cgroups)
- [Linux block I/O priorities](https://docs.kernel.org/block/ioprio.html)
- [Linux mq-deadline](https://docs.kernel.org/block/deadline-iosched.html)
- [Linux BFQ](https://docs.kernel.org/block/bfq-iosched.html)
- [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [Linux VM sysctl](https://docs.kernel.org/admin-guide/sysctl/vm.html)
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Perfetto CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)

## 小结

排查 Android I/O 卡顿时，按顺序回答四个问题：

1. 线程是否处于明确的 I/O sleep，还是另一种不可中断等待？
2. 延迟在 Page Cache/回写、文件系统、块层 scheduler，还是设备完成阶段？
3. 实机使用哪一个 scheduler，线程在哪个 task profile 与 blkio/io cgroup？
4. App 能否通过减少事务、主线程磁盘访问和无效小写降低同步压力？

Android 17 的 GKI 提供 mq-deadline、Kyber 和多种 blk-cgroup QoS 能力，BFQ 仍是可选项；AOSP task profile 基线继续用 blkio v1 区分 background 与根组。vendor 可以覆盖这些配置，所以任何“Android 17 默认 scheduler”结论都要回到实机验证。

应用配置持久化的同步边界见 6.4，MediaProvider/FUSE 共享存储路径见 6.5。
