---
title: "Simpleperf"
chapter: "14.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['simpleperf', 'pmu']
related_chapters: []
---

# Simpleperf

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Simpleperf 是什么：Android 的 CPU profiling 工具（基于 Linux perf）
- 🔹 基本用法：simpleperf record / simpleperf report
- 🔹 采样类型：cpu-clock、task-clock、硬件 PMU 事件
- 🔹 火焰图生成与解读：FlameGraph / Speedscope
- 🔹 与 Perfetto callstack sampling 的对比

### 扩展（可选深入）

- 🔸 Simpleperf 用于 Native 代码性能分析
- 🔸 内核符号解析与 kallsyms

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
