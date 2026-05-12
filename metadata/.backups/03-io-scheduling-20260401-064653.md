---
title: "I/O 调度与性能"
chapter: "6.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['io', 'ufs']
related_chapters: []
---

# I/O 调度与性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Linux I/O 调度器：CFQ → BFQ → mq-deadline / none
- 🔹 I/O 优先级与 cgroup blkio 控制
- 🔹 前台 App I/O 优先级保障机制
- 🔹 Page Cache 对读性能的加速与对内存的占用
- 🔹 I/O 性能问题在 Perfetto 中的表现：block I/O、iowait

### 扩展（可选深入）

- 🔸 Direct I/O vs Buffered I/O 在 Android 场景的取舍
- 🔸 数据库（SQLite/Room）I/O 优化最佳实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
