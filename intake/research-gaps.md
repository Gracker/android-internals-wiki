## [2026-04-15] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
1. **InputChannel 创建失败处理机制** - 文章完全未提及当 socketpair 创建失败或 App 端无法正确接收时的错误处理和恢复机制。这对系统稳定性和故障排查至关重要。

2. **Input 系统与 SurfaceFlinger 协作** - 缺少 Input 系统与 SurfaceFlinger 在窗口可见性变化、合成时机等方面的交互机制。在全屏/分屏/多窗口场景中，两个系统的协作对性能影响很大。

### 重要程度
高 - 这两个机制都是系统级的关键协作点，对性能优化和问题诊断有直接影响

### 建议研究方向
- 研究 InputChannel 失败时的系统行为和错误恢复策略
- 分析 Input 事件如何影响 SurfaceFlinger 的合成决策
- 添加这两个协作场景的 Trace 分析案例

### 关联章节
- 2.6 SurfaceFlinger 与合成
- 3.2 触摸响应的性能分析
- 9.1 ANR 设计思想

## [2026-04-15] 2.2 帧率与刷新率 — 知识盲区

### 盲区描述
1. **VRR vs ARR 概念混淆** — 章节中 LTPO 面板的 VRR（面板级可变刷新率）和 Android 15 的 ARR（系统级自适应刷新率）被混在一起讨论。ARR 是 SurfaceFlinger 中新增的决策逻辑，利用 VRR 面板能力做更精细的帧率控制。两者是不同层级的概念，需要明确区分。

2. **SurfaceFlinger 刷新率选择算法** — 章节将算法简化为"整除"规则，但 AOSP 中 RefreshRateSelector 的实际实现使用多维度评分系统（帧率匹配度、功耗影响、切换开销、是否无缝）。需要补充更准确的算法描述。

3. **VSync 周期动态变化对 Choreographer 的影响** — 当 SurfaceFlinger 切换刷新率时（如 60Hz→120Hz），VSync-app 间隔变化，正在排队的 VSync 订阅如何处理？

### 重要程度
高

### 建议研究方向
- 梳理 VRR（面板能力）和 ARR（Android 系统策略）的分层关系
- 研究 AOSP RefreshRateSelector 的评分算法核心逻辑
- 验证 Choreographer 在 VSync 周期变化时的行为

### 关联章节
- 2.3 VSync 机制
- 2.6 SurfaceFlinger 与合成
- 2.18 Adaptive Refresh Rate 与动态帧率控制


## [2026-04-15] 14.4 dumpsys 系列命令 — 知识盲区

### 盲区描述
1. **dumpsys cpuinfo 缺失** — 作为 CPU 占用快速排查的基本工具，在性能分析章节中完全未提及。cpuinfo 可以查看每个进程的 CPU 使用率、负载因子，是 dumpsys 工具链中与 meminfo 同等重要的诊断命令。
2. **framestats/gfxinfo 版本行为差异** — gfxinfo reset 在某些版本清除全局统计、framestats 列定义在不同 API level 有变化、聚合统计字段（如 Number Slow bitmap uploads）有引入版本要求。这些版本差异在实战中是高频踩坑点。

### 重要程度
高（cpuinfo）/ 中（版本差异）

### 建议研究方向
- 补充 dumpsys cpuinfo 的输出结构、关键字段（CPU usage per process、load averages）和使用场景
- 梳理 gfxinfo 各字段在不同 Android 版本的变化矩阵
- 确认 gfxinfo reset 在 Android 12+ 是否已修复为仅清除指定进程

### 关联章节
- 5.1 Linux 进程调度基础
- 7.3 卡顿分析方法论
- 13.1 Perfetto 简介与演进



## [2026-04-15] 6.2 文件系统 — 知识盲区

### 盲区描述
f2fs 的 Adaptive Logging 机制（在 normal logging 和 threaded logging 之间动态切换）对性能行为有重大影响，但在 6.2 章节中完全未提及。当存储空间不足时，f2fs 从 normal logging（copy-and-compaction）切换到 threaded logging（在 dirty segment 中复用空间），性能特征会发生质变——这直接关系到"手机存储快满时为什么突然变卡"的用户体验问题。

### 重要程度
高

### 建议研究方向
- f2fs 源码中 `fs/f2fs/segment.c` 的日志策略选择逻辑
- f2fs 官方文档中关于 adaptive logging 的说明
- 在不同空间占用率下 f2fs I/O 延迟的 benchmark 数据
- 对 Perfetto Trace 中识别 threaded logging 模式的方法

### 关联章节
6.2（文件系统）、6.3（I/O 调度）、7.1（流畅性）

## [2026-04-15] 6.2 文件系统 — 知识盲区

### 盲区描述
dm-verity 与 EROFS 的配合机制未在章节中讨论。文中提到"配合 dm-verity 的完整性校验"但未展开。读者需要理解：EROFS 只读 + dm-verity 校验如何协同保护 system 分区完整性，以及这一机制对启动时间的影响（dm-verity 验证需要读取哈希树）。

### 重要程度
中

### 建议研究方向
- dm-verity 工作原理（哈希树、Verified Boot 流程）
- EROFS + dm-verity 的挂载时间开销
- Android 启动过程中 dm-verity 验证的 Perfetto Trace 表现
- dm-verity 对 EROFS 压缩读取路径的影响

### 关联章节
6.2（文件系统）、1.2（系统启动）、16.x（AOSP 安全机制）


## [2026-04-15] 1.3 进程模型与生命周期管理 — 知识盲区

### 盲区 1：CachedAppOptimizer / Freezer 机制（Android 12+）

#### 描述
章节在 Cached Process 部分只提到了 oom_adj 值（900-999），但完全未展开 Android 12 引入的 CachedAppOptimizer 机制。该机制使用 cgroup v2 freezer 冻结 cached 进程，使其线程完全停止执行（不是降优先级，是冻结）。对 Perfetto 分析的影响：冻结进程的线程 slice 彻底消失，与被 LMK 杀死的进程在 Trace 中的表现不同（被杀是进程消失，被冻结是线程消失但进程仍在）。

