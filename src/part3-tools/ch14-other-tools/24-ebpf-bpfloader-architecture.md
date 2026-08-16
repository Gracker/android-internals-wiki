---
title: "eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织"
chapter: "14.24"
section: "14.24"
status: finalized
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [ebpf, bpfloader, rust, bpf, system-architecture, timeInState]
related_chapters: ["13.8", "14.23", "17.4", "26.9"]
last_verified: "2026-08-14"
last_verified_against: "Android 17 / API 37 / android-17.0.0_r1；Android common kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "system/core/rootdir/init.rc"
  - type: aosp
    path: "packages/modules/Connectivity/bpf/loader/netbpfload.rc"
  - type: aosp
    path: "packages/modules/Connectivity/bpf/loader/netbpfload.35rc"
  - type: aosp
    path: "packages/modules/Connectivity/bpf/loader/NetBpfLoad.cpp"
  - type: aosp
    path: "system/bpf/loader/bpfloader.rs"
  - type: aosp
    path: "system/bpf/loader/Loader.cpp"
  - type: aosp
    path: "system/bpf/loader/Android.bp"
  - type: aosp
    path: "system/bpfprogs/Android.bp"
  - type: aosp
    path: "system/bpfprogs/timeInState.c"
  - type: aosp
    path: "system/bpf/loader/BpfLoader.cpp (android-15.0.0_r1)"
  - type: aosp
    path: "system/bpfprogs/Android.bp (android-15.0.0_r1)"
  - type: aosp
    path: "system/bpf/loader/bpfloader.rs (android-16.0.0_r1)"
  - type: aosp
    path: "system/bpfprogs/Android.bp (android-16.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/cputimeinstate/cputimeinstate.cpp"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_KernelCpuBpfTracking.cpp"
  - type: aosp
    path: "frameworks/native/services/gpuservice/bpfprogs/gpuMem.c"
  - type: aosp
    path: "frameworks/native/services/gpuservice/gpumem/GpuMem.cpp"
  - type: aosp
    path: "frameworks/native/services/gpuservice/gpumem/include/gpumem/GpuMem.h"
  - type: aosp
    path: "frameworks/native/services/gpuservice/tracing/GpuMemTracer.cpp"
  - type: aosp
    path: "frameworks/native/services/gpuservice/tracing/include/tracing/GpuMemTracer.h"
  - type: kernel
    path: "common/include/trace/events/{sched,power,gpu_mem}.h"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/bpf"
---

# 14.24 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织

[§14.23](23-ebpf-performance-analysis.md) 介绍如何选择 eBPF 观测点。这里转向系统启动：Android 17 在什么时机装载平台、Mainline 和 vendor BPF 对象，谁负责把已加载的 program 附加到 tracepoint，用户空间又怎样读取 map。

Mainline 是可独立于完整系统更新的 Android 模块，vendor 则指设备厂商随产品镜像交付的部分。

BPF program 是送入内核执行的字节码，map 是 program 与用户空间共享数据的内核对象。理解下面的启动链时，先把三个动作分开：

- **load**：通过 `bpf(2)` 系统调用在内核中创建 program 和 map，期间会经过 verifier（验证器）。`(2)` 表示 Linux 手册的系统调用章节。
- **pin**：把内核对象固定到 bpffs 路径。bpffs 是 BPF 虚拟文件系统；pin 会保留对象引用，使加载进程退出后，其他进程仍能按路径取得 fd（file descriptor，文件描述符）。
- **attach**：把 program 连接到 tracepoint、raw tracepoint、iterator 等触发点。tracepoint 是内核预先定义的事件，raw tracepoint 暴露更原始的参数，iterator 则让 BPF 程序遍历特定内核对象。program 已出现在 `/sys/fs/bpf`，仍不能证明它正在接收事件。

Android 17 的平台源码锚点是 `android-17.0.0_r1`，Android common kernel 的 tracepoint 以 `android17-6.18-2026-06_r6` 为准。common kernel 是 Android 使用的公共内核代码线；GKI（Generic Kernel Image）是 Android 的通用内核镜像方案，具体设备仍可能带不同基线和 vendor 改动。

## Android 17 的完整启动链

