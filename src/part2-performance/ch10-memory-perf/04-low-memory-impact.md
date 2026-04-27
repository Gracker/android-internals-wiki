---
title: "低内存对系统性能的影响"
chapter: "10.4"
section: "10.4"
status: finalized
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
reviewed_date: "2026-04-26"
reviewed_by: openclaw-task6
polish_count: 5
polish_date: "2026-04-22"
polish_by: "task6-review"
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_result: pass-tech-review
task9_state: reviewed
task2b_result: fixed
task2b_state: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-04-27"
last_task9_at: "2026-04-27T19:36:19+08:00"
last_task2b_at: "2026-04-26T11:51:00+08:00"
rework_by: openclaw-task2b
rework_type: "review回炉修复（Task9/External 问题单）"
repaired_date: "2026-04-26"
repaired_by: "openclaw-task2b"
review_round: 3
---

# 低内存对系统性能的影响

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 低内存对系统性能的连锁反应：kswapd 活跃 → direct reclaim → I/O 阻塞 → 全局卡顿
- 🔹 lmkd 频繁杀进程 → App 冷启动增加 → 用户感知卡
- 🔹 低内存下的 GC 行为变化：更频繁的 GC、更长的暂停
- 🔹 Perfetto 中识别内存压力的信号：mm_events、vmscan、lmk、PSI
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

当我们在 Perfetto 里看到主线程长时间处于 D 状态（Uninterruptible Sleep），或者一个前台 App 突然被杀掉、用户重新打开后走了完整的冷启动流程，根因往往是系统整体进入了低内存状态。低内存的影响像一场连锁反应——从内核的内存回收机制被激活开始，到 I/O 被打满、GC 频繁触发、进程被杀、用户感知到系统卡顿——整个过程环环相扣。

理解这条因果链，是我们在 Perfetto 中准确判断"这个卡顿到底是 App 问题还是系统问题"的关键。本节会从内核的内存回收机制出发，逐步展开低内存是如何一步步拖慢整个系统的，以及我们如何通过工具识别和定位这些问题。

## 低内存的连锁反应：从 kswapd 到全局卡顿

### 三条水线与 kswapd 的唤醒

Linux 内核用三条水位线来管理每个内存 zone 的空闲内存状态：MIN、LOW 和 HIGH。它们的关系是 MIN < LOW < HIGH。内核在分配内存时会先检查 zone 的空闲页面是否满足水位线要求，这个机制决定了系统在什么时候开始回收内存、用什么方式回收。

当空闲页面高于 LOW 水位线时，一切正常，直接从 Buddy System 分配。当空闲页面降到 LOW 水位线以下但还在 MIN 水位线之上时，内核会唤醒 kswapd 内核线程来异步回收内存。kswapd 是一个专用的后台回收线程——它的职责是在系统还有一定空闲内存时就预先回收，避免等到内存耗尽才开始清理，把不活跃的页面回收掉，让空闲内存回升到 HIGH 水位线。

kswapd 的核心工作函数是 `balance_pgdat()`。它会根据 `scan_control` 结构中的 priority 参数（初始值为 12，逐次递减）来决定每次扫描多少页面。priority 越小，扫描范围越大。如果经过一轮回收后某个 zone 已经 balance（空闲页面达到 HIGH 水位线），就可以停止回收；否则继续降低 priority 扫描更多页面，直到 priority 降到 0 时扫描所有页面。[已验证: 官方文档, source.android.com; 来源: Personal-Knowlodge/source/2026-03-08_wechat_kswapd介绍.md]

在 Perfetto 中，kswapd 作为一个内核线程会出现在进程列表中。正常情况下它是 sleeping 状态，只有在内存压力下才会活跃。在 Trace 中如果发现 `kswapd0` 长时间处于 Running 状态，说明系统在持续回收内存，这是内存紧张的早期信号。

### Direct Reclaim：进程亲自下场回收

当内存进一步紧张，空闲页面降到 MIN 水位线以下时，异步的 kswapd 已经来不及了。此时，发起内存分配的那个进程会被迫亲自执行内存回收——这就是 Direct Reclaim。

