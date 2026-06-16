---
title: "Android 17 + Kernel 6.12 系统级性能优化"
section: "16.4"
chapter: "16.4"
status: ready-for-review
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-06-16"
reviewed_by: openclaw-task6
last_task6_at: "2026-06-16T09:09:00+08:00"
task6_review_date: "2026-06-16"
task6_review_notes: "2026-06-16 Task6 复审：版本演进表 AutoFDO 数据已确认与官方 README 一致，L1/L2/L3/L4 全部通过，仅一项需确认标注已处理。"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task9_result: auto-fixed
last_task9_at: "2026-05-26T01:27:00+08:00"
task9_reviewed_date: "2026-05-26"
task9_reviewed_by: openclaw-task9
task9_review_notes: "2026-05-26 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2;sched_ext dsq_insert 版本边界残留说明与 AutoFDO 官方链接写入 suggestions;Task6 已通过且 queue 无 pending,自动晋升 finalized。"
last_task9_audit: 2026-06-16
last_task9_audit_at: "2026-06-16T06:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-16-06-audit.md"
last_task9_audit_result: auto-fixed-p1-source-drift
task9_audit_notes: "2026-06-16 Task9 idle audit: AUTO-FIX P1 1; android17-6.18 AutoFDO README 已更新到 6.18.21 与新 benchmark 口径,正文已同步后回到 Task6 复审。"
last_task2b_at: "2026-06-16T08:51:39+08:00"
last_task6_at: "2026-06-16T08:06:00+08:00"
last_task6_audit: "2026-06-16"
last_task6_audit_log: "logs/review/2026-05-24-23-audit.md"
last_task6_audit_notes: "idle audit: 补充缺失 outline 大纲;L1 禁用词正文未命中;frontmatter 完整;outline 锚点覆盖 9/9;无回炉项。"
applicable_versions: "Android 17 (API 37)"
tags:
  - android
  - linux
  - research
sources:
  - type: blog
    path: "Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel"
  - type: docs
    path: "Android GKI Kernel 架构文档"
  - type: kernel
    path: "AOSP kernel/common android15-6.6"
  - type: kernel
    path: "AOSP kernel/common android16-6.12"
  - type: kernel
    path: "AOSP kernel/common android17-6.18"
review_notes: "2026-04-27 Task2B:修正 EEVDF 版本分界,拆开 Android 17/API37 与 android16-6.12 GKI branch,补 DeliQueue 源码锚点并降级 io_uring 用户态采用结论;2026-04-28 task9 deep-review: needs-rework。P1 1(AutoFDO 量化数据需回源限定)。;2026-05-04 task9 deep-review: needs-rework。P0 3 / P1 1 / P2 1。sched_ext 源码级补充混入 `android16-6.12` 不存在/不匹配的路径与符号;AutoFDO 量化数据仍需回源限定。;2026-05-04 task2b: 修正 sched_ext 源码锚点(ext_internal.h→ext.c)、SCX_OPSS_*→SCX_TASK_*、scx_bpf_dsq_insert→scx_bpf_dispatch、AutoFDO 精确数据降级为官方可核验口径;2026-05-04 Task6 revisiting: needs-rework。L1/L2 小修:修正禁用词、表格格式、边界措辞;B 类问题:sched_ext DSQ enum/version 边界与 MGLRU 数据来源/默认启用口径需 Task9/Task2B 复核。 | 2026-05-06 task9 deep-review: needs-rework。P0 3 / P1 2 / P2 0;sched_ext 路径/符号/sysfs 与 android16-6.12 不匹配,MGLRU 量化数据仍需回源。 | 2026-05-07 Task9 00:20:needs-rework。P0 2 / P1 1 / P2 0;DSQ enum 摘录、F2FS checkpoint_merge/fsync 口径、MGLRU 与 LMKD 协同需回炉。 | 2026-05-07 Task9 02:20:pass-tech-review。P0 0 / P1 0 / P2 1;DSQ/F2FS/MGLRU 已处理,Perfetto dm-verity 观察口径写入 suggestions;Task6 已通过且 queue 无 pending,自动晋升 finalized。 | 2026-05-26 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2;sched_ext dsq_insert 版本边界残留说明与 AutoFDO 官方链接写入 suggestions;Task6 已通过且 queue 无 pending,自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-05-26-01-deep-review.md"
last_task6_review_log: "logs/review/2026-06-16-08-review.md"
task6_review_notes: "2026-06-16 Task6：Task9 闲时抽检 auto-fix（AutoFDO README 数据同步）回流后写作复审；发现版本演进表中 AutoFDO benchmark 数据与正文不一致（Boot 1.9% vs 1.1%, Cold App launch 3.4% vs 6.6%），已按正文修正并标注 [需确认]；B 类问题 1 项写入 queue，转 Task2B 复核。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-08
last_task9_autofix_at: 2026-06-16
task2b_result: "verified"
task2b_state: "fixed"
task2b_fixed_at: "2026-06-16T08:51:39+08:00"
task2b_fixed_by: "task2b-main"
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task2b_verification_note: "2026-06-16 验证 android17-6.18 gki/aarch64/afdo/README.md 原文，正文 AutoFDO benchmark 数据准确。清除版本演进表 [需确认] 标注，补充 Binder benchmark 多次运行最佳结果取值限定。"
---

