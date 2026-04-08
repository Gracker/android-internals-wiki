---
title: "Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理"
chapter: "13.9"
section: "13.9"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [tracing, atrace, ftrace, tracepoint, perfetto, kernel, observability]
related_chapters: ["13.1", "13.2", "13.7", "14.10", "1.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "AOSP结构+章节深挖"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/cmds/atrace/"
  - type: aosp
    path: "system/traced/"
  - type: official
    path: "https://source.android.com/docs/core/debug/atrace"
  - type: kernel
    path: "kernel/trace/"
---

# 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么要理解 Tracing 基础设施
- 全书大量使用 Perfetto 分析性能问题，但从未解释数据从哪里来
- 理解底层机制才能自定义追踪点、诊断追踪数据缺失问题
- 对系统/OEM 开发者：添加自定义 tracepoint 是日常工作

### 🔹 锚点 2：Linux 内核 ftrace 框架
- ftrace 是 Linux 内核的函数追踪框架，是 Android tracing 的底层数据源
- function tracer / function_graph tracer / tracepoint 三种模式
- tracefs 文件系统接口（/sys/kernel/tracing/）
- 与 Perfetto 的关系：Perfetto 通过 ftrace 收集内核事件（sched/cpu_freq/binder 等）

### 🔹 锚点 3：内核 Tracepoint 机制
- 静态 tracepoint：编译时插入的探测点（TRACE_EVENT 宏）
- Android 常用 tracepoint 分类：sched（调度）、power（功耗）、binder（IPC）、block（I/O）、net（网络）
- 如何在内核模块中添加自定义 tracepoint
- tracepoint 与 eBPF 的关系（kprobe/uprobe 作为动态替代）

### 🔹 锚点 4：atrace 用户空间追踪框架
- atrace 是 Android 对 ftrace 的封装，提供分类开关（--atrace-categories）
- atrace 分类与 ftrace event 的映射关系（如 sched → sched_switch, sched_wakeup）
- 用户空间 atrace tag（Trace.beginSection/Trace.endSection）的底层实现
- atrace 在 Android 启动过程中的角色（boot trace）

### 🔹 锚点 5：Perfetto traced 守护进程与数据流
- traced（Perfetto daemon）的架构：traced_producer + traced_consumer + service
- traced 如何通过 ftrace 收集内核事件（/sys/kernel/tracing/）
- 用户空间 producer：如何注册自定义 data source
- Perfetto TraceConfig 中 ftrace 配置的底层含义（ftrace_events / ftrace_drain_period_ms）

### 🔹 锚点 6：自定义 Tracing 实战
- App 层：android.os.Trace（beginSection/endSection）和 androidx.tracing
- Framework 层：ATRACE_CALL/ATRACE_BEGIN 宏的使用
- Native 层：libcutils Trace.h
- 内核层：添加自定义 tracepoint 的完整步骤
- 在 Perfetto 中查看自定义追踪数据

### 🔹 锚点 7：Tracing 开销与性能影响
- 不同追踪模式的开销对比：function tracer > tracepoint > userspace tag
- ftrace buffer 大小与数据丢失的权衡
- 高频 tracepoint 对系统性能的影响（量化数据）
- 生产环境中使用 tracing 的最佳实践

## 扩展

### 🔸 扩展点 1：Perfetto SQL 与 ftrace event 的映射
- 如何从 SQL 查询结果反推到底层 ftrace event
- 常用 SQL 查询与对应 ftrace event 的对照表

### 🔸 扩展点 2：eBPF 与传统 tracepoint 的对比
- eBPF kprobe/uprobe 作为动态 tracepoint 的替代
- 性能开销对比（eBPF vs ftrace tracepoint）
- sched_ext 的 tracing 能力

### 🔸 扩展点 3：OEM 自定义 Tracing 方案
- 联发科/高通的厂商扩展 tracepoint
- 如何在不修改 AOSP 的情况下添加 OEM 特有的追踪数据
- Vendor tracepoint 的标准化挑战

<!-- outline-end -->

> 本节内容待加工。
