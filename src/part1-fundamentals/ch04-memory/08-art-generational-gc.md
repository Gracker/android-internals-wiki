---
title: "ART 分代垃圾回收与 GC 暂停优化"
chapter: "4.8"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['ART', 'GC', 'generational-gc', 'Android-17', 'jank']
related_chapters: ['4.3', '1.7', '7.2']
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档（Android 17 行为变更）+ AOSP 源码分析"
---

# 4.8 ART 分代垃圾回收与 GC 暂停优化

<!-- outline-start -->
## 要点

### 🔹 GC 暂停为什么影响流畅性
GC pause 导致的主线程停顿在 Perfetto 中的表现；GC 频率与帧丢弃的因果关系
### 🔹 ART GC 的演进：从 Concurrent Mark-Sweep 到 Generational
Android 14 之前的 GC 策略回顾；分代假说（Generational Hypothesis）在 ART 中的应用动机
### 🔹 Android 17 Generational GC 的实现
Young/Old 分代策略；Write Barrier 的实现与性能开销；Card Table 与 Remembered Set
### 🔹 GC 对应用性能的实际影响
不同分配模式下的 GC 频率与暂停时间；内存抖动（Memory Churn）如何触发频繁 GC
### 🔹 在 Perfetto 中分析 GC 行为
ART GC Track 的解读；GC pause 的 SQL 查询；GC 与 doFrame 的时间冲突分析
### 🔹 App 端的 GC 优化策略
减少对象分配、对象池模式、避免 finalize()；与 4.3 ART 内存管理的联动

## 扩展

### 🔸 GC 调优参数与兼容性
通过系统属性调整 GC 行为的可行性；不同 OEM 对 ART GC 的定制
### 🔸 Compose 对 GC 压力的特殊影响
Compose recomposition 的临时对象分配模式与 GC 压力的关系

<!-- outline-end -->

> 本节内容待加工。
