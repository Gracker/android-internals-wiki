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

[223 more lines in file]

---

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：源码准确性
- **位置**：API版本映射描述
- **问题**：章节提到"Android 15 (API 35)"将 PowerMonitor API 开放到应用层，但表述方式易混淆。Android 15对应API 35，Android 17对应API 37。这种版本数字描述方式违反了清晰的版本映射规则。
- **建议**：修正版本映射表述，明确 Android 15 ↔ API 35，Android 17 ↔ API 37 的对应关系，避免版本数字混淆。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：源码准确性
- **位置**：PowerMonitorReadings.getConsumedEnergy() 方法描述
- **问题**：章节提到 PowerMonitorReadings.getConsumedEnergy() 方法返回累计能耗，但未在 android-17.0.0_r1 中验证该方法的确切签名和返回类型。API 35 的 PowerMonitor 系列接口在 Android 17 中的支持状态需要确认。
- **建议**：确认 PowerMonitor API 在 Android 17 中的支持状态和 API 签名，如存在则明确标注，如不存在需调整内容描述。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：源码准确性
- **位置**：NDK performance_hint.h 路径描述
- **问题**：章节提到 NDK performance_hint.h 在 r28+ 重组，但未说明完整路径变更细节和 API 签名变化。开发者无法确定具体的文件位置和兼容性要求。
- **建议**：补充 NDK performance_hint.h 在 Android 17 中的完整路径变更说明和 API 签名兼容性信息。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：原理链完整性
- **位置**：ADPF PowerMonitor 协作方案
- **问题**：章节提到"PowerMonitor 采样 → 分析能耗特征 → 判断是否启用 power efficiency mode"的协作方案，但缺少了关键的技术细节：如何从 PowerMonitor 的累计能耗数据推导出具体的能耗特征，以及判断逻辑的具体实现机制。
- **建议**：补充从 PowerMonitor 累计能耗数据推导具体能耗特征的技术细节，以及判断逻辑的具体实现机制，完善原理链。

### [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-07-07
- **类型**：版本差异覆盖
- **位置**：Android 17功耗隐私保护机制
- **问题**：章节仅在源码调研部分提到Android 17的功耗隐私保护机制，但未在正文中充分说明这些机制对普通应用的限制影响。普通应用最大20秒数据延迟，250ms粒度需要系统权限，这对功耗分析的准确性有重要影响。
- **建议**：在正文中补充Android 17功耗隐私保护机制对普通应用的限制说明，包括数据粒度差异和权限要求。