# 第 23 章：内存优化实战

App 内存问题通常表现为泄漏、频繁分配、GC 抖动、Native Heap 增长或触发系统内存限制。诊断时需要区分 Java Heap、Native Heap、图形内存和虚拟内存，并结合进程状态判断影响。

第 4 章分析 Android 内存管理机制，第 10 章介绍内存分析工具；这里整理 App 侧的监控、诊断和优化实践。

## 内容索引

- [23.1 内存泄漏检测与治理](01-memory-leak-governance.md)
- [23.2 Bitmap 与图片内存优化](02-bitmap-optimization.md)
- [23.3 Native 内存管理与优化](03-native-memory-management.md)
- [23.4 Java Heap 优化策略](04-java-heap-optimization.md)
- [23.5 内存抖动与 GC 治理](05-memory-churn-gc.md)
- [23.6 大内存与多进程策略](06-large-heap-multiprocess.md)
- [23.7 内存监控与线上治理](07-memory-monitoring.md)
- [23.8 Jetpack Compose 内存分配与 GC 影响](08-compose-memory-allocation-gc.md)
- [23.9 应用虚拟内存优化实战](09-virtual-memory-optimization.md)
- [23.10 端侧大模型推理的内存管理](10-ondevice-llm-memory-management.md)

## 阅读建议

- 泄漏问题可从 23.1、23.3 和 23.7 开始，分配抖动可直接进入 23.5；Compose 场景进入 23.8。
- Native 场景应同时检查 allocator、线程栈、mmap 和图形缓冲区，不能只看 Java Heap。
- 大内存、多进程与 Android 17 MemoryLimiter 统一见 23.6，端侧模型的权重、KV Cache 和后端缓冲预算见 23.10。
- 线上数据需要记录设备内存等级、进程状态和系统压力，便于区分应用增长与系统回收。
