---
title: "HDR 显示管线与色彩管理性能"
chapter: "2.31"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [HDR, color-management, display-pipeline, wide-color-gamut, surfaceflinger]
related_chapters: ["2.1", "2.6", "2.10", "2.22", "2.23"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-28"
gap_source: "AOSP结构+官方文档"
---

# 2.31 HDR 显示管线与色彩管理性能

<!-- outline-start -->
## 要点

### 🔹 Android 色彩管理管线概述
Android Color Management 架构：ColorSpace、ColorSpace.Rgb、Dataspace 枚举体系；Display P3、sRGB、BT.2020 色彩空间的渲染路径差异；SurfaceFlinger 的 ColorLayer 和 BufferLayer 色彩处理流程。

### 🔹 HDR 显示管线与 Tone Mapping
HDR10 / HLG / Dolby Vision 在 Android 上的支持状态；SurfaceFlinger 对 HDR 内容的 tone mapping 策略；SDR + HDR 混合显示时的亮度管理和合成功耗；HDR overlay 与 GPU 合成的性能差异。

### 🔹 Wide Color Gamut (WCG) 渲染开销
启用 wideColorGamut 模式对 GPU 渲染管线的影响；64位 vs 32位像素格式的带宽和填充率开销；Bitmap 硬件加速与色彩空间转换的隐含成本；Compose 中 ColorSpace 的传递与快照性能。

### 🔹 Display P3 色彩适配与性能权衡
Display P3 与 sRGB 的颜色转换开销（CPU/GPU）；未标记色彩空间的 Bitmap 自动转换行为；应用 P3 资源的加载和内存占用增量；UTM (Universal Tone Mapping) 在 Android 14+ 的引入和性能影响。

### 🔹 SurfaceFlinger 色彩管理性能优化
SurfaceFlinger 对不同 Dataspace 的合成路径选择；Force sRGB 模式的性能收益与画质损失；Display Color 管理的 HAL 层（ColorMode、RenderIntent）切换开销；Adaptive Color 在 Android 17 中的实现策略。

### 🔹 HDR 功耗性能权衡
HDR 显示模式对屏幕功耗的影响（峰值亮度提升 vs 电池消耗）；HDR 视频播放的端到端管线功耗分析；动态 tone mapping 的 CPU/GPU 开销与电池寿命的权衡；系统级 HDR 自动切换策略。

## 扩展

### 🔸 HDR 游戏渲染管线性能
Vulkan HDR 渲染、swapchain HDR 模式、GameMode HDR 偏好的性能特征。

### 🔸 色彩管理与 Compose First
Jetpack Compose 中的色彩空间感知渲染；Canvas API 在 WCG 模式下的行为；Animation 在色彩空间转换中的性能影响。

### 🔸 跨设备色彩一致性
不同 OEM 设备的色彩管理实现差异；色彩校准与 Display Calibration 对性能的影响；多显示器场景下的色彩管理（ch02.30 DisplayManagerService）。
<!-- outline-end -->

> 本节内容待加工。
