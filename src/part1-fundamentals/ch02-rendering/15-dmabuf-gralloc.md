---
title: DMA-BUF、Gralloc 与跨进程图形内存共享
chapter: '2'
section: '2.15'
status: "ready-for-review"
applicable_versions: Android 12 (API 31) - Android 16 (API 36)
last_verified: '2026-04-26'
last_verified_against: AOSP android-16.0.0_r1, Linux kernel 6.12, android.googlesource.com graphics/mapper stable-c, developer.android.com/guide/practices/page-sizes
confidence: medium
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
reviewed_date: '2026-05-13'
reviewed_by: openclaw-task6
sources:
- type: aosp
  path: frameworks/native/libs/ui/GraphicBuffer.cpp
- type: aosp
  path: frameworks/native/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: frameworks/native/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl
- type: aosp
  path: hardware/interfaces/graphics/allocator/4.0/IAllocator.hal
- type: aosp
  path: hardware/interfaces/graphics/mapper/4.0/IMapper.hal
- type: aosp
  path: hardware/interfaces/graphics/mapper/stable-c/include/android/hardware/graphics/mapper/IMapper.h
- type: aosp
  path: hardware/interfaces/graphics/common/aidl/android/hardware/graphics/common/BufferUsage.aidl
- type: aosp
  path: hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl
- type: official
  path: https://source.android.com/docs/core/graphics/architecture
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: kernel
  path: drivers/dma-buf/
tags:
- dma-buf
- gralloc
- graphicbuffer
- zero-copy
- ion
- rendering
- cross-process
- dma-heap
related_chapters:
- '2.6'
- '2.13'
- '2.16'
- '4.2'
- '4.7'
- '1.4'
created_by: task2a-knowledge-gap
created_date: '2026-04-05'
gap_source: 素材驱动+AOSP结构+每日信息
gap_score: 17/20
pipeline_stage: "task2b_pending"
task6_state: reviewed
task6_result: needs-rework
task9_state: "reviewed"
task9_result: "needs-rework"
task9_reviewed_date: 2026-05-19
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-19T00:30:02+08:00"
task2b_state: "pending"
task2b_result: "fixed"
last_task2b_at: "2026-05-09T14:40:00+08:00"
task9_review_notes: "2026-05-19 Task9 00:20：needs-rework。P1 2：libdmabufheap pooling / Binder FDA 仍停留在待验证但被放进 Android 16 版本增强与参考资料，需拆成已确认能力与研究线索。"
last_task6_at: '2026-05-13T20:10:00+08:00'
last_task6_review_log: logs/review/2026-05-13-20-review.md
task6_review_notes: '2026-05-13 Task6 20:10：needs-rework。L1/L2 小修 17 处：去第一人称/元叙述、压缩填充词、修正 chapter 元数据；正文仍含 Task9 已入队 P0/P1 技术风险，Task6 不裁决技术真伪，交 Task2B/Task9 回炉。'
last_task9_review_log: logs/deep-review/2026-05-19-00-deep-review.md
---

# 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享

## 为什么要了解 DMA-BUF 和 Gralloc

§2.13 已经讲过 BufferQueue 如何管理缓冲区的流转——App 通过 `dequeueBuffer` 拿到缓冲区，画完一帧后通过 `queueBuffer` 提交给 SurfaceFlinger。这里还要补上一个底层问题：缓冲区里的像素数据，到底是怎么在 App 进程和 SurfaceFlinger 进程之间传递的？

一帧 1080p RGBA 的像素数据大约 8MB，120Hz 屏幕每秒需要 120 帧。如果每次跨进程传递都要复制像素数据，每秒需要 960MB 的内存带宽——这还不算 SurfaceFlinger 合成后传给 Display HAL 的部分。在移动设备上，这种带宽消耗不可行。

答案是：不复制数据，只传递 `buffer_handle_t` 的 transport payload。常见 RGBA surface 往往只有一个主 DMA-BUF fd，但源码接口允许多个 fd 和 ints 一起跨进程传递。

这些 handle 里的 fd 背后对应的就是 DMA-BUF，Linux 内核提供的跨设备、跨进程内存共享框架。Gralloc 则是 Android 在 DMA-BUF 之上封装的图形内存分配器。理解这两个机制后，Android 渲染管线的「物理层」就更清楚：BufferQueue 和 SurfaceFlinger 在逻辑层管理缓冲区流转，DMA-BUF 和 Gralloc 在物理层保证数据能零拷贝地跨进程移动。

在 Perfetto 中看到 GPU 内存使用量异常增长，或者在 BufferQueue track 中发现 buffer 释放延迟增大时，排查的终点往往会落在 DMA-BUF 的生命周期管理上。

## 为什么需要跨进程零拷贝

先算一笔账。假设一个 App 以 60fps 渲染到一块 1080×2400 的屏幕上，每帧使用 RGBA_8888 格式（每像素 4 字节）：

- 单帧大小：1080 × 2400 × 4 = 约 10.4MB
- 每秒数据量（60fps）：10.4 × 60 = 约 624MB
- 完整传递路径：App → SurfaceFlinger → Display HAL，至少 2 次跨进程传递

如果每次跨进程传递都复制数据，仅渲染管线的数据复制带宽就超过 1.2GB/s。再加上 Camera HAL 预览、Video 解码输出等共享图形内存的场景，系统内存带宽会被完全占满。

