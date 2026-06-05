---
title: "CPU Cache 友好代码与数据布局优化"
chapter: "5.18"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [cpu-cache, cache-line, false-sharing, data-layout, dex-reordering, redex, locality, startup-optimization]
related_chapters: ["5.1", "5.3", "8.7", "16.6", "21.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-05"
gap_source: "Clippings结构参考/AOSP结构/章节深挖"
gap_score: 16
material_count: 5
---

# 5.18 CPU Cache 友好代码与数据布局优化

<!-- outline-start -->
## 要点

### 🔹 锚点 1：移动端 CPU Cache 层级与性能影响
- ARM Cortex-A 系列 L1/L2/L3 cache 结构与延迟（典型值：L1 1ns / L2 4-8ns / L3 15-20ns / 主存 80-120ns）
- Cache line 大小（ARMv8 通常 64 字节）对数据加载行为的影响
- 大小核架构下不同核心的 cache 配置差异（A7xx vs A5xx）
- Cache miss 对帧率和启动耗时的量化影响

### 🔹 锚点 2：False Sharing 与多线程性能陷阱
- False sharing 的产生机制：两个线程修改同一 cache line 的不同字段
- Android framework 中的典型案例：MessageQueue、SparseArray、ART GC 卡片表
- 如何通过 perf record / Simpleperf 识别 false sharing（L1-dcache-load-miss 事件）
- 解决手段：padding、@Contended 注解（JVM）、结构体字段重排

### 🔹 锚点 3：数据结构布局与 Cache 局部性
- AoS（Array of Structures）vs SoA（Structure of Arrays）在不同访问模式下的 cache 表现
- 热路径数据紧凑排列：将频繁访问的字段放在结构体头部
- Android 渲染链路中的 cache 局部性案例（RenderNode、DisplayList 指令序列）
- 内存对齐规则（alignas、__attribute__((aligned)))对 cache 命中率的影响

### 🔹 锚点 4：DEX 类重排序与启动 Cache 优化
- DEX 文件中类的排列顺序如何影响冷启动时的 instruction cache miss
- Facebook Redex 的 interdex pass 原理：基于类调用图的拓扑排序
- Android Gradle Plugin 的 DEX 布局优化（reorderClassesWith Profiling）
- Baseline Profile 与 DEX 重排序的协同关系（详见 21.4）
- 实测数据：DEX 重排序对冷启动 P50/P90 的影响

### 🔹 锚点 5：Cache 友好代码的编写准则
- 顺序访问 vs 随机访问的 cache 命中率差异（数组遍历 vs 链表遍历）
- 分支预测与指令 cache：__builtin_expect、likely/unlikely 的使用场景
- Prefetch 指令（__builtin_prefetch）的适用场景与误用风险
- 循环分块（loop tiling）在大数组处理中的应用
- 避免在热路径上创建临时对象：减少 cache 污染

### 🔹 锚点 6：性能观测：如何确认 Cache 瓶颈
- Simpleperf 的 cache 事件采样（L1-dcache-load-miss、LLC-load-miss）
- ARM Streamline Performance Analyzer 的 cache 命中率可视化
- Perfetto 中结合 CPU 频率和 IPC（Instructions Per Cycle）判断 cache 瓶颈
- Linux perf stat 的硬件事件计数在 Android 上的可用性边界
- 低 IPC + 高 CPU 频率 = 典型的 cache miss 瓶颈信号

### 🔹 锚点 7：Android 系统层的 Cache 优化实践
- ART 虚拟机的 inline cache 和方法 hotness 跟踪
- SurfaceFlinger 的 layer 列表遍历与 cache 局部性
- Binder 数据序列化中的连续内存布局设计（Parcel flat structure）
- Kernel 的 SLUB 分配器对 cache line 对齐的处理

## 扩展

### 🔸 扩展点 1：GPU Cache 与异构计算
- GPU 着色器中的共享内存（shared memory）优化
- GPU texture cache 对图片加载管线的影响
- Vulkan 的 device-local memory 与 host-visible memory 的 cache 行为差异

### 🔸 扩展点 2：Rust/NDK 层的 Cache 优化
- Rust 所有权模型对数据布局优化的天然优势
- NDK native 代码中的 cache line 对齐实践
- CrossBeam 无锁数据结构的 cache 友好设计

### 🔸 扩展点 3：SoC 级 Cache 架构差异
- Qualcomm Kryo vs ARM Cortex 的 cache 配置差异
- MediaTek Dimensity 的共享 L3 / 独立 L2 策略
- Samsung Exynos 的 Mongoose 核心 cache 延迟特征

<!-- outline-end -->

> 本节内容待加工。
