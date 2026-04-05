---
title: "ADPF 自适应性能框架"
chapter: "5.9"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [adpf, thermal, performance-hint, game-performance, cpu-boost, frame-rate]
related_chapters: ["5.5", "5.6", "7.5", "14.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档+研究素材+AOSP结构"
gap_score: "15/20"
---

# 5.9 ADPF 自适应性能框架

<!-- outline-start -->
## 要点

### 🔹 锚点 1：ADPF 解决什么问题
- 移动设备的性能困境：CPU/GPU 性能上限固定，但负载波动大（游戏、AR、相机）
- 传统方案的问题：固定频率策略要么浪费功耗（一直高频），要么卡顿（负载突增来不及提频）
- ADPF 的核心思路：让 App 向系统「预告」性能需求，系统据此动态调整 CPU/GPU 频率
- Google 的定位：Performance Hint API + Thermal API + Game Mode API 的统一框架

### 🔹 锚点 2：Performance Hint API 的工作机制
- PerformanceHintManager / PerformanceHintProvider（系统服务）
- HintSession：App 与系统建立的「性能契约」
- reportActualWorkDuration()：App 报告每帧实际耗时
- updateTargetWorkDuration()：App 告知目标帧时间
- 系统侧的响应：根据实际 vs 目标的偏差调整 CPU 频率
- [图：ADPF 反馈循环——App 报告耗时 → 系统调整频率 → App 帧时间变化 → 继续报告]

### 🔹 锚点 3：Thermal API
- ThermalManager：监听设备热状态变化
- THERMAL_STATUS_NONE → LIGHT → MODERATE → SEVERE → CRITICAL → EMERGENCY → SHUTDOWN
- App 如何根据热状态降级（降低画质、减少帧率、简化特效）
- 与 PowerManagerService 的关系

### 🔹 锚点 4：Game Mode API
- GameManager：游戏模式（PERFORMANCE/BATTERY/STANDARD）
- 用户可在系统设置中选择游戏模式
- App 根据模式调整渲染质量和帧率目标
- Game Mode 与 ADPF Hint 的协同

### 🔹 锚点 5：Android 16/17 的 ADPF 新特性
- Headroom API：查询当前 CPU/GPU 的性能余量
- 改进的热状态预测
- ADPF 对非游戏场景的扩展（Camera、视频播放）
- [待验证：Android 17 ADPF 具体新增 API]

### 🔹 锚点 6：在 Perfetto 中的表现
- ADPF Hint Session track：每个 session 的 target duration vs actual duration
- Thermal status track：热状态变化时间线
- CPU frequency track 与 ADPF hint 的关联
- 分析 ADPF 是否有效的判断方法

## 扩展

### 🔸 扩展点 1：Unity/Unreal Engine 的 ADPF 集成
- 主流游戏引擎如何集成 ADPF
- 自动 ADPF vs 手动 ADPF 的取舍

### 🔸 扩展点 2：OEM 对 ADPF 的定制
- 不同 SoC 厂商的 ADPF 调度策略实现差异
- OEM 如何覆写 ADPF 默认行为

<!-- outline-end -->

> 本节内容待加工。
