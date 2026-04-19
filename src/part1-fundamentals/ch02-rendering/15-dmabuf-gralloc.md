---
title: DMA-BUF、Gralloc 与跨进程图形内存共享
chapter: '2.15'
section: '2.15'
status: ready-for-review
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-04-11'
last_verified_against: AOSP android-16.0.0_r1, Linux kernel 6.12
confidence: medium
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
reviewed_date: '2026-04-19'
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
  path: hardware/interfaces/graphics/common/aidl/android/hardware/graphics/common/BufferUsage.aidl
- type: official
  path: https://source.android.com/docs/core/graphics/architecture
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps
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
- '1.4'
created_by: task2a-knowledge-gap
created_date: '2026-04-05'
gap_source: 素材驱动+AOSP结构+每日信息
gap_score: 17/20
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: needs-rework
task9_state: reviewed
task9_result: needs-rework
task9_reviewed_date: "2026-04-19"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-19T12:32:00+08:00"
task2b_state: pending
task2b_result: fixed
---

# 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享

## 为什么要了解 DMA-BUF 和 Gralloc

在 §2.13 中我们讲了 BufferQueue 如何管理缓冲区的流转——App 通过 `dequeueBuffer` 拿到缓冲区，画完一帧后通过 `queueBuffer` 提交给 SurfaceFlinger。但有一个关键问题被我们跳过了：缓冲区里的像素数据，到底是怎么在 App 进程和 SurfaceFlinger 进程之间传递的？

一帧 1080p RGBA 的像素数据大约 8MB，120Hz 屏幕每秒需要 120 帧。如果每次跨进程传递都要复制像素数据，每秒需要 960MB 的内存带宽——这还不算 SurfaceFlinger 合成后传给 Display HAL 的部分。在移动设备上，这种带宽消耗根本不可行。

答案是：不复制数据，只传递一个「文件描述符」。

这个文件描述符背后就是 DMA-BUF，Linux 内核提供的跨设备、跨进程内存共享框架。Gralloc 则是 Android 在 DMA-BUF 之上封装的图形内存分配器。理解了这两个机制，我们就明白了 Android 渲染管线的「物理层」——BufferQueue 和 SurfaceFlinger 在逻辑层管理缓冲区流转，而 DMA-BUF 和 Gralloc 在物理层保证数据能零拷贝地跨进程移动。

如果我们在 Perfetto 中看到 GPU 内存使用量异常增长，或者在 BufferQueue track 中发现 buffer 释放延迟增大，排查的终点往往会落在 DMA-BUF 的生命周期管理上。

## 为什么需要跨进程零拷贝

让我们先算一笔账。假设一个 App 以 60fps 渲染到一块 1080×2400 的屏幕上，每帧使用 RGBA_8888 格式（每像素 4 字节）：

- 单帧大小：1080 × 2400 × 4 = 约 10.4MB
- 每秒数据量（60fps）：10.4 × 60 = 约 624MB
- 完整传递路径：App → SurfaceFlinger → Display HAL，至少 2 次跨进程传递

如果每次跨进程传递都复制数据，仅渲染管线的数据复制带宽就超过 1.2GB/s。再加上 Camera HAL 预览、Video 解码输出等共享图形内存的场景，系统内存带宽会被完全占满。

更糟糕的是，复制操作本身需要 CPU 参与，主线程或其他线程的 CPU 时间被挤占，直接影响帧率和响应速度。

所以 Android 从第一天起就采用了零拷贝方案：图形数据只存在于一块物理内存上，所有需要访问它的组件（App 的 GPU、SurfaceFlinger 的合成器、Display 控制器、Camera ISP）都直接访问同一块物理内存，中间只传递一个「引用」（文件描述符），不复制任何像素数据。

## DMA-BUF 机制核心原理

DMA-BUF 是 Linux 内核提供的一套 buffer sharing framework，定义在 `include/linux/dma-buf.h`。它的设计目标是让不同的硬件设备（GPU、Camera ISP、Display 控制器、Video 编解码器）和不同的用户进程能够共享同一块物理内存，而不需要复制数据。

### Exporter 与 Importer 模型

DMA-BUF 的核心是一个 exporter-importer 模型：