#### 重要程度
高

#### 建议研究方向
- AOSP `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` 实现
- `system/core/libprocessgroup/profiles/task_profiles.json` 中 freezer 相关 profile
- Google 官方文档关于 cached app freezer 的说明
- Perfetto 中冻结 vs 被杀的区分方法

#### 关联章节
1.3, 4.4, 5.8

### 盲区 2：adj 值版本演进历史

#### 描述
章节给出 android-16 的完整 adj 值表，但缺少版本演进说明。中间档位 PERCEPTIBLE_MEDIUM_APP_ADJ (225) 和 PERCEPTIBLE_LOW_APP_ADJ (250) 的引入版本不明确。SERVICE_A_ADJ 的移除版本也未标注。对于 applicable_versions 覆盖 Android 10-16 的章节，读者需要知道这些值在不同版本上的差异。

#### 重要程度
中

#### 建议研究方向
- 逐版本对比 ProcessList.java 中的 adj 常量变化（Android 10 → 11 → 12 → 13 → 14 → 15 → 16）
- 特别关注 PERCEPTIBLE 细分档位和 SERVICE_A 的引入/移除节点

#### 关联章节
1.3, 4.4

## [2026-04-15] 15.1 性能优化的术、道、器 — 知识盲区

### 盲区描述
性能分析的开销（Profiling Overhead）在方法论章节中完全未提及。包括：
1. Perfetto trace 的 CPU 开销和 buffer 对内存的影响
2. Simpleperf 采样频率对测量精度的 trade-off
3. Benchmark 工具运行时的热降频对结果的影响
4. 如何设计实验来隔离和量化测量开销本身

### 重要程度
高 — 方法论章节强调「数据驱动」但不讨论「测量本身如何影响数据」，是一个结构性缺陷。

### 建议研究方向
- 收集 Perfetto 不同 config（ftrace buffer size、atrace categories）对被测 App 性能的影响数据
- 收集 Simpleperf 不同采样频率（99Hz vs 999Hz vs 9999Hz）对目标进程执行时间的影响
- 研究 Android Benchmark 库的 warmup 机制如何应对热降频
- 参考 Brendan Gregg 对 profiling overhead 的讨论（Systems Performance Chapter 2）

### 关联章节
15.1, 13.1, 13.2, 14.5

## [2026-04-16] 8.3 启动优化策略 — 知识盲区

### 盲区描述
章节 applicable_versions 标注覆盖 Android 8-17，但正文内容在 Android 12 SplashScreen 之后未涉及任何版本差异。Android 13-17 中的启动优化相关行为变更完全空白，包括：per-app language 对 SplashScreen 的影响、Cloud Profile Mainline 化、AutoFDO 协同、profileable 标记要求变化、reportFullyDrawn() 行为变更等。

### 重要程度
高

### 建议研究方向
- 查证 Android 13/14/15/16/17 中与启动优化相关的 Behavior Changes
- 整理 SplashScreen API 在各版本的兼容行为差异
- 梳理 Baseline Profile + Cloud Profile + AutoFDO 在 Android 15/16 中的协同机制
- 验证 `reportFullyDrawn()` 在 Android 15+ 的变更（`androidx.activity:activity:1.8.0` 引入的自动 TTFD 追踪）

### 关联章节
8.1, 8.7, 1.12, 5.10

## [2026-04-16] 8.4 其他响应速度场景 — 知识盲区

### 盲区描述
1. Jetpack Navigation Component 完全未提及。Navigation 是现代 Android 页面导航的标准方案，其性能特征（NavGraph inflate 开销、deep link 解析延迟、Fragment swap 优化、shared element transition）与本章「页面跳转速度」主题高度相关。
2. Compose Navigation 未提及。Compose 的页面切换性能（relocate 节点复用 vs 传统 inflate）是 applicable_versions 涵盖 Android 16 时的必要话题。

### 重要程度
高（Navigation Component）/ 中（Compose Navigation）

### 建议研究方向
- Navigation Component 的 NavGraph inflate 耗时及 lazy inflation
- Navigation deep link vs 普通 startActivity 的额外 Binder 开销
- Compose Navigation 的性能对比数据（Compose vs View 体系的页面切换延迟）
- Activity Transition API / shared element transition 对感知延迟的优化

### 关联章节
8.1, 8.2, 8.3, 3.1


## [2026-04-16] 13.10 Perfetto SQL 性能分析实战手册 — 知识盲区

### 盲区描述
1. 完全未提及 PerfettoSQL 的核心扩展操作符：`SPAN_JOIN`、`LEFT_JOIN_SPAN`、`PARTITIONED_JOIN`。这些是 Perfetto 特有的时间区间 JOIN 操作符，是实现"帧期间的 GC/Binder/锁"这类交叉分析的正确工具。当前章节的交叉分析 SQL 使用普通 JOIN + 时间范围条件，在大 Trace 上性能差且逻辑不精确。
2. 未提及窗口函数（LEAD/LAG/FIRST_VALUE）用于帧节奏时序分析。
3. 未提及 `dur = -1`（未结束 slice）和 `dur = 0`（即时事件）的过滤——新手常见坑。
4. 未提及 PERCENTILE/QUANTILES 函数用于帧时间 P50/P90/P99 分布——行业标准做法。
5. 未提及 `trace_bounds` 表用于获取 Trace 起止时间。

### 重要程度
高（SPAN_JOIN 是 PerfettoSQL 的核心差异化特性）
中（窗口函数和百分位统计）
中（dur=-1 过滤是实战常见坑）

### 建议研究方向
- 梳理 Perfetto v54.0 中所有标准库模块（android.frames、android.monitor、android.input、android.startup 等）提供的视图和函数
- 整理 SPAN_JOIN / LEFT_JOIN_SPAN 的典型用法模式（特别是帧×Binder、帧×GC 交叉分析）
- 收集 Perfetto SQL 性能优化技巧（大 Trace 查询加速）
- 汇总 PerfettoSQL 与标准 SQLite 的差异点（哪些函数不可用、哪些扩展可用）

