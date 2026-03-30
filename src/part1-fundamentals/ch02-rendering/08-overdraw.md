---
title: "过度绘制"
chapter: "2.8"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['overdraw']
related_chapters: []
---

# 过度绘制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 过度绘制的定义：同一像素在一帧内被绘制多次
- 🔹 过度绘制的性能影响：GPU fillrate 消耗、内存带宽浪费
- 🔹 检测方法：开发者选项中的 GPU 过度绘制调试工具（颜色层次：蓝-绿-粉-红）
- 🔹 常见过度绘制原因：多层背景叠加、不必要的全屏绘制、透明区域
- 🔹 优化手段：移除多余背景、clipRect、减少层级、自定义 View 的 canvas.clipRect/quickReject

### 扩展（可选深入）

- 🔸 Compose 中过度绘制的特点与排查
- 🔸 GPU Profiler 中观察 overdraw 的方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
