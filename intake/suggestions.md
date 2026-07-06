## [Task9 Deep Review] 15.5 线上性能监控 — 2026-07-06
- **类型**：版本差异
- **位置**：ProfilingManager 和 ProfilingTrigger 版本边界描述
- **问题**：章节中提到的 API 版本引入时间与实际 AOSP android-17.0.0_r1 源码存在差异。ProfilingManager 在 Android 14 (API 34) 已引入，章节误标为 Android 15 (API 35)；ProfilingTrigger 在 android-16.0.0_r1 中已存在，章节误标为 Android 16 (API 36) 才加入。
- **建议**：修正 API 版本边界，补充准确的版本信息：ProfilingManager 实际从 Android 14 (API 34) 开始可用；ProfilingTrigger 在 Android 16 (API 35) 引入，并提供具体的源码路径验证。
---

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
