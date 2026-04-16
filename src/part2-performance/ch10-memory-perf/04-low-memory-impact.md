---
title: "低内存对系统性能的影响"
chapter: "10.4"
section: "10.4"
status: ready-for-review
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium-high
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_kswapd介绍.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_Linux内存变低会发生什么问题.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_Android帝国之进程杀手--lmkd.md"
  - type: research
    path: "intake/research-feeds/2026-04-02-11-ch04-zram-multialgo-mglru-2025.md"
  - type: official
    path: "source.android.com - mm_events, PSI, lmkd"
tags: ['low-memory', 'kswapd', 'direct-reclaim', 'lmkd', 'GC', 'memory-pressure', 'PSI', 'ZRAM', 'Perfetto', 'MGLRU', 'cgroup', 'mm-events', 'vmscan', 'oom-score-adj']
related_chapters: ["4.1", "4.2", "4.4", "4.5", "4.8", "10.1", "10.6"]
reviewed_date: "2026-04-16"
reviewed_by: openclaw-task6
polish_count: 2
polish_date: "2026-04-09"
polish_by: "task2b-polish"
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: pending
task2b_state: idle
---

# 低内存对系统性能的影响

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 低内存对系统性能的连锁反应：kswapd 活跃 → direct reclaim → I/O 阻塞 → 全局卡顿
- 🔹 lmkd 频繁杀进程 → App 冷启动增加 → 用户感知卡
- 🔹 低内存下的 GC 行为变化：更频繁的 GC、更长的暂停
- 🔹 Perfetto 中识别内存压力的信号：mm_event、vmscan、lmk、PSI
- 🔹 系统级内存优化手段：ZRAM 调优、cgroup 内存限制

### 扩展（可选深入）

- 🔸 低端机（≤4GB RAM）的专项优化策略
- 🔸 Go Edition / Android Lite 的内存优化措施

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解低内存对性能的影响

当我们在 Perfetto 里看到主线程长时间处于 D 状态（Uninterruptible Sleep），或者一个前台 App 突然被杀掉、用户重新打开后走了完整的冷启动流程，根因往往不是 App 自身的问题，而是系统整体进入了低内存状态。低内存不会只影响某一个进程，它会像一场连锁反应——从内核的内存回收机制被激活开始，到 I/O 被打满、GC 频繁触发、进程被杀、用户感知到系统卡顿——整个过程环环相扣。

理解这条因果链，是我们在 Perfetto 中准确判断"这个卡顿到底是 App 问题还是系统问题"的关键。本节会从内核的内存回收机制出发，逐步展开低内存是如何一步步拖慢整个系统的，以及我们如何通过工具识别和定位这些问题。

## 低内存的连锁反应：从 kswapd 到全局卡顿

### 三条水线与 kswapd 的唤醒

Linux 内核用三条水位线来管理每个内存 zone 的空闲内存状态：MIN、LOW 和 HIGH。它们的关系是 MIN < LOW < HIGH。内核在分配内存时会先检查 zone 的空闲页面是否满足水位线要求，这个机制决定了系统在什么时候开始回收内存、用什么方式回收。

当空闲页面高于 LOW 水位线时，一切正常，直接从 Buddy System 分配。当空闲页面降到 LOW 水位线以下但还在 MIN 水位线之上时，内核会唤醒 kswapd 内核线程来异步回收内存。kswapd 是一个专用的后台回收线程——它的职责是在系统还有一定空闲内存时就预先回收，避免等到内存耗尽才开始清理，把不活跃的页面回收掉，让空闲内存回升到 HIGH 水位线。

kswapd 的核心工作函数是 `balance_pgdat()`。它会根据 `scan_control` 结构中的 priority 参数（初始值为 12，逐次递减）来决定每次扫描多少页面。priority 越小，扫描范围越大。如果经过一轮回收后某个 zone 已经 balance（空闲页面达到 HIGH 水位线），就可以停止回收；否则继续降低 priority 扫描更多页面，直到 priority 降到 0 时扫描所有页面。[已验证: 官方文档, source.android.com; 来源: Personal-Knowlodge/source/2026-03-08_wechat_kswapd介绍.md]

在 Perfetto 中，kswapd 作为一个内核线程会出现在进程列表中。正常情况下它是 sleeping 状态，只有在内存压力下才会活跃。在 Trace 中如果发现 `kswapd0` 长时间处于 Running 状态，说明系统在持续回收内存，这是内存紧张的早期信号。

