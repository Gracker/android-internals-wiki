---
title: AppFlow 研究原型：GB 级应用冷启动内存联合调度
chapter: '16.8'
section: '16.8'
status: finalized
applicable_versions: Android 15 - Android 17（研究原型，非 AOSP 主线）
last_verified: '2026-08-14'
last_verified_against: AppFlow arXiv 2603.17259v1; Android Developers startup/ComponentCallbacks2/LMK docs; AOSP android-17.0.0_r1 lmkd/ProcessList/CachedAppOptimizer/UsageStatsManager/ApplicationExitInfo; Android Common Kernel android17-6.18-2026-06_r6 mm/vmscan.c; Linux PSI docs
confidence: high
pipeline_stage: ready-to-publish
task6_state: reviewed
sources:
- type: paper
  path: https://arxiv.org/abs/2603.17259
- type: paper
  path: https://arxiv.org/html/2603.17259v1
- type: note
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/论文/Android-2026-05-23-AppFlow-ColdLaunch/03-精读.md
- type: research-feed
  path: intake/research-feeds/2026-04-02-15-ch05-appflow-cold-launch-scheduler.md
- type: official
  path: https://source.android.com/docs/core/perf/lmkd
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: official
  path: https://developer.android.com/topic/performance/vitals/lmk
- type: official
  path: https://developer.android.com/reference/android/content/ComponentCallbacks2
- type: kernel-doc
  path: https://docs.kernel.org/accounting/psi.html
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/include/lmkd.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c
tags:
- aosp-performance
- cold-start
- memory-scheduling
- lmkd
- file-preload
related_chapters:
- '4.3'
- '6.2'
- '8.2'
- '16.6'
- '21.1'
---

# AppFlow 研究原型：GB 级应用冷启动内存联合调度

GB 级应用冷启动会同时竞争文件页、匿名页、CPU 与进程生存空间，单点预读可能把延迟转移成更强的内存压力。AppFlow 的价值和边界需要从论文证据出发，分别审视预加载、回收和杀进程策略如何协同。

## 证据边界

AppFlow 是 MobiCom 2026 论文提出的研究原型，它同时协调文件预读、内存页回收和后台进程终止。
当前可公开核查的是 2026 年 3 月发布的 arXiv v1；实验系统以 Android 15 为基础，部署在 Pixel 7、Pixel 8 和 Raspberry Pi 4B 车载试验台上。
论文没有公开完整的 Framework 与 kernel patch：前者指 Android 系统服务层改动，后者指 Linux 内核改动。AppFlow 也没有进入 Android 17 / API 37 的 AOSP 主线。以下内容使用两个独立锚点：

