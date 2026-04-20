# 知识盲区清单

- - 1. **InputChannel 创建失败处理机制** - 文章完全未提及当 socketpair 创建失败或 App 端无法正确接收时的错误处理和恢复机制。这对系统稳定性和故障排查至关重要。

- - 2. **Input 系统与 SurfaceFlinger 协作** - 缺少 Input 系统与 SurfaceFlinger 在窗口可见性变化、合成时机等方面的交互机制。在全屏/分屏/多窗口场景中，两个系统的协作对性能影响很大。

- - 高 - 这两个机制都是系统级的关键协作点，对性能优化和问题诊断有直接影响

- - - 研究 InputChannel 失败时的系统行为和错误恢复策略

- - - 分析 Input 事件如何影响 SurfaceFlinger 的合成决策

- - - 添加这两个协作场景的 Trace 分析案例

- - - 2.6 SurfaceFlinger 与合成

- - - 3.2 触摸响应的性能分析

- - - 9.1 ANR 设计思想

- - 1. **VRR vs ARR 概念混淆** — 章节中 LTPO 面板的 VRR（面板级可变刷新率）和 Android 15 的 ARR（系统级自适应刷新率）被混在一起讨论。ARR 是 SurfaceFlinger 中新增的决策逻辑，利用 VRR 面板能力做更精细的帧率控制。两者是不同层级的概念，需要明确区分。

- - 2. **SurfaceFlinger 刷新率选择算法** — 章节将算法简化为"整除"规则，但 AOSP 中 RefreshRateSelector 的实际实现使用多维度评分系统（帧率匹配度、功耗影响、切换开销、是否无缝）。需要补充更准确的算法描述。

- - 3. **VSync 周期动态变化对 Choreographer 的影响** — 当 SurfaceFlinger 切换刷新率时（如 60Hz→120Hz），VSync-app 间隔变化，正在排队的 VSync 订阅如何处理？

- - 高

- - - 梳理 VRR（面板能力）和 ARR（Android 系统策略）的分层关系

- - - 研究 AOSP RefreshRateSelector 的评分算法核心逻辑

- - - 验证 Choreographer 在 VSync 周期变化时的行为

- - - 2.3 VSync 机制

- - - 2.6 SurfaceFlinger 与合成

- - - 2.18 Adaptive Refresh Rate 与动态帧率控制

- - 1. **dumpsys cpuinfo 缺失** — 作为 CPU 占用快速排查的基本工具，在性能分析章节中完全未提及。cpuinfo 可以查看每个进程的 CPU 使用率、负载因子，是 dumpsys 工具链中与 meminfo 同等重要的诊断命令。

- - 2. **framestats/gfxinfo 版本行为差异** — gfxinfo reset 在某些版本清除全局统计、framestats 列定义在不同 API level 有变化、聚合统计字段（如 Number Slow bitmap uploads）有引入版本要求。这些版本差异在实战中是高频踩坑点。

- - 高（cpuinfo）/ 中（版本差异）

- - - 补充 dumpsys cpuinfo 的输出结构、关键字段（CPU usage per process、load averages）和使用场景

- - - 梳理 gfxinfo 各字段在不同 Android 版本的变化矩阵

- - - 确认 gfxinfo reset 在 Android 12+ 是否已修复为仅清除指定进程

- - - 5.1 Linux 进程调度基础

- - - 7.3 卡顿分析方法论

- - - 13.1 Perfetto 简介与演进

- - f2fs 的 Adaptive Logging 机制（在 normal logging 和 threaded logging 之间动态切换）对性能行为有重大影响，但在 6.2 章节中完全未提及。当存储空间不足时，f2fs 从 normal logging（copy-and-compaction）切换到 threaded logging（在 dirty segment 中复用空间），性能特征会发生质变——这直接关系到"手机存储快满时为什么突然变卡"的用户体验问题。

- - 高

- - - f2fs 源码中 `fs/f2fs/segment.c` 的日志策略选择逻辑

- - - f2fs 官方文档中关于 adaptive logging 的说明

- - - 在不同空间占用率下 f2fs I/O 延迟的 benchmark 数据

- - - 对 Perfetto Trace 中识别 threaded logging 模式的方法

- - 6.2（文件系统）、6.3（I/O 调度）、7.1（流畅性）

- - dm-verity 与 EROFS 的配合机制未在章节中讨论。文中提到"配合 dm-verity 的完整性校验"但未展开。读者需要理解：EROFS 只读 + dm-verity 校验如何协同保护 system 分区完整性，以及这一机制对启动时间的影响（dm-verity 验证需要读取哈希树）。

- - 中

- - - dm-verity 工作原理（哈希树、Verified Boot 流程）

- - - EROFS + dm-verity 的挂载时间开销

- - - Android 启动过程中 dm-verity 验证的 Perfetto Trace 表现

- - - dm-verity 对 EROFS 压缩读取路径的影响

- - 6.2（文件系统）、1.2（系统启动）、16.x（AOSP 安全机制）

- - 章节在 Cached Process 部分只提到了 oom_adj 值（900-999），但完全未展开 Android 12 引入的 CachedAppOptimizer 机制。该机制使用 cgroup v2 freezer 冻结 cached 进程，使其线程完全停止执行（不是降优先级，是冻结）。对 Perfetto 分析的影响：冻结进程的线程 slice 彻底消失，与被 LMK 杀死的进程在 Trace 中的表现不同（被杀是进程消失，被冻结是线程消失但进程仍在）。

- - 高

- - - AOSP `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` 实现

- - - `system/core/libprocessgroup/profiles/task_profiles.json` 中 freezer 相关 profile

- - - Google 官方文档关于 cached app freezer 的说明

- - - Perfetto 中冻结 vs 被杀的区分方法

- - 1.3, 4.4, 5.8

- - 章节给出 android-16 的完整 adj 值表，但缺少版本演进说明。中间档位 PERCEPTIBLE_MEDIUM_APP_ADJ (225) 和 PERCEPTIBLE_LOW_APP_ADJ (250) 的引入版本不明确。SERVICE_A_ADJ 的移除版本也未标注。对于 applicable_versions 覆盖 Android 10-16 的章节，读者需要知道这些值在不同版本上的差异。

- - 中

- - - 逐版本对比 ProcessList.java 中的 adj 常量变化（Android 10 → 11 → 12 → 13 → 14 → 15 → 16）

- - - 特别关注 PERCEPTIBLE 细分档位和 SERVICE_A 的引入/移除节点

- - 1.3, 4.4

- - 性能分析的开销（Profiling Overhead）在方法论章节中完全未提及。包括：

- - 1. Perfetto trace 的 CPU 开销和 buffer 对内存的影响

- - 2. Simpleperf 采样频率对测量精度的 trade-off

- - 3. Benchmark 工具运行时的热降频对结果的影响

- - 4. 如何设计实验来隔离和量化测量开销本身

- - 高 — 方法论章节强调「数据驱动」但不讨论「测量本身如何影响数据」，是一个结构性缺陷。

- - - 收集 Perfetto 不同 config（ftrace buffer size、atrace categories）对被测 App 性能的影响数据

- - - 收集 Simpleperf 不同采样频率（99Hz vs 999Hz vs 9999Hz）对目标进程执行时间的影响

- - - 研究 Android Benchmark 库的 warmup 机制如何应对热降频

- - - 参考 Brendan Gregg 对 profiling overhead 的讨论（Systems Performance Chapter 2）

- - 15.1, 13.1, 13.2, 14.5

- - 章节 applicable_versions 标注覆盖 Android 8-17，但正文内容在 Android 12 SplashScreen 之后未涉及任何版本差异。Android 13-17 中的启动优化相关行为变更完全空白，包括：per-app language 对 SplashScreen 的影响、Cloud Profile Mainline 化、AutoFDO 协同、profileable 标记要求变化、reportFullyDrawn() 行为变更等。

- - 高

- - - 查证 Android 13/14/15/16/17 中与启动优化相关的 Behavior Changes

- - - 整理 SplashScreen API 在各版本的兼容行为差异

- - - 梳理 Baseline Profile + Cloud Profile + AutoFDO 在 Android 15/16 中的协同机制

- - - 验证 `reportFullyDrawn()` 在 Android 15+ 的变更（`androidx.activity:activity:1.8.0` 引入的自动 TTFD 追踪）

- - 8.1, 8.7, 1.12, 5.10

- - 1. Jetpack Navigation Component 完全未提及。Navigation 是现代 Android 页面导航的标准方案，其性能特征（NavGraph inflate 开销、deep link 解析延迟、Fragment swap 优化、shared element transition）与本章「页面跳转速度」主题高度相关。

- - 2. Compose Navigation 未提及。Compose 的页面切换性能（relocate 节点复用 vs 传统 inflate）是 applicable_versions 涵盖 Android 16 时的必要话题。

- - 高（Navigation Component）/ 中（Compose Navigation）

- - - Navigation Component 的 NavGraph inflate 耗时及 lazy inflation

- - - Navigation deep link vs 普通 startActivity 的额外 Binder 开销

- - - Compose Navigation 的性能对比数据（Compose vs View 体系的页面切换延迟）

- - - Activity Transition API / shared element transition 对感知延迟的优化

- - 8.1, 8.2, 8.3, 3.1

- - 1. 完全未提及 PerfettoSQL 的核心扩展操作符：`SPAN_JOIN`、`LEFT_JOIN_SPAN`、`PARTITIONED_JOIN`。这些是 Perfetto 特有的时间区间 JOIN 操作符，是实现"帧期间的 GC/Binder/锁"这类交叉分析的正确工具。当前章节的交叉分析 SQL 使用普通 JOIN + 时间范围条件，在大 Trace 上性能差且逻辑不精确。

- - 2. 未提及窗口函数（LEAD/LAG/FIRST_VALUE）用于帧节奏时序分析。

- - 3. 未提及 `dur = -1`（未结束 slice）和 `dur = 0`（即时事件）的过滤——新手常见坑。

- - 4. 未提及 PERCENTILE/QUANTILES 函数用于帧时间 P50/P90/P99 分布——行业标准做法。

- - 5. 未提及 `trace_bounds` 表用于获取 Trace 起止时间。

- - 高（SPAN_JOIN 是 PerfettoSQL 的核心差异化特性）

- - 中（窗口函数和百分位统计）

- - 中（dur=-1 过滤是实战常见坑）

- - - 梳理 Perfetto v54.0 中所有标准库模块（android.frames、android.monitor、android.input、android.startup 等）提供的视图和函数

- - - 整理 SPAN_JOIN / LEFT_JOIN_SPAN 的典型用法模式（特别是帧×Binder、帧×GC 交叉分析）

- - - 收集 Perfetto SQL 性能优化技巧（大 Trace 查询加速）

- - - 汇总 PerfettoSQL 与标准 SQLite 的差异点（哪些函数不可用、哪些扩展可用）

- - 13.1, 13.3, 13.5, 13.8

- - Traversal vs Relayout 的触发条件区分缺失。App 侧 requestLayout() 触发 in-app traversal（measure/layout/draw，不涉及 Binder），而 Window 属性变化触发 relayoutWindow（Binder 调用 WMS）。读者无法判断"什么情况下 App 自己处理就行，什么情况下必须走 WMS"。这是 Perfetto 分析中的常见困惑——看到 relayoutWindow Slice 时不知道它为什么被触发。

- - 2026-04-19 深度技术 Review 再次确认，正文仍未把 ViewRootImpl `performTraversals()` 中触发 relayout 的 6 个条件（`mFirst`、`windowShouldResize`、`insetsChanged`、`viewVisibilityChanged`、`params != null`、`mForceNextWindowRelayout`）以及 Android 14+ 的 `relayoutAsync()` 路径纳入主线，也没有把 `updateBlastSurfaceIfNeeded()` / `BLASTBufferQueue` 的客户端后续链路接上。

- - 高

- - - 整理 ViewRootImpl 中触发 relayoutWindow vs scheduleTraversals 的条件矩阵

- - - 常见 UI 操作（setVisibility、setBackground、invalidate、requestLayout）分别走哪条路径

- - - 在 Perfetto 中如何区分 WMS 侧的 relayout 和 App 侧的 traversal

- - - 核对 `performTraversals()` 的 6 个 relayout 条件、`relayoutAsync()` 适用条件，以及 `updateBlastSurfaceIfNeeded()`/`BLASTBufferQueue` 的后续链路

- - 2.12, 2.4, 2.5, 3.1, 8.2

- - SELinux/MAC 对每次 Binder transaction 执行权限检查，在高频调用场景下累积效应显著。本章多处讨论 Binder 瓶颈但未提及 SELinux 因素。

- - 高

- - - 测量不同 Android 版本上 SELinux 对 Binder 延迟的贡献

- - - 分析 enforced vs permissive 模式下的性能差异

- - - 研究 Android 14+ 中 SELinux 策略优化的趋势

- - 1.1, 1.4 (Binder IPC)

- - 讨论了 Project Mainline 但未解释 APEX 工作机制（zip + loop device mount），也未说明模块更新对运行时性能的影响。

- - 中

- - - APEX 容器格式和加载机制

- - - 模块更新时服务重启的性能影响

- - - Mainline 模块版本对 Trace 分析的影响（已在文中提及但未深入）

- - 1.1, 1.6 (版本演进), 16.2 (版本变更追踪)

- - applicable_versions 声明 Android 8-16，但遗漏了多项版本级架构变化：Android 10 的 /dev/vndbinder、Android 12 的 cached process frozen state、ART 编译策略演进（cloud profiles）。

- - 高

- - - 梳理 Android 8-16 每个版本在架构层面的关键变化

- - - 重点关注影响 Binder 延迟、进程管理、编译策略的变更

- - - 为每个变化标注对性能分析的具体影响

- - 1.1, 1.6, 16.2

- - startForeground() 超时机制（Android 12+ 5 秒，之前 10 秒）是现代 Android 最常见的 Service ANR 类型之一，但本章未提及。此超时与 Service 启动超时是独立的两个计时器：startForeground() 要求 Service 在 onCreate()/onStartCommand() 后必须在规定时间内调用 startForeground()，否则触发 ANR。

- - 高

- - - AOSP ActivityManagerService.java 中 SERVICE_START_FOREGROUND_TIMEOUT 和 SERVICE_START_FOREGROUND_TIMEOUT_SHORT 的定义和版本变化

