---
title: 低内存对系统性能的影响
chapter: '10.2'
section: '10.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: AOSP android-17.0.0_r1; Android common kernel android17-6.18-2026-06_r6
confidence: high
sources:
- type: blog
  path: Personal-Knowlodge/source/2026-03-08_wechat_kswapd介绍.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_Linux内存变低会发生什么问题.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_Android帝国之进程杀手--lmkd.md
- type: research
  path: intake/research-feeds/2026-04-02-11-ch04-zram-multialgo-mglru-2025.md
- type: aosp
  path: platform/system/memory/lmkd/lmkd.cpp@android-17.0.0_r1
- type: aosp
  path: platform/system/memory/libmeminfo/libmemevents@android-17.0.0_r1
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/LowMemDetector.java@android-17.0.0_r1
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java@android-17.0.0_r1
- type: aosp
  path: platform/frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java@android-17.0.0_r1
- type: kernel
  path: kernel/common/mm/page_alloc.c@android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/mm/vmscan.c@android17-6.18-2026-06_r6
- type: kernel
  path: kernel/common/include/trace/events/vmscan.h@android17-6.18-2026-06_r6
- type: official
  path: https://source.android.com/docs/core/perf/lmkd
- type: official
  path: https://docs.kernel.org/accounting/psi.html
- type: official
  path: https://perfetto.dev/docs/data-sources/memory-counters
tags:
- low-memory
- kswapd
- direct-reclaim
- lmkd
- GC
- memory-pressure
- PSI
- ZRAM
- Perfetto
- MGLRU
- cgroup
- mm-events
- vmscan
- oom-score-adj
related_chapters:
- '4.1'
- '4.3'
- '4.4'
- '4.6'
- '10.1'
- '10.3'
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
task2b_state: fixed
---

# 低内存对系统性能的影响

> 适用范围：Android 10（API 29）至 Android 17（API 37）。平台源码按 `android-17.0.0_r1` 核对；回收、水位线、PSI、ZRAM 与页规整的内核源码按 `android17-6.18-2026-06_r6` 核对。

低内存带来的性能损失没有固定顺序。系统可能回收 clean file page（未修改的文件页）、把匿名页换入 ZRAM（内存中的压缩交换设备）、让分配线程进入 direct reclaim（同步直接回收）、终止 cached process（缓存进程），也可能由 Android 17 Memory Limiter 约束异常进程。不同路径消耗 CPU、I/O、内存带宽或启动时间，必须在同一段 Trace 中核对事件先后和因果关系。

## 1. 从分配失败到回收

### 1.1 Zone 水位线与 kswapd

Linux 将物理内存划分为多个 zone（内存区域），并为每个 zone 维护 `min`、`low`、`high` 等 watermark（水位阈值）。这些阈值参与分配快速路径、后台回收唤醒、保留页和高阶分配判断。常见行为是空闲页接近低水位时，唤醒对应 NUMA node（内存节点）的 `kswapd` 后台回收线程，由 `mm/vmscan.c` 的 `balance_pgdat()` 扫描和回收，随后尝试进入休眠。

这条规则有多个条件：

- 分配的 order（连续页块阶数）、GFP flags（内核分配约束）、允许使用的 zone 与保留页不同。
- per-CPU page list（每 CPU 页缓存）、watermark boost（水位临时增量）、碎片和 compaction（内存规整）会改变分配慢路径。
- `kswapd0` 短暂运行属于正常回收；持续扫描、扫描收益低或频繁 wake/sleep 才值得追查。

Android 17 的 6.18 内核锚点：

- `mm/page_alloc.c`：watermark 检查、分配慢路径与 `wakeup_kswapd()`。
- `mm/vmscan.c`：`balance_pgdat()`、`shrink_node()` 与 direct reclaim。
- `include/trace/events/vmscan.h`：kswapd、direct reclaim 和 LRU 扫描 tracepoint。

### 1.2 Direct reclaim

分配快速路径失败，且请求允许 `__GFP_DIRECT_RECLAIM` 时，当前分配线程可能同步进入回收。空闲页低于 `min` 并不会无条件触发这条路径；分配 order、zone、reserve（保留页）、memcg（内存控制组）与 GFP 语义都会参与选择。

Direct reclaim 会占用当前线程的执行时间。线程可能在 CPU 上扫描页面，也可能因 throttle（限速）、swap 或 I/O 等待进入不可中断睡眠。看到主线程处于 `D` 状态时，仍要用 `sched_switch`、blocked reason（阻塞原因）或内核调用栈证明它在等待什么，不能只凭线程状态归因到内存回收。

