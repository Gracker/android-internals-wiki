---
title: "GAPS：Android 动态分析目标可达性路径重建"
chapter: "7.14"
section: "7.14"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [dynamic-analysis, gui-testing, static-analysis, perfetto, jank, android-testing]
related_chapters: ["7.3", "7.4", "13.1", "13.3"]
created_by: "openclaw-task2a"
created_date: "2026-04-10"
gap_source: "研究素材"
confidence: medium
sources:
  - type: paper
    path: "https://arxiv.org/abs/2511.23213"
    title: "Mind the GAPS: Automated Path Reconstruction for Android Method Reachability"
    authors: "arXiv 2025"
    date: "2025-11"
---

# 7.14 GAPS：Android 动态分析目标可达性路径重建

## 开篇：为什么了解这个

动态分析（Dynamic Analysis）是 Android 性能分析与测试的核心手段：通过在真机上运行 App，观察其行为来推断系统状态。但传统动态分析有一个根本性瓶颈——**目标方法的可达性（Method Reachability）问题**。

当我们想要分析某个特定方法（比如 `View.draw()`）对流畅性的影响时，纯动态分析只能被动等待该方法被触发。如果这个方法只在特定条件下执行（比如列表滑动到第 50 项时），工程师可能需要反复操作几分钟甚至几小时才能触达。AndroTest 基准上，纯动态分析的触达率只有 9.69%（GoalExplorer）到 17.12%（Guardian+LLM）。

GAPS（Graph-based Automated Path Synthesizer）解决的就是这个问题：给定一个目标方法，通过**静态路径重建**（不运行 App）找出所有可能到达该方法的 GUI 操作序列，再通过**轻量级动态执行**验证这些路径是否真实可达。在 AndroTest 基准上，GAPS 实现了 88.24% 的静态路径识别率和 57.44% 的动态触达率，远超所有已知方案。

> 本节内容待加工（draft 已创建，Phase 1.9 知识缺口挖掘完成）。

<!-- outline-start -->
## 要点

### 🔹 目标可达性问题：动态分析的根本瓶颈
- 纯动态分析的被动触发困境：目标方法需要特定条件才能触达
- 现有方案的性能对比：FlowDroid（全程序静态分析）vs 纯动态执行 vs LLM 辅助
- GAPS 解决的核心问题：给定目标方法，重建从 App 入口到该方法的 GUI 操作序列

### 🔹 GAPS 架构：静态路径重建 + 动态 GUI 执行
- 两阶段设计：后向遍历构建目标导向的部分调用图（而非全程序 FlowDroid 分析）
- 关键创新点：points-to 分析 + 常量传播推断条件分支满足路径
- 静态路径识别率 88.24%（4.27 秒/App）vs 其他方案 12.82%

### 🔹 UI 资源 ID 逆向与 GUI 操作序列生成
- 如何从 APK 资源表中提取 GUI 组件 ID
- 静态重建操作序列：点击、长按、滑动、输入等操作的逆向推导
- Android 界面状态空间的建模方法

### 🔹 Perfetto 在 GAPS 工作流中的角色
- GAPS 的动态验证阶段可使用 Perfetto 抓取 trace 验证目标方法是否被触达
- 在 Perfetto中如何确认目标方法的执行（Thread State、Function Call 跟踪）
- [待补充：具体 Perfetto 抓取配置]

### 🔹 与 FlowDroid 等全程序静态分析工具的对比
- FlowDroid：全程序 IFDS 污点分析，计算开销大，无法处理条件分支
- GAPS：目标导向的部分调用图，只分析相关的有限调用链
- 各自的适用场景：GAPS 适合目标明确的验证场景，FlowDroid 适合全程序数据流分析

### 🔹 在 Android 性能分析工作流中的实际应用
- jank 根因分析：给定某个导致 jank 的方法，快速重建触发路径
- ANR 分析：找到导致 ANR 的方法调用的完整触发序列
- 自动化回归测试：根据目标方法集合自动生成 GUI 测试用例

## 扩展

### 🔸 Android 动态分析工具全景
- DroidD（深度变异测试）、AndroTest（基准测试）、Sieve（安全分析）
- GAPS 在这个生态系统中的定位

### 🔸 LLM 在 GUI 测试中的辅助应用
- Guardian+LLM（17.12% 触达率）如何用 LLM 辅助界面理解
- GAPS vs LLM 的互补关系：GAPS 精确、可解释；LLM 灵活但不可控

### 🔸 局限性：动态验证失败的主要原因
- 反射调用、native 方法、复杂加密逻辑导致路径不可达
- GAPS 在 Google Play Top 50 上的动态触达率 59.86%（低于静态识别率 62.03%）

<!-- outline-end -->
