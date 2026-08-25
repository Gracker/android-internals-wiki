---
title: Android 17 Kernel 6.18 与 ARM64 安全开销
section: '18.3'
chapter: '18.3'
status: ready-to-publish
task9_state: reviewed
pipeline_stage: ready-to-publish
applicable_versions: Android 17 (API 37)
tags:
- android
- linux
- research
- kernel-security
- ARM64
- KASLR
- KPTI
- Spectre
- PAC
- BTI
- MTE
- GCS
- CFI
- performance-overhead
sources:
- type: blog
  path: https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html
- type: blog
  path: https://developer.android.com/blog/posts/boosting-android-performance-introducing-autofdo-for-the-kernel
- type: docs
  path: https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds
- type: docs
  path: https://source.android.com/docs/core/perf/lmkd
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp
- type: aosp
  path: https://android.googlesource.com/platform/external/liburing/+/refs/tags/android-17.0.0_r1/Android.bp
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/heads/android15-6.6
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/Kconfig
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/include/asm/barrier.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/nospec.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/entry.S
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/kaslr.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/proton-pack.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/kernel-parameters.txt
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/pointer-authentication.rst
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/memory-tagging-extension.rst
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/gcs.rst
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/arm-mte
- type: official
  path: https://developer.android.com/ndk/guides/stable_apis
task2b_state: fixed
task6_state: reviewed
last_body_apply_at: '2026-08-16T11:18:13+08:00'
last_body_apply_run_id: 20260816-111514-396831f0
last_idle_audit_at: '2026-07-27T10:35:11+08:00'
last_idle_audit_run_id: 20260727-103511-idle-audit-5f410a75
last_verified: '2026-08-16'
last_verified_against: Android 17 GKI 6.18 release matrix through android17-6.18-2026-06_r38 + fixed r6 source snapshot (Linux 6.18.21) + android-17.0.0_r1 lmkd/external liburing source
confidence: high
consolidated_from:
- 与内核主题无关的 ART generational CMC 与 DeliQueue 内容统一归入 18.1
- src/part4-system/ch18-aosp/04-android17-kernel618-performance.md
- src/part4-system/ch18-aosp/10-arm64-kernel-security-mitigation-performance.md
related_chapters:
- '4.9'
- '5.1'
- '5.2'
- '18.1'
- '18.4'
- '18.7'
- '20.11'
last_consolidated_at: '2026-08-24'
---

# Android 17 Kernel 6.18 与 ARM64 安全开销

Android 17 GKI 6.18 改变调度、内存、BPF 和驱动基础，ARM64 安全缓解机制又会影响间接分支、系统调用和上下文切换。性能比较必须保持内核配置和缓解状态一致。

## GKI 6.18 调度、内存与观测变化

### 为什么要把平台和内核分开

