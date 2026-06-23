---
title: "Android 17 PSI/LowMemDetector 与 lmkd 内存压力检测架构演进"
chapter: "4.15"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [PSI, lmkd, LowMemDetector, BPF, memevents, memory-pressure, libpsi, Android-17, oom_score_adj]
related_chapters: ["4.4", "4.10", "4.12", "5.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-23"
gap_source: "素材驱动"
confidence: high
sources:
  - type: aosp
    path: "system/memory/lmkd/ (android-17.0.0_r1)"
  - type: aosp
    path: "system/memory/lmkd/libpsi/psi.cpp"
  - type: deepresearch
    path: "DeepResearch/2026-06-22-android17-psi-lowmemdetector.md"
---

# 4.15 Android 17 PSI/LowMemDetector 与 lmkd 内存压力检测架构演进

<!-- outline-start -->
## 要点

### 🔹 PSI 内核接口与 libpsi 适配层
- `/proc/pressure/memory` 的 some/full 两种压力类型及其语义
- libpsi 独立子库的 API 链：`init_psi_monitor()` → `register_psi_monitor()` → epoll EPOLLPRI
- Android 17 将 `system/core/lmkd/` 迁移到 `system/memory/lmkd/`，libpsi 作为独立共享库

### 🔹 lmkd 检测路径演进
- Android 12 之前的 vmstat 轮询 + memcg v1 方案
- Android 12 引入 PSI 监控后的混合检测策略
- Android 17 标记 `mp_event_common()` deprecated，memcg v1 不再支持
- PSI 阈值参数：`some 70000 1000000`（70ms 停顿 / 1s 窗口）的含义与调优

### 🔹 BPF memevents 事件订阅机制
- `memevent_listener` 通过 BPF ring buffer 订阅四类内核事件
- 事件类型：`MEM_EVENT_DIRECT_RECLAIM_BEGIN/END`、`MEM_EVENT_KSWAPD_WAKE/SLEEP`、`MEM_EVENT_VENDOR_LMK_KILL`、`MEM_EVENT_UPDATE_ZONEINFO`
- 注册时机：`LMK_BOOT_COMPLETED` 后注册，避免 BPF 程序未加载
- 与 PSI 监控的互补关系：PSI 检测持续压力，memevents 捕获瞬时事件

### 🔹 lmkd kill 决策链
- `__mp_event_psi()` 收到 PSI 压力事件后的综合判定流程
- 判定因子：thrashing（页面抖动）、swap_low（交换空间不足）、zone watermark（内存水位）
- oom_score_adj 分级与 kill 优先级排序
- Android 17 对 kill 策略的微调

### 🔹 PSI 阈值调优与性能影响
- PSI 阈值设置对系统响应性的直接影响
- 阈值过高：内存压力检测滞后，导致 ANR 和全局卡顿
- 阈值过低：过早 kill 缓存进程，影响应用重启速度
- 不同设备 RAM 容量下的阈值差异化策略

### 🔹 LowMemDetector 与 lmkd 的协作边界
- LowMemDetector（内核模块）与 lmkd（用户态守护进程）的分工
- LowMemDetector 基于 zone watermark 做快速响应
- lmkd 基于 PSI 做精细化决策，避免不必要的 kill
- 两者的优先级关系和信息流转

## 扩展

### 🔸 PSI 在其他子系统中的应用
- PSI for I/O 压力（`/proc/pressure/io`）在存储性能分析中的应用
- PSI for CPU 压力（`/proc/pressure/cpu`）与 CPU 调度分析的关联

### 🔸 memcg v2 迁移对内存管理的影响
- Android 17 从 memcg v1 到 v2 的迁移时间线
- v2 带来的内存统计粒度变化
- 对应用内存归因和监控的影响

### 🔸 开发者可观测的 PSI 信号
- 应用进程如何读取 `/proc/pressure/memory` 做主动内存管理
- Memory Advice API 与 PSI 的底层关联
- 开发者如何在低内存设备上做差异化优化

<!-- outline-end -->

> 本节内容待加工。
> [结构参考: DeepResearch/2026-06-22-android17-psi-lowmemdetector.md]
> [已验证: AOSP android-17.0.0_r1, system/memory/lmkd/libpsi/psi.cpp]
