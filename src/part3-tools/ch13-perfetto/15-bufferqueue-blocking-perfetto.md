---
title: "BufferQueue 阻塞的 Perfetto 识别"
chapter: "13.15"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 36)"
tags: [perfetto, bufferqueue, frametimeline, jank, surfaceflinger, rendering]
related_chapters: ["2.13", "2.16", "7.15", "18.20"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/章节深挖"
gap_score: 19
material_count: 4
source_refs:
  - OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-bufferqueue-dequeueblocking-jank-perfetto.md
  - OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-bufferqueue-dequeueblocking-mechanism-detail.md
  - https://cs.android.com/android/platform/superproject/+/android14-release:frameworks/native/libs/gui/BufferQueueProducer.cpp
  - https://cs.android.com/android/platform/superproject/+/android14-release:frameworks/native/libs/gui/BufferQueueConsumer.cpp
---

# 13.15 BufferQueue 阻塞的 Perfetto 识别

<!-- outline-start -->
## 要点

### 🔹 从 FrameTimeline 定位 Buffer Stuffing
说明 `actual_frame_timeline_slice`、`jank_type = BufferStuffing`、surface token、layer name 与 App/SF 帧的对应关系。

### 🔹 RenderThread 上的 dequeueBuffer 阻塞特征
整理 `dequeueBuffer` slice 变长、waitForFreeSlotThenRelock、futex/condition wait、调用栈采样的组合判断。

### 🔹 BLASTBufferQueue 与 QueuedBuffer 轨道
解释 Android 12+ BLAST 路径中 QueuedBuffer 计数变化和 release callback 对 App 侧的影响。

### 🔹 Producer/Consumer 两端的因果链
把 App queueBuffer、SurfaceFlinger latch、HWC present、releaseBuffer 串成可验证时间线。

### 🔹 视频列表与 SurfaceView 的场景化判断
给出播放器、CameraX、SurfaceView/TextureView 混用场景下的典型 trace 形态。

### 🔹 误判边界与排查顺序
区分 BufferQueue 阻塞、GPU fence 等待、主线程布局耗时、Binder 回调阻塞。

## 扩展

### 🔸 Android 14 BUFFER_RELEASE_CHANNEL 影响
验证精确 release 通知对虚假唤醒和锁竞争的影响。

### 🔸 Perfetto SQL 模板
整理 FrameTimeline + thread_state + slice 关联查询。

<!-- outline-end -->

> 本节内容待加工。