`bpfloader` 这个名字容易让人误判入口。Android 17 的 init service 由 Connectivity APEX 覆盖。init 是 Android/Linux 的第一个用户空间进程，负责按 `.rc` 文件启动服务；APEX 是 Android 可独立更新的系统模块封装。

同一个加载进程会在 Mainline、UprobeStats、平台和 vendor 加载器之间多次调用 `execve()`。`execve()` 会用新程序替换当前进程映像，成功时不会返回，PID 也不变。

下面的流程图用于标出每一段进程负责的对象范围：

```text
init
  ├─ mount bpffs at /sys/fs/bpf
  └─ trigger load-bpf-programs
       │
       ▼
/apex/com.android.tethering/bin/netbpfload
  ├─ load Connectivity BPF objects
  ├─ optional: exec uprobestatsbpfload
  └─ exec /system/bin/bpfloader
       │
       ▼
/system/bin/bpfloader                  (Rust)
  ├─ libbpf-rs: load registered /system/etc/bpf/*.bpf
  ├─ C++ vendorBpfLoader(): load /vendor/etc/bpf/*.o
  └─ exec netbpfload done
       │
       ▼
netbpfload done
  ├─ set bpf.progs_loaded=1
  └─ return to init; init can start netd
```

这个顺序来自 `system/core/rootdir/init.rc`、Connectivity 的 `netbpfload*.rc` 和各加载器入口。图中的 UprobeStats 步骤是条件分支：只有对应二进制存在时才执行，完成后再 `execve()` 平台 loader。

日志里同时出现 `NetBpfLoad`、`BpfLoader-rs` 和 `LibBpfLoader`，不能据此判断加载器被重复启动。这些 tag 来自同一 PID 先后执行的不同阶段。

### init 为什么在这个时机运行加载器

`init.rc` 在 `on init` 阶段把 bpffs 挂到 `/sys/fs/bpf`。主启动序列完成 `post-fs-data` 后触发 `load-bpf-programs`，位置早于 `zygote-start`。Connectivity 的 `netbpfload.rc` 还要求此时 APEX 与日志系统已经可用，并要求 BPF 程序在 netd 启动前加载完成。

`post-fs-data` 是 `/data` 挂载后的初始化阶段；Zygote 是 Android 应用与多数 Java 系统进程的孵化进程；netd 是系统网络守护进程。

`exec_start bpfloader` 是同步动作，init 会等它结束。加载链末端的 `netbpfload done` 设置 `bpf.progs_loaded=1`，init 随后才启动 netd。

加载器异常退出时，等待条件不会满足；service 的 `reboot_on_failure` 还会让设备以 `bpfloader-failed` 原因重启。这类故障会阻断关键启动序列，不能按普通后台服务崩溃处理。

### 三类对象由谁装载

| 对象来源 | Android 17 装载方 | 典型安装目录 | 说明 |
| --- | --- | --- | --- |
| Connectivity Mainline | Connectivity APEX 的 `netbpfload` | `/apex/com.android.tethering/etc/bpf/mainline/` | 包含 netd、clatd、offload 等网络 BPF 对象 |
| 平台 system image | Rust `bpfloader.rs` + `libbpf-rs` | `/system/etc/bpf/` 及其子目录 | 文件必须登记在 Rust descriptor 中 |
| 厂商分区 | `Loader.cpp::vendorBpfLoader()` | `/vendor/etc/bpf/*.o` | 保留 Android 旧式对象格式和加载规则 |

clatd 负责 IPv4/IPv6 地址转换，offload 指把部分网络处理交给内核或硬件。system image 是平台系统分区，vendor partition 是厂商分区。

`libbpf-rs` 是 libbpf 的 Rust binding（语言绑定）。平台 Rust 加载器不会扫描 `/system/etc/bpf` 后无条件加载每个文件。它按 `BpfFileDesc` descriptor（描述文件路径、权限和对象清单的数据结构）打开指定对象，并逐个核对 map、program 名称。

官方 BPF 文档所说的 `/system/etc/bpf` 启动装载约定仍可用来理解文件布局；分析 Android 17 的精确行为时，还要同时查看 `bpfloader.rs` 的 descriptor。

## 从 Android 15 到 Android 17 的迁移边界

Rust 化发生在 Android 16，Android 17 完成了更多平台对象的迁移：

