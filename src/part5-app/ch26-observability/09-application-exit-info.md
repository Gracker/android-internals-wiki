---
title: "ApplicationExitInfo 与进程退出归因"
chapter: "26.9"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["applicationexitinfo", "observability", "crash", "anr", "oom"]
related_chapters: ["20.3", "20.4", "20.5", "19.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/官方文档"
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-08-applicationexitinfo-android11-below-alternatives.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-09-application-exit-info-android11-alternatives.md"
  - type: clippings
    path: "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
---

# 26.9 ApplicationExitInfo 与进程退出归因

<!-- outline-start -->
## 要点

### 🔹 进程退出归因的观测目标
- crash、native crash、ANR、LMK、用户终止的区分
- 一次退出记录需要保留的字段
- 与 Crash / ANR / OOM 上报的关系

### 🔹 API 30+ 的 ApplicationExitInfo
- getHistoricalProcessExitReasons() 的调用方式
- reason、importance、timestamp、traceInputStream 的含义
- 系统保留数量和历史记录边界

### 🔹 ANR 与 native crash 的现场拼接
- ANR trace 的读取和上报
- native tombstone 与 REASON_CRASH_NATIVE
- 与 Play Console / Crashlytics 数据的差异

### 🔹 Android 11 以下的替代路径
- Signal Handler 自建 native crash 现场
- LMKd / dumpsys / /data/anr 的权限边界
- KOOM fork dump 等低版本保现场策略

### 🔹 端侧存储与上报设计
- 进程重启后读取上一轮退出原因
- 去重、采样和隐私过滤
- 与发版、设备、内存状态维度关联

### 🔹 误判与边界
- 多进程应用的归因错位
- 系统回收与用户杀进程的区分
- 不同厂商系统的记录完整性差异

## 扩展

### 🔸 退出原因与稳定性指标体系的映射
[待补充]

### 🔸 ApplicationExitInfo 与 GWP-ASan / MTE 报告拼接
[待补充]

### 🔸 低版本可观测性能力矩阵
[待补充]

<!-- outline-end -->

> 本节内容待加工。