Direct Reclaim 和 kswapd 走的是同一条回收路径（最终都调用 `shrink_node()`），但有一个关键区别：Direct Reclaim 是同步的。发起分配的进程会被阻塞，直到回收完成。因此，当 App 在主线程分配内存并触发 Direct Reclaim，主线程就被阻塞了——在 Perfetto 中表现为进入 D 状态（Uninterruptible Sleep），调用栈中可见 `__alloc_pages_slowpath` → `__perform_reclaim` 路径。

Direct Reclaim 的执行过程是：扫描 LRU 链表 → 根据 swappiness 参数决定回收匿名页还是文件页 → 对脏文件页执行回写 → 释放页面。其中脏页回写会触发磁盘 I/O，而这个 I/O 是同步等待的。

### 连锁反应的完整链条

低内存引发全局卡顿的完整链条是这样的：

内存不足触发 kswapd 持续活跃。kswapd 在后台回收内存会消耗 CPU，如果回收的是匿名页（需要压缩写入 ZRAM），还会额外消耗 CPU 做压缩计算。

当 kswapd 的回收速度赶不上内存分配速度时，Direct Reclaim 被触发。此时发起内存分配的进程被同步阻塞，必须等待回收完成才能继续执行。

Direct Reclaim 在回收脏文件页时会触发磁盘回写，I/O 带宽可能被打满。更严重的是，当内存紧张到一定程度，几乎所有正在分配内存的进程都会同时进入 Direct Reclaim，争抢同一块 I/O 带宽。[来源: Personal-Knowlodge/source/2026-03-06_wechat_Linux内存变低会发生什么问题.md]

I/O 阻塞进一步蔓延。等待 I/O 完成的进程持有各种内核锁（mutex、rwsem 等），其他等待这些锁的进程也会被连带阻塞——即使某些进程本身不做内存分配，也会因为等待被 I/O 阻塞的进程持有的锁而卡住。

最终传导到用户可感知的层面：UI 线程被阻塞 → 帧渲染超时 → 掉帧。如果阻塞超过 120 秒，甚至可能触发 hungtask 检测，极端情况下整个系统无响应。

在实际分析中，这个连锁反应在 Perfetto 中的典型模式是：多个进程同时出现长时间 D 状态，CPU 使用率反而不高（因为都在等 I/O），I/O 等待时间很长。这个组合是低内存导致全局卡顿的判断依据。

## lmkd 频繁杀进程：冷启动增加与用户感知

### PSI 信号与 lmkd 的触发机制

当内核层面的内存回收（kswapd 和 Direct Reclaim）仍然无法缓解内存压力时，Android 的 lmkd（Low Memory Killer Daemon）就会介入了。lmkd 运行在用户空间，通过 PSI（Pressure Stall Information）信号来感知系统内存紧张程度。

PSI 是 Linux 内核从 4.20 开始提供的一种机制，它统计的是：因为内存（或 CPU、I/O）资源不足，有多少任务被迫等待，以及等待了多久。PSI 提供两种级别的统计：`some`（至少有一个任务在等待）和 `full`（所有非空闲任务都在等待）。lmkd 主要关注 `full` 级别的内存 PSI 信号，因为当所有任务都因为内存不足而等待时，说明系统已经到了必须杀进程的地步。

lmkd 通过 `init_psi_monitors()` 注册 PSI 监听器，设置两个阈值：`psi_partial_stall_ms`（部分阻塞阈值）和 `psi_complete_stall_ms`（完全阻塞阈值）。当内核 PSI 机制检测到内存阻塞时间超过阈值时，会通过 epoll 通知 lmkd。从 Android 10 开始，PSI 已取代早期的 `vmpressure` 机制成为 lmkd 的默认信号来源（`use_psi` 属性默认为 true）。[已验证: 官方文档, source.android.com; 来源: Personal-Knowlodge/source/2026-03-06_wechat_Android帝国之进程杀手--lmkd.md]

### lmkd 的杀进程策略

