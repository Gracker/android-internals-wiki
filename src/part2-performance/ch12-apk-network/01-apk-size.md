---
title: "APK 体积优化"
chapter: "12.1"
status: draft
applicable_versions: "TBD"
last_verified: ""
last_verified_against: ""
confidence: low
sources: []
tags: ['apk', 'r8', 'proguard']
related_chapters: []
---

# APK 体积优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 APK 组成分析：dex、resources、assets、native libraries、META-INF
- 🔹 APK Analyzer（Android Studio）的使用方法
- 🔹 代码瘦身：R8 / ProGuard 配置、移除无用代码、减少方法数
- 🔹 资源瘦身：WebP 替换 PNG、资源混淆、按需下载
- 🔹 Native 库瘦身：ABI 过滤、动态下发 so、strip 符号表
- 🔹 App Bundle 与 Dynamic Feature Module

### 扩展（可选深入）

- 🔸 Baseline Profile 对 APK 体积的影响
- 🔸 各大 App 的包体积优化实践数据

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

> 本节内容待加工。
