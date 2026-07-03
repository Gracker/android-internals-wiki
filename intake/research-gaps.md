## [2026-07-04] ch15-methodology — Android 17 Perfetto 启用机制

### 盲区描述
当前章节对 Android 17 中 Perfetto 启用机制的描述不够准确，`debug.perfetto.enabled` 与 DeviceConfig 的关系需要进一步澄清。AOSP android-17.0.0_r1 源码显示 `debug.perfetto.enabled` 仍有效，主要启用方式为 `persist.traced.enable=1`，DeviceConfig 提供细粒度控制而非完全替代。

### 重要程度
高

### 建议研究方向
- 深入分析 AOSP android-17.0.0_r1 中 Perfetto 启用机制的完整流程
- 验证 `debug.perfetto.enabled`、`persist.traced.enable=1` 和 DeviceConfig 的优先级关系
- 编写准确的 Android 17 Perfetto 启用方式文档，避免误导开发者

### 关联章节
- ch15-methodology
- ch13-perfetto/13.21-perfetto-version-evolution
- ch2-xxx (可能包含 Perfetto 深度分析章节)