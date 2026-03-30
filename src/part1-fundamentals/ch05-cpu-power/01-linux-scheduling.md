---
title: "Linux 进程调度基础"
chapter: "5.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['scheduler', 'cfs']
related_chapters: []
---

# Linux 进程调度基础

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 CFS（Completely Fair Scheduler）的基本原理：虚拟运行时间、红黑树、时间片
- 🔹 调度类优先级：SCHED_FIFO > SCHED_RR > SCHED_OTHER(CFS) > SCHED_IDLE
- 🔹 nice 值与权重的换算关系
- 🔹 CPU Affinity 与 cpuset 对任务绑核的控制
- 🔹 调度延迟（Scheduling Latency）：runqueue wait 在 Perfetto 中的观察

### 扩展（可选深入）

- 🔸 EEVDF 调度器对 CFS 的改进（Linux 6.6+）
- 🔸 Real-time 线程在 Android 中的使用场景（Audio、SurfaceFlinger）
- 🔸 SchedTune / UClamp 对 Android 调度的增强

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
