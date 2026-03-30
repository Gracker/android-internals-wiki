---
title: "内存抖动与频繁 GC"
chapter: "10.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory', 'gc', 'churn', 'optimization']
related_chapters: []
---

# 内存抖动与频繁 GC

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存抖动（Memory Churn）的定义：短时间内大量对象分配与回收
- 🔹 内存抖动对性能的影响：GC 暂停、Allocation Stall、帧耗时波动
- 🔹 常见抖动场景：onDraw 中创建对象、循环体内分配、String 拼接
- 🔹 检测方法：Android Studio Allocation Tracker、Perfetto heapprofd
- 🔹 优化手段：对象池（Object Pool）、预分配、避免 autoboxing

### 扩展（可选深入）

- 🔸 Kotlin 内联类（value class）对减少装箱的作用
- 🔸 ART GC 对短生命周期对象的特殊优化（TLAB / Region）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
