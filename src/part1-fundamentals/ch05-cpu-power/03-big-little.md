---
title: "大小核架构"
chapter: "5.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['big-little', 'dynamiq']
related_chapters: []
---

# 大小核架构

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ARM big.LITTLE / DynamIQ 架构原理
- 🔹 典型 SoC 核心配置：1+3+4 / 1+4+3 / 2+4+2 等
- 🔹 核心迁移（Core Migration）的触发条件与性能影响
- 🔹 cpufreq governor：schedutil 的工作原理
- 🔹 不同核心对单线程性能和多线程吞吐量的差异

### 扩展（可选深入）

- 🔸 Cortex-X 系列超大核的定位与功耗特性
- 🔸 GPU + NPU 的协同调度概念

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
