---
title: "Android 16/17 图形内存分配边界：DMA-BUF、Gralloc 与 16KB Page"
chapter: "2.24"
status: ready-for-review
drafted_date: "2026-05-19"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-19"
last_verified_against: "AOSP refs/heads/master + Android Developers / AOSP Docs, 2026-05-19"
confidence: medium
sources:
  - type: aosp
    path: "system/memory/libdmabufheap/BufferAllocator.cpp"
  - type: aosp
    path: "system/memory/libdmabufheap/include/BufferAllocator/BufferAllocator.h"
  - type: aosp
    path: "hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl"
  - type: aosp
    path: "hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl"
  - type: aosp
    path: "frameworks/native/libs/ui/Gralloc4.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueProducer.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/IGraphicBufferProducer.cpp"
  - type: aosp
    path: "frameworks/native/libs/ui/GraphicBuffer.cpp"
  - type: official
    path: "https://source.android.com/docs/core/architecture/kernel/dma-buf-heaps"
  - type: official
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-19-android-dmabuf-gralloc-16kb-boundary.md"
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

这节把图形 buffer 的分配边界拆清楚：App 和 Framework 提出需求，gralloc / allocator 选择可用内存，kernel DMA-BUF heap 产出可跨进程传递的 fd。读完后要能区分三件事：AOSP 能验证的通用路径、厂商 gralloc 才知道的分配策略、16KB Page Size 只能证明到哪一层。

## 这节解决的问题

图形内存容易被写成一条直线：View 或 Surface 申请 buffer，gralloc 分配内存，SurfaceFlinger 拿去合成。这个说法够做入门图，但不够支撑 Android 16/17 的性能判断。分配路径里至少有四个边界：`BufferQueue` 只管理 slot、handle 和 fence；gralloc 根据宽高、格式、usage 和扩展参数做分配；`libdmabufheap` 面向 `/dev/dma_heap/*` 做用户态封装；kernel 的 page size 决定页粒度，不直接决定每个图形 buffer 的 stride、压缩模式或物理布局。

确定描述只覆盖能从 AOSP 和官方文档确认的部分。厂商私有 heap、Pixel / Qualcomm / MediaTek / Mali gralloc 的内部策略、16KB 页模式下的图形性能收益，都要靠设备源码、vendor log 或实机 trace 再确认。

[已验证: 官方文档, source.android.com/docs/core/architecture/kernel/dma-buf-heaps] Android 12 的 GKI 2.0 文档把 ION 到 DMA-BUF heap 的迁移理由写得很清楚：每个 DMA-BUF heap 是独立字符设备，可以用 sepolicy 分别控制访问；DMA-BUF heaps 的 ioctl ABI 由 upstream Linux kernel 维护，稳定性强于 Android 私有 ION 接口。文档给出的设备节点从 `/dev/ion` 迁移到 `/dev/dma_heap/<heap_name>`，常见通用节点包括 `/dev/dma_heap/system` 和 `/dev/dma_heap/system_uncached`。

## ION 到 DMA-BUF heap 的迁移路径

`libdmabufheap` 是迁移期留给用户态客户端的封装层。它没有把调用方绑死在某个 heap mask 上，而是让调用方用 heap name 表达需求，再由 `BufferAllocator` 选择 DMA-BUF heap 或回退到旧 ION 路径。

[已验证: AOSP refs/heads/master, system/memory/libdmabufheap/BufferAllocator.cpp] `BufferAllocator::Alloc(const std::string& heap_name, size_t len, unsigned int heap_flags, size_t legacy_align)` 的路径很直接：先调用 `OpenDmabufHeap(heap_name)`，打开成功就走 `DmabufAlloc(heap_name, len, dma_buf_heap_fd)`；如果对应 DMA-BUF heap 不存在，再进入 `IonAlloc(...)`。`legacy_align` 只传给旧 ION 分支，不能把它理解成 DMA-BUF heap 的通用对齐参数。

`DmabufAlloc()` 把 `len` 放进 `dma_heap_allocation_data`，通过 `DMA_HEAP_IOCTL_ALLOC` 获取新的 dma-buf fd。这个 fd 才是后续跨进程传递的对象，像素内容没有在 Binder Parcel 里复制。`AllocSystem()` 还会根据 `cpu_access_needed` 选择 `system-uncached` 或 `system` heap：不需要 CPU 访问时优先尝试 `system-uncached`，否则回到 `system`。这个选择只能说明通用库的分配入口，不能替代厂商 gralloc 对格式、usage、缓存策略和压缩策略的判断。

