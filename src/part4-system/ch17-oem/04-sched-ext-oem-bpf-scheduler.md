---
title: "sched_ext 与 OEM BPF 调度器"
chapter: "17.4"
section: "17.4"
status: finalized
drafted_date: "2026-05-15"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 16 (GKI 6.12) - Android 17 (API 37); OEM backport depends on vendor kernel"
last_verified: "2026-05-29"
last_verified_against: "Linux sched_ext documentation, Android common android16-6.12 ext.c/ext.h/cpufreq_schedutil.c, OPPO hmbird_sched proc source"
confidence: medium
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构"
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-04-sched-ext-oplus-impl.md"
  - type: official
    path: "https://raw.githubusercontent.com/torvalds/linux/master/Documentation/scheduler/sched-ext.rst"
  - type: upstream-linux
    path: "https://raw.githubusercontent.com/torvalds/linux/master/kernel/sched/ext.c"
  - type: upstream-linux
    path: "https://raw.githubusercontent.com/torvalds/linux/master/kernel/sched/ext.h"
  - type: upstream-linux
    path: "https://raw.githubusercontent.com/torvalds/linux/master/include/linux/sched/ext.h"
  - type: upstream-linux
    path: "https://raw.githubusercontent.com/torvalds/linux/master/tools/sched_ext/scx_simple.bpf.c"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/kernel/sched/ext.c"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/kernel/sched/ext.h"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/include/linux/sched/ext.h"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/kernel/sched/cpufreq_schedutil.c"
  - type: oem-source
    path: "https://raw.githubusercontent.com/Wuzikh1/sched_ext/main/hmbird_sched_proc_main.c"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12"
tags: ["sched-ext", "bpf", "oem", "scheduler", "kernel-6.12"]
related_chapters: ["5.1", "5.2", "5.7", "14.10", "17.2"]
reviewed_by: openclaw-task6
reviewed_date: "2026-05-29"
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-29"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-29"
task9_reviewed_by: openclaw-task9
task2b_state: fixed
pipeline_stage: ready-to-publish
task2b_result: fixed
last_task9_at: "2026-05-29T07:21:00+08:00"
last_task9_review_log: "logs/deep-review/2026-05-29-07-deep-review.md"
task9_review_notes: "2026-05-29 Task9 deep-review: pass-tech-review。复核 2026-05-20 P0/P1 已修复；Android common 6.12 sched_ext、DSQ、partial switch、scx_bpf_cpuperf_set 与 hmbird_sched proc 控制面口径一致；无新增 P0/P1。queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task6_at: "2026-05-29T07:07:00+08:00"
last_task6_review_log: "logs/review/2026-05-29-07-review.md"
task6_review_notes: "2026-05-29 07:07 Task6 revisiting review: pass-light-edit；L1/L2 通过；Task2B 已修复后送 Task9 复审；无新增 L3/L4 回炉项。"
last_task2b_at: "2026-05-29T06:50:00+08:00"
task2b_fixed_by: openclaw-task2b-main
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-29T07:07:00+08:00"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
last_task9_audit: "2026-06-20"
last_task9_audit_log: "logs/deep-review/2026-06-20-10-audit.md"
last_task9_audit_result: "pass-idle-audit"
last_task9_audit_notes: "idle audit: no P0/P1/P2; Android common android16-6.12 sched_ext paths/constants/sysfs and OPPO hmbird proc controls rechecked; upstream mainline-only DSQ bypass constants remain outside Android 17/API 37 conclusions."
---

# 17.4 sched_ext 与 OEM BPF 调度器

<!-- outline-start -->
## 要点

### 🔹 sched_ext 在调度体系里的位置
- Linux 6.12 引入的 BPF 调度框架
- 与 CFS / EEVDF / EAS 的分工
- Android GKI 与 OEM vendor kernel 的边界

### 🔹 BPF 调度器入口与生命周期
- `struct sched_ext_ops` 的回调集合
- `select_cpu` / `enqueue` / `dispatch` 的职责
- 任务在 SCX core 与 BPF 调度器之间的状态迁移