本文有意固定两个核验锚点：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`；
- Android common kernel：`android17-6.18-2026-06_r6`，其 `Makefile` 版本为 6.18.21。

截至 2026-08-14，官方 `android17-6.18-2026-06` 发布序列已经列到 r38。本文保留 r6，是因为后文的 AutoFDO profile、基准数据和源码判断都绑定这个快照；它不是“当前最新 tag”的代称。验证 r6 之后的构建时，应重新比较目标 tag，不能直接沿用这里的源码存在性结论。

`android15-6.6` 与 `android16-6.12` 只用于解释 EEVDF、sched_ext 和 AutoFDO 的演进，不作为 r6 实现结论。平台行为也不能从内核分支名推导：Android 17 的 generational CMC 与 lock-free `MessageQueue` 位于 ART 和 `frameworks/base`，它们不属于 Linux 6.18 的调度或存储改动。

GKI（Generic Kernel Image，通用内核镜像）把通用内核与板级 vendor modules 分开；vendor modules 是设备厂商提供的内核模块。KMI（Kernel Module Interface，内核模块接口）约束两者之间的二进制接口。

设备采用 `android17-6.18-2026-06_r6` release build，还需要相容的 vendor modules、产品配置和启动参数。源码 tag 中存在某个功能，无法单独证明设备已经启用它。

### Android 17 / 6.18 的核查表

不同来源的性能数据不能汇成一项“Android 17 总收益”。应先确认机制、启用条件和原始测试口径。

| 主题 | `android17-6.18-2026-06_r6` 或平台证据 | 结论边界 |
|---|---|---|
| EEVDF | `kernel/sched/fair.c` 与 `Documentation/scheduler/sched-eevdf.rst` | fair class 的选取模型；不能直接承诺 UI 延迟下降 |
| sched_ext | GKI 配置含 `CONFIG_SCHED_CLASS_EXT=y` | BPF scheduler 加载并运行后才会接管相应任务 |
| F2FS checkpoint merge | `checkpoint_merge` 挂载选项与 checkpoint kthread | 需要设备使用 F2FS 且挂载时启用 |
| dm-verity multi-buffer hashing | r6 的 `dm-verity-target.c` 没有 `verity_hash_mb()` 或 `crypto_shash_finup_mb()` | 外部补丁数据不能记为 r6 收益 |
| io_uring | 6.18 源码含完整实现 | 内核能力不等于 Android 公共 API，也不等于框架采用 |
| AutoFDO | GKI 配置含 `CONFIG_AUTOFDO_CLANG=y`，tag 内含 `kernel.afdo` | README 数据是 Pixel 8 preliminary benchmark |
| MGLRU | GKI 配置含 `CONFIG_LRU_GEN=y` 与 `CONFIG_LRU_GEN_ENABLED=y` | 页回收策略；不能直接换算为 lmkd kill 降幅 |

设备测试记录至少应包含 platform build、kernel release、GKI tag 或 build ID、`vendor_boot` 镜像版本、挂载参数、CPU 拓扑、温度、benchmark 输入和样本统计。CPU 拓扑指核心、集群及其容量关系。缺少这些信息时，结果只适合做该设备的排查线索。

### 调度器变化：EEVDF fair scheduler + sched_ext 可扩展框架

#### EEVDF：fair scheduler 的 lag / deadline 模型

EEVDF 是 Earliest Eligible Virtual Deadline First，即“从符合条件的任务中选择虚拟截止时间最早者”。Linux 从 6.6 开始向 EEVDF 过渡。r6 的 `kernel/sched/fair.c` 保留 `entity_eligible()`、`pick_eevdf()` 和 virtual deadline 相关路径，因此 6.12 不能写成 EEVDF 的 Android 17 分界点。

同优先级 runnable entity 仍按权重分享 CPU；runnable entity 是已经可运行、正在等待 CPU 的调度对象。调度器用 lag 表示它相对公平份额的欠账或超额服务：lag 大于等于零时具备 eligibility，再从 eligible 集合中选 virtual deadline 更早的对象。请求的 slice 是一次希望获得的运行时间片；slice 较短时可以得到更早的 deadline，使延迟敏感任务有机会更早被选择。

这套模型不会识别“UI 线程”或 `doFrame` 语义，也不会保证短任务总能抢占后台任务。`nice` 影响 fair class 权重，`uclamp` 限制调度器看到的利用率；cpuset 与 CPU affinity 限定任务可运行的 CPU。

结果还受 thermal 热约束、CPU frequency selection、RT/DL 实时调度类和厂商扩展影响。评估 EEVDF 时应测从唤醒到真正运行的时间、runnable 队列等待、slice 长度与 preemption（抢占），不能只看总 CPU time。

#### sched_ext：用 BPF 实现可扩展调度器

sched_ext 在 Linux 6.12 进入上游 mainline，允许一组 BPF 程序实现调度策略。BPF 是在内核受控环境中运行的可验证程序，`struct_ops` 让这些程序提供一组内核回调。

Android 17 GKI 开启 `CONFIG_SCHED_CLASS_EXT=y`，但文档明确规定：**BPF scheduler 加载并运行后，sched_ext 才会使用**。只看到配置项或 `kernel/sched/ext.c`，不能声称设备已经由自定义调度器接管。

#### sched_ext 源码结构与设备厂商采用边界

6.18 的核心实现和文档分布如下：

- `kernel/sched/ext.c` 负责 scheduler class、BPF 可调用的内核函数（kfunc）、启停与错误回退；
- `include/linux/sched/ext.h` 定义 `sched_ext_entity`、DSQ 标志和任务状态；
- `tools/sched_ext/` 提供示例调度器和状态工具；
- `Documentation/scheduler/sched-ext.rst` 描述启用条件、DSQ 与故障回退。

BPF scheduler 通过 `struct sched_ext_ops` 提供 `select_cpu()`、`enqueue()`、`dispatch()` 等可选回调，只有 `ops.name` 必填。`select_cpu()` 的结果是优化提示；最终 CPU 仍受任务 cpumask（允许使用哪些 CPU 的位集合）与调度核心校验约束。

任务先进入 dispatch queue（DSQ，待分派队列）。6.18 提供全局 FIFO（先进先出）队列 `SCX_DSQ_GLOBAL`、每 CPU 的 `SCX_DSQ_LOCAL`，BPF scheduler 也可创建自定义 DSQ。CPU 取任务时依次检查本地 DSQ、全局 DSQ，再调用 `ops.dispatch()`。自定义 DSQ 可按 FIFO 或 `dsq_vtime` 虚拟时间排序。

6.18 的插入接口为 `scx_bpf_dsq_insert()` 与 `scx_bpf_dsq_insert_vtime()`。6.12 示例中的旧名 `scx_bpf_dispatch()` / `scx_bpf_dispatch_vtime()` 只适合阅读旧分支，移植时应按目标 tag 编译，避免从函数名猜版本。

sched_ext 的安全回退是运行边界的一部分。BPF scheduler 退出、runnable task stall、内部错误或 `SysRq-S` 紧急按键序列都会让任务回到 fair class；`sched_ext_dump` tracepoint（内核追踪事件点）可读取诊断 dump。

下面的命令用于确认设备是否加载过 BPF scheduler。量产设备可能因权限或裁剪而无法读取这些节点。

```bash
adb shell 'cat /sys/kernel/sched_ext/state 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/root/ops 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/enable_seq 2>/dev/null'
```

`state` 表示当前启停状态，`root/ops` 给出当前调度器名称，单调递增的 `enable_seq` 大于零表示本次启动后曾经加载过 BPF scheduler。节点不存在时，只能说明当前设备没有暴露这组 ABI（用户态可读取的稳定接口），还需结合内核配置和厂商实现核查。

### 存储栈三项核查

F2FS、dm-verity 和 io_uring 位于不同层级。F2FS 是面向闪存设计的文件系统，dm-verity 校验块设备数据完整性，io_uring 是 Linux 异步 I/O 接口。三个子系统都存在于 6.18 tag，但某项上游补丁存在，不代表 r6 已经合入，也不代表 Android 17 设备或应用走到了相应路径。

#### F2FS checkpoint merge：先确认挂载选项

F2FS 的一次 `fsync()` 不必然触发完整 checkpoint；`fsync()` 请求把文件修改同步到持久存储，checkpoint 则保存文件系统可恢复的一致状态。

需要 checkpoint 时，`checkpoint_merge` 可把并发请求交给 `issue_checkpoint_thread` 内核线程处理，减少各调用进程重复发起 checkpoint，并避免请求受调用进程 cgroup 资源组的 I/O budget 和 CPU shares 长时间拖延。

6.18 r6 的 `fs/f2fs/super.c` 解析 `checkpoint_merge` / `nocheckpoint_merge`，默认挂载选项会设置 `MERGE_CHECKPOINT`。可写挂载且没有禁用 checkpoint 时，checkpoint kthread 才会启动；`nocheckpoint_merge` 会停止这条路径。

`fs/f2fs/checkpoint.c` 中的 `f2fs_issue_checkpoint()`、`issue_list`、`queued_ckpt` 与 `ckpt_wait_queue` 构成请求与等待路径。

检查设备时应读取 `/proc/mounts` 或 `/proc/self/mountinfo`，确认 data 分区的文件系统和挂载参数。SQLite WAL（Write-Ahead Logging，预写日志）commit 会调用同步写入，但一次 commit 是否进入 F2FS checkpoint 路径，取决于文件系统状态和 `f2fs_do_sync_file()` 的判定。不能从“应用调用了 fsync”直接推出 checkpoint merge 收益。

#### io_uring：内核实现不是 Android 应用契约

6.18 r6 的 `io_uring/` 包含 multishot、registered buffers、ring setup 和 zero-copy 相关路径。multishot 允许一次提交产生多次完成结果，registered buffers 会预先登记 I/O 内存，zero-copy 则试图减少数据复制。

每项能力都有自己的 opcode（操作码）、flag、内存注册和 fallback 条件；`IORING_SETUP_NO_MMAP` 描述 ring 内存的建立方式，不代表应用数据已经 zero-copy。

AOSP 的 `external/liburing` 提供 native 静态库构建规则，但这不能证明 SQLite、Cronet、OkHttp 或 Java I/O 在 Android 17 默认使用 io_uring。普通应用还受 syscall 可用性、seccomp（系统调用过滤）、SELinux、NDK API 与设备内核配置约束。缺少调用栈或 syscall 证据时，不能把 io_uring 计入应用收益。

#### dm-verity multi-buffer hashing：r6 未合入

逐行核对 r6 的 `drivers/md/dm-verity-target.c`，当前实现是 `verity_hash()` 配合 `crypto_shash_finup()` 等单请求接口。该文件没有 `verity_hash_mb()`，也没有调用这条补丁路径使用的 `crypto_shash_finup_mb()`。

2025 年发布到邮件列表的 v8 补丁曾报告 ARM64 与 x86_64 cold-cache dm-verity read 吞吐约提升 35%；cold cache 表示数据尚未进入内存缓存。作者同时说明指标波动较大。它是补丁环境的测试结果，不能写入 `android17-6.18-2026-06_r6` 的收益表，更不能改写为 Android 17 安装、冷启动或 OTA 固定提升。

#### 存储路径如何测

三项机制应分别测量：

- F2FS：`f2fs_sync_file_enter/exit`、checkpoint 数量、checkpoint 时长、块写入量与挂载参数；
- dm-verity：cold/warm cache 分开，记录当前 hash driver、数据块大小、CPU time 与块设备吞吐；评估 multi-buffer 补丁必须使用明确包含补丁的自定义内核；
- io_uring：确认 `io_uring_setup`、`io_uring_enter`、opcode 和 fallback，再比较每次业务操作的提交数与延迟。

Perfetto 是 Android 系统性能追踪工具，可采集 `block_rq_issue` / `block_rq_complete` 和 F2FS tracepoints。dm-verity 没有一个可通用于所有 Android 设备的“dm-verity track”；需要把 block I/O、CPU sampling（定期抽样 CPU 调用栈）和 `verity_*` 调用栈放在同一业务区间内分析。

### AutoFDO Profile-Guided Optimization 的内核应用

AutoFDO 是基于真实执行样本指导 Clang 内联、分支权重和代码布局的构建期优化。Android 17 GKI `gki_defconfig` 设置 `CONFIG_AUTOFDO_CLANG=y`，r6 tag 也包含绑定 Linux 6.18.21 的 `gki/aarch64/afdo/kernel.afdo` 与说明文件；这证明该 release build 已具备内核 Profile 接入，不证明任意设备运行的内核采用了同一 Profile。

r6 README 中 Pixel 8 的 boot、cold launch 与 Binder 数据都标为初步结果，其中 Binder 项还采用多轮最佳值，不能外推为跨 SoC 或跨产品保证。设备侧需要把 release artifact、build config、kernel build ID 与 Profile 对齐，再做只改变 Profile 的 A/B。

Profile 的采集、ETM/ETE/TRBE 数据转换、`vmlinux` 构建接入、质量控制和完整 A/B 方法统一由 [18.4 AutoFDO 反馈导向优化与 Android 验证](04-autofdo-feedback-directed-optimization.md) 展开。本节只保留它在 GKI 6.18 功能集合中的启用证据与设备核查边界。ART AOT、Baseline Profile、generational CMC 和 DeliQueue 属于用户态或 Framework，不能记为 Kernel 6.18 收益。

### MGLRU 与页面回收优化

MGLRU 是 Multi-Gen LRU，即按多个代际管理“最近最少使用”页面的回收机制。Android 17 GKI r6 的 `gki_defconfig` 同时设置 `CONFIG_LRU_GEN=y` 与 `CONFIG_LRU_GEN_ENABLED=y`，所以 GKI 默认配置已选择它。设备仍可通过产品配置或运行时开关形成差异。

#### generation 表示访问时间窗口

MGLRU 为 memcg（memory cgroup，内存资源组）与 NUMA node（具有本地内存访问特性的硬件节点）维护多代页面。aging 扫描页表访问位等信号，把近期访问的页面放入较新的 generation；reclaim 从较老 generation 选择回收候选。`min_gen_nr` 到 `max_gen_nr` 形成按时间窗口划分的 working-set histogram，也就是各代工作集大小的分布。

generation 主要表达 recency（最近是否访问），不能简化为“每秒访问次数”。MGLRU 文档还包含 refault（页面回收后又被访问）、匿名页与文件页选择、swappiness 和不同访问渠道的处理；swappiness 调整匿名页与文件页之间的回收倾向。它对顺序扫描、匿名内存、文件缓存与 swap 的表现需要结合 workload 解释。

运行时 stable ABI 位于 `/sys/kernel/mm/lru_gen/`。下面的命令用于读取主开关；权限不足时应改从内核配置和厂商诊断产物核查。

```bash
adb shell 'cat /sys/kernel/mm/lru_gen/enabled 2>/dev/null'
```

结果是 bitmask（位掩码）。`0x0001` 表示主功能开启，其余位控制批量清除页表 accessed bit 的能力；设备是否支持这些位还受 MMU（内存管理单元）特性影响。

#### 与 lmkd 的关系是间接影响

`lmkd` 是 Android 的 Low Memory Killer Daemon，负责在高内存压力下选择较不重要的进程终止。它根据 PSI、内存水位、thrashing 与进程 `oom_score_adj` 等信息决策，不读取 MGLRU generation 来挑选进程。

PSI（Pressure Stall Information）统计资源压力造成的等待，thrashing 指页面反复回收又重新载入，`oom_score_adj` 表示进程被选择终止时的相对优先级。MGLRU 改变内核 reclaim 的页面选择和成本，进而可能改变 PSI stall、refault、swap 与可用内存；这些变化才会影响 `lmkd` 所见的压力。

“MGLRU 开启后 kill 次数必然下降”没有源码保证。某些负载可能减少 refault 和 `kswapd` CPU，另一些负载可能因 swap、file cache 或 reclaim 参数呈现不同结果。对照实验应同时记录：

- `/proc/pressure/memory` 的 `some` / `full` stall，分别表示部分任务和所有非空闲任务受阻；
- `mm_vmscan_*` 事件、后台回收线程 `kswapd` 的 CPU time 与任务自行回收页面的 direct reclaim；
- major/minor fault、workingset refault、swap in/out；major fault 需要存储 I/O，minor fault 不需要；
- lmkd kill reason、被杀进程的 `oom_score_adj` 与进程状态；
- 相同业务脚本下的帧、启动与进程留存结果。

### 在 Perfetto 中的可观测性

Perfetto 展示运行结果，不会仅凭一条 track（时间轴轨道）告诉你“EEVDF、MGLRU 或 AutoFDO 带来了多少收益”。需要把机制状态、trace 和 A/B 构建关联起来。

| 主题 | 采集项 | 能回答的问题 |
|---|---|---|
| EEVDF | `sched_waking`、`sched_switch`、线程优先级、CPU frequency、uclamp | 线程何时 runnable、等待多久、在哪个 CPU 运行 |
| sched_ext | sched tracks、`sched_ext_dump`、sysfs 状态、BPF scheduler 自有 trace | 自定义调度器是否启用、是否报错回退 |
| F2FS | `f2fs_sync_file_enter/exit`、checkpoint 事件、block request | 同步写与 checkpoint 分别耗时多久 |
| dm-verity | block request、CPU sampling、`verity_*` 栈 | r6 当前 cold read 卡在 I/O 或 hashing 的比例 |
| MGLRU | `mm_vmscan_*`、PSI、page fault、swap、lmkd 事件 | reclaim stall、refault 与 kill 如何变化 |

`sched_switch` 只能反映谁获得 CPU，不能还原 `pick_eevdf()` 的全部候选和 virtual deadline。`sched_ext_dump` 用于错误或主动 dump，也不等同于每次 BPF 调度决定的流水记录。需要细看策略时，应为目标 BPF scheduler 添加自己的 trace events。

#### A/B 设计

直接比较 Android 16 与 Android 17 会同时改变 framework、ART、kernel、vendor、驱动和配置，无法归因到单个机制。可复现对照应遵循以下顺序：

1. 固定设备、固件、散热条件、业务输入和 kernel source；
2. 只改变一个配置、profile 或运行时开关；
3. 预热后交错执行多轮，避免一组测试总处于更冷或更热的阶段；
4. 报告中位数、尾延迟、离散程度、频率驻留与温度；
5. 把“没有检出差异”和“证明零开销”分开表述。

### 版本演进：把平台版本和 GKI 分支分开

| 维度 | 锚点 | 结论 |
|---|---|---|
| Android 15 相关 GKI | `android15-6.6` | fair scheduler 已有 EEVDF 路径；AutoFDO 后续投放到该 LTS（长期维护）分支 |
| Android 16 相关 GKI | `android16-6.12` | sched_ext 进入 mainline 后可在该分支使用；早期 6.12 示例可能使用 `scx_bpf_dispatch*()` 命名 |
| 本文 Android 17 内核锚点 | `android17-6.18-2026-06_r6`，Linux 6.18.21 | 使用 `scx_bpf_dsq_insert*()`；GKI 配置开启 sched_ext、AutoFDO 与 MGLRU；tag 含 6.18.21 AFDO profile |
| Android 17 平台 | `android-17.0.0_r1` / API 37 | 只作为实验控制变量；平台运行时变化见 18.1 |

F2FS checkpoint merge、MGLRU 与 io_uring 都有跨分支历史。dm-verity multi-buffer hashing 仍是 r6 之外的补丁证据，不能列入该 tag 的功能集合。

### 常见问题与误区

**“设备报告 6.18，所以正文里的全部机制都已启用。”**

kernel release 只能确定代码基线。还要查最终配置、挂载参数、BPF scheduler、CPU 能力、boot 参数和用户态采用。

**“EEVDF 会自动把 UI 线程排在后台任务前面。”**

EEVDF 使用 lag、slice 与 virtual deadline，不读取 Android UI 语义。UI 结果由调度属性、CPU 放置、频率、热状态和 runnable 竞争共同决定。

**“`CONFIG_SCHED_CLASS_EXT=y` 表示 OEM scheduler 正在运行。”**

该配置只编入框架。`/sys/kernel/sched_ext/state`、`root/ops` 与 `enable_seq` 才能提供当前或本次启动期间的加载证据。

**“MGLRU 开启后 lmkd 会按 generation 杀进程。”**

lmkd 仍按 Android 的压力与进程优先级策略决策。MGLRU 位于页面回收层，只能经 reclaim、PSI、refault 和可用内存间接影响 kill 条件。

## ARM64 缓解机制、开销与验证

内核版本基线确定后，安全特性需要按 CPU 能力、内核配置和实际启用状态测量。不能用关闭安全机制的结果代表量产配置。

> **版本口径**：平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核源码以 `android17-6.18-2026-06_r6` 为准。配置、硬件能力和运行时策略共同决定安全机制是否生效。
>
> MTE 的应用实践见 [§4.9](../../part1-fundamentals/ch04-memory/09-android17-memory-tagging-extension-mte.md)，Rust 系统组件的边界见 [§18.7](07-rust-system-services-performance.md)。

### 1. 先确认三个条件

Kconfig 是 Linux 内核描述配置选项、依赖关系和默认值的系统。看到其中的 `default y`，只能说明依赖满足且没有其他配置覆盖时，该选项默认取 `y`。它无法单独证明某台 Android 设备正在使用对应机制。设备结论需要同时满足三个条件：

1. **构建条件**：最终 `.config` 含有所需选项，编译器和链接器也支持相应插桩。
2. **硬件与固件条件**：CPU 实现架构特性，或固件提供内核所需的漏洞缓解调用。
3. **运行时条件**：内核没有通过启动参数关闭功能；用户态机制还需要二进制或进程显式启用。

Android 17 GKI（Generic Kernel Image，通用内核镜像）的基准配置 `gki_defconfig` 明确设置了 `CONFIG_RANDOMIZE_BASE=y`、`CONFIG_SHADOW_CALL_STACK=y` 和 `CONFIG_CFI=y`。

同一配置关闭了 `CONFIG_RANDOMIZE_MODULE_REGION_FULL`。

PAC、BTI、MTE 与 GCS 在 `arch/arm64/Kconfig` 中是 `default y`，仍受工具链、硬件和运行时条件约束。

下面这张表用于确定排查入口，不提供脱离设备和负载的固定性能百分比。

| 机制 | 保护对象 | Android 17 / 6.18 源码入口 | 生效条件 |
|---|---|---|---|
| KASLR | 内核与模块地址布局 | `CONFIG_RANDOMIZE_BASE`、`kaslr.c` | 构建开启、启动阶段获得熵、未传入 `nokaslr` |
| KPTI | EL0 与内核地址空间隔离 | `CONFIG_UNMAP_KERNEL_AT_EL0`、异常入口代码 | 构建开启，CPU 运行时判定需要或通过 `kpti=1` 强制 |
| Spectre v1 | 越界推测访问 | `array_index_nospec()`、架构屏障 | 易受影响的代码点完成局部修复 |
| Spectre v2 | 间接分支预测注入 | `proton-pack.c`、CPU capability 与固件接口 | 取决于 CPU 型号、固件和运行时选择 |
| Spectre-BHB | 分支历史注入 | `CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY` | CPU 需要缓解，内核选择分支序列或固件调用 |
| PAC | 返回地址或用户指针认证 | `CONFIG_ARM64_PTR_AUTH*` | 构建、硬件、二进制策略共同满足 |
| BTI | 计算分支合法落点 | `CONFIG_ARM64_BTI*` | 构建与硬件支持，目标代码带 BTI 属性 |
| SCS | 内核返回地址 | `CONFIG_SHADOW_CALL_STACK` | 编译器插桩与内核运行时支持 |
| KCFI | 内核间接调用目标类型 | `CONFIG_CFI` | 编译器支持 `-fsanitize=kcfi` |
| MTE | 用户态内存访问标签 | `CONFIG_ARM64_MTE` | 构建、硬件、映射属性与进程模式共同满足 |
| GCS | 用户态返回地址栈 | `CONFIG_ARM64_GCS`、GCS 用户 ABI | 构建、硬件和线程级 `prctl()` 启用 |

表中的 EL0 是非特权用户态执行所在的最低异常级。CPU capability 是内核根据特性寄存器、CPU 型号和勘误表得到的能力标志，不等同于产品宣传中的架构名称。

这几组机制保护的边界不同。BTI 约束间接分支的落点，Spectre v2 缓解处理分支预测器状态；两者不能互相替代。SCS 保护内核返回地址，KCFI 检查内核间接调用的静态类型；GCS 是内核向用户态提供的受保护返回地址栈 ABI。

这里的 ABI（Application Binary Interface）指内核与用户程序约定的寄存器、系统调用和数据结构接口。

### 2. KASLR：启动阶段的地址随机化

KASLR（Kernel Address Space Layout Randomization）启用并获得有效随机种子后，会在启动时改变内核及模块的基地址，使攻击者更难预先知道内核对象的位置。ARM64 KASLR 由 `CONFIG_RANDOMIZE_BASE` 控制。

`arch/arm64/Kconfig` 规定，bootloader（引导程序）可通过设备树 `/chosen/kaslr-seed` 传入随机 `u64`，即 64 位无符号种子。经 UEFI stub 启动时，这段早期引导代码可从 `EFI_RNG_PROTOCOL` 获取熵。

这里的熵指难以预测的随机输入，`arch/arm64/kernel/kaslr.c` 用它计算内核镜像与模块区域的偏移。

`CONFIG_RELOCATABLE` 让 AArch64 内核保留运行时重定位所需的信息。重定位是按实际加载基址修正代码或数据中的地址引用，发生在启动阶段。这个成本应在同一构建、同一设备上测量，不能从镜像体积推导固定毫秒数。KASLR 也不会因为地址变化就给每次间接调用附加一项固定成本。

模块区域还有一项容易写错的配置：

- `CONFIG_RANDOMIZE_MODULE_REGION_FULL=y` 会在覆盖核心内核的 2 GiB 窗口内随机化模块区域，并可能让模块到核心内核的调用经过 module PLT veneer。PLT（Procedure Linkage Table）veneer 是位于模块 PLT 中的跳转桩，用来跨越 AArch64 直接分支指令的距离限制。
- Android 17 的 6.18 GKI `gki_defconfig` 明确写着 `# CONFIG_RANDOMIZE_MODULE_REGION_FULL is not set`。模块区域仍会在较小范围内随机化，不等于模块地址固定。

