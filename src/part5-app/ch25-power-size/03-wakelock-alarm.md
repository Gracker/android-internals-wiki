---
title: "WakeLock 与 Alarm 管理"
chapter: "25.3"
section: "25.3"
status: draft
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-10"
last_verified_against: "待验证"
confidence: low
drafted_date: "2026-05-10"
polish_count: 0
sources: []
tags: [wakelock, alarm, exact-alarm, wakelock-leak]
related_chapters: ["25.2", "11.5", "5.6"]
pipeline_stage: draft
task6_state: pending
task9_state: pending
task2b_state: pending
---

# WakeLock 与 Alarm 管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 WakeLock 类型与使用规范
- 🔹 WakeLock 泄漏检测与治理
- 🔹 AlarmManager 最佳实践
- 🔹 Exact Alarm 权限变化（Android 12+）

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解WakeLock 与 Alarm 管理

（待加工）

