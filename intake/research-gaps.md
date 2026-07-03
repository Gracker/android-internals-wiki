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

## [2026-07-04] ch15-methodology — Android 17 FrameRateOverrides 深度机制

### 盲区描述
章节介绍了 Android 17 FrameRateOverrides API 的基本使用，但缺少与底层 VSync 调度机制的深度协同工作原理解释。未说明：1) FrameRateOverrides 如何影响 SurfaceFlinger 的帧调度计划；2) 动态帧率切换时的 VSync offset 调整延迟；3) FrameTimeline Expected Timeline 与实际呈现时间的差异分析。

### 重要程度
高

### 建议研究方向
- 深入研究 FrameRateOverrides 与 SurfaceFlinger VSync 调度的协同机制
- 分析动态帧率切换场景下的性能瓶颈（如 offset 调整延迟）
- 完善 FrameTimeline 数据在 Perfetto trace 中的查询方法

### 关联章节
- ch15-methodology
- ch02-rendering/2.30-android17-frametimeline

---

## [2026-07-04] ch15-methodology — 模拟器 vs 真实设备性能分析差异

### 盲区描述
章节未讨论 Android 模拟器与真实设备在性能分析上的重要差异：1) 模拟器的 ARM 指令集翻译开销；2) Host-OS 资源竞争影响；3) GPU 渲染管道的完全不同实现；4) 系统调用路径差异导致的行为差异。这些差异会导致模拟器上的分析结果无法直接应用到真实设备优化。

### 重要程度
中

### 建议研究方向
- 建立模拟器与真实设备性能差异的校准方法
- 识别哪些性能问题可以在模拟器中准确复现
- 提供模拟器环境下的特殊分析工具和技巧

### 关联章节
- ch15-methodology
- ch13-perfetto/13.21-perfetto-version-evolution
## [2026-07-04] ch15-methodology — 知识盲区

### 盲区描述
Perfetto 在不同 Android 版本中的 tracing 能力差异和 Android 17 Adaptive RefreshRate 对性能分析的具体影响机制

### 重要程度
高

### 建议研究方向
- 深入研究 Android 17 中 FrameRateOverrides API 与 WindowManager 的交互机制
- 分析 Perfetto 在不同 Android 版本中的数据源支持差异
- 调查 Adaptive RefreshRate 场景下的 VSync 调整对渲染管线的影响

### 关联章节
ch15-methodology, 相关的性能优化章节