量产设备常用 `kptr_restrict` 限制内核指针暴露，因而 `/proc/kallsyms` 可能把地址显示为全零。这种结果不能用来判断 KASLR 失效。工程构建可结合最终配置、启动日志和多次冷启动后的符号地址检查；量产结论应以厂商构建产物与启动链配置为依据。

### 3. KPTI：是否执行页表切换由 CPU 判定

KPTI（Kernel Page Table Isolation）用于隔离用户态与内核态页表。`CONFIG_UNMAP_KERNEL_AT_EL0` 的帮助文本描述了 ARM64 实现：CPU 在 EL0 运行时取消大部分内核映射。

发生系统调用、中断或异常后，CPU 经 exception vector table（异常向量表）找到入口，再由 trampoline page（仅保留入口所需映射的跳板页）恢复内核映射。

Android 17 的内核仍把该选项设为 `default y`。

运行时策略比 Kconfig 值更具体。6.18 的启动参数文档对 `kpti=` 的定义是：

- 默认只在需要缓解的核心上启用；
- `kpti=0` 强制关闭；
- `kpti=1` 强制开启。

因此，不能根据 CPU 产品名、上市年份或营销架构名称编制一张“必定启用/跳过”的表。ARM64 内核会综合 CPU capability、MIDR（Main ID Register，CPU 型号与版本标识）匹配、架构特性和勘误信息做判定。