### 关联章节
13.1, 13.3, 13.5, 13.8

## [2026-04-16] 2.12 Window Manager Service 与窗口管理 — 知识盲区

### 盲区描述
Traversal vs Relayout 的触发条件区分缺失。App 侧 requestLayout() 触发 in-app traversal（measure/layout/draw，不涉及 Binder），而 Window 属性变化触发 relayoutWindow（Binder 调用 WMS）。读者无法判断"什么情况下 App 自己处理就行，什么情况下必须走 WMS"。这是 Perfetto 分析中的常见困惑——看到 relayoutWindow Slice 时不知道它为什么被触发。

### 重要程度
高

### 建议研究方向
- 整理 ViewRootImpl 中触发 relayoutWindow vs scheduleTraversals 的条件矩阵
- 常见 UI 操作（setVisibility、setBackground、invalidate、requestLayout）分别走哪条路径
- 在 Perfetto 中如何区分 WMS 侧的 relayout 和 App 侧的 traversal

### 关联章节
2.12, 2.4, 2.5, 3.1, 8.2

## [2026-04-16] 1.1 Android 分层架构 — 知识盲区

### 盲区 1：SELinux 开销对 Binder 性能的影响
#### 描述
SELinux/MAC 对每次 Binder transaction 执行权限检查，在高频调用场景下累积效应显著。本章多处讨论 Binder 瓶颈但未提及 SELinux 因素。
#### 重要程度
高
#### 建议研究方向
- 测量不同 Android 版本上 SELinux 对 Binder 延迟的贡献
- 分析 enforced vs permissive 模式下的性能差异
- 研究 Android 14+ 中 SELinux 策略优化的趋势
#### 关联章节
1.1, 1.4 (Binder IPC)

### 盲区 2：APEX 模块内部机制与性能影响
#### 描述
讨论了 Project Mainline 但未解释 APEX 工作机制（zip + loop device mount），也未说明模块更新对运行时性能的影响。
#### 重要程度
中
#### 建议研究方向
- APEX 容器格式和加载机制
- 模块更新时服务重启的性能影响
- Mainline 模块版本对 Trace 分析的影响（已在文中提及但未深入）
#### 关联章节
1.1, 1.6 (版本演进), 16.2 (版本变更追踪)

### 盲区 3：Android 8-16 版本差异覆盖不足
#### 描述
applicable_versions 声明 Android 8-16，但遗漏了多项版本级架构变化：Android 10 的 /dev/vndbinder、Android 12 的 cached process frozen state、ART 编译策略演进（cloud profiles）。
#### 重要程度
高
#### 建议研究方向
- 梳理 Android 8-16 每个版本在架构层面的关键变化
- 重点关注影响 Binder 延迟、进程管理、编译策略的变更
- 为每个变化标注对性能分析的具体影响
#### 关联章节
1.1, 1.6, 16.2


## [2026-04-16] 9.1 ANR 设计思想 — 知识盲区

### 盲区描述
startForeground() 超时机制（Android 12+ 5 秒，之前 10 秒）是现代 Android 最常见的 Service ANR 类型之一，但本章未提及。此超时与 Service 启动超时是独立的两个计时器：startForeground() 要求 Service 在 onCreate()/onStartCommand() 后必须在规定时间内调用 startForeground()，否则触发 ANR。

### 重要程度
高

### 建议研究方向
- AOSP ActivityManagerService.java 中 SERVICE_START_FOREGROUND_TIMEOUT 和 SERVICE_START_FOREGROUND_TIMEOUT_SHORT 的定义和版本变化
- Android 12 将超时从 10 秒缩短到 5 秒的 commit 和官方说明
- Android 14 新增的 foreground service type 对 startForeground 超时的影响

### 关联章节
9.2, 5.8

## [2026-04-16] 9.1 ANR 设计思想 — 知识盲区

### 盲区描述
InputConnection ANR（InputMethodManagedService timeout）未提及。当 App 的 InputConnection 在 5 秒内未响应 IME 的输入事件请求时，系统会触发 ANR。这在输入法相关应用和自定义 View 中比较常见。

### 重要程度
中

### 建议研究方向
- AOSP InputMethodManagerService.java 中 INPUT_METHOD_NOT_RESPONDING_TIMEOUT 的定义
- InputConnection ANR 与 InputDispatcher ANR 的触发路径差异
- 在 Perfetto 中的表现特征

### 关联章节
9.2, 3.1, 3.4


## [2026-04-16] 9.4 特殊场景的 ANR — 知识盲区

### 盲区描述
Broadcast 风暴的连锁 ANR 真实机制需要深入研究。当前章节描述的"累计超时"机制不存在，但广播风暴确实会导致多 App 同时 ANR。需要明确真正的原因链条：系统资源争抢（CPU 调度延迟、Binder 线程池竞争、I/O 压力）如何使多个独立 receiver 各自超时。同时需要区分有序广播的串行分发延迟和并行广播的并发资源竞争两种情况。

### 重要程度
高

### 建议研究方向
- AOSP BroadcastQueue.processNextBroadcastLocked() 中 setBroadcastTimeoutLocked() 的调用时机和参数
- Android 14 新增的 CPU-starved 超时分级机制（60s→120s）对广播风暴 ANR 模式的影响
- 有序广播串行分发中，前序 receiver 耗时对后序 receiver 调度延迟的影响量化

### 关联章节
9.1, 9.2

## [2026-04-16] 9.4 特殊场景的 ANR — 知识盲区

### 盲区描述
ART GC 代码片段验证不足。当前 CollectGarbageInternal() 代码是伪代码，需要基于实际 AOSP（android-14 或 android-15）提供准确的阶段调用代码。特别关注：ConcurrentCopying collector 的实际 Run() 方法中 PausePhase/ConcurrentPhase 的调用模式，以及 CMC（Concurrent Mark-Compact，Android 15+）是否有不同的暂停模式。