# 16.4 Android 17 + Kernel 6.12 系统级性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 Kernel 6.12 / 6.18 相关性能变化的可核验边界
- 🔹 EEVDF fair scheduler 与 sched_ext 的调度器变化
- 🔹 F2FS checkpoint merge、io_uring 与 dm-verity 的存储栈优化
- 🔹 AutoFDO for GKI Kernel 的限定收益口径
- 🔹 ART 运行时优化与 DeliQueue lock-free MessageQueue
- 🔹 MGLRU 与 LMK 的协同边界
- 🔹 Perfetto 中验证 Kernel 6.12 优化的观察点
- 🔹 Android 平台版本与 GKI 分支的版本边界
- 🔹 常见误区与排查结论

## 为什么要了解 Android 17 + Kernel 6.12 的性能变化

升级系统版本后出现的冷启动、滑动和安装速度改善,常常来自内核与运行时的共同演进。GKI (Generic Kernel Image) 的价值,是把通用内核与 SoC / 板级代码分开:核心内核由 Google 提供 release build,厂商特定能力放进 vendor modules,并通过 stable KMI 约束接口。同一条 LTS / Android 分支内的内核更新更容易独立交付,但某台设备能否收到更新,仍取决于它是否采用兼容的 GKI release build,以及 vendor modules 是否满足对应 KMI 边界。

本节把三类事实分开写。第一类是 ACK / GKI 源码分支事实,例如 `android15-6.6`、`android16-6.12`、`android17-6.18` 中 `kernel/sched/fair.c`、`fs/f2fs/`、`drivers/md/dm-verity-target.c` 的实现变化。第二类是 Android 17 / API 37 平台行为,例如 targetSdk 37 应用启用新的 lock-free `MessageQueue`。第三类是 GKI 分支与 Android 平台版本的对应关系:`android16-6.12` 和 `android17-6.18` 是两条并行的 GKI release branch,后者 Makefile 为 6.18.21,是当前 Android 17 的 common-kernel 分支。不能把 Android 17 / API 37 平台行为与 `android16-6.12` 内核线绑定过紧。

调度器、存储栈、编译优化、内存管理是 Kernel 6.12 相关变化的四条主线。凡是缺少官方公开数据或源码采用证据的性能数字,只保留为待验证线索,不写成确定收益。

## Kernel 6.12 的性能全景

公开资料里的性能数字来自不同来源,不能混成一张"Android 17 必然收益"表。这里按可核验程度拆开。

| 类别 | 来源 | 本节采用口径 |
|------|------------|--------------|
| AutoFDO for GKI | Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel;`android15-6.6` 与 `android16-6.12` 的 GKI AFDO 目录 | 保留官方公开的 cold start 与 Binder microbenchmark 数据,限定在对应 GKI profile / build。 |
| DeliQueue | Android Developers Blog: Under the hood: Android 17's lock-free MessageQueue;Android 17 MessageQueue behavior change | 保留内测设备上的 lock contention、missed frames 与 first frame P95 数据,限定在 targetSdk 37+ 新 `MessageQueue`。 |
| dm-verity multi-buffer hashing | `android16-6.12/drivers/md/dm-verity-target.c` 与 multi-buffer hashing patch discussion | 写成 ARM64 cold-cache read / hash throughput 改善,不推导到所有安装、启动或 OTA 场景。 |
| F2FS / io_uring / MGLRU | `fs/f2fs/`、`io_uring/`、MGLRU patch discussion | 以机制和可观测指标为主;未能逐项溯源的全局百分比删除。 |

对某台设备做验证时,至少要同时记录平台版本、GKI branch、kernel release、设备型号、benchmark 名称和样本口径。缺一项时,数据只能用于排查线索,不能当作跨设备结论。

## 调度器变革：EEVDF fair scheduler + sched_ext 可扩展框架

### EEVDF：fair scheduler 的 lag / deadline 模型

Linux fair scheduler 的 6.6 系列已经能看到 EEVDF 代码路径。复核 AOSP `kernel/common` 的 `android15-6.6/kernel/sched/fair.c`,`pick_eevdf()`、`entity_eligible()` 和 `place_entity()` 已存在;`android16-6.12/kernel/sched/fair.c` 继续保留这些路径。因此注意:`android16-6.12` 不是 EEVDF 从"可选"走向"默认"的分界。

本节把 CFS 当作 fair scheduler 子系统的历史名称使用;EEVDF 改的是 fair class 内部选择下一个 runnable entity 的策略。`update_curr()` 继续推进当前 entity 的 vruntime,`entity_lag()` / `entity_eligible()` 用实际服务时间与权重期望服务时间的差值判断 lag,`pick_eevdf()` 再从 eligible entity 中选择虚拟 deadline 最早的对象。正 lag 表示 entity 获得的 CPU 时间少于应得份额,负 lag 表示已经多拿了服务时间。