### Direct Reclaim：进程亲自下场回收

当内存进一步紧张，空闲页面降到 MIN 水位线以下时，异步的 kswapd 已经来不及了。此时，发起内存分配的那个进程会被迫亲自执行内存回收——这就是 Direct Reclaim。

Direct Reclaim 和 kswapd 走的是同一条回收路径（最终都调用 `shrink_node()`），但有一个关键区别：Direct Reclaim 是同步的。发起分配的进程会被阻塞，直到回收完成。因此，当 App 在主线程上分配内存时触发 Direct Reclaim，主线程就被阻塞了——在 Perfetto 中表现为进入 D 状态（Uninterruptible Sleep），调用栈中可见 `__alloc_pages_slowpath` → `__perform_reclaim` 路径。

Direct Reclaim 的执行过程是：扫描 LRU 链表 → 根据 swappiness 参数决定回收匿名页还是文件页 → 对脏文件页执行回写 → 释放页面。其中脏页回写会触发磁盘 I/O，而这个 I/O 是同步等待的。

### 连锁反应的完整链条

低内存引发全局卡顿的完整链条是这样的：

内存不足触发 kswapd 持续活跃。kswapd 在后台回收内存会消耗 CPU，如果回收的是匿名页（需要压缩写入 ZRAM），还会额外消耗 CPU 做压缩计算。

当 kswapd 的回收速度跟不上分配速度时，Direct Reclaim 被触发。此时发起内存分配的进程被同步阻塞，必须等待回收完成才能继续执行。

Direct Reclaim 在回收脏文件页时会触发磁盘回写，I/O 带宽可能被打满。更要命的是，当内存紧张到一定程度，几乎所有正在分配内存的进程都会同时进入 Direct Reclaim，争抢同一块 I/O 带宽。[来源: Personal-Knowlodge/source/2026-03-06_wechat_Linux内存变低会发生什么问题.md]

I/O 阻塞进一步蔓延。等待 I/O 完成的进程持有各种内核锁（mutex、rwsem 等），其他等待这些锁的进程也会被连带阻塞——即使某些进程本身不做内存分配，也会因为等待被 I/O 阻塞的进程持有的锁而卡住。

最终传导到用户可感知的层面：UI 线程被阻塞 → 帧渲染超时 → 掉帧。如果阻塞超过 120 秒，甚至可能触发 hungtask 检测，极端情况下整个系统无响应。

在实际分析中，这个连锁反应在 Perfetto 中的典型模式是：多个进程同时出现长时间 D 状态，CPU 使用率反而不高（因为都在等 I/O），I/O 等待时间很长。这个组合是低内存导致全局卡顿的判断依据。

## lmkd 频繁杀进程：冷启动增加与用户感知

### PSI 信号与 lmkd 的触发机制

当内核层面的内存回收（kswapd 和 Direct Reclaim）仍然无法缓解内存压力时，Android 的 lmkd（Low Memory Killer Daemon）就会介入了。lmkd 运行在用户空间，通过 PSI（Pressure Stall Information）信号来感知系统内存紧张程度。

PSI 是 Linux 内核从 4.20 开始提供的一种机制，它统计的是：因为内存（或 CPU、I/O）资源不足，有多少任务被迫等待，以及等待了多久。PSI 提供两种级别的统计：`some`（至少有一个任务在等待）和 `full`（所有非空闲任务都在等待）。lmkd 主要关注 `full` 级别的内存 PSI 信号，因为当所有任务都因为内存不足而等待时，说明系统已经到了必须杀进程的地步。

lmkd 通过 `init_psi_monitors()` 注册 PSI 监听器，设置两个阈值：`psi_partial_stall_ms`（部分阻塞阈值）和 `psi_complete_stall_ms`（完全阻塞阈值）。当内核 PSI 机制检测到内存阻塞时间超过阈值时，会通过 epoll 通知 lmkd。在 Android 高版本上（默认启用 `use_psi` 属性为 true），PSI 已经取代了早期的 `vmpressure` 机制成为 lmkd 的主要信号来源。[已验证: 官方文档, source.android.com; 来源: Personal-Knowlodge/source/2026-03-06_wechat_Android帝国之进程杀手--lmkd.md]

### lmkd 的杀进程策略

lmkd 收到内存压力信号后，会根据进程的 `oom_score_adj` 来选择要杀的进程。在 PSI 触发的情况下，`min_score_adj`（最低可杀分数）通常设置为 201（即 `PREVIOUS_APP_ADJ + 1`），即从"上一个应用"开始往后杀。如果内存极度紧张，这个值会降到 0，前台进程也可能被杀。

