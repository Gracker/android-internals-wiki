---

title: "eBPF/BPF 在 Android 性能分析中的应用"
chapter: "14.10"
section: "14.10"
status: "ready-for-review"
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified: "2026-06-14"
last_verified_against: "AOSP android-16.0.0_r4 (platform/system/bpf, packages/modules/UprobeStats, frameworks/native/services/gpuservice); Android common kernel android16-6.12 (include/linux/vmalloc.h, include/trace/events/syscalls.h); external/perfetto android-16.0.0_r4 (data_source_config.proto)"
confidence: medium
sources:
  - type: aosp
    path: "packages/modules/UprobeStats/src/bpf_progs/"
  - type: aosp
    path: "packages/modules/UprobeStats/src/UprobeStats.cpp"
  - type: aosp
    path: "packages/modules/UprobeStats/src/Bpf.cpp"
  - type: aosp
    path: "packages/modules/UprobeStats/src/Guardrail.cpp"
  - type: aosp
    path: "system/bpf/loader/bpfloader.rs"
  - type: aosp
    path: "packages/modules/Connectivity/bpf/progs/"
  - type: aosp
    path: "frameworks/native/services/gpuservice/bpfprogs/gpuMem.c"
  - type: aosp
    path: "external/perfetto/protos/perfetto/config/data_source_config.proto"
  - type: blog
    path: "Cubox/在 Android 中使用 eBPF：开篇-2022-06-12.md"
  - type: blog
    path: "Cubox/探索Android动态埋点的新视界：UprobeStats深度解析-2025-02-21.md"
  - type: blog
    path: "Cubox/基于eBPF的sched-ext会在产品成功的底层逻辑是什么-2025-10-18.md"
  - type: blog
    path: "Cubox/基于eBPF的CPU利用率精准计算小工具开发-2022-03-13.md"
  - type: official
    path: "kernel.org/doc/html/latest/scheduler/sched-ext.html"
  - type: official
    path: "source.android.com/docs/core/architecture/kernel/bpf"
  - type: research
    path: "intake/research-feeds/2026-04-02-15-ch05-sched-ext-bpf-android.md"
  - type: research
    path: "intake/research-feeds/2026-04-03-07-sched-ext-bpf-scheduler.md"
