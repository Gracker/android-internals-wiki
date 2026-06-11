---
title: "AMS 双锁架构与 system_server 锁竞争优化"
chapter: "1.25"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [lock-contention, system-server, ams, process-record, dual-lock, performance]
related_chapters: ["1.14", "1.3", "5.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
gap_source: "研究素材/DeepResearch"
sources:
  - type: research
    path: "DeepResearch/2026-06-10-lru-lock-optimization.md"
---

# 1.25 AMS 双锁架构与 system_server 锁竞争优化

<!-- outline-start -->
## 要点

### 🔹 从单锁到双锁：AMS 锁架构演进
Android 12 引入 `ENABLE_PROC_LOCK = true`，将 `ActivityManagerGlobalLock`（mGlobalLock）拆分为 `mGlobalLock` + `mProcLock`（mProcLock）双层锁。`mProcLock` 是 `ActivityManagerProcLock` 实例，专用于 ProcessRecord 级别操作。背景是 system_server 中 LRU 更新、进程 OOM 调整、时间区变更等高频操作共享一把全局锁，导致多线程并发性能瓶颈。

### 🔹 mGlobalLock 与 mProcLock 的职责划分
- `mGlobalLock`：进程创建/销毁、Activity 生命周期、Service 绑定/解绑等全局状态变更
- `mProcLock`：ProcessRecord 内部状态读写（LRU 位置、OOM adj、进程调度组、内存状态）
- LOSP/LSP 命名约定：`@GuardedBy("mService")` 标记 mGlobalLock 保护的方法，`@GuardedBy("mProcLock")` 标记 mProcLock 保护的方法

### 🔹 CompositeRWLock 注解机制
Android 引入 `@CompositeRWLock` 注解，声明多锁的获取顺序和读写模式，用于静态分析工具检测死锁风险。锁获取顺序规则：mGlobalLock 必须在 mProcLock 之前获取，避免 A-B / B-A 死锁。

### 🔹 LRU 更新路径的锁竞争优化
原先 LRU 列表更新需要持有 mGlobalLock，阻塞所有需要 mGlobalLock 的线程。拆分后 LRU 更新只持 mProcLock，mGlobalLock 持有者不被阻塞。锁竞争时间从约 25ms 降至约 8ms，吞吐量提升约 3 倍（基于 DeepResearch 2026-06-10 测量数据）。

### 🔹 OOM adj 调整与进程优先级更新的并发化
`updateOomAdjLocked` 在旧架构下持 mGlobalLock 独占，阻塞所有 AMS 操作。双锁架构下，OOM adj 计算和写入可只持 mProcLock，允许 Activity 启动/Service 续约等全局操作并行进行。

### 🔹 Perfetto 观测：锁竞争热点定位
在 Perfetto trace 中通过 `binder` 轨道和 `Lock contention` slice 观察 system_server 锁等待。双锁优化后，`ActivityManagerGlobalLock` 的持有时间变短，新出现的 `ActivityManagerProcLock` 持有时间短且竞争少。用 SQL 查询 `thread_track` + `lock_count` 数据验证效果。

### 🔹 观测方法与实战建议
- `adb shell dumpsys activity processes` 输出中的锁信息
- Perfetto SQL：统计 mGlobalLock 和 mProcLock 的等待次数和持续时间
- `StrictMode` 检测跨锁边界的错误用法
- 应用开发者如何避免在 `onServiceConnected` 等 Binder 回调中触发 AMS 锁竞争

## 扩展

### 🔸 Android 12 之前的单锁架构性能瓶颈回顾
旧架构下 system_server 锁竞争的热点场景和典型 trace 表现。

### 🔸 其他系统服务的锁优化模式
对比 PowerManagerService、WindowManagerService 的锁设计，总结 Android 系统服务锁优化的通用模式。

### 🔸 应用侧如何避免间接触发 system_server 锁竞争
高频调用 `ActivityManager.getRunningAppProcesses()`、`ActivityManager.getMemoryInfo()` 等 API 时可能触发的锁竞争，以及替代方案。
<!-- outline-end -->

> 本节内容待加工。
[结构参考: DeepResearch/2026-06-10-lru-lock-optimization.md]
