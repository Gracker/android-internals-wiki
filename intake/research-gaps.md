## [2026-06-18] 26.3 性能指标采集与上报 — 知识盲区

### 盲区描述
Android 系统缺少官方的高精度内存跟踪 API，现有监控主要依赖 Debug.MemoryInfo 类和第三方工具。章节提到的 MemoryTracking、MemoryUsage、LeakDetection 等 API 在 AOSP 中不存在，反映了系统级内存监控的技术断层。

### 重要程度
高

### 建议研究方向
- 研究 Android 原生内存监控机制（如 Debug.MemoryInfo、procfs、smaps）的限制和改进方案
- 探索用户空间内存跟踪库（如自定义的内存跟踪器、基于 eBPF 的解决方案）的实现路径
- 分析 Android 14+ 新增的内存相关 API（如 getProcessMemoryInfo 的 smaps_rollup 优化）
- 研究跨平台内存监控工具（如 Valgrind、AddressSanitizer）在 Android 适配中的可行性

### 关联章节
- 26.3 性能指标采集与上报（当前章节，需重构）
- 23.7 内存监控（PSS/RSS 快速路径与 smaps_rollup 优化）（需补充对比）

---

## [2026-06-18] 10.6 内存抖动与频繁 GC — 知识盲区

### 盲区描述
现代 Jetpack Compose 框架中的内存分配模式与传统 View 系统存在显著差异。Compose 的状态管理、重组机制和 Lambda 表达式使用会产生大量短生命周期对象，但当前章节未覆盖这一重要领域。

### 重要程度
高

### 建议研究方向
- 分析 Compose 重组过程中的内存分配热点
- 研究 Compose 状态对象（MutableState、remember等）的内存模式
- 探索 Compose 与传统 View 系统混合使用时的内存抖动叠加效应
- 研究 Compose 的 Composer 对象和 SlotTable 对内存管理的影响

### 关联章节
- 10.6 内存抖动与频繁 GC（当前章节，需补充）
- 7.2 卡顿原因体系（需补充框架对比）
- 新增：Jetpack Compose 内存管理专题（建议新增章节）