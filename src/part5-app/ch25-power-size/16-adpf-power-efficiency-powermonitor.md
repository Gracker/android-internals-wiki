---
title: "ADPF Power Efficiency Mode 与 PowerMonitor 能耗闭环"
chapter: "25.16"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [adpf, power-efficiency, powermonitor, power-rails, perfetto, power-optimization]
related_chapters: ["5.9", "11.2", "25.1", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "素材驱动/官方文档/AOSP结构"
---

# 25.16 ADPF Power Efficiency Mode 与 PowerMonitor 能耗闭环

<!-- outline-start -->
## 要点

### 🔹 适用场景：什么时候该把线程标成节能优先
长时间、可延迟、吞吐稳定的工作负载适合进入 Power Efficiency Mode；帧渲染、输入响应、播放解码等延迟敏感路径要保留性能优先策略。

### 🔹 ADPF Session 的线程集合与生命周期
围绕 `PerformanceHintManager.Session` 建立线程集合，说明 `createHintSession()`、目标耗时、实际耗时上报、线程迁移和 `close()` 的边界。

### 🔹 Power Efficiency Mode 的系统语义
`setPowerEfficiencyHint(true)` 只表达调度偏好，不保证具体 CPU 频点、核心选择或功耗下降比例；最终执行取决于 Power HAL、调度器、温控状态和 OEM 实现。

### 🔹 PowerMonitor 与 SystemHealthManager 读数模型
梳理 `PowerMonitor`、`PowerMonitorReadings`、`SystemHealthManager.getSupportedPowerMonitors()` 和 `getPowerMonitorReadings()` 的关系，明确读数单位、累计语义和重启边界。

### 🔹 Perfetto power_rails 作为交叉验证通道
用 `android.power_rails`、CPU frequency、应用自定义 trace marker 对齐 ADPF hint 生效窗口，避免只看电池百分比判断节能收益。

### 🔹 线上灰度与指标设计
把 hint 开关、目标线程、任务类型、设备型号、温度状态、rail 能耗差值纳入实验维度，用 P50/P90/P99 耗时和单位任务能耗同时判断收益。

### 🔹 OEM 差异与降级策略
当设备不提供完整 power rail、`PowerMonitor` 列表为空或读数波动过大时，回退到 Perfetto、BatteryStats、Android Studio Power Profiler 或端侧任务耗时指标。

## 扩展

### 🔸 游戏帧循环与后台计算的策略差异
对比游戏帧驱动、媒体处理、批量同步、日志压缩等负载如何设置 target duration 与节能 hint。

### 🔸 PowerMonitor 与 Android Studio Power Profiler 数据口径
拆分 API 读数、Perfetto power rails、ODPM、Power Profiler 的采样边界，避免多个工具混用时口径不一致。

### 🔸 与 Thermal API 的联合治理
把 `PowerManager.OnThermalStatusChangedListener` 与 ADPF hint session 组合，形成温控前的主动降载策略。

### 🔸 待验证：PowerMonitorReadings 与 Perfetto power_rails 一致性
需要在 Pixel 与至少一个 OEM 设备上验证同一时间窗内 API 读数和 Perfetto 表的差值是否一致。

<!-- outline-end -->

> 本节内容待加工。
