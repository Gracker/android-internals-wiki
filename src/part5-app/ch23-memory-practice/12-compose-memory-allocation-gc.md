---
title: "Jetpack Compose 内存分配与 GC 影响"
chapter: "23.12"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [compose, memory, gc, allocation, slottable, recomposition]
related_chapters: ["4.8", "7.7", "10.6", "22.3", "22.20"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-19"
gap_source: "素材驱动/研究素材"
---

# 23.12 Jetpack Compose 内存分配与 GC 影响

<!-- outline-start -->
## 要点

### 🔹 Compose 运行时的内存模型
- Composition 对象的内存组成：SlotTable + 重组范围追踪 + 状态记录
- SlotTable 数据结构：基于数组的持久化树，存储 Composable 执行产生的状态
- Composer 对象的分配模式：每次重组创建的临时对象清单
- RecomposeScope 的生命周期与 GC 关系

### 🔹 重组中的对象分配热点
- @Composable 函数每次执行产生的隐式对象分配：remember 表项、State 记录
- Lambda 捕获的内存开销：闭包变量引用链对堆的压力
- derivedStateOf 和 remember 的对象持有策略
- Strong Skipping（Compose 1.8+）对不稳定参数对象分配的影响

### 🔹 State 对象与内存开销
- MutableState 的内部实现：SnapshotMutableStateImpl 的 state record 链
- mutableStateOf vs mutableStateListOf/mutableStateMapOf 的内存差异
- snapshotFlow 的内存开销：快照持有期间的对象引用
- listStateMapOf 等结构在频繁更新时的内存碎片

### 🔹 SlotTable 内存增长模式
- SlotTable 的数组扩容策略与内存增长曲线
- 深层 Composable 嵌套下的 SlotTable 体积
- SlotTable 在重组时的 gap buffer 机制：预分配空间 vs 按需扩容
- 退出 Composition 后 SlotTable 的内存释放（disposeComposition）

### 🔹 Compose 混合栈（View + Compose）的内存叠加
- AndroidComposeView 作为 View 树节点的额外内存开销
- View 系统和 Compose 并存时的双重状态追踪
- AndroidView wrapper 的 native bitmap 持有
- ComposeView 在多 Fragment 场景下的 Composition 隔离与重复创建

### 🔹 GC 压力与帧抖动
- Compose 短生命周期对象对分代 GC 的影响：minor GC 频率与帧暂停
- 大型 Composable 树重组时的分配峰值（allocation spike）
- Compose 在低端设备上的 GC 表现：dalvik vs ART 的差异
- 通过 Allocation Tracker 定位 Compose 中的异常分配

### 🔹 内存优化策略
- 避免不必要重组的内存收益：比 CPU 收益更显著
- key 参数在 LazyList 中的内存复用价值
- derivedStateOf 作为内存优化工具：减少中间状态对象
- Compose Compiler metrics 诊断分配热点

## 扩展

### 🔸 Compose Multiplatform 的内存差异
- KMP 场景下 Compose 运行时的内存行为差异
- 平台特定内存管理（Android ART vs Desktop JVM）

### 🔸 Compose 测试的内存开销
- Compose UI Test 的内存放大效应
- 多个 Composition 在测试中的内存叠加

<!-- outline-end -->

> 本节内容待加工。
