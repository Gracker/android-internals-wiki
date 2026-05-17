---
title: "Android Studio LeakCanary Profiler 与堆转储分析"
chapter: "14.14"
status: draft
applicable_versions: "Android Studio Panda 2025.3.1+ / Android 8.0 (API 26) - Android 17 (API 37)"
tags: [android-studio, profiler, leakcanary, memory, hprof]
related_chapters: ["10.2", "14.1", "14.3", "19.5", "23.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "官方文档/每日信息/素材驱动"
---

# 14.14 Android Studio LeakCanary Profiler 与堆转储分析

<!-- outline-start -->
## 要点

### 🔹 LeakCanary Profiler task 的定位
说明 Android Studio Panda 将 LeakCanary 分析接入 Profiler 后，工具链从「App 内通知 + 设备端分析」变成「IDE 内任务 + 源码上下文」的使用方式。

### 🔹 HPROF 采集、导出与对象保留路径
梳理 Memory Profiler 捕获 heap dump 的入口、Activity / Fragment leak 过滤、GC root 距离、retained object 链路等分析字段。

### 🔹 设备端与开发机端分析边界
区分 LeakCanary 运行时检测、Android Studio 离线分析、生产环境 APM 上报三类场景，说明各自适合解决的问题。

### 🔹 Java / Kotlin 堆泄漏与 Native 内存问题的分工
明确 HPROF 主要覆盖托管堆对象，Native allocation、malloc debug、heapprofd、Perfetto 需要走另一套证据链。

### 🔹 与现有 LeakCanary 接入方案的取舍
对比库内置 UI、CI 复现、IDE Profiler task、线上监控 SDK，给出开发期和回归期的选择建议。

### 🔹 实战排查流程
按「复现 → 抓取 heap dump → 定位 retained path → 回到源码 → 修复 → 再抓取验证」组织最小闭环。

## 扩展

### 🔸 Android Studio Panda 版本边界
跟踪 Panda 稳定版、预览版功能差异，以及 LeakCanary task 对 AGP、JDK、设备 API 的最低要求。

### 🔸 标准泄漏样例库
整理 Activity、Fragment、匿名内部类、协程、监听器、WebView、Bitmap cache 等常见泄漏复现场景。

### 🔸 Native 内存诊断联动
补充 heapprofd、malloc debug、native allocation tab 与 Perfetto 的联动路径。

<!-- outline-end -->

> 本节内容待加工。
