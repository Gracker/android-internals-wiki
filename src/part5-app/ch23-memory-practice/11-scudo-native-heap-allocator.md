---
title: "Scudo 分配器与 Native Heap 性能边界"
chapter: "23.11"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [native-memory, scudo, allocator, heapprofd, gwp-asan]
related_chapters: ["4.5", "14.3", "20.11", "23.3", "26.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "素材驱动/官方文档/Clippings结构参考"
source_refs:
  - "[结构参考: Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md]"
  - "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - "[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md]"
  - "https://source.android.com/docs/security/test/scudo"
  - "https://source.android.com/docs/core/tests/debug/native-memory"
  - "https://developer.android.com/studio/profile/record-native-allocations"
  - "https://developer.android.com/ndk/guides/gwp-asan"
---

# 23.11 Scudo 分配器与 Native Heap 性能边界

<!-- outline-start -->
## 要点

### 🔹 Native Heap 不只是一条“malloc 增长曲线”
区分 `malloc` / `calloc` / `realloc` / `mmap`、Bitmap 像素、线程栈、映射文件和图形缓冲区在 `dumpsys meminfo`、`smaps`、heapprofd 中的归类差异，避免把所有 Native 内存增长都归因到同一个分配器路径。

### 🔹 Scudo 在 Android Native 分配链路中的位置
梳理 bionic libc 分配入口、Scudo 用户态分配器、GWP-ASan 抽样诊断、MTE heap tagging 之间的职责边界，说明哪些能力来自 allocator，哪些能力来自硬件或调试工具。

### 🔹 安全检查与性能成本的取舍
整理 quarantine、chunk metadata、随机化、tagging、recoverable GWP-ASan 等机制对 CPU、内存碎片和 RSS 的影响，重点解释生产环境能开启什么，调试环境才应该开启什么。

### 🔹 Native 内存异常的观测路径
建立从 `dumpsys meminfo` / `showmap` / `smaps` 到 Android Studio Native Allocations、Perfetto heapprofd、malloc debug、libmemunreachable 的排查顺序，说明每个工具能回答的问题和权限前提。

### 🔹 16KB Page、MTE 与 allocator 行为的交叉影响
补齐 16KB Page Size、MTE ASYNC/SYNC、Scudo 分配粒度与 Bitmap / so / JNI Native 分配之间的版本边界，避免把页大小变化直接写成某个库的确定收益或损耗。

### 🔹 线上治理指标与降级策略
定义 Native Heap 的线上指标：PSS/RSS、`Native Heap Alloc`、分配速率、峰值回落、异常栈样本、进程退出归因；给出采样、告警、灰度和回滚策略。

## 扩展

### 🔸 malloc debug、heapprofd 与 Android Studio Native Allocations 的对照表
按可用版本、是否需要 debuggable/profileable、能否采样线上用户、是否能还原调用栈、运行开销整理工具边界。

### 🔸 Scudo / GWP-ASan / MTE 在 Native Crash 治理中的分工
与 20.11 节交叉引用，只保留实践判断，不重复展开 MTE 原理。

### 🔸 三方 so 的 Native 内存治理
记录不能修改源码时的处理方式：版本替换、灰度隔离、调用路径限流、进程隔离、符号表与 tombstone 归因。

<!-- outline-end -->

> 本节内容待加工。
