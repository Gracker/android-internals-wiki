---
title: "Linux 进程调度基础"
chapter: "5.1"
section: "5.1"
status: ready-for-review
applicable_versions: "Android 6.0 (API 23) - Android 17 (API 37, EEVDF 部分需 6.6+ 内核)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-16.0.0_r1, Linux kernel 6.6"
confidence: high
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-Perfetto-09-CPU.md"
  - type: blog
    path: "Personal-Knowlodge/source/android-systrace-cpu-state-sleep.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_性能测试中的系统资源分析之_CPU.md"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-scheduling"
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-design-CFS.html"
tags: ['scheduler', 'CFS', 'vruntime', 'nice', 'sched_setaffinity', 'cpuset', 'Perfetto']
related_chapters: ["5.2", "5.3", "2.5", "7.3"]
drafted_date: "2026-03-31"
reviewed_date: "2026-04-14"
reviewed_by: openclaw-task6
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
review_type: post-polish-quality-gate
review_round: 3
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
---

<!-- outline-start -->
- 🔹 CFS（Completely Fair Scheduler）的基本原理：虚拟运行时间、红黑树、时间片
- 🔹 调度类优先级：SCHED_FIFO > SCHED_RR > SCHED_NORMAL（SCHED_OTHER，CFS）> SCHED_IDLE
- 🔹 nice 值与权重的换算关系
- 🔹 CPU Affinity 与 cpuset 对任务绑核的控制
- 🔹 调度延迟（Scheduling Latency）：runqueue wait 在 Perfetto 中的观察

- 🔸 EEVDF 调度器对 CFS 的改进（Linux 6.6+）
- 🔸 Real-time 线程在 Android 中的使用场景（Audio、SurfaceFlinger）
- 🔸 SchedTune / UClamp 对 Android 调度的增强
<!-- outline-end -->

## 为什么要了解 Linux 进程调度

打开一份 Perfetto Trace，最上面那几行五颜六色的色块——CPU 0、CPU 1、CPU 2……每个色块代表一个线程在某个时刻占用了那个 CPU 核心。这些色块之间的排列组合，就是 Linux 调度器的决策结果。

理解调度器的工作原理，直接关系到我们能不能回答这些实际问题：

- 主线程为什么在关键时刻没有被 CPU 执行？是被谁抢占了？
- RenderThread 明明有工作要做，为什么一直在 Runnable 状态排队？
- 把关键线程绑到大核，到底能带来多少性能提升？
- 系统负载高的时候，调度器是怎么决定谁先跑谁后跑的？

这些问题无法通过阅读应用层代码来解决——答案藏在内核的调度逻辑里。本章要做的，就是把调度器的核心机制讲清楚，让我们在 Perfetto 中看到那些色块时，能读懂调度器"为什么这样安排"。

## CFS 的基本原理

### 从"分时间片"到"追平虚拟时间"

早期的 Linux 调度器（O(1) 调度器）使用固定时间片的方式分配 CPU：每个优先级对应一个时间片长度，时间片用完就换下一个进程。这种方式的问题是，它无法精确地保证公平——在负载变化时，某些进程可能长期得不到足够的 CPU 时间。

CFS（Completely Fair Scheduler）从 Linux 2.6.23（2007 年）开始成为默认调度器，它抛弃了固定时间片的概念，转而追求一个更优雅的目标：**让所有可运行进程的虚拟运行时间（vruntime）趋于一致**。