这个模型更利于移动设备的延迟控制。短任务(例如 UI 线程的 `doFrame` 回调)运行时间短,lag 更容易回到 eligible 区间,deadline 也更容易排到前面;后台长任务执行时间更长,lag 变负后会暂时退出候选集合,等 lag 恢复后再参与选择。

### sched_ext：用 BPF 实现可扩展调度器

EEVDF 优化了 fair scheduler 内部的调度决策,sched_ext 则从另一个方向打开调度能力——允许用 BPF 程序自定义调度策略,不必修改内核代码。

sched_ext 是 Kernel 6.12 合并的另一个调度器相关框架。它允许开发者用 BPF (Berkeley Packet Filter) 程序实现自定义调度策略,不需要修改内核代码。

不同场景对调度器的目标不同:游戏更重视延迟,数据库更重视吞吐,Android 更重视 UI 响应。sched_ext 让 OEM 或系统开发者可以为特定场景定制调度策略,但这类策略仍需要按设备和负载单独验证。

在 Android 17 的讨论里,sched_ext 的边界要单独写清。`android16-6.12` 的 sched_ext 实现在 `kernel/sched/ext.c`(单文件),常量和公开头文件在 `include/linux/sched/ext.h`,参考调度器示例在 `tools/sched_ext/`。这项能力提供给 OEM 和系统开发者做实验或定制,Google 官方构建仍以 fair scheduler / EEVDF 为主。若某个 ROM 启用了自定义 sched_ext 调度器并出现性能回退,排查方向是确认 sched_ext tracepoint 是否存在,再检查对应 BPF 调度器的行为。

`android17-6.18` 的 sched_ext kfunc API 已从 `scx_bpf_dispatch()` / `scx_bpf_dispatch_vtime()` 重命名为 `scx_bpf_dsq_insert()` / `scx_bpf_dsq_insert_vtime()`;参考调度器示例也同步更新了 API 调用。跨分支阅读源码或移植 BPF 调度器时,要注意这个命名差异。

### sched_ext 源码结构与 OEM 采用边界

以下内容基于 Linux 6.12 mainline 和 OnePlus SM8750 开源模块的公开源码。

#### 关键数据结构:`struct sched_ext_ops`

`kernel/sched/ext.c` 定义了 BPF 调度器的入口表(`struct sched_ext_ops` 在 android16-6.12 中位于此文件),所有调度回调均通过此结构注册:

```c
// kernel/sched/ext.c, android16-6.12(简化)
struct sched_ext_ops {
    s32 (*select_cpu)(struct task_struct *p, s32 prev_cpu, u64 wake_flags);
    void (*enqueue)(struct task_struct *p, u64 enq_flags);
    void (*dequeue)(struct task_struct *p, u64 deq_flags);
    void (*dispatch)(s32 cpu, struct task_struct *prev);
    void (*tick)(struct task_struct *p);
    void (*runnable)(struct task_struct *p, u64 enq_flags);
    void (*running)(struct task_struct *p);
    void (*stopping)(struct task_struct *p, bool runnable);
    // ... 还有 cgroup、cpu_acquire/release、init_task、exit_task 等回调
    const char *name;  // 唯一必填字段
};
```

这段结构的作用是把调度器的关键决策点暴露给 BPF 程序:`select_cpu()` 决定唤醒时的 CPU 选择,`enqueue()` 接收进入调度器的任务,`dispatch()` 再把待运行任务交回 CPU。

#### 任务所有权状态机

`include/linux/sched/ext.h` 与 `kernel/sched/ext.c` 共同定义了任务状态标志,通过 `p->scx.flags` 位字段管理任务在 SCX core 与 BPF 调度器之间的归属:

| 标志 | 含义 |
|------|------|
| `SCX_TASK_QUEUED` | 任务已被 BPF 调度器入队到某个 DSQ,等待 dispatch |
| `SCX_TASK_RESET_RUNNABLE_AT` | 任务即将重新变为 runnable 的过渡标记 |
| `SCX_TASK_DEQD_FOR_SLEEP` | 任务因睡眠被 dequeue |

任务的归属状态由 `p->scx.flags` 中的 `SCX_TASK_STATE_MASK` 位域和 `ops_state` 字段共同管理(`SCX_TASK_NONE` / `SCX_TASK_INIT` / `SCX_TASK_READY` / `SCX_TASK_ENABLED`),用于跟踪任务在 SCX core 与 BPF 调度器之间的生命周期。

这些标志位通过 `p->scx.flags` 管理,允许 SCX core 安全地处理 BPF 调度器的分发请求,避免已 dequeue 任务被重复 dispatch。

#### Dispatch Queue (DSQ) 机制

`include/linux/sched/ext.h` 定义了内置 DSQ ID,具体集合需要以目标分支实际源码为准:

