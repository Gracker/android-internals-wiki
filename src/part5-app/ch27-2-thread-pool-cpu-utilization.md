---
title: "线程池优化与 CPU 利用率提升实战"
chapter: "27.2"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [CPU优化, 线程池, ThreadPoolExecutor, 并发调度, 性能优化]
related_chapters: ["5.1", "5.2", "27.1", "21.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings性能优化参考书 + Ch27结构性缺口"
gap_score: 18
---

# 27.2 线程池优化与 CPU 利用率提升实战

<!-- outline-start -->
## 要点

### 🔹 ThreadPoolExecutor 核心参数与调度策略
- corePoolSize / maximumPoolSize / workQueue 的配比原理
- CPU 密集型 vs IO 密集型线程池的参数选型差异
- keepAliveTime 与非核心线程回收时机
- [结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]

### 🔹 线程池工厂与线程命名治理
- 自定义 ThreadFactory 的工程意义（排查 / 优先级 / 安全）
- 线程命名规范与线上问题定位
- 线程池分组隔离策略：网络池 / 解码池 / 计算池

### 🔹 Executors 预设线程池的陷阱
- FixedThreadPool / CachedThreadPool / SingleThreadExecutor 的适用边界
- newCachedThreadPool 无界线程创建的 OOM 风险
- 为什么 Google 官方推荐显式使用 ThreadPoolExecutor

### 🔹 CPU 利用率测量与瓶颈识别
- /proc/stat 与 /proc/[pid]/stat 读取与 CPU 占用率计算
- top -H / simpleperf / Perfetto 定位 CPU 热点线程
- CPU 利用率指标体系：usr / sys / iowait / idle 的含义与优化目标

### 🔹 线程池空闲检测与动态调优
- 线程池运行时参数热更新：setCorePoolSize / setMaximumPoolSize
- 基于设备性能分级的线程池配置策略
- allowCoreThreadTimeOut 的适用场景

### 🔹 协程 Dispatchers 与线程池映射
- Dispatchers.Default / IO / Main 的底层线程池实现
- CoroutineScheduler 的线程复用与抢占机制
- withContext 切换开销与批量调度优化

## 扩展

### 🔸 Android 17 cgroup v2 对线程优先级的影响
- 前台 / 后台 cgroup 对线程调度优先级的实际影响
- 详见 1.56 节 cgroup v2 统一层级

### 🔸 PerformanceHintManager 与线程池联动
- ADPF 自适应性能提示对线程池吞吐量的影响
- 详见 8.37 节 PerformanceHintManager 实战

### 🔸 多进程架构下的线程池隔离与协同
- 多进程 App 的线程池总量管控
- 跨进程任务分发的 Binder 线程池瓶颈识别

<!-- outline-end -->

> 本节内容待加工。
