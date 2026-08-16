---
title: "Android 17 新增 eBPF 性能观测程序矩阵"
chapter: "14.25"
section: "14.25"
status: finalized
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 (system/bpfprogs, system/bpf, frameworks/native) + Android common kernel android17-6.18-2026-06_r6"
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
    path: "system/bpfprogs/locks/include/locks/bpf_lock_list.h"
  - type: aosp
    path: "system/bpfprogs/Android.bp"
  - type: aosp
    path: "system/bpfprogs/kernelwakelockduration/Android.bp"
  - type: aosp
    path: "system/bpfprogs/kernelwakelockduration/kernelWakelockDuration_test.cpp"
  - type: aosp
    path: "system/bpfprogs/progs.aconfig"
  - type: aosp
    path: "system/bpf/loader/bpfloader.rs"
  - type: aosp
    path: "system/bpf/progs/include/bpf_kernelwakelockduration.h"
  - type: aosp
    path: "frameworks/native/libs/cpucycleperuid/lib.rs"
  - type: aosp
    path: "frameworks/native/libs/cpucycleperuid/Android.bp"
  - type: kernel
    path: "kernel/bpf/dmabuf_iter.c"
  - type: kernel
    path: "drivers/base/power/wakeup.c"
  - type: kernel
    path: "include/trace/events/lock.h"
  - type: blog
    path: "intake/daily-info/2026-07-01.md #27-30, #34"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/bpf"
tags: [eBPF, observability, CPU-cycle, DMA-BUF, wakelock, lock-contention, Rust, Android17]
related_chapters: ["14.23", "14.24", "5.1", "5.4"]
---

# 14.25 Android 17 新增 eBPF 性能观测程序矩阵

[§14.23](23-ebpf-performance-analysis.md) 介绍 eBPF 性能工具，[§14.24](24-ebpf-bpfloader-architecture.md) 讲解 Android 17 `bpfloader`。相较 `android-16.0.0_r4`，Android 17 的首个发布 tag `android-17.0.0_r1` 新增了下面四组程序。这里沿着“构建产物 → 启动加载 → attach（连接到内核触发点）→ 输出 → 用户态消费”逐项核对：

- `cyclePerUid.bpf`：x86_64 平台的 per-UID（按 Linux UID 汇总）CPU cycle（处理器周期）统计。
- `dmabufIter.bpf`：DMA-BUF（设备间共享缓冲区）全局快照迭代器。
- `kernelWakelockDuration.bpf`：至少一个 kernel wakelock（内核唤醒锁）处于 active 状态时的累计时长。
- `bpfLockContention.bpf`：指定内核锁的 contention（竞争等待）时延聚合。

四个对象都由 Soong（Android 构建系统）的 `libbpf_prog` 模块构建为 `.bpf` 文件，但源码层面的内核依赖并不相同：`cyclePerUid`、`dmabufIter` 和 `bpfLockContention` 使用 BTF（BPF Type Format，内核类型信息）；`kernelWakelockDuration` 直接读取 raw tracepoint（原始跟踪点）参数，不依赖 `vmlinux` 类型。对象被编进 system image（系统镜像），不等于启动时已经加载；`bpfloader` 还会检查 CPU 架构、内核版本、配置 flag（开关）以及对应 hook（触发点）能否附加。

## 14.25.1 程序矩阵（matrix）

| 程序 | 构建与加载条件 | attach（附加）点 | 输出 | 明确不提供 |
|---|---|---|---|---|
| `cyclePerUid` | 仅 x86_64；还需 `x86_cpu_energy_attribution` flag | `tp_btf/sched_switch`，由用户态库按需 attach | 每个 UID、每个 CPU 的累计 cycles；desync（归因序列不同步）次数 | 进程维度、调用栈、ARM 统计 |
| `dmabufIter` | riscv64 之外构建；需 `load_dmabuf_iterator` flag | `iter/dmabuf`，启动时自动 attach | inode、size、name、exporter 四个字段的全局快照 | attachment（设备映射关系）数量、引用进程、UID、持续事件 |
| `kernelWakelockDuration` | 需 `kernel_wakelock_duration` flag | `raw_tp/wakeup_source_activate` / `deactivate`，自动 attach | 系统至少有一个 active kernel wakelock 时的时间并集 | wakelock 名称、单个 wakeup source、UID |
| `bpfLockContention` | riscv64 之外构建；内核至少 6.1；需 `load_bpf_lock_contention` flag | `tp/lock/contention_begin` / `end`，自动 attach | TGID（线程组 ID，通常对应进程）× 白名单锁的 sum/count/min/max | 任意锁、持有时长、owner（持有者）、调用栈、用户态锁 |