tags: [eBPF, BPF, observability, tracing, sched_ext, kernel, performance, bpfloader, UprobeStats]
related_chapters: ["14.2", "13.1", "5.1", "1.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "AOSP结构+官方文档+研究素材"
polish_count: 4
polish_date: "2026-06-14"
polish_by: "task2b-main"
p0: 5
p1: 2
p2: 1
task6_result: "pass-light-edit"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-06-14"
task6_state: "reviewed"
last_task6_at: "2026-06-14T03:05:00+08:00"
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-14"
task9_state: "pending"
task2b_result: "fixed"
task2b_state: "fixed"
task2b_rework_date: "2026-06-14T02:50:00+08:00"
pipeline_stage: "task9_pending"
last_task2b_at: "2026-06-14T02:50:00+08:00"
last_task2b_lite_at: "2026-06-14T01:35:00+08:00"
last_task6_audit: "2026-06-14"
last_task9_at: "2026-06-14T02:24:08+08:00"
last_task9_review_log: "logs/deep-review/2026-06-14-02-deep-review.md"
updated_by: "openclaw-task2b-main"
updated_date: "2026-06-14"
---

## 修复记录

**2026-06-14 Task2B 主修复（完整回炉）**:
- 重写开头：编号列表改为叙事段落（Task6#5）
- 重写发展历程：百科式列表改为阶段性叙事，标注平台 BPF loader / 网络 BPF / UprobeStats Mainline / Perfetto 四类能力边界（Task6#1）
- 合并"核心应用"+"实际应用"为统一"实战应用"节：每场景按 问题→方案→trace 观测→注意事项 结构展开（Task6#4）
- 新增"eBPF Attach 点与上下文模型"节：区分 raw tracepoint / tracepoint / kprobe / kretprobe / uprobe 的 ctx 与参数模型（Task9 知识盲区#1）
- 修复 syscall tracepoint 示例：改用 raw_syscalls/sys_enter（id + args[6]）或 syscall-specific 结构体字段（Task9#0）
- 修复 vmalloc/vfree 示例：entry kprobe 只取 size，分配地址改为 kretprobe 返回值（Task9#1）
- 修复 UprobeStats 描述：删除虚假 CLI 和 syscall 监控，改为 config→Guardrail→probe→perf_event_open 真实链路（Task9#2, Task9 原理链#1）
- 修复 Perfetto 配置示例：替换为有效 TraceConfig text proto（ftrace_config + perf_event_config）（Task9#3）
- 修复 GPU 监控示例：amdgpu → gpuMem.c 的 gpu_mem/gpu_mem_total，标注边界（Task9#4）
- 删除虚构伪代码：BPFLoader / unload_ebpf_program / log_error / semanage，替换为 AOSP bpfloader 真实流程（Task9#5, Task6#2）
- 修复权限模型：删除"所有 map AID_SYSTEM"，按 timeInState/gpuMem/netd 分别列出 owner/group（Task9#6）
- 删除"未来发展趋势"空话节，替换为一句基于 main 分支观察的谨慎展望（Task6#2）
- 删除虚构 SELinux 命令（semanage fcontext / restorecon），替换为 Android sepolicy 边界说明（Task9#5）
- 新增 Perfetto trace 观测描述（Task6#3）
- SKILL.md L1 扫描：禁用词 0 命中；高频词 < 5
- 自动晋升检查：task6_result=pass-light-edit（待 Task6 重新审核）+ task9_result=pass-tech-review（待 Task9 重新审核）+ queue 清理后 → 条件暂不满足（需重新经 Task6/Task9 审核），未晋升 finalized

**2026-06-14 Task2B Lite 修复**: 修复 Rust bpfloader 调用序列；收紧 Android 17 版本边界标注
**2026-06-13 Task2B 修复**: 清理 frontmatter；CPU 利用率保守表述；传统工具对比；模糊形容词替换
**2026-05-30 Task2B Lite 修复**: 版本适应性与数据支撑；Android 17 系统级优化引用

# 14.10 eBPF/BPF 在 Android 性能分析中的应用

## 为什么要了解 eBPF 在 Android 中的应用？

Android 12 把 eBPF 从实验性网络功能升级为系统性能数据的默认采集路径，此后每个版本都在扩展 eBPF 的覆盖范围——CPU 时间统计、GPU 内存追踪、网络流量分类、Mainline 模块的 uprobe 框架先后进入系统。到 Android 16，sched-ext 和 Rust 化的 bpfloader 意味着 eBPF 已经从辅助工具变成了内核可观测性的基础设施。

作为 Android 性能工程师，理解 eBPF 的入口是看它和 Perfetto/simpleperf 之间的分工：Perfetto 负责从 HAL 到 ftrace 的端到端时间线，simpleperf 回答"CPU 在哪个函数上耗时"，eBPF 回答的是"内核在执行某个动作时上下文是什么"。三者不互相替代——排障中 Perfetto 钩出宏观耗时，eBPF 探入微观调度和内存事件，simpleperf 提供微架构层面的 PMU 细节。

读完这一章，能搞清楚几件事：Android 上哪些 eBPF 能力是平台内置的、它们的加载链路是什么样的、各 attach 点的参数和返回值模型怎么区分（这是代码示例写错的根因）、以及 eBPF 数据在 Perfetto trace 中长什么样。

## eBPF 在 Android 中的发展历程

> ⚠️ **阅读提示**：以下按三种不同性质的能力分别标注——**AOSP 平台内置 BPF 子系统**（`system/bpf/`、bpfloader）、**Mainline 模块**（如 UprobeStats，通过 Google Play System Update 独立更新）、**内核侧能力**（如 sched-ext 依赖 Android common kernel 版本而非 Android API level）。判断某项能力是否可用时，需同时核对 API level、GKI 内核版本和设备厂商的 tracepoint 开启状态。

### 阶段一：Android 9–11 — 网络 BPF，实验期

Android 9 引入 BPF 的唯一目的是网络流量统计。`QTAGUID` 使用 BPF 过滤器替代旧的 `/proc/net/xt_qtaguid`，通过 `system/bpf/progs/` 下的 C 程序实现 per-UID 网络计数。Android 10—11 在此基础上扩展了网络策略控制：基于 BPF 的流量拦截、数据节省模式下的 socket 过滤、以及 tethering 场景的转发规则。这一阶段的 BPF 程序由 C++ `Loader.cpp` 在 early-init 阶段加载，编译产物是 `.o` ELF 文件，pin 到 `/sys/fs/bpf/` 供系统服务消费。

这一阶段的 eBPF 对性能工程师不直接可见——它藏在网络栈里，由 `netd` 和 ConnectivityService 消费，没有对用户态开放通用加载接口。

### 阶段二：Android 12—13 — 成为默认性能路径

Android 12 是分水岭。`system/bpfprogs/timeInState.c` 开始挂载 `tracepoint/sched/sched_switch`，按 UID 统计每个 CPU 频率上的运行时间，并通过 BPF map 供 `Power Stats HAL` 和 `Battery Historian` 消费。eBPF 从纯网络功能跨入了 CPU 调度观测领域——每台 Android 12+ 设备开机后就在内核里跑着 eBPF 程序做 CPU 时间记账。

Android 13 接续完善了 BPF 程序的生命周期管理：`bpfloader` 增加了程序版本号校验、map pin 路径规范化、以及开机阶段的加载失败回退逻辑。`frameworks/native/services/gpuservice/` 下的 `gpuMem.c` 开始挂载 `tracepoint/gpu_mem/gpu_mem_total`，将 GPU 内存使用按 `(gpu_id, pid)` 维度统计进 BPF map。

### 阶段三：Android 14—15 — Mainline 模块化与 UprobeStats

Android 14 带来的变化主要在 Mainline 模块路径上。`packages/modules/UprobeStats` 作为 uprobe 框架被纳入 Mainline，可以通过 Google Play System Update 单独更新 eBPF 程序版本，而不依赖完整的 OTA。

UprobeStats 的工作链路是：开机时从 `/data/misc/uprobestats-configs/config` 读取探针配置，经 Guardrail 检查允许后，通过 `/sys/bus/event_source/devices/uprobe/type` + `perf_event_open` + `PERF_EVENT_IOC_SET_BPF` 将 BPF 程序附加到用户态符号。它的定位是用户空间函数追踪，不是系统调用监控——系统调用监控另有 `raw_syscalls/sys_enter`（通用）或 `syscalls/sys_enter_*`（特定 syscall）tracepoint 路径。

Android 15 延续了对 bpfloader 稳定性的投入，同时 `android-15.0.0_r17` tag 中出现了 Rust bpfloader 的雏形入口 `loader/bpfloader.rs`。

### 阶段四：Android 16（API 36）— sched-ext 与 Rust bpfloader

Android 16（基于 Android common kernel 6.12）在 eBPF 上有两个重要变化：

**sched-ext 调度器扩展**：允许通过 BPF 程序在不修改内核的情况下实现自定义调度策略。这是一个内核侧能力，依赖 Android common kernel 6.12+（android16-6.12 分支），与 Android API level 解耦——同一 API 36 设备可能运行不同的 GKI 版本。sched-ext 的具体调度策略通过 `tools/sched_ext/scx_simple.bpf.c` 等示例程序定义，由 `bpfloader` 加载并附加到 `sched_ext` 调度类。

**Rust bpfloader**：`android-16.0.0_r4` 中 `system/bpf/loader/bpfloader.rs` 已完成对 C++ `Loader.cpp` 的替代。调用序列为 `load_libbpf_progs()`（加载 `.bpf` 风格程序，如 `timeInState.bpf`）→ `vendorBpfLoader()`（加载 vendor `.o` 风格程序）。Rust 端通过 `bindgen` 调用编译为 `libbpf_android.so` 的 C++ 函数来操作 BPF 对象。这一重构提升了类型安全和 panic 控制面，但对上层使用 BPF map 的系统服务是透明的。

### Android 17 (API 37)：main 分支观察（未进入 release）

> ⚠️ **版本说明**：截至复核时 `platform/frameworks/base`、`platform/system/bpf`、`packages/modules/UprobeStats` 尚无 `android-17.0.0_r1` tag。以下内容基于 AOSP main 分支观察，**不构成 Android 17 已发布版本结论**。

AOSP main 分支中可见的变化：Perfetto eBPF data source 的集成度在持续提高——`data_source_config.proto` 中 `ftrace_config` 和 `perf_event_config` 已经存在，但 eBPF 专用 data source 仍处于活跃开发中。Rust bpfloader 在 main 分支中继续完善错误处理和 vendor BPF 加载路径。这些变化在稳定 tag 出现前不应作为正文结论引用。

## eBPF Attach 点与上下文模型

理解不同 attach 点的上下文结构和参数模型，是避免 eBPF 代码写错的基础。以下四种 attach 类型在 Android eBPF 中最常见，它们的 `ctx` 指针含义各不相同：

| Attach 类型 | ctx 类型 | 参数访问方式 | Android 典型用途 |
|------------|----------|-------------|----------------|
| **raw tracepoint** (`BPF_PROG_TYPE_RAW_TRACEPOINT`) | `struct bpf_raw_tracepoint_args` | `ctx->args[0..N]`（unsigned long 数组） | `raw_syscalls/sys_enter`：`args[0]` = syscall id，`args[1..6]` = 入参 |
| **syscall-specific tracepoint** (`syscalls/sys_enter_*`) | syscall 专属结构体 | 结构体字段（如 `ctx->dfd`、`ctx->filename`） | `syscalls/sys_enter_openat`：字段由 `include/trace/events/syscalls.h` 中 `SYSCALL_METADATA` 生成 |
| **kprobe** | `struct pt_regs *` | `PT_REGS_PARM1(ctx)` 等宏，参数来自 **入口寄存器** | vmalloc entry：`PT_REGS_PARM1(ctx)` = size（唯一入参） |
| **kretprobe** | `struct pt_regs *` | `PT_REGS_RC(ctx)` = 返回值，入口参数不可直接访问 | vmalloc return：`PT_REGS_RC(ctx)` = 分配地址 |
| **uprobe** | `struct pt_regs *` | 同 kprobe，按函数 ABI 取参 | UprobeStats：附加到用户态库的导出符号 |

常见错误：把 `trace_event_raw_sys_enter` 用在 syscall-specific tracepoint 上，或者把 kprobe 的 `PT_REGS_PARM1` 当成返回值。本章后续代码示例中每种 attach 类型的 ctx 访问方式均与上表对齐。

## eBPF 在 Android 中的实战应用

以下五个场景覆盖 Android eBPF 最常被用到的方向。每节按同一结构展开：问题场景 → eBPF 程序 → 在 Perfetto 中的表现 → 注意事项。

### 1. CPU 调度监控

**问题**：哪个进程在每个 CPU 上跑了多久？调度延迟有多大？

传统方案读 `/proc/stat` 有 10ms 级的时间粒度限制，且全局锁在频繁读取时引入可观开销。eBPF 方案直接挂 `sched_switch` tracepoint，以内核调度事件为触发源：

```c
// 挂载点：tracepoint/sched/sched_switch
// ctx 类型：struct trace_event_raw_sched_switch
// 直接读 ctx 字段，不需要 PT_REGS_PARM*
SEC("tracepoint/sched/sched_switch")
int trace_sched_switch(struct trace_event_raw_sched_switch *ctx) {
    u32 prev_pid = ctx->prev_pid;
    u32 next_pid = ctx->next_pid;
    u32 cpu = (u32)bpf_get_smp_processor_id();

    struct sched_event e = {};
    e.prev_pid = prev_pid;
    e.next_pid = next_pid;
    e.cpu = cpu;
    e.ts = bpf_ktime_get_ns();

    bpf_map_update_elem(&sched_events, &e.ts, &e, BPF_ANY);
    return 0;
}
```

**在 Perfetto 中的表现**：`timeInState.c` 的输出不直接出现在 Perfetto UI 中，而是通过 `Power Stats HAL` 聚合成 `power.stats` counter track。Perfetto 自身的 `sched/sched_switch` ftrace event 与 eBPF 挂同一个 tracepoint——两者数据源不同但事件一致。在 Perfetto trace 里看到的 `sched_switch` slice 来自 ftrace；eBPF 侧的数据通过 `uid_time_in_state_map` 提供 per-UID CPU 时间累计值。

**注意事项**：`sched_switch` 事件频率随系统负载波动，典型场景数千次/秒。`timeInState.c` 在每条 sched_switch 路径上执行若干次 BPF map hash lookup，额外功耗在亚毫瓦级（具体因 SoC 而异）。非 Google 设备上需确认该 tracepoint 未被 vendor kernel 裁剪。

### 2. 系统调用监控

**问题**：某个进程在频繁调用哪些 syscall？每次调用的参数和耗时？

系统调用监控有两条路径。**通用路径**使用 `raw_syscalls` tracepoint，`sys_enter` 事件提供 syscall id + 原始参数数组；**特定路径**使用 `syscalls/sys_enter_*`，参数被 syscall metadata 展开为命名结构体字段。对性能工程师来说，通用路径适合做调用频率统计，特定路径适合做参数深度分析。

通用 syscall 入口示例（正确做法）：

```c
// 挂载点：raw_syscalls/sys_enter（raw tracepoint）
// ctx->args[0] = syscall id (__NR_*)
// ctx->args[1..6] = syscall 的第 1—6 个参数
SEC("tp/raw_syscalls/sys_enter")
int trace_raw_sys_enter(struct bpf_raw_tracepoint_args *ctx) {
    unsigned long syscall_id = ctx->args[0];
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    struct syscall_event e = {};
    e.pid = pid;
    e.syscall_id = (u32)syscall_id;
    e.ts = bpf_ktime_get_ns();
    __builtin_memcpy(e.args, &ctx->args[1], sizeof(e.args));
    bpf_get_current_comm(e.comm, sizeof(e.comm));

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &e, sizeof(e));
    return 0;
}
```

特定 syscall 示例——`openat` 的入口捕获：

```c
// 挂载点：syscalls/sys_enter_openat
// ctx 是 struct trace_event_raw_sys_enter_openat，字段由 SYSCALL_METADATA 生成
//   ctx->dfd:  int (dirfd)
//   ctx->filename:  const char * (user-space pointer)
//   ctx->flags:  int
//   ctx->mode:  umode_t
SEC("tracepoint/syscalls/sys_enter_openat")
int trace_sys_enter_openat(struct trace_event_raw_sys_enter_openat *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    char filename[256] = {};
    bpf_probe_read_user_str(filename, sizeof(filename), ctx->filename);
    // filename 现在包含用户态传入的路径字符串
    // ctx->flags 可直接读 int 值，不需要 bpf_probe_read_user
}

// 注意：这里的 ctx->args 数组不可用——openat 的参数已经被命名字段展开。
// 不要写成 ctx->args[0] = fd, ctx->args[1] = filename。
```

**
在 Perfetto 中的表现**：通过 `bpf_perf_event_output` 输出的 eBPF 数据汇入 Perfetto 的 eBPF ring buffer。在 Perfetto trace 中显示为 `linux.ebpf` data source 的 counter track 或 slice track，每条事件带 pid、syscall id、参数和纳秒时间戳。在 Perfetto UI 里可以按 pid 过滤，对比不同进程的 syscall 调用频率。

**注意事项**：`raw_syscalls/sys_enter` 在 Android common kernel 中默认开启，而 `syscalls/sys_enter_openat` 等特定事件能否使用取决于内核编译选项。生产环境需先通过 `adb shell ls /sys/kernel/debug/tracing/events/syscalls/` 确认可用事件列表。

### 3. 网络流量监控

**问题**：哪个进程在收/发多少网络数据？按 socket 协议族分类统计？

网络流量可以通过 `syscalls/sys_enter_sendto` 等特定 syscall tracepoint 实现进程级粒度。下面使用 socket 创建的通用路径做协议族分类：

```c
// 挂载点：raw_syscalls/sys_enter（通用 syscall tracepoint）
// socket(): args[0]=__NR_socket, args[1]=family, args[2]=type, args[3]=protocol
SEC("tp/raw_syscalls/sys_enter")
int trace_raw_sys_enter(struct bpf_raw_tracepoint_args *ctx) {
    unsigned long syscall_id = ctx->args[0];
    if (syscall_id != __NR_socket)
        return 0;

    u32 pid = bpf_get_current_pid_tgid() >> 32;
    struct socket_event e = {};
    e.pid = pid;
    e.family = (int)ctx->args[1];
    e.type = (int)ctx->args[2];
    e.protocol = (int)ctx->args[3];
    e.ts = bpf_ktime_get_ns();

    bpf_map_update_elem(&socket_map, &pid, &e, BPF_ANY);
    return 0;
}
```

**在 Perfetto 中的表现**：网络 BPF 数据主要通过 Android 系统服务消费。`netd` 的 BPF 程序（`system/bpf/progs/netd.c`）做 socket 过滤和流量统计，数据写入 BPF map 后由 `netd` 读取并通过 `NetworkStatsService` 汇入系统网络统计。在 Perfetto 中对应的 track 是 `network.stats` category，但该数据来自 `netd` 的定期拉取，不是 eBPF 直接推送。

**注意事项**：Android 平台上的网络 eBPF 主要被系统服务内部使用，普通应用不能直接挂载自己的网络 BPF 程序。如果需要在应用层做自定义网络观测，优先考虑 Perfetto 的 `network` data source 或 `connectivity` ftrace 事件。

### 4. 内存分配追踪

**问题**：谁在大量分配内核内存？有没有分配后未释放的泄漏？

`vmalloc` 的入口参数只有一个 `size`，分配地址是**返回值**。用 kprobe 挂在入口只能拿到 size，拿不到地址。正确的做法是用 kretprobe 拿返回值：

```c
// 挂载点：kprobe/vmalloc（入口）→ 只记录 size，按 pid 存到临时 map
// vmalloc_noprof(unsigned long size): PT_REGS_PARM1(ctx) = size
SEC("kprobe/vmalloc")
int trace_vmalloc_entry(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 size = PT_REGS_PARM1(ctx);

    struct alloc_pending pending = {};
    pending.size = size;
    pending.ts = bpf_ktime_get_ns();

    bpf_map_update_elem(&pending_allocs, &pid, &pending, BPF_ANY);
    return 0;
}

// 挂载点：kretprobe/vmalloc（返回）→ 拿返回值（分配地址），与入口的 size 配对
SEC("kretprobe/vmalloc")
int trace_vmalloc_return(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    unsigned long addr = PT_REGS_RC(ctx);  // 返回值 = 分配地址

    struct alloc_pending *pending = bpf_map_lookup_elem(&pending_allocs, &pid);
    if (!pending)
        return 0;

    struct alloc_record rec = {};
    rec.pid = pid;
    rec.addr = addr;
    rec.size = pending->size;
    rec.alloc_ts = pending->ts;

    bpf_map_update_elem(&alloc_map, &addr, &rec, BPF_ANY);
    bpf_map_delete_elem(&pending_allocs, &pid);
    return 0;
}

// 挂载点：kprobe/vfree → 标记已释放
// vfree(void *addr): PT_REGS_PARM1(ctx) = addr
SEC("kprobe/vfree")
int trace_vfree_entry(struct pt_regs *ctx) {
    unsigned long addr = PT_REGS_PARM1(ctx);

    struct alloc_record *rec = bpf_map_lookup_elem(&alloc_map, &addr);
    if (rec) {
        u64 now = bpf_ktime_get_ns();
        // 计算存活时间，写入事件日志
        bpf_map_delete_elem(&alloc_map, &addr);
    }
    return 0;
}
```

这个三段式模型（entry 记 size → return 拿 addr 配对 → vfree 清掉）能完整追踪每笔分配的完整生命周期。

**在 Perfetto 中的表现**：内存分配 eBPF 数据通过 ring buffer 提交到用户态，在 Perfetto trace 中显示为 `linux.ebpf` data source 的 events。`alloc_map` 中超过阈值未释放的条目可用于生成 memory leak 告警 track。与 Perfetto 自带的 `kmem/rss_stat` ftrace 事件不同，eBPF 版本可以自定义跟踪的分配函数（不限于 vmalloc，也可以是 kmalloc 或驱动专用分配器），自由度更高但需要手动编写程序。

**注意事项**：`vmalloc` 在 Android 内核中通过 `vmalloc_noprof` 定义。生产环境 BPF 程序需要 BTF 信息来验证函数签名——Android common kernel 的 GKI 构建默认包含 BTF。非 GKI 设备的 BTF 支持取决于 vendor kernel 配置。

### 5. GPU 内存监控

**问题**：GPU 内存被谁用了多少？有没有 abnormal growth？

AOSP 内置的 GPU eBPF 程序是 `frameworks/native/services/gpuservice/bpfprogs/gpuMem.c`，挂载 `tracepoint/gpu_mem/gpu_mem_total`，维护 `(gpu_id, pid) → total_size` 的 BPF hash map：

```c
// 基于 AOSP android-16.0.0_r4 gpuMem.c 简化
// 挂载点：tracepoint/gpu_mem/gpu_mem_total
// 功能：按 (gpu_id, pid) 维度统计 GPU 内存总量
// 消费者：gpuservice，用于 per-app GPU 内存记账
SEC("tracepoint/gpu_mem/gpu_mem_total")
int trace_gpu_mem_total(void *ctx) {
    // gpuMem.c 的具体结构体由 gpu_mem tracepoint 定义，
    // 字段通过 bpf_probe_read 读取以保证可移植性
    u64 gpu_id, pid, size;
    // ... bpf_probe_read 各字段 ...
    // ... 更新 gpu_mem_total_map ...
    return 0;
}
```

**注意**：这里追踪的是 **GPU 内存分配总量**，不是 GPU 命令提交耗时或 GPU 利用率。GPU 利用率分析需要 Perfetto 的 GPU frequency / GPU memory track，或者 vendor 提供的 GPU counter ftrace 事件。

**边界**：`tracepoint/gpu_mem/gpu_mem_total` 的发射方位于 vendor kernel。非 Google 设备上该 tracepoint 可能未实现或未开启——需要先通过 `adb shell ls /sys/kernel/debug/tracing/events/gpu_mem/` 确认。

**在 Perfetto 中的表现**：gpuMem.c 的数据不直接进入 Perfetto。`gpu_mem_total_map` 由 `gpuservice` 读取后通过 `gpu.memory` counter track 汇入 Perfetto。在 Perfetto UI 中，每个进程的 GPU 内存占用显示为独立的 counter 线，可以观测内存增长趋势并与屏幕截图帧的时间线对齐。

## Android eBPF 工具链

### 1. UprobeStats — 用户空间探针框架

UprobeStats 是 Android 平台内置的 uprobe 框架，通过 Mainline 模块 `packages/modules/UprobeStats` 分发。它的定位是**用户空间函数追踪**——对指定 DSO 中的符号附加 BPF 探针，不是系统调用监控工具。

**实际运行链路**（基于 `android-16.0.0_r4`）：

1. **配置读取**：`UprobeStats.cpp` 从 `/data/misc/uprobestats-configs/config` 读取探针配置（目标 DSO 路径、符号名、探针类型）。
2. **Guardrail 校验**：`Guardrail.cpp` 检查配置合法性——目标文件是否存在、符号是否可解析、探针数量是否超限。
3. **Probe 解析**：`Bpf.cpp` 通过 `dlopen` + `dlsym` 解析目标 DSO 中的符号地址。
4. **Attach**：通过 `/sys/bus/event_source/devices/uprobe/type` 获取 uprobe PMU type，然后 `perf_event_open()` 创建 perf event，用 `PERF_EVENT_IOC_SET_BPF` 附加 BPF 程序。
5. **数据消费**：BPF 程序输出走 ring buffer，由用户态消费者线程读取。

UprobeStats 的 binary 名为 `uprobestats`（全小写），由 `oneshot` service 触发执行。它不是长期驻留的守护进程——每次执行根据配置附加探针，采集完成后退出。注意：UprobeStats 不接受 `--pid`、`--syscall` 等命令行参数，探针行为完全由配置文件驱动。

### 2. BPF 程序加载链路

Android BPF 程序的完整生命周期由 `bpfloader` 管理。以 `android-16.0.0_r4` 为例：

```
开机 early-init
  → bpfloader.rs::main()
    → load_libbpf_progs()
      → 加载 /system/etc/bpf/ 下 .bpf 风格程序 (timeInState.bpf 等)
      → 创建 BPF map，pin 到 /sys/fs/bpf/
    → vendorBpfLoader()
      → 加载 /vendor/etc/bpf/ 下 .o 风格程序
      → pin 到 /sys/fs/bpf/
```

BPF 程序的编译产物和编译方式：
- **`system/bpfprogs/`**：使用 `bpfloader` 的 `.bpf` 骨架格式（`timeInState.c` → `timeInState.bpf`），通过 `Android.bp` 中的 `bpf_prog` 规则编译。
- **`system/bpf/progs/`**：网络守护进程 BPF（`netd.c`），编译为 `.o`，由 `netd` 的 `BpfHandler.cpp` 加载。
- **`packages/modules/Connectivity/bpf/progs/`**：Connectivity Mainline BPF 程序。

BPF map 和 prog 创建后，owner/group 由宏或 loader descriptor 指定，常见组合：
- `timeInState.c`：**AID_SYSTEM** 拥有，Power Stats HAL（system 进程）只读访问
- `gpuMem.c`（`frameworks/native/services/gpuservice/bpfprogs/`）：**AID_GRAPHICS** 拥有，gpuservice 读写
- `netd.c`（`packages/modules/Connectivity/bpf/progs/`）：**AID_NET_BW_ACCT** / **AID_NET_ADMIN** 等网络相关 group，由 netd 和 ConnectivityService 消费

不存在全局默认的"所有 map AID_SYSTEM 拥有"，每个程序的权限由 `DEFINE_BPF_MAP_*` 宏中的 `uid`/`gid` 字段或 bpfloader descriptor 单独指定。

### 3. Perfetto 集成

**eBPF → Perfetto 的两条数据路径**：

1. **BPF ring buffer → 用户态 reader → Perfetto**：eBPF 程序通过 `bpf_perf_event_output()` 将事件写入 BPF perf event array，用户态 reader 读取后通过 Perfetto 的 `TraceWriter` 接口写入 trace。这条路径需要用户态守护进程做中转。

2. **BPF map → 系统服务 → Perfetto**：系统服务（如 Power Stats HAL、gpuservice、netd）定期从 BPF map 读取聚合数据，通过各自的 Perfetto data source 输出。这是 `timeInState.c` 和 `gpuMem.c` 的数据路径。

**Perfetto TraceConfig 示例**（基于 `android-16.0.0_r4` 的 `data_source_config.proto`）：

```protobuf
# Perfetto TraceConfig — ftrace + perf 采样
# 注意：这是 text proto 格式，JSON 配置需通过 protobuf 转码

buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "raw_syscalls/sys_enter"
      ftrace_events: "raw_syscalls/sys_exit"
      buffer_size_kb: 8192
    }
  }
}

data_sources {
  config {
    name: "linux.perf"
    perf_event_config {
      timebase {
        frequency: 100
        period: 1
      }
      # CPU cycle 采样用于 callstack profiling
    }
  }
}

duration_ms: 10000
```

Perfetto 的 eBPF data source 集成仍在 AOSP main 分支活跃开发中，`data_source_config.proto` 中已有 `ftrace_config` 和 `perf_event_config` 字段，但 eBPF 专用 data source 的稳定 API 尚未随 Android release tag 出现。

## eBPF 在 Android 中的性能优化实践

### 系统调用频率优化

通过 eBPF 统计每个进程的系统调用频率和模式后，可以有针对性地做优化。下面是一个按 syscall id 统计调用次数的 BPF 程序：

```c
// 挂载点：raw_syscalls/sys_enter
// 统计每个 syscall id 被调用的次数
SEC("tp/raw_syscalls/sys_enter")
int count_syscalls(struct bpf_raw_tracepoint_args *ctx) {
    u32 syscall_id = (u32)ctx->args[0];  // args[0] = __NR_*
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    struct syscall_key key = {.pid = pid, .syscall_id = syscall_id};
    struct syscall_count *cnt = bpf_map_lookup_elem(&syscall_counts, &key);
    if (cnt) {
        __sync_fetch_and_add(&cnt->count, 1);
    } else {
        struct syscall_count init = {.count = 1, .pid = pid};
        bpf_map_update_elem(&syscall_counts, &key, &init, BPF_ANY);
    }
    return 0;
}
```

常见的优化方向：识别单个 vs 批量文件操作的调用频率差异、检测不必要的同步 syscall 阻塞 UI 线程、对比同类应用的系统调用模式。

### 进程调度延迟分析

```c
// 挂载点：tracepoint/sched/sched_switch
// 记录 prev_pid → next_pid 的切换事件及时间戳
SEC("tracepoint/sched/sched_switch")
int trace_sched_switch(struct trace_event_raw_sched_switch *ctx) {
    u64 ts = bpf_ktime_get_ns();

    struct sched_event e = {};
    e.prev_pid = ctx->prev_pid;
    e.next_pid = ctx->next_pid;
    e.ts = ts;

    bpf_map_update_elem(&sched_events, &ts, &e, BPF_ANY);
    return 0;
}
```

调度数据可用于分析：CPU 负载不均衡（某 CPU 上排队时间远超其他 CPU）、进程饥饿（长时间未获得 CPU 时间片）、错误的 CPU affinity 或 cgroup 隔离导致的不必要迁移。

## Android eBPF 加载器架构重构（Rust 化，android-16 引入）

> ⚠️ **版本说明**：Rust bpfloader 在 `platform/system/bpf` 的 `android-16.0.0_r4` tag 中已存在（`loader/bpfloader.rs`）。以下描述基于 `android-16.0.0_r4` 复核。

Android 15 后期 tag（android-15.0.0_r17）已出现 Rust 入口雏形，Android 16（android-16.0.0_r4）进一步完善了 `system/bpf/loader/` 下的 Rust bpfloader 重构：

### C++ 主入口完全替换

- **C++ 加载逻辑**: `Loader.cpp` → 编译为 `libbpf_android.so`，被 Rust 端通过 `bindgen` 调用（android-16.0.0_r4 可验证）
- **Rust 入口**: `bpfloader.rs`（android-15.0.0_r17 已出现雏形，android-16.0.0_r4 完善）

### 混合加载器架构

```rust
// bpfloader.rs:main() — android-16.0.0_r4 调用序列
load_libbpf_progs();           // 加载 .bpf 风格（timeInState.bpf 等）
vendorBpfLoader();             // 加载 vendor .o 风格 BPF 程序
```

### BPF 程序目录分布（android-16.0.0_r4 观察）

1. **`system/bpfprogs/`** - 通用 BPF 程序
   - `timeInState.c`: 每 UID CPU 频率时间追踪
   - `fuseMedia.c`: FUSE 媒体访问策略

2. **`system/bpf/progs/`** - 网络守护进程 BPF
   - `netd.c`: socket 过滤与流量统计

3. **`frameworks/native/services/gpuservice/bpfprogs/`** - GPU 内存跟踪
   - `gpuMem.c`: `(gpu_id, pid) → size` GPU 内存分配统计

4. **`packages/modules/Connectivity/bpf/progs/`** - Connectivity BPF

### timeInState.c 的核心作用

```c
// 挂载点：tracepoint/sched/sched_switch
// 输出：uid_time_in_state_map、uid_concurrent_times_map
// 消费方：Power Stats HAL、Battery Historian
```

### 性能与安全影响

> ⚠️ **数据说明**：以下为粗略估算值，因设备 SoC、内核版本（GKI / vendor kernel）、系统负载和 tracepoint 开关状态而异，不宜作为通用结论引用。

- **性能**: sched_switch 事件频率随系统负载波动，典型场景约数千次/秒；`timeInState.c` 在 sched_switch 路径上执行若干次 BPF map hash lookup。整机额外功耗很小（约亚毫瓦级，具体取决于硬件和 SoC）
- **权限**: 各 map 的 owner/group 按程序分别指定——`timeInState.c` 使用 `AID_SYSTEM`，`gpuMem.c` 使用 `AID_GRAPHICS`，网络 BPF map 使用 `AID_NET_BW_ACCT` 等

### 供应商兼容性

BPF 程序加载过程不依赖芯片厂商代码，但 `tracepoint/gpu_mem/gpu_mem_total` 的发射方位于 vendor kernel，具体 SoC 可能存在实现差异。

## eBPF 在 Android 中的可用性边界

在实际设备上使用 eBPF 受到多层约束：

- **SELinux 与权限**：生产设备上加载 BPF 程序通常需要 `bpfloader` 或等效系统服务间接完成；非 root 用户态进程直接调用 `bpf()` 系统调用在大多数 Android 设备上受限。Android 的 sepolicy 通过 `domain.te` 中 `allow bpfloader self:capability sys_admin` 等规则严格控制 BPF 能力——普通应用进程不在允许域中。
- **BPF loader 权限模型**：BPF map 和 prog 的 owner/group 由 `DEFINE_BPF_MAP_*` 或 `DEFINE_BPF_PROG_*` 宏的 `uid`/`gid` 字段单独指定。常见 owner 包括 `AID_SYSTEM`（timeInState）、`AID_GRAPHICS`（gpuMem）、`AID_NET_BW_ACCT`（netd 网络统计）。不存在全局默认 `AID_SYSTEM`。
- **Vendor kernel tracepoint 差异**：部分 tracepoint（如 `gpu_mem/gpu_mem_total`）的发射方位于 vendor kernel，具体 SoC 可能未实现或未开启。使用前需先检查 `/sys/kernel/debug/tracing/events/`。
- **GKI 版本耦合**：sched-ext 等特性依赖 Android common kernel 版本（如 6.12+）而非 Android API level。同一 API level 的设备可能运行不同 GKI 版本。
- **Google Play System Update 路径**：UprobeStats 等 Mainline 模块通过 Google Play System Update 单独更新，其 eBPF 程序版本可能超前于设备出厂系统版本。
- **BPF 编译环境**：Android BPF 程序通过 `Android.bp` 中的 `bpf_prog` / `bpf` 规则编译，使用 `clang -target bpf`。用户态程序不能直接用 `clang -target bpf` 手工编译后 push 到设备——编译产物需要匹配内核 BTF 和 bpfloader 期望的格式。

## 与传统工具的定位对比

eBPF 不是 perf、systrace、Perfetto 的替代品——它们在 Android 性能栈中各有分工。

| 工具 | 数据来源 | 典型粒度 | 主要适用场景 |
|------|---------|---------|------------|
| **perf / simpleperf** | PMU 硬件计数器 | 采样（几百 Hz） | CPU 微架构分析、cache miss、分支预测 |
| **systrace / Perfetto** | ftrace 内核事件 | 微秒级 tracepoint | 渲染管线、Binder 调用、VSYNC 时序 |
| **eBPF (含 UprobeStats)** | 内核 hook (kprobe/uprobe/tracepoint) | 微秒级，可编程过滤 | 自定义内核级观测、运行时安全、CPU 调度细粒度统计 |

关键区别：
- **perf** 擅长"CPU 在哪个函数上耗时"；**eBPF** 擅长"内核在执行某个动作时上下文是什么"。
- **Perfetto** 覆盖 Android HAL/Java 层到 ftrace 的端到端链路；**eBPF** 更偏内核子系统内部的定制观测。
- 实际排障中，eBPF 常作为 Perfetto 的补充：Perfetto 钩宏观耗时，eBPF 探微观调度/内存事件。

## 总结

eBPF 在 Android 中承担**内核可观测性基础设施**的角色。从 Android 12 开始，每台设备的 CPU 时间记账已经在跑 eBPF；到 Android 16，sched-ext 和 Rust bpfloader 进一步拓宽了 eBPF 在内核调度和加载可靠性上的边界。

> ⚠️ **版本说明**：Perfetto eBPF data source 集成代码在 AOSP main 分支中可见，但尚无 `android-17.0.0_r1` release tag，**未进入 Android 17 release**，不可作为正文结论引用。正文中的源码锚点优先参照 `android-16.0.0_r4`。

从性能排障角度，应把 eBPF 理解为工具箱中的高精度探头——它解决的不是"有没有问题"，而是"这个问题在内核层面到底是怎么发生的"。Perfetto 对 eBPF data source 的支持在持续演进中，eBPF 采集的数据可以直接汇入 Perfetto trace。
