---
title: DMA-BUF、Gralloc 与跨进程图形内存共享
chapter: '2.15'
section: '2.15'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37); earlier ION and
  Gralloc generations retained only as version history
last_verified: '2026-07-25'
last_verified_against: Android 17 / API 37 / android-17.0.0_r1; hardware/interfaces
  android-17.0.0_r1; system/memory/libdmabufheap android-17.0.0_r1;
  android17-6.18-2026-06_r6; Writer rendering_pipelines S08/S11/S12
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/GraphicBuffer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/GraphicBufferAllocator.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/GraphicBufferMapper.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/ui/Gralloc5.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/mapper/stable-c/include/android/hardware/graphics/mapper/IMapper.h
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/graphics/common/aidl/android/hardware/graphics/common/BufferUsage.aidl
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/libdmabufheap/+/android-17.0.0_r1/BufferAllocator.cpp
- type: official
  path: https://source.android.com/docs/core/graphics/architecture
- type: official
  path: https://source.android.com/docs/core/graphics/reduce-consumption
- type: official
  path: https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps
- type: official
  path: https://developer.android.com/ndk/reference/group/a-hardware-buffer
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://perfetto.dev/docs/quickstart/heap-profiling
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/driver-api/dma-buf.rst
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-buf.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/dma-buf.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-heap.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S08_native_graphics_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S11_camera_type.md
- type: material
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
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
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch02-rendering/24-graphic-memory-dmabuf-gralloc-16kb-boundary.md"
---

# 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享

BufferQueue 负责回答“哪个 slot（可复用的槽位索引）归谁使用”，Gralloc（graphics allocator，图形 buffer 分配接口）负责回答“按什么规格分配、怎样导入和访问”，DMA-BUF 负责回答“同一份 buffer 怎样被多个设备驱动和进程引用”。三者解决不同问题。

先区分几个贯穿全文的对象：handle 是描述 buffer 及其文件描述符、私有整数等信息的不透明句柄；raw handle 是尚未导入当前进程的传输形态，imported handle 是 Mapper 导入后可供当前进程使用的形态；backing storage 是真正承载像素和元数据的底层存储；attachment 则表示某个硬件设备已经把这块 DMA-BUF 接入自己的访问路径。关闭一个 fd、释放一个 handle、解除一次 attachment 和回收 backing storage 是四个不同动作。

理解这组边界后，许多常见现象会变得清楚：

- Binder 传递 `GraphicBuffer` 时会复制元数据和文件描述符引用，不会复制整帧像素；
- “零拷贝”只描述跨模块共享这一段，不保证后续没有 GPU 合成、格式转换、resolve（把多重采样或中间结果转成目标图像）或 CPU copy；
- handle 传到另一个进程后还要由 Mapper（Gralloc 的导入与访问接口）执行 import，得到该进程可用的 imported handle；
- 同一个 BufferQueue slot 在两端都有缓存，稳定阶段通常只传 slot、fence（异步工作完成信号）和帧元数据；
- fd、imported handle、设备 attachment、内存映射和队列引用都会延长生命周期，关闭某一个 fd 不代表 backing storage 立即释放。

分析以 Android 17/API 37、`android-17.0.0_r1` 为用户空间锚点，内核侧以 `android17-6.18-2026-06_r6` 为锚点。Gralloc 的分配策略和 handle 布局由 SoC（System on Chip，系统级芯片）厂商实现，AOSP（Android Open Source Project）只能证明接口与框架行为。

## 1. 为什么图形 buffer 不能按普通 Binder 数据传

一张 1080 × 2400、每像素 4 字节的未压缩 RGBA 图像，按紧密排布估算约为 9.9 MiB（1 MiB = 1,048,576 字节）：

```text
1080 × 2400 × 4 = 10,368,000 bytes ≈ 9.9 MiB
```

这个数只用于说明数量级。Gralloc 分配还可能包含 stride padding（每行末尾的对齐填充）、多个 plane（分别存放亮度、色度等分量的平面）、压缩元数据、对齐区和实现私有区域，不能用它推算设备上的准确占用。

若每帧都把像素从应用复制到 SurfaceFlinger，60 fps 时单次 IPC（跨进程调用）边界就会增加约 593 MiB/s 的读写数据量。Android 因而让参与者共享 buffer，并用 handle 传递访问能力。这里仍会产生真实内存流量：GPU 渲染要写，SurfaceFlinger 或 HWC（Hardware Composer，硬件合成器）要读，CLIENT composition（由 RenderEngine/GPU 合成）还会读取源图层，并写入 client target（交给显示系统的 GPU 合成结果）。共享避免的是跨进程所有权转移所需的整帧复制。

## 2. 从 API 到内核的分层

