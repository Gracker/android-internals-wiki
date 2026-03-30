---
title: "Linux 内核内存管理"
chapter: "4.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['kernel', 'memory', 'buddy', 'slab']
related_chapters: []
---

# Linux 内核内存管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 虚拟内存与物理内存映射：页表、TLB、Page Fault
- 🔹 Buddy 分配器与 Slab 分配器的基本原理
- 🔹 页面回收（Page Reclaim）：LRU、kswapd、direct reclaim
- 🔹 内存压缩（Memory Compaction）与碎片化
- 🔹 ION / DMA-BUF 在 Android 图形内存中的角色

### 扩展（可选深入）

- 🔸 16K Page Size（Android 15+ 支持）对内存和性能的影响
- 🔸 KASAN / MTE 等内存安全机制对性能的开销
- 🔸 Huge Pages 在 Android 上的实验

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
