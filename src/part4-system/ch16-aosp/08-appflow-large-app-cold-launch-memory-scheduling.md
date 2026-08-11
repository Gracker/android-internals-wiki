---
title: "AppFlow：GB 级应用冷启动内存联合调度"
chapter: "16.8"
section: "16.8"
status: finalized
drafted_date: "2026-05-23"
applicable_versions: "Android 15 - Android 17（研究原型，非 AOSP 主线）"
last_verified: "2026-07-30"
last_task9_audit: "2026-07-11"
last_verified_against: "AppFlow arXiv 2603.17259v1; AOSP android-17.0.0_r1 lmkd/ProcessList/CachedAppOptimizer/UsageStatsManager/ApplicationExitInfo; Android Common Kernel android17-6.18-2026-06_r6 mm/vmscan.c"
confidence: high
sources:
  - type: paper
    path: "https://arxiv.org/abs/2603.17259"
  - type: note
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/论文/Android-2026-05-23-AppFlow-ColdLaunch/03-精读.md"
  - type: research-feed
    path: "intake/research-feeds/2026-04-02-15-ch05-appflow-cold-launch-scheduler.md"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/lmk"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c"
tags: [aosp-performance, cold-start, memory-scheduling, lmkd, file-preload]
related_chapters: ["4.4", "6.3", "8.2", "16.7", "21.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "研究素材 + 论文精读 + 官方/外部搜索"
---

# AppFlow：GB 级应用冷启动内存联合调度

## 证据边界

AppFlow 是 MobiCom 2026 论文提出的研究原型。当前可公开核查的是 2026 年 3 月发布的 arXiv v1；实验系统以 Android 15 为基础，部署在 Pixel 7、Pixel 8 和 Raspberry Pi 4B 车载试验台上，完整 Framework/kernel patch 没有随论文公开。它没有进入 Android 17 / API 37 的 AOSP 主线。以下内容使用两个独立锚点：

- 原型的设计与实验数字，以 [AppFlow 论文](https://arxiv.org/html/2603.17259v1) 为准；
- 平台已有能力，以 `android-17.0.0_r1` 与 kernel `android17-6.18-2026-06_r6` 为准。

128KB 文件分界、100MB 预加载预算、每 100ms 统计 12,800 个分配页等值来自论文参数搜索。66.5%、67.9%、95% 等结果也只描述论文设备、应用集合和测试方式。它们不代表 Android 17 的配置或性能承诺。

## 冷启动为什么会变成系统问题

Android 官方把 cold start 定义为从头创建应用进程并完成应用与首个 Activity 初始化。系统杀掉后台进程后再次打开应用，也会进入 cold start。TTID 衡量首帧出现时间，TTFD 衡量内容达到可交互状态的时间。大型应用常在这两个时刻之外继续加载模型、贴图或媒体素材，因此还要记录业务可用时刻。

一次大型应用冷启动可以粗略拆成三段成本：

| 成本 | 形成方式 | 常见证据 |
|---|---|---|
| CPU 与调度 | 进程创建、类加载、初始化、编译代码执行、线程竞争 | `sched`、主线程 slice、ART 与 Binder trace |
| 文件 I/O | APK、DEX、SO、资源、模型、贴图或数据库页不在页缓存 | major fault、block I/O、线程 D 状态、文件系统 trace |
| 内存分配与回收 | 新分配触发 kswapd、direct reclaim、压缩或 swap | PSI、`pgscan_*`、`allocstall`、zRAM、workingset refault |

多任务把三段成本耦合起来。预读会占用页缓存；内存回收可能在使用前驱逐刚读入的页；匿名页换出会与预读竞争存储带宽；`lmkd` 杀掉后台应用后，用户返回该应用又会支付进程重建和文件加载成本。只分析 `Application.onCreate()` 会漏掉这些系统等待。

论文用 `T_cold = T_I/O + T_cpu + T_alloc` 表示问题，并把系统可调部分放在 I/O 与分配等待上。这是分析模型，三段在设备上可能并行或互相阻塞，不能直接把 trace 中的 wall time 按公式相加。

## 论文给出的四个观察

AppFlow 的设计来自论文样本中的四组测量。引用这些数据时，应同时保留样本语境。

| 论文观察 | 论文报告的数据 | 能支持的判断 |
|---|---|---|
| 启动访问具有重复性 | 24 个应用中，97.2% 的 cold-launch I/O wait 涉及可预测静态数据 | 稳定资源存在预读机会 |
| 切换期 I/O 有空闲 | 论文测得 79% 的 DRAM I/O bandwidth 未使用 | 预读可尝试使用空闲窗口 |
| 小文件数量多、体积小 | 图 5 汇总为数量约 4.7 倍、内存占比 2.2%；TikTok 个例为 1,002 个、数量 7.47 倍、23MB、约 4% | 小文件适合在有限预算内提前读 |
| 预读和回收会互相抵消 | 低内存下，预读页被回收后启动 I/O 延迟增至 6.4 倍 | 只加 prefetch 可能增加压力与重复读取 |

论文正文在汇总值与 TikTok 个例之间使用了不同数字。Figure 5 的汇总值是 4.7 倍和 2.2%；TikTok 个例是 7.47 倍、23MB、约 4%。工程文档应注明数字来自图表汇总还是单个应用，不能交叉拼接后再当成所有应用共有的常数。

论文还引用既有研究中的“30 分钟内再次访问 92.5%”，并报告 Android 基线杀掉其中 62% 的高概率应用。前一项不是 AppFlow 自己的 100 天数据，后一项依赖论文的 workload 与判定方式。产品预测器需要用自身用户群、场景和隐私约束重新训练与验证。

## Selective File Preloader

预加载器处理“何时读、读哪些内容、每次读多大”三个问题。

### 启动前：频次优先

系统从历史 launch trace 提取稳定访问的文件和区间，在应用启动前读入小文件以及大文件中的热点区间。小文件会制造较多离散请求，但总字节数较小，适合在严格预算下换取更少的同步等待。

论文为每个应用选择文件大小分界 `s_i`，并把候选值限制在 4KB、8KB 等 2 的幂。每个候选值都对应预计预读体积 `P(s_i)` 和启动期 I/O 吞吐 `V(s_i)`，然后用 multiple-choice knapsack 在总预算内为每个应用选一个分界。论文把启动前总预算设为 100MB，求解 60 个应用的配置耗时低于 0.1ms。

128KB 只是论文观察和搜索空间中的代表值，具体应用仍有自己的 `s_i`。把“所有小于 128KB 的文件都预读”写进产品规则，会忽略压缩包内部偏移、资源版本、F2FS/ext4 布局、UFS queue、16KB page size 和应用更新造成的访问变化。

### 启动中：吞吐优先

应用开始启动后，预加载器用较大块读取余下的大文件。论文把它放在独立低优先级进程中，目标是让预读落后时让位给前台读取。低调度优先级只能减少 CPU 竞争，不能自动保证 block 层或文件系统的前台请求总是先完成；产品实现还要观测 I/O priority、queue depth 和读放大。

### 画像何时失效

文件路径相同不等于内容和访问区间稳定。以下变化应使画像降权或失效：

- APK、APEX、资源包、模型或动态特性更新；
- 用户登录态、语言、主题、AB 实验改变启动路径；
- 低内存模式、车载用户切换或屏幕形态改变资源选择；
- 加密状态、文件系统、page size 或存储固件发生变化；
- 画像命中后仍出现较高 refault 或前台 I/O 延迟。

画像键至少包含包版本、build fingerprint、ABI、page size 与资源版本。回滚时应能立即停用预测与预读，不能依赖清空用户数据恢复。

## Adaptive Memory Reclaimer

预读成功只说明数据进入页缓存；启动线程使用它之前，数据仍可能被回收。AppFlow 为此改动 Linux 内核回收路径。

### 论文原型的两种控制

论文每 100ms 读取一次可用内存和页分配计数。当可用内存低于设备阈值、最近窗口分配量高于 `N_alloc` 时，原型进入 file-first 阶段；论文参数搜索得到的 `N_alloc` 是 12,800 页。file-backed 页扫描完成后，原型再进入 anonymous rebalance；压力窗口结束后恢复常规回收策略。这个顺序比“高压期间永远只扫描文件页”更接近论文的算法描述，也避免匿名页长期堆积。

对预加载页，原型按两个窗口处理：

- 启动前读入的少量页每 10 秒轻触一次，应用活跃后停止；
- 启动中读入的文件通过 `/proc` 发布清单，修改 `shrink_page_list()`，扫描到相关页时跳过并标为 active，启动完成后清除清单。

这是一项 kernel patch，不是 `readahead()`、`madvise()` 或普通 page-cache 访问自然提供的保证。论文报告该轻触扫描约耗时 10ms、开销约 0.1%；这个开销仍需在目标 SoC、文件集合和电源状态上复测。

### Android 17 kernel 6.18 的现状

`android17-6.18-2026-06_r6/mm/vmscan.c` 没有 AppFlow 的预加载文件清单或启动窗口。经典 LRU 路径中的 `get_scan_count()` 会根据 swap 能力、swappiness、reclaim priority、file LRU 大小、refault 成本和 cache-trim 状态选择 `SCAN_FILE`、`SCAN_ANON`、`SCAN_EQUAL` 或比例扫描；启用 MGLRU 时走另一套代际老化与逐出路径。

因此，论文对其 Android 15 基线“文件页与匿名页交替回收”的概括不能直接套到 Android 17 kernel 6.18。Android 17 已经按运行状态调整扫描比例，但仍不理解“某个文件页将在本次应用启动中使用”的语义。AppFlow 增加的是这一层短时语义。

file-backed 页也不总是零成本。干净文件页可以丢弃，脏文件页需要回写；被丢弃的页若很快 refault，会产生存储读取和 stall。匿名页可能在 zRAM 中压缩，代价由压缩算法、CPU、swap 空间与后续 swap-in 共同决定。回收策略不能只按 file/anon 二分。

## Context-Aware Process Killer

当页回收不能及时释放足够内存时，AppFlow 再选择后台进程。论文使用两类上下文：

- 近期使用过的应用具有较高返回概率，延后终止；
- 长时间运行且内存相对刚启动基线增长 30%～50% 的应用，重启后缓存和临时分配会回到较低水平。

论文用 `ΔM = M_current - M_relaunch` 估算一次终止带来的长期净释放量，并优先选择 `ΔM` 较大的候选。这个量需要历史 relaunch 画像，当前 RSS/PSS 大并不能推导出重启后的基线。共享页、GPU 内存、memcg charge、isolated process 和服务进程也会使“应用占用”难以由单一 PSS 表示。

候选集合仍要尊重 Android 进程重要性。导航、通话、音频、可感知前台服务、设备管理、车载安全界面和系统持久进程不能因为预测分数低就进入普通缓存进程的牺牲集合。预测只能在系统已经允许终止的候选中排序，并且要有饥饿、公平性和最大延迟约束。

## Android 17 r1 的 LMKD 基线

Android 17 r1 使用一个 userspace `lmkd` 守护进程。源码中有 PSI 新策略、legacy minfree 路径和检测旧 in-kernel 接口的兼容分支，这些是同一守护进程的运行路径。AOSP 没有名为“LMKD v2”的正式组件或独立守护进程。

### 压力检测

r1 默认使用 PSI，设备可以通过属性覆盖。源码默认值如下：

| 参数 | 常规设备 | low-RAM 设备 | 含义 |
|---|---:|---:|---|
| `psi_partial_stall_ms` | 70ms | 200ms | 1,000ms 窗口内的 partial stall 门槛 |
| `psi_complete_stall_ms` | 700ms | 700ms | 1,000ms 窗口内的 complete stall 门槛 |
| `thrashing_limit` | 100% | 30% | workingset refault 相对 file page cache 的门槛 |
| `thrashing_limit_decay` | 10% | 50% | 杀进程后压力未恢复时的门槛衰减比例 |

这些是 r1 源码默认值，产品属性可以覆盖。旧注入材料中的“LOW 70 / MEDIUM 100 / CRITICAL 70”不对应 r1 的 `init_psi_monitors()` 配置，不能继续使用。

`lmkd` 收到压力事件后还会检查 zone watermark、swap、thrashing、direct reclaim 等状态。PSI 负责唤醒与严重度信号，不会单独决定牺牲哪个进程。

### 候选进程和 `oom_score_adj`

AMS 根据进程状态、组件关系和用户可感知性计算 adj。`ProcessList.setOomAdj()` 或 `batchSetOomAdj()` 把这个结果发给 `lmkd`。`lmkd` 从较高 adj 桶向较低 adj 桶查找候选；`kill_heaviest_task=false` 时通常取该桶队尾，配置为 true 时取该桶内占用较大的进程。源码还规定，当搜索进入 `PERCEPTIBLE_APP_ADJ` 或更重要的范围时，选择逻辑会强制改为 heaviest，尽量减少牺牲数量。

adj 表达 Android 组件的当前重要性。把“预计稍后会打开”伪装成 perceptible 或 visible，会改变 AMS、LMKD、cached process 管理与资源公平性的共同约定，也可能把更多内存压力转移给真实的可感知进程。

### `LMK_PROCS_PRIO` 的准确含义

Android 17 r1 的 `LMK_PROCS_PRIO` 是 framework 到 `lmkd` 控制 socket 的内部批量协议：

- `include/lmkd.h` 把单包记录上限定为 3；
- `ProcessList.batchSetOomAdj()` 读取每个 `ProcessRecordInternal.getCurAdj()`，每 3 个进程发送一包；
- `lmkd.cpp::cmd_procs_prio()` 在收包线程内循环调用 `apply_proc_prio()`；
- r1 `lmkd.cpp` 没有 io_uring 处理器，也没有 32 条记录的主线协议。

这项批处理减少控制消息次数，不提供“保护将启动应用”的策略接口。它不能改变文件页回收，也不能接收 AppFlow 的 `ΔM`、访问概率或预加载清单。把 AOSPA 等 fork 的 io_uring 扩展写成 AOSP 17 能力，会直接误导移植工作。

### 全局 LMKD 属性不能代替预测器

`ro.lmk.lowmem_min_oom_score`、`ro.lmk.kill_heaviest_task`、thrashing 门槛等属性影响整台设备。调高最低可杀 adj 可能使 `lmkd` 在严重压力下找不到足够候选，增加 direct reclaim、系统 stall 或 kernel OOM 风险；调低值则扩大可牺牲集合。它们不具备按应用、按启动窗口变化的语义。

`am set-isolated-process-uid-list` 管理 isolated process UID 范围，也和后台应用保护、页预读或 LMKD 候选排序无关。

## CachedAppOptimizer 能做什么

`CachedAppOptimizer` 在 Android 17 r1 中负责 cached app compaction 与 freezer 相关工作。它可以按进程状态和配置执行 SOME/FULL 等压缩，冻结 cached 进程及其 Binder 接口，并在进程恢复时解冻。它处理的是 cached 进程 CPU 活动与匿名内存整理，不记录启动文件热集，也不在 `vmscan` 中保护文件页。

把 AppFlow 的 killer 分数接到 `CachedAppOptimizer` 仍需修改 AMS 的进程策略，并证明 compaction、freezer、adj 更新和 LMKD 选择之间没有竞态。类名相邻不代表已有可复用的 AppFlow hook。

## 原型组件与 Android 17 能力映射

| AppFlow 组件 | Android 17 已有基础 | 主线缺失部分 | 需要的权限或改动 |
|---|---|---|---|
| Selective File Preloader | 应用启动事件、文件 I/O、page cache、UsageStats | 跨应用文件画像、两阶段预算器、启动预测服务 | 平台服务、文件访问权限、预读执行器 |
| Adaptive Memory Reclaimer | classic LRU/MGLRU、zRAM、memcg、PSI、`vmscan` | 启动窗口、预加载文件标记、逐出跳过规则 | kernel core mm patch 与接口 |
| Context-Aware Process Killer | AMS adj、`lmkd`、cached LRU、PSS/RSS 采样 | relaunch 基线、返回概率、净释放排序 | Framework 与 `lmkd` 策略改动 |
| 验证与回滚 | Perfetto、statsd、`ApplicationExitInfo`、系统属性 | AppFlow 专用原因码、命中率和页保护统计 | 埋点、实验开关、版本化画像 |

`UsageStatsManager.queryEvents()` 需要 `PACKAGE_USAGE_STATS`，声明权限后还需用户在设置中授予 usage access；只查询本包事件的接口不需要该权限。论文的后台采集应用不代表普通三方应用可以无提示收集全设备使用序列。系统镜像内的预测服务也要遵守多用户、工作资料、访客与数据保留边界。

## 三种实施权限下的可做范围

### 普通应用

应用可以优化自己的初始化、生成 Baseline Profile、记录 TTID/TTFD、采样自己的文件访问和控制自己的资源读取。它还可以在 `TRIM_MEMORY_UI_HIDDEN` 等有效回调中释放可重建缓存，并用 `ApplicationExitInfo` 了解此前退出原因。

普通应用不能访问 `lmkd` 控制 socket、写其它进程的 `oom_score_adj`、修改 `vmscan`、保护 page cache 中的指定文件，也不能默认读取其它应用的使用历史。应用内预读可能有收益，但它不等同于 AppFlow。

### 特权 Framework 原型

系统厂商可以在 platform service 中采集经过授权的应用切换序列，维护版本化文件画像，并在 launch observer 周围调度预读。此阶段能验证预测准确率、I/O 干扰、100MB 级预算是否适合目标设备，以及 killer 画像有没有稳定信号。

若 kernel 未改，预读页随时可能被正常回收。实验报告要把“预读命中”与“页存活到使用时刻”分开，避免把偶然 page-cache 命中当作回收保护效果。此阶段也不应通过随意降低 adj 模拟存活收益。

### 产品级 OS 与 kernel 原型

要复现论文完整设计，需要 Framework 和 kernel 同时修改：建立启动会话 ID，传递文件或 inode/offset 标识，在 classic LRU 与 MGLRU 都定义短时处理，处理文件截断、更新、卸载、memcg 迁移与多用户隔离，再把 killer 排序放入 AMS/LMKD 的合法候选集合。

GKI 允许 vendor module 和受控 hook 扩展部分功能，但模块不能直接替换 core `mm/vmscan.c` 语义。修改 core mm 意味着维护产品 kernel 分支、ABI 与安全更新合并。实现还需覆盖 CTS、VTS、GTS、SELinux、OTA、suspend/resume、low-RAM 和 kernel OOM 回归。

## 如何设计一轮可信实验

### 固定启动口径

测试脚本应记录目标应用在每轮前的进程状态和 page-cache 条件。cold、warm、hot 必须分组，不能仅用 `am start -W` 输出推断。Android 官方的 TTID/TTFD、Macrobenchmark 启动模式和 Perfetto launch slice 可以互相校验。

清空全局 page cache 适合受控实验室镜像，会影响所有进程与文件系统状态；线上设备不能用这种方式制造 cold 样本。更稳妥的线上分析是观察自然冷启动，并按上次退出、包版本、设备 uptime 和内存压力分层。

### 建立负载组合

每个设备至少覆盖：

- 空闲、常规多任务、内存紧张和 swap 接近上限；
- 4KB/16KB page size、不同 DRAM 档位和存储型号；
- 首次安装、普通版本、应用更新后、系统 OTA 后；
- 屏幕亮灭、充电/电池、温度和 thermal throttling；
- 前台导航、音频、通话、端侧模型推理等不可随意中断的并发任务。

每个格子报告样本数、P50/P90/P95/P99、置信区间和异常值规则。平均数只能作为补充。

### 同时观察四组证据

| 目标 | 指标 | 反例信号 |
|---|---|---|
| 启动变快 | TTID、TTFD、业务可用时刻、cold relaunch 比例 | 首帧快但可交互更晚 |
| 预读有效 | 预读字节、使用字节、major fault、block wait、refault | 读放大、命中低、前台 I/O 被拖慢 |
| 内存更稳 | memory PSI、`pgscan_direct`、allocstall、zRAM、swap-in/out | stall 下降但 swap 或功耗大增 |
| 多任务可接受 | LMK 次数、后台存活、短时间 relaunch、用户可感知 LMK | 保护目标应用后其它任务更早死亡 |

`ApplicationExitInfo.REASON_LOW_MEMORY` 可用于应用侧回看，但设备不一定支持该原因。`ActivityManager.isLowMemoryKillReportSupported()` 返回 false 时，低内存终止可能只表现为 `REASON_SIGNALED` 和 `SIGKILL`。它也不包含完整的 LMKD 候选评分，平台实验仍需 `lmkd` 日志、statsd 和 trace。

### 分离三个组件的贡献

至少保留四组：

1. Android 17 原生基线；
2. 只有 Selective File Preloader；
3. Preloader 加 Adaptive Memory Reclaimer；
4. 三个组件全部开启。

AppFlow 论文的 ablation 已显示只开 SFP 时启动变快，但 cold relaunch 数增加 30%。这个结果说明预读带来的内存压力会抵消一部分收益。组件分组能区分“读取更早”“页活得更久”和“后台进程选择变化”各自造成的影响。

## 论文实验结果该怎样阅读

论文在 Android 15 原型上修改约 1,672 行 Framework 和 1,107 行 Linux kernel 代码。Pixel 设备通过修改 `arm64_memblock_init()` 限制可见内存为 6GB 或 8GB，Raspberry Pi 4B 车载试验台为 4GB。测试包含 60 多个应用、模拟多任务负载和一条 100 天使用 trace。

| 场景 | 论文报告结果 | 限定条件 |
|---|---|---|
| 论文摘要 | cold-launch latency 最多下降 66.5%，示例 2s 到 690ms；100 天中 95% 启动小于 1s | 作者原型与工作负载 |
| Pixel 8 cold launch | 相对 Android 平均下降 33.7%～43.6%；6GB 高负载个例最多下降 57% | 8 个 GB 级应用，三档负载 |
| 17 应用多任务 | 保留后台应用从 7/17 增到 13/17，平均 relaunch 时间下降 37.6% | Pixel 7，6GB/8GB，高负载 |
| 高压力机制指标 | direct reclaim 次数下降 67.9%，LMK 事件下降 33.7% | Pixel 8 6GB 高负载 |
| 100 天 case study | 平均 cold-launch latency 下降 23%，GB 级 cold relaunch 次数下降 31.6% | 一条 60+ 应用 trace |
| 车载 case study | 4.3s 降到 2.0s，下降 53.4% | BYD Seal 供电、Pi 4B 计算、5 个应用 |
| 端侧生成式负载 | 后台 kill 从 8～9 个降到 0～3 个，survivability 从 66.6% 到 100% | Pixel 8 8GB 的论文场景 |

这些结果展示了原型潜力，也留下复现约束：公开论文没有提供完整 Android/kernel patch、每个参数的产品配置、全部原始 trace 与功耗数据；`am start -W`、清文件缓存和人为限制内存也与自然线上启动不同。选型时应把论文当作假设来源，用目标产品重新测量。

## 与 Baseline Profile、Cloud Profile 的关系

Profile 与 AppFlow 处理不同成本：

| 技术 | 主要对象 | 主要收益证据 | 无法解决的部分 |
|---|---|---|---|
| Baseline/Startup Profile | 热方法、类、DEX 布局与预编译 | CPU running 时间、JIT/解释执行、class load | 模型和资源文件不在页缓存 |
| Cloud Profile | 用户群聚合后的 ART profile 与 dexopt | 编译 artifact、启动 CPU 和代码布局 | 当前设备的内存压力与后台存活 |
| AppFlow | 启动文件页、回收窗口、后台进程选择 | major fault、I/O wait、refault、LMK、relaunch | 应用自身重初始化与低效业务逻辑 |

同一启动可以同时受 CPU 和 I/O 限制。A/B 时要固定 dexopt 状态与 profile 版本，再比较预读；评估 profile 时也要记录 page-cache 与后台进程状态。缺少这些控制变量，收益会在两类机制之间错配。

## 车载、端侧模型和大型游戏

车载系统有导航、媒体、语音、仪表、多屏和多用户并发，后台进程的重要性不能仅按最近使用时间推断。冷启动优化需要服从驾驶安全和音视频连续性，预测失误的代价高于手机社交应用。

端侧模型的权重常通过 mmap 形成大规模 file-backed 映射，推理中间张量和运行时堆又会增加匿名页。页面类型与映射方式取决于具体 runtime，不能写成“模型权重都属于匿名页”。大型游戏同样混合 APK/asset pack、native heap、图形驱动和 GPU 分配，单看进程 RSS 会漏掉关键资源。

这三类负载适合验证 AppFlow 提出的联合问题，但 killer 规则需要按角色设置硬约束：导航、通话、正在播放音频和安全相关服务不得由预测模型降级；模型或游戏的预读预算也要服从 thermal、battery 和前台 I/O 门禁。

## 产品化风险与退出条件

| 风险 | 典型后果 | 门禁 |
|---|---|---|
| 预测错误 | 读入未使用数据，增加 I/O 与 DRAM 占用 | 命中率、读放大、版本化画像、快速停用 |
| 页保护过强 | 其它工作集 refault、direct reclaim 或 OOM | 最大保护字节、最大时长、压力强制退出 |
| killer 偏置 | 某些后台应用长期成为牺牲对象 | 角色白名单、每应用 kill 频率、公平性 |
| 隐私越界 | 跨应用使用序列泄露用户行为 | 本地最小化、多用户隔离、保留期限、审计 |
| kernel 分叉 | 安全补丁合并困难、MGLRU/classic LRU 行为分裂 | 小 patch、双路径测试、持续 rebase |
| 功耗与温度 | 空闲预读唤醒存储，竞争前台任务 | 电源/thermal 门禁、能耗 A/B、queue 监控 |

任一压力档位出现 kernel OOM、SystemUI/Launcher 被杀、导航或音频中断、P99 回归、I/O 读放大失控时，策略应自动退出并恢复 Android 原生行为。退出路径必须经过同样规模的压力测试。

## 源码核对入口

- `android-17.0.0_r1/system/memory/lmkd/lmkd.cpp`：PSI、thrashing、候选选择和 `cmd_procs_prio()`。
- `android-17.0.0_r1/system/memory/lmkd/include/lmkd.h`：控制协议与 3 条记录上限。
- `android-17.0.0_r1/frameworks/base/.../ProcessList.java`：adj 发送与 `batchSetOomAdj()`。
- `android-17.0.0_r1/frameworks/base/.../CachedAppOptimizer.java`：cached app compaction 与 freezer。
- `android-17.0.0_r1/frameworks/base/.../UsageStatsManager.java`：使用历史接口与权限说明。
- `android-17.0.0_r1/frameworks/base/.../ApplicationExitInfo.java`：低内存退出原因及设备支持差异。
- `android17-6.18-2026-06_r6/mm/vmscan.c`：classic LRU、MGLRU 和回收扫描选择。

## 与其他章节的边界

- Android 进程优先级、PSI 与 LMKD 机制见 [[04-lmk|4.4 低内存管理与 LMKD]]。
- 冷、温、热启动和 TTID/TTFD 见 [[02-app-launch|8.2 应用启动分析]]。
- Baseline Profile 的采集与验证见 [[07-baseline-profiles|8.7 Baseline Profiles]]。
- 系统启动及 I/O 分阶段分析见 [[07-system-boot-time-optimization|16.7 Android 系统启动耗时分析]]。
- 应用启动诊断流程见 [[01-startup-analysis|21.1 应用启动分析]]。

## 参考资料

- [AppFlow 论文 HTML](https://arxiv.org/html/2603.17259v1)
- [AppFlow 论文摘要与版本信息](https://arxiv.org/abs/2603.17259)
- [AOSP：Low memory killer daemon](https://source.android.com/docs/core/perf/lmkd)
- [Android Developers：App startup time](https://developer.android.com/topic/performance/vitals/launch-time)
- [Android Developers：Low memory killers](https://developer.android.com/topic/performance/vitals/lmk)
- [AOSP r1：lmkd.cpp](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [AOSP r1：lmkd.h](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/include/lmkd.h)
- [AOSP r1：ProcessList.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [AOSP r1：CachedAppOptimizer.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP r1：UsageStatsManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java)
- [AOSP r1：ApplicationExitInfo.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [Android kernel：android17-6.18-2026-06_r6 vmscan.c](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)
