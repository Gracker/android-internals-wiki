---
title: "MainThread 与 RenderThread 协作"
chapter: "2.5"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['renderthread', 'hwui']
related_chapters: []
---

# MainThread 与 RenderThread 协作

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 MainThread 职责：测量(Measure)、布局(Layout)、构建 DisplayList
- 🔹 RenderThread 职责：同步 DisplayList、执行 GPU 绘制命令
- 🔹 MainThread → RenderThread 的同步栅栏（SyncFrameState）
- 🔹 RenderThread 的 GPU 命令提交与 Fence 等待
- 🔹 两个线程的耗时在 Systrace 中的分布与分析方法
- 🔹 常见性能问题：主线程阻塞导致 RenderThread 饥饿、GPU 过载导致帧延迟

### 扩展（可选深入）

- 🔸 Deferred GPU Commands 与 Pipeline flush 的时机
- 🔸 RenderThread 里的动画执行（RenderThread Animations）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
