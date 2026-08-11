---
title: "Android 17 Kernel 6.18 性能机制与验证"
section: "16.4"
chapter: "16.4"
status: finalized
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
reviewed_date: 2026-07-09
reviewed_by: openclaw-task6
task6_review_date: "2026-06-16"
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
last_task9_at: "2026-07-13T19:23:00+08:00"
task9_reviewed_date: "2026-07-09"
task9_reviewed_by: "openclaw-task9"
task9_review_notes: "2026-07-09 05:56 Task9 deep-review: auto-fixed P0 1 (AutoFDO 官方博客引用 URL 404 -> 编码后正确地址); P1 0 / P2 1; 已写入 suggestions,回到 Task6 复审。"
last_task9_audit: 2026-07-09
last_task9_audit_at: "2026-07-09T03:26:14+08:00"
last_task9_review_log: "logs/deep-review/2026-07-13-19-deep-review.md"
last_task9_audit_result: auto-fixed-p0-source-anchor-p1-version-drift
task9_audit_notes: "2026-07-09 Task9 idle audit: AUTO-FIX P0 1 / P1 1; 修正 DeliQueue Android 17 tag 源码锚点为 CombinedMessageQueue/MessageQueue.java,同步 android17-6.18 Makefile 6.18.24 与 AFDO profile 6.18.21 边界,回到 Task6 复审。"
last_task2b_at: "2026-06-16T08:51:39+08:00"
last_task6_at: "2026-07-13T17:17:00+08:00"
last_task6_review_log: "logs/review/2026-07-13-15-review.md"
task6_review_notes: "2026-07-13 Task6 revisiting review: pass-light-edit。修复多处标点符号统一（半角冒号/分号→全角冒号/分号、半角括号→全角括号），删除冗余表达，保证全书风格一致性。L1 禁用词全文未命中。Task9 idle audit auto-fixed 已验证。Outline 9/9 覆盖。无 B 类回炉项。task9_result=auto-fixed (P0 1/P1 0/P2 1 已处理），queue 无 pending，自动晋升 finalized。"
last_task2b_verifier_at: "2026-07-09T03:31:26+08:00"
task2b_verifier_notes: "2026-07-09 Task2B Verifier: status finalized→ready-for-review; Task9 idle audit auto-fixed (P0 1/P1 1), pipeline task6_pending + task6_state revisiting correct, status was stale finalized."
last_task6_audit: "2026-07-13"
pipeline_stage: ready-to-publish
last_task6_audit_log: "logs/review/2026-05-24-23-audit.md"
last_task6_audit_notes: "idle audit: 补充缺失 outline 大纲;L1 禁用词正文未命中;frontmatter 完整;outline 锚点覆盖 9/9;无回炉项。"
applicable_versions: "Android 17 (API 37)"
tags:
  - android
  - linux
  - research
sources:
  - type: blog
    path: "https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html"
  - type: docs
    path: "https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android15-6.6"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6"
review_notes: "2026-04-27 Task2B:修正 EEVDF 版本分界,拆开 Android 17/API37 与 android16-6.12 GKI branch,补 DeliQueue 源码锚点并降级 io_uring 用户态采用结论;2026-04-28 task9 deep-review: needs-rework。P1 1(AutoFDO 量化数据需回源限定)。;2026-05-04 task9 deep-review: needs-rework。P0 3 / P1 1 / P2 1。sched_ext 源码级补充混入 `android16-6.12` 不存在/不匹配的路径与符号;AutoFDO 量化数据仍需回源限定。;2026-05-04 task2b: 修正 sched_ext 源码锚点(ext_internal.h→ext.c)、SCX_OPSS_*→SCX_TASK_*、scx_bpf_dsq_insert→scx_bpf_dispatch、AutoFDO 精确数据降级为官方可核验口径;2026-05-04 Task6 revisiting: needs-rework。L1/L2 小修:修正禁用词、表格格式、边界措辞;B 类问题:sched_ext DSQ enum/version 边界与 MGLRU 数据来源/默认启用口径需 Task9/Task2B 复核。 | 2026-05-06 task9 deep-review: needs-rework。P0 3 / P1 2 / P2 0;sched_ext 路径/符号/sysfs 与 android16-6.12 不匹配,MGLRU 量化数据仍需回源。 | 2026-05-07 Task9 00:20:needs-rework。P0 2 / P1 1 / P2 0;DSQ enum 摘录、F2FS checkpoint_merge/fsync 口径、MGLRU 与 LMKD 协同需回炉。 | 2026-05-07 Task9 02:20:pass-tech-review。P0 0 / P1 0 / P2 1;DSQ/F2FS/MGLRU 已处理,Perfetto dm-verity 观察口径写入 suggestions;Task6 已通过且 queue 无 pending,自动晋升 finalized。 | 2026-05-26 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2;sched_ext dsq_insert 版本边界残留说明与 AutoFDO 官方链接写入 suggestions;Task6 已通过且 queue 无 pending,自动晋升 finalized。"

deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-14
last_task9_autofix_at: "2026-07-09"
task2b_result: "verified"
task2b_state: "fixed"
task2b_fixed_at: "2026-06-16T08:51:39+08:00"
task2b_fixed_by: "task2b-main"
task6_state: reviewed
last_idle_audit_at: "2026-07-27T10:35:11+08:00"
last_idle_audit_run_id: "20260727-103511-idle-audit-5f410a75"
last_idle_audit_result: pass-metadata-source-boundary-fix
last_idle_audit_log: "logs/audit/2026-07-27-20260727-103511-idle-audit-5f410a75-idle-audit.md"
last_verified: "2026-08-11"
confidence: high
consolidated_from:
  - "16.4 中重复的 ART generational CMC 与 DeliQueue 内容移至 16.5"
task2b_verification_note: "2026-06-16 验证 android17-6.18 gki/aarch64/afdo/README.md 原文，正文 AutoFDO benchmark 数据准确。清除版本演进表的待确认标注，补充 Binder benchmark 多次运行最佳结果取值限定。"
---

# Android 17 Kernel 6.18 性能机制与验证

## 为什么要把平台和内核分开

核验使用两个固定锚点：

- Android 平台：Android 17 / API 37 / `android-17.0.0_r1`；
- Android common kernel：`android17-6.18-2026-06_r6`，其 `Makefile` 版本为 6.18.21。

`android15-6.6` 与 `android16-6.12` 只用于解释 EEVDF、sched_ext 和 AutoFDO 的演进，不作为 Android 17 当前实现结论。平台行为也不应从内核分支名推导：Android 17 的 generational CMC 与 lock-free `MessageQueue` 位于 ART 和 `frameworks/base`，它们不属于 Linux 6.18 的调度或存储改动。

GKI（Generic Kernel Image）把通用内核与板级 vendor modules 分开，并以 KMI 约束模块接口。设备采用 `android17-6.18-2026-06_r6` release build，还需要相容的 vendor modules、产品配置和启动参数。源码 tag 中存在某个功能，无法单独证明设备已经启用它。

## Android 17 / 6.18 的核查表

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

设备测试记录至少应包含 platform build、kernel release、GKI tag 或 build ID、vendor boot、挂载参数、CPU 拓扑、温度、benchmark 输入和样本统计。缺少这些信息时，结果只适合做该设备的排查线索。

## 调度器变革：EEVDF fair scheduler + sched_ext 可扩展框架

### EEVDF：fair scheduler 的 lag / deadline 模型

Linux 从 6.6 开始向 EEVDF 过渡。Android 17 的 6.18 `kernel/sched/fair.c` 保留 `entity_eligible()`、`pick_eevdf()` 和 virtual deadline 相关路径，因此 6.12 不能写成 EEVDF 的 Android 17 分界点。

同优先级 runnable entity 仍按权重分享 CPU。调度器用 lag 表示 entity 相对公平份额的欠账或超额服务：lag 大于等于零时具备 eligibility，再从 eligible 集合中选 virtual deadline 更早的对象。较短的请求 slice 可以获得较早 deadline，这为延迟敏感任务提供了表达空间。

这套模型不会识别“UI 线程”或 `doFrame` 语义，也不会保证短任务总能抢占后台任务。Android 结果还受 nice、uclamp、cpuset、CPU affinity、thermal、frequency selection、RT/DL class 和厂商调度扩展影响。评估 EEVDF 时应测 wakeup-to-running、runnable delay、slice 与 preemption，而非只看总 CPU time。

### sched_ext：用 BPF 实现可扩展调度器