lmkd 收到内存压力信号后，会根据进程的 `oom_score_adj` 和当前压力等级选择可杀范围。`min_score_adj` 表示本轮候选进程的最低 `oom_score_adj`，它是运行时阈值或设备属性阈值，不能等同于某个固定进程等级。AOSP `ProcessList` 里常见分层是：前台进程 0、可见进程 100、perceptible 进程 200、服务进程 500、previous app 700、cached 进程 900-999。

被杀进程通常从分数更高的一侧开始筛选：cached 进程（900+）优先，之后才可能进入 previous app（700）、服务进程（500）、perceptible 进程（200）、可见进程（100）和前台进程（0）。常见设备会把 `lowmem_min_oom_score` 放在 701 附近，用来避开 previous app；在压力继续升级或厂商策略更激进时，阈值才会继续下探。分析 lmkd 日志时要直接读事件里的 `oom_score_adj`、`min_score_adj`、kill reason 和释放内存，不能把 201 写成 `PREVIOUS_APP_ADJ`。

在 Perfetto 中，lmkd 的杀进程事件会以 `ProcessKilled` 或 `lmk` 相关的 trace event 出现。我们可以在 Trace 中搜索 `lmk` 关键字，或者查看 `lowmemorykiller` 的日志来定位杀进程的时间点。

### 被杀后的冷启动代价

当用户切换到一个之前被 lmkd 杀掉的 App 时，这个 App 需要完整地走一遍冷启动流程：Zygote fork 新进程 → 加载 Application 类 → 执行 ContentProvider 初始化 → Activity 的 onCreate/onStart/onResume。整个流程可能需要数百毫秒甚至数秒。

这个问题的用户体验非常直接：用户之前打开过的 App，再切回去时需要重新走一遍启动流程——闪屏页可能出现、列表需要重新加载、之前的状态丢失。用户会感觉"这个手机很卡"、"App 总是被杀"。

更严重的是，如果系统持续低内存，lmkd 会反复杀进程，而用户又反复打开被杀的 App，形成"杀进程→冷启动→内存又不够→再杀"的恶性循环。在 Perfetto 中表现为频繁的进程启动和 `ProcessKilled` 事件交替出现。

## 低内存下的 GC 行为变化

### ART GC 在低内存下的触发策略

ART 的垃圾回收会直接受到系统内存压力影响。就 Perfetto 的常见观测口径来说，轻量的 Young / Minor GC 往往落在 1ms-3ms；这个范围适合描述短命对象回收，不适合套到 Major / Full GC。后者在低内存、对象晋升多或需要 compaction 时，停顿可以拉到 10ms 以上。

低内存先带来的变化是 GC 频率抬高。ART 在分配对象时会持续检查堆使用量和增长空间。系统压力一上来，可用堆空间更容易逼近上限，GC 事件的间隔会明显缩短，在 Perfetto 里能看到 GC slice 更密。

内存继续吃紧时，GC 类型也会升级。除了常规的 Young / Minor GC，系统还可能进入更重的 compaction 或 collector transition 路径。这些阶段会让暂停时间和 CPU 占用一起上升，120Hz 设备尤其容易直接体现为掉帧。

后台进程也会在压力下主动做内存收缩。App 退到后台后，ART 可能触发更重的整理型 GC 来降低驻留集。这部分工作虽然不直接阻塞前台界面，但会和 kswapd、压缩 swap 一起争 CPU。

### 内存抖动与 GC 的恶性循环

内存抖动（Memory Churn）在低内存设备上会被放大。所谓内存抖动，是指在短时间内大量创建和释放对象。正常情况下，ART 的 TLAB（Thread-Local Allocation Buffer）和并发 GC 可以应对一定的抖动。但在低内存环境下：

1. 堆空间有限 → 可分配空间少 → 更频繁触发 GC
2. GC 运行时需要暂停应用线程 → 应用执行变慢
3. 应用变慢导致对象在堆中存活时间更长 → GC 需要扫描更多对象
4. CPU 被 GC 占用 → 应用的主线程得到的时间片更少

在 Perfetto 中，这个恶性循环表现为：GC Event（橙色的块）密度明显增加，帧渲染时间变长，帧之间的间隔中 GC 占比显著升高。在 120Hz 设备上（每帧只有 8.33ms），频繁的 GC 块占据 2-3ms 就足以造成卡顿，低内存导致的 GC 频繁触发很可能是根因。

