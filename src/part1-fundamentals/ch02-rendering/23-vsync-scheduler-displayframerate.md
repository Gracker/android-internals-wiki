---
title: "SurfaceFlinger VSync Scheduler 与 DisplayFrameRate 策略"
chapter: "2.23"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [surfaceflinger, vsync, frame-rate, arr, rendering]
related_chapters: ["2.3", "2.18", "2.19", "18.19", "13.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "研究素材/官方文档/AOSP结构"
gap_score: 16
material_count: 4
sources:
  - type: research
    path: "DeepResearch/2026-05-17-surfaceflinger-vsync-scheduler-frame-rate.md"
  - type: official
    path: "https://source.android.com/docs/core/graphics/frame-pacing"
  - type: official
    path: "https://source.android.com/docs/core/graphics/arr"
  - type: official
    path: "https://developer.android.com/media/optimize/performance/frame-rate"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/"
---

# 2.23 SurfaceFlinger VSync Scheduler 与 DisplayFrameRate 策略

<!-- outline-start -->
## 要点

### 🔹 硬件 VSync、VSyncDispatch 与 Scheduler 的分工
梳理 `HW_VSYNC_0` 进入 SurfaceFlinger 后，如何经过 `VSyncDispatch`、`Scheduler` 与 callback 分发给 App / SF 两条渲染循环。

### 🔹 VSyncPredictor 如何替代旧 DispSync 经验模型
解释预测模型需要的采样、period / phase 拟合、resync 条件，以及预测误差如何影响 latch 与 present deadline。

### 🔹 App VSync offset、SF VSync offset 与帧预算拆分
把输入处理、主线程遍历、RenderThread 提交、SurfaceFlinger latch / compose / present 放到同一条时间线里，说明 offset 为什么会改变端到端延迟。

### 🔹 DisplayFrameRate 请求与系统刷新率选择
对齐 `Surface.setFrameRate()` / `Window.setFrameRate()`、兼容性参数、video / game / UI 场景的差异，以及 SurfaceFlinger 如何在多 layer 请求之间选择刷新率。

### 🔹 Android 15+ ARR 与 FrameRateEligibility 边界
整理 adaptive refresh rate、离散 VSync step、应用声明能力、GameManager 介入和设备策略之间的关系，避免把内容帧率、目标帧率和显示刷新率混成一个概念。

### 🔹 Perfetto 中识别 VSync 调度问题
列出 FrameTimeline、SurfaceFlinger、Choreographer、DisplayEventReceiver、HWC / present fence 等观察点，区分 App late、SF late、HWC present late 和刷新率切换带来的抖动。

## 扩展

### 🔸 VSyncPredictor 与 DispSync 的版本边界
核对 Android 11-17 的类名、启用路径和回退条件。

### 🔸 视频 24fps / 30fps 内容在 90Hz / 120Hz 设备上的刷新率选择
补充 media frame rate 文档中的典型场景，并和 8.8 多媒体管线性能交叉引用。

<!-- outline-end -->

> 本节内容待加工。