- **Exporter（导出方）**：拥有这块内存的组件。它负责分配物理内存，并将其「导出」为一个 DMA-BUF 文件描述符（fd）。在 Android 中，Gralloc HAL 就是典型的 exporter——它通过 DMA-BUF Heap 或 ION 分配物理内存，然后导出为 fd。
- **Importer（导入方）**：需要访问这块内存的组件。它拿到 fd 后，通过 `mmap()` 将物理内存映射到自己的地址空间，或者通过 `dma_buf_attach()` + `dma_buf_map_attachment()` 让硬件设备（如 GPU）直接访问。

整个过程的关键点：fd 本身只是一个整数，通过 Binder 的 `BINDER_TYPE_FD` 机制跨进程传递（参见 §1.4 Binder IPC），开销几乎为零。真正的物理内存在整个生命周期中只存在一份。

[已验证: Linux kernel 6.12, drivers/dma-buf/dma-buf.c]

### fd 的跨进程传递

当 producer 侧某个 slot 第一次拿到新的 `GraphicBuffer`，或者走了 `attachBuffer()` 这类把外部分配 buffer 接进来的路径时，底层才会真的发生一次 fd 引用复制。更常见的 steady-state 情况是，producer 和 consumer 两端都已经缓存了这个 slot 对应的 buffer handle，后续每帧 `queueBuffer()` 只提交 slot 编号、fence 和时序元数据，不会重复把整份 `GraphicBuffer` 重新走一遍 Binder。

以 `dequeueBuffer()` 返回 `BUFFER_NEEDS_REALLOCATION` 的路径为例，更接近源码事实的调用过程是：

1. producer 调用 `dequeueBuffer()`，发现某个 slot 需要新 buffer
2. producer 立即调用 `requestBuffer(slot)`，把该 slot 对应的 `GraphicBuffer` 拉到本地
3. Binder 在需要时为目标进程复制一份新的 fd 引用，但仍然指向同一个 DMA-BUF 对象
4. consumer 端只在这个 slot 首次看到新 handle、`attachBuffer()` 或本地 cache miss 时，才需要 import / register
5. 进入稳定阶段后，producer 再次 `queueBuffer(slot, QueueBufferInput)` 时提交的主要是 slot、fence 和帧元数据

注意：fd 编号在不同进程中不同（App 的 fd 42 ≠ SurfaceFlinger 的 fd 15），但它们指向的是同一块物理内存。这就是为什么叫「零拷贝」——数据根本没有移动过。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp; frameworks/native/libs/ui/GraphicBuffer.cpp]

### DMA-BUF 的内核调用链

在内核侧，DMA-BUF 的使用涉及以下关键操作：

- `dma_buf_export()`：将一块物理内存导出为 DMA-BUF fd
- `dma_buf_get()`：通过 fd 获取 dma_buf 结构体的引用
- `dma_buf_attach()` / `dma_buf_map_attachment()`：让另一个设备（如 GPU）获得对这块内存的访问能力
- `dma_buf_put()`：释放引用，当引用计数归零时释放物理内存

Android 的 Gralloc HAL 在底层调用的就是这些内核接口。作为应用层工程师，我们通常不需要直接操作这些内核 API，但理解它们有助于排查 DMA-BUF fd 泄漏等问题。

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

这个过渡对应用层透明，Gralloc HAL 内部只是把 allocator 从 ION 迁到 DMA-BUF Heap，上层 `GraphicBuffer` / `BufferQueue` 的使用方式没有变。但如果我们在做系统级开发或排查底层内存问题，必须先分清哪些路径是 AOSP 通用，哪些只是设备私有实现。

[已验证: 官方文档, source.android.com/docs/core/architecture/kernel/dma-buf-heaps]

## Android Gralloc 与 GraphicBuffer

DMA-BUF 提供了内核级的共享机制，但 Android 还需要一个用户空间层来管理图形缓冲区的分配和访问。这个角色由 Gralloc HAL 和 GraphicBuffer 共同承担。

### Gralloc HAL：图形内存分配器

Gralloc（Graphics Allocator）是 Android 定义的图形内存分配 HAL。它仍然分成两层，但在 Android 16 这个时间点，接口形态不能简单写成“已经完全 AIDL 化”。

