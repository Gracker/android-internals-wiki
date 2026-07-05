---
title: "ART HeapTask 调度管线与 Android 17 新增子类"
chapter: "4.21"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [ART, GC, HeapTask, TaskProcessor, GC抑制, 启动性能, 内存管理]
related_chapters: ["4.8", "4.9", "4.11", "4.14", "4.16", "21.13", "23.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "研究素材"
sources:
  - type: aosp
    path: "art/runtime/gc/task_processor.cc (android-17.0.0_r1)"
  - type: aosp
    path: "art/runtime/gc/heap_task.h (android-17.0.0_r1)"
  - type: aosp
    path: "libcore/libart/src/main/java/java/lang/Daemons.java (android-17.0.0_r1)"
  - type: deepresearch
    path: "DeepResearch/2026-07-05-android17-art-heaptask-system-7-subclasses-source-closed-loop.md"
---

# 4.21 ART HeapTask 调度管线与 Android 17 新增子类

<!-- outline-start -->
## 要点

### 🔹 四层任务管线架构
HeapTaskDaemon(Java) → VMRuntime.runHeapTasks()(JNI) → TaskProcessor::RunAllTasks()(Native) → HeapTask::Run()/Finalize()。Android 17 中 C++ 侧类名从 `HeapTaskDaemon` 重构为 `TaskProcessor`（文件 `heap_task_daemon.cc` → `task_processor.cc`）。

### 🔹 7 种 HeapTask 子类（Android 17 新增 2 种）
ConcurrentGCTask、CollectorTransitionTask、HeapTrimTask、ClearedReferenceTask、StartupCompletedTask（已有 5 种）+ **TriggerPostForkCCGcTask**（新增）、**ReduceTargetFootprintTask**（新增）。新增子类服务于 zygote fork 后的延迟收缩和后置 GC 触发。

### 🔹 优先队列调度模型
Android 17 将任务队列从 FIFO 重写为 `std::multiset<HeapTask*, CompareByTargetRunTime>` 按 `target_run_time_` 排序，`GetTask` 通过 `CondVar::TimedWait(target_run_time)` 精确等待。`UpdateTargetRunTime` 可动态重新排序。

### 🔹 PostForkChildAction 与启动 GC 窗口
Zygote fork 后 `PostForkChildAction` 主动 enqueue `ReduceTargetFootprintTask`/`TriggerPostForkCCGcTask`，阻塞会导致启动垃圾无法回收，引发 ANR 或 OOM。`kPostForkMaxHeapDurationMS` 窗口分析。

### 🔹 GC 抑制在 Android 17 的风险升级
Native hook 阻塞 HeapTaskDaemon / 篡改 task_processor 指针在 Android 17 仍技术上可行，但新增的 PostFork 任务让风险显著升高。抑制窗口与启动关键路径重叠时的故障模式分析。

### 🔹 Perfetto 可观测性
HeapTaskDaemon 线程名在 trace 中保持不变，可按名字定位。TaskProcessor 的 `target_run_time_` 等待、各子类的执行时间可通过 atrace/perfetto 追踪。

## 扩展

### 🔸 GC 抑制方案的替代策略
不阻塞 HeapTaskDaemon 而通过调整 GC 阈值/并发比的低风险方案，对比 §21.13 中的抑制技术。

### 🔸 TaskProcessor 与 Cached App Freezer 的交互
App 冻结/解冻时 TaskProcessor 的行为，与 §4.11 的交叉分析。

### 🔸 跨版本 HeapTask 演进
从 Android 8（5 种子类 + FIFO）到 Android 17（7 种子类 + 优先队列）的完整演进历史。

<!-- outline-end -->

> 本节内容待加工。

[来源: DeepResearch/2026-07-05-android17-art-heaptask-system-7-subclasses-source-closed-loop.md]
[结构参考: AOSP android-17.0.0_r1, art/runtime/gc/task_processor.cc]
