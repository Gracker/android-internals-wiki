---

title: Linux 进程调度基础
chapter: '5.1'
section: '5.1'
status: "finalized"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task6_result: "pass-light-edit"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-12"
reviewed_at: "2026-05-18T01:08:00+08:00"
last_task6_at: "2026-06-12T01:08:00+08:00"
task6_reviewed_date: "2026-05-18"
review_round: 5
task2b_fixed_date: '2026-05-16T11:26:08+08:00'
task2b_fixed_issues:
  - oom-adj-section-trimmed-to-cross-reference
  - eevdf-sysctl-params-and-rt-version-timeline-added
  - diagnostic-decision-framework-added
task6_review_notes: "2026-05-18 task6 复审：pass-light-edit。完成标点/中英文间距/SQL 别名等 L1/L2 小修；无新增 B 类问题。Task9 已 pass-tech-review 且 queue.json 无 pending，自动晋升 finalized。"
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-11"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-11T15:20:00+08:00"
task2b_state: fixed
task2b_result: fixed
applicable_versions: Android 6.0 (API 23) - Android 17 (API 37, EEVDF 部分需 6.6+ 内核)
last_verified: '2026-06-11'
last_verified_against: Linux 6.6 sched-design-CFS + kernel/sched/fair.c/debug.c,
  bionic pthread.h android-16.0.0_r1, libprocessgroup task_profiles.json android-16.0.0_r1
confidence: high
sources:
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md
- type: blog
  path: Personal-Knowlodge/source/android-systrace-cpu-state-sleep.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-08_wechat_性能测试中的系统资源分析之_CPU.md
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://docs.kernel.org/scheduler/sched-design-CFS.html
- type: official
  path: https://docs.kernel.org/scheduler/sched-eevdf.html
- type: official
  path: https://man7.org/linux/man-pages/man7/sched.7.html
- type: official
  path: https://source.android.com/docs/core/perf/uclamp
tags:
- scheduler
- CFS
- vruntime
- nice
- sched_setaffinity
- cpuset
- Perfetto
related_chapters:
- '5.2'
- '5.3'
- '2.5'
- '7.3'
drafted_date: '2026-03-31'
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
review_type: post-polish-quality-gate
task9_review_notes: "2026-05-18 Task9 00:25 → pass-tech-review；前轮 P0/P1 已修复，剩余 P2（SoC 迁移数据、SQL 聚合、sched_base_slice 默认值边界）沿用既有 suggestions，不重复入队；等待 Task6 回炉。 | 2026-06-11 15 Task9 idle audit auto-fix: 修正 Linux 6.6 EEVDF base_slice debugfs 路径、默认值边界与 AOSP source tag 锚点；未发现 Android/API 38+ 越界内容，回到 Task6 复审。"
last_task9_review_log: "logs/deep-review/2026-06-11-15-audit.md"
last_task6_review_log: "logs/review/2026-05-18-01-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-29
last_task6_audit: "2026-06-12"
last_task9_audit: "2026-06-11"
last_task9_autofix_at: "2026-06-11"
updated_date: "2026-06-11"
updated_by: openclaw-task9
---

<!-- outline-start -->
- 🔹 CFS / EEVDF 的基本原理：vruntime、红黑树、base_slice、eligible entity、virtual deadline
- 🔹 调度策略分层：SCHED_DEADLINE → RT（SCHED_FIFO / SCHED_RR）→ fair（SCHED_OTHER / SCHED_BATCH）→ SCHED_IDLE
- 🔹 nice 值与权重的换算关系
- 🔹 CPU Affinity、cpuset 与 task profiles 对可用核心的控制
- 🔹 调度延迟（Scheduling Latency）：runqueue wait 在 Perfetto 中的观察

- 🔸 EEVDF 调度器对 CFS 的改进(Linux 6.6+)
- 🔸 Real-time 线程在 Android 中的使用场景(Audio、SurfaceFlinger)
- 🔸 SchedTune / UClamp 与 libprocessgroup task profiles 的 Android 控制路径
<!-- outline-end -->

## 为什么要了解 Linux 进程调度

打开一份 Perfetto Trace，最上面那几行五颜六色的色块——CPU 0、CPU 1、CPU 2......每个色块代表一个线程在某个时刻占用了那个 CPU 核心。这些色块之间的排列组合，就是 Linux 调度器的决策结果。

理解调度器的工作原理，直接关系到我们能不能回答这些实际问题：

- 主线程为什么在关键时刻没有被 CPU 执行？是被谁抢占了？
- RenderThread 明明有工作要做，为什么一直在 Runnable 状态排队？
- 把关键线程绑到大核，到底能带来多少性能提升？
- 系统负载高的时候，调度器是怎么决定谁先跑谁后跑的？

这些问题无法通过阅读应用层代码来解决——答案藏在内核的调度逻辑里。本章要做的，就是把调度器的核心机制讲清楚，让我们在 Perfetto 中看到那些色块时，能读懂调度器为什么这样安排。

## CFS 的基本原理

### 从"分时间片"到"追平虚拟时间"

打开 Perfetto 的 CPU 调度视图，你会看到各个 CPU 核心上五颜六色的线程运行切片——绿色是 Running，浅绿色是 Runnable。这些切片的排列组合，就是调度器工作原理的直接体现。

早期的 Linux 调度器（O(1) 调度器）使用固定时间片的方式分配 CPU：每个优先级对应一个时间片长度，时间片用完就换下一个进程。这种方式的问题在于，它无法精确地保证公平——在负载变化时，某些进程可能长期得不到足够的 CPU 时间。

CFS（Completely Fair Scheduler）从 Linux 2.6.23（2007 年）开始成为默认调度器，它抛弃了固定时间片的概念，转而追求一个更优雅的目标：**让所有可运行进程的虚拟运行时间（vruntime）趋于一致**。

CFS 的核心思想可以类比成一个记账系统：每个进程都有一个“账户”，记录了它已经消耗了多少 CPU 时间。调度器每次选择“账户余额最少”（vruntime 最小）的进程来运行，确保长期来看每个进程获得的 CPU 时间是公平的。

### vruntime：调度的核心标尺

vruntime（虚拟运行时间）是 CFS 最重要的概念。它的名字中有“虚拟”二字，是因为它并不是简单的墙上时钟时间，而是经过权重调整后的“标准化时间”。

当一个进程在 CPU 上运行了一段时间 `delta_exec`，它的 vruntime 增长量是这样计算的：

```text
delta_vruntime = delta_exec × (NICE_0_LOAD / weight)
```

其中 `NICE_0_LOAD` 是 nice 值为 0 时对应的权重（1024），`weight` 是当前进程的权重。按这个公式看：

- **权重越高的进程**（nice 值越低），vruntime 增长越慢，越容易被再次选中运行——它获得了更多的 CPU 份额
- **权重越低的进程**（nice 值越高），vruntime 增长越快，更容易被调度器换下 CPU

