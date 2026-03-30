---
title: "卡顿的定义与分类"
chapter: "7.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['jank', 'smoothness']
related_chapters: []
---

# 卡顿的定义与分类

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Jank 的标准定义：帧未在预期 VSync 周期内完成（60Hz=16.67ms / 90Hz=11.11ms / 120Hz=8.33ms）
- 🔹 Google 的 Jank 分类：App Jank vs SF Jank vs Display Jank
- 🔹 FrameTimeline 与 JankType 的对应关系（Android 12+）
- 🔹 掉帧率（Janky Frame Rate）、连续掉帧（Frozen Frame）的区别
- 🔹 用户感知与技术指标的映射：多少 ms 延迟人能感知到

### 扩展（可选深入）

- 🔸 各厂商对 Jank 定义的差异（如华为的标准 vs Google 的标准）
- 🔸 Perfetto FrameTimeline 中 Jank 类型的详细解读

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