### 1.3 回收成本来自哪里

不同页面的代价不同：

| 被处理的内存 | 回收动作 | 后续成本 |
| --- | --- | --- |
| clean file page | 丢弃页 | 再访问时可能 refault（页面被回收后很快再次访问）并读取文件 |
| dirty file page（已修改的文件页） | 回写后回收 | 写入延迟与存储竞争 |
| anonymous page（匿名页） | 换出到 ZRAM 或其他 swap | 压缩 CPU、swap-in（换入）解压与延迟 |
| slab / 内核缓存 | shrinker（内核缓存回收器）回收 | 由具体子系统决定 |
| 高阶物理页需求 | compaction / retry（规整后重试） | 页迁移、扫描与分配延迟 |

Direct reclaim 不一定产生存储 I/O。clean file page 可以直接丢弃，匿名页在常见 Android 配置中可进入 ZRAM；设备若启用 ZRAM writeback（回写），部分数据也可能进入 backing device（后备存储设备）。分析时应把 vmscan、block I/O、ZRAM、refault 和线程状态放在一起。

## 2. PSI 怎样描述系统停顿

Pressure Stall Information（PSI，资源压力停顿信息）统计任务因 CPU、memory 或 I/O 资源不足而停顿的时间。memory PSI 中：

- `some`：时间窗内至少有一个非 idle（非空闲）任务因内存压力停顿。
- `full`：时间窗内所有非 idle 任务同时因内存压力停顿。
- `avg10`、`avg60`、`avg300`：滚动时间窗平均值。
- `total`：累计停顿时间，单位为微秒。

`full` 为零不能证明系统没有内存压力；只要仍有其他任务能运行，压力可能只反映在 `some`。PSI 也不会指出哪一页、哪个进程或哪条分配路径造成停顿，还要结合回收与进程数据一起分析。

下面的命令用于查看当前 PSI、vmstat、ZRAM 与进程退出记录：

```bash
adb shell cat /proc/pressure/memory
adb shell cat /proc/vmstat
adb shell cat /proc/swaps
adb shell dumpsys activity exit-info com.example.app
```

`/proc/pressure/memory` 是系统级累计与平均信息，`vmstat` 需要用两个时间点做差分。要确认进程死亡原因，应查看退出记录，不能用当前 PSI 值反推过去某次退出。

## 3. Android 17 的两个 PSI 消费者

### 3.1 lmkd

Android 17 的 lmkd（low memory killer daemon，低内存终止守护进程）启动时初始化 PSI monitors（压力事件监听器）。新的默认策略不使用 LOW 档，把 MEDIUM 映射到可配置的 partial stall（部分任务停顿），把 CRITICAL 映射到可配置的 complete stall（所有非空闲任务停顿）。收到 PSI 事件后，lmkd 还会读取 zone watermark、swap、working-set refault / thrashing（工作集页面频繁换入造成的抖动）、进程 `oom_score_adj`（进程受保护级别）与 footprint（内存占用），再决定是否选择进程。

`use_minfree_levels` 在 Android 17 影响 kill strategy（终止进程策略），不能解释成旧版 `ro.lmk.use_psi=false`。Android 17 源码已经没有该 PSI 开关的旧用法。

lmkd 选择目标时应以事件证据为准：

- 被杀 PID、UID 与进程名。
- 目标 `oom_score_adj` 与本轮 `min_oom_score`（本轮允许选择的最低 OOM 分值）。
- kill reason（终止原因）、thrashing 数据。
- RSS、anon RSS、swap、DMA-BUF PSS/RSS。

不要把某个固定 adj 数写成所有设备的杀进程边界。进程状态、设备属性、OEM 策略和当时压力都会改变候选范围。

Android 17 在成功 kill 后调用 `ATRACE_INSTANT_FOR_TRACK()`，description 格式为 `lmk,pid,reason,oomadj,min_oom_score,max_thrashing`；同一动作也写入 `lowmemorykiller` 日志与统计。现代设备应优先读取这个 userspace instant（用户空间瞬时事件）、logcat/statsd 和 `ApplicationExitInfo`，不要依赖可能不存在的 legacy（旧式）`lowmemorykiller/lowmemory_kill` 内核事件。

### 3.2 system_server 的 LowMemDetector

`LowMemDetector` 是 system_server 内部的另一条 PSI 路径。Android 17 的 Native 实现注册三个 monitor：

