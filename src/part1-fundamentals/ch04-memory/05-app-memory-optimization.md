---
title: "App 内存优化"
chapter: "4.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory-leak', 'bitmap']
related_chapters: []
---

# App 内存优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存优化的分层思路：减少分配 → 及时释放 → 避免泄漏 → 监控兜底
- 🔹 Bitmap 内存优化：inBitmap 复用、采样率、硬件 Bitmap
- 🔹 内存泄漏的常见模式：Activity 引用泄漏、Handler 泄漏、单例持有 Context
- 🔹 Native 内存管控：JNI 层泄漏排查、malloc debug / ASan
- 🔹 onTrimMemory 与 ComponentCallbacks2 的正确响应策略

### 扩展（可选深入）

- 🔸 Glide/Fresco 等图片库的内存管理策略对比
- 🔸 Jetpack Compose 的内存特点与注意事项
- 🔸 大型 App 的内存预算（Memory Budget）管理实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