下图用于区分对象、接口和内核资源。箭头表示控制或引用关系，不表示每台设备都由 DMA-BUF Heap 提供 backing storage。AIDL/HIDL 是 Android HAL 的接口描述机制，Stable-C 则用稳定 C ABI（二进制调用约定）连接 framework 与厂商 Mapper。

```mermaid
flowchart TD
    API["Surface / HardwareBuffer / AHardwareBuffer"]
    GB["GraphicBuffer<br/>尺寸、格式、usage、native handle"]
    BQ["BufferQueue / BLAST<br/>slot 与帧元数据"]
    Alloc["GraphicBufferAllocator<br/>选择 Gralloc 2/3/4/5 wrapper"]
    AIDL["Stable AIDL IAllocator"]
    Mapper["HIDL IMapper 2-4<br/>或 Stable-C AIMapper 5/6"]
    Vendor["vendor allocator / mapper"]
    Handle["buffer_handle_t / native_handle<br/>fds + ints"]
    DmaHeap["DMA-BUF Heap 或 vendor allocator"]
    DmaBuf["struct dma_buf<br/>fd / attachment / sg_table"]
    Devices["GPU / display / camera / codec"]
    Fence["dma-fence / sync_file"]

    API --> GB
    GB --> BQ
    GB --> Alloc --> AIDL --> Vendor
    GB --> Mapper --> Vendor
    Vendor --> Handle
    Vendor --> DmaHeap --> DmaBuf
    Handle --> DmaBuf
    DmaBuf --> Devices
    Fence -. 异步完成关系 .-> Devices
```

图中的 `sg_table` 是 scatter-gather table，即把多个物理页段描述成一份 DMA 映射的数据结构。`buffer_handle_t` 是不透明类型，也是 `native_handle_t` 的图形缓冲区别名，可以带多个 fd 和整数；AOSP 不规定“第一个 fd 必定是像素 DMA-BUF”，也不规定厂商私有整数的意义。只能通过 Mapper metadata API、厂商文档和内核 fd 信息解释具体 handle。

### 2.1 GraphicBuffer 与 AHardwareBuffer

`GraphicBuffer` 是 framework native 层的包装对象，保存 width、height、stride（相邻两行起点之间的跨度）、format、layer count、usage（预期访问方式）、generation number（区分 Surface 重新配置前后 buffer 的代次）、ID 和 handle。像素不在 C++ 对象内部。

公开 NDK（Native Development Kit）API 使用 `AHardwareBuffer`。它允许 native 应用分配、引用、描述、CPU lock（映射并取得 CPU 可访问地址），并把同一 buffer 导入 EGL 或 Vulkan。Java `HardwareBuffer` 包装同类 native 对象。应用应先用 `AHardwareBuffer_isSupported()` 或 `HardwareBuffer.isSupported()` 检查 format、layer 与 usage 组合；系统版本达到 API 下限也不能保证任意组合可分配。

### 2.2 Gralloc Allocator

Android 17 的主线分配接口是 Stable AIDL `IAllocator`。Stable AIDL 表示接口可以跨 framework/vendor 版本稳定通信。当前接口包含：

- `allocate2(BufferDescriptorInfo, count)`：按结构化 descriptor（分配规格描述）分配；
- `isSupported()`：判断 descriptor 是否受支持，内存等资源耗尽仍可能让后续实际分配失败；
- `getIMapperLibrarySuffix()`：定位 vendor Stable-C Mapper SP-HAL（同进程加载的稳定厂商 HAL 库）；
- `isMultiViewSupported()`/`allocateMultiView()`：Android 17 源码中的 multi-view（同一分配具有多个视图）接口。

旧 `allocate(byte[] descriptor, count)` 仍在 AIDL 中，但注释明确：配合 `AIMAPPER_VERSION_5` 时已由 `allocate2()` 替代；设备仍使用 `mapper@4` 时，旧入口还需要实现。Android 17 framework 同时保留新旧 vendor 接口适配，不能概括为“Gralloc 已完全改成 AIDL”。

`BufferDescriptorInfo` 包含名称、宽高、layer count、format、usage、`reservedSize`（为调用方保留的额外区域大小）与 `additionalOptions`。`additionalOptions` 用于不改变总体 usage、却影响分配方式的扩展条件；AIDL 注释以 surface compression level（表面压缩级别）为例。它不是公开的 `AHardwareBuffer_allocateWithOptions()`，NDK 没有这个函数。

### 2.3 Gralloc Mapper

Mapper 负责把 raw handle 导入当前进程，并提供 metadata（描述 buffer 布局和属性的元数据）、CPU lock/unlock、reserved region（保留区域）和释放 imported handle 等操作。Android 17 源码中：