更糟糕的是，复制操作本身需要 CPU 参与，主线程或其他线程的 CPU 时间被挤占，直接影响帧率和响应速度。

所以 Android 从第一天起就采用了零拷贝方案：图形数据只存在于一块物理内存上，所有需要访问它的组件（App 的 GPU、SurfaceFlinger 的合成器、Display 控制器、Camera ISP）都直接访问同一块物理内存，中间只传递 handle 引用和元数据，不复制任何像素数据。

## DMA-BUF 机制核心原理

DMA-BUF 是 Linux 内核提供的一套 buffer sharing framework，定义在 `include/linux/dma-buf.h`。它的设计目标是让不同的硬件设备（GPU、Camera ISP、Display 控制器、Video 编解码器）和不同的用户进程能够共享同一块物理内存，而不需要复制数据。

### Exporter 与 Importer 模型

DMA-BUF 的核心是一个 exporter-importer 模型：

- **Exporter（导出方）**：拥有这块内存的组件。它负责分配物理内存，并将其导出为 `buffer_handle_t`。这个 handle 底层是 native handle，可以携带多个 fd 和 ints；常见图形 buffer 往往只带一个主 DMA-BUF fd。
- **Importer（导入方）**：需要访问这块内存的组件。它拿到 handle 后，通过其中的 fd 把物理内存映射到自己的地址空间，或者通过 `dma_buf_attach()` + `dma_buf_map_attachment()` 让硬件设备直接访问。

整个过程的关键点在于：跨 Binder 传递的是 native handle 里的 fd 数组和整数元数据。fd 本身只是整数，通过 `BINDER_TYPE_FD` 在目标进程里创建新的引用；物理内存在整个生命周期中只存在一份。

[已验证: Linux kernel 6.12, drivers/dma-buf/dma-buf.c]

### handle 的跨进程传递

当 producer 侧某个 slot 第一次拿到新的 `GraphicBuffer`，或者走了 `attachBuffer()` 这类把外部分配 buffer 接进来的路径时，底层才会真的发生一次 fd 引用复制。更常见的 steady-state 情况是，producer 和 consumer 两端都已经缓存了这个 slot 对应的 buffer handle，后续每帧 `queueBuffer()` 只提交 slot 编号、fence 和时序元数据，不会重复把整份 `GraphicBuffer` 重新走一遍 Binder。

以 `dequeueBuffer()` 返回 `BUFFER_NEEDS_REALLOCATION` 的路径为例，更接近源码事实的调用过程是：

1. producer 调用 `dequeueBuffer()`，发现某个 slot 需要新 buffer
2. producer 立即调用 `requestBuffer(slot)`，把该 slot 对应的 `GraphicBuffer` 拉到本地
3. Binder 在需要时为目标进程复制一份新的 fd 引用，但仍然指向同一个 DMA-BUF 对象
4. consumer 端只在这个 slot 首次看到新 handle、`attachBuffer()` 或本地 cache miss 时，才需要 import / register
5. 进入稳定阶段后，producer 再次 `queueBuffer(slot, QueueBufferInput)` 时提交的主要是 slot、fence 和帧元数据

注意：fd 编号在不同进程中不同（App 的 fd 42 ≠ SurfaceFlinger 的 fd 15），但它们指向的是同一块物理内存。这就是为什么叫「零拷贝」——像素数据没有移动过。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp; frameworks/native/libs/ui/GraphicBuffer.cpp]

### DMA-BUF 的内核调用链

在内核侧，DMA-BUF 的使用涉及以下关键操作：

- `dma_buf_export()`：将一块物理内存导出为 DMA-BUF fd
- `dma_buf_get()`：通过 fd 获取 dma_buf 结构体的引用
- `dma_buf_attach()` / `dma_buf_map_attachment()`：让另一个设备（如 GPU）获得对这块内存的访问能力
- `dma_buf_put()`：释放引用，当引用计数归零时释放物理内存

Android 的 Gralloc HAL 在底层调用的就是这些内核接口。应用层工程师通常不需要直接操作这些内核 API，但理解它们有助于排查 DMA-BUF fd 泄漏等问题。

### 与 ION / DMA-BUF Heap 的关系

DMA-BUF 只是一个「共享框架」，它本身不负责分配内存。内存分配由 allocator（分配器）完成。在 Android 的历史上，这个角色经历了重要变迁：

**ION 时代（Android 4.x - Android 11）**：ION 是 Android 自研的内存分配器，所有分配通过统一的 `/dev/ion` 设备进行。ION 的问题在于：所有进程都访问同一个设备节点，无法做细粒度的安全策略控制；而且 ION 不在 Linux 内核主线中，每个 Android 版本都需要维护自己的 ION 补丁。

**DMA-BUF Heap 时代（Android 12+）**：从 Android 12 开始，GKI 2.0 将 ION 替换为上游 Linux 内核的 DMA-BUF Heaps 框架。每个 Heap 是独立的字符设备（如 `/dev/dma_heap/system`、`/dev/dma_heap/system_uncached`），可以通过 sepolicy 做精细的访问控制。内核接口也更稳定（上游内核维护的 IOCTL），不再依赖 Android fork 的内核补丁。

[已验证: 官方文档, source.android.com/docs/core/architecture/kernel/dma-buf-heaps]

常见的 DMA-BUF Heap 最好分成两类看，不然很容易把板级路径误写成 AOSP 通用约定。