- **Allocator HAL**：负责分配 buffer。在 `android-16.0.0_r1` 下，我们能同时看到 `graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl` 和 `graphics/allocator/4.0/IAllocator.hal`。
- **Mapper HAL**：负责 `createDescriptor`、import / free handle、lock / unlock 等映射动作。当前公开 tag 里仍能看到 `graphics/mapper/4.0/IMapper.hal`。

AIDL allocator 的注释写得很直白：如果 `android.hardware.graphics.mapper@4` 仍在使用，旧的 `allocate()` 入口仍然必须实现。也就是说，到 `android-16.0.0_r1` 为止，更准确的说法是 **allocator 已经提供稳定 AIDL 接口，但 mapper@4 兼容路径仍然存在**，不是“整套 Gralloc HAL 已经彻底告别 HIDL”。

Usage flags 这一层也要注意版本语境。很多历史文章还在用 legacy `GRALLOC_USAGE_HW_*` 宏，但 Android 12+ 的主线术语已经落在 `graphics/common/aidl/.../BufferUsage.aidl` 里。对照起来更清楚：

| 历史宏 | Android 12+/AIDL 术语 | 含义 |
|--------|----------------------|------|
| `GRALLOC_USAGE_HW_TEXTURE` | `BufferUsage.GPU_TEXTURE` | GPU 以纹理方式读取 |
| `GRALLOC_USAGE_HW_RENDER` | `BufferUsage.GPU_RENDER_TARGET` | GPU 作为渲染目标写入 |
| `GRALLOC_USAGE_HW_COMPOSER` | `BufferUsage.COMPOSER_OVERLAY` | HWC 作为 overlay 读取 |
| `GRALLOC_USAGE_HW_VIDEO_ENCODER` | `BufferUsage.VIDEO_ENCODER` | 视频编码器读取 |
| `GRALLOC_USAGE_SW_READ_OFTEN` | `BufferUsage.CPU_READ_OFTEN` | CPU 高频读取 |

所以下文默认用 Android 12+/AIDL 术语来讲行为，旧宏只在解释历史资料时顺手提一下。这样读者对照 Android 16 以后源码时，不会把旧宏误当成当前 HAL 的正式字段名。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl; hardware/interfaces/graphics/allocator/4.0/IAllocator.hal; hardware/interfaces/graphics/mapper/4.0/IMapper.hal; hardware/interfaces/graphics/common/aidl/android/hardware/graphics/common/BufferUsage.aidl]

### GraphicBuffer：对缓冲区的封装

GraphicBuffer 是 Android framework 中对图形缓冲区的核心封装类，定义在 `frameworks/native/libs/ui/GraphicBuffer.cpp`。它充当像素数据的「护照」——包含了所有让不同进程和硬件能访问这块内存所需的信息：

- **DMA-BUF fd**：指向实际物理内存的文件描述符
- **元数据**：width、height、stride（行跨度）、format（像素格式）、usage flags
- **buffer_handle_t**：底层的 native handle，Gralloc 分配时返回的 opaque 数据结构

GraphicBuffer 的跨进程传递通过 Binder 实现。具体来说，它使用 flatten/unflatten 机制：

1. 发送方调用 `flatten()` 将 GraphicBuffer 序列化为 Parcel 中的原始数据（元数据 + fd 数组）
2. Binder 驱动在传输过程中将 fd 转换为目标进程的新 fd
3. 接收方调用 `unflatten()` 从 Parcel 中反序列化，重建 GraphicBuffer 对象

```cpp
// frameworks/native/libs/ui/GraphicBuffer.cpp
// @ AOSP android-16.0.0_r1
status_t GraphicBuffer::flatten(void*& buffer, size_t& size,
                                 int*& fds, size_t& count) const {
    // 将 width/height/stride/format/usage 等元数据写入 buffer
    // 将 DMA-BUF fd 写入 fds 数组
    // Binder 驱动负责在跨进程时转换 fds
}
```

这段代码说明了一个关键事实：GraphicBuffer 的跨进程传递就是「元数据 + fd」的传递。像素数据始终停留在原始的物理内存中，从未被复制。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp]