### 重要程度
中

### 建议研究方向
- art/runtime/gc/collector/concurrent_copying.cc 中 Run() 方法的实际实现
- art/runtime/gc/heap.cc 中 CollectGarbageInternal() 的实际代码
- Android 15 CMC collector 的暂停模式变化

### 关联章节
4.3, 4.8

## [2026-04-16] 2.1 Android 渲染架构全景 — 知识盲区

### 盲区描述
HWUI RenderThread 的 Bitmap 纹理上传（texture upload）机制。在 Draw 阶段，如果 View 包含 Bitmap（如 ImageView 加载的图片、RecyclerView 中的列表项图片），需要将 Bitmap 像素数据从 CPU 内存上传到 GPU 纹理。这个 upload 操作在 RenderThread 上执行，可能导致 RenderThread drawFrame 耗时异常，是列表滑动场景中常见的掉帧根因。当前 2.1 章节完全未提及此机制。

### 重要程度
中

### 建议研究方向
- RenderThread 中 uploadTextures_IfNeeded() 的实现和触发条件
- Bitmap 像素格式（ARGB_8888 vs HARDWARE）对上传开销的影响
- 在 Perfetto 中识别 texture upload 导致的 RenderThread 耗时
- 与 2.5 节（MainThread 与 RenderThread 协作）的交叉引用

### 关联章节
2.1, 2.5, 7.10 (图片加载与 Bitmap 性能优化)

## [2026-04-16] 10.4 低内存对系统性能的影响 — 知识盲区

### 盲区 1：Compact Daemon（compactd）机制
#### 描述
章节讨论了 kswapd 和 Direct Reclaim，但完全未提及 Compact Daemon（Android 10+ 引入的用户空间内存规整守护进程）。compactd 在低内存时主动做 memory compaction 减少碎片，与 kswapd 并列的重要低内存缓解机制。
#### 重要程度
高
#### 建议研究方向
- Android 10 compactd 源码路径和触发条件
- compactd 与 kswapd 的协作关系
- Perfetto 中 compactd 的 track 表现
- compactd 对减少 Direct Reclaim 的实际效果数据
#### 关联章节
4.2, 10.4

### 盲区 2：onTrimMemory() 级别与内存压力信号的映射
#### 描述
章节多次提及 onTrimMemory() 回调（"正确的做法是响应 onTrimMemory() 回调"），但从未解释 trim level 体系（TRIM_MEMORY_UI_HIDDEN=20, TRIM_MEMORY_RUNNING_LOW=10, TRIM_MEMORY_MODIFYING=60 等）如何映射到 PSI/vmpressure 压力等级。读者无法理解"系统通知 App 释放内存"的具体机制和时机。
#### 重要程度
高
#### 建议研究方向
- AOSP ActivityThread.handleTrimMemory 的触发链
- AMS 如何根据内存压力级别计算 trimLevel
- trimLevel 与 lmkd 杀进程策略的对应关系
#### 关联章节
4.5, 10.4

## [2026-04-16] 11.4 功耗案例集 — 知识盲区

### 盲区描述
1. **5G Radio 状态机未覆盖**：案例三 Radio 状态机描述基于 3G/LTE 模型（Full Power → Low Power → Standby），5G NR 的 DRX/CDRX 机制和功耗特征有显著差异，未提及。
2. **FCM 中国大陆可用性**：案例三长期方案推荐 FCM 替代轮询，但中国大陆无法使用 Google 服务。需补充自建 WebSocket 或厂商推送通道（小米推送、华为推送、OPPO 推送等）的替代方案。
3. **线上功耗监控体系缺失**：章节末尾已标注 [待补充]，需要一个完整的线上功耗监控体系搭建案例。

### 重要程度
中（5G 差异和 FCM 可用性影响读者在特定场景下的方案选择）

### 建议研究方向
- 5G NR Radio 状态机（DRX/CDRX）与 4G LTE 的功耗模型差异
- 国内主流厂商推送通道的接入方式和功耗对比
- BatteryStats + UsageStatsManager 在 App 内采集功耗数据的方案

### 关联章节
11.1, 11.2, 11.3, 12.2

## [2026-04-17] 3.1 Input 事件分发全流程 — 知识盲区

### 盲区描述
InputDispatcher 的 stale event 丢弃机制在 Android 12+ 中引入。当 App 从后台恢复或长时间未处理 Input 事件时，InputDispatcher 会计算事件的"年龄"，超过阈值的事件会被直接丢弃而不分发给 App。这个机制解释了"为什么后台切换回来时有些触摸事件丢失"的现象，在 Perfetto 中可以看到 wq 中的事件被批量移除（不触发 ANR）。

### 重要程度
高——直接影响"为什么后台切换后触摸事件丢失"的分析能力，且本章覆盖 Android 12-16，stale event 机制在目标版本范围内已生效。

### 建议研究方向
- 在 AOSP android-14 中搜索 `isStale` 或 `STALE_EVENT_TIMEOUT` 相关常量和逻辑
- 在 InputDispatcher.cpp 中找到 stale event 丢弃的具体阈值和判断逻辑
- 在 Perfetto 中验证 stale event 丢弃的 Trace 表现（wq 值突然归零但无 ANR）

### 关联章节
3.1, 3.2, 9.1, 9.2


## [2026-04-17] 2.9 渲染机制的版本演进 — 知识盲区

### 盲区描述
FrameTimeline 机制（Android 12 引入）在本章多次引用但从未解释。FrameTimeline 是 Perfetto 中最重要的渲染性能 Track 之一，提供「预期帧时间 vs 实际帧时间」的对比数据。缺少其数据来源（SurfaceFlinger 的 FrameTimeline 层）、工作原理（App 报告 vs SF 报告 vs HWC 报告的分层机制）和在 Perfetto 中的正确阅读方法。

### 重要程度
高

### 建议研究方向
- AOSP frameworks/native/services/surfaceflinger/FrameTimeline 模块源码
- perfetto.dev 关于 Frame Timeline 的文档
- Android 12 FrameTimeline Jank 追踪的官方博客

