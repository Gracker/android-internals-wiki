---
title: "Compose 布局系统：测量阶段、缓存机制与 Intrinsic 性能"
chapter: "22.25"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, layout, measurement, intrinsic, performance]
related_chapters: ["22.3", "22.21", "22.22", "7.12", "2.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-25"
gap_source: "章节深挖+AOSP结构"
---

# 22.25 Compose 布局系统：测量阶段、缓存机制与 Intrinsic 性能

<!-- outline-start -->
## 要点

### 🔹 Compose 渲染三阶段管线与 layout phase 的位置
composition（重组）→ layout（测量+放置）→ draw（绘制）。重组阶段决定"哪些节点参与布局"，layout 阶段决定"节点多大、放哪里"，draw 阶段负责实际像素输出。layout 阶段是 Compose 性能优化的第二道防线，也是容易被忽略的一环。

### 🔹 LayoutNode 测量缓存机制
Compose 的 LayoutNode 在一次 frame 中缓存 MeasureResult，当 constraints 不变且子树未失效时跳过重测量。缓存失效条件包括：子树 modifier 变更、状态读取导致 RemeasureScope 标记、父节点传入的 constraints 变化。理解缓存命中/失效逻辑是排查"明明没有重组却还是卡"的关键。

### 🔹 Intrinsic 测量的性能开销与级联效应
Intrinsic 测量（maxIntrinsicWidth / minIntrinsicHeight 等）要求子树在约束未知时先做一轮"试探性"测量，再正式测量。多层嵌套 intrinsic（如 BoxWithConstraints → LazyColumn → Card → Column 链）会产生 O(depth) 级联测量，每层多一轮 pass。trace 中表现为同一 LayoutNode 在一帧内被 measure 多次。

### 🔹 SubcomposeLayout 性能边界
SubcomposeLayout 允许在测量过程中动态插入子组合，但代价是推迟组合完成时间。典型场景（LazyList、BoxWithConstraints）的 SubcomposeLayout 用法合理，但在自定义场景中滥用会导致帧延迟增大。需评估是否可以用固定子树 + 修改约束替代。

### 🔹 Modifier 链对布局性能的影响
每个 Modifier 节点都是布局树中的独立 LayoutNode。Modifier 链越长，测量传递层数越多。size + padding + border + background + click + scroll 等常见链的组合顺序会影响测量 pass 次数。Modifier.layout 自定义实现的性能注意事项。

### 🔹 自定义 Layout 的测量优化策略
自定义 Layout（实现 MeasurePolicy）时的性能要点：避免在 measure 中创建临时集合、避免对每个子节点重复查询 intrinsic、善用 LayoutId 标记跳过无关子节点。对比 View 体系 onMeasure/onLayout 的测量优化经验。

### 🔹 RemeasureScope 与最小化重测量范围
通过 Modifier.remeasure 或状态变更触发的重测量，应限制在最小 LayoutNode 子树。Compose 的失效传播从被修改的 LayoutNode 向上传播到最近的"可吸收变化"的祖先节点。理解传播边界有助于写出"只重测量一个卡片而非整个列表"的代码。

### 🔹 Compose 1.7+ LookaheadLayout 的性能特征
LookaheadLayout（用于 beyondBoundsLayout、动画布局过渡）引入两轮测量 pass：先 lookahead 再 actual。对常规 UI 无感知，但对有大量子节点的自定义布局会增加单帧 layout 耗时。需要评估是否真正需要 lookahead 语义。

## 扩展

### 🔸 LayoutInfo 与 Performance Stubs 在 Perfetto trace 中的识别
Compose 1.7+ 在 trace 中增加了 LayoutInfo track，可识别布局阶段的耗时节点。结合 Perfetto SQL 查询 LayoutNode 的 measure/place 耗时。

### 🔸 与 View 体系 layout 缓存的对比
View 体系的 measure 缓存通过 mMeasureWidth/Height 和 forceLayout 标志位实现；Compose 的缓存通过 LayoutNode.measureResult 和 modulation 实现。对比两者的缓存粒度和失效策略差异。

### 🔸 Compose 测量性能检测工具：Layout Inspector + Compose Compiler Reports
Layout Inspector 的 Composition Count 功能、Compose Compiler 的 reports 模式（报告中包含 stability 和 skip 信息），以及如何通过 Compose UI Test 的 BenchmarkMode 检测布局性能。
<!-- outline-end -->

> 本节内容待加工。
