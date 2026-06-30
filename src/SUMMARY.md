---
tags:
  - android
  - ai
  - binder
  - summary
---
# 目录

[写在前面](preface/intro.md)
- [本书的使用方式](preface/how-to-use.md)
- [适用读者](preface/target-audience.md)
- [内容验证标准说明](preface/verification-standards.md)
- [版本约定](preface/version-conventions.md)
- [阅读路径推荐](preface/reading-paths.md)

---

# 第一部分：Android 系统运行机制

- [第 1 章：系统架构全景](part1-fundamentals/ch01-architecture/README.md)
  - [1.1 Android 分层架构](part1-fundamentals/ch01-architecture/01-layered-architecture.md)
  - [1.42 Android 17 RPC Binder 事务上限提升](part1-fundamentals/ch01-architecture/1.42-android-17-rpc-binder-事务上限提升.md)
  - [1.41 Android 17 机器学习驱动的任务调度器](part1-fundamentals/ch01-architecture/1.41-android-17-机器学习驱动的任务调度器.md)
  - [1.43 Android 17 机器学习驱动任务调度器](part1-fundamentals/ch01-architecture/1.43-android17-ml-scheduler.md)
- [第 13 章：性能分析工具](part13-xxx/ch13-xxx/README.md)
  - [13.19 Perfetto v54 Data Explorer 与 SQL 标准库](part5-app/ch13-profiling/13.19-perfetto-v54-data-explorer.md)

- [第 22 章：渲染实战](part22-xxx/ch22-xxx/README.md)
  - [22.27 Compose Pausable Composition 内部实现](part5-app/ch22-rendering-practice/22.27-compose-pausable-composition.md)
  - [Android 17 Vulkan 多队列并行渲染与 GPU 负载均衡](part5-app/ch22-rendering-practice/22.1-vulkan-多队列-gpu-负载均衡-draft.md)


- [第 16 章：AOSP 深度剖析](part16-xxx/ch16-xxx/README.md)
  - [16.18 Linux 6.10 内存碎片整理机制](part4-system/ch16-aosp/16.18-linux610-memory-fragmentation.md)
  - [Android 17 系统启动耗时优化新特性与 bootanalyze 工具链](part4-system/ch16-aosp/16.20-系统启动耗时-bootanalyze-draft.md)


- [16.19 Android 17 bootanalyze 工具链与 Zygote 延迟预加载](part4-system/ch16-aosp/16.19-android17-bootanalyze-zygote-lazy-preload.md)
- [26.23 生产级 ART 动态方法追踪 — XTrace 架构与实战](part5-app/ch26-observability/26.23-xtrace-art-dynamic-method-tracing.md)
- [5.27 端侧大模型推理能效选型：MoE 架构与量化策略](part1-fundamentals/ch05-cpu-power/5.27-ondevice-llm-inference-energy-efficiency.md)


  - [Android 17 MemoryLimiter 的 30 秒 Kill 窗口真相与 ProfilingServiceHelper 触发条件](part1-fundamentals/ch04-memory/4.1-memorylimiter--30-秒-kill--profilingservicehelper-触发条件-draft.md)

  - [Android 17 Binder IPC 优先级继承机制与内核批处理流水线](part1-fundamentals/ch01-architecture/1.9-binder-ipc-优先级继承内核批处理流水线-draft.md)

  - [Android 17 androidx DataStore 多进程 IPC 底层实现源码级验证](part1-fundamentals/ch06-storage/6.1-androidx-datastore--ipc-源码级验证-draft.md)