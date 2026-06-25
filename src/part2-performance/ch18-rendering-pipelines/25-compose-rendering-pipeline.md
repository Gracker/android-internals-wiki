---
title: "Jetpack Compose 渲染管线架构"
chapter: "18.25"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, rendering, rendernode, choreographer, pausable-composition, android-compose-view]
related_chapters: ["2.4", "2.5", "2.6", "7.7", "22.3", "22.20", "22.25", "22.26"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "AOSP结构+章节深挖"
---

# 18.25 Jetpack Compose 渲染管线架构

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Compose 渲染入口 — AndroidComposeView
- AndroidComposeView 继承 ViewGroup，是 Compose 挂载到 Android View 树的根节点
- dispatchDraw() 调用链条：AndroidComposeView.onDraw → RenderNode 创建 → display list 构建
- 与传统 View 的 onDraw(Canvas) 区别：Compose 不走 ViewGroup 的 measure/layout/draw 递归，而是用自己的 LayoutNode 树和测量协议

### 🔹 锚点 2：LayoutNode 树与测量/布局/绘制三阶段
- LayoutNode 是 Compose 的节点抽象（对应 View 体系中的 View）
- 测量协议：IntrinsicMeasureScope.measure() → MeasureResult，与 View 的 onMeasure(WidthMeasureSpec, HeightMeasureSpec) 的对比
- Density / Constraints 传递机制
- LayoutNodeLayoutOrder：深度优先遍历，parent 先 measure 再 layout
- 绘制阶段：LayoutNode.draw(Canvas) → DrawContentScope → RenderNode 创建

### 🔹 锚点 3：RenderNode 与 DisplayList 生成
- 每个 LayoutNode 在绘制时生成或更新对应的 RenderNode
- Compose 使用 RenderNode 的方式与 View 体系一致：构建 display list，提交给 HardwareRenderer
- Compose 的 RenderNode 管理策略：节点的 invalidate / re-record 边界
- LayerManager：何时创建独立 Layer（opacity, clip, transform 场景）

### 🔹 锚点 4：Compose 与 Choreographer 的集成
- AndroidComposeView 注册 Choreographer.FrameCallback 监听 VSync
- doFrame() 回调触发：recomposition → measure/layout → draw → submit to RenderThread
- Compose 1.10+ PausableComposition 改变了这一流程：composition 可在帧 deadline 临近时暂停
- shouldPause 回调与 FrameData.getDeadlineNanos() 的协作
- 与传统 View 的 invalidate() → performTraversals() 的区别

### 🔹 锚点 5：PausableComposition 机制（Compose 1.7+，1.10 默认启用）
- setPausableContent() 返回 PausedComposition 控制器
- LazyList 预取系统集成：空闲时间增量组合即将可见的列表项
- shouldPause lambda 检查点：基于 Node 树结构的 checkpoint 插入
- apply() 提交机制：isComplete=true 时一次性提交所有变更
- 与 1.7 之前行为的对比：单帧必须完成 vs 可跨帧分块

### 🔹 锚点 6：Snapshot 系统与重组触发
- Snapshot（快照）是 Compose 状态管理的核心：StateFlow / mutableStateOf 底层都是 SnapshotState
- 读写追踪：remember / derivedStateOf / recomposition scope 的建立
- invalidation 传播：Snapshot 帧提交时比对 State 变更，标记受影响的 recomposition scope
- 全局快照 vs 局部快照：Snapshot.takeMutableSnapshot() 的应用
- 与传统 View 的 invalidate() 标记-重绘模型的本质差异

### 🔹 锚点 7：Compose 与 RenderThread 的协作
- Compose 构建完 display list 后，通过 HardwareRenderer 提交给 RenderThread
- RenderThread 负责 GPU 绘制命令录制和提交（与 View 体系共用同一条路径）
- Compose 的 drawAll() → syncAndDrawFrame() 链路
- BufferQueue 与 Surface 的关系：Compose 的 Surface 来自 AndroidComposeView

### 🔹 锚点 8：Compose 与 View 体系互操作渲染
- AndroidView composable 的渲染路径：Compose LayoutNode → 包装 View → View 的 draw 挂载
- AndroidView wrap 性能开销：measure/layout 协议转换
- ComposeView 嵌入 View 体系的反向场景
- 互操作场景下的双管线同步问题（Compose invalidation + View invalidate）

## 扩展

### 🔸 扩展点 1：Compose 语义树 (Semantics) 与无障碍性能
- SemanticsNode 的构建成本
- 与 AccessibilityNodeInfo 的映射

### 🔸 扩展点 2：Compose 文本渲染与性能
- TextLayoutResult 缓存机制
- 长文本和 RichText 的测量开销
- BasicTextField 与 IME 的交互性能

### 🔸 扩展点 3：Compose 动画渲染性能
- animate*AsState 与 Animatable 的帧调度
- Compose 动画与 RenderThread 的关系
- LookaheadLayout（预测性布局）的性能成本

### 🔸 扩展点 4：Compose 渲染调试与观测
- Compose Compiler Metrics 输出解读
- Layout Inspector 中的 Compose 树
- Perfetto trace 中 Compose 相关 track 的识别

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Compose rendering internals - AOSP frameworks/support/compose, Jetpack Compose source code]
[关联研究素材: intake/research-feeds/2026-04-10-07-compose-pausable-composition-choreographer-deadline.md]
