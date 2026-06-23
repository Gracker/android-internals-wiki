## [Task9 Deep Review] 18.14 Camera 渲染管线 — 2026-06-23

- **类型**：源码准确性
- **位置**：源码引用路径
- **问题**：引用路径错误：`hardware/interfaces/camera/device/aidl/android/hardware/camera/device/ICameraDevice.aidl` 应为 `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`
- **建议**：修正源码路径引用，确保指向正确的 CameraDevice AIDL 接口

- **类型**：原理链完整性
- **位置**：ZSL 机制原理链
- **问题**：ZSL 机制描述不完整，缺少 HAL reprocessing 能力前置条件说明
- **建议**：补充说明设备必须声明 `REQUEST_AVAILABLE_CAPABILITIES_PRIVATE_REPROCESSING` 才能使用 ZSL，建立完整的 HAL 能力依赖链

- **类型**：版本差异覆盖
- **位置**：版本演进表
- **问题**：Android 16 MemoryLimiter 机制未在章节中提及
- **建议**：在版本演进表中增加 MemoryLimiter 相关说明，补充 Android 17 对高 RAM 设备的内存限制变化

- **类型**：知识盲区
- **位置**：Camera HAL buffer management
- **问题**：Camera HAL buffer management 与 BufferQueue 协作的内存模型未充分覆盖
- **建议**：补充 GraphicBuffer 在 HAL 和 Framework 间的所有权转移机制、内存分配策略、同步原语使用说明

- **类型**：知识盲区
- **位置**：CameraX ZSL 与底层 HAL reprocessing
- **问题**：CameraX ring buffer 如何与 HAL reprocessing request 对应关系不清晰
- **建议**：研究 CameraX ZSL 实现与 HAL reprocessing 的映射关系，分析不同设备 HAL 能力对 ZSL 策略的影响

- **类型**：数据支撑
- **位置**：Stream Use Case 性能影响
- **问题**：不同 Stream Use Case 对 pipeline 延迟和功耗缺少量化数据
- **建议**：补充不同 Stream Use Case 对 pipeline 延迟和功耗的具体影响数据，支持性能调优决策

- **类型**：数据支撑
- **位置**：Buffer 饥饿场景
- **问题**：Buffer 饥饿场景缺少典型阈值数据
- **建议**：补充 ImageReader 回调堆积超过多少帧会被判定为 Buffer 饥饿的典型阈值数据

- **类型**：交叉引用一致性
- **位置**：与 14.9 节引用关系
- **问题**：与 14.9 节 Camera 性能分析的引用关系描述不一致
- **建议**：修正交叉引用，确保章节引用编号和标题准确对应

## [Task9 Deep Review] 26.12 Android 版本化线上诊断能力 — 2026-06-23

- **类型**：源码准确性
- **位置**：ProfilingManager 源码路径
- **问题**：引用路径错误：`frameworks/base/core/java/android/os/ProfilingManager.java` 应为 `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`
- **建议**：更新源码路径引用，确保指向正确的 ProfilingManager 位置

- **类型**：版本差异覆盖
- **位置**：Android 17 MemoryLimiter 行为
- **问题**：Android 17 对高 RAM 设备引入保守应用内存限制的行为未在章节中体现
- **建议**：在版本演进表和证据归档中增加 MemoryLimiter 相关说明，补充退出时的 MemoryLimiter 描述

- **类型**：原理链完整性
- **位置**：ApplicationExitInfo 与 ProfilingManager 证据互补关系
- **问题**：未说明两类证据如何去重和互补
- **建议**：补充相同场景下两种证据的优先级和互补逻辑，建立完整的诊断证据链

- **类型**：知识盲区
- **位置**：StatsD 原子数据与诊断能力集成
- **问题**：StatsD 原子计数器与 ApplicationExitInfo 状态的关联分析缺失
- **建议**：研究 Android StatsD 原子计数器的采集机制，分析与 ApplicationExitInfo 的集成关系

- **类型**：知识盲区
- **位置**：ProfilingManager FLAG_TELEMETRY_APIS 启用条件
- **问题**：Telemetry APIs 启用条件和设备兼容性判断不明确
- **建议**：明确 Telemetry APIs 的启用条件和设备兼容性判断标准

- **类型**：知识盲区
- **位置**：ProfilingService 服务端实现
- **问题**：ProfilingService 后端处理流程和限流机制未详细说明
- **建议**：补充 ProfilingService 服务端处理流程和限流机制的详细说明

- **类型**：数据支撑
- **位置**：ProfilingManager rate limiter 阈值
- **问题**：系统级和进程级限流的具体数值和计算方式未明确
- **建议**：补充 ProfilingManager 系统级和进程级限流的具体数值和计算方式

- **类型**：数据支撑
- **位置**：各 ProfilingType 文件大小和耗时
- **问题**：system trace、heap dump 等的典型文件大小和采集耗时未给出
- **建议**：补充各 ProfilingType 的典型文件大小和采集耗时数据