```c
// android16-6.12 include/linux/sched/ext.h - 简化示意,仅列出常用内置 DSQ
enum scx_dsq_id_flags {
    SCX_DSQ_INVALID = SCX_DSQ_FLAG_BUILTIN | 0,  // 含 BUILTIN flag
    SCX_DSQ_GLOBAL  = SCX_DSQ_FLAG_BUILTIN | 1,  // 全局 FIFO 队列
    SCX_DSQ_LOCAL   = SCX_DSQ_FLAG_BUILTIN | 2,  // 每 CPU 本地队列
    SCX_DSQ_LOCAL_ON = SCX_DSQ_FLAG_BUILTIN | SCX_DSQ_FLAG_LOCAL_ON,
};
// 注意:LOCAL_ON 的 CPU 编码通过 SCX_DSQ_FLAG_LOCAL_ON 与 CPU 编码组合实现,
// 具体掩码定义以目标分支源码为准,此处省略。
// 省略项:SCX_DSQ_LOCAL_CPU_MASK 等,完整定义见源码。
```

> **版本差异**:`SCX_DSQ_BYPASS` 出现在后续 mainline(6.14+)和部分厂商分支,不属于 `android16-6.12` 通用内置 ID。如果在非 GKI 标准分支上看到 `SCX_DSQ_BYPASS`,说明该分支基于更新的 mainline。

调度周期的主线是:CPU 本地 DSQ → 全局 DSQ → `ops.dispatch()` 从 BPF 调度器取任务。

#### OnePlus hmbird_sched proc 接口(已验证开源部分)

OPPO/一加 SM8750 的 `vendor/oplus/kernel/cpu/sched_ext/main.c`(开源于 GitHub)提供了运行时调控接口:

- `/proc/hmbird_sched/scx_enable` - sched_ext 主开关(`int scx_enable`)
- `/proc/hmbird_sched/partial_enable` - 部分启用开关
- `/proc/hmbird_sched/cpuctrl_high/low` - CPU 管控阈值(55/40)
- `/proc/hmbird_sched/cpu7_tl` - CPU7 温度限流(70)
- `/proc/hmbird_sched/scx_gov_ctrl` - 调度器与 freq gov 协同开关
- `/proc/hmbird_sched/isolate_ctrl` - CPU 隔离控制
- `/proc/hmbird_sched/sched_ravg_window_frame_per_sec` - 125Hz 帧率窗口

这些参数暗示 OnePlus 使用 sched_ext 实现帧率稳定性优化(游戏场景)和 CPU 管控。BPF 调度策略主体可能以二进制固件分发,开源仓库仅含 proc 接口。

#### 参考调度器：scx_simple

`tools/sched_ext/scx_simple.bpf.c` 展示了两模式调度器实现:

- **FIFO 模式**:`scx_bpf_dispatch(p, SHARED_DSQ, SCX_SLICE_DFL, enq_flags)` 直接入队
- **vtime 模式**:`scx_bpf_dispatch_vtime(p, SHARED_DSQ, SCX_SLICE_DFL, vtime, enq_flags)` 按虚拟时间排序

> **版本差异**:`scx_bpf_dispatch()` 是 android16-6.12 使用的 API 名称;Linux 6.14+ / 部分厂商分支将其重命名为 `scx_bpf_dsq_insert()`。如果读者在非 GKI 标准分支上看到 `dsq_insert` 命名,说明该分支基于更新的 mainline。

用户态加载器(`scx_simple.c`)通过 libbpf 调用 `SCX_OPS_OPEN`/`SCX_OPS_LOAD`/`SCX_OPS_ATTACH` 注册调度器。

#### 排查要点

如果设备启用了自定义 sched_ext 调度器并出现性能问题,Perfetto 追踪中应关注:

1. `sched_ext_dump` tracepoint - BPF 调度器的退出信息和 debug dump
2. `/sys/kernel/sched_ext/state` - enabled/disabled 状态
3. `/sys/kernel/sched_ext/enable_seq` - 当前启用序号
4. `/sys/kernel/sched_ext/root/ops` - 当前注册的调度器名称
5. `nr_rejected`、`hotplug_seq` 等 sysfs 全局属性 - 可用于判断调度器是否在拒绝任务或经历热插拔

EEVDF 继续使用虚拟时间体系,但调度决策从"vruntime 最小"转向"eligible entity 中 virtual deadline 最早"。详见 5.1 节。

## 存储栈三项优化

Kernel 6.12 对 Android 存储栈引入了三项相互配合的优化:减少重复 checkpoint、提高完整性校验吞吐、扩展异步 I/O 能力。

### F2FS Checkpoint Merge:减少重复 checkpoint 写入