- 原型的设计与实验数字，以 [AppFlow 论文](https://arxiv.org/html/2603.17259v1) 为准；
- 平台已有能力，以 `android-17.0.0_r1` 与 kernel `android17-6.18-2026-06_r6` 为准。

128KB 文件分界、100MB 预加载预算、每 100ms 统计 12,800 个分配页等值来自论文参数搜索。
66.5%、67.9%、95% 等结果也只描述论文设备、应用集合和测试方式，不能当作 Android 17 的默认配置或性能承诺。

## 冷启动为什么会变成系统问题

Android 官方把 cold start（冷启动）定义为从头创建应用进程，并完成应用和首个 Activity 的初始化。系统终止后台进程后再次打开应用，也属于冷启动。
TTID（time to initial display）衡量首帧出现时间；TTFD（time to full display）从系统收到启动 intent 开始计时，到应用调用 `reportFullyDrawn()` 为止，用来表示应用已经完整显示并可用。
TTFD 依赖应用在正确时机主动上报，系统无法自动判断业务是否真的可操作。
大型应用还可能在 TTFD 之后加载模型、贴图或媒体素材，因此实验应另记“关键功能首次可用”的业务时刻。

一次大型应用冷启动可以粗略拆成三段成本：

| 成本 | 形成方式 | 常见证据 |
|---|---|---|
| CPU 与调度 | 进程创建、类加载、初始化、已编译代码执行、线程竞争 | `sched`、主线程 slice（trace 时间片）、ART（Android 运行时）与 Binder（进程间调用）trace |
| 文件 I/O | APK、DEX、SO、资源、模型、贴图或数据库页不在 page cache（文件页缓存） | major fault（需要存储读取的缺页）、块设备 I/O、线程 D 状态、文件系统 trace |
| 内存分配与回收 | 新分配触发 `kswapd`、direct reclaim、内存规整或 swap | PSI、`pgscan_*`、`allocstall`、zRAM、workingset refault |

`kswapd` 是内核后台回收线程；direct reclaim 表示发起内存分配的线程同步参与回收，应用可能直接等待。
内存规整（compaction）尝试得到连续物理页，不等同于 zRAM 的数据压缩；swap 会把匿名页移出 DRAM，Android 常把它们压入 zRAM。
线程处于 D 状态时正在不可中断睡眠，常见原因是等待块设备或内核 I/O。
`pgscan_*` 统计回收器扫描的页面数，`allocstall` 统计内存分配因同步回收而停顿的次数；workingset refault 表示工作集页面逐出后很快又被访问，常用来识别缓存抖动。

多任务会让三段成本互相影响。预读会占用 page cache；内存回收可能在使用前逐出刚读入的页；匿名页换出会与预读竞争存储带宽。
`lmkd` 终止后台应用后，用户返回时还要重新创建进程并加载文件。只分析 `Application.onCreate()` 会漏掉这些系统等待。

论文用 `T_cold = T_I/O + T_cpu + T_alloc` 表示问题，并把系统可调部分放在 I/O 与分配等待上。
这是分析模型，三段在设备上可能并行或互相阻塞，不能直接把 trace 中的 wall time（端到端经过时间）按公式相加。

## 论文给出的四个观察

AppFlow 的设计来自论文样本中的四组测量。引用这些数据时，应同时保留样本语境。

| 论文观察 | 论文报告的数据 | 能支持的判断 |
|---|---|---|
| 启动访问具有重复性 | 24 个应用中，97.2% 的 cold-launch I/O wait 涉及可预测静态数据 | 稳定资源存在预读机会 |
| 切换期 I/O 有空闲 | 论文原文称 79% 的 “DRAM I/O bandwidth” 未使用 | 作者的实验窗口存在预读机会，不能直接推导目标设备的 UFS 或内存带宽余量 |
| 小文件数量多、体积小 | 图 5 汇总为数量约 4.7 倍、内存占比 2.2%；TikTok 个例为 1,002 个、数量 7.47 倍、23MB、约 4% | 小文件适合在有限预算内提前读 |
| 预读和回收会互相抵消 | 低内存下，预读页被回收后启动 I/O 延迟增至 6.4 倍 | 只加 prefetch（预读）可能增加压力与重复读取 |

论文正文在汇总值与 TikTok 个例之间使用了不同数字。Figure 5 的汇总值是 4.7 倍和 2.2%；TikTok 个例是 7.47 倍、23MB、约 4%。
工程文档应注明数字来自图表汇总还是单个应用，不能交叉拼接后再当成所有应用共有的常数。

论文还引用既有研究中的“30 分钟内再次访问 92.5%”，并报告 Android 基线终止了其中 62% 的高概率应用。
前一项不是 AppFlow 自己的 100 天数据，后一项依赖论文的 workload（应用组合与切换序列）和判定方式。产品预测器需要用自身用户群、场景和隐私约束重新训练与验证。

## Selective File Preloader

预加载器处理“何时读、读哪些内容、每次读多大”三个问题。

### 启动前：频次优先

系统从历史 launch trace（启动期间的文件路径、偏移和访问时间记录）提取稳定访问的文件区间，在应用启动前读入小文件以及大文件中反复访问的区间。
小文件会产生较多离散请求，但总字节数较小，适合在严格预算下减少同步等待。

论文为每个应用选择文件大小分界 `s_i`，并把候选值限制在 4KB、8KB 等 2 的幂。每个候选值都对应预计预读体积 `P(s_i)` 和启动期 I/O 吞吐 `V(s_i)`。
随后使用 multiple-choice knapsack（多选背包）：每个应用只能从自己的候选分界中选一个，同时让所有应用的预读体积不超过全局预算。
论文把启动前总预算设为 100MB，求解 60 个应用的配置耗时低于 0.1ms。

128KB 只是论文观察和搜索空间中的代表值，具体应用仍有自己的 `s_i`。
若产品规则固定预读所有小于 128KB 的文件，就会忽略压缩包内部偏移、资源版本、F2FS/ext4 文件系统布局、UFS 请求队列、16KB page size（内存页大小）和应用更新造成的访问变化。

### 启动中：吞吐优先

应用开始启动后，预加载器用较大块读取余下的大文件。论文把它放在独立低优先级进程中，希望预读跟不上时给前台读取让路。
低调度优先级只能减少 CPU 竞争，无法保证 block 层或文件系统一定先完成前台请求。
产品实现还要观测 I/O priority（存储请求优先级）、queue depth（同时在途的请求数）和读放大（实际读取量与最终使用量之比）。

### 历史访问记录何时失效

文件路径相同不代表内容和访问区间稳定。以下变化应降低历史记录的权重，严重时应直接失效：

- APK、APEX、资源包、模型或动态特性更新；
- 用户登录态、语言、主题、A/B 实验改变启动路径；
- 低内存模式、车载用户切换或屏幕形态改变资源选择；
- 加密状态、文件系统、page size 或存储固件发生变化；
- 预读命中后仍出现较高 refault（文件页逐出后很快又被访问）或前台 I/O 延迟。

记录键至少包含包版本、build fingerprint（系统构建标识）、ABI（应用所用指令集接口）、page size 与资源版本。回滚时应能立即停用预测与预读，不能依赖清空用户数据恢复。

## Adaptive Memory Reclaimer

预读成功只说明数据进入 page cache；启动线程使用它之前，内核仍可能回收这些文件页。AppFlow 因此修改了 Linux 内核的回收路径。

### 论文原型的两种控制

论文每 100ms 读取一次可用内存和页分配计数。
当可用内存低于设备阈值、最近窗口分配量高于 `N_alloc` 时，原型先进入 file-first 阶段，优先扫描有文件后备的页；论文参数搜索得到的 `N_alloc` 是 12,800 页。
这个门槛按页计数，换算成字节取决于 page size：4KB 页约为 50MiB，16KB 页约为 200MiB。
file-backed 页扫描完成后，原型进入 anonymous rebalance，重新提高匿名页的回收份额；压力窗口结束后恢复常规策略。该顺序符合论文算法，也避免匿名页长期堆积。

对预加载页，原型按两个窗口处理：

- 启动前读入的少量页每 10 秒访问一次，用来刷新内核记录的活跃度；这不会锁住页面，应用活跃后也会停止；
- 启动中读入的文件通过 `/proc`（内核导出的伪文件系统）发布清单。原型修改 `shrink_page_list()` 回收函数，扫描到清单中的页时暂不逐出，并把页标为 active；启动完成后清除清单。

这项行为来自 kernel patch。`readahead()` 可以提前把文件内容读入 page cache，`madvise(MADV_WILLNEED)` 可以提示内核即将访问某段映射。
两者都不保证页面一直留到应用使用时刻，普通 page-cache 访问也没有这种保证。
论文报告一次活跃度刷新约耗时 10ms，CPU 开销约 0.1%；目标 SoC（系统芯片）、文件集合和电源状态变化后仍需复测。

### Android 17 kernel 6.18 的现状

`android17-6.18-2026-06_r6/mm/vmscan.c` 没有 AppFlow 的预加载文件清单或启动窗口。
classic LRU（传统的近似最近使用链表）路径中的 `get_scan_count()` 会综合 swap 能力、swappiness（匿名页与文件页的相对回收权重）、reclaim priority 和 file LRU 大小。
它还会参考 refault 成本与 cache-trim 状态，最终选择 `SCAN_FILE`、`SCAN_ANON`、`SCAN_EQUAL` 或比例扫描。
启用 MGLRU（Multi-Generational LRU，按访问代际管理页面）时，则进入另一套老化和逐出路径。

其中，reclaim priority 表示当前回收轮次的扫描强度，file LRU 大小表示文件页链表规模；cache-trim 状态表示系统有足够的非活跃文件缓存可优先回收。

论文对其 Android 15 基线“文件页与匿名页交替回收”的概括，不能直接套到 Android 17 kernel 6.18。
Android 17 已经会按运行状态调整扫描比例，但内核仍不知道“某个文件页将在本次应用启动中使用”。AppFlow 增加的正是这种短时启动上下文。

file-backed 页也有不同成本。干净文件页可以直接丢弃，脏文件页要先回写；被丢弃的页若很快 refault，会再次触发存储读取和 stall（任务因资源不足而停顿）。
匿名页可能压入 zRAM，代价由压缩算法、CPU、swap 空间和后续 swap-in（把页读回内存）共同决定。回收策略不能只按 file/anon 二分。

## Context-Aware Process Killer

当页回收不能及时释放足够内存时，AppFlow 再选择后台进程。论文使用两类上下文：

- 近期使用过的应用具有较高返回概率，延后终止；
- 长时间运行且内存相对刚启动基线增长 30%～50% 的应用，重启后缓存和临时分配会回到较低水平。

论文用 `ΔM = M_current - M_relaunch` 估算一次终止带来的长期净释放量，并优先选择 `ΔM` 较大的候选。
`M_relaunch` 表示应用被终止后再次冷启动的内存基线。这个量需要记录应用重新启动后的历史数据，仅凭当前 RSS/PSS 的大小，无法推导出重启后的占用。
RSS 是进程映射到物理内存的页面总量，PSS 会按比例分摊共享页；两者都不完整覆盖 GPU 内存。
memcg（memory cgroup）的记账归属、isolated process（使用隔离 UID 的辅助进程）和独立服务进程也会让“应用占用”难以由单一 PSS 表示。

候选集合仍要服从 Android 的进程重要性规则。
导航、通话、音频、可感知前台服务、设备管理、车载安全界面和系统持久进程，不能因为预测分数低就进入普通 cached process 的可终止集合。
预测器只能给系统原本允许终止的候选重新排序，还要限制同一应用连续成为候选的次数，并设置公平性和最大等待时间，避免长期得不到运行机会的 starvation（饥饿）。

## Android 17 r1 的 LMKD 基线

Android 17 r1 使用 userspace `lmkd`，也就是在用户空间运行的低内存终止守护进程。
源码同时保留三类路径：以 PSI（Pressure Stall Information，压力停顿信息）检测内存压力的新策略；
依据 `minfree` 阈值的 legacy（兼容旧设备）策略；以及检测旧版内核 LMK 接口的兼容分支。
它们都属于同一个守护进程；AOSP 没有名为“LMKD v2”的正式组件或第二个守护进程。

### 压力检测

r1 默认使用 PSI，设备可以通过属性覆盖。源码默认值如下：

| 参数 | 常规设备 | low-RAM 设备 | 含义 |
|---|---:|---:|---|
| `psi_partial_stall_ms` | 70ms | 200ms | 1,000ms 窗口内 PSI `some` 的停顿门槛 |
| `psi_complete_stall_ms` | 700ms | 700ms | 1,000ms 窗口内 PSI `full` 的停顿门槛 |
| `thrashing_limit` | 100% | 30% | workingset refault 相对 file page cache 的比例门槛 |
| `thrashing_limit_decay` | 10% | 50% | 因 thrashing 终止进程后，下一轮门槛的下调比例 |

PSI `some` 表示窗口内至少有部分任务因内存不足而停顿，`full` 表示所有非空闲任务同时停顿。
变量名使用 partial/complete，Linux `/proc/pressure/memory` 中对应的字段名则是 `some/full`。表内数字是 r1 源码默认值，产品属性可以覆盖；low-RAM 的 partial 默认值更高，代表触发较不敏感。
旧材料中的“LOW 70 / MEDIUM 100 / CRITICAL 70”不对应 r1 的 `init_psi_monitors()` 配置，不应继续沿用。

`lmkd` 收到压力事件后还会检查 zone watermark（各内存区域的空闲页水位）、swap、thrashing（页面反复逐出又读回）和 direct reclaim 等状态。
PSI 提供唤醒和压力严重度信号，具体终止哪个进程还要经过候选选择。

### 候选进程和 `oom_score_adj`

ActivityManagerService（AMS）根据进程状态、组件关系和用户可感知性计算 `oom_score_adj`，数值越高通常越容易成为低内存终止候选。
`ProcessList.setOomAdj()` 或 `batchSetOomAdj()` 把结果发给 `lmkd`。`lmkd` 从较高 adj 分组向较低分组查找；`kill_heaviest_task=false` 时通常取该分组队尾，配置为 true 时选取组内占用较大的进程。
源码还规定，当搜索进入 `PERCEPTIBLE_APP_ADJ` 或更重要的范围时，选择逻辑会强制切换为 heaviest，希望用更少的终止次数释放足够内存。

adj 表达 Android 组件此刻的重要性。
若把“预计稍后会打开”的应用伪装成 perceptible（用户能感知）或 visible（界面可见），会破坏 AMS、LMKD 和 cached process 管理共同使用的优先级约定。
这种做法也可能把更多内存压力转移给真正可感知的进程。

### `LMK_PROCS_PRIO` 的准确含义

Android 17 r1 的 `LMK_PROCS_PRIO` 是 framework 到 `lmkd` 控制 socket（进程间通信通道）的内部批量协议：

- `include/lmkd.h` 把每个控制包的记录上限定为 3；
- `ProcessList.batchSetOomAdj()` 读取每个 `ProcessRecordInternal.getCurAdj()`，每 3 个进程发送一包；
- `lmkd.cpp::cmd_procs_prio()` 在收包线程内循环调用 `apply_proc_prio()`；
- r1 `lmkd.cpp` 没有 io_uring 处理器，也没有 32 条记录的主线协议。

这项批处理可以减少控制消息次数，但没有提供“保护将启动应用”的策略接口。它不能改变文件页回收，也不能接收 AppFlow 的 `ΔM`、访问概率或预加载清单。
io_uring 是 Linux 的异步 I/O 接口，AOSP 17 r1 的 `lmkd.cpp` 没有相关处理器。移植设计若参考第三方 fork（从 AOSP 分出的代码分支），必须先区分分支扩展与主线能力。

### 全局 LMKD 属性不能代替预测器

`ro.lmk.lowmem_min_oom_score`、`ro.lmk.kill_heaviest_task`、thrashing 门槛等属性影响整台设备。
调高最低可终止 adj 可能使 `lmkd` 在严重压力下找不到足够候选，增加 direct reclaim、系统 stall 或 kernel OOM（内核因内存耗尽而终止进程）的风险；调低值会扩大候选集合。
这些全局属性无法按应用或启动窗口动态表达预测结果。

`am set-isolated-process-uid-list` 管理 isolated process 的 UID 范围，与后台应用保护、文件页预读或 LMKD 候选排序无关。

## CachedAppOptimizer 能做什么

`CachedAppOptimizer` 在 Android 17 r1 中负责 cached app compaction 和 freezer。
这里的 compaction 是针对目标进程回收文件页或匿名页的操作，SOME/FULL/ANON profile 决定处理哪类页面；它不同于前文为取得连续物理页而进行的内核内存规整。
freezer 会暂停 cached 进程的调度，并先处理该进程的 Binder 通信，恢复使用时再解冻。这个类不记录启动文件热集，也不会在 `vmscan` 中保护预读文件页。

若要让 AppFlow 的进程终止分数影响 `CachedAppOptimizer`，仍需修改 AMS 的进程策略，还要验证 compaction、freezer、adj 更新和 LMKD 选择之间没有 race condition（执行先后变化导致结果不一致）。
源码中也没有可直接复用的 AppFlow hook（扩展入口）。

## 原型组件与 Android 17 能力映射

| AppFlow 组件 | Android 17 已有基础 | 主线缺失部分 | 需要的权限或改动 |
|---|---|---|---|
| Selective File Preloader | 应用启动事件、文件 I/O、page cache、UsageStats | 跨应用文件访问记录、两阶段预算器、启动预测服务 | 平台服务、文件访问权限、预读执行器 |
| Adaptive Memory Reclaimer | classic LRU/MGLRU、zRAM、memcg、PSI、`vmscan` | 启动窗口、预加载文件标记、逐出跳过规则 | kernel core mm patch 与接口 |
| Context-Aware Process Killer | AMS adj、`lmkd`、cached LRU、PSS/RSS 采样 | relaunch 基线、返回概率、净释放排序 | Framework 与 `lmkd` 策略改动 |
| 验证与回滚 | Perfetto、statsd（系统指标收集服务）、`ApplicationExitInfo`、系统属性 | AppFlow 专用原因码、命中率和页保护统计 | 指标记录、实验开关、版本化访问记录 |

`UsageStatsManager.queryEvents()` 需要 `PACKAGE_USAGE_STATS`，在 `AndroidManifest.xml` 声明后还需用户到设置中授予 usage access（使用情况访问权）；只查询本包事件的接口不需要该权限。
论文使用后台采集应用，不代表普通三方应用可以无提示收集整台设备的应用使用序列。系统镜像内的预测服务也要遵守多用户、工作资料、访客和数据保留期限。

## 三种实施权限下的可做范围

### 普通应用

应用可以优化自己的初始化、生成 Baseline Profile、记录 TTID/TTFD、采样自己的文件访问，并控制自己的资源读取。
`TRIM_MEMORY_UI_HIDDEN` 表示应用 UI 从可见变为不可见，应用可在该回调中释放能够重建的界面缓存。
从 API 34 起，系统不再发送多档运行中内存压力回调；API 35 将相应常量标记为 deprecated，但没有废弃 `TRIM_MEMORY_UI_HIDDEN`。
应用还可用 `ApplicationExitInfo` 查询此前的退出原因。

普通应用不能访问 `lmkd` 控制 socket、写其它进程的 `oom_score_adj`、修改 `vmscan`、保护 page cache 中的指定文件，也不能默认读取其它应用的使用历史。
应用内预读可能有收益，但它不等同于 AppFlow。

### 特权 Framework 原型

系统厂商可以在 platform service（系统服务）中采集经过授权的应用切换序列，维护带版本号的文件访问记录，并在 launch observer（启动事件观察器）收到事件前后调度预读。
这个阶段可以验证预测准确率、I/O 干扰、100MB 级预算是否适合目标设备，以及进程终止模型是否有稳定信号。

若 kernel 未改，预读页随时可能按常规策略被回收。
实验报告要分别记录“读取内容最终被使用”和“页面一直留到使用时刻”，避免把偶然的 page-cache 命中算成回收保护效果。这个阶段也不应随意降低 adj 来模拟后台存活收益。

### 产品级 OS 与 kernel 原型

要复现论文完整设计，需要同时修改 Framework 和 kernel：建立启动会话 ID；传递文件或 inode/offset（文件对象编号与字节位置）标识；在 classic LRU 和 MGLRU 中都定义短时保护。
还要处理文件截断、更新、卸载、memcg 迁移和多用户隔离；最后把进程排序限制在 AMS/LMKD 已允许终止的候选集合内。

GKI（Generic Kernel Image，通用内核镜像）允许 vendor module 通过受控 hook 扩展部分功能，但模块不能直接替换 core `mm/vmscan.c` 的回收语义。
修改 core mm 意味着长期维护产品 kernel 分支、内核 ABI（二进制接口）和安全更新合并。
验证范围还要覆盖 CTS/VTS/GTS（应用兼容、厂商接口和 Google 认证测试）、SELinux 权限、OTA 升级、suspend/resume（休眠与唤醒）、low-RAM 设备和 kernel OOM 回归。

## 如何设计一轮可信实验

### 固定启动口径

测试脚本应记录目标应用在每轮前的进程状态和 page-cache 条件。
cold 表示应用进程不存在；hot 表示进程和 Activity 都仍在内存中，只需回到前台；warm 处于两者之间，例如进程仍在但 Activity 要重建。
三类样本必须分组，不能只根据 `am start -W` 的 ActivityManager 时间输出推断缓存状态。Android 官方的 TTID/TTFD、Jetpack Macrobenchmark 的启动模式和 Perfetto launch slice 可以互相校验。

清空全局 page cache 只适合受控实验室镜像，因为它会改变所有进程和文件系统状态；线上设备不能用这种方式制造 cold 样本。
线上应观察自然发生的冷启动，并按上次退出原因、包版本、设备 uptime（自开机起的运行时间）和内存压力分层。

### 建立负载组合

每个设备至少覆盖：

- 空闲、常规多任务、内存紧张和 swap 接近上限；
- 4KB/16KB page size、不同 DRAM 档位和存储型号；
- 首次安装、普通版本、应用更新后、系统 OTA 后；
- 屏幕亮灭、充电/电池、温度和 thermal throttling（温控降频）；
- 前台导航、音频、通话、端侧模型推理等不可随意中断的并发任务。

每种组合都要报告样本数、P50/P90/P95/P99（有 50%/90%/95%/99% 样本不超过该值）、置信区间和异常值规则，平均数仅作补充。

### 同时观察四组证据

| 目标 | 指标 | 反例信号 |
|---|---|---|
| 启动变快 | TTID、TTFD、关键功能可用时刻、cold relaunch（后台进程被终止后的冷重启）比例 | 首帧更快但关键功能更晚可用 |
| 预读有效 | 预读字节、使用字节、major fault、block wait、refault | 读放大、命中低、前台 I/O 被拖慢 |
| 内存更稳 | memory PSI、`pgscan_direct`、allocstall、zRAM、swap-in/out | stall 下降但 swap 或功耗大增 |
| 多任务可接受 | LMK 次数、后台存活、短时间 relaunch、用户可感知 LMK | 保护目标应用后其它任务更早被终止 |

`ApplicationExitInfo.REASON_LOW_MEMORY` 可用于应用侧回看，但并非所有设备都支持该原因。
`ActivityManager.isLowMemoryKillReportSupported()` 返回 false 时，低内存终止可能只记录为 `REASON_SIGNALED` 和 `SIGKILL`。
`ApplicationExitInfo` 也不包含完整的 LMKD 候选评分，平台实验仍需结合 `lmkd` 日志、statsd 和 trace。

### 分离三个组件的贡献

至少保留四组：

1. Android 17 原生基线；
2. 只有 Selective File Preloader；
3. Preloader 加 Adaptive Memory Reclaimer；
4. 三个组件全部开启。

AppFlow 论文的 ablation（逐个关闭组件的消融实验）显示，只开 SFP 时启动变快，但 cold relaunch 数增加 30%。可以理解为预读带来的内存压力抵消了一部分收益。
按组件分组后，才能区分“读取时间提前”“页面保留更久”和“后台进程选择变化”各自造成的影响。

## 论文实验结果该怎样阅读

论文在 Android 15 原型上修改约 1,672 行 Framework 和 1,107 行 Linux kernel 代码。
Pixel 设备通过修改 `arm64_memblock_init()`，把内核可见内存限制为 6GB 或 8GB；这是受控实验配置，不代表设备实际只有这些物理内存。Raspberry Pi 4B 车载试验台使用 4GB 内存。
测试包含 60 多个应用、模拟多任务负载，以及一条记录应用使用顺序的 100 天 trace。

| 场景 | 论文报告结果 | 限定条件 |
|---|---|---|
| 论文摘要 | cold-launch latency（冷启动耗时）最多下降 66.5%，示例从 2s 降到 690ms；100 天中 95% 的启动小于 1s | 作者原型与工作负载 |
| Pixel 8 cold launch | 相对 Android 平均下降 33.7%～43.6%；6GB 高负载个例最多下降 57% | 8 个 GB 级应用，三档负载 |
| 17 应用多任务 | 保留后台应用从 7/17 增到 13/17，平均 relaunch 时间下降 37.6% | Pixel 7，6GB/8GB，高负载 |
| 高压力机制指标 | direct reclaim 次数下降 67.9%，LMK 事件下降 33.7% | Pixel 8 6GB 高负载 |
| 100 天案例 | 平均 cold-launch latency 下降 23%，GB 级 cold relaunch 次数下降 31.6% | 一条 60+ 应用 trace |
| 车载案例 | 4.3s 降到 2.0s，下降 53.4% | BYD Seal 供电、Pi 4B 计算、5 个应用 |
| 端侧生成式负载 | 后台终止数从 8～9 个降到 0～3 个，survivability（任务存活率）从 66.6% 升到 100% | Pixel 8 8GB 的论文场景 |

这些结果展示了原型潜力，也带有明确的复现限制：公开论文没有提供完整 Android/kernel patch、每个参数的产品配置、全部原始 trace 和功耗数据。
`am start -W`、清文件缓存和人为限制内存也不同于线上自然发生的启动。产品评估应把论文作为待验证假设，再在目标设备和真实负载上重新测量。

## 与 Baseline Profile、Cloud Profile 的关系

Profile 与 AppFlow 处理不同成本：

| 技术 | 主要对象 | 主要收益证据 | 无法解决的部分 |
|---|---|---|---|
| Baseline/Startup Profile | 热方法、类、DEX 布局与预编译 | CPU running（线程实际执行）时间、JIT/解释执行、class load | 模型和资源文件不在 page cache |
| Cloud Profile | 用户群聚合后的 ART profile 与 dexopt | 编译 artifact（编译产物）、启动 CPU 和代码布局 | 当前设备的内存压力与后台存活 |
| AppFlow | 启动文件页、回收窗口、后台进程选择 | major fault、I/O wait、refault、LMK、relaunch | 应用自身重初始化与低效业务逻辑 |

同一次启动可能同时受 CPU 和 I/O 限制。做 A/B 实验时，应先固定 dexopt 状态和 Profile 版本，再比较预读策略；评估 Profile 时也要记录 page-cache 和后台进程状态。
缺少这些控制变量，就无法判断收益来自代码编译、文件缓存还是后台进程存活。

## 车载、端侧模型和大型游戏

车载系统有导航、媒体、语音、仪表、多屏和多用户并发，后台进程的重要性不能仅按最近使用时间推断。
冷启动优化需要服从驾驶安全和音视频连续性，预测失误的代价比手机社交应用场景更高。

端侧模型的权重常通过 `mmap` 映射文件，使访问到的权重页成为 file-backed 页面；推理中间张量和 runtime（模型运行时）的堆又会增加匿名页。
页面类型取决于具体 runtime，不能笼统地把模型权重都算作匿名页。
大型游戏同样混合 APK/asset pack（按需分发的资源包）、native heap（原生代码堆）、图形驱动和 GPU 分配，单看进程 RSS 会漏掉关键资源。

这三类负载适合验证 AppFlow 提出的联合问题，但进程终止规则需要按角色设置硬约束：导航、通话、正在播放音频和安全相关服务不得由预测模型降级。
模型或游戏只有在温度、电量和前台 I/O 都满足启用条件时才能预读。

## 产品化风险与退出条件

| 风险 | 典型后果 | 保护与退出条件 |
|---|---|---|
| 预测错误 | 读入未使用数据，增加 I/O 与 DRAM 占用 | 命中率、读放大、版本化访问记录、快速停用 |
| 页保护过强 | 其它工作集 refault、direct reclaim 或 OOM | 最大保护字节、最大时长、压力强制退出 |
| 进程终止偏置 | 某些后台应用长期成为牺牲对象 | 角色白名单、每应用终止频率、公平性 |
| 隐私越界 | 跨应用使用序列泄露用户行为 | 本地最小化、多用户隔离、保留期限、审计 |
| kernel 分叉 | 安全补丁合并困难、MGLRU/classic LRU 行为分裂 | 尽量小的 patch、双路径测试、持续 rebase（把改动迁移到新基线） |
| 功耗与温度 | 空闲预读唤醒存储，竞争前台任务 | 电源与温度启用条件、能耗 A/B、存储队列监控 |

任一压力档位出现 kernel OOM、SystemUI/Launcher 被终止、导航或音频中断、P99 变差或 I/O 读放大失控时，策略都应自动停用并恢复 Android 原生行为。
退出路径也必须经过同等规模的压力测试。

## 源码核对入口

- [`android-17.0.0_r1/system/memory/lmkd/lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)：PSI、thrashing、候选选择和 `cmd_procs_prio()`。
- [`android-17.0.0_r1/system/memory/lmkd/include/lmkd.h`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/include/lmkd.h)：控制协议与 3 条记录上限。
- [`android-17.0.0_r1/frameworks/base/.../ProcessList.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)：adj 发送与 `batchSetOomAdj()`。
- [`android-17.0.0_r1/frameworks/base/.../CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)：cached app compaction 与 freezer。
- [`android-17.0.0_r1/frameworks/base/.../UsageStatsManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java)：使用历史接口与权限说明。
- [`android-17.0.0_r1/frameworks/base/.../ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)：低内存退出原因和设备支持差异。
- [`android17-6.18-2026-06_r6/mm/vmscan.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)：classic LRU、MGLRU 和回收扫描选择。

## 与其他章节的边界

- Android 进程优先级、PSI 与 LMKD 机制见 [4.3 lmkd、Cached App Freezer 与内存压力治理](../../part1-fundamentals/ch04-memory/03-lmkd-freezer-memory-pressure.md)。
- 冷、温、热启动和 TTID/TTFD 见 [8.2 App 冷启动链路与 Binder Trace 分析](../../part2-performance/ch08-responsiveness/02-app-cold-start-binder-trace.md)。
- Baseline Profile 的采集与验证见 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](../../part5-app/ch21-startup/04-baseline-startup-cloud-profile.md)。
- 系统启动及 I/O 分阶段分析见 [16.6 Android 系统启动耗时优化与 bootanalyze](06-system-boot-time-optimization.md)。
- 应用启动诊断流程见 [21.1 App 启动路径、监控与度量](../../part5-app/ch21-startup/01-app-startup-path-monitoring.md)。

## 参考资料

- [AppFlow 论文 HTML](https://arxiv.org/html/2603.17259v1)
- [AppFlow 论文摘要与版本信息](https://arxiv.org/abs/2603.17259)
- [AOSP：Low memory killer daemon](https://source.android.com/docs/core/perf/lmkd)
- [Android Developers：App startup time](https://developer.android.com/topic/performance/vitals/launch-time)
- [Android Developers：Low memory killers](https://developer.android.com/topic/performance/vitals/lmk)
- [Android Developers：ComponentCallbacks2](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Linux kernel：Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [AOSP r1：lmkd.cpp](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [AOSP r1：lmkd.h](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/include/lmkd.h)
- [AOSP r1：ProcessList.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [AOSP r1：CachedAppOptimizer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP r1：UsageStatsManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java)
- [AOSP r1：ApplicationExitInfo.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [Android kernel：android17-6.18-2026-06_r6 vmscan.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)
- 本地精读笔记：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/论文/Android-2026-05-23-AppFlow-ColdLaunch/03-精读.md`
- 研究采集稿：`intake/research-feeds/2026-04-02-15-ch05-appflow-cold-launch-scheduler.md`
