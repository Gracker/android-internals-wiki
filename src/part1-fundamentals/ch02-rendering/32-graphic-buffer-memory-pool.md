---
title: "GraphicBuffer 内存池化与 BufferQueue Slot 复用机制"
chapter: "2.32"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [GraphicBuffer, BufferQueue, BufferQueueCore, GraphicBufferAllocator, Gralloc, DMA-BUF, 内存池, slot 复用, SurfaceFlinger, VkRenderEngine]
related_chapters: ["2.10", "2.13", "2.15", "2.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-10"
gap_source: "DeepResearch 素材驱动 + research-gaps.md GPU 内存管理盲区"
---

# 2.32 GraphicBuffer 内存池化与 BufferQueue Slot 复用机制

<!-- outline-start -->
## 要点

### 🔹 GraphicBufferAllocator：注册表而非内存池
- sAllocList 的 KeyedVector<buffer_handle_t, alloc_rec_t> 数据结构与统计用途
- GraphicBufferAllocator 单例模式与 Gralloc5Allocator/Gralloc4Allocator 分流
- getTotalSize() 的语义：进程级已分配显存总量，非池容量
- ATRACE 计数器 mem.gralloc.buffers / mem.gralloc.allocations 的 Perfetto 可观测路径

### 🔹 BufferQueueCore 四组 Slot 集合：AOSP 唯一真正的 buffer pool
- mFreeSlots / mFreeBuffers / mActiveBuffers / mUnusedSlots 的正交维护
- NUM_BUFFER_SLOTS=64 硬上限与 mAllowExtendedSlotCount 扩容标志
- BufferQueueCore 构造函数的 slot 初始化逻辑（numStartingBuffers 分流）
- getMaxBufferCountLocked() 的计算公式：mMaxAcquiredBufferCount + mMaxDequeuedBufferCount + (async ? 1 : 0)

### 🔹 dequeueBuffer 的 reuse-or-reallocate 分流机制
- waitForFreeSlotThenRelock() 的 slot 获取与阻塞等待
- buffer->needsReallocation(width, height, format, layerCount, usage) 的五维比较
- BUFFER_NEEDS_REALLOCATION flag 的返回与 requestBuffer() 的触发链
- Fast path（稳定帧）vs Cold path（几何变更）的性能差异（< 0.1ms vs 10-50ms）

### 🔹 clearBufferSlotLocked 不释放显存的设计
- slot 状态重置（mGraphicBuffer=nullptr, mBufferState 重置）vs buffer handle 保留
- SurfaceView/TextureView 反复创建销毁导致显存累计的根因
- 进程死亡时 GraphicBufferAllocator 析构链路

### 🔹 Gralloc AIDL 与 Vendor 池化责任分界
- Gralloc5Allocator 的 AIDL allocate2(BufferDescriptorInfo, count) 批量分配语义
- AOSP 接口定义 vs vendor HAT 内部池化实现的责任边界
- 跨 SoC 池化实现差异矩阵（Qualcomm kgsl / Mali / PowerVR / Pixel Tensor）

### 🔹 16KB Page Size 对 GraphicBuffer 分配的影响
- reservedSize 字段的页对齐取整成本
- 小尺寸 buffer（图标 atlas）在 16KB 设备上的内存成本放大
- BufferDescriptorInfo 中 reservedSize 在 Android 15+ 的引入与 Android 17 的行为

## 扩展

### 🔸 Vulkan VkRenderEngine 的内存池策略
- AMD VMA (Vulkan Memory Allocator) 在 Android 17 VkRenderEngine 中的角色
- vkd 驱动层的 VkDeviceMemory 池化与 AOSP 不参与池策略的设计

### 🔸 ANGLE on Vulkan 的 dual cache 合并机制
- ANGLE 翻译 GLES → Vulkan 时的 buffer pool 自维护
- BQ_GL_FENCE_CLEANUP flag 守门的 EGL fence 清理路径

### 🔸 mAdditionalOptionsGenerationId 与 Android 17 扩展分配选项
- COM_ANDROID_GRAPHICS_LIBGUI_FLAGS(BQ_EXTENDEDALLOCATE) flag 门控
- mAdditionalOptions 沿 allocRequest 透传到 Gralloc AIDL 的机制

<!-- outline-end -->

> 本节内容待加工。

## 素材来源

- [来源: DeepResearch/2026-07-09-android17-graphic-buffer-memory-pool-design.md] — android-17.0.0_r1 源码级调研
- [结构参考: §2.10 GPU 渲染深入 — 🔸 GPU 内存管理 扩展点]
- [结构参考: §2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — libdmabufheap 无通用池 contract]
- [research-gaps.md 2026-07-06 GPU 内存管理优化策略盲区]