F2FS 是 Android 设备的主流文件系统(见 4.2 节)。它的 checkpoint 机制在 fsync()/sync() 路径需要 checkpoint 时,将 NAT(Node Address Table)、SIT(Segment Information Table)、CURSEG(Current Segment)等元数据刷盘--但并非每次 fsync 都触发完整 checkpoint,`f2fs_do_sync_file()` 会根据脏数据量和内部状态决定是否执行 checkpoint。如果多个线程同时触发需要 checkpoint 的 fsync,就会产生多次完整 checkpoint,带来冗余的元数据写入。

在 `android16-6.12` 中,源码锚点在 `fs/f2fs/super.c`、`fs/f2fs/checkpoint.c` 和 `fs/f2fs/f2fs.h`。`checkpoint_merge` 挂载选项开启后,`f2fs_issue_checkpoint()` 会把并发的 `CP_SYNC` 请求挂到 `cprc->issue_list`,再由 `issue_checkpoint_thread` 统一执行;`struct ckpt_req_control` 里还能看到 `queued_ckpt`、`ckpt_wait_queue` 和 `ckpt_thread_ioprio` 这些配套字段。机制上的要点是:多个同步 checkpoint 请求会被串到同一个 checkpoint 线程里统一落盘,各个进程不再各自触发一轮完整 checkpoint。

对 SQLite WAL 模式的 commit 性能有潜在影响(Android 中 SQLite 是最常见的同步 I/O 模式之一)。ContentProvider 写操作走 SQLite WAL + fsync 路径,当 fsync 触发 checkpoint 时,`checkpoint_merge` 可以将并发的 `CP_SYNC` 请求合并到 `issue_checkpoint_thread` 统一执行。具体写放大下降比例需要补齐设备、内核分支、挂载参数和写入模型后再写入正文。

### io_uring multishot 与 zero-copy:内核能力不等于框架默认采用

io_uring 是 Linux 5.1 引入的高性能异步 I/O 框架(6.3 节有基础介绍)。在 `android16-6.12/io_uring/` 中,可以核验 multishot、registered buffer、ring setup 等内核能力;`IORING_SETUP_NO_MMAP` 也能在 `io_uring/io_uring.c` 中找到。但这些能力要分三层看。

| 层级 | 可确认事实 | 写作边界 |
|------|------------|----------|
| 内核能力 | `android16-6.12/io_uring/` 包含 io_uring 实现,`IORING_SETUP_NO_MMAP` 是建环相关 flag | 它减少 ring 映射方式上的限制,不能直接等同于应用数据 zero-copy。 |
| 用户态库 | AOSP `platform/external/liburing/Android.bp` 提供 `cc_library_static { name: "liburing" }` | 这是外部 liburing 模块,Java / framework 默认路径不会自动获得该能力。 |
| Android 框架与常用库 | 需要逐项核验 Cronet、SQLite、OkHttp 是否在对应版本接入 io_uring | 没有源码采用证据时,只能写"具备潜在收益",不能写成默认收益。 |

multishot 的稳定结论是减少重复提交 SQE 的开销;zero-copy 的稳定结论要落到具体操作类型、registered buffers、send / receive zero-copy 支持和设备内核配置。对 App 性能分析来说,先看 trace 里是否真的出现 io_uring 相关 syscall / tracepoint,再判断网络或文件 I/O 是否使用了这条路径。

### dm-verity multi-buffer hashing：ARM64 吞吐提升 35%

dm-verity 是 Android 用于验证系统分区完整性的内核模块。传统路径按块计算哈希,热点函数是 `verity_hash()`。在 `android16-6.12` 中,对应源码文件是 `drivers/md/dm-verity-target.c`,多块哈希路径落在 `verity_hash_mb()`,shash 分支会调用 `crypto_shash_finup_mb(desc, data, len, digests, num_blocks)`,ahash 分支则保留逐块 fallback。

公开 patch 讨论给出的收益方向是 dm-verity / fsverity 的 cold-cache read 吞吐提升,ARM64 场景在 35% 左右。可以确认的结论是:6.12 把哈希热点从单块计算扩展到多块交错计算,对安装、首读和 OTA 校验这类需要连续完整性验证的路径更敏感。

### 三项优化的协同观察

这三项优化针对存储栈的不同层:

- **F2FS Checkpoint Merge**:文件系统层,减少重复 checkpoint 带来的元数据写入。
- **io_uring multishot / registered buffer 相关能力**:系统调用层,减少重复提交和部分数据搬运成本,前提是用户态组件实际采用。
- **dm-verity multi-buffer hashing**:块设备验证层,减少连续读场景下的哈希等待。

随机 I/O 延迟这类全局百分比需要完整 benchmark 条件支撑。缺少设备、内核分支、fio 参数、UFS 型号和样本口径时,本节不保留固定百分比。

Perfetto 中观察存储优化时,重点看三类信号:
- **block tracepoint**(`block:block_rq_issue` / `block:block_rq_complete`):单个 I/O 请求的延迟分布
- **f2fs tracepoint**(`f2fs:f2fs_sync_file_enter/exit`):fsync 延迟
- **dm-crypt/dm-verity track**:加密和验证耗时

## AutoFDO Profile-Guided Optimization 的内核应用

