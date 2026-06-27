---
title: "ART TLAB 与对象分配性能"
chapter: "4.16"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [art, tlab, allocation, rosalloc, gc, memory]
related_chapters: ["4.3", "4.8", "4.14", "10.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构"
---

# 4.16 ART TLAB 与对象分配性能

<!-- outline-start -->
## 要点

### 🔹 ART 对象分配路径全景
从 `new` 关键字到内存分配的完整路径：MewArray/NewInstance → AllocObjectWithAllocator → TLAB/RosAlloc/LargeObjectSpace；快速路径与慢速路径的分支条件。

### 🔹 TLAB（Thread-Local Allocation Buffer）机制
每个线程拥有的本地分配缓存区；TLAB 的容量动态调整策略；TLAB 用尽时的 refill 流程；无锁分配的性能优势。

### 🔹 RosAlloc（Region-based Memory Allocator）
RosAlloc 对 TLAB 的替代与增强；按对象大小分组的 region 策略；与 dlmalloc 的对比；Android 14+ 的优化。

### 🔹 LargeObjectSpace 与大对象分配
超过阈值（通常 3KB page 对齐）的对象进入 LOS；LOS 的 mmap/munmap 策略；大对象对 GC 暂停时间的影响。

### 🔹 分配竞争与 GC 触发
分配失败时的 GC 触发逻辑；concurrent GC 与分配的竞争关系；分配阈值（min_free, max_free）的动态调整。

### 🔹 Android 17 ART 分配变更
Region-based allocation 与 TLAB 的整合；concurrent allocation 的改进；GC 暂停优化对分配路径的影响。

### 🔹 实战：观察分配性能
Allocation Tracker / Profiler 的使用；Perfetto 中 ART allocation 的 trace 轨道；如何判断分配瓶颈（TLAB refill 频率、GC 触发频率、LOS 分配比例）。

## 扩展

### 🔸 对象池与 TLAB 的协作
Android Message 对象池的设计；自定义对象池对 GC 压力的影响；TLAB 友好 vs TLAB 敌对的编程模式。

### 🔸 Compose 的分配模式与 TLAB
Compose 的 Snapshot 对象分配频率；remember 的缓存效果对 TLAB 压力的缓解。

<!-- outline-end -->

> 本节内容待加工。
