## [2026-06-27] 15 Android 性能优化研究方法论 — 知识盲区

### 盲区描述
章节中关于 Perfetto 版本可用性的描述可能存在不准确问题。当前声称"Android 9（API 28）起 Perfetto 可用"，但需要官方文档确认准确版本信息。另外缺少 Android 12+ 中 Perfetto 的重要新特性（如 heapprofd、gpu 等数据源）的说明。

### 重要程度
高

### 建议研究方向
- 精确核实 Perfetto 在 Android 各版本中的引入时间线和默认化进程
- 调研 Android 12+ 中 Perfetto 的新增数据源和分析功能
- 整理 Perfetto 与 Systrace 的功能对比和迁移路径

### 关联章节
- 14.1 系统级追踪工具
- 14.2 渲染性能分析
- 14.5 内存分析工具## [2026-06-27] 6.5 SharedPreferences/DataStore 性能与 ANR 优化 — Android 17 源码验证缺失

### 盲区描述
章节标注适用 Android 1.0-37，但源码验证仅基于 android-16.0.0_r1，缺少 Android 17/API 37 中 SharedPreferencesImpl 的性能优化、API 变更或底层机制验证。同时 DataStore 1.1.0+ 的 MultiProcessDataStoreFactory 具体实现差异也未覆盖。

### 重要程度
高

### 建议研究方向
- 对比分析 Android 16 与 Android 17 中 SharedPreferencesImpl 的关键变更
- 验证 Android 17 中 SP 加载、写入、同步机制的变化
- 调研 DataStore 1.1.0+ 中 MultiProcessDataStoreFactory 的实现细节和最佳实践
- 分析 Android 14+ 对主线程等待 SP 写入的系统性优化策略

### 关联章节
- 6.1 基础存储架构
- 6.3 文件系统性能分析
- 9.1 多进程数据一致性
- 8.2 主线程性能优化

