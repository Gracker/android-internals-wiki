---
title: "Android 存储架构"
chapter: "6.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['storage', 'partition']
related_chapters: []
---

# Android 存储架构

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 存储架构：UFS/eMMC → Block Layer → 文件系统 → Scoped Storage / MediaStore
- 🔹 UFS 3.x/4.0 vs eMMC 的性能差异
- 🔹 分区布局：system、vendor、data、metadata 等分区的作用
- 🔹 Scoped Storage（Android 10+）对 App I/O 行为的影响
- 🔹 FBE（File-Based Encryption）对 I/O 性能的影响

### 扩展（可选深入）

- 🔸 Dynamic Partition 与 Virtual A/B 的存储布局
- 🔸 存储寿命与写入放大（Write Amplification）对性能的长期影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
