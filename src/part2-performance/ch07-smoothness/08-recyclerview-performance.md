---
title: "RecyclerView 列表滑动性能深度优化"
chapter: "7.8"
status: draft
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [recyclerview, scrolling, jank, prefetch, difftutil, nested-scrolling, arr]
related_chapters: ["7.1", "7.2", "7.4", "7.5", "2.4", "2.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "读者需求+AOSP结构+研究素材+高爷卡顿洞察"
---

# 7.8 RecyclerView 列表滑动性能深度优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：RecyclerView 渲染管线概述
- RecyclerView 的布局流程：onLayout → dispatchLayoutStep1/2/3
- 测量与布局的分离策略（isAutoMeasureEnabled）
- 与传统 ListView 的架构差异及性能优势来源
- 在 Perfetto 中 RecyclerView 布局的 Track 表现

### 🔹 锚点 2：ViewHolder 回收复用机制与 RecycledViewPool
- Recycler 的四级缓存：AttachedScrap → CachedViews → ViewCacheExtension → RecycledViewPool
- 每级缓存的命中条件、生命周期和性能特征
- RecycledViewPool 的跨 RecyclerView 共享机制
- 缓存命中/未命中在 Trace 中的表现（inflate vs bind 时间差异）
- Pool 大小调优：setRecycledViewPool 与setItemViewCacheSize 的最佳配置

### 🔹 锚点 3：Prefetch 预取机制
- Android 5.0+ GapWorker 预取：在 UI 线程空闲时提前绑定下一帧需要的 ViewHolder
- prefetch 时机与 VSync 的关系：在 doFrame 的 COMMIT 阶段执行
- setInitialPrefetchItemCount 对嵌套 RecyclerView 的影响
- 预取失败的常见原因：缓存污染、布局未完成、ItemDecoration 阻塞
- 在 Perfetto 中识别预取行为（RecyclerView 预取 slice）

### 🔹 锚点 4：DiffUtil 与列表更新性能
- DiffUtil 的 Eugene W. Myers 差分算法原理
- asyncListDiffer 的异步计算与主线程分发机制
- DiffResult → dispatchUpdatesTo → ItemAnimator 的触发链路
- areItemsTheSame / areContentsTheSame 对性能的影响
- 大列表 diff 的耗时优化：detectMoves=false、分页 diff
- Payload 机制实现局部绑定（partial bind）减少不必要的 full bind

### 🔹 锚点 5：嵌套滑动机制与 NestedScrolling 性能
- NestedScrollingParent/Child 协议的交互流程
- 嵌套 RecyclerView（如 ViewPager2 + RecyclerView）的滑动冲突与性能影响
- dispatchNestedScroll / onNestedPreScroll 的调用链路
- 嵌套滑动在 Perfetto 中的特征：频繁的 requestLayout 和 measure
- 优化策略：setMaxRecycledViews、共享 Pool、禁用 OverScroll

### 🔹 锚点 6：滑动卡顿的常见根因与 Perfetto 定位方法
- item 布局过深导致 measure 耗时过长
- onBindViewHolder 中的 IO/计算操作
- item 动画（ItemAnimator）触发的额外布局 pass
- 图片加载回调触发 item 变化和 requestLayout
- RecyclerView.setItemViewCacheSize(0) 的反直觉效果
- VSync 时间精度问题导致的列表滑动不均匀（高爷洞察：VSync ns→ms 取整导致 ±1ms 波动）

### 🔹 锚点 7：RecyclerView 1.4 ARR 集成与高刷新率优化
- RecyclerView 1.4 内置 ARR（Adaptive Refresh Rate）支持
- fling/smoothScroll 时自动提升刷新率的机制
- setFrameContentVelocity API 与刷新率投票
- 高刷新率下 RecyclerView 的性能特征变化（更短的帧预算、更频繁的布局）
- OverScroller 时间精度对高刷新率设备的影响

## 扩展

### 🔸 扩展点 1：自定义 LayoutManager 性能
- 自定义 LayoutManager 的布局策略对性能的影响
- LinearLayoutManager vs GridLayoutManager vs StaggeredGridLayoutManager 的性能差异
- setInitialPrefetchItemCount 在不同 LayoutManager 下的最佳值

### 🔸 扩展点 2：ItemDecoration 与 ItemAnimator 性能
- getItemOffsets 和 onDraw 对布局和绘制性能的影响
- SimpleItemAnimator vs DefaultItemAnimator 的性能差异
- 支持变更动画的代价：需要两次布局 pass

### 🔸 扩展点 3：Compose LazyColumn 与 RecyclerView 的性能对比
- LazyColumn 的 item composition 与 RecyclerView 的 bind 的类比
- Compose lazy list 的 prefetch 策略
- 何时选择 RecyclerView、何时选择 LazyColumn

<!-- outline-end -->

> 本节内容待加工。
