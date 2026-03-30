---
title: "特殊场景的 ANR"
chapter: "9.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['anr', 'accessibility']
related_chapters: []
---

# 特殊场景的 ANR

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 系统负载高导致的 ANR：整机 CPU 饱和、I/O 阻塞
- 🔹 Broadcast 风暴导致的连锁 ANR
- 🔹 ContentProvider 冷启动导致的 ANR
- 🔹 SharedPreferences apply 导致的 ANR（ActivityThread handlePauseActivity 场景）
- 🔹 多进程场景的 Binder 死锁 ANR

### 扩展（可选深入）

- 🔸 低内存触发频繁 GC 导致的 ANR
- 🔸 文件锁竞争导致的 ANR

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
