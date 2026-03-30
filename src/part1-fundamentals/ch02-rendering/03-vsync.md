---
title: "VSync 机制"
chapter: "2.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['vsync', 'surfaceflinger']
related_chapters: []
---

# VSync 机制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 VSync 的起源：解决画面撕裂（Screen Tearing）
- 🔹 Android VSync 架构：HW-VSync → SF-VSync → App-VSync 三级信号
- 🔹 VSync Phase Offset 的作用与调优
- 🔹 VSync 信号在 SurfaceFlinger 和 Choreographer 中的传递路径
- 🔹 VSync 在 Perfetto 中的观察：VSYNC-sf、VSYNC-app

### 扩展（可选深入）

- 🔸 可变刷新率下 VSync 行为的变化
- 🔸 VSync 偏移量对输入延迟的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
