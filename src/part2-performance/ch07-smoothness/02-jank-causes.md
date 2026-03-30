---
title: "卡顿原因体系"
chapter: "7.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['jank']
related_chapters: []
---

# 卡顿原因体系

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 主线程耗时过长：Layout/Measure 过重、RecyclerView Bind 耗时、主线程 I/O
- 🔹 RenderThread 瓶颈：GPU 过载、复杂 Canvas 操作、大量 Path 计算
- 🔹 SurfaceFlinger 瓶颈：合成超时、Layer 过多、HWC 限制
- 🔹 系统级原因：CPU 调度延迟（Runnable 状态过长）、低内存触发 GC、温控限频
- 🔹 Binder 调用导致的主线程阻塞
- 🔹 分析树：从现象到根因的分析决策路径

### 扩展（可选深入）

- 🔸 WebView 渲染导致的 Jank
- 🔸 多窗口/分屏场景的特殊 Jank 问题
- 🔸 动画与手势场景的 Jank 特征

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