1.12 节介绍过 AutoFDO (Automatic Feedback-Directed Optimization) 的基本原理:用运行时的 CPU profiling 数据(硬件性能计数器采样)指导编译器做代码布局优化。Kernel 6.12 将 AutoFDO 的覆盖范围从用户空间扩展到了内核本身。

### 量化数据

Google 在官方博客中公开的 AutoFDO 覆盖 GKI 内核后的收益(限定口径):

- **冷启动延迟**:约 4% 改善(官方博客表述为 "up to 4% cold start improvement",覆盖 Pixel 设备在 `android15-6.6` 和 `android16-6.12` 分支上的 GKI build)
- **Binder microbenchmark**:官方博客提及 Binder 相关 microbenchmark 有显著改善,但未给出逐项精确百分比

> **版本差异**:部分第三方资料引用了更精确的分项数据(如 P50 4.3%、P95 6.8%、Binder-rpc 21.7% 等),但这些精确数字在当前可访问的官方博客正文中无法逐一核验。本节保留官方公开口径,分项数据可在 Google 内部的 GKI profile 仓库或后续公开 benchmark 中进一步确认。

`android17-6.18` 分支的 `gki/aarch64/afdo/README.md` 公开了基于 6.18.21 profile 与 Pixel 8 的 preliminary benchmark 数据(Boot time 1.1%、Cold App launch 6.6%、Binder-rpc 15%、Binder-addints 23%、Hwbinder 23%，其中 Binder 类 benchmark 按多次运行中的最佳结果取值)。README 同时说明 Pixel 设备尚未针对该内核版本完成电源管理、CPU 频率调节和调度优化,这些结果不能外推到所有设备或所有 GKI build。

Binder 调用路径是 AutoFDO 优化的重点之一。Android 的跨进程通信几乎全部走 Binder(1.4 节),冷启动过程中一个典型 App 会发起数百次 Binder 调用。AutoFDO 将内核中 Binder 热路径的代码布局优化后,每次调用的开销降低可以累积为整体冷启动延迟的降低。官方博客给出的整体改善约 4%。

### 工作机制

AutoFDO 对内核的优化路径与用户空间相同:

1. 在代表性的工作负载下采集 CPU profiling 数据(使用 ARM SPE 或 Intel LBR)
2. 生成 AFDO profile 文件
3. 编译器(GCC/Clang)根据 profile 优化内核代码布局--热路径代码放在一起提高指令缓存命中率,冷路径代码分开减少对热路径的污染

区别在于:用户空间的 AutoFDO 只优化 App 代码(通过 dex2oat / ART),而内核的 AutoFDO 优化的是 GKI kernel 的编译产物。设备是否拿到这批优化,取决于对应 GKI release build 是否已经下发到该设备的兼容分支。Android 12+ 只是平台下限,不代表设备会进入同一条 6.12 内核线。

### 与 Cloud Compilation 的关系

1.12 节介绍了 Android 16 的 Cloud Compilation -- 将 dex2oat 从设备端迁移到 Google Play 云端。AutoFDO for kernel 和 Cloud Compilation 形成了完整的编译优化链:

- **用户空间**:Cloud Compilation + Baseline Profiles → 优化 App 的 AOT 编译
- **内核空间**:AutoFDO → 优化 GKI kernel 的代码布局

两端同时优化时,冷启动的"内核初始化 + App 进程创建 + App 代码执行"三个阶段都有机会受益,具体收益取决于设备是否拿到对应 profile / build。

## ART 运行时优化

调度器和存储栈的变化来自内核侧,ART 运行时优化则落在 Android 平台侧——内核和运行时两条线同时演进,才能解释完整的性能变化。

Android 17 的 ART 运行时引入了两项与性能直接相关的变化。

### Concurrent Mark-Compact + Generational GC

在 4.3 节和 4.8 节中已经把 ART 的垃圾回收机制展开过,这里只保留和系统性能结论直接相关的部分。4.8 的适用范围已经覆盖 Android 14-17,因此这里讨论的是 Android 17 对既有分代 GC 的增强。Concurrent Mark-Compact(CMC)路径把更多 young collection 维持在更小的扫描范围内。

分代策略本身没有变化:新对象优先留在 young generation,短命对象尽量在小范围回收,存活对象再逐步晋升。收益点在于 full-heap collection 的频率更低,GC 线程的 CPU 占用也更容易被压住。

把版本演进压缩来看:Android 8.0 先把 pause time 大幅压短;Android 10 之后的 Concurrent Copying 路径已经带有分代回收;Android 17 在 CMC 路径上继续强化 generational GC。对 RecyclerView 滑动和启动阶段的直接收益,是 GC 暂停与并发 GC 的 CPU 抢占都更容易被压到较小范围内。

### DeliQueue lock-free MessageQueue

DeliQueue 属于 Android 17 / API 37 平台行为,不属于 `android16-6.12` 内核分支本身。官方博客给出的适用条件是:targetSdk 37 及以上应用会收到新的 lock-free `android.os.MessageQueue` 实现;依赖反射读取 `MessageQueue` 私有字段的代码需要专项验证。

