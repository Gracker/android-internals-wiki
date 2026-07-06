## [Task9 Deep Review] 15.5 线上性能监控 — 2026-07-06
- **类型**：版本差异
- **位置**：ProfilingManager 和 ProfilingTrigger 版本边界描述
- **问题**：章节中提到的 API 版本引入时间与实际 AOSP android-17.0.0_r1 源码存在差异。ProfilingManager 在 Android 14 (API 34) 已引入，章节误标为 Android 15 (API 35)；ProfilingTrigger 在 android-16.0.0_r1 中已存在，章节误标为 Android 16 (API 36) 才加入。
- **建议**：修正 API 版本边界，补充准确的版本信息：ProfilingManager 实际从 Android 14 (API 34) 开始可用；ProfilingTrigger 在 Android 16 (API 35) 引入，并提供具体的源码路径验证。
---

## [Task9 Idle Audit] 15 Android 性能优化研究方法论 — 2026-07-06
- **类型**：源码准确性
- **位置**：第3.4节 VSync 组件描述
- **问题**：VSyncTracker 描述过于简化，实际涉及多组件协作
- **建议**：补充 VSyncTracker、VSyncModulator、VSyncDispatch 的协作关系说明，与实际 AOSP 实现保持一致

## [Task2B 回炉修复] 20.9 稳定性治理案例集 — 2026-07-06 12:50

来源：frontmatter backlog fallback（task9_result: needs-rework → 2026-07-06 deep-review）

修复内容（P1 3 项 / P2 4 项）：
- P1-1: 扩充 Android 17 信号处理机制（async-signal-safe 校验细则、线程亲和性信号分发、动态 altstack）
- P1-2: 扩充线程亲和性管理讨论（崩溃监控/信号处理确定性/性能关键路径隔离三大场景 + 注意事项）
- P1-3: 扩充 Android 17 线程监控 API（getThreadCpuTime / getThreadPriority / sched 表格 + 使用场景）
- P2-1: 增强 Android 5.0 vs 17 适用性说明（debuggerd handler 链的具体变化）
- P2-2: 增强 Android 15→17 信号处理演进时间线
- P2-3: OOM 案例补充虚拟内存碎片化分析（smaps/maps 碎片模式 + Perfetto 观察方法）
- P2-4: 补充 Android 12+ THREAD_PRIORITY_* 与 cgroup v2 调度讨论
- 修复 frontmatter 重复 key（task2b_state ×2、pipeline_stage 冲突、task2b_result 重复）

状态：pipeline_stage → task6_pending，task9_result → revisiting，等待 Task6 复审

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-06
- **类型**：源码准确性
- **位置**：AGI System Profiler 与 APA System Profiler 对比表格
- **问题**：AGI 的最低支持版本标注为 Android 11，但 AOSP android-17.0.0_r1 中 AGI 的最低支持版本实际为 Android 10
- **建议**：修正为 Android 10+

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-06
- **类型**：版本差异覆盖
- **位置**：Android 17 ANGLE 策略说明
- **问题**：缺少对 Android 15-16 的 allowlist 策略与 Android 17 denylist 策略的对比说明
- **建议**：补充两种策略的具体差异和迁移指导

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-06
- **类型**：知识盲区
- **位置**：GPU Profiling 应用场景
- **问题**：缺少对游戏开发中 GPU Profiling 的特殊考虑，如 Shader 变体预热、Pipeline Cache 优化等
- **建议**：增加游戏开发专属章节，涵盖游戏行业最佳实践

## [Task9 Deep Review] 20.9 稳定性治理案例集 — 2026-07-06
- **类型**：源码准确性
- **位置**：ComputerEngine.java 路径引用
- **问题**：在 AOSP android-17.0.0_r1 中的路径引用需要更新
- **建议**：验证并更新正确的 AOSP 路径

## [Task9 Deep Review] 20.9 稳定性治理案例集 — 2026-07-06
- **类型**：源码准确性
- **位置**：debuggerd_handler.cpp 路径引用
- **问题**：Android 17 中 debuggerd_handler.cpp 已迁移到 bionic/linker/linker_debuggerd_android.cpp
- **建议**：更新路径引用并说明迁移背景

## [Task9 Deep Review] 20.9 稳定性治理案例集 — 2026-07-06
- **类型**：知识盲区
- **位置**：Android 17 线程监控 API
- **问题**：缺少对 android.os.Process.getThreadCpuTime() 等新 API 的具体使用示例
- **建议**：增加线程监控 API 的使用示例和最佳实践
## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-06
- **类型**：源码路径修正
- **位置**：Perfetto GPU 配置 proto 路径引用
- **问题**：引用路径 `protos/perfetto/config/gpu/gpu_counter_config.proto` 与实际 AOSP android-17.0.0_r1 结构不符
- **建议**：更新为正确路径 `system/perfetto/protos/gpu_config.proto`

## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-07-06
- **类型**：版本差异
- **位置**：Android 17 ANGLE denylist 影响
- **问题**：denylist 模式下 AGI Frame Profiler 对 GLES 应用的分析路径差异描述不完整
- **建议**：补充 denylist 设备上 AGI 的特殊处理逻辑和结果解读指南

## [Task9 Deep Review] 20.9 稳定性治理案例集 — 2026-07-06
- **类型**：源码准确性
- **位置**：debuggerd 路径引用
- **问题**：未体现 Android 17 debuggerd 架构迁移，路径引用过时
- **建议**：更新路径为 `bionic/linker/linker_debuggerd_android.cpp` 并说明架构变化