### 🔹 OEM 使用形态
- OPPO / OnePlus `hmbird_sched` 的公开线索
- proc 开关、partial enable、CPU 控制参数
- 高通与联发科平台公开信息不足的边界

### 🔹 对前台交互性能的影响
- 帧率 boost 与任务分组
- RenderThread / binder / worker 线程的 CPU 选择
- 误配后可能出现的延迟和能耗代价

### 🔹 可观测与验证方法
- 确认内核配置和 proc 节点
- Perfetto sched / cpufreq / binder 联合观测
- 对比开启前后的延迟分布

### 🔹 工程使用边界
- AOSP 默认路径与 OEM 实验路径区分
- root / vendor kernel / SELinux 限制
- 不能把单一厂商策略写成 Android 通用机制

## 扩展

### 🔸 sched_ext 与 uclamp / cpuset 的关系
[已覆盖]

### 🔸 Android 17 Kernel 6.12 之后的默认启用可能性
[已覆盖]

### 🔸 厂商游戏模式与 BPF 调度器的验证清单
[已覆盖]

<!-- outline-end -->

## sched_ext 解决的不是 App 线程池问题

`sched_ext` 是 Linux 6.12 合入的 BPF extensible scheduler class。它让内核可以加载一组 BPF 程序来实现调度策略，入口是 `struct sched_ext_ops`。Android 性能分析里要把它放在系统调度层看：它影响的是 runnable task 如何选 CPU、入队、出队、分发，不是 App 侧线程池、协程调度器或 WorkManager 的替代品。

对 Android 工程师来说，`sched_ext` 的价值不在于“自己写一个调度器”。大多数 App 无法也不该直接控制它。更现实的场景是：某台 OEM 设备开启了自定义 BPF 调度器，Perfetto 里同一类线程的 CPU 迁移、频率响应、binder 等待时间和其它设备不一样。读懂这些差异，才能判断问题来自 App 任务组织、系统调度策略，还是厂商内核实验。

[已验证: Linux Documentation/scheduler/sched-ext.rst；Linux 文档明确说明 `sched_ext` 由 BPF scheduler 定义行为，可动态开启和关闭，异常时回退到 fair-class scheduler]

## sched_ext 在 Android 调度体系里的位置

Android 的 CPU 调度通常要同时看三层：Linux scheduler class 决定任务如何进入 CPU，EAS / sugov / cpufreq 决定频率与能效策略，Android framework 和 vendor 服务通过 hint、uclamp、cpuset、task profile 等机制影响任务属性。`sched_ext` 位于第一层，它改变的是普通任务在 scheduler class 内部的排队与分发方式。

和 §5.1、§5.2 的关系可以这样划分：

- **CFS / EEVDF**：Linux fair-class 的默认策略，负责普通任务的公平性和虚拟时间排序。Android 设备没有加载 BPF scheduler 时，普通 App 线程仍按 fair-class 运行。
- **EAS**：在异构 CPU 上用能耗模型参与 CPU 选择，重点是“任务放到哪个 CPU 更省电或更合适”。详见 5.2 节。
- **sched_ext**：提供一套 BPF 回调接口。BPF scheduler 可以自己维护队列、选择 CPU、决定何时把任务交给内核的 dispatch queue。
- **OEM vendor kernel**：厂商可以在 GKI 之外加入 proc 节点、系统服务、BPF 程序和策略参数。这里的行为不能直接外推到 AOSP 默认系统。

这张图把边界放清楚：

```mermaid
flowchart TD
    App[App threads: main / RenderThread / binder / worker] --> Attr[task policy / affinity / uclamp / cpuset]
    Attr --> Core[Linux scheduler core]
    Core --> Fair[fair-class: CFS / EEVDF]
    Core --> SCX[sched_ext class]
    SCX --> Ops[BPF scheduler: struct sched_ext_ops]
    Ops --> DSQ[dispatch queues: local / global / custom DSQ]
    DSQ --> CPU[CPU runqueue]
    CPU --> Freq[cpufreq / sugov / vendor governor]
    Vendor[OEM service / procfs / BPF loader] --> Ops
    Vendor --> Freq
```

