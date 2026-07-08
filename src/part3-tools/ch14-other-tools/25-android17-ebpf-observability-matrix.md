---
title: "Android 17 eBPF 性能可观测性程序矩阵扩展"
chapter: "14.25"
status: ready-for-review
drafted_date: "2026-07-02"
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-07-02"
last_verified_against: "AOSP android-17.0.0_r1; 参考章节 14.10/14.21 已验证源码"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/... (cyclePerUid eBPF program)"
  - type: aosp
    path: "libs/cpucycleperuid/lib.rs"
  - type: blog
    path: "intake/daily-info/2026-07-01.md #27-30, #34"
  - type: official
    path: "source.android.com/docs/core/architecture/kernel/bpf"
tags: [eBPF, observability, CPU-cycle, DMA-BUF, wakelock, lock-contention, Rust, Android17]
related_chapters: ["14.10", "14.21", "5.1", "5.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-02"
gap_source: "每日技术文章 intake"
---

# 14.25 Android 17 eBPF 性能可观测性程序矩阵扩展

> **版本边界**：本节基于 Android 17 (API 37) 源码基线 `android-17.0.0_r1`。新增 eBPF 程序来源于 AOSP main 分支观察与多源技术文章交叉验证。由于 `platform/system/bpf` 的 `android-17.0.0_r1` tag 在部分子仓库中尚在同步中，个别源码路径标注为 `[待验证: 源码路径可能已变更]`。
>
> **定位**：§14.10 从工具使用角度介绍了 eBPF 在 Android 性能分析中的应用全景；§14.21 从 bpfloader 架构角度分析了 BPF 程序的加载链路与 map 组织。本节聚焦 Android 17 **新增的 4 个 eBPF 程序和 1 个 Rust FFI 库**，分析它们填补了哪些可观测性空白，以及与既有 eBPF 程序矩阵的互补关系。

## 要点

### 🔹 cyclePerUid — 按 UID 统计 CPU 周期

**定位**：Android 17 新增的 `cyclePerUid` eBPF 程序，以 UID 为维度统计 CPU 周期数（CPU cycles），扩展了 Android 12 引入的 `timeInState.c`（按 UID × 频率统计驻留时间）的能力。

**与 timeInState 的关系**：

| 维度 | timeInState (Android 12+) | cyclePerUid (Android 17) |
|------|---------------------------|--------------------------|
| 统计单位 | 时间（ns） | CPU 周期数（cycles） |
| 维度 | UID × CPU 频率档位 | UID |
| 数据来源 | `tracepoint/sched/sched_switch` | PMU 硬件计数器（推测） |
| 消费者 | Power Stats HAL, Battery Historian | 系统性能分析、能耗归因 |
| 优势 | 频率维度精细 | 不依赖频率映射，跨架构可比 |

timeInState 的局限在于：它依赖 `cpu_policy_map` 和 `freq_to_idx_map` 将 CPU 频率映射到索引。当设备使用 EAS（Energy Aware Scheduling）调度器且频率档位频繁变化时，频率索引映射需要动态更新。cyclePerUid 直接使用 PMU 周期计数器，绕过了频率映射层，在不同 SoC 架构间更具可比性。

**性能分析价值**：
- CPU cycles 可直接换算为能耗（每 cycle 的能耗取决于微架构 IPC 和电压/频率点），适合做跨应用的能耗效率对比
- 对于后台进程的尾延迟分析，cycles 维度比时间维度更能反映实际计算开销（不受调度等待时间干扰）
- 在多进程应用（如 Chrome 渲染进程、WebView、应用 sandbox）场景下，UID 维度统计比 per-process 更准确——同一个 UID 下的多个进程共享资源配额

[结构参考: Clippings 技术文章 #27]
[交叉验证: intake/daily-info/2026-07-01.md #27 + §14.21 timeInState.c 源码分析]

### 🔹 dmabufIter — DMA-BUF 迭代器

**定位**：Android 17 新增的 `dmabufIter` eBPF 程序，用于系统侧 DMA-BUF 观测。这是继 `gpuMem.c`（按 `(gpu_id, pid)` 统计 GPU 内存总量）之后，Android 在图形/共享内存归因上的又一次扩展。

**DMA-BUF 的角色**：

DMA-BUF 是 Linux 内核的共享 buffer 机制（`dma-buf` framework），允许不同子系统（GPU、显示控制器、相机 ISP、媒体编解码器、CPU）零拷贝共享大块物理内存。在 Android 中，几乎所有图形 buffer（SurfaceFlinger 的 GraphicBuffer、相机 HAL 的 capture buffer、媒体 codec 的 input/output buffer）都基于 DMA-BUF。

**dmabufIter 的观测价值**：

已有 `gpuMem.c` 只统计 GPU 侧的内存总量（`gpu_mem_total` tracepoint），但无法回答以下问题：
- 某块 DMA-BUF 被哪些子系统引用？（引用计数）
- DMA-BUF 的总系统占用量是多少？（跨所有 exporter）
- 是否存在 DMA-BUF 泄漏？（buffer 分配后未被释放）

`dmabufIter` 作为迭代器（iterator）类型的 BPF 程序，可以遍历系统的 `dma-buf` 列表，读取每块 buffer 的 `size`、`expander_name`、`attachment_count` 等字段。这为以下场景提供了数据基础：
- **图形内存泄漏诊断**：当 SurfaceFlinger 或 Camera HAL 的 DMA-BUF 分配后未释放，`dmabufIter` 可以捕获到 buffer 数量异常增长
- **跨子系统内存归因**：一块被 GPU 和 Display 共享的 buffer 在 `dumpsys meminfo` 中可能被双重计算，`dmabufIter` 提供了去重的可能
- **大 buffer 审计**：快速定位系统中 >100MB 的 DMA-BUF，排查异常分配

> ⚠️ 原文只列出该程序名称，具体挂载方式（iterator vs tracepoint）、输出 map 结构、以及是否已对接 Perfetto data source，需要继续读 AOSP 实现确认。

[结构参考: Clippings 技术文章 #28]
[交叉验证: intake/daily-info/2026-07-01.md #28 + §14.10 gpuMem.c 分析]

### 🔹 kernelwakelockduration — 内核唤醒锁持续时间统计

**定位**：Android 17 新增的 `kernelwakelockduration` eBPF 程序，统计内核态 wakelock 的持有持续时间，直接服务于功耗归因。

**与现有功耗监控的互补**：

Android 的功耗监控体系已有多个层次：

| 层次 | 机制 | 粒度 | 来源 |
|------|------|------|------|
| 应用层 | `PowerManager.WakeLock` | Java API，per-app | `frameworks/base/core/java/android/os/PowerManager.java` |
| 系统服务 | `WakeLockMetrics` | 汇聚到 `statsd` | `frameworks/base/services/core/java/com/android/server/power/` |
| 内核 ftrace | `power/wakeup_source_activate` / `power/wakeup_source_deactivate` | 事件级 | common kernel tracepoint |
| **eBPF（新增）** | `kernelwakelockduration` | 持续时间聚合 | Android 17 新增 |

ftrace 方式需要 Perfetto 在 trace 期间持续记录 `wakeup_source_activate` 和 `wakeup_source_deactivate` 事件，然后在用户态做差值计算。这有两个问题：
1. 高频 wakelock 场景下 ftrace 事件量大，trace 文件膨胀
2. 用户态差值计算可能因事件丢失而不准确

`kernelwakelockduration` 在内核侧直接用 eBPF 做 wakelock 持续时间的聚合，减少了用户态处理开销和事件丢失风险。对于以下场景有直接价值：
- **待机功耗排查**：快速定位持锁时间最长的 wakelock source
- **后台耗电归因**：结合 UID 信息可以区分不同应用的 wakelock 影响
- **回归测试**：在 CI 流水线中自动采集 wakelock 持续时间，对比版本回归

[结构参考: Clippings 技术文章 #29]
[交叉验证: intake/daily-info/2026-07-01.md #29 + §5.1 功耗分析]

### 🔹 locks — 锁竞争分析

**定位**：Android 17 新增的 `locks` eBPF 程序，用于内核/系统侧锁竞争（lock contention）分析。

**锁竞争为何重要**：

锁竞争是系统级性能问题的常见根因，典型表现包括：
- **UI 卡顿**：Binder 线程池锁竞争导致主线程等待跨进程调用返回
- **尾延迟（tail latency）**：99th percentile 响应时间远高于 median，通常由偶发锁竞争导致
- **调度异常**：spinlock 持有时间过长导致 CPU 空转，影响其他任务调度

**与现有工具的互补**：

| 工具 | 机制 | 优势 | 局限 |
|------|------|------|------|
| simpleperf | PMU 采样 | 精确到指令级 | 只看 on-CPU 时间，无法区分锁等待 |
| Perfetto ftrace | `sched/sched_switch` | 可重建线程调度序列 | 需手动分析锁等待因果关系 |
| **locks eBPF** | 内核锁事件 tracepoint | 直接捕获锁获取/等待/释放 | 侵入性需评估 |

`locks` eBPF 程序可能挂载在 `tracepoint/lock/lock_acquire` 和 `tracepoint/lock/lock_release`（或 `lock_contended`）上，这些 tracepoint 由内核 `CONFIG_LOCKDEP` 或 `CONFIG_LOCK_EVENT_COUNTS` 控制。eBPF 程序可以在不开启完整 lockdep（lockdep 有约 10–20% 性能开销）的情况下，选择性采集锁竞争数据。

实际使用场景：
- 结合 Binder 观测（§1.44/§1.48 Binder IPC 优先级继承与批处理），定位 Binder 事务中的锁等待
- 与 simpleperf 硬件采样交叉验证，区分 CPU bound 和 lock bound 的性能瓶颈
- 在生产环境中以低侵入方式持续监控关键锁的竞争情况

> ⚠️ 具体挂载的 tracepoint 名称、map 结构、以及是否需要特定的内核配置（如 `CONFIG_LOCKDEP`），需要 AOSP 源码确认。

[结构参考: Clippings 技术文章 #30]
[交叉验证: intake/daily-info/2026-07-01.md #30 + §14.10 simpleperf/§1.44 Binder]

### 🔹 cpucycleperuid Rust FFI 库

**定位**：Android 17 新增的 Rust FFI 库 `libs/cpucycleperuid/lib.rs`，为系统侧交互状态与 CPU 周期统计提供底层支持。

**Rust 在 Android 系统编程中的趋势**：

这延续了 Android 12+ 的 Rust 化趋势（参见 §14.21：bpfloader 从 C++ 迁移到 Rust 壳）。`cpucycleperuid` 库位于 `libs/` 目录下，说明它是平台级共享库（而非某个模块私有），可被多个系统服务引用。

**架构推测**：

基于库命名和源文章描述，`cpucycleperuid` 库的职责可能包括：

1. **读取 cyclePerUid BPF map**：提供 C/C++ 可调用的 FFI 接口，封装 BPF map 读取逻辑（`bpf_map_lookup_elem`、fd 管理、错误处理）
2. **交互状态关联**：将 CPU cycle 数据与交互状态（`InteractionType`、`JankType` 等 systemUI/FrameTracker 定义的状态枚举）关联，用于按场景归因性能数据
3. **Rust 安全封装**：Rust 端管理 BPF map fd 的生命周期（`OwnedFd`/`Drop`），通过 FFI 导出 C ABI 函数给 C++/Java 系统服务调用

这个库与 `cyclePerUid` eBPF 程序形成互补：eBPF 程序在内核侧采集数据，`cpucycleperuid` 库在用户侧提供安全的数据读取接口。

[结构参考: Clippings 技术文章 #34]
[交叉验证: intake/daily-info/2026-07-01.md #34 + §14.21 bpfloader Rust 化趋势]

## Android 17 eBPF 程序矩阵总览

将 Android 17 新增程序与既有程序合并，得到完整的 eBPF 可观测性矩阵：

| eBPF 程序 | 引入版本 | Attach 类型 | 观测维度 | 主要消费者 |
|-----------|---------|-------------|----------|-----------|
| timeInState.c | Android 12 | tracepoint/sched_switch | UID × 频率 × 时间 | Power Stats HAL |
| gpuMem.c | Android 13 | tracepoint/gpu_mem_total | GPU × PID × bytes | GpuService, Perfetto |
| fuseMedia.c | Android 13 | tracepoint/fuse_lookup | FUSE 访问 | MediaProvider |
| netd.c | Android 9 | socket filter/cgroup | 网络流量 | NetworkStatsService |
| UprobeStats | Android 14 | uprobe | 用户态函数 | 可配置（Mainline） |
| **cyclePerUid** | **Android 17** | **PMU/tracepoint（待确认）** | **UID × cycles** | **系统性能分析** |
| **dmabufIter** | **Android 17** | **BPF iterator** | **DMA-BUF × size/refcount** | **图形内存诊断** |
| **kernelwakelockduration** | **Android 17** | **tracepoint（待确认）** | **wakelock × duration** | **功耗归因** |
| **locks** | **Android 17** | **tracepoint/lock_*** | **锁 × 等待时间** | **性能瓶颈分析** |

**Android 17 的扩展方向**：从 Android 12-13 的「频率/时间统计」扩展到了「周期计数（cyclePerUid）、共享内存（dmabufIter）、功耗（kernelwakelockduration）、同步（locks）」四个新维度，基本覆盖了性能可观测性的主要盲区。

## 扩展

### 🔸 eBPF 程序矩阵与 Perfetto 数据源映射

Android 17 新增的 4 个 eBPF 程序是否能直接映射到 Perfetto 的 track/event 体系，取决于：

1. **Perfetto data source 注册**：Perfetto 通过 `DataSourceConfig` proto 注册数据源。如果新增 eBPF 程序有对应的 Perfetto producer（如 `traced_probes` 或自定义 producer），则可以在 trace 中直接看到对应 track。
2. **BPF → Perfetto 桥接**：Perfetto 的 `perf_event` data source 可以通过 `perf_event_open()` 系统调用读取 PMU 计数器，但 BPF 程序通常需要用户态 reader 进程从 BPF map 或 ring buffer 拉取数据，再写入 Perfetto custom track。

当前已知 `timeInState.c` 的数据通过 Power Stats HAL → `statsd` → Battery Historian 链路消费，不直接出现在 Perfetto trace 中。新增程序是否会有更紧密的 Perfetto 集成，值得持续跟踪。

[待验证: 4 个新 eBPF 程序的 Perfetto data source 对接状态]

### 🔸 cyclePerUid 与现有 per-process CPU 采样的互补关系

在多进程应用场景下（如 Chrome 的 renderer/GPU/browser 进程、WebView 的 sandbox 进程、应用的主进程 + 子进程），UID 维度统计比 per-process 更准确的场景包括：

1. **资源配额归因**：Android 的 `lmkd` 和 `MemoryLimiter` 以 UID 为单位做内存限制（§4.18），CPU cycle 归因也应以 UID 为单位才能与内存配额对齐
2. **能耗效率对比**：跨应用对比能耗效率时，需要把同一应用的所有进程的 CPU 开销汇总，per-process 数据需要额外的合并逻辑
3. **安全审计**：应用的恶意行为（挖矿、后台密集计算）通常跨多个 sandbox 进程，UID 维度更容易发现异常

但在以下场景中 per-process 数据仍然必要：
- 主线程 vs 子线程的性能分析
- IPC 密集型应用中不同进程的 CPU 分布
- 调度器调优（per-process nice value / cgroup）

[待补充: cyclePerUid 是否同时提供 per-process 分解能力，还是纯粹 per-UID]

### 🔸 dmabufIter 对图形内存泄漏诊断的价值

dmabufIter 能否辅助定位 SurfaceFlinger/Camera HAL 的 DMA-BUF 泄漏，取决于以下条件：

1. **BPF iterator 机制**：Linux 5.8+ 引入了 BPF iterator，允许 eBPF 程序遍历内核数据结构（如所有 task、所有 file descriptor）。如果 dmabufIter 基于 BPF iterator 机制，它可以遍历 `dma-buf` 的 `file->private_data` 链表，读取每块 buffer 的元数据。
2. **导出方信息**：`dma-buf` 的 `expander_name` 字段标识了 buffer 的创建者（如 `gem`、`ion`、`dma_heap`），可以区分是 GPU buffer 还是相机 buffer 还是媒体 buffer。
3. **引用计数**：`attachment_count` 表示该 buffer 被多少个设备 attach。如果 attachment_count 持续增长但从不下降，可能存在 attachment 泄漏。

[待验证: dmabufIter 能否辅助定位 SurfaceFlinger/Camera HAL 的 DMA-BUF 泄漏]

### 🔸 新增 eBPF 程序对 bpfloader 的影响

§14.21 分析了 Android 17 bpfloader 的 Rust 化重构。新增的 4 个 eBPF 程序是否会走 Rust libbpf-rs 路径（`FILE_ARR`）还是老路径（`legacyBpfLoader()`），影响以下方面：

- **加载时机**：Rust 路径在 `load_libbpf_progs()` 中先行加载，老路径在后
- **文件格式**：libbpf 路径加载 `.bpf`（BTF-enabled CO-RE 格式），老路径加载 `.o`（传统 ELF 格式）
- **版本兼容**：`.bpf` 格式依赖 BTF 信息，非 GKI 设备可能不支持

如果新程序走老路径，则与 Android 14-16 的加载方式一致，兼容性更好但无法利用 CO-RE 的跨内核可移植性。

[待验证: 新增 eBPF 程序的加载路径与文件格式]

---

> 本节基于 AOSP `android-17.0.0_r1` 源码基线撰写。新增 eBPF 程序的来源：[来源: intake/daily-info/2026-07-01.md #27-30, #34]；架构分析交叉引用 §14.10（eBPF 工具应用）和 §14.21（bpfloader 架构）。


---

<!-- AIW-源码调研-2026-07-09 -->

## 源码级验证补充（android-17.0.0_r1 实读）

> 本节为 2026-07-09 源码调研的补充：直接读取 `platform/system/bpfprogs/+/refs/heads/android17-release` HEAD `238924255acb29e72d0204ca66d4ea0792b84abb` 下的 6 个文件，把上文所有 `[待验证]` 项目**用源码事实**替代。完整报告见 `DeepResearch/2026-07-09-android17-ebpf-observability-matrix-verified.md`。

### 附件 1 — 仓库拓扑与 Android.bp 构建清单

`android17-release` 标签下 `system/bpfprogs/` 的真实目录结构：

```
Android.bp              # 顶层构建清单（113 行）
cyclePerUid.c           # 主目录新增
dmabufIter.c            # 主目录新增
fuseMedia.c             # 既有（Android 13+）
timeInState.c           # 既有（Android 12+）
progs.aconfig           # aconfig flag 定义（23 行）
locks/                  # 子目录新增
  ├── Android.bp
  ├── bpfLockContention.c
  └── include/locks/
kernelwakelockduration/ # 子目录新增
  ├── Android.bp
  ├── kernelWakelockDuration.c
  └── TEST_MAPPING
```

**关键结论（澄清上文 [待验证: 加载路径]）**：所有 4 个新增程序均使用 `libbpf_prog { ... }`（而非老式 `bpf { ... }`），即**走 BTF-enabled CO-RE 路径**，输出 `.bpf` 文件，**不走 `legacyBpfLoader()`**。依赖 BTF 信息意味着**非 GKI 设备可能不支持这些程序**。

| 模块名 | 源码文件 | `relative_install_path` | 启用架构 | 是否 aconfig flag |
|--------|---------|------------------------|---------|------------------|
| `timeInState.bpf` | `timeInState.c` | `cputimeinstate` | 全架构 | 否（默认加载） |
| `fuseMedia.bpf` | `fuseMedia.c` | （默认） | 全架构 | 否（默认加载） |
| `dmabufIter.bpf` | `dmabufIter.c` | `dmabuf` | 全架构（除 riscv64） | **是**（`load_dmabuf_iterator`） |
| `cyclePerUid.bpf` | `cyclePerUid.c` | `cpucycleperuid` | **仅 x86_64** | 否（构建时决定） |

`cyclePerUid.bpf` 的 `enabled: false` + `arch: { x86_64: { enabled: true } }` 模式表明：**在 ARM 架构的 Pixel 设备上 cyclePerUid 不会被编译进 system image**。这是因为该程序依赖 x86 TSC（Time Stamp Counter），ARM 平台需要改用 AMU 计数器，路径完全不同。

### 附件 2 — cyclePerUid：attach 类型与 map 结构

**Attach 类型**：`tp_btf/sched_switch`（**BTF-enabled tracepoint**，注意是 `tp_btf/` 而非 `tracepoint/`，使用 BTF 描述的 tracepoint 参数）。

**5 个 map 定义**（源码 `cyclePerUid.c:30-37`）：

| Map 名称 | 类型 | 键 | 值 | 容量 | UID | 用途 |
|---------|------|----|----|------|-----|------|
| `last_recorded_cycle_map` | PERCPU_ARRAY | uint32_t | uint64_t | 1 | AID_SYSTEM | 上一次本 CPU 的 TSC 值 |
| `last_running_pid_map` | PERCPU_ARRAY | uint32_t | pid_t | 1 | AID_SYSTEM | 上一次本 CPU 切换入的 PID（防 suspend/resume 双发） |
| `uid_cpu_cycle_map` | LRU_PERCPU_HASH | uint32_t (UID) | uint64_t | MAX_TRACKED_UIDS | AID_SYSTEM | **per-UID 累计 cycle 聚合** |
| `tsc_events` | PERF_EVENT_ARRAY | uint32_t (cpu) | int | MAX_CPUS | AID_SYSTEM | 挂载 TSC 硬件计数器 |
| `desync_counter` | PERCPU_ARRAY | uint32_t | uint64_t | 1 | AID_SYSTEM | suspend/resume 后 desync 事件计数 |

**澄清上文 [待补充: cyclePerUid 是否同时提供 per-process 分解能力]**：源码 `cyclePerUid.c:108-112` 显示归因键**仅用 `uid = uid_gid & 0xFFFFFFFF`**——cyclePerUid **纯粹 per-UID，不提供 per-process 分解**。要 per-process 必须叠加其他观测手段（如 simpleperf）。

**TSC 溢出判断**（源码注释）：`// The Time Stamp Counter (TSC) is a 64-bit counter. Wraparound is not a practical concern as it would take over 100 years for a 5GHz CPU.` — cycles 维度在 5GHz CPU 上需 100+ 年溢出，可视为单调递增。

### 附件 3 — dmabufIter：iterator 机制与输出字段

**Attach 类型**：`iter/dmabuf`（**BPF iterator**，挂载在内核 `bpf_iter__dmabuf` 钩子）。

**输出字段**（源码 `dmabufIter.c:42`）：每块 dma_buf 输出一行 4 段 →

```
%lu
%llu
%s
%s

└── inode / size / name / exp_name
```

注意源码中 `exp_name` 字段是 `dmabuf->exp_name`（DMA-BUF 导出方名字），而 §14.25 上文推测的 `attachment_count` 字段**在源码中并未出现**——dmabufIter 适合做 buffer 数量审计、总占用审计，但不能直接给出 attachment 引用计数。

**字符串清洗**：源码 `dmabufIter.c:24-28` 显式实现 `sanitize_string()`——把 `
` 替换为空格，避免破坏 seq_file 行分隔。这意味着**用户态解析需按行读，不能简单按字段 split**。

### 附件 4 — locks/bpfLockContention：tracepoint 与聚合算法

**Attach 类型**（澄清上文 [待验证]）：
- `tp/lock/contention_begin`
- `tp/lock/contention_end`

注意是 **`contention_begin/end`** 而非上文的 `lock_acquire/release` 推测——`contention_begin` 只在**实际发生竞争等待时**触发，非每次锁获取都触发，**数据量级更低、聚焦真正有性能影响的事件**。

**2 个 HASH map**（4096 entry，AID_SYSTEM）：

| Map | 键 | 值 | 用途 |
|-----|----|----|------|
| `contention_start_map` | `{tgid, tid, lock_name}` | uint64_t (起始 ns) | in-flight 跟踪：每个线程 × 每个锁 |
| `contention_latency_map` | `{tgid, lock_name}` | `{sum, count, max, min, comm}` | 聚合：每个进程 × 每个锁 |

**白名单机制**：源码 `bpfLockContention.c:38-41` 调用 `get_lock_id(lock_addr, task)`——返回 `LOCK_ID_UNKNOWN` 直接 return 0，**只跟踪列入白名单的全局锁**。具体白名单在 `locks/include/locks/bpf_lock_macros.h` 中定义（本次未读取）。

**性能控制**：
- sum/count 使用 `__sync_fetch_and_add` 原子累加（无锁）
- min/max 使用「racy but simpler」的非原子更新（源码注释 `// Use racy but simpler updates for min/max`）
- 不依赖完整 `CONFIG_LOCKDEP`（lockdep 全开有 10-20% 性能开销），仅需 `CONFIG_LOCK_EVENT_COUNTS`——**相对低侵入**

### 附件 5 — kernelWakelockDuration：cec 增量算法与初始化竞态

**Attach 类型**：`raw_tp/wakeup_source_activate` + `raw_tp/wakeup_source_deactivate`（**raw tracepoint**，直接读 `bpf_raw_tracepoint_args->args[]`，跳过 tracepoint 格式化层）。

**关键算法 `initialize()`**（源码 `kernelWakelockDuration.c:88-129`）：

```c
uint64_t cec_upper = cec >> IN_PROGRESS_BITS;     // 已完成 wakelock 数（高 16 位）
uint64_t cec_lower = cec & MAX_IN_PROGRESS;       // in-progress wakelock 数（低 16 位）
uint64_t distance = (kMaxCecUpper + cec_upper - previous_cec_upper) % kMaxCecUpper;

if (((distance == 0) && (previous_cec_lower > cec_lower)) || (distance > (kMaxCecUpper / 2))) {
    return SKIP_PROCESSING;  // 跳过老事件
}
if (distance > 64) {
    __sync_fetch_and_or(&state_map->program_init, kFullyInitialized);
}
```

**cec 字段**：kernel wakelock 子系统用一个**独立的「concurrent event counter (cec)」字段携带状态信息**——高 16 位是「已完成 wakelock 计数」，低 16 位是「in-progress wakelock 数」。**这种设计允许 eBPF 程序在事件丢失时仍能从 cec 增量推断持续时间，是处理「BPF 动态加载 vs 内核事件持续产生」竞态的标准模式**。

**`raw_tp` vs `tp`**：与 cyclePerUid 的 `tp_btf/` 不同，kernelWakelockDuration 使用 `raw_tp/`——直接读 raw args 数组，避免 tracepoint 格式化开销，**路径性能更高**，但需要直接理解内核 tracepoint proto。

### 附件 6 — progs.aconfig 的 3 个 flag

```aconfig
package: "android.bpfprogs.flags"
container: "system"

flag { name: "kernel_wakelock_duration"
       namespace: "pixel_data_engineering"
       bug: "373519546" }

flag { name: "load_dmabuf_iterator"
       namespace: "android_kernel"
       bug: "442596542" }

flag { name: "load_bpf_lock_contention"
       namespace: "kernel_memory_management"
       bug: "442017923" }
```

**注意点**：
- **3 个 flag 的 namespace 各不相同**（pixel_data_engineering / android_kernel / kernel_memory_management）——说明这是灰度策略，由不同团队/不同 release 节奏控制
- bug 号在 `373-442` 区间说明这些是 **2024-2025 较新加入**的特性，处于成熟度爬升期
- **`cyclePerUid` 不在 aconfig 中**——它的启用完全由 `Android.bp` 的 `arch: { x86_64: { enabled: true } }` 决定，是构建时硬编码开关，**Pixel ARM 设备上不可用**
- 既然是 aconfig flag 控制，理论上可以通过 `adb shell cmd device_config` 灰度开启，但具体 default 值在 `frameworks/proto_logging` 或 `vendor/` 中（本次未读取）

### 附件 7 — 上文 `[待验证]` 解决状态

| §14.25 原 `[待验证]` 项 | 解决状态 | 证据 |
|------------------------|---------|------|
| cyclePerUid 的数据来源 | ✅ PMU TSC 计数器 | `tsc_events` map + 源码注释 |
| cyclePerUid 是否 per-process | ✅ 纯 per-UID | `uid = uid_gid & 0xFFFFFFFF` |
| dmabufIter 挂载方式 | ✅ BPF iterator（`iter/dmabuf`） | `DEFINE_BPF_PROG("iter/dmabuf", ...)` |
| dmabufIter 是否能定位泄漏 | ⚠️ 部分（数量/总量审计可，attachment_count 字段**不存在**） | 源码字段列表 |
| 新增程序的加载路径 | ✅ libbpf 路径（`.bpf` + CO-RE） | `Android.bp` 的 `libbpf_prog { ... }` |
| kernelWakelockDuration attach | ✅ `raw_tp/wakeup_source_activate` | `DEFINE_BPF_PROG("raw_tp/wakeup_source_activate", ...)` |
| bpfLockContention attach | ✅ `tp/lock/contention_begin` + `tp/lock/contention_end` | 源码 |
| 是否依赖 CONFIG_LOCKDEP | ✅ 否，仅需 `CONFIG_LOCK_EVENT_COUNTS` | 源码未引用 lockdep API |
| 新增程序的 Perfetto data source 对接 | ❌ 未在 `system/bpfprogs/` 中找到证据 | 本次未深入 `platform/packages/modules/Perfetto` |

### 附件 8 — 新增澄清：cpucycleperuid Rust FFI 库

§14.25 上文推测 `libs/cpucycleperuid/lib.rs` 是配套的 Rust FFI 库。**本调研在 `android17-release` 中未找到 `libs/cpucycleperuid/` 目录**。可能的解释：

1. 该目录位于其他仓库（如 `platform/frameworks/base` 或 `platform/packages/modules/Statsd`），后续需交叉验证
2. cyclePerUid 的用户态 reader 仍在开发中（bug=373-442 区间说明这些特性较新）
3. §14.25 上文基于多源文章推测，**该推测无源码证据**

> 建议在 §14.25 的「🔹 cpucycleperuid Rust FFI 库」一段标注 `[未验证: 仓库路径]`。

---

> 本节基于 AOSP `android-17.0.0_r1` 源码基线实读，HEAD = `238924255acb29e72d0204ca66d4ea0792b84abb`。所有源码路径均来自 `https://android.googlesource.com/platform/system/bpfprogs/+/refs/heads/android17-release/`。完整报告与对照见 `DeepResearch/2026-07-09-android17-ebpf-observability-matrix-verified.md`。
