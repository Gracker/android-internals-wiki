---
title: "文件系统"
chapter: "6.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['f2fs', 'ext4', 'erofs']
related_chapters: []
---

# 文件系统

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ext4 的核心特性与在 Android 上的使用
- 🔹 F2FS（Flash-Friendly File System）的设计思想与在 Android 上的优势
- 🔹 EROFS（Enhanced Read-Only File System）用于 system 分区
- 🔹 文件系统对随机读写性能的影响
- 🔹 fsync / fdatasync 对写性能的影响与优化

### 扩展（可选深入）

- 🔸 各厂商对文件系统的选型差异
- 🔸 文件系统碎片化对长期使用后性能退化的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