- - - Android 12 将超时从 10 秒缩短到 5 秒的 commit 和官方说明

- - - Android 14 新增的 foreground service type 对 startForeground 超时的影响

- - 9.2, 5.8

- - InputConnection ANR（InputMethodManagedService timeout）未提及。当 App 的 InputConnection 在 5 秒内未响应 IME 的输入事件请求时，系统会触发 ANR。这在输入法相关应用和自定义 View 中比较常见。

- - 中

- - - AOSP InputMethodManagerService.java 中 INPUT_METHOD_NOT_RESPONDING_TIMEOUT 的定义

- - - InputConnection ANR 与 InputDispatcher ANR 的触发路径差异

- - - 在 Perfetto 中的表现特征

- - 9.2, 3.1, 3.4

- - Broadcast 风暴的连锁 ANR 真实机制需要深入研究。当前章节描述的"累计超时"机制不存在，但广播风暴确实会导致多 App 同时 ANR。需要明确真正的原因链条：系统资源争抢（CPU 调度延迟、Binder 线程池竞争、I/O 压力）如何使多个独立 receiver 各自超时。同时需要区分有序广播的串行分发延迟和并行广播的并发资源竞争两种情况。

- - 高

- - - AOSP BroadcastQueue.processNextBroadcastLocked() 中 setBroadcastTimeoutLocked() 的调用时机和参数

- - - Android 14 新增的 CPU-starved 超时分级机制（60s→120s）对广播风暴 ANR 模式的影响

- - - 有序广播串行分发中，前序 receiver 耗时对后序 receiver 调度延迟的影响量化

- - 9.1, 9.2

- - ART GC 代码片段验证不足。当前 CollectGarbageInternal() 代码是伪代码，需要基于实际 AOSP（android-14 或 android-15）提供准确的阶段调用代码。特别关注：ConcurrentCopying collector 的实际 Run() 方法中 PausePhase/ConcurrentPhase 的调用模式，以及 CMC（Concurrent Mark-Compact，Android 15+）是否有不同的暂停模式。

- - 中

- - - art/runtime/gc/collector/concurrent_copying.cc 中 Run() 方法的实际实现

- - - art/runtime/gc/heap.cc 中 CollectGarbageInternal() 的实际代码

- - - Android 15 CMC collector 的暂停模式变化

- - 4.3, 4.8

- - HWUI RenderThread 的 Bitmap 纹理上传（texture upload）机制。在 Draw 阶段，如果 View 包含 Bitmap（如 ImageView 加载的图片、RecyclerView 中的列表项图片），需要将 Bitmap 像素数据从 CPU 内存上传到 GPU 纹理。这个 upload 操作在 RenderThread 上执行，可能导致 RenderThread drawFrame 耗时异常，是列表滑动场景中常见的掉帧根因。当前 2.1 章节完全未提及此机制。

- - 中

- - - RenderThread 中 uploadTextures_IfNeeded() 的实现和触发条件

- - - Bitmap 像素格式（ARGB_8888 vs HARDWARE）对上传开销的影响

- - - 在 Perfetto 中识别 texture upload 导致的 RenderThread 耗时

- - - 与 2.5 节（MainThread 与 RenderThread 协作）的交叉引用

- - 2.1, 2.5, 7.10 (图片加载与 Bitmap 性能优化)

- - 章节讨论了 kswapd 和 Direct Reclaim，但完全未提及 Compact Daemon（Android 10+ 引入的用户空间内存规整守护进程）。compactd 在低内存时主动做 memory compaction 减少碎片，与 kswapd 并列的重要低内存缓解机制。

- - 高

- - - Android 10 compactd 源码路径和触发条件

- - - compactd 与 kswapd 的协作关系

- - - Perfetto 中 compactd 的 track 表现

- - - compactd 对减少 Direct Reclaim 的实际效果数据

- - 4.2, 10.4

- - 章节多次提及 onTrimMemory() 回调（"正确的做法是响应 onTrimMemory() 回调"），但从未解释 trim level 体系（TRIM_MEMORY_UI_HIDDEN=20, TRIM_MEMORY_RUNNING_LOW=10, TRIM_MEMORY_MODIFYING=60 等）如何映射到 PSI/vmpressure 压力等级。读者无法理解"系统通知 App 释放内存"的具体机制和时机。

- - 高

- - - AOSP ActivityThread.handleTrimMemory 的触发链

- - - AMS 如何根据内存压力级别计算 trimLevel

- - - trimLevel 与 lmkd 杀进程策略的对应关系

- - 4.5, 10.4

- - 1. **5G Radio 状态机未覆盖**：案例三 Radio 状态机描述基于 3G/LTE 模型（Full Power → Low Power → Standby），5G NR 的 DRX/CDRX 机制和功耗特征有显著差异，未提及。

- - 2. **FCM 中国大陆可用性**：案例三长期方案推荐 FCM 替代轮询，但中国大陆无法使用 Google 服务。需补充自建 WebSocket 或厂商推送通道（小米推送、华为推送、OPPO 推送等）的替代方案。

- - 3. **线上功耗监控体系缺失**：章节末尾已标注 [待补充]，需要一个完整的线上功耗监控体系搭建案例。

- - 中（5G 差异和 FCM 可用性影响读者在特定场景下的方案选择）

- - - 5G NR Radio 状态机（DRX/CDRX）与 4G LTE 的功耗模型差异

- - - 国内主流厂商推送通道的接入方式和功耗对比

- - - BatteryStats + UsageStatsManager 在 App 内采集功耗数据的方案

- - 11.1, 11.2, 11.3, 12.2

- - InputDispatcher 的 stale event 丢弃机制在 Android 12+ 中引入。当 App 从后台恢复或长时间未处理 Input 事件时，InputDispatcher 会计算事件的"年龄"，超过阈值的事件会被直接丢弃而不分发给 App。这个机制解释了"为什么后台切换回来时有些触摸事件丢失"的现象，在 Perfetto 中可以看到 wq 中的事件被批量移除（不触发 ANR）。

- - 高——直接影响"为什么后台切换后触摸事件丢失"的分析能力，且本章覆盖 Android 12-16，stale event 机制在目标版本范围内已生效。

- - - 在 AOSP android-14 中搜索 `isStale` 或 `STALE_EVENT_TIMEOUT` 相关常量和逻辑

- - - 在 InputDispatcher.cpp 中找到 stale event 丢弃的具体阈值和判断逻辑

- - - 在 Perfetto 中验证 stale event 丢弃的 Trace 表现（wq 值突然归零但无 ANR）

- - 3.1, 3.2, 9.1, 9.2

- - FrameTimeline 机制（Android 12 引入）在本章多次引用但从未解释。FrameTimeline 是 Perfetto 中最重要的渲染性能 Track 之一，提供「预期帧时间 vs 实际帧时间」的对比数据。缺少其数据来源（SurfaceFlinger 的 FrameTimeline 层）、工作原理（App 报告 vs SF 报告 vs HWC 报告的分层机制）和在 Perfetto 中的正确阅读方法。

- - 高

- - - AOSP frameworks/native/services/surfaceflinger/FrameTimeline 模块源码

- - - perfetto.dev 关于 Frame Timeline 的文档

- - - Android 12 FrameTimeline Jank 追踪的官方博客

- - 2.1, 2.4, 2.6, 13.10

- - Deoptimization（去优化）机制在 ART 编译管线章节中完全缺失。当 AOT 编译代码因以下原因失效时，ART 必须去优化回解释执行：

- - - 类加载发生变化（新类被加载导致内联假设失效）

- - - JIT Profile 反馈与 AOT 假设矛盾

- - - 调试器附加（debugger attach）

- - - 部分 Android 版本中动态代理类变化

- - 去优化是编译管线的核心闭环，没有它 JIT→AOT→解释执行的循环不完整。在 Perfetto 中可通过 `Deoptimization` Slice 观测。

- - 高——编译管线章节不讨论去优化，等同于 GC 章节不讨论 GC 触发条件。

- - - AOSP art/runtime/deoptimization.cc 去优化实现

- - - art/runtime/jit/jit_code_cache.cc 中的去优化触发逻辑

- - - Perfetto 中 Deoptimization 相关 Slice 的观测方法

- - - 不同 Android 版本中去优化策略的差异

- - 1.7, 4.3

- - Debug 构建与 Release 构建在 profiling 时的系统性行为差异：ART JIT 优化策略差异、GC 行为差异、锁实现差异（debug 构建使用可调试锁）、Scheduler 钩子差异等。这些差异导致在 debug 构建上观察到的性能问题可能不是 release 构建上的实际问题，反之亦然。作为工具使用章节，这是一个高价值的补充方向。

- - 高

- - - AOSP 中 `art/runtime/debugger.cc` 和 `art/runtime/jit/jit.cc` 对 debuggable 标志的处理

- - - Android 官方文档中关于 debuggable vs profileable vs release 构建的 profiling 行为差异

- - - Google I/O 2019/2020 关于 profileable 构建的演讲内容

- - 14.1, 15.6, 13.1

- - BLAST vs Legacy BufferQueue 的架构对比缺失。章节多次提到"BLAST 模型的核心变化点"但从未解释 Legacy 模式的架构（Consumer 端在 SF 进程的 BufferQueue 模型），读者无法理解 BLAST 解决了什么问题、为什么需要迁移。这是理解整个 18.2 章节的前提知识。

- - 高

- - - AOSP 中 BLASTBufferQueue 替换 Legacy BufferQueue 的 commit 历史（Android 11 R）

- - - Legacy 模式下 BufferQueue 的 Consumer 在 SurfaceFlinger 进程中的工作方式

- - - BLAST 模式下 BBQ 在 App 进程内作为 Consumer 的架构变化

- - - SurfaceControl.Transaction 的引入时机和动机

- - 18.2, 2.1, 2.6, 2.13, 2.16, 18.10

- - 章节 L699 声称 "Android 16 中引入了 AsyncBufferQueue"，但无法在 AOSP android-16.0.0_r1 源码或官方 changelog 中确认。需要验证此组件是否真实存在、具体功能是什么、以及引入的确切版本。

- - 高

- - - 搜索 AOSP android-16.0.0_r1 中是否存在 AsyncBufferQueue 类

- - - 检查 Android 16 Developer Preview / Beta 的官方 release notes

- - - 如果不存在，修正为正确的缓冲区管理变更描述

- - 2.1, 2.6, 18.2

- - TTID/TTFD 讨论未区分冷启动（Cold Start）、温启动（Warm Start）、热启动（Hot Start）三种启动类型。Google 官方文档（developer.android.com/topic/performance/launch-time）明确区分三种类型：

- - - Cold Start：进程从头创建，最慢

- - - Warm Start：进程存活但 Activity 需重建

- - - Hot Start：Activity 存活，最快

- - 缺少此分类会导致：线上监控数据混杂不同启动类型，无法区分"启动慢是因为冷启动多还是真的有回归"。

- - 高

- - - Google 官方文档中 cold/warm/hot start 的精确定义和度量方法

- - - 各启动类型下 TTID/TTFD 的典型基线数据

- - - 线上监控如何区分三种启动类型（通过 Activity.onCreate 是否被调用等信号）

- - 15.3, 8.1, 8.2

- - 厂商特定的温控中间层（Qualcomm thermal-engine、MediaTek thermal manager）未提及。这些用户态守护进程在 Thermal HAL 和内核之间实现了实际的 PID 控制策略和 OEM 定制算法，是决定设备温控行为的关键组件。不了解这一层，读者无法理解：(1) 为什么同样 SoC 的不同设备温控行为差异巨大；(2) 在 Perfetto 中看到的某些温控行为可能来自 vendor daemon 而非 Android 框架。

- - 高

- - - Qualcomm thermal-engine 开源代码（codeaurora.org / git.codelinaro.org）中的控制策略实现

- - - MediaTek thermal manager 的公开文档或源码

- - - 如何在 Perfetto 中区分 Android 框架温控和厂商温控的行为

- - 5.5, 5.12

- - Linux 内核的 thermal governor 算法（step_wise、fair_share、bang_bang）未讨论。章节介绍了 trip point 和 cooling device 的概念，但未解释 governor 如何决定 cooling state 的变化。Android 设备默认使用 step_wise governor，它决定了温度上升时频率是渐进降低的（阶梯式），这对理解 Perfetto 中频率变化的模式至关重要。

- - 中

- - - Linux kernel Documentation/thermal/sysfs-api.rst 中 governor 的说明

- - - step_wise governor 源码：drivers/thermal/step_wise.c

- - - Android GKI 默认 governor 配置

- - 5.5, 5.4

- - GLES 链路的帧节奏控制（Frame Pacing）完全未讨论。Continuous 模式下 GLThread 紧凑循环渲染，帧率仅受 BufferQueue 限制，无法精确控制。Swappy / Frame Pacing Library 在 GLES 中的集成方式、如何与 Choreographer 协调、如何设置目标帧率等关键话题缺失。这是游戏和地图应用开发者最关心的 GLES 性能话题之一。

- - 高

- - - Android Frame Pacing Library（Swappy）源码和 GLES 集成方式

- - - Choreographer + requestRender() 实现 VSync 对齐的方案

- - - EGL_EXT_swap_buffers_with_damage 扩展对帧节奏的影响

- - - 不同 GLES 帧率控制策略的 Perfetto 表现对比

- - 18.8, 2.17, 18.6

- - EGLConfig 的选择（color buffer depth、stencil buffer、MSAA、depth buffer size）直接决定 GPU 渲染带宽和帧缓冲内存占用，但章节完全未提及。在移动设备上，16-bit vs 32-bit color buffer 的选择可以影响 30-50% 的渲染带宽；MSAA 的开启会显著增加 GPU 负载。作为渲染链路章节，这些参数选择是连接「机制理解」和「性能实战」的关键桥梁。

- - 中

- - - EGLConfig 选择对移动 GPU 渲染性能的影响

- - - MSAA 在 Adreno/Mali/PowerVR 上的实际开销

- - - GLSurfaceView.setEGLConfigChooser() 的默认行为和性能影响

- - 18.8, 2.10, 18.6

