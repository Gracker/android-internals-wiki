---
title: "ANR Kernel Trace 联合诊断与系统事件关联"
chapter: "9.8"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [anr, ftrace, kernel-trace, atrace, perfetto, diagnosis, system-events]
related_chapters: ["9.3", "9.5", "13.9", "26.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "研究素材/每日信息/AOSP结构"
gap_score:
  素材丰富度: 3
  与全书目标相关性: 5
  读者需求度: 5
  时效性: 4
  total: 17
sources:
  - type: research
    path: "DeepResearch/2026-06-03-anr-monitoring-ftrace.md"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Trace.java"
  - type: aosp
    path: "system/core/libapp_fatal/"
---

# 9.8 ANR Kernel Trace 联合诊断与系统事件关联

<!-- outline-start -->
## 要点

ANR 的诊断传统上依赖 SIGQUIT 信号触发的 Java 堆栈 dump（/data/anr/ 目录下的 trace 文件），但 Java 堆栈只能看到应用层的阻塞，无法直接观测内核态行为、Binder 驱动层排队、CPU 调度延迟、I/O 阻塞等系统级因素。Kernel Trace（ftrace/atrace）与 Perfetto 的联合使用，把 ANR 诊断从"看堆栈猜原因"推进到"端到端时序关联定位"。

### 🔹 锚点 1：ANR 堆栈 dump 的信息边界

Java 堆栈 dump 的覆盖范围：只能看到 Java 层调用栈，无法穿透 JNI 进入 native/kernel 层。/data/anr/ trace 文件包含的信息类型（线程状态、held locks、Binder 状态）及其局限性。 BlockedDetector → AnrHelper → StackTracesDumpHelper 的 Android 17 调用链。堆栈 dump 触发本身引入的延迟（dump 过程可能影响系统性能）。

### 🔹 锚点 2：ATrace/Ftrace 基础设施与 ANR 可见性

Android trace 基础设施的分层架构：Java 层 Trace.beginSection → nativeTraceBegin → /sys/kernel/tracing/trace_marker。ftrace buffer 与 atrace 的关系。ANR 相关的 atrace tag：`am`（ActivityManager）、`binder_driver`、`sched`、`freq`、`block`。这些 tag 在 Perfetto 中的对应 track。

### 🔹 锚点 3：Perfetto 端到端 ANR 诊断流程

用 Perfetto 代替 /data/anr/ trace 做端到端 ANR 分析的完整流程：抓取配置（需要的 atrace tag + ftrace events）、时间线对齐（ANR 触发时间点定位）、多 track 关联（主线程调度状态 + Binder 调用 + CPU 频率 + I/O 等待）。如何识别"ANR 根因在系统侧"而非"应用主线程阻塞"。

### 🔹 锚点 4：Binder 驱动层 ANR 诊断

Binder transaction 的 ftrace 可见性：`binder: binder_transaction`、`binder_lock` 等 tracepoint。当 ANR 由 Binder 同步调用阻塞引起时，如何在 Perfetto 中追踪阻塞的 Binder transaction（从应用线程 → binder_driver → 对端服务线程）。区分"对端慢"和"Binder 驱动层排队"。

### 🔹 锚点 5：CPU 调度延迟与 ANR 关联

主线程被抢占/调度延迟导致的 ANR：如何在 Perfetto 中识别（sched track 中的 sleep/wake 状态切换、CPU running 时间占比）。D-state（不可中断睡眠）与 I/O 阻塞的关联。`sched_blocked_reason` ftrace event 的使用。

### 🔹 锚点 6：I/O 阻塞 ANR 的 Kernel Trace 定位

主线程在 I/O 操作上的阻塞（如 SharedPreference 写入、数据库查询）如何通过 ftrace 的 `block` tag 和 `io_uring`/`block_rq_issue` 事件定位。从 Java 层 I/O 调用到内核 block 层的完整追踪路径。区分"磁盘慢"和"锁竞争导致 I/O 排队"。

### 🔹 锚点 7：Android 17 ANR 监控增强

Android 17 在 ANR 监控方面的系统级增强：AnrHelper/ProcessErrorStateRecord 的更新、与 ftrace 的协同改进。ProfilingManager 提供的 ANR 相关 trigger 能力。

## 扩展

### 🔸 扩展点 1：eBPF 辅助 ANR 实时诊断

eBPF 程序挂载到 sched_switch、binder_transaction 等 tracepoint，实现零开销的 ANR 相关事件实时采集。与 Perfetto 的离线分析互补。

### 🔸 扩展点 2：自动化 ANR 根因分类

基于 Kernel Trace 数据的自动化 ANR 根因分类框架：将 Binder 阻塞、CPU 调度延迟、I/O 阻塞、GC 停顿等模式自动识别。输出分类报告。

### 🔸 扩展点 3：生产环境 Kernel Trace 采集策略

生产环境中 Kernel Trace 的性能开销评估和采样策略：哪些 ftrace event 可以持续开启，哪些只能按需触发。与线上 APM 系统的集成方案。

<!-- outline-end -->

> 本节内容待加工。

[结构参考: DeepResearch/2026-06-03-anr-monitoring-ftrace.md]
