---
title: 线程 CPU 状态分析
section: '13.6'
chapter: '13.6'
status: ready-for-review
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
reviewed_date: '2026-04-22'
reviewed_by: openclaw-task6
applicable_versions: Android 8.0 (API 26) - Android 16 (API 36)
last_verified: '2026-04-03'
last_verified_against: perfetto.dev/docs/data-sources/cpu-scheduling
confidence: high
sources:
- type: blog
  path: https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/
- type: blog
  path: https://www.androidperformance.com/2022/01/21/android-systrace-cpu-state-runnable/
- type: blog
  path: https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-running/
- type: blog
  path: https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
tags:
- perfetto
- thread-state
- sched-switch
- running
- runnable
- sleep
- uninterruptible-sleep
- cpu-scheduling
related_chapters:
- '5.1'
- '13.1'
- '13.5'
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task6_result: pass-light-edit
task9_state: "pending"
task2b_state: "fixed"
task9_result: needs-rework
task9_reviewed_date: '2026-05-13'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-05-13T04:11:19+08:00'
task2b_result: "fixed"
last_task2b_at: '2026-04-28T01:40:00+08:00'
task9_review_notes: '2026-05-13 task9 deep-review: needs-rework。P0/P1 技术问题已写入 queue。'
---


# 线程 CPU 状态分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 线程 CPU 状态定义：Running (R)、Runnable (R+)、Sleeping (S)、Uninterruptible Sleep (D)、Stopped (T)
- 🔹 在 Perfetto 中读取线程状态：sched_switch events、thread state track
- 🔹 Runnable 过长的常见含义：CPU 争抢、核数不足、优先级过低
- 🔹 Uninterruptible Sleep 的常见含义：I/O 等待、内核锁、Page Fault
- 🔹 从线程状态分析性能瓶颈的方法论

### 扩展（可选深入）

- 🔸 wakeup 事件分析：谁唤醒了这个线程
- 🔸 irq/softirq 对线程调度的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解线程 CPU 状态

在 Perfetto 中打开一段 Trace，展开任意一个线程，我们会看到一条由不同颜色的色块拼接而成的轨道——绿色、蓝色、白色、橙色交替出现。这些色块不是装饰，它们是线程在整个生命周期中的"呼吸记录"：什么时候在 CPU 上跑，什么时候在排队等 CPU，什么时候在睡觉等资源，什么时候卡死了谁都叫不醒。

如果我们在做性能优化，这条轨道就是我们最基础的分析入口。无论是卡顿、ANR、启动慢、还是功耗高，最终的答案几乎都能追溯到线程的 CPU 状态上：**一个线程花在 Running 以外的时间越久，它完成任务就越慢**。理解每种状态的含义、知道在 Perfetto 中怎么读取、怎么判断异常，是从"看 Trace 发呆"到"看 Trace 定位问题"的分水岭。

[已验证: 来源见 Android-Perfetto-09-CPU.md]

## 五种核心状态

Linux 内核为每个线程维护了一个状态字段。从性能分析的视角，我们需要关注的有五种：

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-scheduling]

**Running**：线程正在某个 CPU 核心上执行代码。这是唯一真正在消耗 CPU 算力的状态。在 Perfetto 的线程轨道上显示为**绿色**。

**Runnable (R)**：线程已经具备运行的一切条件，只差一个 CPU 核心来执行它。它被放在某个 CPU 的运行队列里排队，等待调度器的裁决。在 Perfetto 中显示为**蓝色/浅绿色**。

**Runnable (R+)**：线程原本在 Running，但在执行内核态代码期间被更高优先级的任务强行打断，被迫让出 CPU。这里的 `+` 号代表"被抢占"（Preempted）。这和普通 Runnable 的区别在于，R+ 意味着非自愿的让出——线程自己并不知道要停下来。

**Sleeping (S)**：线程在等待某个事件——锁、Binder 回复、I/O、定时器。这种等待是可以被信号中断的。在 Perfetto 中显示为**白色**。

**Uninterruptible Sleep (D)**：线程在等待硬件 I/O 操作完成或持有内核锁，期间不能被任何信号打断，甚至连 `kill -9` 都无效。内核这样设计是为了保护进程与设备交互过程中数据的一致性。在 Perfetto 中显示为**橙色**。

此外还有两个不太常见但值得知道的状态：

- **Stopped (T)**：线程被暂停，通常是因为收到 SIGSTOP 信号或正在被调试器 attach。
- **Zombie (Z)**：线程已执行完毕但父进程尚未回收它的退出状态。

在实际的性能分析中，我们 99% 的时间都在处理 Running、Runnable、Sleeping 和 Uninterruptible Sleep 这四种状态。Stopped 和 Zombie 通常意味着系统级的异常，需要具体问题具体分析。

[已验证: 来源见 android-systrace-cpu-state-sleep.md §Linux中的Sleep状态]
[已验证: 来源见 Android-Perfetto-09-CPU.md §线程状态深度解析]

## 在 Perfetto 中读取线程状态

### CPU Scheduling 轨道

Perfetto 的 CPU 相关信息通常分组置于顶部区域。最核心的是 **CPU Scheduling** 轨道，它可视化展示了每个 CPU 核心上正在执行哪个线程。数据来源于 Linux 内核 ftrace 中的 `sched/sched_switch` 事件——每当调度器做出一次切换决策，这个事件就会被记录下来。