- - 章节多次提到不同 GPU 厂商的计数器 ID 不同（Adreno/Mali/PowerVR），但未提供任何具体的计数器名称映射或获取方法。开发者无法从文中得知：(1) 如何获取自己设备的可用 GPU 计数器列表；(2) 同一指标（如 GPU Utilization）在不同厂商计数器中的名称和语义差异；(3) 跨设备对比时需要注意的陷阱。

- - 此外，章节缺少工具版本矩阵——各工具支持的最低 Android 版本、GPU 厂商、API（Vulkan/GLES）和功能（系统级/帧级）的交叉对照。

- - 中

- - - Adreno/Mali/PowerVR 三大移动 GPU 的常用计数器名称和语义对比

- - - Perfetto `gpu.counters` 在各厂商驱动中的可用性差异

- - - 各 GPU profiling 工具的版本支持矩阵（Android 版本 × GPU 厂商 × API × 功能层级）

- - - 如何通过 adb shell 或 AGI 查询设备支持的 GPU 计数器列表

- - 14.8, 2.10, 13.3

- - 多进程 ContentProvider (android:process) 的性能特征完全未覆盖。ContentProvider 声明为独立进程时，初始化、IPC、ANR 行为与单进程场景有重大差异。

- - 高

- - - android:process 声明对 ContentProvider 初始化时序的影响

- - - 独立 Provider 进程的 Binder 线程池与主进程的关系

- - - ContentProviderClient.setDetectNotResponding() (Android 11+) 在多进程场景的用法

- - - Provider 进程冷启动对调用方 ANR 的级联影响

- - 1.10, 9.1, 9.2

- - 1. **Dirty Rect 的真实实现机制缺失** —— 章节把 Dirty Rect 简化成“只重绘变化区域”，但 AOSP Surface::lock() 实际还包含旧前台 Buffer 的 copyback、dirty region 扩张、前帧内容不可用时的全量回退。这决定了 Dirty Rect 什么时候真的省事，什么时候反而退化成整帧拷贝 + 局部重绘。

- - 2. **软件渲染仍然受 BufferQueue 背压约束** —— 章节把软件路径描述成“没有复杂同步问题”，但软件 producer 依然会经过 dequeueBuffer()/queueBuffer()，在槽位被 SurfaceFlinger 占住时同样可能卡在 BufferQueue。

- - 高

- - - 研究 frameworks/native/libs/gui/Surface.cpp 中 Surface::lock()/unlockAndPost() 的 dirty region 与 copyBlt 流程

- - - 梳理 software producer 的 fence 传递链：dequeue fence → lockAsync → unlockAsync → queueBuffer

- - - 对比 Android 9 Legacy BufferQueue 与 Android 12+ BLAST 下 software path 的实际差异

- - - 2.13 图形缓冲区管理

- - - 18.1 Android 图形渲染链路全景

- - - 18.2 Android View 标准链路

- - - 18.6 SurfaceView 直出链路

- - HTTP/3 / Cronet 的 Android 落地矩阵缺失。当前章节只把 HTTP/3 描述成“引入 Cronet，APK 增加约 1-2MB”，但没有区分：

- - 1. Cronet by Play Services Provider（GMS 设备，APK 增量极小）

- - 2. Standalone / Bundled Cronet（无 GMS 或需自带内核，体积数 MB）

- - 3. 非 GMS 设备的 fallback 策略（退回 OkHttp HTTP/2、按机型灰度、按网络质量切换）

- - 缺少这一层，读者会把“协议选择”误解成单纯的网络优化问题，而忽略了 Android 生态里的分发、可用性和包体积约束。

- - 高

- - - 梳理 Cronet by Play Services 与 standalone Cronet 的包体积、更新路径、依赖条件差异

- - - 补充 GMS / 非 GMS 设备的 HTTP/3 可用性判断与 fallback 方案

- - - 研究连接迁移、0-RTT、provider 切换在 Android 真实设备上的验证方法

- - - 给出适合 App 侧的“何时值得引入 HTTP/3”决策矩阵

- - - 12.2 网络性能优化

- - - 12.1 APK 体积优化

- - - 16.2 各 Android 版本性能变更追踪

- - - 17.2 SoC 平台差异

- - 1. **HWASAN / MTE 开销数据缺少官方量化来源** — 章节给出了“HWASAN 约 1.5 倍内存开销”“MTE 约 1-5% 性能开销”这类数字，但当前未找到可追溯的官方量化文档。

- - 2. **procrank 在新版本设备上的可用性矩阵缺失** — Android 14+ 的 user / userdebug 设备是否默认提供 `procrank`、是否需要 root 或额外推送二进制，当前没有系统性结论。

- - 3. **malloc hooks 的公开稳定性边界不够清晰** — 已确认 bionic `malloc.h` 中存在 API 28+ 的 hook 声明，但其是否适合作为对外建议能力、不同版本的兼容性与限制仍需进一步梳理。

- - 中高

- - - 搜集官方文档、AOSP 提交记录或 Google/ARM 演讲材料，给出 HWASAN/MTE 开销的可追溯表述。

- - - 建立 `procrank` / `showmap` / `libmeminfo` 在 Android 10-16、user/userdebug、root/非 root 下的可用性矩阵。

- - - 补做 malloc hooks 的 API 稳定性审计，确认是否适合在正文中作为“推荐方案”出现。

- - - 10.1 App 内存分析

- - - 10.3 内存持续增长

- - - 13.1 Perfetto 简介与演进

- - - 14.4 dumpsys 系列命令

- - SurfaceControl NDK 的 FrameTimeline 小节缺少“如何从 AChoreographerFrameCallbackData 的多条 candidate timelines 中选择 vsyncId”的关键解释，也没有说明 ASurfaceTransaction_setDesiredPresentTime() 与 ASurfaceTransaction_setFrameTimeline() 的配合关系。读者容易把 vsyncId 误解为单一回调值，无法建立稳定的帧节拍选择模型。

- - 高

- - - 核对 AChoreographer_postVsyncCallback() / AChoreographerFrameCallbackData_* 系列 NDK 文档和示例

- - - 梳理 callbackData 中 frame timeline count、deadline、expectedPresentTime、preferred timeline 的选择规则

- - - 补一段“desiredPresentTime + setFrameTimeline”的最小可运行范例，并说明 Android 12 与 Android 13+ 的 NDK 能力边界

- - 18.10, 18.2, 2.9

- - 章节把 Overlay、Secure Buffer、SIDEBAND、Tunnel Mode 压成了一条“统一硬件直出链路”，但真实情况是三套机制叠在一起：

- - 1. **标准 DEVICE composition / Overlay**：Buffer 仍经 SurfaceFlinger layer latch，再由 HWC 规划 plane。

- - 2. **受保护内容路径**：是否允许 protected texture / secure GPU post-processing，取决于设备扩展、内容级别和实现策略。

- - 3. **Tunneled playback / sideband stream**：更偏 Android TV / 特定 SoC 的特例路径，音画同步和数据流都与普通 Overlay 不同。

- - 此外，Overlay eligibility 还高度依赖 SoC 与 HWC 代际，YUV/RGBA、plane alpha、rotation、crop、HDR、protected content 的支持矩阵并不统一。

- - 高

- - - 梳理 HWC2.x（HIDL）到 composer3（AIDL）的关键差异，以及对 Overlay / client target 的影响

- - - 建立主流 SoC（Qualcomm / MTK / Tensor）在 YUV/RGBA、alpha、rotation、HDR、protected composition 上的能力矩阵

- - - 补 Tunneled playback / sideband stream 的标准链路，与普通 SurfaceView Overlay 做并列图

- - - 给出 dumpsys SurfaceFlinger / Perfetto 中识别 DEVICE composition、client target、sideband layer 的证据链

- - - 2.6 SurfaceFlinger 与合成

- - - 2.13 图形缓冲区管理（BufferQueue）

- - - 2.16 Sync Fence 框架与帧同步机制

- - - 18.6 SurfaceView 直出链路

- - - 18.10 SurfaceControl API 深入

- - 当前章节把“视频飘移”的改善主要归因到 Android 12+ BLAST / Transaction，但混合渲染真正容易混淆的是三层机制：

- - 1. **位置同步**：SurfaceView 官方文档说明从 Android N 起，window position 已与其他 View 同步更新。

- - 2. **Buffer / 几何协同**：BLAST / Transaction 在后续版本里进一步减少 buffer 更新与几何变化错拍。

- - 3. **透明与挖洞语义**：Android 14+ 才支持 arbitrary alpha blending；更早版本的 alpha 与 composition order 作用点不同，overlapping SurfaceViews 也可能无法正确混合。

- - 同时，官方文档还明确指出 SurfaceView 的可见透明区域基于 layout position，post-layout transform 的 sibling overlay 可能与 surface 不能正确合成。这个约束和章节中的动画/飘移/几何变换话题直接相关，但正文未覆盖。

- - 高

- - - 对照 SurfaceView 官方 API，梳理 Android N、Android 11/12、Android 14+ 三个关键版本的行为差异

- - - 建立“位置同步 vs buffer 同步 vs alpha/composition-order”三层模型，避免把不同层的问题混成一个 BLAST 故事

- - - 补充 post-layout transform、overlay、rounded corner、overlapping SurfaceView 的可用性边界与排查方法

- - - 18.4 Android View 混合渲染链路

- - - 18.6 SurfaceView 直出链路

- - - 18.10 SurfaceControl API 深入

- - - 2.6 SurfaceFlinger 与合成

- - 1. **direct `SurfaceControl.Transaction.setBuffer()` 与 BLAST/BufferQueue 的分层关系** —— 章节把 direct buffer path 与标准 queueBuffer/BBQ 路径混在一起，没有说明两者的连接条件，也没有告诉读者在 Perfetto 里该看哪类证据。

- - 2. **acquire fence / release fence / buffer pool 生命周期** —— 文中只讲 producer 侧的 acquire fence，没有覆盖 release callback、buffer 复用时机、以及 HBR 不自动清空旧内容的语义。

- - 3. **HDR 输出链前提** —— 只提到了 DISPLAY_P3 和“RGBA_F16”，没有展开 `HardwareBuffer.RGBA_FP16`、dataspace/color mode、SurfaceFlinger/HWC 支持链及其 fallback。

- - 高

- - - 验证官方文档与 AOSP 中 HardwareBufferRenderer / SurfaceControl.Transaction 的 direct buffer 语义

- - - 补一段 direct setBuffer 路径的真实 Trace 案例，区分它与 BLASTBufferQueue 路径的可观测点

- - - 总结单 buffer / 双 buffer / buffer pool 的 release fence 复用模式

- - - 梳理 wide color 离屏渲染与真实 HDR composition 的条件矩阵

- - - 18.2

- - - 18.3

- - - 18.10

- - - 2.10

- - - 2.16

- - 游戏引擎在 Perfetto 中的可观测性前提没有系统展开。当前章节把 `SwappyTracer` callback、FrameTimeline、graphics tracing、Unity/Unreal 自定义 marker 混在一起，读者不知道哪些是默认可见，哪些需要 ATrace/TrackEvent，哪些要启用 Vulkan/GLES graphics tracing 或切到 AGI。这个矩阵直接决定 trace 诊断能否真正落地。

- - 高

- - - 梳理 Unity 默认 markers、Unreal trace/Insights、SwappyTracer callback 与 ATrace/TrackEvent 的对应关系

- - - 梳理 Perfetto 默认数据源、graphics tracing、GPU render stage、AGI 的覆盖边界

- - - 给出 60Hz / 90Hz / 120Hz 下启用 Swappy 前后的最小 trace case

- - - 2.17 Frame Pacing Library 与帧节奏控制

- - - 8.9 Android 游戏性能与 Game Mode/State API

- - - 13.1 Perfetto 简介与演进

- - - 18.8 OpenGL ES 渲染链路

- - - 18.9 Vulkan 原生渲染链路

- - 1. **ZSL 能力矩阵缺失** — 章节把 ZSL 写成统一的“环形缓冲区挑帧 + reprocess”模型，但没有区分 `PRIVATE_REPROCESSING`、`YUV_REPROCESSING`、`CONTROL_ENABLE_ZSL`、reprocessable session 以及 CameraX 自己的 ZSL/fallback 路径。读者很难判断某台设备为什么能开 ZSL、为什么另一台只能退化成普通 still capture。

- - 2. **现代 Camera preview / analysis 背压契约缺失** — 没有把 Android 10+ HAL3.5 buffer management、Android 11+ SurfaceView/BLAST、`ImageReader.maxImages` / `acquireLatestImage()` / `image.close()` 这几组决定背压位置的机制串起来。实际排查时，这几个点决定了堵塞到底发生在 HAL、Framework stream 还是 Analysis consumer。

- - 高

- - - 对照 `ICameraDeviceSession` / `ICameraDeviceCallback`、Camera2 API 和 developer docs，梳理 ZSL 的 capability matrix

- - - 补一张 Android 5-9、Android 10+、Android 11+ 的 preview / buffer management 演进图

- - - 收集一条 `ImageReader` consumer 堵塞导致 buffer starvation 的真实 Perfetto case，标出 `maxImages`、回调堆积和 buffer 归还的对应关系

- - 14.9、18.6、2.15

- - 章节把多窗口/PIP 的关键同步问题几乎全部落在 SurfaceFlinger + BLAST 上，但没有覆盖 Android 12+ 的 Shell 控制面：`PipTaskOrganizer`、`TaskOrganizer`、`WindowContainerTransaction`、Shell transitions / SyncEngine 这条链路决定了进入 PIP、窗口 resize、bounds 变更何时提交到 WMS 和 SurfaceFlinger。缺了这一层，读者很难解释为什么同样是 resize，Android 8-10、11、12+ 的表现和 Trace 观察点并不一样。

- - 高

- - - `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/pip/PipTaskOrganizer.java` 与 Shell transition 相关类

- - - `WindowContainerTransaction` / SyncEngine / BLASTBufferQueue 在 resize 同步中的职责边界

- - - PIP / Freeform 场景下 WindowManager trace、Perfetto FrameTimeline、SurfaceFlinger transaction 的联合观察方法

- - 18.18, 18.10, 2.12