### 从 AOSP 源码看分配过程

当 App 调用 `Surface.dequeueBuffer()` 获取一个缓冲区时，底层经历了一条相当长的调用链：

1. `Surface.dequeueBuffer()` → 通过 Binder 调用 BufferQueue 的 `dequeueBuffer()`
2. `BufferQueue` 如果需要分配新的 GraphicBuffer，调用 `GraphicBufferAllocator`
3. `GraphicBufferAllocator` 通过 Gralloc Allocator HAL 分配内存
4. Gralloc Allocator HAL 调用 DMA-BUF Heap（或 SoC 厂商自定义的 allocator）分配物理内存
5. 返回一个包含 DMA-BUF fd 的 `buffer_handle_t`

如果 BufferQueue 的 slot 中已经有合适的 GraphicBuffer（大小和格式匹配），则复用已有的缓冲区，不需要重新分配。这就是为什么我们说 BufferQueue 的「slot」持有的是 GraphicBuffer 的引用（参见 §2.13）——slot 本身不移动，producer / consumer 两端维护的是 slot 到 buffer handle 的镜像关系。

这里还有一个容易写错的版本点：在 `android-16.0.0_r1` 中，我们能同时看到 AIDL allocator 和 HIDL allocator / mapper 接口，所以更准确的说法不是“Android 16 已经完全改成 AIDL”，而是 allocator 已提供 AIDL 入口，mapper@4 兼容路径仍在。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl; hardware/interfaces/graphics/allocator/4.0/IAllocator.hal; hardware/interfaces/graphics/mapper/4.0/IMapper.hal]

## 跨进程传递的实际路径

了解了 DMA-BUF 和 Gralloc 的机制后，让我们跟踪一帧数据从 App 到屏幕的完整传递路径，看看每一步发生了什么。

### 一帧的零拷贝旅程

如果按 classic BufferQueue 路径看，一帧通常是这样走的：

1. **App 获取 slot**：`dequeueBuffer()` 返回 slot。只有返回 flags 带 `BUFFER_NEEDS_REALLOCATION` 时，producer 才会继续 `requestBuffer(slot)` 拿到新的 `GraphicBuffer`。
2. **App 渲染写入**：RenderThread / GPU 把像素写进这个 slot 绑定的 DMA-BUF。
3. **App 提交帧**：`queueBuffer(slot, QueueBufferInput)` 提交的是 slot 编号、fence、crop、timestamp 等元数据。steady-state 下，这一步不会每帧重传完整 `GraphicBuffer` handle。
4. **consumer 导入新 handle**：只有该 slot 第一次出现新 buffer、`attachBuffer()`，或者本地 cache miss 时，consumer 才需要 import / register 新 handle。
5. **consumer 读取并释放**：consumer 读取同一块物理内存，处理完成后 `releaseBuffer()`，slot 重新回到 producer 可用状态。

如果按现代应用窗口路径看，App 和 SurfaceFlinger 之间常常还会插入一层 BLASTBufferQueue。它会先在本地 consumer 侧 `acquireNextBufferLocked()`，再通过 `SurfaceControl.Transaction` 把 buffer 提交给 SurfaceFlinger。这一层的作用是把窗口事务和 buffer latch 绑在一起，而不是改变 DMA-BUF 的共享语义。我们在 App trace 里看到的 `queueBuffer()`，通常只是把帧交给本地 BLAST consumer，不等于 SurfaceFlinger 在这一刻首次 import 了新 handle。

[图：classic BufferQueue 路径 vs BLAST window path。左侧画 producer `dequeueBuffer()` → `requestBuffer()` → `queueBuffer(slot, QueueBufferInput)` → consumer `acquireBuffer()`；右侧画 App → BLASTBufferQueue → `SurfaceControl.Transaction` → SurfaceFlinger，并标出“新 handle 首次出现时才 import”]

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/gui/BufferQueueProducer.cpp; frameworks/native/libs/gui/BLASTBufferQueue.cpp]

### 为什么说 BufferQueue 是「逻辑通道」

从上面的流程可以看出，BufferQueue 管理的是缓冲区的**状态流转**（谁在用、谁可以用），而 DMA-BUF 管理的是**物理内存的共享**（谁在访问、怎么访问）。两者是正交的：

