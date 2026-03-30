---
title: "Jetpack Compose 性能优化"
chapter: "7.7"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['compose', 'jank', 'smoothness', 'recomposition']
related_chapters: []
---

# Jetpack Compose 性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Compose 渲染模型：Composition → Layout → Drawing 三阶段与传统 View 体系的对比
- 🔹 Recomposition 的触发条件与最小化策略：stable 标记、remember、derivedStateOf
- 🔹 Compose 中的性能陷阱：不稳定参数导致的过度重组、LazyColumn 的 key 策略
- 🔹 Compose 性能检测：Layout Inspector Recomposition 计数、Compose Compiler Metrics
- 🔹 Compose 与 View 混合布局的性能考量（ComposeView / AndroidView 开销）

### 扩展（可选深入）

- 🔸 Compose Multiplatform 的性能差异
- 🔸 Compose 动画性能：animate*AsState vs Animatable vs transition

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
