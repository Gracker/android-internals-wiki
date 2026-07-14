---
title: "Android 17 内核 EEVDF 调度器：从 CFS 到 Earliest Eligible Virtual Deadline First"
chapter: "5.31"
status: "draft"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [EEVDF, CFS, Linux内核, CPU调度, sched, kernel6.10, 虚拟截止时间]
related_chapters: [5.1, 5.2, 5.3, 5.28]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
---
# 5.31 Android 17 内核 EEVDF 调度器：从 CFS 到 Earliest Eligible Virtual Deadline First

<!-- outline-start -->
## 要点

### 🔹 EEVDF 核心算法：eligibility 与 virtual deadline 计算
{基于缺口分析生成的锚点内容}

### 🔹 Linux 6.10 调度器替换：CFS → EEVDF 的变更全景与 AOSP kernel 适配
{基于缺口分析生成的锚点内容}

### 🔹 与 EAS/PELT 的协作：EEVDF 在大小核架构下的能效表现
{基于缺口分析生成的锚点内容}

### 🔹 uclamp 与 EEVDF：用户空间.clamp_hint 对 deadline/eligibility 的影响
{基于缺口分析生成的锚点内容}

### 🔹 sched_ext 框架：Android 17 对 BPF 可编程调度器的支持边界
{基于缺口分析生成的锚点内容}

### 🔹 对应用性能的实际影响：帧调度、后台任务排队、前台交互优先级
{基于缺口分析生成的锚点内容}

## 扩展

### 🔸 EEVDF 与游戏高性能场景：ADPF Hint Session 与 deadline 联动
{可选深入方向}

### 🔸 OEM 自定义调度策略在 EEVDF 时代的适配路径
{可选深入方向}

<!-- outline-end -->

> 本节内容待加工。
