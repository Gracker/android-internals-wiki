---
title: "Binder Freezer 与缓存进程冻结性能"
chapter: "1.18"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [binder, process-freezer, cached-apps, cgroup, performance]
related_chapters: ["1.3", "1.4", "5.8", "11.2", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构/官方文档"
---

# 1.18 Binder Freezer 与缓存进程冻结性能

<!-- outline-start -->
## 要点

### 🔹 缓存进程冻结解决的问题
说明 Android 为什么在 LMK 之外引入 cached app freezer：降低 cached 进程空转 CPU、减少后台异常唤醒，并保持比杀进程更低的恢复成本。

### 🔹 CachedAppOptimizer 的冻结入口
梳理 `OomAdjuster`、`ProcessList.FREEZER_CUTOFF_ADJ` 与 `CachedAppOptimizer` 的协作边界，区分 oom_adj 计算、冻结资格判断和实际冻结执行。

### 🔹 cgroup v2 freezer 状态机
解释 `cgroup.freeze`、`CGRP_FREEZE`、`CGRP_FROZEN`、`JOBCTL_TRAP_FREEZE` 与任务调度状态之间的关系，说明冻结态线程为什么不消耗 CPU。

### 🔹 Binder Freezer 的跨进程调用边界
整理 Binder 驱动如何感知 frozen 目标进程、同步/异步事务在冻结态下的差异，以及哪些调用会形成等待、失败或延迟投递。

### 🔹 Perfetto 与线上指标中的可观测特征
总结冻结进程在 Perfetto sched 轨道、CPU 频率、Binder latency、ANR 归因和 ApplicationExitInfo 中的可观测信号。

### 🔹 版本演进与调试入口
按 Android 12-17 梳理 cached app freezer、cgroup v2 freezer、Binder freezer API 与退出原因枚举的版本边界，给出 `dumpsys activity processes`、`cmd activity`、`/sys/fs/cgroup` 的排查入口。

## 扩展

### 🔸 前台服务、广播与 JobScheduler 的冻结豁免边界
后续可补齐不同组件状态对冻结资格的影响，避免把后台限制、cached freezer 和 Doze 混成一类机制。

### 🔸 厂商后台管控与 AOSP freezer 的差异
后续可收集 OEM 实机 trace，对比标准 AOSP freezer 与厂商自研冻结/墓碑/保活策略的差异。

### 🔸 冻结态 Binder 等待与 ANR 风险案例
后续可补一个最小复现实验：调用 cached 目标进程 Binder 服务，观察等待时间、解冻时机和 trace 证据。

<!-- outline-end -->

> 本节内容待加工。
