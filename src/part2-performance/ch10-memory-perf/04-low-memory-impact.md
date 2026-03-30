---
title: "低内存对系统性能的影响"
chapter: "10.4"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['lmk', 'kswapd']
related_chapters: []
---

# 低内存对系统性能的影响

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 低内存对系统性能的连锁反应：kswapd 活跃 → direct reclaim → I/O 阻塞 → 全局卡顿
- 🔹 lmkd 频繁杀进程 → App 冷启动增加 → 用户感知卡
- 🔹 低内存下的 GC 行为变化：更频繁的 GC、更长的暂停
- 🔹 Perfetto 中识别内存压力的信号：mm_event、vmscan、lmk、PSI
- 🔹 系统级内存优化手段：ZRAM 调优、cgroup 内存限制

### 扩展（可选深入）

- 🔸 低端机（≤4GB RAM）的专项优化策略
- 🔸 Go Edition / Android Lite 的内存优化措施

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