- BufferQueue：逻辑层，管理 slot 的 DEQUEUED / QUEUED / FREE / ACQUIRED 状态
- DMA-BUF + Gralloc：物理层，管理 fd 的创建、传递和映射

这就是为什么在 §2.13 中我们可以完全不讲 DMA-BUF 也能说清楚 BufferQueue 的行为——BufferQueue 的状态机不关心底层用什么机制共享内存。但当需要理解「为什么 dequeueBuffer 会阻塞」或「为什么缓冲区没有释放」时，就需要深入到 DMA-BUF 这一层了。

## 在 Perfetto 中的表现

DMA-BUF 和 Gralloc 本身没有专门的 Perfetto Track，但它们的行为会通过多个间接 Track 体现出来。

### GPU 内存使用量

在 Perfetto 的 `gfx` 或 `gpu` 相关 Track 中，可以看到 GPU 内存的使用趋势。如果 DMA-BUF fd 泄漏（进程持有 fd 但不再使用），GPU 内存会持续增长而不回落。这种模式下，增长曲线呈阶梯状——每次分配新 buffer 不释放旧的。

### BufferQueue Track 中的 Buffer 状态

BufferQueue Track（如 `BufferQueue - <package> (<surface>)`）中可以看到每个 slot 的 buffer 状态变化。如果某个 buffer 长时间停留在 ACQUIRED 状态不释放，可能意味着 SurfaceFlinger 端的 importBuffer 或 fence 等待出了问题（fence 机制将在 §2.16 详细讨论）。

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

这是最常见的 DMA-BUF 相关问题，但根因经常被写错。`unflatten()` 是反序列化入口，不是清理 API。真正的释放发生在 `GraphicBuffer::~GraphicBuffer()` 里的 `free_handle()`：如果 buffer 由 `ownHandle` 持有，会走 `mBufferMapper.freeBuffer(handle)`；如果由 `ownData` 持有，会走 `GraphicBufferAllocator::free(handle)`。

所以排查时我们更该盯住三类路径：

- imported handle 生命周期过长，consumer 侧一直没走到 `freeBuffer`
- allocator / mapper 的释放路径漏调，或者异常分支忘了 `close()` / 注销 handle
- producer / consumer 断开后，本地 cache、buffer cache 或 fence 还在持有引用

这类问题的共同特征是，fd 数量和 DMA-BUF 占用一起上涨，但 `GraphicBuffer` 对象本身不一定还在 Java 层可见。排查方法仍然是通过 `/proc/<pid>/fd/` 统计 DMA-BUF 类型的 fd 数量，再结合 Perfetto 或 meminfo 看 buffer 占用是否只涨不回。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp]
[待补充：Trace 截图展示 fd 泄漏时 GPU 内存增长的表现]

### Gralloc 分配延迟

首次分配 GraphicBuffer 时，Gralloc 需要与内核交互（通过 DMA-BUF Heap ioctl），这个过程的延迟通常在 1-5ms 之间。对于 60fps 的 App 来说，一帧只有 16.6ms，首帧分配可能占用 10-30% 的帧时间预算。

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

优化方向：确保 Camera 和 App 的缓冲区使用不同的 DMA-BUF Heap（如果 SoC 支持），避免在同一个内存控制器上争抢带宽。

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

### Android 16：allocator AIDL 与 mapper@4 共存

到 `android-16.0.0_r1` 为止，我们还能同时看到 `graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl`、`graphics/allocator/4.0/IAllocator.hal` 和 `graphics/mapper/4.0/IMapper.hal`。AIDL allocator 的注释甚至直接写明，如果 `android.hardware.graphics.mapper@4` 仍在使用，旧的 `allocate()` 入口仍要实现。

所以这一阶段更稳妥的说法是，allocator 接口已经提供稳定 AIDL 版本，但 mapper@4 兼容路径还在，系统并不是“一刀切地彻底 AIDL 化”。至于 Android 17 是否完全收口到 AIDL，需要等正式 tag 再看；在当前稿件里，我们只按已经能核实的接口形态来写，不把“IPC 更少”这类效果判断提前当成结论。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl; hardware/interfaces/graphics/allocator/4.0/IAllocator.hal; hardware/interfaces/graphics/mapper/4.0/IMapper.hal]
[待验证: Android 17 正式 tag 下 mapper 接口是否仍保留 HIDL 兼容层]