- - 文章没有覆盖 Android 上 ANGLE 真正的 driver-selection 机制：GraphicsEnvironment 的全局 / 按包 override、platform allowlist、ANGLE APK 与 system ANGLE 的装载顺序，以及 rules string / debuggable 限制。这个盲区会直接影响“为什么同一 APK 在两台设备上路径不同”的定位。

- - 高

- - - 梳理 `GraphicsEnvironment.queryAngleChoice()` 与 `frameworks/native/opengl/libs/EGL/Loader.cpp` 的完整选路顺序

- - - 区分 system ANGLE、ANGLE APK、native GLES driver、vendor Vulkan driver 的职责边界

- - - 补一组 native GLES / ANGLE 对照证据：`GL_RENDERER`、settings、maps、Perfetto / AGI

- - - 确认 Android 15 Developer Options 与非 Pixel / 非 debuggable 场景的限制条件

- - - 2.14 图形 API 演进与选择策略

- - - 18.8 OpenGL ES 渲染链路

- - - 18.9 Vulkan 原生渲染链路

- - 章节把 ANR 和广播超时几乎都压进 AMS 视角，遗漏了现代 system_server 中真正负责判责的中间层：WMS `AnrController` 的 Input ANR 归因，以及 `BroadcastQueueImpl` 的 soft-timeout / CPU-delay 扩展逻辑。读者按当前章节去排查，容易直接盯 AMS，而忽略 WMS 焦点仲裁和广播队列的软超时延展。

- - 高

- - - 梳理 `InputDispatcher` → `InputManagerCallback` → `AnrController` → `ActivityRecord/AMS` 的现代 Input ANR 判责链

- - - 研究 `BroadcastQueueImpl.deliveryTimeoutSoftLocked()` 如何根据 runnable-but-waiting 的 CPU delay 延长硬超时

- - - 给出一个 no-focused-window ANR 和一个 broadcast CPU-starved 超时的 Perfetto/trace 案例

- - - 3.1 Input 事件分发全流程

- - - 9.1 ANR 设计思想

- - - 9.2 ANR 类型与触发条件

- - 1. **secondary zygote / ABI 路由缺失** — 章节提到 secondary zygote，但没有解释 `openZygoteSocketIfNeeded(abi)` 如何在 primary / secondary 之间选择，也没有说明 32 位 / 64 位应用在双 ABI 设备上的建进程入口差异。

- - 2. **USAP 与 child zygote 边界缺失** — 章节把 USAP、App Zygote、WebViewZygote 放在同一节，但没有点明 USAP pool 只适用于 primary / secondary zygote，child zygote 不支持 USAP pool。现代启动分析里，这会直接影响对 isolated service / WebView provider 启动路径的判断。

- - 高

- - - 对照 `ZygoteProcess.openZygoteSocketIfNeeded(abi)` 梳理 primary / secondary zygote 的 ABI 选择逻辑

- - - 梳理 USAP pool 仅在 primary / secondary zygote 可用的源码依据和版本边界

- - - 补一个 dual-ABI 设备的 Perfetto / event log 观察示例，说明普通 App、isolated service、WebView provider 各走哪条创建路径

- - - 1.4

- - - 1.17

- - - 8.2

- - - 8.3

- - 章节把七类问题和六类代码模式直接推广到 Android 8-17，但缺少按 Android 版本（尤其 Android 12+ 后台限制、SplashScreen、FrameTimeline、高刷新率普及）和 App 规模分层的实证数据。这样会让读者误以为这些占比和优先级在所有版本、所有体量的应用上都稳定不变。

- - 高

- - - 按 Android 8-11 / 12-14 / 15-17 分层整理性能问题与 contributing factors 的分布变化

- - - 对比中小应用与大型 App 在响应性、内存、启动问题上的差异

- - - 补充能映射到 §15.5 线上监控、§16.2 版本演进、§8.1 / §9.1 观测面的案例

- - 15.5, 16.2, 8.1, 9.1

- - 章节已经覆盖 Normal Mixer / FAST Mixer / MMAP，但仍缺 DirectOutputThread / OffloadThread / MmapPlaybackThread 的完整对照，导致 `flushWrittenFramesFromPosition()`、`getCodecProvenance()`、AAudio offloaded playback 这些 offload only 能力没有落回到明确的线程模型与选路图。

- - 高

- - - 回源 Android 16/17 的 AAudio offloaded playback API（如 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED`）与传统 `AudioTrack` offload 的边界

- - - 补齐 AudioPolicyManager output profile 到 PlaybackThread / OffloadThread / MmapThread 的选路图和 `dumpsys audio` 可观测点

- - - 给出 1 份 Perfetto + `dumpsys audio` 联合样例，区分 fast path、mmap path、offload path

- - 1.16, 5.6, 14.4, 16.5

- - 章节已经覆盖 Flutter Android 渲染主干，但对 Android embedding 的三个关键边界仍然不够清楚：1) Merged Platform Model 下 Main(UI+Platform) 与 engine 内部 task runner 的职责边界；2) `RenderMode.surface` / `texture` / `image` 与 Platform Views composition mode 的组合关系；3) Hybrid Composition 与 Texture Layer Hybrid Composition 在 WebView、Map、SurfaceView 场景里的实际代价，包括滚动 jank、a11y、magnifier 和变换约束。

- - 高

- - - 回源 Flutter Android embedding 官方文档和 engine 源码，梳理 thread merge 后 Main / Raster / IO 的可观测边界

- - - 单独整理 `RenderMode` 与 Platform Views composition mode 的对照表，区分默认路径与少见但重要的 `RenderMode.image`

- - - 补 1 份 WebView 或 Map 的真实 Perfetto trace，展示 Hybrid Composition 与 Texture Layer Hybrid Composition 的线程、合成和卡顿差异

- - - 2.11 Flutter 渲染管线与性能

- - - 18.6 SurfaceView 直出链路

- - - 18.7 TextureView 合成链路

- - - 7.11 WebView 渲染性能与优化

- - 章节已经单列 Android 16 Cloud Compilation / SDM，但当前没有把 PMS、ART Service、Play 分发之间的真实集成点讲清，也没有说明 cloud compilation 未命中时会如何回落到本机 dexopt。设备侧可观测信号同样缺失，读者无法判断一次安装到底走了哪条编译路径。

- - 高

- - - 回源 Android 16 的官方开发者博客、I/O 资料或 AOSP / Play 文档，确认 SDM 的签名、校验主体和加载入口

- - - 补一条设备侧观测路径，说明如何用 `cmd package art dump`、logcat 或编译产物布局判断是否命中 cloud compilation

- - - 对比 Play 分发、侧载、无可用 profile 三类场景下的 fallback 行为

- - 1.7, 1.9, 8.3, 16.5

- - 章节没有拆开 native mutex contention、condition variable wait 和 Binder wait queue 的诊断边界，导致 `futex_*` 观察点容易被统一解释成“锁竞争”。这会直接影响 Perfetto 现场判断，尤其是 `pthread_cond_wait` 这类条件同步等待。

- - 高

- - - 梳理 `pthread_mutex`、`pthread_cond_wait`、Binder wait queue 在 Perfetto 中的最小可观测差异

- - - 给出 owner / waiter、谓词等待、reply 等待三类场景的诊断矩阵和示例 trace

- - - 补充 Java monitor 所需的最小 trace 配置，避免 `android_monitor_contention` 空结果被误判为“没有锁竞争”

- - 1.5, 1.13, 13.3, 13.6

- - ------

- - --------

- - ------------

- - 13.1

- - - External AI review

- - perf 事件（Callstack Sampling）配置差异

- - 中

- - 简介中提及了 Trace Processor 和 Data source，但未说明 native profiling (perf) 与 atrace 的边界，这可作为后续章节深化的方向。

- - 13.1

- - - External AI review

- - ------

- - --------

- - ------------

- - 13.2

- - - External AI review

- - perf 事件（Callstack Sampling）配置差异

- - 中

- - 无

- - 13.2

- - - External AI review

- - ---

- - ---

- - ---

- - 14.1

- - - External AI review

- - `ProfilingManager` 的线上数据脱敏 (Redaction) 机制

- - 中

- - 官方提到 profiling 结果通常会通过 redactor 脱敏后返回给 App。这一机制对于隐私安全很重要，建议后续研究。

- - 14.1

- - - External AI review

- - ---

- - ---

- - ---

- - 14.10

- - - External AI review

- - sched_ext 在 Android 16 GKI 6.12 上的实际编译状态

- - 高

- - 虽然 Linux 6.12 合入了 sched_ext，但 GKI 的 defconfig 是否开启了 `CONFIG_SCHED_CLASS_EXT` 需要确认。

- - 14.10

- - - External AI review

- - Android 17 GKI 6.18 的具体新增 eBPF 功能

- - 中

- - Kernel 6.18 可能带来新的 BPF helper 和 map 类型。

- - 14.10

- - - External AI review

- - ---

- - ---

- - ---

- - 14.11

- - - External AI review

- - Android 17 ODPM Power Rail 的新增项

- - 低

- - 是否有新的 Power Rail 可以被 Power Profiler 读取。

- - 14.11

- - - External AI review

- - ---

- - ---

- - ---

- - 14.2

- - - External AI review

- - off-CPU 火焰图的直观解读

- - 中

- - 文中提到了 off-CPU profiling，但如果没有对比图，读者可能难以直观理解 on/off 区域在 HTML 报告中是如何分布和区分的。

- - 14.2

- - - External AI review

- - ---

- - ---

- - ---

- - 14.3

- - - External AI review

- - MTE (Memory Tagging Extension) 在 Android 15 上的默认策略

- - 中

- - 文中提到 MTE 可用异步模式，可以进一步调研 Android 15 是否对开发者开启了更严格的默认 MTE 检查。

- - 14.3

- - - External AI review

- - ---

- - ---

- - ---

- - 14.4

- - - External AI review

- - `dumpsys meminfo` 统计口径与 `smaps` PSS 差异

- - 低

- - dumpsys 从内核读取数据时，针对 GFX 等硬件内存的统计口径在各厂商可能存在差异。

- - 14.4

- - - External AI review

- - ---

- - ---

- - ---

- - 14.5

- - - External AI review

- - Booster 对 AGP 8+ 的最新支持状态

- - 高

- - 调研 Booster 官方是否已经完全切完了 Instrumentation API，这对于新项目的选型至关重要。

- - 14.5

- - - External AI review

- - ---

- - ---

- - ---

- - 14.6

- - - External AI review

- - Macrobenchmark 1.3+ 新增指标

- - 低

- - 最新版的 Macrobenchmark 库是否新增了 Memory 或 Energy 类指标。

- - 14.6

- - - External AI review

- - ---

- - ---

- - ---

- - 14.7

- - - External AI review

- - `version 36.1` 标注的含义

- - 中

- - 部分触发器（`APP_REQUEST_RUNNING_TRACE`、`KILL_FORCE_STOP`、`KILL_RECENTS`、`KILL_TASK_MANAGER`）标注的是 `version 36.1` 而非标准 `API level`，可能代表 Mainline 模块更新。需要确认这在实际设备上的可用性。

- - 14.7

- - - External AI review

- - ---

- - ---

- - ---

- - 14.8

- - - External AI review

- - Sokatoa 开源后的实际使用体验

- - 中

- - 文章写作时 Sokatoa 尚在开源计划阶段，建议后续补充开源后的实际操作步骤和功能验证。

- - 14.8

- - - External AI review

- - ---

- - ---

- - ---

- - 14.9

- - - External AI review

- - Android 14+ Camera Extension API 的性能影响

- - 低

- - Camera Extensions (Night Mode, HDR 等) 是否引入了新的 HAL 延迟模式。

- - 14.9

- - - External AI review

- - 1. **独立 SurfaceControl 合成的触发条件矩阵缺失** — 章节提到 provider、feature、场景条件会影响 WebView 是否切到独立 child layer，但没有整理 provider 版本、feature flag、trace 证据三者之间的对应关系。没有这张矩阵，现场很难判断“当前设备到底有没有这条模式”。

- - 2. **第三方 WebView SDK 的真实渲染实现缺失** — X5、UC 等 SDK 被概括成 Custom TextureView 路径，但没有版本矩阵、Layer dump 证据和 trace 识别方法。对国内 App 场景，这会直接影响链路判别和优化方向。

- - 高

- - - 梳理 WebView provider 版本、feature flag 与独立 child layer / OOP rasterization 的对应关系

- - - 在 Android 10-16 上抓取最小 trace，对照 `dumpsys SurfaceFlinger` 验证独立 WebView layer 的出现条件

- - - 收集 X5 / UC 等第三方 SDK 的公开资料、版本说明和实际 trace / layer dump 证据

- - - 补充 `WebViewCompat.getCurrentWebViewPackage()` 与 `adb shell dumpsys webviewupdate` 的现场验证步骤

- - - 7.11 WebView 渲染性能与优化

- - - 18.10 SurfaceControl API 深入

- - - 18.6 SurfaceView 直出链路

- - - 18.7 TextureView 合成链路

- - 1. **GPU / Graphics 内存归属矩阵缺失** — 章节把 Native Heap、Graphics、Hardware Bitmap、memtrack、`dumpsys meminfo`/`dumpsys gpu` 混在一起讲，但没有给出 Android 8-16 上“哪类图形内存出现在什么统计口径里”的矩阵。缺这张矩阵，读者很难判断 Hardware Bitmap、Surface、GraphicBuffer 到底该看 Java Heap、Native Heap 还是 Graphics/memtrack。

- - 2. **MTE 的 Android 平台边界缺失** — ARM FEAT_MTE3/4、Android 13+ 设备支持、`android:memtagMode` 能力和 Scudo 集成被揉成一条时间线，缺少“架构特性”和“Android 面向 App 的可用能力”两层边界。

- - 高

- - - 梳理 Android 8-16 上 software bitmap / native bitmap / hardware bitmap / Surface / GraphicBuffer 在 Java Heap、Native Heap、Graphics、GL、memtrack、PSS 中的可见性矩阵

- - - 对照 `dumpsys meminfo`、`dumpsys gpu`、Perfetto process memory track、Memtrack HAL 文档，整理一套现场排查口径

- - - 拆分 ARM MTE 架构时间线与 Android 平台时间线，分别标注 Android 13/14/15/16 的设备支持范围、manifest 能力和调试方式

- - - 补 Pixel / GKI / NDK 官方资料，明确 sync / async 与架构层 Asymmetric 的边界

- - - 4.5 App 内存优化

- - - 10.1 App 内存分析

- - - 2.9 渲染机制的版本演进

- - - 4.2 Linux 内核内存管理

- - Android 12+ 的 FrameTimeline 责任归因矩阵没有并入本节原因树。当前流程仍以 VSYNC-app / doFrame 为统一入口，缺少 `AppDeadlineMissed`、`SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed`、`DisplayHAL`、`PredictionError`、`BufferStuffing` 与 MainThread / RenderThread / SurfaceFlinger / Display HAL 根因之间的映射。

- - 高

- - - 对照 Perfetto FrameTimeline 文档，整理 `JankType` → App / SurfaceFlinger / Display HAL 的归因矩阵

- - - 补 1 份 Android 12+ 实际 trace 观察清单，说明 `Actual Timeline`、`On time finish`、`Present Type`、`GPU Composition` 的使用顺序

- - - 将 Android 5-11 的 VSYNC / doFrame 路径与 Android 12+ 的 FrameTimeline 路径分开描述

- - - 7.1 卡顿定义

- - - 7.3 卡顿分析方法论

- - - 2.6 SurfaceFlinger 与合成

- - API 33+ 的公开帧时间线入口缺位。正文已经解释了框架内部 `doFrame(..., VsyncEventData)`、`vsyncId`、deadline 和 Frame Timeline，但没有把应用侧真正可用的 `postVsyncCallback(VsyncCallback)` / `FrameData` / `FrameTimeline` 接上来，读者很容易把内部结构和公开 API 混为一谈。

- - 高

- - - 梳理 `Choreographer.postVsyncCallback(VsyncCallback)`、`FrameData`、`FrameTimeline` 的 API 33+ 公开方法与返回字段

- - - 对照 AOSP 内部 `DisplayEventReceiver.VsyncEventData`，解释公开 `FrameData` 能拿到什么、拿不到什么

- - - 补 1 份最小示例，展示如何在 App 侧读取 preferred timeline / expected presentation time，并与 Perfetto FrameTimeline 对齐

- - - 明确 `FrameCallback#doFrame(long)` 与 `VsyncCallback#onVsync(FrameData)` 的使用边界

