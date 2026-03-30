---
title: "ANR 类型与触发条件"
chapter: "9.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['anr']
related_chapters: []
---

# ANR 类型与触发条件

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Input Dispatching Timeout：5s，触摸/按键事件无响应
- 🔹 BroadcastReceiver Timeout：前台 10s / 后台 60s
- 🔹 Service Timeout：前台 20s / 后台 200s
- 🔹 ContentProvider Timeout：10s（publish timeout）
- 🔹 各类型 ANR 在 Logcat 中的标识特征

### 扩展（可选深入）

- 🔸 执行 Service startForeground 的 ANR（FGS 超时）
- 🔸 JobService 超时机制与 ANR 的关系

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
