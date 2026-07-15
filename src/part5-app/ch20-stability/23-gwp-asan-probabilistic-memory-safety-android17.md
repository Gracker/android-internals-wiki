---
title: "GWP-ASan 灰度检测演进与 Android 17 内存安全防线"
chapter: "20.23"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['gwp-asan', 'memory-safety', 'use-after-free', 'heap-overflow', 'scudo', 'android17']
related_chapters: ['20.11', '4.9']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "research-gaps + AOSP结构"
gap_score: "15/20"
---

# 20.23 GWP-ASan 灰度检测演进与 Android 17 内存安全防线

<!-- outline-start -->
## 要点

### 🔹 GWP-ASan 设计哲学：概率性堆内存安全检测
Google Wide-Process ASan 的采样检测原理、与 Scudo Hardened Allocator 的集成关系、生产环境零开销特性。

### 🔹 Android 17 中 GWP-ASan 配置与激活策略
bionic libc 中 GWP-ASan 的初始化路径、系统属性配置（gwp_asan.*）、进程级启用/禁用机制、Android 17 新增的调优参数。

### 🔹 检测能力：Use-After-Free / Heap-Buffer-Overflow / Double-Free
每类内存错误的检测原理、GWP-ASan 的 Guard Region 布局、采样命中概率与进程内存压力的关系。

### 🔹 GWP-ASan 与其他内存安全机制的协同
GWP-ASan × MTE (Memory Tagging Extension) × HWASan × Scudo 的互补关系与组合策略、ARMv9 硬件支持的影响。

### 🔹 线上灰度部署策略与效果度量
GWP-ASan 在 Google Play 应用中的灰度比例、检测到的内存错误分布、对崩溃率的量化影响。

## 扩展

### 🔸 GWP-ASan crash 报告解析与栈回溯
GWP-ASan 触发的 SIGSEGV 信号处理路径、tombstone 中的 GWP-ASan 特有信息、与 debuggerd 的协作。

### 🔸 从 GWP-ASan 发现到修复的工作流
检测 → 分类 → 优先级排序 → 修复 → 回归验证的完整流程、与 crash aggregation 系统的集成。

<!-- outline-end -->

> 本节内容待加工。