| 旧 ION 模型 | DMA-BUF heap 模型 | 性能分析时怎么用 |
|---|---|---|
| 调用方传 heap mask / flags | 调用方传 heap name，例如 `system` / `system_uncached` | 查 `/dev/dma_heap/*` 和 allocator log，确认设备暴露了哪些 heap |
| `/dev/ion` 是统一入口 | 每个 heap 是独立字符设备 | sepolicy、节点权限、vendor 私有 heap 要分开看 |
| `legacy_align` 可进入 ION 分配 | DMA-BUF 分支按 heap ioctl 分配 | 不要把旧参数写成 16KB 图形 buffer 对齐证据 |

[已验证: AOSP refs/heads/master, system/memory/libdmabufheap/include/BufferAllocator/BufferAllocator.h] `BufferAllocator.h` 对 `Alloc()` 的注释也限定了边界：如果 DMA-BUF heap 分配失败且 ION fd 可用，库会从保存的 heap 映射里找 ION heap ID / mask。这个注释说明 `libdmabufheap` 是兼容层，不是图形 buffer 策略层。

## Gralloc4 / IAllocator 的描述符边界

图形 buffer 的需求不会直接变成 `DMA_HEAP_IOCTL_ALLOC`。Framework 侧先构造描述符，描述符描述宽、高、层数、像素格式、usage、保留区和扩展参数，再交给 allocator / mapper 实现。这里的关键边界是：AOSP 定义字段和接口契约，厂商实现决定这些字段如何映射到内存类型、压缩模式、stride 和私有 heap。

[已验证: AOSP refs/heads/master, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl] AIDL 版 `IAllocator` 提供 `allocate2(in BufferDescriptorInfo descriptor, in int count)`，并保留旧的 `allocate(in byte[] descriptor, in int count)`。接口注释写明，`allocate()` 在 allocator V2 搭配 `AIMAPPER_VERSION_5` 时已被 `allocate2()` 替代；如果仍在使用 graphics mapper 4，旧接口仍要实现。这个版本边界写文章时要留住，避免把 Android 10-13、Android 14+、Android 16/17 的 allocator 入口混成一个版本。

[已验证: AOSP refs/heads/master, hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl] `BufferDescriptorInfo.additionalOptions` 是 `ExtendableType[]`，注释说它用于“不会改变整体 usage、但会影响 buffer 如何分配”的扩展选项，示例是 EGL surface compression 的压缩等级；allocator 对不认识的 option 应返回 `isSupported() == false` 并拒绝分配。这里没有 AOSP 通用的 “16KB 图形 buffer 对齐开关”。如果某台设备用 additionalOptions 传 page-size、压缩、secure heap 或 vendor 私有参数，那是设备实现约定，不是跨设备 API 契约。

[已验证: AOSP refs/heads/master, frameworks/native/libs/ui/Gralloc4.cpp] Framework 侧 `Gralloc4Mapper::createDescriptor()` 先校验 `BufferDescriptorInfo`，再调用 mapper 的 `createDescriptor()`；`validateBufferSize()` 也会重新构造描述符并把 stride 交给 mapper 校验。这说明 Framework 能检查字段范围和 usage bit，但 buffer 的物理布局仍在 mapper / allocator 实现里完成。

| 描述符字段 | AOSP 层能确认什么 | 不该写成什么 |
|---|---|---|
| `width` / `height` / `layerCount` | 调用方请求的几何信息 | 最终行跨度一定等于宽度 |
| `format` | 像素格式需求 | 厂商内部存储格式一定与外部格式一致 |
| `usage` | CPU / GPU / compositor / protected 等使用意图 | 某个 usage 必然命中固定 heap |
| `reservedSize` | buffer 关联保留区大小 | 图形像素区大小 |
| `additionalOptions` | 可扩展分配选项，未知项应拒绝 | 通用 16KB 对齐开关 |

## BufferQueue 中的图形 buffer 传递路径

`BufferQueue` 的职责是管理生产者和消费者之间的 slot 状态、`GraphicBuffer` handle、acquire / release fence，以及队列顺序。它不是 allocator。生产者侧拿到的是 slot 和 fence，必要时再通过 `requestBuffer()` 读取对应 slot 的 `GraphicBuffer`。

