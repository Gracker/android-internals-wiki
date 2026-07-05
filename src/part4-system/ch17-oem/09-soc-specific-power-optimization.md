---
title: "SoC 特异性功耗优化策略：高通/联发科/三星"
chapter: "17.9"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [soc, power, qualcomm, mediatek, exynos, dvfs, scheduling, oem]
related_chapters: ["17.1", "17.2", "5.4", "5.5", "25.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "研究素材/知识盲区"
---

# 17.9 SoC 特异性功耗优化策略：高通/联发科/三星

<!-- outline-start -->
## 要点

### 🔹 高通骁龙 SoC 功耗管理特性
- Qualcomm LPM (Low Power Mode) 架构：ULTRALOW/LOW/MEDIUM 子模式与延迟矩阵
- DCVS (Dynamic Clock and Voltage Scaling) 在 Adreno GPU 上的策略
- `mdm_hsic` 5G 调制解调器在不同 RRC 状态下的功耗特征
- Snapdragon 8 Gen 系列的 cluster topology 与 EAS 调度器交互
- Power Hint Interface (PHI) 与 `vendor.qti.hardware.power` HAL

### 🔹 联发科 Dimensity SoC 功耗管理特性
- MediaTek MTLP (Multi-Tier Low Power) 与 CorePilot 调度算法
- HyperEngine 游戏引擎的帧率/功耗平衡策略
- Imagiq ISP 在拍照/录像时的功耗包络
- Dimensity 9000+ 的 tri-cluster big.LITTLE 与 task packing 策略

### 🔹 三星 Exynos SoC 功耗管理特性
- Exynos 2400/2500 的 custom CPU core 与 GNP (Global Power Management)
- Xclipse GPU (基于 AMD RDNA) 的功耗特征与 driver 差异
- Samsung LSI 的 SiP (System in Package) 热设计约束
- One UI 性能模式与 SoC 功耗策略的联动

### 🔹 跨厂商功耗优化最佳实践
- 通用策略：CPU affinity pinning、big.LITTLE task routing
- 厂商特异性 API 调用：PowerHAL hints、SchedTune boost
- `schedtune.boost` / `schedtune.prefer_idle` 调参对不同 SoC 的效果差异
- GPU frequency capping 在 Adreno vs Mali vs Xclipse 的效果对比

### 🔹 SoC 功耗基准测试方法论
- 制定跨 SoC 公平对比的测试框架（固定分辨率、统一工作负载）
- idle / sustained / peak 三种场景下的功耗模型
- 温度对 SoC 功耗的影响与 thermal throttling 触发时机
- 百度/腾讯/字节等大厂的 SoC 适配经验

### 🔹 Android 17 对 SoC 功耗管理的系统增强
- `PowerManager` 新增的 thermal headroom API
- AOSP generic PowerHAL 与 vendor HAL 的接口约定
- Android 17 对 OEM 自定义调度器的 `sched_ext` 约束

## 扩展

### 🔸 SoC 演进趋势与功耗策略前瞻
- 3nm/2nm 工艺节点的 leakage power 挑战
- 芯片级 NPU 的功耗隔离与电源域管理
<!-- outline-end -->

> 本节内容待加工。
