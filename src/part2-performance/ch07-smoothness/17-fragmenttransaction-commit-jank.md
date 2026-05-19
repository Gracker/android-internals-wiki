---
title: "FragmentTransaction 提交时序与主线程卡顿"
chapter: "7.17"
status: draft
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [fragment, jank, main-thread, choreographer, jetpack]
related_chapters: ["7.3", "7.4", "8.1", "13.3", "22.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "素材驱动/官方文档/AOSP结构"
gap_score: 17
material_paths:
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-fragmenttransaction-commit-source-chain.md"
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-05-fragmenttransaction-commit-source-chain.md"
  - "DeepResearch/2026-05-08-fragment-transaction-commit-source-chain.md"
  - "https://developer.android.com/guide/fragments/transactions"
  - "https://developer.android.com/topic/performance/vitals/render"
  - "https://cs.android.com/androidx/platform/frameworks/support/+/androidx-main:/fragment/"
---

# 7.17 FragmentTransaction 提交时序与主线程卡顿

<!-- outline-start -->
## 要点

### 🔹 提交入口：commit、commitNow 与 allowStateLoss 的性能语义
区分 `commit()`、`commitNow()`、`commitAllowingStateLoss()`、`executePendingTransactions()` 的执行方式、状态保存边界和主线程阻塞风险，避免把生命周期语义问题误判成单纯的卡顿问题。

### 🔹 待执行队列：从 BackStackRecord 到 FragmentManager pending actions
梳理 AndroidX FragmentManager 将事务封装为待执行操作的路径，重点记录 `enqueueAction()`、`scheduleCommit()`、`mExecCommit`、`execPendingActions()` 之间的关系。平台 `android.app.Fragment` 已废弃，正文以 AndroidX 为主，平台实现只作为历史对照。

### 🔹 主线程时序：Handler.post、Looper 与 Choreographer 的相对位置
说明 `commit()` 只把事务安排到主线程消息队列，并不绑定某一次 VSync；影响帧的是事务执行期间创建/销毁 Fragment view、触发布局和生命周期回调的耗时。需要把 Looper message、Choreographer callback、View traversal 三段时间分开观察。

### 🔹 卡顿根因：事务本身、视图膨胀和生命周期副作用分开归因
把一次 Fragment 切换拆成事务调度、`onCreateView()` / inflate、`onViewCreated()` 初始化、列表首屏绑定、网络/磁盘误入主线程几类成本，避免把所有长帧都归到 FragmentManager。

### 🔹 可观测性：Perfetto、trace section 与 FrameTimeline 对齐
给出 trace 观察点：主线程 message 边界、`FragmentManager` 日志、应用自定义 trace section、FrameTimeline jank 标记、RecyclerView / Compose 首屏绑定轨道。章节只给排查框架，SQL 细节引用 13.3、13.10 和 13.14。

### 🔹 优化策略：延迟、拆分、预加载与事务合并的边界
整理可执行策略：避免同帧连续提交多笔事务、重视 `setReorderingAllowed(true)`、把重初始化移出生命周期回调、首屏列表使用稳定的预取策略、需要同步可见结果时优先评估 `commitNow()` 的阻塞代价。

### 🔹 版本边界：平台 Fragment、AndroidX Fragment 与 Jetpack 版本差异
记录平台 Fragment 废弃、AndroidX Fragment release note、`FragmentStrictMode`、事务重排行为和 Navigation 组件对 Fragment 事务的封装差异，避免把旧平台源码结论直接套到现代 AndroidX 项目。

## 扩展

### 🔸 FragmentTransaction 与 Navigation 组件的时序差异
比较手写事务、Navigation `navigate()`、DialogFragment `show()` / `showNow()` 在提交时机和生命周期推进上的差异。

### 🔸 Fragment 切换与共享元素动画的帧预算
补充共享元素、Transition、Postponed enter transition 对首帧和中间帧的影响。

### 🔸 FragmentScenario / Macrobenchmark 验证模板
给出可复现实验方向：同一页面用 `commit()`、`commitNow()`、事务合并、预 inflate 四种方式对比 P50/P90 frame time。

<!-- outline-end -->

> 本节内容待加工。