| 平台版本 | 平台入口 | `timeInState` 构建方式 | `fuseMedia` 构建方式 |
| --- | --- | --- | --- |
| Android 15 | `BpfLoader.cpp` | `bpf { name: "timeInState.o" }` | `fuseMedia.o` |
| Android 16 | `bpfloader.rs` | 同时构建 `.o` 与 `.bpf` | `fuseMedia.o` |
| Android 17 | `bpfloader.rs` | 只构建 `timeInState.bpf` | 只构建 `fuseMedia.bpf` |

Android 16 的双构建用于迁移 libbpf/CO-RE 路径。libbpf 是 Linux 的 BPF 用户空间加载库；CO-RE（Compile Once – Run Everywhere）利用 BTF（BPF Type Format，内核类型信息格式）重定位字段访问，以兼容一组内核版本。

到了 Android 17，`system/bpfprogs/Android.bp` 中已经没有 `timeInState.o` 和 `fuseMedia.o`；C++ `Loader.cpp` 仍存在，用途收窄到 `/vendor/etc/bpf/*.o`。因此，Android 17 不能概括成“Rust 外壳调用 C++ 装载全部平台对象”。

加载器迁移也没有移除平台内部的消费接口。Android 17 的 `libtimeinstate` 与 GpuMem 仍通过 `retrieveProgram()`、`bpf_attach_tracepoint()` 和 `BpfMap` wrapper 取得 pinned 对象、完成 attach 并读写 map；这些是平台内部接口，不是普通应用 SDK。

## Rust 加载器怎样处理一个 `.bpf` 对象

`bpfloader.rs` 的 descriptor 同时声明文件路径、bpffs 前缀、map、program、权限和版本条件。`libbpf_worker()` 对每个对象执行以下工作：

1. 根据 `skip_on_user` 和构建类型决定是否跳过测试对象；
2. 检查文件是否存在，只有 `allow_missing` 对象可以缺失；
3. 用 `ObjectBuilder::open_file()` 打开 ELF 对象，再按运行内核版本关闭不适用的 map 或 program；ELF 是 Android/Linux 原生对象文件使用的格式；
4. 调用 `load()` 让内核 verifier 校验并创建对象；
5. 按 descriptor 逐一 pin map 和 program，设置 Unix mode、owner、group；
6. descriptor 少写了一个 ELF 中的 map 或 program 时返回错误，避免静默留下无权限定义的对象。

map 的 pin 路径遵循：

`/sys/fs/bpf/<prefix>/map_<ELF 文件名>_<map 名>`

program 或持久化 link 的路径遵循：

`/sys/fs/bpf/<prefix>/prog_<ELF 文件名>_<program 名>`

文件名中的点会被替换成下划线。这里的 `<ELF 文件名>` 取 `file_stem()`，因此 `timeInState.bpf` 会变成 `timeInState`。UID 频率驻留 map 的实际路径是：

`/sys/fs/bpf/cputimeinstate/map_timeInState_uid_time_in_state_map`

### load 与 auto-attach 的边界

`ProgDesc::new()` 默认把 `auto_attach` 设为 `false`。此时 loader 只 pin program，消费者稍后取得 program fd 并完成 attach。

descriptor 明确写入 `auto_attach: true` 时，loader 才会调用 libbpf 的 `attach()`，pin 返回的 BPF link，再用 `disconnect()` 阻止 Rust link 对象析构时解除附加。BPF link 是内核中表示“program 已连接到 attach 点”的对象。

Android 17 中的例子：

| 对象 | loader 是否自动附着 | 后续责任 |
| --- | --- | --- |
| `timeInState.bpf` | 否 | `libtimeinstate` 附着三个程序 |
| `gpuMem.bpf` | 否 | GpuService 附着 `gpu_mem/gpu_mem_total` |
| `kernelWakelockDuration.bpf` | 是 | loader pin link |
| `dmabufIter.bpf` | 是 | loader pin iterator link |
| `bpfLockContention.bpf` | 是 | loader 在内核 6.1+ pin 两个 tracepoint link |

“program 已 pin”只能证明加载阶段完成。map 始终为空时，还要检查消费者是否启动、attach 是否成功，以及对应内核 tracepoint 是否有事件。

### 基础清单与条件清单