同一 SoC（System on Chip，系统级芯片）还可能包含多种核心。以设备的内核日志、漏洞状态节点和源码匹配结果为准。

KPTI 的热点位于用户态与内核态的往返路径。系统调用、缺页异常和中断密集的负载更值得测量；纯用户态计算的结果不能代表 Binder、网络或存储负载。

TLB（Translation Lookaside Buffer）缓存虚拟地址到物理地址的转换，ASID（Address Space Identifier）用于区分不同地址空间的缓存项。页表切换对 TLB 的影响取决于 ASID、CPU 特性和内核实现，不能概括为“每次都完整刷新 TLB”。

### 4. ARM64 投机执行漏洞缓解

#### 4.1 Spectre v1：局部代码修复

Spectre v1 属于 bounds-check bypass（边界检查绕过）：CPU 可能在边界判断完成前推测执行后续访问。

通用 `array_index_nospec()` 会调用架构提供的 mask 实现。6.18 ARM64 的 `array_index_mask_nospec()` 用比较结果生成全零或全一掩码，使越界索引失去可用值，并在返回前执行 `CSDB`，限制后续指令提前使用推测得到的数据。

`SSBS`（Speculative Store Bypass Safe）控制 Spectre v4 相关的推测存储绕过，不能用来概括这条数组索引修复路径。

