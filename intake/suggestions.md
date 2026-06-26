## [Task9 Deep Review] 15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：源码准确性
- **位置**：Line 204-210 (ADB 命令引用)
- **问题**：ADB 命令缺少版本限定说明，部分命令在不同 Android 版本中行为有差异
- **建议**：为每个 ADB 命令添加版本限定条件，例如 `adb shell dumpsys meminfo` 在 Android 8+ 中的输出格式变化，`adb shell top` 在 Android 9+ 中的进程分组特性等

## [Task9 Idle Audit] 15 Android 性能优化研究方法论 — 2026-06-27
- **类型**：版本差异覆盖
- **位置**：Line 233 (Perfetto 版本可用性描述)
- **问题**："Android 9（API 28）起 Perfetto 可用"的描述需要官方文档验证准确性
- **建议**：核实 Perfetto 准确的引入版本，并补充 Android 12+ 中 Perfetto 新特性的说明

## [Task2B Lite 已修复] ch15 方法论 — 2026-06-27
- P1 Perfetto 版本描述：已修正为 Android 9 traced 入 system image 但非 Pixel 需手动 enable，Android 11+ 默认启用
- P2 ADB 命令版本限定：已为 dumpsys meminfo / top / batterystats 补版本说明
- 章节 src/ch15-methodology.md 已回 ready-for-review，待 Task6/Task9 复审
