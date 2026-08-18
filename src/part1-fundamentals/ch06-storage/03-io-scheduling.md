---
status: ready-for-review
title: I/O 调度与性能
chapter: '6.3'
section: '6.3'
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-18'
last_verified_against: AOSP android-17.0.0_r1, Android Common Kernel android17-6.18-2026-06_r6, Linux/Android/Perfetto official docs
confidence: medium-high
sources:
- type: material
  path: Cubox/IO调度器详解-2024-03-08.md
- type: material
  path: Personal-Knowlodge/source/2026-03-08_wechat_手机Android存储性能优化架构分析_1.md
- type: material
  path: Personal-Knowlodge/source/2026-03-07_wechat_性能优化基础_深入理解Linux文件系统.md
- type: aosp-kernel
  path: 'kernel/common block/Kconfig.iosched, block/mq-deadline.c, block/kyber-iosched.c, block/blk-ioprio.c @ android17-6.18-2026-06_r6'
- type: aosp-kernel
  path: 'kernel/common arch/arm64/configs/gki_defconfig, Documentation/admin-guide/cgroup-v2.rst, Documentation/admin-guide/sysctl/vm.rst, include/uapi/linux/stat.h @ android17-6.18-2026-06_r6'
- type: aosp
  path: 'system/core/libprocessgroup/profiles/cgroups.json, task_profiles.json; rootdir/init.rc @ android-17.0.0_r1'
- type: aosp
  path: 'system/core/init/service_parser.cpp, init/service_utils.cpp, libcutils/iosched_policy.cpp @ android-17.0.0_r1'
- type: aosp
  path: 'external/perfetto/src/trace_processor/perfetto_sql/stdlib/linux/block_io.sql @ android-17.0.0_r1'
- type: aosp
  path: 'external/sqlite/dist/Android.bp, dist/sqlite-autoconf-3500600/sqlite3.c @ android-17.0.0_r1'
- type: official
  path: 'https://source.android.com/docs/core/perf/cgroups'
- type: official
  path: 'https://docs.kernel.org/block/ioprio.html'
- type: official
  path: 'https://docs.kernel.org/block/deadline-iosched.html'
- type: official
  path: 'https://docs.kernel.org/block/bfq-iosched.html'
- type: official
  path: 'https://docs.kernel.org/admin-guide/cgroup-v2.html'
- type: official
  path: 'https://docs.kernel.org/admin-guide/sysctl/vm.html'
- type: official
  path: 'https://perfetto.dev/docs/analysis/stdlib-docs'
- type: official
  path: 'https://perfetto.dev/docs/data-sources/cpu-scheduling'
tags:
- linux
- android
- research
pipeline_stage: ready-for-review
task6_state: pending-review
task9_state: pending-review
task2b_state: fixed
last_rework_at: '2026-08-18T17:35:40+08:00'
last_rework_run_id: '20260818-173540-rework-07bf55ca'
---
# 6.3 I/O 调度与性能

## 从 D 状态开始，但不要停在 D 状态

主线程出现一段 `D`（uninterruptible sleep，不可中断睡眠）状态时，I/O 是重要嫌疑，却还不能直接定案。`D` 表示线程睡在不可中断的等待点，等待对象也可能是驱动、内存回收或其他内核资源。Perfetto 中的 `thread_state.io_wait=1`、`sched_blocked_reason`、文件系统 tracepoint（内核跟踪点）和 block 事件可以进一步缩小范围。

即便调用栈落在 `read()` 或 `fsync()`，延迟也可能来自不同位置：

1. Page Cache miss（页缓存未命中）或脏页回写。
2. ext4 journal（日志）、F2FS checkpoint（检查点）/GC（垃圾回收）等文件系统工作。
3. request 进入块层后等待 scheduler dispatch（调度器派发）。
4. device-mapper（设备映射层）、inline crypto（内联加密）、UFS host（主机控制器）与设备内部队列。
5. UFS 固件的 cache flush（缓存刷写）、FTL（闪存转换层）GC、磨损控制和温度策略。

I/O scheduler（I/O 调度器）只负责块层请求进入设备前的一段路径。它能影响请求顺序、带宽份额和队列深度，却无法抢占已经发给设备的命令，也无法修复主线程上设计不当的同步写。