源码锚点在 AOSP `frameworks/base/core/java/android/os/`:历史实现可以看 `LockedMessageQueue/MessageQueue.java`,新实现可以看 `ConcurrentMessageQueue/MessageQueue.java`,`CombinedMessageQueue/MessageQueue.java` 负责兼容选择。博客描述的实现模型是生产者侧 lock-free Treiber stack + Looper 侧 min-heap:多个线程插入消息时不再抢同一把 monitor lock,Looper 仍由单线程维护到期消息的顺序。

官方博客给出的数据来自内部 beta traces,适合写成限定条件下的观测结果:

- App 主线程花在 `MessageQueue` lock contention 上的时间减少 15%。
- App missed frames 减少 4%。
- System UI / Launcher interactions missed frames 减少 7.7%。
- App startup 到 first frame drawn 的 P95 时间减少 9.1%。

这些数据不能直接外推到所有设备和所有 App。实际排查时,仍然要在 Perfetto 中搜索 `monitor contention with ...`,确认旧实现是否真的在 `MessageQueue` 上产生锁竞争。

## MGLRU 与页面回收优化

Multi-Gen LRU (MGLRU) 在 Kernel 6.1 引入。它在 `android16-6.12` 中通过 `CONFIG_LRU_GEN` 和 `CONFIG_LRU_GEN_ENABLED` Kconfig 选项控制;是否在特定设备的 GKI defconfig 中默认启用,需要查看对应分支的 `defconfig` 文件。它与 Android 的 LMK 机制(见 4.4 节)直接协同。

### 传统 LRU 的问题

Linux 内核的传统 LRU(Least Recently Used)用两条链表(active/inactive)跟踪页面的访问时间。问题在于:它只记录"是否访问过",不记录"访问了多少次"。一个被扫描器顺序读过的页面(每个页面只读一次)和一个被热循环反复访问的页面(每秒访问几千次),在传统 LRU 中可能获得相同的"最近访问"标记。

### MGLRU 的改进

MGLRU 将单一 active/inactive 链表拆分为多个 generation(代),每代有自己的时间窗口。页面的访问频率决定了它在哪一代--频繁访问的页面留在较新的 generation,很少访问的页面逐代下降直到被回收。

公开测试和论文显示 MGLRU 在页面回收效率上有方向性改善,但具体百分比因设备、内核分支和负载差异极大,本节不保留固定数值。方向性结论:

- `kswapd` CPU 占用下降,但幅度需要回到具体测试口径确认
- LMK 事件减少(前台 App 被误杀的概率随之下降)
- 渲染延迟在高内存压力场景有改善

对具体设备做验证时,需要补齐测试口径(内核分支、内存配置、负载模型、样本量)后再写入精确百分比。

对 Android 而言,MGLRU 更准确地识别活跃页面,减少错误回收(把正在使用的页面回收导致后续 page fault)。在内存紧张的设备上,前台 App 被误杀的概率会随之下降。

### 与 LMK 的协同

MGLRU 的改进最终要落到与 Android LMK 机制的协同上。在 4.4 节中我们讨论过 LMK 的机制:`lmkd` 守护进程根据 PSI/vmpressure 信号、内存水位和 `oom_score_adj` 做杀进程决策,不直接读取 MGLRU 的 generation 信息。MGLRU 的作用落在内核回收层--更准确地识别活跃页面、减少误回收,从而降低内存压力信号的触发频率。`lmkd` 收到的压力信号减少,杀进程的频率自然下降。如果要写"kill 频率下降 N%",需要补同设备前后 trace 或统计。

## 在 Perfetto 中的可观测性

Kernel 6.12 的优化在 Perfetto 中有多个可观测维度:

### 调度器相关
- **sched track**:线程的调度事件,EEVDF 的调度决策体现在线程获得 CPU 时间的模式上
- **sched_switch tracepoint**:可以观察短任务(UI 线程 doFrame)是否获得更低延迟
- **sched_ext tracepoint**:如果 OEM 使用了自定义调度器,这里能看到 BPF 调度器的决策

### 存储相关
- **block tracepoint**(`block:block_rq_issue` / `block:block_rq_complete`):单个 I/O 请求的延迟
- **f2fs tracepoint**(`f2fs:f2fs_sync_file_enter/exit`):fsync 延迟
- **dm-verity track**:哈希验证耗时

### 内存相关
- **Memory track**:`kswapd` 的 CPU 使用
- **lmk track**:低内存杀死事件频率
- **kmem tracepoint**:page fault 频率

### 如何验证 Kernel 6.12 优化是否生效

1. 对比同一设备在 Android 16 / 17 上的冷启动 Trace,关注 Binder transaction 延迟和 GC 暂停时间
2. 在 Memory track 中观察 `kswapd` 的 CPU 占比是否降低
3. 在 block tracepoint 中观察 fsync 的延迟分布是否改善

