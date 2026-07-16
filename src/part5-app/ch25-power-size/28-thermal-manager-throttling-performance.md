---
title: "ThermalManager 热节流适配与性能降级治理实战"
chapter: "25.28"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [thermal, throttling, performance-degradation, power, ThermalManager, ThrottlingSeverity]
related_chapters: ["5.4", "5.9", "25.1", "25.12", "25.27"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "AOSP结构+官方文档+章节深挖"
---

# 25.28 ThermalManager 热节流适配与性能降级治理实战

<!-- outline-start -->
## 要点

### 🔹 ThermalManagerService 架构与 API 边界
- ThermalManagerService 在 system_server 中的位置与 IPC 链路
- Power HAL Thermal 回调链路：IThermal → ThermalService → ThermalManager API
- Android 17 Thermal HAL 2.0+ 接口演进与 CoolingDevice 语义

### 🔹 应用层热状态监听与响应策略
- ThermalManager.addThermalStatusListener 回调机制
- ThermalStatus 枚举值（NONE → LIGHT → MODERATE → SEVERE → CRITICAL → EMERGENCY → SHUTDOWN）
- 应用如何根据不同 ThermalStatus 执行降级策略（帧率降低、计算简化、后台任务暂停）

### 🔹 热节流引发的性能降级模式分析
- CPU 频率限制 → 主线程耗时增加 → ANR/jank 链路
- GPU 频率限制 → 渲染管线延迟 → 掉帧链路
- 充电热限制 → 后台任务延迟执行 → 应用功能受限
- 热节流与 Doze/App Standby 叠加效应

### 🔹 设备温升模型与性能预算
- SoC 温度-功耗-性能三角关系
- 典型场景温升曲线（游戏、导航、视频通话、直播）
- 性能预算分配策略：短期 burst vs 长期 sustained 工作负载

### 🔹 ADPF Headroom 与 Thermal 协同
- ADPF PerformanceHintManager 提供的性能 headroom 数据
- 应用如何结合 thermal status + ADPF hint 动态调整工作负载
- [结构参考: Clippings/Android 性能优化 - CPU 优化（下）]

### 🔹 线上热节流监控与治理
- ThermalStatus 变化事件的线上采集方案
- 热节流场景下的性能指标分桶（按 thermal status 分组统计 jank/ANR）
- 热节流告警阈值设置与自动化响应（如自动降低视频码率）

### 🔹 OEM 厂商热管理差异
- 高通 / 联发科 / 三星热管理策略差异
- 厂商私有 thermal engine 对 AOSP ThermalManager 的覆盖
- 中国厂商热管理白名单机制

### 🔹 游戏与高性能应用的热治理最佳实践
- GameMode API + ThermalManager 协同
- Unity / Unreal 引擎热节流适配
- 长直播场景的热节流治理案例

## 扩展

### 🔸 PowerManager.isThermalStatusProtectionEnabled
- Android 13+ 新增 API，检查系统是否启用了热保护
- 与 Battery Saver 模式的交互关系

### 🔸 Thermal HAL 2.0 的 sendThermalNotify 机制
- HAL 层主动推送 vs 应用轮询的性能差异

### 🔸 Android 17 Thermal Mitigation 列表
- 系统提供的 thermal mitigation 行为列表及查询方法

<!-- outline-end -->

> 本节内容待加工。
