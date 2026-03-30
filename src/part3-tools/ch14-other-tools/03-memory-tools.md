---
title: "内存分析工具"
chapter: "14.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['mat', 'koom']
related_chapters: []
---

# 内存分析工具

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 LeakCanary 原理与配置
- 🔹 MAT（Memory Analyzer Tool）的使用方法
- 🔹 heapprofd（Perfetto）Native 内存分析
- 🔹 adb shell dumpsys meminfo 的详细解读
- 🔹 showmap / procrank / libmeminfo 等内存查看工具

### 扩展（可选深入）

- 🔸 malloc debug / malloc hooks 的使用方法
- 🔸 HWASAN / MTE 用于内存错误检测

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
