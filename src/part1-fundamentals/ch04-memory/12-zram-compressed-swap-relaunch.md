---
title: "ZRAM 压缩交换与应用重启延迟"
chapter: "4.12"
section: "4.12"
status: ready-for-review
drafted_date: "2026-05-20"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-20"
last_verified_against: "AOSP main system/memory/lmkd, AOSP main frameworks/base ZramWriteback, Linux zram docs, Perfetto memory docs, Android Developers ApplicationExitInfo / 16KB page size docs, arXiv 2502.12826"
confidence: medium
sources:
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/ZramWriteback.java"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "https://docs.kernel.org/admin-guide/blockdev/zram.html"
  - type: official
    path: "https://perfetto.dev/docs/case-studies/memory"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/memory-counters"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/lmk"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: paper
    path: "https://arxiv.org/abs/2502.12826"
  - type: obsidian
    path: "DeepResearch/PSI 驱动的 Android LMKD 进程杀机制 — 源码级深度调研.md"
  - type: obsidian
    path: "DeepResearch/2026-05-09-mglru-vs-traditional-lru-lock-contention.md"
tags: [memory, zram, swap, lmkd, relaunch, performance]
related_chapters: ["4.2", "4.4", "8.2", "10.1", "15.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "研究素材/官方文档/AOSP结构"
---

# 4.12 ZRAM 压缩交换与应用重启延迟

<!-- outline-start -->
## 要点

### 🔹 ZRAM 在 Android 内存压力中的位置
说明 ZRAM 处理的是匿名页压缩交换，和 page cache 回收、LMKD 杀进程不是同一层动作。

### 🔹 kswapd、direct reclaim、LMKD 的分工边界
区分后台回收、同步回收、进程淘汰三类路径，避免把低内存卡顿全部归因到 App 主线程。

### 🔹 应用重启延迟为什么受 swap-in 影响
从后台保活、匿名页换入、页面触碰顺序解释 relaunch 比冷启动和热启动都更难定位的原因。

### 🔹 热数据、冷数据与压缩块大小取舍
整理热感知压缩交换的研究结论，说明解压速度、压缩率、CPU 占用之间的取舍。

### 🔹 Perfetto 与 /proc 指标观测路径
列出 `kswapd`、PSI、major fault、RSS/swap、LMKD event、ApplicationExitInfo 的交叉验证入口。

### 🔹 Android 版本演进：MGLRU、ZRAM recompression、16KB page
跟踪内核和 Android 版本中与内存回收、压缩交换、页大小相关的行为变化。

### 🔹 App 端可做与不可做的边界
说明 App 能通过内存预算、缓存释放、进程拆分降低压力，但不能直接控制系统 swap 策略。

## 扩展

### 🔸 Ariadne 论文与热感知压缩交换
基于 HPCA 2025 / arXiv 2502.12826 梳理 hotness-aware、size-adaptive、proactive decompression 三个方向。

### 🔸 低内存设备与 Android Go 策略
补充低内存设备上的内存预算、后台保活和启动体验差异。

### 🔸 与 ApplicationExitInfo / LMK 归因的交叉验证
把 relaunch 延迟、LMK 退出原因、RSS 口径和线上上报串起来。

<!-- outline-end -->

## ZRAM 解决的是匿名页压力，不等于 LMKD

ZRAM 是内存压力下的缓冲层。它把暂时不用的匿名页压缩后放进 RAM 中的块设备，给系统多留一点时间回收 page cache、等待前台负载结束，或者让后台进程继续活着。它不负责决定杀谁，也不负责判断哪个 App 更不重要；进程淘汰仍由 `lmkd` 结合进程优先级、PSI、swap 利用率、文件页抖动等信号完成。详见 4.4 节。 [已验证: 官方文档, source.android.com/docs/core/perf/lmkd]

内核视角下，ZRAM 主要处理的是匿名页。文件页干净时可以直接丢掉，需要时再从原文件读回；匿名页没有稳定文件后备，不能像干净文件页那样丢弃。Perfetto 的内存案例文档把 dirty page、swapped page、not present page 分开解释：Android 上 dirty page 即使被压进 ZRAM，仍会占用系统内存预算，只是占用形态从原始页变成压缩对象。 [已验证: 官方文档, perfetto.dev/docs/case-studies/memory]

这也是排查 relaunch 延迟时容易误判的地方：看到应用没有被杀，不代表回前台路径就是热启动；看到 `lmkd` 没有 kill event，也不代表内存压力没有影响用户。进程还在，但一批匿名页已经被换出，下一次回前台触碰这些页时，内核需要把压缩对象解压并重新映射到进程地址空间。

## 三条路径：kswapd、direct reclaim、LMKD

内存压力到来后，系统通常沿三类路径释放空间。

- `kswapd`: 后台回收线程，水位低于阈值后开始扫描 LRU，优先尝试把系统拉回较安全的空闲页范围。它运行在内核线程里，App 主线程未必直接阻塞，但 CPU 时间、内存带宽和锁竞争会影响前台任务。
- direct reclaim: 分配路径同步回收。某个线程申请内存时发现水位不足，会在自己的调用路径上进入回收或压缩。它更接近用户可感知卡顿，因为阻塞发生在发起分配的线程上。
- `lmkd`: 用户态低内存守护进程。Android 10 之后优先使用 PSI monitor 判断任务因内存短缺而延迟的时间，再结合 swap、watermark、thrashing 等指标选择进程。AOSP `lmkd.cpp` 中保留了 `ro.lmk.psi_partial_stall_ms`、`ro.lmk.psi_complete_stall_ms`、`ro.lmk.swap_free_low_percentage`、`ro.lmk.thrashing_limit`、`ro.lmk.swap_util_max` 等参数。 [已验证: AOSP main, system/memory/lmkd/lmkd.cpp]

`lmkd` 的源码里还有一个容易被忽略的判断：ZRAM 场景下不能只看 `SwapFree`。`get_free_swap()` 会在 `free_swap` 与 `easy_available * swap_compression_ratio` 之间取较小值，因为 ZRAM 的 swap 空间来自可用内存或可回收内存，并不是一块独立磁盘空间。 [已验证: AOSP main, system/memory/lmkd/lmkd.cpp]

排查时要把三条路径分开看。`kswapd` 活跃说明系统在后台回收；direct reclaim 说明某条业务路径已经被迫帮系统回收；LMKD 事件说明系统选择用进程淘汰止损。三者可以连续发生，也可能只出现其中一种。

## relaunch 慢，常见原因是换入顺序和工作集不匹配

Android 启动分析通常分冷启动、温启动、热启动，详见 8.2 节。ZRAM 相关的 relaunch 不完全落在这三个分类里：进程还在、Activity record 可能还在、Java 对象也可能还在，但其中一部分匿名页被压缩交换。用户点回应用后，路径看起来像热启动，成本却接近一段受 swap-in 影响的恢复过程。

这类延迟有三个特征。

- 它不一定表现为一段长 Java 方法。主线程可能卡在页面触碰后的 major fault、swap fault、binder 回复等待或 RenderThread 资源恢复上，Java slice 里只留下碎片化耗时。
- 它依赖页面触碰顺序。同样的 RSS，被压出的页面如果正好是首屏状态、图片缓存索引、布局中间结构，回前台就会集中换入；如果压出的是短期不用的后台数据，用户可能无感。
- 它受系统同一时刻的 CPU 和 I/O 状态影响。ZRAM 解压需要 CPU，writeback 场景还会碰到后备设备 I/O；低端设备上，这部分成本更容易和前台渲染抢资源。

Ariadne 论文把这个问题描述得很直接：现有 ZRAM 不区分热匿名页和冷匿名页，也不利用 relaunch 期间的数据局部性；在 Pixel 7 / Android 14 实验中，热感知组织、大小自适应压缩、主动解压三项结合后，相比普通 ZRAM 平均降低 50% relaunch latency，并减少 15% 压缩/解压 CPU 使用。论文结论不能直接当作 AOSP 已采用能力，只能作为解释 relaunch 症状的研究证据。 [已验证: 论文, arXiv:2502.12826]

## 热数据、冷数据与压缩块大小

ZRAM 的取舍不是“压缩越强越好”。压缩率高可以容纳更多匿名页，减少 LMKD 的触发概率；解压快可以降低回前台的长尾；CPU 占用低可以减少和前台线程抢核。三者通常不能同时拉满。

Linux zram 文档已经提供了两个方向的机制：`CONFIG_ZRAM_WRITEBACK` 允许把 idle 或 incompressible page 写回 backing device；`CONFIG_ZRAM_MULTI_COMP` 允许用多个压缩算法重压部分页面，冷页可以换更高压缩率，热页保留更快解压路径。AOSP `ZramWriteback` 服务则通过 `ro.zram.mark_idle_delay_mins`、`ro.zram.first_wb_delay_mins`、`ro.zram.periodic_wb_delay_hours` 调度 idle 标记和 writeback job。 [已验证: 官方文档, docs.kernel.org/admin-guide/blockdev/zram.html] [已验证: AOSP main, frameworks/base/services/core/java/com/android/server/ZramWriteback.java]

Ariadne 的贡献在于把这套取舍绑定到 relaunch：热数据使用较小压缩块，降低换入时的解压成本；冷数据使用较大压缩块，换更高压缩率；预测下一批将被触碰的数据并提前解压。这里的边界也很清楚：这是研究系统，不是 Android SDK 能力。App 不能向系统声明某个匿名页是 relaunch 热页，也不能直接控制 ZRAM 的算法选择。 [待验证: AOSP 未见 Ariadne 合入证据]

## 观测路径：用多个信号拼同一件事

单看一个指标很容易误判。`VmSwap` 高不代表用户一定卡，`kswapd` 活跃也不代表卡顿来自系统，`REASON_LOW_MEMORY` 更只能证明上次进程死亡与低内存有关。可靠做法是把时间线、进程状态和系统压力放到同一个窗口里。

Perfetto 配置的用途是同时采集进程 RSS 变化、内存事件直方图和系统 meminfo/vmstat 计数。排查 relaunch 慢时，重点看 `mem.mm.maj_flt`、`mem.mm.swp_flt`、`mem.mm.reclaim`、`kmem/rss_stat` 与目标进程主线程/RenderThread 的时间关系。

```protobuf
buffers: { size_kb: 8960 fill_policy: DISCARD }
buffers: { size_kb: 1280 fill_policy: DISCARD }

data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "kmem/rss_stat"
      ftrace_events: "mm_event/mm_event_record"
      ftrace_events: "sched/sched_switch"
    }
  }
}

data_sources: {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
      proc_stats_poll_ms: 1000
    }
  }
}

data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms: 1000
      vmstat_period_ms: 1000
    }
  }
}

duration_ms: 30000
```

Perfetto 文档说明，`rss_stat` 是事件驱动的 RSS 变化记录，能捕捉很短的内存峰值；`mm_event` 会记录 minor fault、major fault、swapcache fault、read I/O fault、compaction、reclaim 等事件的次数和延迟统计。 [已验证: 官方文档, perfetto.dev/docs/data-sources/memory-counters]

设备上还要补 `/proc` 和系统 API 口径。命令的用途是把 trace 里看到的时间点映射到系统压力状态和进程上次退出原因。

```bash
adb shell cat /proc/pressure/memory
adb shell cat /proc/meminfo | grep -E 'MemAvailable|SwapTotal|SwapFree|SwapCached|Zram|Anon|File'
adb shell cat /proc/vmstat | grep -E 'pgmajfault|pswpin|pswpout|pgscan_kswapd|workingset_refault'
adb shell dumpsys activity exit-info <package-name>
```

`ApplicationExitInfo` 从 API 30 开始提供进程死亡原因、`getPss()`、`getRss()`、`getTimestamp()` 等信息。`REASON_LOW_MEMORY` 表示进程被系统低内存杀死；不是所有设备都能报告这个 reason，不支持时可能返回 `REASON_SIGNALED` 且 status 为 `SIGKILL`，需要用 `ActivityManager.isLowMemoryKillReportSupported()` 判断。 [已验证: 官方文档, developer.android.com/reference/android/app/ApplicationExitInfo]

## 版本演进：MGLRU、ZRAM recompression、16KB page

4.2 节已经解释了 Linux 页面回收。放到 ZRAM relaunch 这个问题里，版本差异主要看三类变化。

- MGLRU 改变冷热页识别方式。传统 active/inactive LRU 更依赖链表移动和扫描；MGLRU 用 generation 表示访问年龄，减少部分锁内操作，也让回收选择更接近时间局部性。Android 设备是否启用、内核版本和厂商参数差异较大，不能只按 Android API level 判断。 [来源: DeepResearch/2026-05-09-mglru-vs-traditional-lru-lock-contention.md]
- ZRAM recompression / writeback 给系统更多分层空间。冷页可以重压，idle 或 incompressible page 可以写回后备设备。收益取决于设备是否配置 backing device、压缩算法、低电量策略和后台负载。
- 16KB page 会改变 page fault 粒度、TLB 行为和内存浪费边界。Android Developers 文档给出的初始测试结果是：16KB 设备在内存压力下 app launch 平均降低 3.16%，部分应用最高 30%；同时平均多用一些内存。这个数据不能直接推出“relaunch 一定变快”，但说明页大小已经进入启动和内存压力的共同变量。 [已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

这些变化会互相影响。更大的页可能减少 TLB miss，也可能让小对象密集的匿名页面对更粗的换入粒度；MGLRU 能改善回收选择，但 App 热页是否被保留仍取决于系统全局压力；ZRAM recompression 降低空间压力时，也可能把冷页解压成本推到更晚的 relaunch 窗口。

## App 端能做什么，不能做什么

App 不能控制 ZRAM，不应把“关闭 swap”或“调系统属性”写进优化方案。App 能做的是减少自己制造的匿名页压力，并在进入后台时主动降低被系统换出或淘汰后的恢复成本。

- 建立前后台内存预算。用 10.1 节的方法分清 Java heap、native heap、graphics、mmap file、匿名 mmap；只盯 PSS 不够，relaunch 相关问题更关心匿名 dirty 与 swap。
- 响应 `onTrimMemory()`。`TRIM_MEMORY_UI_HIDDEN` 是进入后台后释放首选缓存的时机，图片解码缓存、临时 JSON、可重建索引、预加载列表数据都应有清晰的释放策略。开发者文档也建议用 trim callback 降低后台后被 LMK 的概率。 [已验证: 官方文档, developer.android.com/topic/performance/vitals/lmk]
- 把首屏恢复路径做小。回前台最早触碰的数据越多，越容易把 swap-in 成本集中到用户等待窗口。首屏状态、导航栈、必要业务对象要小；可延后的缓存恢复放到首帧之后。
- 进程拆分要看恢复成本。把后台服务、推送、播放器拆到独立进程可以隔离部分内存压力，但也会增加总 RSS、Binder 交互和进程调度成本。拆分前后要用同一套 trace 比较。
- 线上归因不要只记 `REASON_LOW_MEMORY`。建议同时记录 relaunch TTID/TTFD、上次 `ApplicationExitInfo`、前后台停留时间、设备 RAM 档位、进程内存快照和是否走冷启动。没有这些上下文，线上只能知道“发生过低内存”，很难定位到 ZRAM 换入。

本小节的结论可以压成一句：ZRAM 减少的是进程被杀的概率，代价可能转移到回前台时的解压、换入和重新触碰页面。把这部分成本从启动耗时里拆出来，才能判断问题该归到 App 内存预算、系统内存压力，还是设备级 ZRAM 策略。


<!-- AIW-源码调研-2026-07-14:Android 17 ZRAM 多后端 + recompression 架构（Kernel 6.18） -->

## Android 17 ZRAM 多后端 + recompression 架构（Kernel 6.18 源码补全）

> 调研日期：2026-07-14  
> 源码基准：`android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6`  
> 调研依据：`DeepResearch/2026-07-14-android17-zram-psi-pressure-management.md`

**目录迁移**：Android 17 内核（6.18）把 ZRAM 从历史位置 `mm/zram.c` 拆为 `drivers/block/zram/` 子目录，并按压缩算法分离 backend：

```
drivers/block/zram/
├── zram_drv.c / zram_drv.h / zram_ioctl.c
├── zcomp.c / zcomp.h        # 压缩抽象层
├── backend_lzo.c / backend_lzorle.c
├── backend_lz4.c / backend_lz4hc.c
├── backend_zstd.c / backend_deflate.c
└── backend_842.c            # Power 架构
```

`zcomp.c` 通过 `backends[]` 注册表 + `IS_ENABLED(CONFIG_ZRAM_BACKEND_*)` 控制编译期可见性，所有 backend 实现统一 `zcomp_ops` 接口（`create_ctx / destroy_ctx / compress / decompress`）。

**多 compressor 设计**（`zram_drv.h`）：

```c
#ifdef CONFIG_ZRAM_MULTI_COMP
#define ZRAM_PRIMARY_COMP     0U
#define ZRAM_SECONDARY_COMP   1U
#define ZRAM_MAX_COMPS        4U   // 最多 4 个 compressor
#else
#define ZRAM_PRIMARY_COMP     0U
#define ZRAM_SECONDARY_COMP   0U
#define ZRAM_MAX_COMPS        1U
#endif
```

每个 slot 的 `attr.flags` 用 `ZRAM_COMP_PRIORITY_BIT1 / BIT2` 两位记录「该 slot 当前由 primary 还是 secondary 压缩」。recompression 阶段（`comp_algorithm_recomp_store`）依据优先级判断升档：

```c
// zram_drv.c（约 2644-2653 行）
if (get_slot_comp_priority(zram, index) + 1 >= prio_max)
    goto next;   // 已达最高优先级，跳过
```

**huge class 跳过压缩**（`zram_drv.c` 2517、2558 行）：当 `comp_len >= zs_huge_class_size(zram->mem_pool)` 时直接打 `ZRAM_HUGE` 标记并可选走 `ZRAM_WRITEBACK` 把冷大页踢出 zram，省 zsmalloc 内存。

**post-processing 异步流水线**（`zram_drv.c` 1100-1300 行附近）：

- `select_pp_slot()` 从红黑树选 idle / huge slot
- `zram_prefetch_from_bdev()` 发起 `REQ_OP_READ` bio
- `zram_prefetch_read_endio()` 在 `bi_end_io` 回调 `INIT_WORK(&req->work, zram_deferred_prefetch)` 后 `queue_work(system_highpri_wq, ...)`
- `zram_deferred_prefetch()` 重新 `slot_lock()` + 二次校验 `ZRAM_WB` flag 后调 `zram_populate_table()`

要点：prefetch 在 bdev IO 完成前 slot 锁可释放，避免与 free 路径 race。

**Kconfig 默认值**：`ZRAM_DEF_COMP_LZORLE`（`drivers/block/zram/Kconfig`）。`ZRAM_BACKEND_FORCE_LZO` 提供兜底：当所有新 backend 关闭时强制开启 LZO，兼容老 GKI 编译。

[适用版本: Android 17 (API 37) / Kernel 6.18（`android17-6.18-2026-06_r6`）]