### CFS 调度循环的源码路径

CFS 的调度决策在 `kernel/sched/fair.c` 中实现。Linux 5.x / 6.1 内核（当前 Android 主流）的调度循环经过以下关键函数：

**1. 记账：`update_curr()`**。每次时钟中断或任务状态变化时调用，计算当前任务的 `delta_exec`（实际运行时间），再通过 `calc_delta_fair()` 按权重换算为 vruntime 增量，累加到 `se->vruntime`。这是 vruntime 持续增长的源头。

**2. 入队/出队：`enqueue_entity()` / `dequeue_entity()`**。`enqueue_entity()` 将任务加入红黑树，以 `se->vruntime` 为 key；`dequeue_entity()` 将任务移出。被唤醒的任务调用 `enqueue_entity()` 重新入队，时间片用完或被抢占的任务通过 `dequeue_entity()` 出队。

**3. 选人：`pick_next_task_fair()`**。fair class 的核心选人入口。在 pre-EEVDF 内核（Linux < 6.6）中，它调用 `pick_next_entity()` 取红黑树最左节点（`rb_leftmost`）——也就是 vruntime 最小的调度实体。

**4. 抢占判定：`check_preempt_wakeup()`**。在任务被唤醒时调用，比较被唤醒任务和当前运行任务的 vruntime 差距，决定是否触发抢占。如果新唤醒的任务 vruntime 远小于当前任务，调度器会在下一个调度点切换。

```text
schedule()
  └→ __schedule()
       ├→ pick_next_task_fair()        ← fair class 选人入口
       │    └→ pick_next_entity()      ← 取 vruntime 最小实体
       │         └→ rb_leftmost        ← 红黑树最左节点
       └→ update_curr()                ← 更新当前任务 vruntime
            └→ calc_delta_fair()       ← 按权重换算 vruntime
```

### 红黑树：O(log N) 的调度队列

CFS 使用一棵红黑树（Red-Black Tree）来管理所有可运行进程。这是一棵自平衡二叉搜索树，以 vruntime 为 key 排序。

[图：CFS 红黑树结构示意图，展示 vruntime 从小到大排列，最左节点为下一个被调度的进程]

红黑树的关键特性是：**最左边的节点就是 vruntime 最小的进程**，也就是下一次应该被调度执行的进程。调度器不需要遍历整棵树，只需要缓存一个指向最左节点的指针（`rb_leftmost`），就能在 O(1) 时间内找到下一个要运行的进程。

进程的入队和出队操作（插入和删除）的时间复杂度都是 O(log N)，其中 N 是可运行进程的数量。即使系统中有几百个进程，log2(500) ≈ 9，调度开销依然很小。

在 Perfetto 中，当一个进程从 Runnable 变为 Running，或者从 Running 被抢占回到 Runnable，对应的就是一次红黑树的出队和入队操作。如果看到大量短暂的 Running → Runnable 切换，往往意味着有更高优先级的进程频繁抢占。

### Linux 6.6 基线下怎么看“时间片”

很多资料会用 `target_slice = sched_period × (weight / total_weight)` 解释经典 CFS。拿它说明"权重越高，分到的 CPU 份额越大"没有问题，但它不是 Linux 6.6 fair class 的当前源码锚点。

Linux 官方 CFS 文档明确写了两件事。第一，CFS 不再按旧调度器那样讨论固定 timeslice。第二，当前只保留 `base_slice_ns` 这个中心 tunable。到了 Linux 6.6，fair class 的选人逻辑已经按 EEVDF 路径运行，源码里参与决策的是 `entity_eligible()`、`pick_eevdf()` 和 `update_deadline()` 这一组函数。

```c
// kernel/sched/fair.c, Linux 6.6
static void update_deadline(struct cfs_rq *cfs_rq, struct sched_entity *se)
{
    se->slice = sysctl_sched_base_slice;
    se->deadline = se->vruntime + calc_delta_fair(se->slice, se);
}
```

沿着 6.6 源码看，任务先按 vruntime 记账，再用 `base_slice` 和权重换算出 virtual deadline；调度器只在 eligible task 里，通过 `pick_eevdf()` 选择 virtual deadline 最早的实体。拿 6.6 Trace 或源码做核对时，应该沿着这条路径看，不要再把 `sched_period()` 当成现行实现。

如果这里是为了说明经典 CFS 的直觉，保留"权重决定 CPU 份额"这层解释就够了，但要明确它服务于原理理解，不是 Linux 6.6 fair.c 的现状描述。

## 调度策略与优先级体系

Linux 内核不是只靠一种策略调度所有线程。对用户空间可见的普通策略，可以把层级关系概括成：

**SCHED_DEADLINE → RT 类(SCHED_FIFO / SCHED_RR)→ fair 类(SCHED_OTHER / SCHED_BATCH)→ SCHED_IDLE**

如果把内核内部的 `stop_sched_class` 也算上，它还在最上面。但那不是用户空间可以直接设置的策略，这里先不展开。

### 先分"策略层级”，再分"static priority 编号”

这里最容易混淆的是两套概念：

1. **策略层级**，决定不同调度类谁先拿到 CPU。
2. **static priority**，是内核给 RT / fair 线程分配的内部编号。

把两套概念拆开后，规则就清楚了：

| 层级 | 用户态策略 | `sched_priority` | 内核编号 / 备注 |
| --- | --- | --- | --- |
| Deadline | `SCHED_DEADLINE` | 不使用 `sched_priority`，而是 `sched_runtime` / `sched_deadline` / `sched_period` | deadline class 高于 RT |
| Real-time | `SCHED_FIFO`、`SCHED_RR` | 1..99，数值越大优先级越高 | 内核把 RT 区间预留为 0..99，数值越小优先级越高 |
| Fair | `SCHED_OTHER`、`SCHED_BATCH` | 固定为 0 | `NICE_TO_PRIO(nice)`，范围 100..139，对应 nice -20..19 |
| Idle | `SCHED_IDLE` | 固定为 0 | `sched_priority` 仍为 0，由 idle sched class 排在 fair 之后 |

把用户态参数和内核编号对起来看，Linux 6.6 `__normal_prio()` 的规则很直接：RT 线程走 `MAX_RT_PRIO - 1 - rt_prio`，所以 `sched_priority=99` 落在 RT 区间最前端；fair 线程走 `NICE_TO_PRIO(nice)`，也就是 Perfetto 里常见的 `priority = 120 + nice`。这两套编号方向相反，混着看最容易把表写错。

`SCHED_FIFO` 和 `SCHED_RR` 也不是“谁永远压谁”的关系。它们都属于 RT 类，先比较 `sched_priority`。只有两个线程的 RT 优先级相同，策略差异才开始生效：`SCHED_FIFO` 不做同级轮转，`SCHED_RR` 会按 quantum 在同优先级队列里轮转。

### SCHED_DEADLINE：按截止时间调度

