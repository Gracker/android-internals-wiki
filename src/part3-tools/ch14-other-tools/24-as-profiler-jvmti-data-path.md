---
title: "Android Studio Memory Profiler JVMTI 数据通路源码分析"
chapter: "14.24"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [MemoryProfiler, JVMTI, perfa, AndroidStudio, profiler-internals, allocation-tracking]
related_chapters: ["14.1", "14.3", "14.14", "14.22", "13.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "素材驱动"
score: 15
score_breakdown: "素材丰富度5 + 相关性4 + 读者需求3 + 时效性3"
source_material:
  - "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-25-as-memory-profiler-jvmti-source.md"
---

# 14.24 Android Studio Memory Profiler JVMTI 数据通路源码分析

<!-- outline-start -->
## 要点

### 🔹 JVMTI 不是 Android 8.0 引入：标准接口与实际差异
- JVMTI (JVM Tool Interface) 是 JSR-163 标准，随 Java 5（2003）推出
- Android 8.0（API 26）真正的新增项：去除 DDMS HPROF 65535 条记录上限
- perfa agent 源码 Copyright 2017，随 Android Profiler GA 同步发布
- 精度提升来自 perfa 采样率改造（sampling_num_interval_），而非 JVMTI 演进

### 🔹 双进程架构：Studio 端 + device 端 perfa agent
- Studio（Kotlin/Java）通过 gRPC 与推送至 /data/local/tmp/perfd 的 daemon 通信
- perfd 使用 am attach-agent 把 libperfa.so 注入目标应用进程
- perfa 通过 jvmti.h AddCapabilities / SetEventCallbacks 注册事件回调
- 三类分配记录路径：alloc（legacy DDMS）/ heapprofd（native）/ JVMTI（默认 Java/Kotlin）

### 🔹 perfa JVMTI 事件注册与数据采集
- VMObjectAlloc：对象分配事件，通过 GetTag/SetTag 标记对象
- ObjectFree：对象释放事件，用于追踪 GC 回收
- GarbageCollectionStart/Finish：GC 起止事件
- ClassPrepare：类加载事件，用于类层次构建
- GetStackTrace：获取分配调用栈

### 🔹 数据精度与采样策略演进
- Legacy DDMS HPROF 协议的全局 65535 条记录限制
- perfa 2018 年起的采样率改造（sampling_num_interval_）
- 全量追踪 vs 采样的性能开销对比
- Leak Detection 的 Activity/Fragment 自动标记机制

### 🔹 JVMTI Memory Profiler vs Perfetto heapprofd
- JVMTI 覆盖 Java/Kotlin 堆分配，heapprofd 覆盖 native（malloc）分配
- 两者的性能开销差异：JVMTI 需 attach agent，heapprofd 通过 BPF/seccomp
- 数据粒度对比：JVMTI 全量事件 vs heapprofd 采样
- 何时选择哪个工具的组合策略

### 🔹 Android 17 Memory Profiler 的变化
- perfa agent 与 ART JVMTI 实现的版本兼容性
- Android 17 对 JVMTI 事件回调的性能优化
- 与 ProfilingManager / ProfilingTrigger 的协同关系

## 扩展

### 🔸 自定义 JVMTI agent 开发
- 使用 jvmti.h 开发自定义内存分析 agent
- attach-agent 机制的工作原理
- JVMTI agent 对 App 启动性能的影响

### 🔸 Memory Profiler 数据准确性验证
- 已知分配 vs Profiler 显示分配的偏差来源
- 短生命周期对象的漏报问题
- 多线程并发分配的栈追踪准确性

### 🔸 Perfetto java_hprof 数据源与 JVMTI 的关系
- Perfetto 不使用 JVMTI，而是直接读取 ART heap snapshot
- 两种数据源的互补关系（详见 §14.22）

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - ASM 与字节码插桩：改写字节码的"神器".md]
