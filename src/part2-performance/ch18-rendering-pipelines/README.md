# 第 18 章：渲染链路全景

> 本章系统梳理了 Android 系统中几乎所有的主流出图链路，从最基础的 Android View 标准链路到游戏引擎、Flutter、WebView、Camera 等复杂场景。

## 本章内容

- 渲染链路分类与选择矩阵
- Android View 标准链路（BLAST 深入）
- Android View 软件渲染链路
- Android View 混合渲染链路
- Android View 多窗口链路
- SurfaceView 直出链路
- TextureView 合成链路
- OpenGL ES 渲染链路
- Vulkan 原生渲染链路
- SurfaceControl API 深入
- ANGLE（GLES-over-Vulkan 翻译层）
- Flutter 渲染链路
- WebView 渲染链路（四种模式）
- Camera 渲染管线
- 视频叠加与 HWC
- 游戏引擎渲染链路
- Hardware Buffer Renderer
- PIP 与自由窗口渲染
- 可变刷新率渲染管线
- 链路分析方法论
- EyeDropper API 与跨设备协作性能

## 阅读建议

- **新手入门**：先读 18.1 了解全貌，然后按需阅读具体链路
- **性能分析实战**：直接读 18.20 链路分析方法论，遇到问题再深入对应章节
- **深度理解**：按顺序阅读 18.2 → 18.7（从标准链路到各种变体）