`aconfig` 是 Android 的功能开关配置机制。`android.bpfprogs.flags` 中的三个声明分别控制 wakelock、DMA-BUF 和 lock contention 程序。`cyclePerUid` 的构建限制写在 `Android.bp`，加载还由 `backstage_power_flags::x86_cpu_energy_attribution()` 控制。`progs.aconfig` 只声明开关，不能据此判断某款产品最终采用什么值。

## 14.25.2 Android 17 的加载和固定路径

Android 17 的 Rust `bpfloader` 先执行 `load_libbpf_progs()`，再进入 legacy loader（旧的 C++ vendor 加载器）。bpffs 是挂载在 `/sys/fs/bpf` 的 BPF 虚拟文件系统；pin 会用文件系统路径保留内核对象引用。program 是送入内核执行的 BPF 代码，map 是 program 与用户态共享的内核键值存储。对这四组程序，libbpf（Linux BPF 用户态加载库）路径负责：

1. 根据 flag 和架构组装待加载文件列表。
2. 打开 `.bpf` 对象，并按内核版本关闭不适用的 map 或 program。
3. 把 map 固定到 `/sys/fs/bpf/<prefix>/map_<object>_<map>`。
4. 对 `auto_attach` program 建立 BPF link，并把 link 固定到 `/sys/fs/bpf/<prefix>/prog_<object>_<program>`。BPF link 是记录“程序已附加到哪个触发点”的内核对象。
5. 对不自动 attach 的 program，只固定 program，交给用户态消费者决定 attach 生命周期。

`userdebug` 和 `eng` 是面向调试或工程开发的系统构建类型，root 表示取得超级用户权限。在这类设备上，下面的命令用于检查加载结果；它只读取 bpffs，不会改写 map：

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

命令会逐个列出四个 bpffs 目录；不存在时打印 `not loaded`。目录缺失可能来自架构不符、flag 关闭、对象未安装、BTF 或 hook 不兼容，也可能是加载失败。排查时还要查看 `bpfloader` 日志，不能只根据 `/system/etc/bpf/` 中有无对象文件下结论。

## 14.25.3 `cyclePerUid`：x86 CPU cycle 与 RAPL 归因

### BPF 侧如何归因

`cyclePerUid.c` 定义五张 map。这里的 `PERCPU` 表示每个 CPU 各有一份值，`LRU` 表示容量满时按近期使用情况淘汰旧键，`PERF_EVENT_ARRAY` 则保存 perf event（性能计数事件）的文件描述符：

| map | 类型 | 作用 |
|---|---|---|
| `last_recorded_cycle_map` | `PERCPU_ARRAY` | 保存每个 CPU 上一次读取的 cycle 值 |
| `last_running_pid_map` | `PERCPU_ARRAY` | 保存每个 CPU 上一次切入的 PID |
| `uid_cpu_cycle_map` | `LRU_PERCPU_HASH` | 按 UID 保存各 CPU 的累计 cycle，最多 1024 个 UID |
| `tsc_events` | `PERF_EVENT_ARRAY` | 保存每个 CPU 的 perf event fd（file descriptor，文件描述符） |
| `desync_counter` | `PERCPU_ARRAY` | 记录上下文切换序列不连续的次数 |

程序附加到 `tp_btf/sched_switch`；`sched_switch` 是调度器切换当前运行任务时触发的 tracepoint。每次上下文切换时，程序读取当前 CPU 的 cycle 计数，用本次值减去上次值，再把差值记到被切出任务的 UID。`last_running_pid_map` 用来识别 suspend/resume（系统挂起/恢复）附近可能重复出现的 idle（空闲任务）切换；PID 序列对不上时，本次归因会被跳过，并增加 `desync_counter`。

