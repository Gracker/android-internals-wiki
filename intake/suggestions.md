## [Task9 Deep Review] 8.10 ProfilingManager 系统触发式性能追踪 — 源码准确性
- **类型**：源码准确性
- **位置**：系统触发到 ProfilingManager 的触发链路
- **问题**：缺少 ActivityManagerService 如何检测性能问题并调用 ProfilingManager 的中间环节，原理链断裂
- **建议**：补充系统触发机制的完整流程图和关键方法调用链，明确各组件间的交互时序

---

## [Task9 Deep Review] 8.10 ProfilingManager 系统触发式性能追踪 — 版本差异
- **类型**：版本差异
- **位置**：ProfilingManager 适用性说明
- **问题**：未说明在不支持 ProfilingManager 的设备上的降级方案
- **建议**：添加兼容性检查机制和降级策略说明，提供替代的性能监控方案

---

## [Task9 Deep Review] 7.7 Jetpack Compose 性能优化 — 数据支撑
- **类型**：数据支撑
- **位置**：性能对比部分
- **问题**：缺少 LazyColumn 和 RecyclerView 的具体性能对比数据，缺乏量化分析
- **建议**：补充 Macrobenchmark 或 Perfetto 的实际测试数据，包括不同设备、不同滚动速度下的帧耗时对比

---

## [Task9 Deep Review] 7.7 Jetpack Compose 性能优化 — 版本演进
- **类型**：版本差异
- **位置**：PausableComposition 说明
- **问题**：未详细说明 Compose 1.0-1.5 中 PausableComposition 的实现变化
- **建议**：补充 PausableComposition 在不同 Compose 版本中的演进历程，重点说明 1.3 和 1.5 中的重大改进

---

## [Task9 Deep Review] 4.5 App 内存优化 — 数据支撑
- **类型**：数据支撑
- **位置**：16KB Page Size 迁移部分
- **问题**：缺少 16KB Page Size 对实际 App 启动时间的具体影响数据
- **建议**：补充实际测试数据，包括不同类型应用（冷启动、热启动）的启动时间改善幅度，以及内存使用变化

---

## [Task9 Deep Review] 4.5 App 内存优化 — 知识盲区补充
- **类型**：知识盲区
- **位置**：内存优化策略部分
- **问题**：未详细说明 Android 17 中新增的内存管理特性
- **建议**：补充 Android 17 新增的内存相关 API 和优化建议，特别是与 Jetpack Compose 相关的内存管理最佳实践

## [Task6 Review] 14.13 Hook 基础设施 — 2026-06-24
- **类型**：技术矛盾（L3）
- **位置**：PLT vs Inline Hook 对比表 — "绕过方式"行
- **问题**：对比表将 IFUNC resolver 列为 Inline Hook 的绕过方式（"函数内跳指令（如 IFUNC resolver）"），但正文紧接其下明确写道"使用 IFUNC resolver 在 linker 阶段替换实现，PLT Hook 就拦截不到。这些场景必须用 inline hook"。表格与正文对 IFUNC 的定位矛盾。
- **建议**：修正对比表 — PLT Hook 的绕过方式应包含"dlsym 直接调用"和"IFUNC resolver 替换"；Inline Hook 的绕过方式应改为"函数内 tail call / 间接分支"等真正能绕过入口覆写的场景。
- **review 日志**：logs/review/2026-06-24-12-review.md