图里容易误判的是 `sched_ext` 和频率治理的关系。`sched_ext` 直接处理任务调度，cpufreq 仍由 governor 和 util 信号驱动；同时，Android common `android16-6.12` 已包含一条 Linux sched_ext 通用 CPU performance target 路径：BPF scheduler 可通过 `scx_bpf_cpuperf_set()` 设置 CPU performance target，`cpufreq_schedutil.c` 中的 `sugov_get_util()` 读取 `scx_cpuperf_target(cpu)` 并参与 schedutil 的 util 计算。厂商的 `scx_gov_ctrl`、`cpuctrl_high/low` 属于额外控制面，不能反过来否定这条通用路径。

[已验证: Linux Documentation/scheduler/sched-ext.rst；Android common android16-6.12 `kernel/sched/ext.c`、`include/linux/sched/ext.h`、`kernel/sched/cpufreq_schedutil.c`；详见 5.1 节、5.2 节、14.10 节]

## BPF 调度器入口：`struct sched_ext_ops`

`sched_ext` 的主入口是 `struct sched_ext_ops`。BPF scheduler 通过这张回调表告诉内核：任务 wakeup 时怎么选 CPU，任务 runnable 后怎么入队，CPU 空闲或本地队列空时怎么分发任务，任务开始运行、停止运行、退出时怎么更新调度器内部状态。

常见回调可以按调度周期分组：

| 回调 | 调用时机 | 分析价值 |
|------|----------|----------|
| `select_cpu()` | 任务 wakeup、fork 或 exec 后准备选择 CPU | 影响线程醒来后更可能跑在哪个 CPU；返回值是优化提示，不是最终绑定 |
| `enqueue()` | 任务进入 runnable 状态且未被 `select_cpu()` 直接放入 DSQ | 判断任务被直接放进内置 DSQ，还是进入 BPF scheduler 自己维护的队列 |
| `dispatch()` | 某个 CPU 的 local DSQ 没任务可跑 | 决定从 custom DSQ 或 BPF 内部队列取哪些任务交给 CPU |
| `running()` / `stopping()` | 任务开始运行或停止运行 | 常用于更新虚拟时间、运行时统计和权重消耗 |
| `init_task()` / `exit_task()` | 任务加入或离开 BPF scheduler 管理范围 | 用来建立或清理 per-task 状态 |
| `cpu_acquire()` / `cpu_release()` | CPU 被 sched_ext 接管或让出 | 能解释 RT/DL/stop class 抢占后调度器状态变化 |

`select_cpu()` 这一点容易被写重。Linux 文档说得很明确：它返回的 CPU 是优化提示，内核可以在后续调度阶段把任务放到其它允许的 CPU 上。如果 BPF 程序在 `select_cpu()` 中把任务直接插入 `SCX_DSQ_LOCAL`，`enqueue()` 会被跳过；如果没有直接插入，任务会继续走 `enqueue()`。

`tools/sched_ext/scx_simple.bpf.c` 是理解这套接口的参考实现。它在 `select_cpu()` 中调用 `scx_bpf_select_cpu_dfl()`，如果拿到空闲 CPU，就把任务插入 `SCX_DSQ_LOCAL`；否则在 `enqueue()` 中把任务放入共享 DSQ，并在 `dispatch()` 中把共享 DSQ 的任务移动到 CPU local DSQ。这个例子足够解释大多数 Perfetto 现象：线程换 CPU，通常发生在 wakeup、入队、分发几个阶段的重新放置过程中。

[已验证: Linux kernel/sched/ext.c（torvalds/master + Android common android16-6.12）；Linux tools/sched_ext/scx_simple.bpf.c]

## DSQ 决定任务从 BPF 调度器回到 CPU 的方式

DSQ 是 dispatch queue 的缩写。`sched_ext` 用 DSQ 衔接内核调度器和 BPF scheduler：BPF scheduler 可以把任务插入内置 DSQ，也可以创建自定义 DSQ，再在 `dispatch()` 中移动任务。

内置 DSQ 和时间片常量按版本拆开写。

**Android common kernel `android16-6.12` 可用的内置 DSQ：**

