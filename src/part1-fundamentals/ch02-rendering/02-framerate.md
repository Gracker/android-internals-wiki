---
title: "帧率与刷新率"
chapter: "2.2"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['framerate', 'refresh-rate', 'vrr']
related_chapters: []
---

# 帧率与刷新率

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 帧率基础：FPS、帧时间（Frame Time）、帧间隔一致性
- 🔹 刷新率演进：60Hz → 90Hz → 120Hz → LTPO 动态刷新率
- 🔹 多刷新率下的渲染挑战：SurfaceFlinger 如何选择刷新率
- 🔹 Frame Pacing：Choreographer 如何对齐帧边界
- 🔹 掉帧（Missed Frame / Janky Frame）的定义与量化

### 扩展（可选深入）

- 🔸 Game Mode / Frame Rate 策略对渲染的影响
- 🔸 LTPO 面板的工作原理与 Android 的适配
- 🔸 120Hz 场景的功耗权衡与智能降帧策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
