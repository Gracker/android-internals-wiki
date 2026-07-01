---
title: "Android 17 simpleperf 微架构级性能采样与工作流增强"
chapter: "14.24"
status: draft
applicable_versions: "Android 17 (API 37)"
tags: [simpleperf, ARM-SPE, TRBE, profiling, microarchitecture, AutoFDO]
related_chapters: ["14.2", "14.10", "14.21"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-02"
gap_source: "每日技术文章 intake"
---

# 14.24 Android 17 simpleperf 微架构级性能采样与工作流增强

<!-- outline-start -->
## 要点

### 🔹 ARM SPE 硬件采样支持
Android 17 simpleperf 新增 SPERecorder.cpp/h 和 SPEDecoder.cpp/h，支持 ARM SPE（Statistical Profiling Extension），可采集 L1D、L2、LLC、TLB cache miss 以及 branch misprediction 等微架构级性能事件。[结构参考: daily-info/2026-07-01 技术文章 #20]

### 🔹 TRBE Trace Buffer Extension 支持
TMRecorder 新增对 TRBE（Trace Buffer Extension）的检测与使用，支持 per-CPU 内置 trace buffer，此前主要支持 ETR（集中式 Embedded Trace Router）。[结构参考: daily-info/2026-07-01 技术文章 #21]

### 🔹 --background 后台采集模式
cmd_record 新增 --background 参数，通过 ForkBackgroundProcess() 双 fork 脱离终端，适合长时间运行服务的持续性能分析。[结构参考: daily-info/2026-07-01 技术文章 #22]

### 🔹 --app 按包名自动发现进程
cmd_stat 新增 --app 参数，自动发现属于指定包名的所有进程并加入监控，特别适合应用启动阶段的 stat 采集。[结构参考: daily-info/2026-07-01 技术文章 #23]

### 🔹 Qualcomm pmu_lib 计数器冲突处理
cmd_stat 新增对高通 pmu_lib 驱动的检测与临时禁用（DEADBEEF/BEEFDEAD），避免 PMU 计数器被占用导致采集失败。[结构参考: daily-info/2026-07-01 技术文章 #24]

### 🔹 内核模块 .ko ETM AutoFDO 支持
cmd_inject 扩展支持解析内核模块 ELF 的 .text section 作为可执行段，可对 Android 内核模块（如 zram）收集 AutoFDO profile。[结构参考: daily-info/2026-07-01 技术文章 #25]

## 扩展

### 🔸 ARM SPE 与 traditional sampling 的精度与开销对比
[待补充: 在实际设备上对比 SPE 统计采样与传统基于 PMU 中断的采样在 cache miss 分析中的精度差异]

### 🔸 TRBE vs ETR trace 带宽与延迟
[待补充: per-CPU TRBE 与集中式 ETR 在多核 trace 采集中的带宽、延迟和丢数据场景对比]

### 🔸 simpleperf 与 Perfetto 的协同采样工作流
[待验证: Android 17 中 simpleperf ARM SPE 数据是否能直接导入 Perfetto UI 展示]

<!-- outline-end -->

> 本节内容待加工。
