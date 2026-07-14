---
title: "Android 17 cgroup v2 统一层级与进程资源隔离机制"
chapter: "1.56"
status: "draft"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [cgroup, cgroup-v2, 资源限制, 进程隔离, CPU, 内存, 后台限制]
related_chapters: [1.3, 1.34, 5.8, 5.17]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
---
# 1.56 Android 17 cgroup v2 统一层级与进程资源隔离机制

<!-- outline-start -->
## 要点

### 🔹 cgroup v1 → v2 迁移：Android 统一层级架构与控制器挂载
{基于缺口分析生成的锚点内容}

### 🔹 libprocessgroup：AOSP 统一进程分组 API 的架构与演进
{基于缺口分析生成的锚点内容}

### 🔹 CPU 控制器（cpu/cpu.max/cpu.weight）：前后台 CPU 配额与优先级
{基于缺口分析生成的锚点内容}

### 🔹 内存控制器（memory.max/memory.low）：进程级内存限制与 OOM 保护
{基于缺口分析生成的锚点内容}

### 🔹 freezer 控制器：缓存进程冻结与 Binder Freezer 协作
{基于缺口分析生成的锚点内容}

### 🔹 schedtune → uclamp 迁移：cgroup v2 下的 CPU 性能提示
{基于缺口分析生成的锚点内容}

### 🔹 进程状态与 cgroup 映射：OomAdjuster procstate → cgroup 路径联动
{基于缺口分析生成的锚点内容}

## 扩展

### 🔸 cgroup v2 对 APM / 后台监控 SDK 的影响
{可选深入方向}

### 🔸 OEM 自定义 cgroup 策略与 AOSP 默认实现差异
{可选深入方向}

<!-- outline-end -->

> 本节内容待加工。