Android 17 的静态 `FILE_ARR` 包含：

- `timeInState.bpf`
- `fuseMedia.bpf`
- `gpuMem.bpf`
- `gpuWork.bpf`
- `memevents/bpfMemEvents.bpf`
- 仅非 user 构建加载的 `bpfMemEventsTest.bpf`
- 仅非 user 构建加载的 `bpfRingbufProg.bpf`

`get_file_vec()` 再根据 aconfig flag 加入 `kernelWakelockDuration.bpf`、`dmabufIter.bpf`、`bpfLockContention.bpf`；x86_64 还可加入 `cyclePerUid.bpf`。aconfig 是 Android 平台的类型化 feature flag 系统。

部分 descriptor 带 `min_kver=6.1`，loader 会按 `uname()` 返回的运行内核版本关闭不适用的 ELF section（对象文件分区）。

`bpfloader` 的 `Android.bp` 把 `timeInState.bpf`、`kernelWakelockDuration.bpf`、`dmabufIter.bpf` 和 `bpfLockContention.bpf` 列为 required 模块，也就是随 loader 一起打包的构建依赖。`bpftool` 只进入 debuggable 产品；量产 user build 通常不含这个调试命令。

### owner、group 与 mode

Rust `MapDesc::new()` 把 owner 固定为 `AID_ROOT`，descriptor 传入的是 group。`timeInState` 的 map 因而是 `root:system`，读写权限按用途分为 owner-only、group read/write 和 other read/write 等不同组合。

原 BPF C 宏中的 `AID_SYSTEM` 也表达访问组，但 Android 17 的最终 mode 与属主应以 Rust descriptor 为准。

这项设计阻止普通 App 直接读取平台 BPF 统计。即使知道 pin 路径，调用进程仍要通过 DAC（基于 owner/group/mode 的传统自主访问控制）和 SELinux 安全域检查；具备 shell 权限也不等于具备 map 的读写权限。

## timeInState：三个程序、十五个 map

`timeInState.c` 统计 UID 与受跟踪进程在 CPU 频点上的运行时间，也维护同时处于 active 状态的 CPU 数。Android 17 的对象包含 15 个 map，按用途可分为四组：

| 用途 | map |
| --- | --- |
| CPU 与时间状态 | `cpu_last_pid_map`、`cpu_last_update_map`、`nr_active_map`、`policy_nr_active_map` |
| CPU policy 与频率索引 | `cpu_policy_map`、`freq_to_idx_map`、`policy_freq_idx_map` |
| UID 与整机累计 | `uid_time_in_state_map`、`uid_concurrent_times_map`、`uid_last_update_map`、`total_time_in_state_map` |
| 进程跟踪 | `pid_tracked_hash_map`、`pid_tracked_map`、`pid_task_aggregation_map`、`pid_time_in_state_map` |

map 的 PERCPU、HASH、ARRAY 类型以 `timeInState.c` 中的 `DEFINE_BPF_MAP_*` 声明为准。PERCPU 为每个逻辑 CPU 保存独立 value，HASH 用稀疏 key 查找，ARRAY 使用固定整数索引。

`pid_tracked_hash_map` 与 `pid_tracked_map` 分工不同。用户空间先用 `BPF_NOEXIST`（仅当 key 不存在时插入）向 HASH map 原子占用一个空闲 slot（固定数组槽位），再把 PID 与状态写入同一 index 的 ARRAY map。BPF program 会把这段定长遍历在编译期完全展开，因此 verifier 看不到运行时循环。

### 三个触发点各做什么

| program | 内核触发点 | 工作 |
| --- | --- | --- |
| `tracepoint_sched_sched_switch` | `sched/sched_switch` | 结算刚被切出的任务在当前频率上的时间，更新 UID、总量、并发度和可选进程统计 |
| `tracepoint_power_cpu_frequency` | `power/cpu_frequency` | 把 CPU policy 的当前频率更新为内部索引 |
| `tracepoint_sched_sched_process_free` | raw tracepoint `sched_process_free` | 清理退出 PID 的跟踪 slot 与聚合映射 |

三个触发点都能在 `android17-6.18-2026-06_r6` 的 common kernel 源码中找到：`sched_switch`、`sched_process_free` 位于 `include/trace/events/sched.h`，CPU frequency 事件位于 `include/trace/events/power.h`。