sched_ext 在 Linux 6.12 进入 mainline，允许一组 BPF `struct_ops` 程序实现调度策略。Android 17 GKI 开启 `CONFIG_SCHED_CLASS_EXT=y`，但文档明确规定：**BPF scheduler 加载并运行后，sched_ext 才会使用**。只看到配置项或 `kernel/sched/ext.c`，不能声称设备已经由自定义调度器接管。

### sched_ext 源码结构与 OEM 采用边界

6.18 的核心实现和文档分布如下：

- `kernel/sched/ext.c` 负责 scheduler class、BPF kfunc、启停与错误回退；
- `include/linux/sched/ext.h` 定义 `sched_ext_entity`、DSQ 标志和任务状态；
- `tools/sched_ext/` 提供示例调度器和状态工具；
- `Documentation/scheduler/sched-ext.rst` 描述启用条件、DSQ 与故障回退。

BPF scheduler 通过 `struct sched_ext_ops` 提供 `select_cpu()`、`enqueue()`、`dispatch()` 等可选回调，只有 `ops.name` 必填。`select_cpu()` 的结果是优化提示；最终 CPU 仍受任务 cpumask 与调度核心校验约束。

任务先进入 dispatch queue（DSQ）。6.18 提供全局 FIFO `SCX_DSQ_GLOBAL`、每 CPU 的 `SCX_DSQ_LOCAL`，BPF scheduler 也可创建自定义 DSQ。CPU 取任务时依次检查本地 DSQ、全局 DSQ，再调用 `ops.dispatch()`。自定义 DSQ 可按 FIFO 或 `dsq_vtime` 排序。

6.18 的插入接口为 `scx_bpf_dsq_insert()` 与 `scx_bpf_dsq_insert_vtime()`。6.12 示例中的旧名 `scx_bpf_dispatch()` / `scx_bpf_dispatch_vtime()` 只适合阅读旧分支，移植时应按目标 tag 编译，避免从函数名猜版本。

sched_ext 的安全回退是运行边界的一部分。BPF scheduler 退出、runnable task stall、内部错误或 `SysRq-S` 都会让任务回到 fair class；`sched_ext_dump` tracepoint 可读取诊断 dump。

下面的命令用于确认设备是否加载过 BPF scheduler。量产设备可能因权限或裁剪而无法读取这些节点。

```bash
adb shell 'cat /sys/kernel/sched_ext/state 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/root/ops 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/enable_seq 2>/dev/null'
```

`state` 表示当前启停状态，`root/ops` 给出当前调度器名称，单调递增的 `enable_seq` 大于零表示本次启动后曾经加载过 BPF scheduler。节点不存在时，只能说明当前设备没有暴露这组 ABI，还需结合内核配置和厂商实现核查。

## 存储栈三项核查

F2FS、dm-verity 和 io_uring 位于不同层级。三个子系统都存在于 6.18 tag，但某项上游补丁存在，不代表 r6 已经合入，也不代表 Android 17 设备或应用走到了相应路径。

### F2FS checkpoint merge：先确认挂载选项

F2FS 的一次 `fsync()` 不必然触发完整 checkpoint。需要 checkpoint 时，`checkpoint_merge` 可把并发请求交给 `issue_checkpoint_thread` 处理，减少各调用进程重复发起 checkpoint，并避免请求受调用进程 cgroup I/O budget 和 CPU shares 长时间拖延。

6.18 r6 的 `fs/f2fs/super.c` 解析 `checkpoint_merge` / `nocheckpoint_merge`，默认挂载选项会设置 `MERGE_CHECKPOINT`。可写挂载且没有禁用 checkpoint 时，checkpoint kthread 才会启动；`nocheckpoint_merge` 会停止这条路径。`fs/f2fs/checkpoint.c` 中的 `f2fs_issue_checkpoint()`、`issue_list`、`queued_ckpt` 与 `ckpt_wait_queue` 构成请求与等待路径。

检查设备时应读取 `/proc/mounts` 或 `/proc/self/mountinfo`，确认 data 分区的文件系统和挂载参数。SQLite WAL commit 会调用同步写入，但一次 commit 是否进入 F2FS checkpoint 路径，取决于文件系统状态和 `f2fs_do_sync_file()` 的判定。不能从“应用调用了 fsync”直接推出 checkpoint merge 收益。

### io_uring：内核实现不是 Android 应用契约