- `SCX_DSQ_LOCAL`：每个 CPU 的本地队列。任务进入这里后，目标 CPU 可以直接运行它。
- `SCX_DSQ_GLOBAL`：内置全局 FIFO 队列。本地队列空时，CPU 可以从这里取任务。
- `SCX_DSQ_LOCAL_ON | cpu`：把任务放到指定 CPU 的 local DSQ。

时间片常量：`SCX_SLICE_DFL = 20ms`（默认补 slice）。

**upstream mainline（torvalds/master）新增：**

- `SCX_DSQ_BYPASS`：异常、回退或前进保障场景下使用的绕过队列。
- `SCX_SLICE_BYPASS = 5ms`：bypass 模式下使用的时间片。

这两组常量在 Android common 6.12 分支中不存在。如果正文面向 Android 16 GKI 6.12，不要把 `SCX_DSQ_BYPASS` 和 `SCX_SLICE_BYPASS` 写成当前可用能力。它们属于后续 upstream 差异，待 Android 分支合入后再更新。

`SCX_SLICE_DFL = 20ms` 不是 Android 帧预算，也不是前台线程固定运行时间。它只是 sched_ext 在默认补 slice 模式下使用的时间片常量。把它直接换算成"120Hz 一帧 8.33ms 所以 20ms 一定卡顿"是不成立的，调度器还会被 wakeup、抢占、阻塞、频率变化和 RT 任务打断。

[已验证: Android common kernel android16-6.12 include/linux/sched/ext.h；torvalds/linux master 同文件]

## OEM 公开线索：OPPO / OnePlus `hmbird_sched`

公开材料中，OPPO / OnePlus 的 `hmbird_sched` 是目前最容易追到的 Android OEM 线索。`Wuzikh1/sched_ext` 仓库中的 `hmbird_sched_proc_main.c` 暴露了 `/proc/hmbird_sched` 目录和一批运行时参数，例如 `scx_enable`、`partial_ctrl`、`cpuctrl_high`、`cpuctrl_low`、`scx_shadow_tick_enable`、`heartbeat_enable`、`watchdog_enable`、`isolate_ctrl`、`parctrl_high_ratio`、`isoctrl_high_ratio` 等。

这些节点能说明三件事：

- **有运行时开关**：`scx_enable` 和 `partial_ctrl` 说明策略可以按设备状态或场景切换，不一定整机常开。
- **调度和频率治理可能协同**：`cpuctrl_high/low`、`slim_freq_gov/scx_gov_ctrl` 暗示 vendor 策略会同时调度任务和调整 governor 参数。
- **帧率场景被纳入参数体系**：`slim_walt/frame_per_sec` 对应 `sched_ravg_window_frame_per_sec = 125`，说明厂商策略至少考虑了 frame rate 相关窗口。

### partial enable 与接管范围

Linux sched_ext 加载 BPF scheduler 后，默认接管 `SCHED_OTHER`、`SCHED_BATCH`、`SCHED_IDLE` 和 `SCHED_EXT` 等 policy 的普通任务。如果 BPF scheduler 设置了 `SCX_OPS_SWITCH_PARTIAL` 标志，只接管显式切换到 `SCHED_EXT` policy 的任务，其余仍留在 fair class（CFS/EEVDF）。

这个分支直接决定"普通 App 线程是否受 sched_ext 影响"：

- **默认模式（non-partial）**：所有普通线程进入 BPF scheduler 管理。前台 App 的 main 线程、RenderThread、binder 线程都会被 `select_cpu()`、`enqueue()`、`dispatch()` 处理。
- **partial 模式**：只有显式 `sched_setscheduler(pid, SCHED_EXT, ...)` 的任务进入 BPF scheduler。未切换的 App 线程仍走 fair class。

OPPO/OnePlus 的 `partial_ctrl` proc 节点与 `SCX_OPS_SWITCH_PARTIAL` 的对应关系需要从 vendor kernel 源码或 tracepoint 确认——它可能是控制 partial 模式开关的厂商接口，也可能只是命名相近但逻辑不同的控制面。验证方式：