[已验证: AOSP refs/heads/master, frameworks/native/libs/gui/BufferQueueProducer.cpp] `BufferQueueProducer::requestBuffer(int slot, sp<GraphicBuffer>* buf)` 会检查 slot 范围和状态，然后把 `mSlots[slot].mGraphicBuffer` 返回给调用方。`queueBuffer()` 入队时，把 `mSlots[slot].mGraphicBuffer`、`acquireFence`、frame number、transform、dataspace 等字段写进 `BufferItem`。这些字段描述的是“这帧使用哪个 buffer、何时可读、如何显示”，不是“重新分配一块内存”。

[已验证: AOSP refs/heads/master, frameworks/native/libs/gui/IGraphicBufferProducer.cpp] Binder 代理 `BpGraphicBufferProducer::requestBuffer()` 发送 `REQUEST_BUFFER` transaction，收到 reply 后创建 `GraphicBuffer` 并调用 `reply.read(**buf)`。同一文件还存在 `requestBuffers()` / `dequeueBuffers()` 这类批量接口，用 vector 承载多个 slot 请求或出队请求。批量接口能减少 transaction 次数，但不能直接推出 fd 安装成本已经被消除；fd 仍随 native handle 进入 Binder 传输路径。

[已验证: AOSP refs/heads/master, frameworks/native/libs/ui/GraphicBuffer.cpp] `GraphicBuffer::flatten()` 会写入 `width`、`height`、`stride`、`format`、`layerCount`、64 位 `usage`、generation number，并把 native handle 中的 fd 数和 int 数记录到扁平化数据里，同时把 fd 拷到 Parcel 的 fd 区。`unflatten()` 读取 `numFds` / `numInts`，并做数量上限和空间检查。这个源码锚点足够支撑一个判断：跨进程传递的是 handle 和 fd，不是图形 buffer 内容。

和 2.13、2.16 的关系可以这样放：2.13 讲 BufferQueue 的 slot 状态机，2.16 讲 fence 控制读写时序，这里补充“buffer 内存来自哪里，以及 fd 如何成为跨进程共享句柄”。这样不会重复写前面章节已经覆盖的状态机和同步机制。

## 16KB Page Size 对图形内存的影响

[已验证: 官方文档, source.android.com/docs/core/architecture/16kb-page-size/16kb] 官方文档把 page size 定义为 OS 管理内存的粒度。Android 历史上围绕 4KB page size 构建，ARM CPU 支持 16KB page size；从 Android 15 开始，AOSP 支持构建 16KB page size 的 Android。文档还写明，Android 15 及以上支持 16KB ELF alignment，配合 android14-6.1 及以上内核，可同时运行在 4KB 和 16KB kernel 上。

[已验证: 官方文档, developer.android.com/guide/practices/page-sizes] 面向应用开发者的文档要求：只要 App 直接或通过 SDK 使用 NDK 库，就要为 16KB 设备重新构建；共享库 ELF segment 必须满足 16KB ELF alignment。这个要求主要约束 native binary 的装载和内存映射，不等于图形 buffer 都自动获得更低延迟或更低内存占用。

图形 buffer 受 16KB page size 影响的路径更靠后：kernel 以页为单位管理内存，DMA-BUF heap 返回的 fd 背后是按 kernel 规则分配的内存对象；gralloc 再在这层内存对象上处理像素格式、usage、stride、padding、压缩和 cache policy。16KB 页可以改变页粒度和页表行为，也可能增加小对象内部浪费。具体到某个 Surface、视频 overlay 或游戏 swapchain，性能收益要看 buffer 尺寸、访问模式、GPU / display controller 约束、vendor allocator 策略和是否发生额外拷贝。

| 判断对象 | 能写成确定结论 | 需要设备证据 |
|---|---|---|
| 系统 page size | `getconf PAGE_SIZE` 或内核配置可确认 4KB / 16KB | 无 |
| App native 库兼容性 | ELF segment alignment 必须满足 16KB 要求 | 具体 SDK 是否已重构建 |
| DMA-BUF heap 节点 | `/dev/dma_heap/*` 可列出通用和私有 heap | 私有 heap 的用途、权限、分配策略 |
| gralloc 分配结果 | handle fd、stride、format、usage 可从日志 / dumpsys / trace 侧面观察 | 物理连续性、压缩模式、page-size 专用分支 |
| 性能收益 | 官方只说明 16KB 模式有系统性能收益和额外内存成本 | 单场景帧耗时、内存占用、功耗、TLB 相关指标 |

