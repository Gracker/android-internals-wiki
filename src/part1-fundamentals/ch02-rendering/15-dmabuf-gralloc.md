---
title: "DMA-BUF、Gralloc 与跨进程图形内存共享"
chapter: "2.15"
section: "2.15"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-16.0.0_r1, Linux kernel 6.12"
confidence: medium
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
sources:
  - type: aosp
    path: "frameworks/native/libs/ui/GraphicBuffer.cpp"
  - type: aosp
    path: "hardware/interfaces/graphics/mapper/"
  - type: aosp
    path: "hardware/interfaces/graphics/allocator/"
  - type: official
    path: "https://source.android.com/docs/core/graphics/architecture"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps"
  - type: kernel
    path: "drivers/dma-buf/"
tags: [dma-buf, gralloc, graphicbuffer, zero-copy, ion, rendering, cross-process, dma-heap]
related_chapters: ["2.6", "2.13", "2.16", "4.2", "1.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "素材驱动+AOSP结构+每日信息"
gap_score: "17/20"
---

# 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享

## 为什么要了解 DMA-BUF 和 Gralloc

在 §2.13 中我们讲了 BufferQueue 如何管理缓冲区的流转——App 通过 `dequeueBuffer` 拿到缓冲区，画完一帧后通过 `queueBuffer` 提交给 SurfaceFlinger。但有一个关键问题被我们跳过了：缓冲区里的像素数据，到底是怎么在 App 进程和 SurfaceFlinger 进程之间传递的？

一帧 1080p RGBA 的像素数据大约 8MB，120Hz 屏幕每秒需要 120 帧。如果每次跨进程传递都要复制像素数据，每秒需要 960MB 的内存带宽——这还不算 SurfaceFlinger 合成后传给 Display HAL 的部分。在移动设备上，这种带宽消耗根本不可行。

答案是：不复制数据，只传递一个「文件描述符」。

这个文件描述符背后就是 DMA-BUF，Linux 内核提供的跨设备、跨进程内存共享框架。Gralloc 则是 Android 在 DMA-BUF 之上封装的图形内存分配器。理解了这两个机制，我们就明白了 Android 渲染管线的「物理层」——BufferQueue 和 SurfaceFlinger 在逻辑层管理缓冲区流转，而 DMA-BUF 和 Gralloc 在物理层保证数据能零拷贝地跨进程移动。

如果你在 Perfetto 中看到 GPU 内存使用量异常增长、或者 BufferQueue track 中 buffer 释放延迟增大，排查的终点往往会落在 DMA-BUF 的生命周期管理上。

## 为什么需要跨进程零拷贝

让我们先算一笔账。假设一个 App 以 60fps 渲染到一块 1080×2400 的屏幕上，每帧使用 RGBA_8888 格式（每像素 4 字节）：

- 单帧大小：1080 × 2400 × 4 = 约 10.4MB
- 每秒数据量（60fps）：10.4 × 60 = 约 624MB
- 完整传递路径：App → SurfaceFlinger → Display HAL，至少 2 次跨进程传递

如果每次跨进程传递都复制数据，仅渲染管线的数据复制带宽就超过 1.2GB/s。再加上 Camera HAL 预览、Video 解码输出等共享图形内存的场景，系统内存带宽会被完全占满。

更糟糕的是，复制操作本身需要 CPU 参与，这意味着主线程或其他线程的 CPU 时间被挤占，直接影响帧率和响应速度。

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

当一个 GraphicBuffer 需要从 App 进程传到 SurfaceFlinger 进程时，底层发生的事情是：

1. App 进程持有 DMA-BUF 的 fd（比如 fd 42）
2. App 通过 Binder 发送事务，事务中包含一个 `BINDER_TYPE_FD` 类型的对象
3. Binder 驱动在目标进程中创建一个新的 fd（比如 fd 15），指向同一个 DMA-BUF 对象
4. SurfaceFlinger 进程拿到 fd 15，通过它访问同一块物理内存

注意：fd 编号在不同进程中不同（App 的 fd 42 ≠ SurfaceFlinger 的 fd 15），但它们指向的是同一块物理内存。这就是为什么叫「零拷贝」——数据根本没有移动过。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp — flatten/unflatten 机制]

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

