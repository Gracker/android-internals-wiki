---
title: "优化策略"
chapter: "7.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['optimization', 'recyclerview', 'compose']
related_chapters: []
---

# 优化策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 布局优化：减少层级、ConstraintLayout、ViewStub 延迟加载
- 🔹 RecyclerView 优化：预创建 ViewHolder、DiffUtil、SnapHelper 性能考量
- 🔹 渲染优化：减少 overdraw、合理使用 Hardware Layer、Canvas 操作简化
- 🔹 线程优化：耗时操作异步化、Binder 调用优化、合理的线程池配置
- 🔹 Compose 性能优化：减少重组（Recomposition）、stable 标记、remember/derivedStateOf

### 扩展（可选深入）

- 🔸 RenderEffect / Blur 等特效的性能考量
- 🔸 预渲染（Prefetch）与预计算策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
