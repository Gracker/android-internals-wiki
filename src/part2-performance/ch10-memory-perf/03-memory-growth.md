---
title: "内存持续增长"
chapter: "10.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory']
related_chapters: []
---

# 内存持续增长

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存持续增长（非泄漏）的常见原因：缓存无上限、Bitmap 累积、Native 碎片化
- 🔹 与内存泄漏的区分方法
- 🔹 LRU Cache 策略的正确实现
- 🔹 内存增长的监控指标：PSS 趋势、Java Heap 使用率趋势
- 🔹 内存碎片化的检测与应对

### 扩展（可选深入）

- 🔸 WebView 内存增长问题与多进程 WebView
- 🔸 长时间运行 App（如音乐播放器）的内存管理策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
