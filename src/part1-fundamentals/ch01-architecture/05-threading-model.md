---
title: "线程模型"
chapter: "1.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['thread', 'handler', 'looper', 'messagequeue']
related_chapters: []
---

# 线程模型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 主线程（UI Thread）的职责与消息循环：Looper → MessageQueue → Handler
- 🔹 Handler / Message / MessageQueue 的工作原理及 IdleHandler
- 🔹 RenderThread 的角色：分担 GPU 命令提交，与主线程的同步点
- 🔹 AsyncTask（API 30 deprecated）→ Executor → Kotlin Coroutine 的演进与最佳实践
- 🔹 线程优先级：nice 值、cgroup（foreground/background）、SCHED_FIFO vs SCHED_OTHER
- 🔹 HandlerThread / IntentService / WorkManager 的适用场景

### 扩展（可选深入）

- 🔸 Kotlin Coroutine Dispatcher 与线程池的映射关系
- 🔸 线程数量对性能的影响：过度线程化引发的调度开销与 CPU 争抢
- 🔸 ThreadLocal 在 Looper、Choreographer 中的应用

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
