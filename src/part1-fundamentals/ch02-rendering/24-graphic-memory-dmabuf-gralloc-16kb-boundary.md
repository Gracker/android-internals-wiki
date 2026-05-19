---
title: "Android 16/17 图形内存分配边界：DMA-BUF、Gralloc 与 16KB Page"
chapter: "2.24"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [dmabuf, gralloc, bufferqueue, graphic-memory, 16kb-page-size]
related_chapters: ["2.13", "2.15", "2.16", "4.7", "14.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "每日信息/DeepResearch/官方文档/AOSP结构"
source_candidates:
  - "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-19-android-dmabuf-gralloc-16kb-boundary.md"
  - "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - "https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps"
---

# 2.24 Android 16/17 图形内存分配边界：DMA-BUF、Gralloc 与 16KB Page

<!-- outline-start -->
## 要点

### 🔹 这节解决的问题
厘清图形 buffer 从 App / Framework 到 DMA-BUF heap 的分配边界，区分 AOSP 通用路径、kernel 页面大小约束、厂商 gralloc 策略和未验证的性能结论。

### 🔹 ION 到 DMA-BUF heap 的迁移路径
围绕 `libdmabufheap`、`BufferAllocator::Alloc()`、`/dev/dma_heap/*` 建立用户态分配入口，说明它和旧 `ion_alloc_fd()` 的参数模型差异。

### 🔹 Gralloc4 / IMapper 的描述符与厂商参数
梳理 `GraphicBuffer`、`IAllocator`、`IMapper`、`BufferDescriptor` 的职责边界，重点确认 `additionalOptions` 只传递厂商参数，不等同于跨设备统一的 16KB 对齐策略。

### 🔹 BufferQueue 中的图形 buffer 传递路径
从 `BufferQueueProducer` / `BufferQueueConsumer` 出发，说明 producer、consumer、SurfaceFlinger 之间共享 buffer handle、fence 和 fd 的路径，并回连 2.13 BufferQueue 与 2.16 Sync Fence。

### 🔹 16KB Page Size 对图形内存的真实影响
把 ELF alignment、kernel page size、DMA-BUF heap 分配粒度、gralloc 物理对齐拆开，避免把系统 16KB 支持直接写成所有图形 buffer 都获得性能收益。

### 🔹 AOSP 通用能力与厂商实现边界
用表格区分 AOSP 可验证路径、Pixel / SoC vendor gralloc 实现、设备私有 heap 节点和需要实机验证的指标。

### 🔹 可观测信号与排障入口
整理 `dumpsys SurfaceFlinger`、Winscope、Perfetto FrameTimeline / SurfaceFlinger slice、buffer count、fd 数、RSS/PSS/graphics memory 的组合观察方法。

## 扩展

### 🔸 Binder fd array 与 GraphicBuffer 跨进程传递
追踪 `GraphicBuffer::flatten()` / `unflatten()`、Binder native handle 与 fd 安装路径，确认是否存在可直接影响 BufferQueue 高频传递成本的批量 fd 机制。

### 🔸 libdmabufheap pooling 与 buffer 复用
确认 AOSP `libdmabufheap` 是否提供通用 buffer pooling，或只是厂商 allocator / gralloc 层面的复用策略。

### 🔸 设备级 16KB 图形内存验证清单
建立 Pixel / Qualcomm / MediaTek / Mali gralloc 的检查项：page size、heap 节点、对齐函数、buffer stride、allocation logs、SF/HWC 侧可见指标。

<!-- outline-end -->

> 本节内容待加工。