`SCHED_DEADLINE` 通过 `sched_runtime`、`sched_deadline`、`sched_period` 描述任务预算和周期，内核实现采用 GEDF + CBS。它的层级高于 RT 类，通常需要 `CAP_SYS_NICE`。普通 Android App 几乎不会直接碰到它，但在讲"Linux 调度策略总表"时不能把它漏掉。

### SCHED_FIFO 和 SCHED_RR：实时调度

**`SCHED_FIFO`**：线程一旦拿到 CPU，就会一直运行到主动让出、阻塞，或者被更高 RT 优先级线程抢占为止。

**`SCHED_RR`**:和 `SCHED_FIFO` 同属 RT 类，但同优先级线程之间会按 round-robin quantum 轮转。

在 Android 中，实时调度主要出现在对时序非常敏感的线程里。最典型的是 AudioFlinger 的 FastMixer。音频周期通常只有几毫秒，一次调度抖动就可能变成 audible glitch。

### SCHED_OTHER / SCHED_BATCH：绝大多数线程的归宿

Android 上绝大多数应用线程和系统服务线程都落在 fair 类里，也就是 `SCHED_OTHER` 或 `SCHED_BATCH`。资料里经常把 `SCHED_OTHER` 写成 `SCHED_NORMAL`，讲的是同一档默认普通线程。

`SCHED_OTHER` 是默认策略，受 nice 值和 CFS / EEVDF 逻辑影响。`SCHED_BATCH` 也走 fair class，但更偏向批处理工作负载，不给交互式唤醒额外偏置。Android 设备上直接把线程设成 `SCHED_BATCH` 的场景并不多，但它在策略层级上和 `SCHED_OTHER` 属于同一档。

### SCHED_IDLE：最低优先级

`SCHED_IDLE` 的优先级低于其他普通策略，连 nice +19 都压不过它。Android 产品代码里不常直接设置 `SCHED_IDLE`，但极低优先级的后台维护任务会采用类似思路，尽量把资源让给前台和实时线程。

## nice 值与权重的换算关系

nice 值是用户空间调节进程优先级的主要接口。范围从 -20（最高优先级）到 +19（最低优先级），默认值为 0。

### 从 nice 值到 CFS 权重

CFS 不直接使用 nice 值，而是通过一个查表将 nice 值映射为权重。内核中的 `prio_to_weight[]` 数组定义了这个映射关系：

| nice 值 | 权重 | 相对比例（以 nice 0 为基准） |
|---------|------|------------------------------|
| -20 | 88761 | × 86.7 |
| -10 | 9548 | × 9.3 |
| -5 | 3121 | × 3.0 |
| 0 | 1024 | × 1.0（基准） |
| 5 | 335 | × 0.33 |
| 10 | 110 | × 0.11 |
| 15 | 36 | × 0.035 |
| 19 | 15 | × 0.015 |

(注：prio_to_weight[] 定义在 Linux 内核源码中，不在 AOSP platform tag 里)]

从这个表中我们可以看出几个关键信息：

**每增加 1 个 nice 值，CPU 份额大约减少 10%。** 这个比例是内核有意设计的。nice 值 +1 表示进程“更客气”（nice），愿意让出大约 10% 的 CPU 时间给其他进程。反过来，nice 值 -1 的进程比默认进程多获得大约 10% 的 CPU 时间。

**极端值的差距巨大。** nice -20 的权重是 88761，而 nice +19 的权重只有 15。按这张表计算，一个 nice -20 的进程获得的 CPU 时间是 nice +19 进程的将近 6000 倍。

### Android 中的 nice 值实践

Android Framework 通过 `Process.setThreadPriority()` 来设置线程的 nice 值。几个常见的优先级设置：

```java
Process.setThreadPriority(Process.THREAD_PRIORITY_DEFAULT)      // nice 0
Process.setThreadPriority(Process.THREAD_PRIORITY_FOREGROUND)    // nice -2
Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND)    // nice 10
Process.setThreadPriority(Process.THREAD_PRIORITY_DISPLAY)       // nice -4
Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_DISPLAY)// nice -8
```

当应用切换到后台时，系统会将其线程的 nice 值提升（优先级降低），减少对前台应用的影响。这是 oom_adj 调整机制的一部分——第 1.3 节（进程模型与生命周期管理）中有详细讨论。

在 Perfetto 中，点击一个 CPU 调度切片，详情面板会显示该线程的 `priority` 值。这个值是内核内部优先级(100-139)，换算关系是 `priority = 120 + nice`。所以看到 priority=122 就对应 nice=2，priority=116 就对应 nice=-4。

## CPU Affinity 与 cpuset 绑核控制

### sched_setaffinity：控制线程能跑在哪些 CPU 上

`sched_setaffinity()` 是 Linux 提供的系统调用，用于设置一个线程的 CPU 亲和性（CPU Affinity）——也就是限制它只能在哪些 CPU 核心上运行。

```c
int sched_setaffinity(pid_t pid, size_t cpusetsize, const cpu_set_t *mask);
```

参数 `mask` 是一个位掩码，每一位对应一个 CPU 核心。例如，要把线程限制在 CPU 6 和 CPU 7（通常是大小核架构中的大核）上运行：

```c
cpu_set_t mask;
CPU_ZERO(&mask);
CPU_SET(6, &mask);
CPU_SET(7, &mask);
sched_setaffinity(tid, sizeof(mask), &mask);
```

### 为什么需要绑核：大小核架构的调度陷阱

现代手机 SoC 普遍采用 big.LITTLE（大小核）异构架构，甚至 big.Medium.LITTLE（大中小核）架构。以高通骁龙 8 Gen 3 为例，它有 1 个超大核（Prime）、3 个大核、4 个小核。

在这种架构下，调度器的选核决策直接影响线程的性能表现。一个 CPU 密集型任务如果被调度到小核上，即使小核跑在最高频率，性能也只有大核的一半甚至更少。这在 Perfetto 中表现为：线程处于 Running 状态但执行缓慢，Wall 时间远大于 CPU 时间。

**绑核的典型应用场景**是把 RenderThread 固定到大核上。RenderThread 负责将主线程生成的 DisplayList 转换为 GPU 指令，这个过程中的 OpenGL/Vulkan 调用（尤其是 draw call 的准备阶段）是 CPU 密集的。如果 RenderThread 被调度到小核，帧的提交时间就会变长，导致掉帧。

### Android 中绑核和 CPU 可用范围的几条路径

Android 里要区分两件事：**线程 affinity mask** 和 **进程组 cpuset mask**。线程最终能跑在哪些 CPU 上，取的是两者的交集。只盯着 `sched_setaffinity()`，会漏掉系统层的 cpuset 限制。

**1. `sched_setaffinity()`：最常见的线程级接口**

Native 层最常见的做法还是直接调用 `sched_setaffinity()`。这里传入的是 Linux TID，也就是线程 ID，通常用 `gettid()` 取得。