## [Task9 Deep Review] 20.9 稳定性治理案例集 — 2026-07-06
- **类型**：知识盲区
- **位置**：线程监控 API
- **问题**：未详细说明 Android 17 新增的 `Process.getThreadCpuTime()` 64位计数器修复
- **建议**：补充 API 使用示例、性能对比数据以及与旧版本 32位计数的差异说明

## [Task9 Deep Review] 14.8 GPU图形调试与分析工具 — 2026-07-06
- **类型**：源码路径修正
- **位置**：Perfetto GPU 配置 proto 路径引用
- **问题**：引用路径 `protos/perfetto/config/gpu/gpu_counter_config.proto` 与实际 AOSP android-17.0.0_r1 结构不符
- **建议**：更新为正确路径 `system/perfetto/protos/gpu_config.proto`

## [Task9 Deep Review] 14.8 GPU图形调试与分析工具 — 2026-07-06
- **类型**：版本差异
- **位置**：Android 17 ANGLE denylist 影响
- **问题**：denylist 模式下 AGI Frame Profiler 对 GLES 应用的分析路径差异描述不完整
- **建议**：补充 denylist 设备上 AGI 的特殊处理逻辑和结果解读指南

## [Task9 Deep Review] 14.8 GPU图形调试与分析工具 — 2026-07-06
- **类型**：知识盲区
- **位置**：AGI 最低支持版本
- **问题**：章节中提到的 AGI 最低支持版本标注为 Android 11，但 AOSP android-17.0.0_r1 中 AGI 的最低支持版本实际为 Android 10
- **建议**：修正为 Android 10+

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：源码准确性
- **位置**：PowerStatsAggregator 路径描述
- **问题**：文中提到 PowerStatsAggregator 在 Android 16/17 中迁移到新路径，但未在 android-17.0.0_r1 中验证该路径存在，可能导致开发者找不到对应源码
- **建议**：验证 PowerStatsAggregator 在 Android 17 中的实际存在路径，如已迁移需要更新说明

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：源码准确性
- **位置**：BatteryUsageStats 系列类路径
- **问题**：BatteryUsageStats、BatteryUsageStatsQuery、BatteryConsumer、BatteryStatsHistory 等类的引用路径在 android-17.0.0_r1 中均无法找到，说明统一归因 API 在 Android 17 中可能重大重构
- **建议**：重新验证这些核心类的路径和 API 在 Android 17 中的实际存在性，如不存在需要重新组织内容说明

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：数据支撑
- **位置**：ADPF Power Efficiency Mode 与 PowerMonitor 协作章节
- **问题**：协作方案缺乏具体的使用案例和验证步骤，开发者难以理解和应用
- **建议**：补充具体的代码示例、验证步骤和预期效果对比，帮助开发者理解和应用协作方案


## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：版本差异
- **位置**：PowerMonitor API 适用版本描述
- **问题**：章节提到 Android 15 (API 35) 开放了 PowerMonitor API，但未说明 API 29 的 Macrobenchmark PowerMetric 兼容性要求和 API 35 的具体变化，导致开发者对适用范围判断不清晰
- **建议**：补充 PowerMonitor API 版本兼容性说明：1) 明确 API 35 是应用层开放时间，2) 说明 API 29 Macrobenchmark PowerMetric 的基础能力，3) 列出 API 35 相比之前版本的具体新增功能，4) 提供版本兼容性检查建议

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：数据支撑
- **位置**：ADPF Power Efficiency Mode 效果描述
- **问题**：章节提到 "功耗降低 15-30%" 但缺少具体测试数据、基准参考或实际案例支撑，这一数字缺乏可验证性
- **建议**：补充 "功耗降低 15-30%" 的具体测试背景和数据来源：1) 提供测试设备和环境描述，2) 给出具体的基准对比数据表格，3) 说明测试用例和持续时间，4) 提供其他研究或厂商报告的交叉验证

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：知识盲区
- **位置**：ADPF + PowerMonitor 协作方案
- **问题**：章节描述了 ADPF + PowerMonitor 协作的理论机制，但缺少实际应用案例和最佳实践指导，开发者难以理解如何在实际项目中落地
- **建议**：补充 ADPF + PowerMonitor 的实际应用案例：1) 提供完整的代码示例展示协作流程，2) 说明常见的使用场景和适用条件，3) 给出配置调优的最佳实践，4) 列出常见问题和解决方案

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：源码准确性
- **位置**：ADPF 与 PowerMonitor 协作机制说明
- **问题**：未说明如何在代码层面将 PowerMonitor 数据用于 setPreferPowerEfficiency 决策，缺少具体的代码示例和数据流转说明
- **建议**：补充从 PowerMonitor 采样 → 分析能耗特征 → 调用 setPreferPowerEfficiency → 再次采样的完整代码示例，说明如何判断何时启用 power efficiency mode

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：数据支撑
- **位置**：功耗对比数据部分
- **问题**：缺少实际功耗对比数据（如优化前后的 CPU rail 功耗下降百分比）和典型设备的功耗基准数据
- **建议**：添加 Pixel 6/7/8 各子系统（CPU、GPU、Display、Network）的典型功耗范围数据，以及常见优化场景（如网络请求合并、GPS 优化）的功耗改善百分比案例

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-06
- **类型**：版本差异
- **位置**：Android 17 PowerMonitor API 新功能说明
- **问题**：Android 17 中新增的细粒度 rail 分组特性未展开说明，读者无法了解新版本的具体增强
- **建议**：补充 Android 17 中 PowerMonitor 新增的细粒度 rail 分组功能说明，包括新增的 rail 类型、精度提升、以及相应的代码适配建议