> 源码锚点：Android 17 / API 37 / `android-17.0.0_r1`，Android Common Kernel `android17-6.18-2026-06_r6`。

## blk-mq 与 I/O scheduler 的位置

现代 Linux 块层使用 blk-mq（多队列块层）。软件提交队列把请求分发到一个或多个硬件队列，驱动再把命令交给控制器。可选的 elevator（块 I/O 调度器）位于 request queue（请求队列）上，用来合并、排序或限流尚未 dispatch 的请求。

UFS 没有机械磁头，但 scheduler 仍可能有价值：

- 读与同步写对交互延迟敏感，后台顺序写更重视吞吐。
- 设备队列过深会增加排队时间；过浅又可能浪费并行度。
- 多个进程或 cgroup（控制组）需要隔离。
- 相邻请求合并可减少软件和设备命令开销。

“闪存随机访问很快”不等于“请求顺序不再重要”。UFS 的读写不对称、SLC cache（以单层单元模式工作的高速缓存）、内部并行单元与 FTL 回收，都会让尾延迟随队列形态变化。

## CFQ、BFQ、mq-deadline、Kyber 与 `none`

这些调度器名称不构成一张固定的 Android 版本替换表。CFQ 属于旧 single-queue（单队列）块层；BFQ、mq-deadline 和 Kyber 都可以工作在 blk-mq 上；`none` 表示目标 request queue 没有挂载可选 elevator。Android 版本、GKI（Generic Kernel Image，通用内核镜像）能力、vendor kernel（厂商内核）配置与块设备的最终选择要分开判断。

### CFQ：历史背景

CFQ（Completely Fair Queuing，完全公平排队）为每个 I/O context（I/O 上下文）管理队列，并通过时间片和优先级分配设备服务。它曾是通用 Linux 配置中的重要调度器，但没有进入当前 6.18 的 blk-mq scheduler 集合。

把 CFQ 简化成“所有进程完全相同”并不准确：CFQ 支持 I/O class 与 priority。它退出当前内核的主要背景是块层迁移到 blk-mq，不能归因于一个 Android 前后台场景。

### BFQ：按 budget 分配服务

BFQ（Budget Fair Queueing，预算公平排队）按照权重和 budget（一次获准处理的数据量）为队列分配服务，目标是在吞吐、公平性和交互延迟之间取得平衡。启用 `CONFIG_BFQ_GROUP_IOSCHED` 后，它还能进行 cgroup 层级调度。

BFQ 的 per-request（逐请求）处理和队列管理比 mq-deadline 更复杂。在较慢设备、需要比例带宽或交互保障的负载上，这份成本可能值得；在高 IOPS（每秒 I/O 操作次数）设备上，额外调度工作也可能限制吞吐。不能用“最低延迟一定是 mq-deadline 的数倍”概括所有设备。

Android 17 的 6.18 `Kconfig.iosched` 把 BFQ 保留为可选项，但 arm64 GKI defconfig（默认内核配置）没有显式启用 `CONFIG_IOSCHED_BFQ`。vendor 可以改变配置，因此实机上是否出现 `bfq` 仍以 sysfs（内核导出的运行时属性接口）为准。

### mq-deadline：位置队列、FIFO 与 I/O class

mq-deadline 为 RT、BE、IDLE 三种 I/O class（优先级类别）分别维护读写队列。每个请求会同时进入按 sector（扇区位置）排序的红黑树和按到期时间排列的 FIFO（先进先出队列）；调度器通常沿 sector 顺序批量 dispatch，并在批次边界处理超期请求。

下面的源码常量用于说明 Android 17 内核的默认软期限，摘自 `block/mq-deadline.c`：

```c
static const int read_expire = HZ / 2;
static const int write_expire = 5 * HZ;
static const int prio_aging_expire = 10 * HZ;
static const int writes_starved = 2;
static const int fifo_batch = 16;
```

`read_expire=500ms` 和 `write_expire=5s` 是 scheduler 开始考虑 dispatch 的软期限，不能当作设备完成延迟上限。`writes_starved=2` 表示连续优先处理一定次数的读批次后要照顾写队列，它也不是固定的“读写 2:1”带宽比例。

