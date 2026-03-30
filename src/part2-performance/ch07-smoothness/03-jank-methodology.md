---
title: "卡顿分析方法论"
chapter: "7.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['methodology']
related_chapters: []
---

# 卡顿分析方法论

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 流畅性问题的完整分析流程：复现 → 抓 Trace → 定位帧 → 分析主线程/RenderThread/SF
- 🔹 Perfetto 中定位 Jank 帧的方法：FrameTimeline、Expected vs Actual
- 🔹 Systrace 中关键标记的解读：doFrame、DrawFrame、SurfaceFlinger onMessageReceived
- 🔹 CPU 调度问题导致的 Jank：识别 Runnable 过长、Uninterruptible Sleep
- 🔹 分析模板：标准化的 Jank 分析 Checklist

### 扩展（可选深入）

- 🔸 FrameMetrics API 在线上监控中的应用
- 🔸 使用 SQL 查询 Perfetto Trace 进行批量分析

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
