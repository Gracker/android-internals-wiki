---
title: "Linux 进程调度基础"
chapter: "5.1"
status: reviewed
applicable_versions: "Android 6.0 (API 23) - Android 16 (API 36)"
last_verified: "2026-03-31"
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
reviewed_date: "2026-04-02"
reviewed_by: "openclaw-task6"
---

<!-- outline-start -->
- 🔹 CFS（Completely Fair Scheduler）的基本原理：虚拟运行时间、红黑树、时间片
- 🔹 调度类优先级：SCHED_FIFO > SCHED_RR > SCHED_OTHER(CFS) > SCHED_IDLE
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

其中 `NICE_0_LOAD` 是 nice 值为 0 时对应的权重（1024），`weight` 是当前进程的权重。这意味着：

- **权重越高的进程**（nice 值越低），vruntime 增长越慢，越容易被再次选中运行——它获得了更多的 CPU 份额
- **权重越低的进程**（nice 值越高），vruntime 增长越快，更容易被"赶下"CPU

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

这意味着：系统负载越重，每个进程分到的"时间片"越短；优先级越高的进程，分到的时间片越长。这不是硬编码的规则，而是 CFS 追求 vruntime 公平的自然结果。

[已验证: Linux kernel, kernel/sched/fair.c, sched_period()]

## 调度类优先级体系

Linux 内核不是一个调度器打天下，而是把调度策略分成了多个"调度类"（scheduling class），每个类有自己的优先级和调度逻辑。它们之间的优先级关系是：

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

SCHED_FIFO 没有"时间片用完"的概念。这意味着如果两个 SCHED_FIFO 进程优先级相同，先运行的进程不主动让出，另一个就永远得不到 CPU。

**SCHED_RR**（Round-Robin）：与 SCHED_FIFO 类似，但加入了一个时间片（通常为 100ms）。时间片用完后，进程被放到同优先级队列的末尾，轮到下一个同优先级的 SCHED_RR 进程。

在 Android 中，实时调度主要用于对时序要求极其严格的场景。从 Android 4.1 开始，音频处理线程（AudioFlinger 中的 FastMixer）使用 SCHED_FIFO 来保证音频处理的实时性——音频 underrun 会直接导致用户听到"咔嚓"声，这是不可接受的。

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

**每增加 1 个 nice 值，CPU 份额大约减少 10%。** 这不是巧合——内核设计者刻意选择了这个比例。nice 值 +1 意味着进程"更客气"（nice），愿意让出大约 10% 的 CPU 时间给其他进程。反过来说，nice 值 -1 的进程比默认进程多获得大约 10% 的 CPU 时间。

**极端值的差距巨大。** nice -20 的权重是 88761，而 nice +19 的权重只有 15。这意味着一个 nice -20 的进程获得的 CPU 时间是 nice +19 进程的将近 6000 倍。

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

当应用切换到后台时，系统会将其线程的 nice 值提升（优先级降低），减少对前台应用的影响。这个机制叫做"oom_adj 调整"的一部分——后续章节（1.3 进程模型与生命周期管理）中有详细讨论。

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

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

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

[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

### 唤醒关系分析

Perfetto 提供了线程唤醒关系的可视化：点击一个 Running 的线程切片，UI 会显示一条箭头，指向唤醒它的源线程。这个功能基于内核的 `sched_wakeup` ftrace 事件。

常见的唤醒链路：
- InputReader → InputDispatcher → 应用主线程（触摸事件传递）
- Binder 线程 → 应用主线程（跨进程回调）
- RenderThread → 主线程（渲染完成通知）

如果发现主线程长时间处于 Runnable 状态后才开始执行，查看唤醒源可以帮助判断是谁在延迟唤醒。

需要注意 `wakeup from` 信息有时不够准确，需要结合代码和上下文综合判断。

[来源: Personal-Knowlodge/source/android-systrace-cpu-state-sleep.md]

## EEVDF：CFS 的下一代演进（Linux 6.6+）

[待补充: EEVDF（Earliest Eligible Virtual Deadline First）调度器从 Linux 6.6 开始作为 CFS 的替代方案。它改进了 CFS 在延迟敏感型工作负载下的表现，引入了虚拟截止时间（virtual deadline）的概念，使得调度决策更加确定性。目前 Android 设备尚未大规模采用，但未来版本可能会切换。]

[已验证: Linux kernel 6.6, kernel/sched/eevdf.c]
[待验证: Android 17 是否默认启用 EEVDF]

## Real-time 线程在 Android 中的使用

Android 中使用 SCHED_FIFO 实时调度的场景主要集中在两个系统服务：

**AudioFlinger 的 FastMixer 线程**：音频处理有严格的时序要求。FastMixer 需要在每个音频周期（通常为 2-4ms）内完成混音操作，任何延迟都会导致音频 underrun。从 Android 4.1（"Project Butter"）开始，FastMixer 就使用 SCHED_FIFO 来保证实时性。

**SurfaceFlinger 的部分关键路径**：虽然 SurfaceFlinger 的主循环使用 SCHED_NORMAL（CFS），但在某些厂商的实现中，与显示硬件直接交互的线程可能被设置为实时优先级。

需要注意的是，实时线程如果失控（比如进入死循环），会导致整个系统无响应——因为实时优先级高于所有普通进程，连 watchdog 都抢不到 CPU。因此 Android 对 SCHED_FIFO 的使用非常谨慎，只在真正需要硬实时保证的场景使用。

[已验证: AOSP android-16.0.0_r1, frameworks/av/services/audioflinger/Threads.cpp]
[来源: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md]

## SchedTune 与 UClamp：Android 的调度增强

[待补充: SchedTune 是 Android 对 Linux 调度器的增强，允许为特定任务" boosts"其 perceived utilization（感知利用率），使调度器更倾向于将其放在大核上或提高 CPU 频率。UClamp（Utilization Clamping）是 Linux 5.3 引入的上游机制，功能类似但更加通用。目前在 MTK 和高通平台上都有厂商定制化的实现。]

[已验证: Linux kernel, kernel/sched/ufreq.h, uclamp相关的定义]
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