6.18 实现会把 `IOPRIO_CLASS_NONE` 映射到 BE，并识别 RT/BE/IDLE class。优先级 class 可以影响 dispatch；class 内的 0–7 level（等级）是否生效则依赖 scheduler，不能只看 `ionice` 命令是否返回成功。

### Kyber：用 token 控制队列深度

Kyber 把请求分成 READ、WRITE、DISCARD 和 OTHER 域，通过 token（令牌）限制各域同时在途的请求数，并根据延迟直方图动态调整。6.18 源码中的默认 target 是读 2 ms、写 10 ms、discard 5 s。这些值用于内部控制，不承诺每个请求都在目标时间内完成。

Linux 的通用 I/O priority 文档把 BFQ 和 mq-deadline 列为支持者；因此需要 `ionice` 或 cgroup I/O class 时，不应假设 Kyber 会提供相同效果。

### `none`：不挂 elevator

`none` 会跳过可选 scheduler 的排序和 QoS（服务质量）策略。blk-mq、plugging（暂存请求以便批量提交）、request 构造、硬件 tag（队列槽位标识）与驱动队列仍然存在，部分合并也可能发生。把 `none` 说成“完全没有块层处理”会误导排查。

### Android 17 提供什么，设备选择什么

6.18 的 `Kconfig.iosched` 默认提供 mq-deadline 与 Kyber，BFQ 是可选配置。设备的动态分区可能显示为 `dm-*`，直接承载请求的 UFS LUN（逻辑单元）则对应另一个 request queue；应沿 device-mapper 映射找到叶子块设备，再读取它的 scheduler。

下面的命令用于列出设备上所有可见 request queue 的当前与候选 scheduler：

```bash
adb shell 'for q in /sys/block/*/queue/scheduler; do
  printf "%s: " "$q"
  cat "$q"
done'
```

方括号包围的名称是当前选择。某个设备只显示 `[none]`，可能源于驱动能力、queue 类型或内核配置，不能据此推导出 Android 17 的统一默认值。

## I/O priority：先问谁消费它

Linux 的 `ioprio_set()` 和 `ionice` 使用三种通用 I/O priority class：

- **RT（Real Time）**：高于 BE/IDLE，持续高负载可能使低 class 长时间得不到服务。
- **BE（Best Effort）**：普通的尽力服务类别，level 范围为 0–7。
- **IDLE**：有其他工作时延后。

下面的示例只用于调试受控进程的 class，不建议把普通前台 App 任意设成 RT：

```bash
adb shell su 0 ionice -c 3 -p <pid>
adb shell su 0 ionice -c 2 -n 4 -p <pid>
```

第一条把进程设为 IDLE class，第二条设为 BE level 4。命令通常需要足够权限；如果 scheduler 不读取相应的 class/level，即使命令设置成功，也未必改变请求派发。

Android init service 还支持 `ioprio <rt|be|idle> <0-7>`，最终通过 `SYS_ioprio_set` 设置服务进程。但 Android App 的前后台保障并不是由 ActivityManager 为每个前台进程调用一次 `ionice RT` 实现的。

## Android 17 的 blkio task profile

### AOSP tag 中的基线

`android-17.0.0_r1` 的 `system/core/libprocessgroup/profiles/cgroups.json` 仍把 `blkio` 配置为 cgroup v1，并挂载在 `/dev/blkio`。同一份文件的 cgroup v2 基线只列出 freezer（进程冻结控制器）和可选的 memory controller（内存控制器），因此“Android 17 已把 I/O 全部迁到 cgroup v2”与这个版本标签不符。

`task_profiles.json` 的关键动作是：

- `LowIoPriority`：加入 `/dev/blkio/background`。
- `NormalIoPriority`、`HighIoPriority`、`MaxIoPriority`：加入 blkio 根组。
- `SCHED_SP_BACKGROUND`：包含 `LowIoPriority`。
- `SCHED_SP_FOREGROUND`：包含 `HighIoPriority`。
- `SCHED_SP_TOP_APP`：包含 `MaxIoPriority`。

这些名称容易引起误解。AOSP 的 `HighIoPriority` 和 `MaxIoPriority` 本身没有设置 RT class，它们都只是把任务移回 blkio 根组；前台收益主要来自避开 background 组的降权和 class 限制。