与 [4.5 App 内存优化](../../part1-fundamentals/ch04-memory/05-app-memory-optimization.md) 和 [10.6 内存抖动与频繁 GC](06-memory-churn.md) 的交叉要点：低内存放大了 App 自身的内存管理问题。一个在 8GB 设备上可以容忍的内存抖动模式，在 4GB 设备上可能导致频繁 GC 和严重卡顿。

## 在 Perfetto 中识别内存压力的信号

在 Perfetto Trace 中识别内存压力，需要关注以下几个关键信号源。这些信号通常不会单独出现，而是组合在一起时才有诊断价值。

### mm_events：内存压力触发的 Perfetto 记录

`mm_events` 是 Android 12+ 的内存压力记录机制，和 `perf_event_open` 常驻订阅 tracepoint 的用户态守护进程模型不同。设备启用后，内存压力触发器会拉起一段受限采集窗口，按 `/vendor/etc/mm_events.cfg` 记录 vmstat 和 ftrace/mm_event 数据，用来保留压力发生前后的证据。

排查时先看 `persist.mm_events.enabled` 是否打开，再看触发器和限流配置。常见触发器是 `kmem_activity`，触发过密时会受 rate limit 限制；所以 trace 里没有 `mm_events` 记录，不等于设备没有发生内存压力。

在 Perfetto 里，`mm_events` 要和 `linux.ftrace` 轨道一起读：前者给出压力窗口内的统计快照，后者用 `mm_vmscan_*`、`mm_compaction_*` 把时序补齐。Android 10/11 还没有这条路径，分析这两个版本时仍然回到 `vmscan` ftrace、PSI 和 lmkd 日志。

[已验证: 官方文档, source.android.com; 源码锚点: system/memory/mm_events/]

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

可复现的低内存 Trace 可以从下面这份配置起步。它覆盖 vmscan、sched、process stats、PSI、ART GC 和 lmkd 事件；设备内核裁剪不同时，录制前先用 `adb shell ls /sys/kernel/tracing/events/vmscan` 和 `adb shell atrace --list_categories` 确认可用项。

```protobuf
buffers { size_kb: 32768 fill_policy: RING_BUFFER }
duration_ms: 10000

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "vmscan/mm_vmscan_kswapd_wake"
      ftrace_events: "vmscan/mm_vmscan_kswapd_sleep"
      ftrace_events: "vmscan/mm_vmscan_direct_reclaim_begin"
      ftrace_events: "vmscan/mm_vmscan_direct_reclaim_end"
      atrace_categories: "am"
      atrace_categories: "dalvik"
      atrace_categories: "lmkd"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config { scan_all_processes_on_start: true }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms: 1000
      vmstat_period_ms: 1000
      stat_period_ms: 1000
      psi_period_ms: 1000
    }
  }
}
```

读这类 Trace 时按同一时间窗核对四组信号：`kswapd0` 长时间 Running，应用线程出现 Direct Reclaim 前后的 D 状态，目标 App 的 GC slice 变密，随后出现 `lmkd` / `ProcessKilled` 事件。Perfetto 版本暴露 `mem.mm_events` 视图时，可以用它汇总 kswapd、direct reclaim 和 compaction 计数；没有该视图时，直接回到上面的 ftrace slice 和线程状态。

## 系统级内存优化手段

### ZRAM 调优

ZRAM 是 Android 内存管理的核心组件之一。它在 RAM 中创建一个压缩的块设备作为 swap 空间。当内核需要回收匿名页时，不会写到慢速的闪存上，而是压缩后写入 ZRAM。LZ4 算法的典型压缩比约为 3:1，意味着 3GB 的匿名页数据大约只需要 1GB 的 ZRAM 空间。

ZRAM 的调优涉及几个参数：

**ZRAM 大小**。设备厂商通常在设备初始化阶段给 ZRAM 设一个上限。上限大，后台匿名页更容易驻留；上限小，前台能拿到更多原始物理内存。它是在 RAM 和驻留率之间做取舍，不存在统一最优值。排查设备配置时，可以先用 `cat /proc/swaps` 看 swap 设备和容量，再用 `cat /sys/block/zram0/mm_stat` 看原始数据大小、压缩后大小和回收效果。

