---
title: "Android 17 eBPF 性能可观测性程序矩阵扩展"
chapter: "14.25"
section: "14.25"
status: ready-for-review
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1 + android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "system/bpfprogs/cyclePerUid.c"
  - type: aosp
    path: "system/bpfprogs/dmabufIter.c"
  - type: aosp
    path: "system/bpfprogs/kernelwakelockduration/kernelWakelockDuration.c"
  - type: aosp
    path: "system/bpfprogs/locks/bpfLockContention.c"
  - type: aosp
    path: "system/bpfprogs/Android.bp"
  - type: aosp
    path: "system/bpfprogs/progs.aconfig"
  - type: aosp
    path: "system/bpf/loader/bpfloader.rs"
  - type: aosp
    path: "frameworks/native/libs/cpucycleperuid/lib.rs"
  - type: kernel
    path: "kernel/bpf/dmabuf_iter.c"
  - type: kernel
    path: "drivers/base/power/wakeup.c"
  - type: kernel
    path: "include/trace/events/lock.h"
  - type: blog
    path: "intake/daily-info/2026-07-01.md #27-30, #34"
  - type: official
    path: "source.android.com/docs/core/architecture/kernel/bpf"
tags: [eBPF, observability, CPU-cycle, DMA-BUF, wakelock, lock-contention, Rust, Android17]
related_chapters: ["14.23", "14.24", "5.1", "5.4"]
---

# 14.25 Android 17 eBPF 性能可观测性程序矩阵扩展

§14.23 介绍 eBPF 性能工具，§14.24 讲解 Android 17 `bpfloader`。这里沿着“构建产物 → 启动加载 → attach → 输出 → 用户态消费”检查 Android 17 新增的四组程序：

- `cyclePerUid.bpf`：x86_64 平台的 per-UID CPU cycle 统计。
- `dmabufIter.bpf`：DMA-BUF 全局快照迭代器。
- `kernelWakelockDuration.bpf`：至少一个 kernel wakelock 处于 active 状态的累计时长。
- `bpfLockContention.bpf`：指定内核锁的竞争时延聚合。

它们都由 `libbpf_prog` 构建为 `.bpf` 对象，依赖内核 BTF 与对应 hook。文件被编进 system image，不等于启动时已经加载；`bpfloader` 还会检查架构、内核版本和 aconfig flag。

## 14.25.1 程序 matrix

| 程序 | 构建与加载条件 | attach 点 | 输出 | 明确不提供 |
|---|---|---|---|---|
| `cyclePerUid` | 仅 x86_64；还需 `x86_cpu_energy_attribution` flag | `tp_btf/sched_switch`，由用户态库按需 attach | per-UID、per-CPU 累计 cycles；desync 次数 | per-process、调用栈、ARM 统计 |
| `dmabufIter` | riscv64 之外构建；需 `load_dmabuf_iterator` flag | `iter/dmabuf`，启动时自动 attach | inode、size、name、exporter 的全局快照 | attachment 数、引用进程、UID、持续事件 |
| `kernelWakelockDuration` | 需 `kernel_wakelock_duration` flag | `raw_tp/wakeup_source_activate` / `deactivate`，自动 attach | 系统存在 active kernel wakelock 的时间并集 | wakelock 名称、per-source、per-UID |
| `bpfLockContention` | riscv64 之外构建；内核至少 6.1；需 `load_bpf_lock_contention` flag | `tp/lock/contention_begin` / `end`，自动 attach | TGID × 白名单锁的 sum/count/min/max | 任意锁、持有时长、owner、调用栈、用户态锁 |

三个 `android.bpfprogs.flags` 声明分别控制 wakelock、DMA-BUF 和 lock contention 程序。`cyclePerUid` 的构建限制写在 `Android.bp`，加载还由 `backstage_power_flags::x86_cpu_energy_attribution()` 控制。`progs.aconfig` 本身不能说明某款产品的运行值。

## 14.25.2 Android 17 的加载和固定路径

Rust `bpfloader` 先执行 `load_libbpf_progs()`，再进入 legacy loader。对这四组程序，libbpf 路径负责：

1. 根据 flag 和架构组装待加载文件列表。
2. 打开 `.bpf` 对象并按内核版本关闭不适用的 map 或 program。
3. 把 map 固定到 `/sys/fs/bpf/<prefix>/map_<object>_<map>`。
4. 对 `auto_attach` program 建立 BPF link，并把 link 固定到 `/sys/fs/bpf/<prefix>/prog_<object>_<program>`。
5. 对不自动 attach 的 program，只固定 program，交给用户态消费者决定 attach 生命周期。

在 root 的 userdebug/eng 设备上，下面的命令用于检查加载结果。它读取 bpffs，不会改写 map：