每个 CPU 核心对应一行独立的轨迹，不同颜色的色块代表不同线程在该 CPU 核心上运行的时间片段。点击任意一个色块，下方的详情面板会显示这次调度的具体信息：`cpu`（哪个核）、`end_state`（线程被切出时的状态）、`priority`（优先级）、`process/thread`（所属进程和线程名）。

[图：Perfetto CPU Scheduling 轨道总览，展示多个 CPU 核心上的线程调度色块] [待高爷补充]

### Thread State 轨道

从 CPU 区域向下展开到进程级别，再展开到具体的线程，我们会看到每个线程拥有一条独立的 **thread_state** 轨道。这条轨道上，时间轴被切割成连续的色块，每个色块代表线程在某个时间段的状态：

- **绿色**：Running
- **蓝色/浅绿色**：Runnable（含 Runnable 和 Runnable (Preempted)）
- **白色**：Sleeping
- **橙色**：Uninterruptible Sleep

> **注意**：Runnable 在 Perfetto 中只对应蓝色/浅绿色，白色是 Sleeping。分析调度延迟时，需要同时关注 `R` 和 `R+` 两种 Runnable 子状态。

这条轨道是分析单线程性能瓶颈的首选入口。选中任何一个色块，Current State 面板会显示该状态的详细信息，包括持续时间和阻塞原因。

[图：线程的 thread_state 轨道，展示不同颜色的状态色块及 Current State 面板] [待高爷补充]

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-scheduling]

### 抓取配置

要让 Perfetto 完整记录所有线程状态信息，需要在 TraceConfig 中启用正确的 ftrace 事件。以下是推荐的最小 CPU 分析配置：

```protobuf
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"        # 调度切换（必需）
      ftrace_events: "sched/sched_waking"         # 唤醒事件
      ftrace_events: "sched/sched_wakeup_new"     # 新线程唤醒
      ftrace_events: "sched/sched_blocked_reason"  # D 状态阻塞原因
      ftrace_events: "power/cpu_frequency"        # CPU 频率变化
      ftrace_events: "power/cpu_idle"             # CPU 空闲状态
      symbolize_ksyms: true
      disable_generic_events: true
    }
  }
}
```

其中 `sched/sched_switch` 是绝对必需的，它是所有线程状态分析的基础数据源。`sched/sched_blocked_reason` 对分析 Uninterruptible Sleep 很有用，它会记录线程进入 D 状态时正在执行的内核函数，是定位 I/O 瓶颈的关键线索。`sched/sched_waking` 用于唤醒关系分析，我们后面会详细讨论。

[已验证: 来源见 Android-Perfetto-09-CPU.md §TraceConfig]

## Running：线程在干活，但活可能太多

### 正常情况

Running 是最"健康"的状态——线程正在 CPU 上执行代码。对于 UI 线程来说，一帧的 doFrame 回调中的 Running 时间就是实际执行 measure、layout、draw 的时间。只要这个时间不超过一帧的预算（120Hz 下约 8.33ms，60Hz 下约 16.67ms），就不会出现掉帧。

### Running 过长的原因

当 Running 时间超出预期，意味着线程在 CPU 上做了太多的计算。这不是调度的问题，而是代码本身的问题。常见的原因有：

**代码复杂度高**。这是最常见的原因。某个函数的算法复杂度过高、循环层数太深、或者在不该做大量计算的地方做了大量计算。在 Perfetto 中，我们会看到一长条绿色的色块，持续几毫秒到几十毫秒不等。

定位具体是哪段代码导致 Running 过长，需要借助其他工具。Perfetto 中的 CPU 火焰图（需要启用 `linux.perf` 数据源）可以直接看到函数级别的热点；simpleperf 也能以时间线的方式展示函数执行流。此外，也可以在代码中通过 `Trace.beginSection()` / `Trace.endSection()` 手动添加 tracepoint，将长绿色块拆解为更细粒度的子任务。

**跑在了小核上**。即使代码本身没问题，如果线程被调度到了小核执行，由于小核的 IPC（Instructions Per Cycle）和主频都远低于大核，同样的代码需要更长的 Running 时间。在 Perfetto 中，我们可以通过点击绿色色块查看它运行在哪个 CPU 核心上，结合设备的核编号划分（比如 CPU 0-3 为小核，4-6 为大核，7 为超大核）来判断调度是否合理。

**CPU 频率太低**。即使线程运行在大核上，如果 CPU 频率因为温控、省电等原因被限制在低频，代码执行也会变慢。这时需要结合 Perfetto 的 **CPU Frequency** 轨道，观察线程运行期间 CPU 频率是否正常。

**代码以解释方式执行**。刚安装、未经过 dex2oat 编译的应用，或者使用了某些 ART 运行时特性（如频繁 JNI 调用、反复反射调用）的代码，可能以解释方式运行，性能远低于编译后的代码。在 Trace 中如果看到"Compiling"字样，就可能属于这种情况。

### CPU 时间与墙上时间的关系

在 Perfetto 中选中任何一个调度切片，详情面板会显示两个时间值：**Wall**（墙上时间）和 **CPU**（CPU 时间）。

- **Wall** 是这个切片从开始到结束的真实世界时间。
- **CPU** 是线程真正在 CPU 上运行的时间。

`Wall = CPU + 该时间窗内全部 off-CPU 状态的总和`。这里的 off-CPU 不只包含 Runnable 和 Sleeping，也包含 Uninterruptible Sleep、Stopped 等没有占到 CPU 的时间。