局部修复分布在各子系统中，开销也与命中这些路径的次数有关。若性能回退集中在一个驱动或系统调用，需要检查该路径生成的指令和采样结果，不能把整机差异统一归到 Spectre v1。

#### 4.2 Spectre v2：CPU、固件和运行时代码选择

ARM64 的主实现位于 `arch/arm64/kernel/proton-pack.c`。内核识别 CPU 是否受影响，再选择架构提供的硬件行为、固件调用、CPU 专用回调或内核指令序列。

ARM64 alternatives 是其中一项启动期代码选择机制：内核启动时按 CPU 能力改写预留的指令片段。它参与部分异常入口和 BHB 缓解路径，不能概括所有 Spectre v2 处理方式。

Retpoline 是 x86 中常见的返回跳板软件方案，不能用来描述 Android ARM64 的 Spectre v2 主路径。`CONFIG_ARM64_BTI_KERNEL` 也不负责“替换 Retpoline”：BTI 检查计算分支能否到达目标位置，Spectre v2 缓解则约束推测执行利用分支预测状态的方式。

#### 4.3 Spectre-BHB 与 Speculative Store Bypass

BHB（Branch History Buffer）保存近期分支历史，攻击者可能借此影响后续推测路径。`CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY` 在 6.18 中为 `default y`。Kconfig 对处理方式的描述是：从用户态进入异常时，用一段分支序列或固件调用覆盖分支历史。

