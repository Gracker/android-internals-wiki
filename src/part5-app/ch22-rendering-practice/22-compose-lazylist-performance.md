---
title: "Compose LazyList/LazyGrid 滑动性能深度优化"
chapter: "22.22"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, lazylist, lazygrid, jank, recomposition, performance, scrolling, recycling]
related_chapters: ["22.3", "22.2", "22.20", "22.21", "7.9", "18.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-08"
gap_source: "参考书结构/章节深挖/官方文档/社区热点"
gap_score:
  素材丰富度: 4
  与全书目标相关性: 5
  读者需求度: 5
  时效性: 4
  total: 18
material_count: 5
queue_priority: 80
---

# 22.22 Compose LazyList/LazyGrid 滑动性能深度优化

<!-- outline-start -->
## 要点

### 🔹 LazyList 滑动卡顿的分类与归因
区分 Compose 重组开销（recomposition scope 过大、不稳定参数）、布局计算开销（嵌套 LazyList、自定义 Layout）、项绑定/数据加载耗时（图片解码、数据库查询）、以及 GC / 内存抖动导致的帧延迟。建立从「感知卡顿 → Perfetto trace → 具体瓶颈」的归因路径。

### 🔹 key 与 contentType 的性能影响
解释 `key {}` 对项复用和动画连续性的影响，`contentType` 对 LazyList 内部 item pool 分池回收的作用。给出错误用例（使用 index 做 key 导致不必要的重组）和正确实践（使用业务唯一标识）。量化 key 设置对 DiffUtil 计算量和列表更新动画帧率的影响。

### 🔹 重组范围控制与 remember/derivedStateOf 模式
分析 LazyList 项内部的状态管理对滑动性能的影响：`remember` 缓存计算结果避免重复创建、`derivedStateOf` 减少无效重组、`LaunchedEffect` 与 `rememberCoroutineScope` 在项内部的生命周期管理。重点说明「不稳定 lambda」导致的整列表重组和如何用 `remember {}` 包装 lambda 打破传导链。

### 🔹 LazyList 预取、子项合成与嵌套滚动
LazyList 内部预取机制（prefetch count）的工作原理和 Perfetto 中的 trace 表现；嵌套 LazyList（水平 + 垂直）的子项复用与合成策略；`nestedScroll` 连接对滑动连贯性的影响。对照 RecyclerView 的嵌套滚动机制，说明 Compose 中的差异。

### 🔹 Perfetto 诊断 LazyList 卡顿的 SQL 模板
提供可直接使用的 Perfetto SQL 查询：LazyList 重组 trace（`compose-recomposition` 数据源）、帧 timeline 与 LazyList 滑动帧的关联、GC 暂停与 LazyList 项创建的时序关联、内存分配热点（`android.java.heap_stats`）与 LazyList 滑动的叠加分析。

### 🔹 大列表优化策略：分页、占位与虚拟化边界
Paging 3 + LazyList 集成的性能要点：`LazyPagingItems` 的刷新范围、加载状态占位符的渲染开销、列表末端触发的预加载窗口。讨论超长列表（10 万+项）下的内存占用和 item pool 大小控制。

### 🔹 Android 17 LazyList 行为变化与适配
Android 17 Compose 1.8+ 对 LazyList 内部实现的优化（移除不必要的重组、改进 item pool 策略），以及 targetSdk 37 环境下的 LazyList 行为变化。提供 targetSdk 36→37 的回归测试清单。

## 扩展

### 🔸 LazyVerticalGrid / LazyHorizontalGrid 的特殊考量
Grid 布局中 span size、交错布局（staggered）对 item pool 和复用的影响，与 LazyColumn 的差异。

### 🔸 与 RecyclerView 性能对比选型
从滑动帧率、内存占用、首屏加载、动态更新四个维度对比 Compose LazyList 与 RecyclerView，给出选型建议和混合使用场景。

### 🔸 Wear OS / TV LazyList 特殊性能约束
圆形屏幕、低帧率、遥控器焦点导航对 LazyList 滑动性能的特殊要求。

<!-- outline-end -->

> 本节内容待加工。