这个对比在定位瓶颈时很好用。选中一个关键切片（比如 `Choreographer#doFrame`），比较 Wall 和 CPU：

- 如果 `Wall ≈ CPU`，说明线程大部分时间都在真正执行代码，瓶颈更接近计算过重。这时优先看火焰图和函数热点。
- 如果 `Wall >> CPU`，说明大量时间花在排队或等待上。回到 `thread_state` 轨道，再拆 R、S、D 和其他 off-CPU 状态的占比，才能判断是在等 CPU、等 Binder、等锁，还是卡在 I/O。

[图：Perfetto 中 Wall 与 CPU 时间的对比展示] [待高爷补充]

[已验证: 来源见 android-systrace-cpu-state-running.md]
[已验证: 来源见 Android-Perfetto-09-CPU.md §CPU时间与墙上时间]

## Runnable：线程准备好了，但 CPU 没空

### 正常情况

线程处于 Runnable，意味着它已经获得了运行所需的一切资源（锁拿到了、I/O 完成了、数据准备好了），只差一个 CPU 核心来执行。它被放入某个 CPU 的运行队列中，等待调度器选中。

Runnable 状态的出现是正常的——毕竟 CPU 核心数量有限，不可能所有线程都同时执行。对于普通线程，几微秒到几百微秒的 Runnable 等待是完全可接受的。

### Runnable 过长的五种原因

当关键线程（特别是 UI 线程、RenderThread 这类对时序敏感的线程）长时间处于 Runnable 状态，意味着它在排队等 CPU，任务无法及时完成，直接表现为卡顿或掉帧。

**原因一：优先级设置错误。** 线程的优先级决定了它在运行队列中的排队顺序。如果关键线程的优先级被设置得太低，它会被其他线程反复抢先，始终拿不到 CPU 时间。更隐蔽的情况是，某些应用或系统服务把无关线程的优先级设得太高，反而抢占了关键线程的 CPU 时间。从 Perfetto 中可以追踪线程被哪个线程抢占：点击 Runnable 色块旁边的 Running 色块，查看正在占用该 CPU 的是哪个线程。

三方应用开发者一般不建议直接调用优先级相关的 API。不同厂商对调度器有各自的客制化改动（如 OPPO 的蜂鸟引擎），应用设置的优先级在某些厂商的调度策略下可能出现"水土不服"，弄巧成拙。更靠谱的方式是合理安排自己的任务模型，不要把对实时性要求很高的任务放到 worker 线程上。

[已验证: 来源见 android-systrace-cpu-state-runnable.md §原因1优先级错误]

**原因二：绑核不合理。** 有些开发者为了追求性能，会将线程绑定到特定的大核上。但绑核是双刃剑：一旦绑定，该线程只能在这个核上运行，即使其他核很空闲也无法迁移。如果多个线程绑在同一个核上，当该核繁忙时，所有绑在上面的线程都会出现长时间 Runnable。绑核应以 CPU 簇为单位（如大核簇 4-7），而不是单个核心。

绑核时还需要注意：正确区分大小核（不同平台编号不同）、只能在 CPUSET 允许范围内绑核（否则会失败甚至出现致命错误）、2 个大核平台要尽量减少绑大核的线程数目。

[已验证: 来源见 android-systrace-cpu-state-runnable.md §原因2绑核不合理]

**原因三：系统负载过高。** 当系统整体负载很高时——可能是因为应用自身开了太多线程，也可能是因为系统服务或后台进程占用大量 CPU——所有线程的排队时间都会变长。在 Perfetto 的 CPU 区域，我们会看到每个核上都排满了密密麻麻的色块，几乎没有空闲间隙。选中一个区间按时间排序，可以查看都在执行什么任务，逐个排查原因。

**原因四：CPU 算力受限。** 即使负载不高，如果 CPU 被锁频（温控导致降频）、锁核（关闭部分核心）、或者设备本身算力较弱，有限的 CPU 资源也会导致排队时间变长。这种情况需要结合 CPU Frequency 轨道和设备硬件参数来综合判断。

**原因五：软件架构的线程依赖过重。** 如果关键操作需要多个线程协同完成（比如 UI Thread → Render Thread → SurfaceFlinger → HWC 的渲染管线），每个线程间的等待和唤醒都会增加一次 Runnable 排队的机会。依赖链越长，某个环节出问题的概率就越高。最常见的模式是：两个线程之间有频繁的通讯与等待（线程 A 把任务转移到线程 B 执行，A 等待 B 任务执行完后被唤醒），CPU 繁忙时很容易打出 Runnable 等待。

[已验证: 来源见 android-systrace-cpu-state-runnable.md]

### Runnable 的三种子类型

仔细观察 Perfetto 的 thread_state 轨道，Runnable 其实可以细分为三种来源：

1. **从 Sleep 中唤醒**。线程因等待的资源（锁、I/O、Binder 回复）已经就绪，从 S 或 D 状态被唤醒，进入 Runnable 排队。这是最常见的类型。

2. **用户抢占**。线程的运行时间片用完，或出现更高优先级的任务，调度器在从内核态返回用户态时决定换下当前线程。此时 `sched_switch` 的 `prev_state` 标记为 `R`。

3. **内核抢占**。更高优先级的任务在当前线程正在执行内核态代码期间就强行将其打断。此时 `prev_state` 标记为 `R+`，Perfetto 会标注为 `Runnable (Preempted)`。