### `sched_switch` 的计账顺序

处理函数用 `cpu_last_update_map` 保存每 CPU 上一次切换时间，用 `cpu_last_pid_map` 检查本次 `prev_pid` 是否等于上次记录的 `next_pid`。这项检查处理 suspend-to-RAM（内存保留、其余硬件进入低功耗）恢复后可能连续出现的 idle 切换，避免重复修改 active CPU 数。

通过一致性检查后，程序：

1. 根据 `prev_pid` 与 `next_pid` 更新整机和 policy 的 active CPU 计数；
2. 从 `cpu_policy_map` 与 `policy_freq_idx_map` 取得当前频率 bucket；
3. 读取当前被切出任务的 UID，计算 `ktime_now - old_last`；
4. 把 delta 写入 UID 驻留时间、UID 并发时间与整机总量；
5. 若 TGID 在跟踪列表中，再写入进程级频率驻留 map。

CPU policy 是共享同一调频策略的一组 CPU，frequency bucket 是把频点映射成的紧凑索引。`ktime` 是内核单调时钟时间，delta 是本次与上次事件的时间差。

SDK sandbox 是 Android 为第三方 SDK 提供的隔离进程环境。其 UID 有一段专门逻辑：运行时间会记到对应 App UID，也会记到保留的 `AID_SDK_SANDBOX` 聚合 UID。framework 侧在计算系统总量时要处理这份重复记录。

函数返回的 `ALLOW=1` 是该 Android tracepoint BPF wrapper 与 simpleperf 共存所需的返回值，不是 Linux 调度器的任务准入结果。

### 初始化、附着与读取都在 `libtimeinstate`

`frameworks/native/libs/cputimeinstate/cputimeinstate.cpp` 补齐了 loader 之后的初始化、attach 与读取工作：

- 扫描 `/sys/devices/system/cpu/cpufreq/policy*`，建立 policy、CPU 与频率表；
- 写入 `cpu_policy_map`、`freq_to_idx_map` 和 policy 当前频率；
- 取得三个 pinned program，分别调用 `bpf_attach_tracepoint()` 与 `bpf_attach_raw_tracepoint()`；
- 通过 pinned map 读取 UID 频率时间、UID 并发时间、整机时间和进程聚合时间。

`system_server` 中的 `KernelCpuBpfTracking` 通过 JNI（Java Native Interface）调用 `isTrackingUidTimesSupported()`、`startTrackingUidTimes()` 和 `getCpuFreqs()`，更高层的 BPF map reader 再使用这些入口。

这证明 framework 可以接入 `libtimeinstate`；仍不能把 `dumpsys batterystats` 中任意一个 CPU 字段直接等同于某个 BPF map。

## gpuMem：loader、GpuService 与 Perfetto 的分工

`gpuMem.c` 挂在 `gpu_mem/gpu_mem_total` tracepoint。Android 17 common kernel 的 `include/trace/events/gpu_mem.h` 定义了 `gpu_id`、`pid` 和 `size` 三个字段，其中 `pid=0` 表示全局总量，正数 PID 表示进程总量。

BPF 程序使用 64 位 key：

`key = (gpu_id << 32) | pid`

value 是字节数。事件的 `size` 为 0 时删除条目，其余情况更新该 GPU、PID 的当前总量。map 保留当前快照，不保存每次分配与释放的历史。

Android 17 的责任划分如下：

1. Rust loader 从 `/system/etc/bpf/gpuMem.bpf` 加载对象，并 pin program 与 `gpu_mem_total_map`；
2. GpuService 等待 `bpf.progs_loaded`，取得 pinned program；
3. GpuService 调用 `bpf_attach_tracepoint()`；GPU 驱动尚未注册 tracepoint 时每秒重试，超时常量为 30 秒；
4. GpuService 以只读 wrapper `BpfMapRO<uint64_t, uint64_t>` 遍历 map；
5. `dumpsys gpu --gpumem` 输出按 GPU 和 PID 组织的当前快照；`dumpsys` 是导出 Android 系统服务状态的命令。

`gpuMem.bpf` 已列入 Rust `FILE_ARR`，不再走厂商 `.o` 扫描路径。

