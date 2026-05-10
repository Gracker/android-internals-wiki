---
title: "Native Crash 分析与治理"
chapter: "20.3"
section: "20.3"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [native-crash, tombstone, signal, breakpad, symbolication]
related_chapters: ["20.1", "20.2", "1.15"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# Native Crash 分析与治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Linux 信号机制与 Native 崩溃产生流程
- 🔹 Tombstone 结构解读
- 🔹 breakpad / crashpad 集成与符号化
- 🔹 常见 Native 崩溃模式：SIGSEGV、SIGABRT、SIGBUS

### 扩展（可选深入）

- 🔸 addr2line / ndk-stack 实战
- 🔸 JNI 边界崩溃的排查

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解Native Crash 分析与治理

（待加工）

