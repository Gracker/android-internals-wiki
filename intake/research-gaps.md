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


