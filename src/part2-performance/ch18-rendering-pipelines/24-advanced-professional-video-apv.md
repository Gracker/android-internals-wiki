---
title: "Advanced Professional Video 与专业视频编解码管线"
chapter: "18.24"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [media, apv, mediacodec, professional-video, android16]
related_chapters: ["18.23", "14.9", "24.13", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "官方文档/AOSP结构/素材驱动"
gap_score: "14/20"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: official
    path: "https://developer.android.com/media/optimize/performance/codec"
---

# 18.24 Advanced Professional Video 与专业视频编解码管线

<!-- outline-start -->
## 要点

### 🔹 APV 的定位与适用场景
区分 APV 面向专业录制、剪辑、后期交换的 intra-frame 高码率工作流，避免把它和普通在线视频播放编码混在一起。

### 🔹 APV 422-10 Profile 的能力边界
覆盖 YUV 422、10-bit、最高 2Gbps 目标码率、HDR 与多视图/辅助视频等能力，以及设备支持探测方式。

### 🔹 MediaCodec 能力探测与降级策略
围绕 codec list、profile / level、hardware acceleration、performance point 和 vendor codec 差异设计能力矩阵。

### 🔹 编码、解码与存储 I/O 成本
建立 2K/4K/8K 高码率素材的 CPU、GPU、内存带宽、存储吞吐和发热风险检查项。

### 🔹 专业视频 App 的管线设计
拆分录制、预览、代理文件、后台转码、导出和缓存清理，不把所有工作压到交互路径。

### 🔹 Perfetto 与媒体日志观察点
明确 MediaCodec、Camera、Surface、AudioTrack、I/O 和 thermal 轨道的观察顺序。

## 扩展

### 🔸 APV 与 HEVC/AV1/ProRes 工作流对照
[待补充]

### 🔸 OpenAPV 参考实现与 Android 平台支持边界
[待补充]

### 🔸 高码率素材的线上失败率与设备分桶
[待补充]

<!-- outline-end -->

> 本节内容待加工。
