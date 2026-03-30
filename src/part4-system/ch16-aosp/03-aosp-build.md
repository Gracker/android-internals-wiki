---
title: "AOSP 源码编译与调试环境"
chapter: "16.3"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['aosp', 'build']
related_chapters: []
---

# AOSP 源码编译与调试环境

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 AOSP 下载与编译环境搭建（Ubuntu / Mac 环境）
- 🔹 Lunch target 选择与 build variant（userdebug / eng）
- 🔹 模拟器运行 AOSP（emulator / Cuttlefish）
- 🔹 修改 Framework 代码并验证的工作流
- 🔹 常用 debug 手段：增加 Log、修改 SystemProperties、dumpsys

### 扩展（可选深入）

- 🔸 使用 ADB root + 修改 system partition 的快速调试方式
- 🔸 Pixel 设备刷 AOSP 自编译 ROM 的流程

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