- - - 2.3 VSync 机制

- - - 2.18 Adaptive Refresh Rate 与动态帧率控制

- - - 2.19 刷新率切换与帧率适配性能

- - - 13.1 Perfetto 基础与抓取

- - 正文已经建议在 `JNI_OnLoad()` 缓存 `jclass` / `jmethodID`，也解释了 native 线程 attach/detach，但没有补上 perf-jni 官方文档里的关键边界：natively-created attached thread 上 `FindClass()` 会从 system class loader 开始，App 类查找可能失败。缺这条因果链，读者容易把“缓存 ID”当成经验技巧，而不是和 ClassLoader 语义直接相关的硬边界。

- - 高

- - - 对照 perf-jni 官方文档整理 `JNI_OnLoad()` 缓存、Java 传入 `Class` / `ClassLoader`、Java-started thread 三种规避方案

- - - 补 1 个最小错误示例：native worker thread 中 `FindClass("com/example/Decoder")` 失败，再对照修复版本

- - - 说明这条边界和线程 attach/detach、ID 缓存、`FindClass()` 热路径禁用之间的关系

- - - 1.15 JNI/NDK 性能优化

- - 章节还缺一张“Android 11-14 多刷新率 / mode switching → Android 15-QPR1+ ARR → Android 16 Display 查询 API”的分层矩阵，也缺一张对应的 Perfetto 观察矩阵。现在正文把 VRR、ARR、模式切换、慢帧显示延长写成一条直线，读者很难判断自己遇到的是面板能力、系统策略，还是 app / SurfaceFlinger deadline miss。

- - 高

- - - 对比 Android 11-14 多刷新率路径与 Android 15-QPR1+ ARR 的正式能力边界

- - - 补齐 Display / View / Surface 三层 API 的时间线，区分查询 API、投票 API、Surface hint

- - - 整理 Perfetto 观察矩阵：VSYNC-app、VSYNC-sf、expected_frame_timeline_slice、actual_frame_timeline_slice、surface/display frame token、refresh-rate selection slice

- - - 2.3 VSync 机制

- - - 2.18 Adaptive Refresh Rate 与动态帧率控制

- - - 2.19 刷新率切换与帧率适配性能

- - - 18.19 可变刷新率渲染管线

- - 章节把 ashmem、SharedMemory、GraphicBuffer、FMQ 和 dmabuf-heaps 放进同一条“共享内存演进线”，但没有拆开三类完全不同的对象：1) 应用通用共享内存（ashmem / MemoryFile / SharedMemory，若追内核演进还要看 memfd）；2) 图形 / 媒体 DMA buffer allocator（ION → dmabuf-heaps）；3) HAL 高频零拷贝队列（FMQ）。缺少这层边界后，读者很难判断 CursorWindow、BufferQueue、AIDL/HIDL HAL 的 fd 传递到底各自落在哪条路径上。

- - 高

- - - 回源 `android/os/SharedMemory.java`、`android_os_SharedMemory.cpp`、`MemoryFile.java`，确认应用通用共享内存仍然走哪套实现

- - - 梳理 ION → dmabuf-heaps 在 GraphicBuffer / Gralloc / BufferQueue 路线中的真实版本节点

- - - 给出一张“对象类型 → fd 传递方式 → 典型场景 → Trace / dumpsys 观察点”的对照表

- - - 1.10

- - - 2.13

- - - 2.15

- - - 16.1

- - “Project Mainline”小节把 AutoFDO 只写成 GKI / kernel OTA 路线，缺少 userspace/native AutoFDO 与 kernel AutoFDO 的拆分。官方 2026 AutoFDO blog 已明确 userspace native binaries 与 GKI kernel 使用不同的 profile 来源和 rollout 方式，§1.12 也已经按这两条路线展开。现有写法会让读者误把 userspace native AutoFDO 也映射到 `android15-6.6` / `android16-6.12` 这类 GKI 目录。

- - 高

- - - 对照 Google AutoFDO 官方 blog 中 userspace native binaries 与 GKI kernel rollout 的原始表述

- - - 补一张 “Mainline / Play 编译 / userspace AutoFDO / kernel AutoFDO” 交付路径对照表

- - - 明确 `android15-6.6`、`android16-6.12` 目录只覆盖 kernel profile，不代表 userspace native rollout

- - - 1.12 AutoFDO 反馈导向编译优化

- - - 16.1 Google 官方的性能优化思路

- - - 16.4 Android 17 + Kernel 6.12 系统级性能优化

- - Macrobenchmark 作为竞品对比工具未被深入介绍。文章在第 394 行标注了「[待补充: 使用 Macrobenchmark 库实现自动化启动和滑动测试的完整示例]」。Macrobenchmark 提供了标准化的启动和滑动性能测试框架，支持自动 CompilationMode 控制（Speed、SpeedProfile、None），这对竞品对比中的编译状态控制是一个更优雅的方案。

- - 中

- - - 补充使用 Macrobenchmark StartupTimingMetric 和 FrameTimingMetric 做竞品对比的示例

- - - 展示如何用 CompilationMode 控制编译状态以保证公平对比

- - - 与手动 am start -W 方案的精度和可重复性对比

- - - 15.4（竞品分析方法）

- - - 14.1（Macrobenchmark 详细介绍）

- - - Claude Opus 4.6 (Thinking) 外部 review

- - ADPF Hint Session 实战

- - 高

- - 研究 App 如何通过 ADPF 告知系统工作负载以避免随机掉帧。

- - 7.3

- - - 外部 AI review (2026-04-19-10-03-jank-methodology-external-review.md)

- - Android 16 System-triggered Profiling

- - 中

- - 研究系统如何在检测到卡顿时自动触发并保存 Trace 到 `/data/misc/perfetto-traces`。

- - 7.3

- - - 外部 AI review (2026-04-19-10-03-jank-methodology-external-review.md)

- - Android 17 DeliQueue 机制

- - 中

- - 深入 AOSP 源码分析 MessageQueue 无锁化对 Handler 消息延迟的改善程度。

- - 7.3

- - - 外部 AI review (2026-04-19-10-03-jank-methodology-external-review.md)

- - ------

- - ------

- - -------

- - 7.5

- - - 外部 AI review (2026-04-19-10-05-optimization-external-review.md)

- - Compose Pausable Composition

- - 高

- - Android 17 (Compose 1.10) 引入的可暂停重组对长列表平滑度的贡献

- - 7.5

- - - 外部 AI review (2026-04-19-10-05-optimization-external-review.md)

- - FrameTimeline 与 ARR

- - 中

- - 在 ARR 开启时，Perfetto 中 FrameTimeline 预测帧耗时的变化规律

- - 7.5

- - - 外部 AI review (2026-04-19-10-05-optimization-external-review.md)

- - ------

- - ------

- - -------

- - 7.6

- - - 外部 AI review (2026-04-19-10-06-case-studies-external-review.md)

- - 16 KB 页支持 (Android 15)

- - 中

- - 研究其对内存分配效率及 NDK 应用的影响

- - 7.6

- - - 外部 AI review (2026-04-19-10-06-case-studies-external-review.md)

- - Variable Refresh Rate (VRR)

- - 高

- - 120Hz 下 8.3ms 预算对 `sync` 阻塞的放大效应

- - 7.6

- - - 外部 AI review (2026-04-19-10-06-case-studies-external-review.md)

- - Bitmap.prepareToDraw()

- - 中

- - 异步上传纹理以缓解 `syncFrameState` 阻塞

- - 7.6

- - - 外部 AI review (2026-04-19-10-06-case-studies-external-review.md)

- - ------

- - ----------

- - --------------

- - 7.7

- - - 外部 AI review (2026-04-19-10-07-compose-performance-external-review.md)

- - Pausable Composition 状态恢复机制

- - 高

- - 研究 SlotTable 在暂停点如何保存上下文，以及是否会造成过期的状态读取。

- - 7.7

- - - 外部 AI review (2026-04-19-10-07-compose-performance-external-review.md)

- - Strong Skipping 与 Lambda Memoization

- - 中

- - 深入研究编译器如何自动为捕获不稳定变量的 Lambda 包裹 remember。

- - 7.7

- - - 外部 AI review (2026-04-19-10-07-compose-performance-external-review.md)

- - LookaheadScope 性能边界

- - 中

- - 研究其在复杂共享元素动画中对 Layout 阶段耗时的具体影响。

- - 7.7

- - - 外部 AI review (2026-04-19-10-07-compose-performance-external-review.md)

- - ------

- - ------

- - -------

- - 7.8

- - - 外部 AI review (2026-04-19-10-08-recyclerview-performance-external-review.md)

- - Prefetch 与自定义 LayoutManager 的对接

- - 中

- - 研究 `LayoutManager.collectAdjacentPrefetchPositions` 的实现要求

- - 7.8

- - - 外部 AI review (2026-04-19-10-08-recyclerview-performance-external-review.md)

- - 144Hz/165Hz 高刷新率下的 GapWorker 表现

- - 低

- - 测试极短 Gap 时间（<2ms）下的预取放弃率

- - 7.8

- - - 外部 AI review (2026-04-19-10-08-recyclerview-performance-external-review.md)

- - Ultra HDR Gainmap 合成

- - 高

- - 研究 `Gainmap` 在 GPU 侧的合成成本及 CPU 回退风险

- - 7.10

- - - 外部 AI review (2026-04-19-10-10-image-bitmap-performance-external-review.md)

- - AGSL 自定义滤镜

- - 中

- - 探索 `RuntimeColorFilter` 替代传统 Bitmap 像素操作的性能优势

- - 7.10

- - - 外部 AI review (2026-04-19-10-10-image-bitmap-performance-external-review.md)

- - 16KB 内存页影响

- - 低

- - 分析 Android 15 强制 16KB 页对大图加载的 PSS 影响

- - 7.10

- - - 外部 AI review (2026-04-19-10-10-image-bitmap-performance-external-review.md)

- - ------

- - ----------

- - --------------

- - 7.12

- - - 外部 AI review (2026-04-19-10-13-systemui-performance-external-review.md)

- - Flexiglass / Scene Framework

- - 高

- - 了解 SystemUI 如何通过 `SceneInteractor` 管理状态栏、抽屉、锁屏的切换逻辑。

- - 7.12

- - - 外部 AI review (2026-04-19-10-13-systemui-performance-external-review.md)

- - Notification Pipeline v2 过滤机制

- - 中

- - 研究 `NotifFilter` 和 `NotifPromoter` 如何在绑定前影响性能。

- - 7.12

- - - 外部 AI review (2026-04-19-10-13-systemui-performance-external-review.md)

- - ------

- - ----------

- - --------------

- - 7.14

- - - 外部 AI review (2026-04-19-10-14-gaps-dynamic-analysis-external-review.md)

- - 混淆代码路径重建

- - 高

- - 研究 GAPS 如何配合 mapping.txt 或利用语义恢复技术分析混淆后的方法路径

- - 7.14

- - - 外部 AI review (2026-04-19-10-14-gaps-dynamic-analysis-external-review.md)

- - Android 17 新型 UI 组件适配

- - 中

- - 研究 Compose/Compose-Multiplatform 等非传统 View 层级对 GAPS 静态 ID 提取的影响

- - 7.14

- - - 外部 AI review (2026-04-19-10-14-gaps-dynamic-analysis-external-review.md)

- - ------

- - ----------

- - --------------

- - unknown

- - - 外部 AI review (2026-04-19-10-README-external-review.md)

- - ARR (Adaptive Refresh Rate) 与 VSync 解耦

- - 高

- - 研究 HWC 3.0 如何在单模式内通过 VSync 步长调整刷新率

- - unknown

- - - 外部 AI review (2026-04-19-10-README-external-review.md)

- - ProfilingManager 系统触发采样

- - 中

- - 研究 Android 16 如何根据卡顿自动触发 Perfetto 追踪

- - unknown

- - - 外部 AI review (2026-04-19-10-README-external-review.md)

- - RecyclerView 1.4 的 ARR 自动适配

- - 高

- - 分析其如何通过 WindowInsets 接口向 SF 请求动态刷新率