- `cat /proc/<pid>/sched | grep ext`：查看目标线程是否在 ext class
- `tracepoint:sched:sched_switch` 或 Perfetto sched slice：对比 partial 开关前后，目标线程的调度行为变化
- vendor kernel 源码中 `scx_enable` 和 `partial_ctrl` 的读写逻辑

这份公开源码没有给出 BPF 调度策略主体。它展示的是 procfs 控制面，不等于完整的 scheduler policy。文档或文章如果只看到这些节点，就推断“所有 OnePlus 设备都用某个 BPF 算法调度前台线程”，证据不够。

高通和联发科平台也不能凭 SoC 厂商名下结论。sm8750 设备出现 `hmbird_sched`，只能说明某个 OEM 在某条产品线上使用了这套机制；其它高通设备、联发科设备、Google Pixel 或三星设备是否启用，需要回到内核配置、procfs/sysfs 节点和 Perfetto 证据。

[已验证: OPPO public hmbird_sched_proc_main.c；待验证: BPF 调度策略主体未在公开仓库中出现]

## 对前台交互性能的影响

`sched_ext` 影响前台交互性能的路径主要有三类。

**CPU 选择改变 wakeup 延迟。** `RenderThread`、主线程、binder 线程和解码/布局 worker 线程经常在短时间内反复 sleep 和 wakeup。`select_cpu()` 如果稳定把这些线程放到空闲且合适的 CPU 上，wakeup 后的 runnable 等待时间会下降；如果 CPU 选择和任务 affinity、cpuset、热限制冲突，线程会在 runnable 状态等待更久。

**队列策略改变线程之间的相对顺序。** BPF scheduler 可以把任务放入自定义 DSQ，再按自定义规则移动到 local DSQ。厂商可能给前台进程、游戏线程、SurfaceFlinger 相关线程或 binder reply 更高权重。收益是交互路径更快；代价是后台任务、IO worker 或低优先级 binder 请求被推迟。

**频率策略可能和调度策略一起变化。** 先区分两条路径：Linux sched_ext 通用路径可以通过 `scx_bpf_cpuperf_set()` 影响 schedutil 读取到的 CPU performance target；vendor 路径可能再叠加 `scx_gov_ctrl`、`cpuctrl_high/low` 这类私有参数。Perfetto 中如果出现“线程迁移变少 + 频率响应更快”的组合，分析时不能只盯 `sched` 表，也要看 `cpufreq`、CPU idle、thermal、binder transaction 和 frame timeline。

误配通常表现为一组信号同时出现：前台线程 runnable 时间变长、binder reply 延迟上升、CPU 频率长期维持高位、温度触发降频、后台任务 tail latency 变差。遇到这类设备差异，先确认是否存在 `sched_ext` 或 vendor proc 节点，再把 trace 和同 SoC 不同 ROM、同 ROM 不同开关状态做对比。

[已验证: Linux sched_ext scheduling cycle；OPPO hmbird_sched proc 参数；性能影响部分需结合实机 trace 验证]

## 可观测与验证方法

验证 `sched_ext` 不要从结论开始，要从设备证据开始。下面这些检查按侵入性从低到高排列。

命令行检查用于确认内核能力、当前状态和 vendor 节点：

```bash
adb shell 'zcat /proc/config.gz 2>/dev/null | grep CONFIG_SCHED_CLASS_EXT'
adb shell 'cat /sys/kernel/sched_ext/state 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/root/ops 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/enable_seq 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/switch_all 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/nr_rejected 2>/dev/null'
adb shell 'cat /sys/kernel/sched_ext/hotplug_seq 2>/dev/null'
adb shell 'grep ext /proc/self/sched 2>/dev/null'
adb shell 'ls -la /proc/hmbird_sched 2>/dev/null'
```

这组命令分别回答：内核是否编进 `CONFIG_SCHED_CLASS_EXT`，当前是否有 BPF scheduler 运行，运行的 ops 名称是什么，本次 boot 是否曾加载过 scheduler，是否发生过全局切换、拒绝加载或热插拔序列变化，当前 task 是否在 ext class 上，以及设备是否暴露 OPPO/OnePlus 风格的 vendor 控制节点。user build 可能因为 SELinux、内核配置隐藏或 `/proc/config.gz` 关闭而读不到结果，读不到不等于未启用。