归因键来自 `bpf_get_current_uid_gid()` 返回值的低 32 位，即 UID；map 中没有 PID 或线程维度。同一 UID 下的多个进程会合并统计，继续定位到进程、线程和函数时还要配合 `simpleperf` 等采样工具。

### 只面向 x86_64

`system/bpfprogs/Android.bp` 默认关闭 `cyclePerUid.bpf`，只在 x86_64 架构启用。`frameworks/native/libs/cpucycleperuid` 中的 Rust bindgen（从 C 声明生成 Rust 绑定）、FFI shared library（供其他语言调用的共享库）和测试也采用同样的架构限制。FFI 是 Foreign Function Interface，指跨语言调用边界。

Rust 库为每个 CPU 打开 `PERF_COUNT_HW_CPU_CYCLES` perf event，把 fd 填入 `tsc_events`，再把已固定到 bpffs 的 `tp_btf` program 附加到 `sched_switch`。虽然 map 名叫 `tsc_events`，这里存放的计数源是上述 perf hardware event，不能仅凭名字把结果解释成直接读取 TSC（Time Stamp Counter，时间戳计数器）。该库还依赖两个 Intel RAPL（Running Average Power Limit，处理器封装能量计数接口）节点：

- `/sys/class/powercap/intel-rapl:0/energy_uj`
- `/sys/class/powercap/intel-rapl:0/max_energy_range_uj`

因此，这条链路不能作为 ARM 手机上的通用 per-UID cycle 方案。CPU cycle 的含义还会受到频率、IPC（instructions per cycle，每周期指令数）、微架构和 PMU（Performance Monitoring Unit，性能监控单元）实现影响，不适合直接拿不同 SoC（System on Chip，片上系统）的绝对值排名。

### 能量分摊是估算模型

`libcycleperuid` 的 `read_uid_power_delta()` 在相邻两次读取之间计算：

1. RAPL package energy（处理器封装能量）增量。
2. 每个 UID 的 CPU cycle 增量。
3. 所有 UID 的 cycle 增量总和。
4. 按 `uid_cycles / total_cycles` 的比例分配 package energy 增量。

这个结果是“按 cycle 占比分摊的 package energy”，不代表硬件直接测得某个 UID 的能量。内存、GPU、I/O、idle、不同核心的能效和频率差异都没有在公式中单独建模。报告中应明确标为“估算”，并同时监控 `desync_counter`。

Rust FFI 通过 C ABI（Application Binary Interface，二进制接口）导出 start/stop、RAPL 可用性、program 是否存在、累计 cycles、desync count 和 per-UID energy delta 等能力。应用层不应直接依赖 bpffs map 的二进制布局；平台消费者应复用该库，或提供带版本约束的适配层。

## 14.25.4 `dmabufIter`：四字段全局快照

`dmabufIter.c` 附加到 `iter/dmabuf`。BPF iterator（迭代器）会在一次读取过程中遍历某类内核对象；这里逐个提供表示 DMA-BUF 的 `struct dma_buf`。程序通过 CO-RE（Compile Once – Run Everywhere）读取四项数据，CO-RE 会借助 BTF 调整不同内核版本中的结构体成员偏移：

1. `file->f_inode->i_ino`
2. `dma_buf::size`
3. `dma_buf::name`
4. `dma_buf::exp_name`

`inode` 是 DMA-BUF 所对应文件对象的 inode 编号，`size` 是字节数，`name` 是可选名称，`exp_name` 则标识导出这个缓冲区的驱动或子系统。每个字段单独占一行，每个 DMA-BUF 固定四行。`name` 可以为空，也可能来自用户态；程序会把其中的换行替换为空格，避免破坏记录边界。

已加载的 iterator link 会 pin（固定）在下面的 bpffs 路径。打开这个 link 会触发一次遍历并返回文本记录：

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

第一条命令中的重定向由主机 shell 执行，因此 `dmabuf.snapshot` 保存在主机上；`paste - - - -` 再把连续四行拼成一行。合并后的列顺序是 inode、bytes、name、exporter。诊断时至少采集两个时间点，按 inode 对比新增、消失和大小变化；单次快照只能描述读取当时仍存活的 DMA-BUF。

### 能做与不能做

该 iterator 适合：