6.18 r6 的 `io_uring/` 包含 multishot、registered buffers、ring setup 和 zero-copy 相关路径。每项能力都有自己的 opcode、flag、内存注册和 fallback 条件；`IORING_SETUP_NO_MMAP` 描述 ring 内存的建立方式，不代表应用数据已经 zero-copy。

AOSP 的 `external/liburing` 提供 native 静态库构建规则，但这不能证明 SQLite、Cronet、OkHttp 或 Java I/O 在 Android 17 默认使用 io_uring。普通应用还受 syscall 可用性、seccomp、SELinux、NDK API 与设备内核配置约束。缺少调用栈或 syscall 证据时，不能把 io_uring 计入应用收益。

### dm-verity multi-buffer hashing：r6 未合入

逐行核对 r6 的 `drivers/md/dm-verity-target.c`，当前实现是 `verity_hash()` 配合 `crypto_shash_finup()` 等单请求接口。该文件没有 `verity_hash_mb()`，r6 源码树也没有这条路径使用的 `crypto_shash_finup_mb()`。

2025 年发布到邮件列表的 v8 补丁曾报告 ARM64 与 x86_64 cold-cache dm-verity read 吞吐约提升 35%，作者也说明指标波动较大。它是补丁环境的测试结果，不能写入 `android17-6.18-2026-06_r6` 的收益表，更不能改写为 Android 17 安装、冷启动或 OTA 固定提升。

### 存储路径如何测

三项机制应分别测量：

- F2FS：`f2fs_sync_file_enter/exit`、checkpoint 数量、checkpoint 时长、块写入量与挂载参数；
- dm-verity：cold/warm cache 分开，记录当前 hash driver、数据块大小、CPU time 与块设备吞吐；评估 multi-buffer 补丁必须使用明确包含补丁的自定义内核；
- io_uring：确认 `io_uring_setup`、`io_uring_enter`、opcode 和 fallback，再比较每次业务操作的提交数与延迟。

Perfetto 可采集 `block_rq_issue` / `block_rq_complete` 和 F2FS tracepoints。dm-verity 没有一个可通用于所有 Android 设备的“dm-verity track”；需要把 block I/O、CPU sampling 和 `verity_*` 调用栈放在同一业务区间内分析。

## AutoFDO Profile-Guided Optimization 的内核应用

AutoFDO 用采样得到的执行 profile 指导 Clang 的内联、分支概率和代码布局决策。Android 17 GKI `gki_defconfig` 设置 `CONFIG_AUTOFDO_CLANG=y`，r6 tag 的 `gki/aarch64/afdo/` 同时包含 README 与 `kernel.afdo`。

### r6 tag 中可引用的数据

README 说明 profile 采自 kernel 6.18.21，测试设备是 Pixel 8。结果被标记为 preliminary，因为该设备当时还没有针对这版内核完成电源管理、CPU frequency scaling 和调度调优。

| Benchmark | README 报告的 improvement | 限定 |
|---|---:|---|
| Boot time | 1.1% | Pixel 8 preliminary result |
| Cold App launch time | 6.6% | Pixel 8 preliminary result |
| Binder-rpc | 15% | 多轮中的最佳结果 |
| Binder-addints | 23% | 多轮中的最佳结果 |
| Hwbinder | 23% | 多轮中的最佳结果 |

Binder 三项使用最佳单轮结果，不能与 boot、launch 或统计分位数按同一置信度解读。README 也没有给出跨 SoC、跨产品或功耗收益。

2026 年 3 月的 Android Developers Blog 当时只描述 6.6 与 6.12 的投放，并把 6.18 写为后续计划；6 月 r6 tag 中的 profile 证明计划已经进入这个 release build。引用时应使用 r6 tag 证据，不再沿用博客发布时的未来时态。

### profile 从采集到构建

r6 README 给出的流程是：

1. 在 Pixel 设备运行热门应用的 launch 与 crawler workload；
2. 使用 CoreSight ETM 或 ARM ETE 记录内核指令流；
3. 合并样本并转换为 LLVM AutoFDO profile；
4. 构建时用 `kernel.afdo` 指导 vmlinux 优化；
5. 用目标 benchmark 检查性能与回退。

它优化的是 GKI 内核编译产物。ART AOT、Baseline Profile 和 cloud compilation 属于用户态编译链，二者可以同时影响一次冷启动，却没有一个可直接相加的收益模型。

