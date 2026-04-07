---
title: "eBPF/BPF 在 Android 性能分析中的应用"
chapter: "14.10"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [eBPF, BPF, observability, tracing, sched_ext, simpleperf, kernel, performance]
related_chapters: ["14.2", "13.1", "5.1", "1.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "AOSP结构+官方文档+研究素材"
---

# 14.10 eBPF/BPF 在 Android 性能分析中的应用

<!-- outline-start -->
## 要点

### 🔹 锚点 1：eBPF 是什么，为什么 Android 性能分析需要它
- eBPF 在 Linux 内核中的定位：安全、高效的内核可编程框架
- 与传统性能分析工具（perf/strace/ftrace）的本质区别
- Android 从哪个版本开始系统级使用 eBPF（Android 9+ BPF loader）
- 在 Perfetto 中 eBPF 数据的表现

### 🔹 锚点 2：Android eBPF 基础设施
- AOSP BPF loader 的工作方式（/system/etc/bpf/）
- BPF 程序的加载、maps、pinning 机制
- Android 中已有的系统级 eBPF 程序（网络统计、防火墙、能耗统计）
- BPF CO-RE（Compile Once – Run Everywhere）对 Android 的意义

### 🔹 锚点 3：Simpleperf 与 eBPF 的结合
- Simpleperf 的 eBPF 后端（stat/record/report）
- 如何用 Simpleperf 进行 eBPF 性能分析
- 与传统 perf_event 硬件采样的对比
- 实际使用场景（CPU hotspot、锁竞争、系统调用追踪）

### 🔹 锚点 4：UprobeStats 与动态埋点
- UprobeStats 的原理与使用
- 用户态动态追踪（uprobe）对 App 性能分析的价值
- 与传统 Trace.beginSection 的区别
- 性能开销对比与适用场景

### 🔹 锚点 5：sched_ext 与可扩展调度器
- sched_ext 在 Linux 6.12 中合并的背景
- eBPF 驱动的自定义调度策略对 Android 性能优化的意义
- Android 17 GKI Kernel 6.12 中 sched_ext 的状态
- OEM/SoC 厂商如何利用 sched_ext 定制调度

### 🔹 锚点 6：eBPF 在 Android 性能分析中的实战场景
- CPU 利用率精准计算（对比 /proc/stat 的精度差异）
- 系统调用延迟追踪
- 网络包处理性能分析
- I/O 延迟分布统计
- 内存分配追踪

### 🔹 锚点 7：限制与注意事项
- eBPF 在非 root/非 debug 设备上的限制
- 性能开销（每次 eBPF 事件的 CPU 消耗）
- 与 Android SELinux 策略的交互
- 调试 eBPF 程序的挑战

## 扩展

### 🔸 扩展点 1：bpftrace 在 Android 上的使用
- bpftrace 作为高层 eBPF 前端
- 适合性能工程师的快速追踪脚本
- Android 上运行 bpftrace 的限制与变通

### 🔸 扩展点 2：eBPF 与 Perfetto SQL 的集成
- 如何将 eBPF 采集的数据导入 Perfetto 分析
- 自定义 Perfetto data source 的开发
- 与现有 Perfetto trace 的关联分析

### 🔸 扩展点 3：eBPF 在 OEM 性能优化中的角色
- OEM 如何利用 eBPF 进行调度/功耗定制
- MTK/高通平台上 eBPF 的实际使用情况
- eBPF 与厂商性能框架（如 MTK Dynamic Boost）的关系

<!-- outline-end -->

> 本节内容待加工。