被杀进程的选择顺序大致是：缓存进程（900+）→ 后台服务（500+）→ 上一个应用（200）→ 后台可见进程（100）→ 前台进程（0）。分数越高的进程越先被杀。

在 Perfetto 中，lmkd 的杀进程事件会以 `ProcessKilled` 或 `lmk` 相关的 trace event 出现。我们可以在 Trace 中搜索 `lmk` 关键字，或者查看 `lowmemorykiller` 的日志来定位杀进程的时间点。

### 被杀后的冷启动代价

当用户切换到一个之前被 lmkd 杀掉的 App 时，这个 App 需要完整地走一遍冷启动流程：Zygote fork 新进程 → 加载 Application 类 → 执行 ContentProvider 初始化 → Activity 的 onCreate/onStart/onResume。整个流程可能需要数百毫秒甚至数秒。

这个问题的用户体验非常直接：用户之前打开过的 App，再切回去时需要重新走一遍启动流程——闪屏页可能出现、列表需要重新加载、之前的状态丢失。用户会感觉"这个手机很卡"、"App 总是被杀"。

更严重的是，如果系统持续低内存，lmkd 会反复杀进程，而用户又反复打开被杀的 App，形成"杀进程→冷启动→内存又不够→再杀"的恶性循环。在 Perfetto 中表现为频繁的进程启动和 `ProcessKilled` 事件交替出现。

## 低内存下的 GC 行为变化

### ART GC 在低内存下的触发策略

ART 虚拟机的垃圾回收策略会受到系统内存压力的直接影响。在 Android 8.0（Oreo）之后，ART 默认使用 Concurrent Copying（CC）垃圾收集器，这是一个分代、并发的收集器。在正常情况下，CC 收集器的 Young GC 暂停时间通常在 1ms 以下 [待验证: 具体数值因设备、堆大小和 GC 策略而异]，对应用帧率几乎没有影响。

但当系统进入低内存状态时，ART 的 GC 行为会发生几个明显的变化。

最直接的影响是 GC 触发更频繁。ART 在分配对象时会检查当前堆的使用量是否接近上限。在低内存环境下，系统给 App 分配的堆空间可能被压缩（通过 `setSoftLimit` 等 API），导致堆更容易"满"，GC 更频繁地被触发。表现为 Perfetto 中 GC Event 的密度显著增加。

当内存压力持续增加时，GC 类型也会升级。ART 会根据内存压力情况在几种收集器之间切换。轻度压力下使用 Concurrent Copying（并发复制），只需要短暂暂停应用线程。但如果 `onTrimMemory` 回调没有被正确响应，或者系统内存极其紧张，ART 可能会触发 Homogeneous Space Compaction（同构空间压缩）或 Collector Transition（收集器切换），这些操作的暂停时间远高于普通 Young GC，可能导致明显的帧卡顿。[已验证: 官方文档, developer.android.com]

此外，后台 App 也会遭遇压缩 GC。当 App 进入后台后，在低内存环境下 ART 会主动触发压缩 GC 来减少内存占用。这个操作虽然是后台执行的，但会消耗 CPU 资源，可能影响前台 App 的性能。

### 内存抖动与 GC 的恶性循环

内存抖动（Memory Churn）在低内存设备上会被放大。所谓内存抖动，是指在短时间内大量创建和释放对象。正常情况下，ART 的 TLAB（Thread-Local Allocation Buffer）和并发 GC 可以应对一定的抖动。但在低内存环境下：

1. 堆空间有限 → 可分配空间少 → 更频繁触发 GC
2. GC 运行时需要暂停应用线程 → 应用执行变慢
3. 应用变慢导致对象在堆中存活时间更长 → GC 需要扫描更多对象
4. CPU 被 GC 占用 → 应用的主线程得到的时间片更少

在 Perfetto 中，这个恶性循环表现为：GC Event（橙色的块）密度明显增加，帧渲染时间变长，帧之间的间隔中 GC 占比显著升高。在 120Hz 设备上（每帧只有 8.33ms），频繁的 GC 块占据 2-3ms 就足以造成卡顿，低内存导致的 GC 频繁触发很可能是根因。

与 [4.5 App 内存优化](../ch04-memory/05-app-memory-optimization.md) 和 [10.6 内存抖动与频繁 GC](06-memory-churn.md) 的交叉要点：低内存放大了 App 自身的内存管理问题。一个在 8GB 设备上可以容忍的内存抖动模式，在 4GB 设备上可能导致频繁 GC 和严重卡顿。

