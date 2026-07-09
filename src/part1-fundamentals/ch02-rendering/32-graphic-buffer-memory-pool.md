---
title: "GraphicBuffer 内存池化与 BufferQueue Slot 复用机制"
chapter: "2.32"
section: "2.32"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
drafted_date: "2026-07-10"
drafted_by: "openclaw-task2a"
tags: [GraphicBuffer, BufferQueue, BufferQueueCore, GraphicBufferAllocator, Gralloc, DMA-BUF, 内存池, slot 复用, SurfaceFlinger, VkRenderEngine, 16KB Page Size]
related_chapters: ["2.10", "2.13", "2.15", "2.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-10"
gap_source: "DeepResearch 素材驱动 + research-gaps.md GPU 内存管理盲区"
sources:
  - type: aosp
    path: "frameworks/native/libs/ui/GraphicBufferAllocator.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueCore.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueProducer.cpp (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/ui/include/ui/BufferQueueDefs.h (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/native/libs/ui/Gralloc4.cpp (android-17.0.0_r1)"
  - type: deepresearch
    path: "DeepResearch/2026-07-09-android17-graphic-buffer-memory-pool-design.md"
---

# 2.32 GraphicBuffer 内存池化与 BufferQueue Slot 复用机制

Android 图形缓冲区的内存池化是一个容易被误解的话题。许多开发者假设 AOSP 维护了一个类似 Java 对象池的 "GraphicBuffer 池"，但实际架构更为分层：AOSP 框架层仅维护 **slot 级别的复用机制**（BufferQueueCore），而真正的显存分配/回收/池化策略完全由 SoC 厂商的 Gralloc HAL 实现。理解这一责任边界，是做图形内存优化和高负载场景分析的基本盘。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/ui/GraphicBufferAllocator.cpp]
[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BufferQueueCore.cpp]

---

## 要点

### 🔹 GraphicBufferAllocator：注册表而非内存池

**核心结论**：`GraphicBufferAllocator` 的 `sAllocList` 是一张"已分配句柄注册表"，用于统计和 dump，**不具备释放后回收复用能力**。

#### 单例与分流

`GraphicBufferAllocator` 是 AOSP 框架层的唯一 buffer 分配入口，采用 `ANDROID_SINGLETON_STATIC_INSTANCE` 单例模式。构造函数根据 `GraphicBufferMapper::getMapperVersion()` 分流到不同的底层 allocator：

```cpp
// frameworks/native/libs/ui/GraphicBufferAllocator.cpp (android-17.0.0_r1)
GraphicBufferAllocator::GraphicBufferAllocator()
    : mMapper(GraphicBufferMapper::getInstance()) {
    switch (mMapper.getMapperVersion()) {
        case GraphicBufferMapper::GRALLOC_5:
            mAllocator = std::make_unique<const Gralloc5Allocator>(...);
            break;
        case GraphicBufferMapper::GRALLOC_4:
            mAllocator = std::make_unique<const Gralloc4Allocator>(...);
            break;
        // ...
    }
}
```

Android 17 的主流设备全部走 Gralloc 5（AIDL 路径），Gralloc 4（HIDL 路径）仅保留兼容性。详见 §2.15「DMA-BUF、Gralloc 与跨进程图形内存共享」对 Gralloc AIDL 接口的完整分析。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/ui/Gralloc4.cpp]

#### sAllocList 的真实语义

```cpp
// 静态注册表，记录每个 buffer_handle_t 对应的分配元数据
Mutex GraphicBufferAllocator::sLock;
KeyedVector<buffer_handle_t,
    GraphicBufferAllocator::alloc_rec_t> GraphicBufferAllocator::sAllocList;

// alloc_rec_t 结构：
// struct alloc_rec_t {
//     uint32_t width;
//     uint32_t height;
//     uint32_t stride;
//     PixelFormat format;
//     uint32_t layerCount;
//     uint64_t usage;
//     uint64_t size;         // 分配大小（字节）
//     std::string requestorName;  // 请求者进程名
// };
```