- 按 exporter 汇总 DMA-BUF 数量和字节数。
- 找出持续存在的大 buffer。
- 比较场景前后的全局 DMA-BUF 集合。
- 用 inode 作为同一快照内和相邻快照间的关联线索；对象销毁后 inode 可能被复用，不能把它当作长期全局 ID。

它没有读取 attachment list、文件引用计数、进程、UID 或分配调用栈。仅凭四字段输出无法判断由哪个进程泄漏，也不能把 `exp_name` 当作当前引用者；它表示 exporter（导出方）。需要进程归因时，应把快照与进程 fd、`/proc/<pid>/fdinfo`、DMA-BUF sysfs 统计和图形或相机服务状态联合分析。`fdinfo` 是内核为某个文件描述符暴露的附加信息，sysfs 则是 `/sys` 下的内核对象属性接口。

## 14.25.5 `kernelWakelockDuration`：全局 active 时间并集

Linux 电源管理用 wakeup source（唤醒源）阻止或记录系统挂起期间的唤醒活动；Android 代码常把处于 active 状态的 wakeup source 称为 kernel wakelock。程序自动附加到两个 raw tracepoint：

- `raw_tp/wakeup_source_activate`
- `raw_tp/wakeup_source_deactivate`

内核 tracepoint 参数是 `(name, state)`。这里的 BPF 程序只从原始参数数组读取第二项 `state`，不读取 `name`，也不通过 BTF 访问内核结构体。`state` 对应内核的 `combined_event_count`（把进行中数量和已完成计数压进一个整数）：

- 低 16 位：当前 active wakeup source 的数量。
- 高 16 位：已经完成的 wakeup event 计数；该字段会回绕。

位数来自共享宏 `IN_PROGRESS_BITS = sizeof(int) * 4`；在这里的 32 位 `int` 布局中，一半是 16 位。

程序只有一张 `ARRAY` map，键固定为 0，值包含：

- `program_init`：处理动态加载期间事件竞态的初始化状态，类型是 `uint64_t`。
- `timer_state_ns`：系统至少有一个 kernel wakelock active 时的累计时间状态，类型是有符号的 `int64_t`。

active 数量从 0 变为 1 时，程序从 `timer_state_ns` 中减去 `bpf_ktime_get_boot_ns()`；从 1 变为 0 时再加回当前时间。这个 BPF helper（内核提供给 BPF program 的辅助函数）返回以纳秒计的 boot time，即包含系统 suspend 时间的启动后时钟。读取 map 时如果值为负，说明当前仍有 active wakelock；用户态应使用同一时钟域计算 `timer_state_ns + 当前 CLOCK_BOOTTIME 纳秒值`，得到截至读取时刻的累计值。

累计值只覆盖 `program_state` map 创建并开始处理事件后的时段；设备重启或 map 重建会归零。计算某个采集窗口的增量时，应先把窗口两端的负值状态分别换算成累计时长，再用结束值减去开始值。

动态 attach 时，不同 CPU 上先前触发的事件可能晚于首个初始化事件到达。程序先保存首个事件的 `combined_event_count`，再用高低位和 16 位回绕距离判断后续事件是否更旧；已完成计数向前推进超过 64 后，`program_init` 才会写入 `UINT64_MAX`，表示初始化完成。初始化阶段判定为旧的事件会被跳过，避免它们污染累计值。

该程序输出的是全局时间并集：多个 wakelock 同时 active 时，重叠区间只计算一次。它不提供 wakeup source 名称、单个 source 的 active 时长、UID 或调用者。按名称查异常 wakeup source 仍要读取对应统计，或用 Perfetto、ftrace（内核函数与事件跟踪器）记录带 `name` 的 activate/deactivate 事件。

`bpftool` 是 Linux 内核配套的 BPF 对象查看与管理工具。在装有它的 root 调试设备上，下面的命令用于确认 map 和两个持久 link 是否存在：

```bash
adb shell su root sh -c '
  ls -l /sys/fs/bpf/kernelwakelockduration
  bpftool map dump pinned \
    /sys/fs/bpf/kernelwakelockduration/map_kernelWakelockDuration_program_state
'
```