### Perfetto 看到的是什么

GpuService 注册的 Perfetto producer data source 名为 `android.gpu.memory`。producer 是向 Perfetto 写 trace packet 的数据生产者，data source 是采集时选择的数据源名称。一次采集开始时，`GpuMemTracer` 遍历 `gpu_mem_total_map`，为已有条目写入 `gpu_mem_total_event` 初始 packet。

`GpuMemTracer` 本身没有循环轮询这个 map。若同一份 trace 还要记录后续变化，采集配置需另外启用 `gpu_mem/gpu_mem_total` ftrace 事件；ftrace 是 Linux 内核跟踪框架。

所以，UI 中出现 GPU memory counter（随时间变化的数值轨道），不代表 Perfetto 在持续轮询 BPF map。map 在这里提供采集起点的全量快照，内核 tracepoint 提供后续事件流。若设备 GPU 驱动没有发出 `gpu_mem_total` tracepoint，program 可以成功加载，map 仍会为空。

## 调试：按加载、附着、数据三层检查

### 1. 确认启动链完成

以下命令用于确认完成属性、相关进程日志和 pin 目录：

```bash
adb shell getprop bpf.progs_loaded
adb shell logcat -d -s \
  'bpfloader:*' 'LibBpfLoader:*' 'BpfLoader-rs:*' \
  'NetBpfLoad:*' 'NetBpfLoader:*'
adb shell find /sys/fs/bpf -maxdepth 3 -print
```

属性应为 `1`。日志过滤器来自 Android 17 的 `netbpfload.35rc` 调试说明。Rust logger 把 Info 及以上写入 Android main log buffer，只把 Error 写入 `/dev/kmsg`；`dmesg` 适合查致命错误，不能代替完整的 logcat 启动日志。

`getprop` 读取 Android property，`logcat` 读取用户空间日志缓冲区，`find` 列出 bpffs 中的 pin 路径。`/dev/kmsg` 写入内核日志环形缓冲区，`dmesg` 读取该缓冲区；两者看到的内容范围与 logcat 不同。

### 2. 在 debuggable 构建查看内核对象

`bpftool` 是内核配套的 BPF 对象检查工具，也是 `bpfloader` 在 debuggable 产品中的 required 模块。userdebug/eng 设备取得 root 后，可用以下命令核对 program 与 map 元数据：

```bash
adb root
adb shell bpftool prog show
adb shell bpftool map show
adb shell bpftool prog show pinned \
  /sys/fs/bpf/cputimeinstate/prog_timeInState_tracepoint_sched_sched_switch
adb shell bpftool map show pinned \
  /sys/fs/bpf/cputimeinstate/map_timeInState_uid_time_in_state_map
```

`bpftool map dump pinned <path>` 能按内核中的 raw key/value 布局导出内容，但 `timeInState` 的 key、PERCPU value 和 frequency bucket 需要结合 `bpf_timeinstate.h` 解码。对 pin 文件执行 `cat` 得不到有意义的 map 内容；bpffs pin 是内核对象句柄，不是普通数据文件。

### 3. 确认消费者已经附着

program 存在而 map 无数据时，检查消费进程：

```bash
adb shell dumpsys gpu --gpumem
adb shell logcat -d -s 'GpuMem:*' 'GpuMemTracer:*' 'libtimeinstate:*'
adb shell ls /sys/kernel/tracing/events/gpu_mem/gpu_mem_total
adb shell ls /sys/kernel/tracing/events/sched/sched_switch
adb shell ls /sys/kernel/tracing/events/power/cpu_frequency
```

`dumpsys gpu --gpumem` 的输出能区分 GpuService 初始化失败与 map 为空。tracefs 是承载 ftrace 控制项和事件目录的调试文件系统；目录存在只能证明内核导出了事件，仍要结合 GpuService 或 `libtimeinstate` 日志判断 attach 是否成功。

### 4. 解释常见故障形态

