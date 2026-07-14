## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-07-14
- **类型**：源码准确性
- **位置**：Preload 序列源码行号
- **问题**：文中声称在 ZygoteInit.java 行 119-163，经 android-17.0.0_r1 实际源码复核，完整 Preload 序列在行 296-371，不是 119-163 行
- **建议**：修正为正确的源码行号 android-17.0.0_r1 的 296-371 行

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-07-14
- **类型**：源码准确性
- **位置**：SurfaceFlinger 切片表缺 android-17 行
- **问题**：文中表格只到 android-15，缺少 android-17 的切片信息。根据 AOSP android-17.0.0_r1 SurfaceFlinger.cpp 验证，android-17 主路径仍然是 `commit <vsyncId>` → `composite <vsyncId>` → `postComposition`，与 android-16 一致

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-07-14
- **类型**：数据缺失
- **位置**：16 KB Page Size 性能影响描述
- **问题**：文中提到"16 KB 页会减少页表项数量，通常有利于 TLB 命中"但缺少具体数据支撑
- **建议**：补充页表减少比例（约 75%）、TLB 命中率提升幅度的量化数据，以及来自 Android Developers 文档的实测数据

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-07-14
- **类型**：数据缺失
- **位置**：USAP 性能对比
- **问题**：文中提到 USAP 概念但缺少与普通 fork 的量化性能对比数据
- **建议**：补充启动时间节省（如 P99 启动时间改善）、内存使用差异（如 COW 节省比例）等量化数据

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-07-14
- **类型**：交叉引用一致性
- **位置**：DaliQueue 提及
- **问题**：文中提到 DaliQueue 但未在本章展开，缺少明确的后续章节标注
- **建议**：添加明确的交叉引用标注，如"详见 §1.13 MessageQueue 机制"或"将在后续章节详细讨论"}
- **建议**：补充 android-17 行到 SurfaceFlinger 切片表中，确保版本覆盖完整

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-07-14
- **类型**：版本差异
- **位置**：16KB Page Size 版本边界描述
- **问题**：文中描述"Android 16 架构层面的最新变化（如 Mainline 模块持续扩展）"，但 16KB Page Size 实际是 Android 15 引入并在 Android 16 继续完善的特性，不是 Android 16 新引入
- **建议**：修正版本边界描述，明确区分构建能力、设备配置校验和应用发布要求三个不同层面

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-07-14
- **类型**：数据缺失
- **位置**：Binder 池容量规划经验值
- **问题**：文中提到的"普通 App：mMaxThreads = 4-8 足够"、"系统服务：保留 15 默认值"等经验值缺乏实测依据
- **建议**：补充实测数据支持或修改为更保守的经验表述，注明数据来源和测试条件

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-07-14
- **类型**：原理链完整性
- **位置**：USAP 与 Child Zygote 关系描述
- **问题**：文中提到 USAP 只服务 primary/secondary zygote，但未充分解释为什么 App Zygote/WebViewZygote 等 Child Zygote 无法使用 USAP Pool
- **建议**：补充源码级证据说明 ZygoteServer 构造函数中 mUsapPoolSupported 的初始化差异，增强原理解释的完整性

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-07-14
- **类型**：数据缺失
- **位置**：Binder 调用次数数据
- **问题**：文中提到"一个完整的冷启动涉及多次 Binder 往返和一次 LocalSocket 通信，Binder 调用总量可能达到数十次"，但未给出具体的测量方法和数据来源
- **建议**：补充测量方法说明和实际设备测试数据，或修改为更保守的表述

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-07-14
- **类型**：数据缺失
- **位置**：fork 时间范围
- **问题**："一次 Zygote fork 大约只需要 20-50 ms"的表述范围过大，缺乏不同设备类型的分类数据
- **建议**：根据不同设备类型（高端/中端/入门）给出更具体的分类数据，或注明测试条件和设备范围

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-07-14
- **类型**：交叉引用一致性
- **位置**：与 §1.2 系统启动全流程的引用关系
- **问题**：文中提到"看 Zygote 在开机链里的位置"，但未说明在 §1.2 的哪个具体位置讨论了开机流程的完整时序图
- **建议**：明确引用 §1.2 中的具体章节编号和小节，增强交叉引用的精确性