`ls` 用于确认一张 map 和两个持久 link，`bpftool` 则展示原始 key/value。共享 ABI 头 `system/bpf/progs/include/bpf_kernelwakelockduration.h` 定义了上述 `uint64_t` 与 `int64_t` 字段及固定路径；用户态解析时必须采用相同字段顺序、大小和符号类型。这个头提供的是二进制布局约定，不会替用户态完成负值到累计时长的换算。

## 14.25.6 `bpfLockContention`：白名单内核锁的等待聚合

Android 17 的程序附加到 `lock/contention_begin` 与 `lock/contention_end`。这两个 tracepoint 位于多类锁进入等待的慢路径，包括 mutex（可睡眠互斥锁）、rwsem（读写信号量）、queued spinlock（排队自旋锁）和 RT mutex（支持优先级继承的实时互斥锁）。它们与 `lock_acquire` / `lock_release` 属于不同事件；后两者依赖 `CONFIG_LOCKDEP`，即内核锁依赖检查器的编译开关。目标设备仍应从 tracefs（内核跟踪事件文件系统）核对事件是否存在：

```bash
adb shell su root sh -c '
  test -e /sys/kernel/tracing/events/lock/contention_begin/id &&
  test -e /sys/kernel/tracing/events/lock/contention_end/id &&
  echo "lock contention tracepoints available"
'
```

命令只在两个事件目录都存在时打印成功提示。没有输出时，BPF 对象即使安装在 system image，也无法完成对应 attach。`bpfloader` 对这组 program 和 map 还设置了 Linux 6.1 的最低版本。

### 只追踪源码列出的锁

program 收到发生竞争的锁地址后，`get_lock_id()` 只匹配 `bpf_lock_list.h` 中的全局锁，以及嵌在当前任务相关结构体里的动态锁。Android 17 列表包括：

- 全局锁：`tasklist_lock`、`cgroup_mutex`、`rtnl_mutex`、`rcu_state`、`pcpu_drain_mutex`、`vmap_purge_lock`、`freezer_mutex`、`buslock_sem`、`console_sem`、`dm_bufio_clients_lock`、`list_lrus_mutex`。
- 动态锁：当前任务相关的 `mmap_lock`、`page_table_lock`、`pi_lock`、`alloc_lock`、`futex_exit_mutex`、`perf_event_mutex`。

全局符号以 weak ksym（弱内核符号引用）声明；某个内核未提供对应符号时，该引用可以为空并被跳过。锁地址没有命中列表时，program 直接返回，不写入 map。因此，这里得到的是“指定锁集合的竞争统计”，覆盖不到任意驱动锁，也覆盖不到 Java、ART 或 Binder 用户态代码中的 mutex。

### 两张 map 的数据语义

`contention_start_map` 用 `{tgid, tid, lock_name}` 保存等待开始时间，容量为 4096 条，用于配对同一线程的 begin/end。TGID 是线程组 ID，通常作为进程 ID 使用；TID 是具体线程 ID。`contention_latency_map` 再用 `{tgid, lock_name}` 聚合：

- `sum`：等待时长总和，单位 ns。
- `count`：竞争次数。
- `max` / `min`：观察到的最大、最小时长。
- `comm`：该聚合项首次创建时读取的任务名，长度和含义受内核 task comm 字段限制。

`sum` 与 `count` 使用原子累加，多个 CPU 并发更新时不会互相覆盖。源码对 `min` / `max` 采用允许竞态的简化更新，因此平均值 `sum / count` 可用于排序，`min` 和 `max` 在高并发下只能看作近似值。map 也没有 owner、持有时间、调用栈或等待者列表，不能单靠它重建“哪把锁等待哪把锁”的依赖关系。

下面的命令用于读取聚合 map。读取后是否清空，应由采集规则预先确定，包括开始时间、结束时间以及是否在每个窗口前后删除条目；没有基线时不应直接清空累计数据：

```bash
adb shell su root bpftool map dump pinned \
  /sys/fs/bpf/lock_contention/map_bpfLockContention_contention_latency_map
```

`bpftool` 输出的是聚合 map 当前保存的键和值。做版本回归时，应固定采集时长和工作负载，按 TGID、锁名比较 count、sum 与平均等待时长，并同时记录 map 条目数是否接近 4096 上限以及 program 加载日志。

