---
title: "App 内存分析"
chapter: "10.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory', 'pss', 'rss']
related_chapters: []
---

# App 内存分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 App 内存分析的核心工具：Android Studio Memory Profiler、adb shell dumpsys meminfo、MAT
- 🔹 Java Heap 分析：Retained Size、Shallow Size、Dominator Tree
- 🔹 Native Heap 分析：malloc debug、ASan、heapprofd
- 🔹 Graphics 内存的归属与计量：dumpsys gpu / memtrack
- 🔹 内存基线建立与回归检测方法

### 扩展（可选深入）

- 🔸 使用 Perfetto heapprofd 分析 Native 内存分配
- 🔸 线上内存监控的采样策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
