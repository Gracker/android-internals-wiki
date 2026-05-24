---
title: "音频 Offload 与 AudioTrack 精确控制功耗实践"
chapter: "25.18"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); AAudio compressed offload API 36+, AudioTrack flush/provenance API 37"
tags: [audio, power, aaudio, audiotrack, offload, android17]
related_chapters: ["1.16", "8.8", "18.23", "25.17", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "研究素材/官方文档/AOSP结构/Clippings结构参考"
gap_score: 16
material_count: 6
sources:
  - type: clipping
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: research
    path: "intake/research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md"
  - type: official
    path: "https://developer.android.com/ndk/reference/group/audio"
  - type: official
    path: "https://developer.android.com/reference/android/media/AudioTrack"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
---

# 25.18 音频 Offload 与 AudioTrack 精确控制功耗实践

<!-- outline-start -->
## 要点

### 🔹 场景边界：什么时候音频播放值得走 Offload
区分长音频播放、短音效、语音/助手、低延迟互动和后台播放场景，明确 Offload 适合压缩音频长时间播放，低延迟互动仍优先关注 AAudio/MMAP 与缓冲区策略。

### 🔹 AAudio compressed Offload 的能力探测
围绕 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED`、压缩格式、设备能力和 `AAudioStream_getPerformanceMode()` 建立探测流程，避免把请求 Offload 等同于实际走到 DSP 路径。

### 🔹 AudioTrack Offload 的 API 37 新边界
覆盖 `getCodecProvenance()`、`getFlushWrittenFramesFromPositionSupport()`、`flushWrittenFramesFromPosition(long, int)`、`FLUSH_FROM_ACCURACY_EXACT` / `BEST_EFFORT`，说明它们对音频定位、切歌、广告插入和有声书断点续播的影响。

### 🔹 功耗收益的验证方式
用 CPU 时间、音频线程唤醒、batterystats、Perfetto power/audio 相关轨道和播放器侧指标验证收益；只记录可复现实验条件，不用单次主观听感下结论。

### 🔹 延迟、音质与兼容性代价
说明 Offload 可能带来的 seek 精度、音效链、倍速播放、空间音频、设备 HAL 差异和 回退代价，给出「可开启」「灰度开启」「禁用」三档策略。

### 🔹 Assistant 与后台音频的版本交叉
衔接 Android 17 `USAGE_ASSISTANT` 专用音量流、`MODE_ASSISTANT_CONVERSATION` 和 25.17 后台音频 hardening，避免把音量流隔离、后台播放资格和 Offload 能力混在一起判断。

### 🔹 线上监控与回滚开关
设计播放器侧埋点：请求模式、实际性能模式、编解码器来源、回退原因、音频定位/flush 失败、播放中断和功耗实验分组，用于灰度与回滚。

## 扩展

### 🔸 Media3 / ExoPlayer 与平台 Offload 能力映射
梳理 Media3 offload 相关配置如何落到平台 `AudioTrack` / `AudioAttributes`，以及哪些播放器特性会阻断 Offload。

### 🔸 DSP Offload 与 Sound Dose / 音量安全边界
结合 Android 音频框架对压缩音频和 DSP 的处理边界，标注声压、音量安全和 HAL 上报能力的验证点。

### 🔸 不同 SoC / OEM 音频 HAL 差异
记录高通、联发科、Tensor 等设备上 Offload 支持和 fallback 的差异，只作为测试矩阵，不写未验证结论。

<!-- outline-end -->

> 本节内容待加工。
