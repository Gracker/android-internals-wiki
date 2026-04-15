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