理解这三种类型的区别有助于精细判断调度延迟的原因。大量的 `R+`（Preempted）可能暗示系统中存在频繁的高优先级唤醒源，或者当时 CPU 已经满载，低优先级线程很容易被抢占。如果我们的关键 Task 总是被抢占，需要考虑调整优先级。

[已验证: 来源见 Android-Perfetto-09-CPU.md §R-Runnable]

## Sleeping：线程在等，要找清它在等谁

### 正常情况

Sleeping 是线程最常见的状态。打开 Perfetto，我们会看到大量线程长时间处于白色——这是正常的。Android 中的 Looper 机制就是典型的 Sleeping：线程调用 `epoll_wait()` 等待新消息到来，期间进入 Sleeping 状态，不消耗 CPU 资源。

Sleeping 本身不是问题。问题在于关键线程在不该等的时候等了太久。

### Sleeping 过长的常见原因

**锁竞争。** 等待获取一个 Java 锁（synchronized / ReentrantLock）或 native futex。当多个线程争抢同一把锁时，拿不到锁的线程会进入 Sleeping。在 SystemServer 这种高并发的进程里，锁竞争尤为常见。Binder 多线程并行化或抢占公共资源是 SystemServer 中锁竞争的主要来源。

**Binder 通信。** 当线程发起一个同步 Binder 调用后，会等待对端进程返回结果。如果对端处理缓慢——可能是因为对端也在等锁、或者对端的线程处于 Runnable 排不上 CPU——调用方就会长时间 Sleeping。通过 Perfetto 中的唤醒关系可以追踪到对端线程。

**I/O 操作。** 等待网络 socket 数据（`epoll_wait`）、等待文件读写完成。关键路径上的同步 I/O 是 Sleeping 的常见来源。

**主动等待。** 代码中显式调用了 `Thread.sleep()` 或 `Object.wait()`。这需要检查代码逻辑，判断等待是否合理。

**等待 GPU 执行完毕。** 等 GPU fence 时间。常见原因有渲染任务过重、GPU 能力弱、GPU 频率低等。优化方向包括提升 GPU 频率、降低渲染任务复杂度（精简 Shader、降低渲染分辨率、降低 Texture 画质）。

[已验证: 来源见 android-systrace-cpu-state-sleep.md §耗时原因]

### 唤醒关系：找到"等谁"的方法

当一个线程长时间 Sleeping 时，先定位它在等谁。Perfetto 提供了唤醒关系的可视化功能来回答这个问题。

在 Perfetto 的 CPU 区域中，选中一个处于 Running 状态的线程切片，Perfetto 会自动绘制一条从"唤醒者"到"被唤醒者"的箭头，高亮显示唤醒源所在的线程。底层原理是：当线程 T1 释放了某个资源（如解锁、完成 Binder 调用），而线程 T2 正在等待该资源时，内核会将 T2 标记为 Runnable，并记录一条 `sched_waking` 事件。Perfetto 解析这条事件，把 waker 线程和被唤醒线程连起来，帮助我们回看依赖链。这里看到的是"谁让线程变成 runnable"，后面是否立刻拿到 CPU，还要再看 runqueue 排队、迁核和优先级竞争。

通过唤醒分析，可以清晰地追踪复杂的调用链。例如：UI 线程等待 Binder 调用 → Binder 线程执行任务 → Binder 线程等待另一个锁 → 持锁线程释放锁并唤醒 Binder 线程 → Binder 线程完成任务并唤醒 UI 线程。整个过程中的瓶颈点一目了然。

不过 `wakeup from` 信息有时候并不稳定，原因和具体的 tracepoint 类型、内核实现有关。它也不是完整的锁依赖图。分析时要把它和 Binder 轨道、slice、代码路径一起交叉看。

[已验证: 来源见 Android-Perfetto-09-CPU.md §唤醒关系分析]
[已验证: 来源见 android-systrace-cpu-state-sleep.md §诊断方法]

## Uninterruptible Sleep：线程卡死了，谁都叫不醒

### 为什么需要这个状态

我们可能会问，既然已经有了 Sleeping（可中断睡眠），为什么还需要一个"不可中断"的版本？

原因在于数据一致性。当一个线程与硬件设备打交道时——比如正在执行磁盘 I/O 操作——内核不希望这个过程中被信号打断，因为中断可能导致设备状态和内存状态不一致。TASK_UNINTERRUPTIBLE 就是内核为这种场景设计的保护机制：线程进入这个状态后，只有它等待的资源就绪了才能被唤醒，信号（包括 `kill -9`）都不起作用。

这个设计思路在内核中很常见。Linux 处理硬件调度时会临时关闭中断控制器，调度时也会临时关闭抢占功能，目的都是"防止程序流程进入不可控的状态"。TASK_KILLABLE 是一个变种，等同于 `TASK_WAKEKILL` | `TASK_UNINTERRUPTIBLE`，可以接受 Kill 类型的 Signal。

Linux 内核中很多路径使用了 Uninterruptible Sleep：Swap 读数据、信号量机制、某些 mutex 锁的慢路径、内存回收的慢路径等。

[已验证: 来源见 android-systrace-cpu-state-sleep.md §TASK_UNINTERRUPTIBLE作用]

### Uninterruptible Sleep 分为两类