### 关联章节
2.1, 2.4, 2.6, 13.10


## [2026-04-17] 1.7 ART 编译管线与 dex2oat 优化 — 知识盲区

### 盲区描述
Deoptimization（去优化）机制在 ART 编译管线章节中完全缺失。当 AOT 编译代码因以下原因失效时，ART 必须去优化回解释执行：
- 类加载发生变化（新类被加载导致内联假设失效）
- JIT Profile 反馈与 AOT 假设矛盾
- 调试器附加（debugger attach）
- 部分 Android 版本中动态代理类变化

去优化是编译管线的核心闭环，没有它 JIT→AOT→解释执行的循环不完整。在 Perfetto 中可通过 `Deoptimization` Slice 观测。

### 重要程度
高——编译管线章节不讨论去优化，等同于 GC 章节不讨论 GC 触发条件。

### 建议研究方向
- AOSP art/runtime/deoptimization.cc 去优化实现
- art/runtime/jit/jit_code_cache.cc 中的去优化触发逻辑
- Perfetto 中 Deoptimization 相关 Slice 的观测方法
- 不同 Android 版本中去优化策略的差异

### 关联章节
1.7, 4.3



## [2026-04-17] 14.1 Android Studio Profiler — 知识盲区

### 盲区描述
Debug 构建与 Release 构建在 profiling 时的系统性行为差异：ART JIT 优化策略差异、GC 行为差异、锁实现差异（debug 构建使用可调试锁）、Scheduler 钩子差异等。这些差异导致在 debug 构建上观察到的性能问题可能不是 release 构建上的实际问题，反之亦然。作为工具使用章节，这是一个高价值的补充方向。

### 重要程度
高

### 建议研究方向
- AOSP 中 `art/runtime/debugger.cc` 和 `art/runtime/jit/jit.cc` 对 debuggable 标志的处理
- Android 官方文档中关于 debuggable vs profileable vs release 构建的 profiling 行为差异
- Google I/O 2019/2020 关于 profileable 构建的演讲内容

### 关联章节
14.1, 15.6, 13.1


## [2026-04-17] 18.2 Android View 标准链路（BLAST 深入）— 知识盲区

### 盲区描述
BLAST vs Legacy BufferQueue 的架构对比缺失。章节多次提到"BLAST 模型的核心变化点"但从未解释 Legacy 模式的架构（Consumer 端在 SF 进程的 BufferQueue 模型），读者无法理解 BLAST 解决了什么问题、为什么需要迁移。这是理解整个 18.2 章节的前提知识。

### 重要程度
高

### 建议研究方向
- AOSP 中 BLASTBufferQueue 替换 Legacy BufferQueue 的 commit 历史（Android 11 R）
- Legacy 模式下 BufferQueue 的 Consumer 在 SurfaceFlinger 进程中的工作方式
- BLAST 模式下 BBQ 在 App 进程内作为 Consumer 的架构变化
- SurfaceControl.Transaction 的引入时机和动机

### 关联章节
18.2, 2.1, 2.6, 2.13, 2.16, 18.10

## [2026-04-17] 2.1 Android 渲染架构全景 — 知识盲区

### 盲区描述
章节 L699 声称 "Android 16 中引入了 AsyncBufferQueue"，但无法在 AOSP android-16.0.0_r1 源码或官方 changelog 中确认。需要验证此组件是否真实存在、具体功能是什么、以及引入的确切版本。

### 重要程度
高

### 建议研究方向
- 搜索 AOSP android-16.0.0_r1 中是否存在 AsyncBufferQueue 类
- 检查 Android 16 Developer Preview / Beta 的官方 release notes
- 如果不存在，修正为正确的缓冲区管理变更描述

### 关联章节
2.1, 2.6, 18.2


## [2026-04-17] 15.3 性能指标体系 — 知识盲区

### 盲区描述
TTID/TTFD 讨论未区分冷启动（Cold Start）、温启动（Warm Start）、热启动（Hot Start）三种启动类型。Google 官方文档（developer.android.com/topic/performance/launch-time）明确区分三种类型：
- Cold Start：进程从头创建，最慢
- Warm Start：进程存活但 Activity 需重建
- Hot Start：Activity 存活，最快

缺少此分类会导致：线上监控数据混杂不同启动类型，无法区分"启动慢是因为冷启动多还是真的有回归"。

### 重要程度
高

### 建议研究方向
- Google 官方文档中 cold/warm/hot start 的精确定义和度量方法
- 各启动类型下 TTID/TTFD 的典型基线数据
- 线上监控如何区分三种启动类型（通过 Activity.onCreate 是否被调用等信号）

### 关联章节
15.3, 8.1, 8.2

## [2026-04-17] 5.5 Thermal 管控 — 知识盲区

### 盲区描述
厂商特定的温控中间层（Qualcomm thermal-engine、MediaTek thermal manager）未提及。这些用户态守护进程在 Thermal HAL 和内核之间实现了实际的 PID 控制策略和 OEM 定制算法，是决定设备温控行为的关键组件。不了解这一层，读者无法理解：(1) 为什么同样 SoC 的不同设备温控行为差异巨大；(2) 在 Perfetto 中看到的某些温控行为可能来自 vendor daemon 而非 Android 框架。

### 重要程度
高

### 建议研究方向
- Qualcomm thermal-engine 开源代码（codeaurora.org / git.codelinaro.org）中的控制策略实现
- MediaTek thermal manager 的公开文档或源码
- 如何在 Perfetto 中区分 Android 框架温控和厂商温控的行为

### 关联章节
5.5, 5.12

## [2026-04-17] 5.5 Thermal 管控 — 内核 thermal governor 算法

### 盲区描述
Linux 内核的 thermal governor 算法（step_wise、fair_share、bang_bang）未讨论。章节介绍了 trip point 和 cooling device 的概念，但未解释 governor 如何决定 cooling state 的变化。Android 设备默认使用 step_wise governor，它决定了温度上升时频率是渐进降低的（阶梯式），这对理解 Perfetto 中频率变化的模式至关重要。

