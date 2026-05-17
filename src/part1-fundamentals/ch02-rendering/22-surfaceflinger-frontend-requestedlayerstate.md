---
title: "SurfaceFlinger FrontEnd 与 RequestedLayerState"
chapter: "2.22"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [rendering, surfaceflinger, frontend, requestedlayerstate, transaction]
related_chapters: ["2.6", "2.12", "2.13", "18.10", "13.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "素材驱动/AOSP结构/官方文档"
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrontEnd/RequestedLayerState.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrontEnd/LayerLifecycleManager.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrontEnd/TransactionHandler.h"
  - type: official
    path: "https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager"
  - type: research
    path: "DeepResearch/2026-05-09-surfaceflinger-frontend-architecture-android15.md"
---

# 2.22 SurfaceFlinger FrontEnd 与 RequestedLayerState

<!-- outline-start -->
## 要点

### 🔹 FrontEnd 引入背景：Layer 状态从单体锁到请求快照
说明 Android 15 之后 SurfaceFlinger 为什么把客户端请求状态和合成计算状态拆开，重点落在事务吞吐、`mStateLock` 持锁范围、Layer 数量增长后的主线程压力。

### 🔹 RequestedLayerState：App 请求状态的稳定表示
梳理 `RequestedLayerState` 与 `layer_state_t` 的关系、`Changes` bitmask 的用途、几何/层级/元数据/帧率等字段如何记录客户端意图。

### 🔹 LayerLifecycleManager：Layer 创建、销毁与变更批处理
说明 `addLayers()`、`applyTransactions()`、`commitChanges()` 的边界，以及 `getChangedLayers()` / `getGlobalChanges()` 如何把全量状态管理变成增量更新。

### 🔹 LayerHierarchyBuilder：从请求状态构建可遍历层级
解释普通父子、relative parent、mirror layer、detached layer 的层级表达，以及为什么 SurfaceFlinger 需要在合成前重新计算遍历路径。

### 🔹 TransactionHandler：事务队列、就绪判断与 fence 约束
覆盖 `TransactionState`、`TransactionReadiness`、unsignaled buffer、present time、barrier 等因素如何决定一笔 SurfaceControl 事务是否能进入本帧。

### 🔹 FrontEnd 与合成线程的交接点
说明 FrontEnd 产出的 LayerSnapshot / 层级结果如何进入后续 composition planning，避免把 HWC、BufferQueue、Sync Fence 原理在本节重复展开。

### 🔹 观测方法：Perfetto、Winscope 与 dumpsys 如何对应 FrontEnd 状态
列出能观察事务、Layer 层级、latch 时间和合成结果的工具入口，说明哪些字段来自请求状态，哪些字段来自合成后的运行状态。

## 扩展

### 🔸 Android 15 前后 SurfaceFlinger 状态管理差异
对比旧架构中 Layer 内部状态直接更新的路径和 FrontEnd 架构的请求快照路径。

### 🔸 FrontEnd 对锁竞争与事务延迟的影响验证
设计一套验证方法：多 SurfaceControl 事务压测、Perfetto 中 SurfaceFlinger 主线程 slice、锁等待、事务排队时间和帧延迟的关联分析。

### 🔸 SurfaceControl API 使用误区
整理 App 侧频繁提交 position/alpha/crop/frameRate 事务时可能带来的调度压力，以及与 Choreographer 帧节奏的关系。

<!-- outline-end -->

> 本节内容待加工。
