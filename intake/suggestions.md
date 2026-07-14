## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15
- **类型**：版本差异覆盖
- **位置**：游戏引擎 API 支持情况
- **问题**：未明确说明兼容的 Unity/Unreal 版本范围，特别是 Android 17 对这些引擎 API 的限制或增强
- **建议**：补充 Unity/Unreal 在 Android 17 中的兼容性说明，包括 API 版本要求和新特性支持

## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15
- **类型**：知识盲区
- **位置**：GPU 计算任务调度优化
- **问题**：未讨论 Android 17 中的 GPU 计算任务调度优化，包括 compute shader 分时调度和后台计算任务管理
- **建议**：补充 Android 17 GPU 计算任务调度的优化机制，说明其对 GPU 性能监控的新影响