Perfetto 里可以先看迁移和 runnable 时间。下面的 SQL 用 `sched` 表统计目标线程的 CPU 迁移次数，适合比较开关前后或不同设备的差异：

```sql
WITH target AS (
  SELECT utid
  FROM thread
  WHERE name IN ('main', 'RenderThread', 'Binder:')
), sched_points AS (
  SELECT
    s.utid,
    s.ts,
    s.cpu,
    LAG(s.cpu) OVER (PARTITION BY s.utid ORDER BY s.ts) AS prev_cpu
  FROM sched s
  JOIN target t USING (utid)
)
SELECT
  thread.name,
  COUNT(*) FILTER (WHERE prev_cpu IS NOT NULL AND cpu != prev_cpu) AS migrations,
  COUNT(*) AS sched_slices
FROM sched_points
JOIN thread USING (utid)
GROUP BY thread.name
ORDER BY migrations DESC;
```

这条 SQL 只说明线程被调度到不同 CPU 的次数，不能单独证明迁移好坏。要继续看同一时间窗口里的 `thread_state` runnable 时长、`cpufreq` 频率变化、binder 等待、frame timeline missed frame。对调度策略来说，迁移次数下降但 runnable 时间上升，通常比迁移次数高更值得警惕。

[已验证: Perfetto `sched` 表常规分析方式；详见 13.6 节、13.10 节、14.10 节]

## sched_ext 与 uclamp、cpuset 的关系

`uclamp` 和 `cpuset` 是 Android 调度路径里经常和 `sched_ext` 混在一起的两个机制。区分它们能减少很多误判。

`cpuset` 限制任务能在哪些 CPU 上运行。`sched_ext` 的 `select_cpu()` 返回值不是最终绑定，内核仍会检查任务允许的 CPU mask。一个后台任务如果被放在受限 cpuset 中，BPF scheduler 不能随意把它发到不允许的高性能核心上。

`uclamp` 给任务的 util 加上下界或上界，常用于前台 boost、游戏模式、相机等场景。它更接近频率和容量选择的输入，而不是 BPF scheduler 的队列语义。厂商 BPF scheduler 可以读取或间接受到这类属性影响，但是否尊重 `uclamp.min`、是否把某类任务放进特殊 DSQ，是 vendor 策略问题。

所以分析顺序应该是：确认 task profile / cpuset / uclamp，再判断 scheduler class 和 BPF ops。只看 `sched_ext` 开关，不看任务属性，容易把 Android framework 层的性能 hint 误写成内核 BPF 调度器效果。

[已验证: Linux sched_ext 文档对 CPU 选择约束的描述；Android task profile/uclamp 行为详见 5.2、5.4、5.9 节]

## Android 17 之后会默认启用吗

Android 16 / Android 17 进入 kernel 6.12 之后，`sched_ext` 基础设施出现在 Android common kernel 分支并不意外。问题不在“源码里有没有”，而在“产品构建是否启用配置、是否加载 BPF scheduler、是否把普通任务切到 ext class”。

当前能写进正文的判断只有三个：

- Linux upstream 已提供 `CONFIG_SCHED_CLASS_EXT`、`/sys/kernel/sched_ext/*` 状态接口和 `tools/sched_ext` 示例调度器。
- Android common kernel `android16-6.12` 分支公开存在，搜索结果中也能看到 OPPO 相关 scx tracepoint / symbol list 线索。
- AOSP 默认用户态没有公开资料表明普通 App 线程会统一切到某个 BPF scheduler；量产行为仍由设备厂商、内核配置和系统服务决定。

因此，本书不能把 `sched_ext` 写成 Android 17 默认调度机制。更稳的说法是：Kernel 6.12 之后，Android OEM 有了更标准的 BPF 调度扩展入口；某些厂商可以把它用于游戏、前台交互或功耗策略，但是否启用必须逐设备验证。

