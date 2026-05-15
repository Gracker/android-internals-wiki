---
title: "FragmentTransaction 提交链路与页面切换性能"
chapter: "22.12"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [fragment, rendering, jank, startup, androidx]
related_chapters: ["7.4", "8.4", "13.3", "18.2", "22.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/AOSP结构/官方文档"
---

# 22.12 FragmentTransaction 提交链路与页面切换性能

<!-- outline-start -->
## 要点

### 🔹 commit() 的异步提交语义
从 `FragmentTransaction.commit()`、`BackStackRecord.commitInternal()` 到 `FragmentManager.enqueueAction()` 建立源码链路，区分 `commit()`、`commitNow()`、`executePendingTransactions()` 和 `commitAllowingStateLoss()` 的执行边界。

### 🔹 execPendingActions() 与主线程 MessageQueue
解释待执行事务如何进入主线程队列，`execPendingActions()` 如何批量取出 pending action，并说明递归执行、状态保存和 `mExecutingActions` 这类保护逻辑对性能排查的影响。

### 🔹 与 Choreographer / traversal 的时序关系
把 Fragment 生命周期推进、`runOnCommit()`、`ViewRootImpl` traversal、下一帧绘制放到同一条时间线中，说明页面切换卡顿为什么经常出现在主线程消息而非 `doFrame` 切片内。

### 🔹 setReorderingAllowed(true) 的性能含义
基于 AndroidX Fragment 官方文档和源码，说明 reordering 对生命周期回调、动画/transition、冗余操作合并的影响，避免把它误解成单纯的“加速开关”。

### 🔹 页面切换 Perfetto 观察点
整理 trace 中可观察的 Activity/Fragment 生命周期、主线程长任务、layout/inflate、动画帧、Binder 与磁盘 I/O 迹象，形成页面切换卡顿的排查清单。

### 🔹 工程治理策略
给出复杂页面拆分、懒加载、事务批处理、`commitNow()` 使用边界、首帧前后任务切分、Fragment Result / Navigation 回退的实践建议。

## 扩展

### 🔸 AndroidX Fragment 版本差异
跟踪 Fragment 1.4+ 新 State Manager、1.6/1.7/1.8 行为修复，以及与平台 `android.app.Fragment` 废弃路径的差异。

### 🔸 Navigation Component 与 FragmentTransaction
分析 Navigation 内部事务封装、back stack、动画和 shared element transition 对页面切换性能的影响。

### 🔸 Compose 与 Fragment 混用边界
补充 `ComposeView` 在 Fragment 生命周期中的销毁策略、RecyclerView / Fragment 嵌套时的 pooling container 语义，以及与 22.3 的交叉引用。

<!-- outline-end -->

> 本节内容待加工。