```bash
adb shell su root sh -c '
  for name in cpucycleperuid dmabuf kernelwakelockduration lock_contention; do
    dir=/sys/fs/bpf/$name
    if [ -d "$dir" ]; then
      echo "[$name]"
      ls -l "$dir"
    else
      echo "[$name] not loaded"
    fi
  done
'
```

目录缺失可能来自架构不符、flag 关闭、对象未安装、BTF/hook 不兼容或加载失败。排查时还要查看 `bpfloader` 日志，不能只根据 `/system/etc/bpf/` 中有无对象文件下结论。

## 14.25.3 `cyclePerUid`：x86 CPU cycle 与 RAPL 归因

### BPF 侧如何归因

`cyclePerUid.c` 定义五张 map：

| map | 类型 | 作用 |
|---|---|---|
| `last_recorded_cycle_map` | `PERCPU_ARRAY` | 保存每个 CPU 上一次读取的 cycle 值 |
| `last_running_pid_map` | `PERCPU_ARRAY` | 保存每个 CPU 上一次切入的 PID |
| `uid_cpu_cycle_map` | `LRU_PERCPU_HASH` | 按 UID 保存各 CPU 的累计 cycle，最多 1024 个 UID |
| `tsc_events` | `PERF_EVENT_ARRAY` | 保存每个 CPU 的 perf event fd |
| `desync_counter` | `PERCPU_ARRAY` | 记录上下文切换序列不连续的次数 |

程序挂在 `tp_btf/sched_switch`。每次上下文切换时，它读取当前 CPU 的 cycle 计数，用本次值减去上次值，再把差值记到被切出任务的 UID。`last_running_pid_map` 用来识别 suspend/resume 周围可能重复出现的 idle 切换；PID 序列对不上时，本次归因被跳过，并增加 `desync_counter`。

归因键来自 `bpf_get_current_uid_gid()` 的低 32 位，map 中没有 PID 或线程维度。多进程应用会自然合并到同一 UID，想继续定位到进程和函数还要配合 Simpleperf。

### 只面向 x86_64

`system/bpfprogs/Android.bp` 默认关闭 `cyclePerUid.bpf`，只在 x86_64 架构启用。`frameworks/native/libs/cpucycleperuid` 的 Rust bindgen、FFI shared library 和测试也采用同样的架构限制。

Rust 库打开每个 CPU 的 `PERF_COUNT_HW_CPU_CYCLES` perf event，把 fd 填入 `tsc_events`，再把固定的 `tp_btf` program attach 到 `sched_switch`。它还依赖两个 Intel RAPL 节点：

- `/sys/class/powercap/intel-rapl:0/energy_uj`
- `/sys/class/powercap/intel-rapl:0/max_energy_range_uj`

所以，这条链路不能作为 ARM 手机上的通用 per-UID cycle 方案。CPU cycle 的含义还受频率、IPC、微架构和 perf PMU 实现影响，不适合直接拿不同 SoC 的绝对值做横向排名。

### 能量分摊是估算模型

`libcycleperuid` 的 `read_uid_power_delta()` 在相邻两次读取之间计算：

1. RAPL package energy 增量。
2. 每个 UID 的 CPU cycle 增量。
3. 所有 UID 的 cycle 增量总和。
4. 按 `uid_cycles / total_cycles` 的比例分配 package energy 增量。

这个结果是“按 cycle 占比分摊的 package energy”，不代表硬件直接测得某个 UID 的能量。内存、GPU、I/O、idle、不同核心能效和频率差异都没有在公式中单独建模。报告中应保留“估算”属性，并同时监控 `desync_counter`。

Rust FFI 导出 start/stop、RAPL 可用性、program 是否存在、累计 cycles、desync count 和 per-UID energy delta 等 C ABI。应用层不应直接依赖 bpffs 的二进制布局，平台消费者应复用该库或提供受版本控制的适配层。

## 14.25.4 `dmabufIter`：四字段全局快照

`dmabufIter.c` 挂载到 `iter/dmabuf`。内核迭代器逐个提供 `struct dma_buf`，程序通过 CO-RE 读取四项数据：

1. `file->f_inode->i_ino`
2. `dma_buf::size`
3. `dma_buf::name`
4. `dma_buf::exp_name`

每个字段单独占一行，每个 buffer 固定四行。`name` 可以为空，也可能来自用户态；程序会把其中的换行替换为空格，避免破坏记录边界。

已加载的 iterator link 固定在下面的路径：

```text
/sys/fs/bpf/dmabuf/prog_dmabufIter_iter_dmabuf
```

在支持读取 pinned iterator link 的 root 调试环境中，可以用下面的命令抓取快照，并在主机端把每四行合成一行：

