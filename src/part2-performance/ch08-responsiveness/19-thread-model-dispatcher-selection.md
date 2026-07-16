---
title: "Android 线程模型与调度器选型实战"
chapter: "8.19"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['thread-model', 'coroutine-dispatcher', 'executor-service', 'handler-thread', 'thread-pool']
related_chapters: ['8.06', '8.17', '21.16']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动"
---

# 8.19 Android 线程模型与调度器选型实战

<!-- outline-start -->
## 要点

### 🔹 Coroutine Dispatchers 底层实现：CoroutineDispatcher 与 ThreadPoolExecutor 映射
### 🔹 Dispatchers.IO vs Dispatchers.Default：线程池共享与并发度控制
### 🔹 ExecutorService → Coroutine 桥接：asCoroutineDispatcher 的开销与陷阱
### 🔹 HandlerThread / Handler / MessageQueue 性能特征
### 🔹 线程池大小选择：CPU 密集型 vs IO 密集型 vs 混合型
### 🔹 线程优先级与 Android 进程优先级的交互
### 🔹 Structured concurrency 与线程取消传播
### 🔹 Android 17 线程调度变更与 PerformanceHintManager 协同

## 扩展

### 🔸 Snapshot/Channel vs BlockingQueue 选型
### 🔸 协程上下文切换开销实测
### 🔸 线程泄漏检测与治理（衔接 20.25）

<!-- outline-end -->

> 本节内容待加工。

<!--
缺口分析摘要：全书缺少线程模型选型的系统性对比。ExecutorService vs Coroutine Dispatcher 0 次提及，HandlerThread performance 0 次提及。需要覆盖：Dispatchers.IO/Default/Main/Unconfined 的底层实现与适用场景、ExecutorService 与 Coroutine Dispatcher 的等价关系与转换、HandlerThread 与 MessageQueue 性能特征、线程池大小选择策略、Android 17 线程调度变更。
评分：17/20 ({'素材丰富度': 3, '相关性': 5, '读者需求度': 5, '时效性': 4})
-->