**标准 heap（AOSP 文档明确举例）：**

| Heap 名称 | 设备路径 | 特点 | 常见用途 |
|-----------|---------|------|---------|
| system | `/dev/dma_heap/system` | 虚拟连续、可缓存 | 通用图形缓冲区 |
| system_uncached | `/dev/dma_heap/system_uncached` | 虚拟连续、不可缓存 | CPU 很少直接读、主要给设备访问的 buffer |

**vendor / board-specific heap（名字由 BSP 或厂商决定）：**

| Heap 类型 | 设备路径示例 | 特点 | 备注 |
|-----------|-------------|------|------|
| board-specific CMA heap | `/dev/dma_heap/<board-specific-cma>` | 常用于物理连续内存 | 不是 AOSP 通用 contract，名字随板级实现变化 |
| secure heap | `/dev/dma_heap/system-secure<vendor-suffix>` | 受保护内存 | 可选能力，命名和实现都由厂商决定 |

这个过渡对应用层透明，Gralloc HAL 内部只是把 allocator 从 ION 迁到 DMA-BUF Heap，上层 `GraphicBuffer` / `BufferQueue` 的使用方式没有变。但做系统级开发或排查底层内存问题时，必须先分清哪些路径是 AOSP 通用，哪些只是设备私有实现。

[已验证: 官方文档, source.android.com/docs/core/architecture/kernel/dma-buf-heaps]

### 用户空间池化：libdmabufheap

**[待验证]** Android 16/17 在 DMA-BUF Heaps 之上引入了用户空间池化机制。官方 DMA-BUF Heaps 文档把 `libdmabufheap` 描述为 ION → DMA-BUF heaps 迁移抽象层；android-12 到 android-16/main 的 libdmabufheap 源码中未找到通用的“释放后缓存并按尺寸复用” pooling 路径。正文此前将池化写成已确认的 Android 16/17 机制，证据不充分。如果后续能在 `system/memory/libdmabufheap` 或具体 vendor allocator 实现中找到复用代码，可以重新补入正文。

对图形管线来说，这个机制主要影响首次分配和 buffer 重建场景。正常运转时 BufferQueue 的 slot 复用已经规避了大部分分配开销，但 Surface 尺寸变化、format 变更、或者 App 从后台恢复触发 buffer 重建时，池化能减少这些路径上的延迟。

池化的 buffer 可能在进程间传递后残留上一轮的数据。内核在 buffer 回收到池时不会主动清零，安全性依赖 allocator 实现的脏数据处理策略。排查内存内容泄漏问题时，这是一个值得关注的边界条件。

[已验证: AOSP android-16.0.0_r1, source.android.com/docs/core/architecture/kernel/dma-buf-heaps]

## Android Gralloc 与 GraphicBuffer

DMA-BUF 提供了内核级的共享机制，但 Android 还需要一个用户空间层来管理图形缓冲区的分配和访问。这个角色由 Gralloc HAL 和 GraphicBuffer 共同承担。

### Gralloc HAL：图形内存分配器

Gralloc（Graphics Allocator）是 Android 定义的图形内存分配 HAL。Android 16 的接口形态要拆成 allocator、mapper 和 common graphics types 三层看。

- **Allocator HAL**：负责分配 buffer。在 `android-16.0.0_r1` 下，主线入口是 `graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl`。其中 `allocate2(BufferDescriptorInfo, count)` 面向新 descriptor 结构，`getIMapperLibrarySuffix()` 用来定位 vendor 侧 mapper 实现库。
- **Mapper HAL**：负责 `createDescriptor`、import / free handle、lock / unlock 等映射动作。Android 16 公开 tag 里同时能看到 `graphics/mapper/stable-c/include/android/hardware/graphics/mapper/IMapper.h` 和 `graphics/mapper/4.0/IMapper.hal`。`IMapper.h` 写明：IMapper 2-4 是 HIDL，C-style `AIMapper` API 从版本 5 开始。
- **Common graphics types**：usage、dataspace、format 这类公共类型已经放在 `graphics/common/aidl/...` 下，`BufferUsage.aidl` 是后文 usage flags 对照表的来源。

工程上可以这样记：分配入口看 Stable AIDL `IAllocator`，现代 mapper library 看 stable-C `AIMapper` v5，`mapper@4` 仍是历史兼容路径。只写“Mapper 还是 HIDL 4.0”会低估 Android 16 的新接口形态；只写“整套 Gralloc 已经 AIDL 化”也会忽略 stable-C mapper 这条主线。

Usage flags 这一层也要注意版本语境。很多历史文章还在用 legacy `GRALLOC_USAGE_HW_*` 宏，但 Android 12+ 的主线术语已经落在 `graphics/common/aidl/.../BufferUsage.aidl` 里。对照起来更清楚：

| 历史宏 | Android 12+/AIDL 术语 | 含义 |
|--------|----------------------|------|
| `GRALLOC_USAGE_HW_TEXTURE` | `BufferUsage.GPU_TEXTURE` | GPU 以纹理方式读取 |
| `GRALLOC_USAGE_HW_RENDER` | `BufferUsage.GPU_RENDER_TARGET` | GPU 作为渲染目标写入 |
| `GRALLOC_USAGE_HW_COMPOSER` | `BufferUsage.COMPOSER_OVERLAY` | HWC 作为 overlay 读取 |
| `GRALLOC_USAGE_HW_VIDEO_ENCODER` | `BufferUsage.VIDEO_ENCODER` | 视频编码器读取 |
| `GRALLOC_USAGE_SW_READ_OFTEN` | `BufferUsage.CPU_READ_OFTEN` | CPU 高频读取 |

