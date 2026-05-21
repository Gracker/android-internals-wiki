---
title: "Choreographer Buffer Stuffing Recovery 与帧节拍修正"
chapter: "2.25"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [rendering, choreographer, bufferqueue, vsync, android16]
related_chapters: ["2.4", "2.13", "2.16", "13.15", "18.20"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "研究素材/AOSP结构"
---

# 2.25 Choreographer Buffer Stuffing Recovery 与帧节拍修正

<!-- outline-start -->
## 要点

### 🔹 Buffer Stuffing 问题边界
说明应用端等待 Buffer 释放时，`dequeueBuffer` 阻塞如何把单帧耗时扩散成后续帧节拍错位；区分 BufferQueue producer 侧等待、SurfaceFlinger latch 延迟和应用主线程 traversal 本身耗时。

### 🔹 Android 16 的 Choreographer 新增状态机
整理 `Choreographer.BufferStuffingState`、`RecoveryAction`、`isStuffed`、`isRecovering`、`numberWaitsForNextVsync` 的职责边界，说明它们只负责帧调度恢复，不直接改变 BufferQueue 容量。

### 🔹 onWaitForBufferRelease() 的触发条件
定位 `Choreographer.onWaitForBufferRelease(long durationNanos)` 的调用语义：等待 Buffer 释放时间超过半帧周期时标记 stuffing，并进入后续 recovery 判断。

### 🔹 OFFSET 与 DELAY_FRAME 两类恢复动作
拆分负偏移提前下一帧和主动延迟一帧的适用条件，说明二者分别解决延迟累积和时间戳回退风险。

### 🔹 与 VSync、FrameTimeline 和 skipped frame 的关系
解释恢复机制如何接入 `doFrame()`、`FrameDisplayEventReceiver` 和 callback 队列；补充 Perfetto 中可观察的 VSync、Choreographer、FrameTimeline 与 BufferQueue 等信号。

### 🔹 版本边界与兼容判断
对比 Android 14/15/16/17：Android 16 起存在该机制；Android 15 及之前只能从 BufferQueue、SurfaceFlinger 与应用主线程侧做诊断。

### 🔹 实战诊断路径
给出卡顿 Trace 中识别 Buffer Stuffing 的步骤：先看 producer 侧等待点，再看 Choreographer 帧时间修正，最后回到 SurfaceFlinger latch/present 证据。

## 扩展

### 🔸 与 SurfaceFlinger 双缓冲/三缓冲策略的交互
记录待验证问题：不同 Buffer slot 数量、HWC 合成压力和 releaseBuffer 时机是否会影响 RecoveryAction 分布。

### 🔸 与 FPSDivisor、可变刷新率的边界
补充待验证方向：降低目标帧率、可变刷新率切换和 Buffer Stuffing Recovery 是否存在互相放大或抵消的场景。

### 🔸 Perfetto SQL 识别模板
后续可扩展为 SQL 模板，关联 Choreographer slice、FrameTimeline、BufferQueue producer 等待点和 SurfaceFlinger present 时刻。

<!-- outline-end -->

> 本节内容待加工。