| 现象 | 优先检查 |
| --- | --- |
| `bpf.progs_loaded` 不是 `1` | `NetBpfLoad`、`BpfLoader-rs`、verifier 日志，文件缺失与启动重启原因 |
| 对象文件存在但没有 pin | descriptor 名称是否与 ELF section 一致、内核版本门槛、verifier 拒绝原因 |
| program 已 pin，map 一直为空 | 消费者是否执行 attach、tracepoint 是否存在、驱动是否发出事件 |
| root 可读，shell 不可读 | pin 的 mode、group 与 SELinux；不要把它误判为加载失败 |
| 测试对象在 user build 缺失 | 检查 `skip_on_user`，这是预期行为 |
| `bpftool` 命令不存在 | 量产 user build 未安装该调试模块 |

排查 verifier 失败时，从日志末尾向前找到第一个被拒绝的 program，再核对它依赖的 helper、context 字段、BTF 与内核版本。helper 是内核向 BPF program 开放的受限函数，context 是触发点传入的参数结构。只看到上层“load failed”不足以定位原因。

## 源码阅读路线

阅读 Android 17 加载链时，建议沿调用方向查看：

1. `system/core/rootdir/init.rc`：bpffs mount 与 `load-bpf-programs` 触发位置；
2. `packages/modules/Connectivity/bpf/loader/netbpfload.rc`、`netbpfload.35rc`：service override、同步等待与失败策略；
3. `packages/modules/Connectivity/bpf/loader/NetBpfLoad.cpp`：Mainline 对象加载、`exec /system/bin/bpfloader` 与 `done` 属性；
4. `system/bpf/loader/bpfloader.rs`：平台 `.bpf` descriptor、pin、权限、版本过滤和 auto-attach；
5. `system/bpf/loader/Loader.cpp`：厂商 `.o` 扫描与回到 `netbpfload done`；
6. 具体 BPF C 源码与消费者：例如 `timeInState.c` 对 `cputimeinstate.cpp`，`gpuMem.c` 对 `GpuMem.cpp`。

这条路线能持续区分“谁把对象装进内核”“谁把 program 连到事件”“谁读取 map”。只读 BPF C 文件会漏掉初始化数据、权限和 attach 生命周期。

## 参考资料

- [Android 17 platform manifest](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml)
- [Android 17 init.rc](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/rootdir/init.rc)
- [Android 17 netbpfload.rc](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/bpf/loader/netbpfload.rc)
- [Android 17 netbpfload.35rc](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/bpf/loader/netbpfload.35rc)
- [Android 17 NetBpfLoad.cpp](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/bpf/loader/NetBpfLoad.cpp)
- [Android 17 Rust bpfloader](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/bpfloader.rs)
- [Android 17 vendor Loader.cpp](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/Loader.cpp)
- [Android 17 bpfloader build definition](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/Android.bp)
- [Android 17 system BPF program build definition](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/Android.bp)
- [Android 17 timeInState.c](https://android.googlesource.com/platform/system/bpfprogs/+/refs/tags/android-17.0.0_r1/timeInState.c)
- [Android 17 libtimeinstate consumer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/cputimeinstate/cputimeinstate.cpp)
- [Android 17 KernelCpuBpfTracking JNI](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/com_android_internal_os_KernelCpuBpfTracking.cpp)
- [Android 17 gpuMem.c](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/bpfprogs/gpuMem.c)
- [Android 17 GpuMem consumer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/gpumem/GpuMem.cpp)
- [Android 17 GpuMem interface](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/gpumem/include/gpumem/GpuMem.h)
- [Android 17 GpuMem Perfetto producer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/tracing/GpuMemTracer.cpp)
- [Android 17 GpuMem Perfetto data source declaration](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/tracing/include/tracing/GpuMemTracer.h)
- [Android common kernel 6.18 sched tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
- [Android common kernel 6.18 power tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/power.h)
- [Android common kernel 6.18 GPU memory tracepoint](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/gpu_mem.h)
- [AOSP eBPF architecture documentation](https://source.android.com/docs/core/architecture/kernel/bpf)

**延伸阅读**：[14.23 eBPF/BPF 在 Android 性能分析中的应用](23-ebpf-performance-analysis.md) · [5.6 Android 功耗管理](../../part1-fundamentals/ch05-cpu-power/06-android-power.md) · [13.8 Android Tracing 基础设施](../ch13-perfetto/08-tracing-infrastructure.md) · [26.9 eBPF 在线追踪与 Binder 语义重建](../../part5-app/ch26-observability/09-ebpf-online-tracing-binder-semantics.md)
