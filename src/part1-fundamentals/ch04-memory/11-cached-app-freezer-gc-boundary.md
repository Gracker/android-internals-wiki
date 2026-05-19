---
title: "Cached App Freezer 与 GC 触发边界"
chapter: "4.11"
status: draft
applicable_versions: "Android 11 QPR3+; Android 14+ FrozenStateChangeCallback; Android 16/17 16KB Page Size"
tags: [cached-app-freezer, gc, lmkd, oom-adj, binder-freezer, memory]
related_chapters: ["1.18", "4.2", "4.3", "4.4", "4.7", "5.8", "20.5", "26.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "每日信息/DeepResearch/AOSP结构/官方文档"
---

# 4.11 Cached App Freezer 与 GC 触发边界

<!-- outline-start -->
## 要点

### 🔹 Freezer 解决的是 cached 进程继续消耗 CPU 的问题
梳理 Cached App Freezer 的定位：它把符合条件的 cached 进程迁移到 frozen cgroup，停止线程调度，减少后台 CPU 和电量消耗；同时说明冻结本身不释放 Java Heap、Native Heap 或匿名页内存。

### 🔹 OOM Adj 是入口条件，不是 LMK 决策复用
围绕 `ProcessList.CACHED_APP_MIN_ADJ`、`FREEZER_CUTOFF_ADJ`、`CACHED_APP_LMK_FIRST_ADJ` 拆清边界：freezer 与 LMKD 都会看进程重要性，但一个暂停执行，一个杀进程释放内存，排障时不能把两者合并成“低内存处理”。

### 🔹 CachedAppOptimizer 的冻结/解冻链路
以 `OomAdjuster.applyOomAdjLocked()`、`CachedAppOptimizer.freezeProcess()`、framework/native JNI 与 cgroup 写入为主线，给出冻结触发、异步处理线程、`mFrozenProcesses` 状态记录和进程移除清理路径。

### 🔹 Binder Freezer 与解冻延迟
说明 Android 14+ `IBinder.addFrozenStateChangeCallback` 与 binder freezer 文档的协作方式；重点放在同步 binder call、服务绑定、UI 可见性恢复等解冻入口，以及解冻延迟对调用方卡顿/ANR 的排查价值。

### 🔹 GC 触发与 Freezer 没有直接因果关系
把 ART GC 的触发路径放回 `art/runtime/gc/heap.cc`：对象分配、堆占用阈值、后台 GC 与 low-memory 信号会影响 GC；freezer 只是停止调度，不会主动触发 GC，也不会替代 `onTrimMemory()` 或 LMKD。

### 🔹 16KB Page Size 影响内存粒度，不改写 freezer 语义
解释 16KB 页对分配粒度、页对齐、native/anonymous memory 观测口径的影响；同时标注待验证点：Android 16/17 分支中是否存在 freezer 专属 16KB 适配代码，不能从页大小变化推导出 GC/freezer 策略变化。

### 🔹 线上归因：区分冻结、GC、LMK 与用户感知重启
建立排障口径：Perfetto/trace 中看线程调度停顿，dumpsys activity/process 看 adj 和 frozen 状态，ApplicationExitInfo 看退出原因，GC log/heap profile 看堆事件，避免把“回前台慢”“像冷启动”“内存突然下降”混成同一类问题。

## 扩展

### 🔸 Android 11 QPR3 到 Android 17 的版本演进
整理 cached app freezer、binder freezer callback、DeviceConfig throttle、16KB Page Size 支持之间的时间线。

### 🔸 厂商 freezer 策略差异
补充 Pixel、国内 ROM、低内存设备上的 freezer 开关、阈值、白名单和后台保活策略差异；需要实机 trace 或厂商源码验证。

### 🔸 与 1.18 Binder Freezer 的边界
本节只讲内存/GC/LMK 视角；Binder 协议与 frozen process 通信细节详见 1.18。

<!-- outline-end -->

> 本节内容待加工。