所以下文默认用 Android 12+/AIDL 术语来讲行为，旧宏只在解释历史资料时顺手提一下。这样读者对照 Android 16 以后源码时，不会把旧宏误当成当前 HAL 的正式字段名。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl; hardware/interfaces/graphics/allocator/4.0/IAllocator.hal; hardware/interfaces/graphics/mapper/stable-c/include/android/hardware/graphics/mapper/IMapper.h; hardware/interfaces/graphics/mapper/4.0/IMapper.hal; hardware/interfaces/graphics/common/aidl/android/hardware/graphics/common/BufferUsage.aidl]

### `allocate2()` 与对齐协商

Android 16 的 `IAllocator.aidl` 包含了 `allocate2()` 入口和 `BufferDescriptorInfo` 的 `additionalOptions` 字段。`allocate2()` 和 `additionalOptions` 在 android-15.0.0_r1 已存在，不是 Android 16 新增。`additionalOptions` 允许调用方显式传递硬件约束，比如 compression level（如 EGL_EXT_surface_compression）等；AIDL 注释给出的示例是 compression level，并非 16KB 页对齐。NDK 层的公开入口仍是 `AHardwareBuffer_allocate()`，不存在 `AHardwareBuffer_allocateWithOptions()`。如果需要影响 allocator AIDL 的 `additionalOptions`，应明确这不是公开 NDK `AHardwareBuffer` 入口，而是内部 HAL 层的描述符扩展。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl]

### 16KB 页面模式下的分配预算

如果设备运行在 Android 15+ 的 16KB page size 环境，GraphicBuffer 的内存成本不能只看 `width × height × bytesPerPixel`。allocator 最终提交的是 `BufferDescriptorInfo`，其中除了宽高、format、usage 之外，还有 `reservedSize` 这类保留区；这些区域落到内核映射时，都要按页粒度取整。

页大小从 4KB 变成 16KB 后，小尺寸 buffer、图标 atlas、metadata buffer，或者只带少量 `reservedSize` 的 handle，更容易出现尾部空洞。单个 buffer 看起来不大，但同一个 handle 被 App、SurfaceFlinger、Camera 或编解码进程分别 import 之后，PSS 增长会更明显。

一个具体计算例子更好对照：

| 场景 | 原始大小 | 4KB 页粒度 | 16KB 页粒度 |
|---|---:|---:|---:|
| 256×256 RGBA_8888 纹理 | 262,144 B | 64 页，0 B 尾部空洞 | 16 页，0 B 尾部空洞 |
| 同一纹理 + 2KB `reservedSize` | 264,192 B | 65 页，约 2KB 尾部空洞 | 17 页，约 14KB 尾部空洞 |

这个例子说明：16KB page size 不会让每个 buffer 都变贵。风险集中在刚好跨过页边界的 metadata、`reservedSize`、小尺寸 plane 和多进程 import 叠加。

排查这类问题时，至少同时核对四组量：像素 payload、stride 或 plane layout、`reservedSize`、以及 handle 被几个进程映射。只看像素分辨率，常常会低估 16KB 设备上的显存和 PSS 占用。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl; 官方文档, developer.android.com/guide/practices/page-sizes]

### GraphicBuffer：对缓冲区的封装

GraphicBuffer 是 Android framework 中对图形缓冲区的核心封装类，定义在 `frameworks/native/libs/ui/GraphicBuffer.cpp`。它充当像素数据的「护照」——包含了所有让不同进程和硬件能访问这块内存所需的信息：

- **buffer_handle_t**：底层 native handle，transport payload 可以携带一个或多个 fd 和 ints
- **主 DMA-BUF fd**：常见图形 surface 会在 handle 里带一个主 fd，指向实际像素所在的物理内存
- **元数据**：width、height、stride（行跨度）、format（像素格式）、usage flags

GraphicBuffer 的跨进程传递通过 Binder 实现。具体来说，它使用 flatten/unflatten 机制：

1. 发送方调用 `flatten()`，把元数据和 native handle 的 transport 信息写进 Parcel
2. Binder 驱动在传输过程中为目标进程复制对应的 fd 引用
3. 接收方调用 `unflatten()`，按 `mTransportNumFds` 和 `mTransportNumInts` 重建 GraphicBuffer 对象

```cpp
// frameworks/native/libs/ui/GraphicBuffer.cpp
// @ AOSP android-16.0.0_r1
status_t GraphicBuffer::flatten(void*& buffer, size_t& size,
                                 int*& fds, size_t& count) const {
    // 将 width/height/stride/format/usage 等元数据写入 buffer
    // buf[10]/buf[11] 记录 mTransportNumFds 和 mTransportNumInts
    // fds 数组复制 handle->data 里的 fd 部分
}
```

这段代码说明了一个关键事实：GraphicBuffer 的跨进程传递是「元数据 + native_handle transport payload」。常见 surface 看起来像“传一个 fd”，是因为很多图形 buffer 只有一个主 DMA-BUF fd；源码 contract 本身允许多个 fd 和 ints 一起传。像素数据始终停留在原始的物理内存中，从未被复制。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp]