### 重要程度
中

### 建议研究方向
- Linux kernel Documentation/thermal/sysfs-api.rst 中 governor 的说明
- step_wise governor 源码：drivers/thermal/step_wise.c
- Android GKI 默认 governor 配置

### 关联章节
5.5, 5.4


## [2026-04-17] 18.8 OpenGL ES 渲染链路 — Frame Pacing 控制机制

### 盲区描述
GLES 链路的帧节奏控制（Frame Pacing）完全未讨论。Continuous 模式下 GLThread 紧凑循环渲染，帧率仅受 BufferQueue 限制，无法精确控制。Swappy / Frame Pacing Library 在 GLES 中的集成方式、如何与 Choreographer 协调、如何设置目标帧率等关键话题缺失。这是游戏和地图应用开发者最关心的 GLES 性能话题之一。

### 重要程度
高

### 建议研究方向
- Android Frame Pacing Library（Swappy）源码和 GLES 集成方式
- Choreographer + requestRender() 实现 VSync 对齐的方案
- EGL_EXT_swap_buffers_with_damage 扩展对帧节奏的影响
- 不同 GLES 帧率控制策略的 Perfetto 表现对比

### 关联章节
18.8, 2.17, 18.6

## [2026-04-17] 18.8 OpenGL ES 渲染链路 — EGL Config 选择对性能的影响

### 盲区描述
EGLConfig 的选择（color buffer depth、stencil buffer、MSAA、depth buffer size）直接决定 GPU 渲染带宽和帧缓冲内存占用，但章节完全未提及。在移动设备上，16-bit vs 32-bit color buffer 的选择可以影响 30-50% 的渲染带宽；MSAA 的开启会显著增加 GPU 负载。作为渲染链路章节，这些参数选择是连接「机制理解」和「性能实战」的关键桥梁。

### 重要程度
中

### 建议研究方向
- EGLConfig 选择对移动 GPU 渲染性能的影响
- MSAA 在 Adreno/Mali/PowerVR 上的实际开销
- GLSurfaceView.setEGLConfigChooser() 的默认行为和性能影响

### 关联章节
18.8, 2.10, 18.6

## [2026-04-17] 14.8 GPU 图形调试与分析工具 — GPU 计数器跨厂商映射与工具版本矩阵

### 盲区描述
章节多次提到不同 GPU 厂商的计数器 ID 不同（Adreno/Mali/PowerVR），但未提供任何具体的计数器名称映射或获取方法。开发者无法从文中得知：(1) 如何获取自己设备的可用 GPU 计数器列表；(2) 同一指标（如 GPU Utilization）在不同厂商计数器中的名称和语义差异；(3) 跨设备对比时需要注意的陷阱。

此外，章节缺少工具版本矩阵——各工具支持的最低 Android 版本、GPU 厂商、API（Vulkan/GLES）和功能（系统级/帧级）的交叉对照。

### 重要程度
中

### 建议研究方向
- Adreno/Mali/PowerVR 三大移动 GPU 的常用计数器名称和语义对比
- Perfetto `gpu.counters` 在各厂商驱动中的可用性差异
- 各 GPU profiling 工具的版本支持矩阵（Android 版本 × GPU 厂商 × API × 功能层级）
- 如何通过 adb shell 或 AGI 查询设备支持的 GPU 计数器列表

### 关联章节
14.8, 2.10, 13.3

## [2026-04-17] 1.10 ContentProvider 性能与优化 — 知识盲区

### 盲区描述
多进程 ContentProvider (android:process) 的性能特征完全未覆盖。ContentProvider 声明为独立进程时，初始化、IPC、ANR 行为与单进程场景有重大差异。

### 重要程度
高

### 建议研究方向
- android:process 声明对 ContentProvider 初始化时序的影响
- 独立 Provider 进程的 Binder 线程池与主进程的关系
- ContentProviderClient.setDetectNotResponding() (Android 11+) 在多进程场景的用法
- Provider 进程冷启动对调用方 ANR 的级联影响

### 关联章节
1.10, 9.1, 9.2


## [2026-04-17] 18.3 Android View 软件渲染链路 — 知识盲区

### 盲区描述
1. **Dirty Rect 的真实实现机制缺失** —— 章节把 Dirty Rect 简化成“只重绘变化区域”，但 AOSP Surface::lock() 实际还包含旧前台 Buffer 的 copyback、dirty region 扩张、前帧内容不可用时的全量回退。这决定了 Dirty Rect 什么时候真的省事，什么时候反而退化成整帧拷贝 + 局部重绘。
2. **软件渲染仍然受 BufferQueue 背压约束** —— 章节把软件路径描述成“没有复杂同步问题”，但软件 producer 依然会经过 dequeueBuffer()/queueBuffer()，在槽位被 SurfaceFlinger 占住时同样可能卡在 BufferQueue。

### 重要程度
高

### 建议研究方向
- 研究 frameworks/native/libs/gui/Surface.cpp 中 Surface::lock()/unlockAndPost() 的 dirty region 与 copyBlt 流程
- 梳理 software producer 的 fence 传递链：dequeue fence → lockAsync → unlockAsync → queueBuffer
- 对比 Android 9 Legacy BufferQueue 与 Android 12+ BLAST 下 software path 的实际差异

### 关联章节
- 2.13 图形缓冲区管理
- 18.1 Android 图形渲染链路全景
- 18.2 Android View 标准链路
- 18.6 SurfaceView 直出链路

## [2026-04-18] 12.2 网络性能优化 — 知识盲区

### 盲区描述
HTTP/3 / Cronet 的 Android 落地矩阵缺失。当前章节只把 HTTP/3 描述成“引入 Cronet，APK 增加约 1-2MB”，但没有区分：
1. Cronet by Play Services Provider（GMS 设备，APK 增量极小）
2. Standalone / Bundled Cronet（无 GMS 或需自带内核，体积数 MB）
3. 非 GMS 设备的 fallback 策略（退回 OkHttp HTTP/2、按机型灰度、按网络质量切换）