**2. `pthread_setaffinity_np()`:Android 16 / API 36 起可用的 pthread 封装**

AOSP android-16.0.0_r1 的 `bionic/libc/include/pthread.h` 已经声明了 `pthread_getaffinity_np()` 和 `pthread_setaffinity_np()`，并标成 `__INTRODUCED_IN(36)`，注释里也写了 "Available since API level 36"。所以"Android 上没有 `pthread_setaffinity_np()`"这句话只适用于旧版本。面向 API 36 之前的设备或旧 NDK target 时，兼容写法仍然是 `sched_setaffinity(gettid(), ...)`;面向新平台时，直接按 `pthread_t` 调 `pthread_setaffinity_np()` 也成立。

**3. cpuset / task profiles：系统级 CPU 可用范围**

Android 更常见的控制入口是 task profiles。Framework 通过 `libprocessgroup` 的 `SetTaskProfiles()` / `SetProcessProfiles()` 把逻辑状态写进 cgroup controller。AOSP android-16.0.0_r1 的 `system/core/libprocessgroup/profiles/task_profiles.json` 里，`ProcessCapacityHigh` 会加入 `cpuset/foreground`，`ProcessCapacityMax` 会加入 `cpuset/top-app`;`HighPerformance` / `MaxPerformance` 则映射到 `cpu/foreground` / `cpu/top-app`。

```text
/dev/cpuset/
├── foreground/
├── foreground_window/
├── background/
├── system-background/
└── top-app/
```

当应用从后台切到前台时，Perfetto 里看到线程从小核迁到大核，很多时候不是某个线程手工调用了 `sched_setaffinity()`，而是它所在进程组的 cpuset / cpu profile 变了。分析这类问题时，要同时看 thread affinity、cpuset 和调频策略。

### 绑核的注意事项

### 硬件迁移效率对绑核必要性的影响

骁龙 8 Elite 等基于 ARMv9.2 的 SoC 将跨核迁移开销压缩到了 1.5μs - 3.5μs 级别，远低于前代平台的 10μs+。这种高频率、低损耗的迁移使调度器可以更激进地进行负载均衡——线程在大核和小核之间来回迁移的性能代价变小了。从性能分析角度看：

- 在 ARMv9.2 平台上，线程被调度到小核不一定是性能问题。迁移成本足够低时，调度器的动态选核可能比硬绑核更优
- 手动 `sched_setaffinity()` 绑核的收益在新型 SoC 上会收窄，绑核前更应该先用 Perfetto 对比绑与不绑的实际 wall time 差异
- 功耗角度上，让调度器自由选核可以利用小核处理短突发任务，降低整体能耗

绑核不是银弹。过度使用绑核会导致：

- **负载不均衡**:强制绑到大核后，如果大核已经有高优先级任务，线程反而要排队等待
- **功耗增加**:大核的能耗远高于小核，不必要的绑核会显著增加功耗
- **灵活性丧失**:绑核绕过了调度器的动态调度，在某些场景下反而不如让调度器自己决策

实践中，绑核应该作为“有明确性能瓶颈且已确认是调度问题”后的针对性优化手段，而不是常规操作。

## 调度延迟：Perfetto 中的观察方法

理解了调度器的原理后，下面把这些机制对应到 Perfetto，重点看调度相关问题怎么定位。

### Runnable 状态：调度延迟的直接证据

在 Perfetto 中，线程处于 Runnable 状态（浅绿色）的时间，就是它"准备好运行但还没被调度到 CPU"的等待时间。这段时间就是**调度延迟**(Scheduling Latency)。

[图：Perfetto 中线程状态示意图，标注 Running（绿色）、Runnable（浅绿色）、Sleep（白色）、Uninterruptible Sleep（橙色）]

Runnable 状态有三种典型的进入方式，理解它们有助于判断调度延迟的原因：

**1. 从 Sleep 中唤醒（Wake-up）**：最常见的场景。线程等待的资源（锁、I/O、Binder 回复）已经就绪，被唤醒后进入 Runnable,等待调度器选中。如果 Runnable 时间很长，说明系统负载高或者调度器没有及时响应。

**2. 用户抢占(User Preemption)**:线程的时间片用完，或者更高优先级的任务到来，调度器在从内核态返回用户态时换下当前线程。在 `sched_switch` trace 中标记为 `prev_state=R`。

**3. 内核抢占(Kernel Preemption)**:更高优先级的任务在当前线程执行内核代码期间就强行将其打断。在 trace 中标记为 `prev_state=R+`。大量 R+ 通常意味着 CPU 满载，低优先级线程频繁被抢占。

### Perfetto SQL：量化调度延迟

Perfetto 的 SQL 引擎让我们可以精确地量化调度延迟。以下是几个常用的查询：

**查找主线程调度延迟最严重的时刻：**

```sql
WITH target_thread AS (
  SELECT t.utid
  FROM thread t
  JOIN process p USING (upid)
  WHERE p.name = 'com.example.app'
    AND t.name = 'main'
  LIMIT 1
)
SELECT
  ts,
  dur / 1e6 AS runnable_time_ms
FROM thread_state
WHERE utid = (SELECT utid FROM target_thread)
  AND state = 'R'
ORDER BY dur DESC
LIMIT 20;
```

**统计线程在各 CPU 核心上的运行时间分布：**

```sql
WITH target_thread AS (
  SELECT t.utid
  FROM thread t
  JOIN process p USING (upid)
  WHERE p.name = 'com.example.app'
    AND t.name = 'RenderThread'
  LIMIT 1
)
SELECT
  cpu,
  SUM(dur) / 1e6 AS time_on_cpu_ms
FROM sched
WHERE utid = (SELECT utid FROM target_thread)
GROUP BY cpu
ORDER BY cpu;
```

如果发现 RenderThread 大量时间在 CPU 0-3（小核），就说明调度策略可能需要调整。

**Wall 时间 vs CPU 时间分析：**

在 Perfetto 中选中一个 `doFrame` 切片，对比 Wall 时间（墙上时间）和 CPU 时间：

- `Wall ≈ CPU`:计算过重，需要用火焰图定位热点函数
- `Wall >> CPU`:大量时间花在 Runnable 或 Sleep 状态，需要检查调度延迟和线程依赖

### 唤醒关系分析

Perfetto 提供了线程唤醒关系的可视化：点击一个 Running 的线程切片，UI 会显示一条箭头，指向唤醒它的源线程。这个功能基于内核的 `sched_wakeup` ftrace 事件。

常见的唤醒路径（谁唤醒了谁）:
- InputReader → InputDispatcher → 应用主线程（触摸事件传递）
- Binder 线程 → 应用主线程（跨进程回调）
- RenderThread → 主线程（渲染完成通知）

如果发现主线程长时间处于 Runnable 状态后才开始执行，查看唤醒源可以帮助判断是谁在延迟唤醒。

需要注意 `wakeup from` 信息有时不够准确，需要结合代码和上下文综合判断。

