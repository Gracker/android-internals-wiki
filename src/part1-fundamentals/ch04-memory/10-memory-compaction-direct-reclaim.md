---
title: "内存规整与直接回收性能边界"
chapter: "4.10"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [memory, linux-kernel, compaction, direct-reclaim, lmkd]
related_chapters: ["4.2", "4.4", "10.4", "13.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "素材驱动/AOSP结构/官方文档"
sources:
  - type: source-index
    path: "Cubox/不懂 内存规整，别说你会 Linux 内存调优-2026-05-13.md"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: aosp
    path: "kernel/common/mm/compaction.c"
---

# 4.10 内存规整与直接回收性能边界

<!-- outline-start -->
## 要点

### 🔹 问题边界：规整、回收、压缩不是同一件事
说明 memory compaction、page reclaim、ZRAM compression 的职责差异，避免把“内存压缩”混成一个概念。

### 🔹 高阶页分配为什么会触发规整
解释连续物理页需求、迁移类型、fragmentation index 与 direct compaction 的触发条件。

### 🔹 kswapd、direct reclaim 与 direct compaction 的耗时路径
区分后台回收和分配现场同步等待，说明为什么 App 线程可能在内核态停住。

### 🔹 Android 侧内存压力传导：PSI、lmkd 与进程优先级
把内核压力信号、lmkd 决策和 `oom_score_adj` 串起来，说明规整失败与杀进程之间的关系边界。

### 🔹 Perfetto / bugreport 中如何识别规整和回收
列出可观察线索：`kswapd`、`kcompactd`、direct reclaim、page fault、PSI stall、线程 Running/Sleeping 状态。

### 🔹 App 侧能做什么，不能做什么
说明对象分配、Bitmap/Native 内存、内存峰值、后台缓存释放能降低压力，但不能直接控制内核规整策略。

## 扩展

### 🔸 与 16KB Page Size 的关系
大页大小改变会影响高阶页和碎片化压力，但具体收益必须基于设备内核配置和 workload 验证。

### 🔸 与低内存设备和后台保活的关系
低内存设备上回收、swap、规整和 lmkd 决策更容易互相放大，适合作为 10.4 的实战案例入口。

### 🔸 厂商内核调参差异
不同设备的 watermark、compaction、ZRAM、lmkd 参数差异可能改变观测结果，需要在 17.2/17.1 中交叉引用。

<!-- outline-end -->

> 本节内容待加工。
