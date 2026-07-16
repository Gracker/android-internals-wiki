---
title: "Bitmap 解码管线性能与 ImageDecoder 实战"
chapter: "22.35"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ['bitmap', 'image-decoder', 'decode-pipeline', 'hardware-bitmap', 'image-format']
related_chapters: ['22.06', '22.17', '23.02']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "章节深挖"
---

# 22.35 Bitmap 解码管线性能与 ImageDecoder 实战

<!-- outline-start -->
## 要点

### 🔹 ImageDecoder API 架构与 BitmapFactory 对比
### 🔹 硬件位图 (Hardware Bitmap) 解码路径与 GPU 上传
### 🔹 图片格式解码性能：PNG / WebP / HEIF / AVIF 对比
### 🔹 解码线程调度：专用线程 vs 线程池 vs 协程
### 🔹 内存映射解码与 mmap 在图片加载中的应用
### 🔹 inBitmap 复用对解码性能与内存的双重收益
### 🔹 Bitmap 内存模型：Android 17 下的 ashmem 与 dma_buf
### 🔹 解码性能指标采集：FrameMetrics + Perfetto 双轨方案

## 扩展

### 🔸 九宫格/瀑布流场景的解码调度策略
### 🔸 Glide / Coil / Picasso 解码管线对比
### 🔸 Android 17 ImageDecoder 新增 API 与行为变更

<!-- outline-end -->

> 本节内容待加工。

<!--
缺口分析摘要：ImageDecoder API 性能仅 2 次提及。现有 06-image-loading 偏重图片库使用，缺少解码管线层面的性能分析。需覆盖：ImageDecoder vs BitmapFactory 性能差异、硬件位图解码路径与限制、WebP/AVIF/HEIF 解码耗时对比、解码线程调度、内存映射解码、inBitmap 复用与解码性能、inSampleSize/inDensity 计算优化。
评分：15/20 ({'素材丰富度': 3, '相关性': 5, '读者需求度': 4, '时效性': 3})
-->