- - unknown

- - - 外部 AI review (2026-04-19-10-README-external-review.md)

- - ADPF Hint Session (GPU)

- - 高

- - 研究 Android 15 如何通过 `PerformanceHintManager` 报告 GPU 工作时长以优化响应速度。

- - Gemini 外部 review

- - ProfilingManager

- - 中

- - Android 15 引入的自动触发 Perfetto 机制，用于捕捉生产环境的响应速度异常。

- - Gemini 外部 review

- - 16KB Page Size

- - 低

- - Android 15/16 内存页大小变化对底层 I/O 响应的影响（虽然主要影响启动，但涉及整机响应）。

- - Gemini 外部 review

- - 章节

- - 高

- - 7.3

- - Gemini 外部 review

- - 盲区描述

- - 高

- - Android 16 引入的 `AppJankStats` 如何取代部分 `FrameMetrics` 职责。

- - Gemini 外部 review

- - 建议补充方向

- - 高

- - 在 FrameMetrics 章节后增加“未来演进：AppJankStats”小节。

- - Gemini 外部 review

- - 章节

- - 高

- - `05-optimization.md`

- - Gemini 外部 review

- - 盲区描述

- - 高

- - Compose 1.10 的 Pausable Composition。

- - Gemini 外部 review

- - 重要程度

- - 高

- - 高。

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - 调研 Compose 1.10 如何实现在渲染时间不足时暂停并在下一帧恢复。

- - Gemini 外部 review

- - 章节

- - 高

- - 7.6 案例二

- - **盲区**：`SharedPreferences` 启动阻塞。

- - **建议研究**：在案例二补强 SP 阻塞的分析，提供 `awaitLoadedLocked` 的 Trace 特征。

- - Gemini 外部 review

- - 盲区描述

- - 高

- - Compose 1.9 引入的 `CacheWindow` API 对 Lazy 预取的影响。

- - Gemini 外部 review

- - 重要程度

- - 高

- - 高

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - 结合 Pausable Composition，研究其如何量化预取窗口以平衡内存与流畅度。

- - Gemini 外部 review

- - 源码锚点

- - 高

- - `androidx.recyclerview.widget.GapWorker`

- - Gemini 外部 review

- - 关键路径

- - 高

- - `GapWorker.java` -> `prefetchPositionWithDeadline()`

- - Gemini 外部 review

- - 技术结论

- - 高

- - 预取不仅依赖时间戳，更依赖 `willCreateInTime` 和 `willBindInTime` 对历史成本的实时评估。

- - Gemini 外部 review

- - 资产价值

- - 高

- - 解释了为什么有时候 Trace 里有预取动作但没有后续 Bind，这是系统在“舍车保帅”防止卡顿。

- - Gemini 外部 review

- - 章节

- - 高

- - `01-jank-definition.md`

- - Gemini 外部 review

- - 盲区描述

- - 高

- - Android 16 ARR 深度适配机制

- - Gemini 外部 review

- - 重要程度

- - 高

- - 高

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - RecyclerView 如何利用新 API 动态提频。

- - Gemini 外部 review

- - 章节

- - 高

- - 9.1

- - Gemini 外部 review

- - 盲区描述

- - 高

- - system_server 处理 ANR 时的“二次挂起”风险。

- - Gemini 外部 review

- - 重要程度

- - 高

- - 中

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - 调研 `AnrHelper` 虽然异步化了，但其调用的 `dumpStackTraces` 是否仍会竞争全局锁。

- - Gemini 外部 review

- - MTE (Memory Tagging Extension)

- - 高

- - Android 11+ 在 ARMv9 设备上通过硬件标签检测 Native 泄漏的机制

- - Gemini 外部 review

- - GWP-ASan

- - 中

- - 针对生产环境的低开销 Native 堆损坏检测

- - Gemini 外部 review

- - Heap Redaction

- - 中

- - Android 15+ 如何在 Dump 过程中移除 PII 隐私数据

- - Gemini 外部 review

- - 章节

- - 高

- - 10.2

- - Gemini 外部 review

- - 盲区描述

- - 高

- - 硬件级内存检测（MTE/HWASan）在内存泄漏排查中的角色。

- - Gemini 外部 review

- - 重要程度

- - 高

- - 高

- - Gemini 外部 review

- - 可能关联章节

- - 高

- - 4.2 Linux 内存管理, 4.6 内存版本演进

- - Gemini 外部 review

- - AnrConsumer / AnrController

- - 中

- - Android 11+ 系统内部处理 ANR 的新链路（不再仅仅是直接写文件）

- - Gemini 外部 review

- - Android 17 Lock-free MessageQueue

- - 高

- - Android 17 的无锁消息队列如何改变 `nativePollOnce` 的堆栈表现

- - Gemini 外部 review

- - Input ANR 5s 超时分档

- - 中

- - Android 15 对不同 Input 事件（点击 vs 手势）的超时判定差异

- - Gemini 外部 review

- - 一手资料

- - 高

- - Android 17 无锁 MessageQueue (DeliQueue)。

- - Gemini 外部 review

- - 关键结论

- - 高

- - Android 17 消除了 `withContext(Dispatchers.Main)` 的锁争用，后台协程切回主线程性能提升极大（高并发下最高 5000 倍）。

- - Gemini 外部 review

- - Trace 观察点

- - 高

- - 在 Android 17 上，主线程 `MessageQueue#next` 不再会因为后台线程 `enqueueMessage` 而进入 `Waiting` 状态。

- - Gemini 外部 review

- - DeliQueue 机制

- - 高

- - 建议在第 1.4 章（Binder）或第 1.2 章（Handler）中建立关联，解释无锁队列如何减少多线程竞争。

- - Gemini 外部 review

- - 章节

- - 高

- - 9.7

- - Gemini 外部 review

- - 盲区描述

- - 高

- - Android 15+ 可能引入的针对 `binderfs` 的更严苛权限限制对 ANR 分析的影响。

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - 调研新版本 `logd` 和 `dumpstate` 如何在没有 root 权限时导出 Binder 状态。

- - Gemini 外部 review

- - 核心 SQL (Codec2 聚合分析)

- - 高

- - ```sql

- - SELECT name, AVG(dur)/1e6 as avg_ms, MAX(dur)/1e6 as max_ms

- - FROM slice

- - WHERE name LIKE 'C2Component::process%' OR name LIKE 'C2Component::onWorkDone%'

- - GROUP BY name;

- - ```

- - Gemini 外部 review

- - 关键源码路径

- - 高

- - - `frameworks/native/services/surfaceflinger/CompositionEngine/src/Layer.cpp` (Sideband 传递逻辑)

- - - `frameworks/av/media/libstagefright/MediaCodec.cpp` (异步回调分发逻辑)

- - Gemini 外部 review

- - 章节

- - 高

- - 8.8 系统触发式性能追踪

- - Gemini 外部 review

- - 盲区描述

- - 高

- - 系统层级（System-wide）对 Profiling 请求的具体限流策略。

- - Gemini 外部 review

- - 重要程度

- - 高

- - 中

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - 阅读 `ProfilingService.java` 中关于 `checkLimit` 或 `isQuotaExceeded` 的逻辑，找出 `DeviceConfig` 对应的命名空间。

- - Gemini 外部 review

- - 章节

- - 高

- - 8.9

- - Gemini 外部 review

- - 盲区描述

- - 高

- - VRR 与 `preferredFrameRateCategory` 的协同机制。

- - Gemini 外部 review

- - 重要程度

- - 高

- - 中

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - SurfaceFlinger 内部对 Category 映射到具体刷新率的权重算法。

- - Gemini 外部 review

- - 章节

- - 高

- - `01-anr-design.md`

- - Gemini 外部 review

- - 盲区描述

- - 高

- - Android 17 无锁队列对三方监控库的兼容性挑战。

- - Gemini 外部 review

- - 建议研究方向

- - 高

- - 调研如何不依赖反射 `mMessages` 来获取主线程消息积压情况。

- - Gemini 外部 review

- - 1. **Android 16 Headroom API**：替代过时的 onTrimMemory 细分级别的新机制，具体 API 形态和触发条件待研究。

- - 2. **RSS 优先监控策略**：PSS 采集在 Android 14+ 受 Throttling 限制（可能返回 5 分钟前缓存数据），需转向 RSS 趋势监控或组合方案。

- - 3. **MTE (Memory Tagging Extension) 开销**：在支持 MTE 的硬件（如 Pixel 8/9）上对内存增长的影响。

- - 高（Headroom API）/ 中（RSS）/ 低（MTE）

- - - AOSP SystemHealthManager.java 查看 Headroom API 实现

- - - 对比 RSS 与 PSS 在高频采样下的精度差异

- - - Perfetto Native Heap Profiler 在 16KB 页面设备上的 Trace 表现差异

- - - 10.3, 10.4

- - - Gemini 外部 review (2026-04-19)

- - 补充以下新盲区（已存在 compactd/onTrimMemory 盲区）：

- - 1. **16KB Page Size 对 RSS 的量化影响**：Android 15 引入后物理内存增加约 9%，meminfo 输出因对齐变粗产生数值跳变。

- - 2. **ZRAM 后台重压缩触发条件**：Android 15 支持 recomp_algorithm（主算法 LZ4 + 重压缩 ZSTD），空闲时重新压缩 ZRAM 页面。

- - 3. **PSI 统计窗口厂商定制化**：常见国产厂商（小米、OPPO）对 psi_partial_stall_ms 的魔改情况。

- - 高（16KB）/ 中（ZRAM、PSI）

- - - Google 官方 16KB Page 性能白皮书

- - - zram_config 在 Android 15 中的默认策略

- - - 国产厂商 PSI 定制调研

- - - 10.3, 10.4

- - - Gemini 外部 review (2026-04-19)

- - 1. **MGLRU 开启后的 kswapd0 调度**：extra_free_kbytes 调优策略是否需要改变？

- - 2. **GPU 私有 ioctl 监控**：如何通过 eBPF 监控 /dev/dri/renderD128 的私有接口调用。

- - 3. **硬件加速与 Canvas.saveLayer**：View.setLayerType 与 Canvas.saveLayer 在不同 Android 版本的差异。

- - 高（MGLRU）/ 中（GPU ioctl）/ 高（saveLayer）

- - - mg_lru_gen 及其对 allocstall 指标的影响

- - - eBPF 监控 GPU 驱动私有接口

- - - View.setLayerType 版本差异对比

- - - 10.4, 10.5

- - - Gemini 外部 review (2026-04-19)

- - 1. **Generational CMC 内部细节**：Android 16 的分代 CMC 如何在 Userfaultfd 基础上划分 Young/Old 区。

- - 2. **Lock-free MessageQueue 的影响**：Android 17 的 lock-free 机制是否缓解了高频消息导致的抖动感。

- - 高（Generational CMC）/ 中（Lock-free MQ）

- - - 对比 Generational CC 与 Generational CMC 在相同抖动负载下的 CPU 功耗

- - - art/runtime/gc/collector/mark_compact.cc CMC 实现

- - - 10.6

- - - Gemini 外部 review (2026-04-19)

- - 1. **Android 15+ memfd 对 CursorWindow 的影响**：从 ashmem 迁移到 memfd 后的性能和安全性（SELinux）具体约束。

- - 2. **SQLite 3.37+ STRICT 表**：Android 15+ 携带的 SQLite 版本是否支持 STRICT 及对 Room 的影响。

- - 中

- - - 查看 AOSP system/core/libcutils 对 sys.use_memfd 的最新判断逻辑

- - - STRICT 表对 Room Schema 的影响

- - - 10.7

- - - Gemini 外部 review (2026-04-19)

- - 1. **BatteryUsageStats 架构重构**：Android 12 如何将 BatteryStatsImpl 原始数据封装为 BatteryConsumer 对象。

- - 2. **系统服务的 WorkSource 传递链路**：DownloadManager/LocationManager 如何将 UID 链传递给 BatteryStats。

- - 3. **CPU Scaling Policy 与 Cluster 的解耦**：Android 16 为何弃用 getAveragePowerForCpuCluster 转向 ScalingPolicy。

- - 高

- - - BatteryUsageStatsProvider.java 架构

- - - 追踪 DownloadManager 的 WorkSource 传递路径

- - - CpuPowerStatsCollector.java (Android 16 新增类)

- - - 11.1, 11.5

- - - Gemini 外部 review (2026-04-19)

- - 补充以下新盲区（已存在 5G Radio/FCM 盲区）：

- - 1. **5G C-DRX 参数对 App 心跳频率的敏感度**：drx-InactivityTimer 对不同频率的影响。

- - 2. **Android 16 16KB Page Size 对功耗的影响**：NDK 应用在 16KB 页下是否存在缓存未命中导致的额外 CPU 功耗。

- - 3. **厂商 ODPM 数据格式**：IPowerStats HAL 接口定义。

- - 高（5G C-DRX）/ 中（16KB 功耗、ODPM）

- - - 5G EN-DC 双连接功耗突增现象

- - - perfetto.dev 针对 5G Power Rails 的分析文档

- - - 11.1, 11.2, 11.4

- - - Gemini 外部 review (2026-04-19)

- - 1. **SystemSuspend 的引用计数与死锁风险**：IWakeLock.aidl 的调用路径。

- - 2. **Android 17 对"频繁唤醒"的 Quota 算法**：QuotaController 在 PowerManagement 中的新应用。

- - 高（Quota）/ 中（SystemSuspend）

- - - system/hardware/interfaces/suspend 的 AIDL 实现

- - - Android 17 QuotaController 源码分析

- - - 11.5

- - - Gemini 外部 review (2026-04-19)

- - 1. **磁盘占用 vs 下载体积**：ART AOT 编译产物对 /data 分区的压力。

- - 2. **R8 Full Mode 对反射的隐形破坏**：android.enableR8.fullMode 开启后对 Gson/Retrofit 的潜在影响。

- - 3. **AXML 的内存对齐优化**：AOSP ResXMLTree 的二进制对齐对膨胀效率的影响。

- - 高（R8 反射）/ 中（AXML、磁盘占用）

- - - libs/androidfw/ResourceTypes.cpp ResTable 解析逻辑

- - - R8 Full Mode 兼容性矩阵

- - - 12.1