Perfetto v53+ 的 `thread_state` 表把 D 状态再拆了一层，排查时可以把 `state='D'` 和 `io_wait` 一起看：

| 观测项 | 常见含义 | 排查入口 |
|---|---|---|
| `state='D'` 且 `io_wait=1` | 更接近磁盘、块设备、Swap 等 I/O 等待 | 结合 Block Reason、文件访问、Page Fault、存储负载看 |
| `state='D'` 且 `io_wait=0` | 更接近内核锁、页表、内存回收、驱动内部等待 | 结合 Block Reason、锁路径、内存压力看 |
| `state='D'` 但 `io_wait` 为空 | 这份 trace 没把相关字段带出来 | 回到 Current State 面板和 `sched_blocked_reason` 交叉看 |

**I/O 等待（iowait）**。线程在等待磁盘 I/O 完成。在 Perfetto 的 Current State 面板中，D 状态如果伴有 `(iowait)` 标记，则明确表示在等待 I/O。CPU 内部缓存（L1/L2/L3）的访问速度最快，内存次之，磁盘最慢，它们之间的延迟差异是数量级的。系统越是从磁盘中读取数据，对整体性能的影响就越大。

**非 I/O 等待（内核锁等）**。线程在等待内核级别的锁或资源。Binder 驱动在高负载下的内部锁竞争是典型场景。与 I/O 等待不同，这类等待的根因通常更隐蔽，需要结合 Block Reason 和内核代码来定位。

### I/O 等待的常见原因

**应用主动 I/O 操作。** 在主线程上执行频繁或大量的文件读写操作。多应用同时下发 I/O 也会互相加剧等待。低端设备上磁盘碎片化、器件老化、剩余空间少都会放大这个问题。文件系统特性（某些文件系统的内部操作也会表现为 I/O 等待）和 Swap 读取也是来源。

**低内存导致 I/O 变多。** 内存紧张时，系统的 PageCache 命中率下降，原本可以从内存中读取的数据不得不去磁盘读取。同时，Swap 机制的引入会让数据从 Swap 分区中读取，这就是高频的磁盘 I/O。内存和 I/O 之间存在紧密的耦合关系：内存越多，PageCache 越大，I/O 越少；反之亦然。

### 非 I/O 等待的常见原因

**内存压力下的回收等待。** 系统物理内存不足时，kswapd 等回收线程工作加重，应用程序可能陷入 D 状态等待内存回收完成。

**Binder 驱动锁竞争。** 高负载下 Binder 驱动内部的锁竞争也会导致线程陷入 D 状态。

**其他内核锁。** 内核中各种热点区域的锁保护，不胜枚举。结合 Block Reason 的诊断方法来具体分析。

### Block Reason：定位 D 状态的利器

Perfetto 提供了一个非常有用的线索来帮助定位 D 状态的原因——**Block Reason**。

Android 内核中有一个由 Google 工程师 Riley Andrews 提交的 tracepoint 补丁，它在线程进入 D 状态时记录一条 `sched_blocked_reason` 事件，包含线程是否在等待 I/O（`iowait` 字段）以及进入 D 状态前最后一个非调度器函数的调用地址（`caller` 字段）。Perfetto v53+ 的 `thread_state.io_wait` 也是围绕这组信息展开的，所以 SQL 里不必只靠颜色判断 D 状态。

在 ftrace 中的记录格式如下：

```
sched_blocked_reason: pid=30235 iowait=0 caller=get_user_pages_fast+0x34/0x70
```

在 Perfetto 中，选中 D 状态的色块，Current State 面板会显示 Block Reason。例如 `get_user_pages_fast` 表示线程在执行内存页面映射时被阻塞，`do_page_fault` 表示在处理缺页中断。

定位到具体的内核函数后，需要结合内核源码来理解该函数的行为。以 `get_user_pages_fast` 为例，它会先通过无锁方式 pin 应用侧的 pages，如果失败则走慢速执行路径，需要获取 `mmap_lock`。如果此时锁被其他线程持有（比如另一个线程正在执行 `mmap` 操作），当前线程就会陷入等待。

需要注意，这个补丁未合入 Linux 上游主线，是 Android 内核的独有特性。不同厂商的内核是否包含此补丁需要确认。

[已验证: 来源见 android-systrace-cpu-state-sleep.md §BlockReason]

### 系统调度与 D 状态的耦合

有一种比较棘手的情况：线程 A 持有一把锁并处于 D 状态（等待 I/O），线程 B 想要获取同一把锁而进入 D 状态。此时如果线程 A 的 I/O 完成了并被唤醒，但它却长时间处于 Runnable（排不上 CPU），那么线程 B 的等待时间就会进一步拉长。更极端的情况是，即使锁持有的实际时间很短，如果锁持有者在被唤醒后长时间排不上 CPU，等待者感知到的锁等待时间也会很长。

这种调度与锁竞争的耦合问题，是目前 Android 性能优化中的难点之一。不同厂家有不同的解决方案，这也是各厂商核心竞争力的体现。

[已验证: 来源见 android-systrace-cpu-state-sleep.md §调度与D状态耦合]

## 唤醒事件与调度延迟分析

线程从 Sleeping 到真正 Running，中间需要经历两个步骤：被唤醒（变成 Runnable）→ 被调度器选中（变成 Running）。这两个步骤之间的时间差就是**调度延迟**（Scheduling Latency）。

