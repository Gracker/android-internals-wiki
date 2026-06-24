
## [2026-06-24] 8.10 ProfilingManager 系统触发式性能追踪 — 知识盲区

### 盲区描述
ProfilingManager 的 multi-package support 和 UID 级别控制机制在实际使用中非常重要，但章节未覆盖这些关键功能。

### 重要程度
高

### 建议研究方向
- 研究 ProfilingManager 如何支持多包同时的 Profiling Session
- 分析 UID 级别的权限控制机制和安全边界
- 查找 AOSP 中关于 multi-package support 的实现细节
- 研究 Extension SDK 36.1 的运行时判断逻辑和版本适配

### 关联章节
- 8.10 (当前章节)
- 1.3 权限安全
- 2.5 渲染线程与主线程交互

## [2026-06-24] 7.7 Jetpack Compose 性能优化 — 知识盲区

### 盲区描述
Compose Compiler 2.0 Strong Skipping 与 1.x 版本在底层实现和优化策略上有显著差异，需要详细对比分析。

### 重要程度
中

### 建议研究方向
- 深入分析 derivedStateOf 与 derivedSnapshotState 的底层实现差异
- 研究 Compose Compiler 2.0 Strong Skipping 的新特性
- 分析 Kotlin 2.0+ 对 Compose 编译优化的影响
- 测试不同版本间的性能差异

### 关联章节
- 7.7 (当前章节)
- 8.10 ProfilingManager (性能测量方法)


## [2026-06-24] 14.13 Hook 基础设施与性能工具实现原理 — 知识盲区

### 盲区描述
Hook技术在Android 17+环境下的具体实现限制和边界条件，特别是在SELinux enforcing模式、Mainline模块化架构和16KB page size环境下的完整技术方案。现有文档缺少具体的实验验证数据和性能基准。

### 重要程度
高

### 建议研究方向
- Android 17+环境下SELinux策略对Hook框架的实际影响验证，包括不同domain的权限差异
- Mainline模块化架构下Hook工具的适配策略，特别是APEX模块的Hook限制和解决方案
- 16KB page size环境下Hook框架的内存对齐和mprotect策略调整
- Hook技术在多进程场景下的完整实现方案，包括进程间状态同步和数据共享机制
- Hook工具在生产环境中的实际性能开销基准测试和稳定性统计

### 关联章节
8.10 ProfilingManager系统触发式性能追踪; 20.7 异常处理架构; 20.12 SafeMode

## [2026-06-24] 19.10 其他开源 APM 库(AndroidGodEye、Collie、Rabbit) — 知识盲区

### 盲区描述
APM工具在实际生产环境中的性能开销基准数据和兼容性验证，特别是在现代Android版本(15-17)和不同厂商定制ROM上的适配情况。现有文档缺乏实际使用数据和性能对比。

### 重要程度
中

### 建议研究方向
- APM工具在不同Android版本(15-17)上的性能开销基准测试
- 主流厂商定制ROM上APM工具的兼容性验证和适配策略
- APM工具在真实生产环境中的crash率、内存占用和CPU使用率统计
- 轻量级APM方案与商业平台方案的实际效果对比分析
- APM工具在多进程、低内存设备上的表现优化策略

### 关联章节
14.13 Hook基础设施与性能工具实现原理; 8.10 ProfilingManager系统触发式性能追踪

## [2026-06-24] 8.10 ProfilingManager 系统触发式性能追踪 — 知识盲区

### 盲区描述
ANOMALY触发器的具体实现规则和判定条件未公开，系统异常检测机制的具体实现细节缺失，缺少实际生产环境中的使用效果验证数据。

### 重要程度
高

### 建议研究方向
- ANOMALY触发器的具体实现规则和判定条件反向工程验证
- 系统异常检测机制的详细实现和配置方法研究
- ProfilingManager在实际项目中的使用效果数据收集
- ANOMALY触发器在不同设备和Android版本上的行为差异分析
- ProfilingManager与其他性能监控工具的协同工作机制

### 关联章节
14.13 Hook基础设施与性能工具实现原理; 4.4 内存管理机制