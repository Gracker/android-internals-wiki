---
title: "图片加载与 Bitmap 性能优化"
chapter: "7.10"
section: "7.10"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [bitmap, image-decode, hardware-bitmap, glide, coil, image-loading, memory, jank]
related_chapters: ["7.4", "7.5", "7.8", "4.5", "2.10", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "AOSP结构+官方文档+读者需求"
gap_score: 17
---

# 7.10 图片加载与 Bitmap 性能优化

<!-- outline-start -->
## 要点

### 🔹 为什么图片加载是卡顿的头号嫌疑犯
- 列表滑动场景中，图片解码是掉帧的最大单一来源
- 一张 4000×3000 的 JPEG 解码后占用 48MB 内存（ARGB_8888）
- BitmapFactory.decode* 系列方法在主线程调用时的典型耗时
- 与 §7.4 典型场景分析、§7.8 RecyclerView 优化的关联

### 🔹 BitmapFactory 与 ImageDecoder 的内部机制
- BitmapFactory 解码流程：读取文件 → 解析头部 → 分配内存 → 解码像素
- BitmapFactory.Options 的关键参数：inSampleSize、inJustDecodeBounds、inBitmap、inPreferredConfig
- Android 9 (API 28) ImageDecoder 替代 BitmapFactory 的优势
- inBitmap 复用机制如何减少 GC 压力
- 各 Bitmap.Config (ARGB_8888/RGB_565/HARDWARE/ALPHA_8) 的内存开销对比

### 🔹 Hardware Bitmap 的性能优势与限制
- 从 Android 8.0 (API 26) 引入的 BITMAP_FLAG_HARDWARE
- Hardware Bitmap 像素数据存储在 GPU 内存而非 Java 堆
- 内存节省量化：一张 1000×1000 图片从 4MB → 接近 0 Java 堆占用
- 文件描述符限制（每个 hardware bitmap 消耗一个 fd）
- 限制：不支持软件渲染、Palette 提取、shared element transition
- Glide/Coil 对 hardware bitmap 的处理策略

### 🔹 图片格式解码性能对比
- JPEG/PNG/WebP/AVIF/GIF 的解码速度对比
- AVIF 在 Android 14+ 的系统级支持
- WebP 有损 vs 无损的解码时间差异
- 大图（>4MP）解码的 OOM 风险与 inSampleSize 策略
- PNG 逐行解码（interlaced）的性能影响

### 🔹 Glide 管线架构与性能调优
- Glide 请求生命周期：RequestBuilder → Engine → DecodeJob → Resource
- Glide 的内存缓存策略：LRU ResourceCache + LRU BitmapPool
- Glide 自动降采样（downsample）如何匹配 ImageView 尺寸
- Glide 的 BitmapPool 复用策略与 inBitmap 的配合
- RecycleView 中 Glide 的生命周期管理与 preload
- 常见配置误区：禁用缓存、错误的 ThreadPoolSize

### 🔹 Coil 管线架构与性能特性
- Coil 基于 Kotlin Coroutine 的异步架构
- Coil 的三级缓存：Memory → Disk → Network
- Coil 3.0 Multiplatform 支持
- Coil vs Glide 的内存模型差异
- Compose 中 AsyncImage 的性能特性

### 🔹 在 Perfetto 中定位图片解码卡顿
- BitmapFactory.decode* 在 Trace 中的表现
- 如何用 Perfetto SQL 查询大图解码事件
- GPU 内存压力导致 hardware bitmap 降级的 Trace 特征
- 结合 Android Studio Profiler 的 Native Memory 分析

## 扩展

### 🔸 图片 Exif 信息处理性能
- ExifInterface 的 I/O 开销
- 图片旋转处理对解码性能的影响
- [待补充]

### 🔸 Compose 中的图片性能
- AsyncImage vs SubcomposeAsyncImage 的性能差异
- rememberAsyncImagePainter 的 recomposition 开销
- [待补充]

### 🔸 图片后处理性能
- Bitmap.createBitmap 的内存拷贝开销
- Canvas 绘制到 Bitmap 的性能
- RenderScript → GPU Compute 的迁移
- [待补充]

<!-- outline-end -->

> 本节内容待加工。