常见的 DMA-BUF Heap 类型：

| Heap 名称 | 设备路径 | 特点 | 用途 |
|-----------|---------|------|------|
| system | `/dev/dma_heap/system` | 虚拟连续、可缓存 | 通用图形缓冲区 |
| system_uncached | `/dev/dma_heap/system_uncached` | 虚拟连续、不可缓存 | 需要硬件一致性访问的场景 |
| cma | `/dev/dma_heap/default_cma_region` | 物理连续 | Camera、Display 等需要物理连续内存的硬件 |
| vendor-secure | `/dev/dma_heap/system-secure-<vendor>` | 受保护内存 | DRM、安全视频解码 |

这个过渡对应用层透明——Gralloc HAL 内部从调用 ION 换成了调用 DMA-BUF Heap，上层 API 不变。但如果你在做系统级开发或排查底层内存问题，需要知道这个变化。

## Android Gralloc 与 GraphicBuffer

DMA-BUF 提供了内核级的共享机制，但 Android 还需要一个用户空间层来管理图形缓冲区的分配和访问。这个角色由 Gralloc HAL 和 GraphicBuffer 共同承担。

### Gralloc HAL：图形内存分配器

Gralloc（Graphics Allocator）是 Android 定义的 HAL 接口，负责分配适合图形使用的内存缓冲区。它的接口分为两部分：

- **Allocator HAL**（`hardware/interfaces/graphics/allocator/`）：负责分配缓冲区。调用时需要指定 width、height、pixel format 和 usage flags。
- **Mapper HAL**（`hardware/interfaces/graphics/mapper/`）：负责将缓冲区映射到进程的地址空间，以及注册/注销来自其他进程的缓冲区 handle。

Usage flags 是 Gralloc 的关键设计——它告诉 Gralloc 这块内存会被哪些硬件访问，以便选择最优的物理布局。常见的 usage：

- `GRALLOC_USAGE_HW_RENDER`：GPU 渲染写入
- `GRALLOC_USAGE_HW_TEXTURE`：GPU 作为纹理读取
- `GRALLOC_USAGE_HW_COMPOSER`：HWC 合成使用
- `GRALLOC_USAGE_HW_VIDEO_ENCODER`：视频编码器读取
- `GRALLOC_USAGE_SW_READ_OFTEN`：CPU 频繁读取

当一块缓冲区同时标记了 `HW_RENDER` 和 `HW_COMPOSER`（这在渲染管线中非常常见），Gralloc 需要选择一种对所有参与方都高效的内存布局。不同 SoC 厂商的 Gralloc 实现对此有不同的优化策略——这就是为什么同样分辨率的缓冲区在不同设备上的分配延迟和内存占用可能差异很大。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/]

### GraphicBuffer：对缓冲区的封装

GraphicBuffer 是 Android framework 中对图形缓冲区的核心封装类，定义在 `frameworks/native/libs/ui/GraphicBuffer.cpp`。它不是像素数据本身，而是像素数据的「护照」——包含了所有让不同进程和硬件能访问这块内存所需的信息：

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

这段代码说明了一个关键事实：GraphicBuffer 的跨进程传递，本质上就是「元数据 + fd」的传递。像素数据始终停留在原始的物理内存中，从未被复制。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/GraphicBuffer.cpp]

### 从 AOSP 源码看分配链路

当 App 调用 `Surface.dequeueBuffer()` 获取一个缓冲区时，底层经历了一条相当长的调用链：

1. `Surface.dequeueBuffer()` → 通过 Binder 调用 BufferQueue 的 `dequeueBuffer()`
2. `BufferQueue` 如果需要分配新的 GraphicBuffer，调用 `GraphicBufferAllocator`
3. `GraphicBufferAllocator` 通过 Gralloc Allocator HAL 分配内存
4. Gralloc Allocator HAL 调用 DMA-BUF Heap（或 SoC 厂商自定义的 allocator）分配物理内存
5. 返回一个包含 DMA-BUF fd 的 `buffer_handle_t`

