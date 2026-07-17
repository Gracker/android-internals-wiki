---
title: "Compose LazyGrid 性能优化实战"
chapter: "22.45"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [Compose, LazyGrid, LazyVerticalGrid, StaggeredGrid, performance, scrolling]
related_chapters: ["22.22", "22.25", "22.34", "22.44"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "章节深挖"
---

# 22.45 Compose LazyGrid 性能优化实战

<!-- outline-start -->
## 要点

### 🔹 LazyVerticalGrid / LazyHorizontalGrid 架构与测量模型
- LazyGridScope 与 LazyListScope 的差异
- Grid 的 span 机制（GridCells.Fixed / GridCells.Adaptive）
- 多列测量与子项排列算法

### 🔹 LazyVerticalStaggeredGrid 的特殊性能考量
- 高度不均匀项的测量策略
- staggered 布局的额外测量开销
- 与 LazyVerticalGrid 的性能差异基准

### 🔹 item key 与 contentType 在 LazyGrid 中的正确用法
- key 参数对复用槽位的作用
- contentType 在混合类型 Grid 中的池化优化
- 缺失 key 导致的动画断裂与状态丢失

### 🔹 预取（prefetch）与滚动性能
- beyondBoundsItemCount 与 LazyGrid 预取窗口
- 预取的线程调度与主线程竞争
- 快速 fling 下的预取抑制策略

### 🔹 LazyGrid + Compose 重组的交互
- 列表项重组对滚动帧率的影响
- item content lambda 的 stability 与跳过机制
- 嵌套 LazyGrid 的性能退化与替代方案

### 🔹 大数据集 Grid 的内存占用
- Grid item 的组合缓存（prefetchDistance 调优）
- Bitmap 加载与 Grid 滚动的协同
- 回收机制与 SlotTable 的 span

## 扩展

### 🔸 LazyGrid 在折叠屏大屏上的自适应
- GridCells.Adaptive 在不同屏幕宽度下的性能特征
- 响应式列数切换的重组开销

### 🔸 LazyGrid 与 Paging 3 集成的性能
- LazyPagingItems 在 Grid 中的 append/prepend 性能
- 分页加载时的占位符策略

<!-- outline-end -->

> 本节内容待加工。 [结构参考: Clippings/《Android 性能优化》列表渲染相关章节]
