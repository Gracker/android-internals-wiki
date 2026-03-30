---
title: "性能测试最佳实践"
chapter: "15.6"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['testing']
related_chapters: []
---

# 性能测试最佳实践

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 性能测试环境标准化：设备选择、温控、电量、网络
- 🔹 消除测试干扰：关闭不必要 App、清理后台、恒温控制
- 🔹 数据采样策略：多次采样取中位数/P90、Warm-up 轮次
- 🔹 性能基线管理与回归检测
- 🔹 测试报告的撰写规范

### 扩展（可选深入）

- 🔸 Macrobenchmark 在 CI 中的集成实践
- 🔸 使用 Firebase Performance Monitoring 的限制与替代方案

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
