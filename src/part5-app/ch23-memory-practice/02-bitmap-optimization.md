---
title: "Bitmap 与图片内存优化"
chapter: "23.2"
section: "23.2"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [bitmap, insamplesize, native-memory, inbitmap, hardware-bitmap]
related_chapters: ["23.1", "22.6", "7.10", "4.3"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# Bitmap 与图片内存优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Bitmap 内存计算与 inSampleSize
- 🔹 Android 8.0+ Bitmap Native 内存迁移
- 🔹 图片内存监控与大图检测
- 🔹 图片复用池与 inBitmap

### 扩展（可选深入）

- 🔸 Hardware Bitmap 的使用场景与限制

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解Bitmap 与图片内存优化

（待加工）

