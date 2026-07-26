---
title: "Android 17 AppFlow + LMKD v2 内存联合调度协作机制"
chapter: "4.12"
status: deprecated
applicable_versions: "Android 17 (API 37)"
tags: [内存管理, AppFlow, LMKD, 联合调度, OOM防护]
related_chapters: ["4.5", "4.11", "16.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-03"
gap_source: "AOSP结构"
---
> ⚠️ **本节已废弃 (deprecated 2026-07-04)**：与 4.5 (ready-for-review, 504 lines) 内容重复。



# 4.12 Android 17 AppFlow + LMKD v2 内存联合调度协作机制

<!-- outline-start -->
## 要点

### 🔹 AppFlow 三段式调度模型
- 大应用冷启动阶段：内存预分配策略
- 正常运行阶段：动态内存调整
- 后台冻结阶段：智能内存释放
- 各阶段之间的状态切换机制

### 🔹 LMKD v2 优先级杀死机制
- LM_PROCS_PRIO (id=11) 异步批量处理
- 最大32进程的批处理能力
- io_uring 实现的高效异步处理
- thrashing_limit 的动态衰减策略

### 🔹 内存压力协同指标
- Memory Reclaim Priority 配置
- Adaptive Background Activity Manager 集成
- MGLRU 状态机独立运行
- 内存压力辅助指标的计算方法

### 🔹 协作协议设计
- AppFlow与LMKD的通信接口
- 内存阈值共享机制
- 冲突解决策略
- 一致性保证协议

### 🔹 启动期保护窗口
- thrashing_limit 动态衰减算法
- 启动期内存保护机制
- 优先级提升策略
- 性能基准监控

## 扩展

### 🔸 系统集成测试
- 协作机制的性能基准测试
- 多应用场景的压力测试
- 边界条件的验证方案
- 内存泄漏的检测机制

### 🔸 运维监控体系
- 联合调度状态的实时观测
- 性能指标的量化分析
- 异常情况的告警机制
- 调优参数的动态配置

### 🔸 设备厂商适配
- 不同硬件规格的参数调优
- 内存压力感知的差异化配置
- 厂商定制特性的兼容处理
- 性能回归的测试方法

<!-- outline-end -->

> **废弃说明**：本页没有独立源码或测试材料，且 protected outline 中的 AppFlow 协作协议、`LM_PROCS_PRIO`、32 进程批处理、io_uring 与启动保护窗口均无法在 `android-17.0.0_r1` 中成立。正确命令名为 `LMK_PROCS_PRIO`，每个控制 packet 最多携带 3 条记录；详见 [4.36 LMK_PROCS_PRIO 批量命令](4.36-android17-lmkd-procs-prio-batch.md)。Android 17 lmkd 的全局 PSI 与 cgroup 边界见 [4.50 LMKD PSI 分层内存压力治理](4.50-lmkd-v2-psi-tiered-pressure-governance.md)。本页不再维护。
