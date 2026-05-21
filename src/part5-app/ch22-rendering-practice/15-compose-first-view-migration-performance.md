---
title: "Compose First 与 View/Compose 混合迁移性能边界"
chapter: "22.15"
status: draft
applicable_versions: "Jetpack Compose 1.9 - 1.10 / Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, view-interop, rendering, migration, performance]
related_chapters: ["7.7", "22.2", "22.3", "18.2", "14.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "每日信息/官方文档/研究素材"
gap_score: 18
sources:
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/android-ui-development-is-compose-first.html"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/first"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/migrate/interoperability-apis"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-15-compose-pausable-composition-lazy-layout-cache-window.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-18-android-17-compose-pausable-composition-tooling-verification.md"
---

# 22.15 Compose First 与 View/Compose 混合迁移性能边界

<!-- outline-start -->
## 要点

### 🔹 Compose First 改变新增 UI 能力入口
说明 Google 2026 年将 Android UI guidance、tools、API 和 samples 转向 Compose 的背景，并把它转成工程判断：新增功能优先 Compose，老页面按触碰频率和性能风险分批迁移。

### 🔹 View 维护模式与存量页面边界
区分 android.widget、Fragment、RecyclerView、ViewPager 等 View based 组件的维护状态、继续可用范围和不再承接新特性的影响，避免把“维护模式”误读成“立即废弃”。

### 🔹 View/Compose interop 的性能成本
梳理 `ComposeView`、`AndroidView`、Fragment 容器、RecyclerView item 中嵌入 Compose 的常见成本：生命周期桥接、measure/layout 重复、状态同步、slot table 与 View tree 双重管理。

### 🔹 迁移顺序与风险分层
给出页面迁移排序：新页面、低频设置页、长列表 item、动画密集页、大屏/窗口化页面分别采用不同验证门槛，性能敏感路径先做 Macrobenchmark 和线上指标基线。

### 🔹 Lazy 列表、Pausable Composition 与版本边界
结合 Compose Foundation 1.9/1.10 的 LazyLayoutCacheWindow、Pausable Composition、runtime tracing，说明长列表迁移时要看具体 Compose 版本和默认开关，不把 alpha 能力写成稳定默认能力。

### 🔹 观测工具与验收指标
说明 Compose Profiler、Perfetto、Android Performance Analyzer、Macrobenchmark、Baseline Profile 的分工，建立启动耗时、帧耗时、重组次数、跳过次数、GC 暂停和内存峰值的验收表。

## 扩展

### 🔸 XML to Compose migration skill 的适用范围
记录官方迁移 skill 适合做布局草案转换，最终仍需人工确认状态提升、语义、可访问性和性能数据。

### 🔸 Compose Multiplatform 与 Android App 迁移的差异
区分跨平台 UI 选型和 Android 原生页面迁移，避免把 Compose Multiplatform 的限制直接套到 Android App 页面上。

### 🔸 Compose 1.10+ release notes 跟踪
后续补充 Pausable Composition、Lazy prefetch、Modifier 优化和 runtime tracing 的稳定版本边界。

<!-- outline-end -->

> 本节内容待加工。
