---
title: "内存相关的版本演进"
chapter: "4.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory']
related_chapters: []
---

# 内存相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 5.0 ART 替代 Dalvik，GC 效率大幅提升
- 🔹 Android 8.0 Bitmap 内存从 Java Heap 移至 Native Heap
- 🔹 Android 10 GC 改为 Concurrent Copying，暂停时间降至亚毫秒
- 🔹 Android 11+ malloc 切换到 Scudo allocator
- 🔹 各版本对进程内存限制、大堆(largeHeap)策略的变化

### 扩展（可选深入）

- 🔸 MTE (Memory Tagging Extension) 在 Android 14+ 的推进
- 🔸 各版本 Graphics 内存的计量方式变化（如 GPU 内存归属）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