缺少这一层，读者会把“协议选择”误解成单纯的网络优化问题，而忽略了 Android 生态里的分发、可用性和包体积约束。

### 重要程度
高

### 建议研究方向
- 梳理 Cronet by Play Services 与 standalone Cronet 的包体积、更新路径、依赖条件差异
- 补充 GMS / 非 GMS 设备的 HTTP/3 可用性判断与 fallback 方案
- 研究连接迁移、0-RTT、provider 切换在 Android 真实设备上的验证方法
- 给出适合 App 侧的“何时值得引入 HTTP/3”决策矩阵

### 关联章节
- 12.2 网络性能优化
- 12.1 APK 体积优化
- 16.2 各 Android 版本性能变更追踪
- 17.2 SoC 平台差异

## [2026-04-18] 14.3 内存分析工具 — 知识盲区

### 盲区描述
1. **HWASAN / MTE 开销数据缺少官方量化来源** — 章节给出了“HWASAN 约 1.5 倍内存开销”“MTE 约 1-5% 性能开销”这类数字，但当前未找到可追溯的官方量化文档。
2. **procrank 在新版本设备上的可用性矩阵缺失** — Android 14+ 的 user / userdebug 设备是否默认提供 `procrank`、是否需要 root 或额外推送二进制，当前没有系统性结论。
3. **malloc hooks 的公开稳定性边界不够清晰** — 已确认 bionic `malloc.h` 中存在 API 28+ 的 hook 声明，但其是否适合作为对外建议能力、不同版本的兼容性与限制仍需进一步梳理。

### 重要程度
中高

### 建议研究方向
- 搜集官方文档、AOSP 提交记录或 Google/ARM 演讲材料，给出 HWASAN/MTE 开销的可追溯表述。
- 建立 `procrank` / `showmap` / `libmeminfo` 在 Android 10-16、user/userdebug、root/非 root 下的可用性矩阵。
- 补做 malloc hooks 的 API 稳定性审计，确认是否适合在正文中作为“推荐方案”出现。

### 关联章节
- 10.1 App 内存分析
- 10.3 内存持续增长
- 13.1 Perfetto 简介与演进
- 14.4 dumpsys 系列命令

## [2026-04-18] 18.10 SurfaceControl API 深入 — 知识盲区

### 盲区描述
SurfaceControl NDK 的 FrameTimeline 小节缺少“如何从 AChoreographerFrameCallbackData 的多条 candidate timelines 中选择 vsyncId”的关键解释，也没有说明 ASurfaceTransaction_setDesiredPresentTime() 与 ASurfaceTransaction_setFrameTimeline() 的配合关系。读者容易把 vsyncId 误解为单一回调值，无法建立稳定的帧节拍选择模型。

### 重要程度
高

### 建议研究方向
- 核对 AChoreographer_postVsyncCallback() / AChoreographerFrameCallbackData_* 系列 NDK 文档和示例
- 梳理 callbackData 中 frame timeline count、deadline、expectedPresentTime、preferred timeline 的选择规则
- 补一段“desiredPresentTime + setFrameTimeline”的最小可运行范例，并说明 Android 12 与 Android 13+ 的 NDK 能力边界

### 关联章节
18.10, 18.2, 2.9



## [2026-04-18] 18.15 视频叠加与 HWC — Overlay 能力矩阵与受保护视频路径

### 盲区描述
章节把 Overlay、Secure Buffer、SIDEBAND、Tunnel Mode 压成了一条“统一硬件直出链路”，但真实情况是三套机制叠在一起：
1. **标准 DEVICE composition / Overlay**：Buffer 仍经 SurfaceFlinger layer latch，再由 HWC 规划 plane。
2. **受保护内容路径**：是否允许 protected texture / secure GPU post-processing，取决于设备扩展、内容级别和实现策略。
3. **Tunneled playback / sideband stream**：更偏 Android TV / 特定 SoC 的特例路径，音画同步和数据流都与普通 Overlay 不同。

此外，Overlay eligibility 还高度依赖 SoC 与 HWC 代际，YUV/RGBA、plane alpha、rotation、crop、HDR、protected content 的支持矩阵并不统一。

### 重要程度
高

### 建议研究方向
- 梳理 HWC2.x（HIDL）到 composer3（AIDL）的关键差异，以及对 Overlay / client target 的影响
- 建立主流 SoC（Qualcomm / MTK / Tensor）在 YUV/RGBA、alpha、rotation、HDR、protected composition 上的能力矩阵
- 补 Tunneled playback / sideband stream 的标准链路，与普通 SurfaceView Overlay 做并列图
- 给出 dumpsys SurfaceFlinger / Perfetto 中识别 DEVICE composition、client target、sideband layer 的证据链

### 关联章节
- 2.6 SurfaceFlinger 与合成
- 2.13 图形缓冲区管理（BufferQueue）
- 2.16 Sync Fence 框架与帧同步机制
- 18.6 SurfaceView 直出链路
- 18.10 SurfaceControl API 深入

## [2026-04-18] 18.4 Android View 混合渲染链路 — SurfaceView 位置同步与 alpha/hole-punch 版本行为

### 盲区描述
当前章节把“视频飘移”的改善主要归因到 Android 12+ BLAST / Transaction，但混合渲染真正容易混淆的是三层机制：
1. **位置同步**：SurfaceView 官方文档说明从 Android N 起，window position 已与其他 View 同步更新。
2. **Buffer / 几何协同**：BLAST / Transaction 在后续版本里进一步减少 buffer 更新与几何变化错拍。
3. **透明与挖洞语义**：Android 14+ 才支持 arbitrary alpha blending；更早版本的 alpha 与 composition order 作用点不同，overlapping SurfaceViews 也可能无法正确混合。

同时，官方文档还明确指出 SurfaceView 的可见透明区域基于 layout position，post-layout transform 的 sibling overlay 可能与 surface 不能正确合成。这个约束和章节中的动画/飘移/几何变换话题直接相关，但正文未覆盖。

