---
title: "SurfaceFlinger 与合成"
chapter: "2.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['surfaceflinger', 'bufferqueue', 'hwc']
related_chapters: []
---

# SurfaceFlinger 与合成

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SurfaceFlinger 的核心职责：Layer 合成、VSync 生成、Buffer 管理
- 🔹 合成方式：Client Composition (GPU) vs Device Composition (HWC)
- 🔹 Layer 的概念与 z-order 排列
- 🔹 SurfaceFlinger 主循环：onMessageReceived → handleTransaction → handlePageFlip → composite
- 🔹 Jank 与 SurfaceFlinger 的关系：SF 主线程卡顿对全局帧率的影响

### 锚点（必须覆盖）（续）

- 🔹 BlastBufferQueue 的引入与改进（Android 12+）

### 扩展（可选深入）

- 🔸 SurfaceFlinger 与 HWC HAL 的交互协议
- 🔸 Transaction 机制与 SyncTransaction

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
