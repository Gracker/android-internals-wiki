---
title: "DVFS 与功耗管理"
chapter: "5.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['dvfs', 'cpufreq']
related_chapters: []
---

# DVFS 与功耗管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 DVFS（Dynamic Voltage and Frequency Scaling）的原理：频率与电压的正相关
- 🔹 CPU frequency governor 机制：schedutil 基于 utilization 调频
- 🔹 OPP Table：离散的频率-电压档位
- 🔹 调频延迟对性能的影响：升频延迟 → 短暂掉帧
- 🔹 功耗公式：P ∝ C × V² × f（为什么降压比降频更省电）

### 扩展（可选深入）

- 🔸 GPU DVFS 机制
- 🔸 内存频率（DDR/LPDDR）调频对性能的影响
- 🔸 Perfetto 中观察 CPU/GPU 频率变化的方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