- IMapper 2–4 使用 HIDL；
- C 风格 `AIMapper` 从版本 5 开始；
- `AIMapperV6` 增加 multi-view 查询与 view handle 导入；
- framework 的 `GraphicBufferMapper` 把 Stable-C 路径归在 `GRALLOC_5` wrapper 下，同时保留 Gralloc 2/3/4 wrapper。

Stable-C `IMapper.h` 明确说明它是 `libui` 与 vendor Mapper 之间的 SP-HAL 接口，不是给普通应用直接调用的 NDK API。

### 2.4 Usage 描述访问者，不承诺执行路径

usage 会影响 allocator 选择内存布局、压缩、cache policy（缓存策略）和安全属性。常见对应关系如下：

| 现代 usage | 典型含义 |
|---|---|
| `CPU_READ_*`/`CPU_WRITE_*` | 允许通过 Mapper/AHardwareBuffer lock 进行 CPU 访问 |
| `GPU_SAMPLED_IMAGE` | GPU 作为纹理或 sampled image 读取 |
| `GPU_COLOR_OUTPUT`/`GPU_FRAMEBUFFER` | GPU 作为 framebuffer attachment 写入 |
| `COMPOSER_OVERLAY` | buffer 可能交给 Composer HAL（显示合成硬件抽象层）使用 |
| `VIDEO_ENCODE` | 视频编码器读取 |
| `PROTECTED_CONTENT` | 仅允许受保护路径，禁止普通 CPU 访问 |
| `FRONT_BUFFER` | 请求 front-buffer（直接更新当前显示使用的前台 buffer）用途，其他 usage 会影响具体行为 |

usage 表达“哪些访问必须被支持”。带 `COMPOSER_OVERLAY` 不保证 HWC 一定分配 overlay plane（显示硬件可直接合成的平面）；带 CPU usage 也不保证 lock 没有同步和 cache maintenance（缓存维护）成本。format 与 usage 的组合要通过 `isSupported()` 验证。

## 3. DMA-BUF：共享框架，不是唯一分配器

Linux DMA-BUF 把共享对象表示为 `struct dma_buf`，并能以 fd（文件描述符）暴露给用户空间。Android 17 内核文档将相关能力分成三个主要原语：

- `dma-buf`：共享 buffer，内部关联 backing storage 与 attachment；
- `dma-fence`：异步硬件工作完成信号；
- `dma-resv`：为某个 dma-buf 管理一组 implicit synchronization fence（由驱动隐式关联的同步依赖）。

Android 图形栈大量使用显式 fence fd；不能因为内核提供 `dma-resv`，就假设所有 Android GPU、HWC 与 Camera 访问都由 implicit sync 自动排序。

### 3.1 Exporter 与 importer

Exporter（导出方）决定怎样分配 backing storage，实现 `dma_buf_ops`，并通过 `dma_buf_export()` 建立共享对象。Importer（导入方）通过 fd 获得引用，再为自己的硬件设备建立 attachment 与 DMA mapping（设备可访问的 DMA 地址映射）。典型内核接口包括：

- `dma_buf_get()` / `dma_buf_put()`：取得与释放引用；
- `dma_buf_attach()` / `dma_buf_detach()`：把设备关联到共享对象；
- `dma_buf_map_attachment()`/`dma_buf_unmap_attachment()`：获得或释放适合该设备 DMA 的 scatter-gather 映射，即把多个不连续内存段组成设备可访问的列表；
- `dma_buf_begin_cpu_access()`/`dma_buf_end_cpu_access()`：在 CPU 访问边界处理 coherency（CPU 与设备看到一致内容所需的同步和缓存维护）。

Importer 看到的是适合自身设备的 DMA 地址与 scatterlist。IOMMU（输入输出内存管理单元）可以把设备看到的地址映射到一组物理页，因此“共享一份 buffer”不表示所有设备使用同一个物理地址；scatter-gather、压缩布局与迁移也可能由 exporter 和驱动处理。

### 3.2 fd 传递与引用

Binder 把 fd 传到目标进程时，会在那里安装一个指向同一 file object（内核文件对象）的 fd。两个进程中的整数编号通常不同，且每个 fd 都有自己的 close 生命周期。像素 payload（实际数据内容）没有随 Parcel 复制。

backing storage 的寿命也不只由可见 fd 数量决定。imported handle、`mmap`（把对象映射进进程虚拟地址空间）、设备 attachment、内核引用和对象缓存都可能继续持有它。最后一个相关引用释放后，dma-buf exporter 的 `release` 才有机会回收资源。

DMA-BUF 文档要求 exporter 创建 fd 时支持原子设置 `O_CLOEXEC`，使该 fd 在进程执行新程序时自动关闭，避免多线程程序在 `fork`/`exec` 之间的竞态窗口泄漏访问能力。这既是资源问题，也是安全边界。

### 3.3 DMA-BUF Heap 与 ION

