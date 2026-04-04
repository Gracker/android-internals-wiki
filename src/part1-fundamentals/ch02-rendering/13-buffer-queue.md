---
title: "图形缓冲区管理 (BufferQueue)"
chapter: "2.13"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 36)"
tags: [BufferQueue, BufferQueueLayer, GraphicBuffer, Surface, 渲染管线, BlastBufferQueue]
related_chapters: ["2.1", "2.5", "2.6", "2.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+研究素材"
gap_score: "14/20"
---

# 2.13 图形缓冲区管理 (BufferQueue)

<!-- outline-start -->
## 要点

### 🔹 BufferQueue 核心模型
Producer-Consumer 模式：App（Producer）通过 Surface dequeueBuffer入队，SurfaceFlinger（Consumer）通过 acquireBuffer 消费

### 🔹 GraphicBuffer 分配与生命周期
GRALLOC 分配、跨进程共享（handle/fd）、引用计数（AtomicInteger）

### 🔹 BlastBufferQueue 演进
Android 10 引入取代 BufferQueue 的事务化模型：acquire/release 与 SurfaceControl 事务绑定

### 🔹 Triple Buffering 与缓冲区策略
双缓冲 vs 三缓冲的取舍：减少 vs 内存占用

### 🔹 BufferQueue 在 Perfetto 中的表现
如何通过 Trace 诊断缓冲区相关问题（ dequeue 阻塞、 acquire 延迟）

## 扩展

### 🔸 BufferState 状态机详解
DEQUEUED → QUEUED → ACQUIRED → RELEASED 完整转换

### 🔸 不同 Surface 类型的缓冲区差异
SurfaceView / TextureView / WindowSurface / InputSurface
<!-- outline-end -->

> 本节内容待加工。缺口评分：14/20。素材丰富度：3 篇。与全书目标直接关联渲染管线核心。
