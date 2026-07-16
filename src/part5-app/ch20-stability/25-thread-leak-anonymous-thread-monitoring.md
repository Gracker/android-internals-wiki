---
title: "线程泄漏与匿名线程监控实战"
chapter: "20.25"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [thread, leak, monitoring, stability, ThreadGroup, pthread, FD]
related_chapters: ["20.1", "20.5", "20.21"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动+章节深挖"
---

# 20.25 线程泄漏与匿名线程监控实战

<!-- outline-start -->
## 要点

### 🔹 线程泄漏的危害与类型
- 线程泄漏 → FD 耗尽 → ANR/crash 链路
- 匿名线程（Anonymous Thread）的来源：第三方 SDK、线程池配置不当、未取消的定时任务
- 线程泄漏与内存泄漏的关联：线程持有 Context → Activity 无法回收

### 🔹 Java 层线程监控方案
- ThreadGroup.activeCount() 遍历与线程列表获取
- Thread.getAllStackTraces() 获取全量线程堆栈
- 线程命名规范与「匿名线程」识别策略
- [结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决"匿名"线程？]

### 🔹 Native 层线程监控
- /proc/self/task/ 目录遍历获取 Native 线程列表
- pthread_create hook 监控 Native 线程创建
- 线程名通过 prctl(PR_SET_NAME) 设置的覆盖率检查

### 🔹 线程池泄漏检测
- ThreadPoolExecutor 的 activeCount vs poolSize 判断
- ScheduledThreadPoolExecutor 未关闭任务检测
- OkHttp Dispatcher 线程池监控
- Kotlin Coroutine Dispatcher 线程泄漏排查

### 🔹 线程创建阈值与告警
- 基于 ulimit 与 /proc/self/limits 的线程数上限检测
- 线程数分级告警策略（如 200 警告 / 400 严重 / 500 危急）
- 线程数突增检测（短时间大量创建）

### 🔹 线程与 FD 关联监控
- 每个线程默认占用 1MB 栈空间（可通过 Thread.stackSize 调整）
- 线程数与 FD 消耗的对应关系
- /proc/self/fd 目录监控与 FD 类型分析

### 🔹 线上线程治理体系
- 线程命名注册表（ThreadFactory 统一命名）
- 线程快照定期上报（启动后/前台/后台/ANR 时）
- 线程数基准线与版本间回归检测

### 🔹 典型案例分析
- 第三方广告 SDK 创建大量匿名线程导致 FD 耗尽
- Coroutine 的 GlobalScope 泄漏导致线程不可回收
- WorkManager 多进程场景下的线程数膨胀

## 扩展

### 🔸 Android 17 线程创建限制
- Android 17 对 bionic 的线程创建安全检查增强
- RLIMIT_NPROC 在 Android 容器化场景下的影响

### 🔸 Perfetto 线程状态追踪
- 使用 Perfetto 的 Linux process_stats 插件进行线程级分析
- sched_switch 事件与线程生命周期的关联

<!-- outline-end -->

> 本节内容待加工。