DMA-BUF 本身不规定 backing storage 从哪里来。DMA-BUF Heap 是一个标准用户空间分配前端，通过 `/dev/dma_heap/<heap-name>` 分配并返回 dma-buf fd；GPU GEM（图形执行管理器的内存对象）、Camera 或 vendor allocator 也可以成为 exporter。

Android 12 的 GKI（Generic Kernel Image，通用内核镜像）2.0 用 DMA-BUF Heaps 替换 ION（Android 旧的共享内存分配框架）作为 GKI 分配框架。`libdmabufheap` 在迁移阶段曾支持把 heap name 映射回 ION；Android 17 的 `android-17.0.0_r1` 已移除 ION 实现。当前 `Alloc()` 打开 `/dev/dma_heap/<name>` 后直接执行 `DMA_HEAP_IOCTL_ALLOC`，打开失败就返回错误。带旧参数的 overload（重载函数）和 `MapNameToIonHeap()` 仅为二进制兼容保留，`CheckIonSupport()` 固定返回 false，不能再据此推导 ION fallback（备用路径）。设备上的 heap 名称、安全或物理连续策略、cache policy 与访问权限仍由产品和 vendor 决定。看到 `/dev/dma_heap/system` 等节点可以确认分配入口，不能据此断定物理内存控制器或带宽已经隔离。

## 4. 一次分配怎样发生

以 classic BufferQueue（不含 BLAST 特有封装的通用队列路径）为例，Android 17 `BufferQueueProducer::dequeueBuffer()` 会先选择可用 slot，再检查该 slot 的 `GraphicBuffer` 是否为空，或 width、height、format、layer count、usage 是否需要重新分配。

需要新 buffer 时，流程如下：

1. `BufferQueueProducer` 清理旧 slot 内容并设置 `BUFFER_NEEDS_REALLOCATION`（需要重新分配）；
2. 创建新的 `GraphicBuffer`；
3. `GraphicBufferAllocator` 按 Mapper 版本选择 Gralloc 2/3/4/5 allocator wrapper（对不同代接口的适配封装）；
4. vendor Allocator 按 descriptor 分配，并返回 raw native handle；
5. 常规 `GraphicBuffer` 分配会把 allocator 返回的 raw handle 导入为当前进程可用的 handle；只有显式请求 raw handle 的内部调用方会跳过这一步；
6. producer 看到 reallocation flag 后调用 `requestBuffer(slot)`，取得这一 slot 的 `GraphicBuffer`；
7. `queueBuffer()` 要求该 slot 已经执行过 `requestBuffer()`。

`GraphicBufferAllocator` 不直接承诺使用某个 DMA-BUF Heap。它只调用适配当前 Gralloc 版本的 allocator。AOSP 的 `sAllocList` 保存已分配 handle 的估算尺寸和请求者，用于 `dump()`、`getTotalSize()` 与 atrace（Android 系统 trace 标记）计数；释放后不会由这张表保留 buffer 供再次分配。

### 4.1 什么时候会复用 slot 中的 buffer

`GraphicBuffer::needsReallocation()` 在以下条件变化时返回 true：

- width 或 height；
- pixel format；
- layer count；
- 现有 usage 不能覆盖新 usage；
- protected usage 状态变化。

Android 17 的扩展分配 flag 开启时，additional options generation（附加分配选项的代次）变化也会触发 reallocation（重新分配）。反过来，属性仍兼容且 slot 中已有 buffer 时，dequeue 可以复用对象，不经过新的物理分配。

这里的“复用”是 BufferQueue slot 持有同一个 `GraphicBuffer`。vendor allocator 释放后是否缓存 backing storage 属于设备实现，不能从 AOSP `GraphicBufferAllocator` 或 slot 状态推导。

### 4.2 16 KB page size 怎样影响估算

Android 15 起平台支持 16 KB page size（内存页大小）设备。它会影响 ELF 可执行文件、`mmap`、页表和许多按页管理的区域，但不能简单写成“每个 GraphicBuffer 都按 16 KB 向上取整”。图形 buffer 可能采用多 plane、tile（分块布局）、压缩或 vendor 私有布局，最终 allocation size 由 allocator 和 exporter 决定。

评估图形内存时至少要区分：

- 逻辑尺寸：width × height；
- stride 与 plane layout；
- format、compression metadata 和 alignment；
- `reservedSize`；
- IOMMU/CPU mapping 与页表成本；
- 多进程统计是否重复计算同一 dma-buf inode（内核中标识同一文件对象的编号）。

`GraphicBufferAllocator` 的 `stride × height × bytesPerPixel` 只是部分格式的估算，源码也把 dump 文案写成 estimate。判断 16 KB 设备上的变化应使用 allocator metadata、dma-buf size 和目标设备测量。

### 4.3 DMA-BUF Heap 的页对齐边界

