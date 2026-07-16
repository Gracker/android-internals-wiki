---
title: "Compose ↔ View 互操作性能实战"
chapter: "22.41"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, interop, androidview, composeview, rendering-performance, migration]
related_chapters: ["22.3", "22.15", "22.22", "22.31"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "AOSP结构/官方文档/章节深挖"
---

# 22.41 Compose ↔ View 互操作性能实战

<!-- outline-start -->
## 要点

### 🔹 AndroidView 的性能开销模型
- AndroidView 包装 View 的 inflate / measure / layout / draw 开销
- Compose 重组合触发 View 重新布局的条件（invalidation 传播链）
- View 的状态变化如何反向通知 Compose（避免循环重组）

### 🔹 ComposeView 嵌入传统 View 树的开销
- ComposeView 在 RecyclerView 中的复用语义与 ViewTreeLifecycleOwner
- 多个 ComposeView 实例的 Lifecycle/SaveableStateRegistry 内存开销
- Android 17 Compose 1.10+ 的 ViewTreeHostingRegistry 优化

### 🔹 RecyclerView + Compose 混合滚动性能
- RecyclerView Item 中嵌入 AndroidView 的帧预算分析
- LazyColumn 与 RecyclerView 嵌套滚动的手势冲突与性能退化
- 迁移策略：分批替换 vs 全量替换的性能对比

### 🔹 互操作场景下的 Inspector / Layout Inspector 工具链
- Layout Inspector 对 Compose ↔ View 混合树的显示差异
- Perfetto 中 Compose 互操作 trace 的识别方法
- Compose Compiler Metrics 对 AndroidView 调用点的标记

### 🔹 Android 17 Compose 1.10+ 互操作性能改进
- PausableComposition 对 AndroidView 包裹区域的影响
- Modifier.Node 架构对 View 事件传递链的优化
- Compose Runtime Tracing 对互操作调用栈的端到端追踪

### 🔹 典型迁移阶段与性能基线
- 阶段 1: 单页面 Compose（ComposeView 承载）的性能基线
- 阶段 2: Fragment 内 Compose + 传统 View 混合的性能特征
- 阶段 3: 全 Compose 导航栈的性能回归监控

## 扩展

### 🔸 互操作场景下的帧率适配
- AndroidView 内 SurfaceView/TextureView 与 Compose 帧率不同步的问题
- Adaptive Refresh Rate 在混合渲染树中的行为边界

### 🔸 Compose 测试中 View 依赖的 Mock 策略
- AndroidView 在测试中的替换与Espresso/ComposeTestRule 混用

<!-- outline-end -->

> 本节内容待加工。[结构参考: 官方文档 Compose-View interop / AOSP Compose runtime 源码]