| 内部等级 | PSI 类型 | AOSP Android 17 窗口与 stall |
| --- | --- | --- |
| LOW | `PSI_SOME` | 1 s 窗口内 15 ms |
| MEDIUM | `PSI_FULL` | 1 s 窗口内 30 ms |
| HIGH | `PSI_FULL` | 1 s 窗口内 50 ms |

这些是 `android-17.0.0_r1` 的 Framework 常量，不能直接作为所有 OEM 分支的性能阈值。Java 线程通过 epoll（事件等待机制）等待等级变化，CRITICAL 区间会留下 `criticalLowMemory` trace slice（轨迹片段）。该状态供 ActivityManager 内部的 memory factor（内存压力等级）、进程统计和相关调整使用。

LowMemDetector 与 lmkd 读取同一个 PSI 子系统，但监听配置和动作不同。前者属于 system_server 状态管理，后者负责内存压力下的进程选择与终止；出现两个监听 fd（文件描述符）不表示 PSI 被重复计算。

## 4. lmkd kill 怎样转化为用户性能损失

cached process 被终止后，物理内存得到回收。用户再次访问该 App 时，系统需要创建进程、加载代码与资源、初始化 Application / ContentProvider、恢复 Activity 和业务状态。代价取决于包体、I/O、初始化工作、编译状态和系统压力，不能用一个固定毫秒数概括。

评估低内存的产品影响时，建议关联：

1. lmkd kill 时间与原因。
2. 用户返回该 App 的时间间隔。
3. warm/hot resume（温启动或热恢复）变成 cold start（冷启动）的比例。
4. 冷启动 CPU、I/O、首帧与状态恢复。
5. 同一进程是否在短时间内反复启动和退出。

`ApplicationExitInfo.REASON_LOW_MEMORY` 可帮助识别低内存退出。Android 17 Memory Limiter 的退出使用 `REASON_OTHER`，description 含 `MemoryLimiter:AnonSwap`，不能混入普通 lmkd kill 统计。

## 5. 全局低内存与 ART GC 的边界

ART GC 的频率主要由 App 的 allocation rate（分配速率）、live set（仍存活对象集合）、heap target（堆目标大小）、collector（垃圾收集器）和进程状态决定。公开规则中没有“全局 PSI 升高后，前台 App 直接切换到某种更重 GC”这一机制。以下现象可能同时出现，但需要分别证明：

- App 自身分配率高、live heap 接近目标，GC slice（GC 轨迹片段）变密。
- kswapd、ZRAM 或 compaction 消耗 CPU，GC 并发线程获得的 CPU 时间减少。
- 分配线程进入 direct reclaim，allocation stall 与 GC pause 出现在相邻时间窗。
- cached process 被 Framework compact（压减进程驻留内存）或 freeze（冻结调度），属于进程驻留优化，不等同于 ART 的 Java heap GC。

60 Hz 一帧约 16.67 ms，120 Hz 一帧约 8.33 ms。刷新率越高，可供 GC pause、调度延迟和回收干扰使用的余量越小。仍应按实际 FrameTimeline（帧时间线）、GC slice 和调度时间判断掉帧，不能给所有设备设置通用 GC 毫秒阈值。

如果 GC 密度上升而 PSI、vmscan 和 kswapd 平稳，问题更可能来自 App allocation churn。若 PSI 和 direct reclaim 上升而 GC 不变，瓶颈可能位于系统回收或 I/O。两组信号重叠时，再检查 CPU 竞争和分配线程调用栈。

## 6. Android 17 中 `memevents` 与旧 `mm_events`

两个名称容易混淆：

- `libmemevents`：Android 17 的 BPF（内核可编程观测机制）memory event 库。lmkd 用 `MemEventListener` 订阅 direct reclaim begin/end、kswapd wake/sleep、vendor kill 和 zone info 更新；初始化失败时回退到 vmstat（内核虚拟内存统计）。
- Perfetto `mm_events` service：旧版本中用于常驻启用 `kmem_activity` trigger 的脚本和 probe（探针）。

`android-17.0.0_r1` 的 Perfetto 源码已经没有 `tools/mm_events`、`kmem_activity_trigger` 和对应测试配置。Android 17 排查不能假设 `persist.mm_events.enabled`、`/vendor/etc/mm_events.cfg` 或 `mem.mm_events` SQL view（查询视图）存在。OEM 或旧系统可能保留自己的版本，使用前要从设备镜像和 trace schema（轨迹数据结构）核验。