在 `android17-6.18-2026-06_r6` 中，通用 `dma_heap_buffer_alloc()` 会对传入长度执行 `PAGE_ALIGN`（按内核页大小向上对齐）。16 KB 内核因而把交给 DMA-BUF Heap 的最终长度向上取整到 16 KB；这一步发生在 Gralloc 已经决定 stride、plane、压缩 metadata 和实现对齐之后，不能反推所有 GraphicBuffer 的 stride 都是 16 KB 倍数。

通用 system heap 可以用多个不同 order（连续页块大小等级）的 page 构造 `sg_table`，不承诺整块 buffer 物理连续。IOMMU domain（同一套 I/O 地址空间）还会按自己的 `pgsize_bitmap` 选择支持的映射页大小；CPU base page、IOMMU page 和 GPU page table 不是同一个参数。

Android 17 的 `libdmabufheap` 已移除 ION 实现。`Alloc()` 打开目标 `/dev/dma_heap/<name>` 失败后直接返回错误，带 `legacy_align` 的 overload 只保留二进制兼容，`CheckIonSupport()` 固定为 false。`AllocSystem()` 是否选择 `system-uncached` 也只描述通用库入口；vendor Gralloc 仍可根据 format、usage、protected content 和硬件约束选择其他 exporter。

### 4.4 16 KB App 兼容不是图形内存开关

ELF `LOAD` segment（装载段）、APK 中未压缩 `.so`、`mmap()` 参数和硬编码 `4096` 属于应用运行时兼容问题。它们可以用 `getconf PAGE_SIZE`、`readelf -lW` 和 `zipalign -c -P 16` 分别验证，但通过这些检查既不能证明 GraphicBuffer layout 改变，也不能证明 GPU/HWC 性能提升。

排查时把三组证据分开保存：页大小与原生二进制文件兼容性；Surface、slot、buffer id、format/usage 和 fence 生命周期；dma-buf inode、size、exporter 与跨进程引用。多个进程导入同一个 inode 时不能把每个进程的映射大小相加成唯一物理占用。

## 5. GraphicBuffer 怎样跨进程

`GraphicBuffer` 实现 flatten/unflatten，即把对象序列化为可传输数据，再在接收端恢复。Android 17 的 `flatten()` 写入 13 个基础整数，其中包括尺寸、格式、usage、ID、generation number、transport fd 数量和 transport int 数量；transport ints 是随 handle 传输的普通整数，fd 则放入独立数组，私有整数跟在扁平数据之后。

接收端 `unflatten()`：

1. 校验格式、数量与边界；
2. 创建临时 `native_handle`；
3. 填入 Binder 已安装到本进程的 fd 和 transport ints；
4. 调用 `GraphicBufferMapper::importBuffer()`；
5. 关闭并删除临时 raw handle，保存 imported handle；
6. 对象析构时按 owner（负责释放资源的一方）类型调用 Mapper `freeBuffer()` 或 Allocator `free()`。

因此，fd 被成功传递仍不等于 Mapper import 一定成功。vendor metadata 不兼容、资源不足或错误 handle 都可能让 import 返回错误。

### 5.1 BufferQueue 为何不在每帧重传 handle

BufferQueue 两端按 slot 缓存 buffer。`BufferQueueConsumer::acquireBuffer()` 在某个 slot 第一次 acquire 新对象时返回 `mGraphicBuffer`；该 slot 之前已被 consumer acquire 过时，源码把输出的 `mGraphicBuffer` 设为 null，避免 consumer 再次 remap（重新导入或映射同一对象）。后续帧仍会携带 slot、frame number、fence、crop、transform、dataspace、damage 和时间信息。

以下序列用于说明 classic BufferQueue 的 handle 缓存点。以跨进程 consumer 为例，首次返回的 `GraphicBuffer` 在 IPC 反序列化时由 `GraphicBuffer::unflatten()` 调用 Mapper import；consumer 侧业务代码不会额外发起这次调用。

```mermaid
sequenceDiagram
    participant P as Producer
    participant BQ as BufferQueue
    participant C as Consumer

    P->>BQ: dequeueBuffer(attributes)
    BQ->>BQ: slot 为空或属性不兼容，分配 GraphicBuffer
    BQ-->>P: slot + BUFFER_NEEDS_REALLOCATION
    P->>BQ: requestBuffer(slot)
    BQ-->>P: GraphicBuffer handle
    P->>BQ: queueBuffer(slot, fence, metadata)
    C->>BQ: acquireBuffer()
    BQ-->>C: 首次返回 slot + GraphicBuffer transport + fence
    C->>C: IPC unflatten 导入 raw handle
    C->>BQ: releaseBuffer(slot, release fence)
    P->>BQ: 后续 queueBuffer(slot, fence, metadata)
    C->>BQ: 后续 acquireBuffer()
    BQ-->>C: slot + null GraphicBuffer + fence
```