所以，本节不把 “Android 16/17 + 16KB Page Size” 写成图形内存优化公式。更稳的写法是：16KB 是系统内存管理和 native 兼容性的版本边界，图形 buffer 的结果还要经过 gralloc / allocator / heap / vendor 实现四层转换。

## AOSP 通用能力与厂商实现边界

AOSP 能验证的是接口和通用实现：`libdmabufheap` 怎么打开 `/dev/dma_heap/<heap_name>`，`IAllocator` 描述符有哪些字段，`BufferQueue` 怎么传递 `GraphicBuffer`，`GraphicBuffer::flatten()` 怎么携带 fd。厂商实现决定的是更接近硬件的部分：哪些 usage 命中 secure heap、video heap 或 camera heap，压缩格式怎么选，stride 怎么补齐，buffer 是否复用，以及 16KB 页模式下有没有专门路径。

| 层级 | AOSP 可验证内容 | 厂商 / 设备相关内容 |
|---|---|---|
| Kernel DMA-BUF heap | `/dev/dma_heap/system`、`system_uncached`、`DMA_HEAP_IOCTL_ALLOC` | `qcom,*`、`mtk,*`、secure / camera / video 私有 heap 命名和权限 |
| `libdmabufheap` | heap name 到 DMA-BUF / ION 兼容路径 | 调用方选择哪个 heap、是否包一层缓存池 |
| Gralloc / mapper | 描述符字段、usage 校验、mapper / allocator 接口 | format 转换、压缩、stride、cache policy、page-size 专用策略 |
| BufferQueue | slot、fence、handle、frame number 的传递 | producer / consumer 调用频率、是否复用 buffer、SurfaceFlinger / HWC 决策 |
| 16KB page size | AOSP 构建支持、ELF alignment、kernel page granularity | 图形场景收益、额外内存成本、SoC display / GPU 约束 |

[待验证] Pixel Tensor、Qualcomm、MediaTek、Mali gralloc 是否在 Android 16/17 上为 16KB 页模式添加专门分支，需要读取对应 vendor 源码或设备日志。公开 AOSP 通用路径不足以证明这个判断。

## 可观测信号与排障入口

排查图形内存问题时，不要只看单个 “graphics memory” 数字。更可靠的做法是把 page size、heap 节点、buffer 数、fd 数、SurfaceFlinger 状态和帧时序放在同一张证据表里。

| 要确认的问题 | 推荐入口 | 读数方式 |
|---|---|---|
| 设备是否运行在 16KB 页模式 | `adb shell getconf PAGE_SIZE` | 返回 `16384` 才能把问题归入 16KB 设备路径 |
| 系统暴露了哪些 DMA-BUF heap | `adb shell ls -l /dev/dma_heap` | 区分 `system`、`system_uncached` 与 vendor 私有 heap |
| 某个进程是否持有大量图形 fd | `adb shell ls -l /proc/<pid>/fd`，结合 `dmabuf` / `anon_inode` 名称 | fd 数持续增长时，再查 buffer 生命周期和 Surface 复用 |
| SurfaceFlinger 是否积压 buffer | `adb shell dumpsys SurfaceFlinger`、Winscope | 查 layer、buffer count、composition 类型、可见性和窗口状态 |
| 帧是否卡在 producer / consumer 同步 | Perfetto FrameTimeline、SurfaceFlinger slice、fence 相关事件 | 回连 2.13 BufferQueue 和 2.16 Sync Fence 判断阻塞点 |
| dma-buf 全局占用 | root / userdebug 设备上的 `/sys/kernel/debug/dma_buf/bufinfo` 或 vendor 诊断节点 | release 设备常被权限挡住，不能当作通用线上方案 |

一个实用判断顺序是：先确认 page size 和 heap 节点，再看进程 fd / buffer 数是否增长，随后用 SurfaceFlinger / Winscope 判断 layer 是否复用异常，再用 Perfetto 把 producer、consumer、fence 和合成时序放回同一帧。只要其中一步缺证据，就不要把问题直接归因到 16KB Page Size。

## 扩展

### Binder fd array 与 GraphicBuffer 跨进程传递

[待验证] AOSP 中 `IGraphicBufferProducer` 已有 `requestBuffers()` / `dequeueBuffers()` 批量接口，`GraphicBuffer::flatten()` 也明确携带 native handle fd。还需要继续确认 Binder 驱动层 fd array 安装路径、批量接口在不同 producer 中的调用频率，以及它对高频 BufferQueue 场景的成本占比。暂不把 “批量 fd 安装降低 BufferQueue 成本” 写成确定结论。