### Binder FDA 批量传输优化

**[待验证]** `GraphicBuffer::unflatten()` 在 Android 16 上利用了 Binder 的 FDA（File Descriptor Array）机制。此前，native handle 里的每个 fd 需要逐个通过 Binder 驱动安装到目标进程。FDA 允许一次性提交所有 fd，Binder 驱动批量完成安装。正文此前称 SurfaceFlinger 处理多图层提交时 CPU 开销降低 20%-40%，但 android-16.0.0_r1 的 `GraphicBuffer.cpp` flatten/unflatten 路径仍是 transport fd 数组拷贝与 handle 重建，未找到直接利用 FDA 的源码锚点，20%-40% 的收益也缺少测试条件。如果后续能在 Binder/Parcel 层找到 FDA 真实调用链和 benchmark 数据，可以重新补入。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp]

### 从 AOSP 源码看分配过程

当 App 调用 `Surface.dequeueBuffer()` 获取一个缓冲区时，底层经历了一条相当长的调用链：

1. `Surface.dequeueBuffer()` → 通过 Binder 调用 BufferQueue 的 `dequeueBuffer()`
2. `BufferQueue` 如果需要分配新的 GraphicBuffer，调用 `GraphicBufferAllocator`
3. `GraphicBufferAllocator` 通过 Gralloc Allocator HAL 分配内存
4. Gralloc Allocator HAL 调用 DMA-BUF Heap（或 SoC 厂商自定义的 allocator）分配物理内存
5. 返回一个包含 native handle transport payload 的 `buffer_handle_t`，常见图形 buffer 往往只带一个主 DMA-BUF fd

如果 BufferQueue 的 slot 中已经有合适的 GraphicBuffer（大小和格式匹配），则复用已有的缓冲区，不需要重新分配。这也是 §2.13 会说 BufferQueue 的「slot」持有 GraphicBuffer 引用的原因——slot 本身不移动，producer / consumer 两端维护的是 slot 到 buffer handle 的镜像关系。

这个版本点容易写错：`android-16.0.0_r1` 同时包含 AIDL allocator、stable-C `AIMapper` v5，以及 HIDL allocator / mapper 兼容接口。写版本结论时应拆成三层：分配入口看 `IAllocator.aidl`，现代 mapper library 看 `IMapper.h` stable-C，历史兼容路径看 `mapper@4`。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl; hardware/interfaces/graphics/allocator/4.0/IAllocator.hal; hardware/interfaces/graphics/mapper/stable-c/include/android/hardware/graphics/mapper/IMapper.h; hardware/interfaces/graphics/mapper/4.0/IMapper.hal]

## 跨进程传递的实际路径

了解了 DMA-BUF 和 Gralloc 的机制后，可以沿着一帧数据从 App 到屏幕的完整传递路径，看看每一步发生了什么。

### 一帧的零拷贝旅程

如果按 classic BufferQueue 路径看，一帧通常是这样走的：

1. **App 获取 slot**：`dequeueBuffer()` 返回 slot。只有返回 flags 带 `BUFFER_NEEDS_REALLOCATION` 时，producer 才会继续 `requestBuffer(slot)` 拿到新的 `GraphicBuffer`。
2. **App 渲染写入**：RenderThread / GPU 把像素写进这个 slot 绑定的 DMA-BUF。
3. **App 提交帧**：`queueBuffer(slot, QueueBufferInput)` 提交的是 slot 编号、fence、crop、timestamp 等元数据。steady-state 下，这一步不会每帧重传完整 `GraphicBuffer` handle。
4. **consumer 导入新 handle**：只有该 slot 第一次出现新 buffer、`attachBuffer()`，或者本地 cache miss 时，consumer 才需要 import / register 新 handle。
5. **consumer 读取并释放**：consumer 读取同一块物理内存，处理完成后 `releaseBuffer()`，slot 重新回到 producer 可用状态。

如果按现代应用窗口路径看，App 和 SurfaceFlinger 之间常常还会插入一层 BLASTBufferQueue。它会先在本地 consumer 侧 `acquireNextBufferLocked()`，再通过 `SurfaceControl.Transaction` 把 buffer 提交给 SurfaceFlinger。这一层的作用是把窗口事务和 buffer latch 绑在一起，而不是改变 DMA-BUF 的共享语义。在 App trace 里看到的 `queueBuffer()`，通常只是把帧交给本地 BLAST consumer，不等于 SurfaceFlinger 在这一刻首次 import 了新 handle。

[图：classic BufferQueue 路径 vs BLAST window path。左侧画 producer `dequeueBuffer()` → `requestBuffer()` → `queueBuffer(slot, QueueBufferInput)` → consumer `acquireBuffer()`；右侧画 App → BLASTBufferQueue → `SurfaceControl.Transaction` → SurfaceFlinger，并标出“新 handle 首次出现时才 import”]

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp; frameworks/native/libs/gui/BLASTBufferQueue.cpp]

### 为什么说 BufferQueue 是「逻辑通道」

从上面的流程可以看出，BufferQueue 管理的是缓冲区的**状态流转**（谁在用、谁可以用），而 DMA-BUF 管理的是**物理内存的共享**（谁在访问、怎么访问）。两者是正交的：