图中 import 的进程和 IPC 次数取决于 BufferQueue 拓扑。同进程 producer/consumer 不需要跨 Binder 复制 fd。标准应用窗口常由应用进程内的 BLASTBufferQueue 先消费窗口 buffer，再用 `SurfaceControl.Transaction` 把 buffer 与窗口状态提交给 SurfaceFlinger；此时 SF（SurfaceFlinger）侧还有自己的 buffer cache 与 import 边界。不能把 classic BufferQueue 的单次 IPC 示意直接套到所有窗口。

## 6. 同步：共享地址不代表可以同时读写

Producer 把 GPU 或 CPU 写入完成的 fence 随 buffer 提交给 consumer。consumer 在读取前必须遵守该依赖；读取或显示结束后，再返回 release fence，告诉 producer 何时可以安全复用。Android native fence fd 通常由 `sync_file` 包装一个或多个 `dma_fence`。

这条关系与 fd 引用是两套机制：

- dma-buf/native handle 传递“访问哪块 buffer”；
- dma-fence/sync_file 传递“前一项异步工作何时完成”；
- BufferQueue slot 状态传递“当前所有权处于哪个阶段”。

关闭 fence fd 不等于释放 buffer，关闭 buffer fd 也不表示 GPU 工作已经完成。第 2.16 节会继续展开 fence 所有权和 signal/wait（标记完成/等待完成）。

### 6.1 CPU lock 也要处理同步与 cache

`AHardwareBuffer_lock()` 接收一个 fence fd。fence 非负时，API 会在 lock 过程中等待；传入负值时，调用者要保证先前写入已经完成。lock 还可能因硬件工作尚未完成、cache synchronization（CPU 与设备缓存同步）或实现条件而阻塞。

创建 buffer 时必须声明兼容的 CPU usage。受保护 buffer 不能与 CPU read/write usage 组合。CPU 写完后调用 `AHardwareBuffer_unlock()`：若传入 fence 输出指针，函数返回有效 fence fd 或 `-1`，调用者负责关闭有效 fd；若传入 `nullptr`，函数会阻塞到 unlock 工作完成。不能只依赖“同一进程里调用顺序”推断其他设备何时能看到新内容。

## 7. 生命周期与内存占用

一块图形 buffer 可能同时被以下对象持有：

- allocator/exporter 的 backing storage；
- 各进程中的 raw 或 imported native handle；
- BufferQueue producer/consumer slot；
- BLAST 或 SurfaceFlinger transaction/buffer cache；
- RenderEngine、HWC、Camera、codec 或 GPU driver 的设备 attachment；
- CPU mmap、EGLImage、Vulkan image/memory import；
- 尚未完成的异步工作与 fence 关联对象。

“Java 对象已回收”只排除了其中一类引用。排查泄漏需要同时确认 fd、imported handle、queue slot、layer、API image 与驱动对象的寿命。

常见错误包括：

- clone/dup（复制 handle 或 fd 引用）后遗漏 `native_handle_close()` 或关闭 fd；
- Mapper import 成功后遗漏 `freeBuffer()`；
- `AHardwareBuffer_acquire()` 与 `AHardwareBuffer_release()` 不配对；
- `Image`、`HardwareBuffer`、EGLImage 或 Vulkan import 对象关闭顺序错误；
- Surface 断开后，业务缓存仍持有旧 buffer；
- 异常路径提前返回，跳过 unlock、release 或 transaction release callback。

## 8. 怎样观测与归因

### 8.1 先按 dma-buf inode 去重

`/proc/<pid>/fd` 可以找到进程持有的 fd，`/proc/<pid>/fdinfo/<fd>` 在内核与驱动支持时提供 inode、size、exporter 等信息。不同进程中的两个 fd 若指向同一 dma-buf，按进程分别相加会重复统计，因此应先按 inode 去重。

内核开启 `CONFIG_DMABUF_SYSFS_STATS` 时，`/sys/kernel/dmabuf/buffers/<inode>/` 可提供 `size` 与 `exporter_name`。debugfs（内核调试文件系统）可用的调试设备上，还可以看 `/sys/kernel/debug/dma_buf/bufinfo`。user build（面向用户发布的系统构建）是否开放这些节点由内核配置与权限决定。

以下命令用于在有权限的设备上快速查看某个进程的 fd 与 fdinfo。它不会自动识别所有 vendor handle，还需要按 inode 汇总。

```bash
adb shell 'for f in /proc/<pid>/fd/*; do readlink \"$f\"; done'
adb shell 'for f in /proc/<pid>/fdinfo/*; do echo \"$f\"; cat \"$f\"; done'
adb shell 'find /sys/kernel/dmabuf/buffers -maxdepth 2 -type f -print 2>/dev/null'
```

