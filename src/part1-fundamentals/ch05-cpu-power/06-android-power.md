---
title: "Android 功耗管理"
chapter: "5.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['doze', 'wakelock', 'standby']
related_chapters: []
---

# Android 功耗管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 功耗管理框架：PowerManagerService → WakeLock → Suspend
- 🔹 Doze 模式与 App Standby 的工作原理与影响
- 🔹 Battery Historian 工具与功耗分析方法
- 🔹 WakeLock 的种类与滥用检测
- 🔹 JobScheduler / WorkManager 的省电调度策略

### 扩展（可选深入）

- 🔸 Adaptive Battery 与 ML 预测
- 🔸 Background Restriction 对后台功耗的控制
- 🔸 RESTRICTED bucket 与 Exemption 机制

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
