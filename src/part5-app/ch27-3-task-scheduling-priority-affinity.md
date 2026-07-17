---
title: "任务调度优先级与 CPU 亲和性实战"
chapter: "27.3"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [CPU优化, 任务调度, 线程优先级, CPU亲和性, PerformanceHintManager]
related_chapters: ["5.1", "5.2", "5.31", "27.1", "27.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings性能优化参考书（任务调度优化章）+ AOSP cgroup/scheduling"
gap_score: 16
---

# 27.3 任务调度优先级与 CPU 亲和性实战

<!-- outline-start -->
## 要点

### 🔹 线程优先级体系与 nice 值
- Linux nice 值（-20 ~ 19）与 Android Process.setThreadPriority
- Thread.setPriority 与 Linux nice 的映射关系
- 前台线程优先级提升的实际调度效果
- [结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]

### 🔹 cgroup 与任务分类
- Android cgroup v2 分层：top-app / foreground / background / restricted
- 任务被打入 background cgroup 的场景与性能影响
- cgroup CPU 配额机制对线程执行速度的直接制约

### 🔹 CPU 亲和性（affinity）设置
- sched_setaffinity 与 CPU 核心绑定
- 大核 / 小核任务分配策略
- Android 17 EEVDF 调度器下亲和性的新行为（详见 5.31 节）

### 🔹 任务调度框架对比：Handler / Executor / Coroutine
- Handler.post 的消息驱动调度模型
- ThreadPoolExecutor 的任务排队与拒绝策略
- Kotlin Coroutine 的结构化并发与调度器选择
- 三者的适用场景与性能特性对比

### 🔹 后台任务调度与系统节流
- JobScheduler / WorkManager 的优先级与节流机制
- Android 12+ 后台执行限制对任务调度的影响
- 前台服务 + 线程池的后台高性能调度方案

### 🔹 关键路径任务提权实战
- UI 线程关联任务的 bindService / getContentProvider 提权
- AsyncTask Deprecated 后的正确异步模式
- 关键路径线程优先级动态提升与恢复

## 扩展

### 🔸 sched_ext 与 BPF 可编程调度器
- Android 17 GKI 6.18 的 sched_ext 对应用层调度的影响
- 详见 5.31 节 EEVDF 调度器

### 🔸 AMU / PMU 辅助的 CPU 微架构感知调度
- ARM AMU 计数器驱动的任务->核心分配
- 详见 5.28 节 PELT Boost 回退与 AMU/PMU

<!-- outline-end -->

> 本节内容待加工。
