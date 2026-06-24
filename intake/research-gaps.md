## [2026-06-25] 2.14 图形 API 演进与选择策略 — 知识盲区

### 盲区描述
WebGPU 在 Android 上的实际性能数据基准测试较少，缺少具体设备上的吞吐量对比数据，影响开发者进行 API 选型决策。

### 重要程度
中

### �议研究方向
- 收集不同 Android 设备（高端/中端/低端）上 WebGPU vs Vulkan vs OpenGL ES 的性能对比数据
- 测试典型工作负载（游戏渲染、图像处理、ML推理）下的 GPU 吞吐量和延迟
- 分析 WebGPU 在不同 Vulkan 版本（1.0/1.1/1.3/1.4）设备上的性能表现差异
- 建立 WebGPU 的适用性评估框架，帮助开发者判断何时选择 WebGPU 更合适

### 关联章节
2.10 GPU 渲染深入; 14.8 GPU 图形调试与分析工具

## [2026-06-25] 2.14 图形 API 演进与选择策略 — 知识盲区

### 盲区描述
WebGPU 在 Android 上的实际性能数据基准测试较少，缺少具体设备上的吞吐量对比数据，影响开发者进行 API 选型决策。

### 重要程度
中

### 建议研究方向
- 收集不同 Android 设备（高端/中端/低端）上 WebGPU vs Vulkan vs OpenGL ES 的性能对比数据
- 测试典型工作负载（游戏渲染、图像处理、ML推理）下的 GPU 吞吐量和延迟
- 分析 WebGPU 在不同 Vulkan 版本（1.0/1.1/1.3/1.4）设备上的性能表现差异
- 建立 WebGPU 的适用性评估框架，帮助开发者判断何时选择 WebGPU 更合适

### 关联章节
2.10 GPU 渲染深入; 14.8 GPU 图形调试与分析工具
## [2026-06-25] 26.12 Android 版本化线上诊断能力 — 知识盲区

### 盲区描述
Android 17 中  的具体触发条件和产物类型未在源码层面验证，仅基于官方文档描述。该 trigger 对应 "OS-defined memory limits" 临界点，可能覆盖 MemoryLimiter 退出的事前窗口，但具体的触发阈值、产物格式、与  的关系需要进一步研究。

### 重要程度
高（直接影响 Android 17 内存问题诊断能力）

### 建议研究方向
- 深入研究 AOSP android17-release 源码中的 ProfilingTrigger 常量定义
- 验证 ANOMALY trigger 与 MemoryLimiter 的具体关系
- 确定 ANOMALY trigger 的产物类型和格式规范
- 研究 ANOMALY 与其他 trigger（如 OOM、KILL_EXCESSIVE_CPU_USAGE）的边界条件

### 关联章节
- 26.12 (本章)
- 20.5 (OOM 治理策略)
- 19.24 (Crash SDK 机制)
- 8.10 (ProfilingTrigger 接入代码)