## 在 Perfetto 中识别内存压力的信号

在 Perfetto Trace 中识别内存压力，需要关注以下几个关键信号源。这些信号通常不会单独出现，而是组合在一起时才有诊断价值。

### mm_events：内核内存事件的快照

mm_events 是 Android 12+ 引入的内存压力追踪机制。它的工作方式比较特别——不会持续记录，只在检测到内存压力时自动启动一段时间的追踪。具体来说，当 kswapd 被唤醒、Direct Reclaim 被触发或内存规整（compaction）开始时，mm_events 会开始收集内存统计数据，包括 vmstat 字段（如 `nr_free_pages`、`pgpgin`、`pgsteal`）和 ftrace 内存事件。

mm_events 的配置文件通常位于 `/vendor/etc/mm_events.cfg`。在 Perfetto 中，我们可以在 `linux.ftrace` 或 `mem.mm_events` 相关的 track 中找到这些数据。[已验证: 官方文档, source.android.com]

### vmscan ftrace 事件

vmscan 是内核虚拟内存扫描子系统的 ftrace 事件。关键的 vmscan 事件包括：

- `mm_vmscan_kswapd_wake`：kswapd 被唤醒，说明空闲内存降到了 LOW 水位线以下
- `mm_vmscan_kswapd_sleep`：kswapd 完成回收进入休眠，说明内存压力缓解
- `mm_vmscan_direct_reclaim_begin` / `mm_vmscan_direct_reclaim_end`：Direct Reclaim 的开始和结束
- `mm_vmscan_lru_shrink_inactive`：正在扫描 Inactive LRU 回收页面

在 Perfetto 中，这些事件可以帮助我们精确判断内存压力开始的时间点、持续多久、触发了哪种级别的回收。[已验证: 官方文档, source.android.com]

### lmk 事件

lmkd 的杀进程事件在 Perfetto 中通常以 `lowmemorykiller` 标签出现。我们可以在 logcat 中搜索 `lowmemorykiller` 或 `lmk` 关键字，在 Perfetto 中搜索 `ProcessKilled` slice。每条 lmk 事件包含了被杀进程的 PID、UID、`oom_score_adj`、释放的内存大小以及触发原因（如 `device is low on swap`、`thrashing`）。

### PSI 数据

PSI 数据在 Perfetto 的 `sys_stats` 数据源中可以找到。PSI 为每种资源（memory、cpu、io）提供 `some` 和 `full` 两种级别的统计，分别在 10 秒、60 秒和 300 秒的时间窗口内取平均值。

关注 PSI 的 `memory full` 指标最为关键——当这个值持续大于 0 时，说明系统中有时间所有非空闲任务都在等待内存，这是严重的内存压力信号。PSI monitor（lmkd 使用的那种）可以检测到短时间内的压力突增，比平均值更敏感。通过 `cat /proc/pressure/memory` 可以查看当前系统的内存 PSI 实时数值。[已验证: 官方文档, kernel.org]

### 综合判断模式

在实际分析中，内存压力的判断不能只看单一指标。一个典型的内存压力场景在 Perfetto 中表现为：

1. **kswapd 长时间活跃**：`kswapd0` 线程持续 Running
2. **Direct Reclaim 事件增多**：多个进程同时出现 D 状态，调用栈中有 `shrink_node`
3. **GC 密度增加**：目标 App 的 GC Event 间隔明显缩短
4. **I/O 等待升高**：进程的 `iowait` 比例增加
5. **lmk 事件出现**：后台进程被杀
6. **冷启动增多**：用户打开 App 时走了完整启动流程

如果 1-3 出现但还没有 5-6，说明系统在低内存但还在努力维持。如果 5-6 也出现了，说明系统已经无法仅靠内存回收来维持运转了。

[图：Perfetto 中低内存场景的典型 Trace 片段，标注 kswapd 活跃区域、Direct Reclaim 的 D 状态、GC 密集区域和 lmk 事件]

## 系统级内存优化手段

### ZRAM 调优

ZRAM 是 Android 内存管理的核心组件之一。它在 RAM 中创建一个压缩的块设备作为 swap 空间。当内核需要回收匿名页时，不会写到慢速的闪存上，而是压缩后写入 ZRAM。LZ4 算法的典型压缩比约为 3:1，意味着 3GB 的匿名页数据大约只需要 1GB 的 ZRAM 空间。

