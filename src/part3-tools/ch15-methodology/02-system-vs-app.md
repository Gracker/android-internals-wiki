---
title: "如何区分系统问题和 App 问题"
chapter: "15.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['methodology']
related_chapters: []
---

# 如何区分系统问题和 App 问题

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 区分系统问题 vs App 问题的重要性
- 🔹 从 Trace 判断：CPU 调度延迟 → 系统、主线程耗时 → App
- 🔹 系统负载高的特征：CPU 全核满载、kswapd 活跃、SurfaceFlinger 延迟
- 🔹 App 自身问题的特征：主线程 Slice 耗时明显、特定操作触发
- 🔹 灰色地带：系统资源不足导致 App 表现差（谁该负责？）

### 扩展（可选深入）

- 🔸 多 App 共存时的性能归因
- 🔸 系统级性能回归的排查方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