`SB` 是 Speculation Barrier 指令，但具体 CPU 还可能使用 `ClearBHB`、分支循环、固件调用或硬件保证，不能把实现固定写成“入口插入一条 `SB`”。

Speculative Store Bypass 使用另一套控制。`ssbd=` 是 SSBD（Speculative Store Bypass Disable）的启动参数，支持 `force-on`、`force-off` 和 `kernel`；`kernel` 表示内核持续使用缓解，并允许用户线程通过 `prctl()` 按需请求。

`prctl()` 是调整进程或线程行为的系统调用。它与 Spectre v1、v2、BHB 应分别核查。

设备上的只读状态节点比 CPU 名称推断更可靠。工程机可读取以下信息建立证据链。

```bash
adb shell 'cat /proc/cmdline'
adb shell 'for f in /sys/devices/system/cpu/vulnerabilities/*; do
  printf "%s: " "$(basename "$f")"
  cat "$f"
done'
```

第一项显示启动参数，第二项遍历 sysfs（内核导出的虚拟文件系统）的 `vulnerabilities` 节点，读取内核向用户空间报告的漏洞和缓解状态。节点集合与文本由设备内核决定；缺少某个节点时应回到该设备的源码和配置核查。

### 5. PAC、BTI、SCS 与 KCFI：四条控制流防线

#### 5.1 PAC：指针认证码

PAC（Pointer Authentication Code）把密钥、指针值及上下文计算成认证码，用于检测指针被替换或破坏。ARM64 用户态 PAC 支持由 `CONFIG_ARM64_PTR_AUTH` 控制。Linux 文档列出五个密钥：APIA、APIB 用于指令地址，APDA、APDB 用于数据地址，APGA 用于通用认证码。

内核在 `exec()` 时为进程初始化密钥，同一进程内的线程共享这些密钥；`fork()` 后子进程继承。文档没有规定密钥必须由 `RNDR` 或 `RNDRRS` 指令直接生成，也不能据此推导一个固定的进程创建耗时。

`CONFIG_ARM64_PTR_AUTH_KERNEL` 的范围更窄：编译器为内核函数返回地址加入保护。该选项不能概括成“所有内核函数指针都会被 PAC 签名”。对间接函数指针调用的前向保护，应查看 KCFI 与 BTI。

用户态通过 `HWCAP_PACA` 和 `HWCAP_PACG` 获知相应能力。HWCAP（hardware capability）是内核通过 ELF 辅助向量交给进程的硬件能力位。二进制是否使用 PAC 取决于生成的指令与运行库策略；硬件支持本身不会给已有代码自动加入函数序言与尾声。

ELF note 是二进制中的构建属性记录，可作为静态证据；反汇编中的 `PAC*`/`AUT*` 指令才能直接说明目标代码包含认证序列。

#### 5.2 BTI：限制间接分支入口

`CONFIG_ARM64_BTI` 允许内核为用户态提供 BTI 支持，`CONFIG_ARM64_BTI_KERNEL` 让内核及其模块带有 BTI 标记并在硬件支持时执行检查。后者依赖 PAC 内核配置和编译器的 `-mbranch-protection` 能力。

BTI（Branch Target Identification）把合法目标缩小到带相应 landing pad 的位置。landing pad 是编译器放在允许入口处的兼容指令，常见形式为 `BTI`；CPU 可拒绝间接分支跳入其他位置。BTI 与 PAC 配合保护控制流，但覆盖面仍取决于全部参与链接和加载的代码是否带兼容属性。内核模块也必须满足同一要求。

#### 5.3 Shadow Call Stack

`CONFIG_SHADOW_CALL_STACK`（SCS）使用编译器插桩，把返回地址的受保护副本保存在独立的 shadow stack（影子调用栈）中，降低普通栈内存破坏覆盖返回地址的风险。Android 17 GKI `gki_defconfig` 已开启该项。它是内核构建期机制，与后文的用户态 GCS 不属于同一个 ABI。

#### 5.4 KCFI

6.18 的 `CONFIG_CFI` 使用 KCFI（Kernel Control-Flow Integrity）。编译器在间接函数调用处加入类型检查，只允许目标落到静态类型匹配的函数。这里的前向保护指调用者到间接调用目标的边，SCS 和 PAC return-address protection 则处理函数返回路径。

检查本地 ELF 是否声明 AArch64 branch protection，可使用 NDK 中对应版本的 `llvm-readelf`。下面的命令用于观察 GNU property 和 note，不能单独证明运行时硬件已经执行检查。

```bash
llvm-readelf -n libexample.so
llvm-objdump -d libexample.so | grep -E '\bbti\b|\bpaci[ab]sp\b|\bauti[ab]sp\b'
```

第一行读取 ELF note，第二行抽查反汇编中的 BTI 与 PAC 指令。还需要结合进程映射、设备 HWCAP 和完整链接产物判断覆盖范围；若其中一个静态库没有使用兼容选项，最终二进制的属性或覆盖面也可能变化。

### 6. MTE：标签粒度不等于固定 PSS 增量

ARM64 MTE（Memory Tagging Extension）把内存划分为 16 字节的 allocation granule（分配标签粒度），每个粒度保存 4 位 allocation tag（内存标签），指针高位携带 logical tag（逻辑标签）。CPU 访问内存时比较两者。

tag mismatch（标签不匹配）可同步报告到出错指令，也可异步延迟到稍后的内核入口；asymmetric 模式对读访问同步报告、对写访问异步报告。

内核支持由 `CONFIG_ARM64_MTE` 控制，硬件与内核同时支持时通过 `HWCAP2_MTE` 告知用户空间。带标签的页只能来自使用 `PROT_MTE` 的匿名映射或 RAM-backed 文件映射，例如 tmpfs 或 `memfd`；RAM-backed 表示内容由内存页支撑，不是普通持久化文件。

线程还要通过 `PR_SET_TAGGED_ADDR_CTRL` 设置 tagged-address ABI（允许地址高位携带标签的约定）与 fault mode（标签错误的报告模式）。