### libdmabufheap pooling 与 buffer 复用

[已验证: AOSP refs/heads/master, system/memory/libdmabufheap/BufferAllocator.cpp] 当前 `BufferAllocator::Alloc()` / `DmabufAlloc()` 路径是打开 heap、执行 ioctl、返回 fd；源码里没有通用 buffer pool。图形 buffer 复用主要在上层对象生命周期里观察，例如 BufferQueue slot 复用、producer 缓存、Surface / ImageReader / codec 的 buffer 管理，或厂商 allocator 的私有策略。

### 设备级 16KB 图形内存验证清单

设备验证至少要收集这些信息：

- 系统页大小：`getconf PAGE_SIZE`，记录设备型号、系统版本、kernel 版本。
- Native 兼容性：用官方脚本或构建检查确认 `.so` 的 16KB ELF alignment。
- Heap 节点：列出 `/dev/dma_heap/*`，标注通用 heap 和 vendor 私有 heap。
- 图形 buffer 状态：记录 SurfaceFlinger layer、buffer count、composition 类型、相关进程 fd 数。
- 帧时序：抓 Perfetto，保留 FrameTimeline、SurfaceFlinger、RenderThread、Binder 和 fence 相关轨道。
- 版本边界：把 Android 15/16/17、kernel 分支、SoC、GPU、display HAL / gralloc 版本写进证据包。

缺少这些证据时，文章里只能写“可能受 16KB 页模式影响”，不能写成确定性能结论。

## 参考资料

### Android 16/17 DMA-BUF/Gralloc 图形内存优化版本边界验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-26-android-16-17-dmabuf-gralloc-graphics-memory-version-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：源码级验证三个关键论点：(1) AOSP libdmabufheap 无通用池化路径，池化属厂商私有实现；(2) IAllocator allocate2() additionalOptions 在 Android 15 已存在非 Android 16 新增；(3) GraphicBuffer flatten/unflatten 仍为传统 transport
- 注入时间：2026-05-28
- 价值：源码级验证材料，含 AOSP 路径、版本矩阵和未验证项标注，可直接作为章节补充参考


- [已验证: 官方文档] Transition from ION to DMA-BUF heaps (5.4 kernel only), Android Open Source Project, `source.android.com/docs/core/architecture/kernel/dma-buf-heaps`
- [已验证: 官方文档] 16 KB page size, Android Open Source Project, `source.android.com/docs/core/architecture/16kb-page-size/16kb`
- [已验证: 官方文档] Support 16 KB page sizes, Android Developers, `developer.android.com/guide/practices/page-sizes`
- [已验证: AOSP refs/heads/master] `system/memory/libdmabufheap/BufferAllocator.cpp`
- [已验证: AOSP refs/heads/master] `hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/IAllocator.aidl`
- [已验证: AOSP refs/heads/master] `hardware/interfaces/graphics/allocator/aidl/android/hardware/graphics/allocator/BufferDescriptorInfo.aidl`
- [已验证: AOSP refs/heads/master] `frameworks/native/libs/ui/Gralloc4.cpp`
- [已验证: AOSP refs/heads/master] `frameworks/native/libs/gui/BufferQueueProducer.cpp`
- [已验证: AOSP refs/heads/master] `frameworks/native/libs/gui/IGraphicBufferProducer.cpp`
- [已验证: AOSP refs/heads/master] `frameworks/native/libs/ui/GraphicBuffer.cpp`
- [来源: Obsidian/DeepResearch/2026-05-19-android-dmabuf-gralloc-16kb-boundary.md] 源码调研：Android 16/17 图形内存优化 DMA-BUF/Gralloc 公开边界验证

### Android 16/17 DMA-BUF/Gralloc 图形内存版本边界验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-26-android-16-17-dmabuf-gralloc-graphics-memory-version-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：源码级验证三个关键论点：AOSP libdmabufheap 无通用池化路径；allocate2() additionalOptions 在 Android 15 已存在非 16 新增；GraphicBuffer flatten/unflatten 未用 FDA 批量安装。此前引用的 20%-40% 收益缺 benchmark 支撑。
- 注入时间：2026-05-27
- 价值：纠正 AIW 章节中多处版本边界错误，含 AOSP android-16.0.0_r1 源码锚点验证