`sAllocList` 的用途仅限于：
- `getTotalSize()`：遍历求和，统计当前进程已分配的显存总量
- `dumpsys SurfaceFlinger` / `dumpsys GraphicBufferAllocator`：输出分配明细
- ATRACE 计数器 `mem.gralloc.buffers`（总字节数）和 `mem.gralloc.allocations`（总笔数）

**关键区分**：`getTotalSize()` 返回的是"当前进程通过 GraphicBufferAllocator 已分配、尚未析构的 buffer 总量"，**不是 pool 容量**。当 GraphicBuffer 析构时，`deallocate()` 会从 `sAllocList` 中 erase 对应条目。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/ui/GraphicBufferAllocator.cpp]

#### Perfetto 可观测路径

在 Perfetto trace 中，搜索 `mem.gralloc.allocations` 和 `mem.gralloc.buffers` 两个 ATRACE counter track，可以实时观察 buffer 分配频率和累计显存。当 `mem.gralloc.allocations` 在短时间内密集增长而后续不回落，通常意味着 buffer 泄漏（GraphicBuffer 的 sp 引用未释放）。

[已验证: 官方文档, source.android.com/docs/core/graphics]

---

### 🔹 BufferQueueCore 四组 Slot 集合：AOSP 唯一真正的 buffer pool

**核心结论**：`BufferQueueCore` 维护的四组 slot 集合是 Android 框架层**唯一真正的 buffer 复用机制**，但其复用粒度是 slot（数组槽位），不是显存页。

#### 四组 slot 的正交维护

```cpp
// frameworks/native/libs/gui/BufferQueueCore.cpp (android-17.0.0_r1)
BufferQueueCore::BufferQueueCore()
    : mSlots(BufferQueueDefs::NUM_BUFFER_SLOTS),  // 固定 64 个槽位
      mFreeSlots(),       // set<int>: 空闲且无 buffer 的 slot
      mFreeBuffers(),     // set<int>: 空闲但携带 buffer 的 slot
      mUnusedSlots(),     // deque<int>: 完全未使用的 slot
      mActiveBuffers(),   // set<int>: 被 producer/consumer 持有的 slot
      mAllowExtendedSlotCount(false),  // Android 10+ 可扩展超 64
      mMaxBufferCount(BufferQueueDefs::NUM_BUFFER_SLOTS),
      mMaxAcquiredBufferCount(1),
      mMaxDequeuedBufferCount(1),
      // ...
```

四组集合的语义区别：

| 集合 | 含义 | 是否绑定 GraphicBuffer |
|------|------|----------------------|
| `mFreeSlots` | 可立即被 dequeue 的空闲 slot | ❌ 无 buffer |
| `mFreeBuffers` | buffer 已 release 但仍保留 | ✅ 有 buffer（可复用） |
| `mActiveBuffers` | 正在被 producer/consumer 使用 | ✅ 有 buffer |
| `mUnusedSlots` | 从未被实例化的 slot | ❌ 无 buffer |

构造时的初始化逻辑：

