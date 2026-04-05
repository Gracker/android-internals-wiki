---
title: "Android Camera 性能与 Perfetto 分析"
chapter: "14.9"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ['camera', 'Perfetto', 'performance', 'buffer-queue', 'preview-stutter']
related_chapters: ['2.13', '13.5', '11.2']
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "素材索引（2 篇高质量未映射素材：Camera Perfetto 分析）"
---

# 14.9 Android Camera 性能与 Perfetto 分析

<!-- outline-start -->
## 要点

### 🔹 Camera 性能问题的分类
预览卡顿、拍照延迟、录像丢帧、内存压力——四大类 Camera 性能问题及其根因
### 🔹 Camera 管线的 Buffer 流转
Camera HAL → BufferQueue → SurfaceTexture → SurfaceView/TextureView 的缓冲区流转机制
### 🔹 在 Perfetto 中分析 Camera 性能
camera HAL track 的解读；BufferQueue 状态追踪；帧到达间隔异常的 SQL 查询
### 🔹 Camera 预览卡顿分析
Buffer 耗尽、SurfaceFlinger 合成延迟、GPU 纹理上传瓶颈的排查方法
### 🔹 Camera 功耗优化
Sensor 模式选择、帧率与分辨率的功耗权衡；高帧率预览的功耗代价

## 扩展

### 🔸 Camera2 API vs CameraX API 的性能差异
不同 API 层的抽象开销；CameraX 的性能自动优化机制
### 🔸 HAL3 管线延迟的深度分析
从 request → result 的完整延迟链路；ZSL（Zero Shutter Lag）的实现代价

<!-- outline-end -->

> 本节内容待加工。
