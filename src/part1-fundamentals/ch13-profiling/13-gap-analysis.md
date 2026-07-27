---
title: "Android 17 eBPF观测增强"
chapter: "ch13/ch13.13"
status: quarantined
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: ["Android-17", "ch13/ch13", "源码分析", "性能优化"]
related_chapters: ["ch13/ch13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-08"
gap_source: "素材驱动"
gap_score: "19/20"
---
<!-- 
[QUARANTINE NOTICE — 2026-07-08]
原因：outline 模板错误：标题为 eBPF 观测增强，但大纲内容全部是 LMKD/PSI（copy-paste 错误）。
处理：本章由 task2a-knowledge-gap 自动创建，但 outline 模板存在 copy-paste 错误。
如需恢复，请手动修正 outline 后将 status 改回 draft。
-->


# 13 Android 17 eBPF观测增强

<!-- outline-start -->
## 本节要点大纲

### 🔹 锚点（必须覆盖）

- 🔸 LMKD 从 kernel module 到 userspace 守护进程的演进路径
- 🔸 PSI（Pressure Stall Information）监听机制与 BPF ring buffer 实现
- 🔸 三维决策模型：zone watermarks、thrashing、swap utilization
- 🔸 pidfd 等待机制替代传统信号量的实现方案
- 🔸 epoll 事件驱动的高效响应架构（10ms/100ms 双间隔）
- 🔸 Android 17 LMKD 与传统 LowMemoryKiller 的根本差异
- 🔸 PSI 监听对内存压力识别精度的提升效果

### 🔹 扩展（可选深入）

- 🔸 各厂商对 PSI 监听参数的定制化配置
- 🔸 通过 Perfetto 观察 PSI 监听行为的方法
- 🔸 LMKD 在极端内存压力下的行为边界
- 🔸 PSI 与 vmpressure 的兼容性和迁移策略

## 本节内容待加工

> 本节基于 DeepResearch 素材驱动，通过源码级分析Android 17 LMKD的PSI协同机制，从内核态到用户态的完整迁移路径。
>
> **注**：所有锚点内容待加工，需要基于 AOSP android-17.0.0_r1 源码进行验证和深化。

<!-- outline-end -->

## 审阅结论

本文件标题是 eBPF 可观测性，受保护提纲却在讨论 lmkd/PSI。两者都运行在 Linux/Android 系统层，也都能提供性能证据，但 Android 17 源码没有让 lmkd 通过 BPF ring buffer 接收 PSI 的实现。继续沿原提纲扩写，会把两套独立数据路径画成一条不存在的调用关系。

本页保持 `quarantined`，只记录 `android-17.0.0_r1` 与 `android17-6.18-2026-06_r6` 下可以复核的边界。eBPF 与 lmkd 专题应分别阅读。

## 1. Android 17 bpfloader 中可核对的对象

Android 17 的 Rust `bpfloader.rs` 明确登记了下面四类对象。它们的装载条件、attach 类型和消费者并不相同。

| 对象 | loader 中的镜像路径 | 装载条件与 attach | 观测边界 |
|---|---|---|---|
| `cyclePerUid.bpf` | `/system/etc/bpf/cpucycleperuid/` | 仅编译到 x86_64；还要求 `x86_cpu_energy_attribution` flag | 按 UID 归集 TSC cycle，并由 Rust 库结合 Intel RAPL；不能外推到 ARM SoC |
| `kernelWakelockDuration.bpf` | `/system/etc/bpf/kernelWakelockDuration.bpf` | `kernel_wakelock_duration` flag；自动 attach `wakeup_source_activate/deactivate` | 聚合系统是否被 kernel wakeup source 持续阻止 suspend 的时间 |
| `dmabufIter.bpf` | `/system/etc/bpf/dmabuf/dmabufIter.bpf` | `load_dmabuf_iterator` flag；自动 attach `iter/dmabuf` | 按需遍历 DMA-BUF，适合数量和总量审计 |
| `bpfLockContention.bpf` | `/system/etc/bpf/lock_contention/` | `load_bpf_lock_contention` flag；内核至少 6.1；attach contention begin/end | 聚合被允许观察的内核锁竞争延迟 |

原材料把第四项写成 `locks`，这个名称过于宽泛。Android 17 loader 使用 `bpfLockContention.bpf`，pin 前缀是 `lock_contention/`，并为 `contention_start_map` 与 `contention_latency_map` 设置不同权限。

`cyclePerUid` 也不是通用 Android 手机能力。loader 用 `#[cfg(target_arch = "x86_64")]` 排除其他架构，`frameworks/native/libs/cpucycleperuid/lib.rs` 还直接读取 Intel RAPL 的 `energy_uj`。在 arm64 设备上讨论 UID 能耗归因时，不能复用这条实现。

这些对象被 bpfloader 加载和 pin，不表示 Perfetto UI 会自动出现同名 track。需要查看具体用户态 reader 是否读取 map/iterator，再确认它把数据交给 statsd、dumpsys、Perfetto producer 或其他消费者。没有消费者路径时，不能从“BPF 对象存在”推导出“应用可直接查询”。

### ring buffer 也不是统一数据出口

`system/bpf/progs/bpfRingbufProg.c` 的确验证了 `BPF_MAP_TYPE_RINGBUF`，但 Android 17 loader 将对应对象标成 `skip_on_user: true`，构建配置也只在 debuggable 产品要求安装。它是 loader/ringbuf 测试程序，不能用来证明上述生产对象或 lmkd 都通过 ring buffer 上报。

## 2. lmkd/PSI 的真实数据路径

Android 17 的 `libpsi` 直接打开 `/proc/pressure/memory`、`/proc/pressure/io` 或 `/proc/pressure/cpu`，把 threshold/window 配置写入 fd，再以 `EPOLLPRI` 注册到 epoll。lmkd 收到 PSI 事件后读取 `/proc/meminfo`、`/proc/vmstat`、zoneinfo、PSI 统计和进程状态，随后综合 watermark、swap、thrashing、reclaim 类型与可杀进程的 `oom_score_adj` 做决定。

因此，“zone watermark、thrashing、swap utilization 三维模型”只能算排障提示，不能当成完整算法。源码还处理 free swap、file cache、direct reclaim、kswapd、critical stall、上一次 kill、可感知进程保护和多种配置阈值。

`PSI_POLL_PERIOD_SHORT_MS = 10` 与 `PSI_POLL_PERIOD_LONG_MS = 100` 是压力事件之后读取状态的短/长轮询间隔。它们会根据低 swap、正在 kill、reclaim 等状态切换；PSI trigger 自身的 window 由 `psi_window_size_ms` 控制，默认是 1000 ms。把 10/100 ms 写成两档 PSI 窗口会误读源码。

pidfd 也没有“替代传统信号量”的语义。lmkd 对目标调用 `pidfd_open()`，通过 `pidfd_send_signal()` 发出 kill，并可用 `process_mrelease()` 回收地址空间；等待目标退出时暂停压力轮询，避免连续杀进程。pidfd 解决 PID 复用和进程生命周期竞态，线程同步仍由各自的队列、锁和 epoll 状态负责。

Android 17 的 PSI 路径继续保留 vmpressure 兼容代码，实际选择取决于 kernel 支持和 lmkd 配置。厂商调整阈值前要保留相同 workload 的 kill 数、重启率、PSI stall、swap、thrashing 和用户可感知进程存活数据，不能只追求更快触发。

## 3. 该怎样观察

| 问题 | 优先证据 |
|---|---|
| lmkd 为什么被唤醒 | `/proc/pressure/*`、lmkd 日志、kill reason、PSI some/full |
| 为什么选择某个进程 | `oom_score_adj`、进程状态、RSS/swap、killinfo/statsd |
| DMA-BUF 是否增长 | dmabuf iterator/`dmabuf_dump`、GpuService 数据、进程与 exporter 归因 |
| kernel wakeup source 是否阻止 suspend | kernel wakelock duration map、wakeup source、suspend trace |
| 内核锁是否形成长尾 | lock contention map、对应锁白名单、sched/ftrace 上下文 |
| App 线程为什么卡住 | Perfetto sched/thread_state、atrace、应用 marker；不能只看系统 BPF 聚合值 |

聚合计数适合发现异常方向，完整调用路径仍需要 trace、日志和源码上下文。生产采集还要检查 pinned map 权限、SELinux、用户数据归因和采集开销。

## 4. 正确阅读入口

- Android 17 / ACK 6.18 的 BPF 加载、安全与内核能力边界，见 [1.60 Android 17 / ACK 6.18 BPF 可观测性与可编程边界](../ch01-architecture/1.60-linux-610-bpf-android17-boundary.md)。
- PSI trigger、lmkd 决策与进程回收，见 [4.15 Android 17 PSI/LowMemDetector 与 lmkd 内存压力检测架构演进](../ch04-memory/15-psi-lowmemdetector-lmkd-architecture.md)。
- DMA-BUF 与 GpuService 的数据路径，见 [14.30 GpuService GPU 内存可观测性架构](../../part3-tools/ch14-other-tools/14.30-android17-gpuservice-gpu-memory-observability.md)。

## 源码入口

- [Android 17 Rust `bpfloader.rs`](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/loader/bpfloader.rs)
- [Android 17 `cpucycleperuid` Rust reader](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/cpucycleperuid/lib.rs)
- [Android 17 `lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [Android 17 `libpsi`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/libpsi/psi.cpp)
- [Android 17 lmkd `reaper.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/reaper.cpp)