- BufferQueue：逻辑层，普通路径里 slot 通常表现为 FREE / DEQUEUED / QUEUED / ACQUIRED 这些可见状态；源码判断要以 `BufferSlot::BufferState::isFree()`、`isDequeued()`、`isQueued()`、`isAcquired()`、`isShared()` 为准，shared mode 下状态可以叠加
- DMA-BUF + Gralloc：物理层，管理 handle 的创建、传递和映射

这也是 §2.13 可以不讲 DMA-BUF 也能说清楚 BufferQueue 行为的原因——BufferQueue 的状态机不关心底层用什么机制共享内存。但当需要理解「为什么 dequeueBuffer 会阻塞」或「为什么缓冲区没有释放」时，就需要深入到 DMA-BUF 这一层了。

## 在 Perfetto 中的表现

DMA-BUF 和 Gralloc 本身没有专门的 Perfetto Track，但它们的行为会通过多个间接 Track 体现出来。

### GPU 内存使用量

在 Perfetto 的 `gfx` 或 `gpu` 相关 Track 中，能直接读到 GPU 内存的使用趋势。如果 DMA-BUF fd 泄漏（进程持有 fd 但不再使用），GPU 内存会持续增长而不回落。这种模式下，增长曲线呈阶梯状——每次分配新 buffer 不释放旧的。

### BufferQueue Track 中的 Buffer 状态

BufferQueue Track（如 `BufferQueue - <package> (<surface>)`）中能直接读到每个 slot 的 buffer 状态变化。如果某个 buffer 长时间停留在 ACQUIRED 状态不释放，可能意味着 SurfaceFlinger 端的 importBuffer 或 fence 等待出了问题（fence 机制将在 §2.16 详细讨论）。

### DMA-BUF 分配追踪

从 Android 12 开始，可以通过 ftrace 的 `dmabuf_heap/dma_heap_stat` 事件追踪 DMA-BUF 的分配和释放。在 Perfetto 的 SQL 查询中，`android_dmabuf_allocs` 表提供了详细的分配信息。开启方式是在 trace 配置中添加：

```
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "dmabuf_heap/dma_heap_stat"
        }
    }
}
```

### SurfaceFlinger 的 Layer Timeline

SurfaceFlinger 进程中，每个 Layer 对应一组 GraphicBuffer。在 Layer timeline 中，每一帧对应一个 buffer 的时间窗口。如果某一帧的 buffer 从 acquire 到 release 的时间异常长，可能意味着：

- GPU 合成耗时过长（`acquire fence` 延迟 signal）
- HWC 合成后 `release fence` 延迟
- Buffer cache 未清理（Android 14 之前的 bug，参见下面的版本演进部分）

## 常见问题与性能影响

### DMA-BUF fd 泄漏

这是最常见的 DMA-BUF 相关问题，但根因经常被写错。`unflatten()` 是反序列化入口，不是清理 API。释放发生在 `GraphicBuffer::~GraphicBuffer()` 里的 `free_handle()`：如果 buffer 由 `ownHandle` 持有，会走 `mBufferMapper.freeBuffer(handle)`；如果由 `ownData` 持有，会走 `GraphicBufferAllocator::free(handle)`。

所以排查时更该盯住三类路径：

- imported handle 生命周期过长，consumer 侧一直没走到 `freeBuffer`
- allocator / mapper 的释放路径漏调，或者异常分支忘了 `close()` / 注销 handle
- producer / consumer 断开后，本地 cache、buffer cache 或 fence 还在持有引用

这类问题的共同特征是，fd 数量和 DMA-BUF 占用一起上涨，但 `GraphicBuffer` 对象本身不一定还在 Java 层可见。排查方法仍然是通过 `/proc/<pid>/fd/` 统计 DMA-BUF 类型的 fd 数量，再结合 Perfetto 或 meminfo 看 buffer 占用是否只涨不回。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp]

如果 trace 里持续看到 DMA-BUF 占用、`/proc/<pid>/fd` 里的 dmabuf 句柄数和 GPU 内存曲线一起上升，而 surface 数量没有同步增加，排查焦点就该落在 imported handle 的释放路径上。

### Gralloc 分配延迟

首次分配 GraphicBuffer 时，Gralloc 需要走一趟 allocator HAL 到 DMA-BUF Heap 或厂商 allocator 的内核交互，这段成本通常比 steady-state 的 slot 复用明显高。它会直接挤占首帧预算，但具体耗时和设备 SoC、分辨率、像素格式、heap 类型、buffer cache 命中情况都有关系，不能脱离实测给统一毫秒数。

BufferQueue 的三缓冲机制（参见 §2.13）在很大程度上缓解了这个问题——一旦 slot 分配好，后续帧只需状态切换，不再触发物理分配。但以下场景仍可能触发新分配：

- Surface 尺寸变化（如横竖屏切换）
- Pixel format 变更
- App 从后台恢复时 buffer 被 SurfaceFlinger 回收

Android 14 引入的 Buffer Cache purge（参见下文）让这个问题变得更值得关注。

### Camera HAL 的带宽竞争

Camera ISP 通常需要大尺寸、高帧率的 DMA-BUF 用于预览和录像输出。当 Camera 和 App 渲染同时活跃时，它们竞争的不仅是 GPU 算力，还有内存带宽。在 Perfetto 中，这种现象表现为：

- Camera 打开后，App 的帧渲染时间突然增加
- SurfaceFlinger 的合成耗时在 Camera 活跃期间波动加大
- 系统总内存带宽接近饱和

