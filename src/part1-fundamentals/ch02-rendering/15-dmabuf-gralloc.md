---
title: "DMA-BUF、Gralloc 与跨进程图形内存共享"
chapter: "2.15"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [dma-buf, gralloc, graphicbuffer, zero-copy, ion, rendering, cross-process]
related_chapters: ["2.6", "2.13", "4.2", "1.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "素材驱动+AOSP结构+每日信息"
gap_score: "17/20"
---

# 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么需要跨进程零拷贝内存共享
- App 进程渲染一帧后，这帧数据需要传给 SurfaceFlinger（合成）再传给 Display HAL（显示），中间经过 2-3 次跨进程传递
- 如果每次传递都复制像素数据（一帧 1080p RGBA = 8MB），120Hz 下每秒需要 960MB 内存带宽，根本不可行
- DMA-BUF 提供的方案：只传「文件描述符」（一个整数），不传数据本身

### 🔹 锚点 2：DMA-BUF 机制核心原理
- Linux 内核的 buffer sharing framework（dma-buf.h）
- exporter（导出方）与 importer（导入方）模型
- fd 传递通过 Binder（BINDER_TYPE_FD）实现跨进程
- dma_buf_attach / dma_buf_map_attachment 的内核调用链
- 与 ION/DMA-HEAP 的关系：内存分配器的角色

### 🔹 锚点 3：Android Gralloc 与 GraphicBuffer
- Gralloc HAL（hardware/interfaces/graphics/mapper/allocator）
- GraphicBuffer = DMA-BUF fd + metadata（width/height/stride/format/usage）
- BufferQueue 中的 buffer 为什么叫 "slot"：每个 slot 持有一个 GraphicBuffer 引用
- 从 AOSP 源码看分配链路：GraphicBuffer → GraphicBufferAllocator → Gralloc Allocator HAL → DMA-BUF Heap

### 🔹 锚点 4：跨进程传递的实际路径
- App 通过 dequeueBuffer 获取 buffer → 渲染 → queueBuffer 提交
- BufferQueue 跨进程传递 buffer 的 Binder 事务
- SurfaceFlinger 通过 importBuffer 获取 buffer 的过程
- [图：一帧数据从 App GPU → BufferQueue → SurfaceFlinger → Display HAL 的传递路径，标注每步涉及的 DMA-BUF fd]

### 🔹 锚点 5：在 Perfetto 中的表现
- gfx memory track：GPU 内存使用量
- BufferQueue track：buffer 状态（DEQUEUED/QUEUED/FREE/ACQUIRED）
- SurfaceFlinger 的 Layer timeline：每个 Layer 对应一个 GraphicBuffer
- 当看到 buffer 传递延迟增大时的排查思路

### 🔹 锚点 6：常见问题与性能影响
- DMA-BUF fd 泄漏：buffer 无法释放导致 GPU 内存持续增长
- Gralloc 分配延迟：首次分配需要与内核交互，可能影响首帧渲染
- DMA-BUF sync 与 fence 的关系（交叉引用 §2.16 Sync Fence）
- Camera HAL 共享 buffer 的特殊场景（与渲染管线的带宽竞争）

## 扩展

### 🔸 扩展点 1：DMA-BUF Heap 的演进（Android 11+ 替代 ION）
- ION 到 DMA-BUF Heap 的过渡
- system heap / cma heap / gpu heap 的区别与用途

### 🔸 扩展点 2：不同 SoC 的 Gralloc 实现差异
- Qualcomm ION/Gralloc vs MediaTek vs Samsung
- OEM 自定义 heap 对性能的影响

### 🔸 扩展点 3：DMA-BUF 在 Camera/Video 管线中的应用
- Camera HAL 的 buffer 共享机制
- Video codec 的零拷贝解码输出

<!-- outline-end -->

> 本节内容待加工。
