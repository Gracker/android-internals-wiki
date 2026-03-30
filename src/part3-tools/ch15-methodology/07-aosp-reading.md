---
title: "AOSP 代码阅读"
chapter: "15.7"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['aosp']
related_chapters: []
---

# AOSP 代码阅读

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 AOSP 源码在线阅读工具：cs.android.com（Android Code Search）
- 🔹 关键目录结构：frameworks/base、frameworks/native、system/core、art
- 🔹 阅读技巧：从 Logcat 日志反查代码、从 Systrace tag 定位代码
- 🔹 性能相关的核心源码入口：ActivityThread、ViewRootImpl、Choreographer、SurfaceFlinger
- 🔹 如何高效追踪一个调用链（IDE 搜索 vs grep vs codesearch）

### 扩展（可选深入）

- 🔸 本地 AOSP 全量代码的下载与 IDE 配置
- 🔸 利用 git log/blame 追踪功能变更历史

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
