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

## 审核说明

上面的 outline 是重复章节创建时留下的流水线记录，为避免破坏历史任务定位而原样保留。它不是 Android 17 的技术结论，不能据此新增实现。技术正文统一维护在 20.14，避免两个入口出现不同结论。

本入口沿用 20.14 的核查基线：平台源码为 Android 17 / API 37 / `android-17.0.0_r1`，涉及 `/proc` 的内核语义为 `android17-6.18-2026-06_r6`。主章节已经覆盖可验证的 FD 快照、创建归因、线程治理、资源关联和线上开关。

需要特别排除以下误读：

- 应用读取自身 `/proc/self/fd` 与 `/proc/self/fdinfo` 是常见诊断手段；不能笼统写成“Android 17 限制”，应以目标设备上的访问结果和错误码为准。
- `libfdtrack` 属于 Android 平台内部实现，不是 API 37 面向普通应用提供的 FD guard SDK。应用不能把链接或 Hook 它作为稳定方案。
- `_IO_FILE` 是特定 C 库的数据结构表达，无法覆盖 socket、epoll、eventfd、ashmem/memfd、Binder 驱动等全部 FD，也不是 Android 应用 FD 归因的统一入口。
- `Thread.setDefaultUncaughtExceptionHandler()` 只能接收未捕获异常，不能观察线程创建、存活或泄漏。
- PLT Hook 只能覆盖指定调用方经过动态重定位槽的 `pthread_create` 等调用；内部直接调用、内联、直接 syscall 和后装载 ELF 都要单独评估。
- eBPF 追踪依赖内核能力、SELinux、挂载与权限配置，不是普通未特权应用可默认启用的线上方案。
- `RLIMIT_NOFILE` 与 cgroup 配置属于设备和进程环境，不应宣称 Android 17 为所有应用统一调整了上限。采集时要记录 `getrlimit()` 的运行时结果。
- Binder 线程池耗尽、应用线程失控和 FD 耗尽可以互相放大，但三者没有固定因果关系，必须用线程栈、Binder 状态与 FD 快照按时间关联。

权威正文见 [20.14《线程与 FD 资源监控治理》](14-thread-fd-resource-monitoring.md)。本文件只保留历史路径，不再承载独立知识内容。