## 14.25.7 与既有 Android BPF 观测的关系

| 问题 | 程序 | 仍需补充的观测 |
|---|---|---|
| 哪个 UID 消耗 x86 CPU cycles | `cyclePerUid` | `simpleperf` 细化到进程、线程、函数；调度 trace 解释等待 |
| 哪些 DMA-BUF 仍然存活 | `dmabufIter` | fdinfo/sysfs/服务状态用于进程和子系统归因 |
| 系统被 kernel wakelock 阻止休眠多久 | `kernelWakelockDuration` | wakeup source 统计或 ftrace 用于名称归因 |
| 指定内核锁等待多久 | `bpfLockContention` | `perf` 采样、调度 trace、源码路径用于解释调用者和影响 |

四组程序都没有在自身源码中写入 Perfetto packet（trace 中的协议消息），也没有定义 Perfetto data source（负责产出某类 trace 数据的组件）。平台上的其他消费者可以读取 map 或 iterator，再转写到 Perfetto trace；仅看到 BPF 程序已加载，无法推断 Perfetto UI 中会出现对应 track（时间线轨道）。

## 14.25.8 调试顺序

1. 查看 `/system/etc/bpf/`，确认 `.bpf` 对象是否安装进设备镜像。
2. 查看 bpffs，确认 `bpfloader` 是否加载并 pin 了 program、map 或 link。
3. 核对产品 flag、CPU 架构和内核版本是否满足加载条件。
4. 从 tracefs、BTF 和内核配置确认 attach 点及所需类型信息存在。
5. 读取 map 或 iterator，并严格按照对应版本的源码结构解析字段。
6. 记录 desync 次数、map 条目是否接近容量上限，以及明确的采集起止时间；这四组聚合程序没有统一的“丢事件”计数。
7. 用 `simpleperf`、Perfetto、sysfs、fdinfo 或服务状态补充 program 没有提供的维度。

这套顺序能区分“对象未安装”“启动时未选择”“内核拒绝加载或 attach”“没有匹配事件”“用户态解析错误”等情况，避免看到空数据就直接归因于工作负载。

## 源码索引

- [system/bpfprogs/Android.bp：四组 `.bpf` 对象的构建和架构限制](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/Android.bp)
- [cyclePerUid.c：sched_switch cycle 归因与五张 map](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/cyclePerUid.c)
- [dmabufIter.c：DMA-BUF iterator 的四字段输出](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/dmabufIter.c)
- [kernelWakelockDuration.c：全局 active 时间并集与初始化算法](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/kernelwakelockduration/kernelWakelockDuration.c)
- [kernelWakelockDuration_test.cpp：负值计时状态与初始化竞态测试](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/kernelwakelockduration/kernelWakelockDuration_test.cpp)
- [bpf_kernelwakelockduration.h：共享状态结构和固定路径](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/progs/include/bpf_kernelwakelockduration.h)
- [bpfLockContention.c：begin/end 配对与聚合](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/locks/bpfLockContention.c)
- [bpf_lock_list.h：Android 17 的锁白名单](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/locks/include/locks/bpf_lock_list.h)
- [progs.aconfig：三组启动加载 flag](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/progs.aconfig)
- [bpfloader.rs：选择、加载、auto-attach 与 bpffs 固定规则](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/bpfloader.rs)
- [frameworks/native cpucycleperuid/lib.rs：x86 cycle、RAPL 与 C FFI](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/cpucycleperuid/lib.rs)
- [frameworks/native cpucycleperuid/Android.bp：x86_64 构建限制](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/cpucycleperuid/Android.bp)
- [Android 17 kernel dmabuf_iter.c：`iter/dmabuf` 内核实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/bpf/dmabuf_iter.c)
- [Android 17 kernel wakeup.c：`combined_event_count` 语义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/base/power/wakeup.c)
- [Android 17 kernel lock.h：contention begin/end tracepoint](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/lock.h)
- [Android BPF 官方文档：加载、权限与调试基础](https://source.android.com/docs/core/architecture/kernel/bpf)

**延伸阅读**：[14.23 eBPF/BPF 在 Android 性能分析中的应用](23-ebpf-performance-analysis.md) · [14.24 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织](24-ebpf-bpfloader-architecture.md)