下面的 init 配置摘录用于固定 Android 17 AOSP 对后台 blkio 组的初始设置，来自 `system/core/rootdir/init.rc`：

```rc
write /dev/blkio/blkio.weight 1000
write /dev/blkio/background/blkio.weight 200
write /dev/blkio/background/blkio.bfq.weight 10
write /dev/blkio/background/blkio.prio.class restrict-to-be
```

根组与后台组配置了不同权重；只有内核和目标 queue 使用 BFQ 时，BFQ 专用权重才会生效。`restrict-to-be` 来自 blk-cgroup I/O priority policy，它会把后台请求限制在 BE class，并能作用于支持 cgroup writeback（按控制组归属回写）的缓冲写。

### GKI 能力不等于产品已经启用

Android 17 arm64 GKI 开启了 `CONFIG_BLK_CGROUP`、`CONFIG_BLK_DEV_THROTTLING`、`CONFIG_BLK_CGROUP_IOCOST` 和 `CONFIG_BLK_CGROUP_IOPRIO`。这些选项只说明内核具备相应控制器能力；产品还需要正确挂载 controller（控制器）、创建层级、设置参数，并选择能够读取这些策略的 scheduler。

Android 允许 API-level 和 vendor 文件覆盖默认 `cgroups.json` / `task_profiles.json`。因此排查实机时要读取：

- `/proc/cgroups`、`/proc/<pid>/cgroup` 与 `/proc/mounts`；
- `/system/etc/task_profiles/` 和 `/vendor/etc/task_profiles.json`；
- `/dev/blkio/` 或 `/sys/fs/cgroup/` 下实际存在的控制文件；
- 叶子块设备的 `/sys/block/<dev>/queue/scheduler`。

不要混用 blkio v1 的 `blkio.*` 示例和 cgroup v2 的 `io.*` 示例。应先确认层级版本，再解释 `blkio.weight`、`io.weight`、`io.max`、`io.prio.class` 或 `io.pressure`。

## Buffered I/O、Page Cache 与 cgroup writeback

### 读路径

普通 `read()` 会先查询 Page Cache。命中时不访问存储；未命中时，文件系统读取 folio（由内核管理的一组连续内存页），并可能触发 readahead（预读）。App 冷启动中的 DEX、资源和数据库读取是否命中缓存，会显著改变耗时，因此“同一文件第二次读更快”不能用来衡量 UFS 性能。

Page Cache 属于可回收的 file-backed memory（有文件作为后备的数据页）。出现内存压力时，内核会在活跃/非活跃 file LRU（文件页最近最少使用链表）、匿名页与 swap（交换空间）之间选择回收对象。后台大范围扫描可能挤出前台仍需使用的数据，增加 refault（回收后很快再次缺页）；但回收决策还受 memcg（内存控制组）保护、访问频率、working set（工作集）检测和 swap 成本影响。

### 写路径

Buffered write（缓冲写）会先把 folio 标为 dirty（脏），writeback（回写）随后把数据转换成 `bio`（块 I/O 描述结构）/request（块层请求）。脏页控制横跨 memory 与 I/O：

- memory controller 决定脏内存在哪个 memory domain（内存记账域）统计和限速；
- I/O controller 决定 writeback `bio` 归到哪个 blkcg（块 I/O 控制组）；
- 文件系统需要支持 cgroup writeback，ext4 与 F2FS 均支持；
- inode（索引节点）的 writeback owner（回写归属者）会根据持续写入来源调整，不能把每个回写请求都归因于当时运行的 flush（刷写）线程。

缓冲写转交后台线程后，不会必然丢失原进程的 cgroup 信息。支持 cgroup writeback 的路径会把 `bio` 关联到 inode owner 所属的 blkcg。

### dirty sysctl 与 swappiness

`dirty_background_ratio`、`dirty_ratio`、对应的 `*_bytes`、`dirty_expire_centisecs` 和 `dirty_writeback_centisecs` 会影响回写触发条件与节奏。它们可以被产品 init 配置覆盖，也会与 backing device（后备存储设备）、memcg 阈值共同作用，不能把 Linux 常见默认值当作所有 Android 设备的当前值。

Android 17 AOSP 只在 low-RAM（低内存）或 batteryless（无电池）等特定条件下写入部分参数，例如 low-RAM 分支把 `dirty_background_ratio` 设为 5。这不代表所有 Android 17 设备都使用 5。