```bash
adb shell su root cat \
  /sys/fs/bpf/dmabuf/prog_dmabufIter_iter_dmabuf \
  > dmabuf.snapshot

paste - - - - < dmabuf.snapshot
```

合并后的列顺序是 inode、bytes、name、exporter。诊断时至少采集两个时间点，按 inode 对比新增、消失和大小变化；单次快照只能描述当时仍存活的 buffer。

### 能做与不能做

该 iterator 适合：

- 按 exporter 汇总 DMA-BUF 数量和字节数。
- 找出持续存在的大 buffer。
- 比较场景前后的全局 DMA-BUF 集合。
- 用 inode 作为同一快照内和相邻快照间的关联线索。

它没有读取 attachment list、文件引用计数、进程、UID 或分配调用栈。仅凭四字段输出无法判断由哪个进程泄漏，也不能把 `exp_name` 当作当前引用者。需要进程归因时，应把快照与进程 fd、`/proc/<pid>/fdinfo`、DMA-BUF sysfs 统计和图形/相机服务状态联合分析。

## 14.25.5 `kernelWakelockDuration`：全局 active 时间并集

程序自动挂到两个 raw tracepoint：

- `raw_tp/wakeup_source_activate`
- `raw_tp/wakeup_source_deactivate`

内核 tracepoint 参数是 `(name, state)`，这里的 BPF 程序只读取第二个参数 `state`，不读取 `name`。`state` 对应内核 `combined_event_count`：

- 低 16 位：当前 active wakeup source 数量。
- 高 16 位：已经完成的 wakeup event 计数。

程序只有一张 `ARRAY` map，键固定为 0，值包含：

- `program_init`：处理动态加载期间事件竞态的初始化状态。
- `timer_state_ns`：系统至少有一个 kernel wakelock active 的累计时间状态。

active 数量从 0 变为 1 时，程序从 `timer_state_ns` 中减去 `bpf_ktime_get_boot_ns()`；从 1 变为 0 时再加回当前时间。读取 map 时如果值为负，说明仍有 active wakelock，需要加上当前 boottime 才能得到截至读取时刻的累计值。

初始化代码使用高低位计数判断事件新旧，并在观察到足够的完成事件后进入稳定状态。这样可以避免 BPF program attach 过程中乱序到达的旧事件污染累计值。

该程序输出的是全局时间并集。多个 wakelock 同时 active 时只计一段时间；它不提供锁名、每个 source 的持有时长、UID 或调用者。按名称查异常 wakelock 仍要读取 wakeup source 统计，或用 Perfetto/ftrace 记录带 `name` 的 activate/deactivate 事件。

在装有 `bpftool` 的 root 调试设备上，下面的命令用于确认 map 和两个持久 link 是否存在：

```bash
adb shell su root sh -c '
  ls -l /sys/fs/bpf/kernelwakelockduration
  bpftool map dump pinned \
    /sys/fs/bpf/kernelwakelockduration/map_kernelWakelockDuration_program_state
'
```

`bpftool` 会展示原始 key/value。要把 value 解析成两个 64 位字段，用户态结构必须与 `bpf_kernelwakelockduration.h` 保持一致。

## 14.25.6 `bpfLockContention`：白名单内核锁的等待聚合

Android 17 的程序挂到 `lock/contention_begin` 与 `lock/contention_end`。这两个 tracepoint 位于常规 mutex、rwsem、queued spinlock、RT mutex 等慢路径；它们和依赖 `CONFIG_LOCKDEP` 的 `lock_acquire` / `lock_release` 不是同一组事件。目标设备仍应从 tracefs 核对事件：

```bash
adb shell su root sh -c '
  test -e /sys/kernel/tracing/events/lock/contention_begin/id &&
  test -e /sys/kernel/tracing/events/lock/contention_end/id &&
  echo "lock contention tracepoints available"
'
```

没有输出时，BPF 对象即使安装在 system image，也无法完成对应 attach。`bpfloader` 对这组 program 和 map 还设置了 Linux 6.1 的最低版本。

### 只追踪源码列出的锁

程序收到锁地址后，`get_lock_id()` 只匹配 `bpf_lock_list.h` 中的全局锁和当前任务结构内的动态锁。Android 17 列表包括：

- 全局锁：`tasklist_lock`、`cgroup_mutex`、`rtnl_mutex`、`rcu_state`、`pcpu_drain_mutex`、`vmap_purge_lock`、`freezer_mutex`、`buslock_sem`、`console_sem`、`dm_bufio_clients_lock`、`list_lrus_mutex`。
- 动态锁：当前任务相关的 `mmap_lock`、`page_table_lock`、`pi_lock`、`alloc_lock`、`futex_exit_mutex`、`perf_event_mutex`。

