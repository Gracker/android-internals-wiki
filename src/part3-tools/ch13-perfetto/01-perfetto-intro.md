---
title: "Perfetto 简介与演进"
chapter: "13.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['perfetto', 'systrace']
related_chapters: []
---

# Perfetto 简介与演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Perfetto 是什么：Google 的下一代系统级 tracing 工具，Systrace 的继任者
- 🔹 Perfetto 与 Systrace 的关系与区别
- 🔹 Perfetto 的架构：traced（守护进程）、traced_probes（数据源）、Perfetto UI
- 🔹 核心概念：TraceConfig、Data Source、Track、Slice、Counter
- 🔹 为什么性能分析离不开 Perfetto

### 扩展（可选深入）

- 🔸 Perfetto 在 Chrome / Linux 上的跨平台支持
- 🔸 Perfetto SDK 嵌入 App 的能力（Custom Data Sources）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
