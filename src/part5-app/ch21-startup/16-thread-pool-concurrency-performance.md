---
title: "线程池与并发调度性能实战"
chapter: "21.16"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [thread-pool, concurrency, cpu-scheduling, startup, coroutines]
related_chapters: ["1.5", "5.1", "8.6", "8.17", "20.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "素材驱动/参考书"
---

# 21.16 线程池与并发调度性能实战

<!-- outline-start -->
## 要点

### 🔹 线程池配置对启动性能的直接冲击

`ThreadPoolExecutor` 的 corePoolSize / maxPoolSize / queueCapacity 三参数如何决定启动阶段的任务吞吐；核心线程数设太低导致任务排队 → 启动拉长；设太高 → CPU 上下文切换开销暴增；启动阶段推荐配置策略（CPU 密集型 corePoolSize = CPU 核心数 + 1）。

### 🔹 线程池类型选型矩阵

`FixedThreadPool` vs `CachedThreadPool` vs `ScheduledThreadPool` vs `ForkJoinPool` 的适用场景；Android 启动阶段各线程池的实测吞吐对比（任务粒度 <1ms / 1-10ms / >10ms）；为什么 `AsyncTask.THREAD_POOL_EXECUTOR` 的默认配置在大型 App 中会变成瓶颈。

### 🔹 CPU 线程池与 IO 线程池分离

CPU 密集型任务（解码、计算、编译）与 IO 密集型任务（网络、磁盘、数据库）为什么要用不同线程池；IO 线程池可以远超 CPU 核心数（等待不消耗 CPU），CPU 线程池不能；混合使用导致 CPU 线程被 IO 任务占满的典型故障模式。

### 🔹 线程优先级与 Android 调度

`Process.setThreadPriority()` 与 `Thread.setPriority()` 的区别；Android 的 nice 值体系（-20 到 19）与 Linux CFS 调度器的交互；关键路径线程（主线程、RenderThread）绑定大核的策略；`sched_setaffinity` 在 Android 上的使用边界。

### 🔹 Coroutine Dispatcher 与线程池映射

`Dispatchers.Default` 的底层实现（`SchedulerCoroutineDispatcher` → `CoroutineScheduler`）；`Dispatchers.IO` 的弹性线程池与 `limitedParallelism` 新机制；为什么 `Dispatchers.Main` 不适合做计算密集任务；Coroutine 线程池与传统 ThreadPool 的性能对比（上下文切换开销、调度延迟）。

### 🔹 线程治理：减少线程数量的工程实践

大型 App 动辄 200+ 线程的根因（SDK 各自创建线程池、匿名 Thread）；线程数量过多对内存（每个线程约 1MB 虚拟内存栈）和 CPU（调度开销）的双重压力；线程收敛策略：统一线程池管理、SDK 线程审计、Hook `Thread.start()` 拦截；线程命名规范对调试效率的影响。

### 🔹 线程泄漏检测与监控

线程泄漏的典型模式（未 shutdown 的线程池、匿名 Thread 持有 Activity）；如何在线上监控线程数量与生命周期；`Thread.isActive` 与 `ThreadPoolExecutor` 状态检测方案；参考 ch20.14 的线程与 FD 资源监控体系。

### 🔹 启动阶段任务编排中的线程池策略

启动框架（App Startup / 自研启动框架）中的线程池配置策略；有依赖关系的任务如何调度（拓扑排序 + 线程池分配）；无依赖任务的并行度控制；启动阶段 CPU 使用率监控：目标 80%+ 但避免 100% 饱和。

### 🔹 Android 16/17 线程调度行为变更

Android 16 对后台线程调度的限制变更；Android 17 Foreground Service 类型声明对线程优先级的影响；`OomAdjuster` 对线程优先级的动态调整策略。

## 扩展

### 🔸 WorkManager 内部线程池

WorkManager 的 Worker 线程池配置与系统配额机制；Coroutine Worker vs ListenableWorker 的性能差异。

### 🔸 线程池监控指标体系

活跃线程数、队列长度、拒绝任务数、任务平均执行时间的采集方案；线程池热点定位（哪个任务占用了线程池）。

### 🔸 Java 21 Virtual Thread 在 Android 的前瞻

Project Loom Virtual Thread 在 Android 的可行性；ART 对 Virtual Thread 的支持时间线预测；Virtual Thread 对现有线程池架构的冲击。

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]
[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]
[结构参考: Clippings/Android 性能优化 - 线程优化：如何做好线程治理也将会是一种优化手段.md]
