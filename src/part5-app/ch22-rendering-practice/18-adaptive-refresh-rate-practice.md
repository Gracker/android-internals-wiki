---
title: "Adaptive Refresh Rate 与帧率策略实战"
chapter: "22.18"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [adaptive-refresh-rate, frame-rate, jank, power, android16]
related_chapters: ["2.18", "2.19", "7.8", "22.2", "25.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "官方文档/章节深挖/素材驱动"
gap_score: "18/20"
sources:
  - type: official
    path: "https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate"
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
---

# 22.18 Adaptive Refresh Rate 与帧率策略实战

<!-- outline-start -->
## 要点

### 🔹 ARR 的应用侧收益边界
说明 ARR 解决的是高刷新率驻留和模式切换卡顿问题，应用侧仍要管理内容帧率、触摸 boost 和动画节奏。

### 🔹 Android 15/16 API 版本矩阵
覆盖 Android 15 ARR 基础能力、Android 16 `hasArrSupport()`、`getSuggestedFrameRate(int)` 与 `getSupportedRefreshRates()` 的使用边界。

### 🔹 列表、短动画与低频动态内容策略
结合 RecyclerView 1.4 settling 支持、进度条、音频可视化、轮播图和静态阅读场景设计帧率策略。

### 🔹 `Window.setFrameRateBoostOnTouchEnabled()` 的取舍
说明禁用触摸 boost 的适用场景、误用风险和交互延迟验证方式。

### 🔹 Perfetto 观测与线上指标
用 FrameTimeline、display refresh rate、SurfaceFlinger 和功耗数据验证降刷新率是否引入 jank。

### 🔹 跨设备降级与灰度
处理 HAL 支持差异、OEM 策略差异、Jetpack 支持进度和线上开关。

## 扩展

### 🔸 ARR 与游戏/视频帧率策略的差异
[待补充]

### 🔸 ARR 与 Compose 动画、LazyList 滚动的协同
[待补充]

### 🔸 高刷新率设备的功耗 A/B 设计
[待补充]

<!-- outline-end -->

> 本节内容待加工。