在实际分析中，调度延迟是否值得关注，先看**关键路径上的 Runnable 时间是否超过了帧周期的 10%**。以 120Hz 屏幕为例，一帧周期为 8.33ms,如果主线程在 `doFrame` 期间有超过 0.8ms 的 Runnable 等待，就需要继续往下看。60Hz 屏幕下，这个阈值约为 1.6ms。

## EEVDF:CFS 的下一代演进(Linux 6.6+)

在看完调度延迟的分析方法后，我们再补一块正在进入 Android 生态的新变化。2023 年，Linux 6.6 将 EEVDF（Earliest Eligible Virtual Deadline First）并入默认调度路径，用它替代了原来的 CFS 调度逻辑。

EEVDF 由 Peter Zijlstra 主导合入，算法理论基础来自 1995 年发表的同名论文。对 Android 性能分析来说，目前不需要逐行拆解 EEVDF 的实现细节——当前大多数 Android 设备的内核还停留在 5.x 或 6.1，EEVDF 还没到需要日常排查的地步。

更实际的意义是，当设备升级到 6.6+ 内核后，我们在 Perfetto 中看到的 Runnable 分布、交互线程延迟和抢占行为都可能变化，分析时需要知道背后的原因。

### CFS 的局限性：为什么需要替换

CFS 追求的是"所有可运行进程的 vruntime 趋于一致",这个目标保证了长期的 CPU 时间公平分配。但“公平”不等于“低延迟”——一个交互式任务（比如触摸事件处理）和一个后台计算任务在 CFS 看来是平等的竞争者，调度器并不区分"谁更需要尽快拿到 CPU"。

CFS 在实践中依赖一些启发式规则来弥补这个缺陷，比如 `sched_latency_ns`、`sched_min_granularity_ns` 等调优参数。这些参数本身是经验值，在不同工作负载下表现不一，也给厂商的调优带来了负担。EEVDF 的核心改进就是用更严格的算法替代这些启发式规则。

### EEVDF 的核心机制：资格 + 虚拟截止时间

EEVDF 的调度决策分两步走：先判断"谁有资格运行",再在有资格的进程中选出"最紧急的"。

**第一步：资格判定(Eligibility)。** 每个进程维护一个"lag"值，表示它"欠"了多少 CPU 时间或“透支”了多少。lag 的计算方式是：一个进程按权重应该获得的理想运行时间，减去它实际获得的运行时间。lag ≥ 0 表示这个进程还没有用完它的公平份额，有资格参与调度；lag < 0 表示它已经超支了，需要等一等，让其他进程先跑。

这个机制解决了一个 CFS 的实际问题：在 CFS 中，一个刚从睡眠中醒来的进程，其 vruntime 可能远小于其他进程，导致它在唤醒后立刻"霸占"CPU 很长时间来追平 vruntime。EEVDF 的资格判定机制能更精确地控制这种行为——如果进程已经超支了，即使刚醒来也要排队等资格恢复。

**第二步：虚拟截止时间(Virtual Deadline)。** 对于有资格运行的进程，EEVDF 为每个进程计算一个虚拟截止时间。调度器选择虚拟截止时间最早的进程来执行。虚拟截止时间的计算考虑了进程申请的时间片长度——申请短时间片的进程（通常是延迟敏感型任务）会得到更早的截止时间，从而被优先调度。

CFS 的调度标准只有一个维度——vruntime 谁最小，不区分任务对延迟的敏感程度。EEVDF 通过引入"截止时间"概念，让延迟敏感型任务天然地排在前面，而不需要额外的启发式规则。

### 关键差异总结

| 维度 | CFS | EEVDF |
|------|-----|-------|
| 选核标准 | vruntime 最小 | 有资格且虚拟截止时间最早 |
| 延迟优化 | 依赖启发式参数（sched_min_granularity 等） | 算法内建，通过时间片请求体现 |
| 睡眠任务处理 | 唤醒后可能"报复性"占用 CPU | lag 衰减机制防止超支 |
| 时间片请求 | 被动接受调度器分配 | 任务可通过 sched_setattr() 主动申请(100μs~100ms) |
| 调优复杂度 | 需要调整多个 sysctl 参数 | 算法驱动，大幅减少调优需求 |

### vlag 的量化诊断（EEVDF 内核 6.6+）

EEVDF 调度器中每个任务维护一个 vlag（virtual lag）值，表示该任务“被欠”或“透支”了多少 CPU 时间。vlag > 0 表示任务还没用完公平份额（系统“欠”它 CPU 时间），vlag < 0 表示任务已经超支。vlag 的绝对值越大，说明该任务的调度时机越偏离理想状态。

vlag 是 EEVDF 调度器的内部字段，stock Linux v6.6 / v6.12 和 Android common kernel 都没有通过 ftrace 或 perf_event 暴露该字段。Perfetto 也没有对应的 SQL 表或轨道。要量化调度公平性，只能基于已有的 `sched_switch`、`sched_wakeup`、`thread_state` 轨道观察 Runnable 等待时间：

- 如果主线程在关键路径（如 `doFrame`）期间 Runnable 等待时间持续偏长，说明它被其他任务“抢”了太多 CPU 时间
- 如果后台线程几乎不等待，说明它在大量占用 CPU 份额

如果需要读取 vlag，需要通过 vendor tracepoint、BPF 程序或 kprobe 自行采集，这不是 Perfetto 默认支持的数据源。

```sql
-- 观察 Runnable 等待时间分布（替代 vlag 的实战方法）
-- 替换 '目标线程名'
SELECT
  s.ts,
  s.dur / 1e6 AS runnable_ms
FROM thread_state s
JOIN thread t ON s.utid = t.utid
WHERE t.name = '目标线程名'
  AND s.state = 'R'
ORDER BY s.ts
LIMIT 100;
```

### 调度器关键可调参数

EEVDF 将 CFS 的多个启发式调度参数收敛到 debugfs 暴露的 `base_slice_ns`（源码变量 `sysctl_sched_base_slice`）这个核心参数。Linux 6.6+ fair class 的关键可调项：

| 参数 | 默认值 | 作用 | 对 Android 性能分析的意义 |
|------|--------|------|--------------------------|
| `base_slice_ns` / `sysctl_sched_base_slice` | 0.75ms × (1 + ilog(ncpus))，8 核设备约 3ms | 替代旧 `sched_min_granularity_ns`，定义调度实体申请的基本时间片长度 | 直接影响任务在 CPU 上的最短驻留时间；调大→吞吐优先，调小→响应优先 |
| `sched_wakeup_granularity_ns` | 已移除 (EEVDF) | 旧 CFS 参数，控制唤醒抢占粒度 | EEVDF 下通过 lag/virtual deadline 自动处理唤醒抢占，不再需要手动调整 |
| `sched_latency_ns` | 已弱化 (EEVDF) | 旧 CFS 参数，定义调度周期的目标延迟 | EEVDF 用 `base_slice_ns` × runnable 数量推导，不再作为独立 tunable |
| `sched_nr_migrate` | 8 | 控制 RT 任务迁移时最多移动多少个 fair class 任务 | 大核负载均衡场景下可能影响迁移效率，一般不需要调整 |

