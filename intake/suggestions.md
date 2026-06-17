## [Task9 Deep Review] 16.2 各 Android 版本性能变更追踪 — 2026-06-17
- **类型**：源码准确性/版本差异
- **位置**：Android 17 NeuralNetworks HAL 1.3 状态描述段落
- **问题**：文中提到"NN HAL 本身仍维持 1.3 不变"，但源码引用显示只使用 android-16.0.0_r1，未找到 android-17.0.0_r1 的源码锚点，且明确标注"不直接引用行号"
- **建议**：明确区分源码调研边界，标注使用 android-16.0.0_r1 作为锚点的限制，或等待 android-17.0.0_r1 tag 发布后再更新结论

## [Task9 Deep Review] 16.2 各 Android 版本性能变更追踪 — 2026-06-17
- **类型**：版本差异
- **位置**：Android 17 ProfilingManager 触发器描述段落
- **问题**：API 37 触发器描述提到"到 API 37 才出现在公开参考页里"，但未明确标注这些触发器是否可用或在 Android 17 上已稳定，也缺少与 API 36.1 的兼容性说明
- **建议**：补充触发器的稳定性判断（stable/deprecated/experimental），说明与之前版本的增量关系，明确标注在 Android 17 上的实际可用性