- - - Gemini 外部 review (2026-04-19)

- - 1. **OkHttp 5 setPolicy 预建连** — OkHttp 5 引入 ConnectionPool.setPolicy，允许针对特定地址配置最小连接数（proactive open）。对冷启动首页请求等极低延迟场景有重要实战价值，但章节未涉及。

- - 2. **DoH3 与运营商防火墙兼容性** — 部分运营商可能拦截 UDP 443 导致 DoH3 回退到传统 DNS。移动端 DNS 优化的实际可靠性受此影响。

- - 3. **HttpEngine 缓存共享** — Android 14 HttpEngine 是否与 Chrome 浏览器或其他 App 共享缓存尚不明确，影响缓存策略设计。

- - 中

- - - OkHttp 5 setPolicy 在 App 冷启动网络加速中的实战效果

- - - DoH3 在国内运营商环境下的兼容性与回退策略

- - - Android 14 HttpEngine 缓存隔离机制与共享边界

- - - 5G RRC_INACTIVE 状态对功耗和延迟的优化（原文仅覆盖 4G 状态机）

- - - 12.2 网络性能优化

- - - 11.1 功耗模型

- - - 2026-04-19-12-03-network-performance-deep-external-review.md

- - 1. **CursorWindow 共享内存机制演进** — 文章仅提到 ashmem FD 共享，但 Android 12+ 已默认使用 memfd 替代 ashmem。Android 15+ GKI 强制使用 memfd，memfd 通过 F_SEAL_WRITE 密封机制替代了 ashmem 的 ioctl 权限控制。现代设备 /proc/pid/maps 中看到的是 memfd:CursorWindow 而非 /dev/ashmem。

- - 2. **SQLite STRICT 表** — Android 15+ 携带的 SQLite 版本（3.37+）支持 STRICT 表，对 Room 的数据类型约束和性能影响尚未覆盖。

- - 3. **config_cursorWindowSize OEM 定制** — frameworks/base/core/res/res/values/config.xml 中的 cursorWindowSize 值，不同厂商（华为、小米）可能有不同的定制。

- - 中（memfd 版本演进）/ 中（STRICT 表）/ 低（OEM 定制）

- - - 查看 AOSP system/core/libcutils 源码中 sys.use_memfd 的判断逻辑

- - - 验证 Android 15+ 上 memfd 的 SELinux 约束

- - - 梳理主流 OEM 对 cursorWindowSize 的定制情况

- - - 10.7 SQLite / Room 性能优化

- - - 10.1 App 内存分析

- - - 6.2 文件系统

- - - 外部 AI review: 2026-04-19-11-07-sqlite-room-performance-external-review.md

- - 1. **OkHttp 0-RTT 实战打通** — OkHttp 并无简单 API 开关启用 0-RTT，需通过 Conscrypt API（Conscrypt.setUseSessionTickets）干预 SSLSocket 创建，且需自行控制仅幂等请求发送 early data 防止重放攻击

- - 2. **平台级 ECH 对应用层 Socket 的透明代理机制** — Android 17 平台层 DNS 劫持/代理机制（Bionic 层改动）如何向 OkHttp 提供 ECH 透明传输

- - 高（0-RTT）/ 中（ECH 透明代理）

- - - 研究 Conscrypt 与 OkHttp 结合的 0-RTT 最佳实践与拦截器配置，补充代码示例

- - - 研究 Android 17 平台层的 DNS 劫持/代理机制

- - - 12.3 网络性能深入

- - - Gemini 外部 review

- - WebView 在 Android 14+ / Vulkan 启用后的 GL Functor 行为变化。HWUI 默认开启 Vulkan 渲染后，WebView 的传统 GL 绘制调用链（DrawGlInfo）如何通过 ANGLE 或过渡层完成适配。

- - 中

- - - AOSP frameworks/webview/ 和 Chromium android_webview/ 源码

- - - DrawGlInfo 结构体在不同 Android 版本的演进

- - - 第 18 章 WebView 专题

- - - Gemini 外部 review

- - 1. **BBQ 内部并发与锁竞争** — BLASTBufferQueue 内部处理 queueBuffer、acquireNextBuffer 和 transactionCallback 时存在的锁机制，极端情况可能导致 App 阻塞

- - 2. **VSync Phase Offset 设计** — DispSync / VsyncModulator 如何控制 App 和 SF 的唤醒时间差（App 通常早于 SF 唤醒），对 Triple Buffering 流水线优势至关重要

- - 高（BBQ 锁竞争）/ 中（Phase Offset）

- - - 深入分析 BLASTBufferQueue.cpp 锁竞争场景

- - - 研究 DispSync 如何为 App 和 SF 分配不同偏移量

- - - 18.1 渲染管线概览

- - - 2.3 VSync 机制

- - - Gemini 外部 review

- - 各家 GPU 供应商（Adreno, Mali）的 Gralloc/Mapper 对 CPU 映射 GraphicBuffer 时的 Cache 策略，以及这对 Surface.cpp::copyBlt 的具体性能影响数值。DMA-BUF 分配的 GraphicBuffer 通常为 uncached/write-combined，CPU 读写性能惩罚远高于普通 RAM。

- - 高

- - - AOSP Gralloc 接口实现及实际 Trace 对比

- - - 不同供应商的 SW_READ_OFTEN 标志下的 DMA-BUF Cache 行为

- - - 2.13 BufferQueue 内存管理

- - - Gemini 外部 review

- - 1. **Android 14 SurfaceSyncGroup** — 跨窗口、多 Surface 动画中的具体编排流程，如何收集、等待、合并多个底层 Transaction

- - 2. **SurfaceView vs TextureView 性能边界** — 什么情况下必须回退到 TextureView（如需对视频进行 Shader 处理或 View 级层级穿插）

- - 高（SurfaceSyncGroup）/ 中（TextureView 边界）

- - - 阅读 SurfaceSyncGroup.java，分析其多 Transaction 合并流程

- - - SurfaceView/TextureView 混合渲染的实战选型决策树

- - - 系统同步机制、动画子系统

- - - Gemini 外部 review

- - Vulkan 渲染后端在同进程多窗口切换时的底层耗时机制（区别于 EGL eglMakeCurrent）。Android 10+ 默认启用 Vulkan 渲染后，需研究 VulkanManager 对应的 Surface 切换逻辑（VkSwapchainKHR acquire/present 争抢）。

- - 中

- - - AOSP hwui/renderthread/VulkanManager.cpp

- - - Vulkan 多 Surface 场景下的 swapchain 管理

- - - 第 2 部分底层图形 API 章节

- - - Gemini 外部 review

- - 章节已经写出了 `createChoreographerThread()` 的内部回退树，但还没有把“公开初始化前提”和“内部线程回退实现”拆开。当前缺的不是更多概念，而是一张接入边界矩阵：OpenGL 公开入口 `SwappyGL_init(JNIEnv*, jobject)`、Vulkan 公开入口 `SwappyVk_initAndGetRefreshCycleDuration(JNIEnv*, jobject, ...)`、`SwappyGL_setWindow()` / `SwappyVk_setWindow()` 的窗口句柄前提、以及 API 16-23 / 24-30 / 31+ 在 Choreographer 与 refresh-rate callback 上的差异。如果这块不补，读者很容易把 `vm == nullptr` / `NoChoreographerThread` 误读成“任意 native-only 场景都能直接照抄”的接入方式。

- - 高

- - - 对照 `include/swappy/swappyGL.h`、`include/swappy/swappyVk.h`，整理公开 API 的 JNI / Activity / ANativeWindow 前置条件

- - - 对照 `games-frame-pacing/common/ChoreographerThread.cpp`，梳理 internal fallback 触发条件，区分实现细节与 public contract

- - - 输出一张版本矩阵，明确 API 16-23、24-30、31+ 在 Java Choreographer、NDK Choreographer、DisplayManager helper、native refresh-rate callback 上的边界

- - - 补 1 组“窗口未配置时 frame-rate vote 不生效”的源码+trace 证据链

- - - 2.3 VSync 信号机制

- - - 2.4 Choreographer 编舞者

- - - 2.16 Sync Fence 同步栅栏

- - - 2.18 Adaptive Refresh Rate 与动态帧率控制

- - APK 编译原理及 aapt2 内部机制；HTTPDNS 实践及底层防劫持原理；网络耗时在 Perfetto 中的特征；App Bundle 与 PackageManagerService 的交互。

- - 高

- - - cs.android.com 检索 frameworks/base/tools/aapt2 以及 R8/D8 编译器的字节码优化机制

- - - 结合 OkHttp 拦截器及系统层 DNS 解析机制 (bionic/libc/dns/) 分析 HTTPDNS

- - - 分析网络请求时的唤醒机制及基带模块耗时的 Trace 表现

- - - Play Store 分发机制及 frameworks/base/services/core/java/com/android/server/pm/ 中的处理逻辑

- - - 12.1 APK 体积优化

- - - 12.3 网络性能深入

- - - 2026-04-19-14-12.0-external-review.md

- - vkQueuePresentKHR 的底层 IPC 阻塞风险：当 BufferQueue 满导致 dequeueBuffer 阻塞时，如何反向阻塞 Vulkan 提交流程。Frame Pacing 与 FrameTimeline 的映射逻辑。

- - 高

- - - AOSP libvulkan QueuePresentKHR 函数中对 BufferQueue 的超时控制

- - - Swappy 库如何通过 SurfaceControl API 使用 Choreographer Vsync Id 与 FrameTimeline 握手

- - - 18.1 渲染管线概览

- - - 18.10 SurfaceControl API

- - - 2026-04-19-14-18.9-external-review.md

- - 纯 NDK 下的跨进程 ASurfaceControl 传递与跨进程 Reparent 机制。Java 层可通过 Parcelable 传递 SurfaceControl，但 NDK 层是否有原生 IPC 手段尚不明确。FrameTimeline VsyncId 溯源。

- - 高

- - - 确认 NDK 层是否有原生 IPC 手段（如 libbinder_ndk 中的映射），或是否必须借道 JNI

- - - VsyncId 在 Choreographer 中的生成逻辑及 SF 消费时机

- - - 18.4 混合渲染

- - - 18.12 Flutter 渲染链路

- - - 2026-04-19-14-18.10-external-review.md

- - ANGLE 翻译层的 Shader/Pipeline Cache 落盘与跨进程/重启复用机制，与原生 GLES shader cache 的差异。ANGLE 的分层决策树（全局设置 > 包级别 opt-in/out > Game Mode > 平台 rules）。

- - 中

- - - AOSP external/angle 中的 cache 管理逻辑及 Vulkan Pipeline Cache 交互

- - - 18.9 Vulkan 原生渲染链路

- - - 2026-04-19-14-18.11-external-review.md

- - Flutter Raster 线程与宿主 RenderThread 在 TextureView 模式下的 VSync 拍频错位导致的一帧延迟。HC 模式下 SurfaceControl 的 Layer 分配。

- - 高

- - - Perfetto trace 实证，结合不同帧率场景（60fps vs 120fps）下的表现差异

- - - 结合 dumpsys SurfaceFlinger 分析 Flutter 叠加层与原生 View 的 Layer 层级

- - - 18.7 TextureView 原理

- - - 18.10 SurfaceControl API

- - - 2026-04-19-14-18.12-external-review.md

- - WebView GPU/Viz 线程组在单进程/多进程模式下的 Perfetto 追踪特征。CrGpuMain、VizCompositorThread 与 App RenderThread 在 Functor 和 SurfaceControl 两种模式下的时序区别。

- - 高

- - - 结合 Perfetto Trace 截图分析 CrGpuMain、VizCompositorThread 与 App RenderThread 的时序差异

- - - Hardware Draw Functor (DrawFn)：Android 10+ WebViewFunctor.h 的底层实现及 Vulkan 兼容性

- - - 7.11 WebView 渲染性能与优化

- - - 18.10 SurfaceControl API

- - - 2026-04-19-14-18.13-external-review.md

- - 1. **PiP / 视频类窗口的 FrameTimeline 观测边界** — Perfetto FrameTimeline 文档明确写明该能力要求 Android 12+，且 `SurfaceView` 当前不支持。当前章节把多窗口诊断主线过度收敛到三类 jank，却没有告诉读者 PiP、视频小窗、地图小窗这类高频多窗口场景为什么经常要改看 layer snapshots、BufferQueue 或 `gpu.renderstages`。

- - 2. **多显示器 pacesetter 调度链** — 当前章节把 connected display 简化成“多一套 display pipeline”，但 AOSP `SurfaceFlinger::commit(PhysicalDisplayId pacesetterId, const scheduler::FrameTargets&)` 已表明多显示帧目标由 pacesetter display 驱动。外接显示器刷新率不同、display mode 变化或 HAL present 抖动时，jank 可能来自跨 display 的调度耦合。external-review 已命中过这个方向，正文仍未闭环。

- - 高

- - - 对照 Perfetto FrameTimeline 文档，补 PiP / SurfaceView 场景的观测替代路径：layer snapshots、BufferQueue、`gpu.renderstages`、播放器轨道

- - - 结合 `SurfaceFlinger::commit(...)`、display scheduler 和 mode 切换路径，梳理 pacesetter display 如何影响内外屏 frame target

- - - 抓同一设备的 full-screen / split-screen / connected-display 对照 trace，补 layer 数、jank 类型和 display mode 的联动证据

- - 2.20, 2.6, 2.12, 2.13, 2.18, 7.4

- - Simpleperf 跨版本能力矩阵没有展开。正文已覆盖 Android 5-16，却没有把 Android 5-8 的 native/debbugable 限制、Android 9 的 Java 栈采样、Android 10 的 `profileable`、以及 user / userdebug 在 PMU 与 off-CPU 采样上的差异串成可执行矩阵。

- - 高

- - - 核对 simpleperf README 与 Android Developers 文档，整理 Android 5-8 / 9 / 10+ 的能力差异

- - - 补 user、userdebug、debuggable、profileable 四类运行条件的支持矩阵

- - - 补一组 Java 栈采样与 off-CPU 采样的版本边界示例

- - - 14.1

- - - 13.6

- - - 15.6

