---
title: "OEM 性能优化的通用思路"
chapter: "17.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['oem']
related_chapters: []
---

# OEM 性能优化的通用思路

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 OEM 性能优化的通用方向：启动优化、流畅性、内存管理、功耗、温控
- 🔹 OEM 优化的技术手段分层：Kernel（调度/内存）→ Native（Binder/SF）→ Framework（AMS/WMS）→ App（预加载/冻结）
- 🔹 应用冻结技术：Frozen Process、SIGSTOP、cgroup freezer
- 🔹 预加载与预测启动：智能预测用户下一步操作
- 🔹 后台管理策略差异：保活 vs 杀后台的平衡

### 扩展（可选深入）

- 🔸 OEM 优化带来的兼容性问题（如后台杀进程过于激进）
- 🔸 各厂商性能优化品牌（HyperBoost / RAMDISK / LPDDR Training 等）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
