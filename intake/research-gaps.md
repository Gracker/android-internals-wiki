
## [2026-05-10] 3.0 输入系统 — 知识盲区

### 盲区描述
1. HCI 感知阈值研究与 Android 实际产品实现的转化逻辑缺失，需要建立从实验室研究结果到产品性能目标的桥梁
2. 输入事件反压机制未覆盖，缺乏 InputDispatcher 在目标窗口无响应时的降级策略说明
3. 高负载场景下输入事件的优先级处理机制未覆盖，缺乏系统资源紧张时的优先级调度逻辑
4. 输入事件的异步处理和回调机制未覆盖，缺乏 InputConsumer 与 Native 层的异步协作机制说明

### 重要程度
高

### 建议研究方向
- HCI 感知阈值与 Android 端到端延迟的映射关系研究
- InputDispatcher 的背压处理和降级策略实现机制
- 高负载场景下输入事件的优先级算法和调度策略
- InputConsumer 与 Native 层的异步处理流程优化

### 关联章节
1.1, 2.3, 2.4, 2.5, 8.1

---

## [2026-05-09] 4.3 ART 虚拟机内存管理 — 知识盲区

### 盲区描述
ART FinalizerDaemon 线程与 ReferenceQueue 的并发优化边界未证实。AOSP 源码中 `libcore ReferenceQueue.java` 仍使用 `private final Object lock`，未见证据表明 `ConcurrentMessageQueue` 无锁投递已接入 ART 内部的 ReferenceQueue 路径。Android 16 引入的并发优化与 ART 内部锁竞争的关联性需要进一步确认。

### 重要程度
高

### 建议研究方向
- 深入分析 Android 16 AOSP 源码中 `ConcurrentMessageQueue` 与 `ReferenceQueue` 的集成可能性
- 调研 FinalizerDaemon 线程在 Android 16 上的锁优化实现细节
- 验证 ART 是否在 Android 16+ 中引入了无锁 ReferenceQueue 机制
- 分析 MessageQueue 并发优化对 ART GC 性能的实际影响

### 关联章节
4.3, 1.6, 7.7
## [2026-05-09] 3.0 输入系统 — 知识盲区

### 盲区描述
Android 15/16 输入系统架构重构，包括 InputFlinger Rust 组件、ARR (Adaptive Refresh Rate) 与输入协同、预测性返回性能影响

### 重要程度
高

### 建议研究方向
- AOSP  目录结构演进
- Android 15 中 Input 如何驱动刷新率切换的调用链
- Predictive Back 在 Android 14+ 中的性能影响量化

### 关联章节
3.1, 3.3, 3.4, 3.5



## [2026-05-10] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 知识盲区

### 盲区描述
DeliQueue 的完整工作机制，特别是 drain 触发条件和内部实现细节；Generational CMC 的具体 gating 条件配置方法；ProfilingManager 触发器的内部判断逻辑；ConcurrentMessageQueue 的实际数据结构实现

### 重要程度
高

### 建议研究方向
- 深入分析 AOSP frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java 的实际实现
- 研究 DeliQueue drain 操作的具体触发时机和实现算法
- 分析 Generational CMC 的 gating 条件具体含义和配置方法
- 探究 ProfilingManager 触发器如何判断 "anomalous behavior" 等系统事件
- 验证 ConcurrentMessageQueue 是否真的使用 ConcurrentSkipListSet 还是其他数据结构

### 关联章节
4.8, 14.7, 16.2, 16.4

### 外部 Review 命中
external-review 未直接命中此盲区，但 Task 6 已指出 DeliQueue 概念模型与实际实现存在语义差异