ZRAM 的调优涉及几个参数：

**ZRAM 大小**。设备厂商通常在设备初始化时设置 ZRAM 的最大容量。对于 Android Go 设备，Qualcomm 的调优指南建议设为物理 RAM 的 75%。更大的 ZRAM 意味着更多后台应用可以保持在内存中（以压缩形式），但也会增加压缩/解压缩的 CPU 开销。在设备上可以通过 `cat /proc/swaps` 查看 swap 设备和容量，通过 `cat /sys/block/zram0/mm_stat` 查看原始数据大小、压缩后大小等详细统计。

**Swappiness**。这个内核参数控制内核回收匿名页（swap out）和回收文件页（drop page cache）的倾向比例。取值范围 0-200，默认值 60。在 Android 设备上，较低值（10-30）通常更适合，因为移动设备优先保证前台 UI 响应，而不是积极地 swap 后台进程。但某些厂商会设置为 100 甚至更高来更积极地利用 ZRAM。[已验证: 官方文档, developer.android.com]

**压缩算法**。Android 通常使用 LZ4 作为 ZRAM 的压缩算法，在压缩速度和压缩比之间取得平衡。Kernel 6.12 引入了 `CONFIG_ZRAM_MULTI_COMP`（多算法重压缩），允许先用 LZ4 快速压缩，后台再用 ZSTD 进一步压缩提升压缩比。同样的物理 RAM 就可以容纳更多压缩后的页面。[已验证: 官方文档, kernel.org; 来源: intake/research-feeds/2026-04-02-11-ch04-zram-multialgo-mglru-2025.md]

### cgroup 内存限制

Android 使用 cgroup（Control Group）来对进程组施加资源限制，其中内存 cgroup 是低内存管理的核心工具之一。

Android 10+ 引入了 cgroup 抽象层和 Task Profiles 机制。厂商可以在 `cgroups.json` 中定义 cgroup 配置，在 `task_profiles.json` 中将特定类型的任务映射到对应的 cgroup。这使得系统可以为不同优先级的进程设置不同的内存限制——前台进程几乎没有限制，而后台进程在内存紧张时会被优先限制甚至终止。

cgroup 与 lmkd 配合工作：lmkd 通过 cgroup 来监控进程的内存使用，并基于 `oom_score_adj` 选择要杀的进程。在 Android 5.0+ 上，lmkd 使用用户空间的 cgroup 接口来管理进程，替代了早期内核空间的 `lowmemorykiller` 驱动。[已验证: 官方文档, source.android.com]

### MGLRU：更高效的页面回收

MGLRU（Multi-Generational LRU）是 Linux 6.1 引入的页面回收优化，替代了传统的 Active/Inactive 双链表 LRU。MGLRU 使用多个"代"（generation）来跟踪页面的热度，比传统的二分法更精确。简单来说，传统 LRU 只有"热"和"冷"两个桶，而 MGLRU 有多个温度层级，能更准确地识别真正应该被回收的页面。

MGLRU 已在 Android Common Kernel 中启用。它的实际效果是减少"误杀"——把还在使用的页面错误回收，然后很快又要读回来（thrashing）的情况显著减少。在 Perfetto 中，MGLRU 减少了 vmscan 事件中的无效回收次数。[已验证: 官方文档, kernel.org; 来源: intake/research-feeds/2026-04-02-11-ch04-zram-multialgo-mglru-2025.md]

`[自动发现]` MGLRU 和 Kernel 6.12 的 ZRAM 多算法重压缩是 2025-2026 年内存管理的重要进展，预示着未来的 Android 设备在同样 RAM 容量下将能维持更多的后台应用。

## 低端机的专项优化策略

对于 4GB 及以下 RAM 的设备，低内存是常态而非异常。这些设备需要更激进的优化策略。

### 内存分配策略调整

低端机通常会调低各种内存阈值。比如将 ActivityManager 的后台进程上限从标准设备的 32 个降到 8-12 个；降低缓存进程阈值（如 lmkd 的 min_free_level 配置）让 lmkd 更早开始杀后台进程；减小 ZRAM 的最大容量（因为物理 RAM 本身就少，需要留更多给前台应用使用）。这些调整的目标是：宁可牺牲后台保活能力，也要保证前台应用的流畅性。

### App 层面的适配

