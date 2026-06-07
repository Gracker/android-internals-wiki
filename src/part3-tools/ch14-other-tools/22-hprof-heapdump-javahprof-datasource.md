---
title: "HPROF Heap Dump 管线与 Perfetto java_hprof 数据源"
chapter: "14.22"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [hprof, heap-dump, art, perfetto, java_hprof, memory-analysis]
related_chapters: ["10.1", "10.2", "14.3", "14.14", "19.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "素材驱动/DeepResearch/AOSP结构"
---

# 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源

<!-- outline-start -->
## 要点

### 🔹 HPROF Heap Dump 三层调用栈
Android 的 HPROF 堆转储形成三层调用栈：`am dumpheap` shell 命令 → AMS 层（`dumpHeap`）→ ActivityThread 层（`handleDumpHeap`）→ ART 层（`DumpHeap` → `Hprof::Dump`）。每一层有明确的权限检查和保护机制。

### 🔹 Shell 命令层：am dumpheap 参数
`am dumpheap` 支持 `-n`（非托管 dump）、`-g`（执行 GC）、`-m`（导出 malloc 信息）、`-b`（导出位图）。不同参数组合影响 dump 的内容范围和耗时。

### 🔹 AMS 层：权限与 Freezer 保护
AMS 的 `dumpHeap` 需要高危权限 `SET_ACTIVITY_WATCHER`（level 1000）。关键保护机制：调用 `enableFreezer(false)` 防止 Cached App Freezer 干扰堆 dump 过程。通过 `IApplicationThread.dumpHeap()` 异步执行。

### 🔹 ART 层：双重保护机制
ART 实现使用 `gc::ScopedGCCriticalSection` 和 `ScopedSuspendAll` 双重保护确保堆稳定性。输出兼容标准 JAVA PROFILE 1.0.3 格式的 hprof 文件。理解这个保护机制对分析 dump 过程中的性能影响至关重要。

### 🔹 Perfetto java_hprof 数据源
Android 17 新增 `art_hprof` 数据源，通过 `ArtHprofParser` 解析 HPROF 文件转换为结构化堆图数据。支持连续导出和选择性过滤，实现从原生堆 dump 到火焰图可视化的完整链路。

### 🔹 HPROF 文件格式与解析
标准 JAVA PROFILE 1.0.3 格式的关键结构：header、record 类型、heap dump segment、heap dump end。Android 对标准格式的扩展（如 app 自然堆 vs zygote 堆的区分）。

### 🔹 实战：Heap Dump 的性能影响
heap dump 过程对应用性能的影响：ART 暂停所有线程、GC critical section 持续时间、dump 文件大小与内存压力。如何在生产环境安全使用（KOOM fork-dump 方案 vs 系统 dumpheap）。

## 扩展

### 🔸 Perfetto heap_graph 表与 SQL 分析
如何使用 Perfetto 的 `heap_graph` 系列表进行堆分析：对象统计、Retained Size 计算、GC Root 追踪。

### 🔸 KOOM fork-dump 机制
快手 KOOM 通过 fork 子进程 dump heap，避免主进程暂停。其实现原理与系统 dumpheap 的对比。

<!-- outline-end -->

> 本节内容待加工。
