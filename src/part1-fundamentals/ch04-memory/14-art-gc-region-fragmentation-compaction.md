---
title: "ART GC Region 碎片化与 Compaction 策略"
chapter: "4.14"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['ART', 'GC', 'RegionSpace', 'MarkCompact', '碎片化', '内存管理']
related_chapters: ['4.3', '4.8', '4.10']
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
gap_source: "DeepResearch 调研结果（score 19）+ AOSP 源码结构"
---

# 4.14 ART GC Region 碎片化与 Compaction 策略

<!-- outline-start -->
## 要点

### 🔹 锚点 1：RegionSpace UnevacFromSpace 机制
RegionSpace 的区域级碎片控制：CC 收集器按 75% 存活率阈值（kEvacuateLivePercentThreshold）决定每个 region 是搬迁到 to-space 还是就地降级为 unevac from-space。高占用率 region 不再被反复搬迁，从根源消除 region 级循环分配碎片（bug b/33795328）。

### 🔹 锚点 2：并发 MarkCompact（CMC）与 userfaultfd 压缩
当设备支持 userfaultfd 时，ART 把整堆压缩改造为页级 fault-retry 模型（依赖 Linux 5.7+ 内核 UFFD minor-fault 特性）。YoungMarkCompact 与 MarkCompact 共享底层状态机，实现 young/mid/old 三代半空间-压缩混合模型。

### 🔹 锚点 3：Generational CMC 门控与 DeviceConfig 开关
use_generational_cmc flag 与 persist.device_config.runtime_native_boot.use_generational_gc 持久化属性控制三代 CMC 的启用。启用条件、降级策略与运行时行为变更。

### 🔹 锚点 4：LargeObjectSpace 与碎片诊断
LargeObjectSpace 保持 CanMoveObjects() == false，不参与压缩。LogFragmentationAllocFailure() 在分配失败时打印最大连续可分配块长度，作为碎片诊断信号。

### 🔹 锚点 5：Region 分配策略与 kCyclicRegionAllocation
kCyclicRegionAllocation 策略减少 region 复用，帮助早期发现 GC bug，但可能造成 region 级内存碎片。仅在 debug 模式启用，production 使用线性分配。

### 🔹 锚点 6：GC 暂停预算与端侧 AI 场景适配
整套碎片控制方案的目标：把 GC 暂停压到 sub-2ms，消除 region 反复搬迁造成的 RSS 增长。对大模型推理、长会话直播等长生命周期对象密集的应用场景影响分析。

### 🔹 锚点 7：从 CC 到 CMC 的路径选择与版本演进
Android 14-17 各版本中 RegionSpace/CMC 的演进路径，不同设备能力（userfaultfd 支持）下的 GC 策略选择矩阵。

## 扩展

### 🔸 扩展点 1
CMC 与 ZRAM 压缩的交互：压缩内存页对 UFFD minor-fault 路径的影响

### 🔸 扩展点 2
16KB Page Size 对 Region 大小选择与碎片化率的量化影响

### 🔸 扩展点 3
端侧 LLM 推理场景下 GC 暂停对推理延迟的实际影响案例

<!-- outline-end -->

> 本节内容待加工。
