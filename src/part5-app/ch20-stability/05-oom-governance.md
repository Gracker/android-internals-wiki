---
title: "OOM 治理"
chapter: "20.5"
section: "20.5"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [oom, memory, thread-limit, fd-leak, virtual-memory]
related_chapters: ["20.1", "23.1", "23.4", "4.3", "4.4"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# OOM 治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Java Heap OOM 分类与治理
- 🔹 Native 内存 OOM
- 🔹 线程数 OOM（pthread_create 失败）
- 🔹 FD 泄漏导致的 OOM
- 🔹 虚拟内存空间耗尽（32 位进程）

### 扩展（可选深入）

- 🔸 OOM 兜底与安全降级
- 🔸 大型 App 的内存预算管理

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解OOM 治理

（待加工）