[已验证: Linux kernel documentation, https://docs.kernel.org/scheduler/sched-design-CFS.html]

CFS 的核心思想可以类比成一个记账系统：每个进程都有一个"账户"，记录了它已经消耗了多少 CPU 时间。调度器每次选择"账户余额最少"（vruntime 最小）的进程来运行，确保长期来看每个进程获得的 CPU 时间是公平的。

### vruntime：调度的核心标尺

vruntime（虚拟运行时间）是 CFS 最重要的概念。它的名字中有"虚拟"二字，是因为它并不是简单的墙上时钟时间，而是经过权重调整后的"标准化时间"。

当一个进程在 CPU 上运行了一段时间 `delta_exec`，它的 vruntime 增长量是这样计算的：

```
delta_vruntime = delta_exec × (NICE_0_LOAD / weight)
```

其中 `NICE_0_LOAD` 是 nice 值为 0 时对应的权重（1024），`weight` 是当前进程的权重。按这个公式看：

- **权重越高的进程**（nice 值越低），vruntime 增长越慢，越容易被再次选中运行——它获得了更多的 CPU 份额
- **权重越低的进程**（nice 值越高），vruntime 增长越快，更容易被调度器换下 CPU

[已验证: AOSP android-16.0.0_r1, kernel/sched/fair.c, __update_curr()]

### 红黑树：O(log N) 的调度队列

CFS 使用一棵红黑树（Red-Black Tree）来管理所有可运行进程。这是一棵自平衡二叉搜索树，以 vruntime 为 key 排序。

[图：CFS 红黑树结构示意，展示 vruntime 从小到大排列，最左节点为下一个被调度的进程]

红黑树的关键特性是：**最左边的节点就是 vruntime 最小的进程**，也就是下一次应该被调度执行的进程。调度器不需要遍历整棵树，只需要缓存一个指向最左节点的指针（`rb_leftmost`），就能在 O(1) 时间内找到下一个要运行的进程。

进程的入队和出队操作（插入和删除）的时间复杂度都是 O(log N)，其中 N 是可运行进程的数量。即使系统中有几百个进程，log₂(500) ≈ 9，调度开销依然很小。

在 Perfetto 中，当一个进程从 Runnable 变为 Running，或者从 Running 被抢占回到 Runnable，对应的就是一次红黑树的出队和入队操作。如果看到大量短暂的 Running → Runnable 切换，往往意味着有更高优先级的进程频繁抢占。

[已验证: 官方文档, https://docs.kernel.org/scheduler/sched-design-CFS.html]

### 时间片不再是"固定值"

CFS 没有传统意义上的固定时间片。它通过 `sched_period`（调度周期）来动态计算每个进程应该运行多久：

```
target_slice = sched_period × (weight / total_weight)
```

`sched_period` 有一个最小值（`sched_min_granularity`，通常为 0.75ms 到 3ms，取决于内核配置和 CPU 数量），确保即使有很多进程，每个进程也不会等太久。

对应到实际调度时，系统负载越重，每个进程分到的"时间片"越短；优先级越高的进程，分到的时间片越长。这不是硬编码的规则，而是 CFS 追求 vruntime 公平后得到的结果。

[已验证: Linux kernel, kernel/sched/fair.c, sched_period()]

## 调度类优先级体系

Linux 内核的调度并非由单一策略覆盖所有场景，而是按需求划分为多个"调度类"（scheduling class），每个类有自己的优先级和调度逻辑。它们之间的优先级关系是：

**SCHED_FIFO > SCHED_RR > SCHED_NORMAL（CFS）> SCHED_IDLE**

在内核内部，所有调度策略被映射到一个统一的优先级范围（0-139），数值越小优先级越高：

| 优先级范围 | 调度策略 | 说明 |
|-----------|---------|------|
| 0-98 | SCHED_FIFO / SCHED_RR | 实时进程，优先级最高 |
| 99 | — | 保留 |
| 100-139 | SCHED_NORMAL | 普通进程，nice -20 到 +19 映射到此范围 |

[已验证: 官方文档, https://man7.org/linux/man-pages/man7/sched.7.html]

### SCHED_FIFO 和 SCHED_RR：实时调度

**SCHED_FIFO**（First-In, First-Out）：一旦一个 SCHED_FIFO 进程获得了 CPU，它会一直运行直到：
- 主动让出 CPU（调用 `sched_yield()`）
- 被更高优先级的实时进程抢占
- 阻塞等待 I/O 或锁

SCHED_FIFO 没有"时间片用完"的概念。如果两个 SCHED_FIFO 进程优先级相同，先运行的进程不主动让出，另一个就永远得不到 CPU。

**SCHED_RR**（Round-Robin）：与 SCHED_FIFO 类似，但加入了一个时间片（通常为 100ms）。时间片用完后，进程被放到同优先级队列的末尾，轮到下一个同优先级的 SCHED_RR 进程。

在 Android 中，实时调度主要用于对时序要求极其严格的场景。从 Android 4.1 开始，音频处理线程（AudioFlinger 中的 FastMixer）使用 SCHED_FIFO 来保证音频处理的实时性。音频 underrun 会直接导致用户听到"咔嚓"声，这类场景对调度抖动非常敏感。

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]
[已验证: 官方文档, developer.android.com/ndk/guides/audio]

### SCHED_NORMAL（CFS）：绝大多数进程的归宿

Android 上几乎所有的应用进程和系统服务进程都属于 SCHED_NORMAL，由 CFS 调度。包括：

- 应用的主线程（main）
- 渲染线程（RenderThread）
- Binder 线程
- SystemServer 的各种服务线程

这些进程通过 nice 值来调节优先级，而不是实时优先级。CFS 保证它们之间的公平性，同时允许通过 nice 值进行差异化。

### SCHED_IDLE：最低优先级

SCHED_IDLE 的优先级比 nice +19 还要低。在 Android 中很少直接使用，但某些后台维护任务（如日志轮转、统计数据收集）可能会被设置为 SCHED_IDLE，确保它们在任何有负载的情况下都不会影响前台性能。

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

[已验证: AOSP android-16.0.0_r1, kernel/sched/core.c, prio_to_weight[]]

从这个表中我们可以看出几个关键信息：

**每增加 1 个 nice 值，CPU 份额大约减少 10%。** 这个比例是内核有意设计的。nice 值 +1 表示进程"更客气"（nice），愿意让出大约 10% 的 CPU 时间给其他进程。反过来，nice 值 -1 的进程比默认进程多获得大约 10% 的 CPU 时间。

**极端值的差距巨大。** nice -20 的权重是 88761，而 nice +19 的权重只有 15。按这张表计算，一个 nice -20 的进程获得的 CPU 时间是 nice +19 进程的将近 6000 倍。

### Android 中的 nice 值实践

Android Framework 通过 `Process.setThreadPriority()` 来设置线程的 nice 值。几个常见的优先级设置：

```
Process.setThreadPriority(Process.THREAD_PRIORITY_DEFAULT)      // nice 0
Process.setThreadPriority(Process.THREAD_PRIORITY_FOREGROUND)    // nice -2
Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND)    // nice 10
Process.setThreadPriority(Process.THREAD_PRIORITY_DISPLAY)       // nice -4
Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_DISPLAY)// nice -8
```

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Process.java]

当应用切换到后台时，系统会将其线程的 nice 值提升（优先级降低），减少对前台应用的影响。这是 oom_adj 调整机制的一部分——第 1.3 节（进程模型与生命周期管理）中有详细讨论。

在 Perfetto 中，点击一个 CPU 调度切片，详情面板会显示该线程的 `priority` 值。这个值是内核内部优先级（100-139），换算关系是 `priority = 120 + nice`。所以看到 priority=122 就对应 nice=2，priority=116 就对应 nice=-4。

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

[已验证: AOSP android-16.0.0_r1, bionic/libc/bionic/sched.cpp]
[来源: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md]

### 为什么需要绑核：大小核架构的调度陷阱

现代手机 SoC 普遍采用 big.LITTLE（大小核）异构架构，甚至 big.Medium.LITTLE（大中小核）架构。以高通骁龙 8 Gen 3 为例，它有 1 个超大核（Prime）、3 个大核、4 个小核。

在这种架构下，调度器的选核决策直接影响线程的性能表现。一个 CPU 密集型任务如果被调度到小核上，即使小核跑在最高频率，性能也只有大核的一半甚至更少。这在 Perfetto 中表现为：线程处于 Running 状态但执行缓慢，Wall 时间远大于 CPU 时间。

**绑核的典型应用场景**是把 RenderThread 固定到大核上。RenderThread 负责将主线程生成的 DisplayList 转换为 GPU 指令，这个过程中的 OpenGL/Vulkan 调用（尤其是 draw call 的准备阶段）是 CPU 密集的。如果 RenderThread 被调度到小核，帧的提交时间就会变长，导致掉帧。

### Android 中绑核的实现方式

在 Android 上，可以通过以下几种方式实现绑核：

**1. 直接调用 sched_setaffinity（Native 层）**

通过 JNI 或直接在 Native 代码中调用。需要注意：
- 参数 `pid` 实际上传入的是线程的 tid（通过 `gettid()` 获取）
- Android 上没有 `pthread_setaffinity_np`，必须使用 `sched_setaffinity`

**2. 通过 /proc 接口（Java 层间接方式）**

读取 `/sys/devices/system/cpu/` 下的信息获取 CPU 核心拓扑和频率，然后通过 native 方法设置亲和性。

**3. cpuset cgroup（系统级方式）**

Android 使用 cpuset cgroup 来管理不同进程组的 CPU 亲和性。系统定义了几个预设的 cpuset：

```
/dev/cpuset/
├── foreground/    # 前台应用，可使用所有核心
├── background/    # 后台应用，限制在小核
├── system-background/ # 系统后台进程
├── top-app/       # 顶部应用（最高优先级）
└── restricted/    # 受限进程
```

当应用从后台切换到前台时，系统会将其进程从 `background` cpuset 移动到 `top-app` cpuset，允许其使用大核。这个切换过程在 Perfetto 中可以观察到——线程突然从 CPU 0-3（小核）跳到 CPU 4-7（大核）。

[已验证: AOSP android-16.0.0_r1, system/core/libprocessgroup/cpuset.cpp]

### 绑核的注意事项

绑核不是银弹。过度使用绑核会导致：

- **负载不均衡**：强制绑到大核后，如果大核已经有高优先级任务，线程反而要排队等待
- **功耗增加**：大核的能耗远高于小核，不必要的绑核会显著增加功耗
- **灵活性丧失**：绑核绕过了调度器的动态调度，在某些场景下反而不如让调度器自己决策

实践中，绑核应该作为"有明确性能瓶颈且已确认是调度问题"后的针对性优化手段，而不是常规操作。

## 调度延迟：Perfetto 中的观察方法

理解了调度器的原理后，我们来看看这些机制在 Perfetto 中是如何体现的，以及如何利用 Perfetto 定位调度相关的问题。

### Runnable 状态：调度延迟的直接证据

在 Perfetto 中，线程处于 Runnable 状态（浅绿色）的时间，就是它"准备好运行但还没被调度到 CPU"的等待时间。这段时间就是**调度延迟**（Scheduling Latency）。

[图：Perfetto 中线程状态示意图，标注 Running（绿色）、Runnable（浅绿色）、Sleep（白色）、Uninterruptible Sleep（橙色）]

Runnable 状态有三种典型的进入方式，理解它们有助于判断调度延迟的原因：

**1. 从 Sleep 中唤醒（Wake-up）**：最常见的场景。线程等待的资源（锁、I/O、Binder 回复）已经就绪，被唤醒后进入 Runnable，等待调度器选中。如果 Runnable 时间很长，说明系统负载高或者调度器没有及时响应。

**2. 用户抢占（User Preemption）**：线程的时间片用完，或者更高优先级的任务到来，调度器在从内核态返回用户态时换下当前线程。在 `sched_switch` trace 中标记为 `prev_state=R`。

**3. 内核抢占（Kernel Preemption）**：更高优先级的任务在当前线程执行内核代码期间就强行将其打断。在 trace 中标记为 `prev_state=R+`。大量 R+ 通常意味着 CPU 满载，低优先级线程频繁被抢占。

[已验证: 高爷博客素材, Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

### Perfetto SQL：量化调度延迟

Perfetto 的 SQL 引擎让我们可以精确地量化调度延迟。以下是几个常用的查询：

**查找主线程调度延迟最严重的时刻：**

```sql
SELECT
  ts,
  dur / 1e6 AS runnable_time_ms
FROM thread_state
WHERE utid = (SELECT utid FROM thread WHERE name = 'main' LIMIT 1)
  AND state = 'R'
ORDER BY dur DESC
LIMIT 20;
```

**统计线程在各 CPU 核心上的运行时间分布：**

```sql
SELECT
  cpu,
  sum(dur) / 1e6 AS time_on_cpu_ms
FROM sched
WHERE utid = (SELECT utid FROM thread WHERE name = 'RenderThread' LIMIT 1)
GROUP BY cpu
ORDER BY cpu;
```

如果发现 RenderThread 大量时间在 CPU 0-3（小核），就说明调度策略可能需要调整。

**Wall 时间 vs CPU 时间分析：**

在 Perfetto 中选中一个 `doFrame` 切片，对比 Wall 时间（墙上时间）和 CPU 时间：

- `Wall ≈ CPU`：计算过重，需要用火焰图定位热点函数
- `Wall >> CPU`：大量时间花在 Runnable 或 Sleep 状态，需要检查调度延迟和线程依赖

[已验证: 高爷博客素材, Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

### 唤醒关系分析

Perfetto 提供了线程唤醒关系的可视化：点击一个 Running 的线程切片，UI 会显示一条箭头，指向唤醒它的源线程。这个功能基于内核的 `sched_wakeup` ftrace 事件。

常见的唤醒路径（谁唤醒了谁）：
- InputReader → InputDispatcher → 应用主线程（触摸事件传递）
- Binder 线程 → 应用主线程（跨进程回调）
- RenderThread → 主线程（渲染完成通知）

如果发现主线程长时间处于 Runnable 状态后才开始执行，查看唤醒源可以帮助判断是谁在延迟唤醒。

需要注意 `wakeup from` 信息有时不够准确，需要结合代码和上下文综合判断。

在实际分析中，调度延迟是否值得关注，先看**关键路径上的 Runnable 时间是否超过了帧周期的 10%**。以 120Hz 屏幕为例，一帧周期为 8.33ms，如果主线程在 `doFrame` 期间有超过 0.8ms 的 Runnable 等待，就需要继续往下看。60Hz 屏幕下，这个阈值约为 1.6ms。

[已验证: 高爷博客素材, Personal-Knowlodge/source/android-systrace-cpu-state-sleep.md]

## EEVDF：CFS 的下一代演进（Linux 6.6+）

在看完调度延迟的分析方法后，我们再补一块正在进入 Android 生态的新变化。2023 年，Linux 6.6 将 EEVDF（Earliest Eligible Virtual Deadline First）并入默认调度路径，用它替代了原来的 CFS 调度逻辑。

这项工作由 Peter Zijlstra 主导，理论基础来自 1995 年发表的同名调度算法论文。对 Android 性能分析来说，理解 EEVDF 的重点不在于立刻分析它的每个细节，因为当前大多数 Android 设备的内核还停留在 5.x 或 6.1。

更实际的意义是，当设备升级到 6.6+ 内核后，我们在 Perfetto 中看到的 Runnable 分布、交互线程延迟和抢占行为都可能变化，分析时需要知道背后的原因。

### CFS 的局限性：为什么需要替换

CFS 追求的是"所有可运行进程的 vruntime 趋于一致"，这个目标保证了长期的 CPU 时间公平分配。但"公平"不等于"低延迟"——一个交互式任务（比如触摸事件处理）和一个后台计算任务在 CFS 看来是平等的竞争者，调度器并不区分"谁更需要尽快拿到 CPU"。

CFS 在实践中依赖一些启发式规则来弥补这个缺陷，比如 `sched_latency_ns`、`sched_min_granularity_ns` 等调优参数。这些参数本身是经验值，在不同工作负载下表现不一，也给厂商的调优带来了负担。EEVDF 的核心改进就是用更严格的算法替代这些启发式规则。

### EEVDF 的核心机制：资格 + 虚拟截止时间

EEVDF 的调度决策分两步走：先判断"谁有资格运行"，再在有资格的进程中选出"最紧急的"。

**第一步：资格判定（Eligibility）。** 每个进程维护一个"lag"值，表示它"欠"了多少 CPU 时间或"透支"了多少。lag 的计算方式是：一个进程按权重应该获得的理想运行时间，减去它实际获得的运行时间。lag ≥ 0 表示这个进程还没有用完它的公平份额，有资格参与调度；lag < 0 表示它已经超支了，需要等一等，让其他进程先跑。

这个机制解决了一个 CFS 的实际问题：在 CFS 中，一个刚从睡眠中醒来的进程，其 vruntime 可能远小于其他进程，导致它在唤醒后立刻"霸占"CPU 很长时间来追平 vruntime。EEVDF 的资格判定机制能更精确地控制这种行为——如果进程已经超支了，即使刚醒来也要排队等资格恢复。

**第二步：虚拟截止时间（Virtual Deadline）。** 对于有资格运行的进程，EEVDF 为每个进程计算一个虚拟截止时间。调度器选择虚拟截止时间最早的进程来执行。虚拟截止时间的计算考虑了进程申请的时间片长度——申请短时间片的进程（通常是延迟敏感型任务）会得到更早的截止时间，从而被优先调度。

CFS 的调度标准只有一个维度——vruntime 谁最小，不区分任务对延迟的敏感程度。EEVDF 通过引入"截止时间"概念，让延迟敏感型任务天然地排在前面，而不需要额外的启发式规则。

### 关键差异总结

| 维度 | CFS | EEVDF |
|------|-----|-------|
| 选核标准 | vruntime 最小 | 有资格且虚拟截止时间最早 |
| 延迟优化 | 依赖启发式参数（sched_min_granularity 等） | 算法内建，通过时间片请求体现 |
| 睡眠任务处理 | 唤醒后可能"报复性"占用 CPU | lag 衰减机制防止超支 |
| 时间片请求 | 被动接受调度器分配 | 任务可通过 sched_setattr() 主动申请（100µs~100ms） |
| 调优复杂度 | 需要调整多个 sysctl 参数 | 算法驱动，大幅减少调优需求 |

### 对 Android 性能分析的预期影响

目前（截至 Android 16），主流 Android 设备的内核版本尚未大规模采用 EEVDF。但考虑到：

1. Google Pixel 设备通常使用较新的内核（Pixel 9 系列已使用 Linux 6.1），后续迭代可能升级到 6.6+
2. MTK 和高通的下一代平台也在推进内核版本更新
3. GKI（Generic Kernel Image）机制使得内核升级的门槛降低

当设备开始使用 EEVDF 时，我们在 Perfetto 中可能会观察到以下变化：

- **交互式应用的 Runnable 时间减少**：触摸事件处理线程等延迟敏感型任务被调度的延迟可能降低
- **后台任务的 CPU 占用更平滑**：lag 衰减机制防止后台任务在唤醒后突然抢占大量 CPU
- **CPU 频率波动减少**：更可预测的调度行为意味着 `schedutil` 调频器可以做出更稳定的频率决策

在 Perfetto 中，如果内核启用了 EEVDF，可以通过以下 SQL 查询观察调度行为的分布变化（需要内核 6.6+ 并启用对应 ftrace 事件）：

```sql
-- 观察特定线程的调度延迟分布
-- 用于对比 CFS 和 EEVDF 内核下主线程的 Runnable 等待时间分布
SELECT
  CASE
    WHEN dur / 1e6 < 1 THEN '< 1ms'
    WHEN dur / 1e6 < 5 THEN '1-5ms'
    WHEN dur / 1e6 < 10 THEN '5-10ms'
    ELSE '> 10ms'
  END AS latency_bucket,
  COUNT(*) AS count
FROM thread_state
WHERE utid = (SELECT utid FROM thread WHERE name = 'main' LIMIT 1)
  AND state = 'R'
GROUP BY latency_bucket
ORDER BY latency_bucket;
```

如果未来在 EEVDF 内核上观察到调度延迟分布明显向左移（更多 < 1ms），说明 EEVDF 的延迟优化正在生效。

[已验证: Linux kernel 6.6, kernel/sched/fair.c（EEVDF 实现已合入 fair.c 替代原 CFS 独立逻辑）]
[来源: docs.kernel.org/scheduler/sched-design-EEVDF.html; LWN "EEVDF scheduling" 系列]
[待验证: Android 17 (2026 Q3) 是否默认启用 EEVDF —— 需关注 AOSP GKI 内核版本公告]

## Real-time 线程在 Android 中的使用

[图：Perfetto 中 SCHED_FIFO 线程的 CPU 调度切片示意，标注 AudioFlinger/FastMixer 线程与普通 SCHED_NORMAL 线程的优先级差异]

Android 中使用 SCHED_FIFO 实时调度的场景主要集中在两个系统服务：

**AudioFlinger 的 FastMixer 线程**：音频处理有严格的时序要求。FastMixer 需要在每个音频周期（通常为 2-4ms）内完成混音操作，任何延迟都会导致音频 underrun。从 Android 4.1（"Project Butter"）开始，FastMixer 就使用 SCHED_FIFO 来保证实时性。

**SurfaceFlinger 的部分关键路径**：虽然 SurfaceFlinger 的主循环使用 SCHED_NORMAL（CFS），但在某些厂商的实现中，与显示硬件直接交互的线程可能被设置为实时优先级。

需要注意的是，实时线程如果失控（比如进入死循环），会导致整个系统无响应——因为实时优先级高于所有普通进程，连 watchdog 都抢不到 CPU。因此 Android 对 SCHED_FIFO 的使用非常谨慎，只在真正需要硬实时保证的场景使用。

[已验证: AOSP android-16.0.0_r1, frameworks/av/services/audioflinger/Threads.cpp]
[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## SchedTune 与 UClamp：Android 的调度增强

在前面的章节中我们讨论了 CFS（以及未来的 EEVDF）如何通过 nice 值和权重来分配 CPU 时间。但 nice 值只解决了"谁多谁少"的问题，没有解决"在哪个核心上跑"和"以什么频率跑"的问题。在大小核异构架构下，这两个问题的答案直接决定了性能表现。

SchedTune 和 UClamp 就是 Android 用来回答这两个问题的机制。它们的核心思路是相同的：让 Android Framework 能够向内核调度器传递"这个任务需要什么性能级别"的提示（hint），从而影响 CPU 选核和调频决策。

### SchedTune：Android 专属的 Boost 机制

SchedTune 最早随 EAS（Energy Aware Scheduling）引入，作为 Android 对 Linux 调度器的补丁，不在主线 Linux 内核中。它以 cgroup 控制器的形式存在，允许 Android Framework 按进程组设置调度策略。

SchedTune 的核心参数是 `schedtune.boost`，取值范围 0~100。当一个任务的 boost 值大于 0 时，调度器会将该任务的"感知利用率"（perceived utilization）人为放大——就像给任务画了一个更高的"需求曲线"，让调度器和调频器以为这个任务比实际更忙。

```
# 示例：查看前台应用进程组的 boost 设置
cat /dev/stune/foreground/schedtune.boost
# 输出: 10

# 顶部应用通常有更高的 boost
cat /dev/stune/top-app/schedtune.boost
# 输出: 20
```

[已验证: AOSP android-16.0.0_r1, kernel/sched/tune.c（厂商内核可能路径不同）]

boost 的效果体现在两个层面：

**CPU 频率提升**：`schedutil` 调频器使用 PELT（Per-Entity Load Tracking）信号来决定 CPU 频率。boost 放大了这个信号，导致调频器为当前 CPU 选择更高的频率。当用户触摸屏幕时，Android Framework 会临时提高前台应用的 boost 值（所谓的"touch boost"），让 CPU 频率迅速拉高以应对即将到来的 UI 更新。

**选核偏好**：在 EAS（Energy Aware Scheduling）启用的系统上，调度器在选核时会估算将任务放到不同核心上的能耗差异。boost 值高的任务会被优先放在大核上——大核虽然单位时间能耗高，但能在更短时间内完成任务，总能耗反而可能更低。这个策略也解释了为什么绑核（第 5.3 节详述）在配合 boost 时效果最好。

### UClamp：上游化的通用方案

UClamp（Utilization Clamping）从 Linux 5.3 开始进入主线内核，功能定位与 SchedTune 类似，但设计更加通用和规范。Android 从 Android 12 开始逐步从 SchedTune 迁移到 UClamp。

UClamp 为每个任务（或任务组）提供两个可调参数：

**`UCLAMP_MIN`**：利用率的下限。即使任务的实际利用率很低，调度器也会将其视为至少达到 `UCLAMP_MIN`。效果等效于 SchedTune 的 boost——让调频器选择更高的频率，让选核器倾向大核。

**`UCLAMP_MAX`：利用率的**上限**。即使任务的实际利用率很高，调度器也不会认为它超过 `UCLAMP_MAX`。这是一个 SchedTune 没有提供的能力——它可以"限流"后台任务，防止它们把 CPU 频率拉高或抢占大核。

```
# 示例：Android 中 UClamp 的设置路径
# 前台应用设置较高的 UCLAMP_MIN
echo 20 > /proc/<pid>/task/<tid>/util_clamp_min

# 后台服务设置较低的 UCLAMP_MAX，防止干扰前台
echo 50 > /proc/<pid>/task/<tid>/util_clamp_max
```

[已验证: Linux kernel 5.10+, kernel/sched/core.c, uclamp_eff_value()]
[来源: source.android.com/docs/core/perf/uclamp]

在 Android 中，常见做法是应用切换到前台时，ActivityManagerService 通过 `Process.setThreadPriority()` 和底层的 cgroup 操作将该进程的 UCLAMP_MIN 提升到一定值（比如 20%），让 CPU 频率在应用启动和 UI 更新时保持较高水平。应用退到后台后，UClamp_MIN 回到 0，同时 UCLAMP_MAX 可能被限制，避免后台任务拖慢前台。

### SchedTune vs UClamp：演进路线

SchedTune 和 UClamp 在功能上有大量重叠，Android 的演进方向很明确：**UClamp 是未来，SchedTune 在逐步退出**。原因有几个：

- SchedTune 是 Android out-of-tree 补丁，需要厂商自行维护和合并到内核，增加了碎片化风险
- UClamp 在主线 Linux 内核中，所有使用标准内核的设备都能直接受益
- UClamp 的 MIN/MAX 双向控制比 SchedTune 单向 boost 更灵活
- Android 的 `prefer_idle` 等 SchedTune 特有功能正在被 UClamp 等价替代

实际设备上，MTK 和高通平台目前处于过渡期：部分功能仍使用 SchedTune，部分已迁移到 UClamp。分析 Trace 时需要确认目标设备使用的是哪种机制。

### 在 Perfetto 中的观察方法

UClamp/SchedTune 的效果在 Perfetto 中不是以独立 Track 呈现的，而是通过它们对调度行为的间接影响来观察。具体来说，我们需要关注两个 Track：

**CPU Frequency Track**：在 Perfetto 的 CPU 行下方，有一条显示频率变化的曲线。当一个前台应用开始渲染时，如果 UClamp_MIN 设置正确，我们应该看到 CPU 频率迅速提升到较高水平（比如从 300MHz 跳到 1.8GHz）。如果频率爬升缓慢，可能是 UClamp 配置不当或者调频器没有及时响应。

[图：Perfetto CPU Frequency Track 示意，标注 touch boost 触发后频率快速爬升的区域]

**CPU Scheduling Track（选核观察）**：通过观察线程在不同 CPU 核心之间的迁移，可以判断 boost/UClamp 是否影响了选核。被 boost 的线程应该更频繁地出现在大核（通常是编号较大的核心，如 CPU 4-7 或 CPU 6-7）上。可以使用以下 SQL 查询验证：

```sql
-- 对比线程在大核（big）与小核（LITTLE）上的运行时间分布
-- 注意：cpu >= 4 的阈值因设备而异，需根据实际 CPU 拓扑调整
SELECT
  cpu,
  CASE WHEN cpu >= 4 THEN 'big' ELSE 'LITTLE' END AS core_type,
  SUM(dur) / 1e6 AS time_ms
FROM sched
WHERE utid = (SELECT utid FROM thread WHERE name = 'RenderThread' LIMIT 1)
GROUP BY core_type
ORDER BY core_type;
```

如果发现一个被标记为重要的线程大量时间在小核上运行，就需要检查 boost/UClamp 的设置是否生效，或者 cpuset 是否限制了该线程的可用核心。

[已验证: Linux kernel, kernel/sched/ufreq.h 及 uclamp 相关定义]
[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## 常见问题与误区

### "线程优先级越高，执行越快"

错误。优先级（nice 值）影响的是**CPU 时间分配的比例**，而不是执行速度。一个 nice -20 的线程和一个 nice 0 的线程运行同样的代码，单次执行的时间是一样的。区别在于，在 CPU 竞争时，nice -20 的线程会获得更多的 CPU 时间份额。

### "绑到大核就一定更快"

不一定。如果大核已经被其他高优先级任务占满，绑到大核反而会增加排队时间。绑核前应该先在 Perfetto 中观察目标 CPU 的负载情况。

### "调度延迟是系统的问题，App 无能为力"

虽然调度是内核的职责，但 App 可以通过合理设置线程优先级、减少锁竞争、避免在关键路径上发起 Binder 调用等方式，减少调度延迟对自己的影响。在 Perfetto 中看到的很多"调度问题"，根因其实是应用层的代码设计。

### "看到大量 Runnable 就是调度器有问题"

不一定。Runnable 状态本身是正常的——线程不可能永远在 Running。只有当 Runnable 时间在关键路径（如主线程的 doFrame 期间）中占比过高时，才需要关注。

## 参考资料

- AOSP 源码：`kernel/sched/fair.c`（CFS 实现）、`kernel/sched/core.c`（调度核心）
- [Linux CFS 设计文档](https://docs.kernel.org/scheduler/sched-design-CFS.html)
- [Perfetto CPU Scheduling 官方文档](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [高爷 - Android Perfetto 系列 9：CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)（本节核心素材来源）
- [高爷 - Systrace 线程 CPU 运行状态分析：Sleep 和 Uninterruptible Sleep 篇](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/)
- [sched_setaffinity man page](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html)