确认设备收益时，要先证明设备内核由对应 profile 构建。只看到源码目录中的 `kernel.afdo` 还不够；还需关联 GKI release artifact、build config 与设备运行的 kernel build ID。严格 A/B 应保持源码、配置、工具链和设备一致，只改变是否应用 profile。

ART generational CMC 与 DeliQueue 属于平台运行时和 Framework，不是 Kernel 6.18 能力。它们的 gate、源码和测试方法统一由 16.5 承载，本节只在 A/B 设计中把 ART/Framework build 视为必须固定的控制变量。

## MGLRU 与页面回收优化

Multi-Gen LRU 是 Linux 的另一套页面回收实现。Android 17 GKI r6 的 `gki_defconfig` 同时设置 `CONFIG_LRU_GEN=y` 与 `CONFIG_LRU_GEN_ENABLED=y`，所以 GKI 默认配置已选择它。设备仍可通过产品配置或运行时开关形成差异。

### generation 表示访问时间窗口

MGLRU 为 memcg 与 NUMA node 维护多代页面。aging 扫描页表访问位等信号，把近期访问的页面放入较新的 generation；reclaim 从较老 generation 选择候选。`min_gen_nr` 到 `max_gen_nr` 形成按时间窗口划分的 working-set histogram。

generation 主要表达 recency，不能简化为“每秒访问次数”。MGLRU 文档还包含 refault、匿名页与文件页选择、swappiness 和不同访问渠道的处理。它对顺序扫描、匿名内存、文件缓存与 swap 的表现需要结合 workload 解释。

运行时 stable ABI 位于 `/sys/kernel/mm/lru_gen/`。下面的命令用于读取主开关；权限不足时应改从内核配置和厂商诊断产物核查。

```bash
adb shell 'cat /sys/kernel/mm/lru_gen/enabled 2>/dev/null'
```

结果是位掩码。`0x0001` 表示主功能开启，其余位控制批量清除页表 accessed bit 的能力；设备是否支持这些位还受架构 MMU 特性影响。

### 与 lmkd 的关系是间接影响

`lmkd` 根据 PSI、内存水位、thrashing 与进程 `oom_score_adj` 等信息决策，不读取 MGLRU generation 来挑选进程。MGLRU改变内核 reclaim 的页面选择和成本，进而可能改变 PSI stall、refault、swap 与可用内存；这些变化才会影响 `lmkd` 所见的压力。

“MGLRU 开启后 kill 次数必然下降”没有源码保证。某些负载可能减少 refault 和 `kswapd` CPU，另一些负载可能因 swap、file cache 或 reclaim 参数呈现不同结果。对照实验应同时记录：

- `/proc/pressure/memory` 的 `some` / `full` stall；
- `mm_vmscan_*` 事件、`kswapd` CPU time 与 direct reclaim；
- major/minor fault、workingset refault、swap in/out；
- lmkd kill reason、被杀进程的 `oom_score_adj` 与进程状态；
- 相同业务脚本下的帧、启动与进程留存结果。

## 在 Perfetto 中的可观测性

Perfetto 展示运行结果，不会仅凭一条 track 告诉你“EEVDF、MGLRU 或 AutoFDO 带来了多少收益”。需要把机制状态、trace 和 A/B 构建关联起来。

| 主题 | 采集项 | 能回答的问题 |
|---|---|---|
| EEVDF | `sched_waking`、`sched_switch`、线程优先级、CPU frequency、uclamp | 线程何时 runnable、等待多久、在哪个 CPU 运行 |
| sched_ext | sched tracks、`sched_ext_dump`、sysfs 状态、BPF scheduler 自有 trace | 自定义调度器是否启用、是否报错回退 |
| F2FS | `f2fs_sync_file_enter/exit`、checkpoint 事件、block request | 同步写与 checkpoint 分别耗时多久 |
| dm-verity | block request、CPU sampling、`verity_*` 栈 | r6 当前 cold read 卡在 I/O 或 hashing 的比例 |
| MGLRU | `mm_vmscan_*`、PSI、page fault、swap、lmkd 事件 | reclaim stall、refault 与 kill 如何变化 |

`sched_switch` 只能反映谁获得 CPU，不能还原 `pick_eevdf()` 的全部候选和 virtual deadline。`sched_ext_dump` 用于错误或主动 dump，也不等同于每次 BPF 调度决定的流水记录。需要细看策略时，应为目标 BPF scheduler 添加自己的 trace events。

