---
title: "Compose 状态订阅与重组控制实战"
chapter: "22.44"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [Compose, recomposition, state, derivedStateOf, stability, performance]
related_chapters: ["22.03", "22.20", "22.21", "22.25", "22.28", "22.39"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "章节深挖+素材驱动"
---

# 22.44 Compose 状态订阅与重组控制实战

<!-- outline-start -->
## 要点

### 🔹 Composable 重组触发机制：snapshot state observation 链路
- Compose 编译器对 @Composable 函数的 state 读取注入 Snapshot 读取追踪
- mutableStateOf 的 value getter 注册订阅 → 状态变更时标记 invalidate
- RecomposeScope 的创建、绑定与失效机制

### 🔹 derivedStateOf 与重组粒度控制
- derivedStateOf 作为缓存层：仅在依赖的 state 真正变更时通知下游
- 高频状态（如 scroll offset）→ 低频结果（如是否显示按钮）的正确用法
- derivedStateOf 嵌套与多层缓存的性能陷阱

### 🔹 @Immutable 与 @Stable 注解的正确使用
- 编译器如何利用 Stability 推断决定跳过重组
- @Immutable vs @Stable 的语义差异与适用场景
- 第三方类型（如 OkHttp Request/Response）的稳定性标注策略
- @Immutable 但实际可变（List/MutableList）的陷阱

### 🔹 remember(key) 与 key 参数控制重组
- remember 的 key 策略：何时该带 key，何时不该带
- rememberUpdatedState 与 lambda 捕获的陷阱
- key() 可组合函数在 LazyList 中的作用与误用

### 🔹 重组避让模式（Recomposition Avoidance Patterns）
- 状态下沉（state hoisting）对重组范围的影响
- lambda 传递 vs value 传递对重组的控制
- ComposableLambda 与 inline 函数的重组优化
- 不必要的重组：常见反模式（在 Composable 中创建对象、读取 State 不在最内层）

### 🔹 ComposableKey 与 recomposition 调试
- androidx.compose.runtime 中的 currentRecompositionScope
- Layout Inspector 的 recomposition count 标签
- Compose Compiler Metrics 中的 stability 报告解读

### 🔹 Android 17 Compose Runtime 重组调度优化
- PausableComposition 在 Android 14+ 的默认启用与帧预算协同
- MonotonicFrameClock 与 Choreographer 帧对齐
- 重组与 layout/draw 阶段的流水线化

## 扩展

### 🔸 Compose Snapshot 系统与重组的底层关系
- 详见 22.39 Compose Snapshot 系统深度

### 🔸 recomposition 与 compositionLocal 的传播代价
- CompositionLocalProvider 的重组影响域分析
- 静态 CompositionLocal vs dynamic CompositionLocal

<!-- outline-end -->

> 本节内容待加工。 [结构参考: Clippings/《Android 性能优化》Compose 相关章节]
