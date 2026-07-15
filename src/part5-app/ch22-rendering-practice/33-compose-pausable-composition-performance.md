---
title: "Compose PausableComposition 性能机制与 Choreographer Deadline 协作"
chapter: "22.33"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Compose, PausableComposition, Choreographer, 渲染性能, FrameData]
related_chapters: ["2.4", "22.3", "22.21", "22.22"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "研究素材+章节深挖"
confidence: medium
---

# 22.33 Compose PausableComposition 性能机制与 Choreographer Deadline 协作

<!-- outline-start -->
## 要点

### 🔹 PausableComposition 的起源与版本演进
- Compose 1.7 引入 PausableComposition 作为内部性能优化机制
- Compose 1.10（2025 年 12 月稳定）将其设为默认行为
- 从"必须单帧完成"到"可跨帧暂停"的范式转变

### 🔹 核心控制流：setPausableContent → resume() → shouldPause → apply()
- setPausableContent() 不立即组合 UI，返回 PausedComposition 控制器对象
- resume() 执行分块组合工作，内部通过 shouldPause lambda 检查帧截止时间
- shouldPause 返回 true 时暂停 Composition，主线程让出给当前帧绘制任务
- isComplete=true 后调用 apply() 提交 UI 变更

### 🔹 shouldPause 回调与 FrameData Deadline 判定
- shouldPause 基于 Choreographer.FrameData.getDeadlineNanos() 判定
- 与 VSYNC-app、Frame Timeline 的 Expected/Actual 协同
- 帧截止时间临近时如何决定暂停粒度

### 🔹 LazyList 预取系统集成
- PausableComposition 与 LazyColumn/LazyRow 预取深度集成
- 空闲时间增量组合即将滚动到可见区域的列表项
- Compose 1.9 CacheWindow API 进一步利用 pausable composition

### 🔹 applyChanges() 提交机制
- applyChanges() 回放缓冲命令、分发生命周期回调
- 未完成的 UI 树不会被渲染
- SideEffect 排队与 flush 时机

### 🔹 Node 树 Checkpoint 与可暂停位置
- Composition tree 结构支持在特定位置插入可暂停 checkpoint
- 不是协程的 CancellationException 机制，而是 Compose runtime 内部中断点
- Compose 1.7 之前单帧不可中断的约束及其导致的 jank

## 扩展

### 🔸 与 Compose 1.10 默认行为的性能对比数据
- 使用 Macrobenchmark 对比 1.9 vs 1.10 的帧率差异
- LazyColumn 滚动场景下的 jank 率变化

### 🔸 CacheWindow API 与 PausableComposition 的协同
- Compose 1.9 CacheWindow 对预取窗口的精确控制
- 与 LazyList prefetch 机制的交互

<!-- outline-end -->

> 本节内容待加工。