### A/B 设计

直接比较 Android 16 与 Android 17 会同时改变 framework、ART、kernel、vendor、驱动和配置，无法归因到单个机制。可复现对照应遵循以下顺序：

1. 固定设备、固件、散热条件、业务输入和 kernel source；
2. 只改变一个配置、profile 或运行时开关；
3. 预热后交错执行多轮，避免一组测试总处于更冷或更热的阶段；
4. 报告中位数、尾延迟、离散程度、频率驻留与温度；
5. 把“没有检出差异”和“证明零开销”分开表述。

## 版本演进：把平台版本和 GKI 分支分开

| 维度 | 锚点 | 结论 |
|---|---|---|
| Android 15 相关 GKI | `android15-6.6` | fair scheduler 已有 EEVDF 路径；AutoFDO 后续投放到该 LTS 分支 |
| Android 16 相关 GKI | `android16-6.12` | sched_ext 进入 mainline 后可在该分支使用；早期 6.12 示例可能使用 `scx_bpf_dispatch*()` 命名 |
| Android 17 当前内核 | `android17-6.18-2026-06_r6`，Linux 6.18.21 | 使用 `scx_bpf_dsq_insert*()`；GKI 配置开启 sched_ext、AutoFDO 与 MGLRU；tag 含 6.18.21 AFDO profile |
| Android 17 平台 | `android-17.0.0_r1` / API 37 | 只作为实验控制变量；平台运行时变化见 16.5 |

F2FS checkpoint merge、MGLRU 与 io_uring 都有跨分支历史。dm-verity multi-buffer hashing 仍是 r6 之外的补丁证据，不能列入该 tag 的功能集合。

## 常见问题与误区

**“设备报告 6.18，所以正文里的全部机制都已启用。”**

kernel release 只能确定代码基线。还要查最终配置、挂载参数、BPF scheduler、CPU 能力、boot 参数和用户态采用。

**“EEVDF 会自动把 UI 线程排在后台任务前面。”**

EEVDF 使用 lag、slice 与 virtual deadline，不读取 Android UI 语义。UI 结果由调度属性、CPU 放置、频率、热状态和 runnable 竞争共同决定。

**“`CONFIG_SCHED_CLASS_EXT=y` 表示 OEM scheduler 正在运行。”**

该配置只编入框架。`/sys/kernel/sched_ext/state`、`root/ops` 与 `enable_seq` 才能提供当前或本次启动期间的加载证据。

**“MGLRU 开启后 lmkd 会按 generation 杀进程。”**

lmkd 仍按 Android 的压力与进程优先级策略决策。MGLRU 位于页面回收层，只能经 reclaim、PSI、refault 和可用内存间接影响 kill 条件。

## 参考资料

- [Android 17 GKI 6.18 release builds：r6 tag 与 SHA](https://source.android.com/docs/core/architecture/kernel/gki-android17-6_18-release-builds)
- [`android17-6.18-2026-06_r6` 源码根目录](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
- [r6 `Makefile`：Linux 6.18.21](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Makefile)
- [r6 GKI `gki_defconfig`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig)
- [EEVDF 内核文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-eevdf.rst)
- [r6 fair scheduler 源码](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [sched_ext 内核文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/scheduler/sched-ext.rst)
- [r6 sched_ext 源码](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/ext.c)
- [F2FS 内核文档：`checkpoint_merge`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/f2fs.rst)
- [r6 F2FS checkpoint 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/f2fs/checkpoint.c)
- [r6 io_uring 源码目录](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/io_uring/)
- [dm-verity r6 实现](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/md/dm-verity-target.c)
- [dm-verity multi-buffer hashing v8 patch 与测试口径（未合入 r6）](https://lists.infradead.org/pipermail/linux-arm-kernel/2025-February/1000047.html)
- [MGLRU 内核文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/mm/multigen_lru.rst)
- [r6 AutoFDO profile README](https://android.googlesource.com/kernel/common/+show/refs/tags/android17-6.18-2026-06_r6/gki/aarch64/afdo/README.md)
- [Android Developers Blog：Kernel AutoFDO 投放与采集流程](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)
- [AOSP `external/liburing` Android 17 tag](https://android.googlesource.com/platform/external/liburing/+/refs/tags/android-17.0.0_r1)