`swappiness` 描述 swap I/O 与 filesystem paging（文件页换入换出）的相对成本，范围为 0–200，100 表示两者成本相同。它影响匿名页与 file-backed page 的回收权衡，不代表“Page Cache 最大占比”。Android 通常使用 zram（内存压缩交换设备），合适的取值仍要结合压缩成本、refault 和产品内存容量测量。

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

第一组输出应与设备 init 配置一起解释；PSI（Pressure Stall Information，资源压力停顿信息）中的 `some`/`full` 表示部分任务或所有非 idle 任务因 I/O 停顿的时间比例，比一个孤立的 CPU iowait 百分比更适合描述系统压力。

## Direct I/O 与 Buffered I/O

### Buffered I/O 适合多数 App

Page Cache 可以合并小写、提供 readahead，并让热点数据复用。数据库、配置、资源和代码文件普遍依赖这些能力。写入先返回到用户态不代表已经持久化，崩溃一致性仍由事务、`fsync()` 和文件系统语义保证。

### `O_DIRECT` 的边界

`O_DIRECT` 尝试让文件数据 I/O 绕过 Page Cache。它适合自身管理缓存、访问模式明确，而且能够满足对齐约束的系统软件。Linux 6.18 可以通过 `statx(..., STATX_DIOALIGN)` 查询文件系统报告的 direct-I/O 对齐要求。

几个限制需要记住：

- buffer 地址、长度和文件 offset 常有对齐要求；
- 绕过 Page Cache 会失去普通 readahead 和缓存复用；
- `O_DIRECT` 不提供持久化保证，必要时仍要 `fsync()`；
- 同一文件混用 buffered 与 direct I/O 会增加一致性和失效处理难度；
- inline encryption、device-mapper 或驱动可能增加 bounce buffer（中转缓冲）、请求拆分等成本。

AOSP SQLite 的 Unix VFS（Unix 平台的虚拟文件系统适配层）以普通缓冲文件 I/O 为基线，F2FS batch atomic write（批量原子写）则属于另一套 ioctl（设备控制命令）能力。没有源码证据时，不应声称 Android SQLite 的 WAL（Write-Ahead Logging，预写式日志）默认使用 Direct I/O。

## Perfetto：从线程等待走到块设备

### 录制数据要够

要分析这条路径，trace 至少需要 scheduler 数据；进一步定位还要按设备开放情况加入：

- `sched_switch`、`sched_wakeup`、`sched_blocked_reason`；
- `block_rq_insert`、`block_rq_issue`、`block_rq_complete`；
- `writeback:*`；
- `ext4:*` 或 `f2fs:*` 中的 sync、writeback、checkpoint、GC 事件；
- UFS、device-mapper 与 PSI 数据。

`sched_blocked_reason` 在不同 build type（系统构建类型）和内核配置上的可用性不同。没有它时，`thread_state.io_wait` 可能为 NULL，此时不能把所有 `D` 状态都标记成 I/O 等待。

### 第一问：哪些线程在 I/O sleep

下面的 PerfettoSQL 用于聚合明确标记为 `io_wait=1` 的 D 状态，兼容 Android 17 对应的 `thread_state` schema（表结构）：

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

查询结果给出线程等待总量和单次最大值，但不会说明线程正在等待哪个文件或块设备。下一步仍要回到对应时间窗，检查调用栈、文件系统 slice（事件区间）和 block 请求。

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

这个 stdlib view（Perfetto 标准库视图）基于 `track.type='block_io'` 的 slice。录制中没有 block issue/complete 数据时，查询不会凭空生成结果；device id 还要映射到实机的 major:minor（主/次设备号）和 device-mapper 层。

### 第三问：等待发生在哪一层

把同一时间窗的证据对齐：

- `sync_file_enter/exit` 区间很长，但 block queue 不深：关注 journal/checkpoint、锁、writeback 或 flush。
- 从 issue 到 complete 的时间很长：关注设备排队、UFS、加密、dm 层和器件状态。
- `D` 状态很长，但 `io_wait` 不明确，block 事件也没有活动：检查 blocked function（阻塞函数）、reclaim（内存回收）以及 Binder/驱动等待。
- 后台 `wbytes/wios`（写入字节数/写操作数）上升，且前台 refault/major fault（需要存储读取的缺页）增多：同时检查 blkio、memcg 和 Page Cache 竞争。
- `io.pressure` 的 `full` 持续上升：系统曾有一段时间所有非 idle 任务都因 I/O 受阻，需要结合 CPU、内存和块层判断原因。