Android 应用通常由 `android:memtagMode`、runtime（运行时）和 Scudo 分配器完成进程级原生堆配置，不要求业务代码逐个调用 `mmap()`。

4 位标签是架构标签存储格式，不能换算成“PSS 固定增加 3% 或 5%”。标签存储、分配器元数据、页提交、工作集和故障模式对 CPU 与内存指标的影响不同。评估 MTE 时至少分别记录：

- 进程 PSS、RSS、匿名页和 swap；
- 分配速率、释放速率与 Scudo 路径；
- 同步 fault 的定位收益和用户可见延迟；
- 异步 fault 的发现延迟与崩溃归因；
- 同一业务脚本下的 CPU time、帧时间和功耗。

PSS（Proportional Set Size）把私有页全额计入，并按共享进程数分摊共享页；RSS（Resident Set Size）统计当前驻留在物理内存中的页，swap 是被换出的匿名内存。三者口径不同，应同时查看。Scudo 是 Android 使用的强化型原生堆分配器，分配与释放策略也会影响 MTE 的观测结果。

[§4.9](../../part1-fundamentals/ch04-memory/09-android17-memory-tagging-extension-mte.md) 讨论 MTE 的进程配置。

[§20.11](../../part5-app/ch20-stability/11-mte-gwp-asan-native-memory-safety.md) 讨论 MTE 崩溃检测与治理。这里仅限定内核能力与性能测量边界。

### 7. GCS：Android 17 内核提供用户态 ABI

GCS（Guarded Control Stack）为用户态线程维护一份受硬件保护的返回地址栈。`CONFIG_ARM64_GCS` 位于 ARMv9.4 架构特性菜单，6.18 Kconfig 将其设为 `default y`。这个配置让内核在硬件存在时提供 GCS 用户 ABI；它没有让 Linux 内核函数自动改用 GCS。

用户态通过 `HWCAP_GCS` 发现硬件与内核支持，再按线程调用 `prctl(PR_SET_SHADOW_STACK_STATUS, PR_SHADOW_STACK_ENABLE, ...)` 启用。新线程继承状态，`exec()` 会清除启用状态。

GCS 检查失败通过 `SIGSEGV` 和 `SEGV_CPERR` 上报；`/proc/<pid>/smaps` 是进程内存映射的详细视图，受保护栈页可在其中显示 `ss` 标志。

因此，`CONFIG_ARM64_GCS=y`、CPU 支持 GCS、Android runtime 或 native（原生）程序启用 GCS 是三件独立的事。没有进程侧证据时，不能把 GCS 开销计入应用，也不能给出每次调用固定周期数。

### 8. 设备核查方法

#### 8.1 核对构建与启动状态

工程构建可尝试读取压缩内核配置；量产设备往往不暴露 `/proc/config.gz`，此时应读取构建生成的 `.config` 或厂商发布的内核构建产物（kernel build artifact）。

```bash
adb shell 'test -r /proc/config.gz &&
  zcat /proc/config.gz |
  grep -E "CONFIG_(RANDOMIZE_BASE|UNMAP_KERNEL_AT_EL0|ARM64_PTR_AUTH|ARM64_BTI|ARM64_MTE|ARM64_GCS|SHADOW_CALL_STACK|CFI)="'
adb shell 'cat /proc/cmdline'
adb shell 'grep -E "paca|pacg|bti|mte|gcs" /proc/cpuinfo'
```

配置回答“内核是否编入支持”，命令行回答“启动时是否覆盖策略”，`/proc/cpuinfo` 的 CPU features 回答“内核向用户态公布了哪些能力”。三者缺一时，结论应保留条件。

#### 8.2 为工作负载建立归因

性能审计应按路径选择指标。下表中的 PMU（Performance Monitoring Unit）事件是 CPU 硬件计数器记录的周期、分支、缓存或 TLB 等事件；事件名称和可用范围由 SoC 决定。

| 怀疑对象 | 适合的负载 | 需要记录 |
|---|---|---|
| KASLR | 冷启动与内核阶段启动 | 同一镜像的启动阶段时间点、重定位日志、样本分布 |
| KPTI | 高频短系统调用、Binder、网络、存储 | 系统调用率、内核/用户 CPU time、调度与 TLB 相关 PMU 事件 |
| Spectre v2/BHB | 频繁进出内核、间接分支密集路径 | CPU 型号、漏洞状态、固件版本、分支预测相关 PMU 事件 |
| PAC/BTI/SCS/KCFI | native 与内核控制流密集负载 | 指令数、cycles、branch miss、文本大小、调用栈分布 |
| MTE | native 分配与访存密集负载 | fault mode、分配器指标、PSS/RSS、CPU time、功耗 |
| GCS | 明确启用 GCS 的 native 进程 | 线程状态、`smaps`、调用密度、fault 记录 |

`simpleperf` 适合核对指令、周期和分支事件，Perfetto 适合把调度、Binder、缺页、I/O 与业务阶段放到同一时间轴。PMU 事件名称随 SoC 和内核权限变化，采集前应运行 `simpleperf list`，只使用设备公布的事件。

下面的命令用于确认设备支持的事件，再对一个可重复的 native workload（原生测试负载）采样。

```bash
adb shell simpleperf list
adb shell simpleperf stat \
  -e task-clock,cycles,instructions,branches,branch-misses \
  -- /data/local/tmp/security_bench
```

输出可用于计算 IPC（instructions per cycle，每周期指令数；这里不是进程间通信）、每次业务操作消耗的 cycles（CPU 周期数）和 branch-miss（分支预测失败）比例。一次采样不足以归因，需要预热、固定业务输入并记录温度与频率状态。

#### 8.3 A/B 测试的安全边界

关闭缓解只适用于隔离实验室中的可丢弃工程镜像。测试设备不得承载账号、密钥、个人数据或生产网络访问。每个实验只改一个因素，并保留完整的 boot image、内核配置、启动参数和固件版本。

6.18 文档中与 ARM64 相关的参数如下：

| 参数 | 6.18 定义 | 审计提示 |
|---|---|---|
| `nokaslr` | 关闭内核与模块 base offset ASLR | 独立于 `mitigations=off` |
| `kpti=0` / `kpti=1` | 强制关闭或开启页表隔离 | 默认值是“在需要缓解的核心上开启” |
| `nospectre_v2` | 关闭 ARM64 Spectre v2 缓解 | 会暴露数据泄漏风险 |
| `nospectre_bhb` | 关闭 ARM64 Spectre-BHB 缓解 | 会暴露数据泄漏风险 |
| `ssbd=force-off` | 关闭 Speculative Store Bypass 缓解 | 与 Spectre v1/v2 分开 |
| `arm64.nopauth` | 关闭 Pointer Authentication 支持 | 影响内核公布与使用该能力 |
| `arm64.nomte` | 关闭 MTE 支持 | 影响内核公布与使用该能力 |
| `mitigations=off` | 关闭一组可选 CPU 漏洞缓解 | 不会自动关闭 KASLR |

