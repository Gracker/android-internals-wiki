---
title: "Trace 抓取"
chapter: "13.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['perfetto', 'trace']
related_chapters: []
---

# Trace 抓取

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 命令行抓取：perfetto -c config.pbtxt -o trace.perfetto-trace
- 🔹 常用 TraceConfig 配置项：buffer_size、duration、data_sources
- 🔹 系统 atrace categories 配置：sched、gfx、view、wm、am、binder 等
- 🔹 用 record_android_trace 脚本快速抓取
- 🔹 通过 Perfetto UI 在线配置与抓取
- 🔹 在 App 中用 Trace.beginSection / Trace.endSection 添加自定义标记

### 扩展（可选深入）

- 🔸 长时间 Trace（Long Trace）的配置与分割策略
- 🔸 Heap Profiling 与 Callstack Sampling 的配置

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
