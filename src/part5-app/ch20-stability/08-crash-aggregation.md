---
title: "崩溃聚合与归因分析"
chapter: "20.8"
section: "20.8"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [crash-aggregation, attribution, alerting, stack-dedup]
related_chapters: ["20.6", "26.2", "19.18"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# 崩溃聚合与归因分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 堆栈聚合算法与去重策略
- 🔹 崩溃归因维度：版本、机型、OS、场景
- 🔹 自动分派与责任人匹配
- 🔹 崩溃趋势分析与异常告警

### 扩展（可选深入）

- 🔸 基于 AI 的崩溃智能归类

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解崩溃聚合与归因分析

（待加工）