在 Perfetto 中，这段延迟对应的就是 Runnable 状态的持续时间。通过唤醒事件（`sched_waking`），我们可以更精确地分析这段延迟：

- `sched_waking` 在线程被标记为可运行（R）时发出。
- `sched_wakeup` 与跨 CPU 唤醒有关，可能记录在源或目的 CPU 上。

对大多数延迟分析而言，仅 `sched_waking` 已足够。

### 非 work-conserving 的调度器

多数 Linux 调度配置在通用优先级下并非严格"work-conserving"。也就是说，即使有空闲 CPU，调度器也可能不会立刻把刚唤醒的线程迁移过去，而是等待当前 CPU 自然空闲。这是因为跨核迁移本身有额外开销和功耗代价。这种策略会导致 Runnable 状态下的排队延迟——但这不一定异常，而是调度器在性能和功耗之间的权衡。

排查思路：
1. 在目标线程的 thread_state 轨道中筛选 `state=R` 的切片，作为调度延迟的直接证据。
2. 同步对照同一 CPU 的其它重负载线程与 IRQ/SoftIRQ 轨迹，验证是否存在时间重叠的抢占。
3. 若频繁以 `end_state=R+` 收尾，说明非自愿抢占严重，需评估优先级和负载均衡策略。

[已验证: 来源见 Android-Perfetto-09-CPU.md §调度唤醒与延迟分析]
[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-scheduling]

## [自动发现] 用户态与内核态的区分

Running 状态的绿色色块未必都是应用代码在忙。如果线程陷入单个长系统调用（如 `sys_read`、`sys_futex`），它仍然显示为 Running，但用户态的 CPU 采样火焰图可能几乎为空。

判断方法：如果 UI 线程某段 Running 很长，但火焰图几乎没有用户态热点：
1. 打开该线程的 slice 视图，查找是否存在长时间的 `sys_*` 切片。
2. 若存在，瓶颈多在 I/O 或同步原语，优先检查 I/O 路径、锁粒度与访问模式。
3. 若不存在，回到火焰图，继续剖析用户态热点函数。

[已验证: 来源见 Android-Perfetto-09-CPU.md §用户态与内核态]

## [自动发现] irq/softirq 对线程调度的影响

硬中断（hard IRQ）在 interrupt context 中执行，ARM64 平台通常使用独立的 IRQ 栈，不共享当前进程的用户态栈。softirq 可能在被中断任务的上下文中执行，也可能由 `ksoftirqd` 内核线程处理。当硬中断或 softirq 频繁触发时，当前 CPU 上正在运行的线程会被抢占——Perfetto 中线程仍显示为 Running，但有效执行时间被中断处理压缩。

这种影响在 Perfetto 中不太容易直接观察到。间接判断方法：如果线程的 CPU 时间（火焰图上的用户态执行时间）明显少于对应 Running 色块的时间跨度，差异可能来自中断处理。更直接的证据需要启用 `irq` / `softirq` ftrace 事件或 `irq/` 轨道来观察中断活动；`ksoftirqd` 线程的 CPU 占用也能间接反映 softirq 负载。[已修正: ARM64 hard IRQ 使用独立栈, softirq 可由 ksoftirqd 执行][已验证: 来源见 android-systrace-cpu-state-sleep.md §中断讨论]

## 从线程状态分析性能瓶颈的方法论

了解了每种状态的含义之后，我们需要一个系统化的方法来从线程状态中定位性能瓶颈。

### 第一步：定位问题切片

从 Perfetto 的 thread_state 轨道开始。找到目标线程（比如 UI 线程），定位到出问题的时间段（比如掉帧发生的那一帧）。选中 `Choreographer#doFrame` 切片，查看 Wall 与 CPU 的比值。

### 第二步：拆解状态分布

如果 `Wall >> CPU`，说明线程花了大量时间在等。查看该时间段内 thread_state 轨道的颜色分布：

- **蓝色占比高**（Runnable 过长）：CPU 争抢问题。查看同一时间段内所有 CPU 的负载情况，是谁在占用 CPU？关键线程的优先级是否合理？是否需要绑核？
- **白色占比高**（Sleeping 过长）：依赖等待问题。通过唤醒关系找到线程在等谁，是锁、Binder、还是 I/O？
- **橙色占比高**（D 状态过长）：I/O 或内核锁问题。查看 Block Reason 确定是 I/O 还是内核锁。如果是 I/O，检查是否在关键路径上做了同步 I/O；如果是内存压力导致，检查系统内存使用情况。

### 第三步：使用 SQL 量化分析

Perfetto 内置的 SQL 引擎可以对线程状态进行精确的量化统计。以下是一些常用的查询：

**查询某线程的状态时间分布：**

```sql
SELECT
  CASE
    WHEN state = 'Running' THEN 'Running'
    WHEN state IN ('R', 'R+') THEN 'Runnable'
    WHEN state = 'S' THEN 'Sleeping'
    WHEN state = 'D' THEN 'Uninterruptible Sleep'
    ELSE state
  END AS state_name,
  sum(dur) / 1e6 AS total_time_ms
FROM thread_state
WHERE utid = (SELECT utid FROM thread WHERE name = 'surfaceflinger' LIMIT 1)
GROUP BY state_name
ORDER BY total_time_ms DESC;
```

**查询某线程 Runnable 中 R 和 R+ 的占比：**

