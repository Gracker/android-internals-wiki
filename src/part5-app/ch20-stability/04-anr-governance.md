---
title: "ANR 治理策略"
chapter: "20.4"
section: "20.4"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [anr, main-thread, binder, lock-contention, watchdog]
related_chapters: ["20.1", "9.1", "9.2", "9.3", "1.4", "1.5"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# ANR 治理策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 主线程瘦身策略与异步化
- 🔹 IPC（Binder）调用治理
- 🔹 锁竞争与死锁预防
- 🔹 ContentProvider / BroadcastReceiver 超时治理
- 🔹 ANR Watchdog 搭建

### 扩展（可选深入）

- 🔸 后台 ANR 与前台 ANR 的差异化治理
- 🔸 系统负载导致的 ANR 识别与过滤

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解ANR 治理策略

（待加工）

