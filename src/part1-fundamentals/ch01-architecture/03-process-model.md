---
title: "进程模型与生命周期管理"
chapter: "1.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['process', 'ams', 'adj']
related_chapters: []
---

# 进程模型与生命周期管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 进程的 5 级优先级模型：Foreground → Visible → Service → Cached → Empty
- 🔹 oom_adj_score 机制及 AMS 如何动态调整进程优先级
- 🔹 Zygote fork 机制：为什么 App 进程都是 Zygote 的子进程
- 🔹 Application / Activity / Service / BroadcastReceiver / ContentProvider 与进程的对应关系
- 🔹 进程间通信方式总览：Binder、Socket、共享内存（ashmem/memfd）、管道
- 🔹 进程死亡回调（DeathRecipient）与进程保活的系统视角

### 锚点（必须覆盖）（续）

- 🔹 Phantom Process Killer（Android 12+）对后台进程的限制

### 扩展（可选深入）

- 🔸 App Standby Buckets 对进程调度策略的影响
- 🔸 Isolated Process 与 SDK Sandbox 进程

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
