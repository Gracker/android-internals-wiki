---
title: "Perfetto CPU 频率与 DVFS 关联分析"
chapter: "13.13"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [perfetto, cpu-frequency, dvfs, power, scheduling]
related_chapters: ["5.2", "5.4", "11.1", "13.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/官方文档/AOSP结构"
---

# 13.13 Perfetto CPU 频率与 DVFS 关联分析

<!-- outline-start -->
## 要点

### 🔹 采集入口：`power/cpu_frequency`、`power/cpu_idle` 与 `linux.sys_stats`
说明事件驱动与轮询两种 CPU 频率来源的差异，明确 `cpufreq_period_ms` 适合补齐 trace 开头缺少初始频率的问题。

### 🔹 CPU 频率、空闲状态与线程 Running 的关系
把 `sched`、`thread_state`、`cpufreq`、`cpuidle` 放到同一条判断路径里，避免把 Running 时间直接等同于高频运行时间。

### 🔹 大小核与 CPU cluster 的频率轨道识别
利用 `linux.system_info`、`cpu_freq` 表和可用频点识别 cluster，说明同一 cluster 内多个 CPU 同步变频的常见表现。

### 🔹 DVFS 调节滞后对启动、滑动与后台任务的影响
覆盖短突发任务、连续渲染负载、后台批处理三类场景，说明频率爬升、降频滞后和空闲状态恢复成本如何影响性能判断。

### 🔹 Perfetto SQL：从 counter 表重建频率时间线
给出 `counter` + `cpu_counter_track` 的查询方向，后续正文补充可直接复用的 SQL 模板和结果解释方式。

### 🔹 端侧 AI 推理中的 CPU/GPU governor 协同问题
基于移动端 LLM DVFS 论文素材，说明 CPU、GPU、内存 governor 分开调节时可能出现的能效错配，并标注设备与模型边界。

### 🔹 误判清单：USB、空闲态、缺失事件与厂商 governor
列出 trace 采集和解释时最容易出错的条件，包括 USB 保持唤醒、空闲态下频率值含义变弱、部分平台不暴露频率事件、厂商调度策略不可外推。

## 扩展

### 🔸 与 EAS / uclamp / thermal 的交叉验证
结合 5.2、5.4、11.1 节，补充 CPU capacity、任务迁移、降频与温控事件的组合判断。

### 🔸 线上采集能力边界
对比本地 Perfetto、Android Studio System Profiler、ProfilingManager 返回 trace 的字段可见性和隐私裁剪边界。

### 🔸 典型 SQL 模板集
后续可拆出 CPU 频率分布、Running 时间加权频率、cluster 迁移前后频率变化、渲染帧窗口内频率统计四类模板。

<!-- outline-end -->

> 本节内容待加工。
