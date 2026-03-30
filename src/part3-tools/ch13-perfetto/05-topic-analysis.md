---
title: "专题解读"
chapter: "13.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['perfetto', 'cpu', 'vsync', 'surfaceflinger']
related_chapters: []
---

# 专题解读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 启动分析专题：从 Trace 中定位冷启动各阶段耗时
- 🔹 流畅性分析专题：FrameTimeline 分析、Jank 帧定位
- 🔹 Binder 分析专题：Binder 调用频率、耗时、跨进程追踪
- 🔹 内存分析专题：heapprofd、RSS/PSS counter
- 🔹 I/O 分析专题：block I/O events、filesystem events

### 扩展（可选深入）

- 🔸 功耗分析专题：CPU freq、suspend/resume、wakelock
- 🔸 多进程协同分析：System Server + App 进程联合分析

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
