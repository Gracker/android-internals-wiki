---
title: "Thermal 管控深度：从内核子系统到 ADPF 主动降频"
chapter: "5.12"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [thermal, throttling, ADPF, Thermal HAL, sustained performance, 游戏性能, 功耗]
related_chapters: ["5.5", "5.9", "8.9", "11.1", "16.4"]
section: "5.12"
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
gap_source: "官方文档+研究素材+AOSP结构+读者需求"
gap_score: "18/20"
---

# 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么 Thermal 管控是性能分析的关键维度
- 移动设备的物理约束：散热面积有限，SoC 功耗密度持续上升
- Thermal throttling 对帧率、启动时间、持续性能的直接影响
- 从"被动降频"到"主动温控"的范式转变
- 在 Perfetto 中观察 thermal throttling：CPU freq 突降、线程迁移、帧时间突增

### 🔹 锚点 2：Linux 内核 Thermal 子系统
- thermal_zone：温度传感器抽象层（CPU/GPU/Battery/Skin）
- thermal governor：step_wise、fair_share、power_allocator、user_space
- cooling_device：频率限制、CPU 核心离线、电压调节
- trip point：passive/active/hot/critical 四级温度阈值
- devfreq：GPU/NPU 等设备的动态频率调节与 thermal 联动
- [已验证: 来源见 Linux kernel source drivers/thermal/]

### 🔹 锚点 3：Android Thermal HAL 框架
- Thermal HAL 2.0 (AIDL)：IThermal.aidl 接口
- Temperature/TemperatureType/ThrottlingSeverity 数据结构
- 从 HIDL (Android 10-13) 到 AIDL (Android 14+) 的迁移
- PowerHAL 与 Thermal HAL 的协作关系
- OEM 实现差异：不同 SoC 厂商的 thermal 策略（Qualcomm/MediaTek/Samsung）

### 🔹 键点 4：ADPF Thermal API 与主动温控
- PowerManager.THERMAL_STATUS_NONE → THERMAL_STATUS_EMERGENCY 分级
- ThermalManager.OnThermalStatusChangedListener 回调机制
- thermal headroom 百分比预测：当前性能能维持多久
- Android 15 Power Efficiency Mode：hint session 的功耗优先路径
- Android 16/17 的 thermal balancing 改进

### 🔹 锚点 5：Sustained Performance API 与游戏场景
- WindowManager.setSustainedPerformanceMode() 的设计意图
- 游戏场景的 thermal 管控策略：分辨率动态调整、帧率目标降级
- Game Mode API 与 thermal 的联动：PERFORMANCE/SAVED/BATTERY
- MediaTek MAGT (MediaTek Adaptive Gaming Technology) 与 ADPF 的集成
- 量化数据：有效使用 ADPF 的游戏帧率提升 57%

### 🔹 锚点 6：在 Perfetto 中分析 Thermal 问题
- CPU frequency track：观察降频事件
- Thermal status track：设备 thermal 状态变化
- 帧时间与 thermal 状态的关联分析 SQL
- 区分 thermal throttling 与 CPU 调度导致的性能下降
- 实战案例：游戏场景下从 120fps → 60fps → 30fps 的 thermal 降级链

```sql
-- 查询 thermal 状态变化与帧时间关联
SELECT
  ts,
  name,
  CAST(dur / 1e6 AS FLOAT) AS duration_ms
FROM slice
WHERE name GLOB '*thermal*'
ORDER BY ts
LIMIT 50;
```

### 🔹 锚点 7：Thermal 优化的工程实践
- App 层：ADPF Thermal API 集成、动态画质调整策略
- Framework 层：JobScheduler 在 thermal 压力下的调度退避
- Kernel 层：power_allocator governor 参数调优
- OEM 层：VC (Vapor Chamber) 散热设计与软件协同
- 测试方法：如何复现和量化 thermal throttling

## 🔸 扩展 1：版本演进
- Android 7.0 Sustained Performance API 引入
- Android 8.0 Thermal HAL 1.0
- Android 10 Thermal HAL 2.0 (HIDL)
- Android 14 Thermal HAL AIDL 迁移
- Android 15 ADPF Power Efficiency Mode
- Android 16/17 Thermal Balancing + Adaptive Thermal

## 🔸 扩展 2：常见问题与误区
- 「thermal throttling 只影响游戏」→ 错误，相机、视频录制、导航、下载等场景同样受影响
- 「降低 CPU 频率就能降温」→ 不完全正确，需要考虑功耗-频率的非线性关系
- 「thermal 问题纯靠硬件解决」→ 软件策略（workload 调度、主动降频）同样重要

## 🔸 扩展 3：与其他机制的关系
- **5.4 DVFS**：DVFS 是 thermal 管控的执行手段之一
- **5.5 Thermal 管控**：本章是 5.5 的深度扩展
- **5.9 ADPF**：ADPF 是连接 App 与系统 thermal 策略的桥梁
- **8.9 游戏性能**：游戏是 thermal 问题最集中的场景
- **11.1 功耗模型**：thermal 和功耗是一体两面
<!-- outline-end -->

> 本节内容待加工。
