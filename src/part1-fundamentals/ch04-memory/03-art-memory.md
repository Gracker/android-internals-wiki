---
title: "ART 虚拟机内存管理"
chapter: "4.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['art', 'gc', 'jit', 'aot']
related_chapters: []
---

# ART 虚拟机内存管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ART 堆结构：Image Space、Zygote Space、Allocation Space、Large Object Space
- 🔹 GC 策略演进：CMS → CC (Concurrent Copying) GC
- 🔹 GC 对性能的影响：暂停时间（Pause Time）、吞吐量、Allocation Stall
- 🔹 对象分配路径：TLAB → Region → Full GC
- 🔹 ART Profile-Guided Compilation：Install-time、Runtime、Cloud Profile

### 扩展（可选深入）

- 🔸 JIT Compilation 的内存开销与 Code Cache 管理
- 🔸 Reference Processing（SoftRef、WeakRef、PhantomRef）与 GC 的交互
- 🔸 ART 在 Android 16 上的最新优化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
