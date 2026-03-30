---
title: "CPU 相关的版本演进"
chapter: "5.7"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['autofdo']
related_chapters: []
---

# CPU 相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 5.0+ 引入 JobScheduler 优化后台功耗
- 🔹 Android 6.0 Doze 模式引入
- 🔹 Android 9.0 Adaptive Battery + App Standby Buckets
- 🔹 Android 10 EAS 成为默认调度策略
- 🔹 Android 12+ 对精确闹钟、前台服务、后台启动的持续限制

### 扩展（可选深入）

- 🔸 GKI 对内核调度模块定制化的影响
- 🔸 Android 16 功耗与调度相关的新变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
