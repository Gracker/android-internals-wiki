## [2026-05-11] 20.1 应用稳定性全景 — 知识盲区

### 盲区描述
Android 15+ 的新特性 Battery Historian 2.0、ANR Predictor 等优化机制未覆盖，缺乏对新一代稳定性监控工具的说明

### 重要程度
高

### 建议研究方向
- Battery Historian 2.0 的事件收集机制和性能优化改进
- ANR Predictor 的工作原理和准确率评估
- Android 15+ 的系统级稳定性监控API演进
- 新特性对开发者调试和优化的实际影响

### 关联章节
20.4, 20.5, 1.7

---

## [2026-05-11] 20.1 应用稳定性全景 — 知识盲区

### 盲区描述
Native Crash 的符号表处理机制说明不足，缺少对`.sym`文件的生成、加载和符号还原的完整流程

### 重要程度
中

### 建议研究方向
- Native Crash 符号表文件的生成标准和工具链
- 符号表在运行时的加载和缓存机制
- 多进程场景下的符号表管理
- 符号还原的性能优化和最佳实践

### 关联章节
20.3, 5.7

---

## [2026-05-11] 20.2 Java Crash 治理 — 知识盲区

### 盲区描述
Kotlin协程异常处理机制与UncaughtExceptionHandler的关系说明不足，缺少对协程上下文中的异常捕获机制

### 重要程度
高

### 建议研究方向
- CoroutineExceptionHandler 与 UncaughtExceptionHandler 的优先级和协作机制
- 协程异常的传播路径和日志格式标准
- 多个协程异常处理器的链式调用规则
- 协程异常的监控和上报最佳实践

### 关联章节
20.1, 1.7, 25.4

---

## [2026-05-11] 20.2 Java Crash 治理 — 知识盲区

### 盲区描述
多进程应用的特殊性未覆盖，缺少多进程场景中的异常处理最佳实践和进程间通信异常的处理策略

### 重要程度
中

### 建议研究方向
- 多进程场景中的异常传播和跨进程上报机制
- Service/Activity进程崩溃对主进程的影响评估
- 进程间异常处理的一致性和性能考量
- 多进程应用的稳定性监控策略

### 关联章节
20.1, 15.3, 1.3

---

## [2026-05-11] 2.10 GPU 渲染深入 — 知识盲区

### 盲区描述
GPU计算着色器在Android UI渲染中的应用场景未覆盖，缺少对计算着色器与图形着色器的协作机制

### 重要程度
中

### 建议研究方向
- Android UI渲染中的计算着色器应用模式
- 计算着色器与图形管线的性能权衡
- 模糊、阴影等效果的GLSL优化实现
- 计算着色器在Material Design效果中的应用案例

### 关联章节
2.9, 3.2, 14.3

---

## [2026-05-11] 2.10 GPU 渲染深入 — 知识盲区

### 盲区描述
Metal/Vulkan互操作和iOS/Metal相关对比内容缺失，缺乏跨平台GPU渲染的技术对比

### 重要程度
低

### 建议研究方向
- Android Vulkan vs iOS Metal 的API设计对比
- 跨平台GPU代码的统一架构设计
- Metal的Metal Performance Shaders vs Android的优化策略
- 跨平台GPU调试工具的集成方案

### 关联章节
2.9, 3.2, 14.3

---

## [2026-05-10] 3.0 输入系统 — 知识盲区

### 盲区描述
HCI 感知阈值研究与 Android 实际产品实现的转化逻辑缺失，需要建立从实验室研究结果到产品性能目标的桥梁

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
- AOSP 目录结构演进
- Android 15 中 Input 如何驱动刷新率切换的调用链

[已发现external-review命中: 3.0 输入系统external-review文档已命中ARR相关技术盲区]