### 重要程度
高

### 建议研究方向
- 对照 SurfaceView 官方 API，梳理 Android N、Android 11/12、Android 14+ 三个关键版本的行为差异
- 建立“位置同步 vs buffer 同步 vs alpha/composition-order”三层模型，避免把不同层的问题混成一个 BLAST 故事
- 补充 post-layout transform、overlay、rounded corner、overlapping SurfaceView 的可用性边界与排查方法

### 关联章节
- 18.4 Android View 混合渲染链路
- 18.6 SurfaceView 直出链路
- 18.10 SurfaceControl API 深入
- 2.6 SurfaceFlinger 与合成

## [2026-04-18] 18.17 Hardware Buffer Renderer — 知识盲区

### 盲区描述
1. **direct `SurfaceControl.Transaction.setBuffer()` 与 BLAST/BufferQueue 的分层关系** —— 章节把 direct buffer path 与标准 queueBuffer/BBQ 路径混在一起，没有说明两者的连接条件，也没有告诉读者在 Perfetto 里该看哪类证据。
2. **acquire fence / release fence / buffer pool 生命周期** —— 文中只讲 producer 侧的 acquire fence，没有覆盖 release callback、buffer 复用时机、以及 HBR 不自动清空旧内容的语义。
3. **HDR 输出链前提** —— 只提到了 DISPLAY_P3 和“RGBA_F16”，没有展开 `HardwareBuffer.RGBA_FP16`、dataspace/color mode、SurfaceFlinger/HWC 支持链及其 fallback。

### 重要程度
高

### 建议研究方向
- 验证官方文档与 AOSP 中 HardwareBufferRenderer / SurfaceControl.Transaction 的 direct buffer 语义
- 补一段 direct setBuffer 路径的真实 Trace 案例，区分它与 BLASTBufferQueue 路径的可观测点
- 总结单 buffer / 双 buffer / buffer pool 的 release fence 复用模式
- 梳理 wide color 离屏渲染与真实 HDR composition 的条件矩阵

### 关联章节
- 18.2
- 18.3
- 18.10
- 2.10
- 2.16



## [2026-04-18] 18.16 游戏引擎渲染链路 — 知识盲区

### 盲区描述
游戏引擎在 Perfetto 中的可观测性前提没有系统展开。当前章节把 `SwappyTracer` callback、FrameTimeline、graphics tracing、Unity/Unreal 自定义 marker 混在一起，读者不知道哪些是默认可见，哪些需要 ATrace/TrackEvent，哪些要启用 Vulkan/GLES graphics tracing 或切到 AGI。这个矩阵直接决定 trace 诊断能否真正落地。

### 重要程度
高

### 建议研究方向
- 梳理 Unity 默认 markers、Unreal trace/Insights、SwappyTracer callback 与 ATrace/TrackEvent 的对应关系
- 梳理 Perfetto 默认数据源、graphics tracing、GPU render stage、AGI 的覆盖边界
- 给出 60Hz / 90Hz / 120Hz 下启用 Swappy 前后的最小 trace case

### 关联章节
- 2.17 Frame Pacing Library 与帧节奏控制
- 8.9 Android 游戏性能与 Game Mode/State API
- 13.1 Perfetto 简介与演进
- 18.8 OpenGL ES 渲染链路
- 18.9 Vulkan 原生渲染链路

## [2026-04-18] 18.14 Camera 渲染管线 — 知识盲区

### 盲区描述
1. **ZSL 能力矩阵缺失** — 章节把 ZSL 写成统一的“环形缓冲区挑帧 + reprocess”模型，但没有区分 `PRIVATE_REPROCESSING`、`YUV_REPROCESSING`、`CONTROL_ENABLE_ZSL`、reprocessable session 以及 CameraX 自己的 ZSL/fallback 路径。读者很难判断某台设备为什么能开 ZSL、为什么另一台只能退化成普通 still capture。
2. **现代 Camera preview / analysis 背压契约缺失** — 没有把 Android 10+ HAL3.5 buffer management、Android 11+ SurfaceView/BLAST、`ImageReader.maxImages` / `acquireLatestImage()` / `image.close()` 这几组决定背压位置的机制串起来。实际排查时，这几个点决定了堵塞到底发生在 HAL、Framework stream 还是 Analysis consumer。

### 重要程度
高

### 建议研究方向
- 对照 `ICameraDeviceSession` / `ICameraDeviceCallback`、Camera2 API 和 developer docs，梳理 ZSL 的 capability matrix
- 补一张 Android 5-9、Android 10+、Android 11+ 的 preview / buffer management 演进图
- 收集一条 `ImageReader` consumer 堵塞导致 buffer starvation 的真实 Perfetto case，标出 `maxImages`、回调堆积和 buffer 归还的对应关系

### 关联章节
14.9、18.6、2.15

## [2026-04-18] 18.18 PIP 与自由窗口渲染 — Shell 控制面链路

### 盲区描述
章节把多窗口/PIP 的关键同步问题几乎全部落在 SurfaceFlinger + BLAST 上，但没有覆盖 Android 12+ 的 Shell 控制面：`PipTaskOrganizer`、`TaskOrganizer`、`WindowContainerTransaction`、Shell transitions / SyncEngine 这条链路决定了进入 PIP、窗口 resize、bounds 变更何时提交到 WMS 和 SurfaceFlinger。缺了这一层，读者很难解释为什么同样是 resize，Android 8-10、11、12+ 的表现和 Trace 观察点并不一样。

### 重要程度
高

### 建议研究方向
- `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/pip/PipTaskOrganizer.java` 与 Shell transition 相关类
- `WindowContainerTransaction` / SyncEngine / BLASTBufferQueue 在 resize 同步中的职责边界
- PIP / Freeform 场景下 WindowManager trace、Perfetto FrameTimeline、SurfaceFlinger transaction 的联合观察方法

### 关联章节
18.18, 18.10, 2.12
