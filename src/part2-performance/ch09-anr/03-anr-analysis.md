---
title: "ANR 分析方法"
chapter: "9.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['anr', 'traces']
related_chapters: []
---

# ANR 分析方法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ANR traces.txt 的解读方法：主线程堆栈、锁信息、等待对象
- 🔹 从 Perfetto/Systrace 分析 ANR：主线程在 ANR 时间窗口内的活动
- 🔹 常见 ANR 根因分类：死锁、主线程 I/O、Binder 调用超时、CPU 饥饿、系统负载高
- 🔹 CPU 使用率信息（ANR info 中的 CPU usage）的解读
- 🔹 线上 ANR 的分析流程与工具链

### 扩展（可选深入）

- 🔸 ANR Rate 的量化与监控体系搭建
- 🔸 使用 Perfetto SQL 批量分析 ANR Trace

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