Android 17 的通用证据仍是 vmscan / compaction ftrace（内核函数跟踪事件）、PSI、vmstat、lmkd userspace event、进程统计和 App trace。

## 7. 用 Perfetto 还原压力时间窗

### 7.1 需要观察的事件

| 信号 | 能回答的问题 |
| --- | --- |
| `mm_vmscan_kswapd_wake/sleep` | 后台回收何时开始和结束 |
| `mm_vmscan_direct_reclaim_begin/end` | 哪个线程同步回收、持续多久 |
| `mm_vmscan_lru_shrink_inactive` | 扫描与回收的规模 |
| `mm_compaction_begin/end` | 页规整窗口与连续页块 order |
| PSI some/full | 系统停顿程度 |
| sched state / blocked reason | 目标线程正在运行、等待 CPU 或处于 D 状态 |
| ART GC slice | App GC 类型与时序 |
| lmkd instant / log | 谁被 kill、原因和候选边界 |
| process stats | 进程创建、退出与 RSS 变化 |

下面的配置可作为 Android 17 低内存复现的起始模板。buffer（轨迹缓冲区）和时长属于采集参数，应按复现窗口调整：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 30000

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
      ftrace_events: "vmscan/mm_vmscan_lru_shrink_inactive"
      ftrace_events: "compaction/mm_compaction_begin"
      ftrace_events: "compaction/mm_compaction_end"
      atrace_categories: "am"
      atrace_categories: "dalvik"
      atrace_categories: "memreclaim"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
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

Android 17 的 `atrace.cpp` 明确定义了 `memreclaim` category（轨迹类别），它启用 direct reclaim、kswapd 和可选 lowmemorykiller 事件组。配置同时显式列出 vmscan 事件，便于在设备裁剪类别时核对。录制前应查看 tracefs（内核跟踪文件系统）中的事件是否存在；缺少可选事件时按设备能力删减。

### 7.2 阅读顺序

1. 在卡顿、启动或 kill 附近划定时间窗。
2. 看 PSI some/full 与 vmstat 差分，确认是否有系统级停顿。
3. 看 kswapd 与 direct reclaim，区分后台回收和分配线程同步回收。
4. 看 sched state、block I/O（块设备 I/O）与 ZRAM，识别 CPU 扫描、压缩、swap 或存储等待。
5. 看 GC slice 与 FrameTimeline，确认 App 自身分配是否叠加影响。
6. 看 lmkd instant、日志和进程生命周期，确认回收后的启动代价。

“kswapd Running + 主线程 D 状态”仍不足以证明主线程因内存回收而阻塞。需要 direct reclaim event 或调用栈把主线程与回收关联，也要排除 Binder、文件系统、GPU fence（GPU 同步栅栏）和其他不可中断等待。

## 8. 系统侧调优的边界

### 8.1 ZRAM

ZRAM 用 RAM 保存压缩后的 swap page（交换页）。它提高匿名页的存储密度，也消耗物理内存和压缩/解压 CPU；部分设备还启用 writeback 或 recompression（重新压缩）。不存在跨设备通用的 ZRAM 大小、压缩比、算法或 swappiness（交换倾向参数）值。

下面的节点用于保存设备配置与运行统计：

```bash
adb shell cat /proc/swaps
adb shell cat /sys/block/zram0/mm_stat
adb shell cat /sys/block/zram0/comp_algorithm
adb shell cat /sys/block/zram0/recomp_algorithm
adb shell cat /proc/sys/vm/swappiness
adb shell cat /proc/sys/vm/page-cluster
```

节点是否存在取决于内核配置。`mm_stat` 可查看原始数据、压缩后数据、内存总量和页面状态；算法列表用方括号标出当前选择。`page-cluster` 控制一次换入时预读的相邻页数量；在 16 KB 设备上，同一个值会覆盖更大的字节范围。是否调整仍要看 swap-in 命中、解压 CPU、PSI 和 App 切换时延。

评估 ZRAM 改动要同时比较：

- `pswpin` / `pswpout`（累计换入/换出页数）、ZRAM 占用和压缩效率。
- memory PSI、direct reclaim 和 kswapd 时间。
- swap-in 后的启动、页面恢复和交互延迟。
- 压缩线程 CPU 与功耗。
- lmkd kill、refault 和 cached App 存活。

只提高压缩比可能增加 CPU；只增加 ZRAM 容量可能挤占未压缩内存。参数应按 SoC、RAM 档位和负载测试。

