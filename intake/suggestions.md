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