- - Graphics / dma-buf 内存没有独立诊断分支。正文已经提到 Graphic Buffer、Graphics bucket 和 `/dev/dmabuf`，但没有说明这类内存为何不在 malloc heap 里、该怎样用 `dumpsys meminfo`、`showmap`、SurfaceFlinger 与 Perfetto GPU 轨道闭环定位。

- - 高

- - - 补 Graphics bucket、Graphic Buffer、dma-buf 与 Native Heap 的边界说明

- - - 整理 `dumpsys meminfo` Graphics、`showmap` `/dev/dmabuf` 与 SurfaceFlinger layer 观察点

- - - 增加与 §2.15 DMA-BUF、§10.1 App 内存分析、§7.10 图片加载章节的联动

- - - 2.15

- - - 10.1

- - - 7.10

- - 章节没有覆盖 Baseline Profiles 在 Compose 首次启动、首帧渲染和库代码 AOT 编译中的作用。当前内容几乎把优化重心全部放在重组与稳定性上，缺少安装时编译这条与 Compose 运行时同样关键的性能轴。

- - 高

- - - 梳理 Compose 官方性能文档中 Baseline Profiles 的推荐位置和适用场景

- - - 用 Macrobenchmark 生成 app-specific Baseline Profile，并总结与库自带 profile 的边界

- - - 补一个“首启卡顿 vs 运行期重组卡顿”的诊断分流表

- - - 核对 Baseline Profiles 对 Compose 首次进入页面、首次滚动、首次动画的改善证据

- - - 7.7 Jetpack Compose 性能优化

- - - 8.1 响应速度原理

- - TextureView 对硬件加速的强依赖没有被纳入章节主线。`TextureView.java` 明确要求 hardware accelerated window，软件渲染模式下会直接不出图。当前稿件缺少这条边界，导致黑屏 / 不更新问题没有首要排查入口。

- - 高

- - - 回源 `TextureView.java` 的类注释与 `draw(Canvas)` / `getTextureLayer()` 路径，说明为什么软件渲染窗口无法承载 TextureView

- - - 补一个“TextureView 黑屏排查清单”，把硬件加速开关、Window/Activity 级禁用场景、兼容模式列为首项

- - - 与 SurfaceView 做一张兼容性矩阵，区分性能、变换能力和硬件加速前置条件

- - - 18.6 SurfaceView 直出链路

- - - 18.7 TextureView 合成链路

- - - 18.8 OpenGL ES 渲染链路

- - 章节把“输入安全边界”集中在 InputFilter、无障碍过滤和事件注入，但缺少官方主线里的 obscured touch / untrusted touch 防护链路。当前正文没有覆盖 `MotionEvent.FLAG_WINDOW_IS_OBSCURED` / `FLAG_WINDOW_IS_PARTIALLY_OBSCURED`、`View.setFilterTouchesWhenObscured()` / `onFilterTouchEventForSecurity()`，也没有纳入 Android 12 引入的 `BLOCK_UNTRUSTED_TOUCHES_MODE` 系统级阻断策略。这样会让读者理解“谁能拦截/注入输入”，却看不到 Android 防 tapjacking / overlay 诱导触摸的核心边界。

- - 高

- - - 核对 `MotionEvent.FLAG_WINDOW_IS_OBSCURED` 与 `FLAG_WINDOW_IS_PARTIALLY_OBSCURED` 在 App 侧的判定语义

- - - 补 `View.setFilterTouchesWhenObscured()` 与 `onFilterTouchEventForSecurity()` 的适用边界

- - - 梳理 Android 12+ `BLOCK_UNTRUSTED_TOUCHES_MODE`、`notifyUntrustedTouch()` 与系统遮挡触摸阻断策略

- - - 给一段 overlay / toast / accessibility 叠层场景下的 trace 或行为验证

- - - 3.1 Input 事件分发全流程

- - - 9.1 ANR 设计思想

- - - 9.2 ANR 类型与触发机制

- - 1. **16KB page size / gralloc 对齐对 Hardware Layer backing store 的影响** — recent external-review 已命中。章节把显存代价泛化成“多一块 GPU 纹理”，但没有解释 Android 15/16 上 16KB page size 与 buffer 对齐如何放大小尺寸 layer 的 slack space / 内部碎片。

- - 2. **现代 HWUI 的资源预算与回收边界** — recent external-review 已命中。缺少 layer residency、cache purge、budget pressure 的机制说明，也没有给出 Perfetto 或 GPU memory 观察点。

- - 高

- - - 梳理 Android 15/16 的 16KB page size、gralloc 对齐与 Hardware Layer backing store 的对应关系

- - - 追踪 HWUI / Skia resource cache 在 budget pressure 下的 purge 触发点与可观测信号

- - - 补一组大面积 layer + 内存压力实验，给出 Trace / GPU memory 对照

- - - 2.15 DMA-BUF 与 Gralloc

- - - 4.7 16KB Page Size 适配与性能

- - - 18.17 HardwareBuffer 直接渲染

- - 1. **Android 12+ Font APEX / `com.android.fonts` 的版本边界** — recent external-review 已命中。章节讲了系统 emoji 与 emoji2，但没有交代系统字体和 emoji 可通过 Play system update 更新后的分层变化。

- - 2. **Variable font / font variation settings 的性能边界** — recent external-review 已命中。优化实践未覆盖 variable font，缺少对宽度中性轴（如 GRAD）与 relayout 关系的说明。

- - 高

- - - 梳理 Font APEX、系统 emoji、EmojiCompat、downloadable font provider 的时间线与职责边界

- - - 补 `setFontVariationSettings()` / Compose 字体轴配置在 TextView 与 Compose 中的性能观察点

- - - 实测 width-neutral 轴与 `wght` / `wdth` 轴对测量与重排的影响差异

- - - 7.12 View 体系性能

- - - 12.1 APK 体积优化（字体资源与 downloadable font）

- - - 16.2 各 Android 版本性能变更追踪

- - AAudio offloaded playback 已进入正文主线，但 API level、入口常量、PCM/压缩 payload 支持边界与设备 capability 仍未完成正式核验。

- - 高

- - - 核对 Android 16/17 API diff 中 AAudio/AudioTrack/offload 相关新增常量与 builder 入口

- - - 补查 `dumpsys audio`、AudioPolicy profile 与 HAL capability 如何区分 MMAP / direct / offload

- - - 确认 Oboe 与 AAudio power-saving/offloaded 模式的映射关系及最低 API level

- - 1.16、5.6、16.5
  - 当前公开口径只够确认 Android 17 通过 `OPEN_EYE_DROPPER` Intent 打开系统级取色流程，但章节缺少 SystemUI 侧的真实实现细节，例如截图来源、放大镜/取色 UI 的宿主组件、结果如何安全回传给发起应用，以及这些步骤在 Trace 中能看到哪些进程和 slice。
  - 高

- 搜索 `OPEN_EYE_DROPPER` 在 AOSP / SystemUI 中的处理入口，确认宿主 Activity 或 Controller

- 梳理截图隔离、取色 UI、结果回传这三段实际调用链

- 抓一条从发起 Intent 到收到 `Intent.EXTRA_COLOR` 的真实 Perfetto / logcat case，确认可观测的进程与 slice
  - 18.21, 2.6, 8.2
  - ch18 README 大纲作为渲染链路全景指南，严重缺失底层核心机制的章节索引：
  - 1. BufferQueue (IGraphicBufferProducer/Consumer) 跨进程图像流转机制 — 连接 App 渲染与 SurfaceFlinger 合成的核心桥梁
  - 2. Frame Timeline (Android 12+) 掉帧追踪体系 — Perfetto 中分析 Jank 的核心 UI 轨道
  - 3. BLASTBufferQueue 事务同步机制 (Android 11+) — 替代传统 BufferQueue 的现代方案
  - 4. AGSL (Android Graphics Shading Language, Android 13+) — 实现复杂 UI 效果的标准途径
  - 高

- AOSP `frameworks/native/libs/gui/BufferQueue.cpp` 及 IGraphicBufferProducer 接口模型

- Perfetto 官方文档 Frame Timeline，AOSP `surfaceflinger/FrameTimeline` 模块

- Android 11+ BLASTBufferQueue.cpp 与 SurfaceControl Transaction 结合机制

- Android 13+ AGSL 官方文档、RenderEffect 运行机制及对 GPU 性能的影响

- Android 12+ 可更新 GPU 驱动与 Game Mode API

- 18.1 (渲染管线总览)

- 18.2 (标准 View 渲染路径)

- 18.10 (SurfaceControl API)

- 2.13 (BufferQueue)

- 2.6 (SurfaceFlinger)

- 2.17 (Frame Pacing)

- Gemini 外部 review: 2026-04-20-11-18.0-external-review.md

- `frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp`

- 关键类：TokenManager, DisplayFrame, SurfaceFrame

- Frame Timeline 调用链：Choreographer → VsyncId → queueBuffer → SF 匹配 Expected vs Actual → 判定 App/SF Deadline Miss

- 版本差异：Android 12 引入，替代 Vsync-App/SF 切片观测

- Perfetto 观察点：Expected Timeline (绿框) vs Actual Timeline (红/蓝框) 叠加对比



## [2026-04-20] 13.0 Perfetto README — 知识盲区

### 盲区描述
13.0 Perfetto README 综述未体现 2026 年平台化特征。需提炼 eBPF (UprobeStats) 和 AndroidX Tracing 2.0 对 2026 版 Trace 体系的影响。目录缺失 13.8/13.9/13.10 三篇核心章节。

### 重要程度
中高

### 建议研究方向
- eBPF (UprobeStats) 在 Android 16/17 Perfetto 中的集成状态
- AndroidX Tracing 2.0 新能力与 Perfetto 的配合关系
- 2026 年 Trace 体系平台化趋势总结
- 补全 README 目录条目 13.8/13.9/13.10

### 关联章节
- 13.1
- 14.10
- 15.6

### 外部 review 来源
- Gemini 外部 review (2026-04-20-13-README-external-review.md)


## [2026-04-21] 14.8 GPU 图形调试与分析工具 — 知识盲区

### 盲区描述
AGI 底层架构演进方向不明确。AGI 传统基于 GAPID 追踪框架，Samsung Sokatoa 基于 GFXReconstruct，但 Google 是否将 AGI 的 Frame Profiler 底层完全切换为 GFXReconstruct 缺乏官方确认。

### 重要程度
高

### 建议研究方向
- 确认 AGI 是否正在或已经合入 GFXReconstruct 相关代码（cs.android.com 搜索 AGI 源码）
- 搜索 "Android GPU Inspector" "GFXReconstruct" 关键词获取官方声明

### 关联章节
- 14.8
- 14.10

### 外部 review 来源
- Gemini 外部 review (2026-04-20)

---

## [2026-04-21] 14.8 GPU 图形调试与分析工具 — ANGLE 版本差异

### 盲区描述
Android 15/16/17 中 ANGLE 作为默认 GLES 驱动的渐进策略细节未梳理。需要明确 `ro.gfx.angle.supported` 和默认驱动选择的属性变化逻辑。

### 重要程度
中

### 建议研究方向
- AOSP 中关于 ANGLE 默认驱动选择属性的版本变化逻辑
- Android 15 Developer Options 中 ANGLE 切换机制

### 关联章节
- 14.8
- 2.6 SurfaceFlinger 与合成

### 外部 review 来源
- Gemini 外部 review (2026-04-20)

---

## [2026-04-21] 14.9 Android Camera 性能与 Perfetto 分析 — 知识盲区

### 盲区描述
CameraMetadataNative 的内存回收机制演进未覆盖。Android 10+ 已使用 NativeAllocationRegistry 替代 Finalizer，App 层实际拿到 TotalCaptureResult 而非 CameraMetadataNative，无法直接 close。

### 重要程度
高

### 建议研究方向
- 查阅 AOSP 中 CameraMetadataNative.java 的 NativeAllocationRegistry 使用情况
- 梳理 Camera API 中 CaptureResult 持有与 GC 触发机制
- 搜索: AOSP CameraMetadataNative NativeAllocationRegistry

### 关联章节
- 14.9
- 11.2 App 耗电优化

### 外部 review 来源
- Gemini 外部 review (2026-04-20)

---

## [2026-04-21] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 知识盲区

### 盲区描述
bpftrace 在 AOSP 的集成现状未准确描述。自 Android 12/13 起 AOSP external/bpftrace 已引入，userdebug/eng 版本可通过 m bpftrace 编译运行。

### 重要程度
中

### 建议研究方向
- 查阅 external/bpftrace 在 Android 14/15 的编译支持和系统预置情况
- 搜索: AOSP external/bpftrace

### 关联章节
- 14.10

### 外部 review 来源
- Gemini 外部 review (2026-04-20)

## [2026-04-21] 16.3 AOSP 源码编译与调试环境 — Pixel 真机刷机路径在 2025+ 的公开支持矩阵

### 盲区描述
章节已经触到 2025 年后 Pixel 设备树 / 驱动公开策略变化，但缺少一份可执行的“哪些 Pixel 型号还能按官方公开材料完成 AOSP 真机验证”的矩阵。当前正文把设备树、driver binaries、kernel history 混写，读者很难判断真机验证边界。

### 重要程度
高

### 建议研究方向
- 核对 developers.google.com/android/drivers 当前仍公开的 Pixel / Nexus 驱动包范围
- 梳理 Android 16 之后 Pixel 设备树与 kernel history 的公开边界
- 形成“Cuttlefish / 老 Pixel / 新 Pixel”三类验证路径建议

### 关联章节
16.2, 16.3

## [2026-04-21] 16.4 Android 17 + Kernel 6.12 系统级性能优化 — android16-6.12 的真实 rollout 边界与 io_uring 用户态可见性

### 盲区描述
章节有大量 2026 新信息，但最关键的两条边界还没实锤：一是哪些设备 / 分支真的拿到 `android16-6.12` 或 AutoFDO rollout；二是 Android 17 上 io_uring 到底只对系统进程开放，还是已有可公开验证的 userspace 接口。

### 重要程度
高

### 建议研究方向
- 整理 GKI `android15-6.6` / `android16-6.12` / 未来分支与设备更新关系
- 核对 source.android.com GKI release builds 与设备兼容说明
- 核对 Android 上 io_uring 的 SELinux / app sandbox 限制，以及 `external/liburing` 的公开使用场景

### 关联章节
16.2, 16.4, 6.3