第一组输出用于发现 fd 类型，第二组提供可关联字段，第三组查看全系统 dma-buf 统计。生产设备上遇到 permission denied 属于正常安全限制，不应为了普通性能采样而修改 SELinux 策略。

### 8.2 Perfetto 与系统 dump

Android 17 `GraphicBufferAllocator.cpp` 定义了两个直接观察点：

- `mem.gralloc.buffers`：当前注册在该进程 `sAllocList` 中的数量；
- `mem.gralloc.allocations`：分配 instant track（记录瞬时事件的轨道），包含 requestor、尺寸和 handle。

它们只覆盖经过该进程 `GraphicBufferAllocator` 的对象，不是系统全部 dma-buf。设备支持时还可采集 `dmabuf_heap/dma_heap_stat` ftrace event（内核函数跟踪事件）；事件是否存在取决于内核配置和 vendor 实现，应先检查 tracefs（内核 trace 接口文件系统）的 `available_events`。

结合以下信息更容易定位：

| 证据 | 回答的问题 |
|---|---|
| BufferQueue/BufferTX、slot 与 frame number | 哪条数据流在增加或长期持有 buffer |
| `mem.gralloc.*` | 哪个进程、请求者和尺寸触发 framework 分配 |
| dma-buf fdinfo/sysfs inode | 同一 backing storage 被哪些进程引用、大小与 exporter 是什么 |
| SurfaceFlinger layer trace/dump | layer 是否仍存在，buffer cache 与合成路径怎样 |
| fence、GPU 与 HWC trace | buffer 因异步工作未完成而不能复用，还是引用没有释放 |
| PSI（Pressure Stall Information，资源压力停顿统计）、direct reclaim（当前线程直接回收内存）、IOMMU/GPU driver 事件 | 分配慢是否来自内存压力或设备映射 |

看到 buffer 长时间处于 ACQUIRED 状态时，先判断 consumer 是否按协议持有，再看 release fence 和队列上限。Mapper import 通常发生在新 handle 首次出现时，不能把每次 ACQUIRED 停留都归因于 import。

## 9. 三类常见性能问题

### 9.1 分配抖动

Surface resize、format/usage 变化、protected 状态变化、slot 被清理、外部 buffer attach/detach（接入或移除队列），以及 additional options 更新，都可能触发 reallocation。分配路径会跨 framework、HAL、vendor allocator 和内核，内存压力下还可能伴随 reclaim（内存回收）或 IOMMU mapping。

优化时先查谁改变了 descriptor，再考虑预分配、稳定尺寸、减少 pool（可复用对象池）重建或延后非关键资源。不能使用脱离设备、格式和压力条件的统一毫秒数。

### 9.2 Camera/codec/display 的带宽竞争

Camera preview（相机预览）常把 HAL 产出的 buffer 交给 SurfaceTexture、ImageReader、GPU filter、codec 或 HWC。一个 camera buffer 可以在模块间共享，但 ISP（图像信号处理器）写入、GPU 采样、颜色转换、编码器读取和显示扫描都消耗内存带宽。

因此，零拷贝不等于零带宽。分析相机打开后 UI 掉帧时，应分别测量 Camera fence、GPU render pass、最终 Surface present、内存控制器与热状态；heap 名称本身不能证明物理带宽隔离。两条 BufferQueue 与中间 consumer/producer 需要分别检查，以确认积压位置。

视频也遵循同一原则。SurfaceView 视频可能保留独立 layer，TextureView 会把解码 buffer 再采样进宿主窗口；是否获得 HWC DEVICE composition 取决于格式、变换、protected 属性、plane 和带宽等整屏条件。“共享同一 buffer”“省去一次 RenderEngine 合成”和“没有内存带宽成本”是三种不同结论。

### 9.3 引用泄漏

fd 数量上涨只是线索。若 imported handle 被释放但进程还保留 mmap，或 fd 已关闭但 GPU object 仍持有 attachment，单看 `/proc/<pid>/fd` 都会漏判。反过来，同一个 dma-buf 在多个进程各有 fd 也不能按 fd 数量乘以 size。

应把分配事件、dma-buf inode、BufferQueue slot/layer、API 对象和释放时点放在同一时间范围内。只有确定“哪个引用超过预期寿命”，才能修正实际持有方。

## 10. 版本演进

### Android 12 / API 31

Android 12 的 GKI 2.0 以 DMA-BUF Heaps 替换 ION 分配框架。BufferQueue、GraphicBuffer 和 dma-buf 共享早已存在，变化集中在 allocator 的内核入口与 GKI 可维护性。旧版本或 vendor 私有组件仍可能保留 ION，不能仅按系统 API level 猜测节点；Android 17 AOSP 的 `libdmabufheap` 本身不再提供 ION fallback。

