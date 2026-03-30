---
title: "Kotlin Coroutine 性能实践"
chapter: "8.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['coroutine', 'performance', 'dispatcher', 'structured-concurrency']
related_chapters: []
---

# Kotlin Coroutine 性能实践

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Dispatcher 选择对性能的影响：Main / IO / Default / Unconfined 的底层实现与适用场景
- 🔹 Coroutine 上下文切换开销 vs 线程切换开销的量化对比
- 🔹 结构化并发（Structured Concurrency）对资源泄漏的防护
- 🔹 Flow 的背压与性能：conflate、buffer、collectLatest 的取舍
- 🔹 Coroutine 在 Perfetto/Systrace 中的追踪：kotlinx-coroutines-debug

### 扩展（可选深入）

- 🔸 Coroutine 与 RxJava 的性能对比
- 🔸 自定义 Dispatcher 的场景与实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