```sql
SELECT
  CASE
    WHEN state = 'R' THEN 'Runnable'
    WHEN state = 'R+' THEN 'Runnable (Preempted)'
  END AS runnable_type,
  sum(dur) / 1e6 AS total_time_ms
FROM thread_state
WHERE utid = (SELECT utid FROM thread WHERE name = 'surfaceflinger' LIMIT 1)
  AND state IN ('R', 'R+')
GROUP BY runnable_type
ORDER BY total_time_ms DESC;
```

如果 R+ 占比高，说明该线程频繁被高优先级任务抢占，需要评估优先级和负载均衡策略。

**查询某线程 D 状态里 `io_wait` 的分布：**

```sql
SELECT
  io_wait,
  sum(dur) / 1e6 AS total_time_ms
FROM thread_state
WHERE utid = (SELECT utid FROM thread WHERE name = 'surfaceflinger' LIMIT 1)
  AND state = 'D'
GROUP BY io_wait
ORDER BY total_time_ms DESC;
```

`io_wait=1` 更接近 I/O 等待，`io_wait=0` 更接近内核锁或内存回收；为空时，说明这份 trace 没把相关字段带出来。

**查询 D 状态的阻塞函数分布（需要 sched_blocked_reason）：**

```sql
SELECT
  ts,
  dur / 1e6 AS duration_ms,
  io_wait,
  blocked_function
FROM thread_state
WHERE utid = (SELECT utid FROM thread WHERE name = 'surfaceflinger' LIMIT 1)
  AND state = 'D'
  AND blocked_function IS NOT NULL
ORDER BY dur DESC
LIMIT 20;
```

`blocked_function` 来自 `sched/sched_blocked_reason` ftrace 事件，记录线程进入 D 状态前最后一个非调度器内核函数。如果 `blocked_function` 为空，说明这份 trace 没有启用 `sched_blocked_reason` 事件，需要回到抓取配置补上。

**查询某线程在各 CPU 核心上的运行时间分布（判断是否被调度到小核）：**

```sql
SELECT
  cpu,
  sum(dur) / 1e6 AS time_on_cpu_ms
FROM sched
WHERE utid = (SELECT utid FROM thread WHERE name = 'system_server' LIMIT 1)
GROUP BY cpu
ORDER BY cpu;
```

**查询 CPU 利用率最高的进程（判断系统整体负载）：**

```sql
SELECT
  process.name AS process_name,
  100 * sum(dur) / CAST(TRACE_END() - TRACE_START() AS REAL) AS cpu_utilization_percent
FROM sched
JOIN thread ON sched.utid = thread.utid
JOIN process ON thread.upid = process.upid
GROUP BY process.name
ORDER BY cpu_utilization_percent DESC
LIMIT 20;
```

**查询特定时间段内 CPU 消耗最高的线程（分析特定场景）：**

```sql
SELECT
  thread.name,
  sum(dur) / 1e9 AS cpu_time_s
FROM sched
JOIN thread ON sched.utid = thread.utid
-- 时间戳单位为纳秒，可加上 WHERE ts > 2e9 AND ts < 5e9 来取某一段时间
GROUP BY thread.name
ORDER BY cpu_time_s DESC
LIMIT 20;
```

[已验证: 来源见 Android-Perfetto-09-CPU.md §实战与SQL]

### 第四步：结合 CPU 架构和频率

线程的 Running 时间不仅取决于代码本身，还取决于它在哪个核心上、以什么频率运行。分析时需要结合 Perfetto 的 CPU Frequency 轨道和设备的核心架构（big.LITTLE）来综合判断。

一个关键认知：在异构 CPU 上，同为 2.0 GHz，小核与大核的实际算力天差地别。大核通常具备更宽的乱序执行、更多执行端口、更大的缓存与更激进的预取/分支预测，同频下完成同样工作所需时间更短。因此，"关键线程跑在小核"和"关键线程在大核但频率被限制"都是需要关注的异常信号。

### 总结：状态→原因→优化的速查表

| 状态占比异常 | 可能原因 | 排查方向 |
|---|---|---|
| Running 过长 | 代码计算过重 / 跑小核 / CPU 降频 / 解释执行 | 火焰图 + CPU 频率 + 核心类型 |
| Runnable 过长 | 优先级低 / 绑核不当 / 系统负载高 / CPU 降频锁核 | CPU 负载分布 + 优先级 + 绑核策略 |
| Sleeping 过长 | 锁竞争 / Binder 等待 / I/O 等待 / 主动 sleep | 唤醒关系 + Binder 轨道 + 代码审查 |
| D 状态过长 | 磁盘 I/O / 内存压力 / 内核锁 | Block Reason + I/O 模式 + 内存状态 |

## 与其他章节的关系

本节讨论的线程 CPU 状态是性能分析的"原子单位"。理解了这些状态之后：

- **5.1 Linux 进程调度基础** 解释了为什么线程会被调度或等待——调度器的选核、迁移、优先级策略决定了 Runnable 时间的长短。
- **13.1 Perfetto 基础** 介绍了 Perfetto 的基本操作和视图，是本节的前置知识。
- **13.5 CPU 分析** 从 CPU 整体视角分析频率、负载、调度策略，与本节的线程视角互补。

## 常见问题与误区

**"线程 CPU 使用率高就说明有问题"**。不一定。Running 时间长可能只是因为线程确实有大量工作要做。关键看它是否影响了关键路径上的时序。一个后台线程跑满 CPU，只要不抢占 UI 线程的 CPU 时间，用户体验不受影响。

