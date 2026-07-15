---
title: "Compose 无限动画与 VectorConverter 性能优化"
chapter: "22.32"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, animation, infinite-transition, vector-converter, performance]
related_chapters: ["22.5", "22.21", "22.11", "22.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构+章节深挖"
confidence: medium
---

# 22.32 Compose 无限动画与 VectorConverter 性能优化

<!-- outline-start -->
## 要点

### 🔹 rememberInfiniteTransition 的性能特征
- InfiniteTransition 与 Transition 的架构差异
- rememberInfiniteTransition 的帧驱动机制：基于 Choreographer 的 vsync 回调
- 无限动画对主线程帧预算的持续占用
- 多个 infiniteAnimable 并行运行时的 CPU 开销累积

### 🔹 InfiniteAnimation 的底层调度
- AnimationClockakov 与 MonotonicFrameClock 的协作
- InfiniteTransition.runInfiniteLoop() 的重组模式
- 无限动画暂停时的资源释放（DisposableEffect 链路）
- Android 17 Compose 1.9+ 中 infinite animation 的帧调度优化

### 🔹 VectorConverter 与 AnimatedVectorDrawable 性能
- AnimatedVectorDrawable 在 Compose 中的加载路径
- VectorConverter：将 VectorDrawable XML 转换为 Compose 动画树
- VectorConverter 生成的 ObjectAnimation 的性能开销分析
- 批量 VectorConverter 解析对内存分配的影响

### 🔹 无限动画的性能优化策略
- 使用 graphicsLayer 替代 Modifier.offset 进行变换
- alpha 动画的合成层策略与 GPU 开销
- 无限动画的降帧策略：在低端机上降低更新频率
- DeratingStrategy：在不可见时自动暂停动画（basedOnState 等模式）

### 🔹 场景案例
- 加载指示器（Loading Spinner）的性能优化
- 呼吸灯/脉冲动画的 GPU 合成层复用
- 声纹/波形动画的 Canvas 绘制优化
- 进度条动画的帧节流策略

### 🔹 动画性能诊断工具
- Compose Compiler Metrics 中的动画重组检测
- Layout Inspector 的动画录制与回放分析
- Perfetto 中 Compose 动画帧的 trace 标记
- Choreographer.skippedFrames 的监控

## 扩展

### 🔸 Compose 动画与 ViewPropertyAnimator 的对比
- 声明式 vs 命令式动画的性能差异
- 混合使用场景下的最佳实践

### 🔸 Android 17 Compose 动画新特性
- Compose 1.9+ 的 AnimationSpec 改进
- TargetBasedAnimation 的预测性帧调度

<!-- outline-end -->

> 本节内容待加工。

[缺口来源: 全书 0 处提及 rememberInfiniteTransition、VectorConverter，动画实战覆盖不足]
