---
title: "命令行打开超大 Trace"
chapter: "13.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['perfetto']
related_chapters: []
---

# 命令行打开超大 Trace

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 大 Trace 的挑战：几百 MB 到 GB 级别，浏览器内存不足
- 🔹 trace_processor：命令行交互式查询工具
- 🔹 Perfetto SQL 查询基础：tables、views、常用查询模式
- 🔹 trace_processor_shell 批量分析脚本编写
- 🔹 用 Python 的 perfetto.trace_processor 库做自动化分析

### 扩展（可选深入）

- 🔸 trace_to_text 转换工具
- 🔸 自建 Perfetto 分析 Pipeline 的实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