**Swappiness**。这个内核参数控制内核回收匿名页（swap out）和回收文件页（drop page cache）的倾向比例。取值范围 0-200，默认值 60。在 Android 设备上，较低值（10-30）通常更适合，因为移动设备优先保证前台 UI 响应，而不是积极地 swap 后台进程。但某些厂商会设置为 100 甚至更高来更积极地利用 ZRAM。[已验证: 官方文档, developer.android.com]

**压缩算法与重压缩**。默认主算法通常还是 LZ4，优先保障压缩和解压延迟。支持 Multi-Comp 的内核会额外暴露 `/sys/block/zram0/recomp_algorithm`，让设备为冷页配置更高压缩比的二级算法。新写入的匿名页先走低延迟算法，长时间驻留的冷页再用 ZSTD 这类算法重压缩，换取更高的驻留密度。排查设备配置时，先 `cat /sys/block/zram0/recomp_algorithm` 看支持列表和当前选择，再结合 `mm_stat` 判断压缩比有没有明显变化。[已验证: 官方文档, kernel.org; 来源: intake/research-feeds/2026-04-02-11-ch04-zram-multialgo-mglru-2025.md]

### Android 15+：16KB 页面与内存压力口径

Android 15 支持 16KB Page Size。页变大后，TLB miss 和 page table walk 会下降，但内部碎片也会增加。公开量化材料和外部 review 都把平均内存占用抬升描述在约 9% 这个量级，跨版本对比 `meminfo`、RSS、PSS 时要先把页大小纳入口径。

低内存分析里最直接的变化有两个。第一，同样一批分配在 16KB 设备上的 RSS 往往更高。第二，回收一个 page 释放的是 16KB 而不是 4KB，kswapd、direct reclaim 和 ZRAM 写入的节奏也会跟着变化。看到 Android 15 设备更早进入压力区时，要把页大小和页边界变化一起纳入判断。

设备侧可以用 `adb shell getconf PAGE_SIZE` 确认页大小。做回归报表时，最好把 4KB 和 16KB 设备分桶。

### cgroup 内存限制

Android 使用 cgroup（Control Group）来对进程组施加资源限制，其中内存 cgroup 是低内存管理的核心工具之一。

Android 10+ 引入了 cgroup 抽象层和 Task Profiles 机制。厂商可以在 `cgroups.json` 中定义 cgroup 配置，在 `task_profiles.json` 中把不同类型的任务映射到对应的 cgroup。这让系统可以按进程优先级做记账、隔离和资源约束：前台路径尽量宽松，后台进程更容易在压力下被收缩。

这里的版本线要拆开看。早期 Android 主要依赖内核态 `lowmemorykiller` 驱动。Android 9 起，如果设备没有检测到 in-kernel LMK，且内核满足 memcg 等前提，可以启用 userspace `lmkd`。Android 10 起，内核提供 PSI monitor 时，lmkd 默认优先用 PSI 做内存压力检测；缺少 PSI 时再回退到 `vmpressure` 或 `minfree` 路径。

cgroup 和 PSI 不是同一层。cgroup 负责进程分组、内存记账和 task profile 约束；PSI 负责把 stall 时间暴露给 lmkd，帮助它决定什么时候该杀后台进程。把这几条线分开看，才不会把“userspace lmkd”、“memcg 依赖”和“PSI 模式”写成同一个版本开关。[已验证: 官方文档, source.android.com]

### 内存规整：内核 kcompactd 与 cached app compaction

公开 Android / AOSP 口径里没有 Android 10 引入 `compactd` 这个独立用户空间 daemon。低内存分析要拆成两层：内核 compaction 负责把分散空闲页整理成连续高阶页；Android Framework 的 cached app compaction 负责压缩或回收 cached 进程的一部分匿名页，降低后台 RSS。

