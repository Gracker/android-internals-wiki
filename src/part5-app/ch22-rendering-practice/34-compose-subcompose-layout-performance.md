---
title: "Compose SubcomposeLayout 性能深度：层级测量、Intrinsic 与重组陷阱"
chapter: "22.34"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [Compose, SubcomposeLayout, 布局性能, Intrinsics, 测量]
related_chapters: ["22.3", "22.22", "22.25", "22.28"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "章节深挖"
confidence: medium
---

# 22.34 Compose SubcomposeLayout 性能深度：层级测量、Intrinsic 与重组陷阱

<!-- outline-start -->
## 要点

### 🔹 SubcomposeLayout 的设计目标与核心机制
- 动态组合子元素：根据可用空间决定显示哪些子组件
- 典型使用场景：LazyColumn/LazyRow 底层实现、条件布局
- SubcomposeLayout 与常规 Layout 的测量流程差异

### 🔹 测量阶段性能开销
- 双趟测量：Intrinsic 测量 + 实际测量
- 每次子组合的 recomposition scope 扩大风险
- N 层 SubcomposeLayout 嵌套的指数级测量风险

### 🔹 Intrinsic 查询的性能陷阱
- minIntrinsicWidth/maxIntrinsicWidth 的传播链路
- 何时 Intrinsic 查询触发全树重新测量
- @IntrinsicMeasurer 的开销与规避策略

### 🔹 Subcomposition 与 Recomposition 的交互
- subcompose() 调用的时机与频率
- 子 composition scope 与父 composition scope 的依赖追踪
- 重组传播在 SubcomposeLayout 边界的行为

### 🔹 性能诊断方法
- Compose Compiler Metrics 中的 SubcomposeLayout 标记
- Layout Inspector 中的测量次数统计
- Perfetto trace 中 Compose:recompose track 的 subcompose 事件

### 🔹 替代方案与迁移策略
- 使用 BoxWithConstraints 替代 SubcomposeLayout 的场景
- 基于固定尺寸或 Modifier 链的静态布局优化
- Compose 1.7+ LookaheadScope API 的替代思路

## 扩展

### 🔸 LazyList 内部对 SubcomposeLayout 的使用
- LazyList 实现 中 SubcomposeLayout 的特殊优化
- item key 对 subcomposition 缓存的影响

### 🔸 Android 17 上 Compose 的布局性能改进
- 测量缓存的新策略
- 是否有 framework 层对 SubcomposeLayout 的原生优化

<!-- outline-end -->

> 本节内容待加工。