**"Runnable 时间长一定是调度器的问题"**。不完全是。虽然调度器决策确实影响 Runnable 时间，但更常见的原因是系统整体负载过高或线程优先级设置不当。在分析时，先排除负载和优先级因素，再考虑调度器策略。

**"D 状态一定会导致 ANR"**。不一定。短时间的 D 状态是正常的（比如短暂的 I/O 操作）。只有当 D 状态持续时间超过 ANR 超时阈值（前台 Service 10 秒、前台 Input 5 秒）时，才会触发 ANR。但 D 状态确实是 ANR 的常见原因之一，特别是当它与内核锁或频繁 I/O 操作关联时。

**"wakeup from 信息一定准确"**。不一定。wakeup from 的准确性取决于底层 tracepoint 的类型和内核实现。某些情况下唤醒信息可能指向错误的线程，需要结合代码逻辑和 Binder 调用链来交叉验证。

**"Sleeping 状态不消耗 CPU，所以不影响性能"**。这是对性能的误解。Sleeping 状态下线程虽然不消耗 CPU，但它在等待——等待本身就消耗时间。如果关键线程在执行关键任务时长时间 Sleeping，用户感知到的就是卡顿或延迟。

**"应用设置高优先级就能解决 Runnable 问题"**。不一定，甚至可能适得其反。不同厂商对调度器有各自的客制化改动，应用设置的优先级在某些厂商的调度策略下可能出现意料之外的行为。更可靠的做法是合理安排任务模型，减少关键路径上的线程依赖。


### Perfetto Running 状态全栈技术分析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/当 Perfetto 显示 Running 时,Android 程序到底在做什么? .md
- 类型：DeepResearch 调研结果
- 摘要：从 Perfetto trace 中 Setup proxies 片段的 Running 状态出发，逐层拆解 Linux task_struct→sched_switch→ftrace→Perfetto sched_slice 的完整信号链，覆盖用户态/内核态、ART/native、缓存/TLB 微架构层级，给出 Running vs Runnable vs Sleeping 的精确定义与诊断手法。
- 注入时间：2026-04-28
- 价值：源码级解释了 Perfetto thread state 的内核来源，对 ch13 的 CPU 状态分析章节是极好的补充参考



### 当 Perfetto 显示 Running 时,Android 程序到底在做什么?
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/当 Perfetto 显示 Running 时,Android 程序到底在做什么? .md
- 类型：DeepResearch 调研结果
- 摘要：从 Perfetto trace 中 thread_state='Running' 切片出发，逐层拆解 Running 在 Linux task_struct、ftrace sched_switch、ART 虚拟机、native/Bionic、Binder、系统调用、内核调度器、Arm CPU 微架构各层的精确语义。涵盖 on_rq/on_cpu 区分、用户态/内核态 CPI 分析、cache/TLB miss 诊断方法，并给出从 Perfetto SQL 到 Streamline 的完整诊断工作流。
- 注入时间：2026-04-30
- 价值：源码级贯通 Perfetto Running 状态的完整技术栈，对理解 CPU 调度追踪与性能诊断有直接参考价值

## 参考资料

### 当 Perfetto 显示 Running 时,Android 程序到底在做什么?
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/当 Perfetto 显示 Running 时,Android 程序到底在做什么? .md
- 类型：DeepResearch 调研结果
- 摘要：从 Perfetto trace 中 Setup proxies slice 的 Running 状态出发,逐层拆解 Java→ART→Native→Binder→系统调用→Linux 内核→Arm CPU 微架构的全栈执行路径。详述 task_struct 状态机、sched_switch ftrace 事件、Perfetto sched_slice 视图与 R/R+/S/D 状态的精确语义,涵盖 on_rq/on_cpu 字段、CPU 调度器内部状态迁移,以及如何从 Running 时长推断用户态/内核态时间分布。
- 注入时间：2026-04-29
- 价值：源码级贯通 Perfetto Running 状态的内核语义与调度器实现,对理解 Perfetto 线程状态分析极具参考价值


- [Perfetto 官方文档 - CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [高爷博客 - Android Perfetto 系列 9：CPU 信息解读](https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/)
- [高爷博客 - Systrace 线程 CPU 运行状态分析技巧 - Runnable 篇](https://www.androidperformance.com/2022/01/21/android-systrace-cpu-state-runnable/)
- [高爷博客 - Systrace 线程 CPU 运行状态分析技巧 - Running 篇](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-running/)
- [高爷博客 - Systrace 线程 CPU 运行状态分析技巧 - Sleep 和 Uninterruptible Sleep 篇](https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/)
- [Linux 内核 - TASK_UNINTERRUPTIBLE 定义](https://elixir.bootlin.com/linux/latest/ident/TASK_UNINTERRUPTIBLE)

### 当 Perfetto 显示 Running 时，Android 程序到底在做什么？
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/当 Perfetto 显示 Running 时,Android 程序到底在做什么? .md
- 类型：DeepResearch 调研结果
- 摘要：以 `BindApplication / Setup proxies` 为切口，把 Perfetto 的 Running 状态和 Linux `TASK_RUNNING`、`sched_slice`、user/kernel 切换、ART/native 执行及 CPU 微架构停顿联系起来，能直接提升线程状态解读的精度。
- 注入时间：2026-04-24
- 价值：把 Running 从“在线程状态名词”推进到可落地的 Perfetto 诊断方法。
