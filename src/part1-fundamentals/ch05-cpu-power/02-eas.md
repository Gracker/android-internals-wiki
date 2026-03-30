---
title: "EAS 能量感知调度"
chapter: "5.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['eas', 'energy']
related_chapters: []
---

# EAS 能量感知调度

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 EAS（Energy Aware Scheduling）的核心思想：在满足性能需求的同时最小化能耗
- 🔹 能量模型（Energy Model）：OPP（Operating Performance Points）与功耗曲线
- 🔹 Task Placement 策略：将轻任务放小核、重任务放大核
- 🔹 Util（utilization）信号与 PELT（Per-Entity Load Tracking）
- 🔹 EAS 在 Perfetto 中的观察：cpu_frequency、sched_switch、uclamp

### 扩展（可选深入）

- 🔸 各 SoC 厂商对 EAS 的定制化（高通 / 联发科 / 三星）
- 🔸 Pixel 设备上的调度策略特点

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