### 8.2 MGLRU

Multi-Gen LRU（MGLRU，多代最近最少使用）用 generation（代）记录页面访问热度，回收时优先选择较老的一代。Android 17 的 6.18 内核包含该路径，但设备是否启用要读取 `/sys/kernel/mm/lru_gen/enabled` 并核对配置。

评估 MGLRU 不能只看开关。需要比较 refault、scan/steal（扫描页数/成功回收页数）、direct reclaim、PSI、swap 与冷启动回访。generation 的 bitmask（位掩码）受内核版本和配置影响，不应把某个十六进制值当成永久常量。

### 8.3 Cached App Optimizer

Android 17 的 `CachedAppOptimizer` 同时包含 cached app compaction（缓存进程内存压减）与 freezer（进程冻结）逻辑。compaction profile 有 `SOME`（file）、`ANON` 和 `FULL`（file + anon），系统会根据 RSS、时间、swap 余量和配置决定是否执行或降级。

这条路径通过 `madvise` / memcg compaction（控制组内存回收）降低 cached process 的驻留成本，不会删除 App 的业务对象，也不能修复泄漏。Freezer 暂停 cached process 的调度，解冻时还要处理 Binder、文件锁和任务积压；它与物理页规整、ART GC 属于不同机制。

### 8.4 cgroup、Task Profiles 与 Android 17 Memory Limiter

Android 的 cgroup（控制组）抽象和 Task Profiles（任务资源配置）负责进程分组与资源策略。PSI 负责度量 stall（资源停顿），lmkd 负责在压力下选择进程。这三项职责不能写成一个开关。

Android 17 还在部分设备启用 App Memory Limiter。`MemoryLimiter.java` 为 visible / not-visible 状态配置 cgroup `memory.high` 与 `memory.swap.high`；越限后可采集诊断并终止目标进程。它的退出记录是 `REASON_OTHER` + `MemoryLimiter:AnonSwap`，与 lmkd 的系统压力 kill 分开统计。

下面的命令用于检查设备是否支持该机制，并在测试设备验证受限场景：

```bash
adb shell am memory-limiter status
adb shell am memory-limiter manual <pid> <limit-in-mb>
adb shell am memory-limiter manual <pid> none
```

命令在未启用 Memory Limiter 的设备上没有效果。手动限制适合测试状态保存与恢复，不能由测试值推导产品设备的系统阈值。

### 8.5 `onTrimMemory()`

Android 17 App 侧稳定可用的状态提示包括 `TRIM_MEMORY_UI_HIDDEN` 与 `TRIM_MEMORY_BACKGROUND`。`TRIM_MEMORY_RUNNING_*`、`MODERATE`、`COMPLETE` 自 API 34 起不再投递，并在 API 35 标为 deprecated。

App 应在 UI 隐藏和进入后台状态时缩减可重新生成的缓存、停止预取并关闭界面资源。该回调不提供 PSI 数值，也不能代替 hard memory budget（内存硬上限）。主动 `System.gc()` 无法释放仍被引用的对象，也会干扰正常调度。

## 9. App 与低 RAM 产品适配

`ActivityManager.isLowRamDevice()` 表示设备使用 low-RAM（低内存设备）产品配置，不能用“RAM 小于等于某个 GB 数”替代。`getMemoryClass()` 只描述 ART heap 的近似预算，也不等于进程 PSS 上限。

App 可以按产品档位调整：

- 图片解码尺寸、内存缓存与预取窗口。
- 列表、地图瓦片、消息和模型的内存页数。
- WebView、Codec、Camera、Surface 与后台进程的并发数量。
- 非必要 SDK 与进程的初始化时机。
- 冷启动状态恢复和 cached process 被 kill 后的数据加载。

Android Go Edition 是一组面向低内存设备的产品配置与系统应用策略，不能只按物理 RAM 判断。测试范围应覆盖真实 Go / low-RAM 设备、普通 4 KB 与 16 KB page size 设备，以及启用和未启用 Android 17 Memory Limiter 的产品。

## 10. 诊断表

