---
title: "缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升"
chapter: "21.18"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [缓存优化, Cache, CPU, 缓存命中率, 性能优化]
related_chapters: ["1.1", "5.1", "21.1", "21.6", "27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动(Clippings)"
confidence: medium
---

# 21.18 缓存优化实战：冷热端分离、重排序与 CPU 缓存命中率提升

<!-- outline-start -->
## 要点

### 🔹 CPU 缓存层次结构与 Android 设备特性
- L1/L2/L3 cache 在 ARM Cortex / X 系列核心的大小与延迟
- big.LITTLE / DynamIQ 架构下的缓存拓扑差异
- Android 17 设备典型缓存配置

### 🔹 缓存命中率对应用性能的量化影响
- Cache miss 的代价：L1 miss ~10 cycles, L2 miss ~40 cycles, L3 miss ~100+ cycles
- 为什么缓存优化是"免费的性能提升"

### 🔹 冷热端分离策略
- 将频繁访问的数据（热端）与很少访问的数据（冷端）分离到不同内存区域
- 数据结构设计中的 cache locality：数组 vs 链表 vs 对象池
- Android 应用中典型的冷热数据分离场景

### 🔹 数据重排序与内存布局优化
- 字段排序：将高频访问字段集中到 cache line（通常 64 bytes）
- Struct of Arrays vs Array of Structs 在 Android 中的适用性
- @Contended 注解与伪共享（false sharing）规避

### 🔹 代码缓存优化
- 指令缓存局部性：热点函数的集中布局
- ART AOT 编译后的代码布局特征
- Baseline Profile 对代码缓存命中率的间接影响

### 🔹 实战案例分析
- 列表滚动场景的数据结构重排序：从 LinkedList 到 ArrayBacked
- 启动路径中对象池的缓存友好设计
- [结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率]

### 🔹 缓存命中率测量方法
- simpleperf stat -e cache-misses,cache-references 的使用
- Perfetto trace 中的 CPU cache 相关 counter
- ARM PMU 事件在 Android 17 上的可用性

## 扩展

### 🔸 Compose 数据结构的缓存友好性分析
- Compose Slot Table 的内存布局特征
- Compose 1.x 到 1.10 的内存分配器优化对缓存的影响

### 🔸 SoC 厂商差异化缓存配置
- 高通 / 联发科 / 三星旗舰芯片的缓存层级差异
- OEM 场景下的缓存调优策略

<!-- outline-end -->

> 本节内容待加工。