[待验证: Android 17 正式发布后 GKI defconfig、CDD/VTS 约束、Pixel 与主流 OEM user build 的默认状态]

## 厂商游戏模式与 BPF 调度器验证清单

游戏模式、帧率稳定和前台交互是 OEM 最可能接入自定义调度策略的场景。验证时不要只看游戏帧率，要同时确认调度、频率、温度和后台代价。

建议按这个清单记录证据：

| 维度 | 要采集的证据 | 判断边界 |
|------|--------------|----------|
| 内核能力 | `CONFIG_SCHED_CLASS_EXT`、`/sys/kernel/sched_ext/state`、`enable_seq` | 只能说明能力和状态，不能说明具体策略 |
| vendor 控制面 | `/proc/hmbird_sched/*` 或同类 vendor 节点 | 节点存在不等于 BPF scheduler 已加载 |
| 前台线程 | main / RenderThread / UnityMain / UE RenderThread 的 runnable 时间和 CPU 迁移 | 需要和 frame timeline 对齐 |
| binder 路径 | binder reply 等待、system_server 相关线程 runnable 时间 | 前台 boost 可能挤压系统线程，反而造成等待 |
| 频率与温度 | `cpufreq`、thermal throttling、CPU idle | 调度收益可能被热降频抵消 |
| 对照实验 | 同设备开关前后、同 SoC 不同 ROM、同 App 不同场景 | 没有对照就不要写成因果结论 |

如果只拿到一条 `/proc/hmbird_sched/scx_enable=1`，只能写“该设备暴露并开启了 vendor scx 开关”。要写“它改善了游戏帧率稳定性”，还需要帧时间分布、runnable 延迟、频率和温度的对照数据。

[已验证: OPPO hmbird_sched proc 节点；待验证: 具体游戏策略需要实机 Perfetto + 温度/频率数据]

## 工程使用边界

`sched_ext` 适合作为 OEM 调度策略分析入口，不适合作为 App 性能优化的直接操作项。App 团队能做的是减少不必要的 runnable 竞争、控制线程数量、合理使用 coroutine dispatcher / executor、避免在关键帧窗口里堆后台任务。设备侧是否用 BPF scheduler，通常不是 App 能决定的。

写作和排查时守住三条边界：

- **AOSP 与 OEM 分开写**：Linux / Android common kernel 提供能力，OPPO/OnePlus `hmbird_sched` 是厂商实现线索，两者不能混成一个默认机制。
- **公开源码与固件策略分开写**：procfs 控制面能说明有哪些开关，不能还原 BPF scheduler 的完整算法。
- **现象与因果分开写**：Perfetto 中看到 CPU 迁移减少、频率更高、帧率更稳，只能作为相关性证据；要写因果，需要开关前后对照或源码级策略证明。

这套边界也适用于其它 vendor 调度功能。性能文章里要避免把单一厂商、单一固件版本的行为写成 Android 通用规律；承认未知反而更稳。

## 参考资料


- [已验证: Linux sched_ext 官方文档, `Documentation/scheduler/sched-ext.rst`](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/scheduler/sched-ext.rst)
- [已验证: Linux `struct sched_ext_ops`, `kernel/sched/ext.c`（torvalds/master + Android common 6.12）](https://raw.githubusercontent.com/torvalds/linux/master/kernel/sched/ext.c)
- [已验证: Linux DSQ 与 sched_ext entity, `include/linux/sched/ext.h`](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/sched/ext.h)
- [已验证: Linux 示例 BPF scheduler, `tools/sched_ext/scx_simple.bpf.c`](https://raw.githubusercontent.com/torvalds/linux/master/tools/sched_ext/scx_simple.bpf.c)
- [已验证: OPPO/OnePlus `hmbird_sched` proc 控制面, `hmbird_sched_proc_main.c`](https://raw.githubusercontent.com/Wuzikh1/sched_ext/main/hmbird_sched_proc_main.c)
- [来源: AIW AutoResearchClaw 调研报告, `2026-05-04-sched-ext-oplus-impl.md`]
- [待验证: Android common kernel `android16-6.12` 分支与各 OEM user build 默认启用状态]
