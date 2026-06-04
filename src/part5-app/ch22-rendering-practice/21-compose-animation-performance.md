---
title: "Jetpack Compose 动画性能深度优化"
chapter: "22.21"
section: "22.21"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, animation, animated-visibility, transition, animatable, strong-skipping, performance]
related_chapters: ["22.3", "22.5", "22.20", "7.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "研究素材"
sources:
  - type: research
    path: "DeepResearch/2026-06-01-android-compose-animation-performance-bottlenecks.md"
  - type: research
    path: "DeepResearch/2026-06-02-android-compose-110-strong-skipping-mechanism.md"
  - type: research
    path: "DeepResearch/2026-06-02-android-compose-derivedstate-sso-deep-source-analysis.md"
---

# 22.21 Jetpack Compose 动画性能深度优化

<!-- outline-start -->
## 要点

### 🔹 AnimatedVisibility 底层机制与双重重绘风险
- updateTransition(visible) 创建/复用 Transition<Boolean> 实例
- Layout measure policy 遍历子元素取最大宽高，动画期间每帧尺寸变化
- 父容器 wrap_content 时每帧触发父容器重测
- exit 动画未完成前 content 仍在 Composition 中保持活跃

### 🔹 Transition 状态机与 MutableTransitionState 性能特征
- Transition 是非重启式组合，通过 MutableTransitionState 管理状态
- 动画运行在 Compose AnimationClock 而非 Choreographer 帧时钟
- 快速 toggling visible 导致动画频繁中断重启

### 🔹 Animatable 精密动画控制与非重组驱动
- Animatable<T> 是单值动画状态持有者
- animateTo() 在协程中运行，不触发重组只触发重绘
- 与 Transition 的适用场景区别

### 🔹 produceState 在动画场景中的陷阱
- produceState 使用 LaunchedEffect(Unit) 启动协程，key 固定不重启
- producer 内 state.value 更新频率直接决定重组频率
- 60fps 动画 + produceState = 每帧一次 Snapshot 写事务 + 重组传播
- 优化路径：snapshotFlow 做节流 / 使用 animateXxxAsState 专用 API

### 🔹 AnimatedVisibility vs AnimatedContent 性能对比
- AnimatedVisibility：exit 动画完成后才移除内容，退出期间 content 仍参与重组
- AnimatedContent：内容切换时立即替换，重组风险低
- 尺寸动画传播范围差异
- 列表场景中的选型建议

### 🔹 Strong Skipping 模式对动画代码的影响
- Strong Skipping 改变了 Composable 的重启条件
- 动画相关 Composable 中 lambda 捕获的稳定性要求
- rememberCoroutineScope / produceState 在 Strong Skipping 下的行为变化

### 🔹 动画帧预算与性能观测
- Choreographer 帧信号与 Compose 动画时钟的同步关系
- Perfetto 中识别 Compose 动画导致的帧延迟
- FrameMetrics 定位动画相关的帧超时

### 🔹 Compose 动画性能优化实践清单
- P0 级：必须避免的动画反模式
- P1 级：推荐优化实践
- 动画场景下的 Compose 重组成略

## 扩展

### 🔸 Compose 动画与 View 动画的互操作性能
- ComposeView 内嵌 View 动画的同步问题
- AndroidView + Compose 动画的帧预算共享

### 🔸 大规模列表中的动画性能策略
- LazyColumn 中 item 出现/消失动画的帧预算控制
- ItemAnimator 与 Compose AnimatedVisibility 的替代方案

### 🔸 Compose 动画的 Benchmark 方法
- Macrobenchmark 测量动画帧率
- Compose Animation Inspector 的使用
- [待补充]

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