## 与其他机制的关系

DMA-BUF 和 Gralloc 是 Android 图形栈的「物理基础设施」，它们与渲染管线中几乎所有组件都有交互：

- **§2.3 VSync**：VSync 信号驱动整个渲染管线的节奏，DMA-BUF 的 fence 机制（§2.16）与 VSync 时序紧密配合
- **§2.4 Choreographer**：Choreographer 的 `doFrame()` 触发一帧的渲染，渲染结果最终写入 DMA-BUF
- **§2.5 MainThread/RenderThread**：RenderThread 通过 GPU 将渲染指令写入 DMA-BUF 对应的 GraphicBuffer
- **§2.6 SurfaceFlinger**：SurfaceFlinger 通过 DMA-BUF fd 读取 App 渲染的帧数据进行合成
- **§2.13 BufferQueue**：BufferQueue 管理 GraphicBuffer 的状态流转，DMA-BUF 提供底层的物理共享
- **§2.16 Sync Fence**：Fence 机制保证「GPU 写完再读」，建立在 DMA-BUF 的 fence 框架之上
- **§1.4 Binder IPC**：DMA-BUF fd 通过 Binder 的 `BINDER_TYPE_FD` 跨进程传递
- **§4.2 Linux 内存管理**：DMA-BUF Heap 的物理内存分配依赖 Linux 内核的 buddy allocator 和 CMA

## 常见问题与误区

### 「GraphicBuffer 里存的就是像素数据」

不是。GraphicBuffer 存的是 DMA-BUF fd + 元数据（宽高、格式等），像素数据在 fd 指向的物理内存中。GraphicBuffer 本身只是一个「护照」。

### 「跨进程传递 GraphicBuffer 会复制像素」

不会。Binder 传递的是 fd（一个整数），不是像素数据。Binder 驱动在目标进程创建新 fd 指向同一个 DMA-BUF 对象。整个过程零拷贝。

### 「所有设备上的 Gralloc 实现都一样」

差异很大。Gralloc 是 SoC 厂商实现的 HAL，Qualcomm（Adreno GPU）、MediaTek（Mali/Immortalis GPU）、Samsung 各有不同。不同实现可能：

- 使用不同的 DMA-BUF Heap 策略
- 对同一组 usage flags 选择不同的内存布局
- 分配延迟差异显著（1ms vs 5ms）
- 对 GPU/CPU 共享访问的优化程度不同

这就是为什么同样的 App 在不同设备上的图形性能可能差异很大，即使 CPU/GPU 算力相近。

### 「DMA-BUF 内存泄漏只影响图形性能」

DMA-BUF 泄漏影响的是**物理内存**。如果泄漏的是来自 CMA Heap 的物理连续内存，会导致 Camera、Display 等需要物理连续内存的硬件无法分配到足够的缓冲区，直接导致功能异常（Camera 预览黑屏、Display 闪烁等），不仅仅是帧率下降。

## 参考资料

- AOSP 源码：
  - `frameworks/native/libs/ui/GraphicBuffer.cpp` — GraphicBuffer 的 flatten/unflatten 实现
  - `frameworks/native/libs/ui/GraphicBufferAllocator.cpp` — 分配器的框架层封装
  - `hardware/interfaces/graphics/allocator/` — Gralloc Allocator HAL 接口定义
  - `hardware/interfaces/graphics/mapper/` — Gralloc Mapper HAL 接口定义
  - `drivers/dma-buf/` — Linux 内核 DMA-BUF 框架源码
- 官方文档：
  - [Android Graphics Architecture](https://source.android.com/docs/core/graphics/architecture)
  - [DMA-BUF Heaps](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)
  - [BufferQueue](https://source.android.com/docs/core/graphics/bufferqueue)
- Linux 内核文档：
  - [DMA-BUF documentation](https://www.kernel.org/doc/html/latest/driver-api/dma-buf.html)
