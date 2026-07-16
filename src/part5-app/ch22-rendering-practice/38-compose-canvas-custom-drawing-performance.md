---
title: "Compose Canvas 自定义绘制性能实战"
chapter: "22.38"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, canvas, custom-drawing, drawbehind, drawwithcontent, graphicslayer, rendernode]
related_chapters: ["2.1", "2.3", "7.7", "22.3", "22.25", "22.31"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "章节深挖 + 官方文档"
---

# 22.38 Compose Canvas 自定义绘制性能实战

<!-- outline-start -->
## 要点

### 🔹 Compose Canvas 绘制模型
- `Canvas(drawScope)` 的底层实现：Skia direct binding vs DisplayList
- `drawBehind` / `drawWithContent` / `drawIntoCanvas` 的语义差异
- DrawScope 与 Paint 的对象复用策略
- Compose 绘制 vs View `onDraw(Canvas)` 的性能等价性分析

### 🔹 GraphicsLayer 与硬件加速
- `Modifier.graphicsLayer` 的 RenderNode 映射
- `GraphicsLayer` 的 clip / transform / alpha 合成路径
- 硬件层缓存（Hardware Layer Caching）的启用条件
- 多层 graphicsLayer 嵌套的性能开销

### 🔹 绘制性能关键模式
- 常见性能陷阱：每帧创建 Paint 对象、频繁 Path 分配
- `rememberObject` / `remember { Paint() }` 缓存绘制资源
- 复杂图形的离屏缓冲（saveLayer）与 Compose 等价方案
- 大面积渐变 / 模糊效果的帧时间影响

### 🔹 自定义绘制与重组的关系
- `drawBehind` 不触发重组 — 绘制阶段与组合阶段的解耦
- 状态读取导致绘制层 invalidate 的机制
- `drawWithContent` 中读取 state 的正确模式
- 避免在绘制阶段进行昂贵计算

### 🔹 实战场景与优化策略
- 粒子效果 / 动画背景：Canvas draw vs SurfaceView 取舍
- 自定义图表（折线图、柱状图）：缓存策略与增量绘制
- 动态壁纸 / 全屏着色器：RuntimeShader 与 Canvas 的协作
- 墨迹书写 / 手势绘制：Path 增量追加与 Surface 性能

### 🔹 与性能工具链配合
- `androidx.tracing` 标记 Compose 绘制阶段
- Perfetto 中 `FrameTimeslice` 识别绘制阶段耗时
- Layout Inspector 的 Compose Recomposition Counts
- Profile Installer 确保绘制代码被 AOT 编译

### 🔹 Android 17 相关变化
- Skia GPU 线程模型变更对 Compose Canvas 的影响
- Vulkan 后端下 Canvas API 的行为差异
- Hardware Bitmap 与 Canvas 绘制的互操作

## 扩展

### 🔸 Vulkan 后端对 Canvas 绘制路径的影响
- 详见 2.15 节（Android 17 GPU 图形调试与性能优化工具链）
- Vulkan vs GLES 下 DrawOp 提交延迟差异

### 🔸 Compose Canvas 在游戏化 UI 中的边界
- Compose Canvas 与 SurfaceView/TextureView 的混合方案
- 独立渲染线程的可行性评估

<!-- outline-end -->

> 本节内容待加工。