检查设备实际值：

```bash
# Linux 6.6+，需要 root、CONFIG_SCHED_DEBUG 且已挂载 debugfs
cat /sys/kernel/debug/sched/base_slice_ns
# 查看 sched debugfs 下暴露的调度参数
ls /sys/kernel/debug/sched/
```

在 Perfetto 中观察调度行为时，如果发现大量短时间 Runnable→Running→Runnable 切换（微秒级），先检查 `/sys/kernel/debug/sched/base_slice_ns` 是否偏小——slice 偏小会让 EEVDF 更频繁地在 eligible entity 之间切换。`base_slice_ns` 偏大则倾向于增加单次驻留和响应延迟。这类分析需要对照 `sched_switch` 事件的时间间隔与 `base_slice_ns` 的关系。

### Real-time 调度在 Android 版本中的演进

Real-time 线程（SCHED_FIFO/SCHED_RR）在 Android 中的使用策略随版本逐步严格：

| Android 版本 | RT 调度关键变化 |
|---|---|
| Android 4.1 (Project Butter) | AudioFlinger FastMixer 引入 SCHED_FIFO，音频管线首次获得 RT 保证 |
| Android 7.0 | 后台进程 nice 值统一提升至 10+，减少后台调度干扰 |
| Android 9 | `Process.setThreadPriority()` 中 THREAD_PRIORITY_DISPLAY(-4) 标注 "Applications can not normally change to this priority" |
| Android 12 | GKI 5.10 迁移到 UClamp，SchedTune 退场；RT 线程管理从 vendor 调度器统一到主线 cgroup |
| Android 14+ | 后台执行限制继续加严，`cpuset/background` 收窄到小核子集，RT 线程几乎只存在于系统服务 |
| Android 16 (GKI 6.1) | 默认 fair class 调度仍为 CFS 逻辑；sched_ext 基础设施在 common kernel 6.12 中可用但未默认启用 |

### 对 Android 性能分析的预期影响

目前（截至 Android 16），主流 Android 设备的内核版本尚未大规模采用 EEVDF。但考虑到：

1. Google Pixel 设备通常使用较新的内核（Pixel 9 系列已使用 Linux 6.1），后续迭代可能升级到 6.6+
2. MTK 和高通的下一代平台也在推进内核版本更新
3. GKI（Generic Kernel Image）机制使得内核升级的门槛降低

当设备开始使用 EEVDF 时，我们在 Perfetto 中可能会观察到以下变化：

- **交互式应用的 Runnable 时间减少**:触摸事件处理线程等延迟敏感型任务被调度的延迟可能降低
- **后台任务的 CPU 占用更平滑**:lag 衰减机制防止后台任务在唤醒后突然抢占大量 CPU
- **CPU 频率波动减少**:更可预测的调度行为意味着 `schedutil` 调频器可以做出更稳定的频率决策

在 Perfetto 中，如果内核启用了 EEVDF,可以通过以下 SQL 查询观察调度行为的分布变化（需要内核 6.6+ 并启用对应 ftrace 事件）:

```sql
-- 观察特定线程的调度延迟分布
-- 用于对比 CFS 和 EEVDF 内核下主线程的 Runnable 等待时间分布
WITH target_thread AS (
  SELECT t.utid
  FROM thread t
  JOIN process p USING (upid)
  WHERE p.name = 'com.example.app'
    AND t.name = 'main'
  LIMIT 1
)
SELECT
  CASE
    WHEN dur / 1e6 < 1 THEN '< 1ms'
    WHEN dur / 1e6 < 5 THEN '1-5ms'
    WHEN dur / 1e6 < 10 THEN '5-10ms'
    ELSE '> 10ms'
  END AS latency_bucket,
  COUNT(*) AS count
FROM thread_state
WHERE utid = (SELECT utid FROM target_thread)
  AND state = 'R'
GROUP BY latency_bucket
ORDER BY latency_bucket;
```

如果未来在 EEVDF 内核上观察到调度延迟分布明显向左移（更多 < 1ms），说明 EEVDF 的延迟优化正在生效。

## Real-time 线程在 Android 中的使用

[图：Perfetto 中 SCHED_FIFO 线程的 CPU 调度切片示意，标注 AudioFlinger/FastMixer 线程与普通 SCHED_NORMAL 线程的优先级差异]

Android 中使用 SCHED_FIFO 实时调度的场景主要集中在两个系统服务：

**AudioFlinger 的 FastMixer 线程**：音频处理有严格的时序要求。FastMixer 需要在每个音频周期（通常为 2-4ms）内完成混音操作，任何延迟都会导致音频 underrun。从 Android 4.1（"Project Butter"）开始，FastMixer 就使用 SCHED_FIFO 来保证实时性。

**SurfaceFlinger 的部分关键路径**:虽然 SurfaceFlinger 的主循环使用 SCHED_NORMAL(CFS)，但在某些厂商的实现中，与显示硬件直接交互的线程可能被设置为实时优先级。

实时线程如果失控（比如进入死循环），会导致整个系统无响应——实时优先级高于所有普通进程，连 watchdog 都抢不到 CPU。因此 Android 对 SCHED_FIFO 的使用非常谨慎，只在需要硬实时保证的场景使用。

## SchedTune 与 UClamp:Android 的调度增强

在前面的章节中我们讨论了 CFS（以及未来的 EEVDF）如何通过 nice 值和权重来分配 CPU 时间。但 nice 值只解决了“谁多谁少”的问题，没有解决“在哪个核心上跑”和“以什么频率跑”的问题。在大小核异构架构下，这两个问题的答案直接决定了性能表现。

SchedTune 和 UClamp 就是 Android 用来回答这两个问题的机制。它们的核心思路是相同的：让 Android Framework 能够向内核调度器传递“这个任务需要什么性能级别”的提示(hint)，从而影响 CPU 选核和调频决策。

### SchedTune：Android 专属的 Boost 机制

SchedTune 是旧版厂商内核（Android 11 及更早）的专有调度增强机制，不在主线 Linux 内核中，也不存在于 Android common kernel 6.1/6.6/6.12 或 GKI 设备。Android 12+ 设备的主路径已转向 UClamp + cpu controller（见下节）。下文 SchedTune 描述适用于仍在维护旧版厂商内核的场景，或需要理解历史 boost 机制的读者。

SchedTune 最早随 EAS（Energy Aware Scheduling）引入，以 cgroup 控制器的形式存在，允许 Android Framework 按进程组设置调度策略。核心参数是 `schedtune.boost`，取值范围 0~100。当一个任务的 boost 值大于 0 时，调度器会将该任务的"感知利用率"(perceived utilization)人为放大——让调度器和调频器以为这个任务比实际更忙。

