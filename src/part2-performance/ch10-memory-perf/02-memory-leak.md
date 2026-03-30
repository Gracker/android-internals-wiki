---
title: "内存泄漏"
chapter: "10.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['memory-leak', 'mat', 'leakcanary']
related_chapters: []
---

# 内存泄漏

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存泄漏的定义：对象不再使用但无法被 GC 回收
- 🔹 LeakCanary 的原理：WeakReference + ReferenceQueue + Heap Dump
- 🔹 常见泄漏模式：Activity 泄漏、Fragment 泄漏、Handler 泄漏、Listener 未解注册
- 🔹 Native 内存泄漏的排查方法：malloc debug / heapprofd
- 🔹 Heap Dump 分析：GC Root → Reference Chain → Leaked Object

### 扩展（可选深入）

- 🔸 Compose 场景的内存泄漏特征
- 🔸 线上内存泄漏的自动检测方案

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
