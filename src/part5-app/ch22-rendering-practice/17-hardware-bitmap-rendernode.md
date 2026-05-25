---
title: "Hardware Bitmap 与 RenderNode 缓存策略"
chapter: "22.17"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [rendering, bitmap, rendernode, hwui, surfaceflinger]
related_chapters: ["2.5", "2.13", "2.15", "7.10", "22.6", "23.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "素材驱动/AOSP结构/官方文档"
sources:
  - type: aosp
    path: "frameworks/base/libs/hwui/hwui/Bitmap.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/HardwareBitmapUploader.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/graphics/images/optimization"
  - type: official
    path: "https://developer.android.com/topic/performance/rendering/profile-gpu"
  - type: research
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-02-hardware-bitmap-rendernode-surfaceflinger-composition.md"
---

# 22.17 Hardware Bitmap 与 RenderNode 缓存策略

<!-- outline-start -->
## 要点

### 🔹 Hardware Bitmap 解决的问题
说明 `Bitmap.Config.HARDWARE` 的适用前提：像素只用于屏幕绘制、无需 CPU 读写、希望减少 Java heap 占用与首帧 GPU texture upload 抖动。区分它与普通 `ARGB_8888` Bitmap、`Bitmap.prepareToDraw()`、图片库预加载策略的边界。

### 🔹 AHardwareBuffer、SkImage 与 HWUI 绘制路径
梳理 Hardware Bitmap 从 `HardwareBitmapUploader` 分配 `AHardwareBuffer`，到 `SkImages::DeferredFromAHardwareBuffer` 暴露给 Skia，再被 RenderNode display list 记录和 RenderThread 执行的路径。标注源码验证点，不照搬调研稿代码。

### 🔹 RenderThread 中被省掉的 upload 成本
解释普通 Bitmap 首次绘制可能在 RenderThread 出现 texture upload，而 Hardware Bitmap 主要省掉这一段同步成本。给出 Perfetto 观察口径：`Upload ... Texture`、`DrawFrame`、`syncFrameState`、RenderThread CPU slice 与帧耗时对照。

### 🔹 不能直接交给 SurfaceFlinger 合成
澄清常见误判：Hardware Bitmap 仍然是应用 Surface 内部的绘制资源，通常不会变成独立 layer 交给 SurfaceFlinger。只有 SurfaceView、TextureView、ImageReader、MediaCodec 等 Surface 生产者路径才会改变 BufferQueue 与合成边界。

### 🔹 内存、FD 与 Low RAM 风险
覆盖 Hardware Bitmap 的资源代价：GPU/graphics memory 占用、AHardwareBuffer/文件描述符压力、不可变和不可 CPU 读写约束、低内存设备上的降级策略，以及图片库中禁用或限制 Hardware Bitmap 的场景。

### 🔹 工程选型与回退策略
形成应用层实践清单：大图首屏、列表预取、圆角/滤镜/截图/共享元素转场、Compose `ImageBitmap.prepareToDraw()`、Glide/Coil 配置、线上灰度指标与回退开关。

## 扩展

### 🔸 与 22.6 图片加载章节的分工
本节只讲 Hardware Bitmap 与 RenderNode/HWUI 路径，解码缓存、采样率、磁盘缓存、图片格式选择详见 22.6 节。

### 🔸 与 23.2 Bitmap 内存治理的交叉
补充 graphics memory 与 Java heap 的统计差异，避免把 Hardware Bitmap 的 Java heap 下降误判为总内存下降。

### 🔸 与 2.13/2.15 图形缓冲章节的交叉
只引用 BufferQueue、DMA-BUF、Gralloc 的机制章节，不重复展开底层图形内存原理。

<!-- outline-end -->

> 本节内容待加工。