```bash
# 示例:查看前台应用进程组的 boost 设置(仅旧版厂商内核)
cat /dev/stune/foreground/schedtune.boost
# 输出: 10

# 顶部应用通常有更高的 boost
cat /dev/stune/top-app/schedtune.boost
# 输出: 20
```

boost 的效果体现在两个层面：

**CPU 频率提升**:`schedutil` 调频器使用 PELT（Per-Entity Load Tracking）信号来决定 CPU 频率。boost 放大了这个信号，导致调频器为当前 CPU 选择更高的频率。当用户触摸屏幕时，Android Framework 会临时提高前台应用的 boost 值（所谓的“touch boost”），让 CPU 频率迅速拉高以应对即将到来的 UI 更新。

**选核偏好**:在 EAS（Energy Aware Scheduling）启用的系统上，调度器在选核时会估算将任务放到不同核心上的能耗差异。boost 值高的任务会被优先放在大核上——大核虽然单位时间能耗高，但能在更短时间内完成任务，总能耗反而可能更低。这个策略也解释了为什么绑核（第 5.3 节详述）在配合 boost 时效果最好。

### UClamp：上游化的通用方案

UClamp（Utilization Clamping）从 Linux 5.3 进入主线。它和 SchedTune 的目标接近，都是把"这个任务至少/至多需要多强的 CPU 性能"这个提示交给调度器和 `schedutil`。

UClamp 为任务或任务组提供两个核心参数：

**`UCLAMP_MIN`**:利用率下限。即使任务实际 util 很低，调度器也会把它当成至少达到这个值。结果通常是更高频率、更偏向高 capacity CPU。

**`UCLAMP_MAX`**:利用率上限。任务再忙也不会被视为超过这个值。后台工作常用它来限制频率和大核占用。

Linux 既支持按任务接口设置，也支持按 cgroup controller 设置。单线程实验时，内核通常会暴露类似下面的 per-task 接口：

```bash
# per-task UClamp 通过 sched_setattr() 设置，命令行可用 uclampset:
uclampset -m 256 -M 512 <command>

# 或在代码中使用 sched_setattr()（需 CAP_SYS_NICE 或 root）:
# sched_attr.sched_util_min = 256;
# sched_attr.sched_util_max = 512;
# sched_setattr(pid, &sched_attr, 0);
```

Android 产品机上更常见的入口是 cgroup controller 或 task profiles，而不是手动调用 `sched_setattr`：

```bash
# cgroup cpu controller（Android 12+ / GKI 5.10+）
echo 256 > /dev/cgroot/cpu/<cgroup>/cpu.uclamp.min
echo 512 > /dev/cgroot/cpu/<cgroup>/cpu.uclamp.max
```

Android 产品机上更常见的入口是 task profiles,而不是手写 `/proc`。

### Android userspace 到 cpuset / schedtune / uclamp 的控制链

把 Android 的控制链顺着 userspace 往内核拆开，Perfetto 里的调度结果会更容易解释：

1. **ActivityManagerService / WindowManager / Power HAL 改变场景状态。** 例如应用进入 `top-app`、退到后台，或者收到 touch / launch / animation 这类性能提示。
2. **`libprocessgroup` 应用 task profile。** Framework 通过 `SetTaskProfiles()` / `SetProcessProfiles()` 把逻辑状态翻译成 cgroup 操作。
3. **task profile 写入 cpuset / schedtune / cpu controller。** 这里才是 Android 落到内核的控制点。
4. **调度器和调频器执行结果。** 最终表现为线程可用 CPU 集合变化、选核偏好变化，以及 CPU frequency 更快拉起。

把版本差异展开后，这条链会清楚很多。

**Android 10-11 的常见路径**

- `ProcessCapacityHigh` / `ProcessCapacityMax` 把进程放进 `cpuset/foreground` / `cpuset/top-app`
- `HighPerformance` / `MaxPerformance` 把进程放进 `schedtune/foreground` / `schedtune/top-app`
- 同一份 `task_profiles.json` 里已经同时声明了 `schedtune.boost`、`schedtune.prefer_idle` 和 `cpu.uclamp.min` / `cpu.uclamp.max`，所以 11 时代设备很容易出现 `cpuset + schedtune + uclamp` 混用

**Android 12+ / GKI 5.10+ 的常见路径**

- `ProcessCapacityHigh` / `ProcessCapacityMax` 继续控制 `cpuset/foreground` / `cpuset/top-app`
- `HighPerformance` / `MaxPerformance` 改为进入 `cpu/foreground` / `cpu/top-app`
- `UClampMin`、`UClampMax`、`UClampLatencySensitive` 再落到 `cpu.uclamp.min`、`cpu.uclamp.max`、`cpu.uclamp.latency_sensitive`

沿着这条链看 Perfetto,主线程或 RenderThread 从小核迁到大核、CPU frequency 一起抬升时，先查进程组 profile 有没有从 `foreground` 切到 `top-app`，再看对应 cpuset / cpu controller 文件有没有变化。只盯线程自己有没有调 `sched_setaffinity()`，很容易漏掉关键控制点。

### SchedTune 与 UClamp 的版本边界

主线 Linux 的 `uclamp` 从 5.3 合入。版本边界拆开看：

| Android 版本 | GKI 内核 | Boost 机制 | task_profiles.json 中的关键 controller |
|---|---|---|---|
| 10-11 | 厂商 4.x/5.x | SchedTune(`/dev/stune`) | `schedtune.boost` + `cpu.uclamp.*` 共存 |
| 12-14 | GKI 5.10 | UClamp(`/dev/cgroot/cpu`) | `schedtune` controller 退场，改用 `cpu.uclamp.min/max` |
| 15-17 | GKI 6.1/6.6/6.12 | UClamp | 同上，无 SchedTune |

厂商内核是否还保留 `stune`，要以目标设备实际 cgroup 布局为准——在 shell 里 `ls /dev/stune/` 存在就说明还在用旧路径。

### 在 Perfetto 中的观察方法

UClamp/SchedTune 在 Perfetto 中没有独立 Track,它们的效果只能通过调度行为的间接影响来观察。具体来说，关注两个 Track:

**CPU Frequency Track**:在 Perfetto 的 CPU 行下方，有一条显示频率变化的曲线。当一个前台应用开始渲染时，如果 UClamp_MIN 设置正确，我们应该看到 CPU 频率迅速提升到较高水平（比如从 300MHz 跳到 1.8GHz）。如果频率爬升缓慢，可能是 UClamp 配置不当或者调频器没有及时响应。

[图：Perfetto CPU Frequency Track 示意，标注 touch boost 触发后频率快速爬升的区域]

**CPU Scheduling Track（选核观察）**:通过观察线程在不同 CPU 核心之间的迁移，可以判断 boost/UClamp 是否影响了选核。被 boost 的线程应该更频繁地出现在大核（通常是编号较大的核心，如 CPU 4-7 或 CPU 6-7）上。可以使用以下 SQL 查询验证：