```cpp
int numStartingBuffers = getMaxBufferCountLocked();
// 默认: mMaxAcquiredBufferCount(1) + mMaxDequeuedBufferCount(1) + (async ? 1 : 0) = 2~3
for (int s = 0; s < numStartingBuffers; s++) {
    mFreeSlots.insert(s);     // 前几个 slot 注入空闲池
}
for (int s = numStartingBuffers; s < BufferQueueDefs::NUM_BUFFER_SLOTS; s++) {
    mUnusedSlots.push_front(s);  // 其余进入未使用池
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BufferQueueCore.cpp]

#### NUM_BUFFER_SLOTS=64 硬上限

```cpp
// frameworks/native/libs/ui/include/ui/BufferQueueDefs.h
static constexpr int NUM_BUFFER_SLOTS = 64;
```

这个 64 的硬上限自 Android 8（Oreo）引入（之前为 16）。实际使用的 slot 数量由 `getMaxBufferCountLocked()` 决定：

```cpp
int BufferQueueCore::getMaxBufferCountLocked() const {
    int maxBufferCount = mMaxAcquiredBufferCount + mMaxDequeuedBufferCount;
    if (mAsyncMode) {
        maxBufferCount++;  // 异步模式额外加 1
    }
    return maxBufferCount;
}
```

典型场景：

| 模式 | maxAcquired | maxDequeued | async | 总 slot 数 |
|------|-------------|-------------|-------|-----------|
| 双缓冲同步 | 1 | 1 | false | 2 |
| 三缓冲异步 | 1 | 1 | true | 3 |
| BLAST + triple buffering | 1 | 2 | true | 4 |

`mAllowExtendedSlotCount` 标志（Android 10+）允许 vendor 路径突破 64 的上限，但需要底层 Gralloc allocator 支持更大的 slot 数组。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/ui/include/ui/BufferQueueDefs.h]

#### BLAST 模式下的 BufferQueue

Android 12+ 引入 BLASTBufferQueue 后，BufferQueue 的 Consumer 端从 SurfaceFlinger 进程移入 App 进程（BLASTBufferItemConsumer），但核心的 slot 管理机制完全不变。详见 §2.13「SurfaceFlinger 与合成流水线」中 BLAST 架构分析。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BLASTBufferQueue.cpp]

---

### 🔹 dequeueBuffer 的 reuse-or-reallocate 分流机制

**核心结论**：稳定帧率下 `dequeueBuffer` 走 fast path（< 0.1ms），仅复用 slot 内已有 buffer；几何变更时走 cold path（10-50ms），触发完整分配链。

#### waitForFreeSlotThenRelock 的 slot 获取

```cpp
// frameworks/native/libs/gui/BufferQueueProducer.cpp (android-17.0.0_r1)
status_t BufferQueueProducer::dequeueBuffer(int* outSlot, ...) {
    while (found == BufferItem::INVALID_BUFFER_SLOT) {
        status_t status = waitForFreeSlotThenRelock(
            FreeSlotCaller::Dequeue, lock, &found);
        if (status != NO_ERROR) return status;
        // ...
    }
}
```

`waitForFreeSlotThenRelock()` 的策略：
1. 优先从 `mFreeBuffers` 中取（有 buffer 的空闲 slot，可直接复用）
2. 其次从 `mFreeSlots` 中取（无 buffer 的空闲 slot，需要分配）
3. 若两者都空，阻塞在 `mDequeueCondition` 上等待 `releaseBuffer()` 唤醒

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp]

#### needsReallocation 的五维比较

获取到 slot 后，通过 `buffer->needsReallocation()` 判断是否需要重新分配：

```cpp
const sp<GraphicBuffer>& buffer(mSlots[found].mGraphicBuffer);
bool needsReallocation = buffer == nullptr ||
    buffer->needsReallocation(width, height, format, BQ_LAYER_COUNT, usage);
```

五个比较维度：
- **width**：目标宽度
- **height**：目标高度
- **format**：像素格式（RGBA_8888 / RGB_565 / YUV 等）
- **layerCount**：层级数（通常为 1）
- **usage**：使用标志（GPU_TEXTURE / GPU_RENDER_TARGET / HW_COMPOSER 等）

任一维度不匹配 → `BUFFER_NEEDS_REALLOCATION` flag 返回。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp]

#### Fast path vs Cold path 性能差异

| 路径 | 触发条件 | 开销 | 占比 |
|------|---------|------|------|
| Fast path（slot reuse） | 分辨率/格式/usage 不变 | < 0.1ms | 稳态帧 ~99% |
| Cold path（reallocate） | 首帧 / 旋转 / 格式切换 | 10-50ms | < 1% |

Cold path 的完整链路：

```
dequeueBuffer()
  → BUFFER_NEEDS_REALLOCATION 返回
  → producer 调用 requestBuffer()
  → GraphicBuffer::allocate()
  → GraphicBufferAllocator::allocate()
  → Gralloc5Allocator::allocate()
  → IAllocator AIDL → vendor HAT
  → DMA-BUF Heap / vendor private allocator
