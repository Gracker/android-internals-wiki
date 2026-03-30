---
title: "Low Memory Killer"
chapter: "4.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['lmk', 'oom']
related_chapters: []
---

# Low Memory Killer

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 LMK 的设计目标：在内存不足时有序释放进程
- 🔹 传统 LowMemoryKiller（内核模块）→ lmkd（用户空间守护进程）的演进
- 🔹 oom_adj_score 与进程优先级的映射关系
- 🔹 lmkd 的杀进程策略：PSI（Pressure Stall Information）驱动的现代策略 vs 传统 minfree 阈值触发，PSI 信号的含义与使用
- 🔹 LMK 在性能问题中的角色：频繁 kill → 频繁冷启动 → 用户感知卡顿

### 扩展（可选深入）

- 🔸 各厂商对 lmkd 的定制化策略
- 🔸 通过 Perfetto 观察 lmkd 行为的方法
- 🔸 Android 16 上 lmkd 的变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