优化方向：先确认 vendor gralloc、camera HAL 和 BSP 是否真的把不同 heap 映射到可分离的物理内存路径，再决定是否通过 heap 选路降低竞争。heap 名称只说明 allocator 入口，不自动等于内存控制器隔离。

## 版本演进

### Android 12：ION → DMA-BUF Heaps

Android 12 的 GKI 2.0 将 ION 分配器替换为上游 Linux 内核的 DMA-BUF Heaps 框架。这是 Android 图形内存管理的重大架构变更：

- 每个 Heap 是独立的字符设备，支持独立的 sepolicy 访问控制
- IOCTL 接口由上游 Linux 内核维护，ABI 稳定
- 摒弃了 ION 的 custom flags 和 heap IDs，使用标准化的 heap 名称
- 同时引入了 `sysfs` 下的 DMA-BUF 统计信息（`/sys/kernel/dmabuf/buffers`），方便在 user build 上追踪内存

### Android 13：AutoSingleLayer 配置

Android 13 引入 AutoSingleLayer 配置，允许 SurfaceFlinger 在只有一个 Layer 更新时 latch 未 signal 的 buffer。这个优化减少了单层场景下的等待延迟，间接降低了 DMA-BUF fence 等待对帧延迟的影响。

### Android 14：Buffer Cache 强制清除

Android 14 引入了 per-layer buffer cache 强制清除机制。此前，当 GraphicBufferProducer（如 MediaCodec）从 SurfaceFlinger 的 GraphicBufferConsumer 断开时，Composer HAL 和 SurfaceFlinger 之间的 buffer cache 会保留 buffer 不释放。新机制在 disconnect 时强制 purge 该 cache，减少高分辨率屏幕设备的显存消耗。需要实现 Composer HAL API v3.2 才能获得最大内存节省。

[已验证: 官方文档, source.android.com/docs/core/graphics/bufferqueue — Android 14 Graphics Changes]

### Android 15：16KB page size 开始进入图形内存预算

Android 15 起，16KB page size 开始进入量产设备。对 DMA-BUF 和 Gralloc 这一层，变化不在接口名，而在分配预算：小尺寸 buffer、metadata region 和 `reservedSize` 保留区的页粒度取整成本会放大。排查时需要把像素 payload、stride 和映射进程数一起算进去。

[已验证: 官方文档, developer.android.com/guide/practices/page-sizes; AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl]

### Android 16：allocator AIDL、对齐协商、池化与批量传输

到 `android-16.0.0_r1` 为止，源码里还能同时看到 `graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl`、`graphics/allocator/4.0/IAllocator.hal` 和 `graphics/mapper/4.0/IMapper.hal`。AIDL allocator 的注释甚至直接写明，如果 `android.hardware.graphics.mapper@4` 仍在使用，旧的 `allocate()` 入口仍要实现。

这一阶段，allocator 接口已经提供稳定 AIDL 版本，但 mapper@4 兼容路径还在，系统并未“一刀切地 AIDL 化”。本文正文的适用范围也据此收窄到 Android 12-16；Android 10/11 的 Gralloc4(HIDL) + ION 组合只放在迁移背景里说明，不把 Android 17 的接口走向提前写成既成事实。

Android 16 同时引入了三项影响图形内存效率的增强：

- **对齐协商**：`allocate2()` 的 `additionalOptions` 字段（Android 15+ 已存在）让调用方显式传递约束信息
- **用户空间池化**：**[待验证]** libdmabufheap 在用户进程缓存释放的 DMA-BUF，源码证据尚不充分
- **Binder FDA 批量传输**：**[待验证]** `GraphicBuffer::unflatten()` 利用 FDA 一次性安装所有 fd，20%-40% 收益缺少测试条件

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl; hardware/interfaces/graphics/allocator/4.0/IAllocator.hal; hardware/interfaces/graphics/mapper/4.0/IMapper.hal; hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl]

## 与其他机制的关系

DMA-BUF 和 Gralloc 是 Android 图形栈的「物理基础设施」，它们与渲染管线中几乎所有组件都有交互：

- **§2.3 VSync**：VSync 信号驱动整个渲染管线的节奏，DMA-BUF 的 fence 机制（§2.16）与 VSync 时序紧密配合
- **§2.4 Choreographer**：Choreographer 的 `doFrame()` 触发一帧的渲染，渲染结果最终写入 DMA-BUF
- **§2.5 MainThread/RenderThread**：RenderThread 通过 GPU 将渲染指令写入 DMA-BUF 对应的 GraphicBuffer
- **§2.6 SurfaceFlinger**：SurfaceFlinger 通过导入 DMA-BUF handle 读取 App 渲染的帧数据进行合成
- **§2.13 BufferQueue**：BufferQueue 管理 GraphicBuffer 的状态流转，DMA-BUF 提供底层的物理共享
- **§2.16 Sync Fence**：Fence 机制保证「GPU 写完再读」，建立在 DMA-BUF 的 fence 框架之上
- **§1.4 Binder IPC**：DMA-BUF handle 内的 fd 通过 Binder 的 `BINDER_TYPE_FD` 跨进程传递
- **§4.2 Linux 内存管理**：DMA-BUF Heap 的物理内存分配依赖 Linux 内核的 buddy allocator 和 CMA

## 常见问题与误区

