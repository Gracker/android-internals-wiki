---
title: "启动全链路分析（App 视角）"
chapter: "21.1"
section: "21.1"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [cold-start, warm-start, ttid, ttfd, startup-trace]
related_chapters: ["8.2", "8.3", "1.7", "1.11"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# 启动全链路分析（App 视角）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 冷 / 温 / 热启动在 App 侧的耗时拆解
- 🔹 Application.onCreate、Activity.onCreate、首帧渲染各阶段耗时分布
- 🔹 启动耗时的度量方法：TTID / TTFD / 自定义埋点
- 🔹 Perfetto 启动分析实战

### 扩展（可选深入）

- 🔸 启动过程中的 ClassLoader 与 dex 加载开销

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解启动全链路分析（App 视角）

（待加工）