```

旋转后掉帧的典型 Perfetto 签名：在 `dequeueBuffer` 轨迹中看到 `BUFFER_NEEDS_REALLOCATION` 打点，紧接着 `GraphicBufferAllocator::allocate` 持续 10-25ms（Pixel 6 实测）。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp]
[来源: DeepResearch/2026-07-09-android17-graphic-buffer-memory-pool-design.md]

---

### 🔹 clearBufferSlotLocked 不释放显存的设计

**核心结论**：slot 状态重置与 buffer 显存释放是两个独立操作。`clearBufferSlotLocked` 只重置 slot 元数据，**不调用 `GraphicBufferAllocator::deallocate()`**。

```cpp
void BufferQueueCore::clearBufferSlotLocked(int slot) {
    mSlots[slot].mGraphicBuffer.clear();  // sp<> 引用计数减 1，但不一定析构
    mSlots[slot].mBufferState.reset();
    mSlots[slot].mRequestBufferCalled = false;
    mSlots[slot].mAcquireCalled = false;
    mSlots[slot].mFence = Fence::NO_FENCE;
    // ... 其他元数据重置
}
```

`mGraphicBuffer.clear()` 释放的是 `sp<GraphicBuffer>` 的引用。如果其他地方（如 EGL image cache、GL 纹理引用）仍持有同一 buffer 的引用，buffer handle 不会真正释放。

#### SurfaceView/TextureView 显存累计根因

这一设计导致了 Android 开发中一个经典的显存泄漏场景：

1. App 创建 SurfaceView → SurfaceFlinger 创建 BufferQueue
2. App 销毁 SurfaceView → `clearBufferSlotLocked` 被调用
3. Slot 元数据重置，但 `sAllocList` 中的 buffer handle 仍存在
4. App 重新创建 SurfaceView → 新的 BufferQueue，新的 allocate 调用
5. 循环往复，`dumpsys meminfo` 中 Graphics 内存持续增长

**修复方式**：确保 EGL/GLES 上下文正确销毁（`eglDestroySurface` + `eglTerminate`），让 GPU 驱动释放 buffer 引用，`GraphicBuffer` 析构链才能走到 `GraphicBufferAllocator::deallocate()`。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/BufferQueueCore.cpp]
[来源: DeepResearch/2026-07-09-android17-graphic-buffer-memory-pool-design.md]

#### 进程死亡时的清理

进程死亡时，`GraphicBufferAllocator` 析构函数会遍历 `sAllocList`，逐个调用 `deallocate()`。但由于 binder 死亡通知的延迟，SurfaceFlinger 端的 buffer 可能要到下一个 frame cycle 才被回收。

---

### 🔹 Gralloc AIDL 与 Vendor 池化责任分界

**核心结论**：AOSP 只定义 Gralloc AIDL 接口和序列化语义，**任何显存层级的池化/缓存策略都在 vendor allocator 服务内部实现**，不进入 AOSP mainline。

#### Gralloc5Allocator 的 AIDL 入口

```cpp
// Gralloc5Allocator 通过 AIDL 调用 vendor IAllocator 服务
// 关键接口（hardware/interfaces/graphics/allocator/aidl）：
//   void allocate2(in BufferDescriptorInfo descriptor,
//                  in int count,
//                  out AllocationResult result);
```

`allocate2()` 的批量分配语义允许 vendor 一次分配多个同规格 buffer（减少 IPC 往返），但 AOSP 框架层**不感知 vendor 内部的池化策略**。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/ui/Gralloc4.cpp]

#### 跨 SoC 池化实现差异

| SoC / Vendor | 池化责任方 | 关键接口 | AOSP 可见性 |
|--------------|------------|---------|-------------|
| Qualcomm Adreno | kgsl 驱动 / GPU HAT | `kgsl_ioctl_gpumem_alloc` 内部 cache | 黑盒，仅 ATRACE `kgsl` track 可见 |
| Mali (ARM) | vendor `gralloc.so` | `mali_alloc` 内部 free-list | 黑盒 |
| PowerVR (Imagination) | vendor `gralloc.so` | `PVRSRVAlloc` with import refcount | 黑盒 |
| Pixel Tensor (GS201) | AOSP + vendor private | `gpu_buffer_pool` sysfs | 部分可见 |
| Swiftshader (CPU 回退) | AOSP | `Buffer::CreateBuffer` simple cache | 源码可见 |

**调试入口**：
- `dumpsys SurfaceFlinger`：输出各 BufferQueue 的 `mFreeBuffers / mActiveBuffers / mFreeSlots / mUnusedSlots` 计数
- `dumpsys meminfo <package>`：报告 `Graphics` / `EGL mtrack` / `GL mtrack` 三类显存总量
- Perfetto：搜索 `mem.gralloc.allocations` / `mem.gralloc.buffers` counter track

[来源: DeepResearch/2026-07-09-android17-graphic-buffer-memory-pool-design.md]

---

### 🔹 16KB Page Size 对 GraphicBuffer 分配的影响

**核心结论**：Android 15 引入 16KB page size 支持后，小尺寸 GraphicBuffer 的实际内存成本因页对齐而放大。

#### reservedSize 字段与页对齐

`BufferDescriptorInfo` 在 Android 15+ 引入了 `reservedSize` 字段，允许 vendor allocator 预留额外空间（如 GPU 驱动元数据）。在 4KB page 设备上，`reservedSize` 按 4KB 取整；在 16KB page 设备上，按 16KB 取整。

对于小尺寸 buffer（如 256×256 图标 atlas，RGBA_8888 = 256KB 像素数据），在 4KB page 设备上的实际分配为 ~260KB（像素数据 + 4KB reservedSize 取整）；在 16KB page 设备上可能达到 ~272KB（reservedSize 按 16KB 取整）。放大比例约 4-8%，但对于大量小 buffer 的场景（如纹理 atlas），累积效应显著。

[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

#### metadata region 取整成本

每个 GraphicBuffer 除了像素数据外，还包含：
- **metadata region**：存储 width/height/format/usage/stride 等元数据
- **reservedSize**：vendor 预留空间（GPU 驱动私有数据）
- **guard pages**：部分 vendor 实现的溢出保护页

在 16KB page size 设备上，这些辅助开销的页对齐成本叠加后，对极小 buffer（如 32×32 图标）的实际内存成本可能达到理论像素数据的 1.5-2 倍。

详见 §2.15「DMA-BUF、Gralloc 与跨进程图形内存共享」中关于 16KB page size 的完整分析。

---

## 扩展

### 🔸 Vulkan VkRenderEngine 的内存池策略

Android 17 的 SurfaceFlinger `VkRenderEngine`（Vulkan 后端合成引擎）使用 AMD VMA（Vulkan Memory Allocator）管理 `VkDeviceMemory` 的子分配。但这个池化层**完全在 VkRenderEngine 进程内部**，与 BufferQueue 的 slot 池化是正交的两个层级：

- **BufferQueue 层**：管理 GraphicBuffer（DMA-BUF fd）的 slot 复用
- **VkRenderEngine 层**：将 GraphicBuffer import 为 VkImage，VMA 管理 VkDeviceMemory 的 sub-allocation

GPU 驱动层（vkd）可能还有自己的 `VkDeviceMemory` 池化，AOSP 完全不参与这一层的策略。

[待验证: VkRenderEngine 源码路径未直接读取，基于架构推断]

---

### 🔸 ANGLE on Vulkan 的 buffer pool 自维护

当设备使用 ANGLE（GLES → Vulkan 翻译层）时，ANGLE 内部会维护自己的 buffer pool：

- GLES `glGenTextures` / `glBufferData` 调用经过 ANGLE 翻译为 Vulkan 等价调用
- ANGLE 的 `BufferPool` 在 `external/angle/` 仓库中实现
- 与 BufferQueue 的关系：BufferQueue 负责 surface-level 的 buffer 传递，ANGLE 负责 texture/buffer object 级别的复用

Android 17 引入的 `BQ_GL_FENCE_CLEANUP` flag（由 `com_android_graphics_libgui_flags` 守门）管的是 EGL fence 的清理路径，与 buffer pool 路径并行而非交叉。

[待验证: ANGLE buffer pool 实现细节需 external/angle 仓库源码确认]

---

### 🔸 mAdditionalOptionsGenerationId 与 Android 17 扩展分配选项

Android 17 引入了 `COM_ANDROID_GRAPHICS_LIBGUI_FLAGS(BQ_EXTENDEDALLOCATE)` flag，守门一个新的扩展分配选项机制：

```cpp
// BufferQueueCore.h (android-17.0.0_r1)
// mAdditionalOptions: 沿 allocRequest 透传到 Gralloc AIDL
// mAdditionalOptionsGenerationId: 每次扩展选项变更时递增
```

`mAdditionalOptions` 允许 producer 在 dequeueBuffer 时附带 vendor 私有的分配选项（如特定压缩格式、保护内容标记等），这些选项通过 `BufferDescriptorInfo` 透传到 vendor allocator。

该机制目前处于 flag 门控状态，默认未在 AOSP mainline 开启，具体启用状态取决于 vendor 构建。

[待验证: BQ_EXTENDEDALLOCATE flag 在 Android 17 的 default rollout 状态需进一步确认]

---

## 版本演进

| 版本 | 变更 |
|------|------|
| Android 8 (O) | `NUM_BUFFER_SLOTS = 64` 硬上限引入（之前为 16） |
| Android 10 (Q) | `mAllowExtendedSlotCount` 支持，允许 > 64 slot |
| Android 12 (S) | BLASTBufferQueue 重构，Consumer 移入 App 进程；AIDL allocator 引入 |
| Android 13 (T) | `PlaneLayout` 支持，多平面 buffer 描述（YUV） |
| Android 14 (U) | per-layer buffer cache disconnect 强制清除；triple buffering 默认 |
| Android 15 (V) | `BufferDescriptorInfo.reservedSize` 引入；16KB page size 支持 |
| Android 17 (37) | `BQ_EXTENDEDALLOCATE` flag + `mAdditionalOptions` 扩展分配选项 |

[已验证: AOSP android-17.0.0_r1]

---

## 交叉引用

- **§2.10 GPU 渲染深入**：GPU 内存管理的概念性框架，本节是其「🔸 GPU 内存管理」扩展点的展开
- **§2.13 SurfaceFlinger 与合成流水线**：BLASTBufferQueue 架构、Consumer 端位置变更
- **§2.15 DMA-BUF、Gralloc 与跨进程图形内存共享**：libdmabufheap 无通用池 contract 的论证（本节印证了这一点）、16KB page size 的完整分析
- **§2.24 BufferQueue 与 BLASTBufferQueue**：slot 状态机、dequeueBuffer 阻塞机制

---

## 调试速查

| 现象 | 检查方法 | 可能根因 |
|------|---------|---------|
| Graphics 内存持续增长 | `dumpsys meminfo <pkg>` 看 Graphics 列 | SurfaceView 反复创建未正确释放 EGL context |
| dequeueBuffer 频繁阻塞 | Perfetto 搜 `waitForFreeSlotThenRelock` | triple buffering 未启用 / release 延迟 |
| 首帧 / 旋转后掉帧 | Perfetto 搜 `BUFFER_NEEDS_REALLOCATION` | cold path allocate 开销 10-50ms |
| Graphics 异常偏高 | `dumpsys GraphicBufferAllocator` | vendor allocator 内部池泄漏 / sp 引用未释放 |