| 现象 | 需要验证 | 常见方向 |
| --- | --- | --- |
| kswapd 活跃，direct reclaim 少 | 后台 scan/steal、refault、ZRAM CPU | 工作集、文件页、MGLRU、ZRAM |
| App 线程出现 direct reclaim | GFP 调用栈、持续时间、回收结果 | 减少峰值分配、预分配、系统余量 |
| memory PSI full 升高 | sched、I/O、vmscan、并发任务 | 系统级停顿来源 |
| lmkd kill 后冷启动增加 | kill reason、`oom_score_adj`、返回间隔 | 降低后台内存占用、状态恢复 |
| GC slice 变密，PSI 平稳 | allocation rate、live heap | App churn、对象生命周期 |
| PSI 与 GC 同时升高 | CPU 竞争、分配线程、FrameTimeline | App 分配与系统压力分别处理 |
| ZRAM 使用高且切回慢 | pswpin/out、解压 CPU、page-cluster | 容量、算法、预读与工作集 |
| Android 17 `MemoryLimiter:AnonSwap` | exit-info、anomaly profile（异常诊断数据）、进程状态 | 单进程预算、泄漏、恢复 |

## 版本边界

- Android 10 起，userspace lmkd 的 PSI 路径成为现代 Android 的主要实现方向。
- Android 14（API 34）起，App 不再收到旧的运行时压力 trim levels。
- Android 15（API 35）起，AOSP 支持 16 KB page size 设备；内存基线要按 page size 分组。
- Android 17（API 37）的 lmkd 直接初始化 PSI monitors，并优先使用 BPF `libmemevents` 观察回收事件，失败时回退到 vmstat。
- Android 17 在部分设备启用 App Memory Limiter；最高版本边界为 Android 17。
- 内核机制以 `android17-6.18-2026-06_r6` 的 vmscan、PSI、ZRAM、MGLRU 与 compaction 为准。

## 检查清单

- 是否把 kswapd、direct reclaim、PSI 与 lmkd 当作不同证据？
- D 状态（不可中断睡眠）是否有 blocked reason、调用栈或 direct reclaim event 支撑？
- clean file reclaim、ZRAM、dirty writeback 与 refault 是否分开？
- lmkd kill 是否记录 PID、adj、reason、RSS、swap 与 DMA-BUF？
- GC 变密是否有 App allocation rate 与 live heap 证据？
- 是否误用 Android 17 已删除的 Perfetto `mm_events` service？
- ZRAM 与 MGLRU 参数是否经过同设备 A/B 对照测试，而非套用固定值？
- cached app compaction、freezer、ART GC 与物理页 compaction 是否分开？
- Android 17 退出记录是否区分 lmkd 与 `MemoryLimiter:AnonSwap`？
- 低 RAM 档位是否来自产品配置和实机，而非固定 GB 线？

## 与其他章节的关系

- [4.1 Android 与 Linux 内存管理全景](../../part1-fundamentals/ch04-memory/01-android-linux-memory-overview.md)：进程内存口径，以及 watermark、reclaim、swap 与 compaction 等系统物理页机制。
- [§4.3 Low Memory Killer](../../part1-fundamentals/ch04-memory/03-lmkd-freezer-memory-pressure.md)：lmkd 选择策略与进程优先级。
- [§4.4 App 内存优化](../../part1-fundamentals/ch04-memory/04-app-memory-optimization.md)：App hard budget、trim 与资源生命周期。
- [10.1 App 内存分析与案例](01-app-memory-analysis-cases.md)：PSS、RSS、Graphics、heap 与退出信息。
- [§10.3 内存抖动与频繁 GC](03-memory-churn.md)：allocation rate、GC 与帧时间。

## 参考资料

- [AOSP `lmkd.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [AOSP `libmemevents`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/libmemevents/)
- [AOSP `LowMemDetector.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/LowMemDetector.java)
- [AOSP `LowMemDetector.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/jni/com_android_server_am_LowMemDetector.cpp)
- [AOSP `CachedAppOptimizer.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP `MemoryLimiter.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [AOSP `atrace.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp)
- [Kernel `mm/page_alloc.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/page_alloc.c)
- [Kernel `mm/vmscan.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)
- [Kernel vmscan tracepoints（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/vmscan.h)
- [Kernel PSI documentation](https://docs.kernel.org/accounting/psi.html)
- [Kernel ZRAM documentation](https://docs.kernel.org/admin-guide/blockdev/zram.html)
- [Kernel Multi-Gen LRU documentation](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)
- [Android lmkd documentation](https://source.android.com/docs/core/perf/lmkd)
- [Android cgroups and Task Profiles](https://source.android.com/docs/core/perf/cgroups)
- [Perfetto memory counters](https://perfetto.dev/docs/data-sources/memory-counters)
- [Android 17 App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Android `ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