如果 BufferQueue 的 slot 中已经有合适的 GraphicBuffer（大小和格式匹配），则复用已有的缓冲区，不需要重新分配。这就是为什么我们说 BufferQueue 的「slot」持有的是 GraphicBuffer 的引用（参见 §2.13）——slot 本身不移动，移动的是每个 slot 中 buffer 的状态（DEQUEUED / QUEUED / FREE / ACQUIRED）。

[待验证: Gralloc Allocator AIDL 接口在 Android 16 中是否已完全替代 HIDL 接口]

## 跨进程传递的实际路径

了解了 DMA-BUF 和 Gralloc 的机制后，让我们跟踪一帧数据从 App 到屏幕的完整传递路径，看看每一步发生了什么。

### 一帧的零拷贝旅程

1. **App 获取缓冲区**：`dequeueBuffer()` → 如果 slot 为空或尺寸不匹配，触发 GraphicBuffer 分配（Gralloc → DMA-BUF Heap → 物理内存）。App 拿到一个 GraphicBuffer，其中包含指向物理内存的 DMA-BUF fd。

2. **App 渲染写入**：GPU 通过 fd 访问物理内存，将渲染结果直接写入这块 DMA-BUF。此时 App 进程和 GPU 看到的是同一块物理内存。

3. **App 提交缓冲区**：`queueBuffer()` → 通过 Binder 将 GraphicBuffer 的 handle（包含 fd 和元数据）传递给 BufferQueue 的消费者端。Binder 驱动在 SurfaceFlinger 进程中创建新的 fd 指向同一块物理内存。

4. **SurfaceFlinger 获取缓冲区**：`acquireBuffer()` → SurfaceFlinger 拿到 GraphicBuffer handle，通过 Gralloc Mapper HAL 将其「注册」到 SurfaceFlinger 进程。注册过程告诉 SurfaceFlinger 的 GPU 驱动如何访问这块内存。

5. **SurfaceFlinger 合成**：GPU 或 HWC 直接从这块 DMA-BUF 读取像素数据作为纹理进行合成。

6. **SurfaceFlinger 释放缓冲区**：合成完成后，`releaseBuffer()` → GraphicBuffer 通过 Binder 归还给 App 端的 BufferQueue，可以再次被 `dequeueBuffer()` 获取。

7. **Display HAL 显示**：HWC 将合成后的帧通过 DMA-BUF 传递给 Display 控制器，Display 直接从 DMA-BUF 读取像素并显示。

[图：一帧数据从 App GPU → BufferQueue → SurfaceFlinger → Display HAL 的传递路径，标注每步涉及的 DMA-BUF fd 传递，突出「物理内存只有一份」的特点]

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

这是最常见的 DMA-BUF 相关问题。每个打开的 fd 都持有对 DMA-BUF 的引用，阻止物理内存被释放。泄漏的典型原因：

- GraphicBuffer 对象被 GC 回收前没有调用 `unflatten` 清理 fd
- Native 代码中 `close()` 调用缺失或路径遗漏
- Binder 事务异常导致 fd 在传输过程中丢失

排查方法：通过 `/proc/<pid>/fd/` 统计 DMA-BUF 类型的 fd 数量，如果数量持续增长不回落，就存在泄漏。

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

### Android 16/17：Gralloc AIDL 化

Android 16 开始将 Gralloc HAL 从 HIDL 迁移到 AIDL 接口。AIDL 提供更好的性能（更少的 IPC 开销）和更灵活的类型系统。对应用层透明，但系统开发者需要注意 HAL 接口的变更。

[待验证: Android 17 Gralloc AIDL 接口是否完全替代 HIDL]

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

差异很大。Gralloc 是 SoC 厂商实现的 HAL，Qualcomm（Adreno GPU）、MediaTek（Mali/Immortalis GPU）、Samsung各有不同。不同实现可能：

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