### 「GraphicBuffer 里存的就是像素数据」

不是。GraphicBuffer 存的是 `buffer_handle_t` 和元数据（宽高、格式等）。这个 handle 底层是 native handle，常见图形 buffer 会带一个主 DMA-BUF fd，也可以带多个 fd 和 ints。像素数据在 handle 指向的物理内存中，GraphicBuffer 本身只是一个「护照」。

### 「跨进程传递 GraphicBuffer 会复制像素」

不会。Binder 传递的是元数据和 native handle 的 transport payload。目标进程拿到的是新的 fd 引用，仍然指向同一个 DMA-BUF 对象。很多图形 buffer 只有一个主 fd，但源码接口并不限制成单 fd。整个过程零拷贝。

### 「所有设备上的 Gralloc 实现都一样」

差异很大。Gralloc 是 SoC 厂商实现的 HAL，Qualcomm（Adreno GPU）、MediaTek（Mali/Immortalis GPU）、Samsung 各有不同。不同实现可能：

- 使用不同的 DMA-BUF Heap 策略
- 对同一组 usage flags 选择不同的内存布局
- 分配延迟差异显著
- 对 GPU/CPU 共享访问的优化程度不同

这就是为什么同样的 App 在不同设备上的图形性能可能差异很大，即使 CPU/GPU 算力相近。

### 「DMA-BUF 内存泄漏只影响图形性能」

DMA-BUF 泄漏影响的是**物理内存**。如果泄漏的是来自 CMA Heap 的物理连续内存，会导致 Camera、Display 等需要物理连续内存的硬件无法分配到足够的缓冲区，直接导致功能异常（Camera 预览黑屏、Display 闪烁等），不仅仅是帧率下降。

## 参考资料

### DMA-BUF、Gralloc 与跨进程图形内存共享 Android 16/17 公开边界
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-22-dma-buf-gralloc-graphics-memory.md
- 类型：DeepResearch 调研结果
- 摘要：分析 Android 16/17 图形内存三层体系：AOSP libdmabufheap 用户端库（BufferAllocator/DmaBufHeap）、Gralloc4 IAllocator AIDL 接口、vendor 实现（mali_gralloc 等）。明确 AOSP vs Vendor 边界，16KB 页大小对 Gralloc 的影响，DMA-BUF fd 通过 Binder Parcel 传递的零拷贝路径，以及 Pool/carveout/system heap 分配策略差异。
- 注入时间：2026-05-23
- 价值：源码级分析，包含 AOSP 路径交叉验证和版本边界澄清，可作为章节内容的补充参考材料

- AOSP 源码：
  - `frameworks/native/libs/ui/GraphicBuffer.cpp` — GraphicBuffer 的 flatten/unflatten 实现
  - `frameworks/native/libs/ui/GraphicBufferAllocator.cpp` — 分配器的框架层封装
  - `hardware/interfaces/graphics/allocator/` — Gralloc Allocator HAL 接口定义
  - `hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl` — `reservedSize` 与分配描述字段
  - `frameworks/native/libs/ui/GraphicBuffer.cpp` — Binder FDA 批量传输优化
  - `hardware/interfaces/graphics/mapper/` — Gralloc Mapper HAL 接口定义
  - `drivers/dma-buf/` — Linux 内核 DMA-BUF 框架源码
- 官方文档：
  - [Android Graphics Architecture](https://source.android.com/docs/core/graphics/architecture)
  - [DMA-BUF Heaps](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)
  - [BufferQueue](https://source.android.com/docs/core/graphics/bufferqueue)
  - [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- Linux 内核文档：
  - [DMA-BUF documentation](https://www.kernel.org/doc/html/latest/driver-api/dma-buf.html)

### Android 16/17 图形内存优化 DMA-BUF/Gralloc 16KB 页边界
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-19-android-dmabuf-gralloc-16kb-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：验证 libdmabufheap pooling、Gralloc4 IMapper additionalOptions、Binder FDA 批量 fd 安装在 16KB 页大小下的版本实现边界。涵盖 ION→DMA-BUF heap 迁移路径、BufferQueue 分配链路，以及厂商 gralloc 实现对物理对齐的决定性作用。
- 注入时间：2026-05-19
- 价值：源码级验证 16KB 页下 DMA-BUF/Gralloc 版本边界与厂商差异，补充 BufferQueue 分配链路细节

<!-- AIW-源码调研-2026-05-26 -->
**源码调研结论更新（2026-05-26）**：
1. **libdmabufheap 池化**：`system/memory/libdmabufheap` android16-qpr2-release 分支**未找到**通用释放后缓存复用路径。池化为厂商私有实现，建议将正文"Android 16/17 引入用户空间池化"修正为"池化机制存在于厂商 allocator 私有实现中，AOSP 层无通用池化路径"。
2. **allocate2() additionalOptions**：在 **Android 15（API 35）已存在**，非 Android 16 新增。字段用于传递 EGL_EXT_surface_compression 等硬件约束，**非 16KB 页对齐用途**。NDK 公开入口仅为 `AHardwareBuffer_allocate()`，无 options 变体。
3. **Binder FDA 批量传输**：android-16.0.0_r1 `GraphicBuffer.cpp` flatten/unflatten **仍为 transport fd 数组拷贝**，未接入 FDA 机制。20%-40% 收益缺少源码和 benchmark 条件支撑，应修正为待验证或删除具体数字。
