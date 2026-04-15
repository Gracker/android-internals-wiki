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