- **类型**：交叉引用一致性
- **位置**：与 8.10 节引用关系
- **问题**：与 8.10 节 ProfilingTrigger 的实现细节描述有冲突
- **建议**：明确引用范围，区分客户端和服务端实现细节

## [Task9 Deep Review] 25.2 后台功耗治理 — 2026-06-23

- **类型**：知识盲区
- **位置**：WorkManager 与 JobScheduler 实现差异
- **问题**：Android 15+ JobScheduler quota 控制与 WorkManager 的映射关系不清晰
- **建议**：补充 Android 15+ JobScheduler quota 控制与 WorkManager 的映射关系说明

- **类型**：数据支撑
- **位置**：后台定位功耗对比
- **问题**：不同定位优先级（NO_POWER/BALANCED/HIGH_ACCURACY）的典型功耗范围未给出
- **建议**：补充不同定位优先级的典型功耗范围数据，支持功耗优化决策

## [Task9 Deep Review] 20.7 异常处理架构设计 — 2026-06-23

### P2 建议改进：

- **类型**：版本差异覆盖
- **位置**：getTraceInputStream() 方法说明
- **问题**：Android 11/API 30 引入该方法用于 REASON_ANR，Android 12/API 31 起扩展用于 REASON_CRASH_NATIVE，但底层存储是全局循环缓冲区，高崩溃频率下会被覆盖并返回 null。现有表述未清晰说明版本差异和限制条件。
- **建议**：添加版本表格说明不同 Android 版本中该方法的可用性和限制，特别强调高崩溃频率下的数据丢失风险。

- **类型**：版本差异覆盖
- **位置**：ApplicationExitInfo 兼容性
- **问题**：章节标注适用 Android 10-37，但 Android 10 缺少 ApplicationExitInfo，fallback 机制依赖本地记录，实现细节不足。
- **建议**：为 Android 10 单独添加 fallback 策略说明，明确 getHistoricalProcessExitReasons() 不可用时的本地记录替代方案。

- **类型**：原理链完整性
- **位置**：SupervisorScope 异常处理
- **问题**：未说明子任务失败如何影响同级任务，以及异常在不同作用域间的传播规则，影响开发者正确设计异常边界。
- **建议**：补充 SupervisorScope 中子任务异常传播示意图，说明取消传播和独立失败的处理策略。

- **类型**：数据支撑
- **位置**：SafeMode 阈值设定
- **问题**："阈值不要写死在代码里，应当由本地默认值和远程配置共同决定"缺少量化指导原则，开发者难以确定合理的默认阈值。
- **建议**：提供基于 DAU、启动路径和 Crash 分布的阈值计算公式和实际业务案例参考。

- **类型**：交叉引用一致性
- **位置**：与 26.2 Crash 上报体系集成
- **问题**：章节末尾提到"与 26.2 的稳定性指标合并设计"，但缺少具体的集成路径和字段映射说明。
- **建议**：添加与 26.2 的数据流转图，明确 crash_envelope、runtime_context 与上报系统的字段映射关系。

- **类型**：原理链完整性
- **位置**：多进程崩溃文件处理
- **问题**：缺少跨版本升级后历史 crash 记录的处理原理，可能导致升级后的记录混乱或丢失。
- **建议**：补充版本升级时的文件迁移和清理策略，说明如何处理不同版本间的记录格式变化。

- **类型**：数据支撑
- **位置**：性能影响说明
- **问题**："指数退避、本地计数、达到阈值后关闭"等策略缺少性能影响数据，难以评估实现成本。
- **建议**：提供典型场景下的重启延迟和资源消耗数据，帮助开发者权衡保活要求和用户体验。

- **类型**：知识盲区
- **位置**：协程异常与页面生命周期绑定
- **问题**：缺少 viewModelScope、lifecycleScope 异常的具体实现示例，难以判断页面销毁时序相关的异常处理。
- **建议**：添加页面销毁时协程异常的处理示例，说明如何避免内存泄漏和不必要的异常上报。

## [Task9 Deep Review] 8.10 ProfilingManager 系统触发式性能追踪 — 2026-06-23

- **类型**：源码准确性
- **位置**：ANOMALY 产物动态性说明
- **问题**：ANOMALY 触发器的产物类型选择逻辑不清晰，何时返回 heap dump vs stack sampling 的判断标准未明确
- **建议**：补充具体的 anomaly-detector 规则判断逻辑，或说明产物类型由 anomaly 类型决定的具体机制

## [Task9 Deep Review] 8.10 ProfilingManager 系统触发式性能追踪 — 2026-06-23

- **类型**：版本差异
- **位置**：Android 17 APP_COMPAT=11 描述
- **问题**：APP_COMPAT trigger 描述过于简略，未说明具体使用场景和产物类型
- **建议**：补充 APP_COMPAT 的具体使用场景、返回产物类型和分析方法

## [Task9 Deep Review] 8.10 ProfilingManager 系统触发式性能追踪 — 2026-06-23

- **类型**：数据支撑
- **位置**：性能影响章节
- **问题**：缺少具体的性能基准数据支持
- **建议**：补充不同 trigger 类型的内存占用、CPU 占用、存储占用等量化数据，以及针对不同使用场景的优化建议

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-06-23