内核侧看 `kcompactd` 线程、`/proc/vmstat` 里的 `compact_*` 计数，以及 ftrace 的 `mm_compaction_*` 事件。它处理的是系统空闲页碎片化，目标是让高阶页分配更容易成功，不会直接释放 App 的 Java 对象。

Framework 侧看 `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` 相关逻辑。它会按 cached 进程状态触发 partial / full compaction，和 lmkd、PSI 配合降低后台进程驻留成本。排查时不要把这条路径命名为 `compactd`，也不要让读者去找不存在的守护进程。[已验证: source.android.com; AOSP frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

### onTrimMemory 与系统压力信号的边界

`onTrimMemory()` 只能给 App 一个粗粒度提示，PSI、`mm_vmscan_*` 和 lmkd 日志才是系统压力判断的主证据。特别是在 API 34 之后，`TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 这些级别已经不再投递给 App；API 35 又把这些常量标成 deprecated。

对现代版本来说，更稳的解释方式只有两类：

- `TRIM_MEMORY_UI_HIDDEN (20)`：界面离开前台，适合释放 UI 相关资源
- `TRIM_MEMORY_BACKGROUND (40)`：进程退到 LRU 背景区，后台缓存继续收缩

API 33 及以下如果还能收到更细的 trim level，可以把它当额外提示，但正文里的系统压力判断不要再建立在这些旧常量上。确认系统是不是已经进入低内存自救阶段，证据还是 PSI、`mm_vmscan_*`、lmkd kill 日志和冷启动回访率。

### MGLRU：更高效的页面回收

MGLRU（Multi-Generational LRU）用多代链表跟踪页面热度，替代传统 active/inactive 双链表的二分口径。回收时优先淘汰最老一代，所以页面冷热判断更细，错误回收和很快又被读回来的 refault 会更少。

判断设备是否开启这条路径，先看 `/sys/kernel/mm/lru_gen/enabled`。常见值如 `0x0007` 说明核心代际回收能力已经打开，不同 GKI / OEM 分支也可能给出别的 bitmask，所以把它当成能力标记来读，不要写成绝对常量。

在 Perfetto 里量化 MGLRU 是否起作用，重点看三组信号：

1. `mm_vmscan_direct_reclaim_*` 是否减少，前台线程的 D 状态是否缩短
2. `mm_vmscan_kswapd_*` 仍然存在，但反复扫描同一批页的迹象是否下降
3. lmkd 的 thrashing / refault 相关 kill 是否减少，冷启动回访率是否更稳

ZRAM 重压缩和 MGLRU 经常一起出现，但两者解决的问题不同。前者提高匿名页驻留密度，后者减少错误回收。看 Trace 时要把“压得下”和“回得准”分开判断。

[已验证: 官方文档, kernel.org; 来源: intake/research-feeds/2026-04-02-11-ch04-zram-multialgo-mglru-2025.md]

## 低端机的专项优化策略

对于 4GB 及以下 RAM 的设备，低内存是常态而非异常。这些设备需要更激进的优化策略。

### 内存分配策略调整

低 RAM 设备通常会把后台进程上限、缓存进程阈值和 ZRAM 预算设得更紧，让 lmkd 更早回收后台进程，把更多物理内存留给前台路径。设计目标很直接：后台保活能力可以下降，前台交互不能被拖垮。

### App 层面的适配

Google 提供了 `ActivityManager.isLowRamDevice()` API，让 App 可以感知自己运行在低端设备上，据此调整行为。常见的适配包括：降低图片加载的分辨率、减少内存缓存大小、延迟非关键资源的加载、使用更轻量的数据结构。对于开发者来说，在 4GB 设备上测试 App 的内存行为比在 8GB 设备上更能暴露问题。

### Android Go Edition 的优化

Android Go Edition 是面向低 RAM 设备的一组系统配置和产品策略。除了更紧的内存阈值之外，还会配套更轻量的系统应用、较小的预装体积和更保守的后台策略，目标是把有限内存优先留给前台交互。[已验证: 官方文档, android.com]

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
- [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes) — 16KB 页面大小的版本背景与适配要求
- [Android cgroups — source.android.com](https://source.android.com/docs/core/perf/cgroups) — Android cgroup 抽象层与 Task Profiles
