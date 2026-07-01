---
title: "Android 17 eBPF 性能可观测性程序矩阵扩展"
chapter: "14.25"
status: draft
applicable_versions: "Android 17 (API 37)"
tags: [eBPF, observability, CPU-cycle, DMA-BUF, wakelock, lock-contention]
related_chapters: ["14.10", "14.21", "5.1", "5.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-02"
gap_source: "每日技术文章 intake"
---

# 14.25 Android 17 eBPF 性能可观测性程序矩阵扩展

<!-- outline-start -->
## 要点

### 🔹 cyclePerUid — 按 UID 统计 CPU 周期
Android 17 新增 cyclePerUid eBPF 程序，按 UID 维度统计 CPU 周期，比单进程维度更贴近 Android 应用和系统服务的资源归因。可用于能耗、性能和调度问题分析。[结构参考: daily-info/2026-07-01 技术文章 #27]

### 🔹 dmabufIter — DMA-BUF 迭代器
新增 dmabufIter eBPF 程序，围绕 DMA-BUF 做系统侧观测。DMA-BUF 是图形、相机、媒体等子系统共享 buffer 的关键机制，dmabufIter 加强了共享内存/图形内存的归因能力。[结构参考: daily-info/2026-07-01 技术文章 #28]

### 🔹 kernelwakelockduration — 内核唤醒锁持续时间统计
新增 kernelwakelockduration eBPF 程序，统计内核 wakelock 持续时间，直接关系到待机功耗和后台耗电归因。eBPF 采集降低了侵入性。[结构参考: daily-info/2026-07-01 技术文章 #29]

### 🔹 locks — 锁竞争分析
新增 locks eBPF 程序，用于锁竞争分析。锁竞争是系统卡顿、尾延迟和线程调度异常的重要来源，eBPF 方式可降低侵入性。[结构参考: daily-info/2026-07-01 技术文章 #30]

### 🔹 cpucycleperuid Rust FFI 库
Android 17 新增 Rust FFI 库 libs/cpucycleperuid/lib.rs，为系统侧交互状态与 CPU 周期统计提供底层支持。[结构参考: daily-info/2026-07-01 技术文章 #34]

## 扩展

### 🔸 eBPF 程序矩阵与 Perfetto 数据源映射
[待验证: 4 个新 eBPF 程序的输出是否可映射到 Perfetto 的 track/event 体系]

### 🔸 cyclePerUid 与现有 per-process CPU 采样的互补关系
[待补充: 在多进程应用（如 Chrome/Webview）场景下，UID 维度统计比 per-process 更准确的条件]

### 🔸 dmabufIter 对图形内存泄漏诊断的价值
[待验证: dmabufIter 能否辅助定位 SurfaceFlinger/Camera HAL 的 DMA-BUF 泄漏]

<!-- outline-end -->

> 本节内容待加工。
