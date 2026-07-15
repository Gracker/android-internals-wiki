---
title: "FD 泄漏监控与线程资源治理实战"
chapter: "20.21"
status: deprecated
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [fd-leak, thread-monitoring, resource-governance, stability, native]
related_chapters: ["20.14", "20.2", "20.3", "20.4", "20.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动+Clippings"
confidence: medium
---

> ⚠️ **本节已废弃（2026-07-16）**
> 与已 finalized 的 §20.14「线程与 FD 资源监控治理」内容重叠 >80%。
> §20.14 已完整覆盖 FD 快照、创建归因、匿名线程治理、线上策略和关联判定，
> 并使用相同 Clippings 参考书。本节大纲为重复创建，不再单独成节。
> 详见：`src/part5-app/ch20-stability/14-thread-fd-resource-monitoring.md`



# 20.21 FD 泄漏监控与线程资源治理实战

<!-- outline-start -->
## 要点

### 🔹 文件描述符（FD）泄漏的常见路径
- 未关闭的 FileInputStream / FileOutputStream / ParcelFileDescriptor
- Socket / ServerSocket 泄漏（尤其 NIO Selector 与非阻塞 IO）
- ContentProvider query 返回的 Cursor 未关闭
- MediaPlayer / Camera / SensorManager 的 native FD 释放链路
- SQLite WAL 模式下数据库连接的 FD 管理
- Android 17 中 `/proc/self/fd` 的限制与 art fd tracking

### 🔹 FD 泄漏的线上监控方案
- 周期性读取 `/proc/self/fdinfo/` 的 FD 状态快照
- 基于_IO_FILE 结构的 Native FD 引用追踪
- StrictMode.VmPolicy.Builder().detectLeakedClosableObjects() 的适用边界
- Android 17 FD guard（libfdtrack）的工作原理与定制化
- 监控方案对性能的影响评估：采样频率 vs 覆盖率

### 🔹 线程创建与匿名线程监控
- Thread.setDefaultUncaughtExceptionHandler 的链式责任模式
- pthread_create 监控：通过 PLT Hook 拦截 native 线程创建
- 匿名线程（无名称的 Thread / HandlerThread）的自动命名方案
- 线程优先级 (Process.setThreadPriority) 对调度的影响与最佳实践
- Android 17 Binder 线程池上限与线程饥饿的关联

### 🔹 线程泄漏与资源耗尽
- Inner class / 匿名内部类导致的 Activity/Fragment 线程泄漏
- RxJava / Coroutine 的 dispose/cancel 机制与线程释放
- HandlerThread 的 quitSafely() 与消息队列清理
- ThreadPoolExecutor 的 shutdown 链路与线程存活检测
- ForkJoinPool / Coroutine DefaultDispatcher 的线程回收机制

### 🔹 线上资源治理体系
- 线程/FD/内存的联合监控面板设计
- 资源阈值的动态调整（低端机 vs 高端机）
- 灰度发布中的资源监控告警策略
- Crash 发生前的资源快照采集（ forensic snapshot）

### 🔹 案例分析
- 典型 FD 泄漏场景：Cursor 未关闭导致的 ANR
- 线程爆炸场景：第三方 SDK 的 ThreadPoolExecutor 配置失控
- Binder 线程耗尽场景：同步 Binder 调用阻塞主线程

## 扩展

### 🔸 Native FD 追踪进阶
- libfdtrack 的 hook 机制详解
- 基于 BPF 的 FD 生命周期追踪

### 🔸 Android 17 资源限制变化
- per-process FD 限制的调整（RLIMIT_NOFILE）
- cgroup v2 对线程资源的细粒度控制

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决"匿名"线程？.md]
[缺口来源: 全书 FD monitoring 仅 7 处提及，thread monitoring 12 处，实战覆盖不足]