Google 提供了 `ActivityManager.isLowRamDevice()` API，让 App 可以感知自己运行在低端设备上，据此调整行为。常见的适配包括：降低图片加载的分辨率、减少内存缓存大小、延迟非关键资源的加载、使用更轻量的数据结构。对于开发者来说，在 4GB 设备上测试 App 的内存行为比在 8GB 设备上更能暴露问题。

### Android Go Edition 的优化

Android Go Edition（Android 16 Go 版本扩展到了 4GB RAM 设备）是一系列系统级优化的集合。除了上述的 ZRAM 和 cgroup 调优之外，Go Edition 还包括：更轻量的系统 App（如 Google Go、Chrome Lite）、预装应用体积更小、默认开启 Chrome 的数据节省模式、更精简的通知机制。Go Edition 的内核也经过了裁剪，移除了一些在低端硬件上用不到的特性来减少内核自身的内存占用。[已验证: 官方文档, android.com]

## 常见问题与误区

**"低内存只是低端机的问题"** — 不对。即使是 8GB 或 12GB 的设备，如果用户打开了大量 App（尤其是 Chrome 这种吃内存的应用），或者某个 App 存在内存泄漏，系统同样会进入低内存状态。无论设备 RAM 多大，在 Perfetto 中分析性能问题时都应检查是否存在内存压力信号。

**"kswapd 活跃就说明有问题"** — 不准确。kswapd 周期性地被唤醒和休眠是正常的内存管理行为。只有当 kswapd 持续活跃（长时间 Running 状态无法进入 Sleep），或者伴随大量 Direct Reclaim 事件时，才说明内存压力真正严重。

**"手动调用 System.gc() 可以帮助缓解低内存"** — 恰恰相反。手动触发 GC 会干扰 ART 的自动回收策略，增加 GC 暂停次数。正确的做法是响应 `onTrimMemory()` 回调释放不必要的资源。

**"ZRAM 越大越好"** — 不对。ZRAM 本身占用物理 RAM 来存储压缩后的数据。过大的 ZRAM 会挤占前台应用可用的内存空间，而且压缩/解压缩操作本身消耗 CPU。需要根据设备的 RAM 容量、CPU 性能和使用场景来平衡。

**"lmkd 杀进程是 bug"** — 不是。lmkd 杀后台进程是正常的内存管理行为，目的是为前台应用腾出内存。只有当前台进程被杀（oom_score_adj 为 0 的进程），或者同一批进程被反复杀和重启时，才是需要关注的问题。

## 与其他章节的关系

本章讨论的低内存影响与多个章节存在交叉：

- **§4.1 Android 内存模型全景**：理解 Android 整体内存管理框架
- **§4.2 Linux 内核内存管理**：kswapd、Direct Reclaim 的详细机制分析
- **§4.4 Low Memory Killer**：lmkd 的完整工作流程和配置
- **§4.5 App 内存优化**：App 层面如何减少内存占用，降低被 lmkd 杀的概率
- **§10.1 App 内存分析**：使用工具分析 App 内存使用
- **§4.8 ART 分代垃圾回收**：ART GC 策略在不同内存压力下的行为变化
- **§10.6 内存抖动与频繁 GC**：GC 频繁触发与低内存的关系

## 参考资料

- [AOSP mm_events 文档](https://source.android.com/docs/core/memory/mm-events) — Android 内存压力追踪机制
- [Linux Kernel PSI 文档](https://docs.kernel.org/accounting/psi.html) — Pressure Stall Information 机制说明
- [lmkd 源码](https://android.googlesource.com/platform/system/memory/lmkd/) — Android Low Memory Killer Daemon
- [Perfetto 文档 - Memory Tracking](https://perfetto.dev/docs/data-sources/memory) — Perfetto 内存追踪数据源
- [kswapd 详解 — OPPO 内核工匠](https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247487168) — kswapd 工作流程深度解析
- [Linux 内存变低会发生什么 — 腾讯技术工程](https://mp.weixin.qq.com/s?__biz=MjM5ODYwMjI2MA==&mid=2649785631) — 低内存的连锁反应分析
- [ZRAM Multi-Comp — kernel.org](https://kernel.org/doc/html/latest/admin-guide/blockdev/zram.html) — ZRAM 多算法重压缩
- [MGLRU — kernel.org](https://kernel.org/doc/html/latest/admin-guide/mm/multigen_lru.html) — Multi-Generational LRU 页面回收
- [Android cgroups — source.android.com](https://source.android.com/docs/core/perf/cgroups) — Android cgroup 抽象层与 Task Profiles
