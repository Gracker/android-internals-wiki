---
title: "存储相关的版本演进"
chapter: "6.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['storage']
related_chapters: []
---

# 存储相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 4.4 FUSE → 8.0 SDCardFS → 11 回归 FUSE 的演进
- 🔹 Scoped Storage 的引入（Android 10+）与 MediaStore API
- 🔹 EROFS 在 Android 12+ system 分区的启用
- 🔹 UFS 规格演进对 Android 存储性能的影响

### 扩展（可选深入）

- 🔸 各版本对 App 外部存储访问权限的收紧
- 🔸 Incremental FS 用于大型应用的按需下载

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
