---
title: "图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE）"
chapter: "2.14"
status: draft
applicable_versions: "Android 4.0 (API 14) - Android 17 (API 37)"
tags: [opengl-es, vulkan, angle, gpu, graphics-api, rendering]
related_chapters: ["2.1", "2.9", "2.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "AOSP结构+官方文档+研究素材"
---

# 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE）

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Android 图形 API 的三代演进
- OpenGL ES 1.x → 2.0 → 3.0 → 3.2 的能力演进
- Vulkan 1.0 → 1.1 → 1.3 → 1.4 的引入与推广
- ANGLE（Almost Native Graphics Layer）的定位：GLES → Vulkan 翻译层
- 在 Android 版本时间线上看三代 API 的官方支持状态

### 🔹 锚点 2：Vulkan 与 OpenGL ES 的架构差异
- OpenGL ES 的状态机模型 vs Vulkan 的显式命令模型
- 驱动开销差异：Vulkan 的验证层 vs GLES 的隐式验证
- 多线程渲染能力对比：Vulkan 天然支持 vs GLES 有限支持
- 对性能分析的影响：为什么 Vulkan 更适合精细化的性能调优

### 🔹 锚点 3：ANGLE 的角色与 Android 17 强制迁移
- ANGLE 的工作原理：GLES API 调用 → 翻译为 Vulkan 或 Metal 后端
- Android 12 引入 ANGLE opt-in → Android 15 扩展 → Android 17 强制
- 性能影响：ANGLE 翻译层开销 vs 原生 GLES 驱动开销
- 对现有 GLES 应用的兼容性与迁移路径

### 🔹 锚点 4：API 选择对渲染性能的实际影响
- Vulkan 的 command buffer 复用带来的帧时间优化
- GLES 的 implicit optimization（驱动自动优化）vs Vulkan 的 explicit control
- 在 Perfetto 中对比 Vulkan 和 GLES 的 GPU 时间分布
- 游戏引擎（Unity/Unreal）的 API 选择策略

### 🔹 锚点 5：图形 API 与 Perfetto/工具分析
- 如何在 Perfetto 中识别当前使用的图形 API
- GPU counter 的可用性差异（Vulkan 更丰富的 GPU 性能计数器）
- Android GPU Inspector (AGI) 与不同 API 的兼容性
- 不同 API 在 Frame Timeline 中的表现差异

### 🔹 锚点 6：迁移策略与最佳实践
- 何时选择 Vulkan vs 何时保持 GLES（通过 ANGLE）
- Android 17 ANGLE mandatory 对开发者的实际影响
- 从 GLES 迁移到 Vulkan 的关键步骤与性能陷阱
- 混合使用场景：WebView/WebGL 仍走 GLES 路径

## 扩展

### 🔸 扩展点 1：Vulkan 1.4 的新特性与 Android 17
- Vulkan 1.4 的关键新功能
- 对渲染管线的具体性能影响
- Android 17 要求 Vulkan 1.4 合规的 OEM 影响

### 🔸 扩展点 2：OpenGL ES 的维护模式与未来
- GLES 在 Android 17+ 进入 maintenance mode 的含义
- 长期支持计划（LTS）与新功能开发的停止
- 对遗留 GLES 代码的建议

<!-- outline-end -->

> 本节内容待加工。
