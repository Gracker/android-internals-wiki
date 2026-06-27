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

## [2026-06-27] 16.8 AppFlow：GB 级应用冷启动内存联合调度 — LMKD新机制兼容性

### 盲区描述
章节中AppFlow研究原型与Android现有内存管理机制的兼容性分析不充分。缺少对Android 17中LMKD v2、Memory Reclaim Priority、Adaptive Background Activity Manager等新机制的兼容性讨论，未分析AppFlow与这些现有机制的协作或冲突关系。

### 重要程度
高

### 建议研究方向
- 分析AppFlow三段式调度模型与Android 17 LMKD v2的职责边界和协作方式
- 研究Memory Reclaim Priority如何影响AppFlow的Adaptive Memory Reclaimer策略
- 调研AppFlow在Adaptive Background Activity Manager调度框架下的适用性
- 分析AppFlow与Android现有Low Memory Killer属性的兼容性配置

### 关联章节
- 16.7 系统启动耗时优化
- 16.1 内存管理基础
- 8.2 后台进程管理

## [2026-06-27] 16.7 Android 系统启动耗时优化与 bootanalyze — Android 17新特性缺失

### 盲区描述
章节缺少Android 17中系统启动优化的新特性分析。未涵盖Android 17中Zygote启动优化的新机制、APEX模块化对启动影响的深入分析、以及后台服务调度的新特性。缺少对Android 17启动时间性能基准的量化数据。

### 重要程度
高

### 建议研究方向
- 分析Android 17中Zygote启动优化的新机制和性能表现
- 调研Android 17中APEX模块化对系统启动时序和service依赖的影响
- 研究Android 17中后台服务调度的新特性和优化策略
- 收集Android 17设备在不同启动场景下的性能基准数据

### 关联章节
- 1.2 Android进程模型
- 16.1 内存管理基础
- 8.2 后台进程管理



## [2026-06-28] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 知识盲区 (Task9更新)

### 盲区描述
基于Deep Tech Review发现的高优先级知识盲区：
1. **hprof文件解析性能瓶颈** - 未详细分析大内存设备上hprof解析的性能瓶颈，包括内存占用、解析速度、工具兼容性等关键问题
2. **设备厂商定制差异** - 缺少对主流设备厂商（高通、联发科、三星等）在hprof实现上的定制差异分析，可能影响跨设备一致性
3. **高级hprof解析技术** - 未覆盖针对复杂内存模式的高级解析技术，如内存泄漏根因分析、内存热点追踪、对象引用图构建等

### 重要程度
高

### 建议研究方向
- 分析不同设备规格（RAM大小、CPU核心数）对hprof解析性能的影响
- 调研主流Android设备厂商对HPROF格式的定制实现和差异点
- 研究Perfetto java_hprof数据源在超大内存场景（6GB+）下的性能表现和优化策略
- 开发针对复杂内存模式的高级分析工具和方法论
- 对比分析MAT、Android Studio、Perfetto三种分析工具在相同场景下的优劣

### 关联章节
- 10.1 (内存泄漏定义)
- 14.3 (内存分析工具)
- 14.14 (内存分析流程)
- 19.3 (KOOM实现细节)

## [2026-06-28] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 知识盲区 (Task9更新)

### 盲区描述
基于当前Deep Tech Review发现的高优先级知识盲区：
1. **Binder 优先级调度机制** - 未解释Binder驱动如何处理不同类型事务的优先级（如oneway vs 同步 vs death notification）
2. **缓冲区溢出处理策略** - 未解释BINDER_VM_SIZE 1MB缓冲区满后的溢出策略和降级机制
3. **多进程场景下的Binder路由** - 未说明跨进程Binder调用时的路由选择机制和负载均衡策略

### 重要程度
高

### 建议研究方向
- 分析Binder驱动的优先级调度算法，实现oneway/同步/death notification的差异化处理
- 研究1MB缓冲区溢出后的处理策略，包括重新分配、降级机制和错误处理
- 调研多进程场景下的Binder路由选择机制，包括进程间通信的负载均衡
- 补充Android 12-17中冻结回执机制的渐进式优化细节
- 分析oneway spam检测机制的具体阈值设定和累计算法

### 关联章节
- 1.4 (Binder基础架构)
- 1.13 (IPC通信机制)
- 1.27 (协议层解析)
- 1.30 (事务队列优化)

## [2026-06-28] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 知识盲区

### 盲区描述
章节缺少 Binder 事务优先级机制在 Android 17 中的实现细节，以及未讨论跨进程同步机制（如 Barrier/CountDownLatch）与 Binder oneway 的交互。这两个盲区影响开发者对高性能 IPC 和同步机制的理解，特别是在高并发场景下的最佳实践选择。

### 重要程度
高

### 建议研究方向
- 研究 Android 17 中 Binder 事务的优先级调度机制，包括高优先级事务的识别和执行策略
- 分析 Binder oneway 与传统同步机制（Barrier、CountDownLatch、条件变量）的交互模式和潜在冲突
- 探索在混合同步/异步 IPC 场景下的死锁预防和性能优化策略
- 调研 Android 17 中是否引入了新的事务优先级相关的 BR_/BC_ 命令或 ioctl 调用

### 关联章节
1.4 (Binder 基础架构)，1.13 (IPC 通信机制)，§4.11 (进程生命周期与 Freezer)## [2026-06-28] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 知识盲区 (Task9新发现)

### 盲区描述
基于Deep Tech Review发现的关键知识盲区：
1. **Binder 线程池内部调度机制** - 未解释在大量 oneway 调用场景下，binder 线程池的内部调度策略和线程竞争机制
2. **BR_TRANSACTION_PENDING_FROZEN 重投递机制** - 未解冻后事务重新投递的内部机制，包括解冻判断和事务重排序逻辑

### 重要程度
高

### 建议研究方向
- 分析 binder 线程池在高频 oneway 调用下的内部调度算法和线程状态管理
- 研究 BR_TRANSACTION_PENDING_FROZEN 的事务暂存和重投递机制，包括解冻触发条件
- 调研不同进程类型（应用进程 vs system_server）的 binder 线程池配置差异
- 分析 oneway 调用在高频场景下的内存管理和性能瓶颈

### 关联章节
1.4 (Binder 基础架构)，1.13 (IPC 通信机制)，1.27 (协议层解析)