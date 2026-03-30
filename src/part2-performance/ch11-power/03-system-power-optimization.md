---
title: "系统级功耗优化"
chapter: "11.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['doze', 'standby']
related_chapters: []
---

# 系统级功耗优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Doze 模式的分阶段触发与维护窗口机制
- 🔹 App Standby Buckets（Active/Working/Frequent/Rare/Restricted）的调度差异
- 🔹 系统级限后台策略：Background Activity Starts 限制、后台定位限制
- 🔹 省电模式下的系统行为变化
- 🔹 厂商级功耗管理：后台冻结、自启动管理、后台杀进程策略

### 扩展（可选深入）

- 🔸 Adaptive Battery 的 ML 模型工作原理
- 🔸 电池健康管理（Adaptive Charging）与性能的关系

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