全局符号以 weak ksym 声明，某个内核没有对应符号时可以跳过。地址没有命中列表时直接返回，不进入 map。由此得到的是“指定锁集合的竞争统计”，覆盖不到任意驱动锁，也覆盖不到 Java、ART、Binder 用户态代码中的 mutex。

### 两张 map 的数据语义

`contention_start_map` 用 `{tgid, tid, lock_name}` 保存开始时间，容量 4096，用于配对同一线程的 begin/end。`contention_latency_map` 用 `{tgid, lock_name}` 聚合：

- `sum`：等待时长总和，单位 ns。
- `count`：竞争次数。
- `max` / `min`：观察到的最大、最小时长。
- `comm`：该聚合项创建时读取的任务名。

`sum` 与 `count` 使用原子累加，源码明确把 `min` / `max` 的更新设计为允许竞争的简化实现。因此，平均值 `sum / count` 可用于排序，`min` 和 `max` 在高并发下只能看作近似值。map 也没有 owner、持有时间、调用栈或等待者列表，不能单靠它重建锁依赖图。

下面的命令用于读取聚合 map。读取完成后是否清空，要由采集窗口协议决定，不应在没有基线的情况下直接删除数据：

```bash
adb shell su root bpftool map dump pinned \
  /sys/fs/bpf/lock_contention/map_bpfLockContention_contention_latency_map
```

做版本回归时，应固定采集窗口和工作负载，按 TGID、锁名比较 count、sum 与平均等待时长，并同时记录 map 容量压力和 program 加载日志。

## 14.25.7 与既有 Android BPF 观测的关系

| 问题 | 程序 | 仍需补充的观测 |
|---|---|---|
| 哪个 UID 消耗 x86 CPU cycles | `cyclePerUid` | Simpleperf 细化到进程、线程、函数；调度 trace 解释等待 |
| 哪些 DMA-BUF 仍然存活 | `dmabufIter` | fdinfo/sysfs/服务状态用于进程和子系统归因 |
| 系统被 kernel wakelock 阻止休眠多久 | `kernelWakelockDuration` | wakeup source 或 ftrace 用于锁名归因 |
| 指定内核锁等待多久 | `bpfLockContention` | perf、调度 trace、源码路径用于解释调用者和影响 |

四组程序都没有在自身源码中写入 Perfetto packet，也没有定义 Perfetto data source。平台上的其他消费者可以读取 map 或 iterator 后转写到 trace，但不能因为 BPF 程序已加载就认定 Perfetto UI 会出现对应 track。

## 14.25.8 调试顺序

1. 从 `/system/etc/bpf/` 确认对象是否安装。
2. 从 bpffs 确认对象是否由 `bpfloader` 加载并固定。
3. 核对产品 flag、CPU 架构和内核版本。
4. 从 tracefs、BTF 和内核配置确认 attach 点存在。
5. 读取 map 或 iterator，并按源码结构解析。
6. 记录丢失、desync、map 容量和采集窗口。
7. 用 Simpleperf、Perfetto、sysfs、fdinfo 或服务状态补充程序没有提供的维度。

这一顺序能区分“对象没有编译”“启动时未选择”“内核拒绝加载”“program 已运行但用户态解析错误”四类故障，避免把空数据直接归因到业务负载。

## 源码索引

- [system/bpfprogs/Android.bp：四组 `.bpf` 对象的构建和架构限制](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/Android.bp)
- [cyclePerUid.c：sched_switch cycle 归因与五张 map](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/cyclePerUid.c)
- [dmabufIter.c：DMA-BUF iterator 的四字段输出](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/dmabufIter.c)
- [kernelWakelockDuration.c：全局 active 时间并集与初始化算法](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/kernelwakelockduration/kernelWakelockDuration.c)
- [bpfLockContention.c：begin/end 配对与聚合](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/locks/bpfLockContention.c)
- [bpf_lock_list.h：Android 17 的锁白名单](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/locks/include/locks/bpf_lock_list.h)
- [progs.aconfig：三组启动加载 flag](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/progs.aconfig)
- [bpfloader.rs：选择、加载、auto-attach 与 bpffs 固定规则](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/bpfloader.rs)
- [frameworks/native cpucycleperuid/lib.rs：x86 cycle、RAPL 与 C FFI](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/cpucycleperuid/lib.rs)
- [frameworks/native cpucycleperuid/Android.bp：x86_64 构建限制](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/cpucycleperuid/Android.bp)
- [Android 17 kernel dmabuf_iter.c：`iter/dmabuf` 内核实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/bpf/dmabuf_iter.c)
- [Android 17 kernel wakeup.c：`combined_event_count` 语义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c)
- [Android 17 kernel lock.h：contention begin/end tracepoint](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/lock.h)