## 版本演进：把平台版本和 GKI 分支分开

| 维度 | 锚点 | 本节结论 |
|------|------------|----------|
| Android 15 相关 GKI | `kernel/common` `android15-6.6/kernel/sched/fair.c` | 已存在 `pick_eevdf()`、`entity_eligible()`、`place_entity()`,不能写成"6.6 仍是纯 CFS 默认"。 |
| Android 16 相关 GKI | `kernel/common` `android16-6.12/kernel/sched/fair.c`、`kernel/sched/ext.c` | fair scheduler 继续使用 EEVDF 路径;6.12 的明确新增点是 sched_ext 等能力。sched_ext kfunc 使用 `scx_bpf_dispatch()` / `scx_bpf_dispatch_vtime()` 命名。 |
| Android 17 相关 GKI | `kernel/common` `android17-6.18` Makefile 6.18.21;`kernel/sched/ext.c`;`gki/aarch64/afdo/README.md` | 6.18 分支的 sched_ext kfunc 已重命名为 `scx_bpf_dsq_insert()` / `scx_bpf_dsq_insert_vtime()`;AutoFDO README 公开 preliminary benchmark 数据(Boot 1.1%、Cold App launch 6.6%、Binder-rpc 15%、Binder-addints 23%、Hwbinder 23%，与正文数据一致；Binder 类按多次运行最佳结果取值)。 |
| Android 17 / API 37 平台行为 | Android 17 release notes / behavior changes;`frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java` | DeliQueue / lock-free `MessageQueue` 按 targetSdk 37 等条件生效,属于平台行为层,需和 GKI branch 分开记录。 |

存储栈优化仍然是累积性的:F2FS folio 化、checkpoint merge、dm-verity multi-buffer hashing、io_uring 新能力分别处在文件系统、块设备验证和系统调用层。某台设备是否具备这些变化,要回到它实际使用的 kernel release、GKI build 和厂商配置。

## 常见问题与误区

**误区 1:"Kernel 6.12 的优化只影响新设备"**

不准确。6.12 的优化先落在对应的 GKI release branch 上,再由兼容这条 branch 的设备去接收。能否看到收益,取决于设备是否采用对应的 GKI 内核、vendor modules 是否满足 stable KMI 约束,以及 OEM 是否真的把这条 release build 交付到量产版本。把"GKI 支持独立更新"理解成"所有 Android 12+ 设备都会自动收到同一条 6.12 更新",是错误的。

**误区 2:"EEVDF 进入 fair scheduler 是因为 CFS 有 bug"**

把 EEVDF 写成 CFS bug 的修复不准确;它是 fair scheduler 在移动交互延迟上的一次策略调整。旧模型更强调按 vruntime 拉平 CPU 时间,EEVDF 更强调 eligible entity 与 virtual deadline。移动设备上的 UI 回调、输入响应和前台短任务更依赖低延迟调度。

**误区 3:"sched_ext 意味着 Android 可以用任意调度器"**

sched_ext 是一个框架,Google 官方构建仍以 fair scheduler / EEVDF 为主。OEM 可以通过 sched_ext 自定义调度策略,但 Google 不提供官方支持。如果第三方 ROM 启用了自定义 sched_ext 调度器导致性能问题,排查方向是确认 sched_ext tracepoint 是否存在并检查自定义调度器的行为。

**误区 4:"MGLRU 可以解决所有内存问题"**

MGLRU 优化页面回收策略,让内核更准确地决定回收哪些页面。它不会增加物理内存,也不会减少 App 自身的内存占用。如果一个 App 有内存泄漏导致持续增长,MGLRU 只能让 LMK 更精准地处理目标进程,无法阻止泄漏继续发生。

## 参考资料

- [Google Android Developers Blog: Boosting Android Performance - AutoFDO for GKI Kernel](https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html)
- [GKI Kernel 架构文档](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)
- [AOSP GKI Kernel android15-6.6 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android15-6.6)
- [AOSP GKI Kernel android16-6.12 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12)
- [AOSP GKI Kernel android17-6.18 分支](https://android.googlesource.com/kernel/common/+/refs/heads/android17-6.18)
- [Android Developers Blog: Under the hood - Android 17 lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [AOSP external/liburing](https://android.googlesource.com/platform/external/liburing/+/refs/heads/main)
- [Lore.kernel.org: F2FS Checkpoint Merge 补丁系列](https://lore.kernel.org/all/)
- [Lore.kernel.org: MGLRU 补丁系列](https://lore.kernel.org/all/)
- [Kernel 6.12 Changelog](https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12)
- 交叉引用:§1.4 Binder IPC、§1.6 版本演进、§1.12 AutoFDO、§1.13 DeliQueue、§4.4 LMK、§4.8 ART GC、§5.1 调度基础、§5.7 CPU 版本演进、§6.2 文件系统、§6.3 I/O 调度、§8.2 应用启动、§16.1 Google 官方优化思路