不要使用跨设备固定的“fsync 超过 5 ms”“随机读超过 1 ms”或“iowait 超过 5%”作为异常线。UFS 代际、容量、温度、文件系统、队列深度和 trace 开销都会改变分布。更可靠的基线来自同机型、同镜像、同电量与温度，以及相同 workload（工作负载）下的 P50/P95/P99（第 50/95/99 百分位）。

### CPU iowait 的含义

CPU iowait 是 CPU idle 记账中的一个状态，无法精确归属到某个 App，也不等于所有线程 I/O 等待时间之和。异步 writeback 可能让设备很忙而 CPU iowait 很低；一个线程等待 I/O 时，其他 runnable（可运行）线程也可能让 CPU 保持忙碌。

因此，CPU iowait 适合作为系统级线索；定位时还要结合线程 `io_wait`、I/O PSI、block queue、文件系统事件和应用调用栈。

## SQLite、Room 与 SharedPreferences：优先减少同步工作

调度策略可以减轻竞争，却不能让一次不必要的主线程事务变得合理。App 侧优先检查：

1. **事务边界**：把同一业务动作的多条数据库修改放在一个事务中，避免循环自动提交。
2. **线程边界**：Room 默认拒绝主线程数据库访问；应使用 `suspend`、Flow、RxJava 或 executor（任务执行器）等异步 DAO（数据访问对象），不要开启 `allowMainThreadQueries()` 绕过限制。
3. **WAL 条件**：WAL 常能改善读写并发，但仍有 WAL sync、checkpoint、文件增长和多进程边界。应按真实 workload 验证。
4. **SharedPreferences**：`apply()` 把磁盘写排到后台，连续调用仍制造 I/O，生命周期切换也可能等待排队任务。
5. **开发期检查**：StrictMode 可以发现主线程磁盘访问；release（发布版本）的性能仍需通过 Perfetto、数据库统计和现场分位数验证。

Android 17 的 AOSP SQLite 编译了 F2FS batch atomic write 支持，运行时还要由 Unix VFS 探测文件系统 ioctl，并满足 pager（页面缓存与事务管理模块）的条件。它可以减少部分 journal 工作，但不保证每个事务都能绕开同步或块层竞争。

## `io_uring` 与 FUSE：存在能力不等于路径已使用

6.18 Kconfig 默认提供 `IO_URING`，Android 17 GKI 也启用了 FUSE（Filesystem in Userspace，用户空间文件系统）和 FUSE BPF（借助内核可编程机制处理部分 FUSE 操作）。由此只能确认内核具备相关能力。若要声称 Android 17 的某条 MediaProvider、外部存储或 OTA（在线系统更新）路径使用 io_uring（Linux 异步 I/O 接口），需要找到对应的 AOSP 调用点、进程权限、设备配置与 trace 事件。

“io_uring 让 FUSE 快 40%”或“dm-verity（块设备完整性校验机制）并行哈希让冷读快 35%”都缺少可迁移到所有 Android 17 设备的前提，不能作为平台结论。

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

排查 Android I/O 卡顿时，可以按顺序回答四个问题：

1. 线程是否处于明确的 I/O sleep（睡眠等待），还是另一种不可中断等待？
2. 延迟在 Page Cache/回写、文件系统、块层 scheduler，还是设备完成阶段？
3. 实机使用哪一个 scheduler，线程在哪个 task profile 与 blkio/io cgroup？
4. App 能否通过减少事务、主线程磁盘访问和无效小写降低同步压力？

Android 17 的 GKI 提供 mq-deadline、Kyber 和多种 blk-cgroup QoS 能力，BFQ 仍是可选项；AOSP task profile 基线继续使用 blkio v1 区分 background 与根组。vendor 可以覆盖这些配置，因此任何“Android 17 默认 scheduler”结论都要回到实机验证。

应用配置持久化的同步边界见 6.4，MediaProvider/FUSE 共享存储路径见 6.5。
