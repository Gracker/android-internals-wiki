---
title: "Media Performance Class 与设备能力分级"
chapter: "17.6"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37); Android 11 可通过 Jetpack Core 回退读取"
tags: [media-performance-class, device-capability, oem, camera, media]
related_chapters: ["8.8", "14.9", "17.2", "18.14", "25.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "官方文档"
source_candidates:
  - "https://developer.android.com/topic/performance/performance-class"
  - "https://source.android.com/docs/compatibility/16/android-16-cdd"
  - "https://source.android.com/docs/compatibility/cts/media-cts"
  - "https://android-developers.googleblog.com/2022/03/using-performance-class-to-optimize.html"
---

# 17.6 Media Performance Class 与设备能力分级

<!-- outline-start -->
## 要点

### 🔹 能力等级的读取边界
建立 `Build.VERSION.MEDIA_PERFORMANCE_CLASS`、Jetpack Core `DevicePerformance` 与 Android 版本之间的关系，说明返回值为 0、随 OTA 提升、同一 Android 版本设备能力不同三类边界。

### 🔹 CDD 约束覆盖哪些硬件能力
按 CDD 拆出 Media Performance Class 覆盖的相机、编解码、显示、内存、存储和系统性能约束，只列能力类别，不复述 CDD 条款原文。

### 🔹 App 侧按能力分级做功能降级
给出视频拍摄、相机预览、图片处理、WebView/Hybrid、端侧 AI 推理等场景的分级策略：高等级启用高规格体验，低等级走保守参数，不用机型白名单替代能力判断。

### 🔹 线上指标要携带设备能力标签
APM 上报中增加 Media Performance Class、SoC、内存、存储和刷新率标签，用于区分真实性能回归、设备能力差异和厂商配置差异。

### 🔹 OEM 差异与 CTS 证据链
说明同一 SoC 不必然对应同一能力等级，厂商 OTA 可能提升等级；分析时优先采用系统返回值、CTS / Media CTS / Camera ITS 证据和实机指标。

### 🔹 与媒体、相机和渲染章节的引用关系
本节只处理设备能力分级和工程决策，媒体管线详见 8.8 节，相机 Trace 详见 14.9 节，Camera 渲染管线详见 18.14 节。

## 扩展

### 🔸 Android 17 媒体与相机新能力的分级接入
后续补充 Android 17 专业媒体/相机能力与 Media Performance Class 的关系，区分平台新 API、设备能力声明和业务启用策略。

### 🔸 低等级设备的体验保护策略
补充低等级设备上的帧率、分辨率、码率、滤镜、后台任务和上传压缩策略，避免把能力分级写成只服务高端机的开关。

<!-- outline-end -->

> 本节内容待加工。
