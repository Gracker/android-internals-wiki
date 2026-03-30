---
title: "Hardware Layer"
chapter: "2.7"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['hardware-layer']
related_chapters: []
---

# Hardware Layer

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Hardware Layer 的本质：将 View 树缓存为离屏 GPU 纹理
- 🔹 setLayerType(LAYER_TYPE_HARDWARE) 的适用场景：复杂动画、Alpha 变换
- 🔹 Hardware Layer 的代价：额外 GPU 内存、失效与重建开销
- 🔹 何时 Hardware Layer 能提升性能 vs 何时反而劣化

### 扩展（可选深入）

- 🔸 与 RenderNode.setUseCompositingLayer 的关系
- 🔸 在 Compose 中使用 graphicsLayer 的性能考量

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
