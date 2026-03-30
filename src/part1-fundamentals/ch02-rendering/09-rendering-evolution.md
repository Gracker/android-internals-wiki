---
title: "渲染机制的版本演进"
chapter: "2.9"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['frametimeline', 'vulkan']
related_chapters: []
---

# 渲染机制的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 3.0 引入硬件加速，4.0 默认开启
- 🔹 Android 5.0 引入 RenderThread，主线程与 GPU 命令分离
- 🔹 Android 12 引入 BlastBufferQueue 统一 Buffer 管理
- 🔹 HWUI 后端演进：OpenGL ES → Skia OpenGL → Skia Vulkan
- 🔹 Android 16 渲染管线的最新改进

### 扩展（可选深入）

- 🔸 Project Butter（4.1）、Project Silk（后续帧率优化）的历史意义
- 🔸 各版本 Choreographer / FrameMetrics API 的演进

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
