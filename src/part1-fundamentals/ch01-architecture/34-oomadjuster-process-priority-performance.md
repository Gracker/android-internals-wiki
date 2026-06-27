---
title: "OomAdjuster 与进程优先级计算"
chapter: "1.34"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [oom, oom_adj, process_priority, lmk, freezer, AMS]
related_chapters: ["4.4", "1.3", "5.8", "4.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/章节深挖"
---

# 1.34 OomAdjuster 与进程优先级计算

<!-- outline-start -->
## 要点

### 🔹 oom_adj 分级体系
从 NATIVE_ADJ(-17) 到 CACHED_APP_MIN_ADJ(900) 的完整 adj 等级；每个等级的语义和对进程命运的影响；adj 数值与 LMK 杀进程顺序的关系。

### 🔹 computeOomAdjLSP 核心算法
OomAdjuster.computeOomAdjLSP 的计算流程；输入因子（进程状态、组件可见性、前台/后台、Service 连接、ContentProvider 观察、Activity 栈位置）；输出三元组（adj, schedGroup, state）。

### 🔹 进程状态（ProcessState）与调度组（ScheduleGroup）
PROCESS_STATE_PERSISTENT 到 PROCESS_STATE_CACHED_EMPTY 的完整状态枚举；SP_DEFAULT/SP_FOREGROUND/SP_TOP 等 schedGroup 与 CFS 调度优先级的关系。

### 🔹 OomAdjuster 触发时机
什么操作会触发 re-evaluate：组件生命周期变化、Service bind/unbind、Activity resume/pause、Provider 访问；系统定时 re-evaluate 的周期和触发路径。

### 🔹 Android 17 OomAdjuster 变更
Android 17 对 cached app adj 的收紧；与 Freezer 的联动（frozen 进程的 adj 维持策略）；内存压力下的动态 adj 提升（PSI 集成）。

### 🔹 OomAdjuster 性能开销
system_server 中 OomAdjuster 的锁竞争（mPidsLock, mOomAdjLock）；批量 re-evaluate 的优化策略；多核并行计算的尝试。

### 🔹 实战：通过 dumpsys 和 trace 观察进程优先级
`adb shell dumpsys activity processes` 输出解读；Perfetto 中 oom_adj 的变化轨道；进程 adj 变化与性能退化（CPU 限频、冻结、杀）的因果关系。

## 扩展

### 🔸 App Standby Bucket 与 OomAdjuster 的交互
App Standby 的 restricted/active 状态如何影响 adj 计算。

### 🔸 OEM 自定义 adj 优先级（VIP 进程）
OEM 如何通过 override 调整特定进程的 adj（如通信链路进程、桌面进程）。

<!-- outline-end -->

> 本节内容待加工。
