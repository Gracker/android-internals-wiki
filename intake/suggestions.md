## [Task9 Deep Review] 18.16 游戏引擎渲染链路 — 2026-07-16
- **类型**：版本差异
- **位置**：ADPF / Frame Rate API 部分
- **问题**：Android 15/API 35 和 Android 16/API 36 的 API 变化未充分覆盖具体行为边界
- **建议**：补充 API 35 `setPreferPowerEfficiency` 和 API 36 `FRAME_RATE_COMPATIBILITY_AT_LEAST` 的适用场景和边界条件说明

## [Task9 Deep Review] 18.16 游戏引擎渲染链路 — 2026-07-16
- **类型**：数据缺失
- **位置**：DrawCall 合批性能优化部分
- **问题**：缺少具体的 DrawCall 数量与性能影响的数据支撑
- **建议**：补充典型游戏场景下不同 DrawCall 数量（100, 500, 1000, 2000）对帧率和 GPU 负载的实测数据