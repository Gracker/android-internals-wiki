---
title: "线上性能监控"
chapter: "15.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['monitoring']
related_chapters: []
---

# 线上性能监控

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 线上性能监控的必要性：发现线下测试无法覆盖的问题
- 🔹 帧率监控：Choreographer FrameCallback、FrameMetrics API
- 🔹 启动耗时监控：手动埋点 vs Jetpack App Startup 集成
- 🔹 ANR 监控：FileObserver 监听 traces.txt / ANR signal handler
- 🔹 监控数据的采样、聚合与报警策略

### 扩展（可选深入）

- 🔸 使用 Perfetto SDK 做线上 tracing
- 🔸 监控数据的可视化与归因分析平台

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