```sql
-- 对比线程在大核(big)与小核(LITTLE)上的运行时间分布
-- 注意:cpu >= 4 的阈值因设备而异,需根据实际 CPU 拓扑调整
WITH target_thread AS (
  SELECT t.utid
  FROM thread t
  JOIN process p USING (upid)
  WHERE p.name = 'com.example.app'
    AND t.name = 'RenderThread'
  LIMIT 1
)
SELECT
  cpu,
  CASE WHEN cpu >= 4 THEN 'big' ELSE 'LITTLE' END AS core_type,
  SUM(dur) / 1e6 AS time_ms
FROM sched
WHERE utid = (SELECT utid FROM target_thread)
GROUP BY core_type
ORDER BY core_type;
```

如果发现一个被标记为重要的线程大量时间在小核上运行，就需要检查 boost/UClamp 的设置是否生效，或者 cpuset 是否限制了该线程的可用核心。

## 常见问题与误区

### "线程优先级越高，执行越快"

错误。优先级（nice 值）影响的是**CPU 时间分配的比例**,而不是执行速度。一个 nice -20 的线程和一个 nice 0 的线程运行同样的代码，单次执行的时间是一样的。区别在于，在 CPU 竞争时，nice -20 的线程会获得更多的 CPU 时间份额。

### "绑到大核就一定更快"

不一定。如果大核已经被其他高优先级任务占满，绑到大核反而会增加排队时间。绑核前应该先在 Perfetto 中观察目标 CPU 的负载情况。

### "调度延迟是系统的问题，App 无能为力"

虽然调度是内核的职责，但 App 可以通过合理设置线程优先级、减少锁竞争、避免在关键路径上发起 Binder 调用等方式，减少调度延迟对自己的影响。在 Perfetto 中看到的很多“调度问题”,根因往往是应用层的代码设计。

### "看到大量 Runnable 就是调度器有问题"

不一定。Runnable 状态本身是正常的——线程不可能永远在 Running。只有当 Runnable 时间在关键路径（如主线程的 doFrame 期间）中占比过高时，才需要关注。

### 进程优先级与内存回收的衔接

调度优先级（nice 值、RT priority）与进程内存回收优先级（oom_score_adj）是两套独立但联动的体系。前台进程同时拥有更低的 nice 值和更低的 oom_score_adj，后台进程则两方面都被降级。两者通过 Android Framework 的 `ActivityManagerService.updateOomAdjLocked()` 协调：进程状态变化时，AMS 同时更新 cgroup cpuset/cpu profile（影响调度）和 oom_score_adj（影响 lmkd 杀进程决策）。

Android OOM Adj 分数体系、lmkd PSI 监控机制和 TrimMemory 回调的完整源码分析见 §7.3「内存回收」。本节只覆盖与调度直接相关的交叉点：进程从 `top-app` 降到 `background` 时，cpuset 可用 CPU 集合收窄、cpu.uclamp.min 归零、nice 值提升，三者叠加让后台进程对前台调度的干扰降到最低。

## 调度问题的诊断决策框架

在 Perfetto 中发现调度相关性能问题时，按以下路径逐步定位：

**Step 1：确认是否属于调度层问题。** 选中关键路径切片（如 `doFrame`），对比 Wall 时间与 CPU 时间。如果 `Wall ≈ CPU`，瓶颈是计算过重而非调度；如果 `Wall >> CPU`，差异来自 Runnable 等待或 Sleep 阻塞。

**Step 2：区分 Runnable 等待与 Sleep 阻塞。** Runnable（浅绿色）是调度延迟——线程准备好但没拿到 CPU；Sleep（白色）是线程在等锁、I/O、Binder 回复。两者的优化方向完全不同。

**Step 3：Runnable 等待→检查系统负载。** 用 Perfetto SQL 统计对应时间段内各 CPU 的利用率。如果多数 CPU > 90% 满载，调度延迟是系统级负载问题；如果 CPU 有空闲但线程仍在等，检查线程的 cpuset 限制和 affinity mask。

```sql
-- 检查特定时间窗口内 CPU 负载
SELECT
  cpu,
  SUM(dur) / (MAX(ts + dur) - MIN(ts)) * 100 AS cpu_util_pct
FROM sched
WHERE ts BETWEEN ${start_ts} AND ${end_ts}
GROUP BY cpu
ORDER BY cpu;
```

**Step 4：检查 UClamp / cpuset 配置是否生效。** 前台应用主线程和 RenderThread 应该在 `top-app` cpuset 中（可访问大核）。用以下信号验证：

- 线程运行在哪些 CPU 编号上（`sched` 表按 `cpu` 分组）
- CPU 频率是否在关键时刻拉起(CPU Frequency Track)
- 进程是否从 `foreground` cpuset 迁移到 `top-app` cpuset——通过 `/proc/<pid>/cgroup` 查看 cgroup 归属，或在 Perfetto 中观察线程迁移到更大 CPU 集合的时间点

**Step 5：决定优化动作。**

| 诊断结果 | 优化方向 |
|----------|----------|
| CPU 满载 + 关键线程 Runnable 等待长 | 减少非关键线程的 CPU 占用（降低 nice 值、裁剪后台任务） |
| 关键线程被困在小核 | 检查 cpuset profile 是否正确应用到 top-app 组 |
| CPU 频率爬升慢 | 检查 UClamp_MIN 是否配置、schedutil governor 是否生效 |
| 大量短时间 Runnable↔Running 切换 | 检查 `/sys/kernel/debug/sched/base_slice_ns` 是否偏小，EEVDF 内核下考虑调整 |
| RenderThread 在关键帧期间被抢占 | 绑核到大核（需 Perfetto 对比绑核前后 wall time 差异） |

> ⚠️ 本框架覆盖的是基于 Perfetto 可观测信号的诊断路径。针对特定应用场景的调度优化经验（如大型社交应用的消息队列线程调度策略、游戏引擎的渲染线程调度配置等）需要结合具体应用架构和实测数据，不在本节讨论范围内。

## 参考资料

- AOSP 源码：`kernel/sched/fair.c`、`kernel/sched/core.c`、`system/core/libprocessgroup/profiles/task_profiles.json`、`bionic/libc/include/pthread.h`
- [Linux CFS 设计文档](https://docs.kernel.org/scheduler/sched-design-CFS.html)
- [Linux EEVDF 调度文档](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [Linux 调度策略总览 `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html)
- [Android UClamp 文档](https://source.android.com/docs/core/perf/uclamp)
- [Perfetto CPU Scheduling 官方文档](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [高爷 - Android Perfetto 系列 9:CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)(本节核心素材来源)
- [高爷 - Systrace 线程 CPU 运行状态分析：Sleep 和 Uninterruptible Sleep 篇](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/)
- [sched_setaffinity man page](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html)