- **类型**：源码准确性
- **位置**：Canvas.java 源码路径
- **问题**：引用路径错误 - frameworks/base/graphics/java/android/graphics/Canvas.java 在 AOSP android-16.0.0_r1 中存在，但调用链中的 BaseCanvas.java 路径不准确
- **建议**：统一引用 frameworks/base/graphics/java/android/graphics/ 包下的 Canvas.java 和 BaseCanvas.java 路径

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-06-23

- **类型**：版本差异覆盖
- **位置**：Android 16 瓦片大小相关内容
- **问题**：文中提到"在统一内存架构下"，但对 Android 16 的统一内存架构变化描述较少，缺少对 16KB 页环境下 GPU 内存管理变化的补充
- **建议**：补充 Android 16 统一内存架构变化和 16KB 页环境下 GPU 内存管理的具体说明

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-06-23

- **类型**：数据支撑
- **位置**：GPU 性能数据
- **问题**：缺少 "GPU busy" 计数器的具体数值对比或实际案例分析
- **建议**：补充 GPU busy 计数器在不同场景下的具体数值对比或实际案例分析

## [Task9 Deep Review] 4.5 App 内存优化 — 2026-06-23

- **类型**：知识盲区
- **位置**：大型 App 内存预算管理
- **问题**：仅提到分层思路，缺少大型 App 内存预算模型和内存压力监测的具体实践
- **建议**：补充大型 App 内存预算模型和内存压力监测的具体实践案例

## [Task9 Deep Review] 4.5 App 内存优化 — 2026-06-23

- **类型**：数据支撑
- **位置**：优化数据支撑
- **问题**：内存优化章节缺少优化前后的具体数据对比
- **建议**：补充内存优化前后的具体数据对比案例

## [Task6 Review] 19.10 其他开源 APM 库 — 2026-06-23
- **类型**：L3 内容深度
- **位置**：横向对比表格
- **问题**：缺乏具体的项目落地数据支持各类方案的实际表现
- **建议**：补充真实项目中各类 APM 方案的成本对比数据或明确标注为"理论分析"

## [Task6 Review] 19.10 其他开源 APM 库 — 2026-06-23
- **类型**：L4 活人感
- **位置**：使用建议段落
- **问题**：内容像标准检查清单，缺乏具体场景的选择判断依据
- **建议**：增加团队实际决策时的具体案例和判断逻辑

## [Task6 Review] 7.7 Jetpack Compose 性能优化 — 2026-06-23
- **类型**：L3 内容深度
- **位置**："与传统 View 体系的性能对比"段落
- **问题**：缺乏具体的数据支撑和对比测试方法论
- **建议**：补充真实的设备测试数据或明确标注为"理论分析"

## [Task6 Review] 7.7 Jetpack Compose 性能优化 — 2026-06-23
- **类型**：L4 活人感  
- **位置**："为什么要关注 Compose 的性能"段落
- **问题**：部分内容读起来像AI整理材料，缺乏个人观察痕迹
- **建议**：增加实际项目中遇到的具体案例和判断依据

## [Task6 Review] 7.7 Jetpack Compose 性能优化 — 2026-06-23
- **类型**：L1 事实准确性
- **位置**："PausableComposition"描述
- **问题**：版本边界描述不够精确
- **建议**：需要核实具体的Compose Runtime版本边界

## [Task2B 回炉阻塞] 8.10 ProfilingManager — 2026-06-23

**原因**：Task 9 Deep Tech Review 指出章节引用的 AOSP 源码路径（`packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`）在 android-17.0.0_r1 及之前 tag 中均未公开，无法验证章节技术描述的准确性。

**状态**：`blocked` — 须等待 Android Profiling 模块源码公开，或由高爷确认是否标注「源码未公开，基于文档推断」。

**来源 queue 条目**：priority 95, added_by task9-deep-tech-review

## [Task6 Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-06-24
- **类型**：需重写 / 需修正
- **位置**：多处（详见下）
- **问题**：
  1. **代码示例 Java/C 混用**（§应用场景 > 代码注入）：```c 代码块中使用 Java Intent 类型，`intent.getAction().equals()` 是 Java 语法
  2. **try/catch 错误处理模式**（§错误处理和恢复）：try/catch 是 C++ 语法，纯 C Hook 场景应用返回值检查（已临时修正语言标签为 cpp）
  3. **未来发展章节填充**（§Hook 技术的未来发展）：整节内容已被现有工具实现或过于笼统，违反 writing-guide 禁止填充原则
  4. **JIT 优化建议不当**（§最佳实践 > 优化 Hook 性能）：ART JIT 只优化 Java/Kotlin 方法，不适用于 C Hook 函数
  5. **多处伪代码未标注**（§实际应用案例 案例 1-2）：hook_sched_switch 等函数签名是虚构的，读者可能误以为可照搬
- **建议**：见上述逐条；详细 review 日志见 logs/review/2026-06-24-01-review.md
- **review 日志**：logs/review/2026-06-24-01-review.md
