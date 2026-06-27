---
title: "FrameTracer 与 Graphics Frame Event 数据通路"
chapter: "13.19"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [perfetto, frametracer, graphics, buffer-lifecycle, surfaceflinger, gpu]
related_chapters: ["13.5", "13.14", "13.17", "2.6", "18.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "研究素材"
---

# 13.19 FrameTracer 与 Graphics Frame Event 数据通路

<!-- outline-start -->
## 要点

### 🔹 FrameTracer 与 FrameTimeline 的职责区分
FrameTracer（`android.surfaceflinger.frame`）追踪的是 buffer 在 GPU↔HWC 流水线上的生命周期事件（DEQUEUE → QUEUE → ACQUIRE_FENCE → LATCH → PRESENT_FENCE 等 13 种 BufferEventType），回答"buffer 卡在哪一步"。FrameTimeline（`android.surfaceflinger.frametimeline`）追踪的是每帧的预期/实际时间线与 jank 分类，回答"这一帧是否按时、为何延迟"。两者通过共享 buffer_id 和 frame_number 可在 trace processor 侧关联。

### 🔹 FrameTracer 的 13 种 BufferEventType 事件链
从 `FrameTracer.cpp` 源码（android-17.0.0_r1）注册的 Perfetto 数据源输出完整 buffer 生命周期：DEQUEUE → QUEUE → ACQUIRE_FENCE → LATCH → HWC_COMPOSITION_QUEUED → FALLBACK_COMPOSITION → PRESENT_FENCE → RELEASE_FENCE。每个事件携带 trace_cookie（layer 标识）、buffer_id、frame_number 三个关键字段。

### 🔹 Perfetto SQL 查询 FrameTracer 数据
FrameTracer 事件存储在 `android.surfaceflinger.frame` slice track 中，可通过 trace_processor SQL 查询 buffer 各阶段耗时。典型查询模式：按 layer_id 分组 → 计算每帧从 DEQUEUE 到 PRESENT_FENCE 的总延迟 → 定位卡在哪一步。

### 🔹 GPU Stall 与 HWC 决策诊断
FrameTracer 数据能区分三种典型异常：(1) ACQUIRE_FENCE 等待过长（GPU 渲染慢），(2) LATCH 到 HWC_COMPOSITION_QUEUED 间隔长（HWC 决策延迟），(3) FALLBACK_COMPOSITION 频繁触发（HWC 无法合成，回退到 GPU 合成）。

### 🔹 版本边界与数据源可用性
FrameTracer 在 Android 12 (API 31) 引入，Android 14+ 默认启用。Android 17 (API 37) 中新增了 FRAME_END 和 GPU_RENDERTHREAD_SUBMIT 事件类型，覆盖范围更完整。Android 11 及以下无法使用此数据源。

### 🔹 与 FrameTimeline 数据的联合分析
通过 buffer_id 和 frame_number 字段做 SPAN_JOIN 或 JOIN，可将 FrameTracer 的 buffer 阶段数据与 FrameTimeline 的 jank 分类数据拼合，得到完整诊断视图：某帧之所以 jank，是因为 GPU 渲染慢（ACQUIRE_FENCE 延迟）还是 HWC 合成失败（FALLBACK_COMPOSITION）。

## 扩展

### 🔸 FrameTracer 与 heapprofd/gpu_memory 联合观测
FrameTracer 记录 buffer 生命周期，结合 gpu_memory counter track 可观测 GPU 内存随帧的变化趋势，在 GPU 内存泄漏诊断中有独特价值。

### 🔸 FrameTracer 在游戏场景的限制
游戏通常使用 SurfaceView 或 ANativeWindow 直出，buffer 流转路径与普通 View 不同。FrameTracer 仍能追踪，但事件链更短（缺少部分 HWC 阶段），分析时需调整预期。

<!-- outline-end -->

> 本节内容待加工。
