---
title: "Android 17 App Memory Limits 与内存泄漏治理"
chapter: "23.9"
status: draft
applicable_versions: "Android 17 (API 37)+; Android Studio Panda 1+"
tags: [android17, memory-limits, memory-leak, applicationexitinfo, profilingmanager, leakcanary]
related_chapters: ["10.2", "20.5", "23.1", "26.9", "26.12", "14.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/每日信息/章节深挖/Clippings结构参考"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture"
  - type: local
    path: "intake/daily-info/2026-05-19.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md"
---

# 23.9 Android 17 App Memory Limits 与内存泄漏治理

<!-- outline-start -->
## 要点

### 🔹 Android 17 App Memory Limits 的边界
说明该限制按设备总 RAM 建立应用内存上限，面向所有运行在 Android 17 上的应用；区分系统级极端内存泄漏限制、LMKD 压力杀进程、Java Heap OOM 与 Native/匿名页膨胀。

### 🔹 MemoryLimiter:AnonSwap 的退出归因
围绕 `ApplicationExitInfo.getDescription()`、`REASON_OTHER` 与 `MemoryLimiter:AnonSwap` 字符串建立线上归因路径，说明它能回答的问题和不能单独证明的原因。

### 🔹 TRIGGER_TYPE_ANOMALY 与触发式堆转储
梳理 `ProfilingManager` 触发式采集在内存上限命中时的使用方式，说明 heap dump、trace、隐私与采样成本的工程边界。

### 🔹 Android Studio Panda LeakCanary Profiler 工作流
整理 IDE 内置 LeakCanary task 的适用场景：本地泄漏复现、源码定位、和线上退出归因互补；避免把开发期泄漏检测当成线上监控替代。

### 🔹 内存基线与灰度门禁
定义版本发布前后的 PSS/RSS/Java Heap/Native Heap/Anon Swap 基线，给出按设备 RAM 档位、页面场景和长驻时长拆分的观测维度。

### 🔹 与 OOM 治理、稳定性治理的交叉
把本节定位为 Android 17 行为变更下的实战补充：详见 20.5 OOM 治理、23.1 内存泄漏检测与治理、26.9 ApplicationExitInfo 与进程退出归因。

## 扩展

### 🔸 AOSP MemoryLimiter 源码路径
追踪 Android 17 中 MemoryLimiter 与进程退出记录的具体实现路径，补齐 ActivityManager / ProcessRecord / ApplicationExitInfo 的调用链。

### 🔸 设备 RAM 档位与阈值策略
整理低内存设备、主流旗舰、平板/桌面窗口化场景下限制命中的差异，避免给出无设备条件的固定阈值。

### 🔸 线上告警与隐私合规
补充 heap dump 采集的用户授权、数据脱敏、上传策略和采样率控制。

<!-- outline-end -->

> 本节内容待加工。
