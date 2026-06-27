## [Task9 Deep Review] 14.16 Layout Inspector 与 ViewDebug 布局调试 — 2026-06-28
- **类型**：原理链完整性
- **位置**：invalidate 与 measure/layout 关系说明
- **问题**：未充分解释 invalidate 触发后的完整调用链，特别是与 measure/layout 阶段的因果关系
- **建议**：补充 invalidate → PFLAG_DIRTY → Choreographer callback → scheduleTraversals → performMeasure/performLayout 的完整流程说明

## [Task9 Deep Review] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 2026-06-28
- **类型**：数据支撑
- **位置**：heap dump 性能影响数据
- **问题**：章节中提到的 heap dump 暂停时长和 I/O 压力数据缺少实际测量来源和实验条件说明
- **建议**：补充具体的测试环境、堆大小范围、实际测量数据来源，或注明数据来自第三方研究报告

## [Task9 Deep Review] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 2026-06-28
- **类型**：交叉引用一致性
- **位置**：§19.3 章节引用
- **问题**：章节中引用 §19.3 讲述 KOOM fork-dump，但该章节编号可能不存在或内容不符
- **建议**：验证 §19.3 章节是否存在并包含相关内容，或修正为正确的章节编号