`nospectre_v1` 在该文档中只标记为 x86 与 PowerPC 参数，不能列入 ARM64 测试方案。旧写法 `nopti` 也不应替代 ARM64 文档明确给出的 `kpti=0`。

每组测试应执行多轮并交错顺序，报告中给出分位数、离散程度和热状态。若差异小于样本噪声，应记录为“当前负载未检出差异”，避免把微基准结果外推到整机体验。

### 9. 应用与系统性能优化边界

应用开发者通常不能改变内核缓解策略，也不应通过关闭安全机制换取分数。性能工作可以从可控路径入手：

- 用 Perfetto 统计 Binder transaction（一次 Binder 驱动事务）、系统调用、I/O 和调度等待，确认时间花在哪个阶段；
- 批量 Binder 请求前先检查接口语义、错误处理和延迟预算，避免只为减少调用次数扩大单次事务；
- 共享内存适合大块数据传输，但同步、生命周期、权限和一致性成本需要计入；
- native 热点应根据 profile（采样或剖析结果）决定内联、数据布局或间接调用调整，不能为了躲避 KCFI/BTI 破坏类型安全；
- NDK 库启用 branch protection（PAC/BTI 分支保护）时，要核查全部静态库、共享库和装载路径的兼容性；
- MTE 的同步模式适合需要精确故障地址的验证阶段，生产策略要结合崩溃治理、性能和设备覆盖率。

Android NDK 的 Native APIs 文档没有把 `io_uring` 列为 Android 原生 API。直接调用 `io_uring` 面对的是 Linux kernel UAPI，即内核与用户空间之间的底层接口。

即使某个 GKI 构建含有实现，SELinux 强制访问控制、seccomp 系统调用过滤器、系统调用可用性和 Android API 兼容边界仍可能限制普通应用。只有在目标设备、应用沙箱和兼容范围都经过验证后，才能把它作为特定场景方案。

### 10. 核查清单

- [ ] 平台结论锚定 `android-17.0.0_r1`，内核结论锚定 `android17-6.18-2026-06_r6`
- [ ] 使用最终 `.config`，没有把 Kconfig 的 `default y` 写成设备启用证明
- [ ] 同时记录 CPU 型号、固件版本、启动参数和漏洞状态节点
- [ ] 没有把 BTI 写成 Spectre v2 或 Retpoline 的替代机制
- [ ] 没有把 SSBS 写成 Spectre v1 的通用屏障
- [ ] PAC kernel 的范围限定为返回地址保护
- [ ] SCS、KCFI、PAC、BTI 与 GCS 的保护对象分开说明
- [ ] MTE 标签位数没有直接换算成固定 PSS 增量
- [ ] 性能数字来自当前设备、当前镜像和可复现测试负载
- [ ] 关闭缓解的对照实验只在隔离工程设备上执行

### 11. ARM64 核查入口

- [ARM64 Kconfig：KPTI、BHB、PAC、BTI、MTE、GCS 与 KASLR](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/Kconfig)
- [Android 17 GKI `gki_defconfig`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig)
- [通用 arch Kconfig：Shadow Call Stack 与 KCFI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/Kconfig)
- [ARM64 KASLR 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/kaslr.c)
- [ARM64 Spectre 与 SSBD 运行时实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/proton-pack.c)
- [通用 `array_index_nospec()`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/nospec.h)
- [ARM64 `array_index_mask_nospec()` 与 `CSDB`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/include/asm/barrier.h)
- [ARM64 异常入口实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/kernel/entry.S)
- [Linux 6.18 启动参数](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/kernel-parameters.txt)
- [ARM64 Pointer Authentication 用户 ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/pointer-authentication.rst)
- [ARM64 Memory Tagging Extension 用户 ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/memory-tagging-extension.rst)
- [ARM64 Guarded Control Stack 用户 ABI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/arch/arm64/gcs.rst)
- [Android MTE 进程配置](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [Android NDK Native APIs](https://developer.android.com/ndk/guides/stable_apis)

## 小结

Android 17 的 GKI 6.18 需要按调度、存储、页面回收和构建优化分别确认配置与运行状态；源码中存在机制不等于设备已经采用。ARM64 安全特性又受最终 `.config`、CPU/固件能力、启动参数和进程启用方式共同约束。性能对照必须保持这些条件一致，并以目标工作负载的调度、I/O、PMU、内存与安全状态证据判断成本，不能用关闭缓解的工程镜像替代量产结论。

## 参考资料

- [Android 17 GKI 6.18 release builds：r6 tag 与 SHA](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)
- [`android15-6.6` 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android15-6.6)
- [`android16-6.12` 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12)
- [`android17-6.18-2026-06_r6` 源码根目录](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
- [r6 `Makefile`：Linux 6.18.21](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Makefile)
- [r6 GKI `gki_defconfig`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig)
- [EEVDF 内核文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-eevdf.rst)
- [r6 fair scheduler 源码](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [sched_ext 内核文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-ext.rst)
- [r6 sched_ext 源码](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c)
- [F2FS 内核文档：`checkpoint_merge`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/f2fs.rst)
- [r6 F2FS `fsync()` 判定路径](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/f2fs/file.c)
- [r6 F2FS checkpoint 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/f2fs/checkpoint.c)
- [r6 io_uring 源码目录](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/io_uring/)
- [dm-verity r6 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/md/dm-verity-target.c)
- [dm-verity multi-buffer hashing v8 patch 与测试口径（未合入 r6）](https://lists.infradead.org/pipermail/linux-arm-kernel/2025-February/1000047.html)
- [MGLRU 内核文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/mm/multigen_lru.rst)
- [Android lmkd：内存压力信号与回收策略](https://source.android.com/docs/core/perf/lmkd)
- [AOSP `lmkd.cpp` Android 17 tag](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [r6 AutoFDO profile README](https://android.googlesource.com/kernel/common/+show/refs/tags/android17-6.18-2026-06_r6/gki/aarch64/afdo/README.md)
- [Android Developers Blog：Kernel AutoFDO 投放与采集流程](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)
- [AOSP `external/liburing` Android 17 `Android.bp`](https://android.googlesource.com/platform/external/liburing/+/refs/tags/android-17.0.0_r1/Android.bp)
