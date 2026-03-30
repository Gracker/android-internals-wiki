---
title: "线程 CPU 状态分析"
chapter: "13.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['perfetto', 'running', 'runnable', 'sleep']
related_chapters: []
---

# 线程 CPU 状态分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 线程 CPU 状态定义：Running (R)、Runnable (R+)、Sleeping (S)、Uninterruptible Sleep (D)、Stopped (T)
- 🔹 在 Perfetto 中读取线程状态：sched_switch events、thread state track
- 🔹 Runnable 过长意味着什么：CPU 争抢、核数不足、优先级过低
- 🔹 Uninterruptible Sleep 意味着什么：I/O 等待、内核锁、Page Fault
- 🔹 从线程状态分析性能瓶颈的方法论

### 扩展（可选深入）

- 🔸 wakeup 事件分析：谁唤醒了这个线程
- 🔸 irq/softirq 对线程调度的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
