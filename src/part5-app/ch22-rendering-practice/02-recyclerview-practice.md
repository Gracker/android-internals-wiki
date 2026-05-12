---
title: "RecyclerView 最佳实践"
chapter: "22.2"
section: "22.2"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [recyclerview, viewholder, diffutil, prefetch, nested-scroll]
related_chapters: ["22.1", "7.8", "2.4"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# RecyclerView 最佳实践

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ViewHolder 复用与 ItemType 设计
- 🔹 DiffUtil 与增量更新
- 🔹 预取（Prefetch）机制与配置
- 🔹 嵌套滚动与多 RecyclerView 场景优化

### 扩展（可选深入）

- 🔸 RecyclerView vs LazyColumn 性能对比

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解RecyclerView 最佳实践

（待加工）

