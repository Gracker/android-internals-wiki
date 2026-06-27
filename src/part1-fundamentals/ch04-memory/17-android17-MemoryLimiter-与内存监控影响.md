---
title: "Android 17 MemoryLimiter 与内存监控影响"
chapter: "ch04.17"
status: draft
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: ['内存管理', 'MemoryLimiter', 'cgroup', '监控']
related_chapters: ['4.4', '4.15']
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "daily-info + research-gaps"
---

# ch04.17 Android 17 MemoryLimiter 与内存监控影响

<!-- outline-start -->
## 要点

### 🔹 MemoryLimiter 子系统架构与 Java 实现 ### 🔹 cgroup memory.high 限制机制与边界 ### 🔹 PSS 抖动与 30s kill 窗口影响分析 ### 🔹 Debug.MemoryInfo 指标缺失与补偿方案 ### 🔹 swap 指标在内存限制下的行为变化 ### 🔹 多层级内存保护策略协同机制 

## 扩展

### 🔸 MemoryLimiter 与 LMKD 的协同工作 ### 🔸 应用内存限制的在线动态调整 ### 🔸 内存限制场景下的性能优化 

<!-- outline-end -->

> 本节内容待加工。基于 daily-info 和 research-gaps 中的 Android 17 新特性分析。