### Android 13–14

这两版持续演进 BLAST、SurfaceFlinger buffer cache、Composer 与内存诊断，但没有改变 dma-buf/Gralloc 的基本职责。讨论某个 cache purge（主动清理缓存）或 Composer 优化时，要绑定对应实现、HAL 版本和可复现内存变化，不能把它写成所有 buffer 生命周期的固定步骤。

### Android 15–16

16 KB page size 支持让 native library 与映射对齐受到更多关注；图形内存仍应以 allocator 返回的布局和 dma-buf size 为准。Stable AIDL Allocator 与 Stable-C Mapper 路径继续取代旧接口的主线位置，同时保留 vendor 兼容层。

### Android 17 / API 37

`android-17.0.0_r1` 中，Stable AIDL `IAllocator` 同时提供 `allocate2()`、capability（支持能力）查询和 multi-view 分配；Stable-C `IMapper.h` 同时声明 `AIMAPPER_VERSION_5` 与 `AIMAPPER_VERSION_6`，后者增加 multi-view 操作。framework 仍有 Gralloc 2/3/4/5 wrapper，说明当前系统需要适配多代 vendor HAL。

在内核 `android17-6.18-2026-06_r6` 中，dma-buf、dma-fence、dma-resv、sync_file 与 DMA-BUF Heap 仍是共享和同步基础。具体 GPU、display、Camera 与 codec driver 的 exporter、attachment、IOMMU 和 tracepoint（可供 trace 采集的内核事件点）要按设备补齐。

## 11. 常见误区

### GraphicBuffer 里保存了整帧像素

`GraphicBuffer` 保存描述信息与 handle。像素在 handle 引用的 backing storage 中，CPU lock 后获得的虚拟地址也只是一次映射。

### 跨进程传 GraphicBuffer 会复制像素

flatten/Binder 传递元数据、transport ints 和 fd 引用，不复制整帧 payload。后续 GPU 合成、格式转换或软件 copy 仍可能产生新的像素写入，需按渲染拓扑判断。

### 一个 GraphicBuffer 只有一个 dma-buf fd

常见 RGBA buffer 可能只有一个主 fd，但 `native_handle` 约定支持多个 fd 和整数。多 plane 与 vendor metadata 的布局由 Mapper 实现决定。

### 只要关闭 fd，内存就会释放

其他 fd、imported handle、mmap、attachment、queue slot 或驱动对象仍可持有引用。应追踪对象的完整生命周期。

### BufferQueue slot 复用等于 vendor 显存池

slot 复用表示继续持有同一个 `GraphicBuffer`。buffer 被释放后，vendor allocator 是否缓存 backing storage 是另一层策略，AOSP `sAllocList` 不提供该能力。

### 零拷贝意味着不占内存带宽

共享省去 IPC 边界的整帧副本，producer 写入、consumer 读取、合成与显示仍消耗带宽。Camera、GPU、codec 和 display 并发时尤其明显。

## 12. Android 17 源码入口

| 目标 | 源码 |
|---|---|
| GraphicBuffer transport 与释放 | `frameworks/native/libs/ui/GraphicBuffer.cpp` |
| allocator wrapper、统计 trace | `frameworks/native/libs/ui/GraphicBufferAllocator.cpp` |
| slot 分配与 producer 复用 | `frameworks/native/libs/gui/BufferQueueProducer.cpp` |
| consumer 首次 handle 传递 | `frameworks/native/libs/gui/BufferQueueConsumer.cpp` |
| BLAST transaction buffer 路径 | `frameworks/native/libs/gui/BLASTBufferQueue.cpp` |
| Stable AIDL Allocator | `hardware/interfaces/graphics/allocator/aidl/.../IAllocator.aidl` |
| Stable-C Mapper v5/v6 | `hardware/interfaces/graphics/mapper/stable-c/.../IMapper.h` |
| dma-buf exporter/importer | `drivers/dma-buf/dma-buf.c`、`include/linux/dma-buf.h` |
| DMA-BUF Heap | `drivers/dma-buf/dma-heap.c` |
| native fence fd | `drivers/dma-buf/sync_file.c` |

## 参考资料

- [Android Graphics architecture](https://source.android.com/docs/core/graphics/architecture)
- [Reduce graphics memory consumption](https://source.android.com/docs/core/graphics/reduce-consumption)
- [Transition from ION to DMA-BUF Heaps](https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps)
- [AHardwareBuffer NDK reference](https://developer.android.com/ndk/reference/group/a-hardware-buffer)
- [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- [Perfetto memory profiling：DMA-BUF ftrace event](https://perfetto.dev/docs/quickstart/heap-profiling)
- [Linux DMA-BUF documentation](https://docs.kernel.org/6.18/driver-api/dma-buf.html)
